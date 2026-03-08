#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use tauri::{Emitter, Manager, WindowEvent};

#[cfg(target_os = "windows")]
#[repr(C)]
struct POINT {
    x: i32,
    y: i32,
}

#[cfg(target_os = "windows")]
extern "system" {
    fn GetCursorPos(point: *mut POINT) -> i32;
}

#[cfg(target_os = "windows")]
fn get_cursor_pos() -> (i32, i32) {
    unsafe {
        let mut pt = POINT { x: 0, y: 0 };
        GetCursorPos(&mut pt);
        (pt.x, pt.y)
    }
}

#[derive(Clone, serde::Deserialize)]
struct UiRect {
    x: f64,
    y: f64,
    width: f64,
    height: f64,
}

struct HitTestState {
    rects: Vec<UiRect>,
    ignoring: bool,
}

struct AudioStreamState {
    child: Option<Child>,
}

#[derive(Clone, serde::Serialize)]
struct AudioLogEvent {
    level: String,
    message: String,
}

#[tauri::command]
fn register_ui_rects(state: tauri::State<'_, Arc<Mutex<HitTestState>>>, rects: Vec<UiRect>) {
    if let Ok(mut state) = state.lock() {
        state.rects = rects;
    }
}

#[tauri::command]
fn start_live_audio_stream(
    app: tauri::AppHandle,
    state: tauri::State<'_, Arc<Mutex<AudioStreamState>>>,
    python_exe: String,
    script_path: String,
    base_url: String,
    session_id: String,
    source: String,
    sample_rate: i32,
    channels: i32,
    chunk_ms: i32,
    device_name: Option<String>,
) -> Result<(), String> {
    println!(
        "start_live_audio_stream called: python_exe={} script_path={} base_url={} session_id={} source={} sample_rate={} channels={} chunk_ms={} device_name={:?}",
        python_exe, script_path, base_url, session_id, source, sample_rate, channels, chunk_ms, device_name
    );

    stop_live_audio_stream_internal(&state)?;

    let mut command = Command::new(&python_exe);
    command
        .arg(&script_path)
        .arg("--source")
        .arg(&source)
        .arg("--base-url")
        .arg(&base_url)
        .arg("--session-id")
        .arg(&session_id)
        .arg("--sample-rate")
        .arg(sample_rate.to_string())
        .arg("--channels")
        .arg(channels.to_string())
        .arg("--chunk-ms")
        .arg(chunk_ms.to_string())
        .arg("--output-mode")
        .arg("json")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    if let Some(name) = device_name {
        if !name.trim().is_empty() {
            command.arg("--device-name").arg(name);
        }
    }

    let mut child = command
        .spawn()
        .map_err(|error| format!("live audio stream spawn 실패: {error}"))?;

    println!("live audio stream spawned successfully");

    if let Some(stdout) = child.stdout.take() {
        let app_handle = app.clone();
        thread::spawn(move || {
            use std::io::{BufRead, BufReader};

            let reader = BufReader::new(stdout);
            for line in reader.lines().map_while(Result::ok) {
                println!("live audio payload: {}", line);
                let _ = app_handle.emit("live-audio-payload", line);
            }
        });
    }

    if let Some(stderr) = child.stderr.take() {
        let app_handle = app.clone();
        thread::spawn(move || {
            use std::io::{BufRead, BufReader};

            let reader = BufReader::new(stderr);
            for line in reader.lines().map_while(Result::ok) {
                eprintln!("live audio stderr: {}", line);
                let _ = app_handle.emit(
                    "live-audio-log",
                    AudioLogEvent {
                        level: "error".into(),
                        message: line,
                    },
                );
            }
        });
    }

    if let Ok(mut guard) = state.lock() {
        guard.child = Some(child);
    }

    Ok(())
}

#[tauri::command]
fn stop_live_audio_stream(
    state: tauri::State<'_, Arc<Mutex<AudioStreamState>>>,
) -> Result<(), String> {
    stop_live_audio_stream_internal(&state)
}

fn stop_live_audio_stream_internal(
    state: &tauri::State<'_, Arc<Mutex<AudioStreamState>>>,
) -> Result<(), String> {
    let mut guard = state
        .lock()
        .map_err(|_| "live audio state lock 실패".to_string())?;

    if let Some(mut child) = guard.child.take() {
        println!("stopping live audio stream child process");
        child
            .kill()
            .map_err(|error| format!("live audio stream 종료 실패: {error}"))?;
    }

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(Arc::new(Mutex::new(HitTestState {
            rects: vec![],
            ignoring: false,
        })))
        .manage(Arc::new(Mutex::new(AudioStreamState { child: None })))
        .invoke_handler(tauri::generate_handler![
            register_ui_rects,
            start_live_audio_stream,
            stop_live_audio_stream
        ])
        .setup(|app| {
            let window = app
                .get_webview_window("overlay")
                .expect("overlay 윈도우를 찾을 수 없습니다");
            let _ = window.set_always_on_top(true);
            let _ = window.set_title("Meeting Overlay HUD");

            if let Some(monitor) = window.current_monitor().ok().flatten() {
                let size = monitor.size();
                let pos = monitor.position();
                let _ = window.set_position(tauri::PhysicalPosition::new(pos.x, pos.y));
                let _ = window.set_size(tauri::PhysicalSize::new(size.width, size.height));
            }

            let _ = window.set_ignore_cursor_events(true);

            let hit_state = app.state::<Arc<Mutex<HitTestState>>>().inner().clone();
            let win = window.clone();

            #[cfg(target_os = "windows")]
            thread::spawn(move || loop {
                thread::sleep(Duration::from_millis(50));

                let (cx, cy) = get_cursor_pos();
                let scale = win.scale_factor().unwrap_or(1.0);
                let win_pos = match win.outer_position() {
                    Ok(position) => position,
                    Err(_) => continue,
                };

                let rx = (cx - win_pos.x) as f64 / scale;
                let ry = (cy - win_pos.y) as f64 / scale;

                let mut state = match hit_state.lock() {
                    Ok(guard) => guard,
                    Err(_) => continue,
                };

                let over_ui = state.rects.iter().any(|rect| {
                    rx >= rect.x
                        && rx <= rect.x + rect.width
                        && ry >= rect.y
                        && ry <= rect.y + rect.height
                });

                if over_ui && state.ignoring {
                    let _ = win.set_ignore_cursor_events(false);
                    state.ignoring = false;
                } else if !over_ui && !state.ignoring {
                    let _ = win.set_ignore_cursor_events(true);
                    state.ignoring = true;
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let audio_state = window.state::<Arc<Mutex<AudioStreamState>>>();
                let _ = stop_live_audio_stream_internal(&audio_state);
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("tauri overlay shell 실행에 실패했습니다.");
}

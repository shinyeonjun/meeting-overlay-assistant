#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::Write;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use tauri::{Emitter, Manager, WindowEvent};

#[cfg(target_os = "windows")]
#[repr(C)]
struct Point {
    x: i32,
    y: i32,
}

#[cfg(target_os = "windows")]
extern "system" {
    fn GetCursorPos(point: *mut Point) -> i32;
}

#[cfg(target_os = "windows")]
fn get_cursor_pos() -> (i32, i32) {
    unsafe {
        let mut pt = Point { x: 0, y: 0 };
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
    config: Option<AudioStreamConfig>,
    prewarmed: bool,
}

#[derive(Clone, serde::Serialize)]
struct AudioLogEvent {
    level: String,
    message: String,
}

#[derive(Clone, serde::Serialize)]
struct AudioExitEvent {
    source: String,
    prewarmed: bool,
    exit_code: Option<i32>,
}

#[derive(Clone, PartialEq, Eq)]
struct AudioStreamConfig {
    python_exe: String,
    script_path: String,
    source: String,
    sample_rate: i32,
    channels: i32,
    chunk_ms: i32,
    device_name: Option<String>,
    silence_gate_enabled: bool,
    silence_gate_min_rms_bits: u32,
    silence_gate_hold_chunks: i32,
}

impl AudioStreamConfig {
    fn new(
        python_exe: String,
        script_path: String,
        source: String,
        sample_rate: i32,
        channels: i32,
        chunk_ms: i32,
        device_name: Option<String>,
        silence_gate_enabled: bool,
        silence_gate_min_rms: f32,
        silence_gate_hold_chunks: i32,
    ) -> Self {
        Self {
            python_exe,
            script_path,
            source,
            sample_rate,
            channels,
            chunk_ms,
            device_name: normalize_optional(device_name),
            silence_gate_enabled,
            silence_gate_min_rms_bits: silence_gate_min_rms.to_bits(),
            silence_gate_hold_chunks,
        }
    }

    fn silence_gate_min_rms(&self) -> f32 {
        f32::from_bits(self.silence_gate_min_rms_bits)
    }
}

#[tauri::command]
fn register_ui_rects(state: tauri::State<'_, Arc<Mutex<HitTestState>>>, rects: Vec<UiRect>) {
    if let Ok(mut state) = state.lock() {
        state.rects = rects;
    }
}

fn normalize_optional(value: Option<String>) -> Option<String> {
    value.and_then(|raw| {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            None
        } else {
            Some(trimmed.to_string())
        }
    })
}

fn send_child_command(child: &mut Child, payload: &str) -> Result<(), String> {
    let stdin = child
        .stdin
        .as_mut()
        .ok_or_else(|| "live audio stream stdin이 닫혀 있습니다.".to_string())?;
    stdin
        .write_all(format!("{payload}\n").as_bytes())
        .map_err(|error| format!("live audio stream 명령 전송 실패: {error}"))?;
    stdin
        .flush()
        .map_err(|error| format!("live audio stream stdin flush 실패: {error}"))?;
    Ok(())
}

fn start_audio_stream_monitor(
    app: tauri::AppHandle,
    state: Arc<Mutex<AudioStreamState>>,
) {
    thread::spawn(move || loop {
        thread::sleep(Duration::from_millis(200));

        let exit_event = {
            let mut guard = match state.lock() {
                Ok(guard) => guard,
                Err(_) => continue,
            };

            let status = match guard.child.as_mut() {
                Some(child) => match child.try_wait() {
                    Ok(status) => status,
                    Err(_) => None,
                },
                None => None,
            };

            status.map(|status| {
                let event = AudioExitEvent {
                    source: guard
                        .config
                        .as_ref()
                        .map(|config| config.source.clone())
                        .unwrap_or_else(|| "unknown".to_string()),
                    prewarmed: guard.prewarmed,
                    exit_code: status.code(),
                };
                guard.child = None;
                guard.config = None;
                guard.prewarmed = false;
                event
            })
        };

        if let Some(event) = exit_event {
            let _ = app.emit("live-audio-exit", event);
        }
    });
}

fn spawn_live_audio_stream_child(
    app: &tauri::AppHandle,
    state: &tauri::State<'_, Arc<Mutex<AudioStreamState>>>,
    config: AudioStreamConfig,
    base_url: Option<String>,
    session_id: Option<String>,
    access_token: Option<String>,
    prewarm_only: bool,
) -> Result<(), String> {
    let mut command = Command::new(&config.python_exe);
    command
        .arg(&config.script_path)
        .arg("--source")
        .arg(&config.source)
        .arg("--sample-rate")
        .arg(config.sample_rate.to_string())
        .arg("--channels")
        .arg(config.channels.to_string())
        .arg("--chunk-ms")
        .arg(config.chunk_ms.to_string())
        .arg("--output-mode")
        .arg("json")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    if prewarm_only {
        command.arg("--prewarm-only");
    } else {
        let resolved_base_url =
            base_url.ok_or_else(|| "base_url이 필요합니다.".to_string())?;
        let resolved_session_id =
            session_id.ok_or_else(|| "session_id가 필요합니다.".to_string())?;
        command.arg("--base-url").arg(resolved_base_url);
        command.arg("--session-id").arg(resolved_session_id);
        if let Some(token) = normalize_optional(access_token) {
            command.arg("--access-token").arg(token);
        }
    }

    if let Some(name) = &config.device_name {
        command.arg("--device-name").arg(name);
    }

    if config.silence_gate_enabled {
        command.arg("--silence-gate-enabled");
        command
            .arg("--silence-gate-min-rms")
            .arg(config.silence_gate_min_rms().to_string());
        command
            .arg("--silence-gate-hold-chunks")
            .arg(config.silence_gate_hold_chunks.to_string());
    }

    let mut child = command
        .spawn()
        .map_err(|error| format!("live audio stream 시작 실패: {error}"))?;

    if let Some(stdout) = child.stdout.take() {
        let app_handle = app.clone();
        thread::spawn(move || {
            use std::io::{BufRead, BufReader};

            let reader = BufReader::new(stdout);
            for line in reader.lines().map_while(Result::ok) {
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

    let mut guard = state
        .lock()
        .map_err(|_| "live audio state lock 실패".to_string())?;
    guard.child = Some(child);
    guard.config = Some(config);
    guard.prewarmed = prewarm_only;
    Ok(())
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
    access_token: Option<String>,
    silence_gate_enabled: bool,
    silence_gate_min_rms: f32,
    silence_gate_hold_chunks: i32,
) -> Result<(), String> {
    let config = AudioStreamConfig::new(
        python_exe,
        script_path,
        source,
        sample_rate,
        channels,
        chunk_ms,
        device_name,
        silence_gate_enabled,
        silence_gate_min_rms,
        silence_gate_hold_chunks,
    );

    let should_reuse = {
        let mut guard = state
            .lock()
            .map_err(|_| "live audio state lock 실패".to_string())?;
        let reusable = guard.child.is_some()
            && guard.prewarmed
            && guard.config.as_ref() == Some(&config);

        if reusable {
            let command = serde_json::json!({
                "type": "start_stream",
                "session_id": session_id,
                "base_url": base_url,
                "access_token": access_token,
            })
            .to_string();
            if let Some(child) = guard.child.as_mut() {
                send_child_command(child, &command)?;
            }
            guard.prewarmed = false;
        }

        reusable
    };

    if should_reuse {
        return Ok(());
    }

    stop_live_audio_stream_internal(&state)?;
    spawn_live_audio_stream_child(
        &app,
        &state,
        config,
        Some(base_url),
        Some(session_id),
        access_token,
        false,
    )
}

#[tauri::command]
fn prewarm_live_audio_stream(
    app: tauri::AppHandle,
    state: tauri::State<'_, Arc<Mutex<AudioStreamState>>>,
    python_exe: String,
    script_path: String,
    source: String,
    sample_rate: i32,
    channels: i32,
    chunk_ms: i32,
    device_name: Option<String>,
    silence_gate_enabled: bool,
    silence_gate_min_rms: f32,
    silence_gate_hold_chunks: i32,
) -> Result<(), String> {
    let config = AudioStreamConfig::new(
        python_exe,
        script_path,
        source,
        sample_rate,
        channels,
        chunk_ms,
        device_name,
        silence_gate_enabled,
        silence_gate_min_rms,
        silence_gate_hold_chunks,
    );

    {
        let guard = state
            .lock()
            .map_err(|_| "live audio state lock 실패".to_string())?;
        if guard.child.is_some() && guard.config.as_ref() == Some(&config) {
            return Ok(());
        }
    }

    stop_live_audio_stream_internal(&state)?;
    spawn_live_audio_stream_child(&app, &state, config, None, None, None, true)
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
        let mut graceful_exit = false;

        if let Some(stdin) = child.stdin.as_mut() {
            if stdin.write_all(b"stop\n").is_ok() && stdin.flush().is_ok() {
                for _ in 0..15 {
                    match child.try_wait() {
                        Ok(Some(_status)) => {
                            graceful_exit = true;
                            break;
                        }
                        Ok(None) => thread::sleep(Duration::from_millis(100)),
                        Err(_error) => break,
                    }
                }
            }
        }

        if !graceful_exit {
            child
                .kill()
                .map_err(|error| format!("live audio stream 종료 실패: {error}"))?;
        }
    }

    guard.config = None;
    guard.prewarmed = false;
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(Arc::new(Mutex::new(HitTestState {
            rects: vec![],
            ignoring: false,
        })))
        .manage(Arc::new(Mutex::new(AudioStreamState {
            child: None,
            config: None,
            prewarmed: false,
        })))
        .invoke_handler(tauri::generate_handler![
            register_ui_rects,
            start_live_audio_stream,
            prewarm_live_audio_stream,
            stop_live_audio_stream
        ])
        .setup(|app| {
            let audio_state = app.state::<Arc<Mutex<AudioStreamState>>>().inner().clone();
            start_audio_stream_monitor(app.handle().clone(), audio_state);

            let window = app
                .get_webview_window("overlay")
                .expect("overlay 창을 찾을 수 없습니다");
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

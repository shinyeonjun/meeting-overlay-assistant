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

/// 앱이 어떤 식으로 끝나든(정상 종료, 강제 종료, 개발 서버 중지) 캡처 프로세스가 남지 않게 한다.
///
/// 앱 프로세스를 "마지막 핸들이 닫히면 안의 프로세스를 모두 끝내는" Job Object에 넣는다.
/// 이후 띄우는 캡처 프로세스와 그 자식(venv 실행기가 띄우는 실제 python)도 같은 Job에 들어가고,
/// 앱이 사라져 핸들이 닫히면 Windows가 함께 정리한다.
#[cfg(target_os = "windows")]
mod process_job {
    use std::ffi::c_void;

    const JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS: i32 = 9;
    const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x2000;

    #[repr(C)]
    #[derive(Default)]
    struct IoCounters {
        read_operation_count: u64,
        write_operation_count: u64,
        other_operation_count: u64,
        read_transfer_count: u64,
        write_transfer_count: u64,
        other_transfer_count: u64,
    }

    #[repr(C)]
    #[derive(Default)]
    struct BasicLimitInformation {
        per_process_user_time_limit: i64,
        per_job_user_time_limit: i64,
        limit_flags: u32,
        minimum_working_set_size: usize,
        maximum_working_set_size: usize,
        active_process_limit: u32,
        affinity: usize,
        priority_class: u32,
        scheduling_class: u32,
    }

    #[repr(C)]
    #[derive(Default)]
    struct ExtendedLimitInformation {
        basic_limit_information: BasicLimitInformation,
        io_info: IoCounters,
        process_memory_limit: usize,
        job_memory_limit: usize,
        peak_process_memory_used: usize,
        peak_job_memory_used: usize,
    }

    extern "system" {
        fn CreateJobObjectW(attributes: *mut c_void, name: *const u16) -> *mut c_void;
        fn SetInformationJobObject(job: *mut c_void, class: i32, info: *mut c_void, length: u32) -> i32;
        fn AssignProcessToJobObject(job: *mut c_void, process: *mut c_void) -> i32;
        fn GetCurrentProcess() -> *mut c_void;
    }

    /// 성공하면 true. 핸들은 일부러 닫지 않는다 (앱이 끝날 때 OS가 닫으며 정리가 일어난다).
    pub fn attach_current_process() -> bool {
        unsafe {
            let job = CreateJobObjectW(std::ptr::null_mut(), std::ptr::null());
            if job.is_null() {
                return false;
            }
            let mut info = ExtendedLimitInformation::default();
            info.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            let configured = SetInformationJobObject(
                job,
                JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                &mut info as *mut ExtendedLimitInformation as *mut c_void,
                std::mem::size_of::<ExtendedLimitInformation>() as u32,
            );
            if configured == 0 {
                return false;
            }
            AssignProcessToJobObject(job, GetCurrentProcess()) != 0
        }
    }
}

/// 프로세스와 그 자식까지 끝낸다. venv의 python.exe는 실제 인터프리터를 자식으로 띄우는
/// 실행기라서 `Child::kill()`만으로는 실제 캡처 프로세스가 남는다.
fn kill_process_tree(child: &mut Child) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let status = Command::new("taskkill")
            .args(["/T", "/F", "/PID", &child.id().to_string()])
            .creation_flags(CREATE_NO_WINDOW)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
        if matches!(status, Ok(s) if s.success()) {
            let _ = child.wait();
            return Ok(());
        }
    }
    child
        .kill()
        .map_err(|error| format!("live audio stream 종료 실패: {error}"))?;
    let _ = child.wait();
    Ok(())
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
            python_exe: resolve_repo_path(&python_exe),
            script_path: resolve_repo_path(&script_path),
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

/// 상대 경로를 저장소 루트(빌드 시점의 src-tauri 기준 세 단계 위) 기준으로 푼다.
fn resolve_repo_path(raw: &str) -> String {
    let path = std::path::Path::new(raw);
    if path.is_absolute() {
        return raw.to_string();
    }
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("..")
        .join(path)
        .to_string_lossy()
        .into_owned()
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
            kill_process_tree(&mut child)?;
        }
    }

    guard.config = None;
    guard.prewarmed = false;
    Ok(())
}

fn main() {
    #[cfg(target_os = "windows")]
    if !process_job::attach_current_process() {
        eprintln!("[overlay] Job Object를 붙이지 못했습니다. 앱이 강제 종료되면 캡처 프로세스가 남을 수 있습니다.");
    }

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
                // 창을 숨기기만 하면 트레이도 없어 다시 열 방법 없이 앱과 캡처가 남는다. 캡처를 멈추고 앱을 끝낸다.
                api.prevent_close();
                let audio_state = window.state::<Arc<Mutex<AudioStreamState>>>();
                let _ = stop_live_audio_stream_internal(&audio_state);
                window.app_handle().exit(0);
            }
        })
        .run(tauri::generate_context!())
        .expect("tauri overlay shell 실행에 실패했습니다.");
}

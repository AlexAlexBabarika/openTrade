// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

fn project_root() -> std::path::PathBuf {
    let manifest = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest.parent().unwrap().to_path_buf()
}

fn spawn_backend() -> Option<Child> {
    let root = project_root();
    let script = root.join("run_backend.py");
    if !script.exists() {
        eprintln!("OpenTrade: run_backend.py not found at {:?}", script);
        return None;
    }
    for cmd in ["python3", "python"] {
        if let Ok(c) = Command::new(cmd)
            .arg("run_backend.py")
            .current_dir(&root)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
        {
            std::thread::sleep(Duration::from_millis(800));
            return Some(c);
        }
    }
    eprintln!("OpenTrade: could not start Python backend");
    None
}

pub struct BackendProcess(pub Mutex<Option<Child>>);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_handle = BackendProcess(Mutex::new(spawn_backend()));

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(backend_handle)
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if window.app_handle().webview_windows().len() == 0 {
                    if let Some(backend) = window.app_handle().try_state::<BackendProcess>() {
                        if let Ok(mut guard) = backend.0.lock() {
                            if let Some(mut child) = guard.take() {
                                let _ = child.kill();
                            }
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

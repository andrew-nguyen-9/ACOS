mod haptics;

use std::sync::Mutex;
use tauri::http::{Response, StatusCode};
use tauri::Manager;
use tauri_plugin_shell::{process::CommandChild, ShellExt};

struct BackendProcess(Mutex<Option<CommandChild>>);

/// Minimal extension→MIME map for the asset:// scheme. Kept tiny (no mime crate)
/// — the scheme only serves the local images / exported docs ACOS itself writes.
fn mime_for(path: &std::path::Path) -> &'static str {
    match path.extension().and_then(|e| e.to_str()) {
        Some("png") => "image/png",
        Some("jpg") | Some("jpeg") => "image/jpeg",
        Some("webp") => "image/webp",
        Some("svg") => "image/svg+xml",
        Some("pdf") => "application/pdf",
        Some("json") => "application/json",
        _ => "application/octet-stream",
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        // 13.9 (ADR-011): signed background auto-update + relaunch. The updater
        // verifies each artifact's signature against the bundled pubkey before
        // applying; a tampered/unsigned artifact is rejected.
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        // asset:// custom scheme (PERF-IPC-002): serve local files via memory read
        // instead of HTTP. Every path goes through resolve_asset_path, which
        // canonicalizes against the allowlisted app-data dir and rejects traversal.
        .register_uri_scheme_protocol("asset", |ctx, request| {
            let app = ctx.app_handle();
            let root = match app.path().app_data_dir() {
                Ok(dir) => dir,
                Err(_) => {
                    return Response::builder()
                        .status(StatusCode::INTERNAL_SERVER_ERROR)
                        .body(Vec::new())
                        .unwrap()
                }
            };
            match haptics::resolve_asset_path(&root, request.uri().path()) {
                Some(path) => match std::fs::read(&path) {
                    Ok(bytes) => Response::builder()
                        .status(StatusCode::OK)
                        .header("Content-Type", mime_for(&path))
                        .body(bytes)
                        .unwrap(),
                    Err(_) => Response::builder()
                        .status(StatusCode::NOT_FOUND)
                        .body(Vec::new())
                        .unwrap(),
                },
                None => Response::builder()
                    .status(StatusCode::FORBIDDEN)
                    .body(Vec::new())
                    .unwrap(),
            }
        })
        .setup(|app| {
            // Ensure the allowlisted asset root exists so the scheme can serve.
            if let Ok(dir) = app.path().app_data_dir() {
                let _ = std::fs::create_dir_all(&dir);
            }
            let sidecar_cmd = app.shell().sidecar("acos-backend")?;
            let (_rx, child) = sidecar_cmd.spawn()?;
            app.manage(BackendProcess(Mutex::new(Some(child))));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(state) = window.app_handle().try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![haptics::haptic])
        .run(tauri::generate_context!())
        .expect("error while running ACOS");
}

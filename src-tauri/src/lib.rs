mod gateway;
mod gateway_artifact;
mod gateway_diagnostics;

use std::sync::Arc;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let gateway_diagnostics =
                gateway_diagnostics::new_shared_gateway_diagnostics(256, 64 * 1024);
            let diagnostics_for_runtime = gateway_diagnostics.clone();
            app.manage(gateway_diagnostics);
            match gateway::start_gateway(&app.handle(), diagnostics_for_runtime) {
                Ok(gateway_runtime) => {
                    app.manage(gateway_runtime);
                }
                Err(err) => {
                    eprintln!("gateway startup degraded: {err}");
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            gateway::get_gateway_info,
            gateway_diagnostics::get_gateway_diagnostics
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                if let Some(runtime) = window
                    .app_handle()
                    .try_state::<Arc<gateway::GatewayRuntime>>()
                {
                    let _ = runtime.shutdown();
                }
                window.app_handle().exit(0);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

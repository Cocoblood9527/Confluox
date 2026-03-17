mod gateway;

use std::io;
use std::sync::Arc;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let gateway_runtime =
                gateway::start_gateway(&app.handle()).map_err(io::Error::other)?;
            app.manage(gateway_runtime);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![gateway::get_gateway_info])
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

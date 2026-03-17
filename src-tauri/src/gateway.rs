use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use tauri::AppHandle;
use tauri::Manager;
use uuid::Uuid;

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GatewayInfo {
    pub base_url: String,
    pub auth_token: String,
}

#[derive(Debug, Deserialize)]
struct ReadyPayload {
    status: String,
    port: Option<u16>,
    pid: Option<u32>,
    message: Option<String>,
}

pub struct GatewayRuntime {
    pub info: GatewayInfo,
    child: Mutex<Option<Child>>,
    ready_file: PathBuf,
}

impl GatewayRuntime {
    pub fn shutdown(&self) -> Result<(), String> {
        let _ = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(2))
            .build()
            .map_err(|err| err.to_string())
            .and_then(|client| {
                client
                    .post(format!("{}/api/system/shutdown", self.info.base_url))
                    .header("Authorization", format!("Bearer {}", self.info.auth_token))
                    .send()
                    .map_err(|err| err.to_string())?;
                Ok(())
            });

        let mut child = {
            let mut lock = self.child.lock().map_err(|_| "gateway lock poisoned")?;
            lock.take()
        };

        if let Some(mut process) = child.take() {
            let deadline = Instant::now() + Duration::from_secs(3);
            loop {
                match process.try_wait() {
                    Ok(Some(_)) => break,
                    Ok(None) => {
                        if Instant::now() >= deadline {
                            let _ = process.kill();
                            let _ = process.wait();
                            break;
                        }
                        thread::sleep(Duration::from_millis(100));
                    }
                    Err(_) => break,
                }
            }
        }

        let _ = fs::remove_file(&self.ready_file);
        Ok(())
    }
}

#[tauri::command]
pub fn get_gateway_info(state: tauri::State<'_, Arc<GatewayRuntime>>) -> GatewayInfo {
    state.info.clone()
}

pub fn start_gateway(app: &AppHandle) -> Result<Arc<GatewayRuntime>, String> {
    let data_dir = app.path().app_data_dir().map_err(|err| err.to_string())?;
    fs::create_dir_all(&data_dir).map_err(|err| err.to_string())?;

    let ready_file = data_dir.join("gateway.ready.json");
    let _ = fs::remove_file(&ready_file);

    let auth_token = Uuid::new_v4().to_string();
    let host_pid = std::process::id();
    let allowed_origin = if cfg!(debug_assertions) {
        "http://localhost:1420".to_string()
    } else {
        "tauri://localhost".to_string()
    };

    let child = spawn_gateway_process(
        app,
        &data_dir,
        &auth_token,
        &ready_file,
        host_pid,
        &allowed_origin,
    )?;
    let child_pid = child.id();
    let port = wait_for_ready_port(&ready_file, child_pid, Duration::from_secs(30))?;

    Ok(Arc::new(GatewayRuntime {
        info: GatewayInfo {
            base_url: format!("http://127.0.0.1:{port}"),
            auth_token,
        },
        child: Mutex::new(Some(child)),
        ready_file,
    }))
}

fn spawn_gateway_process(
    app: &AppHandle,
    data_dir: &Path,
    auth_token: &str,
    ready_file: &Path,
    host_pid: u32,
    allowed_origin: &str,
) -> Result<Child, String> {
    let mut cmd = if cfg!(debug_assertions) {
        let gateway_dir = workspace_root()?.join("gateway");
        let mut command = Command::new("python3");
        command.current_dir(gateway_dir);
        command.arg("-m").arg("gateway.main");
        command
    } else {
        let resource_dir = app.path().resource_dir().map_err(|err| err.to_string())?;
        let gateway_bin = resource_dir.join("gateway");
        if gateway_bin.exists() {
            Command::new(gateway_bin)
        } else {
            let gateway_dir = workspace_root()?.join("gateway");
            let mut command = Command::new("python3");
            command.current_dir(gateway_dir);
            command.arg("-m").arg("gateway.main");
            command
        }
    };

    cmd.arg("--data-dir")
        .arg(data_dir)
        .arg("--auth-token")
        .arg(auth_token)
        .arg("--ready-file")
        .arg(ready_file)
        .arg("--host-pid")
        .arg(host_pid.to_string())
        .arg("--allowed-origin")
        .arg(allowed_origin)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::inherit());

    cmd.spawn().map_err(|err| err.to_string())
}

fn wait_for_ready_port(ready_file: &Path, child_pid: u32, timeout: Duration) -> Result<u16, String> {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if let Ok(content) = fs::read_to_string(ready_file) {
            let parsed: ReadyPayload =
                serde_json::from_str(&content).map_err(|err| format!("invalid ready json: {err}"))?;
            if parsed.status == "error" {
                return Err(parsed
                    .message
                    .unwrap_or_else(|| "gateway reported startup error".to_string()));
            }
            if parsed.status == "ready" {
                if parsed.pid == Some(child_pid) {
                    if let Some(port) = parsed.port {
                        return Ok(port);
                    }
                }
            }
        }
        thread::sleep(Duration::from_millis(200));
    }
    Err("timed out waiting for gateway ready file".to_string())
}

fn workspace_root() -> Result<PathBuf, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| "failed to resolve workspace root".to_string())
}

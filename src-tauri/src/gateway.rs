use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::env;
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

    let mut child = spawn_gateway_process(
        app,
        &data_dir,
        &auth_token,
        &ready_file,
        host_pid,
        &allowed_origin,
    )?;
    let port = wait_for_ready_port(&ready_file, &mut child, Duration::from_secs(30))?;

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
        let mut command = Command::new(resolve_python_interpreter()?);
        command.current_dir(gateway_dir);
        command.arg("-m").arg("gateway.main");
        command
    } else {
        let resource_dir = app.path().resource_dir().map_err(|err| err.to_string())?;
        let gateway_bin = resolve_bundled_gateway_binary(&resource_dir)?;
        Command::new(gateway_bin)
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

fn executable_name(base: &str) -> String {
    match env::consts::EXE_SUFFIX {
        "" => base.to_string(),
        suffix => format!("{base}.{suffix}"),
    }
}

fn resolve_bundled_gateway_binary(resource_dir: &Path) -> Result<PathBuf, String> {
    let gateway_name = executable_name("gateway");
    let legacy_name = executable_name("confluox-gateway");
    let candidates = vec![
        resource_dir.join(&gateway_name),
        resource_dir.join(&legacy_name),
        resource_dir.join("gateway").join(&gateway_name),
        resource_dir.join("gateway").join(&legacy_name),
        resource_dir.join("confluox-gateway").join(&legacy_name),
        resource_dir.join("confluox-gateway").join(&gateway_name),
    ];

    for candidate in &candidates {
        if candidate.is_file() {
            return Ok(candidate.to_path_buf());
        }
    }

    let checked = candidates
        .iter()
        .map(|path| path.display().to_string())
        .collect::<Vec<_>>()
        .join(", ");
    Err(format!(
        "bundled gateway executable not found in resources dir {} (checked: {}). build gateway artifact first (gateway/scripts/build_gateway.sh) and include it via tauri bundle resources",
        resource_dir.display(),
        checked
    ))
}

fn wait_for_ready_port(
    ready_file: &Path,
    child: &mut Child,
    timeout: Duration,
) -> Result<u16, String> {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if let Ok(Some(status)) = child.try_wait() {
            return Err(format!("gateway exited before ready file: {status}"));
        }

        if let Ok(content) = fs::read_to_string(ready_file) {
            let parsed: ReadyPayload = serde_json::from_str(&content)
                .map_err(|err| format!("invalid ready json: {err}"))?;
            if parsed.status == "error" {
                return Err(parsed
                    .message
                    .unwrap_or_else(|| "gateway reported startup error".to_string()));
            }
            if parsed.status == "ready" {
                if parsed.pid == Some(child.id()) {
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

fn resolve_python_interpreter() -> Result<String, String> {
    let mut candidates: Vec<String> = Vec::new();
    if let Ok(value) = env::var("CONFLUOX_PYTHON") {
        candidates.push(value);
    }
    if let Ok(value) = env::var("PYTHON") {
        candidates.push(value);
    }
    candidates.push("/Library/Frameworks/Python.framework/Versions/3.12/bin/python3".to_string());
    candidates.push("/opt/homebrew/bin/python3".to_string());
    candidates.push("/usr/local/bin/python3".to_string());
    candidates.push("python3".to_string());

    let mut seen = HashSet::new();
    for candidate in candidates {
        if !seen.insert(candidate.clone()) {
            continue;
        }
        if python_has_gateway_deps(&candidate) {
            return Ok(candidate);
        }
    }

    Err("failed to locate Python interpreter with fastapi+uvicorn".to_string())
}

fn python_has_gateway_deps(python: &str) -> bool {
    Command::new(python)
        .arg("-c")
        .arg("import fastapi, uvicorn")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

fn workspace_root() -> Result<PathBuf, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .map(|p| p.to_path_buf())
        .ok_or_else(|| "failed to resolve workspace root".to_string())
}

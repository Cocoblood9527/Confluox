use crate::gateway_artifact::resolve_gateway_binary_from_artifacts;
use crate::gateway_diagnostics::SharedGatewayDiagnostics;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
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
    bootstrap_stdin: Mutex<Option<ChildStdin>>,
    ready_file: PathBuf,
    diagnostics: SharedGatewayDiagnostics,
}

impl GatewayRuntime {
    pub fn shutdown(&self) -> Result<(), String> {
        if let Ok(mut stdin_handle) = self.bootstrap_stdin.lock() {
            let _ = stdin_handle.take();
        }

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

        with_gateway_diagnostics(&self.diagnostics, |diagnostics| {
            diagnostics.append_shutdown("gateway runtime shutdown complete");
        });

        let _ = fs::remove_file(&self.ready_file);
        Ok(())
    }
}

#[tauri::command]
pub fn get_gateway_info(state: tauri::State<'_, Arc<GatewayRuntime>>) -> GatewayInfo {
    state.info.clone()
}

pub fn start_gateway(
    app: &AppHandle,
    diagnostics: SharedGatewayDiagnostics,
) -> Result<Arc<GatewayRuntime>, String> {
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

    let spawned = match spawn_gateway_process(
        app,
        &data_dir,
        &auth_token,
        &ready_file,
        host_pid,
        &allowed_origin,
        diagnostics.clone(),
    ) {
        Ok(spawned) => spawned,
        Err(err) => {
            with_gateway_diagnostics(&diagnostics, |capture| {
                capture.append_startup_status(false, Some(err.clone()));
            });
            return Err(err);
        }
    };
    let SpawnedGatewayProcess {
        mut child,
        bootstrap_stdin,
    } = spawned;
    let port = match wait_for_ready_port(&ready_file, &mut child, Duration::from_secs(30)) {
        Ok(port) => port,
        Err(err) => {
            with_gateway_diagnostics(&diagnostics, |capture| {
                capture.append_startup_status(false, Some(err.clone()));
            });
            return Err(err);
        }
    };

    with_gateway_diagnostics(&diagnostics, |capture| {
        capture.append_startup_status(true, None);
    });

    Ok(Arc::new(GatewayRuntime {
        info: GatewayInfo {
            base_url: format!("http://127.0.0.1:{port}"),
            auth_token,
        },
        child: Mutex::new(Some(child)),
        bootstrap_stdin: Mutex::new(Some(bootstrap_stdin)),
        ready_file,
        diagnostics,
    }))
}

struct SpawnedGatewayProcess {
    child: Child,
    bootstrap_stdin: ChildStdin,
}

fn spawn_gateway_process(
    app: &AppHandle,
    data_dir: &Path,
    auth_token: &str,
    ready_file: &Path,
    host_pid: u32,
    allowed_origin: &str,
    diagnostics: SharedGatewayDiagnostics,
) -> Result<SpawnedGatewayProcess, String> {
    let mut cmd = if cfg!(debug_assertions) {
        let gateway_dir = workspace_root()?.join("gateway");
        let mut command = Command::new(resolve_python_interpreter()?);
        command.current_dir(gateway_dir);
        command.arg("-m").arg("gateway.main");
        command
    } else {
        let resource_dir = app.path().resource_dir().map_err(|err| err.to_string())?;
        let gateway_bin = resolve_gateway_binary_from_artifacts(&resource_dir)?;
        Command::new(gateway_bin)
    };

    cmd.arg("--ready-file")
        .arg(ready_file)
        .arg("--host-pid")
        .arg(host_pid.to_string())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    let mut child = cmd.spawn().map_err(|err| err.to_string())?;
    let mut bootstrap_stdin = child
        .stdin
        .take()
        .ok_or_else(|| "failed to capture gateway stdin".to_string())?;
    if let Err(err) = write_gateway_bootstrap_payload(
        &mut bootstrap_stdin,
        data_dir,
        auth_token,
        allowed_origin,
    ) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(err);
    }

    let log_file = open_gateway_runtime_log(data_dir);

    if let Some(stdout) = child.stdout.take() {
        spawn_gateway_stream_reader("stdout", stdout, diagnostics.clone(), log_file.clone());
    }

    if let Some(stderr) = child.stderr.take() {
        spawn_gateway_stream_reader("stderr", stderr, diagnostics, log_file);
    }

    Ok(SpawnedGatewayProcess {
        child,
        bootstrap_stdin,
    })
}

#[derive(Serialize)]
struct GatewayBootstrapPayload {
    data_dir: String,
    auth_token: String,
    allowed_origin: String,
}

fn write_gateway_bootstrap_payload(
    stdin: &mut ChildStdin,
    data_dir: &Path,
    auth_token: &str,
    allowed_origin: &str,
) -> Result<(), String> {
    let payload = GatewayBootstrapPayload {
        data_dir: data_dir.to_string_lossy().to_string(),
        auth_token: auth_token.to_string(),
        allowed_origin: allowed_origin.to_string(),
    };
    serde_json::to_writer(&mut *stdin, &payload).map_err(|err| err.to_string())?;
    stdin.write_all(b"\n").map_err(|err| err.to_string())?;
    stdin.flush().map_err(|err| err.to_string())
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

type SharedLogFile = Arc<Mutex<fs::File>>;

fn open_gateway_runtime_log(data_dir: &Path) -> Option<SharedLogFile> {
    let log_path = data_dir.join("gateway.runtime.log");
    fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(log_path)
        .ok()
        .map(|file| Arc::new(Mutex::new(file)))
}

fn spawn_gateway_stream_reader(
    stream_name: &'static str,
    stream: impl std::io::Read + Send + 'static,
    diagnostics: SharedGatewayDiagnostics,
    log_file: Option<SharedLogFile>,
) {
    thread::spawn(move || {
        let mut reader = BufReader::new(stream);
        let mut line = String::new();
        loop {
            line.clear();
            match reader.read_line(&mut line) {
                Ok(0) => break,
                Ok(_) => {
                    let message = line.trim_end_matches(['\r', '\n']).to_string();
                    if stream_name == "stdout" {
                        with_gateway_diagnostics(&diagnostics, |capture| {
                            capture.append_stdout(message.clone());
                        });
                    } else {
                        with_gateway_diagnostics(&diagnostics, |capture| {
                            capture.append_stderr(message.clone());
                        });
                    }
                    write_runtime_log(&log_file, stream_name, &message);
                }
                Err(err) => {
                    let message = format!("failed to read gateway {stream_name}: {err}");
                    with_gateway_diagnostics(&diagnostics, |capture| {
                        capture.append_stderr(message.clone());
                    });
                    write_runtime_log(&log_file, "reader-error", &message);
                    break;
                }
            }
        }
    });
}

fn write_runtime_log(log_file: &Option<SharedLogFile>, stream_name: &str, message: &str) {
    let Some(log_file) = log_file else {
        return;
    };
    if let Ok(mut file) = log_file.lock() {
        let _ = writeln!(file, "[gateway:{stream_name}] {message}");
    }
}

fn with_gateway_diagnostics(
    diagnostics: &SharedGatewayDiagnostics,
    operation: impl FnOnce(&mut crate::gateway_diagnostics::GatewayDiagnostics),
) {
    if let Ok(mut capture) = diagnostics.lock() {
        operation(&mut capture);
    }
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

use serde::Deserialize;
use std::fs;
use std::path::{Component, Path, PathBuf};

const TRACK_PRIORITY: [&str; 2] = ["nuitka", "pyinstaller"];

#[derive(Debug, Deserialize)]
struct GatewayArtifact {
    track: String,
    entry: String,
}

pub fn resolve_gateway_binary_from_artifacts(resource_dir: &Path) -> Result<PathBuf, String> {
    let gateway_root = resource_dir.join("gateway");
    let mut checked_paths: Vec<String> = Vec::new();
    let mut failure_reasons: Vec<String> = Vec::new();

    for expected_track in TRACK_PRIORITY {
        let artifact_path = gateway_root.join(expected_track).join("gateway-artifact.json");
        checked_paths.push(artifact_path.display().to_string());

        let artifact = match load_artifact(&artifact_path) {
            Ok(artifact) => artifact,
            Err(reason) => {
                failure_reasons.push(reason);
                continue;
            }
        };

        if artifact.track != expected_track {
            failure_reasons.push(format!(
                "{} has mismatched track field '{}'",
                artifact_path.display(),
                artifact.track
            ));
            continue;
        }
        if artifact.entry.trim().is_empty() {
            failure_reasons.push(format!("{} has empty 'entry' field", artifact_path.display()));
            continue;
        }
        if Path::new(&artifact.entry).is_absolute() {
            failure_reasons.push(format!(
                "{} has invalid absolute entry '{}'",
                artifact_path.display(),
                artifact.entry
            ));
            continue;
        }
        if !is_safe_relative_entry(&artifact.entry) {
            failure_reasons.push(format!(
                "{} entry '{}' escapes track directory via unsafe relative path",
                artifact_path.display(),
                artifact.entry
            ));
            continue;
        }

        let artifact_dir = artifact_path
            .parent()
            .expect("artifact file path should have a parent");
        let entry_path = artifact_dir.join(&artifact.entry);
        if !entry_path.is_file() {
            failure_reasons.push(format!(
                "{} points to missing entry {}",
                artifact_path.display(),
                entry_path.display()
            ));
            continue;
        }

        let artifact_dir_real = match fs::canonicalize(artifact_dir) {
            Ok(path) => path,
            Err(err) => {
                failure_reasons.push(format!(
                    "failed to canonicalize artifact dir {}: {}",
                    artifact_dir.display(),
                    err
                ));
                continue;
            }
        };
        let entry_real = match fs::canonicalize(&entry_path) {
            Ok(path) => path,
            Err(err) => {
                failure_reasons.push(format!(
                    "failed to canonicalize entry {}: {}",
                    entry_path.display(),
                    err
                ));
                continue;
            }
        };
        if entry_real.starts_with(&artifact_dir_real) {
            return Ok(entry_real);
        }
        failure_reasons.push(format!(
            "{} entry {} escapes track directory {}",
            artifact_path.display(),
            entry_path.display(),
            artifact_dir.display()
        ));
    }

    Err(format!(
        "bundled gateway executable not found via artifact metadata in resources dir {} (checked paths: {}; reasons: {}). build gateway artifacts first (gateway/scripts/build_gateway.sh) and include dist/gateway via tauri bundle resources",
        resource_dir.display(),
        checked_paths.join(", "),
        failure_reasons.join(" | "),
    ))
}

fn load_artifact(path: &Path) -> Result<GatewayArtifact, String> {
    let content = fs::read_to_string(path)
        .map_err(|err| format!("{} is unavailable: {}", path.display(), err))?;
    serde_json::from_str::<GatewayArtifact>(&content)
        .map_err(|err| format!("{} is invalid JSON: {}", path.display(), err))
}

fn is_safe_relative_entry(entry: &str) -> bool {
    let path = Path::new(entry);
    if path.is_absolute() {
        return false;
    }
    path.components().all(|component| {
        !matches!(
            component,
            Component::ParentDir | Component::RootDir | Component::Prefix(_)
        )
    })
}

#[cfg(test)]
mod tests {
    use super::resolve_gateway_binary_from_artifacts;
    use serde_json::json;
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn selects_nuitka_before_pyinstaller_when_both_exist() {
        let resource_dir = create_temp_resource_dir("both");
        write_track(&resource_dir, "pyinstaller", "confluox-gateway/confluox-gateway");
        write_track(&resource_dir, "nuitka", "confluox-gateway.dist/confluox-gateway");

        let selected = resolve_gateway_binary_from_artifacts(&resource_dir).unwrap();

        assert!(selected.ends_with(Path::new(
            "gateway/nuitka/confluox-gateway.dist/confluox-gateway"
        )));
    }

    #[test]
    fn falls_back_to_pyinstaller_when_nuitka_missing() {
        let resource_dir = create_temp_resource_dir("fallback");
        write_track(&resource_dir, "pyinstaller", "confluox-gateway/confluox-gateway");

        let selected = resolve_gateway_binary_from_artifacts(&resource_dir).unwrap();

        assert!(selected.ends_with(Path::new(
            "gateway/pyinstaller/confluox-gateway/confluox-gateway"
        )));
    }

    #[test]
    fn returns_diagnostic_error_when_no_artifact_available() {
        let resource_dir = create_temp_resource_dir("missing");

        let err = resolve_gateway_binary_from_artifacts(&resource_dir).unwrap_err();

        let nuitka_artifact = Path::new("gateway")
            .join("nuitka")
            .join("gateway-artifact.json")
            .display()
            .to_string();
        let pyinstaller_artifact = Path::new("gateway")
            .join("pyinstaller")
            .join("gateway-artifact.json")
            .display()
            .to_string();

        assert!(err.contains("checked paths"));
        assert!(err.contains(&nuitka_artifact));
        assert!(err.contains(&pyinstaller_artifact));
    }

    #[test]
    fn rejects_entry_that_escapes_track_directory() {
        let resource_dir = create_temp_resource_dir("escape");
        let track_dir = resource_dir.join("gateway").join("nuitka");
        fs::create_dir_all(&track_dir).expect("must create track dir");
        fs::write(resource_dir.join("outside-bin"), b"fake-binary").expect("must write outside file");

        let payload = json!({
            "track": "nuitka",
            "platform": "darwin-arm64",
            "entry": "../outside-bin",
            "resources_dir": ".",
            "version": "0.1.0",
            "built_at": "2026-03-17T00:00:00Z",
        });
        fs::write(
            track_dir.join("gateway-artifact.json"),
            serde_json::to_vec(&payload).expect("json serialization should work"),
        )
        .expect("must write artifact file");

        let err = resolve_gateway_binary_from_artifacts(&resource_dir).unwrap_err();
        assert!(err.contains("escapes track directory"));
    }

    fn create_temp_resource_dir(label: &str) -> PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be valid")
            .as_nanos();
        let root = std::env::temp_dir().join(format!("confluox-gateway-artifacts-{label}-{unique}"));
        fs::create_dir_all(root.join("gateway")).expect("must create resource dir");
        root
    }

    fn write_track(resource_dir: &Path, track: &str, entry: &str) {
        let track_dir = resource_dir.join("gateway").join(track);
        fs::create_dir_all(&track_dir).expect("must create track dir");

        let entry_path = track_dir.join(entry);
        if let Some(parent) = entry_path.parent() {
            fs::create_dir_all(parent).expect("must create entry parent");
        }
        fs::write(&entry_path, b"fake-binary").expect("must write fake binary");

        let payload = json!({
            "track": track,
            "platform": "darwin-arm64",
            "entry": entry,
            "resources_dir": ".",
            "version": "0.1.0",
            "built_at": "2026-03-17T00:00:00Z",
        });
        fs::write(
            track_dir.join("gateway-artifact.json"),
            serde_json::to_vec(&payload).expect("json serialization should work"),
        )
        .expect("must write artifact file");
    }
}

use serde::Serialize;
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum GatewayDiagnosticEventKind {
    Stdout,
    Stderr,
    StartupStatus,
    Shutdown,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GatewayDiagnosticEvent {
    pub kind: GatewayDiagnosticEventKind,
    pub message: String,
}

#[derive(Clone, Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GatewayDiagnosticsSnapshot {
    pub healthy: bool,
    pub startup_error_summary: Option<String>,
    pub events: Vec<GatewayDiagnosticEvent>,
}

pub struct GatewayDiagnostics {
    max_lines: usize,
    max_bytes: usize,
    total_bytes: usize,
    healthy: bool,
    startup_error_summary: Option<String>,
    events: VecDeque<GatewayDiagnosticEvent>,
}

impl GatewayDiagnostics {
    pub fn new(max_lines: usize, max_bytes: usize) -> Self {
        Self {
            max_lines: max_lines.max(1),
            max_bytes: max_bytes.max(1),
            total_bytes: 0,
            healthy: false,
            startup_error_summary: None,
            events: VecDeque::new(),
        }
    }

    pub fn append_stdout(&mut self, line: impl Into<String>) {
        self.append_event(GatewayDiagnosticEventKind::Stdout, line.into());
    }

    pub fn append_stderr(&mut self, line: impl Into<String>) {
        self.append_event(GatewayDiagnosticEventKind::Stderr, line.into());
    }

    pub fn append_startup_status(&mut self, healthy: bool, summary: Option<String>) {
        self.healthy = healthy;
        self.startup_error_summary = if healthy {
            None
        } else {
            summary
                .clone()
                .or_else(|| Some("gateway reported startup error".to_string()))
        };

        let message = if healthy {
            "gateway startup ready".to_string()
        } else {
            self.startup_error_summary
                .clone()
                .unwrap_or_else(|| "gateway reported startup error".to_string())
        };
        self.append_event(GatewayDiagnosticEventKind::StartupStatus, message);
    }

    pub fn append_shutdown(&mut self, message: impl Into<String>) {
        self.healthy = false;
        self.append_event(GatewayDiagnosticEventKind::Shutdown, message.into());
    }

    pub fn snapshot(&self) -> GatewayDiagnosticsSnapshot {
        GatewayDiagnosticsSnapshot {
            healthy: self.healthy,
            startup_error_summary: self.startup_error_summary.clone(),
            events: self.events.iter().cloned().collect(),
        }
    }

    fn append_event(&mut self, kind: GatewayDiagnosticEventKind, message: String) {
        self.total_bytes += message.len();
        self.events.push_back(GatewayDiagnosticEvent { kind, message });
        self.trim_to_capacity();
    }

    fn trim_to_capacity(&mut self) {
        while self.events.len() > self.max_lines
            || (self.total_bytes > self.max_bytes && self.events.len() > 1)
        {
            if let Some(removed) = self.events.pop_front() {
                self.total_bytes = self.total_bytes.saturating_sub(removed.message.len());
            } else {
                break;
            }
        }
    }
}

impl Default for GatewayDiagnostics {
    fn default() -> Self {
        Self::new(256, 64 * 1024)
    }
}

pub type SharedGatewayDiagnostics = Arc<Mutex<GatewayDiagnostics>>;

pub fn new_shared_gateway_diagnostics(max_lines: usize, max_bytes: usize) -> SharedGatewayDiagnostics {
    Arc::new(Mutex::new(GatewayDiagnostics::new(max_lines, max_bytes)))
}

pub fn snapshot_from_shared(state: &SharedGatewayDiagnostics) -> GatewayDiagnosticsSnapshot {
    match state.lock() {
        Ok(guard) => guard.snapshot(),
        Err(_) => GatewayDiagnosticsSnapshot {
            healthy: false,
            startup_error_summary: Some("gateway diagnostics lock poisoned".to_string()),
            events: Vec::new(),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn collect_messages(snapshot: &GatewayDiagnosticsSnapshot) -> Vec<String> {
        snapshot.events.iter().map(|event| event.message.clone()).collect()
    }

    #[test]
    fn appends_stdout_and_stderr_events() {
        let mut diagnostics = GatewayDiagnostics::new(16, 1024);
        diagnostics.append_stdout("gateway started");
        diagnostics.append_stderr("plugin import failed");

        let snapshot = diagnostics.snapshot();
        assert_eq!(snapshot.events.len(), 2);
        assert_eq!(snapshot.events[0].kind, GatewayDiagnosticEventKind::Stdout);
        assert_eq!(snapshot.events[0].message, "gateway started");
        assert_eq!(snapshot.events[1].kind, GatewayDiagnosticEventKind::Stderr);
        assert_eq!(snapshot.events[1].message, "plugin import failed");
    }

    #[test]
    fn retains_event_order_across_event_kinds() {
        let mut diagnostics = GatewayDiagnostics::new(16, 1024);
        diagnostics.append_startup_status(true, None);
        diagnostics.append_stdout("listening");
        diagnostics.append_stderr("warning");
        diagnostics.append_shutdown("host closed");

        let snapshot = diagnostics.snapshot();
        let kinds: Vec<GatewayDiagnosticEventKind> =
            snapshot.events.iter().map(|event| event.kind.clone()).collect();
        assert_eq!(
            kinds,
            vec![
                GatewayDiagnosticEventKind::StartupStatus,
                GatewayDiagnosticEventKind::Stdout,
                GatewayDiagnosticEventKind::Stderr,
                GatewayDiagnosticEventKind::Shutdown,
            ]
        );
        assert!(!snapshot.healthy);
    }

    #[test]
    fn trims_old_entries_when_line_cap_is_exceeded() {
        let mut diagnostics = GatewayDiagnostics::new(3, 4096);
        diagnostics.append_stdout("line-1");
        diagnostics.append_stdout("line-2");
        diagnostics.append_stdout("line-3");
        diagnostics.append_stdout("line-4");

        let snapshot = diagnostics.snapshot();
        assert_eq!(collect_messages(&snapshot), vec!["line-2", "line-3", "line-4"]);
    }

    #[test]
    fn trims_old_entries_when_byte_cap_is_exceeded() {
        let mut diagnostics = GatewayDiagnostics::new(8, 12);
        diagnostics.append_stdout("12345");
        diagnostics.append_stdout("67890");
        diagnostics.append_stdout("ab");
        diagnostics.append_stdout("XYZ");

        let snapshot = diagnostics.snapshot();
        assert_eq!(collect_messages(&snapshot), vec!["67890", "ab", "XYZ"]);
    }
}

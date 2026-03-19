# Quick Start

## What You Are Running

In development, Confluox runs three parts together:

- a Vite frontend on `http://localhost:1420`
- a Tauri desktop host
- a Python gateway process started by the desktop host

The desktop host starts the gateway, waits for a structured ready file, then exposes the gateway URL and auth token to the frontend.

## Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer
- Rust toolchain
- Tauri CLI

## Install Dependencies

### Python gateway

```bash
python -m pip install -U pip
python -m pip install -e 'gateway[dev]'
```

### Frontend

```bash
cd frontend
npm ci
```

### Tauri CLI

```bash
cargo install tauri-cli --version "^2" --locked
```

## Run In Development

Start the frontend first:

```bash
cd frontend
npm run dev
```

Then start the desktop app:

```bash
cargo tauri dev
```

If everything is working, the desktop window should show:

- gateway base URL
- gateway health status
- example plugin response

## Gateway Token Lifecycle

- The desktop host now issues scoped short-lived gateway tokens (`scope: gateway-api`).
- The frontend automatically refreshes the token once when it receives `401` with `auth_token_expired`.
- Token refresh is local-only and handled through a Tauri command (`refresh_gateway_auth_token`).

## Diagnostics Redaction

- Gateway diagnostics returned to the frontend are redacted by default.
- Bearer-like values and auth header values are masked as `[REDACTED]`.
- Non-sensitive log lines are preserved unchanged.

## How Development Mode Works

- the frontend is served by Vite on port `1420`
- Tauri connects to that development URL
- the Rust host starts `python -m gateway.main`
- the Python gateway binds a random localhost port
- the gateway writes a ready file with the chosen port
- Rust reads the ready file and gives the frontend the final connection info

## Build Gateway Artifacts

For production packaging, build the gateway artifacts first:

```bash
cd gateway
./scripts/build_gateway.sh --track all
```

This script prepares `dist/gateway` with the packaged gateway layout used by Tauri bundle resources.

## Build The Desktop App

After the frontend build and gateway artifacts are ready:

```bash
cd frontend
npm run build
cd ..
cargo tauri build
```

## Related Guides

- [Plugin Guide](plugin-guide.md)
- [Integration Guide](integration-guide.md)
- [中文快速开始](../zh-CN/quick-start.md)

import {
  findNextSseFrameBoundary,
  parseSseFrame,
  type SseChunk,
} from './sse'

export type GatewayRuntimeConfig = {
  baseUrl: string
  token: string
}

export type GatewayDiagnostics = {
  healthy: boolean
  startupErrorSummary: string | null
  recentEventLines: string[]
}

export type PluginActivationStatus = {
  state: string
  error_code: string | null
  error_message: string | null
}

export type PluginActivationSnapshot = {
  plugins: Record<string, PluginActivationStatus>
}

export type GatewayStreamChunk = SseChunk

type TauriGatewayPayload = {
  baseUrl: string
  authToken: string
}

type TauriGatewayDiagnosticsPayload = {
  healthy: boolean
  startupErrorSummary: string | null
  recentEventLines: string[]
}

declare global {
  interface Window {
    __GATEWAY__?: GatewayRuntimeConfig
  }
}

let configPromise: Promise<GatewayRuntimeConfig> | null = null

async function resolveGatewayConfig(): Promise<GatewayRuntimeConfig> {
  if (window.__GATEWAY__) {
    return window.__GATEWAY__
  }

  if (configPromise) {
    return configPromise
  }

  configPromise = (async () => {
    const { invoke } = await import('@tauri-apps/api/core')
    const payload = await invoke<TauriGatewayPayload>('get_gateway_info')
    const config: GatewayRuntimeConfig = {
      baseUrl: payload.baseUrl,
      token: payload.authToken,
    }
    window.__GATEWAY__ = config
    return config
  })()

  return configPromise
}

async function request<T>(
  method: 'GET' | 'POST',
  path: string,
  body?: unknown,
): Promise<T> {
  const config = await resolveGatewayConfig()
  const response = await fetch(`${config.baseUrl}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.token}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`${method} ${path} failed: ${response.status} ${text}`)
  }

  return (await response.json()) as T
}

export async function getGatewayConfig(): Promise<GatewayRuntimeConfig> {
  return resolveGatewayConfig()
}

export async function getGatewayDiagnostics(): Promise<GatewayDiagnostics> {
  const { invoke } = await import('@tauri-apps/api/core')
  const payload = await invoke<TauriGatewayDiagnosticsPayload>('get_gateway_diagnostics')
  return {
    healthy: payload.healthy,
    startupErrorSummary: payload.startupErrorSummary,
    recentEventLines: payload.recentEventLines,
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>('GET', path)
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>('POST', path, body)
}

export async function getPluginActivationSnapshot(): Promise<PluginActivationSnapshot> {
  return request<PluginActivationSnapshot>('GET', '/api/system/plugin-activation')
}

export async function streamGatewaySse(
  path: string,
  onChunk: (chunk: GatewayStreamChunk) => void,
): Promise<void> {
  const config = await resolveGatewayConfig()
  const response = await fetch(`${config.baseUrl}${path}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${config.token}`,
      Accept: 'text/event-stream',
    },
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`GET ${path} failed: ${response.status} ${text}`)
  }

  if (!response.body) {
    throw new Error(`GET ${path} returned empty stream body`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''

  while (true) {
    const { value, done } = await reader.read()
    pending += decoder.decode(value ?? new Uint8Array(), { stream: !done })

    let boundary = findNextSseFrameBoundary(pending)
    while (boundary !== null) {
      const frame = pending.slice(0, boundary.index)
      pending = pending.slice(boundary.index + boundary.delimiterLength)
      const parsed = parseSseFrame(frame)
      if (parsed) {
        onChunk(parsed)
      }
      boundary = findNextSseFrameBoundary(pending)
    }

    if (done) {
      break
    }
  }

  if (pending.trim()) {
    const parsed = parseSseFrame(pending)
    if (parsed) {
      onChunk(parsed)
    }
  }
}

export async function startSystemStreamDemo(
  onData: (chunk: string, event: string) => void,
): Promise<void> {
  return streamGatewaySse('/api/system/stream-demo', ({ event, data }) => {
    onData(data, event)
  })
}

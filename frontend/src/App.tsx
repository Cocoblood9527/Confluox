import { useEffect, useState } from 'react'
import {
  apiGet,
  getGatewayConfig,
  getGatewayDiagnostics,
  getPluginActivationSnapshot,
  startSystemStreamDemo,
  type GatewayDiagnostics,
  type GatewayRuntimeConfig,
  type PluginActivationSnapshot,
} from './api/client'
import './App.css'

type SystemHealth = {
  status: string
}

type ExampleResponse = {
  plugin: string
}

function App() {
  const [gatewayConfig, setGatewayConfig] = useState<GatewayRuntimeConfig | null>(null)
  const [diagnostics, setDiagnostics] = useState<GatewayDiagnostics | null>(null)
  const [pluginActivation, setPluginActivation] = useState<PluginActivationSnapshot | null>(null)
  const [health, setHealth] = useState<string>('loading')
  const [examplePlugin, setExamplePlugin] = useState<string>('loading')
  const [error, setError] = useState<string | null>(null)
  const [streamOutput, setStreamOutput] = useState<string>('')

  useEffect(() => {
    let active = true

    async function loadStatus() {
      try {
        const config = await getGatewayConfig()
        const diagnosticsResult = await getGatewayDiagnostics()
        const pluginActivationResult = await getPluginActivationSnapshot()
        const healthResult = await apiGet<SystemHealth>('/api/system/health')
        const exampleResult = await apiGet<ExampleResponse>('/api/example')

        if (!active) {
          return
        }

        setGatewayConfig(config)
        setDiagnostics(diagnosticsResult)
        setPluginActivation(pluginActivationResult)
        setHealth(healthResult.status)
        setExamplePlugin(exampleResult.plugin)
      } catch (err) {
        if (!active) {
          return
        }
        const message = err instanceof Error ? err.message : String(err)
        setError(message)
        const diagnosticsResult = await getGatewayDiagnostics().catch(() => null)
        if (diagnosticsResult) {
          setDiagnostics(diagnosticsResult)
        }
        const pluginActivationResult = await getPluginActivationSnapshot().catch(() => null)
        if (pluginActivationResult) {
          setPluginActivation(pluginActivationResult)
        }
      }
    }

    loadStatus()
    return () => {
      active = false
    }
  }, [])

  const shouldShowDiagnostics =
    !!error ||
    (diagnostics !== null && !diagnostics.healthy) ||
    (health !== 'loading' && health !== 'ok') ||
    (pluginActivation !== null && Object.keys(pluginActivation.plugins).length > 0)

  async function handleStreamDemo() {
    setStreamOutput('')
    try {
      await startSystemStreamDemo((chunk, event) => {
        setStreamOutput((prev) => `${prev}${prev ? '\n' : ''}${event}: ${chunk}`)
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setStreamOutput((prev) => `${prev}${prev ? '\n' : ''}error: ${message}`)
    }
  }

  return (
    <>
      <section id="center">
        <div>
          <h1>Confluox Desktop Bridge</h1>
          <p>Gateway runtime status from the local sidecar process.</p>
          {gatewayConfig ? (
            <>
              <p>
                Base URL: <code>{gatewayConfig.baseUrl}</code>
              </p>
            </>
          ) : (
            <p>Gateway config: loading...</p>
          )}
          <p>
            Gateway health: <code>{health}</code>
          </p>
          <p>
            Example plugin: <code>{examplePlugin}</code>
          </p>
          {error ? (
            <p>
              Error: <code>{error}</code>
            </p>
          ) : null}
          {diagnostics && shouldShowDiagnostics ? (
            <div>
              <p>
                Diagnostics: <code>{diagnostics.startupErrorSummary ?? 'runtime unhealthy'}</code>
              </p>
              {diagnostics.recentEventLines.length > 0 ? (
                <p>
                  Recent logs:{' '}
                  <code>{diagnostics.recentEventLines.slice(-3).join(' | ')}</code>
                </p>
              ) : null}
              {pluginActivation !== null && Object.keys(pluginActivation.plugins).length > 0 ? (
                <p>
                  Plugin activation:{' '}
                  <code>
                    {Object.entries(pluginActivation.plugins)
                      .map(([pluginName, status]) =>
                        status.error_code
                          ? `${pluginName}=${status.state}(${status.error_code})`
                          : `${pluginName}=${status.state}`,
                      )
                      .join(' | ')}
                  </code>
                </p>
              ) : null}
            </div>
          ) : null}
          <button type="button" onClick={handleStreamDemo}>
            Start stream demo
          </button>
          <p>
            Stream output: <code>{streamOutput || 'idle'}</code>
          </p>
        </div>
      </section>
    </>
  )
}

export default App

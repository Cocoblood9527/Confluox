import { useEffect, useState } from 'react'
import { apiGet, getGatewayConfig, type GatewayRuntimeConfig } from './api/client'
import './App.css'

type SystemHealth = {
  status: string
}

type ExampleResponse = {
  plugin: string
}

function App() {
  const [gatewayConfig, setGatewayConfig] = useState<GatewayRuntimeConfig | null>(null)
  const [health, setHealth] = useState<string>('loading')
  const [examplePlugin, setExamplePlugin] = useState<string>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function loadStatus() {
      try {
        const config = await getGatewayConfig()
        const healthResult = await apiGet<SystemHealth>('/api/system/health')
        const exampleResult = await apiGet<ExampleResponse>('/api/example')

        if (!active) {
          return
        }

        setGatewayConfig(config)
        setHealth(healthResult.status)
        setExamplePlugin(exampleResult.plugin)
      } catch (err) {
        if (!active) {
          return
        }
        const message = err instanceof Error ? err.message : String(err)
        setError(message)
      }
    }

    loadStatus()
    return () => {
      active = false
    }
  }, [])

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
              <p>
                Auth Token: <code>{gatewayConfig.token}</code>
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
        </div>
      </section>
    </>
  )
}

export default App

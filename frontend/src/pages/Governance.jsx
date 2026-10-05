import { useEffect, useState } from 'react'
import { useData } from '../context/DataContext'
import { useSocket } from '../context/SocketContext'
import { api } from '../api/client'
import { Card, KpiRow, KpiCard, PageHeader, Button } from '../components/ui'
import { click as playClick } from '../utils/sound'

const TABS = ['PII Detection', 'Data Contracts', 'Streaming / Kafka', 'Audit Log', 'Jira / PagerDuty']

function PiiTab({ active }) {
  const [results, setResults] = useState(null)
  const [tokenizing, setTokenizing] = useState('')

  const scan = async () => {
    const { data } = await api.post('/governance/pii/scan', null, { params: { filename: active } })
    setResults(data)
  }

  const tokenize = async (column) => {
    await api.post('/governance/pii/tokenize', { column }, { params: { filename: active } })
    setTokenizing(column)
  }

  return (
    <Card>
      <p className="text-sm text-text-secondary mb-3">Regex pattern matching only — this is NOT a legal compliance determination.</p>
      <Button variant="primary" onClick={scan}>Scan for PII</Button>
      {results && (
        <div className="mt-4 space-y-2">
          {results.map((r) => (
            <div key={r.column} className="flex items-center justify-between border-b border-border pb-2 text-sm">
              <div>
                <b>{r.column}</b> — {r.pattern} ({r.match_count} matches, {r.match_pct}%)
                <div className="text-xs text-text-secondary">{r.sample_masked.join(', ')}</div>
              </div>
              <Button onClick={() => tokenize(r.column)} disabled={tokenizing === r.column}>
                {tokenizing === r.column ? 'Tokenized ✓' : 'SHA-256 tokenize'}
              </Button>
            </div>
          ))}
          {results.length === 0 && <p className="text-sm text-text-secondary">No PII-like patterns found.</p>}
        </div>
      )}
    </Card>
  )
}

function ContractsTab({ active }) {
  const [result, setResult] = useState(null)

  const validate = async () => {
    const form = new FormData()
    const { data } = await api.post('/governance/contracts/validate', form, { params: { filename: active, use_example: true } })
    setResult(data)
  }

  const statusColor = { PASS: 'good', WARN: 'warning', BLOCKED: 'critical' }

  return (
    <Card>
      <p className="text-sm text-text-secondary mb-3">Validates against the bundled example contract for the sample retail dataset.</p>
      <Button variant="primary" onClick={validate}>Validate against example contract</Button>
      {result && (
        <div className="mt-4">
          <div className="font-semibold mb-2" style={{ color: `var(--color-${statusColor[result.deployment_status]})` }}>
            Deployment status: {result.deployment_status}
          </div>
          {result.violations.length === 0 ? (
            <p className="text-sm text-good">No contract violations.</p>
          ) : (
            <div className="space-y-1 text-sm">
              {result.violations.map((v, i) => (
                <div key={i} className="border-b border-border pb-1">
                  <b>{v.column}</b> — {v.rule} ({v.severity}): {v.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

function StreamingTab() {
  const { subscribe, send } = useSocket()
  const [live, setLive] = useState(false)
  const [metrics, setMetrics] = useState(null)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    api.get('/streaming/status').then((r) => setStatus(r.data))
    return subscribe('stream_tick', (msg) => setMetrics(msg.metrics))
  }, [subscribe])

  const toggle = () => {
    if (live) send({ action: 'stop_stream' })
    else send({ action: 'start_stream' })
    setLive((l) => !l)
  }

  return (
    <Card>
      <p className="text-sm text-text-secondary mb-1">Real-time / streaming pipeline</p>
      {status && (
        <p className={`text-xs mb-4 px-3 py-2 rounded-lg ${status.available ? 'bg-good/10 text-good' : 'bg-warning/10 text-warning'}`}>
          {status.available ? `Kafka: ${status.reason}` : `Kafka unavailable: ${status.reason}`}
        </p>
      )}
      <Button variant="primary" onClick={toggle}>{live ? '■ Stop live stream' : '▶ Start live stream'}</Button>
      {live && <span className="ml-3 text-xs text-good inline-flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-good dqi-pulse" /> ticking every second…</span>}

      {metrics && (
        <>
          <p className="text-xs text-text-secondary mt-4">{metrics.status}</p>
          <KpiRow>
            <KpiCard label="Throughput (events/sec)" value={metrics.throughput_eps} decimals={2} />
            <KpiCard label="Valid events" value={metrics.valid_events} subStatus="good" />
            <KpiCard label="Malformed" value={metrics.malformed_events} subStatus={metrics.malformed_events ? 'serious' : 'good'} />
            <KpiCard label="Schema violations" value={metrics.schema_violations} subStatus={metrics.schema_violations ? 'warning' : 'good'} />
            <KpiCard label="Quarantined" value={metrics.quarantined_events} />
          </KpiRow>
          <p className="text-xs text-text-secondary">Circuit breaker: malformed/invalid events are quarantined and never propagated downstream.</p>
        </>
      )}
    </Card>
  )
}

function AuditTab() {
  const [entries, setEntries] = useState([])
  useEffect(() => { api.get('/governance/audit-log').then((r) => setEntries(r.data)) }, [])
  return (
    <Card className="!p-0 overflow-hidden">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-text-secondary border-b border-border">
          {['Timestamp', 'Action', 'Dataset', 'Object', 'Result'].map((h) => <th key={h} className="py-2 px-3 font-semibold">{h}</th>)}
        </tr></thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={i} className="border-b border-border/60">
              <td className="py-2 px-3 text-xs text-text-secondary whitespace-nowrap">{new Date(e.timestamp).toLocaleString()}</td>
              <td className="py-2 px-3">{e.action}</td>
              <td className="py-2 px-3">{e.dataset}</td>
              <td className="py-2 px-3">{e.affected_object}</td>
              <td className="py-2 px-3 text-text-secondary">{e.result}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}

function IntegrationBadge({ name, info }) {
  if (!info) return null
  return (
    <div className="flex items-center justify-between px-3 py-2 rounded-lg border border-border bg-surface-raised text-sm">
      <span className="font-semibold capitalize">{name === 'pagerduty' ? 'PagerDuty' : 'Jira'}</span>
      {info.configured ? (
        <span className="text-good text-xs font-semibold">● Configured</span>
      ) : (
        <span className="text-warning text-xs font-semibold">
          ● Not configured — missing {info.missing.join(', ')}
        </span>
      )}
    </div>
  )
}

function ExternalTab() {
  const [summary, setSummary] = useState('DQI: critical data quality issue detected')
  const [msg, setMsg] = useState(null)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    api.get('/governance/integrations/status').then((r) => setStatus(r.data))
  }, [])

  const call = async (endpoint) => {
    const { data } = await api.post(endpoint, { summary })
    setMsg(data.message)
  }

  return (
    <Card>
      <p className="text-sm text-text-secondary mb-3">
        Never fakes success — without credentials configured, these return an honest "integration unavailable" result.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
        <IntegrationBadge name="jira" info={status?.jira} />
        <IntegrationBadge name="pagerduty" info={status?.pagerduty} />
      </div>
      {status && (!status.jira.configured || !status.pagerduty.configured) && (
        <p className="text-xs text-text-secondary mb-4">
          Add the missing variables to the <code>.env</code> file in the project root (copy from <code>.env.example</code>),
          then restart the backend.
        </p>
      )}
      <input value={summary} onChange={(e) => setSummary(e.target.value)}
             className="bg-surface border border-border rounded-lg px-3 py-2 text-sm w-full mb-3" />
      <div className="flex gap-3">
        <Button onClick={() => call('/governance/jira/create-ticket')}>Create Jira ticket</Button>
        <Button onClick={() => call('/governance/pagerduty/trigger')}>Trigger PagerDuty alert</Button>
      </div>
      {msg && <p className="text-sm mt-3 text-text-secondary">{msg}</p>}
    </Card>
  )
}

export default function Governance() {
  const { active } = useData()
  const [tab, setTab] = useState(0)

  if (!active) return <div className="text-text-secondary">Load a dataset on the Dashboard first.</div>

  return (
    <div>
      <PageHeader icon="🛡️" title={`Governance — ${active}`}
                  subtitle="PII detection, data contracts, streaming telemetry, and the audit trail." />
      <div className="flex gap-1 border-b border-border mb-5">
        {TABS.map((t, i) => (
          <button key={t} onClick={() => { playClick(); setTab(i) }}
                  className={`dqi-tappable px-4 py-2 text-sm font-semibold border-b-2 -mb-px transition ${
                    tab === i ? 'border-series-1 text-text' : 'border-transparent text-text-secondary hover:text-text'
                  }`}
                  style={tab === i ? { borderColor: 'var(--color-series-1)' } : undefined}>
            {t}
          </button>
        ))}
      </div>
      {tab === 0 && <PiiTab active={active} />}
      {tab === 1 && <ContractsTab active={active} />}
      {tab === 2 && <StreamingTab />}
      {tab === 3 && <AuditTab />}
      {tab === 4 && <ExternalTab />}
    </div>
  )
}

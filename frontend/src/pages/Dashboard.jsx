import { useCallback, useEffect, useRef, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend,
} from 'recharts'
import { motion, AnimatePresence } from 'framer-motion'
import { useData } from '../context/DataContext'
import { useSocket } from '../context/SocketContext'
import { getHealth, getIssues, getRanking } from '../api/results'
import { api } from '../api/client'
import { Card, KpiCard, KpiRow, PageHeader, Button, Badge } from '../components/ui'
import PipelineProgress from '../components/PipelineProgress'
import PipelineFlow from '../components/PipelineFlow'
import Terrain3D from '../components/Terrain3D'
import LiquidGauge from '../components/LiquidGauge'
import SafeBoundary from '../components/SafeBoundary'

/** Mounts the WebGL canvas only once the dashboard has settled, so view switches never race a render. */
function SettledTerrain(props) {
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setReady(true), 350)
    return () => { clearTimeout(t); setReady(false) }
  }, [])
  if (!ready) return <div className="w-full h-[420px] rounded-xl border border-border bg-surface-raised" />
  return <Terrain3D {...props} />
}

const STAGE_IDS = ['ingestion', 'profiling', 'issue_detection', 'quality_pillars', 'health_index', 'impact_scoring', 'ranking_stats']

const STATUS_STYLE = {
  queued: { icon: '○', color: 'var(--muted)' },
  uploading: { icon: '◐', color: 'var(--color-series-1)' },
  done: { icon: '✓', color: 'var(--color-good)' },
  error: { icon: '✕', color: 'var(--color-critical)' },
}

/** Per-file upload status. Rendered from DataContext, so it stays visible while the pipeline view runs. */
function UploadQueue({ queue, onClear }) {
  if (queue.length === 0) return null
  const done = queue.filter((i) => i.status === 'done').length
  const failed = queue.filter((i) => i.status === 'error').length
  const finished = done + failed === queue.length
  return (
    <Card className="mb-5">
      <div className="flex items-center justify-between mb-3">
        <div className="font-semibold text-sm">Upload queue · {done}/{queue.length} processed{failed ? ` · ${failed} failed` : ''}</div>
        {finished && <Button onClick={onClear}>Clear</Button>}
      </div>
      <ul className="space-y-1.5">
        <AnimatePresence initial={false}>
          {queue.map((item) => (
            <motion.li key={item.name} layout initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                       className="flex items-center justify-between text-sm px-3 py-2 rounded-lg bg-surface-raised border border-border">
              <span className="flex items-center gap-2 min-w-0">
                <span className={item.status === 'uploading' ? 'dqi-pulse' : ''} style={{ color: STATUS_STYLE[item.status].color }}>
                  {STATUS_STYLE[item.status].icon}
                </span>
                <span className="truncate">{item.name}</span>
              </span>
              <span className="text-xs text-text-secondary ml-3 truncate max-w-[45%]">{item.detail || item.status}</span>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
    </Card>
  )
}

function UploadPanel({ onUploadFiles, onSample, loading }) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = (fileList) => {
    const files = Array.from(fileList)
    if (!files.length) return
    onUploadFiles(files)
  }

  return (
    <Card>
      <motion.div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
        animate={{ scale: dragOver ? 1.015 : 1, borderColor: dragOver ? 'var(--color-series-1)' : 'var(--border)' }}
        className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer bg-surface-raised"
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" multiple accept=".csv,.parquet,.xlsx,.xls" className="hidden"
               onChange={(e) => handleFiles(e.target.files)} />
        <motion.div animate={{ y: dragOver ? -4 : [0, -3, 0] }} transition={{ repeat: dragOver ? 0 : Infinity, duration: 2.2 }}
                    className="text-3xl mb-2">⬆️</motion.div>
        <div className="font-semibold">Drop one or many CSV, Parquet or Excel files, or click to browse</div>
        <div className="text-xs text-text-secondary mt-1">Files are processed in order; the last one becomes active.</div>
      </motion.div>

      <div className="flex items-center gap-3 mt-4">
        <div className="h-px bg-border flex-1" />
        <span className="text-xs text-text-secondary">or</span>
        <div className="h-px bg-border flex-1" />
      </div>
      <Button variant="primary" className="w-full mt-4" disabled={loading} onClick={onSample}>
        {loading ? 'Working…' : 'Load sample retail dataset'}
      </Button>
    </Card>
  )
}

/** Drift timeline: health of one dataset across every upload / remediation commit in this session. */
function DriftTimeline({ filename, refreshKey }) {
  const [snaps, setSnaps] = useState(null)
  useEffect(() => {
    if (!filename) return
    api.get('/datasets/history', { params: { filename } }).then((r) => setSnaps(r.data.snapshots))
  }, [filename, refreshKey])

  if (!snaps) return null
  if (snaps.length < 2) {
    return (
      <p className="text-sm text-text-secondary">
        Drift timeline: upload this dataset again (or commit a remediation) to see how its health changes across uploads.
        {snaps.length === 1 && <> Recorded so far: 1 snapshot at health {snaps[0].health}.</>}
      </p>
    )
  }
  const data = snaps.map((s, i) => ({
    name: `#${i + 1}`, health: s.health, issues: s.issues, critical: s.critical,
    time: new Date(s.at).toLocaleTimeString(),
  }))
  const first = snaps[0].health
  const last = snaps[snaps.length - 1].health
  const delta = Math.round((last - first) * 100) / 100
  return (
    <div>
      <div className="flex gap-6 text-sm mb-3">
        <span>Snapshots: <b>{snaps.length}</b></span>
        <span>First: <b>{first}</b></span>
        <span>Latest: <b>{last}</b></span>
        <span style={{ color: delta < 0 ? 'var(--color-critical)' : delta > 0 ? 'var(--color-good)' : undefined }}>
          Drift: <b>{delta > 0 ? '+' : ''}{delta}</b>
        </span>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--gridline)" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
          <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }}
                   formatter={(v, k) => [v, k === 'health' ? 'Health' : k]}
                   labelFormatter={(l, p) => `Upload ${l} · ${p?.[0]?.payload?.time ?? ''} · ${p?.[0]?.payload?.issues ?? ''} issues`} />
          <Line type="monotone" dataKey="health" stroke="var(--color-series-1)" strokeWidth={2.5}
                dot={{ r: 4 }} isAnimationActive animationDuration={700} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function Dashboard() {
  const { datasets, active, activeSummary, loading, uploadFiles, loadSample, queue, clearQueue } = useData()
  const { subscribe, send } = useSocket()

  const [showUpload, setShowUpload] = useState(false)
  const [progress, setProgress] = useState({})
  const [pct, setPct] = useState(0)
  const [running, setRunning] = useState(false)
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    const un1 = subscribe('pipeline_progress', (msg) => {
      setRunning(true)
      setPct(msg.pct)
      setProgress((p) => ({ ...p, [msg.stage]: { status: msg.status, detail: msg.detail, label: msg.label } }))
    })
    const un2 = subscribe('pipeline_done', () => {
      setTimeout(() => setRunning(false), 500)
    })
    return () => { un1(); un2() }
  }, [subscribe])

  useEffect(() => {
    if (!active) { setDetail(null); return }
    let cancelled = false
    Promise.all([getHealth(active), getIssues(active), getRanking(active)]).then(([health, issues, ranking]) => {
      if (!cancelled) setDetail({ health, issues, ranking: ranking.ranking, corr: ranking.correlation })
    })
    return () => { cancelled = true }
  }, [active, running])

  const replay = useCallback(() => {
    if (!active) return
    setProgress({}); setPct(0); setRunning(true)
    send({ action: 'run_pipeline', filename: active })
  }, [active, send])

  if (datasets.length === 0 && !running) {
    return (
      <div className="max-w-xl mx-auto mt-10">
        <PageHeader icon="📊" title="Data Quality Intelligence"
                    subtitle="An impact-aware framework for assessing and prioritizing data quality issues." />
        <UploadPanel onUploadFiles={uploadFiles} onSample={loadSample} loading={loading} />
        <div className="mt-5"><UploadQueue queue={queue} onClear={clearQueue} /></div>
      </div>
    )
  }

  if (running) {
    return (
      <div className="max-w-3xl mx-auto mt-6">
        <PageHeader icon="⚡" title="Running the pipeline live" subtitle={active || 'Processing…'} />
        <UploadQueue queue={queue} onClear={clearQueue} />
        <Card>
          <PipelineFlow stageIds={STAGE_IDS} progress={progress} running={running} />
          <div className="mt-4">
            <PipelineProgress progress={progress} pct={pct} />
          </div>
        </Card>
      </div>
    )
  }

  if (!activeSummary || !detail) {
    return <div className="text-text-secondary">Loading dataset…</div>
  }

  const { health, issues, ranking, corr } = detail
  const topIssues = [...issues].sort((a, b) => (b.impact_score || 0) - (a.impact_score || 0)).slice(0, 8)
  const rankCompare = ranking.slice(0, 10).map((r) => ({
    name: `${r.issue_type} · ${r.column}`, Frequency: r.frequency_rank, Impact: r.impact_rank,
  }))

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <PageHeader icon="🧭" title={`Dashboard — ${activeSummary.filename}`} />
        <div className="flex gap-2">
          <Button onClick={() => setShowUpload((s) => !s)}>{showUpload ? 'Hide upload' : '+ Add datasets'}</Button>
          <Button onClick={replay}>↻ Replay live pipeline</Button>
        </div>
      </div>

      <UploadQueue queue={queue} onClear={clearQueue} />

      <AnimatePresence>
        {showUpload && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }} className="overflow-hidden mb-5">
            <UploadPanel onUploadFiles={uploadFiles} onSample={loadSample} loading={loading} />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-5">
        <Card className="flex items-center justify-center">
          <LiquidGauge value={activeSummary.health} band={activeSummary.band} label="Dataset Health" />
        </Card>
        <div className="xl:col-span-2">
          <KpiRow>
            <KpiCard label="Quality Issues" value={activeSummary.issue_count} />
            <KpiCard label="Critical Issues" value={activeSummary.critical_count}
                     sub={activeSummary.critical_count ? 'needs action' : 'none'}
                     subStatus={activeSummary.critical_count ? 'critical' : 'good'} />
            <KpiCard label="Top Impact Score" value={activeSummary.top_impact_score} decimals={1} />
            <KpiCard label="Rows Analyzed" value={activeSummary.rows} />
            <KpiCard label="Remediation" value={activeSummary.remediated ? 'Applied' : 'Not yet run'} animate={false}
                     subStatus={activeSummary.remediated ? 'good' : 'warning'} />
          </KpiRow>
          <Card title="Top critical issues (by impact score)">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2 max-h-56 overflow-y-auto">
              {topIssues.map((i) => (
                <div key={i.issue_id} className="flex items-center justify-between text-sm border-b border-border pb-2">
                  <div className="min-w-0">
                    <div className="font-medium truncate">{i.issue_type} <span className="text-text-secondary">· {i.column}</span></div>
                    <div className="text-xs text-text-secondary">{i.affected_records.toLocaleString()} records</div>
                  </div>
                  <Badge label={`${i.impact_score}`} status={i.severity >= 4 ? 'critical' : i.severity === 3 ? 'warning' : 'good'} />
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <Card title="Health terrain — each pillar is a hill; issues float above their pillar" className="mb-5">
        <SafeBoundary resetKey={active}>
          <SettledTerrain pillarScores={health.pillar_scores} issues={issues} />
        </SafeBoundary>
      </Card>

      <Card title="Drift timeline — health across uploads" className="mb-5">
        <DriftTimeline filename={active} refreshKey={`${running}-${activeSummary.updated_at}`} />
      </Card>

      <Card title="Impact-aware vs frequency-based priority">
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={rankCompare} margin={{ top: 10, right: 10, left: 0, bottom: 60 }}>
            <CartesianGrid stroke="var(--gridline)" vertical={false} />
            <XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} height={80}
                   tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} />
            <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8 }} />
            <Legend />
            <Bar dataKey="Frequency" fill="var(--color-series-1)" radius={[3, 3, 0, 0]} isAnimationActive animationDuration={600} />
            <Bar dataKey="Impact" fill="var(--color-series-2)" radius={[3, 3, 0, 0]} isAnimationActive animationDuration={600} />
          </BarChart>
        </ResponsiveContainer>
        <div className="text-sm text-text-secondary mt-2">
          Spearman rs = {corr.spearman_rs}, Kendall τ = {corr.kendall_tau} — see Impact Analysis for the full breakdown.
        </div>
      </Card>
    </div>
  )
}

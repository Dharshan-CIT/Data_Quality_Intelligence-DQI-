import { useEffect, useRef, useState } from 'react'
import { useData } from '../context/DataContext'
import { api } from '../api/client'
import { Card, PageHeader, Button } from '../components/ui'
import { click as playClick } from '../utils/sound'

const SUGGESTIONS = [
  'Why is this dataset unhealthy?',
  'What is the highest-impact issue?',
  'Which column needs attention first?',
  'What remediation would you recommend?',
]

async function download(endpoint, filename) {
  const res = await api.post(endpoint, null, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([res.data]))
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click(); a.remove()
  window.URL.revokeObjectURL(url)
}

export default function Reports() {
  const { active } = useData()
  const [tab, setTab] = useState('report')
  const [summary, setSummary] = useState(null)
  const [llmAvailable, setLlmAvailable] = useState(false)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [asking, setAsking] = useState(false)
  const [sharing, setSharing] = useState(false)
  const [share, setShare] = useState(null)

  const createShare = async () => {
    setSharing(true)
    try {
      const { data } = await api.post('/reports/share', null, { params: { filename: active } })
      setShare({ path: data.path, url: `${window.location.origin}${data.path}` })
    } finally {
      setSharing(false)
    }
  }

  useEffect(() => {
    if (!active) return
    api.get('/reports/summary', { params: { filename: active } }).then((r) => setSummary(r.data))
  }, [active])

  useEffect(() => { api.get('/assistant/status').then((r) => setLlmAvailable(r.data.llm_available)) }, [])

  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)
  const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
  const speechSupported = !!SpeechRecognition

  const ask = async (q) => {
    setAsking(true); setQuestion(q); setAnswer(null)
    try {
      const { data } = await api.post('/assistant/ask', { question: q }, { params: { filename: active } })
      setAnswer(data.answer)
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel()
        window.speechSynthesis.speak(new SpeechSynthesisUtterance(data.answer))
      }
    } finally {
      setAsking(false)
    }
  }

  const toggleMic = () => {
    if (!SpeechRecognition) return
    if (listening) { recognitionRef.current?.stop(); return }
    const rec = new SpeechRecognition()
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.onresult = (e) => {
      const spoken = e.results[0][0].transcript
      setQuestion(spoken)
      ask(spoken)
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    recognitionRef.current = rec
    setListening(true)
    rec.start()
  }

  if (!active) return <div className="text-text-secondary">Load a dataset on the Dashboard first.</div>

  const base = active.replace(/\.[^.]+$/, '')

  return (
    <div>
      <PageHeader icon="📄" title={`Reports & Assistant — ${active}`} />
      <div className="flex gap-1 border-b border-border mb-5">
        {['report', 'assistant'].map((t) => (
          <button key={t} onClick={() => { playClick(); setTab(t) }}
                  className={`dqi-tappable px-4 py-2 text-sm font-semibold border-b-2 -mb-px capitalize ${tab === t ? 'text-text' : 'border-transparent text-text-secondary'}`}
                  style={tab === t ? { borderColor: 'var(--color-series-1)' } : undefined}>
            {t === 'report' ? 'Report Export' : 'Assistant'}
          </button>
        ))}
      </div>

      {tab === 'report' && (
        <Card>
          <p className="text-sm text-text-secondary mb-3">Every export (JSON/CSV/PDF) is built from the same report — the numbers always match.</p>
          {summary && (
            <pre className="text-xs bg-surface-raised rounded-lg p-3 overflow-x-auto mb-4">{JSON.stringify(summary, null, 2)}</pre>
          )}
          <div className="flex gap-3">
            <Button onClick={() => download('/reports/export/json', `${base}_report.json`)}>Export JSON</Button>
            <Button onClick={() => download('/reports/export/csv', `${base}_ranking.csv`)}>Export ranking CSV</Button>
            <Button onClick={() => download('/reports/export/pdf', `${base}_report.pdf`)}>Export PDF</Button>
          </div>

          <div className="mt-6 pt-5 border-t border-border">
            <div className="font-semibold mb-1">Shareable link</div>
            <p className="text-sm text-text-secondary mb-3">
              Freezes this report as a read-only snapshot. Anyone with the link can view it; it does not update when the dataset changes.
            </p>
            <Button variant="primary" disabled={sharing} onClick={createShare}>
              {sharing ? 'Creating…' : 'Create read-only link'}
            </Button>
            {share && (
              <div className="flex items-center gap-2 mt-3 dqi-fade-in">
                <input readOnly value={share.url} onFocus={(e) => e.target.select()}
                       className="bg-surface border border-border rounded-lg px-3 py-2 text-sm flex-1 font-mono" />
                <Button onClick={() => navigator.clipboard?.writeText(share.url)}>Copy</Button>
                <a href={share.path} target="_blank" rel="noreferrer"
                   className="px-4 py-2 rounded-lg text-sm font-semibold border border-border bg-surface hover:bg-surface-raised">Open</a>
              </div>
            )}
          </div>
        </Card>
      )}

      {tab === 'assistant' && (
        <Card>
          <p className="text-sm text-text-secondary mb-4">
            {llmAvailable
              ? 'An LLM could be wired in here; this build answers deterministically from computed results either way.'
              : 'Deterministic local assistant — answers come only from already-computed results for this dataset, never invented.'}
          </p>
          <div className="flex flex-wrap gap-2 mb-4">
            {SUGGESTIONS.map((s) => <Button key={s} onClick={() => ask(s)}>{s}</Button>)}
          </div>
          <div className="flex gap-2">
            <input value={question} onChange={(e) => setQuestion(e.target.value)}
                   onKeyDown={(e) => e.key === 'Enter' && ask(question)}
                   placeholder="Ask a question about this dataset…"
                   className="bg-surface border border-border rounded-lg px-3 py-2 text-sm flex-1" />
            <Button onClick={toggleMic} className={listening ? 'ring-2 ring-critical' : ''} disabled={!speechSupported}>
              {listening ? '● Listening…' : '🎙 Speak'}
            </Button>
            <Button variant="primary" onClick={() => ask(question)} disabled={asking}>Ask</Button>
          </div>
          {asking && <p className="text-sm text-text-secondary mt-3">Thinking…</p>}
          {answer && <p className="text-sm mt-4 bg-surface-raised rounded-lg p-3 dqi-fade-in"><b>Answer:</b> {answer}</p>}
        </Card>
      )}
    </div>
  )
}

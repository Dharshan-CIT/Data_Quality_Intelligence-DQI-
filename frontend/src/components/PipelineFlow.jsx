import { useEffect, useRef } from 'react'

const SHORT = ['Ingest', 'Profile', 'Detect', 'Pillars', 'Health', 'Impact', 'Rank']

/** Particles stream left→right; a node glows once its stage is done. */
export default function PipelineFlow({ stageIds, progress, running }) {
  const canvasRef = useRef(null)
  const stateRef = useRef({ particles: [], doneSet: new Set(), running })

  useEffect(() => {
    stateRef.current.doneSet = new Set(stageIds.filter((id) => progress[id]?.status === 'done'))
    stateRef.current.running = running
  }, [progress, running, stageIds])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    const W = canvas.clientWidth
    const H = canvas.clientHeight
    canvas.width = W * dpr
    canvas.height = H * dpr
    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    const n = stageIds.length
    const pad = 36
    const xFor = (i) => pad + (i * (W - pad * 2)) / (n - 1)
    const yMid = H / 2
    let raf
    let last = performance.now()
    let spawnAcc = 0

    function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      const st = stateRef.current

      if (st.running) {
        spawnAcc += dt * 14
        while (spawnAcc >= 1) {
          spawnAcc -= 1
          st.particles.push({ x: pad - 10, lane: (Math.random() - 0.5) * 16, speed: 90 + Math.random() * 70, hue: Math.random() < 0.5 ? 210 : 150 })
        }
      }
      st.particles = st.particles.filter((p) => p.x < W + 20)
      st.particles.forEach((p) => {
        // only move past a node once its stage has finished; otherwise bunch up behind it
        const nextIdx = Math.floor(((p.x - pad) / (W - pad * 2)) * (n - 1)) + 1
        const cap = nextIdx < n && !st.doneSet.has(stageIds[nextIdx]) ? xFor(nextIdx) - 14 : Infinity
        p.x = Math.min(cap, p.x + p.speed * dt)
      })

      ctx.clearRect(0, 0, W, H)
      // base track
      ctx.strokeStyle = 'rgba(127,127,127,0.25)'
      ctx.lineWidth = 3
      ctx.beginPath(); ctx.moveTo(pad, yMid); ctx.lineTo(W - pad, yMid); ctx.stroke()

      // completed segments glow
      ctx.strokeStyle = '#2a78d6'
      ctx.lineWidth = 3
      for (let i = 0; i < n - 1; i++) {
        if (st.doneSet.has(stageIds[i])) {
          ctx.beginPath(); ctx.moveTo(xFor(i), yMid); ctx.lineTo(xFor(i + 1), yMid); ctx.stroke()
        }
      }

      // particles
      st.particles.forEach((p) => {
        ctx.fillStyle = `hsla(${p.hue}, 80%, 55%, 0.85)`
        ctx.beginPath()
        ctx.arc(p.x, yMid + p.lane, 2.4, 0, Math.PI * 2)
        ctx.fill()
      })

      // nodes
      ctx.font = '11px system-ui, sans-serif'
      ctx.textAlign = 'center'
      stageIds.forEach((id, i) => {
        const done = st.doneSet.has(id)
        const x = xFor(i)
        if (done) {
          const pulse = 6 + Math.sin(now / 300 + i) * 1.5
          ctx.fillStyle = 'rgba(42,120,214,0.25)'
          ctx.beginPath(); ctx.arc(x, yMid, pulse + 6, 0, Math.PI * 2); ctx.fill()
        }
        ctx.fillStyle = done ? '#2a78d6' : 'rgba(127,127,127,0.5)'
        ctx.beginPath(); ctx.arc(x, yMid, 7, 0, Math.PI * 2); ctx.fill()
        ctx.fillStyle = done ? 'rgba(127,127,127,0.95)' : 'rgba(127,127,127,0.55)'
        ctx.fillText(SHORT[i] || id, x, yMid + 26)
      })

      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(raf)
  }, [stageIds])

  return <canvas ref={canvasRef} className="w-full h-[110px] block" />
}

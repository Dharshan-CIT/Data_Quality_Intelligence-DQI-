import { useEffect, useRef, useState } from 'react'

const LABEL_W = 120
const ROW_H = 18

function cellColor(v) {
  // interpolate surface -> warning -> critical; zero stays near-transparent
  if (v <= 0) return 'rgba(127,127,127,0.08)'
  const t = Math.min(1, v * 4)
  const r = Math.round(250 * t + 210 * (1 - t))
  const g = Math.round(178 * t + 230 * (1 - t))
  const b = Math.round(25 * t + 240 * (1 - t))
  return `rgba(${r},${g},${b},${0.25 + 0.75 * t})`
}

export default function MissingHeatmap({ data, onCellClick, selected }) {
  const canvasRef = useRef(null)
  const wrapRef = useRef(null)
  const [hover, setHover] = useState(null)
  const [width, setWidth] = useState(600)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    if (!data || !canvasRef.current) return
    const canvas = canvasRef.current
    const dpr = window.devicePixelRatio || 1
    const cols = data.columns.length
    const cellW = Math.max(4, (width - LABEL_W) / data.bins)
    canvas.width = width * dpr
    canvas.height = (cols * ROW_H + 4) * dpr
    canvas.style.width = `${width}px`
    canvas.style.height = `${cols * ROW_H + 4}px`
    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, width, cols * ROW_H + 4)
    ctx.font = '11px system-ui, sans-serif'
    ctx.textBaseline = 'middle'
    data.columns.forEach((name, r) => {
      ctx.fillStyle = 'rgba(127,127,127,0.9)'
      ctx.fillText(name.length > 16 ? name.slice(0, 15) + '…' : name, 0, r * ROW_H + ROW_H / 2)
      data.matrix[r].forEach((v, c) => {
        ctx.fillStyle = cellColor(v)
        ctx.fillRect(LABEL_W + c * cellW, r * ROW_H + 1, cellW - 1, ROW_H - 2)
      })
    })
  }, [data, width])

  if (!data) return null
  const cols = data.columns.length
  const cellW = Math.max(4, (width - LABEL_W) / data.bins)

  const cellAt = (e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const c = Math.floor((x - LABEL_W) / cellW)
    const r = Math.floor((y - 2) / ROW_H)
    if (c < 0 || r < 0 || r >= cols || c >= data.bins) return null
    return { x, y, column: data.columns[r], bin: c, pct: (data.matrix[r][c] * 100).toFixed(1) }
  }

  const onMove = (e) => setHover(cellAt(e))
  const onClick = (e) => {
    const cell = cellAt(e)
    if (cell && onCellClick) onCellClick({ column: cell.column, bin: cell.bin })
  }

  return (
    <div ref={wrapRef} className="relative w-full overflow-x-auto">
      <canvas ref={canvasRef} onMouseMove={onMove} onMouseLeave={() => setHover(null)} onClick={onClick}
              className={`block ${onCellClick ? 'cursor-pointer' : ''}`} />
      {hover && (
        <div className="absolute pointer-events-none px-2 py-1 rounded-md text-xs bg-surface border border-border shadow"
             style={{ left: Math.min(hover.x + 12, width - 180), top: hover.y - 36 }}>
          <b>{hover.column}</b> · rows block {hover.bin + 1}/{data.bins}: {hover.pct}% missing
        </div>
      )}
      {selected && (
        <div className="absolute border-2 border-series-1 rounded-sm pointer-events-none"
             style={{
               left: LABEL_W + selected.bin * cellW - 1, top: selected.row * ROW_H,
               width: cellW + 1, height: ROW_H,
               borderColor: 'var(--color-series-1)',
             }} />
      )}
      <div className="text-[11px] text-text-secondary mt-1">
        Each column is a row of cells; each cell is a slice of the dataset (≈{Math.ceil(data.rows / data.bins).toLocaleString()} rows). Amber/red = more missing values.
        {onCellClick && <> Click a cell to inspect the rows behind it.</>}
      </div>
    </div>
  )
}

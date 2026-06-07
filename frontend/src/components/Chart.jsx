import { useState } from 'react'

// Dependency-free SVG line chart + sparkline. Each series: { color, points: [{ x?, y }] }.
// Points are plotted by index, so pass them pre-sorted chronologically.
// Pass `tip(i) => { label, rows: [[k, v]] }` to enable a hover crosshair + tooltip
// (e.g. to read off the date and values for each point directly on the chart).
export default function LineChart({ series, height = 240, format = (v) => v, fill = false, tip = null }) {
  const [hover, setHover] = useState(null) // { i, px } — px is cursor position in % of width
  const all = series.flatMap((s) => s.points)
  if (all.length === 0) return null

  const ys = all.map((p) => p.y).filter((v) => v != null)
  if (ys.length === 0) return null
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const pad = (maxY - minY) * 0.08 || Math.abs(maxY) * 0.1 || 1
  const lo = minY - pad
  const hi = maxY + pad

  const W = 880
  const H = height
  const padL = 60
  const padR = 16
  const padT = 14
  const padB = 22
  const x = (i, len) => padL + (len <= 1 ? 0 : (i / (len - 1)) * (W - padL - padR))
  const y = (v) => padT + (1 - (v - lo) / (hi - lo || 1)) * (H - padT - padB)

  // longest series drives the crosshair index mapping (all series share the index axis)
  const len = Math.max(...series.map((s) => s.points.length))

  const onMove = (e) => {
    if (!tip || len < 1) return
    const rect = e.currentTarget.getBoundingClientRect()
    const frac = ((e.clientX - rect.left) / rect.width - padL / W) / ((W - padL - padR) / W)
    let i = Math.round(frac * (len - 1))
    i = Math.max(0, Math.min(len - 1, i))
    setHover({ i, px: ((e.clientX - rect.left) / rect.width) * 100 })
  }

  const info = hover && tip ? tip(hover.i) : null
  const tipLeft = hover ? Math.min(Math.max(hover.px, 12), 80) : 0

  const svg = (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="chart"
      preserveAspectRatio="none"
      style={{ height }}
      onMouseMove={onMove}
      onMouseLeave={() => setHover(null)}
    >
      {[0, 0.25, 0.5, 0.75, 1].map((t) => {
        const gy = padT + t * (H - padT - padB)
        const val = hi - t * (hi - lo)
        return (
          <g key={t}>
            <line x1={padL} x2={W - padR} y1={gy} y2={gy} className="grid" />
            <text x={padL - 8} y={gy + 3} className="axis" textAnchor="end">
              {format(val)}
            </text>
          </g>
        )
      })}
      {series.map((s, si) => {
        const pts = s.points.filter((p) => p.y != null)
        const path = pts.map((p, i) => `${x(i, s.points.length)},${y(p.y)}`).join(' ')
        return (
          <g key={si}>
            {fill && (
              <polygon
                points={`${padL},${H - padB} ${path} ${x(s.points.length - 1, s.points.length)},${H - padB}`}
                fill={s.color}
                opacity="0.08"
              />
            )}
            <polyline className="line" style={{ stroke: s.color }} points={path} />
          </g>
        )
      })}
      {/* hover crosshair + a marker dot on each series */}
      {info && (
        <g>
          <line className="crosshair" x1={x(hover.i, len)} x2={x(hover.i, len)} y1={padT} y2={H - padB} />
          {series.map((s, si) => {
            const p = s.points[hover.i]
            return p && p.y != null
              ? <circle key={si} cx={x(hover.i, len)} cy={y(p.y)} r="3.2" fill={s.color} />
              : null
          })}
        </g>
      )}
    </svg>
  )

  if (!tip) return svg
  return (
    <div className="chart-wrap">
      {svg}
      {info && (
        <div className="chart-tip" style={{ left: tipLeft + '%', top: 6 }}>
          {info.label != null && <div className="tip-date">{info.label}</div>}
          {info.rows.map(([k, v]) => (
            <div className="tip-row" key={k}><span className="tk">{k}</span><span>{v}</span></div>
          ))}
        </div>
      )}
    </div>
  )
}

export function Sparkline({ values, color = 'var(--accent)', height = 34 }) {
  const ys = values.filter((v) => v != null)
  if (ys.length < 2) return null
  const lo = Math.min(...ys)
  const hi = Math.max(...ys)
  const W = 120
  const H = height
  const x = (i) => (i / (ys.length - 1)) * W
  const y = (v) => H - 2 - ((v - lo) / (hi - lo || 1)) * (H - 4)
  const path = ys.map((v, i) => `${x(i)},${y(v)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height }}>
      <polygon points={`0,${H} ${path} ${W},${H}`} fill={color} opacity="0.10" />
      <polyline points={path} fill="none" stroke={color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

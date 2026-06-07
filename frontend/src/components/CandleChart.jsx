import { useState, useRef } from 'react'
import { fmt, fmtCompact } from './ui.jsx'

// Candlestick + volume chart. `bars` are chronological (oldest first):
//   { date, open, high, low, close, volume }
// Pure SVG, dependency-free, with a crosshair + hover tooltip.
export default function CandleChart({ bars, height = 340 }) {
  const [hover, setHover] = useState(null)
  const wrapRef = useRef(null)

  const data = bars.filter((b) => b.close != null && b.high != null && b.low != null)
  if (data.length < 2) return null

  const W = 900
  const H = height
  const padL = 58
  const padR = 14
  const padT = 12
  const volH = 56
  const gap = 14
  const priceB = H - volH - gap
  const plotW = W - padL - padR

  const highs = data.map((b) => b.high)
  const lows = data.map((b) => b.low)
  let hi = Math.max(...highs)
  let lo = Math.min(...lows)
  const padY = (hi - lo) * 0.06 || hi * 0.05 || 1
  hi += padY
  lo -= padY

  const maxVol = Math.max(...data.map((b) => b.volume || 0)) || 1

  const n = data.length
  const step = plotW / n
  const cw = Math.max(1, Math.min(11, step * 0.62))

  const xCenter = (i) => padL + step * (i + 0.5)
  const yPrice = (v) => padT + (1 - (v - lo) / (hi - lo || 1)) * (priceB - padT)
  const yVol = (v) => priceB + gap + (1 - v / maxVol) * (volH)

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => lo + t * (hi - lo))

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const xRel = ((e.clientX - rect.left) / rect.width) * W
    let i = Math.floor((xRel - padL) / step)
    i = Math.max(0, Math.min(n - 1, i))
    setHover({ i, px: ((e.clientX - rect.left) / rect.width) * 100 })
  }

  const hb = hover != null ? data[hover.i] : null
  const tipLeft = hover ? Math.min(Math.max(hover.px, 12), 78) : 0

  return (
    <div className="chart-wrap" ref={wrapRef}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="chart"
        preserveAspectRatio="none"
        style={{ height }}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {/* price gridlines + axis */}
        {ticks.map((v, t) => {
          const gy = yPrice(v)
          return (
            <g key={t}>
              <line x1={padL} x2={W - padR} y1={gy} y2={gy} className="grid" />
              <text x={padL - 8} y={gy + 3} className="axis" textAnchor="end">
                {fmtCompact(v)}
              </text>
            </g>
          )
        })}

        {/* volume bars */}
        {data.map((b, i) => {
          const up = (b.close ?? 0) >= (b.open ?? 0)
          const vy = yVol(b.volume || 0)
          return (
            <rect
              key={'v' + i}
              x={xCenter(i) - cw / 2}
              y={vy}
              width={cw}
              height={Math.max(0, priceB + gap + volH - vy)}
              className={up ? 'vol-up' : 'vol-down'}
            />
          )
        })}

        {/* candles */}
        {data.map((b, i) => {
          const up = (b.close ?? 0) >= (b.open ?? 0)
          const x = xCenter(i)
          const yO = yPrice(b.open ?? b.close)
          const yC = yPrice(b.close)
          const bodyTop = Math.min(yO, yC)
          const bodyH = Math.max(1.2, Math.abs(yC - yO))
          return (
            <g key={'c' + i} className={up ? 'candle-up' : 'candle-down'}>
              <line x1={x} x2={x} y1={yPrice(b.high)} y2={yPrice(b.low)} strokeWidth="1" />
              <rect x={x - cw / 2} y={bodyTop} width={cw} height={bodyH} />
            </g>
          )
        })}

        {/* crosshair */}
        {hb && (
          <line
            className="crosshair"
            x1={xCenter(hover.i)}
            x2={xCenter(hover.i)}
            y1={padT}
            y2={priceB + gap + volH}
          />
        )}
      </svg>

      {hb && (
        <div className="chart-tip" style={{ left: tipLeft + '%', top: 6 }}>
          <div className="tip-date">{hb.date}</div>
          <Row k="O" v={hb.open} />
          <Row k="H" v={hb.high} />
          <Row k="L" v={hb.low} />
          <Row k="C" v={hb.close} strong />
          {hb.volume != null && (
            <div className="tip-row"><span className="tk">Vol</span><span>{fmtCompact(hb.volume)}</span></div>
          )}
        </div>
      )}
    </div>
  )
}

function Row({ k, v, strong }) {
  return (
    <div className="tip-row">
      <span className="tk">{k}</span>
      <span style={strong ? { color: 'var(--text)', fontWeight: 600 } : undefined}>{fmt(v)}</span>
    </div>
  )
}

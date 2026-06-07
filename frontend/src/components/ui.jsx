import { useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { Icon } from './icons.jsx'

// Reusable hover tooltip for table rows: shows full record details near the cursor.
// Rendered through a portal to <body> so its position:fixed is viewport-relative and
// not thrown off by any transformed/scrolled ancestor (e.g. the animated .view-inner).
// Usage:
//   const tip = useTooltip()
//   <tr {...tip.rowProps('2024-01-03', [['open', 45003], ['close', 42869]])}>…</tr>
//   {tip.element}
export function useTooltip() {
  const [tip, setTip] = useState(null) // { title, rows: [[k,v]], x, y }
  const rowProps = useCallback((title, rows) => ({
    onMouseEnter: (e) => setTip({ title, rows, x: e.clientX, y: e.clientY }),
    onMouseMove: (e) => setTip((t) => (t ? { ...t, x: e.clientX, y: e.clientY } : t)),
    onMouseLeave: () => setTip(null),
  }), [])

  let element = null
  if (tip && typeof document !== 'undefined') {
    const vw = window.innerWidth
    const vh = window.innerHeight
    // flip to the left / above the cursor near the right / bottom edges
    const left = tip.x + 16 + 260 > vw ? Math.max(8, tip.x - 276) : tip.x + 16
    const top = tip.y + 16 + 180 > vh ? Math.max(8, tip.y - 196) : tip.y + 16
    element = createPortal(
      <div className="data-tip" style={{ left, top }}>
        {tip.title != null && <div className="data-tip-title">{tip.title}</div>}
        {tip.rows.map(([k, v]) => (
          <div className="data-tip-row" key={k}><span>{k}</span><b>{v}</b></div>
        ))}
      </div>,
      document.body,
    )
  }
  return { rowProps, element }
}

export function Header({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="sub">{subtitle}</p>}
      </div>
      {children && <div className="header-actions">{children}</div>}
    </div>
  )
}

export function Panel({ title, eyebrow, actions, children, className = '' }) {
  return (
    <div className={'panel ' + className}>
      {(title || actions) && (
        <div className="panel-title">
          <div>
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            {title && <h3>{title}</h3>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }) {
  return (
    <div className="spinner">
      <span className="ring" /> {label}
    </div>
  )
}

export function Skeleton({ h = 14, w = '100%', style }) {
  return <div className="skeleton" style={{ height: h, width: w, ...style }} />
}

export function ErrorBox({ error }) {
  if (!error) return null
  return (
    <div className="error">
      <span>⚠</span>
      <span>{String(error.message || error)}</span>
    </div>
  )
}

export function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}

export function Empty({ children, icon = 'inbox' }) {
  const I = Icon[icon] || Icon.inbox
  return (
    <div className="empty">
      <span className="empty-ico"><I size={30} /></span>
      <span>{children}</span>
    </div>
  )
}

export function Badge({ kind = 'neutral', children }) {
  return <span className={'badge ' + kind}>{children}</span>
}

// number formatting
export function fmt(v, digits = 2) {
  if (v == null) return '—'
  if (typeof v !== 'number') return v
  return v.toLocaleString(undefined, { maximumFractionDigits: digits })
}

export function fmtCompact(v) {
  if (v == null || typeof v !== 'number') return v ?? '—'
  return v.toLocaleString(undefined, { notation: 'compact', maximumFractionDigits: 1 })
}

export function pct(v) {
  if (v == null) return '—'
  const s = v >= 0 ? '+' : ''
  return s + v.toFixed(2) + '%'
}

export function fmtDateTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch {
    return iso
  }
}

// classify an asset by its `class` attribute for badge styling
export function assetKind(attrs = {}) {
  const c = (attrs.class || '').toLowerCase()
  if (c.includes('crypto')) return 'crypto'
  if (c.includes('stock') || c.includes('equity')) return 'up'
  return 'neutral'
}

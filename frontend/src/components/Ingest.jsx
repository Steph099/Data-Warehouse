import { useState } from 'react'
import { api, daysAgo } from '../api.js'
import { useApp } from '../App.jsx'
import { Header, Panel, Spinner, ErrorBox, Field, Badge } from './ui.jsx'
import { Icon } from './icons.jsx'

export default function Ingest() {
  const app = useApp()
  const [form, setForm] = useState({
    symbols: 'BTCUSD ETHUSD',
    provider: 'bitfinex',
    start: daysAgo(90),
    end: '',
  })
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const run = (e) => {
    e.preventDefault()
    const symbols = form.symbols.split(/[\s,]+/).filter(Boolean)
    if (symbols.length === 0) return
    setLoading(true)
    setError(null)
    setStats(null)
    api
      .ingest({ symbols, provider: form.provider, start: form.start || null, end: form.end || null })
      .then(setStats)
      .catch(setError)
      .finally(() => setLoading(false))
  }

  return (
    <>
      <Header title="Ingest" subtitle="Pull live OHLCV history from an external provider. The ETL is idempotent and records full data provenance (UC1)." />

      <form className="toolbar" onSubmit={run}>
        <Field label="Symbols (space / comma separated)">
          <input value={form.symbols} onChange={set('symbols')} placeholder="BTCUSD ETHUSD" size={26} className="mono" />
        </Field>
        <Field label="Provider">
          <select value={form.provider} onChange={set('provider')}>
            <option value="bitfinex">Bitfinex (public)</option>
            <option value="nasdaq_data_link">Nasdaq Data Link (key)</option>
            <option value="both">Both (Bitfinex + Nasdaq)</option>
          </select>
        </Field>
        <Field label="Start">
          <input type="date" className="mono" value={form.start} onChange={set('start')} />
        </Field>
        <Field label="End (optional)">
          <input type="date" className="mono" value={form.end} onChange={set('end')} />
        </Field>
        <button className="btn primary" type="submit" disabled={loading}>
          <Icon.ingest size={14} /> {loading ? 'Ingesting…' : 'Run ingestion'}
        </button>
      </form>

      {loading && <Spinner label="Fetching from provider, transforming & loading…" />}
      <ErrorBox error={error} />

      {stats && stats.length === 0 && <Panel><div className="muted">No symbols processed.</div></Panel>}

      {stats && stats.map((s) => {
        const ok = s.failed === 0
        return (
          <Panel key={`${s.dataSourceId}/${s.symbol}`} className="stat-card">
            <div className="stat-head">
              <Badge kind="neutral">{s.symbol}</Badge>
              <Icon.arrowDown size={13} style={{ color: 'var(--muted)', transform: 'rotate(-90deg)' }} />
              <span className="chip click" onClick={() => app.goto('assets', { asset: s.assetId })}>{s.assetId}</span>
              <span className="muted small">via</span>
              <span className="chip click" onClick={() => app.goto('sources', { source: s.dataSourceId })}>{s.dataSourceId}</span>
              <div style={{ flex: 1 }} />
              <Badge kind={ok ? 'up' : 'down'}>{ok ? 'success' : `${s.failed} failed`}</Badge>
            </div>
            <div className="stat-grid">
              <Stat n={s.fetched} l="fetched" />
              <Stat n={s.transformed} l="transformed" />
              <Stat n={s.stored} l="stored" tone="good" />
              <Stat n={s.skipped} l="skipped" />
              <Stat n={s.failed} l="failed" tone={s.failed ? 'bad' : ''} />
            </div>
            <div className="attrs" style={{ marginTop: 4 }}>
              <span className="attrs-label">indicators discovered</span>
              {s.attributes.map((a) => <span key={a} className="chip"><Icon.hash size={11} /> {a}</span>)}
            </div>
            <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
              <button className="btn sm" onClick={() => app.goto('timeseries', { asset: s.assetId, source: s.dataSourceId })}>
                <Icon.series size={13} /> View time series
              </button>
            </div>
          </Panel>
        )
      })}
    </>
  )
}

function Stat({ n, l, tone = '' }) {
  return (
    <div className={'stat ' + tone}>
      <div className="stat-n">{n}</div>
      <div className="stat-l">{l}</div>
    </div>
  )
}

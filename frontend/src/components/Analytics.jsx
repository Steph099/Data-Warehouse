import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../App.jsx'
import { Header, Panel, Spinner, ErrorBox, Field, Empty, fmt, fmtCompact, pct } from './ui.jsx'
import { Icon } from './icons.jsx'
import LineChart from './Chart.jsx'

export default function Analytics() {
  const app = useApp()
  const [assets, setAssets] = useState([])
  const [sources, setSources] = useState([])
  const [sel, setSel] = useState({ assetId: app.asset || '', dataSourceId: app.source || '' })
  const [range, setRange] = useState({ from: '', to: '' }) // business-date filter for analytics + forecast
  const [totals, setTotals] = useState(null)
  const [preds, setPreds] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(null) // 'aggregation' | 'regression' | null
  const [jobMsg, setJobMsg] = useState(null)

  useEffect(() => {
    api.listAssets(0, 1000).then((a) => {
      setAssets(a)
      setSel((s) => ({ ...s, assetId: s.assetId || a[0] || '' }))
    }).catch(() => {})
    api.listDataSources(0, 1000).then((s) => {
      setSources(s)
      setSel((x) => ({ ...x, dataSourceId: x.dataSourceId || (s.includes('BITFINEX') ? 'BITFINEX' : s[0]) || '' }))
    }).catch(() => {})
  }, [])

  const load = () => {
    if (!sel.assetId || !sel.dataSourceId) return
    setLoading(true)
    setError(null)
    setTotals(null)
    setPreds(null)
    Promise.all([
      api.totals(sel.assetId, sel.dataSourceId),
      api.predictions(sel.assetId, sel.dataSourceId, 2000),
    ])
      .then(([t, p]) => { setTotals(t); setPreds(p) })
      .catch(setError)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (sel.assetId && sel.dataSourceId && totals == null && !loading) load()
  }, [sel.assetId, sel.dataSourceId]) // eslint-disable-line

  // Trigger a Spark job in the container, then reload the result tables.
  const runJob = (job) => {
    if (!sel.assetId || !sel.dataSourceId || running) return
    setRunning(job)
    setError(null)
    setJobMsg(null)
    api
      .runJob(job, sel.assetId, sel.dataSourceId)
      .then((r) => { setJobMsg(r.message); load() })
      .catch(setError)
      .finally(() => setRunning(null))
  }

  // ---- date-range filtering (applies to both the totals table and the forecast) ----
  const inRange = (iso) => (!range.from || iso >= range.from) && (!range.to || iso <= range.to)
  const yearInRange = (y) =>
    (!range.from || y >= +range.from.slice(0, 4)) && (!range.to || y <= +range.to.slice(0, 4))
  const fTotals = totals ? totals.filter((t) => yearInRange(t.year)) : null
  const fPreds = preds ? preds.filter((p) => inRange(p.businessDate)) : null

  // regression accuracy: mean abs % error (over the filtered window)
  const scored = fPreds ? fPreds.filter((p) => p.open && p.prediction) : []
  const mape = scored.length
    ? (scored.reduce((a, p) => a + Math.abs((p.prediction - p.open) / p.open), 0) / scored.length) * 100
    : null

  const predSeries = fPreds
    ? [
        { color: 'var(--muted)', points: fPreds.map((p) => ({ y: p.open })) },
        { color: 'var(--accent)', points: fPreds.map((p) => ({ y: p.prediction })) },
      ]
    : []

  const clearRange = () => setRange({ from: '', to: '' })

  return (
    <>
      <Header title="Analytics & Forecasting" subtitle="Spark aggregation (per-year totals) and an ML regression that predicts the daily open — computed in Spark, persisted back into the warehouse (UC3)." />

      <form className="toolbar" onSubmit={(e) => { e.preventDefault(); load() }}>
        <Field label="Asset">
          <select value={sel.assetId} onChange={(e) => setSel({ ...sel, assetId: e.target.value })}>
            {assets.map((a) => <option key={a}>{a}</option>)}
          </select>
        </Field>
        <Field label="Data source">
          <select value={sel.dataSourceId} onChange={(e) => setSel({ ...sel, dataSourceId: e.target.value })}>
            {sources.map((s) => <option key={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="From (incl)">
          <input type="date" className="mono" value={range.from} onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} />
        </Field>
        <Field label="To (incl)">
          <input type="date" className="mono" value={range.to} onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} />
        </Field>
        {(range.from || range.to) && (
          <button type="button" className="btn ghost sm" style={{ alignSelf: 'center' }} onClick={clearRange}>
            <Icon.refresh size={13} /> All dates
          </button>
        )}
        <button className="btn primary" type="submit"><Icon.refresh size={14} /> Load</button>
        <div style={{ flex: 1 }} />
        <button
          type="button" className="btn" disabled={!!running || !sel.assetId}
          onClick={() => runJob('aggregation')}
          title="Recompute the per-year totals in Spark"
        >
          <Icon.analytics size={14} /> {running === 'aggregation' ? 'Running…' : 'Run aggregation'}
        </button>
        <button
          type="button" className="btn" disabled={!!running || !sel.assetId}
          onClick={() => runJob('regression')}
          title="Retrain the ML regression for this asset in Spark"
        >
          <Icon.assistant size={14} /> {running === 'regression' ? 'Running…' : 'Run regression'}
        </button>
      </form>

      {running && <Spinner label={`Running Spark ${running} job in the container — this can take a minute…`} />}
      {jobMsg && !running && <div className="notice">✓ {jobMsg}</div>}
      {loading && !running && <Spinner label="Reading Spark outputs…" />}
      <ErrorBox error={error} />

      {fTotals && (
        <Panel eyebrow="Spark aggregation · totals table" title="Per-year close statistics">
          {fTotals.length === 0 ? (
            <Empty icon="analytics">
              {totals.length === 0 ? 'No aggregates yet.' : 'No aggregates in the selected date range.'}
              {totals.length === 0 && (
                <button className="btn sm" style={{ marginTop: 10 }} disabled={!!running} onClick={() => runJob('aggregation')}>
                  <Icon.analytics size={13} /> {running === 'aggregation' ? 'Running…' : 'Run aggregation job'}
                </button>
              )}
            </Empty>
          ) : (
            <>
              <div className="grid cols-4" style={{ marginBottom: 16 }}>
                <Mini label="Years covered" value={fTotals.length} />
                <Mini label="Data points" value={fmtCompact(fTotals.reduce((a, t) => a + t.count, 0))} />
                <Mini label="All-time low" value={fmtCompact(Math.min(...fTotals.map((t) => t.minClose)))} accent="down" />
                <Mini label="All-time high" value={fmtCompact(Math.max(...fTotals.map((t) => t.maxClose)))} accent="up" />
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>year</th><th className="num">count</th><th className="num">min close</th><th className="num">max close</th><th className="num">avg close</th><th className="num">range</th></tr>
                  </thead>
                  <tbody>
                    {fTotals.map((t) => {
                      const span = t.maxClose && t.minClose ? ((t.maxClose - t.minClose) / t.minClose) * 100 : null
                      return (
                        <tr key={t.year}>
                          <td className="mono">{t.year}</td>
                          <td className="num">{t.count}</td>
                          <td className="num">{fmt(t.minClose)}</td>
                          <td className="num">{fmt(t.maxClose)}</td>
                          <td className="num">{fmt(t.avgClose)}</td>
                          <td className="num up">{span == null ? '—' : pct(span)}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Panel>
      )}

      {fPreds && fPreds.length > 0 && (
        <Panel
          eyebrow="Spark ML · regression_results table"
          title="Predicted vs. actual daily open"
          actions={mape != null && <span className="chip">MAPE {mape.toFixed(2)}%</span>}
        >
          <LineChart
            series={predSeries}
            format={fmtCompact}
            tip={(i) => {
              const p = fPreds[i]
              const err = p.open && p.prediction ? ((p.prediction - p.open) / p.open) * 100 : null
              return {
                label: p.businessDate,
                rows: [
                  ['actual', fmt(p.open)],
                  ['predicted', fmt(p.prediction)],
                  ['error', err == null ? '—' : pct(err)],
                ],
              }
            }}
          />
          <div className="x-axis">
            <span>{fPreds[0].businessDate}</span>
            <span>{fPreds[fPreds.length - 1].businessDate}</span>
          </div>
          <div className="legend">
            <span className="lg"><i style={{ background: 'var(--muted)' }} /> actual open</span>
            <span className="lg"><i style={{ background: 'var(--accent)' }} /> predicted open</span>
            <span className="lg muted">{fPreds.length} test points{(range.from || range.to) ? ' in range' : ''}</span>
          </div>
        </Panel>
      )}

      {/* Forecast table — hover a row to see the full data point */}
      {fPreds && fPreds.length > 0 && (
        <Panel eyebrow="forecast records" title="Forecast table">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>business date</th>
                  <th className="num">actual open</th>
                  <th className="num">predicted open</th>
                  <th className="num">error</th>
                </tr>
              </thead>
              <tbody>
                {fPreds.map((p) => {
                  const err = p.open && p.prediction ? ((p.prediction - p.open) / p.open) * 100 : null
                  return (
                    <tr key={p.businessDate}>
                      <td className="mono">{p.businessDate}</td>
                      <td className="num">{fmt(p.open)}</td>
                      <td className="num">{fmt(p.prediction)}</td>
                      <td className={'num ' + (err == null ? '' : err >= 0 ? 'up' : 'down')}>
                        {err == null ? '—' : pct(err)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Panel>
      )}

      {preds && fPreds && fPreds.length === 0 && totals && totals.length > 0 && (
        <Panel><Empty icon="analytics">
          {preds.length === 0 ? 'No predictions for this pair yet.' : 'No predictions in the selected date range.'}
          {preds.length === 0 && (
            <button className="btn sm" style={{ marginTop: 10 }} disabled={!!running} onClick={() => runJob('regression')}>
              <Icon.assistant size={13} /> {running === 'regression' ? 'Running…' : 'Run regression job'}
            </button>
          )}
        </Empty></Panel>
      )}
    </>
  )
}

function Mini({ label, value, accent }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className={'kpi-val ' + (accent || '')} style={{ fontSize: 22 }}>{value}</div>
    </div>
  )
}

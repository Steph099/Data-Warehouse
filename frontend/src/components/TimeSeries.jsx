import { useEffect, useState } from 'react'
import { api, daysAgo, today } from '../api.js'
import { useApp } from '../App.jsx'
import { Header, Panel, Spinner, ErrorBox, Field, Empty, Badge, fmt, fmtCompact } from './ui.jsx'
import { Icon } from './icons.jsx'
import CandleChart from './CandleChart.jsx'
import LineChart from './Chart.jsx'

const RANGES = [
  { id: '30d', label: '30D', days: 30 },
  { id: '90d', label: '90D', days: 90 },
  { id: '180d', label: '180D', days: 180 },
  { id: '1y', label: '1Y', days: 365 },
]
const PRICE_KEYS = ['close', 'last', 'mid', 'adj_close', 'price']

export default function TimeSeries() {
  const app = useApp()
  const [assets, setAssets] = useState([])
  const [sources, setSources] = useState([])
  const [range, setRange] = useState('90d')
  const [form, setForm] = useState({
    assetId: app.asset || '',
    dataSourceId: app.source || '',
    start: daysAgo(90),
    end: today(),
    includeAttributes: true,
    asOf: '',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listAssets(0, 1000).then((a) => {
      setAssets(a)
      setForm((f) => ({ ...f, assetId: f.assetId || a[0] || '' }))
    }).catch(() => {})
    api.listDataSources(0, 1000).then((s) => {
      setSources(s)
      setForm((f) => ({ ...f, dataSourceId: f.dataSourceId || s[0] || '' }))
    }).catch(() => {})
  }, [])

  const set = (k) => (e) =>
    setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const applyRange = (r) => {
    setRange(r.id)
    setForm((f) => ({ ...f, start: daysAgo(r.days), end: today() }))
  }

  const submit = (e) => {
    e?.preventDefault()
    if (!form.assetId || !form.dataSourceId) return
    setLoading(true)
    setError(null)
    setResult(null)
    api.getData(form).then(setResult).catch(setError).finally(() => setLoading(false))
  }

  // auto-run on first mount once selects are populated / when arriving via deep-link
  useEffect(() => {
    if (form.assetId && form.dataSourceId && !result && !loading) submit()
  }, [form.assetId, form.dataSourceId]) // eslint-disable-line

  const records = result?.data?.records || []
  const cols = records.length
    ? Array.from(new Set(records.flatMap((r) => Object.keys(r.values)))).sort()
    : []

  // chronological bars for charting
  const bars = [...records].reverse().map((r) => ({ date: r.businessDate, ...r.values }))
  const hasOHLC = ['open', 'high', 'low', 'close'].every((k) => cols.includes(k))
  const priceKey = PRICE_KEYS.find((k) => cols.includes(k)) || cols.find((c) => typeof records[0]?.values[c] === 'number')
  const linePoints = !hasOHLC && priceKey ? bars.filter((b) => b[priceKey] != null).map((b) => ({ y: b[priceKey] })) : []

  const exportCsv = () => {
    const header = ['businessDate', ...cols].join(',')
    const lines = records.map((r) => [r.businessDate, ...cols.map((c) => r.values[c] ?? '')].join(','))
    const blob = new Blob([[header, ...lines].join('\n')], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${form.assetId}_${form.dataSourceId.replace(/[/]/g, '-')}_${form.start}_${form.end}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <Header title="Time Series Explorer" subtitle="Half-open [start, end) range, newest first, latest version per business date — with optional as-of time travel (Q5)." />

      <form className="toolbar" onSubmit={submit}>
        <Field label="Asset">
          <select value={form.assetId} onChange={set('assetId')}>
            {assets.map((a) => <option key={a}>{a}</option>)}
          </select>
        </Field>
        <Field label="Data source">
          <select value={form.dataSourceId} onChange={set('dataSourceId')}>
            {sources.map((s) => <option key={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="Range">
          <div className="range-tabs">
            {RANGES.map((r) => (
              <button type="button" key={r.id} className={range === r.id ? 'on' : ''} onClick={() => applyRange(r)}>{r.label}</button>
            ))}
          </div>
        </Field>
        <Field label="Start (incl)">
          <input type="date" className="mono" value={form.start} onChange={(e) => { setRange(''); set('start')(e) }} />
        </Field>
        <Field label="End (excl)">
          <input type="date" className="mono" value={form.end} onChange={(e) => { setRange(''); set('end')(e) }} />
        </Field>
        <Field label="As of (snapshot)">
          <input type="datetime-local" className="mono" value={form.asOf} onChange={set('asOf')} />
        </Field>
        <label className="toggle" style={{ alignSelf: 'center' }}>
          <input type="checkbox" checked={form.includeAttributes} onChange={set('includeAttributes')} /> attributes
        </label>
        <button className="btn primary" type="submit"><Icon.search size={14} /> Query</button>
      </form>

      {loading && <Spinner label="Querying the warehouse…" />}
      <ErrorBox error={error} />

      {result && (
        <>
          <div className="meta-row">
            <Badge kind="neutral">{result.data.assetId}</Badge>
            <span className="muted">×</span>
            <Badge kind="neutral">{result.data.dataSourceId}</Badge>
            <span className="muted small">{records.length} record(s)</span>
            {form.asOf && <Badge kind="crypto"><Icon.history size={11} /> as of {form.asOf.replace('T', ' ')}</Badge>}
            <div style={{ flex: 1 }} />
            {records.length > 0 && (
              <button className="btn sm" onClick={exportCsv}><Icon.download size={13} /> Export CSV</button>
            )}
          </div>

          {bars.length > 1 && hasOHLC && (
            <Panel eyebrow="OHLCV" title="Candlestick">
              <CandleChart bars={bars} height={360} />
              <div className="x-axis">
                <span>{bars[0].date}</span>
                <span>{bars[bars.length - 1].date}</span>
              </div>
            </Panel>
          )}

          {linePoints.length > 1 && (
            <Panel eyebrow={`indicator · ${priceKey}`} title={`${priceKey} over time`}>
              <LineChart series={[{ color: 'var(--accent)', points: linePoints }]} format={fmtCompact} fill />
              <div className="x-axis">
                <span>{bars[0].date}</span>
                <span>{bars[bars.length - 1].date}</span>
              </div>
              <div className="legend"><span className="muted">This source supplies no OHLC candles, so the <b>{priceKey}</b> indicator is plotted instead — a direct view of the heterogeneous data model.</span></div>
            </Panel>
          )}

          {records.length === 0 ? (
            <Panel><Empty icon="series">No records in this range. Try widening the dates, or ingest this asset/source pair.</Empty></Panel>
          ) : (
            <Panel eyebrow="raw records · newest first" title="Time series">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>businessDate</th>
                      {cols.map((c) => <th key={c} className="num">{c}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((r, i) => (
                      <tr key={i}>
                        <td className="mono">{r.businessDate}</td>
                        {cols.map((c) => <td key={c} className="num">{fmt(r.values[c])}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          )}
        </>
      )}
    </>
  )
}

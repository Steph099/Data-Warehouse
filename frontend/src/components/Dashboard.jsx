import { useEffect, useState } from 'react'
import { api, daysAgo, today } from '../api.js'
import { useApp } from '../App.jsx'
import { Header, Panel, Spinner, ErrorBox, Empty, Badge, fmt, fmtCompact, pct, Skeleton } from './ui.jsx'
import { Icon } from './icons.jsx'
import CandleChart from './CandleChart.jsx'
import { Sparkline } from './Chart.jsx'

const WINDOW = 140 // days of history loaded for the overview

export default function Dashboard() {
  const app = useApp()
  const [assets, setAssets] = useState([])
  const [sources, setSources] = useState([])
  const [rows, setRows] = useState([]) // per-asset market summary
  const [featured, setFeatured] = useState(null) // {id, bars}
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    ;(async () => {
      try {
        const [a, s] = await Promise.all([api.listAssets(0, 100), api.listDataSources(0, 100)])
        if (!alive) return
        setAssets(a)
        setSources(s)
        const primary = s.includes('BITFINEX') ? 'BITFINEX' : s[0]
        const start = daysAgo(WINDOW)
        const end = today()
        const summaries = await Promise.all(
          a.slice(0, 8).map(async (id) => {
            try {
              const r = await api.getData({ assetId: id, dataSourceId: primary, start, end })
              const recs = r.data.records // newest first
              if (!recs.length) return null
              const closes = recs.map((x) => x.values.close).filter((v) => v != null)
              const last = closes[0]
              const prev = closes[1]
              const m30 = closes[Math.min(closes.length - 1, 30)]
              return {
                id,
                source: primary,
                last,
                change24: prev != null ? ((last - prev) / prev) * 100 : null,
                change30: m30 != null ? ((last - m30) / m30) * 100 : null,
                spark: [...closes].reverse(),
                bars: recs
                  .map((x) => ({ date: x.businessDate, ...x.values }))
                  .reverse(),
                latestDate: recs[0].businessDate,
              }
            } catch {
              return null
            }
          })
        )
        if (!alive) return
        const valid = summaries.filter(Boolean)
        setRows(valid)
        const pick = valid.find((v) => v.id === app.asset) || valid[0]
        if (pick) setFeatured({ id: pick.id, source: pick.source, bars: pick.bars, latest: pick.last, change: pick.change24, latestDate: pick.latestDate })
      } catch (e) {
        if (alive) setError(e)
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => { alive = false }
  }, []) // eslint-disable-line

  const coverage = rows.length ? rows[0].latestDate : null

  return (
    <>
      <Header
        title="Market Overview"
        subtitle="A live snapshot of everything in the warehouse — assets, sources, and recent price action, served straight from the bi-temporal store."
      />

      {error && <ErrorBox error={error} />}

      {/* KPI row */}
      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Kpi icon="assets" label="Assets tracked" value={loading ? null : assets.length} sub="financial instruments" />
        <Kpi icon="source" label="Data sources" value={loading ? null : sources.length} sub="ingestion providers" />
        <Kpi
          icon="layers"
          label={featured ? featured.id + ' last close' : 'Last close'}
          value={featured ? fmtCompact(featured.latest) : null}
          sub={featured ? 'as of ' + featured.latestDate : '—'}
          accent={featured && featured.change != null ? (featured.change >= 0 ? 'up' : 'down') : null}
          spark={featured ? rows.find((r) => r.id === featured.id)?.spark : null}
        />
        <Kpi icon="history" label="Coverage" value={coverage ? coverage.slice(0, 4) : null} sub={coverage ? 'latest business date ' + coverage : '—'} />
      </div>

      <div className="grid cols-2" style={{ alignItems: 'start' }}>
        {/* featured candlestick */}
        <Panel
          eyebrow="Price action · last 140 days"
          title={featured ? featured.id + ' · ' + featured.source : 'Featured asset'}
          actions={
            featured && (
              <button className="btn sm" onClick={() => app.goto('timeseries', { asset: featured.id, source: featured.source })}>
                Open in Explorer <Icon.external size={13} />
              </button>
            )
          }
        >
          {loading ? (
            <Skeleton h={320} />
          ) : featured && featured.bars.length > 1 ? (
            <>
              <CandleChart bars={featured.bars} height={320} />
              <div className="x-axis">
                <span>{featured.bars[0].date}</span>
                <span>{featured.bars[featured.bars.length - 1].date}</span>
              </div>
              <div className="legend">
                <span className="lg"><i style={{ background: 'var(--up)' }} /> bullish day</span>
                <span className="lg"><i style={{ background: 'var(--down)' }} /> bearish day</span>
                <span className="lg muted">volume shown below price</span>
              </div>
            </>
          ) : (
            <Empty icon="series">No price data yet — ingest an asset to begin.</Empty>
          )}
        </Panel>

        {/* movers list */}
        <Panel eyebrow="Snapshot" title="Markets">
          {loading ? (
            <div className="stack">
              {[0, 1, 2].map((i) => <Skeleton key={i} h={52} />)}
            </div>
          ) : rows.length === 0 ? (
            <Empty icon="inbox">Nothing ingested yet.</Empty>
          ) : (
            <div className="stack" style={{ gap: 2 }}>
              {rows.map((r) => (
                <MoverRow
                  key={r.id}
                  r={r}
                  active={featured && featured.id === r.id}
                  onView={() => setFeatured({ id: r.id, source: r.source, bars: r.bars, latest: r.last, change: r.change24, latestDate: r.latestDate })}
                  onExplore={() => app.goto('timeseries', { asset: r.id, source: r.source })}
                />
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* capability cards */}
      <div className="grid cols-3" style={{ marginTop: 16 }}>
        <FeatureCard
          icon="ingest" title="Ingest market data"
          body="Pull OHLCV history from Bitfinex or Nasdaq Data Link. Idempotent ETL records full provenance."
          cta="Run ingestion" onClick={() => app.goto('ingest')}
        />
        <FeatureCard
          icon="analytics" title="Spark analytics & ML"
          body="Per-year aggregates and a regression that forecasts the daily open — computed in Spark, stored back in the warehouse."
          cta="View analytics" onClick={() => app.goto('analytics', { asset: featured?.id, source: featured?.source })}
        />
        <FeatureCard
          icon="assistant" title="Ask the assistant"
          body="A grounded LLM that answers in natural language by calling the warehouse tools over MCP — never guessing."
          cta="Open assistant" onClick={() => app.goto('assistant')}
        />
      </div>
    </>
  )
}

function Kpi({ icon, label, value, sub, accent, spark }) {
  const I = Icon[icon]
  return (
    <div className="kpi">
      <div className="kpi-label">
        <span className="kpi-ico"><I size={15} /></span> {label}
      </div>
      <div className={'kpi-val ' + (accent || '')}>
        {value == null ? <Skeleton h={28} w={90} style={{ marginTop: 4 }} /> : value}
      </div>
      <div className="kpi-sub">{sub}</div>
      {spark && (
        <div className="kpi-spark">
          <Sparkline values={spark} color={accent === 'down' ? 'var(--down)' : 'var(--up)'} height={34} />
        </div>
      )}
    </div>
  )
}

function MoverRow({ r, active, onView, onExplore }) {
  const up = (r.change24 ?? 0) >= 0
  return (
    <div
      className="idlist"
      style={{ padding: 0 }}
    >
      <div
        onClick={onView}
        className={'mover' + (active ? ' sel' : '')}
        style={{
          display: 'grid', gridTemplateColumns: '1fr 88px 78px', alignItems: 'center', gap: 10,
          padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
          background: active ? 'var(--panel-3)' : 'transparent',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <div className="mono" style={{ fontWeight: 600 }}>{r.id}</div>
          <div className="muted small">{r.source}</div>
        </div>
        <div className="num" style={{ textAlign: 'right' }}>{fmtCompact(r.last)}</div>
        <div style={{ textAlign: 'right' }}>
          {r.change24 == null ? <span className="muted">—</span> : (
            <Badge kind={up ? 'up' : 'down'}>
              {up ? <Icon.arrowUp size={11} /> : <Icon.arrowDown size={11} />} {pct(r.change24)}
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, body, cta, onClick }) {
  const I = Icon[icon]
  return (
    <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <span style={{ color: 'var(--accent)' }}><I size={22} /></span>
      <h3 style={{ margin: 0, fontSize: 15 }}>{title}</h3>
      <p className="muted small" style={{ margin: 0, flex: 1, lineHeight: 1.55 }}>{body}</p>
      <button className="btn sm" style={{ alignSelf: 'flex-start' }} onClick={onClick}>
        {cta} <Icon.external size={13} />
      </button>
    </div>
  )
}

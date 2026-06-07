import { useEffect, useState, useMemo } from 'react'
import { api } from '../api.js'
import { useApp } from '../App.jsx'
import { Header, Panel, Spinner, ErrorBox, Empty, Badge, Skeleton, fmtDateTime, assetKind } from './ui.jsx'
import { Icon } from './icons.jsx'

const LIMIT = 50

export default function Assets() {
  const app = useApp()
  const [ids, setIds] = useState([])
  const [offset, setOffset] = useState(0)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(app.asset || null)
  const [detail, setDetail] = useState(null)
  const [history, setHistory] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.listAssets(offset, LIMIT).then(setIds).catch(setError).finally(() => setLoading(false))
  }, [offset])

  useEffect(() => {
    if (!selected) return
    app.setAsset(selected)
    setDetail(null)
    setError(null)
    api.getAsset(selected, history).then(setDetail).catch(setError)
  }, [selected, history]) // eslint-disable-line

  const shown = useMemo(
    () => (q ? ids.filter((id) => id.toLowerCase().includes(q.toLowerCase())) : ids),
    [ids, q]
  )

  return (
    <>
      <Header title="Assets" subtitle="Browse financial instruments, inspect heterogeneous attributes, and replay every stored version (Q1 · Q2)." />
      <div className="split">
        <Panel className="list-panel">
          <div className="list-head">
            <span className="eyebrow">Asset ids · offset {offset}</span>
            <div className="pager">
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>‹</button>
              <button disabled={ids.length < LIMIT} onClick={() => setOffset(offset + LIMIT)}>›</button>
            </div>
          </div>
          <div className="field search">
            <div style={{ position: 'relative' }}>
              <Icon.search size={14} style={{ position: 'absolute', left: 10, top: 10, color: 'var(--faint)' }} />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter ids…" className="mono" style={{ width: '100%', paddingLeft: 32 }} />
            </div>
          </div>
          {loading ? (
            <div className="stack" style={{ gap: 6 }}>{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} h={34} />)}</div>
          ) : shown.length === 0 ? (
            <Empty icon="assets">{ids.length ? 'No match.' : 'No assets yet — ingest some.'}</Empty>
          ) : (
            <ul className="idlist">
              {shown.map((id) => (
                <li key={id} className={id === selected ? 'sel' : ''} onClick={() => setSelected(id)}>
                  <Icon.hash size={13} style={{ color: 'var(--faint)', flex: 'none' }} />
                  <span className="id-name">{id}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <div>
          {!selected ? (
            <Panel><Empty icon="assets">Select an asset to see its details.</Empty></Panel>
          ) : (
            <Panel>
              <div className="detail-head">
                <div className="detail-title">
                  <h2>{selected}</h2>
                  {detail && !history && detail.deleted && <Badge kind="tombstone">delisted</Badge>}
                  {detail && !history && !detail.deleted && (
                    <Badge kind={assetKind(detail.attributes)}>
                      {detail.attributes?.class || 'instrument'}
                    </Badge>
                  )}
                </div>
                <div className="detail-actions">
                  <button className="btn sm" onClick={() => app.goto('timeseries', { asset: selected })}>
                    <Icon.series size={13} /> Time series
                  </button>
                  <button className="btn sm" onClick={() => app.goto('analytics', { asset: selected })}>
                    <Icon.analytics size={13} /> Analytics
                  </button>
                  <button className="btn sm" onClick={() => app.goto('assistant', { asset: selected, intent: { prompt: `Summarize recent price action for ${selected} and explain the trend.` } })}>
                    <Icon.sparkles size={13} /> Ask
                  </button>
                  <label className="toggle" style={{ marginLeft: 4 }}>
                    <input type="checkbox" checked={history} onChange={(e) => setHistory(e.target.checked)} /> history
                  </label>
                </div>
              </div>
              <ErrorBox error={error} />
              {!detail ? (
                <Spinner />
              ) : history ? (
                <HistoryTimeline versions={detail} render={(a) => <AttrChips attrs={a.attributes} />} />
              ) : (
                <AssetDetail a={detail} />
              )}
            </Panel>
          )}
        </div>
      </div>
    </>
  )
}

function AssetDetail({ a }) {
  return (
    <>
      <div className="kv-grid">
        <div className="k">name</div><div className="v">{a.name ?? '—'}</div>
        <div className="k">description</div><div className="v">{a.description ?? '—'}</div>
        <div className="k">version (system time)</div><div className="v num">{fmtDateTime(a.system_time)}</div>
        <div className="k">status</div><div className="v">{a.deleted ? <Badge kind="down">deleted tombstone</Badge> : <Badge kind="live">active</Badge>}</div>
      </div>
      <div className="attrs">
        <div className="attrs-label">attributes</div>
        <AttrChips attrs={a.attributes} />
      </div>
    </>
  )
}

function AttrChips({ attrs = {} }) {
  const entries = Object.entries(attrs)
  if (entries.length === 0) return <span className="muted small">no attributes</span>
  return entries.map(([k, v]) => (
    <span key={k} className="chip">{k}: {v}</span>
  ))
}

export function HistoryTimeline({ versions, render }) {
  if (!versions.length) return <Empty icon="history">No versions.</Empty>
  return (
    <div className="timeline">
      {versions.map((v, i) => (
        <div key={i} className={'tl-item' + (v.deleted ? ' deleted' : '')}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span className="tl-time">{fmtDateTime(v.system_time)}</span>
            {i === 0 && <Badge kind="live">latest</Badge>}
            {v.deleted && <Badge kind="tombstone">tombstone</Badge>}
          </div>
          <div className="attrs" style={{ marginTop: 0 }}>{render(v)}</div>
        </div>
      ))}
    </div>
  )
}

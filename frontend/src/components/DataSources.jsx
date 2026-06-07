import { useEffect, useState, useMemo } from 'react'
import { api } from '../api.js'
import { useApp } from '../App.jsx'
import { Header, Panel, Spinner, ErrorBox, Empty, Badge, Skeleton, fmtDateTime } from './ui.jsx'
import { Icon } from './icons.jsx'
import { HistoryTimeline } from './Assets.jsx'

const LIMIT = 50

export default function DataSources() {
  const app = useApp()
  const [ids, setIds] = useState([])
  const [offset, setOffset] = useState(0)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(app.source || null)
  const [detail, setDetail] = useState(null)
  const [history, setHistory] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.listDataSources(offset, LIMIT).then(setIds).catch(setError).finally(() => setLoading(false))
  }, [offset])

  useEffect(() => {
    if (!selected) return
    app.setSource(selected)
    setDetail(null)
    setError(null)
    api.getDataSource(selected, history).then(setDetail).catch(setError)
  }, [selected, history]) // eslint-disable-line

  const shown = useMemo(
    () => (q ? ids.filter((id) => id.toLowerCase().includes(q.toLowerCase())) : ids),
    [ids, q]
  )

  return (
    <>
      <Header title="Data Sources" subtitle="Inspect each provider's provenance and the heterogeneous set of indicators it supplies (Q3 · Q4)." />
      <div className="split">
        <Panel className="list-panel">
          <div className="list-head">
            <span className="eyebrow">Source ids · offset {offset}</span>
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
            <div className="stack" style={{ gap: 6 }}>{[0, 1, 2].map((i) => <Skeleton key={i} h={34} />)}</div>
          ) : shown.length === 0 ? (
            <Empty icon="source">{ids.length ? 'No match.' : 'No data sources yet.'}</Empty>
          ) : (
            <ul className="idlist">
              {shown.map((id) => (
                <li key={id} className={id === selected ? 'sel' : ''} onClick={() => setSelected(id)}>
                  <Icon.source size={13} style={{ color: 'var(--faint)', flex: 'none' }} />
                  <span className="id-name">{id}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <div>
          {!selected ? (
            <Panel><Empty icon="source">Select a data source to see its details.</Empty></Panel>
          ) : (
            <Panel>
              <div className="detail-head">
                <div className="detail-title">
                  <h2>{selected}</h2>
                  {detail && !history && (detail.deleted ? <Badge kind="tombstone">retired</Badge> : <Badge kind="live">active</Badge>)}
                </div>
                <div className="detail-actions">
                  <button className="btn sm" onClick={() => app.goto('timeseries', { source: selected })}>
                    <Icon.series size={13} /> Query this source
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
                <HistoryTimeline versions={detail} render={(s) => <IndicatorChips attrs={s.attributes} />} />
              ) : (
                <SourceDetail s={detail} />
              )}
            </Panel>
          )}
        </div>
      </div>
    </>
  )
}

function SourceDetail({ s }) {
  return (
    <>
      <div className="kv-grid">
        <div className="k">name</div><div className="v">{s.name ?? '—'}</div>
        <div className="k">provenance</div><div className="v">{s.description ?? '—'}</div>
        <div className="k">version (system time)</div><div className="v num">{fmtDateTime(s.system_time)}</div>
        <div className="k">indicators</div><div className="v num">{(s.attributes || []).length}</div>
      </div>
      <div className="attrs">
        <div className="attrs-label">supported indicators</div>
        <IndicatorChips attrs={s.attributes} />
      </div>
    </>
  )
}

function IndicatorChips({ attrs = [] }) {
  if (!attrs.length) return <span className="muted small">none declared</span>
  return attrs.map((a) => (
    <span key={a} className="chip"><Icon.hash size={11} /> {a}</span>
  ))
}

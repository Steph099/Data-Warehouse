import { useState, useEffect, createContext, useContext, useCallback } from 'react'
import { api } from './api.js'
import { Icon } from './components/icons.jsx'
import Dashboard from './components/Dashboard.jsx'
import Assets from './components/Assets.jsx'
import DataSources from './components/DataSources.jsx'
import TimeSeries from './components/TimeSeries.jsx'
import Analytics from './components/Analytics.jsx'
import Ingest from './components/Ingest.jsx'
import Assistant from './components/Assistant.jsx'

// Flat, ordered tab list for the top navigation bar.
const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard', el: Dashboard },
  { id: 'assets', label: 'Assets', icon: 'assets', el: Assets },
  { id: 'sources', label: 'Data Sources', icon: 'source', el: DataSources },
  { id: 'timeseries', label: 'Time Series', icon: 'series', el: TimeSeries },
  { id: 'analytics', label: 'Analytics', icon: 'analytics', el: Analytics },
  { id: 'assistant', label: 'Assistant', icon: 'assistant', el: Assistant },
  { id: 'ingest', label: 'Ingest', icon: 'ingest', el: Ingest },
]

// ---- shared app context: selected asset/source + cross-view navigation ----
const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

export default function App() {
  const [tab, setTab] = useState('dashboard')
  const [healthy, setHealthy] = useState(null)
  // cross-view selection context (carried when deep-linking between views)
  const [sel, setSel] = useState({ asset: null, source: null })
  const [pending, setPending] = useState(null) // one-shot intent for a target view
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const ping = () =>
      api.health().then(() => setHealthy(true)).catch(() => setHealthy(false))
    ping()
    const h = setInterval(ping, 15000)
    const c = setInterval(() => setNow(new Date()), 1000)
    return () => { clearInterval(h); clearInterval(c) }
  }, [])

  // navigate to a view, optionally seeding selection + an intent payload
  const goto = useCallback((target, ctx = {}) => {
    setSel((s) => ({
      asset: ctx.asset !== undefined ? ctx.asset : s.asset,
      source: ctx.source !== undefined ? ctx.source : s.source,
    }))
    if (ctx.intent) setPending({ view: target, ...ctx.intent })
    setTab(target)
  }, [])

  const consumeIntent = useCallback((view) => {
    if (pending && pending.view === view) {
      const p = pending
      setPending(null)
      return p
    }
    return null
  }, [pending])

  const active = TABS.find((t) => t.id === tab) || TABS[0]
  const Active = active.el

  const ctxValue = {
    asset: sel.asset, source: sel.source,
    setAsset: (asset) => setSel((s) => ({ ...s, asset })),
    setSource: (source) => setSel((s) => ({ ...s, source })),
    goto, consumeIntent,
  }

  return (
    <Ctx.Provider value={ctxValue}>
      <div className="app">
        <header className="appbar">
          <div className="brand">
            <span className="brand-mark"><Icon.layers size={19} /></span>
            <div className="brand-text">
              <div className="brand-title">MarketVault</div>
              <div className="brand-sub">Financial Data Warehouse</div>
            </div>
          </div>

          <nav className="tabs">
            {TABS.map((t) => {
              const I = Icon[t.icon]
              return (
                <button
                  key={t.id}
                  className={'tab' + (t.id === tab ? ' active' : '')}
                  onClick={() => setTab(t.id)}
                >
                  <I className="ico" size={16} />
                  <span>{t.label}</span>
                </button>
              )
            })}
          </nav>

          <div className="appbar-right">
            {sel.asset && (
              <button className="chip click" onClick={() => goto('timeseries')}>
                <Icon.assets size={13} /> {sel.asset}
              </button>
            )}
            <div className="clock">
              <Icon.clock size={14} />
              <span>{now.toLocaleTimeString(undefined, { hour12: false })}</span>
            </div>
            <div className="health" title="Bi-temporal store · records are immutable; history is preserved and replayable.">
              <span className={'dot ' + (healthy ? 'ok' : healthy === false ? 'bad' : '')} />
              <span className="health-lbl">
                {healthy == null ? 'connecting…' : healthy ? 'online' : 'offline'}
              </span>
            </div>
          </div>
        </header>

        <main className="view">
          <div className="view-inner" key={tab}>
            <Active />
          </div>
        </main>
      </div>
    </Ctx.Provider>
  )
}

const BASE = '/api/v1'

async function req(path, opts) {
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    let detail
    try {
      detail = (await res.json()).detail
    } catch {
      detail = `HTTP ${res.status}`
    }
    throw new Error(typeof detail === 'string' ? detail : `HTTP ${res.status}`)
  }
  return res.json()
}

// Asset/source ids may contain '/', which the backend captures via a {:path} route.
const enc = (id) => id.split('/').map(encodeURIComponent).join('/')
const json = (body) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  health: () => fetch('/health').then((r) => r.json()),

  listAssets: (offset = 0, limit = 50) => req(`/assets?offset=${offset}&limit=${limit}`),
  getAsset: (id, history = false) => req(`/assets/${enc(id)}${history ? '?history=true' : ''}`),

  listDataSources: (offset = 0, limit = 50) =>
    req(`/data-sources?offset=${offset}&limit=${limit}`),
  getDataSource: (id, history = false) =>
    req(`/data-sources/${enc(id)}${history ? '?history=true' : ''}`),

  getData: (p) => {
    const q = new URLSearchParams({
      assetId: p.assetId,
      dataSourceId: p.dataSourceId,
      startBusinessDate: p.start,
      endBusinessDate: p.end,
      includeAttributes: p.includeAttributes ? 'true' : 'false',
    })
    if (p.asOf) q.set('asOf', p.asOf)
    return req(`/data?${q.toString()}`)
  },

  ingest: (body) => req('/ingest', json(body)),
  totals: (assetId, dataSourceId) =>
    req(`/analytics/totals?assetId=${enc(assetId)}&dataSourceId=${enc(dataSourceId)}`),
  predictions: (assetId, dataSourceId, limit = 200) =>
    req(`/analytics/predictions?assetId=${enc(assetId)}&dataSourceId=${enc(dataSourceId)}&limit=${limit}`),
  runJob: (job, assetId, dataSourceId) =>
    req(`/analytics/jobs/${encodeURIComponent(job)}`, json({ assetId, dataSourceId })),
  ask: (question) => req('/assistant/ask', json({ question })),
}

// ---- date helpers ----
export const isoDate = (d) => d.toISOString().slice(0, 10)
export const today = () => isoDate(new Date())
export const daysAgo = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return isoDate(d)
}

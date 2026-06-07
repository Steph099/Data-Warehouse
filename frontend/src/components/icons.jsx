// Inline stroke icons (lucide-style), dependency-free.
const S = ({ children, size = 17, ...p }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...p}
  >
    {children}
  </svg>
)

export const Icon = {
  dashboard: (p) => (<S {...p}><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></S>),
  assets: (p) => (<S {...p}><path d="M3 3v18h18"/><path d="M7 14l3-3 3 3 4-5"/></S>),
  source: (p) => (<S {...p}><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></S>),
  series: (p) => (<S {...p}><path d="M3 3v18h18"/><path d="M19 9l-5 5-4-4-3 3"/></S>),
  analytics: (p) => (<S {...p}><path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="6"/><rect x="12" y="7" width="3" height="10"/><rect x="17" y="13" width="3" height="4"/></S>),
  ingest: (p) => (<S {...p}><path d="M12 3v12"/><path d="m8 11 4 4 4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></S>),
  assistant: (p) => (<S {...p}><path d="M12 2a3 3 0 0 1 3 3v1h1a3 3 0 0 1 3 3v2a3 3 0 0 1-3 3h-1l-3 3v-3H9a3 3 0 0 1-3-3V9a3 3 0 0 1 3-3h0"/><circle cx="9.5" cy="10.5" r="1"/><circle cx="14.5" cy="10.5" r="1"/></S>),
  search: (p) => (<S {...p}><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></S>),
  clock: (p) => (<S {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></S>),
  history: (p) => (<S {...p}><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/></S>),
  arrowUp: (p) => (<S {...p}><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></S>),
  arrowDown: (p) => (<S {...p}><path d="M12 5v14"/><path d="m19 12-7 7-7-7"/></S>),
  download: (p) => (<S {...p}><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></S>),
  send: (p) => (<S {...p}><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4Z"/></S>),
  sparkles: (p) => (<S {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="m6 6 2 2M16 16l2 2M18 6l-2 2M8 16l-2 2"/></S>),
  layers: (p) => (<S {...p}><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/></S>),
  hash: (p) => (<S {...p}><path d="M4 9h16M4 15h16M10 3 8 21M16 3l-2 18"/></S>),
  external: (p) => (<S {...p}><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></S>),
  inbox: (p) => (<S {...p}><path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13l3.5 7v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6Z"/></S>),
  refresh: (p) => (<S {...p}><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></S>),
}

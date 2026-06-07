import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import { useApp } from '../App.jsx'
import { Header, Panel, Empty } from './ui.jsx'
import { Icon } from './icons.jsx'

const SUGGESTIONS = [
  'What crypto assets do we have, and how did BTCUSD move in the last week of February 2024?',
  'Which data sources are available and what indicators does BITFINEX provide?',
  'Summarize ETHUSD prices in January 2024.',
  'Compare BTCUSD and ETHUSD over the first quarter of 2024.',
]

export default function Assistant() {
  const app = useApp()
  const [messages, setMessages] = useState([]) // {role, text, steps?, error?}
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const logRef = useRef(null)

  // seed prompt from a deep-link intent (e.g. "Ask" on an asset)
  useEffect(() => {
    const intent = app.consumeIntent?.('assistant')
    if (intent?.prompt) setQ(intent.prompt)
  }, []) // eslint-disable-line

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const ask = (text) => {
    const question = (text ?? q).trim()
    if (!question || loading) return
    setQ('')
    setMessages((m) => [...m, { role: 'user', text: question }])
    setLoading(true)
    api
      .ask(question)
      .then((resp) =>
        setMessages((m) => [...m, { role: 'bot', text: resp.answer, steps: resp.steps, error: resp.error }])
      )
      .catch((e) =>
        setMessages((m) => [...m, { role: 'bot', error: `Couldn't reach the assistant: ${e.message}. Make sure the API is running and Ollama is serving a tool-calling model.` }])
      )
      .finally(() => setLoading(false))
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask() }
  }

  return (
    <>
      <Header title="Assistant" subtitle="A grounded LLM that answers by calling the warehouse's MCP tools — every number is read from real data, never invented (UC4)." />

      <Panel className="chat">
        <div className="chat-log" ref={logRef} style={{ maxHeight: '52vh', overflow: 'auto' }}>
          {messages.length === 0 && !loading && (
            <Empty icon="assistant">
              Ask anything about the assets, data sources, or price history in the warehouse.
            </Empty>
          )}
          {messages.map((m, i) => <Message key={i} m={m} />)}
          {loading && (
            <div className="msg bot">
              <div className="avatar"><Icon.sparkles size={15} /></div>
              <div className="bubble">
                <div className="muted small" style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                  <span className="ring" /> thinking · calling tools…
                </div>
              </div>
            </div>
          )}
        </div>

        {messages.length === 0 && (
          <div className="suggestions">
            {SUGGESTIONS.map((s, i) => (
              <span key={i} className="chip click suggestion" onClick={() => ask(s)}>
                {s.length > 52 ? s.slice(0, 52) + '…' : s}
              </span>
            ))}
          </div>
        )}

        <div className="chat-input">
          <textarea
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKey}
            rows={2}
            placeholder="Ask about assets, data sources, or price history…  (Enter to send, Shift+Enter for newline)"
          />
          <button className="btn primary" onClick={() => ask()} disabled={loading || !q.trim()}>
            <Icon.send size={15} /> Ask
          </button>
        </div>
      </Panel>
    </>
  )
}

function Message({ m }) {
  if (m.role === 'user') {
    return (
      <div className="msg user">
        <div className="avatar">You</div>
        <div className="bubble"><div className="body">{m.text}</div></div>
      </div>
    )
  }
  return (
    <div className="msg bot">
      <div className="avatar"><Icon.sparkles size={15} /></div>
      <div className="bubble">
        {m.error ? (
          <div className="error" style={{ margin: 0 }}><span>⚠</span><span>{m.error}</span></div>
        ) : (
          <div className="body">{m.text || '(no answer)'}</div>
        )}
        {m.steps?.length > 0 && (
          <div className="tool-trace">
            <div className="tt-label">tool calls · {m.steps.length}</div>
            {m.steps.map((s, i) => (
              <div key={i} className={'step' + (s.ok ? '' : ' err')}>
                <span className="step-tool">{s.tool}</span>
                <span className="step-args">{JSON.stringify(s.args)}</span>
                <span className="step-ok">{s.ok ? '✓' : '✕'}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

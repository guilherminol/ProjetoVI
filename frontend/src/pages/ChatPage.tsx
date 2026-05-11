import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { type Source, streamChat, submitFeedback } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  not_found?: boolean
  logId?: number
  rating?: 'useful' | 'not_useful' | null
  streaming?: boolean
}

export default function ChatPage() {
  const { user, logout } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId] = useState(() => crypto.randomUUID())
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault()
    const question = input.trim()
    if (!question || busy) return

    setInput('')
    setBusy(true)
    setMessages((prev) => [...prev, { role: 'user', content: question }])

    const assistantIdx = messages.length + 1
    setMessages((prev) => [...prev, { role: 'assistant', content: '', streaming: true }])

    try {
      let logId: number | undefined
      await streamChat(
        question,
        sessionId,
        (token) => {
          setMessages((prev) =>
            prev.map((m, i) => (i === assistantIdx ? { ...m, content: m.content + token } : m)),
          )
        },
        (done) => {
          logId = done.log_id
          setMessages((prev) =>
            prev.map((m, i) =>
              i === assistantIdx
                ? { ...m, streaming: false, sources: done.sources, not_found: done.not_found, logId }
                : m,
            ),
          )
        },
      )
    } catch {
      setMessages((prev) =>
        prev.map((m, i) =>
          i === assistantIdx
            ? { ...m, content: 'Erro ao conectar com o servidor. Tente novamente.', streaming: false }
            : m,
        ),
      )
    } finally {
      setBusy(false)
    }
  }

  async function rate(msgIndex: number, rating: 'useful' | 'not_useful') {
    const msg = messages[msgIndex]
    if (!msg.logId) return
    await submitFeedback(msg.logId, rating)
    setMessages((prev) => prev.map((m, i) => (i === msgIndex ? { ...m, rating } : m)))
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between border-b bg-white px-6 py-3 shadow-sm">
        <div>
          <span className="font-bold text-blue-700">Cancella</span>
          <span className="ml-2 text-sm text-gray-500">Suporte Técnico</span>
        </div>
        <div className="flex items-center gap-4">
          {user?.role === 'admin' && (
            <Link to="/admin" className="text-sm text-blue-600 hover:underline">
              Painel Admin
            </Link>
          )}
          <span className="text-sm text-gray-600">{user?.email}</span>
          <button onClick={logout} className="text-sm text-gray-400 hover:text-gray-600">
            Sair
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-2xl space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 mt-16">
              <p className="text-lg font-medium">Como posso ajudar?</p>
              <p className="text-sm mt-1">Faça sua pergunta técnica sobre os produtos Cancella.</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-xl rounded-2xl px-4 py-3 text-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-800 border border-gray-200 shadow-sm'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.streaming && (
                  <span className="inline-block h-3 w-1 animate-pulse bg-gray-400 ml-1 align-middle" />
                )}

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3 border-t border-gray-100 pt-2">
                    <p className="text-xs font-medium text-gray-500 mb-1">Fonte:</p>
                    <div className="flex flex-wrap gap-2">
                      {msg.sources.map((s) => (
                        <a
                          key={s.document_id}
                          href={`/api${s.download_url}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-blue-600 underline hover:text-blue-800"
                        >
                          {s.filename}
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Feedback */}
                {msg.role === 'assistant' && !msg.streaming && msg.logId && (
                  <div className="mt-3 flex items-center gap-2 border-t border-gray-100 pt-2">
                    <span className="text-xs text-gray-400">Esta resposta foi útil?</span>
                    <button
                      onClick={() => rate(i, 'useful')}
                      className={`rounded px-2 py-0.5 text-xs font-medium transition ${
                        msg.rating === 'useful'
                          ? 'bg-green-100 text-green-700'
                          : 'text-gray-400 hover:text-green-600'
                      }`}
                    >
                      Útil
                    </button>
                    <button
                      onClick={() => rate(i, 'not_useful')}
                      className={`rounded px-2 py-0.5 text-xs font-medium transition ${
                        msg.rating === 'not_useful'
                          ? 'bg-red-100 text-red-700'
                          : 'text-gray-400 hover:text-red-600'
                      }`}
                    >
                      Não Útil
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-white px-4 py-4">
        <form onSubmit={sendMessage} className="mx-auto flex max-w-2xl gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
            placeholder="Digite sua dúvida técnica..."
            className="flex-1 rounded-xl border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
          >
            Enviar
          </button>
        </form>
      </div>
    </div>
  )
}

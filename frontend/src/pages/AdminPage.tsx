import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  type DocItem,
  type FeedbackStats,
  deleteDocument,
  getFeedbackStats,
  listDocuments,
  uploadDocument,
} from '../api/client'
import { useAuth } from '../contexts/AuthContext'

type Tab = 'upload' | 'documents' | 'feedback'

export default function AdminPage() {
  const { user, logout } = useAuth()
  const [tab, setTab] = useState<Tab>('documents')

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <header className="flex items-center justify-between border-b bg-white px-6 py-3 shadow-sm">
        <div>
          <span className="font-bold text-blue-700">Cancella</span>
          <span className="ml-2 text-sm text-gray-500">Painel Administrativo</span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/" className="text-sm text-blue-600 hover:underline">Chat</Link>
          <span className="text-sm text-gray-600">{user?.email}</span>
          <button onClick={logout} className="text-sm text-gray-400 hover:text-gray-600">Sair</button>
        </div>
      </header>

      <div className="flex border-b bg-white px-6">
        {(['documents', 'upload', 'feedback'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`mr-6 py-3 text-sm font-medium border-b-2 transition ${
              tab === t ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'documents' ? 'Documentos' : t === 'upload' ? 'Upload' : 'Feedback'}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {tab === 'upload' && <UploadTab />}
        {tab === 'documents' && <DocumentsTab />}
        {tab === 'feedback' && <FeedbackTab />}
      </div>
    </div>
  )
}

function UploadTab() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setLoading(true)
    setStatus('')
    try {
      const res = await uploadDocument(file)
      setStatus(`✓ ${res.message}`)
      if (fileRef.current) fileRef.current.value = ''
    } catch (err) {
      setStatus(`Erro: ${(err as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Upload de Manual PDF</h2>
      <form onSubmit={handleUpload} className="space-y-4 rounded-xl border bg-white p-6 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Arquivo PDF</label>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,application/pdf"
            required
            className="w-full text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>
        {status && (
          <p className={`text-sm ${status.startsWith('Erro') ? 'text-red-600' : 'text-green-700'}`}>
            {status}
          </p>
        )}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Enviando...' : 'Fazer Upload'}
        </button>
      </form>
      <p className="mt-3 text-xs text-gray-400">
        O documento será processado automaticamente. Acompanhe o status na aba Documentos.
      </p>
    </div>
  )
}

function DocumentsTab() {
  const [docs, setDocs] = useState<DocItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listDocuments().then((r) => { setDocs(r.documents); setLoading(false) })
  }, [])

  async function handleDelete(docId: string) {
    if (!confirm('Remover este documento da base de conhecimento?')) return
    await deleteDocument(docId)
    setDocs((prev) => prev.filter((d) => d.document_id !== docId))
  }

  const statusColor: Record<string, string> = {
    ready: 'text-green-700 bg-green-50',
    processing: 'text-yellow-700 bg-yellow-50',
    pending: 'text-gray-600 bg-gray-100',
    error: 'text-red-700 bg-red-50',
  }

  if (loading) return <p className="text-sm text-gray-400">Carregando...</p>

  return (
    <div className="mx-auto max-w-3xl">
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Documentos Indexados ({docs.length})</h2>
      {docs.length === 0 ? (
        <p className="text-sm text-gray-400">Nenhum documento ainda. Faça upload na aba Upload.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Adicionado em</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {docs.map((doc) => (
                <tr key={doc.document_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{doc.filename}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor[doc.status] ?? 'text-gray-600'}`}>
                      {doc.status}
                    </span>
                    {doc.error_message && (
                      <p className="mt-0.5 text-xs text-red-500">{doc.error_message}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(doc.created_at).toLocaleDateString('pt-BR')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(doc.document_id)}
                      className="text-xs text-red-500 hover:text-red-700 hover:underline"
                    >
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function FeedbackTab() {
  const [stats, setStats] = useState<FeedbackStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getFeedbackStats().then((s) => { setStats(s); setLoading(false) })
  }, [])

  if (loading) return <p className="text-sm text-gray-400">Carregando...</p>
  if (!stats) return null

  const pct = stats.total_rated > 0 ? Math.round(stats.satisfaction_rate * 100) : null

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h2 className="text-lg font-semibold text-gray-800">Dashboard de Feedback</h2>

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Avaliações" value={stats.total_rated} />
        <StatCard label="Úteis" value={stats.useful_count} accent="text-green-700" />
        <StatCard label="Não Úteis" value={stats.not_useful_count} accent="text-red-600" />
      </div>

      {pct !== null && (
        <div className="rounded-xl border bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500 mb-2">Taxa de satisfação</p>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-3 rounded-full bg-gray-100 overflow-hidden">
              <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-sm font-bold text-gray-700">{pct}%</span>
          </div>
        </div>
      )}

      {stats.worst_responses.length > 0 && (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-gray-700">
            Respostas mais avaliadas negativamente (últimas 20)
          </h3>
          <div className="space-y-3">
            {stats.worst_responses.map((log) => (
              <div key={log.log_id} className="rounded-xl border bg-white p-4 shadow-sm">
                <p className="text-xs font-medium text-gray-500 mb-1">
                  {new Date(log.created_at).toLocaleString('pt-BR')}
                </p>
                <p className="text-sm font-medium text-gray-800 mb-1">P: {log.question}</p>
                <p className="text-sm text-gray-600 line-clamp-3">R: {log.answer}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  accent = 'text-gray-800',
}: {
  label: string
  value: number
  accent?: string
}) {
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm text-center">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${accent}`}>{value}</p>
    </div>
  )
}

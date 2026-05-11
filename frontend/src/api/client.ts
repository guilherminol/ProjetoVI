const API = '/api'

function getToken(): string | null {
  return localStorage.getItem('token')
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = getToken()
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

export async function login(email: string, password: string): Promise<{ access_token: string }> {
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  })
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Login failed')
  return res.json()
}

export async function getMe(): Promise<{ user_id: string; email: string; role: string }> {
  const res = await fetch(`${API}/auth/me`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Unauthorized')
  return res.json()
}

export async function streamChat(
  question: string,
  sessionId: string,
  onToken: (token: string) => void,
  onDone: (data: { not_found: boolean; sources: Source[]; log_id?: number }) => void,
): Promise<void> {
  const res = await fetch(`${API}/chat`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ question, session_id: sessionId }),
  })
  if (!res.ok) throw new Error('Chat request failed')

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = JSON.parse(line.slice(6))
      if (data.type === 'token') onToken(data.content)
      else if (data.type === 'done') onDone(data)
    }
  }
}

export async function submitFeedback(logId: number, rating: 'useful' | 'not_useful'): Promise<void> {
  await fetch(`${API}/chat/feedback/${logId}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify({ rating }),
  })
}

export async function listDocuments(): Promise<{ documents: DocItem[]; total: number }> {
  const res = await fetch(`${API}/admin/documents`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to list documents')
  return res.json()
}

export async function uploadDocument(file: File): Promise<{ document_id: string; status: string; message: string }> {
  const token = getToken()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API}/admin/documents/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  if (!res.ok) throw new Error((await res.json()).detail ?? 'Upload failed')
  return res.json()
}

export async function deleteDocument(docId: string): Promise<void> {
  await fetch(`${API}/admin/documents/${docId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  })
}

export async function getFeedbackStats(): Promise<FeedbackStats> {
  const res = await fetch(`${API}/admin/feedback/stats`, { headers: authHeaders() })
  if (!res.ok) throw new Error('Failed to load feedback stats')
  return res.json()
}

export interface Source {
  document_id: string
  filename: string
  download_url: string
}

export interface DocItem {
  document_id: string
  filename: string
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface FeedbackStats {
  total_rated: number
  useful_count: number
  not_useful_count: number
  satisfaction_rate: number
  worst_responses: {
    log_id: number
    session_id: string
    question: string
    answer: string
    rating: string | null
    created_at: string
  }[]
}

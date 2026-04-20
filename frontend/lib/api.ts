const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('lexquery_token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    localStorage.removeItem('lexquery_token')
    window.location.href = '/login'
    throw new Error('Unauthorised')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }

  return res.json()
}

// ── Auth ─────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_id: string
  tenant_id: string
  role: string
  requires_totp: boolean
}

export interface UserResponse {
  id: string
  email: string
  full_name: string | null
  role: string
  tenant_id: string
  is_active: boolean
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function getMe(): Promise<UserResponse> {
  return request('/auth/me')
}

// ── Workspaces ───────────────────────────────────────────────────

export interface Workspace {
  id: string
  name: string
  description: string | null
  matter_number: string | null
  is_active: boolean
  tenant_id: string
}

export async function listWorkspaces(): Promise<Workspace[]> {
  return request('/workspaces')
}

export async function createWorkspace(data: {
  name: string
  description?: string
  matter_number?: string
}): Promise<Workspace> {
  return request('/workspaces', { method: 'POST', body: JSON.stringify(data) })
}

// ── Documents ────────────────────────────────────────────────────

export interface Document {
  id: string
  filename: string
  document_type: string
  status: string
  chunk_count: number | null
  page_count: number | null
  file_size_bytes: number | null
  workspace_id: string
  error_message: string | null
}

export async function uploadDocument(
  workspaceId: string,
  file: File,
  matterNumber?: string
): Promise<Document> {
  const token = getToken()
  const formData = new FormData()
  formData.append('workspace_id', workspaceId)
  formData.append('file', file)
  if (matterNumber) formData.append('matter_number', matterNumber)

  const res = await fetch(`${API_BASE}/documents`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Upload failed')
  }

  return res.json()
}

export async function getDocument(documentId: string): Promise<Document> {
  return request(`/documents/${documentId}`)
}

// ── Query ────────────────────────────────────────────────────────

export interface Citation {
  citation_number: number
  document_id: string
  filename: string
  page_number: number
  excerpt: string
  relevance_score: number
  matter_number: string | null
}

export interface QueryResponse {
  query: string
  answer: string
  citations: Citation[]
  confidence_score: number
  confidence_label: string
  chunks_retrieved: number
  chunks_used: number
  workspace_id: string | null
}

export async function submitQuery(
  query: string,
  workspaceId?: string
): Promise<QueryResponse> {
  return request('/query', {
    method: 'POST',
    body: JSON.stringify({ query, workspace_id: workspaceId }),
  })
}

// ── Audit ────────────────────────────────────────────────────────

export interface AuditLog {
  id: string
  user_id: string | null
  query_text: string
  workspace_id: string | null
  retrieved_doc_ids: string[] | null
  cited_doc_ids: string[] | null
  confidence_score: number | null
  llm_model: string | null
  guardrail_flags: string | null
  created_at: string
}

export async function getAuditLogs(limit = 50): Promise<AuditLog[]> {
  return request(`/audit/logs?limit=${limit}`)
}

// ── Register ──────────────────────────────────────────────────────

export async function register(data: {
  tenant_name: string
  tenant_slug: string
  email: string
  password: string
  full_name?: string
}): Promise<TokenResponse> {
  return request('/auth/register', { method: 'POST', body: JSON.stringify(data) })
}

// ── Delete document ───────────────────────────────────────────────

export async function deleteDocument(documentId: string): Promise<void> {
  await request(`/documents/${documentId}`, { method: 'DELETE' })
}

// ── Streaming query ───────────────────────────────────────────────

export async function streamQuery(
  query: string,
  workspaceId: string | undefined,
  onChunk: (text: string) => void,
  onDone: (fullResponse: QueryResponse) => void,
  onError: (err: string) => void,
): Promise<void> {
  const token = getToken()
  const res = await fetch(`${API_BASE}/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ query, workspace_id: workspaceId }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    onError(err.detail || 'Query failed')
    return
  }

  const reader = res.body?.getReader()
  const decoder = new TextDecoder()
  if (!reader) { onError('No response body'); return }

  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6).trim()
        if (data === '[DONE]') continue
        try {
          const parsed = JSON.parse(data)
          if (parsed.chunk) onChunk(parsed.chunk)
          if (parsed.done) onDone(parsed)
        } catch {}
      }
    }
  }
}

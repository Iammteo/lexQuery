'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('lexquery_token') : null

type ApiKey = { id: string; name: string; key_prefix: string; is_active: boolean; last_used_at: string | null; created_at: string | null }

export default function ApiKeysPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [newKeyName, setNewKeyName] = useState('')
  const [creating, setCreating] = useState(false)
  const [newRawKey, setNewRawKey] = useState('')
  const [revoking, setRevoking] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!isLoading && !user) router.push('/login')
    if (!isLoading && user && user.role !== 'tenant_admin') router.push('/dashboard')
  }, [user, isLoading, router])

  useEffect(() => {
    if (!user || user.role !== 'tenant_admin') return
    fetch(`${API}/api-keys`, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then(r => r.ok ? r.json() : []).then(setKeys).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyName.trim()) return
    setCreating(true); setError('')
    try {
      const res = await fetch(`${API}/api-keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ name: newKeyName.trim() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to create key')
      setNewRawKey(data.raw_key)
      setKeys(prev => [data, ...prev])
      setNewKeyName('')
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed') }
    finally { setCreating(false) }
  }

  const handleRevoke = async (id: string) => {
    if (!confirm('Revoke this API key? Any applications using it will stop working immediately.')) return
    setRevoking(id)
    try {
      await fetch(`${API}/api-keys/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${getToken()}` } })
      setKeys(prev => prev.filter(k => k.id !== id))
    } catch {} finally { setRevoking(null) }
  }

  const copyKey = () => {
    navigator.clipboard.writeText(newRawKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading || !user) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><p style={{ color: '#9CA3AF' }}>Loading...</p></div>

  return (
    <div style={{ minHeight: '100vh', background: '#F8F7F5', fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif' }}>
      <div style={{ background: '#1A2B4A', padding: '0 24px' }}>
        <div style={{ maxWidth: 860, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Link href="/dashboard/settings" style={{ color: 'rgba(255,255,255,.5)', fontSize: 13, textDecoration: 'none' }}>← Settings</Link>
            <span style={{ color: 'rgba(255,255,255,.2)' }}>·</span>
            <span style={{ color: 'white', fontSize: 13, fontWeight: 600 }}>API Keys</span>
          </div>
          <span style={{ color: 'white', fontSize: 13, fontWeight: 700 }}>LexQuery</span>
        </div>
      </div>

      <div style={{ maxWidth: 860, margin: '0 auto', padding: '28px 20px' }}>

        {/* New key revealed */}
        {newRawKey && (
          <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: 10, padding: 20, marginBottom: 20 }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: '#166534', marginBottom: 6 }}>✓ API key created — copy it now</p>
            <p style={{ fontSize: 12, color: '#166534', marginBottom: 12 }}>This key will not be shown again. Store it somewhere safe.</p>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <code style={{ flex: 1, background: 'white', border: '1px solid #BBF7D0', borderRadius: 5, padding: '8px 12px', fontSize: 12, fontFamily: 'monospace', wordBreak: 'break-all', color: '#1A202C' }}>{newRawKey}</code>
              <button onClick={copyKey} style={{ padding: '8px 14px', background: '#16A34A', color: 'white', border: 'none', borderRadius: 5, fontSize: 13, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' }}>
                {copied ? '✓ Copied' : 'Copy'}
              </button>
            </div>
            <button onClick={() => setNewRawKey('')} style={{ marginTop: 10, fontSize: 12, color: '#6B7280', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
              I've saved my key — dismiss
            </button>
          </div>
        )}

        {/* Create form */}
        <div style={{ background: 'white', border: '1px solid #E2E0DB', borderRadius: 10, padding: 24, marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1A2B4A', marginBottom: 6 }}>Create API key</h2>
          <p style={{ fontSize: 13, color: '#6B7280', marginBottom: 18 }}>API keys allow programmatic access to LexQuery. Treat them like passwords.</p>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <input
              type="text" value={newKeyName} onChange={e => setNewKeyName(e.target.value)}
              placeholder="Key name — e.g. Production App, CI Pipeline"
              style={{ flex: 1, minWidth: 200, padding: '9px 12px', border: '1px solid #E2E0DB', borderRadius: 6, fontSize: 14, outline: 'none', background: '#F8F7F5' }}
            />
            <button type="submit" disabled={creating || !newKeyName.trim()} style={{ padding: '9px 18px', background: (creating || !newKeyName.trim()) ? '#9CA3AF' : '#1A2B4A', color: 'white', border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: (creating || !newKeyName.trim()) ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap' }}>
              {creating ? 'Creating...' : 'Create key'}
            </button>
          </form>
          {error && <p style={{ fontSize: 13, color: '#DC2626', marginTop: 8 }}>{error}</p>}
        </div>

        {/* Keys list */}
        <div style={{ background: 'white', border: '1px solid #E2E0DB', borderRadius: 10, overflow: 'hidden' }}>
          <div style={{ padding: '14px 20px', borderBottom: '1px solid #E2E0DB', background: '#F8F7F5' }}>
            <h2 style={{ fontSize: 14, fontWeight: 700, color: '#374151', margin: 0 }}>Active keys ({keys.length})</h2>
          </div>
          {loading ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>Loading...</div>
          ) : keys.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>No API keys yet. Create one above.</div>
          ) : (
            keys.map((k, i) => (
              <div key={k.id} style={{ padding: '14px 20px', borderBottom: i < keys.length - 1 ? '1px solid #E2E0DB' : 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ minWidth: 0 }}>
                  <p style={{ fontSize: 14, fontWeight: 600, color: '#1A202C', margin: '0 0 3px' }}>{k.name}</p>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    <code style={{ fontSize: 12, color: '#6B7280', fontFamily: 'monospace' }}>{k.key_prefix}••••••••</code>
                    {k.last_used_at ? (
                      <span style={{ fontSize: 12, color: '#9CA3AF' }}>Last used: {new Date(k.last_used_at).toLocaleDateString()}</span>
                    ) : (
                      <span style={{ fontSize: 12, color: '#9CA3AF' }}>Never used</span>
                    )}
                    {k.created_at && <span style={{ fontSize: 12, color: '#9CA3AF' }}>Created: {new Date(k.created_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                <button onClick={() => handleRevoke(k.id)} disabled={revoking === k.id} style={{ fontSize: 12, color: '#DC2626', background: 'none', border: '1px solid #FECACA', borderRadius: 5, padding: '5px 10px', cursor: 'pointer', whiteSpace: 'nowrap', fontWeight: 600 }}>
                  {revoking === k.id ? 'Revoking...' : 'Revoke'}
                </button>
              </div>
            ))
          )}
        </div>

        <div style={{ marginTop: 16, padding: '12px 16px', background: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: 8, fontSize: 13, color: '#92400E' }}>
          <strong>Security note:</strong> API keys have the same access as your account. Never expose them in client-side code or public repositories. Rotate them regularly.
        </div>
      </div>
    </div>
  )
}

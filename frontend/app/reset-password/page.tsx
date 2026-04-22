'use client'
import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'

function ResetContent() {
  const params = useSearchParams()
  const token = params.get('token') || ''
  const router = useRouter()

  const [email, setEmail] = useState('')
  const [tokenValid, setTokenValid] = useState<boolean | null>(null)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!token) { setTokenValid(false); return }
    fetch(`${API}/auth/reset-password/validate?token=${token}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data) { setEmail(data.email); setTokenValid(true) }
        else setTokenValid(false)
      })
      .catch(() => setTokenValid(false))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true); setError('')
    try {
      const res = await fetch(`${API}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Reset failed')
      setSuccess(true)
      setTimeout(() => router.push('/login'), 3000)
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Reset failed') }
    finally { setLoading(false) }
  }

  const inp = { width: '100%', padding: '10px 12px', border: '1px solid #E2E0DB', borderRadius: 6, fontSize: 14, outline: 'none', background: '#F8F7F5', boxSizing: 'border-box' as const }

  if (tokenValid === null) return (
    <div style={{ textAlign: 'center', padding: 24 }}>
      <div style={{ width: 24, height: 24, border: '2px solid #E2E0DB', borderTopColor: '#1A2B4A', borderRadius: '50%', margin: '0 auto', animation: 'spin .7s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      <p style={{ color: '#9CA3AF', fontSize: 13, marginTop: 12 }}>Validating link...</p>
    </div>
  )

  if (tokenValid === false) return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>⚠</div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', marginBottom: 8 }}>Invalid or expired link</h2>
      <p style={{ fontSize: 14, color: '#6B7280', marginBottom: 20 }}>This reset link has expired or already been used.</p>
      <Link href="/forgot-password" style={{ fontSize: 14, color: '#1A2B4A', fontWeight: 600 }}>Request a new link →</Link>
    </div>
  )

  if (success) return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ width: 52, height: 52, background: '#F0FDF4', border: '2px solid #BBF7D0', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', fontSize: 22 }}>✓</div>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', marginBottom: 8 }}>Password reset!</h2>
      <p style={{ fontSize: 14, color: '#6B7280' }}>Redirecting you to sign in...</p>
    </div>
  )

  return (
    <form onSubmit={handleSubmit}>
      <h1 style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', marginBottom: 4 }}>Set new password</h1>
      <p style={{ fontSize: 13, color: '#9CA3AF', marginBottom: 20 }}>
        Resetting password for <strong style={{ color: '#374151' }}>{email}</strong>
      </p>
      <div style={{ marginBottom: 14 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>New password</label>
        <input type="password" required value={password} onChange={e => setPassword(e.target.value)} placeholder="Minimum 8 characters" minLength={8} style={inp} autoFocus />
      </div>
      <div style={{ marginBottom: 20 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Confirm password</label>
        <input type="password" required value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Re-enter password" style={inp} />
      </div>
      {error && <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 6, padding: '10px 12px', fontSize: 13, color: '#DC2626', marginBottom: 14 }}>{error}</div>}
      <button type="submit" disabled={loading} style={{ width: '100%', padding: 11, background: loading ? '#9CA3AF' : '#1A2B4A', color: 'white', border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer' }}>
        {loading ? (
          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,.3)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />
            Resetting...
          </span>
        ) : 'Reset password'}
      </button>
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#F8F7F5', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 16px', fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif' }}>
      <div style={{ width: '100%', maxWidth: 420 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Link href="/" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 30, height: 30, background: '#1A2B4A', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: 'white', fontSize: 14, fontWeight: 700 }}>L</span>
            </div>
            <span style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A' }}>LexQuery</span>
          </Link>
        </div>
        <div style={{ background: 'white', border: '1px solid #E2E0DB', borderRadius: 10, padding: '28px 24px' }}>
          <Suspense fallback={<p style={{ color: '#9CA3AF', textAlign: 'center' }}>Loading...</p>}>
            <ResetContent />
          </Suspense>
        </div>
      </div>
    </div>
  )
}

'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { login } from '@/lib/api'
import { useAuth } from '@/lib/auth-context'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'

const inputStyle = { width: '100%', padding: '10px 12px', border: '1px solid #E2E0DB', borderRadius: 6, fontSize: 14, color: '#1A202C', background: '#F8F7F5', outline: 'none', boxSizing: 'border-box' as const }
const labelStyle = { display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [userId, setUserId] = useState('')
  const [requiresTotp, setRequiresTotp] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setToken } = useAuth()
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const res = await login(email, password)
      if (res.requires_totp) { setUserId(res.user_id); setRequiresTotp(true) }
      else { setToken(res.access_token); router.push('/dashboard') }
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Login failed') }
    finally { setLoading(false) }
  }

  const handleTotp = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const res = await fetch(`${API}/auth/verify-totp`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, code: totpCode }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Invalid code')
      setToken(data.access_token); router.push('/dashboard')
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'Invalid code') }
    finally { setLoading(false) }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#F8F7F5', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 16px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>
      <div style={{ width: '100%', maxWidth: 420 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Link href="/" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 30, height: 30, background: '#1A2B4A', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: 'white', fontSize: 14, fontWeight: 700 }}>L</span>
            </div>
            <span style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', letterSpacing: '-0.3px' }}>LexQuery</span>
          </Link>
        </div>

        <div style={{ background: 'white', border: '1px solid #E2E0DB', borderRadius: 10, padding: '28px 24px' }}>
          {!requiresTotp ? (
            <form onSubmit={handleLogin}>
              <h1 style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', marginBottom: 4 }}>Sign in to your account</h1>
              <p style={{ fontSize: 13, color: '#9CA3AF', marginBottom: 24 }}>Welcome back to LexQuery.</p>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Email address</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@firm.com" style={inputStyle} />
              </div>
              <div style={{ marginBottom: 20 }}>
                <label style={labelStyle}>Password</label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="••••••••" style={inputStyle} />
              </div>
              <div style={{ background: '#F8F7F5', border: '1px solid #E2E0DB', borderRadius: 6, padding: 12, marginBottom: 20 }}>
                <p style={{ fontSize: 12, color: '#6B7280', margin: '0 0 8px', fontWeight: 600 }}>Or continue with</p>
                <div style={{ display: 'flex', gap: 8 }}>
                  {['Google', 'Microsoft'].map(p => (
                    <button key={p} type="button" onClick={() => { if (p === 'Google') window.location.href = 'http://localhost:8000/v1/auth/google/login'; else alert('Microsoft OAuth coming soon') }} style={{ flex: 1, padding: '9px', border: '1px solid #E2E0DB', borderRadius: 5, background: 'white', fontSize: 13, color: '#374151', cursor: 'pointer', fontWeight: 500 }}>
                      {p === 'Google' ? 'G' : 'M'} {p}
                    </button>
                  ))}
                </div>
              </div>
              {error && <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 6, padding: '10px 12px', fontSize: 13, color: '#DC2626', marginBottom: 14 }}>{error}</div>}
              <button type="submit" disabled={loading} style={{ width: '100%', padding: 11, background: loading ? '#9CA3AF' : '#1A2B4A', color: 'white', border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer' }}>
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleTotp}>
              <h1 style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', marginBottom: 4 }}>Two-factor authentication</h1>
              <p style={{ fontSize: 13, color: '#6B7280', marginBottom: 24, lineHeight: 1.6 }}>Enter the 6-digit code from your authenticator app.</p>
              <input type="text" required value={totpCode} onChange={e => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" maxLength={6} autoFocus style={{ ...inputStyle, fontSize: 24, fontWeight: 700, textAlign: 'center', letterSpacing: 6, marginBottom: 20 }} />
              {error && <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 6, padding: '10px 12px', fontSize: 13, color: '#DC2626', marginBottom: 14 }}>{error}</div>}
              <button type="submit" disabled={loading || totpCode.length !== 6} style={{ width: '100%', padding: 11, background: (loading || totpCode.length !== 6) ? '#9CA3AF' : '#1A2B4A', color: 'white', border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: (loading || totpCode.length !== 6) ? 'not-allowed' : 'pointer', marginBottom: 8 }}>
                {loading ? 'Verifying...' : 'Verify'}
              </button>
              <button type="button" onClick={() => setRequiresTotp(false)} style={{ width: '100%', padding: 11, background: 'white', color: '#6B7280', border: '1px solid #E2E0DB', borderRadius: 6, fontSize: 14, cursor: 'pointer' }}>Back</button>
            </form>
          )}
        </div>
        {!requiresTotp && (
          <p style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#9CA3AF' }}>
            Don&apos;t have an account?{' '}
            <Link href="/signup" style={{ color: '#1A2B4A', fontWeight: 700 }}>Start free trial</Link>
          </p>
        )}
      </div>
    </div>
  )
}

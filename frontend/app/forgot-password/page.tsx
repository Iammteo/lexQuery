'use client'
import { useState } from 'react'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      await fetch(`${API}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      setSent(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally { setLoading(false) }
  }

  const inp = { width: '100%', padding: '10px 12px', border: '1px solid #E2E0DB', borderRadius: 6, fontSize: 14, outline: 'none', background: '#F8F7F5', boxSizing: 'border-box' as const }

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
          {sent ? (
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: 52, height: 52, background: '#F0FDF4', border: '2px solid #BBF7D0', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', fontSize: 22 }}>✓</div>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', marginBottom: 8 }}>Check your email</h2>
              <p style={{ fontSize: 14, color: '#6B7280', lineHeight: 1.65, marginBottom: 20 }}>
                If an account exists for <strong style={{ color: '#374151' }}>{email}</strong>, a reset link has been sent. Check your inbox and spam folder.
              </p>
              <p style={{ fontSize: 13, color: '#9CA3AF' }}>The link expires in 1 hour.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <Link href="/login" style={{ color: '#9CA3AF', textDecoration: 'none', fontSize: 18, lineHeight: 1 }}>←</Link>
                <div>
                  <h1 style={{ fontSize: 18, fontWeight: 700, color: '#1A2B4A', marginBottom: 2 }}>Forgot password?</h1>
                  <p style={{ fontSize: 13, color: '#9CA3AF', margin: 0 }}>Enter your email and we'll send a reset link.</p>
                </div>
              </div>
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Email address</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="you@firm.com" style={inp} autoFocus />
              </div>
              {error && <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: 6, padding: '10px 12px', fontSize: 13, color: '#DC2626', marginBottom: 14 }}>{error}</div>}
              <button type="submit" disabled={loading} style={{ width: '100%', padding: 11, background: loading ? '#9CA3AF' : '#1A2B4A', color: 'white', border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer' }}>
                {loading ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                    <span style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,.3)', borderTopColor: 'white', borderRadius: '50%', display: 'inline-block', animation: 'spin .7s linear infinite' }} />
                    Sending...
                  </span>
                ) : 'Send reset link'}
              </button>
              <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
            </form>
          )}
        </div>

        <p style={{ textAlign: 'center', marginTop: 16, fontSize: 13, color: '#9CA3AF' }}>
          Remember your password?{' '}
          <Link href="/login" style={{ color: '#1A2B4A', fontWeight: 700 }}>Sign in</Link>
        </p>
      </div>
    </div>
  )
}

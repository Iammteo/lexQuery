'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { Suspense } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'

function slugify(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
}

function CallbackContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { setToken } = useAuth()

  const token = searchParams.get('token')
  const oauthEmail = searchParams.get('oauth_email')
  const oauthName = searchParams.get('oauth_name') || ''
  const provider = searchParams.get('provider') || 'google'
  const error = searchParams.get('error')

  const [step, setStep] = useState<'loading' | 'org_setup' | 'error'>('loading')
  const [tenantName, setTenantName] = useState('')
  const [tenantSlug, setTenantSlug] = useState('')
  const [fullName, setFullName] = useState(oauthName)
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')

  useEffect(() => {
    if (token) {
      setToken(token)
      router.push('/dashboard')
    } else if (oauthEmail) {
      setFullName(decodeURIComponent(oauthName))
      setStep('org_setup')
    } else if (error) {
      setStep('error')
    }
  }, [token, oauthEmail, error])

  const handleOrgSetup = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setSubmitting(true)
    try {
      const res = await fetch(`${API}/auth/oauth/complete-registration`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: decodeURIComponent(oauthEmail || ''),
          full_name: fullName,
          tenant_name: tenantName,
          tenant_slug: tenantSlug,
          provider,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Registration failed')
      setToken(data.access_token)
      router.push('/dashboard')
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setSubmitting(false)
    }
  }

  const errorMessages: Record<string, string> = {
    invalid_state: 'Authentication session expired. Please try again.',
    google_failed: 'Google sign-in failed. Please try again.',
    microsoft_failed: 'Microsoft sign-in failed. Please try again.',
    no_email: 'Could not retrieve your email address from the provider.',
    account_inactive: 'Your account has been deactivated. Contact your administrator.',
  }

  if (step === 'loading') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#F8F7F5' }}>
        <p style={{ color: '#9CA3AF', fontSize: '14px' }}>Completing sign-in...</p>
      </div>
    )
  }

  if (step === 'error') {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#F8F7F5', padding: '2rem' }}>
        <div style={{ maxWidth: '400px', width: '100%', textAlign: 'center' }}>
          <div style={{ width: '48px', height: '48px', backgroundColor: '#FEF2F2', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem', fontSize: '20px' }}>✕</div>
          <h1 style={{ fontSize: '18px', fontWeight: '700', color: '#1A2B4A', marginBottom: '0.5rem' }}>Sign-in failed</h1>
          <p style={{ fontSize: '14px', color: '#6B7280', marginBottom: '1.5rem' }}>{errorMessages[error || ''] || 'Something went wrong. Please try again.'}</p>
          <a href="/login" style={{ display: 'inline-block', backgroundColor: '#1A2B4A', color: 'white', padding: '10px 24px', borderRadius: '6px', textDecoration: 'none', fontSize: '14px', fontWeight: '600' }}>Back to login</a>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#F8F7F5', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' }}>
      <div style={{ width: '100%', maxWidth: '440px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ width: '30px', height: '30px', backgroundColor: '#1A2B4A', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
            <span style={{ color: 'white', fontSize: '14px', fontWeight: '700' }}>L</span>
          </div>
          <h1 style={{ fontSize: '20px', fontWeight: '700', color: '#1A2B4A', marginBottom: '0.25rem' }}>One last step</h1>
          <p style={{ fontSize: '13px', color: '#9CA3AF' }}>
            Signed in as <strong style={{ color: '#374151' }}>{decodeURIComponent(oauthEmail || '')}</strong> via {provider === 'google' ? 'Google' : 'Microsoft'}.
            <br />Set up your organisation to continue.
          </p>
        </div>

        <div style={{ backgroundColor: 'white', border: '1px solid #E2E0DB', borderRadius: '10px', padding: '2rem' }}>
          <form onSubmit={handleOrgSetup}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '6px' }}>Your full name</label>
              <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} placeholder="Sarah Chen" style={{ width: '100%', padding: '10px 12px', border: '1px solid #E2E0DB', borderRadius: '6px', fontSize: '14px', color: '#1A1A1A', backgroundColor: '#F8F7F5', outline: 'none', boxSizing: 'border-box' }} />
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '6px' }}>Organisation name</label>
              <input type="text" required value={tenantName} onChange={e => { setTenantName(e.target.value); setTenantSlug(slugify(e.target.value)) }} placeholder="Chambers & Partners LLP" style={{ width: '100%', padding: '10px 12px', border: '1px solid #E2E0DB', borderRadius: '6px', fontSize: '14px', color: '#1A1A1A', backgroundColor: '#F8F7F5', outline: 'none', boxSizing: 'border-box' }} />
            </div>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '600', color: '#374151', marginBottom: '6px' }}>Workspace identifier</label>
              <div style={{ display: 'flex', border: '1px solid #E2E0DB', borderRadius: '6px', overflow: 'hidden' }}>
                <span style={{ padding: '10px', backgroundColor: '#F8F7F5', fontSize: '12px', color: '#9CA3AF', borderRight: '1px solid #E2E0DB', whiteSpace: 'nowrap' }}>lexquery.com/</span>
                <input type="text" required value={tenantSlug} onChange={e => setTenantSlug(e.target.value)} placeholder="chambers-partners" style={{ flex: 1, padding: '10px 12px', border: 'none', fontSize: '14px', color: '#1A1A1A', backgroundColor: 'white', outline: 'none' }} />
              </div>
            </div>

            {formError && <div style={{ backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '6px', padding: '10px 12px', fontSize: '13px', color: '#DC2626', marginBottom: '1rem' }}>{formError}</div>}

            <button type="submit" disabled={submitting} style={{ width: '100%', padding: '11px', backgroundColor: submitting ? '#9CA3AF' : '#1A2B4A', color: 'white', border: 'none', borderRadius: '6px', fontSize: '14px', fontWeight: '700', cursor: submitting ? 'not-allowed' : 'pointer' }}>
              {submitting ? 'Setting up...' : 'Create organisation'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><p style={{ color: '#9CA3AF' }}>Loading...</p></div>}>
      <CallbackContent />
    </Suspense>
  )
}

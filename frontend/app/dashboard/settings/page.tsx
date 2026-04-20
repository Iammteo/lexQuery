'use client'
import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('lexquery_token') : null

type Usage = {
  plan: string
  plan_label: string
  trial_days_left: number | null
  subscription_status: string
  queries: { used: number; limit: number }
  pages: { used: number; limit: number }
  seats: { used: number; limit: number }
}

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = limit > 900_000 ? 0 : Math.min(100, Math.round((used / limit) * 100))
  const unlimited = limit > 900_000
  const color = pct > 90 ? '#DC2626' : pct > 70 ? '#D97706' : '#16A34A'
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>{label}</span>
        <span style={{ fontSize: 12, color: '#6B7280' }}>
          {unlimited ? `${used.toLocaleString()} / Unlimited` : `${used.toLocaleString()} / ${limit.toLocaleString()}`}
        </span>
      </div>
      {!unlimited && (
        <div style={{ height: 6, background: '#E2E0DB', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 3, transition: 'width .4s ease' }} />
        </div>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [usage, setUsage] = useState<Usage | null>(null)
  const [orgName, setOrgName] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [logoUploading, setLogoUploading] = useState(false)
  const [portalLoading, setPortalLoading] = useState(false)
  const logoRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!isLoading && !user) router.push('/login')
  }, [user, isLoading, router])

  useEffect(() => {
    if (!user) return
    fetch(`${API}/billing/usage`, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then(r => r.ok ? r.json() : null).then(setUsage).catch(() => {})
  }, [user])

  const handleBillingPortal = async () => {
    setPortalLoading(true)
    try {
      const res = await fetch(`${API}/billing/portal`, { headers: { Authorization: `Bearer ${getToken()}` } })
      const data = await res.json()
      if (data.url) window.location.href = data.url
      else alert('Billing portal not available — set up Stripe first.')
    } catch { alert('Could not open billing portal.') }
    finally { setPortalLoading(false) }
  }

  const handleCheckout = async (plan: string) => {
    try {
      const res = await fetch(`${API}/billing/create-checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ plan }),
      })
      const data = await res.json()
      if (data.url) window.location.href = data.url
      else alert('Checkout not available — set up Stripe first.')
    } catch { alert('Could not start checkout.') }
  }

  const planColor = (plan: string) => {
    if (plan === 'professional') return '#3B82F6'
    if (plan === 'enterprise') return '#8B5CF6'
    if (plan === 'expired') return '#DC2626'
    return '#16A34A'
  }

  if (isLoading || !user) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><p style={{ color: '#9CA3AF' }}>Loading...</p></div>

  return (
    <div style={{ minHeight: '100vh', background: '#F8F7F5', fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif' }}>
      {/* Header */}
      <div style={{ background: '#1A2B4A', padding: '0 24px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Link href="/dashboard" style={{ color: 'rgba(255,255,255,.5)', fontSize: 13, textDecoration: 'none' }}>← Dashboard</Link>
            <span style={{ color: 'rgba(255,255,255,.2)' }}>·</span>
            <span style={{ color: 'white', fontSize: 13, fontWeight: 600 }}>Settings</span>
          </div>
          <span style={{ color: 'white', fontSize: 13, fontWeight: 700 }}>LexQuery</span>
        </div>
      </div>

      <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 20px' }}>

        {/* Plan & usage */}
        <div style={{ background: 'white', border: '1px solid #E2E0DB', borderRadius: 10, padding: 24, marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14, marginBottom: 24 }}>
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1A2B4A', marginBottom: 4 }}>Plan & usage</h2>
              {usage && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'white', background: planColor(usage.plan), borderRadius: 4, padding: '2px 10px', textTransform: 'capitalize' }}>
                    {usage.plan_label}
                  </span>
                  {usage.trial_days_left !== null && (
                    <span style={{ fontSize: 12, color: usage.trial_days_left < 3 ? '#DC2626' : '#D97706', fontWeight: 600 }}>
                      {usage.trial_days_left} day{usage.trial_days_left !== 1 ? 's' : ''} left in trial
                    </span>
                  )}
                  {usage.subscription_status === 'past_due' && (
                    <span style={{ fontSize: 12, color: '#DC2626', fontWeight: 600 }}>⚠ Payment overdue</span>
                  )}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {usage && usage.plan === 'trial' && (
                <>
                  <button onClick={() => handleCheckout('starter')} style={{ padding: '8px 14px', background: '#1A2B4A', color: 'white', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Upgrade to Starter</button>
                  <button onClick={() => handleCheckout('professional')} style={{ padding: '8px 14px', background: '#C9A84C', color: '#1A2B4A', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>Upgrade to Professional</button>
                </>
              )}
              {usage && usage.plan !== 'trial' && (
                <button onClick={handleBillingPortal} disabled={portalLoading} style={{ padding: '8px 14px', background: '#1A2B4A', color: 'white', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                  {portalLoading ? 'Loading...' : 'Manage billing'}
                </button>
              )}
            </div>
          </div>
          {usage ? (
            <div>
              <UsageBar label="Queries this month" used={usage.queries.used} limit={usage.queries.limit} />
              <UsageBar label="Pages indexed" used={usage.pages.used} limit={usage.pages.limit} />
              <UsageBar label="Team members" used={usage.seats.used} limit={usage.seats.limit} />
            </div>
          ) : (
            <p style={{ color: '#9CA3AF', fontSize: 13 }}>Loading usage...</p>
          )}
        </div>

        {/* Pricing cards */}
        {usage?.plan === 'trial' && (
          <div style={{ background: 'white', border: '1px solid #E2E0DB', borderRadius: 10, padding: 24, marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1A2B4A', marginBottom: 18 }}>Choose a plan</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))', gap: 14 }}>
              {[
                { key: 'starter', name: 'Starter', price: '£800', features: ['10 seats', '50k pages', '5k queries/month'] },
                { key: 'professional', name: 'Professional', price: '£3,500', features: ['100 seats', '500k pages', '50k queries/month', 'SSO'], highlight: true },
                { key: 'enterprise', name: 'Enterprise', price: 'Custom', features: ['Unlimited', 'Dedicated CSM', 'SLA'] },
              ].map(p => (
                <div key={p.key} style={{ border: `2px solid ${(p as any).highlight ? '#C9A84C' : '#E2E0DB'}`, borderRadius: 8, padding: 18, position: 'relative' }}>
                  {(p as any).highlight && <div style={{ position: 'absolute', top: -11, left: '50%', transform: 'translateX(-50%)', background: '#C9A84C', color: '#1A2B4A', fontSize: 10, fontWeight: 800, padding: '2px 12px', borderRadius: 20, whiteSpace: 'nowrap' }}>MOST POPULAR</div>}
                  <p style={{ fontSize: 13, fontWeight: 700, color: '#9CA3AF', marginBottom: 4 }}>{p.name}</p>
                  <p style={{ fontSize: 26, fontWeight: 700, color: '#1A2B4A', marginBottom: 12 }}>{p.price}<span style={{ fontSize: 13, color: '#9CA3AF' }}>{p.price !== 'Custom' ? '/mo' : ''}</span></p>
                  <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {p.features.map(f => <li key={f} style={{ fontSize: 12, color: '#6B7280', display: 'flex', gap: 6 }}><span style={{ color: '#16A34A' }}>✓</span>{f}</li>)}
                  </ul>
                  <button onClick={() => handleCheckout(p.key)} style={{ width: '100%', padding: '8px', background: '#1A2B4A', color: 'white', border: 'none', borderRadius: 5, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                    {p.key === 'enterprise' ? 'Contact sales' : 'Start plan'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Account info */}
        <div style={{ background: 'white', border: '1px solid #E2E0DB', borderRadius: 10, padding: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1A2B4A', marginBottom: 18 }}>Account</h2>
          <div style={{ display: 'grid', gap: 12 }}>
            {[
              { label: 'Email', value: user.email },
              { label: 'Role', value: user.role?.replace('_', ' ') },
            ].map(f => (
              <div key={f.label} style={{ display: 'flex', gap: 16, alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #F4F4F2' }}>
                <span style={{ fontSize: 13, color: '#9CA3AF', width: 80, flexShrink: 0 }}>{f.label}</span>
                <span style={{ fontSize: 13, color: '#1A202C', fontWeight: 500, textTransform: 'capitalize' }}>{f.value}</span>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 20 }}>
            <Link href="/dashboard/api-keys" style={{ fontSize: 13, color: '#1A2B4A', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid #E2E0DB', borderRadius: 6, padding: '8px 14px' }}>
              🔑 Manage API keys →
            </Link>
          </div>
        </div>

      </div>
    </div>
  )
}

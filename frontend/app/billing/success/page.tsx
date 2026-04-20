'use client'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Suspense } from 'react'

function SuccessContent() {
  const params = useSearchParams()
  const plan = params.get('plan') || 'your plan'
  const planLabel = plan.charAt(0).toUpperCase() + plan.slice(1)
  return (
    <div style={{ textAlign: 'center', maxWidth: 460, width: '100%' }}>
      <div style={{ width: 64, height: 64, background: '#F0FDF4', border: '2px solid #BBF7D0', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', fontSize: 28 }}>✓</div>
      <h1 style={{ fontSize: 26, fontWeight: 700, color: '#1A2B4A', marginBottom: 10 }}>You're on {planLabel}!</h1>
      <p style={{ fontSize: 15, color: '#6B7280', lineHeight: 1.65, marginBottom: 28 }}>
        Your subscription is now active. All features are unlocked and your usage limits have been updated.
      </p>
      <Link href="/dashboard" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '12px 24px', background: '#1A2B4A', color: 'white', borderRadius: 7, textDecoration: 'none', fontSize: 15, fontWeight: 700 }}>
        Go to dashboard →
      </Link>
      <p style={{ marginTop: 16, fontSize: 13, color: '#9CA3AF' }}>
        A receipt has been sent to your email.{' '}
        <Link href="/dashboard/settings" style={{ color: '#1A2B4A', fontWeight: 600 }}>Manage billing</Link>
      </p>
    </div>
  )
}

export default function BillingSuccessPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#F8F7F5', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif' }}>
      <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 40, textDecoration: 'none' }}>
        <div style={{ width: 28, height: 28, background: '#1A2B4A', borderRadius: 5, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span style={{ color: 'white', fontSize: 13, fontWeight: 700 }}>L</span></div>
        <span style={{ fontSize: 17, fontWeight: 700, color: '#1A2B4A' }}>LexQuery</span>
      </Link>
      <Suspense fallback={<p style={{ color: '#9CA3AF' }}>Loading...</p>}>
        <SuccessContent />
      </Suspense>
    </div>
  )
}

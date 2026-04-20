'use client'
import Link from 'next/link'

export default function BillingCancelledPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#F8F7F5', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif' }}>
      <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 40, textDecoration: 'none' }}>
        <div style={{ width: 28, height: 28, background: '#1A2B4A', borderRadius: 5, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span style={{ color: 'white', fontSize: 13, fontWeight: 700 }}>L</span></div>
        <span style={{ fontSize: 17, fontWeight: 700, color: '#1A2B4A' }}>LexQuery</span>
      </Link>
      <div style={{ textAlign: 'center', maxWidth: 440, width: '100%' }}>
        <div style={{ width: 64, height: 64, background: '#FEF2F2', border: '2px solid #FECACA', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', fontSize: 26 }}>×</div>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1A2B4A', marginBottom: 10 }}>Payment cancelled</h1>
        <p style={{ fontSize: 15, color: '#6B7280', lineHeight: 1.65, marginBottom: 28 }}>
          No charge was made. You can upgrade whenever you're ready — your trial continues in the meantime.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link href="/dashboard/settings" style={{ padding: '11px 22px', background: '#1A2B4A', color: 'white', borderRadius: 7, textDecoration: 'none', fontSize: 14, fontWeight: 700 }}>View plans</Link>
          <Link href="/dashboard" style={{ padding: '11px 22px', background: 'white', color: '#6B7280', border: '1px solid #E2E0DB', borderRadius: 7, textDecoration: 'none', fontSize: 14, fontWeight: 600 }}>Back to dashboard</Link>
        </div>
      </div>
    </div>
  )
}

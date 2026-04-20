'use client'
import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'

function InviteContent() {
  const params = useSearchParams()
  const token = params.get('token') || ''
  const router = useRouter()
  const { setToken } = useAuth()

  const [info, setInfo] = useState<{email:string;role:string;tenant_name:string}|null>(null)
  const [loadError, setLoadError] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!token) { setLoadError('Invalid invitation link.'); return }
    fetch(`${API}/users/invite/${token}`)
      .then(r => r.ok ? r.json() : r.json().then(d => { throw new Error(d.detail||'Invalid link') }))
      .then(setInfo)
      .catch(e => setLoadError(e.message))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setError(''); setLoading(true)
    try {
      const res = await fetch(`${API}/users/accept-invite`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, full_name: fullName, password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to accept invite')
      setToken(data.access_token)
      router.push('/dashboard')
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed') }
    finally { setLoading(false) }
  }

  const inp = {width:'100%',padding:'10px 12px',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,outline:'none',background:'#F8F7F5',boxSizing:'border-box' as const}

  if (loadError) return (
    <div style={{textAlign:'center'}}>
      <div style={{fontSize:32,marginBottom:12}}>⚠</div>
      <h2 style={{fontSize:18,fontWeight:700,color:'#1A2B4A',marginBottom:8}}>Invalid invitation</h2>
      <p style={{fontSize:14,color:'#6B7280',marginBottom:20}}>{loadError}</p>
      <Link href="/login" style={{fontSize:14,color:'#1A2B4A',fontWeight:600}}>Go to sign in</Link>
    </div>
  )

  if (!info) return <p style={{textAlign:'center',color:'#9CA3AF',fontSize:14}}>Loading invitation...</p>

  return (
    <form onSubmit={handleSubmit}>
      <div style={{background:'#F0F7FF',border:'1px solid #BFDBFE',borderRadius:8,padding:'12px 14px',marginBottom:22}}>
        <p style={{fontSize:13,color:'#1E40AF',margin:'0 0 2px',fontWeight:600}}>Joining {info.tenant_name}</p>
        <p style={{fontSize:12,color:'#3B82F6',margin:0}}>As {info.role.replace('_',' ')} · {info.email}</p>
      </div>
      <h1 style={{fontSize:18,fontWeight:700,color:'#1A2B4A',marginBottom:4}}>Accept your invitation</h1>
      <p style={{fontSize:13,color:'#9CA3AF',marginBottom:22}}>Set your name and a password to get started.</p>
      <div style={{marginBottom:14}}>
        <label style={{display:'block',fontSize:13,fontWeight:600,color:'#374151',marginBottom:5}}>Full name</label>
        <input type="text" value={fullName} onChange={e=>setFullName(e.target.value)} placeholder="Sarah Chen" style={inp}/>
      </div>
      <div style={{marginBottom:14}}>
        <label style={{display:'block',fontSize:13,fontWeight:600,color:'#374151',marginBottom:5}}>Password</label>
        <input type="password" required value={password} onChange={e=>setPassword(e.target.value)} placeholder="Minimum 8 characters" minLength={8} style={inp}/>
      </div>
      <div style={{marginBottom:22}}>
        <label style={{display:'block',fontSize:13,fontWeight:600,color:'#374151',marginBottom:5}}>Confirm password</label>
        <input type="password" required value={confirm} onChange={e=>setConfirm(e.target.value)} placeholder="Re-enter password" style={inp}/>
      </div>
      {error&&<div style={{background:'#FEF2F2',border:'1px solid #FECACA',borderRadius:6,padding:'10px 12px',fontSize:13,color:'#DC2626',marginBottom:14}}>{error}</div>}
      <button type="submit" disabled={loading} style={{width:'100%',padding:11,background:loading?'#9CA3AF':'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:loading?'not-allowed':'pointer'}}>
        {loading?'Creating account...':'Create account & join'}
      </button>
    </form>
  )
}

export default function InvitePage() {
  return (
    <div style={{minHeight:'100vh',background:'#F8F7F5',display:'flex',alignItems:'center',justifyContent:'center',padding:'24px 16px',fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'}}>
      <div style={{width:'100%',maxWidth:420}}>
        <div style={{textAlign:'center',marginBottom:28}}>
          <Link href="/" style={{textDecoration:'none',display:'inline-flex',alignItems:'center',gap:10}}>
            <div style={{width:30,height:30,background:'#1A2B4A',borderRadius:6,display:'flex',alignItems:'center',justifyContent:'center'}}><span style={{color:'white',fontSize:14,fontWeight:700}}>L</span></div>
            <span style={{fontSize:18,fontWeight:700,color:'#1A2B4A'}}>LexQuery</span>
          </Link>
        </div>
        <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:10,padding:'28px 24px'}}>
          <Suspense fallback={<p style={{color:'#9CA3AF',fontSize:14,textAlign:'center'}}>Loading...</p>}>
            <InviteContent/>
          </Suspense>
        </div>
      </div>
    </div>
  )
}

'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
const inp = {width:'100%',padding:'10px 12px',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,color:'#1A202C',background:'#F8F7F5',outline:'none',boxSizing:'border-box' as const}
const lbl = {display:'block',fontSize:13,fontWeight:600,color:'#374151',marginBottom:6} as const
type Step = 'org'|'account'|'verify'|'totp'

export default function SignupPage() {
  const [step,setStep]=useState<Step>('org')
  const [tenantName,setTenantName]=useState('')
  const [tenantSlug,setTenantSlug]=useState('')
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [fullName,setFullName]=useState('')
  const [userId,setUserId]=useState('')
  const [verifyCode,setVerifyCode]=useState('')
  const [totpQr,setTotpQr]=useState('')
  const [totpSecret,setTotpSecret]=useState('')
  const [totpCode,setTotpCode]=useState('')
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(false)
  const {setToken}=useAuth()
  const router=useRouter()

  const slugify=(n:string)=>n.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')
  const steps=['Organisation','Account','Verify email','2FA (optional)']
  const stepIdx={org:0,account:1,verify:2,totp:3}[step]

  const handleRegister=async(e:React.FormEvent)=>{
    e.preventDefault();setError('');setLoading(true)
    try{
      const res=await fetch(`${API}/auth/register`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tenant_name:tenantName,tenant_slug:tenantSlug,email,password,full_name:fullName})})
      const data=await res.json()
      if(!res.ok) throw new Error(data.detail||'Registration failed')
      setUserId(data.user_id);setStep('verify')
    }catch(e:unknown){setError(e instanceof Error?e.message:'Registration failed')}
    finally{setLoading(false)}
  }

  const handleVerify=async(e:React.FormEvent)=>{
    e.preventDefault();setError('');setLoading(true)
    try{
      const res=await fetch(`${API}/auth/verify-email`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:userId,code:verifyCode})})
      const data=await res.json()
      if(!res.ok) throw new Error(data.detail||'Verification failed')
      setToken(data.access_token);setStep('totp')
    }catch(e:unknown){setError(e instanceof Error?e.message:'Verification failed')}
    finally{setLoading(false)}
  }

  const handleSetupTotp=async()=>{
    setLoading(true)
    try{
      const token=localStorage.getItem('lexquery_token')
      const res=await fetch(`${API}/auth/totp/setup`,{headers:{Authorization:`Bearer ${token}`}})
      const data=await res.json()
      setTotpQr(data.qr_code_base64);setTotpSecret(data.secret)
    }catch{}finally{setLoading(false)}
  }

  const handleEnableTotp=async(e:React.FormEvent)=>{
    e.preventDefault();setError('');setLoading(true)
    try{
      const token=localStorage.getItem('lexquery_token')
      const res=await fetch(`${API}/auth/totp/enable`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:JSON.stringify({code:totpCode})})
      const data=await res.json()
      if(!res.ok) throw new Error(data.detail||'Invalid code')
      router.push('/dashboard')
    }catch(e:unknown){setError(e instanceof Error?e.message:'Invalid code')}
    finally{setLoading(false)}
  }

  return(
    <div style={{minHeight:'100vh',background:'#F8F7F5',display:'flex',alignItems:'center',justifyContent:'center',padding:'24px 16px',fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'}}>
      <div style={{width:'100%',maxWidth:460}}>
        <div style={{textAlign:'center',marginBottom:22}}>
          <Link href="/" style={{textDecoration:'none',display:'inline-flex',alignItems:'center',gap:10}}>
            <div style={{width:30,height:30,background:'#1A2B4A',borderRadius:6,display:'flex',alignItems:'center',justifyContent:'center'}}><span style={{color:'white',fontSize:14,fontWeight:700}}>L</span></div>
            <span style={{fontSize:18,fontWeight:700,color:'#1A2B4A'}}>LexQuery</span>
          </Link>
        </div>
        <div style={{display:'flex',gap:5,marginBottom:18}}>
          {steps.map((s,i)=>(
            <div key={s} style={{flex:1}}>
              <div style={{height:3,borderRadius:2,background:i<=stepIdx?'#1A2B4A':'#E2E0DB',marginBottom:4,transition:'background .2s'}}/>
              <p style={{fontSize:10,fontWeight:600,color:i<=stepIdx?'#1A2B4A':'#9CA3AF',margin:0,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s}</p>
            </div>
          ))}
        </div>
        <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:10,padding:'26px 22px'}}>
          {step==='org'&&(
            <form onSubmit={e=>{e.preventDefault();setStep('account')}}>
              <h1 style={{fontSize:18,fontWeight:700,color:'#1A2B4A',marginBottom:4}}>Set up your organisation</h1>
              <p style={{fontSize:13,color:'#9CA3AF',marginBottom:20}}>This will be your LexQuery workspace.</p>
              <div style={{marginBottom:14}}>
                <label style={lbl}>Organisation name</label>
                <input type="text" required value={tenantName} onChange={e=>{setTenantName(e.target.value);setTenantSlug(slugify(e.target.value))}} placeholder="Chambers & Partners LLP" style={inp}/>
              </div>
              <div style={{marginBottom:22}}>
                <label style={lbl}>Workspace identifier</label>
                <div style={{display:'flex',border:'1px solid #E2E0DB',borderRadius:6,overflow:'hidden'}}>
                  <span style={{padding:'10px',background:'#F8F7F5',fontSize:12,color:'#9CA3AF',borderRight:'1px solid #E2E0DB',whiteSpace:'nowrap'}}>lexquery.com/</span>
                  <input type="text" required value={tenantSlug} onChange={e=>setTenantSlug(e.target.value)} placeholder="chambers-partners" style={{flex:1,padding:'10px 12px',border:'none',fontSize:14,color:'#1A202C',background:'white',outline:'none'}}/>
                </div>
                <p style={{fontSize:11,color:'#9CA3AF',marginTop:4}}>Lowercase letters, numbers and hyphens only</p>
              </div>
              <button type="submit" style={{width:'100%',padding:11,background:'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:'pointer'}}>Continue</button>
            </form>
          )}
          {step==='account'&&(
            <form onSubmit={handleRegister}>
              <h1 style={{fontSize:18,fontWeight:700,color:'#1A2B4A',marginBottom:4}}>Create your admin account</h1>
              <p style={{fontSize:13,color:'#9CA3AF',marginBottom:20}}>You'll be the Tenant Admin for <strong style={{color:'#374151'}}>{tenantName}</strong>.</p>
              <div style={{marginBottom:12}}>
                <label style={lbl}>Full name</label>
                <input type="text" value={fullName} onChange={e=>setFullName(e.target.value)} placeholder="Sarah Chen" style={inp}/>
              </div>
              <div style={{marginBottom:12}}>
                <label style={lbl}>Work email</label>
                <input type="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="sarah@firm.com" style={inp}/>
              </div>
              <div style={{marginBottom:18}}>
                <label style={lbl}>Password</label>
                <input type="password" required value={password} onChange={e=>setPassword(e.target.value)} placeholder="Minimum 8 characters" minLength={8} style={inp}/>
              </div>
              <div style={{background:'#F8F7F5',border:'1px solid #E2E0DB',borderRadius:6,padding:12,marginBottom:18}}>
                <p style={{fontSize:12,color:'#6B7280',margin:'0 0 8px',fontWeight:600}}>Or continue with</p>
                <div style={{display:'flex',gap:8}}>
                  {['Google','Microsoft'].map(p=>(
                    <button key={p} type="button" onClick={()=>{if(p==='Google')window.location.href='http://localhost:8000/v1/auth/google/login';else alert('Microsoft OAuth coming soon')}} style={{flex:1,padding:9,border:'1px solid #E2E0DB',borderRadius:5,background:'white',fontSize:13,color:'#374151',cursor:'pointer',fontWeight:500}}>
                      {p==='Google'?'G':'M'} {p}
                    </button>
                  ))}
                </div>
              </div>
              {error&&<div style={{background:'#FEF2F2',border:'1px solid #FECACA',borderRadius:6,padding:'10px 12px',fontSize:13,color:'#DC2626',marginBottom:12}}>{error}</div>}
              <div style={{display:'flex',gap:8}}>
                <button type="button" onClick={()=>setStep('org')} style={{padding:'11px 14px',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,color:'#6B7280',background:'white',cursor:'pointer'}}>Back</button>
                <button type="submit" disabled={loading} style={{flex:1,padding:11,background:loading?'#9CA3AF':'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:loading?'not-allowed':'pointer'}}>
                  {loading?'Creating account...':'Create account'}
                </button>
              </div>
            </form>
          )}
          {step==='verify'&&(
            <form onSubmit={handleVerify}>
              <h1 style={{fontSize:18,fontWeight:700,color:'#1A2B4A',marginBottom:4}}>Check your email</h1>
              <p style={{fontSize:13,color:'#6B7280',marginBottom:8,lineHeight:1.6}}>We sent a 6-digit verification code to <strong style={{color:'#374151'}}>{email}</strong>.</p>
              <p style={{fontSize:12,color:'#9CA3AF',marginBottom:20}}>Check your inbox and spam folder. The code expires in 10 minutes.</p>
              <div style={{marginBottom:20}}>
                <label style={lbl}>Verification code</label>
                <input type="text" required value={verifyCode} onChange={e=>setVerifyCode(e.target.value.replace(/\D/g,'').slice(0,6))} placeholder="000000" maxLength={6} style={{...inp,fontSize:28,fontWeight:700,textAlign:'center',letterSpacing:8}}/>
              </div>
              {error&&<div style={{background:'#FEF2F2',border:'1px solid #FECACA',borderRadius:6,padding:'10px 12px',fontSize:13,color:'#DC2626',marginBottom:12}}>{error}</div>}
              <button type="submit" disabled={loading||verifyCode.length!==6} style={{width:'100%',padding:11,background:(loading||verifyCode.length!==6)?'#9CA3AF':'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:(loading||verifyCode.length!==6)?'not-allowed':'pointer'}}>
                {loading?'Verifying...':'Verify email'}
              </button>
            </form>
          )}
          {step==='totp'&&(
            <div>
              <h1 style={{fontSize:18,fontWeight:700,color:'#1A2B4A',marginBottom:4}}>Two-factor authentication</h1>
              <p style={{fontSize:13,color:'#6B7280',marginBottom:20,lineHeight:1.6}}>Add an extra layer of security. Use Google Authenticator, Authy, or 1Password.</p>
              {!totpQr?(
                <>
                  <button onClick={handleSetupTotp} disabled={loading} style={{width:'100%',padding:11,background:'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:'pointer',marginBottom:10}}>{loading?'Generating...':'Set up authenticator app'}</button>
                  <button onClick={()=>router.push('/dashboard')} style={{width:'100%',padding:11,background:'white',color:'#6B7280',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,cursor:'pointer'}}>Skip for now</button>
                </>
              ):(
                <form onSubmit={handleEnableTotp}>
                  <div style={{textAlign:'center',marginBottom:18}}>
                    <img src={`data:image/png;base64,${totpQr}`} alt="QR Code" style={{width:160,height:160,border:'1px solid #E2E0DB',borderRadius:8,padding:6,background:'white'}}/>
                    <p style={{fontSize:11,color:'#9CA3AF',marginTop:8}}>Scan with your authenticator app</p>
                    <div style={{background:'#F8F7F5',border:'1px solid #E2E0DB',borderRadius:4,padding:'5px 10px',display:'inline-block',marginTop:4}}>
                      <code style={{fontSize:11,color:'#374151',letterSpacing:1}}>{totpSecret}</code>
                    </div>
                  </div>
                  <div style={{marginBottom:12}}>
                    <label style={lbl}>Enter the 6-digit code from your app</label>
                    <input type="text" required value={totpCode} onChange={e=>setTotpCode(e.target.value.replace(/\D/g,'').slice(0,6))} placeholder="000000" maxLength={6} style={{...inp,fontSize:24,fontWeight:700,textAlign:'center',letterSpacing:6}}/>
                  </div>
                  {error&&<div style={{background:'#FEF2F2',border:'1px solid #FECACA',borderRadius:6,padding:'10px 12px',fontSize:13,color:'#DC2626',marginBottom:12}}>{error}</div>}
                  <button type="submit" disabled={loading||totpCode.length!==6} style={{width:'100%',padding:11,background:(loading||totpCode.length!==6)?'#9CA3AF':'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:(loading||totpCode.length!==6)?'not-allowed':'pointer',marginBottom:8}}>
                    {loading?'Enabling...':'Enable 2FA'}
                  </button>
                  <button type="button" onClick={()=>router.push('/dashboard')} style={{width:'100%',padding:11,background:'white',color:'#6B7280',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,cursor:'pointer'}}>Skip for now</button>
                </form>
              )}
            </div>
          )}
        </div>
        {step!=='verify'&&step!=='totp'&&(
          <p style={{textAlign:'center',marginTop:14,fontSize:13,color:'#9CA3AF'}}>
            Already have an account?{' '}<Link href="/login" style={{color:'#1A2B4A',fontWeight:700}}>Sign in</Link>
          </p>
        )}
      </div>
    </div>
  )
}

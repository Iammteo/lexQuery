'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('lexquery_token') : null

type User = { id:string; email:string; full_name:string|null; role:string; is_active:boolean; email_verified:boolean }

const ROLES = [
  { value:'viewer', label:'Viewer', desc:'Can query documents. Cannot upload or delete.' },
  { value:'editor', label:'Editor', desc:'Can upload and delete documents.' },
  { value:'matter_admin', label:'Matter Admin', desc:'Can manage workspaces.' },
  { value:'tenant_admin', label:'Tenant Admin', desc:'Full access including this admin panel.' },
]

function RoleBadge({role}:{role:string}) {
  const colors:Record<string,string> = { viewer:'#9CA3AF', editor:'#6B7280', matter_admin:'#3B82F6', tenant_admin:'#1A2B4A' }
  return <span style={{fontSize:11,fontWeight:600,color:'white',background:colors[role]||'#9CA3AF',borderRadius:4,padding:'2px 7px',whiteSpace:'nowrap'}}>{role.replace('_',' ')}</span>
}

export default function AdminPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('viewer')
  const [inviting, setInviting] = useState(false)
  const [inviteMsg, setInviteMsg] = useState('')
  const [inviteError, setInviteError] = useState('')
  const [updatingRole, setUpdatingRole] = useState<string|null>(null)
  const [togglingUser, setTogglingUser] = useState<string|null>(null)
  const [showInvite, setShowInvite] = useState(false)

  useEffect(() => {
    if (!isLoading && !user) { router.push('/login'); return }
    if (!isLoading && user?.role !== 'tenant_admin') { router.push('/dashboard'); return }
  }, [user, isLoading, router])

  useEffect(() => {
    if (!user || user.role !== 'tenant_admin') return
    fetchUsers()
  }, [user])

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API}/users`, { headers: { Authorization: `Bearer ${getToken()}` } })
      if (res.ok) setUsers(await res.json())
    } catch {} finally { setLoading(false) }
  }

  const handleRoleChange = async (userId: string, newRole: string) => {
    setUpdatingRole(userId)
    try {
      const res = await fetch(`${API}/users/${userId}/role`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ role: newRole }),
      })
      if (res.ok) setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
    } catch {} finally { setUpdatingRole(null) }
  }

  const handleToggleActive = async (u: User) => {
    setTogglingUser(u.id)
    const endpoint = u.is_active ? 'deactivate' : 'activate'
    try {
      const res = await fetch(`${API}/users/${u.id}/${endpoint}`, {
        method: 'PATCH', headers: { Authorization: `Bearer ${getToken()}` },
      })
      if (res.ok) setUsers(prev => prev.map(usr => usr.id === u.id ? { ...usr, is_active: !usr.is_active } : usr))
    } catch {} finally { setTogglingUser(null) }
  }

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault(); setInviteMsg(''); setInviteError(''); setInviting(true)
    try {
      const res = await fetch(`${API}/users/invite`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Invite failed')
      setInviteMsg(`Invitation sent to ${inviteEmail}`)
      setInviteEmail(''); setShowInvite(false)
    } catch (e: unknown) { setInviteError(e instanceof Error ? e.message : 'Failed to send invite') }
    finally { setInviting(false) }
  }

  const handleExportAudit = () => {
    const token = getToken()
    const url = `${API}/audit/export`
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.blob())
      .then(blob => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = 'audit_logs.csv'
        a.click()
      })
      .catch(() => alert('Failed to export audit logs'))
  }

  if (isLoading || !user) return <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center'}}><p style={{color:'#9CA3AF'}}>Loading...</p></div>

  return (
    <div style={{minHeight:'100vh',background:'#F8F7F5',fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'}}>
      {/* Header */}
      <div style={{background:'#1A2B4A',padding:'0 24px'}}>
        <div style={{maxWidth:1000,margin:'0 auto',display:'flex',alignItems:'center',justifyContent:'space-between',height:56}}>
          <div style={{display:'flex',alignItems:'center',gap:16}}>
            <Link href="/dashboard" style={{color:'rgba(255,255,255,.5)',fontSize:13,textDecoration:'none',display:'flex',alignItems:'center',gap:6}}>
              {'<-'} Dashboard
            </Link>
            <span style={{color:'rgba(255,255,255,.2)'}}>·</span>
            <span style={{color:'white',fontSize:13,fontWeight:600}}>Admin Panel</span>
          </div>
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <div style={{width:22,height:22,background:'rgba(255,255,255,.15)',borderRadius:4,display:'flex',alignItems:'center',justifyContent:'center'}}><span style={{color:'white',fontSize:10,fontWeight:700}}>L</span></div>
            <span style={{color:'white',fontSize:13,fontWeight:600}}>LexQuery</span>
          </div>
        </div>
      </div>

      <div style={{maxWidth:1000,margin:'0 auto',padding:'28px 20px'}}>

        {/* Page header */}
        <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:28,flexWrap:'wrap',gap:14}}>
          <div>
            <h1 style={{fontSize:22,fontWeight:700,color:'#1A2B4A',marginBottom:4}}>Team members</h1>
            <p style={{fontSize:14,color:'#9CA3AF',margin:0}}>{users.length} member{users.length!==1?'s':''} in your organisation</p>
          </div>
          <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
            <button
              onClick={handleExportAudit}
              style={{padding:'9px 18px',background:'white',color:'#1A2B4A',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,fontWeight:600,cursor:'pointer'}}
            >
              Export audit CSV
            </button>
            <button onClick={()=>setShowInvite(!showInvite)} style={{padding:'9px 18px',background:'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:'pointer'}}>
              + Invite member
            </button>
          </div>
        </div>

        {/* Invite form */}
        {showInvite && (
          <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:10,padding:20,marginBottom:20}}>
            <h3 style={{fontSize:15,fontWeight:600,color:'#1A2B4A',marginBottom:4}}>Invite a team member</h3>
            <p style={{fontSize:13,color:'#9CA3AF',marginBottom:18}}>They will receive an email with a link to set their password and join your workspace.</p>
            <form onSubmit={handleInvite}>
              <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:12,marginBottom:14}}>
                <div>
                  <label style={{display:'block',fontSize:13,fontWeight:600,color:'#374151',marginBottom:5}}>Email address</label>
                  <input type="email" required value={inviteEmail} onChange={e=>setInviteEmail(e.target.value)} placeholder="colleague@firm.com" style={{width:'100%',padding:'9px 12px',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,outline:'none',boxSizing:'border-box' as const}}/>
                </div>
                <div>
                  <label style={{display:'block',fontSize:13,fontWeight:600,color:'#374151',marginBottom:5}}>Role</label>
                  <select value={inviteRole} onChange={e=>setInviteRole(e.target.value)} style={{width:'100%',padding:'9px 12px',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,outline:'none',background:'white',boxSizing:'border-box' as const}}>
                    {ROLES.map(r=><option key={r.value} value={r.value}>{r.label} — {r.desc}</option>)}
                  </select>
                </div>
              </div>
              {inviteError&&<div style={{background:'#FEF2F2',border:'1px solid #FECACA',borderRadius:6,padding:'8px 12px',fontSize:13,color:'#DC2626',marginBottom:12}}>{inviteError}</div>}
              <div style={{display:'flex',gap:8}}>
                <button type="submit" disabled={inviting} style={{padding:'9px 18px',background:inviting?'#9CA3AF':'#1A2B4A',color:'white',border:'none',borderRadius:6,fontSize:14,fontWeight:700,cursor:inviting?'not-allowed':'pointer'}}>
                  {inviting?'Sending...':'Send invitation'}
                </button>
                <button type="button" onClick={()=>setShowInvite(false)} style={{padding:'9px 16px',background:'white',color:'#6B7280',border:'1px solid #E2E0DB',borderRadius:6,fontSize:14,cursor:'pointer'}}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {inviteMsg && <div style={{background:'#F0FDF4',border:'1px solid #BBF7D0',borderRadius:8,padding:'10px 14px',fontSize:13,color:'#166534',marginBottom:20}}>Invitation sent to {inviteMsg.replace('Invitation sent to ','')}</div>}

        {/* Role guide */}
        <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:10,padding:18,marginBottom:20}}>
          <p style={{fontSize:13,fontWeight:600,color:'#374151',marginBottom:10}}>Role permissions</p>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(160px,1fr))',gap:10}}>
            {ROLES.map(r=>(
              <div key={r.value} style={{padding:'10px 12px',background:'#F8F7F5',borderRadius:6,border:'1px solid #E2E0DB'}}>
                <RoleBadge role={r.value}/>
                <p style={{fontSize:12,color:'#6B7280',margin:'6px 0 0',lineHeight:1.4}}>{r.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Users table */}
        <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:10,overflow:'hidden'}}>
          {loading ? (
            <div style={{padding:40,textAlign:'center',color:'#9CA3AF',fontSize:13}}>Loading team members...</div>
          ) : users.length === 0 ? (
            <div style={{padding:40,textAlign:'center',color:'#9CA3AF',fontSize:13}}>No team members yet. Invite someone above.</div>
          ) : (
            <div style={{overflowX:'auto'}}>
              <table style={{width:'100%',borderCollapse:'collapse',minWidth:600}}>
                <thead>
                  <tr style={{borderBottom:'1px solid #E2E0DB',background:'#F8F7F5'}}>
                    {['Member','Role','Status','Actions'].map(h=>(
                      <th key={h} style={{padding:'10px 16px',textAlign:'left',fontSize:11,fontWeight:700,color:'#9CA3AF',letterSpacing:'.5px',textTransform:'uppercase',whiteSpace:'nowrap'}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u,i)=>(
                    <tr key={u.id} style={{borderBottom:i<users.length-1?'1px solid #E2E0DB':'none',opacity:u.is_active?1:.6}}>
                      <td style={{padding:'14px 16px'}}>
                        <p style={{fontSize:14,fontWeight:600,color:'#1A202C',margin:'0 0 2px'}}>{u.full_name||'—'}</p>
                        <p style={{fontSize:12,color:'#9CA3AF',margin:0}}>{u.email}</p>
                        {!u.email_verified&&<span style={{fontSize:10,color:'#D97706',background:'#FFFBEB',border:'1px solid #FDE68A',borderRadius:3,padding:'1px 5px',display:'inline-block',marginTop:3}}>Pending verification</span>}
                      </td>
                      <td style={{padding:'14px 16px'}}>
                        {u.id===user?.id ? (
                          <RoleBadge role={u.role}/>
                        ) : (
                          <select value={u.role} onChange={e=>handleRoleChange(u.id,e.target.value)} disabled={updatingRole===u.id} style={{padding:'5px 8px',border:'1px solid #E2E0DB',borderRadius:5,fontSize:13,background:'white',cursor:'pointer',outline:'none'}}>
                            {ROLES.map(r=><option key={r.value} value={r.value}>{r.label}</option>)}
                          </select>
                        )}
                        {updatingRole===u.id&&<span style={{fontSize:11,color:'#9CA3AF',marginLeft:6}}>Saving...</span>}
                      </td>
                      <td style={{padding:'14px 16px'}}>
                        <span style={{fontSize:12,fontWeight:600,color:u.is_active?'#16A34A':'#DC2626',background:u.is_active?'#F0FDF4':'#FEF2F2',border:`1px solid ${u.is_active?'#BBF7D0':'#FECACA'}`,borderRadius:4,padding:'2px 8px'}}>
                          {u.is_active?'Active':'Deactivated'}
                        </span>
                      </td>
                      <td style={{padding:'14px 16px'}}>
                        {u.id!==user?.id&&(
                          <button onClick={()=>handleToggleActive(u)} disabled={togglingUser===u.id} style={{fontSize:12,color:u.is_active?'#DC2626':'#16A34A',background:'none',border:'none',cursor:'pointer',fontWeight:600,padding:0}}>
                            {togglingUser===u.id?'...':(u.is_active?'Deactivate':'Reactivate')}
                          </button>
                        )}
                        {u.id===user?.id&&<span style={{fontSize:12,color:'#9CA3AF'}}>You</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
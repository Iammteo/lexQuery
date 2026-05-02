'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/lib/auth-context'
import { listWorkspaces, createWorkspace, submitQuery, uploadDocument, getDocument, Workspace, QueryResponse, Document } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1'
const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('lexquery_token') : null
const ACTIVE_WS_KEY = 'lexquery_active_workspace'

function StatusDot({status}:{status:string}) {
  const c = status==='indexed'?'#16A34A':status==='failed'?'#DC2626':status==='processing'?'#D97706':'#9CA3AF'
  return <span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:c,marginRight:5,flexShrink:0}}/>
}

function renderAnswer(text:string) {
  return text.split(/(\*\*[^*]+\*\*|\[[0-9]+\])/).map((part,i)=>{
    if(part.startsWith('**')&&part.endsWith('**')) return <strong key={i}>{part.slice(2,-2)}</strong>
    if(/^\[[0-9]+\]$/.test(part)) return <sup key={i} style={{color:'#C9A84C',fontWeight:700,fontSize:10}}>{part}</sup>
    return part
  })
}

function AnswerBlock({result}:{result:QueryResponse&{streamingText?:string}}) {
  const text = result.streamingText!==undefined?result.streamingText:result.answer
  const conf = result.confidence_label
  const cc = conf==='High'?'#16A34A':conf==='Medium'?'#D97706':'#DC2626'
  return (
    <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:8,padding:'16px 18px',marginBottom:12}}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:10,gap:12,flexWrap:'wrap'}}>
        <p style={{fontSize:13,color:'#9CA3AF',fontStyle:'italic',margin:0,flex:1}}>&ldquo;{result.query}&rdquo;</p>
        {result.confidence_score>0&&<span style={{fontSize:11,fontWeight:700,color:cc,border:`1px solid ${cc}`,borderRadius:4,padding:'2px 7px',whiteSpace:'nowrap',flexShrink:0}}>{conf} · {Math.round(result.confidence_score*100)}%</span>}
      </div>
      <div style={{fontSize:14,lineHeight:1.75,color:'#1A202C',whiteSpace:'pre-wrap'}}>{renderAnswer(text)}</div>
      {result.citations&&result.citations.length>0&&(
        <div style={{marginTop:12,borderTop:'1px solid #E2E0DB',paddingTop:12}}>
          <p style={{fontSize:10,fontWeight:700,color:'#9CA3AF',marginBottom:8,letterSpacing:'.5px',textTransform:'uppercase'}}>Sources</p>
          {result.citations.map(c=>(
            <div key={c.citation_number} style={{display:'flex',gap:8,marginBottom:6,fontSize:12,color:'#6B7280',alignItems:'flex-start'}}>
              <span style={{minWidth:18,height:18,background:'#1A2B4A',color:'white',borderRadius:3,display:'flex',alignItems:'center',justifyContent:'center',fontSize:10,fontWeight:700,flexShrink:0}}>{c.citation_number}</span>
              <div style={{minWidth:0}}>
                <span style={{fontWeight:500,color:'#374151'}}>{c.filename}</span>{' '}· Page {c.page_number}
                <p style={{margin:'2px 0 0',color:'#9CA3AF',fontSize:11,lineHeight:1.5,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{c.excerpt.slice(0,120)}…</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function EmptyState({hasWorkspace,docCount}:{hasWorkspace:boolean,docCount:number}) {
  if (!hasWorkspace) return (
    <div style={{textAlign:'center',padding:'4rem 1rem'}}>
      <div style={{width:52,height:52,background:'#F4F4F2',borderRadius:12,display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 16px',fontSize:24}}>📁</div>
      <h3 style={{fontSize:17,fontWeight:600,color:'#374151',marginBottom:8}}>No workspace selected</h3>
      <p style={{fontSize:14,color:'#9CA3AF',maxWidth:300,margin:'0 auto'}}>Create a workspace in the sidebar to organise your documents and start querying.</p>
    </div>
  )
  if (docCount === 0) return (
    <div style={{maxWidth:560,margin:'4rem auto',padding:'0 1rem'}}>
      <h3 style={{fontSize:17,fontWeight:600,color:'#374151',marginBottom:20,textAlign:'center'}}>Get started in three steps</h3>
      <div style={{display:'flex',flexDirection:'column',gap:12}}>
        {[
          {n:'1',icon:'📄',title:'Upload a document',desc:'Click the + button below and choose "Upload files". Supports PDF, Word (.docx), and plain text files.'},
          {n:'2',icon:'⏳',title:'Wait for indexing',desc:'Documents are automatically parsed and indexed. This usually takes under a minute. The status dot turns green when ready.'},
          {n:'3',icon:'💬',title:'Ask a question',desc:'Type your question in the box below. LexQuery will return a cited answer grounded in your uploaded documents.'},
        ].map(step=>(
          <div key={step.n} style={{background:'white',border:'1px solid #E2E0DB',borderRadius:8,padding:'14px 16px',display:'flex',gap:14,alignItems:'flex-start'}}>
            <div style={{width:32,height:32,background:'#1A2B4A',borderRadius:6,display:'flex',alignItems:'center',justifyContent:'center',color:'white',fontSize:13,fontWeight:700,flexShrink:0}}>{step.n}</div>
            <div>
              <p style={{fontSize:14,fontWeight:600,color:'#1A2B4A',margin:'0 0 4px'}}>{step.title}</p>
              <p style={{fontSize:13,color:'#6B7280',margin:0,lineHeight:1.55}}>{step.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
  return (
    <div style={{textAlign:'center',padding:'4rem 1rem'}}>
      <div style={{width:52,height:52,background:'#F4F4F2',borderRadius:12,display:'flex',alignItems:'center',justifyContent:'center',margin:'0 auto 16px',fontSize:24}}>⚖</div>
      <h3 style={{fontSize:17,fontWeight:600,color:'#374151',marginBottom:8}}>{docCount} document{docCount!==1?'s':''} indexed</h3>
      <p style={{fontSize:14,color:'#9CA3AF',maxWidth:320,margin:'0 auto'}}>Ask a question below. LexQuery will search your documents and return a cited answer.</p>
    </div>
  )
}

export default function DashboardPage() {
  const {user,isLoading,logout}=useAuth()
  const router=useRouter()
  const [workspaces,setWorkspaces]=useState<Workspace[]>([])
  const [activeWs,setActiveWs]=useState<Workspace|null>(null)
  const [results,setResults]=useState<(QueryResponse&{streamingText?:string})[]>([])
  const [query,setQuery]=useState('')
  const [querying,setQuerying]=useState(false)
  const [queryError,setQueryError]=useState('')
  const [uploading,setUploading]=useState(false)
  const [uploadMsg,setUploadMsg]=useState('')
  const [documents,setDocuments]=useState<Document[]>([])
  const [docsLoading,setDocsLoading]=useState(false)
  const [showNewWs,setShowNewWs]=useState(false)
  const [newWsName,setNewWsName]=useState('')
  const [deletingDoc,setDeletingDoc]=useState<string|null>(null)
  const [sidebarOpen,setSidebarOpen]=useState(false)
  const [showQuickActions,setShowQuickActions]=useState(false)
  const [showUrlQuick,setShowUrlQuick]=useState(false)
  const [urlQuickInput,setUrlQuickInput]=useState('')
  const [urlLoading,setUrlLoading]=useState(false)
  const fileRef=useRef<HTMLInputElement>(null)
  const bottomRef=useRef<HTMLDivElement>(null)

  useEffect(()=>{ if(!isLoading&&!user) router.push('/login') },[user,isLoading,router])

  useEffect(()=>{
    if(!user) return
    listWorkspaces().then(ws=>{
      setWorkspaces(ws)
      if(ws.length>0){
        const savedId = localStorage.getItem(ACTIVE_WS_KEY)
        const saved = savedId ? ws.find(w=>w.id===savedId) : null
        setActiveWs(saved||ws[0])
      }
    })
  },[user])

  const fetchDocs = useCallback(async(wsId:string)=>{
    setDocsLoading(true)
    try {
      const res = await fetch(`${API}/documents?workspace_id=${wsId}`,{headers:{Authorization:`Bearer ${getToken()}`}})
      if(res.ok) setDocuments(await res.json())
    } catch {} finally { setDocsLoading(false) }
  },[])

  useEffect(()=>{
    if(!activeWs) return
    localStorage.setItem(ACTIVE_WS_KEY,activeWs.id)
    fetchDocs(activeWs.id)
    setResults([])
  },[activeWs,fetchDocs])

  useEffect(()=>{ bottomRef.current?.scrollIntoView({behavior:'smooth'}) },[results])

  useEffect(()=>{
    if(!showQuickActions) return
    const close=(e:MouseEvent)=>{
      const target=e.target as HTMLElement
      if(!target.closest('[data-quick-actions]')) setShowQuickActions(false)
    }
    document.addEventListener('mousedown',close)
    return ()=>document.removeEventListener('mousedown',close)
  },[showQuickActions])

  const handleQuery=async()=>{
    if(!query.trim()||querying||!activeWs) return
    setQuerying(true); setQueryError('')
    const q=query.trim(); setQuery('')
    const placeholder={query:q,answer:'',citations:[],confidence_score:0,confidence_label:'',chunks_retrieved:0,chunks_used:0,workspace_id:activeWs.id,streamingText:''}
    setResults(prev=>[...prev,placeholder])
    const idx=results.length
    try {
      const res=await fetch(`${API}/query`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${getToken()}`},body:JSON.stringify({query:q,workspace_id:activeWs.id})})
      if(!res.ok){const err=await res.json();throw new Error(err.detail||'Query failed')}
      const data:QueryResponse=await res.json()
      const words=data.answer.split(' ')
      let current=''
      for(let i=0;i<words.length;i++){
        current+=(i===0?'':' ')+words[i]
        const streamed=current
        setResults(prev=>prev.map((r,j)=>j===idx?{...data,streamingText:streamed}:r))
        await new Promise(r=>setTimeout(r,15))
      }
      setResults(prev=>prev.map((r,j)=>{if(j!==idx)return r;const{streamingText:_,...rest}=r as any;return rest}))
    } catch(e:unknown){
      setResults(prev=>prev.filter((_,j)=>j!==idx))
      setQueryError(e instanceof Error?e.message:'Query failed')
    } finally{setQuerying(false)}
  }

  const handleUpload=async(e:React.ChangeEvent<HTMLInputElement>)=>{
    const file=e.target.files?.[0];if(!file||!activeWs) return
    setUploading(true);setUploadMsg(`Uploading ${file.name}...`)
    try{
      const doc=await uploadDocument(activeWs.id,file)
      setDocuments(prev=>[doc,...prev]);setUploadMsg(`Indexing ${file.name}...`)
      const poll=setInterval(async()=>{
        const updated=await getDocument(doc.id)
        setDocuments(prev=>prev.map(d=>d.id===updated.id?updated:d))
        if(updated.status==='indexed'||updated.status==='failed'){
          clearInterval(poll)
          setUploadMsg(updated.status==='indexed'?`✓ Indexed (${updated.chunk_count} chunks)`:`✗ Indexing failed`)
          setUploading(false)
        }
      },3000)
    }catch(e:unknown){setUploadMsg(`Error: ${e instanceof Error?e.message:'Upload failed'}`);setUploading(false)}
    e.target.value=''
  }

  const handleDeleteDoc=async(docId:string)=>{
    if(!confirm('Delete this document? This cannot be undone.')) return
    setDeletingDoc(docId)
    try{
      await fetch(`${API}/documents/${docId}`,{method:'DELETE',headers:{Authorization:`Bearer ${getToken()}`}})
      setDocuments(prev=>prev.filter(d=>d.id!==docId))
    }catch{}finally{setDeletingDoc(null)}
  }

  const handleCreateWs=async()=>{
    if(!newWsName.trim()) return
    const ws=await createWorkspace({name:newWsName.trim()})
    setWorkspaces(prev=>[...prev,ws]);setActiveWs(ws);setNewWsName('');setShowNewWs(false)
  }

  const handleQuickUrlSubmit=async(url:string)=>{
    if(!url.trim()||!activeWs) return
    setUrlLoading(true)
    try{
      const res=await fetch(`${API}/documents/from-url`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${getToken()}`},body:JSON.stringify({url:url.trim(),workspace_id:activeWs.id})})
      const data=await res.json()
      if(!res.ok) throw new Error(data.detail||'Failed to fetch URL')
      setDocuments(prev=>[data,...prev])
      setUploadMsg(`Indexing "${data.filename}"...`)
      const poll=setInterval(async()=>{
        const updated=await getDocument(data.id)
        setDocuments(prev=>prev.map(d=>d.id===updated.id?updated:d))
        if(updated.status==='indexed'||updated.status==='failed'){
          clearInterval(poll)
          setUploadMsg(updated.status==='indexed'?`✓ Indexed — ${updated.chunk_count} chunks`:'✗ Indexing failed')
          setUrlLoading(false)
        }
      },3000)
    }catch(e:unknown){setUploadMsg(`✗ ${e instanceof Error?e.message:'Failed'}`);setUrlLoading(false)}
  }

  const isAdmin=user?.role==='tenant_admin'
  const indexedCount=documents.filter(d=>d.status==='indexed').length

  if(isLoading) return <div style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'#F8F7F5'}}><p style={{color:'#9CA3AF'}}>Loading...</p></div>

  const sidebar=(
    <div style={{background:'#1A2B4A',display:'flex',flexDirection:'column',height:'100%',minHeight:0}}>
      <div style={{padding:'14px 12px',borderBottom:'1px solid rgba(255,255,255,.08)',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
        <Link href="/" style={{display:'flex',alignItems:'center',gap:8,textDecoration:'none'}}>
          <div style={{width:26,height:26,background:'rgba(255,255,255,.15)',borderRadius:4,display:'flex',alignItems:'center',justifyContent:'center'}}><span style={{color:'white',fontSize:12,fontWeight:700}}>L</span></div>
          <span style={{color:'white',fontWeight:700,fontSize:14,letterSpacing:'-.3px'}}>LexQuery</span>
        </Link>
        <button onClick={()=>setSidebarOpen(false)} className="hd" style={{background:'none',border:'none',color:'rgba(255,255,255,.5)',fontSize:20,cursor:'pointer',lineHeight:1}}>×</button>
      </div>
      <div style={{padding:'10px 10px',flex:1,overflowY:'auto'}}>
        <p style={{fontSize:10,fontWeight:700,color:'rgba(255,255,255,.4)',letterSpacing:'.8px',textTransform:'uppercase',marginBottom:5}}>Workspaces</p>
        {workspaces.map(ws=>(
          <button key={ws.id} onClick={()=>{setActiveWs(ws);setSidebarOpen(false)}} style={{width:'100%',textAlign:'left',padding:'6px 8px',borderRadius:4,border:'none',cursor:'pointer',background:activeWs?.id===ws.id?'rgba(255,255,255,.12)':'transparent',color:activeWs?.id===ws.id?'white':'rgba(255,255,255,.6)',fontSize:13,marginBottom:2}}>{ws.name}</button>
        ))}
        {showNewWs?(
          <div style={{marginTop:5}}>
            <input autoFocus value={newWsName} onChange={e=>setNewWsName(e.target.value)} onKeyDown={e=>e.key==='Enter'&&handleCreateWs()} placeholder="Workspace name" style={{width:'100%',padding:'6px 8px',background:'rgba(255,255,255,.1)',border:'1px solid rgba(255,255,255,.2)',borderRadius:4,color:'white',fontSize:12,outline:'none',marginBottom:4}}/>
            <div style={{display:'flex',gap:4}}>
              <button onClick={handleCreateWs} style={{flex:1,padding:4,fontSize:11,background:'rgba(255,255,255,.15)',color:'white',border:'none',borderRadius:4,cursor:'pointer'}}>Create</button>
              <button onClick={()=>setShowNewWs(false)} style={{padding:'4px 8px',fontSize:11,background:'transparent',color:'rgba(255,255,255,.4)',border:'none',cursor:'pointer'}}>Cancel</button>
            </div>
          </div>
        ):(
          <button onClick={()=>setShowNewWs(true)} style={{width:'100%',textAlign:'left',padding:'6px 8px',borderRadius:4,border:'1px dashed rgba(255,255,255,.2)',cursor:'pointer',background:'transparent',color:'rgba(255,255,255,.4)',fontSize:12,marginTop:3}}>+ New workspace</button>
        )}

        {activeWs&&(
          <div style={{marginTop:18}}>
            <p style={{fontSize:10,fontWeight:700,color:'rgba(255,255,255,.4)',letterSpacing:'.8px',textTransform:'uppercase',marginBottom:5}}>Documents</p>
            <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" onChange={handleUpload} style={{display:'none'}}/>
            {uploadMsg&&<p style={{fontSize:11,color:'rgba(255,255,255,.4)',marginBottom:5,lineHeight:1.4}}>{uploadMsg}</p>}
            {docsLoading&&<p style={{fontSize:11,color:'rgba(255,255,255,.25)',fontStyle:'italic'}}>Loading...</p>}
            {!docsLoading&&documents.length===0&&<p style={{fontSize:11,color:'rgba(255,255,255,.25)',fontStyle:'italic'}}>No documents yet</p>}
            {documents.map(doc=>(
              <div key={doc.id} style={{padding:'4px 6px',borderRadius:3,marginBottom:2,display:'flex',alignItems:'flex-start',gap:4}}>
                <div style={{flex:1,minWidth:0}}>
                  <p style={{fontSize:11,color:'rgba(255,255,255,.7)',margin:0,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}} title={doc.filename}>{doc.filename}</p>
                  <p style={{fontSize:10,color:'rgba(255,255,255,.3)',margin:'1px 0 0',display:'flex',alignItems:'center'}}>
                    <StatusDot status={doc.status}/>{doc.status}{doc.chunk_count?` · ${doc.chunk_count}`:''}
                  </p>
                </div>
                <button onClick={()=>handleDeleteDoc(doc.id)} disabled={deletingDoc===doc.id} style={{background:'transparent',border:'none',color:'rgba(255,255,255,.2)',cursor:'pointer',fontSize:16,padding:'0 2px',lineHeight:1,flexShrink:0}}>
                  {deletingDoc===doc.id?'…':'×'}
                </button>
              </div>
            ))}
          </div>
        )}

        {isAdmin&&(
          <div style={{marginTop:18,paddingTop:14,borderTop:'1px solid rgba(255,255,255,.08)'}}>
            <Link href="/dashboard/admin" onClick={()=>setSidebarOpen(false)} style={{display:'flex',alignItems:'center',gap:8,padding:'6px 8px',borderRadius:4,color:'rgba(255,255,255,.5)',fontSize:12,textDecoration:'none'}}
              onMouseEnter={e=>(e.currentTarget.style.color='white')} onMouseLeave={e=>(e.currentTarget.style.color='rgba(255,255,255,.5)')}>
              <span>⚙</span> Admin panel
            </Link>
          </div>
        )}
      </div>

      <div style={{padding:'10px 12px',borderTop:'1px solid rgba(255,255,255,.08)',display:'flex',alignItems:'center',justifyContent:'space-between',gap:8}}>
        <div style={{minWidth:0}}>
          <p style={{fontSize:12,color:'rgba(255,255,255,.7)',margin:0,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{user?.full_name||user?.email}</p>
          <p style={{fontSize:10,color:'rgba(255,255,255,.3)',margin:'1px 0 0',textTransform:'capitalize'}}>{user?.role?.replace('_',' ')}</p>
        </div>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <Link href="/dashboard/settings" style={{fontSize:11,color:'rgba(255,255,255,.3)',textDecoration:'none'}} title="Settings">⚙</Link>
          <button onClick={logout} style={{background:'transparent',border:'none',color:'rgba(255,255,255,.3)',fontSize:11,cursor:'pointer',flexShrink:0,whiteSpace:'nowrap'}}>Sign out</button>
        </div>
      </div>
    </div>
  )

  return (
    <>
      <style>{`
        .hm{display:flex}.hd{display:none}
        @media(max-width:767px){.hm{display:none!important}.hd{display:flex!important}}
        @keyframes spin{to{transform:rotate(360deg)}}
      `}</style>
      <div style={{display:'flex',height:'100dvh',overflow:'hidden',background:'#F8F7F5',fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'}}>

        {/* Desktop sidebar */}
        <div className="hm" style={{width:220,flexShrink:0,flexDirection:'column'}}>{sidebar}</div>

        {/* Mobile sidebar overlay */}
        {sidebarOpen&&(
          <div className="hd" style={{position:'fixed',inset:0,zIndex:100,display:'flex'}}>
            <div style={{width:260,flexShrink:0}}>{sidebar}</div>
            <div onClick={()=>setSidebarOpen(false)} style={{flex:1,background:'rgba(0,0,0,.5)'}}/>
          </div>
        )}

        {/* Main */}
        <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden',minWidth:0}}>
          {/* Header */}
          <div style={{padding:'12px 16px',borderBottom:'1px solid #E2E0DB',background:'white',display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,flexShrink:0}}>
            <div style={{display:'flex',alignItems:'center',gap:12,minWidth:0}}>
              <button onClick={()=>setSidebarOpen(true)} className="hd" style={{background:'none',border:'none',cursor:'pointer',display:'flex',flexDirection:'column',gap:4,flexShrink:0,padding:4}}>
                {[0,1,2].map(i=><div key={i} style={{width:18,height:2,background:'#1A2B4A',borderRadius:1}}/>)}
              </button>
              <div style={{minWidth:0}}>
                <h1 style={{fontSize:15,fontWeight:600,color:'#1A202C',margin:0,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{activeWs?.name||'Select a workspace'}</h1>
              </div>
            </div>
            <div style={{display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
              {activeWs&&<span style={{fontSize:12,color:'#9CA3AF',whiteSpace:'nowrap'}}>{indexedCount} doc{indexedCount!==1?'s':''} · {results.length} quer{results.length!==1?'ies':'y'}</span>}
              {isAdmin&&<Link href="/dashboard/admin" style={{fontSize:12,color:'#6B7280',background:'#F4F4F2',border:'1px solid #E2E0DB',borderRadius:5,padding:'4px 10px',textDecoration:'none',whiteSpace:'nowrap'}} className="hm">Admin</Link>}
              <Link href="/dashboard/settings" style={{fontSize:12,color:'#6B7280',background:'#F4F4F2',border:'1px solid #E2E0DB',borderRadius:5,padding:'4px 10px',textDecoration:'none',whiteSpace:'nowrap'}} className="hm">Settings</Link>
            </div>
          </div>

          {/* Results */}
          <div style={{flex:1,overflowY:'auto',padding:'16px'}}>
            {results.length===0&&<EmptyState hasWorkspace={!!activeWs} docCount={indexedCount}/>}
            {results.map((r,i)=><AnswerBlock key={i} result={r}/>)}
            {querying&&<div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:8,padding:'16px 18px',marginBottom:12,color:'#9CA3AF',fontSize:13}}>Searching documents...</div>}
            {queryError&&<div style={{background:'#FEF2F2',border:'1px solid #FECACA',borderRadius:8,padding:'12px 16px',marginBottom:12,fontSize:13,color:'#DC2626'}}>{queryError}</div>}
            <div ref={bottomRef}/>
          </div>

          {/* Query input */}
          <div style={{padding:'12px 16px 16px',borderTop:'1px solid #E2E0DB',background:'white',flexShrink:0}}>
            <div style={{maxWidth:720,margin:'0 auto',width:'100%'}}>
              <div style={{position:'relative'}} data-quick-actions="">
                {/* Dropdown menu */}
                {showQuickActions&&activeWs&&(
                  <div style={{position:'absolute',bottom:52,left:0,background:'white',border:'1px solid #E2E0DB',borderRadius:12,boxShadow:'0 8px 32px rgba(0,0,0,.12)',zIndex:50,minWidth:220,overflow:'hidden'}}>
                    {[
                      {icon:'📎',label:'Upload files',action:()=>{fileRef.current?.click();setShowQuickActions(false)}},
                      {icon:'🔗',label:'Add from URL',action:()=>{setShowUrlQuick(true);setShowQuickActions(false)}},
                      {icon:'📁',label:'View documents',action:()=>{setSidebarOpen(true);setShowQuickActions(false)}},
                      ...(results.length>0?[{icon:'✨',label:'New conversation',action:()=>{setResults([]);setShowQuickActions(false)}}]:[]),
                    ].map((item,i,arr)=>(
                      <button key={item.label} onClick={item.action}
                        style={{width:'100%',display:'flex',alignItems:'center',gap:10,padding:'11px 16px',background:'none',border:'none',borderBottom:i<arr.length-1?'1px solid #F4F4F2':'none',fontSize:13,color:'#374151',cursor:'pointer',textAlign:'left',fontFamily:'inherit',fontWeight:500}}
                        onMouseEnter={e=>e.currentTarget.style.background='#F8F7F5'}
                        onMouseLeave={e=>e.currentTarget.style.background='none'}
                      >
                        <span style={{fontSize:16}}>{item.icon}</span> {item.label}
                      </button>
                    ))}
                  </div>
                )}
                {/* Input row */}
                <div style={{display:'flex',alignItems:'center',border:'1px solid #E2E0DB',borderRadius:24,background:'white',boxShadow:'0 1px 4px rgba(0,0,0,.06)',paddingLeft:6,paddingRight:6,gap:4}}>
                  <button
                    onClick={()=>setShowQuickActions(p=>!p)}
                    title="Quick actions"
                    style={{width:32,height:32,borderRadius:'50%',background:showQuickActions?'#1A2B4A':'transparent',border:showQuickActions?'none':'1.5px solid #D1D5DB',color:showQuickActions?'white':'#6B7280',fontSize:showQuickActions?16:20,cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,transition:'all .15s',lineHeight:1}}
                  >
                    {showQuickActions?'×':'+'}
                  </button>
                  <textarea
                    value={query}
                    onChange={e=>{
                      setQuery(e.target.value)
                      e.target.style.height='auto'
                      e.target.style.height=Math.min(e.target.scrollHeight,160)+'px'
                    }}
                    onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();handleQuery()}}}
                    placeholder={!activeWs?'Select a workspace to begin...':results.length>0?'Ask a follow-up question...':`Ask a question about "${activeWs.name}" documents...`}
                    disabled={!activeWs||querying}
                    rows={1}
                    style={{flex:1,minHeight:44,maxHeight:160,padding:'11px 4px',border:'none',fontSize:14,color:'#1A202C',background:'transparent',resize:'none',outline:'none',fontFamily:'inherit',lineHeight:1.5,overflowY:'auto'}}
                  />
                  <button
                    onClick={handleQuery}
                    disabled={!query.trim()||querying||!activeWs}
                    style={{width:32,height:32,borderRadius:'50%',background:(!query.trim()||querying||!activeWs)?'#E2E0DB':'#1A2B4A',border:'none',cursor:(!query.trim()||querying||!activeWs)?'not-allowed':'pointer',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,transition:'background .15s'}}
                  >
                    {querying?(
                      <span style={{width:12,height:12,border:'2px solid rgba(255,255,255,.3)',borderTopColor:'white',borderRadius:'50%',display:'inline-block',animation:'spin .7s linear infinite'}}/>
                    ):(
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"/>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                      </svg>
                    )}
                  </button>
                </div>
                {/* Inline URL input */}
                {showUrlQuick&&activeWs&&(
                  <div style={{marginTop:8,display:'flex',gap:8,alignItems:'center'}}>
                    <input
                      autoFocus
                      type="url"
                      value={urlQuickInput}
                      onChange={e=>setUrlQuickInput(e.target.value)}
                      onKeyDown={e=>{
                        if(e.key==='Enter'){handleQuickUrlSubmit(urlQuickInput);setUrlQuickInput('');setShowUrlQuick(false)}
                        if(e.key==='Escape'){setShowUrlQuick(false);setUrlQuickInput('')}
                      }}
                      placeholder="https://example.com/document.pdf"
                      style={{flex:1,padding:'9px 14px',border:'1px solid #E2E0DB',borderRadius:20,fontSize:13,outline:'none',fontFamily:'inherit'}}
                    />
                    <button
                      onClick={()=>{handleQuickUrlSubmit(urlQuickInput);setUrlQuickInput('');setShowUrlQuick(false)}}
                      disabled={!urlQuickInput.trim()}
                      style={{padding:'9px 16px',background:urlQuickInput.trim()?'#1A2B4A':'#E2E0DB',color:urlQuickInput.trim()?'white':'#9CA3AF',border:'none',borderRadius:20,fontSize:13,fontWeight:600,cursor:urlQuickInput.trim()?'pointer':'not-allowed'}}
                    >
                      {urlLoading?'Fetching...':'Fetch'}
                    </button>
                    <button onClick={()=>{setShowUrlQuick(false);setUrlQuickInput('')}} style={{background:'none',border:'none',color:'#9CA3AF',cursor:'pointer',fontSize:18,lineHeight:1,padding:'0 4px'}}>×</button>
                  </div>
                )}
              </div>
              <p style={{fontSize:11,color:'#C4C0BA',marginTop:6,textAlign:'center'}}>Enter to send · Shift+Enter for new line</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
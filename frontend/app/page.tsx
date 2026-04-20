'use client'
import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'

const slides = [
  { label:'Contract Review', query:'What is the notice period required for contract termination?', answer:'The agreement requires a minimum of **30 days written notice** prior to termination by either party [1]. In cases of material breach, the non-breaching party may terminate with **7 days notice** provided the breach remains uncured [2].', sources:[{n:1,file:'Service_Agreement_v3.pdf',clause:'§8.2 Termination',page:'p. 14'},{n:2,file:'Service_Agreement_v3.pdf',clause:'§8.4 Termination for Cause',page:'p. 15'}], confidence:94 },
  { label:'Due Diligence', query:'Are there any change of control provisions in this agreement?', answer:'Yes. The agreement contains a **change of control clause** at §12.1 permitting either party to terminate within 60 days of a change of control event [1]. "Change of control" means any transaction where a third party acquires more than 50% of voting shares [2].', sources:[{n:1,file:'Acquisition_Agreement.pdf',clause:'§12.1 Change of Control',page:'p. 22'},{n:2,file:'Acquisition_Agreement.pdf',clause:'§1.1 Definitions',page:'p. 3'}], confidence:91 },
  { label:'GDPR', query:'Does this privacy policy comply with UK GDPR Article 17?', answer:'The policy *partially* addresses Article 17. It acknowledges the right to erasure [1] but omits the **30-day response window** required under UK GDPR [2]. The retention schedule in §4.3 also conflicts with erasure obligations [3].', sources:[{n:1,file:'Privacy_Policy_v2.pdf',clause:'§5.2 Your Rights',page:'p. 8'},{n:2,file:'GDPR_Report.pdf',clause:'Article 17 Analysis',page:'p. 2'},{n:3,file:'Privacy_Policy_v2.pdf',clause:'§4.3 Retention',page:'p. 11'}], confidence:87 },
  { label:'Employment', query:'What is the duration and scope of the non-compete restriction?', answer:'The non-compete prohibits working for a competitor for **12 months post-termination** [1]. Geographic scope is limited to **England & Wales** [2], applying to firms with revenues above £5M in legal technology [1].', sources:[{n:1,file:'Employment_Contract.pdf',clause:'§9.1 Non-Competition',page:'p. 6'},{n:2,file:'Employment_Contract.pdf',clause:'§9.3 Geographic Scope',page:'p. 7'}], confidence:96 },
]

const features = [
  {title:'Cited answers, not guesses',desc:'Every sentence links to its exact clause, page, and document. Any claim can be verified in seconds.'},
  {title:'Hybrid legal search',desc:'Semantic retrieval combined with exact-term matching. Clause numbers and defined terms are never missed.'},
  {title:'Permission-aware',desc:'Users see only what they are authorised to access. Enforced at the database layer — not the application.'},
  {title:'Immutable audit trail',desc:'Every query logged with user, timestamp, sources, and confidence. Export for compliance in one click.'},
  {title:'Multi-tenant isolation',desc:"Each organisation's data is fully isolated. No cross-tenant access possible at any layer."},
  {title:'Calibrated confidence',desc:'Every answer carries a score. Low-confidence responses are flagged so teams know when to verify.'},
]

const faqs = [
  {q:'How does LexQuery prevent hallucinations?',a:'Every answer is constrained to retrieved passages from your uploaded documents. If the source does not support a claim, LexQuery says so explicitly. Confidence is calibrated against a held-out legal benchmark and surfaced on every response — there is no inference beyond the record.'},
  {q:'Where is our data stored?',a:'You choose UK, EU, or US data residency at setup. Data is encrypted with AES-256 at rest and TLS 1.3 in transit. Your documents are never used to train foundation models and are never shared between tenants.'},
  {q:'What about legal privilege and confidentiality?',a:'Document access is permission-aware and enforced at the database layer. Every query, answer, and source view is written to an immutable audit trail that your General Counsel can review at any time. Nothing leaves your tenancy.'},
  {q:'How do user roles and permissions work?',a:'Tenant Admins can invite team members by email, assign roles (Viewer, Editor, Matter Admin, or Tenant Admin), and deactivate accounts from the Admin Panel. Viewers can only query — they cannot upload or delete documents. This gives you precise control over who can do what.'},
  {q:'How long does onboarding take?',a:'A typical deployment ingests a first tranche of documents within 48 hours. You can start querying the moment a document is indexed — usually within minutes of upload. SSO and SCIM provisioning are completed in the first week for most mid-market firms.'},
  {q:'Can we bring our own LLM?',a:'Enterprise customers can route answer generation to their own Azure OpenAI deployment or AWS Bedrock endpoint. Retrieval, citation extraction, and audit logging remain on LexQuery infrastructure.'},
]

const pricing = [
  {name:'Starter',price:'£800',per:'/month',desc:'Small in-house teams and boutique firms.',features:['Up to 10 seats','50,000 pages indexed','5,000 queries/month','UK data residency','CSV audit export'],highlight:false},
  {name:'Professional',price:'£3,500',per:'/month',desc:'Mid-market firms and growing legal teams.',features:['Up to 100 seats','500,000 pages indexed','50,000 queries/month','SSO included','Full audit export','UK or EU residency'],highlight:true},
  {name:'Enterprise',price:'Custom',per:'',desc:'Large firms and regulated enterprises.',features:['Unlimited seats','Custom volume','99.9% uptime SLA','Dedicated CSM','SCIM provisioning','UK · EU · US residency'],highlight:false},
]

const testimonials = [
  {quote:'Reduced contract review time by 60%. Associates now spend time on analysis, not searching.',name:'Partner, Commercial Disputes',firm:'Top 50 UK Law Firm'},
  {quote:'The citation system sold our risk committee. Every answer is auditable — the bar we need to clear.',name:'Head of Legal Operations',firm:'FTSE 250 Company'},
  {quote:'Due diligence that used to take a day now takes an hour. Accuracy on defined terms is exceptional.',name:'Associate, M&A',firm:'Magic Circle Firm'},
]

function useReveal() {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current; if (!el) return
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { el.style.opacity='1'; el.style.transform='none' } }, {threshold:0.1})
    io.observe(el); return () => io.disconnect()
  }, [])
  return ref
}
function Reveal({children,delay=0}:{children:React.ReactNode;delay?:number}) {
  const ref = useReveal()
  return <div ref={ref} style={{opacity:0,transform:'translateY(16px)',transition:`opacity .7s ease ${delay}ms, transform .7s ease ${delay}ms`}}>{children}</div>
}
function renderAnswer(text:string) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|\[[0-9]+\])/).map((part,i)=>{
    if(part.startsWith('**')&&part.endsWith('**')) return <strong key={i}>{part.slice(2,-2)}</strong>
    if(part.startsWith('*')&&part.endsWith('*')) return <em key={i}>{part.slice(1,-1)}</em>
    if(/^\[[0-9]+\]$/.test(part)) return <sup key={i} style={{color:'#C9A84C',fontWeight:700,fontSize:10,marginLeft:1}}>{part}</sup>
    return part
  })
}

export default function LandingPage() {
  const [slide,setSlide]=useState(0)
  const [mounted,setMounted]=useState(false)
  const [menuOpen,setMenuOpen]=useState(false)
  const [openFaq,setOpenFaq]=useState<number|null>(0)

  useEffect(()=>{
    setMounted(true)
    const t=setInterval(()=>setSlide(s=>(s+1)%slides.length),5000)
    return ()=>clearInterval(t)
  },[])

  const s=slides[slide]

  return (
    <div style={{background:'#F8F7F5',minHeight:'100vh',color:'#1A202C',fontFamily:'-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'}}>
      <style>{`
        *{box-sizing:border-box;margin:0;padding:0}
        a{color:inherit;text-decoration:none}
        button{font-family:inherit;cursor:pointer}
        .c{max-width:1100px;margin:0 auto;padding:0 20px}
        @media(min-width:768px){.c{padding:0 40px}}
        .btn{display:inline-flex;align-items:center;gap:8px;padding:11px 22px;background:#1A2B4A;color:white;border:none;border-radius:6px;font-size:14px;font-weight:700;text-decoration:none;transition:opacity .2s;cursor:pointer}
        .btn:hover{opacity:.88}
        .btn-g{background:white;color:#1A2B4A;border:1px solid #E2E0DB}
        .btn-g:hover{border-color:#1A2B4A;opacity:1}
        .sl{font-size:11px;font-weight:700;color:#9CA3AF;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px}
        .gb{width:26px;height:3px;background:#C9A84C;border-radius:2px;margin-bottom:14px}
        details summary{list-style:none} details summary::-webkit-details-marker{display:none}
      `}</style>

      {/* Nav */}
      <nav style={{position:'sticky',top:0,zIndex:50,background:'rgba(248,247,245,.95)',backdropFilter:'blur(8px)',borderBottom:'1px solid #E2E0DB'}}>
        <div className="c" style={{display:'flex',alignItems:'center',justifyContent:'space-between',height:60}}>
          <Link href="/" style={{display:'flex',alignItems:'center',gap:10}}>
            <div style={{width:28,height:28,background:'#1A2B4A',borderRadius:5,display:'flex',alignItems:'center',justifyContent:'center'}}><span style={{color:'white',fontSize:13,fontWeight:700}}>L</span></div>
            <span style={{fontWeight:700,fontSize:16,color:'#1A2B4A',letterSpacing:'-.3px'}}>LexQuery</span>
            <div style={{width:18,height:2,background:'#C9A84C',borderRadius:1}}/>
          </Link>
          <div style={{display:'flex',gap:24,alignItems:'center'}} className="hm">
            {['#features','#how','#pricing','#faq'].map((h,i)=>(
              <a key={h} href={h} style={{fontSize:13,color:'#6B7280'}}>{['Features','How it works','Pricing','FAQ'][i]}</a>
            ))}
          </div>
          <div style={{display:'flex',gap:10,alignItems:'center'}} className="hm">
            <Link href="/login" style={{fontSize:13,color:'#6B7280'}}>Sign in</Link>
            <Link href="/signup" className="btn" style={{padding:'8px 16px',fontSize:13}}>Get started</Link>
          </div>
          <button onClick={()=>setMenuOpen(!menuOpen)} className="hd" style={{background:'none',border:'none',padding:8,display:'flex',flexDirection:'column',gap:5}}>
            {[0,1,2].map(i=><div key={i} style={{width:22,height:2,background:'#1A2B4A',borderRadius:1,transition:'all .2s',transform:menuOpen&&i===0?'translateY(7px) rotate(45deg)':menuOpen&&i===2?'translateY(-7px) rotate(-45deg)':menuOpen&&i===1?'scaleX(0)':'none'}}/>)}
          </button>
        </div>
        {menuOpen&&(
          <div className="hd" style={{background:'white',borderTop:'1px solid #E2E0DB',padding:'16px 20px',display:'flex',flexDirection:'column',gap:14}}>
            {[['#features','Features'],['#how','How it works'],['#pricing','Pricing'],['#faq','FAQ']].map(([h,l])=>(
              <a key={h} href={h} onClick={()=>setMenuOpen(false)} style={{fontSize:15,color:'#1A2B4A',fontWeight:500}}>{l}</a>
            ))}
            <div style={{borderTop:'1px solid #E2E0DB',paddingTop:14,display:'flex',flexDirection:'column',gap:10}}>
              <Link href="/login" onClick={()=>setMenuOpen(false)} style={{fontSize:15,color:'#6B7280'}}>Sign in</Link>
              <Link href="/signup" onClick={()=>setMenuOpen(false)} className="btn" style={{textAlign:'center',justifyContent:'center'}}>Get started</Link>
            </div>
          </div>
        )}
        <style>{`.hm{display:flex}.hd{display:none}@media(max-width:767px){.hm{display:none!important}.hd{display:flex!important}}`}</style>
      </nav>

      {/* Hero */}
      <section style={{padding:'60px 0 48px'}}>
        <div className="c">
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(280px,1fr))',gap:48,alignItems:'center'}}>
            <div style={{opacity:mounted?1:0,transform:mounted?'none':'translateY(16px)',transition:'all .7s ease'}}>
              <div style={{display:'inline-block',background:'white',border:'1px solid #E2E0DB',borderRadius:20,padding:'4px 14px',fontSize:11,fontWeight:700,color:'#6B7280',marginBottom:18,letterSpacing:'.8px',textTransform:'uppercase'}}>Enterprise Legal Intelligence</div>
              <h1 style={{fontSize:'clamp(36px,6vw,54px)',fontWeight:700,color:'#1A2B4A',lineHeight:1.08,letterSpacing:'-1.5px',marginBottom:18}}>
                Legal research.<br/>Answered in<br/><span style={{color:'#C9A84C'}}>seconds.</span>
              </h1>
              <p style={{fontSize:17,color:'#6B7280',lineHeight:1.7,marginBottom:26,maxWidth:460}}>Upload contracts, case law, and regulatory documents. Ask in plain English. Get cited answers grounded in the exact source — not hallucinations.</p>
              <div style={{display:'flex',gap:10,flexWrap:'wrap',marginBottom:22}}>
                <Link href="/signup" className="btn">Start free trial</Link>
                <a href="#how" className="btn btn-g">How it works</a>
              </div>
              <div style={{display:'flex',gap:18,flexWrap:'wrap'}}>
                {['GDPR compliant','UK data residency','14-day free trial'].map(t=>(
                  <span key={t} style={{fontSize:12,color:'#9CA3AF',display:'flex',alignItems:'center',gap:4}}><span style={{color:'#16A34A',fontWeight:700}}>✓</span>{t}</span>
                ))}
              </div>
            </div>

            {/* Product window */}
            <div style={{opacity:mounted?1:0,transition:'opacity .7s ease .2s'}}>
              <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:12,overflow:'hidden',boxShadow:'0 20px 50px -20px rgba(26,43,74,.2)'}}>
                <div style={{background:'#1A2B4A',padding:'10px 14px',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
                  <div style={{display:'flex',gap:5}}>{[0,1,2].map(i=><div key={i} style={{width:9,height:9,borderRadius:'50%',background:'rgba(255,255,255,.2)'}}/>)}</div>
                  <div style={{display:'flex',gap:5}}>
                    {slides.map((sl,i)=>(
                      <button key={i} onClick={()=>setSlide(i)} style={{fontSize:10,fontWeight:i===slide?700:400,color:i===slide?'white':'rgba(255,255,255,.4)',background:i===slide?'rgba(255,255,255,.15)':'transparent',border:'none',borderRadius:4,padding:'2px 8px',cursor:'pointer',transition:'all .2s'}}>{sl.label}</button>
                    ))}
                  </div>
                </div>
                <div style={{padding:'12px 14px',background:'#F8F7F5',borderBottom:'1px solid #E2E0DB',display:'flex',gap:10,alignItems:'center'}}>
                  <p style={{fontSize:13,color:'#6B7280',fontStyle:'italic',margin:0,flex:1}}>&ldquo;{s.query}&rdquo;</p>
                  <div style={{width:28,height:28,background:'#1A2B4A',borderRadius:5,display:'flex',alignItems:'center',justifyContent:'center',color:'white',fontSize:13,flexShrink:0}}>→</div>
                </div>
                <div style={{padding:16}}>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10}}>
                    <span style={{fontSize:10,fontWeight:700,color:'#9CA3AF',textTransform:'uppercase',letterSpacing:'.5px'}}>Answer</span>
                    <span style={{fontSize:10,fontWeight:700,color:'#16A34A',border:'1px solid #16A34A',borderRadius:4,padding:'2px 7px'}}>High · {s.confidence}%</span>
                  </div>
                  <p style={{fontSize:13,lineHeight:1.75,color:'#1A202C',margin:'0 0 12px'}}>{renderAnswer(s.answer)}</p>
                  <div style={{borderTop:'1px solid #E2E0DB',paddingTop:10}}>
                    <p style={{fontSize:10,fontWeight:700,color:'#9CA3AF',textTransform:'uppercase',letterSpacing:'.5px',marginBottom:6}}>Sources</p>
                    {s.sources.map(src=>(
                      <div key={src.n} style={{display:'flex',gap:8,marginBottom:4,fontSize:11,color:'#6B7280',alignItems:'flex-start'}}>
                        <span style={{minWidth:16,height:16,background:'#1A2B4A',color:'white',borderRadius:2,display:'flex',alignItems:'center',justifyContent:'center',fontSize:9,fontWeight:700,flexShrink:0}}>{src.n}</span>
                        <span><strong style={{color:'#374151'}}>{src.file}</strong> · {src.clause} · {src.page}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div style={{padding:'8px 12px',borderTop:'1px solid #E2E0DB',display:'flex',justifyContent:'center',gap:6}}>
                  {slides.map((_,i)=><button key={i} onClick={()=>setSlide(i)} style={{width:i===slide?18:6,height:6,borderRadius:3,background:i===slide?'#1A2B4A':'#E2E0DB',border:'none',cursor:'pointer',transition:'all .3s',padding:0}}/>)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trusted by */}
      <div style={{borderTop:'1px solid #E2E0DB',borderBottom:'1px solid #E2E0DB',padding:'18px 0',background:'white'}}>
        <div className="c" style={{display:'flex',alignItems:'center',gap:24,flexWrap:'wrap',justifyContent:'center'}}>
          <span style={{fontSize:11,fontWeight:700,color:'#9CA3AF',letterSpacing:'.8px',textTransform:'uppercase',whiteSpace:'nowrap'}}>Trusted by</span>
          {['Allen · Murray LLP','Whitehall Chambers','Northstar Legal','Kestrel & Fell','Meridian Counsel'].map((f,i)=>(
            <span key={i} style={{fontSize:14,color:'#6B7280',fontWeight:500,whiteSpace:'nowrap'}}>{f}</span>
          ))}
        </div>
      </div>

      {/* How it works */}
      <section id="how" style={{padding:'72px 0',background:'white',borderBottom:'1px solid #E2E0DB'}}>
        <div className="c">
          <Reveal><div style={{textAlign:'center',marginBottom:48}}><div className="sl">How it works</div><h2 style={{fontSize:'clamp(24px,4vw,34px)',fontWeight:700,color:'#1A2B4A',letterSpacing:'-.5px'}}>From document to answer in three steps</h2></div></Reveal>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:32}}>
            {[{n:'01',title:'Upload your documents',desc:'PDFs, Word documents, or plain text. LexQuery parses, chunks, and indexes everything automatically in minutes.'},{n:'02',title:'Ask in plain English',desc:'Type your question as you would ask a senior colleague. No Boolean operators or query syntax required.'},{n:'03',title:'Get cited answers',desc:'Relevant passages are retrieved and used to generate an answer with inline citations linked to the exact source page.'}].map((st,i)=>(
              <Reveal key={st.n} delay={i*100}>
                <div style={{borderTop:'2px solid #1A2B4A',paddingTop:18}}>
                  <div style={{fontSize:11,fontWeight:700,color:'#C9A84C',letterSpacing:'1px',marginBottom:10}}>{st.n}</div>
                  <h3 style={{fontSize:15,fontWeight:600,color:'#1A2B4A',marginBottom:6}}>{st.title}</h3>
                  <p style={{fontSize:13,color:'#6B7280',lineHeight:1.65,margin:0}}>{st.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" style={{padding:'72px 0',borderBottom:'1px solid #E2E0DB'}}>
        <div className="c">
          <Reveal><div style={{textAlign:'center',marginBottom:48}}><div className="sl">Features</div><h2 style={{fontSize:'clamp(24px,4vw,34px)',fontWeight:700,color:'#1A2B4A',letterSpacing:'-.5px',marginBottom:8}}>Built for legal practice standards</h2><p style={{fontSize:15,color:'#6B7280',maxWidth:440,margin:'0 auto'}}>Every feature designed around the trust and accountability requirements of legal work.</p></div></Reveal>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(270px,1fr))',gap:18}}>
            {features.map((f,i)=>(
              <Reveal key={f.title} delay={i*50}>
                <div style={{background:'white',border:'1px solid #E2E0DB',borderRadius:10,padding:'18px 20px',height:'100%'}}>
                  <div className="gb"/>
                  <h3 style={{fontSize:14,fontWeight:600,color:'#1A2B4A',marginBottom:6}}>{f.title}</h3>
                  <p style={{fontSize:13,color:'#6B7280',lineHeight:1.65,margin:0}}>{f.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section style={{padding:'72px 0',background:'#1A2B4A',borderBottom:'1px solid #162646'}}>
        <div className="c">
          <Reveal><div style={{textAlign:'center',marginBottom:44}}><div style={{fontSize:11,fontWeight:700,color:'rgba(255,255,255,.4)',letterSpacing:'1px',textTransform:'uppercase',marginBottom:10}}>What legal teams say</div><h2 style={{fontSize:'clamp(22px,4vw,30px)',fontWeight:700,color:'white',letterSpacing:'-.5px'}}>Trusted by legal professionals</h2></div></Reveal>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(250px,1fr))',gap:18}}>
            {testimonials.map((t,i)=>(
              <Reveal key={i} delay={i*80}>
                <div style={{background:'rgba(255,255,255,.06)',border:'1px solid rgba(255,255,255,.1)',borderRadius:10,padding:22}}>
                  <div style={{display:'flex',gap:2,marginBottom:12}}>{[1,2,3,4,5].map(s=><span key={s} style={{color:'#C9A84C',fontSize:12}}>★</span>)}</div>
                  <p style={{fontSize:14,color:'rgba(255,255,255,.8)',lineHeight:1.7,margin:'0 0 16px',fontStyle:'italic'}}>&ldquo;{t.quote}&rdquo;</p>
                  <div style={{borderTop:'1px solid rgba(255,255,255,.1)',paddingTop:12}}>
                    <p style={{fontSize:13,fontWeight:600,color:'white',margin:'0 0 2px'}}>{t.name}</p>
                    <p style={{fontSize:11,color:'rgba(255,255,255,.4)',margin:0}}>{t.firm}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Security */}
      <section style={{background:'white',borderBottom:'1px solid #E2E0DB',padding:'72px 0'}}>
        <div className="c">
          <Reveal><div style={{textAlign:'center',marginBottom:44}}><div className="sl">Security & Compliance</div><h2 style={{fontSize:'clamp(22px,4vw,30px)',fontWeight:700,color:'#1A2B4A',letterSpacing:'-.5px'}}>Enterprise-grade data protection</h2></div></Reveal>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:24}}>
            {[{label:'GDPR & UK GDPR',desc:'Full compliance. DPA templates included for every engagement.'},{label:'Data residency',desc:'UK, EU or US. Pinned at setup, never relocated.'},{label:'Encryption',desc:'TLS 1.3 in transit. AES-256 at rest. CMK available.'},{label:'Audit logs',desc:'Immutable. 7-year retention. WORM storage. Exportable.'}].map((s,i)=>(
              <Reveal key={s.label} delay={i*60}>
                <div style={{borderTop:'2px solid #C9A84C',paddingTop:14}}>
                  <p style={{fontSize:13,fontWeight:700,color:'#1A2B4A',margin:'0 0 4px'}}>{s.label}</p>
                  <p style={{fontSize:12,color:'#9CA3AF',margin:0,lineHeight:1.5}}>{s.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" style={{padding:'72px 0',borderBottom:'1px solid #E2E0DB'}}>
        <div className="c">
          <Reveal><div style={{textAlign:'center',marginBottom:48}}><div className="sl">Pricing</div><h2 style={{fontSize:'clamp(24px,4vw,34px)',fontWeight:700,color:'#1A2B4A',letterSpacing:'-.5px',marginBottom:8}}>Simple, transparent pricing</h2><p style={{fontSize:15,color:'#6B7280'}}>14-day free trial on all plans. No credit card required.</p></div></Reveal>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(250px,1fr))',gap:18}}>
            {pricing.map((p,i)=>(
              <Reveal key={p.name} delay={i*80}>
                <div style={{background:p.highlight?'#1A2B4A':'white',border:`2px solid ${p.highlight?'#C9A84C':'#E2E0DB'}`,borderRadius:10,padding:26,position:'relative',height:'100%',display:'flex',flexDirection:'column'}}>
                  {p.highlight&&<div style={{position:'absolute',top:-13,left:'50%',transform:'translateX(-50%)',background:'#C9A84C',color:'#1A2B4A',fontSize:10,fontWeight:800,padding:'3px 14px',borderRadius:20,letterSpacing:'.5px',whiteSpace:'nowrap'}}>MOST POPULAR</div>}
                  <p style={{fontSize:12,fontWeight:700,color:p.highlight?'rgba(255,255,255,.5)':'#9CA3AF',marginBottom:8,letterSpacing:'.5px',textTransform:'uppercase'}}>{p.name}</p>
                  <div style={{display:'flex',alignItems:'baseline',gap:3,marginBottom:6}}>
                    <span style={{fontSize:p.price==='Custom'?28:34,fontWeight:700,color:p.highlight?'white':'#1A2B4A',letterSpacing:'-1px'}}>{p.price}</span>
                    {p.per&&<span style={{fontSize:13,color:p.highlight?'rgba(255,255,255,.4)':'#9CA3AF'}}>{p.per}</span>}
                  </div>
                  <p style={{fontSize:12,color:p.highlight?'rgba(255,255,255,.5)':'#9CA3AF',marginBottom:18}}>{p.desc}</p>
                  <ul style={{listStyle:'none',padding:0,margin:'0 0 22px',display:'flex',flexDirection:'column',gap:8,flex:1}}>
                    {p.features.map(f=>(
                      <li key={f} style={{fontSize:13,color:p.highlight?'rgba(255,255,255,.8)':'#6B7280',display:'flex',gap:8}}>
                        <span style={{color:p.highlight?'#C9A84C':'#16A34A',fontWeight:700,flexShrink:0}}>✓</span>{f}
                      </li>
                    ))}
                  </ul>
                  <Link href="/signup" style={{display:'block',textAlign:'center',padding:11,borderRadius:6,textDecoration:'none',fontSize:14,fontWeight:700,background:p.highlight?'#C9A84C':'#1A2B4A',color:p.highlight?'#1A2B4A':'white'}}>
                    {p.name==='Enterprise'?'Contact sales':'Start free trial'}
                  </Link>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" style={{padding:'72px 0',background:'white',borderBottom:'1px solid #E2E0DB'}}>
        <div className="c">
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(260px,1fr))',gap:60,alignItems:'start'}}>
            <Reveal>
              <div className="sl">FAQ</div>
              <h2 style={{fontSize:'clamp(22px,4vw,32px)',fontWeight:700,color:'#1A2B4A',letterSpacing:'-.5px',marginBottom:12,lineHeight:1.2}}>Questions from counsel</h2>
              <p style={{fontSize:14,color:'#6B7280',lineHeight:1.65}}>If you need a bespoke architecture review or a security whitepaper, our solutions team can provide one under NDA within five working days.</p>
            </Reveal>
            <div style={{borderTop:'1px solid #E2E0DB'}}>
              {faqs.map((f,i)=>(
                <Reveal key={i} delay={i*30}>
                  <div style={{borderBottom:'1px solid #E2E0DB'}}>
                    <button onClick={()=>setOpenFaq(openFaq===i?null:i)} style={{width:'100%',textAlign:'left',background:'none',border:'none',padding:'18px 0',display:'flex',alignItems:'flex-start',gap:14,cursor:'pointer'}}>
                      <span style={{fontFamily:'monospace',fontSize:10,color:'#C9A84C',paddingTop:3,flexShrink:0,letterSpacing:'.05em'}}>Q.{String(i+1).padStart(2,'0')}</span>
                      <span style={{fontSize:15,color:'#1A2B4A',fontWeight:600,flex:1,lineHeight:1.4}}>{f.q}</span>
                      <span style={{color:'#C9A84C',fontSize:18,flexShrink:0,lineHeight:1,transform:openFaq===i?'rotate(45deg)':'none',transition:'transform .2s'}}>+</span>
                    </button>
                    {openFaq===i&&(
                      <div style={{padding:'0 0 18px 34px',fontSize:14,color:'#6B7280',lineHeight:1.7}}>{f.a}</div>
                    )}
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{padding:'72px 0',background:'#F8F7F5',borderBottom:'1px solid #E2E0DB',textAlign:'center'}}>
        <div className="c">
          <Reveal>
            <h2 style={{fontSize:'clamp(26px,5vw,42px)',fontWeight:700,color:'#1A2B4A',letterSpacing:'-1px',marginBottom:14}}>Ready to search smarter?</h2>
            <p style={{fontSize:16,color:'#6B7280',marginBottom:28,maxWidth:380,margin:'0 auto 28px'}}>Join legal teams finding answers in seconds, not hours.</p>
            <div style={{display:'flex',gap:12,justifyContent:'center',flexWrap:'wrap'}}>
              <Link href="/signup" className="btn">Start your free trial</Link>
              <Link href="/login" className="btn btn-g">Sign in to your account</Link>
            </div>
            <p style={{fontSize:12,color:'#9CA3AF',marginTop:16}}>No credit card · 14-day trial · Cancel anytime</p>
          </Reveal>
        </div>
      </section>

      {/* Footer */}
      <footer style={{background:'#1A2B4A',padding:'48px 0 28px'}}>
        <div className="c">
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(130px,1fr))',gap:28,marginBottom:36,paddingBottom:28,borderBottom:'1px solid rgba(255,255,255,.08)'}}>
            <div style={{gridColumn:'span 2'}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
                <div style={{width:22,height:22,background:'rgba(255,255,255,.1)',borderRadius:3,display:'flex',alignItems:'center',justifyContent:'center'}}><span style={{color:'white',fontSize:11,fontWeight:700}}>L</span></div>
                <span style={{fontWeight:700,fontSize:14,color:'white'}}>LexQuery</span>
              </div>
              <p style={{fontSize:13,color:'rgba(255,255,255,.4)',lineHeight:1.6,margin:0,maxWidth:220}}>Grounded legal intelligence for law firms that cannot afford to guess.</p>
            </div>
            {[{h:'Product',links:['Platform','Citations','Audit trail','Changelog']},{h:'Company',links:['About','Customers','Careers','Contact']},{h:'Legal',links:['Privacy','Terms','DPA','Security']}].map(col=>(
              <div key={col.h}>
                <h6 style={{fontSize:11,fontWeight:700,color:'rgba(255,255,255,.3)',letterSpacing:'.1em',textTransform:'uppercase',margin:'0 0 12px'}}>{col.h}</h6>
                {col.links.map(l=><div key={l} style={{marginBottom:8}}><a href="#" style={{fontSize:13,color:'rgba(255,255,255,.5)'}}>{l}</a></div>)}
              </div>
            ))}
          </div>
          <div style={{display:'flex',justifyContent:'space-between',flexWrap:'wrap',gap:8}}>
            <span style={{fontSize:11,color:'rgba(255,255,255,.25)'}}>© 2025 LexQuery Ltd · Registered in England & Wales</span>
            <span style={{fontSize:11,color:'rgba(255,255,255,.25)'}}>London · Edinburgh · New York</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

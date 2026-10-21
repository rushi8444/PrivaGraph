import { useEffect, useState } from 'react';
import './ProjectAnatomy.css';

const stages = [
  { title: 'Bring in company files', detail: 'Add OKF Markdown or PDF files. PrivaGraph reads them locally and keeps table rows together, so one employee’s details do not get attached to another.', tag: '01 · YOUR FILES', icon: '▤' },
  { title: 'Hide private details', detail: 'Names, salaries and identifiers are replaced with consistent stand-in tokens. The same person gets the same token in different files, so useful links still work.', tag: '02 · TOKENIZE', icon: '⌕' },
  { title: 'Lock away originals', detail: 'The real values are encrypted in a local vault. Only PrivaGraph can look them up again; the AI service never gets the vault key.', tag: '03 · LOCKED HERE', icon: '▣' },
  { title: 'Find the right facts', detail: 'PrivaGraph connects people, teams and facts in a knowledge graph, then retrieves only the relevant records within the requested department.', tag: '04 · FIND CONTEXT', icon: '⌘' },
  { title: 'Ask AI, safely', detail: 'A prompt-injection check runs first. The AI gets the question and relevant context with detected private details tokenized. PrivaGraph restores the answer on your side, or answers locally if the AI is unavailable.', tag: '05 · SAFE ANSWER', icon: '⇄' },
];

const Bolt = ({ x, y }) => <circle cx={x} cy={y} r="3.1" className="machine-bolt" />;
const Pipe = ({ d, className = '' }) => <path d={d} className={`machine-pipe ${className}`} />;

function Machine({ step }) {
  return <svg className="privacy-machine" viewBox="0 0 900 550" role="img" aria-label="Animated isometric cutaway of the PrivaGraph privacy pipeline">
    <defs>
      <linearGradient id="metalTop" x2="0.8" y2="1"><stop stopColor="#39453f"/><stop offset="1" stopColor="#202923"/></linearGradient>
      <linearGradient id="vaultFace" x2="0" y2="1"><stop stopColor="#263a31"/><stop offset="1" stopColor="#111a16"/></linearGradient>
      <linearGradient id="paper" x2="0.9" y2="1"><stop stopColor="#e4dcc6"/><stop offset="1" stopColor="#aaa58f"/></linearGradient>
      <filter id="glow"><feGaussianBlur stdDeviation="7" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#8ca090" strokeOpacity=".09"/></pattern>
    </defs>
    <ellipse cx="453" cy="475" rx="340" ry="30" fill="#000" opacity=".34" />
    <path d="M85 340 450 139 815 340 450 543Z" fill="#131a16" stroke="#536158" strokeWidth="2"/>
    <path d="m85 340 365 203v-39L85 302Z" fill="#1a211d" stroke="#3e4a42"/>
    <path d="m450 543 365-203v-39L450 504Z" fill="#101612" stroke="#3e4a42"/>
    <path d="M106 338 450 149l344 189-344 191Z" fill="url(#grid)" opacity=".85"/>
    {/* raised perimeter frame and fasteners */}
    <path d="m111 337 339-185 339 185M138 353l312-170 312 170M122 363l328 181 328-181" fill="none" stroke="#59675d" strokeWidth="3"/>
    {[[112,337],[450,152],[790,337],[450,523],[142,354],[758,354],[450,185],[450,490]].map(([x,y],i)=><Bolt key={i} x={x} y={y}/>)}
    {/* input dock: stacked source sheets, clamp, feed rollers */}
    <g className={step === 0 ? 'part-active' : ''}>
      <path d="m125 295 75-42 76 42-76 43Z" fill="#333e36" stroke="#69766b"/>
      {[0,1,2].map(i=><path key={i} d={`m${143+i*3} ${286-i*5} 55-31 58 31-55 31Z`} fill="url(#paper)" stroke="#77796b"/>)}
      <path d="m153 274 45-25m-39 32 40-23m-30 30 35-20" stroke="#77796b" strokeWidth="2"/>
      <path d="m145 322 54 30 57-32M162 329v11m68-27v12" fill="none" stroke="#758178" strokeWidth="3"/>
      <circle cx="275" cy="301" r="13" fill="#171d19" stroke="#67756a" strokeWidth="4"/><circle cx="275" cy="301" r="4" fill="#a2ad9e"/>
    </g>
    {/* parser comb and protected row lanes */}
    <g className={step === 0 ? 'part-active' : ''}>
      <path d="m252 315 69-39 75 42-69 39Z" fill="#29342d" stroke="#78847a" strokeWidth="2"/>
      {[0,1,2,3,4].map(i=><g key={i}><path d={`M${275+i*13} ${308-i*7}l26 14`} stroke="#b5bdaf" strokeWidth="3"/><circle cx={280+i*13} cy={310-i*7} r="2.5" fill="#a1b5a4"/></g>)}
      <path d="m276 338 52 29 59-33" fill="none" stroke="#56645a" strokeWidth="3"/>
    </g>
    {/* HMAC tokenizer: rotating drum */}
    <g className={`token-drum ${step === 1 ? 'part-active' : ''}`}>
      <ellipse cx="406" cy="300" rx="37" ry="21" fill="#25332b" stroke="#88a78f" strokeWidth="2"/>
      <path d="M369 300v35c0 12 17 22 37 22s37-10 37-22v-35" fill="#202b24" stroke="#74877a" strokeWidth="2"/>
      <ellipse cx="406" cy="335" rx="37" ry="21" fill="#1a241e" stroke="#68796d" strokeWidth="2"/>
      <path d="M380 300v35m13-40v43m13-43v45m13-43v42m13-36v31" stroke="#8da094" strokeOpacity=".5"/>
      <circle cx="406" cy="300" r="6" fill="#94b79b"/>
      <text x="406" y="388" textAnchor="middle" className="machine-engrave">HMAC</text>
    </g>
    {/* protected local vault */}
    <g className={`vault-body ${step === 2 ? 'part-active' : ''}`}>
      <path d="m449 309 107-60 104 58-107 62Z" fill="#2c3e33" stroke="#829487" strokeWidth="2"/>
      <path d="m449 309 104 60v82l-104-59Z" fill="url(#vaultFace)" stroke="#596c5e" strokeWidth="2"/>
      <path d="m553 369 107-62v82l-107 62Z" fill="#111b15" stroke="#617166" strokeWidth="2"/>
      <path d="m474 309 80-45 77 43-80 46Z" fill="#1d2b22" stroke="#64796a"/>
      <path d="M546 303v28m-13-20 26 14m-26 0 26-14" stroke="#a7c6ad" strokeWidth="4" strokeLinecap="round"/>
      <circle cx="546" cy="317" r="22" fill="none" stroke="#a7c6ad" strokeWidth="2"/>
      {[0,1,2].map(i=><path key={i} d={`m${474+i*7} ${342+i*4} 55 32`} stroke="#617366" strokeWidth="2"/>)}
      <text x="555" y="438" textAnchor="middle" className="machine-engrave">LOCAL VAULT</text>
      <path d="M661 321v47m-7-40 7-7 7 7m-14 33 7 7 7-7" stroke="#91a597" strokeWidth="2" fill="none"/>
    </g>
    {/* graph assembly: hubs and edges on a raised board */}
    <g className={step === 3 ? 'part-active' : ''}>
      <path d="m326 401 88-50 95 53-88 51Z" fill="#202a23" stroke="#68776c" strokeWidth="2"/>
      <path d="m346 402 76-43m-47 55 78-44m-40 58 70-40m-105-8 98 54m-51-72 96 53m-143-30 95 54" stroke="#7e9582" strokeOpacity=".5" strokeWidth="2"/>
      {[[371,395],[420,367],[461,403],[390,432],[445,435],[480,385]].map(([x,y],i)=><g key={i}><circle cx={x} cy={y} r={i===2?9:6} fill={i===2?'#9aba9e':'#566e5b'} stroke="#b3c0b3" strokeWidth="1.5"/><circle cx={x} cy={y} r="2" fill="#d3dfd3"/></g>)}
      <text x="407" y="471" textAnchor="middle" className="machine-engrave">GRAPH / BFS</text>
    </g>
    {/* trust boundary fence, substantial and mechanically gated */}
    <path d="m668 248 57 32v112l-57-32Z" fill="#101713" fillOpacity=".82" stroke="#9aab9d" strokeDasharray="5 5"/>
    <path d="m674 260 45 26m-45-14 45 26m-45-14 45 26m-45-14 45 26m-45-14 45 26" stroke="#748879" strokeOpacity=".55"/>
    <g className={step === 4 ? 'part-active' : ''}>
      {/* tokens travel outward; plaintext glyphs never appear outside */}
      <Pipe d="M282 297C322 274 345 274 370 289" className="pipe-source"/>
      <Pipe d="M442 297C456 281 466 275 485 274" className="pipe-local"/>
      <Pipe d="M658 282C706 260 737 263 774 282" className="pipe-token"/>
      <path d="m752 245 48 27v61l-48-27Z" fill="#1f2a23" stroke="#84948a" strokeWidth="2"/>
      <path d="m761 258 30 17m-30-7 30 17m-30-7 21 12" stroke="#a5b0a8" strokeWidth="2"/>
      <path d="M797 285h37v21h-37" fill="#29352d" stroke="#728176" strokeWidth="2"/>
      <circle cx="830" cy="295" r="3" fill="#a4b4a8"/>
      <text x="786" y="345" textAnchor="middle" className="machine-engrave">TOKEN ONLY</text>
    </g>
    {/* fine cable runs, clips, ribs, connector studs */}
    <Pipe d="M194 351v22l49 27" className="pipe-dim"/><Pipe d="M312 355v22l28 16" className="pipe-dim"/>
    <Pipe d="M603 430v23l48-28" className="pipe-dim"/>
    {[[244,399],[332,392],[604,452],[714,352]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r="4" fill="#303b33" stroke="#86948a" strokeWidth="1.5"/>)}
    {Array.from({length:13},(_,i)=><path key={i} d={`M${163+i*18} ${458-i*9}l7 4`} stroke="#738076" strokeOpacity=".5" strokeWidth="2"/>)}
    <circle className="signal-pulse pulse-a" r="5" fill="#e2d9be" filter="url(#glow)"><animateMotion dur="5.2s" repeatCount="indefinite" path="M282 297C322 274 345 274 370 289"/></circle>
    <circle className="signal-pulse pulse-b" r="4" fill="#a9d1b0" filter="url(#glow)"><animateMotion dur="5.2s" repeatCount="indefinite" path="M442 297C456 281 466 275 485 274"/></circle>
    <circle className="signal-pulse pulse-c" r="4" fill="#d9e4d8" filter="url(#glow)"><animateMotion dur="5.2s" repeatCount="indefinite" path="M658 282C706 260 737 263 774 282"/></circle>
    <path d="m98 387 45 25m615-45 44-25M84 402l21 12m690 4 21-12" stroke="#526057" strokeWidth="4"/>
  </svg>;
}

export default function ProjectAnatomy() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setStep((current) => (current + 1) % stages.length), 6200);
    return () => window.clearInterval(timer);
  }, []);
  return <main className="anatomy-page">
    <header className="anatomy-heading">
      <div><div className="anatomy-kicker"><span className="status-dot"/> PRIVAGRAPH / WHY IT EXISTS</div><h1>Use AI with company data.<br/><em>Keep private details private.</em></h1><p className="anatomy-intro">PrivaGraph sits between your files and an AI service. It hides sensitive details before sending a question, then restores the useful answer inside your organization.</p></div>
      <div className="anatomy-stamp"><span>TRUST MODEL</span><strong>LOCAL → CLOUD</strong><small>RAW DATA STAYS LOCAL</small></div>
    </header>
    <section className="privacy-example" aria-label="Example of private data protection">
      <div className="example-intro"><span className="example-kicker">THE PROBLEM IT SOLVES</span><strong>Ask about confidential records<br/>without exposing the records.</strong><small>Example only · fictional HR data</small></div>
      <article className="example-card raw-example"><div className="example-card-head"><span className="example-icon">!</span><span>IN YOUR COMPANY FILE</span><b>PRIVATE</b></div><p>Priya Nandakumar · Engineering</p><strong>Salary $210,000 · SSN 912-04-7731</strong></article>
      <div className="example-arrow" aria-hidden="true"><span>PrivaGraph</span><b>→</b></div>
      <article className="example-card token-example"><div className="example-card-head"><span className="example-icon">✓</span><span>WHAT THE AI RECEIVES</span><b>HIDDEN</b></div><p>⟦A1_PERSON_0C2F91AB⟧ · Engineering</p><strong>Salary ⟦B4_SALARY_8E102C5D⟧ · SSN ⟦C2_US_SSN_71A043EF⟧</strong></article>
      <div className="example-outcome"><span>AI helps find the answer.</span><strong>PrivaGraph restores the real value locally.</strong></div>
    </section>
    <section className="anatomy-card" aria-label="Animated PrivaGraph workflow model">
      <div className="anatomy-card-top"><span><b>FIG. 01</b> / PRIVACY RELAY</span><span>MODEL · MULTI-STAGE / 3D CUTAWAY</span></div>
      <div className="machine-wrap"><div className="zone-label zone-local"><span/> LOCAL TRUST ZONE</div><div className="zone-label zone-cloud"><span/> EXTERNAL / UNTRUSTED</div><Machine step={step}/></div>
      <div className="anatomy-card-bottom"><span>SELECT A STAGE TO TRACE THE SIGNAL</span><span>HOVER TO INSPECT · MOTION IS EASED</span></div>
    </section>
    <section className="anatomy-details">
      <div className="stage-list" role="tablist" aria-label="Workflow stages">{stages.map((stage,index)=><button key={stage.title} role="tab" aria-selected={step===index} className={`stage-button ${step===index?'selected':''}`} onClick={()=>setStep(index)}><span className="stage-icon">{stage.icon}</span><span className="stage-copy"><small>{stage.tag}</small><strong>{stage.title}</strong></span><span className="stage-index">0{index+1}</span></button>)}</div>
      <article className="stage-explainer" key={step}><div className="explainer-overline">CURRENT OPERATION <span> / 0{step+1}</span></div><h2>{stages[step].title}</h2><p>{stages[step].detail}</p><div className="flow-readout"><span>DATA FLOW</span><strong>{step < 2 ? 'SOURCE → LOCAL PROCESSING' : step === 2 ? 'PLAINTEXT → ENCRYPTED VAULT' : step === 3 ? 'SCOPED GRAPH CONTEXT' : 'TOKENIZED CONTEXT → CLOUD'}</strong></div></article>
    </section>
    <footer className="anatomy-foot"><span>WHY THIS MATTERS</span><p>Teams can ask questions across sensitive documents while PrivaGraph keeps the real identity-to-value mapping in its encrypted local vault.</p><span className="mono-foot">FILES → PRIVATE GRAPH → SAFER AI</span></footer>
  </main>;
}

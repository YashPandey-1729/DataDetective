import {useEffect, useRef, useState} from 'react';
import {Activity, ArrowDownToLine, ArrowRight, ArrowUpRight, BarChart3, CheckCircle2, ChevronRight, CircleHelp, Database, FileChartColumn, FileText, Fingerprint, FlaskConical, GitBranch, Image, Layers3, LoaderCircle, Plus, Search, ShieldCheck, Sparkles, X, AlertCircle, Rows3, Columns3} from 'lucide-react';
import {api, ApiError, upload} from './api';
import {validateUpload} from './uploadValidation';
import {formatNumber} from './formatNumber';
import type {Dataset, Investigation, ModelOption} from './types';
import FileUploader from './components/FileUploader';
import DatasetPreview from './components/DatasetPreview';
import AgentTimeline from './components/AgentTimeline';
import ChartViewer from './components/ChartViewer';
import ReportViewer from './components/ReportViewer';
import EvidenceLink from './components/EvidenceLink';
import VisionContext from './components/VisionContext';
import ModelSelector from './components/ModelSelector';
import StatisticsWorkbench from './components/StatisticsWorkbench';

const examples = ['Why did revenue decline in February? Compare regions, then investigate products in the region contributing most.','Find unusual patterns and potential outliers in this dataset.','Compare category performance and identify the largest differences.'];
type Health = {ai_configured: boolean; model: string; models?: ModelOption[]};
export default function App() {
  const [health,setHealth] = useState<Health | null>(null);
  const [dataset,setDataset] = useState<Dataset | null>(null);
  const [investigation,setInvestigation] = useState<Investigation | null>(null);
  const [question,setQuestion] = useState(examples[0]);
  const [mode,setMode] = useState<'agent' | 'offline'>('agent');
  const [selectedModel,setSelectedModel] = useState('');
  const [section,setSection] = useState('workspace');
  const [busy,setBusy] = useState('');
  const [error,setError] = useState('');
  const [pollError,setPollError] = useState('');
  const [pollPaused,setPollPaused] = useState(false);
  const [checkingHealth,setCheckingHealth] = useState(false);
  const [image,setImage] = useState<{id: string; name: string; url: string} | null>(null);
  const imageUrl = useRef<string | null>(null);
  const actionBusy = useRef(false);
  const active = investigation?.status === 'running' || investigation?.status === 'queued';
  const locked = !!busy || (active && !pollPaused);
  const modelOptions: ModelOption[] = health?.models ?? (health ? [{id:health.model,label:health.model}] : []);
  const selectedOption = modelOptions.find(model => model.id === selectedModel);
  const selectedAvailable = selectedOption?.available ?? !!health?.ai_configured;
  const localSelected = selectedOption?.provider === 'ollama' || selectedModel.startsWith('ollama:');

  async function checkHealth(signal?: AbortSignal) {
    setCheckingHealth(true);
    try { const h = await api<Health>('/health', {signal}, 10_000); setHealth(h); setMode(current => h.ai_configured ? current : 'offline'); setSelectedModel(current => {const options = h.models ?? [{id:h.model,label:h.model,available:h.ai_configured}]; return options.some(model => model.id === current) ? current : (options.find(model => model.id === h.model && model.available !== false) ?? options.find(model => model.available !== false))?.id ?? h.model;}); setError(''); }
    catch (e) {if ((e as Error).name !== 'AbortError') {setHealth(null); setError('Cannot reach the backend. Start FastAPI on port 8000, then reconnect.');}}
    finally {if (!signal?.aborted) setCheckingHealth(false);}
  }
  useEffect(() => {const controller = new AbortController(); void checkHealth(controller.signal); return () => {controller.abort(); if (imageUrl.current) URL.revokeObjectURL(imageUrl.current);};}, []);
  useEffect(() => {
    if (!investigation || !active || pollPaused) return;
    const controller = new AbortController();
    let cancelled = false; let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {const next = await api<Investigation>(`/investigations/${investigation!.id}`, {signal:controller.signal}, 15_000); if (!cancelled) {setInvestigation(next); setPollError(''); if (['queued','running'].includes(next.status)) timer = setTimeout(poll,1000);}}
      catch (e) {if (!cancelled) {
        if (e instanceof ApiError && (e.status === 404 || e.status === 410)) {
          setPollError('This investigation is no longer available. Its session may have expired or the backend restarted. Start a new investigation and upload the dataset again.');
          setPollPaused(true);
        } else {setPollError('Progress updates are temporarily unavailable. Retrying the connection…'); timer = setTimeout(poll,3000);}
      }}
    }
    timer = setTimeout(poll,500);
    return () => {cancelled = true; clearTimeout(timer); controller.abort();};
  }, [investigation?.id,active,pollPaused]);

  function clearImage() {
    if (imageUrl.current) URL.revokeObjectURL(imageUrl.current);
    imageUrl.current = null;
    setImage(null);
  }
  function prepareDataset(next: Dataset) {
    history.replaceState(null, '', location.pathname); clearImage(); setDataset(next); setInvestigation(null); setPollError(''); setPollPaused(false); setSection('workspace');
  }

  async function loadFile(file: File) {
    if (actionBusy.current || locked) return;
    const validation = validateUpload(file, false); if (validation) {setError(validation); return;}
    actionBusy.current = true;
    setBusy('dataset'); setError('');
    try {prepareDataset(await upload<Dataset>('/datasets',file));}
    catch (e) {setError((e as Error).message);} finally {actionBusy.current = false; setBusy('');}
  }
  async function loadDemo(name = 'retail_sales') {
    if (actionBusy.current || locked) return;
    actionBusy.current = true;
    setBusy('demo'); setError('');
    try {prepareDataset(await api<Dataset>(`/demo/${name}`)); setQuestion(name === 'retail_sales' ? examples[0] : examples[1]);}
    catch (e) {setError((e as Error).message);} finally {actionBusy.current = false; setBusy('');}
  }
  async function loadImage(file: File) {
    if (actionBusy.current || locked) return;
    const validation = validateUpload(file, true); if (validation) {setError(validation); return;}
    actionBusy.current = true;
    setBusy('image'); setError('');
    try {const result = await upload<{id:string}>('/images',file); if (imageUrl.current) URL.revokeObjectURL(imageUrl.current); imageUrl.current=URL.createObjectURL(file); setImage({id:result.id,name:file.name,url:imageUrl.current});}
    catch (e) {setError((e as Error).message);} finally {actionBusy.current = false; setBusy('');}
  }
  async function start() {
    if (!dataset || actionBusy.current || locked || question.trim().length < 5) return;
    actionBusy.current = true; setBusy('start');setError('');setPollError('');setPollPaused(false);
    try {setInvestigation(await api<Investigation>('/investigations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dataset_id:dataset.id,question:question.trim(),mode,image_id:image?.id ?? null,...(health?.models ? {model:mode === 'agent' ? selectedModel || null : null} : {})})}));setSection('results');}
    catch (e) {setError((e as Error).message);} finally {actionBusy.current = false; setBusy('');}
  }
  function navigate(next: string) {setSection(next); document.getElementById(next === 'report' ? 'report' : next === 'results' ? 'results' : 'workspace')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'start'});}
  function reset() {if (locked) return; clearImage();setDataset(null);setInvestigation(null);setQuestion(examples[0]);setSection('workspace');setError('');setPollError('');setPollPaused(false);navigate('workspace');}
  const p = dataset?.profile;
  const verified = investigation?.evidence.filter(e => e.tool === 'verify_finding' && e.result.status === 'verified') || [];
  const anomalies = investigation?.evidence.find(e => e.tool === 'calculate_statistics' && e.result.method);
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="#" onClick={e => {e.preventDefault();navigate('workspace');}}><span className="brand-icon"><Fingerprint size={25}/></span><span>DataDetective<span className="brand-ai">AI</span><small>INTELLIGENCE, INVESTIGATED.</small></span></a>
      <button className="new-button" onClick={reset} disabled={locked}><Plus size={17}/>New investigation<span>↗</span></button>
      <span className="nav-label">WORKSPACE</span><nav aria-label="Workspace sections">{[{id:'workspace',icon:Database,label:'Dataset workspace'},{id:'results',icon:Activity,label:'Investigation results'},{id:'report',icon:FileText,label:'Reports'}].map(n => <button key={n.id} className={section === n.id ? 'selected' : ''} aria-current={section === n.id ? 'page' : undefined} disabled={n.id === 'report' && !investigation?.report} onClick={() => navigate(n.id)}><n.icon size={17}/>{n.label}{section === n.id && <span className="nav-dot"/>}</button>)}</nav>
      <div className="sidebar-datasets"><span className="nav-label">CURRENT DATASET</span>{dataset ? <div className="dataset-link"><FileChartColumn size={15}/><span>{dataset.name}<small>{p?.rows.toLocaleString()} records</small></span><span className="green-dot"/></div> : <p>Your next discovery<br/>starts with a dataset.</p>}</div>
      <div className="sidebar-bottom"><div className="agent-note"><GitBranch size={20}/><h4>Follow the evidence.</h4><p>Every tool call leaves a trail. Every number has a source.</p><span>Plan → Execute → Verify</span></div><a href="https://ai.google.dev/gemini-api/docs/api-key" target="_blank" rel="noreferrer" className="help"><CircleHelp size={16}/>Google AI setup guide<ArrowUpRight size={13}/></a><div className="workspace-user"><span>DD</span><div>Hackathon workspace<small>Local session · 2-hour retention</small></div></div></div>
    </aside>
    <div className="main-shell"><header className="topbar"><div><span>Workspace</span><ChevronRight size={13}/><strong>{section === 'report' ? 'Investigation report' : section === 'results' ? 'Investigation results' : 'Dataset investigation'}</strong></div><div className="connection"><span className={health ? 'green-dot' : 'amber-dot'}/>{health ? 'Backend connected' : 'Backend offline'}<span className="topbar-divider"/><span className="pill">LOCAL WORKSPACE</span></div></header>
      <nav className="mobile-nav" aria-label="Workspace sections">{[['workspace','Dataset'],['results','Results'],['report','Report']].map(([id,label]) => <button key={id} className={section === id ? 'selected' : ''} aria-current={section === id ? 'page' : undefined} disabled={id === 'report' && !investigation?.report} onClick={() => navigate(id)}>{label}</button>)}</nav>
      <main id="workspace"><div className="page-heading"><div><div className="eyebrow"><span className="cyan-dot"/>YOUR AUTONOMOUS DATA PARTNER</div><h1>Good questions. <span>Verified discoveries.</span></h1><p>Bring your data. Follow the clues. Let the evidence tell the story.</p></div><button className="button secondary" disabled={locked} onClick={() => void loadDemo()}>{busy === 'demo' ? <LoaderCircle className="spin" size={15}/> : <FlaskConical size={16}/>}Load sample data</button></div>
      <div className={`configuration ${health?.ai_configured ? 'configured' : ''}`}><span className="config-icon">{health?.ai_configured ? <Sparkles size={18}/> : <CircleHelp size={18}/>}</span><div><strong>{health?.ai_configured ? `${selectedOption?.label || health.model} is selected` : 'Explore now. Connect Gemini or local Gemma for AI investigations.'}</strong><p>{health?.ai_configured ? (selectedAvailable ? 'The agent chooses each step from actual observations. Model access is checked when an investigation starts.' : selectedOption?.reason || 'This model is not ready. Complete setup, then reconnect.') : 'Offline analytics runs real queries. Start Ollama and download Gemma, or configure GEMINI_API_KEY, then reconnect.'}</p></div><button onClick={() => void checkHealth()} disabled={checkingHealth || locked} className="text-button">Reconnect <ArrowRight size={14}/></button></div>
      {error && <div className="error-banner" role="alert"><AlertCircle size={18}/><span>{error}</span><button aria-label="Dismiss error" onClick={() => setError('')}><X size={16}/></button></div>}
      {pollError && <div className="error-banner" role="status"><AlertCircle size={18}/><span>{pollError}</span>{pollPaused && <button className="text-button" onClick={reset}>New investigation</button>}</div>}
      <div className="metrics-grid">{[{label:'Records available',value:p?.rows.toLocaleString() ?? '—',icon:Rows3,detail:dataset ? 'Ready for analysis' : 'Upload a dataset to begin'},{label:'Data dimensions',value:p?.column_count ?? '—',icon:Columns3,detail:p ? `${p.metrics.length} metrics · ${p.dimensions.length} categories` : 'Automatic schema detection'},{label:'Data completeness',value:p ? `${(100*(1-p.missing/(p.rows*p.column_count))).toFixed(1)}%` : '—',icon:Layers3,detail:p ? `${p.missing.toLocaleString()} missing cells · ${p.duplicates} duplicates` : 'Quality checks included'},{label:'Verified numeric cells',value:investigation ? verified.length : '—',icon:ShieldCheck,detail:investigation ? `${investigation.evidence.length} evidence records collected` : 'Recomputed from source queries'}].map(m => <div className="metric-card" key={m.label}><div><span>{m.label}</span><m.icon size={17}/></div><strong>{m.value}</strong><small>{m.detail}</small></div>)}</div>
      <div className="workspace-grid"><div className="workspace-left"><section className="panel source-panel"><div className="panel-head"><div><span className="eyebrow">01 / CONNECT</span><h3>Your investigation starts here</h3></div><Database size={18} className="muted"/></div><div className="source-content"><FileUploader busy={busy === 'dataset' || busy === 'demo'} disabled={locked} onFile={file => void loadFile(file)}/>{dataset && <div className="loaded-file"><span className="file-icon"><FileChartColumn size={19}/></span><div><strong>{dataset.name}</strong><small>Profiled successfully · {p?.rows.toLocaleString()} rows</small></div><CheckCircle2 size={18}/></div>}<div className="source-divider"><span>VISUAL CONTEXT</span><span>Optional</span></div>{image ? <div className="image-preview"><img src={image.url} alt="Uploaded chart reference"/><div><strong>{image.name}</strong><small>{mode === 'offline' ? 'Not interpreted in offline mode' : 'Ready for vision analysis'}</small></div><button disabled={locked} aria-label="Remove image" onClick={clearImage}><X size={16}/></button></div> : <FileUploader image busy={busy === 'image'} disabled={locked} onFile={file => void loadImage(file)}/>}</div><div className="sample-strip"><FlaskConical size={14}/><span>Synthetic demos</span>{['retail_sales','sensor_data','student_performance'].map((n,i) => <button key={n} onClick={() => void loadDemo(n)} disabled={locked}>{['Retail','Sensors','Students'][i]}<ArrowUpRight size={11}/></button>)}</div></section>
      <section className="panel investigator-panel"><div className="panel-head"><div><span className="eyebrow">02 / INVESTIGATE</span><h3><Sparkles size={17}/>Ask a better question</h3></div><span className="pill cyan">{mode === 'agent' ? 'AI agent' : 'Offline rules'}</span></div><div className="question-body"><label htmlFor="question">What would you like to uncover?</label><textarea id="question" maxLength={2000} value={question} disabled={locked} onChange={e => setQuestion(e.target.value)} placeholder="Ask about a trend, a difference, or something that doesn't look right…"/><div className="example-prompts">{['Investigate a decline','Find anomalies','Compare categories'].map((s,i) => <button disabled={locked} key={s} onClick={() => setQuestion(examples[i])}>{s}<ArrowUpRight size={11}/></button>)}</div>{mode === 'agent' && <ModelSelector models={modelOptions} value={selectedModel} disabled={locked || !health} onChange={setSelectedModel}/>} {mode === 'agent' && selectedOption?.available === false && <p role="status" className="privacy-note">{selectedOption.reason} Complete setup, then click Reconnect.</p>}<div className="investigator-actions"><label className="mode-select"><select aria-label="Investigation mode" value={mode} disabled={locked} onChange={e => setMode(e.target.value as 'agent' | 'offline')}><option value="agent">Autonomous AI agent</option><option value="offline">Offline analytics · no AI</option></select></label><button className="button primary" onClick={() => void start()} disabled={!dataset || question.trim().length < 5 || locked || (mode === 'agent' && !selectedAvailable)}>{active || busy === 'start' ? <LoaderCircle className="spin" size={16}/> : <Search size={16}/>} {active ? 'Investigating…' : 'Start investigation'}{!active && <ArrowRight size={15}/>}</button></div><p className="privacy-note"><ShieldCheck size={12}/>{mode === 'agent' ? (localSelected ? 'Questions, images and tool results are processed by local Ollama on this machine. No Google API key is required.' : 'Dataset samples, images and tool results are sent to Google AI. Credentials stay on the backend.') : 'Offline mode uses fixed analytical rules; it does not interpret your question or image.'}</p></div></section></div><AgentTimeline investigation={investigation} paused={pollPaused}/></div>
      {dataset && <><DatasetPreview dataset={dataset}/><StatisticsWorkbench key={dataset.id} dataset={dataset} disabled={locked}/></>}
      <section id="results" className="results-section"><div className="section-title"><div><span className="eyebrow">03 / DISCOVER</span><h2>Evidence, connected.</h2></div><span className="pill">{investigation?.mode === 'offline' ? 'Deterministic offline analysis' : 'Computed from your data'}</span></div>
      {!investigation ? <div className="results-placeholder"><div><BarChart3 size={24}/><h3>There’s a story in your data.</h3><p>Start an investigation to uncover trends, contributing segments, and unexpected patterns.</p></div><div className="ghost-chart" aria-hidden="true">{[25,38,30,60,50,75,56,89,68,92,79,100].map((h,i) => <i key={i} style={{height:h+'%'}}/>)}</div></div> : <>
      {investigation.status === 'partial' && <div className="partial-banner" role="status"><CircleHelp size={17}/><span>The investigation reached a resource limit. Available evidence is shown below; review its limitations before drawing conclusions.</span></div>}
      {investigation.mode === 'offline' && <p className="offline-label"><FlaskConical size={15}/>Offline analytics demo · Real computation, deterministic decisions · No LLM conclusions</p>}
      {investigation.status === 'failed' && <div className="error-banner"><AlertCircle size={18}/><span>{investigation.errors.at(-1)}</span><button className="text-button" onClick={() => void start()} disabled={locked}>Retry <ArrowRight size={14}/></button></div>}
      <div className="charts-grid">{investigation.charts.map((c,i) => <ChartViewer key={i} chart={c}/>)}</div>
      {anomalies && <div className="anomaly-banner"><Activity size={18}/><div><strong>{anomalies.result.count} outlier candidates identified</strong><span>IQR rule · descriptive flags for review, not confirmed errors</span></div><EvidenceLink id={anomalies.id}>Inspect evidence <ArrowUpRight size={14}/></EvidenceLink></div>}
      {verified.length > 0 && <div className="verification-ledger"><h3><ShieldCheck size={17}/>Numerical verification ledger</h3>{verified.map(e => <div key={e.id}><span className="pill green">Recomputed</span><code>{e.result.field} = {e.result.actual === undefined ? '—' : formatNumber(e.result.actual)}</code><EvidenceLink id={e.id}>{e.id} · source {e.result.evidence_id} ↗</EvidenceLink></div>)}<small>Verification covers the exact numeric cell only. It does not establish causality or validate all narrative claims.</small></div>}
      {investigation.findings.length > 0 && <div className="findings-grid">{investigation.findings.map((f,i) => <article className="panel finding-card" key={i}><div><span className="finding-number">{String(i+1).padStart(2,'0')}</span><span className={`pill ${f.status === 'inconclusive' ? '' : 'cyan'}`}>{f.kind} · {f.status}</span></div><p>{f.claim}</p>{f.measurements?.length ? <div className="finding-measurements">{f.measurements.map((m,j) => <div key={j}><strong>{m.field}: {formatNumber(m.value)}</strong><small>{Object.entries(m.context || {}).map(([key,value]) => `${key}: ${String(value)}`).join(' · ')}</small><EvidenceLink id={m.evidence_id}>{m.evidence_id} · {m.verification === 'verified' ? 'Recomputed' : 'Computed source value'} ↗</EvidenceLink></div>)}</div> : null}<div className="finding-refs">{f.evidence_ids.map(id => <EvidenceLink id={id} key={id}>{id}<ArrowUpRight size={11}/></EvidenceLink>)}</div></article>)}</div>}
      {investigation.report && <ReportViewer investigation={investigation}/>}
      {investigation.image_context && <VisionContext context={investigation.image_context}/>}
      {investigation.evidence.length > 0 && <section className="panel evidence-panel"><div className="panel-head"><div><span className="eyebrow">AUDITABLE BY DESIGN</span><h3>Evidence & executed queries</h3></div><span className="pill">{investigation.evidence.length} records</span></div>{investigation.evidence.map(e => <details id={e.id} key={e.id}><summary><code>{e.id}</code><strong>{e.tool}</strong>{e.result.sql && <span>Read-only SQL</span>}<ChevronRight size={15}/></summary>{e.result.sql && <pre className="sql-code">{e.result.sql}</pre>}<pre>{JSON.stringify(e.result,null,2)}</pre></details>)}</section>}
      {investigation.errors.length > 0 && <details className="panel errors-details"><summary>Execution notices ({investigation.errors.length})</summary><ul>{investigation.errors.map((e,i) => <li key={i}>{e}</li>)}</ul></details>}
      </>}</section><footer><span><Fingerprint size={15}/>DataDetective AI</span><p>From raw data to verified discoveries — autonomously.</p><span>Built for curious minds.<ArrowDownToLine size={13}/></span></footer>
      </main></div>
  </div>;
}

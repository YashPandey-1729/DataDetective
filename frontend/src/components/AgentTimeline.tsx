import {Activity, Check, Circle, LoaderCircle, X, SkipForward} from 'lucide-react';
import type {Investigation} from '../types';
import EvidenceLink from './EvidenceLink';
export default function AgentTimeline({investigation, paused = false}: {investigation: Investigation | null; paused?: boolean}) {
  return <section className="panel timeline-panel"><div className="panel-head"><div><span className="eyebrow">OBSERVE THE PROCESS</span><h3><Activity size={17}/>Investigation activity</h3></div><span role="status" className={`pill ${investigation?.status === 'running' && !paused ? 'cyan' : ''}`}>{paused ? 'Updates unavailable' : investigation?.status || 'Standby'}</span></div>
    {!investigation ? <div className="timeline-empty"><span className="orb"><Activity size={25}/></span><h4>Every discovery has a trail.</h4><p>Watch decisions, tool executions, and evidence appear as your investigation unfolds.</p><div className="mini-flow"><span>Plan</span><i>→</i><span>Investigate</span><i>→</i><span>Verify</span></div></div> : <>
    {investigation.plan.length > 0 && <details className="plan"><summary>Investigation plan · {investigation.plan.length} steps</summary><ol>{investigation.plan.map((p,i) => <li key={i}>{p}</li>)}</ol></details>}
    <div className="timeline">{investigation.events.map(e => <div className={`event ${e.status}`} key={e.id}><span className="event-dot" role="img" aria-label={e.status}>{e.status === 'completed' ? <Check size={12}/> : e.status === 'failed' ? <X size={12}/> : e.status === 'running' ? <LoaderCircle className="spin" size={12}/> : e.status === 'skipped' ? <SkipForward size={12}/> : <Circle size={12}/>}</span><div><div className="event-label"><code>{e.tool}</code><small>{new Date(e.time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})}</small></div><p>{e.description}</p>{e.evidence_id && <EvidenceLink id={e.evidence_id}>{e.evidence_id} · view evidence ↗</EvidenceLink>}{e.error && <small className="error-text">{e.error}</small>}</div></div>)}</div>
    {investigation.status === 'queued' && <p className="muted padded">Waiting for an available investigator…</p>}</>}
  </section>;
}

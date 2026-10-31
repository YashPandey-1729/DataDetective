import {Component, lazy, Suspense, type ReactNode} from 'react';
import type {Chart} from '../types';
import EvidenceLink from './EvidenceLink';
const Plot = lazy(() => import('./Plot'));
class ChartBoundary extends Component<{children: ReactNode; evidenceId: string}, {failed: boolean}> {
  state = {failed: false};
  static getDerivedStateFromError() {return {failed:true};}
  render() {return this.state.failed ? <div className="chart-loading chart-error" role="alert"><p>The chart could not be displayed. Your computed results are still available.</p><EvidenceLink id={this.props.evidenceId}>Inspect source evidence ↗</EvidenceLink></div> : this.props.children;}
}
export default function ChartViewer({chart}: {chart: Chart}) {
  return <section className="panel chart-panel" aria-label={chart.title}><div className="panel-head"><h3>{chart.title}</h3><EvidenceLink className="pill" id={chart.evidence_id}>{chart.evidence_id} ↗</EvidenceLink></div><ChartBoundary key={chart.evidence_id + chart.title} evidenceId={chart.evidence_id}><Suspense fallback={<div className="chart-loading" role="status">Loading interactive chart…</div>}><Plot chart={chart}/></Suspense></ChartBoundary>{chart.truncated && <small className="padded muted">Chart displays a truncated result.</small>}</section>;
}

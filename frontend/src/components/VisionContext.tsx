import {Image, CircleHelp} from 'lucide-react';

export default function VisionContext({context}: {context: Record<string, unknown>}) {
  const fields = [['axes','Visible axes'],['metrics','Metrics'],['categories','Categories'],['time_periods','Time periods'],['highlighted_regions','Highlighted regions'],['matching_columns','Matched dataset columns'],['visible_patterns','Visual observations'],['ambiguities','Ambiguities']] as const;
  const text = (value: unknown) => Array.isArray(value) ? value.map(String) : typeof value === 'string' && value ? [value] : [];
  return <section className="panel vision-panel"><div className="panel-head"><h3><Image size={17}/>Chart interpretation</h3><span className="pill">{String(context.chart_type || 'Unknown chart')}</span></div><p className="vision-notice"><CircleHelp size={15}/>Visual context guides the investigation. Image estimates are not verified numerical evidence.</p><div className="vision-grid">{fields.map(([field,label]) => {
    const values = text(context[field]);
    return <div key={field} className={field === 'ambiguities' ? 'vision-ambiguities' : ''}><h4>{label}</h4>{values.length ? <ul>{values.map((value,index) => <li key={index}>{value}</li>)}</ul> : <p>{field === 'ambiguities' ? 'None reported by the model.' : 'Not identified in the image.'}</p>}</div>;
  })}</div><details><summary>Inspect structured interpretation</summary><pre>{JSON.stringify(context,null,2)}</pre></details></section>;
}

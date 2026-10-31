import {Database, Hash, CalendarDays, Type} from 'lucide-react';
import type {Dataset} from '../types';
export default function DatasetPreview({dataset}: {dataset: Dataset}) {
  const p = dataset.profile;
  return <section className="panel" id="dataset-preview"><div className="panel-head"><div><span className="eyebrow">DATA EXPLORER</span><h3><Database size={16}/>{dataset.name}</h3></div><span className="pill">First {p.preview.length} rows</span></div>
    <div className="table-scroll"><table><thead><tr>{p.columns.map(c => <th key={c.name}><span className="column-title">{c.kind === 'numeric' ? <Hash size={12}/> : c.kind === 'date' ? <CalendarDays size={12}/> : <Type size={12}/>} {c.name}</span><small>{c.kind} · {c.missing} missing</small></th>)}</tr></thead>
    <tbody>{p.preview.map((row, i) => <tr key={i}>{p.columns.map(c => <td key={c.name}>{row[c.name] === null ? <em>null</em> : String(row[c.name]).replace('T00:00:00.000','')}</td>)}</tr>)}</tbody></table></div>
    <div className="table-footer"><span>{p.rows.toLocaleString()} rows · {p.column_count} columns</span><span>{p.duplicates} potential duplicates · {p.missing} missing cells</span></div>
    <details className="schema-details"><summary>Column statistics & schema</summary><div className="schema-grid">{p.columns.map(c => <div key={c.name}><strong>{c.name}</strong><small>{c.dtype} · {c.unique.toLocaleString()} unique</small>{c.summary && <span>Mean {c.summary.mean?.toLocaleString(undefined,{maximumFractionDigits:2}) ?? '—'} · Range {c.summary.min} – {c.summary.max}</span>}</div>)}</div></details>
  </section>;
}

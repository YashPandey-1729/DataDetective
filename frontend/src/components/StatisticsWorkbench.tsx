import {useEffect,useRef,useState} from 'react';
import {Calculator,ChevronDown,Download,LoaderCircle} from 'lucide-react';
import {api} from '../api';
import {formatNumber} from '../formatNumber';
import {parameterDefaults,statisticalRequest,resultSource,type StatisticalDefinition} from '../statistics';
import type {Dataset} from '../types';

interface Catalog {operations:{name:string;category:string;description:string}[];excel_functions:{name:string}[]}
export default function StatisticsWorkbench({dataset,disabled}:{dataset:Dataset;disabled:boolean}) {
  const [catalog,setCatalog]=useState<Catalog|null>(null);
  const [selection,setSelection]=useState('summary');
  const [definition,setDefinition]=useState<StatisticalDefinition|null>(null);
  const [fields,setFields]=useState<Record<string,string>>({});
  const [parameters,setParameters]=useState('{}');
  const [result,setResult]=useState<Record<string,unknown>|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const [loading,setLoading]=useState(false);
  const [retry,setRetry]=useState(0);
  const request=useRef<AbortController|null>(null);
  useEffect(()=>{
    const controller=new AbortController();
    api<Catalog>('/statistics/catalog',{signal:controller.signal}).then(setCatalog).catch(e=>{if(e.name!=='AbortError')setError(e.message);});
    return ()=>controller.abort();
  },[retry]);
  useEffect(()=>{
    const controller=new AbortController();setLoading(true);setDefinition(null);setResult(null);setError('');
    api<StatisticalDefinition>(`/statistics/catalog?name=${encodeURIComponent(selection)}`,{signal:controller.signal}).then(next=>{
      setDefinition(next);setParameters(JSON.stringify(parameterDefaults(next,dataset.profile.metrics),null,2));
      setFields({column:dataset.profile.metrics[0] || dataset.profile.columns[0]?.name || '',other_column:dataset.profile.metrics[1] || '',group_by:dataset.profile.dimensions[0] || '',before:'',after:''});
    }).catch(e=>{if(e.name!=='AbortError')setError(e.message);}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[selection,dataset.id,retry]);
  useEffect(()=>()=>request.current?.abort(),[]);
  async function calculate() {
    if (!definition || busy || request.current) return;
    const controller=new AbortController();request.current=controller;setBusy(true);setError('');setResult(null);
    try {
      const body=statisticalRequest(definition,fields,parameters);
      setResult(await api<Record<string,unknown>>(`/datasets/${dataset.id}/statistics`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal},60000));
    } catch(e) {if((e as Error).name!=='AbortError')setError((e as Error).message);}
    finally {request.current=null;setBusy(false);}
  }
  function download() {
    const url=URL.createObjectURL(new Blob([JSON.stringify({dataset:dataset.name,selection,result},null,2)],{type:'application/json'}));
    const link=document.createElement('a');link.href=url;link.download='computed-statistics.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  const rows=Array.isArray(result?.rows) ? result.rows as Record<string,unknown>[] : [];
  const scalars=result ? Object.entries(result).filter(([key,value])=>typeof value==='number' && !['row_count','total_rows'].includes(key)) : [];
  const render=(value:unknown)=>typeof value==='number'?formatNumber(value):value===null?'—':typeof value==='object'?JSON.stringify(value):String(value);
  return <section className="panel statistics-panel" aria-label="Statistics workbench"><div className="panel-head"><div><span className="eyebrow">COMPUTE DIRECTLY</span><h3><Calculator size={17}/>Statistics workbench</h3></div><span className="pill cyan">No AI key required</span></div><div className="statistics-body">
    <p className="statistics-intro">Run a calculation on your uploaded dataset. Results come from the statistical engine and remain separate from the AI investigation.</p>
    <div className="statistics-fields"><label>Analysis<select value={selection} disabled={busy||disabled} onChange={e=>setSelection(e.target.value)}>{catalog ? [...new Set(catalog.operations.map(o=>o.category))].map(category=><optgroup key={category} label={category.replaceAll('_',' ')}>{catalog.operations.filter(o=>o.category===category&&o.name!=='excel').map(o=><option key={o.name} value={o.name}>{o.name.replaceAll('_',' ')}</option>)}</optgroup>) : <option value="summary">summary</option>}{catalog && <optgroup label="Excel statistical functions">{catalog.excel_functions.map(f=><option key={f.name} value={f.name}>{f.name}</option>)}</optgroup>}</select></label>
    {definition?.required_arguments?.map(field=><label key={field}>{field.replaceAll('_',' ')}{['before','after'].includes(field)?<input type="number" step="any" value={fields[field]||''} disabled={busy||disabled} onChange={e=>setFields({...fields,[field]:e.target.value})}/>:<select value={fields[field]||''} disabled={busy||disabled} onChange={e=>setFields({...fields,[field]:e.target.value})}><option value="">Select a column</option>{dataset.profile.columns.map(c=><option key={c.name} value={c.name}>{c.name} · {c.kind}</option>)}</select>}</label>)}</div>
    {definition && <><p className="statistics-description">{definition.description}</p>{definition.assumptions&&<p className="statistics-assumptions">{definition.assumptions}</p>}<details className="statistics-options"><summary>Advanced options <ChevronDown size={12}/></summary><label htmlFor="statistics-options">Named calculation parameters (JSON)</label><textarea id="statistics-options" value={parameters} disabled={busy||disabled} onChange={e=>setParameters(e.target.value)}/><details><summary>Parameter definitions and required fields</summary><pre>{JSON.stringify(definition.parameters_schema,null,2)}</pre></details>{definition.note&&<p>{definition.note}</p>}</details></>}
    {error&&<div className="error-banner" role="alert"><span>{error}</span>{!definition&&<button onClick={()=>setRetry(retry+1)}>Retry connection</button>}</div>}
    <div className="statistics-actions"><button className="button primary" disabled={busy||loading||!definition||disabled} onClick={()=>void calculate()}>{busy||loading?<LoaderCircle className="spin" size={15}/>:<Calculator size={15}/>} {busy?'Calculating…':loading?'Loading analysis…':'Calculate'}</button>{result&&<button className="button secondary" onClick={download}><Download size={14}/>Export result</button>}</div>
    {result&&<div className="statistics-output" role="region" aria-label="Computed statistics"><span className="pill">{resultSource(result)} · {selection}</span><div className="statistics-metrics">{scalars.map(([key,value])=><div key={key}><small>{key.replaceAll('_',' ')}</small><strong>{formatNumber(value as number)}</strong></div>)}</div>{typeof result.assumptions==='string'&&<p className="statistics-assumptions">{result.assumptions}</p>}{typeof result.note==='string'&&<p className="statistics-description">{result.note}</p>}{result.truncated===true&&<p className="statistics-assumptions">The result is truncated to its retained rows.</p>}{rows.length>0&&<div className="table-scroll"><table><thead><tr>{Object.keys(rows[0]).map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{Object.keys(rows[0]).map(k=><td key={k}>{render(row[k])}</td>)}</tr>)}</tbody></table></div>}<details className="statistics-options"><summary>Full calculation result</summary><pre>{JSON.stringify(result,null,2)}</pre></details></div>}
  </div></section>;
}

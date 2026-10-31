import asyncio
import json
import os
import math
from datetime import datetime, timezone
from google import genai
from google.genai import types
from backend.agent.schemas import AgentAction, ToolArgs, AgentReport
from backend.agent.prompts import SYSTEM, LOCAL_SYSTEM
from backend.agent.tool_contracts import validate_tool_arguments
from backend.services.sessions import datasets, images
from backend.services.reporting import finalize_report
from backend.services.gemini import generate_structured
from backend.services.models import default_model, is_local_model
from backend.services import ollama
from backend.tools.profiler import profile_dataset
from backend.tools.sql_engine import execute_sql
from backend.tools.statistics import calculate_statistics
from backend.tools.statistical_catalog import describe_statistics
from backend.tools.charts import generate_chart
from backend.tools.verifier import verify_finding
from backend.tools.vision import inspect_image

gate = asyncio.Semaphore(2)


def event(state, tool, description, status='running'):
    item = {'id':len(state['events'])+1,'tool':tool,'description':description,'status':status,
            'time':datetime.now(timezone.utc).isoformat()}
    state['events'].append(item)
    return item


def evidence(state, tool, result):
    item = {'id':f"E{len(state['evidence'])+1:02d}",'tool':tool,'result':result}
    state['evidence'].append(item)
    return item


class InvestigationAgent:
    def __init__(self, state, client=None):
        self.state = state
        self.dataset = datasets[state['dataset_id']]
        self.client = client
        self.model = state.get('model') or default_model()
        # Hold an image reference while queued/running; expiry must not invalidate a job.
        self.image = images.get(state.get('image_id'))

    async def tool(self, action):
        s=self.state; args=action.args; df=self.dataset.df
        if action.tool=='profile_dataset':
            return profile_dataset(df)
        if action.tool=='execute_sql':
            return await asyncio.to_thread(execute_sql, df, args.sql or '')
        if action.tool=='calculate_statistics':
            return await asyncio.to_thread(calculate_statistics, df, args,s['evidence'])
        if action.tool=='statistics_catalog':
            return describe_statistics(args.name or 'all',args.category)
        if action.tool=='generate_chart':
            src = next((e for e in s['evidence'] if e['id']==args.evidence_id and e['tool'] in {'execute_sql','calculate_statistics'}),None)
            if not src:
                raise ValueError('Select existing tabular evidence for the chart.')
            chart=generate_chart(src['result'],args); s['charts'].append(chart)
            return chart
        if action.tool=='verify_finding':
            return await asyncio.to_thread(verify_finding, df, s['evidence'], args, execute_sql)
        if action.tool=='inspect_image':
            if s['image_context']:
                return s['image_context']
            if not s['image_id'] or not self.client:
                raise ValueError('Image understanding requires an image and an available AI model.')
            if not self.image:
                raise ValueError('Attached image is no longer available.')
            result=await inspect_image(self.client,self.model,self.image['bytes'],list(df.columns),on_retry=self.rate_limit_notice)
            s['image_context']=result
            return result
        raise ValueError('Unsupported tool.')

    async def execute(self, action):
        item=event(self.state,action.tool,action.explanation)
        item['input']=action.args.model_dump(exclude_none=True)
        try:
            validate_tool_arguments(action)
            result=await self.tool(action)
            entry=evidence(self.state,action.tool,result)
            item.update(status='completed',evidence_id=entry['id'])
            return entry
        except Exception as exc:
            # Model / transport errors can contain request metadata; do not expose them.
            message = str(exc)[:350] if isinstance(exc,ValueError) else 'Tool failed or timed out. Adjust the request or retry.'
            item.update(status='failed',error=message)
            self.state['errors'].append(message)
            return {'tool':action.tool,'error':message}

    async def generate(self, schema, context):
        if is_local_model(self.model):
            return await ollama.generate_structured(self.client,model=self.model,schema=schema,
                contents=json.dumps(context,ensure_ascii=False,default=str),system_instruction=LOCAL_SYSTEM,
                action_constraints=self.action_constraints() if schema is AgentAction else None)
        return await generate_structured(self.client,model=self.model,schema=schema,
            contents=json.dumps(context,ensure_ascii=False,default=str),
            system_instruction=SYSTEM,temperature=0.15,on_retry=self.rate_limit_notice)

    def action_constraints(self):
        tabular=[entry for entry in self.state['evidence']
                 if entry['tool'] in {'execute_sql','calculate_statistics'} and entry['result'].get('rows')]
        numeric_sql=[entry['id'] for entry in tabular if entry['tool']=='execute_sql'
                     and any(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
                             for row in entry['result']['rows'] for value in row.values())]
        constraints={'chart_evidence_ids':[entry['id'] for entry in tabular], 'verification_evidence_ids':numeric_sql}
        requests=[]
        for entry in reversed(self.state['evidence']):
            result=entry['result']
            if entry['tool']=='statistics_catalog' and result.get('kind') in {'operation','excel_function'}:
                request={'operation':result['operation'],**({'function':result['function']} if result.get('function') else {})}
                if request not in requests:requests.append(request)
        if requests:constraints['statistical_requests']=requests[:3]
        return constraints

    def rate_limit_notice(self, delay):
        event(self.state,'model',f'AI service rate limit: waiting {delay} seconds before a bounded retry.','completed')

    def context(self, remaining):
        def bounded(value, chars=240, count=12):
            if isinstance(value, str):
                return value if len(value) <= chars else value[:chars] + ' [text truncated]'
            if isinstance(value, list):
                return [bounded(v, chars, count) for v in value[:count]]
            if isinstance(value, dict):
                return {k: bounded(v, chars, count) for k,v in list(value.items())[:100]}
            return value
        observations=[]
        inputs={item.get('evidence_id'):item['input'] for item in self.state['events'] if 'input' in item and item.get('evidence_id')}
        row_limit=5 if is_local_model(self.model) else 35
        for e in self.state['evidence']:
            # Keep every evidence ID and bounded observations, not all raw dataset cells.
            result=e['result']
            if e['tool']=='generate_chart':
                result={'title':result['title'],'evidence_id':result['evidence_id']}
            if e['tool']=='statistics_catalog' and is_local_model(self.model):
                result={key:value for key,value in result.items() if key!='parameters_schema'}
                if result.get('kind')=='catalog':
                    # Keep the entire operation menu. Generic list clipping used
                    # to hide inference/time-series operations after item twelve.
                    result={**result,'operations':{item['name']:item['category'] for item in result.get('operations',[])},
                            'excel_functions':{item['name']:item['description'][:80] for item in result.get('excel_functions',[])[:12]}}
            if isinstance(result,dict) and isinstance(result.get('rows'),list):
                result={**result,'rows':result['rows'][:row_limit], 'context_rows_omitted':max(0,len(result['rows'])-row_limit)}
            clipped=bounded(result)
            if len(json.dumps(clipped,default=str)) > 6500:
                clipped=bounded(result,chars=80,count=1)
                if isinstance(clipped,dict): clipped['context_truncated']=True
            observations.append({**e,'result':clipped,**({'input':bounded(inputs[e['id']],chars=1200)} if e['id'] in inputs else {})})
        profile=self.dataset.profile
        schema={k:v for k,v in profile.items() if k not in {'columns','preview'}}
        schema['columns']=[{k:bounded(v) for k,v in c.items() if k not in {'summary','monthly_coverage'}} for c in profile['columns']]
        context={'question':self.state['question'],'schema':schema,'image_context':bounded(self.state['image_context']),
                'observations':observations,'recent_errors':self.state['errors'][-2:],'remaining_tool_calls':remaining,
                'failed_actions':bounded([{'tool':e['tool'],'args':e['input'],'error':e.get('error')}
                    for e in self.state['events'] if e['status']=='failed' and 'input' in e][-2:],chars=8000),
                'completion_requirements':self.completion_requirements(),
                'context_note':'Text and lists are bounded. Use aggregation tools rather than assuming omitted values. Full retained evidence is available to the user.'}
        # Profile evidence repeats schema and may contain enormous uploaded text cells.
        for observation in context['observations']:
            if observation['tool']=='profile_dataset': observation['result']={'note':'Full schema is provided in the top-level schema field.'}
        if len(json.dumps(context,default=str)) > 100_000:
            for observation in observations:
                if isinstance(observation['result'],dict) and 'rows' in observation['result']:
                    observation['result']={**observation['result'],'rows':[], 'context_truncated':True}
        if len(json.dumps(context,default=str)) > 100_000:
            for observation in observations:
                observation['result']={'context_truncated':True,'note':'Result exceeds planner context budget; aggregate or select fewer columns.'}
        return context

    def analytical_evidence(self):
        return [e for e in self.state['evidence'] if e['tool'] in {'execute_sql','calculate_statistics'}
                and not ('before' in e['result'] and 'after' in e['result'])
                and e['result'].get('source_type','dataset')=='dataset']

    def numeric_sql_cell(self):
        for e in self.state['evidence']:
            if e['tool']=='execute_sql':
                for i,row in enumerate(e['result'].get('rows',[])):
                    for field,value in row.items():
                        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):
                            return e,i,field,value
        return None

    def completion_requirements(self):
        unique={json.dumps([e['tool'],e['result']],sort_keys=True,default=str) for e in self.analytical_evidence()}
        missing=[]
        if len(unique)<2: missing.append('Perform at least two distinct successful analytical actions, with the second informed by the first observation.')
        if self.numeric_sql_cell():
            if not self.state['charts']: missing.append('Generate a chart from analytical evidence.')
            if not any(e['tool']=='verify_finding' and e['result'].get('status')=='verified' for e in self.state['evidence']):
                missing.append('Verify a numeric SQL cell.')
        return missing

    async def ensure_artifacts(self):
        """Transparent finalization only; never substitute fixed queries for model exploration."""
        cell=self.numeric_sql_cell()
        if not cell: return
        source,index,field,value=cell
        if not any(e['tool']=='verify_finding' and e['result'].get('status')=='verified' for e in self.state['evidence']):
            await self.execute(AgentAction(tool='verify_finding',explanation='System finalization: recompute a retained numeric cell; the model did not complete verification.',
                args=ToolArgs(evidence_id=source['id'],row=index,field=field,expected=value,claim='Computed numeric cell')))
        if not self.state['charts']:
            row=source['result']['rows'][index]
            x=next((k for k,v in row.items() if k!=field and isinstance(v,str)),field)
            await self.execute(AgentAction(tool='generate_chart',explanation='System finalization: create a chart from retained query evidence; no new analytical query is added.',
                args=ToolArgs(evidence_id=source['id'],chart_type='histogram' if x==field else 'bar',x=x,y=None if x==field else field,title='Computed evidence')))

    async def run_agent(self):
        if self.client is None:
            self.client=ollama.create_client() if is_local_model(self.model) else genai.Client(
                api_key=os.environ['GEMINI_API_KEY'],http_options=types.HttpOptions(timeout=45000))
        if self.state['image_id']:
            await self.execute(AgentAction(tool='inspect_image',explanation='Read the chart and compare its labels with the dataset schema.'))
        try: budget=max(2,min(int(os.getenv('MAX_AGENT_STEPS','8')),12))
        except ValueError: budget=8
        model_failures=0; tool_failures=0
        completed_actions={}; repeated_actions=0
        self.state['stop_reason']='step_budget_exhausted'
        for step in range(budget):
            try:
                action=await self.generate(AgentAction,self.context(budget-step))
            except Exception as exc:
                model_failures+=1
                self.state['errors'].append(str(exc)[:350] if is_local_model(self.model) and type(exc) is ValueError
                    else 'AI model request failed, timed out, or returned invalid structured output.')
                event(self.state,'model','Model request failed; retrying within the bounded budget.','failed')
                if model_failures>=2:
                    self.state['stop_reason']='model_unavailable'
                    break
                continue
            if action.plan:
                self.state['plan']=action.plan
            if action.tool=='finish':
                missing=self.completion_requirements()
                if missing:
                    self.state['errors'].append('Finish deferred: ' + ' '.join(missing))
                    event(self.state,'evaluate','Finish deferred until the remaining analytical requirements are met.','completed')
                    continue
                self.state['stop_reason']='sufficient_evidence'
                break
            # Match exact tool inputs, never explanations or reformatted SQL:
            # whitespace inside a SQL literal can change the requested analysis.
            action_key=json.dumps([action.tool,action.args.model_dump(exclude_none=True)],sort_keys=True) if action.tool in {'execute_sql','calculate_statistics'} else None
            previous=completed_actions.get(action_key)
            if previous:
                message=f"Repeated analytical action skipped; reuse {previous['id']} and choose a different calculation or finish if completion requirements are met."
                item=event(self.state,action.tool,message,'skipped')
                item.update(input=action.args.model_dump(exclude_none=True),evidence_id=previous['id'],reused_evidence=True)
                self.state['errors'].append(message)
                repeated_actions+=1
                if repeated_actions>=2:
                    self.state['stop_reason']='repeated_action_limit'
                    self.state['errors'].append('Exploration stopped after two repeated analytical requests. Available evidence is retained; narrow the question and start a new investigation to continue.')
                    break
                continue
            result=await self.execute(action)
            if 'error' in result:
                tool_failures+=1
                if tool_failures>=3:
                    self.state['stop_reason']='tool_failure_limit'
                    break
            elif action_key is not None:
                completed_actions[action_key]=result
        if not self.analytical_evidence():
            raise RuntimeError('No analytical tools completed successfully. Check model access and retry, or use offline analytics.')
        await self.ensure_artifacts()
        report_event=event(self.state,'report','Compile findings with evidence references and explicit limitations.')
        try:
            draft=(await self.generate(AgentReport,{**self.context(0),'instruction':'Return the final report. Use numerical-free prose and structured measurements with exact cell values. Reference only actual analytical evidence IDs.'})).model_dump()
        except Exception:
            self.state['errors'].append('Model report unavailable; a computed evidence summary was generated instead.')
            draft=self.fallback_report()
        finalize_report(self.state,draft)
        if not any(f.get('measurements') for f in self.state['findings']) and self.numeric_sql_cell():
            self.state['errors'].append('Model report supplied no valid numeric measurements; showing a computed evidence summary.')
            finalize_report(self.state,self.fallback_report())
        report_event['status']='completed'

    def fallback_report(self):
        findings=[]
        for e in self.state['evidence']:
            if e['tool']=='execute_sql' and e['result'].get('rows'):
                measurements=[{'evidence_id':e['id'],'row':i,'field':k,'value':v}
                    for i,row in enumerate(e['result']['rows'][:3]) for k,v in row.items()
                    if isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v)]
                findings.append({'claim':'Computed query results; inspect the segment labels and source query.',
                    'kind':'observation','evidence_ids':[e['id']],'measurements':measurements[:12]})
            elif e['tool']=='calculate_statistics':
                if e['result'].get('source_type','dataset')!='dataset':continue
                result={k:v for k,v in e['result'].items() if k!='rows'}
                measures=[{'evidence_id':e['id'],'row':None,'field':k,'value':v} for k,v in result.items()
                    if isinstance(v,(float,int)) and not isinstance(v,bool) and math.isfinite(v)]
                findings.append({'claim':'Computed statistical analysis; inspect the tool evidence for method and assumptions.',
                    'kind':'observation','evidence_ids':[e['id']],'measurements':measures})
                if e['result'].get('operation')=='mode':
                    modal_measures=[{'evidence_id':e['id'],'row':i,'field':field,'value':value}
                        for i,row in enumerate(e['result']['rows'][:6]) for field,value in row.items()
                        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)]
                    findings.append({'claim':'Values tied for the highest observed frequency; inspect mode evidence for all retained ties.',
                        'kind':'observation','evidence_ids':[e['id']],'measurements':modal_measures[:12]})
                else:
                    row_measures=[{'evidence_id':e['id'],'row':i,'field':field,'value':value}
                        for i,row in enumerate(e['result'].get('rows',[])[:6]) for field,value in row.items()
                        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)]
                    if row_measures:
                        findings.append({'claim':'Computed statistical table; row labels identify coefficients, bins or other statistical outputs.',
                            'kind':'observation','evidence_ids':[e['id']],'measurements':row_measures[:24]})
        return {'summary':'Computed analytical evidence is available below. Review the query results and verification ledger for exact values.',
                'findings':findings,'limitations':['No causal inference was performed.','Review period coverage and missing values before making business decisions.'],
                'next_steps':['Validate surprising segments against source records.','Investigate additional periods or candidate confounding factors.'],'generation':'computed'}

    async def offline(self):
        s=self.state; p=self.dataset.profile
        s['plan']=['Profile data quality','Compute a temporal or categorical summary','Compare contributing segments','Check outlier candidates','Recompute a numeric result','Build charts and report']
        if s['image_id']:
            event(s,'inspect_image','Offline mode cannot interpret images; chart context is omitted.','skipped')
        metrics=[m for m in p['metrics'] if not any(t in m.lower() for t in [' id','_id','transaction']) and self.dataset.df[m].notna().any()]
        if not metrics:
            raise RuntimeError('Offline analytics requires at least one numeric column.')
        metric=next((m for m in metrics if m.lower()=='revenue'),metrics[0])
        def q(c): return '"'+c.replace('"','""')+'"'
        async def sql(query, description):
            return await self.execute(AgentAction(tool='execute_sql',explanation=description,args=ToolArgs(sql=query)))
        dims=[d for d in p['dimensions'] if 1 < next(c['unique'] for c in p['columns'] if c['name']==d) <= 30]
        if p['dates']:
            date=q(p['dates'][0]); m=q(metric)
            entry=await sql(f"SELECT date_trunc('month', {date}) AS period, SUM({m}) AS total FROM dataset GROUP BY 1 ORDER BY 1",'Offline rule: aggregate the selected metric by calendar month.')
            if 'error' not in entry:
                await self.execute(AgentAction(tool='generate_chart',explanation='Plot the actual monthly totals.',args=ToolArgs(evidence_id=entry['id'],chart_type='line',x='period',y='total',title=metric+' over time')))
                change=await sql(f"WITH monthly AS (SELECT date_trunc('month',{date}) AS period,SUM({m}) AS total FROM dataset WHERE {date} IS NOT NULL GROUP BY 1), compared AS (SELECT period,total,LAG(total) OVER (ORDER BY period) AS previous,LAG(period) OVER (ORDER BY period) AS previous_period FROM monthly) SELECT period,previous_period,previous,total,total-previous AS delta,100.0*(total-previous)/NULLIF(ABS(previous),0) AS pct_change FROM compared WHERE previous IS NOT NULL ORDER BY delta LIMIT 1",'Offline rule: compare adjacent observed months; missing calendar months are not assumed to be zero.')
                if 'error' not in change and change['result']['rows']:
                    r=change['result']['rows'][0]
                    await self.execute(AgentAction(tool='verify_finding',explanation='Recompute the selected monthly change.',args=ToolArgs(evidence_id=change['id'],row=0,field='delta',expected=r['delta'],claim='Monthly total difference')))
                    if dims:
                        d=q(dims[0]); period=r['period'][:10]; previous_period=r['previous_period'][:10]
                        segment=await sql(f"SELECT {d} AS segment,SUM(CASE WHEN date_trunc('month',{date})=DATE '{period}' THEN {m} ELSE 0 END) AS current_total,SUM(CASE WHEN date_trunc('month',{date})=DATE '{previous_period}' THEN {m} ELSE 0 END) AS previous_total,current_total-previous_total AS delta FROM dataset GROUP BY 1 ORDER BY delta",'Offline rule: compare segment contributions across the same observed periods.')
                        if 'error' not in segment and segment['result']['rows']:
                            await self.execute(AgentAction(tool='generate_chart',explanation='Show the computed segment differences.',args=ToolArgs(evidence_id=segment['id'],chart_type='bar',x='segment',y='delta',title='Contribution to monthly change')))
                            if len(dims)>1:
                                worst_value=segment['result']['rows'][0]['segment']
                                worst=str(worst_value).replace("'","''")
                                condition=f'{d} IS NULL' if worst_value is None else f"CAST({d} AS VARCHAR)='{worst}'"
                                next_dimension=min(dims[1:], key=lambda name:next(c['unique'] for c in p['columns'] if c['name']==name))
                                await sql(f"SELECT {q(next_dimension)} AS category,SUM(CASE WHEN date_trunc('month',{date})=DATE '{period}' THEN {m} ELSE 0 END) AS current_total,SUM(CASE WHEN date_trunc('month',{date})=DATE '{previous_period}' THEN {m} ELSE 0 END) AS previous_total,current_total-previous_total AS delta FROM dataset WHERE {condition} GROUP BY 1 ORDER BY delta",'Offline rule: drill into the segment with the lowest computed change using the next compact dimension.')
        elif dims:
            entry=await sql(f'SELECT {q(dims[0])} AS segment,COUNT(*) AS records,AVG({q(metric)}) AS mean,SUM({q(metric)}) AS total FROM dataset GROUP BY 1 ORDER BY total DESC','Offline rule: compare the selected metric by category.')
            if 'error' not in entry:
                await self.execute(AgentAction(tool='generate_chart',explanation='Visualize actual category totals.',args=ToolArgs(evidence_id=entry['id'],chart_type='bar',x='segment',y='total',title=metric+' by '+dims[0])))
                if entry['result']['rows']:
                    await self.execute(AgentAction(tool='verify_finding',explanation='Recompute the leading category total.',args=ToolArgs(evidence_id=entry['id'],row=0,field='total',expected=entry['result']['rows'][0]['total'],claim='Leading category total')))
        if not p['dates'] and not dims:
            sampled=await sql(f'SELECT {q(metric)} FROM dataset WHERE {q(metric)} IS NOT NULL LIMIT 200','Offline rule: sample up to the first two hundred metric values for a distribution chart.')
            if 'error' not in sampled:
                await self.execute(AgentAction(tool='generate_chart',explanation='Plot the retained metric sample, not the whole distribution.',args=ToolArgs(evidence_id=sampled['id'],chart_type='histogram',x=metric,title='Metric distribution · first 200 values')))
        await self.execute(AgentAction(tool='calculate_statistics',explanation='Compute a numerical distribution summary.',args=ToolArgs(operation='summary',column=metric)))
        await self.execute(AgentAction(tool='calculate_statistics',explanation='Flag outlier candidates using the IQR rule.',args=ToolArgs(operation='outliers',column=metric)))
        draft=self.fallback_report()
        draft['summary']='Offline analytics computed the temporal or categorical comparisons and descriptive statistics shown below. Fixed rules chose the metric; the natural-language question did not control this workflow.'
        s['stop_reason']='offline_complete'
        finalize_report(s,draft)

    def mark_cancelled(self, user_requested=False):
        if self.state['status'] not in {'queued','running'}:
            return
        self.state['stop_reason']='user_cancelled' if user_requested else 'cancelled'
        message='Investigation stopped by the user.' if user_requested else 'Investigation was cancelled during server shutdown.'
        self.state['errors'].append(message)
        for item in self.state['events']:
            if item['status']=='running':
                item.update(status='skipped',error=message)
        self.state['status']='failed'
        if user_requested:
            self.state['status']='partial' if self.analytical_evidence() else 'cancelled'
            if self.analytical_evidence():
                try:
                    draft=self.fallback_report()
                    draft['limitations'].append('The user stopped the investigation; requested analyses may be incomplete.')
                    finalize_report(self.state,draft)
                except Exception:
                    self.state['errors'].append('A partial report could not be generated. Completed evidence remains available.')
        event(self.state,'investigation',message,'skipped' if user_requested else 'failed')

    async def run(self):
        try:
            await self._run()
        except asyncio.CancelledError:
            self.mark_cancelled()
            raise

    async def _run(self):
        async with gate:
            self.state['status']='running'
            try:
                entry=evidence(self.state,'profile_dataset',self.dataset.profile)
                event(self.state,'profile_dataset','Dataset schema, missing values, and candidate dimensions inspected.','completed')['evidence_id']=entry['id']
                if self.state['mode']=='offline': await self.offline()
                else: await self.run_agent()
                self.state['status']='completed' if self.state.get('stop_reason') in {'sufficient_evidence','offline_complete'} else 'partial'
                event(self.state,'report','Investigation report ready.','completed')
            except Exception as exc:
                message=str(exc) if isinstance(exc,RuntimeError) else 'Investigation failed. Review configuration and retry.'
                self.state['errors'].append(message); self.state['status']='failed'
                event(self.state,'investigation',message,'failed')
            finally:
                if self.client and hasattr(self.client,'aio'):
                    try: await self.client.aio.aclose()
                    except Exception: pass  # Cleanup must not replace a valid investigation outcome.
                elif self.client and hasattr(self.client,'aclose'):
                    try: await self.client.aclose()
                    except Exception: pass

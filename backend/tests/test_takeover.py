"""Regression tests for the takeover audit, including the full multimodal adaptive path."""
import asyncio
import io
import json
import time
from pathlib import Path
import httpx
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from google import genai
from google.genai import types
from PIL import Image
from backend.main import app
from backend.agent.investigator import InvestigationAgent
from backend.agent.schemas import AgentAction, ToolArgs, InvestigationRequest
from backend.services import sessions
from backend.services.reporting import finalize_report, resolve_measurement
from backend.tools.profiler import profile_dataset


@pytest.fixture(autouse=True)
def clear():
    sessions.datasets.clear(); sessions.images.clear(); sessions.investigations.clear()


def test_numerical_prose_and_false_measurements_rejected():
    state={'mode':'agent','evidence':[{'id':'E01','tool':'execute_sql','result':{'rows':[{'Region':'West','total':10}]}}]}
    finalize_report(state,{'summary':'Revenue fell by 99999 percent.','findings':[
        {'claim':'Revenue is 99999','evidence_ids':['E01'],'kind':'observation','measurements':[
            {'evidence_id':'E01','row':0,'field':'total','value':99999}]},
        {'claim':'Measured regional revenue','evidence_ids':['E01'],'kind':'observation','measurements':[
            {'evidence_id':'E01','row':0,'field':'total','value':10}]}], 'limitations':[],'next_steps':[]})
    assert '99999' not in json.dumps(state['report'])
    assert state['findings'][0]['kind']=='inconclusive'
    assert state['findings'][1]['measurements'][0]['context']=={'Region':'West'}
    assert state['findings'][1]['measurements'][0]['verification']=='computed'


def test_active_retention_and_inactive_expiry():
    old=time.time()-8000
    sessions.datasets['d']=sessions.Dataset('d','x',None,{},created=old)
    sessions.images['i']={'bytes':b'x','created':old}
    state=sessions.create_investigation(InvestigationRequest(dataset_id='d',image_id='i',question='Find trends'))
    state['created']=old;state['accessed']=old
    sessions.cleanup()
    assert 'd' in sessions.datasets and 'i' in sessions.images and state['id'] in sessions.investigations
    state['status']='completed';sessions.cleanup()
    assert not sessions.datasets and not sessions.images and not sessions.investigations


def test_bounded_context_and_cancelled_state():
    frame=pd.DataFrame({'Notes':['x'*1000000],'Revenue':[1.]})
    d=sessions.Dataset('d','x.csv',frame,profile_dataset(frame));sessions.datasets['d']=d
    state=sessions.create_investigation(InvestigationRequest(dataset_id='d',question='Find trends'))
    state['evidence']=[{'id':'E01','tool':'profile_dataset','result':d.profile}]
    agent=InvestigationAgent(state,client=object())
    assert len(json.dumps(agent.context(8)))<100000
    async def cancel():
        async def interrupted(): raise asyncio.CancelledError()
        agent._run=interrupted
        with pytest.raises(asyncio.CancelledError): await agent.run()
    asyncio.run(cancel())
    assert state['status']=='failed' and state['stop_reason']=='cancelled'


def test_premature_finish_is_not_completed(monkeypatch):
    monkeypatch.setenv('MAX_AGENT_STEPS','2')
    frame=pd.DataFrame({'Revenue':[1,2]})
    d=sessions.Dataset('d','x.csv',frame,profile_dataset(frame));sessions.datasets['d']=d
    state=sessions.create_investigation(InvestigationRequest(dataset_id='d',question='Find trends'))
    agent=InvestigationAgent(state,client=object())
    async def model(schema, context):
        if schema.__name__=='AgentReport': return schema(summary='Computed evidence.',findings=[],limitations=[],next_steps=[])
        if not agent.analytical_evidence(): return AgentAction(tool='execute_sql',explanation='Compute revenue.',args=ToolArgs(sql='SELECT SUM(Revenue) AS total FROM dataset'))
        return AgentAction(tool='finish',explanation='Stop prematurely.')
    agent.generate=model
    asyncio.run(agent.run())
    assert state['status']=='partial' and state['stop_reason']=='step_budget_exhausted'
    assert any('Finish deferred' in e for e in state['errors'])
    assert state['charts'] and state['report']['verified_cells']==1
    assert any('System finalization' in e['description'] for e in state['events'])


@pytest.mark.parametrize('lowest',['West','East'])
def test_multimodal_adaptive_sdk_api_e2e(monkeypatch,lowest):
    real_client=genai.Client
    planner_requests=[];followups=[]
    def response(request):
        body=json.loads(request.content)
        has_image=any('inlineData' in p for c in body['contents'] for p in c['parts'])
        if has_image:
            payload={'chart_type':'bar','axes':['Region','Revenue'],'metrics':['Revenue'],'categories':['West','East'],
                'time_periods':[],'highlighted_regions':[lowest],'visible_patterns':['One region has lower revenue.'],
                'matching_columns':['Revenue','Region'],'ambiguities':[]}
        else:
            context=json.loads(body['contents'][0]['parts'][0]['text']);planner_requests.append(context)
            queries=[e for e in context['observations'] if e['tool']=='execute_sql']
            if context.get('instruction'):
                src=queries[-1];value=src['result']['rows'][0]['total']
                payload={'summary':'The lower region warrants follow-up; the data establishes a difference, not its cause.',
                    'findings':[{'claim':'Regional contribution was computed from the uploaded workbook.','kind':'observation',
                        'evidence_ids':[src['id']],'measurements':[{'evidence_id':src['id'],'row':0,'field':'total','value':value}]}],
                    'limitations':['The chart is visual context only.'],'next_steps':['Inspect source records.']}
            else:
                def action(tool,explanation,**args): return AgentAction(tool=tool,explanation=explanation,args=ToolArgs(**args)).model_dump()
                if not queries:
                    payload=action('execute_sql','Compare regions in the highlighted metric.',sql='SELECT Region,SUM(Revenue) AS total FROM dataset GROUP BY 1 ORDER BY total')
                elif len(queries)==1:
                    observed=queries[0]['result']['rows'][0]['Region']
                    followups.append(observed)
                    payload=action('execute_sql','Follow up on the observed lower region.',sql=f"SELECT Region,SUM(Revenue) AS total FROM dataset WHERE Region='{observed}' GROUP BY 1 ORDER BY 1")
                elif not any(e['tool']=='generate_chart' for e in context['observations']):
                    payload=action('generate_chart','Plot actual region totals.',evidence_id=queries[0]['id'],chart_type='bar',x='Region',y='total')
                elif not any(e['tool']=='verify_finding' for e in context['observations']):
                    payload=action('verify_finding','Recompute the follow-up result.',evidence_id=queries[-1]['id'],row=0,field='total',expected=queries[-1]['result']['rows'][0]['total'],claim='Regional total')
                else: payload=action('finish','The numerical comparison is supported.')
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':json.dumps(payload)}]},'finishReason':'STOP'}]})
    def client_factory(**kwargs):
        return real_client(api_key='mock-key',http_options=types.HttpOptions(async_client_args={'transport':httpx.MockTransport(response)}))
    monkeypatch.setattr('backend.agent.investigator.genai.Client',client_factory)
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    frame=pd.DataFrame({'Region':['West','East'],'Revenue':[10,30] if lowest=='West' else [30,10]})
    workbook=io.BytesIO();frame.to_excel(workbook,index=False)
    image=io.BytesIO();Image.new('RGB',(50,50),'white').save(image,format='PNG')
    with TestClient(app) as c:
        dataset=c.post('/api/datasets',files={'file':('regions.xlsx',workbook.getvalue())}).json()
        chart=c.post('/api/images',files={'file':('regions.png',image.getvalue())}).json()
        result=c.post('/api/investigations',json={'dataset_id':dataset['id'],'image_id':chart['id'],'mode':'agent','question':'Compare the highlighted revenue by region and investigate the lowest.'})
        assert result.status_code==202,result.text
        id=result.json()['id']
        for _ in range(200):
            state=c.get('/api/investigations/'+id).json()
            if state['status'] not in {'queued','running'}: break
            time.sleep(.02)
        assert state['status']=='completed',state['errors']
        assert followups==[lowest]
        assert state['report']['verified_cells']==1 and len(state['charts'])==1
        assert state['findings'][0]['measurements'][0]['value']==10
        assert state['findings'][0]['measurements'][0]['verification']=='verified'
        assert planner_requests[0]['image_context']['highlighted_regions']==[lowest]
        assert 'highlighted revenue' in planner_requests[0]['question']
        assert c.get('/api/investigations/'+id+'/report').status_code==200


def test_streamed_request_limit_before_parser():
    from backend.services.request_limits import RequestLimitsMiddleware
    invoked=[];sent=[]
    async def downstream(*args): invoked.append(True)
    async def receive(): return {'type':'http.request','body':b'x'*20000,'more_body':False}
    async def send(message): sent.append(message)
    scope={'type':'http','method':'POST','path':'/api/investigations','headers':[]}
    asyncio.run(RequestLimitsMiddleware(downstream)(scope,receive,send))
    assert not invoked and sent[0]['status']==413


def test_missing_month_segment_totals_reconcile():
    frame=pd.DataFrame({'Date':pd.to_datetime(['2026-01-01','2026-01-02','2026-03-01','2026-03-02']),
                        'Region':['West','East','West','East'],'Revenue':[100.,100.,20.,90.]})
    d=sessions.Dataset('d','gapped.csv',frame,profile_dataset(frame));sessions.datasets['d']=d
    state=sessions.create_investigation(InvestigationRequest(dataset_id='d',question='Compare observed periods',mode='offline'))
    asyncio.run(InvestigationAgent(state).run())
    changes=[e for e in state['evidence'] if e['tool']=='execute_sql' and e['result']['rows'] and 'pct_change' in e['result']['rows'][0]]
    segments=[e for e in state['evidence'] if e['tool']=='execute_sql' and e['result']['rows'] and 'segment' in e['result']['rows'][0]]
    assert state['status']=='completed' and not state['errors']
    assert changes[0]['result']['rows'][0]['delta']==-90
    assert sum(row['delta'] for row in segments[0]['result']['rows'])==-90


def test_pure_numeric_offline_has_real_chart():
    frame=pd.DataFrame({'Value':[10.,20.,30.]})
    sessions.datasets['d']=sessions.Dataset('d','numeric.csv',frame,profile_dataset(frame))
    state=sessions.create_investigation(InvestigationRequest(dataset_id='d',question='Describe the measurements',mode='offline'))
    asyncio.run(InvestigationAgent(state).run())
    assert state['status']=='completed' and not state['errors']
    assert state['charts'][0]['data'][0]['x']==[10.,20.,30.]


def test_sql_timeout_interrupts_expensive_computation():
    from backend.tools.sql_engine import execute_sql
    frame=pd.DataFrame({'value':range(10000)})
    started=time.monotonic()
    with pytest.raises(ValueError,match='[Ii]nterrupt'):
        execute_sql(frame,'SELECT SUM(a.value*b.value+c.value) AS total FROM dataset a CROSS JOIN dataset b CROSS JOIN dataset c')
    assert time.monotonic()-started<8


def test_small_numeric_claim_cannot_be_replaced_with_zero():
    from backend.tools.verifier import verify_finding
    result={'sql':'SELECT value FROM dataset','rows':[{'value':1e-7}]}
    evidence=[{'id':'E01','tool':'execute_sql','result':result}]
    verification=verify_finding(None,evidence,ToolArgs(evidence_id='E01',row=0,field='value',expected=0,claim='Value is zero'),lambda *_:result)
    assert verification['status']=='inconclusive'
    with pytest.raises(ValueError):
        resolve_measurement({'evidence':evidence},{'evidence_id':'E01','row':0,'field':'value','value':0})


def test_sql_requires_dataset_provenance_and_cannot_shadow_it():
    from backend.tools.sql_engine import validate_sql
    for query in ['SELECT 999 AS Revenue','WITH dataset AS (SELECT 999 AS Revenue) SELECT * FROM dataset']:
        with pytest.raises(ValueError): validate_sql(query)


def test_lifespan_cancels_running_job_without_leaving_it_stuck(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    async def pending(self): await asyncio.Event().wait()
    monkeypatch.setattr(InvestigationAgent,'run_agent',pending)
    frame=pd.DataFrame({'Revenue':[10.]})
    sessions.datasets['d']=sessions.Dataset('d','test.csv',frame,profile_dataset(frame))
    with TestClient(app) as client:
        response=client.post('/api/investigations',json={'dataset_id':'d','question':'Find data trends','mode':'agent'})
        id=response.json()['id']
        for _ in range(50):
            if sessions.investigations[id]['status']=='running': break
            time.sleep(.01)
    assert sessions.investigations[id]['status']=='failed'
    assert sessions.investigations[id]['stop_reason']=='cancelled'

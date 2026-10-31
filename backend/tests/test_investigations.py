import asyncio
import io
import json
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.main import app
from backend.agent.investigator import InvestigationAgent
from backend.agent.schemas import AgentAction, ToolArgs, AgentReport, InvestigationRequest
from backend.services import sessions
from backend.services.reporting import finalize_report
from backend.services.pdf_report import pdf_report
from pypdf import PdfReader
from backend.tools.profiler import profile_dataset

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_sessions():
    sessions.datasets.clear(); sessions.images.clear(); sessions.investigations.clear()
    yield


def dataset():
    frame=pd.DataFrame({'Region':['West','East'],'Revenue':[10.,30.]})
    d=sessions.Dataset('test','test.csv',frame,profile_dataset(frame));sessions.datasets[d.id]=d
    return d


def test_adaptive_loop_and_errors():
    d=dataset();state=sessions.create_investigation(InvestigationRequest(dataset_id=d.id,question='Compare regions and verify results'))
    agent=InvestigationAgent(state,client=object());calls=[]
    async def model(schema, context):
        calls.append(context)
        if schema==AgentReport:
            return AgentReport(summary='West has lower revenue.',findings=[{'claim':'West total is 10.','evidence_ids':['E02'],'kind':'observation'}],limitations=[],next_steps=[])
        step=len(calls)
        if step==1: return AgentAction(tool='execute_sql',explanation='Compare revenue by region.',args=ToolArgs(sql='SELECT Region,SUM(Revenue) AS total FROM dataset GROUP BY 1 ORDER BY total'))
        if step==2:
            observed=context['observations'][-1]['result']['rows'][0]
            assert observed['Region']=='West'
            # Follow-up depends on the actual first tool result.
            return AgentAction(tool='execute_sql',explanation='Investigate the observed lowest region.',args=ToolArgs(sql=f"SELECT SUM(Revenue) AS total FROM dataset WHERE Region='{observed['Region']}'"))
        if step==3: return AgentAction(tool='verify_finding',explanation='Recompute West total.',args=ToolArgs(evidence_id='E03',row=0,field='total',expected=10,claim='West total'))
        if step==4: return AgentAction(tool='generate_chart',explanation='Chart computed regions.',args=ToolArgs(evidence_id='E02',chart_type='bar',x='Region',y='total'))
        return AgentAction(tool='finish',explanation='Sufficient descriptive evidence.')
    agent.generate=model
    asyncio.run(agent.run())
    assert state['status']=='completed',(state['errors'],state['events'])
    assert len([e for e in state['evidence'] if e['tool']=='execute_sql'])==2
    assert state['report']['verified_cells']==1 and len(state['charts'])==1
    assert 'West total' in '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf_report(state))).pages)
    assert all(r in {e['id'] for e in state['evidence']} for f in state['findings'] for r in f['evidence_ids'])


def test_tool_failure_and_model_failure():
    d=dataset();state=sessions.create_investigation(InvestigationRequest(dataset_id=d.id,question='Find patterns'))
    agent=InvestigationAgent(state,client=object())
    result=asyncio.run(agent.execute(AgentAction(tool='execute_sql',explanation='Invalid query',args=ToolArgs(sql='DROP TABLE dataset'))))
    assert 'error' in result and state['events'][0]['status']=='failed' and not state['evidence']
    assert agent.context(8)['failed_actions'][0]['args']['sql']=='DROP TABLE dataset'
    async def broken(*args): raise ValueError('bad model output')
    agent.generate=broken;asyncio.run(agent.run())
    assert state['status']=='failed' and state['report'] is None


def test_unknown_evidence_is_not_verified():
    state={'evidence':[],'mode':'agent'}
    finalize_report(state,{'summary':'draft','findings':[{'claim':'Unsupported','evidence_ids':['FAKE'],'kind':'observation'}],'limitations':[],'next_steps':[]})
    assert state['findings'][0]['kind']=='inconclusive' and state['report']['verified_cells']==0


def test_api_offline_e2e():
    with TestClient(app) as client:
        assert client.get('/api/health').status_code==200
        response=client.post('/api/datasets',files={'file':('retail.csv',(ROOT/'demo/retail_sales.csv').read_bytes(),'text/csv')})
        assert response.status_code==200, response.text
        d=response.json(); assert d['profile']['rows']>5000
        image=io.BytesIO();Image.new('RGB',(30,30),'white').save(image,format='PNG')
        img=client.post('/api/images',files={'file':('chart.png',image.getvalue(),'image/png')})
        assert img.status_code==200
        response=client.post('/api/investigations',json={'dataset_id':d['id'],'question':'Why did revenue decline?','mode':'offline','image_id':img.json()['id']})
        assert response.status_code==202,response.text
        id=response.json()['id']
        import time
        for _ in range(150):
            result=client.get('/api/investigations/'+id).json()
            if result['status'] in {'completed','failed'}: break
            time.sleep(.05)
        assert result['status']=='completed',result
        assert not result['errors'],result['errors']
        assert len(result['charts'])==2 and result['report']['verified_cells']==1
        assert any(e['status']=='skipped' for e in result['events'])
        report=client.get('/api/investigations/'+id+'/report')
        assert report.status_code==200 and report.headers['content-type']=='application/pdf'
        text='\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(report.content)).pages)
        assert 'Offline analytics' in text and 'Evidence appendix' in text


def test_api_errors(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    with TestClient(app) as c:
        assert c.get('/api/investigations/missing').status_code==404
        assert c.post('/api/datasets',files={'file':('x.csv',b'','text/csv')}).status_code==422
        assert c.post('/api/images',files={'file':('x.png',b'not an image','image/png')}).status_code==422
        assert c.post('/api/datasets',files={'file':('x.csv',b'x'*(15*1024*1024+1),'text/csv')}).status_code==413
        d=dataset()
        assert c.post('/api/investigations',json={'dataset_id':d.id,'question':'Analyze data','mode':'agent'}).status_code==503


@pytest.mark.parametrize('name',['sensor_data','student_performance'])
def test_cross_domain_offline(name):
    from backend.tools.data_loader import load_dataset
    df=load_dataset((ROOT/'demo'/f'{name}.csv').read_bytes(),f'{name}.csv')
    d=sessions.Dataset(name,name,df,profile_dataset(df));sessions.datasets[name]=d
    state=sessions.create_investigation(InvestigationRequest(dataset_id=name,question='Find unusual patterns',mode='offline'))
    asyncio.run(InvestigationAgent(state).run())
    assert state['status']=='completed' and not state['errors'],state['errors']
    assert any(e['tool']=='calculate_statistics' for e in state['evidence'])

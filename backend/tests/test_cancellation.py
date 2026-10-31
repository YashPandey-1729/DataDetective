"""Cancellation stops actual jobs, retains evidence and handles queue/completion races."""
import asyncio
import threading
import time
import pandas as pd
import pytest
from fastapi.testclient import TestClient
import backend.main as main
from backend.agent.investigator import InvestigationAgent, event
from backend.agent.schemas import AgentAction, InvestigationRequest
from backend.services import sessions
from backend.tools.profiler import profile_dataset


@pytest.fixture(autouse=True)
def dataset(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    sessions.datasets.clear(); sessions.images.clear(); sessions.investigations.clear()
    frame=pd.DataFrame({'Revenue':[10.,20.,30.]})
    sessions.datasets['cancel-test']=sessions.Dataset('cancel-test','test.csv',frame,profile_dataset(frame))
    yield
    sessions.datasets.clear(); sessions.images.clear(); sessions.investigations.clear()


def start(client):
    response=client.post('/api/investigations',json={
        'dataset_id':'cancel-test','question':'Summarize revenue','mode':'agent'})
    assert response.status_code==202,response.text
    return response.json()['id']


def wait_for(client,id,predicate):
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        state=client.get('/api/investigations/'+id).json()
        if predicate(state): return state
        time.sleep(.01)
    pytest.fail('Investigation did not reach the expected state.')


def test_stop_running_job_preserves_real_evidence_and_exports_computed_report(monkeypatch):
    stopped=threading.Event(); continued=[]
    async def pending(self):
        await self.execute(AgentAction(tool='calculate_statistics',explanation='Summarize revenue.',
                                      args={'operation':'summary','column':'Revenue'}))
        event(self.state,'model','Waiting for the next analytical action.')
        try:
            await asyncio.Event().wait()
            continued.append('Another model step must not run.')
        finally:
            stopped.set()
    monkeypatch.setattr(InvestigationAgent,'run_agent',pending)
    with TestClient(main.app) as client:
        id=start(client)
        wait_for(client,id,lambda state:any(e['tool']=='calculate_statistics' for e in state['evidence']))
        response=client.post(f'/api/investigations/{id}/cancel')
        assert response.status_code==200,response.text
        state=response.json()
        assert state['status']=='partial' and state['stop_reason']=='user_cancelled'
        assert state['report']['generation']=='computed'
        assert any(m['field']=='sum' and m['value']==60 for f in state['findings'] for m in f['measurements'])
        assert all(e['status']!='running' for e in state['events'])
        assert stopped.wait(2) and not continued
        assert client.post(f'/api/investigations/{id}/cancel').json()==state
        exported=client.get(f'/api/investigations/{id}/report')
        assert exported.status_code==200 and 'user stopped' in exported.text
    assert not main.tasks and not main.investigation_jobs


def test_stop_before_any_analysis_does_not_invent_a_report(monkeypatch):
    async def pending(self): await asyncio.Event().wait()
    monkeypatch.setattr(InvestigationAgent,'run_agent',pending)
    with TestClient(main.app) as client:
        id=start(client)
        wait_for(client,id,lambda state:state['status']=='running')
        state=client.post(f'/api/investigations/{id}/cancel').json()
        assert state['status']=='cancelled' and state['stop_reason']=='user_cancelled'
        assert state['report'] is None and not state['findings']
        assert client.get(f'/api/investigations/{id}/report').status_code==409


def test_cancel_queued_job_before_coroutine_starts_releases_its_slot():
    async def scenario():
        state=await main.investigate(InvestigationRequest(
            dataset_id='cancel-test',question='Summarize revenue',mode='offline'))
        task,_=main.investigation_jobs[state['id']]
        assert state['status']=='queued'
        await main.cancel_investigation(state['id'])
        await asyncio.gather(task,return_exceptions=True)
        assert task.cancelled()
        assert state['status']=='cancelled' and not state['evidence']
        assert state['stop_reason']=='user_cancelled'
        assert task not in main.tasks and state['id'] not in main.investigation_jobs
    asyncio.run(scenario())


@pytest.mark.parametrize('status',['completed','partial','failed','cancelled'])
def test_cancelling_a_finished_investigation_preserves_its_outcome(status):
    state=sessions.create_investigation(InvestigationRequest(dataset_id='cancel-test',question='Summarize revenue'))
    state.update(status=status,stop_reason='sufficient_evidence' if status=='completed' else 'user_cancelled')
    with TestClient(main.app) as client:
        before=client.get('/api/investigations/'+state['id']).json()
        assert client.post('/api/investigations/'+state['id']+'/cancel').json()==before


def test_unknown_and_unowned_jobs_return_controlled_errors():
    state=sessions.create_investigation(InvestigationRequest(dataset_id='cancel-test',question='Summarize revenue'))
    with TestClient(main.app) as client:
        assert client.post('/api/investigations/missing/cancel').status_code==404
        response=client.post('/api/investigations/'+state['id']+'/cancel')
        assert response.status_code==409 and state['status']=='queued'

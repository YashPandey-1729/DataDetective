import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.agent.investigator import InvestigationAgent
from backend.agent.schemas import InvestigationRequest
from backend.services import sessions
from backend.services.models import available_models, default_model


@pytest.fixture(autouse=True)
def clear_sessions():
    sessions.datasets.clear(); sessions.images.clear(); sessions.investigations.clear()


def test_health_exposes_gemini_gemma_and_the_configured_default(monkeypatch):
    monkeypatch.setenv('GEMINI_MODEL','custom-configured-model')
    with TestClient(app) as client:
        response=client.get('/api/health')
        assert response.status_code==200
        health=response.json()
    assert health['model']=='custom-configured-model'
    assert {item['id'] for item in health['models']}=={
        'gemini-3.5-flash-lite','ollama:gemma4:e4b','custom-configured-model'}
    monkeypatch.setenv('GEMINI_MODEL','gemma-4-26b-a4b-it')
    assert len(available_models())==2


def test_investigation_keeps_its_selected_or_default_model_when_config_changes(monkeypatch):
    frame=pd.DataFrame({'Revenue':[10,20]})
    sessions.datasets['data']=sessions.Dataset('data','data.csv',frame,{})
    monkeypatch.setenv('GEMINI_MODEL','gemini-3.5-flash-lite')
    default=sessions.create_investigation(InvestigationRequest(dataset_id='data',question='Analyze revenue'))
    chosen=sessions.create_investigation(InvestigationRequest(dataset_id='data',question='Analyze revenue',model='ollama:gemma4:e4b'))
    monkeypatch.setenv('GEMINI_MODEL','another-default')
    assert InvestigationAgent(default).model=='gemini-3.5-flash-lite'
    assert InvestigationAgent(chosen).model=='ollama:gemma4:e4b'


def test_unknown_model_is_rejected_before_creating_a_job(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    with TestClient(app) as client:
        data=client.post('/api/datasets',files={'file':('data.csv',b'Revenue\n10\n20')}).json()
        response=client.post('/api/investigations',json={
            'dataset_id':data['id'],'question':'Analyze revenue','mode':'agent','model':'arbitrary-unknown-model'})
    assert response.status_code==422
    assert 'Unknown AI model' in response.json()['detail']
    assert not sessions.investigations


def test_offline_mode_does_not_select_an_ai_model():
    state=sessions.create_investigation(InvestigationRequest(
        dataset_id='offline-data',question='Analyze revenue',mode='offline',model='ollama:gemma4:e4b'))
    assert state['model'] is None


def test_blank_config_keeps_a_usable_default(monkeypatch):
    monkeypatch.setenv('GEMINI_MODEL','  ')
    assert default_model()=='gemini-3.5-flash-lite'


@pytest.mark.parametrize('model',['gemma-4-26b-a4b-it','models/gemma-4-26b-a4b-it','Gemma-4-31b-it'])
def test_hosted_gemma_cannot_be_restored_by_the_cloud_default(monkeypatch,model):
    monkeypatch.setenv('GEMINI_MODEL',model)
    assert default_model()=='gemini-3.5-flash-lite'
    assert model not in {option['id'] for option in available_models()}

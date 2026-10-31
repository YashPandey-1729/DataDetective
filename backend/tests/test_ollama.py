import asyncio
import base64
import json
import httpx
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app
from backend.agent.schemas import AgentAction
from backend.agent.schemas import InvestigationRequest
from backend.agent.investigator import InvestigationAgent
from backend.agent.prompts import LOCAL_SYSTEM
from backend.tools.profiler import profile_dataset
from backend.agent.tool_contracts import local_action_json_schema, validate_tool_arguments
from backend.services import ollama, sessions


@pytest.fixture(autouse=True)
def local_config(monkeypatch):
    monkeypatch.setenv('OLLAMA_MODEL','gemma4:e4b')
    monkeypatch.setenv('OLLAMA_BASE_URL','http://127.0.0.1:11434')
    monkeypatch.setenv('OLLAMA_CONTEXT_LENGTH','8192')
    monkeypatch.setenv('OLLAMA_TIMEOUT_SECONDS','180')
    sessions.datasets.clear();sessions.images.clear();sessions.investigations.clear()


def invoke(handler, images=None, contents='Find a pattern'):
    async def run():
        async with httpx.AsyncClient(base_url=ollama.settings()['url'],transport=httpx.MockTransport(handler)) as client:
            return await ollama.generate_structured(client,model='ollama:gemma4:e4b',schema=AgentAction,
                contents=contents,system_instruction='Choose an analytical tool.',images=images)
    return asyncio.run(run())


def test_schema_image_and_local_model_are_sent_without_credentials():
    def reply(request):
        body=json.loads(request.content)
        assert request.url.host=='127.0.0.1'
        assert 'authorization' not in request.headers and 'x-goog-api-key' not in request.headers
        assert body['model']=='gemma4:e4b' and body['think'] is False and body['stream'] is False
        assert body['format']==local_action_json_schema()
        assert base64.b64decode(body['messages'][-1]['images'][0])==b'chart bytes'
        assert body['options']=={'temperature':0,'num_ctx':8192,'num_predict':2048}
        return httpx.Response(200,json={'done':True,'model':'gemma4:e4b','message':{
            'content':json.dumps({'tool':'execute_sql','explanation':'Compute the total.','args':{'sql':'SELECT SUM(Revenue) AS total FROM dataset'}})}})
    assert invoke(reply,images=[b'chart bytes']).tool=='execute_sql'


@pytest.mark.parametrize('url',['https://ollama.com','http://192.168.1.2:11434','http://127.0.0.1:11434/proxy',
    'http://user:password@localhost:11434','http://localhost:11434?remote=1'])
def test_remote_urls_and_proxy_paths_are_rejected(monkeypatch,url):
    monkeypatch.setenv('OLLAMA_BASE_URL',url)
    with pytest.raises(ValueError,match='loopback'): ollama.create_client()
    assert ollama.status()['ready'] is False


@pytest.mark.parametrize('model',['gemma4:e4b-cloud','gemma4:cloud','llama3:latest'])
def test_cloud_and_other_model_tags_are_rejected(monkeypatch,model):
    monkeypatch.setenv('OLLAMA_MODEL',model)
    with pytest.raises(ValueError,match='local gemma4'): ollama.settings()


@pytest.mark.parametrize('status,message',[(404,'not installed'),(500,'memory status'),(302,'memory status')])
def test_http_errors_are_actionable_without_following_redirects(status,message):
    with pytest.raises(ValueError,match=message):
        invoke(lambda request: httpx.Response(status,json={'error':'sensitive details'},headers={'Location':'https://ollama.com'}))


@pytest.mark.parametrize('result',[
    {'done':False}, {'done':True,'done_reason':'length'}, {'done':True,'model':'gemma4:cloud'},
    {'done':True,'message':None}, {'done':True,'message':{'content':'not JSON'}},
    {'done':True,'message':{'content':'{"tool":"invented","explanation":"Invalid tool"}'}},
])
def test_invalid_incomplete_or_unvalidated_responses_are_rejected(result):
    with pytest.raises(ValueError): invoke(lambda request:httpx.Response(200,json=result))


def test_timeout_and_oversized_context_do_not_fall_back_to_google():
    def timeout(request): raise httpx.ReadTimeout('private transport details',request=request)
    with pytest.raises(ValueError,match='timed out'): invoke(timeout)
    with pytest.raises(ValueError,match='context budget'):
        invoke(lambda request:pytest.fail('Oversized prompts must not be sent'),contents='x'*20000)


def test_local_health_does_not_need_a_google_key(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    monkeypatch.setattr('backend.main.ollama_status',lambda:{'ready':True,'running':True,'message':None})
    with TestClient(app) as client:
        health=client.get('/api/health').json()
    assert health['ai_configured'] is True and health['google_configured'] is False
    assert next(m for m in health['models'] if m['provider']=='ollama')['available'] is True
    assert all(not m['id'].startswith('gemma-') for m in health['models'])


def test_missing_local_model_rejected_without_creating_a_job(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','mock-key')
    monkeypatch.setattr('backend.main.ollama_status',lambda:{'ready':False,'running':True,'message':'Download the local model with: ollama pull gemma4:e4b'})
    with TestClient(app) as client:
        data=client.post('/api/datasets',files={'file':('data.csv',b'Revenue\n10\n20')}).json()
        response=client.post('/api/investigations',json={'dataset_id':data['id'],'question':'Analyze revenue',
            'model':'ollama:gemma4:e4b'})
        hosted=client.post('/api/investigations',json={'dataset_id':data['id'],'question':'Analyze revenue',
            'model':'gemma-4-26b-a4b-it'})
    assert response.status_code==503 and 'ollama pull' in response.json()['detail']
    assert hosted.status_code==422 and not sessions.investigations


@pytest.mark.parametrize('tool,args,missing',[
    ('calculate_statistics',{'column':'trip_distance'},'operation'),
    ('calculate_statistics',{'operation':None,'column':'trip_distance'},'operation'),
    ('calculate_statistics',{'operation':'summary'},'column'),
    ('calculate_statistics',{'operation':'correlation','column':'trip_distance'},'other_column'),
    ('calculate_statistics',{'operation':'group_comparison','column':'total_amount'},'group_by'),
    ('calculate_statistics',{'operation':'percentage_change','before':10},'after'),
    ('execute_sql',{},'sql'), ('execute_sql',{'sql':'   '},'sql'),
    ('generate_chart',{'evidence_id':'E01','chart_type':'bar','x':'Region'},'y'),
    ('verify_finding',{'evidence_id':'E01','field':'total','expected':0},'row'),
])
def test_incomplete_calls_are_rejected_before_execution(tool,args,missing):
    with pytest.raises(ValueError,match=missing):
        validate_tool_arguments(AgentAction(tool=tool,args=args,explanation='Analyze the data.'))


def test_zero_valued_verification_arguments_are_valid():
    action=AgentAction(tool='verify_finding',explanation='Verify zero.',args={
        'evidence_id':'E01','row':0,'field':'total','expected':0})
    assert validate_tool_arguments(action) is action


def test_omitted_operation_is_not_accepted_from_an_ollama_response():
    with pytest.raises(ValueError,match='calculate_statistics requires: operation'):
        invoke(lambda request:httpx.Response(200,json={'done':True,'message':{'content':json.dumps({
            'tool':'calculate_statistics','explanation':'Summarize trips.','args':{'column':'trip_distance'}})}}))


def test_local_schema_requires_arguments_for_the_selected_tool():
    variants=local_action_json_schema()['oneOf']
    tools={item['properties']['tool']['const']:item['properties']['args'] for item in variants}
    assert tools['execute_sql']['required']==['sql']
    assert tools['execute_sql']['properties']['sql']['type']=='string'
    for option in tools['calculate_statistics']['oneOf']:
        assert 'operation' in option['required']
        assert option['properties']['operation']['const'] in {'summary','mode','outliers','correlation','group_comparison','percentage_change'}
        if option['properties']['operation']['const']!='percentage_change':
            assert 'column' in option['required'] and option['properties']['column']['type']=='string'


def test_missing_operation_never_reaches_statistics_and_is_returned_as_feedback(monkeypatch):
    sessions.datasets['taxi']=sessions.Dataset('taxi','taxi.csv',pd.DataFrame({'trip_distance':[1,2,100]}),{'columns':[]})
    state=sessions.create_investigation(InvestigationRequest(dataset_id='taxi',question='Find unusual trips',model='ollama:gemma4:e4b'))
    agent=InvestigationAgent(state,client=object())
    monkeypatch.setattr('backend.agent.investigator.calculate_statistics',lambda *args:pytest.fail('Incomplete calls must not execute'))
    result=asyncio.run(agent.execute(AgentAction(tool='calculate_statistics',explanation='Find unusual trips.',args={'column':'trip_distance'})))
    assert 'requires: operation' in result['error']
    feedback=agent.context(7)['failed_actions'][-1]
    assert feedback['args']=={'column':'trip_distance'} and 'operation' in feedback['error']


def test_wide_local_observations_fit_the_tool_schema_budget_without_losing_retained_rows():
    frame=pd.DataFrame({name:list(range(20)) for name in ['trip_distance','total_amount',*[f'feature_{i}' for i in range(16)]]})
    sessions.datasets['wide']=sessions.Dataset('wide','wide.csv',frame,profile_dataset(frame))
    state=sessions.create_investigation(InvestigationRequest(dataset_id='wide',question='Use SQL to explore unusual trips',model='ollama:gemma4:e4b'))
    rows=frame.to_dict(orient='records')
    state['evidence']=[{'id':'E01','tool':'execute_sql','result':{'sql':'SELECT * FROM dataset','rows':rows}}]
    context=InvestigationAgent(state,client=object()).context(7)
    assert len(context['observations'][0]['result']['rows'])==5
    assert context['observations'][0]['result']['context_rows_omitted']==15
    assert len(state['evidence'][0]['result']['rows'])==20
    assert len(LOCAL_SYSTEM)+len(json.dumps(context))+len(json.dumps(local_action_json_schema(),separators=(',',':')))+60 < 2*8192


def test_chart_and_verification_choices_use_actual_eligible_evidence():
    frame=pd.DataFrame({'trip_distance':[1,2,100]})
    sessions.datasets['taxi']=sessions.Dataset('taxi','taxi.csv',frame,profile_dataset(frame))
    state=sessions.create_investigation(InvestigationRequest(dataset_id='taxi',question='Investigate unusual trips',model='ollama:gemma4:e4b'))
    state['evidence']=[
        {'id':'E01','tool':'calculate_statistics','result':{'r':.9,'n':10}},
        {'id':'E02','tool':'calculate_statistics','result':{'rows':[{'trip_distance':100}]}},
        {'id':'E03','tool':'execute_sql','result':{'rows':[]}},
        {'id':'E04','tool':'execute_sql','result':{'rows':[{'total':0}]}},
    ]
    constraints=InvestigationAgent(state,client=object()).action_constraints()
    assert constraints=={'chart_evidence_ids':['E02','E04'],'verification_evidence_ids':['E04']}
    tools={item['properties']['tool']['const']:item['properties']['args'] for item in local_action_json_schema(constraints)['oneOf']}
    assert all(option['properties']['evidence_id']['enum']==['E02','E04'] for option in tools['generate_chart']['oneOf'])
    assert tools['verify_finding']['properties']['evidence_id']['enum']==['E04']
    initial=local_action_json_schema({'chart_evidence_ids':[],'verification_evidence_ids':[]})
    assert not {'generate_chart','verify_finding'} & {item['properties']['tool']['const'] for item in initial['oneOf']}

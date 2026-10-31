"""Repeated planner requests reuse evidence without hiding failures or new analyses."""
import asyncio
import pandas as pd
import pytest
from backend.agent.investigator import InvestigationAgent
from backend.agent.schemas import AgentAction, AgentReport, InvestigationRequest
from backend.services import sessions
from backend.tools.profiler import profile_dataset


@pytest.fixture
def agent():
    frame=pd.DataFrame({'value':[1,2,2,4],'label':['A B','A  B','Other','Other']})
    dataset=sessions.Dataset('repeat-test','repeat.csv',frame,profile_dataset(frame))
    sessions.datasets[dataset.id]=dataset
    state=sessions.create_investigation(InvestigationRequest(dataset_id=dataset.id,question='Find the sum and mode'))
    investigator=InvestigationAgent(state,client=object())
    yield investigator
    sessions.datasets.pop(dataset.id,None)
    sessions.investigations.pop(state['id'],None)


def statistics(operation='summary',column='value',**kwargs):
    return AgentAction(tool='calculate_statistics',explanation='Calculate requested statistics.',
                       args={'operation':operation,'column':column,**kwargs})


def report(agent):
    source=next(e for e in agent.state['evidence'] if e['tool'] in {'execute_sql','calculate_statistics'})
    sql=source['tool']=='execute_sql'
    return AgentReport(summary='Computed evidence is available.',findings=[{
        'claim':'Measured total from the uploaded data.','kind':'observation','evidence_ids':[source['id']],
        'measurements':[{'evidence_id':source['id'],'row':0 if sql else None,'field':'total' if sql else 'sum',
                         'value':source['result']['rows'][0]['total'] if sql else source['result']['sum']}],
    }],limitations=[],next_steps=[])


def scripted_model(agent,actions,contexts):
    iterator=iter(actions)
    async def generate(schema,context):
        if schema is AgentReport:
            return report(agent)
        contexts.append(context)
        return next(iterator)
    agent.generate=generate


@pytest.mark.parametrize('model',['gemini-3.5-flash-lite','ollama:gemma4:e4b'])
def test_repeated_summary_reuses_evidence_and_model_can_recover(agent,model,monkeypatch):
    monkeypatch.setenv('MAX_AGENT_STEPS','8')
    agent.model=model
    duplicate=statistics()
    duplicate.explanation='Repeat with a different explanation.'
    duplicate.plan=['A changed plan must not make the same calculation new.']
    contexts=[]
    scripted_model(agent,[statistics(),duplicate,statistics('mode'),
                         AgentAction(tool='finish',explanation='Requested statistics are available.')],contexts)
    asyncio.run(agent.run())
    state=agent.state
    assert state['status']=='completed' and state['stop_reason']=='sufficient_evidence'
    assert len(agent.analytical_evidence())==2
    skipped=[e for e in state['events'] if e['status']=='skipped']
    assert len(skipped)==1 and skipped[0]['reused_evidence'] is True
    assert skipped[0]['evidence_id']==agent.analytical_evidence()[0]['id']
    assert any('reuse '+skipped[0]['evidence_id'] in message for message in contexts[2]['recent_errors'])
    assert any('two distinct' in message for message in contexts[2]['completion_requirements'])
    assert state['findings'][0]['measurements'][0]['value']==9


def test_persistent_repetition_stops_early_with_partial_evidence(agent,monkeypatch):
    monkeypatch.setenv('MAX_AGENT_STEPS','8')
    contexts=[]
    scripted_model(agent,[statistics() for _ in range(8)],contexts)
    asyncio.run(agent.run())
    state=agent.state
    assert len(contexts)==3  # One actual calculation and two bounded duplicate requests.
    assert state['status']=='partial' and state['stop_reason']=='repeated_action_limit'
    assert len(agent.analytical_evidence())==1
    assert sum(e['status']=='skipped' for e in state['events'])==2
    assert state['report'] and state['findings'][0]['measurements'][0]['value']==9
    assert any('narrow the question' in message for message in state['errors'])


def test_failed_action_can_be_retried_with_identical_arguments(agent,monkeypatch):
    monkeypatch.setenv('MAX_AGENT_STEPS','8')
    original_tool=agent.tool
    attempts=0
    async def tool(action):
        nonlocal attempts
        if action.tool=='calculate_statistics' and action.args.operation=='summary':
            attempts+=1
            if attempts==1:
                raise ValueError('Temporary calculation failure.')
        return await original_tool(action)
    agent.tool=tool
    scripted_model(agent,[statistics(),statistics(),statistics('mode'),
                         AgentAction(tool='finish',explanation='Requested statistics are available.')],[])
    asyncio.run(agent.run())
    assert attempts==2 and agent.state['status']=='completed'
    assert len(agent.analytical_evidence())==2
    assert not any(e['status']=='skipped' for e in agent.state['events'])


def test_sql_literal_whitespace_stays_distinct_and_verification_still_executes(agent,monkeypatch):
    monkeypatch.setenv('MAX_AGENT_STEPS','8')
    def sql(label):
        return AgentAction(tool='execute_sql',explanation='Compare exact category labels.',
            args={'sql':f"SELECT SUM(value) AS total FROM dataset WHERE label='{label}'"})
    scripted_model(agent,[sql('A B'),sql('A B'),sql('A  B'),sql('A B')],[])
    asyncio.run(agent.run())
    state=agent.state
    sources=[e for e in state['evidence'] if e['tool']=='execute_sql']
    assert [e['result']['rows'][0]['total'] for e in sources]==[1,2]
    assert len({e['id'] for e in sources})==2
    assert state['status']=='partial' and state['stop_reason']=='repeated_action_limit'
    assert any(e['tool']=='verify_finding' and e['result']['status']=='verified' for e in state['evidence'])
    assert state['charts'] and state['report']['verified_cells']==1


def test_parameter_key_order_does_not_repeat_an_advanced_calculation(agent,monkeypatch):
    monkeypatch.setenv('MAX_AGENT_STEPS','8')
    first=statistics('confidence_interval',parameters={'confidence':0.95,'method':'t'})
    reordered=statistics('confidence_interval',parameters={'method':'t','confidence':0.95})
    scripted_model(agent,[statistics(),first,reordered,
                         AgentAction(tool='finish',explanation='Requested calculations are available.')],[])
    asyncio.run(agent.run())
    assert agent.state['status']=='completed',agent.state['errors']
    assert len(agent.analytical_evidence())==2
    assert sum(e['status']=='skipped' for e in agent.state['events'])==1

import asyncio
import json
import numpy as np
import pandas as pd
import pytest
from backend.agent.schemas import AgentAction, InvestigationRequest, ToolArgs
from backend.agent.investigator import InvestigationAgent
from backend.services import sessions
from backend.services.reporting import finalize_report
from backend.tools.profiler import profile_dataset
from backend.tools.sql_engine import execute_sql
from backend.tools.statistics import calculate_statistics


def test_summary_supplies_sum_and_the_requested_descriptive_statistics():
    frame=pd.DataFrame({'total_amount':[10.,20.,20.,40.,50.,np.nan,np.inf]})
    result=calculate_statistics(frame,ToolArgs(operation='summary',column='total_amount'))
    assert result['count']==5 and result['sum']==140
    assert result['mean']==28 and result['min']==10 and result['max']==50
    assert result['std']==pytest.approx(np.std([10,20,20,40,50],ddof=1))
    assert 'sample' in result['note']


@pytest.mark.parametrize('values,expected,frequency',[
    ([10.,20.,20.,40.,np.nan,np.inf],[20.],2),
    ([1,1,2,2,3],[1,2],2),
    ([3,1,2],[1,2,3],1),
    ([1e-12,2e-12,2e-12],[2e-12],2),
    (['Card','Cash','Cash',None],['Cash'],2),
    (['Cash',1,'Cash',1], [1,'Cash'],2),
    ([7],[7],1),
])
def test_mode_preserves_values_frequencies_and_ties(values,expected,frequency):
    result=calculate_statistics(pd.DataFrame({'value':values}),ToolArgs(operation='mode',column='value'))
    assert result['rows']==[{'mode':value,'frequency':frequency} for value in expected]
    assert result['mode_count']==len(expected) and result['frequency']==frequency
    assert result['mode']==(expected[0] if len(expected)==1 else None)
    if len(expected)>1: assert 'no unique mode' in result['note']
    json.dumps(result,allow_nan=False)


def test_mode_reports_truncation_instead_of_pretending_one_value_is_unique():
    result=calculate_statistics(pd.DataFrame({'value':range(250)}),ToolArgs(operation='mode',column='value'))
    assert result['mode'] is None and result['mode_count']==250 and result['frequency']==1
    assert len(result['rows'])==200 and result['truncated'] is True


def test_empty_mode_and_overflowing_summary_fail_with_controlled_errors():
    with pytest.raises(ValueError,match='No nonmissing finite values'):
        calculate_statistics(pd.DataFrame({'value':[np.nan,np.inf]}),ToolArgs(operation='mode',column='value'))
    with pytest.raises(ValueError,match='overflowed'):
        calculate_statistics(pd.DataFrame({'value':[1e308,1e308]}),ToolArgs(operation='summary',column='value'))


def test_integer_sum_does_not_wrap_at_int64_limit():
    result=calculate_statistics(pd.DataFrame({'value':pd.Series([2**62,2**62],dtype='int64')}),ToolArgs(operation='summary',column='value'))
    assert result['sum']==2**63


def test_sql_mode_is_allowed_and_ties_can_be_broken_deterministically():
    frame=pd.DataFrame({'total_amount':[3,3,1,1,9]})
    result=execute_sql(frame,'SELECT MODE(total_amount ORDER BY total_amount) AS mode FROM dataset')
    assert result['rows']==[{'mode':1}]


def test_tied_modes_remain_evidence_backed_in_computed_reports():
    frame=pd.DataFrame({'total_amount':[1,1,2,2,3]})
    dataset=sessions.Dataset('mode-report','mode.csv',frame,profile_dataset(frame))
    sessions.datasets[dataset.id]=dataset
    state=sessions.create_investigation(InvestigationRequest(dataset_id=dataset.id,question='Find all modes',model='ollama:gemma4:e4b'))
    agent=InvestigationAgent(state,client=object())
    result=asyncio.run(agent.execute(AgentAction(tool='calculate_statistics',explanation='Compute all tied modes.',args={'operation':'mode','column':'total_amount'})))
    assert 'error' not in result
    finalize_report(state,agent.fallback_report())
    modes=[item['value'] for finding in state['findings'] for item in finding['measurements'] if item['field']=='mode']
    assert modes==[1,2] and not state['report']['warnings']

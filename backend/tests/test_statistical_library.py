"""Numerical fixtures for the analysis families, not just dispatcher coverage."""
import asyncio
import json
import math
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.agent.schemas import AgentAction, InvestigationRequest, ToolArgs
from backend.agent.investigator import InvestigationAgent
from backend.agent.tool_contracts import local_action_json_schema, validate_tool_arguments
from backend.main import app
from backend.services import sessions
from backend.services.reporting import finalize_report, resolve_measurement
from backend.tools.charts import generate_chart
from backend.tools.profiler import profile_dataset
from backend.tools.statistics import calculate_statistics
from backend.tools.statistical_catalog import OPERATIONS, describe_statistics
from backend.tools.sql_engine import execute_sql


def calc(df,operation,**args):
    result=calculate_statistics(df,ToolArgs(operation=operation,**args))
    json.dumps(result,allow_nan=False)
    return result


def test_extended_summary_and_exclusive_quantiles():
    df=pd.DataFrame({'x':[1.,2,3,4]})
    result=calc(df,'summary',column='x')
    assert result['variance']==pytest.approx(5/3)
    assert result['variance_population']==1.25
    assert result['standard_error']==pytest.approx(math.sqrt(5/3)/2)
    assert result['skewness']==0
    assert result['kurtosis']==pytest.approx(-1.2)
    for method,expected in [('inclusive',1.75),('exclusive',1.25)]:
        assert calc(df,'quantiles',column='x',parameters={'method':method,'probabilities':[.25]})['rows'][0]['value']==expected
    with pytest.raises(ValueError,match='Exclusive percentile'):
        calc(df,'quantiles',column='x',parameters={'method':'exclusive','probabilities':[.1]})


def test_histogram_upper_bounds_and_rank_ties():
    df=pd.DataFrame({'x':[1,2,2,3,4,5]})
    result=calc(df,'histogram',column='x',parameters={'bins':[2,4]})
    assert [r['count'] for r in result['rows']]==[3,2,1]
    assert result['rows'][-1]['cumulative_percent']==100
    ranks=calc(df,'rank',column='x',parameters={'descending':False,'ties':'average'})['rows']
    assert [r['rank'] for r in ranks]==[1,2.5,2.5,4,5,6]
    assert ranks[1]['percentile_rank']==.2


def test_covariance_complete_cases_and_matrix_chart_preserves_cells():
    df=pd.DataFrame({'x':[1.,2,3,np.nan],'y':[2.,4,6,100]})
    assert calc(df,'covariance',column='x',other_column='y',parameters={'population':True})['covariance']==pytest.approx(4/3)
    assert calc(df,'covariance',column='x',other_column='y',parameters={'population':False})['covariance']==2
    for operation,expected in [('covariance_matrix',[[2/3,4/3],[4/3,8/3]]),('correlation_matrix',[[1,1],[1,1]])]:
        result=calc(df,operation,parameters={'columns':['x','y']})
        chart=generate_chart(result,ToolArgs(chart_type='heatmap',evidence_id='E01'))
        np.testing.assert_allclose(chart['data'][0]['z'],expected)
        assert result['n']==3
    result=calc(df.rename(columns={'x':'variable'}),'covariance_matrix',parameters={'columns':['variable','y']})
    chart=generate_chart(result,ToolArgs(chart_type='heatmap',evidence_id='E01'))
    assert chart['data'][0]['x']==['variable','y']
    np.testing.assert_allclose(chart['data'][0]['z'],[[2/3,4/3],[4/3,8/3]])


@pytest.mark.parametrize('method,expected_df',[('paired',4),('equal_variance',8),('welch',pytest.approx(392/53))])
def test_t_test_variants(method,expected_df):
    df=pd.DataFrame({'x':[1.,2,3,4,5],'y':[1.,3,4,6,6]})
    result=calc(df,'t_test',column='x',other_column='y',parameters={'method':method})
    assert result['df']==expected_df
    if method=='paired':
        assert result['statistic']==pytest.approx(-math.sqrt(10))
        assert result['p_value']==pytest.approx(.0341094231674)
    assert not result['reject_null'] if method!='paired' else result['reject_null']


def test_one_sample_z_known_variances_and_f_test():
    df=pd.DataFrame({'x':[1.,2,3],'y':[2.,4,6]})
    normal=calc(df,'one_sample_test',column='x',parameters={'method':'z','mean':2,'sigma':1})
    assert normal['statistic']==0 and normal['p_value']==1
    t=calc(df,'one_sample_test',column='x',parameters={'mean':2})
    assert t['statistic']==0 and t['p_value']==1
    z=calc(df,'z_test',column='x',other_column='y',parameters={'variance1':1,'variance2':4})
    assert z['statistic']==pytest.approx(-2/math.sqrt(5/3))
    f=calc(df,'f_test',column='x',other_column='y')
    assert f['statistic']==.25 and f['p_value']==pytest.approx(.4)
    ci=calc(df,'confidence_interval',column='x',parameters={'method':'normal','sigma':1})
    assert ci['margin']==pytest.approx(1.95996398454/math.sqrt(3))
    with pytest.raises(ValueError,match='known population sigma'):
        calc(df,'confidence_interval',column='x',parameters={'method':'normal'})


def test_chi_square_and_anova_hand_calculations():
    df=pd.DataFrame({'observed':[30.,20,10,40],'expected':[20.,30,20,30]})
    chi=calc(df,'chi_square_test',column='observed',other_column='expected',parameters={'method':'goodness_of_fit'})
    assert chi['statistic']==pytest.approx(50/3)
    assert chi['df']==3
    cats=pd.DataFrame({'a':['a']*50+['b']*50,'b':['c']*30+['d']*20+['c']*10+['d']*40})
    independent=calc(cats,'chi_square_test',column='a',other_column='b')
    assert independent['statistic']==pytest.approx(50/3) and independent['df']==1
    anova=calc(pd.DataFrame({'x':[1.,2,3,4,5,6],'group':['A']*3+['B']*3}),
               'anova_one_way',column='x',group_by='group')
    assert anova['statistic']==13.5
    assert anova['rows'][0]['ss']==13.5 and anova['rows'][1]['ss']==4


def test_high_cardinality_chi_square_is_rejected_before_allocating_contingency_table(monkeypatch):
    df=pd.DataFrame({'a':range(1000),'b':range(1000)})
    monkeypatch.setattr(pd,'crosstab',lambda *a,**k:pytest.fail('Cardinality must be checked before allocating the table'))
    with pytest.raises(ValueError,match='one hundred levels'):
        calc(df,'chi_square_test',column='a',other_column='b')


def test_two_way_anova_replicated_and_without_replication():
    # Cell means [[1.5,3.5],[5.5,9.5]], two replicates per cell.
    df=pd.DataFrame({'x':[1.,2,3,4,5,6,9,10],'a':['A']*4+['B']*4,'b':['C','C','D','D']*2})
    result=calc(df,'anova_two_way',column='x',group_by='a',parameters={'factor2':'b'})
    assert [row['ss'] for row in result['rows']]==pytest.approx([50,18,2,2,72])
    assert [row['f_statistic'] for row in result['rows'][:3]]==pytest.approx([100,36,4])
    single=df.groupby(['a','b'],as_index=False)['x'].mean()
    result=calc(single,'anova_two_way',column='x',group_by='a',parameters={'factor2':'b','replication':False})
    assert [row['ss'] for row in result['rows']]==pytest.approx([25,9,1,35])
    with pytest.raises(ValueError,match='balanced cells'):
        calc(df.iloc[:-1],'anova_two_way',column='x',group_by='a',parameters={'factor2':'b'})


def test_multiple_regression_predictions_and_collinear_rejection():
    df=pd.DataFrame({'x':[1.,2,3,4,5,6],'z':[0.,1,0,1,0,1]})
    df['y']=1+2*df.x+3*df.z
    result=calc(df,'regression',column='y',parameters={'predictors':['x','z'],'predict_at':[[7,1]]})
    assert [r['coefficient'] for r in result['rows']]==pytest.approx([1,2,3])
    assert result['r_squared']==1
    assert result['predictions'][0]['prediction']==pytest.approx(18)
    assert result['sse']<1e-20
    df['x2']=df.x*2
    with pytest.raises(ValueError,match='full-rank'):
        calc(df,'regression',column='y',parameters={'predictors':['x','x2']})


def test_time_series_smoothing_forecast_and_fft():
    df=pd.DataFrame({'x':[1.,2,3,4,5,6,7,8]})
    moving=calc(df,'moving_average',column='x',parameters={'window':2})
    assert [r['moving_average'] for r in moving['rows'][:4]]==[None,1.5,2.5,3.5]
    assert moving['next_forecast']==7.5
    assert calc(df.iloc[:3],'exponential_smoothing',column='x',parameters={'alpha':.5})['next_forecast']==2.25
    forecast=calc(df,'forecast',column='x',parameters={'steps':2})
    assert [r['forecast'] for r in forecast['rows']]==pytest.approx([9,10],abs=1e-3)
    assert all(r['lower']<=r['upper'] for r in forecast['rows'])
    fft=calc(pd.DataFrame({'x':[1.,0,0,0]}),'fourier_analysis',column='x')
    assert [r['real'] for r in fft['rows']]==[1,1,1,1]
    inverse=calc(pd.DataFrame({'x':[1.,1,1,1]}),'fourier_analysis',column='x',parameters={'inverse':True})
    assert [r['real'] for r in inverse['rows']]==[1,0,0,0]
    df['time']=[1,2,3,5,6,7,8,9]
    with pytest.raises(ValueError,match='regularly spaced'):
        calc(df,'forecast',column='x',parameters={'order_by':'time'})
    df['time']=pd.date_range('2026-01-01',periods=8,freq='MS')
    assert calc(df,'forecast',column='x',parameters={'order_by':'time','steps':1})['rows'][0]['forecast']==pytest.approx(9,abs=1e-3)


def test_sampling_random_generation_and_normality():
    df=pd.DataFrame({'x':range(100)})
    sample=calc(df,'sampling',parameters={'size':5,'seed':3})
    assert sample==calc(df,'sampling',parameters={'size':5,'seed':3})
    periodic=calc(df,'sampling',parameters={'method':'periodic','period':10,'size':3})
    assert [r['x'] for r in periodic['rows']]==[9,19,29]
    for distribution in ['normal','uniform','bernoulli','binomial','poisson','discrete','patterned']:
        p={'distribution':distribution,'size':5,'values':[10,20],'probabilities':[.25,.75]}
        result=calc(df,'random_generation',parameters=p)
        assert result['source_type']=='simulation' and len(result['rows'])==5
        assert result==calc(df,'random_generation',parameters=p)
    normal=calc(df,'normality_test',column='x')
    assert normal['statistic']==pytest.approx(.954724744,rel=1e-6)


def test_overflowing_inference_and_fft_return_explicit_errors():
    df=pd.DataFrame({'x':[1e308]*4})
    with pytest.raises(ValueError,match='finite precision'):
        calc(df,'confidence_interval',column='x',parameters={'method':'normal','sigma':1})
    with pytest.raises(ValueError,match='finite precision'):
        calc(df,'fourier_analysis',column='x')


def test_catalog_discovery_is_connected_to_local_schema_and_execution():
    df=pd.DataFrame({'x':[1.,2,3,4,5],'y':[2.,4,4,5,6]})
    item=sessions.Dataset('stat-discovery','stats.csv',df,profile_dataset(df));sessions.datasets[item.id]=item
    state=sessions.create_investigation(InvestigationRequest(dataset_id=item.id,question='Test the difference',model='ollama:gemma4:e4b'))
    agent=InvestigationAgent(state,client=object())
    for name in ['t_test','PERCENTILE.EXC']:
        asyncio.run(agent.execute(AgentAction(tool='statistics_catalog',explanation='Discover exact parameters.',args={'name':name})))
    wire=local_action_json_schema(agent.action_constraints())
    assert 'TTestParameters' in json.dumps(wire) and 'PERCENTILE.EXC' in json.dumps(wire)
    assert '#/$defs/ColumnReference' in json.dumps(wire)
    entry=asyncio.run(agent.execute(AgentAction(tool='calculate_statistics',explanation='Compare actual columns.',
        args={'operation':'t_test','column':'x','other_column':'y','parameters':{'method':'paired'}})))
    assert entry['result']['p_value']<.1
    assert describe_statistics('rank')['kind']=='operation'
    assert describe_statistics('RANK')['function']=='RANK.EQ'
    assert describe_statistics('confidence')['kind']=='catalog'
    assert describe_statistics()['operation_count']==len(OPERATIONS)==29
    finalize_report(state,agent.fallback_report())
    assert any(m['field']=='p_value' for f in state['findings'] for m in f['measurements'])
    assert not state['report']['warnings']
    asyncio.run(agent.execute(AgentAction(tool='statistics_catalog',explanation='Discover all analysis families.',args={'name':'all'})))
    menu=agent.context(5)['observations'][-1]['result']
    assert set(menu['operations'])==set(OPERATIONS)


def test_simulation_and_parameter_calculations_cannot_be_reported_as_dataset_findings():
    result=calc(pd.DataFrame(),'random_generation')
    state={'evidence':[{'id':'E01','tool':'calculate_statistics','result':result}]}
    with pytest.raises(ValueError,match='not dataset-backed'):
        resolve_measurement(state,{'evidence_id':'E01','row':0,'field':'value','value':result['rows'][0]['value']})


@pytest.mark.parametrize('operation,parameters',[('t_test',{'method':'invented'}),('quantiles',{'probabilities':[float('nan')]}),
    ('regression',{'predictors':['x'],'execute':'evil'}),('random_generation',{'size':100000000}),('excel',{'function':'eval','values':[1]})])
def test_invalid_arguments_are_rejected(operation,parameters):
    with pytest.raises(ValueError):
        validate_tool_arguments(AgentAction(tool='calculate_statistics',explanation='Invalid input.',args={'operation':operation,'column':'x','other_column':'y','parameters':parameters}))


def test_statistical_api_works_without_a_model_and_returns_controlled_errors(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    with TestClient(app) as client:
        catalog=client.get('/api/statistics/catalog',params={'name':'T.TEST'}).json()
        assert catalog['function']=='T.TEST'
        uploaded=client.post('/api/datasets',files={'file':('stats.csv',b'x,y\n1,2\n2,4\n3,6\n4,8\n')}).json()
        path=f"/api/datasets/{uploaded['id']}/statistics"
        response=client.post(path,json={'operation':'regression','column':'y','parameters':{'predictors':['x']}})
        assert response.status_code==200
        assert response.json()['rows'][1]['coefficient']==pytest.approx(2)
        response=client.post(path,json={'operation':'excel','parameters':{'function':'NORM.S.DIST','x':0}})
        assert response.status_code==200 and response.json()['value']==.5
        assert response.json()['source_type']=='parameters'
        assert client.post(path,json={'operation':'unknown'}).status_code==422
        assert client.post(path,json={'operation':'summary','column':'unknown'}).status_code==422
        assert client.post('/api/datasets/missing/statistics',json={'operation':'summary','column':'x'}).status_code==404


def test_safe_sql_arithmetic_functions_support_statistical_expressions():
    df=pd.DataFrame({'x':[4.]})
    result=execute_sql(df,'SELECT SQRT(x) AS root, POWER(x, 2) AS square, LN(EXP(1)) AS logarithm, FLOOR(1.9) AS floor_value FROM dataset')
    assert result['rows'][0]=={'root':2.,'square':16.,'logarithm':1.,'floor_value':1.}

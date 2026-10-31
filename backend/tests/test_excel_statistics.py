"""Fixtures for every exposed worksheet function and Microsoft's reference list."""
import json
import math
import numpy as np
import pandas as pd
import pytest
from backend.agent.schemas import ToolArgs
from backend.tools.statistics import calculate_statistics
from backend.tools.statistical_excel import FUNCTIONS, ALIASES, function_schema


# Microsoft Support statistical-functions reference, checked 2026-10-31.
EXCEL_REFERENCE=set('''AVEDEV AVERAGE AVERAGEA AVERAGEIF AVERAGEIFS BETA.DIST BETA.INV
BINOM.DIST BINOM.DIST.RANGE BINOM.INV CHISQ.DIST CHISQ.DIST.RT CHISQ.INV CHISQ.INV.RT
CHISQ.TEST CONFIDENCE.NORM CONFIDENCE.T CORREL COUNT COUNTA COUNTBLANK COUNTIF COUNTIFS
COVARIANCE.P COVARIANCE.S DEVSQ EXPON.DIST F.DIST F.DIST.RT F.INV F.INV.RT F.TEST
FISHER FISHERINV FORECAST FORECAST.ETS FORECAST.ETS.CONFINT FORECAST.ETS.SEASONALITY
FORECAST.ETS.STAT FORECAST.LINEAR FREQUENCY GAMMA GAMMA.DIST GAMMA.INV GAMMALN
GAMMALN.PRECISE GAUSS GEOMEAN GROWTH HARMEAN HYPGEOM.DIST INTERCEPT KURT LARGE LINEST
LOGEST LOGNORM.DIST LOGNORM.INV MAX MAXA MAXIFS MEDIAN MIN MINIFS MINA MODE.MULT
MODE.SNGL NEGBINOM.DIST NORM.DIST NORM.INV NORM.S.DIST NORM.S.INV PEARSON PERCENTILE.EXC
PERCENTILE.INC PERCENTRANK.EXC PERCENTRANK.INC PERMUT PERMUTATIONA PHI POISSON.DIST PROB
QUARTILE.EXC QUARTILE.INC RANK.AVG RANK.EQ RSQ SKEW SKEW.P SLOPE SMALL STANDARDIZE
STDEV.P STDEV.S STDEVA STDEVPA STEYX T.DIST T.DIST.2T T.DIST.RT T.INV T.INV.2T T.TEST
TREND TRIMMEAN VAR.P VAR.S VARA VARPA WEIBULL.DIST Z.TEST'''.split())


def excel(name,df=None,evidence=None,**parameters):
    return calculate_statistics(df if df is not None else pd.DataFrame(),
        ToolArgs(operation='excel',parameters={'function':name,**parameters}),evidence)


def test_reference_coverage_and_schema_definitions():
    assert EXCEL_REFERENCE<=FUNCTIONS.keys()
    assert len(FUNCTIONS)==116
    for name in FUNCTIONS:
        schema=function_schema(name)
        assert schema['properties']['function']['const']==name
        assert schema['additionalProperties'] is False


# Distinct expected results for aggregates; the mixed range separately tests A variants.
AGGREGATES={
    'AVEDEV':1.2,'AVERAGE':3,'AVERAGEA':3,'COUNT':5,'COUNTA':5,'COUNTBLANK':0,
    'DEVSQ':10,'GEOMEAN':120**.2,'HARMEAN':300/137,'KURT':-1.2,'MAX':5,'MAXA':5,
    'MEDIAN':3,'MIN':1,'MINA':1,'MODE.MULT':[2],'MODE.SNGL':2,'SKEW':0,'SKEW.P':0,
    'STDEV.P':math.sqrt(2),'STDEV.S':math.sqrt(2.5),'STDEVA':math.sqrt(2.5),'STDEVPA':math.sqrt(2),
    'VAR.P':2,'VAR.S':2.5,'VARA':2.5,'VARPA':2,'SUM':15,'SUMSQ':55,'PRODUCT':120,
}


@pytest.mark.parametrize('name,expected',AGGREGATES.items())
def test_aggregate_numerical_fixtures(name,expected):
    result=excel(name,values=[1,2,2,3,4] if name.startswith('MODE.') else [1,2,3,4,5])
    if isinstance(expected,list):assert [r['value'] for r in result['rows']]==expected
    else:assert result['value']==pytest.approx(expected)


CASES={
    'LARGE':({'values':[1,2,3,4,5],'k':2},4),
    'SMALL':({'values':[1,2,3,4,5],'k':2},2),
    'TRIMMEAN':({'values':[0,1,2,3,100],'percent':.4},2),
    'PERCENTILE.INC':({'values':[1,2,3,4],'k':.25},1.75),
    'PERCENTILE.EXC':({'values':[1,2,3,4],'k':.25},1.25),
    'QUARTILE.INC':({'values':[1,2,3,4],'quart':1},1.75),
    'QUARTILE.EXC':({'values':[1,2,3,4],'quart':1},1.25),
    'PERCENTRANK.INC':({'values':[1,2,3,4],'x':2.5},.5),
    'PERCENTRANK.EXC':({'values':[1,2,3,4],'x':2.5},.5),
    'RANK.EQ':({'values':[1,2,2,4],'number':2},2),
    'RANK.AVG':({'values':[1,2,2,4],'number':2},2.5),
    'FREQUENCY':({'values':[1,2,2,3,4,5],'bins':[2,4]},[3,2,1]),
    'COUNTIF':({'range':['East','east','West'],'criterion':'e*'},2),
    'AVERAGEIF':({'range':[1,2,3,4],'criterion':'>2'},3.5),
    'SUMIF':({'range':[1,2,3,4],'criterion':'>2','result_range':[10,20,30,40]},70),
    'COUNTIFS':({'criteria':[{'range':[1,2,3,4],'criterion':'>1'},{'range':['A','B','A','B'],'criterion':'A'}]},1),
    'AVERAGEIFS':({'criteria':[{'range':[1,2,3,4],'criterion':'>1'}],'values':[10,20,30,40]},30),
    'MINIFS':({'criteria':[{'range':[1,2,3,4],'criterion':'>1'}],'values':[10,20,30,40]},20),
    'MAXIFS':({'criteria':[{'range':[1,2,3,4],'criterion':'>1'}],'values':[10,20,30,40]},40),
    'SUMIFS':({'criteria':[{'range':[1,2,3,4],'criterion':'>1'}],'values':[10,20,30,40]},90),
    'CORREL':({'array1':[1,2,3],'array2':[2,4,6]},1),
    'PEARSON':({'array1':[1,2,3],'array2':[2,4,6]},1),
    'COVARIANCE.P':({'array1':[1,2,3],'array2':[2,4,6]},4/3),
    'COVARIANCE.S':({'array1':[1,2,3],'array2':[2,4,6]},2),
    'RSQ':({'array1':[1,2,3],'array2':[2,4,6]},1),
    'INTERCEPT':({'known_y':[3,5,7,9],'known_x':[1,2,3,4]},1),
    'SLOPE':({'known_y':[3,5,7,9],'known_x':[1,2,3,4]},2),
    'STEYX':({'known_y':[3,5,7,9],'known_x':[1,2,3,4]},0),
    'FORECAST':({'x':5,'known_y':[3,5,7,9],'known_x':[1,2,3,4]},11),
    'FORECAST.LINEAR':({'x':5,'known_y':[3,5,7,9],'known_x':[1,2,3,4]},11),
    'TREND':({'known_y':[3,5,7,9],'new_x':[5,6]},[11,13]),
    'GROWTH':({'known_y':[2,4,8,16],'new_x':[5]},[32]),
    'STANDARDIZE':({'x':5,'mean':3,'standard_dev':2},1),
    'CONFIDENCE.NORM':({'alpha':.05,'standard_dev':1,'size':100},.195996398454),
    'CONFIDENCE.T':({'alpha':.05,'standard_dev':1,'size':5},1.2416639982),
    'FISHER':({'x':.5},math.log(3)/2),
    'FISHERINV':({'x':math.log(3)/2},.5),
    'GAMMA':({'x':5},24),
    'GAMMALN':({'x':5},math.log(24)),
    'GAMMALN.PRECISE':({'x':5},math.log(24)),
    'GAUSS':({'x':0},0),
    'PHI':({'x':0},1/math.sqrt(2*math.pi)),
    'PERMUT':({'number':5,'number_chosen':2},20),
    'PERMUTATIONA':({'number':5,'number_chosen':2},25),
    'PROB':({'values':[1,2,3],'probabilities':[.2,.3,.5],'lower_limit':2,'upper_limit':3},.8),
    'T.TEST':({'array1':[1,2,3,4,5],'array2':[1,3,4,6,6],'type':1},.0341094231674),
    'F.TEST':({'array1':[1,2,3],'array2':[2,4,6]},.4),
    'Z.TEST':({'values':[1,2,3],'x':2,'sigma':1},.5),
    'CHISQ.TEST':({'actual':[10,20],'expected':[15,15]},.0678891548618),
    'NORM.DIST':({'x':2,'mean':2,'standard_dev':3},.5),
    'NORM.INV':({'probability':.5,'mean':2,'standard_dev':3},2),
    'NORM.S.DIST':({'x':0},.5),
    'NORM.S.INV':({'probability':.5},0),
    'BETA.DIST':({'x':.5,'alpha':2,'beta':2},.5),
    'BETA.INV':({'probability':.5,'alpha':2,'beta':2},.5),
    'BINOM.DIST':({'number_s':2,'trials':4,'probability_s':.5,'cumulative':False},.375),
    'BINOM.DIST.RANGE':({'number_s':1,'number_s2':3,'trials':4,'probability_s':.5},.875),
    'BINOM.INV':({'trials':4,'probability_s':.5,'alpha':.5},2),
    'CHISQ.DIST':({'x':2,'degrees_freedom':2},1-math.exp(-1)),
    'CHISQ.DIST.RT':({'x':2,'degrees_freedom':2},math.exp(-1)),
    'CHISQ.INV':({'probability':1-math.exp(-1),'degrees_freedom':2},2),
    'CHISQ.INV.RT':({'probability':math.exp(-1),'degrees_freedom':2},2),
    'F.DIST':({'x':1,'degrees_freedom1':2,'degrees_freedom2':2},.5),
    'F.DIST.RT':({'x':1,'degrees_freedom1':2,'degrees_freedom2':2},.5),
    'F.INV':({'probability':.5,'degrees_freedom1':2,'degrees_freedom2':2},1),
    'F.INV.RT':({'probability':.5,'degrees_freedom1':2,'degrees_freedom2':2},1),
    'T.DIST':({'x':0,'degrees_freedom':1},.5),
    'T.DIST.RT':({'x':1,'degrees_freedom':1},.25),
    'T.DIST.2T':({'x':1,'degrees_freedom':1},.5),
    'T.INV':({'probability':.75,'degrees_freedom':1},1),
    'T.INV.2T':({'probability':.5,'degrees_freedom':1},1),
    'EXPON.DIST':({'x':1,'rate':1},1-math.exp(-1)),
    'GAMMA.DIST':({'x':1,'alpha':1,'beta':1},1-math.exp(-1)),
    'GAMMA.INV':({'probability':1-math.exp(-1),'alpha':1,'beta':1},1),
    'LOGNORM.DIST':({'x':1,'mean':0,'standard_dev':1},.5),
    'LOGNORM.INV':({'probability':.5,'mean':0,'standard_dev':1},1),
    'WEIBULL.DIST':({'x':1,'alpha':1,'beta':1},1-math.exp(-1)),
    'POISSON.DIST':({'x':0,'mean':2,'cumulative':False},math.exp(-2)),
    'NEGBINOM.DIST':({'number_f':2,'number_s':1,'probability_s':.5,'cumulative':False},.125),
    'HYPGEOM.DIST':({'sample_s':2,'number_sample':2,'population_s':2,'number_pop':4,'cumulative':False},1/6),
}


@pytest.mark.parametrize('name,case',CASES.items())
def test_named_function_numerical_fixtures(name,case):
    parameters,expected=case
    result=excel(name,**parameters)
    json.dumps(result,allow_nan=False)
    if isinstance(expected,list):assert [r['value'] for r in result['rows']]==pytest.approx(expected)
    else:assert result['value']==pytest.approx(expected,abs=1e-9)


def test_regression_and_forecast_family_and_every_function_has_a_fixture():
    for name in ['LINEST','LOGEST']:
        result=excel(name,known_y=[3,5,7,9] if name=='LINEST' else [2,4,8,16])
        assert result['r_squared']==1
        assert result['rows'][1]['coefficient']==pytest.approx(2 if name=='LINEST' else math.log(2))
    series={'values':[1,2,3,4,5,6,7,8],'timeline':list(range(1,9))}
    assert excel('FORECAST.ETS',target=9,seasonality=0,**series)['value']==pytest.approx(9,abs=1e-3)
    assert excel('FORECAST.ETS.CONFINT',target=9,seasonality=0,**series)['value']>=0
    assert excel('FORECAST.ETS.SEASONALITY',**series)['value']==0
    assert excel('FORECAST.ETS.STAT',statistic_type=8,**series)['value']==1
    assert set(FUNCTIONS)==set(AGGREGATES)|set(CASES)|{'LINEST','LOGEST','FORECAST.ETS','FORECAST.ETS.CONFINT','FORECAST.ETS.SEASONALITY','FORECAST.ETS.STAT'}


def test_column_references_missing_pairs_text_logicals_and_aliases():
    df=pd.DataFrame({'mixed':[2,True,'text',None,''],'x':[1.,2,np.nan,4,5],'y':[2.,4,6,np.nan,10]})
    assert excel('AVERAGE',df,values={'column':'mixed'})['value']==2
    assert excel('AVERAGEA',df,values={'column':'mixed'})['value']==.75
    assert excel('COUNT',df,values={'column':'mixed'})['value']==1
    assert excel('COUNTA',df,values={'column':'mixed'})['value']==4
    assert excel('COUNTBLANK',df,values={'column':'mixed'})['value']==2
    assert excel('CORREL',df,array1={'column':'x'},array2={'column':'y'})['value']==1
    assert excel('MODE',values=[2,2,3])['function']=='MODE.SNGL'
    assert set(ALIASES.values())<=FUNCTIONS.keys()
    assert excel('COUNTIF',range=['*','a','[x]','**'],criterion='~*')['value']==1
    assert excel('COUNTIF',range=['[x]','x'],criterion='[x]')['value']==1


def test_evidence_scalar_inputs_preserve_provenance():
    evidence=[{'id':'E01','tool':'calculate_statistics','result':{'mean':3.,'source_type':'dataset'}}]
    result=excel('NORM.DIST',evidence=evidence,x=3,mean={'evidence_id':'E01','field':'mean'},standard_dev=2)
    assert result['value']==.5 and result['source_type']=='dataset'
    assert result['input_evidence_ids']==['E01']
    with pytest.raises(ValueError,match='retained analytical evidence'):
        excel('STANDARDIZE',x={'evidence_id':'E99','field':'mean'},mean=0,standard_dev=1)


@pytest.mark.parametrize('name,parameters',[
    ('PERCENTILE.EXC',{'values':[1,2,3,4],'k':0}),
    ('QUARTILE.INC',{'values':[1,2,3,4],'quart':8}),
    ('MODE.SNGL',{'values':[1,2,3]}),
    ('CORREL',{'array1':[1,1,1],'array2':[2,3,4]}),
    ('NORM.DIST',{'x':0,'mean':0,'standard_dev':0}),
    ('COUNTIFS',{'criteria':[{'range':[1,2],'criterion':1},{'range':[1],'criterion':1}]}),
    ('PROB',{'values':[1,2],'probabilities':[.2,.2],'lower_limit':1}),
    ('CHISQ.TEST',{'actual':[1,2],'expected':[1,0]}),
    ('PERMUT',{'number':1000000,'number_chosen':1000000}),
    ('AVERAGE',{'values':{'column':'../private.csv'}}),
    ('eval',{'values':[1,2,3]}),
])
def test_undefined_and_unsafe_inputs_are_controlled(name,parameters):
    with pytest.raises(ValueError):excel(name,**parameters)


def test_output_rows_are_bounded_and_full_input_is_used():
    df=pd.DataFrame({'x':list(range(1000))})
    result=excel('TREND',df,known_y={'column':'x'})
    assert result['total_rows']==1000 and result['row_count']==200 and result['truncated']
    assert excel('AVERAGE',df,values={'column':'x'})['value']==499.5


def test_empty_frequency_ranges_and_beta_domain():
    assert [row['value'] for row in excel('FREQUENCY',values=[],bins=[2,4])['rows']]==[0,0,0]
    assert [row['value'] for row in excel('FREQUENCY',values=[1,2,3],bins=[])['rows']]==[3]
    with pytest.raises(ValueError,match='Beta x'):
        excel('BETA.DIST',x=2,alpha=2,beta=2)

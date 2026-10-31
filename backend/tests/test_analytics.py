import io
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from backend.tools.data_loader import load_dataset
from backend.tools.profiler import profile_dataset
from backend.tools.sql_engine import execute_sql, validate_sql
from backend.tools.statistics import calculate_statistics
from backend.tools.charts import generate_chart
from backend.tools.verifier import verify_finding
from backend.agent.schemas import ToolArgs

ROOT=Path(__file__).resolve().parents[2]


@pytest.fixture
def df():
    return pd.DataFrame({'Region':['West','East','West'],'Revenue':[100.,200.,50.],'Missing':[1.,np.nan,2.]})


def test_csv_profile(df):
    loaded=load_dataset(df.to_csv(index=False).encode(),'sales.csv')
    p=profile_dataset(loaded)
    assert p['rows']==3 and p['missing']==1 and p['dimensions']==['Region']
    assert p['metrics']==['Revenue','Missing']


def test_excel(df):
    buffer=io.BytesIO();df.to_excel(buffer,index=False)
    assert len(load_dataset(buffer.getvalue(),'sales.xlsx'))==3


@pytest.mark.parametrize('content,name',[(b'', 'x.csv'),(b'not a spreadsheet','x.xlsx'),(b'a\n1','x.py'),(b'a,b\n1,2,3\n4,5,6,7','x.csv'),(b'a\x00b','x.csv')])
def test_invalid_files(content,name):
    with pytest.raises(ValueError): load_dataset(content,name)


@pytest.mark.parametrize('sql',[
    'DROP TABLE dataset','SELECT * FROM dataset; SELECT 1','COPY dataset TO \'secret.csv\'',
    "SELECT * FROM read_csv_auto('C:/secret.csv')", "SELECT read_text('C:/secret')",'SELECT * FROM information_schema.tables',
    "SELECT * FROM glob('*')",'INSTALL httpfs',"ATTACH 'file.db' AS x",'SELECT * FROM range(100000000000)',
    'SELECT * INTO other FROM dataset',"WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT * FROM x) SELECT * FROM x",
    "SELECT getenv('GEMINI_API_KEY')",'SELECT * FROM main.dataset','SELECT * FROM duckdb_settings()'])
def test_readonly(sql):
    with pytest.raises(Exception): validate_sql(sql)


def test_aggregation(df):
    r=execute_sql(df,'SELECT Region, SUM(Revenue) AS total FROM dataset GROUP BY Region ORDER BY total')
    assert r['rows']==[{'Region':'West','total':150.},{'Region':'East','total':200.}]
    assert execute_sql(df,'WITH x AS (SELECT SUM(Revenue) AS v FROM dataset) SELECT v FROM x')['rows'][0]['v']==350


def test_row_bound(df):
    result=execute_sql(pd.DataFrame({'x':range(500)}),'SELECT * FROM dataset ORDER BY x')
    assert len(result['rows'])==200 and result['truncated']


@pytest.mark.parametrize('condition,expected',[
    ("Region = 'West' AND Revenue > 60",100.),
    ("Region = 'East' OR Revenue < 60",250.),
])
def test_boolean_filters_are_valid_analytical_sql(df,condition,expected):
    result=execute_sql(df,f'SELECT SUM(Revenue) AS total FROM dataset WHERE {condition}')
    assert result['rows']==[{'total':expected}]


def test_percentages(df):
    r=calculate_statistics(df,ToolArgs(operation='percentage_change',before=200,after=150))
    assert r['percentage_change']==-25
    with pytest.raises(ValueError): calculate_statistics(df,ToolArgs(operation='percentage_change',before=0,after=1))


def test_stats_validation(df):
    with pytest.raises(ValueError): calculate_statistics(df,ToolArgs(operation='summary',column='Region'))
    assert calculate_statistics(df,ToolArgs(operation='summary',column='Revenue'))['mean']==pytest.approx(350/3)
    assert calculate_statistics(df,ToolArgs(operation='outliers',column='Revenue'))['count']==0


def test_chart_and_verification(df):
    result=execute_sql(df,'SELECT Region, SUM(Revenue) AS total FROM dataset GROUP BY Region ORDER BY total')
    chart=generate_chart(result,ToolArgs(evidence_id='E01',chart_type='bar',x='Region',y='total'))
    assert chart['data'][0]['y']==[150,200] and chart['evidence_id']=='E01'
    evidence=[{'id':'E01','tool':'execute_sql','result':result}]
    args=ToolArgs(evidence_id='E01',row=0,field='total',expected=150,claim='West total')
    assert verify_finding(df,evidence,args,execute_sql)['status']=='verified'
    args.expected=151
    assert verify_finding(df,evidence,args,execute_sql)['status']=='inconclusive'
    args.evidence_id='invented'
    with pytest.raises(ValueError): verify_finding(df,evidence,args,execute_sql)


def test_retail_ground_truth():
    expected=json.loads((ROOT/'demo/expected_findings.json').read_text())
    frame=load_dataset((ROOT/'demo/retail_sales.csv').read_bytes(),'sales.csv')
    r=execute_sql(frame,"SELECT date_trunc('month',\"Date\") AS period,SUM(\"Revenue\") AS total FROM dataset GROUP BY 1 ORDER BY 1")
    jan,feb=[row['total'] for row in r['rows'][:2]]
    assert (feb-jan)/jan*100==pytest.approx(expected['february_pct_change'])
    assert feb-jan==pytest.approx(expected['february_delta'])


def test_unterminated_sql_string_is_a_validation_error(df):
    with pytest.raises(ValueError,match='Invalid DuckDB SELECT syntax'):
        execute_sql(df,"SELECT Revenue FROM dataset WHERE Region='West")

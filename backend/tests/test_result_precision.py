import json
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app
from backend.tools.profiler import profile_dataset,records
from backend.tools.sql_engine import execute_sql


def test_tiny_and_high_precision_values_survive_all_result_layers():
    values=[1e-12,1e-16,1e-30,1.2345678901234567]
    frame=pd.DataFrame({'value':values})
    assert [r['value'] for r in records(frame)]==values
    result=execute_sql(frame,'SELECT value FROM dataset ORDER BY value')
    assert [r['value'] for r in result['rows']]==sorted(values)
    assert profile_dataset(frame)['columns'][0]['summary']['min']==1e-30


def test_records_handle_nullable_nested_and_temporal_values():
    frame=pd.DataFrame({'date':[pd.Timestamp('2026-02-01'),pd.NaT],
                        'value':pd.Series([1,pd.NA],dtype='Int64'),
                        'nested':[{'a':np.float64(1e-12)},None]})
    rows=records(frame)
    assert rows[0]['date']=='2026-02-01T00:00:00.000'
    assert rows[1]['date'] is None and rows[1]['value'] is None
    assert rows[0]['nested']['a']==1e-12
    json.dumps(rows,allow_nan=False)


def test_multipart_preview_preserves_tiny_values_in_http_response():
    with TestClient(app) as client:
        response=client.post('/api/datasets',files={'file':('precision.csv',b'value\n0.000000000001\n1.2345678901234567\n','text/csv')})
        assert response.status_code==200
        assert response.json()['profile']['preview'][0]['value']==1e-12

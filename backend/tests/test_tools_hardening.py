import io
import json
import pandas as pd
import pytest

from backend.agent.schemas import ToolArgs
from backend.tools.data_loader import load_dataset
from backend.tools.profiler import profile_dataset
from backend.tools.sql_engine import execute_sql, validate_sql
from backend.tools.statistics import calculate_statistics
from backend.tools.charts import generate_chart
from backend.tools.verifier import verify_finding


@pytest.mark.parametrize('header', ['amount,amount', 'amount, Amount ', ',amount'])
def test_csv_source_headers_are_validated_before_pandas_renames_them(header):
    with pytest.raises(ValueError, match='Column names'):
        load_dataset((header + '\n1,2\n').encode(), 'upload.csv')


def test_excel_duplicate_header_is_rejected():
    data = io.BytesIO()
    pd.DataFrame([['Revenue', 'Revenue'], [1, 2]]).to_excel(data, index=False, header=False)
    with pytest.raises(ValueError, match='Column names'):
        load_dataset(data.getvalue(), 'upload.xlsx')


@pytest.mark.parametrize('csv', ['a,b\n1,2,3\n', 'a,b\n1\n'])
def test_ragged_csv_is_not_silently_reindexed_or_padded(csv):
    with pytest.raises(ValueError, match='fields'):
        load_dataset(csv.encode(), 'upload.csv')


def test_quoted_csv_newlines_and_bom_remain_supported():
    frame = load_dataset('\ufeffname,amount\n"a\nb",1\n"c,d",2\n'.encode(), 'upload.csv')
    assert frame.name.tolist() == ['a\nb', 'c,d']
    assert frame.amount.sum() == 3


@pytest.mark.parametrize('value', ['inf', '-inf', 'Infinity'])
def test_infinite_input_is_rejected_instead_of_reporting_it_as_complete(value):
    with pytest.raises(ValueError, match='infinite'):
        load_dataset(f'Revenue\n{value}\n1\n'.encode(), 'upload.csv')


def test_all_missing_date_profile_has_json_null_coverage():
    frame = pd.DataFrame({'date': pd.Series([pd.NaT], dtype='datetime64[ns]')})
    result = profile_dataset(frame)
    assert result['columns'][0]['coverage'] == {'min': None, 'max': None, 'distinct_dates': 0}
    json.dumps(result, allow_nan=False)


def test_statistics_exclude_nonfinite_inputs_consistently():
    frame = pd.DataFrame({'metric': [1., 2., 3., float('inf')], 'group': ['A', 'A', 'A', 'A']})
    result = calculate_statistics(frame, ToolArgs(operation='group_comparison', column='metric', group_by='group'))
    assert result['rows'][0]['sum'] == 6 and result['rows'][0]['count'] == 3
    assert calculate_statistics(frame, ToolArgs(operation='outliers', column='metric'))['count'] == 0
    with pytest.raises(ValueError, match='overflows'):
        calculate_statistics(frame, ToolArgs(operation='percentage_change', before=1e-308, after=1e308))


def test_group_name_cannot_collide_with_summary_columns():
    frame = pd.DataFrame({'mean': ['A', 'A'], 'value': [1, 3]})
    result = calculate_statistics(frame, ToolArgs(operation='group_comparison', column='value', group_by='mean'))
    assert result['group_column'] == 'mean_group'
    assert result['rows'][0]['mean_group'] == 'A' and result['rows'][0]['mean'] == 2


def test_heatmap_uses_actual_correlation_and_preserves_undefined_values():
    rows = [{'x': 1, 'y': 3, 'constant': 8}, {'x': 2, 'y': 2, 'constant': 8}, {'x': 3, 'y': 1, 'constant': 8}]
    chart = generate_chart({'rows': rows}, ToolArgs(evidence_id='E01', chart_type='heatmap'))
    assert chart['data'][0]['z'][0][1] == pytest.approx(-1)
    assert chart['data'][0]['z'][0][2] is None
    assert chart['data'][0]['z'][2][2] is None
    assert chart['evidence_id'] == 'E01'
    json.dumps(chart, allow_nan=False)


@pytest.mark.parametrize('bad', [float('inf'), float('nan'), True, 'text'])
def test_chart_rejects_invalid_numeric_values(bad):
    with pytest.raises(ValueError):
        generate_chart({'rows': [{'label': 'A', 'value': bad}]}, ToolArgs(chart_type='bar', x='label', y='value'))


def test_heatmap_rejects_insufficient_numeric_observations():
    with pytest.raises(ValueError, match='three'):
        generate_chart({'rows': [{'x': 1, 'y': 1}, {'x': 2, 'y': 2}]}, ToolArgs(chart_type='heatmap'))


def test_verification_matches_group_identity_when_query_order_changes():
    original = {'sql': 'SELECT label, amount FROM dataset', 'rows': [{'label': 'A', 'amount': 10}, {'label': 'B', 'amount': 20}]}
    evidence = [{'id': 'E01', 'tool': 'execute_sql', 'result': original}]
    def rerun(*_): return {**original, 'rows': list(reversed(original['rows']))}
    result = verify_finding(None, evidence, ToolArgs(evidence_id='E01', row=0, field='amount', expected=10, claim='A amount'), rerun)
    assert result['status'] == 'verified' and result['matched_row'] == 1


def test_verification_does_not_choose_between_ambiguous_unlabelled_rows():
    original = {'sql': 'SELECT amount FROM dataset', 'rows': [{'amount': 10}, {'amount': 20}]}
    evidence = [{'id': 'E01', 'tool': 'execute_sql', 'result': original}]
    result = verify_finding(None, evidence, ToolArgs(evidence_id='E01', row=0, field='amount', expected=10, claim='Amount'), lambda *_: original)
    assert result['status'] == 'inconclusive' and result['actual'] is None


def test_readonly_restrictions_also_cover_nested_external_reads_and_functions():
    for sql in ["WITH x AS (SELECT * FROM read_json('https://example.com')) SELECT * FROM x", "SELECT * FROM query('SELECT 1')", "SELECT current_setting('home_directory')", "SELECT repeat('a',1000000)"]:
        with pytest.raises(ValueError):
            validate_sql(sql)
    frame = pd.DataFrame({'value': [1, 2, 3]})
    assert execute_sql(frame, 'SELECT SUM(value) AS total FROM dataset')['rows'] == [{'total': 6}]

"""Evidence-grounded reports. Model prose is interpretation, never a numerical source."""
import math
import re


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def resolve_measurement(state, item):
    source = next((e for e in state['evidence'] if e['id'] == item['evidence_id']), None)
    if not source or source['tool'] not in {'execute_sql', 'calculate_statistics'}:
        raise ValueError('Measurement must reference analytical evidence.')
    result = source['result']
    if 'before' in result and 'after' in result:
        raise ValueError('Supplied percentage inputs are not dataset-backed evidence.')
    if result.get('source_type','dataset')!='dataset':
        raise ValueError('Supplied-parameter calculations and simulations are not dataset-backed evidence.')
    row_index = item.get('row')
    if row_index is None:
        if source['tool'] != 'calculate_statistics':
            raise ValueError('SQL measurements require a row index.')
        row = result
    else:
        rows = result.get('rows', [])
        if not isinstance(row_index, int) or row_index < 0 or row_index >= len(rows):
            raise ValueError('Measurement row is unavailable.')
        row = rows[row_index]
    actual = row.get(item['field'])
    expected = item.get('value')
    if not numeric(actual) or not numeric(expected) or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError('Reported value does not match the evidence cell.')
    verified = any(e['tool'] == 'verify_finding' and e['result'].get('status') == 'verified'
                   and e['result'].get('evidence_id') == source['id']
                   and e['result'].get('row') == row_index and e['result'].get('field') == item['field']
                   for e in state['evidence'])
    context = {k: v for k, v in row.items() if isinstance(v, str) and len(v) <= 160}
    return {**item, 'value': actual, 'context': context, 'verification': 'verified' if verified else 'computed'}


def finalize_report(state, draft):
    known = {e['id']: e for e in state['evidence']}
    findings, warnings = [], []
    for item in draft['findings']:
        refs = list(dict.fromkeys(r for r in item['evidence_ids'] if r in known))
        measurements = []
        for measure in item.get('measurements', []):
            try:
                resolved = resolve_measurement(state, measure)
                measurements.append(resolved)
                if resolved['evidence_id'] not in refs:
                    refs.append(resolved['evidence_id'])
            except (ValueError, KeyError, TypeError):
                warnings.append('A proposed numerical measurement was omitted because it did not match analytical evidence.')
        claim = item['claim']
        if re.search(r'\d', claim):
            claim = 'Computed measurements from the cited evidence.' if measurements else 'Numerical interpretation withheld: no validated measurement was supplied.'
            warnings.append('Numerical prose was replaced with source-derived measurements.')
        analytical = any(known[r]['tool'] in {'execute_sql','calculate_statistics'}
                         and not ('before' in known[r]['result'] and 'after' in known[r]['result'])
                         and known[r]['result'].get('source_type','dataset')=='dataset' for r in refs)
        kind = item['kind'] if analytical else 'inconclusive'
        if (item.get('measurements') and not measurements) or claim.startswith('Numerical interpretation withheld'):
            kind = 'inconclusive'
        findings.append({'claim': claim, 'kind': kind, 'evidence_ids': refs, 'measurements': measurements,
                         'status': 'evidence-linked' if analytical and kind != 'inconclusive' else 'inconclusive'})
    summary = draft['summary']
    if re.search(r'\d', summary):
        summary = 'Review the computed findings below for numerical results. Interpretations remain descriptive and should be checked against their sources.'
        warnings.append('Numerical summary prose was withheld; exact values are shown in the computed findings.')
    verified = [e for e in state['evidence'] if e['tool'] == 'verify_finding' and e['result'].get('status') == 'verified']
    limitations = list(dict.fromkeys([s for s in draft['limitations'] if not re.search(r'\d',s)] + [
        'Contributing segments are descriptive evidence, not proven causes.',
        'Report numbers come from exact referenced cells. Evidence links do not independently validate narrative interpretation.',
        'Recomputation checks query consistency, not source-data truth or correctness of metric definitions.',
        'Sessions expire after two hours of inactivity and disappear on restart.']))
    if state['mode'] == 'offline':
        limitations.insert(0, 'Offline analytics demo: deterministic rules, no autonomous LLM or image understanding.')
    if state.get('image_id') and not state.get('image_context'):
        limitations.append('The attached chart was not interpreted; no visual context influenced this report.')
    if state.get('stop_reason') not in {None, 'sufficient_evidence', 'offline_complete'}:
        limitations.append('Investigation stopped early: ' + state['stop_reason'].replace('_', ' ') + '. Further analysis may be needed.')
    if any(e['result'].get('truncated') for e in state['evidence'] if isinstance(e['result'], dict)):
        limitations.append('Some evidence was truncated; charts use only the retained result rows.')
    if any(e['result'].get('source_type') in {'simulation','parameters'} for e in state['evidence']):
        limitations.append('Simulations and calculations using only supplied parameters are retained as tool outputs, not findings about the uploaded dataset.')
    if any(e['tool']=='calculate_statistics' and (e['result'].get('operation')=='forecast' or e['result'].get('function','').startswith('FORECAST.ETS')) for e in state['evidence']):
        limitations.append('ETS uses additive Holt-Winters fitting and bootstrap intervals; Excel optimization, seasonality selection and forecast intervals can differ.')
    state['findings'] = findings
    state['report'] = {**draft, 'summary': summary, 'findings': findings, 'limitations': limitations,
                       'next_steps':[s for s in draft['next_steps'] if not re.search(r'\d',s)],
                       'warnings': list(dict.fromkeys(warnings)), 'verified_cells': len(verified),
                       'generation': draft.get('generation', 'model')}

from io import BytesIO
import asyncio
from copy import deepcopy
import time
import pytest
from pypdf import PdfReader
from fastapi.testclient import TestClient
import backend.main as main
from backend.agent.schemas import ToolArgs
from backend.services import sessions
from backend.services.pdf_report import pdf_report
from backend.services.reporting import finalize_report
from backend.tools.charts import generate_chart


@pytest.fixture
def state():
    state={'id':'pdf-test','question':'Compare Revenue <b>literally</b> & costs (€ / μ).',
        'mode':'agent','model':'test-model','status':'partial','stop_reason':'user_cancelled',
        'charts':[],'errors':['Investigation stopped by the user.'],'evidence':[
            {'id':'E01','tool':'execute_sql','result':{'sql':'SELECT Revenue FROM dataset','rows':[{'Revenue':1e-12,'Region':'West'}]}}]}
    finalize_report(state,{'summary':'Measured revenue is available.','generation':'computed',
        'findings':[{'kind':'observation','claim':'Revenue from the uploaded data.','evidence_ids':['E01'],
                     'measurements':[{'evidence_id':'E01','row':0,'field':'Revenue','value':1e-12}]}],
        'limitations':['Interpretation needs review.'],'next_steps':['Check the next period.']})
    return state


def read(content):
    reader=PdfReader(BytesIO(content))
    return reader,'\n'.join(page.extract_text() for page in reader.pages)


def test_pdf_preserves_exact_values_provenance_unicode_and_literal_markup(state):
    before=deepcopy(state)
    content=pdf_report(state)
    reader,text=read(content)
    assert content.startswith(b'%PDF-') and len(reader.pages)>=1
    assert '1e-12' in text and 'E01' in text and 'West' in text
    assert '<b>literally</b>' in text and '€' in text and 'μ' in text
    assert 'INCOMPLETE INVESTIGATION' in text and 'user cancelled' in text
    for section in ['Findings','Numerical verification ledger','Limitations and uncertainty','Recommended next steps','Evidence appendix']:
        assert section in text
    assert all(not page.get('/Annots') for page in reader.pages)
    assert state==before


def test_long_content_paginates_and_evidence_previews_are_explicitly_bounded(state):
    state['report']['summary']='Long narrative with <tag> & literal text. '*100
    state['report']['findings']*=6
    state['evidence'][0]['result']['sql']='SELECT '+('VeryLongIdentifier'*250)+' FROM dataset'
    _,text=read(pdf_report(state))
    assert 'Preview shortened for PDF export' in text
    assert text.count('DataDetective AI | Computed evidence')>=3
    assert 'Evidence appendix' in text


def test_all_supported_charts_are_embedded_from_retained_data(state):
    result={'rows':[{'x':1.,'y':2.},{'x':2.,'y':5.},{'x':3.,'y':4.}]}
    for kind in ['line','bar','scatter','histogram','heatmap']:
        state['charts'].append(generate_chart(result,ToolArgs(evidence_id='E01',chart_type=kind,x='x',y='y',title=kind+' chart')))
    reader,text=read(pdf_report(state))
    images=sum(len(page.images) for page in reader.pages)
    assert images==5 and 'could not be rendered' not in text
    assert 'Charts from computed evidence' in text


def test_pdf_endpoint_sets_mime_filename_and_not_ready_errors(state):
    state.update(created=time.time(),accessed=time.time())
    sessions.investigations[state['id']]=state
    try:
        with TestClient(main.app) as client:
            response=client.get('/api/investigations/pdf-test/report')
            assert response.status_code==200 and response.headers['content-type']=='application/pdf'
            assert 'filename="investigation-pdf-test.pdf"' in response.headers['content-disposition']
            assert 'Measured revenue' in read(response.content)[1]
            state['report']=None
            assert client.get('/api/investigations/pdf-test/report').status_code==409
            assert client.get('/api/investigations/missing/report').status_code==404
            schema=client.get('/openapi.json').json()
            assert 'application/pdf' in schema['paths']['/api/investigations/{id}/report']['get']['responses']['200']['content']
    finally:
        sessions.investigations.pop(state['id'],None)


def test_export_capacity_returns_recoverable_error(state,monkeypatch):
    state.update(created=time.time(),accessed=time.time())
    sessions.investigations[state['id']]=state
    monkeypatch.setattr(main,'report_gate',asyncio.Semaphore(0))
    try:
        with TestClient(main.app) as client:
            response=client.get('/api/investigations/pdf-test/report')
            assert response.status_code==429 and 'Retry' in response.json()['detail']
    finally:
        sessions.investigations.pop(state['id'],None)

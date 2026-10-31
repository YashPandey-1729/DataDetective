"""Exercise the installed official SDK request/response path without live credentials."""
import asyncio
import json
import httpx
import pytest
from pydantic import ValidationError
from google import genai
from google.genai import types
from backend.agent.schemas import AgentAction, AgentReport, ImageContext, ToolArgs
from backend.agent.investigator import InvestigationAgent
from backend.tools.vision import inspect_image


def test_official_sdk_structured_action_report_and_vision():
    requests=[]
    def respond(request):
        body=json.loads(request.content); requests.append(body)
        config=body['generationConfig']
        # The legacy responseSchema conversion sends additional_properties to
        # Gemini, which rejects it. Strict models must use the JSON Schema path.
        assert 'responseSchema' not in config
        schema=config['responseJsonSchema']
        assert schema['additionalProperties'] is False
        assert config['responseMimeType']=='application/json'
        has_image=any('inlineData' in part for c in body['contents'] for part in c['parts'])
        if has_image:
            assert schema['title']=='ImageContext'
            payload={'chart_type':'line','axes':['Month','Revenue'],'metrics':['Revenue'],'categories':[],
                'time_periods':['February'],'highlighted_regions':[],'visible_patterns':['A decline is visible.'],
                'matching_columns':['Revenue','Invented'],'ambiguities':['No numeric labels are legible.']}
        elif schema['title']=='AgentReport':
            assert schema['$defs']['ReportFinding']['additionalProperties'] is False
            assert schema['$defs']['Measurement']['additionalProperties'] is False
            # Nested maxItems limits made the live report schema too complex.
            assert 'maxItems' not in schema['properties']['findings']
            assert 'maxItems' not in schema['$defs']['ReportFinding']['properties']['measurements']
            payload={'summary':'Computed evidence is available.','findings':[
                {'claim':'Measured revenue.','kind':'observation','evidence_ids':['E01'],
                 'measurements':[{'evidence_id':'E01','row':0,'field':'total','value':10}]}],
                'limitations':['Descriptive evidence only.'],'next_steps':['Inspect the source records.']}
        else:
            assert schema['title']=='AgentAction'
            assert schema['$defs']['ToolArgs']['additionalProperties'] is False
            assert schema['$defs']['ToolArgs']['properties']['row']['anyOf'][0]['maximum']==199
            payload=AgentAction(tool='execute_sql',explanation='Compare totals.',args=ToolArgs(sql='SELECT SUM(Revenue) AS total FROM dataset')).model_dump()
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':json.dumps(payload)}]},'finishReason':'STOP'}]})
    async def exercise():
        client=genai.Client(api_key='unit-test-placeholder',http_options=types.HttpOptions(async_client_args={'transport':httpx.MockTransport(respond)}))
        agent=InvestigationAgent.__new__(InvestigationAgent)
        agent.client=client;agent.model='gemini-flash-latest'
        try:
            action=await agent.generate(AgentAction,{'question':'Compare revenue','observations':[]})
            assert action.tool=='execute_sql'
            report=await agent.generate(AgentReport,{'instruction':'Return the final report.'})
            assert report.findings[0].measurements[0].value==10
            vision=await inspect_image(client,agent.model,b'fake-image-bytes-for-mock',['Revenue','Date'])
            assert vision['matching_columns']==['Revenue']
            assert any('discarded' in s for s in vision['ambiguities'])
        finally:
            await client.aio.aclose()
    asyncio.run(exercise())
    assert len(requests)==3


@pytest.mark.parametrize('nested',[False,True])
def test_oversized_model_reports_are_rejected_after_simplifying_wire_schema(nested):
    finding={'claim':'Measured revenue.','kind':'observation','evidence_ids':['E01'],'measurements':[]}
    if nested:
        finding['measurements']=[{'evidence_id':'E01','row':0,'field':'total','value':10}]*13
    payload={'summary':'Computed evidence.','findings':[finding]*(1 if nested else 21),'limitations':[],'next_steps':[]}
    def respond(request):
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':json.dumps(payload)}]},'finishReason':'STOP'}]})
    async def exercise():
        client=genai.Client(api_key='unit-test-placeholder',http_options=types.HttpOptions(async_client_args={'transport':httpx.MockTransport(respond)}))
        agent=InvestigationAgent.__new__(InvestigationAgent)
        agent.client=client;agent.model='gemini-2.5-flash'
        try:
            with pytest.raises(ValidationError,match='too_long'):
                await agent.generate(AgentReport,{'instruction':'Return a bounded report.'})
        finally:
            await client.aio.aclose()
    asyncio.run(exercise())


@pytest.mark.parametrize('schema',[AgentAction,AgentReport,ImageContext])
def test_structured_responses_still_reject_unexpected_fields(schema):
    def respond(request):
        if schema is AgentAction:
            payload={'tool':'finish','explanation':'Enough evidence.'}
        elif schema is AgentReport:
            payload={'summary':'Computed evidence.','findings':[],'limitations':[],'next_steps':[]}
        else:
            payload={'chart_type':'line','axes':[],'metrics':[],'categories':[],'time_periods':[],
                     'highlighted_regions':[],'visible_patterns':[],'matching_columns':[],'ambiguities':[]}
        payload['unexpected']='Must not bypass server-side validation.'
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':json.dumps(payload)}]},'finishReason':'STOP'}]})
    async def exercise():
        client=genai.Client(api_key='unit-test-placeholder',http_options=types.HttpOptions(async_client_args={'transport':httpx.MockTransport(respond)}))
        agent=InvestigationAgent.__new__(InvestigationAgent)
        agent.client=client;agent.model='gemini-flash-latest'
        try:
            with pytest.raises(ValidationError,match='extra_forbidden'):
                if schema is ImageContext:
                    await inspect_image(client,agent.model,b'fake-image-bytes-for-mock',['Revenue'])
                else:
                    await agent.generate(schema,{'question':'Compare revenue'})
        finally:
            await client.aio.aclose()
    asyncio.run(exercise())

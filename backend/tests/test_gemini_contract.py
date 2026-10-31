"""Exercise the installed official SDK request/response path without live credentials."""
import asyncio
import json
from types import SimpleNamespace
import httpx
from google import genai
from google.genai import types
from backend.agent.schemas import AgentAction, ToolArgs
from backend.agent.investigator import InvestigationAgent
from backend.tools.vision import inspect_image


def test_official_sdk_structured_action_and_vision():
    requests=[]
    def respond(request):
        body=json.loads(request.content); requests.append(body)
        has_image=any('inlineData' in part for c in body['contents'] for part in c['parts'])
        payload=({'chart_type':'line','axes':['Month','Revenue'],'metrics':['Revenue'],'categories':[],
            'time_periods':['February'],'highlighted_regions':[],'visible_patterns':['A decline is visible.'],
            'matching_columns':['Revenue','Invented'],'ambiguities':['No numeric labels are legible.']}
            if has_image else AgentAction(tool='execute_sql',explanation='Compare totals.',args=ToolArgs(sql='SELECT SUM(Revenue) AS total FROM dataset')).model_dump())
        return httpx.Response(200,json={'candidates':[{'content':{'role':'model','parts':[{'text':json.dumps(payload)}]},'finishReason':'STOP'}]})
    async def exercise():
        client=genai.Client(api_key='unit-test-placeholder',http_options=types.HttpOptions(async_client_args={'transport':httpx.MockTransport(respond)}))
        agent=InvestigationAgent.__new__(InvestigationAgent)
        agent.client=client;agent.model='gemini-flash-latest'
        try:
            action=await agent.generate(AgentAction,{'question':'Compare revenue','observations':[]})
            assert action.tool=='execute_sql'
            vision=await inspect_image(client,agent.model,b'fake-image-bytes-for-mock',['Revenue','Date'])
            assert vision['matching_columns']==['Revenue']
            assert any('discarded' in s for s in vision['ambiguities'])
        finally:
            await client.aio.aclose()
    asyncio.run(exercise())
    assert len(requests)==2
    assert requests[0]['generationConfig']['responseMimeType']=='application/json'
    assert requests[0]['generationConfig'].get('responseSchema') or requests[0]['generationConfig'].get('responseJsonSchema')

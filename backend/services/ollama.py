"""Local-only Ollama transport; never falls back to a cloud provider."""
import asyncio
import base64
import json
import os
import re
from urllib.parse import urlsplit
import httpx
from backend.services.models import local_model_name
from backend.agent.schemas import AgentAction
from backend.agent.tool_contracts import local_action_json_schema, validate_tool_arguments


def settings():
    url = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
    parsed = urlsplit(url)
    if (parsed.scheme not in {'http','https'} or parsed.hostname not in {'127.0.0.1','localhost','::1'}
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('OLLAMA_BASE_URL must be a loopback HTTP address, such as http://127.0.0.1:11434.')
    model = local_model_name()
    if not re.fullmatch(r'gemma4:[A-Za-z0-9_.-]+', model) or 'cloud' in model.lower():
        raise ValueError('OLLAMA_MODEL must be a local gemma4 tag; cloud models are not supported.')
    try:
        context = int(os.getenv('OLLAMA_CONTEXT_LENGTH','8192'))
        timeout = float(os.getenv('OLLAMA_TIMEOUT_SECONDS','180'))
    except ValueError:
        raise ValueError('Ollama context length and timeout must be numeric.')
    if not 2048 <= context <= 16384 or not 10 <= timeout <= 600:
        raise ValueError('Use an Ollama context length of 2048–16384 and timeout of 10–600 seconds.')
    return {'url':url,'model':model,'context':context,'timeout':timeout}


def status():
    try:
        config = settings()
        with httpx.Client(base_url=config['url'],timeout=1.5,trust_env=False,follow_redirects=False) as client:
            response = client.get('/api/tags')
            response.raise_for_status()
            result = response.json()
            if not isinstance(result,dict) or not isinstance(result.get('models'),list):
                raise ValueError('Invalid Ollama model list')
            models = result['models']
        installed = any(item.get('name',item.get('model')) == config['model'] for item in models if isinstance(item,dict))
        return {'ready':installed,'running':True,'model':config['model'],
                'message':None if installed else f"Download the local model with: ollama pull {config['model']}"}
    except ValueError as exc:
        return {'ready':False,'running':False,'message':str(exc) if str(exc).startswith(('OLLAMA_','Use an Ollama','Ollama context')) else 'Ollama returned an invalid status response.'}
    except httpx.HTTPError:
        return {'ready':False,'running':False,'message':'Start Ollama locally, then download Gemma with: ollama pull '+local_model_name()}


def create_client():
    config = settings()
    return httpx.AsyncClient(base_url=config['url'],timeout=httpx.Timeout(config['timeout'],connect=3),
                             trust_env=False,follow_redirects=False)


async def generate_structured(client, *, model, schema, contents, system_instruction, images=None, action_constraints=None):
    config = settings()
    tag = model.removeprefix('ollama:')
    if tag != config['model']:
        raise ValueError('The selected local model no longer matches the Ollama configuration. Reconnect and retry.')
    output_schema = local_action_json_schema(action_constraints) if schema is AgentAction else schema.model_json_schema()
    system = system_instruction + '\nReturn one JSON object matching this schema: ' + json.dumps(output_schema,separators=(',',':'))
    if len(system) + len(contents) > 2 * config['context']:
        raise ValueError('This investigation exceeds the local model context budget. Ask a more focused question or use fewer columns.')
    message = {'role':'user','content':contents}
    if images:
        message['images'] = [base64.b64encode(data).decode('ascii') for data in images]
    payload = {'model':tag,'messages':[{'role':'system','content':system},message],
               'format':output_schema,'stream':False,'think':False,'keep_alive':'5m',
               'options':{'temperature':0,'num_ctx':config['context'],'num_predict':2048}}
    try:
        response = await asyncio.wait_for(client.post('/api/chat',json=payload),timeout=config['timeout'])
        response.raise_for_status()
        result = response.json()
    except (httpx.TimeoutException,TimeoutError):
        raise ValueError('Local Gemma timed out. Allow time for model loading, or use a smaller model/context.') from None
    except httpx.HTTPStatusError as exc:
        message = 'Local Gemma is not installed. Run: ollama pull '+tag if exc.response.status_code==404 else 'Ollama could not complete the local request. Check its model and memory status.'
        raise ValueError(message) from None
    except httpx.HTTPError:
        raise ValueError('Cannot reach local Ollama. Start Ollama and reconnect.') from None
    except ValueError:
        raise ValueError('Ollama returned an invalid response.') from None
    if (not isinstance(result,dict) or result.get('done') is not True or result.get('done_reason')=='length'
            or 'cloud' in str(result.get('model','')).lower()):
        raise ValueError('Local Gemma returned an incomplete or unexpected response.')
    message = result.get('message')
    content = message.get('content') if isinstance(message,dict) else None
    if not isinstance(content,str):
        raise ValueError('Local Gemma did not return structured text.')
    try:
        parsed = schema.model_validate_json(content)
    except ValueError:
        raise ValueError('Local Gemma returned invalid structured output. Retry or use a more capable model.') from None
    return validate_tool_arguments(parsed) if schema is AgentAction else parsed

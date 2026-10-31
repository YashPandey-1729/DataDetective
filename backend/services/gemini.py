"""Bounded cloud Gemini requests, with provider-directed quota pauses."""
import asyncio
import math
import re
from google.genai.errors import APIError
from google.genai import types
from backend.agent.schemas import gemini_json_schema


def retry_delay(error):
    if error.code != 429 or not isinstance(error.details, dict):
        return None
    details = error.details.get('error', error.details)
    if not isinstance(details, dict):
        return None
    items = details.get('details', [])
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict) or item.get('@type') != 'type.googleapis.com/google.rpc.RetryInfo':
            continue
        match = re.fullmatch(r'(\d+(?:\.\d+)?)s', str(item.get('retryDelay', '')))
        if match:
            seconds = float(match[1])
            if 0 <= seconds <= 60:
                return min(60, math.ceil(seconds) + 1)  # Allow a small quota-reset margin.
    return None


async def generate_content(client, *, model, contents, config, on_retry=None):
    for attempt in range(3):
        try:
            return await asyncio.wait_for(client.aio.models.generate_content(
                model=model, contents=contents, config=config), timeout=50)
        except APIError as exc:
            delay = retry_delay(exc)
            if delay is None or attempt == 2:
                raise
            if on_retry:
                on_retry(delay)
            await asyncio.sleep(delay)


async def generate_structured(client, *, model, schema, contents, system_instruction, temperature=0, on_retry=None):
    response = await generate_content(client,model=model,contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction,response_mime_type='application/json',
            response_json_schema=gemini_json_schema(schema),temperature=temperature),on_retry=on_retry)
    return schema.model_validate_json(response.text)

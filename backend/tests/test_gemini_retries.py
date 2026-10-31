import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from google.genai.errors import ClientError
from backend.services.gemini import generate_content


def rate_limit(delay='1.2s'):
    return ClientError(429, {'error': {'message': 'Rate limited.', 'details': [
        {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': delay}]}})


def client_for(side_effect):
    request = AsyncMock(side_effect=side_effect)
    return SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=request))), request


def test_rate_limit_uses_provider_delay_and_then_returns_result(monkeypatch):
    client, request = client_for([rate_limit(), 'result'])
    sleep = AsyncMock(); monkeypatch.setattr('backend.services.gemini.asyncio.sleep', sleep)
    notices = []
    result = asyncio.run(generate_content(client, model='test', contents='test', config={}, on_retry=notices.append))
    assert result == 'result' and request.await_count == 2
    sleep.assert_awaited_once_with(3)
    assert notices == [3]


def test_rate_limit_retries_are_bounded(monkeypatch):
    client, request = client_for(rate_limit())
    sleep = AsyncMock(); monkeypatch.setattr('backend.services.gemini.asyncio.sleep', sleep)
    with pytest.raises(ClientError):
        asyncio.run(generate_content(client, model='test', contents='test', config={}))
    assert request.await_count == 3 and sleep.await_count == 2


@pytest.mark.parametrize('error', [
    ClientError(400, {'error': {'message': 'Invalid schema.'}}),
    ClientError(429, {'error': {'message': 'Quota exhausted without a retry delay.'}}),
    rate_limit('3600s'),
])
def test_permanent_or_long_quota_failures_are_not_retried(monkeypatch, error):
    client, request = client_for(error)
    sleep = AsyncMock(); monkeypatch.setattr('backend.services.gemini.asyncio.sleep', sleep)
    with pytest.raises(ClientError):
        asyncio.run(generate_content(client, model='test', contents='test', config={}))
    assert request.await_count == 1
    sleep.assert_not_awaited()


def test_cancellation_during_quota_wait_stops_the_request(monkeypatch):
    client, request = client_for(rate_limit())
    monkeypatch.setattr('backend.services.gemini.asyncio.sleep', AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(generate_content(client, model='test', contents='test', config={}))
    assert request.await_count == 1

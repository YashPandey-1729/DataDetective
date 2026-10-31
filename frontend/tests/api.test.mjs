import test, {afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {api, ApiError, upload} from '../src/api.ts';
import {validateUpload} from '../src/uploadValidation.ts';

const originalFetch = globalThis.fetch;
afterEach(() => {globalThis.fetch = originalFetch;});

test('returns a typed expired-session error so polling can stop instead of locking the UI', async () => {
  globalThis.fetch = async () => Response.json({detail:'Investigation not found or expired.'}, {status:404});
  await assert.rejects(api('/investigations/expired'), error => error instanceof ApiError && error.status === 404 && /expired/.test(error.message));
});

test('surfaces FastAPI validation messages instead of an unhelpful generic failure', async () => {
  globalThis.fetch = async () => Response.json({detail:[{msg:'Question is too short'},{msg:'Dataset is required'}]}, {status:422});
  await assert.rejects(api('/investigations'), error => error.status === 422 && error.message === 'Question is too short; Dataset is required');
});

test('a stalled request is aborted within its timeout and becomes a recoverable API error', async () => {
  let requestSignal;
  globalThis.fetch = async (_url, options) => {
    requestSignal = options.signal;
    return new Promise((_resolve,reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted','AbortError')), {once:true}));
  };
  await assert.rejects(api('/health', {}, 15), error => error instanceof ApiError && /did not respond in time/.test(error.message));
  assert.equal(requestSignal.aborted,true);
});

test('caller cancellation remains distinguishable from a backend or timeout failure', async () => {
  const caller = new AbortController();
  globalThis.fetch = async (_url,options) => new Promise((_resolve,reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted','AbortError')), {once:true}));
  const request = api('/investigations/active', {signal:caller.signal});
  caller.abort();
  await assert.rejects(request, error => error.name === 'AbortError');
});

test('non-JSON server failures retain their status and network failures give actionable feedback', async () => {
  globalThis.fetch = async () => new Response('Bad gateway', {status:502});
  await assert.rejects(api('/health'), error => error.status === 502);
  globalThis.fetch = async () => {throw new TypeError('fetch failed');};
  await assert.rejects(api('/health'), error => error.status === 0 && /FastAPI/.test(error.message));
});

test('uploads preserve multipart contents and parse the resulting profile response', async () => {
  const file = new File(['Region,Revenue\nWest,50'], 'retail.csv', {type:'text/csv'});
  globalThis.fetch = async (url,options) => {
    assert.equal(url,'/api/datasets');
    assert.equal(options.method,'POST');
    assert.equal(options.body.get('file').name,'retail.csv');
    assert.equal(await options.body.get('file').text(),'Region,Revenue\nWest,50');
    return Response.json({id:'dataset-id',profile:{rows:1}});
  };
  assert.deepEqual(await upload('/datasets',file),{id:'dataset-id',profile:{rows:1}});
});

test('rejects empty, oversized, and unsupported files before consuming a request slot', () => {
  assert.equal(validateUpload({name:'sales.CSV',size:20}, false),null);
  assert.equal(validateUpload({name:'chart.jpeg',size:50}, true),null);
  assert.match(validateUpload({name:'sales.csv',size:0}, false),/empty/);
  assert.match(validateUpload({name:'sales.exe',size:20}, false),/CSV or Excel/);
  assert.match(validateUpload({name:'chart.svg',size:20}, true),/PNG or JPEG/);
  assert.match(validateUpload({name:'chart.png',size:5*1024*1024+1}, true),/5 MB/);
  assert.match(validateUpload({name:'sales.xlsx',size:15*1024*1024+1}, false),/15 MB/);
});

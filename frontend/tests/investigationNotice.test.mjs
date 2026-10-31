import test from 'node:test';
import assert from 'node:assert/strict';
import {investigationNotice} from '../src/investigationNotice.ts';

test('partial-result notices never appear during active, successful or failed investigations',()=>{
  assert.equal(investigationNotice(null),null);
  for (const status of ['queued','running','completed','failed']) {
    assert.equal(investigationNotice({status,stop_reason:'repeated_action_limit'}),null);
  }
});

test('repeated actions direct users to existing evidence and a revised question',()=>{
  const notice=investigationNotice({status:'partial',stop_reason:'repeated_action_limit'});
  assert.match(notice.reason,/repeated analyses/);
  assert.match(notice.nextStep,/existing evidence/);
  assert.match(notice.nextStep,/narrow your question/);
  assert.doesNotMatch(notice.reason,/resource|step limit|unavailable/i);
});

test('step exhaustion suggests smaller questions rather than more expensive retries',()=>{
  const notice=investigationNotice({status:'partial',stop_reason:'step_budget_exhausted'});
  assert.match(notice.reason,/step limit/);
  assert.match(notice.nextStep,/one focused comparison/);
});

test('tool errors and model failures offer different recovery steps',()=>{
  const tool=investigationNotice({status:'partial',stop_reason:'tool_failure_limit'});
  const model=investigationNotice({status:'partial',stop_reason:'model_unavailable'});
  assert.match(tool.reason,/tool requests failed/);
  assert.match(tool.nextStep,/Execution notices/);
  assert.match(tool.nextStep,/column names/);
  assert.match(model.reason,/model could not continue/);
  assert.match(model.nextStep,/Reconnect/);
  assert.match(model.nextStep,/Offline analytics/);
  assert.doesNotMatch(tool.nextStep,/Reconnect/);
});

test('interrupted investigations suggest checking the backend connection',()=>{
  const notice=investigationNotice({status:'partial',stop_reason:'cancelled'});
  assert.match(notice.reason,/interrupted/);
  assert.match(notice.nextStep,/backend connection/);
});

test('missing or unknown stop reasons use safe generic guidance without displaying raw values',()=>{
  const fallback=investigationNotice({status:'partial'});
  assert.match(fallback.reason,/stopped before completing/);
  assert.match(fallback.nextStep,/report limitations/);
  for (const stop_reason of [null,'','future_reason','__proto__','<script>untrusted</script>']) {
    assert.deepEqual(investigationNotice({status:'partial',stop_reason}),fallback);
  }
});

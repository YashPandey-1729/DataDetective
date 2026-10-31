import test from 'node:test';
import assert from 'node:assert/strict';
import {mergeInvestigationUpdate} from '../src/investigationUpdates.ts';
import {investigationNotice} from '../src/investigationNotice.ts';

test('a delayed poll cannot reactivate a stopped or completed investigation',()=>{
  for (const status of ['partial','cancelled','completed','failed']) {
    const current={id:'one',status,report:{summary:'Retained evidence'}};
    for (const incomingStatus of ['queued','running']) {
      assert.equal(mergeInvestigationUpdate(current,{id:'one',status:incomingStatus}),current);
    }
  }
});

test('old progress responses cannot resurrect a reset or replace another investigation',()=>{
  const incoming={id:'old',status:'running'};
  assert.equal(mergeInvestigationUpdate(null,incoming),null);
  const current={id:'new',status:'queued'};
  assert.equal(mergeInvestigationUpdate(current,incoming),current);
});

test('active polling accepts fresh evidence and terminal cancellation responses',()=>{
  const current={id:'one',status:'running'};
  const progress={id:'one',status:'running',evidence:[{id:'E01'}]};
  assert.equal(mergeInvestigationUpdate(current,progress),progress);
  const stopped={id:'one',status:'partial',stop_reason:'user_cancelled'};
  assert.equal(mergeInvestigationUpdate(progress,stopped),stopped);
});

test('user cancellation is explained without blaming the backend connection',()=>{
  for (const status of ['partial','cancelled']) {
    const notice=investigationNotice({status,stop_reason:'user_cancelled'});
    assert.match(notice.reason,/You stopped/);
    assert.match(notice.nextStep,/evidence is retained/);
    assert.doesNotMatch(notice.nextStep,/backend connection|Reconnect/);
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {parameterDefaults,statisticalRequest,resultSource} from '../src/statistics.ts';

test('literal calculations and simulations are never labeled uploaded observations',()=>{
  assert.equal(resultSource({source_type:'parameters'}),'Calculated from supplied values');
  assert.equal(resultSource({before:100,after:50}),'Calculated from supplied values');
  assert.equal(resultSource({source_type:'simulation'}),'Simulation · not observations');
  assert.equal(resultSource({source_type:'dataset'}),'Computed from uploaded data');
});

test('statistics requests retain exact columns and finite numeric inputs',()=>{
  const definition={operation:'correlation',required_arguments:['column','other_column'],parameters_schema:{}};
  assert.deepEqual(statisticalRequest(definition,{column:'Study hours',other_column:'Score'},'{}'),{operation:'correlation',column:'Study hours',other_column:'Score',parameters:{}});
  assert.throws(()=>statisticalRequest(definition,{column:'Score'},'{}'),/other column/);
  const change={operation:'percentage_change',required_arguments:['before','after'],parameters_schema:{}};
  assert.equal(statisticalRequest(change,{before:'200',after:'150'},'{}').after,150);
  assert.throws(()=>statisticalRequest(change,{before:'Infinity',after:'1'},'{}'),/finite/);
});
test('invalid advanced options never become requests',()=>{
  const def={operation:'summary',parameters_schema:{}};
  for(const json of ['[]','null','bad','1']) assert.throws(()=>statisticalRequest(def,{},json));
});
test('schema defaults seed calculations without inventing measurements',()=>{
  const def={operation:'regression',parameters_schema:{required:['predictors'],properties:{intercept:{default:true},confidence:{default:.95}}}};
  assert.deepEqual(parameterDefaults(def,['Score','Attendance']),{intercept:true,confidence:.95,predictors:['Attendance']});
  assert.deepEqual(parameterDefaults({operation:'excel',function:'SUM',parameters_schema:{required:['values']}},['Revenue']),{function:'SUM',values:{column:'Revenue'}});
});

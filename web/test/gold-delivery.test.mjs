import test from 'node:test';
import assert from 'node:assert/strict';
import {reconcile,ledgerStats,isStale} from '../public/workbench-math.js';
import {createServer} from '../server.mjs';

test('signed river reconciles including intercept; context has no extra vote',()=>{
  const d={score:.45,intercept_contribution:.3,tree:[{family:'rates',contribution:-.1},{family:'trend',contribution:.25},{family:'trend',contribution:0}]};
  const r=reconcile(d);assert.equal(r.valid,true);assert.equal(r.families.length,2);assert.equal(r.base,.3);
  assert.equal(reconcile({...d,score:.9}).valid,false);assert.equal(reconcile({score:null,tree:[]}).valid,false);
});
test('live metrics separate data gaps, abstentions, tested calls and validated edges',()=>{
  const rows=[{horizon:'D5',score:.5,direction:'Positive',edge:'No Edge',outcome:{status:'evaluated',directional_hit:true}},
    {horizon:'D5',score:0,direction:'Neutral',edge:'No Edge',outcome:{status:'evaluated',directional_hit:false}},
    {horizon:'D5',score:null,direction:null,edge:'No Edge'},
    {horizon:'D1',score:.4,direction:'Positive',edge:'No Edge'}];
  const m=ledgerStats(rows,'D5');assert.equal(m.n,3);assert.equal(m.coverage,.5);assert.equal(m.hitRate,1);assert.equal(m.tested,1);assert.equal(m.edges,0);
  assert.equal(isStale('garbage'),true);assert.equal(isStale('2026-09-22T06:00:00Z',Date.parse('2026-09-22T07:00:00Z')),false);
});
test('local AI gateway blocks cross-origin requests and arbitrary endpoints',async()=>{
  let calls=0;const server=createServer({goldReader:async(command,input)=>{calls++;return {status:'available',command,provider:input?.provider};}});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
  const body={provider:'deepseek',model:'deepseek-chat',language:'zh',api_key:''};
  try{
    assert.equal((await fetch(base+'/api/gold/dashboard')).status,200);
    assert.equal((await fetch(base+'/api/gold/commentary',{method:'POST',headers:{'Content-Type':'application/json',Origin:'https://evil.example'},body:JSON.stringify(body)})).status,403);
    assert.equal((await fetch(base+'/api/gold/commentary',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,provider:'custom'})})).status,400);
    assert.equal((await fetch(base+'/api/gold/commentary',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).status,200);
    assert.equal(calls,2);
  }finally{await new Promise(r=>server.close(r));}
});

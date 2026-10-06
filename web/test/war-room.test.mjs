import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {get} from 'node:http';
import {createServer} from '../server.mjs';
import {demoRoom} from '../public/war-room-demo.js';

test('research room routes bind snapshot and analyst, never accept browser secrets',async()=>{
  const calls=[];
  const server=createServer({warRoomReader:async(command,input)=>{calls.push({command,input});return {status:'available',snapshot_id:input.snapshot_id};}});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
  const id='a'.repeat(64),body={asset:'gold',provider:'deepseek',model:'deepseek-chat',language:'zh',snapshot_id:id};
  const send=(route,extra={})=>fetch(base+route,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,...extra})});
  try{
    assert.equal((await fetch(base+'/api/war-room/gold?language=zh')).status,200);
    assert.equal((await fetch(base+'/api/war-room/gold?language=xx')).status,400);
    assert.equal((await send('/api/war-room/ask',{analyst:'rates',question:'为什么？'})).status,200);
    assert.equal(calls.at(-1).command,'ask');assert.equal(calls.at(-1).input.snapshot_id,id);
    assert.equal((await send('/api/war-room/ask',{analyst:'rates',question:'为什么？',api_key:'never-forward'})).status,400);
    assert.equal((await send('/api/war-room/research',{base_url:'https://evil.example'})).status,400);
    assert.equal((await send('/api/war-room/research',{snapshot_id:'other'})).status,400);
    const privateUrl=base+`/api/war-room/gold/analysts/rates?language=zh&snapshot_id=${id}`;
    assert.equal((await fetch(privateUrl)).status,200);
    assert.equal(calls.at(-1).command,'analyst');
    assert.equal((await fetch(privateUrl,{headers:{Origin:'https://evil.example'}})).status,403);
    // Node 26 fetch normalizes Host; use the HTTP client to actually send rebinding Host.
    const rebinding=await new Promise((resolve,reject)=>{const req=get(privateUrl,{headers:{Host:'evil.example'}},response=>{response.resume();response.on('end',()=>resolve(response.statusCode));});req.on('error',reject);});
    assert.equal(rebinding,403);
    assert.equal(calls.length,3);
  }finally{await new Promise(r=>server.close(r));}
});

test('research UI uses safe DOM rendering and does not expose browser credentials',async()=>{
  const html=await readFile(new URL('../public/war-room.html',import.meta.url),'utf8');
  const js=await readFile(new URL('../public/war-room.js',import.meta.url),'utf8');
  assert.doesNotMatch(html,/id="api-key"/);
  assert.match(html,/id="owner-password" type="password"/);
  assert.match(html,/不是 DeepSeek Key/);
  assert.doesNotMatch(js,/Authorization:|Bearer |\.innerHTML\s*=/);
  assert.match(html,/THE BOARD/);assert.match(html,/THE TEAM/);assert.match(html,/ASK THIS ANALYST/);
  assert.match(js,/session_id|analysts\//);
  assert.ok(html.indexOf('id="top-stories"')<html.indexOf('id="price-chart"'));
  assert.ok(html.indexOf('id="brief"')<html.indexOf('id="board"'));
  assert.match(js,/if\(demo\)throw new Error\('DEMO cannot call research or write ledgers'\)/);
  assert.match(html,/RESEARCH DESK/);
});

test('demo fixtures are visibly synthetic, bilingual and unable to supply real snapshot identities',()=>{
  for(const language of ['zh','en']){
    const room=demoRoom(language);
    assert.equal(room.demo,true);assert.equal(room.snapshot_id,'demo-only');
    assert.equal(room.situation.status,'DEMO / MOCK');
    assert.equal(room.situation.top_stories.length,3);
    assert.deepEqual(room.team.map(m=>m.analyst),['director','liquidity','rates','cross_asset','gold','skeptic']);
    assert.ok(room.team.every(m=>m.report.id.startsWith('demo-')));
    assert.ok(room.all_cards.every(e=>e.evidence_id.startsWith('demo-')&&e.source==='DEMO / synthetic'));
    assert.ok(room.research_run.process.some(p=>p.stage==='supplement'));
  }
});

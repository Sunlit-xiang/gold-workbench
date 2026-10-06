import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createServer} from '../server.mjs';

test('macro API is independent of Codex and browser credentials',async()=>{
  const calls=[];const server=createServer({macroReader:async(command,input)=>{calls.push({command,input});return {asset_id:input.asset,status:'available'};},analyzer:async()=>{throw Error('Not allowed');}});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
  try{
    const view=await fetch(base+'/api/macro/audnzd').then(r=>r.json());assert.equal(view.asset_id,'audnzd');
    const body={asset:'gold',provider:'deepseek',model:'deepseek-chat',language:'zh'};
    const send=extra=>fetch(base+'/api/macro/research',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,...extra})});
    assert.equal((await send({})).status,200);
    assert.equal((await send({api_key:'do-not-accept'})).status,400);
    assert.equal((await send({base_url:'https://evil.example'})).status,400);
    assert.equal((await fetch(base+'/api/macro/research',{method:'POST',headers:{'Content-Type':'application/json',Origin:'https://evil.example'},body:JSON.stringify(body)})).status,403);
    assert.equal((await fetch(base+'/api/macro/unknown')).status,404);
    assert.equal((await fetch(base+'/api/macro/snapshots/'+'a'.repeat(64))).status,200);
    assert.equal(calls.at(-1).input.id,'a'.repeat(64));
    assert.equal((await fetch(base+'/api/assets/audnzd/predictions/'+'a'.repeat(64))).status,404);
    assert.equal(calls.length,3);
  }finally{await new Promise(r=>server.close(r));}
});

test('published pages have no credential form, provider request or unsafe text injection',async()=>{
  for(const file of ['macro.html','asset.html']){
    const text=await readFile(new URL('../public/'+file,import.meta.url),'utf8');assert.doesNotMatch(text,/type="password"|id="api-key"/);
  }
  for(const file of ['macro.js','workbench.js']){
    const text=await readFile(new URL('../public/'+file,import.meta.url),'utf8');assert.doesNotMatch(text,/Authorization:|Bearer |config\.api_key|\.innerHTML\s*=/);
  }
});

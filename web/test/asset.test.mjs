import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from '../server.mjs';

test('asset workbench is independent of Codex and validates routing', async()=>{
  const server=createServer({assetReader:async()=>({asset:{id:'gold'},current:{},ledger:[]}),analyzer:async()=>{throw new Error('must not invoke AI');}});
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base=`http://127.0.0.1:${server.address().port}`;
  try{
    const list=await fetch(base+'/api/assets').then(r=>r.json()); assert.equal(list.assets[0].id,'gold');
    const data=await fetch(base+'/api/assets/gold').then(r=>r.json()); assert.equal(data.asset.id,'gold');
    assert.equal((await fetch(base+'/api/assets/eurusd')).status,404);
    assert.equal((await fetch(base+'/api/assets/gold/predictions/not-a-hash')).status,404);
    assert.equal((await fetch(base+'/api/assets/gold/predictions/'+'a'.repeat(64))).status,200);
    const page=await fetch(base+'/asset.html').then(r=>r.text()); assert.match(page,/GC PROXY/);assert.match(page,/冻结账本/);
    assert.equal((await fetch(base+'/asset.js')).status,200);
  }finally{await new Promise(resolve=>server.close(resolve));}
});

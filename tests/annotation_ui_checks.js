// No POSTs: loading/resuming must never create or change a human judgment.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const {Element}=require('./dom_stub');
const html=fs.readFileSync(path.join(__dirname,'../src/demo/annotation.html'),'utf8');
async function check(stored, expected, unavailable=false, packet='synthetic-packet') {
  const nodes=new Map();
  for(const m of html.matchAll(/<([a-z][a-z0-9]*)\b[^>]*\bid="([^"]+)"[^>]*>/gi))nodes.set(m[2],new Element(m[1]));
  const fields=[...html.matchAll(/<input type="checkbox" value="([^"]+)"/g)].map(m=>{const e=new Element('input');e.value=m[1];return e;});
  const get=id=>{assert.ok(nodes.has(id),'Missing HTML element: '+id);return nodes.get(id);};
  const calls=[],memory=new Map(Object.entries(stored));
  const document={getElementById:get,createElement:t=>new Element(t),createTextNode:t=>({textContent:t}),addEventListener(){},querySelectorAll(s){
    if(s==='#fieldChoices input')return fields;
    if(s==='[data-grade]')return [];
    throw Error('Unexpected selector '+s);
  }};
  const localStorage={getItem(k){if(unavailable)throw Error('Unavailable');return memory.get(k)??null;},setItem(k,v){if(unavailable)throw Error('Unavailable');memory.set(k,v);}};
  const context=vm.createContext({document,localStorage,URL,console,fetch:async(url,options)=>{
    assert.ok(!options?.method || options.method==='GET','A read-only resume submitted a judgment');
    const index=Number(new URL(url,'http://127.0.0.1').searchParams.get('index'));calls.push(index);
    return {ok:true,json:async()=>({index,total:4,graded:1,unknown:1,handled:2,next_unhandled:2,candidate_count:4,packet_sha256:packet,review:{annotator:'synthetic'},queries:[{query_id:'synthetic_q',text:'synthetic',rubric:'synthetic'}],query:{query_id:'synthetic_q',text:'synthetic',rubric:'synthetic'},rules:'synthetic',candidate:{name:'synthetic '+index,category:'synthetic',address:'',description:'synthetic',source_url:'https://example.org/synthetic'},existing:null,field_evidence_ref:'synthetic'})};
  }});
  vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
  for(let i=0;i<6;i++)await new Promise(r=>setImmediate(r));
  assert.equal(vm.runInContext('index',context),expected);
  assert.deepEqual(calls,[0,expected]);
  assert.ok(get('message').textContent.includes('已从D盘载入'));
  assert.ok(!get('message').textContent.includes('初始评分全部为空'));
  if(!unavailable)assert.equal(memory.get('cps5801:pilot-position:'+packet),String(expected));
}
(async()=>{
  await check({},2);
  await check({'cps5801:pilot-position:synthetic-packet':'3'},3);
  await check({'cps5801:pilot-position:synthetic-packet':'99'},2);
  await check({'cps5801:pilot-position:synthetic-packet':'bad'},2);
  await check({'cps5801:pilot-position:old-packet':'3'},2);
  await check({},2,true);
  console.log('Synthetic annotation resume checks passed; no judgments submitted.');
})().catch(e=>{console.error(e);process.exitCode=1;});

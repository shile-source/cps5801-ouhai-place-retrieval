// Synthetic review inputs and in-memory responses; never submits a real judgment.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const {Element}=require('./dom_stub');
const html=fs.readFileSync(path.join(__dirname,'../src/demo/adjudication.html'),'utf8');
const nodes=new Map();
for(const m of html.matchAll(/<([a-z][a-z0-9]*)\b[^>]*\bid="([^"]+)"[^>]*>/gi))nodes.set(m[2],new Element(m[1]));
const grades=[...html.matchAll(/<button data-grade="([^"]+)"/g)].map(m=>{const e=new Element('button');e.dataset.grade=m[1];return e;});
const get=id=>{assert.ok(nodes.has(id));return nodes.get(id);};
const document={getElementById:get,querySelectorAll:s=>{assert.equal(s,'#grades button');return grades;}};
const decisions=new Map(),history=[];let locked=false;
const items=[0,1].map(i=>({case_id:'synthetic_'+i,query:{text:'synthetic query '+i,rubric:'synthetic only'},candidate:{name:'<script>synthetic</script>',description:'synthetic text',source_url:'javascript:synthetic'},original:{first_grade:0,second_grade:1}}));
const context=vm.createContext({document,console,fetch:async(url,opts)=>{
 if(url.startsWith('/api/state')){
  const index=Number(url.split('=')[1]);return {ok:true,json:async()=>({total:2,handled:decisions.size,unknown:[...decisions.values()].filter(v=>v.grade===null).length,index,item:items[index],existing:decisions.get(items[index].case_id),next_unhandled:items.findIndex(x=>!decisions.has(x.case_id))<0?null:items.findIndex(x=>!decisions.has(x.case_id)),locked,request_token:'synthetic_token'})};
 }
 assert.equal(opts.headers['X-Review-Token'],'synthetic_token');
 if(url==='/api/finalize'){assert.equal(decisions.size,2);locked=true;return {ok:true,json:async()=>({locked:true})};}
 assert.equal(url,'/api/decision');const v=JSON.parse(opts.body);
 if(!v.confirmed||!v.reviewer||!v.reason)return {ok:false,json:async()=>({error:'synthetic confirmation required'})};
 const event={...v,saved_at:'synthetic saved time'};decisions.set(v.case_id,event);history.push(event);
 return {ok:true,json:async()=>({saved:true,event})};
}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 await tick();assert.equal(decisions.size,0);assert.ok(get('progress').textContent.includes('0／2'));
 assert.equal(get('place').textContent,'<script>synthetic</script>');assert.ok(get('source').hidden);
 get('reviewer').value='synthetic reviewer';get('reason').value='synthetic evidence';
 await grades[0].fire('click');assert.equal(decisions.size,0);assert.ok(get('message').textContent.includes('未保存'));
 get('confirmed').checked=true;
 await grades[0].fire('click');assert.equal(decisions.size,1);assert.equal(history[0].grade,0);
 assert.equal(get('query').textContent,'synthetic query 1');assert.equal(get('reason').value,'');
 get('reason').value='synthetic missing evidence';await grades[3].fire('click');
 assert.equal(decisions.size,2);assert.equal(history[1].grade,null);assert.ok(!get('finalize').disabled);
 await get('finalize').onclick();assert.ok(locked);assert.ok(grades.every(x=>x.disabled));
 assert.ok(get('message').textContent.includes('已完成并锁定'));
 console.log('Synthetic adjudication UI checks passed: no prefill, confirmation, actual save, unknown, next case, unsafe text and lock.');
})().catch(e=>{console.error(e);process.exitCode=1;});

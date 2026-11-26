// Synthetic DOM and mocked local responses. No browser, model, POI fetch or rating.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../src/demo/index.html'), 'utf8');
const {Element} = require('./dom_stub');
const nodes = new Map();
for(const match of html.matchAll(/<([a-z][a-z0-9]*)\b[^>]*\bid="([^"]+)"[^>]*>/gi)) {
  const el = new Element(match[1]);
  if(/\shidden(?=[\s>])/.test(match[0]))el.hidden=true;
  nodes.set(match[2],el);
}
const examples=[...html.matchAll(/<button data-query="([^"]+)"/g)].map(m=>{const e=new Element('button');e.dataset.query=m[1];return e;});
const get = id => {assert.ok(nodes.has(id),'Missing HTML element: '+id);return nodes.get(id);};
const document = {documentElement:{},title:'',getElementById:get,createElement:t=>new Element(t),createElementNS:(_,t)=>new Element(t),querySelectorAll(selector) {
  if(selector==='[data-t]')return [];
  if(selector==='[data-query]')return examples;
  if(selector==='#keyword,#bm25,#encoder,#both,[data-query]')return [...['keyword','bm25','encoder','both'].map(get),...examples];
  throw Error('Unexpected selector: '+selector);
}};
const pending=[];
const backend={candidate_count:2,corpus_sha256:'synthetic',encoder_state:'not_loaded',encoder_ready:false,encoder_min_c_gib:5,disk_free_gib:{C:20,D:100}};
const context=vm.createContext({document,URL,URLSearchParams,console,fetch:async(url,opts)=>{
  if(url==='/api/status')return {ok:true,json:async()=>backend};
  if(url==='/api/constraints/propose')return {ok:true,json:async()=>({constraints:[{field:'seats',operator:'gte',value:50}],requires_user_confirmation:true})};
  assert.equal(url,'/api/search');
  const request=JSON.parse(opts.body);
  return new Promise(resolve=>pending.push({request,reply(){resolve({ok:true,json:async()=>({query:request.query,method:request.method,results:[],request_id:'synthetic',executed_at:'synthetic test',search_ms:1,load_ms:0,elapsed_ms:2,saved_results_used:false,live_computation:true})});}}));
}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const evaluate = code => vm.runInContext(code,context);
const tick = () => new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await tick();
  assert.equal(document.documentElement.lang,'en');
  assert.equal(get('exploreTitle').textContent,'Find more places in Ouhai');
  get('exploreQuery').value='公园 &city=elsewhere';
  await get('exploreQuery').fire('input');
  assert.equal(new URL(get('exploreAmap').href).searchParams.get('keyword'),'温州市瓯海区 公园 &city=elsewhere');
  get('exploreQuery').value='   ';
  assert.ok((await get('exploreForm').fire('submit')).prevented);
  assert.ok(get('exploreQuery').validityReported);

  context.fixture={poi_id:'synthetic_a',name:'synthetic <place>',address:'old synthetic address',source_url:'https://example.org/synthetic',map_preview:{latitude:27.9,longitude:120.6},navigation:{address:'new synthetic address',address_source_url:'https://example.org/review',has_supplement:true,source_checked_on:'synthetic'}};
  evaluate('selectPlace(fixture)');
  assert.equal(get('routeDestination').value,'new synthetic address');
  assert.equal(get('mapSource').href,'https://example.org/review');
  assert.ok(!get('mapPanel').hidden);
  await get('loadMapPreview').fire('click');
  assert.equal(new URL(get('mapPreview').src).searchParams.get('marker'),'27.9,120.6');
  assert.ok(!get('previewFallback').hidden);
  context.second={poi_id:'synthetic_b',name:'synthetic unlocated place',address:'',source_url:''};
  evaluate('selectPlace(second)');
  assert.ok(get('mapPreview').hidden && get('loadMapPreview').hidden);
  assert.equal(get('mapPreview').getAttribute('src'),null);
  assert.equal(get('routeDestination').value,'温州市瓯海区synthetic unlocated place');
  assert.ok(get('mapSource').hidden);
  get('routeOrigin').value='   ';
  assert.ok((await get('routeForm').fire('submit')).prevented);

  evaluate('inventoryRows=[fixture,second];updatePlaceFilters();updateInventory();');
  assert.ok(!get('placeOverview').hidden);
  assert.equal(get('placeOverview').children.filter(x=>x.tagName==='CIRCLE').length,1);
  assert.equal(get('pointLegend').children.length,1);
  get('placeText').value='unlocated';
  await get('placeText').fire('input');
  assert.ok(get('placeOverview').hidden,'Unknown-CRS record must not acquire a marker');
  assert.ok(get('pointLegend').hidden);
  get('language').value='zh';
  await get('language').fire('change');
  assert.equal(get('exploreTitle').textContent,'查找更多瓯海地点');
  assert.ok(get('mapTitle').textContent.includes('已选目的地'));
  get('language').value='en';await get('language').fire('change');

  get('query').value='synthetic original query';
  const running=get('both').fire('click');
  await tick();
  assert.equal(pending.length,1);
  assert.ok(get('query').readOnly && get('bm25').disabled);
  assert.ok(!get('loadMapPreview').disabled && !get('routeMode').disabled,'Map controls must remain available during search');
  // Simulate a programmatic value change while the first response is pending.
  get('query').value='synthetic changed query';
  pending[0].reply();await tick();
  assert.equal(pending.length,2);
  assert.equal(pending[0].request.query,pending[1].request.query,'Both methods must use one captured query');
  assert.equal(pending[1].request.query,'synthetic original query');
  pending[1].reply();await tick();
  assert.equal(pending.length,3);
  assert.equal(pending[2].request.query,'synthetic original query');
  pending[2].reply();await running;await tick();
  assert.ok(!get('query').readOnly && !get('bm25').disabled);
  pending.splice(0,pending.length);
  backend.bge_available=true;
  backend.explicit_hard_filter_available=true;
  backend.dense_states={encoder:'not_loaded',bge_m3:'not_loaded'};
  await evaluate('status()');
  assert.equal(get('bge_m3').hidden,false);
  assert.equal(get('bge_m3Result').hidden,false);
  assert.equal(evaluate("t('both')"),'Run all four methods');
  get('query').value='synthetic three-method query';
  get('hardSeats').value='40';
  const allRunning=get('both').fire('click');
  await tick();
  for(const method of ['keyword','bm25','encoder','bge_m3']){
    const request=pending.shift();assert.equal(request.request.method,method);
    assert.equal(request.request.query,'synthetic three-method query');
    assert.deepEqual(request.request.constraints,[{field:'seats',operator:'gte',value:40}]);
    get('hardSeats').value='999'; // Captured conditions must survive even programmatic edits.
    request.reply();await tick();
  }
  await allRunning;
  context.filterFixture={query:'synthetic',search_ms:0,load_ms:0,elapsed_ms:0,request_id:'synthetic',executed_at:'synthetic',results:[],hard_filter:{eligible_ids:[],unknown_ids:['synthetic'],unmet_ids:[]}};
  evaluate("render('bm25',filterFixture)");
  const filterText=get('bm25Result').querySelector('.content').children.map(n=>n.textContent).join(' ');
  assert.ok(filterText.includes('Required conditions were applied'));
  assert.ok(!filterText.includes('hard-constraint filtering is not applied'));
  backend.encoder_enabled=false;backend.encoder_state='disabled';backend.dense_states={encoder:'disabled',bge_m3:'disabled'};
  await evaluate('status()');
  assert.ok(get('encoder').disabled&&get('bge_m3').disabled&&get('both').disabled);
  assert.ok(get('status').textContent.includes('BGE-M3 paused'));
  get('query').value='synthetic required seats';
  await get('suggestConditions').fire('click');
  assert.equal(get('hardSeats').value,'50');
  assert.equal(get('hardHoldings').value,'');
  assert.ok(get('constraintProposal').textContent.includes('Review the fields'));
  assert.equal(pending.length,0,'Preparing suggestions must not run a retrieval method');
  console.log('Synthetic UI checks passed: map reset, evidence, external search encoding, filters, language, route validation and shared-query concurrency.');
})().catch(error=>{console.error(error);process.exitCode=1;});

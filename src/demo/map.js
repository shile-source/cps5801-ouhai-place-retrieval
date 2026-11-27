'use strict';
const el=id=>document.getElementById(id);
const text=(tag,value,cls)=>{const n=document.createElement(tag);n.textContent=value;if(cls)n.className=cls;return n;};
let catalog=[],displayed=[],state=null,map=null,markers=null,tiles=null,selectedId=null,latest=null,busy=false;
const pins=new Map();
function initMap(){
  if(typeof L==='undefined'){el('mapUnavailable').hidden=false;return;}
  map=L.map('map',{scrollWheelZoom:false}).setView([27.97,120.62],12);
  markers=L.layerGroup().addTo(map);
  tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',keepBuffer:1,updateWhenIdle:true});
  tiles.on('tileerror',()=>{el('tileStatus').textContent='街道底图暂未加载成功，来源标记和列表仍可用；可关闭底图或从详情打开第三方地图。';});
  tiles.on('tileload',()=>{el('tileStatus').textContent='';});
  if(el('basemap').checked)tiles.addTo(map);
}
function usablePoint(row){const p=row.map_location;return p&&Number.isFinite(p.latitude)&&Number.isFinite(p.longitude)&&p.latitude>=27&&p.latitude<=29&&p.longitude>=119&&p.longitude<=122?p:null;}
function locationLabel(row){const p=usablePoint(row);return !p?'位置待核实，未上图':p.kind==='bounding_box_center'?'区域近似中心，非入口':'来源点位，非核实入口';}
function fit(){if(!map)return;const points=displayed.map(usablePoint).filter(Boolean).map(p=>[p.latitude,p.longitude]);if(points.length)map.fitBounds(points,{padding:[35,35],maxZoom:15});}
function select(row,open=true){selectedId=row.poi_id;document.querySelectorAll('.card').forEach(n=>n.classList.toggle('selected',n.dataset.id===selectedId));const marker=pins.get(selectedId);if(marker){const p=usablePoint(row);map.setView([p.latitude,p.longitude],Math.max(map.getZoom(),14));marker.openTooltip();}if(open)detail(row);}
function detail(row){
  el('detailName').textContent=row.name;el('detailCategory').textContent=row.category;el('detailAddress').textContent='来源地址：'+(row.navigation?.address||row.address||'未知');el('detailDescription').textContent=row.description||'暂无来源描述';el('detailLocation').textContent=locationLabel(row)+'。地点区属、当前运营与设施仍需核实。';
  const links=el('detailLinks');links.replaceChildren();
  const urls=[['原始来源',row.source_url],['在高德地图核对',row.navigation?.search_links?.amap],['在百度地图核对',row.navigation?.search_links?.baidu]];
  for(const [title,url] of urls){try{const parsed=new URL(url);if(!['https:','http:'].includes(parsed.protocol)||parsed.username||parsed.password)continue;const a=text('a',title+' ↗');a.href=parsed.href;a.target='_blank';a.rel='noopener noreferrer';links.append(a);}catch(_){}}
  el('detail').showModal();
}
function render(rows,search=null){
  displayed=rows;latest=search;el('results').replaceChildren();pins.clear();if(markers)markers.clearLayers();
  let placed=0;rows.forEach((row,i)=>{
    const article=document.createElement('article');article.className='card';article.dataset.id=row.poi_id;
    const heading=text('div','','card-top');heading.append(text('span',String(i+1).padStart(2,'0'),'rank'));const title=text('div','');title.append(text('h3',row.name),text('div',row.category||'类别未知','category'));heading.append(title);article.append(heading);
    article.append(text('p',row.description||'暂无来源描述','excerpt'));
    if(search){article.append(text('p',search.method==='bge_m3'||search.method==='encoder'?'AI语义相似度 '+row.score.toFixed(4)+' · 仅表示文本相关性':'词汇匹配：'+(row.matched_tokens?.join('、')||'无词汇命中'),'reason'));}
    const bottom=text('div','','card-bottom');bottom.append(text('span',locationLabel(row)));const button=text('button','查看详情 ↗');button.type='button';button.addEventListener('click',()=>select(row));bottom.append(button);article.append(bottom);el('results').append(article);
    const point=usablePoint(row);if(!point||!map)return;placed++;
    const icon=L.divIcon({className:'source-marker',html:`<div class="pin ${point.kind==='bounding_box_center'?'approx':''}">${i+1}</div>`,iconSize:[29,29],iconAnchor:[14,14]});
    const marker=L.marker([point.latitude,point.longitude],{icon,title:row.name,keyboard:true}).addTo(markers);
    marker.bindTooltip(text('span',row.name+' · '+locationLabel(row)));marker.on('click',()=>select(row));pins.set(row.poi_id,marker);
  });
  el('resultCount').textContent=rows.length+' 条记录 · '+placed+' 个来源位置';el('mapStatus').textContent=`当前${rows.length}条记录中，${placed}条有可展示的OSM来源位置，${rows.length-placed}条未上图。空心虚线标记是区域包围盒中心，不保证在区域内，不能作为入口。`;
  el('resultTitle').textContent=search?'搜索结果':'地点目录';el('viewTitle').textContent=search?'与你的需求相关的来源记录':'浏览来源地点';fit();
  if(!rows.length)el('results').append(text('p','没有找到符合当前条件的记录。可以减少必须条件；未知资料不会被当作满足。','small'));
}
function conditions(){const out=[];if(el('category').value)out.push({field:'category',operator:'eq',value:el('category').value});for(const [id,field] of [['seats','seats'],['books','holdings']])if(el(id).value!=='')out.push({field,operator:'gte',value:Number(el(id).value)});return out;}
async function status(){const r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error('本机搜索服务无法连接');state=await r.json();el('service').textContent=`已连接 · ${state.candidate_count}条来源候选 · ${state.dense_precision==='float16'?'FP16节省内存演示（与原FP32实验分开）':'FP32原精度'} · AI按需加载，首次搜索可能需要较长时间。`;
  for(const option of el('method').options){if(['encoder','bge_m3'].includes(option.value)){option.disabled=!state.encoder_enabled||(option.value==='bge_m3'&&!state.bge_available)||['disabled','stopped'].includes(state.dense_states?.[option.value]);}}
  const option=el('method').selectedOptions[0];if(option.disabled){el('notice').hidden=false;const warning='所选AI模型目前不可用，不会自动重试或改用其他方法。你可以手动选择可用方法。';if(!el('notice').textContent.includes(warning))el('notice').textContent+=' '+warning;}
  el('conditions').hidden=!state.explicit_hard_filter_available;
  el('scopeCount').textContent=state.candidate_count;
  el('search').disabled=busy||option.disabled;
}
async function search(event){event.preventDefault();if(busy)return;const query=el('query').value.trim();if(!query)return;busy=true;const method=el('method').value;el('search').disabled=true;el('query').readOnly=true;el('method').disabled=true;el('notice').hidden=false;el('notice').textContent=['encoder','bge_m3'].includes(method)?'AI正在计算。首次需要载入本地模型，请稍候；失败不会显示伪造或旧结果。':'正在检索来源资料…';
  try{const r=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({method,query,top_k:10,constraints:conditions()})});const result=await r.json();if(!r.ok)throw Error(result.error||'搜索失败');if(result.saved_results_used!==false||result.live_computation!==true||result.query!==query||result.method!==method)throw Error('结果与本次请求不一致');
    const lexical=['keyword','bm25'].includes(method);const visible=lexical?result.results.filter(row=>row.matched_tokens?.length>0):result.results;
    render(visible,result);let note=`已完成${el('method').selectedOptions[0].textContent}。搜索 ${result.search_ms.toFixed(1)} ms；本次模型加载 ${result.load_ms.toFixed(1)} ms。`;
    if(visible.length<result.results.length)note+=' 页面隐藏了没有词汇命中的记录；原始检索排名仍单独保留。';
    if(result.hard_filter)note+=` 必须条件：符合${result.hard_filter.eligible_ids.length}，未知${result.hard_filter.unknown_ids.length}，不符合${result.hard_filter.unmet_ids.length}。`;
    if(/安静|湖景|野餐|桌游|亲子|甜品|营业|步道/.test(query))note+=' 需求包含可能缺少来源证据的体验或设施，搜索相关不代表这些条件已满足。';
    el('notice').textContent=note;
  }catch(error){render([]);el('results').replaceChildren();el('resultTitle').textContent='本次搜索未完成';el('notice').textContent='搜索未完成：'+error.message+'。没有自动切换方法或返回旧结果。';}
  finally{busy=false;el('search').disabled=false;el('query').readOnly=false;el('method').disabled=false;try{await status()}catch(_){}}
}
el('searchForm').addEventListener('submit',search);el('closeDetail').addEventListener('click',()=>el('detail').close());el('fit').addEventListener('click',fit);
el('method').addEventListener('change',()=>{el('search').disabled=busy||el('method').selectedOptions[0].disabled;});
el('basemap').addEventListener('change',()=>{if(!map||!tiles)return;if(el('basemap').checked)tiles.addTo(map);else{map.removeLayer(tiles);el('tileStatus').textContent='街道底图已关闭，来源标记仍可浏览。';}});
el('browse').addEventListener('click',()=>{if(!busy){render(catalog);el('notice').hidden=true;}});document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{el('query').value=button.dataset.query;el('query').focus();}));
(async()=>{try{initMap();await status();const r=await fetch('/api/places',{cache:'no-store'});if(!r.ok)throw Error('无法读取地点目录');const data=await r.json();catalog=data.places;for(const category of [...new Set(catalog.map(row=>row.category))].sort()){const option=text('option',category);option.value=category;el('category').append(option);}render(catalog);}catch(error){el('notice').hidden=false;el('notice').textContent=error.message;}})();

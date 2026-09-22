const $ = (s) => document.querySelector(s);
let data, horizon = 'D5', selectedModel = 'full';
const fmt = (n, digits=3) => typeof n === 'number' && Number.isFinite(n) ? n.toLocaleString('en-US', {maximumFractionDigits:digits,minimumFractionDigits:digits}) : '—';
const pct = (n) => typeof n === 'number' ? `${(100*n).toFixed(1)}%` : '—';
const words = {Positive:'偏强 · 待检验',Negative:'偏弱 · 待检验',Neutral:'Neutral / 无明确方向'};
const roles = {predictive_research:'预测研究',candidate:'候选',context:'Context',risk:'Risk',disabled:'Disabled'};
function el(tag, text, cls) {const e=document.createElement(tag); if(text !== undefined)e.textContent=text; if(cls)e.className=cls; return e;}
function row(cells) {const tr=el('tr'); for(const cell of cells)tr.append(el('td',cell)); return tr;}
function safeLink(url,text) {const a=el('a',text); try {const u=new URL(url); if(['http:','https:'].includes(u.protocol)) {a.href=u.href;a.target='_blank';a.rel='noreferrer';}}catch{} return a;}
function drawChart() {
  const prices=data.prices || []; const svg=$('#chart'); svg.replaceChildren();
  if(prices.length<2)return;
  const values=prices.map(p=>p.close); const min=Math.min(...values),max=Math.max(...values); const span=max-min||1;
  const ns='http://www.w3.org/2000/svg';
  for(let i=0;i<4;i++){const y=20+i*53;const line=document.createElementNS(ns,'line');for(const [k,v]of Object.entries({x1:0,x2:1040,y1:y,y2:y,stroke:'#30413c','stroke-dasharray':'3 5'}))line.setAttribute(k,v);svg.append(line);const text=document.createElementNS(ns,'text');text.setAttribute('x','1050');text.setAttribute('y',y+4);text.setAttribute('fill','#9caa9e');text.setAttribute('font-size','11');text.textContent=fmt(max-span*i/3,0);svg.append(text);}
  const line=document.createElementNS(ns,'polyline');line.setAttribute('points',values.map((v,i)=>`${i/(values.length-1)*1035},${20+(max-v)/span*160}`).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','#dec284');line.setAttribute('stroke-width','2.2');svg.append(line);
  $('#chart-range').replaceChildren(el('span',prices[0].date),el('span',prices.at(-1).date));
  $('#price').textContent=fmt(values.at(-1),2);$('#price-date').textContent=prices.at(-1).date+' · 已完成观测';
}
function renderHorizons(){
  $('#horizons').replaceChildren();
  for(const h of ['H4','D1','D3','D5']) {
    const p=data.current[h],d=p?.details;
    const button=el('button',undefined,'horizon'+(h===horizon?' active':''));
    const head=el('span',undefined,'head');head.append(el('span',h==='D5'?'D5 · 一周研究':h),el('span','No Edge'));
    button.append(head,el('strong',d?.score!=null?fmt(d.score):'数据不足'),el('small',words[d?.direction]||'尚无可评分预测'));
    button.onclick=()=>{horizon=h;renderHorizons();renderExplain();renderPerformance();};$('#horizons').append(button);
  }
}
function renderExplain(){
  const prediction=data.current[horizon], d=prediction?.details;
  $('#view-title').textContent=`${horizon} · ${words[d?.direction]||'证据不足'}`;
  $('#view-summary').textContent=d?.score!=null?`Evidence ${fmt(d.score)}。这是固定参数的研究影子模型，未认证 Edge。${d.regime==='stress'?'传统市场压力较高。':'传统市场风险状态：'+d.regime+'。'}`:'该期限尚不能形成严谨的数值判断。没有用日线伪造4小时预测。';
  $('#identity').textContent=prediction?`${prediction.model_version} · 特征日 ${d.feature_date} · 发出 ${prediction.issued_at} · ${prediction.cohort}`:'先运行 collect → publish-shadow → freeze。';
  $('#drivers').replaceChildren();
  const active=[...(d?.tree||[]),...(d?.intercept_contribution?[{label:'BASE_RATE',contribution:d.intercept_contribution}]:[])].filter(n=>n.contribution!==0).sort((a,b)=>Math.abs(b.contribution)-Math.abs(a.contribution));
  if(d?.score!=null && Math.abs(d.intercept_contribution)>Math.abs(d.score)*.5)$('#view-summary').append(' 注意：超过一半净分数来自历史基准/截距，而非当期新因子证据。');
  for(const n of active){const entry=el('div',undefined,'driver'),track=el('div',undefined,'driver-track'),bar=el('div',undefined,'driver-bar');bar.style.width=`${Math.min(100,Math.abs(n.contribution)*100)}%`;bar.style.background=n.contribution>0?'var(--pos)':'var(--neg)';track.append(bar);entry.append(el('span',n.label),track,el('span',fmt(n.contribution),n.contribution>0?'positive':'negative'));$('#drivers').append(entry);}
  if(d)$('#drivers').append(el('p',`截距贡献 ${fmt(d.intercept_contribution)}；所有叶贡献 + 截距 = ${fmt(d.score)}。`,'fine'));
  $('#tree').replaceChildren();const families=new Map();
  for(const n of d?.tree||[]){if(!families.has(n.family))families.set(n.family,[]);families.get(n.family).push(n);}
  for(const [family,nodes] of families){
    const group=el('details',undefined,'family'); const summary=el('summary'); const total=nodes.reduce((s,n)=>s+n.contribution,0);
    summary.append(el('span',family),el('small',`${nodes.filter(n=>n.role==='predictive_research').length} 预测研究 / ${nodes.length} 节点`),el('b',fmt(total),total<0?'negative':'positive'));group.append(summary);
    const leaves=el('div',undefined,'leaves');
    for(const n of nodes){const leaf=el('details',undefined,'leaf'),top=el('summary');top.append(el('span',`${n.id} · ${n.label}`),el('small',roles[n.role]||n.role),el('b',fmt(n.contribution)));leaf.append(top);
      const grid=el('div',undefined,'leaf-grid');
      for(const [label,value]of [['原始输入 / 单位',`${fmt(n.raw_value)} ${n.unit||''}`],['转换后因子值',fmt(n.value)],['Factor Score',fmt(n.score)],['回归敏感度 θ',fmt(n.coefficient,5)],['有效权重（共同有界缩放后）',fmt(n.effective_weight,5)],['最终贡献',fmt(n.contribution,5)],['来源 / 标的',`${n.source||'未绑定'} / ${n.instrument||'—'}`],['观察日期',n.observation_date||'—'],['保守可用时点（非历史PIT认证）',n.available_at_assumed||'—'],['本系统首次取得',n.first_seen_at||'—'],['验证等级',n.validation],['数据状态',n.status]]){const cell=el('div');cell.append(el('label',label),el('span',value));grid.append(cell);}
      const formula=el('div',undefined,'formula');formula.append(el('label','数学变换'),el('span',n.transformation));grid.append(formula);
      const trace=el('div',undefined,'formula');trace.append(el('label','真实尺度参数 / 组合输入'),el('pre',JSON.stringify(n.transform_components||[],null,2)));grid.append(trace);
      const aggregation=el('div',undefined,'formula');aggregation.append(el('label','聚合公式 / 背景压力（不等于预测）'),el('span',`${n.contribution_formula||'—'}; common scale=${fmt(n.common_squash_scale,5)}; Context Score=${fmt(n.context_score)}`));grid.append(aggregation);
      const meaning=el('div',undefined,'formula');meaning.append(el('label','经济含义 / 限制'),el('span',n.meaning));grid.append(meaning);
      const source=el('div',undefined,'formula');source.append(el('label','原始载荷血缘'),el('span',n.payload_id||'未绑定'));if(n.source_url)source.append(el('br'),safeLink(n.source_url,'查看数据源 ↗'));grid.append(source);leaf.append(grid);leaves.append(leaf);
    }group.append(leaves);$('#tree').append(group);
  }
}
function renderPerformance(){
  const h=data.research?.horizons?.[horizon]; const select=$('#model-select'); select.replaceChildren();
  $('#performance-title').textContent=`${horizon} · 样本外比较`;
  $('#stats').replaceChildren();$('#comparison').replaceChildren();$('#years').replaceChildren();
  if(!h?.models){$('#performance-boundary').textContent=h?.reason||'尚未执行历史研究。';return;}
  for(const name of Object.keys(h.models)){const option=el('option',name);option.value=name;select.append(option);}select.value=selectedModel;
  const m=h.models[selectedModel]?.holdout;
  $('#performance-boundary').textContent=`GC Proxy / 重建历史，非严格vintage PIT认证。留出段起点 ${data.research.holdout_start}；共同可比较日期 ${h.eligible_common_dates} / 全部特征日期 ${h.all_feature_dates}。命中率含Flat未命中，Coverage为共同可比较集合内发声比例。`;
  for(const [label,value]of [['留出期方向命中',pct(m?.hit_rate)],['留出期 Coverage',pct(m?.coverage)],['相同发声日趋势基线',pct(m?.baseline_same_dates_hit)],['发声 / 最少非重叠 n',`${m?.directional_n??0} / ${m?.nonoverlap_min_n??0}`]]){const card=el('div',undefined,'stat');card.append(el('span',label),el('strong',value));$('#stats').append(card);}
  if(m?.increment_ci95_block20)$('#stats').append(el('p',`对20D趋势基线的命中差95%区间（20日块）：${m.increment_ci95_block20.map(pct).join(' ～ ')}；不是独立伯努利样本区间。`,'fine'));
  for(const [name,v]of Object.entries(h.models)){const d=v.development,t=v.holdout;$('#comparison').append(row([name,pct(d?.hit_rate),pct(t?.hit_rate),pct(t?.coverage),pct(t?.increment_vs_mom20),`${t?.n??0} / ${t?.directional_n??0}`]));}
  for(const [year,m]of Object.entries(h.by_year||{}))$('#years').append(row([year,pct(m.hit_rate),pct(m.coverage),m.directional_n,m.nonoverlap_min_n]));
  const c=data.calibration;$('#calibration').textContent=c?`正式冻结 ${c.total_predictions} 条，已评价 ${c.evaluated} 条。${c.evaluated?'描述统计已追加，尚无自动晋级。':'结果尚未到期，不能把历史回填填进这里。'} 校准结论 ${c.decision}；参数没有自动修改。`:'尚无真实到期结果。';
}
function renderLedger(){
  $('#ledger-rows').replaceChildren();
  for(const p of data.ledger){const outcome=p.outcome;const tr=row([p.issued_at,p.horizon,fmt(p.score),`${words[p.direction]||'数据不足'} / ${p.edge}`,p.model_version,outcome?`${outcome.status} · ${pct(outcome.return)}`:p.horizon==='H4'?'不支持结果评价':'等待未来基准 / 到期']);const cell=el('td'),button=el('button','展开');button.onclick=async()=>{$('#record-json').textContent='读取冻结原件…';$('#record-dialog').showModal();try{const response=await fetch(`/api/assets/${encodeURIComponent(data.asset.id)}/predictions/${encodeURIComponent(p.id)}`);if(!response.ok)throw new Error(await response.text());$('#record-json').textContent=JSON.stringify({prediction:await response.json(),outcome},null,2);}catch(error){$('#record-json').textContent=error.message;}};cell.append(button);tr.append(cell);$('#ledger-rows').append(tr);}
}
async function load(){
  $('#reload').disabled=true;$('#error').hidden=true;
  try{const asset=new URLSearchParams(location.search).get('asset')||'gold';const response=await fetch(`/api/assets/${encodeURIComponent(asset)}`);if(!response.ok)throw new Error('该资产未注册或本地数据不可用；不会套用其他资产模型。 '+await response.text());data=await response.json();document.title=`${data.asset.name} · Digital Oracle Research`;
    $('#boundary').textContent='GC Proxy 研究影子模型 · EOD_NEXT_SESSION：发出日期之后下一有效日收盘建立基准，再观察 1 / 3 / 5 个有效日。不是盘前即时成交，也不是 XAUUSD 现货模型。';
    drawChart();renderHorizons();renderExplain();renderPerformance();renderLedger();
    $('#source-rows').replaceChildren();for(const s of data.sources)$('#source-rows').append(row([s.id,`${s.source} / ${s.instrument}`,`${s.first} → ${s.last}`,s.count,s.pit]));$('#source-errors').textContent=Object.keys(data.source_errors).length?JSON.stringify(data.source_errors,null,2):'本次归档未报告源连接失败；不等于数据已通过PIT认证。';$('#updated').textContent=`读取 ${data.now}`;
  }catch(error){$('#error').textContent=`未能读取工作台：${error.message}`;$('#error').hidden=false;}finally{$('#reload').disabled=false;}
}
$('#reload').onclick=load;$('#model-select').onchange=(e)=>{selectedModel=e.target.value;renderPerformance();};$('#close-dialog').onclick=()=>$('#record-dialog').close();$('#expand-all').onclick=()=>{const groups=[...document.querySelectorAll('.family')];const open=groups.some(g=>!g.open);groups.forEach(g=>g.open=open);};
for(const button of document.querySelectorAll('[data-tab]'))button.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b===button));document.querySelectorAll('.tab-content').forEach(s=>s.hidden=s.id!==button.dataset.tab);};
load();

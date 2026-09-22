export const finite = x => typeof x === 'number' && Number.isFinite(x);
export function reconcile(detail) {
  const base = detail?.intercept_contribution || 0;
  const families = new Map();
  for (const node of detail?.tree || []) {
    const group = families.get(node.family) || {name:node.family, nodes:[], contribution:0};
    group.nodes.push(node); group.contribution += node.contribution || 0;
    families.set(node.family, group);
  }
  const total = base + [...families.values()].reduce((s,g)=>s+g.contribution,0);
  return {base, families:[...families.values()], total,
    valid:finite(detail?.score) && Math.abs(total-detail.score)<1e-8};
}
export function ledgerStats(rows, horizon, model='all') {
  const selected=rows.filter(p=>p.horizon===horizon && (model==='all'||p.model_version===model));
  const eligible=selected.filter(p=>finite(p.score));
  const voiced=eligible.filter(p=>['Positive','Negative'].includes(p.direction));
  const evaluated=selected.filter(p=>p.outcome?.status==='evaluated');
  const tested=evaluated.filter(p=>['Positive','Negative'].includes(p.direction));
  return {n:selected.length, eligible:eligible.length, voiced:voiced.length, evaluated:evaluated.length,
    coverage:eligible.length?voiced.length/eligible.length:null,
    operationalCoverage:selected.length?voiced.length/selected.length:null,
    hitRate:tested.length?tested.filter(p=>p.outcome.directional_hit===true).length/tested.length:null,
    tested:tested.length, edges:selected.filter(p=>p.edge==='Edge').length};
}
export function isStale(issuedAt, now=Date.now()) {
  const stamp=Date.parse(issuedAt);
  return !Number.isFinite(stamp)||now-stamp>96*3600*1000;
}

'use strict';
let dataset={catalog:[],runs:[]};
const $=id=>document.getElementById(id);
const text=(id,value)=>{$(id).textContent=value;};
function state(){const q=new URLSearchParams(location.hash.slice(1));return {case_id:q.get('case')||'08-completion-gate',mode:q.get('mode')==='live'?'live':'fixture',variant:['nominal','adversarial','uncertain'].includes(q.get('variant'))?q.get('variant'):'nominal'};}
function selectCase(id){let s=state();location.hash=new URLSearchParams({case:id,mode:s.mode,variant:s.variant}).toString();}
function updateHash(){location.hash=new URLSearchParams({case:$('case-select').value,mode:$('mode-select').value,variant:$('variant-select').value}).toString();}
function addText(parent,tag,value,cls){let el=document.createElement(tag);el.textContent=value;if(cls)el.className=cls;parent.appendChild(el);return el;}
function renderList(){let query=$('case-search').value.toLowerCase();$('case-list').replaceChildren();for(const c of dataset.catalog){if(!(c.title+' '+c.group).toLowerCase().includes(query))continue;let b=document.createElement('button');b.className='case-link'+(c.id===state().case_id?' active':'');b.dataset.case=c.id;addText(b,'small',c.group.toUpperCase());addText(b,'span',c.id.slice(0,2)+' / '+c.title);b.onclick=()=>selectCase(c.id);$('case-list').appendChild(b);}}
function render(){
const s=state();let c=dataset.catalog.find(x=>x.id===s.case_id);if(!c)c=dataset.catalog[0];if(!c)return;
$('case-select').value=c.id;$('mode-select').value=s.mode;$('variant-select').value=s.variant;renderList();
text('case-category',c.group.toUpperCase()+' / '+c.id.slice(0,2));text('case-title',c.title);
const candidates=dataset.runs.filter(r=>r.case_id===c.id&&r.mode===s.mode&&r.variant===s.variant).sort((a,b)=>b.recorded_utc.localeCompare(a.recorded_utc));
const r=candidates[0];$('evidence').hidden=!r;$('empty').hidden=!!r;
$('provenance').className='provenance'+(s.mode==='live'?' live':'');
if(!r){text('provenance','NO MATCHING RECEIPT — NO INFERENCE PERFORMED IN THIS VIEW');text('policy-status','NO EVIDENCE');$('policy-status').className='badge';delete document.body.dataset.runId;return;}
text('provenance',r.provenance_label+(window.__WORKBENCH_SNAPSHOT__?' · OFFLINE SNAPSHOT':''));text('policy-status',r.policy.status.replaceAll('_',' '));
$('policy-status').className='badge '+(r.policy.status==='BLOCK'?'block':r.policy.status==='REVIEW'?'review':'pass');
text('decision-title',r.policy.recommendation?r.policy.recommendation.replaceAll('_',' '):r.policy.status.replaceAll('_',' '));
text('decision-reason',r.policy.reasons.join(' '));text('decision-items',r.policy.items?JSON.stringify(r.policy.items):'');
text('input-state',JSON.stringify(r.state,null,2));text('raw-receipt',JSON.stringify(r,null,2));$('answer-list').replaceChildren();
for(const [key,a] of Object.entries(r.answers)){
 const card=document.createElement('div');card.className='answer';const row=document.createElement('div');row.className='answer-top';card.appendChild(row);
 addText(row,'span',key.replaceAll('_',' '));addText(row,'span',a.type.toUpperCase(),'type');
 let v=a.type==='noul'?'P(yes) = '+a.noul.toFixed(3):a.type==='choice'?a.choice.replaceAll('_',' '):'Score = '+a.score.toFixed(2);
 addText(card,'b',v);addText(card,'div',a.type==='noul'?'No separate confidence field.':`Reported confidence: ${a.confidence.toFixed(3)} · not an authorization score`,'prob');
 addText(card,'p',r.questions[key].instructions,'question');$('answer-list').appendChild(card);
}
text('run-id','RUN '+r.run_id);text('model-id',r.model_resolved);text('run-time',r.recorded_utc);
document.body.dataset.runId=r.run_id;document.body.dataset.ready='true';
}
async function load(){try{if(window.__WORKBENCH_SNAPSHOT__){dataset=window.__WORKBENCH_SNAPSHOT__;}else{const response=await fetch('/api/data',{cache:'no-store'});if(!response.ok)throw Error('Receipt refresh failed.');dataset=await response.json();}$('case-select').replaceChildren();for(const c of dataset.catalog){const option=document.createElement('option');option.value=c.id;option.textContent=c.id.slice(0,2)+' / '+c.title;$('case-select').appendChild(option);}text('case-count',dataset.catalog.length);text('fixture-count',dataset.runs.filter(r=>r.mode==='fixture').length);text('live-count',dataset.runs.filter(r=>r.mode==='live').length);text('connection','');render();}catch(e){text('connection','Unable to refresh. Previously loaded evidence may be stale; check the local server.');}}
window.addEventListener('hashchange',render);$('case-search').addEventListener('input',renderList);for(const id of ['case-select','mode-select','variant-select'])$(id).addEventListener('change',updateHash);$('refresh').onclick=load;load();

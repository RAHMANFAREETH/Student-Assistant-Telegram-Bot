import {ACTIVITIES,LABELS} from './super_miniapp_v121_data.mjs';
import {mountStudy} from './super_miniapp_v121_study.mjs';
import {mountMind} from './super_miniapp_v121_mind.mjs';
import {mountHelper} from './super_miniapp_v121_helpers.mjs';
import {escapeHtml,validateCatalog} from './super_miniapp_v121_engine.mjs';
const VERSION='v121';
const byId=(id)=>document.getElementById(id);
const cardGrid=byId('arcade-grid'),dashboard=byId('arcade-dashboard'),game=byId('arcade-game'),panel=byId('arcade-game-panel');
const sessionCache=new Map();
const appStore={get(key,fallback){if(sessionCache.has(key))return sessionCache.get(key);try{let v=JSON.parse(localStorage.getItem('sa-arcade-'+VERSION+'-'+key));return v===null?fallback:v;}catch{return fallback;}},set(key,value){sessionCache.set(key,value);try{localStorage.setItem('sa-arcade-'+VERSION+'-'+key,JSON.stringify(value));return true;}catch{return false;}},remove(key){sessionCache.delete(key);try{localStorage.removeItem('sa-arcade-'+VERSION+'-'+key);}catch{}}};
let lang=appStore.get('lang','en');if(!Object.hasOwn(LABELS,lang))lang='en';
let category='all',query='',active=null,stopCurrent=()=>{};
function l(){return LABELS[lang];}
function renderSummary(){let rec=appStore.get('records',[]);if(!Array.isArray(rec))rec=[];byId('arcade-total').textContent=rec.length;byId('arcade-xp').textContent=rec.reduce((a,b)=>a+(Number(b.xp)||0),0);byId('arcade-play-label').textContent=l().plays;byId('arcade-xp-label').textContent=l().points;}
function translate(){document.documentElement.lang=lang;byId('arcade-title').textContent=l().title;byId('arcade-subtitle').textContent=l().subtitle;byId('arcade-privacy').textContent=l().local;byId('arcade-back').textContent=l().back;byId('arcade-home').textContent=l().home;byId('arcade-search').placeholder=l().search;byId('arcade-empty').textContent=l().noGames;byId('arcade-reset').textContent=l().reset;byId('arcade-game-note').textContent=l().offline;byId('arcade-language').value=lang;
 document.querySelector('[data-filter="all"]').textContent=l().all;document.querySelector('[data-filter="study"]').textContent='📚 '+l().study;document.querySelector('[data-filter="mind"]').textContent='🧠 '+l().mind;document.querySelector('[data-filter="helper"]').textContent='🗓️ '+l().helper;renderSummary();if(active){byId('arcade-game-title').textContent=active.name[lang];byId('arcade-game-category').textContent=l()[active.category];}}
function renderCards(){const shown=ACTIVITIES.filter(a=>(category==='all'||a.category===category)&&a.name[lang].toLocaleLowerCase().includes(query)|| (category==='all'||a.category===category)&&a.name.en.toLowerCase().includes(query));
 cardGrid.innerHTML=shown.map(a=>`<button class="activity-card" type="button" data-id="${a.id}"><span class="activity-icon">${a.emoji}</span><span class="activity-label">${escapeHtml(a.name[lang])}</span><span class="activity-category">${escapeHtml(l()[a.category])}</span></button>`).join('');byId('arcade-empty').hidden=shown.length!==0;
 cardGrid.querySelectorAll('button').forEach(b=>b.onclick=()=>openActivity(b.dataset.id));
 document.querySelectorAll('[data-filter]').forEach(b=>{b.classList.toggle('selected',b.dataset.filter===category);});}
function cleanup(){stopCurrent();stopCurrent=()=>{};panel.replaceChildren();}
function home(){cleanup();active=null;game.hidden=true;dashboard.hidden=false;byId('arcade-home').hidden=true;byId('arcade-hero').hidden=false;translate();renderCards();window.scrollTo({top:0,behavior:'instant'});}
function openActivity(id){const activity=ACTIVITIES.find(x=>x.id===id);if(!activity)return;cleanup();active=activity;dashboard.hidden=true;game.hidden=false;byId('arcade-home').hidden=false;byId('arcade-hero').hidden=true;byId('arcade-game-emoji').textContent=activity.emoji;byId('arcade-game-title').textContent=activity.name[lang];byId('arcade-game-category').textContent=l()[activity.category];
 let activeSession=true,stoppers=[],timers=new Set(),recorded=false;stopCurrent=()=>{activeSession=false;for(const t of timers)clearTimeout(t);timers.clear();for(const s of stoppers){try{s();}catch{}};};
 const ctx={l:l(),store:appStore,delay(fn,ms){const t=setTimeout(()=>{timers.delete(t);if(activeSession)fn();},ms);timers.add(t);return t;},cancel(t){clearTimeout(t);timers.delete(t);},cleanup(fn){stoppers.push(fn);},finish(score,total){if(!activeSession||recorded||activity.category==='helper')return;recorded=true;score=Math.max(0,Math.min(Number(total)||1,Number(score)||0));total=Math.max(1,Number(total)||1);let xp=Math.round((score/total)*30)+5;const rec=appStore.get('records',[]),safe=Array.isArray(rec)?rec.slice(-99):[];safe.push({id,date:new Date().toISOString().slice(0,10),score,total,xp});const persisted=appStore.set('records',safe);renderSummary();const badge=document.createElement('p');badge.className='xp-earned';badge.textContent=`🏆 ${score}/${total} · +${xp} XP — ${persisted?'saved on this device':'session only (device storage unavailable)'}`;panel.append(badge);},download(blob,filename){if(!(blob instanceof Blob))return;const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;a.rel='noopener';document.body.append(a);a.click();a.remove();this.delay(()=>URL.revokeObjectURL(url),35000);}};
 try{if(activity.category==='study')mountStudy(id,panel,ctx);else if(activity.category==='mind')mountMind(id,panel,ctx);else mountHelper(id,panel,ctx);}catch(e){panel.textContent='This activity could not start. Please return to All games.';console.error('Arcade activity error',id,e);}window.scrollTo({top:0,behavior:'instant'});
}
byId('arcade-home').onclick=home;
byId('arcade-language').onchange=e=>{lang=Object.hasOwn(LABELS,e.target.value)?e.target.value:'en';appStore.set('lang',lang);translate();renderCards();if(active){const id=active.id;openActivity(id);}};
byId('arcade-search').oninput=e=>{query=e.target.value.trim().toLocaleLowerCase();renderCards();};
document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{category=b.dataset.filter;renderCards();});
byId('arcade-reset').onclick=()=>{if(!window.confirm(l().confirm))return;for(const k of ['records','questions','topics','studyDates','revision','dailyPlan'])appStore.remove(k);renderSummary();};
if(validateCatalog().total!==32)throw Error('Arcade catalog incomplete');
translate();renderCards();

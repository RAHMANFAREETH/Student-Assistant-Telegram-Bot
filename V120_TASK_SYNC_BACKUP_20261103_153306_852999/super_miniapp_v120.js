import {TOOLS,CATEGORIES,UNITS,compute,securePassword,secureRandom,FORMAT,translateUI,translateCategory,displayToolName,localUI,localField} from '/app/assets/tools.mjs';

// No tracking, analytics or external APIs. All utility calculations run locally.
const $ = id=>document.getElementById(id);
const tg = window.Telegram?.WebApp;
const state={user:null,tab:'home',category:'All',tool:null,favorites:[],recent:[],tasks:[],clockTimer:null,cleanup:null,manuallySetTheme:false,lang:'en',plannerLoaded:false,plannerLoading:false,plannerData:{assignments:[],exams:[]},plannerError:''};
const i18n=key=>localUI(key,state.lang);
const displayName=tool=>displayToolName(tool,state.lang);
function applyLanguage(){document.documentElement.lang=state.lang;document.querySelectorAll('[data-i18n]').forEach(e=>{e.textContent=i18n(e.dataset.i18n);});document.querySelectorAll('[data-i18n-placeholder]').forEach(e=>{e.placeholder=i18n(e.dataset.i18nPlaceholder);});$('language-select').value=state.lang;document.querySelectorAll('[data-v120-label]').forEach(e=>{e.textContent=localField(e.dataset.v120Label,state.lang);});document.querySelectorAll('[data-v120-ui]').forEach(e=>{e.textContent=i18n(e.dataset.v120Ui);});renderCategories();renderGrid();renderTasks();renderPlannerOverview();if(state.tool){const tool=TOOLS.find(t=>t.id===state.tool);if(tool)$('tool-heading').textContent=displayName(tool);}}
const storePrefix=()=>`studentassistant_v120_${state.user}_`;
function readStored(key,fallback){try{const v=JSON.parse(localStorage.getItem(storePrefix()+key));return v??fallback;}catch{return fallback;}}
function saveStored(key,val){try{localStorage.setItem(storePrefix()+key,JSON.stringify(val));}catch{status('Local storage unavailable. Your changes will not be saved.');}}
function status(message){$('status').textContent=message||'';}
function el(tag,attrs={},txt){const x=document.createElement(tag);for(const [k,v] of Object.entries(attrs)){if(k==='class')x.className=v;else if(k==='dataset')for(const [n,b] of Object.entries(v))x.dataset[n]=b;else if(k==='value')x.value=v;else x.setAttribute(k,v);}if(txt!==undefined)x.textContent=txt;return x;}
function clearCleanup(){if(state.cleanup){try{state.cleanup();}catch{}state.cleanup=null;}}
function applyTheme(theme){document.documentElement.dataset.theme=theme==='light'?'light':'dark';}
function localISO(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
const specs = {
 'weekday':[['date','Date','date',localISO()]],
 'days-until':[['start','Start date','date',localISO()],['end','Target date','date',localISO()]],
 'month-shift':[['date','Date','date',localISO()],['offset','Months (+ or -)','number',3]],
 'time-duration':[['start','Start (24h)','time','09:00'],['end','End (24h)','time','17:30']],
 'fraction':[['numerator','Numerator','number',12],['denominator','Denominator','number',18]],
 'ratio':[['left','First number','number',12],['right','Second number','number',18]],
 'average':[['values','Values (commas or new lines)','textarea','10, 20, 30, 40']],
 'gpa':[['rows','Credits,grade points (one course per line)','textarea','3,4.0\n2,3.0\n3,3.7']],
 'tip':[['amount','Bill amount','number',2500],['tip','Tip percentage','number',10],['people','Number of people','number',2]],
 'simple-interest':[['principal','Principal amount','number',10000],['rate','Annual rate (%)','number',8],['years','Years','number',2]],
 'compound-interest':[['principal','Principal amount','number',10000],['rate','Annual rate (%)','number',8],['years','Years','number',2],['times','Compoundings per year','number',12]],
 'loan-payment':[['principal','Loan amount','number',100000],['rate','Annual rate (%)','number',8],['years','Loan term (years)','number',5]],
 'prime':[['value','Integer (0–10000000)','number',97]],
 'square-root':[['value','Nonnegative number','number',144]],
 'text-sort':[['text','Lines to sort','textarea','Apple\nOrange\nBanana']],
 'text-unique':[['text','Lines','textarea','one\ntwo\none'],['ignoreCase','Ignore capitalization','checkbox',true]],
 'reading-time':[['text','Passage','textarea','Type your passage here.'],['speed','Words per minute (80–500)','number',200]],
 'text-reverse':[['text','Text','textarea','Student Assistant']],
 'url-encode':[['text','Text or URL component','textarea','Hello world?'],['mode','Action','select','encode',['encode','decode']]],
 'color-contrast':[['foreground','Foreground hex','text','#FFFFFF'],['background','Background hex','text','#202040']],

 'date-difference':[['start','Start date','date',localISO()],['end','End date','date',localISO()],['include','Include end date','checkbox',false]],
 'date-add':[['date','Start date','date',localISO()],['offset','Days to add (negative to subtract)','number',20]],
 age:[['birth','Date of birth','date','2000-01-01'],['asof','As of','date',localISO()]],
 'day-of-year':[['date','Date','date',localISO()]],
 epoch:[['timestamp','Unix timestamp','number',1793700000],['unit','Unit','select','seconds',['seconds','milliseconds']]],
 temperature:[['value','Temperature','number',25],['from','From','select','Celsius',['Celsius','Fahrenheit','Kelvin']],['to','To','select','Fahrenheit',['Celsius','Fahrenheit','Kelvin']]],
 base:[['value','Integer','text','101011'],['from','From base (2–36)','number',2],['to','To base (2–36)','number',10]],
 calculator:[['a','First number','number',100],['operator','Operation','select','+',['+','-','×','÷','^']],['b','Second number','number',12]],
 percent:[['percent','Percentage','number',20],['value','Of number','number',100]],
 discount:[['price','Original price','number',2500],['percent','Discount %','number',15]],
 bmi:[['weight','Weight (kg)','number',70],['height','Height (cm)','number',175]],
 electricity:[['volts','Voltage (V)','number',230],['amps','Current (A)','number',2]],
 random:[['min','Minimum','number',1],['max','Maximum','number',100]],
 'word-count':[['text','Text','textarea','']],
 'text-case':[['text','Text','textarea',''],['mode','Change to','select','upper',['upper','lower','title']]],
};
function makeField([id,label,type,defaultValue,options]){
 const wrap=el('div',{class:'field'+(type==='textarea'?' full':'')});const lbl=el('label',{for:'v120-'+id,'data-v120-label':label},localField(label,state.lang));
 let input;
 if(type==='select'){input=el('select',{id:'v120-'+id,name:id});for(const opt of options||[])input.append(el('option',{value:opt},opt));input.value=defaultValue;}
 else if(type==='textarea'){input=el('textarea',{id:'v120-'+id,name:id,rows:'5',maxlength:'16000'});input.value=defaultValue;}
 else {input=el('input',{type,id:'v120-'+id,name:id});if(type==='checkbox')input.checked=Boolean(defaultValue);else input.value=String(defaultValue);if(type==='number')input.step='any';}
 wrap.append(lbl,input);return wrap;
}
function formValues(form){const fields={};for(const e of form.elements){if(!e.name)continue;fields[e.name]=e.type==='checkbox'?e.checked:e.value;}return fields;}
function messagePanel(panel,t){panel.append(el('p',{class:'muted'},t));}
function outputBox(panel){const out=el('div',{class:'result',role:'status','aria-live':'polite'});panel.append(out);return out;}
function actionButton(text,callback,cls='primary'){const b=el('button',{type:'button',class:cls},text);b.onclick=callback;return b;}
function genericForm(panel,id){let cfg=specs[id];if(id==='unit'){cfg=[['category','Category','select','Length',Object.keys(UNITS)],['value','Value','number',1],['from','From','select','Meters',Object.keys(UNITS.Length)],['to','To','select','Feet',Object.keys(UNITS.Length)]];}
 const form=el('form',{class:'form-grid'});for(const entry of cfg)form.append(makeField(entry));panel.append(form);
 if(id==='unit'){
  const update=()=>{const c=form.elements.category.value;for(const key of ['from','to']){const sel=form.elements[key],old=sel.value;sel.replaceChildren(...Object.keys(UNITS[c]).map(u=>el('option',{value:u},u)));if(Object.hasOwn(UNITS[c],old))sel.value=old;}if(form.elements.from.value===form.elements.to.value)form.elements.to.selectedIndex=Math.min(1,form.elements.to.length-1);};
  form.elements.category.addEventListener('change',update);
 }
 const out=outputBox(panel),buttons=el('div',{class:'toolbar'}),go=el('button',{type:'submit',class:'primary','data-v120-ui':'calculate'},i18n('calculate'));buttons.append(go);
 const copy=actionButton(i18n('copyResult'),()=>navigator.clipboard?.writeText(out.textContent||'').then(()=>status(i18n('resultCopied'))).catch(()=>status(i18n('copyUnavailable'))),'secondary');copy.dataset.v120Ui='copyResult';buttons.append(copy);panel.insertBefore(buttons,out);
 const run=()=>{try{out.classList.remove('error');out.textContent=compute(id,formValues(form));}catch(e){out.classList.add('error');out.textContent=e.message;}};
 form.addEventListener('submit',e=>{e.preventDefault();run();});run();
}
function localDateTime(zone){return new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date());}
function worldClock(panel){const zones={'Sri Lanka':'Asia/Colombo','New York':'America/New_York','London':'Europe/London','Dubai':'Asia/Dubai','Tokyo':'Asia/Tokyo','Paris':'Europe/Paris','Sydney':'Australia/Sydney','Mumbai':'Asia/Kolkata'};
 const out=el('div');panel.append(out);let timer=null;const render=()=>{out.replaceChildren(...Object.entries(zones).map(([name,z])=>el('div',{class:'result'},`${name} · ${localDateTime(z)}`)));};render();timer=setInterval(render,1000);state.cleanup=()=>clearInterval(timer);}
function timeText(ms){const sec=Math.max(0,Math.floor(ms/1000));return `${String(Math.floor(sec/3600)).padStart(2,'0')}:${String(Math.floor(sec%3600/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`;}
function runningClock(panel,mode){const form=el('div',{class:'form-grid'});let duration=mode==='pomodoro'?25:5;if(mode!=='stopwatch'){form.append(makeField(['minutes','Minutes','number',duration]));panel.append(form);}const digits=el('div',{class:'live-digits'},mode==='stopwatch'?'00:00:00':timeText(duration*60000));panel.append(digits);const tb=el('div',{class:'toolbar'});panel.append(tb);
 let target=0,elapsed=0,started=0,interval=null,remaining=duration*60000;
 function update(){const now=Date.now();if(mode==='stopwatch')digits.textContent=timeText(elapsed+(started?now-started:0));else{const left=started?Math.max(0,target-now):remaining;digits.textContent=timeText(left);if(started&&left<=0){stop();remaining=0;digits.textContent='00:00:00';status('Timer completed while the app was open.');}}}
 function stop(){if(started){if(mode==='stopwatch')elapsed+=Date.now()-started;else remaining=Math.max(0,target-Date.now());started=0;}if(interval){clearInterval(interval);interval=null;}update();}
 tb.append(actionButton('Start',()=>{if(started)return;if(mode!=='stopwatch'&&remaining<=0){const n=Number(form.elements.minutes.value);if(!Number.isFinite(n)||n<=0||n>1440){status('Enter 1–1440 minutes.');return;}remaining=n*60000;}started=Date.now();target=started+remaining;interval=setInterval(update,200);update();}));
 tb.append(actionButton('Pause',stop,'secondary'));
 tb.append(actionButton('Reset',()=>{stop();elapsed=0;remaining=mode==='stopwatch'?0:(Number(form.elements.minutes.value)||duration)*60000;update();},'secondary'));
 if(mode!=='stopwatch'){messagePanel(panel,'Timer alerts only work while this Mini App remains open. Use your bot reminders for later notifications.');}
 state.cleanup=()=>{if(interval)clearInterval(interval);};}
function cryptoTool(panel,mode){const form=el('form',{class:'form-grid'});if(mode==='password'){form.append(makeField(['length','Length (8–128)','number',20]));form.append(makeField(['symbols','Include symbols','checkbox',true]));}if(mode==='uuid')form.append(makeField(['count','Number (1–20)','number',5]));panel.append(form);const out=outputBox(panel),bar=el('div',{class:'toolbar'});const go=()=>{try{if(!crypto?.getRandomValues)throw Error('Secure random generator unavailable.');if(mode==='password')out.textContent=securePassword(Number(form.elements.length.value),{symbols:form.elements.symbols.checked});else{const n=Number(form.elements.count.value);if(!Number.isInteger(n)||n<1||n>20)throw Error('Count must be 1–20.');out.textContent=Array.from({length:n},()=>crypto.randomUUID()).join('\n');}}catch(e){out.textContent=e.message;}};
 bar.append(actionButton('Generate',go));bar.append(actionButton('Copy',()=>navigator.clipboard?.writeText(out.textContent||'').then(()=>status('Copied.')).catch(()=>status('Copy not supported.')),'secondary'));panel.insertBefore(bar,out);messagePanel(panel,'Generated entirely in this browser; nothing is sent to your server.');go();}
function funRoll(panel,mode){const out=outputBox(panel);const go=()=>{if(mode==='coin')out.textContent=secureRandom(0,1)?'Heads 🪙':'Tails 🪙';else out.textContent=Array.from({length:2},()=>String(secureRandom(1,6))).join(' + ');};panel.insertBefore(actionButton(mode==='coin'?'Flip coin':'Roll two dice',go),out);go();}
function reaction(panel){messagePanel(panel,'Tap Start. When the panel turns green, tap it as quickly as you can.');const pad=el('button',{type:'button',class:'reaction-pad'},'Tap Start');panel.append(pad);const out=outputBox(panel);let stage=0,timeout=null,start=0;pad.onclick=()=>{if(stage===0){stage=1;pad.className='reaction-pad wait';pad.textContent='Wait for green…';timeout=setTimeout(()=>{stage=2;start=performance.now();pad.className='reaction-pad ready';pad.textContent='TAP NOW!';},800+secureRandom(0,2200));}else if(stage===1){clearTimeout(timeout);stage=0;pad.className='reaction-pad';pad.textContent='Too early! Tap to retry';out.textContent='False start';}else{out.textContent=`${Math.round(performance.now()-start)} ms`;stage=0;pad.className='reaction-pad';pad.textContent='Try again';}};state.cleanup=()=>{if(timeout)clearTimeout(timeout);};}
function planTime(value){if(typeof value!=='string'||!value)return '';const d=new Date(value);if(!Number.isFinite(d.getTime()))return '';try{return new Intl.DateTimeFormat(state.lang==='ta'?'ta-IN':state.lang==='si'?'si-LK':'en-GB',{dateStyle:'medium',timeStyle:'short'}).format(d);}catch{return d.toISOString().slice(0,16);}}
function renderPlannerOverview(){const assignments=$('planner-assignments'),exams=$('planner-exams');if(!assignments||!exams)return;
 assignments.replaceChildren();exams.replaceChildren();const d=state.plannerData;
 const build=(items,root,timeKey,emptyKey)=>{if(!Array.isArray(items)||!items.length){root.append(el('li',{class:'muted'},i18n(emptyKey)));return;}
 for(const record of items){if(!record||typeof record!=='object')continue;const li=el('li');const title=el('strong',{},String(record.title||'').slice(0,160));const parts=[planTime(record[timeKey]),timeKey==='due_at'?String(record.priority||'').slice(0,32):String(record.location||'').slice(0,120)].filter(Boolean);li.append(title,el('small',{},parts.join(' · ')));root.append(li);}};
 if(state.plannerLoaded){build(d.assignments,assignments,'due_at','plannerNoAssignments');build(d.exams,exams,'exam_at','plannerNoExams');}
 const msg=state.plannerLoading?'plannerLoading':state.plannerError?'plannerUnavailable':state.plannerLoaded?'plannerReadOnly':'plannerLoading';$('planner-remote-status').textContent=i18n(msg);
}
async function loadPlannerOverview(force=false){if(state.plannerLoading||(!force&&state.plannerLoaded))return;if(!tg?.initData)return;
 state.plannerLoading=true;state.plannerError='';renderPlannerOverview();
 try{const response=await fetch('/app/api/planner',{headers:{'X-Telegram-Init-Data':tg.initData},cache:'no-store',credentials:'omit'});
 const data=await response.json();if(!response.ok||data.ok!==true||!Array.isArray(data.assignments)||!Array.isArray(data.exams))throw Error('Read-only planner unavailable');
 state.plannerData={assignments:data.assignments.slice(0,30),exams:data.exams.slice(0,30)};state.plannerLoaded=true;
 }catch{state.plannerError='unavailable';state.plannerLoaded=false;state.plannerData={assignments:[],exams:[]};}
 finally{state.plannerLoading=false;renderPlannerOverview();}
}
function taskId(){if(globalThis.crypto?.randomUUID)return crypto.randomUUID();if(globalThis.crypto?.getRandomValues){const bytes=new Uint8Array(16);crypto.getRandomValues(bytes);return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');}return Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);}
function getTasks(){const ts=readStored('tasks',[]);return Array.isArray(ts)?ts.filter(t=>t&&typeof t.text==='string').slice(0,100):[];}
function updateTasks(){saveStored('tasks',state.tasks);renderTasks();}
function renderTasks(){const list=$('task-list');list.replaceChildren();if(!state.tasks.length)list.append(el('li',{},i18n('taskEmpty')));for(const t of state.tasks){const li=el('li',{class:t.done?'done':''}),cb=el('input',{type:'checkbox','aria-label':i18n('markDone')});cb.checked=!!t.done;cb.addEventListener('change',()=>{t.done=cb.checked;updateTasks();});const txt=el('span',{},t.text),del=el('button',{type:'button','aria-label':i18n('deleteTask')},'×');del.onclick=()=>{state.tasks=state.tasks.filter(x=>x.id!==t.id);updateTasks();};li.append(cb,txt,del);list.append(li);}}
function taskTool(panel){messagePanel(panel,i18n('taskHelp'));const b=actionButton(i18n('openPlanner'),()=>switchTab('planner'));panel.append(b);}
function downloadBlob(blob,filename){const url=URL.createObjectURL(blob);const a=el('a',{href:url,download:filename});document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);}
async function imgLoad(file){if(!file||!file.type.startsWith('image/'))throw Error('Select an image file.');if(file.size>15*1024*1024)throw Error('Use an image under 15 MB for this browser tool.');const img=el('img');const url=URL.createObjectURL(file);try{await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(Error('Image could not be decoded.'));img.src=url;});if(img.naturalWidth*img.naturalHeight>25000000)throw Error('Image dimensions are too large for this device.');return img;}finally{URL.revokeObjectURL(url);}}
function toBlob(canvas,type='image/png',quality=0.8){return new Promise((resolve,reject)=>canvas.toBlob(blob=>blob?resolve(blob):reject(Error('Image export failed.')),type,quality));}
function imageTool(panel,mode){const form=el('form',{class:'form-grid'});form.append(makeField(['photo','Select photo','file','']));const input=form.elements.photo;input.type='file';input.accept='image/*';if(mode==='image-compress')form.append(makeField(['quality','JPEG quality 0.1–1','number',0.72]));if(mode==='image-watermark')form.append(makeField(['watermark','Watermark text','text','Student Assistant']));panel.append(form);messagePanel(panel,'Your image stays in this browser. Exported images are re-encoded, so most original metadata is not retained. Always verify the output.');const out=outputBox(panel);
 panel.insertBefore(actionButton('Process & download',async()=>{try{out.textContent='Processing locally…';const img=await imgLoad(input.files?.[0]);const maxSide=mode==='image-compress'?1600:3000,scale=Math.min(1,maxSide/Math.max(img.naturalWidth,img.naturalHeight)),can=el('canvas');can.width=Math.round(img.naturalWidth*scale);can.height=Math.round(img.naturalHeight*scale);const ctx=can.getContext('2d');if(!ctx)throw Error('Canvas unavailable.');ctx.drawImage(img,0,0,can.width,can.height);
 if(mode==='image-watermark'){const w=String(form.elements.watermark.value||'').slice(0,120);if(!w)throw Error('Enter watermark text.');ctx.font=`bold ${Math.max(16,Math.round(can.width/24))}px sans-serif`;ctx.textAlign='center';ctx.fillStyle='rgba(255,255,255,.65)';ctx.strokeStyle='rgba(0,0,0,.7)';ctx.lineWidth=3;ctx.strokeText(w,can.width/2,can.height*0.9,can.width*0.95);ctx.fillText(w,can.width/2,can.height*0.9,can.width*0.95);}
 const isJpg=mode==='image-compress';const q=isJpg?Number(form.elements.quality.value):1;if(!Number.isFinite(q)||q<0.1||q>1)throw Error('Quality must be 0.1–1.');const blob=await toBlob(can,isJpg?'image/jpeg':'image/png',q);downloadBlob(blob,isJpg?'student-compressed.jpg':'student-export.png');out.textContent=`Exported ${can.width} × ${can.height} · ${Math.round(blob.size/1024)} KiB`;}
 catch(e){out.textContent=e.message;}},'primary'),out);
}
function signatureTool(panel){messagePanel(panel,'Draw your signature with your finger or mouse. Image is generated locally.');const canvas=el('canvas',{class:'canvas-preview',width:'640',height:'250','aria-label':'Drawing canvas'});panel.append(canvas);const ctx=canvas.getContext('2d');if(!ctx){messagePanel(panel,'Canvas unavailable.');return;}ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.strokeStyle='#121827';ctx.lineWidth=3;ctx.lineCap='round';let drawing=false;
 function pos(e){const r=canvas.getBoundingClientRect();return {x:(e.clientX-r.left)*canvas.width/r.width,y:(e.clientY-r.top)*canvas.height/r.height};}
 const down=e=>{drawing=true;canvas.setPointerCapture(e.pointerId);const p=pos(e);ctx.beginPath();ctx.moveTo(p.x,p.y);};const move=e=>{if(!drawing)return;const p=pos(e);ctx.lineTo(p.x,p.y);ctx.stroke();};const up=()=>{drawing=false;};canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);
 const actions=el('div',{class:'toolbar'});actions.append(actionButton('Clear',()=>{ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);},'secondary'));actions.append(actionButton('Save PNG',async()=>downloadBlob(await toBlob(canvas),'signature.png')));panel.append(actions);}
function routeTool(id,panel){if(specs[id]||id==='unit'){genericForm(panel,id);return;}if(id==='world-clock'){worldClock(panel);return;}if(['timer','stopwatch','pomodoro'].includes(id)){runningClock(panel,id);return;}if(id==='password'||id==='uuid'){cryptoTool(panel,id);return;}if(id==='coin'||id==='dice'){funRoll(panel,id);return;}if(id==='reaction'){reaction(panel);return;}if(id==='todo'){taskTool(panel);return;}if(['image-compress','image-strip','image-watermark'].includes(id)){imageTool(panel,id);return;}if(id==='signature'){signatureTool(panel);return;}messagePanel(panel,'Tool is unavailable.');}
function getResults(){const q=$('tool-search').value.toLocaleLowerCase().trim();let tools=TOOLS;
 if(state.category==='Favorites')tools=tools.filter(t=>state.favorites.includes(t.id));else if(state.category!=='All')tools=tools.filter(t=>t.category===state.category);
 if(q)tools=tools.filter(t=>(t.name+' '+displayName(t)+' '+t.category+' '+translateCategory(t.category,state.lang)+' '+t.summary).toLocaleLowerCase().includes(q));return tools;}
function renderCategories(){const area=$('category-pills');area.replaceChildren(...CATEGORIES.map(c=>{const btn=el('button',{type:'button',class:'pill'+(c===state.category?' active':''),'aria-pressed':String(c===state.category)},translateCategory(c,state.lang));btn.onclick=()=>{state.category=c;renderCategories();renderGrid();};return btn;}));}
function renderGrid(){const cards=getResults(),parent=$('tool-grid');parent.replaceChildren(...cards.map(t=>{const btn=el('button',{type:'button',class:'tool-card','aria-label':displayName(t)}),icon=el('span',{class:'tool-icon','aria-hidden':'true'},t.icon),name=el('span',{class:'tool-name'},displayName(t));btn.append(icon,name);btn.onclick=()=>openTool(t.id);return btn;}));$('tool-count').textContent=`${cards.length} ${i18n('toolsUnit')}`;$('category-heading').textContent=state.category==='All'?i18n('explore'):translateCategory(state.category,state.lang);if(!cards.length)parent.append(el('p',{class:'muted'},i18n('empty')));}
function openTool(id){const tool=TOOLS.find(t=>t.id===id);if(!tool)return;clearCleanup();state.tool=id;state.recent=[id,...state.recent.filter(x=>x!==id)].slice(0,12);saveStored('recent',state.recent);
 $('dashboard').hidden=true;$('tool-view').hidden=false;$('tool-emoji').textContent=tool.icon;$('tool-heading').textContent=displayName(tool);$('tool-summary').textContent=tool.summary;
 $('favorite-toggle').textContent=state.favorites.includes(id)?'★':'☆';$('favorite-toggle').setAttribute('aria-pressed',String(state.favorites.includes(id)));$('tool-body').replaceChildren();status('');routeTool(id,$('tool-body'));window.scrollTo({top:0,behavior:'instant'});}
function showDashboard(){clearCleanup();state.tool=null;$('tool-view').hidden=true;$('dashboard').hidden=false;switchTab(state.tab);}
function switchTab(tab){clearCleanup();state.tab=tab;state.tool=null;$('tool-view').hidden=true;$('dashboard').hidden=false;
 const grid=tab==='home'||tab==='tools';$('home-content').hidden=!grid;$('category-pills').hidden=!grid;$('planner-panel').hidden=tab!=='planner';$('profile-panel').hidden=tab!=='profile';$('library-panel').hidden=tab!=='library';
 if(tab==='home')state.category='All';if(tab==='tools'&&state.category==='All')state.category='All';
 document.querySelectorAll('[data-tab]').forEach(x=>{x.classList.toggle('active',x.dataset.tab===tab);x.setAttribute('aria-current',x.dataset.tab===tab?'page':'false');});renderCategories();renderGrid();if(tab==='planner'){renderTasks();loadPlannerOverview();}window.scrollTo({top:0,behavior:'instant'});}
function openBot(){const link='https://t.me/Student_Sl_Assistant_bot';if(tg?.openTelegramLink)tg.openTelegramLink(link);else window.location.assign(link);}
function start(){state.favorites=readStored('favorites',[]).filter(x=>typeof x==='string');state.recent=readStored('recent',[]).filter(x=>typeof x==='string');state.tasks=getTasks();const savedLang=readStored('language', 'en');state.lang=['en','ta','si'].includes(savedLang)?savedLang:'en';$('language-select').onchange=()=>{state.lang=$('language-select').value;saveStored('language',state.lang);applyLanguage();};applyLanguage();$('auth-wall').hidden=true;$('workspace').hidden=false;$('bottom-nav').hidden=false;
 $('tool-search').addEventListener('input',()=>{$('clear-search').hidden=!$('tool-search').value;showDashboard();switchTab('tools');});$('clear-search').onclick=()=>{$('tool-search').value='';$('clear-search').hidden=true;renderGrid();};$('back-tools').onclick=showDashboard;
 $('favorite-toggle').onclick=()=>{const id=state.tool;if(!id)return;state.favorites=state.favorites.includes(id)?state.favorites.filter(x=>x!==id):[...state.favorites,id];saveStored('favorites',state.favorites);$('favorite-toggle').textContent=state.favorites.includes(id)?'★':'☆';$('favorite-toggle').setAttribute('aria-pressed',String(state.favorites.includes(id)));};
 document.querySelectorAll('[data-tab]').forEach(x=>x.onclick=()=>switchTab(x.dataset.tab));$('open-library').onclick=()=>{window.location.assign('/library');};$('open-bot').onclick=()=>openBot();
 $('planner-refresh').onclick=()=>loadPlannerOverview(true);$('planner-open-bot').onclick=()=>openBot();
 $('task-form').onsubmit=e=>{e.preventDefault();const value=$('task-input').value.trim();if(!value)return;if(state.tasks.length>=100){status(i18n('taskLimit'));return;}state.tasks.push({id:taskId(),text:value.slice(0,160),done:false});$('task-input').value='';updateTasks();};
 document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>{navigator.clipboard?.writeText(b.dataset.copy).then(()=>status('Command copied.')).catch(()=>status('Unable to copy.'));});
 $('theme-toggle').onclick=()=>{state.manuallySetTheme=true;applyTheme(document.documentElement.dataset.theme==='light'?'dark':'light');};switchTab('home');}
async function boot(){if(tg){tg.ready();tg.expand();applyTheme(tg.colorScheme);tg.onEvent?.('themeChanged',()=>{if(!state.manuallySetTheme)applyTheme(tg.colorScheme);});}
 if(!tg?.initData){$('auth-wall').querySelector('h2').textContent=localUI('openFromTelegram',state.lang);$('auth-wall').querySelector('p').textContent=localUI('sessionRequired',state.lang);return;}
 try{const response=await fetch('/app/api/session',{headers:{'X-Telegram-Init-Data':tg.initData},cache:'no-store',credentials:'omit'});const data=await response.json();if(!response.ok||data.ok!==true||!Number.isSafeInteger(data.user_id))throw Error(data.error||'Access denied.');state.user=data.user_id;start();}
 catch(e){$('auth-wall').querySelector('h2').textContent=localUI('authUnavailable',state.lang);$('auth-wall').querySelector('p').textContent=e.message||localUI('authRetry',state.lang);}}
boot();

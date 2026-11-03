import {convertTamilFont,detectTamilEncoding,cleanTamilText,inspectUnicode,convertTamilDigits} from '/app/assets/fontstudio.mjs';
const $=id=>document.getElementById(id);
const tg=window.Telegram?.WebApp;
let active='convert';
function setNotice(msg='',error=false){const el=$('font-status');el.textContent=msg;el.classList.toggle('error',error);}
function feedback(msg,error=false){const el=$('studio-feedback');el.textContent=msg;el.hidden=false;el.classList.toggle('error',error);}
function countChars(s){return Array.from(s).length.toLocaleString();}
function recalcFont(){
 const from=$('font-from').value,to=$('font-to').value,input=$('font-input').value;
 try{
  const result=convertTamilFont(input,from,to);
  $('font-output').value=result;$('font-count').textContent=`${countChars(result)} characters`;
  const hints=[];
  if(from!=='Unicode'&&/[a-zA-Z]/.test(input))hints.push('Legacy text shares codes with English; check mixed-language words.');
  if(from!=='Unicode'&&detectTamilEncoding(input).includes('Unicode Tamil'))hints.push('Unicode Tamil found in legacy input; check the selected source profile.');
  if(from==='Unicode'&&input&&!/[\u0B80-\u0BFF]/.test(input))hints.push('No Tamil Unicode letters detected in the input.');
  if(to!=='Unicode')hints.push(`To display Tamil glyphs in a document, apply the ${to} font after pasting.`);
  setNotice(hints.join(' '));
 }catch(e){$('font-output').value='';setNotice(e.message||'Conversion failed.',true);}
}
function recalcClean(){
 try{$('clean-output').value=cleanTamilText($('clean-input').value,{removeZeroWidth:$('clean-zero').checked,normalizeSpaces:$('clean-space').checked,trimLines:$('clean-trim').checked});}
 catch(e){$('clean-output').value=e.message;}
}
function recalcInspect(){try{const r=inspectUnicode($('inspect-input').value);$('inspect-summary').textContent=`${r.characters} code points · ${r.tamil} Tamil code points · ${r.invisible} invisible markers${r.issues.length?'\nWarnings:\n'+r.issues.slice(0,12).join('\n'):''}`;$('inspect-output').value=r.details+(r.truncated?'\n…more code points omitted':'');}catch(e){$('inspect-summary').textContent=e.message;$('inspect-output').value='';}}
function recalcDigits(){try{$('digits-output').value=convertTamilDigits($('digits-input').value,$('digits-direction').value);}catch(e){$('digits-output').value=e.message;}}
async function copyText(text){
 try{
  if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable. Select and copy the text manually.');
  await navigator.clipboard.writeText(text);
  feedback('Copied to clipboard.');
 }catch(e){feedback(e.message||'Clipboard unavailable.',true);}
}
function downloadText(text,name){
 const blob=new Blob(['\uFEFF',text],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
}
function init(){
 document.querySelectorAll('.tabs button').forEach(b=>b.addEventListener('click',()=>{
  active=b.dataset.panel;
  document.querySelectorAll('.tabs button').forEach(btn=>{if(btn===b)btn.setAttribute('aria-current','page');else btn.removeAttribute('aria-current');});
  document.querySelectorAll('.pane').forEach(p=>p.hidden=p.id!==active);
 }));
 for(const name of ['font-input','font-from','font-to'])$(name).addEventListener('input',recalcFont);
 $('swap').addEventListener('click',()=>{
  const oldFrom=$('font-from').value,oldTo=$('font-to').value;
  $('font-from').value=oldTo;$('font-to').value=oldFrom;
  $('font-input').value=$('font-output').value;recalcFont();
 });
 $('sample').addEventListener('click',()=>{$('font-from').value='Unicode';$('font-to').value='Bamini';$('font-input').value='வணக்கம். தமிழ்';recalcFont();});
 $('font-copy').addEventListener('click',()=>copyText($('font-output').value));
 $('font-download').addEventListener('click',()=>downloadText($('font-output').value,'tamil-font-converted.txt'));
 $('font-clear').addEventListener('click',()=>{$('font-input').value='';recalcFont();});
 for(const id of ['clean-input','clean-zero','clean-space','clean-trim'])$(id).addEventListener('input',recalcClean);
 $('inspect-input').addEventListener('input',recalcInspect);
 for(const id of ['digits-input','digits-direction'])$(id).addEventListener('input',recalcDigits);
 document.querySelectorAll('[data-copy]').forEach(btn=>btn.addEventListener('click',()=>copyText($(btn.dataset.copy).value)));
 document.querySelectorAll('[data-download]').forEach(btn=>btn.addEventListener('click',()=>downloadText($(btn.dataset.download).value,'tamil-writing-result.txt')));
 recalcFont();recalcClean();recalcInspect();recalcDigits();
}
async function boot(){
 try{
  tg?.ready();tg?.expand();
  const headers=tg?.initData?{'X-Telegram-Init-Data':tg.initData}:{};
  const res=await fetch('/app/api/session',{headers,cache:'no-store',credentials:'omit'});
  const data=await res.json();
  if(!res.ok||data.ok!==true||(!((data.guest===true&&data.private_features===false)||(Number.isSafeInteger(data.user_id)&&data.private_features===true))))throw Error(data.error||'Open this from the Student Assistant Mini App.');
  $('auth-state').hidden=true;$('studio').hidden=false;init();
 }catch(e){$('auth-state').textContent=e.message||'Unable to verify Mini App access.';}
}
boot();

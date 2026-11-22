/* CloudBridge 13.4 — no external scripts other than Telegram's official SDK. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const tg=window.Telegram?.WebApp;
const names={google:'Google Drive',onedrive:'OneDrive',dropbox:'Dropbox'};
const TEXT={
 en:{accounts:'Connected accounts',refresh:'Refresh',oauthHelp:'Connect your own account. Your files are private to your Telegram user.',transfer:'New transfer',transferHelp:'Use an HTTPS link or a connected cloud file. To upload a Telegram file, reply to it with /cloudpush dropbox /folder/file.pdf.',source:'Source',provider:'Provider',sourceRef:'HTTPS file URL',sourceId:'Cloud file ID (Dropbox: /path/file)',destination:'Destination',path:'Destination path (begin with /)',filename:'File name',start:'Queue transfer',jobs:'My transfers',limits:'Provider quotas and Telegram Bot API limits apply. Interrupted uploads may require destination review before retrying. Share only files you have permission to use.',connect:'Connect',disconnect:'Disconnect',connected:'Connected',none:'No transfers yet',cancel:'Cancel',retry:'Retry',delete:'Delete',login:'Open CloudBridge from your Telegram bot.',loading:'Loading your account…',ready:'Signed in securely.',queued:'Transfer queued.',error:'Something went wrong. Please try again.',confirm:'Disconnect this cloud account?',confirmDelete:'Remove this finished job from history? For needs_review, check the destination first.',sent:'Transfer request submitted.'},
 ta:{accounts:'இணைக்கப்பட்ட கணக்குகள்',refresh:'புதுப்பி',oauthHelp:'உங்களுடைய cloud கணக்கை இணைக்கவும். கோப்புகள் உங்கள் Telegram கணக்கிற்கே தனிப்பட்டவை.',transfer:'புதிய கோப்புப் பரிமாற்றம்',transferHelp:'HTTPS link அல்லது இணைக்கப்பட்ட cloud file பயன்படுத்தலாம். Telegram கோப்புக்கு reply செய்து /cloudpush dropbox /folder/file.pdf அனுப்பவும்.',source:'மூலம்',provider:'சேவை',sourceRef:'HTTPS கோப்பு இணைப்பு',sourceId:'Cloud கோப்பு ID (Dropbox: /path/file)',destination:'சேருமிடம்',path:'சேருமிடப் பாதை (/ உடன் தொடங்கவும்)',filename:'கோப்புப் பெயர்',start:'பரிமாற்றத்தை வரிசையில் சேர்',jobs:'எனது பரிமாற்றங்கள்',limits:'Cloud மற்றும் Telegram கோப்பு வரம்புகள் பொருந்தும். நிறுத்தப்பட்ட upload-ஐ retry செய்யும் முன் சேருமிடத்தைச் சரிபார்க்கவும்.',connect:'இணை',disconnect:'துண்டி',connected:'இணைக்கப்பட்டது',none:'இதுவரை பரிமாற்றம் இல்லை',cancel:'ரத்து',retry:'மீண்டும் முயற்சி',delete:'நீக்கு',login:'Telegram Bot வழியாக CloudBridge-ஐத் திறக்கவும்.',loading:'உங்கள் கணக்கு சரிபார்க்கப்படுகிறது…',ready:'பாதுகாப்பாக உள்நுழைந்தீர்கள்.',queued:'பரிமாற்றம் வரிசையில் சேர்க்கப்பட்டது.',error:'சிக்கல் ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.',confirm:'இந்த cloud கணக்கைத் துண்டிக்கவா?',confirmDelete:'இந்த job-ஐ வரலாற்றிலிருந்து நீக்கவா? needs_review என்றால் முதலில் சேருமிடத்தைச் சரிபார்க்கவும்.',sent:'கோரிக்கை அனுப்பப்பட்டது.'},
 si:{accounts:'සම්බන්ධිත ගිණුම්',refresh:'යාවත්කාලීන',oauthHelp:'ඔබගේම cloud ගිණුම සම්බන්ධ කරන්න. ගොනු ඔබගේ Telegram ගිණුමට පෞද්ගලිකයි.',transfer:'නව ගොනු හුවමාරුව',transferHelp:'HTTPS සබැඳියක් හෝ සම්බන්ධිත cloud ගොනුවක් භාවිතා කරන්න. Telegram ගොනුවකට පිළිතුරු දී /cloudpush dropbox /folder/file.pdf යවන්න.',source:'මූලාශ්‍රය',provider:'සේවාව',sourceRef:'HTTPS ගොනු සබැඳිය',sourceId:'Cloud ගොනු ID (Dropbox: /path/file)',destination:'ගමනාන්තය',path:'ගමනාන්ත මාර්ගය (/ සමඟ)',filename:'ගොනු නාමය',start:'හුවමාරුව පෝලිමට',jobs:'මගේ හුවමාරු',limits:'Cloud සහ Telegram සීමා අදාළයි. නැවත උත්සාහ කිරීමට පෙර බාධා වූ upload පරීක්ෂා කරන්න.',connect:'සම්බන්ධ කරන්න',disconnect:'විසන්ධි කරන්න',connected:'සම්බන්ධයි',none:'තවම හුවමාරු නැත',cancel:'අවලංගු',retry:'නැවත',delete:'මකන්න',login:'Telegram Bot තුළින් CloudBridge විවෘත කරන්න.',loading:'ගිණුම පරීක්ෂා කරමින්…',ready:'ආරක්ෂිතව පිවිසියා.',queued:'පෝලිමට එක් කළා.',error:'දෝෂයක් සිදු විය.',confirm:'ගිණුම විසන්ධි කරන්නද?',confirmDelete:'මෙම කාර්යය ඉතිහාසයෙන් මකන්නද? පළමුව ගමනාන්තය පරීක්ෂා කරන්න.',sent:'ඉල්ලීම යවන ලදි.'}
};
let lang='en',signed=false,timer=null;
const t=key=>(TEXT[lang]||TEXT.en)[key]||TEXT.en[key]||key;
function status(msg,error=false){$('status').textContent=msg;$('status').classList.toggle('error',error);}
function element(tag,klass,value){const el=document.createElement(tag);if(klass)el.className=klass;if(value!==undefined)el.textContent=String(value);return el;}
function translate(){document.documentElement.lang=lang;for(const e of document.querySelectorAll('[data-t]'))e.textContent=t(e.dataset.t);$('source-label').textContent=t($('source-kind').value==='url'?'sourceRef':'sourceId');}
async function api(path,method='GET',body){if(!tg?.initData)throw Error(t('login'));
 const options={method,cache:'no-store',headers:{'X-Telegram-Init-Data':tg.initData}};
 if(body!==undefined){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
 const response=await fetch('/cloud/api/'+path,options);const data=await response.json().catch(()=>({}));
 if(!response.ok||!data.ok)throw Error(data.error||('HTTP '+response.status));return data;}
function toggleFields(){const fromCloud=$('source-kind').value==='provider',toCloud=$('dest-kind').value==='provider';
 $('source-provider-wrap').hidden=!fromCloud;$('dest-provider-wrap').hidden=!toCloud;$('dest-path-wrap').hidden=!toCloud;
 $('source-ref').placeholder=fromCloud?'/path/file (Dropbox), or file ID':'https://example.org/document.pdf';
 $('source-label').textContent=t(fromCloud?'sourceId':'sourceRef');$('dest-path').required=toCloud;}
async function refresh(){try{const [a,j]=await Promise.all([api('accounts'),api('jobs')]);renderAccounts(a.accounts);renderJobs(j.jobs);status(t('ready'));}catch(err){status(err.message||t('error'),true);}}
function renderAccounts(accounts){const connected=new Set((accounts||[]).map(x=>x.provider));$('accounts').replaceChildren();
 for(const [key,name] of Object.entries(names)){
  const box=element('div','account');box.append(element('strong','',name));if(connected.has(key))box.append(element('span','connected',t('connected')));
  const button=element('button','',t(connected.has(key)?'disconnect':'connect'));button.type='button';
  button.addEventListener('click',async()=>{button.disabled=true;try{
   if(connected.has(key)){if(!confirm(t('confirm')))return;await api('accounts/'+key+'/disconnect','POST',{});await refresh();}
   else{const response=await api('oauth/'+key+'/start','POST',{});const url=new URL(response.url);
    if(url.protocol!=='https:')throw Error('Invalid provider URL');
    if(tg?.openLink)tg.openLink(url.href);else window.location.assign(url.href);
    status('Continue authorization in the provider page. Return and tap Refresh.');}
  }catch(err){status(err.message||t('error'),true);}finally{button.disabled=false;}});
  box.append(button);$('accounts').append(box);
 }}
function renderJobs(jobs){$('jobs').replaceChildren();$('job-count').textContent=String((jobs||[]).length);
 if(!jobs?.length){$('jobs').append(element('li','',t('none')));return;}
 for(const job of jobs){const li=element('li','job');const label=element('div');
  label.append(element('div','job-name',job.filename));
  let desc=String(job.status||'unknown')+' · '+String(job.bytes_done||0)+' bytes';if(job.error_code)desc+=' · '+job.error_code;
  label.append(element('span','job-status',desc));li.append(label);
  const action=(job.status==='queued'||job.status==='running')?'cancel':(job.status==='failed'?'retry':'delete');
  if(action){const button=element('button','job-action',t(action));button.type='button';button.addEventListener('click',async()=>{
   button.disabled=true;try{if(action==='delete'&&!confirm(t('confirmDelete')))return;await api('jobs/'+encodeURIComponent(job.id)+'/'+action,'POST',{});await refresh();}
   catch(err){status(err.message||t('error'),true);}finally{button.disabled=false;}});li.append(button);}
  $('jobs').append(li);
 }}
async function submit(event){event.preventDefault();const button=$('submit-transfer');button.disabled=true;
 try{const sk=$('source-kind').value,dk=$('dest-kind').value;
  const source={kind:sk,ref:$('source-ref').value.trim()};if(sk==='provider')source.provider=$('source-provider').value;
  const destination={kind:dk};if(dk==='provider'){destination.provider=$('dest-provider').value;destination.path=$('dest-path').value.trim();}
  await api('jobs','POST',{id:crypto.randomUUID(),source,destination,filename:$('filename').value.trim()});
  status(t('queued'));$('transfer-form').reset();toggleFields();await refresh();
 }catch(err){status(err.message||t('error'),true);}finally{button.disabled=false;}}
async function start(){const picker=$('language');picker.addEventListener('change',()=>{lang=picker.value;translate();});
 picker.value=lang;translate();$('source-kind').addEventListener('change',toggleFields);$('dest-kind').addEventListener('change',toggleFields);
 $('refresh').addEventListener('click',refresh);$('transfer-form').addEventListener('submit',submit);toggleFields();
 if(!tg?.initData){status(t('login'),true);$('transfer-form').querySelector('button[type=submit]').disabled=true;return;}
 tg.ready();status(t('loading'));try{await api('session');signed=true;await refresh();timer=setInterval(()=>{if(document.visibilityState==='visible'&&signed)refresh();},10000);}
 catch(err){status(err.message||t('login'),true);$('submit-transfer').disabled=true;}}
document.addEventListener('DOMContentLoaded',start);
})();

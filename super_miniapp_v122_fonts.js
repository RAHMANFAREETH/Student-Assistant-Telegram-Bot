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

/* V13 multi-font compatibility guide. Purely local UI; no uploads or APIs. */
(()=>{
 const select=document.getElementById('compat-font'),detail=document.getElementById('compat-detail'),preview=document.getElementById('compat-preview');
 if(!select||!detail||!preview)return;
 const unicode=new Set(['Noto Sans Tamil','Noto Serif Tamil','Latha','Nirmala UI','Vijaya']);
 const converted=new Set(['Bamini','SunTommy']);
 const copy={
  en:{unicode:'Unicode Tamil: no text encoding conversion needed. This font is for visual styling. PDF export uses the fonts installed on the server.',
      mapped:'Legacy Tamil: text conversion to/from Unicode is implemented in the Font converter. The actual matching font must be installed to display a PDF correctly.',
      legacy:'Legacy Tamil: document rendering can be protected by matching-font checks. A verified text conversion mapping is not implemented here. Do not use the Bamini mapping for this font.',
      preview:'Unicode font preview',notpreview:'Legacy text is not a Unicode font preview. The sample below stays in Unicode.',
      title:'Tamil font compatibility',intro:'Unicode fonts change appearance. Legacy fonts have separate character encodings; conversion needs a verified mapping.',
      label:'Choose a font',hint:'The browser may substitute a font if the chosen family is not installed. This preview does not confirm a font is available on Render.',
      office:'DOCX / PPTX → PDF requirements',officeText:'For a legacy DOCX/PPTX, the exact licensed font must be installed on the Render server. Windows-installed fonts do not transfer automatically. Missing fonts are reported instead of generating a misleading PDF.'},
  ta:{unicode:'Unicode தமிழ் எழுத்துரு: எழுத்துக் குறியீட்டு மாற்றம் தேவையில்லை. இது தோற்றத்தை மட்டும் மாற்றும்.',
      mapped:'பழைய தமிழ் குறியீடு: Unicode ↔ இந்த வடிவத்திற்கு மாற்றும் வசதி Font converter-இல் உள்ளது. PDF-க்கு பொருத்தமான எழுத்துரு தேவை.',
      legacy:'பழைய தமிழ் எழுத்துரு: PDF உருவாக்கும்போது அதன் உண்மையான எழுத்துரு தேவை. இங்கே சரிபார்க்கப்பட்ட உரை மாற்றும் வரைபடம் இல்லை. Bamini மாற்றத்தைப் பயன்படுத்த வேண்டாம்.',
      preview:'Unicode எழுத்துரு முன்னோட்டம்',notpreview:'இது Unicode மாதிரி மட்டும்; பழைய குறியீட்டு உரை முன்னோட்டம் இல்லை.',
      title:'தமிழ் எழுத்துரு இணக்கத்தன்மை',intro:'Unicode எழுத்துருக்கள் தோற்றத்தை மாற்றும். பழைய எழுத்துருக்களின் குறியீட்டு முறைகள் வேறுபடும்.',
      label:'எழுத்துருவைத் தேர்வு செய்க',hint:'எழுத்துரு இல்லையெனில் browser மாற்று எழுத்துருவைப் பயன்படுத்தலாம். Render-இல் நிறுவப்பட்டுள்ளதற்கான ஆதாரம் அல்ல.',
      office:'DOCX / PPTX → PDF தேவைகள்',officeText:'பழைய DOCX/PPTX கோப்புக்கு பொருத்தமான உரிமம் பெற்ற எழுத்துரு Render server-இல் இருக்க வேண்டும். Windows-இல் இருப்பது போதாது. இல்லாவிட்டால் PDF-க்கு முன் எச்சரிக்கை வழங்கப்படும்.'},
  si:{unicode:'Unicode දෙමළ අකුරු: අක්ෂර කේත පරිවර්තනයක් අවශ්‍ය නැත. පෙනුම පමණක් වෙනස් වේ.',
      mapped:'පැරණි දෙමළ කේතනය: Unicode සමඟ පෙළ පරිවර්තනය Font converter තුළ තිබේ. PDF සඳහා නිවැරදි අකුරු අවශ්‍ය වේ.',
      legacy:'පැරණි දෙමළ අකුරු: PDF සඳහා ගැළපෙන අකුරු අවශ්‍ය වේ. මෙම කේතනය සඳහා තහවුරු කළ පරිවර්තන සිතියමක් නොමැත. Bamini පරිවර්තනය භාවිතා නොකරන්න.',
      preview:'Unicode අකුරු පෙරදසුන',notpreview:'මෙය Unicode නියැදියක් පමණි.',
      title:'දෙමළ අකුරු අනුකූලතාව',intro:'Unicode අකුරු පෙනුම වෙනස් කරයි. පැරණි කේතන වෙන වෙනම වේ.',
      label:'අකුරු තෝරන්න',hint:'තෝරාගත් අකුරු නොමැති නම් browser වෙනත් අකුරු භාවිතා කළ හැක. Render සර්වරය සඳහා මෙය සාක්ෂියක් නොවේ.',
      office:'DOCX / PPTX → PDF අවශ්‍යතා',officeText:'පැරණි DOCX/PPTX සඳහා නිවැරදි බලපත්‍ර සහිත අකුරු Render සර්වරයේ ස්ථාපනය කළ යුතුය. Windows හි තිබීම පමණක් ප්‍රමාණවත් නැත.'}
 };
 function refresh(){
  const lang=document.getElementById('v13-studio-language')?.value||'en',t=copy[lang]||copy.en,name=select.value;
  document.getElementById('compat-title').textContent=t.title;
  document.getElementById('compat-intro').textContent=t.intro;
  document.getElementById('compat-select-label').textContent=t.label;
  document.getElementById('compat-preview-label').textContent=t.preview;
  document.getElementById('compat-hint').textContent=t.hint;
  document.getElementById('compat-office-summary').textContent=t.office;
  document.getElementById('compat-office-message').textContent=t.officeText;
  document.getElementById('compat-tab').textContent=lang==='ta'?'🅰️ எழுத்துரு வழிகாட்டி':lang==='si'?'🅰️ අකුරු මාර්ගෝපදේශය':'🅰️ Font guide';
  detail.textContent=name+' — '+(unicode.has(name)?t.unicode:converted.has(name)?t.mapped:t.legacy);
  // Only Unicode fonts can be previewed with Unicode Tamil text.
  preview.style.fontFamily=unicode.has(name)?'"'+name.replaceAll('"','')+'",sans-serif':'sans-serif';
  preview.setAttribute('aria-label',name+' '+(unicode.has(name)?t.preview:t.notpreview));
 }
 select.addEventListener('change',refresh);
 document.getElementById('v13-studio-language')?.addEventListener('change',refresh);
 refresh();
})();


/* V13 FOUR LANGUAGE FONT STUDIO; local Unicode text operations only. */
(()=>{
 const $=id=>document.getElementById(id);
 const lang=$('ms-language'),font=$('ms-font'),input=$('ms-input'),preview=$('ms-preview'),status=$('ms-status');
 if(!lang||!font||!input||!preview||!status)return;
 const samples={ta:'வணக்கம்! தமிழ் மாணவர்களுக்கு உதவி.',en:'Welcome! Student Assistant helps you learn.',ar:'مرحباً بكم في مساعد الطلاب. العلم نور.',si:'ආයුබෝවන්! සිසුන් සඳහා අධ්‍යාපන සහාය.'};
 const fonts={
  ta:['Noto Sans Tamil','Noto Serif Tamil','Noto Sans Tamil UI','Latha','Nirmala UI','Vijaya'],
  en:['Noto Sans','Noto Serif','Liberation Sans','Liberation Serif','Arial','Times New Roman'],
  ar:['Noto Naskh Arabic','Noto Sans Arabic','Noto Kufi Arabic','Noto Naskh Arabic UI','Amiri','Traditional Arabic'],
  si:['Noto Sans Sinhala','Noto Serif Sinhala','Noto Sans Sinhala UI','Iskoola Pota','Malithi Web']
 };
 const i18n={
  en:{tab:'🌍 Four languages',title:'Four-language Writing Studio',intro:'Preview Unicode fonts for Tamil, English, Arabic and Sinhala. Text stays on this device; this does not convert legacy encodings.',lang:'Writing language',font:'Unicode font',input:'Your text',preview:'Live preview',copy:'Copy text',download:'Download UTF-8 .txt',normalize:'Normalize Unicode (NFC)',sample:'Sample',important:'Important: Office PDF font compatibility',office:'For PDF conversion, Unicode font support depends on fonts installed on Render. Legacy Tamil/Sinhala documents need their original licensed fonts; Arabic needs correct right-to-left shaping. A browser preview does not prove PDF output.',info:'Font availability on Render is not verified by this browser preview.',copied:'Copied text.',failure:'Clipboard is unavailable. Select and copy the text manually.',normalized:'Applied NFC normalization; compare before replacing your original.',characters:'Unicode code points'},
  ta:{tab:'🌍 நான்கு மொழிகள்',title:'நான்கு மொழி எழுத்து அரங்கு',intro:'தமிழ், ஆங்கிலம், அரபு, சிங்களம் ஆகிய மொழிகளுக்கான Unicode எழுத்துரு முன்னோட்டம். உரை உங்கள் சாதனத்திலேயே இருக்கும்.',lang:'எழுத்து மொழி',font:'Unicode எழுத்துரு',input:'உங்கள் உரை',preview:'முன்னோட்டம்',copy:'உரையை நகலெடு',download:'UTF-8 .txt பதிவிறக்கு',normalize:'Unicode NFC சீரமைப்பு',sample:'மாதிரி',important:'DOCX / PDF எழுத்துரு குறிப்பு',office:'PDF மாற்றத்திற்கு Render சேவையகத்தில் சரியான Unicode எழுத்துரு தேவை. பழைய தமிழ்/சிங்கள எழுத்துருக்கள் தனித்த குறியீட்டைப் பயன்படுத்தலாம். அரபு வலமிருந்து இடமாகக் காட்டப்பட வேண்டும்.',info:'இந்த முன்னோட்டம் Render-இல் எழுத்துரு இருப்பதற்கான உறுதி அல்ல.',copied:'உரை நகலெடுக்கப்பட்டது.',failure:'நகலெடுக்க முடியவில்லை; உரையைத் தேர்ந்து நகலெடுக்கவும்.',normalized:'NFC சீரமைக்கப்பட்டது; பழைய உரையுடன் ஒப்பிடவும்.',characters:'Unicode குறியிடங்கள்'},
  ar:{tab:'🌍 أربع لغات',title:'استوديو الكتابة بأربع لغات',intro:'معاينة خطوط يونيكود للتاميلية والإنجليزية والعربية والسنهالية. يبقى النص على جهازك.',lang:'لغة الكتابة',font:'خط يونيكود',input:'النص',preview:'معاينة مباشرة',copy:'نسخ النص',download:'تنزيل نص UTF-8',normalize:'توحيد يونيكود NFC',sample:'نموذج',important:'ملاحظات خطوط PDF',office:'تحتاج ملفات PDF إلى الخطوط المناسبة على خادم Render. النصوص القديمة المكتوبة بترميز خاص تحتاج الخط الأصلي. يجب الحفاظ على اتجاه العربية من اليمين إلى اليسار واتصال الحروف.',info:'المعاينة لا تؤكد توفر الخط على خادم Render.',copied:'تم نسخ النص.',failure:'الحافظة غير متاحة. حدد النص وانسخه يدوياً.',normalized:'تم تطبيق NFC؛ راجع النص الأصلي.',characters:'نقاط يونيكود'},
  si:{tab:'🌍 භාෂා හතරක්',title:'භාෂා හතරක ලේඛන චිත්‍රාගාරය',intro:'දෙමළ, ඉංග්‍රීසි, අරාබි සහ සිංහල Unicode අකුරු පෙරදසුන් බලන්න. පෙළ ඔබේ උපාංගයේම පවතී.',lang:'ලියන භාෂාව',font:'Unicode අකුරු',input:'ඔබගේ පෙළ',preview:'සජීවී පෙරදසුන',copy:'පෙළ පිටපත් කරන්න',download:'UTF-8 .txt බාගන්න',normalize:'Unicode NFC සාමාන්‍යකරණය',sample:'උදාහරණය',important:'Office PDF අකුරු අවශ්‍යතා',office:'PDF නිර්මාණය සඳහා Render සේවාදායකයේ සුදුසු Unicode අකුරු අවශ්‍ය වේ. පැරණි දෙමළ/සිංහල කේතන සඳහා ඒවායේ මුල් අකුරු අවශ්‍ය වේ. අරාබි පෙළ දකුණෙන් වමට නිසි ලෙස හැඩ ගැසිය යුතුය.',info:'මෙම පෙරදසුන Render සේවාදායකයේ අකුරු තිබෙන බව සහතික නොකරයි.',copied:'පෙළ පිටපත් විය.',failure:'පිටපත් කිරීමට නොහැක; පෙළ තෝරා පිටපත් කරන්න.',normalized:'NFC යෙදී ඇත; මුල් පෙළ හා සසඳන්න.',characters:'Unicode අක්ෂර'}
 };
 let lastAuto=samples.ta;
 function statusMessage(message){status.textContent=message;}
 function refreshLabels(){
  const ui=i18n[$('v13-studio-language')?.value]||i18n.en;
  for(const [id,key] of [['ms-title','title'],['ms-intro','intro'],['ms-language-label','lang'],['ms-font-label','font'],['ms-input-label','input'],['ms-preview-label','preview'],['ms-copy','copy'],['ms-download','download'],['ms-normalize','normalize'],['ms-reset','sample'],['ms-important','important'],['ms-office-info','office'],['multiscript-tab','tab']]){
   const e=$(id);if(e)e.textContent=ui[key];
  }
  statusMessage(ui.info);
  render();
 }
 function render(){
  const current=lang.value,selected=font.value;
  preview.textContent=input.value;
  preview.style.fontFamily='"'+selected.replaceAll('"','')+'",'+(current==='ar'?'serif':'sans-serif');
  preview.setAttribute('lang',current);
  preview.setAttribute('dir',current==='ar'?'rtl':'ltr');
  input.setAttribute('lang',current);
  input.setAttribute('dir',current==='ar'?'rtl':'auto');
  $('ms-count').textContent=Array.from(input.value).length+' '+(i18n[$('v13-studio-language')?.value]||i18n.en).characters;
 }
 function chooseLanguage(){
  const old=font.value;
  font.replaceChildren();
  for(const name of fonts[lang.value]){
   const option=document.createElement('option');option.value=name;option.textContent=name;font.append(option);
  }
  if(fonts[lang.value].includes(old))font.value=old;
  if(input.value===''||input.value===lastAuto){input.value=samples[lang.value];lastAuto=input.value;}
  render();
 }
 function download(){
  const blob=new Blob(['\ufeff',input.value],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),anchor=document.createElement('a');
  anchor.href=url;anchor.download='student-assistant-'+lang.value+'-unicode.txt';document.body.appendChild(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
 }
 $('ms-copy').addEventListener('click',async()=>{
  const ui=i18n[$('v13-studio-language')?.value]||i18n.en;
  try{if(!navigator.clipboard?.writeText)throw Error();await navigator.clipboard.writeText(input.value);statusMessage(ui.copied);}
  catch{statusMessage(ui.failure);}
 });
 $('ms-download').addEventListener('click',download);
 $('ms-normalize').addEventListener('click',()=>{input.value=input.value.normalize('NFC');render();statusMessage((i18n[$('v13-studio-language')?.value]||i18n.en).normalized);});
 $('ms-reset').addEventListener('click',()=>{input.value=samples[lang.value];lastAuto=input.value;render();});
 lang.addEventListener('change',chooseLanguage);
 font.addEventListener('change',render);
 input.addEventListener('input',render);
 $('v13-studio-language')?.addEventListener('change',refreshLabels);
 chooseLanguage();refreshLabels();
 // Arabic interface uses the same language picker, but text-conversion mode
 // remains Unicode ↔ Bamini ↔ SunTommy only. No speculative mappings.
 const ARABIC_LABELS={
  'Font & Writing Studio':'استوديو الخطوط والكتابة','🔄 Font converter':'🔄 محول الخطوط',
  '🧹 Text cleaner':'🧹 تنظيف النص','🔎 Unicode inspector':'🔎 فاحص يونيكود',
  '🔢 Tamil digits':'🔢 الأرقام التاميلية','🅰️ Font guide':'🅰️ دليل الخطوط',
  'Input text':'النص المدخل','Converted result':'النص الناتج','Copy result':'نسخ النتيجة',
  'Download .txt':'تنزيل ملف نصي','Clear':'مسح','Sample':'نموذج',
  'From':'من','To':'إلى','Unicode font preview':'معاينة خط يونيكود',
  'Choose a font':'اختر خطاً','Direction':'الاتجاه','Text to clean':'النص المراد تنظيفه',
  'Clean text':'النص المنظّف','Text to inspect':'النص للفحص','Copy report':'نسخ التقرير',
  'Copy clean text':'نسخ النص المنظف','Copy':'نسخ'
 };
 const originals=[];
 for(const e of document.querySelectorAll('h1,h2,summary,button,label')){
  if(e.closest('#multiscript'))continue;
  for(const node of e.childNodes){
   if(node.nodeType===Node.TEXT_NODE){
    const key=node.textContent.trim();
    if(Object.hasOwn(ARABIC_LABELS,key))originals.push([node,key]);
   }
  }
 }
 $('v13-studio-language')?.addEventListener('change',event=>{
  const ar=event.target.value==='ar';
  document.documentElement.dir=ar?'rtl':'ltr';
  if(ar){for(const [node,key] of originals)node.textContent=ARABIC_LABELS[key];}
 });
})();


/* V13 FONT LIBRARY 80: Unicode font preference only; no uploads or font downloads. */
(()=>{
 'use strict';
 const DATA={"schema":1,"disclaimer":"Font names are selections only; exact display and PDF rendering require the font installed on the correct device/server. No font binaries are bundled.","fonts":[{"language":"ta","name":"Latha","category":"academic","source":"system","kind":"unicode"},{"language":"ta","name":"Vijaya","category":"academic","source":"system","kind":"unicode"},{"language":"ta","name":"Nirmala UI","category":"academic","source":"system","kind":"unicode"},{"language":"ta","name":"Noto Serif Tamil","category":"academic","source":"external","kind":"unicode"},{"language":"ta","name":"Tiro Tamil","category":"academic","source":"external","kind":"unicode"},{"language":"ta","name":"Noto Sans Tamil","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Noto Sans Tamil UI","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Catamaran","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Hind Madurai","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Mukta Malar","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Anek Tamil","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Arima","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Pavanam","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Meera Inimai","category":"modern","source":"external","kind":"unicode"},{"language":"ta","name":"Baloo Thambi 2","category":"display","source":"external","kind":"unicode"},{"language":"ta","name":"Kavivanar","category":"display","source":"external","kind":"unicode"},{"language":"ta","name":"Coiny","category":"display","source":"external","kind":"unicode"},{"language":"ta","name":"Oi","category":"display","source":"external","kind":"unicode"},{"language":"en","name":"Times New Roman","category":"academic","source":"system","kind":"unicode"},{"language":"en","name":"Cambria","category":"academic","source":"system","kind":"unicode"},{"language":"en","name":"Georgia","category":"academic","source":"system","kind":"unicode"},{"language":"en","name":"Garamond","category":"academic","source":"system","kind":"unicode"},{"language":"en","name":"Book Antiqua","category":"academic","source":"system","kind":"unicode"},{"language":"en","name":"Noto Serif","category":"academic","source":"external","kind":"unicode"},{"language":"en","name":"EB Garamond","category":"academic","source":"external","kind":"unicode"},{"language":"en","name":"Merriweather","category":"academic","source":"external","kind":"unicode"},{"language":"en","name":"Source Serif 4","category":"academic","source":"external","kind":"unicode"},{"language":"en","name":"Liberation Serif","category":"academic","source":"external","kind":"unicode"},{"language":"en","name":"Caladea","category":"academic","source":"external","kind":"unicode"},{"language":"en","name":"Arial","category":"modern","source":"system","kind":"unicode"},{"language":"en","name":"Calibri","category":"modern","source":"system","kind":"unicode"},{"language":"en","name":"Aptos","category":"modern","source":"system","kind":"unicode"},{"language":"en","name":"Segoe UI","category":"modern","source":"system","kind":"unicode"},{"language":"en","name":"Verdana","category":"modern","source":"system","kind":"unicode"},{"language":"en","name":"Tahoma","category":"modern","source":"system","kind":"unicode"},{"language":"en","name":"Noto Sans","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Liberation Sans","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Carlito","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Lato","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Inter","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Roboto","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Open Sans","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Montserrat","category":"modern","source":"external","kind":"unicode"},{"language":"en","name":"Source Sans 3","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Sakkal Majalla","category":"academic","source":"system","kind":"unicode"},{"language":"ar","name":"Traditional Arabic","category":"academic","source":"system","kind":"unicode"},{"language":"ar","name":"Arabic Typesetting","category":"academic","source":"system","kind":"unicode"},{"language":"ar","name":"Simplified Arabic","category":"academic","source":"system","kind":"unicode"},{"language":"ar","name":"Noto Naskh Arabic","category":"academic","source":"external","kind":"unicode"},{"language":"ar","name":"Amiri","category":"academic","source":"external","kind":"unicode"},{"language":"ar","name":"Scheherazade New","category":"academic","source":"external","kind":"unicode"},{"language":"ar","name":"Lateef","category":"academic","source":"external","kind":"unicode"},{"language":"ar","name":"Noto Naskh Arabic UI","category":"academic","source":"external","kind":"unicode"},{"language":"ar","name":"Andalus","category":"academic","source":"system","kind":"unicode"},{"language":"ar","name":"Aldhabi","category":"academic","source":"system","kind":"unicode"},{"language":"ar","name":"Noto Sans Arabic","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Noto Kufi Arabic","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Cairo","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Tajawal","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Almarai","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Changa","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"El Messiri","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Markazi Text","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Reem Kufi","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"IBM Plex Sans Arabic","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Readex Pro","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Mada","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Harmattan","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Aref Ruqaa","category":"modern","source":"external","kind":"unicode"},{"language":"ar","name":"Mirza","category":"modern","source":"external","kind":"unicode"},{"language":"si","name":"Iskoola Pota","category":"academic","source":"system","kind":"unicode"},{"language":"si","name":"Noto Serif Sinhala","category":"academic","source":"external","kind":"unicode"},{"language":"si","name":"Abhaya Libre","category":"academic","source":"external","kind":"unicode"},{"language":"si","name":"Malithi Web","category":"academic","source":"external","kind":"unicode"},{"language":"si","name":"Bhashita","category":"academic","source":"external","kind":"unicode"},{"language":"si","name":"Noto Sans Sinhala","category":"modern","source":"external","kind":"unicode"},{"language":"si","name":"Noto Sans Sinhala UI","category":"modern","source":"external","kind":"unicode"},{"language":"si","name":"Yaldevi","category":"modern","source":"external","kind":"unicode"},{"language":"si","name":"Gemunu Libre","category":"modern","source":"external","kind":"unicode"},{"language":"si","name":"Maname","category":"modern","source":"external","kind":"unicode"}],"legacy":{"ta":["Bamini","Baamini","SunTommy","Kalaham","Tharmini","Vanavil","Senthamil","TSCII","TAB","TAM","Anjal","Amudham","Shree Lipi","Suratha","Elango"],"si":["FM Abhaya","FM Malithi","FM Bindumathi","FM Derana","DL Manel","DL Araliya","DL Champika","DL Divani","Kaputa","Thibus29STru"]},"priority_exact_pdf":["Sakkal Majalla","Arabic Typesetting","Traditional Arabic","Iskoola Pota"],"samples":{"ta":"தமிழ் மொழி · கல்வி நம் எதிர்காலம்","en":"Education opens doors. 2026","ar":"بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ · العِلْمُ نُورٌ","si":"සිංහල භාෂාව · අධ්‍යාපනය අපේ අනාගතයයි"}};
 const $=id=>document.getElementById(id);
 const lang=$('ms-language'), font=$('ms-font'),filter=$('v130-font-filter'),search=$('v130-font-search');
 const counter=$('v130-font-count'),info=$('v130-font-info'),legacy=$('v130-legacy-tags');
 if(!lang||!font||!filter||!search||!counter||!info||!legacy)return;
 const words={
  en:{style:'Style',search:'Find font',all:'All styles',academic:'Academic / classic',modern:'Modern',display:'Decorative',matches:'font choices',none:'No matching fonts',guide:'Legacy-font guide (not Unicode preview)',legacy:'Legacy encodings need matching fonts. Only Bamini and SunTommy have verified conversion mappings in the current Studio.',note:'Font preference only. The browser may substitute another font. Exact PDF output requires the licensed font on the server.',priority:'This font is commonly installed with Microsoft products; it is NOT bundled for server use.'},
  ta:{style:'எழுத்துரு வகை',search:'எழுத்துரு தேடல்',all:'அனைத்து வகைகள்',academic:'கல்வி / பாரம்பரியம்',modern:'நவீனம்',display:'அலங்காரம்',matches:'எழுத்துருக்கள்',none:'எழுத்துருக்கள் இல்லை',guide:'பழைய குறியீட்டு எழுத்துருக்கள்',legacy:'பழைய எழுத்துருக்களுக்கு அதே எழுத்துரு தேவை. தற்போது Bamini, SunTommy மாற்றங்கள் மட்டுமே சரிபார்க்கப்பட்டுள்ளன.',note:'இது முன்னோட்டம் மட்டுமே. சரியான PDF-க்கு சேவையகத்தில் உரிமம் பெற்ற எழுத்துரு இருக்க வேண்டும்.',priority:'இந்த Microsoft எழுத்துரு இங்கு வழங்கப்படவில்லை.'},
  ar:{style:'نوع الخط',search:'بحث عن خط',all:'جميع الأنواع',academic:'أكاديمي / كلاسيكي',modern:'حديث',display:'زخرفي',matches:'خطوط',none:'لا توجد خطوط مطابقة',guide:'خطوط الترميز القديمة',legacy:'الخطوط القديمة تحتاج ملفاتها الأصلية؛ التحويل المؤكد متاح فقط لباميني وسن تومي.',note:'المعاينة اختيار خط فقط وقد يستخدم المتصفح بديلاً. PDF يتطلب الخط المرخّص على الخادم.',priority:'هذا الخط مرفق عادة مع منتجات Microsoft وليس مضمنًا للتوزيع.'},
  si:{style:'අකුරු වර්ගය',search:'අකුරු සොයන්න',all:'සියලු වර්ග',academic:'අධ්‍යාපන / සාම්ප්‍රදායික',modern:'නවීන',display:'අලංකාර',matches:'අකුරු',none:'ගැළපෙන අකුරු නැත',guide:'පැරණි අකුරු',legacy:'පැරණි අකුරු සඳහා එම අකුරු ගොනුව අවශ්‍ය වේ. අනුමාන කර අකුරු පරිවර්තනය නොකරයි.',note:'මෙය පෙරදසුනක් පමණි. PDF සේවාදායකයේ නිසි බලපත්‍ර අකුරු අවශ්‍යය.',priority:'Microsoft අකුරු මෙම පැකේජයේ අඩංගු නොවේ.'}
 };
 function uiLang(){const v=$('v13-studio-language')?.value;return words[v]?v:'en';}
 function localize(){
  const w=words[uiLang()];
  for(const [id,value] of [['v130-font-filter-label',w.style],['v130-font-search-label',w.search],['v130-legacy-heading',w.guide],['v130-legacy-info',w.legacy]]){
   const e=$(id);if(!e)continue;
   if(e.tagName==='LABEL'){for(const node of e.childNodes){if(node.nodeType===3){node.textContent=value;break;}}}
   else e.textContent=value;
  }
  for(const opt of filter.options){opt.textContent=w[opt.value]||opt.textContent;}
  search.placeholder=w.search;
 }
 function update(){
  const code=lang.value;const chosen=font.value;
  const name=search.value.trim().toLocaleLowerCase();
  const results=DATA.fonts.filter(entry=>entry.language===code &&
   (filter.value==='all'||entry.category===filter.value) &&
   (!name||entry.name.toLocaleLowerCase().includes(name)));
  font.replaceChildren();
  const w=words[uiLang()];
  if(!results.length){
   const option=document.createElement('option');option.value='';option.textContent=w.none;font.append(option);
   font.disabled=true;
  }else{
   font.disabled=false;
   for(const entry of results){
    const opt=document.createElement('option');opt.value=entry.name;opt.textContent=entry.name;
    font.add(opt);
   }
   font.value=results.some(entry=>entry.name===chosen)?chosen:results[0].name;
  }
  counter.textContent=`${results.length} ${w.matches} · ${code.toUpperCase()}`;
  const selected=results.find(x=>x.name===font.value);
  info.textContent=w.note + (selected?.source==='system'?' '+w.priority:'');
  legacy.replaceChildren();
  for(const n of DATA.legacy[code]||[]){
   const span=document.createElement('span');span.textContent=n;legacy.append(span);
  }
  font.dispatchEvent(new Event('change',{bubbles:false}));
 }
 lang.addEventListener('change',()=>{search.value='';filter.value='all';localize();update();});
 filter.addEventListener('change',update);
 search.addEventListener('input',update);
 font.addEventListener('change',()=>{
  const selected=DATA.fonts.find(x=>x.language===lang.value&&x.name===font.value);
  const w=words[uiLang()];info.textContent=w.note+(selected?.source==='system'?' '+w.priority:'');
 });
 $('v13-studio-language')?.addEventListener('change',()=>{localize();update();});
 localize();update();
})();

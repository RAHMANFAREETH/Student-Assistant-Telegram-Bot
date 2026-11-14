/** V13.1 local-only four-language legacy conversion panel. No server text upload. */
import { convertTamilFont } from '/app/assets/fontstudio.mjs';
import {decodeTextFile,encodeTextFile,transcodeTextFile,convertSinhalaText,validateSinhalaProfile,tamilConvert,LEGACY4_CODEPAGES} from '/app/assets/legacy4-core.mjs';
const $=id=>document.getElementById(id);
const L={
 ta:[['Unicode','Unicode'],['Bamini','Bamini'],['SunTommy','SunTommy']],
 si:[['Unicode','Unicode'],['Legacy','Verified Sinhala mapping']],
 ar:[['utf-8','Unicode (UTF-8)'],['windows-1256','Windows-1256'],['iso-8859-6','ISO-8859-6']],
 en:[['utf-8','Unicode (UTF-8)'],['windows-1252','Windows-1252'],['macintosh','Mac Roman']]
};
let sourceFile=null,sinhalaProfile=null,lastBytes=null;
function status(msg,error=false){const el=$('legacy4-status');el.textContent=msg;el.classList.toggle('error',error);}
function putOptions(el,options){el.replaceChildren(...options.map(([value,label])=>{const opt=document.createElement('option');opt.value=value;opt.textContent=label;return opt;}));}
function update(){
 const lang=$('legacy4-language').value,options=L[lang];putOptions($('legacy4-from'),options);putOptions($('legacy4-to'),options);
 $('legacy4-to').selectedIndex=lang==='ta'?1:lang==='si'?0:lang==='ar'?0:0;
 $('legacy4-file-label').hidden=lang==='ta'||lang==='si';$('legacy4-profile-label').hidden=lang!=='si';
 $('legacy4-help').textContent=lang==='ta'?'Uses existing Unicode/Bamini/SunTommy converter.':
 lang==='si'?'Choose a verified font-specific Sinhala mapping JSON. Font name alone is not enough; no mapping is bundled.':
 'Legacy encodings here are byte formats, not font shapes. To read legacy text, upload its ORIGINAL .txt file; Unicode to legacy creates encoded .txt bytes.';
 $('legacy4-input').value='';$('legacy4-output').value='';sourceFile=null;lastBytes=null;status('No text is uploaded to the server.');
}
function bytesDownload(bytes,name){
 const blob=new Blob([bytes],{type:'application/octet-stream'}),url=URL.createObjectURL(blob),a=document.createElement('a');
 a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
}
function result(){
 const lang=$('legacy4-language').value,from=$('legacy4-from').value,to=$('legacy4-to').value,input=$('legacy4-input').value;
 try{
  lastBytes=null;
  if(lang==='ta'){
   $('legacy4-output').value=tamilConvert(input,from,to,convertTamilFont);
  }else if(lang==='si'){
   if(!sinhalaProfile)throw Error('Load a verified Sinhala legacy font mapping JSON first.');
   $('legacy4-output').value=convertSinhalaText(input,sinhalaProfile,from,to);
  }else{
   if(from!=='utf-8'&&!sourceFile)throw Error('For legacy source encoding, upload its original .txt bytes. Pasted mojibake is not reliable.');
   let text;
   if(from==='utf-8')text=input;
   else text=decodeTextFile(sourceFile,lang,from);
   if(to==='utf-8'){$('legacy4-output').value=text;}
   else{
    lastBytes=encodeTextFile(text,lang,to);$('legacy4-output').value=text;
    status('Converted bytes ready. The preview shows Unicode text; use Download to obtain encoded legacy .txt.');return;
   }
  }
  status('Converted locally. Review accuracy against the original document.');
 }catch(e){lastBytes=null;$('legacy4-output').value='';status(e.message||'Conversion failed.',true);}
}
function init(){
 if(!$('legacy4-language'))return;
 $('legacy4-language').addEventListener('change',update);
 $('legacy4-file').addEventListener('change',async e=>{
  const f=e.target.files?.[0];sourceFile=null;if(!f)return;
  try{if(f.size>200000)throw Error('Choose a .txt file smaller than 200 KB.');sourceFile=new Uint8Array(await f.arrayBuffer());status(`Loaded ${f.name} locally (${f.size} bytes).`);}catch(err){status(err.message,true);}
 });
 $('legacy4-profile').addEventListener('change',async e=>{
  const f=e.target.files?.[0];sinhalaProfile=null;if(!f)return;
  try{if(f.size>100000)throw Error('Mapping JSON must be under 100 KB.');const raw=JSON.parse(await f.text());const validated=validateSinhalaProfile(raw);sinhalaProfile=raw;status(`Loaded profile: ${validated.name}. Conversion quality still depends on the mapping.`);}catch(err){status(err.message,true);}
 });
 $('legacy4-convert').addEventListener('click',result);
 $('legacy4-download').addEventListener('click',()=>{
  if(lastBytes){bytesDownload(lastBytes,'converted-legacy.txt');return;}
  const output=$('legacy4-output').value;
  if(!output){status('Convert text first.',true);return;}
  bytesDownload(new TextEncoder().encode(output),'converted-unicode.txt');
 });
 $('legacy4-copy').addEventListener('click',async()=>{
  if(lastBytes){status('Download the encoded file: raw bytes cannot be copied safely as Unicode text.',true);return;}
  if(!$('legacy4-output').value){status('Convert text first.',true);return;}
  try{await navigator.clipboard.writeText($('legacy4-output').value);status('Unicode result copied.');}catch{status('Clipboard unavailable. Select and copy the output manually.',true);}
 });
 update();
}
// DOM exists before this deferred module executes; panel remains gated by existing /app session.
init();

import {FONT_NAMES,checkProfileFile,convertProfile} from '/app/assets/verified-profiles-v133.mjs';
const $=id=>document.getElementById(id);let imported=null;
function status(message,error=false){const el=$('v133-status');el.textContent=message;el.classList.toggle('error',error);}
function setOptions(){const lang=$('v133-lang').value;const el=$('v133-font');el.replaceChildren();for(const name of FONT_NAMES[lang]){const o=document.createElement('option');o.value=name;o.textContent=name+' · mapping required';el.append(o);}imported=null;$('v133-output').value='';status('Select and import a reviewed mapping JSON for the exact font.');}
function download(text){const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='converted-verified-legacy.txt';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);}
function init(){if(!$('v133-lang'))return;
 $('v133-lang').addEventListener('change',setOptions);
 $('v133-profile').addEventListener('change',async e=>{imported=null;const f=e.target.files?.[0];if(!f)return;try{if(f.size>400000)throw Error('Mapping JSON too large.');const raw=JSON.parse(await f.text());const p=checkProfileFile(JSON.stringify(raw));if(p.language!==$('v133-lang').value||p.font.toLowerCase()!==$('v133-font').value.toLowerCase())throw Error('Mapping language or font name does not match your selection.');imported=raw;status(`Profile loaded: ${p.font}, ${p.entryCount} sequences, ${p.verifiedSamples} embedded examples passed. Independently confirm the mapping source and license: ${p.source}`);}catch(error){status(error.message,true);}});
 $('v133-convert').addEventListener('click',()=>{try{if(!imported)throw Error('Import a verified mapping before conversion.');$('v133-output').value=convertProfile($('v133-input').value,imported,$('v133-from').value,$('v133-to').value);status('Conversion completed locally. Compare against the original document.');}catch(error){$('v133-output').value='';status(error.message,true);}});
 $('v133-copy').addEventListener('click',async()=>{try{if(!$('v133-output').value)throw Error('Nothing to copy.');await navigator.clipboard.writeText($('v133-output').value);status('Result copied.');}catch(e){status(e.message,true);}});
 $('v133-download').addEventListener('click',()=>{if(!$('v133-output').value){status('Convert text first.',true);return;}download($('v133-output').value);});
 setOptions();}
init();

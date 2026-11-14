/**
 * V13.1 local-only legacy converter primitives.
 * Tamil reuses the existing, separately tested Bamini/SunTommy conversion.
 * Sinhala legacy font profiles are explicit JSON glyph maps; never guess one.
 * Arabic/English convert real BYTE encodings, not proprietary glyph fonts.
 * No network, no telemetry, no font binaries, no file persistence.
 */
export const LEGACY4_CODEPAGES = Object.freeze({
  ar: Object.freeze(['utf-8','windows-1256','iso-8859-6']),
  en: Object.freeze(['utf-8','windows-1252','macintosh']),
});
export const LEGACY4_TAMIL = Object.freeze(['Unicode','Bamini','SunTommy']);
export const LEGACY4_MAX_TEXT = 120000;
export function assertText(s){
 if(typeof s!=='string'||s.length>LEGACY4_MAX_TEXT)throw Error('Text must be a string of at most 120,000 UTF-16 units.');
 return s;
}
function checkEncoding(lang,enc){
 if(!(lang in LEGACY4_CODEPAGES)||!LEGACY4_CODEPAGES[lang].includes(enc))throw Error('Choose a supported encoding for this language.');
 return enc;
}
// WHATWG Windows-1252 C1 range; Node builds without full ICU may differ.
const CP1252_C1={128:'€',130:'‚',131:'ƒ',132:'„',133:'…',134:'†',135:'‡',136:'ˆ',137:'‰',138:'Š',139:'‹',140:'Œ',142:'Ž',145:'‘',146:'’',147:'“',148:'”',149:'•',150:'–',151:'—',152:'˜',153:'™',154:'š',155:'›',156:'œ',158:'ž',159:'Ÿ'};
function cp1252Char(byte){
 if(byte>=128&&byte<=159){if(!(byte in CP1252_C1))throw Error('Undefined Windows-1252 byte');return CP1252_C1[byte];}
 return String.fromCharCode(byte);
}
export function decodeTextFile(bytes,language,source){
 checkEncoding(language,source);
 if(!(bytes instanceof Uint8Array) || bytes.length>200000)throw Error('Choose a .txt file under 200 KB.');
 try{
  if(source==='windows-1252')return Array.from(bytes,cp1252Char).join('');
  return new TextDecoder(source,{fatal:true}).decode(bytes);
 }catch(e){throw Error(`The file does not decode cleanly as ${source}. Choose the original encoding; text was not changed.`);}
}
const ENCODER_CACHE=new Map();
function inverseCodepage(label){
 let cached=ENCODER_CACHE.get(label);if(cached)return cached;
 const decoder=label==='windows-1252'?null:new TextDecoder(label,{fatal:true});
 const map=new Map();
 for(let i=0;i<256;i++){
  try{
   const t=label==='windows-1252'?cp1252Char(i):decoder.decode(new Uint8Array([i]));
   if(t.length&&t!=='\uFFFD'&&!map.has(t))map.set(t,i);
  }catch{ /* undefined byte in code page; not encodable */ }
 }
 ENCODER_CACHE.set(label,map);
 return map;
}
export function encodeTextFile(value,language,target){
 checkEncoding(language,target);
 const text=assertText(value);
 if(target==='utf-8')return new TextEncoder().encode(text);
 const map=inverseCodepage(target),out=[];
 for(const c of text){
  const byte=map.get(c);
  if(byte===undefined){
   throw Error(`Character U+${c.codePointAt(0).toString(16).toUpperCase()} cannot be saved as ${target}. No lossy substitutions were made.`);
  }
  out.push(byte);
 }
 return new Uint8Array(out);
}
export function transcodeTextFile(bytes,language,source,target){
 return encodeTextFile(decodeTextFile(bytes,language,source),language,target);
}
const SAFE_PASS=/^[\s.,!?;:()\-'"0-9]$/u;
function validString(s,max){return typeof s==='string'&&s.length>0&&s.length<=max&&!/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/u.test(s);}
/** Explicit mapped legacy Sinhala glyph sequences; not an auto-detector. */
export function validateSinhalaProfile(raw){
 if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('Mapping must be a JSON object.');
 if(raw.language!=='si'||!validString(raw.name,80))throw Error('Use a named Sinhala mapping with language "si".');
 const entries=[...Object.entries(raw.singles||{}),...Object.entries(raw.combos||{})];
 if(!entries.length||entries.length>2000)throw Error('The mapping needs 1–2,000 entries.');
 const forwards=new Map();
 for(const [key,val] of entries){
  if(!validString(key,20)||!validString(val,80)||(!/[\u0D80-\u0DFF]/u.test(val)&&!SAFE_PASS.test(val)))
   throw Error('Each mapping must contain a valid key and Sinhala Unicode output.');
  if(forwards.has(key)&&forwards.get(key)!==val)throw Error('Conflicting legacy glyph codes.');
  forwards.set(key,val.normalize('NFC'));
 }
 return Object.freeze({name:raw.name,language:'si',entries:Object.freeze([...forwards.entries()])});
}
function convertWithMap(s,pairs,direction){
 assertText(s);
 const reverse=new Map();
 if(direction==='encode'){
  for(const [source,dest] of pairs){
   if(reverse.has(dest)&&reverse.get(dest)!==source)throw Error('Ambiguous reverse glyph mapping: this profile supports decode only.');
   reverse.set(dest,source);
  }
 }
 const rules=direction==='encode'?[...reverse.entries()]:pairs;
 rules.sort((a,b)=>b[0].length-a[0].length);
 let out='';
 for(let i=0;i<s.length;){
  const found=rules.find(([from])=>s.startsWith(from,i));
  if(found){out+=found[1];i+=found[0].length;continue;}
  const codepoint=String.fromCodePoint(s.codePointAt(i));
  if(SAFE_PASS.test(codepoint)){out+=codepoint;i+=codepoint.length;continue;}
  throw Error(`Unmapped ${direction==='encode'?'Unicode':'legacy'} sequence at position ${i+1}. Check the exact font profile; no result was produced.`);
 }
 return out.normalize('NFC');
}
export function convertSinhalaText(text,profile,from='Legacy',to='Unicode'){
 const p=validateSinhalaProfile(profile);
 if(!['Legacy','Unicode'].includes(from)||!['Legacy','Unicode'].includes(to))throw Error('Choose Legacy or Unicode.');
 if(from===to)return assertText(text);
 return convertWithMap(text,[...p.entries],from==='Legacy'?'decode':'encode');
}
export function tamilConvert(text,from,to,existingConverter){
 assertText(text);
 if(!LEGACY4_TAMIL.includes(from)||!LEGACY4_TAMIL.includes(to))throw Error('Unsupported Tamil font encoding.');
 if(typeof existingConverter!=='function')throw Error('Existing Bamini/SunTommy converter is unavailable.');
 return existingConverter(text,from,to);
}

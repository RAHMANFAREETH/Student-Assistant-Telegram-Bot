/**
 * V12.2 Tamil Font & Writing Studio — browser-only pure functions.
 * Mapping facts reorganized from Unicode to Non Unicode Tamil data
 * https://unicodetononunicode.com/data/tamil-mapping.json (CC BY 4.0),
 * cross-checked there against the MIT-licensed ag-sanjjeev and Pakeetharan converters.
 * Attribution: Unicode to Non Unicode (unicodetononunicode.com), 2026-10-21;
 * this implementation adds context-aware parsing, tests, and UI integration.
 * See README_V122_FONT_STUDIO.md for license and limitations.
 */
const VOWELS = {
  'அ':'m','ஆ':'M','இ':',','ஈ':'<','உ':'c','ஊ':'C','எ':'v',
  'ஏ':'V','ஐ':'I','ஒ':'x','ஓ':'X','ஔ':'xs'
};
const CONSONANTS = {
  'க':'f','ங':'q','ச':'r','ஞ':'Q','ட':'l','ண':'z','த':'j','ந':'e',
  'ப':'g','ம':'k','ய':'a','ர':'u','ல':'y','வ':'t','ழ':'o','ள':'s',
  'ற':'w','ன':'d','ஜ':'[','ஷ':'\\','ஸ':']','ஹ':'`'
};
const SIGNS = {
 'ா':['','h'],'ி':['','p'],'ீ':['','P'],'ு':['','{'],'ூ':['','_'],
 'ெ':['n',''],'ே':['N',''],'ை':['i',''],'ொ':['n','h'],
 'ோ':['N','h'],'ௌ':['n','s'],'்':['',';']
};
const U = {'க':'F','ச':'R','ட':'L','ண':'Z','த':'J','ந':'E','ப':'G','ம':'K','ய':'A','ர':'U','ல':'Y','வ':'T','ழ':'O','ள':'S','ற':'W','ன':'D'};
const UU = {'க':'$','ச':'R+','ட':'^','ண':'Z}','த':'J}','ந':'E}','ப':'G+','ம':'%','ய':'A+','ர':'&','ல':'Y}','வ':'T+','ழ':'*','ள':'Sh','ற':'W}','ன':'D}'};
const SPECIAL = {'ஸ்ரீ':'=','ஶ்ரீ':'=','டி':'b','டீ':'B','ஃ':'/'};
const LETTERS = Object.keys(CONSONANTS);
export const FONT_PROFILES = ['Unicode','Bamini','SunTommy'];
const TAMIL = /[\u0B80-\u0BFF]/u;
const COMBINING = /^[\u0BBE-\u0BCD]$/u;
const CONTROLS = new Set(['\u200B','\u200C','\u200D','\u2060','\uFEFF']);
const PROFILES = new Map();
function build(profile){
 const forward = new Map(Object.entries(VOWELS));
 for(const [ch,code] of Object.entries(CONSONANTS)){
  forward.set(ch,code);
  for(const [sign,[before,after]] of Object.entries(SIGNS)){
   let value=before+code+after;
   if(sign==='ு'&&U[ch])value=U[ch];
   if(sign==='ூ'&&UU[ch])value=UU[ch];
   if(ch==='ர' && sign==='ி')value='hp';
   if(ch==='ர' && sign==='ீ')value='hP';
   if(ch==='ர' && sign==='்')value='h;';
   forward.set(ch+sign,value);
  }
 }
 for(const [ch,v] of Object.entries(SPECIAL))forward.set(ch,v);
 if(profile==='SunTommy'){
  forward.set('சூ','#');forward.set('ளூ','@');forward.set('ஙூ','q+');
 }
 // These codes are accepted for reverse conversion but never generated.
 const reverse = new Map();
 for(const [ch,v] of forward){if(!reverse.has(v))reverse.set(v,ch);}
 // Distinguish special orthography and aliases in the Bamini family.
 reverse.set('H','ர்');reverse.set('u;','ர்');reverse.set('up','ரி');reverse.set('uP','ரீ');
 if(profile==='SunTommy'){
  // In this font R+ is ambiguous with ச+ூ; prefer the canonical # for சூ.
  // The inherited legacy glyph R+ is not emitted by this profile.
  reverse.delete('R+');reverse.delete('Sh');reverse.delete('q+');reverse.set('q+','ஙூ');
 }
 const encoded=[...forward.keys()].sort((a,b)=>[...b].length-[...a].length);
 const codes=[...reverse.keys()].sort((a,b)=>b.length-a.length);
 return {forward,reverse,encoded,codes};
}
for(const p of ['Bamini','SunTommy'])PROFILES.set(p,build(p));
function getProfile(profile){const data=PROFILES.get(profile);if(!data)throw Error('Choose a supported font encoding.');return data;}
function cap(s){const text=String(s??'');if(text.length>120000)throw Error('Limit text to 120,000 characters for local processing.');return text;}
export function encodeLegacy(value,profile='Bamini'){
 const text=cap(value).normalize('NFC'),{forward,encoded}=getProfile(profile);
 let out='';
 for(let i=0;i<text.length;){
  let found=false;
  for(const key of encoded){if(text.startsWith(key,i)){
   out+=forward.get(key);i+=key.length;found=true;break;
  }}
  if(!found){const cp=String.fromCodePoint(text.codePointAt(i));out+=cp;i+=cp.length;}
 }
 return out;
}
export function decodeLegacy(value,profile='Bamini'){
 const text=cap(value),{reverse,codes}=getProfile(profile);
 let out='';
 // A Bamini glyph is encoded in Latin punctuation/letters; even English may be
 // decoded as Tamil. Callers should select only known legacy encoded regions.
 for(let i=0;i<text.length;){
  if(TAMIL.test(text[i])){out+=text[i++];continue;}
  let found=false;
  for(const code of codes){if(text.startsWith(code,i)){
   out+=reverse.get(code);i+=code.length;found=true;break;
  }}
  if(!found){const cp=String.fromCodePoint(text.codePointAt(i));out+=cp;i+=cp.length;}
 }
 return out.normalize('NFC');
}
export function convertTamilFont(value,from='Unicode',to='Bamini'){
 if(!FONT_PROFILES.includes(from)||!FONT_PROFILES.includes(to))throw Error('Choose Unicode, Bamini or SunTommy.');
 if(from===to)return cap(value);
 const unicode=from==='Unicode'?cap(value):decodeLegacy(value,from);
 return to==='Unicode'?unicode:encodeLegacy(unicode,to);
}
export function detectTamilEncoding(value){
 const text=cap(value),tamil=(text.match(/[\u0B80-\u0BFF]/gu)||[]).length;
 const latin=(text.match(/[A-Za-z;\[\]{}\\`]/g)||[]).length;
 if(!text.trim())return 'empty';
 if(tamil>0&&tamil>=latin/3)return 'Unicode Tamil present';
 if(latin>0)return 'Latin/legacy characters — Bamini cannot be confirmed automatically';
 return 'Undetermined';
}
export function cleanTamilText(value,{removeZeroWidth=true,normalizeSpaces=true,trimLines=false}={}){
 let out=cap(value).replace(/\r\n?/g,'\n').normalize('NFC');
 if(removeZeroWidth)out=out.replace(/[\u200B\u200C\u200D\u2060\uFEFF]/gu,'');
 if(normalizeSpaces)out=out.replace(/[\u00A0\u202F]/gu,' ').replace(/[\t ]{2,}/gu,' ');
 if(trimLines)out=out.split('\n').map(x=>x.trim()).join('\n');
 return out;
}
export function inspectUnicode(value,limit=70){
 const s=cap(value),all=Array.from(s);if(!Number.isInteger(limit)||limit<1||limit>200)throw Error('Invalid inspection limit.');
 const issues=[];const parts=[];
 for(const [index,ch] of all.entries()){
  if(CONTROLS.has(ch))issues.push(`${index+1}: invisible U+${ch.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')}`);
  if(COMBINING.test(ch)&&(!index||!TAMIL.test(all[index-1])&&!COMBINING.test(all[index-1])))issues.push(`${index+1}: vowel/pulli sign without a Tamil base`);
  if(index<limit){const code=ch.codePointAt(0).toString(16).toUpperCase().padStart(4,'0');parts.push(`${index+1}. ${ch==='\n'?'↵':ch===' '?'␣':CONTROLS.has(ch)?'(invisible)':ch} — U+${code}`);}
 }
 return {characters:all.length,tamil:all.filter(x=>TAMIL.test(x)).length,invisible:all.filter(x=>CONTROLS.has(x)).length,issues,details:parts.join('\n'),truncated:all.length>limit};
}
const ARABIC='0123456789';const TAMIL_DIGITS='௦௧௨௩௪௫௬௭௮௯';
export function convertTamilDigits(value,direction='toTamil'){
 const s=cap(value);if(!['toTamil','toWestern'].includes(direction))throw Error('Choose a digit conversion direction.');
 const source=direction==='toTamil'?ARABIC:TAMIL_DIGITS,target=direction==='toTamil'?TAMIL_DIGITS:ARABIC;
 return s.replace(direction==='toTamil'?/[0-9]/g:/[௦-௯]/gu,ch=>target[source.indexOf(ch)]);
}

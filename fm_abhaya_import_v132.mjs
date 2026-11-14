/**
 * V13.2 FM-Abhaya *legacy-to-Unicode only* adapter for original
 * Pandukabhaya mapping JSON (MIT):
 * https://github.com/akuruAI/pandukabhaya/tree/main/pandukabhaya/mappings
 * No proprietary font is bundled. No network requests or uploads.
 * Decoding semantics follow the upstream project: preprocessing substitutions,
 * then longest glyph-sequence match. Do NOT claim Unicode->FM support.
 */
function assertText(s){
 if(typeof s!=='string'||s.length>120000)throw Error('Text must be at most 120,000 characters.');
 return s;
}
const MAX_ENTRIES=5000;
const SAFE_UNMAPPED=/^[\s]$/u;
function obj(value,label){
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error(`Invalid ${label} object.`);
 return value;
}
function entries(raw,label){
 const pairs=Object.entries(obj(raw,label));
 if(pairs.length>MAX_ENTRIES)throw Error(`${label} has too many entries.`);
 for(const [k,v] of pairs){
  if(typeof k!=='string'||!k||k.length>24||typeof v!=='string'||!v||v.length>100||
     /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(k+v))
   throw Error(`Unsafe or malformed ${label} entry.`);
 }
 return pairs;
}
function byLongest(a,b){return b[0].length-a[0].length;}
export function validateFMAbhayaSource(raw){
 const data=obj(raw,'mapping file');
 const metadata=obj(data.metadata,'metadata');
 if(metadata?.mapping?.name!=='fm_abhaya'||metadata?.mapping?.license!=='MIT'||
    !/^FM[ -]?Abhaya$/iu.test(String(metadata?.font?.name||'')))
  throw Error('Select the original MIT-licensed Pandukabhaya FM Abhaya mapping JSON. Other Sinhala fonts need different mappings.');
 const maps=obj(data.mappings,'mappings');
 const singles=entries(maps.singles,'singles');
 const combos=entries(maps.combos,'combos');
 const rules=entries(maps.rules||{},'rules');
 // Avoid mistakenly using a tiny illustrative or truncated data file.
 if(singles.length<80||combos.length<80)
  throw Error('This FM Abhaya source is incomplete. Import the full upstream fm_abhaya.json file.');
 const combined=new Map(singles);
 for(const [key,value] of combos)combined.set(key,value);
 for(const [key,value] of combined){
  // ASCII punctuation is valid as output, but there must be Sinhala coverage.
  if(!value||!key)throw Error('Invalid glyph mapping.');
 }
 return Object.freeze({
  name:'FM Abhaya (Pandukabhaya / MIT)',
  source:'Pandukabhaya',
  rules:Object.freeze([...rules].sort(byLongest)),
  glyphs:Object.freeze([...combined.entries()].sort(byLongest)),
  count:combined.size,
 });
}
function substitute(text,pairs,unknownAllowed){
 let out='';
 for(let i=0;i<text.length;){
  let found=null;
  for(const rule of pairs){if(text.startsWith(rule[0],i)){found=rule;break;}}
  if(found){out+=found[1];i+=found[0].length;continue;}
  const cp=String.fromCodePoint(text.codePointAt(i));
  if(unknownAllowed||SAFE_UNMAPPED.test(cp)){out+=cp;i+=cp.length;continue;}
  throw Error(`Unknown FM Abhaya glyph at character ${i+1}. Conversion stopped; check the font and original text.`);
 }
 return out;
}
export function fmAbhayaToUnicode(text,source){
 const original=assertText(text);
 const profile=validateFMAbhayaSource(source);
 const rearranged=substitute(original,profile.rules,true);
 const converted=substitute(rearranged,profile.glyphs,false);
 return converted.normalize('NFC');
}

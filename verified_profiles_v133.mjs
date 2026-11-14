/**
 * V13.3 conservative font-specific glyph converter, separate from byte encodings.
 * No hidden font-family aliases, heuristics, regex from untrusted data or uploads.
 * Mapping files must contain independent verified test vectors and provenance.
 */
const MAX_TEXT=120000, MAX_PROFILE=250000, MAX_MAP=6000;
const WHITESPACE=/^\s$/u;
const SCRIPT={ta:/[\u0B80-\u0BFF]/u,si:/[\u0D80-\u0DFF]/u};
const FONT_NAMES={
 ta:['Kalaham','Vanavil','Tharmini','Senthamil','Amudham','TAB','TAM','TSCII','Anjal','ShreeLipi'],
 si:['FM Abhaya','FM Malithi','FM Derana','FM Bindumathi','DL Manel','DL Champika','DL Divani','Kaputa','Amalee','Thibus']
};
export {FONT_NAMES};
const badControl=/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u;
function isObject(v){return !!v && typeof v==='object' && !Array.isArray(v);}
function text(s,limit=MAX_TEXT){if(typeof s!=='string'||s.length>limit||badControl.test(s))throw Error('Invalid text or text exceeds safe limits.');return s;}
function clean(s,max){if(typeof s!=='string'||!s.trim()||s.length>max||badControl.test(s))throw Error('Invalid profile metadata or character sequence.');return s;}
function replaceAllLiteral(s,rules){
 let out=s;
 for(const [a,b] of rules){if(!a)throw Error('Empty replacement rule.');out=out.split(a).join(b);if(out.length>MAX_TEXT*4)throw Error('Replacement output too large.');}
 return out;
}
function runMapping(s,entries,allowWhitespace=true){
 text(s);let result='';
 const sorted=[...entries].sort((a,b)=>b[0].length-a[0].length);
 for(let i=0;i<s.length;){
  const found=sorted.find(([a])=>s.startsWith(a,i));
  if(found){result+=found[1];i+=found[0].length;continue;}
  const char=String.fromCodePoint(s.codePointAt(i));
  if(allowWhitespace&&WHITESPACE.test(char)){result+=char;i+=char.length;continue;}
  throw Error(`Unmapped character at position ${i+1} (U+${char.codePointAt(0).toString(16).toUpperCase()}). No partial result was produced.`);
 }
 return result.normalize('NFC');
}
function rawDecode(s,p){return runMapping(replaceAllLiteral(s,p.preprocess),p.entries);}
function rawEncode(s,p){
 if(p.direction!=='both')throw Error('This profile is validated for Legacy → Unicode only.');
 if(p.preprocess.length)throw Error('Reverse conversion is not safe for profiles with preprocessing rules.');
 // Reverse only after proving no collisions; do not guess among variant glyphs.
 const invert=new Map();
 for(const [key,val] of p.entries){
  if(invert.has(val)&&invert.get(val)!==key)throw Error('Ambiguous Unicode → legacy mapping. Reverse conversion is disabled.');
  invert.set(val,key);
 }
 return runMapping(s.normalize('NFC'),[...invert.entries()]);
}
export function validateProfile(raw,{allowExperimental=false}={}){
 if(!isObject(raw)||raw.schema!=='student-legacy-profile-v1')throw Error('Unsupported mapping profile schema.');
 const language=raw.language;
 if(!['ta','si'].includes(language))throw Error('Only Tamil or Sinhala font-specific profiles are supported.');
 const font=clean(raw.font,80),license=clean(raw.license,90),source=clean(raw.source,500);
 if(!/^https:\/\//i.test(source)&&!source.startsWith('local-reviewed:'))throw Error('Provide a source HTTPS URL or local-reviewed reference.');
 if(raw.provenanceStatus!=='reviewed'&&!allowExperimental)throw Error('Profile is not marked reviewed. Experimental profiles cannot be used for document conversion.');
 if(!['decode','both'].includes(raw.direction))throw Error('Specify decode or both for supported directions.');
 if(!isObject(raw.mappings))throw Error('Missing mapping table.');
 const entries=Object.entries(raw.mappings);
 if(entries.length<2||entries.length>MAX_MAP)throw Error('Mapping table is empty or too large.');
 let total=0;
 for(const [a,b] of entries){clean(a,40);clean(b,80);if(!SCRIPT[language].test(b))throw Error('Unicode outputs must contain the selected language script.');total+=a.length+b.length;}
 if(total>MAX_PROFILE)throw Error('Mapping size limit exceeded.');
 const preprocess=Object.entries(raw.preprocess||{});
 if(preprocess.length>100)throw Error('Too many preprocessing rules.');
 for(const [a,b] of preprocess){clean(a,20);text(b,30);}
 const samples=raw.samples;
 if(!Array.isArray(samples)||samples.length<2||samples.length>100)throw Error('At least two independent source/expected examples are required.');
 const profile={language,font,license,source,direction:raw.direction,entries,preprocess,samples};
 for(const s of samples){
  if(!isObject(s))throw Error('Invalid example.');
  const legacy=clean(s.legacy,2000),unicode=clean(s.unicode,2000);
  if(!SCRIPT[language].test(unicode)||rawDecode(legacy,profile)!==unicode.normalize('NFC'))throw Error('Mapping does not match supplied sample: '+legacy.slice(0,32));
  if(raw.direction==='both'&&rawEncode(unicode,profile)!==legacy)throw Error('Reverse conversion does not match sample.');
 }
 return Object.freeze({...profile,verifiedSamples:samples.length,entryCount:entries.length});
}
export function convertProfile(textInput,raw,from='legacy',to='unicode'){
 const profile=validateProfile(raw);
 text(textInput);
 if(from===to)return textInput;
 if(from==='legacy'&&to==='unicode')return rawDecode(textInput,profile);
 if(from==='unicode'&&to==='legacy')return rawEncode(textInput,profile);
 throw Error('Choose legacy or Unicode for both source and destination.');
}
export function checkProfileFile(s){
 if(typeof s!=='string'||new TextEncoder().encode(s).length>MAX_PROFILE*3)throw Error('Mapping file exceeds size limit.');
 return validateProfile(JSON.parse(s));
}

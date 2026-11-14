import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fmAbhayaToUnicode,validateFMAbhayaSource} from './fm_abhaya_import_v132.mjs';
// Minimal unit fixture exercises upstream published FM Abhaya examples.
// Synthetic filler entries satisfy file-size checks; this is NOT a replacement
// for testing the full real-world upstream mapping and user documents.
const singles={Y:'ශ',',':'ල',x:'ං',l:'ක',d:'ා','ú':'වි',o:'ද',H:'්‍ය',j:'ව'};
for(let i=0;i<85;i++)singles['k'+i]='ක';
const combos={'%S':'්‍රී'};
for(let i=0;i<85;i++)combos['Z'+i]='ක්';
const raw={metadata:{font:{name:'FM Abhaya'},mapping:{name:'fm_abhaya',license:'MIT'}},mappings:{singles,combos,rules:{}}};
test('FM Abhaya upstream mapping structure accepted (synthetic fixture)',()=>assert.ok(validateFMAbhayaSource(raw).count>80));
test('published example ශ්‍රී ලංකා converted',()=>assert.equal(fmAbhayaToUnicode('Y%S ,xld',raw),'ශ්‍රී ලංකා'));
test('published example විද්‍යාව converted',()=>assert.equal(fmAbhayaToUnicode('úoHdj',raw),'විද්‍යාව'));
test('wrong font explicitly rejected',()=>assert.throws(()=>validateFMAbhayaSource({...raw,metadata:{...raw.metadata,font:{name:'FM Malithi'}}}),/original MIT/));
test('tiny partial mapping blocked',()=>assert.throws(()=>validateFMAbhayaSource({...raw,mappings:{singles:{l:'ක'},combos:{'%S':'්‍රී'}}}),/incomplete/));
test('unknown glyph aborts without substitution',()=>assert.throws(()=>fmAbhayaToUnicode('🙂',raw),/Unknown FM Abhaya/));
test('V13.1 legacy conversion UI retains Tamil and other languages',()=>{
 const ui=readFileSync(new URL('./legacy4_ui_v131.mjs',import.meta.url),'utf8');
 for(const value of ["ta:","si:","ar:","en:","convertSinhalaText", "tamilConvert", "fmAbhayaToUnicode"]){assert.ok(ui.includes(value),value);}
});

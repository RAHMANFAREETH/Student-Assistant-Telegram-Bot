import test from 'node:test';import assert from 'node:assert/strict';
import {validateProfile,convertProfile,FONT_NAMES,checkProfileFile} from './verified_profiles_v133.mjs';
function make(ta=true){return {schema:'student-legacy-profile-v1',language:ta?'ta':'si',font:ta?'Kalaham':'DL Manel',source:'local-reviewed:two-samples',license:'MIT',provenanceStatus:'reviewed',direction:'both',mappings:ta?{A:'அ',B:'ஆ'}:{A:'අ',B:'ආ'},samples:ta?[{legacy:'AB',unicode:'அஆ'},{legacy:'BA',unicode:'ஆஅ'}]:[{legacy:'AB',unicode:'අආ'},{legacy:'BA',unicode:'ආඅ'}]};}
test('Tamil source and reverse verified',()=>{const p=make();assert.equal(validateProfile(p).verifiedSamples,2);assert.equal(convertProfile('AB',p),'அஆ');assert.equal(convertProfile('அஆ',p,'unicode','legacy'),'AB');});
test('Sinhala independently verified examples',()=>{const p=make(false);assert.equal(convertProfile('AB',p),'අආ');});
test('Unmapped glyphs fail closed',()=>assert.throws(()=>convertProfile('A?',make()),/Unmapped/));
test('Samples mismatch fails before conversion',()=>{let p=make();p.samples[0].unicode='ம';assert.throws(()=>validateProfile(p),/sample/);});
test('Provenance is mandatory',()=>{let p=make();p.provenanceStatus='unverified';assert.throws(()=>validateProfile(p),/reviewed/);});
test('Font lists are names, not fake working mappings',()=>{assert.ok(FONT_NAMES.ta.includes('Vanavil'));assert.ok(FONT_NAMES.si.includes('FM Malithi'));});
test('Reverse blocked when direction decode only',()=>{let p=make();p.direction='decode';assert.throws(()=>convertProfile('அஆ',p,'unicode','legacy'),/Legacy.*Unicode only/);});
test('Reverse blocked when mapping has variants',()=>{let p=make();p.direction='both';p.mappings.C='அ';assert.throws(()=>validateProfile(p),/Ambiguous/);});
test('Reject hostile data and mismatched language',()=>{let p=make();p.mappings.B='ආ';assert.throws(()=>validateProfile(p),/script/);});
test('Profile file load validates',()=>{assert.equal(checkProfileFile(JSON.stringify(make())).font,'Kalaham');});

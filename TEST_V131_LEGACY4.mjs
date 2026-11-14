import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {decodeTextFile,encodeTextFile,transcodeTextFile,validateSinhalaProfile,convertSinhalaText,tamilConvert,LEGACY4_TAMIL} from './legacy4_core_v131.mjs';

test('Four languages have distinct conversion classes and Tamil profiles are preserved',()=>{
 assert.deepEqual(LEGACY4_TAMIL,['Unicode','Bamini','SunTommy']);
 assert.equal(tamilConvert('வணக்கம்','Unicode','Bamini',()=> 'TEST'),'TEST');
 assert.throws(()=>tamilConvert('x','Unicode','Other',()=>''),/Unsupported/);
});
test('Arabic legacy windows-1256 roundtrips with Arabic characters',()=>{
 const s='السلام عليكم 123';
 const b=encodeTextFile(s,'ar','windows-1256');
 assert.notEqual(new TextDecoder().decode(b),s);
 assert.equal(decodeTextFile(b,'ar','windows-1256'),s);
});
test('Arabic ISO-8859-6 roundtrips simple Arabic',()=>{
 const s='السلام عليكم';
 assert.equal(decodeTextFile(encodeTextFile(s,'ar','iso-8859-6'),'ar','iso-8859-6'),s);
});
test('English CP1252 and Mac Roman roundtrip punctuation',()=>{
 const s='“Hello” — café';
 for(const cp of ['windows-1252','macintosh'])assert.equal(decodeTextFile(encodeTextFile(s,'en',cp),'en',cp),s);
});
test('Bytes rejected when character not representable - never substitutes',()=>{
 assert.throws(()=>encodeTextFile('සිංහල','ar','windows-1256'),/cannot be saved/);
 assert.throws(()=>encodeTextFile('🙂','en','windows-1252'),/cannot be saved/);
});
test('Invalid decode bytes fail rather than replacement characters',()=>{
 assert.throws(()=>decodeTextFile(Uint8Array.of(0x81),'en','windows-1252'),/does not decode/);
 assert.throws(()=>decodeTextFile(Uint8Array.of(0xff),'en','utf-8'),/does not decode/);
});
test('Transcode Windows-1256 to UTF-8 with exact roundtrip',()=>{
 const text='مرحبا'; const a=encodeTextFile(text,'ar','windows-1256');
 const b=transcodeTextFile(a,'ar','windows-1256','utf-8');
 assert.equal(new TextDecoder().decode(b),text);
});
test('Sinhala profile converts verified mappings both directions',()=>{
 const p=JSON.parse(readFileSync(new URL('./sinhala_profile_example_v131.json',import.meta.url),'utf8'));
 const profile=validateSinhalaProfile(p);
 assert.equal(convertSinhalaText('ld',p,'Legacy','Unicode'),'කා');
 assert.equal(convertSinhalaText('කා',p,'Unicode','Legacy'),'ld');
 assert.throws(()=>convertSinhalaText('Y%S ,xld',p,'Legacy','Unicode'),/Unmapped/);
});
test('Sinhala profile blocks missing or conflicting mappings',()=>{
 assert.throws(()=>validateSinhalaProfile({language:'si',name:'bad',singles:{a:'x'}}),/Sinhala Unicode/);
 const bad={language:'si',name:'ambiguous',singles:{'a':'ක','b':'ක'}};
 assert.throws(()=>convertSinhalaText('ක',bad,'Unicode','Legacy'),/Ambiguous/);
});
test('Sinhala data cannot inject control chars or JavaScript',()=>{
 assert.throws(()=>validateSinhalaProfile({language:'si',name:'x',singles:{'<script>':'ක\u0000'}}),/valid/);
});
test('limits for text and byte files',()=>{
 assert.throws(()=>encodeTextFile('a'.repeat(120001),'en','windows-1252'),/at most/);
 assert.throws(()=>decodeTextFile(new Uint8Array(200001),'en','windows-1252'),/under 200 KB/);
});

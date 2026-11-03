import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {
 FONT_PROFILES,encodeLegacy,decodeLegacy,convertTamilFont,
 cleanTamilText,inspectUnicode,convertTamilDigits,detectTamilEncoding
} from './super_miniapp_v122_fonts.mjs';
import {TOOLS} from './super_miniapp_v120_tools.mjs';

const samples=[
 ['வணக்கம்','tzf;fk;'],['தமிழ்','jkpo;'],['கோவில்','Nfhtpy;'],
 ['அம்மா','mk;kh'],['நன்றி','ed;wp'],['கொடி','nfhb'],
 ['கூடம்','$lk;'],['ஸ்ரீ','='],['பள்ளிக்கூடம்','gs;spf;$lk;']
];

test('existing 68 tools kept intact',()=>assert.equal(TOOLS.length,68));
test('studio exposes only three validated font profiles',()=>assert.deepEqual(FONT_PROFILES,['Unicode','Bamini','SunTommy']));
for(const [unicode,legacy] of samples){
 test(`Bamini known phrase: ${unicode}`,()=>{
  assert.equal(encodeLegacy(unicode),legacy);
  assert.equal(decodeLegacy(legacy),unicode);
 });
}
test('all consonant-plus-sign forms round trip for both profiles',()=>{
 const consonants='கஙசஞடணதநபமயரலவழளறனஜஷஸஹ';
 const signs='ாிீுூெேைொோௌ்';
 for(const profile of ['Bamini','SunTommy']){
  for(const consonant of consonants){
   assert.equal(decodeLegacy(encodeLegacy(consonant,profile),profile),consonant);
   for(const sign of signs){
    const syllable=consonant+sign;
    assert.equal(decodeLegacy(encodeLegacy(syllable,profile),profile),syllable,`${profile}: ${syllable}`);
   }
  }
 }
});
test('right/left vowel shapes and grantha letters',()=>{
 assert.equal(decodeLegacy('nfh'),'கொ');assert.equal(decodeLegacy('Nfh'),'கோ');
 assert.equal(decodeLegacy('if'),'கை');assert.equal(decodeLegacy('hp'),'ரி');
 assert.equal(decodeLegacy('hP'),'ரீ');assert.equal(decodeLegacy('h;'),'ர்');
 assert.equal(decodeLegacy('f;\\'),'க்ஷ');
});
test('SunTommy differs for at least three historical glyph mappings',()=>{
 assert.equal(encodeLegacy('சூ','SunTommy'),'#');
 assert.equal(encodeLegacy('ளூ','SunTommy'),'@');
 assert.equal(encodeLegacy('ஙூ','SunTommy'),'q+');
 assert.equal(decodeLegacy('#@q+','SunTommy'),'சூளூஙூ');
 assert.equal(encodeLegacy('சூ','Bamini'),'R+');
});
test('all three conversion directions, including legacy to legacy',()=>{
 const x='தமிழ்';
 assert.equal(convertTamilFont(convertTamilFont(x,'Unicode','Bamini'),'Bamini','Unicode'),x);
 assert.equal(convertTamilFont(convertTamilFont(x,'Unicode','SunTommy'),'SunTommy','Unicode'),x);
 assert.equal(convertTamilFont('R+','Bamini','SunTommy'),'#');
});
test('preserves emoji and newlines in text',()=>{
 const x='வணக்கம் 👋\nதமிழ்';assert.equal(decodeLegacy(encodeLegacy(x)),x);
});
test('does not pretend to identify arbitrary Latin input as Bamini',()=>{
 assert.match(detectTamilEncoding('Hello world'),/cannot be confirmed/i);
 assert.match(detectTamilEncoding('வணக்கம்'),/Unicode/);
});
test('unknown formats and size guard are errors',()=>{
 assert.throws(()=>encodeLegacy('தமிழ்','Unknown'));
 assert.throws(()=>convertTamilFont('x','Unicode','TAB'));
 assert.throws(()=>encodeLegacy('a'.repeat(120001)),/Limit text/);
});
test('cleanup respects opt outs and normalizes NFC',()=>{
 const x='ந\u200Bன்\u00A0  நண்பன்\r\n  வரி  ';
 assert.equal(cleanTamilText(x,{trimLines:true}),'நன் நண்பன்\nவரி');
 assert.match(cleanTamilText(x,{removeZeroWidth:false}),/\u200B/);
 assert.equal(cleanTamilText('e\u0301'),'é');
});
test('code point inspector reports zero width and stray sign',()=>{
 const r=inspectUnicode('a\u200Bி');
 assert.equal(r.invisible,1);assert.equal(r.characters,3);
 assert.ok(r.issues.some(s=>s.includes('invisible')));
 assert.ok(r.issues.some(s=>s.includes('without a Tamil base')));
});
test('Tamil digit conversion and reverse only modify digits',()=>{
 assert.equal(convertTamilDigits('2026-11-04'),'௨௦௨௬-௧௧-௦௪');
 assert.equal(convertTamilDigits('௨௦௨௬ ஆண்டு','toWestern'),'2026 ஆண்டு');
 assert.throws(()=>convertTamilDigits('1','other'));
});
test('page keeps CSP-friendly self-hosted script, no text upload',()=>{
 const html=fs.readFileSync('super_miniapp_v122_fonts.html','utf8');
 const js=fs.readFileSync('super_miniapp_v122_fonts.js','utf8');
 const py=fs.readFileSync('super_miniapp_v122_fonts.py','utf8');
 assert.match(html,/\/app\/assets\/fontstudio.js/);
 assert.doesNotMatch(html,/<script\s+[^>]*>[^<]+<\/script>/);
 for(const token of ['/app/api/tasks','/app/api/planner','localStorage','BOT_TOKEN','innerHTML']){
  assert.equal(js.includes(token),false,`unexpected token: ${token}`);
 }
 assert.equal(py.includes("methods=['POST']"),false);
});

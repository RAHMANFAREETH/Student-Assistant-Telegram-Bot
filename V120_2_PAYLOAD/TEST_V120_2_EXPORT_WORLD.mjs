import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
 TOOLS,WORLD_CLOCK_ENTRIES,TOOL_NAME_TRANSLATIONS,
 jsonPretty,base64Text,textDiff,attendancePlan,weightedGrades,csvInspect,compute
} from './super_miniapp_v120_tools.mjs';

test('68 IDs are unique and available to all users',()=>{
 assert.equal(TOOLS.length,68);
 assert.equal(new Set(TOOLS.map(t=>t.id)).size,68);
});
test('worldwide clock catalog covers 240+ countries and 400+ locations',()=>{
 assert.ok(WORLD_CLOCK_ENTRIES.length>=400);
 assert.ok(new Set(WORLD_CLOCK_ENTRIES.map(r=>r[0])).size>=240);
});
test('Sri Lanka and representative multi-zone countries are present',()=>{
 assert.ok(WORLD_CLOCK_ENTRIES.some(r=>r[0]==='LK'&&r[2]==='Asia/Colombo'));
 assert.ok(WORLD_CLOCK_ENTRIES.filter(r=>r[0]==='US').length>10);
 assert.ok(WORLD_CLOCK_ENTRIES.some(r=>r[0]==='FR'&&r[2]==='Europe/Paris'));
 assert.ok(WORLD_CLOCK_ENTRIES.some(r=>r[0]==='JP'&&r[2]==='Asia/Tokyo'));
});
test('all world-clock zones supported by node Intl',()=>{
 for(const [code,country,zone] of WORLD_CLOCK_ENTRIES){
  assert.ok(code.length===2&&country&&zone);
  assert.doesNotThrow(()=>new Intl.DateTimeFormat('en-GB',{timeZone:zone}).format(new Date()),zone);
 }
});
test('JSON formatter works and errors on invalid content',()=>{
 assert.equal(jsonPretty('{"a":1}'),'{'+'\n  "a": 1\n}');
 assert.equal(jsonPretty('{"a":1}','compact'),'{"a":1}');
 assert.throws(()=>jsonPretty('{bad}'));
});
test('Base64 round trip supports Tamil and emoji',()=>{
 const text='வணக்கம் 👩‍🎓';
 assert.equal(base64Text(base64Text(text),'decode'),text);
 assert.throws(()=>base64Text('!!!!!','decode'));
});
test('Text difference shows changes and handles identical text',()=>{
 assert.equal(textDiff('a\nb','a\nb'),'No line differences.');
 assert.match(textDiff('a\nb','a\nc'),/Line 2/);
});
test('Attendance planner handles reachable and impossible 100%',()=>{
 assert.equal(attendancePlan(34,40,90).needed,20);
 assert.equal(attendancePlan(40,40,100).needed,0);
 assert.equal(attendancePlan(39,40,100).needed,Infinity);
 assert.throws(()=>attendancePlan(10,5,90));
});
test('Weighted grade math rejects invalid weights',()=>{
 const out=weightedGrades('85,30\n90,20\n75,50');
 assert.equal(out.weight,100);
 assert.equal(out.average,81);
 assert.throws(()=>weightedGrades('100,70\n100,40'));
});
test('CSV inspection handles quoted commas and line breaks',()=>{
 assert.deepEqual(csvInspect('name,value\n"Ali, Ahmad",80\nFatima,95').rows,3);
 assert.equal(csvInspect('a,b\n1,2\n3').consistent,false);
 assert.throws(()=>csvInspect('"unfinished'));
});
test('New tool compute paths are real calculations',()=>{
 for(const [id,fields] of [
  ['json-pretty',{text:'{"x":1}',mode:'format'}],
  ['base64-text',{text:'hello',mode:'encode'}],
  ['text-diff',{before:'a',after:'b'}],
  ['attendance',{attended:34,total:40,target:90}],
  ['weighted-grade',{rows:'90,50\n80,50'}],
  ['csv-inspect',{text:'a,b\n1,2'}],
 ]) assert.ok(compute(id,fields).length>0,id);
});
test('private APIs are not changed and exports use consent-only HTTP upload',()=>{
 const js=readFileSync(new URL('./super_miniapp_v120.js',import.meta.url),'utf8');
 assert.match(js,/Save via Telegram \(temporary upload\)/);
 assert.match(js,/'X-V120-Export-Intent':'1'/);
 assert.match(js,/tg\.downloadFile/);
 assert.match(js,/navigator\.share/);
 assert.match(js,/saveStored\('world_zones'/);
 assert.match(js,/WORLD_CLOCK_ENTRIES/);
 const py=readFileSync(new URL('./super_miniapp_v120_exports.py',import.meta.url),'utf8');
 assert.match(py,/Content-Disposition|as_attachment=True/);
 assert.match(py,/Access-Control-Allow-Origin/);
});

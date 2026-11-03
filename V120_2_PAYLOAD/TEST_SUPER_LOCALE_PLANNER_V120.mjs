import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {TOOLS,localUI,localField,FIELD_LABEL_TRANSLATIONS} from './super_miniapp_v120_tools.mjs';

const js=fs.readFileSync(new URL('./super_miniapp_v120.js',import.meta.url),'utf8');
const html=fs.readFileSync(new URL('./super_miniapp_v120.html',import.meta.url),'utf8');
const api=fs.readFileSync(new URL('./super_miniapp_v120.py',import.meta.url),'utf8');

test('68 tool entries preserved',()=>assert.equal(TOOLS.length,68));
test('76 form labels are localized for Tamil and Sinhala',()=>{
  const keys=Object.keys(FIELD_LABEL_TRANSLATIONS.ta);
  assert.equal(keys.length,76);
  for(const lang of ['ta','si'])for(const k of keys){
    assert.ok(localField(k,lang).length>0);
    assert.notEqual(localField(k,lang),k,`${lang}: missing ${k}`);
  }
  assert.equal(localField('Date','en'),'Date');
});
test('planner and tool actions have translations',()=>{
  const keys=['calculate','copyResult','taskLocalOnly','plannerAssignments','plannerExams','plannerRefresh','plannerUnavailable','taskPlaceholder','openBot','plannerReadOnly','quickTasks'];
  for(const lang of ['en','ta','si'])for(const key of keys){
    assert.ok(localUI(key,lang));
    if(lang!=='en')assert.notEqual(localUI(key,lang),localUI(key,'en'),lang+':'+key);
  }
});
test('frontend renders owned records only from authenticated endpoint',()=>{
  assert.ok(js.includes("fetch('/app/api/planner'"));
  assert.ok(js.includes("'X-Telegram-Init-Data':tg.initData"));
  assert.ok(js.includes("li.append(title,el('small'"));
  assert.ok(!js.includes('innerHTML'));
});
test('planner page exposes refresh and read-only sections',()=>{
  for(const id of ['planner-refresh','planner-assignments','planner-exams','planner-remote-status','planner-open-bot'])assert.ok(html.includes(`id="${id}"`));
});
test('backend never uses query string Telegram account id',()=>{
  assert.ok(api.includes('uid = verify_super_session(request.headers.get("X-Telegram-Init-Data", ""))'));
  assert.ok(api.includes('get_assignments(int(user_id), status="pending", limit=30)'));
  assert.ok(api.includes('get_exams(int(user_id), upcoming_only=True, limit=30)'));
});

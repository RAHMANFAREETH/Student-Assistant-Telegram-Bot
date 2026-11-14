import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const catalog=JSON.parse(fs.readFileSync('font_catalog_v130.json','utf8'));
const source=fs.readFileSync('super_miniapp_v122_fonts.js','utf8');
const start=source.indexOf('/* V13 FONT LIBRARY 80: Unicode font preference only; no uploads or font downloads. */');
assert.ok(start>0,'font-library JS must be appended after existing studio');
const script=source.slice(start);
function makeEl(value='',tagName='DIV'){
 const handlers={};return {
  value,tagName,textContent:'',placeholder:'',disabled:false,options:[],childNodes:[],
  addEventListener(type,fn){(handlers[type]??=[]).push(fn)},
  replaceChildren(){this.options=[];this.children=[];this.value=''},
  add(x){this.options.push(x);if(this.options.length===1)this.value=x.value},
  append(x){(this.children??=[]).push(x)},
  dispatchEvent(e){(handlers[e.type]||[]).forEach(fn=>fn(e))},
  fire(type){this.dispatchEvent({type})},
 };
}
function run(){
 const els=new Map();
 for(const id of ['ms-language','ms-font','v130-font-filter','v130-font-search','v130-font-count','v130-font-info','v130-legacy-tags','v13-studio-language','v130-font-filter-label','v130-font-search-label','v130-legacy-heading','v130-legacy-info'])
  els.set(id,makeEl());
 const by=id=>els.get(id);
 by('ms-language').value='ta';by('v13-studio-language').value='en';by('v130-font-filter').value='all';
 by('v130-font-filter').options=['all','academic','modern','display'].map(value=>({value,textContent:''}));
 for(const id of ['v130-font-filter-label','v130-font-search-label']){
  els.get(id).tagName='LABEL';els.get(id).childNodes=[{nodeType:3,textContent:' '}];
 }
 const document={
  getElementById:by,
  createElement(tag){return {tagName:tag.toUpperCase(),value:'',textContent:''}}
 };
 vm.runInNewContext(script,{document,Event:class{constructor(type){this.type=type}}});
 return by;
}
test('80 distinct Unicode names across all 4 languages',()=>{
 assert.equal(catalog.fonts.length,80);
 assert.equal(new Set(catalog.fonts.map(f=>f.language+'/'+f.name)).size,80);
 assert.deepEqual(Object.fromEntries(['ta','en','ar','si'].map(l=>[l,catalog.fonts.filter(f=>f.language===l).length])),
 {ta:18,en:26,ar:26,si:10});
});
test('Arabic starts with Sakkal Majalla, retained as a system font preference',()=>{
 const by=run();by('ms-language').value='ar';by('ms-language').fire('change');
 assert.equal(by('ms-font').options[0].value,'Sakkal Majalla');
 assert.equal(by('ms-font').options.length,26);
 assert.match(by('v130-font-info').textContent,/Microsoft/);
});
test('Tamil academic filter lists Latha and Vijaya',()=>{
 const by=run();by('v130-font-filter').value='academic';by('v130-font-filter').fire('change');
 const names=by('ms-font').options.map(x=>x.value);
 assert.ok(names.includes('Latha'));assert.ok(names.includes('Vijaya'));
 assert.ok(!names.includes('Kalaham'));
});
test('Search filters fonts and does not change entered text',()=>{
 const by=run();by('ms-language').value='en';by('ms-language').fire('change');
 by('v130-font-search').value='Times';by('v130-font-search').fire('input');
 assert.deepEqual(by('ms-font').options.map(x=>x.value),['Times New Roman']);
});
test('Sinhala legacy names appear separately, not as Unicode selectable fonts',()=>{
 const by=run();by('ms-language').value='si';by('ms-language').fire('change');
 assert.ok(by('ms-font').options.map(x=>x.value).includes('Iskoola Pota'));
 assert.ok(by('v130-legacy-tags').children.some(x=>x.textContent==='FM Abhaya'));
 assert.ok(!by('ms-font').options.some(x=>x.value==='FM Abhaya'));
});
test('Existing Bamini and SunTommy converters remain unchanged',()=>{
 assert.match(source,/convertTamilFont/);
 assert.match(source,/Bamini/);
 assert.match(source,/SunTommy/);
});

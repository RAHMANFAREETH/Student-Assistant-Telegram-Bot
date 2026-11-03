import test from 'node:test';
import assert from 'node:assert/strict';
import {TOOLS,CATEGORIES,compute,displayToolName,TOOL_NAME_TRANSLATIONS,wordCount,reverseText,
 percentChange,salesTax,profitMargin,averageSpeed,gradePercentage,deviation,quadratic,
 factorial,combinations,findReplace,wordFrequency,studySessions} from './super_miniapp_v120_tools.mjs';

test('all 68 tool IDs are unique and categorized',()=>{
 assert.equal(TOOLS.length,68);
 assert.equal(new Set(TOOLS.map(x=>x.id)).size,68);
 assert.ok(TOOLS.every(x=>CATEGORIES.includes(x.category)));
 for(const lang of ['ta','si']) {
  assert.equal(Object.keys(TOOL_NAME_TRANSLATIONS[lang]).length,68);
  assert.ok(TOOLS.every(t=>displayToolName(t,lang)!==t.name));
 }
});
test('percentage change handles increase decrease and zero baseline',()=>{
 assert.equal(percentChange(100,120),20);assert.equal(percentChange(100,80),-20);
 assert.throws(()=>percentChange(0,10),/nonzero/);
});
test('VAT totals',()=>{
 assert.deepEqual(salesTax(100,15),{tax:15,total:115});
 assert.throws(()=>salesTax(-1,15));assert.throws(()=>salesTax(1,101));
});
test('profit and margin including cost of zero',()=>{
 assert.deepEqual(profitMargin(80,100),{profit:20,margin:20,markup:25});
 assert.equal(profitMargin(0,100).markup,null);
 assert.throws(()=>profitMargin(1,0));
});
test('speed positive time only',()=>{assert.equal(averageSpeed(20,30),40);assert.throws(()=>averageSpeed(20,0));});
test('grade percentage rejects impossible marks',()=>{
 assert.equal(gradePercentage(75,100),75);assert.throws(()=>gradePercentage(150,100));
});
test('standard deviation sample and population',()=>{
 const r=deviation('1 2 3 4 5');assert.equal(r.count,5);assert.equal(r.mean,3);
 assert.ok(Math.abs(r.population-Math.sqrt(2))<1e-9);
 assert.ok(Math.abs(r.sample-Math.sqrt(2.5))<1e-9);
 assert.equal(deviation('9').sample,null);
 assert.throws(()=>deviation('1;bad'));
});
test('quadratic real double and complex roots',()=>{
 const r=quadratic(1,-3,2);assert.equal(r.root1,2);assert.equal(r.root2,1);
 const one=quadratic(1,2,1);assert.equal(one.root1,-1);assert.equal(one.root2,-1);
 const c=quadratic(1,0,1);assert.equal(c.real,false);assert.equal(c.imaginary,1);
 assert.throws(()=>quadratic(0,1,2));
});
test('factorial is exact for large integers',()=>{
 assert.equal(factorial(0),'1');assert.equal(factorial(10),'3628800');
 assert.equal(factorial(20),'2432902008176640000');assert.throws(()=>factorial(201));
});
test('combinations exact integers and bounds',()=>{
 assert.equal(combinations(10,3),'120');assert.equal(combinations(100,0),'1');
 assert.equal(combinations(100,100),'1');assert.throws(()=>combinations(3,4));
});
test('find replace treats searches and replacements literally',()=>{
 assert.equal(findReplace('Hello hello','hello','Hi',true),'Hi Hi');
 assert.equal(findReplace('a.b.a','.','X',false),'aXbXa');
 assert.equal(findReplace('C++ c++','C++','$&',true),'$& $&');
 assert.throws(()=>findReplace('hello','','x'));
});
test('word frequencies count Unicode words',()=>{
 assert.deepEqual(wordFrequency('cat CAT dog'),[['cat',2],['dog',1]]);
 const r=wordFrequency('தமிழ் தமிழ் English');assert.deepEqual(r[0],['தமிழ்',2]);
 assert.deepEqual(wordFrequency(''),[]);
});
test('study sessions excludes last break',()=>{
 assert.deepEqual(studySessions(4,25,5),{focus:100,breaks:15,total:115});
 assert.deepEqual(studySessions(1,10,5),{focus:10,breaks:0,total:10});
 assert.throws(()=>studySessions(0,10,5));
});
test('all 12 new tools have live compute implementations',()=>{
 const samples={
 'percentage-change':{before:100,after:80},'sales-tax':{price:100,rate:15},
 'profit-margin':{cost:80,price:100},'speed-calc':{distance:20,minutes:30},
 'grade-percent':{scored:75,total:100},'stddev':{values:'1,2,3,4,5'},
 'quadratic':{a:1,b:-3,c:2},factorial:{n:10},combinations:{n:10,k:3},
 'text-replace':{text:'Hello',find:'H',replace:'Y',ignoreCase:false},
 'word-frequency':{text:'cat cat dog'},'study-sessions':{blocks:4,focus:25,rest:5}};
 for(const [id,values] of Object.entries(samples)){
  const output=compute(id,values);
  assert.equal(typeof output,'string',id);
  assert.ok(output.length>0,id);
 }
 assert.equal(Object.keys(samples).length,12);
});

test('Unicode text tools keep grapheme clusters intact',()=>{
 assert.equal(wordCount('😀').characters,1);
 assert.equal(wordCount('👩‍🎓').characters,1);
 assert.equal(reverseText('A👩‍🎓B'),'B👩‍🎓A');
});

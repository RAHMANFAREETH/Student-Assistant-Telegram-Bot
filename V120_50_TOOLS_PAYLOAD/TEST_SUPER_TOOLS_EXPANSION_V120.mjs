import test from 'node:test';
import assert from 'node:assert/strict';
import {TOOLS,CATEGORIES,compute,weekdayOf,monthShift,timeDuration,fractionReduce,ratioReduce,meanMedian,weightedGpa,billSplit,simpleInterest,compoundInterest,loanPayment,isPrimeNumber,squareRoot,sortLines,uniqueLines,readingTime,reverseText,urlComponent,colorContrast,translateUI,translateCategory,displayToolName,UI_TRANSLATIONS,TOOL_NAME_TRANSLATIONS} from './super_miniapp_v120_tools.mjs';

test('exactly 50 unique tools and no missing categories',()=>{
 assert.equal(TOOLS.length,50);assert.equal(new Set(TOOLS.map(t=>t.id)).size,50);
 assert.ok(TOOLS.every(t=>CATEGORIES.includes(t.category)));
 assert.equal(TOOLS.filter(t=>t.id==='gpa').length,1);
});
test('locales translate all 50 tool names, and core UI keys',()=>{
 for(const lang of ['ta','si']){
  assert.equal(Object.keys(TOOL_NAME_TRANSLATIONS[lang]).length,50);
  assert.ok(TOOLS.every(t=>displayToolName(t,lang)!==t.name));
  for(const key of Object.keys(UI_TRANSLATIONS.en))assert.ok(translateUI(key,lang)!==key);
  for(const c of CATEGORIES)assert.ok(translateCategory(c,lang));
 }
 assert.equal(displayToolName(TOOLS[0],'en'),TOOLS[0].name);
 assert.equal(translateUI('navHome','en'),'Home');
});
test('weekday in UTC and leap day',()=>{assert.equal(weekdayOf('2026-11-03'),'Tuesday');assert.equal(weekdayOf('2024-02-29'),'Thursday');});
test('month shifting clamps month ends and negative offsets',()=>{
 assert.equal(monthShift('2024-01-31',1),'2024-02-29');
 assert.equal(monthShift('2025-03-31',-1),'2025-02-28');
 assert.equal(monthShift('2025-12-01',2),'2026-02-01');
 assert.throws(()=>monthShift('2026-11-03',1201));
});
test('time duration handles overnight and validates input',()=>{
 assert.deepEqual(timeDuration('23:45','01:15'),{hours:1,minutes:30,totalMinutes:90,overnight:true});
 assert.deepEqual(timeDuration('09:15','09:15'),{hours:0,minutes:0,totalMinutes:0,overnight:false});
 assert.throws(()=>timeDuration('25:00','02:00'));
 assert.throws(()=>timeDuration('9:00','10:00'));
});
test('fraction, zero and sign normalization',()=>{
 assert.deepEqual(fractionReduce(18,24),{numerator:3,denominator:4});
 assert.deepEqual(fractionReduce(-18,-24),{numerator:3,denominator:4});
 assert.deepEqual(fractionReduce(0,-10),{numerator:0,denominator:1});
 assert.throws(()=>fractionReduce(1,0));
});
test('ratio reductions and invalid 0:0',()=>{
 assert.deepEqual(ratioReduce(12,18),{left:2,right:3});
 assert.deepEqual(ratioReduce(5,0),{left:1,right:0});
 assert.deepEqual(ratioReduce(0,5),{left:0,right:1});
 assert.throws(()=>ratioReduce(0,0));
});
test('mean median odd and even, invalid list',()=>{
 assert.deepEqual(meanMedian('10,20,30,40'),{count:4,mean:25,median:25,min:10,max:40});
 assert.equal(meanMedian('3,1,2').median,2);
 assert.throws(()=>meanMedian(''));
 assert.throws(()=>meanMedian('2,bad,3'));
});
test('GPA weighted by credits and rejects bad grade points',()=>{
 const r=weightedGpa('3,4\n2,3');assert.equal(r.credits,5);assert.equal(r.gpa,3.6);
 assert.throws(()=>weightedGpa('3,5'));
 assert.throws(()=>weightedGpa('3;4'));
});
test('tip and bill split',()=>{
 assert.deepEqual(billSplit(100,10,2),{tip:10,total:110,perPerson:55});
 assert.throws(()=>billSplit(-1,10,2));assert.throws(()=>billSplit(100,10,0));
});
test('simple interest and compound interest',()=>{
 assert.deepEqual(simpleInterest(1000,10,2),{interest:200,total:1200});
 const r=compoundInterest(1000,10,1,1);assert.ok(Math.abs(r.total-1100)<1e-8);
 assert.throws(()=>compoundInterest(1000,10,1,0));
});
test('loan payment including zero interest',()=>{
 let r=loanPayment(1200,0,1);assert.ok(Math.abs(r.monthly-100)<1e-9);assert.equal(r.interest,0);
 r=loanPayment(100000,6,30);assert.ok(r.monthly>590&&r.monthly<610);
 assert.throws(()=>loanPayment(0,6,3));
});
test('primality and square root',()=>{
 assert.equal(isPrimeNumber(2),true);assert.equal(isPrimeNumber(97),true);
 assert.equal(isPrimeNumber(1),false);assert.equal(isPrimeNumber(100),false);
 assert.equal(squareRoot(144),12);assert.throws(()=>squareRoot(-2));
});
test('line tools preserve order and correctly filter duplicates',()=>{
 assert.equal(sortLines('pear\napple\nbanana'),'apple\nbanana\npear');
 assert.equal(uniqueLines('One\ntwo\none',true),'One\ntwo');
 assert.equal(uniqueLines('One\ntwo\none',false),'One\ntwo\none');
});
test('reading speed, Unicode reversal and URI encoding',()=>{
 assert.deepEqual(readingTime('one two three four',120),{words:4,minutes:4/120,seconds:2});
 assert.equal(reverseText('a😀b'),'b😀a');
 assert.equal(urlComponent('hello world?','encode'),'hello%20world%3F');
 assert.equal(urlComponent('hello%20world%3F','decode'),'hello world?');
 assert.throws(()=>urlComponent('%','decode'));
});
test('WCAG contrast endpoints and invalid colors',()=>{
 const r=colorContrast('#FFFFFF','#000000');assert.ok(Math.abs(r.ratio-21)<1e-10);assert.equal(r.normal,true);
 assert.equal(colorContrast('#000000','#000000').normal,false);
 assert.throws(()=>colorContrast('red','#000000'));
});
test('every expanded generic tool has a live compute handler',()=>{
 const inputs={
 weekday:{date:'2026-11-03'},'days-until':{start:'2026-11-03',end:'2026-11-04'},'month-shift':{date:'2026-11-03',offset:2},'time-duration':{start:'23:00',end:'01:00'},
 fraction:{numerator:4,denominator:8},ratio:{left:2,right:4},average:{values:'1,2,3'},gpa:{rows:'3,4'},tip:{amount:100,tip:10,people:2},
 'simple-interest':{principal:100,rate:10,years:1},'compound-interest':{principal:100,rate:10,years:1,times:12},'loan-payment':{principal:1000,rate:5,years:1},
 prime:{value:7},'square-root':{value:9},'text-sort':{text:'b\na'},'text-unique':{text:'a\na',ignoreCase:false},
 'reading-time':{text:'hello world',speed:200},'text-reverse':{text:'abc'},'url-encode':{text:'a b',mode:'encode'},'color-contrast':{foreground:'#ffffff',background:'#000000'}
 };
 for(const [id,f] of Object.entries(inputs)){const result=compute(id,f);assert.equal(typeof result,'string',id);assert.ok(result.length>0,id);}
 assert.equal(Object.keys(inputs).length,20);
});

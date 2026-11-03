// Pure engines, exported for deterministic Node regression tests.
import {ACTIVITIES} from './super_miniapp_v121_data.mjs';
export function randomInt(n, rng=Math.random){ if(!Number.isInteger(n)||n<=0) throw Error('Invalid bound'); return Math.min(n-1,Math.floor(rng()*n)); }
export function shuffle(items,rng=Math.random){ const a=[...items]; for(let i=a.length-1;i>0;i--){const j=randomInt(i+1,rng);[a[i],a[j]]=[a[j],a[i]];}return a; }
export function safeText(s,max=300){return String(s ?? '').slice(0,max)}
export function escapeHtml(s){return safeText(s,6000).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;');}
export function validateCatalog(){const ids=ACTIVITIES.map(a=>a.id);return {total:ids.length,study:ACTIVITIES.filter(a=>a.category==='study').length,mind:ACTIVITIES.filter(a=>a.category==='mind').length,helper:ACTIVITIES.filter(a=>a.category==='helper').length,unique:new Set(ids).size===ids.length}}
export function isoDate(d){ const x=new Date(d);if(!Number.isFinite(x.getTime()))throw Error('Invalid date');return x.getFullYear()+'-'+String(x.getMonth()+1).padStart(2,'0')+'-'+String(x.getDate()).padStart(2,'0'); }
export function localDateToUTC(s){if(!/^\d{4}-\d{2}-\d{2}$/.test(s))throw Error('Invalid date');let [y,m,d]=s.split('-').map(Number);let dt=new Date(Date.UTC(y,m-1,d));if(dt.getUTCFullYear()!==y||dt.getUTCMonth()+1!==m||dt.getUTCDate()!==d)throw Error('Invalid calendar date');return dt; }
export function dayDifference(start,end){return Math.round((localDateToUTC(end)-localDateToUTC(start))/86400000)}
export function addDays(s,days){ const d=localDateToUTC(s);if(!Number.isInteger(days)||Math.abs(days)>36500)throw Error('Invalid days');d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10);}
export function revisionDates(date){return [1,3,7,14,30].map(i=>({after:i,date:addDays(date,i)}));}
export function studyLoad(topics,minutesPerTopic,days){const n=Number(topics),m=Number(minutesPerTopic),d=Number(days);if(![n,m,d].every(Number.isFinite)||n<=0||n>10000||m<=0||m>1440||d<=0||d>365)throw Error('Enter valid positive values');return {total:n*m,minutesPerDay:(n*m)/d,sessionsPerDay:Math.ceil(n*m/d/25)};}
export function planDay(start,topics,minutes,breakMinutes=5){
 const [h,m]=start.split(':').map(Number);if(!Number.isInteger(h)||h<0||h>23||!Number.isInteger(m)||m<0||m>59)throw Error('Invalid time');
 const tasks=String(topics).split(/\r?\n/).map(x=>x.trim()).filter(Boolean).slice(0,20);if(!tasks.length||tasks.some(t=>t.length>120))throw Error('Enter one or more topics');
 if(!Number.isInteger(minutes)||minutes<5||minutes>180||!Number.isInteger(breakMinutes)||breakMinutes<0||breakMinutes>60)throw Error('Invalid duration');
 const result=[];let t=h*60+m;
 for(let i=0;i<tasks.length;i++){if(t+minutes>1440)throw Error('Schedule exceeds midnight'); result.push({start:fmtTime(t),end:fmtTime(t+minutes),topic:tasks[i]});t+=minutes+(i<tasks.length-1?breakMinutes:0);}
 return result;
}
function fmtTime(t){return String(Math.floor(t/60)).padStart(2,'0')+':'+String(t%60).padStart(2,'0')}
export function streakDays(days,today){let s=new Set(days.filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)));let cursor=today;let n=0;if(!s.has(cursor))cursor=addDays(cursor,-1);for(;s.has(cursor);n++)cursor=addDays(cursor,-1);return n;}
export function apply2048(grid,direction){
 if(!Array.isArray(grid)||grid.length!==16||grid.some(n=>!Number.isInteger(n)||n<0))throw Error('Invalid board');
 const g=[...grid];let gained=0; const compress=line=>{let a=line.filter(v=>v);const out=[];for(let i=0;i<a.length;i++){if(a[i]===a[i+1]){out.push(a[i]*2);gained+=a[i]*2;i++;}else out.push(a[i]);}while(out.length<4)out.push(0);return out;};
 if(!['left','right','up','down'].includes(direction))throw Error('Invalid direction');
 for(let k=0;k<4;k++){
  let idx=[];for(let j=0;j<4;j++)idx.push((direction==='up'||direction==='down')?j*4+k:k*4+j);
  if(direction==='right'||direction==='down')idx.reverse();
  const values=compress(idx.map(i=>g[i]));idx.forEach((pos,j)=>g[pos]=values[j]);
 }
 return {grid:g,gained,moved:g.some((n,i)=>n!==grid[i])};
}
export function spawn2048(board,rng=Math.random){const a=[...board],zero=a.map((n,i)=>n===0?i:-1).filter(i=>i!==-1);if(!zero.length)return a;a[zero[randomInt(zero.length,rng)]]=rng()<.9?2:4;return a;}
export function canMove2048(b){return b.includes(0)||['left','right','up','down'].some(dir=>apply2048(b,dir).moved)}
export function legalSlide(board,i){if(!Array.isArray(board)||board.length!==9)throw Error('Invalid board');const z=board.indexOf(0);if(z<0||i<0||i>8)return false;return Math.abs(Math.floor(z/3)-Math.floor(i/3))+Math.abs(z%3-i%3)===1;}
export function slide(board,i){if(!legalSlide(board,i))return [...board];const n=[...board],z=n.indexOf(0);[n[z],n[i]]=[n[i],n[z]];return n;}
export function shuffleSlide(moves=60,rng=Math.random){let b=[1,2,3,4,5,6,7,8,0],prev=-1;for(let n=0;n<moves;n++){let legal=b.map((_,i)=>i).filter(i=>legalSlide(b,i)&&i!==prev);let old=b.indexOf(0);b=slide(b,legal[randomInt(legal.length,rng)]);prev=old;}return b;}
export function sudokuValid(board){if(!Array.isArray(board)||board.length!==81)return false;for(let i=0;i<81;i++){let x=Number(board[i]);if(!Number.isInteger(x)||x<0||x>9)return false;if(!x)continue;const r=Math.floor(i/9),c=i%9;for(let j=0;j<81;j++){if(i===j||board[j]!==x)continue;let rr=Math.floor(j/9),cc=j%9;if(rr===r||cc===c||(Math.floor(rr/3)===Math.floor(r/3)&&Math.floor(cc/3)===Math.floor(c/3)))return false;}}return true;}
export function sudokuSolved(board){return sudokuValid(board)&&board.every(x=>x>=1&&x<=9)}
export const SUDOKU_PUZZLE='530070000600195000098000060800060003400803001700020006060000280000419005000080079'.split('').map(Number);
export const SUDOKU_SOLUTION='534678912672195348198342567859761423426853791713924856961537284287419635345286179'.split('').map(Number);
export function validate24(input,digits){
 const expr=String(input).trim();if(!expr||expr.length>80)throw Error('Expression too long or empty');
 const tokens=expr.match(/\d+\.?\d*|[()+*\-/]/g);if(!tokens||tokens.join('')!==expr.replace(/\s/g,''))throw Error('Only numbers, +, −, ×, ÷ and parentheses allowed.');
 let nums=tokens.filter(t=>/^\d/.test(t)).map(Number);
 if(nums.length!==4||nums.some(n=>!Number.isInteger(n))||nums.sort((a,b)=>a-b).join(',')!==[...digits].sort((a,b)=>a-b).join(','))throw Error('Use each displayed number exactly once.');
 let i=0;
 function atom(){let t=tokens[i++];if(t==='('){const value=add();if(tokens[i++]!==')')throw Error('Unmatched parentheses');return value;}if(!/^\d/.test(t??''))throw Error('Expected number');return Number(t);}
 function mul(){let v=atom();while(tokens[i]==='*'||tokens[i]==='/'){let op=tokens[i++],r=atom();if(op==='/'&&r===0)throw Error('Cannot divide by zero');v=op==='*'?v*r:v/r;}return v;}
 function add(){let v=mul();while(tokens[i]==='+'||tokens[i]==='-'){let op=tokens[i++],r=mul();v=op==='+'?v+r:v-r;}return v;}
 let value=add();if(i!==tokens.length||!Number.isFinite(value))throw Error('Invalid expression');return {value,correct:Math.abs(value-24)<1e-9};
}
export function makeWordGrid(word='PLANET',size=10,rng=Math.random){
 let target=String(word).trim().toUpperCase().replace(/[^A-Z]/g,'');if(target.length>size||target.length<3)throw Error('Word length unsupported');let grid=Array.from({length:size*size},()=>String.fromCharCode(65+randomInt(26,rng)));
 const directions=[[1,0],[0,1],[1,1]],dirs=directions.filter(([dx,dy])=>target.length<=size);
 const [dx,dy]=dirs[randomInt(dirs.length,rng)],x=randomInt(size-(target.length-1)*dx,rng),y=randomInt(size-(target.length-1)*dy,rng);
 let cells=[];for(let k=0;k<target.length;k++){let idx=(y+dy*k)*size+x+dx*k;cells.push(idx);grid[idx]=target[k];}
 return {grid,size,target,cells};
}
export function wordSelectionValid(board,indices){if(!indices.length)return false;let expected=board.cells.join(',');return indices.join(',')===expected||indices.slice().reverse().join(',')===expected;}
export function getLineCells(a,b,size=10){let x1=a%size,y1=Math.floor(a/size),x2=b%size,y2=Math.floor(b/size);let dx=Math.sign(x2-x1),dy=Math.sign(y2-y1);if(!(x1===x2||y1===y2||Math.abs(x2-x1)===Math.abs(y2-y1)))return [];
 let length=Math.max(Math.abs(x2-x1),Math.abs(y2-y1))+1;return Array.from({length},(_,i)=>(y1+i*dy)*size+x1+i*dx);
}
export function matchingScore(arrA,arrB){return arrA.length===arrB.length&&arrA.every((x,i)=>x===arrB[i])}
export function csvCell(value){let s=String(value??'');return /[",\n\r]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;}
export function progressScore(correct,total){if(!Number.isFinite(correct)||!Number.isFinite(total)||total<=0)return 0;return Math.max(0,Math.min(100,Math.round(correct/total*100)));}

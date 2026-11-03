import {quizBanks,cards,blanks,sentences,spelling,formulas,historic} from './super_miniapp_v121_data.mjs';
import {shuffle,escapeHtml,randomInt,progressScore} from './super_miniapp_v121_engine.mjs';
const esc=escapeHtml;
const help=(s)=>`<p class="instruction">${esc(s)}</p>`;
const btn=(s,cls='')=>`<button type="button" class="${cls}">${esc(s)}</button>`;

export function mountStudy(id,root,c){
 if(id==='quick-quiz')return quiz(root,c,quizBanks.general,'Quick Quiz: choose the best answer.');
 if(id==='mcq-challenge')return quiz(root,c,quizBanks.general,'Multiple-choice round: answer five questions.');
 if(id==='science-challenge')return quiz(root,c,quizBanks.science,'Science challenge: choose the correct scientific fact.');
 if(id==='geography-quiz')return quiz(root,c,quizBanks.geography,'Geography challenge: countries, capitals and continents.');
 if(id==='flashcard-sprint')return flash(root,c);
 if(id==='match-pairs')return pairs(root,c,false);
 if(id==='formula-match')return pairs(root,c,true);
 if(id==='fill-blanks')return blanksGame(root,c);
 if(id==='sentence-builder')return sentenceGame(root,c);
 if(id==='spelling-bee')return spellingGame(root,c);
 if(id==='math-race')return mathRace(root,c);
 if(id==='timeline-challenge')return timelineGame(root,c);
 root.textContent='Activity unavailable.';
}
export function quiz(root,c,bank,intro,{count=5}={}){
 let list=shuffle(bank).slice(0,Math.min(count,bank.length)),i=0,good=0,answered=false;
 function show(){if(i>=list.length){root.innerHTML=`<div class="result">🏆 ${esc(c.l.done)} ${good}/${list.length} — ${progressScore(good,list.length)}%</div>`;c.finish(good,list.length);return;}
 const [q,choices]=list[i];root.innerHTML=help(intro)+`<p class="tag">${i+1}/${list.length}</p><h3>${esc(q)}</h3><div class="choice-grid">${choices.map((x,j)=>`<button type="button" data-choice="${j}" class="choice">${esc(x)}</button>`).join('')}</div><div class="feedback" aria-live="polite" id="game-feedback"></div><button type="button" id="quiz-next" class="primary" hidden>${esc(c.l.next)}</button>`;
 root.querySelectorAll('[data-choice]').forEach(el=>el.addEventListener('click',()=>{
 if(answered)return;answered=true;const pick=Number(el.dataset.choice),correct=list[i][2];if(pick===correct)good++;
 root.querySelectorAll('[data-choice]').forEach(b=>{b.disabled=true;if(Number(b.dataset.choice)===correct)b.classList.add('correct');else if(b===el)b.classList.add('incorrect');});
 root.querySelector('#game-feedback').textContent=(pick===correct?c.l.correct:c.l.wrong)+' '+list[i][3];root.querySelector('#quiz-next').hidden=false;
 }));root.querySelector('#quiz-next').onclick=()=>{i++;answered=false;show();};
 }
 show();
}
function flash(root,c){let deck=shuffle(cards),i=0,known=0,shown=false;
 function show(){if(i>=deck.length){root.innerHTML=`<div class="result">${esc(c.l.done)} ${known}/${deck.length}</div>`;c.finish(known,deck.length);return;}
 const [a,b]=deck[i];root.innerHTML=help('Think of the definition before revealing it.')+`<p class="tag">${i+1}/${deck.length}</p><div class="flashcard"><h2>${esc(a)}</h2><p id="flash-back" ${shown?'':'hidden'}>${esc(b)}</p></div><button class="primary" id="reveal">${esc(c.l.show)}</button><div class="row-buttons"><button id="remember" disabled>${esc(c.l.remembered)} ✓</button><button id="again" disabled>${esc(c.l.again)} ↻</button></div>`;
 root.querySelector('#reveal').onclick=()=>{shown=true;root.querySelector('#flash-back').hidden=false;root.querySelector('#remember').disabled=false;root.querySelector('#again').disabled=false;};
 root.querySelector('#remember').onclick=()=>{known++;i++;shown=false;show();};root.querySelector('#again').onclick=()=>{i++;shown=false;show();};
 }
 show();
}
function pairs(root,c,isFormula){let pairs=shuffle(isFormula?formulas:cards).slice(0,4),entries=shuffle(pairs.flatMap(([a,b],i)=>[{id:i,side:0,text:a},{id:i,side:1,text:b}]));let first=null,matched=new Set(),attempts=0,busy=false;
 root.innerHTML=help('Tap a term and its matching definition. Find all four pairs.')+`<div class="match-grid">${entries.map((x,i)=>`<button data-idx="${i}" type="button" class="match-card">${esc(x.text)}</button>`).join('')}</div><p id="match-status" role="status">0/4 pairs</p>`;
 root.querySelectorAll('[data-idx]').forEach(el=>el.onclick=()=>{let index=Number(el.dataset.idx),item=entries[index];if(busy||matched.has(item.id)&&first===null||el.classList.contains('picked'))return;
 if(first===null){first=index;el.classList.add('picked');return;}
 const a=entries[first],aEl=root.querySelector(`[data-idx="${first}"]`);attempts++;
 if(a.id===item.id&&a.side!==item.side){matched.add(item.id);el.classList.add('matched');aEl.classList.add('matched');aEl.classList.remove('picked');first=null;root.querySelector('#match-status').textContent=matched.size+'/4 pairs';if(matched.size===4)c.finish(4,4);}
 else{el.classList.add('incorrect');busy=true;c.delay(()=>{el.classList.remove('incorrect');aEl.classList.remove('picked');first=null;busy=false;},650);}
 });
}
function blanksGame(root,c){let deck=shuffle(blanks),i=0,good=0;function show(){if(i>=deck.length){root.innerHTML=`<div class="result">${esc(c.l.done)} ${good}/${deck.length}</div>`;c.finish(good,deck.length);return;}
 root.innerHTML=help('Type the missing word or number (case-insensitive).')+`<p class="tag">${i+1}/${deck.length}</p><h3>${esc(deck[i][0])}</h3><form id="blank-form"><label>Missing answer <input required maxlength="50" autocomplete="off" name="answer"></label><button type="submit" class="primary">${esc(c.l.check)}</button></form><p role="status" id="blank-result"></p><button id="blank-next" hidden>${esc(c.l.next)}</button>`;
 root.querySelector('#blank-form').onsubmit=e=>{e.preventDefault();let input=e.target.elements.namedItem('answer');let ok=input.value.trim().toLocaleLowerCase()===deck[i][1].toLocaleLowerCase();if(ok)good++;root.querySelector('#blank-result').textContent=(ok?c.l.correct:c.l.wrong)+' '+deck[i][1];input.disabled=true;e.target.querySelector('button').disabled=true;root.querySelector('#blank-next').hidden=false;};root.querySelector('#blank-next').onclick=()=>{i++;show();};
 }show();}
function sentenceGame(root,c){let deck=shuffle(sentences),i=0,good=0;function show(){if(i>=deck.length){root.innerHTML=`<div class="result">${esc(c.l.done)} ${good}/${deck.length}</div>`;c.finish(good,deck.length);return;}
 let words=deck[i].split(' '),scrambled=shuffle(words);if(scrambled.join(' ')===words.join(' '))scrambled.reverse();let picked=[];
 root.innerHTML=help('Tap the words in the correct order.')+`<p class="tag">${i+1}/${deck.length}</p><div class="answer-zone" id="sentence-answer" aria-live="polite">…</div><div class="choice-grid" id="sentence-choices">${scrambled.map((w,j)=>`<button data-word="${j}">${esc(w)}</button>`).join('')}</div><div class="row-buttons"><button id="sentence-undo">${esc(c.l.undo)}</button><button id="sentence-check" class="primary">${esc(c.l.check)}</button></div><p id="sentence-result" role="status"></p><button id="sentence-next" hidden>${esc(c.l.next)}</button>`;
 function draw(){root.querySelector('#sentence-answer').textContent=picked.length?picked.map(j=>scrambled[j]).join(' '):'…';root.querySelectorAll('[data-word]').forEach(el=>el.disabled=picked.includes(Number(el.dataset.word)));}
 root.querySelectorAll('[data-word]').forEach(el=>el.onclick=()=>{picked.push(Number(el.dataset.word));draw();});root.querySelector('#sentence-undo').onclick=()=>{picked.pop();draw();};root.querySelector('#sentence-check').onclick=()=>{if(picked.length!==words.length)return;let result=picked.map(j=>scrambled[j]).join(' ');let ok=result===deck[i];if(ok)good++;root.querySelector('#sentence-result').textContent=(ok?c.l.correct:c.l.wrong)+' '+deck[i];root.querySelector('#sentence-next').hidden=false;root.querySelectorAll('[data-word],#sentence-undo,#sentence-check').forEach(el=>el.disabled=true);};root.querySelector('#sentence-next').onclick=()=>{i++;show();};
 }show();}
function spellingGame(root,c){let deck=shuffle(spelling),i=0,good=0;function show(){if(i>=deck.length){root.innerHTML=`<div class="result">${esc(c.l.done)} ${good}/${deck.length}</div>`;c.finish(good,deck.length);return;}
 root.innerHTML=help('Spell the word described by the hint.')+`<p class="tag">${i+1}/${deck.length}</p><h3>💡 ${esc(deck[i][0])}</h3><form id="spell"><label>Spell the word<input maxlength="60" name="answer" required spellcheck="false" autocomplete="off"></label><button class="primary">${esc(c.l.check)}</button></form><p id="spell-feedback" role="status"></p><button id="spell-next" hidden>${esc(c.l.next)}</button>`;
 root.querySelector('#spell').onsubmit=e=>{e.preventDefault();let val=e.target.elements.namedItem('answer').value.trim().toLowerCase(),ok=val===deck[i][1];if(ok)good++;root.querySelector('#spell-feedback').textContent=(ok?c.l.correct:c.l.wrong)+' '+deck[i][1];root.querySelector('#spell-next').hidden=false;e.target.querySelectorAll('input,button').forEach(el=>el.disabled=true);};root.querySelector('#spell-next').onclick=()=>{i++;show();};
 }show();}
function mathRace(root,c){let questions=Array.from({length:10},()=>{let a=1+randomInt(12),b=1+randomInt(12),op=['+','−','×'][randomInt(3)];return {q:`${a} ${op} ${b} = ?`,answer:op==='+'?a+b:op==='−'?a-b:a*b};});let i=0,good=0,begin=performance.now();
 function show(){if(i>=questions.length){let seconds=Math.round((performance.now()-begin)/1000);root.innerHTML=`<div class="result">${esc(c.l.done)} ${good}/10 · ${seconds}s</div>`;c.finish(good,10);return;}
 root.innerHTML=help('Solve ten arithmetic questions. Timer runs until the last answer.')+`<p class="tag">${i+1}/10</p><h2>${esc(questions[i].q)}</h2><form id="math-form"><label>${esc(c.l.answer)} <input type="number" step="1" required name="answer"></label><button class="primary">${esc(c.l.submit)}</button></form><p id="math-feedback" role="status"></p>`;
 root.querySelector('#math-form').onsubmit=e=>{e.preventDefault();let val=Number(e.target.elements.namedItem('answer').value);if(val===questions[i].answer)good++;i++;show();};
 }show();}
function timelineGame(root,c){let ordered=[...historic].sort((a,b)=>a[1]-b[1]),items=shuffle(ordered),changed=true;
 if(items.every((x,i)=>x[0]===ordered[i][0]))items.reverse();
 root.innerHTML=help('Put these historical events in chronological order (earliest first).')+`<div id="timeline-items" class="timeline-items"></div><button id="timeline-check" class="primary">${esc(c.l.check)}</button><div id="timeline-feedback" role="status"></div>`;
 function render(){let box=root.querySelector('#timeline-items');box.innerHTML=items.map((x,i)=>`<div class="timeline-row"><span>${esc(x[0])}</span><div><button data-move="up" data-index="${i}" aria-label="Move up" ${i===0?'disabled':''}>↑</button><button data-move="down" data-index="${i}" aria-label="Move down" ${i===items.length-1?'disabled':''}>↓</button></div></div>`).join('');box.querySelectorAll('[data-move]').forEach(b=>b.onclick=()=>{let i=Number(b.dataset.index),j=i+(b.dataset.move==='up'?-1:1);[items[i],items[j]]=[items[j],items[i]];render();});}
 render();root.querySelector('#timeline-check').onclick=()=>{let ok=items.every((x,i)=>x[0]===ordered[i][0]);root.querySelector('#timeline-feedback').textContent=ok?c.l.correct: c.l.wrong+' Earliest: '+ordered.map(x=>x[0]).join(' → ');if(ok){c.finish(1,1);root.querySelector('#timeline-check').disabled=true;}};
}

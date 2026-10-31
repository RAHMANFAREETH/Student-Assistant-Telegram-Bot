(() => {
  'use strict';
  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();
  const $=id=>document.getElementById(id);
  const state={tab:'all',q:'',category:'',page:0,more:false};
  const notice=t=>{$('notice').textContent=t;};
  async function api(path,options={}){
    if(!tg?.initData){throw Error('Open this library using the button inside Telegram.');}
    const result=await fetch(path,{...options,headers:{'X-Telegram-Init-Data':tg.initData,'Content-Type':'application/json',...(options.headers||{})},cache:'no-store',credentials:'omit'});
    const obj=await result.json();if(!result.ok)throw Error(obj.error||'Service unavailable');return obj;
  }
  const make=(tag,cls,text)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(text!==undefined)el.textContent=text;return el;};
  function card(book){
    const box=make('article','card'),cover=book.cover_url?make('img','cover'):make('div','cover','📖');
    if(book.cover_url){cover.src=book.cover_url;cover.alt='Book cover';cover.loading='lazy';}
    const body=make('div','body');body.append(make('h2','',book.title||'Untitled'));
    body.append(make('div','meta',[(book.author||'Unknown author'),book.language,book.category].filter(Boolean).join(' · ')));
    const buttons=make('div','actions');
    if(book.deep_link){const link=make('a','','📥 Get book');link.href=book.deep_link;link.target='_blank';link.rel='noopener';buttons.append(link);}
    const fav=make('button','secondary','♡ Favorite');fav.addEventListener('click',async()=>{try{const x=await api('/library/api/favorite',{method:'POST',body:JSON.stringify({book_id:book.id})});fav.textContent=x.favorite?'♥ Saved':'♡ Favorite';}catch(e){notice(e.message);}});
    buttons.append(fav);
    const details=make('button','secondary','About / Preview');
    details.addEventListener('click',async()=>{
      try{const data=await api('/library/api/book/'+encodeURIComponent(book.id));
        $('detail-title').textContent=data.book.title||'Book';
        $('detail-info').textContent=[data.book.author,data.book.edition,data.book.series_name].filter(Boolean).join(' · ');
        $('detail-desc').textContent=data.book.description||'No description available.';
        $('detail-preview').textContent=data.book.preview_text||'No authorized preview was provided.';
        $('details').showModal();
      }catch(e){notice(e.message);}
    });buttons.append(details);
    const status=make('button','secondary','✓ Finished');status.addEventListener('click',async()=>{try{await api('/library/api/reading',{method:'POST',body:JSON.stringify({book_id:book.id,status:'completed',percent:100})});status.textContent='✓ Completed';}catch(e){notice(e.message);}});
    buttons.append(status);
    const related=make('button','secondary','Similar books');
    related.addEventListener('click',async()=>{
      try{const data=await api('/library/api/related/'+encodeURIComponent(book.id));
        if(!data.books.length){notice('No related titles yet.');return;}
        state.more=false;listRows(data.books);notice('Related books');}
      catch(e){notice(e.message);}
    });buttons.append(related);body.append(buttons);box.append(cover,body);return box;
  }
  function listRows(rows){$('books').replaceChildren(...rows.map(card));$('page').textContent=String(state.page+1);$('prev').disabled=state.page===0;$('next').disabled=!state.more;}
  async function load(){
    notice('Loading…');$('books').replaceChildren();
    try{
      if(state.tab==='all'){
        const params=new URLSearchParams({page:state.page,q:state.q,category:state.category});
        const data=await api('/library/api/catalog?'+params);
        state.more=Boolean(data.more);listRows(data.books);notice(data.books.length?'':'No matching books found.');
      }else if(state.tab==='favorites'){
        const data=await api('/library/api/favorites');state.more=false;listRows(data.books);notice(data.books.length?'':'No favorites yet.');
      }else if(state.tab==='reading'){
        const data=await api('/library/api/reading');$('books').replaceChildren(...data.progress.map(r=>make('article','card',`${r.status.toUpperCase()} · ${r.percent}% · Book ${r.book_id}`)));state.more=false;notice(data.progress.length?'':'No reading progress yet.');
      }else{
        const data=await api('/library/api/collections');$('books').replaceChildren(...data.collections.map(r=>make('article','card',r.name)));state.more=false;notice(data.collections.length?'':'Create a collection using /bookcollection in the bot.');
      }
    }catch(e){state.more=false;notice(e.message);} $('next').disabled=!state.more;
  }
  $('detail-close').onclick=()=>$('details').close();
  $('search').onclick=()=>{state.q=$('query').value.trim();state.page=0;state.tab='all';selectTab();load();};
  $('query').addEventListener('keydown',e=>{if(e.key==='Enter')$('search').click();});
  $('categories').onchange=()=>{state.category=$('categories').value;state.page=0;load();};
  function selectTab(){for(const tab of ['all','favorites','reading','collections'])$('tab-'+tab).classList.toggle('active',state.tab===tab);$('filters').hidden=state.tab!=='all';}
  for(const tab of ['all','favorites','reading','collections'])$('tab-'+tab).onclick=()=>{state.tab=tab;state.page=0;selectTab();load();};
  $('prev').onclick=()=>{state.page=Math.max(0,state.page-1);load();};$('next').onclick=()=>{if(state.more){state.page++;load();}};
  (async()=>{try{const x=await api('/library/api/facets');for(const c of x.categories||[]){const option=make('option','',c.value);option.value=c.value;$('categories').append(option);}}catch(e){notice(e.message);}await load();})();
})();

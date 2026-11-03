// Add one Arcade entry point to the existing V12.0.2 home, without modifying its logic.
(async()=>{
 try{
  const response=await fetch('/app/arcade/meta',{credentials:'same-origin',cache:'no-store'});
  if(!response.ok)return;
  const state=await response.json();if(state.enabled!==true||state.activities!==32)return;
  const heading=document.getElementById('home-content');if(!heading)return;
  if(document.getElementById('v121-arcade-link'))return;
  const link=document.createElement('a');link.id='v121-arcade-link';link.href='/app/arcade';link.className='v121-entry';
  const title=document.createElement('strong');title.textContent='🎮 Study & Mind Games Arcade';
  const desc=document.createElement('span');desc.textContent='24 playable games + 8 study helpers · Open Arcade';
  link.append(title,desc);
  heading.insertBefore(link,heading.firstChild);
  // Use a same-origin stylesheet: the existing app has CSP style-src 'self' (no inline styles).
  const css=document.createElement('link');css.rel='stylesheet';css.href='/app/arcade/assets/entry.css';document.head.append(css);
 }catch{/* Existing Mini App must remain functional if the Arcade is disabled/unavailable. */}
})();

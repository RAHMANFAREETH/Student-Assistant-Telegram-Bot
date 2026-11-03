// Progressive Mini App entry: fail closed, never block the existing tools.
(async()=>{
 try{
  const response=await fetch('/app/fontstudio/meta',{credentials:'same-origin',cache:'no-store'});
  if(!response.ok)return;
  const info=await response.json();if(info.enabled!==true||info.tools!==4)return;
  const home=document.getElementById('home-content');if(!home||document.getElementById('v122-fontstudio-link'))return;
  const a=document.createElement('a');a.href='/app/fonts';a.id='v122-fontstudio-link';a.className='v122-entry';
  const title=document.createElement('strong');title.textContent='✍️ Font & Writing Studio';
  const sub=document.createElement('span');sub.textContent='Unicode ↔ Bamini ↔ SunTommy · Tamil text utilities';
  a.append(title,sub);home.insertBefore(a,home.firstChild);
  const css=document.createElement('link');css.rel='stylesheet';css.href='/app/assets/fontstudio-entry.css';document.head.append(css);
 }catch{/* A disabled Studio must not affect the existing Mini App. */}
})();

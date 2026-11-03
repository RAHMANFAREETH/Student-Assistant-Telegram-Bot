"""Optional real Chromium smoke test. No production requests, no bot token, no user data."""
from pathlib import Path
import re,sys,io
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT=Path(__file__).resolve().parent
BASE=ROOT
def page_html():
 html=(BASE/'super_miniapp_v120.html').read_text(encoding='utf-8')
 html=re.sub(r'<script defer src="https://telegram.org/js/telegram-web-app.js"></script>','',html)
 html=re.sub(r'<script type="module" src="/app/assets/app.js"></script>','',html)
 html=html.replace('<link rel="stylesheet" href="/app/assets/style.css">',f'<style>{(BASE/"super_miniapp_v120.css").read_text(encoding="utf-8")}</style>')
 scripts=[]
 for file in ['super_miniapp_v120_tools.mjs','super_miniapp_v120_results.mjs','super_miniapp_v120.js']:
  s=(ROOT/file).read_text(encoding='utf-8') if (ROOT/file).exists() else (BASE/file).read_text(encoding='utf-8')
  s=re.sub(r'^import\s+[^;]+;\s*$', '', s, flags=re.M)
  s=re.sub(r'\bexport\s+(?=(?:const|let|var|function|class)\b)','',s)
  scripts.append(s)
 stub="window.fetch=async function(url){if(url==='/app/api/session')return {ok:true,json:async()=>({ok:true,guest:true,user_id:null,private_features:false})};throw Error('Unexpected private fetch: '+url);};"
 html=html.replace('</body>','<script>'+stub+'\n'+'\n'.join(scripts)+'</script></body>')
 return html

def main():
 errs=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,**({'executable_path':'/usr/bin/chromium','args':['--no-sandbox']} if Path('/usr/bin/chromium').exists() else {}))
  page=browser.new_page(viewport={'width':393,'height':852},accept_downloads=True)
  page.on('pageerror',lambda err:errs.append(str(err)))
  page.set_content(page_html(),wait_until='load')
  page.wait_for_selector('#workspace:visible',timeout=15000)
  count=page.locator('button.tool-card').count()
  assert count==62, count
  results={}
  allnames=page.locator('button.tool-card').evaluate_all('(els)=>els.map(e=>e.getAttribute("aria-label"))')
  for name in allnames:
   page.locator('button.tool-card[aria-label="'+name.replace('"','\\"')+'"]').first.click()
   assert page.locator('#tool-view').is_visible(),name
   assert not page.locator('#tool-body').inner_text().startswith('Tool is unavailable.'),name
   # Click the generic action and check that it results in an output (or validation error)
   generic=page.locator('#v120-active-tool-form')
   if generic.count():
    page.locator('#tool-body button:has-text("Calculate")').first.click()
    output=page.locator('#tool-body .result').first.inner_text()
    if not output.strip() and generic.locator('[name="text"]').count():
     generic.locator('[name="text"]').first.fill('Test input')
     output=page.locator('#tool-body .result').first.inner_text()
    assert output.strip(), name+' returned no output'
    results[name]=output[:100]
   else:
    results[name]='special interactive panel rendered'
   page.locator('#back-tools').click()
  def open_tool(name):
   page.locator('button.tool-card[aria-label="'+name+'"]').first.click()
  open_tool('Password Generator')
  page.locator('#tool-body [name="length"]').fill('10')
  page.locator('#tool-body button:has-text("Generate")').first.click()
  out=page.locator('#tool-body .result').inner_text().strip()
  assert len(out)==10 and 'Invalid length' not in out,repr(out)
  page.locator('#back-tools').click()
  open_tool('Discount');page.locator('#tool-body [name="price"]').fill('100');page.locator('#tool-body [name="percent"]').fill('15')
  out=page.locator('#tool-body .result').inner_text();assert 'Final price: 85' in out and 'You save: 15' in out,repr(out)
  page.locator('#back-tools').click()
  open_tool('Word Counter');page.locator('#tool-body [name="text"]').fill('Hello world test')
  assert '3 words' in page.locator('#tool-body .result').inner_text()
  page.locator('#back-tools').click()
  open_tool('URL Encode / Decode');page.locator('#tool-body [name="text"]').fill('Cats and dogs?')
  assert page.locator('#tool-body .result').inner_text().strip()=='Cats%20and%20dogs%3F'
  page.locator('#back-tools').click()
  open_tool('Percentage Change');page.locator('#tool-body [name="after"]').fill('110')
  assert '10% change' in page.locator('#tool-body .result').inner_text()
  page.locator('#back-tools').click()
  open_tool('Combinations (nCr)');page.locator('#tool-body [name="n"]').fill('20');page.locator('#tool-body [name="k"]').fill('10')
  assert page.locator('#tool-body .result').inner_text().strip()=='184756'
  page.locator('#back-tools').click()
  open_tool('Find & Replace');page.locator('#tool-body [name="text"]').fill('Hi HI');page.locator('#tool-body [name="find"]').fill('hi');page.locator('#tool-body [name="replace"]').fill('Hey');page.locator('#tool-body [name="ignoreCase"]').check()
  assert page.locator('#tool-body .result').inner_text().strip()=='Hey Hey'
  page.locator('#back-tools').click()
  open_tool('World Clock');assert page.locator('#tool-body .result').count()>=6
  page.locator('#back-tools').click()
  open_tool('UUID Generator');page.locator('#tool-body button:has-text("Generate")').first.click();out=page.locator('#tool-body .result').inner_text()
  assert '-' in out and 'unavailable' not in out.lower(), repr(out)
  page.locator('#back-tools').click()
  open_tool('Dice Roller');page.locator('#tool-body [name="diceCount"]').fill('5');page.locator('#tool-body button:has-text("Roll dice")').click();assert page.locator('#tool-body .result').inner_text().count(' + ')==4;page.locator('#back-tools').click()
  open_tool('Timer');page.locator('#tool-body input[name="minutes"]').fill('2');page.locator('#tool-body button:has-text("Start")').first.click()
  page.wait_for_timeout(350);timer_text=page.locator('#tool-body .live-digits').inner_text();assert timer_text.startswith('00:01:'),repr(timer_text)
  page.locator('#tool-body button:has-text("Pause")').first.click();page.locator('#tool-body button:has-text("Reset")').first.click()
  page.locator('#back-tools').click()
  open_tool('Signature Pad');assert page.locator('#tool-body canvas').count()==1
  # Signature export uses real canvas/download.
  with page.expect_download(timeout=5000) as download_info:
   page.locator('#tool-body button:has-text("Save PNG")').first.click()
  assert download_info.value.suggested_filename=='signature.png'
  page.locator('#back-tools').click()
  im=Image.new('RGB',(100,100),'#2468ac');buf=io.BytesIO();im.save(buf,format='PNG')
  for name in ['Image Compression','Remove Photo Metadata','Image Watermark']:
   open_tool(name)
   page.locator('#tool-body input[type="file"]').set_input_files({'name':'qa-test.png','mimeType':'image/png','buffer':buf.getvalue()})
   with page.expect_download(timeout=12000) as download_info:
    page.locator('#tool-body button:has-text("Process & download")').first.click()
   output=page.locator('#tool-body .result').inner_text()
   assert 'Exported' in output, f'{name}: {output}'
   results[name]='export passed'
   page.locator('#back-tools').click()
  page.locator('#language-select').select_option('ta')
  assert page.locator('button.tool-card[aria-label="சதவீத மாற்றம்"]').count()==1
  page.locator('#language-select').select_option('si')
  assert page.locator('button.tool-card[aria-label="ප්‍රතිශත වෙනස"]').count()==1
  print('Dashboard tools:',count,'interactive audited:',len(results))
  print('Critical input changes: pass; password/uuid: pass; timer: pass; image exports: pass; signature: pass; language: pass')
  print('Page errors:',errs)
  assert not errs
  browser.close()
if __name__=='__main__':main()

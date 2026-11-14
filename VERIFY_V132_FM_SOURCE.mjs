/** Optional local-only test of a FULL Pandukabhaya mapping file downloaded by the user.
 * Usage: node VERIFY_V132_FM_SOURCE.mjs "C:\\...\\Downloads\\fm_abhaya.json"
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {fmAbhayaToUnicode,validateFMAbhayaSource} from './fm_abhaya_import_v132.mjs';
const file=process.argv[2];
if(!file){console.error('Usage: node VERIFY_V132_FM_SOURCE.mjs <downloaded-full-fm_abhaya.json>');process.exit(2);}
try{
 const raw=JSON.parse(readFileSync(resolve(file),'utf8'));
 const prof=validateFMAbhayaSource(raw);
 const fixtures=[['Y%S ,xld','ශ්‍රී ලංකා'],['úoHdj','විද්‍යාව']];
 for(const [legacy,expected] of fixtures){
  const actual=fmAbhayaToUnicode(legacy,raw);
  if(actual!==expected)throw Error(`Sample mismatch: ${JSON.stringify(legacy)} => ${JSON.stringify(actual)}; expected ${JSON.stringify(expected)}`);
 }
 console.log(`Verified source structure: ${prof.name} (${prof.count} glyph sequences)`);
 console.log('2/2 published example phrases converted correctly.');
 console.log('Real document review is still required; reverse Unicode->FM conversion is not supported.');
}catch(err){console.error('FM-Abhaya source validation failed:',err.message);process.exitCode=1;}

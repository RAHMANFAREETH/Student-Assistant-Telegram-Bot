/* Pure browser tool engine. No dependencies or server calls; safe to test with node --test. */
export const TOOLS = [
 ['date-difference','Date Difference','📆','Date & Time','Days, weekdays and weeks between dates'],
 ['date-add','Add / Subtract Date','🗓️','Date & Time','Move a date forward or backward'],
 ['age','Age Calculator','🎂','Date & Time','Age in years, months and days'],
 ['day-of-year','Day of the Year','📅','Date & Time','Find the ordinal day in the year'],
 ['epoch','Epoch Converter','⏳','Date & Time','Unix timestamp to a UTC date'],
 ['world-clock','World Clock','🌍','Date & Time','Current times across time zones'],
 ['timer','Timer','⏲️','Date & Time','Simple countdown while the app remains open'],
 ['stopwatch','Stopwatch','⏱️','Date & Time','Measure elapsed time'],
 ['unit','Unit Conversion','📏','Converters','Length, mass, area and more'],
 ['temperature','Temperature','🌡️','Converters','Celsius, Fahrenheit and Kelvin'],
 ['base','Numeral Systems','🔢','Converters','Convert integers between bases 2–36'],
 ['calculator','Calculator','🧮','Calculators','Arithmetic without unsafe expression evaluation'],
 ['percent','Percentage','💯','Calculators','Find a percentage of a number'],
 ['discount','Discount','🏷️','Calculators','Discounted price and savings'],
 ['bmi','BMI Calculator','⚖️','Calculators','Adult body mass index screening'],
 ['electricity','Electrical Power','⚡','Calculators','Calculate watts from volts and amps'],
 ['password','Password Generator','🔐','Generators','Secure random passwords on your phone'],
 ['uuid','UUID Generator','🆔','Generators','Generate cryptographic UUID v4 IDs'],
 ['random','Random Number','🎲','Generators','Secure random whole numbers'],
 ['word-count','Word Counter','📝','Text & Study','Count words and characters'],
 ['text-case','Text Case','🔠','Text & Study','Convert text capitalization'],
 ['todo','To-do List','✅','Productivity','Private task list on this device'],
 ['pomodoro','Pomodoro','🍅','Productivity','Focus and rest timer'],
 ['image-compress','Image Compression','🖼️','Image Tools','Export smaller JPEGs locally'],
 ['image-strip','Remove Photo Metadata','🛡️','Image Tools','Re-encode pixels to omit most metadata'],
 ['image-watermark','Image Watermark','💧','Image Tools','Add text over an image on-device'],
 ['signature','Signature Pad','✍️','Image Tools','Draw and export a PNG signature'],
 ['coin','Coin Flip','🪙','Fun & Learning','Heads or tails'],
 ['dice','Dice Roller','🎲','Fun & Learning','Roll up to five dice'],
 ['reaction','Reaction Time','🚦','Fun & Learning','Test your reaction time'],
].map(([id,name,icon,category,summary])=>({id,name,icon,category,summary}));
export const CATEGORIES = ['All','Date & Time','Converters','Calculators','Generators','Text & Study','Productivity','Image Tools','Fun & Learning','Favorites'];

const isLeap = y => y%4===0 && (y%100!==0||y%400===0);
const toDateUTC = s => {
 if(!/^\d{4}-\d{2}-\d{2}$/.test(String(s))) throw Error('Select a valid date.');
 const [y,m,d]=s.split('-').map(Number);const date=new Date(Date.UTC(y,m-1,d));
 if(date.getUTCFullYear()!==y||date.getUTCMonth()!==m-1||date.getUTCDate()!==d)throw Error('Invalid calendar date.');
 return date;
};
const fmtDate = date => date.toISOString().slice(0,10);
const num=(x,label='value')=>{if(String(x).trim()==='')throw Error(`Enter ${label}.`);const n=Number(x);if(!Number.isFinite(n))throw Error(`Invalid ${label}.`);return n;};
const natural=(n, label, low=0, high=1e9)=>{const x=num(n,label);if(!Number.isInteger(x)||x<low||x>high)throw Error(`Enter ${label} between ${low} and ${high}.`);return x;};
const nice=(n,digits=5)=>Number(n.toFixed(digits)).toLocaleString('en-US',{maximumFractionDigits:digits});

export function dateDifference(a,b,inclusive=false){
 const x=toDateUTC(a),y=toDateUTC(b),delta=(y-x)/86400000;
 const direction=delta<0?-1:1;
 const signedDays=delta+(inclusive?direction:0),abs=Math.abs(signedDays);
 // Count weekdays in the traversed calendar days, including the start day in the
 // forward direction and the end day in reverse; inclusive adds the other endpoint.
 // This is O(1) even for large ranges (only six remainder days are inspected).
 const start=direction===1?x.getTime():y.getTime()+(inclusive?0:86400000);
 let weekend=Math.floor(abs/7)*2;
 for(let i=0;i<abs%7;i++){
   const day=new Date(start+i*86400000).getUTCDay();
   if(day===0||day===6)weekend++;
 }
 return {days:signedDays,weeks:Math.floor(abs/7),remaining:abs%7,business:abs-weekend,weekends:weekend,hours:signedDays*24};
}
export function addDays(a,offset){const d=toDateUTC(a);const n=natural(Math.abs(num(offset,'days')),'days',0,100000);d.setUTCDate(d.getUTCDate()+Math.sign(Number(offset))*n);return fmtDate(d);}
export function ageAt(birth,asOf){
 const b=toDateUTC(birth),t=toDateUTC(asOf);if(b>t)throw Error('Birth date must be on or before the end date.');
 const dateAfterMonths=months=>{const y=b.getUTCFullYear(),m=b.getUTCMonth()+months;
   const first=new Date(Date.UTC(y,m,1)),last=new Date(Date.UTC(first.getUTCFullYear(),first.getUTCMonth()+1,0)).getUTCDate();
   return new Date(Date.UTC(first.getUTCFullYear(),first.getUTCMonth(),Math.min(b.getUTCDate(),last)));};
 let total=(t.getUTCFullYear()-b.getUTCFullYear())*12+t.getUTCMonth()-b.getUTCMonth();
 if(dateAfterMonths(total)>t)total--;
 const milestone=dateAfterMonths(total),days=Math.round((t-milestone)/86400000);
 return {years:Math.floor(total/12),months:total%12,days};
}
export function dayOfYear(s){const d=toDateUTC(s);return {number:1+Math.round((d-Date.UTC(d.getUTCFullYear(),0,1))/86400000),length:isLeap(d.getUTCFullYear())?366:365};}
export const UNITS = {
 Length:{'Millimeters':0.001,'Centimeters':0.01,'Meters':1,'Kilometers':1000,'Inches':0.0254,'Feet':0.3048,'Yards':0.9144,'Miles':1609.344},
 Mass:{'Milligrams':0.000001,'Grams':0.001,'Kilograms':1,'Metric tonnes':1000,'Ounces':0.028349523125,'Pounds':0.45359237},
 Area:{'Square centimeters':0.0001,'Square meters':1,'Square kilometers':1e6,'Square feet':0.09290304,'Acres':4046.8564224,'Hectares':10000},
 Volume:{'Milliliters':0.001,'Liters':1,'Cubic meters':1000,'US gallons':3.785411784,'US fluid ounces':0.0295735295625},
 Speed:{'Meters per second':1,'Kilometers per hour':1/3.6,'Miles per hour':0.44704,'Knots':0.5144444444},
 Time:{'Seconds':1,'Minutes':60,'Hours':3600,'Days':86400,'Weeks':604800},
 Data:{'Bits':0.125,'Bytes':1,'Kilobytes (KB)':1000,'Megabytes (MB)':1e6,'Gigabytes (GB)':1e9,'Kibibytes (KiB)':1024,'Mebibytes (MiB)':1048576,'Gibibytes (GiB)':1073741824},
};
export function unitConvert(category,value,from,to){const units=UNITS[category];if(!units||!(from in units)||!(to in units))throw Error('Select valid units.');return num(value)*units[from]/units[to];}
export function temperatureConvert(value,from,to){const x=num(value,'temperature');const valid=['Celsius','Fahrenheit','Kelvin'];if(!valid.includes(from)||!valid.includes(to))throw Error('Select temperature units.');const k=from==='Celsius'?x+273.15:from==='Fahrenheit'?(x+459.67)*5/9:x;if(k<0)throw Error('Temperature cannot be below absolute zero.');return to==='Kelvin'?k:to==='Celsius'?k-273.15:k*9/5-459.67;}
export function baseConvert(value,from,to){const a=natural(from,'source base',2,36),b=natural(to,'destination base',2,36);const sign=String(value).trim().startsWith('-')?-1n:1n;const text=String(value).trim().replace(/^-/,'').toLowerCase();if(!text||!Array.from(text).every(x=>parseInt(x,36)>=0&&parseInt(x,36)<a))throw Error('Digits do not match the source base.');if(text.length>48)throw Error('Use 48 digits or fewer.');let result=0n;for(const ch of text)result=result*BigInt(a)+BigInt(parseInt(ch,36));return (result*sign).toString(b).toUpperCase();}
export function calculate(a,op,b){const x=num(a,'first number'),y=num(b,'second number');let result;switch(op){case '+':result=x+y;break;case '-':result=x-y;break;case '×':result=x*y;break;case '÷':if(y===0)throw Error('Cannot divide by zero.');result=x/y;break;case '^':result=x**y;break;default:throw Error('Unknown operation.');}if(!Number.isFinite(result))throw Error('Result is too large.');return result;}
export function bmi(weight,heightCm){const kg=num(weight,'weight'),cm=num(heightCm,'height');if(kg<=0||cm<=0)throw Error('Height and weight must be positive.');const result=kg/((cm/100)**2);return {value:result,category:result<18.5?'Underweight':result<25?'Typical adult range':result<30?'Overweight':'Obesity range'};}
export function discount(price,percentage){const p=num(price,'price'),r=num(percentage,'discount');if(p<0||r<0||r>100)throw Error('Price must be positive and discount must be 0–100%.');return {saved:p*r/100,total:p*(1-r/100)};}
export function secureInt(maxExclusive, cryptoImpl=globalThis.crypto){if(!Number.isSafeInteger(maxExclusive)||maxExclusive<1||maxExclusive>0xffffffff)throw Error('Invalid random range.');if(!cryptoImpl?.getRandomValues)throw Error('Secure randomness not available in this browser.');const max=0x100000000,limit=Math.floor(max/maxExclusive)*maxExclusive,arr=new Uint32Array(1);let n;do{cryptoImpl.getRandomValues(arr);n=arr[0];}while(n>=limit);return n%maxExclusive;}
export function securePassword(length=16,options={},cryptoImpl=globalThis.crypto){const n=natural(length,'length',8,128);const pool=(options.upper===false?'':'ABCDEFGHIJKLMNOPQRSTUVWXYZ')+(options.lower===false?'':'abcdefghijklmnopqrstuvwxyz')+(options.digits===false?'':'0123456789')+(options.symbols===true?'!@#$%^&*_-+=':'');if(!pool)throw Error('Choose at least one character type.');let result='';for(let i=0;i<n;i++)result+=pool[secureInt(pool.length,cryptoImpl)];return result;}
export function secureRandom(min,max,cryptoImpl=globalThis.crypto){const a=natural(min,'minimum',-1000000000,1000000000),b=natural(max,'maximum',-1000000000,1000000000);if(a>b)throw Error('Minimum must not exceed maximum.');return a+secureInt(b-a+1,cryptoImpl);}
export function wordCount(s){const t=String(s||'').trim();return {characters:String(s||'').length,words:t?(t.match(/\S+/gu)||[]).length:0,lines:t?t.split(/\r?\n/).length:0};}
export function textCase(s,mode){const t=String(s||'');if(mode==='upper')return t.toLocaleUpperCase();if(mode==='lower')return t.toLocaleLowerCase();if(mode==='title')return t.toLocaleLowerCase().replace(/\b\S/gu,x=>x.toLocaleUpperCase());throw Error('Choose a text case.');}
export function compute(id,f){switch(id){
 case 'date-difference':{const r=dateDifference(f.start,f.end,Boolean(f.include));return `${r.days} days\n${r.weeks} weeks and ${r.remaining} days\n${r.business} weekdays · ${r.weekends} weekend days\n${nice(r.hours,0)} hours`;}
 case 'date-add':return addDays(f.date,Number(f.offset))+' (YYYY-MM-DD)';
 case 'age':{const r=ageAt(f.birth,f.asof);return `${r.years} years, ${r.months} months, ${r.days} days`;}
 case 'day-of-year':{const r=dayOfYear(f.date);return `Day ${r.number} of ${r.length}`;}
 case 'epoch':{const d=new Date(num(f.timestamp,'timestamp')*(f.unit==='milliseconds'?1:1000));if(!Number.isFinite(d.getTime()))throw Error('Timestamp out of range.');return d.toISOString()+' (UTC)';}
 case 'unit':return nice(unitConvert(f.category,f.value,f.from,f.to));
 case 'temperature':return `${nice(temperatureConvert(f.value,f.from,f.to))} ${f.to}`;
 case 'base':return baseConvert(f.value,f.from,f.to);
 case 'calculator':return nice(calculate(f.a,f.operator,f.b),9);
 case 'percent':return nice(num(f.value,'value')*num(f.percent,'percentage')/100,8);
 case 'discount':{const r=discount(f.price,f.percent);return `Final price: ${nice(r.total,2)}\nYou save: ${nice(r.saved,2)}`;}
 case 'bmi':{const r=bmi(f.weight,f.height);return `BMI: ${nice(r.value,2)}\n${r.category}\nAdult screening only, not a diagnosis.`;}
 case 'electricity':return `${nice(num(f.volts,'volts')*num(f.amps,'amps'))} watts`;
 case 'word-count':{const x=wordCount(f.text);return `${x.words} words · ${x.characters} characters · ${x.lines} lines`;}
 case 'text-case':return textCase(f.text,f.mode);
 case 'random':return String(secureRandom(f.min,f.max));
 default:throw Error('This tool needs its interactive panel.');}}
export const FORMAT = nice;

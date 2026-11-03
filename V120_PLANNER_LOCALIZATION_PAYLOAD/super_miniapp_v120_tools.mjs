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
 ['weekday','Weekday Finder','📅','Date & Time','Find the weekday for any valid calendar date'],
 ['days-until','Days Until Date','🗓️','Date & Time','Countdown between two selected dates'],
 ['month-shift','Add / Subtract Months','📆','Date & Time','Move by months and clamp month-end dates'],
 ['time-duration','Time Duration','🕐','Date & Time','Elapsed hours and minutes, including overnight'],
 ['fraction','Simplify Fraction','➗','Calculators','Reduce an integer fraction to simplest terms'],
 ['ratio','Simplify Ratio','🔢','Calculators','Reduce a two-number ratio'],
 ['average','Mean & Median','📈','Calculators','Analyze a list of numeric values'],
 ['gpa','GPA Calculator','🎓','Calculators','Weighted grade points and credits, 4-point scale'],
 ['tip','Tip & Split Bill','🧾','Calculators','Divide a bill including a percentage tip'],
 ['simple-interest','Simple Interest','💰','Calculators','Estimate interest without compounding'],
 ['compound-interest','Compound Interest','📊','Calculators','Estimate interest with regular compounding'],
 ['loan-payment','Loan Payment','🏦','Calculators','Estimate fixed monthly payments'],
 ['prime','Prime Number Test','🔎','Calculators','Check whether an integer is prime'],
 ['square-root','Square Root','√','Calculators','Find the nonnegative square root'],
 ['text-sort','Sort Lines','🔤','Text & Study','Sort nonempty text lines alphabetically'],
 ['text-unique','Remove Duplicate Lines','🧹','Text & Study','Remove duplicate lines while preserving order'],
 ['reading-time','Reading Time','📖','Text & Study','Estimate time to read a passage'],
 ['text-reverse','Reverse Text','🔁','Text & Study','Reverse Unicode code points in a string'],
 ['url-encode','URL Encode / Decode','🔗','Text & Study','Encode or decode URL components safely'],
 ['color-contrast','Color Contrast','🎨','Generators','Check WCAG contrast between two hex colors'],
].map(([id,name,icon,category,summary])=>({id,name,icon,category,summary}));
export const CATEGORIES = ['All','Date & Time','Converters','Calculators','Generators','Text & Study','Productivity','Image Tools','Fun & Learning','Favorites'];


// Preview UI localization. English field labels and descriptions remain until reviewed.
export const UI_TRANSLATIONS = {
 en: {welcome:'Study smarter, every day.',subtitle:'Books, calculators and useful everyday tools.',search:'Search tools…',back:'← All tools',tasks:'🗓️ My tasks',profile:'👤 My profile',libraryHeading:'Your Book Library',openLibrary:'Open Book Library ↗',navHome:'Home',navLibrary:'Library',navTools:'Tools',navPlanner:'Planner',navProfile:'Profile',explore:'Explore tools',toolsUnit:'tools',empty:'No matching tools. Try another search.'},
 ta: {welcome:'தினமும் சிறப்பாகக் கற்போம்.',subtitle:'புத்தகங்கள், கணிப்பான்கள் மற்றும் பயனுள்ள கருவிகள்.',search:'கருவிகளைத் தேடுங்கள்…',back:'← எல்லா கருவிகளும்',tasks:'🗓️ எனது பணிகள்',profile:'👤 எனது சுயவிவரம்',libraryHeading:'உங்கள் புத்தக நூலகம்',openLibrary:'புத்தக நூலகத்தைத் திறக்கவும் ↗',navHome:'முகப்பு',navLibrary:'நூலகம்',navTools:'கருவிகள்',navPlanner:'திட்டம்',navProfile:'சுயவிவரம்',explore:'கருவிகளைப் பாருங்கள்',toolsUnit:'கருவிகள்',empty:'பொருந்தும் கருவிகள் இல்லை. வேறு சொல் முயற்சிக்கவும்.'},
 si: {welcome:'සෑම දිනකම වඩා හොඳින් ඉගෙන ගන්න.',subtitle:'පොත්, ගණක යන්ත්‍ර සහ ප්‍රයෝජනවත් මෙවලම්.',search:'මෙවලම් සොයන්න…',back:'← සියලු මෙවලම්',tasks:'🗓️ මගේ කාර්යයන්',profile:'👤 මගේ පැතිකඩ',libraryHeading:'ඔබේ පොත් පුස්තකාලය',openLibrary:'පොත් පුස්තකාලය විවෘත කරන්න ↗',navHome:'මුල් පිටුව',navLibrary:'පුස්තකාලය',navTools:'මෙවලම්',navPlanner:'සැලසුම්',navProfile:'පැතිකඩ',explore:'මෙවලම් සොයන්න',toolsUnit:'මෙවලම්',empty:'ගැළපෙන මෙවලම් නැත. වෙනත් වචනයක් භාවිතා කරන්න.'}
};
export const CATEGORY_TRANSLATIONS = {
 en: {},
 ta: {'All':'அனைத்தும்','Date & Time':'தேதி & நேரம்','Converters':'மாற்றிகள்','Calculators':'கணிப்பான்கள்','Generators':'உருவாக்கிகள்','Text & Study':'உரை & கல்வி','Productivity':'உற்பத்தித்திறன்','Image Tools':'படக் கருவிகள்','Fun & Learning':'விளையாட்டும் கல்வியும்','Favorites':'பிடித்தவை'},
 si: {'All':'සියල්ල','Date & Time':'දිනය සහ වේලාව','Converters':'පරිවර්තක','Calculators':'ගණක යන්ත්‍ර','Generators':'නිර්මාණ','Text & Study':'පෙළ සහ අධ්‍යයනය','Productivity':'ඵලදායීතාව','Image Tools':'රූප මෙවලම්','Fun & Learning':'විනෝදය සහ ඉගෙනීම','Favorites':'ප්‍රියතම'}
};
export const TOOL_NAME_TRANSLATIONS = {
 ta: {
 'date-difference':'தேதி வித்தியாசம்','date-add':'தேதி கூட்டல் / கழித்தல்','age':'வயது கணிப்பான்','day-of-year':'ஆண்டின் நாள்','epoch':'யூனிக்ஸ் நேரம்','world-clock':'உலகக் கடிகாரம்','timer':'நேரக் கணிப்பான்','stopwatch':'ஸ்டாப்வாட்ச்','unit':'அலகு மாற்றி','temperature':'வெப்பநிலை','base':'எண் முறை மாற்றி','calculator':'கணிப்பான்','percent':'சதவீதம்','discount':'தள்ளுபடி','bmi':'BMI கணிப்பான்','electricity':'மின்சார சக்தி','password':'கடவுச்சொல் உருவாக்கி','uuid':'UUID உருவாக்கி','random':'சீரற்ற எண்','word-count':'சொல் எண்ணி','text-case':'எழுத்து மாற்றி','todo':'செயல் பட்டியல்','pomodoro':'கவன நேரம்','image-compress':'படச் சுருக்கம்','image-strip':'படத் தகவல் நீக்கம்','image-watermark':'பட நீர்க்குறி','signature':'கையொப்பப் பலகை','coin':'நாணயம் சுண்டுதல்','dice':'பகடை உருட்டுதல்','reaction':'எதிர்வினை நேரம்',
 'weekday':'வாரத்தின் நாள்','days-until':'மீதமுள்ள நாட்கள்','month-shift':'மாதங்கள் கூட்டல் / கழித்தல்','time-duration':'நேர இடைவெளி','fraction':'பின்னம் சுருக்கம்','ratio':'விகிதம் சுருக்கம்','average':'சராசரி & நடுக்கோடு','gpa':'GPA கணிப்பான்','tip':'டிப் & பில் பகிர்வு','simple-interest':'தனிவட்டி','compound-interest':'கூட்டுவட்டி','loan-payment':'கடன் தவணை','prime':'பகா எண் சோதனை','square-root':'வர்க்கமூலம்','text-sort':'வரிகளை வரிசைப்படுத்து','text-unique':'நகல் வரிகளை நீக்கு','reading-time':'வாசிப்பு நேரம்','text-reverse':'உரையைத் திருப்பு','url-encode':'URL குறியாக்கம்','color-contrast':'நிற வேறுபாடு'
 },
 si: {
 'date-difference':'දින අතර වෙනස','date-add':'දින එකතු / අඩු','age':'වයස් ගණකය','day-of-year':'වසරේ දිනය','epoch':'යුනික්ස් වේලාව','world-clock':'ලෝක ඔරලෝසුව','timer':'ටයිමරය','stopwatch':'නැවතුම් ඔරලෝසුව','unit':'ඒකක පරිවර්තකය','temperature':'උෂ්ණත්වය','base':'සංඛ්‍යා පද්ධති','calculator':'ගණක යන්ත්‍රය','percent':'ප්‍රතිශතය','discount':'වට්ටම','bmi':'BMI ගණකය','electricity':'විදුලි බලය','password':'මුරපද නිර්මාණය','uuid':'UUID නිර්මාණය','random':'අහඹු අංකය','word-count':'වචන ගණන','text-case':'අකුරු වෙනස් කිරීම','todo':'කාර්ය ලැයිස්තුව','pomodoro':'අවධානයේ කාලය','image-compress':'රූප සම්පීඩනය','image-strip':'රූප තොරතුරු ඉවත් කිරීම','image-watermark':'රූප දියසලකුණ','signature':'අත්සන','coin':'කාසි පෙරළීම','dice':'දාදු පෙරළීම','reaction':'ප්‍රතිචාර වේලාව',
 'weekday':'සතියේ දිනය','days-until':'ඉතිරි දින ගණන','month-shift':'මාස එකතු / අඩු','time-duration':'කාල පරතරය','fraction':'භාගය සරල කිරීම','ratio':'අනුපාතය සරල කිරීම','average':'සාමාන්‍යය සහ මධ්‍යස්ථය','gpa':'GPA ගණකය','tip':'බිල බෙදීම','simple-interest':'සරල පොලිය','compound-interest':'සංයුක්ත පොලිය','loan-payment':'ණය වාරිකය','prime':'ප්‍රථමක සංඛ්‍යා','square-root':'වර්ගමූලය','text-sort':'පේළි වර්ග කිරීම','text-unique':'අනුපිටපත් පේළි ඉවත් කිරීම','reading-time':'කියවීමේ කාලය','text-reverse':'පෙළ ආපසු හැරවීම','url-encode':'URL කේතනය','color-contrast':'වර්ණ වෙනස'
 }
};
export function displayToolName(tool,lang='en'){return TOOL_NAME_TRANSLATIONS[lang]?.[tool.id]||tool.name;}
export function translateCategory(category,lang='en'){return CATEGORY_TRANSLATIONS[lang]?.[category]||category;}
export function translateUI(key,lang='en'){return UI_TRANSLATIONS[lang]?.[key]||UI_TRANSLATIONS.en[key]||key;}

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

// Additional self-contained study utilities. No network requests and no dynamic code execution.
export function weekdayOf(date){return new Intl.DateTimeFormat('en-US',{timeZone:'UTC',weekday:'long'}).format(toDateUTC(date));}
export function monthShift(value,offset){
 const d=toDateUTC(value),n=natural(offset,'month offset',-1200,1200);
 const first=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+n,1));
 const last=new Date(Date.UTC(first.getUTCFullYear(),first.getUTCMonth()+1,0)).getUTCDate();
 return fmtDate(new Date(Date.UTC(first.getUTCFullYear(),first.getUTCMonth(),Math.min(d.getUTCDate(),last))));
}
export function timeDuration(start,end){
 const minutes=t=>{if(!/^\d{2}:\d{2}$/.test(String(t)))throw Error('Enter time as HH:MM.');const [h,m]=t.split(':').map(Number);if(h>23||m>59)throw Error('Invalid 24-hour time.');return h*60+m;};
 const a=minutes(start),b=minutes(end),diff=(b-a+1440)%1440;
 return {hours:Math.floor(diff/60),minutes:diff%60,totalMinutes:diff,overnight:b<a};
}
export function fractionReduce(numerator,denominator){
 const a=natural(numerator,'numerator',-1e9,1e9),b=natural(denominator,'denominator',-1e9,1e9);
 if(b===0)throw Error('Denominator cannot be zero.');
 const gcd=(a,b)=>{while(b){[a,b]=[b,a%b];}return Math.abs(a);};
 const g=gcd(Math.abs(a),Math.abs(b));return {numerator:a===0?0:a/g*(b<0?-1:1),denominator:Math.abs(b/g)};
}
export function ratioReduce(a,b){const x=natural(a,'first part',0,1e9),y=natural(b,'second part',0,1e9);if(x===0&&y===0)throw Error('Both ratio values cannot be zero.');const r=fractionReduce(x,y===0?1:y);if(y===0)return {left:1,right:0};return {left:r.numerator,right:r.denominator};}
function numericList(value,max=500){
 const raw=String(value??'').trim();if(!raw)throw Error('Enter numeric values.');
 const parts=raw.split(/[\s,;]+/).filter(Boolean);if(parts.length>max)throw Error(`Maximum ${max} values.`);
 return parts.map((x,i)=>num(x,`value ${i+1}`));
}
export function meanMedian(value){const values=numericList(value),sorted=[...values].sort((a,b)=>a-b),n=values.length,total=values.reduce((a,b)=>a+b,0);return {count:n,mean:total/n,median:n%2?sorted[(n-1)/2]:(sorted[n/2-1]+sorted[n/2])/2,min:sorted[0],max:sorted[n-1]};}
export function weightedGpa(rows){
 const lines=String(rows??'').trim().split(/\r?\n/).filter(s=>s.trim());if(!lines.length||lines.length>60)throw Error('Enter 1–60 rows of credits,grade points.');
 let credits=0,weighted=0;
 for(const [index,line] of lines.entries()){const pair=line.split(',').map(x=>x.trim());if(pair.length!==2)throw Error(`Row ${index+1}: use credits,grade points.`);const c=num(pair[0],'credits'),g=num(pair[1],'grade points');if(c<=0||c>100||g<0||g>4)throw Error(`Row ${index+1}: credits must be 0–100 and points 0–4.`);credits+=c;weighted+=c*g;}
 return {credits,gpa:weighted/credits};
}
export function billSplit(price,tipPercent,people){const p=num(price,'bill'),r=num(tipPercent,'tip'),n=natural(people,'people',1,1000);if(p<0||r<0||r>100)throw Error('Bill must be nonnegative and tip 0–100%.');const tip=p*r/100,total=p+tip;return {tip,total,perPerson:total/n};}
export function simpleInterest(principal,annualRate,years){const p=num(principal,'principal'),r=num(annualRate,'rate'),t=num(years,'years');if(p<0||r<0||r>100||t<0||t>100)throw Error('Principal must be nonnegative, rate 0–100%, years 0–100.');return {interest:p*r*t/100,total:p*(1+r*t/100)};}
export function compoundInterest(principal,annualRate,years,perYear){const p=num(principal,'principal'),r=num(annualRate,'rate'),t=num(years,'years'),n=natural(perYear,'compoundings per year',1,365);if(p<0||r<0||r>100||t<0||t>100)throw Error('Principal must be nonnegative, rate 0–100%, years 0–100.');const total=p*(1+r/100/n)**(n*t);if(!Number.isFinite(total))throw Error('Result out of range.');return {interest:total-p,total};}
export function loanPayment(principal,annualRate,years){const p=num(principal,'principal'),r=num(annualRate,'rate'),t=num(years,'years');if(p<=0||r<0||r>100||t<=0||t>50)throw Error('Principal must be positive, rate 0–100%, term >0 and up to 50 years.');const n=t*12,monthlyRate=r/1200,monthly=monthlyRate===0?p/n:p*monthlyRate/(1-(1+monthlyRate)**(-n));return {monthly,total:monthly*n,interest:monthly*n-p};}
export function isPrimeNumber(value){const n=natural(value,'integer',0,10000000);if(n<2)return false;if(n===2)return true;if(n%2===0)return false;for(let i=3;i*i<=n;i+=2)if(n%i===0)return false;return true;}
export function squareRoot(value){const x=num(value,'number');if(x<0)throw Error('Enter a nonnegative number.');return Math.sqrt(x);}
export function sortLines(text){const lines=String(text||'').split(/\r?\n/).filter(x=>x.trim());if(lines.length>500)throw Error('Maximum 500 lines.');return lines.sort((a,b)=>a.localeCompare(b,undefined,{sensitivity:'base',numeric:true})).join('\n');}
export function uniqueLines(text,ignoreCase=false){const seen=new Set(),out=[];for(const line of String(text||'').split(/\r?\n/)){if(!line.trim())continue;const key=ignoreCase?line.trim().toLocaleLowerCase():line.trim();if(!seen.has(key)){if(out.length>=500)throw Error('Maximum 500 unique lines.');seen.add(key);out.push(line);}}return out.join('\n');}
export function readingTime(text,wordsPerMinute=200){const pace=natural(wordsPerMinute,'reading speed',80,500),count=wordCount(text).words;return {words:count,minutes:count/pace,seconds:Math.ceil(count/pace*60)};}
export function reverseText(text){return Array.from(String(text||'')).reverse().join('');}
export function urlComponent(text,operation='encode'){if(operation==='encode')return encodeURIComponent(String(text||''));if(operation==='decode')return decodeURIComponent(String(text||''));throw Error('Choose encode or decode.');}
export function colorContrast(foreground,background){const parse=(value)=>{const t=String(value||'').trim();if(!/^#[0-9a-f]{6}$/i.test(t))throw Error('Use a 6-digit hex color like #FFFFFF.');const rgb=[1,3,5].map(i=>parseInt(t.slice(i,i+2),16)/255).map(v=>v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4);return 0.2126*rgb[0]+0.7152*rgb[1]+0.0722*rgb[2];};const a=parse(foreground),b=parse(background),ratio=(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);return {ratio,normal:ratio>=4.5,large:ratio>=3};}

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
 case 'weekday':return weekdayOf(f.date);
 case 'days-until':{const r=dateDifference(f.start,f.end);return `${r.days} days (${r.business} weekdays, ${r.weekends} weekend days)`;}
 case 'month-shift':return monthShift(f.date,f.offset);
 case 'time-duration':{const r=timeDuration(f.start,f.end);return `${r.hours} hours, ${r.minutes} minutes${r.overnight?' (overnight)':''}`;}
 case 'fraction':{const r=fractionReduce(f.numerator,f.denominator);return `${r.numerator}/${r.denominator}`;}
 case 'ratio':{const r=ratioReduce(f.left,f.right);return `${r.left}:${r.right}`;}
 case 'average':{const r=meanMedian(f.values);return `Count: ${r.count}\nMean: ${nice(r.mean,4)}\nMedian: ${nice(r.median,4)}\nMin: ${nice(r.min)} · Max: ${nice(r.max)}`;}
 case 'gpa':{const r=weightedGpa(f.rows);return `Weighted GPA: ${nice(r.gpa,3)} / 4.000\nCredits: ${nice(r.credits,2)}\nEnter numerical grade points on a 0–4 scale; this is not a university-specific GPA policy.`;}
 case 'tip':{const r=billSplit(f.amount,f.tip,f.people);return `Tip: ${nice(r.tip,2)}\nTotal: ${nice(r.total,2)}\nEach person: ${nice(r.perPerson,2)}`;}
 case 'simple-interest':{const r=simpleInterest(f.principal,f.rate,f.years);return `Interest: ${nice(r.interest,2)}\nTotal: ${nice(r.total,2)}`;}
 case 'compound-interest':{const r=compoundInterest(f.principal,f.rate,f.years,f.times);return `Interest: ${nice(r.interest,2)}\nTotal: ${nice(r.total,2)}\nEstimate, before fees or taxes.`;}
 case 'loan-payment':{const r=loanPayment(f.principal,f.rate,f.years);return `Monthly: ${nice(r.monthly,2)}\nTotal payments: ${nice(r.total,2)}\nTotal interest: ${nice(r.interest,2)}\nFixed rate, no fees or taxes.`;}
 case 'prime':return isPrimeNumber(f.value)?'Prime number':'Not prime';
 case 'square-root':return nice(squareRoot(f.value),9);
 case 'text-sort':return sortLines(f.text);
 case 'text-unique':return uniqueLines(f.text,Boolean(f.ignoreCase));
 case 'reading-time':{const r=readingTime(f.text,f.speed);return `${r.words} words · approximately ${r.seconds} seconds (${nice(r.minutes,2)} minutes)`;}
 case 'text-reverse':return reverseText(f.text);
 case 'url-encode':return urlComponent(f.text,f.mode);
 case 'color-contrast':{const r=colorContrast(f.foreground,f.background);return `WCAG contrast: ${nice(r.ratio,2)}:1\nNormal-size AA text: ${r.normal?'Pass':'Fail'}\nLarge-size AA text: ${r.large?'Pass':'Fail'}\nApplies to solid colors without alpha.`;}
 case 'random':return String(secureRandom(f.min,f.max));
 default:throw Error('This tool needs its interactive panel.');}}
export const FORMAT = nice;

// V12 development: reviewed interface labels. Calculation results remain English in this stage.
export const EXTRA_UI_TRANSLATIONS = {
 "en": {
  "calculate": "Calculate",
  "copyResult": "Copy result",
  "resultCopied": "Result copied.",
  "copyUnavailable": "Copy is unavailable.",
  "taskPlaceholder": "Add an assignment or goal…",
  "add": "Add",
  "taskEmpty": "No tasks yet.",
  "taskLocalOnly": "These quick tasks stay on this device. Assignments and exams below come from your existing bot.",
  "plannerReadOnly": "Assignments and exams are read-only here. Edit them using the existing Telegram bot.",
  "plannerAssignments": "Upcoming assignments",
  "plannerExams": "Upcoming exams",
  "plannerLoading": "Loading your academic plan…",
  "plannerRefresh": "Refresh",
  "plannerNoAssignments": "No pending assignments.",
  "plannerNoExams": "No upcoming exams.",
  "plannerUnavailable": "Could not load saved academic records. Check your Telegram session and try again.",
  "plannerNotSynced": "Device tasks are not synchronized across devices.",
  "plannerBotHelp": "Edit assignments, exams or reminders in your Telegram bot.",
  "openBot": "Open Student Assistant Bot",
  "privacyLine": "Your user data is visible only to your signed Telegram session.",
  "deviceOnly": "Favorites and quick tasks are saved only in this browser. They are not synced to Supabase.",
  "libraryInfo": "Continue using your existing live Library, with searches, favorites and reading progress.",
  "libraryKeep": "The existing /library page and API remain unchanged.",
  "tagline": "EVERYTHING IN ONE PLACE",
  "taskLimit": "Task limit: 100 on this device.",
  "markDone": "Mark task complete",
  "deleteTask": "Delete task",
  "openPlanner": "Open Planner",
  "taskHelp": "Tasks are stored on this device only, not synchronized.",
  "authOpening": "Checking Telegram access…",
  "authOpen": "Open this Mini App from your Student Assistant bot.",
  "openFromTelegram": "Open from Telegram",
  "sessionRequired": "This dashboard requires signed Telegram Mini App access and a verified 18+ account.",
  "authUnavailable": "Access unavailable",
  "authRetry": "Please reopen from the bot.",
  "completed": "Completed",
  "noLocation": "No location",
  "plannerHead": "🗓️ My study plan",
  "quickTasks": "Quick tasks on this device"
 },
 "ta": {
  "calculate": "கணக்கிடு",
  "copyResult": "முடிவை நகலெடு",
  "resultCopied": "முடிவு நகலெடுக்கப்பட்டது.",
  "copyUnavailable": "நகலெடுக்க முடியவில்லை.",
  "taskPlaceholder": "பணி அல்லது இலக்கைச் சேர்க்கவும்…",
  "add": "சேர்",
  "taskEmpty": "இன்னும் பணிகள் இல்லை.",
  "taskLocalOnly": "இந்த விரைவுப் பணிகள் இச்சாதனத்தில் மட்டுமே சேமிக்கப்படும். கீழே உள்ள ஒப்படைப்புகளும் தேர்வுகளும் உங்கள் Bot-இலிருந்து வருகின்றன.",
  "plannerReadOnly": "ஒப்படைப்புகளையும் தேர்வுகளையும் இங்கே பார்க்க மட்டுமே முடியும். மாற்றுவதற்கு Telegram Bot-ஐப் பயன்படுத்தவும்.",
  "plannerAssignments": "வரவிருக்கும் ஒப்படைப்புகள்",
  "plannerExams": "வரவிருக்கும் தேர்வுகள்",
  "plannerLoading": "உங்கள் கல்வித் திட்டம் ஏற்றப்படுகிறது…",
  "plannerRefresh": "புதுப்பி",
  "plannerNoAssignments": "நிலுவையிலுள்ள ஒப்படைப்புகள் இல்லை.",
  "plannerNoExams": "வரவிருக்கும் தேர்வுகள் இல்லை.",
  "plannerUnavailable": "கல்வித் தகவல்களைப் பெற முடியவில்லை. Telegram அமர்வைச் சரிபார்த்து மீண்டும் முயலவும்.",
  "plannerNotSynced": "இந்தச் சாதனத்தின் பணிகள் பிற சாதனங்களுடன் ஒத்திசைக்கப்படாது.",
  "plannerBotHelp": "ஒப்படைப்புகள், தேர்வுகள், நினைவூட்டல்களை Telegram Bot-இல் மாற்றவும்.",
  "openBot": "Student Assistant Bot-ஐத் திறக்கவும்",
  "privacyLine": "சரிபார்க்கப்பட்ட உங்கள் Telegram அமர்வில் மட்டுமே தனிப்பட்ட தகவல்கள் காட்டப்படும்.",
  "deviceOnly": "பிடித்தவை மற்றும் விரைவுப் பணிகள் இந்த உலாவியில் மட்டுமே சேமிக்கப்படும்; Supabase-உடன் ஒத்திசைக்கப்படாது.",
  "libraryInfo": "தேடல், பிடித்தவை, வாசிப்பு முன்னேற்றம் கொண்ட தற்போதைய நூலகத்தைத் தொடர்ந்து பயன்படுத்தவும்.",
  "libraryKeep": "தற்போதைய /library பக்கமும் API-யும் மாற்றப்படவில்லை.",
  "tagline": "எல்லாம் ஒரே இடத்தில்",
  "taskLimit": "இந்தச் சாதனத்தில் அதிகபட்சம் 100 பணிகள்.",
  "markDone": "பணியை முடித்ததாகக் குறி",
  "deleteTask": "பணியை நீக்கு",
  "openPlanner": "திட்டத்தைத் திறக்கவும்",
  "taskHelp": "பணிகள் இந்தச் சாதனத்தில் மட்டுமே சேமிக்கப்படுகின்றன.",
  "authOpening": "Telegram அணுகல் சரிபார்க்கப்படுகிறது…",
  "authOpen": "Student Assistant Bot-இலிருந்து Mini App-ஐத் திறக்கவும்.",
  "openFromTelegram": "Telegram-இலிருந்து திறக்கவும்",
  "sessionRequired": "கையொப்பமிடப்பட்ட Telegram அணுகலும் சரிபார்க்கப்பட்ட 18+ கணக்கும் தேவை.",
  "authUnavailable": "அணுக முடியவில்லை",
  "authRetry": "Bot-இலிருந்து மீண்டும் திறக்கவும்.",
  "completed": "முடிந்தது",
  "noLocation": "இடம் குறிப்பிடப்படவில்லை",
  "plannerHead": "🗓️ எனது கல்வித் திட்டம்",
  "quickTasks": "இந்தச் சாதனத்தின் விரைவுப் பணிகள்"
 },
 "si": {
  "calculate": "ගණනය කරන්න",
  "copyResult": "ප්‍රතිඵලය පිටපත් කරන්න",
  "resultCopied": "ප්‍රතිඵලය පිටපත් කළා.",
  "copyUnavailable": "පිටපත් කළ නොහැක.",
  "taskPlaceholder": "කාර්යයක් හෝ ඉලක්කයක් එක් කරන්න…",
  "add": "එක් කරන්න",
  "taskEmpty": "තවම කාර්යයන් නැත.",
  "taskLocalOnly": "මෙම ඉක්මන් කාර්යයන් මෙම උපාංගයේ පමණක් සුරැකේ. පහත පැවරුම් සහ විභාග ඔබේ Bot වෙතින් ලබාගනී.",
  "plannerReadOnly": "පැවරුම් සහ විභාග මෙහි කියවීමට පමණි. වෙනස් කිරීමට Telegram Bot භාවිතා කරන්න.",
  "plannerAssignments": "ඉදිරි පැවරුම්",
  "plannerExams": "ඉදිරි විභාග",
  "plannerLoading": "අධ්‍යයන සැලැස්ම පූරණය වේ…",
  "plannerRefresh": "යාවත්කාලීන කරන්න",
  "plannerNoAssignments": "පොරොත්තු පැවරුම් නැත.",
  "plannerNoExams": "ඉදිරි විභාග නැත.",
  "plannerUnavailable": "අධ්‍යයන දත්ත ලබාගත නොහැක. Telegram සැසිය පරීක්ෂා කර නැවත උත්සාහ කරන්න.",
  "plannerNotSynced": "උපාංග කාර්යයන් වෙනත් උපාංග සමඟ සමමුහුර්ත නොවේ.",
  "plannerBotHelp": "පැවරුම්, විභාග සහ සිහිකැඳවීම් Telegram Bot තුළ වෙනස් කරන්න.",
  "openBot": "Student Assistant Bot විවෘත කරන්න",
  "privacyLine": "ඔබේ පුද්ගලික තොරතුරු සත්‍යාපිත Telegram සැසියට පමණක් පෙන්වයි.",
  "deviceOnly": "ප්‍රියතම සහ ඉක්මන් කාර්යයන් මෙම බ්‍රවුසරයේ පමණක් සුරැකේ; Supabase සමඟ සමමුහුර්ත නොවේ.",
  "libraryInfo": "සෙවීම, ප්‍රියතම සහ කියවීමේ ප්‍රගතිය සමඟ පවතින පුස්තකාලය භාවිතා කරන්න.",
  "libraryKeep": "පවතින /library පිටුව සහ API වෙනස් කර නැත.",
  "tagline": "සියල්ල එකම තැනක",
  "taskLimit": "මෙම උපාංගයේ කාර්යයන් 100 ක් පමණි.",
  "markDone": "කාර්යය නිම කළ ලෙස සලකුණු කරන්න",
  "deleteTask": "කාර්යය මකන්න",
  "openPlanner": "සැලසුම විවෘත කරන්න",
  "taskHelp": "කාර්යයන් මෙම උපාංගයේ පමණක් සුරැකේ.",
  "authOpening": "Telegram ප්‍රවේශය පරීක්ෂා වේ…",
  "authOpen": "Student Assistant Bot වෙතින් Mini App විවෘත කරන්න.",
  "openFromTelegram": "Telegram වෙතින් විවෘත කරන්න",
  "sessionRequired": "අත්සන් කළ Telegram ප්‍රවේශය සහ සත්‍යාපිත 18+ ගිණුමක් අවශ්‍යයි.",
  "authUnavailable": "ප්‍රවේශය නොමැත",
  "authRetry": "Bot වෙතින් නැවත විවෘත කරන්න.",
  "completed": "නිමයි",
  "noLocation": "ස්ථානයක් නැත",
  "plannerHead": "🗓️ මගේ අධ්‍යයන සැලැස්ම",
  "quickTasks": "මෙම උපාංගයේ ඉක්මන් කාර්යයන්"
 }
};
export const FIELD_LABEL_TRANSLATIONS = {
 "ta": {
  "Action": "செயல்",
  "Annual rate (%)": "ஆண்டு வட்டி வீதம் (%)",
  "As of": "கணக்கிடும் தேதி",
  "Background hex": "பின்னணி நிறக் குறியீடு",
  "Bill amount": "பில் தொகை",
  "Category": "வகை",
  "Change to": "இதற்கு மாற்று",
  "Compoundings per year": "ஆண்டுக்கு வட்டி சேர்க்கும் தடவைகள்",
  "Credits,grade points (one course per line)": "பாடநெறிக்கு வரவு, மதிப்பெண் (ஒரு வரியில் ஒன்று)",
  "Current (A)": "மின்னோட்டம் (A)",
  "Date": "தேதி",
  "Date of birth": "பிறந்த தேதி",
  "Days to add (negative to subtract)": "சேர்க்க வேண்டிய நாட்கள் (கழிக்க எதிர்மறை எண்)",
  "Denominator": "பகுதி எண்",
  "Discount %": "தள்ளுபடி %",
  "End (24h)": "முடிவு (24 மணி)",
  "End date": "முடிவு தேதி",
  "First number": "முதல் எண்",
  "Foreground hex": "முன்புற நிறக் குறியீடு",
  "From": "இதிலிருந்து",
  "From base (2–36)": "தொடக்க எண் முறை (2–36)",
  "Height (cm)": "உயரம் (செ.மீ.)",
  "Ignore capitalization": "பெரிய/சிறிய எழுத்து வேறுபாட்டைப் புறக்கணி",
  "Include end date": "முடிவு தேதியையும் சேர்",
  "Include symbols": "குறியீடுகளையும் சேர்",
  "Integer": "முழு எண்",
  "Integer (0–10000000)": "முழு எண் (0–10000000)",
  "JPEG quality 0.1–1": "JPEG தரம் 0.1–1",
  "Length (8–128)": "நீளம் (8–128)",
  "Lines": "வரிகள்",
  "Lines to sort": "வரிசைப்படுத்த வேண்டிய வரிகள்",
  "Loan amount": "கடன் தொகை",
  "Loan term (years)": "கடன் காலம் (ஆண்டுகள்)",
  "Maximum": "அதிகபட்சம்",
  "Minimum": "குறைந்தபட்சம்",
  "Minutes": "நிமிடங்கள்",
  "Months (+ or -)": "மாதங்கள் (+ அல்லது -)",
  "Nonnegative number": "எதிர்மறையல்லாத எண்",
  "Number (1–20)": "எண்ணிக்கை (1–20)",
  "Number of people": "நபர்கள் எண்ணிக்கை",
  "Numerator": "மேல் எண்",
  "Of number": "இந்த எண்ணின்",
  "Operation": "கணிதச் செயல்",
  "Original price": "மூல விலை",
  "Passage": "உரைப் பகுதி",
  "Percentage": "சதவீதம்",
  "Principal amount": "முதன்மைத் தொகை",
  "Second number": "இரண்டாம் எண்",
  "Select photo": "படத்தைத் தேர்வு செய்க",
  "Start (24h)": "தொடக்கம் (24 மணி)",
  "Start date": "தொடக்க தேதி",
  "Target date": "இலக்கு தேதி",
  "Temperature": "வெப்பநிலை",
  "Text": "உரை",
  "Text or URL component": "உரை அல்லது URL பகுதி",
  "Tip percentage": "டிப் சதவீதம்",
  "To": "இதற்கு",
  "To base (2–36)": "இலக்கு எண் முறை (2–36)",
  "Unit": "அலகு",
  "Unix timestamp": "யூனிக்ஸ் நேரமுத்திரை",
  "Value": "மதிப்பு",
  "Values (commas or new lines)": "மதிப்புகள் (காற்புள்ளி / புதிய வரி)",
  "Voltage (V)": "மின்னழுத்தம் (V)",
  "Watermark text": "நீர்க்குறி உரை",
  "Weight (kg)": "எடை (கி.கி.)",
  "Words per minute (80–500)": "நிமிடத்திற்கு சொற்கள் (80–500)",
  "Years": "ஆண்டுகள்"
 },
 "si": {
  "Action": "ක්‍රියාව",
  "Annual rate (%)": "වාර්ෂික පොලී අනුපාතය (%)",
  "As of": "ගණනය කරන දිනය",
  "Background hex": "පසුබිම් වර්ණ කේතය",
  "Bill amount": "බිල් මුදල",
  "Category": "කාණ්ඩය",
  "Change to": "මෙයට වෙනස් කරන්න",
  "Compoundings per year": "වසරකට සංයුක්ත වාර ගණන",
  "Credits,grade points (one course per line)": "පාඨමාලා ණය, ශ්‍රේණි ලකුණු (පේළියකට එකක්)",
  "Current (A)": "ධාරාව (A)",
  "Date": "දිනය",
  "Date of birth": "උපන් දිනය",
  "Days to add (negative to subtract)": "එක් කරන දින (අඩු කිරීමට ඍණ අගය)",
  "Denominator": "හරය",
  "Discount %": "වට්ටම %",
  "End (24h)": "අවසන් වේලාව (පැය 24)",
  "End date": "අවසන් දිනය",
  "First number": "පළමු අංකය",
  "Foreground hex": "ඉදිරිපස වර්ණ කේතය",
  "From": "සිට",
  "From base (2–36)": "මුල් සංඛ්‍යා පාදය (2–36)",
  "Height (cm)": "උස (සෙ.මී.)",
  "Ignore capitalization": "ලොකු/කුඩා අකුරු නොසලකන්න",
  "Include end date": "අවසන් දිනයත් ඇතුළත් කරන්න",
  "Include symbols": "සංකේත ඇතුළත් කරන්න",
  "Integer": "පූර්ණ සංඛ්‍යාව",
  "Integer (0–10000000)": "පූර්ණ සංඛ්‍යාව (0–10000000)",
  "JPEG quality 0.1–1": "JPEG ගුණාත්මකභාවය 0.1–1",
  "Length (8–128)": "දිග (8–128)",
  "Lines": "පේළි",
  "Lines to sort": "අනුපිළිවෙළට සකසන පේළි",
  "Loan amount": "ණය මුදල",
  "Loan term (years)": "ණය කාලය (වසර)",
  "Maximum": "උපරිමය",
  "Minimum": "අවමය",
  "Minutes": "මිනිත්තු",
  "Months (+ or -)": "මාස (+ හෝ -)",
  "Nonnegative number": "ඍණ නොවන අංකය",
  "Number (1–20)": "ගණන (1–20)",
  "Number of people": "පුද්ගලයන් ගණන",
  "Numerator": "ලවය",
  "Of number": "මෙම අංකයෙන්",
  "Operation": "ගණිත ක්‍රියාව",
  "Original price": "මුල් මිල",
  "Passage": "ඡේදය",
  "Percentage": "ප්‍රතිශතය",
  "Principal amount": "මුල් මුදල",
  "Second number": "දෙවන අංකය",
  "Select photo": "රූපයක් තෝරන්න",
  "Start (24h)": "ආරම්භය (පැය 24)",
  "Start date": "ආරම්භක දිනය",
  "Target date": "ඉලක්ක දිනය",
  "Temperature": "උෂ්ණත්වය",
  "Text": "පෙළ",
  "Text or URL component": "පෙළ හෝ URL කොටස",
  "Tip percentage": "ටිප ප්‍රතිශතය",
  "To": "දක්වා",
  "To base (2–36)": "ඉලක්ක පාදය (2–36)",
  "Unit": "ඒකකය",
  "Unix timestamp": "යුනික්ස් කාල මුද්‍රාව",
  "Value": "අගය",
  "Values (commas or new lines)": "අගයන් (කොමා හෝ නව පේළි)",
  "Voltage (V)": "වෝල්ටීයතාව (V)",
  "Watermark text": "දිය සලකුණ පෙළ",
  "Weight (kg)": "බර (කි.ග්‍රෑ.)",
  "Words per minute (80–500)": "මිනිත්තුවකට වචන (80–500)",
  "Years": "වසර"
 }
};
export function localUI(key,lang="en"){return EXTRA_UI_TRANSLATIONS[lang]?.[key] || translateUI(key,lang);}
export function localField(label,lang="en"){return FIELD_LABEL_TRANSLATIONS[lang]?.[label] || label;}

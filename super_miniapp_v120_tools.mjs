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

// V12 functional QA expansion: no external API, no remote storage.
TOOLS.push(
 {id:'percentage-change',name:'Percentage Change',icon:'📉',category:'Calculators',summary:'Increase or decrease from an original value'},
 {id:'sales-tax',name:'Sales Tax / VAT',icon:'🧾',category:'Calculators',summary:'Tax amount and total price'},
 {id:'profit-margin',name:'Profit & Margin',icon:'💹',category:'Calculators',summary:'Profit, gross margin, and markup'},
 {id:'speed-calc',name:'Average Speed',icon:'🚴',category:'Calculators',summary:'Calculate distance per hour'},
 {id:'grade-percent',name:'Grade Percentage',icon:'📚',category:'Text & Study',summary:'Convert scored marks to a percentage'},
 {id:'stddev',name:'Standard Deviation',icon:'📊',category:'Calculators',summary:'Population and sample standard deviation'},
 {id:'quadratic',name:'Quadratic Equation',icon:'📐',category:'Calculators',summary:'Solve ax² + bx + c = 0, including complex roots'},
 {id:'factorial',name:'Factorial',icon:'🔢',category:'Calculators',summary:'Exact factorial of integers up to 200'},
 {id:'combinations',name:'Combinations (nCr)',icon:'🧩',category:'Calculators',summary:'Exact number of ways to choose k from n'},
 {id:'text-replace',name:'Find & Replace',icon:'🔎',category:'Text & Study',summary:'Replace literal text without regular expressions'},
 {id:'word-frequency',name:'Word Frequency',icon:'🔤',category:'Text & Study',summary:'Most frequent words across languages'},
 {id:'study-sessions',name:'Study Session Planner',icon:'🍅',category:'Productivity',summary:'Estimate total focus and break time'}
);

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
export function wordCount(s){const original=String(s||'');const t=original.trim();const characters=typeof Intl.Segmenter==='function'?[...new Intl.Segmenter(undefined,{granularity:'grapheme'}).segment(original)].length:Array.from(original).length;return {characters,words:t?(t.match(/\S+/gu)||[]).length:0,lines:t?t.split(/\r?\n/).length:0};}
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
export function reverseText(text){const src=String(text||'');const segments=typeof Intl.Segmenter==='function'?[...new Intl.Segmenter(undefined,{granularity:'grapheme'}).segment(src)].map(x=>x.segment):Array.from(src);return segments.reverse().join('');}
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

 case 'percentage-change':return `${nice(percentChange(f.before,f.after),2)}% change`;
 case 'sales-tax':{const r=salesTax(f.price,f.rate);return `Tax: ${nice(r.tax,2)}\nTotal: ${nice(r.total,2)}`;}
 case 'profit-margin':{const r=profitMargin(f.cost,f.price);return `Profit: ${nice(r.profit,2)}\nGross margin: ${nice(r.margin,2)}%\nMarkup: ${r.markup===null?'N/A':nice(r.markup,2)+'%'}`;}
 case 'speed-calc':return `${nice(averageSpeed(f.distance,f.minutes),3)} km/h`;
 case 'grade-percent':return `${nice(gradePercentage(f.scored,f.total),2)}%`;
 case 'stddev':{const r=deviation(f.values);return `Count: ${r.count}\nMean: ${nice(r.mean,4)}\nPopulation σ: ${nice(r.population,4)}\nSample s: ${r.sample===null?'N/A':nice(r.sample,4)}`;}
 case 'quadratic':{const r=quadratic(f.a,f.b,f.c);return r.real?`Roots: ${nice(r.root1,6)}, ${nice(r.root2,6)}\nDiscriminant: ${nice(r.discriminant,6)}`:`Complex roots: ${nice(r.realPart,6)} ± ${nice(r.imaginary,6)}i\nDiscriminant: ${nice(r.discriminant,6)}`;}
 case 'factorial':return factorial(f.n);
 case 'combinations':return combinations(f.n,f.k);
 case 'text-replace':return findReplace(f.text,f.find,f.replace,f.ignoreCase);
 case 'word-frequency':return wordFrequency(f.text).map(([word,n])=>`${word}: ${n}`).join('\n') || 'No words found.';
 case 'study-sessions':{const r=studySessions(f.blocks,f.focus,f.rest);return `Focus: ${r.focus} minutes\nBreaks: ${r.breaks} minutes\nTotal: ${Math.floor(r.total/60)}h ${r.total%60}m`;} 
 case 'random':return String(secureRandom(f.min,f.max));
 case 'json-pretty':return jsonPretty(f.text,f.mode);
 case 'base64-text':return base64Text(f.text,f.mode);
 case 'text-diff':return textDiff(f.before,f.after);
 case 'attendance':{const r=attendancePlan(f.attended,f.total,f.target);return `Current: ${r.current.toFixed(2)}%\n${Number.isFinite(r.needed)?`Attend ${r.needed} consecutive class(es) to reach target.`:'100% cannot be reached if any class was missed.'}`;}
 case 'weighted-grade':{const r=weightedGrades(f.rows);return `Average on graded work: ${r.average.toFixed(2)}%\nTotal weight: ${r.weight.toFixed(2)}%\nContribution to final grade: ${r.contribution.toFixed(2)} points`;}
 case 'csv-inspect':{const r=csvInspect(f.text);return `Rows: ${r.rows}\nColumns: ${r.columns}\nConsistent width: ${r.consistent?'Yes':'No'}\nFirst row: ${r.preview.join(' | ')}`;}
 default:throw Error('This tool needs its interactive panel.');}}

// Additional tested pure calculations. Inputs never leave the device.
export function percentChange(before,after){const a=num(before,'original value'),b=num(after,'new value');if(a===0)throw Error('Original value must be nonzero.');return (b-a)/Math.abs(a)*100;}
export function salesTax(price,rate){const p=num(price,'price'),r=num(rate,'tax rate');if(p<0||r<0||r>100)throw Error('Price must be nonnegative and tax rate 0–100%.');const tax=p*r/100;return {tax,total:p+tax};}
export function profitMargin(cost,price){const c=num(cost,'cost'),p=num(price,'sale price');if(c<0||p<=0)throw Error('Cost must be nonnegative and sale price positive.');const profit=p-c;return {profit,margin:profit/p*100,markup:c===0?null:profit/c*100};}
export function averageSpeed(distance,minutes){const d=num(distance,'distance'),m=num(minutes,'minutes');if(d<0||m<=0)throw Error('Distance cannot be negative and minutes must be positive.');return d*60/m;}
export function gradePercentage(scored,possible){const s=num(scored,'scored marks'),p=num(possible,'total marks');if(s<0||p<=0||s>p)throw Error('Marks must be between zero and the positive total.');return s/p*100;}
export function deviation(value){const text=String(value??'').trim();if(!text)throw Error('Enter numeric values.');const parts=text.split(/[\s,;]+/).filter(Boolean);if(parts.length>500)throw Error('Maximum 500 values.');const vals=parts.map((x,i)=>num(x,`value ${i+1}`));let mean=0,m2=0;for(let i=0;i<vals.length;i++){const delta=vals[i]-mean;mean+=delta/(i+1);m2+=delta*(vals[i]-mean);}return {count:vals.length,mean,population:Math.sqrt(m2/vals.length),sample:vals.length>1?Math.sqrt(m2/(vals.length-1)):null};}
export function quadratic(a,b,c){const x=num(a,'a'),y=num(b,'b'),z=num(c,'c');if(x===0)throw Error('Coefficient a must not be zero.');const d=y*y-4*x*z;if(!Number.isFinite(d))throw Error('Coefficients out of range.');if(d>=0){const r=Math.sqrt(d);return {discriminant:d,real:true,root1:(-y+r)/(2*x),root2:(-y-r)/(2*x)};}return {discriminant:d,real:false,realPart:-y/(2*x),imaginary:Math.sqrt(-d)/(2*Math.abs(x))};}
export function factorial(n){const k=natural(n,'n',0,200);let out=1n;for(let i=2;i<=k;i++)out*=BigInt(i);return out.toString();}
export function combinations(n,k){const a=natural(n,'n',0,200),b=natural(k,'k',0,200);if(b>a)throw Error('k must not exceed n.');const count=Math.min(b,a-b);let answer=1n;for(let i=1;i<=count;i++)answer=answer*BigInt(a-count+i)/BigInt(i);return answer.toString();}
export function findReplace(text,needle,replacement,ignoreCase=false){const src=String(text??'');const term=String(needle??'');if(!term)throw Error('Enter text to find.');if(term.length>1000)throw Error('Search term too long.');const rep=String(replacement??'');if(!ignoreCase)return src.split(term).join(rep);const escaped=term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');return src.replace(new RegExp(escaped,'giu'),()=>rep);}
export function wordFrequency(value){const words=(String(value??'').toLocaleLowerCase().match(/[\p{L}\p{M}\p{N}]+/gu)||[]);const counts=new Map();for(const w of words)counts.set(w,(counts.get(w)||0)+1);return [...counts.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,20);}
export function studySessions(blocks,focus,rest){const n=natural(blocks,'sessions',1,100),f=natural(focus,'focus minutes',1,240),b=natural(rest,'break minutes',0,60);return {focus:n*f,breaks:(n-1)*b,total:n*f+(n-1)*b};}

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
// Additional strings for optional V12 Supabase task sync. User preferences remain local.
export const TASK_SYNC_TRANSLATIONS = {
 en: {
  tasksSynced:'Tasks synchronized across devices.', tasksDeviceFallback:'Offline: tasks on this device only.',
  tasksReadOnly:'Saved tasks are temporarily read-only.', tasksLoading:'Loading synchronized tasks…',
  tasksOffline:'Sync unavailable; changes here will not sync automatically.', tasksRetry:'Could not save. Please retry.',
  taskImportLocal:'Import older device-only tasks', tasksImported:'Previous tasks imported successfully.',
  tasksPartialImport:'Import interrupted. Original tasks are still preserved; retry to continue.',
  taskIdUnavailable:'Secure task ID unavailable on this device.',
  taskHelp:'Quick tasks synchronize when the Mini App is connected. Older device-only tasks can be imported manually.',
  taskLocalOnly:'Quick tasks sync across your devices when connected. Older device-only tasks are preserved until you import them.',
  quickTasks:'My synchronized quick tasks',
  deviceOnly:'Quick tasks sync securely when connected. Favorites and language preferences stay on this device; old device tasks are kept for manual import.',
  taskLimit:'Maximum of 100 quick tasks.',
 },
 ta: {
  tasksSynced:'பணிகள் உங்கள் சாதனங்களில் ஒத்திசைக்கப்பட்டுள்ளன.', tasksDeviceFallback:'இணைப்பு இல்லை: பணிகள் இந்தச் சாதனத்தில் மட்டுமே.',
  tasksReadOnly:'சேமிக்கப்பட்ட பணிகளைத் தற்போது பார்க்க மட்டுமே முடியும்.', tasksLoading:'ஒத்திசைக்கப்பட்ட பணிகள் ஏற்றப்படுகின்றன…',
  tasksOffline:'ஒத்திசைவு கிடைக்கவில்லை; இங்கே செய்யும் மாற்றங்கள் தானாகப் பகிரப்படாது.', tasksRetry:'சேமிக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.',
  taskImportLocal:'பழைய சாதனப் பணிகளை இறக்குமதி செய்', tasksImported:'முந்தைய பணிகள் வெற்றிகரமாக இறக்குமதி செய்யப்பட்டன.',
  tasksPartialImport:'இறக்குமதி இடைநிறுத்தப்பட்டது. பழைய பணிகள் பாதுகாக்கப்பட்டுள்ளன; மீண்டும் முயலவும்.',
  taskIdUnavailable:'பாதுகாப்பான பணி அடையாளத்தை உருவாக்க முடியவில்லை.',
  taskHelp:'இணைய இணைப்புள்ளபோது விரைவுப் பணிகள் ஒத்திசைக்கப்படும். பழைய சாதனப் பணிகளை விருப்பப்படி இறக்குமதி செய்யலாம்.',
  taskLocalOnly:'இணைப்புள்ளபோது விரைவுப் பணிகள் உங்கள் சாதனங்களில் ஒத்திசைக்கப்படும். இறக்குமதி செய்யும் வரை பழைய பணிகள் பாதுகாக்கப்படும்.',
  quickTasks:'எனது ஒத்திசைக்கப்பட்ட விரைவுப் பணிகள்',
  deviceOnly:'விரைவுப் பணிகள் பாதுகாப்பாக ஒத்திசைக்கப்படும். பிடித்தவையும் மொழி விருப்பமும் இந்தச் சாதனத்தில் மட்டுமே. பழைய பணிகளை பின்னர் இறக்குமதி செய்யலாம்.',
  taskLimit:'அதிகபட்சம் 100 விரைவுப் பணிகள்.',
 },
 si: {
  tasksSynced:'කාර්යයන් ඔබේ උපාංග අතර සමමුහුර්ත කර ඇත.', tasksDeviceFallback:'නොබැඳි: කාර්යයන් මෙම උපාංගයේ පමණි.',
  tasksReadOnly:'සුරකින ලද කාර්යයන් තාවකාලිකව නැරඹීමට පමණි.', tasksLoading:'සමමුහුර්ත කළ කාර්යයන් පූරණය වෙමින්…',
  tasksOffline:'සමමුහුර්ත කිරීම නොමැත; මෙහි වෙනස්කම් ස්වයංක්‍රීයව හුවමාරු නොවේ.', tasksRetry:'සුරැකීමට නොහැකි විය. නැවත උත්සාහ කරන්න.',
  taskImportLocal:'පැරණි උපාංගයේ කාර්යයන් ආනයනය කරන්න', tasksImported:'පැරණි කාර්යයන් සාර්ථකව ආනයනය විය.',
  tasksPartialImport:'ආනයනය නතර විය. මුල් කාර්යයන් සුරක්ෂිතයි; නැවත උත්සාහ කරන්න.',
  taskIdUnavailable:'ආරක්ෂිත කාර්ය හැඳුනුම්පතක් ලබාගත නොහැක.',
  taskHelp:'සම්බන්ධතාව ඇති විට ඉක්මන් කාර්යයන් සමමුහුර්ත වේ. පැරණි උපාංග කාර්යයන් අතින් ආනයනය කළ හැක.',
  taskLocalOnly:'සම්බන්ධ වූ විට ඉක්මන් කාර්යයන් ඔබේ උපාංග අතර සමමුහුර්ත වේ. ආනයනය කරන තෙක් පැරණි කාර්යයන් සුරැකේ.',
  quickTasks:'මගේ සමමුහුර්ත ඉක්මන් කාර්යයන්',
  deviceOnly:'ඉක්මන් කාර්යයන් ආරක්ෂිතව සමමුහුර්ත වේ. ප්‍රියතම හා භාෂා සැකසුම් මෙම උපාංගයේ පමණි. පැරණි කාර්යයන් පසුව ආනයනය කළ හැක.',
  taskLimit:'උපරිම ඉක්මන් කාර්යයන් 100 කි.',
 },
};

export function localUI(key,lang="en"){return TASK_SYNC_TRANSLATIONS[lang]?.[key] || EXTRA_UI_TRANSLATIONS[lang]?.[key] || translateUI(key,lang);}
export function localField(label,lang="en"){return FIELD_LABEL_TRANSLATIONS[lang]?.[label] || label;}

// New tools have translated names; unusual numerical output labels remain English.
Object.assign(TOOL_NAME_TRANSLATIONS.ta,{
 'percentage-change':'சதவீத மாற்றம்','sales-tax':'வரி / VAT','profit-margin':'லாபம் & விகிதம்','speed-calc':'சராசரி வேகம்','grade-percent':'மதிப்பெண் சதவீதம்','stddev':'நியம விலகல்','quadratic':'இருபடி சமன்பாடு','factorial':'தொடர்பெருக்கம்','combinations':'சேர்க்கைகள் (nCr)','text-replace':'தேடி மாற்று','word-frequency':'சொல் நிகழ்வெண்','study-sessions':'படிப்பு நேரத் திட்டம்'
});
Object.assign(TOOL_NAME_TRANSLATIONS.si,{
 'percentage-change':'ප්‍රතිශත වෙනස','sales-tax':'විකුණුම් බදු / VAT','profit-margin':'ලාභය සහ ආන්තිකය','speed-calc':'සාමාන්‍ය වේගය','grade-percent':'ලකුණු ප්‍රතිශතය','stddev':'සම්මත අපගමනය','quadratic':'වර්ගජ සමීකරණය','factorial':'ක්‍රමාරෝපිතය','combinations':'සංයෝජන (nCr)','text-replace':'සොයන්න සහ ප්‍රතිස්ථාපනය','word-frequency':'වචන සංඛ්‍යාතය','study-sessions':'අධ්‍යයන කාල සැලැස්ම'
});

// Country / time zone catalog sourced from IANA zone.tab; local browser Intl supplies DST-aware current times.
export const WORLD_CLOCK_ENTRIES = [["AF","Afghanistan","Asia/Kabul"],["AL","Albania","Europe/Tirane"],["DZ","Algeria","Africa/Algiers"],["AS","American Samoa","Pacific/Pago_Pago"],["AD","Andorra","Europe/Andorra"],["AO","Angola","Africa/Luanda"],["AI","Anguilla","America/Anguilla"],["AQ","Antarctica","Antarctica/Casey"],["AQ","Antarctica","Antarctica/Davis"],["AQ","Antarctica","Antarctica/DumontDUrville"],["AQ","Antarctica","Antarctica/Mawson"],["AQ","Antarctica","Antarctica/McMurdo"],["AQ","Antarctica","Antarctica/Palmer"],["AQ","Antarctica","Antarctica/Rothera"],["AQ","Antarctica","Antarctica/Syowa"],["AQ","Antarctica","Antarctica/Troll"],["AQ","Antarctica","Antarctica/Vostok"],["AG","Antigua and Barbuda","America/Antigua"],["AR","Argentina","America/Argentina/Buenos_Aires"],["AR","Argentina","America/Argentina/Catamarca"],["AR","Argentina","America/Argentina/Cordoba"],["AR","Argentina","America/Argentina/Jujuy"],["AR","Argentina","America/Argentina/La_Rioja"],["AR","Argentina","America/Argentina/Mendoza"],["AR","Argentina","America/Argentina/Rio_Gallegos"],["AR","Argentina","America/Argentina/Salta"],["AR","Argentina","America/Argentina/San_Juan"],["AR","Argentina","America/Argentina/San_Luis"],["AR","Argentina","America/Argentina/Tucuman"],["AR","Argentina","America/Argentina/Ushuaia"],["AM","Armenia","Asia/Yerevan"],["AW","Aruba","America/Aruba"],["AU","Australia","Antarctica/Macquarie"],["AU","Australia","Australia/Adelaide"],["AU","Australia","Australia/Brisbane"],["AU","Australia","Australia/Broken_Hill"],["AU","Australia","Australia/Darwin"],["AU","Australia","Australia/Eucla"],["AU","Australia","Australia/Hobart"],["AU","Australia","Australia/Lindeman"],["AU","Australia","Australia/Lord_Howe"],["AU","Australia","Australia/Melbourne"],["AU","Australia","Australia/Perth"],["AU","Australia","Australia/Sydney"],["AT","Austria","Europe/Vienna"],["AZ","Azerbaijan","Asia/Baku"],["BS","Bahamas","America/Nassau"],["BH","Bahrain","Asia/Bahrain"],["BD","Bangladesh","Asia/Dhaka"],["BB","Barbados","America/Barbados"],["BY","Belarus","Europe/Minsk"],["BE","Belgium","Europe/Brussels"],["BZ","Belize","America/Belize"],["BJ","Benin","Africa/Porto-Novo"],["BM","Bermuda","Atlantic/Bermuda"],["BT","Bhutan","Asia/Thimphu"],["BO","Bolivia, Plurinational State of","America/La_Paz"],["BQ","Bonaire, Sint Eustatius and Saba","America/Kralendijk"],["BA","Bosnia and Herzegovina","Europe/Sarajevo"],["BW","Botswana","Africa/Gaborone"],["BR","Brazil","America/Araguaina"],["BR","Brazil","America/Bahia"],["BR","Brazil","America/Belem"],["BR","Brazil","America/Boa_Vista"],["BR","Brazil","America/Campo_Grande"],["BR","Brazil","America/Cuiaba"],["BR","Brazil","America/Eirunepe"],["BR","Brazil","America/Fortaleza"],["BR","Brazil","America/Maceio"],["BR","Brazil","America/Manaus"],["BR","Brazil","America/Noronha"],["BR","Brazil","America/Porto_Velho"],["BR","Brazil","America/Recife"],["BR","Brazil","America/Rio_Branco"],["BR","Brazil","America/Santarem"],["BR","Brazil","America/Sao_Paulo"],["IO","British Indian Ocean Territory","Indian/Chagos"],["BN","Brunei Darussalam","Asia/Brunei"],["BG","Bulgaria","Europe/Sofia"],["BF","Burkina Faso","Africa/Ouagadougou"],["BI","Burundi","Africa/Bujumbura"],["CV","Cabo Verde","Atlantic/Cape_Verde"],["KH","Cambodia","Asia/Phnom_Penh"],["CM","Cameroon","Africa/Douala"],["CA","Canada","America/Atikokan"],["CA","Canada","America/Blanc-Sablon"],["CA","Canada","America/Cambridge_Bay"],["CA","Canada","America/Creston"],["CA","Canada","America/Dawson"],["CA","Canada","America/Dawson_Creek"],["CA","Canada","America/Edmonton"],["CA","Canada","America/Fort_Nelson"],["CA","Canada","America/Glace_Bay"],["CA","Canada","America/Goose_Bay"],["CA","Canada","America/Halifax"],["CA","Canada","America/Inuvik"],["CA","Canada","America/Iqaluit"],["CA","Canada","America/Moncton"],["CA","Canada","America/Rankin_Inlet"],["CA","Canada","America/Regina"],["CA","Canada","America/Resolute"],["CA","Canada","America/St_Johns"],["CA","Canada","America/Swift_Current"],["CA","Canada","America/Toronto"],["CA","Canada","America/Vancouver"],["CA","Canada","America/Whitehorse"],["CA","Canada","America/Winnipeg"],["KY","Cayman Islands","America/Cayman"],["CF","Central African Republic","Africa/Bangui"],["TD","Chad","Africa/Ndjamena"],["CL","Chile","America/Coyhaique"],["CL","Chile","America/Punta_Arenas"],["CL","Chile","America/Santiago"],["CL","Chile","Pacific/Easter"],["CN","China","Asia/Shanghai"],["CN","China","Asia/Urumqi"],["CX","Christmas Island","Indian/Christmas"],["CC","Cocos (Keeling) Islands","Indian/Cocos"],["CO","Colombia","America/Bogota"],["KM","Comoros","Indian/Comoro"],["CG","Congo","Africa/Brazzaville"],["CD","Congo, The Democratic Republic of the","Africa/Kinshasa"],["CD","Congo, The Democratic Republic of the","Africa/Lubumbashi"],["CK","Cook Islands","Pacific/Rarotonga"],["CR","Costa Rica","America/Costa_Rica"],["HR","Croatia","Europe/Zagreb"],["CU","Cuba","America/Havana"],["CW","Curaçao","America/Curacao"],["CY","Cyprus","Asia/Famagusta"],["CY","Cyprus","Asia/Nicosia"],["CZ","Czechia","Europe/Prague"],["CI","Côte d'Ivoire","Africa/Abidjan"],["DK","Denmark","Europe/Copenhagen"],["DJ","Djibouti","Africa/Djibouti"],["DM","Dominica","America/Dominica"],["DO","Dominican Republic","America/Santo_Domingo"],["EC","Ecuador","America/Guayaquil"],["EC","Ecuador","Pacific/Galapagos"],["EG","Egypt","Africa/Cairo"],["SV","El Salvador","America/El_Salvador"],["GQ","Equatorial Guinea","Africa/Malabo"],["ER","Eritrea","Africa/Asmara"],["EE","Estonia","Europe/Tallinn"],["SZ","Eswatini","Africa/Mbabane"],["ET","Ethiopia","Africa/Addis_Ababa"],["FK","Falkland Islands (Malvinas)","Atlantic/Stanley"],["FO","Faroe Islands","Atlantic/Faroe"],["FJ","Fiji","Pacific/Fiji"],["FI","Finland","Europe/Helsinki"],["FR","France","Europe/Paris"],["GF","French Guiana","America/Cayenne"],["PF","French Polynesia","Pacific/Gambier"],["PF","French Polynesia","Pacific/Marquesas"],["PF","French Polynesia","Pacific/Tahiti"],["TF","French Southern Territories","Indian/Kerguelen"],["GA","Gabon","Africa/Libreville"],["GM","Gambia","Africa/Banjul"],["GE","Georgia","Asia/Tbilisi"],["DE","Germany","Europe/Berlin"],["DE","Germany","Europe/Busingen"],["GH","Ghana","Africa/Accra"],["GI","Gibraltar","Europe/Gibraltar"],["GR","Greece","Europe/Athens"],["GL","Greenland","America/Danmarkshavn"],["GL","Greenland","America/Nuuk"],["GL","Greenland","America/Scoresbysund"],["GL","Greenland","America/Thule"],["GD","Grenada","America/Grenada"],["GP","Guadeloupe","America/Guadeloupe"],["GU","Guam","Pacific/Guam"],["GT","Guatemala","America/Guatemala"],["GG","Guernsey","Europe/Guernsey"],["GN","Guinea","Africa/Conakry"],["GW","Guinea-Bissau","Africa/Bissau"],["GY","Guyana","America/Guyana"],["HT","Haiti","America/Port-au-Prince"],["VA","Holy See (Vatican City State)","Europe/Vatican"],["HN","Honduras","America/Tegucigalpa"],["HK","Hong Kong","Asia/Hong_Kong"],["HU","Hungary","Europe/Budapest"],["IS","Iceland","Atlantic/Reykjavik"],["IN","India","Asia/Kolkata"],["ID","Indonesia","Asia/Jakarta"],["ID","Indonesia","Asia/Jayapura"],["ID","Indonesia","Asia/Makassar"],["ID","Indonesia","Asia/Pontianak"],["IR","Iran, Islamic Republic of","Asia/Tehran"],["IQ","Iraq","Asia/Baghdad"],["IE","Ireland","Europe/Dublin"],["IM","Isle of Man","Europe/Isle_of_Man"],["IL","Israel","Asia/Jerusalem"],["IT","Italy","Europe/Rome"],["JM","Jamaica","America/Jamaica"],["JP","Japan","Asia/Tokyo"],["JE","Jersey","Europe/Jersey"],["JO","Jordan","Asia/Amman"],["KZ","Kazakhstan","Asia/Almaty"],["KZ","Kazakhstan","Asia/Aqtau"],["KZ","Kazakhstan","Asia/Aqtobe"],["KZ","Kazakhstan","Asia/Atyrau"],["KZ","Kazakhstan","Asia/Oral"],["KZ","Kazakhstan","Asia/Qostanay"],["KZ","Kazakhstan","Asia/Qyzylorda"],["KE","Kenya","Africa/Nairobi"],["KI","Kiribati","Pacific/Kanton"],["KI","Kiribati","Pacific/Kiritimati"],["KI","Kiribati","Pacific/Tarawa"],["KP","Korea, Democratic People's Republic of","Asia/Pyongyang"],["KR","Korea, Republic of","Asia/Seoul"],["KW","Kuwait","Asia/Kuwait"],["KG","Kyrgyzstan","Asia/Bishkek"],["LA","Lao People's Democratic Republic","Asia/Vientiane"],["LV","Latvia","Europe/Riga"],["LB","Lebanon","Asia/Beirut"],["LS","Lesotho","Africa/Maseru"],["LR","Liberia","Africa/Monrovia"],["LY","Libya","Africa/Tripoli"],["LI","Liechtenstein","Europe/Vaduz"],["LT","Lithuania","Europe/Vilnius"],["LU","Luxembourg","Europe/Luxembourg"],["MO","Macao","Asia/Macau"],["MG","Madagascar","Indian/Antananarivo"],["MW","Malawi","Africa/Blantyre"],["MY","Malaysia","Asia/Kuala_Lumpur"],["MY","Malaysia","Asia/Kuching"],["MV","Maldives","Indian/Maldives"],["ML","Mali","Africa/Bamako"],["MT","Malta","Europe/Malta"],["MH","Marshall Islands","Pacific/Kwajalein"],["MH","Marshall Islands","Pacific/Majuro"],["MQ","Martinique","America/Martinique"],["MR","Mauritania","Africa/Nouakchott"],["MU","Mauritius","Indian/Mauritius"],["YT","Mayotte","Indian/Mayotte"],["MX","Mexico","America/Bahia_Banderas"],["MX","Mexico","America/Cancun"],["MX","Mexico","America/Chihuahua"],["MX","Mexico","America/Ciudad_Juarez"],["MX","Mexico","America/Hermosillo"],["MX","Mexico","America/Matamoros"],["MX","Mexico","America/Mazatlan"],["MX","Mexico","America/Merida"],["MX","Mexico","America/Mexico_City"],["MX","Mexico","America/Monterrey"],["MX","Mexico","America/Ojinaga"],["MX","Mexico","America/Tijuana"],["FM","Micronesia, Federated States of","Pacific/Chuuk"],["FM","Micronesia, Federated States of","Pacific/Kosrae"],["FM","Micronesia, Federated States of","Pacific/Pohnpei"],["MD","Moldova, Republic of","Europe/Chisinau"],["MC","Monaco","Europe/Monaco"],["MN","Mongolia","Asia/Hovd"],["MN","Mongolia","Asia/Ulaanbaatar"],["ME","Montenegro","Europe/Podgorica"],["MS","Montserrat","America/Montserrat"],["MA","Morocco","Africa/Casablanca"],["MZ","Mozambique","Africa/Maputo"],["MM","Myanmar","Asia/Yangon"],["NA","Namibia","Africa/Windhoek"],["NR","Nauru","Pacific/Nauru"],["NP","Nepal","Asia/Kathmandu"],["NL","Netherlands","Europe/Amsterdam"],["NC","New Caledonia","Pacific/Noumea"],["NZ","New Zealand","Pacific/Auckland"],["NZ","New Zealand","Pacific/Chatham"],["NI","Nicaragua","America/Managua"],["NE","Niger","Africa/Niamey"],["NG","Nigeria","Africa/Lagos"],["NU","Niue","Pacific/Niue"],["NF","Norfolk Island","Pacific/Norfolk"],["MK","North Macedonia","Europe/Skopje"],["MP","Northern Mariana Islands","Pacific/Saipan"],["NO","Norway","Europe/Oslo"],["OM","Oman","Asia/Muscat"],["PK","Pakistan","Asia/Karachi"],["PW","Palau","Pacific/Palau"],["PS","Palestine, State of","Asia/Gaza"],["PS","Palestine, State of","Asia/Hebron"],["PA","Panama","America/Panama"],["PG","Papua New Guinea","Pacific/Bougainville"],["PG","Papua New Guinea","Pacific/Port_Moresby"],["PY","Paraguay","America/Asuncion"],["PE","Peru","America/Lima"],["PH","Philippines","Asia/Manila"],["PN","Pitcairn","Pacific/Pitcairn"],["PL","Poland","Europe/Warsaw"],["PT","Portugal","Atlantic/Azores"],["PT","Portugal","Atlantic/Madeira"],["PT","Portugal","Europe/Lisbon"],["PR","Puerto Rico","America/Puerto_Rico"],["QA","Qatar","Asia/Qatar"],["RO","Romania","Europe/Bucharest"],["RU","Russian Federation","Asia/Anadyr"],["RU","Russian Federation","Asia/Barnaul"],["RU","Russian Federation","Asia/Chita"],["RU","Russian Federation","Asia/Irkutsk"],["RU","Russian Federation","Asia/Kamchatka"],["RU","Russian Federation","Asia/Khandyga"],["RU","Russian Federation","Asia/Krasnoyarsk"],["RU","Russian Federation","Asia/Magadan"],["RU","Russian Federation","Asia/Novokuznetsk"],["RU","Russian Federation","Asia/Novosibirsk"],["RU","Russian Federation","Asia/Omsk"],["RU","Russian Federation","Asia/Sakhalin"],["RU","Russian Federation","Asia/Srednekolymsk"],["RU","Russian Federation","Asia/Tomsk"],["RU","Russian Federation","Asia/Ust-Nera"],["RU","Russian Federation","Asia/Vladivostok"],["RU","Russian Federation","Asia/Yakutsk"],["RU","Russian Federation","Asia/Yekaterinburg"],["RU","Russian Federation","Europe/Astrakhan"],["RU","Russian Federation","Europe/Kaliningrad"],["RU","Russian Federation","Europe/Kirov"],["RU","Russian Federation","Europe/Moscow"],["RU","Russian Federation","Europe/Samara"],["RU","Russian Federation","Europe/Saratov"],["RU","Russian Federation","Europe/Ulyanovsk"],["RU","Russian Federation","Europe/Volgograd"],["RW","Rwanda","Africa/Kigali"],["RE","Réunion","Indian/Reunion"],["BL","Saint Barthélemy","America/St_Barthelemy"],["SH","Saint Helena, Ascension and Tristan da Cunha","Atlantic/St_Helena"],["KN","Saint Kitts and Nevis","America/St_Kitts"],["LC","Saint Lucia","America/St_Lucia"],["MF","Saint Martin (French part)","America/Marigot"],["PM","Saint Pierre and Miquelon","America/Miquelon"],["VC","Saint Vincent and the Grenadines","America/St_Vincent"],["WS","Samoa","Pacific/Apia"],["SM","San Marino","Europe/San_Marino"],["ST","Sao Tome and Principe","Africa/Sao_Tome"],["SA","Saudi Arabia","Asia/Riyadh"],["SN","Senegal","Africa/Dakar"],["RS","Serbia","Europe/Belgrade"],["SC","Seychelles","Indian/Mahe"],["SL","Sierra Leone","Africa/Freetown"],["SG","Singapore","Asia/Singapore"],["SX","Sint Maarten (Dutch part)","America/Lower_Princes"],["SK","Slovakia","Europe/Bratislava"],["SI","Slovenia","Europe/Ljubljana"],["SB","Solomon Islands","Pacific/Guadalcanal"],["SO","Somalia","Africa/Mogadishu"],["ZA","South Africa","Africa/Johannesburg"],["GS","South Georgia and the South Sandwich Islands","Atlantic/South_Georgia"],["SS","South Sudan","Africa/Juba"],["ES","Spain","Africa/Ceuta"],["ES","Spain","Atlantic/Canary"],["ES","Spain","Europe/Madrid"],["LK","Sri Lanka","Asia/Colombo"],["SD","Sudan","Africa/Khartoum"],["SR","Suriname","America/Paramaribo"],["SJ","Svalbard and Jan Mayen","Arctic/Longyearbyen"],["SE","Sweden","Europe/Stockholm"],["CH","Switzerland","Europe/Zurich"],["SY","Syrian Arab Republic","Asia/Damascus"],["TW","Taiwan, Province of China","Asia/Taipei"],["TJ","Tajikistan","Asia/Dushanbe"],["TZ","Tanzania, United Republic of","Africa/Dar_es_Salaam"],["TH","Thailand","Asia/Bangkok"],["TL","Timor-Leste","Asia/Dili"],["TG","Togo","Africa/Lome"],["TK","Tokelau","Pacific/Fakaofo"],["TO","Tonga","Pacific/Tongatapu"],["TT","Trinidad and Tobago","America/Port_of_Spain"],["TN","Tunisia","Africa/Tunis"],["TM","Turkmenistan","Asia/Ashgabat"],["TC","Turks and Caicos Islands","America/Grand_Turk"],["TV","Tuvalu","Pacific/Funafuti"],["TR","Türkiye","Europe/Istanbul"],["UG","Uganda","Africa/Kampala"],["UA","Ukraine","Europe/Kyiv"],["UA","Ukraine","Europe/Simferopol"],["AE","United Arab Emirates","Asia/Dubai"],["GB","United Kingdom","Europe/London"],["US","United States","America/Adak"],["US","United States","America/Anchorage"],["US","United States","America/Boise"],["US","United States","America/Chicago"],["US","United States","America/Denver"],["US","United States","America/Detroit"],["US","United States","America/Indiana/Indianapolis"],["US","United States","America/Indiana/Knox"],["US","United States","America/Indiana/Marengo"],["US","United States","America/Indiana/Petersburg"],["US","United States","America/Indiana/Tell_City"],["US","United States","America/Indiana/Vevay"],["US","United States","America/Indiana/Vincennes"],["US","United States","America/Indiana/Winamac"],["US","United States","America/Juneau"],["US","United States","America/Kentucky/Louisville"],["US","United States","America/Kentucky/Monticello"],["US","United States","America/Los_Angeles"],["US","United States","America/Menominee"],["US","United States","America/Metlakatla"],["US","United States","America/New_York"],["US","United States","America/Nome"],["US","United States","America/North_Dakota/Beulah"],["US","United States","America/North_Dakota/Center"],["US","United States","America/North_Dakota/New_Salem"],["US","United States","America/Phoenix"],["US","United States","America/Sitka"],["US","United States","America/Yakutat"],["US","United States","Pacific/Honolulu"],["UM","United States Minor Outlying Islands","Pacific/Midway"],["UM","United States Minor Outlying Islands","Pacific/Wake"],["UY","Uruguay","America/Montevideo"],["UZ","Uzbekistan","Asia/Samarkand"],["UZ","Uzbekistan","Asia/Tashkent"],["VU","Vanuatu","Pacific/Efate"],["VE","Venezuela, Bolivarian Republic of","America/Caracas"],["VN","Viet Nam","Asia/Ho_Chi_Minh"],["VG","Virgin Islands, British","America/Tortola"],["VI","Virgin Islands, U.S.","America/St_Thomas"],["WF","Wallis and Futuna","Pacific/Wallis"],["EH","Western Sahara","Africa/El_Aaiun"],["YE","Yemen","Asia/Aden"],["ZM","Zambia","Africa/Lusaka"],["ZW","Zimbabwe","Africa/Harare"],["AX","Åland Islands","Europe/Mariehamn"]];


// V12.0.2 practical utilities; all calculations remain inside this browser.
TOOLS.push(
 {id:'json-pretty',name:'JSON Formatter',icon:'🧩',category:'Text & Study',summary:'Validate and format JSON with helpful errors'},
 {id:'base64-text',name:'Base64 Text',icon:'🔡',category:'Text & Study',summary:'Encode or decode UTF-8 text in Base64'},
 {id:'text-diff',name:'Text Difference',icon:'🔍',category:'Text & Study',summary:'Compare two passages line by line'},
 {id:'attendance',name:'Attendance Planner',icon:'🎓',category:'Text & Study',summary:'Estimate future classes needed for target attendance'},
 {id:'weighted-grade',name:'Weighted Grades',icon:'📊',category:'Text & Study',summary:'Compute a score from weighted assessments'},
 {id:'csv-inspect',name:'CSV Inspector',icon:'📋',category:'Text & Study',summary:'Count rows and columns in CSV text'}
);
export function jsonPretty(value,mode='format'){
 const obj=JSON.parse(String(value));
 return mode==='compact'?JSON.stringify(obj):JSON.stringify(obj,null,2);
}
export function base64Text(value,mode='encode'){
 const text=String(value??'');
 if(mode==='encode'){
  const bytes=new TextEncoder().encode(text);
  let out='';for(let i=0;i<bytes.length;i++)out+=String.fromCharCode(bytes[i]);
  return btoa(out);
 }
 if(mode!=='decode')throw Error('Invalid action.');
 const clean=text.replace(/\s+/g,'');
 const raw=atob(clean);
 const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
 return new TextDecoder('utf-8',{fatal:true}).decode(bytes);
}
export function textDiff(a,b){
 const x=String(a??'').replace(/\r\n/g,'\n').split('\n');
 const y=String(b??'').replace(/\r\n/g,'\n').split('\n');
 if(x.length>500||y.length>500)throw Error('Maximum 500 lines per input.');
 const out=[];const n=Math.max(x.length,y.length);
 for(let i=0;i<n;i++)if(x[i]!==y[i])out.push(`Line ${i+1}\n− ${x[i]??'(missing)'}\n+ ${y[i]??'(missing)'}`);
 return out.length?out.join('\n\n'):'No line differences.';
}
export function attendancePlan(attended,total,target){
 const a=Number(attended), t=Number(total), p=Number(target);
 if(!Number.isInteger(a)||!Number.isInteger(t)||a<0||t<1||a>t||!Number.isFinite(p)||p<=0||p>100)throw Error('Enter valid attended, total, and target (0–100%).');
 const current=a/t*100;
 const n=p===100?(a===t?0:Infinity):Math.max(0,Math.ceil(((p/100)*t-a)/(1-p/100)-1e-10));
 return {current,needed:n};
}
export function weightedGrades(value){
 const rows=String(value||'').trim().split(/\n+/).filter(Boolean);
 if(!rows.length||rows.length>100)throw Error('Enter 1–100 assessment rows.');
 let weighted=0,totalWeight=0;
 for(const row of rows){
  const parts=row.split(',').map(s=>s.trim());
  if(parts.length!==2)throw Error('Use score,weight on each line.');
  const [score,w]=parts.map(Number);
  if(!Number.isFinite(score)||!Number.isFinite(w)||score<0||score>100||w<=0||w>100)throw Error('Scores must be 0–100 and weights 0–100.');
  weighted+=score*w;totalWeight+=w;
 }
 if(totalWeight>100+1e-9)throw Error('Weights exceed 100%.');
 return {average:weighted/totalWeight,weight:totalWeight,contribution:weighted/100};
}
export function csvInspect(value){
 const s=String(value??'');if(s.length>200000)throw Error('CSV input too large.');
 if(!s.trim())throw Error('Paste CSV text.');
 let q=false,cell='',row=[],rows=[];
 for(let i=0;i<s.length;i++){const c=s[i];
  if(c==='"'){if(q&&s[i+1]==='"'){cell+='"';i++;}else q=!q;}
  else if(c===','&&!q){row.push(cell);cell='';}
  else if((c==='\n'||c==='\r')&&!q){if(c==='\r'&&s[i+1]==='\n')i++;row.push(cell);rows.push(row);row=[];cell='';}
  else cell+=c;
 }
 if(q)throw Error('Unclosed quoted CSV field.');
 if(cell||row.length||s.endsWith(',')){row.push(cell);rows.push(row);}
 const cols=rows[0]?.length||0;
 return {rows:rows.length,columns:cols,consistent:rows.every(r=>r.length===cols),preview:rows[0]?.slice(0,8)||[]};
}
Object.assign(TOOL_NAME_TRANSLATIONS.ta,{
 'json-pretty':'JSON வடிவமைப்பான்','base64-text':'Base64 உரை','text-diff':'உரை ஒப்பீடு','attendance':'வருகை திட்டம்','weighted-grade':'எடையிடப்பட்ட மதிப்பெண்','csv-inspect':'CSV ஆய்வு'
});
Object.assign(TOOL_NAME_TRANSLATIONS.si,{
 'json-pretty':'JSON හැඩතල','base64-text':'Base64 පෙළ','text-diff':'පෙළ වෙනස්කම්','attendance':'පැමිණීමේ සැලැස්ම','weighted-grade':'බර ලකුණු','csv-inspect':'CSV පරීක්ෂාව'
});

Object.assign(FIELD_LABEL_TRANSLATIONS.ta,{
 'JSON text':'JSON உரை','UTF-8 text or Base64':'UTF-8 உரை அல்லது Base64','Original text':'மூல உரை','Updated text':'புதிய உரை',
 'Classes attended':'வருகை தந்த வகுப்புகள்','Classes held':'நடைபெற்ற வகுப்புகள்','Target attendance %':'இலக்கு வருகை %',
 'Score,weight (one per line)':'மதிப்பெண், பங்கு (ஒரு வரிக்கு ஒன்று)','CSV text':'CSV உரை'
});
Object.assign(FIELD_LABEL_TRANSLATIONS.si,{
 'JSON text':'JSON පෙළ','UTF-8 text or Base64':'UTF-8 පෙළ හෝ Base64','Original text':'මුල් පෙළ','Updated text':'නව පෙළ',
 'Classes attended':'සහභාගී වූ පන්ති','Classes held':'පැවැත්වූ පන්ති','Target attendance %':'ඉලක්ක පැමිණීම %',
 'Score,weight (one per line)':'ලකුණු, බර (පේළියකට එකක්)','CSV text':'CSV පෙළ'
});

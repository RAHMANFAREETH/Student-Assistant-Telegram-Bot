// V12 multilingual computed result messages. Never translate user-provided text.
const RESULT_FRAGMENTS = {
  ta: {
    'Final price:':'இறுதி விலை:', 'You save:':'நீங்கள் சேமிப்பது:',
    'Adult screening only, not a diagnosis.':'இது பெரியவர்களுக்கான ஆரம்ப மதிப்பீடு மட்டுமே; நோயறிதல் அல்ல.',
    'Underweight':'குறைந்த உடல் எடை', 'Typical adult range':'பொதுவான வயது வந்தோர் வரம்பு',
    'Overweight':'அதிக உடல் எடை', 'Obesity range':'உடல் பருமன் வரம்பு',
    'Weighted GPA:':'எடையிட்ட GPA:', 'Credits:':'பாட அலகுகள்:',
    'Enter numerical grade points on a 0–4 scale; this is not a university-specific GPA policy.':'0–4 அளவில் மதிப்பெண் புள்ளிகளை உள்ளிடவும்; இது குறிப்பிட்ட பல்கலைக்கழகத்தின் GPA விதிமுறை அல்ல.',
    'Estimate, before fees or taxes.':'கட்டணம் அல்லது வரிகளுக்கு முன்பான மதிப்பீடு.',
    'Fixed rate, no fees or taxes.':'நிலையான வட்டி; கட்டணங்களும் வரிகளும் சேர்க்கப்படவில்லை.',
    'Applies to solid colors without alpha.':'ஒளிபுகா நிறங்களுக்கு மட்டும் பொருந்தும்.',
    'Normal-size AA text:':'சாதாரண அளவு AA உரை:', 'Large-size AA text:':'பெரிய அளவு AA உரை:',
    'WCAG contrast:':'WCAG நிற மாறுபாடு:', 'Total payments:':'மொத்தத் தவணைத் தொகை:', 'Total interest:':'மொத்த வட்டி:',
    'Each person:':'ஒவ்வொருவருக்கும்:', 'Monthly:':'மாதந்தோறும்:', 'Interest:':'வட்டி:', 'Total:':'மொத்தம்:',
    'Mean:':'சராசரி:', 'Median:':'இடைநிலை:', 'Count:':'எண்ணிக்கை:', 'Min:':'குறைந்தபட்சம்:', 'Max:':'அதிகபட்சம்:',
    'Tip:':'சேவைக்கட்டணம்:', 'Prime number':'பகா எண்', 'Not prime':'பகா எண் அல்ல',
    'Pass':'தேர்ச்சி', 'Fail':'தோல்வி', 'approximately':'ஏறத்தாழ',
    'weekend days':'வார இறுதி நாட்கள்', 'weekdays':'வார நாட்கள்', 'weeks and':'வாரங்கள் மற்றும்',
    'overnight':'இரவு தாண்டி', 'characters':'எழுத்துகள்', 'hours':'மணிநேரம்', 'minutes':'நிமிடங்கள்',
    'seconds':'விநாடிகள்', 'months':'மாதங்கள்', 'years':'ஆண்டுகள்', 'days':'நாட்கள்',
    'weeks':'வாரங்கள்', 'words':'சொற்கள்', 'lines':'வரிகள்', 'watts':'வாட்ஸ்', 'Day ':'நாள் ',
    ' of ':' / ', ' and ':' மற்றும் ', ' (':' (',
  },
  si: {
    'Final price:':'අවසාන මිල:', 'You save:':'ඔබ ඉතිරි කරන මුදල:',
    'Adult screening only, not a diagnosis.':'වැඩිහිටියන් සඳහා මූලික ඇගයීමක් පමණි; රෝග විනිශ්චයක් නොවේ.',
    'Underweight':'අඩු බර', 'Typical adult range':'සාමාන්‍ය වැඩිහිටි පරාසය',
    'Overweight':'වැඩි බර', 'Obesity range':'ස්ථූලතා පරාසය',
    'Weighted GPA:':'බරිත GPA:', 'Credits:':'ණය ඒකක:',
    'Enter numerical grade points on a 0–4 scale; this is not a university-specific GPA policy.':'0–4 පරිමාණයේ ලකුණු ඇතුළත් කරන්න; මෙය විශ්වවිද්‍යාලයක නිශ්චිත GPA ප්‍රතිපත්තියක් නොවේ.',
    'Estimate, before fees or taxes.':'ගාස්තු සහ බදු පෙර ඇස්තමේන්තුවකි.',
    'Fixed rate, no fees or taxes.':'ස්ථාවර පොලී අනුපාතය; ගාස්තු සහ බදු ඇතුළත් නොවේ.',
    'Applies to solid colors without alpha.':'පාරදෘශ්‍යතාව නැති වර්ණ සඳහා පමණි.',
    'Normal-size AA text:':'සාමාන්‍ය ප්‍රමාණයේ AA පෙළ:', 'Large-size AA text:':'විශාල AA පෙළ:',
    'WCAG contrast:':'WCAG වර්ණ වෙනස:', 'Total payments:':'මුළු ගෙවීම්:', 'Total interest:':'මුළු පොලිය:',
    'Each person:':'එක් අයෙකුට:', 'Monthly:':'මාසිකව:', 'Interest:':'පොලිය:', 'Total:':'එකතුව:',
    'Mean:':'සාමාන්‍යය:', 'Median:':'මධ්‍යස්ථය:', 'Count:':'ගණන:', 'Min:':'අවම:', 'Max:':'උපරිම:',
    'Tip:':'සේවා ගාස්තුව:', 'Prime number':'ප්‍රථමක සංඛ්‍යාව', 'Not prime':'ප්‍රථමක නොවේ',
    'Pass':'සමත්', 'Fail':'අසමත්', 'approximately':'ආසන්න වශයෙන්',
    'weekend days':'සති අන්ත දින', 'weekdays':'සතියේ දින', 'weeks and':'සති සහ',
    'overnight':'රාත්‍රිය ඉක්මවා', 'characters':'අකුරු', 'hours':'පැය', 'minutes':'මිනිත්තු',
    'seconds':'තත්පර', 'months':'මාස', 'years':'වසර', 'days':'දින',
    'weeks':'සති', 'words':'වචන', 'lines':'පේළි', 'watts':'වොට්', 'Day ':'දිනය ',
    ' of ':' / ', ' and ':' සහ ',
  }
};
const RAW_TEXT_TOOLS = new Set(['text-case','text-sort','text-unique','text-reverse','url-encode', 'base','epoch','date-add','month-shift','weekday']);
export function translateResult(id, value, lang='en') {
  const text = String(value);
  if (!RESULT_FRAGMENTS[lang] || RAW_TEXT_TOOLS.has(id)) return text;
  const source = RESULT_FRAGMENTS[lang];
  // Replace static words only, from longest to shortest. Escape regex safely.
  const pairs = Object.entries(source).sort((a,b)=>b[0].length-a[0].length);
  const escaped = s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const regex = new RegExp(pairs.map(([key])=>escaped(key)).join('|'),'g');
  return text.replace(regex, match=>source[match]);
}
export function translateError(error, lang='en') {
  const source = String(error?.message||error||'');
  if (lang==='en') return source;
  if (lang==='ta') return 'உள்ளீடு செல்லுபடியாகவில்லை. மதிப்புகளைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.';
  if (lang==='si') return 'ඇතුළත් කළ අගයන් වලංගු නැත. කරුණාකර පරීක්ෂා කර නැවත උත්සාහ කරන්න.';
  return source;
}

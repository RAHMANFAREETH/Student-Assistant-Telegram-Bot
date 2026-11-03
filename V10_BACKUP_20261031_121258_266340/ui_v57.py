# V5.8 achievements category
"""Student Assistant Bot V5.8: beginner-friendly, multilingual category navigation.

Existing feature button texts are intentionally left unchanged, so existing
V5.4–V5.6 Telegram handlers keep working. The displayed explanations can be
translated independently of the underlying feature handler names.
"""
from collections import OrderedDict
from threading import RLock
from time import monotonic

from telebot import types

# New category names (do not reuse a legacy feature button string).
CAT_AI = "🤖 AI & Questions"
CAT_STUDY = "📚 Study Tools"
CAT_PLANNER = "📅 Plans & Reminders"
CAT_PRACTICE = "🧠 Practice & Quiz"
CAT_LANGUAGE = "🌍 Languages"
CAT_PROGRESS = "📊 My Progress"
CAT_FILES = "🎙 Voice & PDF"
CAT_MORE = "📦 More Tools"

HELP_CENTER = "❓ Help & Tutorial"
LANGUAGE_MENU = "🌐 Menu Language"
BACK_CATEGORIES = "↩️ All Categories"

CATEGORY_FEATURES = OrderedDict([
    (CAT_AI, ["🤖 Ask AI", "📝 Ask My Notes", "📄 Ask My PDF"]),
    # V6.6 revision hub menu options
    (CAT_STUDY, ["📚 Subjects", "📝 Notes", "📚 Study Materials", "🔎 Global Search",
                 "📖 Revision Hub", "📚 My AI Study Library", "🔄 Revise AI Note"]),
    (CAT_PLANNER, ["📅 Assignments", "🗓 Timetable", "📝 Exams", "⏱ Study Planner",
                   "⏰ Study Reminder", "🎯 Study Goals", "🔔 Smart Notifications"]),
    (CAT_PRACTICE, ["🧠 Flashcards", "🧠 Due Reviews", "📊 Review Stats", "❓ Quiz",
                    "📚 Revision Planner", "🧠 Practice Saved Cards", "📊 Revision Progress",
                    "⏰ Revision Reminders"]),
    (CAT_LANGUAGE, ["🌐 Translate", "🌍 Language Tools"]),
    (CAT_PROGRESS, ["☀️ Today Hub", "📊 Dashboard", "📈 Progress", "✅ Attendance",
                    "📊 Grades & GPA", "🎓 Semesters", "🔥 Study Streak", "🏆 Achievements", "⭐ My Level", "🧠 Smart Insights"]),
    (CAT_FILES, ["📄 PDF Tools", "🎙 Voice Notes"]),
    (CAT_MORE, ["📢 Student Resources", "📦 Export My Data", "ℹ️ Help"]),
])

LANG_BUTTONS = OrderedDict([
    ("🇬🇧 English", "en"),
    ("🇱🇰 தமிழ்", "ta"),
    ("🇱🇰 සිංහල", "si"),
    ("🇸🇦 العربية", "ar"),
])

GUIDE_BUTTONS = OrderedDict([
    ("🚀 Getting Started", "start"),
    ("🤖 Ask AI Guide", "ai"),
    ("📄 Ask My PDF Guide", "pdf"),
    ("🧠 Flashcards Guide", "cards"),
    ("📅 Study Planning Guide", "plan"),
    ("🎙 Voice Notes Guide", "voice"),
    ("🔒 Privacy Tips", "privacy"),
])

# V8.0 option only appears if an administrator enables the pilot.
import os as _v8_os
if _v8_os.getenv("V8_ENABLED", "").lower() in ("true", "1", "yes"):
    CATEGORY_FEATURES[CAT_MORE].insert(0, "🚀 V8 Study Lab")

# V9.0 Academic Toolkit — independent pilot; uses the V8-approved allowlist.
import os as _v9_os
if _v9_os.getenv("V9_ENABLED", "").lower() in ("true", "1", "yes"):
    CATEGORY_FEATURES[CAT_MORE].insert(0, "🧰 V9 Academic Toolkit")

# V9.1: verification requests are available even before V8/V9 authorization.
import os as _v91_os
if _v91_os.getenv("V91_ACCESS_REQUESTS_ENABLED", "").lower() in ("true", "1", "yes"):
    CATEGORY_FEATURES[CAT_MORE].insert(0, "🔐 Verify Adult Access")

ALL_UI_BUTTONS = (set(CATEGORY_FEATURES) | set(LANG_BUTTONS) |
                  set(GUIDE_BUTTONS) | {HELP_CENTER, LANGUAGE_MENU, BACK_CATEGORIES, "🔎 Find a Tool"})

TEXT = {
    "en": {
        "welcome": "👋 Hello, {name}!\n🎓 Student Assistant V7.9\n\nChoose a category below. New here? Tap ❓ Help & Tutorial.\nUse /language to change the guide language.",
        "category": "Select a tool. The buttons below open your existing features.",
        "help": "❓ Quick Help\nChoose a short step-by-step guide:",
        "language": "🌐 Choose a language for menu guidance. Feature button names stay unchanged for compatibility.",
        "saved": "✅ Your guidance language is now English.",
        "private": "🔒 Change your menu language in a private chat with this bot.",
        "back": "Choose a category from the main menu.",
    },
    "ta": {
        "welcome": "👋 வணக்கம், {name}!\n🎓 மாணவர் உதவி Bot V7.9\n\nகீழே உங்களுக்கு தேவையான பகுதியைத் தேர்ந்தெடுக்கவும். புதிதாக பயன்படுத்துகிறீர்களா? ❓ Help & Tutorial அழுத்தவும்.\nவழிகாட்டும் மொழியை மாற்ற /language அனுப்பவும்.",
        "category": "உங்களுக்கு வேண்டிய வசதியைத் தேர்ந்தெடுக்கவும். கீழே உள்ள buttons பழைய வசதிகளையே திறக்கும்.",
        "help": "❓ உதவி மையம்\nஎப்படி பயன்படுத்துவது என்பதை அறியுங்கள்:",
        "language": "🌐 வழிகாட்டும் மொழியைத் தேர்ந்தெடுக்கவும். பழைய features வேலை செய்வதற்காக button பெயர்கள் English-இலேயே இருக்கும்.",
        "saved": "✅ வழிகாட்டும் மொழி தமிழ் ஆக மாற்றப்பட்டது.",
        "private": "🔒 மொழியை மாற்ற Bot-க்கு தனிப்பட்ட chat-இல் செல்லவும்.",
        "back": "முதன்மை மெனுவில் ஒரு பகுதியைத் தேர்ந்தெடுக்கவும்.",
    },
    "si": {
        "welcome": "👋 ආයුබෝවන්, {name}!\n🎓 ශිෂ්‍ය සහායක Bot V7.9\n\nපහළින් ඔබට අවශ්‍ය කාණ්ඩය තෝරන්න. නව පරිශීලකයෙක් නම් ❓ Help & Tutorial තෝරන්න.\nභාෂාව වෙනස් කිරීමට /language යවන්න.",
        "category": "ඔබට අවශ්‍ය මෙවලම තෝරන්න. බොත්තම් දැනටමත් ඇති විශේෂාංග විවෘත කරයි.",
        "help": "❓ උපකාරක මධ්‍යස්ථානය\nපියවරෙන් පියවර උපදෙස් තෝරන්න:",
        "language": "🌐 උපදෙස් භාෂාව තෝරන්න. පැරණි විශේෂාංග ක්‍රියා කිරීම සඳහා බොත්තම් නම් ඉංග්‍රීසියෙන් පවතී.",
        "saved": "✅ උපදෙස් භාෂාව සිංහල ලෙස සැකසුණා.",
        "private": "🔒 භාෂාව වෙනස් කිරීමට Bot සමඟ පුද්ගලික සංවාදයට යන්න.",
        "back": "ප්‍රධාන මෙනුවෙන් කාණ්ඩයක් තෝරන්න.",
    },
    "ar": {
        "welcome": "👋 مرحبًا {name}!\n🎓 مساعد الطالب V7.9\n\nاختر قسمًا من الأزرار أدناه. إن كنت جديدًا فاضغط ❓ Help & Tutorial.\nلتغيير لغة الشرح أرسل /language.",
        "category": "اختر الأداة المطلوبة. تفتح هذه الأزرار الميزات الحالية دون تغيير.",
        "help": "❓ مركز المساعدة\nاختر شرحًا خطوة بخطوة:",
        "language": "🌐 اختر لغة الإرشادات. ستظل أسماء الأزرار بالإنجليزية لضمان عمل الميزات القديمة.",
        "saved": "✅ تم تغيير لغة الإرشادات إلى العربية.",
        "private": "🔒 غيّر اللغة من محادثتك الخاصة مع البوت.",
        "back": "اختر قسمًا من القائمة الرئيسية.",
    },
}

# Keep the multilingual greeting accurate only when V8 is enabled.
if _v8_os.getenv("V8_ENABLED", "").lower() in ("true", "1", "yes"):
    for _lang_text in TEXT.values():
        if "welcome" in _lang_text:
            _lang_text["welcome"] = _lang_text["welcome"].replace("V7.9", "V8.0 Pilot")

CATEGORY_TEXT = {
    "en": {
        CAT_AI: "Ask a question, or learn from your saved notes and PDFs.",
        CAT_STUDY: "Save lessons, find notes and browse subjects.",
        CAT_PLANNER: "Manage exams, deadlines, goals and reminders.",
        CAT_PRACTICE: "Revise with flashcards, due reviews and quizzes.",
        CAT_LANGUAGE: "Translate text and practice languages.",
        CAT_PROGRESS: "Track grades, streaks, attendance and performance.",
        CAT_FILES: "Work with PDF files and recorded voice notes.",
        CAT_MORE: "Find student resources and export your data.",
    },
    "ta": {
        CAT_AI: "பாட சந்தேகங்களைக் கேளுங்கள்; உங்கள் Notes மற்றும் PDF-இல் இருந்து படியுங்கள்.",
        CAT_STUDY: "பாடங்கள், குறிப்புகள், பாடப்பொருட்களைச் சேமித்து தேடுங்கள்.",
        CAT_PLANNER: "தேர்வுகள், assignments, நேர அட்டவணை, reminders நிர்வகிக்கவும்.",
        CAT_PRACTICE: "Flashcards, மறுபயிற்சி, Quiz மூலம் பயிற்சி செய்யுங்கள்.",
        CAT_LANGUAGE: "உரை மொழிபெயர்ப்பு மற்றும் மொழிப் பயிற்சி.",
        CAT_PROGRESS: "மதிப்பெண்கள், வருகை, முன்னேற்றத்தைப் பாருங்கள்.",
        CAT_FILES: "PDF files மற்றும் Voice Notes-ஐப் பயன்படுத்துங்கள்.",
        CAT_MORE: "மாணவர் வளங்கள், தரவு backup போன்றவை.",
    },
    "si": {
        CAT_AI: "ප්‍රශ්න අසන්න; සුරැකි සටහන් සහ PDF වෙතින් ඉගෙන ගන්න.",
        CAT_STUDY: "විෂයයන්, සටහන් සහ අධ්‍යයන ද්‍රව්‍ය සංවිධානය කරන්න.",
        CAT_PLANNER: "විභාග, පැවරුම්, කාලසටහන් සහ සිහිගැන්වීම් සකසන්න.",
        CAT_PRACTICE: "ෆ්ලෑෂ්කාඩ් සහ ප්‍රශ්නාවලි මඟින් පුහුණු වන්න.",
        CAT_LANGUAGE: "පරිවර්තනය සහ භාෂා අධ්‍යයනය.",
        CAT_PROGRESS: "ලකුණු, පැමිණීම සහ ප්‍රගතිය බලන්න.",
        CAT_FILES: "PDF ගොනු සහ හඬ සටහන් භාවිත කරන්න.",
        CAT_MORE: "ශිෂ්‍ය සම්පත් සහ දත්ත අපනයනය.",
    },
    "ar": {
        CAT_AI: "اسأل عن دروسك أو تعلّم من ملاحظاتك وملفات PDF.",
        CAT_STUDY: "نظّم المواد والملاحظات والمراجع الدراسية.",
        CAT_PLANNER: "نظّم الامتحانات والواجبات والجداول والتذكيرات.",
        CAT_PRACTICE: "تدرّب باستخدام البطاقات والأسئلة والمراجعة.",
        CAT_LANGUAGE: "الترجمة وتعلّم اللغات.",
        CAT_PROGRESS: "تابع الدرجات والحضور والتقدم.",
        CAT_FILES: "استخدم ملفات PDF والملاحظات الصوتية.",
        CAT_MORE: "موارد الطلاب وتصدير البيانات.",
    },
}

GUIDES = {
    "start": {
        "en": "🚀 First steps:\n1. Tap 📚 Study Tools → 📚 Subjects to add a subject.\n2. Save a note using 📝 Notes.\n3. Ask a question through 🤖 AI & Questions.\n4. Return with 🏠 Main Menu or ↩️ All Categories.",
        "ta": "🚀 ஆரம்பிக்க:\n1. 📚 Study Tools → 📚 Subjects மூலம் பாடத்தைச் சேர்க்கவும்.\n2. 📝 Notes மூலம் குறிப்பைச் சேமிக்கவும்.\n3. 🤖 AI & Questions மூலம் சந்தேகம் கேளுங்கள்.\n4. திரும்ப 🏠 Main Menu அல்லது ↩️ All Categories அழுத்துங்கள்.",
        "si": "🚀 ආරම්භය:\n1. 📚 Study Tools → 📚 Subjects මඟින් විෂයක් එක් කරන්න.\n2. 📝 Notes මඟින් සටහනක් සුරකින්න.\n3. 🤖 AI & Questions මඟින් ප්‍රශ්න අසන්න.\n4. ආපසු යාමට 🏠 Main Menu භාවිත කරන්න.",
        "ar": "🚀 البداية:\n1. أضف مادة عبر 📚 Study Tools ثم 📚 Subjects.\n2. احفظ ملاحظة عبر 📝 Notes.\n3. اسأل عبر 🤖 AI & Questions.\n4. للعودة اضغط 🏠 Main Menu.",
    },
    "ai": {
        "en": "🤖 Ask AI:\n1. Open 🤖 AI & Questions → 🤖 Ask AI.\n2. Choose 💬 Ask Question or Explain Topic.\n3. Write your question in Tamil, Sinhala, English or Arabic.\n4. AI may make mistakes: verify important answers.",
        "ta": "🤖 AI பயன்படுத்த:\n1. 🤖 AI & Questions → 🤖 Ask AI அழுத்தவும்.\n2. Ask Question அல்லது Explain Topic தேர்ந்தெடுக்கவும்.\n3. தமிழ் அல்லது வேறு மொழியில் கேள்வி எழுதவும்.\n4. AI பதில்களை முக்கியமான சமயங்களில் சரிபார்க்கவும்.",
        "si": "🤖 AI භාවිතයට:\n1. 🤖 AI & Questions → 🤖 Ask AI.\n2. Ask Question හෝ Explain Topic තෝරන්න.\n3. ඔබේ ප්‍රශ්නය යවන්න.\n4. වැදගත් පිළිතුරු තහවුරු කරන්න.",
        "ar": "🤖 لاستخدام AI:\n1. اختر 🤖 AI & Questions ثم 🤖 Ask AI.\n2. اختر Ask Question أو Explain Topic.\n3. أرسل سؤالك بلغتك.\n4. تحقّق من الإجابات المهمة.",
    },
    "pdf": {
        "en": "📄 Ask My PDF:\n1. Open 📚 Study Tools → 📚 Study Materials and save a PDF.\n2. Its readable text must be extracted; scanned pages may need OCR.\n3. Open 🤖 AI & Questions → 📄 Ask My PDF.\n4. Select the saved PDF, confirm sharing selected excerpts and ask your question.",
        "ta": "📄 PDF-ஐ வைத்து கேள்வி கேட்க:\n1. 📚 Study Materials-இல் PDF சேமிக்கவும்.\n2. அதன் எழுத்துக்கள் extract ஆக வேண்டும்; scan செய்யப்பட்ட பக்கங்களுக்கு OCR தேவைப்படலாம்.\n3. 🤖 AI & Questions → 📄 Ask My PDF அழுத்தவும்.\n4. PDF தேர்ந்து அனுமதி அளித்து கேள்வி கேளுங்கள்.",
        "si": "📄 PDF ගැන අසන්න:\n1. 📚 Study Materials වෙත PDF එකක් සුරකින්න.\n2. PDF පෙළ ලබා ගත හැකි විය යුතුය.\n3. 🤖 AI & Questions → 📄 Ask My PDF.\n4. PDF තෝරා අවසර දී ප්‍රශ්නය අසන්න.",
        "ar": "📄 السؤال عن PDF:\n1. احفظ ملف PDF في 📚 Study Materials.\n2. يجب أن يكون النص مستخرجًا؛ قد تحتاج الصفحات الممسوحة إلى OCR.\n3. اختر 🤖 AI & Questions ثم 📄 Ask My PDF.\n4. اختر الملف ووافق على مشاركة المقتطفات ثم اسأل.",
    },
    "cards": {
        "en": "🧠 Flashcards:\n1. Open 🧠 Practice & Quiz → 🧠 Flashcards.\n2. Add a question and answer, then study the cards.\n3. Use 🧠 Due Reviews and rate Again / Hard / Good / Easy to schedule the next review.",
        "ta": "🧠 Flashcards:\n1. 🧠 Practice & Quiz → 🧠 Flashcards.\n2. கேள்வி, பதில் சேர்த்துப் படிக்கவும்.\n3. 🧠 Due Reviews-இல் Again / Hard / Good / Easy தேர்வு செய்யவும்.",
        "si": "🧠 ෆ්ලෑෂ්කාඩ්:\n1. 🧠 Practice & Quiz → 🧠 Flashcards.\n2. ප්‍රශ්නයක් හා පිළිතුරක් එක් කරන්න.\n3. 🧠 Due Reviews මඟින් නැවත පුහුණු වන්න.",
        "ar": "🧠 البطاقات:\n1. افتح 🧠 Practice & Quiz ثم 🧠 Flashcards.\n2. أضف سؤالًا وإجابة.\n3. استخدم 🧠 Due Reviews لتحديد موعد المراجعة التالية.",
    },
    "plan": {
        "en": "📅 Study planning:\n1. Open 📅 Plans & Reminders.\n2. Add 📅 Assignments with deadlines and 📝 Exams with dates.\n3. Check 🗓 Timetable and use ⏰ Study Reminder.\n4. Review today's tasks in ☀️ Today Hub.",
        "ta": "📅 திட்டமிட:\n1. 📅 Plans & Reminders திறக்கவும்.\n2. Assignments, Exams-க்கு தேதிகள் சேர்க்கவும்.\n3. Timetable, Reminder அமைக்கவும்.\n4. ☀️ Today Hub-இல் இன்று செய்ய வேண்டியதைப் பாருங்கள்.",
        "si": "📅 අධ්‍යයන සැලැස්ම:\n1. 📅 Plans & Reminders තෝරන්න.\n2. පැවරුම් හා විභාග දින එක් කරන්න.\n3. කාලසටහන හා සිහිගැන්වීම් සකසන්න.\n4. ☀️ Today Hub බලන්න.",
        "ar": "📅 تنظيم الدراسة:\n1. افتح 📅 Plans & Reminders.\n2. أضف الواجبات وتواريخ الامتحانات.\n3. استخدم الجدول والتذكيرات.\n4. راجع ☀️ Today Hub.",
    },
    "voice": {
        "en": "🎙 Voice Notes:\n1. Open 🎙 Voice & PDF → 🎙 Voice Notes.\n2. Record a short voice note and save it.\n3. Use Transcribe Voice to get text if AssemblyAI is configured.\n4. Check the saved transcript.",
        "ta": "🎙 Voice Notes:\n1. 🎙 Voice & PDF → 🎙 Voice Notes.\n2. குரலை பதிவு செய்து சேமிக்கவும்.\n3. AssemblyAI இருந்தால் Transcribe Voice பயன்படுத்தவும்.\n4. எழுத்து வடிவம் சரியா என்று பார்க்கவும்.",
        "si": "🎙 හඬ සටහන්:\n1. 🎙 Voice & PDF → 🎙 Voice Notes.\n2. හඬ පටිගත කර සුරකින්න.\n3. Transcribe Voice භාවිත කරන්න.\n4. ලියවුණු පෙළ පරීක්ෂා කරන්න.",
        "ar": "🎙 الملاحظات الصوتية:\n1. افتح 🎙 Voice & PDF ثم 🎙 Voice Notes.\n2. سجّل رسالة صوتية واحفظها.\n3. استخدم Transcribe Voice عند تفعيل AssemblyAI.\n4. راجع النص الناتج.",
    },
    "privacy": {
        "en": "🔒 Privacy tips:\n• Don't send passwords, API keys, IDs or confidential records to AI.\n• Ask My PDF/Notes sends selected source excerpts to the configured AI provider after consent.\n• The AI may be incorrect; verify important facts.",
        "ta": "🔒 தனியுரிமை:\n• Password, API key, ரகசியத் தகவல்களை AI-க்கு அனுப்ப வேண்டாம்.\n• Ask My PDF/Notes-இல் உங்கள் அனுமதிக்குப் பின் தேர்ந்தெடுக்கப்பட்ட உரை AI provider-க்கு அனுப்பப்படும்.\n• முக்கியமான பதில்களை சரிபார்க்கவும்.",
        "si": "🔒 පුද්ගලිකත්වය:\n• මුරපද, API keys හෝ රහස් තොරතුරු AI වෙත යවන්න එපා.\n• Ask My PDF/Notes තෝරාගත් කොටස් අවසරයෙන් පසු යවයි.\n• වැදගත් පිළිතුරු තහවුරු කරන්න.",
        "ar": "🔒 الخصوصية:\n• لا ترسل كلمات المرور أو مفاتيح API أو المعلومات السرية إلى AI.\n• يرسل Ask My PDF/Notes مقتطفات محددة بعد الموافقة.\n• تحقّق من الإجابات المهمة.",
    },
}

# Cache is bounded and private to the running process. Supabase stores permanent
# preference once SQL_V5_7_UI.sql is applied.
_PREFS = OrderedDict()
_PREFS_LOCK = RLock()
_CACHE_SECONDS = 600
_CACHE_LIMIT = 1000


def _cache_set(user_id, language):
    with _PREFS_LOCK:
        _PREFS[int(user_id)] = (language, monotonic())
        _PREFS.move_to_end(int(user_id))
        while len(_PREFS) > _CACHE_LIMIT:
            _PREFS.popitem(last=False)


def get_language(user_id):
    uid = int(user_id)
    with _PREFS_LOCK:
        entry = _PREFS.get(uid)
        if entry and monotonic() - entry[1] < _CACHE_SECONDS:
            return entry[0]
    try:
        from db import supabase
        response = (supabase.table("ui_language_v57").select("language")
                    .eq("user_id", uid).limit(1).execute())
        data = response.data or []
        code = data[0]["language"] if data else "en"
        if code not in TEXT:
            code = "en"
    except Exception:
        code = "en"  # Works even if SQL migration has not been applied.
    _cache_set(uid, code)
    return code


def set_language(user_id, language):
    if language not in TEXT:
        raise ValueError("Unsupported language")
    _cache_set(user_id, language)
    try:
        from db import supabase
        supabase.table("ui_language_v57").upsert(
            {"user_id": int(user_id), "language": language},
            on_conflict="user_id",
        ).execute()
        return True
    except Exception:
        return False  # Temporary until SQL migration exists.


def greeting(first_name, user_id):
    language = get_language(user_id)
    name = (str(first_name or "Friend").replace("\n", " ").replace("\r", " "))[:45]
    return TEXT[language]["welcome"].format(name=name)


def _keyboard(buttons, *, row_width=2):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=row_width)
    for i in range(0, len(buttons), row_width):
        keyboard.row(*[types.KeyboardButton(b) for b in buttons[i:i + row_width]])
    return keyboard


def _menu(bot, chat_id, caption, options):
    bot.send_message(chat_id, caption, reply_markup=_keyboard(options))


def register_ui_v57_handlers(bot, show_main_menu):
    """Register BEFORE legacy feature handlers to avoid stale state interception."""
    def show_categories(m):
        show_main_menu(m.chat.id, m.from_user.first_name or "Friend")

    def show_help(m):
        lng = get_language(m.from_user.id)
        _menu(bot, m.chat.id, TEXT[lng]["help"],
              list(GUIDE_BUTTONS) + ["🔎 Find a Tool", LANGUAGE_MENU, BACK_CATEGORIES])

    def show_languages(m):
        if getattr(m.chat, "type", None) != "private":
            bot.send_message(m.chat.id, TEXT["en"]["private"])
            return
        lng = get_language(m.from_user.id)
        _menu(bot, m.chat.id, TEXT[lng]["language"],
              list(LANG_BUTTONS) + [BACK_CATEGORIES])

    def show_category(m, category):
        lng = get_language(m.from_user.id)
        caption = category + "\n\n" + CATEGORY_TEXT[lng][category] + "\n\n" + TEXT[lng]["category"]
        _menu(bot, m.chat.id, caption,
              CATEGORY_FEATURES[category] + [BACK_CATEGORIES, HELP_CENTER])

    @bot.message_handler(commands=["tutorial", "guide"])
    def command_help(m):
        show_help(m)

    @bot.message_handler(commands=["language", "lang"])
    def command_lang(m):
        show_languages(m)

    @bot.message_handler(commands=["categories"])
    def command_categories(m):
        show_categories(m)

    @bot.message_handler(func=lambda m: getattr(m, "text", None) in ALL_UI_BUTTONS)
    def ui_button(m):
        button = m.text
        if button in CATEGORY_FEATURES:
            show_category(m, button)
        elif button == HELP_CENTER:
            show_help(m)
        elif button == LANGUAGE_MENU:
            show_languages(m)
        elif button == "🔎 Find a Tool":
            bot.send_message(m.chat.id,
                "🔎 Find a feature quickly!\nSend /findtool followed by a keyword.\n"
                "Examples: /findtool pdf, /findtool collections, /findtool flashcard, "
                "/findtool தமிழ்")
        elif button == BACK_CATEGORIES:
            show_categories(m)
        elif button in LANG_BUTTONS:
            if getattr(m.chat, "type", "private") != "private":
                bot.send_message(m.chat.id, TEXT["en"]["private"])
                return
            lng = LANG_BUTTONS[button]
            persisted = set_language(m.from_user.id, lng)
            note = "" if persisted else "\n⚠️ Preference is temporary until SQL_V5_7_UI.sql is applied."
            bot.send_message(m.chat.id, TEXT[lng]["saved"] + note)
            show_categories(m)
        elif button in GUIDE_BUTTONS:
            lng = get_language(m.from_user.id)
            _menu(bot, m.chat.id, GUIDES[GUIDE_BUTTONS[button]][lng],
                  [HELP_CENTER, BACK_CATEGORIES])

    return True

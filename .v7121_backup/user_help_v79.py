"""V7.9 read-only feature finder: friendly help with no external API calls."""
from ui_v57 import CATEGORY_FEATURES

# Search terms never change existing Telegram button labels.
ALIASES = {
    "🤖 Ask AI": "cloudflare gemini chatbot question tutor doubt artificial intelligence ai",
    "📝 Ask My Notes": "notes explain saved note தமிழ் குறிப்புகள்",
    "📄 Ask My PDF": "document pdf explain question textbook",
    "📚 Study Materials": "pdf docx txt files upload documents materiallibrary materialread",
    "📝 Notes": "notes write save notebook குறிப்புகள்",
    "🧠 Flashcards": "memory spaced repetition revision cards",
    "🧠 Due Reviews": "repetition review schedule revision",
    "❓ Quiz": "mcq practice tests exams quiz",
    "📝 Exams": "exam preparation dates schedule பரீட்சை தேர்வு",
    "🌐 Translate": "translation translator மொழிபெயர்ப்பு தமிழ் සිංහල العربية",
    "🎙 Voice Notes": "audio speech transcription voice",
    "📅 Assignments": "homework deadline due assignment",
    "📚 Revision Planner": "study plan syllabus revision schedule",
    "📊 Grades & GPA": "gpa marks results grades university credits",
}

# Newer V6/V7 features use commands, not necessarily V5.7 menu labels.
EXTRA_COMMANDS = [
    ("📦 More Tools", "📢 Announcements", "/announcements", "updates subscribe unsubscribe announcements broadcast messages"),
    ("📚 Study Tools", "📚 AI Notes Library", "/studylibrary", "saved ai notes search library"),
    ("📚 Study Tools", "🗂 Organize AI Notes", "/studyorganize", "favorites subjects folders notes"),
    ("📚 Study Tools", "📁 My Collections", "/collections", "collections folders group notes"),
    ("📚 Study Tools", "📚 Material Library", "/materiallibrary", "pdf docx txt files documents browse"),
    ("📚 Study Tools", "🧰 Material Filters", "/materialfilters", "subject pdf txt docx filters statistics"),
    ("📚 Study Tools", "📖 Material Reader", "/materiallibrary", "materialread materialinside read full text search inside material chapters"),
    ("📚 Study Tools", "📤 Export AI Notes", "/studyexport", "export download backup notes txt markdown"),
    ("📚 Study Tools", "📊 Collection Tools", "/collectiontools", "collection statistics search export"),
]


QUICK_HELP = {
    "en": ("🎓 Student Assistant — Quick Help\n\n"
           "Choose a category using the buttons below.\n\n"
           "🤖 AI & Questions — AI help, Ask My Notes/PDF\n"
           "📚 Study Tools — subjects, notes, materials, revision library\n"
           "📅 Plans & Reminders — assignments, exams, reminders\n"
           "🧠 Practice & Quiz — flashcards, quizzes, revision\n"
           "🌍 Languages — translation, vocabulary\n"
           "📊 My Progress — grades, GPA, achievements\n"
           "🎙 Voice & PDF — audio notes and PDF tools\n"
           "📦 More Tools — resources and your data backup\n\n"
           "🔎 Can't find something? Send /findtool pdf or /findtool exams\n"
           "❓ Step-by-step instructions: /guide\n"
           "🌐 Tamil/Sinhala/English/Arabic guidance: /language\n"
           "🏠 Return to the categories any time: /start\n\n"
           "🔒 Please avoid sharing passwords or sensitive information with AI."),
    "ta": ("🎓 Student Assistant — விரைவு உதவி\n\n"
           "கீழே உள்ள வகையைத் தேர்ந்தெடுக்கவும்.\n\n"
           "🤖 AI & Questions — AI கேள்விகள், Notes/PDF விளக்கம்\n"
           "📚 Study Tools — பாடங்கள், குறிப்புகள், Study Materials\n"
           "📅 Plans & Reminders — தேர்வுகள், assignments, நினைவூட்டல்கள்\n"
           "🧠 Practice & Quiz — Flashcards, Quiz, Revision\n"
           "🌍 Languages — மொழிபெயர்ப்பு, சொற்கள்\n"
           "📊 My Progress — GPA, மதிப்பெண்கள், முன்னேற்றம்\n"
           "🎙 Voice & PDF — குரல் குறிப்புகள், PDF வசதிகள்\n"
           "📦 More Tools — கூடுதல் வளங்கள், Data Backup\n\n"
           "🔎 வேண்டிய வசதியைத் தேட: /findtool pdf அல்லது /findtool தமிழ்\n"
           "❓ பயன்படுத்தும் வழிகாட்டி: /guide\n"
           "🌐 மொழி மாற்ற: /language\n"
           "🏠 முதன்மை மெனு: /start\n\n"
           "🔒 கடவுச்சொற்கள், ரகசியத் தகவல்களை AI-க்கு அனுப்ப வேண்டாம்."),
    "si": ("🎓 Student Assistant — ඉක්මන් උදව්\n\n"
           "පහත කාණ්ඩයකින් ඔබට අවශ්‍ය මෙවලම තෝරන්න.\n\n"
           "🤖 AI & Questions — AI ප්‍රශ්න, සටහන්/PDF\n"
           "📚 Study Tools — විෂයයන්, සටහන්, ලේඛන\n"
           "📅 Plans & Reminders — විභාග, පැවරුම්, මතක් කිරීම්\n"
           "🧠 Practice & Quiz — Flashcards, Quiz, නැවත අධ්‍යයනය\n"
           "🌍 Languages — පරිවර්තනය සහ වචන\n"
           "📊 My Progress — ලකුණු, GPA, ප්‍රගතිය\n"
           "🎙 Voice & PDF — හඬ සටහන්, PDF\n"
           "📦 More Tools — සම්පත්, දත්ත පිටපත\n\n"
           "🔎 මෙවලමක් සොයන්න: /findtool pdf\n"
           "❓ උපදෙස්: /guide\n"
           "🌐 භාෂාව: /language\n"
           "🏠 ප්‍රධාන මෙනුව: /start\n\n"
           "🔒 රහස්පද හෝ සංවේදී දත්ත AI සමඟ බෙදා නොගන්න."),
    "ar": ("🎓 مساعد الطالب — مساعدة سريعة\n\n"
           "اختر القسم المناسب من الأزرار أدناه.\n\n"
           "🤖 AI & Questions — أسئلة الذكاء الاصطناعي والملاحظات/PDF\n"
           "📚 Study Tools — المواد والملاحظات والوثائق\n"
           "📅 Plans & Reminders — الاختبارات والواجبات والتذكيرات\n"
           "🧠 Practice & Quiz — البطاقات والاختبارات والمراجعة\n"
           "🌍 Languages — الترجمة والمفردات\n"
           "📊 My Progress — الدرجات والمعدل والتقدم\n"
           "🎙 Voice & PDF — الصوت والملفات\n"
           "📦 More Tools — الموارد والنسخ الاحتياطي\n\n"
           "🔎 للبحث عن أداة: /findtool pdf\n"
           "❓ الدليل: /guide\n"
           "🌐 اللغة: /language\n"
           "🏠 القائمة الرئيسية: /start\n\n"
           "🔒 لا تشارك كلمات المرور أو المعلومات الحساسة مع AI."),
}


def build_quick_help_text(language="en"):
    base = QUICK_HELP.get(language, QUICK_HELP["en"])
    return base + "\n\n📢 Bot announcements: /announcements · /subscribe · /unsubscribe"


def find_tools(query, limit=7):
    """List grounded menu routes and existing commands; no invented buttons."""
    q = " ".join(str(query or "").strip().casefold().split())
    if len(q) < 2 or len(q) > 90:
        return []
    terms = [w for w in q.split() if len(w) > 1]
    results = []

    def score_text(label, words):
        words = words.casefold()
        return ((10 if q in label.casefold() else 0)
                + (5 if q in words else 0)
                + sum(2 for word in terms if word in words))

    for category, buttons in CATEGORY_FEATURES.items():
        for label in buttons:
            score = score_text(label, category + " " + label + " " + ALIASES.get(label, ""))
            if score:
                results.append((-score, label, f"/start → {category} → {label}"))

    for category, label, command, words in EXTRA_COMMANDS:
        score = score_text(label, label + " " + command + " " + words)
        if score:
            results.append((-score, label, command))

    results.sort(key=lambda item: (item[0], item[1], item[2]))
    return [(label, route) for _, label, route in results[:limit]]


def register_user_help_v79_handlers(bot):
    @bot.message_handler(commands=["findtool", "findfeature"])
    def feature_finder(message):
        raw = (getattr(message, "text", "") or "").strip()
        query = raw.partition(" ")[2].strip()
        if not query:
            bot.send_message(message.chat.id,
                "🔎 Find a Tool\nTry /findtool pdf, /findtool collections, "
                "/findtool exam, /findtool தமிழ் or /findtool flashcard.")
            return
        matches = find_tools(query)
        if not matches:
            bot.send_message(message.chat.id,
                "No matching tool found. Try a shorter keyword or open /guide.")
            return
        lines = ["🔎 Matching tools:"]
        for label, route in matches:
            lines.append("• " + label + "\n  Open: " + route)
        bot.send_message(message.chat.id, "\n".join(lines))

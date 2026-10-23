# 🎓 Student Assistant Telegram Bot

A Python-based Telegram bot designed to help students with common study tasks such as PDF management, personal notes, translation, and study reminders.

## ✨ Features

### 📄 PDF Tools

The bot currently supports:

- 🔗 Merge multiple PDF files
- ✂️ Extract selected PDF pages
- 🖼 Convert multiple images into a PDF
- 🔄 Rotate PDF pages
- 🔒 Password-protect PDF files

### 📝 Notes

Each Telegram user can manage personal notes.

Available options:

- ➕ Add Note
- 📚 View Notes
- 🔍 Search Notes
- 🗑 Delete Notes

Notes are stored using SQLite.

### 🌐 Translation

Supported languages:

- 🇬🇧 English
- 🇱🇰 Tamil
- 🇸🇦 Arabic
- 🇱🇰 Sinhala
- 🔎 Automatic source-language detection

The bot uses translation services through the `deep-translator` Python package.

### ⏰ Study Reminders

Users can:

- ➕ Create study reminders
- 📋 View upcoming reminders
- 🗑 Delete reminders

Reminder times use the Sri Lanka timezone:

```text
Asia/Colombo
```

Reminders are stored in SQLite so they remain available after restarting the bot.

---

# 📁 Project Structure

```text
StudentAssistantBot/
│
├── main.py
├── config.py
├── pdf_tools.py
├── notes.py
├── translate.py
├── reminders.py
├── requirements.txt
├── .gitignore
└── README.md
```

### File Explanation

#### `main.py`

Main entry point of the Telegram bot.

It:

- starts the bot
- creates the main menu
- registers all bot modules
- starts the reminder worker
- starts Telegram polling

#### `config.py`

Loads configuration values such as:

```text
BOT_TOKEN
```

It also determines where the SQLite database should be stored.

#### `pdf_tools.py`

Contains all PDF-related features.

#### `notes.py`

Contains the personal Notes system.

#### `translate.py`

Handles translation between supported languages.

#### `reminders.py`

Handles study reminder creation, storage, deletion, and automatic notification.

#### `requirements.txt`

Contains the Python packages required to run the bot.

---

# 🔐 Environment Variables

The Telegram bot token is **not stored inside the source code**.

A local `.env` file is used instead.

Example:

```text
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

## ⚠️ Why is `.env` not uploaded to GitHub?

The `.env` file contains secret information such as the Telegram bot token.

Publishing the token publicly could allow another person to control the bot.

Therefore `.env` is included in `.gitignore`.

Example `.gitignore`:

```text
.env
student_bot.db
__pycache__/
*.pyc
.venv/
venv/
```

Anyone who downloads or clones this project must create their own `.env` file.

---

# 🤖 Create a Telegram Bot Token

1. Open Telegram.
2. Search for `@BotFather`.
3. Send:

```text
/newbot
```

4. Choose a bot name.
5. Choose a bot username.
6. BotFather will provide a token.

Create a `.env` file in the project folder:

```text
BOT_TOKEN=YOUR_TOKEN_FROM_BOTFATHER
```

Never share your Telegram bot token publicly.

---

# ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/RAHMANFAREETH/Student-Assistant-Telegram-Bot.git
```

Enter the project directory:

```bash
cd Student-Assistant-Telegram-Bot
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create:

```text
.env
```

and add:

```text
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

---

# ▶️ Run the Bot

Run:

```bash
python main.py
```

If everything is configured correctly, the terminal should show:

```text
✅ Student Assistant Bot is running...
⏰ Reminder system is running...
```

Then open your Telegram bot and send:

```text
/start
```

---

# 📦 Requirements

The project uses:

```text
pyTelegramBotAPI
python-dotenv
PyPDF2[crypto]
Pillow
deep-translator
tzdata
```

Install all packages with:

```bash
python -m pip install -r requirements.txt
```

---

# 💾 Database

The bot uses SQLite.

Database file:

```text
student_bot.db
```

It stores information such as:

- notes
- reminders
- reminder status

For local development, the database is created automatically.

For cloud deployment, persistent storage should be used so Notes and Reminders are not lost during redeployment.

---

# ☁️ Railway Deployment

This project can be deployed on Railway.

Recommended Railway settings:

### Start Command

```text
python main.py
```

### Environment Variable

Add:

```text
BOT_TOKEN
```

and set its value to your Telegram BotFather token.

Do not upload `.env` to Railway or GitHub.

Railway environment variables replace the local `.env` file.

### Persistent Volume

For SQLite persistence, attach a Railway volume using:

```text
/data
```

The application can then store its database at:

```text
/data/student_bot.db
```

---

# 🔄 Updating the Bot

After making changes:

```bash
git add .
```

```bash
git commit -m "Update bot"
```

```bash
git push
```

If Railway is connected to the GitHub repository, the new version can then be deployed automatically.

---

# 🛡️ Security

Never upload:

```text
.env
```

Never publicly share:

```text
BOT_TOKEN
```

If a Telegram bot token is accidentally exposed, revoke it immediately through BotFather and generate a new one.

---

# 🚀 Current Bot Modules

```text
🎓 Student Assistant Bot
│
├── 📄 PDF Tools
│   ├── Merge PDF
│   ├── Extract Pages
│   ├── Images → PDF
│   ├── Rotate PDF
│   └── Protect PDF
│
├── 📝 Notes
│   ├── Add
│   ├── View
│   ├── Search
│   └── Delete
│
├── 🌐 Translation
│   ├── English
│   ├── Tamil
│   ├── Arabic
│   ├── Sinhala
│   └── Auto Detect
│
└── ⏰ Study Reminders
    ├── Add Reminder
    ├── View Reminders
    └── Delete Reminder
```

---

# 👨‍💻 Developer

**Abdul Rahman**

GitHub:

```text
https://github.com/RAHMANFAREETH
```

Project:

```text
Student Assistant Telegram Bot
```

---

## 📌 Future Improvements

Possible future features include:

- 🤖 AI Study Assistant
- 📚 Study Material Storage
- 📊 Student Progress Tracking
- 📝 Assignment Manager
- 🧠 Quiz Generator
- 📅 Study Planner
- 🔔 Advanced recurring reminders
- 📑 Additional PDF tools

---

⭐ If you find this project useful, consider starring the repository.
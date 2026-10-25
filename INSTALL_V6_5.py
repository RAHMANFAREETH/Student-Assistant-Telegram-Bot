"""V6.5 installer: add confirmed AI-to-Notes/Flashcards saves to an exact V6.4 layout.

Never touches Cloudflare request logic, Gemini client, Supabase schema, or other handlers.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import sys
import tempfile

TARGET = "ai_study_assistant.py"
MARKER = "# V6.5: student-confirmed saves to Notes and Flashcards"

CONSTANTS_ANCHOR = 'V64_STUDY_ACTIONS = {'
CONSTANTS = '''# V6.5: student-confirmed saves to Notes and Flashcards
SAVE_NOTE_BUTTON = "💾 Save AI Answer"
SAVE_QUIZ_BUTTON = "🗂 Save AI Quiz"
SAVE_CONFIRM_BUTTON = "✅ Confirm Save"
SAVE_CANCEL_BUTTON = "❌ Cancel Save"
V65_SAVE_ACTIONS = frozenset((SAVE_NOTE_BUTTON, SAVE_QUIZ_BUTTON))


def _v65_confirmation_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.row(types.KeyboardButton(SAVE_CONFIRM_BUTTON), types.KeyboardButton(SAVE_CANCEL_BUTTON))
    return markup

'''

KEYBOARD_ANCHOR = '''    markup.add(types.KeyboardButton(PRACTICE_BUTTON))
    markup.add(types.KeyboardButton("🏠 Main Menu"))'''
KEYBOARD_PATCH = '''    markup.add(types.KeyboardButton(PRACTICE_BUTTON))
    markup.row(types.KeyboardButton(SAVE_NOTE_BUTTON), types.KeyboardButton(SAVE_QUIZ_BUTTON))
    markup.add(types.KeyboardButton("🏠 Main Menu"))'''

REMEMBER_ANCHOR = '''        ])[-HISTORY_PAIRS * 2:]
        entry["updated_at"] = time.monotonic()'''
REMEMBER_PATCH = '''        ])[-HISTORY_PAIRS * 2:]
        entry["updated_at"] = time.monotonic()
        # Keep the complete last moderated AI reply for explicit student saves.
        # This is memory-only (subject to the existing session TTL and size bound).
        entry["last_answer"] = answer if len(answer) <= 20000 else ""
        entry["last_question"] = question
        entry.pop("pending_save", None)
        entry["saved_note"] = False
        entry["saved_quiz"] = False'''

HANDLER_ANCHOR = '''        # V6.3 quick actions are opt-in. The normal quota and safety path still runs.
        if text in V63_FOLLOW_UPS:'''
HANDLER_PATCH = '''        # V6.5 save commands never call an AI provider or claim an AI quota.
        if text in V65_SAVE_ACTIONS or text in (SAVE_CONFIRM_BUTTON, SAVE_CANCEL_BUTTON):
            with _jobs_lock:
                busy = user_id in _active_user_ids
            if busy:
                bot.send_message(message.chat.id,
                    "⏳ The AI reply is still being generated. Try saving after it finishes.")
                return
            if text in V65_SAVE_ACTIONS:
                from ai_save_v65 import prepare_note, parse_quiz_cards, SaveValidationError
                with _sessions_lock:
                    if _sessions.get(user_id) is not session:
                        return
                    answer = session.get("last_answer") or ""
                    question = session.get("last_question") or ""
                    done = session.get("saved_note" if text == SAVE_NOTE_BUTTON else "saved_quiz", False)
                if done:
                    bot.send_message(message.chat.id, "✅ This answer was already saved in this chat session.")
                    return
                if not answer:
                    bot.send_message(message.chat.id,
                        "🤖 Ask AI for an answer first. Very long answers cannot be saved directly.")
                    return
                try:
                    if text == SAVE_NOTE_BUTTON:
                        payload = prepare_note(question, answer)
                        action = "note"
                        preview = ("📝 Save to My Notes?\\nTitle: " + payload["title"] +
                                   "\\nAnswer length: " + str(len(payload["content"])) + " characters")
                    else:
                        payload = parse_quiz_cards(answer)
                        action = "quiz"
                        preview = ("🧠 Save " + str(len(payload)) +
                                   " multiple-choice questions to Flashcards?\\n" +
                                   "Cards will be saved with No Subject.\\nFirst question: " +
                                   payload[0]["question"].splitlines()[0][:120])
                except SaveValidationError as exc:
                    bot.send_message(message.chat.id, "⚠️ " + str(exc))
                    return
                with _sessions_lock:
                    if _sessions.get(user_id) is not session:
                        return
                    session["pending_save"] = {"action": action, "payload": payload}
                bot.send_message(message.chat.id,
                    preview + "\\n\\nSelect Confirm Save or Cancel Save.",
                    reply_markup=_v65_confirmation_markup())
                return
            if text == SAVE_CANCEL_BUTTON:
                with _sessions_lock:
                    if _sessions.get(user_id) is session:
                        session.pop("pending_save", None)
                bot.send_message(message.chat.id, "❌ Save cancelled. Nothing was written.",
                                 reply_markup=_ai_chat_markup())
                return
            with _sessions_lock:
                if _sessions.get(user_id) is not session:
                    return
                pending = session.pop("pending_save", None)
            if not pending:
                bot.send_message(message.chat.id, "No save awaiting confirmation.",
                                 reply_markup=_ai_chat_markup())
                return
            try:
                from ai_save_v65 import save_note, save_flashcards
                if pending["action"] == "note":
                    new_id = save_note(supabase, user_id, pending["payload"])
                    response = f"✅ Note #{new_id} saved! Open 📝 Notes → 📚 View Notes."
                    flag = "saved_note"
                else:
                    saved = save_flashcards(supabase, user_id, pending["payload"])
                    response = (f"✅ {saved} flashcards saved! Open 🧠 Flashcards → "
                                "📚 My Flashcards. They are filed under No Subject.")
                    flag = "saved_quiz"
                with _sessions_lock:
                    if _sessions.get(user_id) is session:
                        session[flag] = True
                bot.send_message(message.chat.id, response, reply_markup=_ai_chat_markup())
            except Exception as exc:
                # Never log prompts, answers, student records or API credentials.
                print("V6.5 save failure type:", type(exc).__name__)
                bot.send_message(message.chat.id,
                    "⚠️ Could not verify the save in Supabase. Please check My Notes/Flashcards "
                    "before trying again to avoid duplicates.", reply_markup=_ai_chat_markup())
            return
        # V6.3 quick actions are opt-in. The normal quota and safety path still runs.
        if text in V63_FOLLOW_UPS:'''


def patch_ai(source: str) -> tuple[str, bool]:
    ast.parse(source, filename=TARGET)
    eol = '\r\n' if '\r\n' in source else '\n'
    if MARKER in source:
        checks = (
            source.count(MARKER) == 1,
            source.count('V65_SAVE_ACTIONS = ') == 1,
            source.count('if text in V65_SAVE_ACTIONS') == 2,
            source.count('entry["last_answer"] = ') == 1,
            source.count('types.KeyboardButton(SAVE_NOTE_BUTTON)') == 1,
            source.count('types.KeyboardButton(SAVE_QUIZ_BUTTON)') == 1,
        )
        if not all(checks):
            raise ValueError('Partial V6.5 patch detected; files not changed')
        return source, False
    expected = (
        '# V6.4: turn the latest AI answer into study aids',
        '# V6.3: student-controlled AI follow-up shortcuts',
        'def _remember(user_id, question, answer):',
        'V64_STUDY_ACTIONS = {',
        'if text in V64_STUDY_ACTIONS:',
        'def claim_quota(',
        '_provider_call = observe_cloudflare_health(_provider_call)',
        '_provider_call = wrap_cloudflare_provider(_provider_call)',
        'def _check_safety(',
        'def ai_chat_message(message):',
    )
    if any(fragment not in source for fragment in expected):
        raise ValueError('Expected exact V6.4 AI module not found; files not changed')
    anchors = (CONSTANTS_ANCHOR, KEYBOARD_ANCHOR, REMEMBER_ANCHOR, HANDLER_ANCHOR)
    if any(source.count(anchor.replace('\n', eol)) != 1 for anchor in anchors):
        raise ValueError('Expected V6.4 patch points differ; files not changed')
    result = source
    for before, after in (
        (CONSTANTS_ANCHOR, CONSTANTS + CONSTANTS_ANCHOR),
        (KEYBOARD_ANCHOR, KEYBOARD_PATCH),
        (REMEMBER_ANCHOR, REMEMBER_PATCH),
        (HANDLER_ANCHOR, HANDLER_PATCH),
    ):
        result = result.replace(before.replace('\n', eol), after.replace('\n', eol), 1)
    ast.parse(result, filename=TARGET)
    return result, True


def install(root: Path = Path('.')) -> bool:
    root = Path(root)
    path = root / TARGET
    helper = root / 'ai_save_v65.py'
    if not path.is_file() or not helper.is_file():
        raise ValueError('Required project files missing; copy ai_save_v65.py to the bot folder')
    with path.open('r', encoding='utf-8', newline='') as fh:
        before = fh.read()
    after, changed = patch_ai(before)
    if not changed:
        return False
    backup = root / (TARGET + '.before_v65.bak')
    if backup.exists():
        raise ValueError('Backup already exists; refusing to overwrite ' + backup.name)
    shutil.copy2(path, backup)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='', dir=root,
                                         prefix='.v65_', suffix='.tmp', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(after)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)
        raise
    return True


if __name__ == '__main__':
    try:
        changed = install()
    except (ValueError, OSError, UnicodeError, SyntaxError) as exc:
        print('V6.5 safely stopped:', exc)
        sys.exit(1)
    print('V6.5 installed; backup created.' if changed else 'V6.5 already installed; no files changed.')

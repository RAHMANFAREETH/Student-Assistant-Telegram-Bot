"""V6.5: confirmed saves from a private Cloudflare AI chat into existing Supabase tables.

No AI calls, no Telegram registration, no new SQL; DB client is passed explicitly.
"""
from __future__ import annotations

import re

MAX_SAVE_CHARS = 20000
MAX_CARDS = 5


class SaveValidationError(ValueError):
    """Cannot safely make a study record from the provided content."""


def prepare_note(question: str, answer: str) -> dict:
    answer = (answer or "").strip()
    if not answer or len(answer) > MAX_SAVE_CHARS:
        raise SaveValidationError("The AI answer is empty or too long to save. Ask for a shorter answer.")
    title_part = re.sub(r"\s+", " ", (question or "").strip())[:95].strip()
    title = "AI Study: " + (title_part or "Study answer")
    return {"title": title, "content": answer}


_Q = re.compile(r"^\s*(?:(?:Question|Q|கேள்வி|السؤال|ප්‍රශ්නය)\s*)?([1-5])\s*[.):\-]\s*(\S.*)$", re.I)
_OPTION = re.compile(r"^\s*([A-D])\s*[).:\-]\s*(\S.*)$", re.I)
_ANSWER = re.compile(r"^\s*(?:[Qq]\s*)?([1-5])\s*[).:\-]\s*(?:Answer\s*[:\-]?\s*)?([A-D])(?:\b|\s|[).:\-])\s*(.*)$", re.I)
_KEY_HEADING = re.compile(r"^\s*[*# _]*(?:answer\s*key|answers?|solutions?|correct\s*answers?|விடைகள்|பதில்கள்|சரியான\s*பதில்கள்|الإجابات|الأجوبة|පිළිතුරු|නිවැරදි\s*පිළිතුරු)\s*[:：-]?\s*$|^\s*(?:Answer\s*Key|Answers?)\s*:\s*\d", re.I)


def parse_quiz_cards(answer: str) -> list[dict]:
    """Parse strict A-D MCQs plus a numbered answer key. Never infer missing answers.

    Returns question/answer only; caller applies Telegram user_id and subject_id.
    """
    answer = (answer or "").strip()
    if not answer or len(answer) > MAX_SAVE_CHARS:
        raise SaveValidationError("There is no complete AI quiz to save.")
    lines = answer.splitlines()
    questions = {}
    key = {}
    part = "questions"
    current = None
    for raw in lines:
        line = raw.strip().strip('`')
        line = re.sub(r"^\*{1,2}(.*?)\*{1,2}$", r"\1", line).strip()
        if not line:
            continue
        if _KEY_HEADING.search(line):
            part = "answers"
            current = None
            # Detect a key on the same line as the heading, e.g. 'Answers: 1. B'
            tail = line.split(":", 1)[1].strip() if ":" in line else ""
            if tail:
                line = tail
            else:
                continue
        if part == "answers":
            match = _ANSWER.match(line)
            if match:
                no, letter, extra = match.groups()
                no = int(no)
                if no in key:
                    raise SaveValidationError("The quiz answer key contains duplicate entries.")
                key[no] = (letter.upper(), extra.strip())
            continue
        qmatch = _Q.match(line)
        if qmatch:
            no = int(qmatch.group(1))
            if no in questions:
                raise SaveValidationError("The quiz has duplicate question numbers.")
            questions[no] = {"prompt": qmatch.group(2).strip(), "options": {}}
            current = no
            continue
        optmatch = _OPTION.match(line)
        if optmatch and current is not None:
            letter, content = optmatch.groups()
            letter = letter.upper()
            if letter in questions[current]["options"]:
                raise SaveValidationError("The quiz has duplicate options.")
            questions[current]["options"][letter] = content.strip()

    if not questions or len(questions) > MAX_CARDS or set(questions) != set(key):
        raise SaveValidationError(
            "Quiz format is incomplete. Generate a quiz with numbered questions, A-D choices, "
            "and a numbered Answer Key (1. B, 2. A, ...), then try again."
        )
    cards = []
    for number in sorted(questions):
        question = questions[number]
        options = question["options"]
        letter, explanation = key[number]
        if set(options) != set("ABCD") or not options.get(letter):
            raise SaveValidationError("Quiz options or answer key are incomplete; no cards were saved.")
        qtext = f"{question['prompt']}\n" + "\n".join(f"{ch}) {options[ch]}" for ch in "ABCD")
        atext = f"{letter}) {options[letter]}"
        if explanation:
            atext += "\n" + explanation[:450]
        if len(qtext) > 2000 or len(atext) > 2000:
            raise SaveValidationError("A question or answer is too long for a flashcard.")
        cards.append({"question": qtext, "answer": atext})
    return cards


def save_note(supabase, user_id: int, note: dict) -> int:
    uid = int(user_id)
    if uid <= 0:
        raise SaveValidationError("Invalid student ID.")
    response = (supabase.table("notes")
                .insert({"user_id": uid, "title": note["title"], "content": note["content"]})
                .select("id").execute())
    data = getattr(response, "data", None) or []
    if not data or "id" not in data[0]:
        raise RuntimeError("Unable to verify saved note.")
    return int(data[0]["id"])


def save_flashcards(supabase, user_id: int, cards: list[dict]) -> int:
    uid = int(user_id)
    if uid <= 0 or not 1 <= len(cards) <= MAX_CARDS:
        raise SaveValidationError("Invalid student ID or flashcards.")
    payload = [{"user_id": uid, "subject_id": None, "question": c["question"],
                "answer": c["answer"]} for c in cards]
    response = supabase.table("flashcards").insert(payload).select("id").execute()
    data = getattr(response, "data", None) or []
    if len(data) != len(payload):
        raise RuntimeError("Unable to verify saved flashcards.")
    return len(data)

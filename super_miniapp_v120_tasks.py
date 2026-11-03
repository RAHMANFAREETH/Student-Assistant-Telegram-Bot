"""V12 private quick-task service. Never accepts a user ID from the browser.

Only call from routes after Telegram initData HMAC and verified-adult checks.
Uses existing server-side db.supabase; the browser never receives credentials.
"""
from __future__ import annotations

from uuid import UUID

MAX_TASKS = 100
TABLE = 'v120_quick_tasks'


class TaskInputError(ValueError):
    pass


class TaskLimitError(TaskInputError):
    pass


def _uuid(value):
    if not isinstance(value, str) or len(value) > 40:
        raise TaskInputError('Invalid task ID.')
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise TaskInputError('Invalid task ID.') from exc
    # Canonical hyphenated UUID only; browser imports preserve this for idempotency.
    if str(parsed) != value.lower():
        raise TaskInputError('Invalid task ID.')
    return str(parsed)


def _uid(value):
    if type(value) is not int or value <= 0:
        raise TaskInputError('Invalid account.')
    return value


def _db():
    from db import supabase
    return supabase


def _clean_row(row):
    return {
        'id': str(row['id']),
        'text': str(row['title'])[:160],
        'done': row.get('done') is True,
    }


def list_tasks(user_id, client=None):
    uid = _uid(user_id)
    db = client if client is not None else _db()
    rows = (db.table(TABLE).select('id,title,done,created_at')
            .eq('user_id', uid).order('created_at', desc=False)
            .limit(MAX_TASKS).execute()).data or []
    return [_clean_row(r) for r in rows if isinstance(r, dict) and r.get('id') and 'title' in r]


def create_task(user_id, body, client=None):
    uid = _uid(user_id)
    if not isinstance(body, dict) or set(body) - {'id', 'text', 'done'}:
        raise TaskInputError('Invalid task request.')
    text = body.get('text')
    if not isinstance(text, str) or not text.strip() or len(text.strip()) > 160 or '\x00' in text:
        raise TaskInputError('Task text must be 1 to 160 characters.')
    text = text.strip()
    done = body.get('done', False)
    if type(done) is not bool:
        raise TaskInputError('Invalid task completion value.')
    tid = _uuid(body.get('id'))
    db = client if client is not None else _db()
    # Idempotency: after an uncertain network response, repeating POST with the
    # same UUID returns the previously stored row and does not create a duplicate.
    found = (db.table(TABLE).select('id,title,done')
             .eq('user_id', uid).eq('id', tid).limit(1).execute()).data or []
    if found:
        return _clean_row(found[0]), False
    count_rows = (db.table(TABLE).select('id').eq('user_id', uid)
                  .limit(MAX_TASKS).execute()).data or []
    if len(count_rows) >= MAX_TASKS:
        raise TaskLimitError('Maximum of 100 synchronized tasks.')
    # Database trigger also protects quota against simultaneous requests.
    stored = (db.table(TABLE).insert({'user_id': uid, 'id': tid, 'title': text, 'done': done})
              .execute()).data or []
    if not stored:
        # Some PostgREST configurations return no rows for INSERT.
        stored = (db.table(TABLE).select('id,title,done').eq('user_id', uid)
                  .eq('id', tid).limit(1).execute()).data or []
    if not stored:
        raise RuntimeError('Task write did not return a row.')
    return _clean_row(stored[0]), True


def update_task(user_id, task_id, body, client=None):
    uid = _uid(user_id)
    tid = _uuid(task_id)
    if not isinstance(body, dict) or set(body) != {'done'} or type(body['done']) is not bool:
        raise TaskInputError('Expected a boolean done value.')
    db = client if client is not None else _db()
    rows = (db.table(TABLE).update({'done': body['done']})
            .eq('user_id', uid).eq('id', tid).execute()).data or []
    return _clean_row(rows[0]) if rows else None


def delete_task(user_id, task_id, client=None):
    uid = _uid(user_id)
    tid = _uuid(task_id)
    db = client if client is not None else _db()
    # Deleted IDs are intentionally not enumerable. Always scoped to owner.
    db.table(TABLE).delete().eq('user_id', uid).eq('id', tid).execute()
    return True

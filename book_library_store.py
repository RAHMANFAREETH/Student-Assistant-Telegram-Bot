"""Book Library data layer. Bot stores only a catalog; files remain in Telegram.

Requires SQL_BOOK_LIBRARY.sql and the existing service-role db.supabase client.
Never exposes the service key or storage-channel IDs in search results.
"""
from __future__ import annotations
import os
import re
import uuid

TABLE = 'book_library_items'
FIELDS = 'id,title,author,language,file_name,file_size,channel_id,message_id,added_at,active'

class LibraryError(RuntimeError):
    pass


def _db():
    from db import supabase
    return supabase


def _rows(result):
    return getattr(result, 'data', None) or []


def validate_metadata(title: str, author: str, language: str):
    title, author, language = (str(x).strip() for x in (title, author, language))
    if not (2 <= len(title) <= 180 and 2 <= len(author) <= 120 and 2 <= len(language) <= 40):
        raise ValueError('Title (2–180), author (2–120), and language (2–40) are required.')
    if any('\n' in x or '\r' in x or '<' in x or '>' in x for x in (title, author, language)):
        raise ValueError('Single-line plain-text catalog details only.')
    return title, author, language


def parse_caption(caption: str):
    bits = (caption or '').split('|')
    if len(bits) != 3:
        raise ValueError('Use this caption exactly: Title | Author | Language')
    return validate_metadata(*bits)


def format_size(n):
    try:
        n = max(0, int(n or 0))
    except (TypeError, ValueError):
        return 'Unknown size'
    if n >= 1024 * 1024 * 1024:
        return f'{n / (1024 ** 3):.2f} GB'
    if n >= 1024 * 1024:
        return f'{n / (1024 ** 2):.1f} MB'
    return f'{n / 1024:.0f} KB'


def add_book(*, title, author, language, channel_id, message_id, file_name,
             file_size, uploaded_by, db=None):
    title, author, language = validate_metadata(title, author, language)
    if int(channel_id) >= 0 or int(message_id) <= 0 or int(uploaded_by) <= 0:
        raise ValueError('Invalid Telegram identifiers.')
    values = dict(title=title, author=author, language=language,
                  channel_id=int(channel_id), message_id=int(message_id),
                  file_name=str(file_name or '')[:255], file_size=int(file_size or 0),
                  uploaded_by=int(uploaded_by), active=True)
    rows = _rows((db or _db()).table(TABLE).insert(values).execute())
    if not rows or not rows[0].get('id'):
        raise LibraryError('Catalog record could not be confirmed.')
    return rows[0]


def search_books(query, *, limit=8, db=None):
    query = str(query or '').strip()
    if not 2 <= len(query) <= 100:
        return []
    # RPC uses a bind parameter and substring matching; never interpolate a PostgREST filter.
    rows = _rows((db or _db()).rpc('book_library_search', {
        'p_query': query, 'p_limit': max(1, min(int(limit), 10))
    }).execute())
    return [r for r in rows if isinstance(r, dict) and r.get('active', True)]


def latest_books(*, limit=8, db=None):
    return _rows((db or _db()).table(TABLE).select(FIELDS)
                 .eq('active', True).order('added_at', desc=True)
                 .limit(max(1, min(int(limit), 10))).execute())


def get_book(book_id, *, db=None):
    try:
        key = str(uuid.UUID(str(book_id)))
    except (ValueError, TypeError, AttributeError):
        return None
    rows = _rows((db or _db()).table(TABLE).select(FIELDS)
                 .eq('id', key).eq('active', True).limit(1).execute())
    return rows[0] if rows else None


def deactivate_book(book_id, *, db=None):
    try:
        key = str(uuid.UUID(str(book_id)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError('Invalid book UUID.')
    rows = _rows((db or _db()).table(TABLE).update({'active': False})
                 .eq('id', key).eq('active', True).execute())
    return bool(rows)

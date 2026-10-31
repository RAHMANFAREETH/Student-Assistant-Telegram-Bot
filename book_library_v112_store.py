"""V11.2 private-channel library enhancements; service-role Supabase client only."""
from __future__ import annotations
import re
import uuid

BOOKS = 'book_library_items'
FAVORITES = 'book_library_favorites'
PUBLIC_FIELDS = 'id,title,author,language,category,isbn,file_size,cover_file_id,download_count,added_at,active'


def _db():
    from db import supabase
    return supabase


def _rows(result):
    data = getattr(result, 'data', None)
    return data if isinstance(data, list) else []


def uid(value):
    number = int(value)
    if number <= 0:
        raise ValueError('Invalid Telegram user ID.')
    return number


def book_uuid(value):
    return str(uuid.UUID(str(value)))


def simple_text(value, *, min_len=2, max_len=120):
    value = str(value or '').strip()
    if not min_len <= len(value) <= max_len or any(ch in value for ch in '<>\n\r|'):
        raise ValueError(f'Use one line of {min_len}–{max_len} plain-text characters.')
    return value


def normalize_isbn(value):
    if value is None or str(value).strip() in ('', '-', 'none'):
        return None
    value = re.sub(r'[ -]', '', str(value)).upper()
    if not re.fullmatch(r'(?:[0-9]{13}|[0-9]{9}[0-9X])', value):
        raise ValueError('ISBN must contain 10 or 13 digits (ISBN-10 may end in X).')
    if len(value) == 10:
        total = sum((10-i) * (10 if digit == 'X' else int(digit)) for i, digit in enumerate(value))
        if total % 11:
            raise ValueError('ISBN-10 check digit is invalid.')
    elif sum(int(x)*(1 if i % 2 == 0 else 3) for i, x in enumerate(value)) % 10:
        raise ValueError('ISBN-13 check digit is invalid.')
    return value


def parse_extended_caption(caption):
    """Title | Author | Language [| Category [| ISBN]], backward-compatible."""
    chunks = [c.strip() for c in str(caption or '').split('|')]
    if len(chunks) not in (3, 4, 5):
        raise ValueError('Caption: Title | Author | Language | Category | ISBN (last two optional).')
    from book_library_store import validate_metadata
    title, author, language = validate_metadata(*chunks[:3])
    category = simple_text(chunks[3], max_len=60) if len(chunks) >= 4 else 'General'
    isbn = normalize_isbn(chunks[4]) if len(chunks) == 5 else None
    return title, author, language, category, isbn


def browse_books(*, query=None, category=None, author=None, language=None,
                 isbn=None, page=0, page_size=5, db=None):
    page = int(page)
    if not 0 <= page <= 99:
        raise ValueError('Page must be between 0 and 99.')
    page_size = max(1, min(int(page_size), 8))
    filters = dict(p_query=query or None, p_category=category or None,
                   p_author=author or None, p_language=language or None,
                   p_isbn=normalize_isbn(isbn) if isbn else None,
                   p_limit=page_size+1, p_offset=page*page_size)
    if query is not None and not 2 <= len(str(query).strip()) <= 100:
        raise ValueError('Search needs 2–100 characters.')
    for val in (category, author, language):
        if val and len(str(val)) > 120:
            raise ValueError('Filter is too long.')
    data = _rows((db or _db()).rpc('book_library_v112_browse', filters).execute())
    return data[:page_size], len(data) > page_size


def facets(kind, *, db=None):
    if kind not in ('category', 'author', 'language'):
        raise ValueError('Invalid filter type.')
    return _rows((db or _db()).rpc('book_library_v112_facets', {'p_kind':kind}).execute())[:30]


def get_details(book_id, *, db=None):
    try:
        key = book_uuid(book_id)
    except (ValueError, TypeError, AttributeError):
        return None
    found = _rows((db or _db()).table(BOOKS).select(PUBLIC_FIELDS)
                  .eq('id', key).eq('active', True).limit(1).execute())
    return found[0] if found else None


def update_metadata(book_id, *, title, author, language, category='General', isbn=None, db=None):
    from book_library_store import validate_metadata
    title, author, language = validate_metadata(title, author, language)
    category = simple_text(category, max_len=60)
    isbn = normalize_isbn(isbn)
    data = dict(title=title, author=author, language=language, category=category, isbn=isbn)
    rows = _rows((db or _db()).table(BOOKS).update(data)
                 .eq('id', book_uuid(book_id)).eq('active', True).execute())
    return bool(rows)


def set_cover(book_id, file_id, *, db=None):
    if file_id is not None:
        file_id = str(file_id).strip()
        if not (3 <= len(file_id) <= 256) or any(c in file_id for c in '\n\r'):
            raise ValueError('Invalid Telegram photo file ID.')
    rows = _rows((db or _db()).table(BOOKS).update({'cover_file_id': file_id})
                 .eq('id', book_uuid(book_id)).eq('active', True).execute())
    return bool(rows)


def is_favorite(user_id, book_id, *, db=None):
    rows = _rows((db or _db()).table(FAVORITES).select('book_id')
                 .eq('user_id', uid(user_id)).eq('book_id', book_uuid(book_id))
                 .limit(1).execute())
    return bool(rows)


def toggle_favorite(user_id, book_id, *, db=None):
    d = db or _db()
    book_id = book_uuid(book_id)
    user_id = uid(user_id)
    if not get_details(book_id, db=d):
        raise ValueError('Book is unavailable.')
    # Toggle is scoped to the authenticated Telegram UID on the server, never user-provided UID.
    if is_favorite(user_id, book_id, db=d):
        d.table(FAVORITES).delete().eq('user_id', user_id).eq('book_id', book_id).execute()
        return False
    d.table(FAVORITES).upsert({'user_id':user_id, 'book_id':book_id},
                              on_conflict='user_id,book_id').execute()
    return True


def list_favorites(user_id, *, page=0, page_size=5, db=None):
    d = db or _db()
    page = int(page)
    if not 0 <= page <= 99:
        raise ValueError('Invalid page.')
    rows = _rows(d.table(FAVORITES).select('book_id').eq('user_id', uid(user_id))
                 .order('created_at', desc=True)
                 .range(page*page_size, page*page_size+page_size).execute())
    more = len(rows) > page_size
    selected = rows[:page_size]
    books = []
    for r in selected:
        obj = get_details(r['book_id'], db=d)
        if obj:
            books.append(obj)
    return books, more


def record_delivery(book_id, *, db=None):
    """Best-effort aggregate counter AFTER Telegram confirms the copy; stores no user IDs."""
    (db or _db()).rpc('book_library_v112_record_delivery', {'p_book_id':book_uuid(book_id)}).execute()


def top_downloaded(*, limit=10, db=None):
    return _rows((db or _db()).table(BOOKS).select(PUBLIC_FIELDS)
                 .eq('active', True).order('download_count', desc=True)
                 .limit(max(1, min(int(limit), 20))).execute())


def recently_uploaded(*, limit=10, db=None):
    return _rows((db or _db()).table(BOOKS).select(PUBLIC_FIELDS)
                 .eq('active', True).order('added_at', desc=True)
                 .limit(max(1, min(int(limit), 20))).execute())

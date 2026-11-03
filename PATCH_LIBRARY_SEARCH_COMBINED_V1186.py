"""V11.8.6 combined safe patch: V11.8.5 language UI + search progress/empty state.

Requires the installed V11.8.3 search module. Makes only three production
source edits, creates backups and is safe to rerun. No database writes.
"""
from __future__ import annotations
import argparse
import difflib
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from PATCH_LIBRARY_LANGUAGE_PICKER_V1185 import transform_search, transform_facets

MARK_MEDIA='# V11.8.6 user-visible search progress and zero-results feedback.'
MARK_UI='# V11.8.6 edit the searching message into results.'


def replace_once(src, old, new, name):
    n=src.count(old)
    if n != 1:
        raise ValueError(f'{name}: expected a single known anchor; found {n}: {old[:95]!r}')
    return src.replace(old,new,1)


def transform_media(src):
    name='library_media_v117_bot.py'
    if MARK_MEDIA in src:
        if src.count(MARK_MEDIA) != 1 or 'def _replace_search_status(' not in src:
            raise ValueError(name+': partial or duplicate V11.8.6 install')
        return src
    start=src.index('def unified_search(bot,chat_id,query,group=False,requester_id=None):')
    end=src.index('\ndef unified_latest(',start)
    old=src[start:end]
    new='''# V11.8.6 user-visible search progress and zero-results feedback.
def _remember_search_status(bot, chat_id, sent, *, group):
    if group and getattr(sent, 'message_id', None):
        try:
            from group_ui_v115 import _remember
            _remember(bot, chat_id, sent.message_id, kind='book_links')
        except Exception:
            LOG.warning('Cannot queue search message cleanup', exc_info=True)


def _searching_message(bot, chat_id, query, *, group):
    try:
        sent=_message(bot, chat_id,
            '🔎 SEARCHING FOR FILES\\n'
            f'📚 {query[:100]}\\n'
            '⏳ Checking the library catalog…'
            + ('\\nThis message auto-deletes after 5 minutes.' if group else ''))
    except Exception:
        LOG.warning('Search progress message could not be sent', exc_info=True)
        return None
    _remember_search_status(bot, chat_id, sent, group=group)
    return sent


def _replace_search_status(bot, chat_id, status, text, *, group, markup=None):
    """Edit progress in place; if unsupported, send final and remove progress."""
    mid=getattr(status, 'message_id', None)
    if mid is not None:
        try:
            updated=bot.edit_message_text(text, chat_id=chat_id, message_id=mid,
                                         reply_markup=markup)
            if updated is not False:
                return status
        except Exception:
            LOG.warning('Cannot edit search status; using a new message', exc_info=True)
    try:
        sent=_message(bot, chat_id, text, reply_markup=markup)
    except Exception:
        LOG.exception('Could not send search feedback')
        return False
    _remember_search_status(bot, chat_id, sent, group=group)
    if mid is not None:
        try: bot.delete_message(chat_id, mid)
        except Exception: LOG.debug('Search progress cleanup unavailable')
    return sent


def _no_search_results_keyboard(query):
    from urllib.parse import quote_plus
    kb=_keyboard()
    # Spelling lookup only: no third-party downloading or file forwarding.
    kb.add(_button('🔎 Check spelling on Google',
                   url='https://www.google.com/search?q='+quote_plus(query[:100])))
    return kb


def unified_search(bot,chat_id,query,group=False,requester_id=None):
    if not enabled():return None
    q=str(query or '').strip()
    if not q or len(q)>180:
        return _message(bot,chat_id,'🔎 Example: /book Arabic grammar type:image lang:Tamil')
    try:
        parse_search_query(q)
    except ValueError as exc:
        return _message(bot,chat_id,'⚠️ '+str(exc)[:250])
    status=_searching_message(bot,chat_id,q,group=group)
    try:
        items=union_search(q,limit=30)
        if not items:
            note=('😕 NO FILES FOUND\\n'
                  f'🔎 Search: {q[:100]}\\n\\n'
                  'Please check your spelling or try a shorter title, author, or another language.\\n'
                  '📚 Example: /book Psychology\\n'
                  '💌 You can request a missing book using /bookrequest TITLE in private.'
                  + ('\\n⏳ This result auto-deletes after 5 minutes.' if group else ''))
            return _replace_search_status(bot,chat_id,status,note,group=group,
                                          markup=_no_search_results_keyboard(q))
        heading=('📚 Library results: '+q[:100]+'\\n'
                 '📄 PDFs · 🖼️ Images · 🎧 Audio · 🎥 Video · 📦 ZIP\\n'
                 '📩 Tap an item to preview it privately.'
                 + ('\\n⏳ Auto-delete after 5 minutes.' if group else ''))
        if group and requester_id is None:
            # Preserve old URL-only keyboard when requester cannot be identified.
            result=_send_results(bot,chat_id,heading,items,group=group)
            if status is not None and getattr(status,'message_id',None):
                try: bot.delete_message(chat_id,status.message_id)
                except Exception: LOG.debug('Cannot remove search progress')
            return result
        from library_search_ui_v1183 import send_search_results
        return send_search_results(bot,chat_id,heading,items,group=group,
                                   requester_id=requester_id,status_message=status)
    except Exception:
        LOG.exception('V11.7 unified search failed')
        note=('⚠️ Library search is temporarily unavailable. Please try again later.'
              + ('\\n⏳ This message auto-deletes after 5 minutes.' if group else ''))
        return _replace_search_status(bot,chat_id,status,note,group=group)

'''
    src=src[:start]+new+src[end:]
    compile(src,name,'exec')
    return src


def transform_ui(src):
    name='library_search_ui_v1183.py'
    src=transform_search(src)  # Includes both language selection and Tamil file-list UI.
    if MARK_UI in src:
        if src.count(MARK_UI)!=1 or 'status_message=None' not in src:
            raise ValueError(name+': incomplete V11.8.6 update')
        return src
    old='''def send_search_results(bot, chat_id, heading, items, *, group=False, requester_id=None):
    """Called only by unified_search; prior latest/favorites menus stay unchanged."""
    from library_media_v117_bot import _message
    token, session = _create(chat_id, items, heading, group=group, requester_id=requester_id)
    text, kb = _display(bot, token, session)
    try:
        sent = _message(bot, chat_id, text, reply_markup=kb)
    except Exception:
        with _LOCK:
            _SESSIONS.pop(token, None)
        raise
'''
    new='''# V11.8.6 edit the searching message into results.
def send_search_results(bot, chat_id, heading, items, *, group=False, requester_id=None,
                        status_message=None):
    """Called only by unified_search; prior latest/favorites menus stay unchanged."""
    from library_media_v117_bot import _message
    token, session = _create(chat_id, items, heading, group=group, requester_id=requester_id)
    text, kb = _display(bot, token, session)
    mid=getattr(status_message, 'message_id', None)
    try:
        if mid is not None:
            try:
                updated=bot.edit_message_text(text, chat_id=chat_id,
                                              message_id=mid, reply_markup=kb)
                if updated is False:
                    raise RuntimeError('Telegram did not confirm result edit')
                sent=status_message
            except Exception:
                LOG.warning('Cannot replace progress; sending new results', exc_info=True)
                sent=_message(bot, chat_id, text, reply_markup=kb)
                try: bot.delete_message(chat_id, mid)
                except Exception: LOG.debug('Search progress cleanup unavailable')
        else:
            sent=_message(bot, chat_id, text, reply_markup=kb)
    except Exception:
        with _LOCK:
            _SESSIONS.pop(token, None)
        raise
'''
    src=replace_once(src,old,new,name)
    compile(src,name,'exec')
    return src


def transform_book(src):
    src=transform_facets(src)
    compile(src,'book_library_v112_bot.py','exec')
    return src


def transform_group(src):
    """Optional no-match feedback for ordinary text in authorized book-only groups."""
    name='group_books_only_v116.py'
    mark='# V11.8.6 optionally search unmatched ordinary text in designated groups.'
    if mark in src:
        if src.count(mark)!=1 or 'LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED' not in src:
            raise ValueError(name+': incomplete ordinary-text routing')
        return src
    old="""    try:
        if _is_book_match(text):
            _book_search(bot, m, text)
    except Exception:
        LOG.warning('V11.6 group catalog lookup unavailable', exc_info=True)
    return None
"""
    new="""    try:
        # V11.8.6 optionally search unmatched ordinary text in designated groups.
        # Existing auto-group-search, verified-adult, group allowlist, length,
        # and cooldown restrictions are still enforced above and in _book_search.
        all_text=os.getenv('LIBRARY_SEARCH_V1186_ALL_TEXT_ENABLED','false').lower() in (
            'true','1','yes','on')
        if all_text or _is_book_match(text):
            _book_search(bot, m, text)
    except Exception:
        LOG.warning('V11.6 group catalog lookup unavailable', exc_info=True)
    return None
"""
    src=replace_once(src,old,new,name)
    compile(src,name,'exec')
    return src


def transform_prior_installer(src):
    # Keep historical V11.8.3 idempotency tests valid after V11.8.6.
    name='PATCH_LIBRARY_SEARCH_UI_V1183.py'
    marker='# V11.8.6 supersedes V11.8.3 unified_search body.'
    if marker in src:
        if src.count(marker) != 1:
            raise ValueError(name+': duplicate compatibility guard')
        return src
    before='def transform_media(text):\n    if FLAG in text:\n'
    after=(
        'def transform_media(text):\n'
        '    # V11.8.6 supersedes V11.8.3 unified_search body.\n'
        "    if '# V11.8.6 user-visible search progress and zero-results feedback.' in text:\n"
        "        if (text.count('# V11.8.6 user-visible search progress and zero-results feedback.') != 1\n"
        "                or 'status_message=status' not in text or 'register_private_handlers(bot)' not in text):\n"
        "            raise ValueError('V11.8.6 media integration incomplete or duplicated')\n"
        '        return text\n'
        '    if FLAG in text:\n')
    src=replace_once(src,before,after,name)
    compile(src,name,'exec')
    return src


def generate(root):
    helper=root/'library_language_picker_v1185.py'
    if not helper.is_file():
        raise FileNotFoundError('Missing bundled library_language_picker_v1185.py; extract all files.')
    compile(helper.read_text(encoding='utf-8'),'library_language_picker_v1185.py','exec')
    mapping={
      'library_search_ui_v1183.py':transform_ui,
      'book_library_v112_bot.py':transform_book,
      'library_media_v117_bot.py':transform_media,
      'PATCH_LIBRARY_SEARCH_UI_V1183.py':transform_prior_installer,
      'group_books_only_v116.py':transform_group,
    }
    changes={}
    for name,fn in mapping.items():
        path=root/name
        if not path.is_file(): raise FileNotFoundError(f'Missing {name}; install V11.8.3 first.')
        old=path.read_text(encoding='utf-8')
        new=fn(old)
        if old!=new: changes[name]=(old,new)
    return changes


def install(root,*,apply):
    changes=generate(root)
    if not changes:
        print('V11.8.6 already installed. No files changed.')
        return
    if not apply:
        for name,(old,new) in changes.items():
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                                              fromfile=name+':current',tofile=name+':planned')))
        print('CHECK OK. No files changed.')
        return
    backup=root/('V1186_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir()
    try:
        for name in changes: shutil.copy2(root/name,backup/name)
        for name,(_,new) in changes.items():
            descriptor,tmp=tempfile.mkstemp(prefix='.v1186_',suffix='.tmp',dir=root)
            try:
                with os.fdopen(descriptor,'w',encoding='utf-8',newline='') as fp:fp.write(new)
                os.replace(tmp,root/name)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
    except Exception:
        for name in changes:
            if (backup/name).is_file():shutil.copy2(backup/name,root/name)
        raise
    print('V11.8.6 installed. Previous source backed up at:',backup)
    print('Modified four library/group modules and the V11.8.3 installer guard. No Supabase migrations.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    install(Path(__file__).resolve().parent,apply=args.apply)

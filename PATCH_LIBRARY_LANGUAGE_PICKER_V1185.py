"""Safe V11.8.5 UI-only language-picker patch for an installed V11.8.3 bot.

Edits only library_search_ui_v1183.py and book_library_v112_bot.py;
backs up originals, checks anchors, and is safe to rerun.
"""
from __future__ import annotations
import argparse
import difflib
import json
import shutil
from datetime import datetime
from pathlib import Path

MARK_SEARCH = '# V11.8.5 paired language selector.'
MARK_FACETS = '# V11.8.5 paired private-language menu.'


def replace_once(source, old, new, filename):
    count = source.count(old)
    if count != 1:
        raise ValueError(f'{filename}: expected exactly one anchor, found {count}: {old[:100]!r}')
    return source.replace(old,new,1)


def apply_result_list(source, name):
    """Add Tamil/English selection result screens without altering delivery paths."""
    config = Path(__file__).resolve().with_name('V1185_LANGUAGE_RESULTS_CHANGES.json')
    if not config.is_file():
        raise FileNotFoundError(f'Missing language results fixture: {config.name}')
    pairs = json.loads(config.read_text(encoding='utf-8'))[name]
    for old, new in pairs:
        if new in source:
            continue
        source = replace_once(source, old, new, name)
    compile(source, name, 'exec')
    return source


def transform_search(source):
    name = 'library_search_ui_v1183.py'
    if MARK_SEARCH in source:
        if source.count(MARK_SEARCH) != 1 or 'language_counts' not in source:
            raise ValueError(name+': partial/duplicate language UI installation')
        return apply_result_list(source,name)
    old = '''def _options(items, key):
    values = {}
    for item in items:
        val = _value(item, key)
        values[val] = values.get(val, 0) + 1
    return sorted(values.items(), key=lambda x: x[0].casefold())[:30]
'''
    new = '''def _options(items, key):
    values = {}
    for item in items:
        val = _value(item, key)
        values[val] = values.get(val, 0) + 1
    # V11.8.5 paired language selector.
    if key == 'language':
        from library_language_picker_v1185 import language_counts
        return language_counts(values.items())
    return sorted(values.items(), key=lambda x: x[0].casefold())[:30]
'''
    source=replace_once(source,old,new,name)
    old='''        all_label = '⭐ Relevance' if mode == 'sort' else f'🌍 All {mode.replace("_", " ")}s'
        kb.add(_button(all_label, f'{_PREFIX}{token}:x'))
        for code, label in choices:
            kb.add(_button(label, f'{_PREFIX}{token}:v:{code}'))
        kb.add(_button('⬅️ Back to results', f'{_PREFIX}{token}:b'))
        text = s['heading'].split('\\n', 1)[0] + '\\n' + title + ' — choose an option'
'''
    new='''        all_label = '⭐ Relevance' if mode == 'sort' else f'🌍 All {mode.replace("_", " ")}s'
        kb.add(_button(all_label, f'{_PREFIX}{token}:x'))
        if mode == 'language':
            # Two buttons per row, just like the requested Telegram selector.
            for i in range(0, len(choices), 2):
                kb.add(*[_button(label, f'{_PREFIX}{token}:v:{code}')
                         for code, label in choices[i:i+2]])
            kb.add(_button('↩️ Back to Files', f'{_PREFIX}{token}:b'))
        else:
            for code, label in choices:
                kb.add(_button(label, f'{_PREFIX}{token}:v:{code}'))
            kb.add(_button('⬅️ Back to results', f'{_PREFIX}{token}:b'))
        text = s['heading'].split('\\n', 1)[0] + ('\\n🌐 SELECT LANGUAGE — choose an option\\n'
              'Counts show indexed files in this search. (0) means unavailable.'
              if mode == 'language' else '\\n' + title + ' — choose an option')
'''
    source=replace_once(source,old,new,name)
    compile(source,name,'exec')
    return apply_result_list(source,name)


def transform_facets(source):
    name='book_library_v112_bot.py'
    if MARK_FACETS in source:
        if source.count(MARK_FACETS) != 1 or 'language_counts' not in source:
            raise ValueError(name+': partial/duplicate language UI installation')
        return apply_result_list(source,name)
    old='''def _send_facets(bot, chat_id, kind):
    try:
        values = facets(kind)
        if not values:
            bot.send_message(chat_id,'📚 No entries yet.'); return
        kb = _keyboard()
        for item in values[:30]:
            name = str(item.get('value') or '').strip()
            if not name:
                continue
            context = {'kind':'browse','title':f'📚 {kind.title()}: {_short(name,70)}',kind:name}
            token = _save_session(chat_id,context)
            kb.add(_button(f'{_short(name,35)} ({int(item.get("book_count") or 0)})',
                           callback_data=f'lib2:filter:{token}'))
        bot.send_message(chat_id,f'📚 Choose a {kind}:',reply_markup=kb)
    except Exception:
        log.exception('V11.2 list facets failed')
        bot.send_message(chat_id, '⚠️ Filters currently unavailable.')
'''
    new='''def _send_facets(bot, chat_id, kind):
    try:
        values = facets(kind)
        # V11.8.5 paired private-language menu.
        if kind == 'language':
            from library_language_picker_v1185 import language_counts
            choices = language_counts((v.get('value'),v.get('book_count',0)) for v in values)
            kb = _keyboard()
            buttons = []
            for name,count in choices:
                context = {'kind':'browse','title':f'🌐 Language: {_short(name,70)}',kind:name}
                token = _save_session(chat_id,context,owner=int(chat_id))
                buttons.append(_button(f'{_short(name,28)} ({count})',
                                       callback_data=f'lib2:filter:{token}'))
            for i in range(0,len(buttons),2):
                kb.row(*buttons[i:i+2])
            kb.add(_button('↩️ Back to Files',callback_data='lib2:browse'))
            bot.send_message(chat_id,'🌐 SELECT LANGUAGE\\n'
                'Choose a language. Counts include indexed Book Library PDFs only; '
                'a (0) means no matching books there.',reply_markup=kb)
            return
        if not values:
            bot.send_message(chat_id,'📚 No entries yet.'); return
        kb = _keyboard()
        for item in values[:30]:
            name = str(item.get('value') or '').strip()
            if not name:
                continue
            context = {'kind':'browse','title':f'📚 {kind.title()}: {_short(name,70)}',kind:name}
            token = _save_session(chat_id,context)
            kb.add(_button(f'{_short(name,35)} ({int(item.get("book_count") or 0)})',
                           callback_data=f'lib2:filter:{token}'))
        bot.send_message(chat_id,f'📚 Choose a {kind}:',reply_markup=kb)
    except Exception:
        log.exception('V11.2 list facets failed')
        bot.send_message(chat_id, '⚠️ Filters currently unavailable.')
'''
    source=replace_once(source,old,new,name)
    compile(source,name,'exec')
    return apply_result_list(source,name)


def install(root:Path, *, apply:bool):
    helper=root/'library_language_picker_v1185.py'
    if not helper.is_file():
        raise FileNotFoundError('Extract library_language_picker_v1185.py first.')
    compile(helper.read_text(encoding='utf-8'),str(helper),'exec')
    transformations={ 'library_search_ui_v1183.py':transform_search,
                      'book_library_v112_bot.py':transform_facets }
    changes={}
    for name,func in transformations.items():
        path=root/name
        if not path.is_file(): raise FileNotFoundError(name+' not found; requires V11.8.3')
        old=path.read_text(encoding='utf-8')
        new=func(old)
        if new != old: changes[name]=(old,new)
    if not changes:
        print('V11.8.5 already installed; no changes needed.')
        return
    if not apply:
        for name,(old,new) in changes.items():
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),
                  fromfile=name+':current',tofile=name+':planned')))
        print('CHECK OK. No files changed.')
        return
    backup=root/('V1185_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=False,exist_ok=False)
    try:
        for name in changes: shutil.copy2(root/name,backup/name)
        for name,(_,new) in changes.items():
            tmp=root/(name+'.v1185.tmp')
            try:
                tmp.write_text(new,encoding='utf-8',newline='')
                tmp.replace(root/name)
            finally:
                tmp.unlink(missing_ok=True)
    except Exception:
        for name in changes:
            if (backup/name).exists():shutil.copy2(backup/name,root/name)
        raise
    print('V11.8.5 installed. Backup:',backup)
    print('Only the two language-menu modules were modified.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true')
    group.add_argument('--apply',action='store_true')
    arguments=parser.parse_args()
    install(Path(__file__).resolve().parent,apply=arguments.apply)

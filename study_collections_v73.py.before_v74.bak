"""V7.3 — Private collections for existing saved AI Study Notes.

No AI calls, provider changes, note mutations, extra dependencies, or AI quota use.
Every private message/callback uses the Telegram *sender* ID; every note link
requires a fresh server-side ownership check. All DB operations are user-scoped.
"""
from __future__ import annotations

import re

COLLECTIONS = 'ai_study_collections_v73'
ITEMS = 'ai_study_collection_notes_v73'
MENU = '📁 My Collections'
MAX_COLLECTIONS = 30
MAX_NOTES_PER_COLLECTION = 100
PAGE_SIZE = 8
MAX_PAGE = 12
MAX_NAME = 60
MAX_ID = 10**18 - 1
CB = re.compile(r'^v73:(list|c|p|a|r|x|y|l):([1-9][0-9]{0,17}|0)(?::([1-9][0-9]{0,17}|0))?$')


def _id(x):
    if isinstance(x, bool):
        raise ValueError('Invalid ID')
    try:
        result = int(x)
    except (TypeError, ValueError, OverflowError):
        raise ValueError('Invalid ID') from None
    if not 1 <= result <= MAX_ID:
        raise ValueError('Invalid ID')
    return result


def _rows(result):
    values = getattr(result, 'data', None)
    if not isinstance(values, list):
        raise RuntimeError('Unexpected database result')
    return values


def _private(obj):
    message = getattr(obj, 'message', obj)
    chat = getattr(message, 'chat', None)
    sender = getattr(obj, 'from_user', None)
    uid = getattr(sender, 'id', None)
    return (type(uid) is int and uid > 0 and getattr(chat, 'type', None) == 'private'
            and getattr(chat, 'id', None) == uid)


def clean_name(text):
    # Avoid multiline or invisible-control rendering, keep multilingual names.
    if not isinstance(text, str):
        raise ValueError('Collection name required')
    result = ' '.join(text.split()).strip()
    if not 1 <= len(result) <= MAX_NAME or any(ord(ch) < 32 or ord(ch) == 127 for ch in result):
        raise ValueError('Collection name must be 1–60 characters')
    return result


def list_collections(db, uid):
    uid = _id(uid)
    return _rows(db.table(COLLECTIONS).select('id,name').eq('user_id', uid)
                 .order('id', desc=True).limit(MAX_COLLECTIONS+1).execute())


def get_collection(db, uid, collection_id):
    uid, cid = _id(uid), _id(collection_id)
    data = _rows(db.table(COLLECTIONS).select('id,name').eq('user_id', uid)
                 .eq('id', cid).limit(1).execute())
    return data[0] if data else None


def create_collection(db, uid, name):
    uid, name = _id(uid), clean_name(name)
    if len(list_collections(db, uid)) >= MAX_COLLECTIONS:
        raise ValueError('Maximum 30 collections reached')
    result = _rows(db.table(COLLECTIONS).insert({'user_id':uid, 'name':name}).execute())
    if not result:
        raise RuntimeError('Collection could not be created')
    return result[0]


def rename_collection(db, uid, collection_id, name):
    uid, cid, name = _id(uid), _id(collection_id), clean_name(name)
    if not get_collection(db, uid, cid):
        raise ValueError('Collection not found')
    return _rows(db.table(COLLECTIONS).update({'name':name})
                 .eq('user_id', uid).eq('id',cid).execute())


def delete_collection(db, uid, collection_id):
    uid, cid = _id(uid), _id(collection_id)
    if not get_collection(db,uid,cid):
        raise ValueError('Collection not found')
    # FK ON DELETE CASCADE removes membership rows. Does NOT delete actual notes.
    db.table(COLLECTIONS).delete().eq('user_id',uid).eq('id',cid).execute()


def list_memberships(db, uid, cid, page=0):
    uid,cid = _id(uid), _id(cid)
    if not isinstance(page,int) or not 0 <= page <= MAX_PAGE:
        raise ValueError('Invalid page')
    if not get_collection(db, uid, cid):
        raise ValueError('Collection not found')
    start=page*PAGE_SIZE
    data=_rows(db.table(ITEMS).select('note_id').eq('user_id', uid)
               .eq('collection_id',cid).order('note_id', desc=True)
               .range(start, start+PAGE_SIZE).execute())
    return data[:PAGE_SIZE], len(data)>PAGE_SIZE


def add_note(db, uid, collection_id, note_id, load_note):
    uid,cid,nid = _id(uid),_id(collection_id),_id(note_id)
    if not get_collection(db,uid,cid):
        raise ValueError('Collection not found')
    if not load_note(db,uid,nid):
        raise ValueError('Saved AI note not found')
    # The database PK prevents double-insertion. Fetch only 101 rows at most.
    existing=_rows(db.table(ITEMS).select('note_id').eq('user_id',uid)
                   .eq('collection_id',cid).limit(MAX_NOTES_PER_COLLECTION+1).execute())
    if any(_id(r.get('note_id'))==nid for r in existing):
        return False
    if len(existing)>=MAX_NOTES_PER_COLLECTION:
        raise ValueError('This collection has reached 100 notes')
    db.table(ITEMS).insert({'user_id':uid, 'collection_id':cid,'note_id':nid}).execute()
    return True


def remove_note(db,uid,cid,nid,load_note):
    uid,cid,nid=_id(uid),_id(cid),_id(nid)
    if not get_collection(db,uid,cid) or not load_note(db,uid,nid):
        raise ValueError('Collection or note not found')
    db.table(ITEMS).delete().eq('user_id',uid).eq('collection_id',cid).eq('note_id',nid).execute()


def note_collection_keyboard(types, note_id):
    try:
        nid=_id(note_id)
    except ValueError:
        return None
    kb=types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton('📁 Add to Collection',callback_data=f'v73:p:{nid}'))
    return kb


def _list_ui(bot,db,types,uid,chat_id):
    rows=list_collections(db,uid)
    kb=types.InlineKeyboardMarkup(row_width=1)
    for row in rows[:MAX_COLLECTIONS]:
        cid=_id(row['id'])
        name=' '.join(str(row.get('name') or 'Untitled').split())[:45]
        kb.add(types.InlineKeyboardButton('📁 '+name,callback_data=f'v73:c:{cid}'))
    inventory = '\n'.join(f'#{_id(row["id"])} — '+
                          ' '.join(str(row.get('name') or 'Untitled').split())[:55]
                          for row in rows[:MAX_COLLECTIONS])
    message=('📁 My Study Collections\n\n'
             'Create: /collectioncreate Biology Revision\n'
             'Rename: /collectionrename 12 New Name\n'
             'Delete: /collectiondelete 12 (asks confirmation)\n'
             'Add a note: open it from /studylibrary and tap 📁 Add to Collection.\n'
             f'Collections: {min(len(rows),MAX_COLLECTIONS)}/{MAX_COLLECTIONS}\n\n'
             + inventory)
    if not rows:
        message+='\n\n📭 No collections yet.'
    bot.send_message(chat_id,message,reply_markup=kb if rows else None)


def _show_collection(bot,db,types,uid,chat_id,cid,load_note,page=0):
    collection=get_collection(db,uid,cid)
    if not collection:
        bot.send_message(chat_id,'⚠️ Collection not found.')
        return
    memberships,more=list_memberships(db,uid,cid,page)
    kb=types.InlineKeyboardMarkup(row_width=1)
    shown=0
    for membership in memberships:
        nid=_id(membership['note_id'])
        # Recheck user ownership and AI Study title every time, even for stale links.
        note=load_note(db,uid,nid)
        if not note:
            continue
        shown+=1
        title=' '.join(str(note.get('title') or '').split())[:37]
        kb.add(types.InlineKeyboardButton('📖 '+title,callback_data=f'v66:n:{nid}'))
        kb.add(types.InlineKeyboardButton('➖ Remove this note',callback_data=f'v73:r:{cid}:{nid}'))
    nav=[]
    if page:
        nav.append(types.InlineKeyboardButton('⬅️ Newer',callback_data=f'v73:l:{cid}:{page-1}'))
    if more and page < MAX_PAGE:
        nav.append(types.InlineKeyboardButton('Older ➡️',callback_data=f'v73:l:{cid}:{page+1}'))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton('🗑 Delete Collection',callback_data=f'v73:x:{cid}'))
    kb.add(types.InlineKeyboardButton('📁 All Collections',callback_data='v73:list:0'))
    name=' '.join(str(collection['name']).split())[:60]
    bot.send_message(chat_id,f'📁 {name} • Page {page+1}\n'
                     +(f'{shown} saved AI note(s) on this page.' if shown else '📭 No available notes on this page.'),
                     reply_markup=kb)


def register_study_collections_v73_handlers(bot, db, load_note, types):
    """Register once, before broad wildcard handlers, next to V7.2 registration."""
    @bot.message_handler(commands=['collections'])
    @bot.message_handler(func=lambda m: getattr(m,'text',None)==MENU)
    def v73_collections(message):
        if not _private(message):
            bot.send_message(message.chat.id,'🔒 Collections work only in your private bot chat.')
            return
        try:
            _list_ui(bot,db,types,message.from_user.id,message.chat.id)
        except Exception as exc:
            print('V7.3 list failed:',type(exc).__name__)
            bot.send_message(message.chat.id,'⚠️ Collections unavailable. Check SQL_V7_3_COLLECTIONS.sql in Supabase.')

    @bot.message_handler(commands=['collectioncreate'])
    def v73_create(message):
        if not _private(message):
            bot.send_message(message.chat.id,'🔒 Use your private chat.')
            return
        name=(getattr(message,'text','') or '').partition(' ')[2]
        try:
            row=create_collection(db,message.from_user.id,name)
            bot.send_message(message.chat.id,f'✅ Collection created: {row["name"]}\nOpen /collections to view.')
        except ValueError as exc:
            bot.send_message(message.chat.id,f'⚠️ {exc}\nUsage: /collectioncreate Biology Revision')
        except Exception as exc:
            print('V7.3 create failed:',type(exc).__name__)
            bot.send_message(message.chat.id,'⚠️ Could not create collection. It may already exist or SQL has not been run.')

    @bot.message_handler(commands=['collectionrename'])
    def v73_rename(message):
        if not _private(message):
            bot.send_message(message.chat.id,'🔒 Use your private chat.')
            return
        payload=(getattr(message,'text','') or '').partition(' ')[2].strip()
        cid, separator, new_name=payload.partition(' ')
        try:
            if not separator:
                raise ValueError('Provide collection ID and new name')
            rename_collection(db,message.from_user.id,_id(cid),new_name)
            bot.send_message(message.chat.id,'✅ Collection renamed. Use /collections.')
        except ValueError as exc:
            bot.send_message(message.chat.id,f'⚠️ {exc}\nUsage: /collectionrename 12 Biology Notes')
        except Exception as exc:
            print('V7.3 rename failed:',type(exc).__name__)
            bot.send_message(message.chat.id,'⚠️ Rename failed. Name may already be in use.')

    @bot.message_handler(commands=['collectiondelete'])
    def v73_delete(message):
        if not _private(message):
            bot.send_message(message.chat.id,'🔒 Use your private chat.')
            return
        try:
            cid=_id((getattr(message,'text','') or '').partition(' ')[2].strip())
            row=get_collection(db,message.from_user.id,cid)
            if not row:
                raise ValueError('Collection not found')
            kb=types.InlineKeyboardMarkup(row_width=2)
            kb.add(types.InlineKeyboardButton('🗑 Confirm Delete',callback_data=f'v73:y:{cid}'),
                   types.InlineKeyboardButton('❌ Cancel',callback_data='v73:list:0'))
            bot.send_message(message.chat.id,
                             f'⚠️ Delete collection “{row["name"]}”? Notes themselves will NOT be deleted.',
                             reply_markup=kb)
        except ValueError:
            bot.send_message(message.chat.id,'Usage: /collectiondelete 12 (get IDs from /collections)')
        except Exception as exc:
            print('V7.3 delete prompt failed:',type(exc).__name__)
            bot.send_message(message.chat.id,'⚠️ Collection lookup unavailable.')

    @bot.callback_query_handler(func=lambda call: bool(CB.fullmatch(str(getattr(call,'data','') or ''))))
    def v73_callback(call):
        if not _private(call):
            bot.answer_callback_query(call.id,'Open your private bot chat.',show_alert=True)
            return
        parsed=CB.fullmatch(str(getattr(call,'data','') or ''))
        if parsed is None:
            return
        action, first, second=parsed.groups()
        uid=call.from_user.id
        chat_id=call.message.chat.id
        try:
            if action=='list' and first=='0' and second is None:
                bot.answer_callback_query(call.id)
                _list_ui(bot,db,types,uid,chat_id)
                return
            if action=='p' and second is None:
                nid=_id(first)
                if not load_note(db,uid,nid):
                    raise ValueError('Saved AI note not found')
                collections=list_collections(db,uid)
                kb=types.InlineKeyboardMarkup(row_width=1)
                for collection in collections[:MAX_COLLECTIONS]:
                    cid=_id(collection['id'])
                    name=' '.join(str(collection['name']).split())[:42]
                    kb.add(types.InlineKeyboardButton('➕ '+name,
                           callback_data=f'v73:a:{cid}:{nid}'))
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id,'📁 Choose a collection for your AI note:' if collections else
                                 '📭 No collections. Create one with /collectioncreate Biology Revision.',
                                 reply_markup=kb if collections else None)
                return
            cid=_id(first)
            if action=='c' and second is None:
                bot.answer_callback_query(call.id)
                _show_collection(bot,db,types,uid,chat_id,cid,load_note)
                return
            if action=='l' and second is not None:
                page=int(second)
                bot.answer_callback_query(call.id)
                _show_collection(bot,db,types,uid,chat_id,cid,load_note,page)
                return
            if action=='a' and second is not None:
                created=add_note(db,uid,cid,_id(second),load_note)
                bot.answer_callback_query(call.id,'Added to collection.' if created else 'Already in collection.')
                return
            if action=='r' and second is not None:
                remove_note(db,uid,cid,_id(second),load_note)
                bot.answer_callback_query(call.id,'Removed from collection.')
                _show_collection(bot,db,types,uid,chat_id,cid,load_note)
                return
            if action=='x' and second is None:
                collection=get_collection(db,uid,cid)
                if not collection:
                    raise ValueError('Collection unavailable')
                kb=types.InlineKeyboardMarkup(row_width=2)
                kb.add(types.InlineKeyboardButton('🗑 Confirm Delete',callback_data=f'v73:y:{cid}'),
                       types.InlineKeyboardButton('❌ Cancel',callback_data=f'v73:c:{cid}'))
                bot.answer_callback_query(call.id)
                bot.send_message(chat_id,f'⚠️ Delete collection “{collection["name"]}”? '
                                 'Saved AI notes will remain untouched.',reply_markup=kb)
                return
            if action=='y' and second is None:
                delete_collection(db,uid,cid)
                bot.answer_callback_query(call.id,'Collection deleted.')
                _list_ui(bot,db,types,uid,chat_id)
                return
            bot.answer_callback_query(call.id,'Invalid action.',show_alert=True)
        except ValueError as exc:
            bot.answer_callback_query(call.id,str(exc)[:180],show_alert=True)
        except Exception as exc:
            print('V7.3 collection action failed:',type(exc).__name__)
            bot.answer_callback_query(call.id,'Collections temporarily unavailable.',show_alert=True)
    return True

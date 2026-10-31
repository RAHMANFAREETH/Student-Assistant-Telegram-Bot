"""V11.4 optional Book Library session privacy and menu cleanup helpers.

Only addresses Book Library workflows, not arbitrary historical handlers.
Group search results can be routed privately; old public URLs can't be revoked.
"""
from __future__ import annotations
import logging
import os
from types import SimpleNamespace

log = logging.getLogger(__name__)


def on(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('true', '1', 'yes', 'on')


def private_group_results(message):
    return (on('BOOK_LIBRARY_PRIVATE_GROUP_RESULTS', False)
            and getattr(getattr(message, 'chat', None), 'type', None) in ('group', 'supergroup'))


def _delete_group_command(bot, message):
    if not on('BOOK_LIBRARY_DELETE_GROUP_COMMANDS', False):
        return
    # Do not automatically delete everyday group conversation messages.
    text = str(getattr(message, 'text', '') or '')
    if not text.startswith('/'):
        return
    try:
        bot.delete_message(int(message.chat.id), int(message.message_id))
    except Exception:
        log.debug('Cannot delete group book command (permission/age restriction)', exc_info=True)


def private_target(bot, message):
    """Return user's private chat copy of message, or None if they haven't started the bot.

    The source Telegram from_user.id comes from the update, not user-supplied text.
    """
    if not private_group_results(message):
        return message
    uid = int(message.from_user.id)
    try:
        bot.send_chat_action(uid, 'typing')
    except Exception:
        try:
            import book_library_bot as lib
            uname = lib._bot_username(bot)
            bot.send_message(message.chat.id,
                f'🔐 Please start @{uname} in private, then repeat your book search. '
                'Your results will not appear in this group.')
        except Exception:
            log.warning('Could not send a private-start notice')
        return None
    _delete_group_command(bot, message)
    return SimpleNamespace(chat=SimpleNamespace(id=uid, type='private'),
                           from_user=message.from_user,
                           text=getattr(message, 'text', None),
                           caption=getattr(message, 'caption', None),
                           message_id=getattr(message, 'message_id', None))


def route_group(bot, message, fn):
    """For public /book or /booklatest from groups, run fn(private_chat_id).

    Returns True when private routing handled this update; False when opt-in is off.
    """
    if not private_group_results(message):
        return False
    private = private_target(bot, message)
    if private is None:
        return True
    try:
        fn(int(private.chat.id))
    except Exception:
        log.exception('Private group-book delivery failed')
        # Avoid accidentally posting private book results into the group on failure.
        try:
            bot.send_message(private.chat.id, '⚠️ Could not display your books privately. Please open the bot and retry.')
        except Exception:
            pass
    return True


def cleanup_menu(bot, callback):
    """Best-effort delete BOT's inline-button message after authorized selection.

    Deletion is only attempted for an eligible callback. Never delete another
    user's messages. When Telegram denies deletion, remove buttons instead.
    """
    if not on('BOOK_LIBRARY_AUTODELETE_MENU', False):
        return False
    message = getattr(callback, 'message', None)
    chat = getattr(message, 'chat', None)
    if chat is None or getattr(message, 'message_id', None) is None:
        return False
    # Only private-chat menus. Group commands use private routing, not shared menus.
    if chat.type != 'private' or int(chat.id) != int(callback.from_user.id):
        return False
    try:
        bot.delete_message(chat.id, message.message_id)
        return True
    except Exception:
        try:
            bot.edit_message_reply_markup(chat_id=chat.id, message_id=message.message_id,
                                          reply_markup=None)
            return True
        except Exception:
            log.debug('Cannot remove old book menu', exc_info=True)
    return False

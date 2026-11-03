"""Patch compatible V7.11+ PDF Tools in-place while retaining earlier modules."""
from __future__ import annotations
import ast

MARKER = 'from scan_document_v716 import ('


def once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise ValueError(f'Cannot safely patch PDF Tools: {label} anchor occurred {count} times (expected 1).')
    return source.replace(old, new, 1)


def patch_pdf_tools(source: str, fragment: str) -> str:
    if MARKER in source:
        return source
    if ('def register_pdf_handlers(bot, show_main_menu):' not in source or
        'from telebot.handler_backends import ContinueHandling' not in source or
        'from navigation import should_yield_to_navigation' not in source or
        'def _mode_keyboard(*buttons):' not in source):
        raise ValueError('Unsupported PDF Tools layout. Send your current pdf_tools.py for a compatible V7.16 patch.')
    source = once(source,
        'from navigation import should_yield_to_navigation\n',
        '''from scan_document_v716 import (
    SCAN_BUTTON, SCAN_MODE, SCAN_PREVIEW, SCAN_ADJUST, SCAN_RESCAN,
    SCAN_ORIGINAL, SCAN_SAVE_IMAGE, SCAN_SAVE_PDF, SCAN_CHANGE,
    SCAN_CANCEL, SUPPORTED_EXTENSIONS as SCAN_EXTENSIONS,
    MAX_SOURCE_BYTES as SCAN_MAX_SOURCE_BYTES, ScanError,
    read_photo as scan_read_photo, detect_corners, parse_corners,
    rectify, create_scan, create_scan_pdf,
)

from navigation import should_yield_to_navigation
''', 'scan import')
    if 'from photo_crop_v715 import (' in source:
        menu = '        types.KeyboardButton(PHOTO_CROP_BUTTON),\n'
        help_line = '            f"{PHOTO_CROP_BUTTON}\\n"\n'
    else:
        menu = '        types.KeyboardButton("🖼 Images → PDF"),\n'
        help_line = '            "🖼 Images → PDF\\n"\n'
    source = once(source, menu, menu + '        types.KeyboardButton(SCAN_BUTTON),\n', 'scanner button')
    source = once(source, help_line, help_line + '            f"{SCAN_BUTTON}\\n"\n', 'scanner help')
    source = once(source,
        'def _mode_keyboard(*buttons):\n',
        '''def _scanner_keyboard():
    return _mode_keyboard(
        [SCAN_PREVIEW, SCAN_ADJUST],
        [SCAN_RESCAN, SCAN_ORIGINAL],
        [SCAN_SAVE_IMAGE, SCAN_SAVE_PDF],
        [SCAN_CHANGE, SCAN_CANCEL],
        ["🔙 PDF Tools", "🏠 Main Menu"],
    )


def _mode_keyboard(*buttons):
''', 'scanner keyboard')
    anchor = 'def register_pdf_handlers(bot, show_main_menu):\n'
    source = once(source, anchor, anchor + '\n' + fragment + '\n', 'scanner handler registration')
    ast.parse(source, 'pdf_tools.py')
    return source

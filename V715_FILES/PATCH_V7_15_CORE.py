"""Patch the V7.14 PDF Tools module for an independent photo/image crop tool."""
from __future__ import annotations
import ast

MARKER = 'from photo_crop_v715 import ('


def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise ValueError(f"Unsupported PDF Tools layout: {label} matched {n} times (expected 1).")
    return src.replace(old, new, 1)


def patch_pdf_tools(src: str, fragment: str) -> str:
    if MARKER in src:
        return src
    if 'from image_crop_v714 import (' not in src or 'def register_pdf_handlers(bot, show_main_menu):' not in src:
        raise ValueError("V7.14 Auto Crop must be installed before Photo/Image Crop V7.15.")
    src = replace_once(src,
        'from navigation import should_yield_to_navigation\n',
        'from photo_crop_v715 import (\n'
        '    PHOTO_CROP_BUTTON, PHOTO_CROP_MODE, PREVIEW_CROP_BUTTON,\n'
        '    SAVE_CROP_BUTTON, CUSTOM_CROP_BUTTON, CHANGE_PHOTO_BUTTON,\n'
        '    CANCEL_CROP_BUTTON, AUTO_PAGE_BUTTON, ORIGINAL_BUTTON, PRESETS,\n'
        '    MAX_SOURCE_BYTES, VALID_EXTENSIONS, PhotoCropError,\n'
        '    parse_custom_edges, read_image, create_cropped_image,\n'
        ')\n\n'
        'from navigation import should_yield_to_navigation\n',
        "photo crop import")
    src = replace_once(src,
        '        types.KeyboardButton("🖼 Images → PDF"),\n',
        '        types.KeyboardButton("🖼 Images → PDF"),\n'
        '        types.KeyboardButton(PHOTO_CROP_BUTTON),\n',
        "photo crop menu button")
    src = replace_once(src,
        '            "🖼 Images → PDF\\n"\n',
        '            "🖼 Images → PDF\\n"\n'
        '            f"{PHOTO_CROP_BUTTON}\\n"\n',
        "photo crop help description")
    src = replace_once(src,
        'def _image_tools_keyboard():\n',
        '''def _photo_crop_keyboard():
    return _mode_keyboard(
        ["⬜ Square 1:1", "📷 Portrait 4:5"],
        ["📱 Story 9:16", "🖼 Landscape 16:9"],
        [AUTO_PAGE_BUTTON, CUSTOM_CROP_BUTTON],
        [ORIGINAL_BUTTON, PREVIEW_CROP_BUTTON],
        [SAVE_CROP_BUTTON, CHANGE_PHOTO_BUTTON],
        ["🔙 PDF Tools", CANCEL_CROP_BUTTON],
        "🏠 Main Menu",
    )


def _image_tools_keyboard():
''',
        "photo crop keyboard")
    anchor = 'def register_pdf_handlers(bot, show_main_menu):\n'
    src = replace_once(src, anchor, anchor + '\n' + fragment + '\n', "crop handler registration")
    ast.parse(src)
    return src

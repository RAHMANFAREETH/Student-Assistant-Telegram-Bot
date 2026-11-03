"""Read-only local/Git V7.16 Scanner deployment check; never prints credentials."""
from __future__ import annotations
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
KEYS = (
    ('Scanner module import', 'from scan_document_v716 import ('),
    ('Scan Document menu button', 'types.KeyboardButton(SCAN_BUTTON)'),
    ('/scan command handler', 'commands=["scan"]'),
    ('PDF handler registration', 'def register_pdf_handlers(bot, show_main_menu)'),
)

def source_at(ref):
    if ref == 'working tree':
        file = ROOT / 'pdf_tools.py'
        return (file.read_text(encoding='utf-8-sig') if file.exists() else None)
    cmd = subprocess.run(['git', 'show', f'{ref}:pdf_tools.py'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return cmd.stdout if cmd.returncode == 0 else None

print('V7.16 scanner deployment diagnostic (read-only)')
print('scan_document_v716.py exists:', (ROOT/'scan_document_v716.py').is_file())
for ref in ('working tree', 'HEAD', 'origin/main'):
    src=source_at(ref)
    print('\n'+ref+':')
    if src is None:
        print('  Unavailable; no files changed')
        continue
    for label, needle in KEYS:
        print(' ', 'YES' if needle in src else 'NO ', label)
print('\nIf working tree=YES but HEAD/origin/main=NO, the scanner changes have not been committed/pushed.')
print('If all=YES but Telegram still lacks /scan, check Render deployment commit and startup logs.')

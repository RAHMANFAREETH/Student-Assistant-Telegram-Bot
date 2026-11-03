"""Download Noto fonts on the bot's own server. Not run for Telegram messages.

Use in Render build command AFTER pip installs dependencies:
    pip install -r requirements.txt && python INSTALL_TEXT_PDF_FONTS.py

No font binaries are included in the ChatGPT upgrade ZIP or committed to Git.
"""
from pathlib import Path
import os
import tempfile
from urllib.request import Request, urlopen

FONT_FILES = [
    ("NotoSans-Regular.ttf", "NotoSans"),
    ("NotoSansTamil-Regular.ttf", "NotoSansTamil"),
    ("NotoSansSinhala-Regular.ttf", "NotoSansSinhala"),
    ("NotoSansArabic-Regular.ttf", "NotoSansArabic"),
]
REPOSITORY = "https://raw.githubusercontent.com/googlefonts/noto-fonts/main/hinted/ttf"
MAX_BYTES = 5_000_000


def _valid_font(path):
    from fontTools.ttLib import TTFont
    try:
        font = TTFont(str(path), lazy=True)
        ok = bool(font["cmap"].getBestCmap())
        font.close()
        return ok
    except Exception:
        return False


def provision_font_files(target_dir=None):
    destination = Path(target_dir or os.environ.get("TEXT_PDF_FONT_DIR") or
                       (Path(__file__).resolve().parent / "pdf_fonts"))
    destination.mkdir(parents=True, exist_ok=True)
    for filename, family in FONT_FILES:
        final_path = destination / filename
        if final_path.exists() and _valid_font(final_path):
            print("Already installed:", filename)
            continue
        url = f"{REPOSITORY}/{family}/{filename}"
        print("Installing Unicode font:", filename)
        req = Request(url, headers={"User-Agent": "StudentAssistantBot/TextPDF/7.11"})
        with urlopen(req, timeout=25) as response:
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES or len(data) < 15_000:
            raise RuntimeError(f"Invalid font download size for {filename}")
        fd, temp_file = tempfile.mkstemp(prefix=".font_", suffix=".tmp", dir=destination)
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(data)
            temp_path = Path(temp_file)
            if not _valid_font(temp_path):
                raise RuntimeError(f"Invalid font file received for {filename}")
            os.replace(temp_path, final_path)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    print("Unicode PDF fonts ready in", destination)


if __name__ == "__main__":
    provision_font_files()

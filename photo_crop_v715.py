"""Private, in-memory Telegram photo crop helper for Student Assistant Bot V7.15.

No image is uploaded to any third-party service. The helper re-encodes the result,
which also strips metadata (including EXIF GPS tags). Pillow is already required.
"""
from __future__ import annotations

from io import BytesIO
import math
import re

from PIL import Image, ImageOps, UnidentifiedImageError

from image_crop_v714 import auto_crop_image

PHOTO_CROP_BUTTON = "✂️ Photo/Image Crop"
PHOTO_CROP_MODE = "photo_crop_v715"
PREVIEW_CROP_BUTTON = "👁 Preview Crop"
SAVE_CROP_BUTTON = "✅ Save Cropped Image"
CUSTOM_CROP_BUTTON = "📐 Custom Edges"
CHANGE_PHOTO_BUTTON = "🔄 Change Photo"
CANCEL_CROP_BUTTON = "❌ Cancel Crop"
AUTO_PAGE_BUTTON = "📄 Auto Page Crop"
ORIGINAL_BUTTON = "📐 Original (No Crop)"

PRESETS = {
    "⬜ Square 1:1": (1, 1),
    "📷 Portrait 4:5": (4, 5),
    "📱 Story 9:16": (9, 16),
    "🖼 Landscape 16:9": (16, 9),
}
SELECTIONS = frozenset(PRESETS) | {CUSTOM_CROP_BUTTON, AUTO_PAGE_BUTTON, ORIGINAL_BUTTON}
MAX_SOURCE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
MAX_FINAL_BYTES = 18 * 1024 * 1024
MAX_PREVIEW_SIZE = (960, 960)
VALID_EXTENSIONS = frozenset((".jpg", ".jpeg", ".png", ".webp"))


class PhotoCropError(ValueError):
    pass


def read_image(data: bytes) -> Image.Image:
    """Return a separate RGB/RGBA image, EXIF oriented, with limits enforced."""
    if not data or len(data) > MAX_SOURCE_BYTES:
        raise PhotoCropError("❌ Image must be under 12 MB.")
    try:
        with Image.open(BytesIO(data)) as source:
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                raise PhotoCropError("❌ Image too large to process safely (24 MP max).")
            if source.format not in {"PNG", "JPEG", "WEBP"}:
                raise PhotoCropError("❌ Send a JPG, PNG, or WEBP image.")
            corrected = ImageOps.exif_transpose(source)
            try:
                corrected.load()
                return corrected.convert("RGBA" if "A" in corrected.getbands() else "RGB")
            finally:
                if corrected is not source:
                    corrected.close()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        if isinstance(error, PhotoCropError):
            raise
        raise PhotoCropError("❌ Could not read this image. Try JPG or PNG.") from error


def parse_custom_edges(text: str) -> tuple[float, float, float, float]:
    """Accept four percentage edges: left top right bottom, e.g. 10 5 90 95."""
    fields = re.split(r"[\s,;]+", (text or "").strip())
    if len(fields) != 4:
        raise PhotoCropError("❌ Enter four percentages: LEFT TOP RIGHT BOTTOM\nExample: 10 10 90 90")
    try:
        coords = tuple(float(x) for x in fields)
    except ValueError as error:
        raise PhotoCropError("❌ Please enter numbers, e.g. 10 10 90 90") from error
    left, top, right, bottom = coords
    if not all(math.isfinite(v) and 0 <= v <= 100 for v in coords):
        raise PhotoCropError("❌ Each percentage must be between 0 and 100.")
    if right - left < 3 or bottom - top < 3:
        raise PhotoCropError("❌ Right and bottom must be greater than left and top by at least 3%.")
    return coords


def _crop_box(width: int, height: int, selection: str, edges=None):
    if selection == ORIGINAL_BUTTON:
        return (0, 0, width, height)
    if selection == CUSTOM_CROP_BUTTON:
        if edges is None:
            raise PhotoCropError("❌ Set custom edges first.")
        left, top, right, bottom = edges
        x0, y0 = int(width * left / 100), int(height * top / 100)
        x1, y1 = math.ceil(width * right / 100), math.ceil(height * bottom / 100)
        if x1 - x0 < 8 or y1 - y0 < 8:
            raise PhotoCropError("❌ Selected area is too small. Choose a larger crop.")
        return x0, y0, x1, y1
    if selection not in PRESETS:
        raise PhotoCropError("❌ Choose a crop option first.")
    ratio_w, ratio_h = PRESETS[selection]
    target_ratio = ratio_w / ratio_h
    if width / height > target_ratio:
        new_w, new_h = max(1, round(height * target_ratio)), height
    else:
        new_w, new_h = width, max(1, round(width / target_ratio))
    left = (width - new_w) // 2
    top = (height - new_h) // 2
    return (left, top, left + new_w, top + new_h)


def crop_image(image: Image.Image, selection: str, edges=None) -> Image.Image:
    if selection == AUTO_PAGE_BUTTON:
        return auto_crop_image(image)
    return image.crop(_crop_box(*image.size, selection, edges))


def create_cropped_image(data: bytes, selection: str, edges=None, preview=False) -> BytesIO:
    """Render selection to a seeked, independently owned file buffer."""
    with read_image(data) as image:
        with crop_image(image, selection, edges) as cropped:
            if preview:
                # Keep preview bounded and fast; never downscale the final download.
                work = cropped.copy()
                work.thumbnail(MAX_PREVIEW_SIZE, Image.Resampling.LANCZOS)
            else:
                work = cropped.copy()
            with work:
                if preview:
                    fmt = "JPEG"
                else:
                    # Preserve PNG format where user uploaded a PNG, including transparency.
                    fmt = "PNG" if data[:8] == b"\x89PNG\r\n\x1a\n" else "JPEG"
                if fmt == "JPEG" and work.mode != "RGB":
                    rgb = Image.new("RGB", work.size, (255, 255, 255))
                    if "A" in work.getbands():
                        rgb.paste(work, mask=work.getchannel("A"))
                    else:
                        rgb.paste(work)
                    encoded = rgb
                else:
                    encoded = work
                try:
                    buffer = BytesIO()
                    if fmt == "JPEG":
                        encoded.save(buffer, format="JPEG", quality=88, optimize=True)
                        buffer.name = "cropped_preview.jpg" if preview else "cropped_photo.jpg"
                    else:
                        encoded.save(buffer, format="PNG", optimize=True)
                        buffer.name = "cropped_photo.png"
                    if len(buffer.getvalue()) > MAX_FINAL_BYTES:
                        buffer.close()
                        raise PhotoCropError("❌ Output is too large. Try a smaller image.")
                    buffer.seek(0)
                    return buffer
                finally:
                    if encoded is not work:
                        encoded.close()

"""Optional, conservative document auto-crop for Images -> PDF.

Only Pillow is used. The algorithm handles a rectangular, mostly light page
surrounded by a contrasting desk/background. It does not promise perspective
correction or accurate detection for every image. If uncertain, keep the image.
"""
from __future__ import annotations

from statistics import median
from PIL import Image

CROP_MENU_BUTTON = "✂️ Crop Mode"
CROP_ORIGINAL_BUTTON = "📐 Original (Default)"
CROP_AUTO_BUTTON = "✂️ Auto Crop"
CROP_NAMES = {False: "Original", True: "Auto Crop"}


def selected_crop(state: dict) -> bool:
    return state.get("image_autocrop") is True


def _box_for_page(image: Image.Image):
    """Return conservative full-resolution (left, top, right, bottom), or None.

    Uses the four outer corners as background reference and looks for a large,
    low-saturation, bright rectangular paper region centered within the photo.
    Color/contrast or insufficient surrounding desk => do not crop.
    """
    w, h = image.size
    if w < 90 or h < 90:
        return None
    scale = min(1.0, 256.0 / max(w, h))
    sw, sh = max(1, round(w * scale)), max(1, round(h * scale))
    sample = image.convert("RGB")
    try:
        if (sw, sh) != sample.size:
            sample.thumbnail((sw, sh), Image.Resampling.BILINEAR)
        sw, sh = sample.size
        if sw < 50 or sh < 50:
            return None
        pix = sample.load()
        edge = max(2, min(7, min(sw, sh) // 20))
        corner_colors = []
        for x0, y0 in ((0, 0), (sw-edge, 0), (0, sh-edge), (sw-edge, sh-edge)):
            channels = [[], [], []]
            for y in range(y0, y0 + edge):
                for x in range(x0, x0 + edge):
                    rgb = pix[x, y]
                    for k in range(3):
                        channels[k].append(rgb[k])
            corner_colors.append(tuple(median(ch) for ch in channels))
        bg = tuple(median(c[k] for c in corner_colors) for k in range(3))
        # Nonuniform surroundings (table clutter, unusual lighting): leave alone.
        if max(sum(abs(c[k] - bg[k]) for k in range(3)) for c in corner_colors) > 125:
            return None
        bg_luma = (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2])
        # White background at the image corners: often an already cropped scan.
        if bg_luma > 225 and max(bg) - min(bg) < 32:
            return None
        row_sum = [0] * sh
        col_sum = [0] * sw
        for y in range(sh):
            for x in range(sw):
                r, g, b = pix[x, y]
                lum = (299*r + 587*g + 114*b) / 1000
                chroma = max(r, g, b) - min(r, g, b)
                dist = abs(r-bg[0]) + abs(g-bg[1]) + abs(b-bg[2])
                if (lum >= 150 and chroma <= 76 and
                    (lum >= bg_luma + 27 or dist >= 105)):
                    row_sum[y] += 1
                    col_sum[x] += 1
        if max(row_sum) < 0.40 * sw or max(col_sum) < 0.40 * sh:
            return None
        rows = [i for i, n in enumerate(row_sum) if n >= max(0.22 * sw, max(row_sum) * 0.36)]
        cols = [i for i, n in enumerate(col_sum) if n >= max(0.22 * sh, max(col_sum) * 0.36)]
        if not rows or not cols:
            return None
        l, t, r, b = min(cols), min(rows), max(cols)+1, max(rows)+1
        pw, ph = r-l, b-t
        if pw < 0.38*sw or ph < 0.38*sh:
            return None
        if not (l < sw/2 < r and t < sh/2 < b):
            return None
        # Need an actual margin of desk on all four edges.
        if min(l, t, sw-r, sh-b) < max(2, round(min(sw, sh)*0.018)):
            return None
        ratio = (pw * ph) / (sw * sh)
        if not (0.25 <= ratio <= 0.90):
            return None
        # Extra 2% paper margin so edge handwriting is not clipped.
        pad_x, pad_y = max(1, round(pw*.020)), max(1, round(ph*.020))
        l, t, r, b = max(0, l-pad_x), max(0, t-pad_y), min(sw, r+pad_x), min(sh, b+pad_y)
        # Account for downsampling and round outward.
        from math import floor, ceil
        result = (max(0, floor(l * w / sw)), max(0, floor(t * h / sh)),
                  min(w, ceil(r * w / sw)), min(h, ceil(b * h / sh)))
        if result[2]-result[0] <= 0 or result[3]-result[1] <= 0:
            return None
        return result
    finally:
        sample.close()


def auto_crop_image(image: Image.Image) -> Image.Image:
    """Return a separate image object; never mutate the source image."""
    box = _box_for_page(image)
    return image.crop(box) if box else image.copy()

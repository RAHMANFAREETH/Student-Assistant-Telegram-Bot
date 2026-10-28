"""Offline paper scanner: auto four-corner detection, perspective rectification, preview and A4 export.

No OCR or external API. Operates on byte arrays in memory. User images are
re-encoded without EXIF/GPS metadata. Not guaranteed to find every document.
"""
from __future__ import annotations

from io import BytesIO
import math
import re

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

SCAN_BUTTON = "📸 Scan Document"
SCAN_MODE = "scan_document_v716"
SCAN_PREVIEW = "👁 Preview Scan"
SCAN_ADJUST = "📐 Adjust Corners"
SCAN_RESCAN = "🔄 Auto Detect Again"
SCAN_ORIGINAL = "↩️ Original Photo"
SCAN_SAVE_IMAGE = "🖼 Save as Image"
SCAN_SAVE_PDF = "📄 Save as PDF"
SCAN_CHANGE = "🔁 Change Photo"
SCAN_CANCEL = "❌ Cancel Scan"
SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
MAX_SOURCE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
MAX_OUTPUT_BYTES = 18 * 1024 * 1024


class ScanError(ValueError):
    pass


def read_photo(data: bytes) -> Image.Image:
    """Decode a safe, EXIF-oriented image and return a detached RGB image."""
    if not data or len(data) > MAX_SOURCE_BYTES:
        raise ScanError("❌ Image must be smaller than 12 MB.")
    try:
        with Image.open(BytesIO(data)) as source:
            w, h = source.size
            if w < 100 or h < 100 or w * h > MAX_IMAGE_PIXELS:
                raise ScanError("❌ Image must be at least 100×100 and at most 24 megapixels.")
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ScanError("❌ Send a JPG, PNG or WEBP photo.")
            corrected = ImageOps.exif_transpose(source)
            try:
                corrected.load()
                if corrected.mode == "RGBA":
                    background = Image.new("RGB", corrected.size, "white")
                    background.paste(corrected, mask=corrected.getchannel("A"))
                    return background
                return corrected.convert("RGB")
            finally:
                if corrected is not source:
                    corrected.close()
    except ScanError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
        raise ScanError("❌ This image could not be opened. Please send JPG, PNG or WEBP.") from error


def ordered_quad(points) -> np.ndarray:
    """Order arbitrary 4 corners TL, TR, BR, BL; reject degenerate shapes."""
    pts = np.asarray(points, dtype=np.float32).reshape(4, 2)
    if not np.all(np.isfinite(pts)):
        raise ScanError("❌ Corner positions must be valid numbers.")
    # y-sorted top/bottom then x-sort each pair works for approximately upright pages.
    y_idx = np.argsort(pts[:, 1], kind="stable")
    top = pts[y_idx[:2]]
    bottom = pts[y_idx[2:]]
    top = top[np.argsort(top[:, 0])]
    bottom = bottom[np.argsort(bottom[:, 0])]
    rect = np.array([top[0], top[1], bottom[1], bottom[0]], dtype=np.float32)
    if abs(cv2.contourArea(rect.reshape(-1, 1, 2))) < 100:
        raise ScanError("❌ The four corners are too close together.")
    if not cv2.isContourConvex(rect.reshape(-1, 1, 2)):
        raise ScanError("❌ Corners overlap. Please use TL TR BR BL order.")
    return rect


def detect_corners(image: Image.Image) -> np.ndarray | None:
    """Detect the strongest large quadrilateral; returns original-image coordinates.

    Fail closed on weak edges: do not invent a crop which could cut off writing.
    """
    w, h = image.size
    scale = min(1.0, 1200 / max(w, h))
    if scale < 1:
        sample = image.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    else:
        sample = image
    try:
        rgb = np.asarray(sample.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edge = cv2.Canny(gray, 45, 130)
        edge = cv2.morphologyEx(edge, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(edge, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        canvas_area = float(edge.shape[0] * edge.shape[1])
        possible = []
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:45]:
            area = cv2.contourArea(contour)
            if area < canvas_area * .18 or area > canvas_area * .995:
                continue
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, .024 * perimeter, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            try:
                quad = ordered_quad(approx.reshape(4, 2))
            except ScanError:
                continue
            # Skip extremely skinny, indistinct quadrilaterals.
            lens = [np.linalg.norm(quad[(i + 1) % 4] - quad[i]) for i in range(4)]
            if min(lens) < 45 or max(lens) / max(min(lens), 1) > 9:
                continue
            possible.append((area, quad))
        if not possible:
            return None
        _, corners = max(possible, key=lambda item: item[0])
        return corners / scale
    finally:
        if sample is not image:
            sample.close()


def parse_corners(text: str, size: tuple[int, int]) -> np.ndarray:
    """Parse 8 percentages in TL TR BR BL order (x y x y x y x y)."""
    values = re.split(r"[,;\s]+", text.strip())
    if len(values) != 8:
        raise ScanError("❌ Send eight percentages: TLx TLy TRx TRy BRx BRy BLx BLy. Example: 5 5 95 5 95 95 5 95")
    try:
        nums = [float(v) for v in values]
    except ValueError as error:
        raise ScanError("❌ Corner positions must be numbers between 0 and 100.") from error
    if any(not math.isfinite(n) or n < 0 or n > 100 for n in nums):
        raise ScanError("❌ Each percentage must be between 0 and 100.")
    w, h = size
    pts = np.array(nums, dtype=np.float32).reshape(4, 2) * [w / 100, h / 100]
    ordered = ordered_quad(pts)
    # Protect against a reordered shape from user input by requiring listed order.
    if not np.allclose(ordered, pts, atol=max(w, h) * .001):
        raise ScanError("❌ Enter corners in this order: top-left, top-right, bottom-right, bottom-left.")
    if cv2.contourArea(ordered.reshape(-1, 1, 2)) < w * h * .025:
        raise ScanError("❌ Selected paper area is too small.")
    return ordered


def _margin(corners: np.ndarray, w: int, h: int) -> np.ndarray:
    """Grow 2% from center to keep handwritten ink near the border."""
    middle = corners.mean(axis=0)
    expanded = middle + (corners - middle) * 1.025
    expanded[:, 0] = np.clip(expanded[:, 0], 0, w - 1)
    expanded[:, 1] = np.clip(expanded[:, 1], 0, h - 1)
    return expanded.astype(np.float32)


def rectify(image: Image.Image, corners: np.ndarray | None) -> Image.Image:
    """Perspective-correct a page, or return original when edges are uncertain."""
    if corners is None:
        return image.copy()
    w, h = image.size
    corners = _margin(ordered_quad(corners), w, h)
    tl, tr, br, bl = corners
    width = int(round(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))))
    height = int(round(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))))
    if width < 80 or height < 80:
        raise ScanError("❌ The page is too small. Select wider corners.")
    resize_factor = min(1.0, 3200 / max(width, height), math.sqrt(14_000_000 / (width * height)))
    width, height = max(1, round(width * resize_factor)), max(1, round(height * resize_factor))
    destination = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], np.float32)
    matrix = cv2.getPerspectiveTransform(corners, destination)
    array = np.asarray(image.convert("RGB"))
    transformed = cv2.warpPerspective(array, matrix, (width, height), flags=cv2.INTER_CUBIC,
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    return Image.fromarray(transformed, "RGB")


def create_scan(image_bytes: bytes, corners: np.ndarray | None, *, preview: bool = False) -> BytesIO:
    with read_photo(image_bytes) as image:
        with rectify(image, corners) as corrected:
            output = BytesIO()
            if preview:
                draft = corrected.copy()
                try:
                    draft.thumbnail((1050, 1050))
                    draft.save(output, "JPEG", quality=82, optimize=True)
                    output.name = "scan_preview.jpg"
                finally:
                    draft.close()
            else:
                corrected.save(output, "JPEG", quality=90, optimize=True)
                output.name = "scanned_document.jpg"
            if output.tell() > MAX_OUTPUT_BYTES:
                raise ScanError("❌ Scanned result is too large; please use a smaller photo.")
            output.seek(0)
            return output


def create_scan_pdf(image_bytes: bytes, corners: np.ndarray | None) -> BytesIO:
    """Create a one-page A4 PDF, photo embedded as a raster image (not OCR)."""
    with read_photo(image_bytes) as image:
        with rectify(image, corners) as page:
            # A4 at 150 dpi with 3% surrounding white margin; landscape as needed.
            cw, ch = (1240, 1754) if page.width <= page.height else (1754, 1240)
            margin = 38
            factor = min((cw - margin * 2) / page.width,
                         (ch - margin * 2) / page.height)
            fitted_size = (max(1, round(page.width * factor)),
                           max(1, round(page.height * factor)))
            fitted = page.resize(fitted_size, Image.Resampling.LANCZOS)
            try:
                sheet = Image.new("RGB", (cw, ch), "white")
                try:
                    sheet.paste(fitted, ((cw - fitted.width) // 2,
                                         (ch - fitted.height) // 2))
                    output = BytesIO()
                    sheet.save(output, "PDF", resolution=150.0)
                    if output.tell() > MAX_OUTPUT_BYTES:
                        raise ScanError("❌ PDF is too large; please use a smaller photo.")
                    output.name = "scanned_document.pdf"
                    output.seek(0)
                    return output
                finally:
                    sheet.close()
            finally:
                fitted.close()

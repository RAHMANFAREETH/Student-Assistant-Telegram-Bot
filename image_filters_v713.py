"""Local-only, non-destructive filters for Student Assistant's Images -> PDF.

No external service or database calls. Pillow is already required by pdf_tools.py.
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageEnhance, ImageOps, ImageFilter, UnidentifiedImageError

FILTER_BUTTON = "🎨 Choose Filter"
PREVIEW_BUTTON = "👁 Preview Last"
REMOVE_BUTTON = "🗑 Remove Last"
BACK_BUTTON = "↩️ Back to Images"
FILTER_LABELS = {
    "🌈 Original": "original",
    "📄 Clean Scan": "scan",
    "⚫ Black & White": "bw",
    "⚪ Grayscale": "gray",
    "✨ Auto Enhance": "auto",
    "☀️ Brighter": "bright",
    "🎚 High Contrast": "contrast",
    "🔎 Sharpen": "sharp",
}
FILTER_NAMES = {v: k for k, v in FILTER_LABELS.items()}
MAX_IMAGES = 15
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 48 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
MAX_PDF_DIMENSION = 2000


class ImageFilterError(ValueError):
    """Safe, user-displayable image validation error."""


def selected_filter(state: dict) -> str:
    value = state.get("image_filter", "original")
    return value if value in FILTER_NAMES else "original"


def _read_image(data: bytes, *, max_dimension: int = MAX_PDF_DIMENSION) -> Image.Image:
    if not isinstance(data, bytes) or not data:
        raise ImageFilterError("❌ This image could not be read. Send a valid JPG, PNG or WEBP.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageFilterError("❌ This image is too large (maximum 12 MB per image).")
    try:
        with Image.open(BytesIO(data)) as source:
            if source.width < 1 or source.height < 1:
                raise ImageFilterError("❌ Invalid image dimensions.")
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise ImageFilterError("❌ Image resolution is too large. Try a smaller photo.")
            if source.format not in ("JPEG", "PNG", "WEBP", "BMP"):
                raise ImageFilterError("❌ Use JPG, PNG or WEBP images.")
            # Auto-rotate phone photos, using EXIF orientation before filtering.
            rotated = ImageOps.exif_transpose(source)
            try:
                if rotated.mode in ("RGBA", "LA") or "transparency" in rotated.info:
                    rgba = rotated.convert("RGBA")
                    white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                    white.alpha_composite(rgba)
                    rgb = white.convert("RGB")
                    white.close()
                    rgba.close()
                else:
                    rgb = rotated.convert("RGB")
            finally:
                if rotated is not source:
                    rotated.close()
    except ImageFilterError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise ImageFilterError("❌ This file is not a valid image. Send JPG, PNG or WEBP.") from exc
    if max_dimension and max(rgb.size) > max_dimension:
        rgb.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    return rgb


def enqueue_image(state: dict, data: bytes) -> int:
    images = state.setdefault("images", [])
    if len(images) >= MAX_IMAGES:
        raise ImageFilterError(f"❌ Maximum {MAX_IMAGES} images per PDF. Create this PDF first.")
    if not isinstance(data, bytes) or len(data) > MAX_IMAGE_BYTES:
        raise ImageFilterError("❌ Maximum image size is 12 MB.")
    if sum(len(item) for item in images) + len(data) > MAX_TOTAL_BYTES:
        raise ImageFilterError("❌ Total images are too large. Create a PDF with fewer photos.")
    # Validate before storing; free the decoded object immediately.
    validated = _read_image(data, max_dimension=0)
    validated.close()
    images.append(data)
    return len(images)


def filter_image(image: Image.Image, filter_code: str) -> Image.Image:
    if filter_code not in FILTER_NAMES:
        raise ImageFilterError("❌ Unknown filter. Please select one from the menu.")
    if filter_code == "original":
        return image.copy()
    if filter_code == "gray":
        return ImageOps.grayscale(image).convert("RGB")
    if filter_code == "bw":
        gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
        return gray.point(lambda pixel: 255 if pixel >= 165 else 0).convert("RGB")
    if filter_code == "scan":
        gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=2)
        return ImageEnhance.Contrast(gray).enhance(1.35).filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=3)).convert("RGB")
    if filter_code == "auto":
        enhanced = ImageOps.autocontrast(image, cutoff=1, preserve_tone=True)
        return ImageEnhance.Contrast(enhanced).enhance(1.08)
    if filter_code == "bright":
        return ImageEnhance.Brightness(image).enhance(1.28)
    if filter_code == "contrast":
        return ImageEnhance.Contrast(image).enhance(1.55)
    if filter_code == "sharp":
        return ImageEnhance.Sharpness(image).enhance(2.0)
    raise ImageFilterError("❌ Unknown filter.")


def make_preview(data: bytes, filter_code: str) -> BytesIO:
    image = _read_image(data, max_dimension=900)
    try:
        filtered = filter_image(image, filter_code)
        try:
            result = BytesIO()
            result.name = "image_filter_preview.jpg"
            filtered.save(result, format="JPEG", quality=83, optimize=True)
            result.seek(0)
            return result
        finally:
            filtered.close()
    finally:
        image.close()


def images_to_pdf(image_items: list[bytes], filter_code: str = "original") -> BytesIO:
    if not image_items:
        raise ImageFilterError("❌ Send at least one image first.")
    if len(image_items) > MAX_IMAGES:
        raise ImageFilterError(f"❌ Maximum {MAX_IMAGES} images per PDF.")
    if filter_code not in FILTER_NAMES:
        raise ImageFilterError("❌ Unknown filter. Please choose a supported filter.")
    converted = []
    try:
        for data in image_items:
            original = _read_image(data)
            try:
                converted.append(filter_image(original, filter_code))
            finally:
                original.close()
        output = BytesIO()
        output.name = "filtered_images.pdf" if filter_code != "original" else "images_to_pdf.pdf"
        converted[0].save(
            output, format="PDF", save_all=True, append_images=converted[1:],
            resolution=150.0, quality=85,
        )
        output.seek(0)
        return output
    except (OSError, ValueError) as exc:
        if isinstance(exc, ImageFilterError):
            raise
        raise ImageFilterError("❌ Could not create PDF from these images. Try smaller photos.") from exc
    finally:
        for image in converted:
            image.close()

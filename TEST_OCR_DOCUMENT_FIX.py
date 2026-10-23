"""Offline OCR tests: no external API requests or credentials needed."""
import os
import unittest
from io import BytesIO
from unittest.mock import patch

try:
    from PyPDF2 import PdfWriter
except ImportError:
    from pypdf import PdfWriter
import translation_ocr as ocr


def make_pdf(pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class Response:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self.payload = payload if payload is not None else {
            "IsErroredOnProcessing": False,
            "OCRExitCode": 1,
            "ParsedResults": [{"ParsedText": "Arabic sample"}],
        }
    def json(self):
        return self.payload


class OCRDocumentTests(unittest.TestCase):
    def setUp(self):
        self.key = patch.dict(os.environ, {"OCR_SPACE_API_KEY": "fake-testing-key"})
        self.key.start()
        self.addCleanup(self.key.stop)

    def test_1_page_pdf_uses_ascii_filename(self):
        with patch.object(ocr.requests, "post", return_value=Response()) as post:
            self.assertIn("Arabic sample", ocr.extract_text_with_ocr(make_pdf(1), "آداب يوم الجمعة.pdf"))
            self.assertEqual(post.call_args.kwargs["files"]["file"][0], "scanned_document.pdf")
            self.assertEqual(post.call_args.kwargs["data"]["filetype"], "PDF")

    def test_4_page_pdf_split_3_plus_1(self):
        with patch.object(ocr.requests, "post", return_value=Response()) as post:
            text = ocr.extract_text_with_ocr(make_pdf(4), "ar.pdf")
            self.assertEqual(post.call_count, 2)
            self.assertEqual(text.count("Arabic sample"), 2)

    def test_7_page_pdf_split_3_3_1(self):
        with patch.object(ocr.requests, "post", return_value=Response()) as post:
            ocr.extract_text_with_ocr(make_pdf(7), "ar.pdf")
            self.assertEqual(post.call_count, 3)

    def test_400_includes_actionable_details(self):
        with patch.object(ocr.requests, "post", return_value=Response(400, {"error": "E400 Invalid file"})):
            with self.assertRaisesRegex(RuntimeError, "HTTP 400.*E400"):
                ocr.extract_text_with_ocr(make_pdf(1), "ar.pdf")

    def test_429_includes_actionable_details(self):
        with patch.object(ocr.requests, "post", return_value=Response(429)):
            with self.assertRaisesRegex(RuntimeError, "429"):
                ocr.extract_text_with_ocr(make_pdf(1), "ar.pdf")

    def test_image_uses_ascii_filename(self):
        with patch.object(ocr.requests, "post", return_value=Response()) as post:
            ocr.extract_text_with_ocr(b"fake-image", "صورتي.jpg")
            self.assertEqual(post.call_args.kwargs["files"]["file"][0], "scanned_image.jpg")

    def test_png_file_preserves_png_media_type(self):
        with patch.object(ocr.requests, "post", return_value=Response()) as post:
            ocr.extract_text_with_ocr(b"\x89PNG\r\n\x1a\n" + b"fake", "صورة.png")
            self.assertEqual(post.call_args.kwargs["files"]["file"][0], "scanned_image.png")
            self.assertEqual(post.call_args.kwargs["files"]["file"][2], "image/png")

    def test_missing_key(self):
        with patch.dict(os.environ, {"OCR_SPACE_API_KEY": ""}):
            with self.assertRaisesRegex(RuntimeError, "not configured"):
                ocr.extract_text_with_ocr(b"fake-image")

    def test_rejected_api_key(self):
        with patch.object(ocr.requests, "post", return_value=Response(403)):
            with self.assertRaisesRegex(RuntimeError, "OCR_SPACE_API_KEY"):
                ocr.extract_text_with_ocr(b"fake-image")

    def test_processing_errors_not_ignored(self):
        with patch.object(ocr.requests, "post", return_value=Response(200, {
            "IsErroredOnProcessing": True, "ErrorMessage": ["Unreadable page"]
        })):
            with self.assertRaisesRegex(RuntimeError, "Unreadable page"):
                ocr.extract_text_with_ocr(make_pdf(1), "ar.pdf")

    def test_too_many_pages_fails_before_api(self):
        with patch.object(ocr.requests, "post") as post:
            with self.assertRaisesRegex(ValueError, "split it"):
                ocr.extract_text_with_ocr(make_pdf(31), "ar.pdf")
            post.assert_not_called()

    def test_multipart_chunk_over_limit_split_again(self):
        with patch.object(ocr, "OCR_MAX_UPLOAD_BYTES", 1):
            with patch.object(ocr.requests, "post") as post:
                with self.assertRaisesRegex(RuntimeError, "1 MB"):
                    ocr.extract_text_with_ocr(make_pdf(1), "ar.pdf")
                post.assert_not_called()


if __name__ == "__main__":
    unittest.main()

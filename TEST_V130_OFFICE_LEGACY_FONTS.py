import io, unittest, zipfile
from unittest.mock import patch
import office_legacy_fonts_v130 as fonts

def docx_with(font):
    xml=(f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
         f'<w:body><w:p><w:r><w:rPr><w:rFonts w:ascii="{font}" w:hAnsi="{font}"/></w:rPr>'
         f'<w:t>Vanakkam</w:t></w:r></w:p></w:body></w:document>')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        z.writestr('word/document.xml',xml)
    return out.getvalue()

class FontGuardTests(unittest.TestCase):
    def test_detect_kalaham(self):
        self.assertEqual(fonts.required_legacy_fonts(docx_with('Kalaham'),'docx'),('Kalaham',))
    def test_no_false_positive_noto(self):
        self.assertEqual(fonts.required_legacy_fonts(docx_with('Noto Sans Tamil'),'docx'),())
    def test_missing_detected(self):
        with patch.object(fonts,'installed_font_families',return_value={'notosanstamil'}):
            self.assertEqual(fonts.missing_legacy_fonts(docx_with('Kalaham'),'docx'),('Kalaham',))
    def test_available_font_accepted(self):
        with patch.object(fonts,'installed_font_families',return_value={'kalaham'}):
            self.assertFalse(fonts.missing_legacy_fonts(docx_with('Kalaham'),'docx'))
    def test_unverifiable_font_not_silently_accepted(self):
        with patch.object(fonts,'installed_font_families',return_value=None):
            self.assertEqual(fonts.missing_legacy_fonts(docx_with('Kalaham'),'docx'),('Kalaham',))
    def test_pptx_font_detection(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('ppt/slides/slide1.xml','<p:sld xmlns:p="x" xmlns:a="y"><a:rPr><a:latin typeface="Bamini"/></a:rPr></p:sld>')
        self.assertEqual(fonts.required_legacy_fonts(out.getvalue(),'pptx'),('Bamini',))
    def test_font_table_alone_does_not_trigger(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="x"/>')
            z.writestr('word/fontTable.xml','<w:fonts xmlns:w="x"><w:font w:name="Kalaham"/></w:fonts>')
        self.assertEqual(fonts.required_legacy_fonts(out.getvalue(),'docx'),())
    def test_end_to_end_converter_rejects_missing(self):
        import office_to_pdf_v713 as conv
        with patch.object(fonts,'installed_font_families',return_value=set()):
            with self.assertRaisesRegex(conv.OfficePdfError,'Kalaham'):
                # Invoke guard in isolation to avoid requiring a full test DOCX.
                conv._require_supported_legacy_fonts(docx_with('Kalaham'),'docx')
    def test_converter_accepts_unicode_docx(self):
        import office_to_pdf_v713 as conv
        with patch.object(fonts,'installed_font_families',return_value=set()):
            conv._require_supported_legacy_fonts(docx_with('Noto Sans Tamil'),'docx')

if __name__=='__main__':unittest.main()

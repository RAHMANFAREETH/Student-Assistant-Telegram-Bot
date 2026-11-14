"""Run from project root: python -X utf8 -m unittest TEST_V130_FONT_LIBRARY -q"""
import json
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import zipfile

from office_font_catalog_v130 import catalog,declared_font_names,missing_exact_fonts,normalize

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def docx(font, *, used=True):
    doc=f'<w:document xmlns:w="{W}"><w:body><w:p><w:pPr><w:pStyle w:val="active"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="{font}"/></w:rPr><w:t>Sample</w:t></w:r></w:p></w:body></w:document>'
    styles=f'<w:styles xmlns:w="{W}"><w:style w:styleId="unused"><w:rPr><w:rFonts w:ascii="Sakkal Majalla"/></w:rPr></w:style><w:style w:styleId="active"><w:rPr><w:rFonts w:ascii="Noto Sans"/></w:rPr></w:style></w:styles>'
    buffer=BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr('word/document.xml',doc)
        z.writestr('word/styles.xml',styles)
    return buffer.getvalue()

class FontLibraryTests(unittest.TestCase):
    def test_four_script_counts(self):
        data=catalog();fonts=data['fonts']
        self.assertEqual(len(fonts),80)
        self.assertEqual({lang:sum(x['language']==lang for x in fonts) for lang in ('ta','en','ar','si')},
                         {'ta':18,'en':26,'ar':26,'si':10})
        self.assertEqual(len({(f['language'],f['name']) for f in fonts}),80)
    def test_priority_fonts(self):
        data=catalog()
        for font in ('Sakkal Majalla','Traditional Arabic','Arabic Typesetting','Iskoola Pota'):
            self.assertIn(font,data['priority_exact_pdf'])
    def test_no_legacy_Unicode_mislabel(self):
        data=catalog()
        unicode_names={x['name'] for x in data['fonts']}
        for bad in ('Bamini','Kalaham','FM Abhaya'):
            self.assertNotIn(bad,unicode_names)
    def test_sakkal_detected(self):
        self.assertIn('Sakkal Majalla',declared_font_names(docx('Sakkal Majalla'),'docx'))
    def test_used_styles_not_unused(self):
        self.assertNotIn('Sakkal Majalla',declared_font_names(docx('Noto Sans'),'docx'))
    def test_missing_sakkal_blocks_when_not_installed(self):
        self.assertEqual(missing_exact_fonts(docx('Sakkal Majalla'),'docx',installed={'amiri'},policy='priority'),('Sakkal Majalla',))
    def test_present_sakkal_not_blocked(self):
        self.assertEqual(missing_exact_fonts(docx('Sakkal Majalla'),'docx',installed={'sakkalmajalla'},policy='priority'),())
    def test_off_policy_bypasses_exact_unicode_check_only(self):
        self.assertEqual(missing_exact_fonts(docx('Sakkal Majalla'),'docx',installed=set(),policy='off'),())
    def test_nonpriority_font_not_blocked_default(self):
        self.assertEqual(missing_exact_fonts(docx('Times New Roman'),'docx',installed=set(),policy='priority'),())
    def test_catalog_strict_detects_times(self):
        self.assertIn('Times New Roman',missing_exact_fonts(docx('Times New Roman'),'docx',installed=set(),policy='catalog'))
    def test_unverified_is_not_success(self):
        with patch('office_legacy_fonts_v130.installed_font_families',return_value=None):
            self.assertEqual(missing_exact_fonts(docx('Sakkal Majalla'),'docx',policy='priority'),('Sakkal Majalla',))
    def test_corrupt_input_raises(self):
        with self.assertRaises(ValueError):declared_font_names(b'untrusted','docx')
    def test_invalid_policy_raises(self):
        with self.assertRaises(ValueError):missing_exact_fonts(docx('Sakkal Majalla'),'docx',policy='weird')
    def test_pptx_declaration(self):
        blob=BytesIO()
        with zipfile.ZipFile(blob,'w') as z:
            z.writestr('ppt/slides/slide1.xml','<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:latin typeface="Sakkal Majalla"/></p:sld>')
        self.assertIn('Sakkal Majalla',declared_font_names(blob.getvalue(),'pptx'))

if __name__=='__main__':unittest.main()

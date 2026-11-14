"""Tests for four-language Office diagnostics and guarded installer.
Use: python -X utf8 -m unittest TEST_V130_FOUR_LANGUAGES -q
"""
from __future__ import annotations
from io import BytesIO
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parent

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

check=load(ROOT/'office_language_check_v130.py','office_language_check_v130_test')
installer=load(ROOT/'INSTALL_V130_FOUR_LANGUAGES.py','installer_v130_four_test')

def docx(text,font='Noto Sans Tamil'):
    document=('<?xml version="1.0" encoding="utf-8"?><w:document '
              'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:body><w:p><w:r><w:rPr><w:rFonts w:ascii="'+font+'"/>'
              '</w:rPr><w:t>'+text+'</w:t></w:r></w:p></w:body></w:document>')
    b=BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('[Content_Types].xml','<Types/>')
        z.writestr('word/document.xml',document)
    return b.getvalue()

class FourLanguageChecks(unittest.TestCase):
    def test_docx_detects_four_unicode_scripts(self):
        result=check.report(docx('தமிழ் Hello مرحبا සිංහල'),'docx')
        self.assertEqual(set(result['languages']),{'Tamil','English/Latin','Arabic','Sinhala'})
        self.assertGreater(result['language_counts']['ar'],2)
        self.assertGreater(result['language_counts']['ta'],2)
    def test_privacy_report_never_contains_text(self):
        result=str(check.report(docx('private document words Hello'),'docx'))
        self.assertNotIn('private document',result)
    def test_original_not_modified(self):
        blob=docx('مرحبا')
        check.report(blob,'docx')
        self.assertEqual(blob,docx('مرحبا'))
    def test_latin_legacy_not_claimed_unicode(self):
        blob=docx('vl;Hsp','Bamini')
        result=check.report(blob,'docx')
        self.assertEqual(result['language_counts']['ta'],0)
        self.assertGreater(result['language_counts']['en'],0)
    def test_reject_invalid_kind(self):
        with self.assertRaises(ValueError):check.report(b'','pdf')
    def test_invalid_archive_fails(self):
        with self.assertRaises(zipfile.BadZipFile):check.report(b'not a document','docx')
    def test_legacy_sinhala_detection(self):
        font=load(ROOT/'office_legacy_fonts_v130.py','legacyfont_v130_test')
        for name in ['FMAbhaya','FM-Malithi','DL Manel','Kaputa','Thibus29STru']:
            self.assertTrue(font.recognized_legacy_font(name),name)
        for name in ['Noto Sans Sinhala','Noto Naskh Arabic','Iskoola Pota']:
            self.assertFalse(font.recognized_legacy_font(name),name)
    def test_pptx_script_detection(self):
        b=BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            z.writestr('ppt/slides/slide1.xml','<p:sld xmlns:p="p" xmlns:a="a"><a:t>مرحبا සිංහල</a:t></p:sld>')
        result=check.report(b.getvalue(),'pptx')
        self.assertGreater(result['language_counts']['ar'],0)
        self.assertGreater(result['language_counts']['si'],0)
    def test_too_large_zip_member_rejected(self):
        b=BytesIO()
        with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('word/document.xml','A'*(16*1024*1024+1))
        with self.assertRaises(ValueError):check.report(b.getvalue(),'docx')

class InstallerChecks(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory()
        root=Path(temp.name)
        baseline=ROOT/'V130_MULTIFONT_PAYLOAD/baseline'
        for name in ('Dockerfile','office_to_pdf_v713.py','super_miniapp_v122_fonts.html','super_miniapp_v122_fonts.css','super_miniapp_v122_fonts.js'):
            shutil.copy2(baseline/name,root/name)
        return temp,root
    def test_plan_original_v13(self):
        temp,root=self.fixture()
        try:
            planned=installer.plan(root)
            self.assertIn('office_legacy_fonts_v130.py',planned)
            self.assertIn('super_miniapp_v122_fonts.js',planned)
            self.assertIn('fonts-noto-ui-core',planned['Dockerfile'])
            self.assertIn('value="ar"',planned['super_miniapp_v122_fonts.html'])
        finally:temp.cleanup()
    def test_apply_is_idempotent(self):
        temp,root=self.fixture()
        try:
            installer.execute(root,apply=True)
            self.assertEqual(installer.plan(root),{})
            self.assertEqual((root/'super_miniapp_v122_fonts.html').read_text().count('id="multiscript"'),1)
        finally:temp.cleanup()
    def test_custom_existing_file_rejected(self):
        temp,root=self.fixture()
        try:
            (root/'office_legacy_fonts_v130.py').write_text('custom content',encoding='utf-8')
            with self.assertRaises(installer.SafeStop):installer.plan(root)
        finally:temp.cleanup()

if __name__=='__main__':unittest.main()

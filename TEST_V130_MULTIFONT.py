import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as ET
import office_legacy_fonts_v130 as f

NS='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def make_doc(textfont=None,style=False,unused=False):
 def make_xml():
  w='w'
  prefix=f'xmlns:w="{NS}"'
  rfont=f'<w:rFonts w:ascii="{textfont}" w:hAnsi="{textfont}"/>' if textfont else ''
  if style:
   return f'<w:document {prefix}><w:body><w:p><w:pPr><w:pStyle w:val="Used"/></w:pPr><w:r><w:t>abc</w:t></w:r></w:p></w:body></w:document>',rfont
  return f'<w:document {prefix}><w:body><w:p><w:r><w:rPr>{rfont}</w:rPr><w:t>abc</w:t></w:r></w:p></w:body></w:document>',rfont
 doc,rfont=make_xml();out=io.BytesIO()
 with zipfile.ZipFile(out,'w') as z:
  z.writestr('word/document.xml',doc)
  if style or unused:
   inner=f'<w:style w:styleId="Used"><w:rPr>{rfont}</w:rPr></w:style>' if style else ''
   inner+='<w:style w:styleId="Unused"><w:rPr><w:rFonts w:ascii="Kalaham"/></w:rPr></w:style>'
   z.writestr('word/styles.xml',f'<w:styles xmlns:w="{NS}">{inner}</w:styles>')
 return out.getvalue()

class FontTests(unittest.TestCase):
 def test_known_families(self):
  for name in ['Kalaham','Bamini Plain Medium','SunTommy','Vanavil','TSCII','TAB102','TAM12','Tharmini Plain']:
   self.assertTrue(f.recognized_legacy_font(name),name)
 def test_unicode_not_legacy(self):
  for name in ['Noto Sans Tamil','Nirmala UI','Latha','Arial','Tamil99','Table','Tamber','Kalahamxyz']:
   self.assertFalse(f.recognized_legacy_font(name),name)
 def test_explicit_run(self):
  self.assertEqual(f.required_legacy_fonts(make_doc('Kalaham'),'docx'),('Kalaham',))
 def test_style_font(self):
  self.assertEqual(f.required_legacy_fonts(make_doc('Bamini',style=True),'docx'),('Bamini',))
 def test_unused_style_not_required(self):
  self.assertEqual(f.required_legacy_fonts(make_doc('Arial',unused=True),'docx'),())
 def test_missing_font(self):
  with patch.object(f,'installed_font_families',return_value={'nirmalaui','bamini'}):
   self.assertEqual(f.missing_legacy_fonts(make_doc('Kalaham'),'docx'),('Kalaham',))
 def test_bamini_variant_detection(self):
  with patch.object(f,'installed_font_families',return_value={'baminiplainmedium'}):
   self.assertEqual(f.missing_legacy_fonts(make_doc('Bamini'),'docx'),())
 def test_no_cross_encoding_alias(self):
  with patch.object(f,'installed_font_families',return_value={'baaminiplainmedium'}):
   self.assertEqual(f.missing_legacy_fonts(make_doc('Bamini'),'docx'),('Bamini',))
 def test_pptx(self):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   z.writestr('ppt/slides/slide1.xml','<p:sld xmlns:p="x" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:latin typeface="Tharmini"/></p:sld>')
  self.assertEqual(f.required_legacy_fonts(out.getvalue(),'pptx'),('Tharmini',))
 def test_bad_xml_detected(self):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:z.writestr('word/document.xml','<bad')
  with self.assertRaises(ValueError):f.required_legacy_fonts(out.getvalue(),'docx')
 def test_installer_check_and_idempotency(self):
  import INSTALL_V130_MULTIFONT as inst
  source=Path(__file__).resolve().parent
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name in ('office_to_pdf_v713.py','Dockerfile','super_miniapp_v122_fonts.html','super_miniapp_v122_fonts.js','super_miniapp_v122_fonts.css'):
    (root/name).write_bytes((source/'V130_MULTIFONT_PAYLOAD'/'baseline'/name).read_bytes())
   changes=inst.plan(root,source/'V130_MULTIFONT_PAYLOAD')
   self.assertEqual(len(changes),8)
   inst.execute(root,source/'V130_MULTIFONT_PAYLOAD',apply=True)
   self.assertEqual(inst.plan(root,source/'V130_MULTIFONT_PAYLOAD'),{})
   txt=(root/'office_to_pdf_v713.py').read_text()
   self.assertEqual(txt.count('    _require_supported_legacy_fonts(blob, kind)\n'),1)
   self.assertIn('id="compat"',(root/'super_miniapp_v122_fonts.html').read_text())
   (root/'Dockerfile').write_text('unknown',encoding='utf-8')
   with self.assertRaises(inst.LayoutError):
    inst.plan(root,source/'V130_MULTIFONT_PAYLOAD')

if __name__=='__main__':unittest.main()

import sys
import tempfile
from pathlib import Path
import unittest
from docx import Document
from docx.shared import Pt
sys.path.insert(0,str(Path(__file__).resolve().parent))
from AUDIT_CONVERT_LEGACY_DOCX_V133 import validate_profile,convert,audit

def sample():
 return {'schema':'student-legacy-profile-v1','language':'ta','font':'Kalaham','source':'local-reviewed:qa','license':'MIT','provenanceStatus':'reviewed','direction':'decode','mappings':{'A':'அ','B':'ஆ'},'samples':[{'legacy':'AB','unicode':'அஆ'},{'legacy':'BA','unicode':'ஆஅ'}]}
class TestDocx(unittest.TestCase):
 def test_convert_copy(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'sample.docx';out=Path(tmp)/'unicode.docx'
   d=Document();run=d.add_paragraph().add_run('AB');run.font.name='Kalaham';d.save(source)
   result=convert(source,sample(),out);self.assertEqual(result['converted_runs'],1)
   self.assertEqual(Document(str(out)).paragraphs[0].text,'அஆ')
   self.assertEqual(Document(str(source)).paragraphs[0].text,'AB')
 def test_wrong_font_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'sample.docx';d=Document();d.add_paragraph('AB');d.save(source)
   with self.assertRaisesRegex(ValueError,'No explicitly declared'):convert(source,sample(),Path(tmp)/'out.docx')
 def test_wrong_mapping_refuses(self):
  p=sample();p['samples'][0]['unicode']='ஓ'
  with self.assertRaisesRegex(ValueError,'reviewed examples'):validate_profile(p)
 def test_multiple_runs_refuses(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'sample.docx';d=Document();para=d.add_paragraph()
   for piece in ('A','B'):para.add_run(piece).font.name='Kalaham'
   d.save(source)
   with self.assertRaisesRegex(ValueError,'Adjacent'):convert(source,sample(),Path(tmp)/'out.docx')
if __name__=='__main__':unittest.main()

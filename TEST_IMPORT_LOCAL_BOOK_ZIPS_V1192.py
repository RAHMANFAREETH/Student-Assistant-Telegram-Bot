"""Offline tests for local ZIP → Telegram Smart Bulk importer. No network or Telegram credentials."""
import asyncio
import importlib.util
import os
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('IMPORT_LOCAL_BOOK_ZIPS_V1192.py')
spec = importlib.util.spec_from_file_location('v1192_zip_import', SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class ZipImportTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)

    def zip(self, name='sample.zip', entries=None):
        path=self.root/name
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for a, b in (entries or {'Tamil_Book.pdf':b'PDFtest','book2.epub':b'EPUBtest'}).items():
                z.writestr(a,b)
        return path

    def test_archive_file(self):
        self.assertEqual(mod.archives_from_source(str(self.zip())), [self.root/'sample.zip'])

    def test_archive_folder(self):
        self.zip('a.zip');self.zip('b.zip');(self.root/'x.txt').write_text('x')
        self.assertEqual([x.name for x in mod.archives_from_source(str(self.root))], ['a.zip','b.zip'])

    def test_missing_path(self):
        with self.assertRaises(ValueError):mod.archives_from_source(str(self.root/'missing'))

    def test_unicode_and_nested_path_kept_name_only(self):
        p=self.zip(entries={'inner/தமிழ்_புத்தகம்.pdf':b'x','arabic/صحيح البخاري.pdf':b'y'})
        with zipfile.ZipFile(p) as z:
            self.assertEqual([i.filename for i in mod.candidates(z)], ['தமிழ்_புத்தகம்.pdf','صحيح البخاري.pdf'])

    def test_reject_traversal(self):
        bad=['../secret.pdf','/absolute.pdf','C:/secret.pdf','folder/../oops.pdf','folder\\..\\hi.pdf','folder//bad.pdf']
        for name in bad:
            with self.subTest(name=name):
                self.assertIsNone(mod.safe_member_name(zipfile.ZipInfo(name)))

    def test_reject_unsupported(self):
        for name in ('archive.zip','evil.exe','readme.png','README','dir/'):
            with self.subTest(name=name):
                self.assertIsNone(mod.safe_member_name(zipfile.ZipInfo(name)))

    def test_reject_encrypted_zip_entry(self):
        i=zipfile.ZipInfo('test.pdf');i.flag_bits |=1
        self.assertIsNone(mod.safe_member_name(i))

    def test_reject_symlink_zip_entry(self):
        i=zipfile.ZipInfo('test.pdf');i.external_attr=(0o120777<<16)
        self.assertIsNone(mod.safe_member_name(i))

    def test_reject_zip_bomb_ratio(self):
        i=zipfile.ZipInfo('test.pdf');i.file_size=2*1024**3;i.compress_size=500
        self.assertIn('ZIP-bomb',mod.safety_reason(i))

    def test_over_4gb_member_rejected(self):
        i=zipfile.ZipInfo('test.pdf');i.file_size=4*1024**3+1;i.compress_size=4*1024**3
        self.assertIn('4 GB',mod.safety_reason(i))

    def test_disk_margin(self):
        i=zipfile.ZipInfo('test.pdf');i.file_size=1000;i.compress_size=1000
        self.assertIn('disk',mod.safety_reason(i,free_bytes=2000,reserve_bytes=2000))

    def test_stream_extract(self):
        path=self.zip(entries={'dir/Clear_Book.pdf':b'%PDF'+b'A'*8192})
        with zipfile.ZipFile(path) as z:
            can=list(mod.candidates(z))[0]
            out=mod.extract_one(z,can,self.root)
        self.assertEqual(out.name,'Clear_Book.pdf')
        self.assertEqual(out.read_bytes(),b'%PDF'+b'A'*8192)

    def test_extract_collision_is_refused(self):
        p=self.zip(entries={'x/Test.pdf':b'1'})
        with zipfile.ZipFile(p) as z:
            c=list(mod.candidates(z))[0]
            (self.root/'Test.pdf').write_bytes(b'existing')
            with self.assertRaises(FileExistsError):mod.extract_one(z,c,self.root)

    def test_checkpoint_resume(self):
        p=self.zip()
        cp=mod.checkpoint_file(p,self.root)
        self.assertEqual(mod.read_checkpoint(cp),-1)
        mod.write_checkpoint(cp,19)
        self.assertEqual(mod.read_checkpoint(cp),19)
        self.assertEqual(mod.checkpoint_file(p,self.root),cp)

    def test_checkpoint_invalid_type(self):
        cp=self.root/'bad.json';cp.write_text('{"last_sent_entry": "4"}')
        with self.assertRaises(ValueError):mod.read_checkpoint(cp)

    def test_metadata_permission_required(self):
        a=types.SimpleNamespace(rights=None,language='Tamil',category='Education',author='Unknown',rights_note='')
        with self.assertRaises(ValueError):mod.validate_metadata(a)
        a.rights='permission';a.rights_note='Verified lawful distribution rights'
        mod.validate_metadata(a)

    def test_max_no_fixed_archive_size_or_file_count(self):
        self.assertFalse(hasattr(mod,'MAX_FILES'))
        self.assertIsNone(mod.safety_reason(zipfile.ZipInfo('empty.pdf')))

    def test_dry_run_no_telegram_import(self):
        p=self.zip()
        with patch.object(mod,'data_dir',return_value=self.root/'local'):
            self.assertEqual(mod.main(['--dry-run','--source',str(p)]),0)

    def test_single_member_upload_and_resume(self):
        p=self.zip(entries={'nested/test.pdf':b'pdfdata'})
        class FakeFloodWaitError(Exception):
            seconds=10
        class FakeRPCError(Exception):pass
        fakeerrors=types.SimpleNamespace(FloodWaitError=FakeFloodWaitError,RPCError=FakeRPCError)
        fakeclient=types.SimpleNamespace()
        sent=[]
        async def send_file(dest, path, force_document):
            self.assertEqual(dest,'@somebot')
            self.assertTrue(force_document)
            sent.append((Path(path).name, Path(path).read_bytes()))
        fakeclient.send_file=send_file
        args=types.SimpleNamespace(reset_checkpoint=False,minimum_free_mb=256,delay=0)
        with patch.dict(sys.modules,{'telethon':types.SimpleNamespace(errors=fakeerrors),
                                      'telethon.errors':fakeerrors}):
            a,b=asyncio.run(mod._send_archive(fakeclient,'@somebot',p,args,self.root))
            self.assertEqual((a,b),(1,0))
            self.assertEqual(sent,[('test.pdf',b'pdfdata')])
            self.assertEqual(mod.read_checkpoint(mod.checkpoint_file(p,self.root)),0)
            a,b=asyncio.run(mod._send_archive(fakeclient,'@somebot',p,args,self.root))
            self.assertEqual((a,b),(0,0))
            self.assertEqual(len(sent),1)

    def test_over_100_separate_docs(self):
        p=self.zip(entries={f'{i:03}.pdf':b'valid small doc' for i in range(105)})
        class FakeFloodWaitError(Exception):seconds=10
        class FakeRPCError(Exception):pass
        fakeerrors=types.SimpleNamespace(FloodWaitError=FakeFloodWaitError,RPCError=FakeRPCError)
        fakeclient=types.SimpleNamespace()
        sent=[]
        async def send_file(*args,**kwargs):sent.append(args[1])
        fakeclient.send_file=send_file
        args=types.SimpleNamespace(reset_checkpoint=False,minimum_free_mb=256,delay=0)
        with patch.dict(sys.modules,{'telethon':types.SimpleNamespace(errors=fakeerrors),
                                      'telethon.errors':fakeerrors}):
            with patch('builtins.print'):
                a,b=asyncio.run(mod._send_archive(fakeclient,'@somebot',p,args,self.root))
        self.assertEqual((a,b),(105,0))
        self.assertEqual(len(sent),105)


if __name__=='__main__':unittest.main()

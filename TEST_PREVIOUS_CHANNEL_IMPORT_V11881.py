"""V11.8.8.1 historical-import offline tests; no credentials or network access."""
from __future__ import annotations
import asyncio
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import IMPORT_PREVIOUS_CHANNEL_FILES_V11881 as imp
import library_smart_bulk_v1188 as smart


def make_post(message_id=1, file_name='Old_Tamil_Book.pdf', *, protected=False):
    doc = types.SimpleNamespace(attributes=[types.SimpleNamespace(file_name=file_name)]) if file_name else None
    return types.SimpleNamespace(id=message_id, document=doc, noforwards=protected)


class HelperTests(unittest.TestCase):
    def test_file_recognition(self):
        self.assertEqual(imp.supported_name(make_post(file_name='தமிழ்.pdf')), 'தமிழ்.pdf')
        self.assertIsNone(imp.supported_name(make_post(file_name='archive.zip')))
        self.assertIsNone(imp.supported_name(make_post(file_name=None)))
        self.assertEqual(imp.supported_name(make_post(file_name='BOOK.PDF')), 'BOOK.PDF')
    def test_admin_channel_only(self):
        self.assertTrue(imp.allowed_source(types.SimpleNamespace(broadcast=True,creator=True)))
        self.assertTrue(imp.allowed_source(types.SimpleNamespace(broadcast=True,admin_rights=object())))
        self.assertFalse(imp.allowed_source(types.SimpleNamespace(broadcast=True,creator=False,admin_rights=None)))
        self.assertFalse(imp.allowed_source(types.SimpleNamespace(broadcast=False,creator=True)))
    def test_no_protected_content(self):
        own = types.SimpleNamespace(noforwards=False)
        self.assertFalse(imp.protected(own, make_post()))
        self.assertTrue(imp.protected(own, make_post(protected=True)))
        self.assertTrue(imp.protected(types.SimpleNamespace(noforwards=True)))
    def test_valid_and_invalid_rights(self):
        imp.validate_metadata('Tamil','Education','Unknown','permission','License verified')
        for args in [ ('Tamil','Education','Unknown','other','License verified'),
                      ('Tamil','Education','Unknown','permission',''),
                      ('Tamil','Education','Unknown','permission','Unsafe | delimiter') ]:
            with self.assertRaises(ValueError): imp.validate_metadata(*args)
    def test_checkpoint_persist_and_identity(self):
        with tempfile.TemporaryDirectory() as d:
            p = imp.checkpoint_path(123, 456, Path(d))
            self.assertEqual(imp.read_checkpoint(p,123,456),0)
            imp.write_checkpoint(p,123,456,79)
            self.assertEqual(imp.read_checkpoint(p,123,456),79)
            with self.assertRaises(ValueError): imp.read_checkpoint(p,123,457)
            self.assertNotIn('TG_API_HASH', p.read_text())
    def test_parser_requires_mode(self):
        with self.assertRaises(SystemExit): imp.parser().parse_args([])
    def test_session_outside_git_repo(self):
        with patch.dict(os.environ,{'LOCALAPPDATA':'/tmp/LocalAppData'}):
            path=str(imp.local_data_dir())
            self.assertIn('StudentAssistantBot',path)
            self.assertNotIn('Desktop',path)


class ForwardCaptionTests(unittest.TestCase):
    def test_manual_forward_ignores_channel_caption(self):
        m=types.SimpleNamespace(caption='Subscribe to us | Follow | Thanks',
                                 forward_origin=types.SimpleNamespace(type='channel'),
                                 document=types.SimpleNamespace(file_name='Arabic_Book.pdf',file_size=42,file_id='f1',file_unique_id='u1'),
                                 photo=None,audio=None,video=None)
        config=dict(language='Arabic',category='Education',author='Unknown',
                    rights='permission',comment='Permission verified')
        caption, _info = smart._caption(m,config)
        self.assertEqual(caption,'Arabic Book | Unknown | Arabic | Education | permission | Permission verified')
    def test_direct_upload_keeps_explicit_caption(self):
        m=types.SimpleNamespace(caption='Custom Title | Writer | Tamil | Books | permission | Verified',
                                 document=types.SimpleNamespace(file_name='Filename.pdf',file_size=42,file_id='f2',file_unique_id='u2'),
                                 photo=None,audio=None,video=None)
        config=dict(language='English',category='Study',author='Unknown',
                    rights='permission',comment='Permission verified')
        caption,_ = smart._caption(m,config)
        self.assertEqual(caption,m.caption)


class FakeClient:
    def __init__(self, posts):
        self.source=types.SimpleNamespace(id=1001,title='Old Book Channel',broadcast=True,
                                          creator=True,noforwards=False)
        self.bot=types.SimpleNamespace(id=2002,username='StudyBot',bot=True)
        self.posts=posts
        self.sent=[]
        self.forwarded=[]
    async def get_me(self): return types.SimpleNamespace(bot=False,id=333)
    async def get_entity(self, name): return self.source if str(name)=='@Source' else self.bot
    async def send_message(self, dest, text):
        self.sent.append(text)
        return types.SimpleNamespace(id=200+len(self.sent))
    async def iter_messages(self, source, **kw):
        for post in self.posts:
            if post.id>kw.get('min_id',0):
                yield post
    async def forward_messages(self, dest, msg, **kw):
        self.forwarded.append((msg.id,kw))


class EndToEndMockTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.args=imp.parser().parse_args(['--apply','--source','@Source','--bot','@StudyBot',
                                            '--max-files','2','--rights','permission',
                                            '--rights-note','License verified'])
        self.fakes=types.SimpleNamespace(RPCError=type('RPCError',(Exception,),{}),
                                          FloodWaitError=type('FloodWaitError',(Exception,),{}))
        self.module_patch=patch.dict(sys.modules, {'telethon':types.ModuleType('telethon'),
                                                   'telethon.errors':self.fakes})
        self.module_patch.start();self.addCleanup(self.module_patch.stop)
        self.patch_root=patch.object(imp,'local_data_dir',return_value=self.root)
        self.patch_root.start();self.addCleanup(self.patch_root.stop)
    def test_dry_run_no_message_sent(self):
        args=imp.parser().parse_args(['--dry-run','--source','@Source','--bot','@StudyBot'])
        client=FakeClient([make_post(1),make_post(2,'note.txt')])
        asyncio.run(imp._run(args,client))
        self.assertEqual(client.sent,[])
        self.assertEqual(client.forwarded,[])
        self.assertFalse(list(self.root.glob('checkpoint-*.json')))
    def test_apply_forwards_eligible_old_docs_and_checkpoints(self):
        client=FakeClient([make_post(1,'a.pdf'),make_post(2,'bad.zip'),make_post(3,'b.epub'),make_post(4,'c.pdf')])
        async def ack(*args,**kwargs): return True
        with patch.object(imp,'_wait_for_reply',side_effect=ack),patch('builtins.input',return_value='IMPORT'),\
             patch.object(imp.asyncio,'sleep',return_value=None):
            asyncio.run(imp._run(self.args,client))
        self.assertEqual([x[0] for x in client.forwarded],[1,3])
        self.assertTrue(all(x[1].get('drop_media_captions') for x in client.forwarded))
        self.assertEqual(client.sent[0],'/mediabulk')
        self.assertTrue(client.sent[1].startswith('/mediabulkset Tamil'))
        self.assertEqual(client.sent[-1],'/mediabulkstatus')
        path=imp.checkpoint_path(1001,2002,self.root)
        self.assertEqual(imp.read_checkpoint(path,1001,2002),3)
    def test_apply_stops_without_confirmation(self):
        client=FakeClient([make_post(1)])
        with patch('builtins.input',return_value='NO'):
            asyncio.run(imp._run(self.args,client))
        self.assertEqual(client.sent,[])
        self.assertEqual(client.forwarded,[])
    def test_resume_skips_completed_posts(self):
        path=imp.checkpoint_path(1001,2002,self.root)
        imp.write_checkpoint(path,1001,2002,2)
        client=FakeClient([make_post(1),make_post(2),make_post(3)])
        async def ack(*args,**kwargs):return True
        with patch.object(imp,'_wait_for_reply',side_effect=ack),patch('builtins.input',return_value='IMPORT'),\
             patch.object(imp.asyncio,'sleep',return_value=None):
            asyncio.run(imp._run(self.args,client))
        self.assertEqual([x[0] for x in client.forwarded],[3])
    def test_rejects_nonadmin_channel(self):
        client=FakeClient([make_post(1)])
        client.source.creator=False
        with self.assertRaises(ValueError):asyncio.run(imp._run(self.args,client))
        self.assertEqual(client.sent,[])


if __name__=='__main__':unittest.main()

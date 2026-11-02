"""Safe offline unit tests for Telegram ZIP importer; no Telegram credentials or network."""
import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace as NS
import zipfile

import IMPORT_TELEGRAM_ZIPS_V11921 as remote


class LinkTests(unittest.TestCase):
    def test_private_message_link(self):
        self.assertEqual(remote.parse_message_link('https://t.me/c/4489007052/7'), (-1004489007052, 7))

    def test_public_message_link(self):
        self.assertEqual(remote.parse_message_link('https://t.me/MyBookChannel/124?single'), ('MyBookChannel',124))

    def test_public_preview_link(self):
        self.assertEqual(remote.parse_message_link('https://t.me/s/MyBookChannel/124'), ('MyBookChannel',124))

    def test_bad_invite_not_accepted(self):
        for link in ('https://t.me/+SECRET', 'https://t.me/joinchat/SECRET',
                     'https://example.org/a.zip', 'https://t.me/c/nope/1',
                     'https://t.me/c/345/0', 'https://t.me/MyChat',
                     'https://t.me/MyChat/17/2'):
            with self.subTest(link=link), self.assertRaises(ValueError):
                remote.parse_message_link(link)

    def test_file_source_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'links.txt'
            file.write_text('#skip\nhttps://t.me/c/1234/5\nhttps://t.me/c/1234/5\n',encoding='utf8')
            args=NS(link=['https://t.me/PublicBookChannel/3'],links_file=str(file))
            self.assertEqual(remote.source_links(args), ['https://t.me/PublicBookChannel/3','https://t.me/c/1234/5'])

    def test_zip_name_and_size(self):
        m=NS(document=NS(size=400,attributes=[]),file=NS(name='كتب.zip',size=400))
        self.assertEqual(remote.safe_name_and_size(m), ('كتب.zip',400))

    def test_bad_document(self):
        for m in (NS(document=None,file=NS(name='hi.zip',size=1)),
                  NS(document=NS(size=10,attributes=[]),file=NS(name='hi.pdf',size=10)),
                  NS(document=NS(size=0,attributes=[]),file=NS(name='hi.zip',size=0))):
            with self.assertRaises(ValueError):remote.safe_name_and_size(m)

    def test_channel_protection(self):
        self.assertTrue(remote.is_protected(NS(noforwards=True),NS(noforwards=False)))
        self.assertTrue(remote.is_protected(NS(noforwards=False),NS(noforwards=True)))
        self.assertFalse(remote.is_protected(NS(noforwards=False),NS(noforwards=False)))


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_channel_requires_accessible_dialog(self):
        class Fake:
            async def iter_dialogs(self):
                for entity in (NS(id=981),NS(id=234)):
                    yield NS(entity=entity)
            async def get_messages(self,entity,ids):
                raise AssertionError('Should not get inaccessible message')
        with self.assertRaisesRegex(ValueError,'not found'):
            await remote.get_source(Fake(),'https://t.me/c/1234/5')

    async def test_rejects_protected_source_even_with_document(self):
        class Fake:
            async def get_entity(self,user):return NS(noforwards=True,title='Protected')
            async def get_messages(self,entity,ids):return NS(noforwards=False,document=NS(size=5),file=NS(name='a.zip',size=5))
        with self.assertRaisesRegex(ValueError,'protects'):
            await remote.get_source(Fake(),'https://t.me/ProtectedBookChannel/5')

    async def test_private_link_accessible_membership(self):
        class Fake:
            async def iter_dialogs(self):
                yield NS(entity=NS(id=4489007052,noforwards=False,title='Private'))
            async def get_messages(self,entity,ids):
                self.msg_id=ids
                return NS(id=ids,noforwards=False,document=NS(size=5),file=NS(name='a.zip',size=5))
        out = await remote.get_source(Fake(),'https://t.me/c/4489007052/7')
        self.assertEqual(out[2:], ('a.zip',5))

    async def test_fetch_archive_and_cache(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'a.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('a.txt','hello')
            data=path.read_bytes()
            cache=Path(d)/'cache'
            class Fake:
                calls=0
                async def download_media(self,msg,file):
                    self.calls+=1
                    Path(file).write_bytes(data)
                    return file
            fake=Fake()
            link='https://t.me/c/1234/5'
            first=await remote.fetch_zip(fake,NS(),link,len(data),cache)
            self.assertTrue(zipfile.is_zipfile(first))
            second=await remote.fetch_zip(fake,NS(),link,len(data),cache)
            self.assertEqual(first,second)
            self.assertEqual(fake.calls,1)

    async def test_corrupt_download_not_saved(self):
        with tempfile.TemporaryDirectory() as d:
            class Fake:
                async def download_media(self,msg,file):
                    Path(file).write_bytes(b'notzip')
                    return file
            cache=Path(d)/'cache';link='https://t.me/c/1234/7'
            with self.assertRaisesRegex(ValueError,'valid ZIP'):
                await remote.fetch_zip(Fake(),NS(),link,6,cache)
            self.assertFalse(remote.local_zip_path(link,cache).exists())

    async def test_disk_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(remote.shutil,'disk_usage',return_value=NS(free=1024)):
                with self.assertRaisesRegex(ValueError,'free disk'):
                    remote.ensure_free_space(Path(d),100*1024**2)


if __name__=='__main__':unittest.main()

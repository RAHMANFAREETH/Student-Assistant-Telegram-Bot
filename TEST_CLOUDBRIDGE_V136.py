"""Offline V13.6 regression/security tests; no live Google/Telegram calls.

Run: py -3 -m unittest TEST_CLOUDBRIDGE_V136 -q
"""
from __future__ import annotations

import os
import types
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import cloudbridge_v134 as web
import cloudbridge_v134_core as core
import cloudbridge_v134_worker as worker
import cloudbridge_v136_large as large
from TEST_CLOUDBRIDGE_V134 import FakeDb


def job(*, size=None, ciphertext=None):
    return {"id": str(uuid4()), "user_id": 101, "filename": "large.bin",
            "source_kind": "provider", "source_provider": "google",
            "source_ref": "fileId_1234", "destination_kind": "provider",
            "destination_provider": "google", "destination_path": "/large.bin",
            "status": "running", "worker": "worker-123", "cancel_requested": False,
            "bytes_done": 0, "attempts": 1, "upload_state_ciphertext": ciphertext,
            "total_bytes": size, "source_version": "drive:7" if ciphertext else None}


class FakeSource:
    def __init__(self, size):
        self.size = size
        self.version = "drive:7"
        self.reads = []
        self.verified = False

    def read_range(self, offset, count):
        self.reads.append((offset, count))
        return b"x" * count

    def verify_version(self):
        self.verified = True


class TransferTests(unittest.TestCase):
    def test_4096_setting_is_real_not_silently_clamped_to_1024(self):
        with patch.dict(os.environ, {"CLOUDBRIDGE_MAX_MB": "4096"}):
            self.assertEqual(worker.max_bytes(), 4096 * 1024 * 1024)
        with patch.dict(os.environ, {"CLOUDBRIDGE_MAX_MB": "999999"}):
            self.assertEqual(worker.max_bytes(), 4096 * 1024 * 1024)
        with patch.dict(os.environ, {"CLOUDBRIDGE_MAX_MB": "invalid"}):
            self.assertEqual(worker.max_bytes(), 100 * 1024 * 1024)

    def test_google_resumable_offset_is_accurate(self):
        response = Mock(status_code=308, headers={"Range": "bytes=0-5242879"})
        with patch.object(large, "_requests", return_value=Mock(put=Mock(return_value=response))):
            self.assertEqual(large._confirmed_offset(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=X", 9_000_000),
                (5_242_880, None))

    def test_resumable_session_rejects_untrusted_host(self):
        for url in ("https://evil.example/upload/drive/v3/files?uploadType=resumable",
                    "http://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
                    "https://www.googleapis.com.evil.com/upload/drive/v3/files?uploadType=resumable",
                    "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable#bad"):
            with self.subTest(url=url), self.assertRaises(core.BridgeError):
                large._upload_url(url)

    def test_range_mismatch_detected(self):
        with self.assertRaises(core.BridgeError):
            large._range_check({"Content-Range": "bytes 0-4/8"}, 0, 5, 9)
        with self.assertRaises(core.BridgeError):
            large._range_check({"Content-Range": "bytes 0-4/8", "Content-Encoding": "gzip"}, 0, 5, 8)

    def test_pinned_https_range_requires_matching_etag_and_exact_byte_count(self):
        reply = Mock(status=206, headers={"Content-Range": "bytes 0-0/10", "ETag": '"version-1"'})
        reply.read.side_effect = [b"Z", b""]
        pool = Mock(request=Mock(return_value=reply))
        with (patch.object(large, "validated_https_url", return_value=("https://example.org/file", ["8.8.8.8"])),
              patch("urllib3.HTTPSConnectionPool", return_value=pool)):
            self.assertEqual(large._https_range("https://example.org/file", 0, 1),
                             (10, '"version-1"', b"Z"))
        self.assertEqual(pool.request.call_args.kwargs["headers"]["Range"], "bytes=0-0")
        self.assertEqual(pool.request.call_args.kwargs["headers"]["Host"], "example.org")
        self.assertEqual(pool.request.call_args.kwargs["headers"]["Accept-Encoding"], "identity")

    def test_https_range_refuses_missing_strong_etag(self):
        reply = Mock(status=206, headers={"Content-Range": "bytes 0-0/10", "ETag": 'W/"weak"'})
        pool = Mock(request=Mock(return_value=reply))
        with (patch.object(large, "validated_https_url", return_value=("https://example.org/file", ["8.8.8.8"])),
              patch("urllib3.HTTPSConnectionPool", return_value=pool),
              self.assertRaises(core.BridgeError)):
            large._https_range("https://example.org/file", 0, 1)

    def test_google_partial_get_checks_content_range_and_version(self):
        meta = Mock(status_code=200, json=Mock(return_value={
            "size": "10", "version": "42", "mimeType": "application/octet-stream",
            "capabilities": {"canDownload": True, "canCopy": True}}))
        media = Mock(status_code=206, headers={"Content-Range": "bytes 0-4/10"},
                     iter_content=Mock(return_value=[b"hello"]))
        requests = Mock(get=Mock(side_effect=[meta, media, meta]))
        with (patch.object(large, "access_token", return_value="private-token"),
              patch.object(large, "_requests", return_value=requests)):
            source = large.GoogleSource(101, "valid_file_id", FakeDb())
            self.assertEqual(source.read_range(0, 5), b"hello")
            source.verify_version()
        self.assertEqual(source.size, 10)
        self.assertEqual(source.version, "drive:42")
        self.assertEqual(requests.get.call_args_list[1].kwargs["headers"]["Range"], "bytes=0-4")
        media.close.assert_called_once()

    def test_crash_resume_at_end_of_real_four_gibabyte_offset(self):
        size = 4096 * 1024 * 1024
        source = FakeSource(size)
        row = job(size=size, ciphertext="encrypted-session")
        row["source_kind"] = "url"
        row["source_provider"] = None
        row["source_ref"] = "https://example.org/file.bin"
        row["source_version"] = "drive:7"
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        bot = Mock()
        with (patch.object(large, "HttpsSource", return_value=source),
              patch.object(large, "decrypt_token", return_value={"url": "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=abc",
                                                                "size": size, "version": "drive:7"}),
              patch.object(large, "_confirmed_offset", return_value=(size - 1024 * 1024, None)) as seek,
              patch.object(large, "_put_chunk", return_value=(size, {"id": "drive_9876"})) as put,
              patch.object(large, "CHUNK", 1024 * 1024)):
            large.transfer(row, bot, db, maximum=size)
        seek.assert_called_once()
        self.assertEqual(source.reads, [(size - 1024 * 1024, 1024 * 1024)])
        self.assertEqual(put.call_args.args[2], size - 1024 * 1024)
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["bytes_done"], size)
        self.assertEqual(row["result_file_id"], "drive_9876")
        self.assertIsNone(row["upload_state_ciphertext"])
        self.assertTrue(source.verified)
        self.assertIn("drive.google.com/file/d/drive_9876", bot.send_message.call_args.args[1])

    def test_new_upload_saves_encrypted_session_before_first_chunk(self):
        source = FakeSource(12)
        row = job()
        row["source_kind"] = "url"
        row["source_provider"] = None
        row["source_ref"] = "https://example.org/small.bin"
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        def uploaded(*_args):
            self.assertEqual(row["upload_state_ciphertext"], "encrypted-persisted")
            self.assertEqual(row["stage"], "upload")
            return 12, {"id": "new_drive_9"}
        with (patch.object(large, "HttpsSource", return_value=source),
              patch.object(large, "_upload_session", return_value="https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&upload_id=ok") as create,
              patch.object(large, "encrypt_token", return_value="encrypted-persisted"),
              patch.object(large, "_put_chunk", side_effect=uploaded)):
            large.transfer(row, Mock(), db, maximum=1024)
        create.assert_called_once()
        self.assertEqual(source.reads, [(0, 12)])
        self.assertEqual(row["status"], "completed")

    def test_google_drive_server_side_copy_avoids_download_entirely(self):
        source = FakeSource(4096 * 1024 * 1024)
        source.ref = "fileId_1234"
        row = job()
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        bot = Mock()
        requests = Mock()
        requests.post.return_value = Mock(status_code=200, json=Mock(return_value={"id": "copied_file_123"}))
        with (patch.object(large, "GoogleSource", return_value=source),
              patch.object(large, "_existing_drive_copy", return_value=None),
              patch.object(large, "_requests", return_value=requests),
              patch.object(large, "access_token", return_value="private-token"),
              patch.object(large, "encrypt_token", return_value="encrypted-copy-state")):
            large.transfer(row, bot, db, maximum=source.size)
        self.assertEqual(source.reads, [])
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["bytes_done"], source.size)
        self.assertEqual(row["result_file_id"], "copied_file_123")
        self.assertEqual(requests.post.call_count, 1)
        self.assertIn("appProperties", requests.post.call_args.kwargs["json"])

    def test_copy_resume_only_looks_up_existing_copy_not_double_posts(self):
        source = FakeSource(200)
        source.ref = "fileId_1234"
        row = job(ciphertext="persisted-copy")
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        requests = Mock()
        with (patch.object(large, "GoogleSource", return_value=source),
              patch.object(large, "decrypt_token", return_value={"mode": "copy", "version": "drive:7", "size": 200}),
              patch.object(large, "_existing_drive_copy", return_value={"id": "prior_copy_1"}),
              patch.object(large, "_requests", return_value=requests)):
            large.transfer(row, Mock(), db, maximum=1024)
        requests.post.assert_not_called()
        self.assertEqual(row["status"], "completed")

    def test_uncertain_drive_copy_stays_needs_review_without_resending(self):
        source = FakeSource(200)
        source.ref = "fileId_1234"
        row = job(ciphertext="persisted-copy")
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        requests = Mock()
        with (patch.object(large, "GoogleSource", return_value=source),
              patch.object(large, "decrypt_token", return_value={"mode": "copy", "version": "drive:7", "size": 200}),
              patch.object(large, "_existing_drive_copy", return_value=None),
              patch.object(large, "_requests", return_value=requests)):
            large.transfer(row, Mock(), db, maximum=1024)
        self.assertEqual(row["status"], "needs_review")
        requests.post.assert_not_called()
        self.assertEqual(row["upload_state_ciphertext"], "persisted-copy")

    def test_changed_https_source_never_reuses_old_upload_session(self):
        source = FakeSource(200)
        source.version = '"changed"'
        row = job(ciphertext="encrypted-session")
        row.update(source_kind="url", source_provider=None, source_ref="https://example.org/x")
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        with (patch.object(large, "HttpsSource", return_value=source),
              patch.object(large, "_put_chunk") as put):
            large.transfer(row, Mock(), db, maximum=1024)
        self.assertEqual(row["status"], "needs_review")
        put.assert_not_called()

    def test_pausing_and_resuming_google_upload(self):
        row = job(ciphertext="encrypted-session")
        row["status"] = "running"
        row["source_kind"] = "url"
        row["source_provider"] = None
        row["source_ref"] = "https://example.org/a.bin"
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        with patch.dict(os.environ, {"CLOUDBRIDGE_V136_ENABLED": "true"}):
            core.update_job(101, row["id"], "pause", db)
        self.assertTrue(row["pause_requested"])
        large.transfer(row, Mock(), db, maximum=400)
        self.assertEqual(row["status"], "paused")
        self.assertEqual(row["upload_state_ciphertext"], "encrypted-session")
        self.assertEqual(core.update_job(101, row["id"], "resume", db)["status"], "queued")

    def test_atomic_google_copy_cannot_be_paused(self):
        row = job()
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        with patch.dict(os.environ, {"CLOUDBRIDGE_V136_ENABLED": "true"}):
            with self.assertRaisesRegex(core.BridgeError, "Pause is available"):
                core.update_job(101, row["id"], "pause", db)

    def test_stale_worker_cannot_overwrite_new_worker(self):
        row = job()
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        old = dict(row)
        row["worker"] = "other-worker"
        with self.assertRaises(large.LostLease):
            large._check(old, db)
        with self.assertRaises(large.LostLease):
            large._set(old, db, status="completed")
        self.assertEqual(row["status"], "running")

    def test_cancel_during_large_upload_requires_review(self):
        row = job(ciphertext="encrypted-session")
        row["cancel_requested"] = True
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        large.transfer(row, Mock(), db, maximum=200)
        self.assertEqual(row["status"], "needs_review")
        self.assertEqual(row["upload_state_ciphertext"], "encrypted-session")

    def test_provider_dispatch_only_google_destination(self):
        row = job()
        with (patch.dict(os.environ, {"CLOUDBRIDGE_V136_ENABLED": "true"}),
              patch.object(large, "transfer") as transfer):
            worker.execute_job(row, Mock(), FakeDb())
        transfer.assert_called_once()

    def test_retry_requires_saved_google_session_and_owner(self):
        row = job(ciphertext="encrypted-session")
        row["status"] = "needs_review"
        row["bytes_done"] = 456
        db = FakeDb()
        db.data["cloudbridge_jobs_v134"] = [row]
        self.assertIsNone(core.update_job(202, row["id"], "retry", db))
        with patch.dict(os.environ, {"CLOUDBRIDGE_V136_ENABLED": "false"}):
            with self.assertRaises(core.BridgeError):
                core.update_job(101, row["id"], "retry", db)
        with patch.dict(os.environ, {"CLOUDBRIDGE_V136_ENABLED": "true"}):
            self.assertEqual(core.update_job(101, row["id"], "retry", db)["status"], "queued")
        self.assertEqual(row["bytes_done"], 456)


class CopyCommandTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        self.handlers = {}
        class Bot:
            def __init__(self, owner):
                self.owner = owner
                self.copy_message = Mock()
                self.send_message = Mock()
                self.get_chat = Mock(return_value=types.SimpleNamespace(type="channel"))
                self.get_me = Mock(return_value=types.SimpleNamespace(id=303))
                self.get_chat_member = Mock(side_effect=lambda dest, uid: types.SimpleNamespace(
                    status="administrator", can_post_messages=True))
            def message_handler(self, **kw):
                def register(fn):
                    for command in kw.get("commands", []):
                        self.owner.handlers[command] = fn
                    return fn
                return register
        self.bot = Bot(self)
        self.app = Flask(__name__)
        with patch.object(worker, "start_worker", return_value=False):
            web.register_cloudbridge(self.app, self.bot)

    @staticmethod
    def message(uid=101, private=True, media=True):
        return types.SimpleNamespace(chat=types.SimpleNamespace(id=uid, type="private" if private else "channel"),
            from_user=types.SimpleNamespace(id=uid), text="/cloudcopy",
            reply_to_message=types.SimpleNamespace(message_id=21, document=Mock() if media else None))

    def test_copy_only_from_own_private_chat(self):
        with patch.dict(os.environ, {"CLOUDBRIDGE_V134_ENABLED": "true"}):
            self.handlers["cloudcopy"](self.message())
            self.bot.copy_message.assert_called_once_with(chat_id=101, from_chat_id=101, message_id=21)
            self.bot.copy_message.reset_mock()
            self.handlers["cloudcopy"](self.message(private=False))
            self.handlers["cloudcopy"](types.SimpleNamespace(
                **{**vars(self.message()), "from_user": types.SimpleNamespace(id=202)}))
            self.assertFalse(self.bot.copy_message.called)

    def test_copy_requires_reply_to_media(self):
        with patch.dict(os.environ, {"CLOUDBRIDGE_V134_ENABLED": "true"}):
            self.handlers["cloudcopy"](self.message(media=False))
        self.bot.copy_message.assert_not_called()
        self.bot.send_message.assert_called_once()

    def test_copy_to_channel_requires_both_admins(self):
        msg = self.message()
        msg.text = "/cloudcopy @mychannel"
        with patch.dict(os.environ, {"CLOUDBRIDGE_V134_ENABLED": "true"}):
            self.handlers["cloudcopy"](msg)
        self.bot.copy_message.assert_called_once_with(
            chat_id="@mychannel", from_chat_id=101, message_id=21)
        self.bot.send_message.assert_called_once()

    def test_copy_blocks_other_peoples_channels(self):
        msg = self.message()
        msg.text = "/cloudcopy @notmychannel"
        self.bot.get_chat_member.side_effect = lambda dest, uid: types.SimpleNamespace(
            status="member" if uid == 101 else "administrator", can_post_messages=True)
        with patch.dict(os.environ, {"CLOUDBRIDGE_V134_ENABLED": "true"}):
            self.handlers["cloudcopy"](msg)
        self.bot.copy_message.assert_not_called()
        self.assertIn("admin", self.bot.send_message.call_args.args[1])

    def test_copy_blocks_private_target_and_bot_without_post_rights(self):
        msg = self.message()
        msg.text = "/cloudcopy -100123456789"
        self.bot.get_chat.return_value = types.SimpleNamespace(type="private")
        with patch.dict(os.environ, {"CLOUDBRIDGE_V134_ENABLED": "true"}):
            self.handlers["cloudcopy"](msg)
        self.bot.copy_message.assert_not_called()
        self.bot.get_chat.return_value = types.SimpleNamespace(type="channel")
        self.bot.get_chat_member.side_effect = lambda dest, uid: types.SimpleNamespace(
            status="administrator", can_post_messages=uid == 101)
        with patch.dict(os.environ, {"CLOUDBRIDGE_V134_ENABLED": "true"}):
            self.handlers["cloudcopy"](msg)
        self.bot.copy_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()

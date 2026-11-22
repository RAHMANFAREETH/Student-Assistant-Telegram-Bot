"""Run: python -m unittest TEST_CLOUDBRIDGE_V134 -v

Offline tests: no Telegram network access, no Supabase credentials or live OAuth.
"""
import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import quote, urlencode
from uuid import uuid4

import cloudbridge_v134 as web
import cloudbridge_v134_core as core
import cloudbridge_v134_worker as worker


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.filters, self.action, self.payload = [], "select", None
        self.count = None

    def select(self, *_args, **_kwargs):return self
    def eq(self, key, value):self.filters.append((key, value));return self
    def order(self, *_args, **_kwargs):return self
    def limit(self, *_args, **_kwargs):return self
    def insert(self, value):self.action, self.payload = "insert", value;return self
    def upsert(self, value, **_kwargs):self.action, self.payload = "upsert", value;return self
    def update(self, value):self.action, self.payload = "update", value;return self
    def delete(self):self.action = "delete";return self

    def execute(self):
        rows = self.db.data.setdefault(self.table, [])
        matches = [r for r in rows if all(r.get(k) == v for k, v in self.filters)]
        if self.action == "insert":
            record = dict(self.payload);rows.append(record)
            return Mock(data=[record])
        if self.action == "upsert":
            record = dict(self.payload)
            for row in rows:
                if row.get("user_id") == record.get("user_id") and row.get("provider") == record.get("provider"):
                    row.update(record);return Mock(data=[row])
            rows.append(record);return Mock(data=[record])
        if self.action == "update":
            for row in matches:row.update(self.payload)
            return Mock(data=matches)
        if self.action == "delete":
            for row in matches:rows.remove(row)
            return Mock(data=matches)
        return Mock(data=matches)


class FakeDb:
    def __init__(self):self.data={}
    def table(self, name):return FakeQuery(self,name)
    def rpc(self, name, params):
        if name == "cloudbridge_consume_oauth_v134":
            rows = self.data.get("cloudbridge_oauth_states_v134", [])
            matches = [r for r in rows if r["state_hash"] == params["p_hash"]]
            for row in matches:rows.remove(row)
            return Mock(execute=lambda:Mock(data=matches))
        if name == "cloudbridge_claim_job_v134":
            queued = [r for r in self.data.get("cloudbridge_jobs_v134", []) if r.get("status") == "queued"]
            if queued:queued[0]["status"]="running"
            return Mock(execute=lambda:Mock(data=queued[:1]))
        raise AssertionError(name)


def signed_init_data(uid=101, key="test-token", now=None):
    stamp = str(now or int(time.time()))
    data = {"auth_date": stamp, "user": json.dumps({"id": uid}, separators=(",", ":"))}
    check = "\n".join(f"{k}={v}" for k,v in sorted(data.items()))
    secret = hmac.new(b"WebAppData",key.encode(),hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


class FakeBot:
    def message_handler(self, **_kwargs):return lambda fn:fn
    def send_message(self, *_args, **_kwargs):pass


class CoreTests(unittest.TestCase):
    def make_body(self, **changes):
        item={"id":str(uuid4()), "source":{"kind":"provider","provider":"dropbox","ref":"/my.pdf"},
              "destination":{"kind":"telegram"}, "filename":"my.pdf"}
        item.update(changes)
        return item

    def test_valid_cloud_to_telegram(self):
        item=core.validate_job(self.make_body())
        self.assertEqual(item["source_provider"],"dropbox")
        self.assertEqual(item["destination_kind"],"telegram")

    def test_invalid_file_names_and_paths(self):
        for name in ("../bad", "x/y", "", "a\x00b", "a"*161):
            with self.subTest(name=name), self.assertRaises(core.BridgeError):
                core.safe_filename(name)
        for path in ("/x/../b","/a//b", "\\windows", "", "/a/./b"):
            with self.subTest(path=path), self.assertRaises(core.BridgeError):
                core.safe_cloud_path(path)

    def test_source_and_destination_must_be_well_formed(self):
        with self.assertRaises(core.BridgeError):
            core.validate_job(self.make_body(source={"kind":"telegram","ref":"file"},destination={"kind":"telegram"}))
        with self.assertRaises(core.BridgeError):
            core.validate_job(self.make_body(destination={"kind":"provider","provider":"unknown","path":"/a"}))
        with self.assertRaises(core.BridgeError):
            core.validate_job(self.make_body(source={"kind":"url","ref":"http://example.org/a"}))
        with self.assertRaises(core.BridgeError):
            core.validate_job(self.make_body(destination={"kind":"telegram","path":"/other-user"}))

    def test_private_ipv4_ipv6_and_ip_literal_blocked(self):
        for address in ("127.0.0.1","10.0.0.1","172.16.1.2","192.168.1.3","169.254.169.254","::1","fc00::1"):
            with self.subTest(ip=address):
                with patch.object(core.socket,"getaddrinfo", return_value=[(2,1,6,"",(address,443))]):
                    with self.assertRaises(core.BridgeError):
                        core.validated_https_url("https://example.org/file")
        with self.assertRaises(core.BridgeError):
            core.validated_https_url("https://127.0.0.1/file")

    def test_https_pinned_public_destination(self):
        with patch.object(core.socket,"getaddrinfo",return_value=[(2,1,6,"",("8.8.8.8",443))]):
            self.assertEqual(core.validated_https_url("https://example.org/a")[1],["8.8.8.8"])
        for value in ("https://user:pass@example.com/a","http://example.com/a","https://example.com:8443/a","https://foo/a","https://example.com/a#b"):
            with self.subTest(url=value),self.assertRaises(core.BridgeError):core.validated_https_url(value)

    def test_account_isolation_and_idempotency(self):
        db=FakeDb();body=self.make_body()
        job,fresh=core.create_job(101,body,db)
        self.assertTrue(fresh)
        self.assertEqual(job["id"],body["id"])
        same,fresh=core.create_job(101,body,db)
        self.assertFalse(fresh)
        self.assertEqual(len(core.list_jobs(101,db)),1)
        self.assertEqual(core.list_jobs(202,db),[])
        self.assertIsNone(core.update_job(202,body["id"],"cancel",db))
        self.assertEqual(db.data["cloudbridge_jobs_v134"][0]["status"],"queued")
        core.update_job(101,body["id"],"cancel",db)
        self.assertEqual(db.data["cloudbridge_jobs_v134"][0]["status"],"cancelled")

    def test_review_is_not_silently_retried(self):
        db=FakeDb();body=self.make_body()
        core.create_job(3,body,db)
        row=db.data["cloudbridge_jobs_v134"][0]
        row["status"]="needs_review"
        with self.assertRaises(core.BridgeError):core.update_job(3,body["id"],"retry",db)

    def test_completed_history_can_be_deleted_only_by_owner(self):
        db=FakeDb();body=self.make_body()
        core.create_job(6,body,db)
        row=db.data["cloudbridge_jobs_v134"][0]
        self.assertIsNone(core.update_job(9,body["id"],"delete",db))
        with self.assertRaises(core.BridgeError):core.update_job(6,body["id"],"delete",db)
        row["status"]="completed"
        self.assertEqual(core.update_job(6,body["id"],"delete",db)["status"],"deleted")
        self.assertEqual(core.list_jobs(6,db),[])

    def test_token_encryption(self):
        from cryptography.fernet import Fernet
        with patch.dict(os.environ,{"CLOUDBRIDGE_FERNET_KEY":Fernet.generate_key().decode()}):
            original={"access_token":"secret","refresh_token":"very-secret","expires_at":123456}
            encrypted=core.encrypt_token(original)
            self.assertNotIn("very-secret",encrypted)
            self.assertEqual(core.decrypt_token(encrypted),original)


class WebTests(unittest.TestCase):
    def setUp(self):
        from flask import Flask
        self.db=FakeDb()
        self.patch_env=patch.dict(os.environ,{"CLOUDBRIDGE_V134_ENABLED":"true","BOT_TOKEN":"test-token"})
        self.patch_env.start()
        self.patch_db=patch.object(web,"database",return_value=self.db)
        self.patch_db.start()
        self.patch_core_db=patch.object(core,"database",return_value=self.db)
        self.patch_core_db.start()
        self.app=Flask(__name__)
        web.register_cloudbridge(self.app,FakeBot())
        self.client=self.app.test_client()

    def tearDown(self):
        self.patch_core_db.stop();self.patch_db.stop();self.patch_env.stop()

    def h(self,uid=101):return {"X-Telegram-Init-Data":signed_init_data(uid)}

    def test_unsigned_and_tampered_sessions_rejected(self):
        self.assertEqual(self.client.get("/cloud/api/session").status_code,401)
        self.assertEqual(self.client.get("/cloud/api/session",headers={"X-Telegram-Init-Data":signed_init_data(102)[:-2]+"xx"}).status_code,401)

    def test_valid_signed_sessions_allow_all_ages(self):
        resp=self.client.get("/cloud/api/session",headers=self.h(101))
        self.assertEqual(resp.status_code,200)
        self.assertEqual(resp.json["user_id"],101)

    def test_cross_account_http_isolation(self):
        job=CoreTests().make_body()
        resp=self.client.post("/cloud/api/jobs",headers=self.h(101),json=job)
        self.assertEqual(resp.status_code,201)
        others=self.client.get("/cloud/api/jobs",headers=self.h(202))
        self.assertEqual(others.json["jobs"],[])
        deny=self.client.post("/cloud/api/jobs/"+job["id"]+"/cancel",headers=self.h(202),json={})
        self.assertEqual(deny.status_code,404)

    def test_disabled_returns_404(self):
        with patch.dict(os.environ,{"CLOUDBRIDGE_V134_ENABLED":"false"}):
            self.assertEqual(self.client.get("/cloud").status_code,404)

    def test_oauth_state_is_random_and_hashed(self):
        a,ah=core.new_oauth_state();b,bh=core.new_oauth_state()
        self.assertNotEqual(a,b);self.assertNotEqual(ah,bh)
        self.assertEqual(ah,hashlib.sha256(a.encode()).hexdigest())

    def test_oauth_start_uses_signed_owner_and_hashed_state(self):
        with patch.object(web,"authorization_url",side_effect=lambda name,state:"https://accounts.example/authorize?state="+state):
            response=self.client.post("/cloud/api/oauth/google/start",headers=self.h(101),json={})
        self.assertEqual(response.status_code,200)
        state=self.db.data["cloudbridge_oauth_states_v134"][0]
        self.assertEqual(state["user_id"],101)
        self.assertEqual(state["provider"],"google")
        self.assertNotIn(state["state_hash"],response.json["url"])
        self.assertEqual(len(state["state_hash"]),64)

    def test_oauth_callback_state_one_time_and_scoped(self):
        raw,digest=core.new_oauth_state()
        self.db.data["cloudbridge_oauth_states_v134"]=[{"user_id":101,"provider":"dropbox","state_hash":digest}]
        with patch.object(web,"exchange_code",return_value={"access_token":"secret-token"}),patch.object(web,"encrypt_token",return_value="ciphertext-only"):
            first=self.client.get("/cloud/oauth/callback",query_string={"state":raw,"code":"valid-code"})
            second=self.client.get("/cloud/oauth/callback",query_string={"state":raw,"code":"valid-code"})
        self.assertEqual(first.status_code,303)
        self.assertEqual(second.status_code,400)
        row=self.db.data["cloudbridge_accounts_v134"][0]
        self.assertEqual(row["user_id"],101)
        self.assertEqual(row["tokens_ciphertext"],"ciphertext-only")


class WorkerTests(unittest.TestCase):
    def test_provider_output_belongs_to_signed_job_user(self):
        db=FakeDb();uid=101
        row={"id":str(uuid4()),"user_id":uid,"source_kind":"url","source_ref":"https://example.org/sample.pdf",
             "destination_kind":"provider","destination_provider":"dropbox","destination_path":"/notes/sample.pdf",
             "filename":"sample.pdf","status":"running","cancel_requested":False}
        db.data["cloudbridge_jobs_v134"]=[row]
        def download(_url,handle,_limit,_cancel):handle.write(b"DATA");return 4
        output=[]
        def upload(uid,name,target,filename,handle,length,_db,_cancel):
            output.append((uid,name,target,filename,handle.read(),length))
        with patch.object(worker,"download_https",side_effect=download),patch.object(worker,"upload_provider",side_effect=upload):
            worker.execute_job(row,Mock(),db)
        self.assertEqual(output,[(101,"dropbox","/notes/sample.pdf","sample.pdf",b"DATA",4)])
        self.assertEqual(row["status"],"completed")

    def test_ambiguous_upload_error_requires_review(self):
        db=FakeDb();row={"id":str(uuid4()),"user_id":101,"source_kind":"url","source_ref":"https://example.org/a",
            "destination_kind":"provider","destination_provider":"dropbox","destination_path":"/a",
            "filename":"a","status":"running","cancel_requested":False}
        db.data["cloudbridge_jobs_v134"]=[row]
        def download(_url,handle,_limit,_cancel):handle.write(b"A");return 1
        with patch.object(worker,"download_https",side_effect=download),patch.object(worker,"upload_provider",side_effect=RuntimeError("sensitive-token")):
            worker.execute_job(row,Mock(),db)
        self.assertEqual(row["status"],"needs_review")
        self.assertNotIn("sensitive-token",str(row))


if __name__=="__main__":unittest.main()

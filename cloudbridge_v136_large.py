"""V13.6 bounded-memory, resumable Google Drive transfers.

Google Drive/HTTPS source -> Google Drive destination. No large temporary file,
no shared credentials and no public sharing of Drive documents. Sessions are
encrypted in Supabase so a new worker can resume a crashed upload by querying
Google for its confirmed offset. Requires SQL_CLOUDBRIDGE_V136.sql first.
"""
from __future__ import annotations

import os
import re
import time
from urllib.parse import parse_qs, quote, urljoin, urlsplit

from cloudbridge_v134_core import (BridgeError, decrypt_token, encrypt_token,
                                   safe_cloud_path, validated_https_url)
from cloudbridge_v134_providers import access_token

CHUNK = 5 * 1024 * 1024  # 256-KiB aligned; ~5 MiB RAM per active transfer
MAX_LIMIT = 4096 * 1024 * 1024
_RANGE = re.compile(r"^bytes (\d+)-(\d+)/(\d+)$")
_ACK = re.compile(r"^bytes=0-(\d+)$")
_DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{4,256}$")


class Cancelled(Exception):
    """The authenticated owner requested cancellation."""


class Paused(Exception):
    """The owner paused the upload at its last acknowledged byte."""


class LostLease(Exception):
    """A different worker has taken ownership; do not mutate its job."""


def enabled():
    return os.getenv("CLOUDBRIDGE_V136_ENABLED", "false").lower() in {"true", "1", "yes", "on"}


def _requests():
    import requests
    return requests


def _json(response, label):
    try:
        value = response.json()
    except (ValueError, AttributeError):
        raise BridgeError(label + " returned invalid metadata.") from None
    if not isinstance(value, dict):
        raise BridgeError(label + " returned invalid metadata.")
    return value


def _range_check(headers, start, length, total):
    if headers.get("Content-Encoding", "identity").lower() != "identity":
        raise BridgeError("Compressed range responses are not supported.")
    match = _RANGE.fullmatch(headers.get("Content-Range", ""))
    if not match or (int(match[1]), int(match[2]), int(match[3])) != (
            start, start + length - 1, total):
        raise BridgeError("Source returned an incorrect byte range; transfer stopped.")


def _read_response(response, amount):
    output = bytearray()
    for piece in response.iter_content(256 * 1024):
        if piece:
            output.extend(piece)
            if len(output) > amount:
                raise BridgeError("Source sent more data than requested.")
    if len(output) != amount:
        raise BridgeError("Source returned an incomplete byte range.")
    return bytes(output)


class GoogleSource:
    def __init__(self, uid, ref, db):
        if not isinstance(ref, str) or not _DRIVE_ID.fullmatch(ref):
            raise BridgeError("Invalid Google Drive file ID.")
        self.uid, self.ref, self.db = uid, ref, db
        self.url = "https://www.googleapis.com/drive/v3/files/" + quote(ref, safe="")
        self.token = access_token(uid, "google", db)
        self.refreshed = time.monotonic()
        self.size, self.version = self._metadata()

    def _auth(self):
        if time.monotonic() - self.refreshed > 2400:
            self.token = access_token(self.uid, "google", self.db)
            self.refreshed = time.monotonic()
        return {"Authorization": "Bearer " + self.token, "Accept-Encoding": "identity"}

    def _metadata(self):
        response = _requests().get(self.url, params={"fields": "id,size,mimeType,version,capabilities(canDownload,canCopy)"},
                                   headers=self._auth(), timeout=(8, 30), allow_redirects=False)
        if response.status_code != 200:
            raise BridgeError("Google Drive source metadata unavailable.")
        item = _json(response, "Drive metadata")
        self.can_copy = (item.get("capabilities") or {}).get("canCopy", True)
        if item.get("mimeType", "").startswith("application/vnd.google-apps."):
            raise BridgeError("Export Google Docs to DOCX or PDF before a large transfer.")
        if (item.get("capabilities") or {}).get("canDownload") is False:
            raise BridgeError("This Drive file cannot be downloaded.")
        try:
            size = int(item["size"])
        except (KeyError, ValueError, TypeError):
            raise BridgeError("Drive did not supply file size.") from None
        version = str(item.get("version", ""))
        if not version or not version.isdecimal():
            raise BridgeError("Drive did not supply a stable file version.")
        return size, "drive:" + version

    def verify_version(self):
        size, version = self._metadata()
        if (size, version) != (self.size, self.version):
            raise BridgeError("Source file changed during transfer; check destination.")

    def read_range(self, start, amount):
        headers = {**self._auth(), "Range": f"bytes={start}-{start + amount - 1}"}
        response = _requests().get(self.url, params={"alt": "media"}, headers=headers,
                                   stream=True, timeout=(8, 90), allow_redirects=False)
        try:
            if response.status_code != 206:
                raise BridgeError("Drive refused partial download (HTTP " + str(response.status_code) + ").")
            _range_check(response.headers, start, amount, self.size)
            return _read_response(response, amount)
        finally:
            response.close()


def _https_range(url, start, amount, *, expected_total=None, expected_tag=None):
    """Pinned HTTPS byte range; revalidate DNS+TLS for every range and redirect."""
    import urllib3
    visited = set()
    for _ in range(4):
        url, addresses = validated_https_url(url)
        if url in visited:
            raise BridgeError("Circular HTTPS redirect.")
        visited.add(url)
        parsed = urlsplit(url)
        pool = urllib3.HTTPSConnectionPool(
            host=addresses[0], port=443, server_hostname=parsed.hostname,
            assert_hostname=parsed.hostname, retries=False, maxsize=1,
            timeout=urllib3.Timeout(connect=8, read=90))
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        response = None
        try:
            headers = {"Host": parsed.hostname, "Accept-Encoding": "identity",
                       "Range": f"bytes={start}-{start + amount - 1}",
                       "User-Agent": "StudentAssistantCloudBridge/13.6"}
            if expected_tag:
                headers["If-Match"] = expected_tag
            response = pool.request("GET", path, headers=headers, redirect=False,
                                    preload_content=False)
            if response.status in (301, 302, 303, 307, 308):
                next_url = response.headers.get("Location", "")
                if not next_url:
                    raise BridgeError("HTTPS source redirect missing location.")
                url = urljoin(url, next_url)
                continue
            if response.status != 206:
                raise BridgeError("HTTPS source must support byte ranges (HTTP " + str(response.status) + ").")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise BridgeError("Compressed HTTPS source is not supported.")
            tag = response.headers.get("ETag", "")
            if not tag or tag.startswith("W/") or (expected_tag and tag != expected_tag):
                raise BridgeError("HTTPS source must supply an unchanged strong ETag.")
            match = _RANGE.fullmatch(response.headers.get("Content-Range", ""))
            if not match or int(match[1]) != start or int(match[2]) != start + amount - 1:
                raise BridgeError("HTTPS source returned an incorrect byte range.")
            total = int(match[3])
            if expected_total is not None and total != expected_total:
                raise BridgeError("HTTPS source size changed during transfer.")
            result = bytearray()
            while len(result) < amount:
                block = response.read(min(256 * 1024, amount - len(result) + 1), decode_content=False)
                if not block:
                    break
                result.extend(block)
                if len(result) > amount:
                    raise BridgeError("HTTPS source sent too many bytes.")
            if len(result) != amount or response.read(1, decode_content=False):
                raise BridgeError("HTTPS source byte range was truncated or oversized.")
            return total, tag, bytes(result)
        finally:
            if response is not None:
                response.release_conn()
            pool.close()
    raise BridgeError("Too many HTTPS redirects.")


class HttpsSource:
    def __init__(self, url):
        self.url = url
        self.size, self.version, _ = _https_range(url, 0, 1)

    def read_range(self, start, amount):
        _, _, content = _https_range(self.url, start, amount,
                                     expected_total=self.size, expected_tag=self.version)
        return content

    def verify_version(self):
        _https_range(self.url, 0, 1, expected_total=self.size, expected_tag=self.version)


def _upload_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "www.googleapis.com"
            or parsed.path != "/upload/drive/v3/files" or parsed.fragment
            or parse_qs(parsed.query).get("uploadType") != ["resumable"] or len(url) > 8192):
        raise BridgeError("Unexpected Drive resumable upload URL.")
    return url


def _upload_session(uid, path, size, db):
    safe_cloud_path(path)
    if path.count("/") != 1:
        raise BridgeError("Google Drive uploads currently support root-level files.")
    token = access_token(uid, "google", db)
    response = _requests().post(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,name,webViewLink",
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Length": str(size),
                 "X-Upload-Content-Type": "application/octet-stream"},
        json={"name": path.lstrip("/")}, timeout=(8, 30), allow_redirects=False)
    if response.status_code not in (200, 201):
        raise BridgeError("Drive upload session could not be created.")
    return _upload_url(response.headers.get("Location", ""))


def _confirmed_offset(url, size):
    response = _requests().put(_upload_url(url), data=b"",
                               headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"},
                               timeout=(8, 35), allow_redirects=False)
    if response.status_code in (200, 201):
        return size, _json(response, "Drive completion")
    if response.status_code != 308:
        raise BridgeError("Drive upload session could not resume. Check the destination before retrying.")
    range_header = response.headers.get("Range", "")
    if not range_header:
        return 0, None
    match = _ACK.fullmatch(range_header)
    if not match or not 0 <= int(match[1]) < size:
        raise BridgeError("Drive returned an invalid resume offset.")
    return int(match[1]) + 1, None


def _put_chunk(url, size, offset, content):
    end = offset + len(content) - 1
    response = _requests().put(
        _upload_url(url), data=content, timeout=(8, 180), allow_redirects=False,
        headers={"Content-Length": str(len(content)),
                 "Content-Range": f"bytes {offset}-{end}/{size}"})
    if response.status_code in (200, 201):
        if end + 1 != size:
            raise BridgeError("Drive completed an upload before all bytes were sent.")
        return size, _json(response, "Drive completion")
    if response.status_code == 308:
        match = _ACK.fullmatch(response.headers.get("Range", ""))
        if not match or not offset < int(match[1]) + 1 <= end + 1:
            raise BridgeError("Drive did not confirm the uploaded chunk.")
        return int(match[1]) + 1, None
    raise BridgeError("Drive chunk upload failed (HTTP " + str(response.status_code) + ").")


def _check(row, db):
    rows = (db.table("cloudbridge_jobs_v134").select("worker,status,cancel_requested,pause_requested")
            .eq("user_id", row["user_id"]).eq("id", row["id"]).limit(1).execute()).data or []
    if not rows or rows[0].get("worker") != row.get("worker") or rows[0].get("status") != "running":
        raise LostLease()
    if rows[0].get("cancel_requested"):
        raise Cancelled()
    if rows[0].get("pause_requested"):
        raise Paused()


def _set(row, db, **values):
    query = (db.table("cloudbridge_jobs_v134").update(values)
             .eq("user_id", row["user_id"]).eq("id", row["id"]).eq("status", "running"))
    if row.get("worker") is not None:
        query = query.eq("worker", row["worker"])
    if not (query.execute().data or []):
        raise LostLease()
    row.update(values)


def _file_id(metadata):
    value = metadata.get("id", "")
    if not isinstance(value, str) or not _DRIVE_ID.fullmatch(value):
        raise BridgeError("Drive finished, but file ID is missing. Check Drive before retrying.")
    return value


def _complete(row, bot, db, src, metadata):
    src.verify_version()
    file_id = _file_id(metadata)
    _set(row, db, status="completed", error_code=None, bytes_done=src.size,
         total_bytes=src.size, result_file_id=file_id, stage="completed",
         upload_state_ciphertext=None)
    try:
        bot.send_message(row["user_id"], "✅ CloudBridge completed: " + row["filename"] +
                         "\n🔒 Your private Google Drive file:\n" +
                         "https://drive.google.com/file/d/" + quote(file_id, safe="") + "/view")
    except Exception:
        pass  # A failed notice cannot turn an existing remote file into failure.


def _existing_drive_copy(row, db):
    """Find a previously completed server-side copy after a worker crashed."""
    token = access_token(row["user_id"], "google", db)
    # ID originates from our UUID validator/SQL uuid column, never free text.
    ident = str(row["id"])
    from uuid import UUID
    if ident != str(UUID(ident)):
        raise BridgeError("Invalid copy job ID.")
    response = _requests().get("https://www.googleapis.com/drive/v3/files",
        headers={"Authorization": "Bearer " + token}, timeout=(8, 30),
        params={"q": "appProperties has { key='cloudbridgeJob' and value='" + ident + "' } and trashed = false",
                "fields": "nextPageToken,files(id,name)", "pageSize": 2}, allow_redirects=False)
    if response.status_code != 200:
        raise BridgeError("Drive could not check for an existing copy.")
    value = _json(response, "Drive copy lookup")
    files = value.get("files") or []
    if not isinstance(files, list) or len(files) > 1 or value.get("nextPageToken"):
        raise BridgeError("Multiple Drive copies found; review destination.")
    return files[0] if files else None


def _copy_google(row, bot, db, src, *, maximum):
    """4 GiB Drive-to-same-Drive copies run entirely on Google's servers.

    Persist a private appProperties marker before the request; on restart we
    search for that marker. A sent-but-unconfirmed copy is NEVER sent twice.
    """
    from datetime import datetime, timezone
    sent = bool(row.get("upload_state_ciphertext"))
    try:
        _check(row, db)
        if not 0 < src.size <= min(maximum, MAX_LIMIT):
            raise BridgeError("File exceeds the configured transfer limit.")
        if getattr(src, "can_copy", True) is False:
            raise BridgeError("Google Drive does not permit copying this file.")
        if row.get("source_version") and row["source_version"] != src.version:
            raise BridgeError("Source changed since the copy began.")
        safe_cloud_path(row["destination_path"])
        if row["destination_path"].count("/") != 1:
            raise BridgeError("Drive copies currently support root-level destinations.")
        if sent:
            state = decrypt_token(row["upload_state_ciphertext"])
            if state.get("mode") != "copy" or state.get("version") != src.version:
                raise BridgeError("Copy state changed; review destination.")
        existing = _existing_drive_copy(row, db)
        if existing:
            _complete(row, bot, db, src, existing)
            return
        if sent:
            raise BridgeError("Copy may have completed but is not indexed yet. Check Drive before retrying.")
        # On a crash between marker persistence and HTTP POST, the user must
        # review/restart manually. That's preferable to duplicate private files.
        _set(row, db, stage="copy", total_bytes=src.size, source_version=src.version,
             upload_state_ciphertext=encrypt_token({"mode": "copy", "version": src.version, "size": src.size}),
             claimed_at=datetime.now(timezone.utc).isoformat())
        sent = True
        _check(row, db)
        token = access_token(row["user_id"], "google", db)
        response = _requests().post(
            "https://www.googleapis.com/drive/v3/files/" + quote(src.ref, safe="") + "/copy",
            params={"fields": "id,name", "ignoreDefaultVisibility": "true"},
            headers={"Authorization": "Bearer " + token},
            json={"name": row["destination_path"].lstrip("/"), "parents": ["root"],
                  "appProperties": {"cloudbridgeJob": str(row["id"])}},
            timeout=(8, 180), allow_redirects=False)
        if response.status_code not in (200, 201):
            raise BridgeError("Google Drive server-side copy failed. Check Drive before retrying.")
        _complete(row, bot, db, src, _json(response, "Drive copy"))
    except LostLease:
        pass
    except Paused:
        try:
            _set(row, db, status="paused", pause_requested=False, error_code=None)
        except LostLease:
            pass
    except Cancelled:
        try:
            _set(row, db, status="needs_review" if sent else "cancelled",
                 error_code="cancelled_copy")
        except LostLease:
            pass
    except BridgeError as exc:
        try:
            _set(row, db, status="needs_review" if sent else "failed", error_code=str(exc)[:180])
        except LostLease:
            pass
    except Exception:
        try:
            _set(row, db, status="needs_review" if sent else "failed", error_code="transfer_error_copy")
        except LostLease:
            pass


def transfer(row, bot, db, *, maximum):
    """Execute one claimed job. A crashed process resumes using the same URL."""
    import datetime as dt
    uid = int(row["user_id"])
    upload_started = bool(row.get("upload_state_ciphertext"))
    try:
        _check(row, db)
        if not upload_started and row.get("stage") in (None, "preparing"):
            # No remote write has occurred yet. Explicitly mark this phase so
            # a restarted worker can safely reclaim it after a process crash.
            _set(row, db, stage="preparing",
                 claimed_at=dt.datetime.now(dt.timezone.utc).isoformat())
        kind = row["source_kind"]
        if kind == "provider" and row.get("source_provider") == "google":
            src = GoogleSource(uid, row["source_ref"], db)
        elif kind == "url":
            src = HttpsSource(row["source_ref"])
        else:
            raise BridgeError("Large transfers support Google Drive or HTTPS sources only.")
        if kind == "provider" and row.get("source_provider") == "google":
            # If an older resumable-streaming session already exists, finish
            # it instead of initiating a second Google Drive copy.
            secret = row.get("upload_state_ciphertext")
            if not secret or decrypt_token(secret).get("mode") == "copy":
                _copy_google(row, bot, db, src, maximum=maximum)
                return
        if not 0 < src.size <= min(maximum, MAX_LIMIT):
            raise BridgeError("File exceeds the configured transfer limit.")
        prior = row.get("source_version")
        if prior and prior != src.version:
            raise BridgeError("Source file changed since upload began. Check destination.")
        _check(row, db)
        secret = row.get("upload_state_ciphertext")
        if secret:
            state = decrypt_token(secret)
            if state.get("version") != src.version or state.get("size") != src.size:
                raise BridgeError("Upload source changed. Check the destination.")
            url = _upload_url(state.get("url", ""))
            offset, result = _confirmed_offset(url, src.size)
        else:
            # First commit metadata; then persist the preauthenticated URL
            # before sending any bytes. A crash before this point creates no file.
            _set(row, db, total_bytes=src.size, source_version=src.version,
                 stage="preparing", claimed_at=dt.datetime.now(dt.timezone.utc).isoformat())
            url = _upload_session(uid, row["destination_path"], src.size, db)
            _set(row, db, upload_state_ciphertext=encrypt_token({"url": url,
                "version": src.version, "size": src.size}), stage="upload")
            upload_started = True
            offset, result = 0, None
        while result is None:
            _check(row, db)
            amount = min(CHUNK, src.size - offset)
            if amount <= 0:
                offset, result = _confirmed_offset(url, src.size)
                if result is None and offset == src.size:
                    raise BridgeError("Drive completion is not confirmed.")
                continue
            data = src.read_range(offset, amount)
            _check(row, db)
            # For a lost reply, query the session; resend only unacknowledged
            # bytes, and never create another remote file automatically.
            import requests
            for attempt in range(4):
                try:
                    new_offset, result = _put_chunk(url, src.size, offset, data)
                    break
                except (BridgeError, requests.RequestException):
                    if attempt == 3:
                        raise
                    time.sleep(min(2 ** attempt, 4))
                    new_offset, result = _confirmed_offset(url, src.size)
                    if new_offset > offset or result is not None:
                        break
            if new_offset <= offset and result is None:
                raise BridgeError("Drive did not acknowledge the chunk.")
            offset = new_offset
            _set(row, db, bytes_done=offset, total_bytes=src.size, stage="upload",
                 claimed_at=dt.datetime.now(dt.timezone.utc).isoformat())
        _complete(row, bot, db, src, result)
    except LostLease:
        return
    except Cancelled:
        try:
            _set(row, db, status="needs_review" if upload_started else "cancelled",
                 error_code="cancelled_during_upload" if upload_started else "cancelled")
        except LostLease:
            pass
    except Paused:
        try:
            _set(row, db, status="paused", error_code=None, pause_requested=False)
        except LostLease:
            pass
    except BridgeError as exc:
        try:
            _set(row, db, status="needs_review" if upload_started else "failed",
                 error_code=str(exc)[:180])
        except LostLease:
            pass
    except Exception:
        # Never log session URLs, OAuth tokens, untrusted source URLs or traces.
        try:
            _set(row, db, status="needs_review" if upload_started else "failed",
                 error_code="transfer_error_large")
        except LostLease:
            pass

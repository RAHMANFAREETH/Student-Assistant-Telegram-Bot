"""CloudBridge official provider APIs. All transfers are bounded and streamed.

No scraping of private third-party sites, credential collection or URL bypass.
Every provider account belongs to the Telegram user who connected it.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from urllib.parse import quote, urlencode, urljoin, urlsplit

from cloudbridge_v134_core import BridgeError, decrypt_token, encrypt_token, provider, validated_https_url

SCOPES = {"google": "https://www.googleapis.com/auth/drive.file",
          "onedrive": "offline_access Files.ReadWrite User.Read",
          "dropbox": ""}
AUTH_URLS = {"google": "https://accounts.google.com/o/oauth2/v2/auth",
             "onedrive": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
             "dropbox": "https://www.dropbox.com/oauth2/authorize"}
TOKEN_URLS = {"google": "https://oauth2.googleapis.com/token",
              "onedrive": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
              "dropbox": "https://api.dropboxapi.com/oauth2/token"}
CHUNK = 5 * 1024 * 1024  # exactly 16 * 320KiB, valid for OneDrive


def _requests():
    import requests
    return requests


def config(name):
    provider(name)
    prefix = "CLOUDBRIDGE_" + name.upper()
    client_id = os.getenv(prefix + "_CLIENT_ID", "")
    secret = os.getenv(prefix + "_CLIENT_SECRET", "")
    redirect = os.getenv("CLOUDBRIDGE_PUBLIC_URL", "").rstrip("/") + "/cloud/oauth/callback"
    if not client_id or not secret or not redirect.startswith("https://"):
        raise RuntimeError(name + " OAuth is not configured.")
    return client_id, secret, redirect


def authorization_url(name, state):
    cid, _secret, redirect = config(name)
    data = {"client_id": cid, "redirect_uri": redirect, "response_type": "code", "state": state}
    if name == "google":
        data.update({"scope": SCOPES[name], "access_type": "offline", "prompt": "consent"})
    elif name == "onedrive":
        data["scope"] = SCOPES[name]
    else:
        data["token_access_type"] = "offline"
    return AUTH_URLS[name] + "?" + urlencode(data)


def exchange_code(name, code):
    cid, secret, redirect = config(name)
    data = {"client_id": cid, "client_secret": secret, "code": code,
            "grant_type": "authorization_code", "redirect_uri": redirect}
    response = _requests().post(TOKEN_URLS[name], data=data, timeout=(8, 25))
    response.raise_for_status()
    token = response.json()
    if not isinstance(token.get("access_token"), str) or not token["access_token"]:
        raise RuntimeError("OAuth provider did not grant access.")
    token["expires_at"] = int(dt.datetime.now(dt.timezone.utc).timestamp()) + int(token.get("expires_in", 3600))
    return token


def access_token(user_id, name, db):
    from cloudbridge_v134_core import account_id
    account_id(user_id)
    provider(name)
    rows = (db.table("cloudbridge_accounts_v134").select("tokens_ciphertext")
            .eq("user_id", user_id).eq("provider", name).limit(1).execute()).data or []
    if not rows:
        raise BridgeError("Connect your " + name + " account first.")
    token = decrypt_token(rows[0]["tokens_ciphertext"])
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    if int(token.get("expires_at", 0)) > now + 90:
        return token["access_token"]
    if not token.get("refresh_token"):
        raise BridgeError("Reconnect your " + name + " account.")
    cid, secret, _redirect = config(name)
    payload = {"client_id": cid, "client_secret": secret, "refresh_token": token["refresh_token"],
               "grant_type": "refresh_token"}
    response = _requests().post(TOKEN_URLS[name], data=payload, timeout=(8, 25))
    response.raise_for_status()
    fresh = response.json()
    if not fresh.get("access_token"):
        raise BridgeError("Cloud account refresh failed. Reconnect it.")
    token.update({k: v for k, v in fresh.items() if k != "refresh_token"})
    token["refresh_token"] = fresh.get("refresh_token") or token["refresh_token"]
    token["expires_at"] = now + int(fresh.get("expires_in", 3600))
    (db.table("cloudbridge_accounts_v134").update({"tokens_ciphertext": encrypt_token(token)})
     .eq("user_id", user_id).eq("provider", name).execute())
    return token["access_token"]


def _auth_header(token):
    return {"Authorization": "Bearer " + token}


def _check_response(resp, label):
    try:
        resp.raise_for_status()
    except Exception as exc:
        # Requests exceptions may contain sensitive URLs. Never propagate them.
        raise BridgeError(label + " failed (HTTP " + str(getattr(resp, "status_code", "?")) + ").") from None


def _copy_to_disk(stream, handle, maximum, check_cancel):
    count = 0
    for block in stream:
        check_cancel()
        if not block:
            continue
        count += len(block)
        if count > maximum:
            raise BridgeError("File exceeds the configured transfer limit.")
        handle.write(block)
    return count


def download_provider(user_id, name, ref, handle, maximum, db, check_cancel):
    token = access_token(user_id, name, db)
    requests = _requests()
    if name == "google":
        if "/" in ref or "?" in ref or len(ref) > 200:
            raise BridgeError("Invalid Drive file ID.")
        url = "https://www.googleapis.com/drive/v3/files/" + quote(ref, safe="")
        meta = requests.get(url, headers=_auth_header(token), params={"fields": "mimeType,size"}, timeout=(8, 25))
        _check_response(meta, "Drive metadata")
        if meta.json().get("mimeType", "").startswith("application/vnd.google-apps."):
            raise BridgeError("Export Google Docs to a file format before transferring.")
        response = requests.get(url, headers=_auth_header(token), params={"alt": "media"},
                                stream=True, timeout=(8, 60), allow_redirects=False)
    elif name == "onedrive":
        if "/" in ref or "?" in ref or len(ref) > 200:
            raise BridgeError("Invalid OneDrive file ID.")
        url = "https://graph.microsoft.com/v1.0/me/drive/items/" + quote(ref, safe="") + "/content"
        response = requests.get(url, headers=_auth_header(token), stream=True,
                                timeout=(8, 60), allow_redirects=False)
        if response.status_code in {301, 302, 303, 307, 308}:
            destination = response.headers.get("Location", "")
            response.close()
            # Redirects are downloaded by our HTTPS IP-pinned fetcher.
            return download_https(destination, handle, maximum, check_cancel)
    else:
        if not ref.startswith("/") or "\x00" in ref or len(ref) > 512:
            raise BridgeError("Dropbox source must be a file path.")
        response = requests.post("https://content.dropboxapi.com/2/files/download",
                                 headers={**_auth_header(token), "Dropbox-API-Arg": json.dumps({"path": ref})},
                                 stream=True, timeout=(8, 60), allow_redirects=False)
    try:
        _check_response(response, "Cloud download")
        return _copy_to_disk(response.iter_content(CHUNK), handle, maximum, check_cancel)
    finally:
        response.close()


def download_https(url, handle, maximum, check_cancel):
    """Pinned DNS, SNI/TLS verification, no cookies and bounded redirects."""
    import urllib3
    previous = set()
    for _ in range(4):
        url, addresses = validated_https_url(url)
        if url in previous:
            raise BridgeError("Circular HTTPS redirect.")
        previous.add(url)
        parsed = urlsplit(url)
        host = parsed.hostname
        port = 443
        # The socket connects to a prevalidated PUBLIC IP; the certificate and
        # SNI are validated for the original hostname, preventing DNS rebinding.
        pool = urllib3.HTTPSConnectionPool(host=addresses[0], port=port, server_hostname=host,
                                            assert_hostname=host, maxsize=1, retries=False,
                                            timeout=urllib3.Timeout(connect=8, read=45))
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        response = None
        try:
            response = pool.request("GET", path, preload_content=False, redirect=False,
                                    headers={"Host": host, "Accept": "application/octet-stream",
                                             "User-Agent": "StudentAssistantCloudBridge/13.4"})
            if response.status in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location", "")
                if not location:
                    raise BridgeError("Missing HTTPS redirect target.")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise BridgeError("Source HTTP " + str(response.status) + ".")
            size_header = response.headers.get("Content-Length")
            if size_header and size_header.isdecimal() and int(size_header) > maximum:
                raise BridgeError("File exceeds the configured transfer limit.")
            def blocks():
                while True:
                    block = response.read(CHUNK)
                    if not block:
                        break
                    yield block
            return _copy_to_disk(blocks(), handle, maximum, check_cancel)
        finally:
            if response is not None:
                response.release_conn()
            pool.close()
    raise BridgeError("Too many HTTPS redirects.")


def _send_chunks(url, auth, handle, length, check_cancel):
    requests = _requests()
    offset = 0
    if length <= 0:
        raise BridgeError("Empty files are not supported.")
    while offset < length:
        check_cancel()
        data = handle.read(min(CHUNK, length - offset))
        if not data:
            raise BridgeError("Source ended before upload finished.")
        end = offset + len(data) - 1
        response = requests.put(url, headers={**auth, "Content-Length": str(len(data)),
                                              "Content-Range": f"bytes {offset}-{end}/{length}"},
                                data=data, timeout=(8, 120), allow_redirects=False)
        if response.status_code not in {200, 201, 202, 308}:
            raise BridgeError("Chunk upload failed (HTTP " + str(response.status_code) + ").")
        if response.status_code in {200, 201} and end + 1 != length:
            raise BridgeError("Provider finished upload prematurely.")
        offset = end + 1


def upload_provider(user_id, name, target, filename, handle, length, db, check_cancel):
    from cloudbridge_v134_core import safe_cloud_path
    target = safe_cloud_path(target)
    token = access_token(user_id, name, db)
    requests = _requests()
    handle.seek(0)
    if name == "google":
        if target.count("/") != 1:
            raise BridgeError("Drive V13.4 supports root folder uploads only.")
        metadata = {"name": target.lstrip("/")}
        response = requests.post("https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
                                 headers={**_auth_header(token), "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Length": str(length)},
                                 json=metadata, timeout=(8, 25), allow_redirects=False)
        _check_response(response, "Drive upload start")
        upload_url = response.headers.get("Location", "")
        if not upload_url.startswith("https://www.googleapis.com/"):
            raise BridgeError("Unexpected Drive upload endpoint.")
        _send_chunks(upload_url, {}, handle, length, check_cancel)
    elif name == "onedrive":
        api_path = quote(target.lstrip("/"), safe="/")
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{api_path}:/createUploadSession"
        response = requests.post(url, headers=_auth_header(token), json={"item": {"@microsoft.graph.conflictBehavior": "rename"}},
                                 timeout=(8, 25), allow_redirects=False)
        _check_response(response, "OneDrive upload start")
        upload_url = response.json().get("uploadUrl", "")
        # Microsoft returns a preauthenticated URL on *.up.1drv.com or
        # dedicated graph upload hosts. Do not forward the bearer token to it.
        from urllib.parse import urlsplit
        host = urlsplit(upload_url).hostname or ""
        if not upload_url.startswith("https://") or not (host.endswith(".1drv.com") or host.endswith(".sharepoint.com") or host.endswith(".microsoft.com")):
            raise BridgeError("Unexpected OneDrive upload endpoint.")
        _send_chunks(upload_url, {}, handle, length, check_cancel)
    else:
        headers = {**_auth_header(token), "Content-Type": "application/octet-stream"}
        first = handle.read(min(CHUNK, length))
        response = requests.post("https://content.dropboxapi.com/2/files/upload_session/start",
                                 headers={**headers, "Dropbox-API-Arg": json.dumps({"close": False})},
                                 data=first, timeout=(8, 120), allow_redirects=False)
        _check_response(response, "Dropbox upload start")
        session_id = response.json()["session_id"]
        offset = len(first)
        while offset < length:
            check_cancel()
            block = handle.read(min(CHUNK, length - offset))
            if not block:
                raise BridgeError("Source ended before upload finished.")
            response = requests.post("https://content.dropboxapi.com/2/files/upload_session/append_v2",
                                     headers={**headers, "Dropbox-API-Arg": json.dumps({"cursor": {"session_id": session_id, "offset": offset}, "close": False})},
                                     data=block, timeout=(8, 120), allow_redirects=False)
            _check_response(response, "Dropbox chunk upload")
            offset += len(block)
        check_cancel()
        response = requests.post("https://content.dropboxapi.com/2/files/upload_session/finish",
                                 headers={**headers, "Dropbox-API-Arg": json.dumps({
                                     "cursor": {"session_id": session_id, "offset": offset},
                                     "commit": {"path": target, "mode": "add", "autorename": True}})},
                                 data=b"", timeout=(8, 60), allow_redirects=False)
        _check_response(response, "Dropbox commit")

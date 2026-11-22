"""Student Assistant V13.4 CloudBridge: validation and durable metadata.

No browser-supplied user ID is trusted. The existing Study Lab age policy is
unchanged; CloudBridge has its own signed Telegram Mini App authentication.
"""
from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import secrets
import socket
import uuid
from urllib.parse import urlsplit

PROVIDERS = frozenset({"google", "onedrive", "dropbox"})
KINDS = frozenset({"telegram", "provider", "url"})
MAX_JOBS = 100


class BridgeError(ValueError):
    pass


def enabled():
    return os.getenv("CLOUDBRIDGE_V134_ENABLED", "false").lower() in {"true", "yes", "1", "on"}


def account_id(value):
    if type(value) is not int or value <= 0:
        raise BridgeError("Invalid Telegram account.")
    return value


def job_id(value):
    try:
        normalized = str(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise BridgeError("Invalid job ID.") from exc
    if value != normalized:
        raise BridgeError("Invalid job ID.")
    return normalized


def provider(value):
    if value not in PROVIDERS:
        raise BridgeError("Unsupported cloud provider.")
    return value


def safe_filename(value):
    if not isinstance(value, str):
        raise BridgeError("Invalid file name.")
    name = value.strip()
    if not name or len(name) > 160 or name in {".", ".."} or re.search(r"[\\/\x00-\x1f]", name):
        raise BridgeError("Invalid file name.")
    return name


def safe_cloud_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 512:
        raise BridgeError("Invalid destination path.")
    if any(ord(char) < 32 for char in value) or "\\" in value:
        raise BridgeError("Invalid destination path.")
    parts = value.strip("/").split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise BridgeError("Invalid destination path.")
    return "/" + "/".join(parts)


def _public_addresses(hostname):
    try:
        infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise BridgeError("Destination could not be resolved.") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise BridgeError("Destination could not be resolved.")
    for value in addresses:
        ip = ipaddress.ip_address(value)
        if not ip.is_global:
            raise BridgeError("Private or restricted addresses are blocked.")
    return sorted(addresses)


def validated_https_url(raw):
    """Return (canonical URL, public IPs). Caller MUST pin network connection.

    DNS checks alone are not an SSRF defense: the HTTP connection must use one
    of these already-resolved IPs and validate the original TLS hostname.
    """
    if not isinstance(raw, str) or len(raw) > 2048 or any(ord(x) < 33 for x in raw):
        raise BridgeError("Invalid HTTPS URL.")
    try:
        parsed = urlsplit(raw)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.port not in (None, 443)
                or parsed.fragment or not parsed.netloc):
            raise BridgeError("Only public HTTPS URLs on port 443 are supported.")
        if len(parsed.hostname) > 253 or parsed.hostname.endswith("."):
            raise BridgeError("Invalid hostname.")
        # No IP literals, IDN tricks or single-label internal hostnames.
        try:
            ipaddress.ip_address(parsed.hostname)
        except ValueError:
            if "." not in parsed.hostname or not parsed.hostname.isascii():
                raise BridgeError("Invalid public hostname.")
        else:
            raise BridgeError("IP-address URLs are not supported.")
        return raw, _public_addresses(parsed.hostname)
    except ValueError as exc:
        if isinstance(exc, BridgeError):
            raise
        raise BridgeError("Invalid HTTPS URL.") from exc


def validate_job(body):
    if not isinstance(body, dict) or set(body) - {"id", "source", "destination", "filename"}:
        raise BridgeError("Invalid transfer request.")
    request_id = job_id(body.get("id"))
    src = body.get("source")
    dst = body.get("destination")
    if not isinstance(src, dict) or not isinstance(dst, dict):
        raise BridgeError("Source and destination are required.")
    if set(src) - {"kind", "provider", "ref"} or set(dst) - {"kind", "provider", "path"}:
        raise BridgeError("Invalid transfer fields.")
    source_kind, destination_kind = src.get("kind"), dst.get("kind")
    if source_kind not in KINDS or destination_kind not in {"provider", "telegram"}:
        raise BridgeError("Unsupported transfer direction.")
    if source_kind == "telegram":
        if not isinstance(src.get("ref"), str) or not 1 <= len(src["ref"]) <= 512:
            raise BridgeError("Invalid Telegram file ID.")
        if src.get("provider") is not None:
            raise BridgeError("Invalid Telegram source.")
    elif source_kind == "provider":
        provider(src.get("provider"))
        if not isinstance(src.get("ref"), str) or not 1 <= len(src["ref"]) <= 512:
            raise BridgeError("Invalid source file reference.")
    else:
        if src.get("provider") is not None:
            raise BridgeError("Invalid URL source.")
        # DNS resolution occurs at execution, never trust validation-time DNS.
        if not isinstance(src.get("ref"), str) or not src["ref"].startswith("https://"):
            raise BridgeError("Only HTTPS source URLs are allowed.")
        # Validate URL syntax here, and public IPs at execution.
        p = urlsplit(src["ref"])
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment or p.port not in (None, 443):
            raise BridgeError("Invalid HTTPS source URL.")
    if destination_kind == "provider":
        provider(dst.get("provider"))
        dest_path = safe_cloud_path(dst.get("path"))
    else:
        if dst.get("provider") is not None or dst.get("path") is not None:
            raise BridgeError("Invalid Telegram destination.")
        dest_path = None
    if source_kind == "telegram" and destination_kind == "telegram":
        raise BridgeError("Use Telegram's existing forward/copy functions.")
    filename = safe_filename(body.get("filename"))
    return {"id": request_id, "source_kind": source_kind, "source_provider": src.get("provider"),
            "source_ref": src["ref"], "destination_kind": destination_kind,
            "destination_provider": dst.get("provider"), "destination_path": dest_path,
            "filename": filename, "status": "queued"}


def database():
    from db import supabase  # deferred: unit tests never contact production
    return supabase


def encrypt_token(data):
    from cryptography.fernet import Fernet
    import json
    key = os.getenv("CLOUDBRIDGE_FERNET_KEY", "")
    if not key:
        raise RuntimeError("CloudBridge token encryption is not configured.")
    return Fernet(key.encode()).encrypt(json.dumps(data).encode()).decode()


def decrypt_token(value):
    from cryptography.fernet import Fernet
    import json
    key = os.getenv("CLOUDBRIDGE_FERNET_KEY", "")
    if not key:
        raise RuntimeError("CloudBridge token encryption is not configured.")
    return json.loads(Fernet(key.encode()).decrypt(value.encode()).decode())


def list_jobs(uid, client=None):
    db = client if client is not None else database()
    rows = (db.table("cloudbridge_jobs_v134").select("id,filename,source_kind,source_provider,destination_kind,destination_provider,status,error_code,bytes_done,created_at,updated_at")
            .eq("user_id", account_id(uid)).order("created_at", desc=True).limit(MAX_JOBS).execute()).data or []
    return rows


def create_job(uid, raw, client=None):
    db = client if client is not None else database()
    job = validate_job(raw)
    job["user_id"] = account_id(uid)
    existing = (db.table("cloudbridge_jobs_v134").select("id,status")
                .eq("user_id", uid).eq("id", job["id"]).limit(1).execute()).data or []
    if existing:
        return existing[0], False
    jobs = list_jobs(uid, client=db)
    if len(jobs) >= MAX_JOBS:
        raise BridgeError("Job history limit reached. Contact the operator.")
    try:
        rows = db.table("cloudbridge_jobs_v134").insert(job).execute().data or []
    except Exception:
        # A simultaneous request with the same UUID might have won the INSERT.
        # Return only a row owned by the same authenticated Telegram account.
        found = (db.table("cloudbridge_jobs_v134").select("id,status")
                 .eq("user_id", uid).eq("id", job["id"]).limit(1).execute()).data or []
        if found:
            return {"id": job["id"], "status": found[0]["status"]}, False
        raise
    if not rows:
        rows = (db.table("cloudbridge_jobs_v134").select("id,status")
                .eq("user_id", uid).eq("id", job["id"]).limit(1).execute()).data or []
    if not rows:
        raise RuntimeError("Job could not be persisted.")
    return {"id": job["id"], "status": rows[0]["status"]}, True


def update_job(uid, jid, action, client=None):
    db = client if client is not None else database()
    jid = job_id(jid)
    account_id(uid)
    rows = (db.table("cloudbridge_jobs_v134").select("id,status")
            .eq("user_id", uid).eq("id", jid).limit(1).execute()).data or []
    if not rows:
        return None
    current = rows[0]["status"]
    if action == "delete" and current in ("completed", "cancelled", "failed", "needs_review"):
        deleted = (db.table("cloudbridge_jobs_v134").delete().eq("user_id", uid)
                   .eq("id", jid).eq("status", current).execute()).data or []
        return {"id": jid, "status": "deleted"} if deleted else None
    if action == "cancel" and current in ("queued", "running"):
        change = {"cancel_requested": True}
        if current == "queued":
            change["status"] = "cancelled"
    elif action == "retry" and current in ("failed", "needs_review"):
        # Never automatically retry an uncertain provider upload: it could
        # already have created a duplicate at the destination.
        if current == "needs_review":
            raise BridgeError("Check the destination and create a new job if necessary.")
        change = {"status": "queued", "cancel_requested": False, "error_code": None, "bytes_done": 0}
    else:
        raise BridgeError("Action unavailable for this job state.")
    changed = (db.table("cloudbridge_jobs_v134").update(change)
               .eq("user_id", uid).eq("id", jid).eq("status", current).execute()).data or []
    return {"id": jid, "status": change.get("status", current)} if changed else None


def new_oauth_state():
    value = secrets.token_urlsafe(36)
    return value, hashlib.sha256(value.encode()).hexdigest()

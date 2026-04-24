#!/usr/bin/env python3
"""
Flask yordamchi funksiyalari: CORS, rate limiter, Telegram auth, dekoratorlar
"""

import collections
import threading
import time as _time
import hmac
import hashlib
import urllib.parse
import json as _json
from datetime import datetime, timezone, timedelta
from functools import wraps

from config import BOT_TOKEN


# ── Simple in-memory rate limiter ──
_rl_buckets = collections.defaultdict(list)
_rl_lock    = threading.Lock()


def _rate_limit(key: str, limit: int, window: int = 60) -> bool:
    """True = ruxsat, False = limit oshdi."""
    now = _time.time()
    with _rl_lock:
        bucket = _rl_buckets[key]
        _rl_buckets[key] = [t for t in bucket if now - t < window]
        if len(_rl_buckets[key]) >= limit:
            return False
        _rl_buckets[key].append(now)
        return True


def rate_limit_check(uid=None, limit=60, window=60):
    from flask import request, jsonify
    key = f"uid:{uid}" if uid else f"ip:{request.remote_addr}"
    if not _rate_limit(key, limit, window):
        return jsonify({"ok": False, "error": "Too many requests"}), 429
    return None


def verify_init_data(init_data_raw: str):
    """Telegram WebApp initData ni HMAC-SHA256 bilan tekshiradi.
    Qaytadi: (uid, user_obj) yoki (None, {}).
    user_obj — Telegram'dan kelgan toʻliq foydalanuvchi ma'lumoti
    (first_name, last_name, username, language_code va h.k.)."""
    if not init_data_raw:
        return None, {}
    try:
        params = dict(urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True))
        received_hash = params.pop("hash", None)
        if not received_hash:
            return None, {}
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(params.items())
        )
        secret_key = hmac.new(BOT_TOKEN.encode(), b"WebAppData", hashlib.sha256).digest()
        computed   = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, received_hash):
            return None, {}
        auth_date = int(params.get("auth_date", 0))
        age = int(_time.time() - auth_date)
        if age > 604800:
            return None, {}
        user_obj = _json.loads(params.get("user", "{}"))
        uid = int(user_obj.get("id", 0)) or None
        if uid:
            print(f"[auth] OK: uid={uid}, age={age}s")
        return uid, user_obj
    except Exception as e:
        print(f"[auth] EXCEPTION: {e}")
        return None, {}


def get_init_tg_first_name():
    """X-Init-Data headeridan Telegram first_name ni xavfsiz oladi.
    HMAC tasdiqlangan ma'lumotdan keladi (frontend soxta qila olmaydi).
    Boʻsh yoki yo'q boʻlsa "" qaytadi. Ishlatish: DB'da ism yoʻq foydalanuvchi
    uchun Telegram'dan kelgan haqiqiy ismni olish (maxfiylikni saqlash —
    Telegram'da ism boʻsh boʻlsa, DB ga yozilmaydi)."""
    from flask import request
    raw = request.headers.get("X-Init-Data", "")
    if not raw:
        return ""
    _, user_obj = verify_init_data(raw)
    name = (user_obj or {}).get("first_name", "") or ""
    return name.strip()


def require_auth(f):
    """Telegram WebApp auth dekoratori"""
    from flask import request, jsonify
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
        uid_in_route = kwargs.get("uid")
        try:
            header_uid = int(request.headers.get("X-User-Id", 0))
        except Exception:
            header_uid = 0
        if not header_uid:
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        if uid_in_route is not None and header_uid != uid_in_route:
            return jsonify({"ok": False, "error": "Forbidden"}), 403
        rl_err = rate_limit_check(uid=header_uid, limit=60, window=60)
        if rl_err:
            return rl_err
        return f(*args, **kwargs)
    return decorated


def _tz_today():
    tz_uz = timezone(timedelta(hours=5))
    return datetime.now(tz_uz)


def _is_done_today(uid_done):
    """done_today[uid_str] qiymatidan foydalanuvchi bajardimi yoki yo'qligini qaytaradi."""
    if isinstance(uid_done, bool):
        return uid_done
    if isinstance(uid_done, dict):
        return True in uid_done.values()
    return False


def _calc_best_streak(u):
    """Foydalanuvchining eng uzun streakini qaytaradi."""
    return max(u.get("best_streak", 0),
               max((h.get("streak", 0) for h in u.get("habits", [])), default=0))


def register_helpers(app):
    """CORS va after_request ro'yxatdan o'tkazish"""
    from flask import jsonify as jfy

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.route("/api/rating", methods=["OPTIONS"])
    @app.route("/api/profile/<int:uid>", methods=["OPTIONS"])
    @app.route("/api/groups/<int:uid>", methods=["OPTIONS"])
    def options_preflight(**kwargs):
        return jfy({}), 200

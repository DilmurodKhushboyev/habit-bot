#!/usr/bin/env python3
"""
Flask API — bir martalik eslatmalar CRUD.

Endpoints:
  GET    /api/reminders/<uid>           — foydalanuvchi eslatmalari ro'yxati
  POST   /api/reminders/<uid>           — yangi eslatma yaratish
  DELETE /api/reminders/<uid>/<rid>     — eslatma o'chirish
  PATCH  /api/reminders/<uid>/<rid>/done — bajarilgan deb belgilash (+2 ball)
"""

from datetime import datetime, timezone
from flask import jsonify, request

from config import REMINDER_MAX_TEXT_LEN, REMINDER_COMPLETE_POINTS
from database import (create_reminder, list_reminders, delete_reminder,
                      update_reminder, get_reminder, load_user, save_user)
from flask_helpers import require_auth

# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================
def _parse_iso_datetime(val):
    """ISO string → datetime (UTC). Noto'g'ri bo'lsa None."""
    if not val or not isinstance(val, str):
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def _serialize_reminder(rem):
    """MongoDB doc → JSON-xavfsiz dict."""
    if not rem:
        return None
    out = dict(rem)
    # datetime → ISO string (UTC, 'Z' bilan — frontend new Date() to'g'ri talqin qilishi uchun)
    for key in ("remind_at", "created_at", "notified_at", "done_at"):
        if key in out and isinstance(out[key], datetime):
            dt = out[key]
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            out[key] = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return out

# ============================================================
#  ROUTE REGISTRATSIYA
# ============================================================
def register_reminders_routes(app):

    @app.route("/api/reminders/<int:uid>", methods=["GET"])
    @require_auth
    def api_reminders_list(uid):
        """Foydalanuvchining barcha eslatmalari (pending, sent, done, skipped, expired)."""
        status = request.args.get("status")  # ixtiyoriy filter
        rems = list_reminders(uid, status=status)
        return jsonify({
            "ok": True,
            "reminders": [_serialize_reminder(r) for r in rems]
        })

    @app.route("/api/reminders/<int:uid>", methods=["POST"])
    @require_auth
    def api_reminders_create(uid):
        """Yangi bir martalik eslatma yaratish.
        Body: { "text": "...", "remind_at": "2026-04-24T15:30:00Z" }
        """
        data = request.get_json() or {}
        text = str(data.get("text", "")).strip()
        remind_at_str = data.get("remind_at")

        # Validatsiya
        if not text:
            return jsonify({"ok": False, "error": "text_required"}), 400
        if len(text) > REMINDER_MAX_TEXT_LEN:
            text = text[:REMINDER_MAX_TEXT_LEN]

        remind_at = _parse_iso_datetime(remind_at_str)
        if not remind_at:
            return jsonify({"ok": False, "error": "invalid_remind_at"}), 400

        # O'tgan vaqt emasligini tekshirish (1 daqiqa tolerance)
        now = datetime.now(timezone.utc)
        if (remind_at - now).total_seconds() < -60:
            return jsonify({"ok": False, "error": "past_time"}), 400

        # Foydalanuvchi tilini olish
        u = load_user(uid)
        lang = u.get("lang", "uz")

        doc = {
            "user_id":   int(uid),
            "text":      text,
            "remind_at": remind_at,
            "status":    "pending",
            "language":  lang,
            "created_at": now,
        }
        rid = create_reminder(doc)
        if not rid:
            return jsonify({"ok": False, "error": "create_failed"}), 500

        doc["_id"] = rid
        return jsonify({
            "ok": True,
            "reminder": _serialize_reminder(doc)
        })

    @app.route("/api/reminders/<int:uid>/<rid>", methods=["DELETE"])
    @require_auth
    def api_reminders_delete(uid, rid):
        """Eslatma o'chirish (faqat egasi o'chira oladi)."""
        rem = get_reminder(rid)
        if not rem:
            return jsonify({"ok": False, "error": "not_found"}), 404
        if rem.get("user_id") != int(uid):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        delete_reminder(rid)
        return jsonify({"ok": True})

    @app.route("/api/reminders/<int:uid>/<rid>/done", methods=["PATCH"])
    @require_auth
    def api_reminders_done(uid, rid):
        """Eslatmani bajarilgan deb belgilash va +2 ball berish."""
        rem = get_reminder(rid)
        if not rem:
            return jsonify({"ok": False, "error": "not_found"}), 404
        if rem.get("user_id") != int(uid):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        if rem.get("status") == "done":
            return jsonify({"ok": False, "error": "already_done"}), 400

        # Ball berish
        u = load_user(uid)
        old_pts = int(u.get("points", 0))
        new_pts = old_pts + REMINDER_COMPLETE_POINTS
        u["points"] = new_pts
        save_user(uid, u)

        update_reminder(rid, {
            "status": "done",
            "done_at": datetime.now(timezone.utc)
        })
        return jsonify({
            "ok": True,
            "points": new_pts,
            "delta": REMINDER_COMPLETE_POINTS
        })

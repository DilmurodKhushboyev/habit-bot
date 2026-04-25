#!/usr/bin/env python3
"""
Eslatmalar scheduler — bir martalik (one-time) eslatmalar.

scheduler.py dan alohida ishlaydi (24-qoida: monolit emas).
Mustaqil fon thread har 30 soniyada pending eslatmalarni tekshiradi.
remind_at <= hozir bo'lsa — Telegram xabarini yuboradi va status="sent" qo'yadi.
"""

import time
import threading
from datetime import datetime, timezone, timedelta

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import REMINDER_COMPLETE_POINTS
from database import (list_pending_reminders_all, update_reminder,
                      load_user, save_user, get_reminder)
from helpers import T, get_lang
from bot_setup import bot

# ── Scheduler loop parametrlari ─────────────────────────────
_CHECK_INTERVAL = 30       # har 30 soniyada tekshirish
_scheduler_thread = None
_scheduler_running = False

# ============================================================
#  VAQT YORDAMCHILARI
# ============================================================
def _now_utc():
    """Hozirgi UTC vaqtni datetime sifatida qaytaradi."""
    return datetime.now(timezone.utc)

def _parse_remind_at(val):
    """remind_at qiymatini datetime ga o'giradi (UTC)."""
    if isinstance(val, datetime):
        # Agar naive bo'lsa — UTC deb hisoblaymiz
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, str):
        try:
            # ISO format: "2026-04-24T15:30:00" yoki "2026-04-24T15:30:00+00:00"
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None

# ============================================================
#  ESLATMA YUBORISH
# ============================================================
def send_one_time_reminder(reminder_id):
    """Bir martalik eslatmani Telegram orqali yuboradi."""
    rem = get_reminder(reminder_id)
    if not rem:
        print(f"[reminder] {reminder_id} topilmadi")
        return
    if rem.get("status") != "pending":
        return  # Allaqachon yuborilgan/bajarilgan

    user_id = rem.get("user_id")
    text    = rem.get("text", "")
    lang    = get_lang(user_id)

    # Xabar matni
    title   = T(user_id, "rem_notif_title")   # "⏰ Eslatma!"
    note    = T(user_id, "rem_notif_body")    # "💡 Bu vazifani bajardingizmi?"
    body    = f"{title}\n\n*{text}*\n\n{note}"

    # Inline tugmalar — bir qatorda (row_width=2), Bot API 9.4 ranglar
    kb = InlineKeyboardMarkup(row_width=2)
    btn_done = InlineKeyboardButton(
        T(user_id, "rem_btn_done"),          # "✅ Bajardim"
        callback_data=f"remdone_{reminder_id}"
    )
    btn_skip = InlineKeyboardButton(
        T(user_id, "rem_btn_skip"),          # "❌ Bajarmadim"
        callback_data=f"remskip_{reminder_id}"
    )
    # Bot API 9.4 (2026-02-09) — tugma rangi: success=yashil, danger=qizil
    # Eski client'larda e'tiborga olinmaydi (xato bermaydi)
    btn_done.style = "success"
    btn_skip.style = "danger"
    kb.add(btn_done, btn_skip)

    try:
        msg = bot.send_message(
            user_id, body,
            parse_mode="Markdown",
            reply_markup=kb
        )
        update_reminder(reminder_id, {
            "status": "sent",
            "notified_at": _now_utc(),
            "message_id": msg.message_id
        })
        print(f"[reminder] Yuborildi: {reminder_id} → {user_id}")
    except Exception as e:
        print(f"[reminder] Yuborishda xato ({reminder_id}): {e}")
        # Yuborilmasa — expired deb belgilash (takror urinish yo'q)
        update_reminder(reminder_id, {"status": "expired"})

# ============================================================
#  SCHEDULER LOOP
# ============================================================
def _scheduler_loop():
    """Fon thread — har 30 soniyada pending eslatmalarni tekshiradi."""
    global _scheduler_running
    print("[reminder_scheduler] Ishga tushdi")
    while _scheduler_running:
        try:
            now = _now_utc()
            pending = list_pending_reminders_all()
            for rem in pending:
                remind_at = _parse_remind_at(rem.get("remind_at"))
                if not remind_at:
                    # Noto'g'ri vaqt — expired
                    update_reminder(rem["_id"], {"status": "expired"})
                    continue
                if remind_at <= now:
                    send_one_time_reminder(rem["_id"])
        except Exception as e:
            print(f"[reminder_scheduler] xato: {e}")
        time.sleep(_CHECK_INTERVAL)

def start_reminders_scheduler():
    """Eslatmalar scheduler'ini ishga tushirish (habit_bot.py dan chaqiriladi)."""
    global _scheduler_thread, _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()

def stop_reminders_scheduler():
    """Testing uchun — odatda ishlatilmaydi."""
    global _scheduler_running
    _scheduler_running = False

# ============================================================
#  ESLATMA BAJARISH (callback'dan chaqiriladi)
# ============================================================
def mark_reminder_done(reminder_id, user_id):
    """Foydalanuvchi 'Bajardim' tugmasini bossa — ball berish."""
    rem = get_reminder(reminder_id)
    if not rem:
        return False, 0
    if rem.get("user_id") != int(user_id):
        return False, 0
    if rem.get("status") == "done":
        return False, 0  # Ikki marta bosilmasin

    # Ball berish
    u = load_user(user_id)
    old_pts = int(u.get("points", 0))
    new_pts = old_pts + REMINDER_COMPLETE_POINTS
    u["points"] = new_pts
    save_user(user_id, u)

    update_reminder(reminder_id, {
        "status": "done",
        "done_at": _now_utc()
    })
    return True, new_pts

def mark_reminder_skipped(reminder_id, user_id):
    """Foydalanuvchi 'O'tkazib yuborish' tugmasini bossa."""
    rem = get_reminder(reminder_id)
    if not rem:
        return False
    if rem.get("user_id") != int(user_id):
        return False
    update_reminder(reminder_id, {"status": "skipped"})
    return True

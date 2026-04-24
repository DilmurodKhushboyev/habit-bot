#!/usr/bin/env python3
"""
Eslatmalar (bir martalik) callback handler.

Callback data formatlari:
  remdone_<reminder_id>  — foydalanuvchi "Bajardim" tugmasini bosdi (+2 ball)
  remskip_<reminder_id>  — foydalanuvchi "O'tkazib yuborish" tugmasini bosdi

callbacks_habits.py pattern'ini takrorlaydi:
  - handle_reminder_callbacks(call, uid, cdata, u) → bool qaytaradi
  - True = ushbu dispatcher qayta ishladi, keyingilari chaqirilmasin
  - False = bizning callback emas
"""

from bot_setup import bot
from helpers import T
from reminders_scheduler import mark_reminder_done, mark_reminder_skipped


def handle_reminder_callbacks(call, uid, cdata, u):
    """Eslatma callback'larini qayta ishlaydi.

    Qaytaradi True — ushbu callback eslatma bilan bog'liq va boshqa
    dispatcher chaqirilmasin. False — boshqa dispatcher tekshirsin.
    """

    # ── BAJARDIM (+2 ball) ──
    if cdata.startswith("remdone_"):
        rid = cdata[len("remdone_"):]
        ok, new_pts = mark_reminder_done(rid, uid)
        if ok:
            # Xabarni yangilash: tugmalarni olib tashlab, "bajarildi" qo'shish
            toast      = T(uid, "rem_done_toast", pts=2)
            old_text   = call.message.text or ""
            # Markdown asterisklari call.message.text da yo'q, toast'ni ham toza qilamiz
            clean_toast = toast.replace("*", "")
            new_text   = old_text + "\n\n" + clean_toast
            try:
                bot.edit_message_text(
                    chat_id=uid,
                    message_id=call.message.message_id,
                    text=new_text,
                    reply_markup=None
                )
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, clean_toast)
            except Exception:
                pass
        else:
            # Allaqachon bajarilgan yoki topilmadi
            try:
                bot.answer_callback_query(call.id, "⚠️", show_alert=False)
            except Exception:
                pass
        return True

    # ── O'TKAZIB YUBORISH ──
    if cdata.startswith("remskip_"):
        rid = cdata[len("remskip_"):]
        ok = mark_reminder_skipped(rid, uid)
        if ok:
            toast      = T(uid, "rem_skipped_toast")
            old_text   = call.message.text or ""
            clean_toast = toast.replace("*", "")
            new_text   = old_text + "\n\n" + clean_toast
            try:
                bot.edit_message_text(
                    chat_id=uid,
                    message_id=call.message.message_id,
                    text=new_text,
                    reply_markup=None
                )
            except Exception:
                pass
            try:
                bot.answer_callback_query(call.id, clean_toast)
            except Exception:
                pass
        else:
            try:
                bot.answer_callback_query(call.id, "⚠️", show_alert=False)
            except Exception:
                pass
        return True

    return False

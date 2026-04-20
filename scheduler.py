#!/usr/bin/env python3
"""
Eslatmalar, kunlik reset, jadval boshqaruvi
"""

import os
import random
import schedule
import time
import threading
from datetime import datetime, date, timedelta, timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID, BOT_TOKEN, mongo_col, groups_col, mongo_db, SHOP_BONUS_EFFECTS
from database import (load_user, save_user, load_all_users, load_group,
                      save_group, load_settings)
from helpers import T, get_lang, today_uz5
from texts import LANGS
from motivation import MOTIVATSIYA
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, done_keyboard)

from handlers_stats import send_weekly_reports, send_monthly_reports, send_yearly_reports

def send_reminder(user_id, habit):
    u      = load_user(user_id)
    habits = u.get("habits", [])
    exists = False
    today  = today_uz5()
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
    current_habit = None
    for h in habits:
        if h["id"] == habit["id"]:
            exists = True
            current_habit = h
            # Eslatma o'chirilgan bo'lsa — yubormaymiz
            if h.get("reminder_enabled") is False:
                return
            # Bugun allaqachon bajarilgan bo'lsa — eslatma yubormaymiz
            if h.get("last_done") == today:
                return
            # total_missed bu yerda EMAS — daily_reset() da hisoblanadi (qo'sh hisoblashni oldini olish)
            break
    if not exists:
        return
    save_user(user_id, u)

    # Shaxsiy ma'lumotlar
    name       = u.get("name", "").split()[0] if u.get("name") else ""
    streak     = current_habit.get("streak", 0) if current_habit else 0
    lang       = get_lang(user_id)
    motiv      = random.choice(MOTIVATSIYA.get(lang, MOTIVATSIYA["uz"]))
    habit_name = current_habit.get("name", habit["name"])

    # Streak ga qarab jonli xabar
    if streak == 0:
        streak_line = f"🌱 Bugun birinchi qadam — eng muhimi shu!"
    elif streak == 1:
        streak_line = f"✨ Kecha boshladingiz — davom eting!"
    elif streak < 7:
        streak_line = f"🔥 {streak} kun ketma-ket! Ajoyib start!"
    elif streak < 14:
        streak_line = f"⚡ {streak} kunlik streak! Haftani yoping!"
    elif streak < 30:
        streak_line = f"💪 {streak} kun! Odat shakllanmoqda — to'xtamang!"
    elif streak < 100:
        streak_line = f"🏆 {streak} kunlik streak! Siz mashinasiz!"
    else:
        streak_line = f"👑 {streak} kun! Siz — odatlar ustasisiz!"

    # Xabar matni
    greeting = f"*{name},* " if name else ""
    text = (
        f"⏰ {greeting}*{habit_name}* vaqti!\n\n"
        f"{streak_line}\n\n"
        f"_{motiv}_"
    )

    try:
        sent_msg = bot.send_message(
            user_id,
            text,
            parse_mode="Markdown",
            reply_markup=done_keyboard(user_id, habit["id"])
        )
        # Javobsiz eslatma xabarini kuzatish: ertasi 00:00 UZ+5 da o'chiriladi (daily_reset)
        try:
            u2 = load_user(user_id)
            pending = u2.get("pending_reminders", [])
            pending.append({
                "message_id": sent_msg.message_id,
                "date_uz5":   today,
            })
            # Xavfsizlik: ro'yxat cheksiz o'smasligi uchun oxirgi 200 bilan cheklaymiz
            if len(pending) > 200:
                pending = pending[-200:]
            u2["pending_reminders"] = pending
            save_user(user_id, u2)
        except Exception as _pe:
            print(f"[reminder] pending saqlash xatosi: {_pe}")
    except Exception as e:
        print(f"[reminder] xato: {e}")

STREAK_MILESTONES = {
    7:   {"emoji": "🔥", "bonus": 20,  "title": "7 kunlik streak!"},
    14:  {"emoji": "⚡", "bonus": 35,  "title": "2 haftalik streak!"},
    21:  {"emoji": "💪", "bonus": 50,  "title": "21 kunlik streak!"},
    30:  {"emoji": "💎", "bonus": 100, "title": "Oylik ustoz!"},
    60:  {"emoji": "🏆", "bonus": 200, "title": "60 kunlik streak!"},
    100: {"emoji": "👑", "bonus": 500, "title": "100 kun shohi!"},
    365: {"emoji": "🌟", "bonus": 1000, "title": "1 yillik streak!"},
}

def _check_streak_milestone(uid, new_streak):
    """Global streak milestone bo'lsa — Telegram xabari yuboradi va bonus ball beradi.
    Qayta yuborishni oldini olish uchun u['streak_milestones_sent'] listidan foydalanadi."""
    ms = STREAK_MILESTONES.get(new_streak)
    if not ms:
        return
    u = load_user(uid)
    sent_list = u.get("streak_milestones_sent", [])
    if new_streak in sent_list:
        return
    # Bonus ball qo'shamiz
    u["points"] = u.get("points", 0) + ms["bonus"]
    sent_list.append(new_streak)
    u["streak_milestones_sent"] = sent_list
    save_user(uid, u)
    lang = get_lang(uid)
    if lang == "ru":
        text = (
            f"{ms['emoji']} *{ms['title']}*\n\n"
            f"Pozdravlyaem! Vy podderzhivaete seriyu *{new_streak} dnej* podryad!\n\n"
            f"\U0001f381 *Bonus:* +{ms['bonus']} \u2b50 ballov dobavleno!"
        )
    elif lang == "en":
        text = (
            f"{ms['emoji']} *{ms['title']}*\n\n"
            f"Congratulations! You've kept a *{new_streak}-day* streak!\n\n"
            f"\U0001f381 *Bonus:* +{ms['bonus']} \u2b50 points added!"
        )
    else:
        text = (
            f"{ms['emoji']} *{ms['title']}*\n\n"
            f"Tabriklaymiz! Siz *{new_streak} kun* ketma-ket odat bajardingiz!\n\n"
            f"\U0001f381 *Bonus:* +{ms['bonus']} \u2b50 ball qo'shildi!"
        )
    try:
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=ok_kb(uid))
    except Exception as e:
        print(f"[milestone] xato {uid}: {e}")

def _try_pet_cat_save(udata, habit, today_str):
    """
    pet_cat faol va cooldown (7 kun) tugagan bo'lsa, streak'ni avtomatik saqlaydi.
    Returns: True agar pet_cat ishlatilgan (streak saqlangan), False aks holda.

    Mantiq:
    1. active_pet == "pet_cat" emasmi — False
    2. Cooldown: pet_cat_last_used_date bor va 7 kundan kam o'tgan — False
    3. Aks holda: pet_cat_last_used_date = today, foydalanuvchiga xushxabar, True qaytariladi

    Eslatma: Bu funksiya streak ni o'zgartirmaydi (chaqiruvchi oldindan saqlaydi).
    """
    if udata.get("active_pet", "") != "pet_cat":
        return False
    effect = SHOP_BONUS_EFFECTS.get("pet_cat")
    if not effect or effect.get("type") != "streak_save":
        return False
    cooldown_days = effect.get("value", 7)
    last_used = udata.get("pet_cat_last_used_date", "")
    if last_used:
        try:
            from datetime import datetime as _dt
            last_dt = _dt.strptime(last_used, "%Y-%m-%d")
            today_dt = _dt.strptime(today_str, "%Y-%m-%d")
            days_passed = (today_dt - last_dt).days
            if days_passed < cooldown_days:
                return False  # Cooldown tugamagan
        except Exception:
            pass  # Sana noto'g'ri bo'lsa, pet_cat ishlatilsin
    # Pet_cat ishlatiladi
    udata["pet_cat_last_used_date"] = today_str
    return True

def _apply_pet_rabbit_soften(udata, change):
    """
    pet_rabbit faol bo'lsa va jon kamayishi (change<0) bo'lsa, jazoni 50% yumshatadi.
    Musbat change (jon o'sishi) yoki 0 ga tegmaydi.
    Returns: yangi change qiymati.
    """
    if udata.get("active_pet", "") != "pet_rabbit":
        return change
    effect = SHOP_BONUS_EFFECTS.get("pet_rabbit")
    if not effect or effect.get("type") != "jon_soften":
        return change
    if change >= 0:
        return change  # Jon o'syapti — soften kerak emas
    soften_percent = effect.get("value", 50)
    # change manfiy: masalan -6.67. soften 50% → -3.33
    softened = change * (1 - soften_percent / 100)
    return softened

def _uz5_to_utc(time_str):
    """UTC+5 vaqtni UTC ga o'giradi. Noto'g'ri bo'lsa None qaytaradi."""
    try:
        h, m = map(int, time_str.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        total  = (h * 60 + m - 5 * 60) % (24 * 60)
        return f"{total // 60:02d}:{total % 60:02d}"
    except Exception:
        return None

def schedule_habit(user_id, habit):
    # Avval eski jadval bo'lsa o'chiramiz (dublikat bo'lmasligi uchun)
    schedule.clear(f"{user_id}_{habit['id']}")

    # Takrorlanuvchi odat: repeat_times ro'yxatidagi har bir vaqt uchun alohida schedule
    repeat_times = habit.get("repeat_times", [])
    if repeat_times:
        scheduled_any = False
        for rt in repeat_times:
            if not rt or rt in ("vaqtsiz", "—", "", None):
                continue
            utc_time = _uz5_to_utc(rt)
            if not utc_time:
                print(f"[schedule] {habit['name']} — noto'g'ri vaqt: '{rt}', o'tkazib yuborildi")
                continue
            schedule.every().day.at(utc_time).do(
                send_reminder, user_id=user_id, habit=habit
            ).tag(f"{user_id}_{habit['id']}")
            print(f"[schedule] {habit['name']} — {rt} (UTC: {utc_time})")
            scheduled_any = True
        if scheduled_any:
            return

    # Oddiy odat yoki repeat_times bo'sh — eski mantiq (bitta time)
    t = habit.get("time", "vaqtsiz")
    if not t or t in ("vaqtsiz", "—", "", None):
        return
    utc_time = _uz5_to_utc(t)
    if not utc_time:
        print(f"[schedule] {habit['name']} — noto'g'ri vaqt: '{t}', o'tkazib yuborildi")
        return

    schedule.every().day.at(utc_time).do(
        send_reminder, user_id=user_id, habit=habit
    ).tag(f"{user_id}_{habit['id']}")
    print(f"[schedule] {habit['name']} — {t} (UTC: {utc_time})")

def unschedule_habit_today(user_id, habit_id):
    """Bugun uchun eslatmani to'xtatish — ertaga avtomatik ishlaydi"""
    schedule.clear(f"{user_id}_{habit_id}")
    print(f"[schedule] {user_id}_{habit_id} — bugunlik to'xtatildi")

def _is_member_done(val):
    """done_today[uid_str] qiymatini to'g'ri tekshiradi (True, {"main": True}, {"main": False})."""
    if val is True:
        return True
    if isinstance(val, dict):
        return True in val.values()
    return False

def group_daily_reset():
    """Har kuni 00:00 (UTC+5) da guruh progressini tozalash va eslatma yuborish"""
    print("[group_reset] Guruh progresslari tozalanmoqda...")
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        for g_doc in groups_col.find({}):
            g_id  = g_doc["_id"]
            g     = {k: v for k, v in g_doc.items() if k != "_id"}
            members    = g.get("members", [])
            done_today = g.get("done_today", {})
            done_date  = g.get("done_date", "")
            # Kecha hamma bajardimi?
            if done_date == yesterday:
                all_done = all(_is_member_done(done_today.get(str(mid), False)) for mid in members)
                if all_done and members:
                    g["streak"] = g.get("streak", 0) + 1
                elif members:
                    # Bajarmagan a'zolarga eslatma
                    for mid in members:
                        if not _is_member_done(done_today.get(str(mid), False)):
                            try:
                                mu = load_user(mid)
                                bot.send_message(
                                    int(mid),
                                    f"😔 *{g['name']}*\n\n"
                                    f"Kecha odatni bajarmadingiz.\n"
                                    f"📌 *{g.get('habit_name','—')}*\n\n"
                                    f"Bugun davom eting! 💪",
                                    parse_mode="Markdown",
                                    reply_markup=ok_kb(int(mid))
                                )
                            except Exception as _e: print(f"[warn] xato: {_e}")
            # Progressni tozalash
            g["done_today"] = {}
            g["done_date"]  = ""
            save_group(g_id, g)
    except Exception as e:
        print(f"[group_reset] Xato: {e}")

def daily_reset():
    """Har kuni 00:00 (UTC+5) da barcha jadvallarni qayta yuklash"""
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    today_str = datetime.now(tz_uz).strftime("%Y-%m-%d")
    # Bugun allaqachon ishlagan bo'lsa — qayta ishlatma
    try:
        settings_doc = mongo_col.find_one({"_id": "_settings"}) or {}
        if settings_doc.get("last_reset_date") == today_str:
            print(f"[daily_reset] Bugun allaqachon ishlagan ({today_str}) — o'tkazib yuborildi")
            return
        mongo_col.update_one({"_id": "_settings"}, {"$set": {"last_reset_date": today_str}}, upsert=True)
    except Exception as e:
        print(f"[daily_reset] Settings xatosi: {e}")
    print("[daily_reset] Barcha jadvallar qayta yuklanmoqda...")
    yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
    users = load_all_users(force=True)
    for uid, udata in users.items():
        changed = False
        for habit in udata.get("habits", []):
            hab_type = habit.get("type", "simple")
            if hab_type == "repeat":
                # Repeat: done_today_count tozalash + bajarilmasa missed++
                fully_done = habit.get("last_done") == yesterday
                if not fully_done:
                    # Kecha to'liq bajarilmagan — missed++
                    if habit.get("total_done", 0) > 0 or habit.get("done_today_count", 0) > 0:
                        habit["total_missed"] = habit.get("total_missed", 0) + 1
                    # Streak nollash (simple habit kabi shield tekshiruvi bilan)
                    if habit.get("streak", 0) > 0:
                        shields = udata.get("streak_shields", 0)
                        if shields > 0:
                            streak_val = habit.get("streak", 0)
                            habit["streak"] = 0
                            pending = udata.get("pending_shield", {})
                            pending[habit["id"]] = streak_val
                            udata["pending_shield"] = pending
                            try:
                                kb_sh = InlineKeyboardMarkup()
                                kb_sh.row(
                                    InlineKeyboardButton("✅ Ha, ishlatish",    callback_data=f"shield_use_{habit['id']}"),
                                    InlineKeyboardButton("❌ Yo'q, nollansin", callback_data=f"shield_skip_{habit['id']}")
                                )
                                bot.send_message(
                                    int(uid),
                                    f"⚠️ *Streakingiz xavf ostida!*\n\n"
                                    f"*🔥 Streak:* {streak_val} kun\n"
                                    f"*📌 Odat:* {habit['name']}\n\n"
                                    f"*🛡 Himoyangiz bor* — ishlatinmi?\n"
                                    f"_(Yo'q desangiz himoya saqlanib qoladi)_",
                                    parse_mode="Markdown",
                                    reply_markup=kb_sh
                                )
                            except Exception:
                                pass
                        else:
                            # pet_cat orqali streak saqlashga urinish
                            if _try_pet_cat_save(udata, habit, today_str):
                                # Streak saqlandi — nollashga tegmaslik, xushxabar yuborish
                                try:
                                    bot.send_message(
                                        int(uid),
                                        f"🐱 *Mushugingiz streakingizni qutqardi!*\n\n"
                                        f"*📌 Odat:* {habit['name']}\n"
                                        f"*🔥 Streak:* {habit.get('streak', 0)} kun saqlandi\n\n"
                                        f"_Keyingi qutqaruv — 7 kundan keyin._",
                                        parse_mode="Markdown"
                                    )
                                except Exception:
                                    pass
                            else:
                                habit["streak"] = 0
                # done_today_count tozalash — lekin last_done ni faqat bajarilmagan bo'lsa nollash
                habit["done_today_count"] = 0
                if not fully_done:
                    habit["last_done"] = None
                changed = True
            else:
                # Oddiy: kecha ham, bugun ham bajarilmagan bo'lsa missed++ va streak nollanadi
                missed_today = False
                last_done = habit.get("last_done")
                if last_done not in (yesterday, today_str, None):
                    habit["total_missed"] = habit.get("total_missed", 0) + 1
                    missed_today = True
                    changed = True
                elif last_done is None and habit.get("total_done", 0) > 0:
                    habit["total_missed"] = habit.get("total_missed", 0) + 1
                    missed_today = True
                    changed = True
                # Streak himoyasi
                if missed_today and habit.get("streak", 0) > 0:
                    shields = udata.get("streak_shields", 0)
                    if shields > 0:
                        # Himoya bor — foydalanuvchiga xabar yuborib qaror qildirish
                        streak_val = habit.get("streak", 0)
                        habit["streak"] = 0  # Hozircha nollanadi
                        changed = True
                        # pending_shield saqlaymiz — Ha bosilsa tiklanadi
                        pending = udata.get("pending_shield", {})
                        pending[habit["id"]] = streak_val
                        udata["pending_shield"] = pending
                        try:
                            kb_sh = InlineKeyboardMarkup()
                            kb_sh.row(
                                InlineKeyboardButton("✅ Ha, ishlatish",      callback_data=f"shield_use_{habit['id']}"),
                                InlineKeyboardButton("❌ Yo'q, nollansin",   callback_data=f"shield_skip_{habit['id']}")
                            )
                            bot.send_message(
                                int(uid),
                                f"⚠️ *Streakingiz xavf ostida!*\n\n"
                                f"*🔥 Streak:* {streak_val} kun\n"
                                f"*📌 Odat:* {habit['name']}\n\n"
                                f"*🛡 Himoyangiz bor* — ishlatinmi?\n"
                                f"_(Yo'q desangiz himoya saqlanib qoladi)_",
                                parse_mode="Markdown",
                                reply_markup=kb_sh
                            )
                        except Exception:
                            pass
                    else:
                        # Himoya yo'q — pet_cat orqali streak saqlashga urinish
                        if _try_pet_cat_save(udata, habit, today_str):
                            # Streak saqlandi — nollashga tegmaslik, xushxabar yuborish
                            try:
                                bot.send_message(
                                    int(uid),
                                    f"🐱 *Mushugingiz streakingizni qutqardi!*\n\n"
                                    f"*📌 Odat:* {habit['name']}\n"
                                    f"*🔥 Streak:* {habit.get('streak', 0)} kun saqlandi\n\n"
                                    f"_Keyingi qutqaruv — 7 kundan keyin._",
                                    parse_mode="Markdown"
                                )
                            except Exception:
                                pass
                        else:
                            habit["streak"] = 0
        # Jon hisoblash
        habits_list = udata.get("habits", [])
        n = len(habits_list)
        if n > 0:
            d = 0
            for h in habits_list:
                # Har ikkala tur uchun ham last_done == yesterday tekshiramiz
                # (repeat uchun done_today_count allaqachon tozalangan bo'ladi)
                if h.get("last_done") == yesterday:
                    d += 1
            # Har bir odat teng ulushga ega: 10% / n
            # Masalan: 3 odat => har biri 3.33%
            jon_before   = udata.get("jon", 100.0)
            step_per_one = 10.0 / n       # har 1 odat uchun ulush
            change       = (d - (n - d)) * step_per_one  # bajarilgan - bajarilmagan
            # pet_rabbit: jon kamayishini 50% yumshatish (faqat change<0 bo'lsa)
            change       = _apply_pet_rabbit_soften(udata, change)
            jon          = round(min(100.0, max(0.0, jon_before + change)), 1)
            udata["jon"] = jon
            changed = True
            # Jon 0% ga yetsa — ogohlantirish xabari yuborish
            if jon <= 0 and jon_before > 0:
                try:
                    user_id_int = int(uid)
                    kb_jon = InlineKeyboardMarkup()
                    kb_jon.add(InlineKeyboardButton("❤️ Bozordan jon sotib olish (50 ball)", callback_data="bozor_buy_jon"))
                    bot.send_message(
                        user_id_int,
                        "*💀 Joningiz 0% ga yetdi!*\n\n"
                        "Kecha barcha odatlaringiz bajarilmadi.\n\n"
                        "Bugun barcha odatlaringizni bajarsangiz jon tiklanadi!\n"
                        "Yoki bozordan *50 ball* evaziga jonni tiklashingiz mumkin.",
                        parse_mode="Markdown",
                        reply_markup=kb_jon
                    )
                except Exception:
                    pass

        if changed:
            try:
                update_data = {
                    "habits":         udata["habits"],
                    "jon":            udata.get("jon", 100),
                    "pending_shield": udata.get("pending_shield", {}),
                    "streak_shields": udata.get("streak_shields", 0),
                    "pet_cat_last_used_date": udata.get("pet_cat_last_used_date", ""),
                }
                mongo_col.update_one({"_id": uid}, {"$set": update_data})
            except Exception:
                pass
    # ── Guruhlar: daily reset ──
    try:
        for gdoc in groups_col.find({}):
            g_id = gdoc["_id"]
            g    = {k: v for k, v in gdoc.items() if k != "_id"}
            # Kecha bajarmagan a'zolarga eslatma yuborish
            done_today = g.get("done_today", {})
            members    = g.get("members", [])
            not_done   = [mid for mid in members if not _is_member_done(done_today.get(str(mid), False))]
            if not_done and done_today:  # Kamida 1 kishi bajariganida
                for mid in not_done:
                    try:
                        bot.send_message(
                            int(mid),
                            f"⏰ *{g['name']}*\n\n"
                            f"Kecha *{g.get('habit_name','—')}* odatini bajarmaganingiz streak uzilishiga olib keldi!\n"
                            f"Bugun bajaring! 💪",
                            parse_mode="Markdown", reply_markup=ok_kb(int(mid))
                        )
                    except Exception as _e: print(f"[warn] xato: {_e}")
            # Streak: agar hammasi bajargan bo'lsa allaqachon +1 bo'lgan
            # Agar hammasi bajarmaganligi bo'lsa streak nollanadi
            done_count = sum(1 for v in done_today.values() if (v is True or (isinstance(v, dict) and True in v.values())))
            if done_count < len(members) and g.get("streak", 0) > 0:
                g["streak"] = 0
            # Yangi kun uchun tozalash
            g["done_today"] = {}
            g["done_date"]  = today_str
            groups_col.update_one({"_id": g_id}, {"$set": g})
    except Exception as e:
        print(f"[daily_reset] guruh reset xatosi: {e}")

    # Kechagi (va undan oldingi) javobsiz eslatma xabarlarini chatdan o'chirish
    # — bugungilar qoladi (hali javob berish vaqti bor)
    try:
        for uid, udata in users.items():
            pending = udata.get("pending_reminders", [])
            if not pending:
                continue
            keep = []
            removed = 0
            for entry in pending:
                entry_date = entry.get("date_uz5", "")
                msg_id     = entry.get("message_id")
                if not entry_date or not msg_id:
                    continue  # Buzuq entry — tushirib yuboramiz
                if entry_date >= today_str:
                    # Bugungi (yoki kelajakdagi) — tegmaymiz
                    keep.append(entry)
                else:
                    # Kechagi yoki eski — chatdan o'chiramiz
                    try:
                        bot.delete_message(int(uid), msg_id)
                    except Exception:
                        pass  # Foydalanuvchi qo'li bilan o'chirgan yoki Telegram 48h limiti
                    removed += 1
            if removed > 0 or len(keep) != len(pending):
                udata["pending_reminders"] = keep
                save_user(int(uid), udata)
    except Exception as e:
        print(f"[daily_reset] pending_reminders tozalash xatosi: {e}")

    # daily_reset ni saqlab, faqat habit jadvallarini tozalash
    all_jobs = schedule.get_jobs()
    for job in all_jobs:
        if "daily_reset" not in job.tags:
            schedule.cancel_job(job)
    load_all_schedules()

def load_all_schedules():
    users = load_all_users(force=True)
    for uid, udata in users.items():
        try:
            user_id = int(uid)
        except ValueError:
            continue
        today = today_uz5()
        for habit in udata.get("habits", []):
            # Bugun allaqachon bajarilgan bo'lsa — rejalashtirmaymiz
            if habit.get("last_done") == today:
                continue
            schedule_habit(user_id, habit)

def send_evening_reminders():
    """Har kuni 21:00 (UTC+5) da — evening_notify=True foydalanuvchilarga bajarilmagan odatlar haqida eslatma."""
    from datetime import timezone, timedelta
    tz_uz = timezone(timedelta(hours=5))
    today = datetime.now(tz_uz).strftime("%Y-%m-%d")
    try:
        users = load_all_users(force=True)
    except Exception as e:
        print(f"[evening] load_all_users xatosi: {e}")
        return
    for uid_str, udata in users.items():
        try:
            if not udata.get("evening_notify", False):
                continue
            habits = udata.get("habits", [])
            undone = [h for h in habits if h.get("last_done") != today]
            if not undone:
                continue
            lang = udata.get("lang", "uz")
            if lang == "ru":
                lines = ["*🌙 Вечернее напоминание*\n\nСегодня ещё не выполнены:"]
                for h in undone:
                    lines.append(f"  {h.get('icon','✅')} {h.get('name','')}")
                lines.append("\n_Ещё есть время! 💪_")
            elif lang == "en":
                lines = ["*🌙 Evening reminder*\n\nNot done yet today:"]
                for h in undone:
                    lines.append(f"  {h.get('icon','✅')} {h.get('name','')}")
                lines.append("\n_You still have time! 💪_")
            else:
                lines = ["*🌙 Kechki eslatma*\n\nBugun hali bajarilmagan odatlar:"]
                for h in undone:
                    lines.append(f"  {h.get('icon','✅')} {h.get('name','')}")
                lines.append("\n_Vaqt bor, ulguring! 💪_")
            text = "\n".join(lines)
            if lang == "ru":
                btn_label = "✅ Понятно"
            elif lang == "en":
                btn_label = "✅ Got it"
            else:
                btn_label = "✅ Tushundim"
            import json as _json
            kb_json = _json.dumps({"inline_keyboard": [[{
                "text": btn_label,
                "callback_data": "evening_dismiss",
                "style": "success"
            }]]})
            bot.send_message(int(uid_str), text, parse_mode="Markdown", reply_markup=kb_json)
        except Exception as e:
            print(f"[evening] uid={uid_str} xato: {e}")

def send_habit_health_warnings():
    """Har juma 11:00 (UTC+5) da — oxirgi 7 kunda foizi past (<30%) odatlar haqida ogohlantirish."""
    from datetime import timezone, timedelta
    tz_uz    = timezone(timedelta(hours=5))
    now_uz   = datetime.now(tz_uz)
    today    = now_uz.strftime("%Y-%m-%d")
    # Faqat juma kuni ishlaydi (weekday 4 = juma)
    if now_uz.weekday() != 4:
        return
    try:
        users = load_all_users(force=True)
    except Exception as e:
        print(f"[health] load_all_users xatosi: {e}")
        return
    warned_count = 0
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            # Bugun allaqachon yuborilganmi?
            if udata.get("habit_health_warned") == today:
                continue
            history = udata.get("history", {})
            lang    = udata.get("lang", "uz")
            weak_habits = []
            for h in habits:
                done_7 = sum(
                    1 for i in range(7)
                    if history.get(
                        (now_uz - timedelta(days=i)).strftime("%Y-%m-%d"), {}
                    ).get("habits", {}).get(h["id"])
                )
                pct = round(done_7 / 7 * 100)
                if pct < 30:
                    weak_habits.append((h.get("icon", "✅"), h.get("name", ""), pct))
            if not weak_habits:
                continue
            # Xabar tuzish
            if lang == "ru":
                lines = ["*⚠️ Слабые привычки на этой неделе:*\n"]
                for icon, name, pct in weak_habits:
                    bar = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
                    lines.append(f"  {icon} *{name}*\n  {bar} {pct}%\n")
                lines.append("_Уделите им больше внимания на следующей неделе! 💪_")
            elif lang == "en":
                lines = ["*⚠️ Weak habits this week:*\n"]
                for icon, name, pct in weak_habits:
                    bar = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
                    lines.append(f"  {icon} *{name}*\n  {bar} {pct}%\n")
                lines.append("_Give them more attention next week! 💪_")
            else:
                lines = ["*⚠️ Bu hafta zaif odatlar:*\n"]
                for icon, name, pct in weak_habits:
                    bar = "█" * round(pct / 10) + "░" * (10 - round(pct / 10))
                    lines.append(f"  {icon} *{name}*\n  {bar} {pct}%\n")
                lines.append("_Keyingi haftada ularga ko'proq e'tibor bering! 💪_")
            text = "\n".join(lines)
            bot.send_message(int(uid_str), text, parse_mode="Markdown", reply_markup=ok_kb(int(uid_str)))
            # Bugun yuborildi — belgilash
            mongo_col.update_one(
                {"_id": uid_str},
                {"$set": {"habit_health_warned": today}},
                upsert=False
            )
            warned_count += 1
            time.sleep(0.05)
        except Exception as e:
            print(f"[health] uid={uid_str} xato: {e}")
    print(f"[health] {warned_count} foydalanuvchiga ogohlantirish yuborildi.")

def resolve_expired_challenges():
    """Muddati o'tgan challengelarni hal qilish — har kuni ishlaydi."""
    import datetime as _dt
    from datetime import timezone, timedelta as _td
    tz_uz     = timezone(_td(hours=5))
    today_str = datetime.now(tz_uz).strftime("%Y-%m-%d")
    yesterday = (datetime.now(tz_uz) - _td(days=1)).strftime("%Y-%m-%d")
    try:
        challenges_col = mongo_db["challenges"]
    except Exception as e:
        print(f"[resolve_challenges] DB xatosi: {e}")
        return

    # ── 1. Pending → expired (3+ kundan beri qabul qilinmagan) ──
    try:
        three_days_ago = (datetime.now(tz_uz) - _td(days=3)).strftime("%Y-%m-%d")
        expired_pending = list(challenges_col.find({
            "status":     "pending",
            "created_at": {"$lte": three_days_ago}
        }))
        for c in expired_pending:
            challenges_col.update_one(
                {"_id": c["_id"]},
                {"$set": {"status": "expired"}}
            )
            # Yuboruvchiga xabar
            try:
                bot.send_message(
                    int(c["from_uid"]),
                    f"⏰ *Challenge muddati o'tdi*\n\n"
                    f"📌 Odat: *{c.get('habit_name','')}*\n"
                    f"Qabul qilinmadi — challenge bekor qilindi.",
                    parse_mode="Markdown",
                    reply_markup=ok_kb(int(c["from_uid"]))
                )
            except Exception:
                pass
        if expired_pending:
            print(f"[resolve_challenges] {len(expired_pending)} ta pending challenge expired qilindi")
    except Exception as e:
        print(f"[resolve_challenges] Pending expiry xatosi: {e}")

    # ── 2. Active → completed (expires_at <= yesterday) ──
    try:
        expired_active = list(challenges_col.find({
            "status":     "active",
            "expires_at": {"$lte": yesterday}
        }))
        for c in expired_active:
            from_uid    = c.get("from_uid", "")
            to_uid      = c.get("to_uid", "")
            bet         = c.get("bet", 50)
            accepted_at = c.get("accepted_at", c.get("created_at", ""))
            expires_at  = c.get("expires_at", yesterday)

            # done_log kunlarini hisoblash (accepted_at dan expires_at gacha)
            def count_done(uid_str):
                try:
                    u = load_user(int(uid_str))
                    if not u:
                        return 0
                    dl = u.get("done_log", {})
                    return sum(1 for d, v in dl.items() if v and accepted_at <= d <= expires_at)
                except Exception:
                    return 0

            from_score = count_done(from_uid)
            to_score   = count_done(to_uid)

            # G'olib aniqlash
            if from_score > to_score:
                winner_uid, loser_uid = from_uid, to_uid
                winner_score, loser_score = from_score, to_score
            elif to_score > from_score:
                winner_uid, loser_uid = to_uid, from_uid
                winner_score, loser_score = to_score, from_score
            else:
                winner_uid = None  # Durrang

            if winner_uid:
                # G'olib bet*2 oladi
                try:
                    u_w = load_user(int(winner_uid))
                    u_l = load_user(int(loser_uid))
                    if u_w:
                        u_w["points"] = u_w.get("points", 0) + bet * 2
                        save_user(int(winner_uid), u_w)
                    # G'olib xabari
                    w_name = u_w.get("name", "G'olib") if u_w else "G'olib"
                    l_name = u_l.get("name", "Raqib") if u_l else "Raqib"
                    try:
                        bot.send_message(
                            int(winner_uid),
                            f"🏆 *Challenge tugadi — Siz g'olib bo'ldingiz!*\n\n"
                            f"📌 Odat: *{c.get('habit_name','')}*\n"
                            f"📊 Natija: *{winner_score}* kun vs {loser_score} kun\n"
                            f"💰 *+{bet * 2} ball* hisobingizga qo'shildi!",
                            parse_mode="Markdown",
                            reply_markup=ok_kb(int(winner_uid))
                        )
                    except Exception:
                        pass
                    try:
                        bot.send_message(
                            int(loser_uid),
                            f"😔 *Challenge tugadi — {w_name} g'olib bo'ldi*\n\n"
                            f"📌 Odat: *{c.get('habit_name','')}*\n"
                            f"📊 Natija: {loser_score} kun vs *{winner_score}* kun\n"
                            f"Keyingi safar omad! 💪",
                            parse_mode="Markdown",
                            reply_markup=ok_kb(int(loser_uid))
                        )
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[resolve_challenges] Winner reward xatosi: {e}")
            else:
                # Durrang — ikkalasi ham bet qaytariladi
                for ruid in [from_uid, to_uid]:
                    try:
                        u_r = load_user(int(ruid))
                        if u_r:
                            u_r["points"] = u_r.get("points", 0) + bet
                            save_user(int(ruid), u_r)
                        bot.send_message(
                            int(ruid),
                            f"🤝 *Challenge durrang tugadi!*\n\n"
                            f"📌 Odat: *{c.get('habit_name','')}*\n"
                            f"📊 Natija: {from_score} kun vs {to_score} kun\n"
                            f"💰 *+{bet} ball* (garov qaytarildi)",
                            parse_mode="Markdown",
                            reply_markup=ok_kb(int(ruid))
                        )
                    except Exception:
                        pass

            challenges_col.update_one(
                {"_id": c["_id"]},
                {"$set": {
                    "status":       "completed",
                    "resolved_at":  today_str,
                    "from_score":   from_score,
                    "to_score":     to_score,
                    "winner_uid":   winner_uid or "tie",
                }}
            )
        if expired_active:
            print(f"[resolve_challenges] {len(expired_active)} ta active challenge hal qilindi")
    except Exception as e:
        print(f"[resolve_challenges] Active resolve xatosi: {e}")

def scheduler_loop():
    from datetime import timezone, timedelta
    tz_uz = timezone(timedelta(hours=5))
    # Bot ishga tushganda: agar bugun hali daily_reset ishlamagan bo'lsa — darhol ishlat
    last_reset_date = None
    now_uz = datetime.now(tz_uz)
    today_str = now_uz.strftime("%Y-%m-%d")
    # daily_reset ni birinchi marta sinxron ishlatish (kechagi reset o'tkazib yuborilgan bo'lsa)
    try:
        # Istalgan foydalanuvchidan bitta repeat odatni olib tekshirish
        users = load_all_users(force=True)
        needs_reset = False
        for uid, udata in users.items():
            for h in udata.get("habits", []):
                if h.get("type") == "repeat" and h.get("done_today_count", 0) > 0:
                    # done_today_count > 0 lekin last_done bugun emas — reset kerak
                    if h.get("last_done") != today_str:
                        needs_reset = True
                        break
            if needs_reset:
                break
        if needs_reset:
            print("[scheduler_loop] O'tkazib yuborilgan reset topildi — darhol daily_reset ishlatilmoqda")
            daily_reset()
    except Exception as e:
        print(f"[scheduler_loop] Startup reset xatosi: {e}")

    load_all_schedules()
    # Har kuni 00:00 (UTC+5 = 19:00 UTC) da reset
    schedule.every().day.at("19:00").do(daily_reset).tag("daily_reset")
    # Har kuni 21:00 (UTC+5 = 16:00 UTC) da kechki eslatma
    schedule.every().day.at("16:00").do(send_evening_reminders).tag("evening_reminder")
    schedule.every().day.at("19:00").do(group_daily_reset).tag("group_daily_reset")
    # Har kuni 00:05 (UTC+5 = 19:05 UTC) da muddati o'tgan challengelar hal qilinadi
    schedule.every().day.at("19:05").do(resolve_expired_challenges).tag("challenge_resolve")
    # Har juma 11:00 (UTC+5 = 06:00 UTC) da odat sog'liqligi tekshiruvi
    schedule.every().friday.at("06:00").do(send_habit_health_warnings).tag("habit_health")
    # Har dushanba 09:00 (UTC+5 = 04:00 UTC) da haftalik hisobot
    schedule.every().monday.at("04:00").do(send_weekly_reports).tag("weekly_report")
    # Har oyning 1-kuni 09:00 (UTC+5 = 04:00 UTC) da oylik hisobot
    schedule.every().day.at("04:01").do(
        lambda: send_monthly_reports() if __import__('datetime').datetime.now(
            __import__('datetime').timezone(__import__('datetime').timedelta(hours=5))
        ).day == 1 else None
    ).tag("monthly_report")
    # Har yilning 1-yanvari 09:00 (UTC+5 = 04:00 UTC) da yillik hisobot
    schedule.every().day.at("04:02").do(
        lambda: send_yearly_reports() if (
            __import__('datetime').datetime.now(
                __import__('datetime').timezone(__import__('datetime').timedelta(hours=5))
            ).month == 1 and
            __import__('datetime').datetime.now(
                __import__('datetime').timezone(__import__('datetime').timedelta(hours=5))
            ).day == 1
        ) else None
    ).tag("yearly_report")
    while True:
        schedule.run_pending()
        time.sleep(30)


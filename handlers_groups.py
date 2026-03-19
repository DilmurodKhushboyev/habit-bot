"""
handlers_groups.py
==================
Oylik/yillik hisobotlar, eslatmalar, scheduler (rejalashtiruvchi),
yangi odat saqlash, guruh funksiyalari, matn handler, to'lov, broadcast.
Bu faylda: send_monthly_reports, send_yearly_reports, send_reminder,
           scheduler_loop, _save_new_habit, handle_text, _run_broadcast va boshqalar.
Bog'liq fayllar: config.py, database.py, languages.py, keyboards.py, handlers_habits.py
"""

import telebot
import os
import requests
import json
import schedule
import time
import threading
import random
import io
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineQueryResultCachedPhoto, SwitchInlineQueryChosenChat
)
from config import BOT_TOKEN, ADMIN_ID, mongo_col, groups_col
from database import load_user, save_user, load_settings, save_settings, load_group, save_group, delete_group, load_all_users, count_users, invalidate_users_cache
from languages import T, get_lang, LANGS, get_rank, MOTIVATSIYA, today_uz5
from keyboards import (bot, main_menu, main_menu_dict, send_message_colored,
                       edit_message_colored, cBtn, ok_kb, kb_to_dict,
                       send_main_menu, build_main_text, done_keyboard,
                       menu2_dict, build_menu2_text, send_menu2,
                       check_subscription, send_sub_required,
                       admin_menu, admin_broadcast_menu, admin_stats_period_menu)
from handlers_habits import (send_onboarding_time, finish_onboarding,
                              send_weekly_reports)

# ============================================================
#  OYLIK HISOBOT
# ============================================================
def build_monthly_report_text(uid, report):
    month_label  = report.get("month_label", "—")
    done_pct     = report.get("done_pct", 0)
    jon_start    = report.get("jon_start", 100)
    jon_end      = report.get("jon_end", 100)
    jon_change   = round(jon_end - jon_start, 1)
    jon_sign     = "+" if jon_change >= 0 else ""
    best_streak  = report.get("best_streak", 0)
    balls_earned = report.get("balls_earned", 0)
    best_habit   = report.get("best_habit", "—")
    worst_habit  = report.get("worst_habit", "—")
    weeks_count  = report.get("weeks_count", 4)

    if done_pct >= 80:   grade = "🏆 Ajoyib oy!"
    elif done_pct >= 60: grade = "✅ Yaxshi oy"
    elif done_pct >= 40: grade = "💪 O'rtacha oy"
    else:                grade = "⚠️ Qiyin oy"

    if jon_end >= 80:   je = "❤️"
    elif jon_end >= 50: je = "🧡"
    elif jon_end >= 20: je = "💛"
    else:               je = "🖤"

    text  = f"📆 *{month_label}*\n"
    text += "▬" * 16 + "\n\n"
    text += f"{grade}\n\n"
    text += f"*🎯 Bajarildi:* {done_pct}%\n"
    text += f"*{je} Jon:* {jon_start}% → {jon_end}% ({jon_sign}{jon_change}%)\n"
    text += f"*🔥 Eng uzun streak:* {best_streak} kun\n"
    text += f"*⭐ Yig'ilgan ball:* +{balls_earned}\n"
    text += f"*📅 Jami hafta:* {weeks_count} ta\n\n"
    text += "▬" * 16 + "\n"
    text += f"*🏆 Eng yaxshi odat:* {best_habit}\n"
    text += f"*⚠️ Eng kam bajarilgan:* {worst_habit}\n"
    return text

def send_monthly_reports():
    from datetime import timezone, timedelta
    tz_uz   = timezone(timedelta(hours=5))
    now     = datetime.now(tz_uz)
    # O'tgan oy
    first_this = now.date().replace(day=1)
    last_month = first_this - timedelta(days=1)
    month_label = last_month.strftime("%B %Y")
    import calendar
    days_in_month = calendar.monthrange(last_month.year, last_month.month)[1]
    weeks_count = round(days_in_month / 7)
    users = load_all_users(force=True)
    print(f"[monthly_report] {len(users)} foydalanuvchiga yuborilmoqda...")
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            uid_int   = int(uid_str)
            jon_end   = udata.get("jon", 100)
            jon_start = max(0, min(100, round(jon_end - (jon_end - 50) * 0.3)))
            total_possible = 0
            total_done_m   = 0
            habit_scores   = []
            best_streak    = 0
            for h in habits:
                rep  = h.get("repeat_count", 1) if h.get("type") == "repeat" else 1
                done = min(h.get("total_done", 0), rep * days_in_month)
                poss = rep * days_in_month
                total_possible += poss
                total_done_m   += done
                score = round(done / poss * 100) if poss else 0
                habit_scores.append((h["name"], score))
                if h.get("streak", 0) > best_streak:
                    best_streak = h.get("streak", 0)
            done_pct     = round(total_done_m / total_possible * 100) if total_possible else 0
            balls_earned = total_done_m * 5
            habit_scores.sort(key=lambda x: x[1], reverse=True)
            best_habit  = habit_scores[0][0]  if habit_scores else "—"
            worst_habit = habit_scores[-1][0] if habit_scores else "—"
            report = {
                "month_label":  month_label,
                "done_pct":     done_pct,
                "jon_start":    jon_start,
                "jon_end":      jon_end,
                "best_streak":  best_streak,
                "balls_earned": balls_earned,
                "best_habit":   best_habit,
                "worst_habit":  worst_habit,
                "weeks_count":  weeks_count,
            }
            try:
                mongo_col.update_one(
                    {"_id": uid_str},
                    {"$push": {"monthly_reports": report}},
                    upsert=False
                )
            except Exception as e:
                print(f"[monthly_report] MongoDB xato {uid_str}: {e}")
            text = "📊 *Oylik hisobotingiz tayyor!*\n\n"
            text += build_monthly_report_text(uid_int, report)
            bot.send_message(uid_int, text, parse_mode="Markdown", reply_markup=ok_kb())
            time.sleep(0.05)
        except Exception as e:
            print(f"[monthly_report] Xato {uid_str}: {e}")
    print("[monthly_report] Yuborildi.")

# ============================================================
#  YILLIK HISOBOT
# ============================================================
def build_yearly_report_text(uid, report):
    year_label   = report.get("year_label", "—")
    done_pct     = report.get("done_pct", 0)
    jon_start    = report.get("jon_start", 100)
    jon_end      = report.get("jon_end", 100)
    jon_change   = round(jon_end - jon_start, 1)
    jon_sign     = "+" if jon_change >= 0 else ""
    best_streak  = report.get("best_streak", 0)
    balls_total  = report.get("balls_total", 0)
    best_habit   = report.get("best_habit", "—")
    worst_habit  = report.get("worst_habit", "—")
    best_month   = report.get("best_month", "—")

    if done_pct >= 80:   grade = "🏆 Zo'r yil!"
    elif done_pct >= 60: grade = "✅ Yaxshi yil"
    elif done_pct >= 40: grade = "💪 O'rtacha yil"
    else:                grade = "⚠️ Qiyin yil"

    if jon_end >= 80:   je = "❤️"
    elif jon_end >= 50: je = "🧡"
    elif jon_end >= 20: je = "💛"
    else:               je = "🖤"

    text  = f"🗓 *{year_label}*\n"
    text += "▬" * 16 + "\n\n"
    text += f"{grade}\n\n"
    text += f"*🎯 Bajarildi:* {done_pct}%\n"
    text += f"*{je} Jon:* {jon_start}% → {jon_end}% ({jon_sign}{jon_change}%)\n"
    text += f"*🔥 Eng uzun streak:* {best_streak} kun\n"
    text += f"*⭐ Jami ball:* {balls_total:,}\n"
    text += f"*📅 Jami hafta:* 52 ta\n"
    text += f"*📆 Jami oy:* 12 ta\n\n"
    text += "▬" * 16 + "\n"
    text += f"*🏆 Eng yaxshi odat:* {best_habit}\n"
    text += f"*⚠️ Eng kam bajarilgan:* {worst_habit}\n"
    text += f"*🌟 Eng yaxshi oy:* {best_month}\n"
    return text

def send_yearly_reports():
    from datetime import timezone, timedelta
    tz_uz    = timezone(timedelta(hours=5))
    now      = datetime.now(tz_uz)
    last_year = now.year - 1
    year_label = f"{last_year}-yil"
    users = load_all_users(force=True)
    print(f"[yearly_report] {len(users)} foydalanuvchiga yuborilmoqda...")
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            uid_int   = int(uid_str)
            jon_end   = udata.get("jon", 100)
            jon_start = max(0, min(100, round(jon_end - (jon_end - 50) * 0.5)))
            total_possible = 0
            total_done_y   = 0
            habit_scores   = []
            best_streak    = 0
            for h in habits:
                rep  = h.get("repeat_count", 1) if h.get("type") == "repeat" else 1
                done = min(h.get("total_done", 0), rep * 365)
                poss = rep * 365
                total_possible += poss
                total_done_y   += done
                score = round(done / poss * 100) if poss else 0
                habit_scores.append((h["name"], score))
                if h.get("streak", 0) > best_streak:
                    best_streak = h.get("streak", 0)
            done_pct    = round(total_done_y / total_possible * 100) if total_possible else 0
            balls_total = udata.get("points", 0)
            habit_scores.sort(key=lambda x: x[1], reverse=True)
            best_habit  = habit_scores[0][0]  if habit_scores else "—"
            worst_habit = habit_scores[-1][0] if habit_scores else "—"
            # Eng yaxshi oy — monthly_reports dan topamiz
            monthly_reps = udata.get("monthly_reports", [])
            if monthly_reps:
                best_m = max(monthly_reps, key=lambda r: r.get("done_pct", 0))
                best_month = best_m.get("month_label", "—")
            else:
                best_month = "—"
            report = {
                "year_label":  year_label,
                "done_pct":    done_pct,
                "jon_start":   jon_start,
                "jon_end":     jon_end,
                "best_streak": best_streak,
                "balls_total": balls_total,
                "best_habit":  best_habit,
                "worst_habit": worst_habit,
                "best_month":  best_month,
            }
            try:
                mongo_col.update_one(
                    {"_id": uid_str},
                    {"$push": {"yearly_reports": report}},
                    upsert=False
                )
            except Exception as e:
                print(f"[yearly_report] MongoDB xato {uid_str}: {e}")
            text = "📊 *Yillik hisobotingiz tayyor!*\n\n"
            text += build_yearly_report_text(uid_int, report)
            bot.send_message(uid_int, text, parse_mode="Markdown", reply_markup=ok_kb())
            time.sleep(0.05)
        except Exception as e:
            print(f"[yearly_report] Xato {uid_str}: {e}")
    print("[yearly_report] Yuborildi.")

# ============================================================
#  ESLATMA
# ============================================================
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
        bot.send_message(
            user_id,
            text,
            parse_mode="Markdown",
            reply_markup=done_keyboard(user_id, habit["id"])
        )
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
        bot.send_message(uid, text, parse_mode="Markdown")
    except Exception as e:
        print(f"[milestone] xato {uid}: {e}")

def schedule_habit(user_id, habit):
    # Avval eski jadval bo'lsa o'chiramiz (dublikat bo'lmasligi uchun)
    schedule.clear(f"{user_id}_{habit['id']}")
    # Vaqtsiz odatni rejalashtirmaymiz
    t = habit.get("time", "vaqtsiz")
    if not t or t in ("vaqtsiz", "—", "", None):
        return
    # Foydalanuvchi UTC+5 da vaqt kiritadi, Railway UTC da ishlaydi
    try:
        h, m = map(int, t.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        total    = h * 60 + m - 5 * 60
        total    = total % (24 * 60)
        utc_h    = total // 60
        utc_m    = total % 60
        utc_time = f"{utc_h:02d}:{utc_m:02d}"
    except Exception:
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
                                    parse_mode="Markdown"
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
                        # Himoya yo'q — streak nollanadi
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
                            parse_mode="Markdown", reply_markup=ok_kb()
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
            bot.send_message(int(uid_str), text, parse_mode="Markdown")
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
                    parse_mode="Markdown"
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
                            parse_mode="Markdown"
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
                            parse_mode="Markdown"
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
                            parse_mode="Markdown"
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

# ============================================================
#  YANGI ODAT SAQLASH (markaziy funksiya)
# ============================================================
def _save_new_habit(uid, u):
    """Yangi odat yaratib saqlash va jadval o'rnatish"""
    import uuid
    temp = u.get("temp_habit", {})
    name = temp.get("name", "").strip()
    if not name:
        send_main_menu(uid)
        return
    hab_type  = temp.get("type", "simple")
    time_val  = temp.get("time", "vaqtsiz")
    today_str = today_uz5()

    if hab_type == "repeat":
        times_list  = temp.get("times_collected", [time_val])
        rep_count   = len(times_list)
        main_time   = times_list[0] if times_list else "vaqtsiz"
        new_habit = {
            "id":              str(uuid.uuid4())[:8],
            "name":            name,
            "type":            "repeat",
            "repeat_count":    rep_count,
            "repeat_times":    times_list,
            "time":            main_time,
            "streak":          0,
            "total_done":      0,
            "total_missed":    0,
            "done_today_count":0,
            "last_done":       None,
            "started_at":      today_str,
        }
    else:
        new_habit = {
            "id":           str(uuid.uuid4())[:8],
            "name":         name,
            "type":         "simple",
            "time":         time_val,
            "streak":       0,
            "total_done":   0,
            "total_missed": 0,
            "last_done":    None,
            "started_at":   today_str,
        }

    habits = u.get("habits", [])
    habits.append(new_habit)
    u["habits"] = habits
    u["state"]  = None
    u.pop("temp_habit", None)
    u.pop("temp_msg_id", None)
    save_user(uid, u)

    if time_val != "vaqtsiz":
        schedule_habit(uid, new_habit)

    time_show = time_val if time_val != "vaqtsiz" else "—"
    sent = bot.send_message(
        uid,
        T(uid, "habit_added", name=name, time=time_show),
        parse_mode="Markdown"
    )
    def del_and_back(chat_id, mid):
        time.sleep(5)
        try: bot.delete_message(chat_id, mid)
        except: pass
        # Odat qo'shish menyusiga qaytish
        u2 = load_user(chat_id)
        menu_dict = {
            "inline_keyboard": [
                [{"text": "📌 Oddiy", "callback_data": "habit_type_simple"},
                 {"text": "🔁 Takrorlanuvchi", "callback_data": "habit_type_repeat"}],
                [{"text": T(chat_id, "btn_home"), "callback_data": "menu_main", "style": "primary"}]
            ]
        }
        s = send_message_colored(chat_id, T(chat_id, "add_more_habits"), menu_dict)
        if s is None:
            kb = InlineKeyboardMarkup()
            kb.row(
                InlineKeyboardButton("📌 Oddiy", callback_data="habit_type_simple"),
                InlineKeyboardButton("🔁 Takrorlanuvchi", callback_data="habit_type_repeat")
            )
            kb.add(cBtn(T(chat_id, "btn_home"), "menu_main", "primary"))
            s = bot.send_message(chat_id, T(chat_id, "add_more_habits"), parse_mode="Markdown", reply_markup=kb)
        u2["main_msg_id"] = s.message_id
        save_user(chat_id, u2)
    threading.Thread(target=del_and_back, args=(uid, sent.message_id), daemon=True).start()

# ============================================================
#  GURUH VIEW YORDAMCHI FUNKSIYA
# ============================================================
def _send_group_view(uid, u, g, g_id):
    """Guruh ichki menyusini ko'rsatish"""
    members    = g.get("members", [])
    today      = today_uz5()
    done_today = g.get("done_today", {})
    if g.get("done_date") != today:
        done_today = {}
    is_admin   = (str(g.get("admin_id","")) == str(uid))
    habits     = g.get("habits", [])

    # Agar eski tizim — bitta odat (habit_name) ni ham ko'rsatamiz
    if not habits and g.get("habit_name"):
        habits = [{"id": "main", "name": g["habit_name"], "time": g.get("habit_time","vaqtsiz")}]

    # Matn: sarlavha
    text  = f"👥 *{g['name']}*\n"
    text += "━" * 16 + "\n"
    text += f"🔥 Streak: *{g.get('streak',0)} kun*   👤 *{len(members)} a'zo*\n\n"

    # Odatlar va progress
    text += "━" * 16 + "\n"
    for h in habits:
        h_id       = h["id"]
        h_name     = h["name"]
        h_time     = h.get("time","vaqtsiz")
        done_count = 0
        for mid in members:
            dt_val = done_today.get(str(mid), {})
            if isinstance(dt_val, dict):
                if dt_val.get(h_id, False):
                    done_count += 1
            else:
                if bool(dt_val) and h_id == "main":
                    done_count += 1
        text += f"\n📌 *{h_name}*"
        if h_time != "vaqtsiz":
            text += f"  ⏰ {h_time}"
        text += f"\n👥 Progress: {done_count}/{len(members)}\n"
        # A'zolar holati
        for mid in members:
            mu     = load_user(mid)
            m_name = mu.get("name","?")
            dt_val = done_today.get(str(mid), {})
            if isinstance(dt_val, dict):
                m_done = dt_val.get(h_id, False)
            else:
                m_done = bool(dt_val) if h_id == "main" else False
            status = "✅" if m_done else "⬜"
            you    = " *(siz)*" if mid == uid else ""
            text  += f"  {status} {m_name}{you}\n"
    text += "━" * 16

    # Tugmalar
    kb_g = InlineKeyboardMarkup()

    # 1-qator: Odat qo'shish | Odat o'chirish (faqat admin)
    if is_admin:
        kb_g.row(
            cBtn("➕ Odat qo'shish",  f"group_habit_add_{g_id}", "primary"),
            cBtn("🗑 Odat o'chirish", f"group_habit_del_{g_id}", "danger")
        )

    # Odatlar — har biri alohida qatorda
    for h in habits:
        h_id   = h["id"]
        h_name = h["name"]
        dt_val = done_today.get(str(uid), {})
        if isinstance(dt_val, dict):
            i_done = dt_val.get(h_id, False)
        else:
            i_done = bool(dt_val) if h_id == "main" else False
        if i_done:
            kb_g.add(InlineKeyboardButton(f"☑️ {h_name}", callback_data=f"group_done_{g_id}_{h_id}"))
        else:
            kb_g.add(cBtn(f"✅ {h_name}", f"group_done_{g_id}_{h_id}", "success"))

    # Taklif havolasi | Guruhni o'chirish (admin) yoki Guruhdan chiqish (a'zo)
    if is_admin:
        kb_g.row(
            cBtn("🔗 Taklif havolasi", f"group_invite_{g_id}",         "primary"),
            cBtn("🗑 Guruhni o'chirish", f"group_delete_confirm_{g_id}", "danger")
        )
    else:
        kb_g.row(
            cBtn("🔗 Taklif havolasi", f"group_invite_{g_id}", "primary"),
            cBtn("🚪 Guruhdan chiqish", f"group_leave_{g_id}", "danger")
        )

    kb_g.add(cBtn("🏠 Asosiy menyu", "menu_main", "primary"))
    return bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_g)

# ============================================================
#  GURUH REYTING YORDAMCHI FUNKSIYA
# ============================================================
def _build_group_rating(uid, g, g_id, period="week"):
    """Guruh reytingini qurish — haftalik yoki oylik"""
    from datetime import timezone, timedelta
    tz_uz   = timezone(timedelta(hours=5))
    today   = datetime.now(tz_uz)
    members = g.get("members", [])

    # Har bir a'zo uchun statistika
    members_data = []
    for mid in members:
        mu       = load_user(mid)
        m_name   = mu.get("name", "?")
        done_log = g.get("member_done_log", {}).get(str(mid), {})
        # done_log = {date_str: True, ...}

        if period == "week":
            # Oxirgi 7 kun
            days   = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
            label  = "Haftalik"
            max_d  = 7
        else:
            # Oxirgi 30 kun
            days   = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
            label  = "Oylik"
            max_d  = 30

        done_count = sum(1 for d in days if done_log.get(d, False))
        streak     = g.get("member_streaks", {}).get(str(mid), 0)
        is_me      = (mid == uid)
        today_done = g.get("done_today", {}).get(str(mid), False)
        members_data.append({
            "name":       m_name,
            "done":       done_count,
            "streak":     streak,
            "is_me":      is_me,
            "today_done": today_done,
            "max":        max_d,
        })

    members_data.sort(key=lambda x: x["done"], reverse=True)

    text  = f"🏆 *{g['name']} — {label} Reyting*\n"
    text += f"📌 _{g.get('habit_name','—')}_\n"
    text += "━" * 16 + "\n\n"

    for i, m in enumerate(members_data, 1):
        medal  = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
        you    = " _(siz)_" if m["is_me"] else ""
        today_s = "✅" if m["today_done"] else "⬜"
        bar_len = round((m["done"] / m["max"]) * 8) if m["max"] > 0 else 0
        bar     = "█" * bar_len + "░" * (8 - bar_len)
        text   += f"{medal} *{m['name']}*{you}\n"
        text   += f"   {today_s} Bugun | 🔥{m['streak']} kun streak\n"
        text   += f"   `{bar}` {m['done']}/{m['max']}\n\n"

    text += "━" * 16

    # Tugmalar: haftalik/oylik filter + orqaga
    other_period = "month" if period == "week" else "week"
    other_label  = "📅 Oylik" if period == "week" else "📅 Haftalik"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(other_label, callback_data=f"group_rating_show_{g_id}_{other_period}"))
    kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
    return text, kb

# ============================================================
#  GURUH YARATISH SAQLASH
# ============================================================
def _save_new_group(uid, u):
    """Yangi guruh yaratib saqlash"""
    import uuid
    temp       = u.get("temp_group", {})
    name       = temp.get("name", "").strip()
    habit_name = temp.get("habit_name", "").strip()
    habit_time = temp.get("time", "vaqtsiz")
    if not name or not habit_name:
        send_menu2(uid)
        return
    admin_groups = [g for g in u.get("groups", []) if str(g.get("admin_id", "")) == str(uid)]
    if len(admin_groups) >= 3:
        bot.send_message(uid, T(uid, "err_max_groups"), parse_mode="Markdown")
        send_menu2(uid)
        return
    g_id = str(uuid.uuid4())[:8]
    group = {
        "id":          g_id,
        "name":        name,
        "habit_name":  habit_name,
        "habit_time":  habit_time,
        "admin_id":    str(uid),
        "members":     [str(uid)],
        "streak":      0,
        "created_at":  today_uz5(),
    }
    save_group(g_id, group)
    # Foydalanuvchi guruhlar ro'yxatiga qo'shish
    groups = u.get("groups", [])
    groups.append({"id": g_id, "name": name, "admin_id": str(uid)})
    u["groups"] = groups
    u.pop("temp_group", None)
    u["state"] = None
    save_user(uid, u)
    # Muvaffaqiyat xabari
    inv_link = f"https://t.me/{get_bot_username()}?start=grp_{g_id}"
    sent = bot.send_message(
        uid,
        f"✅ *Guruh yaratildi!*\n\n"
        f"👥 *{name}*\n"
        f"📌 Odat: *{habit_name}*\n"
        f"⏰ Vaqt: *{habit_time}*\n\n"
        f"🔗 *Invite link:*\n`{inv_link}`\n\n"
        f"_Do'stlaringizga linkni yuboring!_",
        parse_mode="Markdown"
    )
    def del_and_go(chat_id, mid):
        time.sleep(5)
        try: bot.delete_message(chat_id, mid)
        except: pass
        send_menu2(chat_id)
    threading.Thread(target=del_and_go, args=(uid, sent.message_id), daemon=True).start()

def _save_group_habit(uid, u):
    """Guruhga yangi odat qo'shish"""
    import uuid
    temp   = u.get("temp_group_habit", {})
    g_id   = temp.get("g_id")
    h_name = temp.get("name","").strip()
    h_time = temp.get("time","vaqtsiz")
    if not g_id or not h_name:
        return
    g = load_group(g_id)
    if not g or str(g.get("admin_id","")) != str(uid):
        return
    habits = g.get("habits", [])
    # Eski tizim (bitta habit_name) ni ham habits ga ko'chiramiz
    if not habits and g.get("habit_name"):
        habits = [{"id": "main", "name": g["habit_name"], "time": g.get("habit_time","vaqtsiz")}]
    new_h = {"id": str(uuid.uuid4())[:6], "name": h_name, "time": h_time}
    habits.append(new_h)
    g["habits"] = habits
    u.pop("temp_group_habit", None)
    save_user(uid, u)
    save_group(g_id, g)
    # Barcha a'zolarga xabar
    for mid in g.get("members", []):
        try:
            if str(mid) != str(uid):
                bot.send_message(int(mid),
                    f"➕ *{g['name']}* guruhiga yangi odat qo'shildi!\n\n"
                    f"📌 *{h_name}*" + (f"  ⏰ {h_time}" if h_time != "vaqtsiz" else ""),
                    parse_mode="Markdown"
                )
        except Exception as _e: print(f"[warn] send_message: {_e}")
    sent = _send_group_view(uid, u, g, g_id)
    u2 = load_user(uid)
    u2["main_msg_id"] = sent.message_id
    save_user(uid, u2)

# ============================================================
#  MATN HANDLER
# ============================================================
@bot.message_handler(func=lambda m: not (m.text and m.text.startswith("/")), content_types=["text", "photo", "document", "video", "audio", "voice", "sticker", "animation"])
def handle_text(msg):
    import re
    uid   = msg.from_user.id
    text  = msg.text or msg.caption or ""
    u     = load_user(uid)
    state = u.get("state")

    # ── Telefon raqamni matn sifatida kiritish (ro'yxatdan o'tish) ──
    if state == "waiting_phone_reg":
        phone_text = text.strip()
        phone_clean = re.sub(r"[^\d+]", "", phone_text)
        if len(phone_clean) >= 9:
            u["phone"] = phone_clean
            u["state"] = None
            reg_msg_id = u.pop("reg_msg_id", None)
            save_user(uid, u)
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            if reg_msg_id:
                try: bot.delete_message(uid, reg_msg_id)
                except: pass
            # Adminga yangi foydalanuvchi haqida xabar
            try:
                total_users = count_users()
                user_name   = msg.from_user.first_name or "Noma'lum"
                username_str = f"@{msg.from_user.username}" if msg.from_user.username else "—"
                bot.send_message(
                    ADMIN_ID,
                    f"🆕 *Yangi Foydalanuvchi!*\n\n"
                    f"Umumiy: *{total_users}*\n"
                    f"Ismi: *{user_name}*\n"
                    f"Username: {username_str}\n"
                    f"ID: `{uid}`",
                    parse_mode="Markdown", reply_markup=ok_kb()
                )
            except Exception:
                pass
            if not check_subscription(uid):
                sent_rm = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
                def _del_rm_sub_t(cid, mid):
                    time.sleep(2)
                    try: bot.delete_message(cid, mid)
                    except: pass
                threading.Thread(target=_del_rm_sub_t, args=(uid, sent_rm.message_id), daemon=True).start()
                send_sub_required(uid)
                return
            sent_ok = bot.send_message(uid, "✅", reply_markup=ReplyKeyboardRemove())
            def _del_ok_t(cid, mid):
                time.sleep(3)
                try: bot.delete_message(cid, mid)
                except: pass
            threading.Thread(target=_del_ok_t, args=(uid, sent_ok.message_id), daemon=True).start()
            # Referal bonus berish
            referrer_id = u.pop("pending_referrer", None)
            if referrer_id and not u.get("ref_used"):
                try:
                    u["points"] = u.get("points", 0) + 25
                    u["ref_used"] = True
                    sent_ref = bot.send_message(uid,
                        "🎁 *Do\'st taklifi bonusi!*\n\n"
                        "*⭐ +25 ball* hisobingizga qo\'shildi!",
                        parse_mode="Markdown")
                    def _del_ref_t(cid, mid):
                        time.sleep(5)
                        try: bot.delete_message(cid, mid)
                        except: pass
                    threading.Thread(target=_del_ref_t, args=(uid, sent_ref.message_id), daemon=True).start()
                except Exception:
                    pass
                try:
                    u_ref = load_user(referrer_id)
                    u_ref["points"] = u_ref.get("points", 0) + 50
                    refs = u_ref.get("referrals", [])
                    refs.append(uid)
                    u_ref["referrals"] = refs
                    milestone_msg = ""
                    milestones = {5: "🛡 Streak himoyasi (1 ta) qo\'shildi!", 10: "⭐ +100 ball bonus!", 20: "💎 VIP nishon qo\'shildi!"}
                    if len(refs) in milestones:
                        milestone_msg = f"\n\n🏆 *Chegara bonusi:* {milestones[len(refs)]}"
                        if len(refs) == 5:
                            u_ref["streak_shields"] = u_ref.get("streak_shields", 0) + 1
                        elif len(refs) == 10:
                            u_ref["points"] = u_ref.get("points", 0) + 100
                        elif len(refs) == 20:
                            u_ref["is_vip"] = True
                    save_user(referrer_id, u_ref)
                    bot.send_message(referrer_id,
                        f"🎉 *Do\'stingiz botga qo\'shildi!*\n\n"
                        f"*⭐ +50 ball* hisobingizga qo\'shildi!\n"
                        f"*👥 Jami taklif qilganlar:* {len(refs)} ta"
                        + milestone_msg,
                        parse_mode="Markdown", reply_markup=ok_kb())
                except Exception:
                    pass
            # Pending guruh
            pending_g = u.pop("pending_group", None)
            if pending_g:
                try:
                    g = load_group(pending_g)
                    if g and str(uid) not in [str(m) for m in g.get("members", [])]:
                        g["members"].append(str(uid))
                        save_group(pending_g, g)
                        groups = u.get("groups", [])
                        if not any(x.get("id") == pending_g for x in groups):
                            groups.append({"id": pending_g, "name": g["name"], "admin_id": g["admin_id"]})
                            u["groups"] = groups
                        try:
                            g_admin_id = g.get("admin_id")
                            if g_admin_id and str(g_admin_id) != str(uid):
                                bot.send_message(int(g_admin_id),
                                    f"👋 *{u.get('name','Yangi azo')}* guruhga qo\'shildi!\n"
                                    f"👥 *{g['name']}*",
                                    parse_mode="Markdown"
                                )
                        except Exception as _e: print(f"[warn] send_message: {_e}")
                        sent_grp = bot.send_message(uid,
                            f"✅ *{g['name']}* guruhiga qo\'shildingiz!\n"
                            f"📌 Odat: *{g.get('habit_name','—')}*",
                            parse_mode="Markdown", reply_markup=ok_kb()
                        )
                        def _del_grp_t(cid, mid):
                            time.sleep(5)
                            try: bot.delete_message(cid, mid)
                            except: pass
                        threading.Thread(target=_del_grp_t, args=(uid, sent_grp.message_id), daemon=True).start()
                except Exception as e:
                    print(f"[pending_group] xato: {e}")
            # Ism va username saqlash
            u["name"]     = msg.from_user.first_name or "Do'stim"
            u["username"]  = (msg.from_user.username or "").lower()
            save_user(uid, u)
            send_main_menu(uid)
        else:
            try: bot.delete_message(uid, msg.message_id)
            except: pass
            sent_err = bot.send_message(uid, T(uid, "err_wrong_phone"), parse_mode="Markdown")
            def _del_err(cid, mid):
                time.sleep(4)
                try: bot.delete_message(cid, mid)
                except: pass
            threading.Thread(target=_del_err, args=(uid, sent_err.message_id), daemon=True).start()
        return

    # ── Takrorlanuvchi odat - necha marta so'rash ──
    if state == "waiting_repeat_count":
        import re as _re2
        count_text = text.strip()
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            count = int(count_text)
            if count < 1 or count > 20:
                raise ValueError
        except:
            bot.send_message(uid, T(uid, "err_wrong_count"), parse_mode="Markdown")
            return
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        if not u.get("temp_habit"):
            u["state"] = None
            save_user(uid, u)
            send_main_menu(uid)
            return
        u["temp_habit"]["repeat_count"] = count
        u["state"] = "waiting_habit_name"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(uid, T(uid, "ask_habit_name"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Odat nomi ──
    if state == "waiting_habit_name":
        # temp_habit yo'q bo'lsa — xavfsiz holda asosiy menyuga qaytish
        if not u.get("temp_habit"):
            u["state"] = None
            save_user(uid, u)
            send_main_menu(uid)
            return
        habit_name = text.strip()
        if not habit_name:
            return
        old_msg_id = u.pop("temp_msg_id", None)
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        u["temp_habit"]["name"] = habit_name
        hab_type = u["temp_habit"].get("type", "simple")
        u["state"] = "waiting_habit_time"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("⏩ Vaqtsiz qo'shish", callback_data="habit_no_time"))
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        if hab_type == "repeat":
            prompt = (
                f"✅ *{habit_name}*\n\n"
                "🔁 Bu takrorlanuvchi odat.\n"
                "⏰ *1-vaqtni* kiriting:\n_Masalan: 06:00_\n\nYoki vaqtsiz qo'shing:"
            )
        else:
            prompt = (
                f"✅ *{habit_name}*\n\n"
                "⏰ Vaqtini kiriting:\n_Masalan: 07:00, 18:30_\n\nYoki vaqtsiz qo'shing:"
            )
        sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Odat vaqti (oddiy yoki repeat birinchi vaqt) ──
    if state == "waiting_habit_time":
        time_text = text.strip()
        if not re.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        old_msg_id = u.pop("temp_msg_id", None)
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass

        hab_type = u.get("temp_habit", {}).get("type", "simple")
        if hab_type == "repeat":
            # temp_habit yo'q bo'lsa xavfsiz fallback
            if not u.get("temp_habit"):
                u["state"] = None
                save_user(uid, u)
                send_main_menu(uid)
                return
            collected = u["temp_habit"].get("times_collected", [])
            collected.append(time_text)
            u["temp_habit"]["times_collected"] = collected
            rep_count = u["temp_habit"].get("repeat_count", len(collected))
            if len(collected) < rep_count:
                # Yana vaqt kerak
                save_user(uid, u)
                cancel_kb = InlineKeyboardMarkup()
                cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
                sent = bot.send_message(
                    uid,
                    f"⏰ *{len(collected)+1}/{rep_count}* — Keyingi vaqtni kiriting:\n_Masalan: 18:00_",
                    parse_mode="Markdown", reply_markup=cancel_kb
                )
                u["temp_msg_id"] = sent.message_id
                save_user(uid, u)
            else:
                # Barcha vaqtlar to'plandi - saqlash
                save_user(uid, u)
                _save_new_habit(uid, u)
        else:
            u["temp_habit"]["time"] = time_text
            _save_new_habit(uid, u)
        return

    # ── Odat vaqtini tahrirlash (sozlamalar) ──
    if state == "editing_habit_time":
        time_text = text.strip()
        if not re.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass

        habit_id = u.get("editing_habit_id")
        h_type   = u.get("editing_habit_type", "simple")
        if h_type == "repeat":
            collected = u.get("editing_habit_times_collected", [])
            collected.append(time_text)
            rep_count = u.get("editing_habit_rep_count", 1)
            u["editing_habit_times_collected"] = collected
            if len(collected) < rep_count:
                save_user(uid, u)
                cancel_kb = InlineKeyboardMarkup()
                cancel_kb.add(cBtn(T(uid, "btn_cancel"), "settings_habits_time", "danger"))
                sent = bot.send_message(
                    uid,
                    f"⏰ *{len(collected)+1}/{rep_count}* vaqtni kiriting:\n_Masalan: 06:00_",
                    parse_mode="Markdown", reply_markup=cancel_kb
                )
                u["temp_msg_id"] = sent.message_id
                save_user(uid, u)
                return
            # To'liq to'plandi
            for h in u.get("habits", []):
                if h["id"] == habit_id:
                    schedule.clear(f"{uid}_{habit_id}")
                    h["repeat_times"] = collected
                    h["time"]         = collected[0]
                    h["repeat_count"] = rep_count
                    schedule_habit(uid, h)
                    break
        else:
            if habit_id == "ALL":
                for h in u.get("habits", []):
                    schedule.clear(f"{uid}_{h['id']}")
                    h["time"] = time_text
                    schedule_habit(uid, h)
            else:
                for h in u.get("habits", []):
                    if h["id"] == habit_id:
                        schedule.clear(f"{uid}_{habit_id}")
                        h["time"] = time_text
                        schedule_habit(uid, h)
                        break
        u["state"] = None
        u.pop("editing_habit_id", None)
        u.pop("editing_habit_times_collected", None)
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_time_updated"))
        def del_ok_time(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_time, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Barcha odatlar uchun umumiy vaqt ──
    if state == "editing_all_habits_time":
        time_text = text.strip()
        if not re.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        for h in u.get("habits", []):
            schedule.clear(f"{uid}_{h['id']}")
            h["time"] = time_text
            schedule_habit(uid, h)
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_all_times", time=time_text), parse_mode="Markdown")
        def del_ok_all_time(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_all_time, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Ismni yangilash ──
    if state == "updating_name":
        new_name = text.strip()
        if not new_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        info_msg_id = u.pop("info_msg_id", None)
        if info_msg_id:
            try: bot.delete_message(uid, info_msg_id)
            except: pass
        u["name"]  = new_name
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_name_changed", name=new_name), parse_mode="Markdown")
        def del_ok_name(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_name, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Odat nomini o'zgartirish ──
    if state == "renaming_habit":
        new_name = text.strip()
        if not new_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        info_msg_id = u.pop("info_msg_id", None)
        if info_msg_id:
            try: bot.delete_message(uid, info_msg_id)
            except: pass
        habit_id = u.pop("renaming_habit_id", None)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                old_name = h["name"]
                h["name"] = new_name
                break
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_habit_renamed", name=new_name), parse_mode="Markdown")
        def del_ok_rename(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_rename, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Dasturchiga xabar ──
    if state == "waiting_dev_message":
        dev_msg_id = u.pop("dev_msg_id", None)
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        if dev_msg_id:
            try: bot.delete_message(uid, dev_msg_id)
            except: pass
        u["state"] = None
        save_user(uid, u)
        user_name = u.get("name", "Noma'lum")
        try:
            kb_reply = InlineKeyboardMarkup()
            kb_reply.add(InlineKeyboardButton("↩️ Javob berish", callback_data=f"admin_reply_to_{uid}"))
            bot.send_message(
                ADMIN_ID,
                f"💬 *{user_name}* (ID: `{uid}`) dan xabar:\n\n{text}",
                parse_mode="Markdown", reply_markup=kb_reply
            )
        except Exception:
            pass
        sent_ok = bot.send_message(uid, T(uid, "ok_dev_sent"))
        def del_ok_dev(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_dev, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Bozor: ball transfer — ID kiritish ──
    if state == "bozor_waiting_transfer_id":
        target_id_text = text.strip()
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            target_id = int(target_id_text)
            if target_id == uid:
                bot.send_message(uid, T(uid, "err_self_transfer"))
                return
            if not user_exists(target_id):
                bot.send_message(uid, T(uid, "err_user_not_found"))
                return
        except ValueError:
            bot.send_message(uid, T(uid, "err_only_digits"), parse_mode="Markdown")
            return
        u["state"]             = "bozor_waiting_transfer_amount"
        u["transfer_target_id"] = target_id
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        target_u = load_user(target_id)
        sent = bot.send_message(
            uid,
            f"💸 *{target_u.get('name', str(target_id))}* ga necha ball yuborasiz?\n\n"
            f"⭐ Sizda: *{u.get('points', 0)} ball*",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Bozor: ball transfer — miqdor kiritish ──
    if state == "bozor_waiting_transfer_amount":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            amount = int(text.strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            bot.send_message(uid, T(uid, "err_positive_num"), parse_mode="Markdown")
            return
        my_points  = u.get("points", 0)
        target_id  = u.get("transfer_target_id")
        if amount > my_points:
            bot.send_message(uid, T(uid, "err_not_enough_pts", points=my_points), parse_mode="Markdown")
            return
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        target_u = load_user(target_id)
        u["points"] = my_points - amount
        u["state"]  = None
        u.pop("transfer_target_id", None)
        save_user(uid, u)
        target_u["points"] = target_u.get("points", 0) + amount
        save_user(target_id, target_u)
        try:
            bot.send_message(
                target_id,
                f"🎁 *{u.get('name','Kimdir')}* sizga *{amount} ball* yubordi!\n\n⭐ Hisobingiz: {target_u['points']} ball",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        sent_ok = bot.send_message(uid, T(uid, "ok_transfer", amount=amount, points=u["points"]), parse_mode="Markdown")
        def del_ok_transfer(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_transfer, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Bozor: ballarni ayirish ──
    if state == "bozor_waiting_subtract":
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_msg_id = u.pop("temp_msg_id", None)
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        try:
            amount = int(text.strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            bot.send_message(uid, T(uid, "err_positive_num"), parse_mode="Markdown")
            return
        my_points = u.get("points", 0)
        deducted  = min(amount, my_points)
        u["points"] = my_points - deducted
        u["state"]  = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_self_deduct", amount=deducted, points=u['points']), parse_mode="Markdown")
        def del_ok_subtract(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            send_main_menu(chat_id)
        threading.Thread(target=del_ok_subtract, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Admin: foydalanuvchiga ball berish — ID ──
    if state == "admin_waiting_points_id" and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            target_id = int(text.strip())
            if not user_exists(target_id):
                bot.send_message(uid, T(uid, "err_user_not_found"))
                return
        except ValueError:
            bot.send_message(uid, T(uid, "err_only_digits"))
            return
        u["state"] = "admin_waiting_points_amount"
        u["give_target_id"] = target_id
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        target_u = load_user(target_id)
        sent = bot.send_message(
            uid,
            f"🎁 *{target_u.get('name', str(target_id))}* ga necha ball berish yoki ayirish?\n\n"
            "_Minus qo'yish uchun: -50, qo'shish uchun: 100_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["give_points_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Admin: foydalanuvchiga ball berish — miqdor ──
    if state == "admin_waiting_points_amount" and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        try:
            amount = int(text.strip())
        except ValueError:
            bot.send_message(uid, T(uid, "err_enter_number"))
            return
        target_id = u.pop("give_target_id", None)
        if not target_id:
            send_main_menu(uid)
            return
        target_u = load_user(target_id)
        target_u["points"] = max(0, target_u.get("points", 0) + amount)
        save_user(target_id, target_u)
        u["state"] = None
        save_user(uid, u)
        sign = "+" if amount >= 0 else ""
        try:
            bot.send_message(
                target_id,
                T(target_id, "admin_gave_pts", amount=f"{sign}{amount}", points=target_u['points']),
                parse_mode="Markdown"
            )
        except Exception:
            pass
        sent_ok = bot.send_message(uid, f"✅ {sign}{amount} ball berildi. Jami: {target_u['points']}")
        def del_ok_admin_pts(chat_id, mid):
            time.sleep(3)
            try: bot.delete_message(chat_id, mid)
            except: pass
            bot.send_message(chat_id, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        threading.Thread(target=del_ok_admin_pts, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Admin: kanal o'rnatish ──
    if state and state.startswith("admin_waiting_channel_") and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        slot = int(state.split("_")[-1])
        channel = text.strip()
        if not channel.startswith("@"):
            channel = "@" + channel
        settings = load_settings()
        settings[f"required_channel_{slot}"] = channel
        try:
            chat_info = bot.get_chat(channel)
            settings[f"required_channel_title_{slot}"] = chat_info.title or channel
        except Exception:
            settings[f"required_channel_title_{slot}"] = channel
        save_settings(settings)
        u["state"] = None
        save_user(uid, u)
        sent_ok = bot.send_message(uid, f"✅ {slot}-kanal *{channel}* sifatida o'rnatildi!", parse_mode="Markdown")
        def del_ok_ch(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
            bot.send_message(chat_id, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        threading.Thread(target=del_ok_ch, args=(uid, sent_ok.message_id), daemon=True).start()
        return

    # ── Admin: foydalanuvchiga javob ──
    if state and state.startswith("admin_waiting_reply_") and uid == ADMIN_ID:
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        target_id = int(state.split("_")[-1])
        reply_msg_id = u.pop("reply_msg_id", None)
        if reply_msg_id:
            try: bot.delete_message(uid, reply_msg_id)
            except: pass
        u["state"] = None
        save_user(uid, u)
        try:
            bot.send_message(target_id, T(target_id, "admin_reply", text=text), parse_mode="Markdown")
            bot.send_message(uid, "✅ Javob yuborildi.")
        except Exception as e:
            bot.send_message(uid, f"❌ Xato: {e}")
        return

    # ── Guruh yaratish: nom ──
    if state == "group_waiting_name":
        group_name = text.strip()
        if not group_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group"]["name"] = group_name
        u["state"] = "group_waiting_habit"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid,
            f"✅ Guruh nomi: *{group_name}*\n\n"
            "2️⃣ Umumiy odat nomini kiriting:\n"
            "_Masalan: Har kuni 30 bet kitob o'qish_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Guruh yaratish: odat nomi ──
    if state == "group_waiting_habit":
        habit_name = text.strip()
        if not habit_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group"]["habit_name"] = habit_name
        u["state"] = "group_waiting_time"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("⏩ Vaqtsiz", callback_data="group_create_no_time"))
        cancel_kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid,
            f"✅ Odat: *{habit_name}*\n\n"
            "3️⃣ Eslatma vaqtini kiriting:\n"
            "_Masalan: 21:00_\n\n"
            "_Yoki vaqtsiz qo'shish uchun tugmani bosing_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Guruh yaratish: vaqt ──
    if state == "group_waiting_time":
        import re as _re_g
        time_text = text.strip()
        if not _re_g.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group"]["time"] = time_text
        u["state"] = None
        save_user(uid, u)
        _save_new_group(uid, u)
        return

    # ── Guruh odati: nom ──
    if state == "group_habit_waiting_name":
        h_name = text.strip()
        if not h_name:
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group_habit"]["name"] = h_name
        u["state"] = "group_habit_waiting_time"
        save_user(uid, u)
        g_id      = u["temp_group_habit"]["g_id"]
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(InlineKeyboardButton("⏩ Vaqtsiz", callback_data=f"group_habit_no_time_{g_id}"))
        cancel_kb.add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        sent = bot.send_message(uid,
            f"✅ Odat: *{h_name}*\n\n"
            "Eslatma vaqtini kiriting:\n"
            "_Masalan: 08:00_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Guruh odati: vaqt ──
    if state == "group_habit_waiting_time":
        import re as _re_gh
        time_text = text.strip()
        if not _re_gh.match(r'^\d{1,2}:\d{2}$', time_text):
            bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
            return
        try:
            hh, mm = time_text.split(":")
            if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                raise ValueError
            time_text = f"{int(hh):02d}:{int(mm):02d}"
        except:
            bot.send_message(uid, T(uid, "err_time_value"), parse_mode="Markdown")
            return
        try: bot.delete_message(uid, msg.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        u["temp_group_habit"]["time"] = time_text
        u["state"] = None
        save_user(uid, u)
        _save_group_habit(uid, u)
        return

    # ── Onboarding — odat nomini yozish ──
    if state == "onboard_waiting_name":
        habit_name = text.strip()
        if len(habit_name) < 2:
            bot.send_message(uid, T(uid, "err_min_chars"))
            return
        u["state"] = None
        save_user(uid, u)
        send_onboarding_time(uid, habit_name)
        return

    # ── Onboarding — vaqtni yozish ──
    if state == "onboard_waiting_time":
        import re as _re_ob
        t = text.strip()
        if _re_ob.match(r"^\d{1,2}:\d{2}$", t):
            parts = t.split(":")
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                habit_name = u.get("temp_onboard_habit", "Odat")
                u["state"] = None
                save_user(uid, u)
                finish_onboarding(uid, habit_name, f"{h:02d}:{m:02d}")
                return
        bot.send_message(uid, T(uid, "err_time_format"), parse_mode="Markdown")
        return

    # ── Broadcast matn/media (admin) ──
    if state in ("admin_bc_private", "admin_bc_groups", "admin_bc_all") and uid == ADMIN_ID:
        bc_chat_id   = msg.chat.id
        media_grp_id = msg.media_group_id
        if media_grp_id:
            if not hasattr(bot, '_bc_album_buffer'):
                bot._bc_album_buffer = {}
            if media_grp_id not in bot._bc_album_buffer:
                bot._bc_album_buffer[media_grp_id] = {"ids": [], "processing": False}
            buf = bot._bc_album_buffer[media_grp_id]
            buf["ids"].append(msg.message_id)
            if buf["processing"]:
                return
            buf["processing"] = True
            bc_state_cap = state
            bc_uid_cap   = uid
            bc_chat_cap  = bc_chat_id
            def _do_album_broadcast():
                time.sleep(1.5)
                final_ids = bot._bc_album_buffer.pop(media_grp_id, {}).get("ids", [msg.message_id])
                _run_broadcast(bc_uid_cap, bc_chat_cap, final_ids, bc_state_cap)
            threading.Thread(target=_do_album_broadcast, daemon=True).start()
        else:
            threading.Thread(
                target=_run_broadcast,
                args=(uid, msg.chat.id, [msg.message_id], state),
                daemon=True
            ).start()
        return




@bot.pre_checkout_query_handler(func=lambda q: True)
def handle_pre_checkout(query):
    """Telegram Stars to'lovini tasdiqlash"""
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def handle_successful_payment(msg):
    """Stars to'lovi muvaffaqiyatli — itemni berish"""
    uid = msg.from_user.id
    payload = msg.successful_payment.invoice_payload  # "stars_gift_box" formatida
    try:
        item_id = payload.replace("stars_", "", 1)
        u = load_user(uid)
        raw_inv = u.get("inventory", {})
        if isinstance(raw_inv, list):
            inventory = {i: 1 for i in raw_inv}
        else:
            inventory = dict(raw_inv)
        # gift_box — tasodifiy mukofot
        if item_id == "gift_box":
            import random as _rnd
            gifts = [
                ("points", 100), ("points", 200), ("points", 500),
                ("streak_shields", 1), ("xp_booster_days", 3),
            ]
            gift_type, gift_val = _rnd.choice(gifts)
            if gift_type == "points":
                u["points"] = u.get("points", 0) + gift_val
                msg_text = f"🎁 *Sovga qutisi ochildi!*\n\n🎉 *+{gift_val} ball* qo'shildi!"
            elif gift_type == "streak_shields":
                u["streak_shields"] = u.get("streak_shields", 0) + gift_val
                msg_text = f"🎁 *Sovga qutisi ochildi!*\n\n🛡 *{gift_val} ta streak himoyasi* qo'shildi!"
            elif gift_type == "xp_booster_days":
                u["xp_booster_days"] = u.get("xp_booster_days", 0) + gift_val
                msg_text = f"🎁 *Sovga qutisi ochildi!*\n\n💎 *XP Booster {gift_val} kun* qo'shildi!"
            else:
                msg_text = "🎁 Sovga qutisi ochildi!"
        else:
            inventory[item_id] = inventory.get(item_id, 0) + 1
            msg_text = f"✅ *{item_id}* muvaffaqiyatli olindi!"
        u["inventory"] = inventory
        save_user(uid, u)
        bot.send_message(uid, msg_text, parse_mode="Markdown")
    except Exception as e:
        print(f"[stars] successful_payment xatosi: {e}")


def _run_broadcast(admin_uid, bc_chat_id, msg_ids, state):
    """Broadcast yuborish — matn va album uchun umumiy funksiya"""
    # State ni darhol tozalaymiz — restart bo'lsa ham qotib qolmasin
    try:
        u0 = load_user(admin_uid)
        u0["state"] = None
        save_user(admin_uid, u0)
    except Exception:
        pass
    try:
        users      = load_all_users(force=True)
        sent_count = 0
        failed     = 0
        failed_ids = []
        prog_msg = bot.send_message(admin_uid, f"⏳ Yuborilmoqda... (0/{len(users)} ta)")
        for target_uid_str in users:
            try:
                target_uid_int = int(target_uid_str)
            except (ValueError, TypeError):
                continue
            if target_uid_int == admin_uid:
                continue
            try:
                kb_user = InlineKeyboardMarkup()
                kb_user.add(InlineKeyboardButton("▶️ Start", url=f"https://t.me/{get_bot_username()}?start=bc"))
                for i_mid, mid in enumerate(msg_ids):
                    # Tugmani faqat oxirgi xabarga biriktirish
                    if i_mid == len(msg_ids) - 1:
                        bot.copy_message(
                            chat_id=target_uid_int,
                            from_chat_id=bc_chat_id,
                            message_id=mid,
                            reply_markup=kb_user
                        )
                    else:
                        bot.copy_message(
                            chat_id=target_uid_int,
                            from_chat_id=bc_chat_id,
                            message_id=mid
                        )
                sent_count += 1
                time.sleep(0.05)
            except Exception as e:
                err_str = str(e)
                failed += 1
                if "blocked" not in err_str.lower():
                    failed_ids.append(f"{target_uid_str} ({err_str[:40]})")
                print(f"[broadcast] {target_uid_str} ga yuborib bo'lmadi: {e}")
        try: bot.delete_message(admin_uid, prog_msg.message_id)
        except: pass
        result = f"📢 Xabar yuborildi!\n✅ {sent_count} ta muvaffaqiyatli."
        if failed:
            result += f"\n❌ {failed} ta foydalanuvchiga yetmadi."
        kb_bc = InlineKeyboardMarkup()
        if failed_ids:
            kb_bc.add(InlineKeyboardButton("🔍 Batafsil", callback_data="bc_detail"))
        kb_bc.add(InlineKeyboardButton("✅ Tushunarli", callback_data="bc_confirm"))
        bot.send_message(admin_uid, result, reply_markup=kb_bc)
    except Exception as fatal_e:
        print(f"[broadcast FATAL] {fatal_e}")
        try:
            bot.send_message(admin_uid, f"❌ Broadcast xatolik bilan to'xtadi: {fatal_e}")
        except Exception as _e: print(f"[warn] send_message: {_e}")
    finally:
        u = load_user(admin_uid)
        u["state"] = None
        if failed_ids:
            u["bc_failed_list"] = failed_ids
        save_user(admin_uid, u)


# ── Inline query handler — share card rasmini boshqa chatga yuborish ──
@bot.inline_handler(func=lambda query: True)
def inline_share_handler(query):
    uid = query.from_user.id
    file_id = _share_file_ids.get(uid)
    if not file_id:
        try:
            bot.answer_inline_query(query.id, [], cache_time=0)
        except Exception:
            pass
        return
    try:
        caption_text = "\U0001f4ca " + T(uid, "weekly_share_caption")
        results = [
            InlineQueryResultCachedPhoto(
                id="share_weekly_" + str(uid),
                photo_file_id=file_id,
                caption=caption_text
            )
        ]
        bot.answer_inline_query(query.id, results, cache_time=0, is_personal=True)
    except Exception as e:
        print(f"[inline_share] xato: {e}")



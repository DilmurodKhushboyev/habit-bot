#!/usr/bin/env python3
"""
Guruh funksiyalari: ko'rish, reyting, saqlash
"""

import uuid
import random
from datetime import date, datetime, timedelta, timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (load_user, save_user, load_group, save_group,
                      load_all_users)
from helpers import T, get_lang, today_uz5
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict,
                       get_bot_username)
from menus import send_menu2


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
        from scheduler import schedule_habit
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


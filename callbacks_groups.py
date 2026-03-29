#!/usr/bin/env python3
"""
Guruh callback handlerlari
"""

import time
import threading
import uuid
from datetime import date
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (load_user, save_user, load_group, save_group,
                      delete_group, load_all_users)
from helpers import T, get_lang, today_uz5
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict,
                       get_bot_username, edit_message_colored)
from menus import send_menu2
from groups import (_send_group_view, _build_group_rating,
                    _save_new_group, _save_group_habit)


def handle_group_callbacks(call, uid, cdata, u):
    """Guruh callback larini qayta ishlaydi. True = handled."""

    if cdata == "group_create":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["state"] = "group_waiting_name"
        u["temp_group"] = {}
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(
            uid,
            "👥 *Yangi guruh yaratish*\n\n"
            "1️⃣ Guruh nomini kiriting:\n"
            "_Masalan: Kitob o'qish klubi_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "group_create_no_time":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        temp = u.get("temp_group", {})
        temp["time"] = "vaqtsiz"
        u["temp_group"] = temp
        u["state"] = None
        save_user(uid, u)
        _save_new_group(uid, u)
        return True

    if cdata == "group_delete":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        my_groups = [g for g in u.get("groups", []) if str(g.get("admin_id","")) == str(uid)]
        if not my_groups:
            sent_e = bot.send_message(uid,
                "🗑 *Guruhni o'chirish*\n\nSiz admin bo'lgan guruh yo'q.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return True
        kb_del = InlineKeyboardMarkup()
        for g in my_groups:
            kb_del.add(InlineKeyboardButton(
                f"🗑 {g['name']}", callback_data=f"group_delete_confirm_{g['id']}"
            ))
        kb_del.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid,
            "🗑 *Qaysi guruhni o'chirmoqchisiz?*",
            parse_mode="Markdown", reply_markup=kb_del
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("group_delete_confirm_"):
        g_id = cdata[len("group_delete_confirm_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            cBtn("✅ Ha, o'chir", f"group_delete_yes_{g_id}", "danger"),
            cBtn("❌ Yo'q",       "group_delete", "primary")
        )
        bot.send_message(uid,
            "⚠️ *Guruhni o'chirishni tasdiqlaysizmi?*\n\n"
            "Barcha a'zolar guruhdan chiqariladi!",
            parse_mode="Markdown", reply_markup=kb_confirm
        )
        return True

    if cdata.startswith("group_delete_yes_"):
        g_id = cdata[len("group_delete_yes_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if g and str(g.get("admin_id","")) == str(uid):
            # A'zolarni guruhdan chiqarish
            for member_id in g.get("members", []):
                try:
                    mu = load_user(member_id)
                    mu["groups"] = [x for x in mu.get("groups", []) if x.get("id") != g_id]
                    save_user(member_id, mu)
                    if str(member_id) != str(uid):
                        bot.send_message(int(member_id),
                            f"ℹ️ *{g['name']}* guruhi admin tomonidan o'chirildi.",
                            parse_mode="Markdown", reply_markup=ok_kb()
                        )
                except Exception as _e: print(f"[warn] send_message: {_e}")
            delete_group(g_id)
        send_menu2(uid)
        return True

    if cdata == "group_stats":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        groups = u.get("groups", [])
        if not groups:
            sent_e = bot.send_message(uid,
                "📊 *Guruh statistika*\n\nHali hech qanday guruhga a'zo emassiz.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return True
        text = "📊 *Guruh statistika*\n\n"
        for g_info in groups:
            g = load_group(g_info["id"])
            if not g: continue
            members   = g.get("members", [])
            streak    = g.get("streak", 0)
            text += f"👥 *{g['name']}*\n"
            text += f"   A'zolar: {len(members)} ta\n"
            text += f"   Odat: {g.get('habit_name','—')}\n"
            text += f"   🔥 Streak: {streak} kun\n\n"
        kb_back = InlineKeyboardMarkup()
        kb_back.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata == "group_rating":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        groups = u.get("groups", [])
        if not groups:
            sent_e = bot.send_message(uid,
                "🏆 *Guruh reytingi*\n\nHali hech qanday guruhga a'zo emassiz.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return True
        # Bir necha guruh bo'lsa — tanlash
        if len(groups) == 1:
            target_g_id = groups[0]["id"]
            bot.answer_callback_query(call.id)
            # To'g'ridan group_rating_show ga o'tish
            g = load_group(target_g_id)
            if not g:
                send_menu2(uid)
                return True
            text, kb = _build_group_rating(uid, g, target_g_id, "week")
            sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            # Guruhni tanlash menyusi
            kb_sel = InlineKeyboardMarkup()
            for g_info in groups:
                kb_sel.add(InlineKeyboardButton(
                    f"👥 {g_info['name']}", callback_data=f"group_rating_show_{g_info['id']}_week"
                ))
            kb_sel.add(cBtn("⬅️ Orqaga", "menu2_open", "primary"))
            sent = bot.send_message(uid,
                "🏆 *Guruh reytingi*\n\nQaysi guruhni ko'rmoqchisiz?",
                parse_mode="Markdown", reply_markup=kb_sel
            )
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        return True

    if cdata.startswith("group_rating_show_"):
        # group_rating_show_{g_id}_{period}
        parts  = cdata[len("group_rating_show_"):].rsplit("_", 1)
        g_id   = parts[0]
        period = parts[1] if len(parts) > 1 else "week"
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            send_menu2(uid)
            return True
        text, kb = _build_group_rating(uid, g, g_id, period)
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("group_view_"):
        g_id = cdata[len("group_view_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            send_menu2(uid)
            return True
        sent = _send_group_view(uid, u, g, g_id)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("group_done_"):
        # format: group_done_{g_id}_{h_id}
        rest   = cdata[len("group_done_"):]
        parts  = rest.rsplit("_", 1)
        g_id   = parts[0]
        h_id   = parts[1] if len(parts) > 1 else "main"
        g = load_group(g_id)
        if not g:
            bot.answer_callback_query(call.id)
            return True
        members = g.get("members", [])
        today   = today_uz5()
        if g.get("done_date") != today:
            g["done_today"] = {}
            g["done_date"]  = today
        done_today = g.get("done_today", {})
        uid_str    = str(uid)
        # done_today: {uid_str: {h_id: True/False}}
        if uid_str not in done_today or not isinstance(done_today[uid_str], dict):
            done_today[uid_str] = {}
        already_done = done_today[uid_str].get(h_id, False)
        if already_done:
            # Toggle: bekor qilish
            bot.answer_callback_query(call.id, "↩️ Bekor qilindi")
            done_today[uid_str][h_id] = False
            g["done_today"] = done_today
            done_log = g.get("member_done_log", {})
            if uid_str in done_log:
                done_log[uid_str].pop(today + "_" + h_id, None)
            g["member_done_log"] = done_log
            save_group(g_id, g)
            # Ball ayirish
            u["points"] = max(0, u.get("points", 0) - 5)
            save_user(uid, u)
            main_msg_id = u.get("main_msg_id")
            if main_msg_id:
                try:
                    edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                except Exception as _e: print(f"[warn] edit_message: {_e}")
            return True
        bot.answer_callback_query(call.id, "✅ Bajarildi!")
        done_today[uid_str][h_id] = True
        g["done_today"] = done_today
        done_count = sum(1 for v in done_today.values() if (v is True or (isinstance(v, dict) and True in v.values())))
        u_name = u.get("name", "Foydalanuvchi")
        all_done = done_count == len(members)
        if all_done:
            # Guruh streaki — faqat bugun birinchi marta all_done bo'lganda +1
            if g.get("streak_date") != today:
                g["streak"]      = g.get("streak", 0) + 1
                g["streak_date"] = today
        # member_done_log: {uid_str: {date_str: True}}
        done_log = g.get("member_done_log", {})
        if uid_str not in done_log:
            done_log[uid_str] = {}
        # Streak faqat bugun BIRINCHI marta bajarilganda oshsin
        already_logged_today = done_log[uid_str].get(today, False)
        done_log[uid_str][today] = True
        g["member_done_log"] = done_log
        # member_streaks: {uid_str: int} — faqat birinchi marta
        if not already_logged_today:
            m_streaks   = g.get("member_streaks", {})
            from datetime import timezone, timedelta as _td
            tz_uz       = timezone(_td(hours=5))
            yesterday_s = (datetime.now(tz_uz) - _td(days=1)).strftime("%Y-%m-%d")
            if done_log[uid_str].get(yesterday_s):
                m_streaks[uid_str] = m_streaks.get(uid_str, 0) + 1
            else:
                m_streaks[uid_str] = 1
            g["member_streaks"] = m_streaks
        save_group(g_id, g)
        # Foydalanuvchiga: ball + streak xabari
        h_name_display = next((h["name"] for h in g.get("habits",[])
                               if h["id"] == h_id), g.get("habit_name","Odat"))
        u["points"] = u.get("points", 0) + 5
        save_user(uid, u)
        m_streak_val = g.get("member_streaks", {}).get(uid_str, 1)
        if m_streak_val >= 30:   s_extra = f"\n🔥 Streak: {m_streak_val} kun 🏆"
        elif m_streak_val >= 14: s_extra = f"\n🔥 Streak: {m_streak_val} kun 🌟"
        elif m_streak_val >= 7:  s_extra = f"\n🔥 Streak: {m_streak_val} kun 🔥"
        else:                    s_extra = f"\n🔥 Streak: {m_streak_val} kun"
        sent_msg = bot.send_message(uid,
            f"*✅ {h_name_display}* — bajarildi! *+5 ⭐ ball*" + s_extra,
            parse_mode="Markdown"
        )
        def del_grp_msg(chat_id, msg_id):
            time.sleep(3)
            try: bot.delete_message(chat_id, msg_id)
            except: pass
        threading.Thread(target=del_grp_msg, args=(uid, sent_msg.message_id), daemon=True).start()
        # Boshqa a'zolarga bildirishnoma
        for mid in members:
            if mid == uid:
                continue
            try:
                if all_done:
                    bot.send_message(mid,
                        f"🎉 *{g['name']}*\n\n"
                        f"Bugun barchangiz bajardingiz!\n"
                        f"🔥 *Streak: {g['streak']} kun!*",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
                else:
                    bot.send_message(mid,
                        f"✅ *{u_name}* bajardi!\n"
                        f"👥 *{g['name']}:* {done_count}/{len(members)} a'zo",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
            except Exception as _e: print(f"[warn] send_message: {_e}")
        # Asosiy menyuni yangilash — xuddi toggle_ kabi
        main_msg_id = u.get("main_msg_id")
        if main_msg_id:
            try:
                edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
            except Exception as _e: print(f"[warn] edit_message: {_e}")
        return True

    if cdata.startswith("group_habit_add_"):
        g_id = cdata[len("group_habit_add_"):]
        bot.answer_callback_query(call.id)
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return True
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["state"]      = "group_habit_waiting_name"
        u["temp_group_habit"] = {"g_id": g_id}
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        sent = bot.send_message(uid,
            f"➕ *{g['name']}* — yangi odat\n\n"
            "Odat nomini kiriting:\n"
            "_Masalan: Meditatsiya_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("group_habit_del_"):
        g_id = cdata[len("group_habit_del_"):]
        bot.answer_callback_query(call.id)
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return True
        habits = g.get("habits", [])
        if not habits and g.get("habit_name"):
            habits = [{"id": "main", "name": g["habit_name"]}]
        if not habits:
            bot.answer_callback_query(call.id, "O'chiradigan odat yo'q!")
            return True
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        kb_del = InlineKeyboardMarkup()
        for h in habits:
            kb_del.add(InlineKeyboardButton(
                f"🗑 {h['name']}", callback_data=f"group_habit_del_confirm_{g_id}_{h['id']}"
            ))
        kb_del.add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        sent = bot.send_message(uid,
            f"🗑 *{g['name']}* — qaysi odatni o'chirmoqchisiz?",
            parse_mode="Markdown", reply_markup=kb_del
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("group_habit_del_confirm_"):
        rest  = cdata[len("group_habit_del_confirm_"):]
        # format: g_id_h_id — h_id 6 belgi
        g_id  = rest[:-7]   # oxirgi _h_id (7 belgi: _+6)
        h_id  = rest[-6:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return True
        habits = g.get("habits", [])
        if not habits and g.get("habit_name") and h_id == "main":
            g["habit_name"] = None
            save_group(g_id, g)
        else:
            g["habits"] = [h for h in habits if h["id"] != h_id]
            save_group(g_id, g)
        # A'zolarga xabar
        del_name = next((h["name"] for h in habits if h["id"] == h_id), "Odat")
        for mid in g.get("members", []):
            try:
                if str(mid) != str(uid):
                    bot.send_message(int(mid),
                        f"🗑 *{g['name']}* guruhidan *{del_name}* odati o'chirildi.",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
            except Exception as _e: print(f"[warn] send_message: {_e}")
        sent = _send_group_view(uid, u, g, g_id)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("group_habit_no_time_"):
        g_id = cdata[len("group_habit_no_time_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        old_mid = u.pop("temp_msg_id", None)
        if old_mid:
            try: bot.delete_message(uid, old_mid)
            except: pass
        temp = u.get("temp_group_habit", {})
        temp["time"] = "vaqtsiz"
        u["temp_group_habit"] = temp
        u["state"] = None
        save_user(uid, u)
        _save_group_habit(uid, u)
        return True

    if cdata.startswith("group_approve_"):
        # group_approve_{g_id}_{joiner_uid}
        rest      = cdata[len("group_approve_"):]
        parts     = rest.rsplit("_", 1)
        g_id      = parts[0]
        joiner_id = int(parts[1])
        bot.answer_callback_query(call.id, "✅ Qabul qilindi!")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            return True
        # Guruhga qo'shish
        if str(joiner_id) not in [str(m) for m in g.get("members", [])]:
            g["members"].append(str(joiner_id))
            save_group(g_id, g)
        ju = load_user(joiner_id)
        groups = ju.get("groups", [])
        if not any(x.get("id") == g_id for x in groups):
            groups.append({"id": g_id, "name": g["name"], "admin_id": g["admin_id"]})
            ju["groups"] = groups
            save_user(joiner_id, ju)
        # Adminga: tasdiq xabari (5s dan keyin o'chadi)
        admin_name = u.get("name", "Admin")
        bot.send_message(uid,
            f"✅ *{ju.get('name','Foydalanuvchi')}* guruhga qo'shildi!\n"
            f"👥 *{g['name']}*",
            parse_mode="Markdown", reply_markup=ok_kb()
        )
        # Qo'shiluvchiga: so'rov qabul qilindi xabari + tasdiqlash tugmasi
        try:
            kb_confirm = InlineKeyboardMarkup()
            kb_confirm.add(cBtn("✅ Tushunarli!", f"group_join_ack_{g_id}", "success"))
            bot.send_message(joiner_id,
                f"🎉 *{g['name']}* guruhiga qo'shilish so'rovingiz qabul qilindi!\n\n"
                f"📌 Odat: *{g.get('habit_name','—')}*\n"
                f"⏰ Vaqt: *{g.get('habit_time','vaqtsiz')}*",
                parse_mode="Markdown",
                reply_markup=kb_confirm
            )
        except Exception as _e: print(f"[warn] xato: {_e}")
        return True

    if cdata.startswith("group_join_ack_"):
        # Foydalanuvchi "Tushunarli!" ni bosdi — xabar 5s dan keyin o'chadi
        bot.answer_callback_query(call.id, "✅ Tabriklaymiz!")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return True

    if cdata.startswith("group_reject_"):
        # group_reject_{g_id}_{joiner_uid}
        rest      = cdata[len("group_reject_"):]
        parts     = rest.rsplit("_", 1)
        g_id      = parts[0]
        joiner_id = int(parts[1])
        bot.answer_callback_query(call.id, "❌ Rad etildi")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        # Qo'shiluvchiga: rad xabari
        try:
            bot.send_message(joiner_id,
                f"❌ *{g['name'] if g else 'Guruh'}* guruhiga qo'shilish so'rovingiz rad etildi.",
                parse_mode="Markdown", reply_markup=ok_kb()
            )
        except Exception as _e: print(f"[warn] send_message: {_e}")
        return True

    if cdata.startswith("group_invite_"):
        g_id = cdata[len("group_invite_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            return True
        inv_link = f"https://t.me/{get_bot_username()}?start=grp_{g_id}"
        sent = bot.send_message(uid,
            f"🔗 *{g['name']} — Invite link:*\n\n`{inv_link}`\n\n"
            f"_Ushbu linkni do'stlaringizga yuboring!_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("group_leave_"):
        g_id = cdata[len("group_leave_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if g:
            members = g.get("members", [])
            uid_str = str(uid)
            members = [m for m in members if str(m) != uid_str]
            g["members"] = members
            save_group(g_id, g)
            u["groups"] = [x for x in u.get("groups", []) if x.get("id") != g_id]
            save_user(uid, u)
            try:
                admin_id = g.get("admin_id")
                if admin_id and str(admin_id) != uid_str:
                    admin_u = load_user(admin_id)
                    bot.send_message(int(admin_id),
                        f"ℹ️ *{u.get('name','Foydalanuvchi')}* guruhdan chiqdi.",
                        parse_mode="Markdown", reply_markup=ok_kb()
                    )
            except Exception as _e: print(f"[warn] send_message: {_e}")
        send_menu2(uid)
        return True

    return False

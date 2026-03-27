#!/usr/bin/env python3
"""
Menyu navigatsiya, hisobot ro'yxati, onboarding callback handlerlari
"""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user, save_user
from helpers import T, get_lang, today_uz5
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, cBtn, ok_kb, kb_to_dict)
from menus import send_menu2
from handlers_stats import show_stats, delete_habit_menu
from handlers_rating import show_rating


def handle_menu_callbacks(call, uid, cdata, u):
    """Menyu va navigatsiya callback larini qayta ishlaydi. True = handled."""

    if cdata.startswith("weekly_confirm_"):
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        return True

    if cdata == "weekly_reports_list":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        reports = u.get("weekly_reports", [])
        if not reports:
            sent_e = bot.send_message(
                uid,
                "📅 *Haftalik hisobotlar*\n\nHali hisobot yo'q.\nHar dushanba avtomatik yuboriladi!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return True
        # Ro'yxat — oxiridan boshiga (eng yangi avval)
        kb_wr = InlineKeyboardMarkup()
        for i, rep in enumerate(reversed(reports)):
            label = rep.get("week_label", f"{i+1}-hafta")
            pct   = rep.get("done_pct", 0)
            if pct >= 80:   emoji = "🏆"
            elif pct >= 60: emoji = "✅"
            elif pct >= 40: emoji = "💪"
            else:           emoji = "⚠️"
            kb_wr.add(InlineKeyboardButton(
                f"{emoji} {label} — {pct}%",
                callback_data=f"weekly_view_{len(reports)-1-i}"
            ))
        kb_wr.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent_wr = bot.send_message(
            uid,
            "📅 *Haftalik hisobotlar arxivi*\n\nQaysi haftani ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=kb_wr
        )
        u["main_msg_id"] = sent_wr.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("weekly_view_"):
        idx_r = int(cdata[len("weekly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        reports = u.get("weekly_reports", [])
        if idx_r < 0 or idx_r >= len(reports):
            send_main_menu(uid)
            return True
        report = reports[idx_r]
        text   = build_weekly_report_text(uid, report)
        kb_back = InlineKeyboardMarkup()
        kb_back.row(
            cBtn("⬅️ Orqaga", "weekly_reports_list", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent_v = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent_v.message_id
        save_user(uid, u)
        return True


    if cdata == "monthly_reports_list":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("monthly_reports", [])
        if not reports:
            sent_e = bot.send_message(
                uid,
                "📆 *Oylik hisobotlar*\n\nHali hisobot yo'q.\nHar oyning 1-kuni avtomatik yuboriladi!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return True
        kb_mr = InlineKeyboardMarkup()
        for i, rep in enumerate(reversed(reports)):
            label = rep.get("month_label", f"{i+1}-oy")
            pct   = rep.get("done_pct", 0)
            if pct >= 80:   emoji = "🏆"
            elif pct >= 60: emoji = "✅"
            elif pct >= 40: emoji = "💪"
            else:           emoji = "⚠️"
            kb_mr.add(InlineKeyboardButton(
                f"{emoji} {label} — {pct}%",
                callback_data=f"monthly_view_{len(reports)-1-i}"
            ))
        kb_mr.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent_mr = bot.send_message(
            uid,
            "📆 *Oylik hisobotlar arxivi*\n\nQaysi oyni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=kb_mr
        )
        u["main_msg_id"] = sent_mr.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("monthly_view_"):
        idx_m = int(cdata[len("monthly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("monthly_reports", [])
        if idx_m < 0 or idx_m >= len(reports):
            send_main_menu(uid)
            return True
        report = reports[idx_m]
        text   = build_monthly_report_text(uid, report)
        kb_back = InlineKeyboardMarkup()
        kb_back.row(
            cBtn("⬅️ Orqaga", "monthly_reports_list", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent_v = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent_v.message_id
        save_user(uid, u)
        return True

    if cdata == "yearly_reports_list":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("yearly_reports", [])
        if not reports:
            sent_e = bot.send_message(
                uid,
                "🗓 *Yillik hisobotlar*\n\nHali hisobot yo'q.\nHar yilning 1-yanvarida avtomatik yuboriladi!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup().add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
            )
            u["main_msg_id"] = sent_e.message_id
            save_user(uid, u)
            return True
        kb_yr = InlineKeyboardMarkup()
        for i, rep in enumerate(reversed(reports)):
            label = rep.get("year_label", f"{i+1}-yil")
            pct   = rep.get("done_pct", 0)
            if pct >= 80:   emoji = "🏆"
            elif pct >= 60: emoji = "✅"
            elif pct >= 40: emoji = "💪"
            else:           emoji = "⚠️"
            kb_yr.add(InlineKeyboardButton(
                f"{emoji} {label} — {pct}%",
                callback_data=f"yearly_view_{len(reports)-1-i}"
            ))
        kb_yr.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent_yr = bot.send_message(
            uid,
            "🗓 *Yillik hisobotlar arxivi*\n\nQaysi yilni ko'rmoqchisiz?",
            parse_mode="Markdown",
            reply_markup=kb_yr
        )
        u["main_msg_id"] = sent_yr.message_id
        save_user(uid, u)
        return True

    if cdata.startswith("yearly_view_"):
        idx_y = int(cdata[len("yearly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("yearly_reports", [])
        if idx_y < 0 or idx_y >= len(reports):
            send_main_menu(uid)
            return True
        report = reports[idx_y]
        text   = build_yearly_report_text(uid, report)
        kb_back = InlineKeyboardMarkup()
        kb_back.row(
            cBtn("⬅️ Orqaga", "yearly_reports_list", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent_v = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent_v.message_id
        save_user(uid, u)
        return True



    if cdata == "menu_list":

        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # show_habits = statistika bilan bir xil, send_main_menu ishlatamiz
        u2 = load_user(uid)
        habits = u2.get("habits", [])
        if not habits:
            sent_e = bot.send_message(uid, T(uid, "no_habits"), parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup().add(
                                          cBtn(T(uid, "btn_home"), "menu_main", "primary")))
            u2["main_msg_id"] = sent_e.message_id
            save_user(uid, u2)
            return True
        # Barcha odatlarni ro'yxat sifatida ko'rsatish
        today = today_uz5()
        text  = "📋 *Odatlarim ro'yxati*" + "\n" + "▬" * 16 + "\n\n"
        def _sk(h):
            t = h.get("time", "23:59")
            try: hh, mm = t.split(":"); return int(hh)*60+int(mm)
            except: return 9999
        for h in sorted(habits, key=_sk):
            hab_type  = h.get("type", "simple")
            rep_count = h.get("repeat_count", 1)
            streak    = h.get("streak", 0)
            if hab_type == "repeat":
                done_c  = h.get("done_today_count", 0)
                status  = "☑️" if done_c >= rep_count else f"🔄 {done_c}/{rep_count}"
                times_s = ", ".join(h.get("repeat_times", [h.get("time", "—")]))
                text += f"{status} *{h['name']}*\n   🔁 {times_s} | 🔥 {streak} kun\n\n"
            else:
                is_done = h.get("last_done") == today
                status  = "☑️" if is_done else "⬜"
                time_s  = h.get("time", "vaqtsiz")
                text += f"{status} *{h['name']}*\n   ⏰ {time_s} | 🔥 {streak} kun\n\n"
        kb_list = InlineKeyboardMarkup()
        kb_list.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_list)
        u2["main_msg_id"] = sent.message_id
        save_user(uid, u2)
        return True

    if cdata == "menu_stats":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_stats(uid)
        return True

    if cdata.startswith("stats_page_"):
        page = int(cdata[11:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_stats(uid, page=page)
        return True

    if cdata == "menu_delete":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        delete_habit_menu(uid)
        return True

    if cdata == "menu_rating":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_rating(uid)
        return True

    if cdata == "menu_main":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        send_main_menu(uid)
        return True

    # ============================================================
    #  2-MENYU (GURUHLAR)
    # ============================================================
    if cdata == "menu2_open":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        send_menu2(uid)
        return True

    if cdata == "dismiss_ball_notif":
        bot.answer_callback_query(call.id, "✅")
        # Foydalanuvchi ma'lumotini olish
        u2 = load_user(uid)
        user_name = u2.get("name", "Noma'lum")
        # Adminga xabar yuborish - admin tasdiqlasin
        try:
            kb_admin_confirm = InlineKeyboardMarkup()
            kb_admin_confirm.add(InlineKeyboardButton(
                "✅ Tasdiqlash", callback_data=f"admin_confirm_ball_{uid}"
            ))
            bot.send_message(
                ADMIN_ID,
                f"✅ *{user_name}* (ID: `{uid}`) ballni olganini tasdiqladi!",
                parse_mode="Markdown",
                reply_markup=kb_admin_confirm
            )
        except Exception:
            pass
        # Foydalanuvchidagi xabarni darhol o'chirish
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return True

    if cdata.startswith("admin_confirm_ball_") and uid == ADMIN_ID:
        bot.answer_callback_query(call.id, "✅")
        def del_admin_ball_msg(msg_id):
            time.sleep(5)
            try: bot.delete_message(ADMIN_ID, msg_id)
            except: pass
        threading.Thread(target=del_admin_ball_msg, args=(call.message.message_id,), daemon=True).start()
        return True

    if cdata == "noop":
        bot.answer_callback_query(call.id)
        return True

    if cdata == "ack_delete_msg":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return True

    # ── Vaqtsiz odat qo'shish ──

    return False

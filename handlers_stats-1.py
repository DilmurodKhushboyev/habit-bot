#!/usr/bin/env python3
"""
Statistika va hisobotlar (haftalik, oylik, yillik)
"""

import time
import random
from datetime import datetime, date, timedelta, timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import mongo_col
from database import load_user, save_user, load_all_users
from helpers import T, get_lang, get_rank, today_uz5
from texts import LANGS
from motivation import MOTIVATSIYA
from bot_setup import (bot, send_main_menu, send_message_colored,
                       main_menu_dict, main_menu, cBtn, ok_kb)


def show_stats(uid, page=1):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        send_main_menu(uid, T(uid, "no_stats"))
        return
    total_points = u.get("points", 0)
    per_page     = 5
    total_pages  = (len(habits) + per_page - 1) // per_page
    page         = max(1, min(page, total_pages))
    page_habits  = habits[(page - 1) * per_page : page * per_page]

    text  = T(uid, "stats_title", page=page, total=total_pages) + "\n"
    text += "▬" * 16 + "\n"
    text += T(uid, "stats_ball", ball=total_points) + "\n"
    text += T(uid, "stats_rank", rank=get_rank(uid, total_points)) + "\n"
    text += "▬" * 16 + "\n\n"

    for h in page_habits:
        streak  = h.get("streak", 0)
        total   = h.get("total_done", 0)
        started = h.get("started_at", "—")
        if streak >= 30:   medal = "🥇"
        elif streak >= 14: medal = "🥈"
        elif streak >= 7:  medal = "🥉"
        else:              medal = "🌱"
        text += f"{medal} *{h['name']}*\n"
        text += "   " + T(uid, "stats_time",   time=h.get("time","—")) + "\n"
        text += "   " + T(uid, "stats_streak", streak=streak) + "\n"
        text += "   " + T(uid, "stats_done",   n=total) + "\n"
        text += "   " + T(uid, "stats_missed", n=h.get("total_missed",0)) + "\n"
        text += f"   *📅 Boshlangan:* {started}\n\n"

    kb_stats = InlineKeyboardMarkup()
    nav_row  = []
    if page > 1:
        nav_row.append(cBtn(T(uid, "nav_prev", n=page-1), f"stats_page_{page-1}", "primary"))
    if page < total_pages:
        nav_row.append(cBtn(T(uid, "nav_next", n=page+1), f"stats_page_{page+1}", "primary"))
    if nav_row:
        kb_stats.row(*nav_row)
    kb_stats.add(InlineKeyboardButton("📅 Haftalik hisobotlar", callback_data="weekly_reports_list"))
    kb_stats.add(InlineKeyboardButton("📆 Oylik hisobotlar",    callback_data="monthly_reports_list"))
    kb_stats.add(InlineKeyboardButton("🗓 Yillik hisobotlar",   callback_data="yearly_reports_list"))
    kb_stats.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_stats)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)


def build_weekly_report_text(uid, report):
    week_label   = report.get("week_label", "—")
    done_pct     = report.get("done_pct", 0)
    jon_start    = report.get("jon_start", 100)
    jon_end      = report.get("jon_end", 100)
    jon_change   = round(jon_end - jon_start, 1)
    jon_sign     = "+" if jon_change >= 0 else ""
    best_streak  = report.get("best_streak", 0)
    balls_earned = report.get("balls_earned", 0)
    best_habit   = report.get("best_habit", "—")
    worst_habit  = report.get("worst_habit", "—")

    if done_pct >= 80:   grade = "🏆 Ajoyib hafta!"
    elif done_pct >= 60: grade = "✅ Yaxshi hafta"
    elif done_pct >= 40: grade = "💪 O'rtacha hafta"
    else:                grade = "⚠️ Qiyin hafta"

    if jon_end >= 80:   je = "❤️"
    elif jon_end >= 50: je = "🧡"
    elif jon_end >= 20: je = "💛"
    else:               je = "🖤"

    text  = f"📅 *{week_label}*\n"
    text += "▬" * 16 + "\n\n"
    text += f"{grade}\n\n"
    text += f"*🎯 Bajarildi:* {done_pct}%\n"
    text += f"*{je} Jon:* {jon_start}% → {jon_end}% ({jon_sign}{jon_change}%)\n"
    text += f"*🔥 Eng uzun streak:* {best_streak} kun\n"
    best_day = report.get("best_day", "—")
    text += f"*⭐ Yig'ilgan ball:* +{balls_earned}\n"
    text += f"*📆 Eng faol kun:* {best_day}\n\n"
    text += "▬" * 16 + "\n"
    text += f"*🏆 Eng yaxshi odat:* {best_habit}\n"
    text += f"*⚠️ Eng kam bajarilgan:* {worst_habit}\n"
    return text

def send_weekly_reports():
    from datetime import timezone, timedelta
    tz_uz    = timezone(timedelta(hours=5))
    now      = datetime.now(tz_uz)
    today    = now.date()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday + 7)
    week_end   = week_start + timedelta(days=6)
    week_label = f"{week_start.strftime('%d.%m')} – {week_end.strftime('%d.%m.%Y')}"
    users = load_all_users(force=True)
    print(f"[weekly_report] {len(users)} foydalanuvchiga hisobot yuborilmoqda...")
    for uid_str, udata in users.items():
        try:
            habits = udata.get("habits", [])
            if not habits:
                continue
            uid_int  = int(uid_str)
            jon_end  = round(udata.get("jon", 100))
            # O'tgan hafta boshlanish jonini history dan topamiz
            _h_hist = udata.get("history", {})
            _w_jon_vals = []
            for _wi in range(7, 0, -1):
                _wd = (now - timedelta(days=_wi)).strftime("%Y-%m-%d")
                _wd_data = _h_hist.get(_wd, {})
                if "jon" in _wd_data:
                    _w_jon_vals.append(_wd_data["jon"])
            jon_start = round(_w_jon_vals[0]) if _w_jon_vals else max(0, min(100, round(jon_end - (jon_end - 50) * 0.1)))
            # O'tgan 7 kunni history dan hisoblash
            total_possible = 0
            total_done_w   = 0
            habit_scores   = []
            best_streak    = 0
            best_day_count = 0
            best_day_label = "—"
            _day_names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
            for h in habits:
                rep  = h.get("repeat_count", 1) if h.get("type") == "repeat" else 1
                done_w = 0
                for _wi in range(6, -1, -1):
                    _wd = (now - timedelta(days=_wi)).strftime("%Y-%m-%d")
                    if _h_hist.get(_wd, {}).get("habits", {}).get(h["id"]):
                        done_w += 1
                poss = rep * 7
                total_possible += poss
                total_done_w   += done_w
                score = round(done_w / poss * 100) if poss else 0
                habit_scores.append((h["name"], score))
                if h.get("streak", 0) > best_streak:
                    best_streak = h.get("streak", 0)
            # Eng faol kun — o'tgan 7 kundagi eng ko'p odat bajarilgan kun
            for _wi in range(6, -1, -1):
                _wd = (now - timedelta(days=_wi)).strftime("%Y-%m-%d")
                _d_done = _h_hist.get(_wd, {}).get("done", 0)
                if _d_done > best_day_count:
                    best_day_count = _d_done
                    _wd_obj = now - timedelta(days=_wi)
                    best_day_label = f"{_day_names[_wd_obj.weekday()]} ({_wd_obj.strftime('%d.%m')})"
            done_pct     = round(total_done_w / total_possible * 100) if total_possible else 0
            balls_earned = total_done_w * 5
            habit_scores.sort(key=lambda x: x[1], reverse=True)
            best_habit  = habit_scores[0][0]  if habit_scores else "—"
            worst_habit = habit_scores[-1][0] if habit_scores else "—"
            report = {
                "week_label":   week_label,
                "week_start":   str(week_start),
                "done_pct":     done_pct,
                "jon_start":    jon_start,
                "jon_end":      jon_end,
                "best_streak":  best_streak,
                "balls_earned": balls_earned,
                "best_habit":   best_habit,
                "worst_habit":  worst_habit,
                "best_day":     best_day_label,
            }
            try:
                # BUG FIX: _id har doim string saqlanadi, uid_int emas uid_str ishlatish kerak
                mongo_col.update_one(
                    {"_id": uid_str},
                    {"$push": {"weekly_reports": report}},
                    upsert=False
                )
            except Exception as e:
                print(f"[weekly_report] MongoDB saqlash xato {uid_str}: {e}")
            text = "📊 *Haftalik hisobotingiz tayyor!*\n\n"
            text += build_weekly_report_text(uid_int, report)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"weekly_confirm_{uid_str}"))
            bot.send_message(uid_int, text, parse_mode="Markdown", reply_markup=kb)
            time.sleep(0.05)
        except Exception as e:
            print(f"[weekly_report] Xato {uid_str}: {e}")
    print("[weekly_report] Yuborildi.")


def delete_habit_menu(uid):
    u      = load_user(uid)
    habits = u.get("habits", [])
    if not habits:
        _s = send_message_colored(uid, T(uid, "no_delete"), main_menu_dict(uid))
        if _s is None:
            bot.send_message(uid, T(uid, "no_delete"), reply_markup=main_menu(uid))
        return
    # Vaqt bo'yicha tartiblash
    def _sort_key(h):
        t = h.get("time", "23:59")
        try:
            hh, mm = t.split(":")
            return int(hh) * 60 + int(mm)
        except:
            return 9999
    sorted_habits = sorted(habits, key=_sort_key)
    kb = InlineKeyboardMarkup()
    for h in sorted_habits:
        kb.add(InlineKeyboardButton(f"🗑 {h['name']} ({h['time']})", callback_data=f"delete_{h['id']}"))
    kb.row(
        cBtn(T(uid, "btn_home"), "menu_main", "primary")
    )
    sent = bot.send_message(uid, T(uid, "del_which_habit"), parse_mode="Markdown", reply_markup=kb)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)


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


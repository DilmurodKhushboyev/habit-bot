#!/usr/bin/env python3
"""
Matn handleri, to'lov, broadcast, inline query
"""

import os
import io
import json
import time
import random
import threading
import schedule
from datetime import date, datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineQueryResultCachedPhoto, SwitchInlineQueryChosenChat
)

from config import ADMIN_ID, BOT_TOKEN
from database import (load_user, save_user, load_all_users, count_users,
                      load_group, save_group, user_exists,
                      load_settings, save_settings)
from helpers import T, get_lang, today_uz5
from texts import LANGS
from motivation import MOTIVATSIYA
from bot_setup import (bot, send_main_menu, main_menu, main_menu_dict,
                       send_message_colored, cBtn, ok_kb, kb_to_dict,
                       get_bot_username, _share_file_ids)
from menus import (check_subscription, send_sub_required, send_menu2,
                   admin_menu)

from groups import _save_new_habit, _save_new_group, _save_group_habit
from scheduler import schedule_habit

@bot.message_handler(func=lambda m: not (m.text and m.text.startswith("/")), content_types=["text", "photo", "document", "video", "audio", "voice", "sticker", "animation"])
def handle_text(msg):
    import re
    uid   = msg.from_user.id
    text  = msg.text or msg.caption or ""
    u     = load_user(uid)
    state = u.get("state")

    # ── Majburiy obuna tekshiruvi (ro'yxatdan o'tgan foydalanuvchilar uchun) ──
    if u.get("phone") and not (state and state.startswith("admin_")):
        if not check_subscription(uid):
            try:
                bot.delete_message(uid, msg.message_id)
            except Exception:
                pass
            send_sub_required(uid)
            return

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
        cancel_kb.add(InlineKeyboardButton(T(uid, "btn_no_time"), callback_data="habit_no_time"))
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        if hab_type == "repeat":
            rep_count = u["temp_habit"].get("repeat_count", 1)
            prompt = T(uid, "ask_repeat_first_time", name=habit_name, count=rep_count)
        else:
            prompt = T(uid, "ask_habit_time", name=habit_name)
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
                    T(uid, "ask_repeat_next_time", current=len(collected)+1, total=rep_count),
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
                    T(uid, "ask_repeat_next_time", current=len(collected)+1, total=rep_count),
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
        # Eski so'rov xabarini o'chirish
        gp_msg_id = u.pop("give_points_msg_id", None)
        if gp_msg_id:
            try: bot.delete_message(uid, gp_msg_id)
            except: pass
        try:
            target_id = int(text.strip())
        except ValueError:
            bot.send_message(uid, T(uid, "err_only_digits"))
            return
        try:
            if not user_exists(target_id):
                bot.send_message(uid, T(uid, "err_user_not_found"))
                return
        except Exception as e:
            print(f"[admin_give_points] user_exists xato: {e}")
            bot.send_message(uid, f"⚠️ Xatolik: {e}")
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
        # Eski so'rov xabarini o'chirish
        gp_msg_id = u.pop("give_points_msg_id", None)
        if gp_msg_id:
            try: bot.delete_message(uid, gp_msg_id)
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
        # Eski so'rov xabarini o'chirish
        ch_msg_id = u.pop("channel_msg_id", None)
        if ch_msg_id:
            try: bot.delete_message(uid, ch_msg_id)
            except: pass
        slot = int(state.split("_")[-1])
        channel = text.strip()
        # URL formatlarini tozalash: https://t.me/kanal → @kanal
        if "t.me/" in channel:
            channel = channel.split("t.me/")[-1].strip("/")
        # @ belgisini qo'shish
        channel = channel.lstrip("@")
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
        sent_ok = bot.send_message(uid, f"✅ {slot}-kanal {channel} sifatida o'rnatildi!")
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

    # ── Broadcast matn/media (admin) ──
    if state in ("admin_bc_private", "admin_bc_groups", "admin_bc_all") and uid == ADMIN_ID:
        # Eski so'rov xabarini o'chirish
        bc_trigger_id = u.pop("bc_trigger_msg_id", None)
        if bc_trigger_id:
            try: bot.delete_message(uid, bc_trigger_id)
            except: pass
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
            # Noma'lum Stars mahsulot — xato holati (bo'lmasligi kerak)
            print(f"[stars] Noma'lum item_id: {item_id}, uid={uid}")
            return
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



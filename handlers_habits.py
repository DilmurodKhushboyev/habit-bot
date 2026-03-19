"""
handlers_habits.py
==================
Onboarding, reyting rasm generatsiyasi, statistika, haftalik hisobot,
odat o'chirish menyusi va asosiy callback handler.
Bu faylda: send_onboarding, generate_rating_image, show_stats, callback_handler va boshqalar.
Bog'liq fayllar: config.py, database.py, languages.py, keyboards.py
"""

import telebot
import os
import requests
import json
import io
import random
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineQueryResultCachedPhoto, SwitchInlineQueryChosenChat
)
from config import BOT_TOKEN, ADMIN_ID, mongo_col, groups_col
from database import load_user, save_user, load_settings, save_settings, load_group, save_group, load_all_users, count_users, invalidate_users_cache
from languages import T, get_lang, LANGS, get_rank, MOTIVATSIYA, today_uz5
from keyboards import (bot, main_menu, main_menu_dict, send_message_colored,
                       edit_message_colored, cBtn, ok_kb, kb_to_dict,
                       send_main_menu, build_main_text, done_keyboard,
                       menu2_dict, build_menu2_text, send_menu2,
                       check_subscription, send_sub_required,
                       admin_menu, admin_broadcast_menu, admin_stats_period_menu)

# ============================================================
#  ACHIEVEMENTS (muvaffaqiyatlar tizimi)
# ============================================================

_ACHIEVEMENTS = [
    {"id":"streak_3",   "cat":"streak",  "icon":"🔥", "title":"Ilk olov",        "req":3,    "field":"streak"},
    {"id":"streak_7",   "cat":"streak",  "icon":"🌟", "title":"Haftalik qahramon","req":7,    "field":"streak"},
    {"id":"streak_30",  "cat":"streak",  "icon":"💎", "title":"Oylik ustoz",      "req":30,   "field":"streak"},
    {"id":"streak_100", "cat":"streak",  "icon":"👑", "title":"100 kun shohi",    "req":100,  "field":"streak"},
    {"id":"pts_100",    "cat":"ball",    "icon":"⭐", "title":"Birinchi yulduz",  "req":100,  "field":"points"},
    {"id":"pts_500",    "cat":"ball",    "icon":"🌠", "title":"Yulduz yomg'iri",  "req":500,  "field":"points"},
    {"id":"pts_1000",   "cat":"ball",    "icon":"🏆", "title":"Ming ball",        "req":1000, "field":"points"},
    {"id":"pts_5000",   "cat":"ball",    "icon":"💰", "title":"Ball millioneri",  "req":5000, "field":"points"},
    {"id":"hab_1",      "cat":"odat",    "icon":"🌱", "title":"Birinchi qadam",   "req":1,    "field":"habits_count"},
    {"id":"hab_5",      "cat":"odat",    "icon":"🌿", "title":"To'plam",          "req":5,    "field":"habits_count"},
    {"id":"hab_10",     "cat":"odat",    "icon":"🌳", "title":"Bog'bon",          "req":10,   "field":"habits_count"},
    {"id":"done_10",    "cat":"faollik", "icon":"✅", "title":"O'n marta",        "req":10,   "field":"total_done"},
    {"id":"done_50",    "cat":"faollik", "icon":"🎯", "title":"Ellik marta",      "req":50,   "field":"total_done"},
    {"id":"done_100",   "cat":"faollik", "icon":"🚀", "title":"Yuz marta",        "req":100,  "field":"total_done"},
    {"id":"done_500",   "cat":"faollik", "icon":"⚡", "title":"Besh yuz",         "req":500,  "field":"total_done"},
    {"id":"friend_1",   "cat":"ijtimoiy","icon":"🤝", "title":"Birinchi do'st",   "req":1,    "field":"friends_count"},
    {"id":"friend_5",   "cat":"ijtimoiy","icon":"👥", "title":"Jamoatchi",        "req":5,    "field":"friends_count"},
]

def check_achievements_toplevel(uid, u):
    """Bot callback'dan chaqirish uchun top-level achievements tekshiruvi."""
    earned_ids = {a["id"] for a in u.get("achievements", []) if isinstance(a, dict)}
    field_vals = {
        "streak":        u.get("streak", 0),
        "points":        u.get("points", 0),
        "habits_count":  len(u.get("habits", [])),
        "total_done":    sum(h.get("total_done", 0) for h in u.get("habits", [])),
        "friends_count": len(u.get("friends", [])),
    }
    new_ach = []
    ach_list = list(u.get("achievements", []))
    changed = False
    for ach in _ACHIEVEMENTS:
        if ach["id"] in earned_ids:
            continue
        if field_vals.get(ach["field"], 0) >= ach["req"]:
            ach_list.append({"id": ach["id"], "earned_at": today_uz5()})
            new_ach.append(ach)
            changed = True
    if changed:
        u["achievements"] = ach_list
        save_user(uid, u)
    return new_ach

# ============================================================
#  ONBOARDING
# ============================================================
def send_onboarding(uid, name):
    """Yangi foydalanuvchi uchun jonli salomlashuv va birinchi odat yaratish"""
    u = load_user(uid)
    # 1-qadam: Salomlashuv
    text1 = (
        f"🎉 *Xush kelibsiz, {name}!*\n\n"
        f"Men sizga har kuni odatlaringizni bajarishda yordam beraman.\n\n"
        f"*Streak* — ketma-ket bajargan kunlaringiz.\n"
        f"*Ball* — har bajargan odatingiz +5 ball.\n"
        f"*Guruh* — do'stlar bilan birga, odatlar! 😄\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Birinchi odatingizni *birga* qo'shaylikmi? 👇"
    )
    kb1 = InlineKeyboardMarkup()
    kb1.row(
        InlineKeyboardButton("✅ Ha, boshlaylik!", callback_data="onboard_start"),
        InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip")
    )
    sent = bot.send_message(uid, text1, parse_mode="Markdown", reply_markup=kb1)
    u["main_msg_id"] = sent.message_id
    u["onboarding"] = True
    save_user(uid, u)

def send_onboarding_habit_category(uid):
    """Onboarding: odat kategoriyasini tanlash"""
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    text = (
        "🌱 *Qaysi sohadan boshlaysiz?*\n\n"
        "Eng ko'p foyda keltiradigan odatni tanlang:"
    )
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("💪 Sport / Sog'liq", callback_data="onboard_cat_sport"),
        InlineKeyboardButton("📚 O'qish / Bilim",  callback_data="onboard_cat_book")
    )
    kb.row(
        InlineKeyboardButton("🧘 Ruhiy salomatlik", callback_data="onboard_cat_mind"),
        InlineKeyboardButton("💼 Ish / Maqsad",     callback_data="onboard_cat_work")
    )
    kb.row(
        InlineKeyboardButton("✏️ O'zim yozaman",    callback_data="onboard_cat_custom")
    )
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u = load_user(uid)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# Kategoriyaga tayyor misollar
ONBOARD_EXAMPLES = {
    "sport": [
        ("🏃 Ertalab yugurish — 20 daqiqa", "Ertalab yugurish — 20 daqiqa"),
        ("💪 Sport zali — 30 daqiqa",        "Sport zali — 30 daqiqa"),
        ("🚶 10,000 qadam",                  "10,000 qadam"),
    ],
    "book": [
        ("📖 Kitob o'qish — 20 bet",   "Kitob o'qish — 20 bet"),
        ("🎧 Audio kitob — 30 daqiqa", "Audio kitob — 30 daqiqa"),
        ("📝 Kundalik yozish",         "Kundalik yozish"),
    ],
    "mind": [
        ("🧘 Meditatsiya — 10 daqiqa", "Meditatsiya — 10 daqiqa"),
        ("🙏 Namoz",                   "Namoz"),
        ("😴 Erta uxlash",             "Erta uxlash"),
    ],
    "work": [
        ("🎯 Eng muhim vazifa — 1 ta", "Eng muhim vazifa — 1 ta"),
        ("💻 Dasturlash — 1 soat",     "Dasturlash — 1 soat"),
        ("📋 Reja tuzish",             "Reja tuzish"),
    ],
}

def send_onboarding_examples(uid, cat):
    """Onboarding: tanlangan kategoriya misollari"""
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    examples = ONBOARD_EXAMPLES.get(cat, [])
    text = "✨ *Mashhur odatlardan birini tanlang yoki o'zingiz yozing:*"
    kb = InlineKeyboardMarkup()
    for label, habit_name in examples:
        kb.add(InlineKeyboardButton(label, callback_data=f"onboard_habit_{habit_name}"))
    kb.add(InlineKeyboardButton("✏️ O'zim yozaman", callback_data="onboard_cat_custom"))
    kb.add(InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip"))
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u = load_user(uid)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

def send_onboarding_time(uid, habit_name):
    """Onboarding: vaqt tanlash"""
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    u = load_user(uid)
    u["temp_onboard_habit"] = habit_name
    save_user(uid, u)
    text = (
        f"⏰ *\"{habit_name}\" uchun eslatma vaqtini tanlang:*\n\n"
        f"Qachon eslatma olishni xohlaysiz?"
    )
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🌅 06:00 — Erta tong",  callback_data="onboard_time_06:00"),
        InlineKeyboardButton("☀️ 08:00 — Ertalab",    callback_data="onboard_time_08:00"),
    )
    kb.row(
        InlineKeyboardButton("🌞 12:00 — Tushlik",    callback_data="onboard_time_12:00"),
        InlineKeyboardButton("🌆 18:00 — Kechqurun",  callback_data="onboard_time_18:00"),
    )
    kb.row(
        InlineKeyboardButton("🌙 21:00 — Kech",       callback_data="onboard_time_21:00"),
        InlineKeyboardButton("🌃 23:00 — Kech kech",  callback_data="onboard_time_23:00"),
    )
    kb.row(
        InlineKeyboardButton("✏️ O'zim kiriting",      callback_data="onboard_time_custom"),
    )
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

def finish_onboarding(uid, habit_name, habit_time):
    """Onboarding: odat saqlash va yakunlash"""
    import uuid
    try: bot.delete_message(uid, load_user(uid).get("main_msg_id"))
    except: pass
    u = load_user(uid)
    # Odat yaratamiz
    new_habit = {
        "id":         str(uuid.uuid4())[:8],
        "name":       habit_name,
        "time":       habit_time,
        "type":       "simple",
        "streak":     0,
        "total_done": 0,
        "last_done":  None,
        "created_at": today_uz5(),
    }
    habits = u.get("habits", [])
    habits.append(new_habit)
    u["habits"]     = habits
    u["onboarding"] = False
    u.pop("temp_onboard_habit", None)
    save_user(uid, u)
    # Eslatma o'rnatish
    try:
        schedule_habit(uid, new_habit)
    except Exception as _e: print(f"[warn] schedule_habit: {_e}")
    # Tabrik
    text = (
        f"🎊 *Zo'r! Birinchi odatingiz qo'shildi!*\n\n"
        f"📌 *{habit_name}*\n"
        f"⏰ Eslatma: *{habit_time}*\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Bugun bajarsangiz — *streak boshlanadi* 🔥\n"
        f"7 kun ketma-ket → 🥉 medal\n"
        f"14 kun → 🥈 medal\n"
        f"30 kun → 🥇 medal\n\n"
        f"*Muvaffaqiyatlar!* 💪"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 Asosiy menyuga", callback_data="menu_main"))
    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    u = load_user(uid)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)

# ============================================================
#  REYITING
# ============================================================

# ============================================================
#  REYTING RASM GENERATSIYASI
# ============================================================
def generate_rating_image(top10_data):
    """
    top10_data: list of (name, points, jon_val, is_vip, user_id)
    Returns: BytesIO rasm — Top 10 + 7 kunlik done_log grid
    """
    from datetime import timezone, timedelta
    FONT   = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    DAYS    = 7
    W       = 1080
    ROW_H   = 98
    HDR_H   = 175
    FTR_H   = 60
    H       = HDR_H + ROW_H * 10 + FTR_H + 8

    img  = Image.new("RGB", (W, H), (10, 10, 18))
    draw = ImageDraw.Draw(img)

    try:
        f_title = ImageFont.truetype(FONT,   48)
        f_sub   = ImageFont.truetype(FONT_R, 20)
        f_rank  = ImageFont.truetype(FONT,   26)
        f_name  = ImageFont.truetype(FONT,   28)
        f_small = ImageFont.truetype(FONT_R, 19)
        f_pts   = ImageFont.truetype(FONT,   26)
        f_day   = ImageFont.truetype(FONT_R, 16)
        f_label = ImageFont.truetype(FONT_R, 16)
    except Exception:
        f_title = f_sub = f_rank = f_name = f_small = f_pts = f_day = f_label = ImageFont.load_default()

    # ── HEADER ──
    for y in range(HDR_H):
        t = y / HDR_H
        draw.line([(0,y),(W,y)], fill=(int(12+t*8), int(12+t*8), int(28+t*22)))
    draw.rectangle([(0, HDR_H-3),(W, HDR_H)], fill=(200,160,0))
    draw.text((W//2, 68),  "REYTING  TOP-10",              font=f_title, fill=(255,215,0),   anchor="mm")
    tw = int(f_title.getlength("REYTING  TOP-10"))
    draw.rectangle([(W//2-tw//2, 92),(W//2+tw//2, 95)], fill=(180,140,0))
    draw.text((W//2, 128), "Super Habits Bot  •  @Super_habits_bot", font=f_sub, fill=(120,120,165), anchor="mm")

    # Ustun sarlavhalari
    draw.text((90,  153), "O'RIN / ISM", font=f_label, fill=(70,70,105), anchor="lm")
    draw.text((560, 153), "7 KUN",       font=f_label, fill=(70,70,105), anchor="lm")
    draw.text((930, 153), "BALL",        font=f_label, fill=(70,70,105), anchor="rm")

    # 7 kunlik sana sarlavhalari
    tz_uz = timezone(timedelta(hours=5))
    today = datetime.now(tz_uz).date()
    days  = [(today - timedelta(days=6-i)) for i in range(7)]
    days_str = [d.strftime("%d") for d in days]

    GRID_X = 545
    CELL   = 48
    for di, ds in enumerate(days_str):
        cx = GRID_X + di * CELL + CELL // 2
        draw.text((cx, 155), ds, font=f_day, fill=(80,80,115), anchor="mm")

    # ── ROW RANGLAR ──
    top3_bg     = [(40,34,8),   (22,22,44),  (42,26,8)  ]
    top3_accent = [(255,215,0), (180,185,205),(215,130,45)]
    top3_name   = [(255,228,60),(210,210,255),(255,195,120)]
    top3_bar    = [(255,215,0), (150,150,255),(255,140,50)]

    for i,(name,points,jon_val,is_vip,uid_str) in enumerate(top10_data):
        y  = HDR_H + i * ROW_H
        cy = y + ROW_H // 2

        bg = top3_bg[i] if i<3 else ((18,18,30) if i%2==0 else (22,22,34))
        draw.rectangle([(0,y),(W,y+ROW_H)], fill=bg)

        ac = top3_accent[i] if i<3 else (45,55,110)
        draw.rectangle([(0,y),(5,y+ROW_H)], fill=ac)

        # Rank badge
        try:
            f_rn = _tf(FONT, 26 if i==0 else 24 if i<3 else 21)
        except:
            f_rn = f_rank
        if i == 0:
            draw.ellipse([(18,cy-28),(72,cy+28)], fill=(160,120,0))
            draw.ellipse([(22,cy-24),(68,cy+24)], fill=(255,215,0))
            draw.text((45,cy), "1", font=f_rn, fill=(80,50,0), anchor="mm")
        elif i == 1:
            draw.ellipse([(22,cy-24),(68,cy+24)], fill=(130,135,148))
            draw.ellipse([(26,cy-20),(64,cy+20)], fill=(210,215,228))
            draw.text((45,cy), "2", font=f_rn, fill=(50,52,60), anchor="mm")
        elif i == 2:
            draw.ellipse([(22,cy-24),(68,cy+24)], fill=(148,90,28))
            draw.ellipse([(26,cy-20),(64,cy+20)], fill=(220,145,55))
            draw.text((45,cy), "3", font=f_rn, fill=(80,40,8), anchor="mm")
        else:
            draw.ellipse([(26,cy-20),(64,cy+20)], fill=(28,32,55))
            draw.text((45,cy), str(i+1), font=f_rn, fill=(80,110,200), anchor="mm")

        # Separator
        draw.rectangle([(82,y+16),(84,y+ROW_H-16)], fill=(35,38,58))

        # Ism
        nc = top3_name[i] if i<3 else (185,188,215)
        display = name[:14]
        draw.text((96, cy-12), display, font=f_name, fill=nc, anchor="lm")

        # VIP
        if is_vip:
            nx = 96 + int(f_name.getlength(display)) + 12
            s  = 8
            draw.polygon([(nx,cy-20),(nx+s,cy-12),(nx,cy-4),(nx-s,cy-12)], fill=(100,190,255))

        # Jon foizi
        if jon_val>=80:   jc=(245,70,70)
        elif jon_val>=50: jc=(245,148,40)
        elif jon_val>=20: jc=(240,205,40)
        else:             jc=(100,100,100)
        draw.ellipse([(96,cy+10),(106,cy+20)], fill=jc)
        draw.text((112, cy+21), f"{jon_val}%", font=f_small, fill=jc, anchor="lm")

        # ── 7 KUNLIK GRID ──
        users_all = load_all_users(force=True)
        udata     = users_all.get(str(uid_str), {})
        done_log  = udata.get("done_log", {})

        for di, d in enumerate(days):
            cx   = GRID_X + di * CELL + CELL // 2
            ds   = d.strftime("%Y-%m-%d")
            r    = 16
            if ds > today.strftime("%Y-%m-%d"):
                # Kelmagan kun — bo'sh
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(30,30,48))
            elif done_log.get(ds):
                # Bajarilgan — yashil
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(20,160,80))
                draw.ellipse([(cx-r+2,cy-r+2),(cx+r-2,cy-r+2+8)], fill=(40,200,110))
            else:
                # Bajarilmagan — qizil
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(180,40,40))
                draw.ellipse([(cx-r+2,cy-r+2),(cx+r-2,cy-r+2+8)], fill=(220,70,70))

        # Ball
        draw.text((932, cy-12), f"{points}", font=f_pts,   fill=(220,220,242), anchor="rm")
        draw.text((932, cy+10), "ball",      font=f_small, fill=(95,95,132),   anchor="rm")

        # Row chiziq
        draw.rectangle([(5,y+ROW_H),(W-5,y+ROW_H+1)], fill=(25,25,40))

    # ── LEGEND ──
    fy = HDR_H + 10 * ROW_H + 5
    draw.rectangle([(0,fy),(W,H)], fill=(14,14,24))
    draw.rectangle([(0,fy),(W,fy+2)], fill=(140,110,0))

    lx = 60
    ly = fy + FTR_H // 2
    draw.ellipse([(lx-8,ly-8),(lx+8,ly+8)], fill=(20,160,80))
    draw.text((lx+14, ly+1), "Bajarildi", font=f_label, fill=(100,180,120), anchor="lm")
    draw.ellipse([(lx+130-8,ly-8),(lx+130+8,ly+8)], fill=(180,40,40))
    draw.text((lx+144, ly+1), "Bajarilmadi", font=f_label, fill=(180,100,100), anchor="lm")
    draw.ellipse([(lx+270-8,ly-8),(lx+270+8,ly+8)], fill=(30,30,48))
    draw.text((lx+284, ly+1), "Ma'lumot yo'q", font=f_label, fill=(80,80,110), anchor="lm")

    draw.text((W-60, ly+1), "Bugun yangilangan", font=f_label, fill=(70,70,105), anchor="rm")

    buf = io.BytesIO()
    buf.name = "reyting.png"
    img.save(buf, format="PNG", optimize=False, compress_level=1)
    buf.seek(0)
    return buf
def _tf(path, size):
    """Font topish - har xil serverlarda ishlaydi"""
    import os
    bold_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    ]
    regular_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    candidates = [path] if path else []
    for fp in bold_fallbacks + regular_fallbacks:
        if fp not in candidates:
            candidates.append(fp)
    for fp in candidates:
        if fp and os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()


def generate_rating_grid(top10_users, all_users):
    """
    top10_users: [(name, points, username, user_id), ...]
    all_users:   {user_id: udata, ...}
    Returns: BytesIO rasm
    """
    from datetime import timezone, timedelta
    tz_uz     = timezone(timedelta(hours=5))
    today_dt  = datetime.now(tz_uz)
    today_str = today_dt.strftime("%Y-%m-%d")
    days      = [(today_dt - timedelta(days=6-i)).strftime("%Y-%m-%d") for i in range(7)]
    day_lbls  = [(today_dt - timedelta(days=6-i)).strftime("%d") for i in range(7)]

    # Font — _tf() barcha serverlarda ishlaydi (fallback bilan)
    FB = None  # bold
    FR = None  # regular
    for p in ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
              "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"]:
        if os.path.exists(p): FB = p; break
    for p in ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
              "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"]:
        if os.path.exists(p): FR = p; break

    def _f(path, size):
        if path:
            try: return ImageFont.truetype(path, size)
            except: pass
        return ImageFont.load_default()

    # O'lchamlar
    W       = 780
    ROW_H   = 72
    HDR_H   = 108
    FTR_H   = 48
    COL_W   = 56
    NAME_W  = 240
    PAD_L   = 16
    CELL_R  = 22
    ROWS    = len(top10_users)
    H       = HDR_H + ROW_H * ROWS + FTR_H

    F_TITLE = _f(FB, 28)
    F_SUB   = _f(FR, 16)
    F_NAME  = _f(FB, 22)
    F_PTS   = _f(FR, 15)
    F_RANK  = _f(FB, 20)
    F_DAY   = _f(FR, 14)
    F_LEG   = _f(FR, 14)

    img  = Image.new("RGB", (W, H), (13, 13, 22))
    draw = ImageDraw.Draw(img)

    # Header
    for y in range(HDR_H):
        t = y / HDR_H
        r = int(13 + t * 8); b = int(22 + t * 16)
        draw.line([(0,y),(W,y)], fill=(r, r, b))
    draw.rectangle([(0, HDR_H-2),(W, HDR_H)], fill=(180,140,0))
    draw.text((W//2, int(HDR_H*0.38)), "TOP-10  •  7 KUNLIK FAOLLIK",
              font=F_TITLE, fill=(255,215,0), anchor="mm")
    draw.text((W//2, int(HDR_H*0.72)), "Super Habits Bot  •  @Super_habits_bot",
              font=F_SUB, fill=(120,120,165), anchor="mm")

    oy_uzb = ["","Yan","Fev","Mar","Apr","May","Iyn","Iyl","Avg","Sen","Okt","Noy","Dek"]
    for j in range(7):
        cx     = PAD_L + NAME_W + j * COL_W + COL_W // 2
        dt_obj = today_dt - timedelta(days=6-j)
        draw.text((cx, HDR_H - 10), day_lbls[j], font=F_DAY, fill=(180,180,210), anchor="mb")
        if j == 0 or dt_obj.day == 1:
            draw.text((cx, HDR_H - 26), oy_uzb[dt_obj.month], font=F_DAY, fill=(100,100,145), anchor="mb")

    rank_colors = [(255,215,0),(200,205,220),(215,135,55)] + [(80,110,195)]*7
    bg_colors   = [(38,34,10),(20,20,34),(24,24,40),(20,20,34),(24,24,40),
                   (20,20,34),(24,24,40),(20,20,34),(24,24,40),(20,20,34)]

    for i, (name, points, username, target_uid) in enumerate(top10_users):
        y  = HDR_H + i * ROW_H
        cy = y + ROW_H // 2
        rc = rank_colors[i]
        draw.rectangle([(0,y),(W, y+ROW_H)], fill=bg_colors[i])
        draw.rectangle([(0,y),(4, y+ROW_H)], fill=rc)

        rr = ROW_H // 2 - 8
        draw.ellipse([(PAD_L+2, cy-rr),(PAD_L+2+rr*2, cy+rr)], fill=(24,28,52))
        draw.text((PAD_L+2+rr, cy), str(i+1), font=F_RANK, fill=rc, anchor="mm")

        tx = PAD_L + 2 + rr*2 + 10
        draw.text((tx, cy - 12), name[:15], font=F_NAME, fill=(215,215,245), anchor="lm")
        draw.text((tx, cy + 12), f"{points} ball", font=F_PTS, fill=(110,110,155), anchor="lm")

        udata     = all_users.get(str(target_uid), {})
        done_log  = udata.get("done_log", {})
        bot_start = min(done_log.keys()) if done_log else today_str

        for j, dstr in enumerate(days):
            cx = PAD_L + NAME_W + j * COL_W + COL_W // 2
            r  = CELL_R
            if dstr > today_str or dstr < bot_start:
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], outline=(45,45,68), width=2)
            elif done_log.get(dstr):
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(22,145,62))
                draw.ellipse([(cx-r+4,cy-r+4),(cx+r-4,cy+r-4)], fill=(40,200,82))
            else:
                draw.ellipse([(cx-r,cy-r),(cx+r,cy+r)], fill=(145,25,25))
                draw.ellipse([(cx-r+4,cy-r+4),(cx+r-4,cy+r-4)], fill=(195,48,48))

        draw.rectangle([(4,y+ROW_H-1),(W-4, y+ROW_H)], fill=(28,28,44))

    fy = HDR_H + ROWS * ROW_H
    draw.rectangle([(0,fy),(W,H)], fill=(14,14,24))
    draw.rectangle([(0,fy),(W,fy+2)], fill=(120,95,0))
    lx = PAD_L + 8; ly = fy + FTR_H // 2; r2 = 8
    draw.ellipse([(lx,       ly-r2),(lx+r2*2,       ly+r2)], fill=(40,200,82))
    draw.text((lx+r2*2+6,         ly), "Bajarildi",      font=F_LEG, fill=(150,150,180), anchor="lm")
    draw.ellipse([(lx+130,   ly-r2),(lx+130+r2*2,   ly+r2)], fill=(195,48,48))
    draw.text((lx+130+r2*2+6,     ly), "Bajarilmadi",    font=F_LEG, fill=(150,150,180), anchor="lm")
    draw.ellipse([(lx+280,   ly-r2),(lx+280+r2*2,   ly+r2)], outline=(45,45,68), width=2)
    draw.text((lx+280+r2*2+6,     ly), "Ma'lumot yo'q", font=F_LEG, fill=(95,95,125), anchor="lm")

    buf = io.BytesIO()
    buf.name = "reyting.png"
    img.save(buf, format="PNG", optimize=False, compress_level=1)
    buf.seek(0)
    return buf

def show_rating(uid):
    from datetime import timezone, timedelta
    users   = load_all_users(force=True)
    ranking = []
    for user_id, udata in users.items():
        ranking.append((
            udata.get("name", "?"),
            udata.get("points", 0),
            udata.get("username", ""),
            user_id
        ))
    ranking.sort(key=lambda x: x[1], reverse=True)
    top10  = ranking[:10]
    kb     = InlineKeyboardMarkup()
    webapp_url = os.environ.get("WEBAPP_URL", "")
    if webapp_url:
        from telebot.types import WebAppInfo
        kb.add(InlineKeyboardButton("🌐 To'liq ko'rish", web_app=WebAppInfo(url=webapp_url)))
    kb.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
    u = load_user(uid)
    if not top10:
        sent = bot.send_message(uid, T(uid, "rating_empty"), parse_mode="Markdown", reply_markup=kb)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    medals  = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text    = "🏆 *Reyting — Top 10*\n" + "▬" * 12 + "\n\n"
    for i, (name, points, username, target_uid) in enumerate(top10):
        udata   = users.get(str(target_uid), {})
        jon_val = max(0, min(100, udata.get("jon", 100)))
        je      = "❤️" if jon_val>=80 else "🧡" if jon_val>=50 else "💛" if jon_val>=20 else "🖤"
        vip_b   = " 💎" if udata.get("is_vip") else ""
        uname   = username.lstrip("@") if username and username != "—" else ""
        link    = f"[{name}](https://t.me/{uname})" if uname else f"[{name}](tg://user?id={target_uid})"
        text   += f"{medals[i]} {link}{vip_b} — *{points}* ball  {je} {jon_val}%\n"

    sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb,
                            disable_web_page_preview=True)
    u["main_msg_id"] = sent.message_id
    save_user(uid, u)


# ============================================================
#  STATISTIKA
# ============================================================
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

# ============================================================
#  HAFTALIK HISOBOT
# ============================================================
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

# ============================================================
#  ODAT O'CHIRISH
# ============================================================
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

# ============================================================
#  CALLBACK HANDLER
# ============================================================
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    uid   = call.from_user.id
    cdata = call.data
    u     = load_user(uid)

    # Kechki eslatma — "Tushundim" tugmasi
    if cdata == "evening_dismiss":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            bot.answer_callback_query(call.id)
        return

    # Ulashish natijasini o'chirish — "Tasdiqlash" tugmasi
    if cdata == "share_del":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            bot.answer_callback_query(call.id)
        return

    # Eski tugma bosilsa — bot yangilanganini bildirish
    # Til tanlash tugmalari phone bo'lmasa ham ishlashi kerak
    if not u.get("phone") and not cdata.startswith("set_lang_"):
        try:
            bot.answer_callback_query(call.id, "Bot 🆕 yangilangan, /start ni bosing!", show_alert=True)
        except Exception:
            pass
        return

    # Til tanlash
    if cdata.startswith("set_lang_"):
        lang = cdata[9:]
        u["lang"] = lang
        lang_msg_id = u.pop("lang_msg_id", None)
        from_settings = u.pop("lang_from_settings", False)
        save_user(uid, u)
        bot.answer_callback_query(call.id, T(uid, "lang_set"))
        # O'chiriladigan xabarlarni to'plash
        _lang_cleanup = []
        _lang_cleanup.append(call.message.message_id)
        if lang_msg_id and lang_msg_id != call.message.message_id:
            _lang_cleanup.append(lang_msg_id)
        if from_settings:
            # Sozlamalar menyusiga qaytish
            kb_set = InlineKeyboardMarkup()
            kb_set.add(InlineKeyboardButton(T(uid, "btn_change_lang"), callback_data="settings_lang"))
            kb_set.add(InlineKeyboardButton(T(uid, "btn_change_info"), callback_data="settings_info"))
            kb_set.add(cBtn(T(uid, "btn_home"),        "menu_main", "primary"))
            sent = bot.send_message(uid, T(uid, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            name = call.from_user.first_name
            if not u.get("phone"):
                # Til tanlandi, endi telefon so'ralsin
                kb_ph = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                kb_ph.add(KeyboardButton(T(uid, "share_phone"), request_contact=True))
                sent_ph = bot.send_message(
                    uid,
                    T(uid, "ask_phone"),
                    parse_mode="Markdown",
                    reply_markup=kb_ph
                )
                u["reg_msg_id"] = sent_ph.message_id
                u["state"] = "waiting_phone_reg"
                save_user(uid, u)
            elif u.get("habits"):
                sent_main = send_message_colored(uid, build_main_text(uid), main_menu_dict(uid))
                if sent_main is None:
                    sent_main = bot.send_message(uid, build_main_text(uid), parse_mode="Markdown", reply_markup=main_menu(uid))
                u["main_msg_id"] = sent_main.message_id
                save_user(uid, u)
            else:
                sent_main = send_message_colored(uid, T(uid, "welcome_new", name=name), main_menu_dict(uid))
                if sent_main is None:
                    sent_main = bot.send_message(uid, T(uid, "welcome_new", name=name), parse_mode="Markdown", reply_markup=main_menu(uid))
                u["main_msg_id"] = sent_main.message_id
                save_user(uid, u)
        # Yangi kontent ko'rsatilgandan KEYIN eski til xabarlarini o'chirish
        def _del_lang_batch(cid, ids):
            time.sleep(0.5)
            for mid in ids:
                try: bot.delete_message(cid, mid)
                except: pass
        threading.Thread(target=_del_lang_batch, args=(uid, _lang_cleanup), daemon=True).start()
        return

    if cdata not in ("check_sub", "admin_cancel", "admin_close") and not cdata.startswith("admin_"):
        if not check_subscription(uid):
            bot.answer_callback_query(call.id)
            send_sub_required(uid)
            return

    if cdata == "check_sub":
        if check_subscription(uid):
            bot.answer_callback_query(call.id, "✅")
            _sub_msg = call.message.message_id
            u.pop("sub_msg_id", None)
            save_user(uid, u)
            # Til tanlamagan bo'lsa
            if not u.get("lang"):
                sent_lang = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=lang_keyboard())
                u["lang_msg_id"] = sent_lang.message_id
                save_user(uid, u)
            else:
                send_main_menu(uid)
            # Yangi kontent ko'rsatilgandan KEYIN eski sub xabarini o'chirish
            def _del_sub_bg(cid, mid):
                time.sleep(0.5)
                try: bot.delete_message(cid, mid)
                except: pass
            threading.Thread(target=_del_sub_bg, args=(uid, _sub_msg), daemon=True).start()
        else:
            bot.answer_callback_query(call.id, "❌ Hali a'zo bo'lmadingiz!")
        return

    if cdata == "admin_test_onboard":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        send_main_menu(uid)
        return

    if cdata == "admin_close":
        if uid != ADMIN_ID:
            return
        u["state"] = None
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        send_main_menu(uid)
        return

    if cdata == "bc_user_ack":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    if cdata == "bc_confirm":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        try: bot.send_message(uid, "🛠 *Admin panel*", parse_mode="Markdown", reply_markup=admin_menu())
        except: pass
        return

    if cdata == "bc_detail":
        if uid != ADMIN_ID:
            return
        failed_list = u.get("bc_failed_list", [])
        if not failed_list:
            bot.answer_callback_query(call.id, "Bloklagan foydalanuvchi yo'q", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        detail = "🚫 *Botni bloklagan foydalanuvchilar:*\n\n"
        for i, fl in enumerate(failed_list, 1):
            detail += f"  {i}. {fl}\n"
        kb_detail = InlineKeyboardMarkup()
        kb_detail.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data="bc_detail_confirm"))
        try:
            bot.edit_message_text(detail, uid, call.message.message_id,
                                  parse_mode="Markdown", reply_markup=kb_detail)
        except:
            pass
        return

    if cdata == "bc_detail_confirm":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi")
        u.pop("bc_failed_list", None)
        save_user(uid, u)
        def del_bc_detail(chat_id, mid):
            time.sleep(5)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_bc_detail, args=(uid, call.message.message_id), daemon=True).start()
        return

    if cdata == "admin_cancel":
        if uid != ADMIN_ID:
            return
        u["state"] = None
        save_user(uid, u)
        bot.answer_callback_query(call.id, "Bekor qilindi")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        bot.send_message(uid, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
        return

    if cdata == "admin_notify_update":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            InlineKeyboardButton("✅ Ha, yuborish", callback_data="admin_notify_confirm"),
            cBtn("❌ Yo'q", "admin_cancel", "danger")
        )
        sent_ask = bot.send_message(
            uid,
            "🆕 *Bot yangilandi xabari*\n\n"
            "Barcha foydalanuvchilarga quyidagi xabar yuboriladi:\n\n"
            "_\"Bot 🆕 yangilandi. /start ni bosib yoki yuborib siz ham yangilang!\"_\n\n"
            "Davom etasizmi?",
            parse_mode="Markdown",
            reply_markup=kb_confirm
        )
        u["notify_confirm_msg_id"] = sent_ask.message_id
        save_user(uid, u)
        return

    if cdata == "admin_notify_confirm":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        users      = load_all_users(force=True)
        sent_count = 0
        failed     = 0
        update_text = "*Bot 🆕 yangilandi. /start ni bosib yoki yuborib siz ham yangilang!*"
        for target_uid in users:
            if int(target_uid) == ADMIN_ID:
                continue
            try:
                bot.send_message(int(target_uid), update_text, parse_mode="Markdown")
                sent_count += 1
            except Exception:
                failed += 1
        result = f"✅ Yangilanish xabari {sent_count} ta foydalanuvchiga yuborildi."
        if failed:
            result += f"\n❌ {failed} ta foydalanuvchiga yetmadi."
        sent_res = bot.send_message(uid, result)
        def del_res(chat_id, mid):
            time.sleep(5)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_res, args=(uid, sent_res.message_id), daemon=True).start()
        bot.send_message(uid, "🛠 *Admin panel | Maxfiy va muhim qism*", parse_mode="Markdown", reply_markup=admin_menu())
        return

    if cdata == "admin_give_points":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "admin_waiting_points_id"
        kb2 = InlineKeyboardMarkup()
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        sent_gp = bot.send_message(
            uid,
            "🎁 *Ball berish / ayirish*\n\n"
            "Foydalanuvchi *ID raqamini* kiriting:\n\n"
            "_ID raqamni foydalanuvchilar ro'yxatidan topishingiz mumkin_",
            parse_mode="Markdown",
            reply_markup=kb2
        )
        u["give_points_msg_id"] = sent_gp.message_id
        save_user(uid, u)
        return

    if cdata == "admin_broadcast":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot.send_message(uid, "📢 *Habar yuborish*\n\nQayerga yubormoqchisiz?", parse_mode="Markdown", reply_markup=admin_broadcast_menu())
        return

    if cdata in ("admin_bc_private", "admin_bc_groups", "admin_bc_all"):
        if uid != ADMIN_ID:
            return
        u["state"] = cdata
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        labels = {"admin_bc_private": "shaxsiy chatlarga", "admin_bc_groups": "guruhlarga", "admin_bc_all": "hammaga"}
        # Trigger xabari — admindan reply kutamiz
        sent_trigger = bot.send_message(
            uid,
            f"✏️ *Yubormoqchi bo'lgan xabaringizni yozing ({labels[cdata]}):*\n\n"
            f"_Yozing — matn, rasm yoki video_",
            parse_mode="Markdown"
        )
        u["bc_trigger_msg_id"] = sent_trigger.message_id
        save_user(uid, u)
        return

    if cdata == "admin_users" or cdata.startswith("admin_users_page_"):
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        users = load_all_users(force=True)
        if not users:
            bot.send_message(uid, "👥 Foydalanuvchilar yo'q.", reply_markup=admin_menu())
            return
        per_page    = 10
        users_list  = list(users.items())
        total       = len(users_list)
        total_pages = (total + per_page - 1) // per_page
        page        = 1
        if cdata.startswith("admin_users_page_"):
            page = int(cdata[17:])
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end   = start + per_page
        page_users = users_list[start:end]

        text = f"👥 Jami: {total} ta foydalanuvchi | Sahifa {page}/{total_pages}\n" + "▬" * 20 + "\n\n"
        for i, (target_uid, udata) in enumerate(page_users, start + 1):
            name     = udata.get("name", "—")
            username = udata.get("username", "—")
            if username and username != "—" and not username.startswith("@"):
                username = "@" + username
            phone  = udata.get("phone", "Kiritilmagan")
            joined = udata.get("joined_at", "—")
            habits = udata.get("habits", [])
            text += f"👤 {i}. {name}\n"
            text += f"  🆔 ID: {target_uid}\n"
            text += f"  📌 Username: {username}\n"
            text += f"  📞 Tel: {phone}\n"
            text += f"  📅 Qo'shilgan: {joined}\n"
            if habits:
                text += f"  📋 Odatlar ({len(habits)} ta):\n"
                for h in habits:
                    text += f"    • {h['name']} | {h['time']} | streak: {h.get('streak',0)} kun\n"
            else:
                text += "  📋 Odatlar: yo'q\n"
            text += "\n"

        kb = InlineKeyboardMarkup()
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton(f"⬅️ {page-1}", callback_data=f"admin_users_page_{page-1}"))
        nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav.append(InlineKeyboardButton(f"{page+1} ➡️", callback_data=f"admin_users_page_{page+1}"))
        if len(nav) > 1 or total_pages > 1:
            kb.row(*nav)
        kb.row(
            cBtn("🔙 Admin panel", "admin_cancel", "primary"),
            cBtn("🏠 Asosiy menyu", "admin_close", "primary")
        )
        bot.send_message(uid, text, reply_markup=kb)
        return

    if cdata == "admin_channel":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        settings = load_settings()
        msg_text = "🔗 *Majburiy kanallar* (maksimal 3 ta)\n\n"
        kb2 = InlineKeyboardMarkup()
        for i in range(1, 4):
            ch    = settings.get(f"required_channel_{i}", None)
            title = settings.get(f"required_channel_title_{i}", None)
            if ch:
                label = f"✅ {i}. {title or ch}"
                msg_text += f"{i}. {title or ch} ({ch})\n"
                kb2.row(
                    InlineKeyboardButton(f"✏️ {i}-ni o'zgartirish", callback_data=f"admin_ch_edit_{i}"),
                    InlineKeyboardButton(f"🗑 {i}-ni o'chirish",    callback_data=f"admin_ch_del_{i}")
                )
            else:
                msg_text += f"{i}. — (bo'sh)\n"
                kb2.add(InlineKeyboardButton(f"➕ {i}-kanal qo'shish", callback_data=f"admin_ch_edit_{i}"))
        # Eski format bilan moslik
        old_ch = settings.get("required_channel", None)
        if old_ch:
            msg_text += f"\n_(Eski format: {old_ch})_"
        msg_text += "\n\nQaysi kanalni boshqarmoqchisiz?"
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        sent_ch = bot.send_message(uid, msg_text, parse_mode="Markdown", reply_markup=kb2)
        u["channel_msg_id"] = sent_ch.message_id
        save_user(uid, u)
        return

    if cdata.startswith("admin_ch_edit_"):
        if uid != ADMIN_ID:
            return
        slot = int(cdata[14:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = f"admin_waiting_channel_{slot}"
        kb2 = InlineKeyboardMarkup()
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        sent_ch = bot.send_message(
            uid,
            f"🔗 {slot}-kanal username yozing:\n\n_Masalan: @mening_kanalim_",
            parse_mode="Markdown",
            reply_markup=kb2
        )
        u["channel_msg_id"] = sent_ch.message_id
        save_user(uid, u)
        return

    if cdata.startswith("admin_ch_del_"):
        if uid != ADMIN_ID:
            return
        slot = int(cdata[13:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        settings = load_settings()
        settings.pop(f"required_channel_{slot}", None)
        settings.pop(f"required_channel_title_{slot}", None)
        save_settings(settings)
        bot.send_message(uid, f"✅ {slot}-kanal o'chirildi.", reply_markup=admin_menu())
        return

    if cdata == "admin_stats":
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot.send_message(uid, "📈 *Statistika — davr tanlang:*", parse_mode="Markdown", reply_markup=admin_stats_period_menu())
        return

    if cdata.startswith("admin_stats_"):
        if uid != ADMIN_ID:
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        period = cdata[12:]
        users  = load_all_users(force=True)
        today  = date.today()
        if period == "all":
            filtered     = users
            period_label = "Umumiy"
        else:
            days     = int(period)
            filtered = {}
            for k, v in users.items():
                try:
                    joined = date.fromisoformat(v.get("joined_at", "2000-01-01"))
                    if (today - joined).days <= days:
                        filtered[k] = v
                except Exception:
                    pass
            labels       = {"1": "1 kun", "7": "1 hafta", "30": "1 oy", "365": "1 yil"}
            period_label = labels.get(period, period)
        text  = f"📈 *Statistika — {period_label}*\n\n"
        text += f"👥 Qo'shilgan foydalanuvchilar: *{len(filtered)} ta*\n\n"
        text += "📋 *Odat yaratish bo'yicha:*\n"
        habit_counts = []
        for target_uid, udata in users.items():
            count = len(udata.get("habits", []))
            if count > 0:
                habit_counts.append((udata.get("name", f"ID:{target_uid}"), count))
        habit_counts.sort(key=lambda x: x[1], reverse=True)
        if habit_counts:
            for name, count in habit_counts[:20]:
                text += f"  • *{name}*: {count} ta odat\n"
        else:
            text += "  Hali odat yaratilmagan.\n"
        kb2 = InlineKeyboardMarkup()
        kb2.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb2)
        return

    if cdata == "menu_settings":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_set = InlineKeyboardMarkup()
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_lang"),        callback_data="settings_lang"))
        kb_set.add(InlineKeyboardButton(T(uid, "btn_change_info"),        callback_data="settings_info"))
        kb_set.add(InlineKeyboardButton("⚙️ Odat sozlamalari",           callback_data="settings_habits_time"))
        kb_set.add(InlineKeyboardButton("💬 Dasturchiga habar",           callback_data="settings_contact_dev"))
        kb_set.add(cBtn(T(uid, "btn_home"), "menu_main", "primary"))
        sent = bot.send_message(uid, T(uid, "settings_title"), parse_mode="Markdown", reply_markup=kb_set)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "settings_lang":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["lang_from_settings"] = True
        save_user(uid, u)
        kb_lang = lang_keyboard()
        kb_lang.row(
            cBtn("⬅️ Orqaga", "menu_settings", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, "🌐 Tilni tanlang / Choose language / Выберите язык / Dil seçin:", reply_markup=kb_lang)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "settings_contact_dev":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "waiting_dev_message"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "menu_settings", "danger"))
        sent = bot.send_message(uid, T(uid, "set_dev_prompt"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["dev_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "settings_info":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_info = InlineKeyboardMarkup()
        kb_info.add(InlineKeyboardButton("✏️ Ismni o'zgartirish",           callback_data="change_name"))
        kb_info.add(InlineKeyboardButton("📱 Telefon raqamni o'zgartirish", callback_data="change_phone"))
        kb_info.row(
            cBtn("⬅️ Orqaga", "menu_settings", "primary"),
            cBtn(T(uid, "btn_home"),   "menu_main", "primary")
        )
        sent = bot.send_message(uid, T(uid, "change_info_text"), parse_mode="Markdown", reply_markup=kb_info)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Odatlar vaqtini tahrirlash menyusi ---
    if cdata == "settings_habits_time":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        habits = u.get("habits", [])
        if not habits:
            sent_e = bot.send_message(uid, T(uid, "no_habits"), parse_mode="Markdown")
            def del_no_h(chat_id, mid):
                time.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=del_no_h, args=(uid, sent_e.message_id), daemon=True).start()
            kb_back = InlineKeyboardMarkup()
            kb_back.add(cBtn("⬅️ Orqaga", "settings_info", "primary"))
            bot.send_message(uid, T(uid, "change_info_text"), parse_mode="Markdown", reply_markup=kb_back)
            return
        # Umumiy vaqt holati
        all_timed    = all(h.get("time") not in (None, "", "vaqtsiz") for h in habits)
        all_timeless = all(h.get("time") in (None, "", "vaqtsiz") for h in habits)
        kb_habits = InlineKeyboardMarkup()
        for h in habits:
            h_type   = h.get("type", "simple")
            has_time = h.get("time") not in (None, "", "vaqtsiz")
            if h_type == "repeat":
                times = h.get("repeat_times", [h.get("time", "?")])
                lbl = f"🔁 {h['name']} ({', '.join(times)})"
            else:
                icon = "⏰" if has_time else "🔕"
                lbl  = f"{icon} {h['name']} ({h.get('time','vaqtsiz')})"
            kb_habits.add(InlineKeyboardButton(lbl, callback_data=f"edit_htime_{h['id']}"))
        # Umumiy vaqt tugmasi
        if all_timeless:
            kb_habits.add(InlineKeyboardButton("⏰ Umumiy vaqt belgilash", callback_data="edit_htime_all_set"))
        else:
            kb_habits.add(InlineKeyboardButton("🔕 Umumiy vaqtni olib tashlash", callback_data="edit_htime_all_remove"))
        kb_habits.add(InlineKeyboardButton("✏️ Odat nomini o'zgartirish", callback_data="change_habit_name"))
        kb_habits.row(
            cBtn("⬅️ Orqaga", "settings_info", "primary"),
            cBtn(T(uid, "btn_home"),  "menu_main", "primary")
        )
        sent = bot.send_message(uid, T(uid, "set_habit_settings"), parse_mode="Markdown", reply_markup=kb_habits)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Umumiy vaqtni olib tashlash ---
    if cdata == "edit_htime_all_remove":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        for h in u.get("habits", []):
            h["time"] = "vaqtsiz"
            schedule.clear(f"{uid}_{h['id']}")
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "set_all_notime"))
        def del_ok_all(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_ok_all, args=(uid, sent_ok.message_id), daemon=True).start()
        # Ro'yxatni qayta chiqarish
        habits    = u.get("habits", [])
        kb_habits = InlineKeyboardMarkup()
        for h in habits:
            kb_habits.add(InlineKeyboardButton(f"🔕 {h['name']} (vaqtsiz)", callback_data=f"edit_htime_{h['id']}"))
        kb_habits.add(InlineKeyboardButton("⏰ Umumiy vaqt belgilash", callback_data="edit_htime_all_set"))
        kb_habits.row(
            cBtn("⬅️ Orqaga", "settings_info", "primary"),
            cBtn(T(uid, "btn_home"),  "menu_main", "primary")
        )
        sent2 = bot.send_message(uid, T(uid, "set_which_time"), parse_mode="Markdown", reply_markup=kb_habits)
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return

    # --- Umumiy vaqt belgilash (barcha odatlarga bir vaqt) ---
    if cdata == "edit_htime_all_set":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"]             = "editing_all_habits_time"
        u["editing_habit_id"]  = "ALL"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "settings_habits_time", "danger"))
        sent = bot.send_message(uid, T(uid, "set_all_time_ask"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Bitta odat vaqti tahrirlash ---
    if cdata.startswith("edit_htime_") and not cdata.startswith("edit_htime_notime_") and not cdata.startswith("edit_htime_start_"):
        habit_id = cdata[11:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        habits = u.get("habits", [])
        h = next((x for x in habits if x["id"] == habit_id), None)
        if not h:
            send_main_menu(uid)
            return
        h_type    = h.get("type", "simple")
        has_time  = h.get("time") not in (None, "", "vaqtsiz")
        kb_e = InlineKeyboardMarkup()
        if h_type == "repeat":
            times = h.get("repeat_times", [h.get("time", "?")])
            info = f"🔁 *{h['name']}* — takror: {h.get('repeat_count',len(times))} marta\n"
            info += "Joriy vaqtlar: " + " | ".join(f"*{t}*" for t in times) + "\n\n"
            info += "Yangi vaqtlarni qayta kiriting:"
            kb_e.add(InlineKeyboardButton("✏️ Vaqtlarni qayta kiritish", callback_data=f"edit_htime_start_{habit_id}"))
        else:
            curr = h.get("time", "vaqtsiz")
            info = f"⏰ *{h['name']}*\nJoriy vaqt: *{curr}*\n\n"
            if has_time:
                info += "Vaqtni o'zgartirish yoki vaqtsiz holatga o'tkazish:"
                kb_e.add(InlineKeyboardButton("✏️ Vaqtni o'zgartirish",   callback_data=f"edit_htime_start_{habit_id}"))
                kb_e.add(InlineKeyboardButton("🔕 Vaqtsiz holatga o'tish", callback_data=f"edit_htime_notime_{habit_id}"))
            else:
                info += "Hozir vaqtsiz. Vaqt belgilash:"
                kb_e.add(InlineKeyboardButton("⏰ Vaqt belgilash",         callback_data=f"edit_htime_start_{habit_id}"))
        kb_e.row(
            cBtn("⬅️ Orqaga", "settings_habits_time", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, info, parse_mode="Markdown", reply_markup=kb_e)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # --- Vaqtsiz holatga o'tkazish ---
    if cdata.startswith("edit_htime_notime_"):
        habit_id = cdata[18:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                h["time"] = "vaqtsiz"
                schedule.clear(f"{uid}_{habit_id}")
                break
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "set_habit_notime"), parse_mode="Markdown")
        def del_ok_notime(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_ok_notime, args=(uid, sent_ok.message_id), daemon=True).start()
        # Odatlar ro'yxatiga qaytish
        kb_back = InlineKeyboardMarkup()
        kb_back.add(InlineKeyboardButton("⬅️ Odatlar ro'yxati", callback_data="settings_habits_time"))
        kb_back.add(cBtn(T(uid, "btn_home"),     "menu_main", "primary"))
        sent2 = bot.send_message(uid, T(uid, "set_edit_times"), parse_mode="Markdown", reply_markup=kb_back)
        u["main_msg_id"] = sent2.message_id
        save_user(uid, u)
        return

    # --- Vaqtni tahrirlash boshlash ---
    if cdata.startswith("edit_htime_start_"):
        habit_id = cdata[17:]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        h = next((x for x in u.get("habits", []) if x["id"] == habit_id), None)
        if not h:
            send_main_menu(uid)
            return
        h_type    = h.get("type", "simple")
        rep_count = h.get("repeat_count", 1)
        u["state"] = "editing_habit_time"
        u["editing_habit_id"] = habit_id
        u["editing_habit_times_collected"] = []
        u["editing_habit_type"] = h_type
        u["editing_habit_rep_count"] = rep_count
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "settings_habits_time", "danger"))
        if h_type == "repeat" and rep_count > 1:
            prompt = (
                f"⏰ *{h['name']}* uchun *1/{rep_count}* yangi vaqtni kiriting:\n\n"
                f"_Masalan: 06:00_"
            )
        else:
            prompt = f"⏰ *{h['name']}* uchun yangi vaqtni kiriting:\n\n_Masalan: 07:30_"
        sent = bot.send_message(uid, prompt, parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "change_habit_name":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        habits = u.get("habits", [])
        if not habits:
            sent_e = bot.send_message(uid, T(uid, "no_habits"), parse_mode="Markdown")
            def _del_no(chat_id, mid):
                import time as _t; _t.sleep(3)
                try: bot.delete_message(chat_id, mid)
                except: pass
            threading.Thread(target=_del_no, args=(uid, sent_e.message_id), daemon=True).start()
            send_main_menu(uid)
            return
        # Vaqt bo'yicha tartiblash
        def _sk(h):
            t = h.get("time", "23:59")
            try:
                hh, mm = t.split(":")
                return int(hh)*60 + int(mm)
            except: return 9999
        sorted_h = sorted(habits, key=_sk)
        kb_hn = InlineKeyboardMarkup()
        for h in sorted_h:
            kb_hn.add(InlineKeyboardButton(f"✏️ {h['name']} ({h['time']})", callback_data=f"rename_habit_{h['id']}"))
        kb_hn.row(
            cBtn("⬅️ Orqaga", "settings_habits_time", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, T(uid, "set_which_rename"), parse_mode="Markdown", reply_markup=kb_hn)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "change_name":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "updating_name"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn("⬅️ Orqaga", "settings_info", "primary"))
        sent = bot.send_message(uid, T(uid, "set_new_name"), reply_markup=cancel_kb)
        u["info_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("rename_habit_"):
        habit_id = cdata[len("rename_habit_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Odatni topib nomini saqlash
        habit = next((h for h in u.get("habits", []) if h["id"] == habit_id), None)
        if not habit:
            send_main_menu(uid)
            return
        u["state"] = "renaming_habit"
        u["renaming_habit_id"] = habit_id
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "change_habit_name", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            f"✏️ *{habit['name']}* — yangi nom yozing:",
            parse_mode="Markdown",
            reply_markup=cancel_kb
        )
        u["info_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "change_phone":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "updating_phone"
        save_user(uid, u)
        kb_phone = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb_phone.add(KeyboardButton("📱 Yangi raqam yuborish", request_contact=True))
        sent = bot.send_message(
            uid,
            "📱 Yangi telefon raqamingizni yuboring:\n\n"
            "• Tugmani bosib yuboring, _yoki_\n"
            "• Qo'lda kiriting: *+998901234567*",
            parse_mode="Markdown",
            reply_markup=kb_phone
        )
        u["info_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "menu_add":
        # BUG FIX: Limit 10 emas 15 bo'lishi kerak (LANGS da "15 ta" deyilgan)
        if len(u.get("habits", [])) >= 15:
            bot.answer_callback_query(call.id)
            sent_limit = bot.send_message(
                uid,
                T(uid, "limit"),
                parse_mode="Markdown"
            )
            def del_limit(chat_id, msg_id):
                time.sleep(3)
                try: bot.delete_message(chat_id, msg_id)
                except: pass
            threading.Thread(target=del_limit, args=(uid, sent_limit.message_id), daemon=True).start()
            send_main_menu(uid)
            return
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Odat turini tanlash
        kb_type = InlineKeyboardMarkup()
        kb_type.row(
            InlineKeyboardButton("📌 Oddiy",          callback_data="habit_type_simple"),
            InlineKeyboardButton("🔁 Takrorlanuvchi", callback_data="habit_type_repeat")
        )
        kb_type.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            "📋 *Odat turini tanlang:*\n\n"
            "📌 *Oddiy* — kuniga 1 marta\n"
            "🔁 *Takrorlanuvchi* — kuniga bir necha marta (masalan: 5 vaqt namoz)",
            parse_mode="Markdown", reply_markup=kb_type
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "habit_type_simple":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "waiting_habit_name"
        u["temp_habit"] = {"type": "simple"}
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(uid, T(uid, "ask_habit_name"), parse_mode="Markdown", reply_markup=cancel_kb)
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "habit_type_repeat":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        # Avval necha marta takrorlanishi so'ralinsin
        u["temp_habit"] = {"type": "repeat"}
        u["state"] = "waiting_repeat_count"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            "🔁 *Takrorlanuvchi odat*\n\n"
            "Kuniga necha marta bajarasiz?\n"
            "_Masalan: 2, 3, 5_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return



    if cdata == "cancel":
        u["state"] = None
        u.pop("temp_habit", None)
        old_msg_id = u.pop("temp_msg_id", None)
        save_user(uid, u)
        bot.answer_callback_query(call.id, T(uid, "btn_cancel"))
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        send_main_menu(uid)
        return

    if cdata == "cancel_to_main":
        u["state"] = None
        u.pop("temp_habit", None)
        old_msg_id = u.pop("temp_msg_id", None)
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        if old_msg_id:
            try: bot.delete_message(uid, old_msg_id)
            except: pass
        send_main_menu(uid)
        return

    if cdata.startswith("shield_use_"):
        habit_id = cdata[len("shield_use_"):]
        bot.answer_callback_query(call.id)
        # pending_shield dan streak qiymatini olish
        pending = u.get("pending_shield", {})
        streak_val = pending.pop(habit_id, None)
        if streak_val is not None and u.get("streak_shields", 0) > 0:
            # Streakni tiklash
            for h in u.get("habits", []):
                if h["id"] == habit_id:
                    h["streak"] = streak_val
                    break
            u["streak_shields"]  = u.get("streak_shields", 0) - 1
            u["pending_shield"]  = pending
            save_user(uid, u)
            try:
                bot.edit_message_text(
                    f"🛡 *Streak himoyangiz ishlatildi!*\n\n"
                    f"*🔥 Streakingiz saqlanib qoldi:* {streak_val} kun\n"
                    f"*🛡 Qolgan himoyalar:* {u['streak_shields']} ta",
                    uid, call.message.message_id,
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
        return

    if cdata.startswith("shield_skip_"):
        habit_id = cdata[len("shield_skip_"):]
        bot.answer_callback_query(call.id)
        pending = u.get("pending_shield", {})
        pending.pop(habit_id, None)
        u["pending_shield"] = pending
        save_user(uid, u)
        try:
            bot.edit_message_text(
                "❌ *Streak nollandi.*\n\n"
                "🛡 Himoyangiz saqlanib qoldi — keyingi safar ishlatishingiz mumkin!",
                uid, call.message.message_id,
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return

    if cdata.startswith("weekly_confirm_"):
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        return

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
            return
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
        return

    if cdata.startswith("weekly_view_"):
        idx_r = int(cdata[len("weekly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        reports = u.get("weekly_reports", [])
        if idx_r < 0 or idx_r >= len(reports):
            send_main_menu(uid)
            return
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
        return


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
            return
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
        return

    if cdata.startswith("monthly_view_"):
        idx_m = int(cdata[len("monthly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("monthly_reports", [])
        if idx_m < 0 or idx_m >= len(reports):
            send_main_menu(uid)
            return
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
        return

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
            return
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
        return

    if cdata.startswith("yearly_view_"):
        idx_y = int(cdata[len("yearly_view_"):])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        reports = u.get("yearly_reports", [])
        if idx_y < 0 or idx_y >= len(reports):
            send_main_menu(uid)
            return
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
        return


    # ── ONBOARDING callbacklar ──
    if cdata == "onboard_start":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        send_onboarding_habit_category(uid)
        return

    if cdata == "onboard_skip":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["onboarding"] = False
        save_user(uid, u)
        send_main_menu(uid)
        return

    if cdata.startswith("onboard_cat_"):
        cat = cdata[len("onboard_cat_"):]
        bot.answer_callback_query(call.id)
        if cat == "custom":
            # Foydalanuvchi o'zi yozsin
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            u["state"] = "onboard_waiting_name"
            save_user(uid, u)
            kb_cancel = InlineKeyboardMarkup()
            kb_cancel.add(InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip"))
            sent = bot.send_message(
                uid,
                "✏️ *Odatingiz nomini yozing:*\n\n"
                "_Masalan: Ertalab yugurish, Kitob o'qish, Namoz..._",
                parse_mode="Markdown", reply_markup=kb_cancel
            )
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            send_onboarding_examples(uid, cat)
        return

    if cdata.startswith("onboard_habit_"):
        habit_name = cdata[len("onboard_habit_"):]
        bot.answer_callback_query(call.id)
        send_onboarding_time(uid, habit_name)
        return

    if cdata.startswith("onboard_time_"):
        time_val = cdata[len("onboard_time_"):]
        bot.answer_callback_query(call.id)
        if time_val == "custom":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            u["state"] = "onboard_waiting_time"
            save_user(uid, u)
            kb_cancel = InlineKeyboardMarkup()
            kb_cancel.add(InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="onboard_skip"))
            sent = bot.send_message(
                uid,
                "⏰ *Vaqtni kiriting:*\n\n"
                "_Format: HH:MM (masalan: 07:30)_",
                parse_mode="Markdown", reply_markup=kb_cancel
            )
            u["main_msg_id"] = sent.message_id
            save_user(uid, u)
        else:
            habit_name = u.get("temp_onboard_habit", "Odat")
            finish_onboarding(uid, habit_name, time_val)
        return

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
            return
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
        return

    if cdata == "menu_stats":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_stats(uid)
        return

    if cdata.startswith("stats_page_"):
        page = int(cdata[11:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_stats(uid, page=page)
        return

    if cdata == "menu_delete":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        delete_habit_menu(uid)
        return

    if cdata == "menu_rating":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        show_rating(uid)
        return

    if cdata == "menu_main":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        send_main_menu(uid)
        return

    # ============================================================
    #  2-MENYU (GURUHLAR)
    # ============================================================
    if cdata == "menu2_open":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        send_menu2(uid)
        return

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
        return

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
        return

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
            return
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
        return

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
        return

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
        return

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
            return
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
        return

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
            return
        # Bir necha guruh bo'lsa — tanlash
        if len(groups) == 1:
            target_g_id = groups[0]["id"]
            bot.answer_callback_query(call.id)
            # To'g'ridan group_rating_show ga o'tish
            g = load_group(target_g_id)
            if not g:
                send_menu2(uid)
                return
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
        return

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
            return
        text, kb = _build_group_rating(uid, g, g_id, period)
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_view_"):
        g_id = cdata[len("group_view_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            send_menu2(uid)
            return
        sent = _send_group_view(uid, u, g, g_id)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("group_done_"):
        # format: group_done_{g_id}_{h_id}
        rest   = cdata[len("group_done_"):]
        parts  = rest.rsplit("_", 1)
        g_id   = parts[0]
        h_id   = parts[1] if len(parts) > 1 else "main"
        g = load_group(g_id)
        if not g:
            bot.answer_callback_query(call.id)
            return
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
            return
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
        return

    if cdata.startswith("group_habit_add_"):
        g_id = cdata[len("group_habit_add_"):]
        bot.answer_callback_query(call.id)
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return
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
        return

    if cdata.startswith("group_habit_del_"):
        g_id = cdata[len("group_habit_del_"):]
        bot.answer_callback_query(call.id)
        g = load_group(g_id)
        if not g or str(g.get("admin_id","")) != str(uid):
            return
        habits = g.get("habits", [])
        if not habits and g.get("habit_name"):
            habits = [{"id": "main", "name": g["habit_name"]}]
        if not habits:
            bot.answer_callback_query(call.id, "O'chiradigan odat yo'q!")
            return
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
        return

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
            return
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
        return

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
        return

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
            return
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
        return

    if cdata.startswith("group_join_ack_"):
        # Foydalanuvchi "Tushunarli!" ni bosdi — xabar 5s dan keyin o'chadi
        bot.answer_callback_query(call.id, "✅ Tabriklaymiz!")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return

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
        return

    if cdata.startswith("group_invite_"):
        g_id = cdata[len("group_invite_"):]
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        g = load_group(g_id)
        if not g:
            return
        inv_link = f"https://t.me/{get_bot_username()}?start=grp_{g_id}"
        sent = bot.send_message(uid,
            f"🔗 *{g['name']} — Invite link:*\n\n`{inv_link}`\n\n"
            f"_Ushbu linkni do'stlaringizga yuboring!_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(cBtn("⬅️ Orqaga", f"group_view_{g_id}", "primary"))
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

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
        return

    # ============================================================
    #  BOZOR
    # ============================================================
    if cdata == "menu_bozor":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        balls = u.get("points", 0)
        ref_count  = len(u.get("referrals", []))
        jon_val = round(u.get("jon", 100.0))
        bozor_text = (
            f"🛒 *Bozor —* bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.\n\n"
            f"*⭐ Sizning balingiz:* {balls} ball\n"
            f"*👥 Taklif qilganlar:* {ref_count} ta do'st\n"
            f"*❤️ Jon:* {jon_val}%\n\n"
            "*❤️ Jon sotib olish —* 50 ball evaziga jonni 100% ga tiklash\n"
            "*👥 Do'st taklif qilish —* +50 ball (siz), +25 ball (do'st)\n"
            "*💸 Ballarni ayirboshlash —* yaqin insoniga ball yuborish\n"
            "*🔴 Ballarimni 0 ga tushirish —* barcha ballarni nollash\n"
            "*➖ Ballarimdan olib tashlash —* ma'lum miqdorni ayirish"
        )
        bozor_kb = {"inline_keyboard": [
            [{"text": "❤️ Jon sotib olish (50 ball)",  "callback_data": "bozor_buy_jon",       "style": "primary"}],
            [{"text": "👥 Do'st taklif qilish",        "callback_data": "bozor_referral",      "style": "primary"}],
            [{"text": "💸 Ballarni ayirboshlash",       "callback_data": "bozor_transfer"}],
            [{"text": "🔴 Ballarimni 0 ga tushirish",   "callback_data": "bozor_reset_confirm", "style": "danger"}],
            [{"text": "➖ Ballarimdan olib tashlash",    "callback_data": "bozor_subtract"}],
            [{"text": T(uid, "btn_home"),                "callback_data": "menu_main",           "style": "primary"}],
        ]}
        sent = send_message_colored(uid, bozor_text, bozor_kb)
        if sent is None:
            kb_b = InlineKeyboardMarkup()
            kb_b.add(InlineKeyboardButton("❤️ Jon sotib olish (50 ball)", callback_data="bozor_buy_jon"))
            kb_b.add(InlineKeyboardButton("👥 Do'st taklif qilish",      callback_data="bozor_referral"))
            kb_b.add(InlineKeyboardButton("💸 Ballarni ayirboshlash",     callback_data="bozor_transfer"))
            kb_b.add(InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"))
            kb_b.add(InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract"))
            kb_b.add(cBtn(T(uid, "btn_home"),             "menu_main", "primary"))
            sent = bot.send_message(uid, bozor_text, parse_mode="Markdown", reply_markup=kb_b)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "bozor_buy_jon":
        bot.answer_callback_query(call.id)
        balls = u.get("points", 0)
        jon_val = round(u.get("jon", 100.0))
        if jon_val > 20:
            bot.send_message(uid,
                f"❤️ *Jon sotib olish mumkin emas!*\n\n"
                f"Jon faqat *20% va undan kam* bo'lganda sotib olinadi.\n"
                f"Hozirgi joningiz: *{jon_val}%*",
                parse_mode="Markdown"
            )
            return
        if balls < 50:
            bot.send_message(uid,
                f"⭐ *Balingiz yetarli emas!*\n\nJon sotib olish uchun *50 ball* kerak.\n"
                f"Sizda hozir: *{balls} ball*\n\n"
                "Har kuni odatlarni bajaring — ball to'playsiz! 💪",
                parse_mode="Markdown"
            )
            return
        u["points"] = balls - 50
        u["jon"]    = 100.0
        save_user(uid, u)
        bot.send_message(uid,
            "❤️ *Jon tiklandi!*\n\n"
            "50 ball sarflandi — joningiz *100%* ga qaytdi!\n"
            "Endi odatlarni davom ettiring! 💪",
            parse_mode="Markdown"
        )
        return

    if cdata == "bozor_referral":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        bot_info     = bot.get_me()
        bot_username = bot_info.username
        ref_link     = f"https://t.me/{bot_username}?start=ref_{uid}"
        ref_count    = len(u.get("referrals", []))
        balls_from_refs = ref_count * 50
        # Chegara sovg'alar ro'yxati
        milestones = [
            (5,  "🛡 Streak himoyasi",
                 "Bir kun odat bajarmay qolsangiz\nstreakingiz saqlanib qoladi!"),
            (10, "⭐ +100 ball bonus",  ""),
            (20, "💎 VIP nishon",
                 "Reytingda maxsus belgi +\nkelajakda imtiyozlar!"),
        ]
        # Sarlavha
        text  = "👥 *Do'st taklif qilish*\n\n"
        text += f"*🔗 Sizning linkingiz:*\n`{ref_link}`\n\n"
        text += f"*👥 Taklif qilganlar:* {ref_count} ta do'st\n"
        text += f"*⭐ Yig'ilgan ball:* +{balls_from_refs}\n"
        text += "\n" + "━" * 16 + "\n"
        # Har bir do'st uchun mukofot
        text += "*🎁 Har bir do'st uchun:*\n"
        text += "• Siz: *+50 ball*\n"
        text += "• Do'stingiz: *+25 ball*\n"
        text += "\n" + "━" * 16 + "\n"
        # Chegara sovg'alari
        text += "*🏆 Chegara sovg'alari:*\n"
        next_found = False
        for m_count, m_title, m_desc in milestones:
            if ref_count >= m_count:
                # Allaqachon olindi
                text += f"✅ *{m_count} ta* → {m_title}\n"
            else:
                if not next_found:
                    # Keyingi maqsad
                    need = m_count - ref_count
                    text += f"⬜ *{m_count} ta* → {m_title}\n"
                    if m_desc:
                        for line in m_desc.split("\n"):
                            text += f"          _{line}_\n"
                    next_found = True
                else:
                    text += f"⬜ *{m_count} ta* → {m_title}\n"
                    if m_desc:
                        for line in m_desc.split("\n"):
                            text += f"          _{line}_\n"
        text += "\n"
        # Keyingi chegaragacha qolgan
        next_ms = next((m for m in milestones if ref_count < m[0]), None)
        if next_ms:
            need = next_ms[0] - ref_count
            text += f"*⏳ Keyingi sovg'agacha:* {need} ta do'st qoldi"
        else:
            text += "🏆 *Barcha chegara sovg'alarini oldingiz!*"
        kb_ref = InlineKeyboardMarkup()
        kb_ref.add(InlineKeyboardButton("📋 Havolani nusxalash", switch_inline_query=ref_link))
        kb_ref.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb_ref)
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "bozor_transfer":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "bozor_waiting_transfer_id"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            "💸 *Ballarni ayirboshlash*\n\n"
            "Ballarni yubormoqchi bo'lgan foydalanuvchining *Telegram ID* sini kiriting:\n\n"
            "_ID raqamni foydalanuvchidan so'rang yoki reyitingda ko'ring_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "bozor_edit":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        balls = u.get("points", 0)
        kb_edit = InlineKeyboardMarkup()
        kb_edit.add(InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"))
        kb_edit.add(InlineKeyboardButton("➖ Ballarimdan qanchasini olib tashlash", callback_data="bozor_subtract"))
        kb_edit.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            f"✏️ *Ballarni tahrirlash*\n\n⭐ Joriy balingiz: *{balls} ball*",
            parse_mode="Markdown", reply_markup=kb_edit
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "bozor_reset_confirm":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        kb_conf = InlineKeyboardMarkup()
        kb_conf.row(
            cBtn("✅ Ha, 0 ga tushirish", "bozor_reset_do", "success"),
            InlineKeyboardButton("❌ Yo'q",               callback_data="menu_bozor")
        )
        sent = bot.send_message(
            uid,
            "⚠️ Haqiqatan ham barcha ballaringizni *0 ga* tushirmoqchimisiz?",
            parse_mode="Markdown", reply_markup=kb_conf
        )
        u["main_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata == "bozor_reset_do":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["points"] = 0
        save_user(uid, u)
        sent_ok = bot.send_message(uid, T(uid, "ok_points_reset"), parse_mode="Markdown")
        def del_reset_ok(chat_id, mid):
            time.sleep(2)
            try: bot.delete_message(chat_id, mid)
            except: pass
        threading.Thread(target=del_reset_ok, args=(uid, sent_ok.message_id), daemon=True).start()
        # Bozor menyusiga qaytish
        balls = 0
        kb_b  = InlineKeyboardMarkup()
        kb_b.add(InlineKeyboardButton("💸 Ballarni ayirboshlash",    callback_data="bozor_transfer"))
        kb_b.add(InlineKeyboardButton("🔴 Ballarimni 0 ga tushirish", callback_data="bozor_reset_confirm"))
        kb_b.add(InlineKeyboardButton("➖ Ballarimdan olib tashlash",  callback_data="bozor_subtract"))
        kb_b.add(cBtn(T(uid, "btn_home"),             "menu_main", "primary"))
        sent2 = bot.send_message(
            uid,
            f"🛒 *Bozor —* bu sizning ballaringiz bilan qilinadigan barcha ammalar joyi.\n\n*⭐ Sizning balingiz:* {balls} ball\n\n"
            "*💸 Ballarni ayirboshlash —* yaqin insoniga ball yuborish\n"
            "*🔴 Ballarimni 0 ga tushirish —* barcha ballarni nollash\n"
            "*➖ Ballarimdan olib tashlash —* ma'lum miqdorni ayirish",
            parse_mode="Markdown", reply_markup=kb_b
        )
        u2 = load_user(uid)
        u2["main_msg_id"] = sent2.message_id
        save_user(uid, u2)
        return

    if cdata == "bozor_subtract":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = "bozor_waiting_subtract"
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.row(
            cBtn("⬅️ Orqaga", "menu_bozor", "primary"),
            cBtn(T(uid, "btn_home"), "menu_main", "primary")
        )
        sent = bot.send_message(
            uid,
            f"➖ *Ballarni olib tashlash*\n\n⭐ Joriy balingiz: *{u.get('points', 0)} ball*\n\nQancha ball olib tashlansin?",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    if cdata.startswith("admin_reply_to_") and uid == ADMIN_ID:
        target_user_id = int(cdata[15:])
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except Exception: pass
        u["state"] = f"admin_waiting_reply_{target_user_id}"
        kb_cancel = InlineKeyboardMarkup()
        kb_cancel.add(cBtn("❌ Bekor qilish", "admin_cancel", "danger"))
        target_u  = load_user(target_user_id)
        sent_rp   = bot.send_message(
            uid,
            f"↩️ *{target_u.get('name','Foydalanuvchi')}* ga javob yozing:",
            parse_mode="Markdown",
            reply_markup=kb_cancel
        )
        u["reply_msg_id"] = sent_rp.message_id
        save_user(uid, u)
        return

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
        return

    if cdata.startswith("admin_confirm_ball_") and uid == ADMIN_ID:
        bot.answer_callback_query(call.id, "✅")
        def del_admin_ball_msg(msg_id):
            time.sleep(5)
            try: bot.delete_message(ADMIN_ID, msg_id)
            except: pass
        threading.Thread(target=del_admin_ball_msg, args=(call.message.message_id,), daemon=True).start()
        return

    if cdata == "noop":
        bot.answer_callback_query(call.id)
        return

    if cdata == "ack_delete_msg":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    # ── Vaqtsiz odat qo'shish ──
    if cdata == "habit_no_time":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u["temp_habit"]["time"] = "vaqtsiz"
        u.pop("temp_msg_id", None)
        save_user(uid, u)
        _save_new_habit(uid, u)
        return

    # ── Repeat odat: qo'shimcha vaqt qo'shish ──
    if cdata == "repeat_add_more":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        collected = u.get("temp_habit", {}).get("times_collected", [])
        u["state"] = "waiting_habit_time"
        save_user(uid, u)
        cancel_kb = InlineKeyboardMarkup()
        cancel_kb.add(cBtn(T(uid, "btn_cancel"), "cancel", "danger"))
        sent = bot.send_message(
            uid,
            f"⏰ *{len(collected)+1}-vaqtni* kiriting:\n_Masalan: 12:00_",
            parse_mode="Markdown", reply_markup=cancel_kb
        )
        u["temp_msg_id"] = sent.message_id
        save_user(uid, u)
        return

    # ── Repeat odat: yakunlash ──
    if cdata == "repeat_done":
        bot.answer_callback_query(call.id)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        u.pop("temp_msg_id", None)
        save_user(uid, u)
        _save_new_habit(uid, u)
        return

    if cdata.startswith("main_page_"):
        page = int(cdata[10:])
        bot.answer_callback_query(call.id)
        try:
            edit_message_colored(uid, call.message.message_id, build_main_text(uid), main_menu_dict(uid, page=page))
        except Exception:
            try:
                bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=main_menu(uid, page=page))
            except Exception:
                pass
        return

    if cdata.startswith("delete_"):
        habit_id   = cdata[7:]
        u          = load_user(uid)
        habits     = u.get("habits", [])
        habit_name = next((h["name"] for h in habits if h["id"] == habit_id), "")
        bot.answer_callback_query(call.id)
        if not habit_name:
            send_main_menu(uid)
            return
        kb_confirm = InlineKeyboardMarkup()
        kb_confirm.row(
            cBtn(T(uid, "btn_yes"), f"confirm_delete_{habit_id}", "success"),
            cBtn(T(uid, "btn_no"),  "cancel_delete", "danger")
        )
        try:
            bot.edit_message_text(
                T(uid, "confirm_delete", name=habit_name),
                uid, call.message.message_id,
                parse_mode="Markdown",
                reply_markup=kb_confirm
            )
        except Exception:
            bot.send_message(uid, T(uid, "confirm_delete", name=habit_name),
                             parse_mode="Markdown", reply_markup=kb_confirm)
        return

    if cdata.startswith("confirm_delete_"):
        habit_id   = cdata[15:]
        u          = load_user(uid)
        habits     = u.get("habits", [])
        habit_name = next((h["name"] for h in habits if h["id"] == habit_id), "")
        # Schedule dan o'chirish
        schedule.clear(f"{uid}_{habit_id}")
        u["habits"] = [h for h in habits if h["id"] != habit_id]
        save_user(uid, u)
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        sent_del = bot.send_message(uid, T(uid, "deleted", name=habit_name), parse_mode="Markdown")
        def delete_and_back(chat_id, message_id):
            time.sleep(3)
            try:
                bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            delete_habit_menu(chat_id)
        threading.Thread(target=delete_and_back, args=(uid, sent_del.message_id), daemon=True).start()
        return

    if cdata == "cancel_delete":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        delete_habit_menu(uid)
        return

    # --- toggle_ ---
    if cdata.startswith("toggle_"):
        habit_id = cdata[7:]
        today    = today_uz5()
        from datetime import timezone, timedelta
        tz_uz     = timezone(timedelta(hours=5))
        yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
        u        = load_user(uid)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                hab_type  = h.get("type", "simple")
                rep_count = h.get("repeat_count", 1)

                if hab_type == "repeat" and rep_count > 1:
                    # Takrorlanuvchi odat: done_today_count bilan ishlash
                    done_today_count = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done_today_count = 0
                    fully_done       = done_today_count >= rep_count

                    if fully_done:
                        # Bekor qilish: to'liq bajarilganidan qaytarish
                        h["done_today_count"] = 0
                        h["last_done"]  = None
                        h["streak"]     = max(0, h.get("streak", 0) - 1)
                        h["total_done"] = max(0, h.get("total_done", 0) - 1)
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        # done_log: boshqa odat bajarilmagan bo'lsa o'chirish
                        if not _still_done:
                            done_log = u.get("done_log", {})
                            done_log.pop(today, None)
                            u["done_log"] = done_log
                        # History yangilash (undo)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = False
                        day_data["done"] = done_count_now
                        day_data["total"] = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        save_user(uid, u)
                        schedule_habit(uid, h)
                        bot.answer_callback_query(call.id, f"↩️ 0/{rep_count}")
                    else:
                        # Bir bosish = progress +1, lekin ball YO'Q
                        done_today_count += 1
                        h["done_today_count"] = done_today_count
                        h["done_date"] = today
                        if done_today_count >= rep_count:
                            # To'liq bajarildi — faqat shu yerda ball beriladi
                            # BUG FIX: last_done yangilashdan OLDIN yesterday bilan solishtirish kerak
                            h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                            h["last_done"]  = today
                            h["total_done"] = h.get("total_done", 0) + 1
                            # Bonus multiplier (api_checkin bilan bir xil)
                            _base = 5
                            if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                                _base = 15
                            elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                                _base = 10
                            if u.get("xp_booster_days", 0) > 0:
                                _base = round(_base * 1.1)
                            u["points"] = u.get("points", 0) + _base
                            # Global streak: kuniga bir marta oshsin
                            if u.get("streak_last_date") != today:
                                u["streak"] = u.get("streak", 0) + 1
                                u["streak_last_date"] = today
                                if u["streak"] > u.get("best_streak", 0):
                                    u["best_streak"] = u["streak"]
                                    u["best_streak_date"] = today
                                threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                            # done_log: kunlik bajarilish tarixi
                            done_log = u.get("done_log", {})
                            done_log[today] = True
                            u["done_log"] = done_log
                            # history yangilash (statistika uchun)
                            history = u.get("history", {})
                            day_data = history.get(today, {})
                            done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                            hab_map = day_data.get("habits", {})
                            hab_map[habit_id] = True
                            day_data["done"]   = done_count_now
                            day_data["total"]  = len(u.get("habits", []))
                            day_data["habits"] = hab_map
                            history[today] = day_data
                            u["history"] = history
                            # XP booster kunini kamaytirish (kuniga bir marta)
                            if u.get("xp_booster_days", 0) > 0:
                                if u.get("xp_booster_last_day", "") != today:
                                    u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                                    u["xp_booster_last_day"] = today
                            unschedule_habit_today(uid, habit_id)
                            save_user(uid, u)
                            # Achievements tekshirish
                            try:
                                check_achievements_toplevel(uid, u)
                            except Exception as _ae:
                                print(f"[warn] check_achievements toggle_repeat: {_ae}")
                            bot.answer_callback_query(call.id)
                            streak_r = h.get("streak", 1)
                            if streak_r >= 30:   s_extra_r = f"\n🔥 Streak: {streak_r} kun 🏆"
                            elif streak_r >= 14: s_extra_r = f"\n🔥 Streak: {streak_r} kun 🌟"
                            elif streak_r >= 7:  s_extra_r = f"\n🔥 Streak: {streak_r} kun 🔥"
                            else:                s_extra_r = f"\n🔥 Streak: {streak_r} kun"
                            sent_msg = bot.send_message(
                                uid,
                                T(uid, "done_ok", name=h["name"]) + f" *+{_base} ⭐ ball*" + s_extra_r,
                                parse_mode="Markdown"
                            )
                        else:
                            save_user(uid, u)
                            bot.answer_callback_query(call.id, f"✅ {done_today_count}/{rep_count}")
                            sent_msg = bot.send_message(
                                uid,
                                f"✅ *{h['name']}* — *{done_today_count}/{rep_count}* bajarildi!",
                                parse_mode="Markdown"
                            )
                        def del_msg_rep(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg_rep, args=(uid, sent_msg.message_id), daemon=True).start()
                        # Barcha odat bajarildi?
                        all_done = all(
                            (hh.get("last_done") == today if hh.get("type","simple") != "repeat"
                             else hh.get("done_today_count",0) >= hh.get("repeat_count",1))
                            for hh in u.get("habits", [])
                        )
                        if all_done and done_today_count >= rep_count:
                            sent_c = bot.send_message(uid, T(uid, "all_done"))
                            def del_c_rep(chat_id, msg_id):
                                time.sleep(5)
                                try: bot.delete_message(chat_id, msg_id)
                                except: pass
                            threading.Thread(target=del_c_rep, args=(uid, sent_c.message_id), daemon=True).start()

                else:
                    # Oddiy odat
                    if h.get("last_done") == today:
                        # Bekor qilish
                        h["last_done"]  = None
                        h["streak"]     = max(0, h.get("streak", 0) - 1)
                        h["total_done"] = max(0, h.get("total_done", 0) - 1)
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _undo_base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _undo_base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _undo_base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _undo_base = round(_undo_base * 1.1)
                        u["points"] = max(0, u.get("points", 0) - _undo_base)
                        # Global streak: faqat bugun boshqa odat bajarilmagan bo'lsa kamaytir
                        _still_done = any(hh.get("last_done") == today for hh in u.get("habits", []) if hh["id"] != habit_id)
                        if not _still_done and u.get("streak_last_date") == today:
                            u["streak"] = max(0, u.get("streak", 0) - 1)
                            u["streak_last_date"] = ""
                        # done_log: boshqa odat bajarilmagan bo'lsa o'chirish
                        if not _still_done:
                            done_log = u.get("done_log", {})
                            done_log.pop(today, None)
                            u["done_log"] = done_log
                        # History yangilash (undo)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = False
                        day_data["done"] = done_count_now
                        day_data["total"] = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        save_user(uid, u)
                        schedule_habit(uid, h)
                        bot.answer_callback_query(call.id)
                        sent_msg = bot.send_message(uid, T(uid, "undone", name=h["name"]), parse_mode="Markdown")
                        def del_msg1(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg1, args=(uid, sent_msg.message_id), daemon=True).start()
                    else:
                        # Bajarildi
                        # BUG FIX: last_done yangilashdan OLDIN yesterday bilan solishtirish kerak
                        h["streak"]     = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                        h["last_done"]  = today
                        h["total_done"] = h.get("total_done", 0) + 1
                        # Bonus multiplier (api_checkin bilan bir xil)
                        _base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _base = round(_base * 1.1)
                        u["points"] = u.get("points", 0) + _base
                        # Global streak: kuniga bir marta oshsin
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                            threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                        # done_log: kunlik bajarilgan kun
                        done_log = u.get("done_log", {})
                        done_log[today] = True
                        u["done_log"] = done_log
                        # history yangilash (statistika uchun)
                        history = u.get("history", {})
                        day_data = history.get(today, {})
                        done_count_now = sum(1 for hh in u.get("habits", []) if hh.get("last_done") == today)
                        hab_map = day_data.get("habits", {})
                        hab_map[habit_id] = True
                        day_data["done"]   = done_count_now
                        day_data["total"]  = len(u.get("habits", []))
                        day_data["habits"] = hab_map
                        history[today] = day_data
                        u["history"] = history
                        # XP booster kunini kamaytirish (kuniga bir marta)
                        if u.get("xp_booster_days", 0) > 0:
                            if u.get("xp_booster_last_day", "") != today:
                                u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                                u["xp_booster_last_day"] = today
                        save_user(uid, u)
                        # Achievements tekshirish
                        try:
                            check_achievements_toplevel(uid, u)
                        except Exception as _ae:
                            print(f"[warn] check_achievements toggle: {_ae}")
                        unschedule_habit_today(uid, habit_id)
                        bot.answer_callback_query(call.id)
                        streak_s = h.get("streak", 1)
                        if streak_s >= 30:   s_extra_s = f"\n🔥 Streak: {streak_s} kun 🏆"
                        elif streak_s >= 14: s_extra_s = f"\n🔥 Streak: {streak_s} kun 🌟"
                        elif streak_s >= 7:  s_extra_s = f"\n🔥 Streak: {streak_s} kun 🔥"
                        else:                s_extra_s = f"\n🔥 Streak: {streak_s} kun"
                        sent_msg = bot.send_message(uid, T(uid, "done_ok", name=h["name"]) + f" *+{_base} ⭐ ball*" + s_extra_s, parse_mode="Markdown")
                        def del_msg2(chat_id, msg_id):
                            time.sleep(3)
                            try: bot.delete_message(chat_id, msg_id)
                            except: pass
                        threading.Thread(target=del_msg2, args=(uid, sent_msg.message_id), daemon=True).start()
                        # Barcha odat bajarildi?
                        all_done = all(
                            (hh.get("last_done") == today if hh.get("type","simple") != "repeat"
                             else hh.get("done_today_count",0) >= hh.get("repeat_count",1))
                            for hh in u.get("habits", [])
                        )
                        if all_done:
                            sent_c = bot.send_message(uid, T(uid, "all_done"))
                            def del_c(chat_id, msg_id):
                                time.sleep(5)
                                try: bot.delete_message(chat_id, msg_id)
                                except: pass
                            threading.Thread(target=del_c, args=(uid, sent_c.message_id), daemon=True).start()

                # Menyu yangilash
                main_msg_id = u.get("main_msg_id")
                if main_msg_id:
                    try:
                        edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                    except Exception:
                        pass
                return

        # toggle_ - habit topilmadi (o'chirilgan bo'lishi mumkin)
        bot.answer_callback_query(call.id)
        send_main_menu(uid)

    # --- done_ (bildirishnomadan) ---
    if cdata.startswith("skip_"):
        habit_id = cdata[5:]
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(uid, call.message.message_id)
        except: pass
        return

    if cdata.startswith("done_"):
        habit_id = cdata[5:]
        today    = today_uz5()
        from datetime import timezone, timedelta
        tz_uz     = timezone(timedelta(hours=5))
        yesterday = (datetime.now(tz_uz) - timedelta(days=1)).strftime("%Y-%m-%d")
        u        = load_user(uid)
        for h in u.get("habits", []):
            if h["id"] == habit_id:
                hab_type  = h.get("type", "simple")
                rep_count = h.get("repeat_count", 1)

                if hab_type == "repeat" and rep_count > 1:
                    # Repeat odat: progress +1
                    done_today_count = h.get("done_today_count", 0)
                    if h.get("done_date") != today:
                        done_today_count = 0
                    if h.get("last_done") == today:
                        bot.answer_callback_query(call.id, T(uid, "done_today"))
                        return
                    done_today_count += 1
                    h["done_today_count"] = done_today_count
                    h["done_date"] = today
                    if done_today_count >= rep_count:
                        # To'liq bajarildi
                        h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                        h["last_done"] = today
                        h["total_done"] = h.get("total_done", 0) + 1
                        if u.get("streak_last_date") != today:
                            u["streak"] = u.get("streak", 0) + 1
                            u["streak_last_date"] = today
                            if u["streak"] > u.get("best_streak", 0):
                                u["best_streak"] = u["streak"]
                                u["best_streak_date"] = today
                            threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                        _base = 5
                        if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                            _base = 15
                        elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                            _base = 10
                        if u.get("xp_booster_days", 0) > 0:
                            _base = round(_base * 1.1)
                        u["points"] = u.get("points", 0) + _base
                        done_log = u.get("done_log", {})
                        done_log[today] = True
                        u["done_log"] = done_log
                        save_user(uid, u)
                        try:
                            check_achievements_toplevel(uid, u)
                        except Exception: pass
                        unschedule_habit_today(uid, habit_id)
                        bot.answer_callback_query(call.id, "✅")
                        try:
                            bot.edit_message_text(
                                f"{T(uid, 'done_ok', name=h['name'])} *+{_base} ⭐ ball*\n\n🔥 Streak: {h['streak']} kun",
                                uid, call.message.message_id, parse_mode="Markdown"
                            )
                        except Exception: pass
                    else:
                        # Hali to'liq emas — progress ko'rsatish
                        save_user(uid, u)
                        bot.answer_callback_query(call.id, f"✅ {done_today_count}/{rep_count}")
                        try:
                            bot.edit_message_text(
                                f"✅ *{h['name']}* — *{done_today_count}/{rep_count}* bajarildi!",
                                uid, call.message.message_id, parse_mode="Markdown"
                            )
                        except Exception: pass
                    def del_remind_r(chat_id, message_id):
                        time.sleep(3)
                        try: bot.delete_message(chat_id, message_id)
                        except: pass
                    threading.Thread(target=del_remind_r, args=(uid, call.message.message_id), daemon=True).start()
                    main_msg_id = u.get("main_msg_id")
                    if main_msg_id:
                        try: edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                        except Exception: pass
                    return

                # Oddiy (simple) odat
                if h.get("last_done") == today:
                    bot.answer_callback_query(call.id, T(uid, "done_today"))
                    return
                h["streak"] = h.get("streak", 0) + 1 if h.get("last_done") == yesterday else 1
                h["last_done"]  = today
                h["total_done"] = h.get("total_done", 0) + 1
                # Global streak: kuniga bir marta oshsin
                if u.get("streak_last_date") != today:
                    u["streak"] = u.get("streak", 0) + 1
                    u["streak_last_date"] = today
                    if u["streak"] > u.get("best_streak", 0):
                        u["best_streak"] = u["streak"]
                        u["best_streak_date"] = today
                    threading.Thread(target=_check_streak_milestone, args=(uid, u["streak"]), daemon=True).start()
                # Bonus multiplier hisoblash (WebApp api_checkin bilan bir xil)
                _base = 5
                if u.get("bonus_3x_active") and u.get("bonus_3x_date") == today:
                    _base = 15
                elif u.get("bonus_2x_active") and u.get("bonus_2x_date") == today:
                    _base = 10
                if u.get("xp_booster_days", 0) > 0:
                    _base = round(_base * 1.1)
                u["points"]     = u.get("points", 0) + _base
                # done_log: kunlik bajarilgan kunlarni saqlash
                done_log = u.get("done_log", {})
                done_log[today] = True
                u["done_log"] = done_log
                # History yangilash (statistika/heatmap uchun)
                habits_list = u.get("habits", [])
                history = u.get("history", {})
                day_data = history.get(today, {})
                done_count_now = sum(1 for hh in habits_list if hh.get("last_done") == today)
                total_now = len(habits_list)
                hab_map = day_data.get("habits", {})
                hab_map[habit_id] = True
                day_data["done"]   = done_count_now
                day_data["total"]  = total_now
                day_data["habits"] = hab_map
                history[today] = day_data
                u["history"] = history
                # XP booster kunini kamaytirish (kuniga bir marta)
                if u.get("xp_booster_days", 0) > 0:
                    last_boost = u.get("xp_booster_last_day", "")
                    if last_boost != today:
                        u["xp_booster_days"] = max(0, u["xp_booster_days"] - 1)
                        u["xp_booster_last_day"] = today
                save_user(uid, u)
                # Achievements tekshirish (top-level funksiya orqali)
                try:
                    check_achievements_toplevel(uid, u)
                except Exception as _ae:
                    print(f"[warn] check_achievements: {_ae}")
                unschedule_habit_today(uid, habit_id)
                streak = h["streak"]
                if streak >= 30:   msg_extra = f"🔥 Streak: {streak} kun 🏆"
                elif streak >= 14: msg_extra = f"🔥 Streak: {streak} kun 🌟"
                elif streak >= 7:  msg_extra = f"🔥 Streak: {streak} kun 🔥"
                else:              msg_extra = f"🔥 Streak: {streak} kun"
                bot.answer_callback_query(call.id, "✅")
                try:
                    bot.edit_message_text(
                        f"{T(uid, 'done_ok', name=h['name'])} *+{_base} ⭐ ball*\n\n{msg_extra}",
                        uid, call.message.message_id, parse_mode="Markdown"
                    )
                except Exception:
                    pass
                def del_remind(chat_id, message_id):
                    time.sleep(3)
                    try: bot.delete_message(chat_id, message_id)
                    except: pass
                threading.Thread(target=del_remind, args=(uid, call.message.message_id), daemon=True).start()
                main_msg_id = u.get("main_msg_id")
                if main_msg_id:
                    try:
                        edit_message_colored(uid, main_msg_id, build_main_text(uid), main_menu_dict(uid))
                    except Exception:
                        pass
                return
        # Odat topilmadi
        bot.answer_callback_query(call.id)
        return

    # ── Fallback: agar hech bir handler mos kelmasa ──
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass



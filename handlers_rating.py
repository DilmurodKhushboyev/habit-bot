#!/usr/bin/env python3
"""
Reyting rasm generatsiyasi va ko'rsatish
"""

import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import load_user, load_all_users
from helpers import T, get_lang, get_rank
from bot_setup import bot, cBtn, send_message_colored


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



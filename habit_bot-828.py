#!/usr/bin/env python3
"""
Odatlar Shakllantirish Boti
============================
O'rnatish:
    pip install pyTelegramBotAPI schedule pymongo flask Pillow

Ishga tushurish:
    python habit_bot.py
"""

import os
import threading
import logging

# ── Asosiy modullarni yuklash ──
from config import BOT_TOKEN, ADMIN_ID
from database import *      # noqa — DB funksiyalari hamma joyda kerak
from texts import LANGS
from motivation import MOTIVATSIYA
from helpers import *        # noqa — T, get_lang, today_uz5, ...
from bot_setup import bot
from menus import *          # noqa — menu2, subscription, admin menus

# ── Handlerlarni ro'yxatdan o'tkazish (import tartib muhim!) ──
import handlers_commands      # noqa — /start, /admin_panel, contact
import handlers_onboarding    # noqa — onboarding funksiyalari
import handlers_rating        # noqa — reyting rasm generatsiyasi
import handlers_stats         # noqa — statistika, hisobotlar
import handlers_callbacks     # noqa — callback dispatcher
import handlers_text          # noqa — matn handleri, to'lov, inline
import groups                 # noqa — guruh funksiyalari
import achievements           # noqa — yutuqlar

# ── Scheduler ──
from scheduler import scheduler_loop, load_all_schedules

# ── Flask API ──
from flask_api import run_api, api_app


# ============================================================
#  ISHGA TUSHURISH
# ============================================================
if __name__ == "__main__":
    print("=" * 45)
    print("  Odatlar Shakllantirish Boti ishga tushdi!")
    print("=" * 45)
    threading.Thread(target=scheduler_loop, daemon=True).start()
    if run_api:
        threading.Thread(target=run_api, daemon=True).start()
    print("Bot tayyor! /setup_webhook endpointini bir marta oching.")
    # Railway da webhook ishlaydi — polling shart emas
    # Lokal test uchun polling
    WEBAPP_URL_CHECK = os.environ.get("WEBAPP_URL", "")
    if not WEBAPP_URL_CHECK:
        bot.infinity_polling(timeout=60, long_polling_timeout=30,
                             logger_level=logging.DEBUG,
                             allowed_updates=["message", "callback_query", "pre_checkout_query"],
                             restart_on_change=False)
    else:
        # Webhook rejimi: Flask thread asosiy thread sifatida ishlaydi
        import time as _main_sleep
        while True:
            _main_sleep.sleep(60)

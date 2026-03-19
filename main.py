#!/usr/bin/env python3
"""
main.py
=======
Botni ishga tushirish fayli.
Faqat shu faylni Railway'da ishga tushiring: python main.py

Barcha modullarni import qiladi va botni startlaydi.
"""

import threading
import logging
import os

# Barcha handlerlarni import qilish (ular bot'ga avtomatik ro'yxatdan o'tadi)
from keyboards import bot
import handlers_start      # /start, contact, admin
import handlers_habits     # onboarding, reyting, callback_handler
from handlers_groups import scheduler_loop
import handlers_groups     # scheduler, matn handler, guruhlar

# Flask API serveri (ixtiyoriy)
try:
    from api_server import run_api
except ImportError:
    run_api = None
    print("[API] Flask yo'q — Web App API ishlamaydi.")

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
        import logging
        bot.infinity_polling(timeout=60, long_polling_timeout=30, logger_level=logging.DEBUG, allowed_updates=["message", "callback_query", "pre_checkout_query"], restart_on_change=False)
    else:
        # Webhook rejimi: Flask thread asosiy thread sifatida ishlaydi
        import time as _main_sleep
        while True:
            _main_sleep.sleep(60)

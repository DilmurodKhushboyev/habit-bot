#!/usr/bin/env python3
"""
Flask Web App API — app yaratish va route larni ro'yxatdan o'tkazish
"""

import os

run_api = None
api_app = None

try:
    from flask import Flask, send_from_directory

    api_app = Flask(__name__, static_folder='static', static_url_path='')

    @api_app.route('/')
    def serve_index():
        return send_from_directory(api_app.static_folder, 'index.html')

    # Route larni alohida modullarda ro'yxatdan o'tkazish
    from flask_helpers import register_helpers
    from flask_routes_core import register_core_routes
    from flask_routes_data import register_data_routes
    from flask_routes_extra import register_extra_routes
    from flask_routes_reminders import register_reminders_routes

    register_helpers(api_app)
    register_core_routes(api_app)
    register_data_routes(api_app)
    register_extra_routes(api_app)
    register_reminders_routes(api_app)

    def run_api():
        port = int(os.environ.get("PORT", 8080))
        api_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    print("[API] Flask server tayyor (port 8080)")

except ImportError:
    print("[API] Flask yo'q — Web App API ishlamaydi. 'pip install flask flask-cors' qiling.")
    run_api = None

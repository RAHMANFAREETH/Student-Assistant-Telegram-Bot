"""Optional V12.1 Study & Mind Arcade. Separate files; no database or AI calls.

Enabling this public Arcade does not grant access to Telegram-identity-backed tasks.
The existing V12.0 access controls remain the only source of truth for private APIs.
"""
from __future__ import annotations
import os
from pathlib import Path
from flask import abort, jsonify, send_file

_ASSETS = Path(__file__).resolve().parent
_TRUE = {'1', 'true', 'yes', 'on'}
_STATIC = {
    '/app/arcade/assets/style.css': ('super_miniapp_v121.css', 'text/css; charset=utf-8'),
    '/app/arcade/assets/entry.css': ('super_miniapp_v121_entry.css', 'text/css; charset=utf-8'),
    '/app/arcade/assets/app.mjs': ('super_miniapp_v121_app.mjs', 'application/javascript; charset=utf-8'),
    '/app/arcade/assets/super_miniapp_v121_data.mjs': ('super_miniapp_v121_data.mjs', 'application/javascript; charset=utf-8'),
    '/app/arcade/assets/super_miniapp_v121_engine.mjs': ('super_miniapp_v121_engine.mjs', 'application/javascript; charset=utf-8'),
    '/app/arcade/assets/super_miniapp_v121_study.mjs': ('super_miniapp_v121_study.mjs', 'application/javascript; charset=utf-8'),
    '/app/arcade/assets/super_miniapp_v121_mind.mjs': ('super_miniapp_v121_mind.mjs', 'application/javascript; charset=utf-8'),
    '/app/arcade/assets/super_miniapp_v121_helpers.mjs': ('super_miniapp_v121_helpers.mjs', 'application/javascript; charset=utf-8'),
}


def enabled_v121():
    """Public device-only games; master Mini App switch remains mandatory."""
    from super_miniapp_v120 import enabled as master_enabled
    return master_enabled() and os.getenv('SUPER_ARCADE_V121_ENABLED','false').lower().strip() in _TRUE


def register_v121_arcade(app):
    """Called by register_super_miniapp, once, without touching /library.

    Register only with the V12.1 launch flag set during application startup.
    This keeps the V12.0.2 endpoint set unchanged when the Arcade is off.
    Changing the launch flag requires a Render process restart.
    """
    if os.getenv('SUPER_ARCADE_V121_ENABLED', 'false').lower().strip() not in _TRUE:
        return
    if 'v121_arcade_home' in app.view_functions:
        return

    @app.get('/app/arcade/meta', endpoint='v121_arcade_meta')
    def meta():
        from super_miniapp_v120 import enabled as master_enabled
        if not master_enabled():
            abort(404)
        return jsonify({'enabled': enabled_v121(), 'activities': 32, 'version': '12.1'})

    @app.get('/app/assets/arcade-entry.mjs', endpoint='v121_arcade_entry')
    def entry():
        from super_miniapp_v120 import enabled as master_enabled
        if not master_enabled():
            abort(404)
        return send_file(_ASSETS / 'super_miniapp_v121_entry.mjs', mimetype='application/javascript; charset=utf-8')

    @app.get('/app/arcade', endpoint='v121_arcade_home')
    def home():
        if not enabled_v121():
            abort(404)
        return send_file(_ASSETS / 'super_miniapp_v121.html', mimetype='text/html; charset=utf-8')

    for index, (path, (filename, mime)) in enumerate(_STATIC.items()):
        def asset(filename=filename, mime=mime):
            if not enabled_v121():
                abort(404)
            return send_file(_ASSETS / filename, mimetype=mime)
        app.add_url_rule(path, endpoint=f'v121_arcade_asset_{index}', view_func=asset, methods=['GET'])

"""V12.2 opt-in Font & Writing Studio: static GET-only browser tools.

No uploads, no Supabase changes, no Telegram identity override. Existing /app
session endpoint validates access in the client before showing the studio.
"""
from __future__ import annotations
import os
from pathlib import Path
from flask import abort, jsonify, send_file

ASSETS = Path(__file__).resolve().parent
TRUE = {'1','true','yes','on'}
STATIC = {
 '/app/assets/fontstudio.css': ('super_miniapp_v122_fonts.css','text/css; charset=utf-8'),
 '/app/assets/fontstudio.js': ('super_miniapp_v122_fonts.js','application/javascript; charset=utf-8'),
 '/app/assets/fontstudio.mjs': ('super_miniapp_v122_fonts.mjs','application/javascript; charset=utf-8'),
 '/app/assets/fontstudio-entry.mjs': ('super_miniapp_v122_entry.mjs','application/javascript; charset=utf-8'),
 '/app/assets/fontstudio-entry.css': ('super_miniapp_v122_entry.css','text/css; charset=utf-8'),
}

def enabled_v122():
 from super_miniapp_v120 import enabled
 return enabled() and os.getenv('SUPER_FONT_STUDIO_V122_ENABLED','false').strip().lower() in TRUE

def register_v122_fontstudio(app):
 """Register only when explicitly enabled at server startup."""
 if os.getenv('SUPER_FONT_STUDIO_V122_ENABLED','false').strip().lower() not in TRUE:
  return
 if 'v122_fontstudio_home' in app.view_functions:
  return
 @app.get('/app/fontstudio/meta',endpoint='v122_fontstudio_meta')
 def meta():
  if not enabled_v122():abort(404)
  return jsonify({'enabled':True,'tools':4,'version':'12.2'})
 @app.get('/app/fonts',endpoint='v122_fontstudio_home')
 def home():
  if not enabled_v122():abort(404)
  return send_file(ASSETS/'super_miniapp_v122_fonts.html',mimetype='text/html; charset=utf-8')
 for i,(url,(filename,mime)) in enumerate(STATIC.items()):
  def asset(filename=filename,mime=mime):
   if not enabled_v122():abort(404)
   return send_file(ASSETS/filename,mimetype=mime)
  app.add_url_rule(url,endpoint=f'v122_fontstudio_asset_{i}',view_func=asset,methods=['GET'])

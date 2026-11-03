"""Guarded V12 patch: public browser utilities, signed private data, optional manual-age gate.

Does not change other bot features. Does not disable Telegram HMAC validation.
"""
from __future__ import annotations
import argparse
import difflib
from datetime import datetime
from pathlib import Path
import shutil
import sys

MARK_BACKEND = '# >>> V12 PUBLIC UTILITY ACCESS >>>'
MARK_FRONTEND = '// >>> V12 PUBLIC UTILITY ACCESS >>>'
MARK_LAUNCH = '# >>> V12 PUBLIC LAUNCH MODE >>>'


def replace_one(s, old, new, name):
    count = s.count(old)
    if count != 1:
        raise ValueError(f'{name}: expected one anchor, got {count}; refusing unsafe patch')
    return s.replace(old, new, 1)


def backend(s):
    if MARK_BACKEND in s:
        return s
    s = replace_one(s, '_TRUE = {"1", "true", "yes", "on"}\n', '''_TRUE = {"1", "true", "yes", "on"}

''' + MARK_BACKEND + '''
def public_tools_enabled():
    """Public, browser-only calculators; never a replacement for signed identity."""
    return os.getenv('SUPER_MINIAPP_V120_PUBLIC_TOOLS', 'false').strip().lower() in _TRUE


def adult_verification_required():
    """Opt out ONLY for the V12 benign Mini App, not for other bot/AI features."""
    return os.getenv('SUPER_MINIAPP_V120_REQUIRE_ADULT', 'true').strip().lower() not in ('0', 'false', 'no', 'off')


def _guest_session():
    return jsonify({'ok': True, 'guest': True, 'user_id': None,
                    'private_features': False, 'version': '12.0-development-preview'})

# <<< V12 PUBLIC UTILITY ACCESS <<<
''', 'super_miniapp_v120.py flags')
    s = replace_one(s, '''    from study_access_v9 import is_verified_adult
    if not is_verified_adult(uid):
        raise PermissionError("Verified adult access required.")''', '''    if adult_verification_required():
        from study_access_v9 import is_verified_adult
        if not is_verified_adult(uid):
            raise PermissionError("Verified adult access required.")''', 'super_miniapp_v120.py adult check')
    head = '    @app.get("/app/api/session", endpoint="v120_super_session")\n'
    tail = '    @app.route("/app/api/tasks", methods=["GET", "POST"], endpoint="v120_super_tasks")\n'
    if s.count(head)!=1 or s.count(tail)!=1:
        raise ValueError('super_miniapp_v120.py: missing session route boundary')
    before, after = s.split(head, 1)
    _, after = after.split(tail, 1)
    block = '''    @app.get("/app/api/session", endpoint="v120_super_session")
    def session():
        if not enabled():
            abort(404)
        raw = request.headers.get('X-Telegram-Init-Data', '')
        if public_tools_enabled() and not raw:
            return _guest_session()
        try:
            uid = verify_super_session(raw)
        except PermissionError:
            # Anonymous utilities are safe; private endpoints still check HMAC.
            if public_tools_enabled():
                return _guest_session()
            return jsonify({'error': 'Verified 18+ access is required.'}), 403
        # >>> V12.0 SESSION FAILURE DIAGNOSTIC >>>
        except (ValueError, TypeError) as exc:
            # Do not log initData, user ID or the bot token.
            detail = str(exc).lower()
            if 'expired' in detail:
                reason = 'expired_telegram_login'
            elif 'signature' in detail:
                reason = 'invalid_telegram_signature'
            else:
                reason = 'invalid_telegram_login'
            app.logger.warning('V12 login denied: %s (no sensitive data logged)', reason)
            if public_tools_enabled():
                return _guest_session()
            return jsonify({'error':'Open the app from Telegram and sign in again.', 'code': reason}), 401
        # <<< V12.0 SESSION FAILURE DIAGNOSTIC <<<
        return jsonify({'ok': True, 'user_id': uid,
                        'private_features': True, 'version': '12.0-development-preview'})

'''
    return before + block + tail + after


def launcher(s):
    if MARK_LAUNCH in s:
        return s
    old = '''    try:
        from study_access_v9 import is_verified_adult
        return is_verified_adult(uid) is True
    except Exception:
        return False'''
    new = '''    '''+MARK_LAUNCH+'''
    # Public V12 launcher permits calculators for all users. Other bot/AI gates
    # are untouched. Private V12 endpoints independently validate Telegram HMAC.
    if _on('SUPER_MINIAPP_V120_PUBLIC_TOOLS'):
        return True
    if os.getenv('SUPER_MINIAPP_V120_REQUIRE_ADULT', 'true').strip().lower() in ('false', '0', 'no', 'off'):
        return True
    # <<< V12 PUBLIC LAUNCH MODE <<<
    try:
        from study_access_v9 import is_verified_adult
        return is_verified_adult(uid) is True
    except Exception:
        return False'''
    return replace_one(s,old,new,'super_miniapp_v120_launch.py gate')


def frontend(s):
    if MARK_FRONTEND in s:
        return s
    s = replace_one(s, "const storePrefix=()=>`studentassistant_v120_${state.user}_`;", '''// >>> V12 PUBLIC UTILITY ACCESS >>>
// Guest preferences and quick tasks live in sessionStorage, never in shared
// cross-account localStorage. Private data never comes from unsigned user IDs.
const storage=()=>state.user===null?sessionStorage:localStorage;
const storePrefix=()=>`studentassistant_v120_${state.user===null?'guest_session':state.user}_`;
// <<< V12 PUBLIC UTILITY ACCESS <<<''', 'super_miniapp_v120.js storage key')
    s = replace_one(s, 'JSON.parse(localStorage.getItem(storePrefix()+key))', 'JSON.parse(storage().getItem(storePrefix()+key))', 'super_miniapp_v120.js read storage')
    s = replace_one(s, 'localStorage.setItem(storePrefix()+key,JSON.stringify(val))', 'storage().setItem(storePrefix()+key,JSON.stringify(val))', 'super_miniapp_v120.js write storage')
    s = replace_one(s, 'if(state.plannerLoading||(!force&&state.plannerLoaded))return;if(!tg?.initData)return;', 'if(state.plannerLoading||(!force&&state.plannerLoaded))return;if(state.user===null||!tg?.initData)return;', 'super_miniapp_v120.js planner gate')
    old = "$('theme-toggle').onclick=()=>{state.manuallySetTheme=true;applyTheme(document.documentElement.dataset.theme==='light'?'dark':'light');};switchTab('home');loadSyncedTasks();}"
    new = "$('theme-toggle').onclick=()=>{state.manuallySetTheme=true;applyTheme(document.documentElement.dataset.theme==='light'?'dark':'light');};switchTab('home');if(state.user===null){state.tasksMode='local';state.tasks=getTasks();state.plannerError='unavailable';renderTasks();renderPlannerOverview();status('Public tools are available. Private sync needs a valid Telegram session. Guest tasks last for this browser session.');}else{loadSyncedTasks();}}"
    s = replace_one(s,old,new,'super_miniapp_v120.js start')
    old = '''async function boot(){if(tg){tg.ready();tg.expand();applyTheme(tg.colorScheme);tg.onEvent?.('themeChanged',()=>{if(!state.manuallySetTheme)applyTheme(tg.colorScheme);});}
 if(!tg?.initData){$('auth-wall').querySelector('h2').textContent=localUI('openFromTelegram',state.lang);$('auth-wall').querySelector('p').textContent=localUI('sessionRequired',state.lang);return;}
 try{const response=await fetch('/app/api/session',{headers:{'X-Telegram-Init-Data':tg.initData},cache:'no-store',credentials:'omit'});const data=await response.json();if(!response.ok||data.ok!==true||!Number.isSafeInteger(data.user_id))throw Error(data.error||'Access denied.');state.user=data.user_id;start();}
 catch(e){$('auth-wall').querySelector('h2').textContent=localUI('authUnavailable',state.lang);$('auth-wall').querySelector('p').textContent=e.message||localUI('authRetry',state.lang);}}
boot();'''
    new = '''async function boot(){if(tg){tg.ready();tg.expand();applyTheme(tg.colorScheme);tg.onEvent?.('themeChanged',()=>{if(!state.manuallySetTheme)applyTheme(tg.colorScheme);});}
 try{
  const headers=tg?.initData?{'X-Telegram-Init-Data':tg.initData}:{};
  const response=await fetch('/app/api/session',{headers,cache:'no-store',credentials:'omit'});
  const data=await response.json();
  if(!response.ok||data.ok!==true)throw Error(data.error||'Access denied.');
  if(data.guest===true && data.private_features===false){state.user=null;start();return;}
  if(!Number.isSafeInteger(data.user_id)||data.user_id<=0||data.private_features!==true)throw Error('Invalid session.');
  state.user=data.user_id;start();
 }catch(e){$('auth-wall').querySelector('h2').textContent=localUI('authUnavailable',state.lang);$('auth-wall').querySelector('p').textContent=e.message||localUI('authRetry',state.lang);}}
boot();'''
    return replace_one(s,old,new,'super_miniapp_v120.js boot')

PATCHES={'super_miniapp_v120.py':backend,'super_miniapp_v120_launch.py':launcher,'super_miniapp_v120.js':frontend}


def process(root:Path, apply:bool):
    edits={}
    for name,fn in PATCHES.items():
        p=root/name
        if not p.is_file() or p.is_symlink():raise ValueError(f'Missing or unsafe file: {name}')
        old=p.read_text(encoding='utf-8');new=fn(old)
        if name.endswith('.py'):compile(new,name,'exec')
        edits[name]=(old,new)
    for name,(old,new) in edits.items():
        print(('UPDATE ' if new!=old else 'UNCHANGED ')+name)
        if old!=new:
            diff=list(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile=name+' before',tofile=name+' after',lineterm=''))
            print('\n'.join(diff[:130]));
            if len(diff)>130:print('... inspect full source before commit')
    if not apply:
        print('CHECK OK (no files written)');return
    changed=[(name,old,new) for name,(old,new) in edits.items() if old!=new]
    if not changed:
        print('NO CHANGES (already applied)');return
    backup=root/('V120_PUBLIC_ACCESS_BACKUP_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(mode=0o700)
    for name,_,_ in changed:shutil.copy2(root/name,backup/name)
    done=[]
    try:
        for name,_,new in changed:
            temp=root/(name+'.v120-public-tmp')
            temp.write_text(new,encoding='utf-8',newline='')
            temp.replace(root/name)
            done.append(name)
    except Exception:
        for name in done:shutil.copy2(backup/name,root/name)
        raise
    print('APPLIED. Backup:',backup)
    print('Public mode requires SUPER_MINIAPP_V120_PUBLIC_TOOLS=true.')
    print('Signed Telegram identity is still required for saved tasks and planner.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check',action='store_true');g.add_argument('--apply',action='store_true')
    a=p.parse_args()
    try:process(Path(__file__).resolve().parent,a.apply)
    except (OSError,ValueError,SyntaxError) as exc:
        print('ABORT:',exc,file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())

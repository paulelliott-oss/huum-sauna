from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import asyncio
import os

# Simple cookie-based session (stored client-side, encrypted would be better for prod)
def get_session(cookies):
    """Parse session from cookies"""
    session = {}
    if cookies:
        for cookie in cookies.split(';'):
            if '=' in cookie:
                key, val = cookie.strip().split('=', 1)
                if key in ('huum_user', 'huum_pass'):
                    session[key] = val
    return session

def set_session_cookies(username, password):
    """Create session cookies"""
    return [
        f"huum_user={username}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400",
        f"huum_pass={password}; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400"
    ]

def clear_session_cookies():
    """Clear session cookies"""
    return [
        "huum_user=; Path=/; HttpOnly; Max-Age=0",
        "huum_pass=; Path=/; HttpOnly; Max-Age=0"
    ]

async def get_sauna_status(username, password):
    from huum.huum import Huum
    huum = Huum(username=username, password=password)
    await huum.open_session()
    try:
        return await huum.status()
    finally:
        await huum.close_session()

async def turn_on_sauna(username, password, temperature):
    from huum.huum import Huum
    huum = Huum(username=username, password=password)
    await huum.open_session()
    try:
        await huum.turn_on(temperature=temperature)
    finally:
        await huum.close_session()

async def turn_off_sauna(username, password):
    from huum.huum import Huum
    huum = Huum(username=username, password=password)
    await huum.open_session()
    try:
        await huum.turn_off()
    finally:
        await huum.close_session()

def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

def render_page(logged_in=False, status=None, error=None, success=None):
    status_html = ""
    controls_html = ""
    target_temp = 80

    if logged_in and status:
        target_temp = status.targetTemperature or 80
        if status.statusCode in (230, 231):
            badge = '<span style="background:#fb923c;color:#7c2d12;padding:10px 20px;border-radius:25px;font-weight:600">🔥 HEATING</span>'
        elif status.statusCode == 232:
            badge = '<span style="background:#4ade80;color:#166534;padding:10px 20px;border-radius:25px;font-weight:600">✓ READY</span>'
        else:
            badge = '<span style="background:#6b7280;color:#fff;padding:10px 20px;border-radius:25px;font-weight:600">○ OFF</span>'

        door_class = "color:#fbbf24" if status.door else "color:#4ade80"
        door_text = "OPEN" if status.door else "CLOSED"

        status_html = f'''
        <div class="card">
            <div style="text-align:center;margin-bottom:15px">{badge}</div>
            <div style="text-align:center;margin:30px 0">
                <span style="font-size:80px;font-weight:200">{status.temperature}<span style="font-size:32px;vertical-align:super">°C</span></span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-top:20px">
                <div class="info-box"><div class="info-label">Humidity</div><div style="font-size:20px;font-weight:600">{status.humidity}%</div></div>
                <div class="info-box"><div class="info-label">Door</div><div style="font-size:20px;font-weight:600;{door_class}">{door_text}</div></div>
            </div>
        </div>
        '''

        if status.door:
            status_html += '<div class="alert alert-warning">⚠️ Close the door before turning on</div>'

        if status.statusCode in (230, 231, 232):
            btn = '<button type="submit" name="action" value="off" class="btn btn-off">Turn Off</button>'
        else:
            disabled = 'disabled' if status.door else ''
            btn = f'<button type="submit" name="action" value="on" class="btn btn-on" {disabled}>Turn On Sauna</button>'

        controls_html = f'''
        <div class="card">
            <form method="POST" action="/control">
                <div style="margin-bottom:25px">
                    <label style="display:block;margin-bottom:12px;color:rgba(255,255,255,0.7)">Set Temperature</label>
                    <div style="display:flex;align-items:center;gap:12px">
                        <span style="color:rgba(255,255,255,0.5)">40°</span>
                        <input type="range" name="temperature" min="40" max="110" value="{target_temp}" class="temp-slider" id="tempSlider">
                        <span style="color:rgba(255,255,255,0.5)">110°</span>
                    </div>
                    <div style="text-align:center;margin-top:15px"><span style="font-size:28px;font-weight:700;color:#f97316" id="tempValue">{target_temp}°C</span></div>
                </div>
                {btn}
            </form>
        </div>
        <a href="/logout" style="display:block;text-align:center;margin-top:25px;color:rgba(255,255,255,0.4);text-decoration:none">Disconnect</a>
        '''
    elif logged_in:
        controls_html = '<div class="card"><p style="text-align:center">Loading status...</p></div><a href="/logout" style="display:block;text-align:center;margin-top:25px;color:rgba(255,255,255,0.4);text-decoration:none">Disconnect</a>'
    else:
        controls_html = '''
        <div class="card">
            <form method="POST" action="/login">
                <input type="email" name="username" placeholder="HUUM Email" required style="width:100%;padding:16px;border:1px solid rgba(255,255,255,0.2);border-radius:12px;background:rgba(255,255,255,0.1);color:white;font-size:17px;margin-bottom:14px">
                <input type="password" name="password" placeholder="HUUM Password" required style="width:100%;padding:16px;border:1px solid rgba(255,255,255,0.2);border-radius:12px;background:rgba(255,255,255,0.1);color:white;font-size:17px;margin-bottom:14px">
                <button type="submit" class="btn btn-on">Connect</button>
            </form>
        </div>
        <p style="text-align:center;color:rgba(255,255,255,0.3);font-size:12px;margin-top:20px">Use your HUUM app login</p>
        '''

    alert_html = ""
    if error:
        alert_html = f'<div class="alert alert-error">{error}</div>'
    if success:
        alert_html = f'<div class="alert alert-success">{success}</div>'

    return f'''<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<title>Sauna Control</title>
<meta name="apple-mobile-web-app-capable" content="yes">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#1a1a2e,#16213e);min-height:100vh;color:#fff;padding:20px}}
.card{{background:rgba(255,255,255,0.1);border-radius:20px;padding:30px;backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.1);margin-bottom:20px}}
.info-box{{background:rgba(255,255,255,0.05);border-radius:12px;padding:15px;text-align:center}}
.info-label{{color:rgba(255,255,255,0.5);font-size:12px;text-transform:uppercase;margin-bottom:5px}}
.btn{{padding:18px 24px;border:none;border-radius:14px;font-size:18px;font-weight:600;cursor:pointer;width:100%}}
.btn-on{{background:linear-gradient(135deg,#f97316,#ea580c);color:white}}
.btn-off{{background:rgba(255,255,255,0.15);color:white;border:1px solid rgba(255,255,255,0.2)}}
.btn:disabled{{opacity:0.5;cursor:not-allowed}}
.alert{{padding:14px 18px;border-radius:12px;margin-bottom:20px;text-align:center}}
.alert-error{{background:rgba(239,68,68,0.2);border:1px solid #ef4444}}
.alert-success{{background:rgba(34,197,94,0.2);border:1px solid #22c55e}}
.alert-warning{{background:rgba(251,191,36,0.2);border:1px solid #fbbf24;color:#fbbf24}}
.temp-slider{{width:100%;height:12px;border-radius:6px;background:rgba(255,255,255,0.2);-webkit-appearance:none}}
.temp-slider::-webkit-slider-thumb{{-webkit-appearance:none;width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#f97316,#ea580c);cursor:pointer}}
</style>
</head><body>
<div style="max-width:400px;margin:0 auto">
<h1 style="text-align:center;margin-bottom:8px;font-size:28px">🔥 Sauna Control</h1>
<p style="text-align:center;color:rgba(255,255,255,0.6);margin-bottom:30px;font-size:14px">HUUM Controller</p>
{alert_html}
{status_html}
{controls_html}
</div>
<script>
const s=document.getElementById('tempSlider'),v=document.getElementById('tempValue');
if(s)s.addEventListener('input',function(){{v.textContent=this.value+'°C'}});
</script>
</body></html>'''

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        cookies = self.headers.get('Cookie', '')
        session = get_session(cookies)

        if path == '/logout':
            self.send_response(302)
            for cookie in clear_session_cookies():
                self.send_header('Set-Cookie', cookie)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # Main page
        logged_in = 'huum_user' in session and 'huum_pass' in session
        status = None
        error = None

        if logged_in:
            try:
                status = run_async(get_sauna_status(session['huum_user'], session['huum_pass']))
            except Exception as e:
                if '401' in str(e):
                    self.send_response(302)
                    for cookie in clear_session_cookies():
                        self.send_header('Set-Cookie', cookie)
                    self.send_header('Location', '/?error=Session+expired')
                    self.end_headers()
                    return
                error = 'Connection error'

        query = parse_qs(parsed.query)
        error = error or (query.get('error', [None])[0])
        success = query.get('success', [None])[0]

        html = render_page(logged_in=logged_in, status=status, error=error, success=success)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        params = parse_qs(body)
        cookies = self.headers.get('Cookie', '')
        session = get_session(cookies)

        if path == '/login':
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            try:
                run_async(get_sauna_status(username, password))
                self.send_response(302)
                for cookie in set_session_cookies(username, password):
                    self.send_header('Set-Cookie', cookie)
                self.send_header('Location', '/?success=Connected!')
                self.end_headers()
            except:
                self.send_response(302)
                self.send_header('Location', '/?error=Invalid+email+or+password')
                self.end_headers()
            return

        if path == '/control':
            if 'huum_user' not in session:
                self.send_response(302)
                self.send_header('Location', '/?error=Please+login')
                self.end_headers()
                return

            action = params.get('action', [''])[0]
            temp = int(params.get('temperature', ['80'])[0])

            try:
                if action == 'on':
                    run_async(turn_on_sauna(session['huum_user'], session['huum_pass'], temp))
                    self.send_response(302)
                    self.send_header('Location', f'/?success=Heating+to+{temp}°C')
                    self.end_headers()
                elif action == 'off':
                    run_async(turn_off_sauna(session['huum_user'], session['huum_pass']))
                    self.send_response(302)
                    self.send_header('Location', '/?success=Turned+off')
                    self.end_headers()
                else:
                    self.send_response(302)
                    self.send_header('Location', '/')
                    self.end_headers()
            except Exception as e:
                if 'Safety' in str(type(e).__name__):
                    self.send_response(302)
                    self.send_header('Location', '/?error=Close+the+door+first!')
                    self.end_headers()
                else:
                    self.send_response(302)
                    self.send_header('Location', '/?error=Error,+try+again')
                    self.end_headers()
            return

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

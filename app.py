#!/usr/bin/env python3
import asyncio
import os
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production-abc123')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Sauna Control</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔥</text></svg>">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; color: #fff; padding: 20px; }
        .container { max-width: 400px; margin: 0 auto; }
        .card { background: rgba(255,255,255,0.1); border-radius: 20px; padding: 30px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; }
        h1 { text-align: center; margin-bottom: 8px; font-size: 28px; }
        .subtitle { text-align: center; color: rgba(255,255,255,0.6); margin-bottom: 30px; font-size: 14px; }
        .status-badge { display: inline-block; padding: 10px 20px; border-radius: 25px; font-weight: 600; font-size: 16px; }
        .status-on { background: #4ade80; color: #166534; }
        .status-off { background: #6b7280; color: #fff; }
        .status-heating { background: #fb923c; color: #7c2d12; }
        .temp-display { text-align: center; margin: 30px 0; }
        .current-temp { font-size: 80px; font-weight: 200; line-height: 1; }
        .temp-unit { font-size: 32px; font-weight: 300; vertical-align: super; }
        .target-temp { color: rgba(255,255,255,0.6); font-size: 16px; margin-top: 8px; }
        .temp-slider { width: 100%; height: 12px; border-radius: 6px; background: rgba(255,255,255,0.2); -webkit-appearance: none; }
        .temp-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); cursor: pointer; }
        .btn { padding: 18px 24px; border: none; border-radius: 14px; font-size: 18px; font-weight: 600; cursor: pointer; width: 100%; }
        .btn-on { background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); color: white; }
        .btn-off { background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.2); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 20px; }
        .info-box { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 15px; text-align: center; }
        .info-label { color: rgba(255,255,255,0.5); font-size: 12px; text-transform: uppercase; margin-bottom: 5px; }
        .info-value { font-size: 20px; font-weight: 600; }
        .alert { padding: 14px 18px; border-radius: 12px; margin-bottom: 20px; font-size: 15px; text-align: center; }
        .alert-error { background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; }
        .alert-success { background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; }
        .alert-warning { background: rgba(251, 191, 36, 0.2); border: 1px solid #fbbf24; color: #fbbf24; }
        .login-form input { width: 100%; padding: 16px; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; background: rgba(255,255,255,0.1); color: white; font-size: 17px; margin-bottom: 14px; }
        .login-form input::placeholder { color: rgba(255,255,255,0.5); }
        .temp-value { font-size: 28px; font-weight: 700; color: #f97316; }
        .slider-row { display: flex; align-items: center; gap: 12px; }
        .slider-labels { color: rgba(255,255,255,0.5); font-size: 14px; }
        .logout-link { display: block; text-align: center; margin-top: 25px; color: rgba(255,255,255,0.4); text-decoration: none; font-size: 14px; }
        .refresh-hint { text-align: center; color: rgba(255,255,255,0.3); font-size: 12px; margin-top: 20px; }
        .door-open { color: #fbbf24; }
        .door-closed { color: #4ade80; }
        .loading-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 100; }
        .loading-overlay.active { display: flex; }
        .spinner { width: 50px; height: 50px; border: 4px solid rgba(255,255,255,0.3); border-top-color: #f97316; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="loading-overlay" id="loadingOverlay"><div class="spinner"></div></div>
    <div class="container">
        <h1>🔥 Sauna Control</h1>
        <p class="subtitle">HUUM Controller</p>
        {% if error %}<div class="alert alert-error">{{ error }}</div>{% endif %}
        {% if success %}<div class="alert alert-success">{{ success }}</div>{% endif %}
        {% if not logged_in %}
        <div class="card">
            <form class="login-form" method="POST" action="/login" onsubmit="showLoading()">
                <input type="email" name="username" placeholder="HUUM Email" required autocomplete="email">
                <input type="password" name="password" placeholder="HUUM Password" required>
                <button type="submit" class="btn btn-on">Connect</button>
            </form>
        </div>
        <p class="refresh-hint">Use your HUUM app login</p>
        {% else %}
        {% if status %}
        <div class="card">
            <div style="text-align: center; margin-bottom: 15px;">
                {% if status.statusCode == 230 or status.statusCode == 231 %}<span class="status-badge status-heating">🔥 HEATING</span>
                {% elif status.statusCode == 232 %}<span class="status-badge status-on">✓ READY</span>
                {% else %}<span class="status-badge status-off">○ OFF</span>{% endif %}
            </div>
            <div class="temp-display">
                <span class="current-temp">{{ status.temperature }}<span class="temp-unit">°C</span></span>
                {% if status.targetTemperature and (status.statusCode == 230 or status.statusCode == 231 or status.statusCode == 232) %}
                <div class="target-temp">Target: {{ status.targetTemperature }}°C</div>{% endif %}
            </div>
            <div class="info-grid">
                <div class="info-box"><div class="info-label">Humidity</div><div class="info-value">{{ status.humidity }}%</div></div>
                <div class="info-box"><div class="info-label">Door</div><div class="info-value {% if status.door %}door-open{% else %}door-closed{% endif %}">{{ 'OPEN' if status.door else 'CLOSED' }}</div></div>
            </div>
        </div>
        {% if status.door %}<div class="alert alert-warning">⚠️ Close the door before turning on</div>{% endif %}
        {% endif %}
        <div class="card">
            <form method="POST" action="/control" onsubmit="showLoading()">
                <div style="margin-bottom: 25px;">
                    <label style="display: block; margin-bottom: 12px; color: rgba(255,255,255,0.7);">Set Temperature</label>
                    <div class="slider-row">
                        <span class="slider-labels">40°</span>
                        <input type="range" name="temperature" min="40" max="110" value="{{ status.targetTemperature or 80 }}" class="temp-slider" id="tempSlider">
                        <span class="slider-labels">110°</span>
                    </div>
                    <div style="text-align: center; margin-top: 15px;"><span class="temp-value" id="tempValue">{{ status.targetTemperature or 80 }}°C</span></div>
                </div>
                {% if status and (status.statusCode == 230 or status.statusCode == 231 or status.statusCode == 232) %}
                <button type="submit" name="action" value="off" class="btn btn-off">Turn Off</button>
                {% else %}
                <button type="submit" name="action" value="on" class="btn btn-on" {% if status and status.door %}disabled{% endif %}>Turn On Sauna</button>
                {% endif %}
            </form>
        </div>
        <p class="refresh-hint">Pull down to refresh</p>
        <a href="/logout" class="logout-link">Disconnect</a>
        {% endif %}
    </div>
    <script>
        function showLoading() { document.getElementById('loadingOverlay').classList.add('active'); }
        const slider = document.getElementById('tempSlider');
        const tempValue = document.getElementById('tempValue');
        if (slider) { slider.addEventListener('input', function() { tempValue.textContent = this.value + '°C'; }); }
        {% if status and (status.statusCode == 230 or status.statusCode == 231 or status.statusCode == 232) %}
        setTimeout(() => location.reload(), 30000);
        {% endif %}
    </script>
</body>
</html>
"""

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

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

@app.route('/')
def index():
    error = request.args.get('error')
    success = request.args.get('success')
    if 'username' not in session:
        return render_template_string(HTML_TEMPLATE, logged_in=False, error=error)
    try:
        status = run_async(get_sauna_status(session['username'], session['password']))
        return render_template_string(HTML_TEMPLATE, logged_in=True, status=status, error=error, success=success)
    except Exception as e:
        if '401' in str(e) or 'NotAuthenticated' in str(type(e).__name__):
            session.clear()
            return redirect(url_for('index', error='Session expired'))
        return render_template_string(HTML_TEMPLATE, logged_in=True, status=None, error='Connection error')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    try:
        run_async(get_sauna_status(username, password))
        session['username'] = username
        session['password'] = password
        session.permanent = True
        return redirect(url_for('index', success='Connected!'))
    except:
        return redirect(url_for('index', error='Invalid email or password'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/control', methods=['POST'])
def control():
    if 'username' not in session:
        return redirect(url_for('index', error='Please login'))
    action = request.form.get('action')
    temperature = int(request.form.get('temperature', 80))
    try:
        if action == 'on':
            run_async(turn_on_sauna(session['username'], session['password'], temperature))
            return redirect(url_for('index', success=f'Heating to {temperature}°C'))
        elif action == 'off':
            run_async(turn_off_sauna(session['username'], session['password']))
            return redirect(url_for('index', success='Turned off'))
    except Exception as e:
        if 'Safety' in str(type(e).__name__):
            return redirect(url_for('index', error='Close the door first!'))
        return redirect(url_for('index', error='Error, try again'))
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

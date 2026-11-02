#!/usr/bin/env python3
"""Personal Raspberry Pi workbench; stdlib only. Run with python3 backend.py."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs, quote, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
from http.cookies import SimpleCookie
import copy
import hmac
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import fan_control
import update_service

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / '.local' / 'share' / 'pi-workbench'
DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
TOKEN_FILE = DATA / 'access-token'
SETTINGS_FILE = DATA / 'tasks.json'
PHOTOS = Path.home() / 'Pictures' / 'CCD Camera'
NAME_RE = re.compile(r'CCD_[0-9]{8}_[0-9]{6}_[0-9a-f]{6}\.jpg\Z')
LOCK = threading.Lock()
WAKE = threading.Event()
NETWORK_LOCK = threading.Lock()
NETWORK_SAMPLES = {}
DEFAULT = {
    'website': {'enabled': False, 'url': '', 'interval_seconds': 300, 'last_check': None,
                'result': None, 'changed_at': None, 'message': '', 'history': []},
    'photo': {'enabled': False, 'interval_seconds': 3600, 'last_run': None,
              'result': None, 'message': '', 'history': []},
}


def get_token():
    try:
        fd = os.open(TOKEN_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        value = TOKEN_FILE.read_text(encoding='ascii').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{40,100}', value):
            raise RuntimeError('Access token file is invalid; check ' + str(TOKEN_FILE))
        return value
    value = secrets.token_urlsafe(32)
    with os.fdopen(fd, 'w', encoding='ascii') as stream:
        stream.write(value + '\n')
    return value


TOKEN = get_token()


def load_tasks():
    state = copy.deepcopy(DEFAULT)
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
        for key in ('website', 'photo'):
            for field in state[key]:
                if field in raw.get(key, {}):
                    state[key][field] = raw[key][field]
            if not isinstance(state[key]['history'], list):
                state[key]['history'] = []
            state[key]['history'] = state[key]['history'][:10]
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return state


TASKS = load_tasks()


def save_tasks():
    # Caller holds LOCK. Atomic rename avoids corrupting config on interruption.
    temp = DATA / ('tasks.' + secrets.token_hex(6) + '.tmp')
    try:
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(TASKS, stream, ensure_ascii=False, indent=2)
        os.replace(temp, SETTINGS_FILE)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def valid_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        u = urlsplit(value)
        return (u.scheme in ('http', 'https') and bool(u.hostname) and
                not u.username and not u.password and u.port != 0 and
                not any(ord(c) < 32 for c in value))
    except ValueError:
        return False


def web_check(url):
    try:
        req = Request(url, headers={'User-Agent': 'PiWorkbench/1.0'}, method='GET')
        with urlopen(req, timeout=8) as response:
            return 'ok', 'HTTP ' + str(response.status)
    except HTTPError as exc:
        return 'error', 'HTTP ' + str(exc.code)
    except Exception as exc:
        return 'error', (str(getattr(exc, 'reason', exc)) or '连接失败')[:180]


def camera_shot():
    try:
        # A user may have started only the workbench since the last reboot.
        # Start the existing service only when an enabled photo task runs.
        check = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', 'ccd-camera.service'],
                               capture_output=True, text=True, timeout=3)
        if check.returncode != 0:
            start = subprocess.run(['systemctl', '--user', 'start', 'ccd-camera.service'],
                                   capture_output=True, text=True, timeout=8)
            if start.returncode != 0:
                detail = (start.stderr or start.stdout).strip()
                return 'error', ('无法启动相机服务：' + (detail or '请检查服务配置'))[:180]
        deadline = time.monotonic() + 10
        last_error = '相机尚未就绪'
        while time.monotonic() < deadline:
            try:
                with urlopen('http://127.0.0.1:8091/api/status', timeout=2) as response:
                    state = json.loads(response.read(4096))
                if state.get('ready') is True:
                    break
                last_error = state.get('error') or last_error
            except (OSError, ValueError) as exc:
                last_error = str(getattr(exc, 'reason', exc))
            time.sleep(0.5)
        else:
            return 'error', ('相机启动后未就绪：' + str(last_error))[:180]
        req = Request('http://127.0.0.1:8091/api/capture', data=b'{"effect":"ccd"}',
                      headers={'Content-Type': 'application/json'}, method='POST')
        with urlopen(req, timeout=40) as response:
            result = json.loads(response.read(4096))
        if not result.get('url'):
            raise RuntimeError('相机未返回照片地址')
        return 'ok', '照片已保存'
    except HTTPError as exc:
        try:
            message = json.loads(exc.read(4096)).get('error', '')
        except Exception:
            message = ''
        return 'error', (message or '相机服务返回 HTTP ' + str(exc.code))[:180]
    except subprocess.TimeoutExpired:
        return 'error', '启动相机服务超时，请检查相机服务状态'
    except Exception as exc:
        return 'error', ('相机不可用：' + str(getattr(exc, 'reason', exc)))[:180]


def worker():
    while True:
        with LOCK:
            snapshot = copy.deepcopy(TASKS)
        now = time.time()
        site = snapshot['website']
        if site['enabled'] and valid_url(site['url']) and now - (site['last_check'] or 0) >= site['interval_seconds']:
            result, message = web_check(site['url'])
            checked = int(time.time())
            with LOCK:
                current = TASKS['website']
                if current['enabled'] and current['url'] == site['url']:
                    if current['result'] != result:
                        current['changed_at'] = checked
                        current['history'].insert(0, {'time': checked, 'result': result, 'message': message})
                        del current['history'][10:]
                    current.update(last_check=checked, result=result, message=message)
                    save_tasks()
        with LOCK:
            photo = copy.deepcopy(TASKS['photo'])
        now = time.time()
        if photo['enabled'] and now - (photo['last_run'] or 0) >= photo['interval_seconds']:
            result, message = camera_shot()
            finished = int(time.time())
            with LOCK:
                current = TASKS['photo']
                current.update(last_run=finished, result=result, message=message)
                current['history'].insert(0, {'time': finished, 'result': result, 'message': message})
                del current['history'][10:]
                save_tasks()
        WAKE.wait(5)
        WAKE.clear()


def network_details():
    """Read local interface addresses and observed traffic; never perform a speed test."""
    now = time.time()
    monotonic_now = time.monotonic()
    errors = []

    def ip_json(*args):
        try:
            result = subprocess.run(['ip', '-j', *args], capture_output=True,
                                    text=True, timeout=2, check=True)
            value = json.loads(result.stdout)
            if not isinstance(value, list):
                raise ValueError('invalid ip output')
            return value
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            errors.append(str(exc))
            return []

    addresses = ip_json('address', 'show')
    routes4 = ip_json('-4', 'route', 'show', 'default')
    routes6 = ip_json('-6', 'route', 'show', 'default')

    def gateways(routes):
        # Linux may report multiple defaults; prefer the lowest-metric route.
        selected = {}
        for route in sorted(routes, key=lambda item: item.get('metric', 0)):
            name = route.get('dev')
            if name and name not in selected:
                selected[name] = route.get('gateway')
        return selected

    gw4, gw6 = gateways(routes4), gateways(routes6)
    interfaces = []
    for info in addresses:
        name = info.get('ifname', '')
        if not name or name == 'lo' or '/' in name or name in ('.', '..'):
            continue
        base = Path('/sys/class/net') / name

        def number(path):
            try:
                value = int(path.read_text().strip())
                return value if value >= 0 else None
            except (OSError, ValueError):
                return None

        rx = number(base / 'statistics' / 'rx_bytes')
        tx = number(base / 'statistics' / 'tx_bytes')
        speed = number(base / 'speed')
        if speed == 0:
            speed = None
        rx_rate = tx_rate = None
        with NETWORK_LOCK:
            prior = NETWORK_SAMPLES.get(name)
            if prior:
                elapsed = monotonic_now - prior['time']
                # Reuse a recent rate when several clients request simultaneously.
                if elapsed < 0.8:
                    rx_rate, tx_rate = prior['rx_rate'], prior['tx_rate']
                else:
                    if rx is not None and prior['rx'] is not None and rx >= prior['rx']:
                        rx_rate = round((rx - prior['rx']) / elapsed, 1)
                    if tx is not None and prior['tx'] is not None and tx >= prior['tx']:
                        tx_rate = round((tx - prior['tx']) / elapsed, 1)
            if not prior or monotonic_now - prior['time'] >= 0.8:
                NETWORK_SAMPLES[name] = {'time': monotonic_now, 'rx': rx, 'tx': tx,
                                         'rx_rate': rx_rate, 'tx_rate': tx_rate}
        v4, v6 = [], []
        for address in info.get('addr_info', []):
            local = address.get('local')
            if not local:
                continue
            prefix = address.get('prefixlen')
            rendered = str(local) + ('/' + str(prefix) if prefix is not None else '')
            if address.get('family') == 'inet':
                v4.append(rendered)
            elif address.get('family') == 'inet6':
                v6.append(rendered)
        kind = 'wifi' if (base / 'wireless').exists() else (
            'ethernet' if number(base / 'type') == 1 else 'other')
        wifi_rx = wifi_tx = wifi_signal = None
        if kind == 'wifi':
            try:
                link = subprocess.run([shutil.which('iw') or '/usr/sbin/iw', 'dev', name, 'link'],
                                      capture_output=True, text=True, timeout=2, check=True).stdout

                def wifi_rate(direction):
                    match = re.search(r'^\s*' + direction + r' bitrate:\s*([\d.]+)\s*([KMG])Bit/s\b',
                                      link, re.MULTILINE | re.IGNORECASE)
                    if not match:
                        return None
                    multiplier = {'k': 0.001, 'm': 1.0, 'g': 1000.0}[match.group(2).lower()]
                    return round(float(match.group(1)) * multiplier, 3)

                wifi_rx, wifi_tx = wifi_rate('rx'), wifi_rate('tx')
                signal = re.search(r'^\s*signal:\s*(-?\d+(?:\.\d+)?)\s*dBm\b',
                                   link, re.MULTILINE | re.IGNORECASE)
                if signal:
                    wifi_signal = float(signal.group(1))
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
        interfaces.append({'name': name, 'state': info.get('operstate', 'UNKNOWN'),
                           'type': kind, 'mac': info.get('address'), 'mtu': info.get('mtu'),
                           'ipv4': v4, 'ipv6': v6, 'gateway4': gw4.get(name),
                           'gateway6': gw6.get(name), 'link_mbps': speed,
                           'wifi_rx_mbps': wifi_rx, 'wifi_tx_mbps': wifi_tx,
                           'wifi_signal_dbm': wifi_signal,
                           'rx_bytes': rx, 'tx_bytes': tx,
                           'rx_bytes_per_sec': rx_rate, 'tx_bytes_per_sec': tx_rate,
                           'is_default': name in gw4 or name in gw6})
    interfaces.sort(key=lambda item: (not item['is_default'], item['name']))
    return {'interfaces': interfaces, 'sampled_at': int(now),
            'error': '无法读取部分网络信息' if errors else None}


def status():
    memory = {}
    try:
        with open('/proc/meminfo', encoding='ascii') as f:
            for line in f:
                if line.startswith(('MemTotal:', 'MemAvailable:')):
                    k, v = line.split(':', 1)
                    memory[k] = int(v.strip().split()[0]) * 1024
    except (OSError, ValueError):
        pass
    try:
        uptime = float(Path('/proc/uptime').read_text().split()[0])
    except (OSError, ValueError, IndexError):
        uptime = None
    try:
        temp = round(int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000, 1)
    except (OSError, ValueError):
        temp = None
    try:
        p = subprocess.run(['systemctl', '--user', 'is-active', 'ccd-camera.service'],
                           capture_output=True, text=True, timeout=2)
        camera = p.stdout.strip()
        if camera not in ('active', 'inactive', 'failed', 'activating', 'deactivating'):
            camera = 'unknown'
    except (OSError, subprocess.TimeoutExpired):
        camera = 'unknown'
    try:
        p = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=2)
        addresses = p.stdout.split() if p.returncode == 0 else []
    except (OSError, subprocess.TimeoutExpired):
        addresses = []
    try:
        disk = shutil.disk_usage(Path.home())
        disk_data = {'total_bytes': disk.total, 'free_bytes': disk.free}
    except OSError:
        disk_data = {'total_bytes': None, 'free_bytes': None}
    return {'hostname': socket.gethostname(), 'uptime_seconds': uptime, 'cpu_temp_c': temp,
            'memory': {'total_bytes': memory.get('MemTotal'), 'available_bytes': memory.get('MemAvailable')},
            'disk': disk_data, 'ip_addresses': addresses, 'camera_service': camera}


LOGIN = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>个人工作台 · 登录</title><style>body{margin:0;font:16px/1.6 system-ui,sans-serif;background:#f4f2ec;color:#29382f;display:grid;place-items:center;min-height:100vh}main{background:white;padding:32px;border-radius:16px;width:min(380px,calc(100vw - 64px));box-shadow:0 12px 40px #263e2c15}h1{font-size:24px}p{color:#667568}input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #bac8ba;border-radius:8px;font:inherit}button{margin-top:15px;background:#405d4e;color:white;border:0;border-radius:8px;padding:12px 20px;font:inherit;cursor:pointer}</style><main><h1>树莓派个人工作台</h1><p>请输入工作台访问码。</p><form method="get" action="/"><input name="token" aria-label="访问码" placeholder="访问码" required autocomplete="off"><button type="submit">进入工作台</button></form></main></html>'''.encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    server_version = 'PiWorkbench/1.0'

    def log_message(self, fmt, *args):
        # Never log the access token in the query string.
        pass

    def send_data(self, code, data, kind, headers=()):
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, code, value):
        self.send_data(code, json.dumps(value, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

    def authorized(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookies.get('pi_workbench')
            return token is not None and hmac.compare_digest(token.value, TOKEN)
        except Exception:
            return False

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/':
            supplied = parse_qs(parsed.query).get('token', [''])[0]
            if re.fullmatch(r'[A-Za-z0-9_-]{40,100}', supplied) and hmac.compare_digest(supplied, TOKEN):
                self.send_data(303, b'', 'text/plain', [('Location', '/'),
                    ('Set-Cookie', 'pi_workbench=' + TOKEN + '; HttpOnly; SameSite=Strict; Path=/')])
                return
            if not self.authorized():
                self.send_data(200, LOGIN, 'text/html; charset=utf-8')
                return
            try:
                self.send_data(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            except OSError:
                self.send_json(500, {'error': '工作台页面无法读取'})
            return
        if not self.authorized():
            self.send_json(401, {'error': '请先登录工作台'})
            return
        if parsed.path == '/api/status':
            self.send_json(200, status())
        elif parsed.path == '/api/network':
            self.send_json(200, network_details())
        elif parsed.path == '/api/fan':
            self.send_json(200, fan_control.read_fan())
        elif parsed.path == '/api/update':
            self.send_json(200, update_service.get_update_status())
        elif parsed.path == '/api/tasks':
            with LOCK:
                data = copy.deepcopy(TASKS)
            self.send_json(200, data)
        elif parsed.path == '/api/photos':
            names = sorted((p.name for p in PHOTOS.glob('CCD_*.jpg') if NAME_RE.fullmatch(p.name)), reverse=True)[:12]
            self.send_json(200, {'photos': [{'name': name, 'url': '/photo/' + quote(name)} for name in names]})
        elif parsed.path.startswith('/photo/'):
            name = unquote(parsed.path[len('/photo/'):])
            if not NAME_RE.fullmatch(name):
                self.send_json(404, {'error': '未找到照片'})
                return
            try:
                self.send_data(200, (PHOTOS / name).read_bytes(), 'image/jpeg')
            except OSError:
                self.send_json(404, {'error': '未找到照片'})
        else:
            self.send_json(404, {'error': '页面不存在'})

    def do_POST(self):
        if not self.authorized():
            self.send_json(401, {'error': '请先登录工作台'})
            return
        path = urlsplit(self.path).path
        if path not in ('/api/tasks', '/api/fan', '/api/update'):
            self.send_json(404, {'error': '页面不存在'})
            return
        origin = self.headers.get('Origin', '')
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or parsed.netloc != self.headers.get('Host'):
            self.send_json(403, {'error': '请求来源不受信任'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192:
                raise ValueError('请求数据大小不正确')
            data = json.loads(self.rfile.read(length))
            if path == '/api/fan':
                self.send_json(200, fan_control.set_fan(data))
                return
            if path == '/api/update':
                self.send_json(200, update_service.start_update(data['target'], data['action']))
                return
            web = data['website']
            photo = data['photo']
            if not isinstance(web['enabled'], bool) or not isinstance(photo['enabled'], bool):
                raise ValueError('任务开关格式不正确')
            url = web['url'].strip()
            if url and not valid_url(url):
                raise ValueError('请输入有效的 HTTP 或 HTTPS 网站地址')
            if web['enabled'] and not valid_url(url):
                raise ValueError('请填写要检查的网站地址')
            wi, pi = int(web['interval_seconds']), int(photo['interval_seconds'])
            if not 60 <= wi <= 604800:
                raise ValueError('网站检查间隔须在 60 秒至 7 天之间')
            if not 300 <= pi <= 604800:
                raise ValueError('拍照间隔须在 300 秒至 7 天之间')
            with LOCK:
                if TASKS['website']['url'] != url:
                    TASKS['website'].update(last_check=None, result=None, changed_at=None, message='', history=[])
                TASKS['website'].update(enabled=web['enabled'], url=url, interval_seconds=wi)
                TASKS['photo'].update(enabled=photo['enabled'], interval_seconds=pi)
                save_tasks()
                result = copy.deepcopy(TASKS)
            WAKE.set()
            self.send_json(200, result)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {'error': str(exc) or '任务设置格式不正确'})
        except RuntimeError as exc:
            self.send_json(500, {'error': str(exc) or '操作失败'})
        except OSError:
            self.send_json(500, {'error': '无法保存任务设置'})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == '__main__':
    server = Server(('0.0.0.0', 8092), Handler)
    threading.Thread(target=worker, daemon=True).start()
    print('Pi Workbench listening on port 8092', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


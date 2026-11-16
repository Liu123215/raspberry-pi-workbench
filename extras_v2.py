import json, os, shutil, socket, subprocess, threading, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

BASE = Path.home() / '.local' / 'share' / 'pi-workbench'
LOCK = threading.RLock()
BACKUP_LOCK = threading.Lock()

def _read(name, default):
    try:
        return json.loads((BASE / name).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default

def _write(name, value):
    BASE.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = BASE / (name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    os.chmod(tmp, 0o600)
    tmp.replace(BASE / name)

def get_history():
    with LOCK:
        return _read('history.json', {'samples': [], 'alerts': []})

def _sample(status):
    s = status(); now = time.time()
    memory = s.get('memory', {}); disk = s.get('disk', {})
    total = memory.get('total_bytes'); available = memory.get('available_bytes')
    item = {'time': now, 'temperature': s.get('cpu_temp_c'),
            'memory_percent': round(100 * (total - available) / total, 1) if total and available is not None else None,
            'disk_free_bytes': disk.get('free_bytes'), 'camera': s.get('camera_service'),
            'online': bool(s.get('ip_addresses'))}
    alerts = []
    if item['temperature'] is not None and item['temperature'] >= 80: alerts.append('high_temperature')
    if disk.get('total_bytes') and item['disk_free_bytes'] is not None and item['disk_free_bytes'] / disk['total_bytes'] < .1: alerts.append('low_disk')
    if item['camera'] == 'failed': alerts.append('camera_failed')
    if not item['online']: alerts.append('network_disconnected')
    with LOCK:
        h = get_history(); h['samples'] = (h.get('samples', []) + [item])[-1440:]; h['alerts'] = alerts
        _write('history.json', h)

def get_shortcuts():
    with LOCK: return _read('shortcuts.json', [])

def save_shortcuts(data):
    from urllib.parse import urlsplit
    if not isinstance(data, list) or len(data) > 30: raise ValueError('Expected up to 30 shortcuts')
    result = []
    for item in data:
        if not isinstance(item, dict): raise ValueError('Invalid shortcut')
        label = str(item.get('label', '')).strip(); url = str(item.get('url', '')).strip()
        p = urlsplit(url)
        if not label or len(label) > 80 or len(url) > 1024 or p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            raise ValueError('Shortcut requires a label and HTTP(S) address')
        result.append({'label': label, 'url': url})
    with LOCK: _write('shortcuts.json', result)
    return result

def network_check():
    start = time.monotonic()
    try:
        with socket.create_connection(('1.1.1.1', 53), timeout=3): pass
        return {'reachable': True, 'latency_ms': round((time.monotonic() - start)*1000, 1), 'target': '1.1.1.1:53', 'method': 'TCP'}
    except OSError as exc:
        return {'reachable': False, 'latency_ms': None, 'target': '1.1.1.1:53', 'method': 'TCP', 'error': str(exc)}

def speed_test():
    start = time.monotonic(); size = 0
    with urlopen('https://speed.cloudflare.com/__down?bytes=2000000', timeout=15) as response:
        while size < 2000000:
            data = response.read(min(65536, 2000000-size))
            if not data: break
            size += len(data)
    seconds = time.monotonic() - start
    return {'bytes': size, 'seconds': round(seconds, 2), 'download_mbps': round(size * 8 / max(seconds, .001) / 1000000, 2)}

def get_backup():
    with LOCK: return _read('backup.json', {'enabled': False, 'source': str(Path.home() / 'Pictures' / 'CCD Camera'), 'destination': '', 'interval_hours': 24, 'last_success': None, 'last_error': None})

def _validate_backup(source, destination):
    home = Path.home().resolve(); src = Path(source).expanduser().resolve(strict=True); dst = Path(destination).expanduser().resolve(strict=True)
    if not src.is_dir() or not dst.is_dir() or src == home or home not in src.parents: raise ValueError('Source must be an existing folder inside your home directory')
    if src == dst or src in dst.parents or dst in src.parents: raise ValueError('Source and destination cannot contain each other')
    if src.stat().st_dev == dst.stat().st_dev: raise ValueError('Choose an external mounted disk as destination')
    if not os.access(dst, os.W_OK): raise ValueError('Destination is not writable')
    return src, dst

def configure_backup(data):
    old = get_backup(); enabled = data.get('enabled', False)
    if not isinstance(enabled, bool): raise ValueError('Invalid enabled value')
    source = str(data.get('source', old['source'])); destination = str(data.get('destination', old['destination']))
    hours = int(data.get('interval_hours', 24))
    if not 1 <= hours <= 720: raise ValueError('Backup interval must be 1 to 720 hours')
    if enabled: _validate_backup(source, destination)
    old.update(enabled=enabled, source=source, destination=destination, interval_hours=hours)
    with LOCK: _write('backup.json', old)
    return old

def run_backup():
    if not BACKUP_LOCK.acquire(blocking=False): raise ValueError('Backup already running')
    try:
        cfg = get_backup(); src, dst = _validate_backup(cfg['source'], cfg['destination'])
        name = 'pi-workbench-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-%fZ')
        shutil.copytree(src, dst / name, symlinks=True)
        cfg['last_success'] = time.time(); cfg['last_error'] = None
        with LOCK: _write('backup.json', cfg)
        return {'path': str(dst / name), 'last_success': cfg['last_success']}
    except Exception as exc:
        cfg = get_backup(); cfg['last_error'] = str(exc)
        with LOCK: _write('backup.json', cfg)
        raise
    finally: BACKUP_LOCK.release()

def start(status):
    def worker():
        last_attempt = 0
        while True:
            try: _sample(status)
            except Exception: pass
            try:
                cfg = get_backup()
                if cfg['enabled'] and time.time() - max(cfg.get('last_success') or 0, last_attempt) >= cfg['interval_hours'] * 3600:
                    last_attempt = time.time()
                    run_backup()
            except Exception: pass
            time.sleep(60)
    threading.Thread(target=worker, daemon=True, name='workbench-history').start()


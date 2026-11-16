"""Constrained local file, storage, service and power operations."""
import base64
import os
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
import json

ROOTS = {'files': Path.home() / 'Workbench Files', 'photos': Path.home() / 'Pictures' / 'CCD Camera', 'downloads': Path.home() / 'Downloads'}
MAX_UPLOAD = 5 * 1024 * 1024

def resolve(root, path=''):
    if root not in ROOTS or not isinstance(path, str) or len(path) > 4096:
        raise ValueError('无效的文件位置')
    base = ROOTS[root].resolve()
    if Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('无效的文件位置')
    # Do not follow links, including links that point back into the allowed tree:
    # renaming or trashing one must never act on its target instead.
    candidate = base
    for part in Path(path).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError('不能访问符号链接')
    result = candidate.resolve()
    if result != base and base not in result.parents:
        raise ValueError('不能访问此位置')
    return result

def listing(root, path=''):
    directory = resolve(root, path)
    if not directory.is_dir():
        raise ValueError('目录不存在')
    items = []
    for p in directory.iterdir():
        if p.is_symlink():
            continue
        try:
            st = p.stat()
            items.append({'name': p.name, 'is_dir': p.is_dir(), 'size': st.st_size, 'modified': st.st_mtime})
        except OSError:
            continue
    return {'roots': list(ROOTS), 'root': root, 'path': path, 'items': sorted(items, key=lambda x: (not x['is_dir'], x['name'].casefold()))[:1000]}

def action(data):
    root, path, op = data.get('root'), data.get('path', ''), data.get('action')
    target = resolve(root, path)
    if op in ('trash', 'rename'):
        name = data.get('name', '')
        if not isinstance(name, str) or not name or name in ('.', '..') or '/' in name or '\\' in name:
            raise ValueError('文件名无效')
        target = resolve(root, str(Path(path) / name))
    if op == 'trash':
        if target == ROOTS[root].resolve() or not target.exists():
            raise ValueError('不能删除此位置')
        result = subprocess.run(['gio', 'trash', str(target)], capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError('无法移入回收站')
    elif op in ('mkdir', 'rename', 'upload'):
        name = data.get('new_name', '') if op == 'rename' else data.get('name', '')
        if not isinstance(name, str) or not name or name in ('.', '..') or '/' in name or '\\' in name or '\x00' in name:
            raise ValueError('文件名无效')
        dest = target.parent / name if op == 'rename' else target / name
        resolve(root, str(dest.relative_to(ROOTS[root].resolve())))
        if dest.exists() or dest.is_symlink():
            raise ValueError('目标已存在')
        if op == 'mkdir':
            dest.mkdir()
        elif op == 'rename':
            if target == ROOTS[root].resolve():
                raise ValueError('不能重命名根目录')
            target.rename(dest)
        else:
            try:
                content = base64.b64decode(data.get('content', ''), validate=True)
            except Exception:
                raise ValueError('上传内容无效')
            if len(content) > MAX_UPLOAD:
                raise ValueError('单个文件不能超过 5 MB')
            with dest.open('xb') as f:
                f.write(content)
    else:
        raise ValueError('不支持的操作')
    return {'ok': True}

def storage():
    items = []
    for key, base in ROOTS.items():
        size = count = 0
        for folder, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
            for name in files:
                try:
                    p = Path(folder) / name
                    if not p.is_symlink():
                        size += p.stat().st_size
                        count += 1
                except OSError:
                    pass
        items.append({'root': key, 'bytes': size, 'files': count})
    d = shutil.disk_usage(Path.home())
    return {'items': items, 'disk': {'total': d.total, 'used': d.used, 'free': d.free}}

def services():
    entries = []
    for name in ('ccd-camera.service', 'pi-workbench.service'):
        state = subprocess.run(['systemctl', '--user', 'is-active', name], capture_output=True, text=True, timeout=5).stdout.strip()
        logs = subprocess.run(['journalctl', '--user', '-u', name, '-n', '30', '--no-pager'], capture_output=True, text=True, timeout=5)
        entries.append({'name': name, 'state': state or 'unknown', 'logs': (logs.stdout or logs.stderr)[-8000:]})
    return {'services': entries}

def service_action(data):
    name, op = data.get('name'), data.get('action')
    if name != 'ccd-camera.service' or op not in ('start', 'restart', 'stop'):
        raise ValueError('不支持的服务操作')
    if op != 'start':
        check_camera()
    p = subprocess.run(['systemctl', '--user', op, name], capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise ValueError((p.stderr or '服务操作失败')[:300])
    return {'ok': True}

def check_camera():
    try:
        with urlopen('http://127.0.0.1:8091/api/status', timeout=3) as r:
            state = json.loads(r.read(8192))
            if not isinstance(state, dict) or 'recording' not in state:
                raise ValueError('无法确认相机录像状态，请先检查相机')
            recording = state['recording']
            if recording is None or recording is False:
                return
            if recording is True or isinstance(recording, dict):
                raise ValueError('相机正在录像，请先停止')
            raise ValueError('无法确认相机录像状态，请先检查相机')
    except (OSError, json.JSONDecodeError) as exc:
        reason = exc.reason if isinstance(exc, URLError) else exc
        if isinstance(reason, ConnectionRefusedError):
            try:
                service = subprocess.run(['systemctl', '--user', 'is-active', 'ccd-camera.service'],
                                         capture_output=True, text=True, timeout=3)
                if service.returncode == 3 and service.stdout.strip() in ('inactive', 'failed'):
                    return
            except (OSError, subprocess.SubprocessError):
                pass
        raise ValueError('无法确认相机录像状态，请先检查相机')

def power(data, updates):
    op = data.get('action')
    if op not in ('reboot', 'poweroff'):
        raise ValueError('不支持的电源操作')
    if any(v.get('state') == 'running' for v in updates.values()):
        raise ValueError('更新正在进行，请稍后再试')
    check_camera()
    p = subprocess.run(['systemctl', op], capture_output=True, text=True, timeout=10)
    if p.returncode:
        raise ValueError((p.stderr or '电源操作失败，请检查系统权限')[:300])
    return {'ok': True}

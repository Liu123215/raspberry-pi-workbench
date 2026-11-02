#!/usr/bin/env python3
"""Bounded background update jobs for Pi Workbench; no shell commands are used."""
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent
DATA = Path.home() / '.local' / 'share' / 'pi-workbench'
STATE_FILE = DATA / 'update-status.json'
RAW_BASE = 'https://raw.githubusercontent.com/Liu123215/raspberry-pi-workbench/'
BRANCH_URL = 'https://api.github.com/repos/Liu123215/raspberry-pi-workbench/git/ref/heads/main'
FILES = ('backend.py', 'index.html', 'update_service.py', 'fan_control.py')
MAX_FILE = 512 * 1024
MAX_LOG = 12000
LOCK = threading.RLock()
RUNNING = False
STATE = {
    'system': {'state': 'idle', 'message': '尚未检查系统更新', 'log': ''},
    'workbench': {'state': 'idle', 'message': '尚未检查工作台更新', 'log': ''},
}


def _persist():
    """Persist a small result so a workbench restart does not lose the outcome."""
    try:
        DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
        temp = DATA / ('.update-status-' + uuid.uuid4().hex)
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(STATE, f, ensure_ascii=False)
            os.replace(temp, STATE_FILE)
        finally:
            temp.unlink(missing_ok=True)
    except OSError:
        # Failing to save optional update history must not break the web service.
        pass


def _restore():
    try:
        saved = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        for target in STATE:
            item = saved.get(target, {})
            state = item.get('state')
            if state in ('idle', 'running', 'success', 'error'):
                STATE[target].update(state=state, message=str(item.get('message', ''))[:500],
                                     log=str(item.get('log', ''))[-MAX_LOG:])
                if state == 'running':
                    STATE[target].update(state='error', message='上次操作因工作台重启而无法确认结果；系统更新可能仍在后台运行')
    except (OSError, ValueError, TypeError, AttributeError):
        pass


_restore()


def _set(target, state, message, log=None):
    with LOCK:
        STATE[target]['state'] = state
        STATE[target]['message'] = str(message)[:500]
        if log is not None:
            STATE[target]['log'] = str(log)[-MAX_LOG:]
        _persist()


def get_update_status():
    with LOCK:
        return copy.deepcopy(STATE)


def _run(args, timeout):
    """Direct argv only; keep log storage bounded after collecting command output."""
    env = os.environ.copy()
    env['LC_ALL'] = 'C'
    with tempfile.TemporaryFile(mode='w+b') as output:
        try:
            result = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=output,
                                    stderr=subprocess.STDOUT, timeout=timeout, env=env,
                                    check=False)
        except subprocess.TimeoutExpired:
            raise RuntimeError('操作超时，请查看系统状态后再试') from None
        output.seek(0, os.SEEK_END)
        length = output.tell()
        output.seek(max(0, length - MAX_LOG))
        text = output.read(MAX_LOG).decode('utf-8', errors='replace')
    return result.returncode, text


def _system_unit_active():
    try:
        result = subprocess.run(['systemctl', '--user', 'list-units', '--plain', '--no-legend',
                                 '--state=active,activating', 'pi-workbench-system-update-*.service'],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and 'pi-workbench-system-update-' in result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return False


def _run_system(args, timeout):
    # A separate user service is not killed if the web server itself restarts.
    unit = 'pi-workbench-system-update-' + uuid.uuid4().hex[:12]
    command = ['systemd-run', '--user', '--wait', '--quiet', '--collect', '--unit=' + unit,
               '--property=StandardOutput=journal', '--property=StandardError=journal'] + args
    try:
        code, output = _run(command, timeout)
    except RuntimeError:
        raise RuntimeError('操作等待超时，后台任务可能仍在运行；请查看系统状态') from None
    try:
        _, log = _run(['journalctl', '--user', '-u', unit + '.service', '--no-pager', '-n', '150'], 10)
        return code, (output + '\n' + log)[-MAX_LOG:]
    except (OSError, RuntimeError):
        return code, output


def _system(action):
    apt = ['sudo', '-n', 'env', 'DEBIAN_FRONTEND=noninteractive', 'apt-get',
           '-o', 'DPkg::Lock::Timeout=20']
    if action == 'check':
        _set('system', 'running', '正在刷新软件包列表，请稍候')
        code, output = _run_system(apt + ['update'], 600)
        if code:
            _set('system', 'error', '刷新软件包列表失败，系统软件没有更新', output)
            return
        _set('system', 'running', '正在检查可更新的软件包', output)
        code, result = _run_system(apt + ['-s', 'upgrade'], 300)
        if code:
            _set('system', 'error', '检查可更新的软件包失败', result)
            return
        match = re.search(r'(\d+) upgraded,\s*(\d+) newly installed,\s*(\d+) to remove', result)
        message = ('可更新的软件包：' + match.group(1) + ' 个' if match
                   else '检查完成，请查看输出了解可更新的软件包')
        _set('system', 'success', message, result)
    else:
        _set('system', 'running', '正在刷新软件包列表，随后安装更新')
        code, output = _run_system(apt + ['update'], 600)
        if code:
            _set('system', 'error', '刷新软件包列表失败；未开始安装更新', output)
            return
        _set('system', 'running', '正在安装系统更新，请勿关闭或断电', output)
        code, output = _run_system(apt + ['-y', '-o', 'Dpkg::Options::=--force-confdef',
                                   '-o', 'Dpkg::Options::=--force-confold', 'upgrade'], 3600)
        reboot = Path('/var/run/reboot-required').exists()
        if code:
            _set('system', 'error', '系统更新未完成，请查看日志并检查软件包状态', output)
        else:
            _set('system', 'success', '系统更新完成' + ('；系统提示需要重启' if reboot else ''), output)


def _download():
    # Pin all four downloads to one commit so an in-progress publication cannot
    # mix backend, frontend, and helper files from different revisions.
    req = Request(BRANCH_URL, headers={'User-Agent': 'PiWorkbench-Updater/1.0',
                                      'Accept': 'application/vnd.github+json'})
    try:
        with urlopen(req, timeout=20) as response:
            final = urlsplit(response.geturl())
            if final.scheme != 'https' or final.hostname != 'api.github.com':
                raise RuntimeError('更新地址发生非预期的跳转')
            metadata = response.read(131073)
        if len(metadata) > 131072:
            raise RuntimeError('版本信息过大')
        revision = json.loads(metadata)['object']['sha']
        if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise RuntimeError('版本标识无效')
    except Exception as exc:
        raise RuntimeError('无法获取工作台版本信息：' + str(exc)[:160]) from None
    files = {}
    for name in FILES:
        req = Request(RAW_BASE + revision + '/' + name, headers={'User-Agent': 'PiWorkbench-Updater/1.0'})
        try:
            with urlopen(req, timeout=20) as response:
                final = urlsplit(response.geturl())
                if final.scheme != 'https' or final.hostname != 'raw.githubusercontent.com':
                    raise RuntimeError('更新地址发生非预期的跳转')
                content = response.read(MAX_FILE + 1)
        except Exception as exc:
            raise RuntimeError('无法下载 ' + name + '：' + str(exc)[:160]) from None
        if not content or len(content) > MAX_FILE:
            raise RuntimeError('更新文件为空或超出大小限制：' + name)
        try:
            text = content.decode('utf-8-sig')
            if name.endswith('.py'):
                compile(text, name, 'exec')
            elif '<html' not in text.lower() or '</html>' not in text.lower():
                raise ValueError('不是有效的 HTML 页面')
        except (UnicodeError, SyntaxError, ValueError) as exc:
            raise RuntimeError('更新文件格式不正确：' + name + '：' + str(exc)[:160]) from None
        files[name] = content
    return files


def _changed(files):
    changed = []
    for name, content in files.items():
        try:
            current = (ROOT / name).read_bytes()
        except OSError:
            current = b''
        if hashlib.sha256(content).digest() != hashlib.sha256(current).digest():
            changed.append(name)
    return changed


def _workbench(action):
    _set('workbench', 'running', '正在检查 GitHub 上的工作台文件')
    files = _download()
    changed = _changed(files)
    if action == 'check':
        if changed:
            _set('workbench', 'success', '发现 ' + str(len(changed)) + ' 个文件有更新', '\n'.join(changed))
        else:
            _set('workbench', 'success', '工作台已是最新版本', '')
        return
    if not changed:
        _set('workbench', 'success', '工作台已是最新版本', '')
        return
    if not shutil.which('systemd-run') or not shutil.which('systemctl'):
        raise RuntimeError('缺少 systemd 命令，无法安全重启工作台')
    backup = DATA / 'updates' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    backup.mkdir(parents=True, mode=0o700)
    staged = {}
    installed = []
    try:
        for name in FILES:
            target = ROOT / name
            if target.exists():
                shutil.copy2(target, backup / name)
            fd, path = tempfile.mkstemp(prefix='.' + name + '.', dir=ROOT)
            staged[name] = Path(path)
            with os.fdopen(fd, 'wb') as f:
                f.write(files[name])
            os.chmod(path, 0o644)
        for name in FILES:
            os.replace(staged[name], ROOT / name)
            installed.append(name)
        code, output = _run(['systemd-run', '--user', '--quiet', '--on-active=3s',
                             '--unit=pi-workbench-update-' + uuid.uuid4().hex[:10],
                             '/usr/bin/systemctl', '--user', 'restart', 'pi-workbench.service'], 20)
        if code:
            raise RuntimeError('无法安排重启工作台：' + output[-300:])
        _set('workbench', 'success', '更新完成，工作台即将重启；稍后请刷新页面',
             '已更新：' + '、'.join(changed) + '\n旧文件备份于 ' + str(backup))
    except Exception:
        # Restore all replaced files if staging, replacement, or restart scheduling fails.
        for name in reversed(installed):
            old = backup / name
            if old.exists():
                shutil.copy2(old, ROOT / name)
            else:
                (ROOT / name).unlink(missing_ok=True)
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)


def _job(target, action):
    global RUNNING
    try:
        if target == 'system':
            _system(action)
        else:
            _workbench(action)
    except Exception as exc:
        _set(target, 'error', '操作未完成：' + str(exc)[:300])
    finally:
        with LOCK:
            RUNNING = False


def start_update(target, action):
    global RUNNING
    if target not in STATE or action not in ('check', 'install'):
        raise ValueError('无效的更新操作')
    with LOCK:
        if RUNNING or _system_unit_active():
            raise ValueError('已有更新任务正在进行，请等待完成')
        RUNNING = True
        _set(target, 'running', '更新任务已启动', '')
        try:
            threading.Thread(target=_job, args=(target, action), daemon=True).start()
        except Exception:
            RUNNING = False
            _set(target, 'error', '无法启动更新任务')
            raise
        return copy.deepcopy(STATE)


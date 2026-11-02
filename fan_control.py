#!/usr/bin/env python3
"""Persistent Pi 5 PWM control; Linux thermal management remains enabled."""
from pathlib import Path
import json
import os
import secrets
import struct
import subprocess
import threading

HWMON = Path('/sys/class/hwmon')
THERMAL = Path('/sys/class/thermal')
LEVEL_FILES = (Path('/proc/device-tree/cooling_fan/cooling-levels'),
               Path('/sys/firmware/devicetree/base/cooling_fan/cooling-levels'))
DATA = Path.home() / '.local' / 'share' / 'pi-workbench'
STATE_FILE = DATA / 'fan-settings.json'
FAN_HELPER = '/usr/local/libexec/pi-workbench-fan'
_lock = threading.RLock()
_wake = threading.Event()
_started = False
_mode = 'auto'
_target = 50
_error = ''
_safety_override = False


def _fan():
    for hw in sorted(HWMON.glob('hwmon*')):
        try:
            if (hw / 'name').read_text().strip() == 'pwmfan' and (hw / 'pwm1').exists():
                return hw
        except OSError:
            continue
    return None


def _cpu_temperature():
    for zone in sorted(THERMAL.glob('thermal_zone*')):
        try:
            if (zone / 'type').read_text().strip() == 'cpu-thermal':
                return int((zone / 'temp').read_text()) / 1000
        except (OSError, ValueError):
            continue
    raise RuntimeError('无法读取 CPU 温度')


def _automatic_pwm():
    cooling = None
    for device in sorted(THERMAL.glob('cooling_device*')):
        try:
            if (device / 'type').read_text().strip() == 'pwm-fan':
                cooling = device
                break
        except OSError:
            continue
    if cooling is None:
        raise RuntimeError('无法读取风扇自动温控状态')
    state = int((cooling / 'cur_state').read_text())
    for source in LEVEL_FILES:
        try:
            raw = source.read_bytes()
            if len(raw) < 4 or len(raw) % 4:
                continue
            levels = struct.unpack('>' + 'I' * (len(raw) // 4), raw)
            if 0 <= state < len(levels) and all(0 <= x <= 255 for x in levels):
                return state, levels[state]
        except OSError:
            continue
    raise RuntimeError('无法读取风扇自动温控档位')


def _has_fan_permission():
    try:
        return subprocess.run(['sudo', '-n', FAN_HELPER, 'probe'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=2).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _pwm(fan):
    value = int((fan / 'pwm1').read_text())
    if not 0 <= value <= 255:
        raise RuntimeError('风扇状态异常')
    return value


def _write_pwm(fan, value):
    # The root-owned helper validates the PWM value and chooses its own sysfs path.
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
        raise ValueError('无效的风扇控制值')
    proc = subprocess.run(['sudo', '-n', FAN_HELPER, 'set', str(value)],
                          text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3)
    if proc.returncode != 0:
        raise RuntimeError('写入风扇控制失败，请检查设备权限')


def _temperature_or_none():
    try:
        return _cpu_temperature()
    except (OSError, ValueError, RuntimeError):
        return None


def _apply_manual():
    """Apply target every cycle; never reduce after a hot/unknown recheck."""
    global _error, _safety_override
    fan = _fan()
    if fan is None:
        _error = '风扇不可用，无法执行手动控制'
        _safety_override = True
        return False
    temp = _temperature_or_none()
    override = temp is None or temp >= 70
    desired = 255 if override else round(_target * 255 / 100)
    try:
        current = _pwm(fan)
        if desired < current:
            # The temperature may have changed since our first reading.
            new_temp = _temperature_or_none()
            if new_temp is None or new_temp >= 70:
                override, desired = True, 255
                temp = new_temp
        if desired != current:
            _write_pwm(fan, desired)
        _safety_override = override
        _error = '无法读取温度，已请求风扇全速' if temp is None else ''
        return True
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        _safety_override = True
        _error = '风扇控制失败：' + str(exc)[:140]
        # Best effort: a write failure must not be reported as a safe full-speed state.
        try:
            _write_pwm(fan, 255)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            pass
        return False


def _restore_automatic():
    """Give control back to kernel, conservatively retaining high output when hot."""
    fan = _fan()
    if fan is None:
        raise RuntimeError('未检测到风扇')
    current = _pwm(fan)
    temp = _temperature_or_none()
    if temp is None or temp >= 70:
        desired = 255
    else:
        _, auto_pwm = _automatic_pwm()
        desired = max(current, auto_pwm) if temp >= 60 else auto_pwm
    if desired < current:
        recheck = _temperature_or_none()
        if recheck is None or recheck >= 70:
            desired = 255
        elif recheck >= 60:
            _, auto_pwm = _automatic_pwm()
            desired = max(current, auto_pwm)
    if desired != current:
        _write_pwm(fan, desired)


def _persist():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = DATA / ('fan-settings.' + secrets.token_hex(6) + '.tmp')
    try:
        fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump({'mode': _mode, 'target_percent': _target}, output)
        os.replace(tmp, STATE_FILE)
    finally:
        tmp.unlink(missing_ok=True)


def _load():
    global _mode, _target, _error
    try:
        data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        mode, target = data.get('mode'), data.get('target_percent')
        if mode not in ('auto', 'manual') or isinstance(target, bool) or not isinstance(target, int) or not 30 <= target <= 100:
            raise ValueError('风扇设置文件无效')
        _mode, _target = mode, target
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        _mode = 'auto'
        _error = '读取风扇设置失败，保留系统自动温控：' + str(exc)[:100]


def _worker():
    while True:
        with _lock:
            if _mode == 'manual':
                _apply_manual()
        _wake.wait(2)
        _wake.clear()


def start_fan_controller():
    """Start once during server startup so persisted manual settings resume."""
    global _started
    with _lock:
        if _started:
            return
        _load()
        _started = True
        threading.Thread(target=_worker, daemon=True, name='fan-control').start()


def read_fan():
    start_fan_controller()
    with _lock:
        fan = _fan()
        data = {'available': fan is not None, 'controllable': False, 'mode': _mode,
                'percent': None, 'target_percent': _target if _mode == 'manual' else None,
                'rpm': None, 'error': _error, 'safety_override': _safety_override,
                'notice': ''}
        if fan is None:
            data['error'] = '未检测到受支持的树莓派 PWM 风扇'
            return data
        try:
            data['percent'] = round(_pwm(fan) * 100 / 255)
            try:
                data['rpm'] = int((fan / 'fan1_input').read_text())
            except (OSError, ValueError):
                pass
            _automatic_pwm()
            data['controllable'] = _has_fan_permission()
            if not data['controllable']:
                data['error'] = '无法免交互获得风扇调节权限'
            elif _mode == 'manual':
                data['notice'] = '持续维持目标；温度达到 70°C 或读取温度失败时自动全速。'
            else:
                data['notice'] = '系统自动温控已启用；较高温时可能保留较高风速，直至内核下次调节。'
        except (OSError, RuntimeError, ValueError) as exc:
            data['error'] = str(exc)[:180]
        return data


def set_fan(data):
    global _mode, _target, _error, _safety_override
    start_fan_controller()
    if not isinstance(data, dict) or data.get('mode') not in ('auto', 'manual'):
        raise ValueError('请选择自动或手动模式')
    mode = data['mode']
    with _lock:
        if _fan() is None:
            raise ValueError('未检测到受支持的风扇')
        if not _has_fan_permission():
            raise RuntimeError('无法免交互获得风扇调节权限')
        # Ensure the normal automatic cooling control remains available.
        _automatic_pwm()
        old_mode, old_target = _mode, _target
        if mode == 'manual':
            percent = data.get('percent')
            if isinstance(percent, bool) or not isinstance(percent, int) or not 30 <= percent <= 100:
                raise ValueError('手动风扇速度必须是 30 到 100 的整数')
            _mode, _target = mode, percent
            if not _apply_manual():
                _mode, _target = old_mode, old_target
                raise RuntimeError(_error or '风扇调节失败')
        else:
            _restore_automatic()
            _mode = 'auto'
            temp = _temperature_or_none()
            _safety_override = temp is None or temp >= 70
            _error = ''
        try:
            _persist()
        except OSError as exc:
            _mode, _target = old_mode, old_target
            if old_mode == 'auto':
                try:
                    _restore_automatic()
                except Exception:
                    pass
            raise RuntimeError('无法保存风扇设置：' + str(exc)) from exc
        _wake.set()
        return read_fan()


#!/usr/bin/env python3
"""Conservative, one-shot fan boosts without disabling Linux thermal control."""
from pathlib import Path
import struct
import subprocess
import threading

HWMON = Path('/sys/class/hwmon')
THERMAL = Path('/sys/class/thermal')
LEVEL_FILES = (Path('/proc/device-tree/cooling_fan/cooling-levels'),
               Path('/sys/firmware/devicetree/base/cooling_fan/cooling-levels'))
_lock = threading.Lock()
_mode = 'auto'


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
    raise RuntimeError('无法读取 CPU 温度，已停止手动调速')


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


def _has_sudo():
    try:
        return subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=2).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def read_fan():
    fan = _fan()
    data = {'available': fan is not None, 'controllable': False, 'mode': _mode,
            'percent': None, 'rpm': None, 'error': '', 'notice': ''}
    if fan is None:
        data['error'] = '未检测到受支持的树莓派 PWM 风扇'
        return data
    try:
        data['percent'] = round(int((fan / 'pwm1').read_text()) * 100 / 255)
        try:
            data['rpm'] = int((fan / 'fan1_input').read_text())
        except (OSError, ValueError):
            pass
        _automatic_pwm()
        _cpu_temperature()
        data['controllable'] = _has_sudo()
        if not data['controllable']:
            data['error'] = '无法免交互获得风扇调节权限'
        elif _mode == 'manual':
            data['notice'] = '手动设置为一次性调节，内核温控可能随温度变化覆盖；显示为当前占空比。'
        else:
            data['notice'] = '系统温控保持开启；温度较高时，恢复自动可能要等下一次温控调节。'
    except (OSError, RuntimeError, ValueError) as exc:
        data['error'] = str(exc)[:180]
    return data


def _write_pwm(fan, value):
    path = fan / 'pwm1'
    # Arguments are not interpreted by a shell; only the detected pwmfan path is used.
    proc = subprocess.run(['sudo', '-n', 'tee', str(path)], input=str(value) + '\n',
                          text=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3)
    if proc.returncode != 0:
        raise RuntimeError('写入风扇控制失败，请检查设备权限')


def set_fan(data):
    global _mode
    if not isinstance(data, dict) or data.get('mode') not in ('auto', 'manual'):
        raise ValueError('请选择自动或手动模式')
    mode = data['mode']
    with _lock:
        fan = _fan()
        if fan is None:
            raise ValueError('未检测到受支持的风扇')
        try:
            temp = _cpu_temperature()
            state, auto_pwm = _automatic_pwm()
            current = int((fan / 'pwm1').read_text())
            if not 0 <= current <= 255:
                raise RuntimeError('风扇状态异常')
            if not _has_sudo():
                raise RuntimeError('无法免交互获得风扇调节权限')
            if mode == 'manual':
                percent = data.get('percent')
                if isinstance(percent, bool) or not isinstance(percent, int) or not 30 <= percent <= 100:
                    raise ValueError('手动风扇速度必须是 30 到 100 的整数')
                desired = max(round(percent * 255 / 100), auto_pwm)
                if temp >= 60:
                    desired = max(desired, round(0.6 * 255))
                if temp >= 75:
                    desired = 255
                # Only lower the fan when there is ample thermal headroom and
                # the kernel has not requested any cooling. Never disable thermal control.
                if (temp >= 50 or state != 0) and desired < current:
                    raise ValueError('当前温度或自动冷却档位较高，只能提高风扇速度；降温后可调低')
            else:
                # When cool, restore the kernel's current state immediately.
                # Otherwise leave any higher PWM in place until the kernel changes it.
                desired = auto_pwm if temp < 50 and state == 0 else max(current, auto_pwm)
                if temp >= 75:
                    desired = 255
            if desired < current:
                # Recheck immediately before any reduction in case the kernel
                # requested cooling during the decision above.
                latest_temp = _cpu_temperature()
                latest_state, latest_auto = _automatic_pwm()
                if latest_temp >= 50 or latest_state != 0:
                    raise ValueError('温度或自动冷却档位刚刚升高，已取消降速')
                desired = max(desired, latest_auto)
            _write_pwm(fan, desired)
            _mode = mode
            return read_fan()
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('风扇调节超时') from exc
        except OSError as exc:
            raise RuntimeError('风扇调节失败：' + str(exc)) from exc


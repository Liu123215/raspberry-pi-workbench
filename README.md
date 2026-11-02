# 树莓派个人工作台

一个运行在树莓派上的个人工作台：通过电脑或手机浏览设备状态，查看网络信息，按设备支持情况调节风扇，并设置网站状态检查和定时拍照任务。

## 功能

- 查看 CPU 温度、内存和存储使用情况、运行时间及相机服务状态。
- 查看网络接口、IPv4 / IPv6 地址、网关、MAC 地址、累计流量和当前上传、下载速率。链路协商速率不是互联网测速结果。
- 查看兼容风扇的转速并设置手动速度。工作台在手动模式下持续维持目标速度；为保护设备，温度异常或温度读数不可用时会强制全速。可随时切回自动温控。
- 检查并安装树莓派系统软件包更新；从本仓库检查和更新工作台程序。安装更新前请确认，并保持设备供电及网络连接。
- 按间隔检查一个网站是否能访问，并记录状态变化；这不是网页内容更新监控。
- 配合独立的光影相机服务定时拍照、查看最近照片。两项自动任务默认关闭，须由用户启用。

## 隐私与访问

服务默认监听所有网络接口的 8092 端口，首次启动会生成随机访问码，保存在 `~/.local/share/pi-workbench/access-token`，文件仅供当前用户读取。打开页面后输入访问码，工作台使用浏览器 Cookie 保存登录状态。

**工作台使用 HTTP，没有传输加密。请只在可信局域网中使用，不要将端口转发至公网，也不要分享访问码。** 网站检查会访问你设置的地址；只有信任的用户才应获得访问码。

本工作台可以链接独立的 [光影相机](https://github.com/Liu123215/raspberry-pi-ccd-camera)。工作台的访问码不会保护该相机服务；该相机默认也不提供登录验证，不要将其端口暴露到不可信网络。

## 环境要求

- 运行 Raspberry Pi OS 的树莓派，需有 Python 3 和 systemd 用户服务；通过浏览器访问，无需树莓派桌面环境。
- 网络详情依赖系统的 `ip` 命令；部分无线网卡可能无法报告链路协商速率。
- 风扇功能依赖设备及内核暴露兼容的 `pwm-fan` 接口，手动调节需要非交互式 `sudo` 权限。不支持时页面会显示原因。不同设备尚未逐一测试。
- 系统软件包更新适用于使用 `apt` 的系统，且需要非交互式 `sudo`。工作台更新需能访问 GitHub。
- 相机和定时拍照功能需要单独安装和配置光影相机，其余功能可独立使用。

## 安装与启动

在树莓派的终端中执行：

```bash
sudo apt update
sudo apt install -y git python3 iproute2
git clone https://github.com/Liu123215/raspberry-pi-workbench.git ~/pi-workbench
cd ~/pi-workbench
python3 backend.py
```

终端中按 `Ctrl+C` 可以停止服务。首次启动后，另开终端读取访问码：

```bash
cat ~/.local/share/pi-workbench/access-token
hostname -I
```

在树莓派浏览器打开 `http://127.0.0.1:8092/`，或在同一局域网的其他设备上打开 `http://树莓派的局域网IP:8092/`，输入访问码。访问码应妥善保管。

## 可选：后台用户服务

以下示例假设项目位于 `~/pi-workbench`，以当前用户身份运行：

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/pi-workbench.service <<'EOF'
[Unit]
Description=Personal Raspberry Pi Workbench
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/pi-workbench
ExecStart=/usr/bin/python3 %h/pi-workbench/backend.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now pi-workbench.service
```

```bash
systemctl --user status pi-workbench.service
journalctl --user -u pi-workbench.service -f
systemctl --user restart pi-workbench.service
systemctl --user stop pi-workbench.service
```

用户服务启动时机取决于系统和登录设置；仅执行 `enable` 并不保证无人登录时服务会随设备启动。

## 更新和风扇

在工作台的“软件更新”区域，可分别检查系统和工作台更新，确认后再安装。系统更新使用 `apt-get upgrade`，可能需要较长时间或提示重启；工作台更新从本仓库 `main` 分支的同一个提交下载程序文件、备份旧文件并重启工作台。GitHub 不可访问、权限不足或软件包管理器被占用时，操作会显示错误，不会伪装成成功。

风扇的百分比是 PWM 控制值，不是实际转速百分比。手动模式会持续维持目标占空比；当 CPU 温度达到安全阈值或温度读数不可用时，保护机制会临时要求全速，降温后恢复目标。系统热保护不会关闭。转速为 0 RPM 在低温自动停转时可能是正常现象。更换设备后应确认硬件和散热正常，再使用调节功能。

## 常见问题

- **页面打不开：**检查工作台服务、树莓派和手机是否处于可互访的网络，以及 IP 与 8092 端口是否正确。
- **无法登录：**在树莓派上重新查看 `~/.local/share/pi-workbench/access-token`，不要把访问码发给他人。
- **看不到风扇或无法调速：**检查设备是否具有兼容风扇、系统是否暴露相应接口，以及当前用户是否具有非交互式 `sudo` 权限。
- **定时拍照失败：**确认光影相机已单独安装并能通过本机 8091 端口访问；查看工作台页面中的任务结果和日志。
- **更新失败：**检查网络、GitHub 或软件源是否可访问，查看页面日志及 systemd 日志；不要在更新期间断电。

## 文件

- `backend.py`：网页服务、设备状态和自动任务。
- `index.html`：手机和电脑浏览器界面。
- `fan_control.py`：兼容风扇的状态读取与控制。
- `update_service.py`：系统和工作台更新。


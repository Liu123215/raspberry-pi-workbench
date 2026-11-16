# Raspberry Pi Personal Workbench

[中文说明](README.md) · English

## Preview

These screenshots show the version 1.0 interface with simulated device data; the version 2.0 interface may differ.

![Desktop interface with simulated device data](docs/screenshots/desktop.png)

![Mobile interface with simulated device data](docs/screenshots/mobile.png)

## What's new in 2.0

- Browse workbench files, downloads and camera folders; create folders, rename, upload (up to 5 MB per file), download and move items to the system trash. Symbolic links are not shown. Trash requires `gio`.
- Storage analysis, camera and workbench service status and logs, and shutdown/restart controls, subject to system authorization. Power actions are blocked during updates or when recording status cannot be confirmed.
- Status history, alerts, connectivity checks and an on-demand download speed test that consumes network data.
- Editable web shortcuts and scheduled backups of a user directory to a separate, writable mounted filesystem. Backups are full snapshots; the workbench must be running and the destination mounted. Monitor available space and verify the results.

The 1.0 one-click updater can upgrade to 2.0: the backend includes fallback copies of the new modules when the older updater has not installed them yet. Future updates install the full set of files. Alternatively, use the manual upgrade below and keep a backup.

For an installation at `~/pi-workbench`, stop recordings and other active tasks, then run these commands on the Raspberry Pi:

```bash
cp -a ~/pi-workbench ~/pi-workbench-backup-$(date +%Y%m%d-%H%M%S)
stage=$(mktemp -d)
git clone --depth 1 https://github.com/Liu123215/raspberry-pi-workbench.git "$stage/source"
cp "$stage/source/"{workbench_extra.py,extras_v2.py,fan_control.py,update_service.py,index.html,backend.py} ~/pi-workbench/
systemctl --user restart pi-workbench.service
systemctl --user status pi-workbench.service --no-pager
```

For a manually started instance, stop the old process and run `python3 ~/pi-workbench/backend.py` instead of the `systemctl` commands. Keep the backup for rollback; remove the temporary download directory after checking that the new version works.

A Raspberry Pi dashboard for device and network details, compatible fan control, optional camera access, and scheduled tasks. Open it locally or through an SSH tunnel from another device. The interface supports switching between Chinese and English.

> **Looking for the camera app?** The workbench integrates with the separately installed [CCD Camera](https://github.com/Liu123215/raspberry-pi-ccd-camera); installing this repository alone does not install a camera application.

## Contents

- [Features](#features) and [compatibility](#compatibility-and-scope)
- [Access and privacy](#privacy-and-access)
- [Requirements](#requirements) and [installation](#install-and-start)
- [Background service](#optional-run-in-the-background)
- [Using the workbench](#using-the-workbench)
- [Updates and fan control](#updates-and-fan-control)
- [Troubleshooting and FAQ](#troubleshooting-and-faq)
- [Files, tests, and license](#files)

## Features

- View CPU temperature, memory and storage usage, uptime, and the status of the separate camera service.
- Start, restart, or stop the CCD camera service; stop an active recording first.
- Take photos from the dashboard and view system load, reboot status, services, and resource-intensive processes.
- Refresh a diagnostics view of key service states and the processes using the most CPU.
- Manually release reclaimable system memory caches without closing programs or deleting user files.
- View interfaces, IPv4 and IPv6 addresses, gateways, MAC address, cumulative traffic, and current upload/download rates. Wi-Fi link rates and signal strength are shown when available. These values are not an internet bandwidth test.
- View and control a compatible `pwm-fan`. Manual mode continuously maintains a target PWM setting and preserves it across workbench service restarts. The target is temporarily overridden to request full speed if the CPU reaches 70°C or the temperature cannot be read; the system's thermal protections remain enabled. You can return to automatic control.
- Check and install system package updates and update the workbench from this repository.
- Schedule availability checks for one website; record state changes. This checks whether the site is reachable, not whether its content has changed.
- Schedule photos and browse recent images through the separately installed CCD Camera. Both scheduled tasks are disabled by default.

## Compatibility and scope

| Component | Requirements or limitations |
| --- | --- |
| Core dashboard | Intended for Raspberry Pi OS; requires Python 3 and `iproute2` for network details. The documentation does not yet contain device-by-device hardware validation. |
| Fan control | Requires a compatible `pwm-fan` kernel interface and a separately installed restricted helper; support depends on the device. |
| Camera and scheduled photos | Require the separately installed and configured [CCD Camera](https://github.com/Liu123215/raspberry-pi-ccd-camera). |
| System updates and background service | System updates require APT and non-interactive `sudo`; the background-service example uses systemd user services. |

## Privacy and access

Version 2.0 listens on the Raspberry Pi loopback interface on port 8092 by default. On first startup it generates a random access code in `~/.local/share/pi-workbench/access-token`, readable only by the service user. Enter the code on the login page; the browser stores a session cookie. On another computer, run `ssh -L 8092:127.0.0.1:8092 -L 8091:127.0.0.1:8091 user@pi-address`, keep the connection open, and visit `http://127.0.0.1:8092/` in that computer's browser. The second forwarded port enables the camera link; the independent camera service is not protected by the workbench access code.

**The workbench uses unencrypted HTTP. Use it only on a trusted local network, do not forward its port to the internet, and do not share the access code.** Anyone with the code can use the dashboard's controls, including updates and fan settings.

The [CCD Camera](https://github.com/Liu123215/raspberry-pi-ccd-camera) is a separate application. The workbench access code does not protect the camera service, which has no login by default. Do not expose it to an untrusted network.

## Requirements

- A Raspberry Pi running Raspberry Pi OS with Python 3 and systemd user services. A desktop is optional; remote browser access requires an SSH tunnel.
- `iproute2` for network information; `iw` can provide supported Wi-Fi link data. Some interfaces do not report every value. `gio` (provided by `glib2.0-bin` on Raspberry Pi OS) is needed for the trash action.
- A compatible `pwm-fan` interface and the separately installed restricted fan helper. Other devices have not all been tested; unsupported controls report the reason.
- A system using APT and non-interactive `sudo` for system package updates. Workbench updates require Git and access to GitHub.
- The separately installed CCD Camera for camera status, gallery, and scheduled capture. The remaining functions can run without it.

## Install and start

On the Raspberry Pi:

```bash
sudo apt update
sudo apt install -y git python3 iproute2 iw glib2.0-bin
git clone https://github.com/Liu123215/raspberry-pi-workbench.git ~/pi-workbench
cd ~/pi-workbench
python3 backend.py
```

To enable fan control, review `pi-workbench-fan` and the installer, then open another terminal and run `sudo sh install-fan-helper.sh` from the project directory. Installation requires your administrator password and grants the current user passwordless access only to the dedicated fan helper, not general passwordless sudo. Workbench self-updates do not replace the root-owned helper.

To enable memory-cache release, review `pi-workbench-memory` and its installer, then run `sudo sh install-memory-helper.sh` from the project directory. This fixed operation releases reclaimable kernel caches; it does not guarantee a large decrease in memory usage and may temporarily slow file access.

Press `Ctrl+C` to stop a foreground server. After the first startup, open another terminal and retrieve your access code and local network address:

```bash
cat ~/.local/share/pi-workbench/access-token
hostname -I
```

On the Raspberry Pi, open `http://127.0.0.1:8092/`. On another computer, first establish the SSH tunnel described above and open `http://127.0.0.1:8092/` in its browser. Keep the code private. Use the language control in the interface to switch between Chinese and English.

## Optional: run in the background

This example assumes the project is in `~/pi-workbench` and runs as the current user. If `python3 backend.py` is already running in the foreground, stop it with **Ctrl+C** first so that it releases port 8092.

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

Manage it with:

```bash
systemctl --user status pi-workbench.service
journalctl --user -u pi-workbench.service -f
systemctl --user restart pi-workbench.service
systemctl --user stop pi-workbench.service
```

When user services start depends on the system and login configuration. Enabling the service does not by itself guarantee startup when no user is logged in. Persistent manual fan control also depends on the workbench service running; kernel thermal management remains enabled.

## Updates and fan control

Use the **Software Update** area to check system or workbench updates, then confirm an installation. System installation uses `apt-get upgrade`, may take time, and may indicate that a reboot is required. System installation is blocked when enabled Debian sources from different releases are detected; inspect the sources before proceeding. Keep the device powered and connected throughout an update.

Workbench updates fetch the six application files from the same commit on this repository's `main` branch, back up the previous files, and restart the user service. Network failures, missing permissions, or an occupied package manager are reported as errors. Updates install the current `main` branch rather than a pinned release; back up your files before updating. The updater does not replace the optional root-owned helpers.

Fan percentages represent PWM duty cycle, not a guarantee of physical RPM. Manual mode continually reapplies the selected target while the service is running. The live PWM can briefly differ when the kernel adjusts the fan. At 70°C or if the temperature reading fails, the workbench attempts to request full speed; after the condition clears, it resumes the target. A 0 RPM reading can be normal when an automatically controlled fan is stopped at a low temperature.

## Using the workbench

### File manager and storage

Select **Workbench files**, **Camera album**, or **Downloads** to browse `~/Workbench Files`, `~/Pictures/CCD Camera`, or `~/Downloads`. Create folders, rename and upload/download files, or move an item to the system trash. A single upload is limited to **5 MiB**, directories display at most 1,000 sorted entries, and symbolic links are deliberately hidden and cannot be opened. The camera album and Downloads directories must exist before they can be browsed. Deletion requires `gio` and sends items to the system trash rather than permanently erasing them. Storage analysis counts the three supported roots, not every directory on the disk.

### Backups

1. Connect and mount a separate writable disk or filesystem. Confirm the destination folder already exists and has sufficient free space.
2. In the backup panel, enter an existing source folder **inside your home directory** and the existing destination folder. Neither folder may contain the other, and the destination must be on a different filesystem.
3. Set the interval in hours (1–720), enable scheduled backups and save. You can also run a backup manually.
4. Check the displayed result and inspect a copied file on the destination. Each run is a full snapshot, so monitor disk capacity. A failed copy can leave a `.partial` directory to inspect and remove manually if appropriate.

Scheduled backups run only while the workbench is running and the destination remains mounted. A temporary filesystem such as `/dev/shm` is useful for testing but is not durable backup storage. A copy on the same SD card does not protect against that card failing.

### Network, tasks, and alerts

The traffic chart measures interface traffic; it is not an internet speed test. The on-demand speed test downloads approximately 2 MB from a third-party endpoint and depends on internet access. The connectivity test measures a TCP connection to `1.1.1.1:53`; a failure can be caused by local or upstream blocking. Status history is sampled while the service runs. The network-disconnected indicator is based on the presence of an IP address and does not prove internet connectivity.

Website checks and scheduled photos are disabled by default. Website checks report availability, not a change in page content. Scheduled photos require the separate camera service. Stopping the workbench also stops its scheduled tasks.

### Power and services

The service panel shows recent status and logs. Camera start/stop/restart controls depend on the installed user service; power controls require system authorization. Stop an active recording and wait for workbench-managed updates to finish first. The update guard does not guarantee detection of package updates started outside the workbench; check independently before shutting down.

## Troubleshooting and FAQ

Start with `systemctl --user status pi-workbench.service --no-pager` and `journalctl --user -u pi-workbench.service -n 100 --no-pager` when installed as a user service. If running in a terminal, inspect that terminal instead. Do not include your access code, private paths, network addresses, or photo contents in public issue reports.

### The page does not open from my computer or phone

Version 2.0 binds to the Pi's loopback address: browsing directly to `http://<pi-ip>:8092/` from another device will not reach it. Verify the service on the Pi and establish the SSH tunnel in [Privacy and access](#privacy-and-access) **on the device running the browser**. Keep the SSH session open, then use `http://127.0.0.1:8092/`. A phone needs an SSH client capable of local port forwarding. Check for a local port conflict if the tunnel reports `Address already in use`. On the Pi, `ss -lnt | grep 8092` can show whether the service is listening.

### The login page rejects my code

On the Pi, read `cat ~/.local/share/pi-workbench/access-token` and paste it without extra spaces. Use the account running the service: another user has a different home directory and access code. If the page remains at login, allow browser cookies for the local address. Never post the code in an issue.

### The user service fails to start or keeps restarting

Check its status and journal above. If the error says the port is already in use, stop the duplicate foreground instance or other service before restarting. Confirm the `WorkingDirectory` and `ExecStart` paths in the unit match your installation and that all six application files are present. Run `python3 -m py_compile backend.py fan_control.py update_service.py workbench_extra.py extras_v2.py` in the installation directory to identify syntax errors. If `systemctl --user` cannot connect, use a proper user session and check the distribution's systemd setup.

### The service does not start after a reboot

`systemctl --user enable` does not guarantee the user manager starts before login on every installation. Log in first and check the service status. If you need unattended startup, configure and test your system's user-manager and lingering policy; do not assume it is enabled automatically.

### Fan controls are unavailable or the speed changes

The device must expose a compatible `pwm-fan` and the restricted helper must be installed. Inspect the panel message and verify the helper installation described above. Percentage is a PWM request, not a measured RPM; manual targets are limited to 30%–100%. Manual mode requires the workbench to keep running. At 70°C or when temperature is unavailable, the workbench attempts full speed until the condition clears; hardware and kernel controls may also affect actual behavior. Different fan hardware can lack supported controls or an RPM sensor.

### Memory cleanup has no effect or fails

Install the optional restricted memory helper as described above, then check the displayed result. Only reclaimable caches are requested; applications are not forcibly closed. Linux may refill caches, and the available-memory figure may not change much. Cleanup can temporarily reduce disk performance.

### File operations fail or my file is missing

Confirm you selected one of the three permitted roots, that the directory exists, and the service user has the necessary filesystem permissions. Symlinks are hidden by design; listings are capped at 1,000 entries and uploads at 5 MiB. An existing target name cannot be overwritten. Moving to trash requires `gio`, a working desktop trash location, and write access; check the displayed error and the service journal.

### A backup does not run or stops partway through

Confirm the workbench is running, scheduling is enabled, the source and destination exist, and the destination is mounted, writable, on another filesystem, and has enough free space. Check the last error and last success time. The source must be inside the user's home and cannot contain or be contained by the destination. Inspect `.partial` directories left by failed copies before removing them; they are not completed backups. Verify restoration by opening copied files.

### The camera link or scheduled photo fails

Install and configure [CCD Camera](https://github.com/Liu123215/raspberry-pi-ccd-camera) separately. Check `systemctl --user status ccd-camera.service --no-pager` and its journal. When accessing the workbench over SSH, forward port 8091 as well as 8092 as shown above; a browser's `127.0.0.1` points to the browser device. The camera service is independent and is not secured by the workbench access code. Its availability depends on the camera, service and permissions.

### Shutdown or restart is blocked

Wait for the workbench update to finish and stop recording. If the camera service is active but its status cannot be read, inspect its service and local port 8091 before retrying. If authorization fails, review system policy and the service user's privileges. Independently check for package updates launched outside the workbench before shutting down.

### System updates fail or report conflicting sources

Read the update log and inspect the configured APT sources. Mixed Debian release sources are blocked by a preflight check; verify the correct sources for your installed OS before making any change. The update also requires non-interactive `sudo`; expiring authorization or an occupied package manager can cause failure. Avoid forcibly removing lock files or interrupting an active package operation. Consult the system's APT logs and distribution instructions if package repair is needed.

### Workbench updates fail or the interface is stale

Check that Git is installed, the Pi can reach GitHub, the installation directory is writable by the service user, and the systemd user service is available. Inspect the update result and journal, then retry after fixing the cause. The updater requires the systemd user service, downloads application files from `main`, and schedules a service restart; refresh the browser afterwards. If running only in the foreground, use the manual upgrade above. From an old 1.0 installation, the compatibility fallback permits the first four-file update; subsequent 2.0 updates install both additional modules. Keep a separate backup before an upgrade.

### How do I report a reproducible issue?

Open a GitHub issue with the Pi model, Raspberry Pi OS version and architecture, steps to reproduce, expected and actual results, and relevant **redacted** logs. Mention whether you run the service manually or via systemd and whether you access it locally or through an SSH tunnel. Hardware support varies, so include the fan or camera model when relevant.

## Files

- `backend.py` — HTTP service, device status, and scheduled tasks.
- `index.html` — responsive dashboard interface.
- `fan_control.py` — compatible fan monitoring and control.
- `workbench_extra.py` — file, storage, service and power operations.
- `extras_v2.py` — history, backups, shortcuts and network tools.
- `pi-workbench-fan` / `install-fan-helper.sh` — restricted fan helper and installer.
- `update_service.py` — system and workbench updates.
- `README.md` / `README.en.md` — Chinese and English documentation.

## Tests

Run `python3 -B -m unittest discover -s tests -v` from the repository directory. These tests do not require Raspberry Pi hardware; hardware-specific features still need testing on a device.

## License

This project is licensed under the [MIT License](LICENSE).

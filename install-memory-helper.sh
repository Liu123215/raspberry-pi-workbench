#!/bin/sh
set -eu
[ "$(id -u)" -eq 0 ] || { echo 'Run with sudo.' >&2; exit 1; }
user_name=${SUDO_USER:-}
case "$user_name" in ''|*[!a-zA-Z0-9_-]*|[0-9-]*) echo 'Invalid user.' >&2; exit 1;; esac
[ "$(id -u "$user_name")" -ne 0 ] || exit 1
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
src="$source_dir/pi-workbench-memory"
[ -f "$src" ] && [ ! -L "$src" ] || exit 1
for dir in /usr /usr/local /etc/sudoers.d; do
  [ -d "$dir" ] && [ ! -L "$dir" ] && [ "$(stat -c %u "$dir")" -eq 0 ] && [ -z "$(find "$dir" -maxdepth 0 -perm /022 -print)" ] || exit 1
done
if [ ! -e /usr/local/libexec ]; then install -d -o root -g root -m 755 /usr/local/libexec; fi
[ ! -L /usr/local/libexec ] && [ "$(stat -c %u /usr/local/libexec)" -eq 0 ] && [ -z "$(find /usr/local/libexec -maxdepth 0 -perm /022 -print)" ] || exit 1
helper=/usr/local/libexec/pi-workbench-memory
rule=/etc/sudoers.d/pi-workbench-memory-$user_name
tmp_helper=$(mktemp /usr/local/libexec/.pi-workbench-memory.XXXXXXXX)
tmp_rule=$(mktemp /etc/sudoers.d/.pi-workbench-memory.XXXXXXXX)
trap 'rm -f -- "$tmp_helper" "$tmp_rule"' EXIT HUP INT TERM
install -o root -g root -m 755 "$src" "$tmp_helper"
printf '%s ALL=(root) NOPASSWD: %s ""\n' "$user_name" "$helper" > "$tmp_rule"
chown root:root "$tmp_rule"; chmod 440 "$tmp_rule"
visudo -cf "$tmp_rule" >/dev/null
if [ -e "$helper" ] || [ -L "$helper" ]; then
  [ ! -L "$helper" ] && [ "$(stat -c %u:%g:%a "$helper")" = 0:0:755 ] && cmp -s "$tmp_helper" "$helper" || exit 1
else
  ln "$tmp_helper" "$helper"
fi
if [ -e "$rule" ] || [ -L "$rule" ]; then
  [ ! -L "$rule" ] && [ "$(stat -c %u:%g:%a "$rule")" = 0:0:440 ] && cmp -s "$tmp_rule" "$rule" || exit 1
else
  ln "$tmp_rule" "$rule"
fi
echo 'Installed restricted memory-cache helper.'


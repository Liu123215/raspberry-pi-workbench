#!/bin/sh
# Review pi-workbench-fan before running: sudo sh install-fan-helper.sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo 'Run this installer with sudo as the intended workbench user.' >&2
    exit 1
fi
user_name=${SUDO_USER:-}
case "$user_name" in
    ''|*[!a-zA-Z0-9_-]*|[0-9-]*) echo 'Invalid or missing SUDO_USER.' >&2; exit 1 ;;
esac
if ! user_id=$(id -u -- "$user_name" 2>/dev/null) || [ "$user_id" -eq 0 ]; then
    echo 'The workbench user must be an existing non-root account.' >&2
    exit 1
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
source_file="$script_dir/pi-workbench-fan"
helper_dir=/usr/local/libexec
helper="$helper_dir/pi-workbench-fan"
sudoers_dir=/etc/sudoers.d
sudoers_file="$sudoers_dir/pi-workbench-fan-$user_name"
if [ ! -f "$source_file" ] || [ -L "$source_file" ]; then
    echo 'The helper source must be a regular file beside this installer.' >&2
    exit 1
fi
/usr/bin/python3 -I -c 'import ast,sys; ast.parse(open(sys.argv[1], encoding="utf-8").read())' "$source_file"
command -v visudo >/dev/null 2>&1 || { echo 'visudo is required.' >&2; exit 1; }

for dir in /usr /usr/local "$sudoers_dir"; do
    if [ ! -d "$dir" ] || [ -L "$dir" ] || [ "$(stat -c %u "$dir")" -ne 0 ] ||
       [ -n "$(find "$dir" -maxdepth 0 -perm /022 -print)" ]; then
        echo "Unsafe system directory: $dir" >&2
        exit 1
    fi
done
if [ ! -e "$helper_dir" ]; then
    install -d -o root -g root -m 755 "$helper_dir"
fi
if [ ! -d "$helper_dir" ] || [ -L "$helper_dir" ] || [ "$(stat -c %u "$helper_dir")" -ne 0 ] ||
   [ -n "$(find "$helper_dir" -maxdepth 0 -perm /022 -print)" ]; then
    echo "Unsafe system directory: $helper_dir" >&2
    exit 1
fi

tmp_helper=$(mktemp "$helper_dir/.pi-workbench-fan.XXXXXXXX")
tmp_rule=$(mktemp "$sudoers_dir/.pi-workbench-fan.XXXXXXXX")
trap 'rm -f -- "$tmp_helper" "$tmp_rule"' EXIT HUP INT TERM
install -o root -g root -m 755 "$source_file" "$tmp_helper"
printf '%s ALL=(root) NOPASSWD: %s probe, %s set *\n' "$user_name" "$helper" "$helper" > "$tmp_rule"
chown root:root "$tmp_rule"
chmod 440 "$tmp_rule"
visudo -cf "$tmp_rule" >/dev/null

if [ -e "$helper" ] || [ -L "$helper" ]; then
    if [ -L "$helper" ] || [ ! -f "$helper" ] || [ "$(stat -c %u:%g:%a "$helper")" != '0:0:755' ] || ! cmp -s "$tmp_helper" "$helper"; then
        echo "Conflicting helper already exists: $helper" >&2
        exit 1
    fi
else
    ln -- "$tmp_helper" "$helper" || { echo 'Could not install helper safely.' >&2; exit 1; }
fi

if [ -e "$sudoers_file" ] || [ -L "$sudoers_file" ]; then
    if [ -L "$sudoers_file" ] || [ ! -f "$sudoers_file" ] || [ "$(stat -c %u:%g:%a "$sudoers_file")" != '0:0:440' ] || ! cmp -s "$tmp_rule" "$sudoers_file"; then
        echo "Conflicting sudoers rule already exists: $sudoers_file" >&2
        exit 1
    fi
else
    ln -- "$tmp_rule" "$sudoers_file" || { echo 'Could not install sudoers rule safely.' >&2; exit 1; }
fi
echo "Installed the restricted fan helper for $user_name."


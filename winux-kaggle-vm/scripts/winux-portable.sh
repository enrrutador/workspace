#!/usr/bin/env bash
# winux-portable.sh — launcher portable (proot, sin QEMU, sin KVM)
# Uso:
#   bash winux-portable.sh                  → shell dentro de Winux portable
#   bash winux-portable.sh --apt update     → apt dentro (con workarounds Kaggle)
#   bash winux-portable.sh --apps           → lista apps KDE disponibles
#   bash winux-portable.sh <cmd...>         → ejecuta comando dentro
set -eu
DIR="${WINUX_PORTABLE_DIR:-/kaggle/working/vmdata/winux-portable}"
ROOTFS="$DIR/rootfs"
[ -d "$ROOTFS/bin" ] || { echo "ERROR: no existe $ROOTFS. Corre antes winux-portable-build.sh"; exit 1; }

if ! grep -q "8.8.8.8" "$ROOTFS/etc/resolv.conf" 2>/dev/null; then
  printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' > "$ROOTFS/etc/resolv.conf"
fi

proot_base() {
  proot -R "$ROOTFS" \
    -b /dev -b /proc -b /sys -b /tmp \
    -b /kaggle -b /kaggle/working \
    -w / "$@"
}

case "${1:-}" in
  --apt)   shift; proot_base /bin/sh -c "apt-get -o APT::Sandbox::User=root -o Acquire::ForceIPv4=true $*" ;;
  --apps)  proot_base /bin/sh -c 'ls /usr/bin | grep -E "^(dolphin|konsole|firefox|kate|gwenview|okular)" || ls /usr/bin | head -n 40' ;;
  --os)    proot_base /bin/sh -c 'cat /etc/os-release | head -n 3' ;;
  "")      proot_base /bin/bash ;;
  *)       proot_base "$@" ;;
esac

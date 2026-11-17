#!/usr/bin/env bash
# SO-app v0.1 — userland nativo con proot (prioriza velocidad + compatibilidad)
# Uso:
#   bash soapp.sh                  → shell dentro del SO-app
#   bash soapp.sh --chrome         → Chrome headless prueba
#   bash soapp.sh --opencode       → opencode --version dentro
#   bash soapp.sh --apt update     → apt dentro (con workarounds Kaggle)
# Requisitos: proot instalado (apt-get install proot), rootfs en DIR/rootfs
set -eu
DIR="${SOAPP_DIR:-/kaggle/working/vmdata/proot}"
ROOTFS="$DIR/rootfs"

[ -d "$ROOTFS/bin" ] || { echo "ERROR: no existe $ROOTFS (falta rootfs)"; exit 1; }

# DNS público: el de Docker (127.0.0.11) cuelga apt dentro de proot; IPv6 también.
if ! grep -q "8.8.8.8" "$ROOTFS/etc/resolv.conf" 2>/dev/null; then
  printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' > "$ROOTFS/etc/resolv.conf"
fi

proot_base() {
  proot -R "$ROOTFS" \
    -b /dev -b /proc -b /sys -b /tmp \
    -b /tools -b /kaggle \
    -w / "$@"
}

case "${1:-}" in
  --apt)      shift; proot_base /bin/sh -c "apt-get -o APT::Sandbox::User=root -o Acquire::ForceIPv4=true $*" ;;
  --chrome)   proot_base /opt/google/chrome/chrome --version --no-sandbox ;;
  --headless) proot_base /opt/google/chrome/chrome --headless --no-sandbox --disable-gpu --dump-dom about:blank 2>/dev/null ;;
  --opencode) proot_base /tools/node/bin/opencode --version ;;
  --node)     proot_base /tools/node/bin/node --version ;;
  "")         proot_base /bin/bash ;;
  *)          proot_base "$@" ;;
esac

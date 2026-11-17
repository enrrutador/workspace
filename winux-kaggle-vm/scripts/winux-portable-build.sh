#!/usr/bin/env bash
# winux-portable-build.sh — ISO Winux (6.6GB) -> rootfs portable proot (sin QEMU/KVM)
# La ISO NO se versiona. La base portable (base.tar.gz) se crea UNA vez.
# Los cambios diarios van en upper.tar.gz (MBs, no GBs).
#
# Uso:
#   ISO_URL="https://sourceforge.net/projects/windows-linux/files/latest/download" \
#     bash winux-portable-build.sh
# Env: DIR (def /kaggle/working/vmdata/winux-portable), ISO_URL, CLEAN (def 1)
set -eu
DIR="${DIR:-/kaggle/working/vmdata/winux-portable}"
ISO_URL="${ISO_URL:-https://sourceforge.net/projects/windows-linux/files/latest/download}"
CLEAN="${CLEAN:-1}"
ISO="$DIR/winux.iso"
SQDIR="$DIR/iso-extract"
ROOTFS="$DIR/rootfs"
BASE="$DIR/base.tar.gz"

mkdir -p "$DIR"; cd "$DIR"
echo "== [0] deps =="
command -v proot >/dev/null || { apt-get update -qq; apt-get install -y -qq proot squashfs-tools p7zip-full; }
command -v unsquashfs >/dev/null || { apt-get update -qq; apt-get install -y -qq squashfs-tools; }
command -v 7z >/dev/null || { apt-get update -qq; apt-get install -y -qq p7zip-full; }
proot --version | head -n 1; unsquashfs -version 2>&1 | head -n 1

echo "== [1] ISO (resume, ~6.6GB, ~3 min) =="
if [ ! -f "$ISO" ]; then
  curl -sSL -C - -o "$ISO" --retry 3 "$ISO_URL"
else
  echo "ISO presente, reanudo/verifico:"
  curl -sSL -C - -o "$ISO" --retry 3 "$ISO_URL" || true
fi
ls -lh "$ISO"

echo "== [2] localizar filesystem.squashfs dentro de la ISO (sin montar) =="
7z l "$ISO" 2>/dev/null | grep -i -E "squashfs|filesystem" | head -n 20 || true

echo "== [3] extraer solo casper/filesystem.squashfs =="
mkdir -p "$SQDIR"
# Intenta las 2 rutas típicas de live Ubuntu: casper/ y pool/. Solo queremos el squashfs.
if [ ! -f "$SQDIR/casper/filesystem.squashfs" ] && [ ! -f "$SQDIR/filesystem.squashfs" ]; then
  7z x "$ISO" -o"$SQDIR" 'casper/filesystem.squashfs' -y 2>&1 | tail -n 5 || true
  # Fallback: extrae cualquier *.squashfs si la ruta cambió (Winux 11.26.10 noble)
  if [ ! -f "$SQDIR/casper/filesystem.squashfs" ]; then
    echo "-- ruta casper/ no encontrada, buscando cualquier squashfs --"
    7z x "$ISO" -o"$SQDIR" '*.squashfs' -y 2>&1 | tail -n 5 || true
    find "$SQDIR" -name "*.squashfs" -ls
  fi
fi
SQFS="$(find "$SQDIR" -name "filesystem.squashfs" | head -n 1)"
[ -n "${SQFS:-}" ] || { echo "ERROR: no se encontró filesystem.squashfs. Rutas:"; find "$SQDIR" -maxdepth 4 | head -n 40; exit 1; }
ls -lh "$SQFS"

echo "== [4] unsquashfs -> rootfs (una vez, ~5-10 min) =="
if [ ! -d "$ROOTFS/bin" ]; then
  rm -rf "$ROOTFS"
  unsquashfs -f -d "$ROOTFS" "$SQFS"
else
  echo "rootfs existente, reuso"
fi
ls "$ROOTFS/bin/bash"

echo "== [5] limpieza portable (CLEAN=$CLEAN) =="
if [ "$CLEAN" = "1" ]; then
  rm -rf "$ROOTFS/var/cache/apt/archives/"*.deb "$ROOTFS/var/log/"* "$ROOTFS/tmp/"* \
         "$ROOTFS/var/tmp/"* "$ROOTFS/usr/share/doc/"* 2>/dev/null || true
  # snaps: en live pesan GBs y no sirven en proot sin systemd
  rm -rf "$ROOTFS/snap" "$ROOTFS/var/lib/snapd" 2>/dev/null || true
  # kernels/initrd duplicados del live (proot usa el kernel del host, no estos)
  rm -rf "$ROOTFS/boot/"* 2>/dev/null || true
  mkdir -p "$ROOTFS/boot"
fi
printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' > "$ROOTFS/etc/resolv.conf"
du -sh "$ROOTFS" || true

echo "== [6] base.tar.gz (una vez, la capa portable read-only) =="
if [ ! -f "$BASE" ]; then
  tar -czf "$BASE" -C "$DIR" rootfs
else
  echo "base.tar.gz existente, reuso"
fi
ls -lh "$BASE"
python3 - "$DIR" <<'EOF'
import hashlib, json, time
from pathlib import Path
d = Path(__import__('sys').argv[1])
files = {}
for name in ["base.tar.gz"]:
    p = d / name
    if not p.exists(): continue
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(8*1024*1024), b""): h.update(ch)
    files[name] = {"size": p.stat().st_size, "sha256": h.hexdigest()}
man = {"kind": "winux-portable-base", "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": files}
(d / "manifest-base.json").write_text(json.dumps(man, indent=2))
print(json.dumps(man, indent=2)[:600])
EOF

echo "== [7] prueba proot =="
proot -R "$ROOTFS" -b /dev -b /proc -b /sys -w / /bin/bash -c 'cat /etc/os-release | head -n 2; echo BUILD_OK'
echo
echo "Listo. Launcher: bash $(dirname "$0")/winux-portable.sh"
echo "NOTA: portable = userland + apps KDE (terminal, dolphin, firefox). Plasma completo (login/KWin/systemd) NO corre en proot: usa openbox + VNC si quieres escritorio."

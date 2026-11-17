#!/usr/bin/env bash
# winux-portable-persist.sh — persistencia por DELTAS (MBs, no 15GB)
# Base (base.tar.gz, GBs) se sube UNA vez. Diario solo upper.tar.gz (home+etc+opt+paquetes).
# Uso:
#   bash winux-portable-persist.sh upload [DIR] ["notas"]
#   bash winux-portable-persist.sh download [DIR]
set -eu
MODE="${1:-}"; DIR="${2:-/kaggle/working/vmdata/winux-portable}"; NOTES="${3:-checkpoint winux portable}"
DATASET="marceloate/winux-portable-data"
ROOTFS="$DIR/rootfs"

if [ "$MODE" = "upload" ]; then
  [ -d "$ROOTFS/bin" ] || { echo "ERROR: sin rootfs en $ROOTFS"; exit 1; }
  STAGE=/tmp/winux-portable-stage; rm -rf "$STAGE"; mkdir -p "$STAGE"
  echo "== upper: home+etc+opt+root+usr/local + packages.txt =="
  proot -R "$ROOTFS" -b /dev -b /proc -b /sys -w / /bin/sh -c 'apt-mark showmanual > /tmp/packages.txt' 2>/dev/null || true
  cp "$ROOTFS/tmp/packages.txt" "$STAGE/packages.txt" 2>/dev/null || apt-mark showmanual > "$STAGE/packages.txt" || true
  tar -czf "$STAGE/upper.tar.gz" -C "$ROOTFS" home etc opt root usr/local var/lib/dpkg/status 2>/dev/null || \
    tar -czf "$STAGE/upper.tar.gz" -C "$ROOTFS" home etc opt root usr/local 2>/dev/null
  ls -lh "$STAGE/"
  python3 - "$STAGE" <<'EOF'
import hashlib, json, time, sys
from pathlib import Path
stage = Path(sys.argv[1])
files = {}
for p in sorted(stage.iterdir()):
    if not p.is_file(): continue
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(8*1024*1024), b""): h.update(ch)
    files[p.name] = {"size": p.stat().st_size, "sha256": h.hexdigest()}
(stage / "manifest.json").write_text(json.dumps({"kind": "winux-portable-upper", "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": files}, indent=2))
print(json.dumps(files, indent=2)[:800])
EOF
  echo "== base (solo si cambió, una vez) =="
  if [ -f "$DIR/base.tar.gz" ]; then cp "$DIR/base.tar.gz" "$STAGE/" 2>/dev/null || true; fi
  [ -f "$DIR/manifest-base.json" ] && cp "$DIR/manifest-base.json" "$STAGE/" || true
  python3 - "$DATASET" "$STAGE" "$NOTES" <<'EOF'
import sys
import kagglehub as kh
ds, stage, notes = sys.argv[1], sys.argv[2], sys.argv[3]
kh.dataset_upload(ds, stage, version_notes=notes)
print("UPLOAD OK:", ds)
EOF
  rm -rf "$STAGE"
  echo "Checkpoint publicado en $DATASET (upper = MBs)"
elif [ "$MODE" = "download" ]; then
  mkdir -p "$DIR"
  python3 - "$DATASET" <<'EOF'
import sys
import kagglehub as kh
print("DOWNLOAD OK:", kh.dataset_download(sys.argv[1], force_download=True))
EOF
  SRC=/kaggle/input/datasets/marceloate/winux-portable-data
  [ -f "$SRC/manifest.json" ] || { echo "ERROR: dataset sin manifest.json (primera vez: haz build + upload)"; exit 1; }
  if [ ! -d "$ROOTFS/bin" ] && [ -f "$SRC/base.tar.gz" ]; then
    echo "== restaurando base =="
    tar -xzf "$SRC/base.tar.gz" -C "$DIR"
  fi
  if [ -f "$SRC/upper.tar.gz" ]; then
    echo "== aplicando upper (deltas) =="
    tar -xzf "$SRC/upper.tar.gz" -C "$ROOTFS"
  fi
  printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' > "$ROOTFS/etc/resolv.conf"
  if [ -f "$SRC/packages.txt" ]; then
    echo "== reinstalando paquetes apt guardados =="
    cp "$SRC/packages.txt" "$ROOTFS/tmp/packages-restore.txt"
    proot -R "$ROOTFS" -b /dev -b /proc -b /sys -w / /bin/sh -c 'apt-get -o APT::Sandbox::User=root -o Acquire::ForceIPv4=true update -qq; xargs -a /tmp/packages-restore.txt apt-get -o APT::Sandbox::User=root -o Acquire::ForceIPv4=true install -y -qq' || echo "(aviso: algún paquete no reinstaló, sigue con upper)"
  fi
  echo "Rehidratado en $DIR"
else
  echo "Uso: $0 upload|download [DIR] [notas]"; exit 1
fi

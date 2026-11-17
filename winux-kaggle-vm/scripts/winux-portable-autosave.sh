#!/usr/bin/env bash
# winux-portable-autosave.sh — autoguardado por detección de cambios (2 niveles)
# Nivel 1 LOCAL (barato, frecuente): tar upper a $DIR/autosave/ si hay cambios.
# Nivel 2 REMOTO (caro, throttled): kagglehub upload solo si hay cambios + cooldown.
#
# Uso:
#   bash winux-portable-autosave.sh start [DIR]     → daemon en fondo, log en DIR/autosave.log
#   bash winux-portable-autosave.sh stop [DIR]      → frena + checkpoint final remoto
#   bash winux-portable-autosave.sh status [DIR]    → estado
#   bash winux-portable-autosave.sh once [DIR]      → una pasada (para cron/manual)
# Env: LOCAL_EVERY (def 120s), REMOTE_COOLDOWN (def 900s), DATASET (def marceloate/winux-portable-data)
set -eu
CMD="${1:-}"; DIR="${2:-/kaggle/working/vmdata/winux-portable}"
LOCAL_EVERY="${LOCAL_EVERY:-120}"
REMOTE_COOLDOWN="${REMOTE_COOLDOWN:-900}"
DATASET="${DATASET:-marceloate/winux-portable-data}"
ROOTFS="$DIR/rootfs"; AUTO="$DIR/autosave"; PIDF="$DIR/autosave.pid"
WATCH="home etc opt root usr/local var/lib/dpkg/status tmp/packages.txt"

mkdir -p "$AUTO"

fingerprint() {
  # Huella barata: paths + sizes + mtimes de lo que sí persiste (no todo /usr)
  ( cd "$ROOTFS" 2>/dev/null && find home etc opt root usr/local var/lib/dpkg/status -type f -printf '%p %s %T@\n' 2>/dev/null | sort | sha256sum | cut -d' ' -f1 ) || echo "norootfs"
}

snapshot_local() {
  STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
  proot -R "$ROOTFS" -b /dev -b /proc -b /sys -w / /bin/sh -c 'apt-mark showmanual > /tmp/packages.txt' 2>/dev/null || true
  cp "$ROOTFS/tmp/packages.txt" "$AUTO/packages.txt" 2>/dev/null || true
  tar -czf "$AUTO/upper-$STAMP.tar.gz" -C "$ROOTFS" home etc opt root usr/local var/lib/dpkg/status 2>/dev/null || \
    tar -czf "$AUTO/upper-$STAMP.tar.gz" -C "$ROOTFS" home etc opt root usr/local 2>/dev/null || return 1
  cp "$AUTO/packages.txt" "$AUTO/packages-$STAMP.txt" 2>/dev/null || true
  # conserva solo los últimos 5 snapshots locales (el rootfs base ya está en base.tar.gz)
  ls -t "$AUTO"/upper-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
  echo "$STAMP"
}

remote_upload() {
  NOTES="${1:-autosave winux portable}"
  STAGE=/tmp/winux-portable-stage; rm -rf "$STAGE"; mkdir -p "$STAGE"
  LATEST="$(ls -t "$AUTO"/upper-*.tar.gz 2>/dev/null | head -n 1 || true)"
  [ -n "$LATEST" ] || { echo "sin snapshot local, nada que subir"; return 0; }
  cp "$LATEST" "$STAGE/upper.tar.gz"
  cp "$AUTO/packages.txt" "$STAGE/packages.txt" 2>/dev/null || true
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
print("stage:", json.dumps(files)[:400])
EOF
  python3 - "$DATASET" "$STAGE" "$NOTES" <<'EOF'
import sys
import kagglehub as kh
ds, stage, notes = sys.argv[1], sys.argv[2], sys.argv[3]
kh.dataset_upload(ds, stage, version_notes=notes)
print("UPLOAD OK:", ds)
EOF
  date +%s > "$AUTO/.last-remote"
  rm -rf "$STAGE"
}

daemon_loop() {
  echo $$ > "$PIDF"
  trap 'echo "$(date -u +%FT%TZ) SIGTERM: checkpoint final"; snapshot_local >/dev/null 2>&1; remote_upload "autosave final winux portable" >/dev/null 2>&1 || true; rm -f "$PIDF"; exit 0' TERM INT
  echo "$(date -u +%FT%TZ) autosave start DIR=$DIR LOCAL_EVERY=${LOCAL_EVERY}s REMOTE_COOLDOWN=${REMOTE_COOLDOWN}s" >> "$AUTO/autosave.log"
  LAST_FP="$(fingerprint)"; echo "$LAST_FP" > "$AUTO/.last-fp"
  LAST_LOCAL=$(date +%s); echo "$LAST_LOCAL" > "$AUTO/.last-local" 2>/dev/null || true
  [ -f "$AUTO/.last-remote" ] || echo 0 > "$AUTO/.last-remote"
  while true; do
    sleep "$LOCAL_EVERY"
    [ -d "$ROOTFS/bin" ] || continue
    FP="$(fingerprint)"
    if [ "$FP" = "$(cat "$AUTO/.last-fp" 2>/dev/null)" ]; then continue; fi
    echo "$(date -u +%FT%TZ) cambios detectados $FP" >> "$AUTO/autosave.log"
    if STAMP="$(snapshot_local 2>>"$AUTO/autosave.log")"; then
      echo "$FP" > "$AUTO/.last-fp"; date +%s > "$AUTO/.last-local"
      echo "$(date -u +%FT%TZ) snapshot local $STAMP" >> "$AUTO/autosave.log"
      NOW=$(date +%s); LAST_R=$(cat "$AUTO/.last-remote")
      if [ $((NOW - LAST_R)) -ge "$REMOTE_COOLDOWN" ]; then
        echo "$(date -u +%FT%TZ) subiendo remoto (cooldown ok)" >> "$AUTO/autosave.log"
        remote_upload "autosave winux portable $STAMP" >> "$AUTO/autosave.log" 2>&1 || echo "$(date -u +%FT%TZ) upload falló (reintenta próximo ciclo)" >> "$AUTO/autosave.log"
      else
        echo "$(date -u +%FT%TZ) remoto en cooldown ($((REMOTE_COOLDOWN - (NOW - LAST_R))))s, solo local" >> "$AUTO/autosave.log"
      fi
    fi
  done
}

case "$CMD" in
  start)
    [ -d "$ROOTFS/bin" ] || { echo "ERROR: sin rootfs en $ROOTFS (corre build primero)"; exit 1; }
    if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "ya corre (pid $(cat "$PIDF"))"; exit 0; fi
    nohup bash "$0" _daemon "$DIR" >> "$AUTO/autosave.log" 2>&1 &
    echo $! > "$PIDF"; echo "autosave corriendo (pid $(cat "$PIDF")), log $AUTO/autosave.log"
    ;;
  _daemon) daemon_loop ;;
  stop)
    if [ -f "$PIDF" ]; then kill -TERM "$(cat "$PIDF")" 2>/dev/null || true; sleep 3; rm -f "$PIDF"; echo "frenado + checkpoint final intentado (ver log)"; tail -n 5 "$AUTO/autosave.log" 2>/dev/null || true
    else echo "no corría"; fi
    ;;
  status)
    if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "corriendo (pid $(cat "$PIDF"))"; else echo "detenido"; fi
    echo "last-fp: $(cat "$AUTO/.last-fp" 2>/dev/null || echo -)"; echo "snapshots: $(ls "$AUTO"/upper-*.tar.gz 2>/dev/null | wc -l)"; tail -n 5 "$AUTO/autosave.log" 2>/dev/null || true
    ;;
  once)
    [ -d "$ROOTFS/bin" ] || { echo "ERROR: sin rootfs"; exit 1; }
    FP="$(fingerprint)"; [ "$FP" = "$(cat "$AUTO/.last-fp" 2>/dev/null || echo -)" ] && { echo "sin cambios, nada que hacer"; exit 0; }
    STAMP="$(snapshot_local)"; echo "$FP" > "$AUTO/.last-fp"; echo "snapshot local $STAMP"
    NOW=$(date +%s); LAST_R=$(cat "$AUTO/.last-remote" 2>/dev/null || echo 0)
    if [ $((NOW - LAST_R)) -ge "$REMOTE_COOLDOWN" ]; then remote_upload "checkpoint manual $STAMP"; else echo "remoto en cooldown, solo local"; fi
    ;;
  *) echo "Uso: $0 start|stop|status|once [DIR]"; exit 1 ;;
esac

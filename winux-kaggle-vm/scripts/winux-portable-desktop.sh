#!/usr/bin/env bash
# winux-portable-desktop.sh — escritorio estilo Win11 (openbox+tint2) por VNC + noVNC web
# Uso: bash winux-portable-desktop.sh start|stop|status [DIR]
# Puertos localhost: 5900 VNC, 6080 noVNC web (para el túnel del teléfono).
set -eu
CMD="${1:-}"; DIR="${2:-/kaggle/working/vmdata/winux-portable}"
ROOTFS="$DIR/rootfs"
VNC_PORT=5900; WEB_PORT=6080; DISP=":0"

prootx() { proot -R "$ROOTFS" -b /dev -b /proc -b /sys -b /tmp -b /kaggle -b /kaggle/working -w /root env DISPLAY=$DISP "$@"; }

case "$CMD" in
  start)
    [ -d "$ROOTFS/bin" ] || { echo "ERROR: sin rootfs"; exit 1; }
    "$0" stop "$DIR" >/dev/null 2>&1 || true
    mkdir -p "$ROOTFS/root/.vnc" "$ROOTFS/root/.config/openbox" "$ROOTFS/root/.config/tint2"
    # xstartup: fondo + openbox + barra inferior centrada estilo Win11
    cat > "$ROOTFS/root/.vnc/xstartup" <<'EOF'
#!/bin/sh
xsetroot -solid "#0078D4"
openbox &
tint2 &
EOF
    chmod +x "$ROOTFS/root/.vnc/xstartup"
    # tint2: barra inferior centrada, reloj + lista de ventanas
    cat > "$ROOTFS/root/.config/tint2/tint2rc" <<'EOF'
panel_position = bottom center horizontal
panel_size = 60% 40
panel_margin = 0 0 8
panel_background_id = 1
wm_menu = 1
taskbar_mode = single_desktop
taskbar_padding = 6 4 6
task_icon_asb = 100 0 0
task_text = 0
task_icon_size = 24
task_centered = 1
task_padding = 6 2
task_background_id = 2
task_active_background_id = 3
clock = 1
clock_font = sans 10
clock_padding = 6 2
background_id = 1
background_color = #101010 85
border_width = 0
background_id = 2
background_color = #000000 0
border_width = 0
background_id = 3
background_color = #ffffff 25
border_width = 0
border_radius = 6
EOF
    echo "== Xvnc $DISP =="
    setsid proot -R "$ROOTFS" -b /dev -b /proc -b /sys -b /tmp -b /kaggle -b /kaggle/working -w /root \
      /usr/bin/Xvnc $DISP -geometry 1280x800 -depth 24 -rfbport $VNC_PORT -SecurityTypes None -localhost yes \
      < /dev/null > /tmp/xvnc.log 2>&1 &
    echo $! > /tmp/xvnc.pid
    sleep 4
    echo "== openbox + tint2 =="
    prootx /usr/bin/openbox > /tmp/openbox.log 2>&1 &
    sleep 2
    # tint2 SIN -c: lee /root/.config/tint2/tint2rc por defecto (-c falla en esta build)
    prootx /usr/bin/tint2 > /tmp/tint2.log 2>&1 &
    sleep 2
    prootx /usr/bin/xsetroot -solid "#0078D4" > /dev/null 2>&1 || true
    echo "== noVNC web :$WEB_PORT =="
    WEB=$(proot -R "$ROOTFS" -b /dev -b /proc -b /sys -w / /bin/sh -c 'ls -d /usr/share/novnc 2>/dev/null' || echo /usr/share/novnc)
    setsid proot -R "$ROOTFS" -b /dev -b /proc -b /sys -w / /usr/bin/websockify --web="$WEB" 127.0.0.1:$WEB_PORT 127.0.0.1:$VNC_PORT \
      < /dev/null > /tmp/websockify.log 2>&1 &
    echo $! > /tmp/websockify.pid
    sleep 3
    (command -v ss >/dev/null && ss -ltn 2>/dev/null | grep -E ":(5900|6080)" ) || python3 -c "
import socket
for p in (5900, 6080):
    s = socket.create_connection(('127.0.0.1', p), timeout=3); print('puerto', p, 'OK'); s.close()"
    echo "DESKTOP_UP (VNC 5900, web 6080)"
    ;;
  stop)
    for f in /tmp/xvnc.pid /tmp/websockify.pid; do
      [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null || true; rm -f "$f"
    done
    pkill -x Xvnc 2>/dev/null || true; pkill -x openbox 2>/dev/null || true
    pkill -x tint2 2>/dev/null || true
    echo "desktop frenado"
    ;;
  status)
    for p in Xvnc openbox tint2; do pgrep -x "$p" >/dev/null && echo "$p: corre" || echo "$p: caído"; done
    { [ -f /tmp/websockify.pid ] && kill -0 "$(cat /tmp/websockify.pid)" 2>/dev/null && echo "websockify: corre"; } || echo "websockify: caído"
    ;;
  *) echo "Uso: $0 start|stop|status [DIR]"; exit 1 ;;
esac

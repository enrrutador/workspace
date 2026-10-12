# SO-app v0.1 — SO como app (userland nativo con proot)

Prioridad: **velocidad + compatibilidad**. En Kaggle no hay KVM
(sin `/dev/kvm`, sin VMX/SVM) y Docker daemon no existe:
solo QEMU/TCG (~6.5x overhead) o userland nativo con `proot`
(~1.9x, arranque en 0.014s).

## Qué es

Un Ubuntu 22.04 userland que corre **nativo** sobre el kernel del host
vía `proot`, con Chrome real, Node y OpenCode adentro. Es el
" clic al icono y adentro está todo" sin emular hardware.

## Archivos

| Archivo | Qué |
|---|---|
| `soapp.sh` | Launcher: shell, `--chrome`, `--headless`, `--opencode`, `--node`, `--apt ...` |
| `soapp-kaggle.ipynb` | Cuaderno para correrlo en Kaggle desde cero |

## Uso (Kaggle)

1. Subir `soapp-kaggle.ipynb` como notebook Kaggle (o copiar sus celdas).
2. Celda 1: instala `proot`, baja `ubuntu-base-22.04` (29MB), extrae,
   fija DNS y apt, instala `curl` + `ca-certificates`.
3. Celda 2: baja Chrome stable (~137MB), lo instala (los errores dpkg
   de iconos/systemd se ignoran: el binario corre igual), verifica
   Node/OpenCode del host por bind.
4. Celda 3: verificación + tiempos.

Tiempos medidos 2026-10-09: arranque proot 0.014s, `apt update` ~18s,
Chrome headless OK, rootfs final ~1.2GB en `/kaggle/working/vmdata/proot`.

## Trucos Kaggle (ya aplicados en script y cuaderno)

- `/etc/resolv.conf` con 8.8.8.8 (el DNS Docker 127.0.0.11 cuelga apt en proot)
- `apt -o APT::Sandbox::User=root -o Acquire::ForceIPv4=true` (IPv6 cuelga)
- Chrome con `--no-sandbox` (sin SYS_ADMIN no hay sandbox de Chrome)

## Persistencia

- Dir vivo: `/kaggle/working/vmdata/proot/rootfs` (sobrevive restart de kernel).
- Backup: `tar -czf soapp-rootfs.tar.gz rootfs` → Kaggle Dataset
  (mismo patrón que `winux-kaggle-vm/scripts/persist_*.sh`, pero 1.2GB vs 15GB).
- Rehidratar: bajar tar del dataset, extraer, `bash soapp.sh`.

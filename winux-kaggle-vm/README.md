# winux-kaggle-vm

Laboratorio reproducible: **Winux 11** (Linux con estética Windows 11, base Ubuntu 24.04 LTS + KDE Plasma)
virtualizado con **QEMU/TCG** dentro de un Kaggle Notebook, con OpenCode como herramienta de desarrollo.

Origen: investigación `investigacion-windows-kaggle/` — KVM confirmado NO viable en Kaggle
(sin VMX/SVM, sin `/dev/kvm`, sin `CAP_SYS_ADMIN`). Único acelerador funcional: `TCG` (~6.5x overhead CPU medido).

## Qué persiste acá y qué no

| Artefacto | Dónde vive | Por qué |
|---|---|---|
| Scripts, docs, bootstrap | Este repo (GitHub) | Código pequeño, versionable |
| ISO Winux (~6.3GB) | **NO** en GitHub — se re-descarga de SourceForge (~3 min) | Límite GitHub 100MB/archivo; la ISO es reproducible desde URL |
| `winux.qcow2` (60GB) | **NO** en GitHub — scratch `/tmp/vmtest` + snapshot opcional en Kaggle Dataset | Efímero por diseño; cada sesión rehidrata |
| Estado OpenCode/sesiones | Kaggle Dataset `opencode-cloud-state` (flow existente) | Ya funciona vía workstation v9 |

**Este repo no mantiene viva la VM** (Kaggle recicla el contenedor: se pierde `/tmp`
y los paquetes apt — verificado 2026-10-06/07; un recycle nocturno borró ISO+qcow2 de 13GB).
Persistencia real por capas:

1. **Código** → este repo.
2. **Disco instalado (`winux.qcow2` + `OVMF_VARS.fd` + `manifest.json`)** → Kaggle Dataset
   versionado `marceloate/winux-kaggle-vm-data` (round-trip upload/download verificado).
   - Checkpoint: `scripts/persist_upload.sh [DIR] ["notas"]` (VM **apagada**, verifica sha256)
   - Rehidratar: `scripts/persist_download.sh [DIR]` (baja + verifica sha256)
   - Disciplina: checkpoint SIEMPRE antes de cerrar/dejar idle largo. El upload de ~15GB tarda; lanzarlo con tiempo.
3. **ISO (6.3GB)** → NO se persiste (re-descarga ~3 min desde SourceForge).
4. **QEMU/apt** → se reinstala en ~1 min por bootstrap (`fase4` lo hace solo si falta).
5. **Estado OpenCode/sesiones** → Kaggle Dataset `opencode-cloud-state` (flow workstation v9).

Límites: `/kaggle/working` tiene 19GB — el qcow2 instalado (~13-15GB) entra justo; vigilar espacio.

## Uso

```bash
# 1. Diagnóstico (read-only, no toca nada)
bash scripts/fase1_diagnostico.sh

# 2. Smoke test TCG con Alpine (valida emulación + mide overhead)
bash scripts/fase2_qemu_tcg_test.sh

# 3. Winux 11 real (descarga ISO si falta, crea disco, bootea, VNC localhost)
ISO_URL="https://sourceforge.net/projects/windows-linux/files/latest/download" \
  bash scripts/fase4_winux_vm.sh
```

Acceso a la VM: **solo localhost** — VNC `127.0.0.1:0`, SSH guest `127.0.0.1:2222`.
Nunca exponer a Internet.

## Estructura

- `scripts/fase1_diagnostico.sh` — diagnóstico read-only del runtime
- `scripts/fase2_qemu_tcg_test.sh` — QEMU mínimo + benchmark host vs guest
- `scripts/fase3_windows_vm.sh` — plantilla Windows real bajo TCG (referencia)
- `scripts/fase4_winux_vm.sh` — Winux 11: re-descarga ISO, disco virtio, boot TCG, VNC local
- `docs/` — notas de sesiones, métricas, compliance

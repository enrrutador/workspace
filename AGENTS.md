# Notas para opencode en este workspace (Kaggle)

## El entorno restaura y borra .git de repos anidados

Al reiniciar la sesión, el entorno restaura el workspace desde snapshot y
los `.git` de carpetas anidadas (ej. `Marce-agi/`) se pierden; la identidad
git global también se resetea. Además, si `.git` no existe, un `git add/commit`
con workdir en la carpeta anidada termina comutando en el repo RAÍZ
(`/...workspace`), que es sólo un snapshot local.

### Arranque de sesión — bootstrap del repo Marce-agi

```bash
cd Marce-agi
[ -d .git ] || { git init -b main; git remote add origin https://github.com/enrrutador/Marce-agi.git; git fetch origin main; git reset --hard origin/main; }
GHID=$(gh api user --jq '.id'); GHLOGIN=$(gh api user --jq '.login')
git config --global user.name "$GHLOGIN"
git config --global user.email "${GHID}+${GHLOGIN}@users.noreply.github.com"
gh auth setup-git
git push -u origin main 2>&1 | tail -3   # verificar que el alcanzó el remoto VISIBLE en github api
```

- El primer push tras re-init necesita `-u origin main` (sin upstream el push falla en silencio bred `tail`).
- Verificar siempre con `gh api repos/enrrutador/Marce-agi/commits/main --jq '.sha[0:7]'` que el commit vive en GitHub (el remoto es la única persistencia real entre sesiones).

## Convenciones del proyecto

- Documentación y commits inmediatos de cada avance (decisión de Marce).
- Tests del kernel: correr `python3 -m pytest tests -q` desde `Marce-agi/first_model/`
  (desde la raíz del repo no resuelve los imports).
- El stream de eventos del cerebro es `first_model/state/cerebro.jsonl`
  (contrato del frontend observador pendiente).

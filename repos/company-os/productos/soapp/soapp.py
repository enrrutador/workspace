import os, re, shutil, socket, subprocess, tarfile, time, urllib.request

DIR = "/kaggle/working/vmdata/proot"
ROOTFS = os.path.join(DIR, "rootfs")
PORT = 4096
APT_O = ["-o", "APT::Sandbox::User=root", "-o", "Acquire::ForceIPv4=true"]
os.environ["LC_ALL"] = "C"
os.environ["LANG"] = "C"


def log(m=""):
    print(m, flush=True)


def run(cmd, cwd="/", check=False):
    log("$ " + " ".join(cmd))
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, errors="replace")
    for line in p.stdout:
        print(line, end="", flush=True)
    p.wait()
    if check and p.returncode != 0:
        raise RuntimeError("fallo rc=%d: %s" % (p.returncode, " ".join(cmd)))
    return p.returncode


def cap(cmd, timeout=120):
    p = subprocess.run(cmd, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def proot(*args):
    return ["proot", "-R", ROOTFS, "-b", "/dev", "-b", "/proc",
            "-b", "/sys", "-w", "/"] + list(args)


def download(url, dest, label):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000000:
        log("%s: existente, reuso (%dMB)" % (label, os.path.getsize(dest) // 1048576))
        return
    log("%s: descargando..." % label)
    req = urllib.request.Request(url, headers={"User-Agent": "soapp/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        got, last = 0, 0
        while True:
            chunk = r.read(4 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if got - last > 20 * 1024 * 1024:
                extra = ("/%dMB" % (total // 1048576)) if total else ""
                log("  ...%dMB%s" % (got // 1048576, extra))
                last = got
    log("%s: OK (%dMB)" % (label, os.path.getsize(dest) // 1048576))


def port_open(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=2).close()
        return True
    except OSError:
        return False


os.makedirs(DIR, exist_ok=True)

log("=== [1/5] proot ===")
if shutil.which("proot") is None:
    log("instalando proot...")
    run(["apt-get", "update"], check=True)
    run(["apt-get", "install", "-y", "proot"], check=True)
run(["proot", "--version"])

log("=== [2/5] rootfs ===")
if not os.path.isdir(os.path.join(ROOTFS, "bin")):
    download("https://cdimage.ubuntu.com/ubuntu-base/releases/22.04/release/ubuntu-base-22.04-base-amd64.tar.gz",
             os.path.join(DIR, "ubuntu-base.tar.gz"), "ubuntu-base")
    os.makedirs(ROOTFS, exist_ok=True)
    log("extrayendo...")
    with tarfile.open(os.path.join(DIR, "ubuntu-base.tar.gz")) as t:
        t.extractall(ROOTFS)
    log("rootfs OK")
else:
    log("rootfs existente, reuso")
if run(proot("/bin/sh", "-c", "command -v curl")) != 0:
    log("apt update + curl (1-2 min)...")
    run(proot("/usr/bin/apt-get", *(APT_O + ["update"])), check=True)
    run(proot("/usr/bin/apt-get", *(APT_O + ["install", "-y", "curl", "ca-certificates"])), check=True)
else:
    log("curl existente, reuso")
run(proot("/bin/sh", "-c", "command -v curl && echo CURL_OK"), check=True)

log("=== [3/5] Chrome ===")
CHROME = "LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu /opt/google/chrome/chrome --version --no-sandbox"
if run(proot("/bin/sh", "-c", CHROME)) == 0:
    log("Chrome existente, reuso")
else:
    download("https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb",
             "/tmp/chrome.deb", "Chrome")
    log("desempaquetando Chrome...")
    run(proot("/usr/bin/dpkg", "-i", "--force-all", "/tmp/chrome.deb"))
    log("extrayendo librerias directo de los .deb...")
    rc, out = cap(proot("/usr/bin/apt-cache", "depends", "--recurse", "--no-recommends",
                         "--no-suggests", "--no-conflicts", "--no-breaks",
                         "--no-replaces", "--no-enhances", "google-chrome-stable"))
    deps = sorted({m.group(1) for m in re.finditer(r"^\s*\|?Depends:\s*(\S+)", out, re.M)
                   if not m.group(1).startswith("<")})
    log("deps: %d" % len(deps))
    os.makedirs("/tmp/debs", exist_ok=True)
    for i, p in enumerate(deps, 1):
        try:
            r = subprocess.run(proot("/usr/bin/apt-get", *(APT_O + ["download", p])),
                               cwd="/tmp/debs", capture_output=True, text=True,
                               errors="replace", timeout=120)
            if r.returncode != 0:
                log("no-dl: %s" % p)
        except subprocess.TimeoutExpired:
            log("timeout-dl: %s" % p)
        if i % 20 == 0:
            log("  %d/%d pkgs..." % (i, len(deps)))
    run(proot("/bin/sh", "-c",
              'for d in /tmp/debs/*.deb; do [ -f "$d" ] && dpkg-deb -x "$d" /; done; ldconfig; echo EXTRACT_OK'),
        check=True)
    run(proot("/bin/sh", "-c", CHROME), check=True)

log("=== [4/5] opencode web ===")
OCBIN = next((c for c in ["/tools/node/bin/opencode", shutil.which("opencode")]
              if c and os.access(c, os.X_OK)), "")
if not OCBIN:
    log("instalando opencode (unos min)...")
    run(["npm", "install", "-g", "opencode-ai"])
    OCBIN = shutil.which("opencode") or ""
if not OCBIN or not os.access(OCBIN, os.X_OK):
    raise SystemExit("ERROR: sin binario opencode")
log("opencode: " + OCBIN)
run(["pkill", "-f", "opencode web --hostname 127.0.0.1 --port %d" % PORT])
time.sleep(1)
srv = open("/tmp/opencode-web.log", "a")
subprocess.Popen([OCBIN, "web", "--hostname", "127.0.0.1", "--port", str(PORT)],
                 cwd="/kaggle/working", stdout=srv, stderr=subprocess.STDOUT,
                 start_new_session=True)
log("esperando puerto...")
ok = False
for _ in range(30):
    if port_open(PORT):
        ok = True
        break
    time.sleep(2)
if ok:
    log("OPENCODE_UP")
else:
    run(["tail", "-10", "/tmp/opencode-web.log"])
    raise SystemExit("ERROR: opencode no levanto")

log("=== [5/5] tunel ===")
CFD = "/tmp/cloudflared"
if not os.access(CFD, os.X_OK):
    download("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
             CFD, "cloudflared")
    os.chmod(CFD, 0o755)
else:
    log("cloudflared existente, reuso")
run(["pkill", "-f", "cloudflared tunnel --url http://127.0.0.1:%d" % PORT])
time.sleep(1)
tlog = open("/tmp/tunnel.log", "a")
subprocess.Popen([CFD, "tunnel", "--url", "http://127.0.0.1:%d" % PORT],
                 stdout=tlog, stderr=subprocess.STDOUT, start_new_session=True)
URL = ""
for _ in range(45):
    with open("/tmp/tunnel.log", errors="replace") as f:
        m = re.search(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com", f.read())
    if m:
        URL = m.group(0)
        break
    time.sleep(2)
if URL:
    log("TUNEL: " + URL)
else:
    run(["tail", "-15", "/tmp/tunnel.log"])
    raise SystemExit("ERROR: sin URL de tunel")
log("Listo. Los servicios siguen corriendo aunque la celda termine. El link es publico: no lo compartas.")

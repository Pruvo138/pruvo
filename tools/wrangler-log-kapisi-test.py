#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/wrangler-log-kapisi-test.py — `tools/wrangler-log-kapisi.py` HERMETIK kabul bataryasi.

VAKALAR (gecici dizinde sahte agac; kapi `--kok` ile olcer, AG/wrangler YOK):
  V1 py env'siz `subprocess.run(["npx","wrangler",...])`        -> KIRMIZI (LOG_ACIK=1)
  V2 py `env=wrangler_ortami()` (yardimci import)               -> YESIL  (CAGRI=1 KAPALI=1)
  V3 liste elemani `npx`,`wrangler@4` + yardimci fonksiyon donusu -> YAKALANIR (CAGRI=2 ACIK=2)
  V4 JS `spawnSync("npx",["wrangler@4",...])` env'siz            -> KIRMIZI
  V5 JS `env: {...process.env, WRANGLER_WRITE_LOGS: "false"}`    -> YESIL
  V6 wrangler GECMEYEN subprocess (+ "wrangler ..." mesaji, `wrangler-log-*.py` yolu) -> SAYILMAZ
  V7 sarmalayici parametresi: `kos(komut)` <- `kos(["npx","wrangler",...])` -> KIRMIZI
  V8 mevcut env korunarak `env=wrangler_ortami(ortam)`            -> YESIL
  V9 iki kaynakli env parametresi, biri log ACIK (d1-sync EPERM kolu deseni) -> KIRMIZI
  V11 yerel yardimci + literal sabit (`tools/d1-sync.py` deseni, IKIZ tanim) -> YESIL
  V10 GERCEK depo: rc=0, LOG_ACIK=0, WRANGLER_CAGRI >= 16
MUTANTLAR (izole kopya; mutant capasi tutmazsa mutant OLCULEMEDI = basarisiz):
  M1 tarayicidan JS kolu cikar                 -> V4 kirmizi olmali
  M2 yardimcinin kaynak sabiti `"false"`->`"true"` -> V2 kirmizi olmali
  M3 parametre -> cagri yeri cozumu kapali      -> V7 kirmizi olmali
  M4 yerel (d1-sync deseni) literal `"false"`->`"true"` -> V11 kirmizi olmali
Cikti: `VAKA=n/n MUTANT=m/m`; hepsi gecerse rc=0. Gecici dizinler `finally`de silinir.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "wrangler-log-kapisi.py")
OZET = re.compile(r"WRANGLER_CAGRI=(\d+) LOG_KAPALI=(\d+) LOG_ACIK=(\d+)")

PY_YARDIMCI = "from wrangler_ortam import wrangler_ortami\n"
FIKSTUR = {
    "V1": {"tools/a.py": 'import subprocess\nsubprocess.run(["npx", "wrangler", "d1", "execute"], cwd="shop")\n'},
    "V2": {"tools/a.py": "import subprocess\n" + PY_YARDIMCI
           + 'subprocess.run(["npx", "wrangler", "d1", "execute"], env=wrangler_ortami())\n'},
    "V3": {"tools/a.py": 'import subprocess\n\n\ndef wrangler_komutu():\n    return ["npx", "--yes", "wrangler@4"]\n\n\n'
           'subprocess.run(wrangler_komutu() + ["d1", "execute"])\n'
           'komut = ["npx", "--yes", "wrangler@4", "r2", "object", "put"]\n'
           'subprocess.check_output(komut)\n'},
    "V4": {"shop/test/a.mjs": 'import { spawnSync } from "node:child_process";\n'
           'const p = spawnSync("npx", ["--yes", "wrangler@4", "d1", "execute"], { cwd: "shop" });\n'},
    "V5": {"shop/test/a.js": 'const cp = require("child_process");\n'
           'const p = cp.spawnSync("npx", ["--yes", "wrangler@4", "d1", "execute"],\n'
           '  { cwd: "shop", env: { ...process.env, WRANGLER_WRITE_LOGS: "false" } });\n'},
    "V6": {"tools/a.py": 'import subprocess\nsubprocess.run(["git", "status"])\n'
           'subprocess.run(["python3", "tools/wrangler-log-nobetcisi.py", "--budama"])\n'
           'print("wrangler kilitlendi, cikti yok")\n',
           "tools/b.js": 'const { execFileSync } = require("child_process");\n'
           'execFileSync("git", ["log", "--grep", "wrangler.toml"]);\n'},
    "V7": {"tools/a.py": 'import subprocess\n\n\ndef kos(komut, cwd="."):\n'
           '    return subprocess.run(komut, cwd=cwd, capture_output=True)\n\n\n'
           'kos(["npx", "wrangler", "r2", "object", "get"])\n'},
    "V8": {"tools/a.py": "import os\nimport subprocess\n" + PY_YARDIMCI
           + 'ortam = dict(os.environ, CLOUDFLARE_ACCOUNT_ID="x")\n'
           'subprocess.run(["npx", "wrangler", "versions", "upload"], env=wrangler_ortami(ortam))\n'},
    "V9": {"tools/a.py": "import os\nimport subprocess\n" + PY_YARDIMCI
           + '\n\ndef alt(komut, ort=None):\n    if ort is None:\n        ort = wrangler_ortami()\n'
           '    return subprocess.run(komut, env=ort)\n\n\n'
           'alt(["npx", "wrangler", "d1", "execute"])\n'
           'alt(["npx", "wrangler", "d1", "execute"], ort=dict(os.environ, npm_config_cache="/tmp/x"))\n'},
    "V11": {"tools/a.py": "import os\nimport subprocess\n"
            'WRANGLER_LOG_KAPALI = {"WRANGLER_WRITE_LOGS": "false"}\n\n\n'
            "def wrangler_ortami():\n    return dict(os.environ, **WRANGLER_LOG_KAPALI)\n\n\n"
            'subprocess.run(["npx", "--yes", "wrangler@4", "d1", "execute"], env=wrangler_ortami())\n'},
}
# vaka -> (beklenen rc, CAGRI, KAPALI, ACIK)
BEKLENEN = {"V1": (1, 1, 0, 1), "V2": (0, 1, 1, 0), "V3": (1, 2, 0, 2), "V4": (1, 1, 0, 1),
            "V5": (0, 1, 1, 0), "V6": (0, 0, 0, 0), "V7": (1, 1, 0, 1), "V8": (0, 1, 1, 0),
            "V9": (1, 1, 0, 1), "V11": (0, 1, 1, 0)}

MUTANTLAR = [
    ("M1", "JS kolu cikar", "V4",
     'else js_tara(yol, kaynak)', 'else []'),
    ("M2", "yardimci sabiti WRITE_LOGS true", "V2", None, None),
    ("M3", "parametre -> cagri yeri cozumu kapali", "V7",
     "                konum = self.param_konumu(kapsam, d.id)\n",
     "                konum = None\n"),
    ("M4", "yerel yardimci literal WRITE_LOGS true", "V11", None, None),
]


def ortam():
    return dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def kapi_kos(kapi, kok):
    r = subprocess.run([sys.executable, kapi, "--kok", kok], capture_output=True, text=True,
                       env=ortam(), timeout=600)
    m = OZET.search(r.stdout)
    return r.returncode, (tuple(int(x) for x in m.groups()) if m else None), r.stdout + r.stderr


def agac_kur(taban, vaka, sabit='"false"', fikstur_sabit='"false"'):
    kok = os.path.join(taban, vaka)
    os.makedirs(os.path.join(kok, "tools"))
    with open(os.path.join(TOOLS, "wrangler_ortam.py"), encoding="utf-8") as f:
        yardimci = f.read()
    capa = 'WRANGLER_LOG_KAPALI = {"WRANGLER_WRITE_LOGS": "false"}'
    if yardimci.count(capa) != 1:
        raise SystemExit("OLCULEMEDI: wrangler_ortam.py sabit capasi %d kez" % yardimci.count(capa))
    with open(os.path.join(kok, "tools", "wrangler_ortam.py"), "w", encoding="utf-8") as f:
        f.write(yardimci.replace(capa, capa.replace('"false"', sabit)))
    for yol, govde in FIKSTUR[vaka].items():
        tam = os.path.join(kok, yol)
        os.makedirs(os.path.dirname(tam), exist_ok=True)
        with open(tam, "w", encoding="utf-8") as f:
            f.write(govde.replace('"WRANGLER_WRITE_LOGS": "false"', '"WRANGLER_WRITE_LOGS": ' + fikstur_sabit))
    return kok


def vaka_gecti(kapi, taban, vaka, sabit='"false"', fikstur_sabit='"false"'):
    rc, ozet, cikti = kapi_kos(kapi, agac_kur(taban, vaka, sabit, fikstur_sabit))
    b = BEKLENEN[vaka]
    return rc == b[0] and ozet == b[1:], "rc=%s ozet=%s beklenen=%s" % (rc, ozet, b), cikti


def mutant_kapi(taban, ad, eski, yeni):
    d = os.path.join(taban, "mutant-" + ad, "tools")
    os.makedirs(d)
    shutil.copy2(os.path.join(TOOLS, "git_ortami.py"), os.path.join(d, "git_ortami.py"))
    with open(KAPI, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(eski) != 1:
        return None  # capa tutmadi: mutant uygulanamadi
    yol = os.path.join(d, "wrangler-log-kapisi.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni))
    return yol


def main():
    taban = tempfile.mkdtemp(prefix="wlog-kapi-test-")
    gecen = toplam = 0
    m_gecen = 0
    try:
        for vaka in sorted(BEKLENEN, key=lambda v: int(v[1:])):  # V10 (gercek depo) asagida
            toplam += 1
            ok, ozet, cikti = vaka_gecti(KAPI, os.path.join(taban, "vaka"), vaka)
            gecen += ok
            print("%s %s %s" % ("GECTI " if ok else "KALDI ", vaka, ozet))
            if not ok:
                print("  " + cikti.strip().replace("\n", "\n  "))
        # V10: gercek depo
        toplam += 1
        rc, ozet, cikti = kapi_kos(KAPI, KOK)
        ok = rc == 0 and ozet is not None and ozet[2] == 0 and ozet[0] >= 16
        gecen += ok
        print("%s V10 gercek depo rc=%s ozet=%s (beklenen rc=0 ACIK=0 CAGRI>=16)"
              % ("GECTI " if ok else "KALDI ", rc, ozet))
        if not ok:
            print("  " + cikti.strip().replace("\n", "\n  "))

        for ad, aciklama, hedef, eski, yeni in MUTANTLAR:
            mtaban = os.path.join(taban, "m-" + ad)
            if ad == "M2":  # kapi ayni, yardimcinin (tools/wrangler_ortam.py) sabiti bozulur
                ok, ozet, _ = vaka_gecti(KAPI, mtaban, hedef, sabit='"true"')
            elif ad == "M4":  # kapi ayni, fiksturun yerel literal sabiti bozulur
                ok, ozet, _ = vaka_gecti(KAPI, mtaban, hedef, fikstur_sabit='"true"')
            else:
                kapi = mutant_kapi(taban, ad, eski, yeni)
                if kapi is None:
                    print("KALDI  %s %s: mutant capasi tutmadi (OLCULEMEDI)" % (ad, aciklama))
                    continue
                ok, ozet, _ = vaka_gecti(kapi, mtaban, hedef)
            olduruldu = not ok
            m_gecen += olduruldu
            print("%s %s %s -> %s %s" % ("GECTI " if olduruldu else "KALDI ", ad, aciklama, hedef,
                                          "KIRMIZI" if olduruldu else "HALA YESIL (mutant yasadi)") + " " + ozet)
    finally:
        shutil.rmtree(taban, ignore_errors=True)
    print("VAKA=%d/%d MUTANT=%d/%d" % (gecen, toplam, m_gecen, len(MUTANTLAR)))
    print("GECICI_SILINDI=%s" % (not os.path.exists(taban)))
    return 0 if gecen == toplam and m_gecen == len(MUTANTLAR) and not os.path.exists(taban) else 1


if __name__ == "__main__":
    sys.exit(main())

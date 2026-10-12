#!/usr/bin/env python3
"""GH TAVANI + SPEC-YOKLAMA KAPISI — kabul + mutant (BaBa 12 Eki 15:4x sinif kapisi).

OLCULEN VAKA (12 Eki 2026): bir m3 kabul iscisinin `gh run watch` dongusu
(150 tur) filonun TEK GitHub jetonunun 5000/sa butcesini tuketti -> tum
evlerde `gh` 403. Sinif: dis API yoklamasi tavansiz.

`~/.claude/cron/isci.sh` iki kol kazandi:
  * GH-TAVAN-SHIM: kosum-ozel shim dizini motorun PATH'inin basina konur;
    shim her `gh` cagrisini sayar (flock), gercek gh'yi tam yolla exec eder.
    Sayac `PRUVO_ISCI_GH_TAVANI`'ni (varsayilan 20) asinca gercek gh
    CAGRILMAZ: stderr `HAL=GH-TAVAN` + rc 1. Kosum sonu `GH_CAGRI=<n>` her
    kosumda; asimda `HAL=GH-TAVAN` log satiri + `KUTU_SATIRI: GH-TAVAN`.
  * SPEC-YOKLAMA-KAPISI: spec `gh run watch` / `sleep`+`gh` / dongu+`gh`
    istiyorsa `HAL=SPEC-YOKLAMA-RED rc=2`, kosum BASLAMAZ. Satirda
    KULLANMA|YASAK|ÇAĞIRMA geciyorsa RED yok.

VAKALAR (her biri izole CRON_KOKU + sahte claude + sahte gh; GERCEK gh YOK):
  V1 20 cagri -> 20'si sahte gh'ye ulasir, HAL=GH-TAVAN yok, GH_CAGRI=20
  V2 21 cagri -> 21. rc 1 + HAL=GH-TAVAN (stderr), log satiri TAM 1, KUTU_SATIRI
  V3 spec `gh run watch 123` -> SPEC-YOKLAMA-RED rc 2, sahte claude CAGRILMADI
  V4 spec "`gh run watch` KULLANMA" -> RED YOK, sahte claude cagrildi
  V5 PRUVO_ISCI_GH_TAVANI=abc -> rc 2, claude CAGRILMADI
  V6 m3 + claude motorlari: shim bloklari sokulmus kopyaya gore argv/ortam
     AYNI (fark yalniz PATH basindaki shim dizini)
MUTANTLAR (izole kopya; mutant OLMELI = ilgili vaka KIRMIZI yanmali):
  M1 shim'in tavan kontrolu kaldirilir -> V2 KIRMIZI
  M2 spec kapisinin `gh run watch` kalibi kaldirilir -> V3 KIRMIZI

IZOLASYON: gercek isci.log / karantina / tur-cikti / anahtar dosyalarina
DOKUNULMAZ — izole kokte yalniz `*.py`, `*.zsh` ve `isci-baglam` SEMBOLIK
baglanir; durum dosyalari izole kokte sifirdan dogar. HOME sahte (claude
kolu icin sahte 108 baytlik `.ci-token`); ortam MINIMAL kurulur (gercek
jeton/anahtar alt surece GECMEZ). Gecici agac is sonunda silinir.

KOSUM:  python3 tools/isci-gh-tavan-test.py
CIKTI:  VAKA=<ad> ... SONUC=GECTI|KALDI · MUTANT=<ad> ... SONUC=OLDU|YASADI
        son satir: GH-TAVAN VAKA=<g>/6 MUTANT=<o>/2 (rc 0 yalniz 6/6 + 2/2)
CI'da canli hat yoktur -> ONKOSUL_YOK + rc 3 (isci-*-test ailesinin kanonu).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

GERCEK_CRON = "/Users/okan/.claude/cron"
GERCEK_ISCI = os.path.join(GERCEK_CRON, "isci.sh")
GERCEK_SABITLER = os.path.join(GERCEK_CRON, "isci-sabitler.zsh")
TMP_ONEK = "gh-tavan-test-"

SHIM_BLOKLARI = (("# === GH-TAVAN-SHIM BAS", "# === GH-TAVAN-SHIM SON ===\n"),
                 ("# === GH-TAVAN-RAPOR BAS", "# === GH-TAVAN-RAPOR SON ===\n"))
SHIM_TEMIZLE_SATIRI = re.compile(r"^.*# GH-TAVAN-SHIM\n", re.M)
M1_CAPA = ("if n > TAVAN:", "if False:")
M2_CAPA = ("        if WATCH.search(s):\n            red(no)\n", "        pass\n")

SAHTE_CLAUDE = r'''#!%(py)s
# Sahte motor: GERCEK API CAGRISI YAPMAZ. argv/ortami kaydeder, istenen sayida
# `gh` cagrisini PATH uzerinden yapar (shim'e boyle ulasilir).
import json, os, subprocess, sys
iz = os.environ["SAHTE_IZ"]
with open(os.path.join(iz, "claude-cagrildi"), "a") as f:
    f.write("CAGRILDI\n")
with open(os.path.join(iz, "argv-ortam.json"), "w") as f:
    json.dump({"argv": sys.argv[1:], "ortam": dict(os.environ)}, f)
sonuc = []
for i in range(int(os.environ.get("SAHTE_GH_SAYI", "0"))):
    p = subprocess.run(["gh", "api", "sahte/%%d" %% (i + 1)], capture_output=True, text=True)
    sonuc.append({"rc": p.returncode, "stderr": p.stderr})
with open(os.path.join(iz, "gh-sonuc.json"), "w") as f:
    json.dump(sonuc, f)
sys.exit(0)
'''

SAHTE_GH = '''#!/bin/bash
# Sahte gh: GitHub'a GITMEZ. Ulastigini kaydeder.
echo "$*" >> "$SAHTE_IZ/gh-ulasti.txt"
exit 0
'''


def _yaz(yol, metin, kip=0o600):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    os.chmod(yol, kip)


def _izole_kok_kur(tmp, govde):
    """Izole CRON_KOKU: kod sembolik bagli, durum dosyalari izole, isci.sh=govde."""
    kok = os.path.join(tmp, "cron")
    os.makedirs(kok)
    for ad in os.listdir(GERCEK_CRON):
        if ad == "isci-sabitler.zsh" or ad.startswith("."):
            continue
        if ad.endswith((".py", ".zsh")) or ad == "isci-baglam":
            os.symlink(os.path.join(GERCEK_CRON, ad), os.path.join(kok, ad))
    with open(GERCEK_SABITLER, encoding="utf-8") as f:
        sabitler = f.read()
    civili = sabitler.replace("CRON_KOKU=" + GERCEK_CRON, "CRON_KOKU=" + kok, 1)
    if civili == sabitler:
        return None
    _yaz(os.path.join(kok, "isci-sabitler.zsh"), civili)
    _yaz(os.path.join(kok, "isci.sh"), govde, 0o755)
    _yaz(os.path.join(kok, "isci.log"), "")
    _yaz(os.path.join(kok, ".minimax-anahtar"), "sahte-anahtar-yalnizca-test\n")
    return kok


def _ortak_kur(tmp):
    """Sahte HOME (+ .ci-token), sahte claude, sahte gh, ev."""
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".claude", "cron"))
    _yaz(os.path.join(home, ".claude", "cron", ".ci-token"), "sk-ant-oat" + "0" * 98)
    bin_d = os.path.join(tmp, "bin")
    os.makedirs(bin_d)
    _yaz(os.path.join(bin_d, "claude"), SAHTE_CLAUDE % {"py": sys.executable}, 0o755)
    _yaz(os.path.join(bin_d, "gh"), SAHTE_GH, 0o755)
    ev = os.path.join(tmp, "ev")
    os.makedirs(ev)
    return home, bin_d, ev


def _kos(tmp, kok, ortak, ad, motor="minimax-m3", spec_metni="# test spec\n",
         gh_sayi=0, ek_ortam=None, etiket=None, spec_adi=None):
    home, bin_d, ev = ortak
    iz = os.path.join(tmp, "iz-" + ad)
    os.makedirs(iz)
    # Spec yolu istem metnine girer: V6'nin iki kolu AYNI yolu paylasir.
    spec = os.path.join(tmp, "spec-%s.md" % (spec_adi or ad))
    _yaz(spec, spec_metni)
    ortam = {
        "HOME": home, "USER": os.environ.get("USER", "okan"),
        "LANG": "en_US.UTF-8", "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "PATH": "/usr/bin:/bin", "CRON_KOKU": kok,
        "PRUVO_ISCI_CLAUDE_BIN": os.path.join(bin_d, "claude"),
        "PRUVO_ISCI_GH_BIN": os.path.join(bin_d, "gh"),
        "SAHTE_IZ": iz, "SAHTE_GH_SAYI": str(gh_sayi),
    }
    ortam.update(ek_ortam or {})
    log = os.path.join(kok, "isci.log")
    _yaz(log, "")
    p = subprocess.run([os.path.join(kok, "isci.sh"), motor, ev, spec,
                        etiket or ("kabul-gh-tavan-" + ad)],
                       capture_output=True, text=True, env=ortam, timeout=300)
    with open(log, encoding="utf-8", errors="replace") as f:
        log_metni = f.read()

    def oku_json(adi, bos):
        y = os.path.join(iz, adi)
        if not os.path.exists(y):
            return bos
        with open(y, encoding="utf-8") as f:
            return json.load(f)
    ulasti = 0
    uy = os.path.join(iz, "gh-ulasti.txt")
    if os.path.exists(uy):
        with open(uy, encoding="utf-8") as f:
            ulasti = len(f.read().splitlines())
    shim_artik = [a for a in os.listdir(kok) if a.startswith(".isci-gh-shim.")]
    return {
        "rc": p.returncode, "stderr": p.stderr or "", "stdout": p.stdout or "",
        "log": log_metni, "claude": os.path.exists(os.path.join(iz, "claude-cagrildi")),
        "gh_sonuc": oku_json("gh-sonuc.json", []), "ulasti": ulasti,
        "iz": oku_json("argv-ortam.json", None), "shim_artik": shim_artik,
    }


def _hal_satirlari(log, hal):
    return [s for s in log.splitlines() if s.startswith("=== ") and (" HAL=%s " % hal) in s]


# ---------------------------------------------------------------- vakalar
def v1(r):
    hata = []
    if r["ulasti"] != 20:
        hata.append("ulasti=%d" % r["ulasti"])
    if len(r["gh_sonuc"]) != 20 or any(c["rc"] != 0 for c in r["gh_sonuc"]):
        hata.append("gh_rc=%s" % [c["rc"] for c in r["gh_sonuc"]])
    if "HAL=GH-TAVAN" in r["log"] + r["stderr"]:
        hata.append("HAL=GH-TAVAN basildi")
    if "GH_CAGRI=20 tavan=20" not in r["log"]:
        hata.append("GH_CAGRI=20 satiri yok")
    if r["shim_artik"]:
        hata.append("shim artik=%s" % r["shim_artik"])
    return hata


def v2(r):
    hata = []
    son = r["gh_sonuc"][-1] if len(r["gh_sonuc"]) == 21 else None
    if r["ulasti"] != 20:
        hata.append("ulasti=%d (beklenen 20)" % r["ulasti"])
    if son is None or son["rc"] != 1 or "HAL=GH-TAVAN" not in son["stderr"]:
        hata.append("21.cagri=%s" % son)
    if any(c["rc"] != 0 for c in r["gh_sonuc"][:20]):
        hata.append("ilk20 rc!=0")
    satirlar = _hal_satirlari(r["log"], "GH-TAVAN")
    if len(satirlar) != 1 or "cagri=21 tavan=20" not in satirlar[0]:
        hata.append("HAL=GH-TAVAN log satiri=%d" % len(satirlar))
    if "KUTU_SATIRI: GH-TAVAN kabul-gh-tavan-" not in r["stderr"] or " 21/20" not in r["stderr"]:
        hata.append("KUTU_SATIRI yok")
    if r["shim_artik"]:
        hata.append("shim artik=%s" % r["shim_artik"])
    return hata


def v3(r):
    hata = []
    if r["rc"] != 2:
        hata.append("rc=%d" % r["rc"])
    if "HAL=SPEC-YOKLAMA-RED" not in r["stderr"]:
        hata.append("stderr HAL yok")
    if len(_hal_satirlari(r["log"], "SPEC-YOKLAMA-RED")) != 1:
        hata.append("log satiri != 1")
    if r["claude"]:
        hata.append("claude CAGRILDI")
    return hata


def v4(r):
    hata = []
    if "SPEC-YOKLAMA-RED" in r["log"] + r["stderr"]:
        hata.append("RED basildi")
    if not r["claude"]:
        hata.append("claude cagrilmadi rc=%d" % r["rc"])
    return hata


def v5(r):
    hata = []
    if r["rc"] != 2:
        hata.append("rc=%d" % r["rc"])
    if "PRUVO_ISCI_GH_TAVANI gecersiz" not in r["stderr"]:
        hata.append("stderr gecersiz satiri yok")
    if r["claude"]:
        hata.append("claude CAGRILDI")
    return hata


OYNAK_ORTAM = {"CLAUDE_PGID_DOSYASI_K417", "CLAUDE_GRUP_DOSYASI", "SAHTE_IZ", "PATH"}


def _normal(iz):
    argv = list(iz["argv"])
    for i, a in enumerate(argv[:-1]):
        if a == "--session-id":
            argv[i + 1] = "<SID>"
    ortam = {k: v for k, v in iz["ortam"].items() if k not in OYNAK_ORTAM}
    return argv, ortam


def v6_karsilastir(shimli, shimsiz):
    hata = []
    if not shimli["iz"] or not shimsiz["iz"]:
        return ["iz yok (shimli=%s shimsiz=%s)" % (bool(shimli["iz"]), bool(shimsiz["iz"]))]
    a1, o1 = _normal(shimli["iz"])
    a2, o2 = _normal(shimsiz["iz"])
    if a1 != a2:
        hata.append("argv farkli")
    if o1 != o2:
        fark = sorted(k for k in set(o1) | set(o2) if o1.get(k) != o2.get(k))
        hata.append("ortam farkli: %s" % fark)
    p1, p2 = shimli["iz"]["ortam"]["PATH"], shimsiz["iz"]["ortam"]["PATH"]
    bas, _, kalan = p1.partition(":")
    if kalan != p2 or not os.path.basename(bas).startswith(".isci-gh-shim."):
        hata.append("PATH farki shim oneki degil")
    if shimli["rc"] != shimsiz["rc"]:
        hata.append("rc %d!=%d" % (shimli["rc"], shimsiz["rc"]))
    return hata


def _shimsiz_govde(govde):
    for bas, son in SHIM_BLOKLARI:
        i = govde.find(bas)
        j = govde.find(son, i)
        if i < 0 or j < 0:
            return None
        govde = govde[:i] + govde[j + len(son):]
    govde, n = SHIM_TEMIZLE_SATIRI.subn("", govde)
    return govde if n == 1 else None


def _mutant(govde, capa):
    eski, yeni = capa
    return govde.replace(eski, yeni, 1) if govde.count(eski) == 1 else None


def _guvenli_sil(yol):
    gercek = os.path.realpath(yol)
    if not os.path.basename(gercek).startswith(TMP_ONEK):
        print("TEMIZLIK_ATLANDI: gecici olmayan yol " + gercek)
        return
    for korunan in (GERCEK_CRON, os.path.expanduser("~/dev"),
                    os.path.expanduser("~/.claude/projects")):
        if gercek == korunan or gercek.startswith(korunan + os.sep):
            print("TEMIZLIK_ATLANDI: korunan agac " + gercek)
            return
    shutil.rmtree(gercek, ignore_errors=True)


def _yaz_sonuc(etiket, ad, hata, iyi="GECTI", kotu="KALDI"):
    print("%s=%s OLCULEN=%s SONUC=%s" % (etiket, ad, "; ".join(hata) or "beklenen", kotu if hata else iyi))


def main():
    if not os.path.isfile(GERCEK_ISCI) or not os.path.isfile(GERCEK_SABITLER):
        print("ONKOSUL_YOK: canli isci hatti yok (" + GERCEK_CRON + ")")
        print("GH-TAVAN VAKA=OLCULEMEDI — bu kapi YEREL kosulur, CI'da DEGIL")
        return 3
    with open(GERCEK_ISCI, encoding="utf-8") as f:
        govde = f.read()
    tmp = tempfile.mkdtemp(prefix=TMP_ONEK)
    vaka_gecti = 0
    mutant_oldu = 0
    try:
        ortak = _ortak_kur(tmp)
        kok = _izole_kok_kur(os.path.join(tmp, "canli"), govde)
        if kok is None:
            print("VAKA=kurulum OLCULEN=SABITLER_CAPASI_TUTMADI SONUC=KALDI")
            return 1
        canli_tmp = os.path.join(tmp, "canli")

        def kos(ad, **kw):
            return _kos(canli_tmp, kok, ortak, ad, **kw)

        sonuc = [
            ("V1", v1(kos("v1", gh_sayi=20))),
            ("V2", v2(kos("v2", gh_sayi=21))),
            ("V3", v3(kos("v3", spec_metni="# spec\n\n`gh run watch 123`\n"))),
            ("V4", v4(kos("v4", spec_metni="# spec\n\n`gh run watch` KULLANMA\n"))),
            ("V5", v5(kos("v5", ek_ortam={"PRUVO_ISCI_GH_TAVANI": "abc"}))),
        ]
        # V6: ayni izole kokte isci.sh shimli <-> shimsiz degistirilir.
        shimsiz = _shimsiz_govde(govde)
        v6_hata = []
        if shimsiz is None:
            v6_hata.append("SHIM_BLOK_CAPASI_TUTMADI")
        else:
            isci_yol = os.path.join(kok, "isci.sh")
            for motor in ("minimax-m3", "claude"):
                r1 = kos("v6-%s-shimli" % motor, motor=motor, etiket="kabul-gh-tavan-v6",
                         spec_adi="v6")
                _yaz(isci_yol, shimsiz, 0o755)
                r2 = kos("v6-%s-shimsiz" % motor, motor=motor, etiket="kabul-gh-tavan-v6",
                         spec_adi="v6")
                _yaz(isci_yol, govde, 0o755)
                v6_hata += ["%s: %s" % (motor, h) for h in v6_karsilastir(r1, r2)]
        sonuc.append(("V6", v6_hata))
        for ad, hata in sonuc:
            _yaz_sonuc("VAKA", ad, hata)
            vaka_gecti += not hata

        # Mutantlar: ayri izole kok, canli govde DEGISMEZ.
        for ad, capa, senaryo, olcut in (
                ("M1", M1_CAPA, dict(gh_sayi=21), v2),
                ("M2", M2_CAPA, dict(spec_metni="# spec\n\n`gh run watch 123`\n"), v3)):
            m_govde = _mutant(govde, capa)
            m_tmp = os.path.join(tmp, "mutant-" + ad)
            m_kok = _izole_kok_kur(m_tmp, m_govde) if m_govde else None
            if m_kok is None:
                print("MUTANT=%s OLCULEN=CAPA_TUTMADI SONUC=YASADI" % ad)
                continue
            hata = olcut(_kos(m_tmp, m_kok, ortak, ad.lower(), **senaryo))
            # Mutant OLDU = olcut KIRMIZI yandi (vaka mutanti yakaladi).
            print("MUTANT=%s OLCULEN=%s SONUC=%s" % (
                ad, "; ".join(hata) or "vaka-yesil", "OLDU" if hata else "YASADI"))
            mutant_oldu += bool(hata)
    finally:
        _guvenli_sil(tmp)
    print("GH-TAVAN VAKA=%d/6 MUTANT=%d/2" % (vaka_gecti, mutant_oldu))
    return 0 if vaka_gecti == 6 and mutant_oldu == 2 else 1


if __name__ == "__main__":
    sys.exit(main())

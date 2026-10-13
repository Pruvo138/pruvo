#!/usr/bin/env python3
"""Kabul: isci.sh URUN KAPISI (13 Eki 2026, guvenlik-isci-urun-kapisi).

Olculen: tools/isci-urun-kapisi.py (kurulu kopyasi ~/.claude/cron/
isci-urun-kapisi.py; isci.sh BASLANGIC'ta `basla`, BITIS hukmunden once
`bitis` cagirir). Kusur: m3 iscisi urun uretmeden `BITIS rc=0 hal=SAGLIKLI`.

VAKALAR (HERMETIK: gecici dizin, gercek HOME/cron'a yazilmaz)
  V1 URUN_YOLU bos glob, motor SAGLIKLI rc=0      -> HAL=BOS RC=1
  V2 glob'da kosum sirasinda yeni dosya             -> HAL=SAGLIKLI RC=0 URUN=1
  V3 glob'da yalniz ESKI (baslangictan once) dosya  -> HAL=BOS RC=1
  V4 spec'te URUN_YOLU yok                          -> hal/rc AYNEN + OLCULEMEDI-URUN
  V5 motor rc!=0 (BUTCE_TAVANI) + bos glob          -> motorun hukmu KORUNUR
MUTANTLAR (yardimcinin gecici kopyasi; beklenen KIRMIZI)
  M1 BOS kolu kaldirilir  -> V1 KIRMIZI
  M2 mtime sarti kaldirilir -> V3 KIRMIZI
YEREL (canli hat yoksa -- CI -- ATLANDI, hukmu ETKILEMEZ)
  (f) kurulu kopya repo kopyasiyla BIREBIR
  (g) canli isci.sh'in izole kopyasi + sahte claude ile uctan uca:
      E1 bos glob -> BITIS rc=1 hal=BOS · E2 yeni urun -> rc=0 hal=SAGLIKLI
      urun=1 · E3 URUN_YOLU yok -> rc=0 + OLCULEMEDI-URUN
      (`PRUVO_ISCI_SH_KAYNAK=<yol>` ile kurulum ONCESI yan dosya olculur)
Cikti: `VAKA=5/5 MUTANT_OLDU=2/2`; rc 0 yalniz hepsi yesil ise.
"""
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

YARDIMCI = Path(__file__).resolve().parent / "isci-urun-kapisi.py"
GERCEK_CRON = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".claude" / "cron"
KURULU = GERCEK_CRON / "isci-urun-kapisi.py"
ISCI_SH = Path(os.environ.get("PRUVO_ISCI_SH_KAYNAK") or GERCEK_CRON / "isci.sh")


def _cikti(metin):
    d = {}
    for satir in metin.splitlines():
        if "=" in satir:
            k, v = satir.split("=", 1)
            d[k] = v
    return d


def _kos(yardimci, *arg):
    p = subprocess.run([sys.executable, str(yardimci)] + list(arg),
                       capture_output=True, text=True, timeout=30)
    return p.returncode, _cikti(p.stdout), p.stdout + p.stderr


def _kurulum(tmp, urun_satiri=True):
    ev = tmp / "ev"
    (ev / "galeri").mkdir(parents=True, exist_ok=True)
    spec = tmp / "spec.md"
    govde = "# gecici test spec\n"
    if urun_satiri:
        govde += "URUN_YOLU=galeri/*\n"
    spec.write_text(govde, encoding="utf-8")
    return ev, spec


def _tur(yardimci, tmp, hal="SAGLIKLI", rc=0, urun_satiri=True, uret=None):
    ev, spec = _kurulum(tmp, urun_satiri)
    if uret == "eski":
        eski = ev / "galeri" / "eski.png"
        eski.write_bytes(b"x" * 10)
        t = time.time() - 3600
        os.utime(eski, (t, t))
    brc, b, _ = _kos(yardimci, "basla", "--spec", str(spec), "--ev", str(ev))
    if brc != 0 or "ZAMAN" not in b:
        return None, "basla rc=%d" % brc
    if uret == "yeni":
        (ev / "galeri" / "yeni.png").write_bytes(b"x" * 10)
        (ev / "galeri" / "bos.png").write_bytes(b"")  # bos dosya SAYILMAZ
    frc, f, ham = _kos(yardimci, "bitis", "--spec", str(spec), "--ev", str(ev),
                       "--zaman", b["ZAMAN"], "--baslangic-sayi", b.get("SAYI", "-"),
                       "--hal", hal, "--rc", str(rc))
    if frc != 0:
        return None, "bitis rc=%d %s" % (frc, ham.strip()[-200:])
    return f, ham


def vaka_v1(y, tmp):
    f, ham = _tur(y, tmp)
    ok = bool(f) and f.get("HAL") == "BOS" and f.get("RC") == "1" \
        and "SAGLIKLI" not in f.get("HAL", "") and "sebep=urun-yok" in f.get("SATIR", "")
    return ok, "HAL=%s RC=%s" % ((f or {}).get("HAL"), (f or {}).get("RC"))


def vaka_v2(y, tmp):
    f, ham = _tur(y, tmp, uret="yeni")
    ok = bool(f) and f.get("HAL") == "SAGLIKLI" and f.get("RC") == "0" \
        and f.get("URUN") == "1" and "urun=1" in f.get("SATIR", "")
    return ok, "HAL=%s RC=%s URUN=%s" % ((f or {}).get("HAL"), (f or {}).get("RC"),
                                        (f or {}).get("URUN"))


def vaka_v3(y, tmp):
    f, ham = _tur(y, tmp, uret="eski")
    ok = bool(f) and f.get("HAL") == "BOS" and f.get("RC") == "1" \
        and "urun_baslangic=1" in f.get("SATIR", "")
    return ok, "HAL=%s RC=%s SATIR=%s" % ((f or {}).get("HAL"), (f or {}).get("RC"),
                                         (f or {}).get("SATIR"))


def vaka_v4(y, tmp):
    f, ham = _tur(y, tmp, urun_satiri=False)
    ok = bool(f) and f.get("HAL") == "SAGLIKLI" and f.get("RC") == "0" \
        and f.get("SATIR") == "URUN_KAPISI=OLCULEMEDI-URUN sebep=spec-urun-yolu-yok"
    return ok, "HAL=%s RC=%s SATIR=%s" % ((f or {}).get("HAL"), (f or {}).get("RC"),
                                         (f or {}).get("SATIR"))


def vaka_v5(y, tmp):
    f, ham = _tur(y, tmp, hal="BUTCE_TAVANI", rc=1)
    ok = bool(f) and f.get("HAL") == "BUTCE_TAVANI" and f.get("RC") == "1" \
        and "BOS" not in f.get("HAL", "")
    return ok, "HAL=%s RC=%s" % ((f or {}).get("HAL"), (f or {}).get("RC"))


VAKALAR = [("V1", vaka_v1), ("V2", vaka_v2), ("V3", vaka_v3),
           ("V4", vaka_v4), ("V5", vaka_v5)]

MUTANTLAR = [
    ("M1-bos-kolu-yok", "if n == 0 and rc == 0 and hal in EZILEBILIR_HALLER:",
     "if False:", vaka_v1),
    ("M2-mtime-sarti-yok", "if zaman is not None and st.st_mtime < zaman:",
     "if False:", vaka_v3),
]


def vaka_f():
    if not KURULU.exists():
        return None, "kurulu kopya yok (CI) — ATLANDI"
    if KURULU.read_bytes() != YARDIMCI.read_bytes():
        return False, "kurulu kopya %s repo kopyasindan FARKLI" % KURULU
    return True, "kurulu kopya BIREBIR"


# ---------------------------------------------------------------- (g) uctan uca
BAGLANMAZ = {"isci.sh", "isci-sabitler.zsh", "isci.log", ".minimax-anahtar",
             "isci-urun-kapisi.py"}


def _izole_kok(tmp):
    kok = tmp / "cron"
    kok.mkdir()
    # Yalniz KOD dosyalari baglanir: durum dizinleri/dosyalari (isci-tur-cikti,
    # .motor-karantina, sayaclar) baglanirsa test GERCEK cron'a yazar (olculdu:
    # ilk kosumda 3 tur-cikti logu sizdi). Eksik durum izole kokte sifirdan acilir.
    for ad in os.listdir(GERCEK_CRON):
        if ad not in BAGLANMAZ and ad.endswith((".py", ".zsh", ".sh")) \
                and (GERCEK_CRON / ad).is_file():
            try:
                os.symlink(GERCEK_CRON / ad, kok / ad)
            except OSError:
                pass
    sabit = (GERCEK_CRON / "isci-sabitler.zsh").read_text(encoding="utf-8")
    civili = sabit.replace("CRON_KOKU=%s" % GERCEK_CRON, "CRON_KOKU=%s" % kok, 1)
    if civili == sabit:
        return None
    (kok / "isci-sabitler.zsh").write_text(civili, encoding="utf-8")
    shutil.copy2(ISCI_SH, kok / "isci.sh")
    os.chmod(kok / "isci.sh", 0o755)
    shutil.copy2(YARDIMCI, kok / "isci-urun-kapisi.py")  # olculen = repo kopyasi
    (kok / "isci.log").write_text("", encoding="utf-8")
    a = kok / ".minimax-anahtar"
    a.write_text("sahte-anahtar-yalnizca-test\n", encoding="utf-8")
    os.chmod(a, stat.S_IRUSR | stat.S_IWUSR)
    return kok


def _uctan_uca(tmp, ad, urun_satiri, uret):
    t = tmp / ad
    t.mkdir()
    kok = _izole_kok(t)
    if kok is None:
        return False, "SABITLER_CAPASI_TUTMADI"
    ev, spec = _kurulum(t, urun_satiri)
    sahte = t / "claude"
    yaz = ""
    if uret:
        yaz = "printf 'png' > '%s'\n" % (ev / "galeri" / "yeni.png")
    sahte.write_text(
        "#!/bin/bash\n# Sahte claude: API CAGRISI YAPMAZ.\n" + yaz +
        "echo '{\"type\":\"result\",\"subtype\":\"success\",\"is_error\":false,"
        "\"result\":\"ok\"}'\nexit 0\n", encoding="utf-8")
    os.chmod(sahte, 0o755)
    ortam = dict(os.environ)
    ortam["PRUVO_ISCI_CLAUDE_BIN"] = str(sahte)
    ortam.pop("PRUVO_CLAUDE_ISCI_IZNI", None)
    p = subprocess.run([str(kok / "isci.sh"), "minimax-m3", str(ev), str(spec),
                        "kabul-urun-kapisi-" + ad.lower()],
                       capture_output=True, text=True, env=ortam, timeout=300)
    log = (kok / "isci.log").read_text(encoding="utf-8", errors="replace")
    bitis = [s for s in log.splitlines() if " BITIS " in s]
    return p.returncode, (bitis[-1] if bitis else ""), log


def vaka_g(tmp):
    if not GERCEK_CRON.is_dir() or not ISCI_SH.is_file():
        return None, "canli isci hatti yok (CI) — ATLANDI"
    sonuc = []
    rc, b, log = _uctan_uca(tmp, "E1", True, False)
    sonuc.append(("E1", rc == 1 and "rc=1 " in b and "hal=BOS" in b
                  and "HAL=BOS sebep=urun-yok" in log and "hal=SAGLIKLI" not in b,
                  "rc=%s %s" % (rc, b)))
    rc, b, log = _uctan_uca(tmp, "E2", True, True)
    sonuc.append(("E2", rc == 0 and "rc=0 " in b and "hal=SAGLIKLI urun=1 " in b,
                  "rc=%s %s" % (rc, b)))
    rc, b, log = _uctan_uca(tmp, "E3", False, False)
    sonuc.append(("E3", rc == 0 and "hal=SAGLIKLI" in b
                  and "URUN_KAPISI=OLCULEMEDI-URUN sebep=spec-urun-yolu-yok" in log,
                  "rc=%s %s" % (rc, b)))
    for ad, ok, neden in sonuc:
        print("%s %s — %s" % ("YESIL" if ok else "KIRMIZI", ad, neden))
    return all(ok for _, ok, _ in sonuc), "uctan uca %d/%d" % (
        sum(1 for _, ok, _ in sonuc if ok), len(sonuc))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="isci-urun-test-"))
    try:
        sonuc = []
        for ad, fn in VAKALAR:
            d = tmp / ad
            d.mkdir()
            ok, neden = fn(YARDIMCI, d)
            sonuc.append(ok)
            print("%s %s — %s" % ("YESIL" if ok else "KIRMIZI", ad, neden))
        olen = 0
        for ad, eski, yeni, vaka in MUTANTLAR:
            govde = YARDIMCI.read_text(encoding="utf-8")
            if govde.count(eski) != 1:
                print("MUTANT-CAPA-TUTMADI %s" % ad)
                continue
            m = tmp / (ad + ".py")
            m.write_text(govde.replace(eski, yeni, 1), encoding="utf-8")
            d = tmp / ("m-" + ad)
            d.mkdir()
            ok, neden = vaka(m, d)
            olen += 0 if ok else 1
            print("%s %s — %s" % ("MUTANT-YASADI" if ok else "MUTANT-OLDU", ad, neden))
        yerel_ok = True
        for ad, fn in (("(f)", vaka_f), ("(g)", lambda: vaka_g(tmp))):
            ok, neden = fn()
            if ok is None:
                print("ATLANDI %s %s" % (ad, neden))
                continue
            yerel_ok = yerel_ok and ok
            print("%s %s %s" % ("YESIL" if ok else "KIRMIZI", ad, neden))
        yesil = sum(1 for s in sonuc if s)
        print("VAKA=%d/%d MUTANT_OLDU=%d/%d" % (yesil, len(sonuc), olen, len(MUTANTLAR)))
        return 0 if yesil == len(sonuc) and olen == len(MUTANTLAR) and yerel_ok else 1
    finally:
        if tmp.name.startswith("isci-urun-test-"):
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

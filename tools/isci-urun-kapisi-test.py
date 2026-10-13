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
ISCI AGACI/DALI EKSENI (13 Eki, guvenlik-isci-urun-agac; EV gecici git deposu,
  isci `--ev` ana checkout'ta, urun kendi worktree'sinde/dalinda -- 2/2 sahte BOS)
  A1 urun yalniz kosumda acilan worktree'de (commit'siz) -> URUN=1 eksen=agac:<ad>
  A2 urun yalniz kosumda guncellenen dalin commit'inde    -> URUN=1 eksen=dal:<ref>
  A3 urunlu worktree+dal kosumdan ONCE (zaman < ZAMAN)    -> HAL=BOS (eski sayilmaz)
  A4 kosumda agac+dal var ama desene uyan yeni dosya yok  -> HAL=BOS eksen=yok
     (taze checkout'un degismemis eski dosyasi SAYILMAZ)
MUTANTLAR (yardimcinin gecici kopyasi; beklenen KIRMIZI)
  M1 BOS kolu kaldirilir  -> V1 KIRMIZI
  M2 mtime sarti kaldirilir -> V3 KIRMIZI
  M3 agac ekseni kaldirilir -> A1 KIRMIZI
YEREL (canli hat yoksa -- CI -- ATLANDI, hukmu ETKILEMEZ)
  (f) kurulu kopya repo kopyasiyla BIREBIR
  (g) canli isci.sh'in izole kopyasi + sahte claude ile uctan uca:
      E1 bos glob -> BITIS rc=1 hal=BOS · E2 yeni urun -> rc=0 hal=SAGLIKLI
      urun=1 · E3 URUN_YOLU yok -> rc=0 + OLCULEMEDI-URUN
      (`PRUVO_ISCI_SH_KAYNAK=<yol>` ile kurulum ONCESI yan dosya olculur)
Cikti: `VAKA=9/9 MUTANT_OLDU=3/3`; rc 0 yalniz hepsi yesil ise.
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


def _kos(yardimci, *arg, ortam=None):
    p = subprocess.run([sys.executable, str(yardimci)] + list(arg),
                       capture_output=True, text=True, timeout=60, env=ortam)
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


# ------------------------------------------------- isci agaci / dali ekseni
# Gecici git deposu: GIT_DIR/GIT_WORK_TREE miras ALINMAZ (kanca icinde gercek
# depoyu bozma dersi), HOME gecici dizine, global/sistem git ayari okunmaz.
_GIT_ORTAM_SIL = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                  "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                  "GIT_PREFIX", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES")


def _git_ortami(tmp):
    ev_home = tmp / "home"
    ev_home.mkdir(exist_ok=True)
    o = {k: v for k, v in os.environ.items() if k not in _GIT_ORTAM_SIL}
    o.update(HOME=str(ev_home), GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
             GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@ornek.invalid",
             GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@ornek.invalid",
             GIT_CEILING_DIRECTORIES=str(tmp))
    return o


def _g(ortam, kok, *arg, tarih=None):
    o = dict(ortam)
    if tarih is not None:
        o["GIT_AUTHOR_DATE"] = o["GIT_COMMITTER_DATE"] = "@%d +0000" % tarih
    subprocess.run(["git", "-C", str(kok)] + list(arg), check=True, env=o,
                   capture_output=True, text=True, timeout=30)


def _eskit(*yollar):
    t = time.time() - 3600
    for y in yollar:
        if os.path.lexists(y):
            os.utime(y, (t, t))


def _depo(tmp):
    """EV = git deposu (ana checkout); cikti/eski.txt eski commit'te."""
    ortam = _git_ortami(tmp)
    ev = tmp / "ev"
    (ev / "cikti").mkdir(parents=True)
    _g(ortam, tmp, "init", "-q", "-b", "main", str(ev))
    (ev / "cikti" / "eski.txt").write_text("eski\n", encoding="utf-8")
    _g(ortam, ev, "add", "-A")
    _g(ortam, ev, "commit", "-q", "-m", "taban", tarih=int(time.time()) - 3600)
    _eskit(ev / "cikti" / "eski.txt")
    spec = tmp / "spec.md"
    spec.write_text("# gecici test spec\nURUN_YOLU=cikti/*\n", encoding="utf-8")
    return ortam, ev, spec


def _yeni_agac(ortam, ev, agac, dal):
    _g(ortam, ev, "worktree", "add", "-q", "-b", dal, str(agac))
    (agac / "cikti").mkdir(exist_ok=True)


def _git_tur(yardimci, tmp, once=None, sirasinda=None):
    ortam, ev, spec = _depo(tmp)
    if once:
        once(ortam, ev, tmp)
    brc, b, _ = _kos(yardimci, "basla", "--spec", str(spec), "--ev", str(ev), ortam=ortam)
    if brc != 0 or "ZAMAN" not in b:
        return None, "basla rc=%d" % brc
    time.sleep(1.1)  # commit zamani saniye cozunurluklu: ZAMAN'dan sonra olsun
    if sirasinda:
        sirasinda(ortam, ev, tmp)
    frc, f, ham = _kos(yardimci, "bitis", "--spec", str(spec), "--ev", str(ev),
                       "--zaman", b["ZAMAN"], "--baslangic-sayi", b.get("SAYI", "-"),
                       "--hal", "SAGLIKLI", "--rc", "0", ortam=ortam)
    if frc != 0:
        return None, "bitis rc=%d %s" % (frc, ham.strip()[-200:])
    return f, ham


def _ozet(f):
    f = f or {}
    return "HAL=%s RC=%s URUN=%s SATIR=%s" % (f.get("HAL"), f.get("RC"), f.get("URUN"),
                                             f.get("SATIR"))


def vaka_a1(y, tmp):
    def sirasinda(ortam, ev, tmp):
        agac = tmp / "isci-agaci"
        _yeni_agac(ortam, ev, agac, "isci-a1")
        (agac / "cikti" / "urun.txt").write_text("urun\n", encoding="utf-8")
    f, ham = _git_tur(y, tmp, sirasinda=sirasinda)
    ok = bool(f) and f.get("HAL") == "SAGLIKLI" and f.get("RC") == "0" \
        and f.get("URUN") == "1" and " eksen=agac:isci-agaci " in f.get("SATIR", "") \
        and not (tmp / "ev" / "cikti" / "urun.txt").exists()
    return ok, _ozet(f) if f else ham


def vaka_a2(y, tmp):
    def sirasinda(ortam, ev, tmp):
        agac = tmp / "gecici-agac"
        _yeni_agac(ortam, ev, agac, "isci-a2")
        (agac / "cikti" / "urun.txt").write_text("urun\n", encoding="utf-8")
        _g(ortam, agac, "add", "-A")
        _g(ortam, agac, "commit", "-q", "-m", "urun")
        _g(ortam, ev, "worktree", "remove", str(agac))  # isci push'layip agaci kaldirdi
    f, ham = _git_tur(y, tmp, sirasinda=sirasinda)
    ok = bool(f) and f.get("HAL") == "SAGLIKLI" and f.get("RC") == "0" \
        and f.get("URUN") == "1" and " eksen=dal:refs/heads/isci-a2 " in f.get("SATIR", "") \
        and "agac:" not in f.get("SATIR", "")
    return ok, _ozet(f) if f else ham


def vaka_a3(y, tmp):
    def once(ortam, ev, tmp):
        agac = tmp / "eski-agac"
        _yeni_agac(ortam, ev, agac, "isci-a3")
        (agac / "cikti" / "urun.txt").write_text("urun\n", encoding="utf-8")
        _g(ortam, agac, "add", "-A")
        _g(ortam, agac, "commit", "-q", "-m", "urun", tarih=int(time.time()) - 1800)
        (agac / "cikti" / "kirli.txt").write_text("kirli\n", encoding="utf-8")
        gd = ev / ".git" / "worktrees" / "eski-agac"
        _eskit(agac / ".git", gd / "HEAD", gd / "logs" / "HEAD",
               agac / "cikti" / "urun.txt", agac / "cikti" / "kirli.txt")
    f, ham = _git_tur(y, tmp, once=once)
    ok = bool(f) and f.get("HAL") == "BOS" and f.get("RC") == "1" \
        and " eksen=yok " in f.get("SATIR", "")
    return ok, _ozet(f) if f else ham


def vaka_a4(y, tmp):
    def sirasinda(ortam, ev, tmp):
        agac = tmp / "bos-agac"
        _yeni_agac(ortam, ev, agac, "isci-a4")
        (agac / "baska.txt").write_text("baska\n", encoding="utf-8")
        _g(ortam, agac, "add", "-A")
        _g(ortam, agac, "commit", "-q", "-m", "baska")
    f, ham = _git_tur(y, tmp, sirasinda=sirasinda)
    ok = bool(f) and f.get("HAL") == "BOS" and f.get("RC") == "1" \
        and " eksen=yok " in f.get("SATIR", "") and f.get("URUN") == "0"
    return ok, _ozet(f) if f else ham


VAKALAR = [("V1", vaka_v1), ("V2", vaka_v2), ("V3", vaka_v3),
           ("V4", vaka_v4), ("V5", vaka_v5),
           ("A1-agac", vaka_a1), ("A2-dal", vaka_a2), ("A3-eski", vaka_a3),
           ("A4-yok", vaka_a4)]

MUTANTLAR = [
    ("M1-bos-kolu-yok", "if n == 0 and rc == 0 and hal in EZILEBILIR_HALLER:",
     "if False:", vaka_v1),
    ("M2-mtime-sarti-yok", "if zaman is not None and st.st_mtime < zaman:",
     "if False:", vaka_v3),
    ("M3-agac-ekseni-yok", "b = _agac_say(agac, zaman, desenler, ev_bas)",
     "b = set()", vaka_a1),
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

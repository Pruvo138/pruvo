#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AGIR-IS KAPISI kabul testi (13 Eki 2026, BaBa 02:4x hukmu).

Olculen: tools/agir-is.sh (kurulu kopyasi ~/.claude/cron/agir-is.sh) +
tools/isci-semafor.py `al --adet N` (coklu slot, hep-ya-hic).

HERMETIK: her vaka gecici dizinde kendi slot kokunu / isci.log'unu / HOME'unu
kurar (AGIR_IS_* kancalari + HOME); gercek `~/.claude/cron` ve gercek HOME'a
YAZILMAZ. Sahte isci = `sh` sureci (`al` -> `exec sleep`), sahte agir is =
`sh -c` (isaret dosyasi + kisa uyku), sahte 1 dk yuku =
PRUVO_ISCI_SEMAFOR_YUK_DOSYASI dosyasi (bekleme sirasinda degistirilir).
Yuk YARATILMAZ.

VAKALAR
  (a) 1 isci slotu doluyken agir is BEKLER (sebep=slot), bosalinca baslar
  (b) yuk 8.5 iken bekler (sebep=yuk), 8.0'da baslar
  (c) komut gecer -> rc AYNEN doner (0 ve 7) + SINIR slot BIRAKILIR (DOLU=0)
  (d) agir is kosarken yeni isci `al` (adet 1) BEKLER; agir is TERM'le
      oldurulunce trap slotlari birakir, isci baslar
  (e) tavan -> rc=1 + `HAL=KUYRUK-TAVAN tur=agir` satiri, komut KOSMAZ
  (f) `--adet 1` davranisi: tools/isci-semafor-test.py tum vakalarda YESIL
EK (VAKA sayimina girmez, kirmizisi yine rc=1)
  (g) ic ice: isci.sh icinden (PRUVO_ISCI_SEMAFOR_SAHIBI canli, 1 slot tutuyor)
      agir is KALAN SINIR-1 slotu alir, kendi iscisini beklemez (kilitlenme yok)
  SINIR = isci-semafor.py `sinir` (tek kaynak; 21 Eki 2026'dan beri 2)
  (h) kurulu ~/.claude/cron/agir-is.sh repo kopyasiyla BIREBIR (CI'da ATLANDI)
MUTANTLAR (agir-is.sh kopyasi uzerinde; beklenen KIRMIZI)
  M1 --adet SINIR -> 1    => (d) KIRMIZI
  M2 yuk esigi kaldirildi => (b) KIRMIZI

Cikis: hepsi YESIL ve iki mutant da OLDURULDU ise 0, aksi 1.
"""

import os
import pwd
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent
AGIR = KOK / "agir-is.sh"
YARDIMCI = KOK / "isci-semafor.py"
SEMAFOR_TEST = KOK / "isci-semafor-test.py"
ZSH = shutil.which("zsh") or "/bin/zsh"   # CI (ubuntu) adimi zsh'yi kurar
KURULU = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".claude" / "cron" / "agir-is.sh"
# SINIR tek kaynak: yardimcinin `sinir` alt komutu (agir-is.sh de oradan okur).
SINIR = int(subprocess.run(["python3", str(YARDIMCI), "sinir"], capture_output=True,
                           text=True, timeout=10).stdout)
TUM_SLOT = "slot=%s/%d adet=%d " % (",".join(str(n) for n in range(1, SINIR + 1)), SINIR, SINIR)

HIZ = ["--aralik-sn", "0.1", "--izle-sn", "0.2", "--satir-sn", "60"]


class Dunya:
    def __init__(self, agir):
        self.agir = str(agir)
        self.kok = Path(tempfile.mkdtemp(prefix="agir-is-test-"))
        self.slot = self.kok / "isci-slot"
        self.log = self.kok / "isci.log"
        self.yuk = self.kok / "yuk"
        self.yuk.write_text("1.0\n")
        (self.kok / "home").mkdir()
        (self.kok / "cron").mkdir()
        env = dict(os.environ)
        env.pop("PRUVO_ISCI_SEMAFOR_SAHIBI", None)   # test isci.sh icinden kosabilir
        env.update(HOME=str(self.kok / "home"),
                   PRUVO_ISCI_SEMAFOR_YUK_DOSYASI=str(self.yuk),
                   AGIR_IS_CRON_KOKU=str(self.kok / "cron"),
                   AGIR_IS_SEMAFOR=str(YARDIMCI),
                   AGIR_IS_SLOT_KOKU=str(self.slot),
                   AGIR_IS_LOG=str(self.log),
                   AGIR_IS_ARALIK_SN="0.1", AGIR_IS_IZLE_SN="0.2", AGIR_IS_SATIR_SN="60")
        self.env = env
        self.surecler = []

    def isci(self, etiket, uyku=30):
        al = ('python3 "$Y" al --sahip $$ --slot-koku "$S" --log "$L" --etiket %s %s'
              % (etiket, " ".join(HIZ)))
        env = dict(self.env, Y=str(YARDIMCI), S=str(self.slot), L=str(self.log))
        p = subprocess.Popen(["/bin/sh", "-c", '%s || exit $?; exec sleep %d' % (al, uyku)],
                             env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.surecler.append(p)
        return p

    def agir_is(self, etiket, govde, ek_env=None):
        """govde: sh -c metni. Isaret dosyasi `$M` (komut BASLADI kaniti)."""
        env = dict(self.env, M=str(self.kok / ("basladi-" + etiket)))
        if ek_env:
            env.update(ek_env)
        p = subprocess.Popen([ZSH, self.agir, "--etiket", etiket, "--",
                              "/bin/sh", "-c", govde],
                             env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.surecler.append(p)
        return p

    def basladi(self, etiket):
        return (self.kok / ("basladi-" + etiket)).exists()

    def durum(self):
        r = subprocess.run(["python3", str(YARDIMCI), "durum", "--slot-koku", str(self.slot)],
                           env=self.env, capture_output=True, text=True, timeout=10)
        return r.stdout

    def dolu(self):
        for satir in self.durum().splitlines():
            if satir.startswith("DOLU="):
                return int(satir.split()[0].split("=")[1].split("/")[0])
        return -1

    def log_metni(self):
        return self.log.read_text() if self.log.exists() else ""

    def satirlar(self, *parca):
        return [s for s in self.log_metni().splitlines() if all(p in s for p in parca)]

    def bekle(self, kosul, sure=8.0):
        son = time.monotonic() + sure
        while time.monotonic() < son:
            if kosul():
                return True
            time.sleep(0.05)
        return kosul()

    def kapat(self):
        for p in self.surecler:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                p.wait(timeout=5)
            except Exception:
                pass
        time.sleep(0.5)   # tutucular sahip olunce cikar; dizin silinirken yazmasinlar
        shutil.rmtree(self.kok, ignore_errors=True)


UZUN = 'touch "$M"; exec sleep 30'


def vaka_a(agir):
    """1 isci slotu doluyken agir is bekler, bosalinca baslar."""
    d = Dunya(agir)
    try:
        isci = d.isci("i1")
        if not d.bekle(lambda: d.dolu() == 1):
            return False, "isci slot almadi"
        p = d.agir_is("a", 'touch "$M"; sleep 1')
        if not d.bekle(lambda: d.satirlar("HAL=BEKLIYOR", " tur=agir ", " etiket=a "), 4):
            return False, "agir is BEKLIYOR yazmadi (log: %r)" % d.log_metni()[-400:]
        time.sleep(0.6)
        if d.basladi("a") or d.satirlar("SEMAFOR=ALINDI", " etiket=a "):
            return False, "1 slot doluyken agir is basladi (kismi alim)"
        satir = d.satirlar("HAL=BEKLIYOR", " etiket=a ")[0]
        for parca in (" sira=1 ", " bekleme_dk=0 ", " sebep=slot ", " yuk="):
            if parca not in satir:
                return False, "BEKLIYOR satiri bicim disi (%s yok): %r" % (parca.strip(), satir)
        if d.dolu() != 1:
            return False, "bekleyen agir is slot tuttu (dolu=%d, beklenen 1)" % d.dolu()
        os.killpg(isci.pid, signal.SIGTERM)
        isci.wait(timeout=5)
        if not d.bekle(lambda: d.basladi("a"), 5):
            return False, "isci slotu bosaldiginda agir is baslamadi"
        alindi = d.satirlar("SEMAFOR=ALINDI", " etiket=a ")
        if len(alindi) != 1 or TUM_SLOT not in alindi[0]:
            return False, "ALINDI satiri %d slot gostermiyor: %r" % (SINIR, alindi)
        p.wait(timeout=10)
        return True, ("1 slot doluyken bekledi (sebep=slot, slot tutmadan), bosalinca %d/%d aldi"
                      % (SINIR, SINIR))
    finally:
        d.kapat()


def vaka_b(agir):
    """yuk 8.5 iken bekler, 8.0'da baslar."""
    d = Dunya(agir)
    try:
        d.yuk.write_text("8.5\n")
        p = d.agir_is("b", 'touch "$M"; sleep 1')
        if not d.bekle(lambda: d.satirlar("HAL=BEKLIYOR", " etiket=b "), 4):
            return False, "yuk 8.5 iken BEKLIYOR yazilmadi"
        time.sleep(0.6)
        if d.basladi("b"):
            return False, "yuk 8.5 iken agir is basladi (yuk esigi 8 uygulanmadi)"
        if not d.satirlar("HAL=BEKLIYOR", " etiket=b ", " sebep=yuk ", " yuk=8.50 "):
            return False, "BEKLIYOR satirinda sebep=yuk yuk=8.50 yok: %r" % d.log_metni()[-300:]
        d.yuk.write_text("8.0\n")   # esik >8: 8.0 gecer
        if not d.bekle(lambda: d.basladi("b"), 5):
            return False, "yuk 8.0'a dustukten sonra agir is baslamadi"
        p.wait(timeout=10)
        return True, "yuk 8.5'te bekledi (sebep=yuk), 8.0'da basladi"
    finally:
        d.kapat()


def vaka_c(agir):
    """komut rc'si aynen doner + 3 slot birakilir."""
    d = Dunya(agir)
    try:
        rcler = []
        for etiket, govde in (("c0", 'touch "$M"; exit 0'), ("c7", 'touch "$M"; exit 7')):
            p = d.agir_is(etiket, govde)
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                return False, "%s bitmedi" % etiket
            rcler.append(p.returncode)
            if not d.basladi(etiket):
                return False, "%s komutu kosmadi" % etiket
            if not d.bekle(lambda: d.dolu() == 0, 5):
                return False, "%s sonrasi slot birakilmadi (dolu=%d)" % (etiket, d.dolu())
        if rcler != [0, 7]:
            return False, "rc=%r (beklenen [0, 7])" % rcler
        if not d.bekle(lambda: not any((d.slot / str(n)).exists() for n in (1, 2, 3)), 3):
            return False, "isaretci dosyasi kaldi: %r" % d.durum()
        kuyruk = d.slot / ".kuyruk"
        if kuyruk.exists() and list(kuyruk.iterdir()):
            return False, "kuyruk girdisi kaldi"
        return True, "rc 0 ve 7 AYNEN dondu; her kosum sonrasi DOLU=0, isaretci/kuyruk temiz"
    finally:
        d.kapat()


def vaka_d(agir):
    """agir is kosarken yeni isci bekler; agir is TERM'le olunce isci baslar."""
    d = Dunya(agir)
    try:
        p = d.agir_is("d", UZUN)
        if not d.bekle(lambda: d.basladi("d"), 5):
            return False, "agir is baslamadi"
        d.isci("i2")
        d.bekle(lambda: d.satirlar(" etiket=i2 "), 4)
        time.sleep(0.6)
        if d.satirlar("SEMAFOR=ALINDI", " etiket=i2 "):
            return False, "agir is kosarken yeni isci slot aldi (dolu=%d)" % d.dolu()
        if not d.satirlar("HAL=BEKLIYOR", " etiket=i2 ", " sebep=slot "):
            return False, "yeni isci BEKLIYOR sebep=slot yazmadi (log: %r)" % d.log_metni()[-300:]
        if d.dolu() != 3:
            return False, "agir is kosarken dolu=%d (beklenen 3)" % d.dolu()
        t0 = time.monotonic()
        os.kill(p.pid, signal.SIGTERM)
        p.wait(timeout=5)
        if p.returncode != 143:
            return False, "TERM sonrasi agir-is rc=%s (beklenen 143)" % p.returncode
        if not d.bekle(lambda: d.satirlar("SEMAFOR=ALINDI", " etiket=i2 "), 5):
            return False, "agir is olunce isci baslamadi"
        return True, ("agir is kosarken isci bekledi (sebep=slot); TERM -> trap birakti, "
                      "isci %.2f sn'de basladi" % (time.monotonic() - t0))
    finally:
        d.kapat()


def vaka_e(agir):
    """tavan -> rc=1 + HAL=KUYRUK-TAVAN tur=agir; komut kosmaz."""
    d = Dunya(agir)
    try:
        d.yuk.write_text("99\n")
        p = d.agir_is("e", 'touch "$M"', ek_env={"AGIR_IS_TAVAN_SN": "1.0"})
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            return False, "tavan asildi ama agir-is cikmadi"
        hata = p.stderr.read().decode()
        satir = d.satirlar("HAL=KUYRUK-TAVAN", " etiket=e ")
        if p.returncode != 1:
            return False, "rc=%s (beklenen 1)" % p.returncode
        if len(satir) != 1 or "HAL=KUYRUK-TAVAN tur=agir " not in satir[0]:
            return False, "KUYRUK-TAVAN tur=agir satiri yok/bicim disi: %r" % satir
        if "HAL=KUYRUK-TAVAN" not in hata:
            return False, "stderr'de HAL=KUYRUK-TAVAN yok (sessiz dusme)"
        if d.basladi("e"):
            return False, "tavan sonrasi komut KOSTU"
        if d.dolu() != 0:
            return False, "tavan sonrasi slot tutuldu"
        return True, "rc=1 + tek `HAL=KUYRUK-TAVAN tur=agir` satiri + stderr; komut kosmadi"
    finally:
        d.kapat()


def vaka_f():
    """--adet 1 davranisi degismedi: isci-semafor-test tum vakalarda YESIL."""
    r = subprocess.run(["python3", str(SEMAFOR_TEST)], capture_output=True, text=True,
                       timeout=600)
    ozet = [s for s in r.stdout.splitlines() if s.startswith("VAKA=")]
    if r.returncode != 0:
        kirmizi = [s for s in r.stdout.splitlines() if "KIRMIZI" in s or "YASADI" in s]
        return False, "isci-semafor-test rc=%d %s %r" % (r.returncode, ozet, kirmizi)
    return True, "isci-semafor-test rc=0 %s" % (ozet[0] if ozet else "")


def ek_g(agir):
    """ic ice: 1 slot tutan iscinin icinden agir is kalan SINIR-1 slotu alir."""
    d = Dunya(agir)
    try:
        isci = d.isci("i3")
        if not d.bekle(lambda: d.dolu() == 1):
            return False, "isci slot almadi"
        p = d.agir_is("g", 'touch "$M"; sleep 1',
                      ek_env={"PRUVO_ISCI_SEMAFOR_SAHIBI": str(isci.pid)})
        if not d.bekle(lambda: d.basladi("g"), 5):
            return False, "ic ice agir is kendi iscisini bekledi (kilitlenme)"
        alindi = d.satirlar("SEMAFOR=ALINDI", " etiket=g ")
        kalan = SINIR - 1   # adet 1 iken ALINDI satiri `adet=` tasimaz (bayt-ayni bicim)
        adet_ok = (" adet=%d " % kalan in alindi[0]) if alindi and kalan > 1 else (
            bool(alindi) and " adet=" not in alindi[0])
        if len(alindi) != 1 or not adet_ok or d.dolu() != SINIR:
            return False, "ic ice alim %d slot degil: %r dolu=%d" % (kalan, alindi, d.dolu())
        p.wait(timeout=10)
        if p.returncode != 0:
            return False, "rc=%s" % p.returncode
        return True, ("ic ice agir is kalan %d slotu aldi (toplam %d/%d), kilitlenmedi"
                      % (kalan, SINIR, SINIR))
    finally:
        d.kapat()


def ek_h():
    if not KURULU.exists():
        return None, "kurulu kopya yok (CI) — ATLANDI"
    if KURULU.read_bytes() != AGIR.read_bytes():
        return False, "kurulu kopya %s repo kopyasindan FARKLI" % KURULU
    return True, "kurulu agir-is.sh BIREBIR"


def mutant(adi, eski, yeni, vaka):
    tmp = Path(tempfile.mkdtemp(prefix="agir-is-mutant-"))
    try:
        metin = AGIR.read_text(encoding="utf-8")
        if metin.count(eski) != 1:
            return False, "%s capasi %d kez (beklenen 1): %r" % (adi, metin.count(eski), eski)
        kopya = tmp / "agir-is.sh"
        kopya.write_text(metin.replace(eski, yeni), encoding="utf-8")
        ok, neden = vaka(kopya)
        return (not ok), ("OLDURULDU: %s" % neden) if not ok else "HAYATTA KALDI: %s" % neden
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    if not os.path.exists(ZSH):
        print("KIRMIZI zsh bulunamadi (%s) — agir-is.sh OLCULEMEDI" % ZSH)
        print("VAKA=0/6 MUTANT_OLDU=0/2")
        return 1
    sonuc = []
    for ad, fn in (("a", vaka_a), ("b", vaka_b), ("c", vaka_c), ("d", vaka_d), ("e", vaka_e)):
        ok, neden = fn(AGIR)
        sonuc.append(ok)
        print("%s (%s) %s" % ("YESIL" if ok else "KIRMIZI", ad, neden))
    ok, neden = vaka_f()
    sonuc.append(ok)
    print("%s (f) %s" % ("YESIL" if ok else "KIRMIZI", neden))
    ek = []
    ok, neden = ek_g(AGIR)
    ek.append(ok)
    print("%s EK (g) %s" % ("YESIL" if ok else "KIRMIZI", neden))
    ok, neden = ek_h()
    if ok is None:
        print("ATLANDI EK (h) %s" % neden)
    else:
        ek.append(ok)
        print("%s EK (h) %s" % ("YESIL" if ok else "KIRMIZI", neden))
    mutantlar = (
        ("M1 --adet 3->1", "AGIR_ADET=$AGIR_SINIR\n", "AGIR_ADET=1\n", vaka_d),
        ("M2 yuk esigi yok", ' --yuk-esik "$AGIR_YUK_ESIK"', "", vaka_b),
    )
    olen = 0
    for ad, eski, yeni, vaka in mutantlar:
        ok, neden = mutant(ad, eski, yeni, vaka)
        olen += ok
        print("%s %s — %s" % ("MUTANT-OLDU" if ok else "MUTANT-YASADI", ad, neden))
    yesil = sum(sonuc)
    print("EK=%d/%d" % (sum(ek), len(ek)))
    print("VAKA=%d/%d MUTANT_OLDU=%d/%d" % (yesil, len(sonuc), olen, len(mutantlar)))
    tamam = yesil == len(sonuc) and all(ek) and olen == len(mutantlar)
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())

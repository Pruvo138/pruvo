#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISCI-SEMAFOR kabul testi (13 Eki 2026, BaBa 01:2x YEREL YUK hukmu).

Olculen: tools/isci-semafor.py (kurulu kopyasi ~/.claude/cron/isci-semafor.py,
isci.sh motoru cagirmadan once `al`, EXIT/TERM/INT trap'inde `birak` kosar).

HERMETIK: her vaka gecici dizinde kendi slot kokunu / isci.log'unu / HOME'unu
kurar; gercek `~/.claude/cron` ve gercek HOME'a YAZILMAZ. Sahte isci = `sh`
sureci (`al` -> `exec sleep`), sahte 1 dk yuku = PRUVO_ISCI_SEMAFOR_YUK_DOSYASI
ile gosterilen dosya (bekleme sirasinda degistirilir). Yuk YARATILMAZ.

VAKALAR
  (a) 4. isci bekler (HAL=BEKLIYOR sira=1), 3'unden biri biter bitmez baslar
  (b) yuk >12 iken bekler (sebep=yuk), yuk dusunce baslar
  (c) tavan asilir -> rc=64 (isci.sh rc=1) + `HAL=KUYRUK-TAVAN` satiri
  (d) olu PID'li slot geri alinir (SIGKILL'li sahip + bayat isaretci)
  (e) sinyalle (TERM) oldurulen isci trap'te `birak` ile slotunu HEMEN birakir
  (f) kurulu kopya repo kopyasiyla BIREBIR (yalniz kurulu kopya varsa; CI'da ATLANDI)
MUTANTLAR (kopya uzerinde; beklenen KIRMIZI)
  M1 SINIR 3 -> 99            => (a) KIRMIZI
  M2 yuk kolu kaldirilir      => (b) KIRMIZI

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
YARDIMCI = KOK / "isci-semafor.py"
KURULU = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".claude" / "cron" / "isci-semafor.py"

HIZ = ["--aralik-sn", "0.1", "--izle-sn", "0.2", "--satir-sn", "60"]


class Dunya:
    def __init__(self, yardimci):
        self.yardimci = str(yardimci)
        self.kok = Path(tempfile.mkdtemp(prefix="isci-semafor-test-"))
        self.slot = self.kok / "isci-slot"
        self.log = self.kok / "isci.log"
        self.yuk = self.kok / "yuk"
        self.yuk.write_text("1.0\n")
        (self.kok / "home").mkdir()
        self.env = dict(os.environ, HOME=str(self.kok / "home"),
                        PRUVO_ISCI_SEMAFOR_YUK_DOSYASI=str(self.yuk))
        self.surecler = []

    def isci(self, etiket, uyku=30, ek=(), trapli=False):
        arg = " ".join(ek)
        al = ('python3 "$Y" al --sahip $$ --slot-koku "$S" --log "$L" --etiket %s %s %s'
              % (etiket, " ".join(HIZ), arg))
        if trapli:
            govde = ('trap \'python3 "$Y" birak --sahip $$ --slot-koku "$S"; exit 143\' TERM; '
                     '%s || exit $?; sleep %d & wait $!' % (al, uyku))
        else:
            govde = '%s || exit $?; exec sleep %d' % (al, uyku)
        env = dict(self.env, Y=self.yardimci, S=str(self.slot), L=str(self.log))
        p = subprocess.Popen(["/bin/sh", "-c", govde], env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.surecler.append(p)
        return p

    def durum(self):
        r = subprocess.run(["python3", self.yardimci, "durum", "--slot-koku", str(self.slot)],
                           env=self.env, capture_output=True, text=True, timeout=10)
        return r.stdout

    def dolu(self):
        for satir in self.durum().splitlines():
            if satir.startswith("DOLU="):
                return int(satir.split()[0].split("=")[1].split("/")[0])
        return -1

    def log_metni(self):
        return self.log.read_text() if self.log.exists() else ""

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
        # tutucular sahip olunce cikar; kisa bekle ki dizin silinirken yazmasinlar
        time.sleep(0.5)
        shutil.rmtree(self.kok, ignore_errors=True)


def alindi_sayisi(d, etiket):
    return sum(1 for s in d.log_metni().splitlines()
               if s.startswith("SEMAFOR=ALINDI") and (" etiket=%s " % etiket) in s)


def vaka_a(yardimci):
    """4. isci bekler, 3'unden biri biter bitmez baslar."""
    d = Dunya(yardimci)
    try:
        ilk = [d.isci("a%d" % i, uyku=30) for i in (1, 2, 3)]
        if not d.bekle(lambda: d.dolu() == 3):
            return False, "3 slot dolmadi (dolu=%d)" % d.dolu()
        d.isci("a4", uyku=30)
        if not d.bekle(lambda: "HAL=BEKLIYOR" in d.log_metni() and " etiket=a4 " in d.log_metni(), 4):
            return False, "4. isci BEKLIYOR yazmadi (log: %r)" % d.log_metni()[-400:]
        time.sleep(0.6)
        if alindi_sayisi(d, "a4") != 0 or d.dolu() != 3:
            return False, "4. isci sinira ragmen basladi (dolu=%d)" % d.dolu()
        satir = [s for s in d.log_metni().splitlines()
                 if "HAL=BEKLIYOR" in s and " etiket=a4 " in s][0]
        if " sira=1 " not in satir or " bekleme_dk=0 " not in satir or "sebep=slot" not in satir:
            return False, "BEKLIYOR satiri bicim disi: %r" % satir
        t0 = time.monotonic()
        os.killpg(ilk[0].pid, signal.SIGTERM)
        ilk[0].wait(timeout=5)   # gercekte ebeveyn (isci-ayrik) bicer; zombi canli sayilir
        if not d.bekle(lambda: alindi_sayisi(d, "a4") == 1, 5):
            return False, "slot bosaldiginda 4. isci baslamadi"
        gecikme = time.monotonic() - t0
        if d.dolu() != 3:
            return False, "baslangictan sonra dolu=%d (beklenen 3)" % d.dolu()
        return True, "4. isci bekledi (sira=1), slot bosalinca %.2f sn'de basladi, dolu=3" % gecikme
    finally:
        d.kapat()


def vaka_b(yardimci):
    """yuk >12 iken bekler, dusunce baslar."""
    d = Dunya(yardimci)
    try:
        d.yuk.write_text("12.5\n")
        p = d.isci("b1", uyku=30)
        if not d.bekle(lambda: "HAL=BEKLIYOR" in d.log_metni(), 4):
            return False, "yuk 12.5 iken BEKLIYOR yazilmadi"
        time.sleep(0.6)
        if alindi_sayisi(d, "b1") or d.dolu() != 0:
            return False, "yuk 12.5 iken isci basladi (slot bos olmasina ragmen kapi yuk kolunu uygulamadi)"
        if "sebep=yuk" not in d.log_metni():
            return False, "BEKLIYOR satirinda sebep=yuk yok"
        d.yuk.write_text("12.0\n")   # esik >12: 12.0 gecer
        if not d.bekle(lambda: alindi_sayisi(d, "b1") == 1, 5):
            return False, "yuk dustukten sonra isci baslamadi"
        if p.poll() is not None:
            return False, "isci beklenmedik sekilde bitti rc=%s" % p.returncode
        return True, "yuk 12.5'te bekledi (sebep=yuk), 12.0'a dusunce basladi"
    finally:
        d.kapat()


def vaka_c(yardimci):
    """tavan asilir -> rc=64 + HAL=KUYRUK-TAVAN."""
    d = Dunya(yardimci)
    try:
        d.yuk.write_text("99\n")
        p = d.isci("c1", uyku=30, ek=["--tavan-sn", "1.0"])
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            return False, "tavan asildi ama isci cikmadi"
        hata = p.stderr.read().decode()
        satirlar = [s for s in d.log_metni().splitlines() if "HAL=KUYRUK-TAVAN" in s]
        if p.returncode != 64:
            return False, "rc=%s (beklenen 64)" % p.returncode
        if len(satirlar) != 1 or " etiket=c1 " not in satirlar[0] or " rc=1 " not in satirlar[0]:
            return False, "KUYRUK-TAVAN satiri yok/bicim disi: %r" % satirlar
        if "HAL=KUYRUK-TAVAN" not in hata:
            return False, "stderr'de HAL=KUYRUK-TAVAN yok (sessiz dusme)"
        if alindi_sayisi(d, "c1") or d.dolu() != 0:
            return False, "tavan sonrasi slot tutuldu"
        kuyruk = d.slot / ".kuyruk"
        if kuyruk.exists() and list(kuyruk.iterdir()):
            return False, "tavan sonrasi kuyruk girdisi kaldi"
        return True, "rc=64 (isci.sh rc=1) + tek KUYRUK-TAVAN satiri + stderr; kuyruk temiz"
    finally:
        d.kapat()


def vaka_d(yardimci):
    """olu PID'li slot geri alinir (SIGKILL'li sahip + bayat isaretci)."""
    d = Dunya(yardimci)
    try:
        # bayat isaretci: kilidi kimse tutmuyor, sahip PID olu
        d.slot.mkdir(parents=True)
        olu = subprocess.Popen(["true"])
        olu.wait()
        (d.slot / "1").write_text("sahip=%d tutucu=%d slot=1 etiket=bayat\n" % (olu.pid, olu.pid))
        ilk = [d.isci("d%d" % i, uyku=30) for i in (1, 2, 3)]
        if not d.bekle(lambda: d.dolu() == 3):
            return False, "bayat isaretciye ragmen 3 slot dolmadi (dolu=%d)" % d.dolu()
        if "etiket=bayat" in d.durum():
            return False, "bayat isaretcinin uzerine yazilmadi"
        d.isci("d4", uyku=30)
        if not d.bekle(lambda: " etiket=d4 " in d.log_metni(), 4):
            return False, "4. isci BEKLIYOR yazmadi"
        os.killpg(ilk[1].pid, signal.SIGKILL)   # trap yok: yalniz tutucu olumu gorur
        ilk[1].wait(timeout=5)
        if not d.bekle(lambda: alindi_sayisi(d, "d4") == 1, 5):
            return False, "SIGKILL'li sahibin slotu geri alinmadi"
        if d.dolu() != 3:
            return False, "geri alim sonrasi dolu=%d" % d.dolu()
        return True, "bayat isaretci ezildi; SIGKILL'li sahibin slotu tutucu tarafindan birakildi, 4. isci basladi"
    finally:
        d.kapat()


def vaka_e(yardimci):
    """sinyalle oldurulen isci slotunu (trap -> birak) HEMEN birakir."""
    d = Dunya(yardimci)
    try:
        # izle-sn 30: tutucu sahip olumunu 30 sn GORMEZ; serbest birakma yalniz birak'tan gelebilir
        p = d.isci("e1", uyku=60, ek=["--izle-sn", "30"], trapli=True)
        if not d.bekle(lambda: d.dolu() == 1):
            return False, "isci slot almadi"
        t0 = time.monotonic()
        os.kill(p.pid, signal.SIGTERM)
        if not d.bekle(lambda: d.dolu() == 0, 5):
            return False, "TERM sonrasi slot 5 sn icinde birakilmadi"
        sure = time.monotonic() - t0
        p.wait(timeout=5)
        if p.returncode != 143:
            return False, "trap rc=%s (beklenen 143)" % p.returncode
        if (d.slot / "1").exists():
            return False, "isaretci kaldi"
        return True, "TERM -> trap birak -> slot %.2f sn'de bos, isaretci silindi, rc=143" % sure
    finally:
        d.kapat()


def vaka_f():
    if not KURULU.exists():
        return None, "kurulu kopya yok (CI) — ATLANDI"
    if KURULU.read_bytes() != YARDIMCI.read_bytes():
        return False, "kurulu kopya %s repo kopyasindan FARKLI" % KURULU
    return True, "kurulu kopya BIREBIR"


def mutant(adi, eski, yeni, vaka):
    tmp = Path(tempfile.mkdtemp(prefix="isci-semafor-mutant-"))
    try:
        metin = YARDIMCI.read_text(encoding="utf-8")
        if metin.count(eski) != 1:
            return False, "%s capasi %d kez (beklenen 1): %r" % (adi, metin.count(eski), eski)
        kopya = tmp / "isci-semafor.py"
        kopya.write_text(metin.replace(eski, yeni), encoding="utf-8")
        ok, neden = vaka(kopya)
        return (not ok), ("OLDURULDU: %s" % neden) if not ok else "HAYATTA KALDI: %s" % neden
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    sonuc = []
    for ad, fn in (("a", vaka_a), ("b", vaka_b), ("c", vaka_c), ("d", vaka_d), ("e", vaka_e)):
        ok, neden = fn(YARDIMCI)
        sonuc.append(ok)
        print("%s (%s) %s" % ("YESIL" if ok else "KIRMIZI", ad, neden))
    ok, neden = vaka_f()
    if ok is None:
        print("ATLANDI (f) %s" % neden)
    else:
        sonuc.append(ok)
        print("%s (f) %s" % ("YESIL" if ok else "KIRMIZI", neden))
    mutantlar = (
        ("M1 SINIR 3->99", "SINIR = 3\n", "SINIR = 99\n", vaka_a),
        ("M2 yuk kolu yok", "if yuk > a.yuk_esik:", "if False:", vaka_b),
    )
    olen = 0
    for ad, eski, yeni, vaka in mutantlar:
        ok, neden = mutant(ad, eski, yeni, vaka)
        olen += ok
        print("%s %s — %s" % ("MUTANT-OLDU" if ok else "MUTANT-YASADI", ad, neden))
    yesil = sum(sonuc)
    print("VAKA=%d/%d MUTANT_OLDU=%d/%d" % (yesil, len(sonuc), olen, len(mutantlar)))
    return 0 if yesil == len(sonuc) and olen == len(mutantlar) else 1


if __name__ == "__main__":
    sys.exit(main())

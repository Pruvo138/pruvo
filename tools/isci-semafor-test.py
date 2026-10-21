#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISCI-SEMAFOR kabul testi (13 Eki 2026, BaBa 01:2x YEREL YUK hukmu;
21 Eki 2026 BaBa 22:3x: SINIR 3->2, YUK_ESIK 12->6, ARALIK_SN 5->60).

Olculen: tools/isci-semafor.py (kurulu kopyasi ~/.claude/cron/isci-semafor.py,
isci.sh motoru cagirmadan once `al`, EXIT/TERM/INT trap'inde `birak` kosar).

HERMETIK: her vaka gecici dizinde kendi slot kokunu / isci.log'unu / HOME'unu
kurar; gercek `~/.claude/cron` ve gercek HOME'a YAZILMAZ. Sahte isci = `sh`
sureci (`al` -> `exec sleep`), sahte 1 dk yuku = PRUVO_ISCI_SEMAFOR_YUK_DOSYASI
ile gosterilen dosya (bekleme sirasinda degistirilir). Yuk YARATILMAZ.
Esik/sinir VARSAYILANLA olculur (`--sinir`/`--yuk-esik` verilmez).

VAKALAR
  (a) 2 isci kosarken 3. isci bekler (HAL=BEKLIYOR sira=1 dolu=2/2), biri
      biter bitmez baslar
  (b) yuk 6.5 iken bekler (sebep=yuk YUK_KAPISI=6), 5.9'a dusunce baslar
  (c) tavan yuk 6.5'te asilir -> rc=64 (isci.sh rc=1) + `HAL=KUYRUK-TAVAN
      sebep=yuk YUK_KAPISI=6` satiri + stderr (sessiz dusme YOK)
  (d) olu PID'li slot geri alinir (SIGKILL'li sahip + bayat isaretci)
  (e) sinyalle (TERM) oldurulen isci trap'te `birak` ile slotunu HEMEN birakir
  (g) varsayilan aralik 60 sn: yuk 6.5->5.9 dustukten sonra 7 sn icinde
      BASLAMAZ, 60 sn'lik yeniden olcumde baslar; `sinir` alt komutu 2 basar
  (f) kurulu kopya repo kopyasiyla BIREBIR (yalniz kurulu kopya varsa; CI'da ATLANDI)
MUTANTLAR (kopya uzerinde; beklenen KIRMIZI)
  M1 SINIR 2 -> 3             => (a) KIRMIZI
  M2 yuk kolu kaldirilir      => (b) KIRMIZI
  M3 YUK_ESIK 6 -> 12         => (b) KIRMIZI
  M4 ARALIK_SN 60 -> 5        => (g) KIRMIZI

Cikis: hepsi YESIL ve tum mutantlar OLDURULDU ise 0, aksi 1.
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
# (g) icin: aralik VARSAYILAN kalir (60 sn), yalniz izleme hizlanir.
ARALIKSIZ = ["--izle-sn", "0.2", "--satir-sn", "600"]


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

    def isci(self, etiket, uyku=30, ek=(), trapli=False, hiz=HIZ):
        arg = " ".join(ek)
        al = ('python3 "$Y" al --sahip $$ --slot-koku "$S" --log "$L" --etiket %s %s %s'
              % (etiket, " ".join(hiz), arg))
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


def alindi_satirlari(d, etiket):
    return [s for s in d.log_metni().splitlines()
            if s.startswith("SEMAFOR=ALINDI") and (" etiket=%s " % etiket) in s]


def alindi_sayisi(d, etiket):
    return len(alindi_satirlari(d, etiket))


def vaka_a(yardimci):
    """2 isci kosarken 3. isci bekler, biri biter bitmez baslar."""
    d = Dunya(yardimci)
    try:
        ilk = [d.isci("a%d" % i, uyku=30) for i in (1, 2)]
        if not d.bekle(lambda: alindi_sayisi(d, "a1") + alindi_sayisi(d, "a2") == 2):
            return False, "ilk 2 isci slot almadi (dolu=%d)" % d.dolu()
        d.isci("a3", uyku=30)
        if not d.bekle(lambda: "HAL=BEKLIYOR" in d.log_metni() and " etiket=a3 " in d.log_metni(), 4):
            return False, "3. isci BEKLIYOR yazmadi; %d isci ayni anda (log: %r)" % (
                alindi_sayisi(d, "a3") + 2, d.log_metni()[-400:])
        time.sleep(0.6)
        if alindi_sayisi(d, "a3") != 0 or d.dolu() != 2:
            return False, "3. isci sinira ragmen basladi (dolu=%d)" % d.dolu()
        satir = [s for s in d.log_metni().splitlines()
                 if "HAL=BEKLIYOR" in s and " etiket=a3 " in s][0]
        for parca in (" sira=1 ", " bekleme_dk=0 ", "sebep=slot", " dolu=2/2 "):
            if parca not in satir:
                return False, "BEKLIYOR satiri bicim disi (%s yok): %r" % (parca.strip(), satir)
        t0 = time.monotonic()
        os.killpg(ilk[0].pid, signal.SIGTERM)
        ilk[0].wait(timeout=5)   # gercekte ebeveyn (isci-ayrik) bicer; zombi canli sayilir
        if not d.bekle(lambda: alindi_sayisi(d, "a3") == 1, 5):
            return False, "slot bosaldiginda 3. isci baslamadi"
        gecikme = time.monotonic() - t0
        if d.dolu() != 2:
            return False, "baslangictan sonra dolu=%d (beklenen 2)" % d.dolu()
        return True, "3. isci bekledi (sira=1 dolu=2/2), slot bosalinca %.2f sn'de basladi" % gecikme
    finally:
        d.kapat()


def vaka_b(yardimci):
    """yuk 6.5 iken bekler, 5.9'a dusunce baslar."""
    d = Dunya(yardimci)
    try:
        d.yuk.write_text("6.5\n")
        p = d.isci("b1", uyku=30)
        if not d.bekle(lambda: "HAL=BEKLIYOR" in d.log_metni() or alindi_sayisi(d, "b1"), 4):
            return False, "yuk 6.5 iken ne BEKLIYOR ne ALINDI yazildi"
        time.sleep(0.6)
        if alindi_sayisi(d, "b1") or d.dolu() != 0:
            return False, "yuk 6.5 iken isci basladi (esik 6 uygulanmadi)"
        if "sebep=yuk" not in d.log_metni() or " YUK_KAPISI=6 " not in d.log_metni():
            return False, "BEKLIYOR satirinda sebep=yuk / YUK_KAPISI=6 yok: %r" % d.log_metni()[-300:]
        d.yuk.write_text("5.9\n")
        if not d.bekle(lambda: alindi_sayisi(d, "b1") == 1, 5):
            return False, "yuk 5.9'a dustukten sonra isci baslamadi"
        if " YUK_KAPISI=6 " not in alindi_satirlari(d, "b1")[0]:
            return False, "ALINDI satirinda YUK_KAPISI=6 yok: %r" % alindi_satirlari(d, "b1")
        if p.poll() is not None:
            return False, "isci beklenmedik sekilde bitti rc=%s" % p.returncode
        return True, "yuk 6.5'te bekledi (sebep=yuk YUK_KAPISI=6), 5.9'a dusunce basladi"
    finally:
        d.kapat()


def vaka_c(yardimci):
    """tavan yuk 6.5'te asilir -> rc=64 + HAL=KUYRUK-TAVAN sebep=yuk YUK_KAPISI=6."""
    d = Dunya(yardimci)
    try:
        d.yuk.write_text("6.5\n")
        p = d.isci("c1", uyku=30, ek=["--tavan-sn", "1.0"])
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            return False, "tavan asildi ama isci cikmadi"
        hata = p.stderr.read().decode()
        satirlar = [s for s in d.log_metni().splitlines() if "HAL=KUYRUK-TAVAN" in s]
        if p.returncode != 64:
            return False, "rc=%s (beklenen 64; 0 ise yuk 6.5'te basladi)" % p.returncode
        if len(satirlar) != 1:
            return False, "KUYRUK-TAVAN satiri yok/coklu: %r" % satirlar
        for parca in (" etiket=c1 ", " rc=1 ", " sebep=yuk ", " yuk=6.50 ", " YUK_KAPISI=6 "):
            if parca not in satirlar[0]:
                return False, "KUYRUK-TAVAN satiri bicim disi (%s yok): %r" % (parca.strip(), satirlar[0])
        if "HAL=KUYRUK-TAVAN" not in hata or "YUK_KAPISI=6" not in hata:
            return False, "stderr'de HAL=KUYRUK-TAVAN/YUK_KAPISI=6 yok (sessiz dusme)"
        if alindi_sayisi(d, "c1") or d.dolu() != 0:
            return False, "tavan sonrasi slot tutuldu"
        kuyruk = d.slot / ".kuyruk"
        if kuyruk.exists() and list(kuyruk.iterdir()):
            return False, "tavan sonrasi kuyruk girdisi kaldi"
        return True, ("yuk 6.5'te tavan: rc=64 (isci.sh rc=1) + tek KUYRUK-TAVAN satiri "
                      "(sebep=yuk YUK_KAPISI=6) + stderr; kuyruk temiz")
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
        ilk = [d.isci("d%d" % i, uyku=30) for i in (1, 2)]
        if not d.bekle(lambda: d.dolu() == 2):
            return False, "bayat isaretciye ragmen 2 slot dolmadi (dolu=%d)" % d.dolu()
        if "etiket=bayat" in d.durum():
            return False, "bayat isaretcinin uzerine yazilmadi"
        d.isci("d3", uyku=30)
        if not d.bekle(lambda: " etiket=d3 " in d.log_metni(), 4):
            return False, "3. isci BEKLIYOR yazmadi"
        os.killpg(ilk[1].pid, signal.SIGKILL)   # trap yok: yalniz tutucu olumu gorur
        ilk[1].wait(timeout=5)
        if not d.bekle(lambda: alindi_sayisi(d, "d3") == 1, 5):
            return False, "SIGKILL'li sahibin slotu geri alinmadi"
        if d.dolu() != 2:
            return False, "geri alim sonrasi dolu=%d" % d.dolu()
        return True, "bayat isaretci ezildi; SIGKILL'li sahibin slotu tutucu tarafindan birakildi, 3. isci basladi"
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


def vaka_g(yardimci):
    """varsayilan aralik 60 sn: yuk duser, 7 sn icinde baslamaz, ~60 sn'de baslar."""
    r = subprocess.run(["python3", str(yardimci), "sinir"], capture_output=True, text=True,
                       timeout=10)
    if r.returncode != 0 or r.stdout.strip() != "2":
        return False, "`sinir` alt komutu 2 basmadi: rc=%s %r" % (r.returncode, r.stdout)
    d = Dunya(yardimci)
    try:
        d.yuk.write_text("6.5\n")
        p = d.isci("g1", uyku=30, hiz=ARALIKSIZ)
        if not d.bekle(lambda: "HAL=BEKLIYOR" in d.log_metni() or alindi_sayisi(d, "g1"), 4):
            return False, "yuk 6.5 iken ne BEKLIYOR ne ALINDI yazildi"
        if alindi_sayisi(d, "g1"):
            return False, "yuk 6.5 iken isci basladi"
        t0 = time.monotonic()
        d.yuk.write_text("5.9\n")
        if d.bekle(lambda: alindi_sayisi(d, "g1") == 1, 7):
            return False, ("yuk dustukten %.1f sn sonra basladi: yeniden olcum araligi 60 sn "
                           "degil" % (time.monotonic() - t0))
        if not d.bekle(lambda: alindi_sayisi(d, "g1") == 1, 60):
            return False, "60 sn'lik yeniden olcumde de baslamadi"
        gecikme = time.monotonic() - t0
        if p.poll() is not None:
            return False, "isci beklenmedik sekilde bitti rc=%s" % p.returncode
        return True, ("`sinir`=2; yuk 6.5->5.9: 7 sn icinde baslamadi, %.1f sn'de yeniden "
                      "olcumle basladi (aralik 60 sn)" % gecikme)
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
    for ad, fn in (("a", vaka_a), ("b", vaka_b), ("c", vaka_c), ("d", vaka_d), ("e", vaka_e),
                   ("g", vaka_g)):
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
        ("M1 SINIR 2->3", "SINIR = 2\n", "SINIR = 3\n", vaka_a),
        ("M2 yuk kolu yok", "if yuk > a.yuk_esik:", "if False:", vaka_b),
        ("M3 YUK_ESIK 6->12", "YUK_ESIK = 6.0\n", "YUK_ESIK = 12.0\n", vaka_b),
        ("M4 ARALIK_SN 60->5", "ARALIK_SN = 60.0\n", "ARALIK_SN = 5.0\n", vaka_g),
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

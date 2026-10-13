#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AGIR-IS BEKCISI kabul testi (13 Eki 2026, BaBa 06:5x hukmu).

OLAY: `agir-is.sh --etiket far-mutant -- node .../mutant.mjs` 04:25'ten beri
%0 CPU ile 3/3 slotu tuttu; filonun tum iscileri bekledi. Kapi: agir isin
slot tutucusu bekcidir — tavan (`--tavan-dk`) ya da asili (`--asili-dk`,
agac CPU'su kesintisiz <%5) -> KOMUT GRUBUNA TERM -> bekle -> KILL, slotlar
birakilir, agir-is.sh rc=124.

Olculen: tools/agir-is.sh + tools/isci-semafor.py (`al --tur agir` bekcisi,
`grup` yardimcisi, BEKLIYOR satirinin `TUTAN=` alani).

HERMETIK: her vaka gecici dizinde kendi slot kokunu / isci.log'unu / HOME'unu
kurar; gercek `~/.claude/cron` ve gercek HOME'a YAZILMAZ. Sahte zaman =
kisaltilmis sureler (`--tavan-dk 0.02`, `--asili-dk 0.02`,
AGIR_IS_ORNEK_SN=0.2, AGIR_IS_OLUM_BEKLE_SN=1.5); sahte agac CPU'su =
PRUVO_AGIR_CPU_DOSYASI dosyasi. Komut = `sh` lideri + arka plan `sleep`
torunu (gercek yuk YOK). agir-is.sh bir `sh` EBEVEYNI altinda kosar (ayri
oturum): ebeveyn agir-is.sh'nin rc'sini dosyaya yazar — yazabiliyorsa
oldurme onu vurmamistir.

VAKALAR
  V1 tavan asimi -> `HAL=TAVAN-OLDU tur=agir .. etiket .. pid .. sure_dk`,
     rc 124, slot bos (DOLU=0, isaretci yok)
  V2 TERM'i yok sayan komut -> bekle (1.5 sn) sonra `SEMAFOR=KILL`, grup olu
  V3 asili (sahte CPU 0) -> `HAL=ASILI-OLDU`, rc 124, slot bos
  V4 mesgul (sahte CPU 50) uzun kosum OLDURULMEZ (asili penceresinin 3 kati)
  V5 normal bitis -> rc AYNEN (7), slot bos, oldurme satiri 0
  V6 bekleyenin BEKLIYOR satiri `TUTAN=<etiket>:<pid>:<t>` (isci + agir bekleyen)
  V7 yalniz komut grubu oldu: lider + torun olu, agir-is.sh rc 124 (sinyal
     YEMEDI), ebeveyni yasiyor
EK (VAKA sayimina girmez, kirmizisi yine rc=1)
  S  sahip (agir-is.sh) SIGKILL -> sahipsiz komut grubu `HAL=SAHIPSIZ-OLDU`, slot bos
MUTANTLAR (isci-semafor.py kopyasi; beklenen KIRMIZI)
  M1 tavan kontrolu kaldirildi              => V1 KIRMIZI
  M2 asili esigi sonsuz                     => V3 KIRMIZI
  M3 grup yerine yalniz sahip pid oldurulur => V7 KIRMIZI

Cikis: hepsi YESIL ve uc mutant da OLDURULDU ise 0, aksi 1.
"""

import os
import re
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
ZSH = shutil.which("zsh") or "/bin/zsh"   # CI (ubuntu) adimi zsh'yi kurar

UZUN = 'echo $$ > "$M"; sleep 60 & echo $! > "$T"; wait'
TERMSIZ = 'trap "" TERM; echo $$ > "$M"; sleep 60 & echo $! > "$T"; wait'


def canli(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # zombi canli gorunur; ps durumuna bak
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return bool(r.stdout.strip()) and not r.stdout.strip().startswith("Z")


class Dunya:
    def __init__(self, yardimci, cpu="50"):
        self.yardimci = str(yardimci)
        self.kok = Path(tempfile.mkdtemp(prefix="agir-tavan-test-"))
        self.slot = self.kok / "isci-slot"
        self.log = self.kok / "isci.log"
        self.yuk = self.kok / "yuk"
        self.yuk.write_text("1.0\n")
        self.cpu = self.kok / "cpu"
        self.cpu.write_text(cpu + "\n")
        (self.kok / "home").mkdir()
        (self.kok / "cron").mkdir()
        env = dict(os.environ)
        env.pop("PRUVO_ISCI_SEMAFOR_SAHIBI", None)
        env.update(HOME=str(self.kok / "home"),
                   PRUVO_ISCI_SEMAFOR_YUK_DOSYASI=str(self.yuk),
                   PRUVO_AGIR_CPU_DOSYASI=str(self.cpu),
                   AGIR_IS_CRON_KOKU=str(self.kok / "cron"),
                   AGIR_IS_SEMAFOR=self.yardimci,
                   AGIR_IS_SLOT_KOKU=str(self.slot),
                   AGIR_IS_LOG=str(self.log),
                   AGIR_IS_ARALIK_SN="0.1", AGIR_IS_IZLE_SN="0.2", AGIR_IS_SATIR_SN="60",
                   AGIR_IS_ORNEK_SN="0.2", AGIR_IS_OLUM_BEKLE_SN="1.5")
        self.env = env
        self.surecler = []

    def yol(self, ad, etiket):
        return self.kok / ("%s-%s" % (ad, etiket))

    def agir_is(self, etiket, govde, *arg):
        """Ebeveyn `sh` (ayri oturum) -> agir-is.sh -> grup -> `sh -c govde`."""
        env = dict(self.env, A=str(AGIR), Z=ZSH, G=govde,
                   M=str(self.yol("lider", etiket)), T=str(self.yol("torun", etiket)),
                   P=str(self.yol("agirpid", etiket)), R=str(self.yol("rc", etiket)))
        betik = ('"$Z" "$A" --etiket %s %s -- /bin/sh -c "$G" & echo $! > "$P"; '
                 'wait $!; echo $? > "$R"' % (etiket, " ".join(arg)))
        p = subprocess.Popen(["/bin/sh", "-c", betik], env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.surecler.append(p)
        return p

    def isci(self, etiket, uyku=30):
        al = ('python3 "$Y" al --sahip $$ --slot-koku "$S" --log "$L" --etiket %s '
              '--aralik-sn 0.1 --izle-sn 0.2 --satir-sn 60' % etiket)
        env = dict(self.env, Y=self.yardimci, S=str(self.slot), L=str(self.log))
        p = subprocess.Popen(["/bin/sh", "-c", '%s || exit $?; exec sleep %d' % (al, uyku)],
                             env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.surecler.append(p)
        return p

    def sayi(self, ad, etiket):
        try:
            return int(self.yol(ad, etiket).read_text().strip())
        except (OSError, ValueError):
            return None

    def dolu(self):
        r = subprocess.run(["python3", self.yardimci, "durum", "--slot-koku", str(self.slot)],
                           env=self.env, capture_output=True, text=True, timeout=10)
        for satir in r.stdout.splitlines():
            if satir.startswith("DOLU="):
                return int(satir.split()[0].split("=")[1].split("/")[0])
        return -1

    def slot_bos(self):
        isaretci = [a for a in os.listdir(self.slot) if a.isdigit()] if self.slot.exists() else []
        return self.dolu() == 0 and not isaretci

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
        pidler = []
        for ad in ("lider", "torun"):
            for f in self.kok.glob(ad + "-*"):
                try:
                    pidler.append(int(f.read_text().strip()))
                except (OSError, ValueError):
                    pass
        for p in self.surecler:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
        for pid in pidler:
            for fn in (os.killpg, os.kill):
                try:
                    fn(pid, signal.SIGKILL)
                except OSError:
                    pass
        for p in self.surecler:
            try:
                p.wait(timeout=5)
            except Exception:
                pass
        time.sleep(0.5)   # tutucular sahip olunce cikar; dizin silinirken yazmasinlar
        shutil.rmtree(self.kok, ignore_errors=True)


def oldurme_kaniti(d, etiket, hal):
    """Ortak: rc 124, HAL satiri bicimi, slot bos. (ok, neden)"""
    if not d.bekle(lambda: d.sayi("rc", etiket) is not None, 10):
        return False, "agir-is.sh bitmedi / ebeveyn rc yazmadi (log: %r)" % d.log_metni()[-300:]
    rc = d.sayi("rc", etiket)
    if rc != 124:
        return False, "rc=%s (beklenen 124)" % rc
    pid = d.sayi("agirpid", etiket)
    satir = d.satirlar("HAL=%s tur=agir " % hal, " etiket=%s " % etiket)
    if len(satir) != 1:
        return False, "`HAL=%s tur=agir etiket=%s` satiri %d kez" % (hal, etiket, len(satir))
    if not re.search(r" pid=%d sure_dk=\d+\.\d " % pid, satir[0]):
        return False, "HAL satirinda pid=%d sure_dk= yok: %r" % (pid, satir[0])
    if not d.bekle(d.slot_bos, 6):
        return False, "oldurme sonrasi slot BOS degil (dolu=%d)" % d.dolu()
    return True, satir[0]


def v1(yardimci):
    d = Dunya(yardimci, cpu="50")
    try:
        d.agir_is("v1", UZUN, "--tavan-dk", "0.02", "--asili-dk", "0")
        ok, neden = oldurme_kaniti(d, "v1", "TAVAN-OLDU")
        if not ok:
            return False, neden
        if d.satirlar("SEMAFOR=KILL"):
            return False, "TERM'e uyan komut icin gereksiz KILL"
        return True, "tavan -> TERM, rc 124, slot bos; satir: %s" % neden.split(" HAL=")[1][:80]
    finally:
        d.kapat()


def v2(yardimci):
    d = Dunya(yardimci, cpu="50")
    try:
        t0 = time.monotonic()
        d.agir_is("v2", TERMSIZ, "--tavan-dk", "0.02", "--asili-dk", "0")
        ok, neden = oldurme_kaniti(d, "v2", "TAVAN-OLDU")
        if not ok:
            return False, neden
        if not d.satirlar("SEMAFOR=KILL", " etiket=v2 ", "sebep=TERM-sonrasi-canli"):
            return False, "TERM'i yok sayan komut icin SEMAFOR=KILL satiri yok"
        lider, torun = d.sayi("lider", "v2"), d.sayi("torun", "v2")
        if not d.bekle(lambda: not canli(lider) and not canli(torun), 4):
            return False, "KILL sonrasi lider/torun canli"
        sure = time.monotonic() - t0
        if sure < 1.2 + 1.5:
            return False, "KILL bekleme suresinden once geldi (%.1f sn)" % sure
        return True, "TERM yok sayildi -> 1.5 sn sonra KILL, grup olu (%.1f sn)" % sure
    finally:
        d.kapat()


def v3(yardimci):
    d = Dunya(yardimci, cpu="0")
    try:
        d.agir_is("v3", UZUN, "--tavan-dk", "90", "--asili-dk", "0.02")
        ok, neden = oldurme_kaniti(d, "v3", "ASILI-OLDU")
        if not ok:
            return False, neden
        return True, "CPU 0 -> ASILI-OLDU, rc 124, slot bos"
    finally:
        d.kapat()


def v4(yardimci):
    d = Dunya(yardimci, cpu="50")
    try:
        d.agir_is("v4", UZUN, "--tavan-dk", "90", "--asili-dk", "0.02")
        if not d.bekle(lambda: d.sayi("torun", "v4") is not None, 8):
            return False, "komut baslamadi (log: %r)" % d.log_metni()[-300:]
        time.sleep(3.6)   # asili penceresi 1.2 sn'nin 3 kati
        if d.sayi("rc", "v4") is not None:
            return False, "mesgul agir is bitirildi (rc=%s)" % d.sayi("rc", "v4")
        if d.satirlar("-OLDU"):
            return False, "mesgul is icin oldurme satiri: %r" % d.satirlar("-OLDU")
        if not canli(d.sayi("torun", "v4")) or d.dolu() != 3:
            return False, "mesgul is agaci/slotu dustu (dolu=%d)" % d.dolu()
        return True, "CPU %50 ile 3.6 sn (asili 1.2 sn) kosum OLDURULMEDI, dolu=3"
    finally:
        d.kapat()


def v5(yardimci):
    d = Dunya(yardimci, cpu="50")
    try:
        d.agir_is("v5", 'echo $$ > "$M"; sleep 0.5; exit 7')
        if not d.bekle(lambda: d.sayi("rc", "v5") is not None, 10):
            return False, "agir-is.sh bitmedi"
        if d.sayi("rc", "v5") != 7:
            return False, "rc=%s (beklenen 7 AYNEN)" % d.sayi("rc", "v5")
        if not d.bekle(d.slot_bos, 5):
            return False, "normal bitiste slot BOS degil (dolu=%d)" % d.dolu()
        if d.satirlar("-OLDU") or d.satirlar("SEMAFOR=KILL"):
            return False, "normal bitiste oldurme satiri var"
        if (d.slot / ".oldu" / str(d.sayi("agirpid", "v5"))).exists():
            return False, ".oldu isareti kaldi"
        return True, "rc 7 AYNEN, slot bos, oldurme 0"
    finally:
        d.kapat()


def v6(yardimci):
    d = Dunya(yardimci, cpu="50")
    try:
        d.agir_is("tutan", UZUN)
        if not d.bekle(lambda: d.satirlar("SEMAFOR=ALINDI", " etiket=tutan "), 8):
            return False, "tutan agir is slot almadi"
        pid = d.sayi("agirpid", "tutan")
        isaretci = (d.slot / "1").read_text()
        t = re.search(r" t=(\S+)", isaretci).group(1)
        beklenen = " TUTAN=tutan:%d:%s " % (pid, t)
        d.isci("w1")
        d.agir_is("w2", UZUN)
        if not d.bekle(lambda: d.satirlar("HAL=BEKLIYOR", " etiket=w1 ")
                       and d.satirlar("HAL=BEKLIYOR", " etiket=w2 "), 8):
            return False, "bekleyenler BEKLIYOR yazmadi (log: %r)" % d.log_metni()[-300:]
        for etiket in ("w1", "w2"):
            satir = d.satirlar("HAL=BEKLIYOR", " etiket=%s " % etiket)[0]
            if beklenen not in satir:
                return False, "%s BEKLIYOR satirinda %r yok: %r" % (etiket, beklenen.strip(), satir)
        if not re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", t):
            return False, "baslangic utc bicim disi: %r" % t
        return True, "isci+agir bekleyen%s" % beklenen.rstrip()
    finally:
        d.kapat()


def v7(yardimci):
    d = Dunya(yardimci, cpu="50")
    try:
        ebeveyn = d.agir_is("v7", UZUN, "--tavan-dk", "0.02", "--asili-dk", "0")
        if not d.bekle(lambda: d.sayi("torun", "v7") is not None, 8):
            return False, "komut baslamadi"
        lider, torun = d.sayi("lider", "v7"), d.sayi("torun", "v7")
        agir = d.sayi("agirpid", "v7")
        if os.getpgid(lider) == os.getpgid(agir):
            return False, "komut agir-is.sh ile AYNI grupta (pgid %d)" % os.getpgid(agir)
        if not d.bekle(lambda: d.sayi("rc", "v7") is not None, 10):
            return False, "ebeveyn rc yazmadi (oldurme ebeveyni vurdu?)"
        if d.sayi("rc", "v7") != 124:
            return False, "agir-is.sh rc=%s (124 degil: sinyal yedi)" % d.sayi("rc", "v7")
        if not d.bekle(lambda: not canli(lider) and not canli(torun), 4):
            return False, "komut agaci yasiyor (lider=%s torun=%s)" % (canli(lider), canli(torun))
        if ebeveyn.wait(timeout=5) != 0:
            return False, "ebeveyn rc=%s" % ebeveyn.returncode
        return True, "lider+torun olu, agir-is.sh rc 124, ebeveyn yasadi ve 0 ile cikti"
    finally:
        d.kapat()


def ek_s(yardimci):
    d = Dunya(yardimci, cpu="50")
    try:
        d.agir_is("s", UZUN)
        if not d.bekle(lambda: d.sayi("torun", "s") is not None, 8):
            return False, "komut baslamadi"
        torun = d.sayi("torun", "s")
        time.sleep(0.6)   # bekci en az bir ornek alsin (grup bilinsin)
        os.kill(d.sayi("agirpid", "s"), signal.SIGKILL)
        if not d.bekle(lambda: d.satirlar("HAL=SAHIPSIZ-OLDU", " etiket=s "), 8):
            return False, "sahip KILL sonrasi SAHIPSIZ-OLDU yok"
        if not d.bekle(lambda: not canli(torun), 4):
            return False, "sahipsiz komut agaci yasiyor"
        if not d.bekle(d.slot_bos, 6):
            return False, "slot BOS degil"
        return True, "sahip KILL -> sahipsiz grup olduruldu, slot bos"
    finally:
        d.kapat()


def mutant(adi, eski, yeni, vaka):
    tmp = Path(tempfile.mkdtemp(prefix="agir-tavan-mutant-"))
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


GONDER = '''    for g in gruplar:
        try:
            os.killpg(g, sig)
        except OSError:
            pass
    for p in pidler:
        try:
            os.kill(p, sig)
        except OSError:
            pass
'''


def main():
    if not os.path.exists(ZSH):
        print("KIRMIZI zsh bulunamadi (%s) — agir-is.sh OLCULEMEDI" % ZSH)
        print("VAKA=0/7 MUTANT_OLDU=0/3")
        return 1
    sonuc = []
    for ad, fn in (("V1", v1), ("V2", v2), ("V3", v3), ("V4", v4), ("V5", v5),
                   ("V6", v6), ("V7", v7)):
        ok, neden = fn(YARDIMCI)
        sonuc.append(ok)
        print("%s %s %s" % ("YESIL" if ok else "KIRMIZI", ad, neden))
    ok_s, neden = ek_s(YARDIMCI)
    print("%s EK S %s" % ("YESIL" if ok_s else "KIRMIZI", neden))
    mutantlar = (
        ("M1 tavan kontrolu yok", "if tavan_sn and simdi - bas >= tavan_sn:", "if False:", v1),
        ("M2 asili esigi sonsuz", "asili_sn = a.asili_dk * 60", 'asili_sn = float("inf")', v3),
        ("M3 yalniz sahip pid", GONDER,
         "    try:\n        os.kill(sahip, sig)\n    except OSError:\n        pass\n", v7),
    )
    olen = 0
    for ad, eski, yeni, vaka in mutantlar:
        ok, neden = mutant(ad, eski, yeni, vaka)
        olen += ok
        print("%s %s — %s" % ("MUTANT-OLDU" if ok else "MUTANT-YASADI", ad, neden))
    yesil = sum(sonuc)
    print("EK=%d/1" % ok_s)
    print("VAKA=%d/%d MUTANT_OLDU=%d/%d" % (yesil, len(sonuc), olen, len(mutantlar)))
    return 0 if yesil == len(sonuc) and ok_s and olen == len(mutantlar) else 1


if __name__ == "__main__":
    sys.exit(main())

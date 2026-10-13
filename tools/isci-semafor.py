#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISCI-SEMAFOR — makine-geneli isci eszamanlilik kapisi (13 Eki 2026, BaBa 01:2x).

NEDEN: 12 eszamanli cip + m3 iscileri `uptime` 1 dk yukunu 45-82'ye cikardi
(esik <=8; 11 Eki host kesintisi dersi). `~/.claude/cron/isci.sh` her kosumda
motoru cagirmadan ONCE bu yardimciyla slot alir:

  * Ayni anda en fazla SINIR (3) isci (m3 + claude, tum evler). 4.+ isci
    kuyrukta BEKLER (FIFO: yalniz kuyruk basi slot dener).
  * 1 dk yuku > YUK_ESIK (12) iken yeni isci baslamaz (ayni bekleme dongusu).
  * Beklerken her SATIR_SN'de (20 dk) isci.log'a tek satir
    `HAL=BEKLIYOR etiket=<..> sira=<n> bekleme_dk=<n>`; TAVAN_SN (90 dk)
    dolunca `HAL=KUYRUK-TAVAN` satiri + rc=64 (isci.sh rc=1'e cevirir).
    Sessiz dusme YOK.

TASINABILIR SEMAFOR (macOS'ta `flock` ikilisi YOK): slot kilidi
`<slot-koku>/.kilit/<n>` dosyasinda fcntl.flock(LOCK_EX|LOCK_NB). Kilidi alan
bekleyici sureci fork eder; cocuk (TUTUCU) yeni oturuma gecer, kilitli fd'yi
TEK basina tasir ve sahibin (isci.sh $$) PID'ini IZLE_SN'de bir yoklar. Sahip
olunce (normal cikis, TERM/INT, hatta SIGKILL) tutucu kendiliginden cikar ->
cekirdek kilidi birakir: OLU PID'li slot geri alinir, bayat kilit kalamaz.
isci.sh EXIT/TERM/INT trap'i `birak` ile tutucuyu hemen sonlandirir.
Doluluk isaretcisi `<slot-koku>/<n>` (sahip/tutucu/etiket); `ls <slot-koku>`
en fazla SINIR ad gosterir. Isaretci kilidi bos bir slotta kaldiysa BAYATTIR
(`durum` gosterir), bir sonraki alan uzerine yazar.

COKLU SLOT (13 Eki 2026, BaBa 02:4x — agir-is kapisi): `al --adet N` N slotun
HEPSINI ATOMIK alir ya da HICBIRINI almaz (kismi tutup kilitlenme YOK): kuyruk
basi slotlari LOCK_NB ile dener, N'e ulasamazsa aldiklarini HEMEN birakip bekler
(FIFO: arkadaki isciler sira bekler, agir is ac kalmaz). N fd'yi TEK tutucu
tasir; her slotun isaretcisi ayni tutucuyu gosterir. `--adet 1` (varsayilan)
davranisi ve log satirlari onceki surumle BAYT-AYNI. `--tur X` log satirlarina
`tur=X` ekler (agir-is.sh: `tur=agir`). Sarmalayici: ~/.claude/cron/agir-is.sh
(kaynak tools/agir-is.sh, kabul tools/agir-is-test.py).

RC (al): 0 slot alindi · 64 KUYRUK-TAVAN · 65 sahip beklerken oldu ·
2 kullanim · 70 ic hata (isci.sh FAIL-OPEN: `SEMAFOR=OLCULEMEDI` satiri).

Kabul: tools/isci-semafor-test.py (hermetik). Kurulu kopya
`~/.claude/cron/isci-semafor.py` bu dosyanin BIREBIR kopyasidir (test esitligi
yerelde olcer; CI'da kurulu kopya yoktur).
"""

import argparse
import fcntl
import os
import signal
import sys
import time

SINIR = 3
YUK_ESIK = 12.0
TAVAN_SN = 90 * 60
SATIR_SN = 20 * 60
ARALIK_SN = 5.0
IZLE_SN = 2.0

RC_TAVAN = 64
RC_SAHIP_OLDU = 65
RC_IC_HATA = 70

# Test kancasi: dosyadaki sayi 1 dk yuku yerine okunur (bekleme sirasinda
# degistirilebilsin diye deger degil DOSYA). Bos/okunamaz -> gercek yuk.
YUK_DOSYASI_ENV = "PRUVO_ISCI_SEMAFOR_YUK_DOSYASI"


def damga():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def canli(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def yuk_oku():
    yol = os.environ.get(YUK_DOSYASI_ENV, "")
    if yol:
        try:
            with open(yol, encoding="utf-8") as f:
                return float(f.read().strip())
        except (OSError, ValueError):
            pass
    return os.getloadavg()[0]   # == sysctl -n vm.loadavg ilk alan


def log_yaz(log, satir):
    if not log:
        return
    try:
        with open(log, "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except OSError:
        sys.stderr.write(satir + "\n")


def dizinler(kok):
    kilit = os.path.join(kok, ".kilit")
    kuyruk = os.path.join(kok, ".kuyruk")
    os.makedirs(kilit, mode=0o700, exist_ok=True)
    os.makedirs(kuyruk, mode=0o700, exist_ok=True)
    return kilit, kuyruk


def kuyruk_listesi(kuyruk):
    """Canli bekleyicilerin girdileri (eskiden yeniye). Olu girdi silinir."""
    canlilar = []
    for ad in os.listdir(kuyruk):
        parca = ad.split("-")
        if len(parca) != 3 or not all(p.isdigit() for p in parca):
            continue
        if canli(int(parca[2])):
            canlilar.append(ad)
        else:
            try:
                os.unlink(os.path.join(kuyruk, ad))
            except OSError:
                pass
    return sorted(canlilar, key=lambda a: (int(a.split("-")[0]), a))


def kilit_dene(kilit_dizini, sinir, adet=1):
    """Bos ilk `adet` slotu kilitler: ([n..], [fd..]) ya da (None, None).

    Hep-ya-hic: `adet`e ulasilamazsa alinan kilitler kapatilarak birakilir.
    """
    alinan, fdler = [], []
    for n in range(1, sinir + 1):
        fd = os.open(os.path.join(kilit_dizini, str(n)), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            continue
        alinan.append(n)
        fdler.append(fd)
        if len(alinan) == adet:
            return alinan, fdler
    for fd in fdler:
        os.close(fd)
    return None, None


def dolu_say(kilit_dizini, sinir):
    dolu = 0
    for n in range(1, sinir + 1):
        yol = os.path.join(kilit_dizini, str(n))
        if not os.path.exists(yol):
            continue
        fd = os.open(yol, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            dolu += 1
        finally:
            os.close(fd)
    return dolu


def isaretci_oku(yol):
    alan = {}
    try:
        with open(yol, encoding="utf-8") as f:
            for parca in f.read().split():
                if "=" in parca:
                    k, v = parca.split("=", 1)
                    alan[k] = v
    except OSError:
        pass
    return alan


def tutucu_ol(fdler, sahip, isaretciler, izle_sn):
    """Cocuk: kilitli fd'leri tasir, sahip olunce isaretcileri silip cikar."""
    os.setsid()
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    benim = os.getpid()

    def bitir(*_):
        for isaretci in isaretciler:
            if isaretci_oku(isaretci).get("tutucu") == str(benim):
                try:
                    os.unlink(isaretci)
                except OSError:
                    pass
        os._exit(0)

    signal.signal(signal.SIGTERM, bitir)
    signal.signal(signal.SIGINT, bitir)
    # Cagiranin borularini (isci-ayrik stdout/stderr/rc) TASIMA: EOF'u geciktirmesin.
    bos = os.open(os.devnull, os.O_RDWR)
    for hedef in (0, 1, 2):
        os.dup2(bos, hedef)
    for acik in range(3, 256):
        if acik not in fdler:
            try:
                os.close(acik)
            except OSError:
                pass
    while canli(sahip):
        time.sleep(izle_sn)
    bitir()


def al(a):
    kilit_dizini, kuyruk = dizinler(a.slot_koku)
    benim = os.getpid()
    girdi = os.path.join(kuyruk, "%d-%d-%d" % (time.time_ns(), a.sahip, benim))
    with open(girdi, "w", encoding="utf-8") as f:
        f.write("etiket=%s ev=%s motor=%s\n" % (a.etiket, a.ev, a.motor))

    def girdiyi_sil(*_):
        try:
            os.unlink(girdi)
        except OSError:
            pass

    def sinyalle(*_):
        girdiyi_sil()
        os._exit(RC_SAHIP_OLDU)

    signal.signal(signal.SIGTERM, sinyalle)
    signal.signal(signal.SIGINT, sinyalle)
    ortak = ("tur=%s " % a.tur if a.tur else "") + "motor=%s ev=%s etiket=%s" % (
        a.motor, a.ev, a.etiket)
    bas = time.monotonic()
    sonraki_satir = bas
    while True:
        if not canli(a.sahip):
            girdiyi_sil()
            return RC_SAHIP_OLDU
        yuk = yuk_oku()
        sira_listesi = kuyruk_listesi(kuyruk)
        ad = os.path.basename(girdi)
        sira = sira_listesi.index(ad) + 1 if ad in sira_listesi else len(sira_listesi) + 1
        if yuk > a.yuk_esik:
            sebep = "yuk"
        elif sira > 1:
            sebep = "sira"
        else:
            nler, fdler = kilit_dene(kilit_dizini, a.sinir, a.adet)
            if nler is not None:
                isaretciler = [os.path.join(a.slot_koku, str(n)) for n in nler]
                cocuk = os.fork()
                if cocuk == 0:
                    try:
                        tutucu_ol(fdler, a.sahip, isaretciler, a.izle_sn)
                    finally:
                        os._exit(0)
                for fd in fdler:
                    os.close(fd)
                bekleme = int(time.monotonic() - bas)
                for n, isaretci in zip(nler, isaretciler):
                    with open(isaretci, "w", encoding="utf-8") as f:
                        f.write("sahip=%d tutucu=%d slot=%d %s t=%s\n"
                                % (a.sahip, cocuk, n, ortak, damga()))
                girdiyi_sil()
                log_yaz(a.log, "SEMAFOR=ALINDI slot=%s/%d%s bekleme_sn=%d yuk=%.2f %s pid=%d"
                        % (",".join(str(n) for n in nler), a.sinir,
                           " adet=%d" % a.adet if a.adet > 1 else "", bekleme, yuk, ortak,
                           a.sahip))
                return 0
            sebep = "slot"
        gecen = time.monotonic() - bas
        dolu = dolu_say(kilit_dizini, a.sinir)
        if gecen >= a.tavan_sn:
            girdiyi_sil()
            log_yaz(a.log, "=== %s HAL=KUYRUK-TAVAN %s sira=%d bekleme_dk=%d sebep=%s yuk=%.2f "
                    "dolu=%d/%d tavan_dk=%d rc=1 pid=%d ==="
                    % (damga(), ortak, sira, int(gecen // 60), sebep, yuk, dolu, a.sinir,
                       int(a.tavan_sn // 60), a.sahip))
            sys.stderr.write("HATA: HAL=KUYRUK-TAVAN rc=1 — %d dk bekledi (sebep=%s yuk=%.2f "
                             "dolu=%d/%d), isci BASLATILMADI.\n"
                             % (int(gecen // 60), sebep, yuk, dolu, a.sinir))
            return RC_TAVAN
        if time.monotonic() >= sonraki_satir:
            log_yaz(a.log, "=== %s HAL=BEKLIYOR %s sira=%d bekleme_dk=%d sebep=%s yuk=%.2f "
                    "dolu=%d/%d pid=%d ==="
                    % (damga(), ortak, sira, int(gecen // 60), sebep, yuk, dolu, a.sinir,
                       a.sahip))
            sonraki_satir += a.satir_sn
        time.sleep(a.aralik_sn)


def birak(a):
    """Sahibin tuttugu slot(lar)in tutucusunu sonlandirir. Her zaman rc 0."""
    if not os.path.isdir(a.slot_koku):
        return 0
    for ad in os.listdir(a.slot_koku):
        if not ad.isdigit():
            continue
        yol = os.path.join(a.slot_koku, ad)
        alan = isaretci_oku(yol)
        if alan.get("sahip") != str(a.sahip):
            continue
        tutucu = alan.get("tutucu", "")
        if tutucu.isdigit():
            try:
                os.kill(int(tutucu), signal.SIGTERM)
            except OSError:
                pass
    return 0


def durum(a):
    kilit_dizini, kuyruk = dizinler(a.slot_koku)
    dolu = 0
    for n in range(1, a.sinir + 1):
        yol = os.path.join(a.slot_koku, str(n))
        kilitli = False
        kyol = os.path.join(kilit_dizini, str(n))
        if os.path.exists(kyol):
            fd = os.open(kyol, os.O_RDONLY)
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                kilitli = True
            finally:
                os.close(fd)
        dolu += kilitli
        alan = isaretci_oku(yol) if os.path.exists(yol) else {}
        hal = "DOLU" if kilitli else ("BAYAT" if alan else "BOS")
        print("SLOT %d %s %s" % (n, hal, " ".join("%s=%s" % kv for kv in sorted(alan.items()))))
    bekleyen = kuyruk_listesi(kuyruk)
    print("DOLU=%d/%d BEKLEYEN=%d YUK=%.2f" % (dolu, a.sinir, len(bekleyen), yuk_oku()))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    alt = p.add_subparsers(dest="komut", required=True)
    for ad in ("al", "birak", "durum"):
        q = alt.add_parser(ad)
        q.add_argument("--slot-koku", required=True)
        q.add_argument("--sinir", type=int, default=SINIR)
        if ad in ("al", "birak"):
            q.add_argument("--sahip", type=int, required=True)
        if ad == "al":
            q.add_argument("--log", default="")
            q.add_argument("--etiket", default="etiketsiz")
            q.add_argument("--ev", default="?")
            q.add_argument("--motor", default="?")
            q.add_argument("--yuk-esik", type=float, default=YUK_ESIK)
            q.add_argument("--tavan-sn", type=float, default=TAVAN_SN)
            q.add_argument("--satir-sn", type=float, default=SATIR_SN)
            q.add_argument("--aralik-sn", type=float, default=ARALIK_SN)
            q.add_argument("--izle-sn", type=float, default=IZLE_SN)
            q.add_argument("--adet", type=int, default=1)
            q.add_argument("--tur", default="")
    a = p.parse_args(argv)
    if a.sinir < 1:
        p.error("--sinir >= 1 olmali")
    if a.komut == "al" and not 1 <= a.adet <= a.sinir:
        p.error("--adet 1..--sinir araliginda olmali")
    return {"al": al, "birak": birak, "durum": durum}[a.komut](a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as hata:   # isci.sh FAIL-OPEN kolu (rc 70 -> SEMAFOR=OLCULEMEDI)
        sys.stderr.write("SEMAFOR ic hata: %r\n" % (hata,))
        sys.exit(RC_IC_HATA)

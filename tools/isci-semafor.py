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

AGIR IS BEKCISI (13 Eki 2026, BaBa 06:5x — 04:25'te asili kalan mutant
bataryasi 3/3 slotu saatlerce tuttu, filo durdu): YALNIZ `--tur agir` icin
tutucu ayni zamanda BEKCIDIR. Sahibin (agir-is.sh $$) surec AGACINI
(`ps -A -o pid,ppid,pgid,pcpu`, sahip + tum torunlar) ORNEK_SN'de bir olcer:
  * `--is-tavan-dk` (agir-is.sh `--tavan-dk`, 90): slot tutma suresi asilinca
    `HAL=TAVAN-OLDU`;
  * `--asili-dk` (agir-is.sh `--asili-dk`, 10): agac toplam CPU'su bu sure
    boyunca KESINTISIZ < `--asili-cpu` (%5) ise `HAL=ASILI-OLDU`.
Oldurme: once `<slot-koku>/.oldu/<sahip>` (agir-is.sh rc=124 okur) + log
satiri, sonra KOMUT GRUBU(lari)na (agacta sahibin grubundan FARKLI pgid'ler —
agir-is.sh komutu `grup` alt komutuyla yeni oturumda baslatir) + agactaki her
torun pid'e SIGTERM -> OLUM_BEKLE_SN (30) -> hala canli ise SIGKILL. Sahibin
kendisi ve onun grubu (isci.sh, cron) HEDEF DEGILDIR. Sonra tutucu cikar ->
cekirdek flock'u birakir, isaretciler silinir. Sahip KILL ile oldu ve komut
grubu sahipsiz kaldiysa tutucu ayni oldurmeyi `HAL=SAHIPSIZ-OLDU` ile yapar
(agir is slotsuz kosamaz). `HAL=BEKLIYOR` satiri `TUTAN=<etiket>:<pid>:<t>`
(slotlari tutan(lar), virgulle; yoksa `-`) alanini tasir.

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
import subprocess
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

ORNEK_SN = 10.0        # agir bekci orneklemesi (<=30)
OLUM_BEKLE_SN = 30.0   # TERM -> KILL arasi
ASILI_CPU = 5.0        # agac toplam %CPU esigi

# Test kancasi: dosyadaki sayi 1 dk yuku yerine okunur (bekleme sirasinda
# degistirilebilsin diye deger degil DOSYA). Bos/okunamaz -> gercek yuk.
YUK_DOSYASI_ENV = "PRUVO_ISCI_SEMAFOR_YUK_DOSYASI"
# Test kancasi: dosyadaki sayi agir isin agac %CPU toplami yerine okunur.
CPU_DOSYASI_ENV = "PRUVO_AGIR_CPU_DOSYASI"


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


def tutanlar(slot_koku, kilit_dizini, sinir):
    """Kilidi DOLU slotlarin sahipleri: `etiket:sahip:t` (tekil, virgulle) ya da `-`."""
    gorulen = []
    for n in range(1, sinir + 1):
        kyol = os.path.join(kilit_dizini, str(n))
        if not os.path.exists(kyol):
            continue
        fd = os.open(kyol, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            continue
        except OSError:
            pass
        finally:
            os.close(fd)
        alan = isaretci_oku(os.path.join(slot_koku, str(n)))
        parca = "%s:%s:%s" % (alan.get("etiket", "?"), alan.get("sahip", "?"), alan.get("t", "?"))
        if parca not in gorulen:
            gorulen.append(parca)
    return ",".join(gorulen) or "-"


def agac_oku():
    """`ps` -> {pid: (ppid, pgid, pcpu)}; olculemezse None."""
    try:
        r = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,pgid=,pcpu="],
                           capture_output=True, text=True, timeout=20,
                           env=dict(os.environ, LC_ALL="C"))
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    tablo = {}
    for satir in r.stdout.splitlines():
        p = satir.split()
        if len(p) != 4:
            continue
        try:
            tablo[int(p[0])] = (int(p[1]), int(p[2]), float(p[3].replace(",", ".")))
        except ValueError:
            continue
    return tablo


def torunlar(tablo, kok, haric):
    """kok'un tum torunlari (kok HARIC, `haric` pid'i ve onun alt agaci haric)."""
    cocuklar = {}
    for pid, (ppid, _, _) in tablo.items():
        cocuklar.setdefault(ppid, []).append(pid)
    sonuc, yigin = [], list(cocuklar.get(kok, []))
    while yigin:
        pid = yigin.pop()
        if pid == haric or pid in sonuc:
            continue
        sonuc.append(pid)
        yigin.extend(cocuklar.get(pid, []))
    return sonuc


def agac_cpu(tablo, sahip, ben):
    yol = os.environ.get(CPU_DOSYASI_ENV, "")
    if yol:
        try:
            with open(yol, encoding="utf-8") as f:
                return float(f.read().strip())
        except (OSError, ValueError):
            pass
    if tablo is None or sahip not in tablo:
        return None   # olculemedi -> asili SAYILMAZ (yanlis oldurme yok)
    return tablo[sahip][2] + sum(tablo[p][2] for p in torunlar(tablo, sahip, ben))


def hedefler(tablo, sahip, ben):
    """(torun pid'leri, komut gruplari): sahibin grubu ve tutucu HEDEF DEGIL."""
    if tablo is None or sahip not in tablo:
        return [], set()
    sahip_grubu = tablo[sahip][1]
    pidler = torunlar(tablo, sahip, ben)
    gruplar = {tablo[p][1] for p in pidler
               if tablo[p][1] not in (sahip_grubu, os.getpgid(0), 0, 1)}
    return pidler, gruplar


def grup_canli(g):
    try:
        os.killpg(g, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def gonder(pidler, gruplar, sahip, sig):
    for g in gruplar:
        try:
            os.killpg(g, sig)
        except OSError:
            pass
    for p in pidler:
        try:
            os.kill(p, sig)
        except OSError:
            pass


def oldur(pidler, gruplar, sahip, bekle_sn):
    """TERM -> bekle_sn -> KILL. Doner: hangi sinyalle bitti ('TERM'/'KILL')."""
    gonder(pidler, gruplar, sahip, signal.SIGTERM)
    son = time.monotonic() + bekle_sn
    while time.monotonic() < son:
        if not any(canli(p) for p in pidler) and not any(grup_canli(g) for g in gruplar):
            return "TERM"
        time.sleep(0.2)
    gonder(pidler, gruplar, sahip, signal.SIGKILL)
    return "KILL"


def tutucu_ol(fdler, sahip, isaretciler, izle_sn, bekci=None):
    """Cocuk: kilitli fd'leri tasir, sahip olunce isaretcileri silip cikar.

    bekci (yalniz tur=agir): dict(tavan_sn, asili_sn, asili_cpu, ornek_sn,
    olum_bekle_sn, log, ortak, oldu_dosyasi) -> TAVAN/ASILI oldurmesi.
    """
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
    if bekci is None:
        while canli(sahip):
            time.sleep(izle_sn)
        bitir()
    tavan_sn, asili_sn = bekci["tavan_sn"], bekci["asili_sn"]
    bas = time.monotonic()
    sonraki_ornek = bas
    dusuk_bas = None
    bilinen = set()   # gorulen komut gruplari (sahip KILL ile olurse sahipsiz kalanlar)

    def oldur_ve_cik(hal, pidler, gruplar):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)   # oldurme yarida kesilmesin
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        sure_dk = (time.monotonic() - bas) / 60.0
        gruplar = set(gruplar) | {g for g in bilinen if grup_canli(g)}   # ps olculemediyse
        if hal != "SAHIPSIZ-OLDU":
            try:
                os.makedirs(os.path.dirname(bekci["oldu_dosyasi"]), mode=0o700, exist_ok=True)
                with open(bekci["oldu_dosyasi"], "w", encoding="utf-8") as f:
                    f.write("HAL=%s sure_dk=%.1f\n" % (hal, sure_dk))
            except OSError:
                pass
        log_yaz(bekci["log"], "=== %s HAL=%s %s pid=%d sure_dk=%.1f tavan_dk=%g asili_dk=%g "
                "grup=%s torun=%d sinyal=TERM ==="
                % (damga(), hal, bekci["ortak"], sahip, sure_dk, tavan_sn / 60.0,
                   asili_sn / 60.0, ",".join(str(g) for g in sorted(gruplar)) or "-",
                   len(pidler)))
        if oldur(pidler, gruplar, sahip, bekci["olum_bekle_sn"]) == "KILL":
            log_yaz(bekci["log"], "SEMAFOR=KILL %s pid=%d sebep=TERM-sonrasi-canli bekle_sn=%g"
                    % (bekci["ortak"], sahip, bekci["olum_bekle_sn"]))
        bitir()

    while canli(sahip):
        simdi = time.monotonic()
        if simdi >= sonraki_ornek:
            sonraki_ornek = simdi + bekci["ornek_sn"]
            tablo = agac_oku()
            pidler, gruplar = hedefler(tablo, sahip, benim)
            bilinen |= gruplar
            cpu = agac_cpu(tablo, sahip, benim)
            if cpu is not None and cpu < bekci["asili_cpu"]:
                if dusuk_bas is None:
                    dusuk_bas = simdi
            else:
                dusuk_bas = None
            if tavan_sn and simdi - bas >= tavan_sn:
                oldur_ve_cik("TAVAN-OLDU", pidler, gruplar)
            if asili_sn and dusuk_bas is not None and simdi - dusuk_bas >= asili_sn:
                oldur_ve_cik("ASILI-OLDU", pidler, gruplar)
        time.sleep(min(izle_sn, bekci["ornek_sn"]))
    kalan = {g for g in bilinen if grup_canli(g)}
    if kalan:
        oldur_ve_cik("SAHIPSIZ-OLDU", [], kalan)
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
                bekci = None
                if a.tur == "agir" and (a.is_tavan_dk > 0 or a.asili_dk > 0):
                    tavan_sn = a.is_tavan_dk * 60
                    asili_sn = a.asili_dk * 60
                    bekci = dict(tavan_sn=tavan_sn, asili_sn=asili_sn, asili_cpu=a.asili_cpu,
                                 ornek_sn=min(a.ornek_sn, 30.0),
                                 olum_bekle_sn=a.olum_bekle_sn, log=a.log, ortak=ortak,
                                 oldu_dosyasi=os.path.join(a.slot_koku, ".oldu", str(a.sahip)))
                cocuk = os.fork()
                if cocuk == 0:
                    try:
                        tutucu_ol(fdler, a.sahip, isaretciler, a.izle_sn, bekci)
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
                    "dolu=%d/%d pid=%d TUTAN=%s ==="
                    % (damga(), ortak, sira, int(gecen // 60), sebep, yuk, dolu, a.sinir,
                       a.sahip, tutanlar(a.slot_koku, kilit_dizini, a.sinir)))
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


def grup(argv):
    """`grup -- <komut..>`: komutu YENI oturum/surec grubunda exec eder (agir-is.sh).

    Bekcinin grup oldurmesi yalniz bu agaci vurur; agir-is.sh ve cagirani
    (isci.sh, cron) ayri grupta kalir.
    """
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        sys.stderr.write("KULLANIM: isci-semafor.py grup -- <komut..>\n")
        return 2
    try:
        os.setsid()
    except OSError:
        try:
            os.setpgid(0, 0)
        except OSError:
            pass
    try:
        os.execvp(argv[0], argv)
    except OSError as hata:
        sys.stderr.write("grup: %s: %s\n" % (argv[0], hata.strerror))
        return 127


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "grup":
        return grup(argv[1:])
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
            # agir bekci (yalniz --tur agir; 0 = kapali)
            q.add_argument("--is-tavan-dk", type=float, default=0.0)
            q.add_argument("--asili-dk", type=float, default=0.0)
            q.add_argument("--asili-cpu", type=float, default=ASILI_CPU)
            q.add_argument("--ornek-sn", type=float, default=ORNEK_SN)
            q.add_argument("--olum-bekle-sn", type=float, default=OLUM_BEKLE_SN)
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

#!/usr/bin/env python3
"""isci-karantina-durum.py — isci.sh ONCESI motor karantina/yedek karari.

isci-karantina-karar.py YAZAR (tur SONUNDA, bkz o dosyanin basindaki
"Kol C" notu: erisim reddi veya ardisik basarisizlikta $KARANTINA_DOSYASI'na
"<motor> <epoch>" satiri ekler). Bu script OKUR (tur BASLAMADAN once).

27 Agu 2026 (wa-gozcu motor=claude, 13 ardisik rc=1, hic alarm yok vakasi):
yazma tarafi zaten vardi ama HICBIR cagiran bu dosyayi tur baslamadan once
okumuyordu -- karantina kaydı diskte otururken ayni olu motor dakikada bir
sessizce yeniden deneniyordu. Bu script o boslugu kapatir.

Yedek motor secimi TEK KAYNAKTAN: ~/dev/pruvo/tools/mimar_kimlik.py
CANLI_ISCI_MOTORLARI (minimax-m3, kimi) -- nobet-kapi.py'nin AYNI kaynagi
kullandigi ic-ice import deseni (bkz nobet-kapi.py satir ~146-159).
Ikinci bir motor sirasi burada ICAT EDILMEZ.

"claude" bu kumede YOKTUR -- kasitli: wa-gozcu gibi cagiranlar musteriye
gercek zamanli yanit ureten sessiz-hata sinifi isler icin motoru "claude"a
ZORLAR (bkz wa-gozcu-cron.sh basindaki not: "isci.sh'in ucuz-motor
secimine (deepseek/minimax) BIRAKILMAZ"). Bu script o politikayi
BOZMAZ: istenen motor CANLI_ISCI_MOTORLARI disindaysa (orn. "claude")
YEDEK ARANMAZ, DURUM=KARANTINADA yedek=yok doner -- cagiran calismayi
DENEMEDEN LOUD SKIP eder, ucuz motora KAYMAZ.

TTL: nobet-kapi.py KARANTINA_OMUR_SN (6 saat) ile AYNI deger. Iki dosyada
sabit tutulur (zsh/python sinir gecisinde ayni degeri IKI YERDE tanimlamak
kacinilmaz -- isci-karantina-karar.py de yazma tarafinda AYRI dosyadir);
deger degisirse ikisi de guncellenmeli.

Cikti (stdout, TEK satir, makine-okunur):
  DURUM=TEMIZ motor=<istenen>
  DURUM=YEDEK motor=<istenen> yedek=<yedek_motor> sebep=karantina
  DURUM=KARANTINADA motor=<istenen> yedek=yok sebep=karantina

Fail-open: herhangi bir hata/eksik girdide DURUM=TEMIZ basilir, exit 0 --
cagiran KESILMEZ, davranis mekanizma HIC yokmus gibi kalir.

1 Kas 2026 (KARARLAR 92): istenen motor CANLI_ISCI_MOTORLARI icindeyse aday
sirasi CANLI + YEDEK_ISCI_MOTORLARI'dir (mimar_kimlik.py, yedek = "agy"). Istenen
CANLI disindaysa (orn. "claude") davranis AYNEN kalir: yedek aranmaz.

Kullanim:
  isci-karantina-durum.py <istenen_motor> <karantina_dosyasi> [omur_sn]
"""
import os
import sys
import time

KARANTINA_OMUR_SN_VARSAYILAN = 6 * 3600  # nobet-kapi.py KARANTINA_OMUR_SN ile AYNI


def karantina_kayitlari(yol, omur_sn):
    """Dosyadaki, omur_sn'den TAZE motorlari {ad: epoch} olarak dondurur.

    Bicimsiz/eski satirlar sessizce ATLANIR (fail-open) -- dosyanin
    kendisi isci-karantina-karar.py TARAFINDAN atomik yazilir, burada
    yalniz OKUNUR, hicbir zaman degistirilmez.
    """
    simdi = time.time()
    sonuc = {}
    try:
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                parcalar = satir.split()
                if len(parcalar) != 2:
                    continue
                motor, damga_str = parcalar
                try:
                    damga = int(damga_str)
                except ValueError:
                    continue
                if simdi - damga < omur_sn:
                    sonuc[motor] = damga
    except OSError:
        return {}
    return sonuc


def canli_motorlari_al():
    """TEK KAYNAK: mimar_kimlik.CANLI_ISCI_MOTORLARI. Import basarisizsa ()."""
    kok = os.path.expanduser("~/dev/pruvo/tools")
    if kok not in sys.path:
        sys.path.insert(0, kok)
    try:
        from mimar_kimlik import CANLI_ISCI_MOTORLARI
        return tuple(CANLI_ISCI_MOTORLARI)
    except Exception:
        return ()


def yedek_motorlari_al():
    """TEK KAYNAK: mimar_kimlik.YEDEK_ISCI_MOTORLARI. Import basarisizsa ()."""
    kok = os.path.expanduser("~/dev/pruvo/tools")
    if kok not in sys.path:
        sys.path.insert(0, kok)
    try:
        from mimar_kimlik import YEDEK_ISCI_MOTORLARI
        return tuple(YEDEK_ISCI_MOTORLARI)
    except Exception:
        return ()


def karar_ver(istenen, karantina_dosyasi, omur_sn):
    """Yan etkisiz karar fonksiyonu. Test dogrudan cagirir. (durum, yedek) doner."""
    kayitlar = karantina_kayitlari(karantina_dosyasi, omur_sn)
    if istenen not in kayitlar:
        return ("TEMIZ", None)
    canli = canli_motorlari_al()
    if istenen in canli:
        for aday in canli + yedek_motorlari_al():
            if aday == istenen:
                continue
            if aday not in kayitlar:
                return ("YEDEK", aday)
    return ("KARANTINADA", None)


def main(argv):
    if len(argv) not in (3, 4):
        sys.stderr.write(
            "Kullanim: isci-karantina-durum.py <istenen_motor> "
            "<karantina_dosyasi> [omur_sn]\n"
        )
        print("DURUM=TEMIZ motor=? sebep=arguman-hatasi")
        return 0
    istenen = argv[1]
    karantina_dosyasi = argv[2]
    try:
        omur_sn = int(argv[3]) if len(argv) == 4 else KARANTINA_OMUR_SN_VARSAYILAN
    except ValueError:
        omur_sn = KARANTINA_OMUR_SN_VARSAYILAN

    try:
        durum, yedek = karar_ver(istenen, karantina_dosyasi, omur_sn)
    except Exception as e:                                            # noqa: BLE001
        sys.stderr.write("UYARI: karantina durumu olculemedi: %s: %s\n" % (type(e).__name__, e))
        print("DURUM=TEMIZ motor=%s sebep=olcum-hatasi" % istenen)
        return 0

    if durum == "TEMIZ":
        print("DURUM=TEMIZ motor=%s" % istenen)
    elif durum == "YEDEK":
        print("DURUM=YEDEK motor=%s yedek=%s sebep=karantina" % (istenen, yedek))
    else:
        print("DURUM=KARANTINADA motor=%s yedek=yok sebep=karantina" % istenen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

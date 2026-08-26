#!/usr/bin/env python3
"""KOR GOZ — TABAN/SONRA OLCERI (cip KraL-KorGoz-27Agu, 27 Agu 2026).

TEK BETIK, IKI KEZ KOSAR: onarimdan ONCE (TABAN) ve SONRA. Ciktisi BIREBIR
kiyaslanabilir olsun diye butun sayilar tek satirlik `ANAHTAR=deger` jetonu
olarak basilir.

OLCTUGU DORT EKSEN:
  T1  mevcut batarya (`nobet-tetik-test.py`) rc + VAKA/DUSEN satiri
  T2  F1-F4 fikstur tablosu — `karar()` SAF fonksiyonuna sentetik kalp verilir,
      canli dosyaya DOKUNULMAZ. Arizanin tam ifadesi burada okunur: F2 (11
      duran kirmizi) ile F3 (KONTROL, 0 kirmizi) AYNI rc'yi veriyor mu?
  T3  canli log sayimi — 🔴 PENCERE ACIKCA BASILIR. `ci-nobeti.log` IKI gun
      tasiyor; 26 Agu'da "18/21 mi 13/15 mi" tartismasi tam bu yuzden cikti ve
      iki pencere IKI DOGRU sayi verdi. Her TETIK_HUKMU satiri kendisinden
      SONRAKI ilk `BITIS` damgasina baglanir (log es zamanli yazarlar yuzunden
      damga siralamasinda DEGIL, satir siralamasindadir).
  T4  defter sayilari — UC ayri okuyucu yan yana:
        (a) `nobet-kapi.onarim_kalemleri()`  -> ACIK_KALEM
        (b) `parti-borc-kapisi.acik_kalem_listesi()` -> N2B ACIK  (IKINCI OKUYUCU)
        (c) hicbir parser kullanmayan CIPLAK kolon-5 sayimi (K4'un bagimsiz
            dogrulamasi — iki parser de yanilirsa bu yakalar)

SALT OKUMA: hicbir canli dosya YAZILMAZ, tur ACILMAZ, damga KONULMAZ
(`kuru=True` / dogrudan saf fonksiyon cagrisi).
"""

import importlib.util
import json
import os
import re
import subprocess
import sys

CRON = "/Users/okan/.claude/cron"
TETIK = os.path.join(CRON, "nobet-tetik.py")
TETIK_TEST = os.path.join(CRON, "nobet-tetik-test.py")
KAPI = os.path.join(CRON, "nobet-kapi.py")
CI_LOG = os.path.join(CRON, "ci-nobeti.log")
GOZCU_LOG = os.path.join(CRON, "gozcu.log")
DEFTER = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md"
T4_YOLU = "/Users/okan/dev/pruvo/tools/parti-borc-kapisi.py"

SIMDI = 1_755_000_000.0
BUGUN = "2026-08-27"


def modul_yukle(ad, yol):
    if CRON not in sys.path:
        sys.path.insert(0, CRON)
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
    return modul


# --------------------------------------------------------------------------
# T2 — F1..F4 FIKSTURLERI (canli dosyaya dokunmaz)
# --------------------------------------------------------------------------
def _kalp(**ek):
    """Varsayilan = SAGLIKLI + YESIL kalp; vaka yalniz FARKI yazar."""
    temel = {
        "damga": "2026-08-27T00:00:00Z",
        "epok": SIMDI,
        "tetik": "YOK",
        "llm_turu": False,
        "yeni_kirmizi": 0,
        "kirmizi_toplam": 0,
        "hedef_run": "",
        "dagitilabilir": 0,
        "kat_mimar": 0,
        "kat_okan": 0,
        "kat_isci": 0,
        "gunluk_gerekli": False,
        "ci_olculdu": True,
        "ci_sebep": "TAMAM",
        "defter_olculdu": True,
        "icra_rc": None,
        "icra_denendi": False,
        "icra_hal": "KOSULMADI",
        "kosum_hukmu": "TEMIZ",
        "uretken": True,
        "uretken_sebep": "ICRA_DENENMEDI",
        "eskalasyon_acik": 0,
    }
    temel.update(ek)
    return temel


def fiksturler():
    """(ad, aciklama, kalp) — F2 ile F3 YALNIZ `kirmizi_toplam`ta ayrilir."""
    return [
        ("F1", "gozcu ICRA ETTI, 11 duran kirmizi, yeni kirmizi YOK",
         _kalp(kirmizi_toplam=11, icra_denendi=True, icra_hal="KOSTU",
               kosum_hukmu="TEMIZ", uretken=True, uretken_sebep="TEMIZ")),
        ("F2", "gozcu icra ETMEDI, 11 duran kirmizi, yeni kirmizi YOK",
         _kalp(kirmizi_toplam=11)),
        ("F3", "KONTROL — gercekten sakin hat, 0 kirmizi",
         _kalp(kirmizi_toplam=0)),
        ("F4", "GERCEK YENI KIRMIZI — tur ACILMALI",
         _kalp(tetik="CI_KIRMIZI", hedef_run="99887766", yeni_kirmizi=1,
               kirmizi_toplam=1)),
    ]


def t2_fikstur(NT, cikti):
    cikti.append("## T2 FIKSTUR TABLOSU (saf karar(), canli dosya YOK)")
    rc_haritasi = {}
    for ad, aciklama, kalp in fiksturler():
        k = NT.karar(kalp, SIMDI, BUGUN)
        rc = NT.cikis_kodu(k)
        rc_haritasi[ad] = rc
        cikti.append("FIKSTUR %s rc=%d hukum=%s sebep=%s kirmizi=%d  # %s"
                     % (ad, rc, k.hukum, k.sebep, 1 if k.kirmizi else 0, aciklama))
    esit = rc_haritasi.get("F2") == rc_haritasi.get("F3")
    cikti.append("F2_F3_ESIT=%d  # 1 = ARIZA (11 duran kirmizi ile 0 kirmizi "
                 "ayirt EDILEMIYOR)" % (1 if esit else 0))
    cikti.append("F4_TUR_ACILIYOR=%d" % (1 if rc_haritasi.get("F4") in (0, 1) else 0))
    return rc_haritasi


# --------------------------------------------------------------------------
# T3 — CANLI LOG SAYIMI, PENCERE ACIKCA BASILIR
# --------------------------------------------------------------------------
BITIS_DESENI = re.compile(r"^=== (?P<damga>\d{4}-\d{2}-\d{2})[T ]")
TETIK_DESENI = re.compile(r"^TETIK_HUKMU tetik_rc=(?P<rc>-?\d+) acilan_tur=(?P<tur>\d+)")


def t3_log(cikti):
    cikti.append("## T3 CANLI LOG SAYIMI")
    try:
        with open(CI_LOG, encoding="utf-8", errors="replace") as f:
            satirlar = f.read().splitlines()
    except OSError as hata:
        cikti.append("LOG_OLCULEMEDI sebep=%r" % (hata,))
        return

    # Her TETIK_HUKMU satiri, kendisinden SONRAKI ilk BITIS damgasinin gunune
    # yazilir. Satir sirasi = kosum sirasi; damga sirasi DEGIL (es zamanli
    # yazarlar damgalari karistiriyor — 26 Agu'da olculdu).
    sonraki_gun = [None] * len(satirlar)
    gun = "SONRASI-DAMGASIZ"
    for i in range(len(satirlar) - 1, -1, -1):
        m = BITIS_DESENI.match(satirlar[i])
        if m and "BITIS" in satirlar[i]:
            gun = m.group("damga")
        sonraki_gun[i] = gun

    pencereler = {}
    toplam = {"TETIK": 0, "rc10": 0, "rc11": 0, "rc_ac": 0, "tur0": 0, "tur1": 0}
    for i, satir in enumerate(satirlar):
        m = TETIK_DESENI.match(satir)
        if not m:
            continue
        g = sonraki_gun[i]
        kova = pencereler.setdefault(
            g, {"TETIK": 0, "rc10": 0, "rc11": 0, "rc_ac": 0, "tur0": 0, "tur1": 0})
        rc = int(m.group("rc"))
        tur = int(m.group("tur"))
        for hedef in (kova, toplam):
            hedef["TETIK"] += 1
            if rc == 10:
                hedef["rc10"] += 1
            elif rc == 11:
                hedef["rc11"] += 1
            elif rc in (0, 1):
                hedef["rc_ac"] += 1
            hedef["tur1" if tur else "tur0"] += 1

    cikti.append("LOG_DOSYA=%s SATIR=%d" % (CI_LOG, len(satirlar)))
    for g in sorted(pencereler):
        k = pencereler[g]
        cikti.append("PENCERE=%s TETIK_HUKMU=%d tetik_rc10=%d tetik_rc11=%d "
                     "tetik_rc_AC=%d acilan_tur0=%d acilan_tur1=%d"
                     % (g, k["TETIK"], k["rc10"], k["rc11"], k["rc_ac"],
                        k["tur0"], k["tur1"]))
    cikti.append("PENCERE=DOSYA-GENELI TETIK_HUKMU=%d tetik_rc10=%d tetik_rc11=%d "
                 "tetik_rc_AC=%d acilan_tur0=%d acilan_tur1=%d"
                 % (toplam["TETIK"], toplam["rc10"], toplam["rc11"],
                    toplam["rc_ac"], toplam["tur0"], toplam["tur1"]))

    # ACIK_KALEM jetonu — HER gecis sayilir, DEGERE gore kirilir. Sifir-disi
    # her gecisin SATIR NUMARASI basilir ki canli emisyon ile bir cip/insan
    # notu insan gozuyle ayirt edilebilsin (26 Agu'da tek bir prose satiri
    # sayimi kirletmisti; onu "elemek" yerine GORUNUR kiliyoruz).
    jeton = re.compile(r"(?<![A-Za-z0-9_])ACIK_KALEM=(\d+)")
    for ad, yol in (("ci-nobeti.log", CI_LOG), ("gozcu.log", GOZCU_LOG)):
        sayac = {}
        pozitif_satirlar = []
        try:
            with open(yol, encoding="utf-8", errors="replace") as f:
                for satir_no, satir in enumerate(f, 1):
                    for deger in jeton.findall(satir):
                        sayac[deger] = sayac.get(deger, 0) + 1
                        if deger != "0":
                            pozitif_satirlar.append("%d:%s" % (satir_no, deger))
        except OSError as hata:
            cikti.append("ACIK_KALEM_OLCULEMEDI dosya=%s sebep=%r" % (ad, hata))
            continue
        cikti.append("ACIK_KALEM_LOG dosya=%s SIFIR=%d POZITIF=%d DAGILIM=%s"
                     % (ad, sayac.get("0", 0),
                        sum(v for k, v in sayac.items() if k != "0"),
                        json.dumps(sayac, sort_keys=True)))
        cikti.append("ACIK_KALEM_POZITIF_SATIR dosya=%s yerler=%s"
                     % (ad, ",".join(pozitif_satirlar) or "-"))


# --------------------------------------------------------------------------
# T4 — DEFTER: UC OKUYUCU YAN YANA
# --------------------------------------------------------------------------
def t4_defter(NK, cikti):
    cikti.append("## T4 DEFTER — UC OKUYUCU")

    # (a) nöbet kapisinin kendi okuyucusu
    try:
        tum = NK.defter_oku()
        onarilacak = NK.onarim_kalemleri(tum)
        dagitim = [k for k in onarilacak
                   if NK.kat_sec(k) not in (NK.KAT_MIMAR, NK.KAT_OKAN)]
        cikti.append("OKUYUCU_A nobet-kapi.onarim_kalemleri ACIK_KALEM=%d "
                     "DEFTER_SATIR=%d DAGITILABILIR=%d"
                     % (len(onarilacak), len(tum), len(dagitim)))
        cikti.append("OKUYUCU_A_KALEM=%s"
                     % (",".join(k["id"] for k in onarilacak) or "-"))
        sozluk = {}
        for k in tum:
            sozluk[k["durum"]] = sozluk.get(k["durum"], 0) + 1
        cikti.append("OKUYUCU_A_DURUM_DAGILIMI=%s"
                     % json.dumps(sozluk, ensure_ascii=False, sort_keys=True))
    except Exception as hata:
        cikti.append("OKUYUCU_A_OLCULEMEDI sebep=%r" % (hata,))

    # (b) IKINCI OKUYUCU — N2B parti kapisinin besledigi T4 parseri.
    #     Bu dosyaya DOKUNULMUYOR; K5 tam olarak "degistirilmeyen okuyucuya ne
    #     oldu" sorusunu sorar ve cevabi SAYIYLA ister.
    try:
        T4 = modul_yukle("parti_borc_kapisi", T4_YOLU)
        kalemler, okundu, hata = T4.acik_kalem_listesi(DEFTER)
        cikti.append("OKUYUCU_B parti-borc-kapisi.acik_kalem_listesi N2B_ACIK=%d "
                     "okundu=%s hata=%s" % (len(kalemler), okundu, hata or "-"))
        cikti.append("OKUYUCU_B_KALEM=%s"
                     % (",".join(k["kimlik"] for k in kalemler) or "-"))
        cikti.append("OKUYUCU_B_SOZLUK=%s"
                     % ",".join(sorted(T4.ACIK_DURUMLAR)))
    except Exception as hata:
        cikti.append("OKUYUCU_B_OLCULEMEDI sebep=%r" % (hata,))

    # (c) CIPLAK sayim — hicbir parser kullanmaz. K4'un "defterden bagimsiz"
    #     dogrulamasi: iki parser de yanilirsa bunun sayisi ayrisir.
    sayac = {}
    satir_sayisi = 0
    try:
        with open(DEFTER, encoding="utf-8") as f:
            for satir in f:
                if not satir.startswith("| K"):
                    continue
                kolon = satir.split("|")
                if len(kolon) < 7:
                    continue
                if not re.match(r"^K\d+$", kolon[1].strip()):
                    continue
                satir_sayisi += 1
                durum = kolon[5].strip()
                sayac[durum] = sayac.get(durum, 0) + 1
        cikti.append("OKUYUCU_C ciplak_kolon5 K_SATIR=%d DAGILIM=%s"
                     % (satir_sayisi, json.dumps(sayac, ensure_ascii=False,
                                                 sort_keys=True)))
    except OSError as hata:
        cikti.append("OKUYUCU_C_OLCULEMEDI sebep=%r" % (hata,))


# --------------------------------------------------------------------------
def main():
    cikti = ["# KOR GOZ OLCUMU — cip KraL-KorGoz-27Agu"]

    # T1
    cikti.append("## T1 MEVCUT BATARYA")
    try:
        p = subprocess.run([sys.executable, TETIK_TEST], capture_output=True,
                           text=True, timeout=600)
        ozet = "-"
        for satir in reversed((p.stdout or "").strip().splitlines()):
            if satir.startswith("VAKA="):
                ozet = satir
                break
        cikti.append("BATARYA nobet-tetik-test.py rc=%d ozet=%s" % (p.returncode, ozet))
        for satir in (p.stdout or "").splitlines():
            if satir.startswith("KIRIK "):
                cikti.append("BATARYA_" + satir)
    except Exception as hata:
        cikti.append("BATARYA_OLCULEMEDI sebep=%r" % (hata,))

    NT = modul_yukle("nobet_tetik_olcum", TETIK)
    t2_fikstur(NT, cikti)
    t3_log(cikti)
    NK = modul_yukle("nobet_kapi_olcum", KAPI)
    t4_defter(NK, cikti)

    metin = "\n".join(cikti)
    print(metin)
    hedef = os.environ.get("KORGOZ_CIKTI")
    if hedef:
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

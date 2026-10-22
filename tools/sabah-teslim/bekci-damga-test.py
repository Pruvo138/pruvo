#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CIP-DOGUM BEKCISI — `KAPANDI: CANLI=0` BASLIK DAMGASI kabul bataryasi.

NEDEN VAR (BaBa 15 Eki 23:1x (2), cip `KraL-BekciDamga`): 15 Eki'de KraL o
gunun Tamirci kirmizilarini CANLI 3->0 ile kapatti, BaBa kapanisi GECERLI
saydi; bekci ise yalniz CIP DOGUMUNU kapanis saydigi icin
`KANIT_VAR_CIP_DOGMADI` KIRMIZI yakti (sahte kirmizi). Onarim: spec dosyasinin
ILK 5 satirinda tam satir `KAPANDI: CANLI=0 HH:MM (BaBa hükmü HH:MM)` varsa
hukum YESIL `KANIT_VAR_KAPANDI_DAMGASI`.

VAKALAR (hepsi `karar()` uzerinden, uctan uca):
  D1  damgali spec + cip dogmadi           -> YESIL  KANIT_VAR_KAPANDI_DAMGASI
  D2  damgasiz spec + cip dogmadi          -> KIRMIZI KANIT_VAR_CIP_DOGMADI (kontrol)
  D3a damga 6. satirda                     -> KIRMIZI
  D3b damga govdede / alintida             -> KIRMIZI
  D4  `CANLI=1` damgasi                    -> KIRMIZI
  D5  spec OKUNAMADI (damga 1. satirda)    -> KIRMIZI (fail-closed)
  K1  damga + cip DOGDU                    -> YESIL KANIT_VAR_CIP_DOGDU (sira degismedi)
  D6  ev bicimi `09:4x` iki alanda         -> YESIL  KANIT_VAR_KAPANDI_DAMGASI (BaBa 16 Eki 15:2x)
  D7  tek haneli saat `9:4x`               -> KIRMIZI
  D8  eksik dakika `09:4`                  -> KIRMIZI
  T1  isci `etiket=tamir` + kutu YARGI     -> YESIL  KANIT_VAR_TAMIRCI_ISCI_KOSTU
  T2  yalniz isci satiri (kutu YARGI'siz)  -> KIRMIZI KANIT_VAR_CIP_DOGMADI
  T3  yalniz kutu YARGI (isci etiketi baska)-> KIRMIZI
  T4  DUNKU isci satiri + bugunku YARGI    -> KIRMIZI (UTC->yerel gun kurali)
  T5  `etiket=tamir-x` + kutu YARGI        -> KIRMIZI (tam token kurali)
  T6  isci.log OKUNAMAZ + kutu YARGI       -> KIRMIZI (fail-closed)
MUTANTLAR (izole kopyada; canli kaynak sha'si once/sonra ESIT olmali):
  M1  damga kolu silinir                   -> D1 KIRMIZI (yakalanmali)
  M2  baslik siniri (5 satir) kaldirilir   -> D3a YESIL (yakalanmali)
  M3  `is True` -> `is not False`          -> D5 YESIL (fail-closed kolu)
  M4  `x` kabulu kapatilir (`\d{2}`)       -> D6 KIRMIZI (ev bicimi kolu)
  M5  tamirci kolunun (b) sartı silinir    -> T2 YESIL (yakalanmali)
  M6  tamirci kolunun (a) sartı silinir    -> T3 YESIL (yakalanmali)

TAMAMI FIKSTURDEDIR: canli `tamirci-spec/`, bekci logu, damga dizini,
`isci.log` ve posta kutusu HIC okunmaz/yazilmaz; tum yollar `karar()`
parametresiyle gecici dizine baglanir.
Gecici dizin is bitince SILINIR (Okan disk kurali).

KOSUM: python3 tools/sabah-teslim/bekci-damga-test.py   (rc=0 => YESIL)
"""

import datetime as dt
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(KOK, "nobet-onarim", "cron", "cip_dogum_bekcisi.py")

DAMGA = "KAPANDI: CANLI=0 09:47 (BaBa hükmü 09:48)"
JETON = "ADIM 0 — ÇİP-DOĞUM BEKÇİSİ"

M1_CAPA = ("        if kapandi_damgasi_olc(yol) is True:\n"
           "            return _don(\"YESIL\", \"KANIT_VAR_KAPANDI_DAMGASI\", teslim, dogum)\n")
M1_YAMA = "        pass  # MUTANT M1: damga kolu SILINDI\n"
M2_CAPA = ("                if sira >= KAPANDI_DAMGA_SATIR_SINIRI:\n"
           "                    break\n")
M2_YAMA = "                pass  # MUTANT M2: baslik siniri KALDIRILDI\n"
M3_CAPA = "        if kapandi_damgasi_olc(yol) is True:\n"
M3_YAMA = "        if kapandi_damgasi_olc(yol) is not False:  # MUTANT M3\n"
M4_CAPA = ('    r"^KAPANDI: CANLI=0 \\d{2}:\\d[0-9x] '
           '\\(BaBa hükmü \\d{2}:\\d[0-9x]\\)$")\n')
M4_YAMA = ('    r"^KAPANDI: CANLI=0 \\d{2}:\\d{2} '
           '\\(BaBa hükmü \\d{2}:\\d{2}\\)$")  # MUTANT M4\n')
DAMGA_EV = "KAPANDI: CANLI=0 09:4x (BaBa hükmü 09:4x)"
M5_CAPA = '        if tamirci["isci"] is True and tamirci["yargi"] is True:\n'
M5_YAMA = '        if tamirci["isci"] is True:  # MUTANT M5: (b) sartı SILINDI\n'
M6_YAMA = '        if tamirci["yargi"] is True:  # MUTANT M6: (a) sartı SILINDI\n'


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _spec_metni(vaka):
    """Vakaya gore spec govdesi (gercek spec basligini taklit eder)."""
    bas = ["# KraL-Tamirci-FIKSTUR — sabah spec'i",
           "`ROTASYON=OK rc=0 HUKUM=KORUMA_TUTTU`",
           "",
           "Ev: KraL · Etiket: `kabul-sabah-rutini`",
           "Üretim anı: FIKSTUR",
           "",
           "## BUGÜNÜN KIRMIZILARI (CI — bugün UTC) · HÜKÜM=OK · ADET=0"]
    govde = ["- satir %d" % i for i in range(20)]
    if vaka in ("D1", "D5", "K1"):
        satirlar = [DAMGA] + bas + govde
    elif vaka == "D2" or vaka.startswith("T"):
        # T* vakalari da damgasiz spec kullanir: hedef tamirci ISCI KOSTU
        # koludur (damgali spec onlari zaten YESIL'e cikarirdi).
        satirlar = bas + govde
    elif vaka == "D3a":
        satirlar = bas[:5] + [DAMGA] + bas[5:] + govde       # 6. satir
    elif vaka == "D3b":
        satirlar = bas + govde[:8] + ["> " + DAMGA, DAMGA] + govde[8:]
    elif vaka == "D4":
        satirlar = [DAMGA.replace("CANLI=0", "CANLI=1")] + bas + govde
    elif vaka == "D6":
        satirlar = [DAMGA_EV] + bas + govde
    elif vaka == "D7":
        satirlar = [DAMGA_EV.replace("=0 09:4x", "=0 9:4x")] + bas + govde
    elif vaka == "D8":
        satirlar = [DAMGA_EV.replace("=0 09:4x", "=0 09:4")] + bas + govde
    else:
        raise ValueError(vaka)
    return "\n".join(satirlar) + "\n"


def _utc_iso(epoch):
    """Epoch -> isci.log bicimi UTC damgasi (`...Z`)."""
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _isci_satiri(utc, ev="pruvo", etiket="tamir"):
    """Gercek `isci.sh` BASLANGIC biciminin bir satir kopyasi."""
    return ("=== %s BASLANGIC motor=minimax-m3 ev=%s etiket=%s butce=YOK "
            "model=MiniMax-M3[1m] pid=91129 ===" % (utc, ev, etiket))


def _yargi_basligi(yerel, ay):
    """Kutudaki `## … TAMİRCİ <gün> <Ay> YARGI` basligi."""
    return ("## %s 17:3x — ⚖️ KraL halef-49 → **BaBa** — "
            "**TAMİRCİ %d %s YARGI: tamir edilecek kalem 0, KABUL.** Fikstür.\n"
            % (yerel.isoformat(), yerel.day, ay))


def _tamirci_fikstur(vd, vaka, simdi, ay):
    """isci.log + kutu fiksturu; (yol, yol) doner.

    `ay` TEK KAYNAK'tan (`mod.TESLIM_AYLARI`) gelir, test ikinci bir ay
    listesi TAZMAMAZ. T6'da isci.log yerine DIZIN olusturulur: `open()`
    orada `OSError` verir (dosya YOK degil, okunamaz) — fail-closed kolu olcer.
    """
    yerel = dt.datetime.fromtimestamp(simdi)
    bugun = _utc_iso(simdi)
    dun = _utc_iso(simdi - 86400)

    isci_satirlari = [_isci_satiri(bugun, etiket="kabul")]   # temiz taban
    kutu_satirlari = ["## %s 06:20 — ✅ KraL halef-48 — açılış tamam.\n"
                      % (yerel - dt.timedelta(days=1)).date().isoformat()]
    if vaka == "T1":
        isci_satirlari = [_isci_satiri(bugun)]
        kutu_satirlari = [_yargi_basligi(yerel, ay)]
    elif vaka == "T2":
        isci_satirlari = [_isci_satiri(bugun)]
    elif vaka == "T3":
        kutu_satirlari = [_yargi_basligi(yerel, ay)]
    elif vaka == "T4":
        isci_satirlari = [_isci_satiri(dun)]
        kutu_satirlari = [_yargi_basligi(yerel, ay)]
    elif vaka == "T5":
        isci_satirlari = [_isci_satiri(bugun, etiket="tamir-x")]
        kutu_satirlari = [_yargi_basligi(yerel, ay)]
    elif vaka == "T6":
        kutu_satirlari = [_yargi_basligi(yerel, ay)]

    isci_yol = os.path.join(vd, "isci.log")
    if vaka == "T6":
        os.makedirs(isci_yol)               # okunamaz (dizin) — yazma yok
    else:
        with open(isci_yol, "w", encoding="utf-8") as f:
            f.write("\n".join(isci_satirlari) + "\n")
    kutu_yol = os.path.join(vd, "mimar-posta-kutusu.md")
    with open(kutu_yol, "w", encoding="utf-8") as f:
        f.write("# FIKSTUR kutusu\n\n" + "".join(kutu_satirlari))
    return isci_yol, kutu_yol


def _vaka_kos(mod, td, vaka):
    """Tek `karar()` cagrisi; tum duzlem `td` altindaki fiksturden gelir."""
    vd = os.path.join(td, "vaka-%s" % vaka)
    kanit = os.path.join(vd, "kanit")
    os.makedirs(kanit)
    kanca = os.path.join(vd, "SKILL-sag.md")
    with open(kanca, "w", encoding="utf-8") as f:
        f.write(JETON + "\n")
    kalp = os.path.join(vd, "kalp-taze.md")
    taze = (dt.datetime.now(dt.timezone.utc)
            - dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(kalp, "w", encoding="utf-8") as f:
        f.write("KOSTU=A@%s\n" % taze)
    kollar = [{"id": "A", "kanca": kanca, "jeton": JETON, "tavan_saat": 30}]

    simdi = time.time()
    tarih = dt.datetime.fromtimestamp(simdi).date()
    spec_yolu = mod.kanit_yolu(tarih, kanit)
    with open(spec_yolu, "w", encoding="utf-8") as f:
        f.write(_spec_metni(vaka))
    log_yolu = os.path.join(vd, "bekci-bildirim.log")
    with open(log_yolu, "w", encoding="utf-8") as f:
        if vaka == "K1":
            f.write("2026-10-16T09:01:00Z anahtar=%s kanal=cip rc=0 "
                    "teslim=BASARILI task_id=task_abcdef12\n"
                    % tarih.isoformat().replace("-", ""))
    isci_yol, kutu_yol = _tamirci_fikstur(
        vd, vaka, simdi, mod.TESLIM_AYLARI[tarih.month - 1])

    eski_open = getattr(mod, "open", None)
    if vaka == "D5":
        # Yalniz SPEC dosyasinin okunmasi patlar; log/kalp/kanca okunur.
        def _bozuk_open(yol, *a, **k):
            if os.path.abspath(str(yol)) == os.path.abspath(spec_yolu):
                raise PermissionError("FIKSTUR: spec okunamadi")
            return open(yol, *a, **k)
        mod.open = _bozuk_open
    try:
        k = mod.karar(simdi=simdi, dizin=kanit, esik_saat=0,
                      teslim_kollari=kollar, teslim_kalp_yolu=kalp,
                      log_yolu=log_yolu, tamir_log_yolu=isci_yol,
                      kutu_yolu=kutu_yol)
    finally:
        if vaka == "D5":
            if eski_open is None:
                del mod.open
            else:
                mod.open = eski_open
    return k["hukum"], k["sebep"]


BEKLENEN = {
    "D1": ("YESIL", "KANIT_VAR_KAPANDI_DAMGASI"),
    "D2": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "D3a": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "D3b": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "D4": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "D5": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "K1": ("YESIL", "KANIT_VAR_CIP_DOGDU"),
    "D6": ("YESIL", "KANIT_VAR_KAPANDI_DAMGASI"),
    "D7": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "D8": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "T1": ("YESIL", "KANIT_VAR_TAMIRCI_ISCI_KOSTU"),
    "T2": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "T3": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "T4": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "T5": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
    "T6": ("KIRMIZI", "KANIT_VAR_CIP_DOGMADI"),
}
# Mutant -> (hedef vaka, mutantta BEKLENEN yanlis hukum)
MUTANTLAR = (
    ("M1", M1_CAPA, M1_YAMA, "D1", "KIRMIZI"),
    ("M2", M2_CAPA, M2_YAMA, "D3a", "YESIL"),
    ("M3", M3_CAPA, M3_YAMA, "D5", "YESIL"),
    ("M4", M4_CAPA, M4_YAMA, "D6", "KIRMIZI"),
    ("M5", M5_CAPA, M5_YAMA, "T2", "YESIL"),
    ("M6", M5_CAPA, M6_YAMA, "T3", "YESIL"),
)


def main():
    if not os.path.isfile(KAYNAK):
        print("🔴 KAYNAK YOK: %s" % KAYNAK)
        return 2
    sha_once = _sha(KAYNAK)
    td = tempfile.mkdtemp(prefix="bekci-damga-test-")
    hata = 0
    vaka_gecti = 0
    mutant_oldu = 0
    try:
        # Kaynak IZOLE kopyadan yuklenir (canli dosya yalniz okunur).
        kopya = os.path.join(td, "cip_dogum_bekcisi_kopya.py")
        shutil.copy2(KAYNAK, kopya)
        mod = yukle(kopya, "cdb_damga_kopya")
        for vaka, (hukum, sebep) in BEKLENEN.items():
            g_hukum, g_sebep = _vaka_kos(mod, os.path.join(td, "asil"), vaka)
            tamam = (g_hukum, g_sebep) == (hukum, sebep)
            vaka_gecti += int(tamam)
            hata += int(not tamam)
            print("%s %-4s hukum=%s sebep=%s (beklenen %s/%s)" % (
                "✅" if tamam else "🔴", vaka, g_hukum, g_sebep, hukum, sebep))

        with open(KAYNAK, encoding="utf-8") as f:
            metin = f.read()
        for ad, capa, yama, hedef, yanlis in MUTANTLAR:
            adet = metin.count(capa)
            if adet != 1:
                print("🔴 %s CAPA_ADEDI=%d (1 olmali) — mutant uygulanamadi" % (ad, adet))
                hata += 1
                continue
            myol = os.path.join(td, "cip_dogum_bekcisi_%s.py" % ad.lower())
            with open(myol, "w", encoding="utf-8") as f:
                f.write(metin.replace(capa, yama))
            mmod = yukle(myol, "cdb_damga_%s" % ad.lower())
            g_hukum, g_sebep = _vaka_kos(mmod, os.path.join(td, ad), hedef)
            beklenen = BEKLENEN[hedef]
            # Mutant OLDU = hedef vaka mutantta BEKLENENDEN SAPTI ve sapma
            # tam da hedef kolun urettigi yanlis hukum.
            oldu = (g_hukum, g_sebep) != beklenen and g_hukum == yanlis
            mutant_oldu += int(oldu)
            hata += int(not oldu)
            print("%s %s -> %s hukum=%s sebep=%s (mutantta beklenen %s)" % (
                "✅ OLDU" if oldu else "🔴 YASADI", ad, hedef, g_hukum, g_sebep, yanlis))
    finally:
        shutil.rmtree(td, ignore_errors=True)

    sha_sonra = _sha(KAYNAK)
    if sha_once != sha_sonra:
        print("🔴 KONTROL: canli kaynak DEGISTI (%s -> %s)" % (sha_once[:12], sha_sonra[:12]))
        hata += 1
    if os.path.exists(td):
        print("🔴 KONTROL: gecici dizin SILINMEDI: %s" % td)
        hata += 1
    print("VAKA_GECTI=%d/%d MUTANT_OLDU=%d/%d KAYNAK_SHA=%s TEMIZLIK=%s" % (
        vaka_gecti, len(BEKLENEN), mutant_oldu, len(MUTANTLAR), sha_sonra[:12],
        "OK" if not os.path.exists(td) else "KALDI"))
    print("SONUC: %s" % ("YESIL ✅" if hata == 0 else "KIRMIZI 🔴 hata=%d" % hata))
    return 0 if hata == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

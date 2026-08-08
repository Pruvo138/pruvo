#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — parite kaydi YAZARI kanit KUCULTMUYOR, OKUYUCU gerilemeyi GORUYOR mu.

NEDEN VAR (olculdu, 8 Agu 2026):
  YAZAR: `kayit_yaz` kaydi `d["aileler"][aile] = girdi` ile TUMUYLE SET ediyordu —
    birlestirme yok, kuculme kontrolu yok, bayrak yok, kuru prova yok. Kanitin gucunu
    dusuren bir yeniden-olcum sessizce (exit 0) "guncellendi" diyordu.
  OKUYUCU: tools/onizleme-vaat-kapisi.py yalnizca SABIT tabana bakiyordu
    (EN_AZ_PARITE_NOKTA=8000). Canli kayitta olculenNokta 48000; 8000'e cekmek
    (-%83,3) kapiyi YESIL birakirdi. `ilanEdilenIzgara` icin hicbir alt sinir YOKTU;
    `M3` 12971 -> 1 kuculmesi de ">0" iddiasini gecerdi.

NE KILITLER (her madde ilgili satir bozulunca KIRMIZI yanar):
  (a) Sayisal alan KUCULMESI varsayilanda REDDEDILIR; dosya BAYT BAYT degismez ve
      eski->yeni TEK TEK basilir (sessiz basari YOK).
  (b) Kuculme olcusu IKI KAYNAKTAN olculur: mevcut KAYIT ve MONOTON TAVAN. Kayit elle
      dusurulup tavan bayatlatilarak kapi atlatilamaz.
  (c) Kontrol mutanti sayilari da kanittir: M3 12971 -> 1 KUCULMEDIR (">0" iddiasi
      hala gecerdi — ayirt etme gucu yok olurdu).
  (d) BUYUME serbesttir ve tavani YUKSELTIR (eksen YONLU: her yeniden olcum yayini
      durdurmaz).
  (e) `--kuru-prova` HICBIR BAYT yazmaz ama AYNI hukmu verir.
  (f) Kucultmek ACIK `--ezmeye-izin-ver` ister; verilince tavan da o degere CEKILIR.
  (g) OKUYUCU: tavana gore dusmus kayit KIRMIZI — SABIT TABANIN USTUNDE olsa bile.
  (h) OKUYUCU: tavan blogu YOKSA hukum VERILEMEZ -> OLCULEMEDI ("gerileme yok"
      VARSAYILMAZ).
  (i) OKUYUCU KONTROLU: tavanin USTUNE cikan kayit YESIL (yanlis-pozitif nobeti).
  (j) Alan silinerek/tipi bozularak gerileme GIZLENEMEZ.
  (k) Bayraklarin VARSAYILANI `argparse` DEFAULT'undan okunur (duzyazidan DEGIL).

OFFLINE ve SENTETIK: canli jenerator/test/uretilebilirlik-parite.json OKUNMAZ/YAZILMAZ —
gecici bir kok kurulur. Kabul testinin KENDISI olculur:
  python3 tools/parite-kayit-mutasyon-test.py
Calistir:  python3 tools/parite-kayit-test.py   (0 = gecti, 1 = kaldi)
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)


def _yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


pk = _yukle("pruvo_parite_kaydi", os.path.join(TOOLS, "parite_kaydi.py"))

FAILS = []


def kontrol(ad, kosul, ek=""):
    print(("  PASS  " if kosul else "  FAIL  ") + ad
          + (("   [%s]" % ek) if (ek and not kosul) else ""))
    if not kosul:
        FAILS.append(ad)


def bitir():
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldi)" % len(FAILS))
        sys.exit(1)
    print("\nSONUC: YESIL ✅")
    sys.exit(0)


# --------------------------------------------------------------------------
# SENTETIK FIKSTUR
AILE = "test-aile"
MOTOR = "motor-test.scad"
MOTOR_OZET = hashlib.sha256(b"sentetik-motor").hexdigest()
SEMA = {
    "id": "sentetik-urun",
    "kisitlar": [{"min": {"terimler": {"a": 1}}}],
    "parametreler": [
        {"ad": "x", "tip": "sayi", "min": 0, "max": 10, "adim": 1, "aciklama": "metin"},
        {"ad": "y", "tip": "secim", "secenekler": [{"deger": "a"}, {"deger": "b"}]},
    ],
}
IZGARA = pk.ilan_edilen_izgara(SEMA)      # 11 * 2 = 22
ESIK = 10                                  # sabit taban (kucuk): gerileme ekseni ONUN USTUNDE olculur


def girdi_yap(nokta=48000, izgara=None, m3=12971):
    return {
        "surucu": "sentetik", "mod": "nokta=%d" % nokta,
        "olculenNokta": nokta, "tehlikeliKova": 0, "cozulmeyen": 0, "kovalar": {},
        "ilanEdilenIzgara": IZGARA if izgara is None else izgara,
        "kontrolMutantlari": {"M1": 470, "M2": 187, "M3": m3, "M4": 0},
        "motorDosya": MOTOR, "motorOzet": MOTOR_OZET,
        "semaUrunId": SEMA["id"],
        "semaKisitOzeti": pk.kisit_ozeti(SEMA),
        "semaKutuOzeti": pk.kutu_ozeti(SEMA),
        "tarih": "2026-08-08",
    }


def kok_kur():
    kok = tempfile.mkdtemp(prefix="parite-kayit-")
    os.makedirs(os.path.join(kok, *pk.KAYIT_YOLU[:-1]))
    os.makedirs(os.path.join(kok, *pk.PARMAKIZI_YOLU[:-1]))
    with open(os.path.join(kok, *pk.PARMAKIZI_YOLU), "w", encoding="utf-8") as f:
        json.dump({"dosyalar": {MOTOR: MOTOR_OZET}}, f)
    return kok


def kayit_yolu(kok):
    return os.path.join(kok, *pk.KAYIT_YOLU)


def ham(kok):
    with open(kayit_yolu(kok), encoding="utf-8") as f:
        return json.load(f)


def yaz(kok, girdi, **kw):
    """(hata, cikti) — hata None ise yazma denendi (kuru prova dahil)."""
    tampon = io.StringIO()
    hata = None
    try:
        with contextlib.redirect_stdout(tampon):
            pk.kayit_yaz(kok, AILE, girdi, aciklama="sentetik", **kw)
    except Exception as exc:
        hata = exc
    return hata, tampon.getvalue()


def dogrula(kok):
    """girdi_dogrula sarmalayicisi — YAKALANMAYAN istisna kosumu COKERTMEZ.

    Cokme ile KIRMIZI ayni sey degildir ([[mutasyon-kaniti-yeniden-uretilebilir]]):
    mutasyon bataryasi "SONUC:" satirini arar. Istisna burada ACIKCA bir KALDI
    kontrolune cevrilir, hukum "COKTU" olur ve hicbir iddiaya YESIL yazdirmaz."""
    try:
        return pk.girdi_dogrula(kok, AILE, SEMA, ESIK)
    except Exception as exc:
        return "COKTU", "%s: %s" % (type(exc).__name__, str(exc)[:200])


def elle_yaz(kok, d):
    with open(kayit_yolu(kok), "w", encoding="utf-8") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


# ==========================================================================
print("=== A) ILK YAZMA: kayit + MONOTON tavan olusur ===")
KOK = kok_kur()
hata, _ = yaz(KOK, girdi_yap())
kontrol("ilk yazma hatasiz", hata is None, repr(hata))
d = ham(KOK)
kontrol("(a) aileler girdisi yazildi",
        d["aileler"][AILE]["olculenNokta"] == 48000, json.dumps(d)[:200])
tavan = (d.get(pk.TAVAN_ALANI) or {}).get(AILE) or {}
kontrol("(a) tavan blogu olustu ve olculenNokta=48000",
        tavan.get("olculenNokta") == 48000, json.dumps(tavan))
kontrol("(c) tavan kontrol mutanti M3'u de tasiyor (12971)",
        tavan.get("kontrolMutantlari.M3") == 12971, json.dumps(tavan))
kontrol("(a) tavan ilanEdilenIzgara'yi da tasiyor",
        tavan.get("ilanEdilenIzgara") == IZGARA, json.dumps(tavan))

print("\n=== B) KUCULME varsayilanda REDDEDILIR (dosya BAYT BAYT ayni) ===")
_once = open(kayit_yolu(KOK), "rb").read()
hata, cikti = yaz(KOK, girdi_yap(nokta=20000))
kontrol("(a) KucultmeReddi yukseldi", isinstance(hata, pk.KucultmeReddi), repr(hata))
kontrol("(a) dosya BAYT BAYT degismedi", open(kayit_yolu(KOK), "rb").read() == _once)
kontrol("(a) eski->yeni TEK TEK basildi (48000 -> 20000)",
        "olculenNokta 48000 -> 20000" in cikti and "YAZILMADI" in cikti, cikti[-300:])
kontrol("(a) hata metni ACIK bayragi gosteriyor",
        "--ezmeye-izin-ver" in str(hata), str(hata)[:200])

print("\n=== C) KONTROL MUTANTI SAYISI da kanittir (M3 12971 -> 1) ===")
hata, cikti = yaz(KOK, girdi_yap(m3=1))
kontrol("(c) M3 kuculmesi REDDEDILDI ('>0' iddiasi HALA gecerdi)",
        isinstance(hata, pk.KucultmeReddi), repr(hata))
kontrol("(c) hangi alan oldugu basildi",
        "kontrolMutantlari.M3 12971 -> 1" in cikti, cikti[-300:])

print("\n=== D) BUYUME serbest ve TAVANI yukseltir (eksen YONLU) ===")
hata, _ = yaz(KOK, girdi_yap(nokta=60000))
kontrol("(d) buyume kabul edildi", hata is None, repr(hata))
kontrol("(d) tavan 60000'e yukseldi",
        (ham(KOK)[pk.TAVAN_ALANI][AILE]["olculenNokta"]) == 60000)

print("\n=== E) TAVAN AYRI KAYNAK: kayit elle dusurulse de kapi tutar ===")
d = ham(KOK)
d["aileler"][AILE]["olculenNokta"] = 30000          # kayit elle dusuruldu, tavan 60000 KALDI
elle_yaz(KOK, d)
hata, cikti = yaz(KOK, girdi_yap(nokta=40000))       # kayda gore BUYUME, tavana gore DUSUS
kontrol("(b) kayda gore buyume olsa da TAVANA gore dusus REDDEDILDI",
        isinstance(hata, pk.KucultmeReddi), repr(hata))
kontrol("(b) reddin kaynagi TAVAN olarak basildi",
        "KUCULME (tavan)" in cikti, cikti[-300:])

print("\n=== F) --kuru-prova: HICBIR BAYT yazmaz, AYNI hukmu verir ===")
_once = open(kayit_yolu(KOK), "rb").read()
hata, cikti = yaz(KOK, girdi_yap(nokta=90000), kuru_prova=True)
kontrol("(e) kuru provada dosya BAYT BAYT ayni",
        open(kayit_yolu(KOK), "rb").read() == _once)
kontrol("(e) kuru prova ne olacagini basti", "KURU PROVA" in cikti, cikti[-200:])
kontrol("(e) kuru prova hatasiz kosti (mesru buyume)", hata is None, repr(hata))
hata, _ = yaz(KOK, girdi_yap(nokta=40000), kuru_prova=True)
kontrol("(e) kuru provada da KUCULME REDDEDILIR (hukum ayni)",
        isinstance(hata, pk.KucultmeReddi), repr(hata))
kontrol("(e) ve yine hicbir bayt yazilmadi",
        open(kayit_yolu(KOK), "rb").read() == _once)

print("\n=== G) --ezmeye-izin-ver: ACIK istekle kucultur, TAVANI da ceker ===")
hata, cikti = yaz(KOK, girdi_yap(nokta=40000), ezmeye_izin_ver=True)
kontrol("(f) acik bayrakla yazildi", hata is None, repr(hata))
d = ham(KOK)
kontrol("(f) kayit 40000 oldu", d["aileler"][AILE]["olculenNokta"] == 40000)
kontrol("(f) tavan da 40000'e CEKILDI (bilerek)",
        d[pk.TAVAN_ALANI][AILE]["olculenNokta"] == 40000)
kontrol("(f) ezme izi basildi", "BILEREK EZILDI" in cikti, cikti[-300:])
shutil.rmtree(KOK, ignore_errors=True)

# ==========================================================================
print("\n=== H) OKUYUCU: tavana gore GERILEME, SABIT TABANIN USTUNDE olsa da KIRMIZI ===")
KOK = kok_kur()
yaz(KOK, girdi_yap(nokta=48000))
d = ham(KOK)
d["aileler"][AILE]["olculenNokta"] = 20000           # tavan 48000, sabit taban 10
elle_yaz(KOK, d)
hukum, sebep = dogrula(KOK)
kontrol("(g) hukum KIRMIZI", hukum == pk.KIRMIZI, "%s: %s" % (hukum, sebep))
kontrol("(g) sebep GERILEME diyor ve eski->yeni tasiyor",
        "GERILEME" in sebep and "48000 -> 20000" in sebep, sebep[:300])
kontrol("(g) AYIRT EDICI: sabit taban ekseni bunu GORMEZDI (20000 >= %d)" % ESIK,
        "olculen nokta" not in sebep, sebep[:300])

print("\n=== I) OKUYUCU: TAVAN BLOGU YOKSA hukum VERILEMEZ (OLCULEMEDI) ===")
d = ham(KOK)
del d[pk.TAVAN_ALANI]
elle_yaz(KOK, d)
hukum, sebep = dogrula(KOK)
kontrol("(h) hukum OLCULEMEDI ('gerileme yok' VARSAYILMADI)",
        hukum == pk.OLCULEMEDI, "%s: %s" % (hukum, sebep))
kontrol("(h) sebep tavan blogunun yoklugunu soyluyor",
        pk.TAVAN_ALANI in sebep, sebep[:200])

# 🔴 IKINCI KOL: tavan blogu VAR ama BU AILENIN girdisi yok/bos. Yukaridaki kol
# (blok tumuyle yok) tavan_oku'da yakalanir; bu kol girdi_dogrula'nin KENDI
# fail-closed dalidir. Ikisi ayri ayri olculmezse biri sessizce olur.
KOK2 = kok_kur()
yaz(KOK2, girdi_yap(nokta=48000))
d = ham(KOK2)
d[pk.TAVAN_ALANI] = {"baska-aile": {"olculenNokta": 1}}   # blok VAR, aile girdisi YOK
elle_yaz(KOK2, d)
hukum, sebep = dogrula(KOK2)
kontrol("(h2) tavan blogu VAR ama AILE girdisi YOK -> OLCULEMEDI",
        hukum == pk.OLCULEMEDI, "%s: %s" % (hukum, sebep))
kontrol("(h2) sebep GERILEME EKSENI OLCULEMEDI diyor",
        "GERILEME EKSENI OLCULEMEDI" in sebep, sebep[:200])
d[pk.TAVAN_ALANI] = {AILE: {}}                             # aile girdisi BOS
elle_yaz(KOK2, d)
hukum, sebep = dogrula(KOK2)
kontrol("(h2) BOS aile tavani da OLCULEMEDI (bos = 'gerileme yok' DEGIL)",
        hukum == pk.OLCULEMEDI, "%s: %s" % (hukum, sebep))
shutil.rmtree(KOK2, ignore_errors=True)
shutil.rmtree(KOK, ignore_errors=True)

print("\n=== J) OKUYUCU KONTROLU: tavanin USTUNDEKI kayit YESIL (yanlis-pozitif yok) ===")
KOK = kok_kur()
yaz(KOK, girdi_yap(nokta=48000))
d = ham(KOK)
d["aileler"][AILE]["olculenNokta"] = 60000
elle_yaz(KOK, d)
hukum, sebep = dogrula(KOK)
kontrol("(i) buyumus kayit YESIL", hukum == pk.YESIL, "%s: %s" % (hukum, sebep))

print("\n=== K) ALAN SILINEREK/BOZULARAK gerileme GIZLENEMEZ ===")
d = ham(KOK)
d["aileler"][AILE]["olculenNokta"] = "48000"          # sayisal DEGIL -> eksen kor kalirdi
elle_yaz(KOK, d)
hukum, sebep = dogrula(KOK)
kontrol("(j) hukum KIRMIZI", hukum == pk.KIRMIZI, "%s: %s" % (hukum, sebep))
kontrol("(j) sebep 'GERILEME OLCULEMEZ' diyor",
        "GERILEME OLCULEMEZ" in sebep, sebep[:300])
shutil.rmtree(KOK, ignore_errors=True)

print("\n=== L) BAYRAK VARSAYILANI argparse DEFAULT'undan okunur ===")
_olcum = _yukle("pruvo_rulman_olcum",
                os.path.join(ROOT, "jenerator", "test",
                             "rulman-uretilebilirlik-olcum.py"))
_a = _olcum.parser_kur().parse_args([])
kontrol("(k) --ezmeye-izin-ver varsayilani argparse'ta False",
        _a.ezmeye_izin_ver is False, repr(_a.ezmeye_izin_ver))
kontrol("(k) --kuru-prova varsayilani argparse'ta False",
        _a.kuru_prova is False, repr(_a.kuru_prova))
_b = _olcum.parser_kur().parse_args(["--ezmeye-izin-ver", "--kuru-prova"])
kontrol("(k) bayraklar verilince True (kol olu degil)",
        _b.ezmeye_izin_ver is True and _b.kuru_prova is True)
kontrol("(k) kuculme reddinin CLI cikis kodu SIFIR-DISI",
        isinstance(pk.KOD_KUCULTME, int) and pk.KOD_KUCULTME != 0, repr(pk.KOD_KUCULTME))

bitir()

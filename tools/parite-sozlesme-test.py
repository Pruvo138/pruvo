#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — PARITE CIKIS KODU SOZLESMESI: TEK KAYNAK + 4/4 TUKETICI ESLEMESI.

    python3 tools/parite-sozlesme-test.py

NEDEN VAR (olculdu, 27 Tem): parite testlerinin cikis kodlari (0/1/2/3) DORT ayri yerde
tuketiliyordu ve UC AYRI SOZLESME olusmustu — biri exit 3'u ATLANDI, biri BLOKLU, biri
BLOKE sayiyordu ve hicbiri digerinden haberdar degildi. Bir tuketici guncellenmeden
kalinca (regresyon-kapisi.py) kimse fark etmedi. Bu test:
  1. Sozlesmenin TEK KAYNAKTA (tools/parite-ortak.js) yazili oldugunu,
  2. Dort tuketicinin DORDUNUN de o kaynaga ADIYLA referans verdigini,
  3. Her tuketicinin 0/1/2/3 eslemesini AYRI AYRI (fiilen cagirarak) OLCER.

AGSIZ / YAN ETKISIZ: hicbir HTTP istegi, hicbir dosya yazimi yok. regresyon-kapisi.py'nin
esleme mantigi, gercek `_run()` fonksiyonuna istenen kodla CIKAN sentetik bir alt surec
verilerek olculur (parite testleri KOSTURULMAZ).
"""
import importlib.util
import os
import re
import subprocess
import sys

# "IKINCI TABLO" IMZASI: SATIR BASINA capalanmis kod->anlam listesi
#     "# 3 = OLCULEMEDI ..."  /  "  exit 2 = KOSULAMADI ..."
# ⚠️ KAPSAM DERSI (olculdu): once `"0 =" in metin` gibi SERBEST alt-dize aranmisti ->
# "h10 = []" gibi ALAKASIZ satirlar eslesip YANLIS-POZITIF kirmizi uretti. Capa satir
# basinda olmali; asagida hem POZITIF (sentetik tablo yakalanir) hem NEGATIF (gercek
# dosyalar temiz) yon kanitlanir.
_TABLO_SATIR = re.compile(r"^[ \t]*(?:#[ \t]*)?(?:exit[ \t]+)?([0-3])[ \t]*=[ \t]*\S", re.M)


def tablo_kodlari(metin):
    """Metinde SATIR BASINDA tanimlanan cikis kodlarinin kumesi. SAF."""
    return set(_TABLO_SATIR.findall(metin or ""))

TOOLS = os.path.dirname(os.path.abspath(__file__))
ORTAK = os.path.join(TOOLS, "parite-ortak.js")
TUKETICILER = {
    "filament-test.py": os.path.join(TOOLS, "filament-test.py"),
    "edge-flip-hazirlik.py": os.path.join(TOOLS, "edge-flip-hazirlik.py"),
    "regresyon-kapisi.py": os.path.join(TOOLS, "regresyon-kapisi.py"),
}
# 4. tuketici = DOGRUDAN CAGRI (kabuk/CI): sozlesmenin kendisi. Kaynak kod referansi
# yerine, parite-ortak.js'in disa verdigi sabitlerin tabloya UYDUGU olculur.
CAGRI_ADI = "dogrudan cagri (kabuk/CI)"

_gecti = 0
_kaldi = []


def ONA(kosul, ad):
    global _gecti
    if kosul:
        _gecti += 1
        print("  ✅ %s" % ad)
    else:
        _kaldi.append(ad)
        print("  ❌ KALDI: %s" % ad)


def yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ══ 1) TEK KAYNAK: sozlesme blogu parite-ortak.js'te mi? ════════════════════════════
print("\n1) SOZLESME TEK KAYNAKTA MI (tools/parite-ortak.js)")
ortak_metin = open(ORTAK, encoding="utf-8").read()
ONA("CIKIS KODU SOZLESMESI" in ortak_metin, "parite-ortak.js 'CIKIS KODU SOZLESMESI' blogunu iceriyor")
for satir in ("CIKIS_GECTI = 0", "CIKIS_KIRMIZI = 1", "CIKIS_KOSULAMADI = 2",
              "CIKIS_OLCULEMEDI = 3"):
    ONA(satir in ortak_metin, "sabit tanimli: %s" % satir)
ONA("1 (KIRMIZI)" in ortak_metin and "3 (OLCULEMEDI)" in ortak_metin,
    "yonetici ilke (1 > 3 > 0) sozlesmede YAZILI")
for ad in TUKETICILER:
    ONA(ad in ortak_metin, "sozlesme blogu tuketiciyi ADIYLA sayiyor: %s" % ad)

# ══ 2) DORT TUKETICI DE TEK KAYNAGA REFERANS VERIYOR MU? ════════════════════════════
print("\n2) TUKETICILER TEK KAYNAGA REFERANS VERIYOR MU")
for ad, yol in TUKETICILER.items():
    metin = open(yol, encoding="utf-8").read()
    ONA("parite-ortak.js" in metin and "SOZLESME" in metin.upper(),
        "%s -> tools/parite-ortak.js sozlesmesine referans veriyor" % ad)
    # IKINCI KOPYA NOBETI: tuketici kendi TAM tablosunu YENIDEN YAZMAMALI (>=3 kod).
    kod_kumesi = tablo_kodlari(metin)
    ONA(len(kod_kumesi) < 3,
        "%s icinde IKINCI bir tam cikis-kodu tablosu YOK (bulunan kod: %s)"
        % (ad, ",".join(sorted(kod_kumesi)) or "-"))
# NOBETCININ KENDISI DIRI MI (kirmizi-mutasyon: iki yon de kanitlanir)
ONA(len(tablo_kodlari("# 0 = GECTI\n# 1 = KIRMIZI\n# 2 = KOSULAMADI\n# 3 = OLCULEMEDI")) == 4,
    "ikinci-tablo nobetcisi POZITIF yonde calisiyor (sentetik tablo YAKALANIYOR)")
ONA(tablo_kodlari("    h10 = []\n    x = 3\n    y0 = 1\n") == set(),
    "ikinci-tablo nobetcisi ALAKASIZ koda takilmiyor (yanlis-pozitif YOK)")

# ══ 3) ESLEME 1/4 — filament-test.py: 3 -> ATLANDI (gorunur, bloklamaz) ═════════════
print("\n3) ESLEME 1/4 — filament-test.py")
FT = yukle("filament_test", TUKETICILER["filament-test.py"])
ok, et, sb = FT.parite_exit_yorumla(0, "SONUC: BIREBIR PARITE ✅")
ONA(ok and et == FT.PARITE_GECTI, "exit 0 -> GECTI (testi gecirir)")
ok, et, sb = FT.parite_exit_yorumla(1, "SONUC: PARITE YOK ❌")
ONA((not ok) and et == FT.PARITE_KIRMIZI, "exit 1 -> KIRMIZI (testi BLOKLAR)")
ok, et, sb = FT.parite_exit_yorumla(2, "urunAra() bulunamadi")
ONA((not ok) and et == FT.PARITE_KIRMIZI, "exit 2 -> KIRMIZI (fail-closed)")
ok, et, sb = FT.parite_exit_yorumla(3, "⚪ ÖLÇÜLEMEDİ: WAF/UA — HTTP 403")
ONA(ok and et == FT.PARITE_ATLANDI, "exit 3 -> ATLANDI: BLOKLAMAZ (ok=True)")
ONA(bool(sb) and "WAF/UA" in sb, "exit 3 -> sebep GORUNUR (bos degil)")
ok, et, sb = FT.parite_exit_yorumla(3, "⚠️ FIKSTUR MODU: test-only env verildi")
ONA(ok and et == FT.PARITE_ATLANDI and "FIKSTUR MODU" in sb,
    "exit 3 (PARITE_URUNLER) -> ATLANDI + uyari tuketiciye ULASIYOR (A15)")

# ── 3b) UCUNCU SINIF AYRIMI (6 Eyl 2026): kaynak YOK (ortam) ≠ sozlesme KIRIK (gerileme)
# Iki kollu; TERS YON olmadan bu ayrim bir bypass olurdu.
ok, et, sb = FT.parite_exit_yorumla(
    3, "⚪ ÖLÇÜLEMEDİ: BOT KAYNAGI YOK — /Users/okan/dev/pruvo-bot/worker/src/index.js")
ONA(ok and et == FT.PARITE_ATLANDI and "BOT KAYNAGI YOK" in sb,
    "exit 3 (BOT KAYNAGI YOK) -> ATLANDI + sebep ADIYLA (kardes depo CI'da yok)")
ok, et, sb = FT.parite_exit_yorumla(2, "index.js'te markaSorguKanonu() bulunamadi")
ONA((not ok) and et == FT.PARITE_KIRMIZI and "sozlesmesi KIRIK" in sb,
    "TERS YON: kaynak VAR + sozlesme KIRIK -> KIRMIZI KALIYOR (menzil daraltmasi, bypass DEGIL)")
# URETICI TARAFI: parite-ege.js iki kolu AYRI cikis koduna baglamis mi (kaynak metinden)
_ege = open(os.path.join(TOOLS, "parite-ege.js"), encoding="utf-8").read()
ONA("ortak.CIKIS_OLCULEMEDI" in _ege and "BOT KAYNAGI YOK" in _ege,
    "parite-ege.js: kaynak-yok kolu CIKIS_OLCULEMEDI'ye bagli (sabit ADIYLA, ciplak 3 degil)")
ONA("ortak.CIKIS_KOSULAMADI" in _ege,
    "parite-ege.js: sozlesme-kirik kolu CIKIS_KOSULAMADI'ya bagli (KIRMIZI korundu)")
ONA("process.exit(2)" not in _ege and "process.exit(3)" not in _ege,
    "parite-ege.js: ciplak sayiyla cikis YOK (sabitler tek kaynaktan okunur)")
ONA("BOT KAYNAGI YOK" in ortak_metin,
    "sozlesme tablosu ucuncu sinifi ADIYLA sayiyor (tek kaynak guncel)")

# ══ 4) ESLEME 2/4 — edge-flip-hazirlik.py: 3 -> BLOKLU (gerileme degil, GO da yok) ══
print("\n4) ESLEME 2/4 — edge-flip-hazirlik.py")
EF = yukle("edge_flip_hazirlik", TUKETICILER["edge-flip-hazirlik.py"])
ONA(EF.deg_komut(True, 0)[0] == EF.PASS, "exit 0 -> PASS")
ONA(EF.deg_komut(True, 1)[0] == EF.FAIL, "exit 1 -> FAIL (gercek gerileme)")
ONA(EF.deg_komut(True, 2)[0] == EF.BLOKLU, "exit 2 -> BLOKLU (kosulamadi)")
d3, kim3, det3 = EF.deg_komut(True, 3, "⚪ ÖLÇÜLEMEDİ: WAF/UA — HTTP 403")
ONA(d3 == EF.BLOKLU, "exit 3 -> BLOKLU (FAIL DEGIL: yanlis suclama yok)")
ONA(d3 != EF.FAIL and d3 != EF.PASS,
    "exit 3 -> ne FAIL ne PASS (yonetici ilke: olculemeyen YESILE donmez)")
ONA("WAF/UA" in det3 and "gerileme DEGIL" in det3, "exit 3 -> sebep + 'gerileme DEGIL' yazili")
ONA("GO da VERMEZ" in det3, "exit 3 -> GO VERMEDIGI acikca yazili")
d3b, _, det3b = EF.deg_komut(True, 3,
                             "D1 FAZLALIGI: yerel=100 < canli=112 | fazla=12 satir")
ONA("100" in det3b and "112" in det3b and "12" in det3b, "exit 3 sebebi SAYIYLA (olculen kanit)")
ONA("AYIRT EDILEMEDI" in det3b, "exit 3 sebebi KESIN HUKUM basmiyor")
# GO/NO-GO zinciri: BLOKLU bir adim GO VERDIRMEZ (mutasyon: PASS'a cevrilirse yakalanir)
ONA(EF.genel_karar([("parite", EF.BLOKLU, None, det3)]) == "NO-GO",
    "BLOKLU adim -> genel karar NO-GO (exit 3 GO uretemez)")
ONA(EF.genel_karar([("parite", EF.PASS, None, "exit 0")]) == "GO",
    "PASS adim -> GO (kirmizi-mutasyon: iki yon de kanitlandi)")

# ══ 5) ESLEME 3/4 — regresyon-kapisi.py: 3 -> BLOKE KALIR ══════════════════════════
print("\n5) ESLEME 3/4 — regresyon-kapisi.py")
RK = yukle("regresyon_kapisi", TUKETICILER["regresyon-kapisi.py"])


def rk_kod(kod, cikti="parite"):
    """Gercek _run()'i, istenen kodla cikan SENTETIK bir alt surecle olcer (ag/parite YOK)."""
    betik = "import sys; print(%r); sys.exit(%d)" % (cikti, kod)
    return RK._run("sentetik-parite", [sys.executable, "-c", betik], None)


ONA(rk_kod(0) == 0, "exit 0 -> gecer (0 doner)")
ONA(rk_kod(1) == 1, "exit 1 -> BLOKE (nonzero)")
ONA(rk_kod(2) == 2, "exit 2 -> BLOKE (nonzero)")
ONA(rk_kod(3) == 3, "exit 3 -> BLOKE KALIR (fail-closed; yayin yolunda)")
ONA(rk_kod(3) != 0, "exit 3 kesinlikle GECIRILMIYOR")
# Beklenen-desen kapisi hala calisiyor mu (exit 0 ama cikti yanlis)?
ONA(RK._run("desen", [sys.executable, "-c", "print('bos')"], "BIREBIR PARITE") == 1,
    "exit 0 + beklenen desen YOK -> yine BLOKE (desen kapisi diri)")

# ══ 6) ESLEME 4/4 — DOGRUDAN CAGRI: parite-ortak.js sabitleri tabloya uyuyor mu? ════
print("\n6) ESLEME 4/4 — %s" % CAGRI_ADI)
node_betik = (
    "const o=require(" + repr(ORTAK) + ");"
    "console.log(JSON.stringify([o.CIKIS_GECTI,o.CIKIS_KIRMIZI,o.CIKIS_KOSULAMADI,"
    "o.CIKIS_OLCULEMEDI,o.FIKSTUR_ENV,o.SUPURME_MUTLAK_TAVAN,o.ZAMAN_ASIMI_MS,o.DENEME,"
    # TAVAN artik SABIT DEGIL: katalog boyutundan turer. Sozlesme "sayi tanimli mi" degil
    # "OLCEKLENIYOR mu + ust sinir DURUYOR mu" diye olcer (sabitleyen mutant burada da yanar).
    "o.supurmeTavani(10000),o.supurmeTavani(20212),o.supurmeTavani(40424),"
    "o.supurmeTavani(100000000),o.IDS_PARTI]));"
)
p = subprocess.run(["node", "-e", node_betik], capture_output=True, text=True)
ONA(p.returncode == 0, "parite-ortak.js require edilebiliyor (%s)" % (p.stderr.strip()[:120] or "ok"))
if p.returncode == 0:
    import json
    (gecti_k, kirmizi_k, kosulamadi_k, olculemedi_k, fenv, mutlak, za, den,
     t10k, t20k, t40k, tdev, ids_parti) = json.loads(p.stdout)
    ONA([gecti_k, kirmizi_k, kosulamadi_k, olculemedi_k] == [0, 1, 2, 3],
        "dogrudan cagri cikis kodlari = 0/1/2/3 (sozlesme tablosu)")
    ONA("PARITE_URUNLER" in fenv, "PARITE_URUNLER fikstur-env listesinde (0 uretemez)")
    ONA("ARA_UC" in fenv, "ARA_UC fikstur-env listesinde (kanonik uc degistirilirse 0 yok)")
    ONA("PARITE_SUPURME_MUTLAK" in fenv,
        "supurme MUTLAK siniri fikstur-env listesinde (esik baypasi 0 uretemez)")
    ONA(isinstance(mutlak, int) and mutlak > 0,
        "supurme MUTLAK ust siniri tanimli (%s parti)" % mutlak)
    ONA(t10k == -(-10000 // ids_parti) and t20k == -(-20212 // ids_parti)
        and t40k == -(-40424 // ids_parti),
        "tavan KATALOGDAN turuyor (10000->%s, 20212->%s, 40424->%s parti)" % (t10k, t20k, t40k))
    ONA(t20k > t10k and t40k > t20k, "katalog buyudukce tavan BUYUYOR (sabit DEGIL)")
    ONA(tdev == mutlak, "MUTLAK ust sinir DURUYOR (sinirsiz buyume YOK: %s parti)" % tdev)
    ONA(isinstance(za, int) and za > 0, "zaman asimi tanimli (%s ms)" % za)
    ONA(isinstance(den, int) and den >= 2, "yeniden deneme tanimli (%s)" % den)

# ══ SONUC ═══════════════════════════════════════════════════════════════════════════
print("\n" + "-" * 74)
if _kaldi:
    print("PARITE SOZLESME TESTI: %d gecti | %d KALDI ❌" % (_gecti, len(_kaldi)))
    sys.exit(1)
print("PARITE SOZLESME TESTI: %d iddia, hepsi YESIL ✅ (4/4 tuketici eslemesi)" % _gecti)
sys.exit(0)

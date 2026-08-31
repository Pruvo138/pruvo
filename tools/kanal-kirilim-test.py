#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KANAL KIRILIM RAPORU KABUL TESTI.

  python3 tools/kanal-kirilim-test.py

NE OLCER: `tools/kanal-kirilim-raporu.py`nin KARAR fonksiyonlarini — GERCEK
`hukum()` + GERCEK `siniflandir()` (yani gercek node koprusu, gercek
shop/src/kanal-sinif.mjs). Sahte bir siniflayici ENJEKTE EDILMEZ: sahte
siniflayiciyla yesil yanan bir batarya, kaynak degistiginde yesil kalirdi.

ATLANAN TEK SEY CANLI D1'DIR (wrangler + ag). Satirlar fikstur olarak verilir;
`kanal_kolonu_var` bayragi ise raporun kendi fail-closed koluna BIREBIR ayni
degeri tasir — yani OLCULEMEDI hukmu de GERCEK kod yolundan olculur.

🔴 FIKSTUR UYDURMADIR: gercek siparis/musteri verisi bu dosyaya YAZILMAZ.

CIKIS KODU: 0 yesil · 1 kirmizi iddia · 3 OLCULEMEDI (rapor modulu yuklenemedi).
"""
import importlib.util
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAPOR_YOL = os.environ.get("PRUVO_KANAL_RAPOR") or os.path.join(
    KOK, "tools", "kanal-kirilim-raporu.py")

try:
    _spec = importlib.util.spec_from_file_location("kanal_kirilim_raporu", RAPOR_YOL)
    R = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(R)
    for _ad in ("hukum", "siniflandir", "sozluk", "RC_TAMAM", "RC_OLCULEMEDI"):
        if not hasattr(R, _ad):
            raise RuntimeError("rapor `%s` sunmuyor" % _ad)
except Exception as e:  # pragma: no cover
    print("OLCULEMEDI: rapor modulu yuklenemedi (%s): %s" % (RAPOR_YOL, e))
    sys.exit(3)

try:
    SOZ = R.sozluk()
except Exception as e:  # pragma: no cover
    print("OLCULEMEDI: kova sozlugu alinamadi (node koprusu): %s" % e)
    sys.exit(3)

gecen = 0
kalan = 0


def ol(ad, kosul, detay=""):
    global gecen, kalan
    if kosul:
        gecen += 1
        print("  OK  %s" % ad)
    else:
        kalan += 1
        print("  RED %s%s" % (ad, (" — " + str(detay)) if detay else ""))


def s(kanal, atif, durum, tutar=10000, kargo=0):
    """Fikstur satiri. `kanal` None ise anahtar HIC konmaz (kolon yok hali)."""
    k = {"atif": atif, "durum": durum, "tutar_kurus": tutar, "kargo_kurus": kargo}
    if kanal is not None:
        k["kanal"] = kanal
    return k


def kos(satirlar, kanal_kolonu_var=True):
    """GERCEK yol: siniflandir() -> hukum(). Doner (metin, rc)."""
    siniflar = R.siniflandir(satirlar) if kanal_kolonu_var else []
    return R.hukum(satirlar, kanal_kolonu_var, siniflar, SOZ, "(test)")


def kova_satiri(metin, kova):
    """Rapor tablosundan bir kovanin (adet, ciro_adet, ciro_metni) uclusu."""
    for satir in metin.splitlines():
        if satir.startswith(kova + " ") or satir.startswith(kova.ljust(24)):
            p = satir.split()
            # <kova> <adet> <ciro_adet> <ciro>
            return int(p[-3]), int(p[-2]), p[-1]
    return None


# ── 1) DORT KOVA DOGRU SAYAR ──────────────────────────────────────────────────
print("1) dort kova + iki gorunur bilinmiyorum kovasi dogru sayiyor")
FIKSTUR = [
    s("site", '{"ref":"REF:GS-BK-9Z3Q"}', "odendi", 10000, 2500),      # site-ucretli
    s("site", '{"utm_medium":"cpc","utm_source":"google"}', "tamamlandi", 20000),  # site-ucretli
    s("site", '{"ref":"REF:OG-BK-1A2B"}', "kargolandi", 30000),        # site-organik
    s("whatsapp", "", "uretimde", 40000),                              # whatsapp
    s("site", "", "odendi", 50000),                                    # atif-yok (atif-bos)
    s("site", '{"utm_medium":"zzz"}', "odendi", 60000),                # atif-yok (cozulemedi)
    s("instagram-dm", "", "odendi", 70000),                            # kanal-bilinmiyor
]
metin, rc = kos(FIKSTUR)
ol("1a rc=0 (TAMAM)", rc == R.RC_TAMAM, "rc=%s" % rc)
ol("1b HUKUM=TAMAM basiliyor", "HUKUM=TAMAM" in metin)
ol("1c site-ucretli = 2 siparis", (kova_satiri(metin, "site-ucretli") or (None,))[0] == 2,
   kova_satiri(metin, "site-ucretli"))
ol("1d site-organik = 1 siparis", (kova_satiri(metin, "site-organik") or (None,))[0] == 1,
   kova_satiri(metin, "site-organik"))
ol("1e whatsapp = 1 siparis", (kova_satiri(metin, "whatsapp") or (None,))[0] == 1,
   kova_satiri(metin, "whatsapp"))
ol("1f atif-yok/siniflanamaz = 2 siparis (ORGANIGE KATLANMADI)",
   (kova_satiri(metin, "atif-yok/siniflanamaz") or (None,))[0] == 2,
   kova_satiri(metin, "atif-yok/siniflanamaz"))
ol("1g kanal-bilinmiyor = 1 siparis (site'ye de whatsapp'a da YAZILMADI)",
   (kova_satiri(metin, "kanal-bilinmiyor") or (None,))[0] == 1,
   kova_satiri(metin, "kanal-bilinmiyor"))

# 🔴 KOVANIN ADI CIKTIDA GORUNMELI (spec sarti).
print("2) her kovanin ADI ciktida GORUNUYOR (sifir olan dahil)")
for kova in SOZ["kovalar"]:
    ol("2.%s ciktida gecer" % kova, kova in metin)
ol("2z sifir olan kova da tabloda satir aciyor (basilmayan kova, yok sanilirdi)",
   (kova_satiri(metin, "kanal-olculemedi") or (None,))[0] == 0,
   kova_satiri(metin, "kanal-olculemedi"))

# ── 3) CIRO KAPSAMI ───────────────────────────────────────────────────────────
print("3) ciro kapsami — bekliyor/iptal GIRMEZ")
CIRO_FIKSTUR = [
    s("site", '{"ref":"REF:GS-BK-9Z3Q"}', "odendi", 10000, 2500),   # GIRER -> 125,00 TL
    s("site", '{"ref":"REF:GS-BK-9Z3Q"}', "bekliyor", 999900),      # GIRMEZ
    s("site", '{"ref":"REF:GS-BK-9Z3Q"}', "iptal", 888800),         # GIRMEZ
    s("site", '{"ref":"REF:GS-BK-9Z3Q"}', "havale-bekliyor", 777700),  # GIRMEZ
    s("site", '{"ref":"REF:GS-BK-9Z3Q"}', "incele", 666600),        # GIRMEZ
    s("site", '{"ref":"REF:GS-BK-9Z3Q"}', "basarisiz", 555500),     # GIRMEZ
]
metin3, rc3 = kos(CIRO_FIKSTUR)
u = kova_satiri(metin3, "site-ucretli")
ol("3a adet TUM siparisleri sayar (6)", u and u[0] == 6, u)
ol("3b ciro_adet YALNIZ 'odendi ve sonrasi' (1)", u and u[1] == 1, u)
ol("3c ciro = 125,00 TL (tutar 100,00 + kargo 25,00; digerleri GIRMEDI)",
   u and u[2] == "125,00", u)
ol("3d 'iptal' tutari (8.888,00) ciroya SIZMADI", "8.888,00" not in metin3 and
   "888800" not in metin3)
ol("3e 'bekliyor' tutari (9.999,00) ciroya SIZMADI", "9.999,00" not in metin3)
ol("3f ciro kapsami RAPORDA BEYAN ediliyor",
   "BEYAN" in metin3 and "GIRER" in metin3 and "GIRMEZ" in metin3)
ol("3g beyanin GIRER listesi kanal-sinif.mjs CIRO_DURUMLARI ile BIREBIR",
   all(d in metin3 for d in SOZ["ciro_durumlari"]))
ol("3h tahsilat formulu (tutar + kargo) beyan ediliyor",
   "tutar_kurus + kargo_kurus" in metin3)

# ── 4) KANAL KOLONU YOK -> OLCULEMEDI + SIFIR-DISI RC ─────────────────────────
print("4) kanal kolonu YOKKEN fail-closed")
metin4, rc4 = kos(FIKSTUR, kanal_kolonu_var=False)
ol("4a rc SIFIR-DISI", rc4 != 0, "rc=%s" % rc4)
ol("4b rc = RC_OLCULEMEDI (3)", rc4 == R.RC_OLCULEMEDI, "rc=%s" % rc4)
ol("4c HUKUM=OLCULEMEDI basiliyor", "HUKUM=OLCULEMEDI" in metin4)
# 🔴 SPEC OLDURUCUSU: sessizce 'site' saymadigini OLC.
ol("4d hicbir kova SAYISI basilmiyor (yanlis sayi, sayisizliktan kotudur)",
   kova_satiri(metin4, "site-ucretli") is None and
   kova_satiri(metin4, "whatsapp") is None, metin4)
ol("4e 'kolon yok demek hepsi site' cikariminin YASAK oldugu ciktida yaziyor",
   "hepsi site" in metin4 and "YASAK" in metin4)
ol("4f cozum (d1-sync --sema) ciktida yaziyor", "--sema" in metin4)

# ── 5) BILINMEYEN KOVA -> SESSIZ YUTMA YOK ────────────────────────────────────
print("5) siniflayici tanimadigim bir kova dondururse rapor sayi URETMEZ")
sahte = [{"kova": "yepyeni-kova", "sebep": "x", "ciroya_girer": True,
          "tahsilat_kurus": 1000}]
metin5, rc5 = R.hukum([s("site", "", "odendi")], True, sahte, SOZ, "(test)")
ol("5a rc SIFIR-DISI (OLCULEMEDI)", rc5 == R.RC_OLCULEMEDI, "rc=%s" % rc5)
ol("5b bilinmeyen kovanin ADI ciktida GORUNUYOR", "yepyeni-kova" in metin5)
ol("5c bilinmeyen kova hicbir toplama KATILMADI",
   (kova_satiri(metin5, "site-ucretli") or (None,))[0] == 0 and
   "hicbir toplama KATILMADI" in metin5)

# ── 5b) SESSIZ SIFIR + TARIH DOGRULAMASI ──────────────────────────────────────
# 🔴 CANLI KOSUMDA OLCULEN GERCEK HATA (31 Agu): `--baslangic 2026-13-01` kalip
# suzgecinden GECIYOR, SQL dizge kiyasi hicbir satirla eslesmiyor ve rapor
# "HUKUM=TAMAM · 0 satir" basiyordu -> yazim hatasi, "o aralikta siparis yok" gibi
# GORUNUYORDU. Iki kol birden civilenir: takvim dogrulamasi + bos aralik uyarisi.
print("5b) sessiz sifir yasagi + takvim dogrulamasi")
ol("5b1 gecerli gun kabul (2026-08-31)", R.tarih_gecerli("2026-08-31"))
ol("5b2 13. AY reddedilir (kalip gecirirdi)", not R.tarih_gecerli("2026-13-01"))
ol("5b3 32. GUN reddedilir", not R.tarih_gecerli("2026-08-32"))
ol("5b4 subat 30 reddedilir (takvim, kalip degil)", not R.tarih_gecerli("2026-02-30"))
ol("5b5 bos/bicimsiz deger reddedilir",
   not R.tarih_gecerli("31-08-2026") and not R.tarih_gecerli("2026-8-1") and
   not R.tarih_gecerli("bugun"))
metin5b, rc5b = R.hukum([], True, [], SOZ, "2026-01-01 .. 2026-01-02")
ol("5b6 BOS aralik ACIKCA yazilir (sessiz bos tablo YOK)",
   "HIC SIPARIS YOK" in metin5b and "ARALIK bos" in metin5b, metin5b)
ol("5b7 bos aralik HATA DEGIL (rc=0) — ama gorunur", rc5b == R.RC_TAMAM, "rc=%s" % rc5b)

# ── 6) GIZLILIK — YASAK ALANLAR RAPOR CIKTISINDA HIC GECMEZ ───────────────────
print("6) gizlilik — ga_client_id / fbp / fbc rapora sizmiyor")
FBP = "fb.1.9999999999999.1234567890"
FBC = "fb.1.9999999999999.SAHTE-CLICK-ID"
GA_CID = "GA1.1.9999999999.8888888888"
ATIF_TAM = ('{"ga_client_id":"%s","fbp":"%s","fbc":"%s","utm_source":"google",'
            '"utm_medium":"cpc","ref":"REF:GS-BK-9Z3Q"}' % (GA_CID, FBP, FBC))
metin6, _rc6 = kos([s("site", ATIF_TAM, "odendi")])
for ad, deger in (("ga_client_id", GA_CID), ("fbp", FBP), ("fbc", FBC)):
    ol("6.%s ADI da DEGERI de rapor ciktisinda YOK" % ad,
       ad not in metin6 and deger not in metin6)
ol("6z click-id (gclid/gbraid/wbraid) da rapor ciktisinda YOK",
   "gclid" not in metin6 and "gbraid" not in metin6 and "wbraid" not in metin6)

# ── 7) TEK KAYNAK — Python'da IKINCI SOZLUK YOK ───────────────────────────────
print("7) tek kaynak — kova/ciro listesi Python'da elle YAZILI DEGIL")
with open(RAPOR_YOL, "r", encoding="utf-8") as f:
    rapor_metni = f.read()
kod = "\n".join(x for x in rapor_metni.splitlines() if not x.lstrip().startswith("#"))
# Kova adlari yalnizca JS'ten gelmeli: raporun KODUNDA (yorum disi) gecmemeliler.
sizan = [k for k in SOZ["kovalar"] if k != "kanal-olculemedi" and ('"%s"' % k) in kod]
ol("7a kova adlari raporun kodunda ELLE yazili DEGIL", not sizan, sizan)
sizan_durum = [d for d in SOZ["ciro_durumlari"] if ('"%s"' % d) in kod]
ol("7b ciro durumlari raporun kodunda ELLE yazili DEGIL", not sizan_durum, sizan_durum)
ol("7c rapor kova sozlugunu node koprusunden aliyor",
   "kanal-sinif-cli.mjs" in rapor_metni)
# 🔴 "wrangler" kelimesi docstring'de GECER (gerekce yazili) — olcut KELIME degil CAGRI
# olmali: rapor kendi wrangler surecini BASLATMAMALI, d1-sync'in sorgu/kolon_var_mi
# fonksiyonlarini cagirmali. [[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]
ol("7d rapor D1'i KANONIK istemciden okuyor (ikinci wrangler sarmalayicisi YOK)",
   "d1-sync.py" in rapor_metni and "d1.sorgu(" in kod and "d1.kolon_var_mi(" in kod and
   "npx" not in kod and "d1 execute" not in kod)
ol("7e rapor CANLI D1'e YAZMIYOR (INSERT/UPDATE/DELETE/ALTER yok)",
   not any(x in kod.upper() for x in ("INSERT ", "UPDATE ", "DELETE ", "ALTER ", "DROP ")))
ol("7f rapor MUSTERI ALANI okumuyor (ad/tel/eposta/adres SELECT'te yok)",
   not any(x in kod for x in ("musteri_ad", "musteri_tel", "musteri_eposta",
                              "musteri_adres")))

print("\n%d gecti / %d kaldi" % (gecen, kalan))
sys.exit(0 if kalan == 0 else 1)

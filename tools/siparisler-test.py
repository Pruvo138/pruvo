#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIPARISLER.PY KABUL TESTLERI.

    python3 tools/siparisler-test.py

Sahte wrangler ciktisiyla (wrangler_sorgu monkeypatch) tablo bicimini ve
--durum sozgecini dogrular — GERCEK D1'e dokunmaz, GERCEK subprocess
calistirmaz. Son madde (6) CANLI D1'e 1 gercek --son 2 kosumu yapar (bu arac
SALT-OKUNUR, SELECT disina cikamaz — test bunu da ayrica dogrular); ciktidaki
musteri adi/telefonu MASKELIDIR ama maskelemeyi BU TEST YAPMAZ — maskeleme
`siparisler.py`'nin kendisinde (`maskele_ad`/`maskele_tel`, varsayilan ACIK)
yapilir ve nobetcisi `tools/siparis-maske-test.py`'dir. Bu dosya yalnizca
maskeli degerlerin alan alan basildigini olcer (TEST 5).

  1. sql_sorgu: durum="hepsi"      -> WHERE YOK
  2. sql_sorgu: durum="odendi" vb. -> WHERE durum = '...' dogru
  3. sql_sorgu: bilinmeyen durum   -> ValueError (guard calisiyor)
  4. wrangler_sorgu: SELECT olmayan ifade -> ValueError (yazma kapisi kapali)
  5. format_siparis: sahte satirdan beklenen alanlarin hepsi tabloda gorunuyor
     (siparis no, yerel saat, durum, yontem, urun/kargo/genel toplam TL,
     musteri ad+tel MASKELI, kalem basligi+malzeme/renk+adet+tutar+kisaltilmis detay)
  6. CANLI kosum: python3 tools/siparisler.py --son 2 exit 0 doner + cikti
     "PRUVO SIPARISLER" basligini icerir (ad/telefon siparisler.py tarafindan
     zaten maskeli basilir — bkz tools/siparis-maske-test.py)
"""
import json
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import siparisler  # noqa: E402

SONUC = []

# BEYAN: hangi kolda hangi testlerin KAYIT ETMESI zorunlu. Bir testin cagrisi
# silinir / govdesi no-op edilirse "kirmizi yok" diye YESIL yanmasin diye vardir.
BEKLENEN_AGSIZ = (1, 2, 3, 4, 5, "5b", 7)
BEKLENEN_CANLI = (1, 2, 3, 4, 5, "5b", 6, 7)


def suite_butunlugu(sonuc, beklenen):
    """(hatalar) — SAF fonksiyon; oz-nobetci (TEST 7) bunu POZITIF+NEGATIF surer."""
    hatalar = []
    gorulen = [s[0] for s in sonuc]
    eksik = [n for n in beklenen if n not in gorulen]
    mukerrer = sorted(set(str(n) for n in gorulen if gorulen.count(n) > 1))
    fazla = sorted(set(str(n) for n in gorulen if n not in beklenen))
    if eksik:
        hatalar.append("SUITE EKSIK: %s numarali test(ler) hic KAYIT ETMEDI -> govdesi "
                       "silinmis/atlanmis olabilir; 'kirmizi yok' YESIL DEMEK DEGILDIR"
                       % ", ".join(str(n) for n in eksik))
    if mukerrer:
        hatalar.append("SUITE MUKERRER: %s numarasi birden fazla kayit etti"
                       % ", ".join(mukerrer))
    if fazla:
        hatalar.append("SUITE BEYAN DISI: %s numarali test BEKLENEN demetinde yok "
                       "(test eklendiyse demeti guncelle)" % ", ".join(fazla))
    return hatalar


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("OK" if gecti else "FAIL", no, ad,
                                    (" | " + detay) if detay else ""), flush=True)


def test_1_hepsi_where_yok():
    sql = siparisler.sql_sorgu(10, "hepsi")
    kayit(1, "durum=hepsi -> WHERE eklenmiyor",
          "WHERE" not in sql and "LIMIT 10" in sql, sql)


def test_2_durum_where():
    for d in siparisler.DURUMLAR:
        sql = siparisler.sql_sorgu(5, d)
        beklenen = "WHERE durum = '%s'" % d
        if beklenen not in sql or "LIMIT 5" not in sql:
            kayit(2, "durum=%s -> dogru WHERE" % d, False, sql)
            return
    kayit(2, "her gecerli durum icin dogru WHERE + LIMIT", True)


def test_3_bilinmeyen_durum():
    try:
        siparisler.sql_sorgu(10, "gecersiz-durum")
        kayit(3, "bilinmeyen durum -> ValueError", False, "exception firlamadi")
    except ValueError:
        kayit(3, "bilinmeyen durum -> ValueError", True)


def test_4_yazma_kapisi():
    denemeler = [
        "DELETE FROM siparisler",
        "UPDATE siparisler SET durum='odendi'",
        "INSERT INTO siparisler DEFAULT VALUES",
        "  select * from siparisler; DROP TABLE siparisler;",  # bile basi SELECT
    ]
    hepsi_dogru = True
    for sql in denemeler[:3]:
        try:
            siparisler.wrangler_sorgu(sql)
            hepsi_dogru = False
            print("      beklenmedik: reddetmedi -> %r" % sql)
        except ValueError:
            pass
    kayit(4, "SELECT disi ifade wrangler_sorgu tarafindan reddediliyor", hepsi_dogru)


SAHTE_SATIR = {
    "siparis_no": "PR-260101-000000-XYZ",
    "tarih": "2026-01-01T10:00:00.000Z",
    "durum": "odendi",
    "odeme_yontemi": "kart",
    "tutar_kurus": 12345,
    "kargo_kurus": 25000,
    "kdv_kurus": 6111,
    "musteri_ad": "Test Musteri",
    "musteri_tel": "5551112233",
    "urunler": json.dumps([{
        "id": "test-urun",
        "baslik": "Test Urun Basligi",
        "malzeme": "PLA",
        "renk": "Kirmizi",
        "adet": 3,
        "birim_kurus": 4115,
        "tutar_kurus": 12345,
        "parametre_detay": "Bu cok uzun bir parametre detayidir ve kisaltilmasi beklenir " * 2,
    }]),
}


def _blok(row, tty):
    """format_siparis'i SABIT bir TTY halinde uretir. Cikti artik KANALA bagli
    (parametre_detay TTY disinda basilmaz) -> testin hukmu, kosumun bir terminalde
    mi yoksa boruda mi oldugna GORE DEGISMEMELI."""
    eski = siparisler._tty
    siparisler._tty = lambda: tty
    try:
        return siparisler.format_siparis(row)
    finally:
        siparisler._tty = eski


def test_5_format_alanlari():
    blok = _blok(SAHTE_SATIR, False)        # TTY DISI kol (boru/CI) — deterministik
    beklenenler = [
        "PR-260101-000000-XYZ",
        "01.01.2026 13:00",          # UTC 10:00 -> Europe/Istanbul (+3) 13:00
        "durum: odendi",
        "yontem: kart",
        siparisler.tl(12345),        # urun toplami
        siparisler.tl(25000),        # kargo
        siparisler.tl(12345 + 25000),  # genel toplam
        # 🔴 31 TEM — MASKELI beklenti (HAM beklenti SILINMEDI, maskeliye CEVRILDI:
        # "alan hala basiliyor mu" ekseni korunur). Maskeleme siparisler.py'de yapilir;
        # burada LITERAL yazilir (maskele_*() cagrisiyla yazilsa tautoloji olurdu ve
        # fonksiyon bozulunca beklenti de onunla birlikte bozulurdu).
        "T*** M***",                 # musteri_ad "Test Musteri" -> maskeli
        "******2233",                # musteri_tel "5551112233"  -> maskeli
        "Test Urun Basligi",
        "PLA / Kirmizi",
        "adet: 3",
        siparisler.tl(12345),
    ]
    eksik = [b for b in beklenenler if b not in blok]
    # HAM kisisel deger blokta OLMAMALI (asil nobetci siparis-maske-test.py;
    # bu satir beklentinin "maskeliye cevrildi" halinin sessizce geri donmesini yakalar)
    ham_sizan = [h for h in ("Test Musteri", "5551112233") if h in blok]
    kayit(5, "format_siparis beklenen tum alanlari iceriyor (ad/tel MASKELI)",
          not eksik and not ham_sizan,
          ("eksik=%s" % eksik if eksik else "") + ("ham sizinti=%s" % ham_sizan
                                                   if ham_sizan else ""))

    # 🔴 31 TEM (2. tur) — parametre_detay artik KANALA bagli: musteri SERBEST METNI
    # oldugu icin TTY disinda HIC basilmaz (siparisler.py kanal kapisi). Kisaltma
    # ekseni bu yuzden TTY kolunda olculur; TTY disi kolda "hic yok + yer tutucu var"
    # olculur. Iki eksen de tek kayit (5b) altinda — numaralandirma BOZULMADI.
    tam_detay = json.loads(SAHTE_SATIR["urunler"])[0]["parametre_detay"]
    tty_blok = _blok(SAHTE_SATIR, True)
    kisaltiliyor = ("..." in tty_blok) and (tam_detay not in tty_blok)
    ttysiz_gizli = (tam_detay not in blok) and ("parametre detayi:" in blok)
    kayit("5b", "parametre_detay: TTY'de kisaltiliyor, TTY disinda hic basilmiyor",
          kisaltiliyor and ttysiz_gizli,
          "" if (kisaltiliyor and ttysiz_gizli)
          else "kisaltma=%s ttysiz_gizli=%s" % (kisaltiliyor, ttysiz_gizli))


def test_6_canli_kosum():
    p = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "siparisler.py"), "--son", "2"],
        cwd=ROOT, capture_output=True, text=True, timeout=60)
    basarili = p.returncode == 0 and "PRUVO SIPARISLER" in p.stdout
    kayit(6, "canli D1 kosumu exit 0 + basligi iceriyor", basarili,
          ("exit=%d" % p.returncode) if not basarili else "")
    if basarili:
        print("      --- canli cikti (ilk 25 satir; ad/tel siparisler.py'de ZATEN "
              "maskeli — elle maskeleme gerekmez) ---")
        for satir in p.stdout.splitlines()[:25]:
            print("      %s" % satir)
    elif p.stderr:
        print("      stderr: %s" % p.stderr[-500:])


# 🔴 31 TEM — AGSIZ KOL (AYIRMA, susturma DEGIL). OLCULDU: bu dosya CI'ya bloklayici
# adim olarak baglandiginda TEST 1..5b GECTI ama TEST 6 KIRMIZI yandi —
#   "In a non-interactive environment, it's necessary to set a CLOUDFLARE_API_TOKEN
#    environment variable for wrangler to work"
# (GitHub Actions kosumu 30596596650). TEST 6 CANLI D1'e wrangler ile vurur; Pages build
# job'unda o token YOKTUR (yalnizca D1 senkron adiminin env'inde tanimlidir) -> yapisal
# CI-kirmizi. Yerel makinede wrangler kimlikli oldugu icin YESIL yaniyordu: klasik
# "yerel-yesil / CI-kirmizi" tuzagi.
# COZUM: testin AGSIZ yarisi (TEST 1..5b — SQL uretimi, yazma kapisi, format alanlari,
# parametre kisaltmasi) `--agsiz` kolunda ayrildi ve CI'da BLOKLAYICI kosuyor. Canli kol
# SUSTURULMADI: bayraksiz kosum hala TEST 6'yi calistirir (yerel + merge kapisi).
AGSIZ = "--agsiz" in sys.argv


# 🔴 31 TEM — CAGRI SILME (hollowing) FAIL-OPEN'i KAPATILDI. OLCULDU: --agsiz kolunda
# 4 mutasyonun 4'u de YESIL yaniyordu (rc=0, "SONUC: 5/5 GECTI"): test_4 (YAZMA
# KAPISI) cagrisini silmek, govdesini no-op yapmak, test_3/test_1 cagrisini silmek.
# Hukum yalniz SONUC ICINDEKI kirmizilara bakiyordu -> nobetciyi KALDIRMAK, onu
# yesile cevirmenin en kolay yolu oluyordu (415a144e'nin jenerator/test/kabul.py'de
# kapattigi sinifin bu dosyadaki kalintisi). Artik BEKLENEN demeti beyan edilir ve
# suite_butunlugu() eksik/mukerrer/beyan-disi kaydi KIRMIZI yakar; hukum
# fonksiyonunun kendisi de TEST 7'de pozitif+negatif eksende olculur.
# 🔴 BEYAN SINIRI (31 Tem, 2. tur — curutucu olctu, kabul edildi): kapatilanin adi
# CAGRI SILME'dir. Bir testin CAGRISI ve BEKLENEN demetindeki numarasi BIRLIKTE
# silinirse suite YESIL kalir (olculdu). Bu tasarimin KABUL EDILEN SINIRIDIR —
# beyani dusurmek iki satirlik bir duzenlemedir ve DIFF'TE GORUNUR. "Bu dosyada
# hicbir bosaltma fail-open'i yok" demek FAZLA GENIS bir iddia olur.
def test_7_oz_nobetci(beklenen):
    tam = [(n, "sentetik", True) for n in beklenen]
    eksikli = [v for v in tam if v[0] != 4]
    vakalar = [
        ("negatif: tam kume temiz -> hata YOK",
         suite_butunlugu(tam, beklenen) == []),
        ("pozitif: bir test hic kayit etmezse -> SUITE EKSIK",
         any("SUITE EKSIK" in h for h in suite_butunlugu(eksikli, beklenen))),
        ("pozitif: ayni numara iki kez kayit ederse -> SUITE MUKERRER",
         any("SUITE MUKERRER" in h for h in suite_butunlugu(tam + [tam[0]], beklenen))),
        ("pozitif: beyan disi numara -> SUITE BEYAN DISI",
         any("SUITE BEYAN DISI" in h
             for h in suite_butunlugu(tam + [("z9", "sentetik", True)], beklenen))),
    ]
    kotu = [ad for ad, iyi in vakalar if not iyi]
    kayit(7, "oz-nobetci: suite_butunlugu pozitif+negatif eksende olcuyor",
          not kotu, ("BOZUK=%s" % kotu) if kotu else "4/4 eksen")


def main():
    print("SIPARISLER.PY KABUL TESTLERI%s" % (" (AGSIZ kol)" if AGSIZ else ""))
    print("=" * 66)
    beklenen = BEKLENEN_AGSIZ if AGSIZ else BEKLENEN_CANLI
    test_1_hepsi_where_yok()
    test_2_durum_where()
    test_3_bilinmeyen_durum()
    test_4_yazma_kapisi()
    test_5_format_alanlari()
    if AGSIZ:
        print("  ATLANDI TEST 6 — canli D1 kosumu (wrangler + CLOUDFLARE_API_TOKEN "
              "ister; --agsiz kolunda calistirilmaz)")
    else:
        test_6_canli_kosum()
    test_7_oz_nobetci(beklenen)
    print("=" * 66)
    hatalar = suite_butunlugu(SONUC, beklenen)
    for h in hatalar:
        print("  BULGU — %s" % h)
    basarisiz = [s for s in SONUC if not s[2]]
    print("SONUC: %d/%d GECTI%s" % (len(SONUC) - len(basarisiz), len(SONUC),
                                     " | SUITE BUTUNLUGU KIRMIZI" if hatalar else ""))
    return 1 if (basarisiz or hatalar) else 0


if __name__ == "__main__":
    sys.exit(main())

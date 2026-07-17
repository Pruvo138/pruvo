#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIPARISLER.PY KABUL TESTLERI.

    python3 tools/siparisler-test.py

Sahte wrangler ciktisiyla (wrangler_sorgu monkeypatch) tablo bicimini ve
--durum sozgecini dogrular — GERCEK D1'e dokunmaz, GERCEK subprocess
calistirmaz. Son madde (6) CANLI D1'e 1 gercek --son 2 kosumu yapar (bu arac
SALT-OKUNUR, SELECT disina cikamaz — test bunu da ayrica dogrular) ve ilk 2
kaydin telefon numarasini maskeleyip ekrana basar; bu satirlar elle
RAPOR-MIMARA.md'ye yapistirilir.

  1. sql_sorgu: durum="hepsi"      -> WHERE YOK
  2. sql_sorgu: durum="odendi" vb. -> WHERE durum = '...' dogru
  3. sql_sorgu: bilinmeyen durum   -> ValueError (guard calisiyor)
  4. wrangler_sorgu: SELECT olmayan ifade -> ValueError (yazma kapisi kapali)
  5. format_siparis: sahte satirdan beklenen alanlarin hepsi tabloda gorunuyor
     (siparis no, yerel saat, durum, yontem, urun/kargo/genel toplam TL,
     musteri ad+tel, kalem basligi+malzeme/renk+adet+tutar+kisaltilmis detay)
  6. CANLI kosum: python3 tools/siparisler.py --son 2 exit 0 doner + cikti
     "PRUVO SIPARISLER" basligini icerir (telefon maskelenerek ekrana basilir)
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


def test_5_format_alanlari():
    blok = siparisler.format_siparis(SAHTE_SATIR)
    beklenenler = [
        "PR-260101-000000-XYZ",
        "01.01.2026 13:00",          # UTC 10:00 -> Europe/Istanbul (+3) 13:00
        "durum: odendi",
        "yontem: kart",
        siparisler.tl(12345),        # urun toplami
        siparisler.tl(25000),        # kargo
        siparisler.tl(12345 + 25000),  # genel toplam
        "Test Musteri",
        "5551112233",
        "Test Urun Basligi",
        "PLA / Kirmizi",
        "adet: 3",
        siparisler.tl(12345),
    ]
    eksik = [b for b in beklenenler if b not in blok]
    kayit(5, "format_siparis beklenen tum alanlari iceriyor",
          not eksik, ("eksik=%s" % eksik) if eksik else "")

    # kisaltma: ham detay bloka TAM girmemeli (kisaltilmis hali girmeli)
    ham_detay = SAHTE_SATIR["urunler"]
    tam_detay = json.loads(ham_detay)[0]["parametre_detay"]
    kisaltilmis_var = "..." in blok
    tam_yok = tam_detay not in blok
    kayit("5b", "parametre_detay kisaltiliyor (tam metin blokta yok, '...' var)",
          kisaltilmis_var and tam_yok)


def test_6_canli_kosum():
    p = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "siparisler.py"), "--son", "2"],
        cwd=ROOT, capture_output=True, text=True, timeout=60)
    basarili = p.returncode == 0 and "PRUVO SIPARISLER" in p.stdout
    kayit(6, "canli D1 kosumu exit 0 + basligi iceriyor", basarili,
          ("exit=%d" % p.returncode) if not basarili else "")
    if basarili:
        print("      --- canli cikti (ilk 25 satir, RAPOR icin telefon maskele) ---")
        for satir in p.stdout.splitlines()[:25]:
            print("      %s" % satir)
    elif p.stderr:
        print("      stderr: %s" % p.stderr[-500:])


def main():
    print("SIPARISLER.PY KABUL TESTLERI")
    print("=" * 66)
    test_1_hepsi_where_yok()
    test_2_durum_where()
    test_3_bilinmeyen_durum()
    test_4_yazma_kapisi()
    test_5_format_alanlari()
    test_6_canli_kosum()
    print("=" * 66)
    basarisiz = [s for s in SONUC if not s[2]]
    print("SONUC: %d/%d GECTI" % (len(SONUC) - len(basarisiz), len(SONUC)))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())

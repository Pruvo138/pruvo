#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLCULMEMIS-SIPARIS.PY KABUL TESTLERI.

    python3 tools/olculmemis-siparis-test.py            # 1-9 sahte veri + 10 kaynak denetimi
    python3 tools/olculmemis-siparis-test.py --canli    # + 11: GERCEK D1 salt-okunur kosum

Testler SAHTE satirlarla calisir (D1'e dokunmaz, subprocess calistirmaz) — sadece
--canli ile 11. madde gercek D1'e SELECT atar (arac zaten salt-okunur).

  1  izli havale siparisi ({"o":1}) KAYIP SAYILMAZ
  2  izsiz havale siparisi (esik SONRASI) KAYIP SAYILIR
  3  esik ONCESI izsiz siparis KAYIP SAYILMAZ (esik-oncesi kovasi)
  4  'havale-bekliyor' / 'iptal' / 'bekliyor' siparisler SORGUYA HIC GIRMEZ
  5  kart siparisi: iyzico_odeme_id dolu -> olculdu ; bos -> kayip
  6  rapor: kayip adedi + TOPLAM KAYIP CIRO dogru; cikis kodu mantigi (1/0)
  7  salt-okunur kapi: SELECT disi ifade / ';' / yazma sozcugu REDDEDILIR
  8  'odendi' gecis ani durum_gecmisi'nden okunur (siparis tarihi degil) -> esik dogru taraf
  9  izli AMA 7 gunden gec onaylanmis havale -> KAYIP degil, 'meta penceresi disi' UYARISI
  10 KAYNAK DENETIMI: olculmemis-siparis.py icinde SELECT disi SQL ifadesi YOK
     (D1'e yazmadiginin kod-duzeyi kaniti)
  11 (--canli) gercek D1 kosumu: cikis kodu 0/1, cikti raporu iceriyor
  12 KART DOGRUDAN IZ: {"o":1} izli kart -> olculdu (iyzico_odeme_id bos olsa bile);
     esik oncesi izsiz kart -> kayip DEGIL; esik sonrasi izsiz kart -> KAYIP;
     12b eski surum kart (izsiz + iyzico_odeme_id dolu) -> kayip DEGIL
"""
import argparse
import json
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import importlib  # noqa: E402
olc = importlib.import_module("olculmemis-siparis")  # noqa: E402

SONUC = []

ESIK_K = "2026-07-18T09:48:34Z"
ESIK_H = "2026-07-20T01:24:38Z"


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("OK  " if gecti else "FAIL", no, ad,
                                    (" | " + detay) if detay else ""), flush=True)


def satir(no, yontem, durum, gecmis, tutar=30000, kargo=25000,
          tarih="2026-07-20T10:00:00.000Z", odeme_id=None, token=None):
    return {
        "siparis_no": no, "tarih": tarih, "durum": durum, "odeme_yontemi": yontem,
        "tutar_kurus": tutar, "kargo_kurus": kargo,
        "durum_gecmisi": json.dumps(gecmis) if gecmis is not None else "",
        "iyzico_odeme_id": odeme_id, "token": token,
    }


# ------------------------------------------------------------------ 1-3, 8, 9

IZLI_HAVALE = satir(
    "PR-260720-120000-AAA", "havale", "odendi",
    [{"d": "odendi", "z": "2026-07-20T12:00:00.000Z", "o": 1}])

IZSIZ_HAVALE = satir(
    "PR-260720-130000-BBB", "havale", "odendi",
    [{"d": "odendi", "z": "2026-07-20T13:00:00.000Z"}], tutar=100000, kargo=0)

# Ham SQL durum_gecmisi'ne HIC dokunmaz -> bos string; gecis ani bilinmez, tarihe dusulur.
HAM_SQL_HAVALE = satir(
    "PR-260720-140000-CCC", "havale", "uretimde", None, tutar=45000,
    tarih="2026-07-20T14:00:00.000Z")

ESKI_HAVALE = satir(
    "PR-260715-090000-DDD", "havale", "tamamlandi",
    [{"d": "odendi", "z": "2026-07-15T09:00:00.000Z"}],
    tarih="2026-07-15T08:00:00.000Z")

# izli ama siparisten 9 GUN sonra onaylanmis -> Meta 7 gun penceresi disi
GEC_ONAY = satir(
    "PR-260711-090000-EEE", "havale", "odendi",
    [{"d": "odendi", "z": "2026-07-20T09:00:00.000Z", "o": 1}],
    tarih="2026-07-11T09:00:00.000Z")


def test_1_izli_kayip_degil():
    k = olc.siniflandir(IZLI_HAVALE, ESIK_K, ESIK_H)
    kayit(1, "izli havale ({\"o\":1}) KAYIP SAYILMAZ",
          k["sinif"] == olc.OLCULDU, k["sinif"])


def test_2_izsiz_kayip():
    k = olc.siniflandir(IZSIZ_HAVALE, ESIK_K, ESIK_H)
    k2 = olc.siniflandir(HAM_SQL_HAVALE, ESIK_K, ESIK_H)
    kayit(2, "izsiz 'odendi' havale (esik sonrasi) KAYIP SAYILIR",
          k["sinif"] == olc.KAYIP and k2["sinif"] == olc.KAYIP,
          "%s / %s (bos gecmis: %s)" % (k["sinif"], k2["sinif"], k2["an_kesin"]))


def test_3_esik_oncesi():
    k = olc.siniflandir(ESKI_HAVALE, ESIK_K, ESIK_H)
    kayit(3, "esik ONCESI izsiz siparis KAYIP SAYILMAZ",
          k["sinif"] == olc.ESIK_ONCESI, k["sinif"])


def test_8_gecis_ani_gecmisten():
    """Siparis esik ONCESI acilmis ama esik SONRASI onaylanmis -> olcum BEKLENIR.
    Tarihe bakan bir arac bunu yanlislikla 'esik oncesi' der; gecmise bakan yakalar."""
    s = satir("PR-260719-000000-FFF", "havale", "odendi",
              [{"d": "odendi", "z": "2026-07-20T09:00:00.000Z"}],
              tarih="2026-07-19T09:00:00.000Z")
    k = olc.siniflandir(s, ESIK_K, ESIK_H)
    an, kesin = olc.odendi_ani(s)
    kayit(8, "'odendi' ani durum_gecmisi'nden okunur (tarih degil)",
          k["sinif"] == olc.KAYIP and kesin and an == "2026-07-20T09:00:00.000Z",
          "%s / an=%s" % (k["sinif"], an))


def test_9_meta_penceresi():
    k = olc.siniflandir(GEC_ONAY, ESIK_K, ESIK_H)
    kayit(9, "izli + 7 gunden gec onay -> KAYIP degil, meta-penceresi UYARISI",
          k["sinif"] == olc.OLCULDU and k["meta_penceresi_disi"] is True,
          "%s / pencere_disi=%s" % (k["sinif"], k["meta_penceresi_disi"]))


# ------------------------------------------------------------------ 4

def test_4_odenmemis_sorguya_girmez():
    sql = olc.sql_sorgu(50)
    girmemeli = ("havale-bekliyor", "iptal", "bekliyor", "basarisiz", "incele")
    # 'bekliyor' alt-dize olarak 'havale-bekliyor' icinde gecmesin diye tirnakli ara.
    kotu = [d for d in girmemeli if ("'%s'" % d) in sql]
    girmeli = all(("'%s'" % d) in sql for d in olc.ODENMIS_DURUMLAR)
    kayit(4, "odenmemis/iptal durumlar SORGUYA girmez, odenmisler girer",
          not kotu and girmeli, ("sizan=%s" % kotu) if kotu else sql)


# ------------------------------------------------------------------ 5

def test_5_kart():
    dolu = satir("PR-260720-150000-GGG", "kart", "odendi", None, odeme_id="12345678",
                 token="tk1")
    bos = satir("PR-260720-160000-HHH", "kart", "odendi", None, odeme_id="", token="tk2")
    a = olc.siniflandir(dolu, ESIK_K, ESIK_H)
    b = olc.siniflandir(bos, ESIK_K, ESIK_H)
    kayit(5, "kart: iyzico_odeme_id dolu->olculdu, bos->kayip",
          a["sinif"] == olc.OLCULDU and b["sinif"] == olc.KAYIP,
          "%s / %s" % (a["sinif"], b["sinif"]))


def test_12_kart_dogrudan_iz():
    """KART yolu artik durum_gecmisi'ne {"o":1} yaziyor (index.js donus()).

    Uc hal AYRI AYRI sinanir — biri digerini maskelemesin:
      12a DOGRUDAN izli kart siparisi KAYIP SAYILMAZ (iyzico_odeme_id BOS OLSA BILE;
          iyzico paymentId'yi bos dondurdugunde dolayli sinyal cokerdi).
      12b Esik ONCESI izsiz eski kart siparisi KAYIP SAYILMAZ (geriye donuk iz YAZILMADI).
      12c Esik SONRASI izsiz + iyzico_odeme_id'siz kart siparisi KAYIP SAYILIR.
    """
    izli = satir("PR-260720-170000-III", "kart", "odendi",
                 [{"d": "odendi", "z": "2026-07-20T17:00:00.000Z", "o": 1}],
                 odeme_id="", token="tk3")
    # Eski (esik oncesi) kart siparisi: dogrudan iz YOK; dolayli sinyal de bos birakildi ki
    # "kayip degil" karari ESIGE dayansin, sinyale degil.
    eski = satir("PR-260717-100000-JJJ", "kart", "tamamlandi",
                 [{"d": "odendi", "z": "2026-07-17T10:00:00.000Z"}],
                 tarih="2026-07-17T09:00:00.000Z", odeme_id="", token="tk4")
    yeni_izsiz = satir("PR-260720-180000-KKK", "kart", "odendi",
                       [{"d": "odendi", "z": "2026-07-20T18:00:00.000Z"}],
                       odeme_id="", token="tk5")
    a = olc.siniflandir(izli, ESIK_K, ESIK_H)
    b = olc.siniflandir(eski, ESIK_K, ESIK_H)
    c = olc.siniflandir(yeni_izsiz, ESIK_K, ESIK_H)
    kayit(12, "kart: dogrudan iz->olculdu, esik oncesi izsiz->esik-oncesi, "
              "esik sonrasi izsiz->kayip",
          a["sinif"] == olc.OLCULDU and b["sinif"] == olc.ESIK_ONCESI
          and c["sinif"] == olc.KAYIP,
          "%s / %s / %s" % (a["sinif"], b["sinif"], c["sinif"]))
    # Eski satirlarda DOLAYLI sinyal hala kabul edilmeli (geriye donuk yazma YAPILMADI).
    dolayli = satir("PR-260719-120000-LLL", "kart", "odendi", None,
                    tarih="2026-07-19T12:00:00.000Z", odeme_id="87654321", token="tk6")
    d = olc.siniflandir(dolayli, ESIK_K, ESIK_H)
    kayit("12b", "esik SONRASI izsiz ama iyzico_odeme_id'li kart (eski surum) KAYIP SAYILMAZ",
          d["sinif"] == olc.OLCULDU, "%s | %s" % (d["sinif"], d["sebep"]))


# ------------------------------------------------------------------ 6

def test_6_rapor_toplam():
    satirlar = [IZLI_HAVALE, IZSIZ_HAVALE, HAM_SQL_HAVALE, ESKI_HAVALE]
    metin, ozet = olc.rapor(satirlar, ESIK_K, ESIK_H)
    beklenen_ciro = 100000 + (45000 + 25000)   # 1.000,00 + 700,00 = 1.700,00 TL
    dogru = (ozet["kayip_adet"] == 2
             and ozet["kayip_ciro_kurus"] == beklenen_ciro
             and ozet["esik_oncesi_adet"] == 1
             and ozet["olculdu_adet"] == 1
             and olc.tl(beklenen_ciro) in metin
             and "PR-260720-130000-BBB" in metin)
    kayit(6, "rapor: kayip adet/ciro dogru + kayip siparis listede",
          dogru, "adet=%d ciro=%s" % (ozet["kayip_adet"], olc.tl(ozet["kayip_ciro_kurus"])))

    # cikis kodu mantigi: kayip varsa 1, yoksa 0
    _, temiz = olc.rapor([IZLI_HAVALE, ESKI_HAVALE], ESIK_K, ESIK_H)
    kayit("6b", "cikis kodu mantigi: kayipli->1, kayipsiz->0",
          (1 if ozet["kayip_adet"] else 0) == 1 and (1 if temiz["kayip_adet"] else 0) == 0)


# ------------------------------------------------------------------ 7 + 10 (yazma kapisi)

def test_7_salt_okunur_kapi():
    """Kapinin UC katmani AYRI AYRI sinanir — biri digerini maskelemesin.

    (Ilk surumde 'zincirleme SQL' testi yalniz "reddedildi mi" diye bakiyordu; ';'
    katmani kapatilinca anahtar-kelime katmani ayni ifadeyi yakaliyor ve test YESIL
    kaliyordu — yani ';' katmaninin once-red kaniti YOKTU. Artik HANGI katmanin
    reddettigi de dogrulaniyor.)
    """
    beklenen = [
        # (sql, ret mesajinda gecmesi gereken parca = hangi katman reddetmeli)
        ("UPDATE siparisler SET durum='odendi'", "sadece SELECT"),
        ("DELETE FROM siparisler", "sadece SELECT"),
        ("INSERT INTO siparisler DEFAULT VALUES", "sadece SELECT"),
        ("PRAGMA writable_schema=1", "sadece SELECT"),
        ("  ATTACH DATABASE 'x' AS y", "sadece SELECT"),
        # zincirleme: SELECT ile BASLAR -> 1. katman gecirir, ';' katmani durdurmali
        ("SELECT 1; DROP TABLE siparisler", "noktali virgul"),
        ("select siparis_no from siparisler; update siparisler set durum='x'",
         "noktali virgul"),
        # SELECT ile baslar, ';' YOK -> yalniz anahtar-kelime katmani durdurabilir
        ("SELECT * FROM siparisler UNION SELECT 1 FROM sqlite_master WHERE 1 "
         "AND (SELECT 1) IN (REPLACE INTO x)", "yazma ifadesi"),
    ]
    hepsi = True
    for sql, parca in beklenen:
        try:
            olc.salt_okunur_dogrula(sql)
            hepsi = False
            print("      beklenmedik: reddetmedi -> %r" % sql)
        except ValueError as e:
            if parca not in str(e):
                hepsi = False
                print("      yanlis katman reddetti (%r beklendi): %s" % (parca, e))
    # gecerli SELECT gecmeli (kapi asiri kilitli olmasin)
    try:
        olc.salt_okunur_dogrula(olc.sql_sorgu(10))
    except ValueError as e:
        hepsi = False
        print("      beklenmedik: gecerli SELECT reddedildi -> %s" % e)
    kayit(7, "salt-okunur kapi: 3 katman AYRI AYRI dogru ifadeyi reddediyor", hepsi)


def test_10_kaynak_denetimi():
    """Araç D1'e YAZMIYOR — kod duzeyi kanit: kaynakta SELECT disi SQL ifadesi yok."""
    yol = os.path.join(TOOLS, "olculmemis-siparis.py")
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()
    # Yalniz STRING sabitlerini tara: yorum/dokumantasyon icinde 'UPDATE' kelimesi
    # gecebilir (kapi anlatiliyor), ama calisan SQL metni string'de olur.
    stringler = re.findall(r'"([^"\n]*)"|\'([^\'\n]*)\'', kaynak)
    duz = [a or b for a, b in stringler]
    supheli = []
    for s in duz:
        u = s.upper()
        if re.search(r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+TABLE|"
                     r"ALTER\s+TABLE|CREATE\s+TABLE|REPLACE\s+INTO)\b", u):
            supheli.append(s)
    # wrangler komutu da salt-okunur olmali: --command disinda --file YOK
    dosya_yolu_yok = "--file" not in kaynak
    kayit(10, "kaynakta calistirilabilir yazma SQL'i YOK + wrangler --file kullanilmiyor",
          not supheli and dosya_yolu_yok,
          ("supheli=%s" % supheli) if supheli else "")


# ------------------------------------------------------------------ 11 (canli)

def test_11_canli():
    p = subprocess.run(
        [sys.executable, os.path.join(TOOLS, "olculmemis-siparis.py"), "--ayrinti"],
        cwd=ROOT, capture_output=True, text=True, timeout=300)
    ok = p.returncode in (0, 1) and "OLCULMEMIS SIPARIS TESPITI" in p.stdout
    kayit(11, "canli D1 kosumu (salt-okunur) exit 0/1 + rapor basligi", ok,
          "exit=%d" % p.returncode)
    print("      --- CANLI CIKTI (RAPOR-MIMARA.md'ye aynen yapistir) ---")
    for s in p.stdout.splitlines():
        print("      %s" % s)
    if p.stderr:
        print("      stderr: %s" % p.stderr[-800:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canli", action="store_true", help="11. madde: gercek D1 kosumu")
    args = ap.parse_args()

    print("OLCULMEMIS-SIPARIS.PY KABUL TESTLERI")
    print("=" * 78)
    test_1_izli_kayip_degil()
    test_2_izsiz_kayip()
    test_3_esik_oncesi()
    test_4_odenmemis_sorguya_girmez()
    test_5_kart()
    test_6_rapor_toplam()
    test_7_salt_okunur_kapi()
    test_8_gecis_ani_gecmisten()
    test_9_meta_penceresi()
    test_10_kaynak_denetimi()
    test_12_kart_dogrudan_iz()
    if args.canli:
        test_11_canli()
    print("=" * 78)
    basarisiz = [s for s in SONUC if not s[2]]
    print("SONUC: %d/%d GECTI" % (len(SONUC) - len(basarisiz), len(SONUC)))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())

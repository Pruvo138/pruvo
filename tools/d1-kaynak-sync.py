#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URETICI KAYNAK LINKI SENKRONU — gizli kayit -> D1 `urun_kaynak` (AYRI tablo).

  python3 tools/d1-kaynak-sync.py --sema     # tabloyu kur (CREATE TABLE IF NOT EXISTS)
  python3 tools/d1-kaynak-sync.py --kuru     # yazmadan plani bas (yalniz SAYI)
  python3 tools/d1-kaynak-sync.py            # gercek senkron (diff-upsert)
  python3 tools/d1-kaynak-sync.py --durum    # YEREL_LINK / D1_SATIR / EKSIK / FAZLA

NE ISE YARAR: yonetim panelinde (shop/src/yonet.js) her kalemin altinda "🔗 Üretici
kaynağı" satiri cikar. Panel Okan'in KORUMALI ekranidir; bu satir orada yasar.

🔴 NEDEN AYRI TABLO (mimar hukmu G1/G2 — tartisma yok):
`urunler` tablosunu **Ege (WhatsApp botu) OKUYOR**. Kaynak linkini oraya koymak, botun
agzindan musteriye tedarikci sizmasi icin bir yol acardi; depo kurali "tedarikci/tasarimci
adi hicbir public yuzeyde olmaz". Bu yuzden veri KENDI tablosunda (`urun_kaynak`) durur ve
o tabloyu YALNIZ yonetim ucu (`/api/shop/yonet/liste`) sorgular. Kapi olculuyor:
`node shop/test/panel-kaynak.mjs` V8 — `urun_kaynak` gecen TEK kaynak dosyasi yonet.js.

🔴 G3 — YALNIZ `link` TASINIR. `tasarimci` · `uyelik` · `lisans` · `alis_fiyati` ve diger
ticari alanlar TASINMAZ: link zaten kaynaga goturur, geri kalani sizma yuzeyini buyutur.

🔴 G4 — GIZLI KAYIT CI'DA YOKTUR. Bu arac yalniz YERELDE kosar. Kayit dosyasi yoksa
FAIL-CLOSED: hicbir sey yazilmaz, tablo SESSIZCE bosaltilmaz, arac "gizli kayit yok" der
ve sifir-disi doner. (Sessizce bos tablo birakmak, panelde "kaynak kaydi yok" yazan 27 bin
satir uretirdi — yani "kaynak YOK" ile "OLCULEMEDI" ayni yere duserdi.)

🔴 GIZLILIK — LOG DISIPLINI: bu arac gizli veri isler. Hicbir cikti satirinda link,
tasarimci, uyelik ya da fiyat BASILMAZ; yalnizca SAYI basilir. Wrangler'in hata metni
bile `gizle()` suzgecinden gecirilir (SQL yuku ekrana dusebilirdi).

ALAN ONCELIGI (uydurma URL URETILMEZ):
  1. `link` DOLU ise o.
  2. degilse `kaynak` alani YALNIZCA "https://" ile basliyorsa o.
  3. ikisi de yoksa kayit ATLANIR.
"""

import argparse
import importlib.util
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAKLAR = os.path.join(KOK, ".urun-kaynaklari.json")
TABLO = "urun_kaynak"

# WRANGLER YOLU TEK KAYNAKTAN: d1-sync.py'nin wrangler sarmalayicisi yeniden kullanilir
# (surum pini, EPERM/npm-cache tuzagi, gecici-hata siniflandirmasi + artan bekleme,
# "supheliyi basari sayma" cikti cozucusu hepsi orada OLCULMUS halde duruyor). Ikinci bir
# govde yazmak [[ikiz-tanim-sessiz-ayrisma]] olurdu: retry mantigi orada duzeltilince
# burada SESSIZCE eski kalirdi. Modul adi tire icerdigi icin importlib gerekir.
_DS_YOL = os.path.join(KOK, "tools", "d1-sync.py")
sys.path.insert(0, os.path.join(KOK, "tools"))
_ds_spec = importlib.util.spec_from_file_location("d1_sync", _DS_YOL)
ds = importlib.util.module_from_spec(_ds_spec)
_ds_spec.loader.exec_module(ds)

# Tek wrangler cagrisina konacak azami ifade sayisi (d1-sync ile ayni buyukluk sinifi).
PARCA = 400
# SILME EMNIYETI: bu orandan/sayidan fazla satir silinecekse arac DURUR ve acik izin ister.
# GEREKCE [[d1-bayat-yazici-silme]]: yarim/bayat bir gizli kayit dosyasiyla kosulan senkron
# canli tabloyu sessizce budayabilir. Kucuk budamalar (normal is akisi) serbest kalir.
SILME_ORAN_TAVANI = 0.05
SILME_SAYI_TABANI = 500

_URL_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.\-]*://\S+")


def gizle(metin):
    """Ciktiya dusecek her metinden URL'leri sok. Log disiplini: SAYI evet, LINK hayir."""
    return _URL_RE.sub("<URL-GIZLENDI>", str(metin or ""))


def guvenli(fn, *a, **kw):
    """d1-sync cagrilarini sar: SystemExit metnindeki URL'ler ekrana DUSMEZ."""
    try:
        return fn(*a, **kw)
    except SystemExit as e:
        sys.exit(gizle(e.code if isinstance(e.code, str) else str(e)))


def link_sec(kayit):
    """Bir gizli kayittan kaynak linkini sec. Bulunamazsa None (kayit ATLANIR).

    UYDURMA URL URETILMEZ: `kaynak` alani cogunlukla PLATFORM ADIDIR (adres degil), bu
    yuzden yalniz "https://" ile basliyorsa link sayilir.
    """
    if not isinstance(kayit, dict):
        return None
    link = kayit.get("link")
    if isinstance(link, str) and link.strip().startswith("https://"):
        return link.strip()
    if isinstance(link, str) and link.strip():
        # DOLU ama https disi (http/bagil/bozuk): panel suzgeci zaten reddederdi ->
        # tabloya YAZMA (yoksa "kaynak var" sanilir, panel "kaynak kaydi yok" der).
        return None
    kaynak = kayit.get("kaynak")
    if isinstance(kaynak, str) and kaynak.strip().startswith("https://"):
        return kaynak.strip()
    return None


def yerel_linkler():
    """Gizli kayittan {id: link}. Dosya yoksa FAIL-CLOSED (G4)."""
    if not os.path.exists(KAYNAKLAR):
        sys.exit(
            "🔴 GIZLI KAYIT YOK (.urun-kaynaklari.json) — FAIL-CLOSED.\n"
            "   Bu arac YALNIZ yerelde kosar; CI'da/temiz makinede gizli kayit BULUNMAZ.\n"
            "   Hicbir sey yazilmadi, tablo BOSALTILMADI (sessiz bos tablo = sahte 'kaynak yok')."
        )
    with open(KAYNAKLAR, encoding="utf-8") as f:
        ham = json.load(f)
    if isinstance(ham, dict):
        ciftler = ham.items()
    elif isinstance(ham, list):
        ciftler = [(k.get("id"), k) for k in ham if isinstance(k, dict)]
    else:
        sys.exit("🔴 GIZLI KAYIT BICIMI TANINMADI (dict/list bekleniyordu) — FAIL-CLOSED.")
    cikti = {}
    for urun_id, kayit in ciftler:
        if not isinstance(urun_id, str) or not urun_id.strip():
            continue
        link = link_sec(kayit)
        if link:
            cikti[urun_id.strip()] = link
    if not cikti:
        sys.exit("🔴 GIZLI KAYITTA TEK BIR LINK BILE YOK — FAIL-CLOSED (tablo bosaltilmadi).")
    return cikti


def tablo_var_mi():
    r = guvenli(ds.sorgu,
                "SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % TABLO)
    for blok in r:
        if blok.get("results"):
            return True
    return False


def d1_linkler():
    """D1'deki {id: link}. Tablo yoksa BOS sozluk (kurulmamis = 0 satir)."""
    if not tablo_var_mi():
        return {}
    r = guvenli(ds.sorgu, "SELECT id, link FROM %s" % TABLO)
    cikti = {}
    for blok in r:
        for satir in (blok.get("results") or []):
            urun_id = satir.get("id")
            if isinstance(urun_id, str):
                cikti[urun_id] = satir.get("link") or ""
    return cikti


def plan(yerel, d1):
    """(eklenecek, degisen, silinecek) — id listeleri. SAF (D1'e dokunmaz)."""
    eklenecek = sorted(k for k in yerel if k not in d1)
    degisen = sorted(k for k in yerel if k in d1 and d1[k] != yerel[k])
    silinecek = sorted(k for k in d1 if k not in yerel)
    return eklenecek, degisen, silinecek


def sema_kur():
    sql = (
        "CREATE TABLE IF NOT EXISTS %s (\n"
        "  id   TEXT PRIMARY KEY,\n"
        "  link TEXT NOT NULL\n"
        ");" % TABLO
    )
    guvenli(ds.sorgu, sql)
    # KURULUM IDDIASINI GERI-OKUMAYLA KANITA CEVIR (d1-sync --sema deseni).
    if not tablo_var_mi():
        sys.exit("🔴 SEMA: CREATE kostu ama tablo geri-okumada YOK — OLCULEMEDI.")
    print("SEMA: %s tablosu VAR (geri-okumayla teyit edildi)." % TABLO)
    return 0


def satirlari_yaz(yerel, idler):
    """Verilen id'leri parcalar halinde upsert et. Doner: yazilan satir sayisi (wrangler iddiasi)."""
    toplam = 0
    for bas in range(0, len(idler), PARCA):
        dilim = idler[bas:bas + PARCA]
        ifadeler = []
        for k in dilim:
            ifadeler.append(
                "INSERT INTO %s (id, link) VALUES (%s, %s) "
                "ON CONFLICT(id) DO UPDATE SET link=excluded.link;"
                % (TABLO, ds.q(k), ds.q(yerel[k]))
            )
        yaz, _ = guvenli(ds.dosya_calistir, "\n".join(ifadeler))
        toplam += yaz
    return toplam


def satirlari_sil(idler):
    toplam = 0
    for bas in range(0, len(idler), PARCA):
        dilim = idler[bas:bas + PARCA]
        sql = "DELETE FROM %s WHERE id IN (%s);" % (TABLO, ", ".join(ds.q(k) for k in dilim))
        yaz, _ = guvenli(ds.dosya_calistir, sql)
        toplam += yaz
    return toplam


def durum():
    yerel = yerel_linkler()
    d1 = d1_linkler()
    eklenecek, degisen, silinecek = plan(yerel, d1)
    print("YEREL_LINK=%d" % len(yerel))
    print("D1_SATIR=%d" % len(d1))
    print("EKSIK=%d" % (len(eklenecek) + len(degisen)))
    print("FAZLA=%d" % len(silinecek))
    print("  ayrinti: D1'DE_YOK=%d BAYAT=%d" % (len(eklenecek), len(degisen)))
    # HUKUM: EKSIK ve FAZLA sifirsa senkron TAMDIR.
    print("HUKUM=%s" % ("SENKRON" if not (eklenecek or degisen or silinecek) else "SAPMA"))
    return 0 if not (eklenecek or degisen or silinecek) else 1


def senkron(kuru, silmeye_izin):
    yerel = yerel_linkler()
    d1 = d1_linkler()
    eklenecek, degisen, silinecek = plan(yerel, d1)
    print("PLAN: yerel_link=%d d1_satir=%d ekle=%d guncelle=%d sil=%d"
          % (len(yerel), len(d1), len(eklenecek), len(degisen), len(silinecek)))
    if kuru:
        print("KURU KOSUM — hicbir sey yazilmadi.")
        return 0

    if not tablo_var_mi():
        sys.exit("🔴 TABLO YOK — once `python3 tools/d1-kaynak-sync.py --sema` kos.")

    # SILME EMNIYETI (bkz. SILME_ORAN_TAVANI gerekcesi).
    tavan = max(SILME_SAYI_TABANI, int(len(d1) * SILME_ORAN_TAVANI))
    if silinecek and len(silinecek) > tavan and not silmeye_izin:
        sys.exit(
            "🔴 SILME EMNIYETI: %d satir silinecekti (tavan %d) — DURDU.\n"
            "   Gizli kayit YARIM/BAYAT olabilir. Once `--durum` ile bak; gercekten "
            "isteniyorsa `--silmeye-izin` ile tekrar kos." % (len(silinecek), tavan)
        )

    yazilacak = eklenecek + degisen
    yazildi = satirlari_yaz(yerel, yazilacak) if yazilacak else 0
    silindi = satirlari_sil(silinecek) if silinecek else 0
    print("YAZILDI=%d (ifade=%d) SILINDI=%d" % (yazildi, len(yazilacak), silindi))

    # GERI-OKUMA: iddia degil OLCUM. Senkron sonrasi sapma SIFIR olmali.
    d1_son = d1_linkler()
    e2, d2, s2 = plan(yerel, d1_son)
    print("TEYIT: D1_SATIR=%d EKSIK=%d FAZLA=%d" % (len(d1_son), len(e2) + len(d2), len(s2)))
    if e2 or d2 or s2:
        sys.exit("🔴 SENKRON SONRASI SAPMA VAR — fail-loud.")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Uretici kaynak linki senkronu (gizli kayit -> D1 urun_kaynak).")
    ap.add_argument("--sema", action="store_true", help="tabloyu kur (IF NOT EXISTS)")
    ap.add_argument("--durum", action="store_true", help="YEREL_LINK/D1_SATIR/EKSIK/FAZLA")
    ap.add_argument("--kuru", action="store_true", help="yazmadan plani bas")
    ap.add_argument("--silmeye-izin", action="store_true",
                    help="buyuk silme planini onayla (emniyet tavani asildiginda)")
    a = ap.parse_args()
    if a.sema:
        return sema_kur()
    if a.durum:
        return durum()
    return senkron(a.kuru, a.silmeye_izin)


if __name__ == "__main__":
    sys.exit(main())

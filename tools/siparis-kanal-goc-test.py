#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIPARIS KANAL GOCU — GERIYE UYUM KABUL TESTI (1 Agu 2026, WhatsApp siparis ucu).

    python3 tools/siparis-kanal-goc-test.py

*** NEDEN VAR ***
`siparisler` tablosuna IKI kolon eklendi: `kanal` (site|whatsapp) ve `dis_no` (Ege'nin
kendi numarasi). D1 semasina dokunmak bu depodaki EN HASSAS eksendir: canlida ~yuzlerce
odenmis siparis satiri var, tablo PARA yolundadir ve goc GERI ALINAMAZ. "Additive oldugu
icin guvenlidir" bir IDDIADIR — bu test onu SQLite uzerinde FIILEN kosarak olcer.

*** OLCULEN IDDIALAR ***
  A. d1-sema.sql'deki CREATE TABLE iki kolonu DOGRU varsayilanlarla tasiyor.
  B. tools/d1-sync.py GOC_KOLON_SIPARIS ile d1-sema.sql AYRISMAMIS (iki kaynak tek gercek).
  C. GOC ESKI VERIYI BOZMAZ: goc ONCESI yazilmis satirlar ALTER'dan sonra
     kanal='site', dis_no='' alir -> geriye doldurma GEREKMEZ, hicbir satir NULL olmaz.
  D. ESKI OKUMA YOLU CALISMAYA DEVAM EDER: worker'in goc oncesi SELECT'i (kanal/dis_no
     ICERMEYEN kolon listesi) ayni satirlari aynen dondurur.
  E. WORKER YAZMASI SEMAYA UYAR: shop/src/*.js icindeki HER `INSERT INTO siparisler`
     kolon listesi goc SONRASI semanin ALT KUMESIDIR (drift kapisi: worker olmayan bir
     kolona yazarsa CI'da kirmizi yanar, canlida 500 ile degil).
  F. DIS NUMARA TEKILLIGI: kismi UNIQUE indeks ayni (kanal, dis_no) ciftini REDDEDER ama
     dis_no='' olan (site) satirlarin SAYISIZ olmasina izin verir.
  G. GOC IDEMPOTENT: ikinci kosumda eklenecek kolon kalmaz (kor ALTER patlardi).

*** KAPSAM ***
Ag YOK, wrangler YOK, canli D1 YOK — stdlib sqlite3 uzerinde bellek ici bir kopya. D1
SQLite tabanlidir; ALTER TABLE ADD COLUMN / kismi indeks semantigi burada gecerlidir.
"""
import os
import re
import sqlite3
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
SYNC = os.path.join(KOK, "tools", "d1-sync.py")
SHOP_SRC = os.path.join(KOK, "shop", "src")

YENI_KOLONLAR = ["kanal", "dis_no"]

gecen = 0
kalan = []


def ol(ad, kosul, detay=""):
    global gecen
    if kosul:
        gecen += 1
        print("  OK  %s" % ad)
    else:
        kalan.append(ad)
        print("  RED %s%s" % (ad, (" — " + str(detay)) if detay else ""))


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def sql_yorumsuz(s):
    return "\n".join(re.sub(r"--.*$", "", satir) for satir in s.split("\n"))


def create_table_bloklari(metin, tablo):
    """CREATE TABLE ... <tablo> ( ... ); blogunu dondurur (yorumlar dahil)."""
    m = re.search(r"CREATE TABLE IF NOT EXISTS %s\s*\((.*?)\n\);" % tablo, metin, re.S)
    return m.group(1) if m else ""


def kolon_tanimlari(blok):
    """CREATE TABLE govdesinden [(ad, tam_tanim)] listesi (yorum satirlari atilir)."""
    govde = sql_yorumsuz(blok)
    ciktilar = []
    for parca in re.split(r",\s*\n", govde):
        p = parca.strip()
        if not p or p.upper().startswith(("PRIMARY", "UNIQUE", "CHECK", "FOREIGN")):
            continue
        ad = p.split()[0]
        ciktilar.append((ad, " ".join(p.split())))
    return ciktilar


def goc_kolon_siparis():
    """tools/d1-sync.py GOC_KOLON_SIPARIS listesi -> [(ad, tip_tanimi)]."""
    metin = oku(SYNC)
    m = re.search(r"GOC_KOLON_SIPARIS = \[(.*?)\n\]", metin, re.S)
    if not m:
        return []
    return re.findall(r'\("([a-z_]+)",\s*"([^"]+)"\)', m.group(1))


def siparis_indeks():
    metin = oku(SYNC)
    m = re.search(r"SIPARIS_INDEKS = \[(.*?)\n\]", metin, re.S)
    if not m:
        return []
    # Python'daki bitisik dize sabitlerini birlestir.
    parcalar = re.findall(r'"([^"]*)"', m.group(1))
    return ["".join(parcalar)] if parcalar else []


def worker_insert_kolonlari():
    """shop/src/*.js icindeki her `INSERT INTO siparisler (...)` icin kolon listesi."""
    sonuc = []
    for ad in sorted(os.listdir(SHOP_SRC)):
        if not ad.endswith(".js"):
            continue
        metin = oku(os.path.join(SHOP_SRC, ad))
        # JS'te SQL cok satirli dize birlestirmesiyle yazilir: `"..." +\n  "..."`.
        duz = re.sub(r'"\s*\+\s*\n?\s*"', "", metin)
        for m in re.finditer(r"INSERT INTO siparisler\s*\(([^)]*)\)", duz):
            kolonlar = [k.strip() for k in m.group(1).split(",") if k.strip()]
            sonuc.append((ad, kolonlar))
    return sonuc


# ---------------------------------------------------------------- A + B

print("A. d1-sema.sql — yeni kolonlar ve varsayilanlari")
blok = create_table_bloklari(oku(SEMA), "siparisler")
ol("CREATE TABLE siparisler blogu bulundu", bool(blok))
tanimlar = dict(kolon_tanimlari(blok))
ol("kanal kolonu var", "kanal" in tanimlar)
ol("kanal DEFAULT 'site' (eski satirlar dogru degeri alir)",
   "DEFAULT 'site'" in tanimlar.get("kanal", ""), tanimlar.get("kanal"))
ol("kanal NOT NULL", "NOT NULL" in tanimlar.get("kanal", ""))
ol("dis_no kolonu var", "dis_no" in tanimlar)
ol("dis_no DEFAULT '' ", "DEFAULT ''" in tanimlar.get("dis_no", ""), tanimlar.get("dis_no"))

print("\nB. d1-sync.py goc listesi ile sema AYRISMAMIS")
goc = dict(goc_kolon_siparis())
for ad in YENI_KOLONLAR:
    ol("GOC_KOLON_SIPARIS'te %s var (yoksa canliya HIC eklenmez)" % ad, ad in goc)
ol("goc tipi sema ile ayni (kanal)", goc.get("kanal") == "TEXT NOT NULL DEFAULT 'site'",
   goc.get("kanal"))
ol("goc tipi sema ile ayni (dis_no)", goc.get("dis_no") == "TEXT NOT NULL DEFAULT ''",
   goc.get("dis_no"))
indeksler = siparis_indeks()
ol("SIPARIS_INDEKS kismi UNIQUE indeks tanimliyor",
   any("UNIQUE INDEX" in i and "WHERE dis_no <> ''" in i for i in indeksler), indeksler)

# ---------------------------------------------------------------- C + D + E + F + G

print("\nC/D. GOC ESKI VERIYI BOZMUYOR + eski okuma yolu ayakta")
# "Canlidaki bugunku sema" = d1-sema.sql'in YENI kolonlar CIKARILMIS hali.
eski_kolonlar = [t for ad, t in kolon_tanimlari(blok) if ad not in YENI_KOLONLAR]
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE siparisler (\n  %s\n)" % ",\n  ".join(eski_kolonlar))
db.execute(
    "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus,"
    " kdv_kurus, odeme_yontemi, urunler, musteri_ad, musteri_tel, musteri_eposta,"
    " musteri_adres) VALUES ('PR-260731-101010-XYZ', 'tok-1', '2026-07-31T10:10:10Z',"
    " 'odendi', 50000, 25000, 12500, 'kart', '[]', 'A', '0', 'a@b.c', 'Adres')")
db.execute(
    "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus,"
    " kdv_kurus, odeme_yontemi, urunler, musteri_ad, musteri_tel, musteri_eposta,"
    " musteri_adres) VALUES ('PR-260731-101011-ABC', NULL, '2026-07-31T10:10:11Z',"
    " 'havale-bekliyor', 90000, 0, 15000, 'havale', '[]', 'B', '0', '', 'Adres 2')")
db.commit()
eski_sayim = db.execute("SELECT COUNT(*) FROM siparisler").fetchone()[0]

# --- kolon_goc()'un yaptigi is: eksik kolonlar icin ALTER, sonra indeks.
def goc_uygula(baglanti):
    var = {s[1] for s in baglanti.execute("PRAGMA table_info(siparisler)")}
    eksik = [(ad, tip) for ad, tip in goc_kolon_siparis() if ad not in var]
    for ad, tip in eksik:
        baglanti.execute("ALTER TABLE siparisler ADD COLUMN %s %s" % (ad, tip))
    for sql in siparis_indeks():
        baglanti.execute(sql.rstrip(";"))
    baglanti.commit()
    return [ad for ad, _ in eksik]


eklenen = goc_uygula(db)
ol("goc iki yeni kolonu ekledi", set(YENI_KOLONLAR) <= set(eklenen), eklenen)
ol("satir sayisi DEGISMEDI (veri kaybi yok)",
   db.execute("SELECT COUNT(*) FROM siparisler").fetchone()[0] == eski_sayim)
satirlar = db.execute("SELECT siparis_no, kanal, dis_no FROM siparisler ORDER BY id").fetchall()
ol("eski satirlarin HEPSI kanal='site' aldi", all(s[1] == "site" for s in satirlar), satirlar)
ol("eski satirlarin HEPSI dis_no='' aldi", all(s[2] == "" for s in satirlar), satirlar)
ol("hicbir eski satirda NULL yok", all(s[1] is not None and s[2] is not None for s in satirlar))

# Worker'in goc ONCESI (bugunku main) liste SELECT'i — kolon listesi birebir.
eski_secim = ("SELECT id, siparis_no, tarih, durum, tutar_kurus, kargo_kurus, kdv_kurus,"
              " odeme_yontemi, urunler, kargo_firma, kargo_kodu, durum_gecmisi,"
              " musteri_ad, musteri_tel, musteri_eposta, musteri_adres FROM siparisler"
              " ORDER BY id DESC LIMIT 50")
ol("goc SONRASI eski SELECT hala calisiyor (panel render'i bozulmaz)",
   len(db.execute(eski_secim).fetchall()) == eski_sayim)

print("\nE. Worker INSERT'leri semanin ALT KUMESI (yazma drift kapisi)")
sema_kolonlari = {s[1] for s in db.execute("PRAGMA table_info(siparisler)")}
insertler = worker_insert_kolonlari()
ol("shop/src icinde INSERT INTO siparisler bulundu", len(insertler) >= 3,
   [(a, len(k)) for a, k in insertler])
for dosya, kolonlar in insertler:
    fazla = [k for k in kolonlar if k not in sema_kolonlari]
    ol("%s INSERT kolonlari semada var (%d kolon)" % (dosya, len(kolonlar)), not fazla, fazla)
wa = [k for a, k in insertler if "kanal" in k]
ol("WhatsApp INSERT'i kanal + dis_no yaziyor",
   bool(wa) and "dis_no" in wa[0], wa)

print("\nF. Dis numara tekilligi (kismi UNIQUE indeks)")


def wa_yaz(no, dis_no):
    db.execute(
        "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus,"
        " kdv_kurus, odeme_yontemi, urunler, musteri_ad, musteri_tel, musteri_eposta,"
        " musteri_adres, kanal, dis_no) VALUES (?, NULL, '2026-08-01T11:02:00Z',"
        " 'havale-bekliyor', 0, 0, 0, 'havale', '[]', 'C', '0', '', 'Adres', 'whatsapp', ?)",
        (no, dis_no))
    db.commit()


wa_yaz("PR-260801-110200-AAA", "PR-260801-110139")
ol("WhatsApp siparisi yazildi",
   db.execute("SELECT COUNT(*) FROM siparisler WHERE kanal='whatsapp'").fetchone()[0] == 1)
ikiz = False
try:
    wa_yaz("PR-260801-110300-BBB", "PR-260801-110139")
except sqlite3.IntegrityError:
    ikiz = True
ol("ayni dis_no IKINCI kez yazilamaz (ikiz siparis engellendi)", ikiz)
bos_ikinci = True
try:
    db.execute(
        "INSERT INTO siparisler (siparis_no, token, tarih, durum, tutar_kurus, kargo_kurus,"
        " kdv_kurus, odeme_yontemi, urunler, musteri_ad, musteri_tel, musteri_eposta,"
        " musteri_adres) VALUES ('PR-260801-110400-CCC', NULL, '2026-08-01T11:04:00Z',"
        " 'bekliyor', 0, 0, 0, 'kart', '[]', 'D', '0', '', 'Adres')")
    db.commit()
except sqlite3.IntegrityError:
    bos_ikinci = False
ol("dis_no='' olan SITE siparisleri indeksten ETKILENMEZ (coklu bos kayit serbest)",
   bos_ikinci)

print("\nG. Goc idempotent (ikinci kosum)")
ikinci = goc_uygula(db)
ol("ikinci kosumda eklenecek kolon YOK", ikinci == [], ikinci)

print("\n%s — gecen: %d, kalan: %d" %
      ("HEPSI GECTI" if not kalan else "KIRMIZI", gecen, len(kalan)))
if kalan:
    for ad in kalan:
        print("  - %s" % ad)
sys.exit(1 if kalan else 0)

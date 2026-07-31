#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ARA MALIYET KAPISI — /ara'nin D1 sorgusu BIRLESIM SIRASI CEVRILIP tam taramaya dusuyor mu?

NEDEN VAR (olculmus canli olay, 31 Tem — MUSTERI 500 GORDU):
  Canli /ara ucu D1 CPU tavanini asip `D1_ERROR: D1 DB exceeded its CPU time limit and was
  reset` donduruyordu. Sirali prob: 30 istekten 5'i basarisiz (%16,7). Sinif bazinda:
  1-2 token'li sorgu %0, 3+ token'li sorgu %45,8, 10 token'li uzun sorgu %100.

  KOK NEDEN — SESSIZ BIR PLAN CEVRILMESI (indeks eksikligi DEGIL):
    araD1() sorgusu `urunler_fts f JOIN urunler u ON u.rid = f.rowid` uzerine her token
    icin bir `f.hs LIKE '%token%'` kosulu koyar. Token sayisi 1-2 iken SQLite planı
    FTS'ten surer:
        SCAN f VIRTUAL TABLE INDEX 0:L0L0     <- trigram indeksi calisiyor, UCUZ
    3 VE UZERI token'da maliyet tahmini degisir ve planlayici birlesim SIRASINI CEVIRIR:
        SEARCH u USING INDEX urunler_yayin (yayinda=?)
        SCAN f VIRTUAL TABLE INDEX 0:=L0L0L0  <- artik u DIS dongude
    Bu halde YAYINDAKI HER URUN icin ayri bir FTS aramasi yapilir -> tam tarama.
    Canli D1'de olculdu ('Volvo S60 far braketi'): rows_read=16.121, satir sorgusu
    6.810 ms + sayim sorgusu 6.465 ms = 13.275 ms TEK batch'te -> CPU tavani asilir.

  CEVRILMEYI MUMKUN KILAN SEY `urunler_yayin` INDEKSIDIR (atomik yayinla 31 Tem geldi:
  d1-sync.py YAYIN_INDEKS + araD1'e `u.yayinda = 1`). Indeks olmadan planlayicinin `u`'yu
  dis donguye alacak ucuz bir yolu YOKTU. Yani iki dogru degisiklik BIRLESINCE sessiz bir
  performans regresyonu dogurdu — ikisi de tek basina zararsizdi. Bu, kapinin ASIL dersi:
  regresyon SORGU METNINDE degil, PLANDA yasiyor.

  ONARIM: `JOIN` -> `CROSS JOIN`. SQLite'ta CROSS JOIN sonuc kumesini DEGISTIRMEZ, yalnizca
  planlayicinin birlesim sirasini yeniden duzenlemesini KAPATIR (f daima dis dongu). Ayni
  canli olcum onarimla: 13.275 ms -> 3,6 ms, rows_read 16.121 -> 9, DONEN SATIRLAR AYNI.

BU KAPI NE OLCER (iki eksen, ikisi de calistirilabilir):
  E1 SEMANTIK  — eski sekil ile yeni sekil, sorgu korpusunun TAMAMINDA birebir ayni id
                 listesini VE ayni `toplam`i donduruyor mu? Sapma = KIRMIZI. (Arama
                 semantigi degismeyecek sarti burada kanitlanir; parite-test.js canli uca
                 bakar, bu kapi SQL SEKLINE bakar — ikisi farkli eksendir.)
  E2 PLAN      — yeni sekilde plan `u`'yu dis donguye ALMIYOR mu (cevrilme yok) ve maliyet
                 butcenin altinda mi? Cevrilme = KIRMIZI, tek bir sorguda bile.

NICIN YEREL IKIZ: kapi agsiz ve deterministik olmali (CI'da kosabilsin, canli D1'in
oynakligina bagimli olmasin). Ikiz, tools/d1-sema.sql ile AYNI semayi ve hs kolonunu
tools/arama.py haystack() ile — yani D1'e yazan kodun TA KENDISI ile — uretir.

CIKIS KODLARI:
  0 GECTI      — semantik birebir + hicbir sorguda plan cevrilmesi yok.
  1 SAPMA      — semantik ayrisma YA DA plan cevrilmesi (gercek bulgu).
  2 OLCULEMEDI — ikiz kurulamadi (urunler.json okunamadi, FTS5 trigram yok vb.).

KULLANIM:
    python3 tools/ara-maliyet-kapisi.py               # ~600 sorgu
    python3 tools/ara-maliyet-kapisi.py --adet 2000   # daha genis korpus
    python3 tools/ara-maliyet-kapisi.py --tut         # ikizi silme (tekrar kosum hizli)
"""
import argparse
import json
import os
import random
import sqlite3
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

try:
    import arama
except Exception as e:  # pragma: no cover
    print("OLCULEMEDI: tools/arama.py alinamadi: %s" % e)
    sys.exit(2)

# araD1()'in SELECT listesi (worker/src/index.js KART_ALANLARI) — id yeterli olurdu ama
# gercek sorgunun sekli korunsun ki plan da gercekci olsun.
KART = ("u.id, u.baslik, u.kategori, u.marka, u.fiyat, u.taban_fiyat, u.gorsel,"
        " u.parametrik, substr(u.aciklama, 1, 160) AS aciklama")

SEMA = """
CREATE TABLE urunler (
  rid INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE, seq INTEGER NOT NULL,
  baslik TEXT NOT NULL, kategori TEXT NOT NULL, marka TEXT NOT NULL DEFAULT '[]',
  fiyat TEXT NOT NULL DEFAULT '', gorsel TEXT, parametrik INTEGER NOT NULL DEFAULT 0,
  taban_fiyat INTEGER NOT NULL DEFAULT 0, hs TEXT NOT NULL,
  aciklama TEXT NOT NULL DEFAULT '', yayinda INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX urunler_seq ON urunler(seq DESC);
CREATE INDEX urunler_kat ON urunler(kategori, seq DESC);
CREATE INDEX urunler_yayin ON urunler(yayinda, seq DESC);
CREATE INDEX urunler_yayin_kat ON urunler(yayinda, kategori, seq DESC);
CREATE VIRTUAL TABLE urunler_fts USING fts5(
  hs, content='urunler', content_rowid='rid', tokenize='trigram');
"""

# Plan satirinda bu gorunuyorsa birlesim sirasi CEVRILMISTIR: `u` dis dongude, FTS ic
# dongude rowid ile aranıyor -> yayindaki her urun icin bir FTS aramasi = tam tarama.
CEVRILME_IZI = "SEARCH u USING INDEX urunler_yayin"

# Tek sorgunun (satir + sayim) yerel ikizde harcayabilecegi azami VDBE adimi.
# KATALOG BOYUYLA OLCEKLENIR — sabit tavan katalog buyudukce SAHTE KIRMIZI verirdi:
# saglikli en kotu hal (tek 2 harfli token, or. "ic") trigram indeksini kullanamaz ve
# tam FTS taramasi yapar; maliyeti urun sayisiyla DOGRUSAL buyur (15.955 uründe VDBE~655k,
# yani urun basina ~41 adim). 250 = o dogrusal katsayinin ~6 kati.
# AYRISMA PAYI (kapinin isini yapabilmesi icin sart): cevrilmis plan AYNI katalogda
# 20-86 MILYON adim harciyor = butcenin 5-21 KATI. Yani saglikli tarafta %16'da geziyoruz,
# arizali tarafta butceyi 5 kattan fazla asiyoruz — arada 30 kata yakin bosluk var.
ADIM_BUTCESI_KATSAYI = 250
ADIM_BUTCESI_TABAN = 1_000_000
ADIM_BIRIMI = 1000


def ikiz_kur(yol, urunler):
    c = sqlite3.connect(yol)
    c.executescript(SEMA)
    n = len(urunler)
    satirlar = []
    for i, u in enumerate(urunler):
        seq = n - i          # yeni urun urunler.json'un BASINDA -> en buyuk seq
        satirlar.append((seq, u.get("id") or "", seq, u.get("baslik") or "",
                         u.get("kategori") or "",
                         json.dumps(u.get("marka") or [], ensure_ascii=False),
                         u.get("fiyat") or "", (u.get("gorseller") or [None])[0],
                         1 if u.get("parametrik") else 0, arama.haystack(u),
                         (u.get("aciklama") or "")[:400], 1))
    c.executemany(
        "INSERT INTO urunler (rid, id, seq, baslik, kategori, marka, fiyat, gorsel,"
        " parametrik, hs, aciklama, yayinda) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", satirlar)
    c.execute("INSERT INTO urunler_fts(urunler_fts) VALUES ('rebuild')")
    c.commit()
    return c


def sql_kur(tokenlar, limit, cross):
    """araD1()'in urettigi SQL — `cross` disinda BIREBIR ayni sekil."""
    birlesim = ("urunler_fts f CROSS JOIN urunler u ON u.rid = f.rowid" if cross
                else "urunler_fts f JOIN urunler u ON u.rid = f.rowid")
    kaynak = birlesim if tokenlar else "urunler u"
    kosul, bag = [], []
    for t in tokenlar:
        kosul.append("f.hs LIKE ?")
        bag.append("%" + t + "%")
    kosul.append("u.yayinda = 1")
    nere = " WHERE " + " AND ".join(kosul)
    return (("SELECT " + KART + " FROM " + kaynak + nere +
             " ORDER BY u.seq DESC LIMIT ?", bag + [limit]),
            ("SELECT COUNT(*) AS n FROM " + kaynak + nere, list(bag)))


def kos(c, sql, bag, adim_say=False):
    sayac = [0]
    if adim_say:
        def ilerle():
            sayac[0] += 1
            return 0
        c.set_progress_handler(ilerle, ADIM_BIRIMI)
    try:
        satir = c.execute(sql, bag).fetchall()
    finally:
        if adim_say:
            c.set_progress_handler(None, ADIM_BIRIMI)
    return satir, sayac[0] * ADIM_BIRIMI


def korpus(urunler, adet, tohum=20260731):
    """Sorgu korpusu — GERCEK katalog metninden turetilir (uydurma kelime degil).

    Token SAYISI bilerek 1..10 arasinda dagitilir: olay tam da token sayisina bagli
    (1-2 token saglikli, 3+ cevrilmis), yani kapinin korpusu o ekseni ORNEKLEMELI.
    """
    rast = random.Random(tohum)
    kelimeler = []
    for u in urunler:
        for w in arama.norm(u.get("baslik") or "").split():
            if len(w) >= 2:
                kelimeler.append(w)
    sorgular = [
        # Olayda CANLI 500 uretmis, isim isim tekrarlanabilir tetikleyiciler.
        "tekne", "Grandland X havalandırma", "Volvo S60 far braketi",
        "2016 passat b8 arka kapı iç açma kolu sağ taraf",
        "tekne güverte için paslanmaz olmayan halat tutucu braket",
        "göcek", "kapı kolu", "b8 x s6", "a4 x", "3d",
        "kapak kapak kapak kapak",
        "araba icin ozel uretim dayanikli plastik parca kapak",
        # Joker: LIKE'in % / _ karakterleri SITE'de DUZ HARF (araD1 instr ile bunu korur).
        "%kapak", "kapak_", "50%",
    ]
    if not kelimeler:
        return sorgular
    while len(sorgular) < adet:
        n = rast.choice([1, 1, 2, 2, 3, 3, 4, 5, 6, 8, 10])
        sorgular.append(" ".join(rast.choice(kelimeler) for _ in range(n)))
    return sorgular[:max(adet, len(sorgular))]


def kendini_test(c, limit):
    """KAPI GERCEKTEN KONUSUYOR MU? — onarim GERI ALINSA kirmizi yanar mi?

    Nobetci fikstur ilkesi: yesil yanan bir kapi, KIRMIZI yanabildigi kanitlanmadikca
    hicbir sey soylemez. Burada mutasyon gercek: `CROSS JOIN` -> `JOIN` (yani 31 Tem'de
    canlida 500 dondurmus SEKLIN TA KENDISI) ayni ikizde ayni sorgularla kosulur ve
    kapinin PLAN ekseninin onu YAKALAMASI beklenir.

    Bu sorgular BILEREK olaydaki 3+ token'li siniftan secilir — 1-2 token'li sorgu eski
    sekilde de saglikliydi, onunla yapilan bir "mutasyon testi" YESIL yanar ve kapinin
    kor oldugunu gizlerdi.
    """
    mutant_sorgular = [
        "Volvo S60 far braketi",
        "Grandland X havalandırma",
        "2016 passat b8 arka kapı iç açma kolu sağ taraf",
    ]
    yakalanan, kacan = [], []
    for q in mutant_sorgular:
        tk = arama.tokenlar(q)
        (eski_s, eski_b), _ = sql_kur(tk, limit, False)   # MUTASYON: CROSS kaldirildi
        plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + eski_s, eski_b)]
        if any(CEVRILME_IZI in p for p in plan):
            yakalanan.append((q, plan))
        else:
            kacan.append((q, plan))

    print("=== KENDINI TEST: mutasyon = `CROSS JOIN` -> `JOIN` (olayin sekli) ===")
    for q, plan in yakalanan:
        print("  YAKALANDI  %r" % q)
        for p in plan:
            print("      " + p)
    for q, plan in kacan:
        print("  🔴 KACTI    %r" % q)
        for p in plan:
            print("      " + p)
    if kacan:
        print("\n🔴 KAPI KOR: mutasyon %d/%d sorguda YAKALANMADI. Bu kapinin yesili"
              " HICBIR SEY KANITLAMAZ." % (len(kacan), len(mutant_sorgular)))
        return 1
    print("\n%d/%d mutant sorgu yakalandi -> kapinin PLAN ekseni CALISIYOR."
          % (len(yakalanan), len(mutant_sorgular)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adet", type=int, default=600)
    ap.add_argument("--limit", type=int, default=24)
    ap.add_argument("--tut", action="store_true", help="ikiz veritabanini silme")
    ap.add_argument("--kendini-test", action="store_true",
                    help="yalniz mutasyon kabulu: kapi kirmizi yanabiliyor mu")
    a = ap.parse_args()

    try:
        with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
    except Exception as e:
        print("OLCULEMEDI: urunler.json okunamadi: %s" % e)
        return 2
    try:
        sqlite3.connect(":memory:").execute(
            "CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram')")
    except Exception as e:
        print("OLCULEMEDI: yerel SQLite'ta FTS5 trigram yok: %s" % e)
        return 2

    dizin = tempfile.mkdtemp(prefix="ara-maliyet-")
    yol = os.path.join(dizin, "ikiz.db")
    t0 = time.time()
    c = ikiz_kur(yol, urunler)
    print("ikiz kuruldu: %d urun, %.1f sn" % (len(urunler), time.time() - t0))

    butce = max(ADIM_BUTCESI_TABAN, len(urunler) * ADIM_BUTCESI_KATSAYI)

    if a.kendini_test:
        kod = kendini_test(c, a.limit)
        c.close()
        if not a.tut:
            try:
                os.remove(yol)
                os.rmdir(dizin)
            except OSError:
                pass
        return kod

    sorgular = korpus(urunler, a.adet)
    semantik_sapma, plan_sapma = [], []
    en_kotu = (0, "")

    for q in sorgular:
        tk = arama.tokenlar(q)
        (eski_s, eski_b), (eski_c, eski_cb) = sql_kur(tk, a.limit, False)
        (yeni_s, yeni_b), (yeni_c, yeni_cb) = sql_kur(tk, a.limit, True)

        # ── E2 PLAN: yeni sekil `u`'yu dis donguye aliyor mu?
        plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + yeni_s, yeni_b)]
        if any(CEVRILME_IZI in p for p in plan):
            plan_sapma.append((q, tk, plan))
            continue   # cevrilmis planı KOSMA — kapiyi dakikalarca bekletir

        # Eski sekil cevrilmisse onu da KOSMAYIZ (olayin ta kendisi: 6-47 sn surerdi).
        eski_plan = [r[3] for r in c.execute("EXPLAIN QUERY PLAN " + eski_s, eski_b)]
        eski_cevrilmis = any(CEVRILME_IZI in p for p in eski_plan)

        yeni_satir, adim1 = kos(c, yeni_s, yeni_b, adim_say=True)
        yeni_sayim, adim2 = kos(c, yeni_c, yeni_cb, adim_say=True)
        adim = adim1 + adim2
        if adim > en_kotu[0]:
            en_kotu = (adim, q)
        if adim > butce:
            plan_sapma.append((q, tk, ["butce asildi: VDBE~%d > %d" % (adim, butce)]))
            continue

        if eski_cevrilmis:
            # Semantik ekseni yine olculur ama ESKI sekli kosmak olayin maliyetini
            # kapiya tasirdi. Bunun yerine eski sekil, planlayici cevrilmesinden
            # ETKILENMEYEN esdeger bir yolla dogrulanir: CROSS'suz ama FTS'siz duz tarama.
            duz = ("SELECT " + KART + " FROM urunler u WHERE " +
                   " AND ".join(["instr(u.hs, ?) > 0" for _ in tk] + ["u.yayinda = 1"]) +
                   " ORDER BY u.seq DESC LIMIT ?")
            eski_satir, _ = kos(c, duz, list(tk) + [a.limit])
            duz_c = ("SELECT COUNT(*) AS n FROM urunler u WHERE " +
                     " AND ".join(["instr(u.hs, ?) > 0" for _ in tk] + ["u.yayinda = 1"]))
            eski_sayim, _ = kos(c, duz_c, list(tk))
        else:
            eski_satir, _ = kos(c, eski_s, eski_b)
            eski_sayim, _ = kos(c, eski_c, eski_cb)

        eski_id = [r[0] for r in eski_satir]
        yeni_id = [r[0] for r in yeni_satir]
        if eski_id != yeni_id or eski_sayim[0][0] != yeni_sayim[0][0]:
            semantik_sapma.append((q, tk, eski_sayim[0][0], yeni_sayim[0][0],
                                   eski_id[:5], yeni_id[:5]))

    c.close()
    if not a.tut:
        try:
            os.remove(yol)
            os.rmdir(dizin)
        except OSError:
            pass
    else:
        print("ikiz TUTULDU: %s" % yol)

    print("\nsorgu=%d  semantik sapma=%d  plan sapmasi=%d" % (
        len(sorgular), len(semantik_sapma), len(plan_sapma)))
    print("en pahali sorgu: VDBE~%d  %r  (butce %d = %d urun x %d)" % (
        en_kotu[0], en_kotu[1], butce, len(urunler), ADIM_BUTCESI_KATSAYI))

    if semantik_sapma:
        print("\n🔴 SEMANTIK SAPMA — arama sonucu DEGISTI (onarim kabul EDILEMEZ):")
        for q, tk, es, ys, ei, yi in semantik_sapma[:20]:
            print("  q=%r token=%s  toplam eski=%s yeni=%s\n    eski ilk: %s\n    yeni ilk: %s"
                  % (q, tk, es, ys, ei, yi))
    if plan_sapma:
        print("\n🔴 PLAN SAPMASI — birlesim sirasi cevrildi ya da butce asildi:")
        for q, tk, plan in plan_sapma[:20]:
            print("  q=%r token=%s" % (q, tk))
            for p in plan:
                print("      " + p)
        print("\n  NE YAPILMALI: worker/src/index.js araD1() icinde FTS birlesimi"
              " `CROSS JOIN` olarak KALMALI; `JOIN`'e donmus olabilir.")

    return 1 if (semantik_sapma or plan_sapma) else 0


if __name__ == "__main__":
    sys.exit(main())

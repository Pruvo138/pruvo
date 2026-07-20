#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — parametrik urunun TABAN FIYATI D1 feed'ine gidiyor mu (PAKET A-taban-fiyat-d1).

  python3 tools/taban-fiyat-d1-test.py

SORUN: parametrik ("olcuye ozel", sari seri) urunun public fiyat'i BOS; taban fiyat yalniz
jenerator/urunler/<id>.json tabanFiyatTL'de. D1 semasinda taban kolonu YOKTU -> Ege (bot)
parametrik urunde fiyat goremiyor, siparisi insana devrediyor (sessiz satis kaybi).

Bu test CANLI D1'e / wrangler'a / aga DOKUNMAZ: gercek tools/d1-sema.sql'i YEREL bir
sqlite3 kopyasina yukler, gercek d1-sync.py fonksiyonlarini (taban_fiyat_haritasi,
taban_plan, taban_senkron_sql, satir_sql) ve gercek jenerator/urunler semalarini + gercek
urunler.json'daki 21 parametrik urunu kullanir. Boylece "yerel SQLite kopyada senkron
kosulduktan sonra 21/21 taban fiyat > 0" UCTAN UCA kanitlanir.

NO-OP TUZAGI: diff-upsert hash uzerinden calisir; mevcut 21 satirin hash'i degismedigi
icin naif "semaya kolon ekle" cozumu 0 UPDATE uretir, kolon 0 kalir. Bu test tam da o
senaryoyu (RETROFIT) kurar: satirlar ZATEN var + taban_fiyat=0 + hash guncel; hedefli
taban_plan UPDATE'i olmadan taban 0 kalir (kirmizi). Testin sonunda taban_plan MONKEYPATCH
ile no-op yapilip senaryonun GERCEKTEN kirmiziya dondugu de kanitlanir (ic mutasyon guardi).
"""
import importlib.util
import json
import os
import sqlite3
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
URUNLER = os.path.join(KOK, "urunler.json")

gecen = [0]
kalan = [0]


def yukle_modul(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(KOK, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + detay if detay else ""))


def yeni_db():
    """Gercek d1-sema.sql'i yeni bir bellek-ici sqlite3'e yukle (FTS5 trigram + tetikler dahil)."""
    conn = sqlite3.connect(":memory:")
    with open(SEMA, encoding="utf-8") as f:
        conn.executescript(f.read())
    return conn


def kolonlar(conn):
    return [r[1] for r in conn.execute("PRAGMA table_info(urunler)")]


def satir_ekle(conn, d1, arama, u, seq):
    """Bir urunu d1-sync'in GERCEK satir_sql'iyle ekle (taban_fiyat DEFAULT 0 alir —
    RETROFIT: satir zaten senkronlanmis, taban henuz D1'e gitmemis)."""
    sql = d1.satir_sql(u, seq, arama.haystack(u), arama.urun_hash(u), "")
    conn.executescript(sql)


def taban_oku(conn):
    return {r[0]: r[1] for r in conn.execute("SELECT id, taban_fiyat FROM urunler")}


def fts_satir_sayisi(conn):
    return conn.execute("SELECT COUNT(*) FROM urunler_fts").fetchone()[0]


def main():
    d1 = yukle_modul("d1_sync", "d1-sync.py")
    arama = yukle_modul("arama_mod", "arama.py")

    urunler = json.load(open(URUNLER, encoding="utf-8"))
    param = [u for u in urunler if u.get("parametrik")]
    param_idler = {u["id"] for u in param}
    # birkac normal (parametrik olmayan) urun — taban 0 kalmali kontrolu icin
    normal = [u for u in urunler if not u.get("parametrik")][:5]

    # ── (0) SEMA: taban_fiyat kolonu var mi + tip INTEGER DEFAULT 0 ───────────────
    conn = yeni_db()
    kols = kolonlar(conn)
    dogrula("sema: urunler.taban_fiyat kolonu VAR", "taban_fiyat" in kols, str(kols))
    tip = [r for r in conn.execute("PRAGMA table_info(urunler)") if r[1] == "taban_fiyat"]
    dogrula("sema: taban_fiyat INTEGER NOT NULL DEFAULT 0",
            bool(tip) and tip[0][2] == "INTEGER" and tip[0][3] == 1 and str(tip[0][4]) == "0",
            str(tip))
    dogrula("d1-sync GOC_KOLON'da taban_fiyat (canli tabloya ALTER ile eklenir)",
            any(k[0] == "taban_fiyat" for k in d1.GOC_KOLON))
    conn.close()

    # ── (1) taban_fiyat_haritasi: 21 parametrik id -> taban > 0 ───────────────────
    tabanlar = d1.taban_fiyat_haritasi()
    dogrula("taban_fiyat_haritasi 21 parametrik id icerir",
            param_idler <= set(tabanlar),
            "eksik: %s" % (param_idler - set(tabanlar)))
    hepsi_pozitif = all(int(tabanlar.get(i, 0)) > 0 for i in param_idler)
    dogrula("21 parametrik id'nin HEPSININDE taban > 0 (semada)",
            hepsi_pozitif,
            "0/eksik: %s" % [i for i in param_idler if int(tabanlar.get(i, 0)) <= 0])

    # ── (2) taban_plan SAF birim kurallari ────────────────────────────────────────
    # fresh (D1 bos) -> her parametrik icin 1 UPDATE
    plan_fresh = d1.taban_plan(param, tabanlar, {})
    dogrula("taban_plan fresh: 21 UPDATE (her parametrik urune 1)",
            len(plan_fresh) == len(param_idler), "uretilen=%d beklenen=%d" % (len(plan_fresh), len(param_idler)))
    # idempotent (D1 zaten dogru) -> 0 UPDATE
    plan_idem = d1.taban_plan(param, tabanlar, {i: tabanlar[i] for i in param_idler})
    dogrula("taban_plan idempotent: D1 zaten dogruysa 0 UPDATE", plan_idem == [], str(plan_idem[:2]))
    # normal urun (semada taban yok) -> UPDATE URETILMEZ
    plan_normal = d1.taban_plan(normal, tabanlar, {})
    dogrula("taban_plan normal urune DOKUNMAZ (semada taban yok)", plan_normal == [], str(plan_normal[:2]))
    # UPDATE metni: sadece taban_fiyat, content/hs yok
    if plan_fresh:
        s0 = plan_fresh[0]
        dogrula("taban_senkron_sql yalniz taban_fiyat gunceller (hs/content yok)",
                s0.startswith("UPDATE urunler SET taban_fiyat=") and "hs" not in s0 and "hash" not in s0, s0)

    # ── (3) UCTAN UCA — RETROFIT (NO-OP TUZAGI) ───────────────────────────────────
    # 21 parametrik + 5 normal urun ZATEN D1'de (hash guncel, taban_fiyat DEFAULT 0).
    conn = yeni_db()
    seq = 0
    for u in normal + param:
        seq += 1
        satir_ekle(conn, d1, arama, u, seq)
    conn.commit()
    mevcut_taban = taban_oku(conn)
    dogrula("retrofit kurulum: parametrik satirlar D1'de taban_fiyat=0 (senkron oncesi)",
            all(int(mevcut_taban.get(i, -1)) == 0 for i in param_idler),
            "sifir-disi: %s" % {i: mevcut_taban.get(i) for i in param_idler if mevcut_taban.get(i)})

    # NAIF cozum kaniti: hash degismedi -> diff_plan 0 content degisikligi uretir
    # (yani semaya kolon eklemek + INSERT/CONFLICT'e guvenmek TEK BASINA no-op).
    # DB'de olan (normal+param) urunlerle KIYAS: bunlar zaten senkron, hash guncel.
    db_urunler = normal + param
    mevcut_hash = {r[0]: (r[1], "") for r in conn.execute("SELECT id, hash FROM urunler")}
    y, deg, bg, sil, gor = d1.diff_plan(db_urunler, mevcut_hash, {}, False,
                                        conn.execute("SELECT MAX(seq) FROM urunler").fetchone()[0])
    dogrula("NO-OP TUZAGI: hash degismedi -> diff_plan 0 content UPDATE + 0 yeni (naif cozum yetmez)",
            deg == [] and y == [] and sil == [],
            "degisen=%d yeni=%d silinen=%d" % (len(deg), len(y), len(sil)))

    # HEDEFLI cozum: taban_plan UPDATE'lerini uygula
    fts_once = fts_satir_sayisi(conn)
    yazim_once = conn.total_changes
    plan = d1.taban_plan(urunler, tabanlar, mevcut_taban)
    dogrula("retrofit: taban_plan tam 21 UPDATE uretir (yazma sayisi kontrolu)",
            len(plan) == len(param_idler), "uretilen=%d beklenen=%d" % (len(plan), len(param_idler)))
    for s in plan:
        conn.executescript(s)
    conn.commit()
    yazilan = conn.total_changes - yazim_once
    fts_sonra = fts_satir_sayisi(conn)

    sonra = taban_oku(conn)
    param_ok = [i for i in param_idler if int(sonra.get(i, 0)) > 0 and int(sonra.get(i, 0)) == int(tabanlar[i])]
    dogrula("RETROFIT SENKRON SONRASI: 21/21 parametrik id taban_fiyat > 0 (== sema)",
            len(param_ok) == len(param_idler),
            "0/yanlis: %s" % {i: sonra.get(i) for i in param_idler if i not in param_ok})
    dogrula("normal urunlerin taban_fiyat'i 0 kalir (parametrik degil)",
            all(int(sonra.get(u["id"], -1)) == 0 for u in normal),
            "0-disi normal: %s" % {u["id"]: sonra.get(u["id"]) for u in normal if sonra.get(u["id"])})
    dogrula("yazilan satir sayisi < 200 (D1 gunluk limit koruma) — olculen=%d" % yazilan,
            yazilan < 200, "yazilan=%d" % yazilan)
    dogrula("taban UPDATE FTS'i THRASH etmez (hs degismedi -> tetik calismaz)",
            fts_sonra == fts_once, "fts once=%d sonra=%d" % (fts_once, fts_sonra))
    conn.close()

    # ── (4) UCTAN UCA — FRESH (bos D1) ────────────────────────────────────────────
    # Bos D1: yeni INSERT (satir_sql) + taban_plan UPDATE -> 21/21 > 0.
    conn = yeni_db()
    # yeni INSERT'leri satir_sql'le uygula (parametrik + normal)
    seq = 0
    for u in normal + param:
        seq += 1
        satir_ekle(conn, d1, arama, u, seq)
    conn.commit()
    for s in d1.taban_plan(urunler, tabanlar, taban_oku(conn)):
        conn.executescript(s)
    conn.commit()
    fresh_sonra = taban_oku(conn)
    fresh_ok = [i for i in param_idler if int(fresh_sonra.get(i, 0)) > 0 and int(fresh_sonra.get(i, 0)) == int(tabanlar[i])]
    dogrula("FRESH (bos D1) senkron sonrasi: 21/21 parametrik taban_fiyat > 0",
            len(fresh_ok) == len(param_idler),
            "0/yanlis: %s" % {i: fresh_sonra.get(i) for i in param_idler if i not in fresh_ok})
    conn.close()

    # ── (5) IC MUTASYON GUARDI — taban_plan no-op yapilinca RETROFIT KIRMIZI olmali ─
    # (Bu, "yesil test dogru seyi olcuyor" iddiasini ic olarak da muhurler: hedefli UPDATE
    #  olmadan retrofit senaryosu taban=0 birakir.)
    conn = yeni_db()
    seq = 0
    for u in normal + param:
        seq += 1
        satir_ekle(conn, d1, arama, u, seq)
    conn.commit()
    orijinal = d1.taban_plan
    try:
        d1.taban_plan = lambda *a, **k: []   # MUTASYON: hedefli UPDATE'i kaldir
        for s in d1.taban_plan(urunler, tabanlar, taban_oku(conn)):
            conn.executescript(s)
        conn.commit()
        mut_sonra = taban_oku(conn)
        hala_sifir = all(int(mut_sonra.get(i, -1)) == 0 for i in param_idler)
        dogrula("MUTASYON KANITI: taban_plan no-op -> 21 parametrik taban_fiyat 0 KALIR (nobetci calisiyor)",
                hala_sifir,
                "sifir-disi: %s" % {i: mut_sonra.get(i) for i in param_idler if mut_sonra.get(i)})
    finally:
        d1.taban_plan = orijinal
    conn.close()

    print("\nSONUC: %d gecti, %d kaldi%s" %
          (gecen[0], kalan[0], "" if kalan[0] else " — HEPSI YESIL"))
    sys.exit(1 if kalan[0] else 0)


if __name__ == "__main__":
    main()

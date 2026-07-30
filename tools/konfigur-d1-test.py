#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — konfigur SEMASI D1 feed'ine gidiyor mu (PAKET konfigur-d1, FAZ 1+2).

  python3 tools/konfigur-d1-test.py

SORUN (iki kaynak): "olcuye ozel dekor" urununun fiyat semasi (boy araligi + fiyat capalari
+ malzeme katsayilari) urunler.json'da yasar ama Worker onu YALNIZ bundle artefaktindan
(shop/src/konfigurlar.js) gorur. Urun VERISI D1'e OTOMATIK gider (pre-push hook), SEMA ise
ELLE uretilip Worker ELLE deploy edilir. Iki elle adim = 30 Tem'de ikisi de atlandi.
FAZ 1+2 semayi D1'e tasir; boylece urun eklenince hook zaten senkronlar.

🔴 BU TESTIN ASIL KANITI (paketin en kritik bulgusu):
  arama.urun_hash() konfigur alanini KAPSAMIYOR. Yani konfigur DEGISSE bile hash AYNI kalir
  ve diff-upsert (icerik yolu) satiri yeniden YAZMAZ. konfigur'u KOLONLAR listesine
  (ON CONFLICT UPDATE) koyan "naif" cozum bu yuzden SESSIZ HATA uretirdi: D1'deki sema
  eskimis kalir, F4'te (Worker D1'den okumaya cevrildiginde) musteriye ESKI fiyat cikardi.
  Set (2) bunu DOGRUDAN olcer: alan degistir -> hash birebir AYNI -> diff_plan 0 UPDATE.

Bu test CANLI D1'e / wrangler'a / AGA DOKUNMAZ: gercek tools/d1-sema.sql'i YEREL bir
sqlite3 kopyasina yukler, gercek d1-sync.py fonksiyonlarini (konfigur_haritasi_d1,
konfigur_plan, konfigur_senkron_sql, satir_sql, diff_plan) ve gercek urunler.json'daki
konfigurlu urunleri kullanir.

MUTASYON GUARDI: sonda konfigur_plan MONKEYPATCH ile no-op yapilip senaryonun GERCEKTEN
kirmiziya dondugu kanitlanir (yesil test dogru seyi olcuyor mu).
"""
import importlib.util
import json
import os
import re
import sqlite3
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
URUNLER = os.path.join(KOK, "urunler.json")
ARTEFAKT = os.path.join(KOK, "shop", "src", "konfigurlar.js")

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


def trigram_var_mi():
    """Bu Python'un sqlite3'u fts5-trigram tokenizer'ini tasiyor mu?

    NEDEN: CI ubuntu'nun stok sqlite3'unde fts5-trigram YOK (bkz. ci-kapsam-test.py R_FTS5) —
    kardes test tools/taban-fiyat-d1-test.py tam bu yuzden CI'dan MUAF tutuldu. Bu testin
    ASIL kaniti (urun_hash konfigur'u kapsamiyor + hedefli UPDATE) FTS'e HIC ihtiyac duymaz;
    yalnizca "UPDATE FTS'i thrash etmez" iddiasi duyar. Bu yuzden muafiyet YAZMAK yerine
    kabiliyet OLCULUR: trigram yoksa sema'nin FTS bolumu yuklenmez ve o TEK iddia ACIKCA
    'ATLANDI' der (sessizce YESIL saymaz), test CI'da bloklayici kosabilir."""
    # PRUVO_FTS_YOK=1 -> kabiliyeti ZORLA yok say. CI'nin (fts5-trigram'siz) yolunu YERELDE
    # kosturup dogrulamak icin; yoksa "CI'da calisir" iddiasi olculmemis bir varsayim kalirdi.
    if os.environ.get("PRUVO_FTS_YOK") == "1":
        return False
    try:
        c = sqlite3.connect(":memory:")
        c.executescript("CREATE VIRTUAL TABLE t USING fts5(x, tokenize='trigram');")
        c.close()
        return True
    except sqlite3.Error:
        return False


FTS = trigram_var_mi()


def _sema_metni():
    """d1-sema.sql; trigram yoksa FTS5 sanal tablosu + ona bagli tetikler CIKARILIR.

    SATIR BLOGU ile kesilir, `;` ile DEGIL: tetik govdeleri (BEGIN ... ; ... END;) ic noktali
    virgul tasir; naif `;` bolmesi yarim ifade birakip semayi bozar (olculdu: "near baslik").
    TETIK bloklari ayrica `END;` ile kapanir — ic `;`'de kapatilirsa yetim `END;` kalir ve
    SQLite onu COMMIT sanip patlar (olculdu: "cannot commit - no transaction is active").
    Bu yuzden iki ayri bitis kurali var: tetik -> `END;`, digerleri -> `;` ile biten satir."""
    ham = open(SEMA, encoding="utf-8").read()
    if FTS:
        return ham
    cikti = []
    atla = False
    tetik = False
    for satir in ham.splitlines(True):
        k = satir.strip().lower()
        if not atla:
            if k.startswith("create trigger urunler_a"):
                atla, tetik = True, True
            elif (k.startswith("create virtual table") or
                  k.startswith("drop trigger if exists urunler_a")):
                atla, tetik = True, False
        if atla:
            if (tetik and k == "end;") or (not tetik and satir.rstrip().endswith(";")):
                atla = False
            continue
        cikti.append(satir)
    return "".join(cikti)


def yeni_db():
    """Gercek d1-sema.sql'i yeni bir bellek-ici sqlite3'e yukle (varsa FTS5 trigram + tetikler)."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(_sema_metni())
    return conn


def kolonlar(conn):
    return [r[1] for r in conn.execute("PRAGMA table_info(urunler)")]


def satir_ekle(conn, d1, arama, u, seq):
    """Bir urunu d1-sync'in GERCEK satir_sql'iyle ekle (konfigur DEFAULT '' alir —
    RETROFIT: satir zaten senkronlanmis, konfigur henuz D1'e gitmemis)."""
    conn.executescript(d1.satir_sql(u, seq, arama.haystack(u), arama.urun_hash(u), ""))


def konfigur_oku(conn):
    return {r[0]: (r[1] or "") for r in conn.execute("SELECT id, konfigur FROM urunler")}


def fts_satir_sayisi(conn):
    if not FTS:
        return None
    return conn.execute("SELECT COUNT(*) FROM urunler_fts").fetchone()[0]


def bundle_haritasi():
    """CANLI artefakt shop/src/konfigurlar.js icindeki `const VERI = {...};` blogunu ayristirir.
    (Turetici fonksiyonu yeniden cagirmiyoruz — o tautoloji olurdu; DEPLOY EDILEN BAYTLARI
    okuyup D1 degeriyle kiyasliyoruz.)"""
    ham = open(ARTEFAKT, encoding="utf-8").read()
    m = re.search(r"const VERI = (\{.*?\});\n", ham, re.S)
    if not m:
        sys.exit("konfigurlar.js icinde `const VERI = {...};` bulunamadi")
    return json.loads(m.group(1))


def main():
    d1 = yukle_modul("d1_sync", "d1-sync.py")
    arama = yukle_modul("arama_mod", "arama.py")

    urunler = json.load(open(URUNLER, encoding="utf-8"))
    konf_urunler = [u for u in urunler if isinstance(u, dict) and u.get("konfigur")]
    konf_idler = {u["id"] for u in konf_urunler}
    # birkac normal (konfigursuz) urun — konfigur '' kalmali + UPDATE uretilmemeli kontrolu
    normal = [u for u in urunler if isinstance(u, dict) and "konfigur" not in u][:5]

    print("konfigurlu urun: %d | ornek normal urun: %d | katalog: %d"
          % (len(konf_idler), len(normal), len(urunler)))

    # ── (0) SEMA: konfigur kolonu var mi + tip TEXT NOT NULL DEFAULT '' ───────────
    conn = yeni_db()
    kols = kolonlar(conn)
    dogrula("sema: urunler.konfigur kolonu VAR", "konfigur" in kols, str(kols))
    tip = [r for r in conn.execute("PRAGMA table_info(urunler)") if r[1] == "konfigur"]
    dogrula("sema: konfigur TEXT NOT NULL DEFAULT ''",
            bool(tip) and tip[0][2] == "TEXT" and tip[0][3] == 1 and str(tip[0][4]) == "''",
            str(tip))
    dogrula("d1-sync GOC_KOLON'da konfigur (canli tabloya ALTER ile eklenir — additive)",
            any(k[0] == "konfigur" for k in d1.GOC_KOLON))
    dogrula("konfigur ICERIK-UPSERT kolonlarinda DEGIL (KOLONLAR — sessiz eskime kapisi)",
            "konfigur" not in d1.KOLONLAR, str(d1.KOLONLAR))
    # ADDITIVE olmanin gercek testi: mevcut sorgular kirilmiyor mu?
    dogrula("additive: eski SELECT'ler (id,hash,baski,taban_fiyat,seq) HALA calisir",
            bool(conn.execute("SELECT id,hash,baski,taban_fiyat,seq FROM urunler").fetchall()) or True)
    conn.close()

    # ── (1) konfigur_haritasi_d1: 17 id -> kanonik JSON, urunler.json ile BIREBIR ──
    harita, atlanan = d1.konfigur_haritasi_d1(urunler)
    dogrula("konfigur_haritasi_d1 TUM konfigurlu id'leri icerir (%d)" % len(konf_idler),
            konf_idler == set(harita), "eksik=%s fazla=%s" %
            (konf_idler - set(harita), set(harita) - konf_idler))
    dogrula("bozuk/atlanan konfigur kaydi YOK (canli katalog temiz)", atlanan == [], str(atlanan))
    # JSON BIREBIR: D1'e yazilan metin cozuldugunde urunler.json'daki objeye esit olmali
    # (yalniz 1.0->1 sayi normalizasyonu; deger kaybi YOK).
    birebir = []
    for u in konf_urunler:
        beklenen = json.loads(json.dumps(d1.kbk._sayi_normalize(u["konfigur"])))
        birebir.append(json.loads(harita[u["id"]]) == beklenen)
    dogrula("17/17 konfigur JSON'u urunler.json ile BIREBIR (deger kaybi yok)",
            all(birebir) and len(birebir) == len(konf_idler),
            "%d/%d" % (sum(birebir), len(birebir)))
    # BUNDLE PARITESI: D1 degeri, DEPLOY EDILEN artefaktin baytlariyla ayni objeyi tasimali.
    bundle = bundle_haritasi()
    dogrula("D1 degeri CANLI bundle artefaktiyla (konfigurlar.js) BIREBIR — iki ayna ayrisamaz",
            set(bundle) == set(harita) and
            all(json.loads(harita[i]) == bundle[i] for i in harita),
            "id farki: %s" % (set(bundle) ^ set(harita)))
    # Kanonik bicim KARARLI olmali (anahtar sirasi/sayi yazimi sahte UPDATE uretmesin)
    ters = dict(reversed(list(konf_urunler[0]["konfigur"].items())))
    dogrula("kanonik bicim KARARLI: anahtar sirasi degisince metin DEGISMEZ (sahte UPDATE yok)",
            d1.konfigur_kanonik(ters) == d1.konfigur_kanonik(konf_urunler[0]["konfigur"]))

    # ── (2) 🔴 KRITIK BULGU — urun_hash konfigur'u KAPSAMIYOR ─────────────────────
    # Bu, "konfigur'u icerik-upsert yoluna koyma" kararinin OLCULMUS gerekcesi.
    kopya = json.loads(json.dumps(konf_urunler[0]))
    hash_once = arama.urun_hash(kopya)
    kopya["konfigur"]["fiyatCapalari"] = [[60, 700], [300, 3300]]   # FIYATI degistiren mutasyon
    kopya["konfigur"]["malzemeler"] = [{"ad": "PLA", "katsayi": 2.5}]
    hash_sonra = arama.urun_hash(kopya)
    dogrula("🔴 KANIT: konfigur DEGISTI ama urun_hash BIREBIR AYNI (%s) — icerik yolu KOR"
            % hash_once, hash_once == hash_sonra, "%s != %s" % (hash_once, hash_sonra))
    # ... ve bunun DAVRANIS sonucu: diff_plan 0 content UPDATE uretir.
    mevcut_hash = {kopya["id"]: (hash_once, "")}
    y, deg, bg, sil, gor = d1.diff_plan([kopya], mevcut_hash, {}, False, 1, {kopya["id"]: 1})
    dogrula("🔴 KANIT (davranis): konfigur degisiminde diff_plan 0 yeni + 0 content UPDATE "
            "(naif 'KOLONLAR'a ekle' cozumu SESSIZCE eskitirdi)",
            y == [] and deg == [] and sil == [],
            "yeni=%d degisen=%d silinen=%d" % (len(y), len(deg), len(sil)))
    # ... ama HEDEFLI plan degisimi YAKALAR (nobetin yuk tasidigi kanit).
    mut_harita, _ = d1.konfigur_haritasi_d1([kopya])
    plan_mut = d1.konfigur_plan([kopya], mut_harita, {kopya["id"]: harita[kopya["id"]]})
    dogrula("HEDEFLI konfigur_plan AYNI degisimi YAKALAR (1 UPDATE) — hash kor, plan degil",
            len(plan_mut) == 1, str(plan_mut))

    # ── (3) konfigur_plan SAF birim kurallari ─────────────────────────────────────
    plan_fresh = d1.konfigur_plan(urunler, harita, {})
    dogrula("konfigur_plan fresh (D1 bos): tam %d UPDATE (her konfigurlu urune 1)" % len(konf_idler),
            len(plan_fresh) == len(konf_idler),
            "uretilen=%d beklenen=%d" % (len(plan_fresh), len(konf_idler)))
    dogrula("konfigur_plan fresh: 15.000 konfigursuz urune DOKUNMAZ (hedef ''=varsayilan)",
            all("UPDATE urunler SET konfigur=''" not in s for s in plan_fresh),
            [s for s in plan_fresh if "konfigur=''" in s][:1])
    plan_idem = d1.konfigur_plan(urunler, harita, dict(harita))
    dogrula("konfigur_plan idempotent: D1 zaten dogruysa 0 UPDATE", plan_idem == [],
            str(plan_idem[:1]))
    if plan_fresh:
        s0 = plan_fresh[0]
        dogrula("konfigur_senkron_sql yalniz konfigur gunceller (hs/hash/content yok)",
                s0.startswith("UPDATE urunler SET konfigur=") and
                " hs=" not in s0 and " hash=" not in s0, s0[:80])
    # SILINME/BOZULMA: urunden konfigur kaldirilirsa D1 TEMIZLENMELI (stale sema = yanlis fiyat)
    kaldirilmis = json.loads(json.dumps(konf_urunler[0]))
    del kaldirilmis["konfigur"]
    h2, _ = d1.konfigur_haritasi_d1([kaldirilmis])
    plan_sil = d1.konfigur_plan([kaldirilmis], h2, {kaldirilmis["id"]: harita[konf_urunler[0]["id"]]})
    dogrula("konfigur KALDIRILINCA D1 TEMIZLENIR (1 UPDATE -> '') — stale sema birakmaz",
            len(plan_sil) == 1 and plan_sil[0].startswith("UPDATE urunler SET konfigur=''"),
            str(plan_sil))
    # BOZUK konfigur: haritaya girmez + atlanan raporlanir + D1 bosaltilir (fail-closed)
    bozuk = json.loads(json.dumps(konf_urunler[0]))
    del bozuk["konfigur"]["hacim"]
    hb, ab = d1.konfigur_haritasi_d1([bozuk])
    plan_bozuk = d1.konfigur_plan([bozuk], hb, {bozuk["id"]: harita[konf_urunler[0]["id"]]})
    dogrula("BOZUK konfigur: haritaya GIRMEZ + sebep RAPORLANIR + D1 BOSALTILIR (fail-closed)",
            hb == {} and len(ab) == 1 and ab[0][0] == bozuk["id"] and
            len(plan_bozuk) == 1 and "konfigur=''" in plan_bozuk[0],
            "harita=%s atlanan=%s plan=%s" % (hb, ab, plan_bozuk))
    for ad, deger in (("bos obje", {}), ("null", None), ("bos metin", "")):
        hz, az = d1.konfigur_haritasi_d1([dict(konf_urunler[0], konfigur=deger)])
        dogrula("BOS konfigur (%s): haritaya girmez + raporlanir" % ad,
                hz == {} and len(az) == 1, "harita=%s atlanan=%s" % (hz, az))

    # ── (4) UCTAN UCA — RETROFIT (NO-OP TUZAGI) ───────────────────────────────────
    # Konfigurlu + normal urunler ZATEN D1'de (hash guncel, konfigur DEFAULT '').
    conn = yeni_db()
    db_urunler = normal + konf_urunler
    for i, u in enumerate(db_urunler, start=1):
        satir_ekle(conn, d1, arama, u, i)
    conn.commit()
    once = konfigur_oku(conn)
    dogrula("retrofit kurulum: konfigurlu satirlar D1'de konfigur='' (senkron oncesi)",
            all(once.get(i) == "" for i in konf_idler),
            str({i: once.get(i)[:20] for i in konf_idler if once.get(i)}))

    # NAIF cozum kaniti: hash degismedi -> diff_plan 0 content UPDATE uretir.
    mevcut_hash = {r[0]: (r[1], "") for r in conn.execute("SELECT id, hash FROM urunler")}
    y, deg, bg, sil, gor = d1.diff_plan(
        db_urunler, mevcut_hash, {}, False,
        conn.execute("SELECT MAX(seq) FROM urunler").fetchone()[0])
    dogrula("NO-OP TUZAGI: hash guncel -> diff_plan 0 content UPDATE (semaya kolon eklemek YETMEZ)",
            deg == [] and y == [] and sil == [],
            "degisen=%d yeni=%d silinen=%d" % (len(deg), len(y), len(sil)))

    fts_once = fts_satir_sayisi(conn)
    yazim_once = conn.total_changes
    plan = d1.konfigur_plan(urunler, harita, once)
    dogrula("retrofit: konfigur_plan tam %d UPDATE uretir (yazma sayisi kontrolu)" % len(konf_idler),
            len(plan) == len(konf_idler),
            "uretilen=%d beklenen=%d" % (len(plan), len(konf_idler)))
    for s in plan:
        conn.executescript(s)
    conn.commit()
    yazilan = conn.total_changes - yazim_once
    sonra = konfigur_oku(conn)
    ok = [i for i in konf_idler if sonra.get(i) and json.loads(sonra[i]) == json.loads(harita[i])]
    dogrula("RETROFIT SENKRON SONRASI: %d/%d konfigur D1'de BIREBIR" % (len(ok), len(konf_idler)),
            len(ok) == len(konf_idler),
            "eksik/yanlis: %s" % [i for i in konf_idler if i not in ok])
    dogrula("normal urunlerin konfigur'u '' kalir (konfigurlu degil)",
            all(sonra.get(u["id"]) == "" for u in normal),
            str({u["id"]: sonra.get(u["id"]) for u in normal if sonra.get(u["id"])}))
    dogrula("yazilan satir sayisi < 200 (D1 gunluk limit koruma) — olculen=%d" % yazilan,
            yazilan < 200, "yazilan=%d" % yazilan)
    if FTS:
        dogrula("konfigur UPDATE FTS'i THRASH etmez (hs degismedi -> tetik calismaz)",
                fts_satir_sayisi(conn) == fts_once,
                "fts once=%s sonra=%s" % (fts_once, fts_satir_sayisi(conn)))
    else:
        print("  ATLANDI konfigur UPDATE FTS'i THRASH etmez — bu sqlite3'te fts5-trigram YOK "
              "(CI ubuntu stok kurulumu; yerelde kosunca OLCULUR)")
    # IDEMPOTENT ikinci kosum: 0 UPDATE (her push'ta yeniden yazma yok)
    dogrula("ikinci kosum 0 UPDATE (idempotent — her push'ta 17 yazma tekrarlamaz)",
            d1.konfigur_plan(urunler, harita, konfigur_oku(conn)) == [])
    conn.close()

    # ── (5) UCTAN UCA — FRESH (bos D1) ────────────────────────────────────────────
    conn = yeni_db()
    for i, u in enumerate(db_urunler, start=1):
        satir_ekle(conn, d1, arama, u, i)
    conn.commit()
    for s in d1.konfigur_plan(urunler, harita, konfigur_oku(conn)):
        conn.executescript(s)
    conn.commit()
    fresh = konfigur_oku(conn)
    fresh_ok = [i for i in konf_idler
                if fresh.get(i) and json.loads(fresh[i]) == json.loads(harita[i])]
    dogrula("FRESH (bos D1) senkron sonrasi: %d/%d konfigur > '' ve BIREBIR" % (
        len(fresh_ok), len(konf_idler)), len(fresh_ok) == len(konf_idler),
            "eksik: %s" % [i for i in konf_idler if i not in fresh_ok])
    conn.close()

    # ── (6) IC MUTASYON GUARDI — konfigur_plan no-op yapilinca RETROFIT KIRMIZI olmali ─
    conn = yeni_db()
    for i, u in enumerate(db_urunler, start=1):
        satir_ekle(conn, d1, arama, u, i)
    conn.commit()
    orijinal = d1.konfigur_plan
    try:
        d1.konfigur_plan = lambda *a, **k: []      # MUTASYON: hedefli UPDATE'i kaldir
        for s in d1.konfigur_plan(urunler, harita, konfigur_oku(conn)):
            conn.executescript(s)
        conn.commit()
        mut = konfigur_oku(conn)
        dogrula("MUTASYON KANITI: konfigur_plan no-op -> %d konfigur '' KALIR (nobetci calisiyor)"
                % len(konf_idler), all(mut.get(i) == "" for i in konf_idler),
                str({i: mut.get(i)[:20] for i in konf_idler if mut.get(i)}))
    finally:
        d1.konfigur_plan = orijinal
    conn.close()

    # ── (7) MUTASYON — kolon semadan cikarilinca test KIRMIZI yanmali mi? ─────────
    # (0) setinin yuk tasidiginin kaniti: sema metninden konfigur satiri silinir.
    sema_metin = open(SEMA, encoding="utf-8").read()
    mutant_sema = re.sub(r"^\s*konfigur\s+TEXT NOT NULL DEFAULT '',\n", "", sema_metin,
                         count=1, flags=re.M)
    dogrula("mutasyon capasi: sema'daki konfigur kolon satiri BULUNDU (capa yasiyor)",
            mutant_sema != sema_metin)
    mc = sqlite3.connect(":memory:")
    mc.executescript(mutant_sema)
    mut_kols = [r[1] for r in mc.execute("PRAGMA table_info(urunler)")]
    dogrula("MUTASYON KANITI: kolon semadan cikinca (0) seti KIRMIZI yanar",
            "konfigur" not in mut_kols, str(mut_kols))
    mc.close()

    print("\nSONUC: %d gecti, %d kaldi%s" %
          (gecen[0], kalan[0], "" if kalan[0] else " — HEPSI YESIL"))
    sys.exit(1 if kalan[0] else 0)


if __name__ == "__main__":
    main()

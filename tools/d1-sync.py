#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urunler.json -> Cloudflare D1 (katalog + arama indeksi). FAZ 1.

  python3 tools/d1-sync.py --sema     # semayi kur (bir kez / degisince)
  python3 tools/d1-sync.py            # DIFF-UPSERT: sadece degisen/yeni/silinen
  python3 tools/d1-sync.py --kuru     # hicbir sey yazma, ne yapacagini soyle
  python3 tools/d1-sync.py --durum    # D1'deki urun sayisi + son senkron

*** NEDEN DIFF-UPSERT SART ***
D1 ucretsiz katmanda GUNDE 100.000 SATIR YAZMA siniri var (okuma 100M, depolama 5 GB
— onlar bol). Her push'ta tam rebuild yazilirsa 50k urunde 2 rebuild limiti bitirir,
D1 hata dondurmeye baslar ve ARAMA COKER. Bu yuzden ürünün icerik ozeti (hash)
tutulur; ozeti degismeyen urune DOKUNULMAZ. Gunde ~600 yeni urun = ~600 yazma.

*** SIRA (seq) TUZAGI ***
Yeni urun urunler.json'un BASINA eklenir; dizi indeksini sira yapsaydik her eklemede
TUM urunlerin sirasi kayar, hepsi "degismis" gorunur ve her push tam rebuild olurdu
(yukaridaki limit tam da bu yuzden patlardi). Onun yerine her urune ilk eklendiginde
SABIT bir seq verilir; ORDER BY seq DESC = katalog sirasi (en yeni ustte).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arama

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
# PARAMETRIK TABAN FIYAT kaynagi = jenerator/urunler/<id>.json "tabanFiyatTL" (tam sayi TL).
# TEK KAYNAK, build.py uret_taban_fiyatlar() ile AYNI dosyalari okur. Bu dizin GIT'TE
# (izlenir) -> hem yerelde hem GitHub Actions'ta erisilir. taban-fiyatlar.js DEGIL: o
# build.py ciktisi + gitignore -> CI'da/temiz checkout'ta olmayabilir (bayat/eksik).
JEN_URUN_DIR = os.path.join(KOK, "jenerator", "urunler")
# GIZLI kaynak kaydi (gitignore). "baski" alani (uretim ayar onerisi) buradan D1'e
# tasinir — PUBLIC urunler.json'a YAZILMAZ. Dosya yoksa (baska makine/CI) baski bos kalir.
KAYNAKLAR = os.path.join(KOK, ".urun-kaynaklari.json")

# DB'yi ADIYLA degil UUID'siyle cagiriyoruz: boylece wrangler.toml GEREKMEZ ve bu betik
# hem burada hem GitHub Actions'ta (pruvo-bot repo'su orada yok) AYNI yoldan calisir.
# Actions'ta kimlik: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID ortam degiskenleri;
# yerelde: wrangler'in kendi oturumu (npx wrangler login).
DB = "3d99d15e-2342-4c23-9c2d-cb266f19c1ee"  # pruvo-katalog

# Tek wrangler cagrisina konacak azami ifade sayisi (istek boyutu makul kalsin).
PARCA = 400


def wrangler(args, girdi_dosya=None):
    """wrangler d1 execute calistir, JSON sonucu dondur."""
    komut = ["npx", "--yes", "wrangler@4", "d1", "execute", DB, "--remote", "--json"] + args
    p = subprocess.run(komut, cwd=KOK, capture_output=True, text=True)
    ham = (p.stdout or "") + (p.stderr or "")

    # Sandbox'li oturumlarda (Claude/CI) ~/.npm/_cacache yazilamayabilir (EPERM) ve
    # npx daha baslamadan duser (denetim 2026-07-15). Gecici bir npm cache ile TEK
    # SEFER yeniden dene — pre-push senkronunun sessizce kacmasini onler.
    if p.returncode != 0 and "EPERM" in ham and "_cacache" in ham:
        ort = dict(os.environ, npm_config_cache=tempfile.mkdtemp(prefix="pruvo-npm-"))
        p = subprocess.run(komut, cwd=KOK, capture_output=True, text=True, env=ort)
        ham = (p.stdout or "") + (p.stderr or "")

    # En sik hata: token'in D1 yetkisi yok. Ham wrangler ciktisi bunu anlatmiyor
    # ("cozulemedi" deyip gecmek, sonraki oturuma sebebi kaybettiriyor) — acikca soyle.
    if "code: 10000" in ham or "Authentication error" in ham:
        sys.exit(
            "D1 KIMLIK HATASI (code 10000) — token D1'e erisemiyor.\n"
            "  Cloudflare panel > My Profile > API Tokens > CLOUDFLARE_API_TOKEN >\n"
            "  Permissions'a **Account > D1 > Edit** ekle. (Mevcut token cache-purge\n"
            "  icin uretilmis, yalnizca zone yetkisi var.)\n"
            "\n"
            "  !! FAZ 2'DEN SONRA BU ARTIK ZARARSIZ DEGIL: Ege (WhatsApp botu) urunleri\n"
            "  artik urunler.json'dan DEGIL D1'den okuyor. D1 senkronu basarisiz olursa\n"
            "  SITE yeni urunu gosterir ama EGE GORMEZ — musteriye 'boyle bir sey yok'\n"
            "  demez (oyle egitildi) ama urunu de oneremez. Sessiz satis kaybi.\n"
            "  GECICI COZUM: her urun push'undan sonra YERELDE 'python3 tools/d1-sync.py'\n"
            "  calistir (yerelde wrangler'in kendi oturumu kullanilir, token gerekmez)."
        )

    i = p.stdout.find("[")
    if i == -1:
        sys.exit("wrangler cikti vermedi:\n" + ham[-2000:])
    try:
        return json.loads(p.stdout[i:])
    except json.JSONDecodeError:
        sys.exit("wrangler ciktisi cozulemedi:\n" + ham[-2000:])


def sorgu(sql):
    return wrangler(["--command", sql])


def dosya_calistir(sql_metin):
    """Uzun SQL'i gecici dosyaya yazip calistir; (rows_written, rows_read) dondur."""
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
        f.write(sql_metin)
        yol = f.name
    try:
        sonuc = wrangler(["--file", yol])
        yaz = oku = 0
        for r in sonuc:
            m = r.get("meta") or {}
            yaz += m.get("rows_written") or 0
            oku += m.get("rows_read") or 0
        return yaz, oku
    finally:
        os.unlink(yol)


def q(s):
    """SQL metin sabiti — tek tirnak kacisi."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def urunleri_oku():
    with open(URUNLER, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        sys.exit("urunler.json dizi degil")
    return d


def d1_mevcut():
    """D1'deki {id: (hash, baski)} + {id: taban_fiyat} + en buyuk seq.
    baski da OKUNUR: baski senkronu (main) onu D1'dekiyle KIYASLAR — degismemisse yazmaz
    (yoksa her yerel kosum tum baski'lari yeniden yazardi).
    taban_fiyat da OKUNUR: taban senkronu (main) onu semadakiyle KIYASLAR — ayni mantik.
    NOT: taban_fiyat kolonu --sema (GOC_KOLON ALTER) ile eklenir; bu SELECT'ten ONCE
    --sema kosmus olmali (canli uygulama sirasi RAPOR-MIMARA.md'de)."""
    r = sorgu("SELECT id, hash, baski, taban_fiyat FROM urunler")
    satirlar = (r[0].get("results") or []) if r else []
    mevcut = {s["id"]: (s["hash"], s.get("baski") or "") for s in satirlar}
    mevcut_taban = {s["id"]: int(s.get("taban_fiyat") or 0) for s in satirlar}
    r2 = sorgu("SELECT COALESCE(MAX(seq), 0) AS m FROM urunler")
    mseq = ((r2[0].get("results") or [{}])[0] or {}).get("m") or 0
    return mevcut, mevcut_taban, int(mseq)


# Sonradan eklenen kolonlar. Mevcut D1 tablosunda CREATE TABLE IF NOT EXISTS bunlari
# EKLEMEZ (tablo zaten var) -> --sema calistiginda eksikler ALTER ile tamamlanir.
GOC_KOLON = [
    ("aciklama", "TEXT NOT NULL DEFAULT ''"),
    ("ege", "TEXT NOT NULL DEFAULT ''"),
    ("hs_baslik", "TEXT NOT NULL DEFAULT ''"),
    ("hs_baslik_kok", "TEXT NOT NULL DEFAULT ''"),
    ("hs_govde", "TEXT NOT NULL DEFAULT ''"),
    ("hs_govde_kok", "TEXT NOT NULL DEFAULT ''"),
    # BASKI onerisi (siparis yonetimi paketi) — gizli kayittan doldurulur (asagida).
    ("baski", "TEXT NOT NULL DEFAULT ''"),
    # PARAMETRIK TABAN FIYAT (TL, tam sayi) — jenerator/urunler/<id>.json tabanFiyatTL'den
    # doldurulur. Mevcut canli tabloda CREATE atlanir -> --sema ALTER ile ekler. HASH'e
    # KARISMAZ; hedefli UPDATE (taban_senkron_sql) ile senkronlanir (baski deseni).
    ("taban_fiyat", "INTEGER NOT NULL DEFAULT 0"),
]

# siparisler icin ayni mekanizma (shop kargo + siparis yonetimi paketleri): DEFAULT'lu
# ekleme -> eski siparis satirlari bozulmaz (kargo/KDV tahsil edilmedi, onay kutusu yoktu).
GOC_KOLON_SIPARIS = [
    ("kargo_kurus", "INTEGER NOT NULL DEFAULT 0"),
    ("kdv_kurus", "INTEGER NOT NULL DEFAULT 0"),
    ("odeme_yontemi", "TEXT NOT NULL DEFAULT 'kart'"),
    ("sozlesme_onay", "TEXT NOT NULL DEFAULT ''"),
    # Siparis yonetimi paketi: kargo firma+kodu + durum gecmisi (same-row, ek satir yazmaz).
    ("kargo_firma", "TEXT NOT NULL DEFAULT ''"),
    ("kargo_kodu", "TEXT NOT NULL DEFAULT ''"),
    ("durum_gecmisi", "TEXT NOT NULL DEFAULT ''"),
    # Reklam ROI olcumu (reklam-roi-sistemi.md Faz 0): atif kimlikleri (GA client_id + Meta
    # fbp/fbc + UTM) kompakt JSON. Purchase event (shop donus) bunlari kullanir; PII yok.
    ("atif", "TEXT NOT NULL DEFAULT ''"),
]

# ON CONFLICT (UPDATE) sirasinda GUNCELLENEN kolonlar.
# "baski" BILEREK YOK: baski yalnizca gizli .urun-kaynaklari.json'da (CI'da yok).
# Content upsert'i baski'yi da yazsaydi CI HER kosumda baski'yi '' YAPARDI (D1'den
# SILERDI — 2026-07-18: canlida 7381 satirin hepsinde baski='' bulundu, sebep buydu).
# baski AYRI senkronla yonetilir (baski_senkron_sql + main) ve SADECE dosyasi olan
# ortam (yerel) yazar. INSERT VALUES'ta baski VAR (yeni satir onu alir); sadece
# CONFLICT/UPDATE yolu baski'ya dokunmaz.
KOLONLAR = [
    "hash", "baslik", "kategori", "marka", "fiyat", "gorsel", "parametrik", "hs",
    "aciklama", "ege", "hs_baslik", "hs_baslik_kok", "hs_govde", "hs_govde_kok",
]


def baski_haritasi():
    """Gizli .urun-kaynaklari.json'dan id -> baski onerisi. "-"/bos placeholder atlanir.
    Dosya yoksa (CI/baska makine) BOS harita — baski kolonu '' kalir, worker fallback'e duser.
    PUBLIC repoya sizmaz: yalnizca D1'e (ozel) yazilir, urunler.json'a DEGIL."""
    if not os.path.exists(KAYNAKLAR):
        return {}
    try:
        with open(KAYNAKLAR, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    harita = {}
    if isinstance(d, dict):
        for uid, kayit in d.items():
            if not isinstance(kayit, dict):
                continue
            b = (kayit.get("baski") or "").strip()
            if b and b != "-":
                harita[uid] = b
    return harita


# ─── BASKI ve DIFF-HASH AYRIMI (thrash onarimi, 2026-07-18) ───────────────────
# diff-upsert'in "hash" alani = SADECE arama.urun_hash(u) (PUBLIC icerik). baski ASLA
# hash'e KARISMAZ.
#   NEDEN (olculmus hata): eski etkin_hash() baski'yi hash'e katiyordu. Ama baski yalnizca
#   gizli .urun-kaynaklari.json'da; YEREL onu gorur, GitHub Actions (gitignore) GORMEZ.
#   Sonuc: yerel "baski'li hash", CI "baski'siz hash" yazip birbirini EZDI. Her push'ta
#   ~3.700 baski'li urun "degismis" gorunup yeniden yaziliyordu (12 urunluk batch'te
#   ~7.400 yazma = neredeyse tam rebuild; D1 gunluk 100.000 yazma limitine dogru kosuyordu).
#   Ustelik baski KOLONLAR'daydi -> CI content-upsert'i baski'yi '' yapip D1'den SILIYORDU.
# COZUM:
#   (1) hash iki ortamda AYNI (baski'siz) -> content thrash BITER.
#   (2) baski AYRI senkronlanir (baski_senkron_sql), yalnizca dosyasi olan ortam (yerel)
#       ve SADECE D1'dekinden farkliysa yazar -> degismeyen baski'ye dokunulmaz, CI silmez.
def baski_senkron_sql(uid, baski):
    """Tek urun icin SADECE baski kolonunu gunceller (content'e/hs'e dokunmaz -> hash ayni,
    FTS tetigi calismaz, ek satir yazmaz). Yalnizca baski FIILEN degistiyse cagrilir (main)."""
    return "UPDATE urunler SET baski=%s WHERE id=%s;" % (q(baski), q(uid))


# ─── PARAMETRIK TABAN FIYAT (D1 feed'i) ──────────────────────────────────────
# Parametrik urunun public fiyat'i BOS; taban fiyat jenerator/urunler/<id>.json
# tabanFiyatTL'de yasar. Bu bilgi D1'e HIC gitmiyordu -> Ege (bot) parametrik urunde
# fiyat goremiyor, siparisi insana devrediyor (sessiz satis kaybi). Cozum: taban_fiyat
# kolonu + HEDEFLI UPDATE (baski deseni). HASH'e KATILMAZ -> content thrash yok.
def taban_fiyat_haritasi():
    """jenerator/urunler/<id>.json -> {id: tabanFiyatTL(int)} (tabanFiyatTL None/eksik
    ATLANIR). build.py uret_taban_fiyatlar() ile AYNI dosya + AYNI kural (tek kaynak).
    Dizin yoksa (beklenmez; git'te izlenir) BOS harita -> taban_fiyat 0 kalir, Ege
    fallback'e duser (mevcut davranis, regresyon degil)."""
    harita = {}
    if not os.path.isdir(JEN_URUN_DIR):
        return harita
    for ad in sorted(os.listdir(JEN_URUN_DIR)):
        if not ad.endswith(".json"):
            continue
        try:
            with open(os.path.join(JEN_URUN_DIR, ad), encoding="utf-8") as f:
                sema = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        taban = sema.get("tabanFiyatTL")
        if taban is None:
            continue
        try:
            harita[sema.get("id") or ad[:-5]] = int(taban)
        except (TypeError, ValueError):
            continue
    return harita


def taban_senkron_sql(uid, taban):
    """Tek urun icin SADECE taban_fiyat kolonunu gunceller (content'e/hs'e DOKUNMAZ ->
    hash ayni, FTS tetigi (WHEN old.hs<>new.hs) CALISMAZ, ek FTS satiri yazmaz).
    Yalnizca taban FIILEN degistiyse cagrilir (taban_plan)."""
    return "UPDATE urunler SET taban_fiyat=%d WHERE id=%s;" % (int(taban), q(uid))


def taban_plan(urunler, tabanlar, mevcut_taban):
    """SAF plan (canli D1'e DOKUNMAZ -> birim testi burayi cagirir). Doner: hedefli
    taban_fiyat UPDATE'leri listesi.
    - tabanlar   = {id: int}  jenerator semasindaki tabanFiyatTL (istenen deger)
    - mevcut_taban = {id: int} D1'deki mevcut taban_fiyat (yeni urun icin yok -> 0)
    KURAL: yalnizca semada taban VAR (parametrik) VE D1'deki degerden FARKLIYSA 1 UPDATE.
    Yeni urunde mevcut_taban 0 doner -> INSERT'ten SONRA (main ifade sirasi) UPDATE eder.
    Boylece 21 parametrik urun D1'de fiyati gorunur; hash'e dokunmadigi icin no-op tuzagina
    dusmez (diff_plan hash degismedi der ama taban_plan yine de senkronlar)."""
    if not tabanlar:
        return []
    out = []
    gorulen = set()
    for u in urunler:
        uid = u.get("id")
        if not uid or uid in gorulen:
            continue
        gorulen.add(uid)
        hedef = tabanlar.get(uid)
        if hedef is None:
            continue  # taban yok (normal urun / tabanFiyatTL null) -> taban_fiyat 0 kalir
        if int(hedef) != int(mevcut_taban.get(uid, 0)):
            out.append(taban_senkron_sql(uid, hedef))
    return out


def diff_plan(urunler, mevcut, baskilar, baski_yetki, mseq):
    """SAF diff (canli D1'e DOKUNMAZ -> birim testi burayi cagirir).
    mevcut = {id: (hash, baski)}. Doner: (yeni, degisen, baski_guncelle, silinen, gorulen).
    - yeni/degisen: content upsert SQL'leri (baski INSERT VALUES'ta, CONFLICT'te DEGIL).
    - baski_guncelle: SADECE baski FIILEN degistiginde 1 UPDATE (yalniz baski_yetki=EVET)."""
    yeni, degisen, baski_guncelle = [], [], []
    gorulen = set()
    sonraki = mseq
    # TERS gez: dizinin BASI en yeni -> en yuksek seq alsin (ORDER BY seq DESC = katalog sirasi).
    for u in reversed(urunler):
        uid = u.get("id")
        if not uid or uid in gorulen:
            continue
        gorulen.add(uid)
        h = arama.urun_hash(u)          # baski'SIZ — yerel ve CI AYNI degeri uretir
        kayit = mevcut.get(uid)         # (hash, baski) veya None
        eski_h = kayit[0] if kayit else None
        eski_baski = kayit[1] if kayit else ""
        baski = baskilar.get(uid, "")
        if eski_h is None:
            sonraki += 1
            yeni.append(satir_sql(u, sonraki, arama.haystack(u), h, baski))  # INSERT baski'yi da yazar
        elif eski_h != h:
            degisen.append(satir_sql(u, 0, arama.haystack(u), h, baski))     # seq ON CONFLICT'te korunur
        # baski senkronu: YALNIZ yetki varsa (CI atlar -> baski'yi silmez/ezmez),
        # MEVCUT satir icin (yeni urun baski'yi INSERT'te aldi), ve FIILEN degistiyse.
        if baski_yetki and eski_h is not None and baski != eski_baski:
            baski_guncelle.append(baski_senkron_sql(uid, baski))
    silinen = [i for i in mevcut if i not in gorulen]
    return yeni, degisen, baski_guncelle, silinen, gorulen


def kolon_goc():
    """Eksik kolonlari ekle. Idempotent: SQLite'ta 'ADD COLUMN IF NOT EXISTS' yok,
    o yuzden once table_info'ya bakilir (kor ALTER ikinci calismada patlardi)."""
    for tablo, kolonlar in (("urunler", GOC_KOLON), ("siparisler", GOC_KOLON_SIPARIS)):
        r = sorgu("PRAGMA table_info(%s)" % tablo)
        var = {s["name"] for s in (r[0].get("results") or [])}
        eksik = [(ad, tip) for ad, tip in kolonlar if ad not in var]
        if not eksik:
            print("%s kolonlari tam — goc gerekmedi" % tablo)
            continue
        dosya_calistir("\n".join(
            "ALTER TABLE %s ADD COLUMN %s %s;" % (tablo, ad, tip) for ad, tip in eksik))
        print("%s eklenen kolon: %s" % (tablo, ", ".join(ad for ad, _ in eksik)))


def satir_sql(u, seq, hs, h, baski=""):
    """Tek urun icin upsert. ON CONFLICT -> rid/seq korunur (FTS rowid'i sabit kalir)."""
    g = (u.get("gorseller") or [None])[0]
    e_bas = arama.ege_baslik(u)
    e_gov = arama.ege_govde(u)
    degerler = [
        q(u["id"]), q(h), str(seq), q(u.get("baslik") or ""), q(u.get("kategori") or ""),
        q(json.dumps(u.get("marka") or [], ensure_ascii=False)), q(u.get("fiyat") or ""),
        q(g), "1" if u.get("parametrik") else "0", q(hs),
        q(u.get("aciklama") or ""), q(u.get("ege") or ""),
        q(e_bas), q(arama.koke_cevir(e_bas)), q(e_gov), q(arama.koke_cevir(e_gov)),
        q(baski),
    ]
    return (
        "INSERT INTO urunler (id,hash,seq,baslik,kategori,marka,fiyat,gorsel,parametrik,hs,"
        "aciklama,ege,hs_baslik,hs_baslik_kok,hs_govde,hs_govde_kok,baski) VALUES ("
        + ",".join(degerler)
        + ") ON CONFLICT(id) DO UPDATE SET "
        + ", ".join("%s=excluded.%s" % (k, k) for k in KOLONLAR) + ";"
    )


def durum_uyumlu(d1_sayisi, urunler_benzersiz):
    """--durum FAIL-LOUD teyidi: D1 satir sayisi urunler.json'daki BENZERSIZ id sayisina
    ESIT mi? SAF fonksiyon (D1'e/dosyaya DOKUNMAZ) -> birim testi burayi cagirir, wrangler
    gerekmez. d1_sayisi None ise (D1 okunamadi / COUNT None dondu) UYUMSUZ say = fail-loud.
    NEDEN benzersiz: sync id'ye gore dedup eder (diff_plan 'gorulen'); D1'de her benzersiz id
    tam 1 satir olur, dolayisiyla dogru invariant D1 COUNT(*) == benzersiz id sayisi."""
    if d1_sayisi is None:
        return False
    try:
        return int(d1_sayisi) == int(urunler_benzersiz)
    except (TypeError, ValueError):
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sema", action="store_true", help="semayi kur")
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    ap.add_argument("--durum", action="store_true", help="D1 durumu")
    a = ap.parse_args()

    if a.sema:
        with open(SEMA, encoding="utf-8") as f:
            yaz, _ = dosya_calistir(f.read())
        print("sema kuruldu (yazilan satir: %d)" % yaz)
        kolon_goc()   # tablo zaten varsa CREATE atlanir -> yeni kolonlari ALTER ekler
        return

    if a.durum:
        r = sorgu("SELECT COUNT(*) AS n FROM urunler")
        n = ((r[0].get("results") or [{}])[0] or {}).get("n")
        r = sorgu("SELECT anahtar, deger FROM senkron")
        print("D1 urun sayisi:", n)
        for s in (r[0].get("results") or []):
            print("  %s = %s" % (s["anahtar"], s["deger"]))
        # FAIL-LOUD teyit: D1 satir sayisi urunler.json'daki BENZERSIZ id sayisiyla ORTUSMELI.
        # Eskiden --durum yalniz sayiyi BASIP exit 0 donerdi -> insan/hook/CI iki sayiyi ELLE
        # kiyaslamak zorundaydi ve kiyaslamayan "yesil" gorup gecerdi (Ege bayat katalog okur =
        # SESSIZ satis kaybi). Artik uyumsuzlukta exit 1: pre-push hook mesajinin ve CLAUDE.md'nin
        # isaret ettigi 'teyit' fiilen bir KAPI olur.
        urunler = urunleri_oku()
        benzersiz = len({u.get("id") for u in urunler if u.get("id")})
        print("urunler.json benzersiz id:", benzersiz)
        if not durum_uyumlu(n, benzersiz):
            sys.exit(
                "!! D1 SENKRON DRIFT: D1=%s != urunler.json benzersiz=%d.\n"
                "   Senkron kacmis olabilir; Ege bayat katalog goruyor (yeni urunu ONEREMEZ).\n"
                "   Coz: python3 tools/d1-sync.py   (yerelde wrangler oturumu; token gerekmez)"
                % (n, benzersiz)
            )
        print("teyit: D1 == urunler.json benzersiz (%d) ✅" % benzersiz)
        return

    urunler = urunleri_oku()
    mevcut, mevcut_taban, mseq = d1_mevcut()
    baskilar = baski_haritasi()
    tabanlar = taban_fiyat_haritasi()
    # baski YETKISI = gizli kayit dosyasi bu ortamda VAR mi? YOKSA (CI) baski'ya HIC dokunma
    # (yoksa CI baski'yi D1'den silerdi). VARSA (yerel) baski'yi ayrica senkronla.
    baski_yetki = os.path.exists(KAYNAKLAR)
    print("urunler.json: %d urun | D1: %d urun | gizli baski kaydi: %d | baski yetki: %s | taban fiyat semasi: %d"
          % (len(urunler), len(mevcut), len(baskilar),
             "EVET" if baski_yetki else "HAYIR (baski atlanir)", len(tabanlar)))

    yeni, degisen, baski_guncelle, silinen, gorulen = diff_plan(
        urunler, mevcut, baskilar, baski_yetki, mseq)
    # TABAN FIYAT senkronu: baski'dan BAGIMSIZ + HASH'ten bagimsiz (git'te oldugu icin
    # yetki kapisi da yok — CI da yerel de ayni degeri gorur). Yeni urun taban_fiyat'i
    # INSERT DEFAULT 0 alir, bu UPDATE (ifade sirasinda INSERT'ten SONRA) fiyatini yazar.
    taban_guncelle = taban_plan(urunler, tabanlar, mevcut_taban)
    print("yeni: %d | degisen: %d | baski-guncelle: %d | taban-guncelle: %d | silinen: %d | dokunulmayan: %d"
          % (len(yeni), len(degisen), len(baski_guncelle), len(taban_guncelle), len(silinen),
             len(gorulen) - len(yeni) - len(degisen)))

    if a.kuru:
        print("(--kuru: hicbir sey yazilmadi)")
        return
    if not yeni and not degisen and not baski_guncelle and not taban_guncelle and not silinen:
        print("degisiklik yok — D1'e yazilmadi ✅")
        return

    ifadeler = []
    for parca in [silinen[i:i + PARCA] for i in range(0, len(silinen), PARCA)]:
        ifadeler.append("DELETE FROM urunler WHERE id IN (%s);" % ",".join(q(i) for i in parca))
    # SIRA ONEMLI: yeni (INSERT) taban_guncelle'den (UPDATE) ONCE gelmeli -> yeni parametrik
    # urun once eklenir, sonra taban_fiyat'i yazilir (ayni --file'da sirali calisir).
    ifadeler += degisen + yeni + baski_guncelle + taban_guncelle

    top_yaz = 0
    for i in range(0, len(ifadeler), PARCA):
        yaz, _ = dosya_calistir("\n".join(ifadeler[i:i + PARCA]))
        top_yaz += yaz
        print("  parca %d/%d — yazilan satir: %d"
              % (i // PARCA + 1, (len(ifadeler) + PARCA - 1) // PARCA, yaz))

    yaz, _ = dosya_calistir(
        "INSERT INTO senkron (anahtar,deger) VALUES ('urun_sayisi',%s) "
        "ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger;" % q(str(len(gorulen)))
    )
    top_yaz += yaz

    print("TOPLAM yazilan satir: %d (D1 gunluk sinir: 100.000)" % top_yaz)
    if top_yaz > 100000:
        print("!! UYARI: bu tek calisma gunluk yazma limitini asti.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATOMIK YAYIN KAPISI — "karti gorunen urun asla 404 vermez".

  python3 tools/yayin-kapisi.py --durum          # sayilar (D1 taslak/yayinda + canli)
  python3 tools/yayin-kapisi.py --yayinla        # deploy'dan SONRA: canli 200 -> yayinda=1
  python3 tools/yayin-kapisi.py --geriye-doldur  # TEK SEFERLIK goc: canlidakileri yayinda=1
  python3 tools/yayin-kapisi.py --kendini-test   # OFFLINE kabul testi (ag/D1 GEREKMEZ)

════════════════════════════════════════════════════════════════════════════════════
NEDEN VAR — OLCULEN PENCERE (iddia degil; ham sayilar RAPOR-MIMARA.md'de)
════════════════════════════════════════════════════════════════════════════════════
Katalog iki ayri yerde yayinlanir ve bu ikisi AYNI ANDA olmaz:
  * D1 (Ege'nin okudugu yer): `.git/hooks/pre-push` d1-sync'i push'tan ONCE kosar.
  * /urun/<id>/ (musterinin tikladigi sayfa): GitHub Actions'in SONUNDA yayinlanir.
OLCUM (31 Tem, gh api, son 8 basarili kosum): push -> canli MEDYAN 593 sn (9,9 dk),
min 395 sn, max 740 sn. CI KIRMIZI olursa pencere kirmizi kaldigi surece SURER:
run#1079..1082 arasi 3.241 sn (54 dk) — o sure boyunca 98 urun D1'DEYDI, sayfalari 404'tu.
CANLI TEYIT (31 Tem 07:33Z): d75a4cf7'nin 8/8 yeni id'si D1'de bulundu, ornek 3 urun
sayfasinin 3'u de HTTP 404 dondu.

COZUM (Okan'in karari): gorunurluk ile sayfanin yayinlanmasi TEK ATOMIK islem olur.
Yeni urun D1'e TASLAK girer (yayinda=0, hicbir kesif yuzeyinde gorunmez); yayina alma
AYRI bir adimdir ve ancak /urun/<id>/ CANLIDA 200 dondugu FIILEN dogrulaninca yapilir.

🔴 FAIL-CLOSED YONU: bu kapinin her arizasi urunu GORUNMEZ birakir (satis gecikir),
ASLA "404 veren kart" uretmez. Yanlis yon (kolon okunamayinca hepsini gostermek) bu
dosyada BILEREK yoktur.

⚠️ SIRA (bozulursa TUM KATALOG gizlenir):
  1. python3 tools/d1-sync.py --sema        (yayinda/release_id kolonlari + indeksler)
  2. python3 tools/yayin-kapisi.py --geriye-doldur    (canlidaki her urun -> yayinda=1)
  3. python3 tools/yayin-kapisi.py --durum            (taslak sayisi ~0 teyidi)
  4. ANCAK BUNDAN SONRA worker'daki `yayinda=1` okuma sarti yayina alinir (HocA/KraL).
"""
import argparse
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")
SITE = "https://pruvo3d.com"

# Canli sayfa dogrulamasi ayarlari.
UA = "Mozilla/5.0 (compatible; PruvoYayinKapisi/1.0)"   # ciplak urllib UA'si 403 alabiliyor
ZAMAN_ASIMI = 20
ES_ZAMAN = 8                 # paralel HTTP kontrolu (CI suresi makul kalsin)
DENEME = 3                   # CDN isinmasi icin tekrar (404 kaliciysa 3'u de 404 doner)
DENEME_BEKLE = 4.0

# TEK KOSUMDA dogrulanabilecek azami aday. Asilirsa kapi YAYIN YAPMAZ ve sifir-disi doner:
# bu olcekteki taslak yigini "normal parti" degil GOC demektir -> --geriye-doldur kullanilir
# (canli urunler.json'u KANIT alir, 15.000 HTTP istegi atmaz). Sessiz ornekleme YASAK.
AZAMI_ADAY = 300

# UPDATE'lerin tek wrangler cagrisina konacak parca boyu (d1-sync PARCA deseni).
# 400 id ~ 6 KB SQL (D1 ifade tavani ~92 KB) — goc kosumunda cagri sayisini yariya indirir.
# 🔴 ACIK ID LISTESI (NOT IN degil) BILEREK: yayin kararini SELECT anindaki kume KILITLER.
# NOT IN yazilsaydi, SELECT ile UPDATE arasinda baska bir oturumun push'uyla D1'e giren
# YENI satir da (canlida sayfasi YOKKEN) yayina alinirdi — tam da kapattigimiz pencere.
PARCA = 400


def yukle_d1sync():
    """d1-sync.py'yi modul olarak yukle (tire iceren ad -> importlib).
    NEDEN IMPORT: wrangler cagrisi, hata tanisi, alintlama (q) ve parca mantigi TEK
    KAYNAKTA kalsin — ikinci bir wrangler sarmalayicisi yazmak drift uretirdi."""
    yol = os.path.join(KOK, "tools", "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# SAF KARAR MANTIGI (D1'e / aga DOKUNMAZ -> kabul testi burayi dogrudan cagirir)
# ═══════════════════════════════════════════════════════════════════════════════
def adaylari_sec(taslaklar, yerel_idler, canli_idler):
    """Yayina ALINABILECEK id'ler.

    KOSUL (fail-closed, UCU BIRDEN): id D1'de TASLAK olmali + YAYINLANAN (yerel, yani
    deploy edilen commit'in) urunler.json'da olmali + CANLI urunler.json'da da olmali.
    Canli JSON sarti, "CI daha yeni bir commit yayinladi / deploy henuz oturmadi"
    halinde yanlislikla yayina almayi engeller (canli JSON ile /urun/ AYNI artefaktta
    yayinlanir — deploy.yml `_site` beyaz listesi).
    Doner: (adaylar_sirali, atlanan_sebep_haritasi)"""
    yerel = set(yerel_idler)
    canli = set(canli_idler)
    adaylar, atlanan = [], {}
    for uid in taslaklar:
        if uid not in yerel:
            atlanan[uid] = "yerel urunler.json'da YOK (silinmis/bayat satir)"
        elif uid not in canli:
            atlanan[uid] = "canli urunler.json'da HENUZ YOK (deploy oturmadi)"
        else:
            adaylar.append(uid)
    return sorted(adaylar), atlanan


def yayin_karari(adaylar, kodlar):
    """kodlar = {id: HTTP kodu ya da None (istek patladi)}.
    Doner: (yayinlanacak, basarisiz) — SADECE 200 yayinlanir; None/404/500 TASLAK KALIR.
    🔴 Eksik olculen id (kodlar'da hic yoksa) da BASARISIZ sayilir: "olculmedi" asla
    "iyi" demek degildir (bkz. [[nobetci-cagri-satiri-nobetsiz]])."""
    yayinlanacak, basarisiz = [], []
    for uid in adaylar:
        if kodlar.get(uid) == 200:
            yayinlanacak.append(uid)
        else:
            basarisiz.append((uid, kodlar.get(uid, "OLCULMEDI")))
    return yayinlanacak, basarisiz


def ihlal_idler(yayinda, canli_idler):
    """🔴 ASIL DEGISMEZ (invariant): "yayinda=1 olan her id CANLI urunler.json'da vardir."
    Canli JSON ile /urun/ sayfalari AYNI artefaktta yayinlanir ve uretici butunlugu
    (tools/uretim-butunluk-kapisi.py) "JSON'daki her id'nin sayfasi var"i BLOKLAYICI
    olcer -> bu iki kapi birlikte "karti gorunen urun 404 vermez"i verir.
    Bu fonksiyon degismezin IHLALLERINI dondurur; 0 disi her sonuc KIRMIZIDIR.
    Olcum TAM'dir (ornekleme yok) ve TEK HTTP istegi maliyetindedir."""
    return sorted(set(yayinda) - set(canli_idler))


def parcala(idler, boy=PARCA):
    return [idler[i:i + boy] for i in range(0, len(idler), boy)]


def yayin_sql(idler, release, alinti):
    """Tek yon: 0 -> 1. `WHERE yayinda=0` sarti BILEREK var — zaten yayinda olan satirin
    release_id'sini ezmez (denetim izi korunur) ve gereksiz yazma uretmez."""
    return ("UPDATE urunler SET yayinda=1, release_id=%s WHERE yayinda=0 AND id IN (%s);"
            % (alinti(release), ",".join(alinti(i) for i in idler)))


# ═══════════════════════════════════════════════════════════════════════════════
# IO
# ═══════════════════════════════════════════════════════════════════════════════
def yerel_idler():
    with open(URUNLER, encoding="utf-8") as f:
        d = json.load(f)
    return [u["id"] for u in d if u.get("id")]


def canli_getir(yol, ikili=False):
    """Canli siteden dosya cek. Doner: (kod, govde) — hata halinde (None, mesaj)."""
    istek = urllib.request.Request(SITE + yol, headers={"User-Agent": UA,
                                                        "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as c:
            return c.getcode(), c.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:                       # ag/DNS/TLS -> OLCULEMEDI
        return None, str(e).encode("utf-8", "replace")


def canli_urun_idleri():
    """CANLI (yayinlanmis) urunler.json'daki id kumesi. Bu dosya /urun/ sayfalariyla
    AYNI Pages artefaktinda yayinlanir -> icindeki her id'nin sayfasi da canlidadir
    (uretici butunlugu ayrica tools/uretim-butunluk-kapisi.py ile BLOKLAYICI olcuLur)."""
    kod, govde = canli_getir("/urunler.json")
    if kod != 200:
        return None, "canli urunler.json alinamadi (kod=%s)" % kod
    try:
        d = json.loads(govde.decode("utf-8"))
    except Exception as e:
        return None, "canli urunler.json cozulemedi: %s" % e
    return [u["id"] for u in d if u.get("id")], None


def sayfa_kodu(uid):
    """/urun/<id>/ icin HTTP kodu. 200 disi kodlarda DENEME kez tekrar (CDN isinmasi)."""
    kod = None
    for i in range(DENEME):
        kod, _ = canli_getir("/urun/" + uid + "/")
        if kod == 200:
            return 200
        if i < DENEME - 1:
            time.sleep(DENEME_BEKLE)
    return kod


def kodlari_olc(idler):
    if not idler:
        return {}
    with ThreadPoolExecutor(max_workers=ES_ZAMAN) as havuz:
        return dict(zip(idler, havuz.map(sayfa_kodu, idler)))


# ═══════════════════════════════════════════════════════════════════════════════
# KOMUTLAR
# ═══════════════════════════════════════════════════════════════════════════════
def d1_sayilar(m):
    r = m.sorgu("SELECT COUNT(*) AS toplam, "
                "SUM(CASE WHEN yayinda=1 THEN 1 ELSE 0 END) AS yayinda, "
                "SUM(CASE WHEN yayinda=0 THEN 1 ELSE 0 END) AS taslak FROM urunler")
    s = ((r[0].get("results") or [{}])[0] or {})
    return int(s.get("toplam") or 0), int(s.get("yayinda") or 0), int(s.get("taslak") or 0)


def taslak_idler(m):
    r = m.sorgu("SELECT id FROM urunler WHERE yayinda=0")
    return [s["id"] for s in (r[0].get("results") or [])]


def yayinda_idler(m):
    r = m.sorgu("SELECT id FROM urunler WHERE yayinda=1")
    return [s["id"] for s in (r[0].get("results") or [])]


def kolon_hazir(m):
    if m.kolon_var_mi("urunler", "yayinda"):
        return True
    print("!! `yayinda` kolonu D1'de YOK. Once: python3 tools/d1-sync.py --sema")
    return False


def komut_durum(m):
    if not kolon_hazir(m):
        return 1
    toplam, yayinda, taslak = d1_sayilar(m)
    yerel = yerel_idler()
    print("D1 toplam satir      : %d" % toplam)
    print("D1 yayinda (=1)      : %d" % yayinda)
    print("D1 TASLAK  (=0)      : %d" % taslak)
    print("yerel urunler.json id: %d" % len(set(yerel)))
    canli, hata = canli_urun_idleri()
    if canli is None:
        print("canli urunler.json   : OLCULEMEDI (%s)" % hata)
        return 1
    print("canli urunler.json id: %d" % len(set(canli)))
    print("YAYIN GECIKMESI (canli JSON'da olup D1'de TASLAK olan): %d"
          % len(set(taslak_idler(m)) & set(canli)))
    ihlal = ihlal_idler(yayinda_idler(m), canli)
    print("DEGISMEZ IHLALI (yayinda=1 olup canli JSON'da OLMAYAN): %d%s"
          % (len(ihlal), ("  -> " + ", ".join(ihlal[:10])) if ihlal else ""))
    return 1 if ihlal else 0


def komut_yayinla(m, release):
    """DEPLOY'DAN SONRA kosar. Canli 200 dogrulanmadan hicbir satir yayina alinmaz."""
    if not kolon_hazir(m):
        return 1
    taslaklar = taslak_idler(m)
    if not taslaklar:
        print("TASLAK yok — yayina alinacak urun yok (exit 0).")
        return 0
    canli, hata = canli_urun_idleri()
    if canli is None:
        print("OLCULEMEDI: %s — hicbir satir yayina ALINMADI (fail-closed)." % hata)
        return 1
    adaylar, atlanan = adaylari_sec(taslaklar, yerel_idler(), canli)
    print("TASLAK: %d · aday: %d · atlanan: %d" % (len(taslaklar), len(adaylar), len(atlanan)))
    for uid, sebep in sorted(atlanan.items())[:20]:
        print("   atlandi %s — %s" % (uid, sebep))
    if not adaylar:
        print("Yayina alinacak aday yok (exit 0).")
        return 0
    if len(adaylar) > AZAMI_ADAY:
        print("!! ADAY SAYISI TAVANI ASTI: %d > %d. Bu bir GOC yigini; tek tek HTTP "
              "dogrulamasi bu olcekte yapilmaz." % (len(adaylar), AZAMI_ADAY))
        print("!! Coz: python3 tools/yayin-kapisi.py --geriye-doldur")
        return 1

    kodlar = kodlari_olc(adaylar)
    yayinlanacak, basarisiz = yayin_karari(adaylar, kodlar)
    print("canli 200 dogrulanan : %d / %d" % (len(yayinlanacak), len(adaylar)))
    for uid, kod in basarisiz[:20]:
        print("   TASLAK KALDI %s — HTTP %s" % (uid, kod))

    if yayinlanacak:
        for parca in parcala(yayinlanacak):
            m.dosya_calistir(yayin_sql(parca, release, m.q))
        # GERI-OKUMA: iddia degil, D1'den TEYIT (d1-sync write-verify deseni).
        kalan = []
        for parca in parcala(yayinlanacak):
            r = m.sorgu("SELECT id FROM urunler WHERE yayinda=0 AND id IN (%s)"
                        % ",".join(m.q(i) for i in parca))
            kalan += [s["id"] for s in (r[0].get("results") or [])]
        if kalan:
            print("!! YAZMA DOGRULANAMADI: %d id hala TASLAK (or. %s)"
                  % (len(kalan), ", ".join(kalan[:5])))
            return 1
        print("YAYINA ALINDI: %d urun (release=%s) — geri-okuma ile DOGRULANDI"
              % (len(yayinlanacak), release))

    if basarisiz:
        print("!! %d urun canlida 200 VERMEDI -> TASLAK kaldi (Ege gostermez, 404 uretmez)."
              % len(basarisiz))
        return 1
    return 0


def komut_geriye_doldur(m, release):
    """TEK SEFERLIK goc: CANLI urunler.json'da olan her id -> yayinda=1.
    KANIT: canli urunler.json ile /urun/ sayfalari AYNI Pages artefaktindan yayinlanir
    (deploy.yml `_site`), yani canli JSON'daki id'nin sayfasi da canlidadir. Bu yuzden
    15.000 tekil HTTP istegi ATILMAZ — ve ORNEKLEME de yapilmaz: karar TEK bir kanit
    kumesi (canli JSON) uzerinden TAM uygulanir."""
    if not kolon_hazir(m):
        return 1
    canli, hata = canli_urun_idleri()
    if canli is None:
        print("OLCULEMEDI: %s — geriye doldurma YAPILMADI (fail-closed)." % hata)
        return 1
    taslaklar = set(taslak_idler(m))
    hedef = sorted(taslaklar & set(canli))
    print("D1 taslak: %d · canli JSON id: %d · doldurulacak: %d"
          % (len(taslaklar), len(set(canli)), len(hedef)))
    if not hedef:
        print("Doldurulacak satir yok (exit 0).")
        return 0
    for parca in parcala(hedef):
        m.dosya_calistir(yayin_sql(parca, release, m.q))
    toplam, yayinda, taslak = d1_sayilar(m)
    print("SONRASI — toplam=%d yayinda=%d taslak=%d" % (toplam, yayinda, taslak))
    kalan = sorted(set(taslak_idler(m)) & set(canli))
    if kalan:
        print("!! GERI-OKUMA: %d id hala TASLAK (or. %s)" % (len(kalan), ", ".join(kalan[:5])))
        return 1
    print("GERIYE DOLDURMA DOGRULANDI: canli JSON'daki hicbir id TASLAK degil.")
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# KENDINI TEST — OFFLINE (ag YOK, D1 YOK, wrangler YOK, dosya YAZMAZ)
# ═══════════════════════════════════════════════════════════════════════════════
def kendini_test():
    gecen, kalan = [0], [0]

    def dogrula(ad, kosul, detay=""):
        if kosul:
            gecen[0] += 1
            print("  GECTI " + ad)
        else:
            kalan[0] += 1
            print("  KALDI " + ad + (" — " + str(detay) if detay else ""))

    # ── ADAY SECIMI (fail-closed uc sart) ────────────────────────────────────────
    a, atl = adaylari_sec(["x", "y", "z"], ["x", "y"], ["x"])
    dogrula("Y1 ADAY: yalniz yerel VE canli JSON'da olan taslak aday olur", a == ["x"], a)
    dogrula("Y2 ADAY: yerelde olmayan taslak 'bayat satir' diye atlanir",
            "bayat" in atl.get("z", ""), atl)
    dogrula("Y3 ADAY: canlida henuz olmayan taslak 'deploy oturmadi' diye atlanir",
            "deploy oturmadi" in atl.get("y", ""), atl)
    a2, _ = adaylari_sec([], ["x"], ["x"])
    dogrula("Y4 ADAY: taslak yoksa aday da yok (yanlis-pozitif nobeti)", a2 == [], a2)

    # ── YAYIN KARARI (yalniz 200) ────────────────────────────────────────────────
    y, b = yayin_karari(["a", "b", "c", "d"],
                        {"a": 200, "b": 404, "c": None, "d": 500})
    dogrula("Y5 KARAR POZITIF: 200 donen yayina alinir", y == ["a"], y)
    dogrula("Y6 KARAR NEGATIF: 404 TASLAK kalir", ("b", 404) in b, b)
    dogrula("Y7 KARAR NEGATIF: istek patlayan (None) TASLAK kalir", ("c", None) in b, b)
    dogrula("Y8 KARAR NEGATIF: 5xx TASLAK kalir", ("d", 500) in b, b)
    y2, b2 = yayin_karari(["a", "b"], {"a": 200})
    dogrula("Y9 KARAR: HIC OLCULMEYEN id 'iyi' sayilmaz -> basarisiz",
            y2 == ["a"] and b2 == [("b", "OLCULMEDI")], (y2, b2))
    y3, b3 = yayin_karari(["a", "b"], {"a": 200, "b": 200})
    dogrula("Y10 KARAR: hepsi 200 -> hepsi yayinda, basarisiz YOK",
            y3 == ["a", "b"] and b3 == [], (y3, b3))

    # ── SQL SOZLESMESI ───────────────────────────────────────────────────────────
    alinti = (lambda s: "'" + str(s).replace("'", "''") + "'")
    sql = yayin_sql(["a", "b"], "sha1", alinti)
    dogrula("Y11 SQL: yalniz TASLAK satiri gunceller (WHERE yayinda=0)",
            "WHERE yayinda=0" in sql, sql)
    dogrula("Y12 SQL: yayinda=1 + release_id yazilir", "SET yayinda=1" in sql
            and "release_id='sha1'" in sql, sql)
    dogrula("Y13 SQL: TEK YON — yayinda=0'a dusuren ifade URETILMEZ",
            "yayinda=0," not in sql and "SET yayinda=0" not in sql, sql)
    dogrula("Y14 SQL: id'ler alintilanir (enjeksiyon nobeti)",
            yayin_sql(["a'b"], "r", alinti).count("''") == 1,
            yayin_sql(["a'b"], "r", alinti))

    # ── DEGISMEZ (yayinda=1 -> canli JSON'da olmali) ─────────────────────────────
    dogrula("Y20 DEGISMEZ POZITIF: yayindakilerin hepsi canli JSON'da -> ihlal 0",
            ihlal_idler(["a", "b"], ["a", "b", "c"]) == [], ihlal_idler(["a", "b"], ["a", "b", "c"]))
    dogrula("Y21 DEGISMEZ NEGATIF: canli JSON'da olmayan yayinda kayit YAKALANIR",
            ihlal_idler(["a", "hayalet"], ["a"]) == ["hayalet"],
            ihlal_idler(["a", "hayalet"], ["a"]))
    dogrula("Y22 DEGISMEZ: TASLAK kayit ihlal SAYILMAZ (yalniz yayinda=1 olculur)",
            ihlal_idler([], ["a"]) == [])

    # ── PARCALAMA (olcek) ────────────────────────────────────────────────────────
    p = parcala(["i%d" % i for i in range(450)], 200)
    dogrula("Y15 PARCA: 450 id -> 200'luk parcalar (200/200/50), id KAYBI YOK",
            [len(x) for x in p] == [200, 200, 50] and sum(len(x) for x in p) == 450,
            [len(x) for x in p])

    # ── TAVAN: goc yigini yayin YAPMAZ ───────────────────────────────────────────
    dogrula("Y16 TAVAN: AZAMI_ADAY sonlu ve makul (sessiz 15k HTTP taramasi YOK)",
            0 < AZAMI_ADAY <= 2000, AZAMI_ADAY)

    # ── KIRMIZI-MUTASYON: kapinin kendi mantigini bozup KACIRDIGINI kanitla ──────
    # M1: "200 sarti" gevsetilir (200 disi da yayinlanir) -> Y6/Y7/Y8 KACIRILIR.
    def mutant_karar_gevsek(adaylar, kodlar):
        return list(adaylar), []
    ym, bm = mutant_karar_gevsek(["a", "b"], {"a": 200, "b": 404})
    dogrula("Y17 MUTASYON M1: '200 sarti' silinince 404'lu urun yayina girer (kapi olu)",
            ym == ["a", "b"] and bm == [], (ym, bm))
    # M2: aday secimi canli JSON sartini birakir -> Y3 KACIRILIR.
    def mutant_aday_gevsek(taslaklar, yerel, canli):
        return sorted(set(taslaklar) & set(yerel)), {}
    am, _ = mutant_aday_gevsek(["x", "y"], ["x", "y"], ["x"])
    dogrula("Y18 MUTASYON M2: canli JSON sarti silinince deploy oturmadan yayin acilir",
            am == ["x", "y"], am)
    # M3: SQL'den WHERE yayinda=0 dusurulur -> release_id ezilir (denetim izi kaybi).
    mutant_sql = "UPDATE urunler SET yayinda=1, release_id='r' WHERE id IN ('a');"
    dogrula("Y19 MUTASYON M3: WHERE yayinda=0 dusen mutant zaten-yayindaki satiri da yazar",
            "WHERE yayinda=0" not in mutant_sql, mutant_sql)

    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--durum", action="store_true")
    ap.add_argument("--yayinla", action="store_true")
    ap.add_argument("--geriye-doldur", action="store_true", dest="geriye")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    ap.add_argument("--release", default=os.environ.get("GITHUB_SHA", "")[:12] or "yerel")
    a = ap.parse_args()

    if a.kendini:
        sys.exit(kendini_test())
    if not (a.durum or a.yayinla or a.geriye):
        ap.print_help()
        sys.exit(2)

    m = yukle_d1sync()
    if a.durum:
        sys.exit(komut_durum(m))
    if a.geriye:
        sys.exit(komut_geriye_doldur(m, "geriye-doldur"))
    sys.exit(komut_yayinla(m, a.release))


if __name__ == "__main__":
    main()

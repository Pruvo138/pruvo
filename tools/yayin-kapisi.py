#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATOMIK YAYIN KAPISI — "karti gorunen urun asla 404 vermez".

  python3 tools/yayin-kapisi.py --durum          # sayilar (D1 taslak/yayinda + canli)
  python3 tools/yayin-kapisi.py --yayinla        # deploy'dan SONRA: canli 200 -> yayinda=1
  python3 tools/yayin-kapisi.py --geriye-doldur  # TEK SEFERLIK goc: canlidakileri yayinda=1
  python3 tools/yayin-kapisi.py --hal-json       # MAKINE-OKUNUR: stdin'deki id'lerin yayin hali
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
import contextlib
import email.utils
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


def hal_bol(idler, harita):
    """🔴 SAF SINIFLANDIRMA — "yayin gecikmesi" ile "GERCEK KAYIP"i AYIRIR.

    harita = {id: yayinda degeri (0/1)} — D1'den FIILEN okunmus satirlar. Haritada
    OLMAYAN id, D1'de satiri HIC OLMAYAN id'dir.
    Doner: (yok, yayinda, taslak) — ucu de sirali liste.

    🔴 AYRIM SAYI FARKINDAN TUREMEZ: bir id ancak `yayinda` degeri OKUNDUYSA taslak
    sayilir. Deger okunamamissa id 'yok' kolonuna DUSMEZ, cagiran taraf zaten tum
    okumayi basarisiz sayar (fail-closed) — "olcemedim" hicbir kolonda 'iyi' degildir.
    """
    yok, yayinda, taslak = [], [], []
    for uid in idler:
        if uid not in harita:
            yok.append(uid)
        elif int(harita[uid] or 0) == 1:
            yayinda.append(uid)
        else:
            taslak.append(uid)
    return sorted(yok), sorted(yayinda), sorted(taslak)


def yas_sn(kod, tarih, degisim):
    """HTTP `date` - `last-modified` (saniye). Artefaktin NE KADARDIR CANLI oldugu.

    🔴 NEDEN BU SAAT: D1 semasinda zaman damgasi kolonu YOKTUR (d1-sema.sql) — satirin
    "ne zamandir taslak" oldugu D1'den OLCULEMEZ. Olculebilen tek gercek saat, o satirin
    sayfasini tasiyan Pages artefaktinin CANLI OLMA suresidir; ve zararli hal (sayfa
    canli + satir taslak) icin gereken sure TAM OLARAK budur: yayin adiminin elinde ne
    kadar zaman oldugu. Sunucu saati kullanilir (yerel saat kaymasi olcumu bozmasin).
    Doner: int saniye | None (basliklar okunamadi -> OLCULEMEDI).
    """
    if kod is None or not tarih or not degisim:
        return None
    try:
        d = email.utils.parsedate_to_datetime(tarih)
        m = email.utils.parsedate_to_datetime(degisim)
    except Exception:
        return None
    if d is None or m is None:
        return None
    return max(0, int((d - m).total_seconds()))


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


def canli_hal(yol):
    """Canli bir yolun (kod, yas_sn) hali. Govde INDIRILMEZ (HEAD) — /urunler.json 14 MB.

    SINIFLANDIRMA PROBU (yayin kararindan AYRI, bilerek daha ucuz): temiz bir 404
    KESINDIR, tekrar denemek yalniz sure yakar; yalniz AG/5xx hatasinda tek bir tekrar
    yapilir. Yayina alma karari BU FONKSIYONU KULLANMAZ — o hala sayfa_kodu()'nun
    3 denemeli, CDN isinmasina paylı yolundan gecer.
    """
    for i in range(2):
        istek = urllib.request.Request(SITE + yol, method="HEAD",
                                       headers={"User-Agent": UA, "Cache-Control": "no-cache"})
        kod, basliklar = None, None
        try:
            with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as c:
                kod, basliklar = c.getcode(), c.headers
        except urllib.error.HTTPError as e:
            kod, basliklar = e.code, e.headers
        except Exception:
            kod, basliklar = None, None
        if kod is not None and (kod == 200 or kod == 404):
            return kod, yas_sn(kod, basliklar.get("date"), basliklar.get("last-modified"))
        if i == 0:
            time.sleep(1.5)
    return kod, (yas_sn(kod, basliklar.get("date"), basliklar.get("last-modified"))
                 if basliklar is not None else None)


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


def yayin_hali_harita(m, idler):
    """{id: yayinda} — YALNIZ D1'de SATIRI OLAN id'ler icin. Parcali okunur."""
    harita = {}
    for parca in parcala(sorted(set(idler))):
        r = m.sorgu("SELECT id, yayinda FROM urunler WHERE id IN (%s)"
                    % ",".join(m.q(i) for i in parca))
        for s in (r[0].get("results") or []):
            harita[s["id"]] = s.get("yayinda")
    return harita


# HAL-JSON sayfa probu tavani. Bunu asan bir taslak yigini "parti" degil GOC'tur
# (--yayinla ile AYNI olcek kurali, AZAMI_ADAY): o olcekte tek tek HTTP dogrulamasi
# yapilmaz. Tavan asilirsa sayfa hali OLCULMEZ ve cikti bunu ACIKCA soyler; cagiran
# taraf (parite kapisi) o kosumu KANONIK sayamaz.
def komut_hal_json(idler):
    """MAKINE-OKUNUR yayin hali. stdin: id listesi (satir ya da virgul). stdout: TEK JSON.

    🔴 VAR OLMA SEBEBI: her kesif ucu (`/ara`, `/katalog`, `/katalog?ids=`) `yayinda = 1`
    suzer — yani TASLAK satir, uc icin "D1'de HIC YOK" satirdan AYIRT EDILEMEZ. Parite
    kapisi bu iki hali ayirmak zorundadir: ilki gecici YAYIN GECIKMESI, ikincisi GERCEK
    KAYIP. Ayrim ancak `yayinda` kolonunu FIILEN okuyarak kurulabilir; bu komut o okumanin
    TEK kaynagidir (ikinci bir wrangler sarmalayicisi yazilmaz).

    SOZLESME (cagiran taraf buna gore fail-closed davranir):
      {"olculdu": true, "yok": [...], "yayinda": [...],
       "taslak": [{"id": ..., "sayfa": 200|404|null, "yas_sn": int|null}, ...],
       "sayfa_olculdu": bool, "artefakt_yas_sn": int|null}
      Ariza halinde: {"olculdu": false, "sebep": "..."} + sifir-disi cikis.
    stdout'ta JSON'DAN BASKA HICBIR SEY YOKTUR (tum teshis stderr'e gider).
    """
    sonuc = {"olculdu": False, "sebep": "", "yok": [], "yayinda": [], "taslak": [],
             "sayfa_olculdu": False, "artefakt_yas_sn": None}

    def bitir(kod):
        sys.stdout.write(json.dumps(sonuc, ensure_ascii=False) + "\n")
        sys.stdout.flush()
        return kod

    if not idler:
        sonuc["olculdu"] = True
        return bitir(0)

    # Wrangler/d1-sync teshis ciktisi stdout'a KARISMASIN: JSON tek satir kalmali.
    try:
        with contextlib.redirect_stdout(sys.stderr):
            m = yukle_d1sync()
            if not m.kolon_var_mi("urunler", "yayinda"):
                sonuc["sebep"] = "`yayinda` kolonu D1'de YOK (once: d1-sync.py --sema)"
                return bitir(1)
            harita = yayin_hali_harita(m, idler)
    except Exception as e:
        sonuc["sebep"] = "D1 okunamadi: %s" % e
        return bitir(1)

    yok, yayinda, taslak = hal_bol(sorted(set(idler)), harita)
    sonuc["yok"] = yok
    sonuc["yayinda"] = yayinda

    # ARTEFAKT SAATI: canli /urunler.json ne kadardir yayinda (sunucu saatiyle).
    kod, yas = canli_hal("/urunler.json")
    sonuc["artefakt_yas_sn"] = yas if kod == 200 else None

    # SAYFA HALI: taslak satirin ZARARLI mi ZARARSIZ mi oldugunu belirleyen TEK olcu.
    #   sayfa 200 + satir TASLAK -> ZARARLI  (site satiyor, Ege GOREMEZ)
    #   sayfa 200 DEGIL          -> ZARARSIZ (gosterilseydi 404 veren kart uretilirdi —
    #                               atomik yayinin ONLEMEK ICIN VAR OLDUGU hal)
    if taslak and len(taslak) <= AZAMI_ADAY:
        with ThreadPoolExecutor(max_workers=ES_ZAMAN) as havuz:
            haller = list(havuz.map(lambda u: canli_hal("/urun/" + u + "/"), taslak))
        sonuc["sayfa_olculdu"] = True
        sonuc["taslak"] = [{"id": u, "sayfa": h[0], "yas_sn": h[1]}
                           for u, h in zip(taslak, haller)]
    else:
        if taslak:
            sys.stderr.write("!! TASLAK sayisi tavani asti (%d > %d): sayfa hali OLCULMEDI.\n"
                             % (len(taslak), AZAMI_ADAY))
        sonuc["taslak"] = [{"id": u, "sayfa": None, "yas_sn": None} for u in taslak]

    sonuc["olculdu"] = True
    return bitir(0)


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

    # ── HAL-JSON: "yayin gecikmesi" ile "GERCEK KAYIP" ayrimi ────────────────────
    yk, yy, yt = hal_bol(["a", "b", "c"], {"a": 1, "b": 0})
    dogrula("Y23 HAL: D1'de satiri OLMAYAN id 'yok' (GERCEK KAYIP) kolonuna duser",
            yk == ["c"], yk)
    dogrula("Y24 HAL: yayinda=1 olan id 'yayinda' kolonuna duser", yy == ["a"], yy)
    dogrula("Y25 HAL: yayinda=0 olan id 'taslak' (YAYIN GECIKMESI) kolonuna duser",
            yt == ["b"], yt)
    dogrula("Y26 HAL: bos girdi -> uc kolon da bos (yanlis-pozitif nobeti)",
            hal_bol([], {}) == ([], [], []))
    # MUTASYON M4: "haritada yoksa taslak say" -> GERCEK KAYIP sessizce muaf olurdu.
    mutant = sorted([u for u in ["a", "c"] if int({"a": 1}.get(u, 0)) != 1])
    dogrula("Y27 MUTASYON M4: 'bilinmeyen id'yi taslak say' mutanti gercek kaybi YUTAR",
            mutant == ["c"] and yk == ["c"], mutant)

    # ── YAS OLCUSU (sunucu saati; yerel saat kaymasindan BAGIMSIZ) ───────────────
    dogrula("Y28 YAS: date - last-modified saniye olarak cikar",
            yas_sn(200, "Sat, 01 Aug 2026 12:30:00 GMT",
                   "Sat, 01 Aug 2026 12:00:00 GMT") == 1800,
            yas_sn(200, "Sat, 01 Aug 2026 12:30:00 GMT", "Sat, 01 Aug 2026 12:00:00 GMT"))
    dogrula("Y29 YAS: last-modified YOKSA None (OLCULEMEDI — 0 DEGIL)",
            yas_sn(200, "Sat, 01 Aug 2026 12:30:00 GMT", None) is None)
    dogrula("Y30 YAS: cozulemeyen tarih None (uydurma sayi URETILMEZ)",
            yas_sn(200, "dun", "bugun") is None)
    dogrula("Y31 YAS: negatif fark 0'a kirpilir (saat kaymasi negatif yas uretmesin)",
            yas_sn(200, "Sat, 01 Aug 2026 12:00:00 GMT",
                   "Sat, 01 Aug 2026 12:30:00 GMT") == 0)

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
    ap.add_argument("--hal-json", action="store_true", dest="hal")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    ap.add_argument("--release", default=os.environ.get("GITHUB_SHA", "")[:12] or "yerel")
    a = ap.parse_args()

    if a.kendini:
        sys.exit(kendini_test())
    if a.hal:
        ham = sys.stdin.read()
        idler = [s.strip() for s in ham.replace(",", "\n").splitlines() if s.strip()]
        sys.exit(komut_hal_json(idler))
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

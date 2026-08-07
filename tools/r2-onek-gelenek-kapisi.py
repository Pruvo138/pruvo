#!/usr/bin/env python3
"""r2-onek-gelenek-kapisi.py — R2 anahtar ONEK GELENEK kapisi (Cults3D + bilinmeyen-onek + ikiz tanim).

NEDEN (7 Agu 2026 olcumu): tools/r2_anahtar.py'nin ONEKLER tablosunda Cults3D EKSIKTI ->
gkey("Cults3D", slug) BILINMEYEN_ONEK'e ("x") dusuyordu. Canli katalogda 1 kayit
("raymarine-st60-plus-masa-ustu-montaj-kutusu" -> "xraymarine-st60-desk-mount") tam bu
bosluktan yayina girdi. Ayrica AYNI platformda IKI anahtar gelenegi olustu: c3d+SLUG
(1047 kayit, BASKIN) ve c3d+SAYISAL-ID (15 kayit, tarihsel azinlik).

🔴 BAGIMSIZ CURUTME (7 Agu 2026) BU KAPININ ILK SURUMUNU KIRDI — bu surum onarimidir:
  1. Kapi ASIL VEKTORU (BILINMEYEN_ONEK "x") HIC TARAMIYORDU: kusurun kendisi tarama
     yuzeyinin disindaydi. -> B2 ekseni eklendi. BUGUN KIRMIZI YANAR (1 canli kayit);
     bu DOGRU davranistir, veri MaCiT duzlemidir, kapi onu DUZELTMEZ, GORUR.
  2. Kapi kendi YUZEYINI olcmuyordu ("tarama yuzeyi daraltma" + "iddia atlama + sayac
     sabitleme" mutantlari SAG KALMISTI). -> taranan kayit/anahtar sayisi + kosan iddia
     sayisi + IDDIA_TABANI her kosumda BASILIR; iddia sayisi tabandan duserse kapi KENDI
     KENDINI kirmizi yakar ([[kapi-yan-etkisi-gizli-onkosul]], [[mutasyon-kaniti-yeniden-uretilebilir]]).
  3. Muafiyet URUN-ID/BASLIK eksenindeydi -> basligi degisen muaf kayit kapiyi kirmizi
     yakiyor (drift), SILINEN muaf kayit ise sessizce tolere ediliyordu. -> muafiyet artik
     R2 ANAHTARININ KENDISINE bagli ve beklenen kume ile CANLIDA BULUNAN kume AYRISIRSA
     kapi bunu basar ([[envanter-drift-parti-basina]]).
  4. Ikiz-tanim kontrolu KENDI FIKSTURUNU yakaliyordu (tautoloji); GERCEK ikiz
     (~/dev/pruvo-hasat/olcum/hasat_ortak.PLATFORMLAR) yuzey disindaydi ve CGTrader'da
     BUGUN AYRISMIS ("cgt-" vs "cgt"). -> E3/E4 gercek kaynagi okur, okuyamazsa
     FAIL-CLOSED kirmizi yakar ([[ikiz-tanim-sessiz-ayrisma]], ["olculdu" diyen hukum kanit ister]).

Kosum (ag yok, urunler.json'u SALT-OKUNUR acar, hicbir dosyaya YAZMAZ):
    python3 tools/r2-onek-gelenek-kapisi.py

Ortam degiskenleri (mutasyon surucusu tools/r2-onek-mutasyon.py icin; uretimde GEREKMEZ):
    PRUVO_ROOT          — tools/ kokunu ezer (mutant kopyalar gecici dizine yazilir)
    PRUVO_URUNLER_JSON  — katalog yolunu ezer (6MB veri her mutant icin kopyalanmaz)
    PRUVO_HASAT_ORTAK   — gercek ikiz kaynagi (hasat_ortak.py) yolunu ezer

IDDIALAR (her biri kisa, SABIT bir kimlikle basar; mutasyon surucusu kimlikleri karsilastirir):
  A1  ONEKLER["Cults3D"] == BEKLENEN_ONEK_C3D
  B1  canlida MUAFIYET DISINDA sayisal-govdeli c3d anahtari YOK
  B2  canlida BILINMEYEN_ONEK ("x") ile URETILMIS anahtar YOK
      (muafiyet KURALDAN turer: anahtar == urun id'si ise tarihsel BASLIK-turevi anahtardir,
       "x" oneki degildir; liste TUTULMAZ -> drift yok)
  B3  TARAMA YUZEYI tabani: taranan kayit ve c3d anahtar sayisi tabanin ustunde
  B4  SINIFLANDIRICI POZITIF/NEGATIF KONTROL: sayisal-govde tanimi fikstur girdilerinde dogru
  C1  FROZEN_MUAFIYET govdesi TAHRIF EDILMEMIS (len + sha256 sabiti)
  C2  FROZEN_MUAFIYET == canlida FIILEN BULUNAN sayisal-govdeli c3d anahtar kumesi
      (gizli muafiyet eklemek VE muaf kaydin silinmesi burada AYRISMA olarak yanar)
  C3  hash fonksiyonu POZITIF KONTROL: bagimsiz fiksturde bilinen dogru degeri uretir
  D1  gkey() bilinmeyen platformda varsayilan FAIL-CLOSED (raise)
  D2  gkey(..., bilinmeyen_sessiz=True) eski davranisa doner ("x42")
  E1  aktif tools/*.py icinde satir-ici Cults3D anahtar-turetme KOPYASI yok
  E2  gorsel-cakisma-onar.py gkey_for() tek onayli bilinmeyen_sessiz=True'yu tasiyor
  E3  GERCEK ikiz (hasat_ortak.PLATFORMLAR) ile ONEKLER AYRISMAMIS
  E4  GERCEK ikiz kaynagi OKUNDU ve en az BEKLENEN_IKIZ_ASGARI platform ayrıştırıldı

Cikis kodu: 0 = hic kirmizi yok VE iddia sayisi tabandan dusmedi; 1 = aksi.
🔴 BUGUN BEKLENEN HAL: KIRMIZI (B2 + E3) — ikisi de OLCULMUS canli gercekliktir, kapinin
hatasi degildir. Hukum mimarin: veri duzeltmesi MaCiT, onek karari KraL/MaCiT ortak.
"""
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("PRUVO_ROOT") or os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")
URUNLER = os.environ.get("PRUVO_URUNLER_JSON") or os.path.join(ROOT, "urunler.json")

#: gercek ikiz tanim kaynagi (MaCiT deposu). Kapi bu dosyayi OKUR, DEGISTIRMEZ.
HASAT_ORTAK = (os.environ.get("PRUVO_HASAT_ORTAK")
               or "/Users/okan/dev/pruvo-hasat/olcum/hasat_ortak.py")

# ─────────────────────────────────────────────────────────── KAPININ BEKLENTI CAPALARI
# 🔴 Bunlar kapinin KENDI beklentisidir; r2_anahtar'dan TURETILMEZ. Turetilseydi kapi
# "ne varsa o dogrudur" der ve A1/D2 iddialari TOTOLOJIYE donerdi. Ayrismalari A1/D2'de
# ACIKCA olculur -> ikiz sessizce kayamaz ([[ikiz-tanim-sessiz-ayrisma]]).
BEKLENEN_ONEK_C3D = "c3d"
BEKLENEN_ONEK_X = "x"

#: 🔴 TARAMA YUZEYI TABANI — kapinin kac kayda BAKTIGININ alt siniri. Yuzey sessizce
#: kuculurse (mutant/regresyon) butun "ihlal yok" iddialari BOSALIR ve kapi yesil yanar.
#: 7 Agu 2026 olcumu: 21376 kayit · 21346 tekil anahtar · 1047 c3d anahtari.
TARAMA_TABANI_KAYIT = 20000
TARAMA_TABANI_C3D = 1000

#: 🔴 IDDIA TABANI — bu kapinin KOSMASI GEREKEN en az iddia sayisi. Kosum ici sayi sarti;
#: DUSURMEK ancak iddianin neden kaldirildigini yazan AYNI commit'te mesrudur, ARTIS serbest.
IDDIA_TABANI = 14

#: gercek ikizde beklenen asgari platform sayisi (bugun 5: mw/pr/th/cgt/c3d)
BEKLENEN_IKIZ_ASGARI = 5

hatalar = []
_iddialar = []


def sonuc(kimlik, ad, ok, detay=""):
    _iddialar.append((kimlik, ok))
    print("  %-7s %s. %s%s" % ("OK" if ok else "KIRMIZI", kimlik, ad,
                               ("  -> " + str(detay)) if detay else ""))
    if not ok:
        hatalar.append(kimlik)


def _load_r2k():
    yol = os.path.join(TOOLS, "r2_anahtar.py")
    spec = importlib.util.spec_from_file_location("r2_anahtar_kapisi", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


r2k = _load_r2k()

# ──────────────────────────────────────────────── FROZEN_MUAFIYET (ANAHTAR-BAZLI kayitli govde)
# 🔴 EKSEN: R2 ANAHTARININ KENDISI. Ilk surum (urun-id, anahtar) ciftini kilitliyordu; urun
# id'si Turkce BASLIKTAN turedigi icin MaCiT'in rutin bir baslik duzeltmesi kapiyi kirmizi
# yakiyordu (olculdu: D1 drift mutanti). Anahtar ise R2'de DONDURULMUS bir gercektir
# (uzerine yazmak yasak) -> drift kaynagi degildir.
# Bu 15 anahtar 7 Agu 2026 canli olcumunden TURETILDI (elle tahmin DEGIL) ve C2 iddiasi
# her kosumda canlidaki fiili kumeyle KARSILASTIRIR: gizli ekleme de, muaf kaydin silinmesi
# de AYRISMA olarak yanar.
FROZEN_MUAFIYET = [
    "c3d1245377",
    "c3d141214",
    "c3d141217",
    "c3d1427965",
    "c3d1427967",
    "c3d1689729",
    "c3d1831611",
    "c3d225141",
    "c3d2990657",
    "c3d435128",
    "c3d508705",
    "c3d608952",
    "c3d857888",
    "c3d905377",
    "c3d933757",
]
FROZEN_MUAFIYET_BEKLENEN_UZUNLUK = 15
FROZEN_MUAFIYET_BEKLENEN_HASH = \
    "ebcbd155bdaaa9e7c51370ccf0e4d2cd8bb62214bccf06b3465217324c96bd81"

#: hash fonksiyonunun KENDISI icin POZITIF KONTROL fiksturu (C3). Fonksiyon no-op'a
#: cevrilirse (daima beklenen sabiti dondur) C1 sessizce yesil kalirdi — bu fikstur onu yakar.
#: Deger DISARIDA hesaplandi: sha256("alfa\nbeta").
HASH_FIKSTUR = ["alfa", "beta"]
HASH_FIKSTUR_BEKLENEN = \
    "4f2618441a178cd58b83c18aceb3db89873a7df0b5e21def5cebdb8773a21f81"


def _kanonik_hash(anahtarlar):
    """Anahtar listesinin kanonik sha256'si (sirali + newline ile birlestirilmis)."""
    kanon = "\n".join(sorted(anahtarlar))
    return hashlib.sha256(kanon.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────── katalog tarama (TEK yuzey)
ANAHTAR_RE = re.compile(r"/urunler/(.+?)-(\d+)\.jpg$")

_olcum = {"kayit": 0, "anahtar": 0, "c3d": 0, "x": 0, "cgt_tireli": 0, "cgt_tiresiz": 0}


def _sayisal_govde(anahtar, onek=None):
    """anahtar '<onek><yalnizca rakam>' seklinde mi? TEK sinifllandirici — B1/C2 ve B4
    pozitif kontrolu AYNI fonksiyonu kullanir (ayri kopya = ikiz = sessiz ayrisma)."""
    o = BEKLENEN_ONEK_C3D if onek is None else onek
    return bool(re.match(r"^%s\d+$" % re.escape(o), anahtar))


def _katalog_anahtarlari():
    """urunler.json'daki TUM (urun-id, R2-anahtar) ciftleri. Yuzey DARALTILMAZ: butun
    onekler taranir, siniflandirma sonra yapilir (daraltma = sessiz korluk)."""
    if not os.path.exists(URUNLER):
        return None
    urunler = json.load(open(URUNLER, encoding="utf-8"))
    cikti = set()
    for u in urunler:
        if not isinstance(u, dict):
            continue
        _olcum["kayit"] += 1
        pid = u.get("id", "?")
        for g in (u.get("gorseller") or []):
            m = ANAHTAR_RE.search(g)
            if m:
                cikti.add((pid, m.group(1)))
    _olcum["anahtar"] = len(cikti)
    return cikti


# ─────────────────────────────────────────────────────────────────────────────────── A
def test_a(ciftler):
    sonuc("A1", "ONEKLER['Cults3D'] == %r" % BEKLENEN_ONEK_C3D,
          r2k.ONEKLER.get("Cults3D") == BEKLENEN_ONEK_C3D,
          "" if r2k.ONEKLER.get("Cults3D") == BEKLENEN_ONEK_C3D
          else "fiili=%r" % r2k.ONEKLER.get("Cults3D"))


# ─────────────────────────────────────────────────────────────────────────────── B + C
def test_b_c(ciftler):
    c3d_ciftler = sorted((p, a) for p, a in ciftler if a.startswith(BEKLENEN_ONEK_C3D))
    _olcum["c3d"] = len(c3d_ciftler)
    x_ciftler = sorted((p, a) for p, a in ciftler if a.startswith(BEKLENEN_ONEK_X))
    _olcum["x"] = len(x_ciftler)
    _olcum["cgt_tireli"] = sum(1 for _, a in ciftler if a.startswith("cgt-"))
    _olcum["cgt_tiresiz"] = sum(1 for _, a in ciftler
                                if a.startswith("cgt") and not a.startswith("cgt-"))

    bulunan_sayisal = set(a for _, a in c3d_ciftler if _sayisal_govde(a))
    muafiyet = set(FROZEN_MUAFIYET)

    # B1 — muafiyet DISINDA yeni sayisal-id c3d anahtari dogmasin
    yeni = sorted(bulunan_sayisal - muafiyet)
    sonuc("B1", "muafiyet disinda sayisal-govdeli c3d anahtari yok", not yeni,
          ("%d YENI IHLAL: %s" % (len(yeni), ", ".join(yeni[:8]))) if yeni
          else "%d muaf sayisal-id anahtar olculdu" % len(bulunan_sayisal))

    # B2 — 🔴 ASIL VEKTOR: BILINMEYEN_ONEK ("x") ile uretilmis anahtar.
    # KURAL-TABANLI muafiyet (liste DEGIL -> drift yok): anahtar urun id'sinin AYNISI ise
    # bu tarihsel BASLIK-turevi bir anahtardir (adi "x" ile baslayan urun: xbox-, xiaomi-),
    # BILINMEYEN_ONEK urunu degildir. "x" + KAYNAK-SLUG/ID ise gercek kusurdur.
    x_ihlal = sorted((p, a) for p, a in x_ciftler if a != p)
    sonuc("B2", "BILINMEYEN_ONEK ('%s') ile uretilmis anahtar yok" % BEKLENEN_ONEK_X,
          not x_ihlal,
          ("%d IHLAL: %s" % (len(x_ihlal), "; ".join("%s->%s" % (p, a) for p, a in x_ihlal[:8])))
          if x_ihlal else "%d 'x' anahtarin hepsi baslik-turevi (anahtar == urun id)" % len(x_ciftler))

    # B3 — 🔴 KAPI KENDI YUZEYINI OLCER: yuzey sessizce kucultulemez
    yuzey_ok = (_olcum["kayit"] >= TARAMA_TABANI_KAYIT and _olcum["c3d"] >= TARAMA_TABANI_C3D)
    sonuc("B3", "tarama yuzeyi tabanin ustunde (kayit>=%d, c3d>=%d)"
          % (TARAMA_TABANI_KAYIT, TARAMA_TABANI_C3D), yuzey_ok,
          "taranan kayit=%d, c3d anahtar=%d" % (_olcum["kayit"], _olcum["c3d"]))

    # B4 — 🔴 SINIFLANDIRICI POZITIF/NEGATIF KONTROL (B1/C2 ile AYNI fonksiyon).
    # Regex korlestirilirse "ihlal yok" iddiasi BOSALIR; bu fikstur onu ayri bir kimlikle yakar.
    fikstur = [("c3d123456", True), ("c3d1", True), ("c3d0", True),
               ("c3dbazi-slug", False), ("c3d", False), ("c3d12a", False),
               ("th123456", False), ("xc3d123", False)]
    yanlislar = ["%s=>%s(beklenen %s)" % (k, _sayisal_govde(k), b)
                 for k, b in fikstur if _sayisal_govde(k) != b]
    sonuc("B4", "sayisal-govde siniflandiricisi fiksturde dogru (%d girdi)" % len(fikstur),
          not yanlislar, ", ".join(yanlislar))

    # C1 — govde tahrif edilmemis (len + hash sabiti)
    uzunluk_ok = len(FROZEN_MUAFIYET) == FROZEN_MUAFIYET_BEKLENEN_UZUNLUK
    hash_fiili = _kanonik_hash(FROZEN_MUAFIYET)
    hash_ok = hash_fiili == FROZEN_MUAFIYET_BEKLENEN_HASH
    sonuc("C1", "FROZEN_MUAFIYET govdesi tahrif edilmemis (len+sha256)",
          uzunluk_ok and hash_ok,
          "" if (uzunluk_ok and hash_ok) else
          "len=%d (beklenen %d) hash=%s (beklenen %s)"
          % (len(FROZEN_MUAFIYET), FROZEN_MUAFIYET_BEKLENEN_UZUNLUK,
             hash_fiili[:16], FROZEN_MUAFIYET_BEKLENEN_HASH[:16]))

    # C2 — 🔴 BEKLENEN kume ile CANLIDA BULUNAN kume AYRISMASI. Hash'ten BAGIMSIZ eksen:
    # hash fonksiyonu no-op'a cevrilse bile gizli muafiyet burada yanar; muaf kaydin
    # SILINMESI de burada yanar (ilk surumde sessizce tolere ediliyordu).
    fazla = sorted(muafiyet - bulunan_sayisal)   # kayitli ama canlida YOK (silindi/uydurma)
    eksik = sorted(bulunan_sayisal - muafiyet)   # canlida VAR ama kayitli degil (yeni ihlal)
    sonuc("C2", "FROZEN_MUAFIYET == canlida bulunan sayisal-govdeli c3d kumesi",
          not fazla and not eksik,
          "canlida YOK=%s | kayitsiz=%s" % (fazla[:6], eksik[:6]) if (fazla or eksik)
          else "%d anahtar birebir ortusuyor" % len(bulunan_sayisal))

    # C3 — hash fonksiyonunun KENDISI dogru mu (no-op mutantini yakalar)
    fiili = _kanonik_hash(HASH_FIKSTUR)
    sonuc("C3", "hash fonksiyonu bagimsiz fiksturde dogru (pozitif kontrol)",
          fiili == HASH_FIKSTUR_BEKLENEN,
          "" if fiili == HASH_FIKSTUR_BEKLENEN else "fikstur hash=%s (beklenen %s)"
          % (fiili[:16], HASH_FIKSTUR_BEKLENEN[:16]))


# ─────────────────────────────────────────────────────────────────────────────────── D
def test_d(ciftler):
    try:
        r2k.gkey("BuPlatformHicOlmadi", "42")
        sonuc("D1", "bilinmeyen platform varsayilan FAIL-CLOSED", False, "raise etmedi")
    except r2k.BilinmeyenPlatform:
        sonuc("D1", "bilinmeyen platform varsayilan FAIL-CLOSED", True)
    except Exception as e:  # noqa: BLE001
        sonuc("D1", "bilinmeyen platform varsayilan FAIL-CLOSED", False, "yanlis istisna: %r" % e)

    beklenen = BEKLENEN_ONEK_X + "42"
    try:
        a = r2k.gkey("BuPlatformHicOlmadi", "42", bilinmeyen_sessiz=True)
        sonuc("D2", "bilinmeyen_sessiz=True eski davranisa donuyor (%s)" % beklenen,
              a == beklenen, "" if a == beklenen else "uretilen=%r" % a)
    except Exception as e:  # noqa: BLE001
        sonuc("D2", "bilinmeyen_sessiz=True eski davranisa donuyor (%s)" % beklenen,
              False, "raise etti: %r" % e)


# ─────────────────────────────────────────────────────────────────────────────────── E
IKIZ_DESENLERI = [
    re.compile(r'''["']c3d["']\s*\+'''),
    re.compile(r'''\+\s*["']c3d["']'''),
    re.compile(r'''["']Cults3D["']\s*:\s*["']c3d'''),
]
IKIZ_MUAF_DOSYALAR = {"r2_anahtar.py", "r2-anahtar-test.py", "r2-onek-gelenek-kapisi.py",
                      "r2-onek-mutasyon.py"}

#: gercek ikiz tablosunun satir bicimi: "cults3d": {"ad": "Cults3D", "onek": "c3d"}
PLATFORM_SATIR_RE = re.compile(
    r'''["'][a-z0-9_]+["']\s*:\s*\{[^{}]*?["']ad["']\s*:\s*["']([^"']+)["'][^{}]*?'''
    r'''["']onek["']\s*:\s*["']([^"']*)["']''')


def _gercek_ikiz_oku():
    """(platform_adi -> onek, kaynak_yolu) — GERCEK ikiz tanimini kaynaktan ayrıştırır.
    Bulunamazsa ({}, yol) doner; cagiran bunu FAIL-CLOSED kirmizi olarak isler."""
    if not os.path.exists(HASAT_ORTAK):
        return {}, HASAT_ORTAK
    metin = open(HASAT_ORTAK, encoding="utf-8", errors="ignore").read()
    return {ad: onek for ad, onek in PLATFORM_SATIR_RE.findall(metin)}, HASAT_ORTAK


def test_e(ciftler):
    # E1 — aktif tools/ kodunda satir-ici anahtar-turetme kopyasi
    bulunanlar = []
    if os.path.isdir(TOOLS):
        for kok, dizinler, dosyalar in os.walk(TOOLS):
            dizinler[:] = [d for d in dizinler if d != "arsiv"]
            for ad in sorted(dosyalar):
                if not ad.endswith(".py") or ad in IKIZ_MUAF_DOSYALAR:
                    continue
                yol = os.path.join(kok, ad)
                try:
                    metin = open(yol, encoding="utf-8", errors="ignore").read()
                except OSError:
                    continue
                for i, satir in enumerate(metin.splitlines(), 1):
                    if satir.lstrip().startswith("#"):
                        continue
                    if any(d.search(satir) for d in IKIZ_DESENLERI):
                        bulunanlar.append("%s:%d" % (os.path.relpath(yol, TOOLS), i))
    sonuc("E1", "aktif tools/ kodunda satir-ici Cults3D anahtar-turetme kopyasi yok",
          not bulunanlar, "; ".join(bulunanlar[:8]))

    # E2 — gorsel-cakisma-onar.py'nin tek onayli sessiz cagrisi yerinde mi
    onar_yolu = os.path.join(TOOLS, "gorsel-cakisma-onar.py")
    if os.path.exists(onar_yolu):
        metin = open(onar_yolu, encoding="utf-8", errors="ignore").read()
        var = bool(re.search(
            r"r2k\.gkey\(\s*platform\s*,\s*sid\s*,\s*yedek=False\s*,\s*bilinmeyen_sessiz=True\s*\)",
            metin))
        sonuc("E2", "gorsel-cakisma-onar.py gkey_for() bilinmeyen_sessiz=True tasiyor", var)
    else:
        sonuc("E2", "gorsel-cakisma-onar.py gkey_for() bilinmeyen_sessiz=True tasiyor",
              False, "dosya bulunamadi: %s (FAIL-CLOSED)" % onar_yolu)

    # E3 + E4 — 🔴 GERCEK ikiz tanim (fikstur DEGIL): hasat_ortak.PLATFORMLAR <-> ONEKLER
    ikiz, yol = _gercek_ikiz_oku()
    ayrismalar = []
    for ad, onek in sorted(ikiz.items()):
        if ad not in r2k.ONEKLER:
            ayrismalar.append("%s: ikizde '%s', ONEKLER'de YOK" % (ad, onek))
        elif r2k.ONEKLER[ad] != onek:
            ayrismalar.append("%s: ONEKLER='%s' vs ikiz='%s'" % (ad, r2k.ONEKLER[ad], onek))
    if not ikiz:
        # FAIL-CLOSED: "ayrisma yok" hukmu ancak POZITIF tanima izinden turetilebilir.
        sonuc("E3", "gercek ikiz (hasat_ortak.PLATFORMLAR) ile ONEKLER ayrismamis", False,
              "OLCULEMEDI — ikiz kaynagi okunamadi/ayrıştırılamadi: %s" % yol)
    else:
        sonuc("E3", "gercek ikiz (hasat_ortak.PLATFORMLAR) ile ONEKLER ayrismamis",
              not ayrismalar,
              "; ".join(ayrismalar) if ayrismalar else "%d platform birebir" % len(ikiz))
    sonuc("E4", "gercek ikiz kaynagi okundu ve >=%d platform ayrıştırıldı" % BEKLENEN_IKIZ_ASGARI,
          len(ikiz) >= BEKLENEN_IKIZ_ASGARI,
          "ayrıştırılan=%d, kaynak=%s" % (len(ikiz), yol))


# ══════════════════════════════════════════════════════════════════════════════════ kosum
print("r2-onek-gelenek-kapisi — R2 anahtar onek gelenek + ikiz tanim kapisi")
_ciftler = _katalog_anahtarlari()
if _ciftler is None:
    print("KIRMIZI — katalog bulunamadi (FAIL-CLOSED): %s" % URUNLER)
    print("IDDIA: 0 (taban %d)" % IDDIA_TABANI)
    sys.exit(1)

test_a(_ciftler)
test_b_c(_ciftler)
test_d(_ciftler)
test_e(_ciftler)

print("")
print("OLCUM: TARANAN_KAYIT=%d (taban %d) · TARANAN_ANAHTAR=%d · C3D_ANAHTAR=%d (taban %d) · "
      "X_ONEKLI=%d" % (_olcum["kayit"], TARAMA_TABANI_KAYIT, _olcum["anahtar"],
                       _olcum["c3d"], TARAMA_TABANI_C3D, _olcum["x"]))
print("OLCUM: CGT_TIRELI=%d · CGT_TIRESIZ=%d  (ONEKLER['CGTrader']=%r — mimar karari bekliyor)"
      % (_olcum["cgt_tireli"], _olcum["cgt_tiresiz"], r2k.ONEKLER.get("CGTrader")))

_toplam = len(_iddialar)
_taban_dustu = _toplam < IDDIA_TABANI
print("IDDIA: %d (taban %d)%s" % (_toplam, IDDIA_TABANI,
                                  "  🔴 TABAN ALTI — iddia SESSIZCE kayboldu" if _taban_dustu else ""))
print("KIRMIZI_IDDIALAR: %s" % (",".join(hatalar) if hatalar else "-"))
print("SONUC: %s — gecen %d · kalan %d"
      % ("KIRMIZI" if (hatalar or _taban_dustu) else "YESIL", _toplam - len(hatalar), len(hatalar)))
if hatalar or _taban_dustu:
    sys.exit(1)
sys.exit(0)

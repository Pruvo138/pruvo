#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/hafiza-kota-kapisi-test.py — HAFIZA INDEKSI EKSENININ KABUL BATARYASI.

KAPSAM (iki yuzey, TEK tally):
  (A) `tools/hafiza-indeks-arsivle.py` — tavan sahibi + LOSSLESS rotasyon araci
  (B) `tools/defter-kota-kapisi.py`   — UCUNCU EKSEN (HAFIZA_* kovalari)

🔴 AYRI TALLY: bu batarya defter ekseninin (`defter-kota-kapisi.py --kendini-test`)
ve kutu ekseninin sayacina KARISTIRILMAZ. Karisik tally, bir eksenin dusen vakasini
otekinin yesiliyle gizler ([[batarya-kapsam-tabani-sayiyla-civilenir]]).

🔴 FILO DERSI (BaBa, 4 Eyl 2026): bu batarya GERCEK `memory/` agacina TEK BAYT
yazmaz. Butun fiksturler sentetiktir (`tempfile.mkdtemp`), mutantlar YALNIZ IZOLE
KOPYADA kosar, ve batarya sonunda gercek MEMORY.md'nin bayt+mtime'i basta olculen
degerle KARSILASTIRILIR (KONTROL-0). Testte gercek hafiza yoluna yazan/silen tek
satir bile KIRMIZI'dir.

MUTANT TABLOSU — her mutant HEDEF KOLUN ATFIYLA olur:
  M1  tavani SAHIPTEN degil KODA GOMULU kopyadan oku (kapi kolu)
        -> hedef kol: `defter-kota-taban.hafiza_tavan_bayt` turetmesi
  M2  koruma kontrolunu KALDIR (`koruma_sebebi` daima None)
        -> hedef kol: `koruma_sebebi` + dogrula D5/D6
  M3  lossless dogrulamayi DAIMA TRUE yap (`dogrula` daima [] doner)
        -> hedef kol: `dogrula()`; KONTROL cifti ile olculur (bozuk arsiv eki
           dogrulama SAGLAMKEN kirmizi, KALDIRILINCA yesil)
  M4  kapi rc tablosunu TERSINE cevir
        -> hedef kol: `HAFIZA_RC` -> cikis kodu
  M5  su seviyesi yerine TAVANA kadar in (K353 arizasinin ta kendisi)
        -> hedef kol: `planla()` icindeki `hedef_bayt = su_bayt`

CAGRI: python3 tools/hafiza-kota-kapisi-test.py
CIKTI son satirlari:
    VAKA=<gecen>/<toplam> MUTANT=<olen>/<toplam> KONTROL=<YESIL|KIRMIZI>
    DUSEN=<n>
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
ARAC = os.path.join(TOOLS, "hafiza-indeks-arsivle.py")
KAPI = os.path.join(TOOLS, "defter-kota-kapisi.py")

# Izole kopyaya tasinan dosyalar (kapi bunlari yan yana bulmali).
KOPYALANAN = ("hafiza-indeks-arsivle.py", "defter-kota-taban.py",
              "defter-kota-kapisi.py", "serbest_cagrilar.py")

TARIH = "2026-09-05"

sonuclar = []
_gecici = []


def olc(ad, kosul, detay):
    sonuclar.append((ad, bool(kosul), detay))


# ---------------------------------------------------------------------------
# FIKSTUR URETIMI — SENTETIK, gercek hafizaya DOKUNMAZ
# ---------------------------------------------------------------------------
def gecici_dizin(onek):
    d = tempfile.mkdtemp(prefix="hafiza-kota-" + onek + "-")
    _gecici.append(d)
    return d


def indeks_yaz(dizin, bolumler, hedefleri_yarat=True):
    """bolumler: [(bolum_adi, [(etiket, hedef, kuyruk), ...]), ...] -> indeks yolu.

    Hedef `.md` dosyalari (varsa) ARTAN mtime ile yaratilir; boylece aday sirasi
    (eskiden yeniye) DETERMINISTIK olarak dogrulanabilir.
    """
    satirlar = []
    zaman = 1_600_000_000
    for ad, girdiler in bolumler:
        parcalar = []
        for etiket, hedef, kuyruk in girdiler:
            parcalar.append("[%s](%s)%s" % (etiket, hedef, kuyruk))
            if hedefleri_yarat:
                yol = os.path.join(dizin, hedef)
                alt = os.path.dirname(yol)
                if alt and not os.path.isdir(alt):
                    os.makedirs(alt)
                with open(yol, "w", encoding="utf-8") as f:
                    f.write("# %s\n" % etiket)
                os.utime(yol, (zaman, zaman))
                zaman += 60
        satirlar.append("%s: %s" % (ad, ",".join(parcalar)))
    yol = os.path.join(dizin, "MEMORY.md")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n\n".join(satirlar) + "\n")
    return yol


def duz_bolumler(bolum_sayisi, girdi_sayisi, onek="", kuyruk_uzunlugu=28):
    """Sade, TASINABILIR girdilerden olusan bolum listesi."""
    out = []
    n = 0
    for b in range(bolum_sayisi):
        girdiler = []
        for g in range(girdi_sayisi):
            n += 1
            girdiler.append(("%sEtiket %03d" % (onek, n),
                             "hedef-%03d.md" % n,
                             " — " + ("dolgu " * 8)[:kuyruk_uzunlugu].strip()))
        out.append(("Bolum %d" % (b + 1), girdiler))
    return out


def bayt(yol):
    with open(yol, "rb") as f:
        return len(f.read())


def satir(yol):
    with open(yol, "rb") as f:
        return len(f.read().splitlines())


def metin(yol):
    if not os.path.exists(yol):
        return None
    with open(yol, "rb") as f:
        return f.read().decode("utf-8")


def kos(arac, indeks, arsiv=None, ek=(), kuru=False):
    dizin = os.path.dirname(indeks)
    arsiv = arsiv or os.path.join(dizin, "MEMORY-ARSIV.md")
    komut = [sys.executable, arac, "--hafiza", indeks, "--arsiv", arsiv,
             "--kilit", os.path.join(dizin, ".indeks.lock"), "--tarih", TARIH]
    komut.extend(ek)
    if kuru:
        komut.append("--kuru")
    r = subprocess.run(komut, capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout or "") + (r.stderr or ""), arsiv


def jeton(ham, onek):
    for s in ham.splitlines():
        for p in s.split():
            if p.startswith(onek):
                return p[len(onek):]
    return None


def hukum_of(ham):
    for s in ham.splitlines():
        if "HUKUM=" in s:
            return s.split("HUKUM=", 1)[1].split()[0]
    return None


# ---------------------------------------------------------------------------
# IZOLE KOPYA + MUTASYON
# ---------------------------------------------------------------------------
def izole_kopya(onek):
    """<tmp>/tools/ altina arac + bagimliliklarini kopyalar; KOK yolunu doner."""
    kok = gecici_dizin("kopya-" + onek)
    os.makedirs(os.path.join(kok, "tools"))
    for ad in KOPYALANAN:
        shutil.copy2(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    return kok


def yamala(kok, dosya, eski, yeni):
    """Izole kopyada METIN yamasi. Capa BULUNAMAZSA mutant SESSIZ YASAMAZ."""
    yol = os.path.join(kok, "tools", dosya)
    with open(yol, "r", encoding="utf-8") as f:
        ham = f.read()
    if eski not in ham:
        raise AssertionError("MUTANT CAPASI BULUNAMADI (%s): %r" % (dosya, eski[:70]))
    if ham.count(eski) != 1:
        raise AssertionError("MUTANT CAPASI %d KEZ GECIYOR (%s): %r"
                             % (ham.count(eski), dosya, eski[:70]))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(ham.replace(eski, yeni))


def kapi_kos(kok, indeks_yolu):
    """Izole kopyadaki kapinin UCUNCU EKSENINI kosar (yalniz o eksen)."""
    ortam = dict(os.environ)
    ortam["PRUVO_HAFIZA_YOLU"] = indeks_yolu
    r = subprocess.run([sys.executable, os.path.join(kok, "tools",
                                                     "defter-kota-kapisi.py"),
                        "--hafiza-kontrol", kok],
                       capture_output=True, text=True, timeout=300, env=ortam)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ===========================================================================
# KONTROL-0 — GERCEK HAFIZA DOKUNULMAZ (batarya basi olcumu)
# ===========================================================================
_taban_modul = None


def gercek_hafiza_yolu():
    global _taban_modul
    if _taban_modul is None:
        import importlib.util as ilu
        spec = ilu.spec_from_file_location(
            "hafiza_sahip_test", os.path.join(TOOLS, "hafiza-indeks-arsivle.py"))
        mod = ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _taban_modul = mod
    return _taban_modul.HAFIZA_VARSAYILAN


def gercek_imza():
    yol = gercek_hafiza_yolu()
    if not os.path.isfile(yol):
        return None
    st = os.stat(yol)
    return (st.st_size, int(st.st_mtime))


# ===========================================================================
# VAKALAR
# ===========================================================================
def vaka_a():
    """V-A: tavan ustu + tasinabilir VAR -> su seviyesinin ALTINA iner."""
    d = gecici_dizin("va")
    indeks = indeks_yaz(d, duz_bolumler(8, 50))
    once_b = bayt(indeks)
    once_s = satir(indeks)
    rc, ham, arsiv = kos(ARAC, indeks)
    sonra_b = bayt(indeks)
    su = int(jeton(ham, "su_bayt=") or -1)
    tasinan = int(jeton(ham, "tasinan=") or -1)
    olc("V-A tavan ustu + tasinabilir VAR -> TAVAN_BASARILI",
        rc == 0 and hukum_of(ham) == "TAVAN_BASARILI" and once_b > 16384,
        "rc=%d hukum=%s once=%d" % (rc, hukum_of(ham), once_b))
    olc("V-A su seviyesinin ALTINA indi",
        sonra_b <= su and su > 0 and sonra_b < once_b,
        "sonra=%d su=%d once=%d" % (sonra_b, su, once_b))
    olc("V-A lossless dogrulamasi GECTI + arsiv buyudu",
        "lossless_dogrulama=GECTI" in ham and tasinan > 0
        and os.path.isfile(arsiv) and bayt(arsiv) > 0,
        "tasinan=%d arsiv=%d" % (tasinan, bayt(arsiv) if os.path.isfile(arsiv) else -1))
    olc("V-A satir sayisi DEGISMEDI (baslik korumasi)",
        satir(indeks) == once_s, "once=%d sonra=%d" % (once_s, satir(indeks)))
    # ICERIK KORUNDU: tasinan her girdinin etiketi arsivde, hedefi diskte
    ars = metin(arsiv)
    madde = [s[2:] for s in ars.splitlines() if s.startswith("- ")]
    hedefler_var = all(os.path.isfile(os.path.join(d, m.split("](", 1)[1].split(")", 1)[0]))
                       for m in madde)
    olc("V-A icerik korundu: madde sayisi = tasinan, hedefler diskte",
        len(madde) == tasinan and hedefler_var,
        "madde=%d tasinan=%d hedefler_var=%s" % (len(madde), tasinan, hedefler_var))
    # IDEMPOTANS: ikinci kosum artik tavan altinda -> DOLU_NO_OP + bayt bayt AYNI
    onceki = metin(indeks)
    rc2, ham2, _ = kos(ARAC, indeks)
    olc("V-A ikinci kosum DOLU_NO_OP + bayt bayt AYNI",
        rc2 == 0 and hukum_of(ham2) == "DOLU_NO_OP"
        and "TAVAN=DOLU_NO_OP" in ham2 and metin(indeks) == onceki,
        "rc=%d hukum=%s degisti=%s" % (rc2, hukum_of(ham2), metin(indeks) != onceki))
    return d, indeks


def vaka_b():
    """V-B: tavan ustu + TASINABILIR YOK (icerik tukendi) -> fail-loud rc=1."""
    d = gecici_dizin("vb")
    # Hedef `.md` dosyalari YARATILMAZ: bag butunlugu dogrulanamayan girdi
    # TASINMAZ (kural v) ve bu bir KORUMA hali DEGILDIR -> fail-loud beklenir.
    indeks = indeks_yaz(d, duz_bolumler(8, 50), hedefleri_yarat=False)
    once = metin(indeks)
    rc, ham, arsiv = kos(ARAC, indeks)
    olc("V-B tavan ustu + tasinabilir YOK -> TAVAN_FAIL_LOUD rc=1",
        rc == 1 and hukum_of(ham) == "TAVAN_FAIL_LOUD",
        "rc=%d hukum=%s" % (rc, hukum_of(ham)))
    olc("V-B dosya DEGISMEDI (bayt bayt ayni) + arsiv YAZILMADI",
        metin(indeks) == once and not os.path.isfile(arsiv),
        "degisti=%s arsiv_var=%s" % (metin(indeks) != once, os.path.isfile(arsiv)))

    # V-B2: tasinabilir VAR ama YETMIYOR (indirgenemez kutle bolum basliklarinda)
    d2 = gecici_dizin("vb2")
    dev = "Cok uzun bolum basligi " * 400
    bolumler = [(dev + "A", [("Etiket 1", "h-1.md", "")]),
                (dev + "B", [("Etiket 2", "h-2.md", "")])]
    indeks2 = indeks_yaz(d2, bolumler)
    once2 = metin(indeks2)
    rc2, ham2, arsiv2 = kos(ARAC, indeks2)
    olc("V-B2 tasinabilir VAR ama YETMIYOR -> TAVAN_FAIL_LOUD rc=1, YAZILMADI",
        rc2 == 1 and hukum_of(ham2) == "TAVAN_FAIL_LOUD"
        and metin(indeks2) == once2 and not os.path.isfile(arsiv2),
        "rc=%d hukum=%s degisti=%s" % (rc2, hukum_of(ham2), metin(indeks2) != once2))


def vaka_c():
    """V-C: tavan ALTINDA -> DOLU_NO_OP, iki kosum bayt bayt AYNI."""
    d = gecici_dizin("vc")
    indeks = indeks_yaz(d, duz_bolumler(3, 5))
    once = metin(indeks)
    rc1, ham1, arsiv = kos(ARAC, indeks)
    rc2, ham2, _ = kos(ARAC, indeks)
    olc("V-C tavan altinda -> DOLU_NO_OP rc=0 (+ TAVAN=DOLU_NO_OP jetonu)",
        rc1 == 0 and hukum_of(ham1) == "DOLU_NO_OP" and "TAVAN=DOLU_NO_OP" in ham1,
        "rc=%d hukum=%s" % (rc1, hukum_of(ham1)))
    olc("V-C iki kosum da BAYT BAYT AYNI + arsiv acilmadi",
        rc2 == 0 and metin(indeks) == once and not os.path.isfile(arsiv),
        "degisti=%s arsiv_var=%s" % (metin(indeks) != once, os.path.isfile(arsiv)))


def vaka_d():
    """V-D: KORUMALI (🔴 + Acik kuyruk) -> tasinan 0, olculerek basilir."""
    d = gecici_dizin("vd")
    kirmizi = [("🔴 Etiket %03d" % n, "hedef-%03d.md" % n, " — " + "dolgu " * 6)
               for n in range(1, 130)]
    kuyruk = [("Etiket K%03d" % n, "kuyruk-%03d.md" % n, " — " + "dolgu " * 6)
              for n in range(1, 130)]
    indeks = indeks_yaz(d, [("Kapilar", kirmizi), ("Açık kuyruk", kuyruk)])
    once = metin(indeks)
    rc, ham, arsiv = kos(ARAC, indeks)
    olc("V-D korumali indeks tavan ustu -> KORUMA_TUTTU rc=0 tasinabilir=0",
        rc == 0 and hukum_of(ham) == "KORUMA_TUTTU" and jeton(ham, "tasinabilir=") == "0",
        "rc=%d hukum=%s tasinabilir=%s" % (rc, hukum_of(ham), jeton(ham, "tasinabilir=")))
    olc("V-D hal OLCULEREK basildi (KIRMIZI + ACIK_KUYRUK sayilari gorunur)",
        "KIRMIZI=129" in ham and "ACIK_KUYRUK=129" in ham
        and jeton(ham, "KORUMALI_BEKLEYEN=") == "258",
        "koruma satiri: %s" % ([s for s in ham.splitlines()
                                if s.startswith("KORUMA ")] or ["YOK"])[0])
    olc("V-D dosya DEGISMEDI + arsiv YAZILMADI",
        metin(indeks) == once and not os.path.isfile(arsiv),
        "degisti=%s arsiv_var=%s" % (metin(indeks) != once, os.path.isfile(arsiv)))


def vaka_e():
    """V-E: arsiv dosyasi YOK -> olusturulur; VARSA frontmatter BOZULMAZ."""
    d = gecici_dizin("ve")
    indeks = indeks_yaz(d, duz_bolumler(8, 50))
    arsiv = os.path.join(d, "MEMORY-ARSIV.md")
    rc, ham, _ = kos(ARAC, indeks, arsiv=arsiv)
    ars = metin(arsiv)
    olc("V-E arsiv YOKKEN olusturulur + basligi tasir",
        rc == 0 and ars is not None and "arsiv_yeni_dosya=EVET" in ham
        and "## MEMORY.md indeksinden taşındı" in ars,
        "rc=%d arsiv_var=%s" % (rc, ars is not None))

    d2 = gecici_dizin("ve2")
    indeks2 = indeks_yaz(d2, duz_bolumler(8, 50))
    arsiv2 = os.path.join(d2, "MEMORY-ARSIV.md")
    fm = ("---\nname: memory-arsiv\ndescription: arsiv\n---\n\n"
          "# KOTA ARŞİVİ\n\nOnceki icerik BIREBIR korunmali.\n")
    with open(arsiv2, "w", encoding="utf-8") as f:
        f.write(fm)
    rc2, ham2, _ = kos(ARAC, indeks2, arsiv=arsiv2)
    ars2 = metin(arsiv2)
    olc("V-E2 mevcut arsivde frontmatter + govde BOZULMADI (append-only)",
        rc2 == 0 and ars2 is not None and ars2.startswith(fm)
        and "arsiv_yeni_dosya=hayir" in ham2,
        "rc=%d onek_korundu=%s" % (rc2, ars2 is not None and ars2.startswith(fm)))


def vaka_kuru():
    """V-F: --kuru hicbir sey yazmaz ama AYNI hukmu basar."""
    d = gecici_dizin("vf")
    indeks = indeks_yaz(d, duz_bolumler(8, 50))
    arsiv = os.path.join(d, "MEMORY-ARSIV.md")
    once = metin(indeks)
    rc, ham, _ = kos(ARAC, indeks, arsiv=arsiv, kuru=True)
    olc("V-F --kuru: hukum basilir, HICBIR SEY yazilmaz",
        rc == 0 and hukum_of(ham) == "TAVAN_BASARILI"
        and metin(indeks) == once and not os.path.isfile(arsiv),
        "rc=%d degisti=%s arsiv_var=%s"
        % (rc, metin(indeks) != once, os.path.isfile(arsiv)))


# ===========================================================================
# KAPI KOVALARI — YEDI KOVA, HER BIRI RC'SIYLE
# ===========================================================================
def kapi_kovalari():
    kok = izole_kopya("kova")

    # 1) HAFIZA_SAHIPSIZ rc0 — sahip dosyasi bu depoda YOK
    sahipsiz = izole_kopya("sahipsiz")
    os.unlink(os.path.join(sahipsiz, "tools", "hafiza-indeks-arsivle.py"))
    d = gecici_dizin("kova-sahipsiz")
    ix = indeks_yaz(d, duz_bolumler(2, 3))
    rc, ham = kapi_kos(sahipsiz, ix)
    olc("KOVA HAFIZA_SAHIPSIZ rc=0", rc == 0 and "HAFIZA_SAHIPSIZ" in ham,
        "rc=%d" % rc)

    # 2) HAFIZA_MAKINEDE_YOK rc0 — hafiza DIZINI bu makinede hic yok
    yok = os.path.join(gecici_dizin("kova-dizinsiz"), "olmayan-dizin", "MEMORY.md")
    rc, ham = kapi_kos(kok, yok)
    olc("KOVA HAFIZA_MAKINEDE_YOK rc=0", rc == 0 and "HAFIZA_MAKINEDE_YOK" in ham,
        "rc=%d" % rc)

    # 3) HAFIZA_OLCULEMEDI rc1 — dizin VAR, indeks dosyasi YOK (fail-closed)
    d3 = gecici_dizin("kova-dosyasiz")
    rc, ham = kapi_kos(kok, os.path.join(d3, "MEMORY.md"))
    olc("KOVA HAFIZA_OLCULEMEDI rc=1 (fail-closed)",
        rc == 1 and "HAFIZA_OLCULEMEDI" in ham, "rc=%d" % rc)

    # 4) HAFIZA_YESIL rc0
    d4 = gecici_dizin("kova-yesil")
    ix4 = indeks_yaz(d4, duz_bolumler(3, 5))
    rc, ham = kapi_kos(kok, ix4)
    olc("KOVA HAFIZA_YESIL rc=0", rc == 0 and "HAFIZA_YESIL" in ham, "rc=%d" % rc)

    # 5) HAFIZA_ASILDI rc1 — tavan ustu, tasinabilir is VAR
    d5 = gecici_dizin("kova-asildi")
    ix5 = indeks_yaz(d5, duz_bolumler(8, 50))
    rc, ham = kapi_kos(kok, ix5)
    olc("KOVA HAFIZA_ASILDI rc=1 + CARE satiri",
        rc == 1 and "HAFIZA_ASILDI" in ham and "CARE:" in ham
        and "hafiza-indeks-arsivle.py" in ham, "rc=%d" % rc)

    # 6) HAFIZA_TAVAN_USTU_KORUMA_NEDENIYLE rc0
    d6 = gecici_dizin("kova-koruma")
    kirmizi = [("🔴 Etiket %03d" % n, "hedef-%03d.md" % n, " — " + "dolgu " * 6)
               for n in range(1, 260)]
    ix6 = indeks_yaz(d6, [("Kapilar", kirmizi)])
    rc, ham = kapi_kos(kok, ix6)
    olc("KOVA HAFIZA_TAVAN_USTU_KORUMA_NEDENIYLE rc=0",
        rc == 0 and "HAFIZA_TAVAN_USTU_KORUMA_NEDENIYLE" in ham, "rc=%d" % rc)

    # 7) HAFIZA_HUKUM_ALINAMADI rc1 — sahip arac HUKUM basmiyor (fail-closed)
    sessiz = izole_kopya("sessiz")
    with open(os.path.join(sessiz, "tools", "hafiza-indeks-arsivle.py"),
              "w", encoding="utf-8") as f:
        f.write("VARSAYILAN_TAVAN_BAYT = 16384\n"
                "VARSAYILAN_TAVAN_SATIR = 45\n"
                "HAFIZA_VARSAYILAN = '/olmayan/MEMORY.md'\n"
                "ARSIV_VARSAYILAN = '/olmayan/MEMORY-ARSIV.md'\n"
                "import sys\n"
                "if __name__ == '__main__':\n    sys.exit(0)\n")
    d7 = gecici_dizin("kova-hukumsuz")
    ix7 = indeks_yaz(d7, duz_bolumler(8, 50))
    rc, ham = kapi_kos(sessiz, ix7)
    olc("KOVA HAFIZA_HUKUM_ALINAMADI rc=1 (olcemedim YESIL DEGILDIR)",
        rc == 1 and "HAFIZA_HUKUM_ALINAMADI" in ham, "rc=%d" % rc)

    # 7b) SAHIP ICE AKTARIMDA SystemExit ATIYOR -> HAFIZA_OLCULEMEDI rc=1.
    # 🔴 OLCULEN FAIL-OPEN (bu bataryanin BULDUGU ariza): `sys.exit(0)` modul
    # duzeyinde kosarsa `except Exception` suzgecinden GECER ve KAPIYI kendi
    # kodu ile bitirir — kapi SESSIZCE YESIL doner. Bozuk sahip OLCULEMEDI'dir.
    cokuk = izole_kopya("cokuk")
    with open(os.path.join(cokuk, "tools", "hafiza-indeks-arsivle.py"),
              "w", encoding="utf-8") as f:
        f.write("import sys\nsys.exit(0)\n")
    d7b = gecici_dizin("kova-cokuk")
    ix7b = indeks_yaz(d7b, duz_bolumler(3, 5))
    rc, ham = kapi_kos(cokuk, ix7b)
    olc("KOVA sahip ICE AKTARIMDA SystemExit atiyor -> HAFIZA_OLCULEMEDI rc=1 "
        "(fail-open kapatildi)",
        rc == 1 and "HAFIZA_OLCULEMEDI" in ham, "rc=%d" % rc)
    return kok


# ===========================================================================
# MUTANTLAR — YALNIZ IZOLE KOPYADA, HER BIRI HEDEF KOLUN ATFIYLA OLUR
# ===========================================================================
def mutantlar():
    olen = 0
    toplam = 0

    # --- M1: tavani SAHIPTEN degil KODA GOMULU kopyadan oku ----------------
    toplam += 1
    kok = izole_kopya("m1")
    yamala(kok, "defter-kota-kapisi.py",
           "    tavan_bayt = _mod.hafiza_tavan_bayt(mod)",
           "    tavan_bayt = 999999  # M1: koda gomulu IKINCI kopya")
    d = gecici_dizin("m1")
    ix = indeks_yaz(d, duz_bolumler(8, 50))
    rc_m, ham_m = kapi_kos(kok, ix)
    kok_t = izole_kopya("m1-taban")
    rc_t, ham_t = kapi_kos(kok_t, ix)
    oldu = (rc_t == 1 and "HAFIZA_ASILDI" in ham_t
            and rc_m == 0 and "HAFIZA_YESIL" in ham_m)
    olen += 1 if oldu else 0
    olc("M1 tavan koda gomulu kopyadan okununca ASIM GORUNMEZ olur "
        "(hedef kol: defter-kota-taban.hafiza_tavan_bayt turetmesi)",
        oldu, "taban rc=%d/%s  mutant rc=%d/%s"
        % (rc_t, "ASILDI" if "HAFIZA_ASILDI" in ham_t else "?",
           rc_m, "YESIL" if "HAFIZA_YESIL" in ham_m else "?"))

    # --- M2: koruma kontrolunu KALDIR --------------------------------------
    toplam += 1
    kok2 = izole_kopya("m2")
    yamala(kok2, "hafiza-indeks-arsivle.py",
           'def koruma_sebebi(parca, kok):\n    """None = tasinabilir; aksi halde koruma sebebinin ADI."""',
           'def koruma_sebebi(parca, kok):\n    """None = tasinabilir; aksi halde koruma sebebinin ADI."""\n'
           '    return None  # M2: koruma kolu KALDIRILDI')
    d2 = gecici_dizin("m2")
    kirmizi = [("🔴 Etiket %03d" % n, "hedef-%03d.md" % n, " — " + "dolgu " * 6)
               for n in range(1, 130)]
    kuyruk = [("Etiket K%03d" % n, "kuyruk-%03d.md" % n, " — " + "dolgu " * 6)
              for n in range(1, 130)]
    ix2 = indeks_yaz(d2, [("Kapilar", kirmizi), ("Açık kuyruk", kuyruk)])
    once2 = metin(ix2)
    rc_t2, ham_t2, ars_t2 = kos(ARAC, ix2)
    taban_ok = (rc_t2 == 0 and hukum_of(ham_t2) == "KORUMA_TUTTU"
                and metin(ix2) == once2)
    rc_m2, ham_m2, ars_m2 = kos(os.path.join(kok2, "tools",
                                             "hafiza-indeks-arsivle.py"), ix2)
    # Mutantta koruma yok -> ya 🔴/Acik kuyruk girdileri TASINIR (dosya degisir),
    # ya da kendi dogrulamasi (D5/D6) KIRMIZI yakar. Iki hal de TABANDAN FARKLIDIR.
    mutant_farkli = (hukum_of(ham_m2) != "KORUMA_TUTTU") or (metin(ix2) != once2)
    oldu = taban_ok and mutant_farkli
    olen += 1 if oldu else 0
    olc("M2 koruma kolu kaldirilinca KORUMA_TUTTU hali KAYBOLUR "
        "(hedef kol: koruma_sebebi + dogrula D5/D6)",
        oldu, "taban hukum=%s | mutant rc=%d hukum=%s dosya_degisti=%s"
        % (hukum_of(ham_t2), rc_m2, hukum_of(ham_m2), metin(ix2) != once2))

    # --- M3: lossless dogrulamayi DAIMA TRUE yap ---------------------------
    # KONTROL cifti: once arsiv ekini BOZAN bir yama uygulanir (son tasinan girdi
    # arsive YAZILMAZ). Dogrulama SAGLAMKEN bu KIRMIZI yanmali; dogrulama
    # kaldirilinca YESIL'e donmeli. Ikinci hal, D-eksenlerinin gercekten OLCTUGUNU
    # kanitlar ([[lossless-beyani-blok-butunlugu-olcmez]]).
    toplam += 1
    d3 = gecici_dizin("m3")
    ix3 = indeks_yaz(d3, duz_bolumler(8, 50))
    bozuk_capa = "        for g in plan.tasinan:\n            if g.bolum == bolum:\n                parcalar.append(\"- \" + g.metin + \"\\n\")"
    bozuk_yeni = ("        for g in plan.tasinan[:-1]:\n            if g.bolum == bolum:\n"
                  "                parcalar.append(\"- \" + g.metin + \"\\n\")")
    kok3a = izole_kopya("m3-kontrol")
    yamala(kok3a, "hafiza-indeks-arsivle.py", bozuk_capa, bozuk_yeni)
    rc_k, ham_k, _ = kos(os.path.join(kok3a, "tools", "hafiza-indeks-arsivle.py"),
                         ix3, kuru=True)
    kok3b = izole_kopya("m3-mutant")
    yamala(kok3b, "hafiza-indeks-arsivle.py", bozuk_capa, bozuk_yeni)
    yamala(kok3b, "hafiza-indeks-arsivle.py",
           "def dogrula(metin, yeni_metin, arsiv_metin, yeni_arsiv, plan, h, kok):\n    hatalar = []",
           "def dogrula(metin, yeni_metin, arsiv_metin, yeni_arsiv, plan, h, kok):\n"
           "    return []  # M3: lossless dogrulama DAIMA TRUE\n    hatalar = []")
    rc_m3, ham_m3, _ = kos(os.path.join(kok3b, "tools", "hafiza-indeks-arsivle.py"),
                           ix3, kuru=True)
    oldu = (rc_k == 1 and "LOSSLESS DOGRULAMASI KIRMIZI" in ham_k
            and rc_m3 == 0 and "LOSSLESS DOGRULAMASI KIRMIZI" not in ham_m3)
    olen += 1 if oldu else 0
    olc("M3 dogrulama daima-True olunca BOZUK arsiv eki YESIL gecer "
        "(hedef kol: dogrula() D3/D12)",
        oldu, "kontrol(bozuk+dogrulama) rc=%d  mutant(bozuk+dogrulamasiz) rc=%d"
        % (rc_k, rc_m3))

    # --- M4: kapi rc tablosunu TERSINE cevir -------------------------------
    toplam += 1
    kok4 = izole_kopya("m4")
    yamala(kok4, "defter-kota-kapisi.py",
           "HAFIZA_RC = {\n    HAFIZA_SAHIPSIZ: 0,",
           "HAFIZA_RC = {\n    HAFIZA_SAHIPSIZ: 1,")
    yamala(kok4, "defter-kota-kapisi.py",
           "    HAFIZA_ASILDI: 1,\n    HAFIZA_YESIL: 0,",
           "    HAFIZA_ASILDI: 0,\n    HAFIZA_YESIL: 1,")
    d4 = gecici_dizin("m4")
    ix4 = indeks_yaz(d4, duz_bolumler(8, 50))
    ix4y = indeks_yaz(gecici_dizin("m4-yesil"), duz_bolumler(3, 5))
    rc_a, _ = kapi_kos(kok4, ix4)
    rc_y, _ = kapi_kos(kok4, ix4y)
    oldu = (rc_a == 0 and rc_y == 1)
    olen += 1 if oldu else 0
    olc("M4 rc tablosu tersine cevrilince ASILDI gecer / YESIL bloklar "
        "(hedef kol: HAFIZA_RC -> cikis kodu)",
        oldu, "asildi_rc=%d (0 mutant) yesil_rc=%d (1 mutant)" % (rc_a, rc_y))

    # --- M5: su seviyesi yerine TAVANA kadar in (K353 arizasi) -------------
    toplam += 1
    kok5 = izole_kopya("m5")
    yamala(kok5, "hafiza-indeks-arsivle.py",
           "    hedef_bayt = su_bayt",
           "    hedef_bayt = tavan_bayt  # M5: onarim hedefi = CEZA esigi (K353)")
    d5 = gecici_dizin("m5")
    ix5 = indeks_yaz(d5, duz_bolumler(8, 50))
    rc_t5, ham_t5, _ = kos(ARAC, ix5, kuru=True)
    rc_m5, ham_m5, _ = kos(os.path.join(kok5, "tools", "hafiza-indeks-arsivle.py"),
                           ix5, kuru=True)
    su = int(jeton(ham_t5, "su_bayt=") or -1)
    taban_sonra = int(jeton(ham_t5, "sonra_bayt=") or -1)
    mutant_sonra = int(jeton(ham_m5, "sonra_bayt=") or -1)
    oldu = (taban_sonra <= su < mutant_sonra
            and "su_seviyesine_indi=EVET" in ham_t5
            and "su_seviyesine_indi=EVET" not in ham_m5)
    olen += 1 if oldu else 0
    olc("M5 rotasyon TAVANDA durursa su seviyesine INMEZ "
        "(hedef kol: planla() hedef_bayt = su_bayt)",
        oldu, "su=%d taban_sonra=%d mutant_sonra=%d" % (su, taban_sonra, mutant_sonra))

    return olen, toplam


# ===========================================================================
# ANA
# ===========================================================================
def main():
    imza_once = gercek_imza()

    vaka_a()
    vaka_b()
    vaka_c()
    vaka_d()
    vaka_e()
    vaka_kuru()
    kapi_kovalari()
    olen, mutant_toplam = mutantlar()

    # KONTROL-0 — gercek hafiza indeksi DOKUNULMADI
    imza_sonra = gercek_imza()
    kontrol_yesil = (imza_once == imza_sonra)
    olc("KONTROL-0 gercek MEMORY.md bayt+mtime DEGISMEDI (FILO DERSI)",
        kontrol_yesil, "once=%s sonra=%s" % (imza_once, imza_sonra))

    # KONTROL-1 — tek kaynak nobeti: ikinci esik sahibi YOK
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("kapi_tek_kaynak", KAPI)
    kapi = ilu.module_from_spec(spec)
    spec.loader.exec_module(kapi)
    ihlaller = kapi.tek_kaynak_ihlalleri(KOK)
    olc("KONTROL-1 tek kaynak nobeti: hafiza tavani ikinci sabite KOPYALANMAMIS",
        not ihlaller, "ihlal=%s" % (ihlaller or "yok"))
    # KONTROL-2 — hafiza tavanlari nobetin IZLEDIGI kumede (turetildi, yazilmadi)
    esikler = kapi.izlenen_esikler(KOK)
    olc("KONTROL-2 hafiza tavanlari SAHIPTEN turetilip izlenen kumeye girdi",
        16384 in esikler and 45 in esikler, "izlenen=%s" % sorted(esikler))

    dusen = 0
    gecen = 0
    for ad, gecti, detay in sonuclar:
        if gecti:
            gecen += 1
        else:
            dusen += 1
            print("  ✗ %s: %s" % (ad, detay), file=sys.stderr)

    for d in _gecici:
        shutil.rmtree(d, ignore_errors=True)

    print("VAKA=%d/%d MUTANT=%d/%d KONTROL=%s"
          % (gecen, len(sonuclar), olen, mutant_toplam,
             "YESIL" if (kontrol_yesil and not ihlaller) else "KIRMIZI"))
    print("DUSEN=%d" % (dusen + (mutant_toplam - olen)))
    return 0 if (dusen == 0 and olen == mutant_toplam) else 1


if __name__ == "__main__":
    sys.exit(main())

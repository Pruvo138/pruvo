#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SARI SERİ KONFİGÜRATÖR — 8 KABUL TESTİ (tools/paket-sari-konfigurator.md).

Kullanım: python3 jenerator/test/kabul.py [--hizli]
  --hizli: #1'de rastgele set sayısını düşürür (3 -> 1) ve site build'ini
           mevcut urun/ çıktısı varsa atlar (geliştirme turu için).
Çıkış kodu 0 = 8/8 YEŞİL.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
JEN_DIR = os.path.dirname(TEST_DIR)
ROOT = os.path.dirname(JEN_DIR)
SONUC = []

# Sayfanin TARAYICIDA GECERLI govdesi (icerik-adresli /varlik/ referanslari yerine konmus)
# TEK KAYNAKTAN gelir; her kapinin kendi "varligi da oku" kopyasi ikiz tanim olurdu.
sys.path.insert(0, os.path.join(ROOT, "tools"))
import yayin_yuzey  # noqa: E402  (ROOT/tools yolu yukarida kuruluyor)

# Yasaklı ifadeler parçalı kurulur ki bu dosya kendi taramasına takılmasın.
YASAK_GIZLI = "ko" + "olm"
YASAK_BASKI = re.compile(r"3\s*[dD]\s*[-\s]?bask|3\s*boyutlu\s+bask", re.I)
YASAK_RENK = re.compile(r"her\s+renk", re.I)

# TEST 7'nin gecici ornek urunu (finally'de silinir) katalog urunu degil —
# TEST 8 kapsam kumesinden haric tutulur ki yarim kalan kosu yanlis kirmizi yakmasin.
SEMA_FIXTURE = {"ornek-plaka"}


# ---- ORTAK "GERCEK ICRA MI" SUZGECI (TEK KAYNAK) ---------------------------
# TEST 4'un "deploy kopyasi" iddiasi 30 Tem'e kadar DUZ ALT-DIZE aramasiydi:
#     beyaz = "jenerator/hacim.js" in deploy_metni
# OLCULDU (gecici kopyada): deploy.yml'deki `cp jenerator/hacim.js ... _site/jenerator/`
# satiri (a) `echo cp ...`'a cevrilse, (b) `# cp ...` diye yoruma alinsa metin HALA
# dosyada geciyor -> iddia True kaliyor. Yani jenerator varliklarinin yayina
# KOPYALANMAMASI SESSIZ kaliyordu (site parametrik urun sayfalarinda hacim.js'i 404
# alir; konfigurator fiyat hesaplamaz). Artik olcum tools/is-akisi-kapisi.py'nin
# GERCEK YAML + kabuk suzgecinden gelir; KOPYA MANTIK YAZILMAZ.
def _is_akisi_modulu():
    """tools/is-akisi-kapisi.py'yi MODUL olarak yukle. (modul, hata_metni)."""
    import importlib.util
    yol = os.path.join(ROOT, "tools", "is-akisi-kapisi.py")
    if not os.path.exists(yol):
        return None, "tools/is-akisi-kapisi.py YOK"
    if "pruvo_is_akisi_kapisi" in sys.modules:
        return sys.modules["pruvo_is_akisi_kapisi"], None
    try:
        spec = importlib.util.spec_from_file_location("pruvo_is_akisi_kapisi", yol)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["pruvo_is_akisi_kapisi"] = mod
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001 — her tur import arizasi ayni hukmu verir
        return None, "tools/is-akisi-kapisi.py yuklenemedi (%s: %s)" % (type(e).__name__, e)
    if not hasattr(mod, "etkili_mensiyon"):
        return None, "tools/is-akisi-kapisi.py'de etkili_mensiyon() YOK (sozlesme degismis)"
    return mod, None


def deploy_kopyaliyor_mu(deploy_metin, varlik):
    """(ok, tani) — deploy.yml <varlik>'i ETKILI bir komutun argumani olarak tasiyor mu?

    FAIL-CLOSED: suzgec yuklenemezse ya da is akisi ayristirilamazsa YESIL SAYILMAZ —
    'olculemedi' bu iddiada sessiz-yesille aynidir."""
    mod, hata = _is_akisi_modulu()
    if mod is None:
        return False, "OLCULEMEDI (fail-closed KIRMIZI): %s" % hata
    if not mod.ayristirici_var():
        return False, ("OLCULEMEDI (fail-closed KIRMIZI): hicbir YAML ayristiricisi yok "
                       "(pip install pyyaml ya da ruby kur)")
    bulunan = mod.etkili_mensiyon(deploy_metin, varlik)
    if bulunan:
        return True, ""
    return False, ("deploy.yml %r varligini ETKILI bir komutun argumani olarak "
                   "TASIMIYOR (satir silinmis / yoruma alinmis / `echo`'ya cevrilmis / "
                   "`|| true`-`continue-on-error`-`if: false` ile etkisizlestirilmis). "
                   "GERI KOY: 'Icerik dizinleri' adiminda "
                   "`cp jenerator/hacim.js ... _site/jenerator/`." % varlik)


def kayit(no, ad, yesil, detay=""):
    SONUC.append((no, ad, yesil))
    print("[%s] TEST %d — %s%s" % ("YESIL" if yesil else "KIRMIZI", no, ad,
                                   ("\n" + detay) if detay else ""))


# ---- SUITE BUTUNLUGU (31 Tem 2026) — SILINEN TEST GORUNMEZ DEGILDIR ---------
# OLCULEN FAIL-OPEN: ozet `8 - len(kirmizi)` SABIT LITERALI ile basiliyordu ve hukum
# YALNIZ `SONUC` icindeki KIRMIZILARA bakiyordu. Sonuc: bir testin govdesi (ornegin
# TEST 5 gizlilik taramasi) suite'ten SILINSE SONUC'a hic giris yazilmaz -> kirmizi
# YOK -> bayraksiz kol exit 0 ve ozet satiri DEGISMEDEN "8 YESIL" der. Yani nobetciyi
# KALDIRMAK, onu YESILE cevirmenin en kolay yoluydu; hicbir sey bagirmiyordu.
# FAIL-CLOSED: beklenen test NUMARALARI burada BEYAN edilir; eksik/mukerrer/fazla
# giris KIRMIZI'dir. (Yeni test eklerken bu demeti de guncelle — bilincli adim.)
BEKLENEN_TESTLER = (1, 2, 3, 4, 5, 6, 7, 8)


def suite_butunlugu(sonuc, beklenen=BEKLENEN_TESTLER):
    """(hatalar) — SAF fonksiyon; oz-nobetci bunu POZITIF ve NEGATIF yonde surer."""
    hatalar = []
    gorulen = [s[0] for s in sonuc]
    eksik = [n for n in beklenen if n not in gorulen]
    mukerrer = sorted(set(n for n in gorulen if gorulen.count(n) > 1))
    fazla = sorted(set(n for n in gorulen if n not in beklenen))
    if eksik:
        hatalar.append("SUITE EKSIK: %s numarali test(ler) hic KAYIT ETMEDI -> govdesi "
                       "silinmis/atlanmis olabilir; 'kirmizi yok' YESIL DEMEK DEGILDIR"
                       % ", ".join(str(n) for n in eksik))
    if mukerrer:
        hatalar.append("SUITE MUKERRER: %s numarasi birden fazla kayit etti"
                       % ", ".join(str(n) for n in mukerrer))
    if fazla:
        hatalar.append("SUITE BEYAN DISI: %s numarali test BEKLENEN_TESTLER'de yok "
                       "(test eklendiyse demeti guncelle)"
                       % ", ".join(str(n) for n in fazla))
    return hatalar


def kos(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def fold(s):
    return (s or "").lower().translate(str.maketrans("çğıöşüâî", "cgiosuai"))


def parametrik_urunler():
    with io.open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        d = json.load(f)
    urunler = d["urunler"] if isinstance(d, dict) and "urunler" in d else d
    return [u for u in urunler if u.get("parametrik")]


def hacim_fonksiyonlari():
    p = kos(["node", "-p",
             'Object.keys(require("%s")).join(",")' %
             os.path.join(JEN_DIR, "hacim.js")])
    return set(p.stdout.strip().split(",")) if p.returncode == 0 else set()


# ---- TARAMA KUMESI: GITIGNORE'LU ARTEFAKT DISARI, GERCEK POZITIF ICERI ------
# SAHTE KIRMIZI (madde 34, YENIDEN URETILDI): dosya_tara() JEN_DIR'i os.walk ile
# geziyordu ve gitignore'lu `__pycache__/` de kumeye giriyordu. Python'un sabit
# katlamasi bu dosyadaki `YASAK_GIZLI = "ko" + "olm"` ifadesini derlerken TEK
# DIZEYE cevirir -> `__pycache__/kabul.cpython-3xx.pyc` yasak dizeyi HARFIYEN
# tasir ve TEST 5 KIRMIZI yanar. Kimsenin degistirmedigi, yayina hic girmeyen,
# git'in gormedigi bir ARTEFAKT yuzunden. Surekli/kaprisli kirmizi = korelmis
# nobetci: gercek bir sizinti da ayni gurultunun icinde kaybolur.
#
# 🔴 KAPSAMI DARALTIRKEN GERCEK POZITIFI OLDURME ([[kapi-kapsam-genisletme-tuzagi]]
# tersi): "yalniz IZLENEN dosyalari tara" demek KOLAY ama YANLIS olurdu —
#   (a) `urun/` gitignore'ludur (build.py uretir, CI yayinlar) ve sari seri
#       kurallarinin (yasak ifade / rozet / fiyatsiz duzen) TEK gorunur oldugu
#       yer orasidir; disarida biraksaydik TEST 6 gercek pozitifi kaybederdi.
#   (b) Henuz `git add` edilmemis YENI bir kaynak dosya izlenmez ama gitignore'lu
#       da DEGILDIR; taramadan duserse sizinti bir tur gorunmez kalirdi.
# BUGUNKU KURAL: bir dosya taramadan YALNIZCA git'in onu YOKSAYDIGI durumda
# duser (`git check-ignore` — IZLENEN dosyayi yoksayilan saymaz), BEYAN EDILMIS
# uretilen kokler (URETILEN_TARAMA_KOKLERI) ise HER ZAMAN taranir.
# FAIL-CLOSED: git calismazsa/hata verirse kume OLCULEMEZ -> TaramaKumesiYok ->
# cagiran testi KIRMIZI yakar ("olculemedi" burada sessiz-yesille aynidir).
URETILEN_TARAMA_KOKLERI = (os.path.join(ROOT, "urun"),)


class TaramaKumesiYok(Exception):
    """Tarama kumesi (gitignore durumu) OLCULEMEDI — yesil sayilmaz."""


def _beyanli_uretilen(mutlak):
    for kok in URETILEN_TARAMA_KOKLERI:
        if mutlak == kok or mutlak.startswith(kok + os.sep):
            return True
    return False


def _yoksayilanlar(yollar, git_kok):
    """git check-ignore ile YOKSAYILAN yollarin kumesi (tek cagri).

    `git check-ignore` index'e BAKAR: IZLENEN bir dosya, deseni tutsa bile
    'yoksayilan' RAPOR EDILMEZ -> izlenen kaynak taramadan asla dusmez."""
    if not yollar:
        return set()
    try:
        p = subprocess.run(["git", "-C", git_kok, "check-ignore", "--stdin", "-z"],
                           input="\0".join(yollar) + "\0",
                           capture_output=True, text=True)
    except OSError as e:
        raise TaramaKumesiYok("git calistirilamadi: %s" % e)
    if p.returncode not in (0, 1):   # 0 = en az biri yoksayilan, 1 = hicbiri
        raise TaramaKumesiYok("git check-ignore rc=%d (%s)" %
                              (p.returncode, (p.stderr or "").strip()[:200]))
    return set(x for x in p.stdout.split("\0") if x)


def dosya_tara(kokler, desenler, atla=(), git_kok=None):
    """Verilen kok dosya/dizinlerde desen arar; eslesen (dosya, desen_adi) listesi.

    Tarama kumesi olculemezse TaramaKumesiYok firlatir (bkz. guvenli_tara)."""
    git_kok = git_kok or ROOT
    adaylar = []
    for kok in kokler:
        if not os.path.exists(kok):
            continue
        yollar = [kok] if os.path.isfile(kok) else []
        if not yollar:
            for dizin, _, dosyalar in os.walk(kok):
                yollar += [os.path.join(dizin, x) for x in dosyalar]
        for yol in yollar:
            mutlak = os.path.abspath(yol)
            if mutlak in atla or yol.endswith((".stl", ".png", ".jpg")):
                continue
            adaylar.append(mutlak)
    sorulacak = [y for y in adaylar if not _beyanli_uretilen(y)]
    yoksayilan = _yoksayilanlar(sorulacak, git_kok)
    bulunan = []
    for yol in adaylar:
        if yol in yoksayilan:
            continue          # gitignore'lu ARTEFAKT (ör. __pycache__) — yayina girmez
        try:
            with io.open(yol, "r", encoding="utf-8", errors="ignore") as f:
                icerik = f.read()
        except (IOError, OSError):
            continue
        for ad, desen in desenler:
            if (desen.search(icerik) if hasattr(desen, "search")
                    else desen in icerik.lower()):
                bulunan.append((os.path.relpath(yol, ROOT), ad))
    return bulunan


def guvenli_tara(kokler, desenler, atla=(), git_kok=None):
    """(bulunan, olculemedi_tani) — kume olculemezse tani DOLU doner ve cagiran
    testi KIRMIZI yakar (fail-closed)."""
    try:
        return dosya_tara(kokler, desenler, atla=atla, git_kok=git_kok), ""
    except TaramaKumesiYok as e:
        return [], ("OLCULEMEDI (fail-closed KIRMIZI): tarama kumesi olculemedi — %s" % e)


# ---- TARAMA KUMESI NOBETCISI (kabul suite'ini kosturmadan olculur) ----------
def kendini_test():
    """m34 NOBETCISI — POZITIF ve NEGATIF yon AYRI vakalar (tek yon = olu nobetci).

    Kapsam daraltmasi gercek pozitifi OLDURMESIN diye: gitignore'lu artefaktin
    DUSTUGU kadar, izlenen kaynagin / beyanli uretilen kokun / henuz eklenmemis
    yeni dosyanin taramada KALDIGI da ayri ayri olculur."""
    vakalar = []

    def bekle(ad, kosul, detay=""):
        vakalar.append((ad, bool(kosul), detay))

    desen = [("gizli-marka", YASAK_GIZLI)]
    gecici = []
    try:
        # (1) POZITIF-DISI: gitignore'lu __pycache__ artefakti taranmamali
        pycache = os.path.join(TEST_DIR, "__pycache__")
        if not os.path.isdir(pycache):
            os.makedirs(pycache)
        artefakt = os.path.join(pycache, "pruvo-kendini-test.pyc")
        gecici.append(artefakt)
        with io.open(artefakt, "w", encoding="utf-8") as f:
            f.write("baytkod artefakti " + YASAK_GIZLI + "\n")
        b, t = guvenli_tara([TEST_DIR], desen, atla={os.path.abspath(__file__)})
        bekle("V1 gitignore'lu __pycache__ artefakti taranmiyor (sahte KIRMIZI yok)",
              not t and not b, "tani=%s bulgu=%s" % (t, b))

        # (2) POZITIF: IZLENEN kaynak hala taraniyor (kapsam daralmadi)
        b, t = guvenli_tara([os.path.join(JEN_DIR, "hacim.js")],
                            [("izlenen-kaynak", re.compile(r"function\s+oring\s*\("))])
        bekle("V2 IZLENEN kaynak taraniyor (jenerator/hacim.js)",
              not t and len(b) == 1, "tani=%s bulgu=%s" % (t, b))

        # (3) POZITIF: izlenmeyen AMA gitignore'lu OLMAYAN yeni dosya taraniyor
        yeni = os.path.join(JEN_DIR, "pruvo-kendini-test-gecici.js")
        gecici.append(yeni)
        with io.open(yeni, "w", encoding="utf-8") as f:
            f.write("// henuz git add edilmemis kaynak: " + YASAK_GIZLI + "\n")
        b, t = guvenli_tara([JEN_DIR], desen, atla={os.path.abspath(__file__)})
        bekle("V3 izlenmeyen ama YOKSAYILMAYAN yeni kaynak yakalaniyor",
              not t and any(x[0].endswith("pruvo-kendini-test-gecici.js") for x in b),
              "tani=%s bulgu=%s" % (t, b))

        # (4) POZITIF: BEYANLI uretilen kok (urun/) gitignore'lu OLDUGU HALDE taraniyor
        uretilen = os.path.join(ROOT, "urun", "_pruvo-kendini-test")
        if not os.path.isdir(uretilen):
            os.makedirs(uretilen)
        sayfa = os.path.join(uretilen, "index.html")
        gecici.append(sayfa)
        with io.open(sayfa, "w", encoding="utf-8") as f:
            f.write("<p>uretilen sayfa " + YASAK_GIZLI + "</p>\n")
        b, t = guvenli_tara([os.path.join(ROOT, "urun")], desen)
        bekle("V4 gitignore'lu AMA beyanli uretilen kok (urun/) taraniyor",
              not t and any("_pruvo-kendini-test" in x[0] for x in b),
              "tani=%s bulgu=%s" % (t, b))

        # (5) OLCULEMEDI: kume olculemezse YESIL DEGIL
        with tempfile.TemporaryDirectory() as depo_disi:
            b, t = guvenli_tara([os.path.join(JEN_DIR, "hacim.js")], desen,
                                git_kok=depo_disi)
            bekle("V5 tarama kumesi olculemezse OLCULEMEDI (yesil sayilmaz)",
                  bool(t) and not b, "tani=%s" % t)
    finally:
        for yol in gecici:
            if os.path.exists(yol):
                os.remove(yol)
        artefakt_dizin = os.path.join(ROOT, "urun", "_pruvo-kendini-test")
        if os.path.isdir(artefakt_dizin):
            os.rmdir(artefakt_dizin)

    # (6-8) SUITE BUTUNLUGU — bayraksiz kolun "silinen test gorunmez" fail-open'i.
    # Bayraksiz tam suite CI'da KOSMAZ (OpenSCAD/build.py ister) -> onun hukum
    # mantigini SAF fonksiyon olarak burada, CI'da kosan kolda olcuyoruz.
    tam = [(n, "sentetik", True) for n in BEKLENEN_TESTLER]
    bekle("V6 NEGATIF-DISI: tam suite butunluk hatasi URETMEZ (yanlis-pozitif yok)",
          suite_butunlugu(tam) == [], "hatalar=%s" % suite_butunlugu(tam))
    eksikli = [v for v in tam if v[0] != 5]
    bekle("V7 POZITIF: bir test hic KAYIT ETMEZSE (govdesi silinmis) KIRMIZI",
          any("SUITE EKSIK" in h for h in suite_butunlugu(eksikli)),
          "hatalar=%s" % suite_butunlugu(eksikli))
    bekle("V8 POZITIF: ayni numara iki kez kayit ederse KIRMIZI",
          any("SUITE MUKERRER" in h for h in suite_butunlugu(tam + [tam[0]])),
          "hatalar=%s" % suite_butunlugu(tam + [tam[0]]))

    kirmizi = [v for v in vakalar if not v[1]]
    print("TARAMA KUMESI + SUITE BUTUNLUGU NOBETCISI — %d/%d YESIL"
          % (len(vakalar) - len(kirmizi), len(vakalar)))
    for ad, yesil, detay in vakalar:
        print("  %s %-62s %s" % ("+" if yesil else "-", ad, detay if not yesil else ""))
    return 1 if kirmizi else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hizli", action="store_true")
    ap.add_argument("--kendini-test", action="store_true",
                    help="tarama kumesi nobetcisi (kabul suite'ini kosturmaz)")
    args = ap.parse_args()

    if args.kendini_test:
        sys.exit(kendini_test())

    urunler = parametrik_urunler()

    # ---------- TEST 1: hacim doğruluğu (hacim.js vs OpenSCAD render, <=%3) ----------
    set_sayisi = "1" if args.hizli else "3"
    p = subprocess.run([sys.executable, os.path.join(TEST_DIR, "dogrula.py"),
                        "--hepsi", "--set", set_sayisi], text=True)
    # dogrula.py cikis 3 = OPENSCAD YASAK (PRUVO_OPENSCAD_YASAK) -> bu bir "yesil"
    # DEGIL, OLCULEMEDI'dir; kirmizi kalir ama tanisi ayirt edilir.
    kayit(1, "hacim dogrulugu (>=%s rastgele set + varsayilan, <=%%3)" % set_sayisi,
          p.returncode == 0,
          ("OLCULEMEDI: openscad yasagi aktif (PRUVO_OPENSCAD_YASAK) — hicbir "
           "render kosulmadi; bu bir YESIL degildir" if p.returncode == 3 else ""))

    # ---------- site build (3b/5/6 icin gerekli) ----------
    urun_dir = os.path.join(ROOT, "urun")
    if not (args.hizli and os.path.isdir(urun_dir)):
        b = kos([sys.executable, os.path.join(ROOT, "tools", "build.py")], cwd=ROOT)
        if b.returncode != 0:
            print(b.stdout[-2000:], b.stderr[-2000:])
            sys.exit("build.py basarisiz — kabul testleri kosulamaz")

    # ---------- TEST 2: fiyat orantısı (kuruş korunur) + TEST 3a: sınır doğrulama ----------
    p = kos(["node", os.path.join(TEST_DIR, "fiyat-test.js")])
    print(p.stdout.rstrip())
    kayit(2, "fiyat orantisi (198,72 birebir; kurus korunur, yuvarlama yok)",
          p.returncode == 0)

    # ---------- TEST 3b: sayfa kablolaması (geçersiz giriş kilitler + alan kızarır) ----------
    # 🔴 OLCUM YUZEYI: aranan kablolamanin bir kismi artik sayfaya GOMULU DEGIL —
    # `PRUVO_KONF.gecerliMi` /varlik/urun-<hash>.js'e, `.hatali` /varlik/sayfa-<hash>.css'e
    # tasindi. Kod hala tarayiciya iniyor ama HAM HTML'de yok; ham metinde arayan olcum
    # SESSIZCE korelir. Sayfayi TEK KAYNAK yayin yuzeyinden gecirip tasima ONCESIYLE ayni
    # yuzeyi olceriz (varlik diskte yoksa FAIL-CLOSED: kirmizi, sessiz atlama yok).
    eksik = []
    varlik_ref = 0
    for u in urunler:
        sayfa = os.path.join(urun_dir, u["id"], "index.html")
        if not os.path.exists(sayfa):
            eksik.append(u["id"] + ": sayfa yok"); continue
        with io.open(sayfa, encoding="utf-8") as f:
            ham = f.read()
        varlik_ref += len(yayin_yuzey.varlik_referanslari(ham))
        try:
            h = yayin_yuzey.govde(ham, ROOT)
        except yayin_yuzey.VarlikYok as e:
            eksik.append(u["id"] + ": " + str(e)); continue
        if os.path.exists(os.path.join(JEN_DIR, "urunler", u["id"] + ".json")):
            for gerek in ("konfAlanlar", "PRUVO_KONF.gecerliMi", ".hatali",
                          "/jenerator/hacim.js", "/jenerator/konfigurator.js"):
                if gerek not in h:
                    eksik.append(u["id"] + ": " + gerek + " eksik")
    # KAPSAM: yuzey genisletmesi FIILEN kostu mu? Sifir referans = ya tasima geri alinmis
    # ya desen bosa dusmustur; ikisinde de yukaridaki arama tasima ONCESI yuzeyi olcer
    # ve bu testin ne olctugu sessizce degismis olur.
    if urunler and varlik_ref == 0:
        eksik.append("KAPSAM: hicbir urun sayfasinda /varlik/ referansi gorulmedi "
                     "(yayin yuzeyi bosa mi dustu?)")
    kayit(3, "sinir dogrulama (saf cekirdek #2'de; sayfa kilit/kizarma kablolamasi)",
          p.returncode == 0 and not eksik, "\n".join(eksik))

    # ---------- TEST 4: tek kaynak hacim.js ----------
    hacim_yolu = os.path.join(JEN_DIR, "hacim.js")
    with io.open(hacim_yolu, "rb") as f:
        onceki = f.read()
    kos([sys.executable, os.path.join(TEST_DIR, "birlestir.py")])
    with io.open(hacim_yolu, "rb") as f:
        sonraki = f.read()
    deterministik = onceki == sonraki
    with tempfile.TemporaryDirectory() as tmp:  # deploy kopyasi simulasyonu
        shutil.copy(hacim_yolu, os.path.join(tmp, "hacim.js"))
        with io.open(os.path.join(tmp, "hacim.js"), "rb") as f:
            ayni = f.read() == sonraki
    with io.open(os.path.join(ROOT, ".github", "workflows", "deploy.yml"),
                 encoding="utf-8") as f:
        deploy = f.read()
    beyaz, beyaz_tani = deploy_kopyaliyor_mu(deploy, "jenerator/hacim.js")
    kopya, kopya_tani = guvenli_tara(
        [os.path.join(ROOT, "secenekler.js"), os.path.join(ROOT, "index.html"),
         urun_dir, os.path.join(ROOT, "tools")],
        [("hacim fn kopyasi", re.compile(r"function\s+(oring|huni|disli)\s*\("))])
    ayrinti = []
    if kopya_tani:
        ayrinti.append(kopya_tani)
    if not deterministik:
        ayrinti.append("hacim.js birlestir.py sonrasi DEGISTI (deterministik degil)")
    if not ayni:
        ayrinti.append("deploy kopyasi bayt-ozdes DEGIL")
    if not beyaz:
        ayrinti.append(beyaz_tani)
    if kopya:
        ayrinti.append("hacim fn kopyasi: %s" % (kopya,))
    kayit(4, "tek kaynak: hacim.js deterministik + deploy kopyasi bayt-ozdes + kopya yok",
          deterministik and ayni and beyaz and not kopya and not kopya_tani,
          "\n".join(ayrinti))

    # ---------- TEST 5: gizlilik ----------
    bulunan, tani5 = guvenli_tara(
        [JEN_DIR, urun_dir, os.path.join(ROOT, "index.html"),
         os.path.join(ROOT, "secenekler.js")],
        [("gizli-marka", YASAK_GIZLI)],
        atla={os.path.abspath(__file__)})
    kayit(5, "gizlilik: public dosyalarda '%s' yok" % ("k*" + "olm"),
          not bulunan and not tani5,
          "\n".join(["%s -> %s" % b for b in bulunan] + ([tani5] if tani5 else [])))

    # ---------- TEST 6: sarı seri kuralları ----------
    bulunan, tani6 = guvenli_tara(
        [JEN_DIR, urun_dir, os.path.join(ROOT, "index.html"),
         os.path.join(ROOT, "secenekler.js")],
        [("3D-baski-ifadesi", YASAK_BASKI), ("her-renk", YASAK_RENK)],
        atla={os.path.abspath(__file__)})
    duzen = []
    if tani6:
        duzen.append(tani6)
    for u in urunler:
        sema_yolu = os.path.join(JEN_DIR, "urunler", u["id"] + ".json")
        sayfa = os.path.join(urun_dir, u["id"], "index.html")
        if not (os.path.exists(sema_yolu) and os.path.exists(sayfa)):
            continue
        with io.open(sema_yolu, encoding="utf-8") as f:
            sema = json.load(f)
        with io.open(sayfa, encoding="utf-8") as f:
            h = f.read()
        if "ozel-badge" not in h:
            duzen.append(u["id"] + ": rozet yok")
        if sema.get("tabanFiyatTL") is None:
            # fiyatsiz duzen: konfigurator fiyati "—" baslar, sabit fiyat basilmaz
            if 'id="opsiyonFiyat">&mdash;<' not in h and 'id="opsiyonFiyat">—<' not in h:
                duzen.append(u["id"] + ": fiyat '—' degil")
    kayit(6, "sari seri kurallari: yasak ifade yok + rozet/fiyatsiz duzen korunuyor",
          not bulunan and not duzen,
          "\n".join(["%s -> %s" % b for b in bulunan] + duzen))

    # ---------- TEST 7: KURULUM.md canlı testi (örnek ürün uçtan uca + temizlik) ----------
    with io.open(hacim_yolu, "rb") as f:
        hacim_oncesi = f.read()
    ornek_dosyalar = [
        os.path.join(JEN_DIR, "urunler", "ornek-plaka.json"),
        os.path.join(TEST_DIR, "aileler", "ornekplaka.js"),
        os.path.join(TEST_DIR, "esleme", "ornekplaka.json")]
    yesil7 = False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with io.open(os.path.join(tmp, "ornek-plaka.scad"), "w",
                         encoding="utf-8") as f:
                f.write("En = 60;\nBoy = 100;\nKalinlik = 3;\ncube([En, Boy, Kalinlik]);\n")
            with io.open(ornek_dosyalar[0], "w", encoding="utf-8") as f:
                json.dump({"id": "ornek-plaka", "hacimFormulu": "ornekplaka",
                           "parametreler": [
                               {"ad": "en", "etiket": "En", "birim": "mm", "tip": "sayi",
                                "min": 20, "max": 200, "adim": 1, "varsayilan": 60,
                                "aciklama": "Kisa kenar"},
                               {"ad": "boy", "etiket": "Boy", "birim": "mm", "tip": "sayi",
                                "min": 20, "max": 300, "adim": 1, "varsayilan": 100,
                                "aciklama": "Uzun kenar"},
                               {"ad": "kalinlik", "etiket": "Kalinlik", "birim": "mm",
                                "tip": "sayi", "min": 1, "max": 10, "adim": 0.5,
                                "varsayilan": 3, "aciklama": "Kalinlik"}],
                           "tabanHacimMm3": 18000, "tabanFiyatTL": None}, f)
            with io.open(ornek_dosyalar[1], "w", encoding="utf-8") as f:
                f.write("function ornekplaka(p) {\n  return p.en * p.boy * p.kalinlik;\n}\n")
            with io.open(ornek_dosyalar[2], "w", encoding="utf-8") as f:
                # "motor" ZORUNLU (2026-08-02): esleme hangi geometriye kalibre
                # oldugunu BEYAN eder; beyansiz esleme dogrula.py'de OLCULEMEDI.
                # Fikstur KURULUM.md'deki ornekle BIREBIR ayni kalmali.
                json.dump({"urunId": "ornek-plaka", "motor": "pruvo",
                           "scad": "ornek-plaka.scad",
                           "fonksiyon": "ornekplaka",
                           "esleme": {"en": "En", "boy": "Boy", "kalinlik": "Kalinlik"},
                           "sabit": {}}, f)
            ortam = dict(os.environ, PRUVO_SCAD_DIR=tmp)
            p = kos([sys.executable, os.path.join(TEST_DIR, "dogrula.py"),
                     "ornekplaka", "--set", "3", "--seed", "7"], env=ortam)
            print(p.stdout.rstrip())
            yesil7 = p.returncode == 0
    finally:
        for yol in ornek_dosyalar:
            if os.path.exists(yol):
                os.remove(yol)
        kos([sys.executable, os.path.join(TEST_DIR, "birlestir.py")])
    with io.open(hacim_yolu, "rb") as f:
        geri_geldi = f.read() == hacim_oncesi
    kayit(7, "KURULUM.md canli test (ornek urun ucta uca + temizlik izsiz)",
          yesil7 and geri_geldi)

    # ---------- TEST 8: kapsam (küme farkı) + açıklama tutarlılığı ----------
    # Kapsam = "şema tanımlı her parametrik ürün test ediliyor mu?" — SAYI DEĞİL KÜME.
    # Sabit sayı (eski hâli: len(urunler) == 18) katalog büyüyünce kapıyı sürekli
    # kırmızıya çakar; sürekli kırmızı nöbetçi = körelmiş nöbetçi.
    fonksiyonlar = hacim_fonksiyonlari()
    sema_dizin = os.path.join(JEN_DIR, "urunler")
    sema_tanimli = set(
        d[:-5] for d in os.listdir(sema_dizin) if d.endswith(".json")
    ) - SEMA_FIXTURE
    test_edilen = set(u["id"] for u in urunler)
    eksikler = ["KAPSAM DISI (sema var, test edilmiyor): " + uid
                for uid in sorted(sema_tanimli - test_edilen)]
    for u in urunler:
        uid = u["id"]
        sema_yolu = os.path.join(JEN_DIR, "urunler", uid + ".json")
        if not os.path.exists(sema_yolu):
            eksikler.append(uid + ": SEMA YOK"); continue
        with io.open(sema_yolu, encoding="utf-8") as f:
            sema = json.load(f)
        if sema.get("id") != uid:
            eksikler.append(uid + ": sema id uyusmuyor")
        if sema.get("hacimFormulu") not in fonksiyonlar:
            eksikler.append(uid + ": hacim fonksiyonu yok (%s)" % sema.get("hacimFormulu"))
        if not isinstance(sema.get("tabanHacimMm3"), (int, float)):
            eksikler.append(uid + ": tabanHacimMm3 sayisal degil")
        if not (sema.get("tabanFiyatTL") is None or
                isinstance(sema.get("tabanFiyatTL"), (int, float))):
            eksikler.append(uid + ": tabanFiyatTL null/sayi degil")
        aciklama = fold(u.get("aciklama"))
        eslesen = 0
        for prm in sema.get("parametreler", []):
            tip = prm.get("tip", "sayi")
            if tip == "sayi":
                for alan in ("ad", "min", "max", "adim", "varsayilan", "birim"):
                    if prm.get(alan) in (None, ""):
                        eksikler.append("%s.%s: '%s' alani eksik" %
                                        (uid, prm.get("ad"), alan))
            govde = fold(prm.get("etiket", "")) + " " + fold(prm.get("aciklama", ""))
            if any(k and k in aciklama for k in re.split(r"[^a-z0-9]+", govde) if len(k) >= 4):
                eslesen += 1
        if not sema.get("parametreler"):
            eksikler.append(uid + ": parametre listesi bos")
        elif eslesen == 0:
            eksikler.append(uid + ": hicbir parametre 'Neyi ayarliyoruz?' metniyle eslesmiyor")
    kayit(8, "kapsam %d/%d + sema-aciklama tutarliligi" %
          (len(sema_tanimli & test_edilen), len(sema_tanimli | test_edilen)),
          not eksikler, "\n".join(eksikler))

    # ---------- özet ----------
    kirmizi = [s for s in SONUC if not s[2]]
    butunluk = suite_butunlugu(SONUC)
    print("\n==== KABUL OZETI: %d/%d YESIL (beklenen %d test) ===="
          % (len(SONUC) - len(kirmizi), len(SONUC), len(BEKLENEN_TESTLER)))
    for no, ad, yesil in SONUC:
        print("  %s  #%d %s" % ("+" if yesil else "-", no, ad))
    for h in butunluk:
        print("  ❌ %s" % h)
    sys.exit(1 if (kirmizi or butunluk) else 0)


if __name__ == "__main__":
    main()

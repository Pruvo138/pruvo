#!/usr/bin/env python3
"""K50 KABUL BATARYASI — dal basina tek-sahip kaydi.

Bu dosya ANLATI DEGIL, KOSAN VAKADIR. Cividen cikan bes olcut ve karsiligi:

  ① kayit makine-okunur         -> K50-13-DURUM-MAKINE-OKUNUR
  ② YARIS PENCERESI yeniden     -> K50-2-YARIS-IKINCI-RED (iki oturum, sirali)
     uretilir                      K50-3-GERCEK-YARIS (24 surec, BARIYERLE ayni anda)
  ③ yanlis-pozitif nobeti       -> K50-4-YENIDEN-GIRIS / K50-5-KALP-ATISI /
     (sahip kendi dalinda devam)     K50-6-BASKA-DAL
  ④ hedef-kol atifli mutant     -> AYRI DOSYA: tools/dal-sahibi-mutasyon.py
  ⑤ bayat sahiplik kolu         -> K50-7-BAYAT-DEVIR (zaman tavani) /
     (sonsuz kilit YOK)              K50-8-ACIK-DEVIR / K50-9-GEREKCESIZ-DEVIR-RED

Ayrica YASAK maddesi "sahipsiz kaldiginda fail-open birakma":
  K50-10-BOZUK-TAZE-SAHIPLI (bozuk kayit SERBEST sayilmaz).

GERCEK YARIS NASIL URETILIYOR (K50-3): `multiprocessing` fork baglami + `Barrier`.
24 surec fork edilir, hepsi bariyerde bekler, bariyer acilinca MIKROSANIYELER icinde
ayni kayda `al` cagirir. Bu, "subprocess baslatma jitteri yuzunden aslinda sirali kosan
sahte yaris" tuzagini kapatir — mutasyon takimi bu vakayi kilit kolu olmadan kosturunca
BIRDEN COK kazanan cikar (bkz tools/dal-sahibi-mutasyon.py).

KOSUM
  python3 tools/dal-sahibi-test.py            # insan okunur
  python3 tools/dal-sahibi-test.py --json     # mutasyon takimi bunu okur
Cikis: 0 = hepsi GECTI, 1 = en az bir vaka KALDI.
"""
import contextlib
import importlib.util
import io
import json
import multiprocessing as mp
import os
import shutil
import sys
import tempfile

VARSAYILAN_ARAC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dal_sahibi.py")
YARIS_SUREC = 24


def arac_yukle():
    """Olculecek araci dosyadan yukler. Mutasyon takimi PRUVO_DAL_SAHIBI_YOL ile
    MUTANT KOPYAYI gosterir — fikstur kendi kodunu degil, gosterileni olcer."""
    yol = os.environ.get("PRUVO_DAL_SAHIBI_YOL") or VARSAYILAN_ARAC
    spec = importlib.util.spec_from_file_location("dal_sahibi_olculen", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kos(mod, argv):
    """Araci SUREC ICINDE cagirir; (rc, stdout) doner."""
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        try:
            rc = mod.ana(argv)
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 2
    return rc, tampon.getvalue().strip()


def hukum(cikti):
    for parca in cikti.split():
        if parca.startswith("HUKUM="):
            return parca.split("=", 1)[1]
    return "?"


def kol(cikti):
    for parca in cikti.split():
        if parca.startswith("KOL="):
            return parca.split("=", 1)[1]
    return "?"


# ------------------------------------------------------- GERCEK YARIS (K50-3)
def _yaris_cocuk(bariyer, kuyruk, indeks, kok, arac_yolu, dal):
    os.environ["PRUVO_DAL_SAHIP_KOK"] = kok
    if arac_yolu:
        os.environ["PRUVO_DAL_SAHIBI_YOL"] = arac_yolu
    mod = arac_yukle()
    try:
        bariyer.wait()
    except Exception:
        pass
    rc, cikti = kos(mod, ["al", "--dal", dal, "--sahip", "YARIS-%02d" % indeks])
    kuyruk.put((indeks, rc, hukum(cikti)))


def gercek_yaris(kok, arac_yolu, dal, surec=YARIS_SUREC):
    """N sureci BARIYERLE ayni anda saliverir; (kazanan_sayisi, red_sayisi, hata) doner."""
    ctx = mp.get_context("fork")
    bariyer = ctx.Barrier(surec)
    kuyruk = ctx.Queue()
    cocuklar = []
    for i in range(surec):
        p = ctx.Process(target=_yaris_cocuk,
                        args=(bariyer, kuyruk, i, kok, arac_yolu, dal))
        p.start()
        cocuklar.append(p)
    sonuclar = []
    for _ in range(surec):
        sonuclar.append(kuyruk.get(timeout=60))
    for p in cocuklar:
        p.join(timeout=60)
    kazanan = [s for s in sonuclar if s[1] == 0]
    red = [s for s in sonuclar if s[1] == 1]
    hata = [s for s in sonuclar if s[1] not in (0, 1)]
    return len(kazanan), len(red), len(hata)


# ------------------------------------------------------------------- VAKALAR
def vakalar(mod, kok, arac_yolu):
    sonuc = []

    def ekle(ad, gecti, ayrinti):
        sonuc.append((ad, bool(gecti), ayrinti))

    D1, D2, D3, D4, D5 = ("kral/d1-tavsiye-kolon", "kral/yaris-dali",
                          "kral/ucuncu-dal", "kral/bayat-dal", "kral/bozuk-dal")

    # ① + taban: ilk al
    rc, c = kos(mod, ["al", "--dal", D1, "--sahip", "OTURUM-A", "--not", "K50 merge olcumu"])
    ekle("K50-1-ILK-AL", rc == 0 and hukum(c) == "ALINDI",
         "rc=%s hukum=%s" % (rc, hukum(c)))

    # ② YARIS PENCERESI — ikinci oturum ayni dali almaya calisir
    rc, c = kos(mod, ["al", "--dal", D1, "--sahip", "OTURUM-B"])
    ekle("K50-2-YARIS-IKINCI-RED", rc == 1 and hukum(c) == "SAHIPLI",
         "rc=%s hukum=%s kol=%s (beklenen rc=1 SAHIPLI)" % (rc, hukum(c), kol(c)))

    # ② GERCEK ES ZAMANLI YARIS — 24 surec, bariyerle
    kazanan, red, hata = gercek_yaris(kok, arac_yolu, D2)
    ekle("K50-3-GERCEK-YARIS", kazanan == 1 and red == YARIS_SUREC - 1 and hata == 0,
         "surec=%d kazanan=%d red=%d hata=%d (beklenen kazanan=1)"
         % (YARIS_SUREC, kazanan, red, hata))

    # ③ YANLIS-POZITIF NOBETI — sahip kendi dalinda devam edebilmeli
    rc, c = kos(mod, ["al", "--dal", D1, "--sahip", "OTURUM-A"])
    ekle("K50-4-YENIDEN-GIRIS", rc == 0 and hukum(c) == "SAHIP-BEN",
         "rc=%s hukum=%s (kilit kendi sahibini BLOKLAMAMALI)" % (rc, hukum(c)))

    rc, c = kos(mod, ["dokun", "--dal", D1, "--sahip", "OTURUM-A"])
    ekle("K50-5-KALP-ATISI", rc == 0 and hukum(c) == "DOKUNULDU",
         "rc=%s hukum=%s" % (rc, hukum(c)))

    rc, c = kos(mod, ["al", "--dal", D3, "--sahip", "OTURUM-A"])
    ekle("K50-6-BASKA-DAL", rc == 0 and hukum(c) == "ALINDI",
         "rc=%s hukum=%s (sahip BASKA dali da alabilmeli)" % (rc, hukum(c)))

    # ⑤ BAYAT KOLU — zaman tavani asilinca devralinabilir (sonsuz kilit YOK)
    kos(mod, ["al", "--dal", D4, "--sahip", "OLU-OTURUM", "--tavan-sn", "0"])
    rc, c = kos(mod, ["al", "--dal", D4, "--sahip", "OTURUM-C"])
    ekle("K50-7-BAYAT-DEVIR", rc == 0 and hukum(c) == "BAYAT-DEVIR",
         "rc=%s hukum=%s kol=%s (tavan asildi -> devralinabilir)" % (rc, hukum(c), kol(c)))

    # ⑤ ACIK DEVIR — gerekceli
    rc, c = kos(mod, ["devral", "--dal", D1, "--sahip", "OTURUM-D",
                      "--gerekce", "A oturumu panelden kapandi"])
    ekle("K50-8-ACIK-DEVIR",
         rc == 0 and hukum(c) == "DEVRALINDI" and "ONCEKI=OTURUM-A" in c,
         "rc=%s hukum=%s cikti=%s" % (rc, hukum(c), c.splitlines()[0] if c else ""))

    # ⑤ ACIK DEVIR gerekcesiz REDDEDILIR (sessiz calma yok)
    rc, c = kos(mod, ["devral", "--dal", D3, "--sahip", "OTURUM-E"])
    ekle("K50-9-GEREKCESIZ-DEVIR-RED", rc == 2 and hukum(c) == "RED",
         "rc=%s hukum=%s (gerekcesiz devralma RED olmali)" % (rc, hukum(c)))

    # YASAK: fail-open birakma — bozuk ama TAZE kayit SERBEST sayilmaz
    kos(mod, ["al", "--dal", D5, "--sahip", "OTURUM-F"])
    bozuk_yol = os.path.join(mod.kayit_koku(), mod._slug(D5))
    with open(bozuk_yol, "w", encoding="utf-8") as f:
        f.write("{bu json degil")
    rc, c = kos(mod, ["al", "--dal", D5, "--sahip", "OTURUM-G"])
    ekle("K50-10-BOZUK-TAZE-SAHIPLI",
         rc == 1 and hukum(c) == "SAHIPLI" and kol(c) == "OKUNAMAZ",
         "rc=%s hukum=%s kol=%s (bozuk+taze kayit fail-CLOSED olmali)"
         % (rc, hukum(c), kol(c)))

    # birak -> serbest kalir
    rc1, _ = kos(mod, ["birak", "--dal", D3, "--sahip", "OTURUM-A"])
    rc2, c2 = kos(mod, ["al", "--dal", D3, "--sahip", "OTURUM-H"])
    ekle("K50-11-BIRAK-SONRASI-SERBEST",
         rc1 == 0 and rc2 == 0 and hukum(c2) == "ALINDI",
         "birak_rc=%s al_rc=%s hukum=%s" % (rc1, rc2, hukum(c2)))

    # baskasinin kaydini birakamazsin
    rc, c = kos(mod, ["birak", "--dal", D1, "--sahip", "OTURUM-Z"])
    ekle("K50-12-BASKASININ-KAYDINI-BIRAKAMAZ", rc == 1 and hukum(c) == "SAHIPLI",
         "rc=%s hukum=%s" % (rc, hukum(c)))

    # ① kayit MAKINE-OKUNUR
    rc, c = kos(mod, ["durum", "--json"])
    okunur = False
    ayrinti = "cozulemedi"
    try:
        veri = json.loads(c)
        sahipler = {k["dal"]: k["sahip"] for k in veri["kayitlar"] if k.get("dal")}
        okunur = (rc == 0 and sahipler.get(D1) == "OTURUM-D"
                  and sahipler.get(D4) == "OTURUM-C" and veri["kayit_sayisi"] >= 4)
        ayrinti = "kayit_sayisi=%s D1_sahip=%s D4_sahip=%s" % (
            veri.get("kayit_sayisi"), sahipler.get(D1), sahipler.get(D4))
    except Exception as e:
        ayrinti = "JSON cozulemedi: %s" % e
    ekle("K50-13-DURUM-MAKINE-OKUNUR", okunur, ayrinti)

    # ① KAYIT GERCEKTEN TEK MI — butun worktree'ler AYNI koke cozmeli.
    # Bu vaka `PRUVO_DAL_SAHIP_KOK` zorlamasini ATLAR ve `_git_ortak_dizin`i
    # DOGRUDAN olcer; yoksa fikstur hep gecici dizine yazar ve K50'nin ta kendisi
    # (dal kaydi worktree basina AYRISIRSA yaris kapanmaz) olculmeden kalir.
    bura = os.path.dirname(os.path.abspath(__file__))
    ana_git = mod._git_ortak_dizin(bura)
    kokler = {}
    esit = False
    try:
        wt_kayit = os.path.join(ana_git or "", "worktrees")
        adaylar = [bura]
        for ad in sorted(os.listdir(wt_kayit)):
            gd = os.path.join(wt_kayit, ad, "gitdir")
            with open(gd, encoding="utf-8") as f:
                adaylar.append(os.path.dirname(f.read().strip()))
        adaylar.append(os.path.dirname(ana_git))  # ana checkout koku
        for a in adaylar:
            if os.path.isdir(a):
                kokler[a] = mod._git_ortak_dizin(a)
        cozulen = set(kokler.values())
        esit = (len(cozulen) == 1 and ana_git in cozulen
                and os.path.basename(ana_git) == ".git" and len(kokler) >= 3)
    except Exception:
        pass
    ayrinti2 = "agac=%d cozulen_kok=%s (hepsi TEK koke cozmeli)" % (
        len(kokler), sorted(set(kokler.values())))
    ekle("K50-14-ORTAK-KOK-TEK", esit, ayrinti2)

    return sonuc


def ana(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    json_mu = "--json" in argv
    arac_yolu = os.environ.get("PRUVO_DAL_SAHIBI_YOL") or ""
    kok = tempfile.mkdtemp(prefix="k50-dal-sahip-")
    os.environ["PRUVO_DAL_SAHIP_KOK"] = kok
    try:
        mod = arac_yukle()
        sonuc = vakalar(mod, kok, arac_yolu)
    finally:
        shutil.rmtree(kok, ignore_errors=True)  # DISK KURALI: uretecen temizler

    gecen = sum(1 for _, g, _ in sonuc if g)
    if json_mu:
        print(json.dumps({
            "arac": arac_yolu or VARSAYILAN_ARAC,
            "toplam": len(sonuc), "gecen": gecen,
            "vakalar": {ad: {"gecti": g, "ayrinti": a} for ad, g, a in sonuc},
        }, ensure_ascii=False, sort_keys=True))
    else:
        print("K50 KABUL BATARYASI — arac=%s" % (arac_yolu or VARSAYILAN_ARAC))
        for ad, g, a in sonuc:
            print("  %-32s %s  %s" % (ad, "GECTI" if g else "KALDI", a))
        print("K50 KABUL=%d/%d HUKUM=%s"
              % (gecen, len(sonuc), "YESIL" if gecen == len(sonuc) else "KIRMIZI"))
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(ana())

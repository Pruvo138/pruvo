#!/usr/bin/env python3
"""K260 KOSUM PAKETI — adimlari SIRAYLA kosar, ham ciktiyi ve GERCEK rc'yi yazar.

CHIP: KraL-K260KatSec.

NEDEN BETIK: isci "kostum" der ama ciktiyi uydurabilir
([[ucuz-isci-yesil-tablo-uydurur]] · [[isci-yesil-tablo-ic-olcumu-bosaltir]]).
Bu betik her adimi `subprocess` ile kosar, stdout+stderr'i AYNEN dosyaya yazar ve
rc'yi BORUSUZ olcer ([[boru-rc-isci-olcumunu-yalanlar]]). Isci yalniz bu betigi
kosturur; hukmu mimar HAM DOSYADAN okur.

KOSUM:
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz taban
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz kur
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz kabul
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz tur-kuru
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz tur-canli
"""

import argparse
import os
import subprocess
import sys

CRON = "/Users/okan/.claude/cron"
BU_DIZIN = os.path.dirname(os.path.abspath(__file__))
KUR = os.path.join(BU_DIZIN, "k260-kur.py")
BATARYA = os.path.join(CRON, "nobet-kat-kovasi-test.py")
NOBET_KAPI = os.path.join(CRON, "nobet-kapi.py")

# Regresyon tabani (ONCE=SONRA). Taban kirmizisi K260'in kapsami DEGILDIR ama
# YAZILIR ([[olcut-civilenirken-taban-olculmeli]]).
REGRESYON = (
    ("regresyon-nobet-kabul", [sys.executable,
                               os.path.join(CRON, "nobet-kabul-test.py")]),
    ("regresyon-nobet-kapi-mutasyon",
     [sys.executable, os.path.join(CRON, "nobet-kapi-mutasyon.py")]),
    ("regresyon-sayac-durustluk",
     [sys.executable,
      "/Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py"]),
)

FAZLAR = {
    "taban": REGRESYON + (
        ("taban-kurulum-olcumu", [sys.executable, KUR]),
    ),
    "kur": (
        ("kurulum", [sys.executable, KUR, "--uygula"]),
    ),
    # Tur-1 yamasini geri alip DUZELTILMIS yamayi uygular (ankorlar ORIJINAL
    # metne yaslidir; ustune yazmak ANKOR_YOK verirdi).
    "geri-al": (),   # komutu `--damga` ile main() kurar
    "temizlik": (),  # main() dogrudan temizlik() cagirir
    "kutu-rotasyon": (),  # main() dogrudan kutu_rotasyon() cagirir
    "defter-rotasyon": (),  # main() dogrudan defter_rotasyon() cagirir
    # --- K271: damga tasima onarimi + dusmus damganin geri yuklenmesi ---
    "k271-taban": REGRESYON + (
        ("k271-taban-kurulum", [sys.executable, os.path.join(
            os.path.dirname(BU_DIZIN), "k271", "k271-kur.py")]),
        ("k271-taban-k260-batarya", [sys.executable, BATARYA]),
        ("k271-taban-kova", [sys.executable, BATARYA, "--canli"]),
    ),
    "k271-kur": (
        ("k271-kurulum", [sys.executable, os.path.join(
            os.path.dirname(BU_DIZIN), "k271", "k271-kur.py"), "--uygula"]),
    ),
    "k271-geri-yukle": (
        ("k271-geri-yukle-KURU", [sys.executable, os.path.join(
            os.path.dirname(BU_DIZIN), "k271", "k271-kur.py"),
            "--geri-yukle", "--kuru"]),
        ("k271-geri-yukle-GERCEK", [sys.executable, os.path.join(
            os.path.dirname(BU_DIZIN), "k271", "k271-kur.py"), "--geri-yukle"]),
    ),
    "k271-kabul": (
        ("k271-batarya", [sys.executable,
                          os.path.join(CRON, "nobet-damga-tasima-test.py")]),
        ("k271-mutasyon", [sys.executable,
                           os.path.join(CRON, "nobet-damga-tasima-test.py"),
                           "--mutasyon"]),
        ("k271-k260-batarya-REGRESYON", [sys.executable, BATARYA]),
        ("k271-kova-SONRA", [sys.executable, BATARYA, "--canli"]),
    ) + tuple(("k271-sonra-" + ad, komut) for ad, komut in REGRESYON),
    # Kapanis turu: defter satirinin KABUL KOMUTU birebir kosulur (kapanis
    # hukmu KOSAN TESTTEN okunur, beyandan DEGIL), + kova + kuru tur.
    "k271-kapanis": (
        ("k271-KABUL-KOMUTU", [sys.executable,
                               os.path.join(CRON, "nobet-damga-tasima-test.py")]),
        ("k271-kapanis-mutasyon",
         [sys.executable, os.path.join(CRON, "nobet-damga-tasima-test.py"),
          "--mutasyon"]),
        ("k271-kapanis-kova", [sys.executable, BATARYA, "--canli"]),
        ("k271-kapanis-tur-kuru",
         [sys.executable, NOBET_KAPI, "--tur-kapat", "--kuru"]),
    ),
    "k271-tur-kuru": (
        ("k271-tur-kuru", [sys.executable, NOBET_KAPI, "--tur-kapat", "--kuru"]),
    ),
    "k271-tur-canli": (
        ("k271-tur-canli", [sys.executable, NOBET_KAPI, "--tur-kapat"]),
    ),
    # Merge oncesi kapi turu. CI KAPSAM kapisi IKI AGACTA da olculur: kardes
    # mimarin komutu ANA agaci gosteriyordu ama gerekcesi "dalin dosyalari ana
    # agacta gorunmez, sahte yesil verir" diyordu — celiski ikisini de olcup
    # ETIKETLEYEREK cozulur, tahminle DEGIL.
    "merge-kapisi": (
        ("ci-kapsam-DALDA", [sys.executable, os.path.join(
            os.path.dirname(BU_DIZIN), "ci-kapsam-test.py")]),
        ("ci-kapsam-ANA-AGACTA", [sys.executable,
                                  "/Users/okan/dev/pruvo/tools/ci-kapsam-test.py"]),
        ("defter-kota-TAZE", [sys.executable,
                              "/Users/okan/dev/pruvo/tools/defter-kota-kapisi.py"]),
        ("batarya-TAZE", [sys.executable, os.path.join(
            BU_DIZIN, "nobet-kat-kovasi-test.py")]),
    ),
    "kabul": (
        ("kabul-batarya", [sys.executable, BATARYA]),
        ("mutasyon", [sys.executable, BATARYA, "--mutasyon"]),
        ("canli-kova-olcumu", [sys.executable, BATARYA, "--canli"]),
    ) + tuple(("sonra-" + ad, komut) for ad, komut in REGRESYON),
    "tur-kuru": (
        ("tur-kuru", [sys.executable, NOBET_KAPI, "--tur-kapat", "--kuru"]),
    ),
    "tur-canli": (
        ("tur-canli", [sys.executable, NOBET_KAPI, "--tur-kapat"]),
    ),
    # Dagitim SONRASI kuru tur: dagitilan kalem UCUSTA gorunuyor mu?
    "tur-kuru2": (
        ("tur-kuru2", [sys.executable, NOBET_KAPI, "--tur-kapat", "--kuru"]),
    ),
}


# 🔴 DISK — OKAN KURALI: ureten temizler. Kanit dizinleri ve SUPERSEDE olmus
# tur-1 yedekleri silinir; AKTIF `--geri-al` yolu (tur-2 yedegi) KALIR.
TEMIZLENECEK = (
    os.path.join(CRON, "k260-kanit"),
    os.path.join(CRON, "k260-kanit2"),
    os.path.join(CRON, "k260-temizlik-izi"),   # bu kosumun kendi izi
    os.path.join(CRON, "k260-merge-kanit"),
    os.path.join(CRON, "k260-kutu-kanit"),
    os.path.join(CRON, "k260-defter-kanit"),
    os.path.join(CRON, "k271-kanit"),
    os.path.join(CRON, "k271-kanit2"),
    os.path.join(CRON, "k271-kapanis-kanit"),
    os.path.join(CRON, "nobet-kapi.py.yedek-k260-20260824T125221Z"),
    os.path.join(CRON, "testler.py.yedek-k260-20260824T125221Z"),
)
KORUNAN = (
    os.path.join(CRON, "nobet-kapi.py.yedek-k260-20260824T125857Z"),
    os.path.join(CRON, "testler.py.yedek-k260-20260824T125857Z"),
)
# K271 yedekleri KORUNUR: canli yamanin ve VERI ONARIMININ tek geri donus yolu.
# Ozellikle `nobet-geri-iz.json.yedek-k271-*` — veri onarimi geri alinamazsa
# damga restorasyonu tek yonlu bir islem olurdu.
KORUNAN_ONEK = (os.path.join(CRON, "nobet-kapi.py.yedek-k271-"),
                os.path.join(CRON, "testler.py.yedek-k271-"),
                os.path.join(CRON, "nobet-geri-iz.json.yedek-k271-"))


def _boyut_kb(yol):
    """du -sk esdegeri (blok degil bayt tabanli; hukum SAYIYLA basilir)."""
    if os.path.isfile(yol):
        return os.path.getsize(yol) // 1024
    toplam = 0
    for kok, _, dosyalar in os.walk(yol):
        for d in dosyalar:
            try:
                toplam += os.path.getsize(os.path.join(kok, d))
            except OSError:
                pass
    return toplam // 1024


def temizlik():
    import shutil as _sh
    once = 0
    for yol in TEMIZLENECEK:
        var = os.path.exists(yol)
        kb = _boyut_kb(yol) if var else 0
        once += kb
        print("ONCE %-62s VAR=%s KB=%d" % (yol, "E" if var else "H", kb))
    for yol in TEMIZLENECEK:
        if os.path.isdir(yol):
            _sh.rmtree(yol, ignore_errors=True)
        elif os.path.isfile(yol):
            os.remove(yol)
    sonra = 0
    kalan = 0
    for yol in TEMIZLENECEK:
        var = os.path.exists(yol)
        kb = _boyut_kb(yol) if var else 0
        sonra += kb
        kalan += 1 if var else 0
        print("SONRA %-61s VAR=%s KB=%d" % (yol, "E" if var else "H", kb))
    for yol in KORUNAN:
        print("KORUNAN %-59s VAR=%s KB=%d"
              % (yol, "E" if os.path.exists(yol) else "H", _boyut_kb(yol)))
    for ad in sorted(os.listdir(CRON)):
        tam = os.path.join(CRON, ad)
        if any(tam.startswith(o) for o in KORUNAN_ONEK):
            print("KORUNAN %-59s VAR=E KB=%d" % (tam, _boyut_kb(tam)))
    print("TEMIZLIK ONCE_KB=%d SONRA_KB=%d KAZANC_KB=%d KALAN_HEDEF=%d"
          % (once, sonra, once - sonra, kalan))
    print("HUKUM=%s" % ("TEMIZ" if kalan == 0 else "KALINTI_VAR"))
    return 0 if kalan == 0 else 1


KUTU = ("/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/"
        "mimar-posta-kutusu.md")
KUTU_ARSIV = ("/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/"
              "mimar-posta-kutusu-arsiv.md")
KUTU_ARACI = "/Users/okan/dev/pruvo/tools/kutu-arsivle.py"
KOTA_KAPISI = "/Users/okan/dev/pruvo/tools/defter-kota-kapisi.py"


def _blok_basliklari(yol):
    """Kutudaki `## ` blok baslıklarini SIRAYLA dondurur."""
    try:
        with open(yol, encoding="utf-8") as d:
            return [s.rstrip("\n") for s in d if s.startswith("## ")]
    except OSError:
        return []


def _olc(yol):
    try:
        with open(yol, "rb") as d:
            ham = d.read()
        return ham.count(b"\n"), len(ham)
    except OSError:
        return 0, 0


def kutu_rotasyon(dizin):
    """🔴 LOSSLESS iddiasi ARACIN SOZUNE BIRAKILMAZ: kutu+arsiv blok envanteri
    ONCE ve SONRA cikarilir, KAYBOLAN baslik kumesi ayrica hesaplanir."""
    os.makedirs(dizin, exist_ok=True)
    once_k, once_kb = _olc(KUTU)
    once_a, once_ab = _olc(KUTU_ARSIV)
    once_basliklar = _blok_basliklari(KUTU)
    once_arsiv_basliklar = _blok_basliklari(KUTU_ARSIV)
    print("ONCE kutu_satir=%d kutu_bayt=%d arsiv_satir=%d arsiv_bayt=%d "
          "kutu_blok=%d arsiv_blok=%d"
          % (once_k, once_kb, once_a, once_ab,
             len(once_basliklar), len(once_arsiv_basliklar)))

    kos("kutu-arsivle-KURU", [sys.executable, KUTU_ARACI, "--kuru"], dizin)
    kos("kutu-arsivle-GERCEK", [sys.executable, KUTU_ARACI], dizin)

    sonra_k, sonra_kb = _olc(KUTU)
    sonra_a, sonra_ab = _olc(KUTU_ARSIV)
    sonra_basliklar = _blok_basliklari(KUTU)
    sonra_arsiv_basliklar = _blok_basliklari(KUTU_ARSIV)
    print("SONRA kutu_satir=%d kutu_bayt=%d arsiv_satir=%d arsiv_bayt=%d "
          "kutu_blok=%d arsiv_blok=%d"
          % (sonra_k, sonra_kb, sonra_a, sonra_ab,
             len(sonra_basliklar), len(sonra_arsiv_basliklar)))

    # LOSSLESS: ONCE'ki her baslik ya kutuda ya arsivde DURMALI.
    once_kume = set(once_basliklar) | set(once_arsiv_basliklar)
    sonra_kume = set(sonra_basliklar) | set(sonra_arsiv_basliklar)
    kayip = sorted(once_kume - sonra_kume)
    tasinan = sorted(set(once_basliklar) - set(sonra_basliklar))
    for b in tasinan:
        print("TASINAN_BLOK %s" % b[:150])
    for b in kayip:
        print("!! KAYIP_BLOK %s" % b[:150])
    lossless = "GECTI" if not kayip else "DUSTU"
    print("KUTU_ROTASYON once_satir=%d sonra_satir=%d tasinan_blok=%d "
          "lossless=%s" % (once_k, sonra_k, len(tasinan), lossless))
    print("BLOK_KORUNUMU once_toplam=%d sonra_toplam=%d kayip=%d"
          % (len(once_kume), len(sonra_kume), len(kayip)))
    rc = kos("kota-ROTASYON-SONRASI", [sys.executable, KOTA_KAPISI], dizin)
    print("KOTA_SONRASI_RC=%d" % rc)
    return 0 if lossless == "GECTI" else 1


DEVAM = "/Users/okan/dev/pruvo/DEVAM.md"
DEVAM_ARSIV = "/Users/okan/dev/pruvo/DEVAM-ARSIV.md"
DEFTER_ARACI = "/Users/okan/dev/pruvo/tools/defter-rotasyon.py"
# Kardes mimarin bu turda ekledigi YENI satirlar — tasima bolgesine DUSMEMELI.
KORUNMASI_GEREKEN = ("K271", "K275")


def _satir_kumesi(yol):
    """Bos olmayan satirlarin KUMESI — lossless icin en sert olcum."""
    try:
        with open(yol, encoding="utf-8") as d:
            return set(s.strip() for s in d if s.strip())
    except OSError:
        return set()


def defter_rotasyon(dizin):
    """🔴 DEVAM.md rotasyonu. Lossless ARACIN SOZUNE BIRAKILMAZ: DEVAM.md +
    DEVAM-ARSIV.md'nin BOS OLMAYAN SATIR KUMESI once/sonra karsilastirilir."""
    os.makedirs(dizin, exist_ok=True)

    def _durum(etiket):
        d_s, d_b = _olc(DEVAM)
        a_s, a_b = _olc(DEVAM_ARSIV)
        print("%s devam_satir=%d devam_bayt=%d arsiv_satir=%d arsiv_bayt=%d"
              % (etiket, d_s, d_b, a_s, a_b))
        return d_s, d_b, a_s, a_b

    once_kume = _satir_kumesi(DEVAM) | _satir_kumesi(DEVAM_ARSIV)
    once_devam = _satir_kumesi(DEVAM)
    o_ds, o_db, o_as, o_ab = _durum("ONCE")
    for jeton in KORUNMASI_GEREKEN:
        print("ONCE_JETON %s devam_md=%s"
              % (jeton, "VAR" if any(jeton in s for s in once_devam) else "YOK"))

    # 🔴 ARAC IKI KONUMSAL ARGUMAN ISTER (`defter arsiv`) — olculdu: argumansiz
    # cagri argparse `error: the following arguments are required` ile rc=2
    # doner ve HICBIR SEY TASIMAZ. O hal "NO-OP" DEGILDIR, "KOSMADI"dir; ikisini
    # ayni kovaya koymak K272'ye SAHTE kanit yazdirirdi.
    kanonik = [sys.executable, DEFTER_ARACI, DEVAM, DEVAM_ARSIV,
               "--tavan-kaynaktan", "--isaretciye-indir"]
    acik_hedef = [sys.executable, DEFTER_ARACI, DEVAM, DEVAM_ARSIV,
                  "--tavan-bayt", "11400"]

    rc1 = kos("defter-rotasyon-KANONIK", kanonik, dizin)
    ara = _durum("KANONIK_SONRASI")
    degismedi = (ara[0], ara[1]) == (o_ds, o_db)
    # UC HAL: KOSMADI (rc!=0) · NO_OP (rc=0 ama dosya degismedi) · TASIDI.
    print("KANONIK_HAL=%s rc=%d"
          % ("KOSMADI" if rc1 != 0 else ("NO_OP" if degismedi else "TASIDI"),
             rc1))

    rc2 = kos("defter-rotasyon-ACIK-HEDEF", acik_hedef, dizin)
    s_ds, s_db, s_as, s_ab = _durum("SONRA")
    print("ACIK_HEDEF_HAL=%s rc=%d"
          % ("KOSMADI" if rc2 != 0
             else ("NO_OP" if (s_ds, s_db) == (ara[0], ara[1]) else "TASIDI"),
             rc2))

    sonra_devam = _satir_kumesi(DEVAM)
    sonra_kume = sonra_devam | _satir_kumesi(DEVAM_ARSIV)
    kayip = sorted(once_kume - sonra_kume)
    tasinan = sorted(once_devam - sonra_devam)
    for s in tasinan[:40]:
        print("TASINAN_SATIR %s" % s[:150])
    if len(tasinan) > 40:
        print("TASINAN_SATIR ... (+%d satir daha)" % (len(tasinan) - 40))
    for s in kayip:
        print("!! KAYIP_SATIR %s" % s[:150])
    for jeton in KORUNMASI_GEREKEN:
        print("SONRA_JETON %s devam_md=%s"
              % (jeton, "VAR" if any(jeton in s for s in sonra_devam) else "YOK"))

    lossless = "GECTI" if not kayip else "DUSTU"
    print("DEFTER_ROTASYON once_bayt=%d sonra_bayt=%d tasinan_satir=%d "
          "lossless=%s" % (o_db, s_db, len(tasinan), lossless))
    print("SATIR_KORUNUMU once_toplam=%d sonra_toplam=%d kayip=%d"
          % (len(once_kume), len(sonra_kume), len(kayip)))
    print("BAYT_DEVRI devam_delta=%d arsiv_delta=%d"
          % (s_db - o_db, s_ab - o_ab))
    rc = kos("kota-DEFTER-SONRASI", [sys.executable, KOTA_KAPISI], dizin)
    print("KOTA_SONRASI_RC=%d" % rc)
    return 0 if lossless == "GECTI" else 1


def kos(ad, komut, dizin):
    yol = os.path.join(dizin, "%s.txt" % ad)
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=1500)
        govde = p.stdout + p.stderr
        rc = p.returncode
    except subprocess.TimeoutExpired:
        govde, rc = "ZAMAN_ASIMI 1500 sn\n", 124
    except OSError as hata:
        govde, rc = "KOSULAMADI: %s\n" % hata, 127
    with open(yol, "w", encoding="utf-8") as d:
        d.write("KOMUT=%s\n" % " ".join(komut))
        d.write(govde)
        d.write("\nGERCEK_RC=%d\n" % rc)
    print("ADIM=%-34s RC=%d DOSYA=%s" % (ad, rc, yol))
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description="K260 kosum paketi")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--faz", required=True, choices=sorted(FAZLAR))
    ap.add_argument("--damga", help="faz=geri-al icin kurulum damgasi")
    args = ap.parse_args(argv)
    os.makedirs(args.cikti, exist_ok=True)
    adimlar = FAZLAR[args.faz]
    if args.faz == "temizlik":
        return temizlik()
    if args.faz == "kutu-rotasyon":
        return kutu_rotasyon(args.cikti)
    if args.faz == "defter-rotasyon":
        return defter_rotasyon(args.cikti)
    if args.faz == "geri-al":
        if not args.damga:
            print("HUKUM=OLCULEMEDI sebep=damga_verilmedi")
            return 2
        adimlar = (("geri-al", [sys.executable, KUR, "--geri-al", args.damga]),
                   ("geri-al-sonrasi-olcum", [sys.executable, KUR]))
    rcler = []
    for ad, komut in adimlar:
        rcler.append((ad, kos(ad, komut, args.cikti)))
    print("FAZ=%s ADIM=%d RC_SIFIR=%d"
          % (args.faz, len(rcler), sum(1 for _, r in rcler if r == 0)))
    for ad, r in rcler:
        print("OZET %s=%d" % (ad, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())

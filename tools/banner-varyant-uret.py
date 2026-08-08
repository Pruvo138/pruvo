#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ana sayfa banner'larinin duyarli varyantlarini URETIR (yerel) — R2'ye YAZMAZ.

NEDEN REPODA DURUYOR: 9 Agu 2026'da WebP varyantlari uretildi ama URETEN BETIK
BIRAKILMADI; AVIF turunda kaynak anahtarlarin ne oldugu ancak eski bir commit'in
index.html'inden GERI CIKARILABILDI. Uretim hatti = kanit; anlatilan hat kanit degildir
([[mutasyon-kaniti-yeniden-uretilebilir]]). Merdiven degistiginde BU dosya guncellenir.

KAYNAK = R2'deki ORIJINAL banner JPEG'leri. WebP'den transcode EDILMEZ: zaten kayipli
bir gorseli yeniden kayipli kodlamak jenerasyon kaybi uretir; her varyant orijinalden
TEK kayipli gecisle turer.

HAT: orijinal JPEG -> sips (lossless PNG ara adim, olcekleme) -> avifenc -q 65.
Cikti gecici bir dizine yazilir; repoya GORSEL GIRMEZ (CLAUDE.md: gorseller yalniz R2).

Kullanim:
    python3 tools/banner-varyant-uret.py [--cikti <dizin>]
Cikti: olcum tablosu (WebP q80 vs AVIF q65, toplam + MOBILDE SECILEN kume) ve
       <cikti>/yukleme-ciftleri.txt — tools/r2-upload.py'ye verilecek <yerel> <anahtar>
       ciftleri. BU BETIK R2'YE TEK BAYT YAZMAZ.
"""
import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
BASE = "https://media.pruvo3d.com/"

# [[r2-urllib-ua-403-tuzagi]]: ciplak urllib UA'si kenar tarafindan 403 alir.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

SIPS = "/usr/bin/sips"
AVIFENC = "/opt/homebrew/bin/avifenc"

KALITE = "65"   # avifenc -q (0-100). WebP tarafi q80 idi; AVIF q65 gorsel olarak denk.
HIZ = "4"       # -s 4: yavas ama kucuk (tek seferlik uretim, CI'da kosmaz)

# 🔴 MERDIVEN TEK KAYNAK: genislikler index.html'deki srcset ile AYNI olmak ZORUNDA;
# ayrisirsa tools/lcp-onculuk-kapisi.py::A7 kirmizi yakar (dosya adi <-> `w` tutarliligi).
#
# `mobil` = PageSpeed mobil kosumunda tarayicinin FIILEN SECTIGI varyant. DPR 1 ile
# turer (335 CSS px -> merdivenin >=335 olan EN KUCUK basamagi), DPR 2 ile DEGIL:
# bu dogrulandi, secilen kumenin WebP toplami 205.822 B = 201,0 KiB ve e907eac7
# commit'inin olctugu "201,0 KiB" ile BIREBIR tutuyor. DPR 2 varsayimi 216,0 KiB
# verir, yani 15 KiB'lik SESSIZ bir sapma olurdu.
#
# `avif` = bu banner AVIF'e geciyor mu. OLCUM KARARI (9 Agu, asagidaki tabloyla):
# skan-baykus-b5 HARIC hepsi geciyor. Skan'in orijinali zaten kucuk (60 KB) ve AVIF
# kazanci yok: 448'de %0,0 · 672'de %2,1 · 896'da -%5,8 (AVIF DAHA BUYUK). Kazandirmayan
# bir formati eklemek 3 CDN nesnesi + bir <source> kolu maliyetiyle sifir fayda alirdi;
# 896 basamaginda ise olculmus bir GERILEME yayinlanmis olurdu.
BANNERLAR = [
    ("jenerator-banner-cx1", "urunler/jenerator-banner-cx1.jpg",
     "banner/jenerator-banner-cx1-v2", [560, 840, 1120], 560, True),
    ("skan-baykus-b5", "banner/skan-baykus-b5.jpg",
     "banner/skan-baykus-b5-v2", [448, 672, 896], 448, False),
    ("marin-slide-1", "banner/marin-slide-1.jpg",
     "banner/marin-slide-1-v2", [688, 1100, 1376], 688, True),
    ("marin-slide-2", "banner/marin-slide-2.jpg",
     "banner/marin-slide-2-v2", [688, 1100, 1376], 688, True),
    ("marin-slide-3", "banner/marin-slide-3.jpg",
     "banner/marin-slide-3-v2", [688, 1100, 1376], 688, True),
    ("marin-ozel-uretim-b1", "banner/marin-ozel-uretim-b1.jpg",
     "banner/marin-ozel-uretim-b1-v2", [688, 1100, 1376], 688, True),
]


def indir(anahtar, hedef):
    """R2'den GET (salt okuma). Zaten inmisse yeniden indirmez."""
    if os.path.exists(hedef) and os.path.getsize(hedef) > 0:
        return os.path.getsize(hedef)
    istek = urllib.request.Request(BASE + anahtar, headers={"User-Agent": UA})
    with urllib.request.urlopen(istek, timeout=90) as cevap:
        govde = cevap.read()
    with open(hedef, "wb") as f:
        f.write(govde)
    return len(govde)


def kos(argv):
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("KOMUT DUSTU rc=%d: %s\n%s\n%s"
                           % (r.returncode, " ".join(argv),
                              r.stdout[-800:], r.stderr[-800:]))
    return r


def r2_upload_modulu():
    """tools/r2-upload.py'yi ic modul olarak yukle (R1 kabulunu OLCMEK icin)."""
    yol = os.path.join(TOOLS, "r2-upload.py")
    spec = importlib.util.spec_from_file_location("r2_upload_mod", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(prog="banner-varyant-uret.py")
    ap.add_argument("--cikti", default=None,
                    help="cikti dizini (varsayilan: gecici dizin). Repoya YAZILMAZ.")
    a = ap.parse_args()

    for arac in (SIPS, AVIFENC):
        if not os.path.exists(arac):
            print("OLCULEMEDI: %s yok — AVIF kodlayici kurulu degil "
                  "(brew install libavif)" % arac)
            return 2

    kok = a.cikti or tempfile.mkdtemp(prefix="pruvo-banner-avif-")
    ham_d = os.path.join(kok, "ham")
    webp_d = os.path.join(kok, "webp")
    cik_d = os.path.join(kok, "cikti")
    for d in (kok, ham_d, webp_d, cik_d):
        os.makedirs(d, exist_ok=True)

    satirlar = []
    mobil_webp = mobil_avif = toplam_webp = toplam_avif = 0
    # SERVIS EDILECEK mobil kume: AVIF'e gecmeyen banner mobilde WebP olarak KALIR,
    # yani kazanc hesabina onun WebP bayti girer. Aksi halde yayinlanmayan bir
    # iyilesme raporlanmis olurdu ([[hukum-yanlis-birimde]]).
    mobil_servis = 0
    uretilen = []

    for ad, kaynak, taban, genislikler, mobil_w, avif_acik in BANNERLAR:
        ham = os.path.join(ham_d, ad + ".jpg")
        print("kaynak: %-46s %8d B%s"
              % (kaynak, indir(kaynak, ham), "" if avif_acik else "   [AVIF KAPALI]"))
        for w in genislikler:
            png = os.path.join(cik_d, "%s-%d.png" % (ad, w))
            avif = os.path.join(cik_d, "%s-v2-%d.avif" % (ad, w))
            kos([SIPS, "--resampleWidth", str(w), ham,
                 "-s", "format", "png", "--out", png])
            kos([AVIFENC, "-q", KALITE, "-s", HIZ, "--jobs", "all", png, avif])
            os.unlink(png)
            a_boyut = os.path.getsize(avif)
            w_boyut = indir("%s-%d.webp" % (taban, w),
                            os.path.join(webp_d, "%s-v2-%d.webp" % (ad, w)))
            toplam_avif += a_boyut
            toplam_webp += w_boyut
            if w == mobil_w:
                mobil_avif += a_boyut
                mobil_webp += w_boyut
                mobil_servis += a_boyut if avif_acik else w_boyut
            satirlar.append(("%s-v2-%d" % (ad, w), w_boyut, a_boyut,
                             ("MOBIL" if w == mobil_w else "")
                             + ("" if avif_acik else " kapali")))
            if avif_acik:
                uretilen.append((avif, "%s-%d.avif" % (taban, w)))

    print("")
    print("%-34s %11s %11s %8s %13s"
          % ("varyant", "WebP q80", "AVIF q65", "kazanc", ""))
    print("-" * 80)
    for ad, wb, av, isaret in satirlar:
        print("%-34s %9d B %9d B %7.1f%% %13s"
              % (ad, wb, av, 100.0 * (wb - av) / wb if wb else 0.0, isaret))
    print("-" * 80)
    print("TUM MERDIVEN (%2d)     WebP %8.1f KiB -> AVIF %8.1f KiB  (%+.1f%%)"
          % (len(satirlar), toplam_webp / 1024.0, toplam_avif / 1024.0,
             -100.0 * (toplam_webp - toplam_avif) / toplam_webp))
    print("MOBIL kume, ham (%d)   WebP %8.1f KiB -> AVIF %8.1f KiB  (%+.1f%%)"
          % (len(BANNERLAR), mobil_webp / 1024.0, mobil_avif / 1024.0,
             -100.0 * (mobil_webp - mobil_avif) / mobil_webp))
    print("🔴 MOBIL, GERCEKTEN SERVIS EDILECEK   %8.1f KiB -> %8.1f KiB  (%+.1f%%)"
          % (mobil_webp / 1024.0, mobil_servis / 1024.0,
             -100.0 * (mobil_webp - mobil_servis) / mobil_webp))

    # 🔴 UCTAN UCA KANIT: R1 whitelist'i GERCEK AVIF govdesini taniyor mu (fikstur degil).
    mod = r2_upload_modulu()
    kabul = 0
    for yerel, anahtar in uretilen:
        fmt = mod.format_belirle(open(yerel, "rb").read())
        if fmt == "avif":
            kabul += 1
        else:
            print("🔴 R1 KABUL ETMEDI: %s -> format_belirle=%r" % (anahtar, fmt))
    marka = open(uretilen[0][0], "rb").read()[8:12].decode("latin-1")
    print("R1 KAPISI: %d/%d GERCEK AVIF govdesi 'avif' tanindi (olculen marka: %r)"
          % (kabul, len(uretilen), marka))

    ciftler = os.path.join(kok, "yukleme-ciftleri.txt")
    with open(ciftler, "w", encoding="utf-8") as f:
        for yerel, anahtar in uretilen:
            f.write(yerel + " " + anahtar + "\n")
    print("Yukleme ciftleri: %s (%d cift)" % (ciftler, len(uretilen)))
    print("R2'YE TEK BAYT YAZILMADI — yukleme ayri adim (tools/r2-upload.py).")
    return 0 if kabul == len(uretilen) else 1


if __name__ == "__main__":
    sys.exit(main())

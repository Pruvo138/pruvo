#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LCP ONCULUK KAPISI — ana sayfanin duyarli banner gorsel yaminin IKIZ TANIMINI olcer.

NEDEN VAR (olculdu, 8 Agu 2026 PageSpeed mobil): skor 74'un TEK kayip kalemi LCP 10,7 sn'ydi
ve LCP ogesi marin slider'in 1. slaytiydi. Onarim uc parcali: (a) gorseller duyarli
WebP/JPEG varyantlarina bolundu, (b) LCP gorseli <head>'den `rel=preload` ile ONCEDEN
kesfediliyor, (c) gorsel alan adina `preconnect` var.

🔴 BU ONARIM BIR IKIZ TANIM URETTI ve bu depoda ikiz tanim SESSIZCE AYRISIR
([[ikiz-tanim-sessiz-ayrisma]]): <head>'deki `imagesrcset`/`imagesizes` ile gövdedeki LCP
<picture>'in <source srcset>/<source sizes> degeri BIREBIR ayni olmak ZORUNDA. Bir karakter
ayrisirsa tarayici preload'u eslestiremez; hata TAMAMEN SESSIZDIR:
  · sayfa DOGRU gorunur, hicbir test kirmizi yanmaz,
  · ama LCP gorseli IKI KEZ iner -> onarimin tamami geri sarilir ve bayt iki katina cikar.
Ayni sinif `srcset` genislik tanimlayicisinda da var: `-v2-688.webp` dosyasi `1100w` diye
beyan edilirse tarayici YANLIS varyanti secer (ya bulanik ya gereksiz agir) ve yine hicbir
kirmizi yanmaz.

BU KAPI YAYINI BLOKLAMAZ (nobet.yml::serit-b). Gerekce: olctugu sinif bir PERFORMANS
gerilemesidir (cift indirme / yanlis varyant), dogruluk hatasi DEGIL — sayfa her halukarda
dogru gorunur. Ilgisiz bir kapinin tum ekibin yayinini durdurmasi bu depoda saatlik canli
bayatlik pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).

FAIL-CLOSED: index.html okunamazsa ya da hic <picture> bulunamazsa "sapma yok" HUKMU
VERILMEZ; kapi kirmizi yanar. "Olculdu" diyen hukum pozitif tanima izinden turemeli
([[olculdu-diyen-hukum-kaniti]]).

IKI KOL, TEK KOMUT (bayrak YOK — bayrak eklemek ci-kapsam-test.py'ye ayri bir alt-kume
kapsam borcu yazar):
  A) GERCEK TARAMA  — depodaki index.html uzerinde 7 eksen.
  B) MUTASYON BATARYASI — ayni metnin bellekte bozulmus 8 kopyasi; her biri KIRMIZI
     yakmali. Ayrica bir KONTROL mutanti (zararsiz degisiklik) YESIL kalmali, yoksa
     batarya "her sey kirmizi" diye kendini kandirir ([[fikstur-degeri-mutasyon-koru]]).
     Mutantlar sabit literallere DEGIL, metinden REGEX ile bulunan gercek parcalara
     capalidir; boylece mesru bir refaktor kapiyi kirmaz ([[kapi-anchor-coupling-ikilemi]]).

Kullanim:
    python3 tools/lcp-onculuk-kapisi.py
Cikis: 0 = YESIL · 1 = SAPMA/MUTANT KACTI · 2 = OLCULEMEDI (fail-closed)
"""
import io
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(KOK, "index.html")

KOD_KIRMIZI = 1
KOD_OLCULEMEDI = 2

# Gorsel alan adi index.html'den TURETILIR (buraya ikinci bir liste YAZILMAZ).
_HOST_RE = re.compile(r"https://([a-z0-9.-]+)/(?:banner|urunler)/")
_PICTURE_AC = re.compile(r"<picture\b")
_PICTURE_KAPA = re.compile(r"</picture>")
_SOURCE_RE = re.compile(
    r'<source\b[^>]*type="image/webp"[^>]*?sizes="([^"]*)"[^>]*?srcset="([^"]*)"[^>]*>',
    re.S)
_IMG_RE = re.compile(r"<img\b[^>]*>", re.S)
_PRELOAD_RE = re.compile(r'<link\b[^>]*\brel="preload"[^>]*>', re.S)
_PRECONNECT_RE = re.compile(r'<link\b[^>]*\brel="preconnect"[^>]*\bhref="https://([^"/]+)"',
                            re.S)
_SRCSET_OGE = re.compile(r"(\S+)\s+(\d+)w")


def oznitelik(etiket, ad):
    m = re.search(r'\b%s="([^"]*)"' % re.escape(ad), etiket)
    return m.group(1) if m else None


def yorumsuz(metin):
    """Yorumlar IDDIA DEGILDIR: HTML yorumu + CSS/JS blok yorumu soyulur. Nobetcinin
    kendi aciklamasi olcume karismasin ([[nobetci-kendi-dosyasinda-sizinti]])."""
    metin = re.sub(r"<!--.*?-->", "", metin, flags=re.S)
    return re.sub(r"/\*.*?\*/", "", metin, flags=re.S)


def tara(ham):
    """index.html metnini olcer; (hatalar, sayimlar) dondurur. Bos/ayristirilamaz
    girdide 'sapma yok' DEMEZ — OLCULEMEDI hatasi uretir."""
    hata = []
    sayim = {}
    g = yorumsuz(ham)

    # --- A1 picture iskeleti (fail-closed taban) -----------------------------------
    ac = len(_PICTURE_AC.findall(g))
    kapa = len(_PICTURE_KAPA.findall(g))
    sayim["picture"] = ac
    if ac == 0:
        return (["OLCULEMEDI: index.html'de hic <picture> yok — duyarli gorsel yami "
                 "kaybolmus ya da secici bayatlamis; 'sapma yok' hukmu VERILEMEZ."], sayim)
    if ac != kapa:
        hata.append("A1: <picture> %d acilis / %d kapanis — iskelet bozuk" % (ac, kapa))

    imgler = _IMG_RE.findall(g)
    kaynaklar = _SOURCE_RE.findall(g)          # [(sizes, srcset), ...]
    sayim["webp_source"] = len(kaynaklar)
    sayim["img"] = len(imgler)
    if len(kaynaklar) != ac:
        hata.append("A5: %d <picture> var ama %d WebP <source> — her picture'da modern "
                    "format kolu OLMALI" % (ac, len(kaynaklar)))

    # --- A2 LCP isareti: fetchpriority=high TEK bir <img>'de ------------------------
    yuksek = [t for t in imgler if oznitelik(t, "fetchpriority") == "high"]
    sayim["fetchpriority_high"] = len(yuksek)
    if len(yuksek) != 1:
        hata.append("A2: fetchpriority=\"high\" tasiyan <img> sayisi %d (tam 1 olmali — "
                    "sifir ise LCP oncelenmiyor, birden fazlaysa oncelik anlamsizlasiyor)"
                    % len(yuksek))

    # --- A3 preload var mi -----------------------------------------------------------
    on_yuklemeler = [t for t in _PRELOAD_RE.findall(g)
                     if oznitelik(t, "as") == "image" and oznitelik(t, "imagesrcset")]
    sayim["preload_image"] = len(on_yuklemeler)
    if len(on_yuklemeler) != 1:
        hata.append("A3: as=\"image\" + imagesrcset tasiyan <link rel=preload> sayisi %d "
                    "(tam 1 olmali)" % len(on_yuklemeler))

    # --- A4 IKIZ TANIM: preload <-> LCP <source> BIREBIR mi --------------------------
    if len(on_yuklemeler) == 1 and len(yuksek) == 1:
        p_srcset = on_yuklemeler[0]
        pre_set = oznitelik(p_srcset, "imagesrcset") or ""
        pre_siz = oznitelik(p_srcset, "imagesizes") or ""
        # LCP gorselinin adini <img src>'den turet, ONA ait <source>'u ONDAN bul.
        lcp_src = oznitelik(yuksek[0], "src") or ""
        kok_ad = re.sub(r"-v2-\d+\.[a-z0-9]+$", "", lcp_src.rsplit("/", 1)[-1])
        eslesen = [(s, ss) for (s, ss) in kaynaklar if kok_ad and kok_ad in ss]
        sayim["lcp_kok"] = kok_ad or "(bulunamadi)"
        if len(eslesen) != 1:
            hata.append("A4: LCP <img src>'inden turetilen kok %r ile eslesen WebP "
                        "<source> sayisi %d (tam 1 olmali) — preload karsilastirmasi "
                        "YAPILAMADI" % (kok_ad, len(eslesen)))
        else:
            s_siz, s_set = eslesen[0]
            if pre_set != s_set:
                hata.append("A4: IKIZ AYRISMASI — <head> imagesrcset ile LCP <source> "
                            "srcset FARKLI. Tarayici preload'u eslestiremez ve LCP "
                            "gorselini IKI KEZ indirir.\n"
                            "     head : %s\n     govde: %s" % (pre_set, s_set))
            if pre_siz != s_siz:
                hata.append("A4: IKIZ AYRISMASI — <head> imagesizes ile LCP <source> "
                            "sizes FARKLI.\n     head : %s\n     govde: %s"
                            % (pre_siz, s_siz))

    # --- A5 her picture'da modern-olmayan yedek <img src> ----------------------------
    webp_yedek = [t for t in imgler
                  if (oznitelik(t, "src") or "").endswith(".webp")]
    sayim["webp_yedek"] = len(webp_yedek)
    if webp_yedek:
        hata.append("A5: %d <img> yedegi .webp — <picture> yedek kolu WebP DESTEKLEMEYEN "
                    "tarayici icindir, WebP olamaz" % len(webp_yedek))

    # --- A6 preconnect: gorsel alan adlarinin HEPSI isitilmis mi ---------------------
    gorsel_hostlar = set(_HOST_RE.findall(g))
    isitilan = set(_PRECONNECT_RE.findall(g))
    sayim["gorsel_host"] = len(gorsel_hostlar)
    eksik = sorted(gorsel_hostlar - isitilan)
    if eksik:
        hata.append("A6: preconnect EKSIK -> %s (DNS+TLS el sikismasi gövdeye inince "
                    "baslar; LCP'ye ~300 ms ekler)" % ", ".join(eksik))

    # --- A7 srcset genislik tanimlayicisi dosya adiyla tutarli mi --------------------
    tutarsiz = []
    oge_sayisi = 0
    for _s, ss in kaynaklar:
        for url, w in _SRCSET_OGE.findall(ss):
            oge_sayisi += 1
            m = re.search(r"-v2-(\d+)\.[a-z0-9]+$", url)
            if m and m.group(1) != w:
                tutarsiz.append("%s -> %sw" % (url.rsplit("/", 1)[-1], w))
    sayim["srcset_oge"] = oge_sayisi
    if oge_sayisi == 0:
        hata.append("OLCULEMEDI: hicbir srcset ogesi ayristirilamadi (genislik "
                    "tanimlayicisi yok?) — A7 hukmu VERILEMEZ")
    if tutarsiz:
        hata.append("A7: srcset genisligi dosya adiyla CELISIYOR -> %s (tarayici YANLIS "
                    "varyanti secer; hata sessizdir)" % ", ".join(tutarsiz))

    return hata, sayim


# ----------------------------------------------------------------- MUTASYON BATARYASI
def _ilk_source(metin):
    m = _SOURCE_RE.search(yorumsuz(metin))
    return m.group(0) if m else None


def mutantlar(ham):
    """(ad, bozulmus_metin, beklenen) listesi. beklenen=True -> KIRMIZI yanmali.
    Her parca metinden REGEX ile BULUNUR (sabit literal capa YOK)."""
    liste = []
    g = yorumsuz(ham)

    pre = None
    for t in _PRELOAD_RE.findall(g):
        if oznitelik(t, "as") == "image" and oznitelik(t, "imagesrcset"):
            pre = t
            break
    yuksek = None
    for t in _IMG_RE.findall(g):
        if oznitelik(t, "fetchpriority") == "high":
            yuksek = t
            break
    prec = re.search(r'<link\b[^>]*\brel="preconnect"[^>]*>', g)

    if pre:
        liste.append(("M1 preload SILINDI", ham.replace(pre, "", 1), True))
        set_ = oznitelik(pre, "imagesrcset")
        liste.append(("M2 imagesrcset genisligi kaydi (688w -> 689w)",
                      ham.replace(pre, pre.replace(set_, set_.replace("688w", "689w"), 1), 1),
                      True))
        siz = oznitelik(pre, "imagesizes")
        liste.append(("M3 imagesizes ayristi",
                      ham.replace(pre, pre.replace(siz, siz.replace("1060px", "1024px"), 1), 1),
                      True))
    if yuksek:
        liste.append(("M4 fetchpriority=high KALDIRILDI",
                      ham.replace(yuksek, yuksek.replace(' fetchpriority="high"', "", 1), 1),
                      True))
        liste.append(("M5 fetchpriority=high IKINCI bir img'e verildi",
                      ham.replace('fetchpriority="low"', 'fetchpriority="high"', 1), True))
        liste.append(("M8 yedek <img src> WebP'ye cevrildi (yedek kolu yok)",
                      ham.replace(yuksek,
                                  re.sub(r'src="([^"]+)\.jpg"', r'src="\1.webp"', yuksek), 1),
                      True))
    if prec:
        liste.append(("M6 preconnect SILINDI", ham.replace(prec.group(0), "", 1), True))
    # M7: capa SABIT genislik degil — metinden bulunan ILK (url, genislik) ciftidir;
    # genislik dosya adindan farkli bir sayiya kaydirilir. Boylece varyant merdiveni
    # degistiginde capa bayatlamaz ([[kapi-anchor-coupling-ikilemi]]).
    for _s, ss in _SOURCE_RE.findall(g):
        ogeler = _SRCSET_OGE.findall(ss)
        if not ogeler:
            continue
        url, w = ogeler[0]
        eski = "%s %sw" % (url, w)
        yeni_ss = ss.replace(eski, "%s %dw" % (url, int(w) + 7), 1)
        if yeni_ss != ss and ss in ham:
            liste.append(("M7 srcset tanimlayicisi dosya adiyla celisiyor",
                          ham.replace(ss, yeni_ss, 1), True))
            break
    # KONTROL: olcum yuzeyine DOKUNMAYAN degisiklik YESIL kalmali.
    liste.append(("K1 KONTROL — alakasiz metin degisti (YESIL kalmali)",
                  ham.replace("Keşfet", "Kesfet"), False))
    return liste


def main():
    if not os.path.isfile(INDEX):
        print("OLCULEMEDI: %s yok" % INDEX)
        return KOD_OLCULEMEDI
    ham = io.open(INDEX, encoding="utf-8").read()

    print("=" * 74)
    print("LCP ONCULUK KAPISI — %s" % os.path.relpath(INDEX, KOK))
    print("=" * 74)

    hata, sayim = tara(ham)
    olculemedi = [h for h in hata if h.startswith("OLCULEMEDI")]
    print("A) GERCEK TARAMA")
    for k in ("picture", "webp_source", "img", "fetchpriority_high", "preload_image",
              "gorsel_host", "srcset_oge", "lcp_kok"):
        if k in sayim:
            print("   %-20s %s" % (k, sayim[k]))
    if hata:
        for h in hata:
            print("   KIRMIZI %s" % h)
    else:
        print("   YESIL — 7 eksenin hepsi gecti (ikiz tanim BIREBIR)")

    print("B) MUTASYON BATARYASI")
    mut = mutantlar(ham)
    if len(mut) < 9:
        print("   OLCULEMEDI: yalniz %d mutant uretilebildi (>=9 beklenir) — capalar "
              "bayatlamis" % len(mut))
        return KOD_OLCULEMEDI
    kacan = []
    for ad, bozuk, kirmizi_bekleniyor in mut:
        if bozuk == ham:
            kacan.append("%s (MUTASYON UYGULANMADI — capa tutmadi)" % ad)
            continue
        m_hata, _ = tara(bozuk)
        yakalandi = bool(m_hata)
        beklenen = "KIRMIZI" if kirmizi_bekleniyor else "YESIL"
        olculen = "KIRMIZI" if yakalandi else "YESIL"
        if yakalandi != kirmizi_bekleniyor:
            kacan.append("%s (beklenen=%s, olculen=%s)" % (ad, beklenen, olculen))
        print("   %-56s beklenen=%-7s olculen=%-7s %s"
              % (ad, beklenen, olculen, "ok" if yakalandi == kirmizi_bekleniyor else "SAPTI"))
    print("   mutant: %d · kacan: %d" % (len(mut), len(kacan)))
    for k in kacan:
        print("   KIRMIZI %s" % k)

    print("-" * 74)
    if olculemedi:
        print("SONUC: OLCULEMEDI 🟠 — taban bulunamadi, temiz hukum VERILMEDI")
        return KOD_OLCULEMEDI
    if hata or kacan:
        print("SONUC: KIRMIZI ❌ — %d sapma + %d kacan mutant" % (len(hata), len(kacan)))
        return KOD_KIRMIZI
    print("SONUC: YESIL ✅ — %d picture · %d srcset ogesi · ikiz tanim birebir · "
          "%d mutantin hepsi yakalandi" % (sayim["picture"], sayim["srcset_oge"], len(mut) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

🔴 9 AGU 2026 — AVIF KOLU ve IKI YENI SESSIZ EKSEN. Banner'lar AVIF <source> ile
zenginlestirildi (mobil kume 201,0 -> 170,9 KiB, olculdu). Bu iki yeni sessiz arizayi
dogurdu, ikisi de "sayfa dogru gorunur ama kazanc SIFIR" sinifindan:
  A8 SIRA — tarayici <picture> icinde ILK destekledigi <source>'u secer. AVIF WebP'den
     SONRA yazilirsa AVIF'i destekleyen tarayici bile WebP'yi alir: dosyalar CDN'e
     yuklenmis, kol yazilmis, kimse kirmizi gormez, kazanc yoktur.
  A9 PRELOAD TIPI — <head> WebP on-yuklerken govde AVIF seciyorsa ON-YUKLENEN ile
     INDIRILEN farkli olur: gorsel IKI KEZ iner, yani onarim TERSINE doner.
Bu tur ayrica ayristiriciyi FORMAT-AGNOSTIK yapti: eski hali `type="image/webp"`
literaline capaliydi ve AVIF <source>'larini HIC gormuyordu.

BU KAPI YAYINI BLOKLAMAZ (nobet.yml::serit-b). Gerekce: olctugu sinif bir PERFORMANS
gerilemesidir (cift indirme / yanlis varyant), dogruluk hatasi DEGIL — sayfa her halukarda
dogru gorunur. Ilgisiz bir kapinin tum ekibin yayinini durdurmasi bu depoda saatlik canli
bayatlik pencereleri acti ([[kapi-birikimi-yayin-gecikmesi]]).

FAIL-CLOSED: index.html okunamazsa ya da hic <picture> bulunamazsa "sapma yok" HUKMU
VERILMEZ; kapi kirmizi yanar. "Olculdu" diyen hukum pozitif tanima izinden turemeli
([[olculdu-diyen-hukum-kaniti]]).

IKI KOL, TEK KOMUT (bayrak YOK — bayrak eklemek ci-kapsam-test.py'ye ayri bir alt-kume
kapsam borcu yazar):
  A) GERCEK TARAMA  — depodaki index.html uzerinde 9 eksen (A1-A9).
  B) MUTASYON BATARYASI — ayni metnin bellekte bozulmus 10 kopyasi; her biri KIRMIZI
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
_PICTURE_BLOK = re.compile(r"<picture\b.*?</picture>", re.S)
# 🔴 SOURCE AYRISTIRICISI FORMAT-AGNOSTIK (9 Agu 2026). Onceki hali `type="image/webp"`
# LITERALINE capaliydi; whitelist AVIF'e acilinca o capa iki sekilde yalan soylerdi:
# (a) AVIF <source>'lari HIC gormezdi -> A7 genislik tutarliligi ve A5 sayimi AVIF kolunu
#     olcmeden yesil yanardi, (b) A4 ikiz karsilastirmasini DAIMA WebP'ye yaptigi icin
# head AVIF'e cevrildiginde "ayrisma" diye YANLIS kirmizi verirdi. Tip artik oznitelikten
# OKUNUR ve iddia tipe GORE secilir ([[ikiz-tanim-sessiz-ayrisma]]).
_SOURCE_TAG = re.compile(r"<source\b[^>]*>", re.S)
# <picture> icinde tarayici ILK DESTEKLEDIGI <source>'u secer -> sira ANLAMLIDIR.
# Tercih sirasi (kucuk indis = once gelmeli): AVIF, sonra WebP.
MODERN_TIPLER = ("image/avif", "image/webp")
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


def _blok_kaynaklari(g):
    """Her <picture> blogu icin SIRALI kaynak listesi:
    [[(tip, sizes, srcset, ham_etiket), ...], ...]. Sira KORUNUR — A8 ona bakar."""
    return [[(oznitelik(t, "type") or "", oznitelik(t, "sizes") or "",
              oznitelik(t, "srcset") or "", t)
             for t in _SOURCE_TAG.findall(blok)]
            for blok in _PICTURE_BLOK.findall(g)]


def _tum_kaynaklar(g):
    """Duzlestirilmis hali. tara() ve mutantlar() AYNI ayristiriciyi kullanir; ikinci
    bir ayristirici yazmak kabul araligi ile kiyas araligini ayristirirdi
    ([[kabul-araligi-karsilastirma-araligi]])."""
    return [k for liste in _blok_kaynaklari(g) for k in liste]


def eager_gorsel_adaylari(imgler, bloklar):
    """Sayfanin GORSEL LCP adaylari — TEK TANIM (A kolu da B kolu da bunu cagirir;
    ikinci bir tanim yazmak bu depoda sessizce ayrisan ikiz uretir).

    Aday sayilmanin IKI yolu var:
      (1) <img fetchpriority="high"> — YAZAR "LCP'm budur" diye BEYAN etmistir;
          `loading="lazy"` ile birlikte yazilmis olsa bile aday sayilir. Lazy,
          gorus alanindaki bir gorseli agdan CIKARMAZ ve celiskili isaretlemede
          fail-closed davranmak dogrudur
          ([[lazy-fetchpriority-gorus-alanindaki-gizli-gorseli-agdan-cikarmaz]]).
      (2) bir <picture> blogunun ICINDEKI, `loading="lazy"` OLMAYAN <img> — duyarli
          banner yaminin eager kolu.
    Bunlarin disi (rozet/ikon gibi picture'siz kucuk <img>'ler ve lazy banner'lar)
    on-yukleme eksenlerinin menzilinde DEGILDIR.
    """
    picture_govdesi = "".join(bloklar)
    adaylar = []
    for t in imgler:
        lazy = (oznitelik(t, "loading") or "").lower() == "lazy"
        if oznitelik(t, "fetchpriority") == "high":
            adaylar.append(t)
        elif t in picture_govdesi and not lazy:
            adaylar.append(t)
    return adaylar


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
    bloklar = _PICTURE_BLOK.findall(g)
    if len(bloklar) != ac:
        hata.append("A1: %d <picture> acilisi var ama %d tam blok ayristirilabildi — "
                    "ic ice/kapanmamis etiket" % (ac, len(bloklar)))
    blok_kaynaklari = _blok_kaynaklari(g)
    kaynaklar = [k for liste in blok_kaynaklari for k in liste]
    sayim["avif_source"] = sum(1 for k in kaynaklar if k[0] == "image/avif")
    sayim["webp_source"] = sum(1 for k in kaynaklar if k[0] == "image/webp")
    sayim["img"] = len(imgler)

    # --- A5 her <picture>'da WebP kolu ZORUNLU ----------------------------------------
    # 🔴 BURADA IDDIA GEVSETILMEDI. AVIF eklenirken "en az bir modern kol olsun" demek
    # KOLAY ve YANLIS olurdu: AVIF-ONLY bir <picture> bu gevsek iddiadan gecer, ama AVIF
    # desteklemeyen (WebP destekleyen) tarayici DOGRUDAN tam boy JPEG'e duser — yani
    # AVIF eklemek, eski tarayicilar icin bir GERILEME olurdu ve kapi bunu gormezdi.
    # WebP taban koldur: her <picture>'da BULUNMAK ZORUNDA. AVIF ONUN USTUNE eklenir.
    webp_sayisi = sayim["webp_source"]
    if webp_sayisi != ac:
        hata.append("A5: %d <picture> var ama %d WebP <source> — WebP TABAN koldur, her "
                    "picture'da bulunmak ZORUNDA (AVIF onun yerine gecmez: AVIF'i "
                    "desteklemeyen tarayici dogrudan tam boy JPEG'e duser)"
                    % (ac, webp_sayisi))

    # --- A8 SIRA EKSENI (9 Agu): AVIF, WebP'den ONCE gelmeli --------------------------
    # Tarayici ILK destekledigi <source>'u secer. AVIF WebP'den SONRA yazilirsa AVIF'i
    # destekleyen tarayici bile WebP'yi secer: dosyalar yuklenmis, kol yazilmis, kimse
    # kirmizi gormez ve kazanc SIFIRDIR. Tam bu deponun "sessiz" sinifi.
    ters = 0
    for liste in blok_kaynaklari:
        tipler = [k[0] for k in liste]
        if "image/avif" in tipler and "image/webp" in tipler:
            if tipler.index("image/avif") > tipler.index("image/webp"):
                ters += 1
    if ters:
        hata.append("A8: %d <picture>'da AVIF <source> WebP'den SONRA geliyor — tarayici "
                    "ILK destekledigi kolu secer, yani AVIF ASLA servis edilmez "
                    "(dosyalar bosuna yuklenmis olur, hata sessizdir)" % ters)

    # --- MENZIL TURETIMI (9 Eyl 2026, K392): SAYFANIN GORSEL LCP ADAYI VAR MI? -------
    # 🔴 SINIF: A2/A3/A4/A9 "ekranin ustunde on-yuklenecek BIR GORSEL VAR" oncululune
    # dayanir. 5 Eyl'de o oncul KOKTEN cürüdü: `63a48f7a` foto-slider'i SOKTU ve vitrini
    # metne cevirdi (Okan onayli tasarim). Commit govdesi ve index.html <head> yorumu
    # ayni seyi yaziyor: "on-yuklenecek LCP gorseli YOK; olu preload LCP'yi duzeltmez,
    # BOZAR". Kapi bunu goremedigi icin 4 gun boyunca DOGRU davranisi kirmiziya yakti
    # ([[kaldirilan-ozelligi-olcen-kapi]] sinifi — K366'nin kardesi).
    #
    # Menzil BEYANDAN DEGIL, METINDEN turer: "eager gorsel adayi" =
    #   (a) bir <picture> blogunun ICINDEKI <img>, ya da (b) fetchpriority="high" tasiyan
    #   HERHANGI bir <img> — ve `loading="lazy"` OLMAYAN.
    # Aday 0 ise on-yukleme eksenleri KAPSAM DISI'dir (YESIL degil, YOK). Aday >=1 olur
    # olmaz eski iddia AYNEN geri gelir: tam 1 fetchpriority=high + tam 1 preload.
    # Yani banner geri gelirse kapi yeniden kirmizi yanar; gevseme YOK, menzil DARALDI
    # ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
    adaylar = eager_gorsel_adaylari(imgler, bloklar)
    sayim["eager_gorsel_adayi"] = len(adaylar)
    gorsel_lcp_menzilde = len(adaylar) > 0

    # --- A2 LCP isareti: fetchpriority=high TEK bir <img>'de ------------------------
    yuksek = [t for t in imgler if oznitelik(t, "fetchpriority") == "high"]
    sayim["fetchpriority_high"] = len(yuksek)
    if gorsel_lcp_menzilde and len(yuksek) != 1:
        hata.append("A2: fetchpriority=\"high\" tasiyan <img> sayisi %d (tam 1 olmali — "
                    "sifir ise LCP oncelenmiyor, birden fazlaysa oncelik anlamsizlasiyor)"
                    % len(yuksek))

    # --- A3 preload var mi -----------------------------------------------------------
    on_yuklemeler = [t for t in _PRELOAD_RE.findall(g)
                     if oznitelik(t, "as") == "image" and oznitelik(t, "imagesrcset")]
    sayim["preload_image"] = len(on_yuklemeler)
    if gorsel_lcp_menzilde and len(on_yuklemeler) != 1:
        hata.append("A3: as=\"image\" + imagesrcset tasiyan <link rel=preload> sayisi %d "
                    "(tam 1 olmali)" % len(on_yuklemeler))
    # A3b — TERS YON (menzil daraltmasinin bedeli): gorsel adayi YOKKEN duran bir
    # preload "olu preload"dur; gercek (metin) LCP'nin onune gecer. Daraltma bu yuzden
    # iki yonludur: aday yoksa preload da OLMAMALI.
    if not gorsel_lcp_menzilde and len(on_yuklemeler) != 0:
        hata.append("A3b: eager gorsel adayi 0 ama %d adet as=\"image\" preload duruyor "
                    "— OLU PRELOAD: hicbir zaman kullanilmayacak bir gorseli yuksek "
                    "oncelikle indirir ve gercek (metin) LCP'yi GECIKTIRIR"
                    % len(on_yuklemeler))

    # --- A4 + A9 IKIZ TANIM: preload <-> LCP <source> BIREBIR mi ----------------------
    if gorsel_lcp_menzilde and len(on_yuklemeler) == 1 and len(yuksek) == 1:
        p_srcset = on_yuklemeler[0]
        pre_set = oznitelik(p_srcset, "imagesrcset") or ""
        pre_siz = oznitelik(p_srcset, "imagesizes") or ""
        pre_tip = oznitelik(p_srcset, "type") or ""
        lcp_src = oznitelik(yuksek[0], "src") or ""
        sayim["lcp_kok"] = re.sub(r"-v2-\d+\.[a-z0-9]+$", "",
                                  lcp_src.rsplit("/", 1)[-1]) or "(bulunamadi)"
        # LCP <picture>'i, fetchpriority=high <img>'i ICEREN bloktur (ad esleme DEGIL:
        # ad heuristigi iki banner ayni koku paylasinca sessizce yanlis blogu secerdi).
        lcp_liste = None
        for i, blok in enumerate(bloklar):
            if yuksek[0] in blok:
                lcp_liste = blok_kaynaklari[i]
                break
        if lcp_liste is None:
            hata.append("A4: fetchpriority=\"high\" <img> hicbir <picture> blogunun "
                        "ICINDE degil — preload karsilastirmasi YAPILAMADI")
        else:
            modern = [k for k in lcp_liste if k[0] in MODERN_TIPLER]
            sayim["lcp_ilk_modern"] = modern[0][0] if modern else "(yok)"
            # A9: preload TIPI, tarayicinin gercekten sececegi kol olmali.
            if not modern:
                hata.append("A9: LCP <picture>'da modern format <source> YOK — preload "
                            "tipi neyle eslesecegi OLCULEMEZ")
            elif pre_tip != modern[0][0]:
                hata.append("A9: PRELOAD TIPI GOVDEYLE UYUSMUYOR — <head> %r on-yukluyor "
                            "ama tarayici govdede ILK olarak %r kolunu secer. Sonuc: bir "
                            "gorsel ON-YUKLENIR, BASKA bir gorsel indirilir -> LCP "
                            "gorseli IKI KEZ iner ve on-yukleme bosa gider."
                            % (pre_tip, modern[0][0]))
            # A4: karsilastirma preload'un KENDI tipindeki <source> ile yapilir.
            eslesen = [k for k in lcp_liste if k[0] == pre_tip]
            if len(eslesen) != 1:
                hata.append("A4: LCP <picture>'da preload tipiyle (%r) eslesen <source> "
                            "sayisi %d (tam 1 olmali) — ikiz karsilastirmasi YAPILAMADI"
                            % (pre_tip, len(eslesen)))
            else:
                _t, s_siz, s_set, _ham = eslesen[0]
                if pre_set != s_set:
                    hata.append("A4: IKIZ AYRISMASI — <head> imagesrcset ile LCP <source> "
                                "srcset FARKLI. Tarayici preload'u eslestiremez ve LCP "
                                "gorselini IKI KEZ indirir.\n"
                                "     head : %s\n     govde: %s" % (pre_set, s_set))
                if pre_siz != s_siz:
                    hata.append("A4: IKIZ AYRISMASI — <head> imagesizes ile LCP <source> "
                                "sizes FARKLI.\n     head : %s\n     govde: %s"
                                % (pre_siz, s_siz))

    # --- A5b yedek <img src> modern format OLAMAZ -------------------------------------
    # <picture> yedek kolu modern formati DESTEKLEMEYEN tarayici icindir; oraya .webp ya
    # da .avif yazmak yedegi anlamsiz kilar (eski tarayici hicbir sey goremez).
    modern_yedek = [t for t in imgler
                    if (oznitelik(t, "src") or "").endswith((".webp", ".avif"))]
    sayim["webp_yedek"] = len(modern_yedek)
    if modern_yedek:
        hata.append("A5b: %d <img> yedegi .webp/.avif — <picture> yedek kolu modern "
                    "formati DESTEKLEMEYEN tarayici icindir" % len(modern_yedek))

    # --- A6 preconnect: gorsel alan adlarinin HEPSI isitilmis mi ---------------------
    gorsel_hostlar = set(_HOST_RE.findall(g))
    isitilan = set(_PRECONNECT_RE.findall(g))
    sayim["gorsel_host"] = len(gorsel_hostlar)
    eksik = sorted(gorsel_hostlar - isitilan)
    if eksik:
        hata.append("A6: preconnect EKSIK -> %s (DNS+TLS el sikismasi gövdeye inince "
                    "baslar; LCP'ye ~300 ms ekler)" % ", ".join(eksik))

    # --- A7 srcset genislik tanimlayicisi dosya adiyla tutarli mi --------------------
    # TUM kaynaklar (AVIF + WebP) taranir: format basina ayri bir merdiven vardir ve
    # yalniz birini olcmek digerinin sessizce kaymasina izin verirdi.
    tutarsiz = []
    oge_sayisi = 0
    for _tip, _s, ss, _ham in kaynaklar:
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
    for _tip, _s, ss, _t in _tum_kaynaklar(g):
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

    # --- 9 Agu: AVIF kolunun IKI YENI EKSENI ------------------------------------------
    # M9 SIRA: AVIF <source> WebP'den SONRAYA alinir. Sayfa DOGRU gorunur, dosyalar
    # yerinde durur, tek degisen sey AVIF'in ASLA secilmemesidir — kazanc sessizce 0'lanir.
    for blok in _PICTURE_BLOK.findall(g):
        etiketler = _SOURCE_TAG.findall(blok)
        avif_t = next((t for t in etiketler
                       if oznitelik(t, "type") == "image/avif"), None)
        webp_t = next((t for t in etiketler
                       if oznitelik(t, "type") == "image/webp"), None)
        if avif_t and webp_t and avif_t in ham and webp_t in ham:
            yer = "\x00PRUVO-SIRA-MUTANTI\x00"
            bozuk = (ham.replace(avif_t, yer, 1)
                        .replace(webp_t, avif_t, 1)
                        .replace(yer, webp_t, 1))
            if bozuk != ham:
                liste.append(("M9 AVIF <source> WebP'den SONRAYA alindi", bozuk, True))
            break
    # M11 TABAN KOL: AVIF'i olan bir <picture>'dan WebP <source> silinir (AVIF-only).
    # Sayfa AVIF destekleyen tarayicida DOGRU gorunur; yalniz AVIF'siz/WebP'li tarayici
    # sessizce tam boy JPEG'e duser. A5'in gevsek ("en az bir modern kol") halinde bu
    # mutant KACARDI — ayirt edici mutant budur.
    for blok in _PICTURE_BLOK.findall(g):
        etiketler = _SOURCE_TAG.findall(blok)
        if not any(oznitelik(t, "type") == "image/avif" for t in etiketler):
            continue
        webp_t = next((t for t in etiketler
                       if oznitelik(t, "type") == "image/webp"), None)
        if webp_t and webp_t in ham:
            liste.append(("M11 AVIF'li <picture>'dan WebP <source> SILINDI (AVIF-only)",
                          ham.replace(webp_t, "", 1), True))
            break
    # M10 TIP: preload tipi WebP'ye cevrilir; govde HALA AVIF'i secer -> on-yuklenen
    # gorsel ile indirilen gorsel FARKLI olur (LCP gorseli iki kez iner).
    if pre and 'type="image/avif"' in pre:
        liste.append(("M10 preload type AVIF -> WebP (govde AVIF secmeye devam eder)",
                      ham.replace(pre, pre.replace('type="image/avif"',
                                                   'type="image/webp"', 1), 1),
                      True))

    # --- N1/N2 (9 Eyl 2026, K392): MENZIL DARALTMASININ DISLERI --------------------
    # Bu iki mutant, gorsel LCP adayi YOKKEN de URETILEBILIR — yani daraltmanin
    # gecerli oldugu halde batarya bos kalmaz. Daraltma bir bypass DEGILSE, bu ikisi
    # OLMEK ZORUNDA ([[mutantli-kosumla-tabanla-ayniysa-mutant-ulasmadi]]).
    #
    # N1: aday yokken preload enjekte edilir -> A3b "olu preload" KIRMIZI yakmali.
    if "</head>" in ham:
        liste.append(("N1 OLU PRELOAD enjekte edilir (gorsel adayi YOKKEN)",
                      ham.replace("</head>",
                                  '<link rel="preload" as="image" '
                                  'imagesrcset="https://media.pruvo3d.com/banner/x-v2-688.webp 688w" '
                                  'imagesizes="100vw" type="image/webp">\n</head>', 1),
                      True))
    # N2: lazy bir <picture> gorseli EAGER yapilir (banner geri gelmis gibi) ->
    # menzil ACILIR ve A2/A3 iddiasi AYNEN geri gelir, preload olmadigi icin KIRMIZI.
    if 'loading="lazy"' in g:
        _hedef = None
        for blok in _PICTURE_BLOK.findall(g):
            for t in _IMG_RE.findall(blok):
                if (oznitelik(t, "loading") or "").lower() == "lazy":
                    _hedef = t
                    break
            if _hedef:
                break
        if _hedef and _hedef in ham:
            liste.append(("N2 lazy <picture> gorseli EAGER yapilir (banner geri gelir)",
                          ham.replace(_hedef,
                                      _hedef.replace(' loading="lazy"', "", 1), 1),
                          True))

    # KONTROL: olcum yuzeyine DOKUNMAYAN degisiklik YESIL kalmali.
    liste.append(("K1 KONTROL — alakasiz metin degisti (YESIL kalmali)",
                  ham.replace("Keşfet", "Kesfet"), False))
    return liste


# --- 7 Eyl 2026: B KOLUNUN SEBEP TURETIMI -----------------------------------------
# NEDEN: `len(mut) < 12` kolu "capalar bayatlamis" diye SABIT bir teshis basiyordu.
# Bu teshis HIC OLCULMUYORDU. 7 Eyl'de canli vaka: `63a48f7a` (foto-slider SOKULDU)
# index.html'den preload+fetchpriority'yi goturdu; 7 mutant o iki eksene capali oldugu
# icin uretilemedi ve kapi "capalar bayatlamis" dedi -> okuyucu KAPI duzlemine (KraL)
# yonlendirildi, oysa arıza ICERIK duzlemindeydi (index.html / ArTisT).
# KURAL: sebep TABLODAN TURETILIR, iddia EDILMEZ ([[aracin-teshis-cumlesi-olcum-degil]]).
#
# Her mutantin bagli oldugu ICERIK ekseni. Eksik mutant, ekseni ham metinde YOK ise
# ICERIK-TUREVI; ekseni VAR oldugu halde uretilememisse CAPA-BAYAT'tir.
MUTANT_ON_KOSUL = {
    "M1": "preload", "M2": "preload", "M3": "preload", "M10": "preload",
    "M4": "fetchpriority", "M5": "fetchpriority", "M8": "fetchpriority",
    "M6": "preconnect",
    "M7": "srcset",
    "M9": "picture-avif", "M11": "picture-avif",
    "N1": "-", "N2": "picture-lazy",
    "K1": "-",
}
# 🔴 UCUNCU KOVA (9 Eyl 2026, K392): "eksen ham metinde YOK" ile "eksen KAPSAM DISI"
# ayni sey DEGIL. Iki kovali siniflama ucuncu sinifi yutuyordu: gorsel LCP adayi
# olmayan bir sayfada preload/fetchpriority eksenleri EKSIK degil, YERINDE YOK —
# A kolu onlari zaten olcmuyor. Bu mutantlari "uretilemedi" sayip OLCULEMEDI basmak
# kapiyi DOGRU davranista kirmiziya yakar ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
# Kapsam disi eksenler esikten DUSER; menzil acilir acilmaz esige geri GIRERLER.
MENZILE_BAGLI_EKSEN = ("preload", "fetchpriority")
# Esik TABLODAN turer; ikinci bir sabit (magic 12) TUTULMAZ — tablo buyuyunce
# esik kendiliginden buyur, iki kaynak birbirinden SAPAMAZ. Bu, MENZIL ACIKKEN
# gecerli TAM esiktir; daraltilmis hali beklenen_mutant_sayisi() dondurur.
BEKLENEN_MUTANT = len(MUTANT_ON_KOSUL)


def beklenen_mutant_sayisi(hal):
    """Esik TABLODAN turer (magic sabit YOK) ve MENZILE gore daralir."""
    if hal.get("gorsel-lcp-adayi", True):
        return BEKLENEN_MUTANT
    return sum(1 for e in MUTANT_ON_KOSUL.values() if e not in MENZILE_BAGLI_EKSEN)


def on_kosul_hali(ham):
    """B kolunun icerik on-kosullarini ham metinden OLCER (iddia etmez)."""
    g = yorumsuz(ham)
    pre = any(oznitelik(t, "as") == "image" and oznitelik(t, "imagesrcset")
              for t in _PRELOAD_RE.findall(g))
    yuksek = any(oznitelik(t, "fetchpriority") == "high" for t in _IMG_RE.findall(g))
    prec = bool(re.search(r'<link\b[^>]*\brel="preconnect"[^>]*>', g))
    srcset = any(_SRCSET_OGE.findall(ss) for _t, _s, ss, _tt in _tum_kaynaklar(g))
    avif = False
    for blok in _PICTURE_BLOK.findall(g):
        etiketler = _SOURCE_TAG.findall(blok)
        if any(oznitelik(t, "type") == "image/avif" for t in etiketler):
            avif = True
            break
    # Menzil ekseni A kolundaki turetimin AYNISIDIR (ikinci bir tanim yazilmaz):
    # eager gorsel adayi = <picture> icindeki ya da fetchpriority=high olan,
    # loading="lazy" OLMAYAN <img>.
    bloklar = _PICTURE_BLOK.findall(g)
    picture_govdesi = "".join(bloklar)
    imgler = _IMG_RE.findall(g)
    lazy_picture = any(t in picture_govdesi
                       and (oznitelik(t, "loading") or "").lower() == "lazy"
                       for t in imgler)
    aday = bool(eager_gorsel_adaylari(imgler, bloklar))
    return {"preload": pre, "fetchpriority": yuksek, "preconnect": prec,
            "srcset": srcset, "picture-avif": avif,
            "picture-lazy": lazy_picture, "gorsel-lcp-adayi": aday, "-": True}


def eksik_mutant_sebebi(ham, mut):
    """(icerik_turevi, capa_bayat) — eksik mutantlari OLCULEN on-kosula gore ayirir."""
    uretilen = set(ad.split(" ", 1)[0] for ad, _b, _k in mut)
    hal = on_kosul_hali(ham)
    icerik, bayat, kapsam_disi = [], [], []
    for kimlik, eksen in sorted(MUTANT_ON_KOSUL.items()):
        if kimlik in uretilen:
            continue
        if eksen in MENZILE_BAGLI_EKSEN and not hal.get("gorsel-lcp-adayi", True):
            kapsam_disi.append((kimlik, eksen))
        elif not hal.get(eksen, True):
            icerik.append((kimlik, eksen))
        else:
            bayat.append((kimlik, eksen))
    return icerik, bayat, kapsam_disi


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
    for k in ("picture", "avif_source", "webp_source", "img", "fetchpriority_high",
              "preload_image", "gorsel_host", "srcset_oge", "lcp_kok",
              "lcp_ilk_modern"):
        if k in sayim:
            print("   %-20s %s" % (k, sayim[k]))
    if hata:
        for h in hata:
            print("   KIRMIZI %s" % h)
    else:
        print("   YESIL — 9 eksenin hepsi gecti (ikiz tanim BIREBIR · AVIF once · "
              "preload tipi govdeyle ayni)")

    print("B) MUTASYON BATARYASI")
    mut = mutantlar(ham)
    # Capa TUTMAYAN mutantlar HER YOLDA olculur. Onceki hal bunu erken return'un
    # ARKASINA birakiyordu: mutant sayisi esigin altina dustugu an, URETILEN
    # mutantlar arasindaki olu capalar da gorunmez oluyordu
    # ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
    tutmayan = [ad for ad, bozuk, _k in mut if bozuk == ham]
    hal = on_kosul_hali(ham)
    beklenen_mutant = beklenen_mutant_sayisi(hal)
    icerik, bayat, kapsam_disi = eksik_mutant_sebebi(ham, mut)
    if kapsam_disi:
        print("   KAPSAM DISI (%d) — sayfada eager gorsel LCP adayi YOK, on-yukleme "
              "eksenleri A kolunda da olculmuyor; bu mutantlar EKSIK degil, YERINDE "
              "YOK. Aday geri gelir gelmez esige de iddiaya da geri girerler:"
              % len(kapsam_disi))
        for kimlik, eksen in kapsam_disi:
            print("        %-4s eksen=%s" % (kimlik, eksen))
    if len(mut) < beklenen_mutant:
        print("   OLCULEMEDI: %d/%d mutant uretilebildi." % (len(mut), beklenen_mutant))
        if icerik:
            print("   SEBEP=ICERIK-TUREVI (%d) — on-kosul ekseni ham metinde YOK; "
                  "A kolundaki eksik icerik duzelince bu mutantlar KENDILIGINDEN doner:"
                  % len(icerik))
            for kimlik, eksen in icerik:
                print("        %-4s eksen=%s" % (kimlik, eksen))
        if bayat:
            print("   SEBEP=CAPA-BAYAT (%d) — on-kosul ekseni ham metinde VAR ama mutant "
                  "yine de uretilemedi; KAPI govdesi onarilmali:" % len(bayat))
            for kimlik, eksen in bayat:
                print("        %-4s eksen=%s" % (kimlik, eksen))
        if tutmayan:
            print("   AYRICA capa TUTMAYAN (uretildi ama metni DEGISTIRMEDI) %d mutant:"
                  % len(tutmayan))
            for ad in tutmayan:
                print("        %s" % ad)
        print("   YONLENDIRME: %s" % ("ICERIK duzlemi (index.html) — kapi govdesi SAGLAM"
                                      if icerik and not bayat and not tutmayan
                                      else "KAPI govdesi (tools/lcp-onculuk-kapisi.py)"))
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

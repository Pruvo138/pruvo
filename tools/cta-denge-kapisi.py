#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CTA DENGE KAPISI — "Sepete Ekle" WhatsApp'i gorsel olarak eziyor mu?

NEDEN VAR (olculdu, 11 Agu 2026)
--------------------------------
Urun sayfasinda birincil eylem SEPETE EKLE'dir; WhatsApp ikincil bir kanaldir. 11 Agu'ya
kadar canlida bunun TAM TERSI olculdu (mobil 375x812):

  * sticky WhatsApp bandi           : 135 px = ekranin %16,6'si (urun ilk ekranda YOK)
  * "Sepete Ekle"                   : 44 x 44 = 1.936 px^2  (ETIKETSIZ, yalniz ikon)
  * bandaki WhatsApp butonu         : 231 x 44 = 10.164 px^2 (etiketli)
  * oran (sepete-ekle / whatsapp)   : 0,19  -> WhatsApp 5,22 KAT buyuk

Hata SESSIZDIR: hicbir test kirmizi yanmaz, hicbir konsol izi kalmaz. Duzen bir kez
elle duzeltilse bile bir sonraki CSS dokunusunda sessizce geri gelir — bu yuzden kural
bir KAPIYLA kilitlenir, "bakildi iyi gorunuyor" ile DEGIL.

🔴 KANAL KALDIRILMAZ: bu kapi WhatsApp'in VARLIGINI da olcer (A5). Dengeyi "WhatsApp'i
silerek" saglamak bu kapida KIRMIZI yanar.

NE OLCER (bes bagimsiz eksen + kanal nobeti)
---------------------------------------------
  CTA-A1-ORAN        : alan(Sepete Ekle) / alan(en buyuk WhatsApp CTA'si) >= 1,0
                       MOBIL (375) ve MASAUSTU (1100) genisliklerinde AYRI AYRI.
  CTA-A2-BANT-PAYI   : sticky WhatsApp bandinin 812 px'lik mobil ekrandaki payi < %10.
                       Hem urun sayfasi (tools/build.py::PAGE_CSS) hem ana/sepet
                       sayfasi (index.html) icin ayri olculur.
  CTA-A3-SEPET-ALAN  : sepet panelinde birincil odeme CTA'si WhatsApp CTA'sindan
                       BELGE SIRASINDA once ve ALAN olarak buyuk (>= ORAN_TABANI).
  CTA-A4-DOKUNMA-44  : olculen her CTA'nin yuksekligi >= 44 px (WhatsApp kuculurken de).
  CTA-A5-KANAL-WA    : `wa.me` baglantilari + numara YERINDE, sepet butonu ETIKETLI.
  CTA-A6-GECIS-ORAN  : A3 orani GECIS PENCERESINDE de saglaniyor mu? (asagi)

🔴 CTA-A6 NEDEN VAR — "SETTLED YESIL" YANLIS YESILDI (olculdu, 11 Agu 2026, canli)
--------------------------------------------------------------------------------
Sepet paneli acilirken JS iki sinifi ayni anda takar: odeme butonu `.disabled`den
CIKAR, WhatsApp butonu `.ikincil`e GIRER. Iki kuralda da `transition:.15s` yaziyordu —
kisayolun `transition-property` degeri belirtilmedigi icin bu `all` demektir. Yani
font-size ve padding de ANIME olur ve panel, ~150 ms boyunca ESKI geometriyle
RENDER EDILIR. O pencerede canlida olculen (375x812, gercek `clientWidth=375`):

    odeme    317 x 43,5 = 13.790 px²      (hala `.disabled` font-size'i: 13,5 px)
    WhatsApp 249 x 54,25 = 13.516 px²     (hala `.ikincil` ONCESI: padding 14, 15,5 px)
    oran 1,02 — bagimsiz olcumde 0,978 (daha genis fontta WhatsApp ETIKETI SARIYOR,
    buton 44 -> 56,8 px'e uzuyor ve ikincil kanal birincil odemeyi GECIYOR)

Yerlesmis (settled) hal ise saglikli: odeme 317x46 = 14.582 · WhatsApp 232x44 = 10.197
· oran 1,43. Kapi YALNIZ settled hali modelledigi icin CTA-A3 "51,2 > 44,0" deyip
YESIL yaniyordu: Okan'in acikca istedigi seyin ihlalini GOREMIYORDU.

⚠️ PENCERE 150 ms DEGIL: gecis, belge GORUNMEZ (arka plan sekmesi / kisilmis pane)
iken hic ILERLEMEZ. Olculdu — `document.hidden=true` iken `getAnimations()` on iki
gecisi de `playState=running, currentTime=0` gosterdi; buton o halde KILITLI KALDI.
Yani ters oran gecici bir goz kirpmasi degil, gorunmeyen sekmede KALICI bir haldir.

A6 bunu SART olarak degil OLCUM olarak kurar: kapi `transition` bildiriminden
ETKILENEN ozellik kumesini cikarir; kume GEOMETRIYE dokunuyorsa gecis hali GERCEK bir
render halidir ve oran ORADA da saglanmalidir. Geometri hic anime edilmiyorsa gecis
penceresi YOKTUR ve A6, A3 ile ayni sayiyi verir (kapi bunu ACIKCA basar).

GEOMETRI NEREDEN TURER (elle defter YOK)
----------------------------------------
CSS: `build.PAGE_CSS` (urun sayfasinin TEK stil kaynagi) ve index.html'in <style>
blogu GERCEK bir mini-cascade ile ayristirilir (@media max-width bloklari dahil).
HTML: urun sayfasi `build.render_product()` ile SENTETIK bir fikstur urununden
GERCEKTEN uretilir; sepet paneli index.html'den okunur. Ikinci kopya tutulmaz.

Metin genisligi bir MODELDIR: `karakter * font-size * 0,55`. Model iki tarafa da AYNI
uygulanir, yani A1 bir ORAN iddiasidir ve modelin sabitine karsi dayaniklidir. A2/A4
ise yapisal (padding + min-height + kenarlik) olculerdir, metin modeline BAGLI DEGIL.

🔴 MODELIN UC DUZELTMESI (11 Agu, canli olcumle capalandi):
  1. SATIR YUKSEKLIGI KAYNAGA BAGLI. `<button>` UA sayfasinda `line-height:normal`
     tasir ve body'nin 1,5'ini MIRAS ALMAZ; `<a>` alir. Kapi eskiden ikisine de 1,5
     uyguluyordu ve odeme butonunu 51,2 px sanıyordu — canlida 46,0 px. Ayni yanlis,
     A3'u tam da ters dondugu yerde optimist yapiyordu.
  2. SARMA MODELLENIR. Butonun icerik genisligi KULLANILABILIR genisligi asarsa metin
     satirlara boluner ve buton UZAR. Kullanilabilir genislik elle yazilmaz: sepet
     panelinin kendi CSS'inden (`.cart-panel` width/max-width + `.cart-panel-foot`
     padding) turetilir; capa yoksa OLCULEMEDI.
  3. GENISLIK DE OLCULUR. `width:fit-content|max|min-content` daraltir; blok seviyesi
     (`display:block|flex|grid` ya da `width:100%`) kabi DOLDURUR. A3 artik yalniz
     YUKSEKLIK degil ALAN kiyaslar — canlida WhatsApp butonu daha KISA ama daha
     GENISKEN oran 1,02'ye dusmustu; yukseklik tek basina bunu gizliyordu.

OLCULEMEZSE "GECTI" DEMEZ
-------------------------
Gereken bir CSS kurali/bildirimi ya da HTML capasi yoksa kapi `OLCULEMEDI: <sebep>`
basar ve 3 ile doner. Sessiz yesil YASAKTIR.

CIKIS: 0 yesil · 1 kirmizi · 3 olculemedi.  Depoya YAZMAZ, ag ISTEMEZ.
KOSUM: python3 tools/cta-denge-kapisi.py [--kok /baska/agac]
Mutasyon bataryasi: python3 tools/cta-denge-mutasyon.py  (mutasyon DAIMA kopyaya)
"""
import argparse
import importlib
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

YESIL, KIRMIZI, OLCULEMEDI_RC = 0, 1, 3

# Mobil referans ekran (Okan'in sikayetinin olculdugu cihaz sinifi).
MOBIL_EN, MOBIL_BOY = 375, 812
MASAUSTU_EN = 1100
BANT_PAY_TAVANI = 0.10          # A2: sticky bandin ekran payi bunun ALTINDA olmali
ORAN_TABANI = 1.0               # A1: sepete-ekle / whatsapp
DOKUNMA_TABANI = 44.0           # A4: mobil dokunma hedefi alt siniri (px)

# Metin genisligi modeli — ORAN iddiasinda iki tarafa da ayni uygulanir.
KARAKTER_ORANI = 0.55
VARSAYILAN_SATIR_YUKSEKLIGI = 1.5   # body{line-height:1.5} — MIRAS ALAN ogeler (<a> vb.)
# 🔴 <button> UA sayfasinda `line-height:normal` tasir ve body'nin 1,5'ini MIRAS ALMAZ.
# Canli olcum (Chrome/mac, 375 px): 15,5 px yazi + 14 px dolgu -> 46,0 px buton, yani
# icerik 18,6 px = 1,20 x font. 1,5 varsayimi butonu 51,2 px sanıyordu (+%11 optimist).
BUTON_SATIR_YUKSEKLIGI = 1.20
VARSAYILAN_FONT = 16.0

# `width` degeri icerige gore BUZUSEN kume; digerleri blok kabi DOLDURUR sayilir.
DARALTAN_GENISLIK = {"fit-content", "max-content", "min-content"}
BLOK_DISPLAY = {"block", "flex", "grid"}

# 🔴 A6: `transition` bu ozelliklerden BIRINE dokunuyorsa gecis hali GERCEK bir render
# halidir (eski geometri ekranda kalir) ve oran ORADA da olculmelidir. `all` = hepsi.
GEOMETRI_OZELLIKLERI = {
    "all", "width", "min-width", "max-width", "height", "min-height", "max-height",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "font-size", "line-height", "gap", "row-gap", "column-gap",
    "border", "border-width", "border-top-width", "border-right-width",
    "border-bottom-width", "border-left-width",
}
# Sure / gecikme / yumusatma jetonlari — kisayolda OZELLIK ADI sayilmazlar.
_SURE = re.compile(r"^-?\d*\.?\d+m?s$", re.I)
_YUMUSATMA = {"ease", "linear", "ease-in", "ease-out", "ease-in-out",
              "step-start", "step-end", "normal", "none"}

HATALAR = []
OLCULEMEDI = []


def kontrol(jeton, kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + jeton + " · " + mesaj)
    if not kosul:
        HATALAR.append(jeton + " · " + mesaj)
    return bool(kosul)


def olculemedi(sebep):
    print("  ⚠️  OLCULEMEDI: " + sebep)
    OLCULEMEDI.append(sebep)


def olculemedi_kodu():
    """OLCULEMEDI kolunun cikis kodu — ASLA 0 olamaz.

    `OLCULEMEDI_RC` sabitini 0'a cekmek bu kapiyi "olcemedigi her durumda YESIL"
    hale getirirdi; bu depoda olculmus sinif ([[fail-slow-fail-opendir]]). `or KIRMIZI`
    o sessiz-yesil yolunu YAPISAL olarak kapatir: sabit bozulsa bile kapi kirmizi
    doner. Mutasyon kaniti: tools/cta-denge-mutasyon.py :: M7."""
    return OLCULEMEDI_RC or KIRMIZI


# ---------------------------------------------------------------- CSS cascade
YORUM = re.compile(r"/\*.*?\*/", re.S)
MEDIA = re.compile(r"@media[^{]*?max-width\s*:\s*(\d+(?:\.\d+)?)px[^{]*\{", re.I)


def _bildirimler(govde):
    d = {}
    for parca in govde.split(";"):
        if ":" not in parca:
            continue
        ad, _, deger = parca.partition(":")
        ad = ad.strip().lower()
        if ad:
            d[ad] = deger.strip()
    return d


def css_kurallari(css):
    """CSS metnini (secici, bildirimler, media_max_width) listesine cevirir.

    Tek seviye @media destegi yeter: bu depoda ic ice media YOK. Ayristirilamayan
    (ic ice) blok gorulurse None doner -> cagiran taraf OLCULEMEDI basar."""
    css = YORUM.sub("", css)
    kurallar = []
    i, n = 0, len(css)
    media_tavan = None
    media_derinlik = 0
    while i < n:
        if css[i].isspace():
            i += 1
            continue
        m = MEDIA.match(css, i)
        if m:
            if media_derinlik:
                return None
            media_tavan = float(m.group(1))
            media_derinlik = 1
            i = m.end()
            continue
        if css[i] == "}":
            if media_derinlik:
                media_derinlik = 0
                media_tavan = None
            i += 1
            continue
        if css[i] == "@":
            # media disi at-kurali (keyframes vb.) — blogunu atla
            ac = css.find("{", i)
            if ac == -1:
                break
            derin, j = 1, ac + 1
            while j < n and derin:
                if css[j] == "{":
                    derin += 1
                elif css[j] == "}":
                    derin -= 1
                j += 1
            i = j
            continue
        ac = css.find("{", i)
        if ac == -1:
            break
        kapa = css.find("}", ac)
        if kapa == -1:
            return None
        secici = css[i:ac].strip()
        if secici:
            for tek in secici.split(","):
                tek = " ".join(tek.split())
                if tek:
                    kurallar.append((tek, _bildirimler(css[ac + 1:kapa]), media_tavan))
        i = kapa + 1
    return kurallar


def stil(kurallar, jetonlar, viewport):
    """Verilen secici jetonlari icin kaynak sirasina gore birlesmis bildirimler."""
    birlesik = {}
    for secici, bildirim, tavan in kurallar:
        if tavan is not None and viewport > tavan:
            continue
        if secici in jetonlar:
            birlesik.update(bildirim)
    return birlesik


def kural_var(kurallar, secici):
    return any(s == secici for s, _, _ in kurallar)


# ---------------------------------------------------------------- geometri
def _px(deger, yedek=None):
    if deger is None:
        return yedek
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*px", deger)
    if m:
        return float(m.group(1))
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*", deger or "")
    if m:
        return float(m.group(1))
    return yedek


def _dortlu(deger):
    """padding kisayolu -> (ust, sag, alt, sol); cozulemezse None."""
    if deger is None:
        return None
    parcalar = [p for p in deger.replace("!important", "").split() if p]
    sayilar = []
    for p in parcalar:
        v = _px(p)
        if v is None:
            return None
        sayilar.append(v)
    if len(sayilar) == 1:
        return (sayilar[0],) * 4
    if len(sayilar) == 2:
        return (sayilar[0], sayilar[1], sayilar[0], sayilar[1])
    if len(sayilar) == 3:
        return (sayilar[0], sayilar[1], sayilar[2], sayilar[1])
    if len(sayilar) == 4:
        return tuple(sayilar)
    return None


def _kenarlik(d):
    ham = d.get("border")
    if ham is None or ham.strip() in ("none", "0"):
        return 0.0
    v = _px(ham, None)
    return v if v is not None else 0.0


def flex_buyume(d):
    """Ogenin `flex-grow` degeri. `flex` kisayolundan da okunur (`flex:1 1 auto` -> 1,0).

    🔴 `flex:none` = `0 0 auto` ve `flex:auto` = `1 1 auto` (CSS kisayol semantigi).
    Bu ayrim OLCULMUS bir tuzaktir: `.ikon-sepet{flex:1 1 auto}` butonu satirin
    bosluguna kadar buyutuyordu ve kapi bunu GORMUYORDU."""
    ayri = d.get("flex-grow")
    if ayri is not None:
        return _px(ayri, 0.0) or 0.0
    ham = (d.get("flex") or "").strip().lower()
    if not ham:
        return 0.0
    if ham == "none":
        return 0.0
    if ham in ("auto", "initial"):
        return 1.0 if ham == "auto" else 0.0
    ilk = ham.split()[0]
    return _px(ilk, 0.0) or 0.0


def olc_kutu(d, metin, ikon_px, varsayilan_lh=VARSAYILAN_SATIR_YUKSEKLIGI,
             kullanilabilir_en=None, buyume_eni=None, sarmaz=False):
    """Bir buton/link kutusunun (genislik, yukseklik, satir_sayisi) olcusu.

    Cozulemezse None doner. Donen uclunun ilk iki ogesi (w, h) eski cagri bicimiyle
    BIREBIR uyumludur; ucuncusu SARMA nobetinin (CTA-A7) okudugu satir sayisidir.

    varsayilan_lh    : `line-height` BILDIRILMEMISSE kullanilacak carpan. <button> icin
                       BUTON_SATIR_YUKSEKLIGI (UA `normal`), miras alan ogeler icin 1,5.
    kullanilabilir_en: kabin ic genisligi. Verilirse (a) blok seviyesindeki kutu onu
                       DOLDURUR, (b) metin sigmiyorsa SARAR ve buton UZAR. Verilmezse
                       sarma modellenmez — cagiran taraf bunu bilerek yapmali.
    buyume_eni       : ogenin `flex-grow`u pozitifse BUYUYECEGI hedef genislik. Flex
                       satirinda kalan bosluk cagiran tarafca hesaplanip verilir.
    sarmaz           : etiket `white-space:nowrap` tasiyorsa True. O zaman metin
                       sigmasa bile kutu UZAMAZ (tasar) — yukseklik sabit kalir."""
    dolgu = _dortlu(d.get("padding"))
    if dolgu is None:
        return None
    fs = _px(d.get("font-size"), VARSAYILAN_FONT)
    lh_ham = d.get("line-height")
    lh = None
    if lh_ham is not None:
        try:
            lh = float(lh_ham.strip())
        except ValueError:
            v = _px(lh_ham)
            lh = (v / fs) if (v and fs) else None
    if lh is None:
        lh = varsayilan_lh
    kb = _kenarlik(d)
    bosluk = _px(d.get("gap"), 0.0) or 0.0
    metin_w = len(metin) * fs * KARAKTER_ORANI
    yatay_sabit = dolgu[1] + dolgu[3] + 2 * kb + ((ikon_px + bosluk) if ikon_px else 0.0)
    w = yatay_sabit + metin_w

    # --- genislik: daraltan deger mi, kabi dolduran blok mu?
    daraltan = (d.get("width") or "").strip() in DARALTAN_GENISLIK
    blok = ((d.get("display") or "").strip() in BLOK_DISPLAY
            or (d.get("width") or "").strip() == "100%")
    if kullanilabilir_en is not None:
        if daraltan:
            w = min(w, kullanilabilir_en)
        elif blok:
            w = kullanilabilir_en
        else:
            w = min(w, kullanilabilir_en)

    # --- FLEX BUYUMESI: pozitif `flex-grow` tasiyan oge satirin bosluguna YAYILIR.
    # `fit-content` bunu ENGELLEMEZ (flex-basis/grow, width'ten sonra uygulanir), bu
    # yuzden buyume kontrolu daraltan-genislik kontrolunden SONRA gelir.
    if buyume_eni is not None and flex_buyume(d) > 0:
        w = max(w, buyume_eni)

    # 🔴 SIRA ONEMLI: `width`/`min-width` SARMADAN ONCE uygulanir. Eskiden sarma once
    # hesaplaniyordu, yani bir `min-width` kutuyu genisletip sarmayi cozse bile kapi
    # metni hala SARMIS sayiyordu (sahte-yuksek buton). CSS'te kutu genisligi once
    # yerlesir, satir kirilmasi O genislige gore olur.
    sabit_w = _px(d.get("width"))
    if sabit_w is not None:
        w = sabit_w
    en_az_w = _px(d.get("min-width"))
    if en_az_w is not None:
        w = max(w, en_az_w)

    # --- SIGMA / SARMA. Iki AYRI soru, birbirine karistirilmaz:
    #   sigdi : metin kutunun ic genisligine SIGIYOR mu?  (CTA-A7'nin okudugu)
    #   satir : kutu kac satir YUKSELIYOR?                (yukseklik modelinin okudugu)
    # `white-space:nowrap` tasiyan etiket sigmasa bile SARMAZ; kutu uzamaz, metin TASAR.
    # Ikisini tek sayiya indirgemek sessiz bir yesil dogurur: nowrap'li bir etiket
    # kirpilirken "satir=1" diye SAGLIKLI gorunurdu.
    satir, sigdi = 1, True
    if kullanilabilir_en is not None and metin_w > 0:
        ic_en = w - yatay_sabit
        # epsilon: `w = yatay_sabit + metin_w` kayan nokta ile birebir geri gelmeyebilir;
        # tolerans olmadan tam sigan metin SARMIS gorunup butonu sahte uzatiyordu.
        if ic_en > 0 and metin_w > ic_en + 1e-6:
            sigdi = False
            if not sarmaz:
                satir = int(metin_w / ic_en) + (0 if abs(metin_w % ic_en) < 1e-9 else 1)
        elif ic_en <= 0:
            sigdi = False

    icerik_h = max(fs * lh * satir, ikon_px or 0.0)
    h = dolgu[0] + dolgu[2] + 2 * kb + icerik_h
    sabit_h = _px(d.get("height"))
    if sabit_h is not None:
        h = sabit_h
    en_az_h = _px(d.get("min-height"))
    if en_az_h is not None:
        h = max(h, en_az_h)
    return (w, h, satir, sigdi)


# ---------------------------------------------------------------- gecis penceresi
def gecis_ozellikleri(d):
    """`transition` kisayolundan ETKILENEN ozellik adlari kumesi.

    `transition:.15s` gibi ozellik adi TASIMAYAN bir kisayol `all` demektir — bu depoda
    tam olarak bu yazim, sepet CTA'larinin geometrisini anime edip ters bir render hali
    dogurmustu. `transition-property` ayri bildirilmisse O kazanir."""
    ayri = d.get("transition-property")
    if ayri is not None:
        return {p.strip().lower() for p in ayri.split(",") if p.strip()}
    ham = d.get("transition")
    if ham is None:
        return set()
    ham = ham.replace("!important", "")
    kume = set()
    for parca in ham.split(","):
        jetonlar = [t for t in re.split(r"\s+", parca.strip()) if t]
        # cubic-bezier(...) / steps(...) tek jeton olarak gelir; ozellik adi degildir.
        ad = None
        for t in jetonlar:
            tl = t.lower()
            if _SURE.match(tl) or tl in _YUMUSATMA or "(" in tl:
                continue
            ad = tl
            break
        kume.add(ad if ad else "all")
    return kume


def gecis_stili(oncesi, sonrasi, gecisli):
    """Sinif takasinin ILK karesindeki (henuz yerlesmemis) bildirim sozlugu.

    CSS semantigi birebir: GECIS LISTESINDEKI ozellikler ESKI degerden baslar; listede
    OLMAYANLAR aninda YENI degere atlar. Yeni halde VAR olup eski halde OLMAYAN ve
    gecise dahil bir geometri ozelligi (or. `.ikincil`in `width:fit-content`i) eski
    halde YOKTUR -> sozlukten DUSURULUR, yani kutu o karede eski (dolduran) genisligiyle
    olculur. Bu IHTIYATLI yondur: `auto` <-> `fit-content` interpolasyonu tarayiciya
    gore degisir, kapi EN KOTU hali alir ve fail-closed kalir."""
    if not (gecisli & GEOMETRI_OZELLIKLERI):
        return dict(sonrasi)                      # gecis penceresi YOK
    hepsi = "all" in gecisli
    d = dict(sonrasi)
    for ad in list(d):
        if not (hepsi or ad in gecisli or ad.split("-")[0] in gecisli):
            continue
        if ad in oncesi:
            d[ad] = oncesi[ad]
        elif ad in GEOMETRI_OZELLIKLERI:
            del d[ad]
    for ad, deger in oncesi.items():
        if ad not in d and (hepsi or ad in gecisli or ad.split("-")[0] in gecisli):
            d[ad] = deger
    return d


SPAN = re.compile(r'<span class="([^"]+)">(.*?)</span>', re.S)


def gorunur_metin(kurallar, ic_html, viewport):
    """Bir butonun O VIEWPORT'ta GORUNEN metni: display:none olan span'lar DUSER.

    Gizleme kurali VIEWPORT'a gore cozulur: `stil()` bir @media max-width blogunu
    yalnizca viewport tavanin ALTINDAysa tuketir, media DISI (global) kuralı ise HER
    viewport'ta tuketir. Bu ayrim olcumun tasiyicisidir.

    🔴 GUNCEL (11 Agu, Okan karari): `.wa-uzun{display:none}` artik GLOBAL — mobil bloktan
    cikarilip temel CSS'e tasindi. Yani hem 375 hem 1100 px'te hap etiketi KISA
    ("Iletisime Gecin") sayilir. Masaustu CTA dengesini tutan sey budur; `.ikon-sepet`in
    eski `min-width:210px` denge tabani bu yuzden KALDIRILDI. Kural yeniden mobil-only'ye
    daralirsa masaustu hapi buyur ve CTA-A1 KIRMIZI yanmalidir — mutant: M12."""
    def _ele(m):
        for sinif in m.group(1).split():
            d = stil(kurallar, {"." + sinif}, viewport)
            if (d.get("display") or "").strip() == "none":
                return ""
        return m.group(2)
    onceki = None
    while onceki != ic_html:
        onceki = ic_html
        ic_html = SPAN.sub(_ele, ic_html)
    return " ".join(re.sub(r"<[^>]+>", "", ic_html).split())


def ikon_olcusu(kurallar, jetonlar, viewport):
    for j in jetonlar:
        d = stil(kurallar, {j + " svg"}, viewport)
        v = _px(d.get("width"))
        if v is not None:
            return v
    return 0.0


def bant_yuksekligi(kurallar, metin, buton_metni, viewport):
    """Sticky yardim bandinin yuksekligi. Modellenemezse (sebep, None) doner."""
    dis = stil(kurallar, {".help-cta"}, viewport)
    ic = stil(kurallar, {".help-cta-inner"}, viewport)
    yazi = stil(kurallar, {".help-cta-text"}, viewport)
    btn = stil(kurallar, {".help-cta-btn"}, viewport)
    if not ic or not btn:
        return "band capasi yok (.help-cta-inner / .help-cta-btn kurali bulunamadi)", None
    if "sticky" not in (dis.get("position") or ""):
        return "bant sticky degil — olcum ekseni gecersiz", None
    dolgu = _dortlu(ic.get("padding"))
    if dolgu is None:
        return ".help-cta-inner padding cozulemedi", None
    sarma = (ic.get("flex-wrap") or "wrap").strip()
    if sarma != "nowrap":
        return ("bant satir sayisi modellenemedi: .help-cta-inner flex-wrap='%s' "
                "(mobilde 'nowrap' bekleniyor)" % sarma), None
    fs = _px(yazi.get("font-size"), VARSAYILAN_FONT)
    lh_ham = yazi.get("line-height")
    try:
        lh = float((lh_ham or "").strip())
    except ValueError:
        lh = VARSAYILAN_SATIR_YUKSEKLIGI
    kirpma = yazi.get("-webkit-line-clamp")
    if kirpma is None:
        return ".help-cta-text satir kirpmasi (-webkit-line-clamp) yok — yukseklik ustsuz", None
    try:
        satir = int(kirpma.strip())
    except ValueError:
        return "-webkit-line-clamp sayisi cozulemedi: %r" % kirpma, None
    yazi_h = satir * fs * lh
    kutu = olc_kutu(btn, buton_metni, ikon_olcusu(kurallar, [".help-cta-btn"], viewport))
    if kutu is None:
        return ".help-cta-btn olculemedi (padding yok)", None
    alt_kenar = _px(dis.get("border-bottom"), 0.0) or 0.0
    return None, (dolgu[0] + dolgu[2] + alt_kenar + max(yazi_h, kutu[1]), kutu)


# ---------------------------------------------------------------- kaynaklar
def build_yukle(kok):
    yol = os.path.join(kok, "tools")
    if not os.path.exists(os.path.join(yol, "build.py")):
        return None, "tools/build.py yok: %s" % kok
    sys.path.insert(0, yol)
    os.chdir(kok)
    for ad in list(sys.modules):
        if ad == "build":
            del sys.modules[ad]
    try:
        return importlib.import_module("build"), None
    except Exception as e:                                   # noqa: BLE001
        return None, "tools/build.py yuklenemedi: %s" % e


SENTETIK = {
    "id": "cta-denge-fikstur",
    "kategori": "Tamirat",
    "marka": [],
    "baslik": "CTA denge olcum fiksturu",
    "aciklama": "Kapi fiksturu. Yaklasik dis olculer: 10 x 10 x 10 mm",
    "fiyat": "850 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/cta-denge-fikstur-1.jpg"],
}

STIL_BLOK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)


def index_stili(metin):
    bloklar = STIL_BLOK.findall(metin)
    return "\n".join(bloklar) if bloklar else None


# ---------------------------------------------------------------- bolumler
def bolum_urun(kurallar, sayfa, wa_no):
    """A1/A2/A4/A5 — urun sayfasi ekseni. (oranlar, bant_payi) doner."""
    print("\n(1) URUN SAYFASI — Sepete Ekle vs WhatsApp")
    sepet_jeton = {".ikon-btn", ".ikon-sepet"}
    wa_ikon_jeton = {".ikon-btn", ".ikon-wa"}
    for gerek in (".ikon-btn", ".ikon-sepet", ".ikon-wa", ".help-cta-btn"):
        if not kural_var(kurallar, gerek):
            olculemedi("urun sayfasi CSS capasi yok: %s" % gerek)
            return None
    if 'class="cart-label"' not in sayfa:
        olculemedi("uretilen sayfada .cart-label yok — Sepete Ekle etiketi okunamadi")
        return None
    m = re.search(r'<span class="cart-label">([^<]*)</span>', sayfa)
    sepet_metni = m.group(1) if m else ""
    m = re.search(r'class="help-cta-btn"[^>]*>(.*?)</a>', sayfa, re.S)
    if not m:
        olculemedi("uretilen sayfada .help-cta-btn baglantisi yok")
        return None
    bant_btn_ham = m.group(1)

    oranlar, bant_payi, dokunmalar, sarmalar = {}, {}, [], []
    for ad, vw in (("mobil", MOBIL_EN), ("masaustu", MASAUSTU_EN)):
        bant_btn_metni = gorunur_metin(kurallar, bant_btn_ham, vw)
        d_sepet = stil(kurallar, sepet_jeton, vw)
        d_wa = stil(kurallar, wa_ikon_jeton, vw)
        d_satir = stil(kurallar, {".eylem-ikonlar"}, vw)
        # 🔴 KULLANILABILIR GENISLIK — elle sabit YOK, sayfa kabindan turer. Turetilemezse
        # SARMA da FLEX BUYUMESI de modellenemez; "gecti" SAYILMAZ.
        panel_en = eylem_satir_genisligi(kurallar, vw)
        if panel_en is None:
            olculemedi("urun sayfasi eylem satirinin genisligi turetilemedi "
                       "(main max-width/padding · .detail grid-template-columns/gap · "
                       ".opsiyonlar padding capasi yok) — %s" % ad)
            return None
        k_wa = olc_kutu(d_wa, "", ikon_olcusu(kurallar, [".ikon-btn"], vw))
        if k_wa is None:
            olculemedi("urun sayfasi WhatsApp ikonu olculemedi (%s)" % ad)
            return None
        # `.eylem-ikonlar` satiri: `width:100%` ise paneli doldurur, degilse icerige gore
        # buzusur. Sepete Ekle `flex-grow` tasiyorsa satirda KALAN boslugu yutar.
        satir_en = panel_en if (d_satir.get("width") or "").strip() == "100%" else None
        satir_bosluk = _px(d_satir.get("gap"), 0.0) or 0.0
        buyume_eni = None if satir_en is None else (satir_en - satir_bosluk - k_wa[0])
        etiket_sarmaz = (stil(kurallar, {".cart-label"}, vw).get("white-space") or
                         "").strip() == "nowrap"
        k_sepet = olc_kutu(d_sepet, sepet_metni,
                           ikon_olcusu(kurallar, [".ikon-btn"], vw),
                           BUTON_SATIR_YUKSEKLIGI, panel_en, buyume_eni, etiket_sarmaz)
        if k_sepet is None:
            olculemedi("urun sayfasi Sepete Ekle butonu olculemedi (%s)" % ad)
            return None
        sarmalar.append(("%s Sepete Ekle" % ad, k_sepet[2], k_sepet[3]))
        sebep, sonuc = bant_yuksekligi(kurallar, "", bant_btn_metni, vw)
        if vw == MOBIL_EN:
            if sonuc is None:
                olculemedi("urun sayfasi sticky bandi: %s" % sebep)
                return None
            bant_h, k_bant = sonuc
            bant_payi["urun"] = bant_h / MOBIL_BOY
            print("     mobil bant: %.1f px = %%%.1f (%d px ekran)"
                  % (bant_h, 100 * bant_payi["urun"], MOBIL_BOY))
            dokunmalar.append(("urun bant WhatsApp", k_bant[1]))
        else:
            if sonuc is None:
                # masaustunde bant TEK SATIR degil (sarabilir) — A1 icin yalniz
                # buton olcusu gerekir, bandin YUKSEKLIGI degil.
                d_btn = stil(kurallar, {".help-cta-btn"}, vw)
                k_bant = olc_kutu(d_btn, bant_btn_metni,
                                  ikon_olcusu(kurallar, [".help-cta-btn"], vw))
                if k_bant is None:
                    olculemedi("masaustu .help-cta-btn olculemedi")
                    return None
            else:
                k_bant = sonuc[1]
        wa_en_buyuk = max(k_wa[0] * k_wa[1], k_bant[0] * k_bant[1])
        alan_sepet = k_sepet[0] * k_sepet[1]
        oranlar[ad] = alan_sepet / wa_en_buyuk if wa_en_buyuk else 0.0
        print("     %-9s Sepete Ekle %.0fx%.0f = %.0f px² · WhatsApp (en buyuk) "
              "%.0f px² · oran %.2f"
              % (ad, k_sepet[0], k_sepet[1], alan_sepet, wa_en_buyuk, oranlar[ad]))
        dokunmalar.append(("%s Sepete Ekle" % ad, k_sepet[1]))
        dokunmalar.append(("%s WhatsApp ikonu" % ad, k_wa[1]))
        # 🔴 TABANI KAPI YAZAR, INSAN DEGIL: CSS'teki `min-width` bir tasarim degeri
        # degil, bu satirin TURETTIGI dengeleme tabanidir. Sayiyi burada basmak, taban
        # bandin hapi degistiginde kaydiginda gerekcenin izlenebilir kalmasini saglar.
        print("     %-9s -> Sepete Ekle bu eksende en az %.1f px genis olmali "
              "(%.0f px² / %.0f px yukseklik)"
              % (ad, wa_en_buyuk / k_sepet[1], wa_en_buyuk, k_sepet[1]))

    en_dusuk = min(oranlar.values())
    kontrol("CTA-A1-ORAN", en_dusuk >= ORAN_TABANI,
            "Sepete Ekle / WhatsApp alan orani en dusuk %.2f (taban %.2f) "
            "[mobil %.2f · masaustu %.2f]"
            % (en_dusuk, ORAN_TABANI, oranlar["mobil"], oranlar["masaustu"]))
    # 🔴 CTA-A7 (11 Agu, Okan'in daraltma talebiyle eklendi): buton METNE gore
    # daraltildiginda yeni bir sessiz bozulma sinifi acilir — etiket kutuya SIGMAZ.
    # `.cart-label{white-space:nowrap}` oldugu icin bu SARMA olarak degil KIRPILMA
    # olarak goruntlenir: buton yuksekligi ayni kalir, oran saglikli gorunur, metin
    # kesilir. A1/A4 bu vakada YESIL yanar; olcen tek eksen budur.
    tasan = [a for a, _, sigdi in sarmalar if not sigdi]
    cok_satir = [(a, s) for a, s, _ in sarmalar if s != 1]
    kontrol("CTA-A7-ETIKET-SIGDI", not tasan and not cok_satir,
            "Sepete Ekle etiketi TEK satirda ve kutuya sigiyor (%s)"
            % ("hepsi" if not (tasan or cok_satir)
               else "sigmayan: " + ", ".join(tasan) + "; sarmis: " + ", ".join(
                   "%s=%d satir" % (a, s) for a, s in cok_satir)))
    kucuk = [(a, h) for a, h in dokunmalar if h < DOKUNMA_TABANI]
    kontrol("CTA-A4-DOKUNMA-44", not kucuk,
            "urun sayfasi dokunma hedefleri >= %d px (%s)"
            % (DOKUNMA_TABANI,
               "hepsi" if not kucuk else "ihlal: " + ", ".join(
                   "%s=%.1f" % (a, h) for a, h in kucuk)))
    wa_saglam = (wa_no in sayfa) and ('id="orderAlt"' in sayfa) and \
                ("wa.me/" in sayfa) and bool(sepet_metni.strip())
    kontrol("CTA-A5-KANAL-WA", wa_saglam,
            "urun sayfasinda WhatsApp kanali + numara YERINDE ve sepet butonu "
            "etiketli (etiket=%r)" % sepet_metni)
    return oranlar, bant_payi


def eylem_satir_genisligi(kurallar, viewport):
    """Urun sayfasinda `.eylem-ikonlar` satirinin KULLANILABILIR ic genisligi (px).

    🔴 NEDEN VAR (olculdu, 11 Agu 2026 — modelin tam-genislik varsayimi yanlisti):
    Kapi eskiden urun sayfasi butonlarini `kullanilabilir_en=None` ile olcuyordu, yani
    (a) kabin genisligini hic turetmiyor, (b) SARMAYI modelleyemiyor, (c) `flex-grow`
    ile BUYUYEN bir butonu goremiyordu. Mobilde `.eylem-ikonlar{width:100%}` +
    `.ikon-sepet{flex:1 1 auto}` butonu satirin bosluguna kadar sisiriyordu: kapi
    min-width'ten 200 px sanıyordu, tarayicida olculen 249 px idi (%25 sapma).

    Zincir CSS'ten turer, elle sabit YOK:
        main{max-width; padding}  ->  .detail{grid-template-columns; gap}
        ->  .opsiyonlar{padding + border}
    Capa eksikse None doner ve cagiran taraf OLCULEMEDI basar."""
    ana = stil(kurallar, {"main"}, viewport)
    detay = stil(kurallar, {".detail"}, viewport)
    panel = stil(kurallar, {".opsiyonlar"}, viewport)
    if not ana or not detay or not panel:
        return None
    mx = _px(ana.get("max-width"))
    if mx is None:
        return None
    w = min(mx, float(viewport))
    dolgu = _dortlu(ana.get("padding"))
    if dolgu is None:
        return None
    w -= dolgu[1] + dolgu[3]

    # --- grid kolon sayisi: `1fr 1fr` -> 2, `1fr` -> 1. Baska bir yazim cozulmez.
    kolonlar = (detay.get("grid-template-columns") or "").split()
    if not kolonlar or any(k != "1fr" for k in kolonlar):
        return None
    n = len(kolonlar)
    if n > 1:
        bosluk = _px(detay.get("gap"))
        if bosluk is None:
            return None
        w = (w - (n - 1) * bosluk) / n

    p_dolgu = _dortlu(panel.get("padding"))
    if p_dolgu is None:
        return None
    w -= p_dolgu[1] + p_dolgu[3] + 2 * _kenarlik(panel)
    return w if w > 0 else None


def sepet_ic_genisligi(kurallar, viewport=MOBIL_EN):
    """Sepet panelinin BUTONLARA kalan ic genisligi (px). Turetilemezse None.

    Elle sabit yazilmaz: `.cart-panel{width; max-width}` + `.cart-panel-foot{padding}`
    okunur. `max-width:92vw` gibi vw degerleri viewport'a gore cozulur. Canli teyit
    (375 px ekran): min(380, 0,92x375) - 2x14 = 317 px — tarayicida olculen deger de
    tam 317 px."""
    panel = stil(kurallar, {".cart-panel"}, viewport)
    foot = stil(kurallar, {".cart-panel-foot"}, viewport)
    if not panel or not foot:
        return None
    w = _px(panel.get("width"))
    if w is None:
        return None
    mx = (panel.get("max-width") or "").strip()
    if mx:
        m = re.fullmatch(r"(\d+(?:\.\d+)?)vw", mx, re.I)
        if m:
            w = min(w, float(m.group(1)) / 100.0 * viewport)
        else:
            v = _px(mx)
            if v is None:
                return None                      # cozulemeyen kisit -> OLCULEMEDI
            w = min(w, v)
    dolgu = _dortlu(foot.get("padding"))
    if dolgu is None:
        return None
    ic = w - dolgu[1] - dolgu[3]
    return ic if ic > 0 else None


def bolum_sepet(kok, wa_no):
    """A2 (ana/sepet sayfasi bandi) + A3 — sepet panelinde sira ve boyut."""
    print("\n(2) ANA/SEPET SAYFASI — bant payi + odeme/WhatsApp sirasi")
    yol = os.path.join(kok, "index.html")
    if not os.path.exists(yol):
        olculemedi("index.html yok: %s" % yol)
        return None
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    css = index_stili(metin)
    if css is None:
        olculemedi("index.html icinde <style> blogu yok")
        return None
    kurallar = css_kurallari(css)
    if kurallar is None:
        olculemedi("index.html CSS'i ayristirilamadi (ic ice @media?)")
        return None
    for gerek in (".help-cta-inner", ".help-cta-btn", ".help-cta-text",
                  ".cart-pay-btn", ".cart-order-btn", ".cart-order-btn.ikincil"):
        if not kural_var(kurallar, gerek):
            olculemedi("index.html CSS capasi yok: %s" % gerek)
            return None

    m = re.search(r'class="help-cta-btn"[^>]*>(.*?)</a>', metin, re.S)
    if not m:
        olculemedi("index.html'de .help-cta-btn baglantisi yok")
        return None
    bant_btn_metni = gorunur_metin(kurallar, m.group(1), MOBIL_EN)
    sebep, sonuc = bant_yuksekligi(kurallar, "", bant_btn_metni, MOBIL_EN)
    if sonuc is None:
        olculemedi("index.html sticky bandi: %s" % sebep)
        return None
    bant_h, k_bant = sonuc
    pay = bant_h / MOBIL_BOY
    print("     mobil bant: %.1f px = %%%.1f" % (bant_h, 100 * pay))

    i_pay = metin.find('id="cartPay"')
    i_wa = metin.find('id="cartOrder"')
    if i_pay == -1 or i_wa == -1:
        olculemedi("sepet panelinde cartPay/cartOrder capasi yok")
        return None
    # KULLANILABILIR GENISLIK — elle sabit YOK, sepet panelinin KENDI CSS'inden turer.
    ic_en = sepet_ic_genisligi(kurallar)
    if ic_en is None:
        olculemedi("sepet panelinin ic genisligi turetilemedi (.cart-panel width/"
                   "max-width ya da .cart-panel-foot padding capasi yok) — SARMA "
                   "modellenemez, 'gecti' SAYILMAZ")
        return None
    print("     sepet paneli ic genisligi: %.1f px (375 px ekranda)" % ic_en)

    # Sinif kumeleri: (yerlesmis hal, takas ONCESI hal). JS panelde ikisini AYNI ANDA
    # takar — odeme `.disabled`den cikar, WhatsApp `.ikincil`e girer.
    d_pay = stil(kurallar, {".cart-pay-btn"}, MOBIL_EN)
    d_pay0 = stil(kurallar, {".cart-pay-btn", ".cart-pay-btn.disabled"}, MOBIL_EN)
    d_wa = stil(kurallar, {".cart-order-btn", ".cart-order-btn.ikincil"}, MOBIL_EN)
    d_wa0 = stil(kurallar, {".cart-order-btn"}, MOBIL_EN)
    m = re.search(r'id="cartPay"[^>]*>\s*([^<]*)', metin)
    pay_metni = " ".join((m.group(1) if m else "").split())
    m = re.search(r'id="cartOrder"[^>]*>(.*?)</a>', metin, re.S)
    wa_metni = gorunur_metin(kurallar, m.group(1) if m else "", MOBIL_EN)
    wa_ikon = ikon_olcusu(kurallar, [".cart-order-btn"], MOBIL_EN)

    def _olc(d_p, d_w):
        # odeme = <button> (UA line-height:normal) · WhatsApp = <a> (body'den 1,5 miras)
        kp = olc_kutu(d_p, pay_metni, 0.0, BUTON_SATIR_YUKSEKLIGI, ic_en)
        kw = olc_kutu(d_w, wa_metni, wa_ikon, VARSAYILAN_SATIR_YUKSEKLIGI, ic_en)
        return kp, kw

    k_pay, k_wa = _olc(d_pay, d_wa)
    if k_pay is None or k_wa is None:
        olculemedi("sepet paneli butonlari olculemedi")
        return None
    tam_genislik_pay = (d_pay.get("width") or "").strip() in ("100%", "auto") or \
                       (d_pay.get("display") or "").strip() in ("block", "flex")
    # 🔴 `auto` DARALTMAZ: blok seviyesindeki bir flex kabi `width:auto` ile satiri
    # DOLDURUR (tarayicida olculdu — ikincil WhatsApp yine tam genislikteydi). Kapinin
    # kabul ettigi tek daraltici deger kumesi icerige gore buzusen degerlerdir.
    wa_dar = (d_wa.get("width") or "").strip() in DARALTAN_GENISLIK
    alan_pay, alan_wa = k_pay[0] * k_pay[1], k_wa[0] * k_wa[1]
    oran_sepet = (alan_pay / alan_wa) if alan_wa else 0.0
    print("     yerlesmis: odeme %.0fx%.0f = %.0f px² (%r) · WhatsApp %.0fx%.0f = "
          "%.0f px² (%r) · oran %.2f · WhatsApp dar mi: %s"
          % (k_pay[0], k_pay[1], alan_pay, pay_metni,
             k_wa[0], k_wa[1], alan_wa, wa_metni, oran_sepet, wa_dar))
    # 🔴 A3 artik ALAN kiyasliyor. Yukseklik tek basina yaniltir: canlida WhatsApp
    # butonu odemeden KISA ama gecis penceresinde cok daha GENISTI ve oran 1,02'ye
    # dusuyordu — "daha yuksek" iddiasi o vakada YESIL kaliyordu.
    kontrol("CTA-A3-SEPET-ALAN",
            i_pay < i_wa and oran_sepet >= ORAN_TABANI and tam_genislik_pay and wa_dar,
            "birincil odeme CTA'si WhatsApp'tan ONCE (%d < %d) ve ALAN orani %.2f "
            ">= %.2f; odeme tam genislikte, WhatsApp ikincil/dar"
            % (i_pay, i_wa, oran_sepet, ORAN_TABANI))

    # ---- A6: GECIS PENCERESI (sinif takasinin ilk karesi GERCEK bir render halidir)
    gecisli = gecis_ozellikleri(d_pay) | gecis_ozellikleri(d_wa)
    geometrik = sorted(gecisli & GEOMETRI_OZELLIKLERI)
    if not geometrik:
        print("     gecis penceresi YOK — sepet CTA'larinin `transition` bildirimi "
              "geometriye dokunmuyor (anime edilen: %s)"
              % (", ".join(sorted(gecisli)) or "hicbir sey"))
        oran_gecis = oran_sepet
        k_pay_g, k_wa_g = k_pay, k_wa
    else:
        g_pay = gecis_stili(d_pay0, d_pay, gecis_ozellikleri(d_pay))
        g_wa = gecis_stili(d_wa0, d_wa, gecis_ozellikleri(d_wa))
        k_pay_g, k_wa_g = _olc(g_pay, g_wa)
        if k_pay_g is None or k_wa_g is None:
            olculemedi("gecis penceresi butonlari olculemedi")
            return None
        a_p, a_w = k_pay_g[0] * k_pay_g[1], k_wa_g[0] * k_wa_g[1]
        oran_gecis = (a_p / a_w) if a_w else 0.0
        print("     GECIS: odeme %.0fx%.0f = %.0f px² · WhatsApp %.0fx%.0f = %.0f px² "
              "· oran %.2f  (anime edilen geometri: %s)"
              % (k_pay_g[0], k_pay_g[1], a_p, k_wa_g[0], k_wa_g[1], a_w, oran_gecis,
                 ", ".join(geometrik)))
    kontrol("CTA-A6-GECIS-ORAN", oran_gecis >= ORAN_TABANI,
            "sinif takasinin ILK karesinde de odeme/WhatsApp alan orani %.2f >= %.2f "
            "(%s) — gorunmeyen sekmede bu kare KALICIDIR"
            % (oran_gecis, ORAN_TABANI,
               "gecis penceresi yok" if not geometrik
               else "anime edilen geometri: " + ", ".join(geometrik)))

    kucuk = [(a, h) for a, h in (("sepet odeme", k_pay[1]),
                                 ("sepet WhatsApp", k_wa[1]),
                                 ("sepet odeme (gecis)", k_pay_g[1]),
                                 ("sepet WhatsApp (gecis)", k_wa_g[1]),
                                 ("ana sayfa bant WhatsApp", k_bant[1]))
             if h < DOKUNMA_TABANI]
    kontrol("CTA-A4-DOKUNMA-44", not kucuk,
            "sepet/ana sayfa dokunma hedefleri >= %d px (%s)"
            % (DOKUNMA_TABANI,
               "hepsi" if not kucuk else "ihlal: " + ", ".join(
                   "%s=%.1f" % (a, h) for a, h in kucuk)))
    kanal = (wa_no in metin) and ("wa.me/" in metin) and bool(wa_metni.strip())
    kontrol("CTA-A5-KANAL-WA", kanal,
            "sepet panelinde WhatsApp CTA'si ve numara YERINDE (%r)" % wa_metni)
    return pay


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=ROOT,
                    help="olculecek agacin koku (mutasyon bataryasi KOPYAYI verir)")
    a = ap.parse_args()
    kok = os.path.abspath(a.kok)
    print("=" * 78)
    print("CTA DENGE KAPISI — kok: %s" % kok)
    print("=" * 78)

    build, hata = build_yukle(kok)
    if build is None:
        olculemedi(hata)
        print("\nSONUC: OLCULEMEDI ⚠️  (%d sebep)" % len(OLCULEMEDI))
        return olculemedi_kodu()
    wa_no = getattr(build, "WHATSAPP", None)
    if not wa_no:
        olculemedi("build.WHATSAPP sabiti yok — kanal nobeti kurulamadi")
        print("\nSONUC: OLCULEMEDI ⚠️  (%d sebep)" % len(OLCULEMEDI))
        return olculemedi_kodu()
    kurallar = css_kurallari(getattr(build, "PAGE_CSS", "") or "")
    if not kurallar:
        olculemedi("build.PAGE_CSS ayristirilamadi/bos")
        print("\nSONUC: OLCULEMEDI ⚠️  (%d sebep)" % len(OLCULEMEDI))
        return olculemedi_kodu()
    try:
        sayfa = build.render_product(dict(SENTETIK), [dict(SENTETIK)], None)
    except Exception as e:                                   # noqa: BLE001
        olculemedi("sentetik urun sayfasi uretilemedi: %s" % e)
        print("\nSONUC: OLCULEMEDI ⚠️  (%d sebep)" % len(OLCULEMEDI))
        return olculemedi_kodu()

    urun = bolum_urun(kurallar, sayfa, wa_no)
    sepet = bolum_sepet(kok, wa_no)
    if urun is None or sepet is None:
        print("\nSONUC: OLCULEMEDI ⚠️  (%d sebep)" % len(OLCULEMEDI))
        return olculemedi_kodu()
    oranlar, bant_payi = urun
    bant_payi["ana"] = sepet
    tasan = {a: p for a, p in bant_payi.items() if p >= BANT_PAY_TAVANI}
    kontrol("CTA-A2-BANT-PAYI", not tasan,
            "sticky WhatsApp bandinin %dx%d ekran payi < %%%d (urun %%%.1f · ana %%%.1f)"
            % (MOBIL_EN, MOBIL_BOY, 100 * BANT_PAY_TAVANI,
               100 * bant_payi["urun"], 100 * bant_payi["ana"]))

    print("-" * 78)
    print("ORAN=%.2f  BANT_URUN=%.3f  BANT_ANA=%.3f"
          % (min(oranlar.values()), bant_payi["urun"], bant_payi["ana"]))
    if OLCULEMEDI:
        print("SONUC: OLCULEMEDI ⚠️  (%d sebep)" % len(OLCULEMEDI))
        return olculemedi_kodu()
    if HATALAR:
        print("SONUC: KIRMIZI ❌")
        for h in HATALAR:
            print("   · " + h)
        return KIRMIZI
    print("SONUC: YESIL ✅ — Sepete Ekle WhatsApp'i geciyor, bant payi tavanin altinda, "
          "WhatsApp kanali yerinde.")
    return YESIL


if __name__ == "__main__":
    sys.exit(main())

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

NE OLCER (dort bagimsiz eksen + kanal nobeti)
---------------------------------------------
  CTA-A1-ORAN        : alan(Sepete Ekle) / alan(en buyuk WhatsApp CTA'si) >= 1,0
                       MOBIL (375) ve MASAUSTU (1100) genisliklerinde AYRI AYRI.
  CTA-A2-BANT-PAYI   : sticky WhatsApp bandinin 812 px'lik mobil ekrandaki payi < %10.
                       Hem urun sayfasi (tools/build.py::PAGE_CSS) hem ana/sepet
                       sayfasi (index.html) icin ayri olculur.
  CTA-A3-SEPET-SIRA  : sepet panelinde birincil odeme CTA'si WhatsApp CTA'sindan
                       BELGE SIRASINDA once ve alan olarak BUYUK.
  CTA-A4-DOKUNMA-44  : olculen her CTA'nin yuksekligi >= 44 px (WhatsApp kuculurken de).
  CTA-A5-KANAL-WA    : `wa.me` baglantilari + numara YERINDE, sepet butonu ETIKETLI.

GEOMETRI NEREDEN TURER (elle defter YOK)
----------------------------------------
CSS: `build.PAGE_CSS` (urun sayfasinin TEK stil kaynagi) ve index.html'in <style>
blogu GERCEK bir mini-cascade ile ayristirilir (@media max-width bloklari dahil).
HTML: urun sayfasi `build.render_product()` ile SENTETIK bir fikstur urununden
GERCEKTEN uretilir; sepet paneli index.html'den okunur. Ikinci kopya tutulmaz.

Metin genisligi bir MODELDIR: `karakter * font-size * 0,55`. Model iki tarafa da AYNI
uygulanir, yani A1 bir ORAN iddiasidir ve modelin sabitine karsi dayaniklidir. A2/A4
ise yapisal (padding + min-height + kenarlik) olculerdir, metin modeline BAGLI DEGIL.

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
VARSAYILAN_SATIR_YUKSEKLIGI = 1.5   # body{line-height:1.5}
VARSAYILAN_FONT = 16.0

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


def olc_kutu(d, metin, ikon_px):
    """Bir buton/link kutusunun (genislik, yukseklik) olcusu. Cozulemezse None."""
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
        lh = VARSAYILAN_SATIR_YUKSEKLIGI
    kb = _kenarlik(d)
    bosluk = _px(d.get("gap"), 0.0) or 0.0
    icerik_h = max(fs * lh, ikon_px or 0.0)
    h = dolgu[0] + dolgu[2] + 2 * kb + icerik_h
    sabit_h = _px(d.get("height"))
    if sabit_h is not None:
        h = sabit_h
    en_az_h = _px(d.get("min-height"))
    if en_az_h is not None:
        h = max(h, en_az_h)
    w = dolgu[1] + dolgu[3] + 2 * kb + len(metin) * fs * KARAKTER_ORANI
    if ikon_px:
        w += ikon_px + bosluk
    sabit_w = _px(d.get("width"))
    if sabit_w is not None:
        w = sabit_w
    en_az_w = _px(d.get("min-width"))
    if en_az_w is not None:
        w = max(w, en_az_w)
    return (w, h)


SPAN = re.compile(r'<span class="([^"]+)">(.*?)</span>', re.S)


def gorunur_metin(kurallar, ic_html, viewport):
    """Bir butonun O VIEWPORT'ta GORUNEN metni: display:none olan span'lar DUSER.
    (Mobilde `.wa-uzun` gizlenir -> WhatsApp butonu daralir; kapi bunu gormezse
    WhatsApp'i oldugundan genis olcer ve oran iddiasi kayar.)"""
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

    oranlar, bant_payi, dokunmalar = {}, {}, []
    for ad, vw in (("mobil", MOBIL_EN), ("masaustu", MASAUSTU_EN)):
        bant_btn_metni = gorunur_metin(kurallar, bant_btn_ham, vw)
        d_sepet = stil(kurallar, sepet_jeton, vw)
        d_wa = stil(kurallar, wa_ikon_jeton, vw)
        k_sepet = olc_kutu(d_sepet, sepet_metni,
                           ikon_olcusu(kurallar, [".ikon-btn"], vw))
        k_wa = olc_kutu(d_wa, "", ikon_olcusu(kurallar, [".ikon-btn"], vw))
        if k_sepet is None or k_wa is None:
            olculemedi("urun sayfasi eylem butonlari olculemedi (%s)" % ad)
            return None
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

    en_dusuk = min(oranlar.values())
    kontrol("CTA-A1-ORAN", en_dusuk >= ORAN_TABANI,
            "Sepete Ekle / WhatsApp alan orani en dusuk %.2f (taban %.2f) "
            "[mobil %.2f · masaustu %.2f]"
            % (en_dusuk, ORAN_TABANI, oranlar["mobil"], oranlar["masaustu"]))
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
    d_pay = stil(kurallar, {".cart-pay-btn"}, MOBIL_EN)
    d_wa = stil(kurallar, {".cart-order-btn", ".cart-order-btn.ikincil"}, MOBIL_EN)
    m = re.search(r'id="cartPay"[^>]*>\s*([^<]*)', metin)
    pay_metni = " ".join((m.group(1) if m else "").split())
    m = re.search(r'id="cartOrder"[^>]*>(.*?)</a>', metin, re.S)
    wa_metni = gorunur_metin(kurallar, m.group(1) if m else "", MOBIL_EN)
    # Panel genisligi sabit degil; tam genislik butonlari ayni kaba oturur ->
    # ORAN icin genislik ortak carpandir, farki YUKSEKLIK ve genislik KISITI yapar.
    k_pay = olc_kutu(d_pay, pay_metni, 0.0)
    k_wa = olc_kutu(d_wa, wa_metni, ikon_olcusu(kurallar, [".cart-order-btn"], MOBIL_EN))
    if k_pay is None or k_wa is None:
        olculemedi("sepet paneli butonlari olculemedi")
        return None
    tam_genislik_pay = (d_pay.get("width") or "").strip() in ("100%", "auto") or \
                       (d_pay.get("display") or "").strip() in ("block", "flex")
    # 🔴 `auto` DARALTMAZ: blok seviyesindeki bir flex kabi `width:auto` ile satiri
    # DOLDURUR (tarayicida olculdu — ikincil WhatsApp yine tam genislikteydi). Kapinin
    # kabul ettigi tek daraltici deger kumesi icerige gore buzusen degerlerdir.
    wa_dar = (d_wa.get("width") or "").strip() in ("fit-content", "max-content",
                                                   "min-content")
    print("     odeme %.0f px yuksek (%r) · WhatsApp %.0f px yuksek (%r) · "
          "WhatsApp dar mi: %s" % (k_pay[1], pay_metni, k_wa[1], wa_metni, wa_dar))
    kontrol("CTA-A3-SEPET-SIRA",
            i_pay < i_wa and k_pay[1] > k_wa[1] and tam_genislik_pay and wa_dar,
            "birincil odeme CTA'si WhatsApp'tan ONCE (%d < %d), DAHA YUKSEK "
            "(%.1f > %.1f) ve tam genislikte; WhatsApp ikincil/dar"
            % (i_pay, i_wa, k_pay[1], k_wa[1]))
    kucuk = [(a, h) for a, h in (("sepet odeme", k_pay[1]),
                                 ("sepet WhatsApp", k_wa[1]),
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

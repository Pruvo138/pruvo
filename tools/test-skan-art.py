#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKAN ART KABUL TESTI — gizli dekor alt-serisi kategorisi + ana sayfa banner'i.

"Skan Art" (Okan, 23 Tem) = Iskandinav tasarim dilli dekor/heykel alt-serisi. Kategori
davranisi sari seri ("Jeneratör") ile BIREBIR ayni sinif: ana nav'da GIZLI, ana sayfaya
kendi BANNER'iyle girilir, ?kategori= derin linki/arama/urun sayfasi calisir.

Bu dosya o kararin KALICI NOBETCISI. Olctugu maddeler (spec: tools/paket-skan-art-kategori.md):
  (a) "Skan Art" gizli-kategori listesinin HER IKI kaynaginda (tools/build.py NAV_GIZLI +
      index.html GIZLI_KATEGORILER) ve AYNI sira indeksinde.
  (b) GORUNUR CATEGORIES'te DEGIL -> nav cipi basilmaz (renderCats yalniz CATEGORIES'i
      cizer), ama applyUrlParams beyaz listesi gizli listeyi de kapsar -> derin link calisir.
  (c) FONKSIYONEL_KATEGORILER'de (tools/build.py + secenekler.js IKISINDE, ayni icerik).
      Bu liste ciftinin paritesini olcen BASKA test YOK -> nobet burada.
  (d) Kurt urununun URETILEN sayfasi kompakt kart isaretlerini tasiyor, eski genis-buton
      fallback'ini TASIMIYOR (render_product dogrudan cagrilir; urun/ ciktisina muhtac degil).
  (e) Kurt urununun kategorisi "Skan Art" VE urunun kategori disi govdesi degismemis
      (alan kumesi + govde SHA256 capasi -> baslik/fiyat/gorsel/konfigur sessizce oynatilamaz).
  (f) Ana sayfada Skan Art banner'i var: <main> icinde, hedefi /?kategori=Skan%20Art,
      renderGrid goster/gizle listesinde kayitli ve banner HTML+CSS'inde SARI TOKEN YOK
      (sari yalniz parametrik seride — CLAUDE.md).
  (g) Merchant feed taksonomisi: GOOGLE_PRODUCT_CATEGORY'de "Skan Art" var (yoksa
      g:google_product_category satiri feed'e SESSIZCE hic yazilmaz).
  (h) Filament tavsiyesi: filamentler.json kategoriTavsiye'de "Skan Art" var ve uretilen
      sayfada "Tavsiyemiz" rozeti duruyor (yoksa rozet SESSIZCE duserdi).
  (i) Iki kelimeli kategori adi URL'e YUZDE-KODLU giriyor: ne gorunur breadcrumb href'inde
      ne JSON-LD BreadcrumbList item'inde HAM BOSLUK var (bosluk sorgu dizesinde gecersiz).

Offline (ag yok), repo dosyasina YAZMAZ, node gerektirmez. build.py'den ONCE kosabilir.
Kullanim:  python3 tools/test-skan-art.py     (0 = gecti, 1 = kirmizi)
"""
import hashlib
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build  # noqa: E402
import filament_ortak  # noqa: E402

KATEGORI = "Skan Art"
PID = "kurt-heykeli-serit-dekoratif-figur"
# (e) capasi: kurt kaydinin KATEGORI DISI govdesinin SHA256'si (json, sort_keys, ayirici ",:").
# 23 Tem, kategori tasinmasi aninda olculdu. Bu capa bilerek degistirilecekse (or. fiyat
# guncellenirse) yeni deger duzelt.py cikisiyla birlikte BURAYA yazilir — sessiz oynama olmaz.
KURT_GOVDE_SHA256 = "5a77966f32e373f52504c1cbfb587de21c03910d1791fd8d7a9d408e5b6b3f89"
KURT_ALANLAR = {"aciklama", "baslik", "fiyat", "gorseller", "id", "kategori", "konfigur", "marka"}

INDEX = os.path.join(ROOT, "index.html")
SECENEKLER = os.path.join(ROOT, "secenekler.js")
FILAMENTLER = os.path.join(TOOLS, "filamentler.json")
URUNLER = os.path.join(ROOT, "urunler.json")

HATALAR = []


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def js_liste(metin, desen, etiket):
    """JS/Python kaynagindaki tek satirlik dizi literalini JSON olarak ayristir."""
    m = re.search(desen, metin, re.M)
    if not m:
        HATALAR.append("%s bulunamadi (yapi degisti mi?)" % etiket)
        return None
    try:
        return json.loads("[" + m.group(1) + "]")
    except json.JSONDecodeError as e:
        HATALAR.append("%s ayristirilamadi: %s" % (etiket, e))
        return None


# ---------------------------------------------------------------- sari tarayici
SARI_KELIME = re.compile(r"yellow|gold(?:en)?|amber|sar[ıi]\b", re.I)
HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")


def _hue_sat(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0.0, 0.0
    d = mx - mn
    if mx == r:
        h = (60 * ((g - b) / d)) % 360
    elif mx == g:
        h = 60 * ((b - r) / d) + 120
    else:
        h = 60 * ((r - g) / d) + 240
    return h, d / float(mx)


YORUM = re.compile(r"/\*.*?\*/|<!--.*?-->", re.S)


def sari_bulgular(parca):
    """Metin parcasindaki SARI izlerini dondur: sari-tonlu hex + sari kelimesi.

    YORUMLAR once elenir: CSS/HTML yorumu boyanmaz — "SARI KESINLIKLE YOK" gibi bir
    KURAL notunun testi kirmiziya cekmesi sahte pozitif olurdu."""
    parca = YORUM.sub(" ", parca)
    bulgu = []
    for m in HEX.finditer(parca):
        ham = m.group(1)
        if len(ham) == 3:
            ham = "".join(c * 2 for c in ham)
        r, g, b = (int(ham[i:i + 2], 16) for i in (0, 2, 4))
        h, s = _hue_sat(r, g, b)
        # sari kusagi: hue 40-70 derece + doygunluk yuksek + koyu degil
        if 40 <= h <= 70 and s >= 0.35 and max(r, g, b) >= 120:
            bulgu.append("#" + ham)
    for m in SARI_KELIME.finditer(parca):
        bulgu.append(m.group(0))
    return bulgu


# ================================================================== okumalar
index_html = oku(INDEX)
secenekler_js = oku(SECENEKLER)

print("SKAN ART KABUL TESTI")
print("=" * 70)

# ---------------------------------------------------------------- (a) gizli liste paritesi
print("(a) gizli kategori listesi — iki kaynak, ayni sira")
i_giz = js_liste(index_html, r"var\s+GIZLI_KATEGORILER\s*=\s*\[(.*?)\]", "index.html GIZLI_KATEGORILER")
b_giz = list(build.NAV_GIZLI)
kontrol(i_giz is not None and i_giz == b_giz,
        "index.html GIZLI_KATEGORILER == tools/build.py NAV_GIZLI (%s / %s)" % (i_giz, b_giz))
kontrol(KATEGORI in b_giz, '"%s" tools/build.py NAV_GIZLI icinde' % KATEGORI)
kontrol(i_giz is not None and KATEGORI in i_giz, '"%s" index.html GIZLI_KATEGORILER icinde' % KATEGORI)
if i_giz and KATEGORI in i_giz and KATEGORI in b_giz:
    kontrol(i_giz.index(KATEGORI) == b_giz.index(KATEGORI),
            "sira indeksi iki kaynakta ayni (%d)" % b_giz.index(KATEGORI))

# ---------------------------------------------------------------- (b) nav'da gizli + derin link
print("(b) nav cipi YOK, derin link VAR")
i_cat = js_liste(index_html, r"var\s+CATEGORIES\s*=\s*\[(.*?)\]", "index.html CATEGORIES")
kontrol(i_cat is not None and KATEGORI not in i_cat,
        '"%s" GORUNUR index.html CATEGORIES listesinde DEGIL (nav cipi basilmaz)' % KATEGORI)
kontrol(KATEGORI not in build.CATEGORIES,
        '"%s" GORUNUR tools/build.py CATEGORIES listesinde DEGIL' % KATEGORI)
# renderCats cip kaynagini genisletirse gizli kategori nav'da GORUNUR hale gelir -> nobet
m_cats = re.search(r"function\s+renderCats\s*\(\)\s*\{(.*?)\n  \}", index_html, re.S)
kontrol(m_cats is not None and "GIZLI_KATEGORILER" not in m_cats.group(1),
        "renderCats() gizli listeyi cip kaynagina KATMIYOR")
kontrol('.concat(CATEGORIES).concat(GIZLI_KATEGORILER)' in index_html,
        "applyUrlParams beyaz listesi CATEGORIES + GIZLI_KATEGORILER (derin link calisir)")

# ---------------------------------------------------------------- (c) FONKSIYONEL parite
print("(c) FONKSIYONEL_KATEGORILER — build.py + secenekler.js")
s_fonk = js_liste(secenekler_js, r"var\s+FONKSIYONEL_KATEGORILER\s*=\s*\[(.*?)\]",
                  "secenekler.js FONKSIYONEL_KATEGORILER")
b_fonk = list(build.FONKSIYONEL_KATEGORILER)
kontrol(KATEGORI in b_fonk, '"%s" tools/build.py FONKSIYONEL_KATEGORILER icinde' % KATEGORI)
kontrol(s_fonk is not None and KATEGORI in s_fonk,
        '"%s" secenekler.js FONKSIYONEL_KATEGORILER icinde' % KATEGORI)
kontrol(s_fonk is not None and s_fonk == b_fonk,
        "iki FONKSIYONEL_KATEGORILER kopyasi BIREBIR ayni (bu paritenin baska nobetcisi yok)")

# ---------------------------------------------------------------- (e) urun kaydi
print("(e) kurt urunu — kategori tasindi, govde degismedi")
with open(URUNLER, encoding="utf-8") as f:
    katalog = json.load(f)
kurtlar = [u for u in katalog if u.get("id") == PID]
kontrol(len(kurtlar) == 1, "%s katalogda TEK kayit" % PID)
if not kurtlar:
    print("SONUC: KALDI ❌ (urun bulunamadi, kalan maddeler olculemedi)")
    sys.exit(1)
kurt = kurtlar[0]
kontrol(kurt.get("kategori") == KATEGORI, 'kategori == "%s" (bulunan: %r)' % (KATEGORI, kurt.get("kategori")))
kontrol(set(kurt.keys()) == KURT_ALANLAR,
        "alan kumesi degismemis (%s)" % sorted(kurt.keys()))
govde = {k: v for k, v in kurt.items() if k != "kategori"}
ham = json.dumps(govde, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
sha = hashlib.sha256(ham.encode("utf-8")).hexdigest()
kontrol(sha == KURT_GOVDE_SHA256,
        "kategori disi govde SHA256 capasi tutuyor (%s)" % sha[:16])

# ---------------------------------------------------------------- (d) uretilen sayfa
print("(d) uretilen urun sayfasi — kompakt kart, genis-buton fallback YOK")
html = build.render_product(kurt, katalog)
KOMPAKT = ['class="eylem-ikonlar"', 'ikon-btn ikon-sepet', 'ikon-btn ikon-wa', 'opsiyon-adet-eylem']
for isaret in KOMPAKT:
    kontrol(html.count(isaret) == 1, "kompakt kart isareti VAR: %s" % isaret)
FALLBACK = ['<span class="cart-label">Sepete Ekle</span>', 'class="order-wa"']
for isaret in FALLBACK:
    kontrol(html.count(isaret) == 0, "eski genis-buton isareti YOK: %s" % isaret)

# ---------------------------------------------------------------- (h) filament tavsiyesi
print("(h) filament tavsiyesi — kategori haritasi + sayfadaki rozet")
with open(FILAMENTLER, encoding="utf-8") as f:
    filref = json.load(f)
kontrol(KATEGORI in filref.get("kategoriTavsiye", {}),
        'filamentler.json kategoriTavsiye["%s"] tanimli' % KATEGORI)
kontrol(bool(filament_ortak.tavsiyeler(KATEGORI)),
        "filament_ortak.tavsiyeler(%r) bos DEGIL -> %r" % (KATEGORI, filament_ortak.tavsiyeler(KATEGORI)))
kontrol("fil-cip tavsiyeli" in html, 'urun sayfasinda "Tavsiyemiz" rozetli filament cipi var')

# ---------------------------------------------------------------- (i) URL kodlamasi
print("(i) iki kelimeli kategori adi URL'de yuzde-kodlu")
kontrol("?kategori=" + KATEGORI not in html,
        "sayfada HAM BOSLUKLU '?kategori=%s' URL'i YOK" % KATEGORI)
kontrol("?kategori=Skan%20Art" in html, "yuzde-kodlu '?kategori=Skan%20Art' URL'i VAR")
ld_bloklar = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
bread = None
for blok in ld_bloklar:
    obj = json.loads(blok)
    if obj.get("@type") == "BreadcrumbList":
        bread = obj
kontrol(bread is not None, "JSON-LD BreadcrumbList ayristirilabildi")
if bread:
    item = [x for x in bread["itemListElement"] if x.get("position") == 2][0]
    kontrol(" " not in item["item"], "BreadcrumbList item URL'inde ham bosluk YOK: %s" % item["item"])
    kontrol(item.get("name") == KATEGORI, 'BreadcrumbList adi "%s"' % KATEGORI)

# ---------------------------------------------------------------- (g) merchant feed
print("(g) Merchant feed taksonomisi")
kontrol(KATEGORI in build.GOOGLE_PRODUCT_CATEGORY,
        'GOOGLE_PRODUCT_CATEGORY["%s"] tanimli -> %r'
        % (KATEGORI, build.GOOGLE_PRODUCT_CATEGORY.get(KATEGORI)))
feed_xml, feed_adet = build.render_merchant_feed([kurt])
kontrol(feed_adet == 1, "kurt urunu feed'e giriyor (fiyatli + gorselli + parametrik degil)")
kontrol("<g:google_product_category>Home &amp; Garden &gt; Decor</g:google_product_category>" in feed_xml,
        "feed satirinda g:google_product_category basiliyor")
kontrol("<g:product_type>%s</g:product_type>" % KATEGORI in feed_xml,
        "feed g:product_type == %s" % KATEGORI)

# ---------------------------------------------------------------- (f) ana sayfa banner
print("(f) ana sayfa Skan Art banner'i")
m_ban = re.search(r'<a id="skanBanner"[^>]*>.*?</a>', index_html, re.S)
kontrol(m_ban is not None, 'index.html icinde <a id="skanBanner"> blogu var')
banner_html = m_ban.group(0) if m_ban else ""
kontrol('href="/?kategori=Skan%20Art"' in banner_html,
        'banner hedefi href="/?kategori=Skan%20Art"')
m_main = re.search(r"<main>(.*?)</main>", index_html, re.S)
kontrol(m_main is not None and 'id="skanBanner"' in m_main.group(1),
        "banner <main> icinde (ana sayfa vitrininin ustunde)")
# goster/gizle kablolamasi: renderGrid'in banner listesinde kayitli mi
m_tog = re.search(r'\[\s*"jenBanner"\s*,\s*"skanBanner"\s*\]\s*\.forEach', index_html)
kontrol(m_tog is not None,
        "renderGrid goster/gizle listesinde skanBanner kayitli "
        "(kategori/arama gorunumunde banner gizlenir)")
kontrol("if(bEl)" in index_html or "if (bEl)" in index_html,
        "banner toggle NULL-GUARD'li (id kayarsa renderGrid dusmez, grid kaybolmaz)")
# SARI TARAMASI: banner HTML + banner CSS blogu
css_bas = index_html.find("/* ---------- SKAN ART BANNER")
css_son = index_html.find(".brand-row{", css_bas) if css_bas != -1 else -1
kontrol(css_bas != -1 and css_son != -1, "Skan Art banner CSS blogu bulundu")
banner_css = index_html[css_bas:css_son] if (css_bas != -1 and css_son != -1) else ""
bulgu = sari_bulgular(banner_html) + sari_bulgular(banner_css)
kontrol(not bulgu, "banner HTML+CSS'inde SARI token YOK (bulunan: %s)" % (bulgu or "-"))
kontrol("var(--red)" in banner_css, "banner marka paletini kullaniyor (kirmizi aksan var(--red))")

# ================================================================== sonuc
print("=" * 70)
if HATALAR:
    print("SONUC: %d KIRMIZI ❌" % len(HATALAR))
    for h in HATALAR:
        print("  - " + h)
    sys.exit(1)
print("SONUC: GECTI ✅ (Skan Art kategorisi + banner + kurt urunu kabul kriterleri saglandi)")
sys.exit(0)

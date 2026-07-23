#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKAN ART KABUL TESTI — gizli dekor alt-serisi kategorisi + ana sayfa banner'i.

"Skan Art" (Okan, 23 Tem) = Iskandinav tasarim dilli dekor/heykel alt-serisi. Kategori
davranisi sari seri ("Jeneratör") ile BIREBIR ayni sinif: ana nav'da GIZLI, ana sayfaya
kendi BANNER'iyle girilir, ?kategori= derin linki/arama/urun sayfasi calisir.

Bu dosya o kararin KALICI NOBETCISI. Olctugu maddeler (spec: tools/paket-skan-art-kategori.md):
  (a) "Skan Art" gizli-kategori listesinin HER IKI kaynaginda (tools/build.py NAV_GIZLI +
      index.html GIZLI_KATEGORILER) ve AYNI sira indeksinde.
  (b) NAV CIPI YOK + DERIN LINK VAR — kaynak-metni degil DAVRANIS olculur: renderCats()
      ve applyUrlParams() index.html'den AYIKLANIP node ile GERCEKTEN kosturulur
      (sahte DOM/location). Cip listesi ["Tümü"]+CATEGORIES'ten SAPARSA ve
      ?kategori=Skan%20Art activeCat'i SET ETMEZSE kirmizi.
      [23 Tem curutme: eski surum yalniz "GIZLI_KATEGORILER tanimlayicisi renderCats
      govdesinde gecmesin" diyordu -> nav'a duz literal ("Skan Art") eklemek KACAKTI;
      derin link kontrolu de DOSYA GENELINDE alt-dize ariyordu -> applyUrlParams beyaz
      listesi daraltilip eski ifade YORUMDA birakilinca KACAKTI.]
  (c) FONKSIYONEL_KATEGORILER'de (tools/build.py + secenekler.js IKISINDE, ayni icerik)
      VE secenekler.js'in KENDI davranisi node ile olculur: fonksiyonelMi("Skan Art")
      true, satirOzeti malzeme/renk/adet satirini ve malzeme KATSAYISINI uyguluyor.
      [Curutme: liste ciftinin literal esitligi, fonksiyonelMi'ye eklenen
      `&& kategori !== "Skan Art"` bypass'ini GORMUYORDU — para etkisi PETG +%30 kaybi.]
  (d) Kompakt kart duzeni IKI ayri fiksturle olculur:
      (d1) kurt urununun URETILEN sayfasi (bugunku gercek kayit — konfigur'lu),
      (d2) SENTETIK semasiz/konfigursuz Skan Art urunu — kompakt duzeni SADECE
           FONKSIYONEL_KATEGORILER uyeligi tasir. [Curutme: kurt konfigur'lu oldugu icin
           (d1) tek basina FONKSIYONEL uyeligini HIC olcmuyor; "Skan Art" listeden
           silinince kurt sayfasi BAYT-OZDES kaliyordu.]
  (e) Kurt urununun kategorisi "Skan Art", govdesi degismemis (SHA256 capasi) VE
      katalogdaki Skan Art urun SAYISI capali. [Curutme: 168 Dekorasyon urununun
      tamami toptan Skan Art'a tasindiginda test yesil kaliyordu.]
  (f) Ana sayfa banner'i: <main> icinde, hedefi /?kategori=Skan%20Art, renderGrid
      goster/gizle KABLOSU DOGRU YONDE (anaGorunum ? "" : "none" — tersi degil),
      banner ailesinin HICBIR CSS kuralinda banner'i olduren bildirim yok
      (display:none / visibility:hidden / opacity:0 / pointer-events:none),
      banner ailesinin TUM CSS kurallarinda (dosya geneli, pencere YOK) SARI TOKEN yok
      (hex + rgb()/rgba() + hsl() + CSS renk adlari cozumlenir) ve banner metni marka
      kurallarina uyuyor ("3D baski" YOK, sehir adi YOK — CLAUDE.md).
      [Curutme: toggle'i tersine cevirmek, .skan-banner'a display:none/pointer-events:none
      vermek, sari override'i tarama penceresinin ALTINA koymak, sariyi rgb() ile yazmak
      ve banner metnine "Fethiye ... 3D baski" yazmak KACAKTI.]
  (g) Merchant feed taksonomisi: GOOGLE_PRODUCT_CATEGORY'de "Skan Art" var (yoksa
      g:google_product_category satiri feed'e SESSIZCE hic yazilmaz).
  (h) Filament tavsiyesi: filamentler.json kategoriTavsiye'de "Skan Art" var ve uretilen
      sayfada "Tavsiyemiz" rozeti duruyor (yoksa rozet SESSIZCE duserdi).
  (i) Iki kelimeli kategori adi URL'e YUZDE-KODLU giriyor: ne gorunur breadcrumb href'inde
      ne JSON-LD BreadcrumbList item'inde HAM BOSLUK var (bosluk sorgu dizesinde gecersiz).
  (j) ILGILI URUNLER bolumu AYAKTA: ince alt-seride (Skan Art'ta bugun TEK urun) ayni
      kategori havuzu bosalinca build.AKRABA_KATEGORI yedegi devreye girer. [Curutme:
      yedek yokken kurt sayfasi 8 ic linkini kaybediyordu (rel-card 8 -> 0) ve 23 CI
      kapisinin HICBIRI kirmiziya dusmuyordu.]

Ag YOK, repo dosyasina YAZMAZ, build.py'den ONCE kosabilir. NODE GEREKIR (davranis
bolumleri) — CI'da setup-node kurulu ve node yoksa test FAIL-CLOSED kirmizi yanar
(marka-liste-test.py / konfigur-test.py deseni). Yerelde node yoksa acik uyariyla
atlamak icin: SKAN_ART_NODE_ATLA=1.
Kullanim:  python3 tools/test-skan-art.py     (0 = gecti, 1 = kirmizi)
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

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
# (e) KAPSAM capasi: katalogda kac urun "Skan Art"ta. Yeni Skan Art urunu eklenince BILEREK
# guncellenir; toptan/kazara kategori tasinmasi (olculen curutme: 168 Dekorasyon urununun
# hepsi birden) bu sayiyi bozar ve kapi kirmizi yanar.
SKAN_ART_URUN_SAYISI = 1

INDEX = os.path.join(ROOT, "index.html")
SECENEKLER = os.path.join(ROOT, "secenekler.js")
FILAMENTLER = os.path.join(TOOLS, "filamentler.json")
URUNLER = os.path.join(ROOT, "urunler.json")

HATALAR = []


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)


def bitir():
    print("=" * 70)
    if HATALAR:
        print("SONUC: %d KIRMIZI ❌" % len(HATALAR))
        for h in HATALAR:
            print("  - " + h)
        sys.exit(1)
    print("SONUC: GECTI ✅ (Skan Art kategorisi + banner + kurt urunu kabul kriterleri saglandi)")
    sys.exit(0)


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


def js_bildirim(metin, desen, etiket):
    """`var X = ...;` bildiriminin TAM kaynak satirini dondur (node harness'ine gomulur)."""
    m = re.search(desen, metin, re.M)
    if not m:
        HATALAR.append("%s bildirimi bulunamadi (yapi degisti mi?)" % etiket)
        return ""
    return m.group(0)


def js_fonksiyon(metin, ad):
    """`function <ad>(...){...}` govdesini SUSLU PARANTEZ SAYARAK ayikla (regex degil:
    ic blok/nesne literali fonksiyonu erken kesmesin)."""
    m = re.search(r"function\s+%s\s*\(" % re.escape(ad), metin)
    if not m:
        HATALAR.append("function %s bulunamadi (yapi degisti mi?)" % ad)
        return ""
    i = metin.find("{", m.end())
    if i == -1:
        HATALAR.append("function %s govdesi acilmiyor" % ad)
        return ""
    derinlik, k = 1, i + 1
    while k < len(metin) and derinlik:
        if metin[k] == "{":
            derinlik += 1
        elif metin[k] == "}":
            derinlik -= 1
        k += 1
    if derinlik:
        HATALAR.append("function %s govdesi kapanmiyor" % ad)
        return ""
    return metin[m.start():k]


# ---------------------------------------------------------------- CSS ayristirici
def css_bloklari(html_metin):
    """index.html'deki TUM <style> bloklarinin govdesini birlestir."""
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html_metin, re.S))


def css_kurallari(css):
    """(secici, bildirimler) ciftleri. @media/@supports gibi sarmalayicilarin ICI de duz
    listeye acilir -> kural dosyanin NERESINDE olursa olsun taranir (pencere YOK)."""
    css = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)

    def _ayikla(blok):
        out, i = [], 0
        while True:
            j = blok.find("{", i)
            if j == -1:
                return out
            sec = blok[i:j].strip()
            derinlik, k = 1, j + 1
            while k < len(blok) and derinlik:
                if blok[k] == "{":
                    derinlik += 1
                elif blok[k] == "}":
                    derinlik -= 1
                k += 1
            govde = blok[j + 1:k - 1]
            if sec.startswith("@"):
                out.extend(_ayikla(govde))
            else:
                out.append((sec, govde))
            i = k

    return _ayikla(css)


# Banner AILESI: banner elemanina ya da cocuklarina dokunan her secici. .jen-banner de
# dahildir — banner o iskeleti YENIDEN KULLANIYOR, orada verilen bir display:none ikisini
# birden oldururdu.
BANNER_SECICI = re.compile(r"(?:\.skan-banner|\.jen-banner|#skanBanner)[\w-]*")

# Banner'i GORUNMEZ/TIKLANAMAZ yapan bildirimler (bosluklar esnek).
OLDUREN_BILDIRIM = [
    (re.compile(r"display\s*:\s*none", re.I), "display:none"),
    (re.compile(r"visibility\s*:\s*(hidden|collapse)", re.I), "visibility:hidden"),
    (re.compile(r"opacity\s*:\s*0(?:\.0+)?\s*(?:;|$|!)", re.I), "opacity:0"),
    (re.compile(r"pointer-events\s*:\s*none", re.I), "pointer-events:none"),
    (re.compile(r"content-visibility\s*:\s*hidden", re.I), "content-visibility:hidden"),
]


def banner_kurallari(css):
    return [(s, d) for (s, d) in css_kurallari(css) if BANNER_SECICI.search(s)]


# ---------------------------------------------------------------- sari tarayici
# Sari/altin ailesinden CSS renk ADLARI (tarayicinin cozdugu isimler; "amber" CSS adi
# degildir ama pazarlama dilinde geciyor, o yuzden kelime taramasinda kalir).
SARI_ADLAR = {
    "yellow": (255, 255, 0), "gold": (255, 215, 0), "goldenrod": (218, 165, 32),
    "darkgoldenrod": (184, 134, 11), "palegoldenrod": (238, 232, 170),
    "khaki": (240, 230, 140), "darkkhaki": (189, 183, 107),
    "lightyellow": (255, 255, 224), "lemonchiffon": (255, 250, 205),
    "cornsilk": (255, 248, 220), "moccasin": (255, 228, 181),
    "papayawhip": (255, 239, 213), "blanchedalmond": (255, 235, 205),
    "navajowhite": (255, 222, 173), "wheat": (245, 222, 179),
    "greenyellow": (173, 255, 47), "yellowgreen": (154, 205, 50),
}
SARI_KELIME = re.compile(r"yellow|gold(?:en)?|amber|sar[ıi]\b", re.I)
HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGB_FN = re.compile(r"\brgba?\(\s*([\d.]+)(%?)[\s,]+([\d.]+)(%?)[\s,]+([\d.]+)(%?)", re.I)
HSL_FN = re.compile(r"\bhsla?\(\s*([\d.]+)(?:deg)?[\s,]+([\d.]+)%[\s,]+([\d.]+)%", re.I)
AD_FN = re.compile(r"\b(%s)\b" % "|".join(sorted(SARI_ADLAR, key=len, reverse=True)), re.I)
YORUM = re.compile(r"/\*.*?\*/|<!--.*?-->", re.S)


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


def _sari_mi(r, g, b):
    """Sari kusagi: hue 40-70 derece + doygunluk yuksek + koyu degil."""
    h, s = _hue_sat(r, g, b)
    return 40 <= h <= 70 and s >= 0.35 and max(r, g, b) >= 120


def _hsl_rgb(h, s, l):
    h = (h % 360) / 360.0
    s, l = s / 100.0, l / 100.0
    if s == 0:
        v = int(round(l * 255))
        return v, v, v
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def kanal(t):
        t = t % 1.0
        if t < 1 / 6.0:
            return p + (q - p) * 6 * t
        if t < 0.5:
            return q
        if t < 2 / 3.0:
            return p + (q - p) * (2 / 3.0 - t) * 6
        return p

    return tuple(int(round(kanal(h + o) * 255)) for o in (1 / 3.0, 0.0, -1 / 3.0))


def sari_bulgular(parca):
    """Metin parcasindaki SARI izleri: hex + rgb()/rgba() + hsl()/hsla() + CSS renk adi
    + sari kelimesi. YORUMLAR once elenir: CSS/HTML yorumu boyanmaz — "SARI KESINLIKLE
    YOK" gibi bir KURAL notunun testi kirmiziya cekmesi sahte pozitif olurdu."""
    parca = YORUM.sub(" ", parca)
    bulgu = []
    for m in HEX.finditer(parca):
        ham = m.group(1)
        if len(ham) == 3:
            ham = "".join(c * 2 for c in ham)
        r, g, b = (int(ham[i:i + 2], 16) for i in (0, 2, 4))
        if _sari_mi(r, g, b):
            bulgu.append("#" + ham)
    for m in RGB_FN.finditer(parca):
        try:
            kanallar = []
            for deger, yuzde in ((m.group(1), m.group(2)), (m.group(3), m.group(4)),
                                 (m.group(5), m.group(6))):
                v = float(deger)
                kanallar.append(v * 2.55 if yuzde else v)
        except ValueError:
            continue
        if _sari_mi(*kanallar):
            bulgu.append(m.group(0) + ")")
    for m in HSL_FN.finditer(parca):
        try:
            rgb = _hsl_rgb(float(m.group(1)), float(m.group(2)), float(m.group(3)))
        except ValueError:
            continue
        if _sari_mi(*rgb):
            bulgu.append(m.group(0) + ")")
    for m in AD_FN.finditer(parca):
        if _sari_mi(*SARI_ADLAR[m.group(1).lower()]):
            bulgu.append(m.group(1))
    for m in SARI_KELIME.finditer(parca):
        bulgu.append(m.group(0))
    # ayni bulgu birden cok tarayicidan gelebilir (gold hem ad hem kelime) -> tekille
    return sorted(set(bulgu))


# ---------------------------------------------------------------- marka/cografya kurali
# CLAUDE.md: pazarlama metninde "3D baski" DENMEZ; sehir adi GORUNUR pazarlamada GECMEZ
# (istisna: JSON-LD addressLocality / yasal kunye — asagida <script> bloklari elenir).
YASAK_IFADE = [
    (re.compile(r"3\s*[dD]\s*bask", re.I), '"3D baskı" (marka dili: "özel tasarım üretim")'),
    (re.compile(r"3\s*[dD]\s*print", re.I), '"3D print"'),
    (re.compile(r"[üu]ç\s*boyutlu\s*bask", re.I), '"üç boyutlu baskı"'),
    (re.compile(r"Fethiye|Göcek|Gocek|Muğla|Mugla|Dalaman", re.I), "şehir/coğrafya adı"),
]


def yasak_ifadeler(parca):
    return [etiket for desen, etiket in YASAK_IFADE if desen.search(parca)]


# ---------------------------------------------------------------- node kosucu
def node_var_mi():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def node_kos(kaynak, etiket):
    """Gecici .js dosyasi yazip node ile kosar; stdout'un SON satirini JSON ayristirir."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(kaynak)
        yol = f.name
    try:
        r = subprocess.run(["node", yol], capture_output=True, text=True)
    finally:
        os.unlink(yol)
    if r.returncode != 0:
        kontrol(False, "%s node ile kosuyor (stderr: %s)"
                % (etiket, (r.stderr.strip()[:300] or "-")))
        return None
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        kontrol(False, "%s node ciktisi JSON degil: %r" % (etiket, r.stdout[:200]))
        return None


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

# ---------------------------------------------------------------- (b) liste uyeligi (on sart)
print("(b) nav cipi YOK, derin link VAR — once liste uyeligi")
i_cat = js_liste(index_html, r"var\s+CATEGORIES\s*=\s*\[(.*?)\]", "index.html CATEGORIES")
kontrol(i_cat is not None and KATEGORI not in i_cat,
        '"%s" GORUNUR index.html CATEGORIES listesinde DEGIL' % KATEGORI)
kontrol(KATEGORI not in build.CATEGORIES,
        '"%s" GORUNUR tools/build.py CATEGORIES listesinde DEGIL' % KATEGORI)

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
print("(e) kurt urunu — kategori tasindi, govde degismedi, KAPSAM tek urun")
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
skan_urunler = [u for u in katalog if u.get("kategori") == KATEGORI]
kontrol(len(skan_urunler) == SKAN_ART_URUN_SAYISI,
        "katalogda %s urun sayisi capasi == %d (bulunan: %d) — toptan kategori tasimasi kapali"
        % (KATEGORI, SKAN_ART_URUN_SAYISI, len(skan_urunler)))

# ---------------------------------------------------------------- (d1) gercek kurt sayfasi
print("(d1) kurt sayfasi (gercek kayit — konfigur'lu) — kompakt kart, genis-buton YOK")
html = build.render_product(kurt, katalog)
KOMPAKT = ['class="eylem-ikonlar"', 'ikon-btn ikon-sepet', 'ikon-btn ikon-wa', 'opsiyon-adet-eylem']
for isaret in KOMPAKT:
    kontrol(html.count(isaret) == 1, "kompakt kart isareti VAR: %s" % isaret)
FALLBACK = ['<span class="cart-label">Sepete Ekle</span>', 'class="order-wa"']
for isaret in FALLBACK:
    kontrol(html.count(isaret) == 0, "eski genis-buton isareti YOK: %s" % isaret)

# ---------------------------------------------------------------- (d2) FONKSIYONEL fiksturu
# ⚠️ NEDEN SENTETIK: bugunku TEK Skan Art urunu (kurt) `konfigur` alanli. build.py'de
# kart_secim = bool(sema) or (fonksiyonel and not parametrik and not konfigur) ve
# `if kart_secim or konfigur:` -> konfigur yolu kompakt duzeni ZATEN veriyor. Yani (d1)
# FONKSIYONEL_KATEGORILER uyeligini HIC olcmuyor (olculdu 23 Tem: "Skan Art" listeden
# silinince kurt sayfasi BAYT-OZDES kaliyor). Spec §1.5'in ASIL riski —"kategori
# FONKSIYONEL'de olmazsa sayfa eski genis-buton fallback'ine duser"— ancak SEMASIZ +
# KONFIGURSUZ bir Skan Art urununde gorunur. Bu fikstur o urunu temsil eder; katalogda
# yasamaz, urunler.json'a DOKUNMAZ.
print("(d2) sentetik semasiz/konfigursuz Skan Art urunu — FONKSIYONEL uyeliginin nobeti")
SENTETIK = {
    "id": "skan-art-fonksiyonel-nobetci-fiksturu",
    "kategori": KATEGORI,
    "marka": [],
    "baslik": "Nöbetçi fikstürü — şemasız Skan Art ürünü",
    "aciklama": "Yalnız kabul testinde yaşar. Yaklaşık dış ölçüler: 100 × 100 × 100 mm.",
    "fiyat": "900 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/nobetci-fikstur-1.jpg"],
}
html_f = build.render_product(SENTETIK, [SENTETIK])
for isaret in KOMPAKT:
    kontrol(html_f.count(isaret) == 1, "sentetik sayfada kompakt isaret VAR: %s" % isaret)
for isaret in FALLBACK:
    kontrol(html_f.count(isaret) == 0, "sentetik sayfada genis-buton isareti YOK: %s" % isaret)
kontrol("var KART_SECIM = true;" in html_f,
        "sentetik sayfada KART_SECIM bayragi ACIK (malzeme karti secimi kablolu)")

# ---------------------------------------------------------------- (j) ilgili urunler
print("(j) ilgili urunler bolumu — ince alt-seride yedek havuz")
kontrol('<section class="related">' in html,
        'kurt sayfasinda <section class="related"> VAR (ic linkler ayakta)')
rel_adet = html.count('class="rel-card"')
kontrol(rel_adet >= build.REL_EN_AZ,
        "kurt sayfasinda rel-card sayisi >= %d (bulunan: %d)" % (build.REL_EN_AZ, rel_adet))
kontrol(build.AKRABA_KATEGORI.get(KATEGORI) == "Dekorasyon",
        'build.AKRABA_KATEGORI["%s"] == "Dekorasyon" (yedek havuz kablolu)' % KATEGORI)

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
print("(f) ana sayfa Skan Art banner'i — varlik, hedef, GORUNURLUK, palet, marka dili")
m_ban = re.search(r'<a id="skanBanner"[^>]*>.*?</a>', index_html, re.S)
kontrol(m_ban is not None, 'index.html icinde <a id="skanBanner"> blogu var')
banner_html = m_ban.group(0) if m_ban else ""
kontrol('href="/?kategori=Skan%20Art"' in banner_html,
        'banner hedefi href="/?kategori=Skan%20Art"')
m_main = re.search(r"<main>(.*?)</main>", index_html, re.S)
kontrol(m_main is not None and 'id="skanBanner"' in m_main.group(1),
        "banner <main> icinde (ana sayfa vitrininin ustunde)")

# --- goster/gizle KABLOSU: hem listede kayitli hem DOGRU YONDE
m_tog = re.search(r'\[\s*"jenBanner"\s*,\s*"skanBanner"\s*\]\s*\.forEach\s*\('
                  r'function\s*\(\s*\w+\s*\)\s*\{(.*?)\}\s*\)\s*;', index_html, re.S)
kontrol(m_tog is not None,
        "renderGrid goster/gizle listesinde skanBanner kayitli "
        "(kategori/arama gorunumunde banner gizlenir)")
tog_govde = m_tog.group(1) if m_tog else ""
kontrol(re.search(r'style\.display\s*=\s*anaGorunum\s*\?\s*""\s*:\s*"none"', tog_govde) is not None,
        'toggle YONU dogru: display = anaGorunum ? "" : "none" '
        "(tersi banner'i ana sayfada GIZLER, kategori gorunumunde gosterirdi)")
kontrol("if(bEl)" in tog_govde or "if (bEl)" in tog_govde,
        "banner toggle NULL-GUARD'li (id kayarsa renderGrid dusmez, grid kaybolmaz)")

# --- CSS: banner ailesinin TUM kurallari (dosya geneli — pencere YOK)
css_hepsi = css_bloklari(index_html)
b_kurallar = banner_kurallari(css_hepsi)
kontrol(len(b_kurallar) >= 6,
        "banner ailesi CSS kurallari bulundu (%d kural: %s)"
        % (len(b_kurallar), ", ".join(s for s, _ in b_kurallar[:4]) + " ..."))
kontrol(any(".skan-banner" in s for s, _ in b_kurallar),
        "kurallar arasinda .skan-banner secicisi var (blok tumden silinmemis)")

olduren = []
for sec, bildirimler in b_kurallar:
    for desen, ad in OLDUREN_BILDIRIM:
        if desen.search(bildirimler):
            olduren.append("%s { %s }" % (sec, ad))
kontrol(not olduren,
        "banner CSS'inde GORUNURLUGU olduren bildirim YOK (bulunan: %s)" % (olduren or "-"))
# inline stil / hidden ozniteligi ile de oldurulebilir
inline_olduren = [ad for desen, ad in OLDUREN_BILDIRIM if desen.search(banner_html)]
if re.search(r"<a id=\"skanBanner\"[^>]*\shidden(?:\s|>|=)", banner_html):
    inline_olduren.append("hidden ozniteligi")
if re.search(r'aria-hidden\s*=\s*"true"', banner_html):
    inline_olduren.append('aria-hidden="true"')
kontrol(not inline_olduren,
        "banner HTML'inde gizleyen inline stil/oznitelik YOK (bulunan: %s)" % (inline_olduren or "-"))

# --- SARI TARAMASI: banner HTML + banner ailesinin TUM CSS kurallari
bulgu = sari_bulgular(banner_html)
for sec, bildirimler in b_kurallar:
    for b in sari_bulgular(bildirimler):
        bulgu.append("%s -> %s" % (sec, b))
kontrol(not bulgu, "banner HTML + banner ailesi CSS'inde SARI token YOK (bulunan: %s)"
        % (sorted(set(bulgu)) or "-"))
kontrol(any("var(--red)" in d for s, d in b_kurallar if ".skan-banner" in s),
        "banner marka paletini kullaniyor (kirmizi aksan var(--red))")

# --- MARKA/COGRAFYA DILI: banner metni + ana sayfanin GORUNUR pazarlama govdesi
kontrol(not yasak_ifadeler(banner_html),
        "banner metninde yasak ifade YOK (bulunan: %s)" % (yasak_ifadeler(banner_html) or "-"))
main_govde = m_main.group(1) if m_main else ""
main_gorunur = re.sub(r"<script[^>]*>.*?</script>|<style[^>]*>.*?</style>", " ",
                      main_govde, flags=re.S)
main_yasak = yasak_ifadeler(main_gorunur)
kontrol(not main_yasak,
        "ana sayfanin GORUNUR <main> govdesinde yasak ifade YOK "
        "(JSON-LD/script haric — bulunan: %s)" % (main_yasak or "-"))

# ================================================================== DAVRANIS (node)
print("(b/c) DAVRANIS bolumu — index.html + secenekler.js node ile GERCEKTEN kosuyor")
if not node_var_mi():
    if os.environ.get("GITHUB_ACTIONS"):
        kontrol(False, "CI'da node var (FAIL-CLOSED: setup-node eksik/bozuk)")
        bitir()
    if os.environ.get("SKAN_ART_NODE_ATLA") == "1":
        print("UYARI: node yok + SKAN_ART_NODE_ATLA=1 → davranis bolumu ACIK uyariyla atlandi "
              "(yalniz kaynak/uretim kontrolleri kostu).")
        bitir()
    kontrol(False, "node bulundu (yerelde kur ya da SKAN_ART_NODE_ATLA=1 ile acik uyariyla atla)")
    bitir()

cat_src = js_bildirim(index_html, r"^\s*var\s+CATEGORIES\s*=.*$", "index.html CATEGORIES")
giz_src = js_bildirim(index_html, r"^\s*var\s+GIZLI_KATEGORILER\s*=.*$", "index.html GIZLI_KATEGORILER")
rendercats_src = js_fonksiyon(index_html, "renderCats")
applyurl_src = js_fonksiyon(index_html, "applyUrlParams")

# --- (b1) renderCats: cip listesi GERCEKTEN ne uretiyor
IKON = "<EV-IKONU>"
b1 = r"""
"use strict";
__CAT__
__GIZ__
var activeCat = "Tümü";
var cips = [];
var document = {
  getElementById: function(){
    return { set innerHTML(v){}, appendChild: function(b){ cips.push(b.__etiket); } };
  },
  createElement: function(){
    var o = { style:{}, className:"", title:"", __etiket:null, setAttribute:function(){} };
    Object.defineProperty(o, "textContent", {
      set: function(v){ o.__etiket = v; }, get: function(){ return o.__etiket; } });
    Object.defineProperty(o, "innerHTML", {
      set: function(v){ o.__etiket = "__IKON__"; }, get: function(){ return ""; } });
    return o;
  }
};
__RENDERCATS__
renderCats();
console.log(JSON.stringify({ cips: cips, cat: CATEGORIES, gizli: GIZLI_KATEGORILER }));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src) \
   .replace("__RENDERCATS__", rendercats_src).replace("__IKON__", IKON)

s1 = node_kos(b1, "(b1) renderCats") if rendercats_src else None
if s1:
    cips = s1["cips"]
    beklenen = [IKON] + s1["cat"]
    kontrol(cips == beklenen,
            "renderCats() cip listesi TAM olarak ev-ikonu + CATEGORIES (%d cip; fazlalik: %s)"
            % (len(cips), [c for c in cips if c not in beklenen] or "-"))
    sizanlar = [g for g in s1["gizli"] if g in cips]
    kontrol(not sizanlar,
            "GIZLI kategorilerin HICBIRI nav cipi olarak basilmiyor (sizan: %s)" % (sizanlar or "-"))
    kontrol(KATEGORI not in cips, '"%s" nav cipi olarak basilmiyor' % KATEGORI)

# --- (b2) applyUrlParams: derin link GERCEKTEN activeCat'i set ediyor mu
b2 = r"""
"use strict";
__CAT__
__GIZ__
var activeCat, activeBrand, query;
var searchEl = { value: "" };
var clearEl = { className: "" };
function markaKatla(x){ return x; }
var location = { hash: "", search: "", replace: function(){ throw new Error("beklenmedik yonlendirme"); } };
__APPLYURL__
function dene(qs){
  activeCat = "Tümü"; activeBrand = "Tümü"; query = "";
  location.hash = ""; location.search = qs;
  applyUrlParams();
  return activeCat;
}
console.log(JSON.stringify({
  skan: dene("?kategori=Skan%20Art"),
  jen: dene("?kategori=Jenerat%C3%B6r"),
  dekor: dene("?kategori=Dekorasyon"),
  uydurma: dene("?kategori=BoyleBirKategoriYok")
}));
""".replace("__CAT__", cat_src).replace("__GIZ__", giz_src).replace("__APPLYURL__", applyurl_src)

s2 = node_kos(b2, "(b2) applyUrlParams") if applyurl_src else None
if s2:
    kontrol(s2["skan"] == KATEGORI,
            '?kategori=Skan%%20Art derin linki activeCat\'i "%s" yapiyor (bulunan: %r) '
            "— banner tiklamasinin TEK girisi" % (KATEGORI, s2["skan"]))
    kontrol(s2["jen"] == "Jeneratör", "?kategori=Jeneratör derin linki calismaya devam ediyor")
    kontrol(s2["dekor"] == "Dekorasyon", "gorunur kategori derin linki calisiyor (Dekorasyon)")
    kontrol(s2["uydurma"] == "Tümü",
            "tanimsiz kategori derin linki YOK SAYILIYOR (beyaz liste hala yuk tasiyor)")

# --- (c2) secenekler.js davranisi: fonksiyonelMi + satirOzeti (para etkisi)
b3 = r"""
"use strict";
require(__SECENEKLER__);
var S = globalThis.PRUVO_SECENEK;
var urun = { id: "x", kategori: "Skan Art", fiyat: "1.000 TL" };
var satir = { id: "x", malzeme: "PETG", renk: "Siyah", renk_ozel: "", boy_etiket: null, adet: 2 };
var ozet = S.satirOzeti(urun, satir);
console.log(JSON.stringify({
  fonk: S.fonksiyonelMi("Skan Art"),
  fonkDekor: S.fonksiyonelMi("Dekorasyon"),
  fonkYok: S.fonksiyonelMi("BoyleBirKategoriYok"),
  detay: ozet.detay,
  kurus: ozet.kurus
}));
""".replace("__SECENEKLER__", json.dumps(SECENEKLER))

s3 = node_kos(b3, "(c2) secenekler.js")
if s3:
    kontrol(s3["fonk"] is True,
            'PRUVO_SECENEK.fonksiyonelMi("%s") === true (bulunan: %r)' % (KATEGORI, s3["fonk"]))
    kontrol(s3["fonkDekor"] is True, 'fonksiyonelMi("Dekorasyon") === true (emsal bozulmamis)')
    kontrol(s3["fonkYok"] is False, "fonksiyonelMi(tanimsiz kategori) === false (liste yuk tasiyor)")
    kontrol("Malzeme: PETG (+%30)" in (s3["detay"] or ""),
            "satirOzeti Skan Art satirina malzeme/renk detayini yaziyor (bulunan: %r)" % s3["detay"])
    # 1.000 TL × PETG (+%30) = 1.300,00 TL; adet 2 -> 260000 kurus. fonksiyonelMi bypass
    # edilirse katsayi UYGULANMAZ ve 200000 kurus tahsil edilir (sessiz eksik tahsilat).
    kontrol(s3["kurus"] == 260000,
            "malzeme KATSAYISI uygulaniyor: 2 × (1.000 TL +%%30) = 260000 kurus (bulunan: %r)"
            % s3["kurus"])

bitir()

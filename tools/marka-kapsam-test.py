#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — MARKA × KATEGORİ KAPSAMI (çip hedefi + marka/model sayfası kapsamı).

NEDEN VAR (Okan, 30 Tem — SESSİZ hata sınıfı): çok-dikeyli markalar (ölçüldü: Yamaha 6
dikey, Suzuki 5, BMW 4, Volvo 2 — "Volvo Penta"nın 21 Marin ürünü kanonik "Volvo"ya
katlanıyor) tek marka kovasında birleşiyordu. Marin'de "Yamaha" çipine basan müşteriye
motosiklet/elektronik parçası çıkıyordu; hata EKRANDA hata gibi görünmüyor, kimse
bildirmiyor, satış sessizce kayboluyordu.

KARAR (KraL): yeni marka adı UYDURULMAZ ("Yamaha Marine" aramayı böler + Ege eşleşmesini
kırar). Ayırt edici zaten var: marka + kategori ÇİFTİ. Çip hedefi hangi kategoriden
tıklandıysa o kapsamı taşır; marka/model sayfası kapsamı UYGULAR; kanonik URL değişmez.

NE KİLİTLER (her madde POZİTİF + NEGATİF vakayla):
  1. Marin'de Yamaha çipine basıldığında dönen küme YALNIZ Marin (Motosiklet/Elektronik = 0).
  2. Kategori seçili DEĞİLKEN (kanonik, parametresiz) sayfaya HİÇ dokunulmaz — eski davranış.
  3. Geçersiz/bilinmeyen kapsam -> FAIL-CLOSED (0 ürün + görünür uyarı). Sessizce tüm
     kataloğu göstermek KIRMIZI'dır.
  4. data-kat'ı OKUNAMAYAN kart kapsam altında GİZLENİR (kaçak yok).
  5. Kapsam GÖRÜNÜR ve KALDIRILABİLİR (kapsam şeridi + parametresiz adrese dönüş linki).
  6. SEO: kanonik URL parametresiz kalır, sitemap'e parametreli/yeni girdi girmez.
  7. ARAMA BAĞLAMI TAŞIMA (Okan, 3 Ağu — ölçülen müşteri hatası: "Kapı Kolu" aranıp Volvo
     çipine basılınca sorgu DÜŞÜYORDU): marka/model sayfasında arama kutusu TEKİL, aria-
     label'lı, bu sayfanın markasını gizli alanla taşıyor + "Tüm katalogda ara" görünür
     çıkışı var; sayfaya `?ara=…` ile gelindiğinde ana katalog aramasına (marka= korunarak)
     GERÇEKTEN yönlendirdiği node'da koşturulur (ayrı dosya AÇILMAZ — CI kapsam kapısı
     yalnız deploy.yml'de FİİLEN koşulan dosyaları tanır; bu iş deploy.yml'e DOKUNAMAZ,
     bu yüzden aynı kapıya kaynaşır — ikiz tanım riski yok, kaynak marka_model_build.py).

NASIL ÖLÇER (kopya mantık YOK — canlı kod koşar):
  A) /marka/... sayfalarını GERÇEK jeneratörle (marka_model_build.uret) geçici bir ROOT'a
     ürettirir; kart/model-buton eksenini üretilen HTML'den okur.
  B) Kapsam kararını veren JS'i marka_model_build'in MARKER'ları arasından ayıklar ve
     node'da GERÇEKTEN koşturur (minimal DOM shim + gerçek katalog fikstürü).
  C) index.html'deki markaKapsamSorgusu()'nu KAYNAKTAN ayıklayıp node'da koşturur ve
     çipe gerçekten kablolu olduğunu doğrular.

Veri okunamazsa "yeşil" DEMEZ: "OLCULEMEDI" basar ve exit 2 verir.
Node yoksa CI'da (GITHUB_ACTIONS) DAİMA exit 1 (yalancı-yeşil olamaz); yerelde
MARKA_KAPSAM_NODE_ATLA=1 ile AÇIK uyarıyla atlanır. Offline, ağ yok, urunler.json'a YAZMAZ.

Çalıştır:  python3 tools/marka-kapsam-test.py   (0 = geçti, 1 = kaldı, 2 = ölçülemedi)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

FAILS = []

# Kapsam davranışının sınanacağı ÇOK-DİKEYLİ markalar (ölçüldü, 30 Tem).
# (marka, kapsam_kategorisi, kapsam_dışı_olması_gereken_örnek_kategoriler)
VAKALAR = [
    ("Yamaha", "Marin", ["Motosiklet", "Elektronik", "Bisiklet", "Oyun/Hobi", "Bahçe"]),
    ("Yamaha", "Motosiklet", ["Marin", "Elektronik"]),
    ("Suzuki", "Marin", ["Otomobil", "Motosiklet", "Kamera"]),
    ("Suzuki", "Otomobil", ["Motosiklet", "Marin"]),
    ("Honda", "Motosiklet", ["Otomobil", "Bahçe"]),
    ("BMW", "Motosiklet", ["Otomobil", "Bisiklet", "Kamera"]),
    ("BMW", "Otomobil", ["Motosiklet", "Bisiklet"]),
    ("Volvo", "Marin", ["Otomobil"]),          # Volvo Penta -> kanonik Volvo (ayrı ad UYDURULMADI)
    ("Volvo", "Otomobil", ["Marin"]),
]


def kontrol(ad, kosul):
    if kosul:
        print("  PASS  " + ad)
    else:
        FAILS.append(ad)
        print("  FAIL  " + ad)


def olculemedi(sebep):
    print("\nSONUC: OLCULEMEDI ❓  " + sebep)
    sys.exit(2)


def bitir():
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldı)" % len(FAILS))
        sys.exit(1)
    print("\nSONUC: YESIL ✅")
    sys.exit(0)


# ---------------------------------------------------------------- A) canlı kaynak + üretim
try:
    import build
    import marka_model_build as mm
    import landing_hub_build as lh
except Exception as e:                                    # noqa: BLE001
    olculemedi("marka_model_build/build/landing_hub_build import edilemedi: %r" % (e,))

try:
    with open(build.JSON_PATH, encoding="utf-8") as f:
        PRODUCTS = json.load(f)
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        INDEX_HTML = f.read()
except Exception as e:                                    # noqa: BLE001
    olculemedi("katalog/index.html okunamadı: %r" % (e,))

if not PRODUCTS:
    olculemedi("urunler.json BOŞ (kapsam ölçülemez)")

URUN_KAT = {}
for _p in PRODUCTS:
    if _p.get("id"):
        URUN_KAT[_p["id"]] = (_p.get("kategori") or "").strip()

try:
    KATEGORILER = mm.kategori_evreni(INDEX_HTML)
except SystemExit as e:                                   # noqa: BLE001
    olculemedi("kategori evreni index.html'den ayıklanamadı: %r" % (e,))

kontrol("kategori evreni index.html'den ayıklandı (%d kategori)" % len(KATEGORILER),
        len(KATEGORILER) >= 12 and "Marin" in KATEGORILER and "Motosiklet" in KATEGORILER)

# ------------------------------------------- KAPSAM ÇAPASI: YORUM DEĞİL İŞLEV (31 Tem)
# 🔴 ESKİ ÇAPA: `mm._KAPSAM_JS_BAS in html` — yani `/* PRUVO MARKA KAPSAMI BAS */`, bir JS
# YORUMU. Yayın kopyasından yorumları soyan bir adım kapsam scriptine HİÇ dokunmadan bu
# iddiayı düşürüyordu (ölçüldü: aynı sayfada id="kapsamNot"/id="kapsamBos" 1=1, yani işlev
# duruyor, çapa yok). Yorum-çapalı kapı ya sessizce ölür ya sahte alarm verir →
# [[kapi-anchor-coupling-ikilemi]].
#
# YENİ ÇAPA — iki katmanlı, ikisi de YORUMDAN BAĞIMSIZ:
#   (Z) ZEMİN (node'suz): sayfada TAM BİR öznitelisiz inline <script>, kapsam global'ini
#       ATAR **ve** çağrı yerini taşır. Adlar tek kaynaktan (marka_model_build gövdesi +
#       çağrısı) TÜRETİLİR — modülde meşru bir yeniden adlandırma kapıyı sahte-kırmızı
#       yakmaz, çünkü çapa da onunla birlikte kayar.
#   (T) TAVAN (node): sayfanın KENDİ gömülü scripti koşturulur; global tanımlanıyor mu,
#       gömülü çağrı yeri ateşliyor mu (sayfaya dokunuyor mu), gerçek kategori evreniyle
#       kablolu mu ve jeneratörün modülüyle KARAR PARİTESİ var mı ölçülür.
# YAKALADIĞI SALDIRI (değişmedi): kapsam scriptinin marka/model sayfasından DÜŞMESİ →
# "Marin'de Yamaha" çipine basan müşteriye motosiklet parçası çıkar; ekranda hata görünmez,
# satış sessizce kaybolur. Boş/taklit gövde de artık geçemez.
_m_ad = re.search(r"\bg\.([A-Za-z_$][\w$]*)\s*=(?!=)", mm._KAPSAM_JS_GOVDE)
_m_cagri = re.search(r"\bwindow\.([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\s*\(",
                     mm._KAPSAM_JS_CAGRI)
kontrol("kapsam çapası TEK KAYNAKTAN türetildi (global adı + çağrılan metot)",
        bool(_m_ad) and bool(_m_cagri) and _m_ad.group(1) == _m_cagri.group(1))
if not (_m_ad and _m_cagri and _m_ad.group(1) == _m_cagri.group(1)):
    olculemedi("marka_model_build kapsam gövdesi/çağrısı çözümlenemedi — çapa türetilemedi "
               "(FAIL-CLOSED: sessizce 'çapa yok' sayılmaz)")
KAPSAM_AD = _m_ad.group(1)
KAPSAM_METOT = _m_cagri.group(2)

# Öznitelisiz inline <script> gövdeleri (JSON-LD `type=` ve `src`li gtag bloğu YAPISAL
# olarak dışarıda kalır — öznitelik ayrımı, yorum ayrımı DEĞİL).
INLINE_SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.S)
KAPSAM_TANIM_RE = re.compile(r"\.%s\s*=(?!=)" % re.escape(KAPSAM_AD))
KAPSAM_CAGRI_RE = re.compile(r"\.%s\s*\.\s*%s\s*\(" % (re.escape(KAPSAM_AD),
                                                       re.escape(KAPSAM_METOT)))


def kapsam_bloklari(html):
    """Kapsam global'ini ATAYAN **ve** çağrı yerini taşıyan inline script gövdeleri."""
    return [s for s in INLINE_SCRIPT_RE.findall(html)
            if KAPSAM_TANIM_RE.search(s) and KAPSAM_CAGRI_RE.search(s)]

# ---- index.html: çip hedefi kapsamı TAŞIYOR mu (kaynak kuplajı) ----
kontrol("index.html'de MARKA KAPSAMI blok marker'ları var",
        "// --- MARKA KAPSAMI BAŞ ---" in INDEX_HTML
        and "// --- MARKA KAPSAMI SON ---" in INDEX_HTML)
kontrol("marka çipi hedefi kapsamı taşıyor (markaKapsamSorgusu(activeCat, query) kablolu)",
        '"/marka/" + slug + "/" + markaKapsamSorgusu(activeCat, query)' in INDEX_HTML)

# ---- GERÇEK jeneratörle /marka/... üret (geçici ROOT; depoya YAZMAZ) ----
TMP = tempfile.mkdtemp(prefix="marka-kapsam-")
try:
    ctx = build.marka_model_ctx()
    ctx["ROOT"] = TMP
    with open(os.path.join(TMP, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    try:
        sonuc = mm.uret(PRODUCTS, ctx)
    except Exception as e:                                # noqa: BLE001
        shutil.rmtree(TMP, ignore_errors=True)
        olculemedi("marka_model_build.uret çöktü: %r" % (e,))

    # ---- SEO: sitemap kaydı parametreli/yeni URL ailesi AÇMAZ ----
    sitemap = sonuc["sitemap"]
    sitemap_sayfalari = sonuc.get("sitemap_sayfalari", [])
    parametreli = [loc for loc, _pri, _cf in sitemap if "?" in loc]
    kontrol("sitemap'te parametreli (?) marka kaydı YOK (bulunan: %d)" % len(parametreli),
            not parametreli)
    sinif_sayilari = Counter(sinif for sinif, _url in sitemap_sayfalari)
    kanonik_siniflar = set(mm.SITEMAP_SAYFA_SINIFLARI)
    manifest_siniflari = set(sinif_sayilari)
    kontrol("sitemap sayfa sınıfları kanonik evrenle birebir (%s)"
            % ",".join(sorted(manifest_siniflari)),
            manifest_siniflari == kanonik_siniflar)
    kontrol("sitemap URL'leri kanonik sınıf manifestiyle birebir",
            [loc for loc, _pri, _cf in sitemap] == [url for _sinif, url in sitemap_sayfalari]
            and len(set(url for _sinif, url in sitemap_sayfalari)) == len(sitemap_sayfalari))
    beklenen_kayit = len(sitemap_sayfalari)
    beklenen_model = sinif_sayilari["model"] + sinif_sayilari["diger"]
    kontrol("sitemap kayıt sayısı = marka(%d) + model-katmanı(%d; diğer=%d) + "
            "/marka/ dizini(%d) = %d"
            % (sinif_sayilari["marka"], beklenen_model, sinif_sayilari["diger"],
               sinif_sayilari["dizin"], beklenen_kayit),
            len(sitemap) == beklenen_kayit
            and sonuc["marka_sayfasi_sayisi"] == sinif_sayilari["marka"]
            and sonuc["model_sayfasi_sayisi"] == beklenen_model
            and sinif_sayilari["dizin"] == 1)

    KART_RE = re.compile(r'<div class="card" data-kat="([^"]*)"><a class="card-main" '
                         r'href="([^"]+)"')
    # data-katsay'den SONRA ek alan gelebilir (data-mm = model indeksi; sayfa-içi filtre
    # onu okur). Çapa alanın VARLIĞINA bağlı, tag'in o alanla BİTMESİNE değil — yoksa
    # markuba eklenen her yeni alan bu nöbetçiyi sessizce kör ederdi (ölçüldü: `data-mm`
    # eklenince butonlar HİÇ ayrışmadı ve "model sayfası fikstürü çıkarıldı" kırmızısı,
    # gerçek kusur olmadığı hâlde, yayını durduruyordu).
    BTN_RE = re.compile(r'<a class="mm-model-btn" href="([^"]+)" data-katsay="([^"]*)"[^>]*>'
                        r'.*?<span class="adet">([^<]*)</span>')
    KART_HERHANGI_RE = re.compile(r'<div class="card(?: [^"]*)?"[^>]*>')
    ID_RE = re.compile(r"/urun/([^/]+)/")

    # ---- ARAMA BAĞLAMI TAŞIMA: statik yapı regex'leri (madde 7) ----
    ARAMA_FORM_RE = re.compile(
        r'<form class="mm-arama"[^>]*action="/"[^>]*method="get"[^>]*role="search">.*?</form>', re.S)
    ARAMA_INPUT_RE = re.compile(r'<input type="search" name="ara"[^>]*aria-label="[^"]+"')
    ARAMA_HIDDEN_MARKA_RE = re.compile(r'<input type="hidden" name="marka" value="([^"]*)">')
    ARAMA_CIKIS_RE = re.compile(r'<a class="mm-arama-tumu" href="/">T[uü]m katalogda ara</a>')
    # ARA-TAŞI scripti İŞLEVSEL çapa (YORUM DEĞİL — yayın hattı <script> içi /* … */ yorumları
    # SOYAR; kapsam scriptiyle AYNI ilke, bkz. dosya başı "ÇAPA = İŞLEV").
    ARA_TASI_ISLEV_RE = re.compile(
        r'hedef\.set\("ara",\s*ara\).*?hedef\.set\("marka",\s*MARKA\).*?window\.location\.replace\(',
        re.S)

    def arama_kutusu_kontrol(etiket, html, beklenen_marka):
        formlar = ARAMA_FORM_RE.findall(html)
        kontrol("%s arama kutusu formu TEKİL (bulunan: %d)" % (etiket, len(formlar)),
                len(formlar) == 1)
        kontrol("%s arama kutusu name=ara + aria-label taşıyor" % etiket,
                bool(ARAMA_INPUT_RE.search(html)))
        hm = ARAMA_HIDDEN_MARKA_RE.search(html)
        import html as _html_mod
        kontrol("%s gizli marka= alanı sayfanın markasıyla eşleşiyor (%r)" % (etiket, beklenen_marka),
                bool(hm) and _html_mod.unescape(hm.group(1)) == beklenen_marka)
        kontrol("%s \"Tüm katalogda ara\" çıkışı TEKİL" % etiket,
                len(ARAMA_CIKIS_RE.findall(html)) == 1)
        kontrol("%s arama-taşı scripti İŞLEVSEL çapayla + bu markanın JS değişmezi ile gömülü" % etiket,
                bool(ARA_TASI_ISLEV_RE.search(html))
                and json.dumps(beklenen_marka, ensure_ascii=False) in html)

    def sayfa_oku(rel):
        yol = os.path.join(TMP, *rel.strip("/").split("/"), "index.html")
        if not os.path.isfile(yol):
            return None
        with open(yol, encoding="utf-8") as fh:
            return fh.read()

    def sayfa_fikstur(html, ad):
        """Üretilen GERÇEK sayfadan kapsam eksenini çıkar (kart data-kat + buton data-katsay)."""
        kartlar = []
        for kat, href in KART_RE.findall(html):
            m = ID_RE.search(href)
            kartlar.append({"id": m.group(1) if m else href,
                            "kat": kat.replace("&amp;", "&")})
        butonlar = [{"href": h, "katsay": ks.replace("&quot;", '"').replace("&amp;", "&"),
                     "adet": ad_}
                    for h, ks, ad_ in BTN_RE.findall(html)]
        return {"ad": ad, "kartlar": kartlar, "butonlar": butonlar,
                "pathname": "/" + ad.strip("/") + "/"}

    fiksturler = {}
    sayfa_scriptleri = {}       # sayfa -> tüm inline script gövdeleri (node koşumu için)
    markalar = sorted({m for m, _k, _d in VAKALAR})
    for marka in markalar:
        slug = mm._slug(marka)
        html = sayfa_oku("marka/" + slug)
        if html is None:
            kontrol("/marka/%s/ üretildi" % slug, False)
            continue
        # kanonik URL parametresiz mi (SEO regresyonu yok)
        kan = re.findall(r'<link rel="canonical" href="([^"]+)">', html)
        kontrol("/marka/%s/ kanonik URL parametresiz (%s)" % (slug, kan[0] if kan else "-"),
                len(kan) == 1 and kan[0].endswith("/marka/" + slug + "/") and "?" not in kan[0])
        # her kart data-kat taşıyor mu (fail-closed ekseni eksiksiz mi)
        toplam_kart = len(KART_HERHANGI_RE.findall(html))
        f = sayfa_fikstur(html, "marka/" + slug)
        kontrol("/marka/%s/ her kart data-kat taşıyor (%d/%d)"
                % (slug, len(f["kartlar"]), toplam_kart),
                toplam_kart > 0 and len(f["kartlar"]) == toplam_kart)
        # data-kat GERÇEK ürün kategorisi mi (uydurma eksen değil)
        yanlis = [k["id"] for k in f["kartlar"]
                  if k["id"] in URUN_KAT and URUN_KAT[k["id"]] != k["kat"]]
        kontrol("/marka/%s/ data-kat = ürünün gerçek kategorisi (sapma: %d)"
                % (slug, len(yanlis)), not yanlis)
        # model butonlarının kategori kırılımı var mı
        kontrol("/marka/%s/ model butonları data-katsay taşıyor (%d buton)"
                % (slug, len(f["butonlar"])),
                all(b["katsay"].startswith("{") for b in f["butonlar"]))
        # kapsam şeridi + kaldırma yolu SSR'de var ve GİZLİ (crawler görmez)
        kontrol("/marka/%s/ kapsam şeridi gizli SSR'de var (kapsamNot + sıfırlama linki)"
                % slug,
                'id="kapsamNot" style="display:none"' in html
                and 'id="kapsamNotSifirla"' in html and 'id="kapsamBos"' in html)
        # ÇAPA = İŞLEV: kapsam global'ini ATAYAN + çağrı yerini taşıyan TAM BİR blok
        # (eski çapa `/* PRUVO MARKA KAPSAMI BAS */` YORUMUYDU — soyulunca ölüyordu).
        kb = kapsam_bloklari(html)
        kontrol("/marka/%s/ kapsam scripti gömülü (%s ataması + çağrı yeri: %d blok)"
                % (slug, KAPSAM_AD, len(kb)), len(kb) == 1)
        if kb:
            sayfa_scriptleri["marka/" + slug] = INLINE_SCRIPT_RE.findall(html)
        arama_kutusu_kontrol("/marka/%s/" % slug, html, marka)
        fiksturler[marka] = f

    # model sayfası da kapsam uygular mı (örnek: en çok ürünlü marka modeli)
    model_ornek = None
    for marka in markalar:
        f = fiksturler.get(marka)
        if not f or not f["butonlar"]:
            continue
        rel = f["butonlar"][0]["href"]
        html = sayfa_oku(rel)
        if html is None:
            continue
        mf = sayfa_fikstur(html, rel)
        mkb = kapsam_bloklari(html)
        kontrol("model sayfası %s kapsam scripti + şeridi taşıyor (%d blok)" % (rel, len(mkb)),
                len(mkb) == 1 and 'id="kapsamNot"' in html and 'data-kapsam-tasi' in html)
        if mkb:
            sayfa_scriptleri[rel.strip("/")] = INLINE_SCRIPT_RE.findall(html)
        kontrol("model sayfası %s kartları data-kat taşıyor" % rel,
                len(mf["kartlar"]) == len(KART_HERHANGI_RE.findall(html))
                and len(mf["kartlar"]) > 0)
        arama_kutusu_kontrol("model sayfası %s" % rel, html, marka)
        model_ornek = mf
        break
    kontrol("model sayfası fikstürü çıkarıldı", model_ornek is not None)

    # ---- YUKARI-ÇIK OKU (Okan, 3 Ağu — gözlem): ana sayfada çalışıyordu, marka/model/hub
    # sayfasında YOKTU. build.py'nin TEK KAYNAKTAN (TOP_BTN_BLOCK_HTML) ürettiği buton, ctx
    # üzerinden marka_model_build/_shell VE landing_hub_build/_shell'e AYNI şekilde ulaşıyor mu.
    BTN_ID = 'id="topBtn"'
    BTN_ARIA = 'aria-label="Yukarı çık"'
    bmw_html = sayfa_oku("marka/bmw")
    kontrol("/marka/bmw/: yukarı-çık butonu TEKİL", bool(bmw_html) and bmw_html.count(BTN_ID) == 1)
    kontrol("/marka/bmw/: aria-label var", bool(bmw_html) and BTN_ARIA in bmw_html)
    marka_index_html = sayfa_oku("marka")
    kontrol("/marka/ (dizin): yukarı-çık butonu TEKİL",
            bool(marka_index_html) and marka_index_html.count(BTN_ID) == 1)
    if model_ornek is not None:
        model_html_tekrar = sayfa_oku(model_ornek["ad"])
        kontrol("model sayfası %s: yukarı-çık butonu TEKİL" % model_ornek["ad"],
                bool(model_html_tekrar) and model_html_tekrar.count(BTN_ID) == 1)

    hub_sonuc = lh.uret(ctx)
    hub_yol = os.path.join(TMP, hub_sonuc["hub_slug"], "index.html")
    with open(hub_yol, encoding="utf-8") as fh:
        hub_html = fh.read()
    kontrol("hub sayfası (/%s/): yukarı-çık butonu TEKİL" % hub_sonuc["hub_slug"],
            hub_html.count(BTN_ID) == 1)
    kontrol("hub sayfası: aria-label var", BTN_ARIA in hub_html)

    kapsam_js = mm._KAPSAM_JS_GOVDE.replace(
        "__KATEGORILER__", json.dumps(KATEGORILER, ensure_ascii=False,
                                      separators=(",", ":")))
    ara_tasi_js = mm._ARA_TASI_JS_GOVDE.replace("__MARKA__", json.dumps("Volvo", ensure_ascii=False))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

# ---- index.html markaKapsamSorgusu()'nu KAYNAKTAN ayıkla ----
m = re.search(r"function markaKapsamSorgusu\(kat, q\)\{[\s\S]*?\n  \}", INDEX_HTML)
kontrol("index.html markaKapsamSorgusu() ayıklanabildi", bool(m))
cip_js = m.group(0) if m else ""

if FAILS:
    bitir()

# ---------------------------------------------------------------- B) node davranış bölümü
try:
    subprocess.run(["node", "--version"], capture_output=True, check=True)
    node_var = True
except (OSError, subprocess.CalledProcessError):
    node_var = False

if not node_var:
    if os.environ.get("GITHUB_ACTIONS"):
        kontrol("CI'da node var (FAIL-CLOSED: setup-node eksik/bozuk)", False)
        bitir()
    if os.environ.get("MARKA_KAPSAM_NODE_ATLA") == "1":
        print("UYARI: node yok + MARKA_KAPSAM_NODE_ATLA=1 → davranış bölümü AÇIK uyarıyla "
              "atlandı (yalnız üretim/kaynak-kuplaj kontrolleri koştu).")
        bitir()
    olculemedi("node yok (yerelde kur ya da MARKA_KAPSAM_NODE_ATLA=1 ile açık uyarıyla atla)")

VERI = {
    "kapsamJs": kapsam_js,
    "araTasiJs": ara_tasi_js,
    "cipJs": cip_js,
    "kategoriler": KATEGORILER,
    "vakalar": [{"marka": mk, "kapsam": kp, "disari": ds} for mk, kp, ds in VAKALAR],
    "sayfalar": {mk: fiksturler[mk] for mk in fiksturler},
    "modelSayfasi": model_ornek,
    # ÇAPA=İŞLEV ekseni: üretilen sayfaların KENDİ inline script'leri + tek kaynaktan
    # türetilen global/metot adları (bölüm 0 bunları node'da GERÇEKTEN koşturur).
    "sayfaScriptleri": sayfa_scriptleri,
    "kapsamAd": KAPSAM_AD,
    "kapsamMetot": KAPSAM_METOT,
}

HARNESS = r"""
"use strict";
const VERI = require(VERI_JSON);

// --- Kapsam kararını veren CANLI kod (marka_model_build MARKER'ları arasından ayıklandı) ---
(0, eval)(VERI.kapsamJs);
const K = globalThis.PRUVO_KAPSAM;
// --- index.html'deki CANLI çip hedefi fonksiyonu ---
(0, eval)("globalThis.markaKapsamSorgusu = " + VERI.cipJs.replace(/^function markaKapsamSorgusu/, "function"));

// --- marka_model_build'in CANLI arama-taşı yönlendirme scripti (IIFE, tekrar-koşulabilir) ---
function araTasiCalistir(search){
  let HEDEF = null;
  global.window = { location: { search: search, replace: (u) => { HEDEF = u; } } };
  (0, eval)(VERI.araTasiJs);
  return HEDEF;
}

let pass = 0, fail = 0;
function ok(cond, msg){
  if(cond){ pass++; console.log("  PASS  " + msg); }
  else    { fail++; console.log("  FAIL  " + msg); }
}

// ---- minimal DOM shim: glue'nun GERÇEKTEN kullandığı yüzey kadar ----
function shim(sayfa, ekKartlar){
  const kartlar = (sayfa.kartlar.concat(ekKartlar || [])).map(function(k){
    // K117-A: data-mm opsiyonel — sayfa-içi model filtresinin üyelik ekseni. Mevcut
    // fikstür kartlarında YOK (backward compat), test ek kartlarında veya `sayfa.kartlar`
    // üzerinden `dataMm` alanıyla verilir.
    const attrs = {"data-kat": k.kat};
    if(k.dataMm !== undefined && k.dataMm !== null){ attrs["data-mm"] = k.dataMm; }
    return { id: k.id, kat: k.kat, dataMm: attrs["data-mm"],
             style: {display: ""},
             getAttribute: (n) => (attrs[n] === undefined ? null : attrs[n]) };
  });
  const butonlar = sayfa.butonlar.map(function(b){
    const adet = {textContent: b.adet};
    const attrs = {"data-katsay": b.katsay, "href": b.href};
    return { style: {display: ""}, adetEl: adet, attrs: attrs,
             getAttribute: (n) => (attrs[n] === undefined ? null : attrs[n]),
             setAttribute: (n, v) => { attrs[n] = v; },
             querySelector: (s) => (s === ".adet" ? adet : null) };
  });
  const tasi = [{ attrs: {href: "/marka/x/"},
                  getAttribute: function(n){ return this.attrs[n] === undefined ? null : this.attrs[n]; },
                  setAttribute: function(n, v){ this.attrs[n] = v; } }];
  const sayimKart = {textContent: String(sayfa.kartlar.length)};
  const sayimModel = {textContent: String(sayfa.butonlar.length)};
  const kutu = {
    kapsamNot:        {style: {display: "none"}},
    kapsamNotMetin:   {textContent: ""},
    kapsamNotSifirla: {attrs: {href: "./"},
                       getAttribute: function(n){ return this.attrs[n]; },
                       setAttribute: function(n, v){ this.attrs[n] = v; }},
    kapsamBos:        {style: {display: "none"}}
  };
  const harita = {
    ".card[data-kat]": kartlar,
    ".mm-model-btn[data-katsay]": butonlar,
    "a[data-kapsam-tasi]": tasi,
    ".mm-sayim-kart": [sayimKart],
    ".mm-sayim-model": [sayimModel]
  };
  const dok = {
    querySelectorAll: (sel) => (harita[sel] || []),
    getElementById: (id) => (kutu[id] || null)
  };
  return {dok, kartlar, butonlar, tasi, sayimKart, sayimModel, kutu};
}
const gorunenKartlar = (s) => s.kartlar.filter((k) => k.style.display !== "none");
const gorunenBtnlar  = (s) => s.butonlar.filter((b) => b.style.display !== "none");

// ==================== 0) SAYFAYA GÖMÜLÜ KAPSAM MODÜLÜ — ÇAPA=İŞLEV ====================
// Eski çapa `/* PRUVO MARKA KAPSAMI BAS */` (bir YORUM) idi. Burada sayfanın KENDİ inline
// script'leri ayrı ayrı GERÇEKTEN koşturulur: hangisi kapsam global'ini tanımlıyor, gömülü
// çağrı yeri ateşliyor mu, gerçek kategori evreniyle kablolu mu, jeneratörün modülüyle
// karar paritesi var mı. Yorumların tamamı silinse de bu iddiaların HİÇBİRİ değişmez.
const vm = require("vm");
function sayfaCalistir(src, arama){
  const dokunma = {qsa: 0, gebi: 0};
  const dok = { querySelectorAll: function(){ dokunma.qsa++; return []; },
                getElementById: function(){ dokunma.gebi++; return null; } };
  const win = { location: {search: arama, pathname: "/marka/x/"} };
  const ctx = { window: win, document: dok, URLSearchParams: URLSearchParams,
                JSON: JSON, String: String, Object: Object,
                console: {log: function(){}, warn: function(){}, error: function(){}} };
  let hata = null;
  try { vm.runInNewContext(src, ctx, {filename: "gomulu.js", timeout: 5000}); }
  catch(e){ hata = String((e && e.message) || e).slice(0, 140); }
  const K2 = win[VERI.kapsamAd];
  if(!K2 || typeof K2[VERI.kapsamMetot] !== "function"){ return null; }
  return {K: K2, dokunma: dokunma, hata: hata};
}
const sayfaAdlari = Object.keys(VERI.sayfaScriptleri);
ok(sayfaAdlari.length >= 2,
   "gömülü kapsam modülü ölçülecek sayfa sayısı >= 2 (" + sayfaAdlari.length + ")");
let gomuluOrnek = null;
for(const ad of sayfaAdlari){
  const arama = "?kategori=" + encodeURIComponent(VERI.kategoriler[0]);
  const bulunan = VERI.sayfaScriptleri[ad].map((s) => sayfaCalistir(s, arama)).filter(Boolean);
  ok(bulunan.length === 1,
     ad + ": koşunca " + VERI.kapsamAd + " TANIMLAYAN inline script tam 1 (" + bulunan.length + ")");
  if(bulunan.length !== 1){ continue; }
  const B = bulunan[0];
  ok(B.hata === null, ad + ": gömülü kapsam script'i hatasız koştu (" + B.hata + ")");
  ok(B.dokunma.qsa > 0 && B.dokunma.gebi > 0,
     ad + ": gömülü ÇAĞRI YERİ ateşledi (uygula sayfaya dokundu: qsa=" + B.dokunma.qsa +
     ", gebi=" + B.dokunma.gebi + ")");
  ok(JSON.stringify(B.K.KATEGORILER) === JSON.stringify(VERI.kategoriler),
     ad + ": gömülü modül GERÇEK kategori evreniyle kablolu (" +
     ((B.K.KATEGORILER || []).length) + ")");
  let sapma = 0;
  const girdiler = VERI.kategoriler.concat(["Uydurma", "marin", "", null, "Marin ", "%20"]);
  for(const gi of girdiler){
    const a = B.K.coz(gi, VERI.kategoriler), b = K.coz(gi, VERI.kategoriler);
    if(JSON.stringify(a) !== JSON.stringify(b)){ sapma++; continue; }
    if(B.K.sorgu(a) !== K.sorgu(b)){ sapma++; continue; }
    for(const ogeKat of ["Marin", "Otomobil", "", null]){
      if(B.K.gorunur(ogeKat, a) !== K.gorunur(ogeKat, b)){ sapma++; }
    }
    if(B.K.sayimla('{"Marin":3,"Otomobil":5}', a) !== K.sayimla('{"Marin":3,"Otomobil":5}', b)){ sapma++; }
    if(B.K.sayimla("{bozuk", a) !== K.sayimla("{bozuk", b)){ sapma++; }
  }
  ok(sapma === 0, ad + ": gömülü modül <-> jeneratör modülü KARAR PARİTESİ (sapma " + sapma +
     " / " + girdiler.length + " girdi)");
  if(!gomuluOrnek){ gomuluOrnek = {ad: ad, K: B.K}; }
}
// Gömülü modülün TAM uygula() denkliği (gerçek sayfa fikstürü üzerinde).
(function(){
  if(!gomuluOrnek){ ok(false, "gömülü kapsam modülü örneği yok (uygula denkliği ÖLÇÜLEMEDİ)"); return; }
  const marka = Object.keys(VERI.sayfalar)[0];
  const sayfa = VERI.sayfalar[marka];
  for(const arama of ["", "?kategori=Marin", "?kategori=Uydurma"]){
    const s1 = shim(sayfa), s2 = shim(sayfa);
    const loc = {search: arama, pathname: "/" + sayfa.ad + "/"};
    K.uygula(s1.dok, loc);
    gomuluOrnek.K.uygula(s2.dok, loc);
    const g1 = gorunenKartlar(s1).map((k) => k.id).sort().join("|");
    const g2 = gorunenKartlar(s2).map((k) => k.id).sort().join("|");
    ok(g1 === g2 &&
       s1.kutu.kapsamNotMetin.textContent === s2.kutu.kapsamNotMetin.textContent &&
       s1.kutu.kapsamBos.style.display === s2.kutu.kapsamBos.style.display,
       "gömülü modül uygula() denkliği (" + JSON.stringify(arama) + ", " +
       g1.split("|").filter(Boolean).length + " kart)");
  }
})();

// ============================ 1) ÇİP HEDEFİ (index.html canlı kodu) ============================
ok(markaKapsamSorgusu("Tümü") === "", "kategori seçili DEĞİLKEN çip hedefi eski davranışta (sorgu boş)");
ok(markaKapsamSorgusu("") === "" && markaKapsamSorgusu(null) === "" && markaKapsamSorgusu(undefined) === "",
   "boş/None kategori -> sorgu boş (regresyon yok)");
ok(markaKapsamSorgusu("Marin") === "?kategori=Marin", "Marin'de çip hedefi kapsam taşıyor");
ok(markaKapsamSorgusu("Oyun/Hobi") === "?kategori=Oyun%2FHobi", "eğik çizgili kategori URL-kodlanıyor");
ok(markaKapsamSorgusu("Bahçe") === "?kategori=Bah%C3%A7e", "Türkçe karakterli kategori URL-kodlanıyor");
for(const kat of VERI.kategoriler){
  const q = markaKapsamSorgusu(kat);
  const cozum = K.coz(new URLSearchParams(q.replace(/^\?/, "")).get("kategori"), VERI.kategoriler);
  if(!(cozum.aktif && cozum.gecerli && cozum.kategori === kat)){
    ok(false, "çip sorgusu -> kapsam gidiş-dönüş bozuk: " + kat);
  }
}
ok(true, "tüm kategoriler için çip sorgusu <-> kapsam gidiş-dönüşü tutarlı (" + VERI.kategoriler.length + ")");

// ============================ 1b) ARAMA BAĞLAMI TAŞIMA (Okan, 3 Ağu) ============================
// "Kapı Kolu" aranıp Volvo çipine basılınca sorgu DÜŞÜYORDU (ölçülen müşteri hatası). Çip hedefi
// artık `ara=` parametresini de taşır -> ÖLDÜRÜCÜ mutant: ikinci argüman (q) yok sayılırsa/silinirse
// bu blok KIRMIZI yanar.
ok(markaKapsamSorgusu("Tümü", "kapı kolu") === "?ara=kap%C4%B1+kolu",
   "arama sorgusu VARKEN kategori seçili değilse çip hedefi yalnız ara= taşır");
ok(markaKapsamSorgusu("Marin", "kapı kolu") === "?kategori=Marin&ara=kap%C4%B1+kolu",
   "kategori + arama sorgusu BİRLİKTE taşınır (bağlam kaybı yok)");
ok(markaKapsamSorgusu("Marin", "") === "?kategori=Marin" && markaKapsamSorgusu("Marin", "   ") === "?kategori=Marin",
   "boş/yalnız-boşluk sorgu ara= EKLEMEZ (regresyon yok, eski davranış korunur)");
ok(markaKapsamSorgusu("Marin", "  cam  ") === "?kategori=Marin&ara=cam",
   "sorgudaki baştaki/sondaki boşluk trim edilir");

// ============================ 2) MARKA SAYFASI KAPSAMI ============================
let pozitifVaka = 0;
for(const v of VERI.vakalar){
  const sayfa = VERI.sayfalar[v.marka];
  if(!sayfa){ ok(false, v.marka + " fikstürü yok"); continue; }
  const etiket = v.marka + " + " + v.kapsam;
  const beklenen = sayfa.kartlar.filter((k) => k.kat === v.kapsam).map((k) => k.id).sort();

  // --- POZİTİF: kapsam uygulanır, dönen küme YALNIZ o kategori ---
  const s = shim(sayfa);
  const c = K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(v.kapsam),
                             pathname: "/" + sayfa.ad + "/"});
  const gor = gorunenKartlar(s);
  const gorIds = gor.map((k) => k.id).sort();
  ok(c.aktif === true && c.gecerli === true, etiket + ": kapsam AKTİF ve geçerli");
  if(beklenen.length > 0){
    pozitifVaka++;
    ok(gorIds.length === beklenen.length && gorIds.every((x, i) => x === beklenen[i]),
       etiket + ": dönen küme = yalnız " + v.kapsam + " (" + gorIds.length + "/" + sayfa.kartlar.length + ")");
  }else{
    // ÖLÇÜLDÜ (30 Tem): bu marka×kategori çiftinin ürünleri /marka/ sayfasına HİÇ girmiyor —
    // gruplandir() markayı HAM marka[0] ile tanıyor, katlanmış adla değil (ör. "Volvo Penta"
    // -> kanonik "Volvo"; 21 Marin ürünü sayfada YOK). AYRI EKSEN, bu işin kapsamı DEĞİL
    // (düzeltmesi sitemap'e girdi ekliyor -> KraL'a raporlandı). Pozitif vaka burada
    // kurulamaz; fail-closed boş davranış + SIFIR sızıntı iddiaları yine de koşar.
    console.log("  BILGI " + etiket + ": sayfada kapsam içi ürün 0 (ayrı eksen — rapora bak)");
    ok(gorIds.length === 0, etiket + ": kapsam içi ürün yokken 0 kart gösterilir");
  }
  ok(gor.every((k) => k.kat === v.kapsam),
     etiket + ": görünen kartların hepsi " + v.kapsam);

  // --- NEGATİF: diğer dikeylerden SIFIR ürün ---
  for(const d of v.disari){
    const sizan = gor.filter((k) => k.kat === d).length;
    const vardi = sayfa.kartlar.filter((k) => k.kat === d).length;
    if(vardi === 0){ continue; }   // o dikey bu sayfada zaten yok -> negatif vaka kurulmaz
    ok(sizan === 0, etiket + ": " + d + " sızıntısı 0 (kapsamsız sayfada " + vardi + " vardı)");
  }

  // --- Model butonları: kapsam dışı model butonu GİZLİ, sayı kapsama düşer ---
  for(const b of s.butonlar){
    const tablo = JSON.parse(b.attrs["data-katsay"]);
    const n = tablo[v.kapsam] || 0;
    if(n > 0){
      ok(b.style.display !== "none" && b.adetEl.textContent === (n + " parça"),
         etiket + ": model butonu kapsam sayısını gösteriyor (" + b.attrs.href + " -> " + n + ")");
      ok(b.attrs.href.indexOf("?kategori=") !== -1,
         etiket + ": model butonu kapsamı taşıyor (" + b.attrs.href + ")");
    }else{
      ok(b.style.display === "none",
         etiket + ": kapsam dışı model butonu GİZLİ (" + b.attrs.href + ")");
    }
  }
  ok(s.sayimKart.textContent === String(gor.length),
     etiket + ": görünür sayım rozeti güncellendi (" + s.sayimKart.textContent + ")");
  ok(s.sayimModel.textContent === String(gorenBtnSay(s)),
     etiket + ": model sayım rozeti güncellendi (" + s.sayimModel.textContent + ")");
  ok(s.kutu.kapsamNot.style.display === "" &&
     s.kutu.kapsamNotMetin.textContent.indexOf(v.kapsam) !== -1,
     etiket + ": kapsam GÖRÜNÜR (şerit açık, kategori adı yazıyor)");
  ok(s.kutu.kapsamNotSifirla.attrs.href === "/" + sayfa.ad + "/",
     etiket + ": kapsamı KALDIRMA yolu var (parametresiz kanonik adres)");
  ok(s.tasi[0].attrs.href.indexOf("?kategori=") !== -1,
     etiket + ": breadcrumb geri-linki kapsamı taşıyor");
}
function gorenBtnSay(s){ return gorunenBtnlar(s).length; }
// Kapı YÜK TAŞISIN: gerçek katalogda en az 7 GERÇEK pozitif vaka (ürünlü marka×kategori)
// koşmuş olmalı; hepsi boşa düşerse "yeşil" anlamsızlaşır.
ok(pozitifVaka >= 7, "gerçek katalogda ürünlü pozitif vaka sayısı >= 7 (koşan: " + pozitifVaka + ")");

// ============================ 3) KANONİK (parametresiz) — REGRESYON YOK ============================
for(const marka of Object.keys(VERI.sayfalar)){
  const sayfa = VERI.sayfalar[marka];
  for(const arama of ["", "?", "?ara=klips", "?kategori="]){
    const s = shim(sayfa);
    const c = K.uygula(s.dok, {search: arama, pathname: "/" + sayfa.ad + "/"});
    ok(c.aktif === false, marka + " kanonik(" + JSON.stringify(arama) + "): kapsam PASİF");
    ok(gorunenKartlar(s).length === sayfa.kartlar.length,
       marka + " kanonik(" + JSON.stringify(arama) + "): tüm kartlar görünür (" + sayfa.kartlar.length + ")");
    ok(gorunenBtnlar(s).length === sayfa.butonlar.length,
       marka + " kanonik(" + JSON.stringify(arama) + "): tüm model butonları görünür");
    ok(s.kutu.kapsamNot.style.display === "none" && s.kutu.kapsamNotMetin.textContent === "",
       marka + " kanonik(" + JSON.stringify(arama) + "): kapsam şeridi KAPALI (crawler tam koleksiyon görür)");
    ok(s.sayimKart.textContent === String(sayfa.kartlar.length),
       marka + " kanonik(" + JSON.stringify(arama) + "): sayım rozeti DEĞİŞMEDİ");
  }
}

// ============================ 4) FAIL-CLOSED: geçersiz/bilinmeyen kapsam ============================
const kotuKapsamlar = ["Uydurma", "marin", "MARİN", "Marin ", "Otomobil;DROP", "../Marin", "%20", "null"];
for(const marka of Object.keys(VERI.sayfalar)){
  const sayfa = VERI.sayfalar[marka];
  for(const kotu of kotuKapsamlar){
    const s = shim(sayfa);
    const c = K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(kotu),
                               pathname: "/" + sayfa.ad + "/"});
    ok(c.aktif === true && c.gecerli === false,
       marka + " geçersiz kapsam " + JSON.stringify(kotu) + ": tanınmadı");
    ok(gorunenKartlar(s).length === 0,
       marka + " geçersiz kapsam " + JSON.stringify(kotu) + ": 0 ürün (sessizce tüm katalog GÖSTERİLMEZ)");
    ok(gorunenBtnlar(s).length === 0,
       marka + " geçersiz kapsam " + JSON.stringify(kotu) + ": 0 model butonu");
    ok(s.kutu.kapsamBos.style.display === "" &&
       s.kutu.kapsamNotMetin.textContent.indexOf("Geçersiz") === 0,
       marka + " geçersiz kapsam " + JSON.stringify(kotu) + ": görünür uyarı (sessiz değil)");
    ok(K.sorgu(c) === "", marka + " geçersiz kapsam TAŞINMAZ (sorgu boş)");
  }
  // GEÇERLİ ama bu markada ürünü olmayan kategori -> 0 ürün + geçerli kapsam
  const bosKat = VERI.kategoriler.find((k) => !sayfa.kartlar.some((x) => x.kat === k) &&
                                              !sayfa.butonlar.some((b) => (JSON.parse(b.katsay)[k] || 0) > 0));
  if(bosKat){
    const s = shim(sayfa);
    const c = K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(bosKat), pathname: "/" + sayfa.ad + "/"});
    ok(c.gecerli === true && gorunenKartlar(s).length === 0 && s.kutu.kapsamBos.style.display === "",
       marka + " + " + bosKat + " (geçerli ama ürünsüz): 0 ürün + boş uyarısı");
  }
}

// ============================ 5) FAIL-CLOSED: eksen OKUNAMAZSA gizle ============================
(function(){
  const marka = Object.keys(VERI.sayfalar)[0];
  const sayfa = VERI.sayfalar[marka];
  const ek = [{id: "__data-kat-yok__", kat: ""}, {id: "__data-kat-null__", kat: null}];
  const s = shim(sayfa, ek);
  K.uygula(s.dok, {search: "?kategori=Marin", pathname: "/" + sayfa.ad + "/"});
  const kacak = gorunenKartlar(s).filter((k) => !k.kat);
  ok(kacak.length === 0, "kategorisi OKUNAMAYAN kart kapsam altında GİZLENİR (kaçak: " + kacak.length + ")");
  const s2 = shim(sayfa, ek);
  K.uygula(s2.dok, {search: "", pathname: "/" + sayfa.ad + "/"});
  ok(gorunenKartlar(s2).length === sayfa.kartlar.length + ek.length,
     "kapsamsızken data-kat'sız kart GİZLENMEZ (kanonik davranış korunur)");
})();

// bozuk data-katsay -> buton gizlenir (yanlış sayı GÖSTERİLMEZ)
ok(K.sayimla("{bozuk-json", {aktif: true, gecerli: true, kategori: "Marin"}) === 0,
   "bozuk data-katsay -> 0 (fail-closed)");
ok(K.sayimla(null, {aktif: true, gecerli: true, kategori: "Marin"}) === 0,
   "eksik data-katsay -> 0 (fail-closed)");
ok(K.sayimla('{"Marin":3,"Motosiklet":5}', {aktif: false, gecerli: true, kategori: null}) === 8,
   "kapsamsızken data-katsay toplamı korunur (3+5=8)");

// ============================ 6) MODEL SAYFASI KAPSAMI ============================
(function(){
  const mf = VERI.modelSayfasi;
  if(!mf){ ok(false, "model sayfası fikstürü yok"); return; }
  const katlar = [...new Set(mf.kartlar.map((k) => k.kat))];
  const hedef = katlar[0];
  const s = shim(mf);
  K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(hedef), pathname: mf.pathname});
  ok(gorunenKartlar(s).every((k) => k.kat === hedef),
     "model sayfası kapsamı uyguluyor (" + mf.ad + " -> " + hedef + ")");
  const s2 = shim(mf);
  K.uygula(s2.dok, {search: "?kategori=Uydurma", pathname: mf.pathname});
  ok(gorunenKartlar(s2).length === 0, "model sayfası geçersiz kapsamda 0 ürün (fail-closed)");
  const s3 = shim(mf);
  K.uygula(s3.dok, {search: "", pathname: mf.pathname});
  ok(gorunenKartlar(s3).length === mf.kartlar.length, "model sayfası kanonikte DEĞİŞMEZ");
})();

// ============================ 7) ARAMA BAĞLAMI TAŞIMA — yönlendirme davranışı ============================
ok(araTasiCalistir("") === null,
   "parametresiz adreste yönlendirme YOK (kanonik sayfa dokunulmaz)");
ok(araTasiCalistir("?kategori=Otomobil") === null,
   "ara= yokken kategori tek başına yönlendirmez");
(function(){
  const h = araTasiCalistir("?ara=" + encodeURIComponent("kapı kolu"));
  ok(h !== null, "ara= varken yönlendirme TETİKLENDİ");
  if(h !== null){
    const p = new URLSearchParams(h.replace(/^\/\?/, ""));
    ok(p.get("ara") === "kapı kolu", "yönlendirilen ara= değeri korunuyor");
    ok(p.get("marka") === "Volvo", "yönlendirilen marka= bu sayfanın markası (Volvo)");
  }
})();
(function(){
  const h = araTasiCalistir("?ara=cam&kategori=Marin");
  if(h !== null){
    const p = new URLSearchParams(h.replace(/^\/\?/, ""));
    ok(p.get("ara") === "cam" && p.get("marka") === "Volvo" && p.get("kategori") === "Marin",
       "ara+marka+kategori üçü BİRDEN taşınır (bağlam kaybı yok)");
  }
})();

// ============================ 8) K117-A — KAPSAM × MODEL FİLTRESİ BİLEŞİK YÜKLEM ============================
// ÖLÇÜLEN KUSUR (mimar teşhisi): /marka/<m>/?kategori=… adresinde model çipine basılınca
// filtre uygulanıyor, ~1 sn sonra tüm katalog geri geliyor (iki süzgeç, görünürlüğün tek
// sahibi yok). HÜKÜM: görünürlük tek yüklemden türeR (`gorunur() && modelUye()`).
//
// Sentetik fikstür: 6 kart, 2 kategori × 3 model üyelik deseni.
//   a: Marin      + model 0  (kesişim)
//   b: Marin      + model 1  (yalnız model 1)
//   c: Marin      +          (data-mm YOK → fail-closed)
//   d: Otomobil   + model 0  (kesişim)
//   e: Otomobil   + model 1  (yalnız model 1)
//   f: Otomobil   +          (data-mm YOK → fail-closed)
const K117_SENTETIK = {
  kartlar: [
    {id: "a", kat: "Marin",    dataMm: "0"},
    {id: "b", kat: "Marin",    dataMm: "1"},
    {id: "c", kat: "Marin",    dataMm: ""},
    {id: "d", kat: "Otomobil", dataMm: "0"},
    {id: "e", kat: "Otomobil", dataMm: "1"},
    {id: "f", kat: "Otomobil", dataMm: ""}
  ],
  butonlar: [],
  ad: "k117a-sentetik",
  pathname: "/marka/k117a-sentetik/"
};

// Bileşik yüklemin beklentisi: yalnız A ve D (Marin ∩ model 0 + Otomobil ∩ model 0)
// görünür; kapsam yokken model 0'a basılırsa yalnız A, D görünür; data-mm'siz kartlar
// model filtresi altında GİZLİ (fail-closed). Bu fonksiyon bir K (PRUVO_KAPSAM) örneğine
// karşı 6 vakayı koşar — mutasyon turunda HER MUTASYON İÇİN çağrılır.
function k117aVakalari(K){
  const sIz = (s, ix) => K.modelSuzgeciYaz(ix);
  const sayfaAdi = K117_SENTETIK.ad;

  // Vaka 1: kapsam AKTİF (Marin) + model AKTİF (0) → yalnız kesişim (a)
  const s1 = shim(K117_SENTETIK);
  sIz(s1, 0);
  K.uygula(s1.dok, {search: "?kategori=Marin", pathname: K117_SENTETIK.pathname});
  const g1 = gorunenKartlar(s1).map((k) => k.id).sort();
  ok(g1.length === 1 && g1[0] === "a",
     "vaka 1: kapsam+model kesişim (Marin ∩ model 0 → yalnız 'a': " + g1.join(",") + ")");

  // Vaka 2: kapsam AKTİF (Marin) + model KAPALI → bugünkü davranış aynen (a, b, c)
  sIz(s1, null);
  const s2 = shim(K117_SENTETIK);
  K.uygula(s2.dok, {search: "?kategori=Marin", pathname: K117_SENTETIK.pathname});
  const g2 = gorunenKartlar(s2).map((k) => k.id).sort();
  ok(g2.length === 3 && g2.join(",") === "a,b,c",
     "vaka 2: kapsam AKTİF + model KAPALI = bugünkü davranış (Marin: a,b,c) — regresyon yok");

  // Vaka 3: kapsam KAPALI + model AKTİF (0) → yalnız model üyeleri (a, d)
  // M4 TESPİTİ: kapsam sayacı (`.mm-sayim-kart`) süzgeç açıkken YAZILMAZ; shim ilk
  // değeri (kart sayısı = "6") korunmalı. M4 (sayaç koruması kaldırıldı) ile yazılır
  // ve gorunenKart (2) basar — bu iddia kırılır.
  const s3 = shim(K117_SENTETIK);
  sIz(s3, 0);
  K.uygula(s3.dok, {search: "", pathname: K117_SENTETIK.pathname});
  const g3 = gorunenKartlar(s3).map((k) => k.id).sort();
  ok(g3.length === 2 && g3.join(",") === "a,d",
     "vaka 3: kapsam KAPALI + model AKTİF → yalnız model 0 üyeleri (a,d) — c,f GİZLİ (data-mm yok)");
  ok(s3.sayimKart.textContent === String(K117_SENTETIK.kartlar.length),
     "vaka 3: model altında kapsam sayacı YAZILMAZ (sayimKart='" + s3.sayimKart.textContent +
     "', başlangıç='" + K117_SENTETIK.kartlar.length + "' kalır)");

  // Vaka 4: kapsam KAPALI + model KAPALI → sayfaya hiç dokunulmaz (hiç style.display yazılmaz)
  sIz(s3, null);
  const s4 = shim(K117_SENTETIK);
  K.uygula(s4.dok, {search: "", pathname: K117_SENTETIK.pathname});
  const dokunma = s4.kartlar.every((k) => k.style.display === "");
  ok(dokunma,
     "vaka 4: kapsam+model KAPALI → sayfaya HİÇ dokunulmaz (tüm display='' kaldı: " + dokunma + ")");

  // Vaka 5: model AKTİF iken data-mm taşımayan kart GİZLENİR (fail-closed)
  sIz(s4, 0);
  const s5 = shim(K117_SENTETIK);
  K.uygula(s5.dok, {search: "", pathname: K117_SENTETIK.pathname});
  const dmsiz = gorunenKartlar(s5).filter((k) => !k.dataMm || k.dataMm === "").length;
  ok(dmsiz === 0,
     "vaka 5: model AKTİF + data-mm YOK = GİZLİ (kaçak data-mmsiz görünür: " + dmsiz + ")");

  // Vaka 6: geçersiz kapsam + model AKTİF → hiçbir kart görünmez (fail-closed korunur)
  sIz(s5, 0);
  const s6 = shim(K117_SENTETIK);
  K.uygula(s6.dok, {search: "?kategori=Uydurma", pathname: K117_SENTETIK.pathname});
  const g6 = gorunenKartlar(s6).length;
  ok(g6 === 0,
     "vaka 6: geçersiz kapsam + model AKTİF → 0 kart görünür (fail-closed korunur: " + g6 + ")");
  ok(s6.sayimKart.textContent === String(K117_SENTETIK.kartlar.length),
     "vaka 6: model altında kapsam sayacı YAZILMAZ (geçersiz kapsam + model 0: sayimKart='" +
     s6.sayimKart.textContent + "', başlangıç='" + K117_SENTETIK.kartlar.length + "' kalır)");
  sIz(s6, null);   // sonraki testlere temiz bırak
}
k117aVakalari(K);

// ============================ 9) MUTASYON TURU — 4 MUTANTIN HEPSİ KIRMIZI YANMALI ============================
// Her mutant: K'nın kaynak gövdesinin bir kopyası alınır, metinsel olarak değiştirilir,
// yeni bir global scope'a `eval` ile yüklenir; 6 vaka yeniden koşar. Bir mutant
// HİÇBİR vakayı kırmadan geçerse -> SURVIVOR (ölümcül). Beklenen: 4/4 mutant KIRMIZI.
//
// Mutant açıklamaları:
//   M1 — bileşik yüklemdeki `&&` -> `||`  (görünürlük birleşim yerine VEYA olur; 3 vakada kırılır)
//   M2 — modelUye: data-mm yoksa FALSE kolu -> TRUE  (data-mmsiz kartlar model altında GÖRÜNÜR; vaka 3,5 kırılır)
//   M3 — erken çıkış eski haline döner (`if(!c.aktif) return c;`)  (kapsam yokken model kolu çalışmaz; vaka 3,4,5,6 kırılır)
//   M4 — sayaç sahipliği atlanmaz (süzgeç açıkken de kapsam sayacı yazar) — bu K davranışıyla
//        doğrudan ölçülemez (sayaç yazımı GÖZLEMLENEMEZ), bu yüzden M4 yerine KODDA YOK
//        OLMAMASI gerek: model süzgeci altında `_modelSuzgeci === null` korumalı sayaç
//        bloğu KALDIRILIRSA vaka 3 ve 5'te hâlâ kırılmaz (görünürlük doğru); bu yüzden
//        M4'ü sayaç sahipliği yerine kapsam-not metninin (kapsamın KENDİ beyanı) model
//        altında BOZULMAMASI iddiasıyla değiştiriyoruz — mutant oraya `metin.textContent`
//        yazımı ekler. Ama o da gözlemlenemez. DOĞRU M4: `bolumSayaclari()` çağrısı
//        kapsam kolunda KORUNMAZ (süzgeç açıkken bile çağrılır) — gözlem sayım rozetlerinin
//        üzerinden yapılabilir; sentetik shim'imizde `.mm-sayim-kart[data-katsay]` yok,
//        ama `.mm-sayim-kart` var. Bu yeterli.
function mutantUygula(etiket, kaynak, degisiklik){
  // (0, eval) global scope'a çalıştırır -> PRUVO_KAPSAM orada tanımlanır. Eval hata
  // verirse mutant sessizce ölür; hata bilinçli olarak tetiklenebilir.
  let M = null, hata = null;
  const kod = kaynak.replace(degisiklik.eski, degisiklik.yeni);
  if(kod === kaynak){
    return {survivor: true, etiket: etiket + " (replace() eşleşmedi — mutant uygulanamadı)"};
  }
  const onceki = globalThis.PRUVO_KAPSAM;
  // 🔴 KAYNAK IIFE: `typeof window !== "undefined" ? window : globalThis`. Test akışının
  // bir noktasında `global.window = {...}` atandığı için (`araTasiCalistir`), eval
  // sonradan `window`'a yazar — biz `globalThis`'i okuyoruz. Bu sorun ORJ eval için yok
  // (window o sırada undefined). ÇÖZÜM: eval ÖNCESİ window'u gizle, sonra geri al.
  const windowOnceki = (typeof window !== "undefined") ? window : undefined;
  delete globalThis.PRUVO_KAPSAM;
  if(typeof window !== "undefined"){ delete globalThis.window; }
  try { (0, eval)(kod); }
  catch(e){ hata = String((e && e.message) || e).slice(0, 140); }
  if(windowOnceki !== undefined){ globalThis.window = windowOnceki; }
  M = globalThis.PRUVO_KAPSAM || null;
  if(onceki){ globalThis.PRUVO_KAPSAM = onceki; }
  if(!M){ return {survivor: true, etiket: etiket + " (eval hata: " + hata + ")"}; }

  // 6 vakayı bu M'ye karşı koş; mevcut `pass`/`fail` sayaçlarına dokunmadan YEREL
  // sayacla ölç (mutant turu KIRMIZI olursa asıl `fail` sayacına yazılır).
  const oncekiPass = pass, oncekiFail = fail;
  const yedekK = globalThis.PRUVO_KAPSAM;
  globalThis.PRUVO_KAPSAM = M;
  // k117aVakalari `K` parametresiyle çalışır; ikinci kez M ile çağır.
  k117aVakalari(M);
  globalThis.PRUVO_KAPSAM = yedekK;
  const yerelFail = fail - oncekiFail;
  const survivor = (yerelFail === 0);
  return {survivor: survivor, etiket: etiket, yerelFail: yerelFail};
}

const KAYNAK = VERI.kapsamJs;
const MUTANTLAR = [
  // M1: bileşik yüklemdeki && -> ||  (görünürlük birleşim yerine VEYA olur; vaka 1,3,5,6 kırılır)
  // Tam dizge değil, kaynak parçası: replace ilk eşleşmeyi alır, dosya kaynaklı olduğu
  // için unique (kart döngüsü YALNIZ burada).
  {etiket: "M1: bileşik yüklem && -> ||",
   eski: "gorunur(kartlar[i].getAttribute(\"data-kat\"), c)\n            && modelUye(kartlar[i].getAttribute(\"data-mm\"));",
   yeni: "gorunur(kartlar[i].getAttribute(\"data-kat\"), c)\n            || modelUye(kartlar[i].getAttribute(\"data-mm\"));"},
  // M2: modelUye: data-mm yoksa FALSE kolu -> TRUE  (data-mmsiz kartlar model altında GÖRÜNÜR; vaka 3,5 kırılır)
  {etiket: "M2: modelUye data-mm YOK -> true",
   eski: "if(_modelSuzgeci === null){ return true; }\n    if(!ogeMm){ return false; }",
   yeni: "if(_modelSuzgeci === null){ return true; }\n    if(!ogeMm){ return true; }"},
  // M3: erken çıkış eski haline döner (`if(!c.aktif) return c;`)  (kapsam yokken model kolu çalışmaz; vaka 3,4,5,6 kırılır)
  {etiket: "M3: erken çıkış eski haline (model kolu çalışmaz)",
   eski: "if(!c.aktif && _modelSuzgeci === null){ return c; }",
   yeni: "if(!c.aktif){ return c; }"},
  // M4: sayaç sahipliği atlanmaz (süzgeç açıkken de kapsam sayacı yazar) — model
  //     filtresinin `beyaniYaz` ile yazdığı sayıyı kapsam kolu EZEBILECEK iddiası.
  //     Sentetik shim'ımızde `.mm-sayim-kart` rozeti vardır; vaka 3'te rozet içeriği
  //     model altında 0'a (kapsam=hiç) dönerse, model 0 = "a,d" sayısıyla çelişir.
  {etiket: "M4: sayaç sahipliği kaldırıldı (süzgeç açıkken de kapsam sayacı yazar)",
   eski: "if(_modelSuzgeci === null){\n      // GERİYE DÖNÜK KOL:",
   yeni: "{\n      // GERİYE DÖNÜK KOL:"}
];

let survivorSayisi = 0;
const mutOncekiPass = pass, mutOncekiFail = fail;
for(const m of MUTANTLAR){
  const sonuc = mutantUygula(m.etiket, KAYNAK, {eski: m.eski, yeni: m.yeni});
  if(sonuc.survivor){
    survivorSayisi++;
    fail++;
    console.log("  FAIL  SURVIVOR " + m.etiket + " (mutant tüm 6 vakayı geçti — öldürücü değil)");
  }else{
    console.log("  PASS  mutant yakalandı: " + m.etiket + " (yerel fail=" + sonuc.yerelFail + ")");
  }
}
// Mutasyon turu KENDİ sayaçlarını sıfırlar: yakalanan mutantlar `k117aVakalari(M)` üzerinden
// YEREL fail üretir; bunlar global `fail`'e eklenir ama harness sonu `fail === 0 ? 0 : 1`
// ile çıkar — sayım bozulmasın diye mutasyon öncesi pass/fail'e GERİ AL.
pass = mutOncekiPass;
fail = mutOncekiFail;
ok(survivorSayisi === 0,
   "K117-A mutasyon turu: 4 mutantın HEPSİ kırmızı (SURVIVOR=" + survivorSayisi + ", beklenen 0)");

console.log("SONUC " + pass + " gecti " + fail + " kaldi");
process.exit(fail === 0 ? 0 : 1);
"""

with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
    json.dump(VERI, f, ensure_ascii=False)
    veri_yolu = f.name
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(HARNESS.replace("VERI_JSON", json.dumps(veri_yolu)))
    js_yolu = f.name
try:
    r = subprocess.run(["node", js_yolu], capture_output=True, text=True)
finally:
    os.unlink(veri_yolu)
    os.unlink(js_yolu)

sys.stdout.write(r.stdout)
if r.returncode != 0:
    kontrol("node davranış bölümü yeşil (stderr: %s)" % (r.stderr.strip()[:400] or "-"), False)
else:
    kontrol("node davranış bölümü yeşil", True)

bitir()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — MARKA SAYFASI ÜYELİĞİ (hangi ürün hangi /marka/ sayfasına girer?).

NEDEN VAR (ölçüldü, 31 Tem — SESSİZ hata sınıfı): jeneratör üyeliği HAM marka[0] ile
tanıyordu (`taninmis_mi(ham0)`), KATLANMIŞ kanonik adla değil. "Volvo Penta" (21 Marin) ve
"Mercedes-Benz" (20) ham hâlde tanınmış listede olmadığı için 41 ürün HİÇBİR marka
sayfasına girmiyordu. Hata ekranda hata gibi görünmez: ürün katalogda arandığında ÇIKAR,
ana sayfa marka çipi onu GÖSTERİR, ama /marka/volvo/ sayfasında YOKTUR — kimse bildirmez.

İKİNCİ SESSİZ HATA (aynı ölçüm): model kırılımı marka[1]'i her zaman MODEL sanıyordu. Çok
markalı uyumluluk kayıtlarında ("Peugeot"+"Citroen", "Volkswagen"+"Audi") marka[1] BAŞKA BİR
MARKA'dır; sonuç /marka/peugeot/citroen/ gibi ANLAMSIZ 33 sayfaydı (biri mojibake:
/marka/peugeot/citro-n/). Bu ürünler ikinci markanın sayfasında da GÖRÜNMÜYORDU.

⚠️ ÜYELİK EVRENİ ARTIK İKİ KAYNAKTAN TÜRER (3 Ağu, b3090492): marka sayfası evreni
TANINMIS_MARKALAR'la SINIRLI DEĞİL — anasayfa ÇİP EVRENİNDEN (tools/cip-indeks.py) de
beslenir. Küratörlük dışı ama çip olan markalar (Marin: Teleflex/Sierra/NGK/Tecnoseal/
Jabsco/International/3M/TMC/Champion/Johnson Pump/Raymarine/Sea-Doo/Sika) hem çipte hem
/marka/<slug>/ sayfasında yaşar. Bu dosyadaki üyelik yüklemi de ONLARI KAPSAMAK ZORUNDA;
kapsamazsa test kendi BAYAT evrenini "gerçek sapma" sanır ve meşru genişlemeyi kırmızı
yakar (ölçüldü 3 Ağu: E'de 13 marka / 605 ürün, F'de 727 ürün sahte kırmızı).
🔴 EVREN İKİNCİ KEZ YAZILMAZ: burada da cip-indeks.indeks_uret'ten OKUNUR — jeneratörün
kendi yardımcısından (marka_model_build.cip_evreni_markalari) DEĞİL; o okunsaydı jeneratörü
bozan mutant testi de bozar, iddia körelirdi ([[ikiz-tanim-sessiz-ayrisma]]).

KARAR (KraL):
  1. Gruplama KANONİK KATLANMIŞ adla yapılır; katlama tek kaynaktan (index.html
     TANINMIS_MARKALAR + markaKatla portu) gelir, ikinci tablo YAZILMAZ.
  2. marka[1] KENDİSİ tanınan bir marka ise MODEL sayılmaz: model kovası açılmaz, ürün her
     iki marka sayfasına da girer.
  3. Anlamsız /marka/<marka>/<başka-marka>/ sayfası ÜRETİLMEZ.
  4. Üyelik kabul kümesi = TANINMIS_MARKALAR ∪ ÇİP EVRENİ (ikisi de tek kaynaktan okunur).

NE KİLİTLER (her madde POZİTİF + NEGATİF):
  A. Katlanmış üyelik: "Volvo Penta" ürünü /marka/volvo/'da GÖRÜNÜR (poz) ·
     ham-tanınmaz/katlanınca-tanınır sınıfından HİÇBİR ürün sayfasız kalmaz (neg).
  B. Kapsam: /marka/volvo/ sayfasındaki data-kat="Marin" kart kümesi = katalogdaki
     Volvo-üyesi Marin ürün kümesi (sayı EZBERDEN değil, katalogdan ÖLÇÜLÜR) ·
     Otomobil ürünü Marin kümesine SIZMAZ (neg).
  C. marka[1] bir MARKA olan kayıt: iki marka sayfasında da var (poz) · o marka adıyla
     model kovası AÇILMAMIŞ (neg) · üretilen HİÇBİR model sayfasının display'i tanınan bir
     marka DEĞİL (genel neg).
  D. marka[1] gerçek MODEL olan kayıt: model kovası HÂLÂ açılıyor (regresyon nöbeti —
     model kırılımı SEO'nun ana ekseni) · pilot model sayfaları diskte duruyor.
  E. index.html PARİTESİ: her kanonik marka için /marka/<slug>/ (+ model sayfaları) ürün
     kümesi = index.html marka filtresinin (`some(b => markaKatla(b) === hedef)`) kümesi.
     Sapma 0 olmalı — sayfa ile ana sayfa AYNI ürünü göstermeli. Küratörlük dışı çip
     markaları (Sierra/Teleflex/...) da bu iddiaya DAHİL.
  F. Ürün sayfasındaki marka çipi hedefi BİRİNCİL markaya gider (ikincil marka çip
     haritasını EZMEZ — kararsız çıktı olmaz). BİRİNCİL = katlanmış marka[0], o da kabul
     kümesindeyse (tanınmış VEYA çip evreni); değilse ilk üye marka.

NASIL ÖLÇER: kopya mantık YOK — GERÇEK jeneratör (marka_model_build.uret) geçici bir ROOT'a
sayfaları üretir, iddialar ÜRETİLEN HTML'den okunur. Katlama tablosu (index.html
TANINMIS_MARKALAR) ya da çip evreni okunamazsa "yeşil" DENMEZ: OLCULEMEDI + exit 2.

Çalıştır:  python3 tools/marka-uyelik-test.py            (0 geçti · 1 kaldı · 2 ölçülemedi)
           python3 tools/marka-uyelik-test.py --modul /gecici/mutant.py   (mutasyon kanıtı)
"""
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

FAILS = []
BILGI = []


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
    for b in BILGI:
        print("  BILGI " + b)
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldı)" % len(FAILS))
        sys.exit(1)
    print("\nSONUC: YESIL ✅")
    sys.exit(0)


# ---------------------------------------------------------------- kaynaklar
MODUL_YOLU = os.path.join(TOOLS, "marka_model_build.py")
if "--modul" in sys.argv:
    MODUL_YOLU = sys.argv[sys.argv.index("--modul") + 1]

try:
    import build
except Exception as e:                                        # noqa: BLE001
    olculemedi("build import edilemedi: %r" % (e,))

try:
    _spec = importlib.util.spec_from_file_location("mm_uyelik", MODUL_YOLU)
    mm = importlib.util.module_from_spec(_spec)
    sys.modules["mm_uyelik"] = mm
    _spec.loader.exec_module(mm)
except Exception as e:                                        # noqa: BLE001
    olculemedi("jeneratör (%s) import edilemedi: %r" % (MODUL_YOLU, e))

try:
    with open(build.JSON_PATH, encoding="utf-8") as f:
        PRODUCTS = json.load(f)
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        INDEX_HTML = f.read()
except Exception as e:                                        # noqa: BLE001
    olculemedi("katalog/index.html okunamadı: %r" % (e,))

if not PRODUCTS:
    olculemedi("urunler.json BOŞ (üyelik ölçülemez)")

# KATLAMA TABLOSU okunamazsa YEŞİL DEME (fail-closed).
try:
    EVREN = mm.MarkaEvreni(INDEX_HTML)
except SystemExit as e:                                       # noqa: BLE001
    olculemedi("katlama tablosu (index.html TANINMIS_MARKALAR) okunamadı: %r" % (e,))
except Exception as e:                                        # noqa: BLE001
    olculemedi("MarkaEvreni kurulamadı: %r" % (e,))
if not getattr(EVREN, "taninmis", None) or len(EVREN.taninmis) < 20:
    olculemedi("tanınmış marka listesi şüpheli küçük (%d) — katlama ölçülemez"
               % len(getattr(EVREN, "taninmis", []) or []))

# Jeneratör de katlama tablosu OKUNAMAZKEN fail-closed mu (sessizce boş evrene düşmesin)?
try:
    mm.MarkaEvreni(INDEX_HTML.replace("var TANINMIS_MARKALAR = [", "var BOZUK_LISTE = ["))
    _failclosed = False
except SystemExit:
    _failclosed = True
except Exception:                                             # noqa: BLE001
    _failclosed = True
kontrol("katlama tablosu YOKKEN jeneratör fail-closed (sessiz boş evrene düşmüyor)",
        _failclosed)

# ÇİP EVRENİ — üyelik kabul kümesinin İKİNCİ yarısı. Jeneratörün kendi yardımcısından DEĞİL,
# çipin GERÇEK kaynağından (tools/cip-indeks.py) okunur: jeneratörü bozan mutant testin
# beklentisini de bozarsa iddia körelir ([[ikiz-tanim-sessiz-ayrisma]]).
try:
    _cs = importlib.util.spec_from_file_location("ci_uyelik",
                                                 os.path.join(TOOLS, "cip-indeks.py"))
    _ci = importlib.util.module_from_spec(_cs)
    _cs.loader.exec_module(_ci)
    _IX = _ci.indeks_uret(PRODUCTS, INDEX_HTML)
    CIP_EVRENI = set(b for kd in _IX["kat"].values() for b in kd)
except Exception as e:                                        # noqa: BLE001
    olculemedi("çip evreni (tools/cip-indeks.py) okunamadı: %r" % (e,))
if not CIP_EVRENI:
    olculemedi("çip evreni BOŞ — üyelik kabul kümesi ölçülemez (fail-closed)")

# Kabul kümesi GERÇEKTEN genişlemiş mi? Küratörlük dışı çip markası yoksa E/F'nin genişletilmiş
# ekseni ölçülmüyor demektir — "sapma 0" o hâlde iddia değil, boş kümenin sessizliğidir.
KURATORLUK_DISI = sorted(b for b in CIP_EVRENI if not EVREN.taninmis_mi(b))
BILGI.append("çip evreni: %d marka · küratörlük DIŞI: %d %s"
             % (len(CIP_EVRENI), len(KURATORLUK_DISI), KURATORLUK_DISI[:6]))
kontrol("küratörlük DIŞI çip markası sınıfı BOŞ DEĞİL (genişletilmiş eksen ölçülüyor)",
        bool(KURATORLUK_DISI))


def katla(x):
    return EVREN.katla((x or "").strip())


def kabul_mu(k):
    """Üyelik kabul kümesi = TANINMIS_MARKALAR ∪ ÇİP EVRENİ (tek kaynaktan, iki yarı)."""
    return EVREN.taninmis_mi(k) or k in CIP_EVRENI


def uyeler_js(p):
    """index.html marka FİLTRESİNİN yüklemi: some(b => markaKatla(b) === hedef)."""
    out = []
    for b in (p.get("marka") or []):
        k = katla(b)
        if k and kabul_mu(k) and k not in out:
            out.append(k)
    return out


URUN_KAT = {p["id"]: (p.get("kategori") or "").strip() for p in PRODUCTS if p.get("id")}
URUN = {p["id"]: p for p in PRODUCTS if p.get("id")}

# ---------------------------------------------------------------- GERÇEK üretim
KART_RE = re.compile(r'<div class="card" data-kat="([^"]*)"><a class="card-main" href="([^"]+)"')
ID_RE = re.compile(r"/urun/([^/]+)/")

TMP = tempfile.mkdtemp(prefix="marka-uyelik-")
try:
    ctx = build.marka_model_ctx()
    ctx["ROOT"] = TMP
    with open(os.path.join(TMP, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    try:
        SONUC = mm.uret(PRODUCTS, ctx)
    except Exception as e:                                    # noqa: BLE001
        shutil.rmtree(TMP, ignore_errors=True)
        olculemedi("marka_model_build.uret çöktü: %r" % (e,))

    SITE = ctx["SITE"]
    URLLER = [loc[len(SITE):] for loc, _a, _b in SONUC["sitemap"]]
    MARKA_URL = [u for u in URLLER if u.count("/") == 3 and u != "/marka/"]
    MODEL_URL = [u for u in URLLER if u.count("/") == 4]

    SAYFA = {}          # url -> [(urun_id, data_kat), ...]
    for u in URLLER:
        yol = os.path.join(TMP, *u.strip("/").split("/"), "index.html")
        if not os.path.isfile(yol):
            continue
        with open(yol, encoding="utf-8") as fh:
            h = fh.read()
        kart = []
        for kat, href in KART_RE.findall(h):
            m = ID_RE.search(href)
            if m:
                kart.append((m.group(1), kat.replace("&amp;", "&")))
        SAYFA[u] = kart
finally:
    shutil.rmtree(TMP, ignore_errors=True)

kontrol("jeneratör marka sayfası üretti (%d marka, %d model)"
        % (len(MARKA_URL), len(MODEL_URL)), len(MARKA_URL) > 0 and len(MODEL_URL) > 0)

# marka slug -> kanonik marka
SLUG_MARKA = {mm._slug(m): m for m in SONUC["slug_map"]}
# kanonik marka -> sayfada görünen ürün id kümesi (marka sayfası + model sayfaları)
MARKA_URUNLERI = {}
for u in URLLER:
    if u == "/marka/":
        continue
    slug = u.strip("/").split("/")[1]
    marka = SLUG_MARKA.get(slug)
    if marka is None:
        continue
    s = MARKA_URUNLERI.setdefault(marka, set())
    s.update(pid for pid, _k in SAYFA.get(u, ()))

# ==================================================== A) KATLANMIŞ ÜYELİK
# Sınıf: HAM marka[0] tanınmıyor ama KATLANINCA tanınıyor ("Volvo Penta", "Mercedes-Benz").
SINIF = [p for p in PRODUCTS
         if (p.get("marka") or [])
         and not EVREN.taninmis_mi((p["marka"][0] or "").strip())
         and EVREN.taninmis_mi(katla(p["marka"][0]))]
BILGI.append("katlanan-marka[0] sınıfı: %d ürün (ham0 tanınmaz, katla->tanınır)" % len(SINIF))
kontrol("katlanan-marka[0] sınıfı BOŞ DEĞİL (iddia gerçekten ölçülüyor)", len(SINIF) > 0)

sayfasiz = [p["id"] for p in SINIF
            if p.get("id") and not any(p["id"] in s for s in MARKA_URUNLERI.values())]
kontrol("NEG: katlanan-marka[0] sınıfından HİÇBİR ürün sayfasız değil (sayfasız: %d/%d)"
        % (len(sayfasiz), len(SINIF)), not sayfasiz)

vp = [p for p in SINIF if katla(p["marka"][0]) == "Volvo" and p.get("id")]
kontrol("POZ: 'Volvo Penta' sınıfı ürünleri /marka/volvo/ evreninde (%d ürün)" % len(vp),
        bool(vp) and all(p["id"] in MARKA_URUNLERI.get("Volvo", set()) for p in vp))

# ==================================================== B) KAPSAM (marka × kategori)
volvo_url = "/marka/volvo/"
volvo_kart = SAYFA.get(volvo_url, [])
kontrol("/marka/volvo/ üretildi ve kart taşıyor", bool(volvo_kart))
# data-kat = ürünün GERÇEK kategorisi (uydurma eksen değil)
yanlis_kat = [pid for pid, kat in volvo_kart if pid in URUN_KAT and URUN_KAT[pid] != kat]
kontrol("/marka/volvo/ data-kat = ürünün gerçek kategorisi (sapma: %d)" % len(yanlis_kat),
        not yanlis_kat)

# Volvo × Marin: sayfadaki küme = KATALOGDAN ölçülen küme (sayı ezberden YAZILMAZ)
volvo_sayfa_marin = {pid for pid, kat in volvo_kart if kat == "Marin"}
volvo_katalog_marin = {p["id"] for p in PRODUCTS
                       if p.get("id") and (p.get("kategori") or "").strip() == "Marin"
                       and "Volvo" in uyeler_js(p)}
BILGI.append("Volvo × Marin: sayfada %d · katalogda %d"
             % (len(volvo_sayfa_marin), len(volvo_katalog_marin)))
kontrol("POZ: /marka/volvo/?kategori=Marin kümesi katalogla BİREBİR (%d ürün)"
        % len(volvo_katalog_marin),
        len(volvo_katalog_marin) > 0 and volvo_sayfa_marin == volvo_katalog_marin)
sizan = [pid for pid in volvo_sayfa_marin if URUN_KAT.get(pid) != "Marin"]
kontrol("NEG: Marin kapsamına Marin-DIŞI Volvo ürünü sızmıyor (sızan: %d)" % len(sizan),
        not sizan)
volvo_oto = {pid for pid, kat in volvo_kart if kat == "Otomobil"}
kontrol("NEG: /marka/volvo/ Otomobil ürünü de taşıyor ama Marin kümesinde DEĞİL (%d oto)"
        % len(volvo_oto), bool(volvo_oto) and not (volvo_oto & volvo_sayfa_marin))

# ==================================================== C) marka[1] BİR MARKA
cok_marka = [p for p in PRODUCTS
             if p.get("id") and len(p.get("marka") or []) > 1
             and mm.marka_mi((p["marka"][1] or "").strip(), EVREN)
             and katla(p["marka"][1]) != katla(p["marka"][0])
             and EVREN.taninmis_mi(katla(p["marka"][0]))]
BILGI.append("çok-markalı uyumluluk kaydı (marka[1] = başka MARKA): %d ürün" % len(cok_marka))
kontrol("çok-markalı kayıt sınıfı BOŞ DEĞİL (iddia gerçekten ölçülüyor)", bool(cok_marka))

iki_sayfa_yok = []
for p in cok_marka:
    a, b = katla(p["marka"][0]), katla(p["marka"][1])
    if a not in MARKA_URUNLERI or b not in MARKA_URUNLERI:
        continue                       # markanın sayfası yoksa (<ESIK) iddia edilemez
    if not (p["id"] in MARKA_URUNLERI[a] and p["id"] in MARKA_URUNLERI[b]):
        iki_sayfa_yok.append((p["id"], a, b))
kontrol("POZ: çok-markalı ürün HER İKİ marka sayfasında da var (eksik: %d)"
        % len(iki_sayfa_yok), not iki_sayfa_yok)

# NEG: üretilen HİÇBİR model sayfasının adı tanınan bir MARKA olmasın
veri = mm.gruplandir(PRODUCTS, EVREN)
anlamsiz = []
for marka, d in veri.items():
    for g in d["gruplar"].values():
        if len(g["urunler"]) < mm.ESIK:
            continue
        if EVREN.taninmis_mi(g["display"]) or EVREN.taninmis_mi(g["slug"].replace("-", " ")):
            anlamsiz.append("/marka/%s/%s/" % (mm._slug(marka), g["slug"]))
kontrol("NEG: MARKA adıyla model sayfası ÜRETİLMİYOR (bulunan: %d %s)"
        % (len(anlamsiz), anlamsiz[:4]), not anlamsiz)
kontrol("NEG: /marka/peugeot/citroen/ ve /marka/volkswagen/audi/ ÜRETİLMİYOR",
        "/marka/peugeot/citroen/" not in MODEL_URL
        and "/marka/volkswagen/audi/" not in MODEL_URL)

# ==================================================== D) marka[1] GERÇEK MODEL (regresyon)
model_kovasindaki = set()
for marka, d in veri.items():
    for g in d["gruplar"].values():
        model_kovasindaki.update(p.get("id") for p in g["urunler"])
kovasiz = []
gercek_model = 0
for p in PRODUCTS:
    m = p.get("marka") or []
    if not p.get("id") or len(m) < 2:
        continue
    m1 = (m[1] or "").strip()
    if not m1 or mm.marka_mi(m1, EVREN):
        continue
    birincil = katla(m[0])
    if not EVREN.taninmis_mi(birincil):
        continue
    if not mm._strip_marka_oneki(birincil, m1, EVREN):
        continue                        # marka[1] tümüyle marka öneki -> marka-only (doğru)
    gercek_model += 1
    if p["id"] not in model_kovasindaki:
        kovasiz.append(p["id"])
BILGI.append("marka[1] GERÇEK MODEL olan kayıt: %d ürün" % gercek_model)
kontrol("POZ: marka[1] gerçek MODEL olan HER kayıt model kovasında (kovasız: %d/%d)"
        % (len(kovasiz), gercek_model), gercek_model > 0 and not kovasiz)
pilot = ["/marka/ford/focus/", "/marka/ford/f-150/", "/marka/bmw/e46/", "/marka/peugeot/206/"]
eksik_pilot = [u for u in pilot if u not in MODEL_URL]
kontrol("POZ: pilot model sayfaları duruyor (eksik: %s)" % (eksik_pilot or "-"),
        not eksik_pilot)
BILGI.append("model sayfası: %d · marka sayfası: %d" % (len(MODEL_URL), len(MARKA_URL)))

# ==================================================== E) index.html FİLTRE PARİTESİ
js_kume = {}
for p in PRODUCTS:
    if not p.get("id"):
        continue
    for k in uyeler_js(p):
        js_kume.setdefault(k, set()).add(p["id"])
sapan = []
for marka, sayfa_ids in MARKA_URUNLERI.items():
    bekl = js_kume.get(marka, set())
    if sayfa_ids != bekl:
        sapan.append((marka, len(bekl - sayfa_ids), len(sayfa_ids - bekl)))
kontrol("POZ: /marka/<X>/ ürün kümesi = index.html marka filtresi (sapan marka: %d %s)"
        % (len(sapan), sapan[:4]), not sapan)
# NEG: sayfası olan her markanın kümesi BOŞ olmasın (sessiz boşalma nöbeti)
bos = [m for m, s in MARKA_URUNLERI.items() if not s]
kontrol("NEG: sayfası olan hiçbir marka BOŞ değil (boş: %d)" % len(bos), not bos)

# ==================================================== F) çip haritası birincil markada
cip = SONUC.get("product_chip_map", {})
yanlis_cip = []
for pid, yol in cip.items():
    p = URUN.get(pid)
    if not p:
        continue
    slug = yol.strip("/").split("/")[1]
    hedef = SLUG_MARKA.get(slug)
    ham0 = katla((p.get("marka") or [""])[0])
    birincil = ham0 if kabul_mu(ham0) else (uyeler_js(p) or [None])[0]
    if hedef != birincil:
        yanlis_cip.append((pid, hedef, birincil))
kontrol("POZ: ürün çip haritası BİRİNCİL markaya gidiyor (sapan: %d %s)"
        % (len(yanlis_cip), yanlis_cip[:3]), not yanlis_cip)

bitir()

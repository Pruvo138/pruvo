#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFIGUR KABUL TESTI — konfigüre edilebilir DEKOR ürünü altyapısı (renk + boy kaydırıcı).

Kapsam (tools/build.py "konfigur" alanı + /konfigur.js + secenekler.js konfigur bayrağı):
  (a) ŞEMA: konfigur_dogrula geçerli şemayı kabul eder; bozuk mutantların HER BİRİNİ
      (min>=varsayilan, boş renkler, 'Diğer', bilinmeyen renk, hacim ref <=0, kötü görsel
      indeksi, fiyatsız ürün, parametrik:true birlikteliği...) reddeder. render_product
      geçersiz konfigur'da SystemExit ile DÜŞER (fail-closed — yanlış fiyat sessizce yayınlanamaz).
  (b) FİYAT (afin çapa modeli, mimar TUR-3): node ile GERÇEK /konfigur.js koşulur
      (kopya/taklit yok): fiyat 6 cm'den itibaren KESİN ARTAN, çapalar TAM tutar
      (6 cm = 150,00 TL · 30 cm = 1.300,00 TL), minimumun altına inilmez, tüm fiyatlar
      TAM TL, çapadan çözülen birim/sabit mimar türetimiyle örtüşür (≈1,2306 TL/cm³ /
      ≈140,72 TL) ve build.py'deki Python aynası (JS öncesi fiyat metni) node sonuçlarıyla
      kuruşu kuruşuna aynıdır (drift nöbeti). 6/10/15/20/25/30 cm tablosu rapor için basılır.
  (c) GERİ UYUMLULUK — konfigur'suz ürün sayfaları (panelsiz şemasız-Jeneratör, kart-seçim
      fonksiyonel, boy_secenekli, lisanslı, parametrik sarı). DÖRT AYRI İDDİA; ilk üçü
      REFERANSSIZ ve KALICI (CI'da kırmızı yakabilir), dördüncüsü referansa bağlı:
        c1 İZ YOKLUĞU (referanssız): konfigur'a ÖZGÜ hiçbir kanca konfigur'suz sayfaya
           sızmaz (URUN_KONFIGUR / konfigur.js / PRUVO_KONFIGUR / kaydırıcı / data-gorsel
           + malzeme EKSENİ kancaları #malzemeButonlar / .malzeme-btn / data-katsayi).
        c2 YAPISAL ÇEKİRDEK (referanssız, SAYFA BAZLI): her sayfa sınıfı kendi kimlik
           kancalarını KORUR (#filCipler, KART_SECIM bayrağı, #opsiyonlar / büyük buton,
           #boySec, .attribution, jenerator modülleri). SAYI ÇAPASI YOK: "en az 1" / "hiç
           yok" aranır; metin/CSS/kategori düzenlemesi bunları oynatmaz.
        c3 MALZEME ARAYÜZÜ XOR (referanssız, TÜM sayfalarda): her ürün sayfasında malzeme
           arayüzü TAM OLARAK BİR biçimdedir — konfigur+malzemeli sayfa #malzemeButonlar
           (kart bölümü YOK), diğer HER sayfa #filCipler (seçici YOK). Hem "çift-UI"yı
           hem de "konfigur'un kart gizlemesi tüm katalogda tetiklendi" sızıntısını yakar.
        c4 BAYT-EŞİTLİK (REFERANSA BAĞLI — DAL-İÇİ, BLOKLAMAZ): konfigur'suz sayfalar
           merge-base'deki ESKİ build.py çıktısıyla bayt-eşit mi? Bu bir DEĞİŞİM
           dedektörüdür, konfigur EKSENİNİ ölçmez: ana hatta (merge-base == HEAD ->
           referans build.py çalışanla AYNI) karşılaştırma TOTOLOJİdir, dalda ise her
           meşru build.py düzenlemesinde (CSS/metin/JSON-LD) ayrışır. Bu yüzden hard-red
           DEĞİL: ölçülemediğinde ⚪ ÖLÇÜLEMEDİ (çıkış 2, --anahat ile bloklamaz),
           ölçülüp ayrıştığında ⚠️ UYARI. Kalıcı koruma c1/c2/c3'tedir.
  (d) KONFIGUR SAYFASI: JSON-LD Offer.price = taban (EN KÜÇÜK boyun) fiyatı, Merchant
      feed aynı fiyatla basılır; sayfada URUN_KONFIGUR + /konfigur.js?v= + renk butonları
      (data-gorsel) + kaydırıcı + kancalar vardır; 'Diğer'/renkOzel ve büyük butonlar YOKTUR;
      JS öncesi fiyat metni varsayılan boyun kuruşlu fiyatıdır.

Offline (ağ yok), gerçek urunler.json OKUNMAZ (sentetik fikstürler), repo dosyasına YAZMAZ.
node ZORUNLU (deploy.yml setup-node kurar); yoksa FAIL-CLOSED kırmızı.

ÇIKIŞ KODLARI (repo sözleşmesi — parite-ege.js / faz3-gecikme.js ile aynı):
  0 = YEŞİL       — bütün KALICI iddialar ölçüldü ve geçti.
  1 = KIRMIZI     — en az bir KALICI iddia (a/b/c1/c2/c3/d/e) ihlal edildi.
  2 = ÖLÇÜLEMEDİ  — kalıcı iddialar yeşil ama c4'ün referansı alınamadı/totoloji
                    (ne yeşil ne kırmızı). "--anahat" verilirse 2 yerine 0 döner.

Kullanım:
  python3 tools/konfigur-test.py             # geliştirici / dal: ölçülemedi = çıkış 2
  python3 tools/konfigur-test.py --anahat    # ANA HAT (deploy.yml): c4 yapısal olarak
                                             # ölçülemez (merge-base == HEAD) -> ⚪ raporlanır,
                                             # yayını KİLİTLEMEZ; koruma c1/c2/c3'te.
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build  # noqa: E402

HATALAR = []        # KALICI iddia ihlali -> çıkış 1 (KIRMIZI)
UYARILAR = []       # ölçüldü ama BLOKLAMAYAN bulgu (c4 ayrışması) -> çıkış kodunu etkilemez
OLCULEMEDI = []     # ölçüm yapılamadı (referans yok / totoloji) -> çıkış 2 (--anahat ile 0)


def kontrol(kosul, mesaj):
    if kosul:
        print("  ✅ " + mesaj)
    else:
        print("  ❌ " + mesaj)
        HATALAR.append(mesaj)


def uyar(mesaj):
    """BLOKLAMAYAN bulgu: ölçüldü, ihlal olabilir ama yanlış-pozitif riski yüksek eksen."""
    print("  ⚠️  " + mesaj)
    UYARILAR.append(mesaj)


def olculemedi(mesaj):
    """SESSİZ YEŞİL YASAK: ölçüm yapılamadıysa 'geçti' deme, ÖLÇÜLEMEDİ de."""
    print("  ⚪ ÖLÇÜLEMEDİ — " + mesaj)
    OLCULEMEDI.append(mesaj)


# ------------------------------------------------------------------ fikstürler
GORSELLER = [
    "https://media.pruvo3d.com/urunler/test-kurt-siyah-1.jpg",
    "https://media.pruvo3d.com/urunler/test-kurt-beyaz-1.jpg",
    "https://media.pruvo3d.com/urunler/test-kurt-gri-1.jpg",
]

KURT_KONFIGUR = {
    "renkler": ["Siyah", "Beyaz", "Gri"],
    "renkGorselIndeks": {"Siyah": 0, "Beyaz": 1, "Gri": 2},
    "boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150, "etiket": "Yükseklik"},
    "hacim": {"refYukseklikMm": 1899.739, "refHacimCm3": 239222.8},
    # Afin fiyat modeli çapaları (mimar TUR-3, Okan onaylı band): 6 cm = 150 TL,
    # 30 cm = 1300 TL -> birim ≈ 1,2306 TL/cm³, sabit ≈ 140,72 TL (koddan çözülür).
    "fiyatCapalari": [[60, 150], [300, 1300]],
}
TABAN_TL = 150      # çapa-1 fiyatı = "fiyat" alanı = JSON-LD/feed minimum fiyatı
CAPA2_TL = 1300     # çapa-2 (en büyük boy) fiyatı

# MALZEME EKSENİ (Okan KESİN katsayılar; ABS+Karbon SATIŞA KAPALI -> KOYULMAZ):
#   PLA 1.00 (taban/varsayılan) · PETG 1.30 · ASA 1.60.
# Katsayılar secenekler.js FILAMENT_FARK tek kaynağıyla örtüşür (konfigur_dogrula doğrular).
MALZEMELER = [{"ad": "PLA", "katsayi": 1.0},
              {"ad": "PETG", "katsayi": 1.3},
              {"ad": "ASA", "katsayi": 1.6}]
KURT_KONFIGUR_MALZEME = dict(KURT_KONFIGUR, malzemeler=[dict(m) for m in MALZEMELER],
                             varsayilanMalzeme="PLA")


def urun(konfigur=None, **ek):
    p = {
        "id": "test-dekor-kurt-figuru",
        "kategori": "Dekorasyon",
        "marka": [],
        "baslik": "Dekoratif Kurt Figürü",
        "aciklama": "Özel tasarım dekoratif figür. Farklı renk seçenekleriyle üretilir.\n"
                    "Yaklaşık dış ölçüler: 60 × 40 × 150 mm",
        "fiyat": "150 TL",
        "gorseller": list(GORSELLER),
    }
    if konfigur is not None:
        p["konfigur"] = copy.deepcopy(konfigur)
    p.update(ek)
    return p


# ------------------------------------------------------------------ (a) şema doğrulaması
def test_sema():
    print("\n(a) KONFIGUR ŞEMA DOĞRULAMASI")
    kontrol(build.konfigur_dogrula(urun(KURT_KONFIGUR)) == [],
            "geçerli konfigur şeması hatasız kabul edilir")

    def mutant(ad, degistir, urun_degistir=None):
        p = urun(KURT_KONFIGUR)
        if urun_degistir:
            urun_degistir(p)
        degistir(p["konfigur"])
        hatalar = build.konfigur_dogrula(p)
        kontrol(bool(hatalar), "mutant reddedilir: %s (%s)"
                % (ad, hatalar[0] if hatalar else "HATA YOK — sessiz kabul!"))

    mutant("min >= varsayilan", lambda k: k["boyutMm"].update({"min": 150}))
    mutant("varsayilan > max", lambda k: k["boyutMm"].update({"varsayilan": 400}))
    mutant("adim 0", lambda k: k["boyutMm"].update({"adim": 0}))
    mutant("max adıma oturmuyor", lambda k: k["boyutMm"].update({"max": 305}))
    mutant("etiket boş", lambda k: k["boyutMm"].update({"etiket": " "}))
    mutant("renkler boş", lambda k: k.update({"renkler": []}))
    mutant("renkler 'Diğer' içeriyor", lambda k: k.update(
        {"renkler": ["Siyah", "Diğer"], "renkGorselIndeks": {"Siyah": 0, "Diğer": 1}}))
    mutant("bilinmeyen renk", lambda k: k.update(
        {"renkler": ["Mor"], "renkGorselIndeks": {"Mor": 0}}))
    mutant("hacim ref yüksekliği 0", lambda k: k["hacim"].update({"refYukseklikMm": 0}))
    mutant("hacim ref hacmi negatif", lambda k: k["hacim"].update({"refHacimCm3": -1}))
    mutant("renkGorselIndeks eksik anahtar", lambda k: k["renkGorselIndeks"].pop("Gri"))
    mutant("görsel indeksi aralık dışı", lambda k: k["renkGorselIndeks"].update({"Gri": 9}))
    mutant("fiyat alanı boş (minimum fiyat yok)", lambda k: None,
           urun_degistir=lambda p: p.update({"fiyat": ""}))
    mutant("fiyat alanı çapa-1'den farklı", lambda k: None,
           urun_degistir=lambda p: p.update({"fiyat": "200 TL"}))
    mutant("parametrik:true birlikteliği", lambda k: None,
           urun_degistir=lambda p: p.update({"parametrik": True}))
    mutant("fiyatCapalari eksik", lambda k: k.pop("fiyatCapalari"))
    mutant("fiyatCapalari tek çapa", lambda k: k.update({"fiyatCapalari": [[60, 150]]}))
    mutant("capa1 en küçük boyda değil", lambda k: k.update(
        {"fiyatCapalari": [[100, 150], [300, 1300]]}))
    mutant("capa2.boy > max", lambda k: k.update(
        {"fiyatCapalari": [[60, 150], [400, 1300]]}))
    mutant("çapa fiyatları artan değil", lambda k: k.update(
        {"fiyatCapalari": [[60, 1300], [300, 150]]}))
    mutant("çapada negatif değer", lambda k: k.update(
        {"fiyatCapalari": [[60, -150], [300, 1300]]}))

    # --- MALZEME EKSENİ şeması (opsiyonel alan; varsa fail-closed) ---
    kontrol(build.konfigur_dogrula(urun(KURT_KONFIGUR_MALZEME)) == [],
            "geçerli MALZEME ekseni (PLA/PETG/ASA) hatasız kabul edilir")

    def mutant_m(ad, degistir):
        p = urun(KURT_KONFIGUR_MALZEME)
        degistir(p["konfigur"])
        hatalar = build.konfigur_dogrula(p)
        kontrol(bool(hatalar), "malzeme mutant reddedilir: %s (%s)"
                % (ad, hatalar[0] if hatalar else "HATA YOK — sessiz kabul!"))

    mutant_m("varsayilanMalzeme eksik", lambda k: k.pop("varsayilanMalzeme"))
    mutant_m("varsayilanMalzeme listede yok",
             lambda k: k.update({"varsayilanMalzeme": "TPU"}))
    mutant_m("malzemeler boş liste", lambda k: k.update({"malzemeler": []}))
    mutant_m("malzemeler öğesi obje değil",
             lambda k: k.update({"malzemeler": ["PLA", "PETG"]}))
    mutant_m("satışa kapalı malzeme (Karbon)", lambda k: k["malzemeler"].append(
        {"ad": "Karbon", "katsayi": 2.0}))
    mutant_m("satışa kapalı malzeme (ABS)", lambda k: k["malzemeler"].append(
        {"ad": "ABS", "katsayi": 1.5}))
    mutant_m("bilinmeyen malzeme adı", lambda k: k["malzemeler"].append(
        {"ad": "Naylon", "katsayi": 1.4}))
    mutant_m("PETG katsayısı yanlış (1.30!=1.50 — drift)",
             lambda k: k["malzemeler"].__setitem__(1, {"ad": "PETG", "katsayi": 1.5}))
    mutant_m("PLA katsayısı yanlış (1.00!=1.10)",
             lambda k: k["malzemeler"].__setitem__(0, {"ad": "PLA", "katsayi": 1.1}))
    mutant_m("katsayı ≤ 0", lambda k: k["malzemeler"].__setitem__(
        0, {"ad": "PLA", "katsayi": 0}))
    mutant_m("mükerrer malzeme adı", lambda k: k["malzemeler"].append(
        {"ad": "PLA", "katsayi": 1.0}))
    # En düşük malzeme (PLA 1.00) olmadan "fiyat"=150 min offer beyanı YALAN olur:
    mutant_m("PLA yok -> min offer (195) != fiyat (150)",
             lambda k: k.update({"malzemeler": [{"ad": "PETG", "katsayi": 1.3},
                                                 {"ad": "ASA", "katsayi": 1.6}],
                                 "varsayilanMalzeme": "PETG"}))

    # render_product fail-closed: geçersiz konfigur build'i DÜŞÜRÜR
    bozuk = urun(KURT_KONFIGUR)
    bozuk["konfigur"]["boyutMm"]["min"] = 500
    try:
        build.render_product(bozuk, [bozuk])
        kontrol(False, "render_product geçersiz konfigur'da SystemExit vermeli (sessiz üretti!)")
    except SystemExit:
        kontrol(True, "render_product geçersiz konfigur'da SystemExit ile düşer (fail-closed)")


# ------------------------------------------------------------------ (b) fiyat (gerçek JS, node)
NODE_RUNNER = r"""
"use strict";
var KONFIGUR = require(process.argv[2]);        // /konfigur.js modülü (gerçek dosya)
var k = JSON.parse(process.argv[3]);            // konfigur şeması (fiyatCapalari dahil)
var kat = process.argv[4];                      // opsiyonel malzeme katsayısı ("" -> 2-arg çağrı)
var useKat = (kat !== undefined && kat !== "");
var b = k.boyutMm, seri = [];
for (var boy = b.min; boy <= b.max + 1e-9; boy += b.adim) {
  var kurus = useKat ? KONFIGUR.fiyatKurus(k, boy, parseFloat(kat))
                     : KONFIGUR.fiyatKurus(k, boy);   // 2-arg = PLA/malzemesiz identity
  seri.push({ boy: boy, kurus: kurus });
}
process.stdout.write(JSON.stringify({ seri: seri, model: KONFIGUR.fiyatModeli(k) }));
"""


def _node_seri(node, konfigur, kat_arg=""):
    """/konfigur.js'i node ile koşup boy serisini (kuruş) döndürür. kat_arg="" -> 2-arg
    (PLA/malzemesiz identity); "1.3"/"1.6" -> o katsayıyla. (seri, model) döner (hata -> None)."""
    tmp = tempfile.mkdtemp(prefix="konfigur-test-")
    runner = os.path.join(tmp, "runner.js")
    with open(runner, "w", encoding="utf-8") as f:
        f.write(NODE_RUNNER)
    try:
        r = subprocess.run(
            [node, runner, os.path.join(ROOT, "konfigur.js"), json.dumps(konfigur), kat_arg],
            capture_output=True, text=True, timeout=60)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        return None, r.stderr.strip() or "-"
    sonuc = json.loads(r.stdout)
    return (sonuc["seri"], sonuc.get("model") or {}), None


def test_fiyat():
    print("\n(b) AFİN FİYAT MODELİ + MALZEME KATSAYISI — kesin artanlık + çapa/katsayı "
          "doğruluğu (node ile gerçek /konfigur.js)")
    node = shutil.which("node")
    kontrol(bool(node), "node bulunur (FAIL-CLOSED ön koşul — deploy.yml setup-node kurar)")
    if not node:
        return None

    taban, hata = _node_seri(node, KURT_KONFIGUR, "")   # 2-arg = PLA/malzemesiz identity
    kontrol(taban is not None, "node koşumu başarılı (stderr: %s)" % (hata or "-"))
    if taban is None:
        return None
    seri, model = taban

    bm = KURT_KONFIGUR["boyutMm"]
    beklenen_adet = int(round((bm["max"] - bm["min"]) / bm["adim"])) + 1
    kontrol(len(seri) == beklenen_adet,
            "tüm kaydırıcı adımları hesaplandı (%d/%d)" % (len(seri), beklenen_adet))
    kontrol(all(x["kurus"] is not None and x["kurus"] > 0 for x in seri),
            "her boyda pozitif fiyat üretilir")
    kontrol(seri[0]["kurus"] == TABAN_TL * 100,
            "ÇAPA-1: en küçük boyda (6 cm) fiyat TAM %s" % build.taban_fiyat_metni(TABAN_TL))
    kontrol(seri[-1]["kurus"] == CAPA2_TL * 100,
            "ÇAPA-2: en büyük boyda (30 cm) fiyat TAM %s" % build.taban_fiyat_metni(CAPA2_TL))
    kontrol(all(seri[i]["kurus"] > seri[i - 1]["kurus"] for i in range(1, len(seri))),
            "fiyat 6 cm'den itibaren KESİN ARTAN (düz-bölge artefaktı yok)")
    kontrol(all(x["kurus"] >= TABAN_TL * 100 for x in seri),
            "hiçbir boyda minimum (çapa-1) fiyatın altına inilmez")
    kontrol(all(x["kurus"] % 100 == 0 for x in seri),
            "görünen fiyat TAM TL'ye yuvarlanır (kuruş küsuratı yok)")

    # sabit/birim elle yazılmadı, çapadan çözüldü — mimarın verdiği değerlerle örtüşme.
    kontrol(abs(model.get("birim", 0) - 1.2306) < 0.001 and
            abs(model.get("sabit", 0) - 140.72) < 0.01,
            "çapadan çözülen model mimar türetimiyle örtüşür (birim=%.4f TL/cm³, sabit=%.2f TL)"
            % (model.get("birim", 0), model.get("sabit", 0)))

    # Python aynası (build.py JS-öncesi fiyat metni) node ile kuruşu kuruşuna aynı mı (drift)?
    sapmalar = [x["boy"] for x in seri
                if build.konfigur_fiyat_kurus(KURT_KONFIGUR, x["boy"]) != x["kurus"]]
    kontrol(not sapmalar,
            "build.py Python aynası node/JS ile kuruşu kuruşuna aynı (sapan boy: %s)"
            % (sapmalar or "-"))

    # PLA=1.00 IDENTITY: 2-arg (malzemesiz) çağrı, katsayi=1.0 açık çağrıyla BİREBİR aynı
    # (= "malzeme-öncesiyle tutar-eşit" / geri uyumluluk kanıtı).
    pla, phata = _node_seri(node, KURT_KONFIGUR, "1")
    kontrol(pla is not None, "node PLA (katsayi=1.0) koşumu (stderr: %s)" % (phata or "-"))
    pla_seri = pla[0] if pla else []
    kontrol(bool(pla_seri) and all(pla_seri[i]["kurus"] == seri[i]["kurus"]
                                   for i in range(len(seri))),
            "PLA katsayi=1.00 IDENTITY: malzeme-öncesi (2-arg) fiyatla BİREBİR tutar-eşit")

    # --- MALZEME KATSAYILARI: PETG ×1.30, ASA ×1.60 (Okan KESİN) ---
    tablolar = {"PLA": seri}
    for ad, kat, kat_str in (("PETG", 1.3, "1.3"), ("ASA", 1.6, "1.6")):
        malz, mhata = _node_seri(node, KURT_KONFIGUR, kat_str)
        kontrol(malz is not None, "node %s (katsayi=%.2f) koşumu (stderr: %s)"
                % (ad, kat, mhata or "-"))
        if malz is None:
            continue
        mseri = malz[0]
        tablolar[ad] = mseri
        kontrol(len(mseri) == len(seri), "%s: tüm boy adımları hesaplandı" % ad)
        kontrol(all(x["kurus"] % 100 == 0 for x in mseri),
                "%s: görünen fiyat TAM TL (kuruş küsuratı yok)" % ad)
        kontrol(all(mseri[i]["kurus"] > mseri[i - 1]["kurus"] for i in range(1, len(mseri))),
                "%s: boyla KESİN ARTAN" % ad)
        # Çapalarda katsayı TAM: %s = PLA × katsayı (tam TL) — 6 cm ve 30 cm.
        kontrol(mseri[0]["kurus"] == int(round(TABAN_TL * kat)) * 100,
                "%s ÇAPA-1 (6 cm) = %s TL (PLA %d × %.2f)"
                % (ad, int(round(TABAN_TL * kat)), TABAN_TL, kat))
        kontrol(mseri[-1]["kurus"] == int(round(CAPA2_TL * kat)) * 100,
                "%s ÇAPA-2 (30 cm) = %s TL (PLA %d × %.2f)"
                % (ad, int(round(CAPA2_TL * kat)), CAPA2_TL, kat))
        kontrol(mseri[0]["kurus"] == seri[0]["kurus"] * kat and
                mseri[-1]["kurus"] == seri[-1]["kurus"] * kat,
                "%s = PLA × %.2f (çapalarda TAM tutar)" % (ad, kat))
        # Katsayıda MONOTONLUK: her boyda %s fiyatı PLA'dan büyük.
        kontrol(all(mseri[i]["kurus"] > seri[i]["kurus"] for i in range(len(seri))),
                "%s her boyda PLA'dan pahalı (katsayı monotonluğu)" % ad)
        # Drift nöbeti: Python aynası node/JS ile kuruşu kuruşuna aynı (bu katsayıda).
        m_sap = [x["boy"] for x in mseri
                 if build.konfigur_fiyat_kurus(KURT_KONFIGUR, x["boy"], kat) != x["kurus"]]
        kontrol(not m_sap, "%s: build.py Python aynası node/JS ile kuruşu kuruşuna aynı "
                "(sapan boy: %s)" % (ad, m_sap or "-"))

    # ASA > PETG her boyda (katsayı sıralaması 1.60 > 1.30)
    if "ASA" in tablolar and "PETG" in tablolar:
        kontrol(all(tablolar["ASA"][i]["kurus"] > tablolar["PETG"][i]["kurus"]
                    for i in range(len(seri))),
                "ASA her boyda PETG'den pahalı (1.60 > 1.30)")

    print("  --- FİYAT TABLOSU (3 malzeme × 6 boy; afin %d TL @6cm .. %d TL @30cm, standart renk) ---"
          % (TABAN_TL, CAPA2_TL))
    print("      boy   |     PLA(1.00)  |    PETG(1.30)  |     ASA(1.60)")
    for i, x in enumerate(seri):
        if x["boy"] in (60, 100, 150, 200, 250, 300):
            hucre = []
            for ad in ("PLA", "PETG", "ASA"):
                v = tablolar.get(ad, [{}] * len(seri))[i].get("kurus")
                hucre.append(build.taban_fiyat_metni(v / 100.0) if v is not None else "-")
            print("    %5.1f cm | %14s | %14s | %14s"
                  % (x["boy"] / 10.0, hucre[0], hucre[1], hucre[2]))
    return seri


# ------------------------------------------------------------------ (c) geri uyumluluk
# c1 İZ LİSTESİ (NEGATİF, KÜRESEL): konfigur'a ÖZGÜ kancalar. Konfigur'suz HİÇBİR sayfada
# geçmemeli. Malzeme ekseni kancaları da buraya dahil — onlar da yalnız konfigur'lu sayfada
# üretilir; konfigur'suz sayfada görünmeleri "konfigur kodu genel yola sızdı" demektir.
KONFIGUR_IZLERI = ["URUN_KONFIGUR", "konfigur.js", "konfigurBoy", "konfigurKaydirici",
                   "PRUVO_KONFIGUR", "data-gorsel",
                   'id="malzemeButonlar"', "malzeme-btn", "data-katsayi"]

# c2 YAPISAL ÇEKİRDEK (POZİTİF, SAYFA BAZLI — [[kapi-kapsam-genisletme-tuzagi]]):
# her konfigur'suz sayfa sınıfının KİMLİK kancaları. Yalnız YAPI aranır (element id'si, JS
# bayrağı, modül yolu) — görünen metin, CSS sınıf stili, kategori adı, fiyat DEĞİL; böylece
# ilgisiz rutin düzenleme (metin/CSS/yeni kategori/yorum) bu nöbeti YAKMAZ.
# ÇAPA YOK: "en az bir kez geçmeli" (olmali) / "hiç geçmemeli" (olmamali); SAYI karşılaştırması
# yapılmaz -> filament sayısı, ilgili ürün sayısı vb. değişince kırmızı yanmaz.
YAPISAL_CEKIRDEK = {
    # panelsiz dal: opsiyon paneli YOK, sayfa altında BÜYÜK butonlar var, KART_SECIM kapalı
    "test-panelsiz": (['id="filCipler"', "KART_SECIM = false", 'class="cart-btn"'],
                      ['id="opsiyonlar"', "KART_SECIM = true"]),
    # kart-seçim dalı: opsiyon paneli + ikon düzeni (sayfa altı büyük buton YOK)
    "test-oto-parca": (['id="filCipler"', "KART_SECIM = true", 'id="opsiyonlar"',
                        'id="cartBtn"'],
                       ['class="cart-btn"', "KART_SECIM = false"]),
    # boy seçenekli: boy açılır kutusu (#boySec) kart-seçim düzeninin İÇİNDE
    "test-boylu": (['id="filCipler"', "KART_SECIM = true", 'id="opsiyonlar"',
                    'id="boySec"'],
                   ['class="cart-btn"']),
    # lisanslı: CC atıf bloğu KALIR (lisans kuralı — silinmesi ticari/hukuki risk)
    "test-lisansli": (['id="filCipler"', "KART_SECIM = true", 'class="attribution"',
                       'rel="license'],
                      ['class="cart-btn"']),
    # parametrik sarı: jeneratör konfigüratör modülleri sayfaya bağlanır
    "olcuye-ozel-huni": (['id="filCipler"', "KART_SECIM = true",
                          "jenerator/konfigurator.js", "jenerator/hacim.js"],
                         ['class="cart-btn"']),
}

# c4 referans durumları
REF_OLCULDU = "OLCULDU"      # referans build.py alındı ve ÇALIŞANDAN FARKLI -> gerçek ölçüm
REF_TOTOLOJI = "TOTOLOJI"    # referans build.py çalışanla BAYT AYNI -> karşılaştırma boş
REF_YOK = "YOK"              # referans hiç alınamadı (sığ klon / ref yok / git yok)


def eski_build_modulu():
    """merge-base'deki (dal ayrım noktası) tools/build.py'yi ayrı modül olarak yükler.

    (modul, durum, ayrinti) döner. "HEAD" ARTIK REFERANS DEĞİL: `merge-base HEAD HEAD`
    daima HEAD'i verir -> karşılaştırma bir şeyi KENDİSİYLE karşılaştırır (totoloji) ve
    nöbetçi sessizce yeşil yanar. Ana hatta (main'e push) merge-base zaten HEAD olduğu
    için referans build.py çalışan build.py ile BAYT AYNI çıkar; bunu TOTOLOJI olarak
    ayrı raporlarız — "BAYT-EŞİT ✅" yazmak YALAN olurdu."""
    calisan = open(os.path.join(TOOLS, "build.py"), "rb").read()
    for ref in ("origin/main", "main"):
        mb = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", ref],
                            capture_output=True, text=True)
        if mb.returncode != 0:
            continue
        commit = mb.stdout.strip()
        kaynak = subprocess.run(["git", "-C", ROOT, "show", commit + ":tools/build.py"],
                                capture_output=True)
        if kaynak.returncode != 0:
            continue
        taban = "%s (merge-base HEAD..%s)" % (commit[:12], ref)
        if kaynak.stdout == calisan:
            return None, REF_TOTOLOJI, taban
        g = {"__file__": os.path.join(TOOLS, "build.py"), "__name__": "build_eski"}
        exec(compile(kaynak.stdout.decode("utf-8"),
                     "build_eski<%s>" % commit[:12], "exec"), g)
        return g, REF_OLCULDU, taban
    return None, REF_YOK, "merge-base/git show alınamadı (sığ klon / origin-main yok?)"


def _malzeme_arayuzu(html):
    """(kart_bolumu_var, secici_var) — sayfadaki malzeme arayüzünün biçimi."""
    return ('id="filCipler"' in html, 'id="malzemeButonlar"' in html)


def test_geri_uyumluluk():
    print("\n(c) KONFIGUR'SUZ SAYFA GERİ UYUMLULUĞU")
    print("    İDDİA c1 (referanssız/kalıcı): konfigur'a özgü kanca konfigur'suz sayfaya SIZMAZ.")
    print("    İDDİA c2 (referanssız/kalıcı): her sayfa sınıfı yapısal çekirdeğini KORUR.")
    print("    İDDİA c3 (referanssız/kalıcı): malzeme arayüzü XOR — kart bölümü ya da seçici,")
    print("             ikisi birden ya da hiçbiri DEĞİL.")
    print("    İDDİA c4 (referansa bağlı/BLOKLAMAZ): merge-base build.py ile bayt-eşitlik.")
    print("    MEŞRU DEĞİŞİKLİK (kırmızı yakmamalı): metin/CSS/yeni kategori/yeni sayfa/yorum/")
    print("             yeniden adlandırma/JSON-LD alanı — konfigur eksenine dokunmayan her şey.")
    fikstuler = [
        # Panelsiz (opsiyon paneli basılmayan, sayfa-altı büyük butonlu) dal: Okan 23 Tem
        # kararıyla Dekorasyon + Oyun/Hobi FONKSIYONEL oldu; bu dalı bugün yalnız FONKSIYONEL
        # dışı + parametrik olmayan kategori (şemasız Jeneratör) tetikler. Fikstür oraya
        # taşındı ki panelsiz kod yolu ölçülmeye devam etsin.
        ("panelsiz (şemasız Jeneratör)", urun(
            None, id="test-panelsiz", kategori="Jeneratör",
            baslik="Test Panelsiz Ürün", fiyat="150 TL")),
        ("kart-seçim fonksiyonel (Otomobil)", urun(
            None, id="test-oto-parca", kategori="Otomobil", marka=["Audi"],
            baslik="Test Oto Parçası", fiyat="850 TL")),
        ("boy_secenekli fonksiyonel", urun(
            None, id="test-boylu", kategori="Ev", baslik="Test Boylu Ürün", fiyat="300 TL",
            boy_secenekleri=[{"etiket": "20 cm"}, {"etiket": "30 cm", "fark_tl": 100}])),
        ("lisanslı (CC BY)", urun(
            None, id="test-lisansli", kategori="Kamera", baslik="Test Lisanslı",
            fiyat="450 TL", lisans={"tasarimci": "testci", "tur": "CC BY 4.0"})),
        ("parametrik sarı (gerçek şema: huni)", urun(
            None, id="olcuye-ozel-huni", kategori="Jeneratör",
            baslik="Ölçüye Özel Huni", fiyat="", parametrik=True)),
    ]
    tumu = [p for _, p in fikstuler]
    yeni_ciktilar = {}
    for ad, p in fikstuler:
        html = build.render_product(p, tumu)
        yeni_ciktilar[p["id"]] = html
        izler = [iz for iz in KONFIGUR_IZLERI if iz in html]
        kontrol(not izler, "c1 konfigur izi yok: %s (sızan: %s)" % (ad, izler or "-"))

    # --- c2: yapısal çekirdek (POZİTİF, sayfa bazlı) ---
    for ad, p in fikstuler:
        html = yeni_ciktilar[p["id"]]
        olmali, olmamali = YAPISAL_CEKIRDEK[p["id"]]
        eksik = [m for m in olmali if m not in html]
        fazla = [m for m in olmamali if m in html]
        kontrol(not eksik and not fazla,
                "c2 yapısal çekirdek yerinde: %s (kayıp: %s / sızan: %s)"
                % (ad, eksik or "-", fazla or "-"))

    # --- c3: malzeme arayüzü XOR — konfigur'lu sayfalar da dahil TÜM sınıflarda ---
    xor_fikstur = [(ad, p, False) for ad, p in fikstuler]
    xor_fikstur.append(("konfigur (malzemesiz)", urun(KURT_KONFIGUR), False))
    xor_fikstur.append(("konfigur + malzeme ekseni", urun(KURT_KONFIGUR_MALZEME), True))
    for ad, p, secici_beklenir in xor_fikstur:
        html = yeni_ciktilar.get(p["id"]) or build.render_product(p, [p])
        kart, secici = _malzeme_arayuzu(html)
        beklenen = (not secici_beklenir, secici_beklenir)
        kontrol((kart, secici) == beklenen,
                "c3 malzeme arayüzü XOR: %s (#filCipler=%s #malzemeButonlar=%s, beklenen %s/%s)"
                % (ad, kart, secici, beklenen[0], beklenen[1]))

    # --- c4: bayt-eşitlik (referansa bağlı; BLOKLAMAZ — gerekçe modül docstring'inde) ---
    eski, durum, taban = eski_build_modulu()
    if durum == REF_YOK:
        olculemedi("c4 bayt-eşitlik: referans build.py alınamadı (%s). "
                   "Kalıcı koruma c1/c2/c3'te koştu." % taban)
        return
    if durum == REF_TOTOLOJI:
        olculemedi("c4 bayt-eşitlik: referans build.py ÇALIŞANLA BAYT AYNI -> karşılaştırma "
                   "totoloji, hiçbir şey ölçülmedi. Taban: %s. (Ana hatta beklenen durum; "
                   "kalıcı koruma c1/c2/c3'te koştu.)" % taban)
        return
    print("  c4 referans build.py tabanı: %s (çalışandan FARKLI -> ölçülebilir)" % taban)
    for ad, p in fikstuler:
        eski_html = eski["render_product"](p, tumu)
        y = yeni_ciktilar[p["id"]]
        if eski_html == y:
            print("  ✅ c4 BAYT-EŞİT: %s" % ad)
            continue
        # ilk ayrışan bölgeyi raporla (tanılama). BLOKLAMAZ: build.py'ye yapılan MEŞRU
        # düzenleme (CSS/metin/JSON-LD) de burada ayrışır -> kırmızı yakmak yanlış-pozitif
        # olurdu; konfigur ekseni c1/c2/c3 ile ölçülür.
        i = next((j for j in range(min(len(y), len(eski_html)))
                  if y[j] != eski_html[j]), min(len(y), len(eski_html)))
        uyar("c4 BAYT AYRIŞTI (bloklamaz): %s — ilk fark ofset %d\n"
             "        eski=%r\n        yeni=%r"
             % (ad, i, eski_html[max(0, i - 40):i + 40], y[max(0, i - 40):i + 40]))


# ------------------------------------------------------------------ (d) konfigur sayfası
def test_konfigur_sayfasi(seri):
    print("\n(d) KONFIGUR'LU ÜRÜN SAYFASI + JSON-LD/FEED")
    p = urun(KURT_KONFIGUR)
    html = build.render_product(p, [p])

    ld_bloklar = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    kontrol(len(ld_bloklar) >= 2, "JSON-LD blokları basılır")
    product_ld = json.loads(ld_bloklar[0])
    offers = product_ld.get("offers") or {}
    kontrol(offers.get("price") == str(TABAN_TL),
            "JSON-LD Offer.price = taban (EN KÜÇÜK boy) fiyatı: %r" % offers.get("price"))
    kontrol(offers.get("priceCurrency") == "TRY", "JSON-LD priceCurrency TRY")

    feed_xml, feed_n = build.render_merchant_feed([p])
    kontrol(feed_n == 1 and ("<g:price>%d TRY</g:price>" % TABAN_TL) in feed_xml,
            "Merchant feed'e taban fiyatla girer (%d TRY)" % TABAN_TL)

    kontrol('var URUN_KONFIGUR = {"boyutMm"' in html, "inline URUN_KONFIGUR verisi basılır")
    kontrol('"fiyatCapalari":[[60,150],[300,1300]]' in html,
            "URUN_KONFIGUR fiyat çapalarını taşır (eğri çapadan çözülür)")
    kontrol('<script src="/konfigur.js?v=' in html, "/konfigur.js sürümlü (?v=hash) yüklenir")
    kontrol('id="konfigurKaydirici"' in html and 'type="range"' in html,
            "boy kaydırma çubuğu basılır")
    kontrol('id="konfigurBoy"' in html, "boy sayı kutusu basılır")
    kontrol(html.count("data-gorsel=") == len(KURT_KONFIGUR["renkler"]),
            "her renk butonu data-gorsel taşır (görsel değişimi)")
    for r, i in KURT_KONFIGUR["renkGorselIndeks"].items():
        kontrol(('data-renk="%s" data-gorsel="%s"' % (r, GORSELLER[i])) in html,
                "renk -> görsel eşlemesi doğru: %s" % r)
    kontrol('id="renkOzel"' not in html, "'Diğer'/serbest renk kutusu YOK (standart 3 renk)")
    kontrol("Diğer" not in html.split('id="renkButonlar"')[1].split("</div>")[0],
            "renk butonlarında 'Diğer' yok")
    kontrol('<button class="cart-btn"' not in html,
            "sayfa altı büyük butonlar yerine ikon düzeni kullanılır")
    kontrol('id="cartBtn"' in html and "ikon-sepet" in html, "Sepete Ekle ikonu vardır")
    kontrol("PRUVO_KONFIGUR.kur(URUN_KONFIGUR, URUN, render)" in html,
            "kur kancası bağlı (kaydırıcı/renk değişimi render'ı tetikler)")
    kontrol("PRUVO_KONFIGUR.satiraYaz(s)" in html,
            "sepet satırı kancası bağlı (seçimler siparişe taşınır)")
    kontrol("PRUVO_KONFIGUR.tazele()" in html, "fiyat tazeleme kancası bağlı")
    kontrol("PRUVO_KONFIGUR.eksikVurgula()" in html,
            "renk seçilmeden sepete ekleme kilidi bağlı")
    kontrol(" && !URUN_KONFIGUR" in html,
            "varsayılan fiyat yazıcısı konfigur sayfasında devre dışı (çakışma yok)")
    kontrol("KART_SECIM = false" in html,
            "KART_SECIM kapalı (malzeme-kartı kilidi konfigur'da tetiklenmez)")

    kontrol('id="malzemeButonlar"' not in html and "malzeme-btn" not in html,
            "MALZEMESİZ konfigur: malzeme seçici YOK (geri uyumluluk — renk+boy)")

    if seri:
        varsayilan = KURT_KONFIGUR["boyutMm"]["varsayilan"]
        beklenen_kurus = next(x["kurus"] for x in seri if x["boy"] == varsayilan)
        beklenen_metin = build.taban_fiyat_metni(beklenen_kurus / 100.0)
        kontrol(('id="opsiyonFiyat">%s<' % beklenen_metin) in html,
                "JS öncesi fiyat metni = varsayılan boyun kuruşlu fiyatı (%s)" % beklenen_metin)


# --------------------------------------------------------------- (e) malzeme ekseni sayfası
def test_konfigur_malzeme_sayfasi(seri):
    print("\n(e) MALZEME EKSENLİ KONFIGUR SAYFASI (PLA/PETG/ASA) + JSON-LD MİNİMUM")
    p = urun(KURT_KONFIGUR_MALZEME)
    html = build.render_product(p, [p])

    ld_bloklar = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    product_ld = json.loads(ld_bloklar[0])
    offers = product_ld.get("offers") or {}
    kontrol(offers.get("price") == str(TABAN_TL),
            "malzeme ekseninde JSON-LD Offer.price HALA MİNİMUM (PLA 6 cm = %d): %r"
            % (TABAN_TL, offers.get("price")))
    feed_xml, feed_n = build.render_merchant_feed([p])
    kontrol(feed_n == 1 and ("<g:price>%d TRY</g:price>" % TABAN_TL) in feed_xml,
            "Merchant feed minimum (PLA) fiyatla girer (%d TRY)" % TABAN_TL)

    # TEK malzeme arayüzü: seçici #malzemeButonlar İÇİNDE, standart filament KARTIYLA aynı
    # görsel bileşen (fancy .fil-cip) AMA /konfigur.js kancası .malzeme-btn + data-katsayi taşır
    # (Okan 24 Tem: fancy kartlar seçici olsun; üstteki basit selector + alttaki bilgi kartı
    # "çift-UI"si kalksın). Bayt-değişmez fiyat/JSON-LD/feed yukarıda kanıtlandı.
    kontrol('id="malzemeButonlar"' in html, "malzeme seçici (#malzemeButonlar) basılır")
    kontrol(html.count("malzeme-btn") == len(MALZEMELER),
            "her malzeme bir .malzeme-btn kartı (%d): %d" % (len(MALZEMELER), html.count("malzeme-btn")))
    for m in MALZEMELER:
        kontrol(('data-malzeme="%s"' % m["ad"]) in html, "malzeme kartı: %s" % m["ad"])
        kontrol(('data-katsayi="%s"' % build._sayi_metni(m["katsayi"])) in html,
                "malzeme %s -> data-katsayi=%s (fiyat çarpanı)" % (m["ad"], build._sayi_metni(m["katsayi"])))
    # Fancy kart görünümü: #malzemeButonlar kaplayıcı .fil-cipler + her malzeme .fil-cip;
    # ısı dayanımı + bilgi balonu (tooltip) filamentler.json'dan (kart-seçim ürünüyle aynı dil).
    m_cont = re.search(r'id="malzemeButonlar">(.*?)</div>', html, re.S)
    icerik = m_cont.group(1) if m_cont else ""
    kontrol(icerik.count('class="fil-cip') == len(MALZEMELER),
            "malzeme kartları fancy .fil-cip görünümünde (%d): %d"
            % (len(MALZEMELER), icerik.count('class="fil-cip')))
    kontrol("fil-isi" in icerik and "fil-balon" in icerik,
            "malzeme kartları ısı (fil-isi) + bilgi balonu (fil-balon/tooltip) taşır")
    for m_ad, isi in (("PLA", "~55-60°C"), ("PETG", "~70-75°C"), ("ASA", "~90-95°C")):
        kontrol(isi in icerik, "%s kartı ısı dayanımını (%s) gösterir" % (m_ad, isi))
    kontrol('class="fil-cip tavsiyeli malzeme-btn secili" data-malzeme="PLA"' in html,
            "varsayılan PLA fancy kartı önden 'secili' (fil-cip [tavsiyeli] malzeme-btn secili)")
    kontrol('data-malzeme="ABS"' not in html and 'data-malzeme="Karbon"' not in html,
            "ABS/Karbon malzeme SEÇENEĞİ YOK (satışa kapalı)")
    # Çift-UI kalktı: alttaki AYRI standart filament kart bölümü (#filCipler) BASILMAZ;
    # yalnız faydalı mühendislik-malzeme WhatsApp notu + Malzeme Rehberi linki KALIR.
    kontrol('id="filCipler"' not in html,
            "AYRI standart filament KART bölümü YOK (çift-UI kalktı — malzeme tek yerde seçilir)")
    kontrol("Malzeme Rehberi" in html and 'href="/malzeme-rehberi/"' in html,
            "'Malzeme Rehberi' linki KALIR (faydalı bilgi silinmedi)")
    kontrol("wa.me/905451386526" in html and 'class="malzeme-not"' in html,
            "mühendislik malzemesi (Karbon/ABS) WhatsApp notu KALIR")
    kontrol('src="/konfigur.js' in html and 'id="cartBtn"' in html,
            "/konfigur.js + Sepete Ekle ikonu (malzeme sayfada da) bağlı")
    kontrol("KART_SECIM = false" in html,
            "malzeme ekseninde de KART_SECIM kapalı (malzeme-kartı kilidi tetiklenmez)")

    if seri:
        varsayilan = KURT_KONFIGUR["boyutMm"]["varsayilan"]
        beklenen_kurus = next(x["kurus"] for x in seri if x["boy"] == varsayilan)  # PLA serisi
        beklenen_metin = build.taban_fiyat_metni(beklenen_kurus / 100.0)
        kontrol(('id="opsiyonFiyat">%s<' % beklenen_metin) in html,
                "JS öncesi fiyat = varsayılan boy × VARSAYILAN malzeme (PLA): %s" % beklenen_metin)


# ------------------------------------------------------------------ ana akış
CIK_YESIL = 0
CIK_KIRMIZI = 1
CIK_OLCULEMEDI = 2


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # ANA HAT modu: c4 (bayt-eşitlik) main'de YAPISAL OLARAK ölçülemez (merge-base == HEAD).
    # deploy.yml bu bayrakla koşar: ÖLÇÜLEMEDİ hâlâ GÜRÜLTÜLÜ raporlanır ama yayını
    # KİLİTLEMEZ — sessiz yeşil kadar, sürekli kırmızı da yanlış olurdu.
    anahat = "--anahat" in argv
    for a in argv:
        if a not in ("--anahat",):
            print("Bilinmeyen argüman: %s (yalnız --anahat)" % a)
            return CIK_KIRMIZI
    print("KONFIGUR KABUL TESTİ (dekor konfigüratörü altyapısı + malzeme ekseni)%s"
          % (" [ANA HAT MODU]" if anahat else ""))
    test_sema()
    seri = test_fiyat()
    test_geri_uyumluluk()
    test_konfigur_sayfasi(seri)
    test_konfigur_malzeme_sayfasi(seri)
    print("-" * 70)
    if UYARILAR:
        print("UYARI (bloklamaz): %d bulgu" % len(UYARILAR))
    if HATALAR:
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(HATALAR))
        return CIK_KIRMIZI
    if OLCULEMEDI:
        # Kalıcı iddialar (a/b/c1/c2/c3/d/e) YEŞİL; yalnız referansa bağlı c4 ölçülemedi.
        print("SONUC: YESIL ✅ (kalıcı iddialar) — ANCAK %d iddia ÖLÇÜLEMEDİ ⚪:"
              % len(OLCULEMEDI))
        for m in OLCULEMEDI:
            print("   ⚪ " + m.split(".")[0])
        if anahat:
            print("   --anahat: ÖLÇÜLEMEDİ ana hatta BEKLENEN durumdur -> çıkış %d."
                  % CIK_YESIL)
            return CIK_YESIL
        print("   Çıkış %d = ÖLÇÜLEMEDİ (ne yeşil ne kırmızı). Ana hatta bu beklenendir:"
              " 'python3 tools/konfigur-test.py --anahat'." % CIK_OLCULEMEDI)
        return CIK_OLCULEMEDI
    print("SONUC: YESIL ✅")
    return CIK_YESIL


if __name__ == "__main__":
    sys.exit(main())

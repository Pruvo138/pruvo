#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ON-SECILI MALZEME <-> ILAN EDILEN TUTAR PARITE KAPISI (11 Agu 2026).

    python3 tools/onsecim-parite-kapisi.py
    python3 tools/onsecim-parite-kapisi.py --mutasyon      # + kontrol mutantlari

NEDEN VAR — HATA SINIFI SESSIZ VE PARALI (SESSIZ ZAM): urun sayfasinda onden secili
gelen malzeme, ilan edilen tutardan BAGIMSIZ secilirse hicbir sey alarm calmaz.
PETG +%30, ASA +%60; katalogda onerilen malzemesi PLA OLMAYAN urun orani %96,6
(24.492/25.354 — bu kapinin (0) bolumu her kosumda yeniden olcer). Ornek: 350 TL
ilan edilen bir Otomobil parcasi PETG onden secili gelseydi sepete 455,00 TL
yazilirdi; sayfa, kart yuzeyi, yapilandirilmis veri ve besleme hala 350 TL beyan
ederdi. Musteri farki ANCAK odeme ekraninda gorurdu — ya da hic gormezdi.

KAPININ IDDIASI (dort ayak, hepsi KOSULARAK olculur):
  (1) IKIZ TANIM  — kural iki dilde yazilidir (sayfa ureteci tarafi filament_ortak.on_secim,
                    istemci tarafi secenekler.js onSecimMalzeme). TUM KATALOG uzerinde
                    hem secilen malzeme hem hesaplanan kurus BIREBIR karsilastirilir;
                    tek satirlik sapma KIRMIZI (ayrisma sessiz kalamaz).
  (2) BAYRAK KAPALI — kural kapaliyken on-secim guvenli varsayilandir ve ilan edilen
                    tutar liste tutaridir (bugunku davranis, regresyon 0).
  (3) BAYRAK ACIK / PARITE — onerilen malzemesi PLA OLMAYAN ve PLA OLAN urunlerde:
                    onden secili cip = sayfadaki gorunur tutar = uretilen sayfanin KENDI
                    JS'inin (node:vm) hic secim yapmadan sepete yazdigi satir = SUNUCU
                    fiyat kolunun (paylasilan satirOzeti) hesabi — KURUS KURUS.
                    Onerisi OLMAYAN urunde davranis bozulmuyor.
                    🔴 YAPILANDIRILMIS VERI ve BESLEME BU DORTLUNUN DISINDADIR (isletme
                    karari, 11 Agu — Okan'in kendi secimi, GMC reddi riski kendisine
                    YAZILI bildirildikten sonra): ikisi de BASLANGIC tabanini beyan eder.
                    Kapi bunu da olcer ve ikisinin urun sayfasi tutarina KAYMASINI
                    kirmizi yakar (kaymak, acikca reddedilen davranistir).
  (4) TEK TURETME — ilan tutari on-secimi CAGIRARAK turer; ikisini ayiran mutasyon
                    (ornek: cip PETG, tutar PLA) KIRMIZI yakmali (--mutasyon).

NE IDDIA EDILMEZ (beyan edilen kor noktalar — sessiz yesil yasak):
  * OLCUYE OZEL (parametrik) ve YAPILANDIRICILI urun kolu: oralarda tutar tabandan
    CANLI hesaplanir ve kart yuzeyi tabani ayri bir haritadan okur; kural o kolda
    BILEREK uygulanmaz (guvenli varsayilan korunur) ve bu kapi orada parite IDDIA ETMEZ.
  * Katalog verisini okuyan DIS yuzeyler (mesaj kanali gibi) liste tutarini ayri bir
    kaynaktan okur; bayrak acilirsa o yuzey ayri ele alinmalidir — bu kapi olcmez.
  * Gorsel yerlesim/piksel. Olculen sey METIN ve SAYIDIR.

CIKIS: 0 yesil · 1 kirmizi · 2 olculemedi (node/fikstur yok). Depoya YAZMAZ.
"""
import argparse
import importlib.util
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

import build            # noqa: E402
import filament_ortak   # noqa: E402
import yayin_yuzey      # noqa: E402

# Sepet kapisinin node kosucusu + mini DOM'u YENIDEN YAZILMAZ: ayni uretilen sayfayi
# ayni sekilde suren tek bir kosucu vardir, buraya ikinci kopyasi cikarilmaz (iki kopya
# sessizce ayrisir ve iki kapi ayni sayfa hakkinda farkli sey soylerdi).
_SEPET_YOL = os.path.join(TOOLS, "sepet-secim-kapisi.py")
_spec = importlib.util.spec_from_file_location("sepet_secim_kapisi", _SEPET_YOL)
sepet_kapisi = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sepet_kapisi)

# Fikstur urunleri — SABIT FIYATLI katalog kolu (kural yalnizca orada uygulanir).
FIKSTURLER = [
    {"id": "bmw-kaput-a-ma-kolu", "ad": "PLA-disi oneri (ABS +%50)", "bekle": "ABS"},
    {"id": "genesis-coupe-jant-gobek-kapagi", "ad": "PLA-disi oneri (ASA +%60)",
     "bekle": "ASA"},
    {"id": "mitsubishi-klima-kumanda-standi", "ad": "PLA onerisi (fark %0)",
     "bekle": "PLA"},
]

# ---------------------------------------- onerisi TURETILEMEYEN urun (guvenli varsayilan)
# 🔴 NEDEN ID'YE CIVILENMEZ (olculdu 11 Agu — YAYIN DURDU): bu eksen once
# `mitsubishi-4g63-eksantrik-mili-kilit-aparati` ID'sine civilenmisti. O kayitta
# `tavsiyeFilament` DIZE ("PETG") idi, yani oneri TURETILEMIYORDU. Katalog tarafi
# 177469421 ("Filament önerisi alan türlerini düzelt") ile 293 kayitta alani DIZIYE
# cevirdi (["PETG"]) -> denek oneri TASIR hale geldi, SINIF DISI kaldi ve kapi
# `serit-a3`te kirmizi yandi. IDDIA dogruydu, DENEK bayatlamisti
# ([[envanter-drift-parti-basina]]: elle tutulan denek listesi her katalog partisinde
# bayatlar). Denek bu yuzden her kosumda VERININ OZELLIGINDEN turetilir:
#   KRITER (BAGIMSIZ, fonksiyonun ciktisi DEGIL — o tautoloji olurdu):
#   `tavsiyeFilament` alani DOLU ama icindeki adlarin HICBIRI sitede satilan
#   malzeme listesinde YOK -> oneri turetilemez.
# Boyle bir kayit katalogda kalmazsa eksen ATLANMAZ (atlanmasi sessiz yesil olurdu):
# gercek bir sabit-fiyatli kayittan SENTETIK denek turetilir (alan sitede satilmayan
# bir ada ayarlanir) ve eksen aynen olculur.
_SENTETIK_ONERI = "ABS"          # gercek muhendislik malzemesi, sitede SATILMIYOR


def _turetilemeyen_fikstur(urunler):
    site_adlar = {f["ad"] for f in filament_ortak.referans()["filamentler"]
                  if f.get("site")}

    def sabit_kol(p):
        """Kuralin uygulandigi kol: sabit fiyatli, fiyati ayristirilabilen,
           malzeme secicisi BASILAN (fonksiyonel kategori) katalog kaydi."""
        return (not build.fiziksel_mi(p) and not p.get("parametrik")
                and not p.get("konfigur")
                and p.get("kategori") in build.FONKSIYONEL_KATEGORILER
                and build.feed_price((p.get("fiyat") or "").strip()))

    def turetilemez(p):
        ovr = p.get("tavsiyeFilament")
        if not ovr or not isinstance(ovr, list):
            return bool(ovr)          # bos olmayan NON-LIST de turetilemez sinifidir
        return not [a for a in ovr if a in site_adlar]

    adaylar = sorted([p for p in urunler if sabit_kol(p) and turetilemez(p)],
                     key=lambda x: x["id"])
    if adaylar:
        p = adaylar[0]
        print("     onerisi TURETILEMEYEN denek KATALOGDAN: %s (tavsiyeFilament=%s, "
              "sinifta %d kayit)"
              % (p["id"], json.dumps(p.get("tavsiyeFilament"), ensure_ascii=False),
                 len(adaylar)))
        return {"id": p["id"], "urun": p, "ad": "onerisi YOK (guvenli)", "bekle": None}

    taban = next((p for p in urunler if sabit_kol(p)), None)
    if taban is None:
        return None
    if _SENTETIK_ONERI in site_adlar:
        kontrol(False, "sentetik denek adi %r artik SITEDE SATILIYOR — denek sinif "
                       "disi kaldi, ad degistirilmeli" % _SENTETIK_ONERI)
        return None
    p = dict(taban)
    p["tavsiyeFilament"] = [_SENTETIK_ONERI]
    print("     onerisi TURETILEMEYEN denek SENTETIK (katalogda sinif kalmadi): "
          "%s + tavsiyeFilament=[%r]" % (p["id"], _SENTETIK_ONERI))
    return {"id": p["id"], "urun": p, "ad": "onerisi YOK (guvenli)", "bekle": None}

HATALAR = []
OLCULEMEDI = []


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)
    return bool(kosul)


def olculemedi(mesaj):
    print("  ⚠️  OLCULEMEDI: " + mesaj)
    OLCULEMEDI.append(mesaj)


def _urunler():
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        return json.load(f)


def _node():
    return shutil.which("node")


def _acik_secenekler(gecici):
    """secenekler.js'in URUN SAYFASI BAYRAGI ACIK kopyasi (kaynak dosyaya DOKUNULMAZ).

    IDEMPOTENT: bayrak depoda zaten ACIK olabilir (11 Agu'dan beri oyle). "false -> true"
    ikamesinin TAM 1 kez tutmasini sart kosmak, bayrak acildigi anda kapiyi KIRMIZI
    yakardi — iddia ile ilgisi olmayan bir kirmizi. Sart olan sey, kopyanin bayragi
    ACIK olmasidir; asagidaki bolum_1 bunu ayrica KOSARAK dogrular (veri["acik"])."""
    with open(os.path.join(ROOT, "secenekler.js"), encoding="utf-8") as f:
        s = f.read()
    m = re.search(r"var\s+ONERI_ONSECIM_ACIK\s*=\s*(true|false);", s)
    if not m:
        return None
    yeni = s[:m.start()] + "var ONERI_ONSECIM_ACIK = true;" + s[m.end():]
    yol = os.path.join(gecici, "secenekler-acik.js")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    return yol


# ------------------------------------------------------- (0) MARUZIYET (bilgi + kanit izi)
def bolum_0(urunler):
    print("\n(0) MARUZIYET — kural acilirsa kac urunun ilan tutari degisir")
    build.ONERI_ONSECIM_ACIK = True
    try:
        sayac = {}
        degisen = 0
        for p in urunler:
            m = build.on_secim_malzeme(p)
            sayac[m] = sayac.get(m, 0) + 1
            if build.FILAMENT_FARK.get(m, 0):
                degisen += 1
    finally:
        build.ONERI_ONSECIM_ACIK = False
    print("     on-secim dagilimi: " + " · ".join(
        "%s=%d" % (k, v) for k, v in sorted(sayac.items(), key=lambda x: -x[1])))
    print("     ilan tutari DEGISECEK urun: %d / %d (%%%.1f)"
          % (degisen, len(urunler), 100.0 * degisen / max(1, len(urunler))))
    kontrol(degisen > 0,
            "maruziyet OLCULDU — pozitif taniyici iz var (%d urun), 'etkilenen yok' "
            "hukmu sessizce verilemez" % degisen)

    # KURAL BIRIMI — iki savunma ayagi TEK BASINA olculur. Katalogda bugun sitede
    # satilan her malzeme katsayi tablosunda VAR; yani asagidaki iki koruma canli
    # veriyle AYIRT EDILEMEZ ve sentetik girdiyle olculmezse sessizce silinebilirdi.
    kontrol(filament_ortak.on_secim("Otomobil", None, {"PLA"}, "PLA") == "PLA",
            "katsayi tablosunda BULUNMAYAN oneri on-secilemiyor -> guvenli varsayilan "
            "(bulunsaydi fark %0 sanilip liste tutari ilan edilirdi)")
    kontrol(filament_ortak.on_secim("Otomobil", None, set(build.FILAMENT_FARK), "PLA",
                                    acik=False) == "PLA",
            "bayrak KAPALIYKEN kural hicbir oneriyi uygulamiyor -> guvenli varsayilan")


# ------------------------------------------------------- (1) IKIZ TANIM (tam katalog)
JS_DRIFT_RUNNER = r"""
"use strict";
/* Istemci tarafi kurali TUM KATALOG uzerinde kosar; sonuc sayfa ureteci tarafiyla
   birebir karsilastirilir. Kural KOPYALANMAZ: gercek dosya node:vm'de kosar. */
const fs = require("node:fs");
const vm = require("node:vm");
const SEC = process.argv[2];
const URUNLER = process.argv[3];
const REF = process.argv[4];
const ctx = { console: { log() {} }, Math, JSON, Date };
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(SEC, "utf8"), ctx, { filename: "secenekler.js" });
const S = ctx.PRUVO_SECENEK;
const urunler = JSON.parse(fs.readFileSync(URUNLER, "utf8"));
const ref = JSON.parse(fs.readFileSync(REF, "utf8"));
const out = {};
for (const p of urunler) {
  out[p.id] = [S.onSecimMalzeme(p, ref), S.ilanBirimKurus(p, ref), S.onSecimTani(p, ref)];
}
process.stdout.write(JSON.stringify({ acik: S.ONERI_ONSECIM_ACIK, sonuc: out }));
"""


def bolum_1(gecici, urunler):
    print("\n(1) IKIZ TANIM — sayfa ureteci kurali ile istemci kurali TUM KATALOGDA esit mi")
    node = _node()
    if not node:
        olculemedi("node yok — ikiz tanim ekseni olculemedi")
        return
    sec_yol = _acik_secenekler(gecici)
    if not sec_yol:
        kontrol(False, "secenekler.js bayrak satiri bulunamadi (ONERI_ONSECIM_ACIK)")
        return
    uy = os.path.join(gecici, "urunler-drift.json")
    with open(uy, "w", encoding="utf-8") as f:
        json.dump(urunler, f, ensure_ascii=False)
    ry = os.path.join(gecici, "ref-drift.json")
    with open(ry, "w", encoding="utf-8") as f:
        json.dump(filament_ortak.referans(), f, ensure_ascii=False)
    ky = os.path.join(gecici, "drift-kosucu.js")
    with open(ky, "w", encoding="utf-8") as f:
        f.write(JS_DRIFT_RUNNER)
    r = subprocess.run([node, ky, sec_yol, uy, ry], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        olculemedi("drift kosucusu dustu: %s" % (r.stderr or "")[-600:])
        return
    veri = json.loads(r.stdout)
    kontrol(veri.get("acik") is True,
            "istemci kurali ACIK durumda olculdu (bayrak kapali olsaydi iki taraf da "
            "guvenli varsayilani dondurur ve eksen HICBIR SEY olcmezdi)")
    js = veri["sonuc"]

    build.ONERI_ONSECIM_ACIK = True
    try:
        sapan_m, sapan_k, sapan_t, olculen, pla_disi = [], [], [], 0, 0
        tani_sayac = {}
        for p in urunler:
            pid = p["id"]
            if pid not in js:
                continue
            olculen += 1
            py_t, py_m = build.on_secim_tani(p)
            py_k = build.ilan_kurus(p)
            tani_sayac[py_t] = tani_sayac.get(py_t, 0) + 1
            if build.FILAMENT_FARK.get(py_m, 0):
                pla_disi += 1
            if js[pid][0] != py_m and len(sapan_m) < 5:
                sapan_m.append("%s: ureteç=%s istemci=%s" % (pid, py_m, js[pid][0]))
            if js[pid][1] != py_k and len(sapan_k) < 5:
                sapan_k.append("%s: ureteç=%s istemci=%s" % (pid, py_k, js[pid][1]))
            if js[pid][2] != py_t and len(sapan_t) < 5:
                sapan_t.append("%s: ureteç=%s istemci=%s" % (pid, py_t, js[pid][2]))
    finally:
        build.ONERI_ONSECIM_ACIK = False
    kontrol(olculen == len(urunler),
            "tum katalog karsilastirildi (%d/%d kayit)" % (olculen, len(urunler)))
    kontrol(pla_disi > 0,
            "karsilastirma AYIRT EDICI — %d kayitta on-secim PLA DEGIL (hepsi PLA olsaydi "
            "iki taraf da guvenli varsayilani dondurup sahte yesil verirdi)" % pla_disi)
    kontrol(not sapan_m, "ON-SECIM esitligi: sapma YOK (%s)" % (sapan_m or "-"))
    kontrol(not sapan_k, "ILAN KURUSU esitligi: sapma YOK (%s)" % (sapan_k or "-"))
    # TANI JETONU da IKIZ TANIMDIR: iki dil ayni urun icin ayni kolu adlandirmali.
    # Ayrisirsa "taninmayan malzeme" sayimi (fail-loud kol) DILE GORE degisirdi.
    print("     tani dagilimi (ureteç): " + " · ".join(
        "%s=%d" % (k, v) for k, v in sorted(tani_sayac.items(), key=lambda x: -x[1])))
    kontrol(not sapan_t, "TANI JETONU esitligi: sapma YOK (%s)" % (sapan_t or "-"))
    kontrol(tani_sayac.get(filament_ortak.TANI_ONERI, 0) > 0
            and tani_sayac.get(filament_ortak.TANI_KAPSAM_DISI, 0) > 0,
            "tani ekseni AYIRT EDICI — en az iki farkli kol gercek katalogda olculdu "
            "(oneri=%d · kapsam-disi=%d)"
            % (tani_sayac.get(filament_ortak.TANI_ONERI, 0),
               tani_sayac.get(filament_ortak.TANI_KAPSAM_DISI, 0)))


# ------------------------------------------------------- (2)/(3) sayfa + parite
def _sayfa_uret(gecici, p, urunler, etiket):
    havuz = [x for x in urunler if x.get("kategori") == p.get("kategori")][:12]
    if p not in havuz:
        havuz = [p] + havuz
    ham = build.render_product(p, havuz, None)
    yol = os.path.join(gecici, "%s-%s.html" % (etiket, p["id"]))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yayin_yuzey.govde(ham, gecici))
    return yol


def _gorunur_tutar(html):
    """Sayfada JS ONCESI gorunen tutar metni (#opsiyonFiyat govdesi)."""
    m = re.search(r'id="opsiyonFiyat"[^>]*>(.*?)</div>', html, re.S)
    return m.group(1).strip() if m else None


def _ld_price(html):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") == "Product":
            return (d.get("offers") or {}).get("price")
    return None


def _metin_kurus(metin):
    """"455,00 TL" -> 45500. Ayristirilamazsa None."""
    if not metin:
        return None
    m = re.search(r"([0-9.]+),([0-9]{2})\s*TL", metin)
    if not m:
        return None
    return int(m.group(1).replace(".", "")) * 100 + int(m.group(2))


def bolum_2_3(gecici, urunler):
    ix = {p["id"]: p for p in urunler}
    node = _node()
    build.VARLIK_DIR = os.path.join(gecici, "varlik")
    build._VARLIK_ONBELLEK = {}

    fiksturler = list(FIKSTURLER)
    guvenli_fx = _turetilemeyen_fikstur(urunler)
    if guvenli_fx is None:
        kontrol(False, "onerisi TURETILEMEYEN denek uretilemedi — guvenli varsayilan "
                       "ekseni HIC olculmedi (sessiz yesil yasak)")
    else:
        fiksturler.append(guvenli_fx)

    # ----------------------------------------------------- ETIKET <-> BEKLE SINIF KONTROLU
    # 🔴 SINIF KUSURU (13 Agu 2026): etiket metni "PLA-disi oneri (ABS +%60)" gibi bir
    # yuzde tasirsa ve o yuzde OKAN'IN KILITLI katsayi tablosuyla CELISIRSE kapi yanlis
    # malzemeye sessizce kayar (olculdu: +%60 ASA kilidine denk dustu, ABS fiksturu ASA
    # on-secimine kaydi). Burada etiket metni COZULMEZ — kayit `bekle`'den turetme yok;
    # sadece iki alan ARASINDA tutarlilik FAIL-CLOSED kontrol edilir: etiket malzeme
    # adini iceriyor mu + etiket yuzdesi OKAN'IN KILITLI katsayi tablosuyla birebir ayni
    # mi. (Canli `build.FILAMENT_FARK` degil — kilitli tablo kullanilir, cunku spec
    # katsayi tablosunun KENDISINE dokunulmayacagini soyluyor; tablo ile kilitli referans
    # arasinda drift olabilir ve o kapinin isi degil.)
    # KILITLI REFERANS: PLA 0 · PETG 30 · ABS 50 · TPU 55 · ASA 60 (Karbon site haric).
    KILITLI_KATSAYI = {"PLA": 0, "PETG": 30, "ABS": 50, "TPU": 55, "ASA": 60}
    print("\n(0.5) ETIKET <-> BEKLE TUTARLILIK — etiket metni yanlis malzemeye cozulmesin")
    for fx in FIKSTURLER:
        bek = fx.get("bekle")
        ad = fx.get("ad") or ""
        if not bek or bek == build.VARSAYILAN_MALZEME:
            # onerisi olmayan / PLA fiksturunde etiket-yuzde kurali yok
            continue
        if bek not in ad:
            kontrol(False, "%s: etiket malzeme adini icermiyor (etiket=%r, bek=%r)"
                           % (fx["id"], ad, bek))
            continue
        yuzde_m = re.search(r"\+%(\d+)", ad)
        if not yuzde_m:
            kontrol(False, "%s: etiket yuzdeyi icermiyor (etiket=%r)" % (fx["id"], ad))
            continue
        etiket_yuzde = int(yuzde_m.group(1))
        if bek not in KILITLI_KATSAYI:
            kontrol(False, "%s: KILITLI_KATSAYI'da %r YOK (kilitli tablo ile etiket "
                           "dogrulanamadi)" % (fx["id"], bek))
            continue
        beklenen_yuzde = KILITLI_KATSAYI[bek]
        kontrol(etiket_yuzde == beklenen_yuzde,
                "%s: etiket yuzdesi (%%%d) = KILITLI_KATSAYI[%r] (%%%d)"
                % (fx["id"], etiket_yuzde, bek, beklenen_yuzde))

    print("\n(2) BAYRAK KAPALI — bugunku davranis (on-secim guvenli, tutar liste tutari)")
    build.ONERI_ONSECIM_ACIK = False
    for fx in fiksturler:
        p = fx.get("urun") or ix.get(fx["id"])
        if not p:
            olculemedi("fikstur katalogda YOK: %s" % fx["id"])
            continue
        liste = int(build.feed_price((p.get("fiyat") or "").strip())) * 100
        kontrol(build.on_secim_malzeme(p) == build.VARSAYILAN_MALZEME,
                "%s: kapaliyken on-secim guvenli varsayilan (%s)"
                % (fx["ad"], build.VARSAYILAN_MALZEME))
        kontrol(build.ilan_kurus(p) == liste,
                "%s: kapaliyken ilan tutari LISTE tutari (%d kurus)" % (fx["ad"], liste))

    print("\n(3) BAYRAK ACIK — sayfa · yapilandirilmis veri · sepet · sunucu KURUS KURUS")
    build.ONERI_ONSECIM_ACIK = True
    try:
        for fx in fiksturler:
            p = fx.get("urun") or ix.get(fx["id"])
            if not p:
                continue
            ad = fx["ad"]
            liste = int(build.feed_price((p.get("fiyat") or "").strip())) * 100
            secim = build.on_secim_malzeme(p)
            bek = fx["bekle"] or build.VARSAYILAN_MALZEME
            kontrol(secim == bek, "%s: on-secim %r (beklenen %r)" % (ad, secim, bek))
            ilan = build.ilan_kurus(p)
            beklenen = liste * (100 + build.FILAMENT_FARK.get(secim, 0)) // 100
            kontrol(ilan == beklenen,
                    "%s: ilan tutari on-secimden turedi (%d kurus, liste %d)"
                    % (ad, ilan, liste))
            if fx["bekle"] is None:
                kontrol(ilan == liste,
                        "%s: onerisi olmayan urunde tutar DEGISMEDI (regresyon 0)" % ad)

            html = _sayfa_uret(gecici, p, urunler, "acik")
            with open(html, encoding="utf-8") as f:
                h = f.read()
            secili = re.findall(
                r'class="[^"]*\bfil-cip\b[^"]*\bsecili\b[^"]*" data-malzeme="([^"]+)"', h)
            kontrol(secili == [secim],
                    "%s: sayfada onden secili cip = %r (olculen %r)" % (ad, secim, secili))
            gk = _metin_kurus(_gorunur_tutar(h))
            kontrol(gk == ilan,
                    "%s: SAYFADAKI gorunur tutar = ilan tutari (%s vs %s)" % (ad, gk, ilan))
            # 🔴 KAPSAM DEGISTI (isletme karari 11 Agu, Okan'in kendi secimi): markup ve
            # besleme BASLANGIC tabanini beyan eder; urun sayfasi ONERILEN malzemenin
            # tutarini vurgular. Yani yapilandirilmis veri artik LISTE tutarindadir ve
            # ilan tutarindan BILEREK ayrisir. Iddia bu yuzden "= ilan" degil "= liste":
            # markup'in sessizce urun sayfasi tutarina kaymasi da KIRMIZI yanmali
            # (Okan'in acikca reddettigi davranisin AYNASI).
            ld = _ld_price(h)
            ldk = None if ld is None else int(round(float(ld) * 100))
            kontrol(ldk == liste,
                    "%s: yapilandirilmis veri `price` = LISTE tutari (%s vs %s; ilan %s)"
                    % (ad, ldk, liste, ilan))
            fx_xml, _fx_adet = build.render_merchant_feed([p])
            fm = re.search(r"<g:price>([0-9.]+)\s*TRY</g:price>", fx_xml)
            fk = None if not fm else int(round(float(fm.group(1)) * 100))
            if fk is None:
                olculemedi("%s: besleme satiri uretilmedi (gorselsiz/fiyatsiz olabilir)" % ad)
            else:
                kontrol(fk == liste,
                        "%s: besleme `g:price` = LISTE tutari (%s vs %s; ilan %s)"
                        % (ad, fk, liste, ilan))

            if not node:
                olculemedi("%s: node yok — sepet/sunucu ayagi olculemedi" % ad)
                continue
            sepet_kapisi.ROOT = ROOT
            veri, hata = sepet_kapisi.node_kos(gecici, html)
            if veri is None:
                olculemedi("%s: sayfa kosucusu dustu (%s)" % (ad, hata))
                continue
            kontrol(not veri.get("scriptHatalari"),
                    "%s: sayfa scriptleri hatasiz kostu (%s)" % (ad, veri.get("scriptHatalari")))
            s1 = (veri["adimlar"]["c1"].get("sepet") or [])
            kontrol(len(s1) == 1 and s1[0].get("malzeme") == secim,
                    "%s: hic secim yapmadan tiklama on-secimli satiri yazdi (%s)"
                    % (ad, s1[0].get("malzeme") if s1 else "-"))
            kontrol(veri.get("istemciBirim") == ilan,
                    "%s: SEPET satiri = ilan tutari (%s vs %s)"
                    % (ad, veri.get("istemciBirim"), ilan))
            sk = _sunucu_kurus(gecici, p, s1[0] if s1 else None)
            kontrol(sk == ilan,
                    "%s: SUNUCU tutari = ilan tutari (%s vs %s)" % (ad, sk, ilan))
    finally:
        build.ONERI_ONSECIM_ACIK = False


def _sunucu_kurus(gecici, urun, satir):
    """Istemcinin yazdigi satiri SUNUCU fiyat kolundan gecirir (sepet kapisinin kosucusu)."""
    if not satir:
        return None
    girdi = {
        "kalem": {"id": satir.get("id"), "malzeme": satir.get("malzeme"),
                  "renk": satir.get("renk"), "renk_ozel": satir.get("renk_ozel") or "",
                  "adet": satir.get("adet")},
        "d1": {"kategori": urun.get("kategori"), "fiyat": urun.get("fiyat"),
               "tur": urun.get("tur")},
    }
    gy = os.path.join(gecici, "sunucu-girdi-%s.json" % urun["id"])
    with open(gy, "w", encoding="utf-8") as f:
        json.dump(girdi, f, ensure_ascii=False)
    ry = os.path.join(gecici, "sunucu-kosucu.js")
    with open(ry, "w", encoding="utf-8") as f:
        f.write(sepet_kapisi.SUNUCU_RUNNER)
    r = subprocess.run([_node(), ry, ROOT, gy], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return json.loads(r.stdout).get("sunucuBirim")


# ------------------------------------------------------------------ mutasyon
# (kod, aciklama, hedef dosya, eski, yeni, beklenen_rc)
MUTANTLAR = [
    ("N1", "SESSIZ ZAM: ilan tutari on-secimi degil sabit varsayilani okuyor",
     "tools/build.py",
     "    return _birim_kurus(p, on_secim_malzeme(p))",
     "    return _birim_kurus(p, VARSAYILAN_MALZEME)", 1),
    ("N2", "cip sabit varsayilanda kaldi (tutar ilerledi, secim geride)",
     "tools/build.py",
     '    secili = on_secim_malzeme(p)',
     '    secili = VARSAYILAN_MALZEME', 1),
    # N3 YON DEGISTIRDI: markup artik BASLANGIC tabanini beyan ediyor (isletme karari).
    # Tehlikeli yon bu yuzden TERSINE dondu — markup'in urun sayfasi tutarina KAYMASI
    # Okan'in acikca reddettigi davranistir; mutant onu yapar, kapi KIRMIZI yakmali.
    ("N3", "markup urun sayfasi tutarina kaydi (baslangic tabani beyani bozuldu)",
     "tools/build.py",
     "    ld_fiyat = ilan_tl_metni(vitrin_kurus(p)) or pnum",
     "    ld_fiyat = ilan_tl_metni(ilan_kurus(p)) or pnum",
     1),
    ("N11", "besleme urun sayfasi tutarina kaydi (dis listeleme sessizce zamlandi)",
     "tools/build.py",
     "        if ONERI_VITRIN_ACIK:\n            price = ilan_tl_metni(vitrin_kurus(p)) or price",
     "        if ONERI_ONSECIM_ACIK:\n            price = ilan_tl_metni(ilan_kurus(p)) or price",
     1),
    ("N4", "istemci kurali ureteç kuralindan ayristi (sira tersine dondu)",
     "secenekler.js",
     "      for (i = 0; i < harita.length; i++) {",
     "      for (i = harita.length - 1; i >= 0; i--) {", 1),
    ("N5", "JS oncesi statik tutar liste tutarinda birakildi", "tools/build.py",
     "            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))",
     '            baslangic_fiyat = esc(fiyat) + "&#39;den başlayan"', 1),
    ("N6", "on-secim guvenli varsayilana DUSMUYOR (katsayisiz ad gecebilir)",
     "tools/filament_ortak.py",
     "        if ad in katsayi_adlari:\n            return (TANI_ONERI, ad)",
     "        if True:\n            return (TANI_ONERI, ad)", 1),
    # N10 = TANINMAYAN kolunun bekcisi. `tavsiyeFilament` DOLU ama adlari sitede
    # satilmayan urun, "onerisi hic olmayan urun" ile AYNI jetona cokerse sessiz
    # dususu sayan kol (tools/d1-fiyat-parite-kapisi.py eksen E6) korlesir. Mutant yalniz
    # URETEC tarafini cokertir -> ikiz tani ekseni ayrismayi KIRMIZI yakar.
    ("N10", "TANINMAYAN kolu sessizce 'varsayilan'a cokuyor (veri kusuru gorunmez)",
     "tools/filament_ortak.py",
     "    return ((TANI_TANINMAYAN if onerili else TANI_VARSAYILAN), guvenli)",
     "    return (TANI_VARSAYILAN, guvenli)", 1),
    # N9 = onerisi TURETILEMEYEN denegin BEKCISI. Denek her kosumda katalogdan
    # turetilir; bu mutant o turetmenin TAUTOLOJI OLMADIGINI kanitlar: alani dolu
    # ama adlari sitede satilmayan urun, elenen override'dan sonra kategori
    # haritasina DUSERSE sessizce %30 zamlanir. Denek gercekten sinifta ise bu
    # mutant KIRMIZI yakar; denek bayatlar/sinif disi kalirsa N9 YESILE doner ve
    # bayatlama bir sonraki kosumda GORULUR (sessiz kalamaz).
    ("N9", "elenen oneri kategori haritasina DUSUYOR (bozuk alanda sessiz zam)",
     "tools/filament_ortak.py",
     '        return [{"ad": a, "rozet": "Tavsiyemiz"} for a in override '
     'if a in site_adlar]',
     '        _o = [{"ad": a, "rozet": "Tavsiyemiz"} for a in override '
     'if a in site_adlar]\n        if _o:\n            return _o', 1),
    ("N8", "bayrak kapaliyken kural yine de uygulaniyor (habersiz zam)",
     "tools/filament_ortak.py",
     "    if not acik:\n        return (TANI_KAPALI, guvenli)",
     "    if False:\n        return (TANI_KAPALI, guvenli)", 1),
    ("N7", "KONTROL: davranisi degistirmeyen yeniden adlandirma", "tools/build.py",
     "def fiziksel_mi(p):\n    return bool(p) and p.get(\"tur\") == TUR_FIZIKSEL",
     "def fiziksel_mi(kayit):\n    return bool(kayit) and kayit.get(\"tur\") == TUR_FIZIKSEL",
     0),
]
MUTASYON_KOK_DOSYALARI = ("konfigur.js", "index.html", "secenekler.js")


def _gecici_kok():
    tmp = tempfile.mkdtemp(prefix="onsecim-mut-")
    shutil.copytree(TOOLS, os.path.join(tmp, "tools"), symlinks=True)
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git", "varlik", "urun", "_yayin"):
            continue
        kaynak = os.path.join(ROOT, ad)
        if ad in MUTASYON_KOK_DOSYALARI and os.path.isfile(kaynak):
            shutil.copy2(kaynak, os.path.join(tmp, ad))
        else:
            os.symlink(kaynak, os.path.join(tmp, ad))
    return tmp


def _uygula(yol, eski, yeni):
    with open(yol, encoding="utf-8") as f:
        s = f.read()
    if eski not in s:
        return False
    with open(yol, "w", encoding="utf-8") as f:
        f.write(s.replace(eski, yeni, 1))
    return True


def mutasyon():
    print("\n" + "=" * 72)
    print("MUTASYON NOBETI — kapi OLU mu? (%d kirmizi + bir KONTROL yesil)"
          % (len(MUTANTLAR) - 1))
    kendi = os.path.basename(os.path.abspath(__file__))
    sapan = []
    print("\n%-4s %-58s %-9s %-9s %s" % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "SONUC"))
    for kod, aciklama, dosya, eski, yeni, beklenen in MUTANTLAR:
        tmp = _gecici_kok()
        try:
            if not _uygula(os.path.join(tmp, *dosya.split("/")), eski, yeni):
                sapan.append("%s: capa uygulanamadi (%r)" % (kod, eski[:60]))
                print("%-4s %-58s %-9s %-9s CAPA YOK" % (kod, aciklama[:58], beklenen, "-"))
                continue
            r = subprocess.run([sys.executable, os.path.join(tmp, "tools", kendi)],
                               capture_output=True, text=True, cwd=tmp)
            rc = r.returncode
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        renk = "KIRMIZI" if rc == 1 else ("YESIL" if rc == 0 else "rc=%d" % rc)
        tamam = (rc == beklenen)
        if not tamam:
            sapan.append("%s: beklenen rc=%d, olculen rc=%d" % (kod, beklenen, rc))
        print("%-4s %-58s %-9s %-9s %s"
              % (kod, aciklama[:58], "KIRMIZI" if beklenen else "YESIL", renk,
                 "OK" if tamam else "SAPTI"))
    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: %d mutantin hepsi beklenen rengi verdi (N7 kontrol mutanti YESIL)."
          % len(MUTANTLAR))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true")
    a = ap.parse_args()

    print("ON-SECILI MALZEME <-> ILAN EDILEN TUTAR PARITE KAPISI")
    print("depo bayragi ONERI_ONSECIM_ACIK = %s" % build.ONERI_ONSECIM_ACIK)
    urunler = _urunler()
    gecici = tempfile.mkdtemp(prefix="onsecim-")
    try:
        bolum_0(urunler)
        bolum_1(gecici, urunler)
        bolum_2_3(gecici, urunler)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("\n" + "-" * 72)
    if OLCULEMEDI:
        print("OLCULEMEDI (%d):" % len(OLCULEMEDI))
        for m in OLCULEMEDI:
            print("  - " + m)
    if HATALAR:
        print("SONUC: KIRMIZI ❌ — %d iddia dustu" % len(HATALAR))
        for m in HATALAR:
            print("  - " + m)
        return 1
    if OLCULEMEDI:
        print("SONUC: OLCULEMEDI ⚠️")
        return 2
    print("SONUC: YESIL ✅ — on-secim ile ilan edilen tutar AYRISAMAZ")

    if a.mutasyon:
        return mutasyon()
    return 0


if __name__ == "__main__":
    sys.exit(main())

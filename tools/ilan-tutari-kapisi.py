#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ILAN EDILEN TUTAR — KART <-> YAPILANDIRILMIS VERI <-> URUN SAYFASI KAPISI (12 Agu 2026).

    python3 tools/ilan-tutari-kapisi.py
    python3 tools/ilan-tutari-kapisi.py --ozet        # sayfa dokumu basmadan yalniz hukum

NEDEN VAR — HATA SINIFI SESSIZ VE PARALI. Okan'in karari (12 Agu):
  1. VITRIN (kart) = PLA tabani (en ucuz malzemenin tutari)
  2. URUN SAYFASI  = ONERILEN malzemenin tutari
  3. KART METNI    = "X TL'den baslayan" (duz "X TL" DEGIL)
  4. MARKUP        = AggregateOffer lowPrice/highPrice araligi
Ayni urun BILEREK iki tutar gosterir. Tam bu yuzden ucu de AYNI turetme noktasindan
cikmak zorundadir: biri digerinden bagimsiz hesaplanirsa musteri kartta 430 TL gorup
sepete 559 TL yazar, arama motoruna 430 beyan edilir ve HICBIR YERDE alarm calmaz.
Bu depoda ayni sinif iki kez olculdu (11 Agu sessiz zam; 12 Agu markup tabani
`price_number` ile kart tabani `feed_price` ayrisip 1 kayitta 300 TL <-> 30.030 TL).

KAPININ IDDIASI (hepsi KOSULARAK olculur):
  (1) IKIZ TANIM  — kural iki dilde yazili (ureteç: tools/build.py malzeme_aralikli_mi /
                    kart_tutar_metni / en_yuksek_kurus · istemci: secenekler.js
                    malzemeAralikliMi / kartTutarMetni / enYuksekBirimKurus). TUM KATALOG
                    uzerinde ucu de birebir karsilastirilir; tek satirlik sapma KIRMIZI.
  (2) TAM KAPSAM  — URETILEN HER URUN SAYFASI acilir (ORNEKLEME YOK) ve her birinde:
                      lowPrice == KART tutari                       (baslangic tabani)
                      lowPrice <= highPrice                          (aralik gecerli)
                      SAYFADAKI gorunur tutar == ONERILEN malzemenin tutari
                      kart metni "…'den baslayan" ekini TASIYOR <=> tutar malzemeyle
                        yukselebiliyor  (ek ne eksik ne fazla)
                    Olculemeyen sayfa (LD yok / tutar ayristirilamadi) SESSIZ GECMEZ:
                    OLCULEMEDI listesine yazilir ve cikis kodu SIFIR DISI olur.
  (3) TEK SAYIM   — insana basilan ozet, hukmu besleyen KUMEDEN turetilir. Ikinci sayac
                    tutulmaz ([[kapi-ozeti-hukumden-ayrisir]]: bu depoda kapi KIRMIZI iken
                    ozeti "sapan 0" yaziyordu).

NE IDDIA EDILMEZ (beyan edilen sinirlar — sessiz yesil yasak, sayilar RAPORDA basilir):
  * OLCUYE OZEL (parametrik) ve YAPILANDIRICILI (konfigur) urunde gorunen tutar tabandan
    CANLI hesaplanir; o kolda "onerilen malzeme tutari" diye bir sey YOKTUR ve markup
    TEKIL Offer'dir. Kapi orada aralik/onerilen iddiasi ETMEZ, yalniz SAYAR.
  * HAZIR TICARI MALDA uretim malzemesi karsiliksizdir (carpan 1,00) -> aralik YOK.
  * Gorsel yerlesim/piksel. Olculen sey METIN ve SAYIDIR.

CIKIS: 0 yesil · 1 kirmizi · 2 olculemedi (node/render yok). Depoya YAZMAZ.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build            # noqa: E402
import filament_ortak   # noqa: E402

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


# ═══════════════════════════════════════════════ (1) IKIZ TANIM — tam katalog, GERCEK kod
# Kural KOPYALANMAZ: gercek secenekler.js node:vm'de kosar.
JS_IKIZ_KOSUCU = r"""
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const ctx = { console: { log() {} }, Math, JSON, Date };
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), ctx, { filename: "secenekler.js" });
const S = ctx.PRUVO_SECENEK;
const urunler = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const ref = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
const out = {};
for (const p of urunler) {
  const ham = String(p.fiyat == null ? "" : p.fiyat).replace(/^\s+|\s+$/g, "");
  out[p.id] = [S.malzemeAralikliMi(p) ? 1 : 0,
               S.kartTutarMetni(p, ham),
               S.enYuksekBirimKurus(p),
               S.vitrinBirimKurus(p, ref)];
}
process.stdout.write(JSON.stringify({ sonek: S.BASLAYAN_SONEK, sonuc: out }));
"""


def bolum_1(gecici, urunler):
    print("\n(1) IKIZ TANIM — kart metni/kapsam/tavan iki dilde AYNI mi (TUM KATALOG)")
    node = shutil.which("node")
    if not node:
        olculemedi("node yok — ikiz tanim ekseni olculemedi")
        return
    uy = os.path.join(gecici, "urunler-ikiz.json")
    with open(uy, "w", encoding="utf-8") as f:
        json.dump(urunler, f, ensure_ascii=False)
    ry = os.path.join(gecici, "ref-ikiz.json")
    with open(ry, "w", encoding="utf-8") as f:
        json.dump(filament_ortak.referans(), f, ensure_ascii=False)
    ky = os.path.join(gecici, "ikiz-kosucu.js")
    with open(ky, "w", encoding="utf-8") as f:
        f.write(JS_IKIZ_KOSUCU)
    r = subprocess.run([node, ky, os.path.join(ROOT, "secenekler.js"), uy, ry],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        olculemedi("ikiz kosucusu dustu: %s" % (r.stderr or "")[-600:])
        return
    veri = json.loads(r.stdout)
    kontrol(veri.get("sonek") == build.BASLAYAN_SONEK,
            "\"…'den baslayan\" eki TEK KAYNAK (istemci %r == ureteç %r)"
            % (veri.get("sonek"), build.BASLAYAN_SONEK))
    js = veri["sonuc"]

    sapan_k, sapan_m, sapan_t, olculen, aralikli = [], [], [], 0, 0
    for p in urunler:
        pid = p["id"]
        if pid not in js:
            continue
        olculen += 1
        ham = (p.get("fiyat") or "").strip()
        py_a = 1 if build.malzeme_aralikli_mi(p) else 0
        py_m = build.kart_tutar_metni(p, ham)
        py_t = build.en_yuksek_kurus(p)
        aralikli += py_a
        if js[pid][0] != py_a and len(sapan_k) < 5:
            sapan_k.append("%s: ureteç=%s istemci=%s" % (pid, py_a, js[pid][0]))
        if js[pid][1] != py_m and len(sapan_m) < 5:
            sapan_m.append("%s: ureteç=%r istemci=%r" % (pid, py_m, js[pid][1]))
        if js[pid][2] != py_t and len(sapan_t) < 5:
            sapan_t.append("%s: ureteç=%s istemci=%s" % (pid, py_t, js[pid][2]))
    kontrol(olculen == len(urunler),
            "tum katalog karsilastirildi (%d/%d kayit)" % (olculen, len(urunler)))
    # POZITIF TANIYICI: iki taraf da "hayir" deseydi karsilastirma hicbir sey olcmezdi.
    kontrol(aralikli > 0,
            "karsilastirma AYIRT EDICI — %d kayitta tutar malzemeyle YUKSELEBILIYOR "
            "(hicbiri olmasaydi kart metni ekseni sahte yesil verirdi)" % aralikli)
    kontrol(not sapan_k, "KAPSAM (malzemeAralikliMi) esitligi: sapma YOK (%s)"
            % (sapan_k or "-"))
    kontrol(not sapan_m, "KART METNI esitligi: sapma YOK (%s)" % (sapan_m or "-"))
    kontrol(not sapan_t, "TAVAN (en pahali malzeme) esitligi: sapma YOK (%s)"
            % (sapan_t or "-"))


# ═══════════════════════════════════════════════ (2) TAM KAPSAM — uretilen HER sayfa
_LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
_GORUNUR_RE = re.compile(r'id="opsiyonFiyat"[^>]*>(.*?)</div>', re.S)
_TUTAR_RE = re.compile(r"([0-9][0-9.]*),([0-9]{2})\s*TL")


def _product_ld(html):
    for m in _LD_RE.finditer(html):
        try:
            d = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") == "Product":
            return d
    return None


def _kurus(tl_dize):
    """JSON-LD TL dizesini kurusa cevirir ('430' / '430.50' -> 43000 / 43050)."""
    if tl_dize is None:
        return None
    try:
        return int(round(float(tl_dize) * 100))
    except (TypeError, ValueError):
        return None


def _kart_kurus(p):
    """KARTIN yazdigi SAYISAL tutar (kurus) ya da None (kart sayi basmiyor).

    🔴 index.html `kartFiyatMetni` + `ilanFiyatMetni` kollariyla AYNI karar:
      * sabit fiyatli urun -> kart yuzeyinin kendi turetmesi (build.vitrin_kurus)
      * olcuye ozel (parametrik) -> taban-fiyatlar.js haritasinin TEK KAYNAGI olan
        semadaki `tabanFiyatTL` (satisa KAPALI ailede harita bu id'yi TASIMAZ -> None)
      * ikisi de yoksa kart tutar basmaz -> None
    Boylece parametrik kol "olculemedi" diye SESSIZCE atlanmaz; kart tutari ile markup
    tabani orada da KARSILASTIRILIR."""
    if p.get("parametrik"):
        sema = build.konf_sema(p.get("id"))
        if not sema or build.aile_satis_kapali_mi(sema):
            return None
        taban = sema.get("tabanFiyatTL")
        if isinstance(taban, (int, float)) and not isinstance(taban, bool) and taban > 0:
            return int(round(taban * 100))
        return None
    return build.vitrin_kurus(p)


def _gorunur_kurus(html):
    """Sayfada JS ONCESI gorunen tutar (#opsiyonFiyat) -> kurus ya da None."""
    m = _GORUNUR_RE.search(html)
    if not m:
        return None
    t = _TUTAR_RE.search(m.group(1))
    if not t:
        return None
    return int(t.group(1).replace(".", "")) * 100 + int(t.group(2))


def _sayfa_bulgusu(p, html):
    """Bir urun sayfasinin BULGULARI: (ihlaller, olculemedi, sinif).

    🔴 TEK SAYIM NOKTASI: hukum de ozet de BU fonksiyonun dondurdugu kumeden turer;
    kapi baska hicbir yerde ikinci bir sayac tutmaz."""
    pid = p["id"]
    ihlal, olcum_yok = [], []
    aralikli = build.malzeme_aralikli_mi(p)
    sinif = ("aralikli" if aralikli else
             ("olcuye-ozel" if (p.get("parametrik") or p.get("konfigur")) else
              ("hazir-ticari" if build.fiziksel_mi(p) else "aralik-disi")))

    ld = _product_ld(html)
    if ld is None:
        olcum_yok.append("%s: sayfada Product JSON-LD YOK" % pid)
        return ihlal, olcum_yok, sinif
    offers = ld.get("offers")
    kart_k = _kart_kurus(p)                 # KARTIN yazdigi tutar (baslangic tabani)

    if offers is not None and not isinstance(offers, dict):
        olcum_yok.append("%s: offers beklenmedik bicimde (%s)" % (pid, type(offers).__name__))
        return ihlal, olcum_yok, sinif

    ham_low = None if offers is None else offers.get("lowPrice", offers.get("price"))
    low = _kurus(ham_low)
    high = None if offers is None else _kurus(offers.get("highPrice"))
    if ham_low is not None and low is None:
        olcum_yok.append("%s: markup tutari sayisal degil (%r)" % (pid, ham_low))
        return ihlal, olcum_yok, sinif

    # --- A. MARKUP TABANI == KARTIN YAZDIGI TUTAR. Iki yuzeyden biri sayi basip digeri
    #        basmiyorsa da ayrisma vardir — bu yuzden VARLIK da esitlik de olculur.
    if (low is None) != (kart_k is None):
        ihlal.append("%s: markup tabani ile kart tutari VARLIK olarak ayrisiyor "
                     "(markup=%s krs · kart=%s krs)" % (pid, low, kart_k))
    elif low is not None and low != kart_k:
        ihlal.append("%s: lowPrice != KART tutari (%s vs %s krs)" % (pid, low, kart_k))
    if low is None:
        return ihlal, olcum_yok, sinif

    # --- B. aralik: lowPrice <= highPrice ve aralik DOGRU sinifta acilmis
    beklenen_tip = "AggregateOffer" if aralikli else "Offer"
    if offers.get("@type") != beklenen_tip:
        ihlal.append("%s: offers @type=%r (beklenen %r; sinif=%s)"
                     % (pid, offers.get("@type"), beklenen_tip, sinif))
    if aralikli:
        if high is None:
            ihlal.append("%s: aralikli urunde highPrice YOK" % pid)
        else:
            if not (low <= high):
                ihlal.append("%s: lowPrice > highPrice (%s > %s krs)" % (pid, low, high))
            beklenen_high = build.en_yuksek_kurus(p)
            if high != beklenen_high:
                ihlal.append("%s: highPrice EN PAHALI malzemeden turemedi (%s vs %s krs)"
                             % (pid, high, beklenen_high))
    elif high is not None:
        ihlal.append("%s: aralik-disi urunde highPrice basilmis (%s krs)" % (pid, high))

    # --- C. SAYFADAKI gorunur tutar == ONERILEN malzemenin tutari (yalniz malzeme
    #        secicisi basilan kol; olcuye ozel/yapilandiricili urunde tutar CANLI hesaplanir)
    if aralikli:
        gor = _gorunur_kurus(html)
        ilan = build.ilan_kurus(p)
        if gor is None:
            olcum_yok.append("%s: sayfadaki gorunur tutar ayristirilamadi" % pid)
        elif ilan is None:
            olcum_yok.append("%s: onerilen malzeme tutari turetilemedi" % pid)
        elif gor != ilan:
            ihlal.append("%s: URUN SAYFASI tutari onerilen malzemeden turemedi "
                         "(%s vs %s krs)" % (pid, gor, ilan))

    # --- D. KART METNI: ek ne eksik ne fazla
    ham = (p.get("fiyat") or "").strip()
    if ham:
        metin = build.kart_tutar_metni(p, ham)
        ekli = metin.endswith(build.BASLAYAN_SONEK)
        if aralikli and not ekli:
            ihlal.append("%s: kart metni duz tutar yaziyor (%r) — baslangic beyani YOK"
                         % (pid, metin))
        if (not aralikli) and ekli:
            ihlal.append("%s: tutar malzemeyle yukselmedigi halde kart 'baslayan' diyor "
                         "(%r)" % (pid, metin))

    return ihlal, olcum_yok, sinif


def bolum_2(gecici, urunler, ozet_modu):
    print("\n(2) TAM KAPSAM — uretilen HER urun sayfasi (ORNEKLEME YOK)")
    build.VARLIK_DIR = os.path.join(gecici, "varlik")
    build._VARLIK_ONBELLEK = {}
    os.makedirs(build.VARLIK_DIR, exist_ok=True)
    havuz = urunler[:12]                     # yalniz "ilgili urun" bolumu icin

    # 🔴 HUKMU BESLEYEN TEK KUME: asagidaki uc liste + sinif sayaci. Ozet de bunlardan
    # turer; ikinci sayim noktasi ACILMAZ.
    ihlaller, olcum_yok, sinif_sayaci = [], [], {}
    t0 = time.time()
    for i, p in enumerate(urunler):
        try:
            html = build.render_product(p, havuz, None)
        except Exception as e:                                    # noqa: BLE001
            olcum_yok.append("%s: sayfa URETILEMEDI (%s)" % (p.get("id"), str(e)[:120]))
            continue
        i_, o_, sinif = _sayfa_bulgusu(p, html)
        ihlaller.extend(i_)
        olcum_yok.extend(o_)
        sinif_sayaci[sinif] = sinif_sayaci.get(sinif, 0) + 1
        if not ozet_modu and (i + 1) % 5000 == 0:
            print("     … %d/%d sayfa (%.0f sn)" % (i + 1, len(urunler), time.time() - t0))
    olculen = sum(sinif_sayaci.values())
    print("     olculen sayfa: %d / %d  (%.0f sn)"
          % (olculen, len(urunler), time.time() - t0))
    print("     sinif dagilimi: " + " · ".join(
        "%s=%d" % (k, v) for k, v in sorted(sinif_sayaci.items(), key=lambda x: -x[1])))

    kontrol(olculen == len(urunler),
            "TUM katalog sayfasi uretildi ve olculdu (%d/%d)" % (olculen, len(urunler)))
    kontrol(sinif_sayaci.get("aralikli", 0) > 0,
            "olcum AYIRT EDICI — %d sayfada aralik iddiasi GERCEKTEN kosuldu"
            % sinif_sayaci.get("aralikli", 0))
    kontrol(not ihlaller,
            "kart tutari <-> lowPrice <-> urun sayfasi tutari: SAPAN %d"
            % len(ihlaller))
    for m in ihlaller[:10]:
        print("       - " + m)
    for m in olcum_yok:
        olculemedi(m)
    return ihlaller, olcum_yok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ozet", action="store_true",
                    help="ilerleme satiri basma (hukum ayni)")
    a = ap.parse_args()

    print("ILAN EDILEN TUTAR KAPISI — kart <-> yapilandirilmis veri <-> urun sayfasi")
    print("depo bayraklari: ONERI_ONSECIM_ACIK=%s · ONERI_VITRIN_ACIK=%s"
          % (build.ONERI_ONSECIM_ACIK, build.ONERI_VITRIN_ACIK))
    print("en pahali malzeme farki: +%%%d" % build.en_pahali_malzeme_farki())
    urunler = _urunler()
    gecici = tempfile.mkdtemp(prefix="ilan-tutari-")
    try:
        bolum_1(gecici, urunler)
        bolum_2(gecici, urunler, a.ozet)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("\n" + "-" * 72)
    if OLCULEMEDI:
        print("OLCULEMEDI (%d):" % len(OLCULEMEDI))
        for m in OLCULEMEDI[:10]:
            print("  - " + m)
    if HATALAR:
        print("SONUC: KIRMIZI ❌ — %d iddia dustu" % len(HATALAR))
        for m in HATALAR:
            print("  - " + m)
        return 1
    if OLCULEMEDI:
        print("SONUC: OLCULEMEDI ⚠️ — sessiz yesil YOK")
        return 2
    print("SONUC: YESIL ✅ — kart tutari, markup araligi ve urun sayfasi tutari "
          "TEK turetme noktasindan cikiyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())

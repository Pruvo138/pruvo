#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VITRIN <-> D1 FIYAT PARITE KAPISI + KAPSAM SIZINTISI NOBETI (11 Agu 2026).

    python3 tools/d1-fiyat-parite-kapisi.py

NEDEN VAR — HATA SINIFI SESSIZ, PARALI VE IKI AGIZLI
════════════════════════════════════════════════════════════════════════════════
Isletme karari (11 Agu): musteri urunun ICINE girdiginde ONERILEN malzeme onden
secili gelir ve tutar ondan turer; LISTE yuzeyi (ana sayfa · kategori · arama
sonucu karti) ise BASLANGIC tabaninda KALIR. Yani ayni urun iki tutar gosterir ve
bu BILINCLIDIR.

Bu kararin sessiz-hata yuzeyi katalogun IKINCI agzidir. Katalog ayrica bir kenar
veritabaninda tutulur ve mesaj kanali fiyati ORADAN okur; o kolon urunun HAM liste
tutarini tasir. Kart kolu urun sayfasi koluyla birlikte yukari kayarsa:

    site karti 455 TL der   ·   mesaj kanali 350 TL der

Iki agiz ayni urun icin iki fiyat soyler. Hicbir test kirmizi yanmaz: iki taraf da
KENDI icinde tutarlidir. Musteri ya guvenini kaybeder ya da dusuk tutari talep eder.
Sinif [[ikiz-tanim-sessiz-ayrisma]] + [[hukum-yanlis-birimde]]: toplu yesil, tekil
ekseni gizler.

KAPININ IDDIASI (alti eksen, hepsi KOSULARAK olculur)
════════════════════════════════════════════════════════════════════════════════
  E1 KENAR CAPASI     kenar senkronu `fiyat` kolonuna urunun HAM alanini yaziyor mu?
                      (turetilmis bir tutar yazmaya baslarsa bu kapinin kiyas tabani
                      degisir -> OLCULEMEDI, sessiz yesil DEGIL)
  E2 YUZEY CAPASI     kart yuzeyi KENDI anahtarini/turetmesini mi cagiriyor? Urun
                      sayfasi turetmesi kart koluna SIZMIS mi?
  E3 PARITE           TUM KATALOGDA kart tutari == ham liste tutari. Sapan urun 0.
  E4 POZITIF TANIYICI kart anahtari ACIK bir kopyada sapan > 0 olmali. Olmazsa E3
                      hicbir sey olcmuyordur (sahte yesil).
  E5 IKI YUZEY AYRI   urun sayfasi tutari ile kart tutari GERCEKTEN farklilasiyor mu?
                      Farklilasmiyorsa ya urun kolu kapalidir ya kural olmustur.
  E6 TANINMAYAN KOL   malzeme onerisi TASIYAN ama adlari taninmayan urun SAYILIR ve
                      BASILIR. Kutukte OLMAYAN yeni bir kayit cikarsa KIRMIZI.

NE IDDIA EDILMEZ (beyan edilen kor noktalar — sessiz yesil yasak)
════════════════════════════════════════════════════════════════════════════════
  * Kenar veritabaninin CANLI icerigi. Bu kapi AGA CIKMAZ; senkronun YAZDIGI degeri
    kaynaktan turetir. "Canliya gercekten yazildi mi" ayri bir nobetin isidir.
  * Mesaj kanalinin o tutari nasil bicimledigi (baska evin duzlemi).
  * Kart METNI ("X TL" mi "X TL'den baslayan" mi) ve yapilandirilmis verinin
    coklu-teklif bicimi: MIMAR KARARI bekliyor, bu kapi bicime karismaz.
  * Olcuye ozel / yapilandiricili / hazir ticari mal kolu: kural orada zaten
    uygulanmaz (kapsam-disi jetonu).
  * KARDES DEPO (edge Worker kaynagi, ~/dev/pruvo-bot) — BASKA BIR MIMARIN EVI.
    Diskte VARSA E10 onu okur ve kart kolu ACIKKEN eksik alani KIRMIZI yakar
    (hukum bizim BAYRAGIMIZ hakkindadir, onlarin kodu hakkinda degil). Diskte
    YOKSA (CI fresh checkout) bu bir olcum boslugu DEGIL kapsam disiligidir:
    `KARDES_AGAC_KAPSAM_DISI` satiri basilir, cikis kodu ETKILENMEZ. Ayni
    doktrin: tools/edge-kart-kapisi.py. KAPSAM DISILIK YALNIZ BU HUKMU KAPSAR:
    kart kolu KAPALIYKEN oneri alaninin kart tutarini kaydirmadigi kaniti (E10b)
    BIZIM duzlemimizdir, kardes agac olmasa da HER KOSUMDA verilir.

CIKIS: 0 yesil · 1 kirmizi · 2 olculemedi. Depoya YAZMAZ, aga CIKMAZ.
"""
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

# ---------------------------------------------------------------- jetonlar (AYRIK)
# 🔴 Jetonlar birbirinin ALT DIZESI DEGILDIR ([[maskeleme-kismi-kapatma]]): bir kolu
# olduren mutant, baska bir kolun govdesine gomulu ortak metinden GECEMEZ.
JETON_D1_HAM = "KENAR_KOLON_HAM"
JETON_D1_TURETILMIS = "KENAR_KOLON_TURETILMIS"
JETON_YUZEY_AYRI = "KART_YUZEYI_AYRIK"
JETON_YUZEY_SIZDI = "KART_YUZEYI_SIZDI"
JETON_OLCULEMEDI = "COZULEMEDI"
# E10'un kardes-depo kolu: agac YOKKEN verilen KAPSAM DISI hukmunun kendi ayrik jetonu.
# Digerlerinin alt dizesi DEGILDIR; mutasyon bataryasi (M13) tam bu jetonu arar, boylece
# "kapi sustu" ile "kapi kapsam disi dedi" ayni satirdan okunamaz.
JETON_KARDES_KAPSAM_DISI = "KARDES_AGAC_KAPSAM_DISI"
# E10'un kardes agac VARKEN verdigi hukmun jetonu. M3 tam bunu arar (kardes agaci
# SENTETIK fikstur ile GORUNUR kilar): onarim "kardes agac yoksa kapsam disi" kolunu
# agac VARKEN de yutacak sekilde genisletilirse, bu jeton HATALAR'dan kaybolur ve
# batarya SAPTI der.
JETON_KARDES_HUKUM = "KENAR_KART_HUKMU"
# 🔴 12 AGU 2026 — ALAN NOTRLUGU KENDI DUZLEMIMIZDIR, KARDES AGACA BAGLI DEGILDIR.
# "Kart kolu KAPALIYKEN `tavsiyeFilament` alani kart tutarini KAYDIRMAZ" hukmu yalnizca
# build.py + filament_ortak.py hakkindadir; kardes deponun diskte olup olmamasiyla
# hicbir ilgisi YOKTUR. Bu jeton o hukmun AYRIK izidir (M12 tam bunu arar) ve
# digerlerinin ALT DIZESI DEGILDIR ([[maskeleme-kismi-kapatma]]).
JETON_KART_ALAN_NOTR = "KART_ALAN_NOTRLUGU"

# ------------------------------------------------- TANINMAYAN MALZEME KUTUGU (veri kusuru)
# 🔴 NEDEN KUTUK VAR ve NEDEN SADECE EKLEMEYE KIRMIZI YANAR ([[envanter-drift-parti-basina]]):
# katalog verisi baska bir evin duzlemidir; buradan DUZELTILMEZ. Elle tutulan liste her
# partide bayatlar. Bu yuzden kural ASIMETRIKTIR:
#   * kutukte OLMAYAN yeni bir kayit  -> KIRMIZI (yeni veri kusuru sessizce giremez)
#   * kutukteki kayit TEMIZLENMISSE   -> yalnizca BILGI (yayin durmaz; bayatlama kendini
#                                        bir sonraki kosumda gosterir ama kimseyi bloklamaz)
# Kayitlar id + O GUN olculen alan degeriyle yazilir: alan degisirse satir bilgi olarak
# "artik farkli" der, iddiaya karismaz.
TANINMAYAN_KUTUGU = {
    "fiat-ducato-230-cam-suyu-deposu-kapagi": ["TPU (esnek)"],
    "subaru-forester-debriyaj-pedal-lastigi": ["TPU (esnek filament) önerilir"],
    "bmw-k1200s-uyumlu-abs-vidasi": ["ABS"],
}

HATALAR = []
OLCULEMEDI = []


def sifirla():
    del HATALAR[:]
    del OLCULEMEDI[:]


def kontrol(kosul, mesaj):
    print(("  ✅ " if kosul else "  ❌ ") + mesaj)
    if not kosul:
        HATALAR.append(mesaj)
    return bool(kosul)


def olculemedi(mesaj):
    print("  ⚠️  OLCULEMEDI: " + mesaj)
    OLCULEMEDI.append(mesaj)


# ═══════════════════════════════════════════════════ E1 — kenar senkronu capasi
def kenar_kolon_capasi(d1sync_src):
    """Kenar senkronu `fiyat` kolonuna NE yaziyor? (jeton, ayrinti)

    HAM alan -> kiyas tabani gecerli. Turetilmis bir ifade -> kiyas tabani DEGISMIS,
    bu kapinin E3 ekseni ARTIK OLCMUYOR demektir; sessizce yesil yanmak yerine
    OLCULEMEDI der. Cozulemeyen bicim de OLCULEMEDI'dir (fail-closed).
    """
    if "KOLONLAR" not in d1sync_src:
        return (JETON_OLCULEMEDI, "KOLONLAR sabiti bulunamadi")
    # `fiyat` ICERIK upsert'inde mi? (KOLONLAR listesinde ADI GECMELI)
    m_kol = re.search(r"KOLONLAR\s*=\s*\[(.*?)\]", d1sync_src, re.S)
    if not m_kol:
        return (JETON_OLCULEMEDI, "KOLONLAR listesi ayristirilamadi")
    if '"fiyat"' not in m_kol.group(1) and "'fiyat'" not in m_kol.group(1):
        return (JETON_OLCULEMEDI, "`fiyat` KOLONLAR listesinde YOK — icerik upsert'i "
                                  "kolonu yazmiyor olabilir")
    # INSERT deger listesinde `fiyat`in KARSILIGI ne? Ham alan okumasi araniyor.
    m_ham = re.search(r'q\(\s*u\.get\(\s*["\']fiyat["\']\s*\)\s*or\s*["\']["\']\s*\)',
                      d1sync_src)
    if m_ham:
        return (JETON_D1_HAM, m_ham.group(0))
    # Ham okuma YOK: kolon ya turetiliyor ya bicimi degismis. IKISI DE kiyas tabanini
    # bozar; ayri jeton verilir ki "yeni bir sey oluyor" gorunsun.
    if re.search(r'["\']fiyat["\']', d1sync_src):
        return (JETON_D1_TURETILMIS, "`fiyat` yaziliyor ama HAM alan okumasi bulunamadi")
    return (JETON_OLCULEMEDI, "`fiyat` kolonunun yazildigi yer bulunamadi")


# ═══════════════════════════════════════════════════ E2 — kart yuzeyi capasi
def kart_yuzey_capasi(index_src):
    """Kart yuzeyi KENDI turetmesini mi cagiriyor? (jeton, ayrinti)

    SIZMA TANIMI: urun sayfasi turetmesinin ADI (ilanBirimKurus) ya da urun sayfasi
    anahtarinin ADI (ONERI_ONSECIM_ACIK) kart yuzeyi dosyasinda GECIYORSA, kart kolu
    urun sayfasi koluyla birlikte kayar. Kart yuzeyi bu iki adi HIC gormemelidir.
    """
    urun_yolu = re.findall(r"\bilanBirimKurus\b", index_src)
    urun_anahtar = re.findall(r"\bONERI_ONSECIM_ACIK\b", index_src)
    kart_yolu = re.findall(r"\bvitrinBirimKurus\b", index_src)
    kart_anahtar = re.findall(r"\bONERI_VITRIN_ACIK\b", index_src)
    if urun_yolu or urun_anahtar:
        return (JETON_YUZEY_SIZDI,
                "urun sayfasi turetmesi kart yuzeyinde: ilanBirimKurus=%d "
                "ONERI_ONSECIM_ACIK=%d" % (len(urun_yolu), len(urun_anahtar)))
    if not kart_yolu or not kart_anahtar:
        return (JETON_OLCULEMEDI,
                "kart yuzeyi kendi turetmesini/anahtarini HIC cagirmiyor "
                "(vitrinBirimKurus=%d ONERI_VITRIN_ACIK=%d) — yuzey tanimlanamadi"
                % (len(kart_yolu), len(kart_anahtar)))
    return (JETON_YUZEY_AYRI,
            "vitrinBirimKurus=%d · ONERI_VITRIN_ACIK=%d · urun kolu sizintisi YOK"
            % (len(kart_yolu), len(kart_anahtar)))


# 🔴 DIS YUZEYLER (yapilandirilmis veri + urun beslemesi) de BASLANGIC tabanindadir
# (isletme karari, 11 Agu). Ureteç tarafinda o iki dal KART anahtarina bagli olmali;
# urun sayfasi anahtarina baglanirlarsa dis listeleme sessizce zamlanir.
_DIS_YUZEY_DALLARI = (
    ("yapilandirilmis veri",
     "if ONERI_VITRIN_ACIK and pnum:",
     "ld_fiyat = ilan_tl_metni(vitrin_kurus(p)) or pnum"),
    ("urun beslemesi",
     "if ONERI_VITRIN_ACIK:",
     "price = ilan_tl_metni(vitrin_kurus(p)) or price"),
)


def dis_yuzey_capasi(build_src):
    """Markup ve besleme dallari KART anahtarina mi bagli? (jeton, ayrinti)"""
    sizan = []
    for ad, kosul, govde in _DIS_YUZEY_DALLARI:
        if kosul not in build_src or govde not in build_src:
            sizan.append(ad)
    if sizan:
        return (JETON_YUZEY_SIZDI,
                "baslangic tabanina bagli OLMAYAN dis yuzey(ler): %s" % ", ".join(sizan))
    return (JETON_YUZEY_AYRI,
            "markup + besleme baslangic tabanina bagli (%d dal)" % len(_DIS_YUZEY_DALLARI))


# ═══════════════════════════════════════════════════ node kosucusu (kaynak STDIN'den)
# 🔴 KAYNAK DISKE YAZILMAZ: mutasyon bataryasi ayni fonksiyonu DEGISTIRILMIS kaynak
# METNIYLE cagirir; metin stdin'den gecer, gecici .js dosyasi olusmaz.
JS_KOSUCU = r"""
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const src = fs.readFileSync(0, "utf8");
const urunler = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const ref = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const ctx = { console: { log() {} }, Math, JSON, Date };
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(src, ctx, { filename: "secenekler.js" });
const S = ctx.PRUVO_SECENEK;
const out = {};
for (const p of urunler) { out[p.id] = [S.vitrinBirimKurus(p, ref), S.ilanBirimKurus(p, ref)]; }
process.stdout.write(JSON.stringify({
  acikUrun: S.ONERI_ONSECIM_ACIK, acikVitrin: S.ONERI_VITRIN_ACIK, sonuc: out }));
"""


def kuruslar_js(secenekler_src, urun_yolu, ref_yolu, kosucu_yolu):
    """(veri, hata) — kart ve urun sayfasi tutarlari, GERCEK istemci kuralindan."""
    node = shutil.which("node")
    if not node:
        return (None, "node yok")
    r = subprocess.run([node, kosucu_yolu, urun_yolu, ref_yolu],
                       input=secenekler_src, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return (None, (r.stderr or "")[-500:])
    try:
        return (json.loads(r.stdout), None)
    except ValueError as e:
        return (None, "cikti ayristirilamadi: %s" % e)


# ═══════════════════════════════════════════════════ ana olcum
def olc(secenekler_src, index_src, d1sync_src, build_src, urunler, ref_yolu, urun_yolu,
        kosucu_yolu, build_mod):
    """Alti ekseni koşar; (rc, ozet) döner. TUM girdiler METIN/nesne -> mutasyon
    bataryasi bu fonksiyonu BELLEKTE degistirilmis kaynaklarla cagirabilir."""
    sifirla()
    ozet = {}

    # ---------------------------------------------------------------- E1
    print("\n(E1) KENAR CAPASI — senkron `fiyat` kolonuna ham alani mi yaziyor")
    jeton, ayrinti = kenar_kolon_capasi(d1sync_src)
    ozet["e1"] = jeton
    if jeton == JETON_D1_HAM:
        kontrol(True, "%s — kiyas tabani GECERLI (%s)" % (jeton, ayrinti))
    elif jeton == JETON_D1_TURETILMIS:
        kontrol(False, "%s — kolon artik ham alani tasimiyor, bu kapinin kiyas "
                       "tabani DEGISTI (%s)" % (jeton, ayrinti))
    else:
        olculemedi("%s — %s" % (jeton, ayrinti))

    # ---------------------------------------------------------------- E2
    print("\n(E2) YUZEY CAPASI — kart kolu urun sayfasi kolundan AYRI mi")
    jeton2, ayrinti2 = kart_yuzey_capasi(index_src)
    ozet["e2"] = jeton2
    if jeton2 == JETON_YUZEY_AYRI:
        kontrol(True, "%s — %s" % (jeton2, ayrinti2))
    elif jeton2 == JETON_YUZEY_SIZDI:
        kontrol(False, "%s — KAPSAM SIZINTISI: %s" % (jeton2, ayrinti2))
    else:
        olculemedi("%s — %s" % (jeton2, ayrinti2))
    jeton2b, ayrinti2b = dis_yuzey_capasi(build_src)
    ozet["e2b"] = jeton2b
    if jeton2b == JETON_YUZEY_AYRI:
        kontrol(True, "%s (dis yuzey) — %s" % (jeton2b, ayrinti2b))
    else:
        kontrol(False, "%s (dis yuzey) — KAPSAM SIZINTISI: %s" % (jeton2b, ayrinti2b))

    # ---------------------------------------------------------------- E3/E5
    print("\n(E3) PARITE — TUM KATALOGDA kart tutari == ham liste tutari")
    veri, hata = kuruslar_js(secenekler_src, urun_yolu, ref_yolu, kosucu_yolu)
    if veri is None:
        olculemedi("istemci kurali kosturulamadi: %s" % hata)
        ozet["sapan"] = None
        ozet["ayrisan"] = None
    else:
        sapan, ayrisan, olculen, ornek = 0, 0, 0, []
        yuzdeler = []
        en_buyuk = (0.0, None, 0, 0)
        for p in urunler:
            pid = p["id"]
            if pid not in veri["sonuc"]:
                continue
            temel = build_mod.feed_price((p.get("fiyat") or "").strip())
            if not temel:
                continue          # sayisal fiyati yok -> kenar kolonu da tutar tasimaz
            liste = int(temel) * 100
            kart, urun_sayfasi = veri["sonuc"][pid]
            olculen += 1
            if kart != liste:
                sapan += 1
                if len(ornek) < 5:
                    ornek.append("%s: kart=%s kenar=%s" % (pid, kart, liste))
            if urun_sayfasi != kart:
                ayrisan += 1
                if kart:
                    y = 100.0 * (urun_sayfasi - kart) / kart
                    yuzdeler.append(y)
                    if y > en_buyuk[0]:
                        en_buyuk = (y, pid, kart, urun_sayfasi)
        ozet["sapan"] = sapan
        ozet["ayrisan"] = ayrisan
        print("     olculen urun: %d · kart!=kenar sapan: %d · urun sayfasi!=kart: %d"
              % (olculen, sapan, ayrisan))
        kontrol(olculen > 0, "kiyas EVRENI bos degil (%d urun)" % olculen)
        kontrol(sapan == 0,
                "SAPAN URUN = %d (ornek: %s)" % (sapan, ornek or "-"))

        print("\n(E5) IKI YUZEY AYRI — urun sayfasi tutari karttan gercekten farkli mi")
        kontrol(bool(veri["acikUrun"]),
                "urun sayfasi kolu ACIK (kapali olsaydi E5 hicbir sey olcmezdi)")
        kontrol(not veri["acikVitrin"],
                "kart kolu KAPALI — kart baslangic tabaninda")
        kontrol(ayrisan > 0,
                "iki yuzey %d uründe FARKLI tutar veriyor — ayrim GERCEKTEN uygulaniyor "
                "(0 olsaydi ya urun kolu olmus ya kural hic islemiyor demekti)" % ayrisan)

        # ── VITRIN FARKI (SADECE OLCUM — kirmizi YAKMAZ) ───────────────────────────
        # 🔴 Bu sayi bir ARIZA degil, KASITLI bir isletme durumudur (Okan karari). Ama
        # dis listeleme reddi geldiginde ilk bakilacak sayi budur; o yuzden hukum degil
        # OLCUM olarak basilir. Kapiyi kirmizi yaktirmak, kararin kendisini "hata" ilan
        # etmek olurdu ([[hukum-yanlis-birimde]]: yanlis birimde hukum).
        if yuzdeler:
            sirali = sorted(yuzdeler)
            ort = sum(sirali) / len(sirali)
            orta = (sirali[len(sirali) // 2] if len(sirali) % 2
                    else (sirali[len(sirali) // 2 - 1] + sirali[len(sirali) // 2]) / 2.0)
            ozet["vitrin_farki"] = (ayrisan, ort, orta, en_buyuk)
            print("     ── VITRIN FARKI (olcum, hukum DEGIL) ──")
            print("        fark tasiyan urun : %d / %d (%%%.1f)"
                  % (ayrisan, olculen, 100.0 * ayrisan / max(1, olculen)))
            print("        ortalama fark     : +%%%.2f" % ort)
            print("        medyan fark       : +%%%.2f" % orta)
            print("        en buyuk fark     : +%%%.2f  (%s · kart %d kr -> sayfa %d kr)"
                  % (en_buyuk[0], en_buyuk[1], en_buyuk[2], en_buyuk[3]))
        else:
            ozet["vitrin_farki"] = None
            print("     ── VITRIN FARKI: fark tasiyan urun YOK")

    # ---------------------------------------------------------------- E4
    print("\n(E4) POZITIF TANIYICI — kart anahtari ACIK kopyada sapma GORULUYOR mu")
    m = re.search(r"var\s+ONERI_VITRIN_ACIK\s*=\s*(true|false);", secenekler_src)
    if not m:
        olculemedi("kart anahtari kaynakta bulunamadi — tanıyıcı kurulamadi")
        ozet["taniyici"] = None
    else:
        acik_src = (secenekler_src[:m.start()] + "var ONERI_VITRIN_ACIK = true;"
                    + secenekler_src[m.end():])
        veri2, hata2 = kuruslar_js(acik_src, urun_yolu, ref_yolu, kosucu_yolu)
        if veri2 is None:
            olculemedi("tanıyıcı kosumu dustu: %s" % hata2)
            ozet["taniyici"] = None
        else:
            sapan2 = 0
            for p in urunler:
                pid = p["id"]
                if pid not in veri2["sonuc"]:
                    continue
                temel = build_mod.feed_price((p.get("fiyat") or "").strip())
                if not temel:
                    continue
                if veri2["sonuc"][pid][0] != int(temel) * 100:
                    sapan2 += 1
            ozet["taniyici"] = sapan2
            kontrol(sapan2 > 0,
                    "kart anahtari ACILINCA %d urunde sapma DOGUYOR — E3 ekseni CANLI "
                    "(0 olsaydi E3 hicbir seyi olcmuyor demekti)" % sapan2)

    # ---------------------------------------------------------------- E6
    print("\n(E6) TANINMAYAN MALZEME — sessizce tabana dusen VERI KUSURU sayilir")
    taninmayan = {}
    for p in urunler:
        tani, _m = build_mod.on_secim_tani(p, acik=True)
        if tani == "taninmayan":
            taninmayan[p["id"]] = p.get("tavsiyeFilament")
    ozet["taninmayan"] = len(taninmayan)
    print("     TANINMAYAN urun sayisi: %d" % len(taninmayan))
    for pid in sorted(taninmayan):
        durum = "KUTUKTE" if pid in TANINMAYAN_KUTUGU else "🔴 YENI"
        print("       %-9s %-46s %s"
              % (durum, pid[:46], json.dumps(taninmayan[pid], ensure_ascii=False)))
    yeni = sorted(set(taninmayan) - set(TANINMAYAN_KUTUGU))
    temizlenen = sorted(set(TANINMAYAN_KUTUGU) - set(taninmayan))
    if temizlenen:
        print("     BILGI — kutukteki %d kayit artik temiz (yayini DURDURMAZ): %s"
              % (len(temizlenen), ", ".join(temizlenen)))
    kontrol(not yeni,
            "kutukte OLMAYAN yeni taninmayan-malzeme kaydi YOK (%s)" % (yeni or "-"))
    # Kolun KENDISI canli mi? Sentetik girdiyle olculur: gercek katalog temizlense bile
    # eksen ATLANMAZ (sessiz yesil yasak).
    sentetik = {"id": "_sentetik_", "kategori": "Otomobil", "fiyat": "100 TL",
                "tavsiyeFilament": ["ABS"]}
    s_tani, s_malzeme = build_mod.on_secim_tani(sentetik, acik=True)
    kontrol(s_tani == "taninmayan" and s_malzeme == build_mod.VARSAYILAN_MALZEME,
            "taninmayan KOLU canli — satilmayan ad tasiyan urun 'varsayilan' ile "
            "AYNI jetona cokmuyor (olculen: %s/%s)" % (s_tani, s_malzeme))
    bos = {"id": "_sentetik2_", "kategori": "Otomobil", "fiyat": "100 TL"}
    b_tani, _ = build_mod.on_secim_tani(bos, acik=True)
    kontrol(b_tani != "taninmayan",
            "YANLIS-POZITIF YOK — onerisi olmayan urun 'taninmayan' sayilmiyor "
            "(olculen: %s)" % b_tani)

    # ---------------------------------------------------------------- E7
    print("\n(E7) URUN SAYFASI KOLU — onden secili cip TABAN DISI ve tutar ONDAN turuyor")
    # Denek ID'ye CIVILENMEZ ([[envanter-drift-parti-basina]]): her kosumda VERIDEN
    # turetilir. Denek bulunamamasi ATLAMA DEGIL, KIRMIZIDIR — pozitif kolu olduren bir
    # mutasyon tam olarak "artik boyle urun yok" seklinde gorunur.
    denek = None
    for p in urunler:
        if p.get("parametrik") or p.get("konfigur") or build_mod.fiziksel_mi(p):
            continue
        if not build_mod.feed_price((p.get("fiyat") or "").strip()):
            continue
        tani, malzeme = build_mod.on_secim_tani(p, acik=True)
        if tani == "oneri" and build_mod.FILAMENT_FARK.get(malzeme, 0):
            denek = (p, malzeme)
            break
    ozet["e7_denek"] = denek[0]["id"] if denek else None
    if not kontrol(denek is not None,
                   "POZITIF KOL CANLI — katalogda on-secimi TABAN DISI bir urun bulundu "
                   "(%s)" % (denek[0]["id"] if denek else "YOK")):
        pass
    else:
        p, malzeme = denek
        liste = int(build_mod.feed_price((p.get("fiyat") or "").strip())) * 100
        ilan = build_mod.ilan_kurus(p)
        taban_cip = build_mod.cip_kurus(p, build_mod.VARSAYILAN_MALZEME)
        print("     denek: %s · on-secim=%s · liste=%d kr · ilan=%s kr"
              % (p["id"], malzeme, liste, ilan))
        kontrol(ilan == build_mod.cip_kurus(p, malzeme),
                "ilan tutari = ONDEN SECILI CIPIN KENDI tutari (%s vs %s)"
                % (ilan, build_mod.cip_kurus(p, malzeme)))
        kontrol(ilan != liste,
                "ilan tutari taban tutardan FARKLI (%s vs %s) — kural gercekten isliyor"
                % (ilan, liste))
        # AZALTICI (Okan karari): taban secenegin tutari SAYFADA okunabilir kalmali.
        kontrol(taban_cip == liste,
                "TABAN SECENEK tutari = besleme/markup tutari (%s vs %s)"
                % (taban_cip, liste))
        cip_html = "".join(build_mod._fil_cipleri(p, malzeme))
        m_sec = re.search(r'class="[^"]*\bfil-cip\b[^"]*\bsecili\b[^"]*"\s+'
                          r'data-malzeme="([^"]+)"\s+data-kurus="(\d+)"', cip_html)
        kontrol(bool(m_sec) and m_sec.group(1) == malzeme
                and int(m_sec.group(2)) == ilan,
                "BASILAN cip: secili=%s tutar=%s (beklenen %s/%s)"
                % (m_sec.group(1) if m_sec else "-", m_sec.group(2) if m_sec else "-",
                   malzeme, ilan))
        m_taban = re.search(r'data-malzeme="%s"\s+data-kurus="(\d+)"'
                            % re.escape(build_mod.VARSAYILAN_MALZEME), cip_html)
        kontrol(bool(m_taban) and int(m_taban.group(1)) == liste,
                "TABAN cip sayfada GORUNUR ve kendi tutarini tasiyor (%s)"
                % (m_taban.group(1) if m_taban else "YOK"))

    print("\n(E8) TEK TURETME — ilan tutari ile onden secili cipin tutari TUM KATALOGDA esit")
    ayri, bakilan = [], 0
    for p in urunler:
        if p.get("parametrik") or p.get("konfigur"):
            continue
        if not build_mod.feed_price((p.get("fiyat") or "").strip()):
            continue
        bakilan += 1
        a = build_mod.ilan_kurus(p)
        b = build_mod.cip_kurus(p, build_mod.on_secim_malzeme(p))
        if a != b and len(ayri) < 5:
            ayri.append("%s: ilan=%s cip=%s" % (p["id"], a, b))
    kontrol(bakilan > 0, "tek-turetme evreni bos degil (%d urun)" % bakilan)
    kontrol(not ayri, "ilan tutari ile cip tutari AYRISMIYOR (%s)" % (ayri or "-"))

    # ---------------------------------------------------------------- E9
    print("\n(E9) BILINCLI SECIM NOTU — onerilenden sapinca GORUNUR, onerilende GORUNMEZ")
    if denek:
        p, malzeme = denek
        panel = build_mod.panel_malzeme_html(p)
        var_ = re.search(r'<div class="oneri-not" id="oneriNot"([^>]*)>', panel)
        kontrol(bool(var_) and ('data-oneri="%s"' % malzeme) in var_.group(1),
                "onerili uründe not kutusu BASILIYOR ve onerilen malzemeyi tasiyor")
        kontrol(bool(var_) and "hidden" in var_.group(1),
                "acilista GIZLI — onerilen zaten seciliyken not GURULTU YAPMIYOR "
                "(yanlis-pozitif yok)")
        # Toggle KOSULU: "secim var VE onerilenden FARKLI" -> gorunur. Kosulu kaldiran ya da
        # sabitleyen mutasyon burada yakalanir (notu sokmek de, HER secimde gostermek de).
        js = build_mod.PRODUCT_JS if hasattr(build_mod, "PRODUCT_JS") else ""
        kaynak_js = js or build_src
        kontrol('oneriNot.hidden = !(_o && seciliMalzeme && seciliMalzeme !== _o);'
                in kaynak_js,
                "gorunurluk KOSULA bagli (secim onerilenden FARKLI ise) — sabitlenmemis")
        # Onerisi TURETILEMEYEN uründe kutu HIC basilmamali (yalan beyan olurdu).
        onerisiz = None
        for q_ in urunler:
            if q_.get("parametrik") or q_.get("konfigur") or build_mod.fiziksel_mi(q_):
                continue
            if not build_mod.feed_price((q_.get("fiyat") or "").strip()):
                continue
            if build_mod.on_secim_tani(q_, acik=True)[0] in ("taninmayan", "varsayilan"):
                onerisiz = q_
                break
        if onerisiz is None:
            olculemedi("onerisi turetilemeyen denek bulunamadi — E9 negatif kolu olculmedi")
        else:
            kontrol('id="oneriNot"' not in build_mod.panel_malzeme_html(onerisiz),
                    "onerisi TURETILEMEYEN uründe (%s) not kutusu BASILMIYOR"
                    % onerisiz["id"])

    # ---------------------------------------------------------------- E10
    print("\n(E10) MESAJ KANALI AYRISMASI — kenar karti `tavsiyeFilament` tasimiyor")
    # 🔴 NEDEN AYRI EKSEN: kart yuzeyinin IKI ureticisi var — site (istemci) ve kenar
    # Worker'i (kardes depo). Kenar karti onerilen malzeme alanini TASIMIYOR. Bugun bu
    # ZARARSIZDIR cunku kart kolu KAPALI: kural anahtari kapaliyken daha ILK satirda
    # guvenli varsayilana doner ve alani HIC okumaz. Kart kolu ACILIRSA ayni yuzeyin iki
    # ureticisi AYNI urun icin FARKLI tutar yazar ve hicbir sey alarm calmaz.
    # KURAL: alan YOKken kart kolu ACIKSA -> KIRMIZI.
    #
    # 🔴 11 AGU 2026 — KARDES AGAC YOKKEN "OLCULEMEDI" YAPISAL BIR KIRMIZIYDI (onarildi).
    #   Eski kol kardes depo diskte yoksa OLCULEMEDI basiyordu ve kapi rc=2 donuyordu.
    #   Kardes depo (edge Worker, ~/dev/pruvo-bot) BASKA BIR MIMARIN EVIDIR ve CI fresh
    #   checkout'unda HICBIR ZAMAN bulunmaz: `~` orada /home/runner'dir, o agac hic
    #   klonlanmaz. Yani eksen CI'da HER KOSUMDA rc=2 veriyordu -> `serit-a3` failure ->
    #   `deploy` + `yayin` skipped. Olculdu (kosum 31511073366, headSha 35de6880 ve
    #   31513339498/5bd2fb1d): tum ekibin yayini bu tek satirdan duruyordu.
    #
    #   ONARIM GEVSETME DEGIL, KAPSAMIN DOGRU TANIMIDIR. Kardes agacin YOKLUGU bir
    #   OLCUM BOSLUGU degil KAPSAM DISILIKTIR: bu kapinin duzleminde o dosya hic yoktur,
    #   dolayisiyla hakkinda verilecek bir hukum de yoktur. Kardes kapi
    #   (tools/edge-kart-kapisi.py) ayni doktrini zaten uygular — alani OLCER, ASLA
    #   kirmizi yakmaz. Ayrim keskin tutulur:
    #     * kardes agac VARSA  -> bugunku fail-closed hukum AYNEN gecerli (kart kolu ACIK
    #                             + alan eksik => KIRMIZI). M3 bunu kanitlar (kardes agaci
    #                             SENTETIK fikstur ile GORUNUR kilar; makinenin HOME'una
    #                             BAGLI DEGILDIR) ve izini JETON_KARDES_HUKUM ile arar.
    #     * kardes agac YOKSA  -> KAPSAM DISI satiri BASILIR, hukum VERILMEZ, cikis kodu
    #                             ETKILENMEZ. M13 bunu kanitlar; M14 o kolun GERCEK bir
    #                             kapsam sizintisini YUTMADIGINI kanitlar.
    #   "Cozemedim = alan yok" sessiz gecisi HALA YASAK: kardes agac VARDIR ama sabiti
    #   ayristirilamiyorsa eksen yine OLCULEMEDI'dir (asagida).
    #   🔴 KAPSAM DISILIK YALNIZ BU HUKMU KAPSAR: alan notrlugu kaniti (E10b) kardes
    #   agactan BAGIMSIZDIR ve asagida HER KOSUMDA verilir — 12 Agu fail-open onarimi.
    try:
        import importlib.util as _iu
        _s = _iu.spec_from_file_location("_edge_kapi",
                                         os.path.join(TOOLS, "edge-kart-kapisi.py"))
        _edge = _iu.module_from_spec(_s)
        _s.loader.exec_module(_edge)
    except Exception as e:                                   # noqa: BLE001
        _edge = None
        olculemedi("kenar kart cozucusu yuklenemedi: %s" % e)
    tasiyor = None
    if _edge is not None:
        if not os.path.exists(_edge.KARDES_WORKER):
            print("     kenar Worker kaynagi diskte YOK (%s) -> %s: baska bir mimarin "
                  "evi, bu kapinin duzlemi DEGIL — hukum VERILMEZ, cikis kodu "
                  "ETKILENMEZ (CI fresh checkout'unda normal hal)"
                  % (_edge.KARDES_WORKER, JETON_KARDES_KAPSAM_DISI))
        else:
            with open(_edge.KARDES_WORKER, encoding="utf-8") as f:
                _w = f.read()
            satir, eksikler = _edge.worker_kapsam_satiri(_w, ["tavsiyeFilament"])
            print("     " + satir)
            if eksikler is None:
                olculemedi("kenar kart alan listesi COZULEMEDI — hukum verilmedi")
            else:
                tasiyor = not eksikler
    ozet["edge_tasiyor"] = tasiyor
    if tasiyor is not None:
        kontrol(tasiyor or not veri or not veri.get("acikVitrin"),
                "%s kenar karti oneri alanini %s; kart kolu %s -> ayni yuzeyin iki "
                "ureticisi AYRISAMAZ"
                % (JETON_KARDES_HUKUM, "TASIYOR" if tasiyor else "TASIMIYOR",
                   "ACIK" if (veri and veri.get("acikVitrin")) else "KAPALI"))

    # ── E10b ALAN NOTRLUGU — KARDES AGACTAN BAGIMSIZ, HER KOSUMDA VERILIR ─────────
    # 🔴 12 AGU 2026 FAIL-OPEN ONARIMI ([[kapi-kapsam-genisletme-tuzagi]]). Bu blok
    #   11 Agu'da `if tasiyor is not None:` govdesinin ICINDEYDI. Kardes agac (baska
    #   mimarin evi) CI fresh checkout'unda HICBIR ZAMAN bulunmaz -> `tasiyor is None`
    #   -> blok HIC KOSMUYORDU. Yani "kapsam disi" onarimi, kardes depoyla ILGISI
    #   OLMAYAN bir hukmu de beraberinde susturmustu.
    #   OLCULDU: kart kolunun iki katmanli kisa-devresini kaldiran mutant (batarya M12)
    #   kardes agac YOKKEN kapiyi YESIL birakiyordu (rc=0), VARKEN kirmizi yakiyordu.
    #   Ayni kaynak, ayni kusur, iki farkli renk -> hukum makinenin HOME'una bagliydi.
    # NE OLCER: kural anahtari kapaliyken alani TASIMAYAN kart ile TASIYAN kart AYNI
    #   tutari vermeli — yoksa "kapali oldugu icin zararsiz" iddiasi beyandan ibaret
    #   kalirdi ([[beyan-edilmis-survivor]]). Girdisi YALNIZ build.py + urunler.json'dur.
    # 🔴 DENEK AYIRT EDICI SECILIR: alani KALDIRINCA kural BASKA bir malzeme secen bir
    #   kayit gerekir. Aksi halde iddia TAUTOLOJI olurdu (alan zaten kategori haritasiyla
    #   ayni sonucu veriyorsa, silmek hicbir sey degistirmez ve kanit hicbir sey kanitlamaz).
    ayirt = None
    for q_ in urunler:
        if not q_.get("tavsiyeFilament") or q_.get("parametrik") or q_.get("konfigur"):
            continue
        if not build_mod.feed_price((q_.get("fiyat") or "").strip()):
            continue
        q_yok = dict(q_)
        q_yok.pop("tavsiyeFilament", None)
        if (build_mod.on_secim_tani(q_, acik=True)[1]
                != build_mod.on_secim_tani(q_yok, acik=True)[1]):
            ayirt = (q_, q_yok)
            break
    if ayirt is None:
        olculemedi("alani silince BASKA malzeme secen kayit bulunamadi — E10b kaniti "
                   "AYIRT EDICI kurulamadi")
    else:
        q_, q_yok = ayirt
        a_var, a_yok = build_mod.vitrin_kurus(q_), build_mod.vitrin_kurus(q_yok)
        print("     ayirt edici denek: %s (alan VAR -> %s · alan YOK -> %s, kural ACIK)"
              % (q_["id"], build_mod.on_secim_tani(q_, acik=True)[1],
                 build_mod.on_secim_tani(q_yok, acik=True)[1]))
        kontrol(a_var == a_yok,
                "%s KANIT: alani TASIMAYAN kart ile TASIYAN kart AYNI kart tutarini "
                "veriyor (%s = %s) -> kart kolu kapaliyken eksik alan tutari "
                "KAYDIRMIYOR" % (JETON_KART_ALAN_NOTR, a_yok, a_var))
    # MARUZIYET (olcum, hukum DEGIL): mesaj kanali kenar kolonunu okur, urun sayfasi
    # onerilen malzemenin tutarini vurgular. Ayrisan urun sayisi ve ortalama fark.
    if ozet.get("vitrin_farki"):
        _ad, _ort, _orta, _enb = ozet["vitrin_farki"]
        print("     ── MESAJ KANALI MARUZIYETI (olcum) ──")
        print("        mesaj kanali != urun sayfasi : %d urun · ortalama +%%%.2f"
              % (_ad, _ort))
        print("        (mesaj kanali kenar `fiyat` kolonunu okur = kart tutari = taban)")

    # ---------------------------------------------------------------- hukum
    print("\n" + "-" * 72)
    if OLCULEMEDI:
        print("OLCULEMEDI (%d):" % len(OLCULEMEDI))
        for x in OLCULEMEDI:
            print("  - " + x)
    if HATALAR:
        print("SONUC: KIRMIZI ❌ — %d iddia dustu" % len(HATALAR))
        for x in HATALAR:
            print("  - " + x)
        return (1, ozet)
    if OLCULEMEDI:
        print("SONUC: OLCULEMEDI ⚠️")
        return (2, ozet)
    print("SONUC: YESIL ✅ — kart tutari kenar kolonuyla AYRISMIYOR (sapan=%s), "
          "urun sayfasi kolu kartı KAYDIRMIYOR" % ozet.get("sapan"))
    return (0, ozet)


def kaynaklari_oku():
    def oku(*parca):
        with open(os.path.join(ROOT, *parca), encoding="utf-8") as f:
            return f.read()
    return (oku("secenekler.js"), oku("index.html"), oku("tools", "d1-sync.py"),
            oku("tools", "build.py"))


def main():
    import build  # noqa: E402  (kaynak okumasi ROOT'a bagli; import burada)
    print("VITRIN <-> D1 FIYAT PARITE KAPISI + KAPSAM SIZINTISI NOBETI")
    print("depo anahtarlari: urun sayfasi=%s · kart=%s"
          % (build.ONERI_ONSECIM_ACIK, build.ONERI_VITRIN_ACIK))
    sec, ix, d1s, bsrc = kaynaklari_oku()
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    import filament_ortak  # noqa: E402
    gecici = tempfile.mkdtemp(prefix="d1fiyat-")
    try:
        ry = os.path.join(gecici, "ref.json")
        with open(ry, "w", encoding="utf-8") as f:
            json.dump(filament_ortak.referans(), f, ensure_ascii=False)
        uy = os.path.join(gecici, "urunler.json")
        with open(uy, "w", encoding="utf-8") as f:
            json.dump(urunler, f, ensure_ascii=False)
        ky = os.path.join(gecici, "kosucu.js")
        with open(ky, "w", encoding="utf-8") as f:
            f.write(JS_KOSUCU)
        rc, _ozet = olc(sec, ix, d1s, bsrc, urunler, ry, uy, ky, build)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())

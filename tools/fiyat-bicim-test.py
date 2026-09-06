#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIYAT BICIM SOZLESMESI kabul testi (6 Eyl 2026, Okan emri) — offline, tek basina.

    python3 tools/fiyat-bicim-test.py                # kabul kosumu
    python3 tools/fiyat-bicim-test.py M1             # mutant kanitı (M1..M4 OLDURUCU)
    python3 tools/fiyat-bicim-test.py K1             # KONTROL mutanti (YESIL kalmali)
    python3 tools/fiyat-bicim-test.py --kendini-test # CI kolu: batarya + 10 mutant

NEDEN VAR — HATA SINIFI SESSIZ VE PARALI (canlida olculdu):
  Katalogda 616 kayit "250.0 TL" bicimindeydi. Noktayi TURKCE BINLIK AYRACI sanan UC
  AYRI okuyucu tutari ON KAT buyuttu — sepet/odeme yolu DAHIL:
      build.price_number  "250.0 TL" -> "2500"   (JSON-LD / markup lowPrice)
      build.feed_price    "250.0 TL" -> "2500"   (feed / urun sayfasi / D1)
      secenekler.js       "250.0 TL" -> 2500     (SEPET — tahsil edilen tutar)
  Tip sozlesmesi yalnizca JSON tipini (str) olctugu icin bozuk deger HIC yakalanmadi:
  "250.0 TL" bir str'dir. Okan canlida 200 TL'lik urunu "2.000,00 TL" gordu.

IDDIALAR (hepsi KOSULARAK olculur, "bakildi iyi gorunuyor" degil):
  (1) TEK KAYNAK   — price_number ve feed_price AYNI ayristirma noktasindan (
                     arama.fiyat_tam_tl) dogar; TUM katalog uzerinde birebir esit.
                     Ikinci ayristirma kurali tam olarak 12 Agu'daki markup<->kart
                     ayrisimini (300 TL <-> 30.030 TL) uretir.
  (2) FAIL-CLOSED  — ondalik hane tasiyan deger her okuyucuda None/null; sessiz bir
                     varsayilana DUSMEZ ve daha genis bir kabul sinifi ACMAZ.
  (3) IKIZ KURAL   — Python (arama) ile JS (secenekler.js fiyatSayisi, yonet.js
                     fiyatYukariYuvarla) AYNI vaka tablosunda birebir ayni cevabi verir.
  (4) ALT KUME     — panel uygulayicisinin (OTORITE) kalibi kanonik sozlesmeden DAHA
                     DARDIR: kanonigin reddettigi hicbir deger tabana yazilamaz.
  (5) TAM KAPSAM   — canli katalogun TAMAMI (ORNEKLEME YOK) sozlesmeyi gecer.
  (6) YUVARLAMA    — kurus YUKARI yuvarlanir (Okan: "200.1 -> 201"); yuvarlama YALNIZ
                     GIRIS kapisindadir, okuma yolu yuvarlamaz (yoksa bozuk deger
                     kayitta sessizce yasar ve ilan edilen tutar kayittan okunamaz).

NE IDDIA EDILMEZ: gorsel yerlesim/piksel · iyzico'ya giden tutarin ucu ucuna dogrulugu
(o d1-fiyat-parite-kapisi.py'nin ekseni) · parametrik/konfigur canli hesabi.

CIKIS: 0 yesil · 1 kirmizi · 2 OLCULEMEDI (node yok -> IKIZ KURAL kolu kosamaz).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import arama    # noqa: E402
import build    # noqa: E402

# Ortak VAKA TABLOSU — Python ve JS ikizleri BU tabloda kilitlenir.
#   (ham deger, beklenen kanonik TL ya da None)
VAKALAR = [
    ("250 TL", 250),
    ("1.250 TL", 1250),
    ("350 TL (12 cm)", 350),
    ("300 TL/adel", 300),
    ("999999 TL", 999999),
    # 🔴 PARA MALIYETLI SINIF — ondalik. Hepsi None olmak ZORUNDA.
    ("250.0 TL", None),
    ("200.0 TL", None),
    ("200.1 TL", None),
    ("250,50 TL", None),
    ("1.25 TL", None),
    # bicimsiz / anlamsiz
    ("", None),
    ("0 TL", None),
    ("abc TL", None),
    ("olcuye ozel", None),
]

# Yuvarlama vaka tablosu — GIRIS kapisi (panel). (ham, beklenen "N TL" ya da None)
YUVARLAMA = [
    ("200.1 TL", "201 TL"),      # Okan'in birebir ornegi
    ("250.0 TL", "250 TL"),      # kurus YOK -> deger DEGISMEZ
    ("200,01 TL", "201 TL"),     # 1 kurus bile YUKARI
    ("200,00 TL", "200 TL"),
    ("430 TL", "430 TL"),
    # 🔴 MENZIL: yuvarlayici YALNIZ kurus sinifini cozer, baska RED'i GEVSETMEZ.
    # Asagidakiler panelde 400 donmeye DEVAM etmeli (urunler-panel.mjs B4a/B4b/B4c).
    ("1.250 TL", None),          # binlik ayraci panel kalibinda ZATEN yok
    ("500", None),               # TL'siz  -> B4a
    ("500 tl", None),            # kucuk harf -> B4b
    ("abc", None),
    ("", None),
    ("0 TL", None),              # -> B4c
    # 🔴 SINIF KAPISI (Okan 6 Eyl: "dar hale geri cek, sonra it"). Asagidaki UC satir
    # girdi kalibinin KENDI sinir vakalaridir — tekil bir hata degil, MENZIL olculur.
    # Neden gerekli, OLCULEREK: bu satirlar eklenmeden once `[1-9]` -> `[0-9]` mutanti
    # (M7) bataryayi 12/12 YESIL birakip kaciyordu; sifir capasi sessizce dusuyordu.
    # Menzili koruyan kol: --kendini-test (M5/M6/M7 OLDURUCU, K3 KONTROL).
    ("500.123 TL", None),        # kurus hanesi 2'den FAZLA -> cozulemez (panel B4d2)
    ("0.5 TL", None),            # bas hane 0 YASAK; "0.5 TL" 1 TL'ye yuvarlanamaz
    ("0,5 TL", None),            # ayni sinir, virgullu ikizi
]


# --------------------------------------------------------------------- mutantlar
def mutant_uygula(ad):
    """Mutant DAIMA bu SURECTEKI nesneye uygulanir; kaynak dosyalara YAZILMAZ."""
    if ad == "M1":
        # 🔴 GERI DONUS: nokta yine TURKCE BINLIK AYRACI sanilir ("250.0" -> 2500).
        # Emrin oldurmesi gereken tam hal budur.
        def binlik_sanan(deger):
            if not isinstance(deger, str) or not deger.strip():
                return None
            m = re.search(r"(\d[\d.]*)", deger)
            if not m:
                return None
            ham = m.group(1).replace(".", "")
            return int(ham) if ham.isdigit() and int(ham) > 0 else None
        arama.fiyat_tam_tl = binlik_sanan
    elif ad == "M2":
        # Sozlesme her seyi kabul eder (tip kapisi korlesir).
        arama.fiyat_bicim_sebebi = lambda deger: None
    elif ad == "M3":
        # price_number IKINCI bir ayristirma kuralina doner (12 Agu ayrisimi).
        build.price_number = lambda f: (re.sub(r"[^0-9]", "", f) or None) if f else None
    elif ad == "M4":
        # Kurus ASAGI yuvarlanir (Okan emrinin tersi).
        def asagi(deger):
            if not isinstance(deger, str) or not deger.strip():
                return None
            m = re.match(r"^\s*(" + arama.FIYAT_SAYI_RE + r")(?:[.,](\d{1,2}))?\s*"
                         + arama.FIYAT_BIRIMI_RE + arama.FIYAT_EK_RE + r"\s*$",
                         deger.strip(), re.I)
            if not m:
                return None
            tam = int(m.group(1).replace(".", ""))
            return "%d TL" % tam if tam > 0 else None
        arama.fiyat_yukari_yuvarla = asagi
    elif ad == "K1":
        # KONTROL — red SEBEBININ metni degisir, HUKUM degismez. YESIL kalmali:
        # test sebep dizesine degil, red edilip edilmedigine bakmali.
        asil = arama.fiyat_bicim_sebebi
        arama.fiyat_bicim_sebebi = (
            lambda deger: None if asil(deger) is None else "fiyat bicimi gecersiz")
    elif ad == "K2":
        # KONTROL — katalogda HIC kullanilmayan bir bicim (bosluksuz "250TL") da
        # kabul edilir. Kanonik kumeye dokunmaz -> YESIL kalmali.
        asil = arama.fiyat_bicim_sebebi

        def gevsek(deger):
            if isinstance(deger, str) and re.match(r"^\d+TL$", deger.strip()):
                return None
            return asil(deger)
        arama.fiyat_bicim_sebebi = gevsek
    elif ad:
        raise ValueError("bilinmeyen mutant: %s" % ad)


# ------------------------------------------------------------------- JS ikizi
JS_KOSUM = r"""
import fs from "node:fs";
await import(process.argv[2] + "/secenekler.js");
const S = globalThis.PRUVO_SECENEK;
const src = fs.readFileSync(process.argv[2] + "/shop/src/yonet.js", "utf8");
// yonet.js bir Worker modulu (env bagimli import'lar) — yalniz normalize edici
// fonksiyonu ve kalibini KAYNAKTAN ayikla; modulun tamamini yuklemeye calisma.
const rx = src.match(/const FIYAT_GIRDI_RX = (\/.*\/[a-z]*);/);
const fn = src.match(/function fiyatYukariYuvarla\(ham\) \{[\s\S]*?\n\}/);
if (!rx || !fn) { console.log(JSON.stringify({hata: "yonet.js normalize edici bulunamadi"})); process.exit(0); }
// ESM'de eval yeni bagi modul kapsamina SIZDIRMAZ; fonksiyonu DEGER olarak al.
// Dogrudan (direct) eval oldugu icin govde asagidaki FIYAT_GIRDI_RX'i kapatir.
const FIYAT_GIRDI_RX = eval(rx[1]);
const fiyatYukariYuvarla = eval("(" + fn[0] + ")");
const vakalar = JSON.parse(process.argv[3]);
const yuv = JSON.parse(process.argv[4]);
console.log(JSON.stringify({
  fiyatSayisi: vakalar.map((v) => S.fiyatSayisi(v)),
  yuvarla: yuv.map((v) => fiyatYukariYuvarla(v)),
}));
"""


def js_ikizi():
    """(fiyatSayisi listesi, yuvarla listesi) ya da None (node yok / calismadi)."""
    try:
        with tempfile.TemporaryDirectory(prefix="fiyat-bicim-js-") as gecici:
            kosum = os.path.join(gecici, "kosum.mjs")
            with open(kosum, "w", encoding="utf-8") as f:
                f.write(JS_KOSUM)
            p = subprocess.run(
                ["node", kosum, KOK,
                 json.dumps([v for v, _ in VAKALAR]),
                 json.dumps([v for v, _ in YUVARLAMA])],
                capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    try:
        veri = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None
    if "hata" in veri:
        return None
    return veri["fiyatSayisi"], veri["yuvarla"]


# --------------------------------------------------------------------- kabul
# ------------------------------------------------------- MENZIL MUTANTLARI (sinif)
# M1..M4 ayristirma KURALINI mutasyona ugratir ama girdi kalibinin MENZILINI olcmez.
# 6 Eyl 2026'da bu kor nokta canlida ise yaradi: `ecc71b61` FIYAT_GIRDI_RX'i genis hale
# getirdi ("500.123 TL" kabule dondu) ve bu batarya 12/12 YESIL yandi. Menzil, kaynak
# dosyadaki KALIP DIZGESIDIR; onu olcmek icin mutant IKI IKIZE de (arama.py + yonet.js)
# ayni anda uygulanmali ve batarya BASTAN kosulmalidir.
#
# 🔴 Mutant DAIMA IZOLE bir kopyada kosar: gecici kok tempfile.mkdtemp ile acilir, ev
# agacindaki dosyalar SYMLINK'lenir, yalniz iki ikiz GERCEK dosya olarak yazilir.
# Ev yoluna hicbir sey yazilmaz ve hicbir sey silinmez (silinen daima mkdtemp koku).
DAR_JS = "const FIYAT_GIRDI_RX = /^([1-9][0-9]{0,5})(?:[.,]([0-9]{1,2}))? TL$/;"
DAR_PY = '    m = re.match(r"^([1-9]\\d{0,5})(?:[.,](\\d{1,2}))? TL$", ham)'

# (ad, js kalibi, py satiri, OLDURUCU mu, tek cumle gerekce)
MENZIL_MUTANTLARI = [
    ("M5 GENIS (ecc71b61'in birebir hali)",
     "const FIYAT_GIRDI_RX = /^\\s*((?:[0-9]{1,3}(?:\\.[0-9]{3})+|[0-9]+))"
     "(?:[.,]([0-9]{1,2}))?\\s*(?:TL|TRY|\u20ba)?(?:\\s*\\([^()]{1,40}\\)"
     "|\\/[^\\s\\/]{1,20})?\\s*$/i;",
     '    m = re.match(r"^(" + FIYAT_SAYI_RE + r")(?:[.,](\\d{1,2}))?\\s*(?:"'
     " + FIYAT_BIRIMI_RE\n                 + r\")?\" + FIYAT_EK_RE + r\"\\s*$\","
     " ham, re.I)",
     True, "binlik-nokta dali geri gelir: '500.123 TL' 500123 olarak KABUL edilir"),
    ("M6 KURUS3 (kurus hanesi 2 -> 3)",
     DAR_JS.replace("[0-9]{1,2}", "[0-9]{1,3}"),
     DAR_PY.replace("\\d{1,2}", "\\d{1,3}"),
     True, "'500.123 TL' cozulebilir sayilir; belirsiz noktalama kabule doner"),
    ("M7 SIFIR (bas hane [1-9] -> [0-9])",
     DAR_JS.replace("[1-9][0-9]{0,5}", "[0-9][0-9]{0,5}"),
     DAR_PY.replace("[1-9]\\d{0,5}", "[0-9]\\d{0,5}"),
     True, "sifir capasi duser: '0.5 TL' 1 TL'ye yuvarlanir"),
    ("K3 ESDEGER (dar halin ayni anlamli yeniden yazimi)",
     "const FIYAT_GIRDI_RX = /^([1-9][0-9]{0,5})(?:[.,]([0-9]{1,2}))?[ ]TL$/;",
     '    m = re.match(r"^([1-9][0-9]{0,5})(?:[.,]([0-9]{1,2}))? TL$", ham)',
     False, "KONTROL: menzil AYNI, yalniz yazim degisti -> YESIL kalmali"),
]


def _izole_kok(js_yeni, py_yeni):
    """Ev agacini symlink'leyen, iki ikizi MUTASYONLU yazan gecici kok dondurur."""
    kok = tempfile.mkdtemp(prefix="fiyat-bicim-menzil-mut-")
    for ad in os.listdir(KOK):
        if os.path.isfile(os.path.join(KOK, ad)):
            os.symlink(os.path.join(KOK, ad), os.path.join(kok, ad))
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(TOOLS):
        if ad != "arama.py":
            os.symlink(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    os.makedirs(os.path.join(kok, "shop", "src"))
    kaynak_shop = os.path.join(KOK, "shop", "src")
    for ad in os.listdir(kaynak_shop):
        if ad != "yonet.js":
            os.symlink(os.path.join(kaynak_shop, ad),
                       os.path.join(kok, "shop", "src", ad))

    def yaz(hedef, kaynak, eski, yeni):
        with open(kaynak, encoding="utf-8") as f:
            s = f.read()
        # 🔴 CAPA COKMESI SESSIZ GECMEZ: kalip bulunamazsa ya da mutant capayi hic
        # degistirmiyorsa mutant ULASMAMISTIR — bu bir OLCUM ARIZASIDIR, yesil degil.
        if eski not in s or eski == yeni:
            shutil.rmtree(kok)
            return None
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(s.replace(eski, yeni, 1))
        return hedef

    if yaz(os.path.join(kok, "tools", "arama.py"),
           os.path.join(TOOLS, "arama.py"), DAR_PY, py_yeni) is None:
        return None
    if yaz(os.path.join(kok, "shop", "src", "yonet.js"),
           os.path.join(KOK, "shop", "src", "yonet.js"), DAR_JS, js_yeni) is None:
        return None
    return kok


def _kosum(kok):
    """Bataryayi verilen kokte BASTAN kosar; (rc, kirmizi iddia adlari) dondurur."""
    p = subprocess.run([sys.executable, os.path.join(kok, "tools", "fiyat-bicim-test.py")],
                       capture_output=True, text=True, timeout=600)
    kirmizi = [s.split("  ", 1)[-1].strip()
               for s in p.stdout.splitlines() if s.startswith("KIRMIZI")]
    return p.returncode, kirmizi


def kendini_test():
    """Bataryanin KENDI kapsamini olcer: mutantlar gercekten oluyor mu?"""
    print("KENDINI-TEST — menzil + kural mutantlari (izole kopyada)")
    kayit = []

    rc, _ = _kosum(KOK)
    kayit.append(("TABAN (mutantsiz kosum)", rc == 0, "rc=%d" % rc, True))

    for ad in ["M1", "M2", "M3", "M4"]:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), ad],
                           capture_output=True, text=True, timeout=600)
        kayit.append((ad + " kural mutanti OLDURUCU", p.returncode != 0,
                      "rc=%d" % p.returncode, True))
    for ad in ["K1", "K2"]:
        p = subprocess.run([sys.executable, os.path.abspath(__file__), ad],
                           capture_output=True, text=True, timeout=600)
        kayit.append((ad + " KONTROL yesil kalmali", p.returncode == 0,
                      "rc=%d" % p.returncode, True))

    for ad, js_yeni, py_yeni, oldurucu, gerekce in MENZIL_MUTANTLARI:
        kok = _izole_kok(js_yeni, py_yeni)
        if kok is None:
            kayit.append((ad, False, "CAPA TUTMADI — mutant ULASMADI (olcum arizasi)",
                          True))
            continue
        try:
            rc, kirmizi = _kosum(kok)
        finally:
            # Silinen DAIMA mkdtemp koku; ev agacindaki dosyalar SYMLINK oldugu icin
            # yalniz baglar dusler, hedefler durur.
            assert kok.startswith(tempfile.gettempdir()), "izole olmayan kok: %s" % kok
            shutil.rmtree(kok)
        ok = (rc != 0) if oldurucu else (rc == 0)
        kayit.append((ad + (" OLDURUCU" if oldurucu else " KONTROL"), ok,
                      "rc=%d kirmizi=%s | %s" % (rc, kirmizi or "yok", gerekce), True))

    for ad, ok, ek, _ in kayit:
        print("%s %s  [%s]" % ("GECTI " if ok else "KIRMIZI", ad, ek))
    kalan = sum(1 for _, ok, _, _ in kayit if not ok)
    print("KENDINI-TEST SONUC: %d/%d iddia GECTI" % (len(kayit) - kalan, len(kayit)))
    return 1 if kalan else 0


def main():
    arg = sys.argv[1] if len(sys.argv) == 2 else ""
    if len(sys.argv) > 2:
        print("KULLANIM: fiyat-bicim-test.py [M1|M2|M3|M4|K1|K2|--kendini-test]")
        return 1
    if arg == "--kendini-test":
        return kendini_test()
    mutant_uygula(arg)
    sonuc = []

    def ol(ad, kosul, ek=""):
        sonuc.append((ad, bool(kosul), ek))

    # (1) TEK KAYNAK + (2) FAIL-CLOSED — vaka tablosu
    pn_ok = fp_ok = tip_ok = True
    for ham, beklenen in VAKALAR:
        b = None if beklenen is None else str(beklenen)
        if build.price_number(ham) != b:
            pn_ok = False
        if build.feed_price(ham) != b:
            fp_ok = False
        # Bos dize parametrik sozlesmesidir: bicim GECERLI ama tutar YOK.
        red_bekleniyor = beklenen is None and ham.strip() != ""
        if (arama.fiyat_bicim_sebebi(ham) is not None) != red_bekleniyor:
            tip_ok = False
    ol("A1 price_number vaka tablosu", pn_ok)
    ol("A2 feed_price vaka tablosu", fp_ok)
    ol("A3 bicim sozlesmesi ondaligi REDDEDIYOR", tip_ok)

    # 🔴 Emrin cekirdegi: canlida gorulen degerler.
    ol("A4 '250.0 TL' her Python okuyucusunda None",
       build.price_number("250.0 TL") is None and build.feed_price("250.0 TL") is None
       and arama.fiyat_tam_tl("250.0 TL") is None
       and arama.katalog_alan_tip_sebebi("fiyat", "250.0 TL") is not None)

    # (1) IKI OKUYUCU AYRISAMAZ — TUM katalog uzerinde (ORNEKLEME YOK)
    with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
        katalog = json.load(f)
    sapan = [u.get("id") for u in katalog
             if build.price_number(u.get("fiyat")) != build.feed_price(u.get("fiyat"))]
    ol("A5 price_number == feed_price (tum katalog)", not sapan,
       "sapan=%d" % len(sapan))

    # (5) TAM KAPSAM — canli katalogda ihlal YOK
    ihlal = [(u.get("id"), u.get("fiyat")) for u in katalog
             if arama.fiyat_bicim_sebebi(u.get("fiyat", "")) is not None]
    ol("A6 canli katalogda fiyat ihlali YOK", not ihlal,
       "ihlal=%d ornek=%s" % (len(ihlal), ihlal[:3]))
    ondalikli = [u.get("id") for u in katalog
                 if isinstance(u.get("fiyat"), str)
                 and re.match(r"^\s*\d+[.,]\d+\s*TL", u["fiyat"])]
    ol("A7 katalogda ondalikli kayit 0", not ondalikli, "ondalikli=%d" % len(ondalikli))

    # (6) YUVARLAMA — kurus YUKARI
    yuv_ok = all(arama.fiyat_yukari_yuvarla(h) == b for h, b in YUVARLAMA)
    ol("A8 kurus YUKARI yuvarlanir (200.1 -> 201 TL)", yuv_ok)
    # Okuma yolu YUVARLAMAZ: bozuk deger sessizce gecerli sayilamaz.
    ol("A9 okuma yolu yuvarlamiyor (fail-closed)",
       arama.fiyat_tam_tl("200.1 TL") is None and build.feed_price("200.1 TL") is None)

    # (4) ALT KUME — uygulayici (OTORITE) kanonikten DAHA DAR
    uyg = os.path.join(TOOLS, "panel-uygulayici.py")
    with open(uyg, encoding="utf-8") as f:
        m = re.search(r'^FIYAT_BICIMI = re\.compile\(r"(.+?)"\)$', f.read(), re.M)
    if m:
        uyg_rx = re.compile(m.group(1))
        # Kanonigin REDDETTIGI hicbir deger uygulayicidan GECEMEZ.
        kacak = [h for h, _ in VAKALAR + YUVARLAMA
                 if arama.fiyat_bicim_sebebi(h) is not None and uyg_rx.match(h)]
        ol("A10 uygulayici kalibi kanonigin ALT KUMESI", not kacak, "kacak=%s" % kacak)
    else:
        ol("A10 uygulayici kalibi kanonigin ALT KUMESI", False,
           "panel-uygulayici.py FIYAT_BICIMI okunamadi")

    # (3) IKIZ KURAL — GERCEK JS kosturulur (ayna DEGIL)
    js = js_ikizi()
    if js is None:
        print("OLCULEMEDI — node yok ya da JS ikizi kosmadi; IKIZ KURAL kolu OLCULMEDI.")
        print("Neyi olcmek kapatir: `node` kurulu bir ortamda bu testi yeniden kos.")
        return 2
    js_fs, js_yuv = js
    ikiz_fs = all((js_fs[i] if js_fs[i] is not None else None) == VAKALAR[i][1]
                  for i in range(len(VAKALAR)))
    ol("A11 secenekler.js fiyatSayisi == kanonik (SEPET yolu)", ikiz_fs,
       "js=%s" % js_fs)
    ikiz_yuv = all(js_yuv[i] == YUVARLAMA[i][1] for i in range(len(YUVARLAMA)))
    ol("A12 yonet.js fiyatYukariYuvarla == arama.fiyat_yukari_yuvarla", ikiz_yuv,
       "js=%s" % js_yuv)

    gecen = sum(1 for _, ok, _ in sonuc if ok)
    for ad, ok, ek in sonuc:
        print("%s %s%s" % ("GECTI " if ok else "KIRMIZI", ad,
                           ("  [%s]" % ek) if (ek and not ok) else ""))
    print("SONUC: %d/%d iddia GECTI" % (gecen, len(sonuc)))
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())

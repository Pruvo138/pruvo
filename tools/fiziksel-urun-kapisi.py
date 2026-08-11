#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIZIKSEL URUN KAPISI — hazir ticari mal sayfasindan 3D-BASKI SECIM ARAYUZUNUN
kaldirildigini ve KARSILIGI OLMAYAN +%15 renk farkinin ULASILAMAZ oldugunu olcer.

NEDEN VAR (Okan, 31 Tem — canli kusur, ekran goruntusuyle isaretlendi)
----------------------------------------------------------------------
`urunler.json`da `"tur": "fiziksel"` tasiyan kayitlar HAZIR TICARI MALDIR (International
tekne boyasi, vernik, tiner...). Bunlari 3D baskiyla URETMIYORUZ; musteri ne malzeme ne
renk seciyor, fiyat da SABIT. Buna ragmen sayfalari `render_product` icinde
`fonksiyonel and not parametrik` daline dusuyordu (kategori "Marin" FONKSIYONEL_KATEGORILER
icinde) ve su besi basiyordu:
    1. Renk butonlari — Siyah/Beyaz/Gri/**Diğer (+%15)**
    2. Malzeme cipleri — PLA/PETG/ASA/TPU + "Tavsiyemiz" rozeti
    3. "Karbon fiber ... WhatsApp'tan bize yazin" muhendislik-malzeme notu
    4. "Hangi malzeme nerede kullanilir? Malzeme Rehberi ->" linki
    5. "1.000,00 TL'den başlayan" — oysa fiziksel urunun fiyati SABIT

🔴 BU BIR PARA KUSURUYDU, SAYFA KOZMETIGI DEGIL. "Diğer" secimi sepet satirina
`renk: "Diğer"` yazar; `secenekler.js` hesaplaFiyatKurus onu x1,15 yapar, malzeme cipi
ayrica x1,60'a (ASA) kadar cikarir. OLCULDU (secenekler.js satirOzeti — Worker'in
`sepetiFiyatla` sabit-fiyat kolunda cagirdigi AYNI fonksiyon; liste fiyati 1.000 TL):
    PLA/Siyah (varsayilan) -> 100000 kurus = 1.000,00 TL   (DOGRU)
    PLA/"Diğer"            -> 115000 kurus = 1.150,00 TL   (+150 TL karsiliksiz)
    ASA/"Diğer"            -> 184000 kurus = 1.840,00 TL   (+840 TL karsiliksiz)
Yani musteri bir boya kutusu icin var olmayan bir "ozel renk" secip %15 fazla odeyebiliyordu.

ONARIM (tools/build.py render_product): `tur == "fiziksel"` ise renk secici, malzeme
bolumu ve "…'den başlayan" metni BASILMAZ; KART_SECIM bayragi KAPATILIR; adet secici +
sepet ikonu + WhatsApp ikonu KALIR. Secici basilmadigi icin sepet satiri
`PRUVO_SECENEK.bosSatir` varsayilanlariyla (PLA/Siyah = x1,00) uretilir -> +%15 yolu
ISTEMCIDE ULASILAMAZ.

🔴 FAIL-CLOSED YONU: kosul "fiziksel ISE kaldir"dir, "3D ISE goster" DEGIL. `tur` alani
YOKSA ya da taninmayan bir deger tasiyorsa sayfa BUGUNKU gibi uretilir. Ters yazilsaydi
`tur`suz 15.930 baski urunu malzeme/renk secicisini + sepet ikonunu SESSIZCE kaybederdi.

IDDIALAR
--------
  P1 POZITIF   fiziksel fikstur sayfasinda renk butonu / data-renk / renkOzel / fil-cip /
               #filCipler / malzeme-link / "Tavsiyemiz" / "başlayan" / "+%15" YOK.
  P2 POZITIF   AYNI sayfada adet secici + sepet butonu + WhatsApp butonu VAR
               (kaldirmayi FAZLA yapmadik — sayfa satilabilir kaldi).
  P3 ODEME     fiziksel sayfada "Diğer" rengi URETEBILECEK hicbir kanca yok
               (data-renk / #renkOzel / #renkSec YOK ve KART_SECIM = false) -> sepet satiri
               bosSatir varsayilanina duser. Iddia node ile PARAYA baglanir: gercek
               secenekler.js'te bosSatir varsayilani liste fiyatini AYNEN verir, "Diğer"
               ise +%15 uretir (yani susturulan sey GERCEKTEN para yoluydu).
  N1 NEGATIF   `tur` alani OLMAYAN normal 3D urun sayfasinda baski secim ogelerinin +
               satilabilirlik ogelerinin HEPSI durur ve FIYAT OGESI bugunku kuralin
               yazdigi tutari tasir (regresyon nobetcisi, IKI fikstur: kategori onerisi +
               acik `tavsiyeFilament`). Fiyat metni beklentisi ELLE GOMULMEZ, build.py'nin
               karar noktasindan (ONERI_ONSECIM_ACIK + ilan_kurus + taban_fiyat_metni)
               TURETILIR — bkz. n1_fiyat_beklentisi().
  N2 FAIL-CLOSED  `tur` alani TANINMAYAN deger tasiyan urun ("fiziksel-degil", "3d", "",
               null, 0, dizi...) `tur`suz urunle BAYT-BAYT AYNI sayfayi uretir.

MUTASYON (--mutasyon): `tur == "fiziksel"` kosulu no-op edilir (iki yonde de) ve bu
kapinin KIRMIZI yandigi KANITLANIR. Probe DAR: her mutant, yalnizca o kosulun
yakalayabilecegi bir iddiayi dusurur (P/P3 ya da N1/N2), ikisi ayni anda degil.

Offline (ag yok), GERCEK urunler.json OKUNMAZ (sentetik fiksturler), repoya DOSYA YAZMAZ.
node ZORUNLU (deploy.yml setup-node kurar) — yoksa FAIL-CLOSED kirmizi: para iddiasi
(P3) olculmeden bu kapi YESIL veremez.

Kullanim:
    python3 tools/fiziksel-urun-kapisi.py
    python3 tools/fiziksel-urun-kapisi.py --mutasyon

Cikis kodlari: 0 = YESIL (butun iddialar olculdu ve gecti) · 1 = KIRMIZI.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
BUILD_YOL = os.path.join(TOOLS, "build.py")
SECENEKLER_YOL = os.path.join(ROOT, "secenekler.js")

# Kaldirilmasi gereken 3D-BASKI SECIM kancalari. (ad, arama dizesi) — hepsi ANA GOVDEDE
# (<main>, script/style cikarilmis) aranir: FOOT_NAV_HTML her sayfaya bir "/malzeme-rehberi/"
# linki basar, TUM sayfada arasaydik "Malzeme Rehberi kalkti" iddiasi footer'in KENDISIYLE
# karsilanir ve govdedeki link silinse bile OLU/YESIL kalirdi (ayni tuzak konfigur-test.py
# (e) bolumunde olculdu ve orada da bolgeyle kapatildi).
BASKI_SECIM_KANCALARI = [
    ("renk butonlari konteyneri", 'id="renkButonlar"'),
    ("renk butonu data-renk", "data-renk="),
    ('"Diğer (+%15)" etiketi', "Diğer (+%15)"),
    ("ozel renk metin kutusu", 'id="renkOzel"'),
    ("malzeme cipi", "fil-cip"),
    ("malzeme cipleri konteyneri", 'id="filCipler"'),
    ('"Tavsiyemiz" rozeti', "Tavsiyemiz"),
    ("Malzeme Rehberi linki", 'class="malzeme-link"'),
]

# 🔴 "…'den başlayan" IKI EKSENDE FARKLI SEY OLCER — bu yuzden AYRI durur:
#   P1 (fiziksel sayfa): SABIT bir yasaktir. Hazir ticari malin fiyati SABITTIR; hicbir
#      kural onu "…'den başlayan"a cevirmez, o yuzden burada dize elle yazilabilir.
#   N1 (`tur`suz 3D sayfa): fiyat ogesinin METNI KURALA GORE degisir (on-secim acikken
#      kesin tutar, kapaliyken taban + "başlayan"). Orada beklenti n1_fiyat_beklentisi()
#      ile build.py'nin KENDI karar noktasindan TURETILIR — bkz. asagisi.
FIYAT_METNI_KANCASI = ('"…\'den başlayan" fiyat', "den başlayan")

# P1'in aradigi tam kume (fiziksel sayfada HICBIRI olmayacak).
BASKI_KANCALARI = BASKI_SECIM_KANCALARI + [FIYAT_METNI_KANCASI]

# Kalmasi ZORUNLU ogeler — "kaldirmayi fazla yapma" nobetcisi. HER IKI sayfada da durur:
# fiziksel sayfada fiyat SABIT liste fiyatidir, `tur`suz 3D sayfasinda kurala gore turer —
# ama OGENIN KENDISI iki tarafta da basilir, kaybolmasi REGRESYONDUR.
KALAN_OGELER = [
    ("adet secici", 'id="adetSec"'),
    ("sepete ekle butonu", 'id="cartBtn"'),
    ("WhatsApp butonu", 'id="orderAlt"'),
    ("fiyat ogesi (#opsiyonFiyat)", 'id="opsiyonFiyat"'),
]


def n1_fiyat_beklentisi(mod, p):
    """N1'in fiyat METNI beklentisi — KARAR TABLOSUNDAN turetilir, ELLE GOMULMEZ.

    🔴 NEDEN TURETILIYOR (11 Agu, olculmus bayatlama): bu kapi N1'de sabit
    `"…'den başlayan"` dizesini ariyordu. Ilan edilen tutar ON-SECILI malzemeden
    turetilince (isletme karari: urun sayfasi onerilen malzemede acilir) build.py o metni
    KURAL GEREGI kesin tutarla degistirdi; kapi eski dizeyi aradigi icin CI'da kirmizi
    yandi ve YAYINI DURDURDU — kod DOGRUYDU, KAPI BAYATTI. Beklentiyi yeniden elle yazmak
    ayni tuzagi bir sonraki kural degisikligine ertelemek olurdu.

    Beklenti build.py'nin KENDI karar noktasindan okunur (ONERI_ONSECIM_ACIK bayragi +
    ilan_kurus + taban_fiyat_metni) — yani kapi "bugunku kural neyse onu" olcer.
    KORLESTIRMEZ: oge capasi (#opsiyonFiyat) KALAN_OGELER'de ayrica aranir ve METIN
    bos/eksik olamaz; fiyat ogesini gercekten silen ya da tutari on-secim yerine liste
    fiyatindan tureten mutant N1'i KIRMIZI yakar (bkz. MUTANTLAR M3/M4).

    Tautoloji degil: fikstur kategorisi ("Marin") kategori onerisi tasir -> ilan edilen
    tutar (ASA, 1.600,00 TL) liste fiyatindan (1.000,00 TL) FARKLIDIR; ikinci fikstur
    ACIK bir `tavsiyeFilament` tasir (PETG, 1.300,00 TL) -> beklenti sabit bir sayiya da
    urunden bagimsiz tek bir metne de COKMEZ."""
    k = mod.ilan_kurus(p)
    if mod.ONERI_ONSECIM_ACIK and k is not None:
        metin = mod.taban_fiyat_metni(k / 100.0)
        return ("ilan edilen kesin tutar %r (on-secim: %s)"
                % (metin, mod.on_secim_malzeme(p)), metin)
    # Kural KAPALI (ya da fiyatsiz urun): eski davranis — taban "…'den başlayan".
    return FIYAT_METNI_KANCASI


# --------------------------------------------------------------------------- fiksturler
def _urun(uid, tur=Ellipsis, tavsiye=Ellipsis):
    """Sentetik urun kaydi. tur=Ellipsis -> `tur` ALANI HIC YOK (normal 3D urun).
    Kategori "Marin" BILEREK secildi: FONKSIYONEL_KATEGORILER icinde, yani `tur` devreye
    girmezse sayfa kart-secim (renk+malzeme) dalina duser — kapinin olctugu tam eksen.
    Fiyat 1.000 TL: kategori onerisi (ASA, +%60) uygulanirsa ilan edilen tutar 1.600,00 TL
    olur — yani liste fiyatindan AYIRT EDILEBILIR (zayif fikstur tuzagi kapali).
    tavsiye=... -> `tavsiyeFilament` alani (ACIK oneri; ilan tutari kategoriden AYRILIR)."""
    u = {
        "id": uid,
        "baslik": "Sinama Urunu",
        "kategori": "Marin",
        "marka": ["Sinama"],
        "fiyat": "1000 TL",
        "aciklama": "Sinama aciklamasi.\nIkinci satir.",
        "gorseller": ["https://media.example/%s-1.jpg" % uid],
    }
    if tur is not Ellipsis:
        u["tur"] = tur
    if tavsiye is not Ellipsis:
        u["tavsiyeFilament"] = tavsiye
    return u


def _govde(html):
    """ANA GOVDE: <main> icerigi, script/style cikarilmis (footer/inline JS sizmasin)."""
    m = re.search(r"<main\b.*?</main>", html, re.S)
    g = m.group(0) if m else html
    g = re.sub(r"<script\b.*?</script>", "", g, flags=re.S)
    return re.sub(r"<style\b.*?</style>", "", g, flags=re.S)


# --------------------------------------------------------------------------- build modulu
def build_modulu(mutasyon=None):
    """tools/build.py'yi (istege bagli TEK bir kaynak-kodu mutasyonuyla) yukler.

    Mutasyon DISKE YAZILMAZ — kaynak bellekte degistirilip exec edilir. Diske yazmak bu
    depoda olculmus bir tuzaktir: kosum yarida kalirsa mutant build.py commit'e sizar."""
    with open(BUILD_YOL, encoding="utf-8") as f:
        src = f.read()
    if mutasyon is not None:
        eski, yeni = mutasyon
        if src.count(eski) != 1:
            raise SystemExit("MUTASYON CAPASI KAYIP/COKLU (%d adet): %r — build.py degismis, "
                             "mutasyon capasi guncellenmeli." % (src.count(eski), eski))
        src = src.replace(eski, yeni, 1)
    mod = types.ModuleType("build_olculen")
    mod.__file__ = BUILD_YOL
    mod.__name__ = "build_olculen"       # __main__ DEGIL -> main() kendiliginden kosmaz
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(src, BUILD_YOL, "exec"), mod.__dict__)
    return mod


# --------------------------------------------------------------------------- node (para)
def para_olcumu():
    """GERCEK secenekler.js ile: bosSatir varsayilani vs "Diğer" rengi — kurus farki.
    Kopya/taklit YOK; Worker'in (shop/src/index.js) import ettigi AYNI dosya kosturulur."""
    betik = (
        'const S=(await import(%s)).default||globalThis.PRUVO_SECENEK;'
        'const U={kategori:"Marin",fiyat:"1000 TL",parametrik:false,boy_secenekleri:[]};'
        'const b=globalThis.PRUVO_SECENEK.bosSatir("x");'
        'const O=(r)=>globalThis.PRUVO_SECENEK.satirOzeti(U,'
        '{...b,malzeme:r.m,renk:r.r,renk_ozel:r.o||"",adet:1}).birimKurus;'
        'console.log(JSON.stringify({'
        'varsayilan_malzeme:b.malzeme,varsayilan_renk:b.renk,'
        'varsayilan_kurus:O({m:b.malzeme,r:b.renk}),'
        'diger_kurus:O({m:"PLA",r:"Diğer",o:"turuncu"}),'
        'asa_diger_kurus:O({m:"ASA",r:"Diğer",o:"turuncu"}),'
        'renkler:globalThis.PRUVO_SECENEK.RENK_SECENEKLERI}));'
    ) % json.dumps("file://" + SECENEKLER_YOL)
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", encoding="utf-8", delete=False) as f:
        f.write(betik)
        yol = f.name
    try:
        r = subprocess.run([os.environ.get("NODE", "node"), yol],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        # FAIL-CLOSED: node yoksa para iddiasi OLCULEMEZ -> kapi YESIL VEREMEZ.
        raise SystemExit("KIRMIZI: node kosturulamadi (%s) — P3 para iddiasi olculemedi. "
                         "deploy.yml setup-node BLOKLAYICI on-kosuldur." % e)
    finally:
        os.unlink(yol)
    if r.returncode != 0:
        raise SystemExit("KIRMIZI: secenekler.js node'da kosmadi:\n%s" % (r.stderr or "")[:2000])
    return json.loads(r.stdout.strip().splitlines()[-1])


# --------------------------------------------------------------------------- iddialar
def kosum(mod, para):
    """Butun iddialari olcer; (hatalar, satirlar) dondurur. hatalar bos = YESIL."""
    hatalar, satirlar = [], []

    fiz = _urun("sinama-fiziksel", tur="fiziksel")
    nrm = _urun("sinama-normal")                      # `tur` alani YOK, kategori onerisi
    # IKINCI `tur`suz fikstur: ACIK `tavsiyeFilament` -> ilan edilen tutar kategori
    # onerisininkinden de liste fiyatindan da FARKLI. Tek fikstur olsaydi "tutari sabitle"
    # mutanti (M4) yesil gecebilirdi.
    nrm2 = _urun("sinama-normal-oneri", tavsiye=["PETG"])
    tum = [fiz, nrm, nrm2]

    fiz_html = mod.render_product(fiz, tum)
    fiz_g = _govde(fiz_html)
    nrm_html = mod.render_product(nrm, tum)
    nrm_g = _govde(nrm_html)
    nrm2_g = _govde(mod.render_product(nrm2, tum))

    # --- P1: baski secim kancalari fiziksel sayfada YOK
    p1_eksik = [ad for ad, ip in BASKI_KANCALARI if ip in fiz_g]
    if p1_eksik:
        hatalar.append("P1 fiziksel sayfada hala baski secim kancasi var: " + ", ".join(p1_eksik))
    satirlar.append("P1 baski secim kancalari (9) fiziksel sayfada: %s"
                    % ("HEPSI YOK ✔" if not p1_eksik else "SIZAN: %s ✘" % p1_eksik))

    # --- P2: satilabilirlik korundu
    p2_eksik = [ad for ad, ip in KALAN_OGELER if ip not in fiz_g]
    if p2_eksik:
        hatalar.append("P2 fiziksel sayfadan FAZLA kaldirildi, eksik: " + ", ".join(p2_eksik))
    satirlar.append("P2 adet+sepet+WhatsApp+fiyat ogesi fiziksel sayfada: %s"
                    % ("HEPSI VAR ✔" if not p2_eksik else "EKSIK: %s ✘" % p2_eksik))

    # --- P3: ODEME — "Diğer" uretebilecek kanca yok + KART_SECIM kapali
    p3 = []
    for ad, ip in [("renk butonu (data-renk)", "data-renk="),
                   ("ozel renk kutusu (#renkOzel)", 'id="renkOzel"'),
                   ("renk dropdown (#renkSec)", 'id="renkSec"')]:
        if ip in fiz_html:                      # TUM sayfa: inline JS DAHIL
            p3.append(ad)
    if "KART_SECIM = false" not in fiz_html:
        # KART_SECIM acik kalsaydi: (a) currentSatir seciliRenk'i satira yazan kola girer,
        # (b) hicbir cip/buton basilmadigi icin seciliMalzeme/seciliRenk sonsuza kadar bos
        #     kalir ve SEPETE EKLE butonu SESSIZCE hicbir sey yapmaz.
        p3.append("KART_SECIM bayragi kapatilmamis")
    if p3:
        hatalar.append("P3 fiziksel sayfada +%15 'Diğer' yolu HALA ULASILABILIR: " + ", ".join(p3))
    # Para capasi: susturulan seyin GERCEKTEN para oldugunu gercek secenekler.js ile kanitla.
    if para["varsayilan_kurus"] != 100000:
        hatalar.append("P3 para capasi: bosSatir varsayilani liste fiyatini vermiyor (%d kurus)"
                       % para["varsayilan_kurus"])
    if para["diger_kurus"] != 115000:
        hatalar.append("P3 para capasi: 'Diğer' rengi +%%15 uretmiyor (%d kurus) — kapinin "
                       "olctugu para ekseni degismis, gerekce guncellenmeli"
                       % para["diger_kurus"])
    if "Diğer" not in para["renkler"]:
        hatalar.append("P3 para capasi: RENK_SECENEKLERI'nde 'Diğer' yok — iddia OLU kalir")
    satirlar.append("P3 odeme: fiziksel sayfada 'Diğer' kancasi %s | bosSatir=%s/%s -> %d krs "
                    "· 'Diğer' -> %d krs · ASA+'Diğer' -> %d krs"
                    % ("YOK ✔" if not p3 else "VAR ✘",
                       para["varsayilan_malzeme"], para["varsayilan_renk"],
                       para["varsayilan_kurus"], para["diger_kurus"], para["asa_diger_kurus"]))

    # --- N1: `tur`suz normal 3D urunde HER SEY yerinde (regresyon nobetcisi)
    # Fiyat METNI beklentisi urun BASINA turetilir (karar tablosu); geri kalan ogeler sabit.
    n1_eksik, n1_fiyat_rapor = [], []
    for etiket, urun_, govde in [("kategori-onerisi", nrm, nrm_g),
                                 ("acik-oneri", nrm2, nrm2_g)]:
        beklenen = BASKI_SECIM_KANCALARI + KALAN_OGELER + [n1_fiyat_beklentisi(mod, urun_)]
        n1_eksik += ["%s/%s" % (etiket, ad) for ad, ip in beklenen if ip not in govde]
        n1_fiyat_rapor.append("%s -> %s" % (etiket, n1_fiyat_beklentisi(mod, urun_)[1]))
    if "KART_SECIM = true" not in nrm_html:
        n1_eksik.append("KART_SECIM bayragi")
    if n1_eksik:
        hatalar.append("N1 REGRESYON — `tur`suz 3D urun sayfasi oge kaybetti: "
                       + ", ".join(n1_eksik))
    satirlar.append("N1 `tur`suz 3D urun sayfasi (2 fikstur x %d oge + bayrak; "
                    "fiyat metni KARAR TABLOSUNDAN: %s): %s"
                    % (len(BASKI_SECIM_KANCALARI) + len(KALAN_OGELER) + 1,
                       " · ".join(n1_fiyat_rapor),
                       "HEPSI YERINDE ✔" if not n1_eksik else "KAYIP: %s ✘" % n1_eksik))

    # --- N2: FAIL-CLOSED — taninmayan `tur` degeri `tur`suzle BAYT-BAYT AYNI
    n2_sapan = []
    for deger in ["fiziksel-degil", "3d", "Fiziksel", "FIZIKSEL", " fiziksel", "fiziksel ",
                  "", None, 0, 1, True, False, [], ["fiziksel"], {"t": "fiziksel"}]:
        u = _urun("sinama-normal", tur=deger)
        if mod.render_product(u, tum) != nrm_html:
            n2_sapan.append(repr(deger))
    if n2_sapan:
        hatalar.append("N2 FAIL-CLOSED IHLALI — taninmayan `tur` degeri sayfayi degistirdi: "
                       + ", ".join(n2_sapan))
    satirlar.append("N2 fail-closed (16 taninmayan `tur` degeri, bayt-esitlik): %s"
                    % ("HEPSI `tur`suzle AYNI ✔" if not n2_sapan else "SAPAN: %s ✘" % n2_sapan))
    return hatalar, satirlar


# --------------------------------------------------------------------------- mutasyon
# Her mutant DAR bir probe'dur: yalnizca `tur == "fiziksel"` kosulunun yakalayabilecegi bir
# seyi bozar. Kosul no-op edilirse hangi iddianin dusecegi ONCEDEN yazilir; BASKA bir iddia
# dusuyorsa probe genis demektir ve bu da hata sayilir.
MUTANTLAR = [
    ('fiziksel = (p.get("tur") == "fiziksel")',
     'fiziksel = False',
     "kosul DAIMA yanlis -> fiziksel urun eski (baski secimli) sayfayi alir",
     ("P1", "P3")),
    ('fiziksel = (p.get("tur") == "fiziksel")',
     'fiziksel = True',
     "kosul DAIMA dogru -> `tur`suz 3D urun secicilerini kaybeder",
     ("N1", "N2")),
    # M3/M4 — N1'in fiyat beklentisi KARAR TABLOSUNDAN turetildigi icin "kapi korlesti mi"
    # sorusu ayrica olculur. Capalar yukaridakilerden AYRIKTIR (baska satir, baska ifade):
    # ayni capaya bindirilseydi dort mutant tek bir kosulu olcerdi.
    ('\'<div class="opsiyon-fiyat" id="opsiyonFiyat">%s</div>\' % baslangic_fiyat',
     '""',
     "kart-secim dalinda FIYAT OGESI TAMAMEN silinir -> ilan edilen tutar sayfadan kaybolur",
     ("N1",)),
    ('baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))',
     'baslangic_fiyat = esc(taban_fiyat_metni(_birim_kurus(p, VARSAYILAN_MALZEME) / 100.0))',
     "ilan edilen tutar ON-SECIMDEN degil LISTE tabanindan turer -> sayfa dusuk tutar ilan eder",
     ("N1",)),
]


def mutasyon_kosumu(para):
    print("=== MUTASYON: `tur == \"fiziksel\"` kosulu no-op edildiginde kapi KIRMIZI mi?")
    tamam = True
    for eski, yeni, aciklama, beklenen in MUTANTLAR:
        mod = build_modulu((eski, yeni))
        hatalar, _ = kosum(mod, para)
        etiketler = sorted({h.split()[0] for h in hatalar})
        kirmizi = bool(hatalar)
        dogru_eksen = set(etiketler) and set(etiketler).issubset(set(beklenen))
        durum = "KIRMIZI ✔" if kirmizi else "YESIL ✘ (OLU IDDIA)"
        print("  mutant: %s -> %s" % (yeni, aciklama))
        print("    sonuc: %s | dusen iddialar: %s | beklenen eksen: %s%s"
              % (durum, etiketler or "-", list(beklenen),
                 "" if dogru_eksen else "  <- PROBE GENIS/KAYMIS ✘"))
        for h in hatalar:
            print("      - " + h)
        if not (kirmizi and dogru_eksen):
            tamam = False
    print()
    print("MUTASYON: %s" % ("GECTI — kosul kaldirilinca kapi KIRMIZI yaniyor (iddia CANLI)."
                            if tamam else "KALDI — iddia OLU ya da probe genis."))
    return 0 if tamam else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Fiziksel urun sayfasi 3D-baski UI kapisi")
    ap.add_argument("--mutasyon", action="store_true",
                    help="kosulu no-op edip kapinin KIRMIZI yandigini kanitla")
    args = ap.parse_args()

    os.chdir(ROOT)
    para = para_olcumu()

    if args.mutasyon:
        return mutasyon_kosumu(para)

    mod = build_modulu()
    hatalar, satirlar = kosum(mod, para)
    print("=== FIZIKSEL URUN KAPISI (tools/build.py render_product · sentetik fikstur)")
    for s in satirlar:
        print("  " + s)
    print()
    if hatalar:
        print("KIRMIZI — %d iddia ihlal edildi:" % len(hatalar))
        for h in hatalar:
            print("  ✘ " + h)
        return 1
    print("YESIL — fiziksel urun sayfasinda 3D-baski secimi YOK, +%15 renk farki "
          "ULASILAMAZ, `tur`suz 15.930 baski urununde regresyon YOK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

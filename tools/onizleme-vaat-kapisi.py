#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/onizleme-vaat-kapisi.py — URETILEMEZ KONFIGURASYON: SATIS KAPISI + MUSTERI VAADI.

NEDEN VAR (2026-08-03, OLCULDU — SESSIZ-HATA, TICARI SONUCLU)
------------------------------------------------------------
Sari (parametrik) serinin sema kapisi `KONF.dogrula` bir parametre setine
`gecerli:true` diyor; ama URETIM UCU (/ic-derle) AYNI seti assert ile 400/422
vererek REDDEDIYOR. Yani sema kapisindan gecen bir bolge uretim motorunda YOK.
O bolgede fiyat URETILIYOR, sepete giriyor, siparis kabul ediliyor ve PARA
TAHSIL EDILIYOR; hicbir yerde alarm calmiyor.

OLCUM (aile basina 2001 parametre seti + kose alt-uzayinin %100'u; hukum uretim
ucunun KENDI cevabi):
    petek  %50,0   mod="kabartma" bolgesinin TAMAMI      -> satis kapisi ACIKTI
    cetvel %66,7   secim-tanimsiz:tip                     -> satis kapisi ACIKTI
    kase   %83,3   sap + bicim (damga/kase)               -> satis kapisi ACIKTI
    rulman %32,88  bilya + makara                         -> KAPALI (null) ✅ kiyas
    huni · izgara · kasnak · kayis · oring · pervane %0,00 -> TEMIZ, acik kalir
Somut zarar: petek `mod=kabartma, desen=petek, en=125, boy=114, kalinlik=7,
goz=15` -> 60000 kurus (600,00 TL) tutar uretiyordu; ayni konfigurasyon /ic-derle
tarafindan 400 ile reddediliyor.

IKINCI ARIZA — MUSTERIYE YANLIS VAAT: urun sayfasi (tools/build.py ONIZLEME_JS)
bu bolgede "Bu secenekle 3D onizleme simdilik sunulamiyor; SIPARIS VEREBILIRSINIZ,
URETIM ETKILENMEZ" basiyordu. Bu cumle tam olarak URETILEMEZ bolgede basiliyordu.

YAPISAL KURAL (bu kapinin iddiasi — tek satirlik liste duzeltmesi DEGIL)
-----------------------------------------------------------------------
`secenekler.js ONIZLEME_KISITLAR` zaten "uretim motorunda karsiligi olmayan secim
degerleri" beyanidir. O halde:

    ONIZLEME_KISITLAR'da beyani olan bir AILE, HACIM_DOGRULANMIS_AILELER'de
    (yani SATISTA) OLAMAZ.  Iki kumenin KESISIMI BOS olmalidir.

Yarin yeni bir kisit beyan edilirse o aile kendiliginde satista KALAMAZ: bu kapi
kirmizi yakar. Denylist degil, TURETILMIS kural — bayatlayacak ikinci bir liste
YOK ([[ikiz-tanim-sessiz-ayrisma]]).

OLCULEN IDDIALAR (her biri AYRI; hicbiri digerinin VEYA'si degil)
-----------------------------------------------------------------
  A1  ONIZLEME_KISITLAR'daki her urun id'si bir semaya + aileye cozuldu
  A1b OLCULEN uc ailenin (petek/cetvel/kase) kisit beyani HALA yerinde (capa bayat degil)
  A2* OLCULEN uc aile icin parametrikFiyatKurus(...) -> null    (aile basina 1 iddia)
  A3  kisitli aileler kumesi ∩ HACIM_DOGRULANMIS_AILELER = ∅    (yapisal kural)
      🔴 A3, A2'lerin VEYA'si DEGILDIR ve bu KANITLANIR: M4 mutanti (YENI bir kisit
      beyan edilip aile satista birakilir) A3'u TEK BASINA kirmizi yakar, A2'ler
      yesil kalir; tersine M3 (fail-closed `return null` oldurulur) A2'leri yakar,
      A3 yesil kalir. Ayirt edici mutant olmasaydi bu iki eksen TEK iddia olurdu
      ([[beyan-edilmis-survivor]]).
  A4  CANLILIK: acik aileler HALA fiyat uretiyor (kapi kor degil — her seye null
      donduren bir kod A2'yi de gecerdi; tek yonlu test olu nobetcidir)
  A5  fikstur olu degil: en az bir kisitli aile VAR
  B1  build.py'de `onizleme-secenek-kisiti` musteri metninin IKI cagri yeri de
      bulundu (on-kontrol + hata tablosu). Bulunamazsa B2/B4 OLCULEMEDI.
  B2  o metinlerin HICBIRI "siparis verebilirsiniz / uretim etkilenmez" sinifindan
      bir VAAT tasimiyor
  B4  iki cagri yerindeki metin BIREBIR AYNI (biri duzeltilip digeri yalan
      soylemeye devam edemez)

NOT — hangi eksen KIMIN: semanin ONARIMI (uretilemez bolgenin sematik olarak
kapatilmasi) KaaN'in duzlemidir. Bu kapi yalnizca SATIS ucunu ve MUSTERI METNINI
fail-closed tutar; sema onarilip kisit kalkinca aile kendiliginden geri acilir.

KULLANIM
    python3 tools/onizleme-vaat-kapisi.py
    python3 tools/onizleme-vaat-kapisi.py --repo /gecici/ayna
    python3 tools/onizleme-vaat-kapisi.py --kendini-test

KIRMIZI-MUTASYON TURU (--kendini-test): mutasyon DAIMA KOPYAYA uygulanir; canli
agaca HICBIR yazma yapilmaz (sha256 bas/son ciktida basilir). Kontrol mutantlari
(gercek bir bozulma OLMAYAN degisiklikler) YESIL kalmalidir; kalmazsa kapi asiri
hevesli demektir ve bu tur kirmizi yanar.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK_VARSAYILAN = os.path.dirname(TOOLS)

# Musteriye ASLA verilemeyecek vaatler (uretilemez bolgede basilan metinde).
# Normalize edilmis (kucuk harf + Turkce harf katlamasi) halde aranir.
YASAK_VAAT = (
    "siparis verebilirsiniz",
    "siparis verebilir",
    "uretim etkilenmez",
    "uretimi etkilemez",
    "uretim etkilenmiyor",
    "siparisinizi alabiliriz",
)

_KATLAMA = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiIosuCGOSU")

# OLCULEN uc aile (2026-08-03 sema araligi taramasi) — A2'nin CAPASI.
# Bunlar SABIT capalardir: "kisitli aileler" kumesinden TURETILMEZ, cunku o kume
# degisince A2 sessizce baska bir seyi olcmeye baslardi. Capa bayatlarsa A1b yakar.
OLCULEN_AILELER = (
    ("petek", 'mod="kabartma" bolgesinin tamami, %50,0 uretilemez'),
    ("cetvel", "secim-tanimsiz:tip, %66,7 uretilemez"),
    ("kase", "sap + bicim, %83,3 uretilemez"),
)


def _normal(s):
    return s.translate(_KATLAMA).lower()


def _sha256(yol):
    if not os.path.exists(yol):
        return "YOK"
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------------------
# BOLUM A — SATIS KAPISI (para).  Degerler GERCEK secenekler.js'ten, node ile
# okunur; regex ile "sanki okumus gibi" yapilmaz ([[mimar-kapi-parser-taklidi]]).
# ---------------------------------------------------------------------------
NODE_PROBU = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const KOK = process.argv[2];
const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(KOK, "secenekler.js"), "utf8"), sandbox);
const S = sandbox.window.PRUVO_SECENEK;
if (!S) { console.error("PRUVO_SECENEK yuklenemedi"); process.exit(2); }
const sorulan = JSON.parse(process.argv[3]);
const fiyat = {};
for (const a of sorulan) {
  // Taban 100 TL, tabanHacim 1000, hacim 5000 -> ACIK ailede 30000 kurus (3x tavan).
  fiyat[a] = S.parametrikFiyatKurus(a, 100, 1000, 5000, "PLA", "Siyah");
}
console.log(JSON.stringify({
  kisitlar: Object.keys(S.ONIZLEME_KISITLAR || {}),
  acik: Object.keys(S.HACIM_DOGRULANMIS_AILELER || {}),
  fiyat: fiyat,
}));
"""


def _node_olc(kok, sorulan_aileler):
    """secenekler.js'i GERCEKTEN kosturur. (veri, hata) doner."""
    if shutil.which("node") is None:
        return None, "node yok -> fiyat ekseni OLCULEMEDI (fail-closed)"
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(NODE_PROBU)
        prob = f.name
    try:
        s = subprocess.run(["node", prob, kok, json.dumps(sorted(sorulan_aileler))],
                           capture_output=True, text=True)
        if s.returncode != 0:
            return None, "node probu rc=%d: %s" % (s.returncode, (s.stderr or "").strip()[:400])
        return json.loads(s.stdout), None
    except ValueError as e:
        return None, "node ciktisi ayristirilamadi: %s" % e
    finally:
        os.unlink(prob)


def _aile_cozumle(kok, urun_idleri):
    """urun id -> sema.hacimFormulu. (esleme, eksikler) doner."""
    dizin = os.path.join(kok, "jenerator", "urunler")
    esleme, eksik = {}, []
    for uid in urun_idleri:
        yol = os.path.join(dizin, uid + ".json")
        if not os.path.exists(yol):
            eksik.append(uid + " (sema dosyasi yok)")
            continue
        try:
            with open(yol, encoding="utf-8") as f:
                aile = json.load(f).get("hacimFormulu")
        except ValueError as e:
            eksik.append("%s (sema bozuk: %s)" % (uid, e))
            continue
        if not isinstance(aile, str) or not aile:
            eksik.append(uid + " (hacimFormulu yok)")
            continue
        esleme[uid] = aile
    return esleme, eksik


# ---------------------------------------------------------------------------
# BOLUM B — MUSTERI VAADI (metin).  build.py'nin urun sayfasina BASTIGI iki
# cagri yeri capalanir; capalar kayarsa B1 kirmizi yanar (sessizce "hic metin
# bulamadim -> yesil" hali YOK).
# ---------------------------------------------------------------------------
# 1) hata tablosu girisi:  "onizleme-secenek-kisiti":"...."
CAPA_TABLO = re.compile(r'"onizleme-secenek-kisiti"\s*:\s*"((?:[^"\\]|\\.)*)"')
# 2) ONIZLEME_KISITLAR on-kontrolunun hemen ardindaki de("....") cagrisi
CAPA_ONKONTROL_BAS = re.compile(r"PRUVO_SECENEK\.ONIZLEME_KISITLAR")
CAPA_DE = re.compile(r'\bde\("((?:[^"\\]|\\.)*)"\)')


def _vaat_metinleri(kok):
    """build.py'den iki musteri metnini cikarir. (metinler, tanilar) doner."""
    yol = os.path.join(kok, "tools", "build.py")
    tanilar = []
    if not os.path.exists(yol):
        return [], ["tools/build.py yok"]
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()

    metinler = []
    m = CAPA_TABLO.search(kaynak)
    if m:
        metinler.append(("hata-tablosu", m.group(1)))
    else:
        tanilar.append('capa kaydi: "onizleme-secenek-kisiti" hata tablosu girisi BULUNAMADI')

    o = CAPA_ONKONTROL_BAS.search(kaynak)
    if o:
        d = CAPA_DE.search(kaynak, o.end())
        if d:
            metinler.append(("on-kontrol", d.group(1)))
        else:
            tanilar.append("capa kaydi: ONIZLEME_KISITLAR on-kontrolunden sonra de(\"...\") yok")
    else:
        tanilar.append("capa kaydi: PRUVO_SECENEK.ONIZLEME_KISITLAR on-kontrolu BULUNAMADI")
    return metinler, tanilar


# ---------------------------------------------------------------------------
# OLCUM (tek kaynak: hem canli agac hem her mutant AYNI fonksiyondan gecer —
# olcut ESIT, [[kabul-araligi-karsilastirma-araligi]])
# ---------------------------------------------------------------------------
def olc(kok):
    """(iddialar, olculemedi) doner. iddialar: [(ad, ok, detay)]"""
    iddialar, olculemedi = [], []

    def iddia(ad, ok, detay=""):
        iddialar.append((ad, bool(ok), detay))

    # --- kisitli aileler
    veri, hata = _node_olc(kok, [])
    if veri is None:
        olculemedi.append("BOLUM A: " + hata)
        return iddialar, olculemedi

    kisit_urunleri = veri["kisitlar"]
    esleme, eksik = _aile_cozumle(kok, kisit_urunleri)
    iddia("A1 ONIZLEME_KISITLAR urun id'lerinin HEPSI semaya+aileye cozuldu",
          not eksik, "; ".join(eksik))
    kisitli_aileler = sorted(set(esleme.values()))

    iddia("A5 fikstur olu degil: en az bir kisitli aile var",
          len(kisitli_aileler) > 0, "kisitli aile=%d" % len(kisitli_aileler))

    capa_aileleri = [a for a, _ in OLCULEN_AILELER]
    bayat = [a for a in capa_aileleri if a not in kisitli_aileler]
    iddia("A1b OLCULEN uc ailenin kisit beyani hala yerinde (A2 capasi bayat degil)",
          not bayat, "kisit beyani KALKMIS: %s" % bayat)

    acik = set(veri["acik"])
    # Fiyat olcumu: capa aileleri (null OLMALI) + acik ornekler (fiyat OLMALI)
    ornek_acik = sorted(acik - set(kisitli_aileler))[:3]
    veri2, hata2 = _node_olc(kok, capa_aileleri + ornek_acik)
    if veri2 is None:
        olculemedi.append("BOLUM A fiyat: " + hata2)
    else:
        for aile, bolge in OLCULEN_AILELER:
            iddia("A2 uretilemez bolgesi olan aile tutar URETMEZ (null): %s [%s]"
                  % (aile, bolge),
                  veri2["fiyat"].get(aile, "YOK") is None,
                  "donen=%r" % (veri2["fiyat"].get(aile, "YOK"),))
        # CANLILIK: mesru is durmuyor. Bu iddia OLMASA "her seye null donduren"
        # bir kod A2'lerin hepsini gecerdi (olu nobetci).
        canli = [a for a in ornek_acik if veri2["fiyat"].get(a) == 30000]
        iddia("A4 CANLILIK: acik aileler HALA fiyat uretiyor (kapi kor degil)",
              len(ornek_acik) > 0 and len(canli) == len(ornek_acik),
              "acik ornek=%s uretilen=%s" % (ornek_acik,
                                             {a: veri2["fiyat"].get(a) for a in ornek_acik}))

    kesisim = sorted(set(kisitli_aileler) & acik)
    iddia("A3 YAPISAL KURAL: kisitli aileler ∩ satis listesi = ∅",
          not kesisim,
          "SATISTA KALMIS uretilemez aile: %s" % kesisim if kesisim else "")

    # --- BOLUM B
    metinler, tanilar = _vaat_metinleri(kok)
    iddia("B1 musteri metninin IKI cagri yeri de bulundu (on-kontrol + hata tablosu)",
          len(metinler) == 2, "; ".join(tanilar) or "bulunan=%d" % len(metinler))
    if len(metinler) != 2:
        olculemedi.append("B2/B4: capa(lar) kaymis -> metin ekseni olculemedi")
    else:
        kirli = []
        for etiket, metin in metinler:
            n = _normal(metin)
            for vaat in YASAK_VAAT:
                if vaat in n:
                    kirli.append("%s: '%s'" % (etiket, vaat))
        iddia("B2 uretilemez secenekte YANLIS VAAT basilmiyor",
              not kirli, "; ".join(kirli))
        iddia("B4 iki cagri yerindeki metin BIREBIR AYNI",
              metinler[0][1] == metinler[1][1],
              "on-kontrol != hata-tablosu" if metinler[0][1] != metinler[1][1] else "")

    return iddialar, olculemedi


def rapor(kok, sessiz=False):
    iddialar, olculemedi = olc(kok)
    kirmizi = [a for a in iddialar if not a[1]]
    if not sessiz:
        for ad, ok, detay in iddialar:
            print("  [%s] %s%s" % ("OK  " if ok else "HATA", ad,
                                   ("  -> " + detay) if (detay and not ok) else ""))
        for s in olculemedi:
            print("  [OLCULEMEDI] " + s)
        print("IDDIA=%d  KIRMIZI=%d  OLCULEMEDI=%d" %
              (len(iddialar), len(kirmizi), len(olculemedi)))
    return len(iddialar), len(kirmizi), len(olculemedi)


# ---------------------------------------------------------------------------
# KENDINI TEST — mutasyon turu.  MUTASYON DAIMA KOPYAYA ([[mutasyon-diske-yazma-tuzagi]]).
# ---------------------------------------------------------------------------
ESKI_VAAT = ("Bu seçenekle 3D önizleme şimdilik sunulamıyor; "
             "sipariş verebilirsiniz, üretim etkilenmez.")


def _ayna(kok):
    """olc() icin yeterli minimal agac: secenekler.js + tools/build.py KOPYA,
    jenerator/ SYMLINK (semalar salt-okunur girdi)."""
    hedef = tempfile.mkdtemp(prefix="onizleme-vaat-ayna-")
    shutil.copy2(os.path.join(kok, "secenekler.js"), os.path.join(hedef, "secenekler.js"))
    os.makedirs(os.path.join(hedef, "tools"))
    shutil.copy2(os.path.join(kok, "tools", "build.py"),
                 os.path.join(hedef, "tools", "build.py"))
    os.symlink(os.path.join(kok, "jenerator"), os.path.join(hedef, "jenerator"))
    return hedef


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, s):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(s)


# --- mutasyonlar: (ad, uygulayici, beklenen_kirmizi_iddia_onekleri) ---------
def _m_vaat_geri(ayna):
    """Eski YALAN metni IKI cagri yerine de geri koy."""
    yol = os.path.join(ayna, "tools", "build.py")
    kaynak = _oku(yol)
    kaynak = CAPA_TABLO.sub('"onizleme-secenek-kisiti":"%s"' % ESKI_VAAT, kaynak, count=1)
    o = CAPA_ONKONTROL_BAS.search(kaynak)
    d = CAPA_DE.search(kaynak, o.end())
    kaynak = kaynak[:d.start()] + 'de("%s")' % ESKI_VAAT + kaynak[d.end():]
    _yaz(yol, kaynak)
    return ["B2"]


def _m_petek_geri(ayna):
    """Kapatilan aileyi satis listesine GERI EKLE."""
    yol = os.path.join(ayna, "secenekler.js")
    kaynak = _oku(yol)
    kaynak = kaynak.replace("oring: 0.39, pervane: 0.38",
                            "oring: 0.39, pervane: 0.38, petek: 0.00", 1)
    _yaz(yol, kaynak)
    return ["A2 uretilemez bolgesi olan aile tutar URETMEZ (null): petek", "A3"]


def _m_null_kaldir(ayna):
    """parametrikFiyatKurus'un fail-closed `return null` kolunu OLDUR."""
    yol = os.path.join(ayna, "secenekler.js")
    kaynak = _oku(yol)
    kaynak = kaynak.replace("if (!hacimDogrulanmisMi(aile)) { return null; }",
                            "if (false) { return null; }", 1)
    _yaz(yol, kaynak)
    return ["A2 uretilemez bolgesi olan aile tutar URETMEZ (null): cetvel",
            "A2 uretilemez bolgesi olan aile tutar URETMEZ (null): kase",
            "A2 uretilemez bolgesi olan aile tutar URETMEZ (null): petek"]


def _m_yeni_kisit(ayna):
    """YENI bir kisit beyan et ama aileyi satista BIRAK -> yapisal kural tek basina
    kirmizi yakmali (A3'un A2'lerden BAGIMSIZ eksen oldugunun kaniti)."""
    yol = os.path.join(ayna, "secenekler.js")
    kaynak = _oku(yol)
    kaynak = kaynak.replace('"olcuye-ozel-cetvel": { tip: ["duz"] },',
                            '"olcuye-ozel-cetvel": { tip: ["duz"] },\n'
                            '    "olcuye-ozel-oring-conta": { profil: ["yuvarlak"] },', 1)
    _yaz(yol, kaynak)
    return ["A3"]


def _m_liste_bosalt(ayna):
    """Satis listesini TUMUYLE bosalt -> A2/A3 yine yesil, ama CANLILIK (A4) kirmizi:
    'her seye null donduren' kod bu kapiyi gecemez."""
    yol = os.path.join(ayna, "secenekler.js")
    kaynak = _oku(yol)
    bas = kaynak.index("var HACIM_DOGRULANMIS_AILELER = {")
    son = kaynak.index("};", bas) + 2
    _yaz(yol, kaynak[:bas] + "var HACIM_DOGRULANMIS_AILELER = {};" + kaynak[son:])
    return ["A4"]


def _m_tablo_sil(ayna):
    """Hata tablosu girisini sil -> capa kayar, B1 kirmizi (sessiz yesil YOK)."""
    yol = os.path.join(ayna, "tools", "build.py")
    kaynak = _oku(yol)
    m = CAPA_TABLO.search(kaynak)
    bas = kaynak.rindex("\n", 0, m.start())
    son = kaynak.index("\n", m.end())
    _yaz(yol, kaynak[:bas] + kaynak[son:])
    return ["B1"]


def _m_tek_yer_ayrisir(ayna):
    """Yalniz ON-KONTROL metnini degistir (vaat YOK, ama iki yer AYRISTI)."""
    yol = os.path.join(ayna, "tools", "build.py")
    kaynak = _oku(yol)
    o = CAPA_ONKONTROL_BAS.search(kaynak)
    d = CAPA_DE.search(kaynak, o.end())
    kaynak = kaynak[:d.start()] + 'de("Bu secenek su an sunulamiyor.")' + kaynak[d.end():]
    _yaz(yol, kaynak)
    return ["B4"]


# --- KONTROL mutantlari: gercek bir bozulma DEGIL -> YESIL kalmali -----------
def _k_yorum(ayna):
    yol = os.path.join(ayna, "tools", "build.py")
    _yaz(yol, _oku(yol) + "\n# kontrol mutanti: anlamsiz yorum (davranis degismedi)\n")
    return []


def _k_sapma_degeri(ayna):
    """ACIK bir ailenin hacim sapma SAYISINI degistir: anahtar kumesi ayni ->
    kapinin olctugu hicbir sey degismemeli."""
    yol = os.path.join(ayna, "secenekler.js")
    _yaz(yol, _oku(yol).replace("braket: 0.27", "braket: 0.28", 1))
    return []


def _k_sira(ayna):
    """Satis listesindeki iki anahtarin SIRASINI degistir (kume ayni)."""
    yol = os.path.join(ayna, "secenekler.js")
    _yaz(yol, _oku(yol).replace("oring: 0.39, pervane: 0.38",
                                "pervane: 0.38, oring: 0.39", 1))
    return []


MUTANTLAR = [
    ("M1 eski YALAN vaat metni geri geldi", _m_vaat_geri, False),
    ("M2 kapatilan aile (petek) satis listesine geri eklendi", _m_petek_geri, False),
    ("M3 parametrikFiyatKurus fail-closed `return null` kolu olduruldu", _m_null_kaldir, False),
    ("M4 YENI kisit beyan edildi ama aile satista birakildi", _m_yeni_kisit, False),
    ("M5 satis listesi tumuyle bosaltildi (her seye null)", _m_liste_bosalt, False),
    ("M6 hata tablosu girisi silindi (capa kaydi)", _m_tablo_sil, False),
    ("M7 iki cagri yerinin metni ayristirildi", _m_tek_yer_ayrisir, False),
    ("K1 KONTROL: anlamsiz yorum eklendi", _k_yorum, True),
    ("K2 KONTROL: acik ailenin sapma SAYISI degisti", _k_sapma_degeri, True),
    ("K3 KONTROL: satis listesi anahtar SIRASI degisti", _k_sira, True),
]


def kendini_test(kok):
    izlenen = [os.path.join(kok, "secenekler.js"), os.path.join(kok, "tools", "build.py")]
    bas_sha = {y: _sha256(y) for y in izlenen}
    print("SHA256 BASTA:")
    for y in izlenen:
        print("  %s  %s" % (bas_sha[y], os.path.relpath(y, kok)))

    print("\nTABAN (mutasyonsuz ayna) — YESIL olmali:")
    ayna = _ayna(kok)
    try:
        taban_iddia, taban_kirmizi, taban_olculemedi = rapor(ayna)
    finally:
        shutil.rmtree(ayna)
    basarisiz = []
    if taban_kirmizi or taban_olculemedi:
        basarisiz.append("TABAN kirmizi/olculemedi (kirmizi=%d olculemedi=%d)"
                         % (taban_kirmizi, taban_olculemedi))

    print("\nMUTANTLAR (olcut TABANLA AYNI fonksiyon):")
    for ad, uygula, kontrol_mu in MUTANTLAR:
        ayna = _ayna(kok)
        try:
            beklenen = uygula(ayna)
            iddialar, olculemedi = olc(ayna)
            kirmizilar = [a for a, ok, _ in iddialar if not ok]
            # OLCUT ESITLIGI: mutant, tabanla AYNI sayida iddia uretmeli; uretmiyorsa
            # karsilastirma baska birimde yapiliyor demektir ([[hukum-yanlis-birimde]]).
            olcut_esit = (len(iddialar) == taban_iddia)
            if kontrol_mu:
                ok = (not kirmizilar) and (not olculemedi) and olcut_esit
                durum = "YESIL kaldi" if not kirmizilar else ("KIRMIZI: %s" % kirmizilar)
            else:
                # her beklenen onek fiilen kirmizi mi + BEKLENMEYEN kirmizi var mi
                eslesen = [b for b in beklenen
                           if any(k.startswith(b) for k in kirmizilar)]
                fazla = [k for k in kirmizilar
                         if not any(k.startswith(b) for b in beklenen)]
                ok = (len(eslesen) == len(beklenen)) and not fazla
                durum = "kirmizi=%s (beklenen onek=%s%s)" % (
                    kirmizilar, beklenen, "; FAZLA=%s" % fazla if fazla else "")
            # M6 capayi kaydirdigi icin olculemedi URETIR — bu BEKLENEN, kirmizi degil.
            if not kontrol_mu and ad.startswith("M6"):
                ok = ok and len(olculemedi) >= 1
            print("  [%s] %-58s %s%s" % ("PASS" if ok else "FAIL", ad, durum,
                                         "" if olcut_esit else "  [OLCUT KAYDI]"))
            if not ok:
                basarisiz.append(ad)
        finally:
            shutil.rmtree(ayna)

    print("\nSHA256 SONDA (canli agaca yazma OLMAMALI):")
    tutuyor = True
    for y in izlenen:
        s = _sha256(y)
        print("  %s  %s%s" % (s, os.path.relpath(y, kok),
                              "" if s == bas_sha[y] else "   🔴 DEGISTI"))
        tutuyor = tutuyor and (s == bas_sha[y])
    if not tutuyor:
        basarisiz.append("CANLI AGAC DEGISTI (mutasyon kopyaya uygulanmadi)")

    print("\nTABAN IDDIA=%d  MUTANT=%d (kirmizi bekleyen=%d, kontrol=%d)" %
          (taban_iddia, len(MUTANTLAR),
           sum(1 for _, _, k in MUTANTLAR if not k),
           sum(1 for _, _, k in MUTANTLAR if k)))
    if basarisiz:
        print("KIRMIZI: " + " | ".join(basarisiz))
        return 1
    print("KENDINI TEST YESIL.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=KOK_VARSAYILAN)
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test(a.repo)
    print("ONIZLEME VAAT KAPISI — uretilemez konfigurasyon: satis kapisi + musteri metni")
    _, kirmizi, olculemedi = rapor(a.repo)
    return 1 if (kirmizi or olculemedi) else 0


if __name__ == "__main__":
    sys.exit(main())

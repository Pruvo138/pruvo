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
Bir ailenin "sartsiz satilamaz" oldugunu bu depoda IKI kayit soyluyor:

  KOL 1  `secenekler.js ONIZLEME_KISITLAR` — "uretim motorunda karsiligi olmayan
         secim degerleri" beyani (urun id bazli).
  KOL 2  urun semasinin (`jenerator/urunler/<urun-id>.json`) `kisitlar` blogu —
         "bu parametre kutusunun HER noktasi uretilebilir DEGIL, sartli daraltma
         var" beyani (2026-08-03'te `rulman` semasina boyle bir blok girdi).

    KISITLI AILE KUMESI = KOL1 ∪ KOL2   (TEK kanonik kume)
    O kume ile HACIM_DOGRULANMIS_AILELER'in (yani SATISIN) KESISIMI BOS olmali.

🔴 2026-08-03 OLCULEN KOR NOKTA (bu turun sebebi): A3 kumeyi YALNIZ KOL1'den
turetiyordu. Kopyada `rulman` satis listesine eklendiginde kapi rc=0 veriyor, A3
"[OK]" basiyordu — semasinda kisit blogu tanimli bir aile satisa acilsa hicbir kapi
kirmizi yanmiyordu (ayni korluk `vida` icin de olculdu). Artik iki kol da AYNI sema
okuyucudan (`_sema_tara`) turer; ikinci bir yorumlayici kod yolu YOK
([[ikiz-tanim-sessiz-ayrisma]]).

🔴 FAIL-CLOSED (bugunku dersin sinifi = OLCULMEMIS SIFIRI YESIL SAYMAK): sema dizini
okunamiyorsa, bir sema bozuksa, `kisitlar` bicimi TANINMIYORSA ya da aile eslemesi
(`hacimFormulu`) kurulamiyorsa kume HESAPLANMAZ -> A1/A5/A6/A3 HIC BASILMAZ ve kosum
OLCULEMEDI (sifir-disi rc) ile kapanir. "Kisit yok" VARSAYILMAZ.

Yarin yeni bir kisit (hangi koldan olursa olsun) beyan edilirse o aile kendiliginden
satista KALAMAZ: bu kapi kirmizi yakar. Denylist degil, TURETILMIS kural —
bayatlayacak ikinci bir liste YOK.

OLCULEN IDDIALAR (her biri AYRI; hicbiri digerinin VEYA'si degil)
-----------------------------------------------------------------
  A1  ONIZLEME_KISITLAR'daki her urun id'si bir semaya + aileye cozuldu
  A1b OLCULEN uc ailenin (petek/cetvel/kase) kisit beyani HALA yerinde (capa bayat degil)
  A2* OLCULEN uc aile icin parametrikFiyatKurus(...) -> null    (aile basina 1 iddia)
  A6  SATISTAKI her ailenin semasi FIILEN tarandi — yani her acik ailenin `kisitlar`
      tasiyip tasimadigi olculdu. Bir acik ailenin semasi kaybolursa A3 sessizce
      "kisit gormedim" demez; A6 TEK BASINA kirmizi yanar (M10 mutanti).
  A3  kisitli aileler kumesi (KOL1 ∪ KOL2) ∩ HACIM_DOGRULANMIS_AILELER = ∅
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
kapatilmasi) sema/uretim duzlemidir. Bu kapi yalnizca SATIS ucunu ve MUSTERI METNINI
fail-closed tutar; sema onarilip kisit kalkinca aile kendiliginden geri acilir.
KOL2 icin bunun anlami: `kisitlar` blogu bir aileyi satistan ALIKOYAR, satisa ACMAZ.
Blok "bu ailenin parametre kutusu SARTLI" der; kutunun daraltilmis halinin tamamen
uretilebilir oldugu ayri bir olcumdur ve satisa acma karari MIMARINDIR. Sartli bir
aile bu kapiyla sessizce satisa DUSEMEZ.

KULLANIM
    python3 tools/onizleme-vaat-kapisi.py
    python3 tools/onizleme-vaat-kapisi.py --repo /gecici/ayna
    python3 tools/onizleme-vaat-kapisi.py --kendini-test

KIRMIZI-MUTASYON TURU (--kendini-test): mutasyon DAIMA KOPYAYA uygulanir; canli
agaca HICBIR yazma yapilmaz (secenekler.js + tools/build.py + sema dizininin
BIRLESIK ozeti bas/son basilir; ozet dosya adlarini da kapsar, silinen sema da
yakalanir). Uc mutant sinifi:
  OLDURUCU    beklenen iddia(lar) kirmizi, BASKA hicbir iddia kirmizi degil
              (fazla kirmizi = kapi hedefi disina tasiyor).
  KONTROL     gercek bir bozulma OLMAYAN degisiklik -> YESIL kalmali. Kalmazsa
              kapi asiri hevesli demektir; yanlis-pozitif TUM ekibin yayinini durdurur.
              Kontrol mutanti olmayan bir kirmizi KANIT DEGILDIR.
  FAIL-CLOSED kume hesaplanamaz -> A3 HIC BASILMAZ + en az 1 OLCULEMEDI + rc sifir-disi.
              Kabul olcutu cikis kodu DEGIL (bir COKUS de sifir-disi rc verirdi):
              basilan iddia sayisi + "A3 basilmadi" isaret sarti olculur; COKUS ayri
              yakalanir ve FAIL sayilir.
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

# Urun semalarinin dizini + KOL2'nin okudugu alan adi (tek yerde yazili).
SEMA_DIZINI = ("jenerator", "urunler")
KISIT_ALANI = "kisitlar"

# Kapinin OLCTUGU iddia sayisi bunun ALTINA dusemez. Eksen sessizce dusurulurse
# (ornegin bir iddia silinip kosum yine "yesil" yanarsa) --kendini-test kirmizi
# yakar: kabul olcutu cikis kodu DEGIL, basilan iddia sayisidir
# ([[hukum-yanlis-birimde]] · [[mutasyon-kaniti-yeniden-uretilebilir]]).
EN_AZ_IDDIA = 12

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


def _kisit_bloku_say(blok):
    """Semadaki `kisitlar` blogunu TEK yerde yorumlar.

    (kural_sayisi, bicim_hatasi) doner. bicim_hatasi bos degilse blok TANINMADI
    demektir ve cagiran taraf bunu OLCULEMEDI'ye cevirmek ZORUNDADIR — "tanimadim,
    demek ki kisit yok" fail-open'i tam olarak bu depoyu isiran desendir.

    Alan YOK  -> 0 kural (bildirim yok).
    Bos liste -> 0 kural (BEYAN EDILMIS "kisit yok"; bicim tanindi).
    """
    if blok is None:
        return 0, ""
    if not isinstance(blok, list):
        return 0, "`%s` bicimi TANINMADI: liste degil (%s)" % (
            KISIT_ALANI, type(blok).__name__)
    for i, oge in enumerate(blok):
        if not isinstance(oge, dict):
            return 0, "`%s`[%d] bicimi TANINMADI: nesne degil (%s)" % (
                KISIT_ALANI, i, type(oge).__name__)
        if not isinstance(oge.get("parametre"), str) or not oge.get("parametre"):
            return 0, "`%s`[%d] bicimi TANINMADI: `parametre` alani yok" % (KISIT_ALANI, i)
        if ("min" not in oge) and ("max" not in oge):
            return 0, "`%s`[%d] bicimi TANINMADI: ne `min` ne `max` var" % (KISIT_ALANI, i)
    return len(blok), ""


def _sema_tara(kok):
    """TEK KANONIK SEMA OKUYUCU — jenerator/urunler/*.json'un TAMAMI.

    (semalar, tanilar) doner:
      semalar {urun_id: {"aile": hacimFormulu, "kisit": kural_sayisi}}
      tanilar bos DEGILSE semalar None'dir -> cagiran OLCULEMEDI yazar.

    Hem KOL1 (ONIZLEME_KISITLAR id'sini aileye cozme) hem KOL2 (`kisitlar` blogu)
    BU tek okuyucudan beslenir; iki ayri yorumlayici kod yolu YOK.
    """
    dizin = os.path.join(kok, *SEMA_DIZINI)
    goreli = "/".join(SEMA_DIZINI)
    if not os.path.isdir(dizin):
        return None, ["sema dizini YOK: %s" % goreli]
    adlar = sorted(a for a in os.listdir(dizin) if a.endswith(".json"))
    if not adlar:
        return None, ["sema dizini BOS: %s" % goreli]
    semalar, tanilar = {}, []
    for ad in adlar:
        try:
            with open(os.path.join(dizin, ad), encoding="utf-8") as f:
                d = json.load(f)
        except (ValueError, OSError) as e:
            tanilar.append("%s okunamadi/bozuk: %s" % (ad, e))
            continue
        if not isinstance(d, dict):
            tanilar.append("%s kok nesne degil (%s)" % (ad, type(d).__name__))
            continue
        aile = d.get("hacimFormulu")
        if not isinstance(aile, str) or not aile:
            tanilar.append("%s aile eslemesi kurulamadi (hacimFormulu=%r)" % (ad, aile))
            continue
        sayi, bicim_hatasi = _kisit_bloku_say(d.get(KISIT_ALANI))
        if bicim_hatasi:
            tanilar.append("%s %s" % (ad, bicim_hatasi))
            continue
        semalar[ad[:-len(".json")]] = {"aile": aile, "kisit": sayi}
    if tanilar:
        return None, tanilar
    return semalar, []


def kisitli_aile_kumesi(semalar, kisit_urun_idleri):
    """KISITLI AILE KUMESI = KOL1 ∪ KOL2, tek yerde uretilir.

    (kaynaklar, eksik) doner:
      kaynaklar {aile: [gerekce, ...]}  — hangi kol(lar)dan geldigi yazili
      eksik     ONIZLEME_KISITLAR'da olup semaya cozulemeyen urun id'leri (A1)
    """
    kaynaklar, eksik = {}, []
    for uid in sorted(kisit_urun_idleri):                 # KOL 1
        s = semalar.get(uid)
        if s is None:
            eksik.append(uid + " (sema dosyasi yok/taranamadi)")
            continue
        kaynaklar.setdefault(s["aile"], []).append("ONIZLEME_KISITLAR:" + uid)
    for uid in sorted(semalar):                           # KOL 2
        s = semalar[uid]
        if s["kisit"] > 0:
            kaynaklar.setdefault(s["aile"], []).append(
                "sema.%s:%s(%d kural)" % (KISIT_ALANI, uid, s["kisit"]))
    return kaynaklar, eksik


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
def _bolum_a(kok, iddia, olculemedi):
    """SATIS KAPISI. Kume hesaplanamazsa HIC IDDIA BASMAZ (fail-closed)."""
    veri, hata = _node_olc(kok, [])
    if veri is None:
        olculemedi.append("BOLUM A: " + hata)
        return

    semalar, tanilar = _sema_tara(kok)
    if semalar is None:
        # 🔴 "Kisit yok" VARSAYILMAZ: kume hesaplanamadi -> A1/A5/A1b/A6/A3 BASILMAZ.
        olculemedi.append(
            "BOLUM A sema taramasi FAIL-CLOSED ('kisit yok' varsayilmadi, "
            "kisitli aile kumesi HESAPLANMADI): " + "; ".join(tanilar[:6])
            + (" (+%d tani daha)" % (len(tanilar) - 6) if len(tanilar) > 6 else ""))
        return

    kaynaklar, eksik = kisitli_aile_kumesi(semalar, veri["kisitlar"])
    iddia("A1 ONIZLEME_KISITLAR urun id'lerinin HEPSI semaya+aileye cozuldu",
          not eksik, "; ".join(eksik))
    kisitli_aileler = sorted(kaynaklar)

    iddia("A5 fikstur olu degil: en az bir kisitli aile var (KOL1 ∪ KOL2 = %d)"
          % len(kisitli_aileler),
          len(kisitli_aileler) > 0, "kisitli aile=%d" % len(kisitli_aileler))

    capa_aileleri = [a for a, _ in OLCULEN_AILELER]
    bayat = [a for a in capa_aileleri if a not in kisitli_aileler]
    iddia("A1b OLCULEN uc ailenin kisit beyani hala yerinde (A2 capasi bayat degil)",
          not bayat, "kisit beyani KALKMIS: %s" % bayat)

    acik = set(veri["acik"])
    # A6 KAPSAM: satistaki her ailenin semasi FIILEN tarandi mi? Taranmayan bir aile
    # icin "kisiti yok" DEMEK olculmemis sifiri yesil saymaktir.
    taranan_aileler = {s["aile"] for s in semalar.values()}
    kapsamsiz = sorted(a for a in acik if a not in taranan_aileler)
    iddia("A6 KAPSAM: SATISTAKI %d ailenin semasi tarandi (kisit ekseni kor degil)"
          % len(acik),
          not kapsamsiz,
          "semasi TARANMAMIS satistaki aile: %s (kisit tasiyip tasimadigi OLCULMEDI)"
          % kapsamsiz)

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
    iddia("A3 YAPISAL KURAL: kisitli aileler (KOL1 ∪ KOL2) ∩ satis listesi = ∅",
          not kesisim,
          "SATISTA KALMIS kisitli aile: %s"
          % [(a, kaynaklar[a]) for a in kesisim] if kesisim else "")


def olc(kok):
    """(iddialar, olculemedi) doner. iddialar: [(ad, ok, detay)]"""
    iddialar, olculemedi = [], []

    def iddia(ad, ok, detay=""):
        iddialar.append((ad, bool(ok), detay))

    _bolum_a(kok, iddia, olculemedi)

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
    """olc() icin yeterli minimal agac — HEPSI KOPYA.

    🔴 Semalar eskiden SYMLINK'ti; KOL2 geldikten sonra sema mutantlari (bozuk JSON,
    tanimsiz `kisitlar` bicimi, silinen sema) CANLI AGACA yazardi. Artik kopyalanir;
    kendini_test bunu sha256 ile fiilen olcer."""
    hedef = tempfile.mkdtemp(prefix="onizleme-vaat-ayna-")
    shutil.copy2(os.path.join(kok, "secenekler.js"), os.path.join(hedef, "secenekler.js"))
    os.makedirs(os.path.join(hedef, "tools"))
    shutil.copy2(os.path.join(kok, "tools", "build.py"),
                 os.path.join(hedef, "tools", "build.py"))
    shutil.copytree(os.path.join(kok, *SEMA_DIZINI), os.path.join(hedef, *SEMA_DIZINI))
    return hedef


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, s):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(s)


def _sema_yolu(ayna, urun_id):
    return os.path.join(ayna, SEMA_DIZINI[0], SEMA_DIZINI[1], urun_id + ".json")


def _degistir(yol, eski, yeni):
    """Capali metin degisimi — capa BULUNAMAZSA sessizce gecmez, PATLAR.
    (Uygulanmamis bir mutant 'oldurulemedi' degil, OLCULMEMIS demektir.)"""
    kaynak = _oku(yol)
    if eski not in kaynak:
        raise AssertionError("mutasyon capasi BULUNAMADI: %r" % (eski,))
    _yaz(yol, kaynak.replace(eski, yeni, 1))


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


def _m_rulman_satisa(ayna):
    """🔴 KOL2 OLDURUCUSU (2026-08-03 olculen kor nokta): semasinda `kisitlar` blogu
    OLAN bir aile satis listesine eklenir. `rulman` ONIZLEME_KISITLAR'da HIC gecmez —
    yani bu mutanti YALNIZ sema kolu yakalayabilir. Eski kapi bunda rc=0 + A3 [OK]
    veriyordu."""
    _degistir(os.path.join(ayna, "secenekler.js"),
              "oring: 0.39, pervane: 0.38",
              "oring: 0.39, pervane: 0.38, rulman: 0.08")
    return ["A3"]


def _m_vida_satisa(ayna):
    """KOL2 OLDURUCUSU — IKINCI sema-kisitli aile (tek fikstur ailesine capalanmis
    bir kural, kume degil bir ISIM oluyordu; ikinci aile bunu ayirt eder)."""
    _degistir(os.path.join(ayna, "secenekler.js"),
              "oring: 0.39, pervane: 0.38",
              "oring: 0.39, pervane: 0.38, vida: 0.10")
    return ["A3"]


def _m_acik_aile_semasi_silindi(ayna):
    """KAPSAM OLDURUCUSU: SATISTAKI bir ailenin (toka) sema dosyasi silinir.
    Artik o ailenin kisit tasiyip tasimadigi OLCULEMEZ; kume sessizce kuculur.
    A6 TEK BASINA kirmizi yanmali — "gormedim = yok" fail-open'i burada kapanir."""
    os.unlink(_sema_yolu(ayna, "olcuye-ozel-toka"))
    return ["A6"]


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


def _k_kisitsiz_aile_satisa(ayna):
    """🔴 KOL2'nin AYIRT EDICI KONTROLU: semasinda `kisitlar` OLMAYAN ve
    ONIZLEME_KISITLAR'da gecmeyen KAPALI bir aile (rampa) satis listesine eklenir.
    Bu kapi YESIL kalmali. Kalmazsa kural "kisitli aile satilamaz" degil "kapali aile
    acilamaz" olurdu — yanlis-pozitif tum ekibin yayinini durdurur. (rampa'nin kapali
    olmasi HACIM ekseninin karari; bu kapinin olctugu eksen DEGIL.)"""
    _degistir(os.path.join(ayna, "secenekler.js"),
              "oring: 0.39, pervane: 0.38",
              "oring: 0.39, pervane: 0.38, rampa: 0.50")
    return []


def _k_bos_kisit_blogu(ayna):
    """KOL2 KONTROLU: SATISTAKI bir ailenin semasina BOS `kisitlar: []` eklenir.
    Bicim TANINIR, kural sayisi 0 -> kume DEGISMEZ, kapi YESIL kalmali. Kural alanin
    VARLIGINA degil, ICINDEKI KURAL SAYISINA bakiyor."""
    yol = _sema_yolu(ayna, "olcuye-ozel-toka")
    d = json.loads(_oku(yol))
    d[KISIT_ALANI] = []
    _yaz(yol, json.dumps(d, ensure_ascii=False, indent=2))
    return []


# --- FAIL-CLOSED mutantlari: kume HESAPLANAMAZ -> OLCULEMEDI + A3 HIC BASILMAZ.
#     Kabul olcutu cikis kodu DEGIL: "A3 yok + en az 1 OLCULEMEDI" isaret sarti,
#     cunku bir COKUS de sifir-disi rc verir ve kirmiziyla karisirdi.
def _f_sema_bozuk_json(ayna):
    """Bir sema dosyasi BOZUK JSON olur -> `kisitlar` okunamaz."""
    _yaz(_sema_yolu(ayna, "olcuye-ozel-rulman"), '{"id": "olcuye-ozel-rulman", ')
    return []


def _f_kisit_bicimi_nesne(ayna):
    """`kisitlar` liste yerine NESNE (bicim TANINMAZ)."""
    yol = _sema_yolu(ayna, "olcuye-ozel-rulman")
    d = json.loads(_oku(yol))
    d[KISIT_ALANI] = {"eleman": "makara"}
    _yaz(yol, json.dumps(d, ensure_ascii=False, indent=2))
    return []


def _f_kisit_ogesi_taninmaz(ayna):
    """`kisitlar` listesi ama oge sozlesmeye uymuyor (parametre/min/max yok) ->
    kural sayilamaz. Sessizce 0 sayilsaydi aile kisitsiz gorunurdu."""
    yol = _sema_yolu(ayna, "olcuye-ozel-rulman")
    d = json.loads(_oku(yol))
    d[KISIT_ALANI] = [{"eger": {"eleman": "makara"}, "mesaj": "..."}]
    _yaz(yol, json.dumps(d, ensure_ascii=False, indent=2))
    return []


def _f_sema_dizini_yok(ayna):
    """Sema dizininin TAMAMI yok -> kume hic hesaplanamaz."""
    shutil.rmtree(os.path.join(ayna, *SEMA_DIZINI))
    return []


OLDURUCU, KONTROL, FAIL_CLOSED = "oldurucu", "kontrol", "fail-closed"

MUTANTLAR = [
    ("M1 eski YALAN vaat metni geri geldi", _m_vaat_geri, OLDURUCU),
    ("M2 kapatilan aile (petek) satis listesine geri eklendi", _m_petek_geri, OLDURUCU),
    ("M3 parametrikFiyatKurus fail-closed `return null` kolu olduruldu", _m_null_kaldir, OLDURUCU),
    ("M4 YENI kisit beyan edildi ama aile satista birakildi", _m_yeni_kisit, OLDURUCU),
    ("M5 satis listesi tumuyle bosaltildi (her seye null)", _m_liste_bosalt, OLDURUCU),
    ("M6 hata tablosu girisi silindi (capa kaydi)", _m_tablo_sil, OLDURUCU),
    ("M7 iki cagri yerinin metni ayristirildi", _m_tek_yer_ayrisir, OLDURUCU),
    ("M8 SEMA-kisitli aile (rulman) satisa acildi", _m_rulman_satisa, OLDURUCU),
    ("M9 SEMA-kisitli ikinci aile (vida) satisa acildi", _m_vida_satisa, OLDURUCU),
    ("M10 SATISTAKI bir ailenin semasi silindi (kapsam kaydi)",
     _m_acik_aile_semasi_silindi, OLDURUCU),
    ("K1 KONTROL: anlamsiz yorum eklendi", _k_yorum, KONTROL),
    ("K2 KONTROL: acik ailenin sapma SAYISI degisti", _k_sapma_degeri, KONTROL),
    ("K3 KONTROL: satis listesi anahtar SIRASI degisti", _k_sira, KONTROL),
    ("K4 KONTROL: KISITSIZ kapali aile (rampa) satisa acildi",
     _k_kisitsiz_aile_satisa, KONTROL),
    ("K5 KONTROL: satistaki semaya BOS `kisitlar: []` eklendi",
     _k_bos_kisit_blogu, KONTROL),
    ("F1 FAIL-CLOSED: sema dosyasi BOZUK JSON", _f_sema_bozuk_json, FAIL_CLOSED),
    ("F2 FAIL-CLOSED: `kisitlar` liste degil (bicim taninmaz)",
     _f_kisit_bicimi_nesne, FAIL_CLOSED),
    ("F3 FAIL-CLOSED: `kisitlar` ogesi sozlesmeye uymuyor",
     _f_kisit_ogesi_taninmaz, FAIL_CLOSED),
    ("F4 FAIL-CLOSED: sema dizini tumuyle YOK", _f_sema_dizini_yok, FAIL_CLOSED),
]


def _izlenen_ozetler(kok):
    """Canli agacta mutasyonun ASLA dokunmamasi gereken girdiler.
    Sema dizini TEK BIR birlesik ozetle izlenir: ozet dosya ADLARINI da kapsar,
    yani silinen/eklenen bir sema da ozeti degistirir."""
    ozet = {"secenekler.js": _sha256(os.path.join(kok, "secenekler.js")),
            "tools/build.py": _sha256(os.path.join(kok, "tools", "build.py"))}
    dizin = os.path.join(kok, *SEMA_DIZINI)
    h, n = hashlib.sha256(), 0
    for ad in sorted(os.listdir(dizin)) if os.path.isdir(dizin) else []:
        h.update(ad.encode("utf-8"))
        h.update(_sha256(os.path.join(dizin, ad)).encode("ascii"))
        n += 1
    ozet["%s/ (%d dosya, birlesik ozet)" % ("/".join(SEMA_DIZINI), n)] = h.hexdigest()
    return ozet


def kendini_test(kok):
    bas_ozet = _izlenen_ozetler(kok)
    print("SHA256 BASTA:")
    for ad in bas_ozet:
        print("  %s  %s" % (bas_ozet[ad], ad))

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
    # KABUL OLCUTU = BASILAN IDDIA SAYISI (cikis kodu degil): bir eksen sessizce
    # dusurulurse kosum yine "0 kirmizi" verirdi.
    if taban_iddia < EN_AZ_IDDIA:
        basarisiz.append("IDDIA SAYISI DUSTU: %d < EN_AZ_IDDIA=%d (eksen kaybi)"
                         % (taban_iddia, EN_AZ_IDDIA))

    print("\nMUTANTLAR (olcut TABANLA AYNI fonksiyon):")
    for ad, uygula, tur in MUTANTLAR:
        ayna = _ayna(kok)
        try:
            beklenen = uygula(ayna)
            try:
                iddialar, olculemedi = olc(ayna)
            except Exception as e:  # COKUS != KIRMIZI ([[mutasyon-kaniti-...]])
                print("  [FAIL] %-58s COKTU: %s: %s" % (ad, type(e).__name__, e))
                basarisiz.append(ad + " (COKTU)")
                continue
            kirmizilar = [a for a, ok, _ in iddialar if not ok]
            # OLCUT ESITLIGI: mutant, tabanla AYNI sayida iddia uretmeli; uretmiyorsa
            # karsilastirma baska birimde yapiliyor demektir ([[hukum-yanlis-birimde]]).
            olcut_esit = (len(iddialar) == taban_iddia)
            if tur == KONTROL:
                ok = (not kirmizilar) and (not olculemedi) and olcut_esit
                durum = "YESIL kaldi" if not kirmizilar else ("KIRMIZI: %s" % kirmizilar)
            elif tur == FAIL_CLOSED:
                # ISARET SARTI: A3 HIC BASILMAMALI (yani "kisit yok" HUKMU verilmemis)
                # + en az bir OLCULEMEDI + main()'in rc formulu sifir-disi.
                a3_basildi = any(a.startswith("A3") for a, _, _ in iddialar)
                rc = 1 if (kirmizilar or olculemedi) else 0
                ok = (not a3_basildi) and len(olculemedi) >= 1 and rc == 1
                durum = "A3 basildi mi=%s  OLCULEMEDI=%d  rc=%d  iddia=%d" % (
                    a3_basildi, len(olculemedi), rc, len(iddialar))
            else:
                # her beklenen onek fiilen kirmizi mi + BEKLENMEYEN kirmizi var mi
                eslesen = [b for b in beklenen
                           if any(k.startswith(b) for k in kirmizilar)]
                fazla = [k for k in kirmizilar
                         if not any(k.startswith(b) for b in beklenen)]
                ok = (len(eslesen) == len(beklenen)) and not fazla
                durum = "kirmizi=%s (beklenen onek=%s%s)" % (
                    kirmizilar, beklenen, "; FAZLA=%s" % fazla if fazla else "")
                # M6 capayi kaydirdigi icin olculemedi URETIR — BEKLENEN, kirmizi degil.
                if ad.startswith("M6"):
                    ok = ok and len(olculemedi) >= 1
                elif olculemedi:
                    ok = False
                    durum += "; BEKLENMEYEN OLCULEMEDI=%s" % olculemedi
            print("  [%s] %-58s %s%s" % ("PASS" if ok else "FAIL", ad, durum,
                                         "" if (olcut_esit or tur == FAIL_CLOSED)
                                         else "  [OLCUT KAYDI]"))
            if not ok:
                basarisiz.append(ad)
        finally:
            shutil.rmtree(ayna, ignore_errors=True)

    print("\nSHA256 SONDA (canli agaca yazma OLMAMALI):")
    son_ozet = _izlenen_ozetler(kok)
    tutuyor = (son_ozet == bas_ozet)
    for ad in son_ozet:
        print("  %s  %s%s" % (son_ozet[ad], ad,
                              "" if bas_ozet.get(ad) == son_ozet[ad] else "   🔴 DEGISTI"))
    if not tutuyor:
        basarisiz.append("CANLI AGAC DEGISTI (mutasyon kopyaya uygulanmadi)")

    print("\nTABAN IDDIA=%d (en az %d)  MUTANT=%d (oldurucu=%d, kontrol=%d, fail-closed=%d)" %
          (taban_iddia, EN_AZ_IDDIA, len(MUTANTLAR),
           sum(1 for _, _, t in MUTANTLAR if t == OLDURUCU),
           sum(1 for _, _, t in MUTANTLAR if t == KONTROL),
           sum(1 for _, _, t in MUTANTLAR if t == FAIL_CLOSED)))
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

# -*- coding: utf-8 -*-
"""PRUVO filament referansi ORTAK yardimcilari — tek kaynak: tools/filamentler.json.

Kullananlar: tools/build.py (urun sayfasi cipleri + /filament-veri.js), tools/sayfalar.py
(/malzeme-rehberi/), ekleme scriptleri (urun-ekle.py / printables-ekle.py: sanitize edilmis
tavsiyeFilament override'i) ve tools/ege-malzeme.py (ege-bilgi.md MALZEME bolumu).

MIMARI ILKE: filament bilgisi URUN VERISINE YAZILMAZ — kural render aninda kategoriden
turetilir. Tek istisna, YENI urunlerde ekleme scriptinin koyabildigi opsiyonel
"tavsiyeFilament" override alani (mevcut urunlerde tek tek tools/duzelt.py).
"""
import json
import os
import re
import warnings

import arama

_YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filamentler.json")
_ref = None


def referans():
    """filamentler.json'u okur (surec basina bir kez)."""
    global _ref
    if _ref is None:
        with open(_YOL, encoding="utf-8") as f:
            _ref = json.load(f)
    return _ref


# GECMIS: katalogda 2 urunde kategori "Bahce" (ç'siz) yaziyordu (kaynak: AI icerik adiminin
# ASCII kategori listesi). Veri duzeltildi ve kaynak kapatildi (thing-codex.py normalize eder,
# tools/kategori-kapisi.py dogrular) — burasi yalnizca OKUMA tarafinda geriye donuk toleranstir;
# yeni ASCII kategori beklenmiyor, urun verisine dokunulmaz.
_KATEGORI_ALIAS = {"Bahce": "Bahçe"}


def tavsiyeler(kategori, override=None):
    """Urunun tavsiye listesi: [{"ad": <kanonik ad>, "rozet": <rozet metni>}, ...].

    override (urunler.json'daki opsiyonel "tavsiyeFilament") varsa harita yerine O gecer;
    referans disindaki adlar sessizce atilir. Haritada ilk kayit varsayilan tavsiyedir
    ("Tavsiyemiz"); sonrakiler kosul notuyla ("Güneş gören parçada" vb.) rozetlenir.
    SADECE SITEDE SATILAN ("site": true) malzemeler tavsiye edilir — Karbon Katkılı
    mühendislik malzemesi olup WhatsApp özel talebiyle satılır, rozetle "Tavsiyemiz"
    diye SUNULMAZ. (ABS 14 Ağu'da satışa açıldı; kategori süzgeci ROZET ekseninde değil,
    ON-SECIM/CIP ekseninde uygulanır — bkz. build.py malzeme_kategori_uygun_mu.)
    """
    ref = referans()
    site_adlar = {f["ad"] for f in ref["filamentler"] if f.get("site")}
    if override:
        # 🔴 BICIMI TANINMAYAN ALAN -> ONERI TURETILEMEZ (fail-closed, ikiz tanim).
        # Alan LISTE olmak zorundadir. Katalogda alan bir donem DIZE ("PETG") tasidi;
        # o durumda hem burasi hem istemci (secenekler.js onSecimMalzeme) KARAKTER
        # KARAKTER geziyor ve tesadufen bos liste uretiyordu — dogru sonuc, YANLIS
        # sebep. Sozluk gibi baska bir tur gelseydi Python ANAHTARLARI gezip "PETG"
        # bulur, JS ise `length` goremeyip guvenli varsayilana duserdi: iki dil
        # sessizce ayrisirdi. Bos liste donmek kategori haritasina DUSMEK DEGILDIR
        # (dusulseydi alani bozuk urun sessizce %30 zamlanirdi).
        sebep = arama.katalog_alan_tip_sebebi(arama.TAVSIYE_FILAMENT_ALAN, override)
        if sebep is not None:
            warnings.warn("KATALOG TIP UYARISI: %s" % sebep, RuntimeWarning,
                          stacklevel=2)
            return []
        return [{"ad": a, "rozet": "Tavsiyemiz"} for a in override if a in site_adlar]
    kategori = _KATEGORI_ALIAS.get(kategori, kategori)
    out = []
    for t in ref["kategoriTavsiye"].get(kategori, []):
        if t["ad"] not in site_adlar:
            continue
        out.append({"ad": t["ad"],
                    "rozet": "Tavsiyemiz" if not out else (t.get("not") or "Tavsiyemiz")})
    return out


# ---------------------------------------------------------------- TANI JETONLARI
# Kuralin hangi koldan ciktigini adlandirir. Fiyati DEGISTIRMEZ; SESSIZ DUSUSU gorunur
# kilar. Ikiz tanim: secenekler.js icindeki ayni adli jetonlarla BIREBIR ayni dizeler
# (ayrisma tools/onsecim-parite-kapisi.py eksen 1'de fail-closed kirmizi yakar).
#
# 🔴 NEDEN VAR (olculdu 11 Agu): `tavsiyeFilament` alani DOLU ama icindeki adlarin
# hicbiri sitede satilan malzeme degilse (ornek: "TPU (esnek)", "ABS") kural guvenli
# varsayilana duser ve urun rozetsiz + tabanda kalir. Bu bir VERI KUSURUDUR ve bugune
# kadar "onerisi olmayan urun" ile AYNI cikti verdigi icin sayilamiyordu. Iki hal artik
# AYRI jetondur -> kac urunun bu duruma dustugu kapida BASILIR.
TANI_KAPALI = "kapali"
TANI_KAPSAM_DISI = "kapsam-disi"      # olcuye ozel / yapilandiricili / hazir ticari mal
TANI_ONERI = "oneri"
TANI_VARSAYILAN = "varsayilan"
TANI_TANINMAYAN = "taninmayan"


def on_secim_tani(kategori, override, katsayi_adlari, guvenli, acik=True):
    """(tani, malzeme) — on-secimin SONUCU ve hangi koldan geldigi.

    tani:
      kapali      kural bu yuzeyde kapali
      oneri       gecerli bir oneri bulundu, o ad on-secildi
      varsayilan  urun oneri TASIMIYOR (ve kategori haritasi da aday vermedi) -> guvenli
      taninmayan  urun oneri TASIYOR ama hicbir adi ayakta kalmadi (bicim bozuk ya da
                  adlar sitede satilmiyor) -> guvenli, AMA sessiz degil: sayilabilir.
    """
    if not acik:
        return (TANI_KAPALI, guvenli)
    onerili = bool(override)
    adaylar = [t["ad"] for t in tavsiyeler(kategori, override)]
    for ad in adaylar:
        if ad in katsayi_adlari:
            return (TANI_ONERI, ad)
    return ((TANI_TANINMAYAN if onerili else TANI_VARSAYILAN), guvenli)


def on_secim(kategori, override, katsayi_adlari, guvenli, acik=True):
    """Urunun ON-SECILI malzemesi (sayfa ureteci tarafi).

    KURAL tavsiye rozetiyle AYNI SIRADAN turer (tavsiyeler): override varsa harita
    yerine o gecer, sitede satilmayan ad elenir, kalan ILK ad tavsiyedir. Burada
    ek olarak ad KATSAYI TABLOSUNDA da bulunmalidir — bulunmayan bir ad on-secilseydi
    ilan edilen tutar ile sepete yazilan tutar sessizce ayrisirdi.

    acik=False -> guvenli (bugunku davranis birebir). FAIL-CLOSED: aday yoksa guvenli.

    🔴 IKIZ TANIM UYARISI: ayni kural istemci tarafinda da vardir (secenekler.js
    onSecimMalzeme). Iki taraf tam katalog uzerinde karsilastirilir; ayrisma
    fail-closed kirmizi yakar (tools/onsecim-parite-kapisi.py eksen 1).
    """
    return on_secim_tani(kategori, override, katsayi_adlari, guvenli, acik=acik)[1]


# ------------------------------------------------------------- baski -> override sanitize
# Kaynak aciklamasindan gelen `baski` ipucundan SADECE kanonik malzeme adi cikarilir;
# serbest metin, tasarimci adi ya da kaynak izi URUNE TASINMAZ (gizlilik kurali).
_MALZEME_PAT = [
    ("PETG", re.compile(r"\bPETG\b|\bPCTG\b", re.I)),
    ("ASA", re.compile(r"\bASA\b", re.I)),
    ("ABS", re.compile(r"\bABS\b", re.I)),
    ("PLA", re.compile(r"\bPLA\b|\bPLA\+", re.I)),
    ("Karbon Katkılı",
     re.compile(r"(carbon|karbon)[\s-]*(fiber|fibre|fibr|elyaf|katk)|"
                r"\b(PETG|PA|PLA)[\s-]?CF\b", re.I)),
]
# Olumsuz cumlecik: icindeki malzeme anilmalari TAVSIYE DEGILDIR ("PLA is not suitable...").
_OLUMSUZ = re.compile(r"\bnot\b|\bno\b|\bavoid\b|\bnever\b|don'?t|do not|isn'?t|won'?t|"
                      r"instead of|de[gğ]il|[oö]nerilmez|kullanmay|uygun olma|olmaz|yerine",
                      re.I)


def tavsiye_filament(baski_metni):
    """`.urun-kaynaklari.json` `baski` ipucundan sanitize tavsiyeFilament listesi.

    Cumleciklere bolup olumsuz baglamdakileri eler, kalanlarda kanonik malzeme adi arar.
    Ornek: "PLA is not a suitable material; I recommend PETG." -> ["PETG"].
    Kanonik ad bulunamazsa None (override yazilmaz, kategori haritasi gecerli kalir).
    SADECE SITEDE SATILAN malzemeler override olarak yazilir — kaynak metni "karbon" dese
    bile (mühendislik malzemesi, WhatsApp özel talebi; site secilebilir degil) o ad DUSER.
    ABS 14 Ağu'dan beri satilir, yani override olarak YAZILABILIR; ama harıc kategoride
    (Ev/Ofis/Dekorasyon/Skan Art/Oyun-Hobi) on-secim suzgeci onu ELER ve tani "taninmayan"
    olur — o kategorilerde alani hic yazmamak dogrusudur.
    """
    if not baski_metni:
        return None
    site_adlar = {f["ad"] for f in referans()["filamentler"] if f.get("site")}
    bulunan = []
    for parca in re.split(r"[.;!?\n]+", baski_metni):
        if _OLUMSUZ.search(parca):
            continue
        for ad, pat in _MALZEME_PAT:
            if ad in site_adlar and ad not in bulunan and pat.search(parca):
                bulunan.append(ad)
    return bulunan or None


if __name__ == "__main__":
    ornek = ("PLA is not a suitable material since cars reach high temperatures; "
             "I personally recommend using PETG. Print with 20% infill.")
    print(tavsiye_filament(ornek))                  # ['PETG']
    print(tavsiyeler("Otomobil"))                   # PETG (Tavsiyemiz) + ASA (not)
    print(tavsiyeler("Ev", override=["ASA"]))       # override kazanir

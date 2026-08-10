#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""markaKatla / markaNorm / taninmisMarkaMi PORTU (Python) — index.html'deki
MARKA KÜRATÖRLÜĞÜ bloğunun BİREBİR karşılığı.

TEK KAYNAK: TANINMIS_MARKALAR listesi index.html'den PARSE edilir (kopya tutulmaz).
Panel/CSV/kapsama raporu satır evrenini ham defter anahtarları yerine bu kanonik
listeden alır; ham defterdeki tüm anahtarların sayımları markaKatla ile kanonik
markaya katlanır (tanınmayan çöp anahtar hiç görünmez).

🔴 "BİREBİR" PROSE DEĞİL, ÇALIŞTIRILABİLİR KAPIYLA KANITLANIR. Bu dosya 10 Ağu 2026'ya
kadar docstring'inde "birebir" yazıyordu ve DEĞİLDİ (aksan kolu elle listeydi, site
6 Ağu'da NFD genel kuralına geçmişti; MARKA_ALIAS hiç yoktu) — kimse fark etmedi çünkü
sessizdi ([[ikiz-tanim-sessiz-ayrisma]]). İddianın nöbetçisi artık:
    python3 tools/marka-katla-ikiz-kapisi.py     (site gövdesini KOŞUM ANINDA node ile
                                                 çalıştırıp DAVRANIŞ karşılaştırır)
    python3 tools/marka-katla-ikiz-mutasyon-test.py  (o kapının gerçekten ölçtüğünün kanıtı)
Senkron tutulan iki eksen: markaNorm gövdesi (aksan GENEL KURALI + ayıraç kanonu) ve
markaKatla (kanonik/önek eşleşmesi + SONRASINDA marka-düzeyi ALIAS). İkisi de elle
KOPYALANMAZ: TANINMIS_MARKALAR ve MARKA_ALIAS index.html'den PARSE edilir, aksan kolu
ise iki dilde AYNI genel algoritmadır (NFD + birleşen-işaret silme).
"""
import os
import re
import unicodedata

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
INDEX = os.path.join(ROOT, "index.html")


def _norm(s):
    """index.html norm(): Türkçe-duyarlı küçültme + aksan sadeleştirme."""
    s = (s or "").lower()
    # Türkçe locale lowercase: İ ve I ele; norm() önce toLocaleLowerCase("tr") yapıyor.
    # Python lower() İ -> i̇ (combining) üretebilir; site ile birebir olması için elle eşle.
    s = (s.replace("ı", "i").replace("İ", "i")
          .replace("ç", "c").replace("ğ", "g").replace("ö", "o")
          .replace("ş", "s").replace("ü", "u").replace("â", "a").replace("î", "i"))
    return s


# 🔴 AKSAN GENEL KURALLA ÇÖZÜLÜR — index.html markaNorm (6 Ağu, mimar hükmü H4) ile AYNI
# ALGORİTMA, elle liste DEĞİL: `norm(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "")`.
# Eskiden burada elle bir liste vardı (`é/è/ë/ä`) ve caron ("Škoda"), tilde ("Señor"),
# halka ("Åkerman"), akut, macron, breve taşıyan HİÇBİR yazımı görmüyordu — yani site ile
# AYRI bir aksan tanımıydı ([[ikiz-tanim-sessiz-ayrisma]]). Genel kural yazıldığı için
# ileride SİTEYE yeni bir aksan gelse de port kendiliğinden doğru davranır (elle port
# olsaydı yine bayatlardı). Yan kazanç: Python `.lower()` "İ"yi `i + U+0307` üretir; o
# birleşen nokta da burada düşer, yani site `toLocaleLowerCase("tr")` ile hizalanır.
_BIRLESEN_ISARET = re.compile("[\\u0300-\\u036f]")


def _aksan_sil(n):
    return _BIRLESEN_ISARET.sub("", unicodedata.normalize("NFD", n))


def markaNorm(s):
    """norm() + Latin aksan ("Citroën"->"citroen") + marka ayıraç birleştirme.
    "+", "&", " and " tek biçime indirgenir -> "Black+Decker" == "Black and Decker"."""
    n = _norm(s)
    n = _aksan_sil(n)
    # marka ayıraç kanonikleştirme (site markaNorm ile birebir tutulur):
    n = n.replace(" and ", " ").replace("&", " ").replace("+", " ")
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _parse_taninmis(index_path=INDEX):
    """index.html'den TANINMIS_MARKALAR dizisini PARSE et (tek kaynak)."""
    src = open(index_path, encoding="utf-8").read()
    m = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", src, re.S)
    if not m:
        raise RuntimeError("TANINMIS_MARKALAR index.html'de bulunamadı")
    body = m.group(1)
    # yorum satırlarını (// ...) at, sonra tırnaklı stringleri topla
    body = re.sub(r"//[^\n]*", "", body)
    return re.findall(r'"([^"]+)"', body)


def _parse_alias(index_path=INDEX):
    """index.html'den MARKA_ALIAS sözlüğünü PARSE et (tek kaynak — ELLE YAZILMAZ).
    Aynı markanın iki adı ("Vauxhall" = Opel'in İngiltere adı) TEK kaleme iner.
    Elle bir kopya tutulsaydı site tablosu büyüdüğünde port SESSİZCE bayatlardı —
    bu dosyanın 10 Ağu'da kapatılan kusuru tam olarak buydu."""
    src = open(index_path, encoding="utf-8").read()
    m = re.search(r"var MARKA_ALIAS = \{(.*?)\};", src, re.S)
    if not m:
        raise RuntimeError("MARKA_ALIAS index.html'de bulunamadı")
    body = re.sub(r"//[^\n]*", "", m.group(1))
    return dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', body))


TANINMIS_MARKALAR = _parse_taninmis()
MARKA_ALIAS = _parse_alias()
MARKA_KANONIK = {}
for _m in TANINMIS_MARKALAR:
    MARKA_KANONIK[markaNorm(_m)] = _m
MARKA_NORMLU = [markaNorm(m) for m in TANINMIS_MARKALAR]


def _katla_alias_oncesi(m):
    """Değer tanınmış markanın kendisiyse ya da boşluk/tire ile önekliyse o markanın
    kanonik adına katlanır; değilse OLDUĞU GİBİ döner. ALIAS BURADA UYGULANMAZ —
    site markaKatla'da da alias kanonik/önek eşleşmesinden SONRA gelir, sıra
    ANLAMLIDIR ("Vauxhall Astra" önce Vauxhall'a katlanır, sonra Opel'e iner)."""
    n = markaNorm(m)
    if n in MARKA_KANONIK:
        return MARKA_KANONIK[n]
    for i, nm in enumerate(MARKA_NORMLU):
        if n.startswith(nm + " ") or n.startswith(nm + "-"):
            return TANINMIS_MARKALAR[i]
    return m


def markaKatla(m):
    """site markaKatla birebir: kanonik/önek katlaması + SONRASINDA marka-düzeyi ALIAS."""
    sonuc = _katla_alias_oncesi(m)
    if sonuc in MARKA_ALIAS:
        sonuc = MARKA_ALIAS[sonuc]
    return sonuc


def taninmisMarkaMi(m):
    return markaNorm(m) in MARKA_KANONIK


def kanonik_veya_none(m):
    """markaKatla tanınmış bir markaya katladıysa kanonik adı, katlamadıysa None."""
    k = markaKatla(m)
    return k if taninmisMarkaMi(k) else None


# ---- PANEL/CSV/RAPOR ortak katmanı (satır evreni = TANINMIS_MARKALAR) ----------
# 🔴 TEK KANONIK PLATFORM TANIMI. Panel (parity-panel.py), CSV (parity-csv.py) ve defter
# yazıcısı (marka-kapsama.py) platform listelerini ELLE TUTMAZ, hepsi buradan TÜRETİR.
# Gerekçe: elle tutulan ikiz listeler sessizce ayrışır ([[ikiz-tanim-sessiz-ayrisma]]) —
# panel kolonu ile başlık satırı, ya da sunucu-tarafı durum ile istemci-tarafı renk
# birbirini tutmaz ve hüküm yanlış birimde verilir. Sıra ANLAMLIDIR: panel/CSV kolon
# sırası buradan gelir; YENİ PLATFORM SONA EKLENİR (mevcut kolonların kimliği korunur).
# Alanlar: (defter anahtarı, panel/CSV'de görünen kısa ad, link domaini)
PLATFORM_TANIMI = (
    ("Printables",  "Printables",  "printables.com"),
    ("Thingiverse", "Thingiverse", "thingiverse.com"),
    ("MakerWorld",  "MakerWorld",  "makerworld.com"),
    ("Cults3D",     "Cults3D",     "cults3d.com"),
    ("CGTrader",    "CGTrader",    "cgtrader.com"),
)
PLATFORMLAR = [a for a, _k, _d in PLATFORM_TANIMI]
PLATFORM_KISA = [k for _a, k, _d in PLATFORM_TANIMI]
PLATFORM_DOMAIN = {d: a for a, _k, d in PLATFORM_TANIMI}
AZ_ORAN = 0.5   # markanın en dolu platformunun bu oranının altı = "az kalmış" (sarı)
AZ_MIN = 10     # en dolu platform bu sayıdan azsa orantıya bakma (küçük markada gürültü)


def _platform_tanimi_dogrula():
    """FAIL-CLOSED: türetilen listeler ayrışırsa import ANINDA patla (sessiz kalma).
    Ayrışma tek yolla olur: birileri PLATFORM_TANIMI yerine türev listelerden birini
    elle düzenler. O anda modül YÜKLENMEZ -> panel/CSV/test hepsi kırmızı yanar."""
    n = len(PLATFORM_TANIMI)
    if not (len(PLATFORMLAR) == len(PLATFORM_KISA) == n):
        raise RuntimeError("PLATFORM ikiz ayrışması: uzunluklar %d/%d/%d"
                           % (len(PLATFORMLAR), len(PLATFORM_KISA), n))
    if len(set(PLATFORMLAR)) != n or len(set(PLATFORM_KISA)) != n:
        raise RuntimeError("PLATFORM tanımında MÜKERRER anahtar/kısa ad")
    if len(PLATFORM_DOMAIN) != n:
        raise RuntimeError("PLATFORM tanımında MÜKERRER domain")
    for i, (a, k, d) in enumerate(PLATFORM_TANIMI):
        if PLATFORMLAR[i] != a or PLATFORM_KISA[i] != k:
            raise RuntimeError("PLATFORM türevi tanımdan SAPMIŞ (index %d)" % i)
        if not (a and k and d) or "." not in d:
            raise RuntimeError("PLATFORM tanımı eksik/bozuk (index %d)" % i)


_platform_tanimi_dogrula()


def kanonik_kapsama(defter):
    """Ham defter (anahtar -> platform -> kayıt) -> kanonik marka -> platform -> BİRLEŞİK kayıt.
    Satır evreni TANINMIS_MARKALAR: defteri olmayan tanınmış marka da BOŞ girer (to-do çıkar).
    markaKatla ile hiçbir tanınmış markaya katlanmayan çöp anahtar HİÇ görünmez.
    Birleştirme: taranan=max, eklenen/elenen/parti=sum, son_tarih=en yeni."""
    agg = {m: {} for m in TANINMIS_MARKALAR}
    for ham, plats in (defter or {}).items():
        kan = kanonik_veya_none(ham)
        if kan is None:
            continue
        agg.setdefault(kan, {})
        if not isinstance(plats, dict):
            continue
        for p, k in plats.items():
            if not isinstance(k, dict):
                continue
            cur = agg[kan].setdefault(p, {"taranan": 0, "eklenen": 0, "elenen": 0,
                                          "parti": 0, "son_tarih": None})
            cur["taranan"] = max(cur["taranan"], int(k.get("taranan", 0) or 0))
            cur["eklenen"] += int(k.get("eklenen", 0) or 0)
            cur["elenen"] += int(k.get("elenen", 0) or 0)
            cur["parti"] += int(k.get("parti", 0) or 0)
            st = k.get("son_tarih")
            if st and (cur["son_tarih"] is None or str(st) > str(cur["son_tarih"])):
                cur["son_tarih"] = st
    return agg


def hucre_deger(kayit):
    """Panel hücre değeri: eklenen>0 -> eklenen | taranan>0 -> 0 (arandı-boş) | yoksa None."""
    if not kayit:
        return None
    if kayit.get("eklenen", 0) > 0:
        return kayit["eklenen"]
    if kayit.get("taranan", 0) > 0:
        return 0
    return None


def durum_hucreler(vals, platlar=None):
    """vals: {platform: int|None}. (kırmızı_platformlar, sarı_platformlar) döner.
    Hiç harvest edilmemiş tanınmış marka (tot==0) TÜM platformlarda kırmızı to-do.
    Coverage'lı markada: eksik platform kırmızı (tot>=3 ise), dengesiz platform sarı."""
    platlar = platlar or list(vals.keys())
    tot = sum(v for v in vals.values() if v)
    en = max([v for v in vals.values() if v] or [0])
    if tot == 0:
        return list(platlar), []
    kirmizi = [p for p in platlar if vals.get(p) is None] if tot >= 3 else []
    sari = ([p for p in platlar if vals.get(p) and vals[p] < en * AZ_ORAN]
            if en >= AZ_MIN else [])
    return kirmizi, sari


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print("%s -> katla=%s taninmis=%s kanonik=%s"
              % (arg, markaKatla(arg), taninmisMarkaMi(arg), kanonik_veya_none(arg)))

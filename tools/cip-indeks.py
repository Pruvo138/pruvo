#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URETEC — ana sayfa CIP INDEKSI (marka / grup / model capraz daralma tablosu).

  python3 tools/cip-indeks.py               # ozet olcum (dosya YAZMAZ)
  python3 tools/cip-indeks.py --yazdir      # indeksi JSON olarak bas
  python3 tools/cip-indeks.py --olc         # kategori kirilimli dagilim

NE ISE YARAR (olculen musteri sikayeti, 2 Agu): ana sayfada `Marin` + `Bujiler` secilince
MARKA satiri hala `Mercury / Volvo / Yamaha / Jeanneau / Beneteau / GoPro / Zodiac`
gosteriyordu; bu markalarin HICBIRINDE Bujiler grubunda urun YOK -> her cip bir OLU UC.
Kok neden: cip evrenleri KATEGORIDEN turetiliyordu, o anki FILTRELENMIS kumeden degil.
Kartezyen (sabit) menuede bosluk orani olculdu: Marin %86,2 · Motosiklet %72 · Otomobil %58.
Turetilmis menude olu uc 0.

INDEKS bu boslugu KAPATIR: yalnizca DOLU kombinasyonlar tasinir, uc cip satirinin evreni
(MARKA · GRUP · MODEL) ondan turer. Gosterilen her cip >0 urun verir — kabul testi
(tools/cip-indeks-test.py) cipleri TEK TEK dolasip olcer, ORNEKLEME YAPMAZ.

NEDEN YAYIN KOPYASINA GOMULUR (kaynak index.html'e DEGIL):
  * indeks urunler.json'dan turer; MaCiT gunde birden cok parti urun ekler. Kaynak dosyaya
    gomulseydi HER partiden sonra blok BAYAT olur, tazelik kapisi kirmizi yanar ve BASKA
    bir mimarin akisini kilitlerdi. (ALTKATEGORILER blogu bunu yasamaz: o urun verisinden
    degil, sabit izinli kumeden — arama.ALTKATEGORI_IZINLI — turer.)
  * emsal ayni dosyada zaten var: `window.PRUVO_MARKA_SLUG` build.py :: _marka_cip_enjekte
    tarafindan yalniz yayin kopyasina (index.built.html) gomulur.
  * FAIL-CLOSED yon: indeks YOKSA (yerel gelistirme, enjeksiyon kopmasi) istemci ESKI
    davranisa doner — capraz daralma olmaz, MODEL satiri HIC cizilmez, filtreler AYNEN
    calisir. Yanlis liste GOSTERILMEZ; yalnizca daraltma yuzeyi kaybolur. Enjeksiyonun
    fiilen oldugunu tools/cip-indeks-test.py AYRI bir iddiayla (yayin kopyasi uzerinde) olcer.

ESIKLER (mimar spec'i, olculdu):
  * MARKA cipi >= 15 urun. Otomobil'de 84 markanin 30'u esigi gecer ve kategorinin
    %91,9'unu kapsar; kuyruk acilirsa marka x altkategori ikililerinin %58,7'si BOS
    cikardi (>=15'te %9,6).
  * MODEL cipi >= 3 urun, yalniz SECILI marka icin, ve yalniz >= 2 modelli markada
    (Otomobil 22 marka, Motosiklet 4 marka — veriden turetildi).

KAYNAK AYRIMI (olculdu, KODA YAZILMAZ — VERIDEN DOGAR): arac kategorilerinde marka/model
ekseni `uyum[]`ten gelir (Otomobil'de `marka` alaninin %93,5'i zaten uyumdan turetilmistir);
`uyum` bos olan kategorilerde (Marin: kapsama %14,3) yalnizca marka ekseni kalir, model
satiri HIC cizilmez. Marka<->model BAGI yalniz `uyum` cifti kurar; marka UYELIGI her iki
durumda da `marka` dizisinden okunur.

YUKLEM BIRLIGI (kritik): sayimlar index.html `filtered()` ile AYNI yuklemle yapilir —
  kategori TAM esitlik · altkategori TAM esitlik · marka: markaKatla(b) == hedef (dizideki
  HERHANGI bir eleman) · model: HAM etiket `marka` dizisinde.
Ayri bir sayim formulu yazilsaydi cip "3 urun" der, tik 0 getirirdi
([[ikiz-tanim-sessiz-ayrisma]]).

UC MARKA ETIKETI (`e` alani — olculdu 3 Agu, CANLI): cip etiketi KATLANMIS kanoniktir
("Volvo Penta" -> "Volvo"), UC ise ham etiketle TAM/BUYUK-KUCUK DUYARLI eslesir ve
KATLAMAZ. Olculen canli cikti:
    /katalog?kategori=Marin&marka=Volvo        -> toplam 0     (OLU UC — 51 urun kayip)
    /katalog?kategori=Marin&marka=Volvo Penta  -> toplam 51
    /katalog?kategori=Otomobil&marka=Mercedes  -> 1016  (kanonik 1036; "Mercedes-Benz" 20 DUSER)
    marka=Mercedes,Mercedes-Benz -> 0 · marka=merc -> 0 · marka=volvo penta -> 0
Yani uc virgul/coklu/onek/kucuk-harf KABUL ETMIYOR: gonderilebilecek TEK sey bir HAM etiket.
Iki taraf ayri etiket kullandigi surece gorunen cip OLU UC verir ([[ikiz-tanim-sessiz-ayrisma]]).
INDEKS bu yuzden her cipe `e` (uc etiketi) yazar: kanonik ad o kategoride HAM olarak
GECMIYORSA, en cok urunlu ham etiket (esitlikte alfabetik) `e` olur; geciyorsa `e` HIC
yazilmaz (bayt tasarrufu + davranis aynen kalir). Etiket UYDURULMAZ, urunler.json'daki
ham degerden turer. Istemci `e`yi index.html :: ucMarkaEtiketi ile okur.

UC SOZLESMESI (olculdu 2 Agu, canli): /katalog ve /ara `model` parametresini TANIYOR —
`?kategori=Otomobil&marka=BMW&model=E46` -> 104 (indeksin dedigi sayiyla BIREBIR),
`?model=E46` (markasiz) -> 104, `model=xyzyok` -> 0. AMA AYNI GUN daha ONCE olculdugunde
parametre SESSIZCE YOK SAYILIYORDU (marka+model -> 1673 = marka toplaminin aynisi). Bu
yuzden istemci parametreyi gondermekle YETINMEZ, CEVABI DEGER EKSENINDE DOGRULAR
(index.html :: edgeSuzgecSapmasi) — uc suzmeyi birakirsa liste SESSIZCE KABUL EDILMEZ.

TEK KAYNAK: marka kuratorlugu (TANINMIS_MARKALAR) ve katlama kurallari index.html'den
AYIKLANIR, kopya TUTULMAZ (emsal: tools/marka_model_build.py).
"""
import argparse
import json
import os
import re
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(DIR)

SURUM = 1
ESIK_MARKA = 15      # marka cipi: kategori icinde en az bu kadar urun
ESIK_MODEL = 3       # model cipi: marka icinde en az bu kadar urun
EN_AZ_MODEL = 2      # model satiri yalniz bu kadar modeli olan markada anlamli


# ---------------------------------------------------------------- marka evreni
def _norm(s):
    """index.html norm() portu: Turkce-duyarli kucuk harf + aksan sadelestirme."""
    s = (s or "").replace("I", "ı").replace("İ", "i").lower()
    for a, b in (("ı", "i"), ("ç", "c"), ("ğ", "g"), ("ö", "o"),
                 ("ş", "s"), ("ü", "u"), ("â", "a"), ("î", "i")):
        s = s.replace(a, b)
    return s


def _marka_norm(s):
    """index.html markaNorm() portu (aksan + ayirac kanoniklestirme)."""
    n = _norm(s)
    for a, b in (("é", "e"), ("è", "e"), ("ë", "e"), ("ä", "a")):
        n = n.replace(a, b)
    n = n.replace(" and ", " ").replace("&", " ").replace("+", " ")
    return re.sub(r"\s+", " ", n).strip()


class MarkaEvreni(object):
    """index.html'den AYIKLANMIS marka kuratorlugu (TANINMIS_MARKALAR + markaKatla)."""

    def __init__(self, index_metni):
        m = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", index_metni, re.S)
        if not m:
            raise RuntimeError("cip-indeks: index.html'de TANINMIS_MARKALAR YOK — marka "
                               "kuratorlugu turetilemedi (fail-closed).")
        self.taninmis = re.findall(r'"([^"]+)"', m.group(1))
        if not self.taninmis:
            raise RuntimeError("cip-indeks: TANINMIS_MARKALAR BOS — indeks uretilemez.")
        self._kanonik = {}
        for x in self.taninmis:
            self._kanonik[_marka_norm(x)] = x
        self._normlu = [_marka_norm(x) for x in self.taninmis]
        self._bellek = {}

    def katla(self, m):
        if m in self._bellek:
            return self._bellek[m]
        n = _marka_norm(m)
        sonuc = self._kanonik.get(n)
        if sonuc is None:
            sonuc = m
            for i, mn in enumerate(self._normlu):
                if n.startswith(mn + " ") or n.startswith(mn + "-"):
                    sonuc = self.taninmis[i]
                    break
        self._bellek[m] = sonuc
        return sonuc

    def taninmis_mi(self, m):
        return _marka_norm(m) in self._kanonik


def markalari(urun, evren):
    """Urunun UYE oldugu kanonik marka kalemleri — index.html filtered() ile BIREBIR
    (`(p.marka||[]).some(b => markaKatla(b) === hedef)`) + cip kuratorlugu."""
    out = []
    for ham in (urun.get("marka") or []):
        ad = (ham or "").strip()
        if not ad:
            continue
        kan = evren.katla(ad)
        if evren.taninmis_mi(kan) and kan not in out:
            out.append(kan)
    return out


def _ham_kume(urun):
    return set((x or "").strip() for x in (urun.get("marka") or []) if (x or "").strip())


def uc_etiketi(hamlar, kanonik):
    """UC'e gonderilecek HAM etiket — ya da None (kanonik zaten ham olarak var).

    UC katlamaz, TAM eslesir (canli olcum -> modul docstring'i). Kanonik ad o kategoride
    ham olarak GECIYORSA bugunku istek AYNEN calisir -> None (bayt + davranis degismez).
    GECMIYORSA cip OLU UC olurdu -> en cok urunlu ham etiket secilir (esitlikte alfabetik,
    deterministik). Ham kume BOS ise (olamaz ama) None: uydurma etiket URETILMEZ."""
    if not hamlar or kanonik in hamlar:
        return None
    return sorted(hamlar.items(), key=lambda t: (-t[1], t[0]))[0][0]


# ---------------------------------------------------------------- indeks uretimi
def indeks_uret(urunler, index_metni):
    """kategori -> marka -> {n, a{altIx:n}, m{model:{n, a{altIx:n}}}} (+ katalt, alt)

    Yalnizca DOLU kombinasyon tasinir; SIFIR sayi HIC yazilmaz (menu veriden turer,
    kartezyen DEGIL)."""
    evren = MarkaEvreni(index_metni)

    kat_alt = {}            # (kat, altk)         -> n   (URUN bazli; marka'dan BAGIMSIZ)
    kat_marka = {}          # (kat, marka)        -> n
    kat_alt_marka = {}      # (kat, altk, marka)  -> n
    kat_marka_ham = {}      # (kat, marka)        -> {HAM etiket: n}  (uc etiketi icin)
    cift = set()            # (kat, marka, model) — `uyum`un kurdugu marka<->model bagi

    # --- 1. gecis: marka sayimlari + marka<->model bagi + etiket sahipligi ---
    for u in urunler:
        kat = (u.get("kategori") or "").strip()
        altk = (u.get("altkategori") or "").strip()
        kat_alt[(kat, altk)] = kat_alt.get((kat, altk), 0) + 1
        markalar = markalari(u, evren)
        for b in markalar:
            kat_marka[(kat, b)] = kat_marka.get((kat, b), 0) + 1
            kat_alt_marka[(kat, altk, b)] = kat_alt_marka.get((kat, altk, b), 0) + 1
        # UC ETIKETI icin ham etiket sahipligi: URUN basina TEKIL sayilir (kat_marka ile
        # ayni birim), yoksa cok etiketli urun sayiyi sisirir ve `e` yanlis etikete kayar.
        for ham in set(_ham_kume(u)):
            kan = evren.katla(ham)
            if kan not in markalar:
                continue
            d = kat_marka_ham.setdefault((kat, kan), {})
            d[ham] = d.get(ham, 0) + 1
        for oge in (u.get("uyum") or []):
            mk = evren.katla((oge.get("marka") or "").strip())
            md = (oge.get("model") or "").strip()
            if md and mk in markalar:
                cift.add((kat, mk, md))

    # --- 2. gecis: model sayimlari (bag tamamlandiktan SONRA, FILTRE yuklemiyle) ---
    kat_marka_model = {}    # (kat, marka, model)       -> n
    kat_alt_mm = {}         # (kat, altk, marka, model) -> n
    for u in urunler:
        kat = (u.get("kategori") or "").strip()
        altk = (u.get("altkategori") or "").strip()
        ham = _ham_kume(u)
        for b in markalari(u, evren):
            for md in ham:
                if (kat, b, md) not in cift:
                    continue
                kat_marka_model[(kat, b, md)] = kat_marka_model.get((kat, b, md), 0) + 1
                kat_alt_mm[(kat, altk, b, md)] = kat_alt_mm.get((kat, altk, b, md), 0) + 1

    gecerli_marka = set(k for k, v in kat_marka.items() if v >= ESIK_MARKA)
    aday = set(k for k, v in kat_marka_model.items()
               if v >= ESIK_MODEL and (k[0], k[1]) in gecerli_marka)
    sayac = {}
    for (kat, mk, _md) in aday:
        sayac[(kat, mk)] = sayac.get((kat, mk), 0) + 1
    gecerli_model = set(k for k in aday if sayac[(k[0], k[1])] >= EN_AZ_MODEL)

    alt_tablo = sorted(set([a for (_k, a, _m) in kat_alt_marka] +
                           [a for (_k, a) in kat_alt]))
    alt_ix = dict((a, i) for i, a in enumerate(alt_tablo))

    # KATEGORI DUZEYI grup sayimlari — MARKA SECILI DEGILKEN grup satirinin evreni.
    # Marka bazli sayimlarin toplamiyla YAPILAMAZ: cok markali urun MUKERRER sayilir,
    # markasiz urun HIC sayilmazdi -> yanlis "bos" hukmu. Bu yuzden URUN bazli ayri tablo.
    katalt = {}
    for (kat, altk), n in kat_alt.items():
        if n > 0:
            katalt.setdefault(kat, {})[str(alt_ix[altk])] = n

    agac = {}
    for (kat, mk), n in kat_marka.items():
        if (kat, mk) in gecerli_marka:
            dugum = {"n": n, "a": {}, "m": {}}
            e = uc_etiketi(kat_marka_ham.get((kat, mk), {}), mk)
            if e is not None:
                dugum["e"] = e
            agac.setdefault(kat, {})[mk] = dugum
    for (kat, altk, mk), n in kat_alt_marka.items():
        if (kat, mk) in gecerli_marka:
            agac[kat][mk]["a"][str(alt_ix[altk])] = n
    for (kat, mk, md) in gecerli_model:
        agac[kat][mk]["m"][md] = {"n": kat_marka_model[(kat, mk, md)], "a": {}}
    for (kat, altk, mk, md), n in kat_alt_mm.items():
        if (kat, mk, md) in gecerli_model:
            agac[kat][mk]["m"][md]["a"][str(alt_ix[altk])] = n

    return {"surum": SURUM, "alt": alt_tablo, "kat": agac, "katalt": katalt}


def indeks_metni(indeks):
    """Deterministik, tek satirlik gomme metni (sort_keys: byte-kararli cikti)."""
    return ("<script>window.PRUVO_CIP_INDEKS="
            + json.dumps(indeks, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + ";</script>")


def enjekte(html_metni, indeks):
    """Yayin kopyasinin <head>'ine indeksi gomer. Capa yoksa FAIL-CLOSED: build DURUR."""
    if "</head>" not in html_metni:
        raise RuntimeError("cip-indeks: </head> capasi YOK — indeks gomulemedi "
                           "(sessizce atlanmaz; capraz daralma canlida kaybolurdu).")
    return html_metni.replace("</head>", indeks_metni(indeks) + "\n</head>", 1)


# ---------------------------------------------------------------- CLI
def _oku(kok):
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        index_metni = f.read()
    return urunler, index_metni


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=KOK)
    ap.add_argument("--yazdir", action="store_true", help="indeksi JSON bas")
    ap.add_argument("--olc", action="store_true", help="kategori kirilimli dagilim")
    a = ap.parse_args()

    urunler, index_metni = _oku(a.kok)
    ix = indeks_uret(urunler, index_metni)

    if a.yazdir:
        print(json.dumps(ix, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        return 0

    govde = indeks_metni(ix).encode("utf-8")
    marka = sum(len(v) for v in ix["kat"].values())
    model = sum(len(x["m"]) for v in ix["kat"].values() for x in v.values())
    ikili = sum(len(x["a"]) for v in ix["kat"].values() for x in v.values())
    ucler = sum(len(y["a"]) for v in ix["kat"].values() for x in v.values()
                for y in x["m"].values())
    print("cip indeksi: %d kategori · %d marka · %d model · %d (marka,grup) · %d (marka,model,grup)"
          % (len(ix["kat"]), marka, model, ikili, ucler))
    print("gomme boyutu: %d bayt · esikler marka>=%d, model>=%d, en az %d model"
          % (len(govde), ESIK_MARKA, ESIK_MODEL, EN_AZ_MODEL))
    if a.olc:
        for kat in sorted(ix["kat"]):
            v = ix["kat"][kat]
            md = sum(len(x["m"]) for x in v.values())
            print("  %-14s marka=%3d  model=%3d" % (kat, len(v), md))
    return 0


if __name__ == "__main__":
    sys.exit(main())

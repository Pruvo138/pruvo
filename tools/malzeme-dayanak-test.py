#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MALZEME DAYANAK KAPISI (kalici nobetci)

Kural (Okan, 21 Tem): landing sayfalarinda MALZEME SINIFI olarak anilan her ad
tools/filamentler.json envanterinde DAYANAGI olmalidir. Uretemedigimiz bir sinifi
(orn. PC / polikarbonat) sayfa metninde vaat etmek ticari beyan riskidir.

Nasil calisir
  1) tools/filamentler.json OKUNUR; envanter adlari ORADAN TURETILIR (kodda liste
     sabitlenmez -> tek kaynak). "ad" + "uzunAd" alanlarindan polimer jetonlari
     ayiklanir; "-" oncesi taban polimer de envantere girer
     (orn. "Karbon katkili (PETG-CF/PA-CF)" -> PETG-CF, PA-CF, PETG, PA).
  2) sayfalar.CONTENT_PAGES gezilir; her sayfanin GOVDESI + basligi + meta
     aciklamasi taranir (HTML etiketleri soyulur). AYRICA ege-bilgi.md (WhatsApp
     botu Ege'nin bilgi dosyasi) EK BIR TARANAN KAYNAK olarak taranir: bot bu metni
     musteriye aktarir, envanterde OLMAYAN bir malzeme adi (or. PC / polikarbonat)
     buraya sizarsa Ege uretemedigimiz malzemeyi vaat eder ve kimse gormez. Negatif
     kontrol: ege-bilgi.md'de gecen dayanaksiz malzeme -> KIRMIZI (hangi jeton oldugu
     yazilir). Fail-closed: ege-bilgi.md okunamazsa KIRMIZI.
  3) Metinde gecen polimer sinifi adaylari LEKSIK bir sozlukle bulunur (bu sozluk
     envanter DEGIL; dunyadaki filament sinifi adlarinin listesi). Her adayin
     TABAN polimeri envanterde yoksa KIRMIZI.
  4) Takviye eki (-CF / -GF) taban polimerden ayri degerlendirilir: taban
     envanterdeyse kapi KIRMIZI yakmaz, ama envanterde adi gecmeyen takviye eki
     UYARI olarak basilir (mimar karari bekler).

Yanlis-pozitif kapisi (olculdu): "PVC pencere / PVC dograma" gibi kullanimlar
MUSTERININ mevcut sistemini tarif eder, bizim malzeme vaadimiz degildir. Bu yuzden
adayin hemen ardindan URUN-SISTEM kelimesi geliyorsa (dograma/pencere/kapi/panjur/
profil/sineklik) malzeme beyani sayilmaz. Olculen ayrisma: PVC 3/3 sayfa elendi,
PC 75/75 sayfa yakalandi (yanlis-pozitif orani %0, kacan yok).

Fail-closed: filamentler.json okunamaz/bozuksa KIRMIZI.
Cikis: 0 = dayanaksiz yok, 1 = dayanaksiz var / okuma hatasi.
"""
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(KOK)
sys.path.insert(0, KOK)

FILAMENT_JSON = os.path.join(KOK, "filamentler.json")
EGE_BILGI = os.path.join(ROOT, "ege-bilgi.md")

# LEKSIK sozluk = "dunyada filament/polimer sinifi olarak kullanilan adlar".
# Envanteri TEMSIL ETMEZ; envanter filamentler.json'dan turetilir.
KISALTMALAR = [
    "PLA", "PETG", "PET", "PCTG", "ASA", "ABS", "TPU", "TPE", "PC", "PA",
    "PA6", "PA11", "PA12", "POM", "PP", "PE", "PVC", "PVA", "PEEK", "PEI",
    "ULTEM", "PPS", "PPSU", "PSU", "PMMA", "HIPS", "PVDF", "PBT", "SAN", "PSU",
]
TAKVIYE_EKLERI = ["CF", "GF", "CF15", "GF30", "GF25"]
# Turkce tam adlar -> kisaltma karsiligi
TAM_ADLAR = {
    "polikarbonat": "PC",
    "poliamid": "PA",
    "poliamit": "PA",
    "naylon": "PA",
    "nylon": "PA",
    "polipropilen": "PP",
    "polietilen": "PE",
    "poliasetal": "POM",
    "akrilik": "PMMA",
}
# Adayin hemen ardindan gelirse: musterinin mevcut sistemi anlatiliyor demektir.
URUN_SISTEM_KELIMELERI = ["dograma", "doğrama", "pencere", "kapi", "kapı", "panjur",
                          "profil", "sineklik", "cam", "kasa"]

TR_HARF = "0-9A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû"


def _jeton_ayikla(metin):
    """filamentler.json ad/uzunAd alanindan polimer jetonlarini ayiklar.
    Tek harfli jetonlar (°C'deki 'C' gibi) polimer adi degildir; elenir."""
    ham = re.findall(r"[A-Z][A-Z0-9]*(?:-[A-Z]{2}[0-9]{0,2})?", metin or "")
    return set(j for j in ham if len(j.split("-")[0]) >= 2)


def envanteri_oku():
    """filamentler.json -> (tam jetonlar, taban polimerler, takviye ekleri).
    Fail-closed: hata halinde istisna firlatir."""
    with open(FILAMENT_JSON, encoding="utf-8") as fp:
        veri = json.load(fp)
    kayitlar = veri["filamentler"]
    if not kayitlar:
        raise ValueError("filamentler.json: 'filamentler' listesi bos")
    tam = set()
    for kayit in kayitlar:
        tam |= _jeton_ayikla(kayit.get("ad", ""))
        tam |= _jeton_ayikla(kayit.get("uzunAd", ""))
    taban = set()
    ekler = set()
    for jeton in tam:
        parca = jeton.split("-")
        taban.add(parca[0])
        if len(parca) > 1:
            ekler.add(parca[1])
    if not taban:
        raise ValueError("filamentler.json: polimer jetonu turetilemedi")
    return tam, taban, ekler


def _html_soy(html):
    duz = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", duz)


def _aday_deseni():
    kis = sorted(set(KISALTMALAR), key=len, reverse=True)
    ekler = "|".join(sorted(set(TAKVIYE_EKLERI), key=len, reverse=True))
    tam = "|".join(sorted(TAM_ADLAR, key=len, reverse=True))
    return re.compile(
        r"(?<![%s])(?:(?P<kisa>%s)(?:-(?P<ek>%s))?|(?P<tam>%s))(?![%s])"
        % (TR_HARF, "|".join(kis), ekler, tam, TR_HARF),
        re.IGNORECASE,
    )


ADAY_DESENI = _aday_deseni()


def _urun_sistemi_mi(metin, bitis):
    """Adayin hemen ardindaki kelime musterinin mevcut sistemini mi anlatiyor?"""
    kalan = metin[bitis:bitis + 40].strip().lower()
    ilk = re.split(r"[^%s]+" % TR_HARF, kalan)
    ilk = ilk[0] if ilk else ""
    return any(ilk.startswith(k) for k in URUN_SISTEM_KELIMELERI)


def _adaylari_bul(metin):
    """metinde gecen malzeme sinifi adaylarini (kisa, ek, ham) uclusu olarak uretir.
    ham = metinde FIILEN gecen yazim (or. 'polikarbonat' -> kisa 'PC')."""
    for eslesme in ADAY_DESENI.finditer(metin):
        if eslesme.group("tam"):
            ham = eslesme.group("tam")
            kisa = TAM_ADLAR[ham.lower()]
            ek = None
        else:
            ham = eslesme.group("kisa")
            # kisaltmalar BUYUK harfle yazilir; "pc"/"Pc" gibi kullanim
            # (ornegin cumle basi bir kelime) malzeme sinifi sayilmaz.
            if ham != ham.upper():
                continue
            kisa = ham.upper()
            ek = (eslesme.group("ek") or "").upper() or None
        if _urun_sistemi_mi(metin, eslesme.end()):
            continue
        yield kisa, ek, ham


def sayfa_adaylari(metin):
    """metinde gecen malzeme sinifi adaylari -> {(kisaltma, ek)}"""
    return set((kisa, ek) for kisa, ek, _ham in _adaylari_bul(metin))


def main():
    try:
        envanter_tam, envanter_taban, envanter_ekleri = envanteri_oku()
    except Exception as hata:  # fail-closed
        print("KIRMIZI: filamentler.json okunamadi -> %s" % hata)
        return 1

    try:
        import sayfalar
    except Exception as hata:  # fail-closed
        print("KIRMIZI: sayfalar.py yuklenemedi -> %s" % hata)
        return 1

    print("Envanter (filamentler.json): tam=%s taban=%s takviye=%s"
          % (sorted(envanter_tam), sorted(envanter_taban), sorted(envanter_ekleri) or "-"))

    dayanaksiz = {}          # kisaltma -> [kaynak, ...]
    ek_uyarisi = {}          # (kisaltma, ek) -> [kaynak, ...]
    ege_ham = {}             # kisaltma -> {ham jeton, ...} (ege-bilgi.md kanitini yazmak icin)
    gorulen = set()
    sayfa_sayisi = 0
    for slug, baslik, meta, fn in sayfalar.CONTENT_PAGES:
        sayfa_sayisi += 1
        metin = _html_soy(fn()) + " . " + baslik + " . " + meta
        for kisa, ek in sayfa_adaylari(metin):
            gorulen.add(kisa if not ek else "%s-%s" % (kisa, ek))
            if kisa not in envanter_taban:
                dayanaksiz.setdefault(kisa, []).append(slug)
            elif ek and ek not in envanter_ekleri:
                ek_uyarisi.setdefault((kisa, ek), []).append(slug)

    # EK KAYNAK: ege-bilgi.md — WhatsApp botu Ege'nin bilgi dosyasi (landing sayfasi
    # DEGIL). Bot bu metni musteriye aktarir; envanterde olmayan bir malzeme adi
    # buraya sizarsa Ege uretemedigimizi vaat eder. Fail-closed: okunamazsa KIRMIZI.
    try:
        with open(EGE_BILGI, encoding="utf-8") as fp:
            ege_metin = _html_soy(fp.read())
    except Exception as hata:
        print("KIRMIZI: ege-bilgi.md okunamadi -> %s" % hata)
        return 1
    for kisa, ek, ham in _adaylari_bul(ege_metin):
        gorulen.add(kisa if not ek else "%s-%s" % (kisa, ek))
        if kisa not in envanter_taban:
            dayanaksiz.setdefault(kisa, []).append("ege-bilgi.md")
            ege_ham.setdefault(kisa, set()).add(ham)
        elif ek and ek not in envanter_ekleri:
            ek_uyarisi.setdefault((kisa, ek), []).append("ege-bilgi.md")

    print("Taranan sayfa: %d (+ ege-bilgi.md ek kaynak)" % sayfa_sayisi)
    print("Gorulen malzeme adi (%d): %s" % (len(gorulen), sorted(gorulen)))

    for (kisa, ek), slugler in sorted(ek_uyarisi.items()):
        print("UYARI: %s-%s takviye eki '%s' envanterde adlandirilmamis "
              "(taban %s dayanakli) - %d sayfa" % (kisa, ek, ek, kisa, len(slugler)))

    if dayanaksiz:
        print("")
        for kisa, slugler in sorted(dayanaksiz.items(), key=lambda x: -len(x[1])):
            print("KIRMIZI: '%s' filamentler.json envanterinde YOK - %d kaynak:"
                  % (kisa, len(slugler)))
            for slug in sorted(slugler):
                if slug == "ege-bilgi.md" and kisa in ege_ham:
                    print("    %s (jeton: %s)" % (slug, ", ".join(sorted(ege_ham[kisa]))))
                else:
                    print("    %s" % slug)
        print("")
        print("SONUC: KIRMIZI - dayanaksiz malzeme adi %d (%d kaynak kaydi)"
              % (len(dayanaksiz), sum(len(v) for v in dayanaksiz.values())))
        return 1

    print("SONUC: YESIL - dayanaksiz malzeme 0 / %d sayfa + ege-bilgi.md" % sayfa_sayisi)
    return 0


if __name__ == "__main__":
    sys.exit(main())

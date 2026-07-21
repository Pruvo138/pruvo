#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MALZEME DAYANAK KAPISI (kalici nobetci)

Kural (Okan, 21 Tem): YAYINLANAN her yuzeyde MALZEME SINIFI olarak anilan her ad
tools/filamentler.json envanterinde DAYANAGI olmalidir. Uretemedigimiz/tedarik
edemedigimiz bir sinifi metinde vaat etmek ticari beyan riskidir.

TARANAN GOVDE KAYNAKLARI
  A) landing         : sayfalar.CONTENT_PAGES — govde + baslik + meta
  B) ege-bilgi.md    : WhatsApp botu Ege'nin bilgi dosyasi (bot bu metni musteriye aktarir)
  C) statik-gorunur  : sss / gizlilik / hakkimizda / iletisim — GORUNUR metin
  D) statik-jsonld   : ayni 4 sayfanin JSON-LD bloklari (Google'in makineyle okudugu
                       acceptedAnswer metinleri). OLCULDU: sss/index.html'de
                       "Parcalar hangi malzemeden uretiliyor?" cevabi PA6+GF / PA12+GF /
                       POM adlarini FIILEN vaat ediyor — JSON-LD ayri bir yayin yuzeyidir.
Rapor "kaynak: <ad>" kirilimiyla basar; hangi govdeden geldigi gorunur.

Nasil calisir
  1) tools/filamentler.json OKUNUR; envanter adlari ORADAN TURETILIR (kodda liste
     sabitlenmez -> tek kaynak). "ad" + "uzunAd" alanlarindan polimer jetonlari
     ayiklanir; "-" oncesi taban polimer de envantere girer
     (orn. "Karbon katkili (PETG-CF/PA-CF)" -> PETG-CF, PA-CF, PETG, PA).
     Envanter IKI listeden gelir:
       - "filamentler"        : satilan/uretilen aile (site cipleri, Ege, rehber)
       - "_dayanakMalzemeler" : SATISTA OLMAYAN, siparis uzerine hizli tedarik edilen
         siniflar (Okan karari 21 Tem: PA6+GF / PA12+GF / POM stokta degil ama ihtiyac
         aninda tedarigi hizli -> site metni DOGRU, beyanin dayanagi burasi). Bunlar
         YALNIZ beyan dayanagidir; site/Ege/rehber uretimine GIRMEZ (asagida "sizinti").
  2) Metinde gecen polimer sinifi adaylari LEKSIK bir sozlukle bulunur (bu sozluk
     envanter DEGIL; dunyadaki filament sinifi adlarinin listesi). Her adayin
     TABAN polimeri envanterde yoksa KIRMIZI.
  3) Takviye eki (-CF / -GF) taban polimerden ayri degerlendirilir: taban
     envanterdeyse kapi KIRMIZI yakmaz, ama envanterde adi gecmeyen takviye eki
     UYARI olarak basilir (mimar karari bekler).

🔴 YASAKLI MALZEME KARA LISTESI (KARA_LISTE) — envanterle SUSTURULAMAZ
  Curutucu kanitladi: dayanak-kaydi mekanizmasi ayni zamanda bir SUSTURMA deligidir —
  filamentler.json'a {"ad":"PC","satista":false} eklenince "PC uretiyoruz" vaadi
  sessizce YESIL yanabiliyordu. Kara listedeki bir ad, taranan HERHANGI bir govdede
  VEYA filamentler.json'un ICINDE gecerse kapi KIRMIZI yakar; envanterde kaydi olsa
  BILE. Her ad icin "kim/ne zaman karar verdi" kodda yazilidir.

🔴 NEGATIF BAGLAM ELEYICISI YOK (bilincli karar, KraL tur 2)
  Onceki turda "ayni satirda olumsuzlama varsa eslesmeyi ele" diye bir eleyici
  denenmisti; curutucu OLCTU: "- PC ile üretim yok; ama isterse müşteriye PEEK ile
  üretip gönderiyoruz." satiri eleyiciyle YESIL yaniyordu — duz bir ticari vaat
  KACIYORDU. Eleyici GELMEDI. Olculdu (21 Tem, main HEAD 16d24a67): bugunku
  ege-bilgi.md'nin yasak listesi (NBR / FKM-Viton / EPDM / silikon / metal / cam)
  LEKSIK sozlukte GECMIYOR -> haksiz kirmizi YOK, eleyiciye ihtiyac YOK.
  Fikstur F4 bu karari kalici olarak kilitler (eleyici geri gelirse KIRMIZI).

DRIFT NOBETI: tools/ege-malzeme.py'nin BELLEKTE urettigi blok, ege-bilgi.md'deki
isaretciler arasindaki blokla BIREBIR ayni olmali. filamentler.json degisip
ege-bilgi.md guncellenmezse bot sessizce bayatlar -> KIRMIZI. (Dosyaya YAZILMAZ.)

SIZINTI KAPISI: "_dayanakMalzemeler" kayitlari satis kalemi DEGILDIR ->
"satista": false zorunlu, "tedarik" zorunlu, fiyat/katsayi/site alani YASAK
(Okan'in kilitli katsayi listesi disina cikilmaz). "_" onekli anahtar oldugu icin
build.py'nin urettigi public /filament-veri.js'e TASINMAZ ve ref["filamentler"]
uzerinde donen tum ureticiler (urun sayfasi cipleri, /malzeme-rehberi/,
tools/ege-malzeme.py) bu kayitlari GORMEZ -> ege-bilgi.md byte-ozdes kalir.

IC NOBETCI (--ic-nobetci ile tek basina da kosar; normal kosumda da HER SEFER calisir):
Bu kapinin KENDI davranislarini bellekte-fikstur ile kilitler. Sebep: gercek veri
zaten temiz oldugu icin, kapinin kodundan bir yetenegi (kara liste / JSON-LD taramasi /
dayanak alan dogrulamasi / negatif-eleyici YOKLUGU / kaynak kapsami) SILEN bir mutasyon
gercek veride YESIL kalirdi. Fikstur nobetcileri o mutasyonlari oldurur.

Fail-closed: filamentler.json / ege-bilgi.md / statik sayfa okunamaz-bozuksa,
JSON-LD ayristirilamazsa, beklenen bir kaynak bos gelirse KIRMIZI.
Bayraklar (mutasyon testi GERCEK dosyalari BOZMASIN diye tempfile kopyada kossun):
  --filament YOL  --ege YOL  --statik-kok DIZIN  --ege-malzeme YOL  --landing-kapali
Cikis: 0 = temiz, 1 = dayanaksiz ad / kara liste ihlali / kapsam / drift / okuma hatasi.
"""
import argparse
import importlib.util
import io
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(KOK)
sys.path.insert(0, KOK)

FILAMENT_JSON = os.path.join(KOK, "filamentler.json")
EGE_MD = os.path.join(ROOT, "ege-bilgi.md")
EGE_MALZEME_PY = os.path.join(KOK, "ege-malzeme.py")
STATIK_SAYFALAR = ["sss", "gizlilik", "hakkimizda", "iletisim"]
DAYANAK_ANAHTARI = "_dayanakMalzemeler"
DAYANAK_YASAK_ALAN = ["fiyat", "fiyatTL", "katsayi", "fiyatKatsayisi", "site",
                      "kategoriTavsiye"]

# ---------------------------------------------------------------- KARA LISTE
# Kodda SABIT. Envantere kayit eklenerek susturulamaz (bkz. modul basligi).
# ad -> (kim/ne zaman karar verdi, gerekce)
KARA_LISTE = {
    "PC": ("Okan, 21 Tem 2026 (KraL tur-2 talimatiyla iletildi)",
           "Polikarbonat (PC) URETMIYORUZ ve tedarik dayanagi da YOK. Bu ad hicbir "
           "yayin yuzeyinde gecemez; filamentler.json'a kayit eklenerek SUSTURULAMAZ."),
}

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

# Beklenen kaynak -> en az kac govde gelmeli (FAIL-CLOSED KAPSAM NOBETI).
# Bir kaynagi koddan SILEN mutasyon burada olur: gercek veri temiz oldugu icin
# kaynak silinince kapi aksi halde sessizce YESIL kalirdi. Tabanlar OLCULEN
# degerin belirgin altinda (landing 80, statik-gorunur 4, statik-jsonld 2).
KAYNAK_TABANI = {
    "landing": 50,
    "ege-bilgi.md": 1,
    "statik-gorunur": 4,
    "statik-jsonld": 2,
}
# statik-jsonld govdelerinden toplam kac KARAKTER metin cikmali (JSON-LD tarayicisi
# "bos liste dondur" mutasyonuyla susturulmasin). Olculen deger binlerce karakter.
JSONLD_METIN_TABANI = 500


def _jeton_ayikla(metin):
    """filamentler.json ad/uzunAd alanindan polimer jetonlarini ayiklar.
    Tek harfli jetonlar (°C'deki 'C' gibi) polimer adi degildir; elenir."""
    ham = re.findall(r"[A-Z][A-Z0-9]*(?:-[A-Z]{2}[0-9]{0,2})?", metin or "")
    return set(j for j in ham if len(j.split("-")[0]) >= 2)


def dayanak_dogrula(dayanak):
    """_dayanakMalzemeler kayitlari SATIS KALEMI DEGILDIR; sizinti kapisi.
    Hatada ValueError firlatir (fail-closed). -> ad listesi"""
    if not isinstance(dayanak, list):
        raise ValueError("filamentler.json: '%s' liste degil" % DAYANAK_ANAHTARI)
    adlar = []
    for kayit in dayanak:
        if not isinstance(kayit, dict) or not kayit.get("ad"):
            raise ValueError("%s: 'ad' alani olmayan kayit" % DAYANAK_ANAHTARI)
        if kayit.get("satista") is not False:
            raise ValueError('%s["%s"]: "satista": false ZORUNLU (satis kalemi degil)'
                             % (DAYANAK_ANAHTARI, kayit["ad"]))
        if not kayit.get("tedarik"):
            raise ValueError('%s["%s"]: "tedarik" alani ZORUNLU (dayanagin ne oldugu yazilmali)'
                             % (DAYANAK_ANAHTARI, kayit["ad"]))
        for yasak in DAYANAK_YASAK_ALAN:
            if yasak in kayit:
                raise ValueError(
                    '%s["%s"]: "%s" alani YASAK — fiyat katsayisi Okan\'in kilitli '
                    "listesindedir, dayanak kaydi satis kalemi degildir"
                    % (DAYANAK_ANAHTARI, kayit["ad"], yasak))
        adlar.append(kayit["ad"])
    return adlar


def envanteri_coz(veri):
    """Ayristirilmis filamentler.json sozlugu -> (tam, taban, ekler, dayanak_adlar).
    Fail-closed: hata halinde ValueError/KeyError firlatir."""
    kayitlar = veri["filamentler"]
    if not kayitlar:
        raise ValueError("filamentler.json: 'filamentler' listesi bos")
    dayanak = veri.get(DAYANAK_ANAHTARI, [])
    dayanak_adlar = dayanak_dogrula(dayanak)

    tam = set()
    for kayit in list(kayitlar) + list(dayanak):
        tam |= _jeton_ayikla(kayit.get("ad", ""))
        tam |= _jeton_ayikla(kayit.get("uzunAd", ""))
    taban, ekler = set(), set()
    for jeton in tam:
        parca = jeton.split("-")
        taban.add(parca[0])
        if len(parca) > 1:
            ekler.add(parca[1])
    if not taban:
        raise ValueError("filamentler.json: polimer jetonu turetilemedi")
    return tam, taban, ekler, dayanak_adlar


def envanteri_oku(yol=None):
    """Geriye donuk API — dosyadan okur."""
    with io.open(yol or FILAMENT_JSON, encoding="utf-8") as fp:
        return envanteri_coz(json.load(fp))


# ------------------------------------------------------------------ aday bulucu
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
    """Adayin hemen ardindaki kelime musterinin mevcut sistemini mi anlatiyor?
    ("PVC dograma / PVC pencere" = musterinin sistemi, bizim malzeme vaadimiz degil.)
    Olculen ayrisma (main'den devralindi): PVC 3/3 sayfa elendi, PC 75/75 yakalandi."""
    kalan = metin[bitis:bitis + 40].strip().lower()
    ilk = re.split(r"[^%s]+" % TR_HARF, kalan)
    ilk = ilk[0] if ilk else ""
    return bool(ilk) and any(ilk.startswith(k) for k in URUN_SISTEM_KELIMELERI)


def adaylari_bul(metin):
    """metinde gecen malzeme sinifi adaylarini (kisa, ek, ham) uclusu olarak uretir.
    ham = metinde FIILEN gecen yazim (or. 'polikarbonat' -> kisa 'PC').
    🔴 OLUMSUZLAMA/NEGATIF BAGLAM ELEYICISI YOKTUR (bilincli — modul basligina bak)."""
    for eslesme in ADAY_DESENI.finditer(metin):
        if eslesme.group("tam"):
            ham = eslesme.group("tam")
            kisa = TAM_ADLAR[ham.lower()]
            ek = None
        else:
            ham = eslesme.group("kisa")
            kisa = ham.upper()
            # Kisaltmalar BUYUK harfle yazilir; "pet"/"san"/"pvc pencere" gibi
            # kucuk harfli kullanim genellikle Turkce-Ingilizce bir kelimedir ->
            # yanlis-pozitif kapisi. OLCULDU (21 Tem, 87 govde): bu sart bugun
            # SADECE 2 eslesme eliyor, ikisi de "pvc pencere".
            # 🔴 ISTISNA — KARA LISTE: en yuksek bahisli kural buyuk/kucuk harfe
            # takilmasin ("pc ile üretiyoruz" da vaattir). OLCULDU: taranan 87
            # govdenin hicbirinde kucuk harfli "pc" YOK -> yanlis-pozitif maliyeti 0.
            if ham != ham.upper() and kisa not in KARA_LISTE:
                continue
            ek = (eslesme.group("ek") or "").upper() or None
        if _urun_sistemi_mi(metin, eslesme.end()):
            continue
        yield kisa, ek, ham


def sayfa_adaylari(metin):
    """Geriye donuk API: metinde gecen malzeme sinifi adaylari -> {(kisaltma, ek)}"""
    return set((kisa, ek) for kisa, ek, _ham in adaylari_bul(metin))


# ------------------------------------------------------------- govde kaynaklari
def govdeler_landing():
    """kaynak A: sayfalar.CONTENT_PAGES — govde + baslik + meta."""
    import sayfalar
    for slug, baslik, meta, fn in sayfalar.CONTENT_PAGES:
        yield ("landing", slug, _html_soy(fn()) + " . " + baslik + " . " + meta)


def govdeler_ege(yol):
    """kaynak B: ege-bilgi.md (WhatsApp botunun bilgi dosyasi). Fail-closed: bos -> hata."""
    with io.open(yol, encoding="utf-8") as f:
        icerik = f.read()
    if not icerik.strip():
        raise ValueError("ege-bilgi.md bos")
    yield ("ege-bilgi.md", os.path.basename(yol), _html_soy(icerik))


def jsonld_metinleri(ham):
    """HTML'deki JSON-LD bloklarindaki TUM string degerler (acceptedAnswer dahil).
    -> (blok listesi, metin listesi). Fail-closed: blok ayristirilamazsa ValueError."""
    metinler = []
    bloklar = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        ham, flags=re.S | re.I)
    for blok in bloklar:
        try:
            veri = json.loads(blok)
        except Exception as hata:
            raise ValueError("JSON-LD ayristirilamadi: %s" % hata)

        def gez(dugum):
            if isinstance(dugum, dict):
                for deger in dugum.values():
                    gez(deger)
            elif isinstance(dugum, list):
                for deger in dugum:
                    gez(deger)
            elif isinstance(dugum, str):
                metinler.append(dugum)
        gez(veri)
    return bloklar, metinler


def govdeler_statik(kok):
    """kaynak C + D: 4 statik sayfa — GORUNUR metin ve JSON-LD AYRI govdeler."""
    for slug in STATIK_SAYFALAR:
        yol = os.path.join(kok, slug, "index.html")
        with io.open(yol, encoding="utf-8") as f:
            ham = f.read()
        gorunur = re.sub(r"<(script|style)\b.*?</\1>", " ", ham, flags=re.S | re.I)
        yield ("statik-gorunur", slug, _html_soy(gorunur))
        bloklar, metinler = jsonld_metinleri(ham)
        if bloklar:
            yield ("statik-jsonld", slug, " . ".join(metinler))


# ------------------------------------------------------------------- drift nobeti
def _modul_yukle(yol):
    spec = importlib.util.spec_from_file_location("ege_malzeme_modul", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def blok_karsilastir(uretilen, icerik, basla, bitir):
    """(tamam_mi, mesaj) — isaretciler arasi blok uretilenle BIREBIR mi?"""
    if basla not in icerik or bitir not in icerik:
        return False, "ege-bilgi.md'de FILAMENT-REF isaretcileri YOK"
    mevcut = icerik[icerik.index(basla):icerik.index(bitir) + len(bitir)]
    if mevcut == uretilen:
        return True, ("ege-bilgi.md FILAMENT-REF blogu ege-malzeme.py ciktisiyla "
                      "BIREBIR (%d karakter)" % len(mevcut))
    fark = next((i for i in range(min(len(mevcut), len(uretilen)))
                 if mevcut[i] != uretilen[i]), min(len(mevcut), len(uretilen)))
    return False, ("blok BAYAT: ilk fark %d. karakterde | dosya=%r | uretilen=%r"
                   % (fark, mevcut[fark:fark + 60], uretilen[fark:fark + 60]))


def drift_kontrolu(ege_yol, ege_malzeme_yol):
    """ege-malzeme.py'nin BELLEKTE urettigi blok == ege-bilgi.md'deki blok mu?
    Dosyaya YAZMAZ."""
    modul = _modul_yukle(ege_malzeme_yol)
    with io.open(ege_yol, encoding="utf-8") as f:
        icerik = f.read()
    return blok_karsilastir(modul.bolum_uret(), icerik, modul.BASLA, modul.BITIR)


# ------------------------------------------------------------------ degerlendirme
def degerlendir(kaynaklar, envanter_taban, envanter_ekleri):
    """kaynaklar: [(kaynak, slug, metin), ...]
    -> (ozet, dayanaksiz, kara_ihlal, ek_uyarisi)"""
    ozet = {}            # kaynak -> {"govde": n, "adlar": set(), "metin": karakter}
    dayanaksiz = {}      # kisaltma -> [(kaynak, slug, ham), ...]
    kara_ihlal = {}      # kisaltma -> [(kaynak, slug, ham), ...]
    ek_uyarisi = {}      # (kisaltma, ek) -> ["kaynak/slug", ...]
    for kaynak, slug, metin in kaynaklar:
        sayac = ozet.setdefault(kaynak, {"govde": 0, "adlar": set(), "metin": 0})
        sayac["govde"] += 1
        sayac["metin"] += len(metin)
        for kisa, ek, ham in adaylari_bul(metin):
            sayac["adlar"].add(kisa if not ek else "%s-%s" % (kisa, ek))
            if kisa in KARA_LISTE:
                # 🔴 KARA LISTE ENVANTERI EZER: kayit olsa bile KIRMIZI.
                kara_ihlal.setdefault(kisa, []).append((kaynak, slug, ham))
            elif kisa not in envanter_taban:
                dayanaksiz.setdefault(kisa, []).append((kaynak, slug, ham))
            elif ek and ek not in envanter_ekleri:
                ek_uyarisi.setdefault((kisa, ek), []).append("%s/%s" % (kaynak, slug))
    return ozet, dayanaksiz, kara_ihlal, ek_uyarisi


def dayanak_taban_jetonlari(dayanak_adlar):
    """['PA6-GF', 'POM'] -> {'PA6', 'POM'} (taban polimer jetonlari)."""
    return set(ad.split("-")[0].upper() for ad in dayanak_adlar)


def dayanak_sizintisi(dayanak_adlar, uretimler):
    """SIZINTI KONTROLU (calistirilabilir kanit): "_dayanakMalzemeler" kayitlari
    SATIS/URETIM duzlemine SIZMAMALI. uretimler = [(uretim adi, uretilen metin), ...]
    (public /filament-veri.js govdesi, ege-malzeme.py'nin urettigi blok,
    /malzeme-rehberi/ sayfasi). Bir dayanak adi bu ciktilarin BIRINDE gorunurse
    -> sizinti. -> {uretim adi: [jeton, ...]}"""
    hedef = dayanak_taban_jetonlari(dayanak_adlar)
    sizinti = {}
    for ad, metin in uretimler:
        gorulen = set(kisa for kisa, _ek in sayfa_adaylari(metin))
        ortak = sorted(gorulen & hedef)
        if DAYANAK_ANAHTARI in (metin or ""):
            ortak.append(DAYANAK_ANAHTARI)
        if ortak:
            sizinti[ad] = ortak
    return sizinti


def kara_liste_envanterde(ham_json_metni):
    """filamentler.json'un HAM metninde kara listedeki bir ad geciyor mu?
    (Susturma deliginin ikinci agzi: envantere kayit ekleyip kapiyi kandirma.)"""
    bulunan = {}
    for kisa, _ek, ham in adaylari_bul(ham_json_metni):
        if kisa in KARA_LISTE:
            bulunan.setdefault(kisa, set()).add(ham)
    return bulunan


# ------------------------------------------------------------ IC NOBETCI (fikstur)
def _f_envanter(veri=None):
    return envanteri_coz(veri or {"filamentler": [{"ad": "PLA"}, {"ad": "PETG"}]})


def ic_nobetci():
    """Kapinin KENDI yeteneklerini bellekte-fikstur ile kilitler.
    -> (hata listesi, kosulan kontrol sayisi). Dosyaya BAKMAZ, dosyaya YAZMAZ."""
    hata = []
    sayac = [0]

    def kontrol(ad, kosul, ayrinti=""):
        sayac[0] += 1
        if not kosul:
            hata.append("%s %s" % (ad, ayrinti))

    # F1 — KARA LISTE ENVANTERI EZER (envantere kayit ekleyip susturma deligi)
    _t, taban, ekler, _d = _f_envanter({"filamentler": [{"ad": "PLA"}, {"ad": "PC"}]})
    _o, dayanaksiz, kara, _e = degerlendir(
        [("fikstur", "F1", "Talep ederseniz PC ile üretip gönderiyoruz.")], taban, ekler)
    kontrol("F1", "PC" in kara and "PC" not in dayanaksiz,
            "envanterde PC kaydi varken kara liste ihlali YAKALANMADI "
            "(kara=%s dayanaksiz=%s)" % (sorted(kara), sorted(dayanaksiz)))

    # F2/F3 — KARA LISTE envanter METNINDE de yakalanir, temizde yanlis-pozitif yok
    kontrol("F2", "PC" in kara_liste_envanterde('{"filamentler":[{"ad":"PC"}]}'),
            "filamentler.json ham metnindeki PC kaydi yakalanmadi")
    kontrol("F3", not kara_liste_envanterde('{"filamentler":[{"ad":"PETG"}]}'),
            "temiz envanterde yanlis-pozitif kara liste ihlali")

    # F4 — NEGATIF BAGLAM ELEYICISI YOK (curutucunun kacirdigi gercek vaka)
    _t, taban, ekler, _d = _f_envanter()
    _o, dayanaksiz, kara, _e = degerlendir(
        [("fikstur", "F4",
          "- PC ile üretim yok; ama isterse müşteriye PEEK ile üretip gönderiyoruz.")],
        taban, ekler)
    kontrol("F4", "PC" in kara and "PEEK" in dayanaksiz,
            "olumsuzlama iceren satirdaki vaat KACTI (negatif eleyici geri gelmis olabilir) "
            "kara=%s dayanaksiz=%s" % (sorted(kara), sorted(dayanaksiz)))

    # F14 — TAM AD haritasi: Turkce tam ad da malzeme beyanidir ("polikarbonat" -> PC)
    _o, d14, k14, _e = degerlendir(
        [("fikstur", "F14a", "İhtiyaç halinde polikarbonat ile üretiyoruz.")], taban, ekler)
    _o, d14b, _k, _e = degerlendir(
        [("fikstur", "F14b", "Poliasetal ile de üretiyoruz.")], taban, ekler)
    kontrol("F14", "PC" in k14 and not d14 and "POM" in d14b,
            "tam ad haritasi bozuk (polikarbonat->%s/%s · poliasetal->%s)"
            % (sorted(k14), sorted(d14), sorted(d14b)))

    # F5 — JSON-LD taramasi: ad YALNIZ acceptedAnswer icinde olsa da bulunur
    html = ('<html><body><p>temiz gorunur metin</p>'
            '<script type="application/ld+json">'
            '{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"soru",'
            '"acceptedAnswer":{"@type":"Answer","text":"POM ve PEEK ile üretiyoruz."}}]}'
            '</script></body></html>')
    bloklar, metinler = jsonld_metinleri(html)
    kontrol("F5a", len(bloklar) == 1 and any("PEEK" in m for m in metinler),
            "JSON-LD string degerleri ayiklanmadi (metin=%r)" % metinler)
    _o, dayanaksiz, _k, _e = degerlendir(
        [("statik-jsonld", "F5", " . ".join(metinler))], taban, ekler)
    kontrol("F5b", "PEEK" in dayanaksiz and "POM" in dayanaksiz,
            "JSON-LD icindeki dayanaksiz ad yakalanmadi (%s)" % sorted(dayanaksiz))

    # F6 — bozuk JSON-LD fail-closed
    try:
        jsonld_metinleri('<script type="application/ld+json">{bozuk</script>')
        kontrol("F6", False, "bozuk JSON-LD sessizce gecti (fail-closed degil)")
    except ValueError:
        kontrol("F6", True)

    # F7 — URUN/SISTEM eleyicisi: yanlis-pozitif yok ama vaat KACMIYOR
    _o, d1, _k, _e = degerlendir([("fikstur", "F7a", "PVC doğrama profili takarız.")],
                                 taban, ekler)
    _o, d2, _k, _e = degerlendir([("fikstur", "F7b", "PVC ile üretim yapıyoruz.")],
                                 taban, ekler)
    kontrol("F7", not d1 and "PVC" in d2,
            "urun/sistem eleyicisi bozuk (dograma=%s vaat=%s)" % (sorted(d1), sorted(d2)))

    # F8 — dayanak kaydi sizinti kapisi (negatif + pozitif)
    for kotu, neden in [
            ({"ad": "POM", "tedarik": "x"}, "satista alani yok"),
            ({"ad": "POM", "satista": True, "tedarik": "x"}, "satista true"),
            ({"ad": "POM", "satista": False}, "tedarik yok"),
            ({"ad": "POM", "satista": False, "tedarik": "x", "fiyat": "1 TL"}, "fiyat alani"),
            ({"ad": "POM", "satista": False, "tedarik": "x", "katsayi": 1.2}, "katsayi alani"),
            ({"ad": "POM", "satista": False, "tedarik": "x", "site": True}, "site alani"),
            ({"satista": False, "tedarik": "x"}, "ad yok")]:
        try:
            dayanak_dogrula([kotu])
            kontrol("F8", False, "dayanak kaydi REDDEDILMEDI (%s): %r" % (neden, kotu))
        except ValueError:
            kontrol("F8", True)
    try:
        dayanak_dogrula([{"ad": "POM", "satista": False, "tedarik": "siparis uzerine"}])
        kontrol("F8-pozitif", True)
    except ValueError as e:
        kontrol("F8-pozitif", False, "gecerli dayanak kaydi reddedildi: %s" % e)

    # F9 — envanter fail-closed
    for kotu, neden in [({"filamentler": []}, "bos liste"),
                        ({"filamentler": [{"ad": "PLA"}], DAYANAK_ANAHTARI: {}},
                         "dayanak liste degil")]:
        try:
            envanteri_coz(kotu)
            kontrol("F9", False, "bozuk envanter kabul edildi (%s)" % neden)
        except (ValueError, KeyError):
            kontrol("F9", True)

    # F10 — dayanak kaydi envanteri GENISLETIR (site uretimine girmeden)
    _t, taban10, ekler10, adlar10 = _f_envanter(
        {"filamentler": [{"ad": "PLA"}],
         DAYANAK_ANAHTARI: [{"ad": "PA6-GF", "satista": False, "tedarik": "siparis uzerine"}]})
    kontrol("F10", "PA6" in taban10 and "GF" in ekler10 and adlar10 == ["PA6-GF"],
            "dayanak kaydindan taban/ek turetilemedi (taban=%s ek=%s ad=%s)"
            % (sorted(taban10), sorted(ekler10), adlar10))

    # F11 — drift karsilastirmasi (ozdes / farkli / isaretcisiz)
    kontrol("F11a", blok_karsilastir("<A>x<B>", "once <A>x<B> sonra", "<A>", "<B>")[0],
            "ozdes blok DRIFT sayildi")
    kontrol("F11b", not blok_karsilastir("<A>y<B>", "once <A>x<B> sonra", "<A>", "<B>")[0],
            "farkli blok drift SAYILMADI")
    kontrol("F11c", not blok_karsilastir("<A>x<B>", "isaretcisiz metin", "<A>", "<B>")[0],
            "isaretci yoklugu drift SAYILMADI")

    # F13 — SIZINTI dedektoru gercekten atesliyor (ve temizde yanlis-pozitif yok)
    adlar13 = ["PA6-GF", "PA12-GF", "POM"]
    kontrol("F13a", dayanak_taban_jetonlari(adlar13) == {"PA6", "PA12", "POM"},
            "dayanak taban jetonu turetilemedi: %s" % dayanak_taban_jetonlari(adlar13))
    kirli = dayanak_sizintisi(adlar13, [("sahte cikti", "Ürün POM ile üretilir.")])
    temiz = dayanak_sizintisi(adlar13, [("sahte cikti", "Ürün PETG ile üretilir.")])
    anahtar = dayanak_sizintisi(adlar13, [("sahte cikti", '{"%s":[]}' % DAYANAK_ANAHTARI)])
    kontrol("F13b", kirli and not temiz and anahtar,
            "sizinti dedektoru bozuk (kirli=%s temiz=%s anahtar=%s)"
            % (kirli, temiz, anahtar))

    # F15 — BUYUK-HARF sarti duruyor (yanlis-pozitif kapisi) AMA kara listede
    #       buyuk/kucuk harf ayrimi YOK (en yuksek bahisli kural kacmasin)
    _o, d15a, k15a, _e = degerlendir(
        [("fikstur", "F15a", "Müşteri pet şişe kapağı için parça istedi.")], taban, ekler)
    _o, d15b, _k, _e = degerlendir(
        [("fikstur", "F15b", "PET esaslı malzemeyle üretiyoruz.")], taban, ekler)
    _o, _d, k15c, _e = degerlendir(
        [("fikstur", "F15c", "İsterseniz pc ile de üretiyoruz.")], taban, ekler)
    kontrol("F15", not d15a and not k15a and "PET" in d15b and "PC" in k15c,
            "buyuk-harf sarti / kara liste harf duyarsizligi bozuk "
            "(kucuk pet=%s · buyuk PET=%s · kucuk pc kara=%s)"
            % (sorted(d15a), sorted(d15b), sorted(k15c)))

    # F12 — kaynak kapsam tabani gercekten bir sey ISTIYOR (bos/gevsek olmasin)
    # Tabanlar OLCULEN degerlere gore sabitlenmistir; "hepsini 1 yap" mutasyonu kapsam
    # nobetini sessizce olduruyordu -> beklenen degerler burada kilitli.
    kontrol("F12", KAYNAK_TABANI == {"landing": 50, "ege-bilgi.md": 1,
                                     "statik-gorunur": 4, "statik-jsonld": 2}
            and JSONLD_METIN_TABANI >= 500,
            "KAYNAK_TABANI/JSONLD_METIN_TABANI gevsetilmis: %r / %r"
            % (KAYNAK_TABANI, JSONLD_METIN_TABANI))
    return hata, sayac[0]


# ---------------------------------------------------------------------- ana akis
def main(argv=None):
    ap = argparse.ArgumentParser(description="PRUVO malzeme dayanak kapisi")
    ap.add_argument("--filament", default=FILAMENT_JSON)
    ap.add_argument("--ege", default=EGE_MD)
    ap.add_argument("--statik-kok", default=ROOT)
    ap.add_argument("--ege-malzeme", default=EGE_MALZEME_PY)
    ap.add_argument("--landing-kapali", action="store_true",
                    help="yalniz olcum/hizli kosum icin; CI'da KULLANILMAZ")
    ap.add_argument("--ic-nobetci", action="store_true",
                    help="YALNIZ fikstur nobetcilerini kosar (gercek dosyalara bakmaz)")
    args = ap.parse_args(argv)

    ic_hata, ic_sayi = ic_nobetci()
    print("IC NOBETCI (bellekte fikstur): %d kontrol, %d hata" % (ic_sayi, len(ic_hata)))
    for h in ic_hata:
        print("  ❌ " + h)
    if args.ic_nobetci:
        print("SONUC: %s" % ("KIRMIZI ❌" if ic_hata else "YESIL ✅"))
        return 1 if ic_hata else 0

    try:
        with io.open(args.filament, encoding="utf-8") as fp:
            filament_ham = fp.read()
        envanter_tam, envanter_taban, envanter_ekleri, dayanak_adlar = \
            envanteri_coz(json.loads(filament_ham))
    except Exception as hata:  # fail-closed
        print("KIRMIZI: filamentler.json okunamadi -> %s" % hata)
        return 1

    print("Envanter (%s): tam=%s taban=%s takviye=%s"
          % (os.path.basename(args.filament), sorted(envanter_tam),
             sorted(envanter_taban), sorted(envanter_ekleri) or "-"))
    print("Dayanak kaydi (SATISTA DEGIL, siparis uzerine tedarik): %s"
          % (", ".join(dayanak_adlar) or "-"))
    print("Kara liste (envanterle SUSTURULAMAZ): %s" % ", ".join(sorted(KARA_LISTE)))

    kaynaklar = []
    try:
        if not args.landing_kapali:
            kaynaklar.extend(govdeler_landing())
        kaynaklar.extend(govdeler_ege(args.ege))
        kaynaklar.extend(govdeler_statik(args.statik_kok))
    except Exception as hata:  # fail-closed
        print("KIRMIZI: govde kaynagi okunamadi -> %s" % hata)
        return 1

    ozet, dayanaksiz, kara_ihlal, ek_uyarisi = degerlendir(
        kaynaklar, envanter_taban, envanter_ekleri)

    for kaynak in sorted(ozet):
        v = ozet[kaynak]
        print("kaynak: %-16s govde=%-3d metin=%-7d malzeme adi (%d): %s"
              % (kaynak, v["govde"], v["metin"], len(v["adlar"]), sorted(v["adlar"])))
    print("Taranan govde TOPLAM: %d" % sum(v["govde"] for v in ozet.values()))

    # --- kapsam nobeti (bir kaynagi silen/susturan mutasyon burada olur) ---
    kapsam_hata = []
    if not args.landing_kapali:
        for kaynak, taban_sayi in sorted(KAYNAK_TABANI.items()):
            gelen = ozet.get(kaynak, {}).get("govde", 0)
            if gelen < taban_sayi:
                kapsam_hata.append("kaynak '%s' govde=%d < beklenen taban %d "
                                   "(kaynak kaybolmus/susturulmus olabilir)"
                                   % (kaynak, gelen, taban_sayi))
        jsonld_metin = ozet.get("statik-jsonld", {}).get("metin", 0)
        if jsonld_metin < JSONLD_METIN_TABANI:
            kapsam_hata.append("statik-jsonld metin uzunlugu %d < taban %d "
                               "(JSON-LD tarayicisi bos donuyor olabilir)"
                               % (jsonld_metin, JSONLD_METIN_TABANI))

    envanter_kara = kara_liste_envanterde(filament_ham)

    for (kisa, ek), yerler in sorted(ek_uyarisi.items()):
        print("UYARI: %s-%s takviye eki '%s' envanterde adlandirilmamis "
              "(taban %s dayanakli) - %d govde" % (kisa, ek, ek, kisa, len(yerler)))

    drift_tamam, drift_mesaj = True, ""
    ege_blok = None
    try:
        modul = _modul_yukle(args.ege_malzeme)
        ege_blok = modul.bolum_uret()
        with io.open(args.ege, encoding="utf-8") as f:
            drift_tamam, drift_mesaj = blok_karsilastir(
                ege_blok, f.read(), modul.BASLA, modul.BITIR)
    except Exception as hata:  # fail-closed
        drift_tamam, drift_mesaj = False, "drift kontrolu kosulamadi -> %s" % hata
    print("DRIFT (ege-malzeme.py <-> ege-bilgi.md): %s - %s"
          % ("TAMAM" if drift_tamam else "KIRMIZI", drift_mesaj))

    # --- SIZINTI KONTROLU: dayanak kaydi URETIM duzlemine gecmis mi? ---
    # (Talimat sarti: dayanak kayitlari filamentler.json'i tuketen HICBIR ciktiyi
    #  degistirmemeli. Burada calistirilabilir kanit uretilir.)
    sizinti = {}
    sizinti_cikti = 0
    if dayanak_adlar:
        veri = json.loads(filament_ham)
        # build.py'nin /filament-veri.js icin kullandigi AYNI ifade (public govde)
        public_govde = json.dumps(
            {k: v for k, v in veri.items() if not k.startswith("_") and k != "kaynaklar"},
            ensure_ascii=False)
        uretimler = [("public /filament-veri.js govdesi", public_govde)]
        if ege_blok is not None:
            uretimler.append(("ege-malzeme.py uretilen blok", ege_blok))
        for kaynak, slug, metin in kaynaklar:
            if kaynak == "landing" and slug == "malzeme-rehberi":
                uretimler.append(("/malzeme-rehberi/ sayfasi", metin))
        sizinti = dayanak_sizintisi(dayanak_adlar, uretimler)
        sizinti_cikti = len(uretimler)
        print("SIZINTI (dayanak kaydi -> uretim duzlemi): %s - %d cikti tarandi (%s)"
              % ("KIRMIZI" if sizinti else "TEMIZ", sizinti_cikti,
                 ", ".join(ad for ad, _m in uretimler)))
        # Sizinti taramasi SESSIZCE bosalmasin (cikti listesi kirpilirsa kapi
        # kanit uretmeden yesil kalirdi).
        if not args.landing_kapali and sizinti_cikti < 3:
            kapsam_hata.append("sizinti taramasi %d cikti gordu (beklenen >= 3: "
                               "filament-veri.js govdesi + ege-malzeme blogu + "
                               "/malzeme-rehberi/)" % sizinti_cikti)

    kirmizi = False
    if ic_hata:
        print("")
        print("KIRMIZI: IC NOBETCI %d kontrolde basarisiz — kapinin KENDI yetenegi "
              "bozulmus (yukaridaki ❌ satirlari)" % len(ic_hata))
        kirmizi = True

    if envanter_kara:
        print("")
        for kisa, hamlar in sorted(envanter_kara.items()):
            kim, gerekce = KARA_LISTE[kisa]
            print("KIRMIZI: KARA LISTE '%s' filamentler.json ICINDE geciyor (jeton: %s)"
                  % (kisa, ", ".join(sorted(hamlar))))
            print("    karar: %s — %s" % (kim, gerekce))
        kirmizi = True

    if kara_ihlal:
        print("")
        for kisa, yerler in sorted(kara_ihlal.items(), key=lambda x: -len(x[1])):
            kim, gerekce = KARA_LISTE[kisa]
            print("KIRMIZI: KARA LISTE '%s' %d govdede geciyor "
                  "(envanterde kaydi olsa BILE gecerli degil)" % (kisa, len(yerler)))
            print("    karar: %s — %s" % (kim, gerekce))
            for kaynak, slug, ham in sorted(set(yerler))[:12]:
                print("    %s :: %s (jeton: %s)" % (kaynak, slug, ham))
            if len(set(yerler)) > 12:
                print("    ... (+%d govde)" % (len(set(yerler)) - 12))
        kirmizi = True

    if dayanaksiz:
        print("")
        for kisa, yerler in sorted(dayanaksiz.items(), key=lambda x: -len(x[1])):
            print("KIRMIZI: '%s' filamentler.json envanterinde YOK - %d govde:"
                  % (kisa, len(yerler)))
            for kaynak, slug, ham in sorted(set(yerler))[:12]:
                print("    %s :: %s (jeton: %s)" % (kaynak, slug, ham))
            if len(set(yerler)) > 12:
                print("    ... (+%d govde)" % (len(set(yerler)) - 12))
        kirmizi = True

    if kapsam_hata:
        print("")
        for h in kapsam_hata:
            print("KIRMIZI: KAPSAM - " + h)
        kirmizi = True

    if sizinti:
        print("")
        for ad, jetonlar in sorted(sizinti.items()):
            print("KIRMIZI: SIZINTI - dayanak kaydi '%s' ciktisina gecmis: %s"
                  % (ad, ", ".join(jetonlar)))
        print("    Dayanak kayitlari YALNIZ beyan dayanagidir; satis/uretim duzlemine "
              "girmez (fiyat katsayisi Okan'da kilitli).")
        kirmizi = True

    if not drift_tamam:
        print("")
        print("KIRMIZI: ege-bilgi.md MALZEME blogu filamentler.json'dan bayat "
              "(cozum: python3 tools/ege-malzeme.py)")
        kirmizi = True

    if kirmizi:
        print("")
        print("SONUC: KIRMIZI ❌ (dayanaksiz=%d · kara-liste govde=%d · envanter-kara=%d "
              "· kapsam=%d · sizinti=%d · drift=%s · ic nobetci hatasi=%d)"
              % (len(dayanaksiz), len(kara_ihlal), len(envanter_kara), len(kapsam_hata),
                 len(sizinti), "KIRMIZI" if not drift_tamam else "tamam", len(ic_hata)))
        return 1

    print("SONUC: YESIL ✅ - dayanaksiz malzeme 0 / %d govde, kara liste ihlali yok, "
          "drift yok" % sum(v["govde"] for v in ozet.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

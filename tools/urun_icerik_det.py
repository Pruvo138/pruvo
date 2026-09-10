#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DETERMINISTIK URUN ICERIGI — AI YOK, ag YOK, kota YOK.

NEDEN VAR (olculdu 9 Eyl 2026, K398 turu):
  `tools/urun-ekle.py` (+ `printables-ekle.py`, `makerworld-ekle.py`) icerik adimini
  emekli motora TEK BACAKLA baglamisti:
      ai.returncode != 0  -> "HATA: kredi kapisi — urun AI izni yok"   -> URUN DUSER
      oneri.json yok      -> "HATA: emekli motor oneri yok"            -> URUN DUSER
  Deterministik YEDEK YOKTU. Motor 400 dondugu gun (`gpt-5.4-mini` ChatGPT hesabinda
  desteklenmiyor) uc platformun hatti da 0/N STAGE verdi. CLAUDE.md'nin kendi kurali
  bunun TERSINI soyluyor: "Toplu uründe AI YOK, yerel deterministik arac; urun-AI
  kapisi KAPALI: PRUVO_URUN_AI_IZNI".

EMSAL (KraL evinde DEGIL, adiyla yaziliyor — kopyalanmadi, DESENI alindi):
  /Users/okan/dev/pruvo-hasat/olcum/_mkdcgt_icerik_uret6.py :: main()   (MaCiT evi)
  mak-design x CGTrader dilim-6 ureteci. Emekli is motoru/AI cagrisi YOK. Icerik alanlarini
  `*-icerik-elle.json`'dan (insan kuratorlugu) alir, fiyati `_mkdcgt_fiyat.tl_formul()`
  formulunden, id'yi `r2_anahtar.urun_slug()`'tan turetir. Son bir ayda ~10k urun bu
  SINIF yolla eklendi.
  KOPYALAMA KARARI: KOPYALANMADI. Gerekce olculdu — o dosya `hasat_ortak`,
  `_mkdcgt_fiyat` ve kampanyaya-ozel `kalibrasyon/*.json` fikstürlerine bagli; girdisi
  de ELLE yazilmis `icerik-elle.json`. KraL hattinin girdisi bambaska: `thing-hazirla`/
  `prep()` ciktisi `meta.json` + indirilmis galeri. Kopya, iki evi birbirine baglayan
  bir IKIZ TANIM yaratirdi ([[ikiz-tanim-sessiz-ayrisma]]). Alinan sey DESEN:
  "icerik alanlari AI'dan degil, DETERMINISTIK kaynaktan + FORMULDEN turer".

BU MODUL NE YAPAR:
  `meta.json` + galeri dosya adlarindan, `thing-icerik.py`'nin URETTIGI SOZLESMENIN
  AYNISINI (sec_gorseller/elenen/baslik/aciklama/kategori/marka/fiyat_oneri/not)
  deterministik olarak uretir. Ayni girdi -> ayni cikti (saf fonksiyon; tek yan etki
  cagiranin yazdigi dosya).

BU MODUL NE YAPMAZ:
  * urunler.json'a YAZMAZ (yazan tek mesru yol tools/duzelt.py).
  * Ag'a CIKMAZ, model CAGIRMAZ, kota HARCAMAZ.
  * Turkce metni "uydurmaz": basliktan/olcuden EMIN OLMADIGI hicbir ozelligi yazmaz.
    Terim tablosu bir urunu tanimiyorsa cikti `elle_gozden_gecir: True` ile ISARETLENIR
    (sessiz kirpma YASAK dersi, [[artik-yuzey-mutant-dedektorunu-korlestirir]] sinifi).

MARKA DILI: uretilen metin PRUVO'nun URETIM SURECINE dair dil TASIMAZ ("3D baski",
`basil-` koku, dilimleyici/dosya dili). Kaynak baslikta gecen o dil (orn. "3D print
model" — olculdu: yerel 363 kaynak basligin 42'sinde) `temizle_kaynak_baslik()` ile
SILINIR; kalinti `denetim-kapisi.py` KAPI 8'de kirmizi yanar.
"""
import importlib.util
import json
import os
import re
import sys
import unicodedata

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS_DIR)

# oneri.json'a yazilan kaynak damgasi — hangi bacagin urettigi SONRADAN okunabilsin.
KAYNAK_AI = "emekli-motor"
KAYNAK_DET = "deterministik"


def _katla(s):
    """Turkce diakritikleri duserek karsilastirma anahtari ('Bahçe' -> 'bahce')."""
    s = (s or "").replace("ı", "i").replace("I", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).casefold().strip()


# =============================================================================
# 1. KAYNAK BASLIK TEMIZLIGI
# =============================================================================
# OLCULDU (yerel 363 `detail.json`): kaynak basliklarin 42'si "3D print model",
# 8'i "Free", 1'i "3D Model Pack" kuyrugu tasiyor. Bunlar hem PAZARLAMA GURULTUSU
# hem de (ilk ikisi) MARKA DILI IHLALI -> baslik uretimine girmeden SILINIR.
_GURULTU_RE = [
    re.compile(r"\bfree\s+3d\s+print(able)?\s+model\b", re.I),
    re.compile(r"\b3d\s+print(able)?\s+model\b", re.I),
    re.compile(r"\b3d\s+model\s+pack\b", re.I),
    re.compile(r"\b3d\s+print(ed|able)?\b", re.I),
    re.compile(r"\bstl\b|\b3mf\b|\bgcode\b", re.I),
    re.compile(r"\bfree\b", re.I),
    re.compile(r"\bdownload\b|\bremix\b", re.I),
]
# Surum kuyrugu: "V1b", "V2", "v4b" — bilgi tasimaz, baslikta gurultu yapar.
_SURUM_RE = re.compile(r"\bv\s?\d+[a-z]?\b", re.I)


def temizle_kaynak_baslik(ham):
    """Kaynak (Ingilizce) basliktan pazarlama + uretim-sureci gurultusunu ELER."""
    s = ham or ""
    for rx in _GURULTU_RE:
        s = rx.sub(" ", s)
    s = _SURUM_RE.sub(" ", s)
    s = re.sub(r"[\s\-_/|,;:]+", " ", s)
    return s.strip(" -–—·.").strip()


# =============================================================================
# 2. PARCA TERIMI: Ingilizce kaynak jetonu -> Turkce parca adi
# =============================================================================
# 🔴 BU TABLO BIR "CEVIRMEN" DEGIL, BIR TANIYICIDIR. Tanidigini Turkce adlandirir;
# TANIMADIGINI UYDURMAZ -> `elle_gozden_gecir` isareti kalkar ve insan suzgeci
# (URUN-EKLEME-REHBERI "oneri.json'lari suz" adimi) o kaydi gorur.
# Anahtarlar COK KELIMELI olabilir; eslesme UZUN ONCE yapilir (bkz. `parca_terimi`)
# cunku "bottle holder" ile "holder" ayni metinde eslesir ve kisa olan yanlis kazanir.
TERIM = {
    # tutucu / montaj ailesi
    "bottle holder": "Matara Tutucu",
    "phone holder": "Telefon Tutucu",
    "cup holder": "Bardaklık",
    "cable holder": "Kablo Tutucu",
    "pump holder": "Pompa Tutucu",
    "wall mount": "Duvar Askısı",
    "holder": "Tutucu",
    "mount": "Montaj Aparatı",
    "bracket": "Braket",
    "clip": "Klips",
    "hook": "Askı",
    "stand": "Stand",
    "tray": "Tepsi",
    "case": "Kutu",
    "box": "Kutu",
    "cover": "Kapak",
    "cap": "Kapak",
    "plug": "Tapa",
    "lid": "Kapak",
    "adapter": "Adaptör",
    "spacer": "Ara Pul",
    "washer": "Pul",
    "bushing": "Burç",
    "knob": "Topuz",
    "handle": "Kol",
    "lever": "Kol",
    "grip": "Tutamak",
    "handlebar grip": "Gidon Tutamağı",
    "handlebar": "Gidon Parçası",
    "guard": "Koruma",
    "protector": "Koruyucu",
    "mudguard": "Çamurluk",
    "fender": "Çamurluk",
    "spool": "Makara",
    "gear": "Dişli",
    "pulley": "Kasnak",
    "nozzle": "Uç",
    "funnel": "Huni",
    "hinge": "Menteşe",
    "latch": "Mandal",
    "bolt": "Cıvata",
    "nut": "Somun",
    "screw": "Vida",
    "spacer ring": "Ara Halka",
    "ring": "Halka",
    "insert": "İç Parça",
    "plate": "Plaka",
    "panel": "Panel",
    "frame": "Çerçeve",
    "rack": "Taşıyıcı",
    "carrier": "Taşıyıcı",
    "basket": "Sepet",
    "organizer": "Düzenleyici",
    "hanger": "Askı",
    "stopper": "Stoper",
    "damper": "Damper",
    "bumper": "Tampon",
    "seal": "Conta",
    "gasket": "Conta",
    "filter": "Filtre",
    "valve": "Valf",
    "pump": "Pompa",
    "fan": "Fan",
    "propeller": "Pervane",
    "impeller": "Çark",
    "anode": "Tutya",
    "cleat": "Koç Boynuzu",
    "winch": "Vinç",
    "hatch": "Kapak Menfezi",
    "tool": "Alet",
    "wrench": "Anahtar",
    "jig": "Şablon",
    "gauge": "Mastar",
    "vise": "Mengene",
    "clamp": "Kelepçe",
    "key": "Anahtar",
    "keychain": "Anahtarlık",
    "lamp": "Lamba Parçası",
    "light": "Aydınlatma Parçası",
    "switch": "Anahtar Parçası",
    "button": "Düğme",
    "battery holder": "Pil Yuvası",
    "charger": "Şarj Aparatı",
    "camera mount": "Kamera Montaj Aparatı",
    "lens cap": "Lens Kapağı",
    "tripod": "Tripod Parçası",
}
# Eslesme UZUN ONCE (cok-kelimeli anahtar kisa anahtari YUTMASIN).
_TERIM_SIRALI = sorted(TERIM.items(), key=lambda kv: -len(kv[0]))
# 🔴 COGUL TOLERANSI (olculdu): duz `\bdamper\b` kaynak basliktaki "dampers"i KACIRIYORDU.
# Yerel gercek basliklarda "dampers", "fenders", "Bolts", "Nuts", "Grips", "Brushes"
# geciyor. Son jetona (?:e?s)? eklenir — bas kismi degismez, cunku cok-kelimeli
# anahtarlarda cogul YALNIZ son sozcuge gelir ("bottle holders", "bottles holder" DEGIL).
_TERIM_RE = [(re.compile(r"\b" + re.escape(k) + r"(?:e?s)?\b", re.I), v)
             for k, v in _TERIM_SIRALI]


# Ingilizce baslikta BAS ISIM'i bitiren edatlar: "X for Y" / "X of Y" / "X with Y"
# kaliplarinda urun X'tir, Y degildir ("Mounting of a front wing ... for a fork" -> mounting).
_EDAT_RE = re.compile(r"\b(?:for|of|with|to|on|in|from|by)\b", re.I)


def parca_terimi(baslik):
    """Temizlenmis Ingilizce basliktan Turkce parca adi (tanimiyorsa None).

    🔴 KONUM ONEMLI — OLCULDU (gercek urun thing:4790449, "Safety cover latch for skate
    blades"): tabloyu yalniz anahtar UZUNLUGUNA gore taramak "cover"i "latch"ten once
    dondurdu ve urun "Kapak" oldu; dogru bas isim "latch" = "Mandal". Ingilizce'de bas
    isim niteleyicilerin SONUNDADIR, o yuzden eslesmenin BITIS konumu belirleyicidir.
    Arama edattan ONCEKI parcada yapilir ("... for a fork" kuyrugu urunu adlandirmaz);
    edat oncesi parcada hic eslesme yoksa TUM baslik taranir (bilgi kaybetmemek icin).

    🔴 KIYAS ANAHTARI (BITIS, UZUNLUK) — BASLANGIC DEGIL. Ikinci kez olculdu: baslangica
    gore siralamak "Handlebar grip"i "grip"e dusuruyordu (ikisi AYNI yerde biter ama
    cok-kelimeli olan daha ONCE baslar). Bitise gore: "cover"(11) < "latch"(17) -> latch;
    "handlebar grip"(14) == "grip"(14) -> esitlikte UZUN anahtar kazanir.
    """
    b = baslik or ""
    m = _EDAT_RE.search(b)
    for parca in ([b[:m.start()], b] if m else [b]):
        en_iyi = None
        for rx, tr in _TERIM_RE:
            mm = None
            for mm in rx.finditer(parca):
                pass                     # EN SAGDAKI eslesme
            if mm is None:
                continue
            aday = (mm.end(), mm.end() - mm.start(), tr)
            if en_iyi is None or aday[:2] > en_iyi[:2]:
                en_iyi = aday
        if en_iyi is not None:
            return en_iyi[2]
    return None


# =============================================================================
# 3. KATEGORI: SIRALI kural listesi (doktrin = thing-icerik.py PROMPT'u)
# =============================================================================
# SIRA ANLAMLIDIR ve doktrinin kendi onceliklerini kodlar:
#   * Kamera, Elektronik'ten ONCE  ("kameraya dair HER sey -> Kamera").
#   * Bisiklet, Elektronik'ten ONCE ("e-bike Elektronik'e DEGIL").
#   * Tamirat EN SONDA ve YALNIZ marka-BAGIMSIZ atolye aleti icin.
# Terimler kaynak baslik (EN) + varsa uretilen TR terim uzerinde aranir.
KATEGORI_KURALLARI = [
    ("Marin", r"\bboat|marine|kayak|canoe|sail|yacht|anode|cleat|rudder|propeller|"
              r"outboard|kayık|tekne|denizc|pervane|tutya"),
    ("Kamera", r"\bcamera|gopro|dslr|tripod|lens|gimbal|action ?cam|kamera"),
    ("Bisiklet", r"\bbicycle|bike|handlebar|mtb|cycling|e-?bike|pedal|saddle|"
                 r"bisiklet|gidon"),
    ("Motosiklet", r"\bmotorcycle|motorbike|scooter|helmet|motosiklet|kask"),
    ("Otomobil", r"\bcar\b|automobile|vehicle|dashboard|windshield|trunk|bumper|"
                 r"otomobil|araç|torpido|bagaj"),
    ("Bahçe", r"\bgarden|plant|pot\b|hose|irrigation|lawn|greenhouse|bahçe|saks|sulama"),
    ("Elektronik", r"\bprinter|arduino|raspberry|pcb|electronic|usb|cable manage|"
                   r"vacuum|coffee ?machine|fridge|elektronik|kablo düzen"),
    ("Ofis", r"\bpen\b|pencil|desk|office|monitor|headphone|kalem|masaüstü|ofis"),
    ("Ev", r"\bkitchen|bathroom|shower|towel|drawer|closet|mutfak|banyo|çekmece|dolap"),
    ("Dekorasyon", r"\bvase|decor|ornament|wall art|sculpture|vazo|dekor|süs"),
    ("Oyun/Hobi", r"\btoy\b|puzzle|board ?game|dice|hobby|oyuncak|yapboz|zar\b"),
    ("Tamirat", r"\bvise|clamp|wrench|workshop|repair|jig|gauge|mengene|kelepçe|"
                r"anahtar|atölye|tamir"),
]
_KATEGORI_RE = [(ad, re.compile(rx, re.I | re.UNICODE)) for ad, rx in KATEGORI_KURALLARI]
# Hicbir kural tutmazsa: marka-BAGIMSIZ genel parca -> Tamirat (doktrinin artik kovasi).
KATEGORI_ARTIK = "Tamirat"


def gecerli_kategoriler():
    """Kanonik kategori listesi — TEK KAYNAK tools/kategori-kapisi.py (index.html +
    build.py karsilastirmasi). GIZLI kategoriler (Jeneratör = parametrik/sari seri)
    CIKARILIR: o seri ELLE kurgulanir, otomatik ureteç oraya urun DUSUREMEZ.
    Liste BURADA TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]])."""
    yol = os.path.join(TOOLS_DIR, "kategori-kapisi.py")
    spec = importlib.util.spec_from_file_location("kategori_kapisi_det", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    gizli = mod.kaynak_listeler()[1]
    return [k for k in mod.gecerli_kategoriler() if k not in gizli]


def kategori_sec(metin, gecerli):
    """(kategori, eslesen_kural|None). `gecerli` = kanonik kategori listesi (TEK KAYNAK:
    tools/kategori-kapisi.py). Kural listesindeki bir ad gecerli kumede YOKSA ATLANIR —
    boylece bu tablo kategori listesi degistiginde SESSIZCE gecersiz ad uretemez."""
    gset = {_katla(k): k for k in (gecerli or ())}
    for ad, rx in _KATEGORI_RE:
        kanon = gset.get(_katla(ad))
        if kanon is None:
            continue                    # kategori listesinden dusmus ad -> kural OLU
        if rx.search(metin or ""):
            return kanon, ad
    return gset.get(_katla(KATEGORI_ARTIK), (gecerli or ["Tamirat"])[0]), None


# =============================================================================
# 4. MARKA: canli katalogdan TURETILEN sozluk (ikinci elle-liste YOK)
# =============================================================================
# 🔴 KIRLI MARKA kumesi tools/denetim-kapisi.py'nin TEK KAYNAGINDAN okunur; burada
# ikinci kopya tutulmaz ([[ikiz-tanim-sessiz-ayrisma]]). O kume `kapi_marka_kirli`
# tarafindan REDDEDILEN jetonlardir — ureteç onlari HIC uretmemeli.
_MARKA_ONBELLEK = {}


def _denetim_modulu():
    # denetim-kapisi.py kardes modullerini DUZ `import` ile alir (git_ortami, ...) ->
    # tools/ sys.path'te olmadan exec_module COKER. importlib ile yuklerken bu kosul
    # cagiranin sorumlulugudur.
    if TOOLS_DIR not in sys.path:
        sys.path.insert(0, TOOLS_DIR)
    yol = os.path.join(TOOLS_DIR, "denetim-kapisi.py")
    spec = importlib.util.spec_from_file_location("denetim_kapisi_det", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kirli_markalar():
    """denetim-kapisi.py::_KIRLI_MARKA (katlanmis). Okunamazsa BOS kume DEGIL — hata."""
    if "kirli" not in _MARKA_ONBELLEK:
        _MARKA_ONBELLEK["kirli"] = {_katla(m) for m in _denetim_modulu()._KIRLI_MARKA}
    return _MARKA_ONBELLEK["kirli"]


def marka_sozlugu(urunler_yolu=None):
    """Canli katalogun `marka` dizilerinden TURETILEN {katlanmis: kanonik} sozlugu.

    Neden katalogdan: marka evreni zaten orada ve `marka-kanon-uret.py`/`d1-sync`
    ayni kaynaktan turer. Elle ikinci bir marka listesi acmak [[ikiz-tanim]] uretirdi.
    Tek-kelimelik markalar alinir: cok-kelimeli jeton `index.html::BILESIK_MARKA`
    aynasini ilgilendirir ve bu ureteç o yuzeye DOKUNMAZ."""
    yol = urunler_yolu or os.path.join(KOK, "urunler.json")
    anahtar = "sozluk:" + yol
    if anahtar in _MARKA_ONBELLEK:
        return _MARKA_ONBELLEK[anahtar]
    sozluk = {}
    try:
        with open(yol, encoding="utf-8") as f:
            for u in json.load(f):
                for m in (u.get("marka") or []):
                    if not isinstance(m, str):
                        continue
                    m = m.strip()
                    if not m or " " in m or len(m) < 3:
                        continue
                    k = _katla(m)
                    if k in kirli_markalar():
                        continue
                    sozluk.setdefault(k, m)
    except (OSError, ValueError):
        sozluk = {}                     # katalog okunamadi -> marka BOS (uydurma YOK)
    _MARKA_ONBELLEK[anahtar] = sozluk
    return sozluk


def marka_bul(baslik, sozluk=None, urunler_yolu=None):
    """Baslik jetonlarindan KANONIK marka listesi (jenerik urunse [])."""
    sz = marka_sozlugu(urunler_yolu) if sozluk is None else sozluk
    bulunan, gorulen = [], set()
    for t in re.findall(r"[\w]+", baslik or "", re.UNICODE):
        k = _katla(t)
        if k in sz and k not in gorulen:
            gorulen.add(k)
            bulunan.append(sz[k])
    return bulunan


# =============================================================================
# 5. FIYAT: olculen hacimden KADEMELI oneri (denetim-kapisi TABANI = 200 TL)
# =============================================================================
# 🔴 TABAN IKINCI KOPYA DEGIL: denetim-kapisi.py::FIYAT_TABANI'ndan OKUNUR. Oradaki
# sayi degisirse ureteç kendiliginden uyar; gomulu 200 birakmak, kapiyi bir gun
# kirmiziya yakacak sessiz bir ikiz olurdu.
# Kademeler doktrinin kendi cumlesinden turer (thing-icerik.py PROMPT'u):
#   "kucuk tekil parca ~200-600 TL, buyuk/coklu-parca/set ~600-1200 TL".
# Olcusuz kayit (MakerWorld/CGTrader gibi olcu-muaf kaynaklar) -> en dusuk kademe.
FIYAT_KADEME_CM3 = ((30, 250), (150, 350), (600, 500), (2000, 750))
FIYAT_TAVAN = 1200


def fiyat_tabani():
    return float(_denetim_modulu().FIYAT_TABANI)


def fiyat_oner(olcu_mm):
    """[a,b,c] mm -> '<n> TL'. Olcu yoksa taban kademesi. Cikti DAIMA taban ustu."""
    taban = fiyat_tabani()
    hacim_cm3 = None
    if isinstance(olcu_mm, (list, tuple)) and len(olcu_mm) == 3:
        try:
            hacim_cm3 = (float(olcu_mm[0]) * float(olcu_mm[1]) * float(olcu_mm[2])) / 1000.0
        except (TypeError, ValueError):
            hacim_cm3 = None
    if hacim_cm3 is None:
        return "%d TL" % int(taban)
    tl = FIYAT_TAVAN
    for esik, deger in FIYAT_KADEME_CM3:
        if hacim_cm3 < esik:
            tl = deger
            break
    return "%d TL" % int(max(tl, taban))


# =============================================================================
# 6. ACIKLAMA: sablon + OLCU SATIRI (denetim-kapisi KAPI 3 capasi)
# =============================================================================
# 🔴 OLCU SATIRI ZORUNLU: denetim-kapisi.py::_OLCU_RE bu capa ifadesini arar
# ("Yaklaşık dış ölçüler: A × B × C mm."). Thingiverse/Printables kaydinda satir
# YOKSA kapi `auto_sil` verir. Placeholder YAZILMAZ — olcu yoksa satir DA yazilmaz
# (kapi o zaman dogru sekilde kirmizi yanar; sahte satir kapiyi KORLESTIRIRDI).
OLCU_CAPA = "Yaklaşık dış ölçüler: %d × %d × %d mm."


def aciklama_uret(ad, marka, olcu_mm, uyum_notu=None):
    """MARKA DILI'ne uyan, ozellik UYDURMAYAN kisa aciklama."""
    baş = ("%s için %s." % (", ".join(marka), ad.lower())) if marka else ("%s." % ad)
    satirlar = [
        baş,
        "Özel tasarım üretim: sipariş üzerine üretilir.",
        "Sağlam ve hafif bir parça olarak teslim edilir.",
    ]
    if uyum_notu:
        satirlar.append(uyum_notu)
    if isinstance(olcu_mm, (list, tuple)) and len(olcu_mm) == 3:
        try:
            satirlar.append(OLCU_CAPA % (int(olcu_mm[0]), int(olcu_mm[1]), int(olcu_mm[2])))
        except (TypeError, ValueError):
            pass
    return "\n".join(satirlar)


# =============================================================================
# 7. URETEC — thing-icerik.py ile AYNI SOZLESME
# =============================================================================
VARSAYILAN_SECIM = 4        # doktrin: "3-4 iyi gorsel sec" (thing-icerik.py PROMPT)


def _dogal_sirala(dosyalar):
    return sorted(dosyalar, key=lambda f: int(re.sub(r"\D", "", f) or 0))


def uret(meta, galeri, kategoriler=None, azami_secim=VARSAYILAN_SECIM,
         marka_sozluk=None, urunler_yolu=None):
    """meta.json + galeri -> oneri.json sozlesmesi (AI YOK).

    Donen sozluk `thing-icerik.py`nin urettigi anahtarlarin HEPSINI tasir; ustune
    iki IZLENEBILIRLIK alani ekler:
      kaynak            = "deterministik"
      elle_gozden_gecir = terim tablosu urunu TANIMADI (insan suzgeci gorsun)
    """
    kategoriler = gecerli_kategoriler() if kategoriler is None else kategoriler
    galeri = _dogal_sirala(list(galeri or []))
    secili = galeri[:azami_secim]
    elenen = [{"dosya": f, "neden": "deterministik secim disi (ilk %d kart gorseli)"
               % azami_secim} for f in galeri[azami_secim:]]

    ham = meta.get("baslik") or ""
    temiz = temizle_kaynak_baslik(ham)
    terim = parca_terimi(temiz)
    marka = marka_bul(temiz, sozluk=marka_sozluk, urunler_yolu=urunler_yolu)
    # 🔴 MARKA KATEGORIYI SURUKLER (doktrin, thing-icerik.py PROMPT'u): "Arac/marka-OZEL
    # parca -> ilgili arac kategorisine, Tamirat'a DEGIL" ve "marka adi gecen urunu
    # Tamirat'a KOYMA". Bu yuzden kategori kurallari markayi DA gorur: marka jetonlari
    # metne katilir, boylece "Saab 900 fuel cap" gibi (icinde 'car' gecmeyen) bir baslik
    # artik kovaya DUSMEZ. Marka bir arac markasi degilse kurallar zaten tutmaz.
    kategori, _kural = kategori_sec(temiz, kategoriler)
    if _kural is None and marka:
        # Kural tutmadi ama MARKA var -> doktrin geregi artik kova (Tamirat) YASAK.
        # Marka tasiyan parca varsayilan olarak Otomobil'e gider (katalogun olculen
        # agirligi orada); yanlissa insan suzgeci gorur -> elle_gozden_gecir asagida acilir.
        gset = {_katla(k): k for k in kategoriler}
        kategori = gset.get(_katla("Otomobil"), kategori)
        _kural = "marka-suruklemesi"

    if terim:
        # NITELEYICI (olculdu): terim TEK BASINA ayirt etmiyor. "Bicycle Chain Cleaner
        # Wash Brushes Tool" -> yalniz "Alet" kaliyordu; boyle bir ad katalogdaki her
        # aletle Jaccard-ikiz olur ve dedup kapisini korlestirir. Marka varsa marka,
        # yoksa KATEGORI adi niteleyici olur ("Bisiklet Aleti" degil "Bisiklet Alet" —
        # cekim yapmayiz, uydurma dilbilgisi riski yok).
        nitel = " ".join(marka) if marka else (kategori if _katla(kategori) not in
                                               (_katla(terim),) else "")
        ad = ((nitel + " ") if nitel else "") + terim
    else:
        # TANIMADI: kaynak basligi UYDURMADAN tasi. Bos/uydurma bir Turkce ad uretmek
        # dedup kapisini (Jaccard) korlestirirdi.
        ad = temiz or ham or (meta.get("id") or "Parça")

    # ── elle_gozden_gecir: NE OLCUYOR ────────────────────────────────────────────
    # 🔴 ILK TANIMI "kaynak jetonlarindan >=2 dustu" idi ve OLCULDU ki 363/363 kayitta
    # ACIK yaniyordu — daima acik bir bayrak HICBIR SEY olcmez, gurultudur. Su uc
    # OLCULEBILIR kosula daraltildi; her biri insan suzgecinin gercekten bakmasi
    # gereken bir belirsizlik:
    #   (a) terim tablosu urunu TANIMADI -> ad Turkce degil, kaynak basligin kendisi.
    #   (b) kategori kural listesinden DEGIL, artik kovadan ya da marka-suruklemesinden
    #       geldi -> secim bir kanittan degil bir varsayimdan dogdu.
    #   (c) kaynak baslik BOS -> uretilecek hicbir bilgi yok (yerel veride 320/363).
    gozden = (terim is None) or (_kural in (None, "marka-suruklemesi")) or not temiz

    olcu = meta.get("olcu_mm")
    return {
        "sec_gorseller": secili,
        "elenen": elenen,
        "baslik": ad,
        "aciklama": aciklama_uret(ad, marka, olcu),
        "kategori": kategori,
        "marka": marka,
        "fiyat_oneri": fiyat_oner(olcu),
        "not": "deterministik ureteç (AI cagrisi YOK)",
        "kaynak": KAYNAK_DET,
        "elle_gozden_gecir": gozden,
    }


# =============================================================================
# 8. ORKESTRASYON — uc ekle betiginin ORTAK icerik adimi
# =============================================================================
# 🔴 BU FONKSIYON HATTIN TEK BACAKLILIGINI KAPATIR:
#   * AI yolu YALNIZCA PRUVO_URUN_AI_IZNI=EVET iken DENENIR (CLAUDE.md kurali).
#   * Izin yoksa ya da AI BASARISIZSA urun DUSMEZ -> deterministik yol calisir.
#   * Deterministik yol da yazamazsa (galeri bos) ancak o zaman None doner.
def ai_izinli():
    return os.environ.get("PRUVO_URUN_AI_IZNI") == "EVET"


def icerik_sagla(anahtar, cache_dizin, meta, galeri, kategoriler=None,
                 ai_cagir=None, urunler_yolu=None):
    """(oneri_dict|None, kaynak, aciklama_metni) dondurur; oneri.json'u YAZAR.

    `ai_cagir(anahtar) -> bool` cagiranin verdigi AI bacagidir (urun-ekle.py'de
    `thing-icerik.py` alt sureci). None ise AI bacagi HIC denenmez.
    """
    onerip = os.path.join(cache_dizin, "oneri.json")
    if ai_izinli() and ai_cagir is not None:
        # 🔴 BAYAT DOSYA KAPISI: onceki kosumdan kalan oneri.json, basarisiz bir
        # cagriyi "basarili" gosterebilir (varlik kolu tek basina yargic olurdu).
        # Cagridan ONCE silinir -> dosyanin VARLIGI bu kosumun kanitidir.
        if os.path.exists(onerip):
            os.unlink(onerip)
        if ai_cagir(anahtar) and os.path.exists(onerip):
            try:
                with open(onerip, encoding="utf-8") as f:
                    o = json.load(f)
                if isinstance(o, dict) and o.get("baslik"):
                    o.setdefault("kaynak", KAYNAK_AI)
                    return o, KAYNAK_AI, "AI icerigi"
            except (OSError, ValueError):
                pass                    # bozuk JSON -> deterministik yola DUS
        # AI basarisiz: urun DUSMEZ, asagidaki deterministik yol calisir.
    if not galeri:
        return None, None, "gorsel yok — deterministik ureteç calistirilamaz"
    o = uret(meta, galeri, kategoriler, urunler_yolu=urunler_yolu)
    try:
        with open(onerip, "w", encoding="utf-8") as f:
            json.dump(o, f, ensure_ascii=False)
    except OSError as e:
        return None, None, "oneri.json yazilamadi: %s" % e
    return o, KAYNAK_DET, "deterministik icerik"

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATA-LISANS KAPISI — turev kaydin ATA ZINCIRINI, ata BAGLANTISININ HOST'undan cozer.

NEDEN VAR (kok neden, 4 canli emsalle olculdu — hicbir test kirmizi yanmadi):
Bir kaynak platformdaki TUREV kayit, atasinin lisansini KENDI JSON'unda GOSTERMIYOR:
ata referansinin `license` alani BOS ve kimlik 0 geliyor; tek gercek sinyal serbest-metin
`link` URL'sidir. Ata lisansi ANCAK o URL'den HOST + KIMLIK cikarilip O PLATFORMUN kendi
API'sine gidilerek cozuluyor. Dort canli emsalde de ata CC ...-NC / -NC-SA cikti = SATILAMAZ.
Yukleyicinin turevi "CC0" diye YENIDEN LISANSLAMASI GECERSIZ: NC atadan turetilen eser NC kalir.

🔴 OLCULEN BOSLUK: depodaki lisans kapilarinin HEPSI kaynak-platform-ICI bakar
(kayit['lisans'] -> o platformun satilabilir()'i). Ata ZINCIRI hicbir kapinin ekseninde DEGIL:
`originals` / `remixParents` / `derivedFrom` / `ancestors` / `originalDesigns` / `remixOf`
jetonlarinin HICBIRI 5 platform adaptorunun HICBIRINDE gecmiyor (grep: 0/5 isabet).

═══════════════════════════════════════════════════════════════════════════════
SESSIZ-GECIS ONARIMLARI (bagimsiz curutucu 12 delik olctu — hepsi rc=0 ile geciyordu)
═══════════════════════════════════════════════════════════════════════════════
  D1  turev detayi None (404/silinmis/gizli kayit) -> ATA-YOK -> rc 0.  ARTIK: KALICI.
  D2  ata alani listesi TEK ada bakiyordu -> 5 alan adi hic taranmiyordu. ARTIK: 6 ad.
  D3  ata alani dict/string ise ATLANIYORDU; zarfli detay (`{"data":{...}}`) gorulmuyordu;
      BOS detay (`{}`) "ata yok" sayiliyordu. ARTIK: ucu de coz ya da fail-closed.
  D4  tek serbest-metin alanindaki IKINCI URL hic bakilmiyordu. ARTIK: hepsi cozulur.
  D5  IKI KADEMELI zincir (ata BY, atanin atasi NC) cozulmuyordu ve BEYAN da edilmemisti.
      ARTIK: derinlik tavanina (3) kadar OZYINELEME + dongu korumasi; tavan asilirsa KALICI.
  D6  gomulu lisans TEK sozlukle yargilaniyordu -> gecerli CC yazimlari IHLAL damgasi
      yiyordu (yanlis-pozitif). ARTIK: NC/tescilli VETO + COK-SOZLUK tanima birlesimi.
  D7  okuma-timeout'u KALICI kovasina dusuyordu. ARTIK: GECICI (yeniden denenebilir).
  D8  KAPSAM-DISI tek kovaydi: "alan YOK (olculdu)" ile "BAKMADIK" ayni yerdeydi.
      ARTIK: ALAN-YOK(olculdu) vs OLCULMEDI(bakilmadi) AYRI; ikincisi asla temiz sayilmaz
      ve kuru kosumun cikis kodunu 2'ye ceker.
  D9  ATA-YOK erken donusunde urun kimligi set edilmiyordu -> kayit raporda IZLENEMEZDI.
  D10 zincir dongusu hukum uretmeden bosa duserse rc 0 olurdu. ARTIK: KALICI.
  D11 ata detayi zarf acildiktan sonra BOS/taninmayan sekilse gecerdi. ARTIK: KALICI.
  D12 bozuk JSON gecici sayiliyordu. ARTIK: KALICI (yeniden deneme fayda etmez).

═══════════════════════════════════════════════════════════════════════════════
IKINCI TUR — "ALAN-YOK" IDDIASININ KENDISI OLCULMEMISTI (D13..D18 + V1)
═══════════════════════════════════════════════════════════════════════════════
ALAN-YOK bir OLCUM IDDIASIDIR: gerekce metni "detay OLCULDU: ata alani yok" DER. Bagimsiz
curutucu bu iddianin YANLIS oldugu 5 vaka olctu (hepsi rc=0 ile geciyordu). Vakalar bugun
TARANAN tek platformda (ata_destegi=True) ERISILMEZ — cunku o platformun JSON sekli CANLI
olculdu — ama ata_destegi HERHANGI bir platformda sekil OLCULMEDEN True'ya cevrildigi an
SESSIZ FAIL-OPEN olurlar. Onarim: ALAN-YOK artik VARSAYILMAZ, KANITLANIR.
  D13 zarf derinlik tavani 3'tu: 4 kademeli zarf ({"data":{"result":{"response":{"payload":
      {"originals":[...]}}}}}) HIC acilmiyordu -> ALAN-YOK. ARTIK tavan ZARF_TAVANI ve
      tavan ASILIRSA fail-closed SEKIL (ALAN-YOK DEGIL).
  D14 ayni duzeyde IKI zarf anahtari (ör. hem "data" hem "model" dict) -> eski kod
      `len(icler) != 1` ile DIS sozlugu donuyordu -> ata alani gorulmuyor -> ALAN-YOK.
      ARTIK: BELIRSIZ zarf = fail-closed SEKIL ("hangisi govde OLCULMEDI").
  D15 ata alan adlari TAM ESLESME ile araniyordu ("Originals" gorulmuyordu).
  D16 ayni korluk ayrac/yazim varyantinda ("remixparents").
  D17 ayni korluk buyuk harfte ("REMIXOF").
      ARTIK: ad NORMALIZASYONU (buyuk-kucuk + ayrac duyarsiz) — TEK kanonik fonksiyon
      (`_ad`) hem tarama hem zarf ekseninde kullanilir ([[ikiz-tanim-sessiz-ayrisma]]).
      🔴 6 addan YALNIZ "originals" CANLI olculdu; kalan 5'i TAHMINDIR — yeni platformda
      yazim varyanti CANLI RISKTIR.
  D18 taninmayan/olculmemis sekildeki HER detay ALAN-YOK sayiliyordu ("olculdu" YALANI).
      ARTIK: ALAN-YOK yalniz detay TANINAN bir govde ise (GOVDE_ALANLARI isareti tasiyorsa)
      verilir; taninmayan sekil -> COZULEMEDI-SEKIL (rc 1).
  V1  lisans VETOSU duz alt-dizi ariyordu: "exclusive" jetonu yuzunden TAM METIN CC lisanslari
      ("... worldwide, royalty-free, non-exclusive ...") veto yiyordu (yanlis-pozitif; yon
      fail-closed ama yayin durdurur). ARTIK: "non-exclusive" onek muafiyetli desen; tescilli
      "Exclusive License" VETO'da KALIR.

FAIL-CLOSED YON (supheli = satilamaz):
  * host'un adaptoru YOK        -> COZULEMEDI-ADAPTORSUZ (ELLE-BAK kuyruguna) -> rc 1
  * detay sekli TANINMADI       -> COZULEMEDI-SEKIL (ELLE-BAK; sekli OLC)     -> rc 1
  * kimlik/sekil/null/403/bozuk -> COZULEMEDI-KALICI (eskalasyon)             -> rc 1
  * 429 / 5xx / timeout         -> OLCULEMEDI-GECICI (yeniden denenebilir)    -> rc 2
  * ata lisansi satilamaz       -> IHLAL                                      -> rc 1
  GECICI ile KALICI AYRI raporlanir. "Sessizce gecirme" hali YOKTUR.

KAPI DAVRANISI — VERI YAZMAZ: rapor kipi TEK kiptir; urunler.json / gizli kaynak kaydi /
D1 hicbirine dokunmaz, silme UYGULAMAZ. Cikti STDOUT.

CIKIS KODU:  0 = ihlal yok VE her sey olculdu · 1 = ihlal/fail-closed VAR ·
             2 = OLCULEMEDI (gecici hata ya da OLCULMEMIS kapsam kaldi; yesil SAYILMAZ)

MEVCUT YUZEYIN UZERINE KURULUR (yeniden yazilmadi): her platformun `satilabilir()` yargisi
KENDI adaptorundedir ve BURADAN CAGRILIR; serbest-metin lisanslar icin denetim-kapisi.py'nin
GENEL normalizeri (lisans_kisaltma) + printables beyaz listesi zinciri kullanilir.

Kullanim:
    python3 tools/ata-lisans-kapisi.py --kendini-test      # offline oz-denetim (CI kolu)
    python3 tools/ata-lisans-kapisi.py --fikstur <yol>     # agsiz, fikstur uzerinden
    python3 tools/ata-lisans-kapisi.py --kuru-kosum [--limit N] [--kaynak <ad>]   # AG ISTER
"""
import argparse
import collections
import importlib.util
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))


def _yukle(dosya_adi, modul_adi):
    """tools/ altindaki tireli dosyayi modul olarak yukler (repo geneli desen)."""
    yol = os.path.join(_HERE, dosya_adi)
    spec = importlib.util.spec_from_file_location(modul_adi, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- durumlar / hatalar
DURUM_ALAN_YOK = "ALAN-YOK"            # OLCULDU: detay cekildi, ata alani gercekten yok
DURUM_SATILABILIR = "SATILABILIR"
DURUM_IHLAL = "IHLAL"
DURUM_ADAPTORSUZ = "COZULEMEDI-ADAPTORSUZ"
DURUM_KALICI = "COZULEMEDI-KALICI"
DURUM_GECICI = "OLCULEMEDI-GECICI"
# 🔴 D18: detayin SEKLI taninmadi -> "ata alani yok" DENEMEZ (iddia olculmemistir).
# Yeniden deneme fayda etmez; cozum SEKLI OLCMEKTIR -> ELLE-BAK kuyruguna, rc 1.
DURUM_SEKIL = "COZULEMEDI-SEKIL"

IHLAL_DURUMLARI = (DURUM_IHLAL, DURUM_ADAPTORSUZ, DURUM_KALICI, DURUM_SEKIL)   # rc 1
OLCULEMEDI_DURUMLARI = (DURUM_GECICI,)                                         # rc 2

# Zincir kac kademe yukari cikilir (ata -> atanin atasi -> ...). Tavan ASILIRSA fail-closed.
DERINLIK_TAVANI = 3

# Detay JSON'u kac ZARF kademesi acilir. Tavan ASILIRSA fail-closed (D13).
ZARF_TAVANI = 6


class GeciciHata(Exception):
    """429 / 5xx / timeout / ag — YENIDEN DENENEBILIR (kalici degil)."""


class KaliciHata(Exception):
    """401/403/kimlik/sekil/bozuk JSON — ESKALASYON (yeniden denemek fayda etmez)."""


# ---------------------------------------------------------------- adaptor kaydi
Adaptor = collections.namedtuple(
    "Adaptor", "ad hostlar kimlik_cikar detay lisans_cikar satilabilir ata_destegi")


def host_coz(url):
    """URL -> normalize host ('www.' oneki ve port atilir). URL degilse None.

    HOST BU KAPININ TEK YENI EKSENIDIR: ata lisansi yalnizca dogru host'un adaptoruyle
    cozulebilir; host okunmazsa turevin KENDI platformunun lisansi ata sanilir (sessiz hata)."""
    if not isinstance(url, str):
        return None
    s = url.strip()
    if not s:
        return None
    if "//" not in s:
        s = "https://" + s
    try:
        net = urllib.parse.urlparse(s).netloc
    except ValueError:
        return None
    net = (net or "").split("@")[-1].split(":")[0].strip().lower()
    if not net or "." not in net:
        return None
    if net.startswith("www."):
        net = net[4:]
    return net


def adaptor_bul(host, defter):
    """host -> Adaptor ya da None (adaptorsuz = fail-closed ELLE-BAK).

    MUTASYON ANCHOR: bu eslemenin host'u YOK SAYAN her varyanti kabul testini KIRMIZI yakar."""
    if not host:
        return None
    for a in defter:
        for h in a.hostlar:
            if host == h or host.endswith("." + h):
                return a
    return None


# ---------------------------------------------------------------- LISANS YARGISI
# NC ve tescilli/kapali ifadeler HER YAZIMDA veto eder (fail-closed cekirdek). Veto,
# tanima birlesiminden ONCE calisir; boylece "tanima genis" olmasi NC'yi ASLA gecirmez.
_NC_METIN = ("noncommercial", "non-commercial", "non commercial", "not for commercial",
             "no commercial")
_TESCILLI_METIN = ("standard digital file", "all rights reserved",
                   "community use", "personal use", "private use", "ocl v",
                   "official content", "premium")
# 🔴 V1: "exclusive" ALT-DIZI olarak arandiginda TAM METIN lisanslari veto ediyordu —
# "non-exclusive" ibaresi HER standart CC/royalty-free tam metninde gecer ("... a worldwide,
# royalty-free, non-exclusive license ..."). Tescilli olan "Exclusive License"tir, "non-
# exclusive" DEGILDIR. Onek muafiyeti + kelime siniri ile ayrilir; "MakerWorld Exclusive
# License" VETO'da KALIR. (Kalan tescilli ibareler bilerek genis birakildi: yon fail-closed.)
_TESCILLI_DESEN = (re.compile(r"(?<!non)(?<!non[ -])\bexclusive\b"),)


def lisans_vetosu(ham):
    """NC / tescilli-kapali lisans mi? True -> HICBIR sozluk bunu satilabilir yapamaz."""
    if not isinstance(ham, str):
        return True
    s = ham.strip().lower()
    if not s:
        return True
    if any(t in s for t in _NC_METIN):
        return True
    if any(t in s for t in _TESCILLI_METIN):
        return True
    if any(d.search(s) for d in _TESCILLI_DESEN):
        return True
    toks = [t for t in re.split(r"[^a-z0-9]+", s) if t]
    if "nc" in toks:
        return True
    # 🔴 V1 — BITISIKLIK SARTI: "non" ve "commercial" jetonlari YAN YANA olmali. Kume uyeligi
    # (ikisi de metnin HERHANGI bir yerinde) TAM METIN lisanslari veto ediyordu:
    # "... non-exclusive, worldwide, royalty-free; commercial use permitted ..." -> "non" +
    # "commercial" VAR ama lisans SATILABILIR (olculdu). Yan yana sarti ayractan BAGIMSIZ
    # olarak NC'yi yakalamaya devam eder: "non-commercial", "non–commercial", "non_commercial".
    if any(a == "non" and b == "commercial" for a, b in zip(toks, toks[1:])):
        return True
    return False


def satilabilir_ile(ham, yargi):
    """TEK sozluk yargisi + veto (ata API'sinden cozulen lisans icin: sozluk BILINIYOR)."""
    if not ham:
        return False
    if lisans_vetosu(ham):
        return False
    return bool(yargi(ham))


def coklu_sozluk_satilabilir(ham, kaynak_adaptor=None):
    """GOMULU lisans alani icin: sozluk BILINMIYOR (platformlar ayni alana ciplak CC,
    onekli kisaltma ya da insan-okur ad yaziyor). VETO once (NC asla gecmez), sonra
    TANIMA BIRLESIMI (herhangi bir sozluk tanirsa satilabilir).

    🔴 CANLI OLCUM: tek sozlukle yargilaninca "BY-SA", "Creative Commons Attribution 4.0",
    "Attribution 4.0 International" gibi GECERLI lisanslar satilamaz sanildi (yanlis-pozitif;
    250 kayitlik kuru kosumda 13 vurus). Yanlis-pozitif tum ekibin yayinini durdurur."""
    if not ham:
        return False
    if lisans_vetosu(ham):
        return False
    yargilar = [yargi_kaynagi("ciplak-cc"), yargi_kaynagi("kisaltma"),
                yargi_kaynagi("insan-adi"), genel_satilabilir]
    if kaynak_adaptor is not None:
        yargilar.insert(0, kaynak_adaptor.satilabilir)
    for j in yargilar:
        try:
            if j(ham):
                return True
        except Exception:                                           # noqa: BLE001
            continue
    return False


# ---------------------------------------------------------------- ata referanslarini cikar
# Turev kaydin detay JSON'unda ata listesi bu alanlardan birinde durur. Platformlar ayni
# kavrama farkli ad veriyor; TEK ada bakmak sessiz gecistir (olculdu).
ATA_ALANLARI = ("originals", "remixParents", "derivedFrom", "ancestors",
                "originalDesigns", "remixOf")

# Detay bazen zarfli gelir: {"data": {...}} / {"result": {...}}. Zarf acilmazsa ata alani
# GORULMEZ ve kayit sessizce "ata yok" sayilir.
ZARF_ANAHTARLARI = ("data", "result", "response", "payload", "design", "model")

# 🔴 D18: "ata alani yok" bir OLCUM IDDIASIDIR ve ancak detayin GOVDE oldugu TANINIRSA
# verilebilir. Bu isaretler 4 canli adaptorun detay JSON'larinda GECEN alanlardir
# (mw: id/title/license/coverUrl/instances · pr: id/name/license/stls ·
#  c3: name/url/shortUrl/license/illustrationImageUrl · mmf: id/name/license/designer/images).
# Hicbiri yoksa detay ya zarftir ya da SEKLI OLCULMEMISTIR -> fail-closed.
GOVDE_ALANLARI = ("license", "licence", "id", "title", "name", "slug", "url", "shortUrl",
                  "description", "summary", "designId", "modelId", "cover", "coverUrl",
                  "images", "pictures", "instances", "files", "stls", "designer",
                  "author", "creator", "username", "tags", "category", "createdAt",
                  "publishedAt")

_URL_RE = re.compile(r"https?://[^\s,;<>\"'\)\]}]+", re.IGNORECASE)
_AD_TEMIZ = re.compile(r"[^a-z0-9]+")


def _ad(anahtar):
    """JSON alan adini KANONIK bicime indirger: buyuk-kucuk ve ayrac (_ - bosluk) duyarsiz.

    🔴 TEK KANONIK FONKSIYON: alan tarama (ata_kayitlari), zarf inisi ve govde tanima
    AYNI normalizeri kullanir; ikiz tanim sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]])."""
    return _AD_TEMIZ.sub("", str(anahtar).lower())


_ATA_N = frozenset(_ad(a) for a in ATA_ALANLARI)
_ZARF_N = frozenset(_ad(z) for z in ZARF_ANAHTARLARI)
_GOVDE_N = frozenset(_ad(g) for g in GOVDE_ALANLARI)
_ATA_SIRA = {_ad(a): i for i, a in enumerate(ATA_ALANLARI)}


def ata_anahtarlari(d):
    """Sozlukteki GERCEK ata alan adlari (yazim varyantlari dahil), kanonik sirada.

    🔴 D15/D16/D17: eski kod TAM ESLESME ariyordu; "Originals" / "remixparents" / "REMIXOF"
    GORUNMUYOR ve kayit sessizce ALAN-YOK oluyordu."""
    if not isinstance(d, dict):
        return []
    varlar = [k for k in d if _ad(k) in _ATA_N]
    return sorted(varlar, key=lambda k: (_ATA_SIRA.get(_ad(k), 99), str(k)))


def _govde_mi(d):
    """Detay sozlugu TANINAN bir kayit govdesi mi? (ALAN-YOK'un ON KOSULU — D18)"""
    return isinstance(d, dict) and any(_ad(k) in _GOVDE_N for k in d)


def _zarf_ac(detay, tavan=ZARF_TAVANI):
    """Zarfli detay JSON'unu acar. Doner (govde, hata|None, govde_gorundu).

    hata DOLU ise FAIL-CLOSED (hukum VERILMEZ). govde_gorundu = inilen yol uzerinde EN AZ BIR
    kademenin TANINAN govde oldugu; ALAN-YOK'un ON KOSULUDUR (D18).

    Sira her kademede: (1) ata alani BURADA mi -> bittik · (2) govde izi kaydedilir ·
    (3) tek zarf cocuguna inilir. Tavan asilirsa ya da ayni duzeyde BIRDEN COK zarf cocugu
    varsa hukum VERILMEZ: eski kod ikisinde de sessizce disaridaki sozlugu donuyor ve kayit
    ALAN-YOK sayiliyordu (D13/D14).

    🔴 GOVDE ISARETI INISI DURDURMAZ: {"id":1,"title":"x","data":{"originals":[...]}} gibi
    HEM govde isareti tasiyan HEM zarflayan detayda erken durmak, ata alanini yeniden
    gorunmez yapardi (ilk onarim denemesinde olculdu)."""
    d = detay
    n = 0
    govde_gorundu = False
    while isinstance(d, dict) and d:
        if ata_anahtarlari(d):
            return d, None, True                  # ata alani BULUNDU: iz aramaya gerek yok
        govde_gorundu = govde_gorundu or _govde_mi(d)
        icler = [d[k] for k in d if _ad(k) in _ZARF_N and isinstance(d[k], dict)]
        if len(icler) > 1:
            return d, ("detay zarfi BELIRSIZ: ayni duzeyde %d ic sozluk — govde OLCULMEDI"
                       % len(icler)), govde_gorundu
        if not icler:
            return d, None, govde_gorundu         # zarf bitti; hukmu cagiran verir (D18)
        if n >= tavan:
            return d, ("detay zarfi %d kademeden derin (tavan %d) — govde ACILAMADI"
                       % (n + 1, tavan)), govde_gorundu
        d = icler[0]
        n += 1
    return d, None, govde_gorundu


def urlleri_cikar(metin):
    """Serbest-metin alandaki TUM URL'ler. Tek alanda birden fazla ata baglantisi olabilir;
    yalniz ILKINE bakmak sessiz gecistir (olculdu)."""
    if not isinstance(metin, str) or not metin.strip():
        return []
    bulunan = [u.rstrip(".,);]}'\"") for u in _URL_RE.findall(metin)]
    if bulunan:
        return bulunan
    t = metin.strip()
    return [t] if host_coz(t) else []


def _referans_ac(el, alan):
    """Tek ata elemanindan (dict | str | taninmayan) normalize referans(lar)."""
    if isinstance(el, dict):
        metin = str(el.get("link") or el.get("url") or el.get("href") or "")
        lis = str(el.get("license") or el.get("licence") or "")
        kim = el.get("designId", el.get("id"))
    elif isinstance(el, str):
        metin, lis, kim = el, "", None
    else:
        return [{"link": "", "license": "", "kimlik_alani": None, "alan": alan,
                 "_sekil_hatasi": "ata elemani TANINMAYAN sekilde (%s)" % type(el).__name__}]
    urller = urlleri_cikar(metin)
    if not urller:
        return [{"link": "", "license": lis, "kimlik_alani": kim, "alan": alan}]
    return [{"link": u, "license": lis, "kimlik_alani": kim, "alan": alan} for u in urller]


def ata_kayitlari(detay):
    """Detay JSON'undan (referanslar, sekil_hatalari). Sekil hatasi = fail-closed gerekce."""
    if not isinstance(detay, dict):
        return [], ["detay sekli taninmiyor (%s)" % type(detay).__name__]
    refs, hatalar = [], []
    for alan in ata_anahtarlari(detay):
        ham = detay[alan]
        if ham is None or ham == "" or ham == [] or ham == {}:
            continue                                    # alan var ama BOS -> ata yok
        if isinstance(ham, list):
            elemanlar = ham
        elif isinstance(ham, (dict, str)):
            elemanlar = [ham]                           # tekil sekil de COZULUR, atlanmaz
        else:
            hatalar.append("ata alani '%s' TANINMAYAN sekilde (%s)" % (alan, type(ham).__name__))
            continue
        for el in elemanlar:
            refs.extend(_referans_ac(el, alan))
    return refs, hatalar


# ---------------------------------------------------------------- yargi
def _sonuc(durum, gerekce, ata=None, host=None, kimlik=None, lisans=None, adaptor=None,
           derinlik=1):
    return {
        "durum": durum,
        "gerekce": gerekce,
        "ata_link": (ata or {}).get("link", ""),
        "ata_alan": (ata or {}).get("alan"),
        "host": host,
        "ata_kimlik": kimlik,
        "ata_lisans": lisans,
        "adaptor": adaptor,
        "derinlik": derinlik,
    }


def ata_yargi(ata, defter, gs, kaynak_adaptor=None, derinlik=1, gorulen=None):
    """TEK ata referansi + ONUN ATALARI icin yargi LISTESI (zincir yukari).

    kaynak_adaptor: ata referansini BASAN platformun adaptoru (gomulu lisans onun
    sozlugunde yazilabilir; ama sozluk garanti DEGIL -> coklu sozluk yargisi)."""
    gorulen = gorulen if gorulen is not None else set()

    if ata.get("_sekil_hatasi"):
        return [_sonuc(DURUM_KALICI, ata["_sekil_hatasi"], ata, derinlik=derinlik)]

    link = (ata.get("link") or "").strip()
    gomulu = (ata.get("license") or "").strip()

    # 1) Gomulu lisans DOLU ve SATILAMAZ ise ag'a cikmadan ihlal (siki yon).
    #    DOLU ve satilabilir ise hukum VERILMEZ -> host cozumlemesi yine kosar.
    if gomulu and not coklu_sozluk_satilabilir(gomulu, kaynak_adaptor):
        return [_sonuc(DURUM_IHLAL, "ata referansindaki lisans satilamaz (gomulu alan)",
                       ata, host_coz(link), None, gomulu, derinlik=derinlik)]

    if not link:
        return [_sonuc(DURUM_KALICI, "ata baglantisi YOK; host okunamiyor", ata,
                       derinlik=derinlik)]

    host = host_coz(link)
    if not host:
        return [_sonuc(DURUM_KALICI, "ata baglantisi URL olarak ayristirilamadi", ata,
                       derinlik=derinlik)]

    adaptor = adaptor_bul(host, defter)
    if adaptor is None:
        return [_sonuc(DURUM_ADAPTORSUZ, "bu host icin adaptor YOK -> ELLE-BAK", ata, host,
                       derinlik=derinlik)]

    kimlik = adaptor.kimlik_cikar(link)
    if not kimlik:
        return [_sonuc(DURUM_KALICI, "host taniniyor ama kimlik cikarilamadi",
                       ata, host, None, None, adaptor.ad, derinlik)]

    anahtar = (host, str(kimlik))
    if anahtar in gorulen:
        return []                                       # dongu: bu dugum zaten yargilandi
    gorulen.add(anahtar)

    try:
        detay = adaptor.detay(kimlik)
    except GeciciHata as e:
        return [_sonuc(DURUM_GECICI, "gecici API hatasi: %s" % e, ata, host, kimlik, None,
                       adaptor.ad, derinlik)]
    except KaliciHata as e:
        return [_sonuc(DURUM_KALICI, "kalici API hatasi: %s" % e, ata, host, kimlik, None,
                       adaptor.ad, derinlik)]

    if detay is None:
        return [_sonuc(DURUM_KALICI, "API null dondu (kayit yok/erisilemez)",
                       ata, host, kimlik, None, adaptor.ad, derinlik)]

    detay, zarf_hatasi, _iz = _zarf_ac(detay)
    if zarf_hatasi:
        return [_sonuc(DURUM_SEKIL, "ata detayi: " + zarf_hatasi,
                       ata, host, kimlik, None, adaptor.ad, derinlik)]
    if not isinstance(detay, dict) or not detay:
        return [_sonuc(DURUM_KALICI, "ata detayi BOS ya da taninmayan sekilde",
                       ata, host, kimlik, None, adaptor.ad, derinlik)]

    lisans_metni = (adaptor.lisans_cikar(detay) or "").strip()
    if not lisans_metni:
        return [_sonuc(DURUM_KALICI, "ata lisansi BOS dondu", ata, host, kimlik, "",
                       adaptor.ad, derinlik)]

    if not satilabilir_ile(lisans_metni, adaptor.satilabilir):
        return [_sonuc(DURUM_IHLAL, "ATA LISANSI SATILAMAZ (turevin yeniden-lisansi gecersiz)",
                       ata, host, kimlik, lisans_metni, adaptor.ad, derinlik)]

    out = [_sonuc(DURUM_SATILABILIR, "ata lisansi ticari satisa uygun",
                  ata, host, kimlik, lisans_metni, adaptor.ad, derinlik)]

    # --- UST KADEME (zincir): atanin kendi atalari da yargilanir ---
    ustler, sekil_hatalari = ata_kayitlari(detay)
    if ustler or sekil_hatalari:
        if derinlik >= DERINLIK_TAVANI:
            out.append(_sonuc(DURUM_KALICI,
                              "zincir DERINLIK TAVANINA takildi (%d) — zincir TAMAMLANMADI"
                              % DERINLIK_TAVANI, ata, host, kimlik, lisans_metni,
                              adaptor.ad, derinlik))
            return out
        for h in sekil_hatalari:
            out.append(_sonuc(DURUM_KALICI, "ust kademe: " + h, ata, host, kimlik, None,
                              adaptor.ad, derinlik + 1))
        for ust in ustler:
            out.extend(ata_yargi(ust, defter, gs, adaptor, derinlik + 1, gorulen))
    return out


def kayit_yargi(urun_id, detay, defter, gs, kaynak_adaptor=None):
    """Bir turev kaydin TUM ata zincirinin yargisi -> sonuc dict listesi.

    🔴 Detay dogrulamasi BURADADIR: None / dict-degil / (zarf acildiktan sonra) BOS
    detay ARTIK 'ata yok' SAYILMAZ — fail-closed KALICI.

    🔴 D18: ALAN-YOK bir OLCUM IDDIASIDIR; yalniz detay TANINAN bir govde ise verilir.
    Taninmayan sekil -> DURUM_SEKIL (fail-closed) — 'olculdu' DIYE YALAN SOYLENMEZ."""
    if detay is None:
        out = [_sonuc(DURUM_KALICI, "turev detayi YOK (API null / kayit silinmis-gizli)")]
    elif not isinstance(detay, dict):
        out = [_sonuc(DURUM_KALICI, "turev detayi taninmayan sekilde (%s)"
                      % type(detay).__name__)]
    else:
        acik, zarf_hatasi, govde_gorundu = _zarf_ac(detay)
        if zarf_hatasi:
            out = [_sonuc(DURUM_SEKIL, "turev detayi: " + zarf_hatasi)]
        elif not isinstance(acik, dict) or not acik:
            out = [_sonuc(DURUM_KALICI, "turev detayi BOS (zarf acildiktan sonra da)")]
        else:
            atalar, sekil_hatalari = ata_kayitlari(acik)
            out = [_sonuc(DURUM_KALICI, h) for h in sekil_hatalari]
            if not atalar and not sekil_hatalari:
                if govde_gorundu:
                    out = [_sonuc(DURUM_ALAN_YOK, "detay OLCULDU (govde TANINDI): ata alani yok")]
                else:
                    out = [_sonuc(DURUM_SEKIL,
                                  "turev detayi TANINMAYAN sekilde (govde isareti yok) — "
                                  "'ata alani yok' DENEMEZ; bu platformun sekli OLCULMEMIS")]
            else:
                gorulen = set()
                for ata in atalar:
                    out.extend(ata_yargi(ata, defter, gs, kaynak_adaptor, 1, gorulen))
    if not out:
        # zincir dongusu hukum uretmeden bosa dustu -> fail-closed
        out = [_sonuc(DURUM_KALICI, "zincir hukum URETMEDI (dongu) — fail-closed")]
    for s in out:
        s["urun"] = urun_id                     # her sonuc IZLENEBILIR olmali (ALAN-YOK dahil)
    return out


def cikis_kodu(sonuclar, kapsam=None):
    """0 ihlal yok VE her sey olculdu · 1 ihlal/fail-closed · 2 OLCULEMEDI (yesil sayilmaz).

    kapsam verilirse OLCULMEMIS kayitlar da 2'ye ceker: "bakmadigimiz kayit temiz degildir"."""
    durumlar = [s["durum"] for s in sonuclar]
    if any(d in IHLAL_DURUMLARI for d in durumlar):
        return 1
    if any(d in OLCULEMEDI_DURUMLARI for d in durumlar):
        return 2
    if kapsam and (kapsam.get("olculmedi_adaptorlu") or kapsam.get("olculmedi_adaptorsuz")
                   or kapsam.get("taranmadi")):
        return 2
    return 0


# ---------------------------------------------------------------- HTTP yardimcilari
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124 Safari/537.36")


def _http_hata_cevir(e):
    """urllib istisnasini GeciciHata/KaliciHata'ya cevirir (404 -> None ayri ele alinir)."""
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (429, 500, 502, 503, 504):
            return GeciciHata("HTTP %s" % e.code)
        return KaliciHata("HTTP %s" % e.code)
    return GeciciHata("ag hatasi: %s" % type(e).__name__)


def _json_get(url, basliklar=None):
    """JSON GET; 404 -> None. Bozuk JSON KALICI, ag/timeout GECICI."""
    h = {"Accept": "application/json", "User-Agent": _UA}
    h.update(basliklar or {})
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ham = r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise _http_hata_cevir(e)
    except (socket.timeout, TimeoutError):
        raise GeciciHata("okuma timeout")
    except Exception as e:                                          # noqa: BLE001
        raise _http_hata_cevir(e)
    try:
        return json.loads(ham)
    except ValueError:
        raise KaliciHata("bozuk JSON")


def _sarmala(fn, *a, **kw):
    """Var olan adaptor cagrisini Gecici/Kalici siniflandirmasina sarar.

    🔴 SIRA ONEMLI: HTTPError/URLError, OSError'in ALT sinifidir — once onlar yakalanir.
    Timeout/OSError GECICI'dir (yeniden denenebilir); bozuk veri/deger hatasi KALICI."""
    try:
        return fn(*a, **kw)
    except (GeciciHata, KaliciHata):
        raise
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise _http_hata_cevir(e)
    except urllib.error.URLError:
        raise GeciciHata("ag hatasi: URLError")
    except (socket.timeout, TimeoutError):
        raise GeciciHata("okuma timeout")
    except ValueError:
        raise KaliciHata("bozuk JSON / gecersiz deger")
    except OSError as e:
        raise GeciciHata("ag/GC hatasi: %s" % type(e).__name__)
    except Exception as e:                                          # noqa: BLE001
        raise KaliciHata("%s: %s" % (type(e).__name__, e))


# ---------------------------------------------------------------- kimlik cikaricilar
_SON_SAYI = re.compile(r"(\d+)")


def _yol_parcalari(url):
    try:
        yol = urllib.parse.urlparse(url if "//" in url else "https://" + url).path
    except ValueError:
        return []
    return [p for p in yol.split("/") if p]


def _kimlik_bas_sayi(url, isaret):
    """.../<isaret>/<sayi>-<slug> -> sayi (bas taraftaki rakam blogu)."""
    p = _yol_parcalari(url)
    for i, parca in enumerate(p):
        if parca.lower() == isaret and i + 1 < len(p):
            m = re.match(r"(\d+)", p[i + 1])
            if m:
                return m.group(1)
    return None


def _kimlik_son_sayi(url, isaret):
    """.../<isaret>/<slug>-<sayi> -> son rakam blogu."""
    p = _yol_parcalari(url)
    for i, parca in enumerate(p):
        if parca.lower() == isaret and i + 1 < len(p):
            hepsi = _SON_SAYI.findall(p[i + 1])
            if hepsi:
                return hepsi[-1]
    return None


def _kimlik_slug(url, isaret):
    """.../<isaret>/.../<slug> -> son yol parcasi (sorgu/hash atilmis)."""
    p = _yol_parcalari(url)
    if isaret not in [x.lower() for x in p]:
        return None
    return p[-1].split("?")[0].split("#")[0] or None


def _kimlik_thing(url):
    """.../thing:<sayi>  VE  .../things/<sayi> (API bicimi) -> sayi.

    🔴 CANLI KURU KOSUMDA OLCULDU: ata baglantisi bazen SITE bicimiyle degil API bicimiyle
    (`.../things/<sayi>`) yazilmis geliyor. Tek bicim taninirsa kimlik cikmaz ve kayit
    gereksiz yere ELLE-BAK kuyruguna duser (fail-closed ama COZULEBILIR bir vaka)."""
    parcalar = _yol_parcalari(url)
    for i, parca in enumerate(parcalar):
        m = re.match(r"thing:(\d+)", parca, re.IGNORECASE)
        if m:
            return m.group(1)
        if parca.lower() in ("things", "thing") and i + 1 < len(parcalar):
            m2 = re.match(r"(\d+)", parcalar[i + 1])
            if m2:
                return m2.group(1)
    return None


# ---------------------------------------------------------------- URETIM DEFTERI
_ONBELLEK = {}


def _modul(dosya, ad):
    if ad not in _ONBELLEK:
        _ONBELLEK[ad] = _yukle(dosya, ad)
    return _ONBELLEK[ad]


def genel_satilabilir(ham):
    """ADAPTORSUZ / serbest-metin lisans yargisi — MEVCUT zincir (kopya DEGIL):
    denetim-kapisi.lisans_kisaltma() ile normalize + printables satilabilir() beyaz listesi."""
    dk = _modul("denetim-kapisi.py", "ata_denetim_kapisi")
    pr = _modul("printables-api.py", "ata_printables_api")
    return bool(pr.satilabilir(dk.lisans_kisaltma(ham)))


def yargi_kaynagi(etiket):
    """Lisans SOZLUGUNE gore yargi fonksiyonu (var olanlar; kopya YOK). Etiketler platform
    adi DEGIL, lisans YAZIM BICIMIDIR:
      'ciplak-cc' : CC'yi ciplak yazan sozluk ("BY", "BY-SA", "CC0")
      'kisaltma'  : onekli kisaltma sozlugu ("CC-BY", "GPL 3.0")
      'insan-adi' : insan-okur ad sozlugu ("Attribution 4.0 International")
      'genel'     : normalize + kisaltma zinciri (fallback)"""
    if etiket == "ciplak-cc":
        return _modul("makerworld-api.py", "ata_makerworld_api").satilabilir
    if etiket == "kisaltma":
        return _modul("printables-api.py", "ata_printables_api").satilabilir
    if etiket == "insan-adi":
        return _modul("cults3d-api.py", "ata_cults3d_api").satilabilir
    return genel_satilabilir


def _veri_kok():
    vk = _modul("veri_kok.py", "ata_veri_kok")
    _kod, veri, _uyari = vk.cozumle(os.path.join(_HERE, "ata-lisans-kapisi.py"))
    return veri


def uretim_defteri():
    """Canli adaptor defteri. TEMBEL kurulur (import/anahtar maliyeti kosum aninda).

    🔴 `ata_destegi`: ata alaninin O PLATFORMDA CANLI OLCULDUGU anlamina gelir. False olan
    platformlarin kayitlari 'temiz' DEGIL, 'OLCULMEDI'dir (bkz. kapsam_bolumle)."""
    mw = _modul("makerworld-api.py", "ata_makerworld_api")
    pr = _modul("printables-api.py", "ata_printables_api")
    c3 = _modul("cults3d-api.py", "ata_cults3d_api")
    mmf = _modul("myminifactory-api.py", "ata_myminifactory_api")

    def _tv_detay(kimlik):
        kok = _veri_kok()
        tok_yol = os.path.join(kok, ".thingiverse-token")
        if not os.path.exists(tok_yol):
            raise KaliciHata("token dosyasi yok")
        tok = open(tok_yol).read().strip()
        if not tok:
            raise KaliciHata("token bos")
        return _json_get("https://api.thingiverse.com/things/%s" % kimlik,
                         {"Authorization": "Bearer " + tok})

    return (
        Adaptor(
            ad="mw", hostlar=("makerworld.com",),
            kimlik_cikar=lambda u: _kimlik_bas_sayi(u, "models"),
            detay=lambda k: _sarmala(mw.detail, k),
            lisans_cikar=lambda d: str(d.get("license") or ""),
            satilabilir=mw.satilabilir,
            ata_destegi=True),
        Adaptor(
            ad="pr", hostlar=("printables.com",),
            kimlik_cikar=lambda u: _kimlik_bas_sayi(u, "model"),
            detay=lambda k: _sarmala(pr.detail, k),
            lisans_cikar=lambda d: str(((d.get("license") or {}) or {}).get("abbreviation") or ""),
            satilabilir=pr.satilabilir,
            ata_destegi=False),
        Adaptor(
            ad="tv", hostlar=("thingiverse.com",),
            kimlik_cikar=_kimlik_thing,
            detay=_tv_detay,
            lisans_cikar=lambda d: str(d.get("license") or ""),
            satilabilir=genel_satilabilir,
            ata_destegi=False),
        Adaptor(
            ad="c3", hostlar=("cults3d.com",),
            kimlik_cikar=lambda u: _kimlik_slug(u, "3d-model"),
            detay=lambda k: _sarmala(c3.detail, k),
            lisans_cikar=c3.lisans_str,
            satilabilir=c3.satilabilir,
            ata_destegi=False),
        Adaptor(
            ad="mmf", hostlar=("myminifactory.com",),
            kimlik_cikar=lambda u: _kimlik_son_sayi(u, "object"),
            detay=lambda k: _sarmala(mmf.detail, k),
            lisans_cikar=lambda d: str(d.get("license") or ""),
            satilabilir=mmf.satilabilir,
            ata_destegi=False),
    )


# ---------------------------------------------------------------- SENTETIK DEFTER (agsiz)
# Kabul testi GERCEK platformlara CIKMAZ. Fikstur host/kimlik/lisanslari UYDURMADIR
# (".example" TLD'si RFC 2606 ile ayrilmistir). Sekil GERCEK cikti sekliyle AYNI tutulur.
_KIMLIK_STRATEJI = {
    "bas-sayi": _kimlik_bas_sayi,
    "son-sayi": _kimlik_son_sayi,
    "slug": _kimlik_slug,
}


def sentetik_defter(spec):
    """Fikstur tanimindan adaptor defteri kurar (AG YOK).

    spec: [{"ad","hostlar":[...],"kimlik":"bas-sayi:models","ata_destegi":bool,
            "yargi":"genel|ciplak-cc|kisaltma|insan-adi",
            "detaylar":{"<kimlik>": {...} | null | "__GECICI__" | "__KALICI__"
                        | "__TIMEOUT__" | "__BOZUK__"}}]
    """
    defter = []
    for s in spec:
        strateji, _, isaret = str(s.get("kimlik") or "bas-sayi:models").partition(":")
        detaylar = s.get("detaylar") or {}

        def _yap(detaylar=detaylar, strateji=strateji, isaret=isaret):
            def _kimlik(u):
                if strateji == "thing":
                    return _kimlik_thing(u)
                fn = _KIMLIK_STRATEJI.get(strateji)
                return fn(u, isaret) if fn else None

            def _detay(k):
                if k not in detaylar:
                    return None
                v = detaylar[k]
                if v == "__GECICI__":
                    return _sarmala(_patlat, urllib.error.HTTPError(
                        "u", 429, "Too Many Requests", None, None))
                if v == "__KALICI__":
                    return _sarmala(_patlat, urllib.error.HTTPError(
                        "u", 403, "Forbidden", None, None))
                if v == "__TIMEOUT__":
                    return _sarmala(_patlat, socket.timeout("okuma timeout"))
                if v == "__BOZUK__":
                    return _sarmala(_patlat, ValueError("bozuk JSON"))
                return v
            return _kimlik, _detay

        kimlik_fn, detay_fn = _yap()
        defter.append(Adaptor(
            ad=str(s.get("ad") or "?"),
            hostlar=tuple(s.get("hostlar") or ()),
            kimlik_cikar=kimlik_fn,
            detay=detay_fn,
            lisans_cikar=lambda d: str((d or {}).get("license") or ""),
            satilabilir=yargi_kaynagi(s.get("yargi") or "genel"),
            ata_destegi=bool(s.get("ata_destegi"))))
    return tuple(defter)


def _patlat(e):
    """Fikstur ariza enjeksiyonu: GERCEK istisna tipini _sarmala'nin siniflandirmasina verir
    (siniflandirma taklit EDILMEZ, gercek yol kosulur)."""
    raise e


# ---------------------------------------------------------------- KAPSAM
def kapsam_bolumle(kayitlar, defter, kaynak_filtre=None):
    """Kayitlari UC kovaya ayirir. 🔴 'ALAN-YOK (olculdu)' ile 'OLCULMEDI (bakilmadi)'
    AYRI kovalardir; ikincisi ASLA temiz sayilmaz.

    Doner (uygun, olculmedi_adaptorlu, olculmedi_adaptorsuz):
      uygun               : ata alani CANLI OLCULMUS platform -> detay cekilir, hukum verilir
      olculmedi_adaptorlu : adaptoru VAR ama ata alani o platformda HIC CEKILMEMIS -> BAKILMADI
      olculmedi_adaptorsuz: adaptoru YOK / linki okunamiyor -> BAKILAMADI
    """
    uygun, olculmedi_adaptorlu, olculmedi_adaptorsuz = [], [], []
    for urun_id in sorted(kayitlar):
        kayit = kayitlar[urun_id]
        if isinstance(kayit, dict):
            link = str(kayit.get("link") or "")
        elif isinstance(kayit, str):
            link = kayit.split(None, 1)[0] if kayit.strip() else ""
        else:
            link = ""
        if kaynak_filtre and isinstance(kayit, dict):
            if str(kayit.get("kaynak") or "").lower() != kaynak_filtre.lower():
                continue
        host = host_coz(link)
        ad = adaptor_bul(host, defter)
        if ad is None:
            olculmedi_adaptorsuz.append(urun_id)
        elif not ad.ata_destegi:
            olculmedi_adaptorlu.append(urun_id)
        else:
            uygun.append((urun_id, link, host, ad))
    return uygun, olculmedi_adaptorlu, olculmedi_adaptorsuz


# ---------------------------------------------------------------- rapor
def rapor_yaz(sonuclar, kapsam=None, taranan=0, yaz=None):
    yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
    kapsam = kapsam or {}
    say = collections.Counter(s["durum"] for s in sonuclar)
    yaz("ATA-LISANS KAPISI — RAPOR KIPI (veri YAZILMAZ, silme UYGULANMAZ)")
    yaz("  taranan kayit                 : %d" % taranan)
    yaz("  ata referansi (toplam)        : %d" % sum(
        1 for s in sonuclar if s["durum"] != DURUM_ALAN_YOK))
    yaz("  ALAN-YOK (OLCULDU: ata yok)   : %d" % say[DURUM_ALAN_YOK])
    yaz("  cozuldu / SATILABILIR         : %d" % say[DURUM_SATILABILIR])
    yaz("  IHLAL (ata satilamaz)         : %d" % say[DURUM_IHLAL])
    yaz("  COZULEMEDI-ADAPTORSUZ         : %d   -> ELLE-BAK" % say[DURUM_ADAPTORSUZ])
    yaz("  COZULEMEDI-SEKIL              : %d   -> SEKLI OLC (ALAN-YOK DENEMEZ)"
        % say[DURUM_SEKIL])
    yaz("  COZULEMEDI-KALICI             : %d   -> ESKALASYON" % say[DURUM_KALICI])
    yaz("  OLCULEMEDI-GECICI             : %d   -> YENIDEN DENE" % say[DURUM_GECICI])
    if kapsam:
        yaz("  --- OLCULMEDI (BAKILMADI — 'temiz' DEGIL) ---")
        yaz("  adaptoru VAR, ata alani cekilmiyor: %d" % len(kapsam.get("olculmedi_adaptorlu") or []))
        yaz("  adaptoru YOK / link okunamiyor    : %d" % len(kapsam.get("olculmedi_adaptorsuz") or []))
        yaz("  uygun havuzda tavan disi kalan    : %d" % (kapsam.get("taranmadi") or 0))

    ihlaller = [s for s in sonuclar if s["durum"] == DURUM_IHLAL]
    if ihlaller:
        yaz("")
        yaz("IHLAL LISTESI (SATILAMAZ — ata zinciri):")
        for s in ihlaller:
            yaz("  x %s | kademe=%s | ata=%s#%s | lisans=%r | %s"
                % (s.get("urun"), s.get("derinlik"), s.get("host") or "?",
                   s.get("ata_kimlik") or "?", s.get("ata_lisans"), s["gerekce"]))

    elle = [s for s in sonuclar if s["durum"] in (DURUM_ADAPTORSUZ, DURUM_KALICI, DURUM_SEKIL)]
    if elle:
        yaz("")
        yaz("ELLE-BAK KUYRUGU (cozulemedi -> SATILAMAZ SAY):")
        for s in elle:
            yaz("  ? %s | kademe=%s | %s | host=%s | %s"
                % (s.get("urun"), s.get("derinlik"), s.get("ata_link") or "(link yok)",
                   s.get("host") or "?", s["gerekce"]))

    gecici = [s for s in sonuclar if s["durum"] == DURUM_GECICI]
    if gecici:
        yaz("")
        yaz("GECICI HATA (yeniden denenebilir — KALICI DEGIL):")
        for s in gecici:
            yaz("  ~ %s | host=%s | %s" % (s.get("urun"), s.get("host") or "?", s["gerekce"]))
    return say


# ---------------------------------------------------------------- kosum kipleri
def fikstur_kosum(yol, defter=None, gs=None):
    """Agsiz kosum. Fikstur sekli:
        {"adaptorler": [...sentetik defter (istege bagli)...],
         "kayitlar": {"<urun>": {...}}, "detaylar": {"<urun>": {<platform detay JSON>}}}
    """
    with open(yol, encoding="utf-8") as f:
        fx = json.load(f)
    detaylar = fx.get("detaylar") or {}
    kayitlar = fx.get("kayitlar") or {k: {} for k in detaylar}
    if defter is None and fx.get("adaptorler"):
        defter = sentetik_defter(fx["adaptorler"])
    defter = defter if defter is not None else uretim_defteri()
    gs = gs or genel_satilabilir
    sonuclar = []
    for urun_id in sorted(kayitlar):
        kayit = kayitlar[urun_id] if isinstance(kayitlar[urun_id], dict) else {}
        kaynak_ad = adaptor_bul(host_coz(str(kayit.get("link") or "")), defter)
        sonuclar.extend(kayit_yargi(urun_id, detaylar.get(urun_id), defter, gs, kaynak_ad))
    return sonuclar, len(kayitlar)


def kuru_kosum(limit=40, kaynak_filtre=None, yaz=None):
    """AG ISTER. Doner: (sonuclar, taranan, kapsam)."""
    yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
    kok = _veri_kok()
    yol = os.path.join(kok, ".urun-kaynaklari.json")
    if not os.path.exists(yol):
        raise KaliciHata("gizli kaynak kaydi bulunamadi (OLCULEMEDI)")
    with open(yol, encoding="utf-8") as f:
        kayitlar = json.load(f)
    defter = uretim_defteri()

    uygun, olc_adaptorlu, olc_adaptorsuz = kapsam_bolumle(kayitlar, defter, kaynak_filtre)
    yaz("  uygun (ata alani OLCULMUS): %d · OLCULMEDI-adaptorlu: %d · OLCULMEDI-adaptorsuz: %d "
        "· tavan: %d" % (len(uygun), len(olc_adaptorlu), len(olc_adaptorsuz), limit))

    sonuclar, taranan = [], 0
    for urun_id, link, host, ad in uygun:
        if taranan >= limit:
            break
        taranan += 1
        kimlik = ad.kimlik_cikar(link)
        if not kimlik:
            s = _sonuc(DURUM_KALICI, "turev kaydin kendi kimligi cikarilamadi",
                       {"link": link}, host)
            s["urun"] = urun_id
            sonuclar.append(s)
            continue
        try:
            detay = ad.detay(kimlik)
        except GeciciHata as e:
            s = _sonuc(DURUM_GECICI, "turev detayi alinamadi (gecici): %s" % e,
                       {"link": link}, host, kimlik)
            s["urun"] = urun_id
            sonuclar.append(s)
            continue
        except KaliciHata as e:
            s = _sonuc(DURUM_KALICI, "turev detayi alinamadi (kalici): %s" % e,
                       {"link": link}, host, kimlik)
            s["urun"] = urun_id
            sonuclar.append(s)
            continue
        # 🔴 detay None/BOS kontrolu kayit_yargi'nin ICINDE (fail-closed) — burada
        # "detay yok -> ata yok" kisayolu YOKTUR (olculen sessiz gecis sinifi).
        sonuclar.extend(kayit_yargi(urun_id, detay, defter, genel_satilabilir, ad))
    kapsam = {"olculmedi_adaptorlu": olc_adaptorlu,
              "olculmedi_adaptorsuz": olc_adaptorsuz,
              "taranmadi": max(0, len(uygun) - taranan),
              "uygun": len(uygun)}
    return sonuclar, taranan, kapsam


# ---------------------------------------------------------------- oz-denetim (CI kolu)
def kendini_test(yaz=None):
    """OFFLINE oz-denetim. Ag'a CIKMAZ. Doner: (gecen, toplam)."""
    yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
    k = []
    defter = uretim_defteri()
    k.append(("uretim defteri bos degil", len(defter) >= 5))
    k.append(("en az bir adaptorde ata destegi olculmus", any(a.ata_destegi for a in defter)))
    k.append(("host normalize: www ve port atiliyor",
              host_coz("https://WWW.Ornek-Host.example:443/x") == "ornek-host.example"))
    k.append(("host degilse None", host_coz("bu bir url degil") is None))
    k.append(("bilinmeyen host -> adaptor YOK", adaptor_bul("bilinmeyen.example", defter) is None))
    k.append(("bos lisans fail-closed", genel_satilabilir("") is False))
    k.append(("NC veto (insan-adi)",
              lisans_vetosu("Creative Commons - Attribution - Non-Commercial") is True))
    k.append(("NC veto (ciplak)", lisans_vetosu("BY-NC-SA") is True))
    k.append(("tescilli veto", lisans_vetosu("Standard Digital File License") is True))
    k.append(("CC-BY veto YOK", lisans_vetosu("Creative Commons - Attribution") is False))
    k.append(("coklu sozluk: ciplak BY-SA satilabilir",
              coklu_sozluk_satilabilir("BY-SA") is True))
    k.append(("coklu sozluk: insan-adi satilabilir",
              coklu_sozluk_satilabilir("Attribution 4.0 International") is True))
    k.append(("coklu sozluk: NC ASLA", coklu_sozluk_satilabilir("BY-NC") is False))
    k.append(("veto: tam metin 'non-exclusive' VETO YEMEZ",
              lisans_vetosu("Attribution 4.0 International — a worldwide, royalty-free, "
                            "non-exclusive, perpetual license") is False))
    k.append(("veto: tescilli 'Exclusive License' VETO YER",
              lisans_vetosu("MakerWorld Exclusive License") is True))
    k.append(("ata alan listesi 6 ad", len(ATA_ALANLARI) >= 6))
    k.append(("zarf acilir", "originals" in _zarf_ac({"data": {"originals": []}})[0]))
    k.append(("ad normalize: buyuk-kucuk/ayrac duyarsiz", _ad("Remix_Of") == _ad("remixOf")))
    k.append(("ata alani yazim varyantiyla GORULUR",
              ata_anahtarlari({"Originals": [], "REMIXOF": []}) == ["Originals", "REMIXOF"]))
    k.append(("derin zarf (4 kademe) acilir",
              "originals" in _zarf_ac(
                  {"data": {"result": {"response": {"payload": {"originals": []}}}}})[0]))
    k.append(("zarf TAVANI asilirsa fail-closed", bool(_zarf_ac(
        {"data": {"data": {"data": {"data": {"data": {"data": {"data": {"data": {}}}}}}}}},
        tavan=2)[1])))
    k.append(("BELIRSIZ zarf (2 ic sozluk) fail-closed",
              bool(_zarf_ac({"data": {"a": 1}, "model": {"b": 2}})[1])))
    k.append(("govde ISARETLI zarfin icindeki ata alani GORULUR",
              ata_anahtarlari(_zarf_ac(
                  {"id": 1, "title": "x", "data": {"originals": []}})[0]) == ["originals"]))
    k.append(("govde izi ALAN-YOK'un on kosulu",
              _zarf_ac({"title": "x"})[2] is True and _zarf_ac({"foo": 1})[2] is False))
    k.append(("taninan govde -> ALAN-YOK",
              kayit_yargi("u", {"title": "x"}, defter, genel_satilabilir)[0]["durum"]
              == DURUM_ALAN_YOK))
    k.append(("TANINMAYAN sekil -> ALAN-YOK DEGIL (SEKIL)",
              kayit_yargi("u", {"foo": 1}, defter, genel_satilabilir)[0]["durum"]
              == DURUM_SEKIL))
    k.append(("rc: SEKIL ASLA 0", cikis_kodu([{"durum": DURUM_SEKIL}]) != 0))
    k.append(("coklu URL cikar", len(urlleri_cikar("a https://x.example/1 b https://y.example/2")) == 2))
    k.append(("kimlik: site bicimi", _kimlik_thing("https://ornek.example/thing:2304418") == "2304418"))
    k.append(("kimlik: API bicimi", _kimlik_thing("https://api.ornek.example/things/2304418")
              == "2304418"))
    k.append(("kimlik: bicim yoksa None", _kimlik_thing("https://ornek.example/x/1") is None))
    k.append(("turev detayi None -> KALICI",
              kayit_yargi("u", None, defter, genel_satilabilir)[0]["durum"] == DURUM_KALICI))
    k.append(("turev detayi BOS -> KALICI",
              kayit_yargi("u", {}, defter, genel_satilabilir)[0]["durum"] == DURUM_KALICI))
    k.append(("ALAN-YOK sonucunda urun kimligi VAR",
              kayit_yargi("u", {"title": "x"}, defter, genel_satilabilir)[0].get("urun") == "u"))
    bos_ata = {"link": "", "license": "", "alan": "originals"}
    k.append(("linksiz ata fail-closed",
              ata_yargi(bos_ata, defter, genel_satilabilir)[0]["durum"] == DURUM_KALICI))
    adaptorsuz = {"link": "https://adaptorsuz.example/x/1", "license": "", "alan": "originals"}
    k.append(("adaptorsuz host -> ELLE-BAK",
              ata_yargi(adaptorsuz, defter, genel_satilabilir)[0]["durum"] == DURUM_ADAPTORSUZ))
    k.append(("rc: ihlal -> 1", cikis_kodu([{"durum": DURUM_IHLAL}]) == 1))
    k.append(("rc: gecici -> 2", cikis_kodu([{"durum": DURUM_GECICI}]) == 2))
    k.append(("rc: temiz -> 0", cikis_kodu([{"durum": DURUM_SATILABILIR}]) == 0))
    k.append(("rc: adaptorsuz ASLA 0", cikis_kodu([{"durum": DURUM_ADAPTORSUZ}]) != 0))
    k.append(("rc: kalici ASLA 0", cikis_kodu([{"durum": DURUM_KALICI}]) != 0))
    k.append(("rc: OLCULMEMIS kapsam -> 2",
              cikis_kodu([{"durum": DURUM_SATILABILIR}],
                         {"olculmedi_adaptorlu": ["a"]}) == 2))
    k.append(("derinlik tavani beyan edilmis", DERINLIK_TAVANI >= 2))

    gecen = 0
    for ad, ok in k:
        yaz("  %-4s %s" % ("ok" if ok else "HATA", ad))
        gecen += 1 if ok else 0
    return gecen, len(k)


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Ata-lisans zincir kapisi (rapor kipi; veri YAZMAZ)")
    ap.add_argument("--kendini-test", action="store_true", help="offline oz-denetim (CI kolu)")
    ap.add_argument("--fikstur", help="agsiz kosum icin fikstur JSON yolu")
    ap.add_argument("--kuru-kosum", action="store_true", help="gizli kaynak kayitlari (AG ISTER)")
    ap.add_argument("--limit", type=int, default=40, help="kuru kosumda taranacak kayit tavani")
    ap.add_argument("--kaynak", help="kuru kosumda kaynak adi filtresi")
    a = ap.parse_args(argv)

    if a.kendini_test:
        gecen, toplam = kendini_test()
        print("")
        if gecen != toplam:
            print("OZ-DENETIM BASARISIZ — %d/%d gecti." % (gecen, toplam))
            return 1
        print("OZ-DENETIM GECTI (%d kontrol)." % toplam)
        return 0

    if a.fikstur:
        sonuclar, taranan = fikstur_kosum(a.fikstur)
        rapor_yaz(sonuclar, None, taranan)
        return cikis_kodu(sonuclar)

    if a.kuru_kosum:
        try:
            sonuclar, taranan, kapsam = kuru_kosum(a.limit, a.kaynak)
        except KaliciHata as e:
            print("OLCULEMEDI — %s" % e)
            return 2
        rapor_yaz(sonuclar, kapsam, taranan)
        return cikis_kodu(sonuclar, kapsam)

    print("OLCULEMEDI — kip secilmedi (--kendini-test | --fikstur <yol> | --kuru-kosum)")
    return 2


if __name__ == "__main__":
    sys.exit(main())

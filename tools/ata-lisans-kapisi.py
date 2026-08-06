#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ATA-LISANS KAPISI — turev kaydin ATASININ lisansini, ata BAGLANTISININ HOST'undan cozer.

NEDEN VAR (kok neden, 4 canli emsalle olculdu — hicbir test kirmizi yanmadi):
Bir kaynak platformdaki TUREV kayit, atasinin lisansini KENDI JSON'unda GOSTERMIYOR:
ata referansinin `license` alani BOS ve `designId` 0 geliyor; tek gercek sinyal serbest-metin
`link` URL'sidir. Ata lisansi ANCAK o URL'den HOST + KIMLIK cikarilip O PLATFORMUN kendi
API'sine gidilerek cozuluyor. Dort canli emsalde de ata CC ...-NC / -NC-SA cikti = SATILAMAZ;
urunler fail-closed geri cekildi. Yukleyicinin turevi "CC0" diye YENIDEN LISANSLAMASI GECERSIZ:
NC bir atadan turetilen eser NC kalir.

🔴 OLCULEN BOSLUK: depodaki lisans kapilarinin HEPSI kaynak-platform-ICI bakar
(kayit['lisans'] -> o platformun satilabilir()'i). Ata ZINCIRI hicbir kapinin ekseninde DEGIL
(`originals` jetonu 21 Tem itibariyle tools/ altinda HIC gecmiyordu). Yakalama ELLE yapiliyordu.

NE OLCER (tek eksen — ata zinciri):
  turev detay JSON'u -> ata referanslari -> her ata icin:
    URL -> HOST -> O HOST'un adaptoru -> ata lisansi -> satilabilir() yargisi.

FAIL-CLOSED YON (supheli = satilamaz):
  * host'un adaptoru YOK        -> COZULEMEDI-ADAPTORSUZ (ELLE-BAK kuyruguna) -> rc 1
  * kimlik cikarilamadi / null  -> COZULEMEDI-KALICI (eskalasyon)             -> rc 1
  * API 401/403/404-null        -> COZULEMEDI-KALICI (eskalasyon)             -> rc 1
  * API 429 / 5xx / timeout     -> OLCULEMEDI-GECICI (yeniden denenebilir)    -> rc 2
  * ata lisansi satilamaz       -> IHLAL                                      -> rc 1
  GECICI ile KALICI AYRI raporlanir: gecici yeniden denenir, kalici insana cikar.
  "Sessizce gecirme" hali YOKTUR; ucuncu bir yol birakilmadi.

GOMULU LISANS ALANI (varsa) SIKI YONDE kullanilir: ata referansinin kendi `license` alani
DOLU ve SATILAMAZ ise ihlal HEMEN verilir (ag'a cikmadan). DOLU ve satilabilir ise hukum
VERILMEZ — host cozumlemesi YINE kosar (o alanin yaniltici oldugu zaten olculdu).

KAPI DAVRANISI — VERI YAZMAZ:
  Rapor kipi TEK kiptir. Urun verisinin tek yazari baska bir mimardir; bu arac urunler.json /
  gizli kaynak kaydi / D1 hicbirine DOKUNMAZ, silme UYGULAMAZ. Cikti: ihlal listesi + gerekce
  + ata kimlik/lisans + ELLE-BAK kuyrugu (STDOUT; dosyaya da yazilmaz).

CIKIS KODU:  0 = ihlal yok · 1 = ihlal VAR (ya da fail-closed cozulemedi) · 2 = OLCULEMEDI
             (yesil SAYILMAZ; kismi olcum de 2'ye duser, gurultulu sebep basar)

MEVCUT YUZEYIN UZERINE KURULUR (yeniden yazilmadi): her platformun `satilabilir()` yargisi
KENDI adaptorundedir (makerworld-api / printables-api / cults3d-api / myminifactory-api) ve
BURADAN CAGRILIR. Adaptorsuz/serbest-metin lisanslar icin denetim-kapisi.py'nin GENEL
normalizeri (lisans_kisaltma) + printables satilabilir() zinciri kullanilir — ayni fallback
zinciri denetim-kapisi.py'de de kullaniliyor, KOPYALANMADI.

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
DURUM_ATA_YOK = "ATA-YOK"
DURUM_SATILABILIR = "SATILABILIR"
DURUM_IHLAL = "IHLAL"
DURUM_ADAPTORSUZ = "COZULEMEDI-ADAPTORSUZ"
DURUM_KALICI = "COZULEMEDI-KALICI"
DURUM_GECICI = "OLCULEMEDI-GECICI"
DURUM_KAPSAM_DISI = "KAPSAM-DISI"

# rc 1'e goturenler (fail-closed: "satilamaz say")
IHLAL_DURUMLARI = (DURUM_IHLAL, DURUM_ADAPTORSUZ, DURUM_KALICI)
# rc 2'ye goturenler (yeniden denenebilir)
OLCULEMEDI_DURUMLARI = (DURUM_GECICI,)


class GeciciHata(Exception):
    """429 / 5xx / timeout — YENIDEN DENENEBILIR (kalici degil)."""


class KaliciHata(Exception):
    """401/403/kimlik/format — ESKALASYON (yeniden denemek fayda etmez)."""


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


# ---------------------------------------------------------------- ata referanslarini cikar
# Turev kaydin detay JSON'unda ata listesi bu alan(lar)da durur. Sekil:
#   [{"link": "<serbest-metin URL>", "license": "<GENELDE BOS>", "designId": 0}, ...]
ATA_ALANLARI = ("originals",)


def ata_kayitlari(detay):
    """Detay JSON'undan ata referanslari (normalize dict listesi). Ata yoksa bos liste.

    Tolerans: eleman string ise link sayilir; dict degilse ve string degilse ATLANMAZ,
    'link yok' referansi olarak gecer (fail-closed: bilinmeyen sekil sessizce yutulmaz)."""
    if not isinstance(detay, dict):
        return []
    out = []
    for alan in ATA_ALANLARI:
        ham = detay.get(alan)
        if not isinstance(ham, list):
            continue
        for el in ham:
            if isinstance(el, dict):
                out.append({
                    "link": str(el.get("link") or el.get("url") or "").strip(),
                    "license": str(el.get("license") or "").strip(),
                    "kimlik_alani": el.get("designId", el.get("id")),
                })
            elif isinstance(el, str):
                out.append({"link": el.strip(), "license": "", "kimlik_alani": None})
            else:
                out.append({"link": "", "license": "", "kimlik_alani": None})
    return out


# ---------------------------------------------------------------- yargi
def _sonuc(durum, gerekce, ata=None, host=None, kimlik=None, lisans=None, adaptor=None):
    return {
        "durum": durum,
        "gerekce": gerekce,
        "ata_link": (ata or {}).get("link", ""),
        "host": host,
        "ata_kimlik": kimlik,
        "ata_lisans": lisans,
        "adaptor": adaptor,
    }


def ata_yargi(ata, defter, genel_satilabilir, kaynak_adaptor=None):
    """TEK ata referansi icin yargi (dict). Ag'a yalnizca adaptor.detay ile cikar.

    kaynak_adaptor: ata referansini BASAN (turev) platformun adaptoru. Gomulu `license`
    alani O PLATFORMUN kendi lisans SOZLUGUNDE yazilidir (ornegin CC'yi ciplak yazan bir
    platformda "BY-SA"), atanin kendi sozlugunde DEGIL. 🔴 CANLI OLCUM (250 kayitlik kuru
    kosum): gomulu alan GENEL normalize zinciriyle yargilaninca ciplak "BY"/"BY-SA" degerleri
    satilamaz sanildi -> 10 YANLIS-POZITIF. Yanlis-pozitif tum ekibin yayinini durdurur;
    bu yuzden gomulu alan DAIMA BASAN platformun kendi satilabilir()'i ile yargilanir
    (denetim-kapisi.py'nin `_KAYNAK_SATILABILIR` dersi ile ayni)."""
    link = (ata.get("link") or "").strip()
    gomulu = (ata.get("license") or "").strip()
    gomulu_yargi = kaynak_adaptor.satilabilir if kaynak_adaptor is not None else genel_satilabilir

    # 1) Gomulu lisans DOLU ve SATILAMAZ ise ag'a cikmadan ihlal (siki yon).
    #    DOLU ve satilabilir ise hukum VERILMEZ -> host cozumlemesi yine kosar.
    if gomulu and not gomulu_yargi(gomulu):
        return _sonuc(DURUM_IHLAL, "ata referansindaki lisans satilamaz (gomulu alan)",
                      ata, host_coz(link), None, gomulu)

    # 2) Link yok -> host okunamaz -> fail-closed
    if not link:
        return _sonuc(DURUM_KALICI, "ata baglantisi YOK; host okunamiyor", ata)

    host = host_coz(link)
    if not host:
        return _sonuc(DURUM_KALICI, "ata baglantisi URL olarak ayristirilamadi", ata)

    adaptor = adaptor_bul(host, defter)
    if adaptor is None:
        return _sonuc(DURUM_ADAPTORSUZ, "bu host icin adaptor YOK -> ELLE-BAK", ata, host)

    kimlik = adaptor.kimlik_cikar(link)
    if not kimlik:
        return _sonuc(DURUM_KALICI, "host taniniyor ama kimlik cikarilamadi",
                      ata, host, None, None, adaptor.ad)

    try:
        detay = adaptor.detay(kimlik)
    except GeciciHata as e:
        return _sonuc(DURUM_GECICI, "gecici API hatasi: %s" % e, ata, host, kimlik, None, adaptor.ad)
    except KaliciHata as e:
        return _sonuc(DURUM_KALICI, "kalici API hatasi: %s" % e, ata, host, kimlik, None, adaptor.ad)

    if detay is None:
        return _sonuc(DURUM_KALICI, "API null dondu (kayit yok/erisilemez)",
                      ata, host, kimlik, None, adaptor.ad)

    lisans_metni = (adaptor.lisans_cikar(detay) or "").strip()
    if not lisans_metni:
        return _sonuc(DURUM_KALICI, "ata lisansi BOS dondu", ata, host, kimlik, "", adaptor.ad)

    if not adaptor.satilabilir(lisans_metni):
        return _sonuc(DURUM_IHLAL, "ATA LISANSI SATILAMAZ (turevin yeniden-lisansi gecersiz)",
                      ata, host, kimlik, lisans_metni, adaptor.ad)

    return _sonuc(DURUM_SATILABILIR, "ata lisansi ticari satisa uygun",
                  ata, host, kimlik, lisans_metni, adaptor.ad)


def kayit_yargi(urun_id, detay, defter, genel_satilabilir, kaynak_adaptor=None):
    """Bir turev kaydin TUM ata referanslarinin yargisi -> sonuc dict listesi."""
    atalar = ata_kayitlari(detay)
    if not atalar:
        return [_sonuc(DURUM_ATA_YOK, "detayda ata referansi yok")]
    out = []
    for ata in atalar:
        s = ata_yargi(ata, defter, genel_satilabilir, kaynak_adaptor)
        s["urun"] = urun_id
        out.append(s)
    for s in out:
        s.setdefault("urun", urun_id)
    return out


def cikis_kodu(sonuclar):
    """0 ihlal yok · 1 ihlal/fail-closed VAR · 2 OLCULEMEDI (yesil sayilmaz)."""
    durumlar = [s["durum"] for s in sonuclar]
    if any(d in IHLAL_DURUMLARI for d in durumlar):
        return 1
    if any(d in OLCULEMEDI_DURUMLARI for d in durumlar):
        return 2
    return 0


# ---------------------------------------------------------------- HTTP yardimcilari
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124 Safari/537.36")


def _http_hata_cevir(e):
    """urllib istisnasini GeciciHata/KaliciHata'ya cevirir (404 -> None ile ayri ele alinir)."""
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (429, 500, 502, 503, 504):
            return GeciciHata("HTTP %s" % e.code)
        return KaliciHata("HTTP %s" % e.code)
    return GeciciHata("ag hatasi: %s" % type(e).__name__)


def _json_get(url, basliklar=None):
    """JSON GET; 404 -> None. Hata siniflandirmasi _http_hata_cevir ile."""
    h = {"Accept": "application/json", "User-Agent": _UA}
    h.update(basliklar or {})
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise _http_hata_cevir(e)
    except Exception as e:                                          # noqa: BLE001
        raise _http_hata_cevir(e)


def _sarmala(fn, *a, **kw):
    """Var olan adaptor cagrisini Gecici/Kalici siniflandirmasina sarar."""
    try:
        return fn(*a, **kw)
    except (GeciciHata, KaliciHata):
        raise
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise _http_hata_cevir(e)
    except urllib.error.URLError as e:
        raise GeciciHata("ag hatasi: %s" % type(e).__name__)
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
    """.../thing:<sayi> -> sayi."""
    for parca in _yol_parcalari(url):
        m = re.match(r"thing:(\d+)", parca, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------- URETIM DEFTERI
_ONBELLEK = {}


def _modul(dosya, ad):
    if ad not in _ONBELLEK:
        _ONBELLEK[ad] = _yukle(dosya, ad)
    return _ONBELLEK[ad]


def genel_satilabilir(ham):
    """ADAPTORSUZ / serbest-metin lisans yargisi — MEVCUT zincir (kopya DEGIL):
    denetim-kapisi.lisans_kisaltma() ile normalize + printables satilabilir() beyaz listesi.
    Ayni fallback denetim-kapisi.py'de de kullaniliyor."""
    dk = _modul("denetim-kapisi.py", "ata_denetim_kapisi")
    pr = _modul("printables-api.py", "ata_printables_api")
    return bool(pr.satilabilir(dk.lisans_kisaltma(ham)))


def _veri_kok():
    vk = _modul("veri_kok.py", "ata_veri_kok")
    _kod, veri, _uyari = vk.cozumle(os.path.join(_HERE, "ata-lisans-kapisi.py"))
    return veri


def uretim_defteri():
    """Canli adaptor defteri. TEMBEL kurulur (import/anahtar maliyeti kosum aninda)."""
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
            # Ata alani (`originals`) BU platformda CANLI OLCULDU.
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
            # Serbest-metin (insan-okur) lisans adi -> GENEL normalize zinciri.
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
# (".example" TLD'si RFC 2606 ile ayrilmistir; gercek bir kaynak platformu isaret ETMEZ).
# Sekil GERCEK cikti sekliyle AYNI tutulur: ata referansi {link, license(BOS), designId(0)}.
_KIMLIK_STRATEJI = {
    "bas-sayi": _kimlik_bas_sayi,
    "son-sayi": _kimlik_son_sayi,
    "slug": _kimlik_slug,
}


def yargi_kaynagi(etiket):
    """Lisans SOZLUGUNE gore yargi fonksiyonu (var olanlar; kopya YOK). Etiketler platform
    adi DEGIL, lisans yazim bicimidir:
      'ciplak-cc' : CC'yi ciplak yazan sozluk ("BY", "BY-SA", "CC0")
      'kisaltma'  : onekli kisaltma sozlugu ("CC-BY", "GPL 3.0")
      'insan-adi' : insan-okur ad sozlugu ("Attribution - NonCommercial")
      'genel'     : normalize + kisaltma zinciri (fallback)"""
    if etiket == "ciplak-cc":
        return _modul("makerworld-api.py", "ata_makerworld_api").satilabilir
    if etiket == "kisaltma":
        return _modul("printables-api.py", "ata_printables_api").satilabilir
    if etiket == "insan-adi":
        return _modul("cults3d-api.py", "ata_cults3d_api").satilabilir
    return genel_satilabilir


def sentetik_defter(spec):
    """Fikstur tanimindan adaptor defteri kurar (AG YOK).

    spec: [{"ad","hostlar":[...],"kimlik":"bas-sayi:models","ata_destegi":bool,
            "yargi":"genel|ciplak-cc|kisaltma|insan-adi",
            "detaylar":{"<kimlik>": {"license": "..."} | null | "__GECICI__" | "__KALICI__"}}]
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
                    raise GeciciHata("HTTP 429")
                if v == "__KALICI__":
                    raise KaliciHata("HTTP 403")
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


# ---------------------------------------------------------------- rapor
def rapor_yaz(sonuclar, kapsam_disi=0, taranan=0, yaz=None):
    yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
    say = collections.Counter(s["durum"] for s in sonuclar)
    yaz("ATA-LISANS KAPISI — RAPOR KIPI (veri YAZILMAZ, silme UYGULANMAZ)")
    yaz("  taranan kayit                 : %d" % taranan)
    yaz("  ata referansi (toplam)        : %d" % sum(
        1 for s in sonuclar if s["durum"] != DURUM_ATA_YOK))
    yaz("  ata YOK                       : %d" % say[DURUM_ATA_YOK])
    yaz("  cozuldu / SATILABILIR         : %d" % say[DURUM_SATILABILIR])
    yaz("  IHLAL (ata satilamaz)         : %d" % say[DURUM_IHLAL])
    yaz("  COZULEMEDI-ADAPTORSUZ         : %d   -> ELLE-BAK" % say[DURUM_ADAPTORSUZ])
    yaz("  COZULEMEDI-KALICI             : %d   -> ESKALASYON" % say[DURUM_KALICI])
    yaz("  OLCULEMEDI-GECICI             : %d   -> YENIDEN DENE" % say[DURUM_GECICI])
    yaz("  kapsam disi (ata alani olculmemis platform): %d" % kapsam_disi)

    ihlaller = [s for s in sonuclar if s["durum"] == DURUM_IHLAL]
    if ihlaller:
        yaz("")
        yaz("IHLAL LISTESI (SATILAMAZ — ata zinciri):")
        for s in ihlaller:
            yaz("  x %s | ata=%s#%s | lisans=%r | %s"
                % (s.get("urun"), s.get("host") or "?", s.get("ata_kimlik") or "?",
                   s.get("ata_lisans"), s["gerekce"]))

    elle = [s for s in sonuclar if s["durum"] in (DURUM_ADAPTORSUZ, DURUM_KALICI)]
    if elle:
        yaz("")
        yaz("ELLE-BAK KUYRUGU (cozulemedi -> SATILAMAZ SAY):")
        for s in elle:
            yaz("  ? %s | %s | host=%s | %s"
                % (s.get("urun"), s.get("ata_link") or "(link yok)",
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
    `adaptorler` yoksa URETIM defteri kullanilir (o zaman ag'a cikabilir).
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
        # turevin KENDI platformu (gomulu lisans alani onun sozlugundedir)
        kaynak_ad = adaptor_bul(host_coz(str(kayit.get("link") or "")), defter)
        sonuclar.extend(kayit_yargi(urun_id, detaylar.get(urun_id), defter, gs, kaynak_ad))
    return sonuclar, len(kayitlar)


def kuru_kosum(limit=40, kaynak_filtre=None, yaz=None):
    """AG ISTER. Gizli kaynak kayitlarindan, ata alani OLCULMUS platformlari tarar.
    Doner: (sonuclar, taranan, kapsam_disi)."""
    yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
    kok = _veri_kok()
    yol = os.path.join(kok, ".urun-kaynaklari.json")
    if not os.path.exists(yol):
        raise KaliciHata("gizli kaynak kaydi bulunamadi (OLCULEMEDI)")
    with open(yol, encoding="utf-8") as f:
        kayitlar = json.load(f)
    defter = uretim_defteri()
    destekli = tuple(a for a in defter if a.ata_destegi)

    # 1) TAM GECIS: kapsam sayilari TUM kayitlar uzerinden olculur (limit BOZMAZ).
    uygun, kapsam_disi = [], 0
    for urun_id in sorted(kayitlar):
        kayit = kayitlar[urun_id]
        link = ""
        if isinstance(kayit, dict):
            link = str(kayit.get("link") or "")
        elif isinstance(kayit, str):
            link = kayit.split(None, 1)[0] if kayit.strip() else ""
        if kaynak_filtre and isinstance(kayit, dict):
            if str(kayit.get("kaynak") or "").lower() != kaynak_filtre.lower():
                continue
        host = host_coz(link)
        ad = adaptor_bul(host, destekli)
        if ad is None:
            kapsam_disi += 1
            continue
        uygun.append((urun_id, link, host, ad))
    yaz("  ata alani OLCULMUS platformda kayit: %d · kapsam disi: %d · tavan: %d"
        % (len(uygun), kapsam_disi, limit))

    # 2) SINIRLI TARAMA (ag): tavana kadar
    sonuclar, taranan = [], 0
    for urun_id, link, host, ad in uygun:
        if taranan >= limit:
            break
        kimlik = ad.kimlik_cikar(link)
        if not kimlik:
            taranan += 1
            s = _sonuc(DURUM_KALICI, "turev kaydin kendi kimligi cikarilamadi", {"link": link}, host)
            s["urun"] = urun_id
            sonuclar.append(s)
            continue
        try:
            detay = ad.detay(kimlik)
        except GeciciHata as e:
            taranan += 1
            s = _sonuc(DURUM_GECICI, "turev detayi alinamadi (gecici): %s" % e,
                       {"link": link}, host, kimlik)
            s["urun"] = urun_id
            sonuclar.append(s)
            continue
        except KaliciHata as e:
            taranan += 1
            s = _sonuc(DURUM_KALICI, "turev detayi alinamadi (kalici): %s" % e,
                       {"link": link}, host, kimlik)
            s["urun"] = urun_id
            sonuclar.append(s)
            continue
        taranan += 1
        # kaynak_adaptor: gomulu lisans alani BASAN platformun sozlugundedir -> onun yargisi
        sonuclar.extend(kayit_yargi(urun_id, detay, defter, genel_satilabilir, ad))
    return sonuclar, taranan, kapsam_disi


# ---------------------------------------------------------------- oz-denetim (CI kolu)
def kendini_test(yaz=None):
    """OFFLINE oz-denetim: defter kurulur mu, fail-closed yon duruyor mu, host ekseni
    gercekten okunuyor mu. Ag'a CIKMAZ. Doner: (gecen, toplam)."""
    yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
    kontroller = []

    defter = uretim_defteri()
    kontroller.append(("uretim defteri bos degil", len(defter) >= 5))
    kontroller.append(("en az bir adaptorde ata destegi olculmus",
                       any(a.ata_destegi for a in defter)))
    kontroller.append(("host normalize: www ve port atiliyor",
                       host_coz("https://WWW.Ornek-Host.example:443/x") == "ornek-host.example"))
    kontroller.append(("host degilse None", host_coz("bu bir url degil") is None))
    kontroller.append(("bilinmeyen host -> adaptor YOK",
                       adaptor_bul("bilinmeyen-host.example", defter) is None))
    kontroller.append(("bos lisans fail-closed", genel_satilabilir("") is False))
    kontroller.append(("NC fail-closed",
                       genel_satilabilir("Creative Commons - Attribution - Non-Commercial") is False))
    kontroller.append(("CC-BY satilabilir",
                       genel_satilabilir("Creative Commons - Attribution") is True))
    bos_ata = {"link": "", "license": "", "kimlik_alani": 0}
    kontroller.append(("linksiz ata fail-closed",
                       ata_yargi(bos_ata, defter, genel_satilabilir)["durum"] == DURUM_KALICI))
    adaptorsuz = {"link": "https://adaptorsuz-host.example/x/1", "license": "", "kimlik_alani": 0}
    kontroller.append(("adaptorsuz host -> ELLE-BAK",
                       ata_yargi(adaptorsuz, defter, genel_satilabilir)["durum"] == DURUM_ADAPTORSUZ))
    kontroller.append(("ata alani okunuyor",
                       len(ata_kayitlari({"originals": [{"link": "https://a.example/1"}]})) == 1))
    kontroller.append(("ata yoksa bos", ata_kayitlari({"baslik": "x"}) == []))
    kontroller.append(("rc: ihlal -> 1",
                       cikis_kodu([{"durum": DURUM_IHLAL}, {"durum": DURUM_SATILABILIR}]) == 1))
    kontroller.append(("rc: gecici -> 2",
                       cikis_kodu([{"durum": DURUM_GECICI}, {"durum": DURUM_SATILABILIR}]) == 2))
    kontroller.append(("rc: temiz -> 0", cikis_kodu([{"durum": DURUM_SATILABILIR}]) == 0))
    kontroller.append(("rc: adaptorsuz ASLA 0", cikis_kodu([{"durum": DURUM_ADAPTORSUZ}]) != 0))
    kontroller.append(("rc: kalici ASLA 0", cikis_kodu([{"durum": DURUM_KALICI}]) != 0))

    gecen = 0
    for ad, ok in kontroller:
        yaz("  %-4s %s" % ("ok" if ok else "HATA", ad))
        gecen += 1 if ok else 0
    return gecen, len(kontroller)


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Ata-lisans kapisi (rapor kipi; veri YAZMAZ)")
    ap.add_argument("--kendini-test", action="store_true", help="offline oz-denetim (CI kolu)")
    ap.add_argument("--fikstur", help="agsiz kosum icin fikstur JSON yolu")
    ap.add_argument("--kuru-kosum", action="store_true", help="gizli kaynak kayitlari uzerinde (AG ISTER)")
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
        rapor_yaz(sonuclar, 0, taranan)
        return cikis_kodu(sonuclar)

    if a.kuru_kosum:
        try:
            sonuclar, taranan, kapsam_disi = kuru_kosum(a.limit, a.kaynak)
        except KaliciHata as e:
            print("OLCULEMEDI — %s" % e)
            return 2
        rapor_yaz(sonuclar, kapsam_disi, taranan)
        return cikis_kodu(sonuclar)

    print("OLCULEMEDI — kip secilmedi (--kendini-test | --fikstur <yol> | --kuru-kosum)")
    return 2


if __name__ == "__main__":
    sys.exit(main())

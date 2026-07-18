#!/usr/bin/env python3
"""MyMiniFactory REST API ortak cekirdegi — MakerWorld makerworld-api.py'nin esdegeri.

Cok-platform genislemenin UCUNCU adaptoru (Printables + MakerWorld sonrasi); AYNI sablonu izler.

=== ANAHTAR GEREKIR (MakerWorld/Printables'ten FARK) ===
MyMiniFactory arama + detay API'si OAuth2 VEYA `key` (API anahtari) ISTER. Anahtarsiz her
endpoint 401 {"error":"access_denied","error_description":"Authentication required."} doner
(canli olcum 2026-07-18). Anahtar QUERY parametresi olarak gecer: `...?key=<APIKEY>`
(OpenAPI securityScheme: type=apiKey, in=query, name=key).

Anahtar KAYNAGI (sirayla):
  1. ortam degiskeni  MMF_KEY  (ya da MMF_TOKEN)
  2. gitignore'lu dosya  <repo>/.mmf-token         (tek satir: ham anahtar)
  3. gitignore'lu dosya  <repo>/.mmf-credentials.json  ({"key": "..."} ya da {"api_key": "..."})
Hicbiri yoksa require_key() net bir RuntimeError firlatir ("Okan API anahtari girmeli") —
UYDURMA anahtar YOK. .mmf-token / .mmf-credentials.json .gitignore'a eklendi (public repo).
Anahtar almak icin: https://www.myminifactory.com/settings/developer (Okan yapar).

=== KESFEDILEN ENDPOINT'LER (OpenAPI + canli olcum, 2026-07-18) ===
  Taban  : https://www.myminifactory.com/api/v2
  ARAMA  : GET /search?q=<terim>&page=<n>&per_page=<n>&key=<APIKEY>
           -> {"total_count": <int>, "items": [Object, ...]}
           Ek lisans-suzme parametreleri var: commercial_use / remix / exclusive (kullanmiyoruz —
           kendi FAIL-CLOSED kapimiz daha siki; ama commercial_use=1 istege bagli daraltma yapar).
  DETAY  : GET /objects/<object_id>?key=<APIKEY>   -> Object (404 -> None)
  Object : {id, url, name, description, printing_details, views, likes, dimensions (STRING!),
            designer:{username,name,...}, images:[{is_primary, original:{url}, standard:{url},
            thumbnail:{url}}], files:[{filename, viewer_url, download_url(SADECE OAuth), size}],
            categories, tags:[...], licenses:[{type,value:bool}], license (STRING)}
  INDIRME: files[].download_url + /objects/<id>/files ARSIVI SADECE OAuth ile (API key ile DEGIL).
           Yani tam STL indirilemiyor (olcu icin bkz. asagi). files[].viewer_url = kucultulmus
           onizleme STL/ply (decimate; guvenilir bbox VERMEZ) -> KULLANMIYORUZ.

=== OLCU ===
Object'te `dimensions` STRING alani var (or. "180 x 220 x 30 mm"). parse_dimensions() bunu
mm listesine cevirir -> "Yaklasik dis olculer" olarak yazilir. Bos/ayristirilamazsa None
(kaynak notuna "olcu yok" yazilir). Tam STL indirme OAuth ister; API key ile alinmaz.

=== LISANS (EN KRITIK) — gercek string -> satilabilirlik ===
MMF lisans MODELI (canli olcum 2026-07-18, object-licensing sayfasi + gercek urun sayfalari):
  * UCRETSIZ objeler CC lisanslidir. Varsayilan CC BY-NC-SA 4.0 (blog: "introducing the CC licenses").
    Urun sayfasinda IKI bicimde gorunur:
      - CIPLAK CC : "BY-NC-SA", "BY", "BY-SA", "BY-ND", "BY-NC", "BY-NC-ND", "CC0"
                    (MakerWorld gibi — "CC-" oneki YOK; canli: obje 98393 -> "BY-NC-SA")
      - BETIMLEYICI: "MyMiniFactory - Credit - Remix - Noncommercial" (eski bicim; canli:
                    obje 58065). "Credit"=atif(BY), "Remix"=turetme, "Commercial/Noncommercial"=NC.
  * UCRETLI objeler -> "Standard Digital File Store License" (kesin non-commercial, satis/remix YOK;
    object-licensing: "overrides any other licensing option ... no commercial use allowed").
  * Resmi/marka icerik -> "Official Content License" / "All Rights Reserved".
  * Ozel host -> "MyMiniFactory Exclusivity License" / "Exclusive".
  SATILABILIR : BY, BY-SA, BY-ND, CC0/Public Domain, ve BETIMLEYICI "... - Commercial" (Credit'li)
  SATILAMAZ   : NC/Noncommercial (her yazim), Standard/Store, Exclusive/Exclusivity,
                Official / All Rights Reserved, Premium, taninmayan HER SEY (FAIL-CLOSED)
Ek makine-okunur guvence: Object.licenses[] booleanlari (commercial-use / store / exclusivity).
ticari_flags() bunu okur; SADECE REDDEDER (asla kurtarmaz) — string kapisi geceni bir de flag'la
capraz dener (kor eslemeye karsi ikinci siper).

Import: dosya adinda '-' var -> `importlib.util` ile yuklenir (makerworld-api.py deseni).
Burasi tek dogruluk kaynagi (endpoint + anahtar + lisans kurali).
"""
import json, os, re, urllib.request, urllib.error, urllib.parse

ROOT = "/Users/okan/dev/pruvo"

# ---- endpoint'ler ----
BASE = "https://www.myminifactory.com/api/v2"
SEARCH = BASE + "/search"
DETAIL = BASE + "/objects/"

_HDRS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Origin": "https://www.myminifactory.com",
    "Referer": "https://www.myminifactory.com/",
}

# ---- gurultu listeleri (makerworld-api.py / printables-api.py ile ayni felsefe).
# MMF minyatur/masaustu-oyun agirlikli -> COP_OTHER (miniature/scale model) OZELLIKLE onemli.
COP_LOGO = (
    "logo", "logos", "emblem", "emblems", "emblema", "embleme", "emblème",
    "badge", "nameplate", "name plate", "symbol", "monogram", "logotipo",
    "ecusson", "écusson", "insigne", "blason", "abzeichen", "wappen",
    "stemma", "distintivo", "amblem",
    "roundel", "hood ornament", "prancing horse", "trident", "pentastar",
)
COP_MERCH = (
    "keychain", "keychains", "keyring", "key ring", "keyfob", "key fob",
    "keytag", "key tag", "keyholder", "key holder", "keyhanger", "key hanger",
    "llavero", "porte-cle", "porte cle", "porte-clef", "porte-cles", "porte cles",
    "porte-clé", "porte-clés", "porte clé", "porte clés", "porte-clefs",
    "schlusselanhanger", "schluesselanhanger", "schlüsselanhänger",
    "portachiavi", "chaveiro", "anahtarlik",
    "wall art", "wall decor", "wall decoration", "wall hanging", "wall plaque",
    "plaque", "trophy", "ornament", "pendant", "charm",
    "letters", "lettering", "sticker", "coaster", "fridge magnet", "magnet", "keycap",
    "kit card",
)
COP_OTHER = ("miniature", "miniatures", "diecast", "die-cast", "diorama", "scale model",
             "figurine", "statuette", "bust", "tabletop", "wargaming", "warhammer",
             "1:18", "1:24", "1:32", "1:43", "1:64", "1/18", "1/24", "1/43")
COP = COP_LOGO + COP_MERCH + COP_OTHER

# MMF indirme sayisi VERMEZ -> populerlik goruntuleme (views) + begeni (likes) uzerinden.
# Esikler OLCUM BEKLEYEN varsayilan (anahtar gelince kalibre edilecek; bkz. RAPOR-MIMARA.md).
POP_VIEW = 20000     # >= goruntuleme -> populer
POP_LIKE = 200       # >= begeni     -> populer


def populer(views, likes):
    return (views or 0) >= POP_VIEW or (likes or 0) >= POP_LIKE


def is_logo(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_LOGO)


def is_merch(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_MERCH)


def is_nobypass(name):
    """Populerligin DELEMEDIGI eleme: logo/amblem VEYA marka-merch formu."""
    return is_logo(name) or is_merch(name)


def is_cop(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP)


# ---- API anahtari ----
class MMFNoKey(RuntimeError):
    """MMF API anahtari yok — cagiran net rapor bassin diye ayri tip."""


def api_key():
    """Anahtari ortam/dosyadan oku (yoksa None). UYDURMA yok."""
    k = os.environ.get("MMF_KEY") or os.environ.get("MMF_TOKEN")
    if k and k.strip():
        return k.strip()
    p = os.path.join(ROOT, ".mmf-token")
    if os.path.exists(p):
        raw = open(p, encoding="utf-8").read().strip()
        if raw:
            return raw.split()[0]
    p = os.path.join(ROOT, ".mmf-credentials.json")
    if os.path.exists(p):
        try:
            j = json.load(open(p, encoding="utf-8"))
            v = j.get("key") or j.get("api_key") or j.get("token")
            if v and str(v).strip():
                return str(v).strip()
        except (json.JSONDecodeError, OSError):
            pass
    return None


def require_key():
    k = api_key()
    if not k:
        raise MMFNoKey(
            "MMF API anahtari yok. Okan girmeli: <repo>/.mmf-token dosyasina anahtari yaz "
            "(ya da MMF_KEY ortam degiskeni). Anahtar: "
            "https://www.myminifactory.com/settings/developer")
    return k


# ---- HTTP ----
def _get(url):
    req = urllib.request.Request(url, headers=_HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": _HDRS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def search(term, per_page=30, page=1):
    """MMF arama. ANAHTAR GEREKIR (yoksa MMFNoKey). {total_count, items:[Object]} doner."""
    key = require_key()
    qs = urllib.parse.urlencode({"q": term, "per_page": per_page, "page": page, "key": key})
    return _get(SEARCH + "?" + qs)


def detail(oid):
    """Tek obje detayi (/objects/<id>). ANAHTAR GEREKIR. Bulunamazsa None."""
    key = require_key()
    try:
        return _get(DETAIL + str(oid) + "?" + urllib.parse.urlencode({"key": key}))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def model_url(oid, url=None):
    """Object.url zaten tam URL doner; yoksa /object/<id>'e dus."""
    if url:
        return url
    return "https://www.myminifactory.com/object/%s" % oid


def designer_adi(d):
    des = d.get("designer") or {}
    return des.get("name") or des.get("username") or "?"


# ---- gorseller ----
def gallery_images(d, limit=8):
    """Detay JSON'undan galeri gorsel URL'leri (SIRALI, tekrarsiz). is_primary once,
    her gorselde original.url tercih, yoksa standard.url. printables/makerworld deseni."""
    seen, out = set(), []

    def _ekle(url):
        if url and url not in seen:
            seen.add(url)
            out.append(url)

    imgs = d.get("images") or []
    # is_primary olan(lar) basa
    for im in sorted(imgs, key=lambda im: 0 if im.get("is_primary") else 1):
        url = ((im.get("original") or {}).get("url")
               or (im.get("standard") or {}).get("url")
               or (im.get("thumbnail") or {}).get("url"))
        _ekle(url)
    return out[:limit]


# ---- OLCU: dimensions string -> mm ----
_BIRIM_MM = {"mm": 1.0, "millimeter": 1.0, "millimetre": 1.0,
             "cm": 10.0, "centimeter": 10.0, "centimetre": 10.0,
             "m": 1000.0, "meter": 1000.0, "metre": 1000.0,
             "in": 25.4, "inch": 25.4, "inches": 25.4, '"': 25.4}


def parse_dimensions(s):
    """MMF Object.dimensions STRING'ini mm listesine cevir (buyukten kucuge, tam sayi) ya da None.
    Bicimler: "180 x 220 x 30 mm", "180mm x 220mm x 30mm", "18 x 22 x 3 cm", "7 x 8 in".
    3 sayi + (varsa) birim yakalanamazsa None (uydurma olcu yok)."""
    if not s or not isinstance(s, str):
        return None
    low = s.lower()
    nums = re.findall(r"\d+(?:[.,]\d+)?", low)
    if len(nums) < 3:
        return None
    vals = [float(n.replace(",", ".")) for n in nums[:3]]
    # birim: string'de gecen ilk taninan birim (varsayilan mm)
    carpan = 1.0
    for tok, mm in sorted(_BIRIM_MM.items(), key=lambda t: -len(t[0])):
        if re.search(r"(?<![a-z])%s\b" % re.escape(tok) if tok.isalpha() else re.escape(tok), low):
            carpan = mm
            break
    d = sorted([v * carpan for v in vals], reverse=True)
    if d[0] <= 0 or d[0] > 100000:
        return None
    return d


# ---- LISANS (fail-closed beyaz liste) ----
def _norm(lic):
    return (lic or "").upper().strip()


def satilabilir(lic):
    """MMF lisans STRING'i ticari satisa uygun mu? BEYAZ LISTE / FAIL-CLOSED.
    SADECE bilinen ticari-serbest lisanslar True; taninmayan HER sey False (yanlis satmaktansa atla).

    MMF'nin GERCEK string'leri IKI bicimde gelir (canli olcum 2026-07-18):
      CIPLAK CC   : "BY", "BY-SA", "BY-ND", "BY-NC", "BY-NC-SA", "BY-NC-ND", "CC0"
      BETIMLEYICI : "MyMiniFactory - Credit - Remix - Noncommercial" / "... - Commercial"
      TESCILLI    : "Standard Digital File Store License", "MyMiniFactory Exclusivity License",
                    "Official Content License", "All Rights Reserved"

    Kurallar (sirayla; her adim REDDEDER ya da gecerse ilerler):
      1. Noncommercial (HER yazim: "Noncommercial", "Non-Commercial", "Non Commercial", "NC") -> False.
      2. MMF tescilli/kapali: Standard / Store / Exclusive(-ity) / Official / (All Rights) Reserved
         / Premium -> False.  (DIKKAT: "MyMiniFactory" TEK BASINA reddetmez — betimleyici CC
         bicimi de "MyMiniFactory -" ile baslar.)
      3. CC0 / Public Domain -> True.
      4. Betimleyici ticari bicim: "Commercial" tokeni (NC 1. adimda elendi) -> True.
      5. Ciplak CC-BY ailesi: "BY" tokeni (NC elendi) -> True.
      6. Yazilim lisanslari GPL / MIT / BSD -> True.
      7. Baska HER SEY (bos, uydurma) -> False (FAIL-CLOSED)."""
    s = _norm(lic)
    if not s:
        return False
    collapsed = re.sub(r"[\s\-]+", "", s)          # "NON-COMMERCIAL"->"NONCOMMERCIAL"; "BY-NC-SA"->"BYNCSA"
    toks = set(re.split(r"[\s\-/]+", s))           # "BY-NC-SA"->{BY,NC,SA}; betimleyici->{MYMINIFACTORY,CREDIT,...}
    # 1) NonCommercial -> asla
    if "NONCOMMERCIAL" in collapsed or "NC" in toks:
        return False
    # 2) MMF tescilli / kapali lisanslar -> asla
    if toks & {"STANDARD", "STORE", "OFFICIAL", "PREMIUM", "RESERVED"}:
        return False
    if any(t.startswith("EXCLUSIV") for t in toks):   # EXCLUSIVE / EXCLUSIVITY
        return False
    # 3) CC0 / Public Domain
    if "CC0" in toks or "PUBLIC" in collapsed or "PUBLICDOMAIN" in collapsed:
        return True
    # 4) betimleyici ticari bicim ("... - Commercial")
    if "COMMERCIAL" in toks:
        return True
    # 5) ciplak CC-BY aileleri (ND/SA dahil; NC yukarida elendi) — "BY" kisa kodu ya da
    #    tam ad "Attribution" (NonCommercial zaten 1. adimda collapsed ile elendi).
    if "BY" in toks or "ATTRIBUTION" in toks:
        return True
    # 6) ticari-serbest yazilim lisanslari
    if toks & {"GPL", "MIT", "BSD"}:
        return True
    # 7) fail-closed
    return False


def ticari_flags(licenses):
    """Object.licenses[] booleanlarindan makine-okunur satilabilirlik.
    Doner: True (commercial acik, store/exclusive kapali) / False (reddet) / None (bilgi yok).
    SADECE ek siper: string kapisi geceni bir de bununla capraz denenir; asla KURTARMAZ.

    licenses ogesi: {"type": "commercial-use"|"store"|"exclusivity"|"remix"|"mention"|"share",
                     "value": bool}."""
    if not licenses or not isinstance(licenses, list):
        return None
    m = {}
    for it in licenses:
        if isinstance(it, dict) and it.get("type") is not None:
            m[str(it["type"]).lower()] = bool(it.get("value"))
    if not m:
        return None
    if m.get("store") is True:                 # ucretli store lisansi
        return False
    if m.get("exclusivity") is True:           # MMF'ye ozel host
        return False
    if "commercial-use" in m:
        return m["commercial-use"] is True     # ticari kullanim acik mi?
    return None                                 # commercial-use anahtari yok -> karar verme


def cc_turu(lic):
    """Lisanstan urunler.json 'lisans.tur' (atif metni). Atif gerekmiyorsa None.
    CC0/Public/tescilli/GPL -> None; CC-BY / betimleyici-Commercial -> ilgili CC metni."""
    s = _norm(lic)
    collapsed = re.sub(r"[\s\-]+", "", s)
    toks = set(re.split(r"[\s\-/]+", s))
    if "NONCOMMERCIAL" in collapsed or "NC" in toks:
        return None                            # zaten satilamaz
    if "CC0" in toks or "PUBLIC" in collapsed:
        return None                            # atif yok
    is_by = bool(toks & {"BY", "ATTRIBUTION", "CREDIT", "COMMERCIAL"})
    if not is_by:
        return None                            # Standard/Exclusive/GPL... -> atif yok
    if "SA" in toks or "SHAREALIKE" in collapsed:
        return "CC BY-SA 4.0"
    if "ND" in toks or "NODERIV" in collapsed:
        return "CC BY-ND 4.0"
    # betimleyici bicim: Remix yoksa turetme yok -> ND
    if "COMMERCIAL" in toks and "CREDIT" in toks and "REMIX" not in toks:
        return "CC BY-ND 4.0"
    return "CC BY 4.0"


if __name__ == "__main__":
    # Hizli duman testi (ANAHTAR GEREKIR).
    if not api_key():
        print("MMF API anahtari yok — .mmf-token olustur ya da MMF_KEY ver. "
              "(https://www.myminifactory.com/settings/developer)")
        raise SystemExit(0)
    r = search("renault", per_page=3)
    print("toplam:", r.get("total_count"))
    for it in r.get("items", []):
        print(" ", it.get("id"), repr(it.get("license")), (it.get("name") or "")[:50])

#!/usr/bin/env python3
"""MakerWorld (Bambu Lab) REST API ortak cekirdegi — Printables printables-api.py'nin esdegeri.

Cok-platform genislemenin ILK adaptoru; sonraki platformlar (Cults3D vb.) bu sablonu izlesin.
TOKEN GEREKMEZ — arama + metadata + gorseller public. Model DOSYASI indirme LOGIN ISTER (asagi).

=== KESFEDILEN ENDPOINT'LER (canli olcum, 2026-07-18) ===
  ARAMA  : GET https://makerworld.com/api/v1/search-service/select/design2
             ?keyword=<terim>&limit=<n>&offset=<n>
           -> {"total": <int>, "hits": [ {id,title,slug,cover,license,downloadCount,
               likeCount,collectionCount,printCount,designCreator{name,handle},tags,nsfw,
               is_printable, ...}, ... ], "suggest":..., ...}
           NOT: dogru arama endpoint'i `select/design2` — `select/design?query=` FILTRELEMEZ
           (10000 alakasiz sonuc doner), `select/design?keyword=` her zaman total=0 doner.
           `design2` + `keyword` MakerWorld sitesinin gercekten kullandigi cift (JS bundle'dan).
  DETAY  : GET https://makerworld.com/api/v1/design-service/design/<designId>
           -> {id,title,slug,coverUrl,summary,license,designCreator{name},tags,modelId,
               instances:[{id,pictures:[{url,name,isRealLifePhoto}], ...}],
               designExtension:{design_pictures:[{url}]}, ...}
           NOT: URL'deki /models/<id> == arama hit id == detay design/<id> (hepsi ayni sayi).
  INDIRME: GET .../design-service/instance/<instanceId>/f3mf?type=stl
           -> 403 {"error":"Please log in to download models."} — LOGIN GEREKIR.
           Yani Printables'teki gibi OTOMATIK olcu (bbox) ALINAMAZ; API'de de boyut yok.
           makerworld-ekle.py bu yuzden olcusuz stage eder (kaynak notuna yazar).

=== LISANS (EN KRITIK) — gercek string -> satilabilirlik ===
MakerWorld lisanslari CC'yi CIPLAK doner ("BY", "BY-SA"... — Printables'teki "CC-BY" oneki YOK)
+ kendi tescilli lisanslari. Canli olcum (2026-07-18, 16 marka/terim, ~480 model):
  SATILABILIR : BY, BY-SA, BY-ND, CC0
  SATILAMAZ   : BY-NC, BY-NC-SA, BY-NC-ND (NonCommercial),
                "Standard Digital File License", "Standard Digital File License - Community Use",
                "MakerWorld Exclusive License"  (MakerWorld tescilli satis lisanslari)
Beyaz liste + FAIL-CLOSED: taninmayan HER lisans -> satilamaz (yanlis satmaktansa atla).

Import: dosya adinda '-' var -> normal import edilemez; `importlib.util` ile yuklenir
(printables-api.py ile ayni desen). Burasi tek dogruluk kaynagi (endpoint + lisans kurali).
"""
import json, re, urllib.request, urllib.error, urllib.parse

# ---- endpoint'ler ----
SEARCH = "https://makerworld.com/api/v1/search-service/select/design2"
DETAIL = "https://makerworld.com/api/v1/design-service/design/"
INSTANCE_DL = "https://makerworld.com/api/v1/design-service/instance/%s/f3mf?type=stl"

_HDRS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Origin": "https://makerworld.com",
    "Referer": "https://makerworld.com/",
}

# ---- gurultu listeleri (yedek parca vitrinine UYMAYAN); printables-api.py ile ayni felsefe.
# Mimar ORTAK filtreyi sonra birlestirecek (bkz. paket); simdilik burada MakerWorld'e ozel kopya.
COP_LOGO = (
    "logo", "logos", "emblem", "emblems", "emblema", "embleme", "emblème",
    "badge", "nameplate", "name plate", "symbol", "monogram", "logotipo",
    "ecusson", "écusson", "insigne", "blason", "abzeichen", "wappen",
    "stemma", "distintivo", "amblem",
    "roundel", "hood ornament", "prancing horse", "trident", "pentastar",
)
COP_MERCH = (
    "keychain", "key chain", "keychains", "keyring", "key ring", "keyfob", "key fob",
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
COP_OTHER = ("miniature", "diecast", "die-cast", "diorama", "scale model",
             "1:18", "1:24", "1:32", "1:43", "1:64", "1/18", "1/24", "1/43")
COP_FIREARM = (
    "m-lok", "mlok", "magpul", "moe grip", "moe stock", "ctr stock",
    "magwell", "cheek riser", "cheek-riser", "pistol brace", "pistol-brace",
    "picatinny", "handguard", "ar-15", "ar15", "buffer tube",
    "lower receiver", "upper receiver", "pmag",
)
COP = COP_LOGO + COP_MERCH + COP_OTHER + COP_FIREARM

POP_DL = 3000        # >= indirme -> populer
POP_LIKE = 400       # >= begeni -> populer


def populer(dl, likes):
    return (dl or 0) >= POP_DL or (likes or 0) >= POP_LIKE


def is_logo(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_LOGO)


def is_merch(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_MERCH)


def is_firearm(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_FIREARM)


def is_nobypass(name):
    """Populerligin DELEMEDIGI eleme: logo/amblem VEYA marka-merch formu."""
    return is_logo(name) or is_merch(name) or is_firearm(name)


def is_cop(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP)


# ---- HTTP ----
def _get(url):
    req = urllib.request.Request(url, headers=_HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": _HDRS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def search(term, limit=30, offset=0):
    """MakerWorld arama. keyword=<terim> ile alaka-siralı hit'ler doner."""
    qs = urllib.parse.urlencode({"keyword": term, "limit": limit, "offset": offset})
    return _get(SEARCH + "?" + qs)


def detail(pid):
    """Tek model detayi (design/<id>). Bulunamazsa None."""
    try:
        return _get(DETAIL + str(pid))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def model_url(pid, slug=None):
    return "https://makerworld.com/en/models/%s%s" % (pid, ("-" + slug) if slug else "")


# ---- gorseller ----
def gallery_images(d, limit=8):
    """Detay JSON'undan galeri gorsel URL'leri (SIRALI, tekrarsiz). Kapak once, sonra
    instance pictures (gercek-hayat fotolari basa), sonra designExtension galerisi."""
    seen, out = set(), []

    def _ekle(url):
        if url and url not in seen:
            seen.add(url)
            out.append(url)

    _ekle(d.get("coverUrl") or d.get("cover"))
    # instance pictures: gercek-hayat fotografini one al (guven verir)
    piclist = []
    for inst in (d.get("instances") or []):
        for p in (inst.get("pictures") or []):
            if p.get("url"):
                piclist.append((0 if p.get("isRealLifePhoto") else 1, p["url"]))
    for _, u in sorted(piclist, key=lambda t: t[0]):
        _ekle(u)
    for p in ((d.get("designExtension") or {}).get("design_pictures") or []):
        _ekle(p.get("url"))
    return out[:limit]


# ---- LISANS (fail-closed beyaz liste) ----
def satilabilir(lic):
    """MakerWorld lisans string'i ticari satisa uygun mu? BEYAZ LISTE / FAIL-CLOSED.
    SADECE bilinen ticari-serbest lisanslar True; taninmayan HER sey False (atla).

    MakerWorld'un GERCEK string'leri (canli olcum 2026-07-18):
      SATILABILIR : "BY", "BY-SA", "BY-ND", "CC0"
      SATILAMAZ   : "BY-NC", "BY-NC-SA", "BY-NC-ND", "Standard Digital File License",
                    "Standard Digital File License - Community Use", "MakerWorld Exclusive License"
    NOT: MakerWorld CC'yi CIPLAK verir ("BY", "CC-" ONEKI YOK) — ayni kod "CC-BY" formunu da tutar
    (token tabanli), yani ileride oneklerse yine calisir.

    Kurallar (sirayla):
      1. MakerWorld tescilli lisanslari (isim eslemesi) -> False (Standard/Exclusive/Community Use).
      2. NC (NonCommercial) tokeni -> False.
      3. CC0 / Public Domain -> True.
      4. BY (CC-BY ailesi; NC yukarida elendi) -> True.
      5. GPL / MIT / BSD -> True.
      6. Baska HER SEY (bos, uydurma) -> False (FAIL-CLOSED)."""
    s = (lic or "").upper().strip()
    if not s:
        return False
    # 1) MakerWorld tescilli / kapali lisanslar -> asla
    if "STANDARD" in s or "EXCLUSIVE" in s or "MAKERWORLD" in s:
        return False
    if "COMMUNITY USE" in s:          # "Standard ... - Community Use" -> yine kisitli
        return False
    toks = set(re.split(r"[-\s]+", s))    # "BY-NC-SA"->{BY,NC,SA}; "GPL 3.0"->{GPL,3.0}
    # 2) NonCommercial -> asla satilamaz
    if "NC" in toks:
        return False
    # 3) CC0 / Public Domain
    if "CC0" in toks or "PUBLIC" in toks:
        return True
    # 4) CC-BY aileleri (ciplak "BY" ya da "CC-BY"; NC yukarida elendi)
    if "BY" in toks:
        return True
    # 5) ticari-serbest yazilim lisanslari
    if toks & {"GPL", "MIT", "BSD"}:
        return True
    # 6) fail-closed
    return False


def cc_turu(lic):
    """Lisanstan urunler.json 'lisans.tur' (atif metni). Atif gerekmiyorsa None.
    CC0/tescilli/GPL -> None; BY* -> ilgili CC metni."""
    s = (lic or "").upper().strip()
    toks = set(re.split(r"[-\s]+", s))
    if "NC" in toks:
        return None                    # zaten satilamaz
    if "BY" not in toks:
        return None                    # CC0, Standard, Exclusive, GPL... -> atif yok
    if "SA" in toks:
        return "CC BY-SA 4.0"
    if "ND" in toks:
        return "CC BY-ND 4.0"
    return "CC BY 4.0"


# ---- model dosyasi (LOGIN GEREKIR — olcu icin best-effort) ----
def download_stl(design_id, save_path_noext, cookie=None):
    """MakerWorld model (.3mf) indirme DENEMESI. LOGIN ISTER: cookie verilmezse (varsayilan)
    403 -> RuntimeError. Cookie ile (MW_COOKIE) calisabilir. Doner: (ad, yol, uzunluk).
    printables.download_stl imzasiyla uyumlu; caginan yakalayip olcuyu None gececek."""
    d = detail(design_id)
    if not d:
        raise RuntimeError("model bulunamadi")
    insts = d.get("instances") or []
    if not insts:
        raise RuntimeError("instance yok")
    iid = insts[0].get("id") or d.get("defaultInstanceId")
    hdrs = dict(_HDRS)
    if cookie:
        hdrs["Cookie"] = cookie
    req = urllib.request.Request(INSTANCE_DL % iid, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            blob = r.read()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError("MakerWorld indirme login gerektiriyor (403)")
        raise
    save_path = save_path_noext + ".3mf"
    with open(save_path, "wb") as w:
        w.write(blob)
    return "%s.3mf" % iid, save_path, len(blob)


if __name__ == "__main__":
    # Hizli duman testi
    r = search("renault", limit=3)
    print("toplam:", r.get("total"))
    for it in r.get("hits", []):
        print(" ", it["id"], repr(it.get("license")), it.get("title", "")[:50])

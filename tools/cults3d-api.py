#!/usr/bin/env python3
# ⛔ ÇAĞIRMA — EMEKLİ (Okan 18 Tem: Cults3D rate-limit/429 yüzünden çıkarıldı)
"""Cults3D (cults3d.com) GraphQL API ortak cekirdegi — MakerWorld makerworld-api.py'nin esdegeri.

Cok-platform vitrin genislemesinin UCUNCU adaptoru (Thingiverse -> Printables -> MakerWorld ->
Cults3D). MakerWorld sablonunu birebir izler; SATILABILIRLIK KAPISI + endpoint + gorsel yardimcilari
burada, tek dogruluk kaynagi.

=== KESFEDILEN API (canli olcum + resmi/topluluk dokumantasyonu, 2026-07-18) ===
Cults3D'nin RESMI GraphQL API'si var ama MakerWorld/Printables'ten FARKLI: **TOKEN GEREKIR**.
  * GraphQL endpoint : POST https://cults3d.com/graphql  (JSON: {query, variables})
  * KIMLIK DOGRULAMA : HTTP Basic  ->  Authorization: Basic base64("<kullanici>:<api_key>")
                       (api_key = Cults3D hesap ayarlarindan; ucretsiz hesapta da alinir)
                       Kimliksiz istek -> 401 "HTTP Basic: Access denied." (canli olculdu).
  * HTML sitesi (cults3d.com/en/search...) Cloudflare "Just a moment" JS challenge ARDINDA
    (canli: 403) -> duz curl/urllib ile SCRAPE EDILEMEZ. Tek makinali yol GraphQL API'dir.
  * HIZ SINIRI (dok): ~60 istek / 30 sn, ~500 istek / gun. Yalniz GraphQL cagrilari sayilir;
    gorsel indirmeleri (cults CDN) sayilmaz.

KIMLIK NEREDEN: ortam degiskenleri (dokumandaki adlar) — birincil, sir dosyasi GEREKMEZ:
    CULTS_USERNAME / CULTS_API_KEY   (ayrica takma ad: CULTS3D_USER / CULTS3D_API_KEY)
Istege bagli dosya: CULTS3D_CREDENTIALS=/yol/creds.json ({"username":..,"api_key":..}).
  ⚠ REPO PUBLIC: kimlik dosyasini repo koku disinda tut ya da adini .gitignore'a EKLE.
  Env-var yolu hicbir dosya gerektirmez (onerilen).

=== ARAMA / DETAY ===
  ARAMA : creationsSearchBatch(query: String!, limit: Int, offset: Int) { total results { <F> } }
          (Discord bazen searchCreationsBatch der; gist/sema creationsSearchBatch — dok not).
  DETAY : creation(slug: String!) { <F> }    — slug = model URL'sinin son yol parcasi.
  <F> = Creation alanlari (asagida CREATION_FIELDS). name/url/tags LOCALE (EN) alir,
        price CURRENCY (EUR) alir, gorsel version (DEFAULT) alir.

=== LISANS (EN KRITIK) — Cults3D bir PAZAR: cok satis/kapali lisans var ===
CANLI OLCULDU (2026-07-18, kimlikli GraphQL, 320+ urun). `license` bir OBJECT; TEYIT edilen alanlar:
  { code name(locale:EN) allowsCommercialUse availableOnFreeDesigns availableOnPricedDesigns spdxId url }
`code` bir STRING (enum DEGIL). GERCEK degerler (resmi dok'un varsayimindan FARKLI cikti):
  SATILAMAZ (fail-closed'un tuttugu):
    * "cults_pu" / "CULTS PU - Private Use"  -> VARSAYILAN (en yaygin; ucretli icerigin cogu bu),
       kisisel kullanim, ticari DEGIL (acu=False). [DIKKAT: eski varsayim yanlislikla "cults_cu" diyordu.]
    * "cults_cu" / "CULTS CU - Commercial Use" + "cults_cu_nd" / "CULTS CU-ND - Commercial Use - No
       Derivative": Cults'un TICARI lisanslari (acu=True, availableOnPricedDesigns=True). SATIN
       ALINDIGINDA alicisina ticari/yeniden-satis hakki verir — BIZ satin almadigimiz icin fail-closed.
       Her "cults_*" tescilli -> False. ("cults_su" canli veride GORULMEDI.)
    * NonCommercial: "cc_by_nc", "cc_by_nc_sa", "cc_by_nc_nd" (acu=False).
    * bos / taninmayan / "All Rights Reserved" -> FAIL-CLOSED.
  SATILABILIR (beyaz liste; hepsinde Cults allowsCommercialUse=True olctu):
    * "cc_by" / "CC BY - Attribution"                  -> CC BY 4.0   (spdx CC-BY-4.0)
    * "cc_by_sa" / "CC BY-SA - ... - Share alike"      -> CC BY-SA 4.0
    * "cc_by_nd" / "CC BY-ND - ... - No derivatives"   -> CC BY-ND 4.0
    * "mit" / "MIT License" (+ gpl/bsd parite)         -> atif None
  KONTROL/YARGI — CC0: Cults'ta kod "cc_pddc" (ad "CC0 - Creative Commons public domain", spdx CC0-1.0).
    Cults kendi bayragi allowsCommercialUse=FALSE veriyor. satilabilir("cc_pddc")=False (fail-closed);
    ad formu 'cc0' tokeni ile True (evrensel CC0 hukmu) -> KOD/AD CELISKISI. lisans_str() uretimde
    code'u tercih ettigi icin CC0 urunleri pratikte ATLANIR (guvenli). CC0'i acmak = mimar+Okan karari.
NOT: satilabilir CC lisanslari yalniz UCRETSIZ tasarimlara uygulanir (availableOnFreeDesigns).
Cults ticari lisanslari (cults_cu*) yalniz UCRETLI tasarimlara (availableOnPricedDesigns) uygulanir ve
BIZ satin almadikca gecerli DEGIL. Ekle akisi price==0'i AYRICA dogrular (defense-in-depth): sadece
indirilebilir (ucretsiz) + satilabilir-lisansli alinir.

=== OLCU ===
Cults blueprint dosyalari ZIP ve indirme HESAP/SATIN-ALMA + tarayici cookie'si gerektiriyor
(dok: OrderLine.downloadUrl "requires browser cookie"). Ucuncu-taraf ucretsiz modellerin dosyasi
API'den GUVENILIR inmiyor -> MakerWorld gibi genelde OLCUSUZ stage edilir (kaynak notuna yazilir).
CULTS3D_TRY_MEASURE=1 verilirse blueprint fileUrl varsa indirip bbox DENENIR (best-effort).

Import: dosya adinda '-' var -> `importlib.util` ile yuklenir (printables-api.py deseni).
SHAPE TEYIDI (2026-07-18 canli): license{code name(locale:EN)} DOGRU; price = Money{cents value
currency formatted} — value/cents CANLI dogrulandi (ucretli: value>0/cents>0; ucretsiz: 0).
creator{nick} tek dogrulanmayan alan olarak kaldi (ekle akisi '?' fallback'i ile toleransli).
"""
import base64, io, json, os, re, struct, urllib.request, urllib.error, urllib.parse, zipfile

ENDPOINT = "https://cults3d.com/graphql"

_HDRS_BASE = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Origin": "https://cults3d.com",
    "Referer": "https://cults3d.com/",
}

# --- Creation alan seti (TEK KAYNAK). Kesin-olmayan alanlar isaretli: ilk canli kosumda dogrula.
CREATION_FIELDS = """
  id
  name(locale: EN)
  url(locale: EN)
  shortUrl
  license { code name(locale: EN) }        # <-- kesin degil: shape license{code,name} varsayildi
  price(currency: EUR) { value }            # <-- kesin degil: MoneyType alani 'value' varsayildi
  downloadsCount
  likesCount
  illustrationImageUrl(version: DEFAULT)
  illustrations { imageUrl(version: DEFAULT) }
  tags(locale: EN)
  creator { nick }                          # <-- kesin degil: yazar alani 'creator{nick}' varsayildi
"""

SEARCH_Q = "query S($q: String!, $limit: Int!, $offset: Int) {" \
           "  creationsSearchBatch(query: $q, limit: $limit, offset: $offset) {" \
           "    total results {" + CREATION_FIELDS + "} } }"

DETAIL_Q = "query D($slug: String!) { creation(slug: $slug) {" + CREATION_FIELDS + "} }"

BLUEPRINT_Q = "query B($slug: String!) { creation(slug: $slug) {" \
              "  blueprints { fileUrl } illustrations { imageUrl(version: DEFAULT) } } }"

# ---- gurultu listeleri (yedek parca vitrinine UYMAYAN); makerworld-api.py ile ayni felsefe.
# Mimar ORTAK filtreyi sonra birlestirecek; simdilik burada Cults3D'ye ozel kopya.
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
POP_LIKE = 400       # >= begeni  -> populer


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


# ---- KIMLIK ----
# repo koku (tools/ -> ust dizin). Worktree'de gitignore'lu kimlik dosyasi bulunmayabilir; bu yuzden
# kanonik ANA repo yolu da varsayilanlara eklenir (myminifactory-api.py'nin hardcoded ROOT deseni gibi).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_CRED_PATHS = (
    os.path.join(_ROOT, ".cults3d-credentials.json"),
    "/Users/okan/dev/pruvo/.cults3d-credentials.json",
)


def _read_cred_file(path):
    """creds.json -> (user, key) ya da (None, None). Bozuk/eksik dosyada sessizce (None, None)."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None
    u = d.get("username") or d.get("user")
    k = d.get("api_key") or d.get("apiKey") or d.get("key")
    return (u, k) if (u and k) else (None, None)


def _credentials():
    """(kullanici, api_key) — ortam degiskeni (birincil), sonra CULTS3D_CREDENTIALS dosyasi, sonra
    repo-koku VARSAYILAN dosya (.cults3d-credentials.json — env gerektirmez, MMF deseni).
    Bulunamazsa RuntimeError (net mesaj). Import aninda CAGRILMAZ (tembel)."""
    user = os.environ.get("CULTS_USERNAME") or os.environ.get("CULTS3D_USER")
    key = os.environ.get("CULTS_API_KEY") or os.environ.get("CULTS3D_API_KEY")
    if user and key:
        return user, key
    # once acik dosya yolu (env), sonra repo-koku varsayilanlari; ilk gecerli dosya kazanir.
    env_path = os.environ.get("CULTS3D_CREDENTIALS")
    candidates = ([env_path] if env_path else []) + list(_DEFAULT_CRED_PATHS)
    for p in candidates:
        if p and os.path.exists(p):
            u, k = _read_cred_file(p)
            if u and k:
                return u, k
    raise RuntimeError(
        "Cults3D kimligi yok. Ver: CULTS_USERNAME + CULTS_API_KEY ortam degiskenleri "
        "(ya da CULTS3D_CREDENTIALS=/yol/creds.json; ya da repo-koku .cults3d-credentials.json). "
        "api_key: Cults3D hesap ayarlari > API.")


def _auth_header():
    user, key = _credentials()
    tok = base64.b64encode(("%s:%s" % (user, key)).encode("utf-8")).decode("ascii")
    return "Basic " + tok


def _hdrs():
    h = dict(_HDRS_BASE)
    h["Authorization"] = _auth_header()
    return h


# ---- HTTP ----
def gql(query, variables=None):
    """GraphQL sorgusu (Basic auth ile). `data`'yi dondurur; hata varsa RuntimeError.
    401 -> kimlik hatasi net mesajla yeniden firlatilir."""
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers=_hdrs())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("Cults3D 401: kimlik gecersiz/eksik (CULTS_USERNAME/CULTS_API_KEY).")
        raise
    if d.get("errors"):
        raise RuntimeError("Cults3D GraphQL hata: %s" % (d["errors"][0].get("message", d["errors"])))
    return d["data"]


def http_get(url):
    """Gorsel/dosya indir (CDN — kimlik gerekmez, hiz siniri saymaz)."""
    req = urllib.request.Request(url, headers={"User-Agent": _HDRS_BASE["User-Agent"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def search(term, limit=30, offset=0):
    """Cults3D arama. {total, results:[Creation,...]} dondurur (bos ise {'total':0,'results':[]})."""
    d = gql(SEARCH_Q, {"q": term, "limit": limit, "offset": offset})
    return d.get("creationsSearchBatch") or {"total": 0, "results": []}


def detail(slug):
    """Tek model detayi (creation(slug:)). Bulunamazsa None."""
    d = gql(DETAIL_Q, {"slug": slug})
    return d.get("creation")


# ---- URL / slug ----
def model_url(c):
    """Creation dict'inden model URL'si (url > shortUrl)."""
    return c.get("url") or c.get("shortUrl") or ""


def slug_of(c_or_url):
    """Creation dict'i ya da URL string'inden slug (URL'nin son yol parcasi, sorgu/hash yok)."""
    url = c_or_url if isinstance(c_or_url, str) else model_url(c_or_url)
    url = url.split("?")[0].split("#")[0].rstrip("/")
    return url.rsplit("/", 1)[-1] if url else ""


# ---- gorseller ----
def gallery_images(c, limit=8):
    """Creation'dan galeri gorsel URL'leri (SIRALI, tekrarsiz). Kapak (illustrationImageUrl)
    once, sonra illustrations[].imageUrl."""
    seen, out = set(), []

    def _ekle(url):
        if url and url not in seen:
            seen.add(url)
            out.append(url)

    _ekle(c.get("illustrationImageUrl"))
    for il in (c.get("illustrations") or []):
        _ekle(il.get("imageUrl"))
    return out[:limit]


# ---- FIYAT (ucretsiz mi) ----
def ucretsiz(c):
    """Model ucretsiz mi? price null -> ucretsiz kabul; value==0 -> ucretsiz; value>0 -> ucretli."""
    p = c.get("price")
    if not p:
        return True
    try:
        return float(p.get("value") or 0) == 0
    except (TypeError, ValueError):
        return True


# ---- LISANS ----
def lisans_str(c):
    """Creation dict'inden lisans string'i (kanonik code tercih; yoksa name; yoksa licenseCode).
    satilabilir()/cc_turu() bunu alir. Shape'e toleransli (license{code,name} | scalar)."""
    lic = c.get("license")
    if isinstance(lic, dict):
        return lic.get("code") or lic.get("name") or ""
    if isinstance(lic, str):
        return lic
    return c.get("licenseCode") or ""


def lisans_ad(c):
    """Insan-okur lisans adi (kaynak kaydi icin). Yoksa code'a duser."""
    lic = c.get("license")
    if isinstance(lic, dict):
        return lic.get("name") or lic.get("code") or ""
    if isinstance(lic, str):
        return lic
    return c.get("licenseCode") or ""


def satilabilir(lic):
    """Cults3D lisansi (code YA DA insan-adi) ticari satisa uygun mu? BEYAZ LISTE / FAIL-CLOSED.
    SADECE bilinen ticari-serbest CC lisanslari True; taninmayan/tescilli/NC HER sey False.

    Kurallar (sirayla — yasakli olan once):
      1. Cults tescilli lisanslari ("cults" tokeni: cults_cu / cults_su / Cults - Private/Standard
         use ...) -> False. Bu VARSAYILAN + ucretli-ticari lisanslari kapsar.
      2. NonCommercial (nc / noncommercial / non-commercial) -> False.
      3. "personal use" / "private use" (cults'suz tescilli ifade) -> False.
      4. CC0 / Public Domain -> True.
      5. CC-BY aileleri (cc+by ya da 'attribution'; NC yukarida elendi) -> True.
      6. GPL / MIT / BSD (parite; Cults sunmaz) -> True.
      7. Baska HER SEY (bos, uydurma, All Rights Reserved) -> False (FAIL-CLOSED)."""
    s = (lic or "").strip().lower()
    if not s:
        return False
    toks = set(re.split(r"[^a-z0-9]+", s))
    toks.discard("")
    # 1) Cults tescilli (private use / standard use / her cults_*)
    if "cults" in toks:
        return False
    # 2) NonCommercial
    if "nc" in toks or "noncommercial" in toks or "noncommercial" in s or "non-commercial" in s \
            or ("non" in toks and "commercial" in toks):
        return False
    # 3) tescilli kisisel-kullanim ifadesi
    if "personal" in toks or ("private" in toks and "use" in toks):
        return False
    # 4) CC0 / Public Domain
    if "cc0" in toks or "public" in toks:
        return True
    # 5) CC-BY aileleri
    if ("cc" in toks and "by" in toks) or "attribution" in toks:
        return True
    # 6) ticari-serbest yazilim lisanslari
    if toks & {"gpl", "mit", "bsd"}:
        return True
    # 7) fail-closed
    return False


def cc_turu(lic):
    """Lisanstan urunler.json 'lisans.tur' (atif metni). Atif gerekmiyorsa None.
    CC0/public/tescilli/NC -> None; CC-BY* -> ilgili CC metni."""
    s = (lic or "").strip().lower()
    toks = set(re.split(r"[^a-z0-9]+", s))
    toks.discard("")
    if "cults" in toks or "nc" in toks or "noncommercial" in s or "non-commercial" in s:
        return None
    if "cc0" in toks or "public" in toks:
        return None
    is_cc = ("cc" in toks and "by" in toks) or "attribution" in toks
    if not is_cc:
        return None
    if "sa" in toks or ("share" in toks and "alike" in toks):
        return "CC BY-SA 4.0"
    if "nd" in toks or ("no" in toks and ("derivatives" in toks or "derivs" in toks)):
        return "CC BY-ND 4.0"
    return "CC BY 4.0"


# ---- OLCU (best-effort — blueprint indirme genelde hesap/satin-alma gerektirir) ----
def _stl_bbox(path):
    """STL sinir kutusu (mm, buyukten kucuge liste) ya da None. ASCII + binary STL."""
    with open(path, "rb") as f:
        data = f.read()
    head = data[:512].lstrip().lower()
    if head.startswith(b"<") or b"<html" in head or b"just a moment" in head:
        return None
    xs, ys, zs = [], [], []
    if b"vertex" in data[:2000] or data[:5].lower() == b"solid":
        for line in data.decode("utf-8", "ignore").splitlines():
            p = line.strip().split()
            if len(p) == 4 and p[0] == "vertex":
                try:
                    xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
                except ValueError:
                    pass
    if not xs and len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + n * 50 != len(data):
            return None
        off = 84
        for _ in range(n):
            if off + 48 > len(data):
                break
            v = struct.unpack("<12f", data[off:off + 48]); off += 50
            for j in range(3, 12, 3):
                xs.append(v[j]); ys.append(v[j + 1]); zs.append(v[j + 2])
    if not xs:
        return None
    d = sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)
    if d[0] < 2.0:
        d = [x * 1000 for x in d]
    if d[0] <= 0 or d[0] > 100000:
        return None
    return d


def model_bbox(path):
    """Uzantiya gore olcum. .stl -> _stl_bbox. .3mf/diger -> None (best-effort kapsam disi)."""
    return _stl_bbox(path) if path.lower().endswith(".stl") else None


def blueprint_urls(slug):
    """Detaydan blueprint dosya URL'leri (ZIP). Ucuncu-taraf modelde genelde BOS gelir."""
    d = gql(BLUEPRINT_Q, {"slug": slug})
    c = d.get("creation") or {}
    return [b.get("fileUrl") for b in (c.get("blueprints") or []) if b.get("fileUrl")]


def download_stl(slug, save_path_noext):
    """Blueprint (ZIP) indirip icindeki EN BUYUK .stl'i cikarir. LOGIN/SATIN-ALMA GEREKIR:
    blueprint fileUrl yoksa RuntimeError (MakerWorld indirme gibi olcu ALINAMAZ). Doner:
    (dosya_adi, kaydedilen_yol, bayt). ekle akisi yakalayip olcuyu None gececek."""
    urls = blueprint_urls(slug)
    if not urls:
        raise RuntimeError("Cults3D blueprint fileUrl yok (indirme hesap/satin-alma gerektirir)")
    blob = http_get(urls[0])
    # ZIP ise en buyuk .stl uyesini cikar; degilse dogrudan STL varsay
    if blob[:2] == b"PK":
        buf = zipfile.ZipFile(io.BytesIO(blob))
        stls = [n for n in buf.namelist() if n.lower().endswith(".stl")]
        if not stls:
            raise RuntimeError("ZIP icinde .stl yok")
        stls.sort(key=lambda n: buf.getinfo(n).file_size, reverse=True)
        data = buf.read(stls[0])
        name = stls[0]
    else:
        data, name = blob, slug + ".stl"
    save_path = save_path_noext + ".stl"
    with open(save_path, "wb") as w:
        w.write(data)
    return name, save_path, len(data)


if __name__ == "__main__":
    # Hizli duman testi (KIMLIK GEREKIR — env: CULTS_USERNAME + CULTS_API_KEY)
    try:
        r = search("renault", limit=3)
    except RuntimeError as e:
        raise SystemExit("Kimlik/erisim: %s" % e)
    print("toplam:", r.get("total"))
    for c in r.get("results", []):
        print(" ", slug_of(c), repr(lisans_str(c)), "ucretsiz=%s" % ucretsiz(c),
              (c.get("name") or "")[:50])

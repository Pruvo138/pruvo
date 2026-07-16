#!/usr/bin/env python3
"""Printables (Prusa) GraphQL API ortak cekirdegi — Thingiverse yardimcilarinin esdegeri.

Printables'in RESMI REST API'si YOK; site `https://api.printables.com/graphql/` GraphQL
endpoint'ini kullanir. TOKEN GEREKMEZ — arama + metadata + gorseller + STL INDIRME public.

STL indirme: `getDownloadLink` mutation'i login OLMADAN calisir (test edildi, ok:true),
`files.printables.com` uzerinde 24 saat gecerli imzali link verir. Yani Thingiverse'teki gibi
otomatik STL cekip olcebiliyoruz (bkz. download_stl / tools/printables-fetch.py).

Import edilebilir (from printables_api import ...) DEGIL — dosya adinda '-' var; bunun yerine
diger araclar bu modulu `runpy`/subprocess yerine kendi kopyasiyla degil, ortak fonksiyonlari
kullanmak isterse: `import importlib.util` ile yukler. Basitlik icin arama/meta araclari
kendi kucuk gql() sarmalayicisini tutar; buradaki degerler (ENDPOINT, MEDIA, lisans kurali)
tek dog­ruluk kaynagidir.
"""
import json, re, struct, urllib.request, zipfile, io
import xml.etree.ElementTree as ET

ENDPOINT = "https://api.printables.com/graphql/"
MEDIA = "https://media.printables.com/"   # + filePath  ->  tam gorsel URL'si

# Yedek parca vitrinine UYMAYAN gurultu (thing-ara.py ile ayni liste — birlikte guncelle).
# LOGO + MERCH: marka logosu/amblemini biz baskiyla URETEN urunler — telif/marka hakki riski
# nedeniyle POPULERLIK BILE DELMEZ, her zaman elenir (Okan, 2026-07-14). Ilke: logonun kaynak
# gorselinde gorunmesi degil, logoyu BASKIYLA uretmemiz sorunludur; bu yuzden logo-tasiyan
# aksesuar/merch formlari (anahtarlik/duvar-askisi/plaket/trofe...) da hep elenir.
# NOT: cok-dilli terimler eklendi (kacan yabanci basliklar: Llavero, Schlusselanhanger, ecusson).
# Model-adi CAKISMASI olanlar bilerek DISARIDA (Opel "Insignia", Suzuki "Escudo" -> gecerli parca).
COP_LOGO = (
    # cok dilli logo/amblem/rozet
    "logo", "logos", "emblem", "emblems", "emblema", "embleme", "emblème",
    "badge", "nameplate", "name plate", "symbol", "monogram", "logotipo",
    "ecusson", "écusson", "insigne", "blason", "abzeichen", "wappen",
    "stemma", "distintivo", "amblem",
    # markaya ozel sembol adlari (metinde gecerse logo demektir)
    "roundel", "hood ornament", "prancing horse", "trident", "pentastar",
)
# Marka markasini SERGILEYEN/tasiyan aksesuar-merch formlari — logo reprodüksiyonu sayilir,
# POPULERLIK DELMEZ (cok dilli anahtarlik + duvar susu/plaket/trofe/rozet).
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
)
# Populerlik DELEBILIR gurultu (olcek modeli/minyatur) — cok talep goren biri yine de alinir.
COP_OTHER = ("miniature", "diecast", "die-cast", "diorama", "scale model",
             "1:18", "1:24", "1:32", "1:43", "1:64", "1/18", "1/24", "1/43", "kit card")
COP = COP_LOGO + COP_MERCH + COP_OTHER

# POPULERLIK: cok talep goren urun (asagidaki esigi asan) COP_OTHER/yasakli olsa bile ALINIR
# ve aramada EN UST onceligi alir. LOGO icin bu istisna GECERSIZ (asagida is_logo ile ayri
# kontrol edilir). (NC lisans esigi de AYRI ve delinmez — yasal kisit.)
POP_DL = 3000        # >= bu kadar indirme  -> populer
POP_LIKE = 400       # >= bu kadar begeni   -> populer


def populer(dl, likes):
    return (dl or 0) >= POP_DL or (likes or 0) >= POP_LIKE


def is_logo(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_LOGO)


def is_merch(name):
    """Marka-logolu aksesuar/merch formu mu (anahtarlik/askı/plaket/trofe...)?
    LOGO gibi: populerlik DELMEZ."""
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP_MERCH)


def is_nobypass(name):
    """Populerligin DELEMEDIGI eleme: logo/amblem VEYA marka-merch formu."""
    return is_logo(name) or is_merch(name)


_HDRS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Origin": "https://www.printables.com",
    "Referer": "https://www.printables.com/",
}


def gql(query, variables=None):
    """GraphQL sorgusu calistir, `data`'yi dondur (hata varsa exception)."""
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers=_HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    if d.get("errors"):
        raise RuntimeError(d["errors"][0].get("message", "GraphQL hata"))
    return d["data"]


def img_url(file_path):
    return MEDIA + file_path.lstrip("/")


def is_cop(name):
    n = " " + (name or "").lower() + " "
    return any(c in n for c in COP)


def satilabilir(abbr):
    """Lisans kisaltmasi ticari satisa uygun mu? CC-...-NC (Non-Commercial) -> HAYIR.
    OCL (Prusa Open Community License v1/v1.1) -> HAYIR: tasarimdan uretilen urunun
    SATISI ayri anlasma olmadan yasak (dogrulandi 2026-07-15, prusa3d.com/OCL_v1.pdf)."""
    a = (abbr or "").upper()
    if "NC" in a.split("-"):        # CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND ...
        return False
    if a.startswith("OCL"):         # OCL v1, OCL v1.1 ...
        return False
    return True                     # CC-BY, CC-BY-SA, CC-BY-ND, CC0, BSD, GPL, MIT, Standard Digital ...


def model_url(pid, slug=None):
    return "https://www.printables.com/model/%s%s" % (pid, ("-" + slug) if slug else "")


def cc_turu(abbr):
    """Lisans kisaltmasindan urunler.json 'lisans.tur' degeri (atif icin). Atif gerekmiyorsa None.
    CC0/public domain/GPL/BSD/standart -> None; CC-BY* -> ilgili CC metni."""
    a = (abbr or "").upper()
    if "CC0" in a or "PUBLIC" in a:
        return None
    if a.startswith("CC-BY") or a.startswith("CC BY"):
        if "SA" in a.split("-"):
            return "CC BY-SA 4.0"
        if "ND" in a.split("-"):
            return "CC BY-ND 4.0"
        return "CC BY 4.0"
    return None


def stl_bbox(path):
    """STL dosyasinin sinir kutusu olcusu (mm, buyukten kucuge, tam sayi liste) ya da None.
    HTML/bozuk dosyalari eler; metre gelirse mm'ye cevirir."""
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


# 3MF spec'i birim serbest birakir; olcuyu mm'ye cevirmek icin carpan.
# unit yoksa spec varsayilani millimeter.
_3MF_BIRIM_MM = {"micron": 0.001, "millimeter": 1.0, "centimeter": 10.0,
                 "inch": 25.4, "foot": 304.8, "meter": 1000.0}

# 4x4 birim matris (satir-vektor bilesigi icin notr eleman).
_3MF_BIRIM_MAT = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]


def _yerel(tag):
    """ElementTree '{namespace}tag' -> 'tag' (namespace-bagimsiz karsilastirma icin)."""
    return tag.rsplit("}", 1)[-1]


def _oznitelik(el, ad):
    """Namespace onekli/oneksiz oznitelik degeri ( or. production ext'teki p:path)."""
    v = el.get(ad)
    if v is not None:
        return v
    for k, val in el.attrib.items():
        if k.rsplit("}", 1)[-1] == ad:
            return val
    return None


def _matris(metin):
    """3MF transform ozniteligi -> 4x4 matris. 12 sayi satir-major afin: m00 m01 m02
    m10 m11 m12 m20 m21 m22 m30 m31 m32 (son uc = oteleme). Hatali/eksikse None."""
    s = (metin or "").split()
    if len(s) != 12:
        return None
    try:
        m = [float(x) for x in s]
    except ValueError:
        return None
    return [[m[0], m[1], m[2], 0.0],
            [m[3], m[4], m[5], 0.0],
            [m[6], m[7], m[8], 0.0],
            [m[9], m[10], m[11], 1.0]]


def _carp(A, B):
    """4x4 bileske (satir-vektor gelenegi: once A sonra B uygulanir)."""
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _uygula(M, x, y, z):
    """[x y z 1] @ M -> (x', y', z') (3MF'de noktalar satir-vektor)."""
    return (x * M[0][0] + y * M[1][0] + z * M[2][0] + M[3][0],
            x * M[0][1] + y * M[1][1] + z * M[2][1] + M[3][1],
            x * M[0][2] + y * M[1][2] + z * M[2][2] + M[3][2])


def bbox_3mf(path):
    """3MF sinir kutusu olcusu (mm, buyukten kucuge liste) ya da None — STL yoksa yedek olcum.

    Bambu-Studio tarzi cok-.model arsivlerinde geometri 3D/Objects/*.model altindadir; kok
    3D/3dmodel.model yalniz montaj (build item + component referanslari) tutar, vertex icermez.
    Bu yuzden arsivdeki TUM .model uyeleri parse edilir, (dosya, object id) -> element haritasi
    kurulur, <build> item'larindan baslayip component zincirini (p:path ile baska .model'e
    referans + transform matrisleri) coza coza DONUSTURULMUS vertex'lerin birlesik min/max'i
    alinir. build/item yoksa ya da cozum bir seye ulasamazsa tum .model'lerdeki HAM vertex'lerin
    (transform'suz) birlesigine duser. Cikti her zaman MM (dosya birimi ne olursa olsun)."""
    try:
        modeller = {}   # normalize yol (bas '/' yok) -> ET root
        with zipfile.ZipFile(path) as z:
            adlar = [n for n in z.namelist() if n.lower().endswith(".model")]
            if not adlar:
                return None
            for n in adlar:
                try:
                    modeller[n.lstrip("/")] = ET.fromstring(z.read(n))
                except ET.ParseError:
                    pass
        if not modeller:
            return None

        def _build_el(root):
            for ch in root:
                if _yerel(ch.tag) == "build":
                    return ch
            return None

        # Birim: kok modelin (build item'i olan) unit'i — spec model-genelinde tanimli.
        # Okumazsan metre 1000x kucuk cikar, inch/cm MAKUL GORUNEN ama yanlis sayi uretir.
        kok = None
        for root in modeller.values():
            b = _build_el(root)
            if b is not None and list(b):
                kok = root
                break
        if kok is None:
            kok = next(iter(modeller.values()))
        bm = kok.get("unit") or "millimeter"
        carpan = _3MF_BIRIM_MM.get(bm.lower())
        if carpan is None:
            return None                  # tanimadigimiz birim -> uydurma, olcusuz birak

        # her .model icin object id -> element haritasi
        objeler = {}
        for yol, root in modeller.items():
            h = {}
            for obj in root.iter():
                if _yerel(obj.tag) == "object" and obj.get("id") is not None:
                    h[obj.get("id")] = obj
            objeler[yol] = h

        xs, ys, zs = [], [], []

        def _vertices_el(obj):
            for ch in obj:
                if _yerel(ch.tag) == "mesh":
                    for gch in ch:
                        if _yerel(gch.tag) == "vertices":
                            return gch
            return None

        def _coz(yol, oid, M, derinlik):
            if derinlik > 50:            # dongusel referansa karsi tavan
                return
            obj = objeler.get(yol, {}).get(oid)
            if obj is None:
                return
            vs = _vertices_el(obj)
            if vs is not None:
                for vx in vs:
                    if _yerel(vx.tag) != "vertex":
                        continue
                    try:
                        x = float(vx.get("x")); y = float(vx.get("y")); z = float(vx.get("z"))
                    except (TypeError, ValueError):
                        continue
                    px, py, pz = _uygula(M, x, y, z)
                    xs.append(px); ys.append(py); zs.append(pz)
            for ch in obj:
                if _yerel(ch.tag) != "components":
                    continue
                for comp in ch:
                    if _yerel(comp.tag) != "component":
                        continue
                    cid = comp.get("objectid")
                    if cid is None:
                        continue
                    cyol = _oznitelik(comp, "path")      # baska .model'e referans olabilir
                    cyol = cyol.lstrip("/") if cyol else yol
                    T = _matris(comp.get("transform")) or _3MF_BIRIM_MAT
                    _coz(cyol, cid, _carp(T, M), derinlik + 1)

        # build item'lardan transform zincirini cozerek dolas
        for yol, root in modeller.items():
            b = _build_el(root)
            if b is None:
                continue
            for item in b:
                if _yerel(item.tag) != "item" or item.get("objectid") is None:
                    continue
                T = _matris(item.get("transform")) or _3MF_BIRIM_MAT
                _coz(yol, item.get("objectid"), T, 0)

        # geri-dusus: cozum bos donduyse tum modellerin ham vertex'leri (transform'suz)
        if not xs:
            for root in modeller.values():
                for vx in root.iter():
                    if _yerel(vx.tag) != "vertex":
                        continue
                    try:
                        x = float(vx.get("x")); y = float(vx.get("y")); z = float(vx.get("z"))
                    except (TypeError, ValueError):
                        continue
                    xs.append(x); ys.append(y); zs.append(z)
        if not xs:
            return None

        d = sorted([(max(xs) - min(xs)) * carpan,
                    (max(ys) - min(ys)) * carpan,
                    (max(zs) - min(zs)) * carpan], reverse=True)
        if d[0] <= 0 or d[0] > 100000:
            return None
        return d
    except Exception:
        return None                      # sozlesme: hicbir durumda firlatma, olcemezsen None


def model_bbox(path):
    """Uzantiya gore doğru olcum fonksiyonuna yonlendirir (.stl veya .3mf)."""
    if path.lower().endswith(".3mf"):
        return bbox_3mf(path)
    return stl_bbox(path)


def strip_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "", flags=re.I)
    s = re.sub(r"</p>", "\n\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
    return re.sub(r"\n{3,}", "\n\n", s).strip()


SEARCH_Q = """
query S($q: String!, $limit: Int!, $offset: Int, $ordering: SearchChoicesEnum) {
  searchPrints2(query: $q, limit: $limit, offset: $offset, ordering: $ordering) {
    totalCount
    items {
      id name slug downloadCount likesCount ratingAvg filesCount imagesCount
      license { name abbreviation }
      user { publicUsername }
      image { filePath }
    }
  }
}
"""

DETAIL_Q = """
query D($id: ID!) {
  print(id: $id) {
    id name slug summary description
    license { name abbreviation }
    user { publicUsername }
    filesCount imagesCount downloadCount likesCount ratingAvg thingiverseLink
    images { id order filePath }
    stls { id name fileSize }
  }
}
"""


DL_M = """
mutation DL($printId: ID!, $files: [DownloadFileInput], $source: DownloadSourceEnum!) {
  getDownloadLink(printId: $printId, files: $files, source: $source) {
    ok
    errors { field messages }
    output { link ttl count }
  }
}
"""


def search(term, limit=30, offset=0, ordering="popular"):
    return gql(SEARCH_Q, {"q": term, "limit": limit, "offset": offset, "ordering": ordering})["searchPrints2"]


def detail(pid):
    return gql(DETAIL_Q, {"id": str(pid)})["print"]


def download_link(print_id, file_ids, file_type="stl"):
    """getDownloadLink mutation'i — imzali (24s TTL) indirme URL'si dondurur. Login GEREKMEZ.
    file_ids: tek dosyada tek eleman -> tek dosyanin STL linki; birden fazla -> ZIP paketi."""
    v = {"printId": str(print_id), "source": "model_detail",
         "files": [{"fileType": file_type, "ids": [str(i) for i in file_ids]}]}
    r = gql(DL_M, v)["getDownloadLink"]
    if not r.get("ok"):
        raise RuntimeError("getDownloadLink basarisiz: %s" % (r.get("errors")))
    return r["output"]["link"]


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": _HDRS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _is_stl_bytes(blob):
    """Indirilen baytlarin GERCEKTEN STL olup olmadigini dogrular. Printables bazen .stl
    uzantili dosya icin sessizce bir PNG kucuk resim donduruyor (Suzuki partisinde
    yakalandi, 2026-07-16) - bu da olcusuz/yanlis-olculu urun stage edilmesine yol acar.
    ASCII STL: "solid" ile baslar. Binary STL: 80 bayt basligin ardindan gelen uint32
    ucgen sayisi, kalan bayt uzunlugunu (n*50) tam karsilamalidir."""
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        return False
    if blob[:5].lower() == b"solid":
        return True
    if len(blob) >= 84:
        (n,) = struct.unpack("<I", blob[80:84])
        if n > 0 and 84 + n * 50 == len(blob):
            return True
    return False


def download_stl(print_id, save_path_noext):
    """Modelin EN BUYUK gercek dosyasini indirir (.stl tercih edilir; yoksa .3mf'e duser —
    step/obj gibi baski disi formatlar alinmaz). save_path_noext + dogru uzanti ile yazar.
    Doner: (gercek_dosya_adi, kaydedilen_yol, bayt_uzunlugu). Uygun dosya yoksa RuntimeError."""
    d = detail(print_id)
    files = d.get("stls") or []
    stls = [s for s in files if (s.get("name") or "").lower().endswith(".stl")]
    threemf = [s for s in files if (s.get("name") or "").lower().endswith(".3mf")]
    pool = stls or threemf
    if not pool:
        raise RuntimeError("bu modelde .stl/.3mf yok (sadece step/obj olabilir)")
    pool.sort(key=lambda s: s.get("fileSize") or 0, reverse=True)  # en buyuk = ana parca
    chosen = pool[0]
    ext = ".stl" if stls else ".3mf"
    save_path = save_path_noext + ext
    link = download_link(print_id, [chosen["id"]], "stl")
    blob = http_get(link)
    if ext == ".stl" and not _is_stl_bytes(blob):
        raise RuntimeError("indirilen dosya STL degil (Printables PNG/baska format donmus olabilir): %s" % chosen["name"])
    with open(save_path, "wb") as w:
        w.write(blob)
    return chosen["name"], save_path, len(blob)


if __name__ == "__main__":
    # Hizli duman testi
    r = search("renault", limit=3)
    print("toplam:", r["totalCount"])
    for it in r["items"]:
        print(" ", it["id"], it["license"]["abbreviation"], it["name"][:50])

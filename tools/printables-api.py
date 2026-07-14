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
import json, re, struct, urllib.request

ENDPOINT = "https://api.printables.com/graphql/"
MEDIA = "https://media.printables.com/"   # + filePath  ->  tam gorsel URL'si

# Yedek parca vitrinine UYMAYAN gurultu (thing-ara.py ile ayni liste).
COP = ("keychain", "keyring", "key ring", "keyfob", "key fob", "keytag", "key tag", "keyholder",
       "key holder", "keychains", "logo", "logos", "emblem", "badge", "nameplate", "name plate",
       "letters", "lettering", "symbol", "monogram", "sticker", "wall art", "trophy",
       "coaster", "fridge magnet", "magnet",
       "miniature", "diecast", "die-cast", "diorama", "scale model", "1:18", "1:24", "1:32",
       "1:43", "1:64", "1/18", "1/24", "1/43", "keycap", "kit card")

# POPULERLIK: cok talep goren urun (asagidaki esigi asan) COP/yasakli olsa bile ALINIR ve
# aramada EN UST onceligi alir. (NC lisans esigi AYRI ve delinmez — yasal kisit.)
POP_DL = 3000        # >= bu kadar indirme  -> populer
POP_LIKE = 400       # >= bu kadar begeni   -> populer


def populer(dl, likes):
    return (dl or 0) >= POP_DL or (likes or 0) >= POP_LIKE


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
    """Lisans kisaltmasi ticari satisa uygun mu? CC-...-NC (Non-Commercial) -> HAYIR."""
    a = (abbr or "").upper()
    if "NC" in a.split("-"):        # CC-BY-NC, CC-BY-NC-SA, CC-BY-NC-ND ...
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


def download_stl(print_id, save_path):
    """Modelin EN BUYUK gercek .stl'ini indirir save_path'e yazar. Bytes uzunlugunu dondurur.
    (.step/.3mf/.obj disi; sadece .stl. Yoksa RuntimeError.)"""
    d = detail(print_id)
    stls = [s for s in (d.get("stls") or []) if (s.get("name") or "").lower().endswith(".stl")]
    if not stls:
        raise RuntimeError("bu modelde .stl yok (sadece step/3mf olabilir)")
    stls.sort(key=lambda s: s.get("fileSize") or 0, reverse=True)  # en buyuk = ana parca
    link = download_link(print_id, [stls[0]["id"]], "stl")
    blob = http_get(link)
    with open(save_path, "wb") as w:
        w.write(blob)
    return stls[0]["name"], len(blob)


if __name__ == "__main__":
    # Hizli duman testi
    r = search("renault", limit=3)
    print("toplam:", r["totalCount"])
    for it in r["items"]:
        print(" ", it["id"], it["license"]["abbreviation"], it["name"][:50])

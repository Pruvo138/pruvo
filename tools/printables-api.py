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
import json, re, urllib.request

ENDPOINT = "https://api.printables.com/graphql/"
MEDIA = "https://media.printables.com/"   # + filePath  ->  tam gorsel URL'si

# Yedek parca vitrinine UYMAYAN gurultu (thing-ara.py ile ayni liste).
COP = ("keychain", "keyring", "key ring", "keyfob", "key fob", "keytag", "key tag", "keyholder",
       "key holder", "keychains", "logo", "logos", "emblem", "badge", "nameplate", "name plate",
       "letters", "lettering", "symbol", "monogram", "sticker", "wall art", "trophy",
       "coaster", "fridge magnet", "magnet",
       "miniature", "diecast", "die-cast", "diorama", "scale model", "1:18", "1:24", "1:32",
       "1:43", "1:64", "1/18", "1/24", "1/43", "keycap", "kit card")

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

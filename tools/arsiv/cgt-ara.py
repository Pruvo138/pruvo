#!/usr/bin/env python3
# EMEKLI - Okan 19 Tem: bu platformda arama YAPILMAZ (parity-backfill'den cikarildi).
r"""CGTrader'da MARKA/terim arar (TUM saticilar) — sitede OLMAYAN + ISLEVSEL (oto/endustriyel)
+ MARKA-ALAKALI urun sayfasi URL'lerini verir. cgt-ekle.py'nin SATICI modunun (author profili)
tersi: burada butun pazar taranir, sonuc bir ADAY URL LISTESI olur (cgt-ekle.py --marka isler).

Kullanim:  python3 tools/cgt-ara.py "Ford" [max]
   -> aday urun URL'lerini (bir satirda + tam liste) yazar + eleme dokumu basar.

ARAMA DESENI (canli kesfedildi 2026-07-18):
  https://www.cgtrader.com/3d-print-models/<kelime>?page=<n>
  - SSR HTML (JS gerekmez), sayfa basi ~50 sonuc, ?page=2.. ile ilerler (dogrulandi: p1/p2 ayrik).
  - `?keywords=<kelime>` deseni CALISMAZ (sabit "one cikan" listeyi doner) — path-tabanli desen sart.
  - Urun URL kalibi: /3d-print-models/<ustkategori>/<altkategori>/<slug>  (ustkategori = ISLEVSELLIK sinyali).

FILTRELER (EN KRITIK — CGTrader genel pazar, cop bol):
  1. \bMARKA\b TAM KELIME (printables-api.marka_kelime_gecer): slug'da marka tam kelime degilse ELE
     (Oxford/afford -> 'ford' alt-dizesi elenir). Arama listesinde tek metin sinyali slug'dir.
  2. ISLEVSELLIK: SADECE islevsel oto/endustriyel/atolye/ev parcasi kalir. ELE:
     - COP KATEGORI (URL ustkategorisi): art/games-toys/miniatures/jewelry/fashion/science/
       architectural/... = maket/oyuncak/figur/heykel/taki/mimari -> islevsel DEGIL.
     - LOGO/MERCH (pr.is_nobypass) + MINYATUR/DIECAST/DIORAMA (pr.is_cop) -> reprodüksiyon/olcek.
     - CGT-OZEL cop sinyalleri (slug/aciklama): scale/figurine/statue/sculpture/cosplay/helmet/mask/
       mold/silhouette/classic-car/static + render-oyun-varlik (lowpoly/game-ready/for-rendering...).
  3. ZATEN-EKLI dedup: urunler.json + .urun-kaynaklari.json'daki CGTrader model yollari.

Token/sir GEREKMEZ (public HTML). Cikti urunler.json'a DOKUNMAZ; sadece aday URL uretir.
"""
import collections, importlib.util, os, re, subprocess, sys, tempfile, time, urllib.parse

ROOT = "/Users/okan/dev/pruvo"
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
SAYFA_TAVAN = int(os.environ.get("CGT_SAYFA_TAVAN", "15"))   # guvenlik tavani (sonsuz dongu olmasin)

# printables-api.py'yi BU dosyanin yaninda (worktree/main hangisiyse) yukle — ROOT'a bagli degil.
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(_HERE, "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


# --- ISLEVSELLIK KURALI (kategori + sinyal) ---------------------------------------------------
# CGTrader 3d-print-models ustkategorileri; ISLEVSEL parca DISI (dekor/oyuncak/figur/taki/mimari)
# olan ustkategoriler blok. Kalanlar (hobby-diy/tools-organizers/gadgets/house/electronics...)
# islevsel domain kabul edilir; icindeki cop tek tek sinyalle elenir.
COP_KATEGORI_UST = {
    "art", "games-toys", "miniatures", "jewelry", "fashion", "science",
    "architectural", "scanned", "textures", "various", "collectibles", "characters",
}
# Ustkategorisi islevsel gorunse de (or. hobby-diy/automotive) alt kategorisi net cop olanlar.
COP_KATEGORI_ALT = {"keychains", "coins-badges", "wall-art"}

# CGT-ozel cop sinyalleri: pr.is_cop/is_nobypass'in yakalamadigi olcekli-model/figur/heykel/
# elisi/render-oyun-varlik terimleri. TEK kelimeler tam-kelime; COK kelimeli ifadeler alt-dize.
CGT_COP_TEK = {
    # olcekli / maket
    "scale", "diecast", "diorama", "miniature", "static",
    # figur / karakter / heykel
    "figurine", "figure", "statue", "bust", "sculpture", "sculpt", "replica", "cosplay",
    "helmet", "mask", "character", "creature", "monster", "anime", "chibi", "warhammer",
    # dekor / el-isi
    "silhouette", "mold", "freshie", "ornament", "trophy",
    # oyun / render varlik
    "lowpoly", "rigged", "vray", "unreal", "photoreal",
}
CGT_COP_IFADE = (
    "die cast", "scale model", "classic car", "wall art", "wall decor", "cookie cutter",
    "low poly", "game ready", "game-ready", "for rendering", "for render", "action figure",
    "display stand", "hot wheels", "slot car", "rc body", "1 18", "1 24", "1 25", "1 32",
    "1 43", "1 64", "1-18", "1-24", "1-25", "1-32", "1-43", "1-64",
)


def kategori_yolu(path):
    """/3d-print-models/<ust>/<alt>/<slug> -> ('ust', 'alt', 'ust/alt')."""
    parcalar = [p for p in path.split("/") if p]      # ['3d-print-models','ust','alt','slug']
    ust = parcalar[1] if len(parcalar) > 1 else ""
    alt = parcalar[2] if len(parcalar) > 2 else ""
    return ust, alt, (ust + "/" + alt if alt else ust)


def slug_metni(path):
    """URL slug'ini insan-okur metne cevirir (tire -> bosluk); marka/sinyal testi icin."""
    parcalar = [p for p in path.split("/") if p]
    return (parcalar[-1] if parcalar else "").replace("-", " ")


def islevsel_parca(metin, kategori_yolu_str, aciklama=""):
    r"""Aday ISLEVSEL bir oto/endustriyel/atolye/ev parcasi mi? (bool, neden) doner.
    metin           = slug metni ya da baslik (marka/sinyal metni)
    kategori_yolu_str = 'ust/alt' (CGTrader URL kategorisi)
    aciklama        = varsa urun aciklamasi (ek sinyal; arama listesinde genelde bos)
    ELE nedenleri sozel: 'kategori:<ust>' / 'altkategori:<alt>' / 'logo-merch' / 'minyatur-olcek'
    / 'sinyal:<kelime>'. Islevsel ise (True, '')."""
    ust = (kategori_yolu_str or "").split("/")[0]
    alt = (kategori_yolu_str or "").split("/")[1] if "/" in (kategori_yolu_str or "") else ""
    if ust in COP_KATEGORI_UST:
        return False, "kategori:" + ust
    if alt in COP_KATEGORI_ALT:
        return False, "altkategori:" + alt
    blob = pr.tr_lower(metin + " " + (aciklama or ""))
    # proje geneli filtreleri YENIDEN KULLAN (logo/amblem/merch + minyatur/diecast/scale-model)
    if pr.is_nobypass(blob):
        return False, "logo-merch"
    if pr.is_cop(blob):
        return False, "minyatur-olcek"
    # CGT-ozel ifadeler (alt-dize)
    for ifade in CGT_COP_IFADE:
        if ifade in blob:
            return False, "sinyal:" + ifade
    # CGT-ozel tek kelimeler (tam kelime — 'body'/'model' gibi genel kelimeleri BILEREK katmadik:
    # 'throttle body' / '3d model' islevsel parcada da gecer)
    kelimeler = set(re.findall(r"[a-z0-9çğıöşü]+", blob))
    ortak = kelimeler & CGT_COP_TEK
    if ortak:
        return False, "sinyal:" + sorted(ortak)[0]
    return True, ""


def aday_karari(path, marka, aciklama=""):
    r"""Bir aday URL YOLU marka aramasina uygun mu? (gecer_mi, neden). main() ve KABUL TESTI
    ORTAK kullanir (tek dogruluk kaynagi). Sira: once \bMARKA\b slug testi, sonra islevsellik.
    neden: 'marka-alakasiz' | 'kategori:..' | 'altkategori:..' | 'logo-merch' | 'minyatur-olcek'
    | 'sinyal:..' | '' (gecti)."""
    slug = slug_metni(path)
    if not pr.marka_kelime_gecer(slug, marka):
        return False, "marka-alakasiz"
    _ust, _alt, kyol = kategori_yolu(path)
    return islevsel_parca(slug, kyol, aciklama)


# --- ARAMA + DEDUP ----------------------------------------------------------------------------
def fetch(url):
    tmp = os.path.join(tempfile.gettempdir(), "cgtara_%d.html" % (abs(hash(url)) % 10**8))
    subprocess.run(["curl", "-sSL", "-A", UA, url, "-o", tmp], check=False)
    return open(tmp, encoding="utf-8", errors="ignore").read() if os.path.exists(tmp) else ""


def arama_url(term, page):
    kelime = urllib.parse.quote(term.strip().lower())
    base = "https://www.cgtrader.com/3d-print-models/" + kelime
    return base + ("?page=%d" % page if page > 1 else "")


def sayfa_yollari(term):
    """JENERATOR: her sayfada O SAYFADAKI YENI urun yollarini (path, domain'siz) verir.
    Yeni yol gelmeyen ilk sayfada (ya da SAYFA_TAVAN'da) durur. Cagiran yeterince ISLEVSEL
    aday bulunca erken durabilsin diye sayfa sayfa akitir (CGTrader'da cop bol -> derin gerek)."""
    seen = set()
    for page in range(1, SAYFA_TAVAN + 1):
        html = fetch(arama_url(term, page))
        if not html:
            break
        bulunan = re.findall(r'/3d-print-models/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+', html)
        yeni = [u for u in dict.fromkeys(bulunan) if u not in seen]
        if not yeni:
            break                      # bu sayfa yeni urun getirmedi -> son
        for u in yeni:
            seen.add(u)
        yield page, yeni
        time.sleep(0.8)


def mevcut_yollar():
    """urunler.json + .urun-kaynaklari.json'daki CGTrader model yollari (dedup icin, path olarak)."""
    yollar = set()
    for dosya in (URUNLER, KAYNAK):
        if os.path.exists(dosya):
            blob = open(dosya, encoding="utf-8").read()
            for m in re.findall(r'/3d-print-models/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+', blob):
                yollar.add(m)
    return yollar


def main(term, maxn, derin=False, cikis_limiti=None):
    mevcut = mevcut_yollar()
    gecen = []
    elenen_marka, elenen_islev, elenen_ekli = [], collections.Counter(), 0
    ornek_islev = collections.defaultdict(list)
    taranan = son_sayfa = 0
    for page, yeni in sayfa_yollari(term):
        son_sayfa = page
        for path in yeni:
            taranan += 1
            if path in mevcut:
                elenen_ekli += 1
                continue
            ok, neden = aday_karari(path, term)
            if ok:
                gecen.append(path)
            elif neden == "marka-alakasiz":
                elenen_marka.append(path)
            else:
                elenen_islev[neden] += 1
                if len(ornek_islev[neden]) < 3:
                    ornek_islev[neden].append(path.split("/")[-1][:48])
            if not derin and len(gecen) >= maxn:  # eski davranis: keeper-cap'te DUR
                break
        if not derin and len(gecen) >= maxn:  # yeterince islevsel aday bulundu -> derinlemeye gerek yok
            break

    if cikis_limiti is not None:
        gecen = gecen[:cikis_limiti]
    print("=== CGTrader MARKA ARAMA: '%s' (taranan sayfa: %d) ===" % (term, son_sayfa))
    print("Taranan aday yol: %d | zaten-ekli %d | marka-alakasiz(\\b%s\\b slug'da yok) %d | islevsel-degil %d"
          % (taranan, elenen_ekli, term, len(elenen_marka), sum(elenen_islev.values())))
    if elenen_islev:
        print("\n--- ISLEVSEL-DEGIL eleme dokumu ---")
        for neden, adet in elenen_islev.most_common():
            print("  %3d  %-22s  or: %s" % (adet, neden, ", ".join(ornek_islev[neden])))
    if elenen_marka:
        print("\n--- MARKA-ALAKASIZ ornek (slug'da tam kelime '%s' yok) ---" % term)
        for p in elenen_marka[:8]:
            print("  x", p.split("/")[-1][:60])
    print("\n=== '%s' icin %d ISLEVSEL aday (islevsel oto/endustriyel parca) ===" % (term, len(gecen)))
    for p in gecen:
        _u, _a, ky = kategori_yolu(p)
        print("  [%-24s] %s" % (ky, p.split("/")[-1][:52]))
    print("\nADAY URL'LER (cgt-ekle.py --marka'ya verilir):")
    for p in gecen:
        print("https://www.cgtrader.com" + p)
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(p.split("/")[-1] for p in gecen))


if __name__ == "__main__":
    args = sys.argv[1:]
    derin = "--derin" in args
    pos = [a for a in args if a != "--derin"]
    if not pos:
        sys.exit('Kullanim: python3 tools/cgt-ara.py "<marka/terim>" [max] [--derin]')
    if derin:
        cikis = int(pos[1]) if len(pos) > 1 else None
        main(pos[0], maxn=10 ** 9, derin=True, cikis_limiti=cikis)
    else:
        main(pos[0], int(pos[1]) if len(pos) > 1 else 60)

#!/usr/bin/env python3
"""Thingiverse'te MARKA/terim arar, zaten sitede OLMAYAN thing ID'lerini verir.

Kullanim:  python3 tools/thing-ara.py "Hyundai" [max]
   -> aday thing ID'lerini bir satirda (bosluk ayirli) yazar -> orkestratore (urun-ekle.py) girer.
      Ayrica id + baslik listesi basar (gozden gecirme). Lisans/uygunluk kontrolu urun-ekle.py'de.

Zaten eklenmis olanlari `.urun-kaynaklari.json` icindeki thing linklerinden tespit edip ELER.
Token `.thingiverse-token`'dan okunur. Sir icermez.
"""
import importlib.util, json, os, re, sys, urllib.parse, urllib.request

ROOT = "/Users/okan/dev/pruvo"
KAYNAK = os.path.join(ROOT, ".urun-kaynaklari.json")

# Resmi Thingiverse arayuzundeki ticari kullanima acik lisans kodlari. Her biri ayri
# sorgulanir; `license=cc` yalniz CC-BY havuzudur. NC ve taninmayan lisanslar yoktur.
SATILABILIR_LISANSLAR = (
    "cc", "cc-sa", "cc-nd", "pd0", "public", "gpl", "lgpl", "bsd",
)

# marka_kelime_gecer() TEK KAYNAK: printables-api.py (BU dosyanin yaninda; worktree/main farketmez).
# thing-ara ile printables-ara ayni filtre fonksiyonunu paylasir -> drift olmaz.
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(_HERE, "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def _token():
    """Thingiverse token'ini TEMBEL oku (import aninda degil) — token'siz makinede
    modul yine de import edilebilir (marka_kelime_gecer testi gibi ag gerektirmeyen kullanim)."""
    return open(os.path.join(ROOT, ".thingiverse-token")).read().strip()


# Yedek parca sitesine UYMAYAN gurultu (marka aramasi bunlari bol getirir) -> otomatik ELE.
# LOGO + MERCH: marka logosu/amblemini biz baskiyla URETEN urunler — telif/marka hakki riski
# nedeniyle POPULERLIK BILE DELMEZ, her zaman elenir (Okan, 2026-07-14). Ilke: logonun kaynak
# gorselinde gorunmesi degil, logoyu BASKIYLA uretmemiz sorunludur; bu yuzden logo-tasiyan
# aksesuar/merch formlari (anahtarlik/duvar-askisi/plaket/trofe...) da hep elenir.
# NOT: printables-api.py ile AYNI liste — birlikte guncelle. Cok-dilli terimler eklendi (kacan
# yabanci basliklar: Llavero, Schlusselanhanger, ecusson). Model-adi CAKISMASI olanlar bilerek
# DISARIDA (Opel "Insignia", Suzuki "Escudo" -> gecerli yedek parca).
COP_LOGO = (
    "logo", "logos", "emblem", "emblems", "emblema", "embleme", "emblème",
    "badge", "nameplate", "name plate", "symbol", "monogram", "logotipo",
    "ecusson", "écusson", "insigne", "blason", "abzeichen", "wappen",
    "stemma", "distintivo", "amblem",
    "roundel", "hood ornament", "prancing horse", "trident", "pentastar",
)
# Marka-logolu aksesuar/merch formlari — logo reprodüksiyonu sayilir, POPULERLIK DELMEZ.
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
)
# Populerlik DELEBILIR gurultu (olcek modeli/minyatur).
COP_OTHER = ("miniature", "diecast", "die-cast", "diorama", "scale model",
             "1:18", "1:24", "1:32", "1:43", "1:64", "1/18", "1/24", "1/43", "kit card")
COP_FIREARM = (
    "m-lok", "mlok", "magpul", "moe grip", "moe stock", "ctr stock",
    "magwell", "cheek riser", "cheek-riser", "pistol brace", "pistol-brace",
    "picatinny", "handguard", "ar-15", "ar15", "buffer tube",
    "lower receiver", "upper receiver", "pmag", "glock", "sarjor", "şarjör",
    "magazine", "holster", "mermi", "molle sarjor", "molle şarjör",
)
COP = COP_LOGO + COP_MERCH + COP_OTHER + COP_FIREARM


def is_cop(name):
    n = " " + name.lower() + " "
    return any(c in n for c in COP)


def is_logo(name):
    n = " " + name.lower() + " "
    return any(c in n for c in COP_LOGO)


def is_merch(name):
    """Marka-logolu aksesuar/merch formu mu? LOGO gibi: populerlik DELMEZ."""
    n = " " + name.lower() + " "
    return any(c in n for c in COP_MERCH)


def is_firearm(name):
    n = " " + name.lower() + " "
    return any(c in n for c in COP_FIREARM)


def is_nobypass(name):
    """Populerligin DELEMEDIGI eleme: logo/amblem VEYA marka-merch formu."""
    return is_logo(name) or is_merch(name) or is_firearm(name)


# POPULERLIK: cok talep goren thing (asagidaki esigi asan) COP/yasakli olsa bile ALINIR ve
# aramada EN UST onceligi alir. (Thingiverse aramasinda indirme yok -> begeni/make/collect.)
POP_LIKE = 300
POP_MAKE = 25
POP_COLLECT = 300


def populer(h):
    return ((h.get("like_count") or 0) >= POP_LIKE or (h.get("make_count") or 0) >= POP_MAKE
            or (h.get("collect_count") or 0) >= POP_COLLECT)


def api(url):
    r = urllib.request.Request(url, headers={"Authorization": "Bearer " + _token(),
                                             "User-Agent": "pruvo/1.0"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read())


def mevcut_thing_idleri():
    ids = set()
    if os.path.exists(KAYNAK):
        blob = open(KAYNAK, encoding="utf-8").read()
        for m in re.findall(r'thing[:/](\d{4,})', blob):
            ids.add(m)
        for m in re.findall(r'thingiverse\.com/thing:(\d+)', blob):
            ids.add(m)
    return ids


def main(term, maxn, tam_kelime=False, derin=False, cikis_limiti=None):
    """term/marka ara, sitede OLMAYAN uygun satilabilir-lisans adaylarini bas.

    Sayfalama (pagination) ile keeper-cap AYRI (2026-07-18 duzeltme):
      - derin=False (varsayilan, GERIYE-UYUMLU): dongu `maxn` keeper toplayinca DURUR
        (eski davranis birebir). Hizli; parity-backfill/tverse/CLI eski cagrilari icin.
      - derin=True (--derin): `maxn` dongoyu DURDURMAZ; ham havuz `page<400`/hits
        tukenene kadar TAM taranir, deterministik filtreleri gecen TUM adaylar toplanir.
        Boylece uygun satilabilir lisans havuzlari erken kesilmez.
    `cikis_limiti` (opsiyonel): siralamadan sonra donus/cikti listesini kirpar
      (maxn artik dongu capi degil, sadece istenirse bir cikis-limiti). None=kirpma yok.
    """
    mevcut = mevcut_thing_idleri()
    bulunan = []
    elenen = []
    elenen_kelime = []
    seen = set()
    toplam_sayfa = 0
    lisans_indeksi = 0
    page = 0
    lisans_bulunan = 0
    while lisans_indeksi < len(SATILABILIR_LISANSLAR):
        if page >= 400:
            lisans_indeksi += 1
            page = 0
            lisans_bulunan = 0
            continue
        page += 1
        toplam_sayfa += 1
        lisans = SATILABILIR_LISANSLAR[lisans_indeksi]
        url = ("https://api.thingiverse.com/search/%s?type=things&license=%s&per_page=30&page=%d"
               % (urllib.parse.quote(term), urllib.parse.quote(lisans), page))
        try:
            d = api(url)
        except Exception as e:
            print("ARAMA HATA (lisans %s, sayfa %d):" % (lisans, page), e)
            lisans_indeksi += 1
            page = 0
            lisans_bulunan = 0
            continue
        hits = d.get("hits") if isinstance(d, dict) else d
        if not hits:
            lisans_indeksi += 1
            page = 0
            lisans_bulunan = 0
            continue
        for h in hits:
            tid = str(h.get("id"))
            if tid in seen:
                continue
            seen.add(tid)
            if tid in mevcut:
                continue
            name = (h.get("name") or "").replace("\n", " ")
            likes = h.get("like_count") or 0
            makes = h.get("make_count") or 0
            pop = populer(h)
            # --tam-kelime: baslikta marka TAM KELIME degilse (Oxford/afford/Food) ELE
            if tam_kelime and not pr.marka_kelime_gecer(name, term):
                elenen_kelime.append((tid, name)); continue
            if is_nobypass(name):
                elenen.append((tid, name)); continue         # logo/amblem VEYA marka-merch -> populerlik DELMEZ, hep ele
            if is_cop(name) and not pop:
                elenen.append((tid, name)); continue        # cop VE populer degil -> ele
            bulunan.append((tid, name, likes, makes, is_cop(name)))  # son alan: populer-cop mu
            lisans_bulunan += 1
            # keeper-cap SADECE derin-olmayan (eski) modda dongoyu keser
            if not derin and lisans_bulunan >= maxn:
                break
        if not derin and lisans_bulunan >= maxn:
            lisans_indeksi += 1
            page = 0
            lisans_bulunan = 0
    # EN YUKSEK ONCELIK: talep (begeni, sonra make) cok olan thing basa. Populer-cop da burada.
    bulunan.sort(key=lambda b: (b[2], b[3]), reverse=True)
    havuz_toplam = len(bulunan)  # kirpmadan ONCE toplanan gercek aday sayisi (kabul olcumu)
    if not derin:
        bulunan = bulunan[:maxn]
    elif cikis_limiti is not None:
        bulunan = bulunan[:cikis_limiti]
    if elenen_kelime:
        print("--- MARKA ALT-DIZE elenen %d ('%s' tam kelime degil: Oxford/afford/Food gibi) ---"
              % (len(elenen_kelime), term))
        for tid, name in elenen_kelime[:20]:
            print("  x %s  %s" % (tid, name[:60]))
    if elenen:
        print("--- COP elenen %d (anahtarlik/logo/amblem/minyatur; populer OLMAYAN) ---" % len(elenen))
        for tid, name in elenen[:20]:
            print("  x %s  %s" % (tid, name[:60]))
    pop_cop = sum(1 for b in bulunan if b[4])
    kirpma = "" if cikis_limiti is None else " (cikis %d'e kirpildi; havuz %d)" % (len(bulunan), havuz_toplam)
    print("=== '%s' icin %d yeni aday [havuz %d, %d lisans, %d sayfa%s] (zaten ekli %d, cop %d elendi; populer-cop ISTISNA %d) ==="
          % (term, len(bulunan), havuz_toplam, len(SATILABILIR_LISANSLAR), toplam_sayfa,
             kirpma, len(mevcut & seen), len(elenen), pop_cop))
    for tid, name, likes, makes, iscop in bulunan:
        yildiz = " ★POPULER-COP" if iscop else ""
        print("  %s  ♥%-5d ⚒%-4d %s%s" % (tid, likes, makes, name[:52], yildiz))
    print("\nIDLER (talep sirasi, populer basta):")
    print(" ".join(b[0] for b in bulunan))


if __name__ == "__main__":
    # Geriye uyumlu: eski cagri `thing-ara.py "<terim>" [max]` aynen calisir (derin=False).
    #  --tam-kelime : baslikta markayi TAM KELIME arar (alt-dize gurultusunu eler).
    #  --derin      : keeper-cap'i KALDIR, ham CC havuzunu TAM tara (maxn dongoyu durdurmaz).
    #                 derin modda pozisyonel sayi = OPSIYONEL cikis-trim (verilmezse tum havuz).
    args = sys.argv[1:]
    tam_kelime = "--tam-kelime" in args
    derin = "--derin" in args
    pos = [a for a in args if a not in ("--tam-kelime", "--derin")]
    if not pos:
        sys.exit('Kullanim: python3 tools/thing-ara.py "<marka/terim>" [max] [--tam-kelime] [--derin]')
    if derin:
        cikis = int(pos[1]) if len(pos) > 1 else None
        main(pos[0], maxn=10 ** 9, tam_kelime=tam_kelime, derin=True, cikis_limiti=cikis)
    else:
        main(pos[0], int(pos[1]) if len(pos) > 1 else 250, tam_kelime=tam_kelime)

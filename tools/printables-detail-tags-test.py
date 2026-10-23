#!/usr/bin/env python3
"""KABUL TESTI — printables-api.py `detail()` DONUS SEMASI `tags` alanini icermeli.

Neden: `DETAIL_Q` etiket ALT-SECIMI istemedigi icin `detail()` daima `tags` anahtari OLMAYAN
bir print donuyordu. Tuketici MaCiT (`pruvo-hasat/olcum/hasat_tara.py`, printables kolu)
`tags = ",".join(t.get("name","") if isinstance(t, dict) else str(t) for t in (d.get("tags") or []))`
yaziyor -> etiket alanı hic gelmedigi icin BU SATIR HER ZAMAN BOS STRING uretiyordu; model
etiketleri hasat raporuna hic girmiyordu. Alan canli olculdu (2026-10-23): Printables GraphQL
`print` tipinde `tags { id name }` gecerli ve dolu donuyor (4/4 model canli olcumde dolu).

Bu test AG KULLANMAZ (token/uas/cagirim yok): `gql` sahte yanita baglanir, donus semasi
KALICI sozlesme gibi sinanir. Amac `tags` alt-seciminin bir gun geri alinmasini yakalamak.

Kosum:  python3 tools/printables-detail-tags-test.py
Cikti:  son satir 'SONUC=4/4 MUTANT=1/1' (hepsi gecerse exit 0; aksi halde exit 1 + patlayan)

MUTANT: izole kopyada `tags { id name }` satiri silinir -> T1 KIRMIZI olmak ZORUNDA.
"""
import importlib.util
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_API = os.path.join(_HERE, "printables-api.py")

# T3: hasat_tara.py printables kolunun AYNI iki satiri (kelimesi kelimesine) — sozlesme testi.
_HASAT_ETIKET_KODU = (
    'tglist = d.get("tags") or []\n'
    'tags = ",".join(t.get("name", "") if isinstance(t, dict) else str(t) for t in tglist)\n'
)


def yukle(dosya):
    """printables-api.py dosya adinda '-' var -> normal import edilemez, spec ile yukle."""
    spec = importlib.util.spec_from_file_location("printables_api_mutant_%d" % id(dosya), dosya)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- T1: DETAIL_Q metninde `tags` ALT-SECIMI var mi? (ust seviye `tags` degil, alt-secim) ---
def t1_tags_alt_secimi(mod):
    q = mod.DETAIL_Q
    if not any(l.strip().startswith("tags") and "{" in l for l in q.splitlines()):
        return False, "DETAIL_Q'ta `tags { ... }` alt-secimi YOK"
    return True, "tags alt-secimi bulundu"


# --- T4: eski alanlar DETAIL_Q'da duruyor mu? (regresyon korumasi) ---
ESKI_ALANLAR = [
    ("license { name abbreviation }", "license.abbreviation (lisans satisi kurali bunu okur)"),
    ("user { publicUsername }", "user.publicUsername (tasarimci)"),
    ("thingiverseLink", "thingiverseLink (dis kaynak)"),
    ("images { id order filePath }", "images (galeri)"),
    ("stls { id name fileSize }", "stls (dosya listesi)"),
]


def t4_eski_alanlar(mod):
    q = mod.DETAIL_Q
    eksik = [ac for (parca, ac) in ESKI_ALANLAR if parca not in q]
    if eksik:
        return False, "DETAIL_Q'tan SILINMIS: %s" % "; ".join(eksik)
    return True, "5/5 eski alan duruyor"


# --- T2: sahte gql -> detail() `tags` LISTESI dict{name} donuyor mu? ---
SAhte_YANIT = {"print": {
    "id": "1", "name": "Ornek Model", "slug": "ornek", "summary": "s", "description": "d",
    "license": {"name": "Creative Commons", "abbreviation": "CC-BY"},
    "user": {"publicUsername": "tasarimci"},
    "filesCount": 1, "imagesCount": 1, "downloadCount": 3, "likesCount": 2,
    "ratingAvg": 4.5, "thingiverseLink": "https://www.thingiverse.com/thing:1",
    "images": [{"id": "10", "order": 1, "filePath": "/a.png"}],
    "stls": [{"id": "20", "name": "a.stl", "fileSize": 123}],
    "tags": [{"id": "900", "name": "citroen"}, {"id": "901", "name": "clutch"},
             {"id": "902", "name": "thingiverse"}],
}}


def t2_detail_tags_donduruyor(mod):
    gorulen = {}

    def sahte_gql(query, variables=None):
        gorulen["query"] = query
        gorulen["variables"] = variables
        return SAhte_YANIT

    asli_gql = mod.gql
    mod.gql = sahte_gql
    try:
        d = mod.detail(1393618)
    except Exception as e:                                   # noqa: BLE001
        return False, "detail() PATLADI: %r" % e
    finally:
        mod.gql = asli_gql

    if gorulen.get("variables") != {"id": "1393618"}:
        return False, "detail() degiskeni yanlis: %r" % (gorulen.get("variables"),)
    tgl = d.get("tags")
    if not isinstance(tgl, list) or not tgl:
        return False, "detail()['tags'] liste degil/bos: %r" % (tgl,)
    if not all(isinstance(t, dict) and isinstance(t.get("name"), str) for t in tgl):
        return False, "etiketler dict{name} degil: %r" % (tgl,)
    return True, "3/3 etiket dict{name} dondu"


# --- T3: hasat_tara ifadesi bu semayla "a,b" uretiyor mu? ---
def t3_hasat_ifadesi(mod):
    # Donus semasini tuketici GOZUNE gore oku: hasat_tara.py'nin printables kolu bu iki satiri
    # dogrudan calistirir. Semasi bizim donusumuzle degistiyse burasi KIRMIZI olur.
    ns = {"d": SAhte_YANIT["print"], "isinstance": isinstance, "str": str,
          "dict": dict, "__builtins__": {}}
    try:
        exec(_HASAT_ETIKET_KODU, ns)                                      # noqa: S102
    except Exception as e:                                               # noqa: BLE001
        return False, "hasat ifadesi PATLADI: %r" % e
    tags = ns.get("tags")
    if tags != "citroen,clutch,thingiverse":
        return False, "beklenen 'citroen,clutch,thingiverse', gelen %r" % (tags,)
    return True, "'citroen,clutch,thingiverse' uretildi"


def mutant_calistir():
    """Izole kopya: `tags` satiri silinir -> T1 KIRMIZI olmak ZORUNDA (regresyon kaniti)."""
    gecici = tempfile.mkdtemp(prefix="pt-tags-mutant-")
    try:
        kopya = os.path.join(gecici, "printables-api-mutant.py")
        shutil.copy(_API, kopya)
        with open(kopya, encoding="utf-8") as f:
            satirlar = f.readlines()
        # YALNIZCA `tags { ... }` alt-secimini sil; baska hicbir satira dokunma.
        kalan = [l for l in satirlar if not l.strip().startswith("tags {")]
        if len(kalan) == len(satirlar):
            return False, "MUTANT kurulamadi: `tags {` satiri bulunamadi (test kendini yiyor)"
        with open(kopya, "w", encoding="utf-8") as f:
            f.writelines(kalan)
        m = yukle(kopya)
        gecti, _ = t1_tags_alt_secimi(m)
        if gecti:
            return False, "MUTANT KIRMIZI OLMADI — T1 tags'siz kopyada da gecti (test olu)"
        return True, "tags satiri silindi -> T1 kirmizi (beklenen)"
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def main():
    pr = yukle(_API)

    print("printables-detail-tags-test — detail() tags sozlesmesi")
    print("  API: %s" % _API)
    print()

    testler = [
        ("T1 DETAIL_Q'ta tags alt-secimi", lambda: t1_tags_alt_secimi(pr)),
        ("T2 detail() tags listesi dict{name}", lambda: t2_detail_tags_donduruyor(pr)),
        ("T3 hasat_tara ifadesi 'a,b' uretir", lambda: t3_hasat_ifadesi(pr)),
        ("T4 eski alanlar duruyor", lambda: t4_eski_alanlar(pr)),
    ]

    gecen, hatalar = 0, []
    for ad, calistir in testler:
        try:
            gecti, not_ = calistir()
        except Exception as e:                               # noqa: BLE001
            gecti, not_ = False, "PATLADI: %r" % e
        if gecti:
            gecen += 1
            print("  ok   %-40s  %s" % (ad, not_))
        else:
            hatalar.append((ad, not_))
            print("  FAIL %-40s  %s" % (ad, not_))

    print()
    try:
        m_gecti, m_not = mutant_calistir()
    except Exception as e:                                   # noqa: BLE001
        m_gecti, m_not = False, "PATLADI: %r" % e
    m_sayi = 1 if m_gecti else 0
    print("  %-4s %-40s  %s" % ("ok" if m_gecti else "FAIL", "MUTANT tags silinince T1 kirmizi", m_not))

    print()
    toplam = len(testler)
    sonuc = "%d/%d" % (gecen, toplam)
    mutant = "%d/1" % m_sayi
    if hatalar or not m_gecti:
        print("BASARISIZ:")
        for ad, not_ in hatalar:
            print("  x %s -> %s" % (ad, not_))
        print("SONUC=%s MUTANT=%s" % (sonuc, mutant))
        sys.exit(1)
    print("TUM TESTLER GECTI.")
    print("SONUC=%s MUTANT=%s" % (sonuc, mutant))


if __name__ == "__main__":
    main()
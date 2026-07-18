#!/usr/bin/env python3
r"""KABUL TESTI — denetim-kapisi.py (urun-ekleme otomatik denetim kapisi).

FIXTURE tabanli: gecici bir mini urunler.json + kaynak haritasi kurar (GERCEK
urunler.json'a DOKUNMAZ), her kapinin dogru siniflandirdigini assert eder:
  - bir MAKET/olcekli arac-> auto_sil (kapi=maket)
  - bir LOGO urunu        -> eskalasyon (kapi=logo; "logoyu cikar" yargisi mimara)
  - bir SATILAMAZ lisans  -> auto_sil (kapi=lisans)
  - bir OLCUSUZ urun      -> auto_sil (kapi=olcu)
  - bir GORSEL-CAKISMA    -> eskalasyon (silme yok)
  - bir GERCEK-IKIZ cift  -> dedup (biri tutulur, digeri auto_sil)
  - bir FARKLI-VARYANT cift-> eskalasyon (silme yok)
  - bir MARKA-KIRLI urun  -> marka_kirli (silme yok)
  - MUAF: satin-alma / parametrik (lisans+olcu kapisindan gecer)
  - JENERIK dedup: HEAD'deki (canli) ayni-baslik urun kazanir, yeni ikiz auto_sil
  - lisans_kisaltma(): serbest-metin lisans adi -> satilabilir() kisaltmasi

Calistir:  python3 tools/denetim-kapisi-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import importlib.util
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dk = _load("denetim-kapisi.py", "denetim_kapisi")


def check(ad, kosul):
    if not kosul:
        FAILS.append(ad)
        print("TEST KALDI:", ad, file=sys.stderr)


# --- fixture yardimcilari -----------------------------------------------------
OLCU = "Yaklasik dis olculer: 40 × 25 × 10 mm."


def urun(uid, baslik, aciklama=None, marka=None, gorsel=None, **over):
    u = {
        "id": uid,
        "kategori": "Otomobil",
        "marka": marka if marka is not None else ["Renault"],
        "baslik": baslik,
        "aciklama": aciklama if aciklama is not None else ("%s icin parca. %s" % (baslik, OLCU)),
        "fiyat": "300 TL",
        "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % (gorsel or uid)],
    }
    u.update(over)
    return u


def kaynak_cc(uid, lisans="CC BY 4.0"):
    return {"kaynak": "Printables", "link": "https://www.printables.com/model/%s" % uid,
            "lisans": lisans, "tur": "ucretsiz-cc"}


# --- fixture katalogu ---------------------------------------------------------
urunler = []
kaynaklar = {}


def ekle(u, kayit=None):
    urunler.append(u)
    if kayit is not None:
        kaynaklar[u["id"]] = kayit
    return u


# temiz (hicbir kapiya takilmamali)
ekle(urun("temiz-parca", "Renault Kangoo kapi tutamaci"), kaynak_cc("temiz-parca"))

# 1a MAKET/olcekli arac -> auto_sil (YASAK sinif)
ekle(urun("maket-urun", "Suzuki Jimny model araç 1/24 ölçekli"), kaynak_cc("maket-urun"))

# 1b LOGO -> ESKALASYON (silme yok; "logoyu cikar" yargisi mimara)
ekle(urun("logo-urun", "Renault amblem plaket suslemesi"), kaynak_cc("logo-urun"))

# 2 SATILAMAZ lisans -> auto_sil
ekle(urun("satilamaz-urun", "Renault Twingo cam krikosu dislisi"),
     kaynak_cc("satilamaz-urun", lisans="Standard Digital File License"))

# 3 OLCUSUZ -> auto_sil
ekle(urun("olcusuz-urun", "Renault Laguna torpido klipsi",
          aciklama="Dayanikli klips, kolay takilir. Olcu satiri yok."),
     kaynak_cc("olcusuz-urun"))

# 4 GORSEL CAKISMA -> eskalasyon (ayni gorsel anahtari, farkli baslik)
ekle(urun("cakisma-a", "Renault Espace bardaklik", gorsel="paylasilan"),
     kaynak_cc("cakisma-a"))
ekle(urun("cakisma-b", "Renault Scenic konsol kapagi", gorsel="paylasilan"),
     kaynak_cc("cakisma-b"))

# 5a GERCEK IKIZ -> dedup (twin-a 2 gorsel -> tutulur; twin-b silinir)
ikiz_acik = "Renault Clio icin dayanikli vites topuzu, kolay montaj. %s" % OLCU
ekle(urun("twin-a", "Renault Clio vites topuzu", aciklama=ikiz_acik,
          gorseller=["https://media.pruvo3d.com/urunler/twin-a-1.jpg",
                     "https://media.pruvo3d.com/urunler/twin-a-2.jpg"]),
     kaynak_cc("twin-a"))
ekle(urun("twin-b", "Renault Clio vites topuzu", aciklama=ikiz_acik, gorsel="twin-b"),
     kaynak_cc("twin-b"))

# 5b FARKLI VARYANT -> eskalasyon (ayni baslik, aciklama belirgin farkli)
ekle(urun("varyant-a", "Renault Megane ayna kapagi",
          aciklama="Sol taraf ayna govde klipsi tek parca. Yaklasik dis olculer: 30 × 20 × 8 mm.",
          gorsel="varyant-a"), kaynak_cc("varyant-a"))
ekle(urun("varyant-b", "Renault Megane ayna kapagi",
          aciklama="Katlanir dikiz kamerasi braketi montaj aparati agir hizmet. "
                   "Yaklasik dis olculer: 95 × 60 × 42 mm.",
          gorsel="varyant-b"), kaynak_cc("varyant-b"))

# 6 MARKA KIRLI -> marka_kirli (silme yok)
ekle(urun("marka-kirli-urun", "Renault Duster telefon tutucu", marka=["Renault", "GoPro"],
          gorsel="marka-kirli"), kaynak_cc("marka-kirli-urun"))

# MUAF: satin-alma (lisanssiz + olcusuz ama satin-alma -> gecer)
ekle(urun("satin-urun", "Renault Talisman far braketi",
          aciklama="Hazir alinmis parca, olcu siparişte alinir."),
     {"kaynak": "********", "link": "https://www.********.com/x", "tur": "satin-alma"})

# MUAF: parametrik (lisanssiz + olcusuz + fiyat bos -> gecer)
ekle(urun("parametrik-urun", "Olcuye ozel O-ring conta", marka=[],
          aciklama="Farkli renk secenekleri. Olcuye ozel uretim.",
          fiyat="", parametrik=True, kategori="Jeneratör"),
     {"link": "https://makerworld.com/x", "uyelik": "*****"})

# JENERIK dedup: HEAD'de (canli) ayni baslik var -> canli kazanir, yeni ikiz silinir
canli_acik = "Renault Kaptur bagaj kancasi dayanikli askı. %s" % OLCU
ekle(urun("canli-mevcut", "Renault Kaptur bagaj kancasi", aciklama=canli_acik),
     kaynak_cc("canli-mevcut"))
ekle(urun("yeni-jenerik", "Renault Kaptur bagaj kancasi", aciklama=canli_acik, gorsel="yeni-jenerik"),
     kaynak_cc("yeni-jenerik"))

# yeni parti = canli-mevcut HARIC hepsi; HEAD = {canli-mevcut}
head_ids = {"canli-mevcut"}
yeni_ids = {u["id"] for u in urunler if u["id"] not in head_ids}

r = dk.denetle(urunler, yeni_ids, head_ids, kaynaklar)
auto = {(a["id"], a["kapi"]) for a in r["auto_sil"]}
auto_ids = {a["id"] for a in r["auto_sil"]}
sil_ids = set(r["_sil_ids"])
esk = r["eskalasyon"]
esk_ids = {(e.get("id"), e.get("kapi")) for e in esk}
mk_ids = {m["id"] for m in r["marka_kirli"]}


# --- assertler ----------------------------------------------------------------
# 1a maket -> auto_sil
check("maket -> auto_sil(maket)", ("maket-urun", "maket") in auto)
# 1b logo -> ESKALASYON, silme YOK
check("logo -> eskalasyon(logo)", ("logo-urun", "logo") in esk_ids)
check("logo silinmiyor", "logo-urun" not in sil_ids and "logo-urun" not in auto_ids)
# 2 lisans
check("satilamaz -> auto_sil(lisans)", ("satilamaz-urun", "lisans") in auto)
# 3 olcu
check("olcusuz -> auto_sil(olcu)", ("olcusuz-urun", "olcu") in auto)
# 4 gorsel cakisma -> eskalasyon, silme YOK
check("cakisma-a -> eskalasyon(gorsel)", ("cakisma-a", "gorsel-cakisma") in esk_ids)
check("cakisma-b -> eskalasyon(gorsel)", ("cakisma-b", "gorsel-cakisma") in esk_ids)
check("cakisma silinmiyor", "cakisma-a" not in sil_ids and "cakisma-b" not in sil_ids)
# 5a gercek ikiz -> dedup
dedup_twin = [d for d in r["dedup"] if d["tut"] == "twin-a"]
check("ikiz dedup tut=twin-a", bool(dedup_twin))
check("ikiz sil=twin-b", bool(dedup_twin) and "twin-b" in dedup_twin[0]["sil"])
check("twin-b silinecek", "twin-b" in sil_ids)
check("twin-a KORUNUR", "twin-a" not in sil_ids)
# 5b farkli varyant -> eskalasyon, silme YOK
check("varyant -> dedup eskalasyon",
      any(e.get("kapi") == "dedup" and e.get("id") in ("varyant-a", "varyant-b") for e in esk))
check("varyant silinmiyor", "varyant-a" not in sil_ids and "varyant-b" not in sil_ids)
# 6 marka kirli -> rapor, silme YOK
check("gopro -> marka_kirli", "marka-kirli-urun" in mk_ids)
check("marka-kirli silinmiyor", "marka-kirli-urun" not in sil_ids and "marka-kirli-urun" not in auto_ids)
gopro = next((m for m in r["marka_kirli"] if m["id"] == "marka-kirli-urun"), None)
check("gopro token yakalandi", gopro is not None and "GoPro" in gopro["kirli_token"])
check("gopro onerilen marka temiz", gopro is not None and gopro["onerilen_marka"] == ["Renault"])
# MUAF
check("satin-alma MUAF (auto_sil yok)", "satin-urun" not in auto_ids)
check("parametrik MUAF (auto_sil yok)", "parametrik-urun" not in auto_ids)
# JENERIK dedup: canli kazanir
dedup_jen = [d for d in r["dedup"] if d["tut"] == "canli-mevcut"]
check("jenerik dedup tut=canli-mevcut", bool(dedup_jen))
check("jenerik sil=yeni-jenerik", bool(dedup_jen) and "yeni-jenerik" in dedup_jen[0]["sil"])
check("yeni-jenerik silinecek", "yeni-jenerik" in sil_ids)
check("canli-mevcut ASLA silinmez", "canli-mevcut" not in sil_ids)
# temiz urun hicbir yerde
check("temiz urun bulgusuz",
      "temiz-parca" not in auto_ids and "temiz-parca" not in sil_ids
      and "temiz-parca" not in mk_ids
      and not any(e.get("id") == "temiz-parca" for e in esk))

# --- lisans_kisaltma() birim kontrolleri (serbest-metin -> satilabilir) -------
def sat(ham):
    return dk.pr.satilabilir(dk.lisans_kisaltma(ham))


for ham, bekle in [
    ("Creative Commons - Attribution", True),
    ("Creative Commons — Attribution", True),                 # em-dash
    ("Creative Commons — Public Domain", True),
    ("Creative Commons — Attribution  — Share Alike", True),
    ("Creative Commons — Attribution — NoDerivatives", True),
    ("CC BY 4.0", True), ("CC BY-SA 4.0", True), ("CC0", True),
    ("GNU General Public License v3.0", True),
    ("GNU Lesser General Public License", True),
    ("BSD License", True),
    ("Standard Digital File License", False),                 # ASIL BUG sinifi
    ("Open Community License v1", False),
    ("Creative Commons — Attribution — NonCommercial", False),
    ("", False), (None, False),
]:
    check("lisans_kisaltma %r -> satilabilir=%s" % (ham, bekle), sat(ham) is bekle)


if FAILS:
    print("\n%d KONTROL KALDI" % len(FAILS), file=sys.stderr)
    sys.exit(1)
print("TEST GECTI (%d urun fixture, tum kapilar)" % len(urunler))
sys.exit(0)

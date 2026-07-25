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
     {"kaynak": "CGTrader", "link": "https://www.cgtrader.com/x", "tur": "satin-alma"})

# MUAF: parametrik (lisanssiz + olcusuz + fiyat bos -> gecer)
ekle(urun("parametrik-urun", "Olcuye ozel O-ring conta", marka=[],
          aciklama="Farkli renk secenekleri. Olcuye ozel uretim.",
          fiyat="", parametrik=True, kategori="Jeneratör"),
     {"link": "https://makerworld.com/x", "uyelik": "x"})

# JENERIK dedup: HEAD'de (canli) ayni baslik var -> canli kazanir, yeni ikiz silinir
canli_acik = "Renault Kaptur bagaj kancasi dayanikli askı. %s" % OLCU
ekle(urun("canli-mevcut", "Renault Kaptur bagaj kancasi", aciklama=canli_acik),
     kaynak_cc("canli-mevcut"))
ekle(urun("yeni-jenerik", "Renault Kaptur bagaj kancasi", aciklama=canli_acik, gorsel="yeni-jenerik"),
     kaynak_cc("yeni-jenerik"))

# FIX B (olcu capasi — MaCiT teshisi): SADECE kismi spec-mm (otomatik CAPALI on-ek YOK) tasiyan
# Printables urunu OLCUSUZ sayilmali -> auto_sil(olcu). Eski gevsek regex bunu "olculu" sanip
# auto_sil'den YANLIS-NEGATIF kacirdi.
ekle(urun("kismi-specmm-urun", "Renault Trafic yag tapasi",
          aciklama="M32×3.5 vida disi, yaklasik 31 mm dis cap. Dayanikli conta tapasi.",
          gorsel="kismi-specmm"), kaynak_cc("kismi-specmm-urun"))
# FIX B (Ictihat 71 korumasi + KUSUR-2): mesru CAPALI olcu satiri (iki-noktadan sonra ETIKET +
# gercek boyut, gomulu) -> HALA "olculu" -> olcu kapisindan GECER (auto_sil YOK). Fix ters yone
# kacip mesru olcuyu ELEMEMELI (gercek-veri regresyonu: 40+ canli urun bu bicimde).
ekle(urun("capali-olcu-urun", "Renault Trafic kapi kolu",
          aciklama="Saglam kapi kolu. Yaklaşık dış ölçüler: taban 137 × 135 × 70 mm. Kolay montaj.",
          gorsel="capali-olcu"), kaynak_cc("capali-olcu-urun"))

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
# 3b FIX B (kapi seviyesi): kismi spec-mm (on-ek YOK) -> auto_sil(olcu) [yanlis-negatif giderildi]
check("kismi spec-mm -> auto_sil(olcu)", ("kismi-specmm-urun", "olcu") in auto)
# 3c FIX B (kapi seviyesi): gomulu CAPALI olcu satiri -> auto_sil YOK [Ictihat 71 korumasi]
check("capali-olcu urun olcu kapisinden gecer", "capali-olcu-urun" not in auto_ids)
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


# =============================================================================
# FIX B: _olculu() CAPALI ifade eslesmesi — CIFT-YON kirmizi-mutasyon + GERCEK-VERI nobetcisi
# =============================================================================
# KUSUR-1 (MaCiT): eski gevsek desen r"\d[\d\s.,×xX*+-]*mm\b" "aciklamada HERHANGI mm var mi"
#   bakiyordu -> kismi spec-mm ("M32×3.5, ~31 mm") gercek olcuyle karisip olcusuz urunu "olculu"
#   sayiyordu (yanlis-negatif).
# KUSUR-2 (bagimsiz curutucu, gercek-veri regresyonu): otomatik uretici iki-noktadan SONRA
#   etiket/parantez koyabiliyor ("... : taban 137 × 135 × 70 mm.", "(15 cm boyda): 113 × ...").
#   Iki-noktadan HEMEN sonra \s*\d isteyen desen bunlari KACIRIR -> 40+ canli olculu urun
#   "olcusuz" sanilir (Ictihat 71 kitlesel-silme). FIX: capa ifadesine baglan + AYNI SATIRDA
#   lazy ([^\n]*?) ilk boyut tokenina ilerle.
import re as _re  # noqa: E402 (test-ici, kirmizi-mutasyon mutantlari icin)

# too-LAX = KUSUR-1'in eski (duz) regexi: kismi spec-mm'i yanlis "olculu" sayar.
_MUT_LOOSE = _re.compile(r"\d[\d\s.,×xX*+-]*mm\b", _re.IGNORECASE)
# too-STRICT = KUSUR-2'nin ta kendisi: capa + iki-nokta + HEMEN \d (araya etiket/parantez giremez).
# Bu, bagimsiz curutucunun yakaladigi GERCEK regresyon; etiketli/parantezli mesru satiri KACIRIR.
_MUT_COLON = _re.compile(r"Yakla[şs][ıi]k\s+d[ıi][şs]\s+[öo]l[çc][üu]ler\s*:\s*\d[\d\s.,×xX*+-]*mm\b",
                         _re.UNICODE)


def _olculu_mut(rx, aciklama):
    return isinstance(aciklama, str) and rx.search(aciklama) is not None


KISMI = "M32×3.5 vida disi, yaklasik 31 mm dis cap. Dayanikli conta tapasi."   # kismi spec-mm, capa YOK
GOMULU = "Saglam kapi kolu. Yaklaşık dış ölçüler: 20 × 30 × 5 mm. Kolay montaj."  # basit gomulu
ASCII_OLCU = "Dayanikli braket. Yaklasik dis olculer: 40 x 25 x 10 mm."        # eski ASCII yazim
YOK_OLCU = "Dayanikli klips, kolay takilir. Olcu satiri yok."                  # hic olcu yok
# KUSUR-2 GERCEK-VERI bicimleri (curutucu ornekleri; iki-noktadan sonra etiket/parantez):
LABELED = [
    "Renault Arkana bagaj kancasi. Yaklaşık dış ölçüler: taban 137 × 135 × 70 mm.",
    "Audi A4 B9 orta kolcak destek. Yaklaşık dış ölçüler: iç parça 42 × 30 × 8 mm sağlam oturur.",
    "Bosch POF 500/600 freze insert. Yaklaşık dış ölçüler: insert 52 × 24 × 18 mm.",
    "Audi A3 8P bagaj perde mafsali. Yaklaşık dış ölçüler: mafsal gövdesi 64 × 40 × 24 mm.",
    "Yamaha FZ1N sinyal adaptoru. Yaklaşık dış ölçüler (15 cm boyda): 113 × 117 × 150 mm.",
]
# Placeholder: capa VAR ama gercek boyut YOK (dijitsiz) -> gercekten olcusuz, False KALMALI.
# (bare-phrase oracle bunlari yanlislikla True'ya zorlar = KUSUR-1'i geri getirir -> yasak.)
PLACEHOLDER = [
    "Ic tutamac ara parca. Yaklaşık dış ölçüler: yok.",
    "Copluk. Yaklaşık dış ölçüler: Belirtilmedi.",
    "Sandladder. Yaklaşık dış ölçüler: Belirtilmemiş × Belirtilmemiş × Belirtilmemiş mm.",
    "Molle aparat. Yaklaşık dış ölçüler: - × - × - mm.",
]

# --- canli _olculu() dogru siniflandiriyor mu (dogru yon) ---
check("_olculu kismi spec-mm -> False", dk._olculu({"aciklama": KISMI}) is False)
check("_olculu basit gomulu capali -> True (Ictihat 71)", dk._olculu({"aciklama": GOMULU}) is True)
check("_olculu ASCII yazim -> True (geri-uyum)", dk._olculu({"aciklama": ASCII_OLCU}) is True)
check("_olculu olcu yok -> False", dk._olculu({"aciklama": YOK_OLCU}) is False)
for i, s in enumerate(LABELED):
    check("_olculu etiketli/parantezli biciM [%d] -> True (KUSUR-2)" % i, dk._olculu({"aciklama": s}) is True)
for i, s in enumerate(PLACEHOLDER):
    check("_olculu placeholder (gercek boyut yok) [%d] -> False" % i, dk._olculu({"aciklama": s}) is False)

# --- CIFT-YON kirmizi-mutasyon — her mutant en az bir vakada canliyla AYRISMALI ---
#  A) too-LAX (KUSUR-1 eski regex): kismi spec-mm'i YANLIS "olculu" sayar; canli False.
check("MUT-LOOSE kismi spec-mm -> True (KUSUR-1 BUG; kirmizi)", _olculu_mut(_MUT_LOOSE, KISMI) is True)
check("MUT-LOOSE canliyla AYRISIR (kismi)",
      _olculu_mut(_MUT_LOOSE, KISMI) != dk._olculu({"aciklama": KISMI}))
#  B) too-STRICT (KUSUR-2 gercek regresyon): etiketli mesru satiri YANLIS "olcusuz" sayar; canli True.
check("MUT-COLON etiketli biciM -> False (KUSUR-2/Ictihat 71 regresyonu; kirmizi)",
      _olculu_mut(_MUT_COLON, LABELED[0]) is False)
check("MUT-COLON canliyla AYRISIR (etiketli)",
      _olculu_mut(_MUT_COLON, LABELED[0]) != dk._olculu({"aciklama": LABELED[0]}))

# =============================================================================
# GERCEK-VERI ICTIHAT-71 NOBETCISI (izlenen urunler.json, SALT-OKUMA)
# =============================================================================
# Bu nobetci tam da bagimsiz curutucunun buldugu regresyonu yakalar: capa ifadesi + GERCEK
# 3-eksen SAYISAL boyut tasiyan HER canli urun _olculu() -> True olmali. Placeholder ("yok"/
# "Belirtilmedi"/"- × -", DIJITSIZ) urunler gercekten olcusuzdur; oracle onlari HARIC tutar
# (bare-phrase oracle onlari True'ya zorlarsa KUSUR-1'i geri getirir). ESKI kirik regex bu
# kumede 40 urunu False verirdi -> nobetci KIRMIZI (regresyon kaniti); yeni regex 0 kacan.
import json as _json  # noqa: E402
_UR = os.path.join(DIR, "..", "urunler.json")
_PHRASE = _re.compile(r"Yakla[şs][ıi]k\s+d[ıi][şs]\s+[öo]l[çc][üu]ler", _re.UNICODE)
_REAL3 = _re.compile(r"\d[\d.,]*\s*[×xX*]\s*\d[\d.,]*\s*[×xX*]\s*\d[\d.,]*\s*mm\b", _re.UNICODE)
try:
    with open(_UR, encoding="utf-8") as _f:
        _canli = _json.load(_f)
except (OSError, ValueError):
    _canli = None
check("gercek-veri nobetcisi: urunler.json okunabildi (dizi)", isinstance(_canli, list))
if isinstance(_canli, list):
    _hedef = 0
    _kacan = []
    for _u in _canli:
        if not isinstance(_u, dict):
            continue
        _a = _u.get("aciklama")
        if not isinstance(_a, str):
            continue
        if _PHRASE.search(_a) and _REAL3.search(_a):
            _hedef += 1
            if not dk._olculu({"aciklama": _a}):
                _kacan.append(_u.get("id"))
    check("gercek-veri nobetcisi: >=5000 capa+gercek-boyut urun denetlendi", _hedef >= 5000)
    check("gercek-veri nobetcisi: capa+gercek-boyut tasiyan HER urun _olculu()=True (Ictihat 71)",
          len(_kacan) == 0)
    if _kacan:
        print("ICTIHAT-71 KACAN (%d): %s" % (len(_kacan), ", ".join(str(x) for x in _kacan[:30])),
              file=sys.stderr)
    print("gercek-veri nobetcisi: %d capa+gercek-boyut urun denetlendi, %d kacan" % (_hedef, len(_kacan)))


# --- KAPI 1 (lisans) KAYNAGA-OZEL denetim — her platform KENDI natif bicimini dogru okur -------
# MakerWorld/MMF CC'yi CIPLAK ("BY","BY-SA","CC0") saklar, Cults3D code/insan-adi ("cc_by"/
# "CC BY - Attribution"). Bu bicimler pr.satilabilir()'in bekledigi "CC-BY" formuna UYMAZ ve
# lisans_kisaltma() de tanimaz -> kaynak-dispatch OLMADAN HAM deger fail-closed False'a duser =
# GECERLI urun yanlislikla auto_sil (2026-07-18 Dacia partisi: 16/24 MakerWorld urunu yanlis-poz).
# Bu blok kaynak-dispatch'i kilitler; her kaynagin GERCEKTEN satilamaz lisansi HALA yakalanmali.
def lis(kayit, u=None):
    kapi, _ = dk.kapi_lisans(u or urun("lis-x", "Renault parca"), kayit)
    return kapi  # None = gecti (satilabilir), "lisans" = auto_sil


def mw_kayit(lisans):
    return {"kaynak": "MakerWorld", "link": "https://makerworld.com/en/models/1-foo",
            "lisans": lisans, "tur": "ucretsiz-cc"}


# MakerWorld CIPLAK CC -> satilabilir (GECMELI); bug oncesi HEPSI yanlis auto_sil idi
check("MW 'BY' -> gecer (lisans)", lis(mw_kayit("BY")) is None)
check("MW 'BY-SA' -> gecer", lis(mw_kayit("BY-SA")) is None)
check("MW 'BY-ND' -> gecer", lis(mw_kayit("BY-ND")) is None)
check("MW 'CC0' -> gecer", lis(mw_kayit("CC0")) is None)
# MakerWorld GERCEKTEN satilamaz -> HALA auto_sil (kaynak toptan beyaz-listelenmedi)
check("MW 'BY-NC' -> auto_sil", lis(mw_kayit("BY-NC")) == "lisans")
check("MW 'BY-NC-SA' -> auto_sil", lis(mw_kayit("BY-NC-SA")) == "lisans")
check("MW 'Standard Digital File License' -> auto_sil",
      lis(mw_kayit("Standard Digital File License")) == "lisans")
check("MW 'MakerWorld Exclusive License' -> auto_sil",
      lis(mw_kayit("MakerWorld Exclusive License")) == "lisans")
# domain-only tespit (kaynak alani YOK, link makerworld.com) -> yine natif kontrol
check("MW domain-only 'BY-SA' -> gecer",
      lis({"link": "https://makerworld.com/en/models/9", "lisans": "BY-SA"}) is None)
check("MW domain-only 'BY-NC' -> auto_sil",
      lis({"link": "https://makerworld.com/en/models/9", "lisans": "BY-NC"}) == "lisans")

# Cults3D code/insan-adi natif bicim (c3.satilabilir non-alnum ile ayirir)
check("Cults3D 'cc_by' -> gecer",
      lis({"kaynak": "Cults3D", "link": "cults3d:x", "lisans": "cc_by"}) is None)
check("Cults3D 'CC BY - Attribution' -> gecer",
      lis({"kaynak": "Cults3D", "link": "cults3d:x", "lisans": "CC BY - Attribution"}) is None)
check("Cults3D 'cults_pu' (private use) -> auto_sil",
      lis({"kaynak": "Cults3D", "link": "cults3d:x", "lisans": "cults_pu"}) == "lisans")
check("Cults3D 'cc_by_nc' -> auto_sil",
      lis({"kaynak": "Cults3D", "link": "cults3d:x", "lisans": "cc_by_nc"}) == "lisans")

# MyMiniFactory ciplak/betimleyici/tescilli natif bicim
check("MMF 'BY' -> gecer",
      lis({"kaynak": "MyMiniFactory", "link": "https://www.myminifactory.com/object/1",
           "lisans": "BY"}) is None)
check("MMF 'BY-NC-SA' -> auto_sil",
      lis({"kaynak": "MyMiniFactory", "link": "https://www.myminifactory.com/object/1",
           "lisans": "BY-NC-SA"}) == "lisans")
check("MMF 'Standard Digital File Store License' -> auto_sil",
      lis({"kaynak": "MyMiniFactory", "link": "https://www.myminifactory.com/object/1",
           "lisans": "Standard Digital File Store License"}) == "lisans")

# FALLBACK korunur: Printables serbest-metin HALA lisans_kisaltma + pr.satilabilir ile denetlenir
check("Printables 'Creative Commons - Attribution' -> gecer (fallback)",
      lis(kaynak_cc("pf1", "Creative Commons - Attribution")) is None)
check("Printables 'Standard Digital File License' -> auto_sil (fallback)",
      lis(kaynak_cc("pf2", "Standard Digital File License")) == "lisans")
# lisanssiz kayit -> fail-closed auto_sil (kaynak ne olursa olsun; native kapi CAGRILMADAN)
check("MW lisanssiz -> auto_sil (fail-closed)",
      lis({"kaynak": "MakerWorld", "link": "https://makerworld.com/en/models/1"}) == "lisans")
# satin-alma / parametrik lisans kapisindan MUAF (kaynak MakerWorld olsa bile)
check("MW ama satin-alma -> lisans MUAF",
      lis({"kaynak": "MakerWorld", "link": "https://makerworld.com/x", "tur": "satin-alma"}) is None)


if FAILS:
    print("\n%d KONTROL KALDI" % len(FAILS), file=sys.stderr)
    sys.exit(1)
print("TEST GECTI (%d urun fixture, tum kapilar)" % len(urunler))
sys.exit(0)

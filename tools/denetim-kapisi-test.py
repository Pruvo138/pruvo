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


# =============================================================================
# KAPI 7 — FIYAT TABANI 200 TL, TUM KATALOG + KAPI 8 — URETIM-SURECI IFSASI
# TEK KAYNAK: Okan karari 31 Tem 2026 — "200 TL taban artik TUM urunlere uygulanir".
# ONCEKI HAL (30 Tem, POLITIKA-KARARLARI.md): kural YALNIZ kategori == 'Marin' idi.
#
# 🔴 BU BOLUM KAPSAM GENISLEMESININ IKI YONLU NOBETCISIDIR:
#   POZITIF — taban alti NORMAL urun HER kategoride KIRMIZI yanmali (yeni kural yasiyor).
#   NEGATIF — parametrik/Jeneratör (sari seri) ve BOS fiyat YESIL kalmali (istisna yasiyor),
#             taban ve ustu fiyat YESIL kalmali (kapi toptan kirmizi DEGIL).
#   ESKI EKSEN — Marin'in olculmus davranisi (kademeli oneri, BOS fiyat fail-closed,
#             ozel-format niteleyici) AYNEN duruyor; kapsam genislerken silinmedi.
# =============================================================================
def uf(kategori, fiyat, **over):
    """fiyat kapisi fikstoru — GERCEK kayit sekli (canli urunler.json alan kumesi:
    id/kategori/marka/baslik/aciklama/fiyat/gorseller; olculdu 31 Tem)."""
    u = {"id": "f-%s-%s" % (kategori, fiyat), "kategori": kategori, "baslik": "parca",
         "aciklama": "parca. " + OLCU, "fiyat": fiyat, "marka": [], "gorseller": ["x.jpg"]}
    u.update(over)
    return u


def fiyat_kirmizi(u):
    return dk.kapi_fiyat(u)[0] is not None


# canli katalogdaki TUM kategoriler (olculdu 31 Tem: 15.930 urun, 14 kategori — nav'da gizli
# 'Jeneratör' ve arsiv 'Skan Art' dahil). Kural artik hepsinde gecerli (Jeneratör HARIC).
FIYAT_KATEGORILERI = ("Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev", "Ofis",
                      "Elektronik", "Kamera", "Bahçe", "Dekorasyon", "Oyun/Hobi", "Skan Art")

# --- (a) POZITIF: taban alti NORMAL urun -> HER kategoride KIRMIZI ---------------------
# Canli dagilimda gercekten gecen taban-alti degerler (olculdu): 150(1109), 180(392),
# 170(67), 100(65), 190(37), 160(32), 165(22), 155(18), 175(12), 185(4).
for _kat in FIYAT_KATEGORILERI:
    for _f in ("100 TL", "150 TL", "180 TL", "190 TL", "199 TL"):
        check("POZ: %s %s -> IHLAL (taban 200 TL)" % (_kat, _f), fiyat_kirmizi(uf(_kat, _f)))
# ondalik/binlik biciMler de taban altinda yakalanir
check("POZ: '99,50 TL' -> IHLAL", fiyat_kirmizi(uf("Otomobil", "99,50 TL")))
check("POZ: '150 TL/adet' (niteleyici kuyruklu, taban ALTI) -> IHLAL",
      fiyat_kirmizi(uf("Dekorasyon", "150 TL/adet")))

# --- (b) NEGATIF-1: taban ve USTU her kategoride YESIL (kapi toptan kirmizi DEGIL) -----
for _kat in FIYAT_KATEGORILERI:
    for _f in ("200 TL", "300 TL", "350 TL", "850 TL", "1.250 TL"):
        check("NEG: %s %s -> YESIL" % (_kat, _f), not fiyat_kirmizi(uf(_kat, _f)))

# --- (b) NEGATIF-2: SARI SERI istisnasi (parametrik ve/veya Jeneratör) -----------------
check("NEG sari: Jeneratör + parametrik + fiyat BOS -> YESIL",
      not fiyat_kirmizi(uf("Jeneratör", "", parametrik=True)))
check("NEG sari: Jeneratör kategorisi (parametrik alani YOK) + fiyat BOS -> YESIL",
      not fiyat_kirmizi(uf("Jeneratör", "")))
check("NEG sari: ASCII yazim 'Jenerator' + fiyat BOS -> YESIL",
      not fiyat_kirmizi(uf("Jenerator", "")))
# ...ve istisna FIYATLI sari kayitta da gecerli (kategori/parametrik ekseni tasiyor;
# bu vaka mutasyon bolumunde M3 ile ISPATLANIR — bayrak gercekten yuk tasiyor)
check("NEG sari: Jeneratör + '100 TL' -> YESIL (kategori istisnasi)",
      not fiyat_kirmizi(uf("Jeneratör", "100 TL")))
check("NEG sari: parametrik=True Otomobil'de + '100 TL' -> YESIL (parametrik istisnasi)",
      not fiyat_kirmizi(uf("Otomobil", "100 TL", parametrik=True)))
check("NEG sari: parametrik (Marin kategorisinde, fiyat BOS) -> YESIL",
      not fiyat_kirmizi(uf("Marin", "", parametrik=True)))

# --- (b) NEGATIF-3: BOS fiyat kapsam DISI (Okan karari) --------------------------------
# Gerekce: sari seride fiyat taban-fiyatlar.js'ten gelir. OLCULDU (31 Tem): canli katalogda
# BOS fiyatli 23 kayit var ve HEPSI parametrik+Jeneratör — yani bu dal bugun sari seriden
# baska kimseyi gecirmiyor. Marin'de ise ESKI fail-closed davranis KORUNUR (asagida).
check("NEG bos: Otomobil fiyat BOS -> YESIL (kapsam disi)", not fiyat_kirmizi(uf("Otomobil", "")))
check("NEG bos: Dekorasyon fiyat BOS (bosluk) -> YESIL", not fiyat_kirmizi(uf("Dekorasyon", "   ")))

# --- (c) POZITIF: AYIKLANAMAYAN fiyat metni -> KIRMIZI (fail-closed, sessizce gecmez) ---
for _kat in ("Marin", "Otomobil", "Ev", "Oyun/Hobi"):
    for _f in ("sorunuz", "fiyat icin arayiniz", "-", "TL 150", "yakinda"):
        check("POZ fail-closed: %s %r ayristirilamaz -> IHLAL" % (_kat, _f),
              fiyat_kirmizi(uf(_kat, _f)))
check("POZ fail-closed: fiyat alani METIN DEGIL (sayi) -> IHLAL",
      fiyat_kirmizi(uf("Otomobil", 150)))
check("POZ fail-closed: fiyat alani METIN DEGIL (liste) -> IHLAL",
      fiyat_kirmizi(uf("Otomobil", ["150 TL"])))

# --- (d) ESKI MARIN EKSENI KAYBOLMADI --------------------------------------------------
check("ESKI-MARIN: 100/150/199 TL hala IHLAL",
      fiyat_kirmizi(uf("Marin", "100 TL")) and fiyat_kirmizi(uf("Marin", "150 TL"))
      and fiyat_kirmizi(uf("Marin", "199 TL")))
# bucket kurali ONERISI ihlal mesajinda gorunur (170 -> [150,200) -> 300 TL)
check("ESKI-MARIN: 170 TL ihlal mesaji kademeli hedefi (300) onerir",
      "300 TL olmali" in dk.kapi_fiyat(uf("Marin", "170 TL"))[1])
check("ESKI-MARIN: 100 TL ihlal mesaji kademeli hedefi (200) onerir",
      "200 TL olmali" in dk.kapi_fiyat(uf("Marin", "100 TL"))[1])
# kademeli ONERI artik TUM kategorilerde ayni (kural genisledi, mesaj ayni dili konusuyor)
check("kademeli oneri Otomobil'de de var (170 -> 300 TL)",
      "300 TL olmali" in dk.kapi_fiyat(uf("Otomobil", "170 TL"))[1])
# taban ve uzeri GECER (canli Marin dagilimi: 300/350/500/600/650/900)
for _f in ("200 TL", "300 TL", "350 TL", "500 TL", "650 TL", "1.250 TL"):
    check("ESKI-MARIN: %s -> gecer" % _f, not fiyat_kirmizi(uf("Marin", _f)))
check("ESKI-MARIN: fiyat BOS ama parametrik DEGIL -> ihlal (fail-closed EKSEN KORUNDU)",
      fiyat_kirmizi(uf("Marin", "")))
check("ESKI-MARIN: fiyat ayristirilamaz -> ihlal (fail-closed)",
      fiyat_kirmizi(uf("Marin", "sorunuz")))

# --- OZEL-FORMAT NITELEYICILER KORUNUR (canli katalogda 2 kayit: '400 TL/adel',
#     '300 TL (30 cm)' — olculdu 31 Tem; IKISI DE taban USTU) ---------------------------
check("ozel format '500 TL/adel' -> 500 olarak ayristirilir", dk._fiyat_sayi("500 TL/adel") == 500)
check("ozel format '500 TL (30 cm)' -> 500", dk._fiyat_sayi("500 TL (30 cm)") == 500)
check("ozel format Marin'de de YESIL (niteleyici kuyrugu kapiyi bozmaz)",
      not fiyat_kirmizi(uf("Marin", "500 TL/adel"))
      and not fiyat_kirmizi(uf("Marin", "500 TL (30 cm)")))
check("canli ozel-format kayitlari YESIL ('400 TL/adel', '300 TL (30 cm)')",
      not fiyat_kirmizi(uf("Otomobil", "400 TL/adel"))
      and not fiyat_kirmizi(uf("Dekorasyon", "300 TL (30 cm)")))
check("binlik ayirici '1.250 TL' -> 1250", dk._fiyat_sayi("1.250 TL") == 1250)

# --- bucket kurali (POLITIKA-KARARLARI.md) --------------------------------------------
for _n, _h in ((100, 200), (149, 200), (150, 300), (170, 300), (199, 300),
               (200, 350), (249, 350), (250, 500), (450, 500), (499, 500)):
    check("kademeli_hedef(%d) == %d" % (_n, _h), dk.kademeli_hedef(_n) == _h)
check("kademeli_hedef(500) dokunulmaz", dk.kademeli_hedef(500) == 500)
check("kademeli_hedef(900) dokunulmaz", dk.kademeli_hedef(900) == 900)


# =============================================================================
# 🔬 KAPI 7 — CIFT YONLU KOD MUTASYONU (kaynak KOPYAYA uygulanir, DISKE YAZILMAZ)
# -----------------------------------------------------------------------------
# Iddia: yukaridaki pozitif/negatif vakalar OLU DEGIL — kuralin her tasiyici satiri
# oldurulunce ilgili vaka TARAF DEGISTIRIYOR. Iki yon de olculur:
#   KILL  : kurali GERI ALAN mutant, saglam kopyanin verdiginin TERSINI vermeli
#           (yani vaka mutanti YAKALAR = "mutant KIRMIZI yanar").
#   ILGISIZ: fiyat kuralini ilgilendirmeyen bir degisiklik HICBIR fiyat hukmunu
#           degistirmemeli (yalanci-hassasiyet nobeti = "ilgisiz degisiklik YESIL").
# Mutant kaynak BELLEKTE derlenir (ayri modul); canli dosya sha256 ile ONCE/SONRA
# karsilastirilir — dalda mutant KALMADIGININ kaniti.
# =============================================================================
import hashlib as _hashlib  # noqa: E402
import types as _types  # noqa: E402

_DK_YOL = os.path.join(DIR, "denetim-kapisi.py")


def _sha256(yol):
    with open(yol, "rb") as f:
        return _hashlib.sha256(f.read()).hexdigest()


_SHA_ONCE = _sha256(_DK_YOL)


def _mutant_yukle(capa, yeni_metin):
    """Kaynagi okur, capayi BELLEKTE degistirir, ayri modul olarak exec eder.
    capa TEK kez gecmiyorsa None doner (OLCULEMEDI — sessiz yesil YOK)."""
    with open(_DK_YOL, encoding="utf-8") as f:
        src = f.read()
    if src.count(capa) != 1:
        return None
    mod = _types.ModuleType("dk_fiyat_mutant")
    mod.__file__ = _DK_YOL
    exec(compile(src.replace(capa, yeni_metin, 1), _DK_YOL + "#mutant", "exec"), mod.__dict__)
    return mod


# (ad, capa, mutant metin, probe urun, saglamda KIRMIZI mi)
_FIYAT_KILL = [
    ("M1 taban 200 -> 0 (kural etkisiz)",
     "FIYAT_TABANI = 200.0", "FIYAT_TABANI = 0.0",
     uf("Otomobil", "100 TL"), True),
    ("M2 kapsam yeniden Marin'e kilitlendi",
     '    if fiyat_muaf(urun):\n        return None, ""                           # SARI SERI',
     '    if urun.get("kategori") != "Marin":\n        return None, ""\n'
     '    if fiyat_muaf(urun):\n        return None, ""                           # SARI SERI',
     uf("Otomobil", "150 TL"), True),
    ("M3 sari-seri istisnasi olduruldu (parametrik)",
     '    if bool(urun.get("parametrik")):\n        return True\n'
     '    return tr_lower(str(urun.get("kategori") or "")).strip() in FIYAT_MUAF_KATEGORI',
     "    return False",
     uf("Otomobil", "100 TL", parametrik=True), False),
    ("M3b sari-seri istisnasi olduruldu (Jeneratör kategorisi)",
     '    if bool(urun.get("parametrik")):\n        return True\n'
     '    return tr_lower(str(urun.get("kategori") or "")).strip() in FIYAT_MUAF_KATEGORI',
     "    return False",
     uf("Jeneratör", "100 TL"), False),
    ("M4 BOS-fiyat kapsam-disi dali olduruldu",
     '        return None, ""                           # Okan: BOS fiyat kapsam DISI',
     '        return "fiyat", "MUT"',
     uf("Otomobil", ""), False),
    ("M5 ayiklanamayan fiyat fail-closed'u olduruldu (fail-OPEN)",
     '        return "fiyat", "fiyat ayristirilamadi: %r (fail-closed — \'gecerli\' SAYILMAZ)" % ham',
     '        return None, ""',
     uf("Otomobil", "sorunuz"), True),
    ("M6 ESKI MARIN ekseni olduruldu (BOS fiyat fail-closed)",
     "        if urun.get(\"kategori\") == FIYAT_BOS_FAILCLOSED_KATEGORI:",
     "        if False:",
     uf("Marin", ""), True),
    ("M7 metin-olmayan fiyat fail-closed'u olduruldu",
     '        return "fiyat", "fiyat alani metin DEGIL: %r (fail-closed)" % (ham,)',
     '        return None, ""',
     uf("Otomobil", 150), True),
]

_capasiz, _saglam_ters, _sag_kalan = [], [], []
for _ad, _capa, _yeni, _probe, _saglam_kirmizi in _FIYAT_KILL:
    if fiyat_kirmizi(_probe) is not _saglam_kirmizi:
        _saglam_ters.append(_ad)                       # saglam kopya iddiayi TASIMIYOR
        continue
    _mut = _mutant_yukle(_capa, _yeni)
    if _mut is None:
        _capasiz.append(_ad)                           # OLCULEMEDI
        continue
    if (_mut.kapi_fiyat(_probe)[0] is not None) is _saglam_kirmizi:
        _sag_kalan.append(_ad)                         # mutant SAG KALDI = olu iddia
check("MUT-SAGLAM: %d mutasyonun probu saglam kopyada BEKLENEN tarafta" % len(_FIYAT_KILL),
      not _saglam_ters)
check("MUT-CAPA: %d mutasyonun capasi TEK kez tuttu (OLCULEMEDI yok)" % len(_FIYAT_KILL),
      not _capasiz)
check("MUT-KILL: %d/%d mutant OLDU (kurali geri alan degisiklik vakayi taraf degistirir)"
      % (len(_FIYAT_KILL) - len(_sag_kalan) - len(_capasiz) - len(_saglam_ters), len(_FIYAT_KILL)),
      not _sag_kalan)
if _saglam_ters or _capasiz or _sag_kalan:
    print("MUT ayrinti: saglam-ters=%s capasiz=%s sag-kalan=%s"
          % (_saglam_ters, _capasiz, _sag_kalan), file=sys.stderr)

# --- ILGISIZ DEGISIKLIK: fiyat hukmu DEGISMEMELI (yalanci-hassasiyet nobeti) -----------
_PROBE_KUMESI = [uf("Otomobil", "100 TL"), uf("Marin", "150 TL"), uf("Ev", "199 TL"),
                 uf("Otomobil", "200 TL"), uf("Dekorasyon", "850 TL"),
                 uf("Jeneratör", "", parametrik=True), uf("Jeneratör", "100 TL"),
                 uf("Otomobil", ""), uf("Marin", ""), uf("Oyun/Hobi", "sorunuz")]
_SAGLAM_HUKUM = [fiyat_kirmizi(u) for u in _PROBE_KUMESI]
_ILGISIZ = [
    ("I1 dedup esigi degisti (fiyat kurali DISI)", "DEDUP_ESIK = 0.75", "DEDUP_ESIK = 0.60"),
    ("I2 yalnizca yorum satiri eklendi",
     "# KAPI 7: FIYAT TABANI", "# (ilgisiz yorum — mutasyon nobeti)\n# KAPI 7: FIYAT TABANI"),
]
_ilgisiz_capasiz, _ilgisiz_bozdu = [], []
for _ad, _capa, _yeni in _ILGISIZ:
    _mut = _mutant_yukle(_capa, _yeni)
    if _mut is None:
        _ilgisiz_capasiz.append(_ad)
        continue
    if [(_mut.kapi_fiyat(u)[0] is not None) for u in _PROBE_KUMESI] != _SAGLAM_HUKUM:
        _ilgisiz_bozdu.append(_ad)
check("MUT-ILGISIZ capasi tuttu (%d degisiklik)" % len(_ILGISIZ), not _ilgisiz_capasiz)
check("MUT-ILGISIZ: fiyat kurali DISI degisiklik %d probun HICBIRINDE hukmu degistirmedi"
      % len(_PROBE_KUMESI), not _ilgisiz_bozdu)

# --- canli dosya DEGISMEDI (mutant dalda BIRAKILMADI) ---------------------------------
_SHA_SONRA = _sha256(_DK_YOL)
check("MUT-DISK: denetim-kapisi.py sha256 ONCE == SONRA (diske mutant YAZILMADI)",
      _SHA_ONCE == _SHA_SONRA)
print("mutasyon sha256 denetim-kapisi.py: once=%s sonra=%s" % (_SHA_ONCE[:16], _SHA_SONRA[:16]))


# --- KAPI 8: URETIM-SURECI IFSASI -----------------------------------------------------
def ifsa(metin, baslik="Parca"):
    return dk.kapi_ifsa({"baslik": baslik, "aciklama": metin, "marka": []})


def sert_mi(metin, baslik="Parca"):
    return len(ifsa(metin, baslik)["sert"]) > 0


def uyari_mi(metin, baslik="Parca"):
    return len(ifsa(metin, baslik)["uyari"]) > 0


# ONCE-KIRMIZI: uretim-sureci ifsali sahte urun -> KIRMIZI (kesin-yasak sinif)
check("ONCE-KIRMIZI ifsa: '%100 dolgu orani onerilir'", sert_mi("- %100 dolgu oranı önerilir."))
check("ONCE-KIRMIZI ifsa: 'PETG ile basilmasi onerilir'", sert_mi("- PETG ile basılması önerilir."))
check("ONCE-KIRMIZI ifsa: '0.20mm katman yuksekligi'",
      sert_mi("- 0.20 mm katman yüksekliğiyle basılabilir."))
check("ONCE-KIRMIZI ifsa: 'destek gerektirmeden basilabilir'",
      sert_mi("- Destek gerektirmeden basılabilir."))
check("ONCE-KIRMIZI ifsa: 'desteksiz basilir'", sert_mi("- Tek parça halinde desteksiz basılır."))
check("ONCE-KIRMIZI ifsa: 'baski yonu'", sert_mi("- Baskı yönü dayanıklılık için önemlidir."))
check("ONCE-KIRMIZI ifsa: 'kolay baski geometri'", sert_mi("- Kolay baskı alacak geometri."))
check("ONCE-KIRMIZI ifsa: 'FDM veya SLA ile basilabilir'",
      sert_mi("- FDM veya SLA ile basılabilir."))
check("ONCE-KIRMIZI ifsa: baslikta '3D Basilabilir'",
      sert_mi("Rüzgar göstergesi.", baslik="Yelkenli 3D Basılabilir Rüzgar Göstergesi"))
check("ONCE-KIRMIZI ifsa: 'baskiya uygun'", sert_mi("- Baskıya uygun biçimde hazırlanmıştır."))
check("ONCE-KIRMIZI ifsa: 'dilimleme sirasinda'", sert_mi("- Sol taraf için dilimleme sırasında aynalanabilir."))
check("ONCE-KIRMIZI ifsa: 'nozul CAPI' (0,4 mm nozul)", sert_mi("- PLA ile 0,4 mm nozul için tasarlanmıştır."))
check("ONCE-KIRMIZI ifsa: '3 parcali basim'",
      sert_mi("- Üç parça halinde basılıp yapıştırılır."))

# ISLEV/UYUM bilgisi KORUNUR (ifsa DEGIL) -> hicbir kademe yanmaz
for _t in ("Orijinal parçanın yerine geçer, montajı kolaydır.",
           "Dayanıklı malzemeden özel tasarım üretimle hazırlanır.",
           "Farklı renk seçenekleri mevcuttur.",
           "M8 delikler 50 mm aralıklıdır (merkezden merkeze)."):
    check("ISLEV korunur: %r" % _t[:38], not sert_mi(_t) and not uyari_mi(_t))

# --- 🔴 YANLIS-POZITIF FIKSTURU (Turkce cok-anlamlilik) — HEPSI YESIL --------------
# 1) "profesyonel destek" = KURULUMDA usta destegi (dilimleyici destegi DEGIL) — 17 canli kayit
for _t in ("- Kolay montaj imkanı sunar, profesyonel destek gerektirmez.",
           "- Kolay montaj imkanı sunarak profesyonel destek gerektirmeden yenileme sağlar.",
           "Montajı son derece pratiktir, profesyonel destek gerektirmeden kolayca takılabilir."):
    check("FP profesyonel-destek YESIL: %r" % _t[:40], not sert_mi(_t) and not uyari_mi(_t))
# 2) "desteksiz direk" = YELKEN donanimi terimi (istralsiz direk) — 1 canli Marin kaydi
check("FP desteksiz-direk YESIL",
      not sert_mi("- 3 inç çaplı, desteksiz direklerde kullanılır.")
      and not uyari_mi("- 3 inç çaplı, desteksiz direklerde kullanılır."))
# 3) urunun HEDEF CIHAZI 3D yazici (yazici PARCASI satiyoruz) — 6 canli Elektronik/Kamera kaydi
check("FP 3D-yazici-hedef YESIL (anakart fan tutucu)",
      not sert_mi("Anet A6 3D yazıcının anakartını serin tutan özel üretim fan tutucu.",
                  baslik="Anet A6 3D Yazıcı Anakart Soğutma Fanı Tutucusu"))
check("FP 3D-yazici-hedef YESIL (baski kafasi kablo tutucu)",
      not sert_mi("CTC 3D yazıcıların baskı kafası kablo demetini tutan üst destek.",
                  baslik="CTC 3D Yazıcı Üst Kablo Tutucu"))
check("FP 3D-yazici-hedef YESIL (OctoPrint baski takibi)",
      not sert_mi("Anycubic Chiron 3D yazıcıya Raspberry Pi kamerayla baskı takibi "
                  "(OctoPrint vb.) kurmak için özel üretim montaj seti."))
# ... ama muafiyet KOSULLU: "yazici ILE URETILIR" = BIZIM surecimiz -> muafiyet DUSER
check("3D-yazici muafiyeti KACAK DELIGI DEGIL: 'yazicilarla basilabilecek' -> KIRMIZI",
      sert_mi("SLA ve FDM yazıcılarla farklı yönlerde basılabilecek şekilde tasarlanmıştır."))
check("3D-yazici muafiyeti KACAK DELIGI DEGIL: '3D yazici ile uretilir' -> muafiyet duser",
      dk._yazici_hedef_urun("ürün 3d yazıcı ile üretilir") is False)
# 4) "nozul/nozzle" = OTOMOTIV parcasi (far yikama, sprey, supurge) — 9 canli kayit
for _t in ("Far yıkama nozul kapağı; tampondaki nozul yuvasına klipslenir.",
           "Şanzıman yağı değişim nozulu.",
           "Sprey nozzle silecek koluna entegre olduğundan uyumludur."):
    check("FP otomotiv-nozul YESIL: %r" % _t[:38], not sert_mi(_t))
# 5) "SLS" = Mercedes Self-Levelling Suspension (uretim teknolojisi DEGIL)
check("FP Mercedes-SLS YESIL", not sert_mi("Mercedes W126 SLS amortisör takoz halkası."))
# 6) "ABS" = otomotiv fren sistemi; TEK BASINA yasak DEGIL (yalniz baski fiiliyle birlikte)
check("FP otomotiv-ABS YESIL (tek basina)", not sert_mi("ABS fren sensörü kablo klipsi."))
check("ABS PLASTIK + baski fiili -> KIRMIZI", sert_mi("- ABS ile basılması önerilir."))
# 7) "dilimleme makinesi" = GIDA dilimleyici (slicer DEGIL)
check("FP gida-dilimleme-makinesi YESIL",
      not sert_mi("Elektrikli dilimleme makinelerinde motoru bıçağa bağlayan plastik dişli."))
# 8) "basil-" = BASMA (press) anlami — dugme/tus baglaminda ifsa DEGIL
for _t in ("Düğmelere yanlışlıkla basılmasını önleyen kapaktır.",
           "Acil açma tuşuna kazara basılmasını engeller.",
           "Korna düğmesine basılmasını önler.",
           "Fitil yerine basılır; araçta delik açılmaz."):
    check("FP press-anlami YESIL: %r" % _t[:38], not sert_mi(_t) and not uyari_mi(_t))
# 8b) 🔴 PRESS SUSTURUCUSU FAIL-OPEN NOBETCISI (31 Tem)
# _PRESS_RE bir SUSTURUCU. Sinirsiz oldugunda `tu[şs]` masum kelime ICINDE esliyordu
# ("kuTUSu" 585 canli eslesme, "tuTUŞ" 162) ve AYNI CUMLEDEKI gercek baski ifsasini
# sessizce yutuyordu. Probe BILEREK dar: malzeme adi / tavsiye fiili / dosya-tabla-katman
# jetonu YOK -> yalniz 'basil- + surec jetonu' konjonksiyonu yakalayabilir; boylece iddia
# baska bir kovanin sirtina binip OLU hale gelmez.
_M_PRESS_KACAK = "- Sigorta kutusu ters basılır."
check("PRESS FAIL-OPEN: masum 'kutusu' ihlali SUSTURAMAZ -> SERT", sert_mi(_M_PRESS_KACAK))
# ... ve karsi yon: GERCEK press sozcugu ayni cumlede varsa susturma CALISMAYA DEVAM eder
for _t in ("Sigorta kutusundaki düğmeye kazara basılmasını önler.",
           "Torpido kutusu açma tuşuna basılmasını engelleyen kilit dili."):
    check("PRESS susturmasi KORUNDU (kutusu + gercek press) YESIL: %r" % _t[:40],
          not sert_mi(_t) and not uyari_mi(_t))
# 9) fiziksel "destek" parcasi = urunun KENDISI
for _t in ("Kaput destek çubuğunu yerinde tutan özel tasarım klips.",
           "Bimini tente boru iç desteği; kırılan orijinal desteğin yerine geçer."):
    check("FP fiziksel-destek YESIL: %r" % _t[:38], not sert_mi(_t))

# --- SERT vs UYARI AYRIMI: supheli/belirsiz OTOMATIK REDDEDILMEZ ----------------------
check("BELIRSIZ 'iki adet basilir' -> UYARI (sert DEGIL)",
      uyari_mi("- İki adet basılır.") and not sert_mi("- İki adet basılır."))
check("BELIRSIZ 'ek destek gerektirmez' (uretim fiili YOK) -> UYARI",
      uyari_mi("Menteşe düz tabanlıdır, ek destek gerektirmez.")
      and not sert_mi("Menteşe düz tabanlıdır, ek destek gerektirmez."))
check("KESIN 'destek gerektirmeden uretilir' (uretim fiili VAR) -> SERT",
      sert_mi("Destek gerektirmeden üretilir."))

# --- MUTASYON: kapi kendini koruyor (kural listesi bosaltilirsa / no-op olursa KIRMIZI) --
_M_DOLGU = "- %100 dolgu oranı önerilir."
# ⚠️ 31 Tem: PROBE DEGISTI. Eski probe "- PETG ile basılması önerilir." idi; yeni
# 'malzeme-tavsiye' kovasi (malzeme ADI + TAVSIYE fiili) o cumleyi ARTIK BAGIMSIZ
# olarak yakaliyor. Yani _SUREC_TOKEN_RE no-op edilse bile cumle SERT kaliyordu ve
# mutant SAG KALIYORDU — iddia OLU hale gelmisti (kural zayifladi diye DEGIL, ikinci
# bir kova ayni cumleyi kapsadi diye). Iddiayi yasatmak icin probe, YALNIZ
# 'basil- + surec jetonu' konjonksiyonunun yakalayabilecegi bir cumleye cekildi:
# malzeme adi YOK, tavsiye fiili YOK, dosya/tabla/katman jetonu YOK; tasiyici jeton
# yalnizca 'parca halinde'.
# ⚠️ 31 Tem (2. kez): PROBE YINE BAYATLADI. "- İki parça halinde basılır." bu kez
# `basil-print` SERT kuralinin (`parça halinde basıl`) kapsamina girdi; jeton no-op
# edilse bile cumle SERT kaliyor ve mutant SAG kaliyordu (iddia OLU, kabul testi
# taban-KIRMIZI). Probe yeniden daraltildi: tasiyici jeton yalnizca 'ters bas'.
_M_BASKI = "- Ters basılır."
check("mutasyon oncesi taban: dolgu SERT", sert_mi(_M_DOLGU))
_eski_sert = dk._IFSA_SERT_RE
dk._IFSA_SERT_RE = ()                                   # MUT: kesin-yasak listesi BOSALTILDI
check("MUT-BOS-LISTE: kural listesi bosalinca dolgu ifsasi KACAR (liste yuk tasiyor)",
      not sert_mi(_M_DOLGU))
dk._IFSA_SERT_RE = _eski_sert
check("MUT-BOS-LISTE geri alindi: dolgu yine SERT", sert_mi(_M_DOLGU))

_eski_tok = dk._SUREC_TOKEN_RE
dk._SUREC_TOKEN_RE = _re.compile(r"(?!x)x")             # MUT: konjonksiyon jetonu no-op
check("MUT-NOOP-JETON: surec jetonu no-op olunca 'PETG ile basilmasi' SERT'ten duser",
      not sert_mi(_M_BASKI))
dk._SUREC_TOKEN_RE = _eski_tok
check("MUT-NOOP-JETON geri alindi: yine SERT", sert_mi(_M_BASKI))

_eski_muaf = dk._IFSA_MUAF_RE
dk._IFSA_MUAF_RE = ()                                   # MUT: muaf listesi bosaltildi
check("MUT-BOS-MUAF: muaf listesi bosalinca 'profesyonel destek' YANLIS yakalanir "
      "(muaf listesi yuk tasiyor)",
      uyari_mi("- Kolay montaj imkanı sunar, profesyonel destek gerektirmez."))
dk._IFSA_MUAF_RE = _eski_muaf
check("MUT-BOS-MUAF geri alindi: 'profesyonel destek' yine YESIL",
      not uyari_mi("- Kolay montaj imkanı sunar, profesyonel destek gerektirmez."))

# MUT-PRESS-SINIRSIZ: kelime siniri geri alinirsa (fail-open geri gelirse) masum "kutusu"
# gercek ifsayi susturur -> probe SERT'ten duser. Iddia: `\b` yuk tasiyor.
_eski_press = dk._PRESS_RE
dk._PRESS_RE = _re.compile(r"d[üu][ğg]me|tu[şs]|buton|korna|pedal|fitil|ayak\s*day", _re.UNICODE)
check("MUT-PRESS-SINIRSIZ: sinir kalkinca 'kutusu' ihlali SUSTURUR (fail-open geri doner)",
      not sert_mi(_M_PRESS_KACAK))
dk._PRESS_RE = _eski_press
check("MUT-PRESS-SINIRSIZ geri alindi: probe yine SERT", sert_mi(_M_PRESS_KACAK))


# --- GERCEK-VERI NOBETCISI: canli katalogda taban/FP durumu ---------------------------
# (a) 🔴 MERGE SARTI: kapsam ici HICBIR canli kayit taban ALTINDA olmamali. Kapi fail-closed
#     ve --commit-farki koluyla CI'da BLOKLAYICI kosuyor; taban-alti kayit varken dal main'e
#     ALINMAZ. OLCULDU (31 Tem, 15.930 urun): 23 kayit kapsam disi (parametrik/Jeneratör/BOS
#     fiyat — ucu de AYNI 23 kayit), 15.907 kayit kapsam ici, 1.761'i taban ALTI
#     (Otomobil 1.758 · Oyun/Hobi 2 · Ev 1), ayristirilamayan 0. Bu nobetci VERI duzeltilene
#     kadar KIRMIZIDIR ve kirmizi kalmasi DOGRUDUR — veri duzeltmesi ayri duzlem (MaCiT).
# (b) Olculmus 24 yanlis-pozitif kaydin hepsi YESIL kalmali (ifsa desen kaymasi nobetcisi).
_FP_IDLER = [
    "bmw-i3-safedrive-ekran-tutucu-aparat", "bmw-koltuk-klipsi-52-10-1-945-442",
    "bmw-m2-ve-uyumlu-modeller-i-in-debriyaj-pedal-stoperi",
    "fiat-ducato-i-far-anahtar-montaj-yuvas",
    "fiat-ducato-peugeot-boxer-citroen-jumper-usb-montaj-aparat",
    "opel-vivaro-d-rtl-fla-r-d-me-kapa", "peugeot-206-anahtar-tu-tak-m",
    "peugeot-307sw-uyumlu-d-eme-ve-panel-klipsi", "skoda-octavia-kol-ak-kilidi",
    "skoda-superb-orijinal-telefon-tutucu-d-n-t-r-c-aparat",
    "toyota-4runner-3-nesil-arka-k-ll-k-i-ptal-ve-usb-panel-brake",
    "toyota-koltuk-is-tma-d-mesi-er-evesi", "toyota-mr2-sw20-k-ll-k-kapa-ve-telefon-tutucu",
    "toyota-switch-panel-adapt-r", "volkswagen-t4-tavan-d-emesi-klipsi",
    "volvo-740-sinyal-kolu-uzat-c-aparat", "volvo-xc60-havaland-rma-izgaras-y-nlendirme-klipsi",
    "yelkenli-yelken-baglama-halkasi",
    "anet-a6-anakart-sogutma-fan-tutucu", "ctc-yazici-ust-kablo-tutucu",
    "gt2-20-dis-tahrik-kasnagi-nema17", "porsche-turbo-logolu-step-motor-ve-qr-kod-kapa",
    "raspberry-pi-kamera-mount-anet-a8", "raspberry-pi-kamera-mount-chiron",
]
if isinstance(_canli, list):
    _idx = {u.get("id"): u for u in _canli if isinstance(u, dict)}
    _muaf_kayit = [u for u in _canli if isinstance(u, dict) and dk.fiyat_muaf(u)]
    _ihlalli = [u for u in _canli if isinstance(u, dict) and dk.kapi_fiyat(u)[0] is not None]
    _ihlal_kat = {}
    for _u in _ihlalli:
        _k = _u.get("kategori")
        _ihlal_kat[_k] = _ihlal_kat.get(_k, 0) + 1
    check("gercek-veri: sari seri (parametrik/Jeneratör) kapsam DISI ve kirmizi yanmiyor",
          not [u.get("id") for u in _muaf_kayit if dk.kapi_fiyat(u)[0] is not None])
    check("🔴 MERGE SARTI — gercek-veri: canli katalogda taban-alti/ayiklanamaz kayit 0",
          len(_ihlalli) == 0)
    print("KAPI 7 gercek-veri: %d urun · kapsam DISI (sari seri) %d · IHLAL %d %s"
          % (len(_canli), len(_muaf_kayit), len(_ihlalli),
             sorted(_ihlal_kat.items(), key=lambda x: -x[1])))
    if _ihlalli:
        print("TABAN-ALTI (%d, merge sarti: 0): %s" %
              (len(_ihlalli), ", ".join(str(u.get("id")) for u in _ihlalli[:20])),
              file=sys.stderr)
    # --- GERCEK KAYIT SEKLIYLE pozitif/negatif (kisaltilmis sahte sekil DEGIL) ---------
    # Canli katalogdan bir kayit KOPYALANIR, yalniz `fiyat` degistirilir: kapinin hukmu
    # kaydin TAM sekliyle (lisans/gorseller/marka/aciklama alanlari dahil) olculur.
    _gercek_oto = next((u for u in _canli if isinstance(u, dict)
                        and u.get("kategori") == "Otomobil"), None)
    _gercek_sari = next((u for u in _canli if isinstance(u, dict) and dk.fiyat_muaf(u)), None)
    check("gercek-sekil fikstur: canli Otomobil ve sari-seri kaydi bulundu",
          _gercek_oto is not None and _gercek_sari is not None)
    if _gercek_oto is not None:
        _g1 = dict(_gercek_oto); _g1["fiyat"] = "150 TL"
        _g2 = dict(_gercek_oto); _g2["fiyat"] = "250 TL"
        _g3 = dict(_gercek_oto); _g3["fiyat"] = "sorunuz"
        check("gercek-sekil POZ: canli kayit '150 TL' -> IHLAL", fiyat_kirmizi(_g1))
        check("gercek-sekil NEG: canli kayit '250 TL' -> YESIL", not fiyat_kirmizi(_g2))
        check("gercek-sekil POZ: canli kayit 'sorunuz' -> IHLAL (fail-closed)", fiyat_kirmizi(_g3))
    if _gercek_sari is not None:
        _g4 = dict(_gercek_sari); _g4["fiyat"] = "100 TL"
        check("gercek-sekil NEG: canli SARI kayit (fiyat BOS) -> YESIL",
              not fiyat_kirmizi(_gercek_sari))
        check("gercek-sekil NEG: canli SARI kayit '100 TL' olsa bile -> YESIL (istisna)",
              not fiyat_kirmizi(_g4))
    _fp_bulunan = [i for i in _FP_IDLER if i in _idx]
    check("gercek-veri: FP nobetci kumesi >=20 kayit bulundu", len(_fp_bulunan) >= 20)
    _fp_kirmizi = [i for i in _fp_bulunan if dk.kapi_ifsa(_idx[i])["sert"]]
    check("gercek-veri: olculmus 24 yanlis-pozitif kaydin hicbiri SERT yanmiyor",
          len(_fp_kirmizi) == 0)
    if _fp_kirmizi:
        print("FP REGRESYONU (%d): %s" % (len(_fp_kirmizi), ", ".join(_fp_kirmizi)), file=sys.stderr)
    print("KAPI 7/8 gercek-veri: %d urun, taban-alti %d (merge sarti: 0), FP-regresyon %d"
          % (len(_canli), len(_ihlalli), len(_fp_kirmizi)))


if FAILS:
    print("\n%d KONTROL KALDI" % len(FAILS), file=sys.stderr)
    sys.exit(1)
print("TEST GECTI (%d urun fixture, tum kapilar)" % len(urunler))
sys.exit(0)

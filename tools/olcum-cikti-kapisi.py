#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLCUM CIKTI KAPISI (K314②, 27 Agu 2026) — SINIF kapisi, tekil yama DEGIL.

═══════════════════════════════════════════════════════════════════════════════
NEYI KAPATIR
═══════════════════════════════════════════════════════════════════════════════
26 Agu 2026'da iki IC KOSUM RAPORU (`tools/k309d2-kosum-rapor.txt`,
`tools/k309d2-olcum-rapor.txt`) PUBLIC depoya girdi ve `kisisel-veri-test.py`
KURAL A yayini durdurdu. Kok sebep dosyalar DEGIL, araclarin YAZMA YERIYDI:
her iki arac da raporunu `os.path.dirname(__file__)` ile KENDI YANINA — yani
IZLENEN AGACA — yaziyordu.

Iki dosyayi silmek o iki VAKAYI kapatir, SINIFI kapatmaz: ayni araclarin bir
sonraki kosumu ayni yere yeniden yazar; yarin yazilacak UCUNCU olcum araci da
ayni kalibi kopyalar. Bu kapi o kalibi MAKINE olarak yasaklar.

═══════════════════════════════════════════════════════════════════════════════
KURAL (tek cumle)
═══════════════════════════════════════════════════════════════════════════════
Depodaki hicbir Python arac dosyasi, ADI IC-RAPOR ADLANDIRMA AILESINE UYAN bir
dosyayi DEPODAN TURETILEN bir dizine YAZMA kipiyle acmayacak.

  * "ic-rapor adlandirma ailesi" TANIMI BURADA YENIDEN YAZILMAZ: tek kaynak
    `tools/kisisel-veri-test.py::ic_rapor_mu`. Bu kapi o fonksiyonu dosyadan
    YUKLEYIP CAGIRIR. Yuklenemezse hukum YESIL DEGIL, OLCULEMEDI'dir (rc 2).
    ([[ikiz-tanim-sessiz-ayrisma]] — iki kopya sessizce ayrisir.)
  * "depodan turetilen dizin" = `__file__`/`dirname`/`abspath` zincirinden ya da
    depo koku sabitinden turemis bir ad, ya da duz goreli/depo-ici dize.
  * DOGRU YOL: `from olcum_cikti import olcum_yolu` -> kok SABIT ve depo DISI.

🔴 KAPSAM BILEREK DAR (yanlis-pozitif = TUM YAYIN durur):
  * YALNIZ yazma kipi (`w`/`a`/`x`) ile acilan dosyalar. Okuma serbest.
  * YALNIZ ADI aileye uyan dosyalar. `tools/k309d2-kosum-ham.json` gibi baska
    adlar bu kapinin ekseni DEGILDIR (onlari KURAL A da yakalamaz; ayri eksen).
  * Gecici dizine (`tempfile`, `TemporaryDirectory`, `mkdtemp`, `gettempdir`)
    ya da `olcum_cikti` modulune dayanan yollar YESIL — dogru yol budur.
  * Fikstur/veri listelerindeki dize sabitleri (acilmayan adlar) DOKUNULMAZ:
    kural CAGRI YERINE bakar, metne degil ([[kapinin-menzili-cagri-yeridir]]).

KOSUM:
    python3 tools/olcum-cikti-kapisi.py            # canli tarama + fiksturler
    python3 tools/olcum-cikti-kapisi.py --kendini-test
Cikis: 0 = YESIL · 1 = KIRMIZI (ihlal) · 2 = OLCULEMEDI (yesil DEGIL).
"""
import argparse
import ast
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
KURAL_A_KAYNAGI = os.path.join(TOOLS, "kisisel-veri-test.py")

OK, KIRMIZI, OLCULEMEDI = 0, 1, 2

# Yazma kipi jetonlari.
YAZMA_KIPLERI = ("w", "a", "x", "+")
# Depo koku turetme izleri (kaynak metninde aranir).
DEPO_TURETME_IZLERI = ("__file__", "ROOT", "REPO", "BURASI", "HERE", "KOK")
# Gecici/dogru yol izleri — bunlardan biri gecerse yol depo agaci DEGILDIR.
GUVENLI_IZLER = ("tempfile", "gettempdir", "mkdtemp", "TemporaryDirectory",
                 "olcum_yolu", "olcum_dizini", "olcum_koku", "OLCUM_KOKU")


class Olculemedi(Exception):
    """Hukum kuracak veri yok. YESIL DEGILDIR."""


# ---------------------------------------------------------------- tek kaynak: KURAL A
def _ic_rapor_mu_yukle():
    """`ic_rapor_mu`yu KURAL A'nin KENDI dosyasindan yukler (ikinci tanim YOK)."""
    if not os.path.exists(KURAL_A_KAYNAGI):
        raise Olculemedi("KURAL A kaynagi yok: %s" % KURAL_A_KAYNAGI)
    sys.path.insert(0, TOOLS)
    try:
        spec = importlib.util.spec_from_file_location("kisisel_veri_test_kural_a",
                                                      KURAL_A_KAYNAGI)
        if spec is None or spec.loader is None:
            raise Olculemedi("KURAL A modul spec'i kurulamadi")
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
    except Olculemedi:
        raise
    except Exception as e:  # noqa: BLE001
        raise Olculemedi("KURAL A yuklenemedi (%s: %s)" % (type(e).__name__, e))
    fn = getattr(modul, "ic_rapor_mu", None)
    if not callable(fn):
        raise Olculemedi("KURAL A dosyasinda `ic_rapor_mu` YOK — tek kaynak koptu")
    # CANLILIK CAPASI: yuklenen fonksiyon gercekten AYIRT EDIYOR mu? Govdesi
    # `return False` yapilirsa bu kapi sessizce her seyi yesil sayardi.
    if not fn("x/ONARIM-RAPORU.md") or fn("x/urunler.json") or fn("x/raporlama.md"):
        raise Olculemedi("KURAL A `ic_rapor_mu` AYIRT ETMIYOR (olu/gevsek) — "
                         "bu kapi onun uzerine hukum kuramaz")
    return fn


# ---------------------------------------------------------------- AST tarayici
def _kaynak(dugum):
    try:
        return ast.unparse(dugum)
    except Exception:  # noqa: BLE001  (cok eski/bozuk dugum)
        return ""


def _kip_yazma_mi(cagri):
    """`open(...)` cagrisinin kipi yazma mi? Kip BELIRSIZSE yazma SAYILMAZ."""
    kip = None
    if len(cagri.args) >= 2 and isinstance(cagri.args[1], ast.Constant):
        kip = cagri.args[1].value
    for kw in cagri.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            kip = kw.value.value
    if not isinstance(kip, str):
        return False
    return any(c in kip for c in YAZMA_KIPLERI)


def _acma_cagrisi_mi(cagri):
    f = cagri.func
    if isinstance(f, ast.Name) and f.id == "open":
        return True
    if isinstance(f, ast.Attribute) and f.attr == "open":
        return isinstance(f.value, ast.Name) and f.value.id in ("io", "codecs")
    return False


def _dizeler(dugum):
    return [d.value for d in ast.walk(dugum)
            if isinstance(d, ast.Constant) and isinstance(d.value, str)]


# 🔴 27 AGU — ADI KONMUS YOL COZUMLEMESI (kapinin ILK surumunun OLCULEN deligi).
# Ilk surum YALNIZ cagri yerindeki ifadeye bakiyordu ve 26 Agu'nun GERCEK kodunu
# KACIRIYORDU (olculdu, hedef-kol probu: ESKI k309d2-kos.py -> IHLAL=0). Cunku
# gercek kalip iki adimlidir:
#     rapor = os.path.join(BURASI, "k309d2-kosum-rapor.txt")
#     with io.open(rapor, "w", ...) as rf:
# Cagri yerindeki ifade sadece `rapor` adidir; dosya adi ONCEKI ATAMADADIR.
# Kirmizi fiksturlerin hepsi geciyordu cunku hepsi TEK ADIMLI yazilmisti —
# fikstur ailesi gercek kalibi TASIMIYORDU ([[kabul-fiksturu-yasagi-kutsar]]).
# COZUM parser taklidi DEGIL: modul genelinde `<ad> = <ifade>` atamalari
# toplanir ve yol bir ADSA ifadesi yerine konur (en fazla _COZUM_DERINLIGI kez;
# dongusel atamada durur). Kapsam over-approximation'dir ve BILEREK oyle: kural
# ZATEN aile-adi + depo-turetmesi sartlarini birlikte arar.
_COZUM_DERINLIGI = 3


def _atama_haritasi(agac):
    harita = {}
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.Assign):
            for hedef in dugum.targets:
                if isinstance(hedef, ast.Name):
                    harita.setdefault(hedef.id, dugum.value)
        elif isinstance(dugum, ast.AnnAssign) and isinstance(dugum.target, ast.Name):
            if dugum.value is not None:
                harita.setdefault(dugum.target.id, dugum.value)
    return harita


def _yolu_coz(ifade, harita):
    """Yol ifadesini adlari yerine koyarak cozer; (dugumler, gorulen_adlar) doner."""
    dugumler = [ifade]
    adlar = set()
    for _ in range(_COZUM_DERINLIGI):
        yeni = []
        for d in dugumler:
            for alt in ast.walk(d):
                if isinstance(alt, ast.Name) and alt.id in harita and alt.id not in adlar:
                    adlar.add(alt.id)
                    yeni.append(harita[alt.id])
        if not yeni:
            break
        dugumler.extend(yeni)
    return dugumler, adlar


def ihlaller(kaynak_metni, dosya_adi, ic_rapor_mu):
    """(satir, dosya_adi_sabiti, yol_ifadesi) uclulerinin listesi.

    GERCEK tarama ve fikstur oz-kontrolu AYNI govdeyi kullanir: bu fonksiyon
    no-op yapilirsa (`return []`) fiksturler de kirmizi yanar (olu-tarayici
    korumasi — [[kabul-fiksturu-yasagi-kutsar]] dersinin tersi kol).
    """
    try:
        agac = ast.parse(kaynak_metni, filename=dosya_adi)
    except SyntaxError as e:
        raise Olculemedi("%s ayristirilamadi: %s" % (dosya_adi, e))
    harita = _atama_haritasi(agac)
    bulgular = []
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Call) or not _acma_cagrisi_mi(dugum):
            continue
        if not _kip_yazma_mi(dugum):
            continue
        if not dugum.args:
            continue
        yol_ifadesi = dugum.args[0]
        cozulen, _adlar = _yolu_coz(yol_ifadesi, harita)
        metin = " | ".join(_kaynak(d) for d in cozulen)
        if any(iz in metin for iz in GUVENLI_IZLER):
            continue
        # Depo agaci ile iliskili mi? (kaba + dar: ad izi ya da goreli duz dize)
        depo_izi = any(iz in metin for iz in DEPO_TURETME_IZLERI)
        # DAR KALIR: "duz dize" YALNIZ cagri yerindeki ifadenin KENDISI bir dize
        # sabitiyse gecerlidir. Cozulen dugumlerin herhangi birinde dize bulunmasi
        # yeterli SAYILMAZ — o kural neredeyse her yola uyar ve kapiyi genisletir.
        duz_dize = (isinstance(yol_ifadesi, ast.Constant)
                    and isinstance(yol_ifadesi.value, str))
        if not depo_izi and not duz_dize:
            continue
        dizeler = []
        for d in cozulen:
            dizeler.extend(_dizeler(d))
        for dize in dizeler:
            ad = dize.rsplit("/", 1)[-1]
            if "." not in ad:
                continue
            if ic_rapor_mu("x/" + ad):
                bulgular.append((getattr(dugum, "lineno", 0), ad, metin[:200]))
                break
    return bulgular


def _py_dosyalari():
    yollar = []
    for kok, _dizinler, dosyalar in os.walk(TOOLS):
        for d in sorted(dosyalar):
            if d.endswith(".py"):
                yollar.append(os.path.join(kok, d))
    return sorted(yollar)


# ---------------------------------------------------------------- fiksturler
_KIRMIZI_FIKSTURLER = [
    # 🔴 BU FIKSTUR 26 AGU'NUN GERCEK KAYNAK KALIBIDIR (git 5dc23886'dan alinmis
    # bicim): yol ONCE bir ADA atanir, `open` o ADI alir. Kapinin ILK surumu tam
    # bu kalibi KACIRIYORDU (olculdu: ESKI k309d2-kos.py -> IHLAL=0) ve butun
    # fiksturler yine de yesildi — cunku fikstur ailesi tek adimli yazilmisti.
    # Bu satir o deligin nobetcisidir; adi konmus yol cozumlemesi sokulurse KACAR.
    ("ADI KONMUS YOL — 26 Agu'nun GERCEK kalibi (rapor = join(...); open(rapor,'w'))",
     'import os, io\n'
     'BURASI = os.path.dirname(os.path.abspath(__file__))\n'
     'CIKTI = os.path.join(BURASI, "k309d2-kosum")\n'
     'def main():\n'
     '    rapor = os.path.join(BURASI, "k309d2-kosum-rapor.txt")\n'
     '    with io.open(rapor, "w", encoding="utf-8") as rf:\n'
     '        rf.write("x")\n'),
    ("ADI KONMUS YOL — iki halkali (kok -> ara ad -> dosya adi)",
     'import os\n'
     'ROOT = os.path.dirname(os.path.abspath(__file__))\n'
     'DIZIN = os.path.join(ROOT, "cikti")\n'
     'hedef = os.path.join(DIZIN, "ONARIM-RAPORU.md")\n'
     'open(hedef, "w").write("x")\n'),
    ("BURASI + rapor.txt (tek adimli yazim)",
     'import os, io\n'
     'BURASI = os.path.dirname(os.path.abspath(__file__))\n'
     'with io.open(os.path.join(BURASI, "k309d2-kosum-rapor.txt"), "w") as f:\n'
     '    f.write("x")\n'),
    ("ROOT + ONARIM-RAPORU.md",
     'import os\n'
     'ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
     'open(os.path.join(ROOT, "ONARIM-RAPORU.md"), "w").write("x")\n'),
    ("duz goreli dize",
     'open("tools/olcum-raporu.txt", "w").write("x")\n'),
    ("mode= anahtar kelimesiyle",
     'import os\n'
     'BURASI = os.path.dirname(__file__)\n'
     'open(os.path.join(BURASI, "CURUTME-RAPORU.md"), mode="a").write("x")\n'),
    ("alt dizinde de yakalanir (ad ekseni dizinden BAGIMSIZ)",
     'import os\n'
     'ROOT = os.path.dirname(__file__)\n'
     'open(os.path.join(ROOT, "k309d2", "denetim-raporu.txt"), "w").write("x")\n'),
]

_YESIL_FIKSTURLER = [
    ("dogru yol: olcum_yolu",
     'from olcum_cikti import olcum_yolu\n'
     'open(olcum_yolu("k309d2-kosum-rapor.txt"), "w").write("x")\n'),
    ("gecici dizin",
     'import os, tempfile\n'
     'd = tempfile.mkdtemp()\n'
     'open(os.path.join(d, "ONARIM-RAPORU.md"), "w").write("x")\n'),
    ("OKUMA kipi — kural yalniz YAZMAYI olcer",
     'import os\n'
     'BURASI = os.path.dirname(__file__)\n'
     'open(os.path.join(BURASI, "k309d2-kosum-rapor.txt")).read()\n'),
    ("aileye UYMAYAN ad (ham.json) — ayri eksen, bu kapi karismaz",
     'import os\n'
     'BURASI = os.path.dirname(__file__)\n'
     'open(os.path.join(BURASI, "k309d2-kosum-ham.json"), "w").write("x")\n'),
    ("fikstur LISTESINDE gecen ad — acilmadigi icin ihlal DEGIL",
     'ADLAR = ["ONARIM-RAPORU.md", "CURUTME-RAPORU.md"]\n'
     'print(ADLAR)\n'),
    ("ADI KONMUS YOL ama gecici dizine cozuluyor (cozumleme kapiyi GENISLETMESIN)",
     'import os, tempfile\n'
     'KOK = tempfile.mkdtemp()\n'
     'hedef = os.path.join(KOK, "k309d2-kosum-rapor.txt")\n'
     'open(hedef, "w").write("x")\n'),
    ("ADI KONMUS YOL ama olcum_yolu ile cozuluyor",
     'from olcum_cikti import olcum_yolu\n'
     'hedef = olcum_yolu("ONARIM-RAPORU.md")\n'
     'open(hedef, "w").write("x")\n'),
    ("mesru turev: raporlama.md",
     'import os\n'
     'BURASI = os.path.dirname(__file__)\n'
     'open(os.path.join(BURASI, "raporlama.md"), "w").write("x")\n'),
]


def fikstur_hatalari(ic_rapor_mu):
    hatalar = []
    for etiket, kaynak in _KIRMIZI_FIKSTURLER:
        if not ihlaller(kaynak, "fikstur.py", ic_rapor_mu):
            hatalar.append("FIKSTUR(kirmizi) KACTI — kural zayifladi: %s" % etiket)
    for etiket, kaynak in _YESIL_FIKSTURLER:
        bulgu = ihlaller(kaynak, "fikstur.py", ic_rapor_mu)
        if bulgu:
            hatalar.append("FIKSTUR(yesil) YANLIS-POZITIF — kural DARALTILMALI: %s -> %r"
                           % (etiket, bulgu))
    return hatalar


def _mutant_hatalari(ic_rapor_mu):
    """OLU-KAPI KORUMASI: kural kolu sokulunce fiksturler KIRMIZI yanmali."""
    hatalar = []
    # M1 — "yazma kipi" kolu olurse: OKUMA fiksturu artik kirmizi yanmali.
    kaynak_okuma = _YESIL_FIKSTURLER[2][1]
    kip_asli = globals()["_kip_yazma_mi"]
    globals()["_kip_yazma_mi"] = lambda _c: True
    try:
        if not ihlaller(kaynak_okuma, "m1.py", ic_rapor_mu):
            hatalar.append("M1: `yazma kipi` kolu sokuldu ama OKUMA fiksturu hala YESIL "
                           "-> kol zaten olu (hicbir sey olcmuyor)")
    finally:
        globals()["_kip_yazma_mi"] = kip_asli
    # M2 — KONTROL: kol geri konunca ayni fikstur YESIL doner.
    if ihlaller(kaynak_okuma, "m2.py", ic_rapor_mu):
        hatalar.append("M2-KONTROL: kol geri konuldu ama fikstur hala KIRMIZI "
                       "(mutant temizlenmemis)")
    # M3 — ADI KONMUS YOL COZUMLEMESI olurse 26 Agu'nun GERCEK kalibi KACMALI.
    # Bu, kapinin ilk surumunde OLCULEN gercek delikti; mutant onu nobete alir.
    kaynak_gercek = _KIRMIZI_FIKSTURLER[0][1]
    coz_asli = globals()["_yolu_coz"]
    globals()["_yolu_coz"] = lambda ifade, _h: ([ifade], set())
    try:
        if ihlaller(kaynak_gercek, "m3.py", ic_rapor_mu):
            hatalar.append("M3: adi konmus yol cozumlemesi SOKULDU ama 26 Agu kalibi "
                           "hala yakalaniyor -> kirmiziyi baska bir kol veriyor, "
                           "cozumleme kolu NOBETSIZ (hedef-kol atfi yok)")
    finally:
        globals()["_yolu_coz"] = coz_asli
    # M4 — KONTROL: kol geri konunca ayni kalip YENIDEN yakalanmali.
    if not ihlaller(kaynak_gercek, "m4.py", ic_rapor_mu):
        hatalar.append("M4-KONTROL: cozumleme kolu geri konuldu ama 26 Agu kalibi "
                       "yakalanmiyor (mutant temizlenmemis / kol olu)")
    return hatalar


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Olcum cikti kapisi (K314②)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="yalniz fikstur + mutant bataryasi")
    a = ap.parse_args()

    try:
        ic_rapor_mu = _ic_rapor_mu_yukle()
    except Olculemedi as e:
        print("OLCULEMEDI — %s" % e)
        print("SONUC: OLCULEMEDI ⚪ (YESIL DEGIL)")
        return OLCULEMEDI

    hatalar = fikstur_hatalari(ic_rapor_mu)
    hatalar.extend(_mutant_hatalari(ic_rapor_mu))
    print("FIKSTUR: %d kirmizi + %d yesil + 4 mutant (M1/M3 oldurucu, M2/M4 kontrol)"
          % (len(_KIRMIZI_FIKSTURLER), len(_YESIL_FIKSTURLER)))

    ihlal_sayisi = 0
    if not a.kendini_test:
        taranan = 0
        for yol in _py_dosyalari():
            try:
                with open(yol, encoding="utf-8") as f:
                    metin = f.read()
            except OSError as e:
                hatalar.append("OKUNAMADI (fail-closed): %s -> %s" % (yol, e))
                continue
            taranan += 1
            try:
                bulgular = ihlaller(metin, yol, ic_rapor_mu)
            except Olculemedi as e:
                hatalar.append("AYRISTIRILAMADI (fail-closed): %s" % e)
                continue
            for satir, ad, ifade in bulgular:
                ihlal_sayisi += 1
                hatalar.append(
                    "OLCUM CIKTISI IZLENEN AGACA YAZILIYOR: %s:%d -> %s  [%s]  "
                    "CARE: `from olcum_cikti import olcum_yolu` + "
                    "`olcum_yolu(\"%s\")`"
                    % (os.path.relpath(yol, ROOT), satir, ad, ifade, ad))
        print("TARANAN=%d dosya  IHLAL=%d" % (taranan, ihlal_sayisi))

    for h in hatalar:
        print("  ❌ %s" % h)
    print("OLCUM CIKTI KAPISI: %s (%d bulgu)"
          % ("GECTI" if not hatalar else "KIRMIZI", len(hatalar)))
    return OK if not hatalar else KIRMIZI


if __name__ == "__main__":
    sys.exit(main())

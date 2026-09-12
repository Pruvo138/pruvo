#!/usr/bin/env python3
"""sahipsiz-kapi-nobetcisi.py — bir kapi/nobetci/test govdesi SESSIZCE sahipsiz kalamaz.

NEDEN (K408, 11 Eyl 2026 — ucuncu tekrar, tekil yama YASAK): bu repoda bir kapi yazilip
hicbir is akisina baglanmadan birakilabiliyor. Kapi kosunca gercek bulgu basar ama kimse
kosturmadigi icin kimse duymaz. Ayni gun UC ornek olculdu:
  * tools/kategori-kapisi.py     -> katalogda gecersiz kategori buluyordu, atif 0
  * tools/gitignore-kapisi.py    -> 11 eksik + 5 fazla drift tasiyordu, atif 0
  * mimar-kilit-test.py + mimar-kapi-mutasyon-test.py -> 92+92 kirmizi biriktirmisti, atif 0
`tools/ci-kapsam-test.py` bu ekseni ZATEN olcer ve `IZIN_LISTESI` ile gerekceli muafiyet
tutar — bu nobetci onun IKINCI KOPYASI DEGILDIR: muafiyet kaydini ONDAN okur (TEK KAYNAK)
ve yalnizca onun EVRENINE hic girmeyen govdeleri sayar.

SOZLESME — bir kapi/nobetci/test govdesi su UC halden BIRINDE olmalidir:
  (1) KOSAN   : en az bir `.github/workflows/*.yml` dosyasinda `run:` satirinda TAM ADIYLA
                cagriliyor (YORUM satiri atif SAYILMAZ),
  (2) MUAF    : `ci-kapsam-test.py::IZIN_LISTESI` icinde GEREKCESIYLE kayitli,
  (3) YARDIMCI: CLI'si yok (`if __name__ == "__main__"` blogu YOK) ve en az bir baska
                tools/*.py onu import ediyor -> kutuphanedir, ayri cagri yeri BEKLENMEZ.
Dorduncu hal — hicbiri — SESSIZ SAHIPSIZLIKTIR ve bu kapi onu sayar.

🔴 EVREN TUZAGI (bu kapinin dogum sebebi): ilk olcum yalnizca `deploy.yml` + `nobet.yml`e
bakmisti ve 34 govdeyi "sahipsiz" ilan etmisti. Gercekte repoda 11 workflow dosyasi var
(`yayin-yasi-alarmi.yml`, `spec-ifsa-alarmi.yml`, `d1-sapma-alarmi.yml`, ...) ve o
govdelerin bir kismi ORADA kosuyordu. Bu yuzden evren burada GLOB'dan turetilir, elle
liste TUTULMAZ: yeni bir workflow dosyasi eklenince kapi onu kendiliginden gorur.

🔴 ONEK TUZAGI: `grep -c "kategori-kapisi"` komutu `altkategori-kapisi` satirini da sayar.
Burada eslesme TAM DOSYA ADI uzerinden, kelime sinirlariyla yapilir.

NON-GROWTH: bugunku sahipsiz sayisi TABAN olarak kayitlidir. Kapi mevcut borcu kirmizi
yakmaz (yoksa her kosum kirmizidir, kimse bakmaz) — ama TABANI ASAN her YENI sahipsizlik
kirmizi yanar. Borc azaldikca taban `--taban-yaz` ile asagi cekilir, ASLA yukari degil.

Kullanim:
  python3 tools/sahipsiz-kapi-nobetcisi.py                # denetle (taban asilirsa exit 1)
  python3 tools/sahipsiz-kapi-nobetcisi.py --envanter     # tam listeyi kova kova bas
  python3 tools/sahipsiz-kapi-nobetcisi.py --kendini-test # kendi iddialarini olc
  python3 tools/sahipsiz-kapi-nobetcisi.py --taban-yaz    # tabani OLCULENE cek (yalniz asagi)
"""
import argparse
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
AKIS_DIZINI = os.path.join(ROOT, ".github", "workflows")
CI_KAPSAM = os.path.join(TOOLS, "ci-kapsam-test.py")
TABAN_DOSYASI = os.path.join(TOOLS, ".sahipsiz-kapi-taban")

# Bu adlardan BIRINI tasiyan tools/*.py govdesi "kapi/nobetci/test" sinifindadir.
SINIF_IZLERI = ("kapisi", "kapi-", "nobetci", "nobeti", "-test", "test-", "mutasyon")

# Kendisi bu sozlesmenin OLCEN tarafidir; evrende sayilmaz (kurucu kendi kapisina takilir).
KENDI_ADI = "sahipsiz-kapi-nobetcisi.py"


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def sinif_govdeleri(tools_dizini=None):
    """tools/ altindaki kapi/nobetci/test sinifi .py adlari (sirali)."""
    d = tools_dizini or TOOLS
    out = []
    for ad in sorted(os.listdir(d)):
        if not ad.endswith(".py") or ad == KENDI_ADI:
            continue
        if any(iz in ad for iz in SINIF_IZLERI):
            out.append(ad)
    return out


def kosan_atiflar(akis_dizini=None):
    """{dosya_adi: [workflow_dosyasi, ...]} — YORUM satirlari HARIC `run:` ekseninde atif.

    Evren GLOB'dan turer: .github/workflows/*.yml HEPSI. Elle liste yok.
    """
    d = akis_dizini or AKIS_DIZINI
    atif = {}
    if not os.path.isdir(d):
        return atif
    for wf in sorted(os.listdir(d)):
        if not (wf.endswith(".yml") or wf.endswith(".yaml")):
            continue
        for ham in _oku(os.path.join(d, wf)).splitlines():
            satir = ham.strip()
            if satir.startswith("#"):        # YORUM ATFI KOSUM DEGILDIR
                continue
            for ad in re.findall(r"[A-Za-z0-9_.-]+\.py", satir):
                temiz = os.path.basename(ad)
                atif.setdefault(temiz, [])
                if wf not in atif[temiz]:
                    atif[temiz].append(wf)
    return atif


def muaf_adlari(ci_kapsam_yolu=None):
    """ci-kapsam-test.py::IZIN_LISTESI anahtarlari — TEK KAYNAK, ikinci kopya TUTULMAZ.

    AST ile okunur: metin eslemesi yorumlardaki ornekleri de yutardi.
    """
    yol = ci_kapsam_yolu or CI_KAPSAM
    if not os.path.exists(yol):
        return None                          # fail-closed: cagiran OLCULEMEDI basar
    try:
        agac = ast.parse(_oku(yol))
    except SyntaxError:
        return None
    for d in ast.walk(agac):
        if not isinstance(d, ast.Assign):
            continue
        adlar = [t.id for t in d.targets if isinstance(t, ast.Name)]
        if "IZIN_LISTESI" not in adlar or not isinstance(d.value, ast.Dict):
            continue
        out = set()
        for k in d.value.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                out.add(os.path.basename(k.value))
        return out
    return None


YUKLEYICI_CAGRILAR = ("spec_from_file_location", "SourceFileLoader", "import_module",
                      "run_path")


def _cagri_adi(dugum):
    f = dugum.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return None


def _sabitler(dugum):
    return {n.value for n in ast.walk(dugum)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def yukluyor_mu(govde, ad):
    """`govde` (bir .py metni) `ad` modulunu GERCEKTEN yukluyor mu — ADINI ANMAK YETMEZ.

    🔴 K411 (13 Eyl 2026): eski olcut `modul in g or ad in g` idi -> YORUM satirindaki
    "bkz gorsel_mukerrer_kapisi.py" mensiyonu da "import" sayiliyordu; yukleyici satiri
    silinse bile govde YARDIMCI kalirdi (mutant YASARDI). Artik AST ile olculur:
      (i)   `import X` / `from X import ...`
      (ii)  YUKLEYICI_CAGRILAR'dan birinin (spec_from_file_location ...) ARGUMANINDA ad
      (iii) ayni dosyada govdesinde yukleyici cagrisi olan bir SARMALAYICININ
            (ör. `_load("x", "x.py")`) argumaninda ad.
    Ayristirilamayan dosya icin yalniz (i)'nin metin bicimi kullanilir (fail-closed yon:
    daha AZ yardimci -> daha COK sahipsiz).
    """
    modul = ad[:-3]
    nokta = modul.replace("-", "_")
    adaylar = {ad, modul, nokta}
    try:
        agac = ast.parse(govde)
    except (SyntaxError, ValueError):
        return bool(re.search(r"^\s*(import|from)\s+%s\b" % re.escape(nokta), govde, re.M))
    sarmalayicilar = set()
    for d in ast.walk(agac):
        if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(c, ast.Call) and _cagri_adi(c) in YUKLEYICI_CAGRILAR
                   for c in ast.walk(d)):
                sarmalayicilar.add(d.name)
    for d in ast.walk(agac):
        if isinstance(d, ast.Import):
            if any(a.name.split(".")[0] == nokta for a in d.names):
                return True
        elif isinstance(d, ast.ImportFrom):
            if d.module and d.module.split(".")[0] == nokta:
                return True
        elif isinstance(d, ast.Call):
            adi = _cagri_adi(d)
            if adi in YUKLEYICI_CAGRILAR or adi in sarmalayicilar:
                argumanlar = list(d.args) + [k.value for k in d.keywords]
                if any(adaylar & _sabitler(a) for a in argumanlar):
                    return True
                if any(isinstance(s, str) and s.endswith("/" + ad)
                       for a in argumanlar for s in _sabitler(a)):
                    return True
    return False


def yardimci_modul_mu(ad, tools_dizini=None):
    """CLI'si YOK + en az bir baska tools/*.py onu YUKLUYOR -> kutuphane.

    "CI atfi 0" bir modul icin sahipsizlik kaniti DEGILDIR: cagrilan sey modulun
    KENDISI degil, onu yukleyen aractir. Yukleme bicimi `yukluyor_mu` ile AST'ten olculur.
    🔴 CLI'si OLAN govde yuklense de YARDIMCI DEGILDIR (KONTROL-A): 13 Eyl olcumu —
    `gorsel_boyut_kapisi.py` ve `gorsel_mukerrer_kapisi.py` bu yuzden SAHIPSIZ'dedir
    (ikisinde de `if __name__ == "__main__"` var), yukleme bicimi yuzunden DEGIL.
    """
    d = tools_dizini or TOOLS
    yol = os.path.join(d, ad)
    try:
        metin = _oku(yol)
    except OSError:
        return False
    if re.search(r'^if\s+__name__\s*==\s*["\']__main__["\']', metin, re.M):
        return False                          # CLI var -> kutuphane degil
    for baska in sorted(os.listdir(d)):
        if not baska.endswith(".py") or baska == ad:
            continue
        try:
            g = _oku(os.path.join(d, baska))
        except OSError:
            continue
        if yukluyor_mu(g, ad):
            return True
    return False


def denetle(tools_dizini=None, akis_dizini=None, ci_kapsam_yolu=None):
    """(kovalar, olculemedi_sebebi) — kovalar: kosan/muaf/yardimci/SAHIPSIZ."""
    muaf = muaf_adlari(ci_kapsam_yolu)
    if muaf is None:
        return None, ("ci-kapsam-test.py::IZIN_LISTESI OKUNAMADI — muafiyet kaydi "
                      "TEK KAYNAKTIR, onsuz sahipsizlik hukmu verilemez (fail-closed)")
    atif = kosan_atiflar(akis_dizini)
    kovalar = {"kosan": [], "muaf": [], "yardimci": [], "sahipsiz": []}
    for ad in sinif_govdeleri(tools_dizini):
        if atif.get(ad):
            kovalar["kosan"].append((ad, ",".join(atif[ad])))
        elif ad in muaf:
            kovalar["muaf"].append((ad, "IZIN_LISTESI"))
        elif yardimci_modul_mu(ad, tools_dizini):
            kovalar["yardimci"].append((ad, "CLI yok + import ediliyor"))
        else:
            kovalar["sahipsiz"].append((ad, "hicbir is akisinda YOK, gerekce YOK"))
    return kovalar, None


def taban_oku():
    try:
        return int(_oku(TABAN_DOSYASI).strip().splitlines()[0])
    except (OSError, ValueError, IndexError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--envanter", action="store_true", help="tam listeyi kova kova bas")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini_test",
                    help="kapinin kendi iddialarini olc")
    ap.add_argument("--taban-yaz", action="store_true", dest="taban_yaz",
                    help="tabani OLCULEN sayiya cek (yalniz ASAGI)")
    a = ap.parse_args(argv)

    if a.kendini_test:
        import importlib.util
        kt = os.path.join(TOOLS, "sahipsiz-kapi-nobetcisi-test.py")
        if not os.path.exists(kt):
            print("OLCULEMEDI: batarya dosyasi YOK: " + kt)
            return 2
        spec = importlib.util.spec_from_file_location("shk_test", kt)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.kos()

    kovalar, sebep = denetle()
    if kovalar is None:
        print("OLCULEMEDI: " + sebep)
        print("Neyi olcmek kapatir: ci-kapsam-test.py'de IZIN_LISTESI sozlugu AST ile "
              "okunabilir olmali (`python3 -c` YOK; kapi kendi ayristiricisini kullanir).")
        return 2

    n = {k: len(v) for k, v in kovalar.items()}
    toplam = sum(n.values())
    taban = taban_oku()
    print("SAHIPSIZ KAPI NOBETCISI — evren: tools/*.py kapi/nobetci/test sinifi")
    print("  olculen govde   : %d" % toplam)
    print("  (1) KOSAN       : %d  (en az bir .github/workflows/*.yml `run:` satirinda)"
          % n["kosan"])
    print("  (2) MUAF        : %d  (ci-kapsam-test.py::IZIN_LISTESI, gerekceli)" % n["muaf"])
    print("  (3) YARDIMCI    : %d  (CLI yok + baska arac import ediyor)" % n["yardimci"])
    print("  (4) SAHIPSIZ    : %d  (hicbiri — SESSIZ SAHIPSIZLIK)" % n["sahipsiz"])
    print("  is akisi dosyasi: %d (GLOB'dan turedi, elle liste YOK)"
          % len([w for w in sorted(os.listdir(AKIS_DIZINI))
                 if w.endswith((".yml", ".yaml"))]))

    if a.envanter:
        for kova in ("sahipsiz", "yardimci", "muaf", "kosan"):
            print("\n--- %s (%d) ---" % (kova.upper(), n[kova]))
            for ad, nk in kovalar[kova]:
                print("  %-52s %s" % (ad, nk))

    if a.taban_yaz:
        if taban is not None and n["sahipsiz"] > taban:
            print("RED: taban YUKARI cekilemez (%d -> %d). Once borcu kapat."
                  % (taban, n["sahipsiz"]))
            return 1
        with open(TABAN_DOSYASI, "w", encoding="utf-8") as f:
            f.write("%d\n" % n["sahipsiz"])
        print("TABAN YAZILDI: %d" % n["sahipsiz"])
        return 0

    if taban is None:
        print("OLCULEMEDI: taban dosyasi YOK (%s). Ilk kurulumda `--taban-yaz` ile "
              "bugunku sayi cakilir; onsuz ARTIS olculemez." % TABAN_DOSYASI)
        return 2
    if n["sahipsiz"] > taban:
        print("SONUC: KIRMIZI — sahipsiz sayisi TABANI ASTI (%d > %d). "
              "Yeni bir kapi/nobetci hicbir is akisina baglanmadan eklendi."
              % (n["sahipsiz"], taban))
        print("COZUM (uc yoldan BIRI): (a) .github/workflows/ altinda bir `run:` satirina "
              "bagla · (b) ci-kapsam-test.py::IZIN_LISTESI'ne GEREKCESIYLE yaz · (c) SIL.")
        print("DUSEN: " + ", ".join(ad for ad, _ in kovalar["sahipsiz"]))
        return 1
    if n["sahipsiz"] < taban:
        print("SONUC: YESIL ✅ — borc AZALDI (%d < %d). Tabani `--taban-yaz` ile indir."
              % (n["sahipsiz"], taban))
        return 0
    print("SONUC: YESIL ✅ — sahipsiz sayisi taban ile ayni (%d), ARTIS YOK." % taban)
    return 0


if __name__ == "__main__":
    sys.exit(main())

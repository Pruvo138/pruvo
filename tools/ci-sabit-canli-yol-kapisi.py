#!/usr/bin/env python3
"""CI'DA KOSAN BETIKTE SABIT CANLI MAKINE YOLU — KAPI + KENDINI TEST (20 Eyl 2026).

OLCULEN ARIZA (tahmin degil):
  * 19 Eyl, run 35427874787 — `tools/nobet-onarim/cron/t1-kiyas.py` sabit Mac yolu
    tasiyordu; Ubuntu kosucusunda cozulmedi (J5b, `PRUVO_EV_KOKU` ile onarildi).
  * 19 Eyl 22:29Z, run 35473498152 (main `9e1dfecb`) — `tools/kardes-ev-kapisi-test.py`
    modul duzeyinde `REPO = "/Users/okan/dev/pruvo"` tasiyordu. Adim CI'ya 19 Eyl
    `b6720f20` merge'iyle girdi, YEREL Mac'te 19/19 yesildi, GitHub kosucusunda ILK
    zamanlanmis koşumda kirmizi yandi:
        CEVRE: gecici worktree kurulamadi -> fatal: cannot change to
        '/Users/okan/dev/pruvo': No such file or directory
    Adimin yanindaki workflow yorumu "Hermetik + offline ... CI'da kosar" diyordu;
    bu BEYAN hic olculmemisti.

SINIF (iki vaka, tek kok): **CI adimi olarak kaydedilen bir betigin MODUL DUZEYINDE,
duz string sabiti olarak tasidigi `/Users/okan/...` yolu.** Yerelde var, kosucuda yok;
bu yuzden yerel kuru koşum YESIL, CI KIRMIZI olur ([[kabul-kumesi-ci-seritleri]]).

BU KAPININ HUKMU (dar ve olculebilir — genel "/Users/okan gecmesin" yasagi DEGIL):
  Kapsam  : `.github/workflows/*.yml` icindeki `run:` satirlarinda `python3 <yol>.py`
            olarak CAGRILAN, repo icinde VAR OLAN betikler.
  Kirmizi : o betigin MODUL duzeyindeki `AD = "/Users/okan/..."` (ya da f-string'siz
            duz `ast.Constant` str) atamasi.
  Muaf    : (a) deger duz yol degil ANKRAJ metni ise (icinde `=` ya da tirnak var —
                mutasyon capasi; ornek `CAPA_REPO = 'REPO_ONEKI = "..."'`),
            (b) ad ANKRAJ sinifiysa (`CAPA*`, `*_CAPA`, `ANKRAJ*`, `*_ANKRAJ`, `*_CAGRI`),
            (c) atama duz sabit DEGILSE (`os.environ.get(...) or "..."`, `X if
                os.path.isdir(Y) else Z`, tuple/dict/liste, cagri) — bunlar zaten
                CI'da cozulen bir yedek tasir,
            (d) IZIN_LISTESI'nde ADIYLA + GEREKCEYLE yaziliysa (bos gerekce = rc=1).
  Yani kapi "sabit yol yazma" demiyor; "**CI'da kosacaksan yedeksiz sabit yol
  tasiyamazsin**" diyor. Yedek eklemek (env / isdir) ya da adimi CI'dan cikarmak,
  ikisi de kapiyi yesile cevirir — hukum FIILEN olculur.

KULLANIM:
    python3 tools/ci-sabit-canli-yol-kapisi.py              # kapi (rc=0/1)
    python3 tools/ci-sabit-canli-yol-kapisi.py --rapor      # tum bulgular, rc=0
    python3 tools/ci-sabit-canli-yol-kapisi.py --kendini-test  # 9 vaka + 3 mutant + regresyon
Cikis: 0 = temiz, 1 = en az bir yedeksiz sabit yol ya da bos gerekce/bayat izin.
"""
import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANLI_ONEK_ANKRAJ = "/Users/okan/"   # ANKRAJ: taranan ONEK, acilacak yol DEGIL

# `run:` satirindan cagrilan betik. `python3 -m` ve kabuk degiskenli yollar disarida
# kalir (yol cozulemez -> olculemez, sessizce yesil sayilmaz: RAPOR'da gorunur).
CAGRI = re.compile(r"python3\s+((?:tools|olcum|shop|jenerator|onizleme)/[A-Za-z0-9_./-]+\.py)")

ANKRAJ_ADI = re.compile(r"(^CAPA)|(_CAPA$)|(^ANKRAJ)|(_ANKRAJ$)|(_CAGRI$)|(^R_)|(^_R_)")

# ---- IZIN LISTESI (betik -> {ad: GEREKCE}). Bos gerekce = rc=1. ------------
# Buraya bir giris yazmak "olctum, CI'da bu yol COZULMEDEN de adim YESIL bitiyor"
# demektir — BEYAN degil, KOSUM KANITI. Kanit tek bir yerden gelir: adimin AYNI sha
# uzerindeki CI hukmu. Taban olcum (20 Eyl 2026, Tamirci):
#   * nobet.yml   run 35473498152 — main `9e1dfecb`, 19 Eyl 22:29Z. serit-b'de
#     kirmizi olan TEK adim `kardes-ev-kapisi-test.py` (#27); asagidaki diger
#     girislerin adimlari AYNI koşumda success. Yani o dosyalarda sabit yol
#     COZULEMESE de kol `OLCULEMEDI`/atlama ile rc=0 doner.
#   * deploy.yml  run 35469221473 — AYNI sha `9e1dfecb`, success.
# GIRISIN OLUM SARTI: adim ayni sinifla kirmizi yanarsa giris SILINIR ve dosya
# ya yedek alir (env / isdir) ya da adim workflow'dan cikar ([[kabul-kumesi-ci-seritleri]]).
_N = ("OLCULDU nobet.yml run 35473498152 (main 9e1dfecb, 19 Eyl 22:29Z): bu adim "
      "success — sabit canli yol CI'da cozulmese de kol OLCULEMEDI/atlama ile rc=0. ")
_D = ("OLCULDU deploy.yml run 35469221473 (main 9e1dfecb): is akisi success — sabit "
      "kardes-ev yolu CI'da yok, kol kapsam-disi sayip rc=0 doner. ")
# NOT (20 Eyl): ilk taslakta 3 giris daha vardi (`arsiv-kapisi.VARSAYILAN_REPO`,
# `k340-menzil-kabul-test.KANONIK_EV`, `parti-borc-kapisi.EVLER_JSON_VARSAYILAN`).
# BAYAT-IZIN kolu onlari ADIYLA dusurdu: uc dosya da sabitini modulun KENDI yedegiyle
# (`... or SABIT`) kullaniyor, yani muafiyet GEREKMIYOR. Kayit disi birakildilar.
IZIN_LISTESI = {
    "tools/boy-secenekleri-kabul.py": {
        "EDGE_WORKER": _D + "Kardes ev (pruvo-bot) worker dosyasi; yoksa o eksen "
                            "olculemez sayilir."},
    "tools/ege-uretim-sahipligi-test.py": {
        "BOT_INDEX": _D + "Ayni kardes-ev dosyasi; CI'da eksen OLCULEMEDI."},
    "tools/ev-haritasi-kapisi-test.py": {
        "CANLI_KONFIG": _N + "Canli cron duzlemi (`~/.claude/cron`) CI'da YOK; kapi "
                             "bunu ADIYLA olculemedi basar.",
        "CANLI_NOT": _N + "Ayni canli cron duzlemi.",
        "FAR_DEPO_KOKU": _N + "Kardes depo koku yalniz canli filoda olculur.",
        "KRAL_DEPO_KOKU": _N + "Kardes depo koku yalniz canli filoda olculur."},
    "tools/gh-civi-nobetcisi.py": {
        "REPO_KOK": _N + "Nobetci canli checkout'u gozler; CI kolunda yalniz mekanizma "
                         "olculur."},
    "tools/gorselsiz-kayit-kabul.py": {
        "ANA_KAPI": _N + "ANA checkout'taki kapi kopyasi bayatlik kiyasi icindir; CI'da "
                         "kiyas yapilamaz, kol olculemedi der."},
    "tools/id-rename-test.py": {
        "HEDEF": _N + "Canli `index.html` yolu; CI'da fikstur uzerinden olculur."},
    "tools/mimar-commit-kapisi-test.py": {
        "MAIN": _N + "ANA checkout kiyas ekseni; CI'da kum dizininde kosar."},
    "tools/nobet-sayac-durustluk-test.py": {
        "URETIM_YOLU": _N + "Canli `~/.claude/cron` kopyasi; CI'da repo kopyasi olculur."},
    "tools/parti-kapisi.py": {
        "SARMALAYICI_DIZINI": _N + "Canli cron sarmalayici dizini; CI'da yok, kol atlar.",
        "PROJE_ONEKI": _N + "Canli transcript oneki; CI'da damga uretilemez, kol atlar."},
    "tools/tikayici-kaldirma-test.py": {
        "ANA_DAMGA": _N + "Canli oturum damgasi; CI'da kum damgasi kullanilir.",
        "ANA_CHECKOUT": _N + "ANA checkout kiyas ekseni; CI'da kum kokune duser."},
}


def ci_betikleri(kok):
    """{goreli betik yolu: [onu cagiran workflow dosyalari]} — repoda VAR OLANLAR."""
    wf = os.path.join(kok, ".github", "workflows")
    bulunan = {}
    if not os.path.isdir(wf):
        return bulunan
    for ad in sorted(os.listdir(wf)):
        if not (ad.endswith(".yml") or ad.endswith(".yaml")):
            continue
        with open(os.path.join(wf, ad), encoding="utf-8") as f:
            for esleme in CAGRI.finditer(f.read()):
                goreli = esleme.group(1)
                if os.path.isfile(os.path.join(kok, goreli)):
                    bulunan.setdefault(goreli, [])
                    if ad not in bulunan[goreli]:
                        bulunan[goreli].append(ad)
    return bulunan


GUARD_CAGRILARI = ("isdir", "isfile", "exists", "lexists")


def korunan_adlar(agac):
    """Modulun KENDI yedegini kurdugu adlar.

    Iki bicim sayilir (ikisi de CI'da cozulen bir yedek verir):
      * `K = C if os.path.isdir(C) else <baska>`   -> C KORUNUR
      * `K = os.environ.get("X") or C`             -> C KORUNUR (BoolOp icinde)
    Bu yuzden `CANLI_KOK = "/Users/okan/dev/pruvo"` gibi TEK KAYNAK isaretleri,
    hemen ardindan dusen bir yedek varsa KIRMIZI yanmaz (emsal: kapi_dagitim.py)."""
    korunan = set()
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.IfExp) and isinstance(dugum.test, ast.Call):
            cagri = dugum.test.func
            adi = cagri.attr if isinstance(cagri, ast.Attribute) else getattr(
                cagri, "id", "")
            if adi in GUARD_CAGRILARI:
                for alt in ast.walk(dugum.test):
                    if isinstance(alt, ast.Name):
                        korunan.add(alt.id)
        elif isinstance(dugum, ast.BoolOp):
            for deger in dugum.values:
                if isinstance(deger, ast.Name):
                    korunan.add(deger.id)
    return korunan


def sabit_yollar(kaynak_metni):
    """MODUL duzeyinde `AD = "<CANLI_ONEK_ANKRAJ>..."` duz sabit atamalari: [(ad, deger, satir)].

    AST ile okunur; yorum ve docstring icindeki ayni metin SAYILMAZ (yanlis pozitif yok).
    Tuple/dict/cagri/BoolOp/IfExp degerleri de sayilmaz: onlar yedek tasiyan biciml
    erdir (`os.environ.get(...) or ...`, `X if os.path.isdir(...) else Y`)."""
    try:
        agac = ast.parse(kaynak_metni)
    except SyntaxError as hata:
        return [("<AYRISTIRILAMADI>", str(hata), 0)]
    korunan = korunan_adlar(agac)
    bulgular = []
    for dugum in agac.body:                       # YALNIZ modul duzeyi
        hedefler = []
        if isinstance(dugum, ast.Assign):
            hedefler = [h for h in dugum.targets if isinstance(h, ast.Name)]
        elif isinstance(dugum, ast.AnnAssign) and isinstance(dugum.target, ast.Name):
            hedefler = [dugum.target]
        if not hedefler:
            continue
        deger = dugum.value
        if not (isinstance(deger, ast.Constant) and isinstance(deger.value, str)):
            continue                              # yedekli bicim -> muaf (c)
        if not deger.value.startswith(CANLI_ONEK_ANKRAJ):
            continue
        if ('"' in deger.value) or ("'" in deger.value) or ("=" in deger.value):
            continue                              # ANKRAJ metni -> muaf (a)
        for hedef in hedefler:
            if ANKRAJ_ADI.search(hedef.id):
                continue                          # ANKRAJ adi -> muaf (b)
            if hedef.id in korunan:
                continue                          # modul kendi yedegini kuruyor -> muaf (c)
            bulgular.append((hedef.id, deger.value, dugum.lineno))
    return bulgular


def tara(kok):
    """[(betik, ad, deger, satir, hal, workflowlar)] — hal ∈ {KIRMIZI, IZINLI, BOS-GEREKCE}."""
    sonuc = []
    for goreli, workflowlar in sorted(ci_betikleri(kok).items()):
        with open(os.path.join(kok, goreli), encoding="utf-8") as f:
            metin = f.read()
        for ad, deger, satir in sabit_yollar(metin):
            gerekce = (IZIN_LISTESI.get(goreli) or {}).get(ad)
            if gerekce is None:
                hal = "KIRMIZI"
            elif not gerekce.strip():
                hal = "BOS-GEREKCE"
            else:
                hal = "IZINLI"
            sonuc.append((goreli, ad, deger, satir, hal, ",".join(workflowlar)))
    return sonuc


def bayat_izinler(kok, bulgular):
    """IZIN_LISTESI'nde olup ARTIK olculmeyen girisler (bayat muafiyet sessizce yasamaz)."""
    canli = {(b[0], b[1]) for b in bulgular}
    return sorted({(dosya, ad) for dosya, adlar in IZIN_LISTESI.items()
                   for ad in adlar if (dosya, ad) not in canli})


def kapi(kok, rapor=False):
    bulgular = tara(kok)
    kirmizi = [b for b in bulgular if b[4] in ("KIRMIZI", "BOS-GEREKCE")]
    # BAYAT-IZIN yalniz KENDI repo kokunde anlamlidir: kum/fikstur kokunde listedeki
    # dosyalar zaten yoktur, orada bayatlik hukmu verilmez (yanlis kirmizi uretmez).
    bayat = bayat_izinler(kok, bulgular) if os.path.abspath(kok) == KOK else []
    print("CI SABIT CANLI YOL KAPISI — kok=%s" % kok)
    print("  CI adimindan cagrilan betik: %d" % len(ci_betikleri(kok)))
    for goreli, ad, deger, satir, hal, wf in bulgular:
        if hal == "IZINLI" and not rapor:
            continue
        print("  %-11s %s:%d  %s = %r   [%s]" % (hal, goreli, satir, ad, deger, wf))
        if hal == "KIRMIZI":
            print("              -> CI kosucusunda bu yol YOKTUR. Yedek ekle "
                  "(`os.environ.get(...) or ...` / `... if os.path.isdir(...) else ...`) "
                  "ya da adimi workflow'dan cikar; kacamak: IZIN_LISTESI + GEREKCE.")
    for dosya, ad in bayat:
        print("  BAYAT-IZIN  %s:%s — artik olculmuyor, IZIN_LISTESI'nden SIL" % (dosya, ad))
    print("OZET: kirmizi=%d izinli=%d bayat-izin=%d"
          % (len(kirmizi), len(bulgular) - len(kirmizi), len(bayat)))
    if rapor:
        return 0
    return 1 if (kirmizi or bayat) else 0


# ======================= KENDINI TEST (vaka + mutant) =======================
FIKSTUR_KIRMIZI = 'import os\nREPO = "/Users/okan/dev/pruvo"\n'
FIKSTUR_ENV = ('import os\nREPO = os.environ.get("PRUVO_EV_KOKU") or '
               '"/Users/okan/dev/pruvo"\n')
FIKSTUR_ISDIR = ('import os\nC = "/Users/okan/dev/pruvo"\n'
                 'K = C if os.path.isdir(C) else os.path.dirname(__file__)\n')
FIKSTUR_ANKRAJ = 'CAPA_REPO = \'REPO_ONEKI = "/Users/okan/dev/pruvo/"\'\n'
# Yalniz AD ekseni: deger duz yol, ad ANKRAJ sinifi -> (b) kolu TEK BASINA tasir.
FIKSTUR_ANKRAJ_ADI = 'CAPA_KOK = "/Users/okan/dev/pruvo"\n'
FIKSTUR_TUPLE = 'EVLER = (("MaCiT", "/Users/okan/dev/pruvo-hasat"),)\n'
FIKSTUR_ICERIDE = ('def f():\n    yol = "/Users/okan/dev/pruvo"\n    return yol\n')
FIKSTUR_YORUM = '# REPO = "/Users/okan/dev/pruvo"\n"""REPO = /Users/okan/dev/pruvo"""\n'
FIKSTUR_TEMIZ = 'import os\nREPO = os.path.dirname(os.path.abspath(__file__))\n'

VAKALAR = [
    ("V1 duz sabit atama KIRMIZI yanar", FIKSTUR_KIRMIZI, 1),
    ("V2 `env.get(...) or ...` yedegi MUAF", FIKSTUR_ENV, 0),
    ("V3 `isdir()` yedegi MUAF", FIKSTUR_ISDIR, 0),
    ("V4 ANKRAJ metni (icinde tirnak+=) MUAF", FIKSTUR_ANKRAJ, 0),
    ("V4b ANKRAJ ADI (CAPA_*) duz yolda da MUAF", FIKSTUR_ANKRAJ_ADI, 0),
    ("V5 tuple/tablo girisi MUAF", FIKSTUR_TUPLE, 0),
    ("V6 fonksiyon ICI yerel atama MUAF (modul duzeyi degil)", FIKSTUR_ICERIDE, 0),
    ("V7 yorum + docstring MUAF (AST okur, metin degil)", FIKSTUR_YORUM, 0),
    ("V8 KONTROL: yol tasimayan betik temiz", FIKSTUR_TEMIZ, 0),
]


def _kum(dizin, betik_metni, wf_satiri="python3 tools/ornek.py"):
    os.makedirs(os.path.join(dizin, "tools"), exist_ok=True)
    os.makedirs(os.path.join(dizin, ".github", "workflows"), exist_ok=True)
    with open(os.path.join(dizin, "tools", "ornek.py"), "w", encoding="utf-8") as f:
        f.write(betik_metni)
    with open(os.path.join(dizin, ".github", "workflows", "x.yml"),
              "w", encoding="utf-8") as f:
        f.write("jobs:\n  a:\n    steps:\n      - run: %s\n" % wf_satiri)
    return dizin


def kendini_test():
    gecti = dusen = 0
    print("CI SABIT CANLI YOL KAPISI — KENDINI TEST")
    for ad, metin, beklenen in VAKALAR:
        with tempfile.TemporaryDirectory(prefix="ci-sabit-yol-") as d:
            olculen = len([b for b in tara(_kum(d, metin)) if b[4] != "IZINLI"])
        iyi = (olculen > 0) == (beklenen > 0)
        gecti, dusen = (gecti + iyi, dusen + (not iyi))
        print("  %s %-58s olculen=%d beklenen=%s" %
              ("✅" if iyi else "🔴", ad, olculen, "KIRMIZI" if beklenen else "temiz"))

    # --- MUTANT: kapinin KENDI muafiyet kollari oldurulur (kopya uzerinde) ---
    # Her ankraj TAM BIR KEZ eslesmeli; eslesmezse mutant KOSULMAZ ve sebep ADIYLA
    # doner (bayat ankraj sessizce yesillenmez).
    # Ankrajlar PARCALI yazilir: boylece ankrajin kendisi bu tabloda ikinci kez
    # GORUNMEZ ve `count(...) != 1` yanlis "BAYAT ANKRAJ" uretmez.
    mutantlar = [
        ("M1 `agac.body` -> `ast.walk` (modul-duzeyi kolu olur)",
         "for dugum in agac.b" + "ody:", "for dugum in ast.walk(agac):",
         FIKSTUR_ICERIDE),
        ("M2 ANKRAJ-adi muafiyeti olur",
         "if ANKRAJ_ADI.sea" + "rch(hedef.id):",
         "if False and ANKRAJ_ADI.search(hedef.id):", FIKSTUR_ANKRAJ_ADI),
        ("M3 modulun kendi yedegi (isdir/BoolOp) muafiyeti olur",
         "if hedef.id in koru" + "nan:",
         "if False and hedef.id in korunan:", FIKSTUR_ISDIR),
    ]
    kaynak = open(os.path.abspath(__file__), encoding="utf-8").read()
    for ad, eski, yeni, fikstur in mutantlar:
        if kaynak.count(eski) != 1:
            print("  🔴 %-58s BAYAT ANKRAJ (%d vurus)" % (ad, kaynak.count(eski)))
            dusen += 1
            continue
        with tempfile.TemporaryDirectory(prefix="ci-sabit-yol-m-") as d:
            mutant = os.path.join(d, "mutant.py")
            with open(mutant, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
            kum = _kum(os.path.join(d, "kum"), fikstur)
            temiz_kum = _kum(os.path.join(d, "temiz"), FIKSTUR_TEMIZ)
            taban = subprocess.run([sys.executable, mutant, "--kok", kum],
                                   capture_output=True, text=True)
            mutant_rc = taban.returncode
            gurultu = subprocess.run([sys.executable, mutant, "--kok", temiz_kum],
                                     capture_output=True, text=True).returncode
            asil = subprocess.run([sys.executable, os.path.abspath(__file__),
                                   "--kok", kum], capture_output=True, text=True)
        # Kol YUK TASIYOR ise: kapi bu fiksturde SESSIZ (rc=0), mutant KIRMIZI (rc=1),
        # ve mutant temiz betikte gurultu URETMEZ (rc=0).
        iyi = (asil.returncode == 0 and mutant_rc == 1 and gurultu == 0)
        gecti, dusen = (gecti + iyi, dusen + (not iyi))
        print("  %s %-58s kapi=%d mutant=%d gurultu=%d" %
              ("✅" if iyi else "🔴", ad, asil.returncode, mutant_rc, gurultu))

    # --- CAPRAZ: gercek repoda ARIZANIN KENDISI yakalanir mi (regresyon capasi) ---
    with tempfile.TemporaryDirectory(prefix="ci-sabit-yol-r-") as d:
        _kum(d, FIKSTUR_KIRMIZI, "python3 tools/ornek.py")
        yakalandi = any(b[4] == "KIRMIZI" for b in tara(d))
    iyi = yakalandi
    gecti, dusen = (gecti + iyi, dusen + (not iyi))
    print("  %s %-58s yakalandi=%s" %
          ("✅" if iyi else "🔴",
           "R1 19 Eyl arizasinin BIREBIR bicimi (REPO = <mac yolu>)", yakalandi))

    print("VAKA=%d GECTI=%d DUSTU=%d" % (gecti + dusen, gecti, dusen))
    return 1 if dusen else 0


def main():
    ayristirici = argparse.ArgumentParser()
    ayristirici.add_argument("--rapor", action="store_true",
                             help="tum bulgular + izinliler, rc=0")
    ayristirici.add_argument("--kendini-test", action="store_true")
    ayristirici.add_argument("--kok", default=KOK)
    arg = ayristirici.parse_args()
    if arg.kendini_test:
        return kendini_test()
    return kapi(arg.kok, rapor=arg.rapor)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL + MUTASYON SURUCUSU — yedekle.py'nin ZAMANLANMIS GOREV kapsami ve DISLAMASI.

NEDEN VAR (olculdu, 7 Agu 2026): ~/.claude/scheduled-tasks agaci yedekle.py'nin
kapsaminda HIC GECMIYORDU -> 15 zamanlanmis gorevin TANIM METNI diskte TEK KOPYA,
surum gecmisi YOK. Bu makinede 2-3 gunde bir hesap rotasyonu var; gorev KAYDI zaten
hesapla oluyor, METIN de yedeksizse gorev KALICI olarak kayboluyor.

Agac kapsama alinirken IKINCI bir risk dogar: kardes dizin ~/.claude/cron altinda
GERCEK `.ci-token` / `.gh-token` duruyor ve yedek hedefi ORTAK Drive. Yani bu is bir
JETON YUZEYINE KOMSU. Bu yuzden iki ayri iddia var ve IKISI DE tek tek olculur:
  (A) KAPSAM     — gorev metinleri yedege GIRIYOR (bayt bayt).
  (B) DISLAMA    — sir/izinsiz dosya yedege GIRMIYOR, SEBEBIYLE SAYILIYOR.

🔴 KATMANLAR TEK TEK OLCULUR (beyan edilmis survivor tuzagi): "jeton yedekte yok"
iddiasi katmanlarin VEYA'sidir — sir nobeti kapatilsa bile allowlist ayni dosyayi
elerdi ve iddia YESIL kalirdi. Bu yuzden fikstur AYIRT EDICI kurulur:
  * izinli uzantili ama JETON ADLI dosya   -> YALNIZ sir nobeti eler   (G4)
  * izinli uzantili ama IMZALI icerik      -> YALNIZ sir nobeti eler   (G5)
  * zararsiz adli/icerikli IZINSIZ uzanti  -> YALNIZ allowlist eler    (G6)
G11 (uctan uca "jeton hedefte yok") BILEREK bir survivor'dur ve katman kaniti
SAYILMAZ; kabul metninin istedigi uctan uca olcum olarak ayrica tutulur.

🔴 BYTECODE ONBELLEK TUZAGI ELE ALINDI: ayni uzunlukta mutasyon ayni saniyede
yazilinca .pyc onbellegi yuzunden UYGULANMAYABILIR (mutant kirmizi yanar ama dusen
bir oncekinin iddiasidir). Uc onlem birden:
  1. PYTHONDONTWRITEBYTECODE=1 + sys.dont_write_bytecode -> onbellek HIC yazilmaz.
  2. Her mutant AYRI tempdir + AYRI dosya adi.
  3. POZITIF KANIT: mutant diskten GERI OKUNUR; capa metni gitmis, yerine konan
     metin gelmis ve sha256 tabandan farkli olmali. Degilse SURUCU PATLAR.
  4. Kosum sonrasi kum havuzunda __pycache__ OLUSMADIGI ayrica olculur.

⚠️ GERCEK HEDEFE / GERCEK HOME'a YAZMAZ: her sey sahte HOME + sahte git deposu +
drive_yolu STUB'u ile izole tempdir'de kosar.
⚠️ FIKSTURLERDEKI "SIR"LAR TAMAMEN UYDURMA: gercek jeton OKUNMAZ, KOPYALANMAZ.

Kosum:  python3 tools/yedek-gorev-kapsam-mutasyon.py
Cikis:  0 = HUKUM HAZIR, 1 = kirmizi.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
YEDEKLE = os.path.join(TOOLS, "yedekle.py")
DRIVE_YOLU = os.path.join(TOOLS, "drive_yolu.py")

# ---------------------------------------------------------------- fikstur ----
# GERCEK ANAHTAR DEGIL. Dize PARCALI kurulur: hicbir KAYNAK SATIRI jeton desenine
# uymaz (repo geneli sir tarayicilarini bosuna kirmizi yakmasin), CALISMA ANINDAKI
# dize ise yedekle.SIR_IMZALARI "GitHub jetonu" imzasini BIREBIR tetikler.
SAHTE_IMZA = "gh" + "p_" + ("S" * 36)

GOREV_DIZIN = "scheduled-tasks"

# (gorece yol, icerik) — ALLOWLIST'ten ve sir nobetinden GECMESI beklenenler.
#
# 🔴 SAYI BILEREK 6 (FIKSTUR DEGERI MUTASYONU KOR ETMESIN): ilk kurulumda 5 idi ve
# "sayaci sabitle" mutanti (`return 5, yeni`) fikstur degeriyle CAKISTIGI icin SAG
# KALDI — sayac yalan soylerken batarya yesil yandi. Fikstur adedi artik yedekle.py
# icinde gecen hicbir sabitle cakismiyor.
BEKLENEN_IZINLI = (
    ("gorev-a/SKILL.md", "# gorev a\nsaat basi kosar\n"),
    ("gorev-b/SKILL.md", "# gorev b\ngunluk kosar\n"),
    ("gorev-c/SKILL.md", "# gorev c\nhaftalik kosar\n"),
    ("gorev-a/olcum.json", '{"esik": 3, "birim": "saat"}\n'),
    ("gorev-c/olcum-2.json", '{"esik": 11, "birim": "gun"}\n'),
    ("gorev-a/notlar.txt", "elle yazilmis nobet notu\n"),
)

# (gorece yol, icerik, beklenen katman) — yedege GIRMEMESI gerekenler.
#   katman "sir"       -> YALNIZ sir nobeti eler (uzantisi IZINLI)
#   katman "allowlist" -> YALNIZ allowlist eler (adi/icerigi ZARARSIZ)
#   katman "ikisi"     -> gercek jetonun sekli; uctan uca olcum (G11)
BEKLENEN_HARIC = (
    ("gorev-b/gizli-token.md", "sahte govde, gercek jeton DEGIL\n", "sir"),
    ("gorev-b/imza-notu.md", "not\n" + SAHTE_IMZA + "\n", "sir"),
    ("gorev-c/artik.bin", "duz metin, zararsiz ad, IZINSIZ uzanti\n", "allowlist"),
    (".gh-token", "SENTETIK-SAHTE-JETON-GERCEK-DEGIL\n", "ikisi"),
)

SENTETIK_JETON = ".gh-token"

TABAN_IDDIALAR = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10",
                  "G11", "G12")

IDDIA_METNI = {
    "G1": "plan-kapsami: izinli gorev dosyalarinin TAMAMI yedek planinda",
    "G2": "bayt-bayt: her izinli dosya hedefte kaynakla BIREBIR ayni",
    "G3": "damga-sayaci: damga['gorev'] == fikstur adedi (sabit degil, gercek kopya sayisi)",
    "G4": "katman-1a: jeton ADLI ama IZINLI uzantili dosyayi SIR NOBETI eledi",
    "G5": "katman-1b: IMZALI icerikli ama IZINLI uzantili dosyayi SIR NOBETI eledi",
    "G6": "katman-2: zararsiz ama IZINSIZ uzantili dosyayi ALLOWLIST eledi",
    "G7": "dislama-sayaci: damga['gorev_haric'] == 4 VE stdout'ta 4 'DISLANDI:' satiri",
    "G8": "mesru-yutulmadi: izinli dosyalarin HEPSI hedefte (allowlist fazla genis degil)",
    "G9": "imza-plan-hizasi: kaynak_imzasi['adet'] == len(yedek_plani)",
    "G10": "dogrula-yesil: --dogrula cikis kodu 0 (plandaki her dosya hedefte)",
    "G11": "uctan-uca: sentetik sahte jeton hedefte HICBIR YERDE yok (survivor, katman kaniti DEGIL)",
    "G12": "idempotent-sayac: 1. kosum yeni==N, 2. kosum yeni==0 ve gorev YINE N",
}

PYC_SAYAC = []          # her batarya kosumunda olusan __pycache__ girisi sayisi

OLCUM_KODU = (
    "import sys;sys.dont_write_bytecode=True\n"
    "import importlib.util,json\n"
    "spec=importlib.util.spec_from_file_location('y', %r)\n"
    "m=importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(m)\n"
    "plan=m.yedek_plani()\n"
    "gp=m.gorev_plani()\n"
    "print(json.dumps({'plan_hedefleri':[h for _k,h in plan],'plan_adet':len(plan),"
    "'dahil':gp[0],'haric':gp[1],'gurultu':gp[2],'imza':m.kaynak_imzasi(),"
    "'gorev_klasor':m.GOREV_KLASOR,'gorevler':m.GOREVLER}))\n"
)


def _yaz(yol, icerik):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)


def kum_havuzu(td, kaynak_betik):
    """Sahte HOME + sahte git deposu + drive_yolu STUB'u. Gercege DOKUNMAZ."""
    kok = os.path.join(td, "repo")
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(kaynak_betik, os.path.join(kok, "tools", "yedekle.py"))
    pruvo = os.path.join(td, "drive", "Pruvo")
    os.makedirs(pruvo)
    _yaz(os.path.join(kok, "tools", "drive_yolu.py"),
         'DESEN = "/olmayan-mount/*/STL"\n'
         'CFG = "/olmayan-mount/.stl-backup-dir"\n'
         'def stl_dizini(sessiz=False):\n    return %r\n'
         'def pruvo_dizini(sessiz=False):\n    return %r\n'
         % (os.path.join(pruvo, "STL"), pruvo))
    subprocess.run(["git", "-C", kok, "init", "-q"], capture_output=True)

    # yedekle.REPO_BEKLENEN'i kaynaktan OKU (fikstur bayatlamasin).
    beklenen = ()
    with open(kaynak_betik, encoding="utf-8") as f:
        for satir in f:
            if satir.startswith("REPO_BEKLENEN = ("):
                beklenen = tuple(p.strip().strip('",') for p in
                                 satir.split("(", 1)[1].split(")")[0].split(",")
                                 if p.strip())
                break
    for ad in beklenen:
        _yaz(os.path.join(kok, ad), "izole test icerigi: %s\n" % ad)

    ev = os.path.join(td, "ev")
    mem = os.path.join(ev, ".claude", "projects", "-Users-okan-dev-pruvo", "memory")
    for i in range(5):
        _yaz(os.path.join(mem, "not-%02d.md" % i), "hafiza %d\n" % i)
    _yaz(os.path.join(ev, ".claude", "skills", "ornek", "SKILL.md"), "skill\n")

    gorev_kok = os.path.join(ev, ".claude", GOREV_DIZIN)
    for gor, icerik in BEKLENEN_IZINLI:
        _yaz(os.path.join(gorev_kok, gor), icerik)
    for gor, icerik, _katman in BEKLENEN_HARIC:
        _yaz(os.path.join(gorev_kok, gor), icerik)

    ortam = dict(os.environ)
    ortam["HOME"] = ev
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"      # bytecode onbellek tuzagi (onlem 1)
    return {"kok": kok, "betik": os.path.join(kok, "tools", "yedekle.py"),
            "ev": ev, "gorev_kok": gorev_kok, "hedef": os.path.join(pruvo, "backup"),
            "ortam": ortam}


def kos(o, *bayraklar):
    return subprocess.run([sys.executable, o["betik"]] + list(bayraklar),
                          capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])


def olc(o):
    r = subprocess.run([sys.executable, "-c", OLCUM_KODU % o["betik"]],
                       capture_output=True, text=True, env=o["ortam"], cwd=o["kok"])
    try:
        return json.loads(r.stdout.strip())
    except ValueError:
        return {"_hata": (r.stdout + r.stderr)[-400:]}


def _damga(hedef):
    try:
        with open(os.path.join(hedef, ".son-yedek.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def hedef_dosyalari(hedef):
    if not os.path.isdir(hedef):
        return []
    return sorted(os.path.relpath(os.path.join(d, a), hedef)
                  for d, _alt, adlar in os.walk(hedef) for a in adlar)


# ------------------------------------------------------------------ batarya --
def bataryayi_kos(kaynak_betik, atla=None):
    """Adlandirilmis iddialari kosar. Doner: (sonuc dict, notlar list).

    `atla`: bir iddia kimligi -> O IDDIA HIC KOSMAZ (iddia-atlama mutantinin
    kolu). Sonuc sozlugunde YER ALMAZ; hukum bunu 'IDDIA-EKSIK' sayar."""
    sonuc, notlar = {}, []

    def iddia(kimlik, ok, ayrinti=""):
        if atla == kimlik:
            return
        sonuc[kimlik] = bool(ok)
        if not ok and ayrinti:
            notlar.append("%s: %s" % (kimlik, ayrinti))

    td = tempfile.mkdtemp(prefix="gorev-kapsam-")
    try:
        o = kum_havuzu(td, kaynak_betik)
        r = kos(o)
        damga1 = _damga(o["hedef"])
        # IKINCI KOSUM — idempotens ekseni: hicbir kaynak degismedi, dolayisiyla
        # "yeni" 0 olmali ama "gorev" (hedefte duran dosya) AYNI kalmali. Bu eksen
        # olmadan "sayaci sabitle" sinifindaki mutantlar tek bir sayiya bakan
        # iddiayla ayirt edilemiyor (fikstur degeri sabitle CAKISABILIYOR).
        r = kos(o)
        m = olc(o)
        hedef = o["hedef"]
        gk = m.get("gorev_klasor", "gorev-tanimlari")
        hedefte = set(hedef_dosyalari(hedef))
        haric_sozluk = dict(tuple(x) for x in m.get("haric", []))
        plan_hedefleri = set(m.get("plan_hedefleri", []))

        # G1 — plan kapsami
        eksik_plan = [g for g, _i in BEKLENEN_IZINLI
                      if os.path.join(gk, g) not in plan_hedefleri]
        iddia("G1", not eksik_plan, "planda yok: %s" % eksik_plan)

        # G2 — bayt bayt
        bozuk = []
        for g, _i in BEKLENEN_IZINLI:
            try:
                with open(os.path.join(o["gorev_kok"], g), "rb") as f:
                    a = f.read()
                with open(os.path.join(hedef, gk, g), "rb") as f:
                    b = f.read()
            except OSError:
                bozuk.append(g + " (hedefte YOK)")
                continue
            if a != b:
                bozuk.append(g + " (bayt farki)")
        iddia("G2", not bozuk, "; ".join(bozuk))

        # G3 — damga sayaci (BEKLENEN SABIT SAYI ile; kendi kendine tutarlilik DEGIL)
        damga = _damga(hedef)
        iddia("G3", damga.get("gorev") == len(BEKLENEN_IZINLI),
              "damga['gorev']=%r beklenen %d" % (damga.get("gorev"), len(BEKLENEN_IZINLI)))

        # G4/G5/G6 — KATMAN KATMAN. Sebep metni hangi katmandan geldigini soylemeli.
        def katman(gor):
            sebep = haric_sozluk.get(gor)
            if sebep is None:
                return "ELENMEDI"
            return "allowlist" if sebep.startswith("allowlist disi") else "sir"

        iddia("G4", katman("gorev-b/gizli-token.md") == "sir"
              and os.path.join(gk, "gorev-b/gizli-token.md") not in hedefte,
              "katman=%s" % katman("gorev-b/gizli-token.md"))
        s5 = haric_sozluk.get("gorev-b/imza-notu.md", "")
        iddia("G5", s5.startswith("icerik imzasi")
              and os.path.join(gk, "gorev-b/imza-notu.md") not in hedefte,
              "sebep=%r" % s5)
        iddia("G6", katman("gorev-c/artik.bin") == "allowlist"
              and os.path.join(gk, "gorev-c/artik.bin") not in hedefte,
              "katman=%s" % katman("gorev-c/artik.bin"))

        # G7 — dislama SAYISI hem damgada hem STDOUT'ta, BEKLENEN sabit sayiyla
        stdout_dislanan = sum(1 for s in r.stdout.splitlines() if "DISLANDI:" in s)
        iddia("G7", damga.get("gorev_haric") == len(BEKLENEN_HARIC)
              and stdout_dislanan == len(BEKLENEN_HARIC),
              "damga=%r stdout=%d beklenen=%d"
              % (damga.get("gorev_haric"), stdout_dislanan, len(BEKLENEN_HARIC)))

        # G8 — mesru dosya yutulmadi (allowlist FAZLA GENIS degil)
        yutulan = [g for g, _i in BEKLENEN_IZINLI if os.path.join(gk, g) not in hedefte]
        iddia("G8", not yutulan, "hedefte yok: %s" % yutulan)

        # G9 — imza ile plan AYNI kumeden turer (ayrisma nobetcisi)
        imza = m.get("imza") or {}
        iddia("G9", imza.get("adet") == m.get("plan_adet"),
              "imza=%r plan=%r" % (imza.get("adet"), m.get("plan_adet")))

        # G10 — --dogrula yesil
        rd = kos(o, "--dogrula")
        iddia("G10", rd.returncode == 0, "rc=%d %s" % (rd.returncode, rd.stdout[-200:]))

        # G11 — UCTAN UCA (BILEREK SURVIVOR; katman kaniti sayilmaz)
        jeton_izi = [y for y in hedefte if SENTETIK_JETON in os.path.basename(y)]
        iddia("G11", not jeton_izi, "hedefte iz: %s" % jeton_izi)

        # G12 — IDEMPOTENS: 1. kosumda hepsi YENI, 2. kosumda HICBIRI yeni degil ama
        # hedefte duran sayi AYNI. Sayacin GERCEGI izledigini tek sayidan daha guclu
        # olcer (sabitlenmis sayac ikinci kosumda ele verir).
        n = len(BEKLENEN_IZINLI)
        iddia("G12", damga1.get("gorev_yeni") == n and damga.get("gorev_yeni") == 0
              and damga.get("gorev") == n,
              "1.kosum yeni=%r  2.kosum yeni=%r gorev=%r  beklenen %d/0/%d"
              % (damga1.get("gorev_yeni"), damga.get("gorev_yeni"),
                 damga.get("gorev"), n, n))

        # bytecode onbellek onlemi 4 — kum havuzunda .pyc birikmedi (POZITIF OLCUM)
        pyc = [y for y in hedef_dosyalari(o["kok"]) if "__pycache__" in y]
        PYC_SAYAC.append(len(pyc))
        if pyc:
            notlar.append("UYARI: kum havuzunda __pycache__ olustu: %s" % pyc[:3])
        return sonuc, notlar
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ----------------------------------------------------------------- mutantlar --
def mutant_uret(td, ad, degisimler, taban_sha):
    """Mutant kaynagi uretir ve UYGULANDIGINI POZITIF olarak kanitlar."""
    with open(YEDEKLE, encoding="utf-8") as f:
        kaynak = f.read()
    for eski, yeni in degisimler:
        if eski not in kaynak:
            raise RuntimeError("MUTASYON CAPASI BULUNAMADI (yedekle.py degismis): %r" % eski)
        kaynak = kaynak.replace(eski, yeni, 1)
    yol = os.path.join(td, ad)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak)
    with open(yol, encoding="utf-8") as f:               # DISKTEN GERI OKU
        geri = f.read()
    sha = hashlib.sha256(geri.encode("utf-8")).hexdigest()
    if sha == taban_sha:
        raise RuntimeError("MUTASYON UYGULANMADI (sha tabana esit): " + ad)
    for eski, yeni in degisimler:
        if eski in geri and yeni not in geri:
            raise RuntimeError("MUTASYON DISKTE YOK: " + ad)
    return yol


MUTANTLAR = (
    # ---- OLDURUCU olmasi beklenenler ----
    ("M1-sir-katmani-noop", "oldurucu", (
        ("            sebep = sir_sebebi(tam, ad)                 # KATMAN 1 — sir nobeti",
         "            sebep = None  # MUTANT: sir nobeti devre disi"),)),
    ("M2a-plandan-cikar", "oldurucu", (
        ("    for gor in gorev_plani()[0]:\n"
         "        plan.append((os.path.join(GOREVLER, gor), os.path.join(GOREV_KLASOR, gor)))",
         "    for gor in []:  # MUTANT: yeni agac plandan cikarildi\n"
         "        plan.append((os.path.join(GOREVLER, gor), os.path.join(GOREV_KLASOR, gor)))"),)),
    ("M2b-kopyalama-noop", "oldurucu", (
        ("        gorev_olan, gorev_yeni = gorev_yaz(GOREVLER, g_hedef, g_dahil)",
         "        gorev_olan, gorev_yeni = gorev_yaz(GOREVLER, g_hedef, [])  # MUTANT"),)),
    ("M3a-sayac-sabitle", "oldurucu", (
        ("    return olan, yeni",
         "    return 5, yeni  # MUTANT: dosya sayaci sabitlendi"),)),
    ("M3b-yeni-sayaci-olu", "oldurucu", (
        ("            if _kopyala_gerekliyse(os.path.join(kok, gor), os.path.join(hedef, gor)):\n"
         "                yeni += 1",
         "            if _kopyala_gerekliyse(os.path.join(kok, gor), os.path.join(hedef, gor)):\n"
         "                yeni += 0  # MUTANT: 'yeni' sayaci olu"),)),
    ("M4-allowlist-asiri-dar", "oldurucu", (
        ('GOREV_IZINLI_UZANTI = (".md", ".txt", ".json")',
         'GOREV_IZINLI_UZANTI = (".txt", ".json")  # MUTANT: .md yutuldu'),)),
    ("M6-allowlist-noop", "oldurucu", (
        ("            if not _gorev_izinli_mi(ad):                # KATMAN 2 — acik allowlist",
         "            if False:  # MUTANT: allowlist devre disi"),)),
    # ---- KONTROL: yesil KALMALI ----
    ("K1-yorum-degisikligi", "kontrol", (
        ("    🔴 SEBEP METNI ASLA SIRRIN KENDISINI TASIMAZ",
         "    🔴 (kontrol mutanti — anlamsiz metin degisikligi) SEBEP METNI SIRRI TASIMAZ"),)),
    ("K2-allowlist-zararsiz-genisleme", "kontrol", (
        ('GOREV_IZINLI_UZANTI = (".md", ".txt", ".json")',
         'GOREV_IZINLI_UZANTI = (".md", ".txt", ".json", ".rst")  # KONTROL'),)),
)


def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    with open(YEDEKLE, encoding="utf-8") as f:
        taban_sha = hashlib.sha256(f.read().encode("utf-8")).hexdigest()

    print("=" * 78)
    print("TABAN — yedekle.py degistirilmemis hali")
    print("=" * 78)
    taban, notlar = bataryayi_kos(YEDEKLE)
    for k in TABAN_IDDIALAR:
        d = taban.get(k)
        print("  %s %-4s %s" % ("✅" if d else "❌", k, IDDIA_METNI[k]))
    for n in notlar:
        print("     ! " + n)
    taban_gecen = sum(1 for k in TABAN_IDDIALAR if taban.get(k))
    print("IDDIA = %d/%d gecti" % (taban_gecen, len(TABAN_IDDIALAR)))
    if taban_gecen != len(TABAN_IDDIALAR):
        print("\n🔴 TABAN KIRMIZI — mutasyon olcumu anlamsiz, durduruldu.")
        return 1

    print("\n" + "=" * 78)
    print("MUTASYON — dusen iddia kimlikleri AYRISMALI")
    print("=" * 78)
    td = tempfile.mkdtemp(prefix="gorev-mutant-")
    oldurucu_bek = oldurucu_ok = kontrol_bek = kontrol_ok = 0
    imzalar = {}
    try:
        for i, (ad, sinif, degisimler) in enumerate(MUTANTLAR):
            yol = mutant_uret(td, "mutant-%02d-%s.py" % (i, ad), degisimler, taban_sha)
            shutil.copy2(DRIVE_YOLU, os.path.join(td, "drive_yolu.py"))
            sonuc, _n = bataryayi_kos(yol)
            dusen = tuple(sorted(k for k in TABAN_IDDIALAR if not sonuc.get(k, False)))
            if sinif == "oldurucu":
                oldurucu_bek += 1
                oldu = bool(dusen)
                oldurucu_ok += 1 if oldu else 0
                print("  %s %-32s dusen: %s"
                      % ("✅" if oldu else "❌ SAG KALDI", ad, ", ".join(dusen) or "-"))
                imzalar[ad] = dusen
            else:
                kontrol_bek += 1
                yesil = not dusen
                kontrol_ok += 1 if yesil else 0
                print("  %s %-32s dusen: %s"
                      % ("✅ YESIL" if yesil else "❌ KONTROL DUSTU", ad,
                         ", ".join(dusen) or "-"))

        # IDDIA ATLAMA MUTANTI — batarya bir iddiayi HIC kosmazsa hukum KIRMIZI olmali.
        atlanmis, _n = bataryayi_kos(YEDEKLE, atla="G4")
        eksikler = [k for k in TABAN_IDDIALAR if k not in atlanmis]
        oldurucu_bek += 1
        atla_oldu = bool(eksikler)
        oldurucu_ok += 1 if atla_oldu else 0
        print("  %s %-32s dusen: %s"
              % ("✅" if atla_oldu else "❌ SAG KALDI", "M5-iddia-atla",
                 "IDDIA-EKSIK(%s)" % ",".join(eksikler) if eksikler else "-"))
        imzalar["M5-iddia-atla"] = ("IDDIA-EKSIK",)
    finally:
        shutil.rmtree(td, ignore_errors=True)

    gorulen = {}
    for ad, imza in imzalar.items():
        gorulen.setdefault(imza, []).append(ad)
    ayrismayan = sum(len(v) for v in gorulen.values() if len(v) > 1)

    print("\n" + "=" * 78)
    print("IDDIA      = %d/%d" % (taban_gecen, len(TABAN_IDDIALAR)))
    print("OLDURUCU   = %d/%d" % (oldurucu_ok, oldurucu_bek))
    print("KONTROL    = %d/%d" % (kontrol_ok, kontrol_bek))
    print("AYRISMAYAN = %d" % ayrismayan)
    # Bytecode onbellek tuzagi POZITIF olarak kapatildi mi? (bkz. modul basligi)
    print("BYTECODE   = %d batarya kosumu, toplam %d __pycache__ girisi "
          "(0 olmali: PYTHONDONTWRITEBYTECODE + ayri tempdir + sha dogrulamasi)"
          % (len(PYC_SAYAC), sum(PYC_SAYAC)))
    for imza, adlar in sorted(gorulen.items()):
        if len(adlar) > 1:
            print("  ⚠️ AYNI IMZA %s -> %s" % (list(imza), adlar))
    hazir = (taban_gecen == len(TABAN_IDDIALAR) and oldurucu_ok == oldurucu_bek
             and kontrol_ok == kontrol_bek and ayrismayan == 0)
    print("HUKUM      = " + ("hazir" if hazir else "KIRMIZI"))
    return 0 if hazir else 1


if __name__ == "__main__":
    sys.exit(main())

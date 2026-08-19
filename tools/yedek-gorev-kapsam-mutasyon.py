#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL + MUTASYON SURUCUSU — yedekle.py'nin ~/.claude AGAC KAPSAMI ve DISLAMASI.

KAPSAM: AGAC_KAPSAMI tablosundaki uc agac —
  gorev  ~/.claude/scheduled-tasks  (zamanlanmis gorev TANIM metinleri)
  cron   ~/.claude/cron             (nobet surucusu + crontab; ICINDE GERCEK JETON VAR)
  plan   ~/.claude/plans            (elle yazilmis plan belgeleri)

NEDEN VAR (olculdu, 7 Agu 2026): uc agac da yedek kapsaminda HIC GECMIYORDU ->
diskte TEK KOPYA, surum gecmisi YOK, hicbir depoda karsiligi YOK. Bu makinede
2-3 gunde bir hesap rotasyonu var; KOSUM KAYITLARI hesapla zaten olur, ama bu
METINLER de yedeksizse yordamin KENDISI kalici olarak kaybolur.

Agaclar kapsama alinirken IKINCI risk dogar: `cron` agacinin ICINDE gercek
`.ci-token` ve `.gh-token` duruyor ve yedek hedefi ORTAK Drive. Iki ayri iddia:
  (A) KAPSAM  — metinler yedege GIRIYOR (bayt bayt).
  (B) DISLAMA — jeton/izinsiz dosya yedege GIRMIYOR, SEBEBIYLE SAYILIYOR.

🔴 KATMANLAR TEK TEK OLCULUR (beyan edilmis survivor tuzagi): "jeton yedekte yok"
katmanlarin VEYA'sidir — bir katman kapansa oteki ayni dosyayi elerdi ve iddia
YESIL kalirdi. Bu yuzden her agacta AYIRT EDICI fikstur var:
  * IZINLI uzantili ama JETON ADLI dosya    -> YALNIZ sir nobeti eler
  * IZINLI uzantili ama IMZALI icerik       -> YALNIZ sir nobeti eler
  * zararsiz ad/icerik + IZINSIZ uzanti     -> YALNIZ allowlist eler
Uctan uca iddialar (G11 / C7) BILEREK survivor'dur; katman kaniti SAYILMAZ ve
ancak IKI KATMAN BIRDEN kapatan M10 mutanti ile kirmiziya doner (yani bos degil).

🔴 FIKSTUR DEGERI SECIMI KURALI (bu depoda 2. tekrar): fikstur ADEDI, mutantin
koyacagi hicbir sabitle CAKISMAMALI — ilk turda `return 5, yeni` mutanti fikstur
5 dosya oldugu icin SAG KALDI (sayac yalan soylerken batarya yesildi). Adetler
simdi 6 / 4 / 2 ve hicbiri mutant sabiti 5 ile cakismiyor; ayrica sayac IKI
bagimsiz eksenden olculuyor (tek kosum degeri + idempotens).

🔴 BYTECODE ONBELLEK TUZAGI ELE ALINDI (dort onlem):
  1. PYTHONDONTWRITEBYTECODE=1 + sys.dont_write_bytecode -> onbellek HIC yazilmaz
  2. her mutant AYRI tempdir + AYRI dosya adi
  3. POZITIF KANIT: mutant diskten GERI OKUNUR; capa gitmis, yeni metin gelmis ve
     sha256 tabandan farkli olmali — degilse SURUCU PATLAR
  4. kosum sonrasi kum havuzunda __pycache__ SAYILIR (0 olmali)

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
from git_ortami import sentetik_git

TOOLS = os.path.dirname(os.path.abspath(__file__))
YEDEKLE = os.path.join(TOOLS, "yedekle.py")
DRIVE_YOLU = os.path.join(TOOLS, "drive_yolu.py")


def _yedek_kok_adi():
    """Hedef kok adi TEK KAYNAKTAN (yedekle.YEDEK_KOK_ADI, 86e7a035): buradaki
    eski "backup" literali ikiz tanimdi ve batarya BOS klasore bakip TABAN
    KIRMIZI veriyordu (19 Agu SERIT B onarimi)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("yedekle_kok_sabiti", YEDEKLE)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul.YEDEK_KOK_ADI

# GERCEK ANAHTAR DEGIL. Dize PARCALI kurulur: hicbir KAYNAK SATIRI jeton desenine
# uymaz (repo geneli sir tarayicilari bosuna kirmizi yakmasin), CALISMA ANINDAKI
# dize ise yedekle.SIR_IMZALARI "GitHub jetonu" imzasini BIREBIR tetikler.
SAHTE_IMZA = "gh" + "p_" + ("S" * 36)
SAHTE_GOVDE = "SENTETIK-SAHTE-GERCEK-DEGIL\n"

# ---------------------------------------------------------------- fikstur ----
# agac etiketi -> {"dizin": ~/.claude altindaki ad,
#                  "izinli": ((gorece yol, icerik), ...),
#                  "haric":  ((gorece yol, icerik, beklenen katman), ...)}
# katman "sir"       -> YALNIZ sir nobeti eler (uzantisi IZINLI)
# katman "allowlist" -> YALNIZ allowlist eler (adi/icerigi ZARARSIZ)
# katman "ikisi"     -> gercek jetonun sekli (uzantisiz + jeton adli)
FIKSTUR = {
    "gorev": {
        "dizin": "scheduled-tasks",
        "izinli": (
            ("gorev-a/SKILL.md", "# gorev a\nsaat basi kosar\n"),
            ("gorev-b/SKILL.md", "# gorev b\ngunluk kosar\n"),
            ("gorev-c/SKILL.md", "# gorev c\nhaftalik kosar\n"),
            ("gorev-a/olcum.json", '{"esik": 3, "birim": "saat"}\n'),
            ("gorev-c/olcum-2.json", '{"esik": 11, "birim": "gun"}\n'),
            ("gorev-a/notlar.txt", "elle yazilmis nobet notu\n"),
        ),
        "haric": (
            ("gorev-b/gizli-token.md", SAHTE_GOVDE, "sir"),
            ("gorev-b/imza-notu.md", "not\n" + SAHTE_IMZA + "\n", "sir"),
            ("gorev-c/artik.bin", "duz metin, zararsiz ad, IZINSIZ uzanti\n", "allowlist"),
            (".gh-token", SAHTE_GOVDE, "ikisi"),
        ),
    },
    "cron": {
        "dizin": "cron",
        "izinli": (
            ("ci-nobeti.sh", "#!/bin/sh\necho nobet\n"),
            ("ci-nobeti.crontab", "40 * * * * /bin/sh ci-nobeti.sh\n"),
            ("gecici.crontab", "0 3 * * * /bin/sh temizlik.sh\n"),
            ("nobet-gorev.md", "# nobet yordami\n"),
        ),
        "haric": (
            # 🔴 GERCEK JETONLARIN SENTETIK IKIZLERI — ayri iddia (C3).
            (".ci-token", SAHTE_GOVDE, "ikisi"),
            (".gh-token", SAHTE_GOVDE, "ikisi"),
            # IZINLI uzanti (.sh) ama IMZALI icerik -> YALNIZ sir nobeti eler.
            ("kurulum.sh", "#!/bin/sh\nAUTH=" + SAHTE_IMZA + "\n", "sir"),
            # log: turetilmis + sinirsiz buyur -> YALNIZ allowlist eler (C4).
            ("ci-nobeti.log", "2026-08-07 kosum tamam\n", "allowlist"),
            ("mail-supurme.log", "2026-08-07 supuruldu\n", "allowlist"),
        ),
    },
    "plan": {
        "dizin": "plans",
        "izinli": (
            ("plan-bir.md", "# plan bir\n"),
            ("plan-iki.md", "# plan iki\n"),
        ),
        "haric": (
            ("taslak.bin", "zararsiz taslak, IZINSIZ uzanti\n", "allowlist"),
        ),
    },
}

# Tum agaclardaki SENTETIK jeton dosya adlari (uctan uca taramada aranir).
SENTETIK_JETONLAR = (".gh-token", ".ci-token")

TABAN_IDDIALAR = (
    # ---- gorev agaci + global eksenler ----
    "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11", "G12",
    # ---- cron agaci (YENI YUZEY: icinde gercek jeton var) ----
    "C1", "C2", "C3", "C4", "C5", "C6", "C7",
    # ---- plan agaci ----
    "P1", "P2", "P3",
    # ---- yapisal ----
    "S1",
)

IDDIA_METNI = {
    "G1": "gorev/plan-kapsami: izinli gorev dosyalarinin TAMAMI yedek planinda",
    "G2": "gorev/bayt-bayt: her izinli dosya hedefte kaynakla BIREBIR ayni",
    "G3": "gorev/damga-sayaci: damga['gorev'] == fikstur adedi (sabit degil)",
    "G4": "gorev/katman-1a: jeton ADLI ama IZINLI uzantili dosyayi SIR NOBETI eledi",
    "G5": "gorev/katman-1b: IMZALI icerik + IZINLI uzanti -> SIR NOBETI eledi",
    "G6": "gorev/katman-2: zararsiz ama IZINSIZ uzantili dosyayi ALLOWLIST eledi",
    "G7": "gorev/dislama-sayaci: damga['gorev_haric'] beklenen sayida VE stdout'ta o kadar 'DISLANDI:'",
    "G8": "gorev/mesru-yutulmadi: izinli dosyalarin HEPSI hedefte",
    "G9": "GLOBAL/imza-plan-hizasi: kaynak_imzasi['adet'] == len(yedek_plani)",
    "G10": "GLOBAL/dogrula-yesil: --dogrula cikis kodu 0",
    "G11": "gorev/uctan-uca: sentetik jeton hedefte yok (SURVIVOR — katman kaniti DEGIL)",
    "G12": "gorev/idempotens: 1.kosum yeni==N, 2.kosum yeni==0 ve gorev YINE N",
    "C1": "cron/plan-kapsami: .sh + .crontab + .md dosyalarinin TAMAMI planda",
    "C2": "cron/bayt-bayt: 4 nobet dosyasi hedefte kaynakla BIREBIR ayni",
    "C3": "🔴 cron/JETON: .ci-token VE .gh-token SIR NOBETI ile elendi + hedefte YOK",
    "C4": "cron/LOG: iki .log da ALLOWLIST ile elendi + hedefte YOK (sayildi)",
    "C5": "cron/katman-1: IMZALI .sh (IZINLI uzanti) -> YALNIZ sir nobeti eledi",
    "C6": "cron/sayaclar: damga cron/cron_haric beklenen + idempotens (yeni 4 -> 0)",
    "C7": "cron/uctan-uca: sentetik jetonlar TUM backup agacinda yok (SURVIVOR)",
    "P1": "plan/kapsam+bayt-bayt: plan belgeleri planda VE hedefte birebir",
    "P2": "plan/sayaclar: damga plan/plan_haric beklenen sayida",
    "P3": "plan/katman-2: IZINSIZ uzantili taslak ALLOWLIST ile elendi + hedefte YOK",
    "S1": "yapisal: AGAC_KAPSAMI tam olarak beklenen 3 agaci tasiyor (fail-closed)",
}

PYC_SAYAC = []

OLCUM_KODU = (
    "import sys;sys.dont_write_bytecode=True\n"
    "import importlib.util,json\n"
    "spec=importlib.util.spec_from_file_location('y', %r)\n"
    "m=importlib.util.module_from_spec(spec)\n"
    "spec.loader.exec_module(m)\n"
    "plan=m.yedek_plani()\n"
    "agaclar=[]\n"
    "for a in m.AGAC_KAPSAMI:\n"
    "    d,h,g=m.agac_plani(a)\n"
    "    agaclar.append({'etiket':a[0],'kok':a[1],'hedef':a[2],'izinli':list(a[3]),\n"
    "                    'dahil':d,'haric':h,'gurultu':g})\n"
    "print(json.dumps({'plan_hedefleri':[h for _k,h in plan],'plan_adet':len(plan),\n"
    "                  'agaclar':agaclar,'imza':m.kaynak_imzasi()}))\n"
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
    sentetik_git(kok, "init", "-q", capture_output=True)

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

    koklar = {}
    for etiket, fx in FIKSTUR.items():
        agac_kok = os.path.join(ev, ".claude", fx["dizin"])
        os.makedirs(agac_kok, exist_ok=True)
        for gor, icerik in fx["izinli"]:
            _yaz(os.path.join(agac_kok, gor), icerik)
        for gor, icerik, _k in fx["haric"]:
            _yaz(os.path.join(agac_kok, gor), icerik)
        koklar[etiket] = agac_kok

    ortam = dict(os.environ)
    ortam["HOME"] = ev
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    return {"kok": kok, "betik": os.path.join(kok, "tools", "yedekle.py"),
            "ev": ev, "koklar": koklar,
            "hedef": os.path.join(pruvo, _yedek_kok_adi()),
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
        return {"_hata": (r.stdout + r.stderr)[-400:], "agaclar": []}


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
    """Adlandirilmis iddialari kosar. Doner: (sonuc dict, notlar list)."""
    sonuc, notlar = {}, []

    def iddia(kimlik, ok, ayrinti=""):
        if atla == kimlik:
            return
        sonuc[kimlik] = bool(ok)
        if not ok and ayrinti:
            notlar.append("%s: %s" % (kimlik, ayrinti))

    td = tempfile.mkdtemp(prefix="agac-kapsam-")
    try:
        o = kum_havuzu(td, kaynak_betik)
        r1 = kos(o)
        damga1 = _damga(o["hedef"])
        r = kos(o)                       # 2. kosum: idempotens ekseni
        m = olc(o)
        hedef = o["hedef"]
        damga = _damga(hedef)
        hedefte = set(hedef_dosyalari(hedef))
        plan_hedefleri = set(m.get("plan_hedefleri", []))
        agaclar = {a["etiket"]: a for a in m.get("agaclar", [])}
        stdout_dislanan = sum(1 for s in r.stdout.splitlines() if "DISLANDI:" in s)

        # S1 — yapisal: tablo beklenen 3 agaci tasiyor (fail-closed)
        iddia("S1", set(agaclar) == set(FIKSTUR),
              "tablodaki agaclar=%s beklenen=%s" % (sorted(agaclar), sorted(FIKSTUR)))

        def hedef_klasor(etiket):
            return (agaclar.get(etiket) or {}).get("hedef", "?" + etiket)

        def haric_sozluk(etiket):
            return dict(tuple(x) for x in (agaclar.get(etiket) or {}).get("haric", []))

        def katman(etiket, gor):
            sebep = haric_sozluk(etiket).get(gor)
            if sebep is None:
                return "ELENMEDI"
            if sebep.startswith("allowlist disi"):
                return "allowlist"
            if sebep.startswith("icerik imzasi"):
                return "sir-icerik"
            return "sir"

        def planda_eksik(etiket):
            hk = hedef_klasor(etiket)
            return [g for g, _i in FIKSTUR[etiket]["izinli"]
                    if os.path.join(hk, g) not in plan_hedefleri]

        def bayt_bozuk(etiket):
            hk = hedef_klasor(etiket)
            bozuk = []
            for gor, _i in FIKSTUR[etiket]["izinli"]:
                try:
                    with open(os.path.join(o["koklar"][etiket], gor), "rb") as f:
                        a = f.read()
                    with open(os.path.join(hedef, hk, gor), "rb") as f:
                        b = f.read()
                except OSError:
                    bozuk.append(gor + " (hedefte YOK)")
                    continue
                if a != b:
                    bozuk.append(gor + " (bayt farki)")
            return bozuk

        def hedefte_yok(etiket, gor):
            return os.path.join(hedef_klasor(etiket), gor) not in hedefte

        # =================== GOREV AGACI ===================
        n_g = len(FIKSTUR["gorev"]["izinli"])
        h_g = len(FIKSTUR["gorev"]["haric"])
        iddia("G1", not planda_eksik("gorev"), "planda yok: %s" % planda_eksik("gorev"))
        iddia("G2", not bayt_bozuk("gorev"), "; ".join(bayt_bozuk("gorev")))
        iddia("G3", damga.get("gorev") == n_g,
              "damga['gorev']=%r beklenen %d" % (damga.get("gorev"), n_g))
        iddia("G4", katman("gorev", "gorev-b/gizli-token.md") == "sir"
              and hedefte_yok("gorev", "gorev-b/gizli-token.md"),
              "katman=%s" % katman("gorev", "gorev-b/gizli-token.md"))
        iddia("G5", katman("gorev", "gorev-b/imza-notu.md") == "sir-icerik"
              and hedefte_yok("gorev", "gorev-b/imza-notu.md"),
              "katman=%s" % katman("gorev", "gorev-b/imza-notu.md"))
        iddia("G6", katman("gorev", "gorev-c/artik.bin") == "allowlist"
              and hedefte_yok("gorev", "gorev-c/artik.bin"),
              "katman=%s" % katman("gorev", "gorev-c/artik.bin"))
        toplam_haric = sum(len(f["haric"]) for f in FIKSTUR.values())
        iddia("G7", damga.get("gorev_haric") == h_g and stdout_dislanan == toplam_haric,
              "damga=%r stdout=%d beklenen %d/%d"
              % (damga.get("gorev_haric"), stdout_dislanan, h_g, toplam_haric))
        yutulan = [g for g, _i in FIKSTUR["gorev"]["izinli"]
                   if hedefte_yok("gorev", g)]
        iddia("G8", not yutulan, "hedefte yok: %s" % yutulan)
        imza = m.get("imza") or {}
        iddia("G9", imza.get("adet") == m.get("plan_adet"),
              "imza=%r plan=%r" % (imza.get("adet"), m.get("plan_adet")))
        rd = kos(o, "--dogrula")
        iddia("G10", rd.returncode == 0, "rc=%d %s" % (rd.returncode, rd.stdout[-200:]))
        jeton_izi = [y for y in hedefte
                     if os.path.basename(y) in SENTETIK_JETONLAR]
        iddia("G11", not jeton_izi, "hedefte iz: %s" % jeton_izi)
        iddia("G12", damga1.get("gorev_yeni") == n_g and damga.get("gorev_yeni") == 0
              and damga.get("gorev") == n_g,
              "1.kosum yeni=%r 2.kosum yeni=%r gorev=%r beklenen %d/0/%d"
              % (damga1.get("gorev_yeni"), damga.get("gorev_yeni"),
                 damga.get("gorev"), n_g, n_g))

        # =================== CRON AGACI (YENI YUZEY) ===================
        n_c = len(FIKSTUR["cron"]["izinli"])
        h_c = len(FIKSTUR["cron"]["haric"])
        iddia("C1", not planda_eksik("cron"), "planda yok: %s" % planda_eksik("cron"))
        iddia("C2", not bayt_bozuk("cron"), "; ".join(bayt_bozuk("cron")))
        # 🔴 C3 — GERCEK JETONLARIN SENTETIK IKIZLERI, AYRI IDDIA.
        jeton_kat = [(a, katman("cron", a)) for a in (".ci-token", ".gh-token")]
        iddia("C3", all(k == "sir" for _a, k in jeton_kat)
              and all(hedefte_yok("cron", a) for a, _k in jeton_kat),
              "katmanlar=%s" % jeton_kat)
        log_kat = [(a, katman("cron", a)) for a in ("ci-nobeti.log", "mail-supurme.log")]
        iddia("C4", all(k == "allowlist" for _a, k in log_kat)
              and all(hedefte_yok("cron", a) for a, _k in log_kat),
              "katmanlar=%s" % log_kat)
        iddia("C5", katman("cron", "kurulum.sh") == "sir-icerik"
              and hedefte_yok("cron", "kurulum.sh"),
              "katman=%s" % katman("cron", "kurulum.sh"))
        iddia("C6", damga.get("cron") == n_c and damga.get("cron_haric") == h_c
              and damga1.get("cron_yeni") == n_c and damga.get("cron_yeni") == 0,
              "cron=%r haric=%r yeni1=%r yeni2=%r beklenen %d/%d/%d/0"
              % (damga.get("cron"), damga.get("cron_haric"), damga1.get("cron_yeni"),
                 damga.get("cron_yeni"), n_c, h_c, n_c))
        # C7 — UCTAN UCA (SURVIVOR): tum backup agacinda jeton adi gecmiyor.
        iddia("C7", not jeton_izi, "hedefte iz: %s" % jeton_izi)

        # =================== PLAN AGACI ===================
        n_p = len(FIKSTUR["plan"]["izinli"])
        h_p = len(FIKSTUR["plan"]["haric"])
        iddia("P1", not planda_eksik("plan") and not bayt_bozuk("plan"),
              "eksik=%s bozuk=%s" % (planda_eksik("plan"), bayt_bozuk("plan")))
        iddia("P2", damga.get("plan") == n_p and damga.get("plan_haric") == h_p,
              "plan=%r haric=%r beklenen %d/%d"
              % (damga.get("plan"), damga.get("plan_haric"), n_p, h_p))
        iddia("P3", katman("plan", "taslak.bin") == "allowlist"
              and hedefte_yok("plan", "taslak.bin"),
              "katman=%s" % katman("plan", "taslak.bin"))

        pyc = [y for y in hedef_dosyalari(o["kok"]) if "__pycache__" in y]
        PYC_SAYAC.append(len(pyc))
        if pyc:
            notlar.append("UYARI: kum havuzunda __pycache__ olustu: %s" % pyc[:3])
        if r1.returncode != 0:
            notlar.append("1. kosum rc=%d" % r1.returncode)
        return sonuc, notlar
    finally:
        shutil.rmtree(td, ignore_errors=True)


# ----------------------------------------------------------------- mutantlar --
SIR_CAPA = "            sebep = sir_sebebi(tam, ad)                 # KATMAN 1 — sir nobeti"
ALW_CAPA = "            if not _agac_izinli_mi(ad, izinli):         # KATMAN 2 — acik allowlist"
CRON_CAPA = '    ("cron", CRON, "cron-nobet", (".sh", ".crontab", ".md", ".txt", ".json")),'
GOREV_CAPA = '    ("gorev", GOREVLER, "gorev-tanimlari", (".md", ".txt", ".json")),'

MUTANTLAR = (
    ("M1-sir-katmani-noop", "oldurucu", (
        (SIR_CAPA, "            sebep = None  # MUTANT: sir nobeti devre disi"),)),
    ("M2a-plandan-cikar", "oldurucu", (
        ("        for gor in agac_plani(agac)[0]:",
         "        for gor in []:  # MUTANT: agaclar plandan cikarildi"),)),
    ("M2b-kopyalama-noop", "oldurucu", (
        ("            olan, yeni_a = agac_yaz(kok, a_hedef, a_dahil, etiket=etiket)",
         "            olan, yeni_a = agac_yaz(kok, a_hedef, [], etiket=etiket)  # MUTANT"),)),
    ("M3a-sayac-sabitle", "oldurucu", (
        ("    return olan, yeni",
         "    return 5, yeni  # MUTANT: dosya sayaci sabitlendi"),)),
    ("M3b-yeni-sayaci-olu", "oldurucu", (
        ("            if _kopyala_gerekliyse(os.path.join(kok, gor), os.path.join(hedef, gor)):\n"
         "                yeni += 1",
         "            if _kopyala_gerekliyse(os.path.join(kok, gor), os.path.join(hedef, gor)):\n"
         "                yeni += 0  # MUTANT: 'yeni' sayaci olu"),)),
    ("M4-gorev-allowlist-dar", "oldurucu", (
        (GOREV_CAPA,
         '    ("gorev", GOREVLER, "gorev-tanimlari", (".txt", ".json")),  # MUTANT'),)),
    ("M6-allowlist-noop", "oldurucu", (
        (ALW_CAPA, "            if False:  # MUTANT: allowlist devre disi"),)),
    # ---- YENI YUZEYE OZGU MUTANTLAR ----
    ("M7-cron-agacini-cikar", "oldurucu", (
        (CRON_CAPA, "    # MUTANT: cron agaci kapsamdan cikarildi"),)),
    ("M8-cron-log-kapsama-alindi", "oldurucu", (
        (CRON_CAPA,
         '    ("cron", CRON, "cron-nobet", (".sh", ".crontab", ".md", ".txt", ".json",\n'
         '                                  ".log")),  # MUTANT: log kapsama alindi'),)),
    ("M10-IKI-KATMAN-BIRDEN", "oldurucu", (
        (SIR_CAPA, "            sebep = None  # MUTANT"),
        (ALW_CAPA, "            if False:  # MUTANT"))),
    # ---- KONTROL: yesil KALMALI ----
    ("K1-yorum-degisikligi", "kontrol", (
        ("    🔴 SEBEP METNI ASLA SIRRIN KENDISINI TASIMAZ",
         "    🔴 (kontrol mutanti — anlamsiz metin degisikligi) SEBEP METNI SIRRI TASIMAZ"),)),
    ("K2-allowlist-zararsiz-genisleme", "kontrol", (
        (GOREV_CAPA,
         '    ("gorev", GOREVLER, "gorev-tanimlari", (".md", ".txt", ".json", ".rst")),  # KONTROL'),)),
)


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
    with open(yol, encoding="utf-8") as f:
        geri = f.read()
    sha = hashlib.sha256(geri.encode("utf-8")).hexdigest()
    if sha == taban_sha:
        raise RuntimeError("MUTASYON UYGULANMADI (sha tabana esit): " + ad)
    for eski, yeni in degisimler:
        if eski in geri and yeni not in geri:
            raise RuntimeError("MUTASYON DISKTE YOK: " + ad)
    return yol


def main():
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    with open(YEDEKLE, encoding="utf-8") as f:
        taban_sha = hashlib.sha256(f.read().encode("utf-8")).hexdigest()

    print("=" * 78)
    print("TABAN — yedekle.py degistirilmemis hali")
    print("=" * 78)
    taban, notlar = bataryayi_kos(YEDEKLE)
    for k in TABAN_IDDIALAR:
        print("  %s %-5s %s" % ("✅" if taban.get(k) else "❌", k, IDDIA_METNI[k]))
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
    td = tempfile.mkdtemp(prefix="agac-mutant-")
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
                oldurucu_ok += 1 if dusen else 0
                print("  %s %-32s dusen: %s"
                      % ("✅" if dusen else "❌ SAG KALDI", ad, ", ".join(dusen) or "-"))
                imzalar[ad] = dusen
            else:
                kontrol_bek += 1
                kontrol_ok += 1 if not dusen else 0
                print("  %s %-32s dusen: %s"
                      % ("✅ YESIL" if not dusen else "❌ KONTROL DUSTU", ad,
                         ", ".join(dusen) or "-"))

        atlanmis, _n = bataryayi_kos(YEDEKLE, atla="C3")
        eksikler = [k for k in TABAN_IDDIALAR if k not in atlanmis]
        oldurucu_bek += 1
        oldurucu_ok += 1 if eksikler else 0
        print("  %s %-32s dusen: %s"
              % ("✅" if eksikler else "❌ SAG KALDI", "M5-iddia-atla",
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
    for imza, adlar in sorted(gorulen.items()):
        if len(adlar) > 1:
            print("  ⚠️ AYNI IMZA %s -> %s" % (list(imza), adlar))
    print("BYTECODE   = %d batarya kosumu, toplam %d __pycache__ girisi (0 olmali)"
          % (len(PYC_SAYAC), sum(PYC_SAYAC)))
    hazir = (taban_gecen == len(TABAN_IDDIALAR) and oldurucu_ok == oldurucu_bek
             and kontrol_ok == kontrol_bek and ayrismayan == 0)
    print("HUKUM      = " + ("hazir" if hazir else "KIRMIZI"))
    return 0 if hazir else 1


if __name__ == "__main__":
    sys.exit(main())

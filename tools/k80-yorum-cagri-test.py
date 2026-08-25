#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K286 — `is-akisi-kapisi.py` K80 kolu: YORUM satiri CAGRI sayilmasin.

OLCULEN KUSUR (25 Agu 2026, KraL defteri K286)
──────────────────────────────────────────────
K80 adim kimligi `(dosya, job, run_metni)` uclusuydu ve `run: |` govdesindeki YORUM
satirlari o metnin PARCASIYDI. Bir adimin yorumunu duzeltmek — komutu BIR HARF
degistirmeden — kimligi degistiriyor, adim "GERCEKTEN YENI" sayiliyordu.
`nobet.yml`'in hicbir isi `deploy.needs`te olmadigi icin sonuc her seferinde sahte
`K80 ZINCIR_DISI=1`; bloklayici bir dosyada ayni kusur komutu BOSUNA yeniden kosturur.

BU BATARYA NE OLCER
───────────────────
V1 REPRODUKSIYON : YALNIZ yorumu degisen adim YENI SAYILMAZ (kusuru ureten girdi).
V2 YANLIS-NEGATIF: GERCEKTEN yeni adim HALA YAKALANIR — hem zincir DISI hem ICI kolda.
V3 YAPI (dizge degil): tirnak icindeki `#` ARGUMANDIR, yorum degil; ve TAMAMEN yorum
   olan satir icindeki `;` satiri OLCULEMEDI'ye DUSURMEZ (sira kusuru: emniyet kontrolu
   yorum dusuruldukten SONRA gelir — nobet.yml'deki N4A blogu tam olarak boyledir).
M1 HEDEFLI MUTANT: uretimdeki `yorum_ayrimi` kolu OLDURULUR. Beklenen:
   V1 KIRMIZI (hedef kol) **ve** V2 DEGISMEZ (yan eksen yesil kalir). Mutantin yalnizca
   "kirmizi gelmesi" kanit DEGILDIR ([[ad-iki-rolde-mutanti-golgeler]]); kirmizinin
   SEBEBI hedef kola atfedilir.

HERMETIK: gecici bir git deposu kurulur, URETIM dosyasi oraya KOPYALANIR ve importlib
ile ITHAL edilir — ikiz tanim YOK, olculen sey uretim govdesidir. `ROOT = dirname(TOOLS)`
oldugu icin modul kendini o gecici depoda sanir; CANLI repoya, canli git'e, aga SIFIR
dokunus. Ureten temizler: her vaka `finally`de rmtree eder.
"""
import argparse
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
URETIM = os.path.join(TOOLS, "is-akisi-kapisi.py")
SUZGEC = os.path.join(TOOLS, "icra-suzgeci.py")

# Gecici depoda kosturulabilir olmasi gereken betikler (zincir ICI kolda kapi bunlari
# GERCEKTEN kosar; yoksa "betik committe YOK" bulgusu uretir).
BETIKLER = ("hijyen-test.py", "serit-test.py", "hijyen-eklenen.py",
            "serit-eklenen.py", "yayin.py")

# ── FIKSTUR GOVDELERI ───────────────────────────────────────────────────────────
# `hijyen` = zincir DISI (nobet.yml sekli: hicbir is `deploy.needs`te degil)
# `serit` + `deploy: needs:[serit]` = zincir ICI (deploy.yml sekli)
#
# 🔴 A ve B govdelerinde KOMUT AYNIDIR; yalnizca YORUM METNI degisir. Yorum blogu
# BILEREK `;` ve dengesiz `"` tasir — nobet.yml:2114-2119'daki N4A blogunun sekli budur
# ve kusurun ikinci yuzu (sira kusuru) tam olarak orada saklanir.
HIJYEN_A = ('          # N4A: sayac DURUSTLUGU — "USTUSTE_ONARIMSIZ dustu,\n'
            '          # demek ki bir sey onarildi" iddiasini imkansiz kilar.\n'
            '          # (kusur degil) ve mutant cekirdegini YINE kosar; "dosya var ama\n'
            '          python3 tools/hijyen-test.py\n')
HIJYEN_B = ('          # N4A (GUNCELLENDI): sayac DURUSTLUGU — yorum metni DEGISTI,\n'
            '          # komut BIR HARF degismedi; kapi bunu YENI SAYMAMALI.\n'
            '          # (kusur degil) ve mutant cekirdegini YINE kosar; "baska metin\n'
            '          python3 tools/hijyen-test.py\n')
SERIT_A = ('          # serit tarafi ESKI yorum; noktali virgul burada da var.\n'
           '          python3 tools/serit-test.py\n')
SERIT_B = ('          # serit tarafi YENI yorum; noktali virgul burada da var.\n'
           '          python3 tools/serit-test.py\n')

# Pozitif kontrol: GERCEKTEN yeni komut eklenir (yorum DEGIL). A'nin yorumu AYNEN kalir
# ki olculen tek degisken "yeni komut" olsun.
HIJYEN_YENI = HIJYEN_A + '          python3 tools/hijyen-eklenen.py\n'
SERIT_YENI = SERIT_A + '          python3 tools/serit-eklenen.py\n'


def akis(hijyen_run, serit_run):
    return (
        "name: nobet\n"
        "on: [push]\n"
        "jobs:\n"
        "  hijyen:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: hijyen adimi\n"
        "        run: |\n" + hijyen_run +
        "  serit:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - name: serit adimi\n"
        "        run: |\n" + serit_run +
        "  deploy:\n"
        "    needs: [serit]\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: python3 tools/yayin.py\n")


class SahteArgs:
    base = hedef = None
    pre_push = False


def _git(kok, *a):
    r = subprocess.run(["git", "-C", kok] + list(a), capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError("git %s -> %s" % (" ".join(a), r.stderr.strip()))
    return r.stdout.strip()


def _kur(kok):
    os.makedirs(os.path.join(kok, "tools"))
    os.makedirs(os.path.join(kok, ".github", "workflows"))
    shutil.copy2(URETIM, os.path.join(kok, "tools", "is-akisi-kapisi.py"))
    shutil.copy2(SUZGEC, os.path.join(kok, "tools", "icra-suzgeci.py"))
    for ad in BETIKLER:
        with open(os.path.join(kok, "tools", ad), "w", encoding="utf-8") as f:
            f.write("import sys\nsys.exit(0)\n")
    _git(kok, "init", "-q")
    _git(kok, "config", "user.email", "k286@pruvo.local")
    _git(kok, "config", "user.name", "K286")
    _git(kok, "config", "commit.gpgsign", "false")


def _yaz(kok, hijyen_run, serit_run):
    with open(os.path.join(kok, ".github", "workflows", "nobet.yml"), "w",
              encoding="utf-8") as f:
        f.write(akis(hijyen_run, serit_run))


_SAYAC = [0]


def _ithal(kok):
    """Uretim govdesini GECICI depodan ithal et -> ROOT o depoya cozulur."""
    _SAYAC[0] += 1
    yol = os.path.join(kok, "tools", "is-akisi-kapisi.py")
    ad = "k286_kapi_%d" % _SAYAC[0]
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(ad, None)
    if os.path.realpath(mod.ROOT) != os.path.realpath(kok):
        raise RuntimeError("ROOT gecici depoya cozulmedi (%s != %s)" % (mod.ROOT, kok))
    return mod


def olc(hijyen_a, serit_a, hijyen_b, serit_b, yorum_ayrimi=True):
    """Iki commit uret, K80 hukmunu KOSTUR. -> (zincir_disi, bloklayici_yeni, kosulan)."""
    kok = tempfile.mkdtemp(prefix="pruvo-k286-")
    try:
        _kur(kok)
        _yaz(kok, hijyen_a, serit_a)
        _git(kok, "add", "-A")
        _git(kok, "commit", "-q", "-m", "A")
        base = _git(kok, "rev-parse", "HEAD")
        _yaz(kok, hijyen_b, serit_b)
        _git(kok, "add", "-A")
        _git(kok, "commit", "-q", "-m", "B")
        hedef = _git(kok, "rev-parse", "HEAD")

        mod = _ithal(kok)
        args = SahteArgs()
        args.base, args.hedef = base, hedef
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            bulgular, yeni, kosulan = mod.yeni_ci_adimi_kontrol(
                args, yorum_ayrimi=yorum_ayrimi)
        zincir_disi = 0
        for satir in tampon.getvalue().splitlines():
            if satir.startswith("K80 ZINCIR_DISI="):
                zincir_disi = int(satir.split("=", 1)[1].split(" ", 1)[0])
        return zincir_disi, yeni, kosulan, bulgular
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def kimlik_ekseni():
    """V3 — ayrim YAPIDAN turer: tirnakli `#` argumandir, yorumdaki `;` masum."""
    kok = tempfile.mkdtemp(prefix="pruvo-k286-kimlik-")
    try:
        _kur(kok)
        mod = _ithal(kok)
        hatalar = []
        # (a) TIRNAK ICINDEKI `#` YORUM DEGILDIR -> kimlikte KALIR.
        kim = mod._k80_komut_kimligi("python3 tools/x.py '#etiket'")
        if "#etiket" not in kim:
            hatalar.append("V3a: tirnakli '#etiket' argumani kimlikten DUSTU (%r) -> "
                           "dizge tabanli yorum soyma mesru argumani yiyor" % kim)
        # (b) TAMAMEN yorum olan, icinde `;` ve dengesiz `\"` tasiyan satir DUSER;
        #     govde OLCULEMEDI'ye DUSMEZ (sira kusuru nobeti).
        kim = mod._k80_komut_kimligi(
            '# (kusur degil) ve mutant cekirdegini YINE kosar; "dosya var ama\n'
            'python3 tools/x.py\n')
        if kim != "python3 tools/x.py":
            hatalar.append("V3b: `;` tasiyan YORUM satiri govdeyi ham metne dusurdu "
                           "(%r) -> emniyet kontrolu yorumdan ONCE kosuyor" % kim)
        # (c) OLCULEMEYEN govde HAM kalir (fail-closed; gevsetme nobeti).
        ham = "python3 tools/x.py && python3 tools/y.py"
        if mod._k80_komut_kimligi(ham) != ham:
            hatalar.append("V3c: kabuk metakarakterli govde HAM kimlikte kalmadi -> "
                           "olcemedigi yerde kapi GEVSEDI")
        # (d) SATIR SONU yorumu da yapidan duser, komut argv'si BOZULMAZ.
        argv = mod._k80_satirlar("python3 tools/x.py --bayrak  # aciklama")
        if argv != [["python3", "tools/x.py", "--bayrak"]]:
            hatalar.append("V3d: satir-sonu yorumu argv'ye ARGUMAN olarak sizdi (%r)"
                           % (argv,))
        return hatalar
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def taban_curutme(ref):
    """K286 TESHISI TABANDA GERCEKTEN VAR MI — yama ONCESI govdeyle olculur.

    🔴 NEDEN AYRI MOD: V1'in yesili ve M1'in kirmizisi ikisi de YAMALI govdenin
    ustunde olculur; ikisi birlikte bile "kusur main'de VARDI" demez — mutant kolu
    tautoloji olabilir ([[bayat-taban-hipotezi-kosumdan-once-curutulur]]). Bu mod
    `<ref>`teki YAMASIZ dosyayi AYNI V1 fiksturunde kosturur ve `ZINCIR_DISI=1`
    bekler. 1 CIKMAZSA teshis DUSER -> rc=2 (OLCULEMEDI), yesil DEGIL.

    CI'da KOSMAZ: sig checkout'ta `origin/main` bulunmayabilir; bu bir TESHIS
    kolu, kapsam kolu degil.
    """
    kok_repo = os.path.dirname(TOOLS)
    r = subprocess.run(["git", "-C", kok_repo, "show", "%s:tools/is-akisi-kapisi.py" % ref],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print("TABAN OLCULEMEDI: `git show %s:tools/is-akisi-kapisi.py` -> %s"
              % (ref, r.stderr.strip()[:200]))
        return 2
    kok = tempfile.mkdtemp(prefix="pruvo-k286-taban-")
    try:
        _kur(kok)
        # YAMASIZ govdeyi uretim dosyasinin USTUNE yaz (fikstur AYNI kalir).
        with open(os.path.join(kok, "tools", "is-akisi-kapisi.py"), "w",
                  encoding="utf-8") as f:
            f.write(r.stdout)
        _yaz(kok, HIJYEN_A, SERIT_A)
        _git(kok, "add", "-A")
        _git(kok, "commit", "-q", "-m", "A")
        base = _git(kok, "rev-parse", "HEAD")
        _yaz(kok, HIJYEN_B, SERIT_B)
        _git(kok, "add", "-A")
        _git(kok, "commit", "-q", "-m", "B")
        hedef = _git(kok, "rev-parse", "HEAD")
        mod = _ithal(kok)
        args = SahteArgs()
        args.base, args.hedef = base, hedef
        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            _bulgular, yeni, kosulan = mod.yeni_ci_adimi_kontrol(args)
        zd = 0
        for satir in tampon.getvalue().splitlines():
            if satir.startswith("K80 ZINCIR_DISI="):
                zd = int(satir.split("=", 1)[1].split(" ", 1)[0])
        print("TABAN (%s, YAMASIZ) · YALNIZ YORUM degisti -> "
              "ZINCIR_DISI=%d BLOKLAYICI_YENI=%d KOSULAN=%d" % (ref, zd, yeni, kosulan))
        if zd == 1 and yeni == 1:
            print("TABAN_KUSURU=VAR — K286 teshisi tabanda DOGRULANDI "
                  "(yorum degisikligi hem sahte ZINCIR_DISI hem bosuna kosum uretti)")
            return 0
        print("TABAN_KUSURU=YOK — teshis DUSTU: tabanda yorum degisikligi yeni adim "
              "URETMEDI. Yamanin gerekcesi OLCULEMEDI, kabul edilemez.")
        return 2
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="K286 — K80 yorum/cagri ayrimi bataryasi")
    ap.add_argument("--taban-curutme", metavar="REF", nargs="?", const="origin/main",
                    help="TESHIS: <REF>teki YAMASIZ govdede kusur GERCEKTEN var mi "
                         "(varsayilan origin/main). CI kolu DEGIL.")
    args = ap.parse_args()

    if args.taban_curutme:
        return taban_curutme(args.taban_curutme)

    hatalar = []
    vaka = 0
    print("K286 — K80 YORUM/CAGRI AYRIMI (hermetik; canli repoya/aga SIFIR dokunus)")
    print("-" * 74)

    # ── V2 ONCE: TABAN. Pozitif kontrol dusmusse V1'in yesili ANLAMSIZDIR. ──────
    zd_p, blok_p, kosulan_p, _ = olc(HIJYEN_A, SERIT_A, HIJYEN_YENI, SERIT_YENI)
    vaka += 1
    # 🔴 KOSULAN=2 BEKLENIR, 1 DEGIL — sayinin ne SAYDIGI onemli. Kapinin "yeni adim"
    # birimi TEK BIR `run` GOVDESIDIR; kosturucu ise o govdenin HER kosulabilir SATIRINI
    # ayri ayri kosar. `serit` adiminin govdesi V2'de iki satirdir (`serit-test.py` +
    # yeni eklenen `serit-eklenen.py`), dolayisiyla BIR yeni adim IKI kosum uretir.
    # Bu sayiyi 1'e cekmek kosturucunun gercek davranisini gizlerdi.
    print("V2 YANLIS-NEGATIF NOBETI (gercekten yeni adim) : "
          "ZINCIR_DISI=%d BLOKLAYICI_YENI=%d KOSULAN=%d  (beklenen 1/1/2)"
          % (zd_p, blok_p, kosulan_p))
    if (zd_p, blok_p) != (1, 1):
        hatalar.append("V2: GERCEKTEN yeni adim YAKALANMADI (zincir_disi=%d "
                       "bloklayici_yeni=%d, beklenen 1/1) -> kapi KORLESTI, "
                       "V1'in yesili anlamsiz" % (zd_p, blok_p))
    if kosulan_p != 2:
        hatalar.append("V2: bloklayici yeni adimin govdesi KOSTURULMADI (kosulan=%d, "
                       "beklenen 2 = govdenin iki kosulabilir satiri)" % kosulan_p)

    # ── V1: REPRODUKSIYON — kusuru URETEN girdi. ───────────────────────────────
    zd_r, blok_r, kosulan_r, _ = olc(HIJYEN_A, SERIT_A, HIJYEN_B, SERIT_B)
    vaka += 1
    print("V1 REPRODUKSIYON (yalniz YORUM degisti)        : "
          "ZINCIR_DISI=%d BLOKLAYICI_YENI=%d KOSULAN=%d  (beklenen 0/0/0)"
          % (zd_r, blok_r, kosulan_r))
    if (zd_r, blok_r, kosulan_r) != (0, 0, 0):
        hatalar.append("V1: YALNIZ YORUMU degisen adim YENI sayildi (zincir_disi=%d "
                       "bloklayici_yeni=%d kosulan=%d) -> K286 sahte pozitifi YASIYOR"
                       % (zd_r, blok_r, kosulan_r))

    # ── V3: ayrim YAPIDAN mi turuyor? ──────────────────────────────────────────
    v3 = kimlik_ekseni()
    vaka += 4
    print("V3 YAPI EKSENI (tirnakli `#` · yorumdaki `;` · fail-closed · satir-sonu): "
          "%s" % ("YESIL" if not v3 else "KIRMIZI"))
    hatalar.extend(v3)

    # ── M1: HEDEFLI MUTANT + HEDEF-KOL ATFI ────────────────────────────────────
    zd_m, blok_m, _, _ = olc(HIJYEN_A, SERIT_A, HIJYEN_B, SERIT_B, yorum_ayrimi=False)
    zd_my, blok_my, _, _ = olc(HIJYEN_A, SERIT_A, HIJYEN_YENI, SERIT_YENI,
                               yorum_ayrimi=False)
    vaka += 2
    print("M1 HEDEFLI MUTANT (yorum_ayrimi=False)          : "
          "V1->%d/%d (mutant KIRMIZI olmali)  V2->%d/%d (yan eksen DEGISMEMELI 1/1)"
          % (zd_m, blok_m, zd_my, blok_my))
    if (zd_m, blok_m) == (0, 0):
        hatalar.append("M1: yorum_ayrimi kolu OLDURULDUGU halde V1 YESIL kaldi -> "
                       "kolu olculen sey DEGIL; kapi kendi kolunu olcmuyor")
    if (zd_my, blok_my) != (1, 1):
        hatalar.append("M1-ATIF: mutant YAN EKSENI de dusurdu (V2 %d/%d, beklenen 1/1) "
                       "-> V1'in kirmizisi hedef kola ATFEDILEMEZ "
                       "([[ad-iki-rolde-mutanti-golgeler]])" % (zd_my, blok_my))

    print("-" * 74)
    print("VAKA=%d DUSEN=%d" % (vaka, len(hatalar)))
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅ — yorum CAGRI sayilmiyor · gercek yeni adim hala yakalaniyor · "
          "ayrim argv'den (yapidan) turuyor · hedef kol mutantla kanitli")
    return 0


if __name__ == "__main__":
    sys.exit(main())

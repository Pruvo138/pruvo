#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SERIT DERINLIK OLCERI (K314①, 27 Agu 2026) — "kac kirmizi KALDI" sorusunu cevaplar.

═══════════════════════════════════════════════════════════════════════════════
OLCULEN ARIZA (26 Agu 2026 — yayin 4,7 saat kapali)
═══════════════════════════════════════════════════════════════════════════════
Son yesil kosum `55056922` 08:22:49Z idi; ardindan 11 `failure` + 5 `cancelled`,
SIFIR success. Kirmizi ADIM her turda DEGISTI:

  1dc37b38 (08:06)  build:*Urun denetim kapisi* + serit-a2 *Katalog alan kapisi*
  a26732f3 (09:12)  *Urun denetim kapisi*
  1026298c (09:43)  *Varlik kabul testi*
  9473b09d/b5c1a3c4 *Uretici butunluk kapisi*
  4a450346..9f3f4060 *Varlik*
  e450697c (13:02)  *Kisisel veri korumasi testi*

DORT AYRI KIRMIZI ADIM, TEK KESINTI. Sebep: GitHub Actions bir job icinde ILK
kirmizi adimdan sonra kalan adimlari `skipped` yapar. Yani her tur KUYRUGUN
YALNIZ BASINI gosterir; arkada kac kirmizi durdugu HIC gorunmez. Her ev kendi
adimini duzeltip push etti ve "yayin acildi" sandi — acilmadi, cunku
*"kac kirmizi kaldi"* sorusunu cevaplayan bir OLCUM YOKTU.

OLCULEN KANIT (kosum 32995765098, serit-a2): adim 19 `failure`, adim 20-28
`skipped`. Dokuz kapi HIC KOSMADI ve o kosumdan "kalan derinlik" okunamadi.

═══════════════════════════════════════════════════════════════════════════════
🔴 TASARIM KARARI — HIZLI-BASARISIZLIK KALDIRILMADI, DERINLIK OLCULDU
═══════════════════════════════════════════════════════════════════════════════
Uc yol vardi:

  (a) Her kapiya `continue-on-error: true` + sonda toplayici.
      REDDEDILDI: (i) job'un adimlari SIRALI baglidir — `build.py` kirmizi
      yanarsa ondan SONRAKI 8 kapi `urun/` uretilmedigi icin OLCULEMEDI'ye
      duser ve GURULTU KASKADI olusur; gercek kirmizi sayisi SISER.
      (ii) Yesil kosumda da hicbir sey kazandirmaz, cunku yesil kosumda zaten
      hepsi kosuyor. (iii) 100+ satirlik YAML degisikligi, dort seritte.

  (b) Ayri bir "derinlik" job'u ayni kapilari paralel kosar.
      REDDEDILDI: IKIZ TANIM. Adim listesi iki yerde yasar ve sessizce ayrisir
      ([[ikiz-tanim-sessiz-ayrisma]]).

  (c) ✅ SECILEN: adim sirasi ve hizli-basarisizlik AYNEN KALIR. Job'un SONUNA
      `if: failure()` tasiyan TEK adim eklenir; o adim bu araci cagirir, arac
      job'un kapilarini DEPLOY.YML'DEN TURETIP kosturur ve KALAN KIRMIZI
      DERINLIGINI basar.
      * Bedel YALNIZ kirmizi kosumda odenir (yesil kosum bir saniye bile
        uzamaz). 26 Agu'da bedel 4,7 saatlik yayin kesintisiydi.
      * IKIZ TANIM YOK: kapi listesi ELDE TUTULMAZ, `.github/workflows/deploy.yml`
        okunarak TURETILIR. Yarin eklenen kapi kendiliginden olcume girer.
      * Hizli-basarisizlik BIR DEGERDIR ve korunur: job yine ilk kirmizida
        `failure` hukmunu alir; olcum o hukumden SONRA kosar.

═══════════════════════════════════════════════════════════════════════════════
YAN ETKI KAPISI — "OLCMEK ICIN CANLI SISTEME DOKUNMA"
═══════════════════════════════════════════════════════════════════════════════
Bazi adimlar YENIDEN KOSTURULAMAZ (canli D1'e yazar, secret ister). Bunlar
ADIMIN KENDI `env:` blogunda ISARETLENIR:

    env:
      SERIT_DERINLIK: atla
      SERIT_DERINLIK_SEBEP: "canli D1'e yazar"

🔴 SESSIZ KIRPMA YOK: atlanan/olculemeyen her adim ADIYLA basilir ve kendi
sayacina yazilir (`..._ATLANDI` / `..._OLCULEMEDI`). "Kapsadim" gorunumu
uretmek yasak — bir adim olculemediyse hukum "yesil" DEGIL "OLCULEMEDI"dir.

═══════════════════════════════════════════════════════════════════════════════
CIKTI SOZLESMESI (son satirlar — makine okur)
═══════════════════════════════════════════════════════════════════════════════
    <JOB>_KIRMIZI=<n>      kalan + ilk kirmizi TOPLAM kirmizi kapi sayisi
    <JOB>_YESIL=<n>
    <JOB>_OLCULEMEDI=<n>
    <JOB>_ATLANDI=<n>
    <JOB>_KAPI=<n>         olcum kapsamindaki toplam kapi adimi

`<JOB>` = job id'sinin buyuk harfli, `-` yerine `_` konmus hali. Yani
`serit-a3` icin jeton BIREBIR `SERIT_A3_KIRMIZI=<n>`'dir. Jeton ELLE
YAZILMAZ, job adindan TURETILIR — ikinci bir tablo tutulmaz.

CIKIS KODU: 0 = olcum YAPILDI (rapor uretildi) · 2 = OLCULEMEDI (YAML
ayristirilamadi / job yok / arac icice cagrildi). Aracin rc'si "serit yesil mi"
sorusunu CEVAPLAMAZ — o soruyu job'un kendi adimlari cevaplar; bu arac yalnizca
DERINLIGI RAPORLAR. (Hukum karistirmasi: [[rc-hukmu-kapi-imzasini-ezer]].)

KOSUM:
    python3 tools/serit-derinlik.py --serit serit-a3
    python3 tools/serit-derinlik.py --serit serit-a3 --kuru     # kosturmadan siniflar
    python3 tools/serit-derinlik.py --kendini-test              # fikstur bataryasi
"""
import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOY_YML = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

OK = 0
OLCULEMEDI_RC = 2

# Ozyineleme kapisi: arac kendi kosturdugu adimlar icinden TEKRAR cagrilamaz.
IC_KOSUM = "PRUVO_SERIT_DERINLIK"
# is-akisi-kapisi.py K80 kolu DEGISEN her CI adimini hedef commitin agacinda
# 300 sn tavaniyla kosturur. Bu aracin GERCEK isi bir seridin TUM kapilarini
# kosturmaktir — 300 sn'ye SIGMAZ ve K80 onu OLCULEMEDI sayip push'u bloklar.
# K80 kendi ic kosumunu bu degiskenle isaretler; o kosumda arac FIKSTUR
# BATARYASINI kosar (hizli, deterministik) ve rc=0 doner. Ayni kacis is-akisi-
# kapisi.py'nin KENDISI icin de kullanilir (satir ~5846) — yeni mekanizma DEGIL.
K80_IC_KOSUM = "PRUVO_K80_IC_KOSUM"

# Kapi adimlarinin izin verilen bicimi. Kaba + FAIL-CLOSED: parser taklidi YOK.
YORUMLAYICI = ("python3", "node")
BETIK_KOKLERI = ("tools" + os.sep, "shop" + os.sep, "jenerator" + os.sep)
BETIK_UZANTILARI = (".py", ".js", ".mjs", ".cjs")
META = re.compile(r"[;&|`$<>]")

ATLA_ANAHTARI = "SERIT_DERINLIK"
ATLA_DEGERI = "atla"
ATLA_SEBEP_ANAHTARI = "SERIT_DERINLIK_SEBEP"

# Hukum siniflari
KIRMIZI = "KIRMIZI"
YESIL = "YESIL"
OLCULEMEDI = "OLCULEMEDI"
ATLANDI = "ATLANDI"
KENDISI = "KENDISI"
KURULUM = "KURULUM"      # `uses:` adimi ya da run'siz adim — kapi DEGIL

ADIM_TAVAN_SN = 900


class Olculemedi(Exception):
    """Hukum kuracak kadar veri yok. YESIL DEGILDIR."""


# --------------------------------------------------------------------------- YAML
def _yaml_yukle(metin):
    """YAML ayristirici YOKSA fail-closed. CI'da `pip install pyyaml` kurulu."""
    try:
        import yaml  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover - CI'da kurulu
        raise Olculemedi("PyYAML yok (%s) — is akisi ayristirilamadi" % e)
    try:
        return yaml.safe_load(metin)
    except Exception as e:  # noqa: BLE001
        raise Olculemedi("YAML ayristirilamadi: %s" % e)


def _adimlar(yaml_metni, job_id):
    govde = _yaml_yukle(yaml_metni)
    if not isinstance(govde, dict):
        raise Olculemedi("is akisi kok mapping DEGIL")
    jobs = govde.get("jobs")
    if not isinstance(jobs, dict):
        raise Olculemedi("`jobs` mapping YOK")
    if job_id not in jobs:
        raise Olculemedi("`%s` isi bu is akisinda YOK (mevcut: %s)"
                         % (job_id, ", ".join(sorted(str(k) for k in jobs))))
    job = jobs[job_id]
    if not isinstance(job, dict):
        raise Olculemedi("`%s` isi mapping DEGIL" % job_id)
    adimlar = job.get("steps")
    if not isinstance(adimlar, list):
        raise Olculemedi("`%s` isinde `steps` listesi YOK" % job_id)
    return adimlar


# --------------------------------------------------------------------------- sinif
def _komut_satirlari(run):
    """`run:` govdesini ANLAMLI komut satirlarina ayirir (yorum/bos satir duser)."""
    satirlar = []
    for ham in run.splitlines():
        s = ham.strip()
        if not s or s.startswith("#"):
            continue
        satirlar.append(s)
    return satirlar


def _argv_coz(satir):
    """Duz yerel `python3 <betik>` / `node <betik>` satirini argv'ye cevirir.

    KABA + FAIL-CLOSED (K80'in `_k80_argv` idiomuyla AYNI eksen, ayri govde —
    o fonksiyon pre-push kapisinin ic organidir, buraya IMPORT edilmez ki iki
    kapinin arizasi birbirine bulasmasin). Supheli her bicim Olculemedi'dir.
    """
    if META.search(satir) or "\\" in satir:
        raise Olculemedi("kabuk metakarakteri/ifadesi: %r" % satir)
    try:
        parcalar = shlex.split(satir)
    except ValueError as e:
        raise Olculemedi("satir ayristirilamadi (%s): %r" % (e, satir))
    if not parcalar:
        raise Olculemedi("bos komut")
    if parcalar[0] not in YORUMLAYICI:
        raise Olculemedi("yorumlayici `%s` degil: %r" % ("/".join(YORUMLAYICI), satir))
    betikler = [p for p in parcalar[1:]
                if p.endswith(BETIK_UZANTILARI) and not p.startswith("-")]
    if len(betikler) != 1:
        raise Olculemedi("tek betik yolu bulunamadi: %r" % satir)
    betik = betikler[0]
    norm = os.path.normpath(betik)
    if os.path.isabs(norm) or not norm.startswith(BETIK_KOKLERI):
        raise Olculemedi("betik depo koklerinin (%s) disinda: %r"
                         % ("/".join(k.rstrip(os.sep) for k in BETIK_KOKLERI), betik))
    return parcalar


def _kendi_araci_mi(satirlar):
    return any("serit-derinlik.py" in s for s in satirlar)


def adim_sinifla(adim):
    """Tek adimi siniflar -> (sinif, ad, argv_listesi, tani).

    argv_listesi YALNIZ sinif==None (kosulabilir) iken doludur; sinif dolu ise
    adim KOSULMAZ ve dogrudan o sinifla raporlanir.
    """
    ad = str(adim.get("name") or adim.get("uses") or "(adsiz adim)")
    if "run" not in adim:
        return KURULUM, ad, [], "kurulum/`uses` adimi — kapi degil"
    run = adim.get("run")
    if not isinstance(run, str) or not run.strip():
        return OLCULEMEDI, ad, [], "`run` bos/gecersiz"

    env = adim.get("env")
    if isinstance(env, dict) and str(env.get(ATLA_ANAHTARI, "")).strip() == ATLA_DEGERI:
        sebep = str(env.get(ATLA_SEBEP_ANAHTARI, "")).strip() or "(sebep beyan edilmemis)"
        return ATLANDI, ad, [], sebep

    satirlar = _komut_satirlari(run)
    if not satirlar:
        return OLCULEMEDI, ad, [], "`run` icinde anlamli komut satiri YOK"
    if _kendi_araci_mi(satirlar):
        return KENDISI, ad, [], "olcum adiminin kendisi (ozyineleme kapisi)"

    argvler = []
    for s in satirlar:
        try:
            argvler.append(_argv_coz(s))
        except Olculemedi as e:
            return OLCULEMEDI, ad, [], str(e)
    return None, ad, argvler, ""


# --------------------------------------------------------------------------- kosum
def _gercek_kosucu(argv, kok, tavan=ADIM_TAVAN_SN):
    """Gercek alt surec. Donus: (rc, son_satir)."""
    env = dict(os.environ)
    env[IC_KOSUM] = "1"
    try:
        p = subprocess.run(argv, cwd=kok, capture_output=True, text=True,
                           timeout=tavan, env=env)
    except FileNotFoundError as e:
        return None, "yorumlayici/betik BULUNAMADI: %s" % e
    except subprocess.TimeoutExpired:
        return None, "%d sn tavani asildi" % tavan
    ham = (p.stdout or "") + (p.stderr or "")
    satirlar = [s for s in ham.splitlines() if s.strip()]
    return p.returncode, (satirlar[-1][:200] if satirlar else "(cikti BOS)")


def _akis_yok(_kayit):
    return None


def serit_hukumleri(yaml_metni, job_id, kok=ROOT, kosucu=None, kuru=False,
                    akis=_akis_yok):
    """Job'un adimlarini siniflar ve (kuru degilse) kosturur.

    kosucu enjekte edilebilir -> fikstur bataryasi GERCEK is akisina muhtac
    olmadan hukum uretir. GERCEK tarama ve fikstur AYNI govdeyi kullanir:
    bu fonksiyon no-op yapilirsa fiksturler de kirmizi yanar (olu-olcer koruma).
    """
    kosucu = kosucu or _gercek_kosucu
    sonuc = []

    def _ekle(kayit):
        sonuc.append(kayit)
        akis(kayit)
        return kayit

    for adim in _adimlar(yaml_metni, job_id):
        if not isinstance(adim, dict):
            _ekle({"sinif": OLCULEMEDI, "ad": "(mapping olmayan adim)",
                   "tani": "adim mapping DEGIL", "rc": None})
            continue
        sinif, ad, argvler, tani = adim_sinifla(adim)
        if sinif is not None:
            _ekle({"sinif": sinif, "ad": ad, "tani": tani, "rc": None})
            continue
        if kuru:
            _ekle({"sinif": "KOSULABILIR", "ad": ad, "rc": None,
                   "tani": " && ".join(" ".join(a) for a in argvler)})
            continue
        # Cok satirli `run:` blogu: satirlar `bash -e` ile SIRAYLA kosar, ilk
        # sifirdisi adimi dusurur. Ayni semantik burada da korunur.
        rc, son = None, ""
        for argv in argvler:
            rc, son = kosucu(argv, kok)
            if rc != 0:
                break
        if rc is None:
            _ekle({"sinif": OLCULEMEDI, "ad": ad, "tani": son, "rc": None})
        else:
            _ekle({"sinif": KIRMIZI if rc else YESIL, "ad": ad, "tani": son, "rc": rc})
    return sonuc


def jeton_oneki(job_id):
    """`serit-a3` -> `SERIT_A3`. Jeton job adindan TURETILIR, elle yazilmaz."""
    return re.sub(r"[^A-Za-z0-9]", "_", str(job_id)).upper()


def sayaclar(hukumler):
    say = {KIRMIZI: 0, YESIL: 0, OLCULEMEDI: 0, ATLANDI: 0}
    for h in hukumler:
        if h["sinif"] in say:
            say[h["sinif"]] += 1
    return say


def rapor_bas(job_id, hukumler, yaz=print):
    onek = jeton_oneki(job_id)
    yaz("=== SERIT DERINLIK OLCUMU — is `%s` ===" % job_id)
    for h in hukumler:
        if h["sinif"] == KURULUM:
            continue
        yaz("  [%-11s] %s" % (h["sinif"], h["ad"]))
        if h.get("tani"):
            yaz("               %s" % h["tani"])
    say = sayaclar(hukumler)
    kapi = say[KIRMIZI] + say[YESIL] + say[OLCULEMEDI] + say[ATLANDI]
    yaz("")
    yaz("%s_KIRMIZI=%d" % (onek, say[KIRMIZI]))
    yaz("%s_YESIL=%d" % (onek, say[YESIL]))
    yaz("%s_OLCULEMEDI=%d" % (onek, say[OLCULEMEDI]))
    yaz("%s_ATLANDI=%d" % (onek, say[ATLANDI]))
    yaz("%s_KAPI=%d" % (onek, kapi))
    return say


# ═══════════════════════════════════════════════════════════════════════════════
# FIKSTUR BATARYASI
# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 K2 (MUTANT-DERINLIK) BURADA CIVILENIR: ayni is akisi metni uzerinde YALNIZ
# kosucunun hukmu degistirilir. Kontrol (hepsi yesil) 0, bir kirmizi 1, iki
# kirmizi 2 basmalidir. Sayi kosucudan degil OLCERDEN gelir; olcer olurse
# (or. `return []`) ucu de kirmizi yanar.

_FIKSTUR_YML = """
name: fikstur
on: [push]
jobs:
  serit-a3:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Kurulum
        run: pip install boto3 pyyaml
      - name: Kapi bir
        run: python3 tools/fikstur-bir.py
      - name: Kapi iki
        run: python3 tools/fikstur-iki.py
      - name: Kapi uc (cok satirli)
        run: |
          python3 tools/fikstur-uc.py
          node shop/test/fikstur-uc.mjs
      - name: Yan etkili adim
        env:
          SERIT_DERINLIK: atla
          SERIT_DERINLIK_SEBEP: "canli D1'e yazar"
        run: python3 tools/fikstur-yan-etki.py
      - name: Kabuk blogu
        run: |
          if [ -z "$X" ]; then echo yok; fi
      - name: Serit derinlik olcumu
        if: failure()
        run: python3 tools/serit-derinlik.py --serit serit-a3
"""


def _sahte_kosucu(kirmizi_betikler):
    """Adi verilen betikler rc=1, digerleri rc=0 doner."""
    def _kos(argv, kok):  # noqa: ARG001
        for p in argv:
            if any(p.endswith(k) for k in kirmizi_betikler):
                return 1, "IDDIA DUSTU (fikstur)"
        return 0, "OK (fikstur)"
    return _kos


def _fikstur_derinlik(kirmizi_betikler):
    h = serit_hukumleri(_FIKSTUR_YML, "serit-a3", kok="/olmayan",
                        kosucu=_sahte_kosucu(kirmizi_betikler))
    return h, sayaclar(h)


def _gercek_kosucu_canlilik_fiksturu():
    """OLU-KOSUCU KORUMASI: sahte kosucu her seyi yesil sayan bir yalanci olabilir.

    Bu fikstur GERCEK `_gercek_kosucu`yu gecici bir agacta, GERCEK alt surecle
    kosturur: biri `sys.exit(0)`, biri `sys.exit(1)`, biri HIC YOK. Uc hukum de
    ayrisiyorsa kosucu canlidir. ([[prob-gercek-isi-taklit-etmeli]])
    """
    hatalar = []
    with tempfile.TemporaryDirectory(prefix="pruvo-serit-derinlik-") as d:
        araclar = os.path.join(d, "tools")
        os.makedirs(araclar)
        with open(os.path.join(araclar, "yesil.py"), "w", encoding="utf-8") as f:
            f.write("import sys\nprint('YESIL SATIRI')\nsys.exit(0)\n")
        with open(os.path.join(araclar, "kirmizi.py"), "w", encoding="utf-8") as f:
            f.write("import sys\nprint('KIRMIZI SATIRI')\nsys.exit(1)\n")
        rc_y, son_y = _gercek_kosucu(["python3", "tools/yesil.py"], d, tavan=60)
        rc_k, son_k = _gercek_kosucu(["python3", "tools/kirmizi.py"], d, tavan=60)
        rc_yok, son_yok = _gercek_kosucu(["python3", "tools/yok.py"], d, tavan=60)
    if rc_y != 0 or "YESIL SATIRI" not in son_y:
        hatalar.append("GERCEK KOSUCU OLU: yesil betik rc=%r son=%r" % (rc_y, son_y))
    if rc_k != 1 or "KIRMIZI SATIRI" not in son_k:
        hatalar.append("GERCEK KOSUCU OLU: kirmizi betik rc=%r son=%r" % (rc_k, son_k))
    # Var olmayan betik: python3 VARDIR, betik yoktur -> rc != 0. Bu KIRMIZI'dir
    # (adim gercek CI'da da kirmizi yanardi), OLCULEMEDI degil.
    if rc_yok == 0:
        hatalar.append("GERCEK KOSUCU OLU: var olmayan betik rc=0 dondu (son=%r)" % son_yok)
    return hatalar


_UCTAN_UCA_YML = """
name: fikstur
on: [push]
jobs:
  serit-a3:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Kapi bir
        run: python3 tools/g1.py
      - name: Kapi iki
        run: python3 tools/g2.py
      - name: Kapi uc
        run: python3 tools/g3.py
"""


def _uctan_uca_derinlik_fiksturu():
    """K2 MUTANT-DERINLIK — SAHTE kosucuyla DEGIL, GERCEK ALT SURECLERLE.

    Sahte kosucu ile olculen 0/1/2, olcerin ARITMETIGINI kanitlar ama
    "gercek bir CI adimi kirmizi yaninca sayi artiyor mu" sorusunu CEVAPLAMAZ
    ([[prob-gercek-isi-taklit-etmeli]]). Bu fikstur gecici bir agacta GERCEK
    betikler yazar, GERCEK `python3` alt sureclerini kosturur ve ayni uc hukmu
    (0 / 1 / 2 + hedef-kol atfi) uctan uca olcer. Depoya DOKUNMAZ.
    """
    hatalar = []
    with tempfile.TemporaryDirectory(prefix="pruvo-serit-e2e-") as d:
        araclar = os.path.join(d, "tools")
        os.makedirs(araclar)

        def _yaz(ad, kod):
            with open(os.path.join(araclar, ad), "w", encoding="utf-8") as f:
                f.write(kod)

        def _olc(kirmizilar):
            for ad in ("g1.py", "g2.py", "g3.py"):
                _yaz(ad, "import sys\nprint('%s KOSTU')\nsys.exit(%d)\n"
                     % (ad, 1 if ad in kirmizilar else 0))
            h = serit_hukumleri(_UCTAN_UCA_YML, "serit-a3", kok=d)
            return h, sayaclar(h)

        # KONTROL — hepsi yesil
        h0, s0 = _olc(set())
        if s0[KIRMIZI] != 0 or s0[YESIL] != 3:
            hatalar.append("E2E-KONTROL: gercek sureclerle hepsi yesilken "
                           "KIRMIZI=%d YESIL=%d (beklenen 0/3)" % (s0[KIRMIZI], s0[YESIL]))
        # M1 — tek kirmizi
        h1, s1 = _olc({"g2.py"})
        if s1[KIRMIZI] != 1:
            hatalar.append("E2E-M1: gercek surecte tek kirmizida KIRMIZI=%d (beklenen 1)"
                           % s1[KIRMIZI])
        if [x["ad"] for x in h1 if x["sinif"] == KIRMIZI] != ["Kapi iki"]:
            hatalar.append("E2E-M1 ATIF: kirmizi yanan adim %r (beklenen ['Kapi iki'])"
                           % [x["ad"] for x in h1 if x["sinif"] == KIRMIZI])
        # M2 — iki kirmizi: 1 -> 2
        h2, s2 = _olc({"g2.py", "g3.py"})
        if s2[KIRMIZI] != 2:
            hatalar.append("E2E-M2: ikinci adim da kirmiziya cevrilince KIRMIZI=%d "
                           "(beklenen 2) — DERINLIK ARTMIYOR" % s2[KIRMIZI])
        if sorted(x["ad"] for x in h2 if x["sinif"] == KIRMIZI) != ["Kapi iki", "Kapi uc"]:
            hatalar.append("E2E-M2 ATIF: kirmizi kume %r (beklenen ['Kapi iki','Kapi uc'])"
                           % sorted(x["ad"] for x in h2 if x["sinif"] == KIRMIZI))
        # JETON: gercek kosumda da `SERIT_A3_KIRMIZI=2` basiliyor mu
        satirlar = []
        rapor_bas("serit-a3", h2, yaz=satirlar.append)
        if "SERIT_A3_KIRMIZI=2" not in satirlar:
            hatalar.append("E2E-JETON: gercek kosumda `SERIT_A3_KIRMIZI=2` BASILMADI")
        # 🔴 KUYRUGUN GORUNURLUGU — kalemin CEKIRDEK IDDIASI: ilk kirmizidan SONRAKI
        # adimin hukmu de OKUNABILIYOR mu? GitHub Actions'ta `Kapi uc` `skipped`
        # olurdu; olcerde OKUNUR olmali. Bu kol dususe gecerse arac 26 Agu'nun
        # tam da gizledigi seyi yeniden gizliyor demektir.
        h3, _s3 = _olc({"g1.py", "g3.py"})
        hukumler = {x["ad"]: x["sinif"] for x in h3}
        if hukumler.get("Kapi uc") != KIRMIZI or hukumler.get("Kapi iki") != YESIL:
            hatalar.append("E2E-KUYRUK: ILK kirmizidan (Kapi bir) SONRAKI adimlarin "
                           "hukmu okunamadi -> %r" % hukumler)
    return hatalar


def kendini_test():
    hatalar = []

    # --- K2 MUTANT-DERINLIK: 0 / 1 / 2 -------------------------------------
    _h0, s0 = _fikstur_derinlik([])
    if s0[KIRMIZI] != 0:
        hatalar.append("K2-KONTROL: hepsi yesilken KIRMIZI=%d (beklenen 0)" % s0[KIRMIZI])
    _h1, s1 = _fikstur_derinlik(["fikstur-bir.py"])
    if s1[KIRMIZI] != 1:
        hatalar.append("K2-M1: tek kirmizida KIRMIZI=%d (beklenen 1)" % s1[KIRMIZI])
    _h2, s2 = _fikstur_derinlik(["fikstur-bir.py", "fikstur-iki.py"])
    if s2[KIRMIZI] != 2:
        hatalar.append("K2-M2: iki kirmizida KIRMIZI=%d (beklenen 2)" % s2[KIRMIZI])
    # HEDEF-KOL ATFI (K182): sayinin artmasi yetmez, ARTAN ADIMIN ADI dogru olmali.
    kirmizi_adlar = sorted(h["ad"] for h in _h2 if h["sinif"] == KIRMIZI)
    if kirmizi_adlar != ["Kapi bir", "Kapi iki"]:
        hatalar.append("K2-ATIF: kirmizi yanan adimlar %r (beklenen ['Kapi bir','Kapi iki'])"
                       % kirmizi_adlar)
    # Cok satirli adim: ikinci satir kirmizi ise ADIM kirmizidir.
    _h3, s3 = _fikstur_derinlik(["fikstur-uc.mjs"])
    if s3[KIRMIZI] != 1 or [h["ad"] for h in _h3 if h["sinif"] == KIRMIZI] != \
            ["Kapi uc (cok satirli)"]:
        hatalar.append("COK-SATIR: ikinci satirin kirmizisi adimi dusurmedi (%r)" % (s3,))

    # --- SINIFLAMA: atlanan / olculemeyen / kendisi ADIYLA gorunur ----------
    ad_sinif = {h["ad"]: h["sinif"] for h in _h0}
    if ad_sinif.get("Yan etkili adim") != ATLANDI:
        hatalar.append("ATLA: `SERIT_DERINLIK: atla` isaretli adim %r sayildi"
                       % ad_sinif.get("Yan etkili adim"))
    if ad_sinif.get("Kabuk blogu") != OLCULEMEDI:
        hatalar.append("OLCULEMEDI: kabuk blogu %r sayildi" % ad_sinif.get("Kabuk blogu"))
    if ad_sinif.get("Kurulum") != OLCULEMEDI:
        hatalar.append("OLCULEMEDI: `pip install` adimi %r sayildi (yorumlayici degil)"
                       % ad_sinif.get("Kurulum"))
    if ad_sinif.get("Serit derinlik olcumu") != KENDISI:
        hatalar.append("OZYINELEME: olcum adimi kendini %r sayildi"
                       % ad_sinif.get("Serit derinlik olcumu"))
    if s0[OLCULEMEDI] == 0:
        hatalar.append("SESSIZ KIRPMA: olculemeyen adim VAR ama sayac 0")
    if s0[ATLANDI] != 1:
        hatalar.append("SESSIZ KIRPMA: ATLANDI=%d (beklenen 1)" % s0[ATLANDI])

    # --- JETON ADI: `serit-a3` -> `SERIT_A3_KIRMIZI` -----------------------
    if jeton_oneki("serit-a3") != "SERIT_A3":
        hatalar.append("JETON: `serit-a3` -> %r (beklenen SERIT_A3)" % jeton_oneki("serit-a3"))
    satirlar = []
    rapor_bas("serit-a3", _h1, yaz=satirlar.append)
    if "SERIT_A3_KIRMIZI=1" not in satirlar:
        hatalar.append("JETON: `SERIT_A3_KIRMIZI=1` satiri BASILMADI (%r)" % satirlar[-6:])

    # --- FAIL-CLOSED: olmayan is / bozuk YAML -> OLCULEMEDI ---------------
    for etiket, cagri in (
            ("olmayan is", lambda: serit_hukumleri(_FIKSTUR_YML, "yok-boyle-is")),
            ("bozuk YAML", lambda: serit_hukumleri("{{{", "serit-a3")),
            ("jobs YOK", lambda: serit_hukumleri("name: x\non: [push]\n", "serit-a3"))):
        try:
            cagri()
        except Olculemedi:
            pass
        else:
            hatalar.append("FAIL-CLOSED: %s OLCULEMEDI vermedi" % etiket)

    # --- GERCEK KOSUCU CANLI MI -------------------------------------------
    hatalar.extend(_gercek_kosucu_canlilik_fiksturu())

    # --- K2 UCTAN UCA: GERCEK ALT SURECLERLE 0 / 1 / 2 --------------------
    hatalar.extend(_uctan_uca_derinlik_fiksturu())

    # --- CANLI IS AKISI AYRISTIRILABILIYOR MU (kuru sinif) ----------------
    # 🔴 Bu kol CANLI deploy.yml'i okur ama HICBIR kapiyi KOSTURMAZ. Amaci:
    # is akisi bicimi degisince (or. yeni bir `run:` yazimi) olcerin SESSIZCE
    # her adimi OLCULEMEDI'ye dusurmesini yakalamak.
    try:
        with open(DEPLOY_YML, encoding="utf-8") as f:
            canli = f.read()
    except OSError as e:
        hatalar.append("CANLI IS AKISI OKUNAMADI: %s" % e)
    else:
        for job_id, taban in (("serit-a3", 30), ("serit-a2", 15), ("build", 10)):
            try:
                h = serit_hukumleri(canli, job_id, kuru=True)
            except Olculemedi as e:
                hatalar.append("CANLI SINIF OLCULEMEDI (%s): %s" % (job_id, e))
                continue
            kosulabilir = sum(1 for x in h if x["sinif"] == "KOSULABILIR")
            print("  CANLI KURU SINIF %-9s KOSULABILIR=%d ATLANDI=%d OLCULEMEDI=%d"
                  % (job_id, kosulabilir,
                     sum(1 for x in h if x["sinif"] == ATLANDI),
                     sum(1 for x in h if x["sinif"] == OLCULEMEDI)))
            # 🔴 TABAN SAYIYLA CIVILENIR ([[batarya-kapsam-tabani-sayiyla-civilenir]]):
            # cozulebilen kapi sayisi bu tabanin ALTINA duserse olcer korlesmis
            # demektir ve bunu hicbir yesil test gostermez.
            if kosulabilir < taban:
                hatalar.append("CANLI KAPSAM DUSTU (%s): KOSULABILIR=%d < taban %d — "
                               "olcer bicim degisikliginde korlesmis olabilir"
                               % (job_id, kosulabilir, taban))
    return hatalar


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Serit derinlik olceri (K314①)")
    ap.add_argument("--serit", help="olculecek job id (or. serit-a3)")
    ap.add_argument("--kuru", action="store_true",
                    help="kapilari KOSTURMA, yalniz sinifla")
    ap.add_argument("--kendini-test", action="store_true", help="fikstur bataryasi")
    a = ap.parse_args()

    if a.kendini_test or os.environ.get(K80_IC_KOSUM) == "1":
        if os.environ.get(K80_IC_KOSUM) == "1" and not a.kendini_test:
            print("K80 IC KOSUMU — serit KOSTURULMAZ (300 sn tavani), FIKSTUR "
                  "BATARYASI kosuyor. Gercek olcum yalniz `if: failure()` adiminda.")
        hatalar = kendini_test()
        for h in hatalar:
            print("  ❌ %s" % h)
        print("SERIT DERINLIK OZ-TEST: %s (%d bulgu)"
              % ("GECTI" if not hatalar else "KIRMIZI", len(hatalar)))
        return OK if not hatalar else 1

    if not a.serit:
        print("KULLANIM: python3 tools/serit-derinlik.py --serit <job-id>")
        return OLCULEMEDI_RC

    if os.environ.get(IC_KOSUM) == "1":
        print("OLCULEMEDI — serit derinlik olceri ICICE cagrildi (ozyineleme kapisi).")
        return OLCULEMEDI_RC

    # 🔴 CANLI AKIS: her adimin hukmu OLCULUR OLCULMEZ basilir. Sebep: bu olcum
    # KIRMIZI kosumda calisir ve uzun surer; bir zaman asimi/iptal hukumleri
    # yutarsa 26 Agu'nun korlugu geri gelir. Akan satirlar sonda TABLO olarak
    # yeniden ozetlenir (jeton satirlari YALNIZ sonda).
    def _akis(kayit):
        if kayit["sinif"] != KURULUM:
            sys.stdout.write("  … [%-11s] %s\n" % (kayit["sinif"], kayit["ad"]))
            sys.stdout.flush()

    try:
        with open(DEPLOY_YML, encoding="utf-8") as f:
            metin = f.read()
        hukumler = serit_hukumleri(metin, a.serit, kok=ROOT, kuru=a.kuru, akis=_akis)
    except (OSError, Olculemedi) as e:
        print("OLCULEMEDI — %s" % e)
        print("%s_KIRMIZI=OLCULEMEDI" % jeton_oneki(a.serit))
        return OLCULEMEDI_RC

    say = rapor_bas(a.serit, hukumler)
    if say[OLCULEMEDI]:
        print("⚠️ %d adim OLCULEMEDI — bu sayi YESIL DEGILDIR; yukarida ADIYLA basildi."
              % say[OLCULEMEDI])
    return OK


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HACIM-TAM-TAKIM ON-KOSUL + PAKET BUTUNLUK KABUL TESTI (K377 · K378).

NEYI OLCER
==========
`.github/workflows/nobet.yml::hacim-tam-takim` isi 2026-07-16'da EMEKLI EDILEN
`ONIZLEME_PAKET_B64` secret'ini fail-closed on-kosul sayiyordu. Secret repoda YOK ve
OLMAYACAK (Okan karari; tek kaynak tools/onizleme-paket-yukle.py modul sonu notu), bu
yuzden is her elle tetikte on-kosulda `exit 1` verip checkout'a HIC GELMIYORDU. Kol
"dogru" davraniyordu (gurultulu kirmizi) ama YANLIS SARTA capalanmisti: isin tamami
aylarca OLCULMEDI. (K377, 7 Eyl 2026 — on-kosul R2 uclusune capalandi.)

K378 (7 Eyl 2026) o isin IKINCI yarisini olcer: BUTUNLUK adimi. Eski hali yalniz
`test -f eslem-ozel.json` idi — arsivin ACILDIGINI kanitlar, TAM oldugunu DEGIL.
Kayit (onizleme/derleyici/paket-parmakizi.json) 26 dosyanin sha256'sini tasir
(25 *.scad + eslem-ozel.json); tek dosyaya bakan kol, 25 ureteci EKSIK ya da BOZUK
gelen bir paketi "gecti" diye gecirirdi. Yeni hali ORTAK dogrulayiciyi cagirir:
`tools/onizleme-kapisi.py parmakizi-dogrula --dizin ... --paket-anahtar ...` — ayni
arac onizleme-imaj.yml'de de kosar, IKINCI bir dogrulayici YAZILMADI.

Bu test o kollari olcer — YAML'i okur, `run:` govdelerini KAYNAKTAN cikarir ve IZOLE
gecici bir dizinde kosturur. Ikinci bir kopya yazmaz: govde bozulursa/silinirse test
onu goremez degil, KIRMIZI yanar.

KOLLAR
------
  K1  R2 on-kosulu, kimlik BOS        -> rc!=0 + eksik secret ADLARI basilir  (M1 hedefi)
  K2  R2 on-kosulu, kimlik DOLU       -> rc==0            (taban; yoksa K1 totoloji)
  K3  Butunluk, paket TAM (26/26)     -> rc==0 VE SAYI basilir ("26 dosya", "25 .scad")
  K4  Butunluk, 1 *.scad EKSIK        -> rc!=0 + EKSIK DOSYA ADI basilir      (M2 hedefi)
  K5  Butunluk, 1 dosya ICERIGI BOZUK -> rc!=0 + BOZUK DOSYA ADI basilir
  K6  Butunluk, eslem-ozel.json YOK   -> rc!=0 + ADIYLA (eski tek-dosya kolunun ardili)
  K7  Butunluk, CI BASKA anahtar cekti-> rc!=0 (kayit<->R2 anahtar caprazi)   (M3 hedefi)
  K8  NON-GROWTH: hacim-tam-takim govdesinde `ONIZLEME_PAKET_B64` ATFI 0 olmali
  K9  IKIZ CEKME TANIMI YOK: `aws s3 cp` gecen is-akisi dosyasi sayisi 0 — cekme
      mantigi YALNIZ .github/actions/gizli-paket-cek/action.yml icinde yasar; oradaki
      sayi ise >=1 olmali (kolun CANLI oldugunu ayrica kanitlar)
  K10 IKIZ BUTUNLUK TANIMI YOK: `parmakizi-dogrula` cagrisi HER IKI is akisinda da
      (nobet.yml + onizleme-imaj.yml) >=1 olmali (iki kol da CANLI) VE hacim-tam-takim
      govdesinde elle yazilmis ikinci bir ozet mantigi (`sha256sum` / `hashlib`) 0 olmali
  K11 OpenSCAD surum turetme, GERCEK Dockerfile -> rc==0 VE GITHUB_OUTPUT'a yazilan
      dosya/surum bu testin Dockerfile'dan BAGIMSIZ okudugu `ARG OPENSCAD_DOSYA` ile ayni
  K12 OpenSCAD surum turetme, ARG YOK      -> rc!=0 + "adet=0"            (M4 hedefi)
  K13 OpenSCAD surum turetme, ARG IKI KEZ  -> rc!=0 + "adet=2"
  K14 OpenSCAD kurulumu PINLI: kurulum adimi turetilen ciktiyi `env` ile alir, indirme
      URL'si `$OPENSCAD_DOSYA`, `--version` pine karsi dogrulanir VE isin hicbir
      govdesinde snapshot dizini LISTELENMEZ (eski "en son nightly" secimi) (M5 hedefi)

K4/K5 ikilisi, bu turun ONARDIGI SINIFIN ta kendisidir: "1 dosya gordum, gectim"
davranisi geri gelirse ikisi birden KIRMIZI yanar (M2 mutanti bunu kanitlar).

MUTANT KANITI (K182 — her mutant HEDEF kolu OLDURDUGUNU AYRICA kanitlar)
------------------------------------------------------------------------
`--mutant m1|m2|m3` govdeyi IZOLE KOPYADA yamalar (kaynak dosyaya DOKUNMAZ) ve kollari
yeniden kosar. Beklenen: hedef kol TABANDA yesilken mutantla KIRMIZI olur. Mutantli
sonuc tabanla AYNI cikarsa test `MUTANT ULASMADI` der ve rc=2 (OLCULEMEDI) doner —
sessizce yesile DUSMEZ.

  m1: on-kosul govdesindeki `exit 1` -> `exit 0`   (fail-closed kol susturulur)
  m2: butunluk govdesi ESKI HALINE dondurulur (yalniz `test -f eslem-ozel.json`)
      -> K4 ve K5 birlikte olmeli; hedef K4
  m3: butunluk govdesinden `--paket-anahtar` bayragi dusurulur -> hedef K7
  m4: OpenSCAD surum turetme govdesinde `exit 1` -> `exit 0` -> hedef K12 (+K13)
  m5: OpenSCAD kurulum govdesi ESKI "en son snapshot" secimine dondurulur -> hedef K14

FIKSTUR — IZOLE VE SENTETIK: butunluk kollari gecici bir dizinde kurulur; icine
kaynaktan KOPYALANAN tools/onizleme-kapisi.py + 26 SENTETIK dosya konur ve parmakizi
kaydi aracin KENDI yazicisiyla (`parmakizi-yaz`) uretilir. Gercek pakete, gercek
kayda ve gercek ev yoluna YAZILMAZ; silme cagrisi YAPILMAZ (tum kosumlar
tempfile.TemporaryDirectory() icinde).

rc: 0 = YESIL · 1 = KIRMIZI · 2 = OLCULEMEDI (ayristirici yok / mutant ulasmadi)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOBET = os.path.join(KOK, ".github", "workflows", "nobet.yml")
IMAJ = os.path.join(KOK, ".github", "workflows", "onizleme-imaj.yml")
ACTION = os.path.join(KOK, ".github", "actions", "gizli-paket-cek", "action.yml")
IS_AKISI_DIZIN = os.path.join(KOK, ".github", "workflows")
KAPI_ARACI = os.path.join(KOK, "tools", "onizleme-kapisi.py")

IS_ADI = "hacim-tam-takim"
ORTAK_ACTION_YOLU = "./.github/actions/gizli-paket-cek"
ONKOSUL_ADIM = "On-kosul: kardes depo jetonu + R2 paket kimligi beyan edilmis mi"
ACTION_ONKOSUL_ADIM = "On-kosul: R2 kimligi + paket anahtari beyan edilmis mi (fail-closed)"
# BUTUNLUK adimi ORTAK ACTION'da yasar (cekme sozlesmesinin parcasi) — gerekcesi
# action.yml'de OLCULU yazili: cagri nobet.yml govdesine konunca ci-kapsam-test.py
# "BAYAT izin" kirmizisi veriyordu (o kapi tetigi IS AKISI duzeyinde siniflar).
BUTUNLUK_ADIM = "Paket butunlugu: kayittaki TUM dosya adlari + sha256 (fail-closed)"

R2_SECRETLARI = ("R2_ERISIM_ID", "R2_GIZLI_ANAHTAR", "CLOUDFLARE_ACCOUNT_ID")

# Fikstur olcegi GERCEK kaydin sekliyle AYNI: 25 *.scad + eslem-ozel.json = 26.
SCAD_SAYISI = 25
DOSYA_SAYISI = SCAD_SAYISI + 1
TEST_ANAHTAR = "onizleme/paket-vTEST.tar.gz"
BASKA_ANAHTAR = "onizleme/paket-vESKI.tar.gz"
# OpenSCAD pini (K427 artigi, 3 Eki 2026): tek kaynak Dockerfile `ARG OPENSCAD_DOSYA`.
DOCKERFILE = os.path.join(KOK, "onizleme", "derleyici", "Dockerfile")
OPENSCAD_TURET_ADIM = "OpenSCAD surumu (canli imajla ayni — Dockerfile'dan turetilir)"
OPENSCAD_KUR_ADIM = "OpenSCAD (pinli nightly AppImage + xvfb)"
OPENSCAD_TURET_ID = "openscad-surum"
OPENSCAD_ARG_RE = re.compile(r"^ARG OPENSCAD_DOSYA=(\S+)\s*$", re.M)
SNAPSHOT_URL_RE = re.compile(r"files\.openscad\.org/snapshots/(\S*)")
# m5 yuku: kurulum adiminin ESKI hali (snapshot dizininden EN SON nightly secimi).
ESKI_KURULUM = ("FN=$(curl -s https://files.openscad.org/snapshots/ \\\n"
                "     | grep -oE 'OpenSCAD-[0-9.]+\\.ai[0-9]+-x86_64\\.AppImage' "
                "| sort -u | tail -1)\n"
                'wget -q "https://files.openscad.org/snapshots/$FN" -O openscad.AppImage\n'
                "openscad --version\n")

# Kollar bu dosyayi hedefler (sentetik ad; gercek uretec adi kaynakta gecmez).
KURBAN_SCAD = "uretec07.scad"


def yaml_yukle(yol):
    """FAIL-CLOSED: gercek bir YAML ayristirici yoksa YESIL SAYMAZ, OLCULEMEDI der."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("OLCULEMEDI: pyyaml yok — is akisi YAML'i ayristirilamadi.")
        print("  Cozum: pip install pyyaml  (CI'da nobet.yml::hijyen-build zaten kurar)")
        sys.exit(2)
    import yaml
    with open(yol, encoding="utf-8") as f:
        return yaml.safe_load(f)


def adim_govdesi(yol, is_adi, adim_adi):
    """Bir is akisi/action adiminin `run:` govdesini KAYNAKTAN cikarir.

    Adim bulunamazsa OLCULEMEDI: adim yeniden adlandirilirsa test sessizce
    yesile dusmez (ad supurmesi fikstur yuzeyini korlestirir dersi)."""
    belge = yaml_yukle(yol)
    if is_adi is None:
        adimlar = belge.get("runs", {}).get("steps", []) or []
    else:
        adimlar = belge.get("jobs", {}).get(is_adi, {}).get("steps", []) or []
    for adim in adimlar:
        if adim.get("name") == adim_adi:
            govde = adim.get("run")
            if not govde:
                print("OLCULEMEDI: '%s' adiminda `run` govdesi YOK." % adim_adi)
                sys.exit(2)
            return govde
    print("OLCULEMEDI: '%s' adimi bulunamadi (%s)." % (adim_adi, os.path.basename(yol)))
    print("  Adim yeniden adlandirildiysa bu dosyadaki sabiti de guncelleyin.")
    sys.exit(2)


def kos(govde, ortam, calisma_dizini):
    """Govdeyi IZOLE dizinde kosar. Kaynak agaca yazmaz."""
    tam_ortam = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "HOME": calisma_dizini}
    tam_ortam.update(ortam)
    proc = subprocess.run(["bash", "-c", govde], cwd=calisma_dizini,
                          env=tam_ortam, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def m1_yamala(govde):
    """M1: fail-closed kolu sustur — `exit 1` -> `exit 0`."""
    return govde.replace("exit 1", "exit 0")


def m2_yamala(_govde):
    """M2: butunluk kolunu ESKI HALINE (tek dosya varligi) dondur.

    Bu, K378'in ONARDIGI davranisin ta kendisidir: arsiv acildi mi diye bakar, TAM mi
    diye BAKMAZ. K4 (eksik .scad) ve K5 (bozuk icerik) birlikte olmelidir."""
    return ('test -f "$HEDEF_DIZIN"/eslem-ozel.json || {\n'
            '  echo "OLCULEMEDI: paket acildi ama eslem-ozel.json yok"; exit 1; }\n')


def m3_yamala(govde):
    """M3: kayit<->R2 anahtar caprazini sustur — `--paket-anahtar ...` bayragini dusur."""
    return govde.replace('--paket-anahtar "$PAKET_ANAHTAR"', "")


def m4_yamala(govde):
    """M4: OpenSCAD surum turetmenin fail-closed kolunu sustur — `exit 1` -> `exit 0`."""
    return govde.replace("exit 1", "exit 0")


def m5_yamala(adimlar):
    """M5: kurulum adimini ESKI "en son snapshot" secimine dondur (IZOLE kopya)."""
    yeni = []
    for adim in adimlar:
        adim = dict(adim)
        if adim.get("name") == OPENSCAD_KUR_ADIM:
            adim.pop("env", None)
            adim["run"] = ESKI_KURULUM
        yeni.append(adim)
    return yeni


# --------------------------------------------------------------------------- fikstur
def _fikstur_kur(dizin):
    """IZOLE fikstur kurar ve paket dizinini dondurur.

    Icerik: <dizin>/tools/onizleme-kapisi.py (KAYNAKTAN kopya — gate govdesi GERCEK,
    ikinci kopya yazilmadi) + <dizin>/onizleme/derleyici/paket-ozel/ altinda 26
    sentetik dosya + aracin KENDI yazicisiyla uretilmis parmakizi kaydi.

    Arac `ROOT`u kendi __file__ konumundan turetir, bu yuzden kopya <dizin>/tools
    altina konunca VARSAYILAN_MANIFEST de <dizin>/onizleme/derleyici/... olur: gercek
    repo kaydina ne okunur ne yazilir."""
    if not os.path.exists(KAPI_ARACI):
        print("OLCULEMEDI: dogrulayici arac YOK (%s)" % KAPI_ARACI)
        sys.exit(2)
    araclar = os.path.join(dizin, "tools")
    os.makedirs(araclar, exist_ok=True)
    shutil.copy2(KAPI_ARACI, os.path.join(araclar, "onizleme-kapisi.py"))
    paket = os.path.join(dizin, "onizleme", "derleyici", "paket-ozel")
    os.makedirs(paket, exist_ok=True)
    for i in range(SCAD_SAYISI):
        with open(os.path.join(paket, "uretec%02d.scad" % i), "w", encoding="utf-8") as f:
            f.write("// sentetik uretec %d\ncube(%d);\n" % (i, i + 1))
    with open(os.path.join(paket, "eslem-ozel.json"), "w", encoding="utf-8") as f:
        f.write('{"surum": 9, "aileler": {}}\n')
    rc, cikti = kos("python3 tools/onizleme-kapisi.py parmakizi-yaz "
                    "--dizin onizleme/derleyici/paket-ozel "
                    "--paket-anahtar " + TEST_ANAHTAR, {}, dizin)
    if rc != 0:
        print("OLCULEMEDI: fikstur parmakizi kaydi yazilamadi (rc=%d)\n%s"
              % (rc, cikti[:600]))
        sys.exit(2)
    if ("%d dosya" % DOSYA_SAYISI) not in cikti:
        print("OLCULEMEDI: fikstur %d dosya uretmedi -> kayit sekli gercek kayitla "
              "ayristi.\n%s" % (DOSYA_SAYISI, cikti[:600]))
        sys.exit(2)
    return paket


def _butunluk_kos(govde, dizin, anahtar=TEST_ANAHTAR):
    """Govde ortamini CAGIRAN is akisiyla AYNI degiskenlerle kurar (HEDEF_DIZIN +
    PAKET_ANAHTAR); ikisi de ortak action'in `inputs`larindan gelir."""
    return kos(govde, {"PAKET_ANAHTAR": anahtar,
                       "HEDEF_DIZIN": "onizleme/derleyici/paket-ozel"}, dizin)


# --------------------------------------------------------------------------- kollar
def k1_onkosul_bos(govde, _dizin):
    """Kimlik BOS -> KIRMIZI ve eksik adlar basilmali."""
    ortam = {"JEN_TOKEN": "", "R2_ERISIM_ID": "", "R2_GIZLI_ANAHTAR": "",
             "CLOUDFLARE_ACCOUNT_ID": "", "PAKET_ANAHTAR": ""}
    rc, cikti = kos(govde, ortam, _dizin)
    if rc == 0:
        return False, "rc=0 — SESSIZ ATLAMA: bos kimlikle on-kosul GECTI"
    eksik_ad = [ad for ad in R2_SECRETLARI if ad in cikti]
    if not eksik_ad:
        return False, "rc=%d ama eksik secret ADI basilmadi (gurultusuz kirmizi)" % rc
    return True, "rc=%d · basilan eksik ad sayisi=%d" % (rc, len(eksik_ad))


def k2_onkosul_dolu(govde, _dizin):
    """Kimlik DOLU -> YESIL (taban; bu kol olmadan K1 totoloji olurdu)."""
    ortam = {"JEN_TOKEN": "x", "R2_ERISIM_ID": "x", "R2_GIZLI_ANAHTAR": "x",
             "CLOUDFLARE_ACCOUNT_ID": "x", "PAKET_ANAHTAR": "onizleme/paket-vX.tar.gz"}
    rc, cikti = kos(govde, ortam, _dizin)
    if rc != 0:
        return False, "rc=%d — dolu kimlikle on-kosul KIRMIZI yandi: %s" % (rc, cikti.strip()[:200])
    return True, "rc=0 (taban yesil)"


def k3_butunluk_tam(govde, dizin):
    """Paket TAM (26/26) -> YESIL ve SAYI basilmali (acceptance: sayiyi bassin)."""
    _fikstur_kur(dizin)
    rc, cikti = _butunluk_kos(govde, dizin)
    if rc != 0:
        return False, "rc=%d — TAM pakette kirmizi yandi: %s" % (rc, cikti.strip()[-260:])
    if ("%d dosya" % DOSYA_SAYISI) not in cikti or ("%d .scad" % SCAD_SAYISI) not in cikti:
        return False, ("rc=0 ama SAYI basilmadi (beklenen '%d dosya' + '%d .scad'): %s"
                       % (DOSYA_SAYISI, SCAD_SAYISI, cikti.strip()[-200:]))
    return True, "rc=0 · %d/%d dosya (%d .scad) dogrulandi" % (
        DOSYA_SAYISI, DOSYA_SAYISI, SCAD_SAYISI)


def k4_butunluk_eksik_scad(govde, dizin):
    """1 *.scad EKSIK -> KIRMIZI ve o dosya ADIYLA basilmali (M2 hedefi).

    "1 dosya gordum, gectim" davranisinin ta kendisini olcer: eslem-ozel.json YERINDE,
    yalnizca bir uretec kayip."""
    paket = _fikstur_kur(dizin)
    os.remove(os.path.join(paket, KURBAN_SCAD))
    rc, cikti = _butunluk_kos(govde, dizin)
    if rc == 0:
        return False, ("rc=0 — %s EKSIKken butunluk GECTI (paketin yalniz 1 dosyasina "
                       "bakiliyor)" % KURBAN_SCAD)
    if KURBAN_SCAD not in cikti:
        return False, "rc=%d ama eksik dosya ADI (%s) basilmadi" % (rc, KURBAN_SCAD)
    return True, "rc=%d · eksik dosya ADIYLA basildi (%s)" % (rc, KURBAN_SCAD)


def k5_butunluk_bozuk_ozet(govde, dizin):
    """1 dosyanin ICERIGI degismis (sha256 uyusmuyor) -> KIRMIZI + ADIYLA.

    Dosya SAYISI dogru kalir: yalnizca ADLARA bakan bir kol bunu goremez."""
    paket = _fikstur_kur(dizin)
    with open(os.path.join(paket, KURBAN_SCAD), "a", encoding="utf-8") as f:
        f.write("// elle degistirildi\n")
    rc, cikti = _butunluk_kos(govde, dizin)
    if rc == 0:
        return False, ("rc=0 — %s ICERIGI degismisken butunluk GECTI (yalniz ad "
                       "sayiliyor, ozet olculmuyor)" % KURBAN_SCAD)
    if KURBAN_SCAD not in cikti:
        return False, "rc=%d ama bozuk dosya ADI (%s) basilmadi" % (rc, KURBAN_SCAD)
    return True, "rc=%d · icerik sapmasi ADIYLA basildi (%s)" % (rc, KURBAN_SCAD)


def k6_butunluk_eslem_yok(govde, dizin):
    """eslem-ozel.json YOK -> KIRMIZI + ADIYLA (eski tek-dosya kolunun ardili)."""
    paket = _fikstur_kur(dizin)
    os.remove(os.path.join(paket, "eslem-ozel.json"))
    rc, cikti = _butunluk_kos(govde, dizin)
    if rc == 0:
        return False, "rc=0 — eslem-ozel.json YOKken butunluk GECTI (yalanci yesil)"
    if "eslem-ozel.json" not in cikti:
        return False, "rc=%d ama 'eslem-ozel.json' adi basilmadi" % rc
    return True, "rc=%d · eslem-ozel.json ADIYLA basildi" % rc


def k7_anahtar_caprazi(govde, dizin):
    """CI BASKA bir R2 anahtari cekmis -> KIRMIZI (kayit bu pakete ait degil; M3 hedefi)."""
    _fikstur_kur(dizin)
    rc, cikti = _butunluk_kos(govde, dizin, anahtar=BASKA_ANAHTAR)
    if rc == 0:
        return False, ("rc=0 — kayit '%s' icin uretilmisken CI '%s' cekti ve butunluk "
                       "GECTI (anahtar caprazi olu)" % (TEST_ANAHTAR, BASKA_ANAHTAR))
    if BASKA_ANAHTAR not in cikti and TEST_ANAHTAR not in cikti:
        return False, "rc=%d ama ayrisan anahtar ADIYLA basilmadi" % rc
    return True, "rc=%d · kayit/CI anahtar ayrismasi ADIYLA basildi" % rc


def k8_emekli_secret_atfi():
    """NON-GROWTH: hacim-tam-takim govdesinde emekli secret ATFI 0 olmali."""
    belge = yaml_yukle(NOBET)
    adimlar = belge.get("jobs", {}).get(IS_ADI, {}).get("steps", []) or []
    if not adimlar:
        return False, "OLCULEMEDI: %s isinin adimlari okunamadi" % IS_ADI
    metin = str(adimlar)
    sayi = metin.count("ONIZLEME_PAKET_B64")
    if sayi:
        return False, ("emekli secret %d kez ATIFTA — 16 Tem Okan karari geri alinmis "
                       "(repoda YOK, is on-kosulda oluyor)" % sayi)
    return True, "atif=0 (emekli secret geri eklenmemis)"


def k9_ikiz_cekme_tanimi_yok():
    """Cekme mantigi YALNIZ ortak action'da yasamali. Cift yonlu olcum:
    is akislarinda 0 · action'da >=1 (kol CANLI oldugunu ayrica kanitlar)."""
    kirli = []
    for ad in sorted(os.listdir(IS_AKISI_DIZIN)):
        if not ad.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(IS_AKISI_DIZIN, ad), encoding="utf-8") as f:
            if "aws s3 cp" in f.read():
                kirli.append(ad)
    if not os.path.exists(ACTION):
        return False, "OLCULEMEDI: ortak action YOK (%s)" % ACTION
    with open(ACTION, encoding="utf-8") as f:
        action_sayi = f.read().count("aws s3 cp")
    if kirli:
        return False, "IKIZ TANIM: is akisinda cekme mantigi var -> %s" % ", ".join(kirli)
    if action_sayi < 1:
        return False, "OLU KOL: ortak action icinde `aws s3 cp` YOK (cekme nereye gitti?)"
    return True, "is akisi=0 · ortak action=%d (tek tanim)" % action_sayi


def k10_ikiz_butunluk_tanimi_yok():
    """Butunluk dogrulayicisi TEK: tools/onizleme-kapisi.py parmakizi-dogrula.

    DORT YONLU (grep==0 nobetcisi tek basina OLUDUR — ad hem ATIF hem YASAK olamaz):
      (+) ortak action icinde cagri >=1        (butunluk kolu CANLI)
      (+) onizleme-imaj.yml icinde cagri >=1   (B-iddia capasi CANLI: is-akisi-kapisi
          B_IDDIALAR['parmakizi-dizin'] YALNIZ o dosyaya bakar)
      (+) hacim-tam-takim ortak action'i `uses:` ile CAGIRIYOR (butunlugu fiilen aliyor;
          `uses` dusurulurse is akisi cekmeyi de butunlugu de kaybeder)
      (-) hacim-tam-takim govdesinde elle yazilmis ikinci bir ozet mantigi
          (`sha256sum` / `hashlib`) = 0 (ikinci dogrulayici acilmamis)"""
    cagri = "onizleme-kapisi.py parmakizi-dogrula"
    sayilar = {}
    for etiket, yol in (("ortak-action", ACTION), ("onizleme-imaj.yml", IMAJ)):
        if not os.path.exists(yol):
            return False, "OLCULEMEDI: dosya YOK (%s)" % yol
        with open(yol, encoding="utf-8") as f:
            sayilar[etiket] = f.read().count(cagri)
    olu = [e for e, n in sayilar.items() if n < 1]
    if olu:
        return False, ("OLU KOL: `%s` cagrisi %s icinde YOK -> orada butunluk "
                       "olculmuyor" % (cagri, ", ".join(olu)))
    belge = yaml_yukle(NOBET)
    adimlar = belge.get("jobs", {}).get(IS_ADI, {}).get("steps", []) or []
    if not adimlar:
        return False, "OLCULEMEDI: %s isinin adimlari okunamadi" % IS_ADI
    kullanim = len([a for a in adimlar if a.get("uses") == ORTAK_ACTION_YOLU])
    if kullanim < 1:
        return False, ("KOPUK KABLO: %s isi ortak action'i (`%s`) `uses:` ile "
                       "CAGIRMIYOR -> cekilen paketin butunlugu HIC olculmez"
                       % (IS_ADI, ORTAK_ACTION_YOLU))
    elle = [j for j in ("sha256sum", "hashlib") if j in str(adimlar)]
    if elle:
        return False, ("IKINCI DOGRULAYICI: %s govdesinde elle ozet mantigi var (%s) — "
                       "butunluk TEK ARACTA kalmali" % (IS_ADI, ", ".join(elle)))
    return True, "action=%d · imaj=%d · hacim `uses`=%d · elle ozet mantigi=0" % (
        sayilar["ortak-action"], sayilar["onizleme-imaj.yml"], kullanim)


def _dockerfile_metni():
    if not os.path.exists(DOCKERFILE):
        print("OLCULEMEDI: Dockerfile YOK (%s)" % DOCKERFILE)
        sys.exit(2)
    with open(DOCKERFILE, encoding="utf-8") as f:
        return f.read()


def _turet_kos(govde, dizin, dockerfile_metni):
    """Turetme govdesini IZOLE dizinde, sentetik/kopya Dockerfile + GITHUB_OUTPUT ile kosar.
    Donus: (rc, cikti, GITHUB_OUTPUT anahtar->deger)."""
    derleyici = os.path.join(dizin, "onizleme", "derleyici")
    os.makedirs(derleyici, exist_ok=True)
    with open(os.path.join(derleyici, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(dockerfile_metni)
    cikti_dosya = os.path.join(dizin, "github-output.txt")
    open(cikti_dosya, "w").close()
    rc, cikti = kos(govde, {"GITHUB_OUTPUT": cikti_dosya}, dizin)
    with open(cikti_dosya, encoding="utf-8") as f:
        ciktilar = dict(s.split("=", 1) for s in f.read().splitlines() if "=" in s)
    return rc, cikti, ciktilar


def k11_openscad_turet_gercek(govde, dizin):
    """GERCEK Dockerfile -> rc==0 ve cikti, testin BAGIMSIZ okudugu ARG ile ayni."""
    metin = _dockerfile_metni()
    bulunan = OPENSCAD_ARG_RE.findall(metin)
    if len(bulunan) != 1:
        return False, ("OLCULEMEDI: gercek Dockerfile'da `ARG OPENSCAD_DOSYA` %d kez "
                       "(1 olmali)" % len(bulunan))
    beklenen = bulunan[0]
    rc, cikti, ciktilar = _turet_kos(govde, dizin, metin)
    if rc != 0:
        return False, "rc=%d — gercek Dockerfile'la turetme KIRMIZI: %s" % (rc, cikti.strip()[-200:])
    if ciktilar.get("dosya") != beklenen:
        return False, ("PARITE KOPUK: turetilen dosya=%r, Dockerfile pini=%r"
                       % (ciktilar.get("dosya"), beklenen))
    surum = beklenen[len("OpenSCAD-"):-len("-x86_64.AppImage")]
    if ciktilar.get("surum") != surum:
        return False, "surum=%r, beklenen %r" % (ciktilar.get("surum"), surum)
    return True, "rc=0 · dosya=%s · surum=%s (Dockerfile pini ile ayni)" % (beklenen, surum)


def k12_openscad_turet_arg_yok(govde, dizin):
    """ARG YOK -> rc!=0 + adet=0 (sessizce bos surumle indirmeye gecmez; M4 hedefi)."""
    metin = OPENSCAD_ARG_RE.sub("", _dockerfile_metni())
    rc, cikti, ciktilar = _turet_kos(govde, dizin, metin)
    if rc == 0:
        return False, "rc=0 — ARG YOKken turetme GECTI (ciktilar=%r)" % ciktilar
    if "adet=0" not in cikti:
        return False, "rc=%d ama 'adet=0' basilmadi" % rc
    return True, "rc=%d · adet=0 basildi" % rc


def k13_openscad_turet_iki_arg(govde, dizin):
    """ARG IKI KEZ -> rc!=0 + adet=2 (hangisi pin belirsiz; ilkini/sonuncuyu SECMEZ)."""
    metin = _dockerfile_metni() + "\nARG OPENSCAD_DOSYA=OpenSCAD-2099.01.01.ai99999-x86_64.AppImage\n"
    rc, cikti, _ = _turet_kos(govde, dizin, metin)
    if rc == 0:
        return False, "rc=0 — iki pin varken turetme birini SECTI"
    if "adet=2" not in cikti:
        return False, "rc=%d ama 'adet=2' basilmadi" % rc
    return True, "rc=%d · adet=2 basildi" % rc


def k14_openscad_kurulum_pinli(adimlar):
    """Kurulum adimi turetilen pini kullanir; isin hicbir govdesi snapshot LISTELEMEZ."""
    turet = [a for a in adimlar if a.get("name") == OPENSCAD_TURET_ADIM]
    kur = [a for a in adimlar if a.get("name") == OPENSCAD_KUR_ADIM]
    if len(turet) != 1 or len(kur) != 1:
        return False, "OLCULEMEDI: turetme=%d · kurulum=%d adim (1/1 olmali)" % (len(turet), len(kur))
    if turet[0].get("id") != OPENSCAD_TURET_ID:
        return False, "turetme adiminin id'si %r (beklenen %r)" % (turet[0].get("id"), OPENSCAD_TURET_ID)
    env = kur[0].get("env") or {}
    beklenen_env = {"OPENSCAD_DOSYA": "${{ steps.%s.outputs.dosya }}" % OPENSCAD_TURET_ID,
                    "OPENSCAD_SURUM": "${{ steps.%s.outputs.surum }}" % OPENSCAD_TURET_ID}
    kopuk = [k for k, v in beklenen_env.items() if env.get(k) != v]
    if kopuk:
        return False, "KOPUK KABLO: kurulum adimi env %s turetilen ciktiya bagli DEGIL" % ", ".join(kopuk)
    govde = kur[0].get("run") or ""
    if "OpenSCAD version $OPENSCAD_SURUM" not in govde:
        return False, "kurulan ikilinin `--version`'i pine karsi DOGRULANMIYOR"
    urller = []
    for adim in adimlar:
        urller += SNAPSHOT_URL_RE.findall(adim.get("run") or "")
    sapan = [u for u in urller if not u.startswith("$OPENSCAD_DOSYA")]
    if not urller:
        return False, "OLU KOL: isin hicbir govdesinde snapshot indirmesi YOK"
    if sapan:
        return False, ("PINSIZ SECIM: snapshot URL'si pin disi -> %s (dizin listeleniyor "
                       "ya da baska degisken)" % ", ".join(repr(u) for u in sapan))
    return True, "env 2/2 bagli · --version dogrulamasi var · snapshot URL %d/%d pinli" % (
        len(urller), len(urller))


# --------------------------------------------------------------------------- surucu
def kollari_kos(mutant):
    onkosul = adim_govdesi(ACTION, None, ACTION_ONKOSUL_ADIM)
    butunluk = adim_govdesi(ACTION, None, BUTUNLUK_ADIM)
    turet = adim_govdesi(NOBET, IS_ADI, OPENSCAD_TURET_ADIM)
    hacim_adimlari = yaml_yukle(NOBET).get("jobs", {}).get(IS_ADI, {}).get("steps", []) or []
    if mutant == "m1":
        onkosul = m1_yamala(onkosul)
    elif mutant == "m2":
        butunluk = m2_yamala(butunluk)
    elif mutant == "m3":
        butunluk = m3_yamala(butunluk)
    elif mutant == "m4":
        turet = m4_yamala(turet)
    elif mutant == "m5":
        hacim_adimlari = m5_yamala(hacim_adimlari)

    sonuc = {}
    with tempfile.TemporaryDirectory(prefix="pruvo-onkosul-") as d:
        sonuc["K1 on-kosul/kimlik BOS -> KIRMIZI"] = k1_onkosul_bos(onkosul, d)
    with tempfile.TemporaryDirectory(prefix="pruvo-onkosul-") as d:
        sonuc["K2 on-kosul/kimlik DOLU -> YESIL"] = k2_onkosul_dolu(onkosul, d)
    for ad, kol in (("K3 butunluk/TAM 26/26 -> YESIL+SAYI", k3_butunluk_tam),
                    ("K4 butunluk/1 .scad EKSIK -> KIRMIZI", k4_butunluk_eksik_scad),
                    ("K5 butunluk/1 dosya BOZUK -> KIRMIZI", k5_butunluk_bozuk_ozet),
                    ("K6 butunluk/eslem YOK -> KIRMIZI", k6_butunluk_eslem_yok),
                    ("K7 butunluk/anahtar CAPRAZI -> KIRMIZI", k7_anahtar_caprazi)):
        with tempfile.TemporaryDirectory(prefix="pruvo-butunluk-") as d:
            sonuc[ad] = kol(butunluk, d)
    sonuc["K8 emekli secret atfi = 0"] = k8_emekli_secret_atfi()
    sonuc["K9 ikiz cekme tanimi YOK"] = k9_ikiz_cekme_tanimi_yok()
    sonuc["K10 ikiz butunluk tanimi YOK"] = k10_ikiz_butunluk_tanimi_yok()
    for ad, kol in (("K11 openscad turet/GERCEK Dockerfile -> YESIL", k11_openscad_turet_gercek),
                    ("K12 openscad turet/ARG YOK -> KIRMIZI", k12_openscad_turet_arg_yok),
                    ("K13 openscad turet/ARG x2 -> KIRMIZI", k13_openscad_turet_iki_arg)):
        with tempfile.TemporaryDirectory(prefix="pruvo-openscad-") as d:
            sonuc[ad] = kol(turet, d)
    sonuc["K14 openscad kurulum PINLI"] = k14_openscad_kurulum_pinli(hacim_adimlari)
    return sonuc


def bas(baslik, sonuc):
    print(baslik)
    for ad, (gecti, not_) in sonuc.items():
        print("  %s  %-40s %s" % ("✅" if gecti else "❌", ad, not_))
    return [ad for ad, (gecti, _) in sonuc.items() if not gecti]


# Her mutantin OLDURMESI GEREKEN kol + ayni yamayla birlikte dusmesi BEKLENEN kollar.
# `ek` bos degilse o kollarin da dusmesi SARTTIR: m2'nin "1 dosya gordum gectim"
# davranisi TEK bir kolu degil, EKSIK ve BOZUK eksenlerini BIRLIKTE korlestirir.
MUTANT_HEDEF = {
    "m1": ("K1 on-kosul/kimlik BOS -> KIRMIZI", ()),
    "m2": ("K4 butunluk/1 .scad EKSIK -> KIRMIZI",
           ("K5 butunluk/1 dosya BOZUK -> KIRMIZI",)),
    "m3": ("K7 butunluk/anahtar CAPRAZI -> KIRMIZI", ()),
    "m4": ("K12 openscad turet/ARG YOK -> KIRMIZI",
           ("K13 openscad turet/ARG x2 -> KIRMIZI",)),
    "m5": ("K14 openscad kurulum PINLI", ()),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutant", choices=sorted(MUTANT_HEDEF),
                    help="IZOLE kopyada govdeyi yamalar (kaynak dosyaya DOKUNMAZ)")
    args = ap.parse_args()

    print("=" * 74)
    print("HACIM ON-KOSUL + PAKET BUTUNLUK KABULU (K377 · K378)")
    print("=" * 74)

    taban = kollari_kos(None)
    dusen = bas("\nTABAN (mutantsiz):", taban)

    if not args.mutant:
        print("-" * 74)
        if dusen:
            print("SONUC: KIRMIZI ❌ — dusen kol: %s" % " · ".join(dusen))
            return 1
        print("SONUC: YESIL ✅ — %d kol gecti. Mutant kanitini AYRICA kosun:" % len(taban))
        for m in sorted(MUTANT_HEDEF):
            print("  python3 tools/hacim-onkosul-test.py --mutant %s" % m)
        return 0

    if dusen:
        print("-" * 74)
        print("OLCULEMEDI: taban zaten KIRMIZI (%s) — mutant hukmu verilemez." % " · ".join(dusen))
        return 2

    hedef, ek = MUTANT_HEDEF[args.mutant]
    mutantli = kollari_kos(args.mutant)
    dusen_m = bas("\nMUTANT %s (izole kopya):" % args.mutant.upper(), mutantli)

    print("-" * 74)
    if not dusen_m:
        print("MUTANT ULASMADI ❌ — %s yamasi HICBIR kolu oldurmedi; mutantli kosum" % args.mutant)
        print("tabanla AYNI. Yama govdeye degmiyor ya da kol zaten olcmuyor.")
        return 2
    if hedef not in dusen_m:
        print("YANLIS ALAN ❌ — %s dusurdu ama HEDEF kol (%s) hala yesil."
              % (" · ".join(dusen_m), hedef))
        return 2
    kacan = [k for k in ek if k not in dusen_m]
    if kacan:
        print("EKSIK KAPSAM ❌ — %s hedefi oldurdu ama BIRLIKTE olmesi gereken kol(lar) "
              "hala yesil: %s" % (args.mutant, " · ".join(kacan)))
        return 2
    print("MUTANT KANITI ✅ — %s yamasi HEDEF kolu oldurdu: %s" % (args.mutant, hedef))
    if ek:
        print("  Birlikte olen kollar (beklenen): %s" % " · ".join(ek))
    print("  (mutantla dusen kol sayisi: %d · taban: 0)" % len(dusen_m))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""tools/dal-deploy-prova.py kabul bataryasi — sentetik git deposu + kucuk deploy.yml fiksturu.

Vakalar:
  (Y) yesil adimlar -> YESIL (sayilar BIREBIR)
  (K) bir komut rc 1 -> KIRMIZI, ayni adimin sonraki satiri ve sonraki adimlar YINE kosulur
  (C) capa adimi (bas ya da son) yok -> OLCULEMEDI sebep=capa-yok rc 2
  (S) env'de `secrets.` / `${{` -> OLCULEMEDI sayilir, kosulmaz, YESIL'e girmez
  (H) --haric -> KOSULMADI
  (D) agac kosum oncesi kirli -> OLCULEMEDI sebep=agac-kirli
  (A) adim agaci kirletir -> AGAC_KIRLETILDI + rc 1
  (P) PyYAML ve satir ayristiricisi AYNI adim listesini verir (fikstur + GERCEK deploy.yml)
  (G) GERCEK deploy.yml'den turetilen liste "Fotograftan ozel uretim kabul testi" ile baslar, >=10 adim
MUTANTLAR (izole kopyada; canli araca ASLA yazilmaz): turetme bos liste -> (Y)/(G) · ilk kirmizida
dur -> (K) · secret adimi yesil -> (S). Mutantin beklenen kirmizi kumesi kirmizi kumenin alt kumesi
degilse SURVIVOR.

--agir: M4/M5 KABUL VAKASI (14 Eki, Pages 38505301885). `git archive HEAD` -> gecici dizin, temiz
ortamla `git init`+commit; kopyada foto-uretec-kosucu-test.py M4 beklenen kumesi `{"T4"}`'e geri
cevrilir -> prova KIRMIZI ve ilk= foto adimi; bozulmamis kopya -> YESIL. Varsayilan kosumda ATLANIR.

Ag YOK, canli agaca YAZMAZ; gecici dizinler is bitince silinir (GECICI_DIZIN_KALAN=0 basilir).
"""
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(EV, "tools", "dal-deploy-prova.py")
CAPA_BAS = "Fotograftan ozel uretim kabul testi"
GECICI = []

sys.path.insert(0, os.path.join(EV, "tools"))
from git_ortami import sentetik_git  # noqa: E402

FIKSTUR = """name: fikstur
on:
  push:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: "Serit derinlik olcumu (build job'i, aralik disi)"
        run: echo build
  serit-a3:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Onceki adim (aralik disi)
        run: exit 1
      # yorum satiri adimlar arasinda
      - name: %(BAS)s (fikstur)
        run: |
          echo bir
          %(KOMUT)s
          echo iki

      - name: "Ikinci adim: tirnakli"
        run: echo ikinci > /dev/null
      - name: Secretli adim
        env:
          %(ENV)s
        run: echo secret
      - name: "Kanca kablosu (fikstur)"
        if: ${{ !cancelled() }}
        run: echo kanca
      - name: Son adim
        run: |
          %(SON)s
      - name: "%(SONCAPA)s (kalan kirmizi)"
        if: failure()
        run: exit 1
  deploy:
    needs: [serit-a3]
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
"""


def fikstur(KOMUT="true", ENV="ANAHTAR: ${{ secrets.GIZLI }}", SON="echo son", BAS=CAPA_BAS,
            SONCAPA="Serit derinlik olcumu"):
    return FIKSTUR % dict(KOMUT=KOMUT, ENV=ENV, SON=SON, BAS=BAS, SONCAPA=SONCAPA)


def temiz_ortam():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def gecici(onek="dal-prova-test-"):
    d = tempfile.mkdtemp(prefix=onek)
    GECICI.append(d)
    return d


_BOS_KANCA = []


def git(cwd, *arg):
    # Kanonik yol (GIT_* baglami temizlenir — kanca icinde kosarsa gercek depoyu bozmaz);
    # bos kanca dizini: global core.hooksPath'teki gercek kancalar kopyada KOSMAZ.
    if not _BOS_KANCA:
        _BOS_KANCA.append(gecici("dal-prova-kanca-"))
    r = sentetik_git(cwd, *arg, ayarlar=("-c", "core.hooksPath=" + _BOS_KANCA[0], "-c", "commit.gpgsign=false",
                                         "-c", "core.autocrlf=false"),
                     capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("git %s rc=%d: %s" % (" ".join(arg), r.returncode, r.stderr.strip()[-300:]))
    return r.stdout


def depo(yml, ek=None):
    d = gecici()
    os.makedirs(os.path.join(d, ".github", "workflows"))
    with open(os.path.join(d, ".github", "workflows", "deploy.yml"), "w", encoding="utf-8") as f:
        f.write(yml)
    for rel, govde in (ek or {}).items():           # fikstur depoya ek dosya (or. sahte ek kapi)
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        with open(os.path.join(d, rel), "w", encoding="utf-8") as f:
            f.write(govde)
    git(d, "init", "-q")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", "fikstur")
    return d


def kos(arac, agac, *ek):
    r = subprocess.run([sys.executable, arac, agac, *ek], capture_output=True, text=True,
                       env=temiz_ortam(), stdin=subprocess.DEVNULL, timeout=3600)
    satirlar = r.stdout.rstrip("\n").split("\n")
    return r.returncode, r.stdout, satirlar[-1] if satirlar else ""


# ----------------------------------------------------------------------------- vakalar
def v_Y(arac):
    rc, _, son = kos(arac, depo(fikstur()))
    return rc == 0 and son == "DAL_PROVA=YESIL kosulan=4 kirmizi=0 olculemedi=1 kosulmadi=0", "rc=%d %s" % (rc, son)


def v_K(arac):
    rc, out, son = kos(arac, depo(fikstur(KOMUT="false", SON="echo son-adim-kostu")))
    ok = (rc == 1 and son == "DAL_PROVA=KIRMIZI kirmizi=1 ilk=%s (fikstur)" % CAPA_BAS
          and "rc=1 sure=" in out and ":: echo iki" in out
          and ":: echo son-adim-kostu" in out and "ADIM=Son adim HAL=YESIL" in out
          and "ADIM=Ikinci adim: tirnakli HAL=YESIL" in out)
    return ok, "rc=%d %s" % (rc, son)


def v_C(arac):
    sonuc = []
    for yml in (fikstur(BAS="Fotograf kabul testi"), fikstur(SONCAPA="Derinlik")):
        rc, _, son = kos(arac, depo(yml))
        sonuc.append((rc, son))
    ok = all(rc == 2 and son == "DAL_PROVA=OLCULEMEDI sebep=capa-yok" for rc, son in sonuc)
    return ok, " | ".join("rc=%d %s" % x for x in sonuc)


def v_S(arac):
    sonuc = []
    for env in ("ANAHTAR: ${{ secrets.GIZLI }}", "SHA: ${{ github.sha }}"):
        rc, out, son = kos(arac, depo(fikstur(ENV=env)))
        sonuc.append(rc == 0 and "ADIM=Secretli adim HAL=OLCULEMEDI sebep=secret" in out
                     and ":: echo secret" not in out
                     and son == "DAL_PROVA=YESIL kosulan=4 kirmizi=0 olculemedi=1 kosulmadi=0")
    return all(sonuc), "env-vakalari=%s" % sonuc


def v_H(arac):
    rc, out, son = kos(arac, depo(fikstur()), "--haric", "Kanca kablosu")
    ok = (rc == 0 and "ADIM=Kanca kablosu (fikstur) HAL=KOSULMADI sebep=haric" in out
          and ":: echo kanca" not in out
          and son == "DAL_PROVA=YESIL kosulan=3 kirmizi=0 olculemedi=1 kosulmadi=1")
    return ok, "rc=%d %s" % (rc, son)


def v_D(arac):
    d = depo(fikstur())
    with open(os.path.join(d, "yabanci.txt"), "w") as f:
        f.write("x\n")
    rc, out, son = kos(arac, d)
    return rc == 2 and son == "DAL_PROVA=OLCULEMEDI sebep=agac-kirli" and "KOMUT" not in out, "rc=%d %s" % (rc, son)


def v_A(arac):
    rc, out, son = kos(arac, depo(fikstur(SON="touch kirli.txt")))
    return rc == 1 and "AGAC_KIRLETILDI=kirli.txt" in out and son.startswith("DAL_PROVA=KIRMIZI"), "rc=%d %s" % (rc, son)


def v_P(arac):
    try:
        import yaml  # noqa: F401
    except ImportError:
        return False, "OLCULEMEDI: PyYAML yok (ayristirici paritesi olculemez)"
    notlar, ok = [], True
    for ad, agac in (("fikstur", depo(fikstur())), ("gercek", EV)):
        cikti = {}
        for ay in ("yaml", "satir"):
            rc, out, son = kos(arac, agac, "--liste", "--tum", "--ayristirici", ay)
            cikti[ay] = (rc, out)
        esit = cikti["yaml"] == cikti["satir"] and cikti["yaml"][0] == 0
        n = cikti["yaml"][1].count("ADIM_IMZA ")
        ok = ok and esit and n > 0
        notlar.append("%s esit=%s adim=%d" % (ad, esit, n))
    return ok, " · ".join(notlar)


def v_G(arac):
    rc, out, son = kos(arac, EV, "--liste")
    adlar = [s.split("\t", 1)[1] for s in out.splitlines() if s.startswith("ADIM_IMZA ")]
    ok = rc == 0 and len(adlar) >= 10 and adlar[0].startswith(CAPA_BAS) and son == "ADIM_LISTE=%d" % len(adlar)
    return ok, "rc=%d adim=%d ilk=%s" % (rc, len(adlar), adlar[0] if adlar else "-")


def v_Z(arac):
    """SERIT B ek kapisi (BaBa tik 251 A): agacta zarf kapisi varsa KOSAR ve SAYILIR; kirmizisi
    DAL_PROVA'yi KIRMIZI yapar. Yoksa (Y vakasi) sayilmaz -> eski sayimlar degismez."""
    yol = os.path.join("tools", "d1-zarf-fikstur-kapisi.py")
    ad = "SERIT B ek: D1 zarf fikstur kapisi"
    rc1, out1, son1 = kos(arac, depo(fikstur(), {yol: "import sys\nprint('EKSIK=1')\nsys.exit(1)\n"}))
    rc0, out0, son0 = kos(arac, depo(fikstur(), {yol: "print('EKSIK=0')\n"}))
    ok = (rc1 == 1 and son1 == "DAL_PROVA=KIRMIZI kirmizi=1 ilk=" + ad
          and "ADIM=%s HAL=KIRMIZI" % ad in out1 and "| EKSIK=1" in out1
          and rc0 == 0 and son0 == "DAL_PROVA=YESIL kosulan=5 kirmizi=0 olculemedi=1 kosulmadi=0"
          and "ADIM=%s HAL=YESIL" % ad in out0)
    return ok, "kirmizi: rc=%d %s | yesil: rc=%d %s" % (rc1, son1, rc0, son0)


VAKALAR = [("Y", v_Y), ("K", v_K), ("C", v_C), ("S", v_S), ("H", v_H), ("D", v_D), ("A", v_A), ("P", v_P), ("G", v_G),
           ("Z", v_Z)]

MUTANTLAR = [
    ("M-BOS-TURETIM", "    aralik = adimlar[bas[0]:son[0]]\n", "    aralik = []\n", {"Y", "G"}),
    ("M-ILK-KIRMIZIDA-DUR", "        if kirmizi_mi: kirmizi.append(ad)\n",
     "        if kirmizi_mi: kirmizi.append(ad); break\n", {"K"}),
    ("M-SECRET-YESIL", '    return any("secrets." in v or "${{" in v for v in adim["env"].values())\n',
     "    return False\n", {"S"}),
    ("M-EK-KAPI-YOK", "    for ad, komut, dosya in EK_KAPILAR:\n", "    for ad, komut, dosya in ():\n", {"Z"}),
    ("M-EK-KAPI-KIRMIZI-YUTULUR", "            kirmizi.append(ad)\n            for s in cikti",
     "            pass\n            for s in cikti", {"Z"}),
]


def bataryayi_kos(arac, bas=True):
    kirmizi = set()
    for ad, f in VAKALAR:
        try:
            ok, detay = f(arac)
        except Exception as e:  # vaka cokerse KIRMIZI sayilir, gizlenmez
            ok, detay = False, "COKTU: %r" % e
        if not ok:
            kirmizi.add(ad)
        if bas:
            print("VAKA=%s %s :: %s" % (ad, "GECTI" if ok else "KIRMIZI", detay), flush=True)
    return kirmizi


def mutantlari_kos():
    with open(ARAC, encoding="utf-8") as f:
        kaynak = f.read()
    survivor = 0
    for ad, eski, yeni, beklenen in MUTANTLAR:
        if kaynak.count(eski) != 1:
            print("MUTANT=%s HUKUM=SURVIVOR sebep=capa-%d-kez" % (ad, kaynak.count(eski)), flush=True)
            survivor += 1
            continue
        d = gecici("dal-prova-mutant-")
        yol = os.path.join(d, "dal-deploy-prova.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(eski, yeni))
        kirmizi = bataryayi_kos(yol, bas=False)
        oldu = beklenen <= kirmizi
        survivor += 0 if oldu else 1
        print("MUTANT=%s kirmizi=%s beklenen=%s HUKUM=%s" % (ad, sorted(kirmizi), sorted(beklenen),
                                                            "OLDU" if oldu else "SURVIVOR"), flush=True)
    return survivor


# ----------------------------------------------------------------------------- agir vaka
M4_ESKI, M4_YENI = '{"T4", "RR3"}', '{"T4"}'


def agir():
    kok = gecici("dal-prova-agir-")
    tar = os.path.join(kok, "ev.tar")
    git(EV, "archive", "--format=tar", "-o", tar, "HEAD")
    sonuc = []
    for etiket, boz in (("bozuk", True), ("saglam", False)):
        kopya = os.path.join(kok, etiket)
        os.makedirs(kopya)
        with tarfile.open(tar) as t:
            if hasattr(tarfile, "data_filter"):
                t.extractall(kopya, filter="data")
            else:
                t.extractall(kopya)
        if boz:
            hedef = os.path.join(kopya, "tools", "foto-uretec-kosucu-test.py")
            with open(hedef, encoding="utf-8") as f:
                satirlar = f.read().split("\n")
            m4 = [i for i, s in enumerate(satirlar) if s.lstrip().startswith('"M4": (') and M4_ESKI in s]
            if len(m4) != 1:
                print("AGIR=OLCULEMEDI sebep=m4-capa-%d-kez" % len(m4), flush=True)
                return False
            satirlar[m4[0]] = satirlar[m4[0]].replace(M4_ESKI, M4_YENI)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write("\n".join(satirlar))
        git(kopya, "init", "-q")
        git(kopya, "add", "-A")
        git(kopya, "commit", "-q", "-m", "agir-" + etiket)
        t0 = time.time()
        rc, out, son = kos(ARAC, kopya, "--haric", "Kanca kablosu")
        sure = time.time() - t0
        if boz:
            ok = rc == 1 and son.startswith("DAL_PROVA=KIRMIZI") and ("ilk=" + CAPA_BAS) in son
        else:
            ok = rc == 0 and son.startswith("DAL_PROVA=YESIL")
        for s in out.splitlines():
            if s.startswith("ADIM=") or s.startswith("AGAC_KIRLETILDI"):
                print("  [%s] %s" % (etiket, s), flush=True)
        print("AGIR=%s %s rc=%d sure=%.1fs :: %s" % (etiket, "GECTI" if ok else "KIRMIZI", rc, sure, son), flush=True)
        sonuc.append(ok)
        shutil.rmtree(kopya)
    return all(sonuc)


def main():
    agir_mi = "--agir" in sys.argv[1:]
    rc = 1
    try:
        kirmizi = bataryayi_kos(ARAC)
        survivor = mutantlari_kos()
        agir_ok = True
        if agir_mi:
            agir_ok = agir()
        else:
            print("AGIR=ATLANDI (M4/M5 kopya vakasi icin --agir ver)", flush=True)
        print("VAKA=%d/%d SURVIVOR=%d" % (len(VAKALAR) - len(kirmizi), len(VAKALAR), survivor), flush=True)
        rc = 0 if not kirmizi and survivor == 0 and agir_ok else 1
    finally:
        for d in GECICI:
            shutil.rmtree(d, ignore_errors=True)
        kalan = sum(1 for d in GECICI if os.path.exists(d))
        print("GECICI_DIZIN_KALAN=%d (olusturulan=%d)" % (kalan, len(GECICI)), flush=True)
        if kalan:
            rc = 1
    print("SONUC: %s" % ("YESIL" if rc == 0 else "KIRMIZI"), flush=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()

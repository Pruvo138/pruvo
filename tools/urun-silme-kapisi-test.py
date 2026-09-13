#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urun-silme-kapisi-test.py — URUN SILME SINIF KAPISI kabul + mutant bataryasi.

Olcer (hepsi IZOLE gecici depolarda; gercek ev yolunda yazim YOK, gercek repo yalniz
`git show` ile OKUNUR — V12 aea5ccac fiksturu):
  tools/urun-silme-kapisi.py  — id kumesi kuculmesi: RENAME / ARSIVLI / IZINSIZ hukmu,
                                 --index (pre-commit adim 9), CI araligi, merge ebeveyni
  tools/duzelt.py             — `--sil` ve `--toplu` "sil" izinsiz RC_SIL_IZIN + care
                                 `gizli:true`; izinli silme arsive TASIR ve kapidan gecer
  kablolar                    — pre-commit adim 9 + deploy.yml serit-a3 + panel izni

KABUL SORUSU ("bu satiri silsem hangi iddia kirmizi yanar?") mutantlarla CEVAPLANIR:
her mutant kaynagin IZOLE KOPYASINDA tek satiri soker ve HEDEF vakasinin ADIYLA duser.
Capa kaynakta TAM BIR KEZ bulunmazsa mutant "CAPA YOK" ile KIRMIZI (sessiz gecis yok).
KONTROL: zararsiz mutant (yorum eki) TUM vakalari yesil birakmali — harness artefakti degil.

Cikis: 0 = tum vakalar YESIL + tum mutantlar OLDU (>=3) + KONTROL YESIL; aksi 1.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "urun-silme-kapisi.py")
DUZELT = os.path.join(TOOLS, "duzelt.py")
DUZELT_YARDIMCI = ("gorsel_koken.py", "arama.py")   # duzelt.py KOSULSUZ import eder
PANEL = os.path.join(TOOLS, "panel-uygulayici.py")
KANCA = os.path.join(TOOLS, "kancalar", "pre-commit")
DEPLOY = os.path.join(KOK, ".github", "workflows", "deploy.yml")
YOK_KANCA = "/var/empty/urun-silme-kapisi-test-kanca-yok"   # VAR OLMAYAN yol

FIKSTUR_SHA = "aea5ccac"
FIKSTUR_IDLER = ("nissan-ara-i-i-vape-tutucu-adapt-r",
                 "nissan-vape-tutucu-ayarlanabilir-montaj-par-as")
RC_SIL_IZIN = 8

K1 = {"id": "urun-a", "kategori": "Ev", "baslik": "A", "fiyat": "100 TL"}
K2 = {"id": "urun-b", "kategori": "Ev", "baslik": "B", "fiyat": "200 TL"}
K3 = {"id": "urun-c", "kategori": "Ev", "baslik": "C", "fiyat": "300 TL"}
K4 = {"id": "urun-d-yeni", "kategori": "Ev", "baslik": "D", "fiyat": "400 TL"}
K5 = {"id": "urun-q", "kategori": "Ev", "baslik": "Q", "fiyat": "500 TL"}


# ── yardimcilar ──────────────────────────────────────────────────────────────────

def temiz_env(**ek):
    """CI git-baglam mirasi (GITHUB_*, PRUVO_CI_ONCEKI_SHA, GIT_*) fiksturu KIRLETMESIN."""
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("GIT_") or k.startswith("GITHUB_")
                   or k in ("PRUVO_CI_ONCEKI_SHA", "PRUVO_URUN_SIL_IZNI"))}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    env.update(ek)
    return env


def git(depo, *a):
    p = subprocess.run(["git", "-c", "core.hooksPath=" + YOK_KANCA, "-c", "commit.gpgsign=false",
                        "-C", depo] + list(a), capture_output=True, text=True, env=temiz_env())
    if p.returncode != 0:
        raise RuntimeError("git %s rc=%d: %s" % (" ".join(a), p.returncode, p.stderr.strip()))
    return p.stdout.strip()


def yaz(depo, katalog=None, arsiv=None, ham=None):
    with open(os.path.join(depo, "urunler.json"), "w", encoding="utf-8") as f:
        f.write(ham if ham is not None else json.dumps(katalog, ensure_ascii=False, indent=2))
    if arsiv is not None:
        os.makedirs(os.path.join(depo, "arsiv"), exist_ok=True)
        with open(os.path.join(depo, "arsiv", "urunler-arsiv.json"), "w", encoding="utf-8") as f:
            json.dump(arsiv, f, ensure_ascii=False, indent=2)


def commit(depo, mesaj="t"):
    git(depo, "add", "-A")
    git(depo, "commit", "-q", "-m", mesaj)
    return git(depo, "rev-parse", "HEAD")


def yeni_depo(tmp, katalog, arsiv=None):
    d = tempfile.mkdtemp(dir=tmp, prefix="depo-")
    git(d, "init", "-q", "-b", "main")
    yaz(d, katalog, arsiv)
    return d, commit(d, "taban")


def arsiv_girisi(kayit):
    return {"silinme_ts": "2026-09-13T00:00:00Z", "yazan": "test", "kuyruk_id": None,
            "kayit": kayit}


def kapi_kos(kapi, depo, args, env=None):
    p = subprocess.run([sys.executable, kapi, "--depo", depo] + list(args),
                       capture_output=True, text=True, env=env or temiz_env(), timeout=300)
    return p.returncode, p.stdout + p.stderr


def duzelt_sahte(tmp, duzelt, katalog):
    d = tempfile.mkdtemp(dir=tmp, prefix="sahte-")
    os.makedirs(os.path.join(d, "tools"))
    shutil.copy(duzelt, os.path.join(d, "tools", "duzelt.py"))
    for y in DUZELT_YARDIMCI:
        shutil.copy(os.path.join(TOOLS, y), os.path.join(d, "tools", y))
    yaz(d, katalog)
    return d


def duzelt_kos(depo, args, izin=False):
    env = temiz_env(**({"PRUVO_URUN_SIL_IZNI": "OKAN"} if izin else {}))
    p = subprocess.run([sys.executable, os.path.join(depo, "tools", "duzelt.py")] + list(args),
                       capture_output=True, text=True, env=env, cwd=depo, timeout=300)
    return p.returncode, p.stdout + p.stderr


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ── vakalar: (kapi, duzelt, tmp) -> (ok, detay) ──────────────────────────────────

def v1(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, K3])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 1 and "IZINSIZ_SILME urun-b" in out, "rc=%d" % rc


def v2(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, dict(K2, gizli=True), K3])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 0 and "DUSEN=0" in out, "rc=%d" % rc


def v3(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K4, K1, K2, K3])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 0 and "DUSEN=0" in out, "rc=%d" % rc


def v4(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, K3], arsiv=[arsiv_girisi(K2)])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 0 and "ARSIVLI_SILME urun-b" in out, "rc=%d" % rc


def v5(kapi, duzelt, tmp):
    # Geri yuklenmis kayit: arsivde ESKI giris durur; ikinci silme YENI giris ister.
    d, a = yeni_depo(tmp, [K1, K2, K3], arsiv=[arsiv_girisi(K2)])
    yaz(d, [K1, K3])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 1 and "IZINSIZ_SILME urun-b" in out, "rc=%d" % rc


def v6(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, dict(K2, id="urun-b-yeni"), K3])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 0 and "RENAME urun-b -> urun-b-yeni" in out, "rc=%d" % rc


def v7(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, dict(K2, id="urun-b-yeni", fiyat="999 TL"), K3])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 1 and "IZINSIZ_SILME urun-b" in out, "rc=%d" % rc


def v8(kapi, duzelt, tmp):
    d, _ = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, K3])
    git(d, "add", "urunler.json")
    rc, out = kapi_kos(kapi, d, ["--index"])
    return rc == 1 and "eksen=INDEX " in out and "IZINSIZ_SILME urun-b" in out, "rc=%d" % rc


def v8b(kapi, duzelt, tmp):
    d, _ = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, K3])   # stage EDILMEDI -> commit'e girmez
    rc, out = kapi_kos(kapi, d, ["--index"])
    return rc == 0 and "ATLANDI" in out, "rc=%d" % rc


def v9(kapi, duzelt, tmp):
    d, _ = yeni_depo(tmp, [K1, K2, K3])
    git(d, "checkout", "-q", "-b", "dal")
    yaz(d, [K1, K3])
    commit(d, "dalda silme")
    git(d, "checkout", "-q", "main")
    with open(os.path.join(d, "ilgisiz.txt"), "w") as f:
        f.write("x\n")
    commit(d, "ilgisiz")
    git(d, "merge", "--no-ff", "--no-commit", "dal")
    rc, out = kapi_kos(kapi, d, ["--index"])
    return (rc == 0 and "eksen=INDEX+MERGE_HEAD" in out and "DUSEN=0" in out), "rc=%d" % rc


def v10(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, ham="{bozuk")
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 2 and "OLCULEMEDI" in out, "rc=%d" % rc


def v11(kapi, duzelt, tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, K3])
    commit(d)
    yaz(d, [K4, K1, K3])
    c = commit(d)
    rc1, out1 = kapi_kos(kapi, d, [], env=temiz_env(PRUVO_CI_ONCEKI_SHA=a, GITHUB_SHA=c))
    olay = os.path.join(d, "olay.json")
    with open(olay, "w") as f:
        json.dump({"before": a}, f)
    rc2, out2 = kapi_kos(kapi, d, [], env=temiz_env(GITHUB_EVENT_PATH=olay, GITHUB_SHA=c))
    rc3, out3 = kapi_kos(kapi, d, [], env=temiz_env(PRUVO_CI_ONCEKI_SHA="1" * 40, GITHUB_SHA=c))
    ok = (rc1 == 1 and "eksen=CI(acik)" in out1 and "IZINSIZ_SILME urun-b" in out1
          and rc2 == 1 and "IZINSIZ_SILME urun-b" in out2
          and rc3 == 2 and "OLCULEMEDI" in out3)
    return ok, "before=%d olay=%d taban-yok=%d" % (rc1, rc2, rc3)


def v18(kapi, duzelt, tmp):
    # Curutucu B2: yalniz id tasiyan ya da icerigi farkli arsiv girisi izin SAYILMAZ.
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, K3], arsiv=[{"kayit": {"id": "urun-b"}},
                            arsiv_girisi(dict(K2, fiyat="1 TL"))])
    b = commit(d)
    rc, out = kapi_kos(kapi, d, ["--taban", a, "--yeni", b])
    return rc == 1 and "IZINSIZ_SILME urun-b" in out, "rc=%d" % rc


def v19(kapi, duzelt, tmp):
    # Curutucu B3: main'in YENI ekledigi kayit, catisma `--theirs` ile cozulunce yutulur.
    d, _ = yeni_depo(tmp, [K1, K2, K3])
    git(d, "checkout", "-q", "-b", "dal")
    yaz(d, [K1, dict(K2, fiyat="250 TL"), K3])
    commit(d, "dalda degisim")
    git(d, "checkout", "-q", "main")
    yaz(d, [K4, K1, dict(K2, fiyat="275 TL"), K3])
    commit(d, "main yeni urun + degisim")
    p = subprocess.run(["git", "-c", "core.hooksPath=" + YOK_KANCA, "-C", d, "merge", "dal"],
                       capture_output=True, text=True, env=temiz_env())
    if p.returncode == 0:
        return False, "fikstur: catisma BEKLENIYORDU"
    git(d, "checkout", "--theirs", "urunler.json")
    git(d, "add", "urunler.json")
    rc, out = kapi_kos(kapi, d, ["--index"])
    return (rc == 1 and "eksen=INDEX+MERGE_HEAD" in out
            and "IZINSIZ_SILME urun-d-yeni" in out), "rc=%d" % rc


def _pencere_deposu(tmp):
    d, a = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, K3])
    b = commit(d, "izinsiz silme")
    yaz(d, [K4, K1, K3])
    c = commit(d, "ekleme")
    return d, a, b, c


def v20(kapi, duzelt, tmp):
    # Curutucu SUPHE: silme commit'inin koşumu kuyrukta iptal edildi; sonraki koşumun
    # `before`i silmeden SONRAKI commit. Pencere yine yakalamali.
    d, a, b, c = _pencere_deposu(tmp)
    yaz(d, [K4, dict(K1, fiyat="111 TL"), K3])
    e = commit(d, "alan degisimi")
    olay = os.path.join(tmp, "olay-v20-%s.json" % e[:8])
    with open(olay, "w") as f:
        json.dump({"before": c}, f)
    rc, out = kapi_kos(kapi, d, [], env=temiz_env(GITHUB_EVENT_PATH=olay, GITHUB_SHA=e))
    return (rc == 1 and "eksen=CI(pencere-" in out and "IZINSIZ_SILME urun-b" in out), "rc=%d" % rc


def v21(kapi, duzelt, tmp):
    # KONTROL: pencere yapiskan ama ONARILABILIR — kayit geri konunca YESIL.
    d, a, b, c = _pencere_deposu(tmp)
    yaz(d, [K2, K4, K1, K3])
    e = commit(d, "geri konuldu")
    olay = os.path.join(tmp, "olay-v21-%s.json" % e[:8])
    with open(olay, "w") as f:
        json.dump({"before": c}, f)
    rc, out = kapi_kos(kapi, d, [], env=temiz_env(GITHUB_EVENT_PATH=olay, GITHUB_SHA=e))
    return (rc == 0 and "IZINSIZ=0" in out
            and "AFFEDILEN(geri konulan)=1" in out), "rc=%d" % rc


def v22(kapi, duzelt, tmp):
    # Curutucu N2: dal YENI kayit ekler, catisma `--ours` ile cozulur -> index HEAD'e esit
    # ama dalin eklemesi yutuldu. Merge'de on-eleme OLMAMALI.
    d, _ = yeni_depo(tmp, [K1, K2, K3])
    git(d, "checkout", "-q", "-b", "dal")
    yaz(d, [K5, K1, K2, K3])
    commit(d, "dalda yeni urun")
    git(d, "checkout", "-q", "main")
    yaz(d, [K4, K1, K2, K3])
    commit(d, "main yeni urun")
    p = subprocess.run(["git", "-c", "core.hooksPath=" + YOK_KANCA, "-C", d, "merge", "dal"],
                       capture_output=True, text=True, env=temiz_env())
    if p.returncode == 0:
        return False, "fikstur: catisma BEKLENIYORDU"
    git(d, "checkout", "--ours", "urunler.json")
    git(d, "add", "urunler.json")
    rc, out = kapi_kos(kapi, d, ["--index"])
    return rc == 1 and "IZINSIZ_SILME urun-q" in out, "rc=%d" % rc


def v23(kapi, duzelt, tmp):
    # Curutucu N1: rename commit'i + sonraki commit'te yeni id'li kaydin duzenlenmesi ->
    # CI penceresi YESIL kalmali (uc nokta karsilastirmasi sahte KIRMIZI yakiyordu).
    d, _ = yeni_depo(tmp, [K1, K2, K3])
    yaz(d, [K1, dict(K2, id="urun-b-yeni"), K3])
    commit(d, "rename")
    yaz(d, [K1, dict(K2, id="urun-b-yeni", fiyat="222 TL"), K3])
    c = commit(d, "yeni id'li kayitta duzenleme")
    rc, out = kapi_kos(kapi, d, [], env=temiz_env(GITHUB_SHA=c))
    return (rc == 0 and "IZINSIZ=0" in out and "eksen=CI(pencere-" in out), "rc=%d" % rc


def v24(kapi, duzelt, tmp):
    # Dalda kancasiz (`--no-verify` esdegeri) izinsiz silme, catismasiz merge ile main'e
    # girer: merge commit'i MERGE_GETIRISI der; dal commit'i KENDI hukmunu almali.
    d, _ = yeni_depo(tmp, [K1, K2, K3])
    git(d, "checkout", "-q", "-b", "dal")
    yaz(d, [K1, K3])
    commit(d, "dalda izinsiz silme")
    git(d, "checkout", "-q", "main")
    with open(os.path.join(d, "ilgisiz.txt"), "w") as f:
        f.write("x\n")
    commit(d, "ilgisiz")
    git(d, "merge", "-q", "--no-ff", "-m", "merge dal", "dal")
    h = git(d, "rev-parse", "HEAD")
    rc, out = kapi_kos(kapi, d, [], env=temiz_env(GITHUB_SHA=h))
    return rc == 1 and "IZINSIZ_SILME urun-b" in out, "rc=%d" % rc


def v12(kapi, duzelt, tmp):
    rc, out = kapi_kos(kapi, KOK, ["--taban", FIKSTUR_SHA + "^", "--yeni", FIKSTUR_SHA])
    ok = rc == 1 and all(("IZINSIZ_SILME %s" % i) in out for i in FIKSTUR_IDLER)
    return ok, "rc=%d %s" % (rc, out.strip().splitlines()[0][:120] if out.strip() else "")


def v13(kapi, duzelt, tmp):
    d = duzelt_sahte(tmp, duzelt, [K1, K2])
    once = sha(os.path.join(d, "urunler.json"))
    rc, out = duzelt_kos(d, ["urun-b", "--sil", "test"])
    ok = (rc == RC_SIL_IZIN and once == sha(os.path.join(d, "urunler.json"))
          and not os.path.exists(os.path.join(d, ".urunler-sil-izin.json"))
          and not os.path.exists(os.path.join(d, "arsiv"))
          and "python3 tools/duzelt.py urun-b --alan gizli --deger true" in out)
    return ok, "rc=%d" % rc


def v14(kapi, duzelt, tmp):
    d = duzelt_sahte(tmp, duzelt, [K1, K2])
    islem = os.path.join(d, "islem.json")
    with open(islem, "w", encoding="utf-8") as f:
        json.dump([{"id": "urun-a", "alan": "fiyat", "deger": "999 TL"},
                   {"id": "urun-b", "sil": "test"}], f)
    once = sha(os.path.join(d, "urunler.json"))
    rc, out = duzelt_kos(d, ["--toplu", islem])
    ok = (rc == RC_SIL_IZIN and once == sha(os.path.join(d, "urunler.json"))
          and not os.path.exists(os.path.join(d, ".urunler-duzelt-izin.json"))
          and not os.path.exists(os.path.join(d, ".urunler-sil-izin.json"))
          and "--alan gizli --deger true" in out)
    return ok, "rc=%d" % rc


def v15(kapi, duzelt, tmp):
    d = duzelt_sahte(tmp, duzelt, [K1, K2, K3])
    git(d, "init", "-q", "-b", "main")
    commit(d, "taban")
    gerekce = "gizli-gerekce-7f3a"
    rc, out = duzelt_kos(d, ["urun-b", "--sil", gerekce], izin=True)
    if rc != 0:
        return False, "izinli duzelt rc=%d %s" % (rc, out.strip()[-160:])
    with open(os.path.join(d, "urunler.json"), encoding="utf-8") as f:
        kalan = [k["id"] for k in json.load(f)]
    ayol = os.path.join(d, "arsiv", "urunler-arsiv.json")
    if not os.path.exists(ayol):
        return False, "arsiv dosyasi YOK"
    with open(ayol, encoding="utf-8") as f:
        ham = f.read()
    arsiv = json.loads(ham)
    git(d, "add", "urunler.json", "arsiv/urunler-arsiv.json")
    rck, outk = kapi_kos(kapi, d, ["--index"])
    ok = ("urun-b" not in kalan and len(arsiv) == 1 and arsiv[0]["kayit"] == K2
          and gerekce not in ham and rck == 0 and "ARSIVLI_SILME urun-b" in outk)
    return ok, "duzelt rc=%d kapi rc=%d arsiv=%d" % (rc, rck, len(arsiv))


def v16(kapi, duzelt, tmp):
    with open(KANCA, encoding="utf-8") as f:
        kanca = f.read()
    with open(DEPLOY, encoding="utf-8") as f:
        deploy = f.read()
    blok = kanca.split("# --- 9) URUN SILME KAPISI", 1)
    kanca_ok = (len(blok) == 2 and 'python3 "$pruvo_silme" --index' in blok[1]
                and "exit 1" in blok[1] and 'pruvo_silme="$pruvo_kok/tools/urun-silme-kapisi.py"' in blok[1])
    ci_ok = ("run: python3 tools/urun-silme-kapisi.py\n" in deploy
             and "run: python3 tools/urun-silme-kapisi-test.py\n" in deploy)
    return kanca_ok and ci_ok, "kanca=%s ci=%s" % (kanca_ok, ci_ok)


def v17(kapi, duzelt, tmp):
    spec = importlib.util.spec_from_file_location("urun_silme_kapisi_ikiz", kapi)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    with open(duzelt, encoding="utf-8") as f:
        dz = f.read()
    with open(PANEL, encoding="utf-8") as f:
        pn = f.read()
    env_ad = re.search(r'^SIL_IZIN_ENV = "([^"]+)"', dz, re.M)
    env_deger = re.search(r'^SIL_IZIN_DEGERI = "([^"]+)"', dz, re.M)
    panel_arsiv = re.search(r'^ARSIV_DOSYASI = os\.path\.join\("([^"]+)", "([^"]+)"\)', pn, re.M)
    ok = (env_ad and env_deger and panel_arsiv
          and env_ad.group(1) == m.SIL_IZIN_ENV and env_deger.group(1) == m.SIL_IZIN_DEGERI
          and "/".join(panel_arsiv.groups()) == m.ARSIV_YOLU
          and ('%s="%s"' % (m.SIL_IZIN_ENV, m.SIL_IZIN_DEGERI)) in pn)
    return bool(ok), "duzelt/panel/kapi ikiz tanim"


VAKALAR = [
    ("V1_IZINSIZ_SILME", v1), ("V2_GIZLI_TRUE_KONTROL", v2), ("V3_BASA_EKLEME_KONTROL", v3),
    ("V4_ARSIVLI_SILME", v4), ("V5_ESKI_ARSIV_YETMEZ", v5), ("V6_ID_RENAME", v6),
    ("V7_RENAME_ICERIK_DEGISTI", v7), ("V8_INDEX_STAGE_SILME", v8),
    ("V8b_INDEX_STAGESIZ_ATLANDI", v8b), ("V9_MERGE_GETIRISI", v9), ("V10_BOZUK_JSON", v10),
    ("V11_CI_ARALIGI", v11), ("V12_AEA5CCAC_FIKSTURU", v12), ("V13_DUZELT_SIL_IZINSIZ", v13),
    ("V14_DUZELT_TOPLU_SIL_IZINSIZ", v14), ("V15_DUZELT_SIL_IZINLI_UCTAN_UCA", v15),
    ("V16_KANCA_VE_CI_KABLOSU", v16), ("V17_IKIZ_TANIM", v17),
    ("V18_SAHTE_ARSIV_GIRISI", v18), ("V19_MERGE_THEIRS_YENI_KAYIT_KAYBI", v19),
    ("V20_CI_PENCERE_IPTAL_BOSLUGU", v20), ("V21_PENCERE_ONARIM_KONTROL", v21),
    ("V22_MERGE_OURS_DAL_EKLEMESI_KAYBI", v22), ("V23_CI_RENAME_SONRASI_DUZENLEME", v23),
    ("V24_CI_DAL_COMMITI_KENDI_HUKMU", v24),
]
VAKA = dict(VAKALAR)

# (ad, hedef dosya, capa, yerine, hedef vaka)
MUTANTLAR = [
    ("M1_DUZELT_IZIN_KOLU_SOKULDU", "duzelt",
     "    return os.environ.get(SIL_IZIN_ENV) == SIL_IZIN_DEGERI\n", "    return True\n",
     "V13_DUZELT_SIL_IZINSIZ"),
    ("M2_TOPLU_IZIN_KOLU_SOKULDU", "duzelt",
     "    if urun_silmeler and not _sil_izni_var():\n", "    if False:\n",
     "V14_DUZELT_TOPLU_SIL_IZINSIZ"),
    ("M3_ID_KUCULME_OLCUSU_SOKULDU", "kapi",
     "        dusen.append(uid)\n", "        pass\n",
     "V12_AEA5CCAC_FIKSTURU"),
    ("M4_ARSIV_SAYACI_VARLIGA_GEVSEDI", "kapi",
     "        if len(yeni_g) > len(taban_arsiv.get(uid, {}).get(anahtar, [])):\n",
     "        if len(yeni_arsiv.get(uid, {})) > 0:\n", "V5_ESKI_ARSIV_YETMEZ"),
    ("M5_RENAME_ICERIGE_BAKMIYOR", "kapi",
     "    return json.dumps(k, sort_keys=True, ensure_ascii=False)\n", '    return ""\n',
     "V7_RENAME_ICERIK_DEGISTI"),
    ("M6_MERGE_ORTAK_ATA_SARTI_SOKULDU", "kapi",
     "        if (len(ebeveynler) > 1 and uid in ata_idleri\n",
     "        if (len(ebeveynler) > 1\n", "V19_MERGE_THEIRS_YENI_KAYIT_KAYBI"),
    ("M7_DUZELT_ARSIV_YAZIMI_SOKULDU", "duzelt",
     "        _atomic_write(ARSIV, arsiv)\n", "        pass\n", "V15_DUZELT_SIL_IZINLI_UCTAN_UCA"),
    ("M8_ARSIV_ICERIK_ESLESMESI_SOKULDU", "kapi",
     "    return json.dumps(kayit, sort_keys=True, ensure_ascii=False)\n", '    return ""\n',
     "V18_SAHTE_ARSIV_GIRISI"),
    ("M9_CI_PENCERESI_SOKULDU", "kapi",
     "            and _ata_mi(depo, before, hedef) and _ata_mi(depo, before, pencere)):\n",
     "            and _ata_mi(depo, before, hedef)):\n", "V20_CI_PENCERE_IPTAL_BOSLUGU"),
    ("M10_MERGE_ON_ELEMESI_GERI_GELDI", "kapi",
     "            if rc == 0 and not merge_var:\n", "            if rc == 0:\n",
     "V22_MERGE_OURS_DAL_EKLEMESI_KAYBI"),
    ("M11_CI_UC_NOKTA_KARSILASTIRMASI", "kapi",
     "        sonuc = pencere_hukmu(depo, taban, yeni)\n",
     "        sonuc = uc_nokta_hukmu(depo, taban, yeni)\n", "V23_CI_RENAME_SONRASI_DUZENLEME"),
    ("M12_GERI_KONULAN_AFFI_SOKULDU", "kapi",
     '    toplam["izinsiz"] = [u for u in toplam["izinsiz"] if u not in son_idleri]\n',
     '    toplam["izinsiz"] = list(toplam["izinsiz"])\n', "V21_PENCERE_ONARIM_KONTROL"),
    ("M13_CI_YALNIZ_FIRST_PARENT", "kapi",
     '    rc, out, err = _git(depo, ["rev-list", "--reverse", "--parents", "%s..%s" % (taban, yeni)])\n',
     '    rc, out, err = _git(depo, ["rev-list", "--first-parent", "--reverse", "--parents", "%s..%s" % (taban, yeni)])\n',
     "V24_CI_DAL_COMMITI_KENDI_HUKMU"),
]
KONTROL_MUTANT = ("K0_ZARARSIZ_YORUM", "kapi", "import argparse\n",
                  "import argparse  # kontrol mutanti: davranis DEGISMEZ\n")


def mutant_kopya(tmp, hedef, capa, yerine):
    kaynak = KAPI if hedef == "kapi" else DUZELT
    with open(kaynak, encoding="utf-8") as f:
        govde = f.read()
    n = govde.count(capa)
    if n != 1:
        return None, "CAPA YOK/COKLU (%d) %r" % (n, capa.strip()[:60])
    d = tempfile.mkdtemp(dir=tmp, prefix="mutant-")
    yol = os.path.join(d, os.path.basename(kaynak))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(capa, yerine))
    return yol, ""


def vaka_kos(ad, kapi, duzelt, tmp):
    try:
        return VAKA[ad](kapi, duzelt, tmp)
    except Exception as e:   # vaka coktuyse YESIL sayilmaz
        return False, "COKTU: %r" % (e,)


def main():
    with tempfile.TemporaryDirectory(prefix="urun-silme-kapisi-test-") as tmp:
        dusen = 0
        print("== VAKALAR (gercek kaynak) ==")
        for ad, _ in VAKALAR:
            ok, detay = vaka_kos(ad, KAPI, DUZELT, tmp)
            dusen += 0 if ok else 1
            print("%s %s — %s" % ("✅" if ok else "❌", ad, detay))

        print("\n== MUTANTLAR (izole kopya, hedef vakanin ADIYLA duser) ==")
        olen = 0
        for ad, hedef, capa, yerine, hedef_vaka in MUTANTLAR:
            yol, hata = mutant_kopya(tmp, hedef, capa, yerine)
            if yol is None:
                print("❌ MUTANT %s YASADI — %s" % (ad, hata))
                continue
            kapi = yol if hedef == "kapi" else KAPI
            duzelt = yol if hedef == "duzelt" else DUZELT
            if hedef == "duzelt":
                # sahte repo helper'lari TOOLS'tan kopyalar; mutant dosyanin adi duzelt.py kalir
                pass
            ok, detay = vaka_kos(hedef_vaka, kapi, duzelt, tmp)
            if not ok:
                olen += 1
                print("✅ MUTANT %s OLDU — hedef %s KIRMIZI (%s)" % (ad, hedef_vaka, detay))
            else:
                print("❌ MUTANT %s YASADI — hedef %s hala YESIL (%s)" % (ad, hedef_vaka, detay))

        print("\n== KONTROL (zararsiz mutant, TUM vakalar YESIL kalmali) ==")
        ad, hedef, capa, yerine = KONTROL_MUTANT
        yol, hata = mutant_kopya(tmp, hedef, capa, yerine)
        kontrol_ok = yol is not None
        if not kontrol_ok:
            print("❌ %s kurulamadi — %s" % (ad, hata))
        else:
            for vad, _ in VAKALAR:
                ok, detay = vaka_kos(vad, yol, DUZELT, tmp)
                if not ok:
                    kontrol_ok = False
                    print("❌ KONTROL %s altinda %s KIRMIZI — %s" % (ad, vad, detay))
            if kontrol_ok:
                print("✅ KONTROL %s — %d/%d vaka YESIL" % (ad, len(VAKALAR), len(VAKALAR)))

    toplam_mutant = len(MUTANTLAR)
    basarili = (dusen == 0 and olen == toplam_mutant and toplam_mutant >= 3 and kontrol_ok)
    print("\nSONUC: VAKA %d/%d YESIL · MUTANT %d/%d OLDU · KONTROL %s · rc=%d"
          % (len(VAKALAR) - dusen, len(VAKALAR), olen, toplam_mutant,
             "YESIL" if kontrol_ok else "KIRMIZI", 0 if basarili else 1))
    return 0 if basarili else 1


if __name__ == "__main__":
    sys.exit(main())

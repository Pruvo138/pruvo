#!/usr/bin/env python3
"""urun-kuyruk-birlestir.py kabul bataryasi — AG YOK.

Her vaka tempfile altinda TAZE bir bare `origin` + yazar klonu + CI klonu kurar; arac
CI klonunda (`PRUVO_KUYRUK_TEST_KOK`) kosar. gh ve git `PRUVO_KUYRUK_GH/GIT` ile sahte
ikiliye yonlenir: sahte gh `run list` cevabini ENV'den verir, sahte git GERCEK git'e
iletir; ikisi de her cagriyi gunluge yazar -> "push/dispatch SIFIR" iddiasi GUNLUKTEN
assert edilir (cikti satirina guvenilmez). Ortam HOME/GIT_*/GITHUB_*/K80 mirasindan
temizlenir (kanca icinde kosarken GIT_DIR gercek depoyu hedeflemesin).

Vakalar: V1 BEKLE · V2 BOS dal-yok · V3 BOS geride · V4 BOS esit · V5 BIRLESTI-ff ·
V6 BIRLESTI-merge (+kuyruk senkron) · V7 CAKISMA (main degismez) · V8 yabanci-yol RED ·
V9 gizli yabanci yol (ekle+geri al) RED · V10 push yarisi (red -> taze fetch -> merge) ·
V11 gh hatasi OLCULEMEDI · V12 dispatch hatasi · V13 baglam-disi · V14 K80 PROVA ·
V15 dispatch listesi YAML'dan turer (deploy.yml ilk, nobet.yml haric) · V16-V18 aclik ·
V19 semasiz parametrik RED (K441) · V20 sema main'de -> BIRLESTI · V21 gecmis borc
tetiklemez · V22 bozuk urunler.json OLCULEMEDI · YAPISAL BIRLESIM (14 Eki): Y1 iki taraf
basa ekledi -> yol=yapisal · Y2 main'in sildigi geri gelmez · Y3 cift-ekleme · Y4
cift-degisiklik · Y5 sil-degistir · Y6 urunler.json + kod.txt cakismasi -> CAKISMA (sebepsiz)
· Y7 bicim (main roundtrip-esit degil) · Y8 ozdes ekleme tek kopya. Toplam 30 vaka (V15 dahil).
Mutantlar (izole kopya, once TABAN; 9 mutant): BOS erken donusu silinir -> V3 · yol kapisi
kapatilir -> V8 · sema kapisi kapatilir -> V19 · aclik x2 · cakisan-yol kumesi -> Y6 ·
cift-degisiklik -> Y4 · silme korumasi -> Y2 · cift-ekleme -> Y3.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True  # agaca __pycache__ birakma
sys.path.insert(0, os.path.join(KOK, "tools"))
from git_ortami import sentetik_git  # noqa: E402

ARAC = os.path.join(KOK, "tools", "urun-kuyruk-birlestir.py")
GERCEK_GIT = shutil.which("git")

SAHTE_GH = r'''import json, os, sys
with open(os.environ["SAHTE_LOG"], "a") as f:
    f.write(json.dumps(["gh"] + sys.argv[1:]) + "\n")
if sys.argv[1:3] == ["run", "list"]:
    if os.environ.get("SAHTE_GH_RC", "0") != "0":
        sys.stderr.write("gh: sahte hata\n"); sys.exit(1)
    sys.stdout.write(os.environ.get("SAHTE_GH_RUNS", "[]")); sys.exit(0)
if sys.argv[1:3] == ["workflow", "run"]:
    sys.exit(int(os.environ.get("SAHTE_GH_DISPATCH_RC", "0")))
sys.exit(3)
'''
SAHTE_GIT = r'''import json, os, subprocess, sys
with open(os.environ["SAHTE_LOG"], "a") as f:
    f.write(json.dumps(["git"] + sys.argv[1:]) + "\n")
bayrak = os.environ.get("SAHTE_YARIS_BAYRAK", "")
if "push" in sys.argv and any(a.endswith(":refs/heads/main") for a in sys.argv) \
        and bayrak and os.path.exists(bayrak):
    os.remove(bayrak)
    subprocess.run([os.environ["SAHTE_GERCEK_GIT"], "-C", os.environ["SAHTE_YARIS_KLON"],
                    "push", "-q", "origin", "HEAD:main"], check=True)
sys.exit(subprocess.run([os.environ["SAHTE_GERCEK_GIT"]] + sys.argv[1:]).returncode)
'''


def EK_ORTAM(gecici):
    """Gercek HOME/global git ayari (kanca yolu dahil) fikstur depolarina sizmasin."""
    ev = os.path.join(gecici, "ev")
    os.makedirs(ev, exist_ok=True)
    return {"HOME": ev, "XDG_CONFIG_HOME": ev, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
            "PYTHONDONTWRITEBYTECODE": "1"}


def temiz_env(gecici):
    """Aracin ortami: GIT_* baglami, GITHUB_*, K80 (PRUVO_K80_IC_KOSUM) ve SAHTE_ mirasi
    DUSER — K80 bu bataryayi kendi ic kosumunda kosturunca arac PROVA'ya kacmasin."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GIT_", "GITHUB_", "SAHTE_", "PRUVO_"))}
    env.update(EK_ORTAM(gecici))
    return env


class Sahne:
    """Tek vakalik gecici dunya: origin.git + yazar klonu + ci klonu."""

    def __init__(self, kok):
        self.kok = kok
        self.env = temiz_env(kok)
        self.origin = os.path.join(kok, "origin.git")
        self.yazar = os.path.join(kok, "yazar")
        self.ci = os.path.join(kok, "ci")
        self.log = os.path.join(kok, "cagri.log")
        self.g(None, "init", "-q", "--bare", "-b", "main", self.origin)
        self.g(None, "clone", "-q", self.origin, self.yazar)
        self.yaz("urunler.json", "[\n\"a\",\n\"b\"\n]\n")
        self.yaz("kod.txt", "kod-1\n")
        self.yaz("index.html", "<p>1</p>\n")
        self.commit("taban")
        self.g(self.yazar, "push", "-q", "origin", "HEAD:main")

    def g(self, dizin, *args):
        # Fikstur git'i YALNIZ kanonik yardimcidan (GIT_* scrub + cwd sabit; kapi:
        # tools/fikstur-git-sizinti-kapisi.py).
        p = sentetik_git(dizin or self.kok, *args, kimlik_ad="t", kimlik_eposta="t@t",
                         ek_ortam=EK_ORTAM(self.kok), capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError("fikstur git hatasi %s: %s" % (args, p.stderr))
        return p.stdout.strip()

    def yaz(self, yol, metin, dizin=None):
        tam = os.path.join(dizin or self.yazar, yol)
        os.makedirs(os.path.dirname(tam), exist_ok=True)
        with open(tam, "w", encoding="utf-8") as f:
            f.write(metin)

    def commit(self, mesaj, dizin=None):
        d = dizin or self.yazar
        self.g(d, "add", "-A")
        self.g(d, "commit", "-q", "-m", mesaj)
        return self.g(d, "rev-parse", "HEAD")

    def uzak(self, dal):
        p = subprocess.run([GERCEK_GIT, "--git-dir", self.origin, "rev-parse", "--verify",
                            "-q", "refs/heads/" + dal], capture_output=True, text=True,
                           env=self.env)
        return p.stdout.strip()

    def ci_klonla(self):
        self.g(None, "clone", "-q", self.origin, self.ci)

    def cagrilar(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(s) for s in f if s.strip()]

    def push_sayisi(self, hedef=None):
        return sum(1 for c in self.cagrilar() if c[0] == "git" and "push" in c
                   and (hedef is None or any(a.endswith(":refs/heads/" + hedef) for a in c)))

    def dispatchler(self):
        return [c[3] for c in self.cagrilar() if c[0] == "gh" and c[1:3] == ["workflow", "run"]]


def sahte_kur(dizin):
    yollar = {}
    for ad, govde in (("gh", SAHTE_GH), ("git", SAHTE_GIT)):
        yol = os.path.join(dizin, ad)
        with open(yol, "w", encoding="utf-8") as f:
            f.write("#!%s\n%s" % (sys.executable, govde))
        os.chmod(yol, 0o755)
        yollar[ad] = yol
    return yollar


def kos(sahne, sahte, arac=ARAC, env_ek=None, test_kok=True):
    env = dict(sahne.env)
    env.update({"PRUVO_KUYRUK_GH": sahte["gh"], "PRUVO_KUYRUK_GIT": sahte["git"],
                "PRUVO_KUYRUK_DEPO": KOK, "SAHTE_LOG": sahne.log,
                "SAHTE_GERCEK_GIT": GERCEK_GIT})
    if test_kok:
        env["PRUVO_KUYRUK_TEST_KOK"] = sahne.ci
    env.update(env_ek or {})
    p = subprocess.run([sys.executable, arac], capture_output=True, text=True, env=env,
                       timeout=120)
    satirlar = [s for s in p.stdout.splitlines() if s.startswith("KUYRUK=")]
    return p.returncode, (satirlar[-1] if satirlar else ""), p.stdout + p.stderr


# ── vaka kurgulari: sahne -> (env_ek, test_kok) ─────────────────────────────────

def kur_kuyruk_urun(s, metin="[\n\"a\",\n\"b\",\n\"c\"\n]\n"):
    s.yaz("urunler.json", metin)
    k = s.commit("urun: c")
    s.g(s.yazar, "push", "-q", "origin", "HEAD:urun-kuyruk")
    return k


def kur_kuyruk_urun_tarihli(s, tarih, metin="[\n\"a\",\n\"b\",\n\"c\"\n]\n"):
    """Tarihli kuyruk commit'i (author + committer = tarih). sentetik_git GIT_* env'leri
    SCRUB ettigi icin burada dogrudan GERCEK_GIT + env ile yazilir."""
    s.yaz("urunler.json", metin)
    s.g(s.yazar, "add", "-A")
    env = EK_ORTAM(s.kok)
    env["GIT_COMMITTER_DATE"] = tarih
    env["GIT_AUTHOR_DATE"] = tarih
    p = subprocess.run([GERCEK_GIT, "-C", s.yazar, "commit", "-q", "-m", "urun: tarihli"],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0:
        raise RuntimeError("tarihli commit hatasi: %s" % p.stderr)
    k = s.g(s.yazar, "rev-parse", "HEAD")
    s.g(s.yazar, "push", "-q", "origin", "HEAD:urun-kuyruk")
    return k


def tarih_dk_geri(n):
    """n dakika once, ISO 8601 (TZ yok) — git commit --date icin."""
    return (datetime.now() - timedelta(minutes=n)).strftime("%Y-%m-%dT%H:%M:%S")


def main_ilerlet(s, yol="kod.txt", metin="kod-2\n"):
    s.g(s.yazar, "checkout", "-q", "--detach", s.uzak("main"))
    s.yaz(yol, metin)
    m = s.commit("kod: ilerle")
    s.g(s.yazar, "push", "-q", "origin", "HEAD:main")
    return m


def vakalar():
    """(kimlik, kurgu(sahne)->(env_ek, test_kok, baglam), dogrula(sahne, rc, satir, baglam)->hata|None)"""
    v = []

    def v1_kur(s):
        kur_kuyruk_urun(s)
        return {"SAHTE_GH_RUNS": json.dumps([{"status": "in_progress", "databaseId": 42}])}, True, \
            {"main": s.uzak("main")}

    def v1_dog(s, rc, satir, b):
        if (rc, satir) != (0, "KUYRUK=BEKLE pages=42"):
            return "rc/satir"
        if s.push_sayisi() or s.dispatchler():
            return "BEKLE iken push=%d dispatch=%d" % (s.push_sayisi(), len(s.dispatchler()))
        if s.uzak("main") != b["main"]:
            return "main degisti"
    v.append(("V1-BEKLE", v1_kur, v1_dog))

    def bos_dog(beklenen):
        def dog(s, rc, satir, b):
            if (rc, satir) != (0, beklenen):
                return "rc/satir"
            if s.push_sayisi() or s.dispatchler():
                return "BOS iken push=%d dispatch=%d" % (s.push_sayisi(), len(s.dispatchler()))
            if s.uzak("main") != b["main"]:
                return "main degisti"
        return dog

    v.append(("V2-BOS-dal-yok", lambda s: ({}, True, {"main": s.uzak("main")}),
              bos_dog("KUYRUK=BOS sebep=dal-yok")))

    def v3_kur(s):
        s.g(s.yazar, "push", "-q", "origin", "HEAD:urun-kuyruk")
        main_ilerlet(s)
        return {}, True, {"main": s.uzak("main")}
    v.append(("V3-BOS-geride", v3_kur, bos_dog("KUYRUK=BOS sebep=geride")))

    def v4_kur(s):
        s.g(s.yazar, "push", "-q", "origin", "HEAD:urun-kuyruk")
        return {}, True, {"main": s.uzak("main")}
    v.append(("V4-BOS-esit", v4_kur, bos_dog("KUYRUK=BOS sebep=geride")))

    def v5_kur(s):
        k = kur_kuyruk_urun(s)
        return {}, True, {"k": k}

    def v5_dog(s, rc, satir, b):
        if rc != 0 or not satir.startswith("KUYRUK=BIRLESTI sha=%s yol=ff dispatch=deploy.yml" % b["k"][:12]):
            return "rc/satir"
        if s.uzak("main") != b["k"]:
            return "main kuyruk ucuna ff olmadi"
        if s.push_sayisi("main") != 1 or s.push_sayisi("urun-kuyruk") != 0:
            return "push sayisi"
        if s.dispatchler()[:1] != ["deploy.yml"] or "nobet.yml" in s.dispatchler():
            return "dispatch listesi %s" % s.dispatchler()
    v.append(("V5-BIRLESTI-ff", v5_kur, v5_dog))

    def v6_kur(s):
        taban = s.uzak("main")
        k = kur_kuyruk_urun(s)
        m = main_ilerlet(s)
        return {}, True, {"k": k, "m": m, "taban": taban}

    def v6_dog(s, rc, satir, b):
        if rc != 0 or "KUYRUK=BIRLESTI" not in satir or "yol=merge" not in satir:
            return "rc/satir"
        yeni = s.uzak("main")
        s.g(s.yazar, "fetch", "-q", "origin")
        ebeveyn = s.g(s.yazar, "rev-list", "--parents", "-n", "1", yeni).split()[1:]
        if ebeveyn != [b["m"], b["k"]]:
            return "merge ebeveynleri %s" % ebeveyn
        if s.uzak("urun-kuyruk") != yeni:
            return "kuyruk senkronlanmadi"
        icerik = s.g(s.yazar, "show", "%s:urunler.json" % yeni)
        if '"c"' not in icerik or s.g(s.yazar, "show", "%s:kod.txt" % yeni) != "kod-2":
            return "merge icerigi eksik"
        if not s.dispatchler():
            return "dispatch yok"
    v.append(("V6-BIRLESTI-merge", v6_kur, v6_dog))

    def v7_kur(s):
        kur_kuyruk_urun(s, "[\n\"KUYRUK\",\n\"b\"\n]\n")
        m = main_ilerlet(s, "urunler.json", "[\n\"MAIN\",\n\"b\"\n]\n")
        return {}, True, {"main": m}

    def red_dog(onek):
        def dog(s, rc, satir, b):
            if rc != 1 or not satir.startswith(onek):
                return "rc/satir"
            if s.push_sayisi() or s.dispatchler():
                return "RED iken push=%d dispatch=%d" % (s.push_sayisi(), len(s.dispatchler()))
            if s.uzak("main") != b["main"]:
                return "main degisti"
            if os.path.exists(os.path.join(s.ci, ".git", "MERGE_HEAD")):
                return "merge yarim kaldi (abort yok)"
        return dog
    v.append(("V7-CAKISMA", v7_kur, red_dog("KUYRUK=CAKISMA")))

    def v8_kur(s):
        s.yaz("index.html", "<p>2</p>\n")
        kur_kuyruk_urun(s)
        return {}, True, {"main": s.uzak("main")}
    v.append(("V8-yabanci-yol", v8_kur,
              red_dog("KUYRUK=RED sebep=yabanci-yol yollar=index.html")))

    def v9_kur(s):
        s.yaz("tools/sizdir.py", "x = 1\n")
        s.commit("gizli ekle")
        os.remove(os.path.join(s.yazar, "tools", "sizdir.py"))
        s.commit("gizli geri al")
        kur_kuyruk_urun(s)
        return {}, True, {"main": s.uzak("main")}
    v.append(("V9-gizli-yabanci", v9_kur,
              red_dog("KUYRUK=RED sebep=yabanci-yol yollar=tools/sizdir.py")))

    def v10_kur(s):
        k = kur_kuyruk_urun(s)
        yan = os.path.join(s.kok, "yan")
        s.g(None, "clone", "-q", s.origin, yan)
        s.yaz("kod.txt", "yaris\n", dizin=yan)
        y = s.commit("kod: yaris", dizin=yan)
        bayrak = os.path.join(s.kok, "yaris.bayrak")
        open(bayrak, "w").close()
        return {"SAHTE_YARIS_BAYRAK": bayrak, "SAHTE_YARIS_KLON": yan}, True, {"k": k, "y": y}

    def v10_dog(s, rc, satir, b):
        if rc != 0 or "KUYRUK=BIRLESTI" not in satir or "yol=merge" not in satir:
            return "rc/satir"
        yeni = s.uzak("main")
        s.g(s.yazar, "fetch", "-q", "origin")
        for gerekli in (b["k"], b["y"]):
            if subprocess.run([GERCEK_GIT, "-C", s.yazar, "merge-base", "--is-ancestor",
                               gerekli, yeni], env=s.env).returncode != 0:
                return "main %s icermiyor" % gerekli[:12]
        if s.push_sayisi("main") != 2:
            return "main push denemesi %d (beklenen 2)" % s.push_sayisi("main")
    v.append(("V10-push-yarisi", v10_kur, v10_dog))

    def v11_kur(s):
        kur_kuyruk_urun(s)
        return {"SAHTE_GH_RC": "1"}, True, {"main": s.uzak("main")}

    def v11_dog(s, rc, satir, b):
        if (rc, satir) != (2, "KUYRUK=OLCULEMEDI sebep=gh-run-list"):
            return "rc/satir"
        if s.push_sayisi() or s.uzak("main") != b["main"]:
            return "gh olculemezken push"
    v.append(("V11-gh-hata", v11_kur, v11_dog))

    def v12_kur(s):
        k = kur_kuyruk_urun(s)
        return {"SAHTE_GH_DISPATCH_RC": "1"}, True, {"k": k}

    def v12_dog(s, rc, satir, b):
        if rc != 1 or not satir.startswith("KUYRUK=DISPATCH-HATA sha=%s" % b["k"][:12]):
            return "rc/satir"
    v.append(("V12-dispatch-hata", v12_kur, v12_dog))

    def sifir_cagri(beklenen_rc, onek):
        def dog(s, rc, satir, b):
            if rc != beklenen_rc or not satir.startswith(onek):
                return "rc/satir"
            if s.cagrilar():
                return "%d cagri yapildi" % len(s.cagrilar())
        return dog

    def v13_kur(s):
        kur_kuyruk_urun(s)
        return {"GITHUB_WORKFLOW": "Build & deploy to GitHub Pages"}, False, {}
    v.append(("V13-baglam-disi", v13_kur, sifir_cagri(1, "KUYRUK=RED sebep=baglam-disi")))

    def v14_kur(s):
        kur_kuyruk_urun(s)
        return {"PRUVO_K80_IC_KOSUM": "1"}, True, {}
    v.append(("V14-K80-PROVA", v14_kur, sifir_cagri(0, "KUYRUK=PROVA")))

    def v16_kur(s):
        k = kur_kuyruk_urun_tarihli(s, tarih_dk_geri(7))
        return {"SAHTE_GH_RUNS": json.dumps([{"status": "in_progress", "databaseId": 42}]),
                "PRUVO_KUYRUK_ACLIK_DK": "5"}, True, {"k": k}

    def v16_dog(s, rc, satir, b):
        if rc != 0 or not satir.startswith("KUYRUK=BIRLESTI sha=%s yol=ff dispatch=deploy.yml" % b["k"][:12]):
            return "rc/satir: %r" % satir
        if "aclik=1" not in satir:
            return "aclik=1 yok: %r" % satir
        if "bekleme_dk=" not in satir:
            return "bekleme_dk= yok: %r" % satir
        if "nobet.yml" in satir:
            return "beklenmeyen nobet dispatch"
        if s.uzak("main") != b["k"]:
            return "main ff olmadi"
        if not s.dispatchler():
            return "Pages kosarken aclik kolu dispatch etmedi"
    v.append(("V16-BIRLESTI-aclik", v16_kur, v16_dog))

    def v17_kur(s):
        kur_kuyruk_urun_tarihli(s, tarih_dk_geri(3))
        return {"SAHTE_GH_RUNS": json.dumps([{"status": "in_progress", "databaseId": 99}]),
                "PRUVO_KUYRUK_ACLIK_DK": "5"}, True, {"main": s.uzak("main")}

    def v17_dog(s, rc, satir, b):
        if (rc, satir) != (0, "KUYRUK=BEKLE pages=99"):
            return "rc/satir: %r" % satir
        if "aclik" in satir:
            return "beklenmeyen aclik: %r" % satir
        if s.uzak("main") != b["main"]:
            return "main degisti"
        if s.push_sayisi() or s.dispatchler():
            return "BEKLE iken push=%d dispatch=%d" % (s.push_sayisi(), len(s.dispatchler()))
    v.append(("V17-BEKLE-aclik-yok", v17_kur, v17_dog))

    def v18_kur(s):
        k = kur_kuyruk_urun_tarihli(s, tarih_dk_geri(7))
        return {"PRUVO_KUYRUK_ACLIK_DK": "5"}, True, {"k": k}

    def v18_dog(s, rc, satir, b):
        if rc != 0 or not satir.startswith("KUYRUK=BIRLESTI sha=%s yol=ff dispatch=deploy.yml" % b["k"][:12]):
            return "rc/satir: %r" % satir
        if "aclik=" in satir:
            return "beklenmeyen aclik alani (Pages kosmuyor): %r" % satir
    v.append(("V18-BIRLESTI-aclik-yok", v18_kur, v18_dog))

    # ── K441 (13 Eki 2026): parametrik kayit SEMASIZ main'e giremez ────────────────────────
    # Kuyruk yalniz urunler.json tasir (sema = kod; yabanci-yol RED) -> SIRA: once sema main'e,
    # sonra kayit kuyruga. Olculen olay: 009b7315 saksi-vazo kaydi semasiz girdi, deploy 40+ dk
    # SKIPPED kaldi (alakasiz bir test kirmizisi asil kusuru gizledi).
    sema_yok = json.dumps([{"id": "a"}, {"id": "olcuye-ozel-test", "parametrik": True}])

    def v19_kur(s):
        kur_kuyruk_urun(s, sema_yok)
        return {}, True, {"main": s.uzak("main")}
    v.append(("V19-RED-semasiz-parametrik", v19_kur,
              red_dog("KUYRUK=RED sebep=semasiz-parametrik ids=olcuye-ozel-test")))

    def v20_kur(s):
        s.yaz("jenerator/urunler/olcuye-ozel-test.json", "{}\n")
        s.commit("sema: once main'e")
        s.g(s.yazar, "push", "-q", "origin", "HEAD:main")
        k = kur_kuyruk_urun(s, sema_yok)
        return {}, True, {"k": k}

    def v20_dog(s, rc, satir, b):
        if rc != 0 or not satir.startswith("KUYRUK=BIRLESTI sha=%s yol=ff" % b["k"][:12]):
            return "rc/satir: %r" % satir
        if s.uzak("main") != b["k"]:
            return "main kuyruk ucuna ff olmadi"
    v.append(("V20-BIRLESTI-sema-main'de", v20_kur, v20_dog))

    def v21_kur(s):
        # GECMIS BORC: semasiz parametrik kayit ZATEN main'de; kuyruk alakasiz bir kayit ekler.
        s.yaz("urunler.json", sema_yok)
        s.commit("borc: semasiz parametrik main'de")
        s.g(s.yazar, "push", "-q", "origin", "HEAD:main")
        k = kur_kuyruk_urun(s, json.dumps(
            [{"id": "a"}, {"id": "olcuye-ozel-test", "parametrik": True}, {"id": "yeni-duz"}]))
        return {}, True, {"k": k}
    v.append(("V21-BIRLESTI-gecmis-borc-tetiklemez", v21_kur, v20_dog))

    def v22_kur(s):
        kur_kuyruk_urun(s, "[ bozuk json")
        return {}, True, {"main": s.uzak("main")}

    def v22_dog(s, rc, satir, b):
        if rc != 2 or not satir.startswith(
                "KUYRUK=OLCULEMEDI sebep=urunler-json-ayristirilamadi"):
            return "rc/satir: %r" % satir
        if s.push_sayisi() or s.dispatchler() or s.uzak("main") != b["main"]:
            return "olculemezken push/dispatch/main degisimi"
    v.append(("V22-OLCULEMEDI-bozuk-urunler-json", v22_kur, v22_dog))

    # ── YAPISAL BIRLESIM (14 Eki 2026): main de kuyruk da diziye BASTAN ekler -> metin
    # cakismasi; cakisan yol kumesi TAM {urunler.json} ise id ile uc-yollu birlesim.
    def y_kur(taban, kuyruk, main_l, main_metin=None, kuyruk_ek=None, main_ek=None):
        def kur(s):
            s.yaz("urunler.json", kanonik(taban))
            s.commit("taban: kanonik urunler")
            s.g(s.yazar, "push", "-q", "origin", "HEAD:main")
            for yol, metin in (kuyruk_ek or {}).items():
                s.yaz(yol, metin)
            k = kur_kuyruk_urun(s, kanonik(kuyruk))
            s.g(s.yazar, "checkout", "-q", "--detach", s.uzak("main"))
            s.yaz("urunler.json", main_metin if main_metin is not None else kanonik(main_l))
            for yol, metin in (main_ek or {}).items():
                s.yaz(yol, metin)
            m = s.commit("urun: main tarafi")
            s.g(s.yazar, "push", "-q", "origin", "HEAD:main")
            return {}, True, {"main": m, "k": k}
        return kur

    def y_birlesti(beklenen_ids, sayim):
        def dog(s, rc, satir, b):
            if rc != 0 or not satir.startswith("KUYRUK=BIRLESTI") or " yol=yapisal " not in satir:
                return "rc/satir: %r" % satir
            if " eklenen=%d silinen=%d degisen=%d" % sayim not in satir:
                return "sayim alani: %r" % satir
            yeni = s.uzak("main")
            s.g(s.yazar, "fetch", "-q", "origin")
            ebeveyn = s.g(s.yazar, "rev-list", "--parents", "-n", "1", yeni).split()[1:]
            if ebeveyn != [b["main"], b["k"]]:
                return "ebeveynler %s (ilk main olmali)" % ebeveyn
            if s.g(s.yazar, "log", "-1", "--format=%s", yeni) != \
                    "urun-kuyruk: urun-kuyruk -> main birlestirme":
                return "merge mesaji degisti"
            metin = s.g(s.yazar, "show", "%s:urunler.json" % yeni)
            ids = [u["id"] for u in json.loads(metin)]
            if ids != beklenen_ids:
                return "sonuc id sirasi %s != %s" % (ids, beklenen_ids)
            if metin != kanonik(json.loads(metin)):
                return "sonuc kanonik bicimde degil"
            if s.push_sayisi("main") != 1 or s.uzak("urun-kuyruk") != yeni:
                return "push/senkron"
        return dog

    def y_cakisma(sebep):
        taban_dog = red_dog("KUYRUK=CAKISMA main=")

        def dog(s, rc, satir, b):
            beklenen = "KUYRUK=CAKISMA main=%s kuyruk=%s" % (b["main"][:12], b["k"][:12])
            if sebep:
                beklenen += " sebep=" + sebep
            if satir != beklenen:
                return "satir %r != %r" % (satir, beklenen)
            return taban_dog(s, rc, satir, b)
        return dog

    a, bb, c = {"id": "a", "ad": "A"}, {"id": "b", "ad": "B"}, {"id": "c", "ad": "C"}
    k1, m1 = {"id": "k1", "ad": "K1"}, {"id": "m1", "ad": "M1"}
    v.append(("Y1-yapisal-iki-taraf-basa-ekledi",
              y_kur([a, bb], [k1, a, bb], [m1, a, bb]),
              y_birlesti(["k1", "m1", "a", "b"], (1, 0, 0))))
    v.append(("Y2-yapisal-main-sildi-korunur",
              y_kur([a, bb, c], [k1, a, bb, c], [m1, a, bb]),
              y_birlesti(["k1", "m1", "a", "b"], (1, 0, 0))))
    v.append(("Y3-cift-ekleme",
              y_kur([a, bb], [{"id": "x", "ad": "K"}, a, bb], [{"id": "x", "ad": "M"}, a, bb]),
              y_cakisma("cift-ekleme")))
    v.append(("Y4-cift-degisiklik",
              y_kur([a, bb], [k1, {"id": "a", "ad": "AK"}, bb], [m1, {"id": "a", "ad": "AM"}, bb]),
              y_cakisma("cift-degisiklik")))
    v.append(("Y5-sil-degistir",
              y_kur([a, bb, c], [k1, a, bb, {"id": "c", "ad": "CK"}], [m1, a, bb]),
              y_cakisma("sil-degistir")))
    v.append(("Y6-urunler-ve-kod-cakisti",
              y_kur([a, bb], [k1, a, bb], [m1, a, bb],
                    kuyruk_ek={"kod.txt": "kod-K\n"}, main_ek={"kod.txt": "kod-M\n"}),
              y_cakisma(None)))
    v.append(("Y7-bicim-bozuk-main",
              y_kur([a, bb], [k1, a, bb], None,
                    main_metin=json.dumps([m1, a, bb], ensure_ascii=False, indent=4)),
              y_cakisma("bicim")))
    x = {"id": "x", "ad": "X"}
    v.append(("Y8-ozdes-ekleme-tek-kopya",
              y_kur([a, bb], [k1, x, a, bb], [m1, x, a, bb]),
              y_birlesti(["k1", "m1", "x", "a", "b"], (1, 0, 0))))
    return v


def kanonik(liste):
    """Depodaki yazicinin bicimi (tools/duzelt.py::_atomic_write) — fikstur tabani."""
    return json.dumps(liste, ensure_ascii=False, indent=2)


def dispatch_vakasi():
    spec = importlib.util.spec_from_file_location("urun_kuyruk", ARAC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    dispatch, atlanan = mod.dispatch_listesi()
    if dispatch[:1] != ["deploy.yml"]:
        return "deploy.yml ilk degil: %s" % dispatch
    for haric in ("nobet.yml", "urun-kuyruk.yml"):
        if haric in dispatch or "%s(haric)" % haric not in atlanan:
            return "%s haric degil: %s / %s" % (haric, dispatch, atlanan)
    # Capraz olcum (turetimden BAGIMSIZ, metin): dispatch'e giren her dosya
    # workflow_dispatch tasir VE push tetigi main dalindadir.
    for ad in dispatch:
        with open(os.path.join(KOK, ".github", "workflows", ad), encoding="utf-8") as f:
            metin = f.read()
        if "workflow_dispatch" not in metin:
            return "%s workflow_dispatch tasimiyor" % ad
        if not re.search(r"^  push:\n    branches: \[main\]$", metin, re.M):
            return "%s push tetigi main'de degil" % ad
    print("      dispatch=%s atlanan=%s" % (",".join(dispatch), ",".join(atlanan)))
    return None


def vaka_kos(kimlik, kur, dog, sahte, gecici, arac=ARAC):
    s = Sahne(os.path.join(gecici, kimlik))
    env_ek, test_kok, baglam = kur(s)
    s.ci_klonla()
    rc, satir, cikti = kos(s, sahte, arac=arac, env_ek=env_ek, test_kok=test_kok)
    hata = dog(s, rc, satir, baglam)
    return hata, rc, satir, cikti


def izole_kopya(kok, mutasyon=None):
    os.makedirs(os.path.join(kok, "tools"))
    with open(ARAC, encoding="utf-8") as f:
        govde = f.read()
    if mutasyon:
        eski, yeni = mutasyon
        if govde.count(eski) != 1:
            raise SystemExit("MUTANT CAPASI TUTMADI (%d eslesme): %r" % (govde.count(eski), eski))
        govde = govde.replace(eski, yeni)
    hedef = os.path.join(kok, "tools", "urun-kuyruk-birlestir.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(govde)
    return hedef


MUTANTLAR = [
    ("M-BOS", "BOS erken donusu silindi",
     ('        return "KUYRUK=BOS sebep=geride", 0  # MUTANT-CAPA:BOS',
      '        pass  # MUTANT BOS'), "V3-BOS-geride"),
    ("M-YOL", "yabanci yol kapisi kapatildi",
     ("    if yabanci:  # MUTANT-CAPA:YOL", "    if False:  # MUTANT YOL"), "V8-yabanci-yol"),
    ("M-SEMA", "semasiz parametrik kapisi kapatildi (K441)",
     ("    if semasiz:  # MUTANT-CAPA:SEMA", "    if False:  # MUTANT SEMA"),
     "V19-RED-semasiz-parametrik"),
    ("M-ACIK-KALDIR", "aclik kolu kaldirildi (Pages kosarken yine BEKLE)",
     ("    if bitmemis:  # MUTANT-CAPA:ACIK\n        yas_dk = kuyruk_yasi_dk()\n"
      "        if yas_dk < ACIK_DK:\n"
      "            return \"KUYRUK=BEKLE pages=%s\" % bitmemis[0].get(\"databaseId\"), 0\n"
      "        aclik_bilgi = \" aclik=1 bekleme_dk=%d\" % yas_dk",
      "    if bitmemis:\n"
      "        return \"KUYRUK=BEKLE pages=%s\" % bitmemis[0].get(\"databaseId\"), 0  # MUTANT ACLIK KALDIRILDI"),
     "V16-BIRLESTI-aclik"),
    ("M-ESIK-SIFIR", "ACIK_DK=0 (esik sifira cekildi, env override yutulur)",
     ("ACIK_DK = int(os.environ.get(\"PRUVO_KUYRUK_ACLIK_DK\", \"45\"))  # MUTANT-CAPA:ESIK",
      "ACIK_DK = 0  # MUTANT ESIK"), "V17-BEKLE-aclik-yok"),
    ("M-CAKISAN", "cakisan yol kumesi kontrolu kaldirildi (urunler.json + kod.txt yapisala girer)",
     ('            if cakisan != ["urunler.json"]:  # MUTANT-CAPA:CAKISAN',
      "            if False:  # MUTANT CAKISAN"), "Y6-urunler-ve-kod-cakisti"),
    ("M-CIFT-DEGISIKLIK", "cift-degisiklik kontrolu kaldirildi",
     ("    if any(k[i] != m[i] for i in k_deg & m_deg):  # MUTANT-CAPA:CIFT-DEGISIKLIK",
      "    if False:  # MUTANT CIFT-DEGISIKLIK"), "Y4-cift-degisiklik"),
    ("M-SILME", "silme korumasi kaldirildi (main'in sildigi kuyruktan geri gelir)",
     ("    eklenen = [i for i in k_sira if i not in t and i not in m]  # MUTANT-CAPA:SILME",
      "    eklenen = [i for i in k_sira if i not in m]  # MUTANT SILME"),
     "Y2-yapisal-main-sildi-korunur"),
    ("M-CIFT-EKLEME", "cift-ekleme kontrolu kaldirildi",
     ("        if uid not in t and uid in m and m[uid] != k[uid]:  # MUTANT-CAPA:CIFT-EKLEME",
      "        if False:  # MUTANT CIFT-EKLEME"), "Y3-cift-ekleme"),
]


def main():
    hata = 0
    gecici = tempfile.mkdtemp(prefix="urun-kuyruk-test-")
    try:
        sahte = sahte_kur(gecici)
        tablo = {v[0]: v for v in vakalar()}
        for kimlik, kur, dog in tablo.values():
            sorun, rc, satir, cikti = vaka_kos(kimlik, kur, dog, sahte, gecici)
            hata += bool(sorun)
            print("%s %s rc=%d | %s%s" % ("KIRMIZI" if sorun else "YESIL", kimlik, rc, satir,
                                          (" | SORUN: %s\n%s" % (sorun, cikti[-600:])) if sorun else ""))
        sorun = dispatch_vakasi()
        hata += bool(sorun)
        print("%s V15-dispatch-listesi%s" % ("KIRMIZI" if sorun else "YESIL",
                                             " | SORUN: %s" % sorun if sorun else ""))

        taban = izole_kopya(os.path.join(gecici, "taban-arac"))
        for _, _, _, hedef in MUTANTLAR:
            _, kur, dog = tablo[hedef]
            sorun, rc, satir, _ = vaka_kos("TABAN-" + hedef, kur, dog, sahte, gecici, arac=taban)
            hata += bool(sorun)
            print("%s TABAN-%s rc=%d | %s" % ("KIRMIZI" if sorun else "YESIL", hedef, rc, satir))
        for kimlik, aciklama, mutasyon, hedef in MUTANTLAR:
            kopya = izole_kopya(os.path.join(gecici, kimlik + "-arac"), mutasyon)
            _, kur, dog = tablo[hedef]
            sorun, rc, satir, _ = vaka_kos(kimlik + "-" + hedef, kur, dog, sahte, gecici, arac=kopya)
            hata += not sorun
            print("%s %s (%s) -> %s rc=%d | %s | %s" % (
                "YAKALANDI" if sorun else "KACTI", kimlik, aciklama, hedef, rc, satir, sorun))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    vaka = len(tablo) + 1
    print("SONUC: %s vaka=%d mutant=%d hata=%d" % ("YESIL" if hata == 0 else "KIRMIZI",
                                                   vaka, len(MUTANTLAR), hata))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())

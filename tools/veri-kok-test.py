#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""veri-kok-test.py — `veri_kok.py` COZUM SIRASI + KUM (sandbox) ANLAMI kabul testi.

NEDEN (18 Eyl 2026, Build & deploy run 35294096925 KIRMIZI, yayin DURDU): 7 urun araci
(d1-sync / denetim-kapisi / duzelt / mukerrer-kontrol / parti-kontrol / r2-upload /
thumbnail-uret) veri kokunu `veri_kok.py`'den cozmeye basladi; araci gecici koke KOPYALAYAN
testlerin ELLE yazili yardimci listesinde `veri_kok.py` yoktu -> FileNotFoundError. Onarim
iki parca: (a) kok sirasi env `PRUVO_VERI_KOK` -> git ortak-dizin -> `__file__`; kopyalayan
test override'i KENDI kumuna kurar (git/__file__ sansina birakmaz); (b) kopya kumesi
import'lardan TURETILIR (`veri_kok.kum_kur`), elle liste yok.

IDDIALAR
  S1-S6  sira + fail-closed birim: override > git > __file__; bos/dizin-olmayan override
         SystemExit (sessiz dusus YOK); override == kod koku -> uyari yok.
  T1     7 aracin HER BIRI yalniz `kum_kur`'un turettigi kapanisla gecici koke kurulur,
         modul olarak YUKLENIR ve veri koku = kum (FileNotFoundError yok).
  K1 (i)   gecici kokte 1 sahte urun: duzelt.py O urunu bulup duzeltir (rc 0) ve
           denetim-kapisi.py "yeni urun: 1" basar (canli katalog sayisi DEGIL).
  K2 (ii)  linked worktree'den BAYRAKSIZ denetim-kapisi.py ANA kopyanin calisma agacina
           gore sayar: 1. Ayni kurulumda eski ROOT (kod koku) mutanti: 0 (17 Eyl mutanti).
  K3 (iii) override KALDIRILINCA K1 yine gecici kokte kalir (canliya dusmez).
  K4       GIT_DIR mirasi (CI/kanca baglami) varken override'siz kok CANLIYA duser (tehlike
           kaniti; yalniz modul yuklenir, YAZMA YOK), override ile kumda kalir.
  C1       canli katalog (bu checkout'un veri koku) sha256 ONCE = SONRA.

--mutasyon: `veri_kok.py`'nin mutantlari kum kopyasinda kosulur; her biri en az bir iddiayi
KIRMIZI yakmali, zararsiz kontrol YESIL kalmali. Canli `tools/veri_kok.py`'ye DOKUNULMAZ.

Cikis: 0 = hepsi YESIL (mutasyon kipinde: tum mutantlar OLDU + kontrol YESIL); aksi 1.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True

# TEK KAYNAK: sentetik depolardaki git cagrilari `git_ortami.sentetik_git` uzerinden.
from git_ortami import sentetik_git  # noqa: E402

_vk_spec = importlib.util.spec_from_file_location("veri_kok", os.path.join(TOOLS, "veri_kok.py"))
vk = importlib.util.module_from_spec(_vk_spec)
_vk_spec.loader.exec_module(vk)

# Veri kokunu tutan modul degiskeni (arac -> ad). Kaynakta ELLE capa; T1 yanlissa KIRMIZI.
KOK_DEGISKENI = {
    "d1-sync.py": "KOK",
    "denetim-kapisi.py": "ROOT",
    "duzelt.py": "ROOT",
    "mukerrer-kontrol.py": "ROOT",
    "parti-kontrol.py": "ROOT",
    "r2-upload.py": "_VERI_KOK",
    "thumbnail-uret.py": "REPO",
}
KANCA_YOK = "/var/empty/veri-kok-test-kanca-yok"
SAHTE_ID = "veri-kok-test-sahte-1"
ENV_AD = "PRUVO_VERI_KOK"          # BAGIMSIZ capa (vk.ENV_AD'dan okunmaz)

# Modulu __main__ OLMADAN yukleyip veri koku degiskenini basan yukleyici (yan etkisiz:
# araclarin govdesi `if __name__ == "__main__"` arkasinda).
YUKLEYICI = (
    "import importlib.util,sys\n"
    "s=importlib.util.spec_from_file_location('arac_kum_yukleme', sys.argv[1])\n"
    "m=importlib.util.module_from_spec(s)\n"
    "s.loader.exec_module(m)\n"
    "print('VERI_KOKU=' + str(getattr(m, sys.argv[2])))\n"
)

SONUC = []


def iddia(ad, kosul, detay=""):
    SONUC.append((ad, bool(kosul)))
    print(("  ✔ " if kosul else "  ✘ ") + ad
          + (("   [%s]" % str(detay)[:400]) if (detay and not kosul) else ""))


def ortam(**ek):
    """Miras git/CI baglami ve override TEMIZLENMIS ortam (+ ek)."""
    e = {k: v for k, v in os.environ.items()
         if not (k.startswith("GIT_") or k.startswith("GITHUB_") or k == ENV_AD)}
    e.update(ek)
    return e


def git(depo, *a):
    p = sentetik_git(depo, *a,
                     ayarlar=("-c", "core.hooksPath=" + KANCA_YOK, "-c", "commit.gpgsign=false"),
                     capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("git %s rc=%d: %s" % (" ".join(a), p.returncode, p.stderr.strip()))
    return p.stdout.strip()


def sha(yol):
    if not os.path.exists(yol):
        return None
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def urun(uid):
    return {"id": uid, "kategori": "Ev", "marka": ["X"], "baslik": "Sahte " + uid,
            "aciklama": "a", "fiyat": "100 TL",
            "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}


def katalog_yaz(kok, liste):
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)


def katalog_oku(kok):
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        return json.load(f)


def kum(tmp, ad, git_ile=True):
    """<tmp>/<ad>: tools/{duzelt,denetim-kapisi}+TURETILMIS kapanis, bos katalog, taban commit."""
    d = os.path.join(tmp, ad)
    vk.kum_kur(os.path.join(d, "tools"), {"duzelt.py": None, "denetim-kapisi.py": None}, TOOLS)
    katalog_yaz(d, [])
    if git_ile:
        git(d, "init", "-q")
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "taban")
    return d


def kos(argv, env, cwd):
    p = subprocess.run([sys.executable] + list(argv), capture_output=True, text=True,
                       env=env, cwd=cwd, timeout=600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def yeni_urun_sayisi(cikti):
    for satir in cikti.splitlines():
        if "=== DENETIM KAPISI === yeni urun:" in satir:
            try:
                return int(satir.rsplit(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def yukle(betik, degisken, env, stub):
    env = dict(env)
    env["PYTHONPATH"] = stub + os.pathsep + env.get("PYTHONPATH", "")
    rc, out = kos(["-c", YUKLEYICI, betik, degisken], env, os.path.dirname(betik))
    for satir in out.splitlines():
        if satir.startswith("VERI_KOKU="):
            return rc, satir[len("VERI_KOKU="):], out
    return rc, None, out


def ayni(a, b):
    return bool(a) and bool(b) and os.path.realpath(a) == os.path.realpath(b)


# ── vakalar ──────────────────────────────────────────────────────────────────────

def birim(tmp):
    wt = "/x/ana/.claude/worktrees/w1/tools/a.py"
    k, v, u = vk.cozumle(wt, _git=lambda _k: "/x/ana/.git", _ortam={ENV_AD: tmp})
    iddia("S1 override git'ten ONCE gelir (worktree'de bile veri = override)", v == tmp, v)
    k, v, u = vk.cozumle(wt, _git=lambda _k: "/x/ana/.git", _ortam={})
    iddia("S2 override yoksa git ortak-dizin: linked worktree -> ANA kopya",
          v == "/x/ana" and u, v)
    k, v, u = vk.cozumle("/x/dis/tools/a.py", _git=lambda _k: None, _ortam={})
    iddia("S3 override+git yoksa __file__ -> kod koku", v == "/x/dis" and u is None, v)
    for ad, deger in (("S4 BOS override", "  "),
                      ("S5 dizin OLMAYAN override", os.path.join(tmp, "yok-boyle-dizin"))):
        try:
            k, v, u = vk.cozumle(wt, _git=lambda _k: "/x/ana/.git", _ortam={ENV_AD: deger})
            iddia(ad + " FAIL-CLOSED (SystemExit; sessizce git/__file__'a dusmez)", False,
                  "dondu: %s" % v)
        except SystemExit:
            iddia(ad + " FAIL-CLOSED (SystemExit; sessizce git/__file__'a dusmez)", True)
    kod = os.path.join(tmp, "s6")
    os.makedirs(os.path.join(kod, "tools"))
    k, v, u = vk.cozumle(os.path.join(kod, "tools", "a.py"), _git=lambda _k: None,
                         _ortam={ENV_AD: kod})
    iddia("S6 override == kod koku -> uyari YOK", v == kod and u is None, u)


def t1(tmp, stub):
    for ad, degisken in sorted(KOK_DEGISKENI.items()):
        d = os.path.join(tmp, "t1-" + ad[:-3])
        kardes = vk.kum_kur(os.path.join(d, "tools"), {ad: None}, TOOLS)
        # .py DISI kod varligi: parti-kontrol -> kategori-kapisi import aninda CATEGORIES'i
        # KOD kokundeki index.html'den okur (K420: kod yollari _KOD_KOK'tan).
        shutil.copy(os.path.join(os.path.dirname(TOOLS), "index.html"), d)
        rc, kok, out = yukle(os.path.join(d, "tools", ad), degisken,
                             vk.kum_ortami(d, ortam()), stub)
        iddia("T1 %s: turetilmis kapanis (%d kardes, veri_kok.py %s) ile YUKLENDI, veri = kum"
              % (ad, len(kardes), "VAR" if "veri_kok.py" in kardes else "YOK"),
              rc == 0 and ayni(kok, d) and "veri_kok.py" in kardes,
              "rc=%s kok=%s %s" % (rc, kok, out[-300:]))


def k1_k3(tmp, override):
    etiket = "K1 (i)" if override else "K3 (iii) override KALDIRILDI"
    d = kum(tmp, "k1" if override else "k3")
    katalog_yaz(d, [urun(SAHTE_ID)])
    env = vk.kum_ortami(d, ortam()) if override else ortam()
    rc, out = kos([os.path.join(d, "tools", "denetim-kapisi.py")], env, tmp)
    n = yeni_urun_sayisi(out)
    iddia("%s denetim-kapisi.py gecici kokteki 1 sahte urunu gordu (yeni urun: 1)" % etiket,
          n == 1, "n=%s rc=%d %s" % (n, rc, out[-300:]))
    rc, out = kos([os.path.join(d, "tools", "duzelt.py"), SAHTE_ID,
                   "--alan", "baslik", "--deger", "Duzeltildi"], env, tmp)
    kayit = katalog_oku(d)
    iddia("%s duzelt.py gecici kokteki sahte urunu BULDU ve duzeltti (rc 0)" % etiket,
          rc == 0 and len(kayit) == 1 and kayit[0].get("baslik") == "Duzeltildi",
          "rc=%d %s" % (rc, out[-300:]))


def k2(tmp):
    ana = kum(tmp, "k2-ana")
    wt = os.path.join(tmp, "k2-wt")
    git(ana, "worktree", "add", "-q", "-b", "yan", wt)
    katalog_yaz(ana, [urun(SAHTE_ID)])        # ANA kopyada commit'siz 1 urun (MaCiT partisi)
    kapi = os.path.join(wt, "tools", "denetim-kapisi.py")
    rc, out = kos([kapi], ortam(), wt)
    n = yeni_urun_sayisi(out)
    iddia("K2 (ii) linked worktree'den BAYRAKSIZ denetim-kapisi.py ANA koke gore sayar (1)",
          n == 1, "n=%s rc=%d %s" % (n, rc, out[-300:]))
    # 17 Eyl mutanti: eski ROOT = kod koku (worktree) -> kor nobetci 0 basar.
    vk_wt = os.path.join(wt, "tools", "veri_kok.py")
    if not os.path.isfile(vk_wt):
        iddia("K2 kum kapanisi veri_kok.py'yi TASIDI", False, "yok: %s" % vk_wt)
        return
    with open(vk_wt, encoding="utf-8") as f:
        metin = f.read()
    capa = "    kod_kok = os.path.dirname(os.path.dirname(os.path.abspath(betik_dosyasi)))\n"
    if metin.count(capa) != 1:
        iddia("K2 eski-ROOT mutant capasi TEKIL", False, "capa %d kez" % metin.count(capa))
        return
    with open(vk_wt, "w", encoding="utf-8") as f:
        f.write(metin.replace(capa, capa + "    return kod_kok, kod_kok, None  # MUTANT\n"))
    rc, out = kos([kapi], ortam(), wt)
    n0 = yeni_urun_sayisi(out)
    iddia("K2 eski-ROOT (kod koku) mutanti ayni kurulumda 0 basar (kor nobetci ayirt edildi)",
          n0 == 0, "n=%s rc=%d %s" % (n0, rc, out[-300:]))


def k4(tmp, stub):
    ortak = vk._git_ortak_dizin(os.path.dirname(TOOLS))
    if not ortak:
        iddia("K4 bu checkout git deposu (GIT_DIR tehlike kaniti olculebilir)", False, "git yok")
        return
    if not os.path.isabs(ortak):
        ortak = os.path.join(os.path.dirname(TOOLS), ortak)
    ortak = os.path.normpath(ortak)
    canli = os.path.dirname(ortak)
    d = os.path.join(tmp, "k4")
    vk.kum_kur(os.path.join(d, "tools"), {"duzelt.py": None}, TOOLS)
    katalog_yaz(d, [urun(SAHTE_ID)])
    rc, kok, out = yukle(os.path.join(d, "tools", "duzelt.py"), "ROOT",
                         ortam(GIT_DIR=ortak), stub)
    iddia("K4 TEHLIKE KANITI: GIT_DIR mirasi + override YOK -> kopya aracin veri koku CANLI "
          "checkout'a duser (yalniz yuklendi, yazma YOK)", ayni(kok, canli),
          "kok=%s canli=%s %s" % (kok, canli, out[-200:]))
    rc, kok, out = yukle(os.path.join(d, "tools", "duzelt.py"), "ROOT",
                         vk.kum_ortami(d, ortam(GIT_DIR=ortak)), stub)
    iddia("K4 ayni GIT_DIR mirasinda override KURULUNCA veri koku kumda kalir", ayni(kok, d),
          "kok=%s %s" % (kok, out[-200:]))


def stub_kur(tmp):
    """Ag/goruntu kutuphaneleri yalniz modul YUKLEMESI icin sahtelenir (T1/K4)."""
    stub = os.path.join(tmp, "sahte-bagimlilik")
    os.makedirs(os.path.join(stub, "boto3"))
    os.makedirs(os.path.join(stub, "PIL"))
    for yol in (("boto3", "__init__.py"), ("PIL", "__init__.py"), ("PIL", "Image.py"),
                ("PIL", "ImageOps.py")):
        with open(os.path.join(stub, *yol), "w", encoding="utf-8") as f:
            f.write("")
    return stub


def kabul():
    canli_kok = vk.cozumle(os.path.abspath(__file__), _ortam={})[1]
    canli = [os.path.join(canli_kok, a) for a in ("urunler.json", ".urun-kaynaklari.json")]
    once = [sha(y) for y in canli]
    tmp = tempfile.mkdtemp(prefix="veri-kok-test-")
    try:
        stub = stub_kur(tmp)
        print("== S: cozum sirasi (birim) ==")
        birim(tmp)
        print("== T1: 7 arac turetilmis kumda ==")
        t1(tmp, stub)
        print("== K: kabul mutanti (i)(ii)(iii) + GIT_DIR ==")
        k1_k3(tmp, override=True)
        k2(tmp)
        k1_k3(tmp, override=False)
        k4(tmp, stub)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    sonra = [sha(y) for y in canli]
    iddia("C1 canli katalog sha256 ONCE = SONRA (%s)" % canli_kok, once == sonra,
          "%s -> %s" % (once, sonra))
    kirmizi = [ad for ad, ok in SONUC if not ok]
    print("IDDIA SAYISI: %d" % len(SONUC))
    print("KIRMIZI IDDIA: %s" % (", ".join(k.split(" ")[0] for k in kirmizi) or "-"))
    print("SONUC: %s — %d/%d" % ("YESIL" if not kirmizi else "KIRMIZI",
                                 len(SONUC) - len(kirmizi), len(SONUC)))
    return 0 if not kirmizi else 1


# ── mutasyon ─────────────────────────────────────────────────────────────────────

MUTANTLAR = (
    ("M1_OVERRIDE_YOK_SAYILDI",
     "    ov = _override(kod_kok, os.environ if _ortam is None else _ortam)\n",
     "    ov = None\n", True),
    ("M2_ESKI_ROOT_KOD_KOKU",
     "    git = _git or _git_ortak_dizin\n",
     "    return kod_kok, kod_kok, None\n", True),
    ("M3_BOS_OVERRIDE_SESSIZ_DUSUS",
     "    if not ham.strip():\n        raise SystemExit(",
     "    if not ham.strip():\n        return None\n        raise SystemExit(", True),
    ("M4_KAPANIS_KOPYALANMADI",
     "    kardesler = sorted(kardes_kapanisi(kaynaklar, kaynak_tools))\n",
     "    kardesler = []\n", True),
    ("M5_DIZGE_KANITI_DUSTU",
     "                adlar.add(dugum.value)\n",
     "                pass\n", True),
    ("K0_ZARARSIZ_YORUM",
     "    git = _git or _git_ortak_dizin\n",
     "    git = _git or _git_ortak_dizin  # zararsiz\n", False),
)


def mutasyon():
    with open(os.path.join(TOOLS, "veri_kok.py"), encoding="utf-8") as f:
        temiz = f.read()
    kotu = 0
    for ad, eski, yeni, kirmizi_bekle in MUTANTLAR:
        if temiz.count(eski) != 1:
            print("✘ HARNESS BAYAT %s: capa %d kez (tam 1 olmali)" % (ad, temiz.count(eski)))
            kotu += 1
            continue
        d = tempfile.mkdtemp(prefix="veri-kok-mut-")
        try:
            # Kum = kendi git deposu olan mini checkout (K4 git ortak-dizini, T1 index.html
            # ister); testin KENDI "canli" koku de bu kum olur -> gercek katalog menzil disi.
            vk.kum_kur(os.path.join(d, "tools"), {"veri-kok-test.py": None}, TOOLS)
            shutil.copy(os.path.join(os.path.dirname(TOOLS), "index.html"), d)
            with open(os.path.join(d, "tools", "veri_kok.py"), "w", encoding="utf-8") as f:
                f.write(temiz.replace(eski, yeni))
            git(d, "init", "-q")
            git(d, "add", "-A")
            git(d, "commit", "-q", "-m", "mutant kum")
            rc, out = kos([os.path.join(d, "tools", "veri-kok-test.py")], ortam(), d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        kirmizi = [s.split(":", 1)[1].strip() for s in out.splitlines()
                   if s.startswith("KIRMIZI IDDIA:")]
        ozet = kirmizi[0] if kirmizi else "(ozet yok)"
        if kirmizi_bekle:
            ok = rc != 0
            print("%s MUTANT %s %s — KIRMIZI: %s" % ("✅" if ok else "❌", ad,
                                                    "OLDU" if ok else "YASADI", ozet))
        else:
            ok = rc == 0
            print("%s KONTROL %s %s" % ("✅" if ok else "❌", ad, "YESIL" if ok else
                                        "KIRMIZI: " + ozet))
        kotu += 0 if ok else 1
    print("MUTASYON: %d/%d beklentiye uydu" % (len(MUTANTLAR) - kotu, len(MUTANTLAR)))
    return 0 if kotu == 0 else 1


if __name__ == "__main__":
    if "--mutasyon" in sys.argv[1:]:
        sys.exit(mutasyon())
    sys.exit(kabul())

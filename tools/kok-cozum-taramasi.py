#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kok-cozum-taramasi.py — KANCADAN CAGRILAN araclarin DEPO KOKU cozumu,
GERCEK bir linked worktree'de, GERCEK bir pre-commit kancasinin ICINDEN olculur.

🔴 NEDEN VAR (6 Agu 2026, olculdu): `tools/diriltme-kapisi.py` bir worktree'de
pre-commit kancasindan kosarken depo kokunu `<worktree>/tools` cozup TUM commit'leri
rc=2 ile durdurdu. Sebep sinifsaldir, o dosyaya ozel DEGIL: git kancalari kosarken
ortama MUTLAK bir `GIT_DIR` IHRAC EDER; GIT_DIR set ve GIT_WORK_TREE yokken git
KESIF YAPMAZ ve `rev-parse --show-toplevel` CWD'yi kok sayar (`-C <yol>` verilse
bile). ANA CHECKOUT'ta git bu degiskeni kancaya HIC VERMEZ (bu surucunun olctugu
deger: `GIT_DIR='<yok>'`) -> orada kesif calisir ve sinif GORUNMEZ; bu yuzden
yillarca sessiz kalabilir. Bu surucu "hangi kardes arac ayni deseni tasiyor"
sorusunu BEYANLA degil OLCUMLE yanitlar — ve ihrac edilen degiskeni RAPORDA BASAR
ki "ana checkout'ta GIT_DIR goreli" gibi bir varsayim sessizce tasinmasin.

FIKSTUR DISIPLINI: GIT_DIR elle KURULMAZ ([[nobetci-fikstur-sekli]]) — gercek
`git worktree add` + gercek `git commit` kullanilir, ihrac edilen degiskenlerin TAM
kumesini git'in KENDISI belirler.

OLCULEN BIRIM: her aracin kaynagindaki KOK COZUM IFADESI, o baglamda HANGI yolu
dondururdu. Ana checkout kolu AYNI ifadeyle ayrica olculur (kontrol ekseni:
"her yerde mi bozuk, yoksa yalniz worktree'de mi").

Kullanim:  python3 tools/kok-cozum-taramasi.py
"""
import json
import os
import subprocess
import sys
import tempfile

# Taranan kume: `tools/kancalar/pre-commit` + `pre-push`in FIILEN cagirdigi araclar.
ARACLAR = ("diriltme-kapisi.py", "urunler-guard.py", "mukerrer-kontrol.py",
           "mimar-commit-kapisi.py", "kanca-kur.py", "commit-mesaji-kapisi.py")

# `diriltme-kapisi.py::git_ortami` ile AYNI SINIF kume (ikiz tanim: burada KOPYA degil,
# import edilemedigi icin ACIKCA yeniden yazilir ve sapmasi bu surucuyu YANILTMAZ —
# olculen sey "temizlenmis ortamda kok DOGRU mu"dur, kumenin kendisi degil).
KESIF_ORTAMI = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_PREFIX", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
                "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM")


def kos(*args, **kw):
    p = subprocess.run(args, capture_output=True, text=True, **kw)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def olc(agac):
    """Kanca baglaminda (cwd=<agac>, GIT_DIR ihrac EDILMIS) her aracin kok cozumu."""
    tools = os.path.join(agac, "tools")
    out = {"agac": agac, "GIT_DIR": os.environ.get("GIT_DIR", "<yok>"),
           "GIT_WORK_TREE": os.environ.get("GIT_WORK_TREE", "<yok>"), "araclar": {}}

    def kaydet(ad, ifade, deger, notu=None):
        out["araclar"][ad] = {"ifade": ifade, "kok": deger,
                              "dogru": deger == agac, "not": notu}

    # --- diriltme-kapisi.py::depo_kok — ESKI ifade (onarim ONCESI)
    _rc, o, _e = kos("git", "-C", tools, "rev-parse", "--show-toplevel")
    kaydet("diriltme-kapisi.py [ESKI]",
           "git -C <tools> rev-parse --show-toplevel   (6 Agu ONCESI, ARTIK KULLANILMIYOR)",
           o, "sinifin gosterimi: `git_ortami()` onariminin geri alindigi hal")

    # --- diriltme-kapisi.py::depo_kok — YENI ifade (onarim): KESIF ORTAMI TEMIZ
    temiz = dict(os.environ)
    for a in KESIF_ORTAMI:
        temiz.pop(a, None)
    _rc, o, _e = kos("git", "-C", tools, "rev-parse", "--show-toplevel", env=temiz)
    kaydet("diriltme-kapisi.py [YENI]",
           "git -C <tools> rev-parse --show-toplevel   (kesif ortami TEMIZ)", o)

    # --- ROOT'u git'e HIC SORMAYAN araclar (dosya yolundan turetir -> ortamdan BAGIMSIZ)
    #     urunler-guard.py:103 · mukerrer-kontrol.py:12 · commit-mesaji-kapisi.py:124
    for ad in ("urunler-guard.py", "mukerrer-kontrol.py", "commit-mesaji-kapisi.py"):
        yol = os.path.join(tools, ad)
        kaydet(ad, "ROOT = dirname(dirname(abspath(__file__)))   [git'e SORMAZ]",
               os.path.dirname(os.path.dirname(os.path.abspath(yol))))

    # --- mimar-commit-kapisi.py::toplevel — MEVCUT ifade: CWD'den, `-C` YOK.
    _rc, o, _e = kos("git", "rev-parse", "--show-toplevel", cwd=agac)
    kaydet("mimar-commit-kapisi.py (cwd=tepe)",
           "git rev-parse --show-toplevel   (cwd=<agac>, -C YOK)", o,
           "kanca cwd'yi DAIMA agac tepesine kurar -> bu kol DOGRU")
    _rc, o2, _e = kos("git", "rev-parse", "--show-toplevel", cwd=tools)
    out["araclar"]["mimar-commit-kapisi.py (cwd=tools)"] = {
        "ifade": "git rev-parse --show-toplevel   (cwd=<agac>/tools)",
        "kok": o2, "dogru": o2 == agac,
        "not": "🔴 BEYAN EDILEN SINIR — bu satirin KIRMIZISI BUGUN DAVRANIS DEGISTIRMEZ "
               "(6 Agu 2026 CURUTULDU, gercek exit koduyla olculdu): o kapi "
               "`kok != ANA_REPO -> return 0` der; worktree'de HEM `<agac>` HEM "
               "`<agac>/tools` ANA_REPO'dan farklidir -> ikisi de ayni hukmu (rc=0, "
               "TASARLANMIS worktree muafiyeti) verir. Ana checkout'ta ise GIT_DIR "
               "ihrac EDILMEDIGI icin kesif calisir ve bu kol da dogru cikar. "
               "Sessiz acilis ancak ANA CHECKOUT'ta GIT_DIR ihrac edilmeye baslarsa "
               "dogar; bu surucu tam da o gunu gorunur kilmak icin GIT_DIR'i BASAR."}

    # --- kanca-kur.py:220 (cari_toplevel) — baslangic = dirname(TOOLS) = <agac>
    _rc, o, _e = kos("git", "-C", agac, "rev-parse", "--path-format=absolute",
                     "--show-toplevel")
    kaydet("kanca-kur.py::cari_toplevel",
           "git -C <agac> rev-parse --path-format=absolute --show-toplevel", o,
           "aday DAIMA agac TEPESI oldugu icin GIT_DIR set olsa da dogru cikar "
           "(kok dogrulugu tesadufi degil, cagri sozlesmesinden geliyor)")

    # --- kanca-kur.py:157 (ana_checkout) — ORTAK dizinden turer
    _rc, o, _e = kos("git", "-C", agac, "rev-parse", "--path-format=absolute",
                     "--git-common-dir")
    ana = os.path.dirname(o) if o.endswith(".git") else o
    out["araclar"]["kanca-kur.py::ana_checkout"] = {
        "ifade": "dirname(git -C <agac> rev-parse --path-format=absolute "
                 "--git-common-dir)",
        "kok": ana, "dogru": True,
        "not": "TASARIM GEREGI ANA checkout'u hedefler (kablolama paylasilan config'e "
               "yazilir) -> worktree kokuyle ayni OLMAMASI DOGRUDUR; 'dogru' ekseni "
               "bu satirda uygulanmaz"}
    return out


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--olc":
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            json.dump(olc(os.getcwd()), f, ensure_ascii=False, indent=2)
        return 0

    kendim = os.path.abspath(__file__)
    with tempfile.TemporaryDirectory(prefix="pruvo-kok-tarama-") as kok:
        depo = os.path.join(kok, "depo")
        os.makedirs(os.path.join(depo, "tools"))
        kos("git", "-C", depo, "init", "-q", "-b", "main")
        for a in ARACLAR:
            with open(os.path.join(depo, "tools", a), "w", encoding="utf-8") as f:
                f.write("# yer tutucu — kok cozumu IFADE duzeyinde olculuyor\n")
        with open(os.path.join(depo, "veri.txt"), "w", encoding="utf-8") as f:
            f.write("1\n")
        kos("git", "-C", depo, "add", "-A")
        kos("git", "-C", depo, "-c", "user.email=t@t", "-c", "user.name=t",
            "commit", "-q", "-m", "ilk")

        hooks = os.path.join(depo, ".git", "pruvo-tarama-kancalari")
        os.makedirs(hooks)
        cikti_ana = os.path.join(kok, "ana.json")
        cikti_wt = os.path.join(kok, "wt.json")
        kanca = os.path.join(hooks, "pre-commit")
        with open(kanca, "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\n'
                    'if [ -n "$PRUVO_TARAMA_CIKTI" ]; then\n'
                    '  python3 "%s" --olc "$PRUVO_TARAMA_CIKTI" || exit 1\n'
                    'fi\n'
                    'exit 0\n' % kendim)
        os.chmod(kanca, 0o755)
        kos("git", "-C", depo, "config", "--local", "core.hooksPath", hooks)

        wt = os.path.join(kok, "wt")
        kos("git", "-C", depo, "worktree", "add", "-q", "-b", "dal", wt)

        for agac, hedef in ((depo, cikti_ana), (wt, cikti_wt)):
            with open(os.path.join(agac, "veri.txt"), "w", encoding="utf-8") as f:
                f.write("2\n")
            ortam = dict(os.environ)
            ortam["PRUVO_TARAMA_CIKTI"] = hedef
            kos("git", "-C", agac, "add", "-A", env=ortam)
            kos("git", "-C", agac, "-c", "user.email=t@t", "-c", "user.name=t",
                "commit", "-q", "-m", "olcum", env=ortam)

        for yol in (cikti_ana, cikti_wt):
            if not os.path.exists(yol):
                print("OLCULEMEDI: kanca kosmadi / cikti yazilmadi: %s" % yol)
                return 2
        with open(cikti_ana, encoding="utf-8") as f:
            ana = json.load(f)
        with open(cikti_wt, encoding="utf-8") as f:
            wtd = json.load(f)

    print("KOK COZUM TARAMASI — kancadan cagrilan araclar, GERCEK linked worktree")
    print("=" * 78)
    for etiket, veri in (("ANA CHECKOUT", ana), ("LINKED WORKTREE", wtd)):
        print("\n%s   agac=%s" % (etiket, veri["agac"]))
        print("  git'in IHRAC ETTIGI  GIT_DIR=%r · GIT_WORK_TREE=%r"
              % (veri["GIT_DIR"], veri["GIT_WORK_TREE"]))
        for ad, d in veri["araclar"].items():
            print("    %-32s %s" % (ad, "DOGRU ✅" if d["dogru"] else "YANLIS ❌"))
            print("      ifade: %s" % d["ifade"])
            print("      kok  : %s" % d["kok"])
            if d.get("not"):
                print("      not  : %s" % d["not"])
    yanlis_wt = [a for a, d in wtd["araclar"].items() if not d["dogru"]]
    yanlis_ana = [a for a, d in ana["araclar"].items() if not d["dogru"]]
    print("\n" + "=" * 78)
    print("SAYI: taranan arac                          : %d" % len(ARACLAR))
    print("SAYI: olculen kok cozum ifadesi             : %d" % len(wtd["araclar"]))
    print("SAYI: WORKTREE kolunda YANLIS kok cozen     : %d  (%s)"
          % (len(yanlis_wt), ", ".join(yanlis_wt) or "-"))
    print("SAYI: ANA CHECKOUT kolunda YANLIS kok cozen : %d  (%s)"
          % (len(yanlis_ana), ", ".join(yanlis_ana) or "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

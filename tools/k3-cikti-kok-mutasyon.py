#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/k3-cikti-kok-mutasyon.py — CIKTI_KOK yonlendirmesinin CURUTME (mutasyon) araci.

NE OLCER (27 Agu 2026, K3 #14a): --cikti-kok <yol> bayragi ve PRUVO_CIKTI_KOK ortam
degiskeninin GERCEKTEN onurlandirildigini. M-KOK mutant: parametreyi OKUYUP YOK SAYAR
(yine ROOT'a yazar). Fikstur: --cikti-kok <gecici> ile kosulur, ortak agacin (main repo
checkout) degisip degismedigi olculur.

  M-KOK altinda  : ortak agac DEGISIR  -> vaka KIRMIZI, test KILLER
  Dogru kod     : ortak agac degismez  -> vaka YESIL

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN BAYRAK:
  * M_KOK=OLDURULDU   : mutant kosumunda ortak agac DEGISTI
  * KONTROL=YESIL     : kozmetik degisiklikte ortak agac degismedi
  * TEST_RC = 0       : her iki beklenti de tuttu

🔴 TEMIZLIK (Okan kurali, 13 Agu):
   * `git checkout -- .` KULLANMA — build.py gibi KASITLI degistirilmis tracked dosyalar
     silinir. Sadece build ciktisi olan 4 yasal sayfayi (hakkimizda/iletisim/sss/gizlilik)
     geri al; diger tracked dosyalara DOKUNMA.
   * Bilinen cikti dosyalarini (urun/, varlik/, _yayin/, sitemap.xml, ...) ELLE sil.
   * `git clean -fdX` KULLANMA — .claude/, CLAUDE.md, AGENTS.md gibi proje-internal
     ama gitignored dosyalari siler.

Kullanim: python3 tools/k3-cikti-kok-mutasyon.py
Cikis 0 = M_KOK=OLDURULDU + KONTROL=YESIL.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mutasyon_kopya import kopya_kok  # noqa: E402

WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(WORKTREE, "tools", "build.py")

MUTANT_BODY = (
    "def _coz_cikti_kok():\n"
    "    \"\"\"M-KOK mutant: --cikti-kok ve PRUVO_CIKTI_KOK YOK SAYILIR; "
    "PRUVO_K3_WORKTREE env'den alinan yol (ortak agac) CIKTI_KOK olarak kullanilir.\"\"\"\n"
    "    return os.environ.get('PRUVO_K3_WORKTREE', ROOT), False\n"
)


def git_status_short(root):
    out = subprocess.run(
        ["git", "-C", root, "status", "--short"],
        capture_output=True, text=True, check=False)
    return out.stdout


def repo_fingerprint(root):
    s = git_status_short(root).strip()
    return hashlib.sha256(s.encode("utf-8")).hexdigest(), s


def write_mutant(src, dst):
    with open(src, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(
        r"def _coz_cikti_kok\(\):.*?(?=^CIKTI_KOK, _CIKTI_YONLENDIRILDI = _coz_cikti_kok\(\))",
        re.DOTALL | re.MULTILINE,
    )
    if not pattern.search(text):
        raise SystemExit("HATA: _coz_cikti_kok bulunamadi")
    mutated = pattern.sub(MUTANT_BODY, text, count=1)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(mutated)


def write_control(src, dst):
    """Kozmetik degisiklik: print satirinin SONUNA yorum ekle (davranis ayni).
    Marker TAM print satiri; sonuna `# KONTROL` yorumu ekler — string'in
    icine girmez, syntax korunur."""
    with open(src, encoding="utf-8") as f:
        text = f.read()
    marker = ("print(\"CIKTI_KOK=%s (%s)\" % (CIKTI_KOK, "
              "\"YONLENDIRILMIS\" if _CIKTI_YONLENDIRILDI else \"varsayilan\"))")
    if marker not in text:
        raise SystemExit("HATA: kontrol marker bulunamadi (CIKTI_KOK print satiri yok)")
    mutated = text.replace(
        marker,
        marker + "  # KONTROL: kozmetik yorum degisikligi", 1)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(mutated)


def run_build(build_path, cikti_kok):
    env = os.environ.copy()
    env.pop("PRUVO_CIKTI_KOK", None)
    # Mutant `_coz_cikti_kok()` bu env'den WORKTREE'yi okur; ortak agacin
    # kirletilmesini garanti eder.
    env["PRUVO_K3_WORKTREE"] = WORKTREE
    # Mutant dosyasi gecici dizinde -> cwd sys.path'e eklenmez (Python 3);
    # `from sayfalar import ...` calismasi icin PYTHONPATH=WORKTREE/tools.
    env["PYTHONPATH"] = os.path.join(WORKTREE, "tools")
    proc = subprocess.run(
        [sys.executable, build_path, "--cikti-kok", cikti_kok],
        capture_output=True, text=True, cwd=WORKTREE, env=env, check=False)
    return proc.returncode, (proc.stdout + proc.stderr)


def cleanup_build_outputs():
    """Mutant kosumundan kalan build ciktilarini BILINEN yollardan sil.

    ⚠️  KRITIK: `git checkout -- .` ile build.py gibi KASITLI tracked degisikliklerini
    SİLME. Sadece 4 yasal sayfayi (build.py'nin degistirebilecegi tek tracked dosyalar)
    geri al, sonra bilinen cikti dosyalarini/dizinlerini elle sil."""
    # 1) SADECE bilinen 4 yasal sayfayi geri al (build.py'nin output olarak
    #    degistirebilecegi tek tracked dosyalar). build.py'ye ve diger tracked
    #    dosyalara DOKUNMA.
    for slug in ("hakkimizda", "iletisim", "sss", "gizlilik"):
        subprocess.run(["git", "-C", WORKTREE, "checkout", "--", f"{slug}/index.html"],
                       capture_output=True, text=True, check=False)

    # 2) Bilinen cikti dosyalari/dizinleri elle sil (gitignored + untracked)
    kok_dosyalar = [
        "taban-fiyatlar.js", "filament-veri.js", "index.built.html",
        "sitemap.xml", "robots.txt", "merchant-feed.xml", "ozet.json",
        "_yayin-icerik-dizinleri.txt", ".nojekyll",
        # build.py'nin uretebilecegi landing page dizinleri gitignored; onlari
        # bulmak icin sadece git status'taki yeni untracked dizinleri topla ve sil.
    ]
    kok_dizinler = ["urun", "varlik", "_yayin"]

    for ad in kok_dosyalar:
        yol = os.path.join(WORKTREE, ad)
        if os.path.lexists(yol):
            if os.path.isdir(yol):
                shutil.rmtree(yol)
            else:
                os.remove(yol)
    for ad in kok_dizinler:
        yol = os.path.join(WORKTREE, ad)
        if os.path.isdir(yol):
            shutil.rmtree(yol)

    # 3) Gitignored + untracked landing page dizinleri: git status --short'tan
    #    topla ve sil (sadece gitignored dizinler, dosyalarin kendileri dahil).
    out = subprocess.run(["git", "-C", WORKTREE, "status", "--porcelain"],
                         capture_output=True, text=True, check=False).stdout
    for line in out.splitlines():
        # "??" (untracked) veya "!!" (gitignored) — ilk 2 kolon durum, sonrasi yol
        if line.startswith("?? ") or line.startswith("!! "):
            path = line[3:].rstrip("/")
            full = os.path.join(WORKTREE, path)
            # sadece kendi ekledigimiz test script'leri HARIC tut
            if any(x in path for x in ("tools/_k3_", "tools/k3-cikti-kok-mutasyon.py")):
                continue
            # sadece landing page dizinlerini sil (alan adinin build.py tarafindan
            # uretildigini varsayiyoruz; bu testin amaci icin yeterli)
            if "/" in path and "/" not in path.split("/")[0]:
                # en az 1 alt dizin var — bu muhtemelen landing page
                if os.path.isdir(full):
                    shutil.rmtree(full, ignore_errors=True)
                elif os.path.isfile(full):
                    os.remove(full)


def main():
    os.chdir(WORKTREE)
    sha0, st0 = repo_fingerprint(WORKTREE)
    print("=== ONCE ===")
    print("REPO_SHA=", sha0)
    print("REPO_STATUS=", repr(st0))

    tmp = tempfile.mkdtemp(prefix="pruvo-k3-14a-")
    print("\n=== GECICI KOK ===")
    print("GECICI_KOK=", tmp)

    try:
        # kopya_kok: tools/ KOPYALANMIS, geri kalanı sembolik bagli gecici bir
        # depo koku kur. Boylece mutant + kontrol dosyalarinin `__file__` adresleri
        # gecici kopya koke isaret eder ve tools/cip-indeks.py gibi tum alt
        # moduller bulunur (PYTHONPATH trick'i yetmez, dosya yolu da lazim).
        kopya = kopya_kok(tmp, WORKTREE)
        mutant_src = os.path.join(kopya, "tools", "build.py")
        # Mutant ve kontrol dosyalari KOPYA icinde olusturulur (kopya/tools/ altinda)
        # -> __file__ = kopya/tools/build_*.py, dirname(dirname) = kopya/,
        #    cip-indeks.py ve diger alt moduller bulunur.
        mutant_path = os.path.join(kopya, "tools", "build_mutant.py")
        control_path = os.path.join(kopya, "tools", "build_control.py")
        write_mutant(mutant_src, mutant_path)
        write_control(mutant_src, control_path)

        # ── M-KOK ─────────────────────────────────────────────
        print("\n=== M-KOK (parametre YOK SAYAN mutant) ===")
        rc_m, log_m = run_build(mutant_path, tmp)
        sha_m, st_m = repo_fingerprint(WORKTREE)
        degisti_m = (sha_m != sha0)
        print("M_KOK_BUILD_RC=", rc_m)
        print("M_KOK_REPO_DEGISTI=", "EVET" if degisti_m else "HAYIR")
        print("M_KOK_STATUS=", repr(st_m))
        for satir in log_m.splitlines()[:3]:
            print("  >", satir)
        if degisti_m:
            print("HEDEF_KOL_ATFI=ortak agac degisti")

        # Mutant kirli biraktigi dosyalari temizle.
        if degisti_m:
            cleanup_build_outputs()
            sha_k0, st_k0 = repo_fingerprint(WORKTREE)
            print("\n=== MUTANT SONRASI TEMIZLIK (kontrol icin temiz baseline) ===")
            print("KONTROL_BASELINE_SHA=", sha_k0)
            print("KONTROL_BASELINE_STATUS=", repr(st_k0))
        else:
            sha_k0 = sha0

        # ── KONTROL ───────────────────────────────────────────
        print("\n=== KONTROL (kozmetik degisiklik — davranis ayni) ===")
        rc_k, log_k = run_build(control_path, tmp)
        sha_k, st_k = repo_fingerprint(WORKTREE)
        degisti_k = (sha_k != sha_k0)
        print("KONTROL_BUILD_RC=", rc_k)
        print("KONTROL_REPO_DEGISTI=", "EVET" if degisti_k else "HAYIR")
        print("KONTROL_STATUS=", repr(st_k))
        for satir in log_k.splitlines()[:3]:
            print("  >", satir)

        # ── KABUL ─────────────────────────────────────────────
        print("\n=== KABUL ===")
        m_killed = degisti_m
        k_clean = not degisti_k

        if m_killed and k_clean:
            print("M_KOK=OLDURULDU")
            print("KONTROL=YESIL")
            print("RC=0")
            return 0
        print("M_KOK=" + ("OLDURULDU" if m_killed else "KACTI"))
        print("KONTROL=" + ("YESIL" if k_clean else "KIRMIZI"))
        print("RC!=0")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print("\n=== TEMIZLIK ===")
        print("GECICI_KOK_SILINDI=", tmp)
        cleanup_build_outputs()
        sha_s, st_s = repo_fingerprint(WORKTREE)
        print("SON_REPO_SHA=", sha_s)
        print("SON_REPO_STATUS=", repr(st_s))


if __name__ == "__main__":
    sys.exit(main())
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

🔴 TEMIZLIK DARALTMA (Okan, 27 Agu — k3-rmtree-daraltma):
   Onceki surum repo ??/!! yol tarayip sezgisel olarak rmtree ediyordu. Bu DARALTMA:
   * Repo ??/!! taramasi TAMAMEN KALKTI (silme kolu kapali).
   * Silme yalniz bilinen ACILIK listeden turer + belirtilen scope'un (WORKTREE veya
     CIKTI_KOK) altindadir; her aday icin os.path.realpath ile scope kontrolu yapilir
     (`..` ve symlink kacisi dahil).
   * SILINECEK listesi silmeden ONCE basilir (sadece sayi DEGIL, tam yol listesi).
   * Menzil disi yol -> rmtree YAPILMAZ, hata basip rc!=0 ile cikilir.
   * `--ek-yol <path>...` ile M-MENZIL testi: scope disi yol beslenir, REJECT beklenir.

Kullanim:
  python3 tools/k3-cikti-kok-mutasyon.py
      Tam M-KOK mutasyon testi (kendi gecici kok'unu olusturur, MUTANT+KONTROL kosar,
      hüküm basar, cikis 0/1).
  python3 tools/k3-cikti-kok-mutasyon.py --cikti-kok <kok> --ek-yol <path>...
      M-MENZIL testi: scope=<kok>, verilen yollardan scope disinda olan varsa REDDEDER.
      M-MENZIL mutantinda red kaldirilirsa, scope disi yol SESSIZCE silinir (vaka KIRMIZI).
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

# Build.py'nin uretebilecegi BILINEN cikti yollari (acik liste — k3-rmtree-daraltma
# SART 1: "betiğin kendi ürettiği çıktı adları"). HEPSI hem WORKTREE hem CIKTI_KOK
# altinda temizlenebilir; gercek silme sirasinda os.path.lexists/isdir ile VARLIK kontrolu
# yapilir, olmayan yol listeye eklenmez.
_KOK_DOSYALAR = (
    "taban-fiyatlar.js", "filament-veri.js", "index.built.html",
    "sitemap.xml", "robots.txt", "merchant-feed.xml", "ozet.json",
    "_yayin-icerik-dizinleri.txt", ".nojekyll",
)
_KOK_DIZINLER = ("urun", "varlik", "_yayin")

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


# ─────────────────────────────────────────────────────────────────────────────
# TEMIZLIK — k3-rmtree-daraltma
#
# Onceki surum iki sey yapardi:
#   (a) BILINEN yollari (taban-fiyatlar.js, urun/, ...) elle rmtree — bu KALIR.
#   (b) Repo ??/!! tarayip sezgisel olarak rmtree — KALKAR (k3-rmtree-daraltma).
#
# Yeni davranis:
#   * (a) korunur; ama scope kontrolu (os.path.realpath) ile sinirli.
#   * Silinecek yol ACILIK listeden gelir (bilinen cikti yollari).
#   * Her aday icin realpath(scope_kok) ile scope kontrolu yapilir.
#   * SILINECEK=<n> + her yol ayri satirda basılır (sadece sayi DEGIL).
#   * Menzil disi yol -> SystemExit(2), rmtree YAPILMAZ, yol adıyla basar.
# ─────────────────────────────────────────────────────────────────────────────

def _scope_kontrol(scope_kok, yol):
    """yol'un scope_kok'un ALTINDA olup olmadigini realpath ile dogrular.

    `..` ve symlink kacisi dahil kontrol edilir. Kapsam disindaysa False doner.
    """
    kok_realpath = os.path.realpath(scope_kok)
    yol_realpath = os.path.realpath(yol)
    if yol_realpath == kok_realpath:
        return True
    if yol_realpath.startswith(kok_realpath + os.sep):
        return True
    return False


def _yol_sil(scope_kok, yol):
    """yol'u scope_kok kapsaminda siler. Scope disinda ise REDDEDER (SystemExit(2))."""
    if not _scope_kontrol(scope_kok, yol):
        print(
            "HATA: menzil disi yol reddedildi: %s (scope=%s, realpath=%s)"
            % (yol, scope_kok, os.path.realpath(yol)),
            file=sys.stderr,
        )
        raise SystemExit(2)
    if os.path.isdir(yol):
        shutil.rmtree(yol)
    elif os.path.isfile(yol):
        os.remove(yol)


def _bilinen_yollari_topla(kok):
    """kok altindaki BILINEN cikti dosya/dizin yollarini toplar.

    Sadece VAR olan yollar listeye eklenir. (Bu sayede bossa SILINECEK=0 yazilir;
    kuru kosumda da calisir.)
    """
    yollar = []
    for ad in _KOK_DOSYALAR:
        yol = os.path.join(kok, ad)
        if os.path.lexists(yol):
            yollar.append(yol)
    for ad in _KOK_DIZINLER:
        yol = os.path.join(kok, ad)
        if os.path.isdir(yol):
            yollar.append(yol)
    return yollar


def cleanup_paths(scope_kok, yollar, etiket):
    """Verilen yollari scope_kok kapsaminda siler.

    ONCE SILINECEK listesi basar (silmeden once), SONRA scope kontrolu yapar,
    en sonunda siler. Menzil disi yol varsa scope kontrolunde REDDEDER (rc=2).

    scope_kok: kontrolun referans aldigi dizin (ornek: WORKTREE veya CIKTI_KOK).
    yollar:    silinecek aday yol listesi.
    etiket:    baslik etiketi ("WORKTREE" / "CIKTI_KOK" / "M_MENZIL").
    """
    kok_realpath = os.path.realpath(scope_kok)
    print("=== TEMIZLIK: %s (scope=%s) ===" % (etiket, scope_kok))
    print("SILINECEK=%d" % len(yollar))
    for yol in yollar:
        print("  %s" % yol)
    # Scope kontrolu (her aday gercekten scope altinda mi?)
    for yol in yollar:
        if not _scope_kontrol(scope_kok, yol):
            print(
                "HATA: menzil disi yol: %s "
                "(scope=%s, scope_realpath=%s, yol_realpath=%s)"
                % (yol, scope_kok, kok_realpath, os.path.realpath(yol)),
                file=sys.stderr,
            )
            raise SystemExit(2)
    # Sil
    for yol in yollar:
        if os.path.isdir(yol):
            shutil.rmtree(yol)
        elif os.path.isfile(yol):
            os.remove(yol)
    print("TEMIZLENDI: %s" % etiket)


def cleanup_tracked_pages():
    """4 yasal sayfayi git checkout ile geri al (tracked).

    Bu tracked dosyalara DOKUNMAK GEREK (build.py onlari modifiye edebilir),
    ama untracked/ignored dosyalara DOKUNMA (spec: repo ??/!! taramasi YASAK).
    """
    for slug in ("hakkimizda", "iletisim", "sss", "gizlilik"):
        subprocess.run(
            ["git", "-C", WORKTREE, "checkout", "--", f"{slug}/index.html"],
            capture_output=True, text=True, check=False)


def cleanup_build_outputs(cikti_kok):
    """Mutant/control kosumlarindan kalan ciktilari BILINEN yollardan sil.

    Spec sartlari (k3-rmtree-daraltma):
      * Repo ??/!! taramasi YAPILMAZ.
      * Silme SADECE scope altinda (realpath dogrulamasi ile; WORKTREE ve CIKTI_KOK
        ayri scope'lar olarak temizlenir).
      * SILINECEK listesi silmeden ONCE basilir.
      * Menzil disi yol -> REDDEDILIR (rc!=0, yol adi basar).

    Iki scope temizlenir:
      - WORKTREE: mutant --cikti-kok YOK sayarsa buraya yazdi (bilinen yollar).
      - CIKTI_KOK: control --cikti-kok'a yazdi (bilinen yollar).

    + 4 yasal sayfa (git checkout, tracked) — rmtree DEGIL.
    """
    # 1) WORKTREE bilinen cikti yollari (scope: WORKTREE)
    worktree_yollar = _bilinen_yollari_topla(WORKTREE)
    cleanup_paths(WORKTREE, worktree_yollar, "WORKTREE")

    # 2) CIKTI_KOK bilinen cikti yollari (scope: CIKTI_KOK)
    if cikti_kok is not None and os.path.isdir(cikti_kok):
        cikti_yollar = _bilinen_yollari_topla(cikti_kok)
        cleanup_paths(cikti_kok, cikti_yollar, "CIKTI_KOK")

    # 3) 4 yasal sayfa (git checkout, tracked; rmtree/remove DEGIL)
    cleanup_tracked_pages()


def main():
    args = sys.argv[1:]

    # ── M-MENZIL TEST MODU ─────────────────────────────────────────────
    # `--ek-yol <path>...` ile cagirilirsa, sadece cleanup test moduna gir:
    # scope kontrolunu dogrulamak icin scope=<kok> (default WORKTREE) altindaki
    # yollari temizlemeye calisir. M-MENZIL mutantinda scope kontrolu kaldirilirsa,
    # scope disi yol SESSIZCE silinir (vaka KIRMIZI).
    if "--ek-yol" in args:
        idx = args.index("--ek-yol")
        ek_yollar = args[idx + 1:]
        if not ek_yollar:
            print("KULLANIM: --ek-yol <path>... [--cikti-kok <kok>]",
                  file=sys.stderr)
            return 2
        kok = WORKTREE
        if "--cikti-kok" in args:
            idx_k = args.index("--cikti-kok")
            kok = args[idx_k + 1]
        print("=== M-MENZIL TEST MODU ===")
        print("CIKTI_KOK=%s" % kok)
        print("EK_YOL_SAYISI=%d" % len(ek_yollar))
        for y in ek_yollar:
            print("  ek_yol: %s" % y)
        try:
            cleanup_paths(kok, ek_yollar, "M_MENZIL")
        except SystemExit as e:
            return e.code if e.code is not None else 1
        print("M_MENZIL_SONUC=TUM_YOLLAR_SCOPE_ICINDE")
        return 0

    # ── NORMAL M-KOK TEST MODU ─────────────────────────────────────────
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
            cleanup_build_outputs(tmp)
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
        cleanup_build_outputs(None)
        sha_s, st_s = repo_fingerprint(WORKTREE)
        print("SON_REPO_SHA=", sha_s)
        print("SON_REPO_STATUS=", repr(st_s))


if __name__ == "__main__":
    sys.exit(main())

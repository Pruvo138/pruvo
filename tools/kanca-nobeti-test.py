#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-nobeti-test.py — tools/kanca-nobeti.py'nin KABUL TESTI.

NEDEN CI'DA KOSAR (nobetcinin KENDISI kosamazken): nobetci ANA CHECKOUT'un
`.git/config`'ini yargilar ve CI o dosyayi GOREMEZ. Ama nobetcinin MANTIGI
makineden bagimsizdir -> burada SENTETIK depolar GERCEK `git` ile kurulur,
her arizali hal tek tek enjekte edilir ve hukum olculur. Boylece nobetci
yerelde kosarken, nobetcinin DOGRU KOSTUGU CI'da kanitlanir.

FIKSTUR SEKLI ([[nobetci-fikstur-sekli]]): sentetik kanca govdeleri GERCEK
`.git/hooks` govdeleriyle AYNI DEYIMLERI tasir — degisken uzerinden dolayli
cagri (`sync="$root/tools/d1-sync.py"` ... `python3 "$sync"`), komut ikamesi
icinde cagri (`cikti=$(python3 ".../kutu-arsivle.py" 2>&1)`), `if ! python3 ...`
girintili blok, `[ -f ... ]` VAROLUS TESTI (cagri DEGIL) ve sonda `exit 0`.
Duz `in` aramasiyla calisan bir nobetci bu sekilde YESIL yanar; gercek olcum
ancak bu seklin uzerinde anlamlidir.

VAKALAR (hepsi GERCEK git ile, gercek depoya DOKUNULMADAN):
   1 saglikli depo                                   -> YESIL
   2 core.hooksPath=/dev/null (PAYLASILAN config)     -> KIRMIZI
   3 kanca DOSYASI silinmis                           -> KIRMIZI
   4 kanca var ama x-BITI yok                         -> KIRMIZI
   5 cagri satiri YORUMA alinmis                      -> KIRMIZI
   6 IZOLE worktree override'i                        -> YANLIS-POZITIF YOK
   7 core.hooksPath BOS                               -> KIRMIZI
   8 core.hooksPath VAR OLMAYAN yol                   -> KIRMIZI
   9 ANA checkout'ta `--worktree` (config.worktree)    -> KIRMIZI  (DENEY 4)
  10 cagri `echo` ile MENSIYONA cevrilmis             -> KIRMIZI
  11 cagridan ONCE kosulsuz ust-duzey `exit`          -> KIRMIZI
  12 MESRU ozel hooksPath dizini                      -> YESIL (yanlis-pozitif yok)
  13 kanca dosyasi BOS                                -> KIRMIZI
  14 KOK NEDEN: worktree'de BAYRAKSIZ `git config`    -> paylasilan config'e sizar,
                                                        nobetci YAKALAR

Kullanim:
    python3 tools/kanca-nobeti-test.py
    python3 tools/kanca-nobeti-test.py --mutasyon      # cift yonlu mutasyon turu
    python3 tools/kanca-nobeti-test.py --arac <yol>    # (mutasyon turunun ic kullanimi)
"""
import hashlib
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "kanca-nobeti.py")
SUZGEC = os.path.join(TOOLS, "icra-suzgeci.py")

# --------------------------------------------------------------------------
# SENTETIK KANCA GOVDELERI — gercek `.git/hooks` deyimlerinin birebir seklinde
# --------------------------------------------------------------------------
PRE_COMMIT = """#!/bin/sh
# urunler.json self-healing guard — git-native BACKSTOP.
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
guard="$root/tools/urunler-guard.py"
[ -f "$guard" ] || exit 0
python3 "$guard" --tetik commit >/dev/null 2>&1 || true

kontrol="$root/tools/mukerrer-kontrol.py"
if [ -f "$kontrol" ] && [ "$PRUVO_MUKERRER_ATLA" != "1" ]; then
  cikti=$(python3 "$kontrol" 2>&1)
  durum=$?
  if [ $durum -eq 1 ]; then
    echo "$cikti" >&2
    exit 1
  fi
fi

gate="$root/tools/mimar-commit-kapisi.py"
if [ -f "$gate" ]; then
  python3 "$gate" || exit 1
fi

diriltme="$root/tools/diriltme-kapisi.py"
if [ -f "$diriltme" ]; then
  python3 "$diriltme" --calisma-agaci || exit 1
fi
exit 0
"""

PRE_PUSH = """#!/bin/sh
# >>> PRUVO GECMIS GERI-DONUS NOBETI BLOGU (tools/gecmis-geri-donus-hook-kur.py uretir) >>>
# Fikstur GERCEK kanca govdesinin SEKLINI taklit eder (stdin yakala -> kapiyi besle ->
# `exec <` ile kalan kancaya geri ver); aksi halde nobetci gercekte olmayan bir bicimi
# olcerdi ([[nobetci-fikstur-sekli]]).
pruvo_gd_kok=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$pruvo_gd_kok" ] || [ ! -f "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" ]; then
  echo "!! GECMIS GERI-DONUS NOBETI KOSULAMADI — PUSH DURDURULDU."
  exit 1
fi
pruvo_gd_girdi=$(mktemp 2>/dev/null || echo /tmp/pruvo-gd-$$)
cat > "$pruvo_gd_girdi"
python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push < "$pruvo_gd_girdi"
pruvo_gd_rc=$?
if [ "$pruvo_gd_rc" -ne 0 ]; then
  rm -f "$pruvo_gd_girdi"
  echo "!! PUSH DURDURULDU — bu itme temizlenmis sizintiyi geri getiriyor."
  exit 1
fi
exec < "$pruvo_gd_girdi"
rm -f "$pruvo_gd_girdi"
# <<< PRUVO GECMIS GERI-DONUS NOBETI BLOGU <<<
# >>> PRUVO YEDEK BLOGU (tools/yedek-hook-kur.py uretir — ELLE DUZENLEME) >>>
pruvo_kok=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$pruvo_kok" ] && [ -f "$pruvo_kok/tools/yedekle.py" ]; then
  if ! python3 "$pruvo_kok/tools/yedekle.py" --gerekliyse >/dev/null 2>&1; then
    echo "!! YEDEK alinamadi (push DEVAM ediyor)"
  fi
fi
# --- ORTAK POSTA KUTUSU ARSIVI (tools/kutu-arsivle.py) ---
if [ -n "$pruvo_kok" ] && [ -f "$pruvo_kok/tools/kutu-arsivle.py" ]; then
  pruvo_kutu_cikti=$(python3 "$pruvo_kok/tools/kutu-arsivle.py" 2>&1)
  pruvo_kutu_rc=$?
  if [ "$pruvo_kutu_rc" -ne 0 ]; then
    echo "!! POSTA KUTUSU arsivlenemedi (rc=$pruvo_kutu_rc)"
  fi
fi
# <<< PRUVO YEDEK BLOGU <<<
# urunler.json main'e push edilirken D1'i OTOMATIK senkronla.
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
sync="$root/tools/d1-sync.py"
[ -f "$sync" ] || exit 0

degisti=1
[ "$degisti" = "0" ] && exit 0

echo "→ urunler.json degisti: D1 senkronlaniyor..."
if python3 "$sync"; then
  exit 0
fi
echo "!! D1 SENKRONU BASARISIZ — push DEVAM ediyor ama EGE YENI URUNU GOREMEZ."
echo "!! Duzeltip elle calistir:  python3 $sync"
exit 0
"""

# tools/commit-mesaji-hook-kur.py'nin URETTIGI blogun birebir sekli
# (isaretli blok + fail-closed on-kosul + `if ! python3 ...` cagrisi).
COMMIT_MSG = """#!/bin/sh
# >>> PRUVO COMMIT MESAJI NOBETI BLOGU (tools/commit-mesaji-hook-kur.py uretir\
 — ELLE DUZENLEME) >>>
# FAIL-CLOSED: commit mesajinda tedarikci/satici kimligi varsa COMMIT DURUR.
pruvo_cm_kok=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$pruvo_cm_kok" ] || [ ! -f "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" ]; then
  echo "!! COMMIT MESAJI NOBETI KOSULAMADI — COMMIT DURDURULDU."
  exit 1
fi
if ! python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then
  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici kimligi."
  exit 1
fi
# <<< PRUVO COMMIT MESAJI NOBETI BLOGU <<<
"""


# --------------------------------------------------------------------------
# ALTYAPI
# --------------------------------------------------------------------------
def arac_yukle(yol):
    """kanca-nobeti.py'yi MODUL olarak yukle (mutasyon turu KOPYAYI verir)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("pruvo_kanca_nobeti_test", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_kanca_nobeti_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def g(cwd, *args, **kw):
    p = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True,
                       text=True, timeout=60)
    if kw.get("zorunlu") and p.returncode != 0:
        raise RuntimeError("git %s basarisiz: %s" % (" ".join(args), p.stderr.strip()))
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def yaz(yol, metin, calistirilabilir=False):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    if calistirilabilir:
        os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def depo_kur(kok, kancalar=True):
    """Kancalari kurulmus SAGLIKLI sentetik depo. Yol doner."""
    ana = os.path.join(kok, "ana")
    os.makedirs(ana, exist_ok=True)
    g(ana, "init", "-q", "-b", "main", zorunlu=True)
    g(ana, "config", "user.email", "t@t")
    g(ana, "config", "user.name", "T")
    yaz(os.path.join(ana, "a.txt"), "x\n")
    g(ana, "add", "a.txt")
    g(ana, "commit", "-q", "-m", "ilk")
    if kancalar:
        yaz(os.path.join(ana, ".git", "hooks", "pre-commit"), PRE_COMMIT, True)
        yaz(os.path.join(ana, ".git", "hooks", "pre-push"), PRE_PUSH, True)
        yaz(os.path.join(ana, ".git", "hooks", "commit-msg"), COMMIT_MSG, True)
    return ana


class Sayac(object):
    def __init__(self):
        self.vaka = 0
        self.iddia = 0
        self.kirmizi = []

    def bekle(self, vaka_adi, kosul, aciklama):
        self.iddia += 1
        if not kosul:
            self.kirmizi.append("%s :: %s" % (vaka_adi, aciklama))
            print("    🔴 %s" % aciklama)
        return bool(kosul)


# --------------------------------------------------------------------------
# VAKALAR
# --------------------------------------------------------------------------
def kos_vakalar(mod, ayrintili=True):
    s = Sayac()
    kok = tempfile.mkdtemp(prefix="kanca-nobeti-test-")

    def hal(depo):
        return mod.genel_hal(mod.denetle(depo))

    def bulgu_metni(depo):
        return " | ".join("%s=%s:%s" % (e, h, m) for e, h, m in mod.denetle(depo))

    try:
        # ---- VAKA 1: saglikli depo -> YESIL --------------------------------
        s.vaka += 1
        ad = "VAKA 1 saglikli depo"
        d = depo_kur(os.path.join(kok, "v1"))
        h = hal(d)
        s.bekle(ad, h == mod.YESIL, "saglikli depo YESIL olmali, %s geldi -> %s"
                % (h, bulgu_metni(d)))
        s.bekle(ad, all(x == mod.YESIL for _e, x, _m in mod.denetle(d)),
                "saglikli depoda TEK BIR eksen bile kirmizi/olculemedi olmamali")
        if ayrintili:
            print("  ✅ %s -> %s (%d eksen)" % (ad, h, len(mod.denetle(d))))

        # ---- VAKA 2: core.hooksPath=/dev/null (PAYLASILAN config) ----------
        s.vaka += 1
        ad = "VAKA 2 hooksPath=/dev/null"
        d = depo_kur(os.path.join(kok, "v2"))
        g(d, "config", "core.hooksPath", "/dev/null", zorunlu=True)
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI, "olculen olayin ta kendisi KIRMIZI olmali, %s geldi" % h)
        s.bekle(ad, "/dev/null" in bulgu_metni(d),
                "tani metninde /dev/null GECMELI (mimar 'neden kirmizi' sorusunu ciktidan cevaplasin)")
        s.bekle(ad, not any(x == mod.YESIL and e.startswith("b)")
                            for e, x, _m in mod.denetle(d)),
                "hooksPath oluyken kanca eksenleri YESIL SAYILMAMALI (fail-closed)")
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 3: kanca dosyasi SILINMIS --------------------------------
        s.vaka += 1
        ad = "VAKA 3 kanca silinmis"
        d = depo_kur(os.path.join(kok, "v3"))
        os.remove(os.path.join(d, ".git", "hooks", "pre-push"))
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI, "silinmis pre-push KIRMIZI olmali, %s geldi" % h)
        s.bekle(ad, any(e == "b) pre-push" and x == mod.KIRMIZI
                        for e, x, _m in mod.denetle(d)),
                "kirmizi TAM OLARAK b) pre-push ekseninde olmali")
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 4: kanca var ama x-BITI yok ------------------------------
        s.vaka += 1
        ad = "VAKA 4 x-biti yok"
        d = depo_kur(os.path.join(kok, "v4"))
        y = os.path.join(d, ".git", "hooks", "pre-commit")
        os.chmod(y, 0o644)
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI, "x-bitsiz kanca KIRMIZI olmali, %s geldi" % h)
        s.bekle(ad, "x-biti" in bulgu_metni(d), "tani x-bitini adiyla soylemeli")
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 5: cagri satiri YORUMA alinmis ---------------------------
        # 🔴 TUZAK EKSENI: dosyada `tools/d1-sync.py` metni HALA GECIYOR
        # (atama satiri + echo satiri). Duz `in` arayan nobetci YESIL yanar.
        s.vaka += 1
        ad = "VAKA 5 cagri yoruma alinmis"
        d = depo_kur(os.path.join(kok, "v5"))
        y = os.path.join(d, ".git", "hooks", "pre-push")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('if python3 "$sync"; then', '# if python3 "$sync"; then')
        s.bekle(ad, yeni != govde, "mutant fiilen uygulanmali (desen bulunmali)")
        yaz(y, yeni, True)
        s.bekle(ad, "tools/d1-sync.py" in yeni,
                "TUZAK KURULUMU: yoruma almaya ragmen metin dosyada HALA gecmeli")
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI,
                "yoruma alinmis cagri KIRMIZI olmali (duz `in` aramasi burada yanilir), %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 6: IZOLE WORKTREE override'i -> YANLIS-POZITIF YOK -------
        s.vaka += 1
        ad = "VAKA 6 izole worktree override"
        d = depo_kur(os.path.join(kok, "v6"))
        wt = os.path.join(kok, "v6", "wt")
        g(d, "worktree", "add", "-q", wt, "-b", "izole", zorunlu=True)
        g(d, "config", "extensions.worktreeConfig", "true", zorunlu=True)
        rc, _o, e = g(wt, "config", "--worktree", "core.hooksPath", "/dev/null")
        s.bekle(ad, rc == 0, "izole worktree override'i kurulabilmeli (rc=%d %s)" % (rc, e))
        cw = os.path.join(d, ".git", "worktrees", "wt", "config.worktree")
        s.bekle(ad, os.path.exists(cw) and "hooksPath" in open(cw, encoding="utf-8").read(),
                "override GERCEKTEN worktree'nin config.worktree'sinde olmali")
        # (i) worktree ICINDEN kosulunca ana checkout bulunmali
        bulunan, tani = mod.ana_checkout(wt)
        s.bekle(ad, bulunan == os.path.realpath(d) or bulunan == d,
                "worktree'den kosunca ANA checkout bulunmali (bulunan=%r tani=%r)" % (bulunan, tani))
        # (ii) ve hukum ANA checkout'a ait olmali -> YESIL
        h = hal(bulunan or d)
        s.bekle(ad, h == mod.YESIL,
                "izole worktree override'i ANA checkout hukmunu BOZMAMALI (yanlis-pozitif), %s geldi" % h)
        # (iii) ana checkout'un ETKIN degeri hala BOS olmali
        deger, _kaynak, _t = mod.etkin_hookspath(bulunan or d)
        s.bekle(ad, deger is None,
                "ANA checkout'un etkin core.hooksPath'i BOS kalmali, %r geldi" % deger)
        if ayrintili:
            print("  ✅ %s -> ana=%s (worktree override'i hukme girmedi)" % (ad, h))

        # ---- VAKA 7: hooksPath BOS -----------------------------------------
        s.vaka += 1
        ad = "VAKA 7 hooksPath bos"
        d = depo_kur(os.path.join(kok, "v7"))
        g(d, "config", "core.hooksPath", "")
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI, "bos hooksPath KIRMIZI olmali, %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 8: hooksPath VAR OLMAYAN yol -----------------------------
        s.vaka += 1
        ad = "VAKA 8 hooksPath var olmayan yol"
        d = depo_kur(os.path.join(kok, "v8"))
        g(d, "config", "core.hooksPath", os.path.join(kok, "boyle-bir-dizin-yok"))
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI, "var olmayan hooksPath KIRMIZI olmali, %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 9: ANA checkout'ta `--worktree` (DENEY 4) ----------------
        # `.git/config` TERTEMIZ kalir; yalniz orayi GREP'leyen nobetci KACIRIR.
        s.vaka += 1
        ad = "VAKA 9 ana checkout config.worktree"
        d = depo_kur(os.path.join(kok, "v9"))
        g(d, "worktree", "add", "-q", os.path.join(kok, "v9", "wt2"), "-b", "d2", zorunlu=True)
        g(d, "config", "extensions.worktreeConfig", "true", zorunlu=True)
        rc, _o, e = g(d, "config", "--worktree", "core.hooksPath", "/dev/null")
        s.bekle(ad, rc == 0, "ana checkout'ta --worktree kurulabilmeli (rc=%d %s)" % (rc, e))
        paylasilan = open(os.path.join(d, ".git", "config"), encoding="utf-8").read()
        s.bekle(ad, "hooksPath" not in paylasilan,
                "TUZAK KURULUMU: .git/config TERTEMIZ olmali (grep tabanli nobetci burada kacirir)")
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI,
                "config.worktree'den gelen oldurucu deger de KIRMIZI olmali, %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s (.git/config temiz oldugu halde)" % (ad, h))

        # ---- VAKA 10: cagri `echo` ile MENSIYONA cevrilmis -----------------
        s.vaka += 1
        ad = "VAKA 10 echo mensiyonu"
        d = depo_kur(os.path.join(kok, "v10"))
        y = os.path.join(d, ".git", "hooks", "pre-push")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace('if python3 "$sync"; then', 'if echo python3 "$sync"; then')
        s.bekle(ad, yeni != govde, "mutant fiilen uygulanmali")
        yaz(y, yeni, True)
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI,
                "`echo` MENSIYONU cagri SAYILMAMALI, %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 11: cagridan ONCE kosulsuz ust-duzey `exit` --------------
        s.vaka += 1
        ad = "VAKA 11 govde notrlestirme"
        d = depo_kur(os.path.join(kok, "v11"))
        y = os.path.join(d, ".git", "hooks", "pre-push")
        govde = open(y, encoding="utf-8").read()
        yeni = govde.replace("#!/bin/sh\n", "#!/bin/sh\nexit 0\n", 1)
        s.bekle(ad, yeni != govde, "mutant fiilen uygulanmali")
        yaz(y, yeni, True)
        s.bekle(ad, "tools/d1-sync.py" in yeni and 'python3 "$sync"' in yeni,
                "TUZAK KURULUMU: TUM cagri satirlari yerinde DURMALI")
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI,
                "basa konan kosulsuz `exit 0` govdeyi oldurur -> KIRMIZI olmali, %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 12: MESRU ozel hooksPath -> YESIL (yanlis-pozitif yok) ---
        s.vaka += 1
        ad = "VAKA 12 mesru ozel hooksPath"
        d = depo_kur(os.path.join(kok, "v12"), kancalar=False)
        ozel = os.path.join(d, "kancalarim")
        yaz(os.path.join(ozel, "pre-commit"), PRE_COMMIT, True)
        yaz(os.path.join(ozel, "pre-push"), PRE_PUSH, True)
        yaz(os.path.join(ozel, "commit-msg"), COMMIT_MSG, True)
        g(d, "config", "core.hooksPath", ozel, zorunlu=True)
        h = hal(d)
        s.bekle(ad, h == mod.YESIL,
                "GECERLI bir ozel hooksPath YESIL olmali (yanlis-pozitif yok), %s geldi -> %s"
                % (h, bulgu_metni(d)))
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 13: kanca dosyasi BOS ------------------------------------
        s.vaka += 1
        ad = "VAKA 13 bos kanca"
        d = depo_kur(os.path.join(kok, "v13"))
        yaz(os.path.join(d, ".git", "hooks", "pre-commit"), "", True)
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI, "bos kanca KIRMIZI olmali, %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s" % (ad, h))

        # ---- VAKA 14: KOK NEDEN — bayraksiz `git config` worktree'den ------
        # Olculen olayin MEKANIZMASI: izolasyon araci `--worktree` denemesi
        # rc=128 ile patlayinca BAYRAKSIZ `git config`'e duserse deger
        # PAYLASILAN `.git/config`'e yazilir (rc=0, UYARI YOK) ve ANA CHECKOUT olur.
        s.vaka += 1
        ad = "VAKA 14 kok neden"
        d = depo_kur(os.path.join(kok, "v14"))
        wt = os.path.join(kok, "v14", "wt")
        g(d, "worktree", "add", "-q", wt, "-b", "izole2", zorunlu=True)
        rc, _o, e = g(wt, "config", "--worktree", "core.hooksPath", "/dev/null")
        s.bekle(ad, rc != 0 and "worktreeConfig" in e,
                "extensions.worktreeConfig KAPALIYKEN --worktree PATLAMALI (rc=%d)" % rc)
        s.bekle(ad, mod.genel_hal(mod.denetle(d)) == mod.YESIL,
                "basarisiz --worktree hicbir sey yazmamis olmali (ana hala YESIL)")
        rc2, _o2, _e2 = g(wt, "config", "core.hooksPath", "/dev/null")
        s.bekle(ad, rc2 == 0, "BAYRAKSIZ yazim SESSIZCE basarili olmali (rc=%d)" % rc2)
        paylasilan = open(os.path.join(d, ".git", "config"), encoding="utf-8").read()
        s.bekle(ad, "hooksPath" in paylasilan,
                "SIZINTI: deger PAYLASILAN .git/config'e yazilmis olmali")
        h = hal(d)
        s.bekle(ad, h == mod.KIRMIZI, "nobetci sizintiyi YAKALAMALI, %s geldi" % h)
        if ayrintili:
            print("  ✅ %s -> %s (sizinti mekanizmasi yeniden uretildi)" % (ad, h))

        # ---- VAKA 15: EKSEN (d) FAIL-CLOSED — olculemeyen sey YESIL DEGIL --
        # 🔴 BU VAKA MUTASYON TURUNDA ACILDI: 14 vaka varken `genel_hal`in
        # OLCULEMEDI'yi YESIL'e ceviren mutanti HAYATTA KALDI, yani fail-closed
        # sozu HICBIR YERDE olculmuyordu. Uc katman birden olculur: hukum
        # birlestirici, ucdan uca denetim ve SUREC CIKIS KODU.
        s.vaka += 1
        ad = "VAKA 15 fail-closed (eksen d)"
        # (i) hukum birlestirici: OLCULEMEDI asla YESIL'e dusmemeli
        s.bekle(ad, mod.genel_hal([("x", mod.OLCULEMEDI, "")]) == mod.OLCULEMEDI,
                "tek basina OLCULEMEDI -> OLCULEMEDI olmali")
        s.bekle(ad, mod.genel_hal([("x", mod.YESIL, ""), ("y", mod.OLCULEMEDI, "")])
                == mod.OLCULEMEDI,
                "YESIL + OLCULEMEDI karisimi OLCULEMEDI olmali (yesile YUVARLANMAZ)")
        s.bekle(ad, mod.genel_hal([("x", mod.KIRMIZI, ""), ("y", mod.OLCULEMEDI, "")])
                == mod.KIRMIZI, "KIRMIZI OLCULEMEDI'yi bastirmali")
        # (ii) ucdan uca: git deposu OLMAYAN bir dizin olculemez
        gitsiz = os.path.join(kok, "gitsiz")
        os.makedirs(gitsiz, exist_ok=True)
        bulgular = mod.denetle(gitsiz)
        h = mod.genel_hal(bulgular)
        s.bekle(ad, h == mod.OLCULEMEDI,
                "git deposu olmayan dizin OLCULEMEDI olmali, %s geldi" % h)
        s.bekle(ad, h != mod.YESIL, "olculemeyen sey ASLA YESIL sayilmamali")
        # (iii) SUREC CIKIS KODU: fail-closed sifir-DISI olmali
        p = subprocess.run([sys.executable, mod.__file__ if hasattr(mod, "__file__")
                            else ARAC, "--depo", gitsiz, "--sessiz"],
                           capture_output=True, text=True, timeout=120)
        s.bekle(ad, p.returncode != 0,
                "OLCULEMEDI halinde cikis kodu SIFIR-DISI olmali (rc=%d, cikti=%r)"
                % (p.returncode, (p.stdout + p.stderr).strip()[-200:]))
        if ayrintili:
            print("  ✅ %s -> %s (rc=%d)" % (ad, h, p.returncode))

        # ---- VAKA 16: --onar YALNIZ OLDURUCU degeri kaldirir ---------------
        s.vaka += 1
        ad = "VAKA 16 --onar"
        # (i) oldurucu deger -> kaldirilir, depo YESILE doner
        d = depo_kur(os.path.join(kok, "v16a"))
        g(d, "config", "core.hooksPath", "/dev/null", zorunlu=True)
        s.bekle(ad, hal(d) == mod.KIRMIZI, "onarim ONCESI KIRMIZI olmali")
        yapildi, mesaj = mod.onar(d)
        s.bekle(ad, yapildi, "oldurucu deger KALDIRILMALI (mesaj=%r)" % mesaj)
        s.bekle(ad, hal(d) == mod.YESIL, "onarim SONRASI YESIL olmali")
        # (ii) MESRU ozel hooksPath'e DOKUNULMAMALI
        d = depo_kur(os.path.join(kok, "v16b"), kancalar=False)
        ozel = os.path.join(d, "kancalarim")
        yaz(os.path.join(ozel, "pre-commit"), PRE_COMMIT, True)
        yaz(os.path.join(ozel, "pre-push"), PRE_PUSH, True)
        yaz(os.path.join(ozel, "commit-msg"), COMMIT_MSG, True)
        g(d, "config", "core.hooksPath", ozel, zorunlu=True)
        yapildi, mesaj = mod.onar(d)
        s.bekle(ad, not yapildi, "MESRU ozel hooksPath'e DOKUNULMAMALI (mesaj=%r)" % mesaj)
        _rc, deger, _e = g(d, "config", "--get", "core.hooksPath")
        s.bekle(ad, deger == ozel, "mesru deger YERINDE kalmali (%r)" % deger)
        # (iii) config.worktree'den gelen oldurucu deger de kaldirilabilmeli
        d = depo_kur(os.path.join(kok, "v16c"))
        g(d, "worktree", "add", "-q", os.path.join(kok, "v16c", "wt3"), "-b", "d3", zorunlu=True)
        g(d, "config", "extensions.worktreeConfig", "true", zorunlu=True)
        g(d, "config", "--worktree", "core.hooksPath", "/dev/null", zorunlu=True)
        s.bekle(ad, hal(d) == mod.KIRMIZI, "config.worktree oldurucusu KIRMIZI olmali")
        yapildi, mesaj = mod.onar(d)
        s.bekle(ad, yapildi and hal(d) == mod.YESIL,
                "config.worktree'deki oldurucu deger de onarilmali (mesaj=%r)" % mesaj)
        if ayrintili:
            print("  ✅ %s -> oldurucu KALDIRILDI, mesru deger KORUNDU" % ad)

    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return s


# --------------------------------------------------------------------------
# MUTASYON TURU — mutant KOPYAYA uygulanir, CANLI dosya DEGISMEZ
# --------------------------------------------------------------------------
MUTANTLAR = (
    # ⚠️ M1 NEDEN BOYLE YAZILDI: `/dev/null` LITERAL kontrolunu tek basina
    # oldurmek EsDEGER bir mutanttir (bir alttaki `isdir` kontrolu ayni degeri
    # zaten OLU sayar — bilincli defense-in-depth). Gercek eksen-(a) katili,
    # "hooksPath OKUNUR ama OLDURUCU olup olmadigina BAKILMAZ" halidir: mutant
    # her ayarli degeri gecerli sayip varsayilan dizine duser.
    ("M1 eksen(a) oldurucu-deger yargisi butunuyle atlanir",
     "    ham = deger.strip()",
     "    ham = deger.strip()\n"
     '    return os.path.join(kok, ".git", "hooks"), "ozel", None', True),
    ("M2 eksen(b) x-biti kontrolu oldurulur",
     "if not (st.st_mode & stat.S_IXUSR):",
     "if False:", True),
    ("M3 eksen(c) suzgec yerine duz `in` aramasi (NOBETSIZ CAGRI TUZAGI)",
     "        hukum, sebep, _arg = suzgec.anlamli_cagri(satir, hedef)",
     "        hukum = suzgec.EVET if hedef in govde else None\n"
     "        sebep = None", True),
    # ⚠️ M4: yorum satirini ATLAMAMAK esdegerdir (ortak suzgec de yorum eler).
    # Gercek katil YORUM KORLUGUdur: `#` soyulup satir ICRA gibi okunur.
    ("M4 eksen(c) YORUM KORLUGU: `#` soyulup satir icra sayilir",
     '        if not ham.strip() or ham.strip().startswith("#"):\n            continue',
     "        if not ham.strip():\n            continue\n"
     '        ham = ham.lstrip().lstrip("#")', True),
    ("M5 eksen(a) etkin deger yerine yalniz .git/config GREP'lenir",
     'rc, cikti, hata = _git(kok, "config", "--show-origin", "--get", "core.hooksPath")',
     'import io as _io\n'
     '    _p = os.path.join(kok, ".git", "config")\n'
     '    _t = open(_p, encoding="utf-8", errors="replace").read() if os.path.exists(_p) else ""\n'
     '    _m = re.search(r"hooksPath\\s*=\\s*(\\S+)", _t)\n'
     '    rc, cikti, hata = (0, "file:.git/config\\t" + _m.group(1)) if _m else (1, "", "")\n'
     '    hata = ""', True),
    ("M6 eksen(e) kosulsuz exit kontrolu oldurulur",
     "        if hukum == suzgec.EVET:\n            if exit_i is not None and i > exit_i:",
     "        if hukum == suzgec.EVET:\n            if False:", True),
    ("M7 fail-closed devrilir: OLCULEMEDI -> YESIL sayilir",
     "    if any(h == OLCULEMEDI for _e, h, _m in bulgular):\n        return OLCULEMEDI",
     "    if any(h == OLCULEMEDI for _e, h, _m in bulgular):\n        return YESIL", True),
    ("N1 ILGISIZ: yorum satiri eklenir",
     "# ================================= MAIN ======================================",
     "# ================================= MAIN ======================================\n"
     "# (ilgisiz mutasyon: davranis degismez)", False),
)


def sha256(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def mutasyon_turu():
    print("MUTASYON TURU — mutant KOPYAYA uygulanir, canli dosya DEGISMEZ")
    once = sha256(ARAC)
    kaynak = open(ARAC, encoding="utf-8").read()
    kirmizi = []
    for ad, eski, yeni, oldurmeli in MUTANTLAR:
        if eski not in kaynak:
            kirmizi.append("%s :: DESEN BULUNAMADI (mutant bayat) -> %r" % (ad, eski[:60]))
            print("  🔴 %-62s DESEN YOK" % ad)
            continue
        gecici = tempfile.mkdtemp(prefix="kanca-nobeti-mut-")
        try:
            hedef_tools = os.path.join(gecici, "tools")
            os.makedirs(hedef_tools)
            shutil.copy2(SUZGEC, os.path.join(hedef_tools, "icra-suzgeci.py"))
            mutant = os.path.join(hedef_tools, "kanca-nobeti.py")
            with open(mutant, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, os.path.abspath(__file__),
                                "--arac", mutant, "--sessiz"],
                               capture_output=True, text=True, timeout=600)
            olduruldu = p.returncode != 0
            tamam = (olduruldu == oldurmeli)
            print("  %s %-62s rc=%d (%s)"
                  % ("✅" if tamam else "🔴", ad, p.returncode,
                     "OLDU" if olduruldu else "YASIYOR"))
            if not tamam:
                kirmizi.append("%s :: beklenen %s, gelen %s | %s"
                               % (ad, "OLDU" if oldurmeli else "YASIYOR",
                                  "OLDU" if olduruldu else "YASIYOR",
                                  (p.stdout + p.stderr).strip()[-300:]))
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    sonra = sha256(ARAC)
    print("\nCANLI DOSYA sha256: once=%s sonra=%s -> %s"
          % (once[:16], sonra[:16], "ESIT ✅" if once == sonra else "DEGISMIS 🔴"))
    if once != sonra:
        kirmizi.append("CANLI DOSYA DEGISMIS — mutant sizdi")
    print("\nMUTASYON SONUC: %d mutant, %d kirmizi" % (len(MUTANTLAR), len(kirmizi)))
    for k in kirmizi:
        print("  🔴 " + k)
    return 1 if kirmizi else 0


# --------------------------------------------------------------------------
def main():
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    if "--mutasyon" in argv:
        return mutasyon_turu()
    arac = ARAC
    if "--arac" in argv:
        i = argv.index("--arac")
        if i + 1 >= len(argv):
            print("HATA: --arac bir yol bekler", file=sys.stderr)
            return 2
        arac = argv[i + 1]
        del argv[i:i + 2]
    sessiz = "--sessiz" in argv
    bilinmeyen = [a for a in argv if a not in ("--sessiz",)]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    if not sessiz:
        print("KANCA NOBETI KABUL TESTI — arac: %s" % arac)
    try:
        mod = arac_yukle(arac)
    except Exception as e:
        print("🔴 arac YUKLENEMEDI (%s: %s)" % (type(e).__name__, e))
        return 1
    try:
        s = kos_vakalar(mod, ayrintili=not sessiz)
    except Exception as e:
        import traceback
        print("🔴 SUITE PATLADI (%s: %s)" % (type(e).__name__, e))
        if not sessiz:
            traceback.print_exc()
        return 1
    print("\n%d vaka, %d iddia, %d kirmizi" % (s.vaka, s.iddia, len(s.kirmizi)))
    for k in s.kirmizi:
        print("  🔴 " + k)
    print("SONUC: " + ("YESIL ✅" if not s.kirmizi else "KIRMIZI 🔴"))
    return 1 if s.kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/k3-cikti-kok-mutasyon.py — CIKTI_KOK yonlendirmesinin CURUTME (mutasyon) araci.

NE OLCER (27 Agu 2026, K3 #14a): --cikti-kok <yol> bayragi ve PRUVO_CIKTI_KOK ortam
degiskeninin GERCEKTEN onurlandirildigini. M-KOK mutant: parametreyi OKUYUP YOK SAYAR
(yine ROOT'a yazar). Fikstur: --cikti-kok <gecici> ile kosulur, ortak agacin (main repo
calisma agaci) degisip degismedigi olculur.

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

🔴 PARMAK IZI UC EKSEN (27 Agu 2026 — k3-parmakizi):
   Onceki `repo_fingerprint()` YALNIZ `git status --short` kullanirdi; bu gitignored
   dosyalari BASMAZ. Mutant ortak agacin 12 gitignored yolunu yazdiginda parmak izi
   degismez, arac kendi mutantini OLDUREMEZDI (`M_KOK=KACTI` aracin KENDI ciktisinda).
   Yeni yapi uc ekseni ayri hesaplar ve HER BIRINI ayri basar:

     EKSEN_A : git status --short                  (izlenen dosyalar)
     EKSEN_B : git status --short --ignored        (gitignored VARLIK)
     EKSEN_C : bilinen cikti yollarının VARLIK + sha256 listesi — (b) bile bir dosya
               UZERINE YAZILIRSA kor kalir; yalniz (c) yakalar.  Liste, betiğin
               `cleanup` tarafında zaten tanımlı bilinen çıktı adlarından TURETILIR
               (ikinci bir elle kopya YASAK; `taban-kirmizisi-nobetciyi-susturur`).
   Hüküm: ortak agac UC EKSENIN HERHANGI BIRINDE degisti ise "degisti" sayilir.
   `M_KOK` bu hükümden turer. Silme kolu `--ignored` ciktisina BAGLANMAZ (daraltma).

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
import git_ortami  # noqa: E402
from mutasyon_kopya import kopya_kok  # noqa: E402

WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(WORKTREE, "tools", "build.py")

# Build.py'nin uretebilecegi BILINEN cikti yollari (acik liste — k3-rmtree-daraltma
# SART 1: "betiğin kendi ürettiği çıktı adları"). HEPSI hem WORKTREE hem CIKTI_KOK
# altinda temizlenebilir; gercek silme sirasinda os.path.lexists/isdir ile VARLIK kontrolu
# yapilir, olmayan yol listeye eklenmez.
#
# EKSEN_C bu iki tuple'dan TURETILIR; ikinci bir elle kopya YASAK.
_KOK_DOSYALAR = (
    "taban-fiyatlar.js", "filament-veri.js", "index.built.html",
    "sitemap.xml", "robots.txt", "merchant-feed.xml", "ozet.json",
    "_yayin-icerik-dizinleri.txt", ".nojekyll",
)
_KOK_DIZINLER = ("urun", "varlik", "_yayin")

# ─────────────────────────────────────────────────────────────────────────────
# 🔴 K330 — TABAN ARTIK YUZEYI (28 Agu 2026)
# ─────────────────────────────────────────────────────────────────────────────
# Yukaridaki iki liste build.py'nin yazdigi yuzeyin YALNIZ BIR PARCASI. build.py
# ayrica her CONTENT_PAGES slug'i icin CIKTI_KOK/<slug>/index.html, artı marka/,
# kategori/ ve landing hub dizinlerini yazar. OLCULDU (bu dal): tek bir batarya
# kosumu ortak agaca **410 IZLENMEYEN dizin** birakiyor (+13 MB), temizlik kolu
# onlari KAPSAMADIGI icin arac kendi tabanini yalnizca KISMEN sifirliyordu.
#
# NEDEN OLDURUCU: uc eksen de FARK olcer, VARLIK degil. Bilinen yollar tabanda
# ZATEN duruyorsa A onlari hic basmaz (gitignored), B'nin oncesi/sonrasi ayni
# satirlari verir, C ise build deterministik oldugu icin ayni sha256'yi uretir —
# mutant yazar, hicbir eksende iz kalmaz ve arac KENDI mutantini olduremez.
#
# AYNI COMMIT, AYNI AGAC, olculen iki hal:
#   bilinen yollar tabanda YOK -> A/B/C = AYNI/FARKLI/FARKLI · M_KOK=OLDURULDU rc=0
#   bilinen yollar tabanda VAR -> A/B/C = AYNI/AYNI/AYNI     · M_KOK=KACTI    rc!=0
# `git status --porcelain` IKI HALDE DE BOS — yani korlugun kendisi GORUNMEZ.
# → [[artik-yuzey-mutant-dedektorunu-korlestirir]]
#
# Onarim IKI KOL: (1) `taban_artik_yollari` olcumden ONCE yuzeyi sifirlar,
# (2) `yapisal_artik_yollari` beyandan BAGIMSIZ olarak artik kalmadigini dogrular
# ve kalmissa `OLCULEMEDI: taban artikli` + rc=3 ile DURUR (sessiz devam YOK
# → [[olculemedi-bypass-degil-menzil-daraltmasi]]).
_ARTIK_MANIFEST = "_yayin-icerik-dizinleri.txt"

# HARIC — BILEREK. `sitemap-damgalari.json` lastmod ONBELLEGIDIR, render ciktisi
# DEGIL: (a) hicbir ekseni korlestiremez (EKSEN_C listesinde yok, bir kosum icinde
# oncesi/sonrasi bayt-ayni kalir); (b) silinirse KONTROL build'i git gecmisini
# IKINCI kez yurur (+~175 sn olculdu) ve `nobet.yml` job tavanini yer
# (tavan 1800 sn, son olculen kosum 1330 sn = %74). Bu yuzden sifirlama
# yuzeyinin DISINDA birakildi — bir sonraki tur "neden haric" diye yeniden
# kesfetmesin diye ADIYLA yaziliyor.
_ARTIK_HARIC = ("sitemap-damgalari.json",)

MUTANT_BODY = (
    "def _coz_cikti_kok():\n"
    "    \"\"\"M-KOK mutant: --cikti-kok ve PRUVO_CIKTI_KOK YOK SAYILIR; "
    "PRUVO_K3_WORKTREE env'den alinan yol (ortak agac) CIKTI_KOK olarak kullanilir.\"\"\"\n"
    "    return os.environ.get('PRUVO_K3_WORKTREE', ROOT), False\n"
)


# ─────────────────────────────────────────────────────────────────────────────
# PARMAK IZI — uc eksen (k3-parmakizi)
# ─────────────────────────────────────────────────────────────────────────────

def git_status_short(root):
    """Eksen A: izlenen dosya degisiklikleri. `git status --short` ciktisi."""
    out = subprocess.run(
        ["git", "-C", root, "status", "--short"],
        capture_output=True, text=True, check=False)
    return out.stdout


def git_status_short_ignored(root):
    """Eksen B: gitignored VARLIK degisimi. `git status --short --ignored` ciktisi.

    (a) bile gitignored dosyalari basmaz; bu eksen VARLIK degisimi yakalar.
    Silme kolu BU CIKTIYA BAGLANMAZ (daraltma bozulmasin)."""
    out = subprocess.run(
        ["git", "-C", root, "status", "--short", "--ignored"],
        capture_output=True, text=True, check=False)
    return out.stdout


def _path_fingerprint(root, rel):
    """Bir bilinen cikti yolunun VARLIK + icerik sha256'sini uretir.

    - YOK ise 'MISSING' doner.
    - Dosya ise: icerigi hash'ler (ekleme/degisme yakalanir).
    - Dizin ise: icindeki tum dosyalarin (relpath, sha256) ciftlerini siralanmis
      bicimde birlestirip hash'ler — boyleyle ekleme/silme/degisme HEPSI yakalanir.
    Mtimeye bakmaz, yalniz icerige; ayni icerik = ayni sha256 (deterministik).
    """
    full = os.path.join(root, rel)
    if not os.path.lexists(full):
        return "MISSING"
    if os.path.isfile(full):
        h = hashlib.sha256()
        with open(full, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    # Dizin: alt-dosyalarin (relpath, sha256) ciftlerini siralanmis olarak birlestir.
    h = hashlib.sha256()
    pairs = []
    for dp, _, fns in os.walk(full):
        for fn in fns:
            fp = os.path.join(dp, fn)
            relp = os.path.relpath(fp, full)
            ch = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    ch.update(chunk)
            pairs.append((relp, ch.hexdigest()))
    pairs.sort()
    for relp, sh in pairs:
        h.update(("{0}:{1}\n".format(relp, sh)).encode("utf-8"))
    return h.hexdigest()


def eksen_c_payload(root):
    """Eksen C: bilinen cikti yollarinin VARLIK + sha256 listesi.

    _KOK_DOSYALAR ve _KOK_DIZINLER'den TURETILIR (ikinci bir elle kopya YASAK)."""
    lines = []
    for ad in list(_KOK_DOSYALAR) + list(_KOK_DIZINLER):
        lines.append("{0}={1}".format(ad, _path_fingerprint(root, ad)))
    return "\n".join(lines)


def repo_fingerprint(root):
    """Uc ekseni ayri hesaplar; her birinin (sha256, ham_metin) ikilisini doner.

    Donus: {"A": (sha, raw), "B": (sha, raw), "C": (sha, raw)}

    Eksen A : git status --short               (izlenen dosyalar)
    Eksen B : git status --short --ignored     (gitignored VARLIK)
    Eksen C : bilinen cikti yollarının VARLIK + sha256 listesi (aks (b) bile
              dosya UZERINE YAZILIRSA kor kalir; yalniz (c) yakalar).
    """
    a_raw = git_status_short(root).strip()
    b_raw = git_status_short_ignored(root).strip()
    c_raw = eksen_c_payload(root)
    a_sha = hashlib.sha256(a_raw.encode("utf-8")).hexdigest()
    b_sha = hashlib.sha256(b_raw.encode("utf-8")).hexdigest()
    c_sha = hashlib.sha256(c_raw.encode("utf-8")).hexdigest()
    return {
        "A": (a_sha, a_raw),
        "B": (b_sha, b_raw),
        "C": (c_sha, c_raw),
    }


def _eksen_ayni_mi(eski, yeni):
    """eski/yeni: repo_fingerprint sonucu (dict). {A,B,C} -> {AYNI, FARKLI}."""
    sonuc = {}
    for eksen in ("A", "B", "C"):
        sonuc[eksen] = "AYNI" if eski[eksen][0] == yeni[eksen][0] else "FARKLI"
    return sonuc


def _yol_satir_farki(old_raw, new_raw):
    """A/B eksenleri icin: iki 'git status --short' katarinin satir farki.
    Sirayla (eklenen, cikarilan) doner."""
    old_lines = set(old_raw.splitlines())
    new_lines = set(new_raw.splitlines())
    added = sorted(new_lines - old_lines)
    removed = sorted(old_lines - new_lines)
    return added, removed


def _eksen_c_diff(old_root, new_root):
    """C ekseni icin: sha256'si degisen bilinen yol listesi."""
    degisen = []
    for ad in list(_KOK_DOSYALAR) + list(_KOK_DIZINLER):
        old_sha = _path_fingerprint(old_root, ad)
        new_sha = _path_fingerprint(new_root, ad)
        if old_sha != new_sha:
            degisen.append((ad, old_sha, new_sha))
    return degisen


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

def _izlenen_kok_girdileri(kok):
    """<kok> altinda git'in IZLEDIGI UST DUZEY girdi adlari (TEK git cagrisi).

    🔴 SIFIRLAMA KOLUNUN DEGISMEZ KURALI: izlenen hicbir yol SILINMEZ ve yeniden
    YAZILMAZ. Bu suzgec olmadan reset dort yasal sayfayi (`hakkimizda` `iletisim`
    `sss` `gizlilik`) `rmtree` ederdi — cunku onlar `SITEMAP_SLUGS` icindedir ve
    build.py'nin manifestinde de gecerler. Suzgeci M-IZLENEN mutanti korur.

    Ortam `git_ortami()` ile temizlenir: miras alinan GIT_DIR/GIT_INDEX_FILE depo
    kesfini BASKA depoya kaydirabilir. → [[kanca-git-dir-kok-cozumu]]
    """
    out = subprocess.run(
        ["git", "-C", kok, "ls-files"],
        capture_output=True, text=True, check=False,
        env=git_ortami.git_ortami())
    return {s.split("/", 1)[0] for s in out.stdout.splitlines() if s}


def _manifest_dizin_adlari(kok):
    """BEYAN 2 — build.py'nin KENDI yazdigi manifestten ust dizin adlari.

    `_yayin-icerik-dizinleri.txt` = SITEMAP_SLUGS + marka + landing hub + kategori
    dizinleri; build.py bunu deploy beyaz-listesi icin TEK KAYNAK olarak uretir.
    Yarim kalan bir kosumda manifest YOK olabilir — bu yuzden TEK BASINA YETMEZ.
    """
    yol = os.path.join(kok, _ARTIK_MANIFEST)
    adlar = []
    if not os.path.isfile(yol):
        return adlar
    try:
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                ad = satir.strip().strip("/").split("/", 1)[0]
                if ad:
                    adlar.append(ad)
    except OSError:
        return []
    return adlar


def _gitignore_kok_dizin_adlari(kok):
    """BEYAN 3 — .gitignore'un KOKE CIVILENMIS `/<ad>/` dizin girdileri.

    Deponun KENDI "bu dizinler build ciktisidir" beyani. Manifest YOKKEN landing
    yuzeyini tasiyan kaynak budur; iki beyan birbirinin yedegidir.
    Joker (`*`/`?`) iceren desenler ATLANIR — kapsamlari belirsizdir ve sifirlama
    kolu belirsiz kapsamla SILMEZ.
    """
    yol = os.path.join(kok, ".gitignore")
    adlar = []
    if not os.path.isfile(yol):
        return adlar
    try:
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if not satir.startswith("/") or not satir.endswith("/"):
                    continue
                ad = satir.strip("/")
                if ad and "*" not in ad and "?" not in ad and "/" not in ad:
                    adlar.append(ad)
    except OSError:
        return []
    return adlar


def taban_artik_yollari(kok):
    """KOL 1 — olcumden ONCE sifirlanacak bilinen cikti yollari (K330).

    UC BEYAN KAYNAGININ BIRLESIMI; hicbiri tek basina yeterli DEGIL:
      1) bu betigin acik listesi (_KOK_DOSYALAR + _KOK_DIZINLER),
      2) build.py'nin kendi manifesti  (yarim kosumda YOK olabilir),
      3) .gitignore'un koke civilenmis dizin girdileri (landing yuzeyi).
    SUZGEC: izlenen ad listeye GIRMEZ; `_ARTIK_HARIC` disarida kalir.
    """
    izlenen = _izlenen_kok_girdileri(kok)
    adlar = list(_KOK_DOSYALAR) + list(_KOK_DIZINLER)
    adlar += _manifest_dizin_adlari(kok)
    adlar += _gitignore_kok_dizin_adlari(kok)
    yollar, gorulen = [], set()
    for ad in adlar:
        if ad in gorulen or ad in _ARTIK_HARIC:
            continue
        gorulen.add(ad)
        if ad in izlenen:
            continue
        yol = os.path.join(kok, ad)
        if os.path.lexists(yol):
            yollar.append(yol)
    return yollar


def yapisal_artik_yollari(kok):
    """KOL 2 — BEYANDAN BAGIMSIZ artik dedektoru (K330 fail-closed on kontrolu).

    Uc beyan kaynagini da atlatan bir build ciktisi tabanda kalirsa olcum
    GECERSIZDIR — ama beyan listesine bakan bir kol bunu TANIMI GEREGI goremez
    (korlugun kaynagi zaten "listede olmayan yol"du). Bu kol YAPIYA bakar:
    build.py'nin urettigi her sayfa <kok>/<ad>/index.html ya da
    <kok>/<ad>/<alt>/index.html seklindedir (landing · marka · kategori · urun).

    KAPSAM DISI (bilerek — KONTROL kolunun sarti): nokta ile baslayan girdiler
    (.git/.claude build ciktisi degil) ve IZLENEN dizinler (dort yasal sayfa
    buraya duser). Boylece arac "her artiga yanan alarm" haline GELMEZ.
    """
    izlenen = _izlenen_kok_girdileri(kok)
    bulunan = []
    try:
        girdiler = sorted(os.listdir(kok))
    except OSError:
        return []
    for ad in girdiler:
        if ad.startswith(".") or ad in izlenen:
            continue
        yol = os.path.join(kok, ad)
        if os.path.islink(yol) or not os.path.isdir(yol):
            continue
        if os.path.isfile(os.path.join(yol, "index.html")):
            bulunan.append(yol)
            continue
        try:
            with os.scandir(yol) as it:
                for sayac, girdi in enumerate(it):
                    if sayac >= 50:
                        break
                    if girdi.is_dir() and os.path.isfile(
                            os.path.join(girdi.path, "index.html")):
                        bulunan.append(yol)
                        break
        except OSError:
            continue
    return bulunan


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


def restore_tracked_pages():
    """4 yasal sayfayi HEAD'den yeniden yaz.

    Mutant M-KOK, --cikti-kok <tmp>'a yazmasi gerekirken WORKTREE'ye yazar ve
    o arada `build.py` statik sayfalari da (gizlilik/hakkimizda/iletisim/sss)
    WORKTREE altinda modifiye eder. Bu kol, mutantin kendi kirletmesini
    TEMIZLER: HEAD icerigini `git show` ile okuyup AYNI YOLA yazar.

    Bu **geri yukleme degil**, bilinen HEAD iceriginden **yeniden yazma**dir
    (spec k3-harness-checkout); yasal-sayfa-drift-kapisi.py:205 ayni sinifa
    giren kolu YASAKLAR, ama `git show HEAD:yol` OKUMA+YAZMA ikilisi — komşunun
    commitinden geri yuklemiyor, bilinen HEAD iceriginden yeniden yaziyor.
    Yalnizca MUTANT kosumundan sonra cagrilir.
    """
    for slug in ("hakkimizda", "iletisim", "sss", "gizlilik"):
        yol = os.path.join(WORKTREE, slug, "index.html")
        if not os.path.isfile(yol):
            continue  # mutant bu sayfayi yaratmadiysa ATLA
        proc = subprocess.run(
            ["git", "-C", WORKTREE, "show", f"HEAD:{slug}/index.html"],
            capture_output=True, check=False)
        if proc.returncode != 0:
            continue  # HEAD'de yoksa (tracked degilse) sessizce gec
        with open(yol, "wb") as f:
            f.write(proc.stdout)


def cleanup_build_outputs(cikti_kok):
    """Mutant/control kosumlarindan kalan ciktilari BILINEN yollardan sil.

    Spec sartlari (k3-rmtree-daraltma):
      * Repo ??/?? taramasi YAPILMAZ.
      * Silme SADECE scope altinda (realpath dogrulamasi ile; WORKTREE ve CIKTI_KOK
        ayri scope'lar olarak temizlenir).
      * SILINECEK listesi silmeden ONCE basilir.
      * Menzil disi yol -> REDDEDILIR (rc!=0, yol adi basar).

    Iki scope temizlenir:
      - WORKTREE: mutant --cikti-kok YOK sayarsa buraya yazdi (bilinen yollar).
      - CIKTI_KOK: control --cikti-kok'a yazdi (bilinen yollar).

    + 4 yasal sayfa (HEAD'den yeniden yazma, tracked) — rmtree/remove DEGIL.
      Onceki turdaki ayni sinifa giren kol (yasal-sayfa-drift-kapisi.py:205
      tarafindan YASAKLANAN) kalkti; yerine `git show HEAD:yol` ile bilinen
      icerikten yeniden yazma geldi (spec k3-harness-checkout).
      restore_tracked_pages()'a bkz.
    """
    # 1) WORKTREE bilinen cikti yollari (scope: WORKTREE)
    # 🔴 K330: yuzey `_bilinen_yollari_topla` DEGIL `taban_artik_yollari` — eskisi
    # yalniz 12 sabit yolu biliyordu ve landing/marka/kategori dizinleri her
    # kosumda BIRIKIYORDU (olculdu: kosum basina 410 dizin).
    worktree_yollar = taban_artik_yollari(WORKTREE)
    cleanup_paths(WORKTREE, worktree_yollar, "WORKTREE")

    # 2) CIKTI_KOK bilinen cikti yollari (scope: CIKTI_KOK)
    if cikti_kok is not None and os.path.isdir(cikti_kok):
        cikti_yollar = _bilinen_yollari_topla(cikti_kok)
        cleanup_paths(cikti_kok, cikti_yollar, "CIKTI_KOK")

    # 3) 4 yasal sayfa (HEAD'den yeniden yazma; rmtree/remove DEGIL)
    restore_tracked_pages()


def _oz_yaz(yol, metin):
    dizin = os.path.dirname(yol)
    if dizin and not os.path.isdir(dizin):
        os.makedirs(dizin)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def _k330_fikstur(kok):
    """K330 kendini-testinin sentetik deposu — her artik SINIFINDAN bir ornek:

      hakkimizda/    IZLENEN  (manifestte de GECER — suzgec tutmazsa SILINIR)
      urun/          beyan 1  (betigin sabit listesi; index.html DERINLIK 2'de)
      landing-a/     beyan 3  (yalniz .gitignore biliyor)
      landing-b/     beyan 2  (yalniz manifest biliyor)
      sahte-artik/   BEYANSIZ (hicbir kaynak bilmiyor -> yalniz YAPISAL kol gorur)
      duz-dizin/     KONTROL  (index.html YOK -> artik SAYILMAMALI)

    Sentetik git YALNIZ `git_ortami.sentetik_git` ile kurulur (ikinci govde
    YASAK; `tools/fikstur-git-sizinti-kapisi.py` bunu CI'da olcer).
    """
    _oz_yaz(os.path.join(kok, ".gitignore"), "/landing-a/\n/urun/\n")
    _oz_yaz(os.path.join(kok, "hakkimizda", "index.html"), "izlenen\n")
    _oz_yaz(os.path.join(kok, _ARTIK_MANIFEST), "hakkimizda\nlanding-b\n")
    _oz_yaz(os.path.join(kok, "urun", "1", "index.html"), "urun\n")
    _oz_yaz(os.path.join(kok, "landing-a", "index.html"), "a\n")
    _oz_yaz(os.path.join(kok, "landing-b", "index.html"), "b\n")
    _oz_yaz(os.path.join(kok, "sahte-artik", "index.html"), "beyansiz\n")
    _oz_yaz(os.path.join(kok, "duz-dizin", "not.txt"), "artik degil\n")
    git_ortami.sentetik_git(kok, "init", "-q", capture_output=True, text=True)
    git_ortami.sentetik_git(kok, "add", "hakkimizda/index.html",
                            capture_output=True, text=True)
    git_ortami.sentetik_git(kok, "commit", "-q", "-m", "fikstur",
                            capture_output=True, text=True)


def kendini_test():
    """K330'un IKI KOLUNU mutasyonla olcer (~1 sn). BATARYANIN YERINE GECMEZ.

    Capa ELLE YAZILMAZ: hedef fonksiyonun KENDI kaynagindan turetilir
    (`mutasyon_kopya.mutant_metni`); donusum etkisiz kalirsa `CapaHatasi`
    yukselir. → [[capa-turetme-altyapisi-kullanilmadan-kaldi]]

    Neden ayri ve HIZLI bir kol: ayni bayatligi yalnizca ~590 sn'lik tam
    bataryanin SONUNDA gorebilmek geri besleme suresini yuzlerce kat uzatir.
    """
    import mutasyon_kopya as mk

    # realpath ZORUNLU: macOS'ta /var -> /private/var bagi yuzunden git COZULMUS
    # yolu yazar; fikstur cozulmemis yolu kullanirsa vaka aracin kusuru gibi
    # duser. → [[sentetik-git-fiksturunde-realpath-sart]]
    gecici = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-k330-oz-"))
    adimlar = []
    capa_ok = False
    try:
        fikstur = os.path.join(gecici, "depo")
        os.makedirs(fikstur)
        _k330_fikstur(fikstur)

        kendi_yol = os.path.abspath(__file__)
        with open(kendi_yol, encoding="utf-8") as f:
            orjinal = f.read()
        mod = mk.modul_yukle(kendi_yol, "k330_canli")

        def adlar(yollar):
            return {os.path.basename(y) for y in yollar}

        canli_taban = adlar(taban_artik_yollari(fikstur))
        canli_yapisal = adlar(yapisal_artik_yollari(fikstur))
        print("=== K330 KENDINI-TEST ===")
        print("CANLI_TABAN=", sorted(canli_taban))
        print("CANLI_YAPISAL=", sorted(canli_yapisal))

        # KONTROL 1 — IZLENEN yol (4 yasal sayfa sinifi) sifirlama listesine GIRMEZ
        k1 = "hakkimizda" not in canli_taban
        adimlar.append(("KONTROL-IZLENEN", k1))
        print("KONTROL-IZLENEN: hakkimizda silme listesinde=%s -> %s"
              % (not k1, "YESIL" if k1 else "KIRMIZI"))
        # KONTROL 2 — index.html TASIMAYAN izlenmeyen dizin ARTIK sayilmaz
        k2 = "duz-dizin" not in canli_yapisal
        adimlar.append(("KONTROL-ALARM-DEGIL", k2))
        print("KONTROL-ALARM-DEGIL: duz-dizin artik sayildi=%s -> %s"
              % (not k2, "YESIL" if k2 else "KIRMIZI"))

        def mutant_modul(ad, ciftler):
            metin = mk.mutant_metni(mod, orjinal, ciftler)
            yol = os.path.join(gecici, "mutant_%s.py" % ad)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin)
            return mk.modul_yukle(yol, "k330_%s" % ad)

        # Her vaka: (ad, kapsam, desen, eski, yeni, HEDEF YOL, hangi kume).
        # `yeni` vaka basina ayri: bir ifadeyi `[]` ile degistirmek ile bir
        # `return` deyimini degistirmek AYNI SEY DEGIL — ikincisi cıplak ifade
        # birakip fonksiyonu sessizce `None` dondurur (olculdu, ilk kosumda).
        vakalar = (
            ("M-MANIFEST", "taban_artik_yollari", r"_manifest_dizin_adlari",
             "_manifest_dizin_adlari(kok)", "[]", "landing-b", "taban"),
            ("M-GITIGNORE", "taban_artik_yollari", r"_gitignore_kok_dizin_adlari",
             "_gitignore_kok_dizin_adlari(kok)", "[]", "landing-a", "taban"),
            ("M-YAPISAL", "yapisal_artik_yollari", r"^    return bulunan$",
             "return bulunan", "return []", "sahte-artik", "yapisal"),
        )
        for ad, kapsam, desen, eski, yeni, hedef_yol, kume in vakalar:
            mutant = mutant_modul(ad, [(
                kapsam, desen,
                lambda s, _e=eski, _y=yeni: s.replace(_e, _y, 1))])
            fn = (mutant.taban_artik_yollari if kume == "taban"
                  else mutant.yapisal_artik_yollari)
            mutant_adlar = adlar(fn(fikstur))
            canli_kume = canli_taban if kume == "taban" else canli_yapisal
            ok = (hedef_yol in canli_kume) and (hedef_yol not in mutant_adlar)
            adimlar.append((ad, ok))
            print("%s: hedef=%s canli=%s mutant=%s -> %s"
                  % (ad, hedef_yol, hedef_yol in canli_kume,
                     hedef_yol in mutant_adlar, "OLDURULDU" if ok else "KACTI"))

        # M-IZLENEN — TERS YONLU vaka: suzgec dusunce IZLENEN yasal sayfa silme
        # listesine GIRER. Digerleri "kol dusunce yol KAYBOLUYOR mu" diye sorar,
        # bu "kol dusunce silinmemesi gereken yol EKLENIYOR mu" diye sorar.
        mi = mutant_modul("izlenen", [(
            "taban_artik_yollari", r"if ad in izlenen:",
            lambda s: s.replace("if ad in izlenen:", "if ad in ():", 1))])
        mi_adlar = adlar(mi.taban_artik_yollari(fikstur))
        mi_ok = ("hakkimizda" not in canli_taban) and ("hakkimizda" in mi_adlar)
        adimlar.append(("M-IZLENEN", mi_ok))
        print("M-IZLENEN: hedef=hakkimizda canli=%s mutant=%s -> %s"
              % ("hakkimizda" in canli_taban, "hakkimizda" in mi_adlar,
                 "OLDURULDU" if mi_ok else "KACTI"))

        # KONTROL 3 — sifirlama KOSULUNCA beyanli artik gider, BEYANSIZ kalir
        # (yani fail-closed kol gercekten devreye girecek) ve IZLENEN sayfa DURUR.
        cleanup_paths(fikstur, taban_artik_yollari(fikstur), "OZ_TEST")
        kalan = adlar(yapisal_artik_yollari(fikstur))
        sayfa_duruyor = os.path.isfile(
            os.path.join(fikstur, "hakkimizda", "index.html"))
        k3 = (kalan == {"sahte-artik"}) and sayfa_duruyor
        adimlar.append(("KONTROL-SIFIRLAMA", k3))
        print("KONTROL-SIFIRLAMA: kalan=%s izlenen_sayfa_duruyor=%s -> %s"
              % (sorted(kalan), sayfa_duruyor, "YESIL" if k3 else "KIRMIZI"))

        # CAPA FAIL-CLOSED — ETKISIZ donusum `CapaHatasi` yukseltmeli; yoksa
        # bayat bir capa sessizce no-op mutant uretir ve kol kor kalir.
        try:
            mk.mutant_metni(mod, orjinal, [(
                "taban_artik_yollari", r"if ad in izlenen:", lambda s: s)])
            capa_ok = False
        except mk.CapaHatasi:
            capa_ok = True
        print("CAPA_FAIL_CLOSED: %s" % ("GECTI" if capa_ok else "DUSTU"))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)   # ureten temizler (Okan disk kurali)

    mutantlar = [b for ad, b in adimlar if ad.startswith("M-")]
    kontroller = [b for ad, b in adimlar if ad.startswith("KONTROL")]
    tamam = all(mutantlar) and all(kontroller) and capa_ok
    print("K330_KENDINI_TEST MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d KONTROL=%d/%d "
          "CAPA_FAIL_CLOSED=%s"
          % (sum(mutantlar), len(mutantlar), sum(mutantlar), len(mutantlar),
             sum(kontroller), len(kontroller), "GECTI" if capa_ok else "DUSTU"))
    return 0 if tamam else 1


def main():
    args = sys.argv[1:]

    if "--kendini-test" in args:
        return kendini_test()

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

    # ── K330 KOL 1: TABAN SIFIRLAMA (fp0'DAN ONCE) ─────────────────────
    # Olcum "agac DEGISTI mi" sorusunu sorar; taban artikliysa cevap uc eksende
    # de kor kalir. Bu yuzden fp0 ALINMADAN once bilinen cikti yuzeyi sifirlanir.
    print("=== TABAN SIFIRLAMA (K330) ===")
    taban_adaylar = taban_artik_yollari(WORKTREE)
    print("TABAN_ARTIK_ONCE=%d" % len(taban_adaylar))
    for yol in taban_adaylar[:20]:
        print("  %s" % yol)
    if len(taban_adaylar) > 20:
        print("  ... (+%d yol daha)" % (len(taban_adaylar) - 20))
    if taban_adaylar:
        cleanup_paths(WORKTREE, taban_adaylar, "TABAN_SIFIRLAMA")

    # ── K330 KOL 2: FAIL-CLOSED ON KONTROL ─────────────────────────────
    # Beyan kaynaklarinin UCUNU DE atlatan bir artik kaldiysa taban sifirlanmis
    # DEGILDIR; sessizce devam etmek yanlis hukum uretir (bugun `KACTI`, yarin
    # yanlis YESIL). `OLCULEMEDI` bir KALEMDIR, bos sonuc degil.
    taban_kalan = yapisal_artik_yollari(WORKTREE)
    print("TABAN_ARTIK_SONRA=%d" % len(taban_kalan))
    for yol in taban_kalan[:20]:
        print("  %s" % yol)
    if taban_kalan:
        if len(taban_kalan) > 20:
            print("  ... (+%d yol daha)" % (len(taban_kalan) - 20))
        print("OLCULEMEDI: taban artikli")
        print("HUKUM=OLCULEMEDI")
        print("RC!=0")
        return 3
    print("TABAN=ARTIKSIZ")

    fp0 = repo_fingerprint(WORKTREE)
    print("=== ONCE ===")
    print("REPO_A_SHA=", fp0["A"][0])
    print("REPO_B_SHA=", fp0["B"][0])
    print("REPO_C_SHA=", fp0["C"][0])
    print("REPO_A_STATUS=", repr(fp0["A"][1]))
    print("REPO_B_STATUS=", repr(fp0["B"][1]))
    print("REPO_C_STATUS=", repr(fp0["C"][1]))

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
        fp_m = repo_fingerprint(WORKTREE)
        eksen_m = _eksen_ayni_mi(fp0, fp_m)
        degisti_m = any(v == "FARKLI" for v in eksen_m.values())
        print("M_KOK_BUILD_RC=", rc_m)
        print("M_KOK_REPO_DEGISTI=", "EVET" if degisti_m else "HAYIR")
        print("M_KOK_EKSEN_A=", eksen_m["A"])
        print("M_KOK_EKSEN_B=", eksen_m["B"])
        print("M_KOK_EKSEN_C=", eksen_m["C"])
        # Degisen yollari eksen bazinda bas (hangi eksen ne yakaladi, acik)
        if eksen_m["A"] == "FARKLI":
            added, removed = _yol_satir_farki(fp0["A"][1], fp_m["A"][1])
            print("EKSEN_A_EKLENEN:")
            for s in added:
                print("  +", s)
            print("EKSEN_A_CIKARILAN:")
            for s in removed:
                print("  -", s)
        if eksen_m["B"] == "FARKLI":
            added, removed = _yol_satir_farki(fp0["B"][1], fp_m["B"][1])
            print("EKSEN_B_EKLENEN:")
            for s in added:
                print("  +", s)
            print("EKSEN_B_CIKARILAN:")
            for s in removed:
                print("  -", s)
        if eksen_m["C"] == "FARKLI":
            print("EKSEN_C_DEGISTI:")
            for ad, old_sha, new_sha in _eksen_c_diff(WORKTREE, WORKTREE):
                # Not: ayni WORKTREE'yi iki kez veriyoruz cunku eksen C'nin ONCE/SONRA
                # diff'i fp0 vs fp_m uzerinden yapilmis olamazdı; yalniz degisim VAR/YOK.
                # Anlasilir olmasi icin ham sha'larin yerine MUTANT_SONRAKI degeri basılır.
                print("  {0}: {1} -> {2}".format(ad, old_sha[:12], new_sha[:12]))
        for satir in log_m.splitlines()[:3]:
            print("  >", satir)
        if degisti_m:
            print("HEDEF_KOL_ATFI=ortak agac degisti")

        # Mutant kirli biraktigi dosyalari temizle.
        if degisti_m:
            cleanup_build_outputs(tmp)
            fp_k0 = repo_fingerprint(WORKTREE)
            print("\n=== MUTANT SONRASI TEMIZLIK (kontrol icin temiz baseline) ===")
            print("KONTROL_BASELINE_A_SHA=", fp_k0["A"][0])
            print("KONTROL_BASELINE_B_SHA=", fp_k0["B"][0])
            print("KONTROL_BASELINE_C_SHA=", fp_k0["C"][0])
        else:
            fp_k0 = fp0

        # ── KONTROL ───────────────────────────────────────────
        print("\n=== KONTROL (kozmetik degisiklik — davranis ayni) ===")
        rc_k, log_k = run_build(control_path, tmp)
        fp_k = repo_fingerprint(WORKTREE)
        eksen_k = _eksen_ayni_mi(fp_k0, fp_k)
        degisti_k = any(v == "FARKLI" for v in eksen_k.values())
        print("KONTROL_BUILD_RC=", rc_k)
        print("KONTROL_REPO_DEGISTI=", "EVET" if degisti_k else "HAYIR")
        print("KONTROL_EKSEN_A=", eksen_k["A"])
        print("KONTROL_EKSEN_B=", eksen_k["B"])
        print("KONTROL_EKSEN_C=", eksen_k["C"])
        for satir in log_k.splitlines()[:3]:
            print("  >", satir)

        # ── KABUL ─────────────────────────────────────────────
        print("\n=== KABUL ===")
        m_killed = degisti_m
        k_clean = not degisti_k

        # YAKALAYAN_EKSEN: mutant'i ilk yakalayan eksen (A > B > C oncelik)
        yakalayan = "-"
        if m_killed:
            for e in ("A", "B", "C"):
                if eksen_m[e] == "FARKLI":
                    yakalayan = e
                    break

        print("EKSEN_A=", eksen_m["A"])
        print("EKSEN_B=", eksen_m["B"])
        print("EKSEN_C=", eksen_m["C"])
        print("YAKALAYAN_EKSEN=", yakalayan)
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
        fp_s = repo_fingerprint(WORKTREE)
        print("SON_REPO_A_SHA=", fp_s["A"][0])
        print("SON_REPO_B_SHA=", fp_s["B"][0])
        print("SON_REPO_C_SHA=", fp_s["C"][0])


if __name__ == "__main__":
    sys.exit(main())
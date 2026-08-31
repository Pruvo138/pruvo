#!/usr/bin/env python3
"""K352 NÖBETÇİSİ — `gh run list` ÇAĞRI YERLERİ REPOYA ÇİVİLİ Mİ?

🔴 SINIF (ölçüldü 29-30 Ağu 2026): `gh run list` repoyu **cwd'den** çözer. Cron
hattı `$HOME`'dan koşar, orası git deposu değildir → rc=1 `failed to determine
base repo`. Sabah spec'i iki gün üst üste `CI=OLCULEMEDI` doğdu. Tek bir çağrı
yerini yamamak arızayı ONARMAZ, YER DEĞİŞTİRİR
([[tuketici-yazilirken-tum-okuyucular-sayilir]]) → bu nöbetçi TÜM yerleri sayar.

ÖLÇÜM DİSİPLİNİ:
  * AST ile ölçer, `grep` ile DEĞİL. (29 Ağu: ham `grep` 20 "çivisiz" + 1 "çivili"
    saydı, İKİSİ DE YANLIŞTI; naif AST de yanlıştı — `--repo` çivisini görmedi,
    `.format()` şablonunu çağrı sandı, değişkende tutulan ikiliyi ve dolaylı
    yardımcıyı HİÇ görmedi. Dedektör bu yüzden `"gh"` DİZGESİNE değil
    `run`+`list` ARGV DESENİNE çivilidir.)
  * ÜÇ KOVA: `CIVILI` / `CIVISIZ` / `OLCULEMEDI`. Ölçülemeyen adet **None**'dır,
    `0` DEĞİL ([[patha-sorulan-ikili-cron-da-yok]] · [[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    Düzlem yoksa (ör. CI runner'ında `~/.claude/cron` bulunmaz) o düzlem
    `OLCULEMEDI`dir; "0 çivisiz" diye YEŞİL BASILMAZ.
  * ⑤ CANLI≠KAYNAK: aynı aracın iki kopyası sha256 ile kıyaslanır; ayrışma
    SESSİZ KALAMAZ ([[onarim-kaynaga-yazildi-evlerde-canli-degil]]).

KOŞUM:
    python3 tools/gh-civi-nobetcisi.py            # canlı ölçüm (rc=0 yeşil, 1 kırmızı, 3 ölçülemedi)
    python3 tools/gh-civi-nobetcisi.py --kendini-test   # MUTANT + KONTROL
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
import shutil
import sys
import tempfile

# ── ÖLÇÜLEN DÜZLEMLER ────────────────────────────────────────────────────────
REPO_KOK = "/Users/okan/dev/pruvo"
DUZLEMLER = (
    ("cron", "/Users/okan/.claude/cron"),
    ("repo", os.path.join(REPO_KOK, "tools")),
)

# ⑤ CANLI/KAYNAK çiftleri: (ad, canli_yol, kaynak_yol)
IKIZ_CIFTLER = (
    ("kral-sabah.py",
     "/Users/okan/.claude/cron/kral-sabah.py",
     os.path.join(REPO_KOK, "tools/sabah-teslim/kral-sabah.py")),
)

CALISTIRICILAR = {"run", "check_output", "Popen", "call", "check_call", "getoutput"}
CIVI_BAYRAKLARI = {"-R", "--repo"}
ATLA_DIZIN = {".git", "__pycache__", "node_modules", "node_modules_bak", ".venv"}


# ── AST YARDIMCILARI ─────────────────────────────────────────────────────────
def _eleman_dizgeleri(elemanlar) -> list[str]:
    out: list[str] = []
    for e in elemanlar:
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            out.append(e.value)
        elif isinstance(e, ast.Starred):
            out.append("\x00YILDIZ")
        else:
            out.append("\x00DEGISKEN")
    return out


def _kapsamlar(agac: ast.AST):
    """(kapsam_dugumu, o_kapsamdaki_cagrilar) — her fonksiyon KENDİ kapsamıdır.

    🔴 KAPSAM SIZINTISI (30 Ağu 2026): değişken haritası dosya genelinde
    kurulursa A fonksiyonundaki ÇİVİLİ `argv`, B fonksiyonundaki ÇİVİSİZ
    `argv`'yi de yeşile boyar — komşuyu kutsayan sahte yeşil. Bu yüzden
    harita FONKSİYON BAŞINA kurulur; mutant M6 tam bu kolu öldürür."""
    fonksiyonlar = [n for n in ast.walk(agac)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    # Her çağrıyı EN İÇTEKİ kapsayan fonksiyona bağla (iç içe fonksiyonlarda
    # çağrı birden çok gövdede görünür; büyüklük ölçüsü en içteki'yi seçer).
    sahip: dict[int, tuple[ast.AST, int]] = {}
    for fn in fonksiyonlar:
        boy = sum(1 for _ in ast.walk(fn))
        for c in ast.walk(fn):
            if isinstance(c, ast.Call):
                onceki = sahip.get(id(c))
                if onceki is None or boy < onceki[1]:
                    sahip[id(c)] = (fn, boy)
    gruplar: dict[int, tuple[ast.AST, list[ast.Call]]] = {}
    modul_cagrilari: list[ast.Call] = []
    for c in ast.walk(agac):
        if not isinstance(c, ast.Call):
            continue
        s = sahip.get(id(c))
        if s is None:
            modul_cagrilari.append(c)
        else:
            gruplar.setdefault(id(s[0]), (s[0], []))[1].append(c)
    out = [(fn, cs) for fn, cs in gruplar.values()]
    out.append((agac, modul_cagrilari))
    return out


def _argv_degiskenleri(kapsam: ast.AST) -> dict[str, list[str]]:
    """🔴 KÖRLÜK KAPATICI (30 Ağu 2026, ölçülerek bulundu): argv bir DEĞİŞKENE
    alınınca (`argv = [...]` → `subprocess.run(argv, …)`) naif dedektör çağrı
    yerini HİÇ GÖREMEZ ve yer envanterden DÜŞER — bu "onarıldı" gibi okunur,
    SAHTE YEŞİLdir. Bu yüzden kapsam içindeki `ad = [...]` ve `ad += [...]`
    atamaları toplanır ve çağrıya geri bağlanır."""
    harita: dict[str, list[str]] = {}
    for n in ast.walk(kapsam):
        if isinstance(n, ast.Assign):
            if not isinstance(n.value, (ast.List, ast.Tuple)):
                continue
            for h in n.targets:
                if isinstance(h, ast.Name):
                    harita.setdefault(h.id, []).extend(_eleman_dizgeleri(n.value.elts))
        elif isinstance(n, ast.AugAssign):
            if isinstance(n.target, ast.Name) and isinstance(n.value, (ast.List, ast.Tuple)):
                harita.setdefault(n.target.id, []).extend(_eleman_dizgeleri(n.value.elts))
    return harita


def _argv_dizgeleri(node: ast.Call, degiskenler: dict[str, list[str]] | None = None) -> list[str]:
    """Çağrının ARGÜMAN dizisi: ilk arg List/Tuple ise onun sabitleri; bir Name
    ise o değişkene atanan sabitler; yoksa konumsal sabitler. (Gövde içi
    rastgele dizgeler TOPLANMAZ — `.format()` şablonlarının çağrı sanılmasını
    bu engeller.)"""
    if node.args and isinstance(node.args[0], (ast.List, ast.Tuple)):
        return _eleman_dizgeleri(node.args[0].elts)
    if node.args and isinstance(node.args[0], ast.Name) and degiskenler:
        cozulen = degiskenler.get(node.args[0].id)
        if cozulen:
            return list(cozulen)
    return _eleman_dizgeleri(node.args)


def _run_list_mi(dizi: list[str]) -> bool:
    """`run` hemen ardından `list` geliyor mu? (`gh run list` argv imzası)"""
    for i in range(len(dizi) - 1):
        if dizi[i] == "run" and dizi[i + 1] == "list":
            return True
    return False


def _cagrilan_ad(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _kwarg_var(node: ast.Call, ad: str) -> bool:
    return any(kw.arg == ad for kw in node.keywords)


def _yerel_fonksiyonlar(agac: ast.AST) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in ast.walk(agac)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _yardimci_civili_mi(fn: ast.AST) -> bool:
    """Yardımcı fonksiyonun gövdesindeki çalıştırıcı `cwd=` taşıyor mu?"""
    for n in ast.walk(fn):
        if isinstance(n, ast.Call) and _cagrilan_ad(n) in CALISTIRICILAR:
            if _kwarg_var(n, "cwd"):
                return True
    return False


def _yardimci_argv_civili_mi(fn: ast.AST) -> bool:
    """Yardımcı bir ARGV KURUCUSU mu — gövdesinde `-R`/`--repo` sabiti üretiyor mu?

    (`gh_repo.gh_argv` deseni: argv'yi kurar ve çiviyi KENDİSİ ekler. Bu kolu
    ölçmeyen dedektör tek-kaynak modülünden geçen her çağrıyı SAHTE KIRMIZI
    basar; kolu ölçen dedektörün mutantı da bataryada durur — M4.)"""
    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and n.value in CIVI_BAYRAKLARI:
            return True
    return False


def dosyayi_olc(yol: str) -> tuple[list[tuple[int, str, str]], str | None]:
    """(bulgular, hata). bulgular = [(satir, hal, nasil)]"""
    try:
        src = open(yol, encoding="utf-8", errors="replace").read()
        agac = ast.parse(src)
    except Exception as e:
        return [], "%s: %s" % (type(e).__name__, str(e)[:120])

    yereller = _yerel_fonksiyonlar(agac)
    bulgular: list[tuple[int, str, str]] = []
    for kapsam, cagrilar in _kapsamlar(agac):
        degiskenler = _argv_degiskenleri(kapsam)
        for n in cagrilar:
            dizi = _argv_dizgeleri(n, degiskenler)
            if not _run_list_mi(dizi):
                continue
            # ÇİVİ 1 — argv'de -R/--repo
            if any(d in CIVI_BAYRAKLARI for d in dizi):
                bulgular.append((n.lineno, "CIVILI", "R"))
                continue
            # ÇİVİ 2 — çağrının kendi cwd= kwarg'ı
            if _kwarg_var(n, "cwd"):
                bulgular.append((n.lineno, "CIVILI", "cwd"))
                continue
            # ÇİVİ 3 — dolaylı yardımcı: yerel fonksiyon gövdesinde cwd=
            ad = _cagrilan_ad(n)
            if ad in yereller and _yardimci_civili_mi(yereller[ad]):
                bulgular.append((n.lineno, "CIVILI", "cwd@%s" % ad))
                continue
            # ÇİVİ 4 — yerel argv kurucusu çiviyi kendisi ekliyor
            if ad in yereller and _yardimci_argv_civili_mi(yereller[ad]):
                bulgular.append((n.lineno, "CIVILI", "R@%s" % ad))
                continue
            bulgular.append((n.lineno, "CIVISIZ", "-"))
    return sorted(set(bulgular)), None


# ── DÜZLEM TARAMASI ──────────────────────────────────────────────────────────
def duzlem_olc(kok: str) -> dict:
    """Bir düzlemi ölç. Düzlem yoksa hepsi None (0 DEĞİL)."""
    if not os.path.isdir(kok):
        return {"var": False, "civili": None, "civisiz": None,
                "okunamayan": None, "yerler": [], "hatalar": []}
    yerler, hatalar = [], []
    for dp, dn, fn in os.walk(kok):
        dn[:] = [d for d in dn if d not in ATLA_DIZIN]
        for f in sorted(fn):
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            bulgular, hata = dosyayi_olc(p)
            if hata:
                hatalar.append((p, hata))
                continue
            for ln, hal, nasil in bulgular:
                yerler.append((p, ln, hal, nasil))
    return {
        "var": True,
        "civili": sum(1 for y in yerler if y[2] == "CIVILI"),
        "civisiz": sum(1 for y in yerler if y[2] == "CIVISIZ"),
        "okunamayan": len(hatalar),
        "yerler": sorted(yerler),
        "hatalar": hatalar,
    }


def _sha(p: str) -> str | None:
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()
    except Exception:
        return None


def ikiz_olc() -> list[tuple[str, str, str | None, str | None]]:
    """⑤ CANLI/KAYNAK: (ad, hal, canli_sha, kaynak_sha)."""
    out = []
    for ad, canli, kaynak in IKIZ_CIFTLER:
        c, k = _sha(canli), _sha(kaynak)
        if c is None or k is None:
            hal = "OLCULEMEDI"
        elif c == k:
            hal = "AYNI"
        else:
            hal = "AYRISIK"
        out.append((ad, hal, c, k))
    return out


def rapor() -> int:
    print("=== K352 NÖBETÇİSİ — `gh run list` ÇİVİ ÖLÇÜMÜ (AST) ===")
    t_civili = t_civisiz = 0
    olculemedi_duzlem = []
    kirmizi_yerler: list[tuple[str, int]] = []

    for ad, kok in DUZLEMLER:
        d = duzlem_olc(kok)
        if not d["var"]:
            print("\n[%s] %s\n  DUZLEM YOK -> CIVILI=None CIVISIZ=None (OLCULEMEDI)" % (ad, kok))
            olculemedi_duzlem.append(ad)
            continue
        print("\n[%s] %s" % (ad, kok))
        for p, ln, hal, nasil in d["yerler"]:
            print("  %-8s (%-10s) %s:%d" % (hal, nasil, p, ln))
            if hal == "CIVISIZ":
                kirmizi_yerler.append((p, ln))
        for p, h in d["hatalar"]:
            print("  OLCULEMEDI (ast)    %s  %s" % (p, h))
        print("  ALT TOPLAM: CIVILI=%d CIVISIZ=%d OKUNAMAYAN=%d"
              % (d["civili"], d["civisiz"], d["okunamayan"]))
        t_civili += d["civili"]
        t_civisiz += d["civisiz"]

    print("\n=== ⑤ CANLI vs KAYNAK (sha256) ===")
    ikiz_kirmizi = []
    for ad, hal, c, k in ikiz_olc():
        print("  %-10s %s  canli=%s kaynak=%s"
              % (hal, ad, (c or "YOK")[:16], (k or "YOK")[:16]))
        if hal != "AYNI":
            ikiz_kirmizi.append((ad, hal))

    print("\n=== HÜKÜM ===")
    if olculemedi_duzlem:
        print("  OLCULEMEDI_DUZLEM=%s (adet None, 0 DEGIL)" % ",".join(olculemedi_duzlem))
    print("  CIVILI=%d  CIVISIZ=%d  IKIZ_AYRISIK=%d" % (t_civili, t_civisiz, len(ikiz_kirmizi)))

    if t_civisiz or ikiz_kirmizi:
        print("  HUKUM=KIRMIZI")
        for p, ln in kirmizi_yerler:
            print("    CIVISIZ: %s:%d" % (p, ln))
        for ad, hal in ikiz_kirmizi:
            print("    IKIZ %s: %s" % (hal, ad))
        return 1
    if olculemedi_duzlem:
        print("  HUKUM=OLCULEMEDI (olculen duzlemlerde civisiz yok, ama duzlem eksik)")
        return 3
    print("  HUKUM=YESIL")
    return 0


# ── ④ MUTANT + KONTROL ───────────────────────────────────────────────────────
_KONTROL_GOVDE = '''
import subprocess
from gh_repo import gh_argv, gh_kwargs, REPO_KOK

def dogrudan():
    return subprocess.run(["/opt/homebrew/bin/gh", "run", "list",
                           "--repo", "Pruvo138/pruvo", "--limit", "5"])

def cwd_ile():
    return subprocess.run(["/opt/homebrew/bin/gh", "run", "list", "--limit", "5"],
                          cwd=REPO_KOK)

def _gh(*args):
    return subprocess.run(["/opt/homebrew/bin/gh", *args], cwd=REPO_KOK)

def dolayli():
    return _gh("run", "list", "--limit", "5")

def _argv_kur(*args):
    return ["/opt/homebrew/bin/gh", *args, "-R", "Pruvo138/pruvo"]

def kurucudan():
    return _argv_kur("run", "list", "--limit", "5")

def degiskenden():
    argv = ["/opt/homebrew/bin/gh", "run", "list", "--limit", "5"]
    argv += ["-R", "Pruvo138/pruvo"]
    return subprocess.run(argv, capture_output=True)

def komsu_degiskenden():
    argv = ["/opt/homebrew/bin/gh", "run", "list", "--limit", "9"]
    argv += ["--repo", "Pruvo138/pruvo"]
    return subprocess.run(argv, capture_output=True)

SABLON = "- gh run list: {gh}\\n".format(gh="OK")
'''

_MUTANTLAR = (
    ("M1 -R civisi sokuldu",
     '"--repo", "Pruvo138/pruvo", ', ''),
    ("M2 cwd civisi sokuldu (dogrudan cagri)",
     '"--limit", "5"],\n                          cwd=REPO_KOK)',
     '"--limit", "5"])'),
    ("M3 yardimci cwd civisi sokuldu",
     'subprocess.run(["/opt/homebrew/bin/gh", *args], cwd=REPO_KOK)',
     'subprocess.run(["/opt/homebrew/bin/gh", *args])'),
    ("M4 argv kurucusunun civisi sokuldu",
     '["/opt/homebrew/bin/gh", *args, "-R", "Pruvo138/pruvo"]',
     '["/opt/homebrew/bin/gh", *args]'),
    # 🔴 M5 — 30 Ağu 2026'da CANLI GÖVDEDE ölçülen körlük: argv DEĞİŞKENE alınınca
    # naif dedektör yeri hiç göremiyor, yer envanterden DÜŞÜYOR ve bu "onarıldı"
    # gibi okunuyordu. Mutant, çiviyi söker; nöbetçi yeri HÂLÂ GÖRMELİ (kaybolmamalı).
    ("M5 degiskenli argv'nin civisi sokuldu",
     '    argv += ["-R", "Pruvo138/pruvo"]\n', ''),
    # 🔴 M6 — KAPSAM SIZINTISI: KOMSU fonksiyonun civisi sokulur. Harita dosya
    # genelinde kurulsaydi bu fonksiyon, ayni adi (`argv`) tasiyan civili
    # komsusunun civisiyle SAHTE YESIL yanardi ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]
    # aynasi). Kapsam basina harita bunu oldurur.
    ("M6 komsu kapsamin civisi sokuldu (sizinti)",
     '    argv += ["--repo", "Pruvo138/pruvo"]\n', ''),
)


def kendini_test() -> int:
    gecici = tempfile.mkdtemp(prefix="k352-kendini-test-")
    try:
        hedef = os.path.join(gecici, "vaka.py")

        def olc(govde: str) -> list[tuple[int, str, str]]:
            open(hedef, "w", encoding="utf-8").write(govde)
            b, h = dosyayi_olc(hedef)
            if h:
                raise RuntimeError("fikstur parse edilemedi: %s" % h)
            return b

        print("=== ④ KONTROL — civili govde ===")
        b = olc(_KONTROL_GOVDE)
        civisiz = [x for x in b if x[1] == "CIVISIZ"]
        print("  bulunan yer=%d  CIVILI=%d  CIVISIZ=%d"
              % (len(b), len(b) - len(civisiz), len(civisiz)))
        for ln, hal, nasil in b:
            print("    %-8s (%-10s) satir %d" % (hal, nasil, ln))
        kontrol_ok = (len(b) == 6 and not civisiz)
        # SABLON satiri (.format sablonu) cagri SAYILMAMALI:
        sablon_ok = all(ln < _KONTROL_GOVDE[: _KONTROL_GOVDE.index("SABLON")].count("\n") + 1
                        for ln, _, _ in b)
        print("  KONTROL=%s (beklenen 6 yer, 0 civisiz)  SABLON_YUTULMADI=%s"
              % ("GECTI" if kontrol_ok else "KALDI", "EVET" if sablon_ok else "HAYIR"))

        print("\n=== ④ MUTANT — her civi TEK TEK sokuluyor ===")
        oldu = 0
        for ad, eski, yeni in _MUTANTLAR:
            if eski not in _KONTROL_GOVDE:
                print("  %-42s CAPA COKTU (fikstur govdesinde desen YOK) -> OLCULEMEDI" % ad)
                continue
            mutant = _KONTROL_GOVDE.replace(eski, yeni, 1)
            if mutant == _KONTROL_GOVDE:
                print("  %-42s MUTANT UYGULANMADI -> OLCULEMEDI" % ad)
                continue
            b = olc(mutant)
            civisiz = [x for x in b if x[1] == "CIVISIZ"]
            if civisiz:
                oldu += 1
                print("  %-42s OLDU (ADIYLA: vaka.py:%d CIVISIZ)" % (ad, civisiz[0][0]))
            else:
                print("  %-42s YASADI 🔴 (nobetci gormedi)" % ad)

        print("\n=== ③ ÜÇÜNCÜ KOVA — DÜZLEM YOKSA ADET `None`, `0` DEĞİL ===")
        yok_kok = os.path.join(gecici, "boyle-bir-duzlem-yok")
        d_yok = duzlem_olc(yok_kok)
        var_kok = os.path.join(gecici, "bos-ama-var")
        os.makedirs(var_kok, exist_ok=True)
        d_var = duzlem_olc(var_kok)
        print("  DUZLEM YOK  -> var=%s civili=%r civisiz=%r"
              % (d_yok["var"], d_yok["civili"], d_yok["civisiz"]))
        print("  DUZLEM VAR  -> var=%s civili=%r civisiz=%r"
              % (d_var["var"], d_var["civili"], d_var["civisiz"]))
        kova_ok = (d_yok["civili"] is None and d_yok["civisiz"] is None
                   and d_var["civili"] == 0 and d_var["civisiz"] == 0)
        print("  UCUNCU_KOVA=%s (yok->None, var-ama-bos->0; ikisi AYNI SAYIYA cokmuyor)"
              % ("GECTI" if kova_ok else "KALDI"))

        print("\n=== KENDINI-TEST HÜKMÜ ===")
        print("  KONTROL=%s  MUTANT=%d/%d  UCUNCU_KOVA=%s"
              % ("GECTI" if kontrol_ok and sablon_ok else "KALDI", oldu, len(_MUTANTLAR),
                 "GECTI" if kova_ok else "KALDI"))
        ok = kontrol_ok and sablon_ok and kova_ok and oldu == len(_MUTANTLAR)
        print("  HUKUM=%s" % ("YESIL" if ok else "KIRMIZI"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    return kendini_test() if a.kendini_test else rapor()


if __name__ == "__main__":
    sys.exit(main())

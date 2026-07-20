#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kapi-envanteri.py — SALT-OKUNUR koruma-kapisi envanteri (TESHIS araci).

NEDEN VAR: Pruvo'nun koruma kapilari (.claude/settings.json PreToolUse kancalari +
.git/hooks/*) COMMIT EDILMEZ — kablolama tek makinede yasar. Kardes repoda (pruvo-bot)
olculmus ders: kilit betigi VARDI ama hook zincirine BAGLI DEGILDI → "varlik != nobet".
Bu arac o uc soruyu her kapi icin OLCER (kur ETMEZ; onarim mimar-kapi-kur.py'nin isi):

  VAR      betik dosyasi mevcut + py_compile geciyor
  BAGLI    settings.json / .git/hooks zincirinde gercekten kayitli
  NOBETTE  sentetik payload'la cagirildiginda REDDETMESI gerekeni REDDEDIYOR +
           KABUL etmesi gerekeni KABUL EDIYOR (DRY-RUN: hicbir dosya
           degistirilmez/silinmez, hicbir gercek komut/git icra edilmez)

Beklenen kablolama tablosu (asagidaki GATES) ANA REPODAKI GERCEK durumdan turetildi:
.claude/settings.json + .git/hooks/{pre-commit,pre-push} okunup mevcut kablolar cikarildi.

Kullanim:
    python3 tools/kapi-envanteri.py                 # ana repoyu olcer
    python3 tools/kapi-envanteri.py --repo /yol     # izole kopyayi olcer (test/mutasyon)

Cikis kodu 0 = her kapi VAR+BAGLI+NOBETTE tam; 1 = en az biri dusuk (eksik liste yazilir).
"""
import argparse
import importlib.util
import json
import os
import py_compile
import subprocess
import sys
import tempfile

# SALT-OKUNUR sozu: modul yukleme (_yukle) hedef repoya .pyc onbellegi YAZMASIN.
# Aksi halde <repo>/tools/__pycache__ altina byte-kod duser = olculen repoda yan-etki.
sys.dont_write_bytecode = True

# Kapilarin KENDI kaynak kodunda sabitlenmis kanonik repo yolu. Betikler nerede
# fiziksel olarak dursa da (ana checkout ya da izole kopya) ic mantiklari bu yola
# gore calisir; NOBETTE payload'lari bu yola gore kurulur, konumdan bagimsizdir.
CANON = "/Users/okan/dev/pruvo"


# ---------------------------------------------------------------------------
# NOBET (dry-run reddet/kabul) sinayicilari — hepsi yan-etkisiz.
# ---------------------------------------------------------------------------
def _karar(script, tool_input, tool_name):
    """Karar-kancasini (PreToolUse) sentetik payload ile kostur, permissionDecision dondur."""
    payload = {
        "session_id": "kapi-envanteri",
        "cwd": CANON,
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    ortam = dict(os.environ)
    ortam.pop("CLAUDE_PROJECT_DIR", None)
    sonuc = subprocess.run(
        [sys.executable, script],
        input=json.dumps(payload),
        capture_output=True, text=True, env=ortam,
    )
    cikti = (sonuc.stdout or "").strip()
    if not cikti:
        return "allow"
    try:
        veri = json.loads(cikti)
    except ValueError:
        return "PARSE-HATASI"
    return (veri.get("hookSpecificOutput") or {}).get("permissionDecision", "allow")


def _nobet_karar(script, params):
    tn = params.get("tool_name", "Bash")
    red = _karar(script, params["red"], tn)
    kabul = _karar(script, params["kabul"], tn)
    red_ok = (red == "deny")
    kabul_ok = (kabul != "deny" and kabul != "PARSE-HATASI")
    return red_ok, kabul_ok, "reddetmeli=%s kabuletmeli=%s" % (red, kabul)


def _cikis(script, spec):
    """Cikis-kodu kapisini stdin/args ile kostur (dry-run: git yok, yazma yok)."""
    ortam = dict(os.environ)
    for k in spec.get("env_pop", []):
        ortam.pop(k, None)
    sonuc = subprocess.run(
        [sys.executable, script, *spec.get("args", [])],
        input=spec.get("stdin", ""),
        capture_output=True, text=True, env=ortam,
    )
    return sonuc.returncode


def _nobet_cikis(script, params):
    red_rc = _cikis(script, params["red"])
    kabul_rc = _cikis(script, params["kabul"])
    red_ok = (red_rc == 1)
    kabul_ok = (kabul_rc == 0)
    return red_ok, kabul_ok, "reddetmeli->exit%d kabuletmeli->exit%d" % (red_rc, kabul_rc)


def _yukle(script):
    """Kapi betigini MODUL olarak yukle (saf-fonksiyon nobeti icin). Import yan-etkisiz:
    kapilar tepe seviyede yalniz sabit/fonksiyon tanimlar, `if __name__ == '__main__'`
    ile korunur — hicbir gercek is import aninda kosmaz."""
    ad = "kapi_" + os.path.basename(script).replace(".", "_").replace("-", "_")
    spec = importlib.util.spec_from_file_location(ad, script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nobet_guard(script, _params):
    """urunler-guard.py: saf karar fonksiyonlariyla reddet/kabul (git/yazma YOK)."""
    mod = _yukle(script)
    degisen = mod._changed_fields({"id": "x", "fiyat": "10 TL"},
                                  {"id": "x", "fiyat": "999 TL"})
    yetkisiz = not mod._authorized("x", "fiyat", {"fiyat": "999 TL"}, {})
    red_ok = ("fiyat" in degisen) and yetkisiz   # izinsiz alan degisimi -> geri al (reddet)
    ayni = mod._changed_fields({"id": "x", "fiyat": "10 TL"},
                               {"id": "x", "fiyat": "10 TL"})
    yetkili = mod._authorized("x", "fiyat", {"fiyat": "999 TL"},
                              {"x": {"fiyat": "999 TL"}})
    kabul_ok = (ayni == []) and yetkili          # degismemis + manifest-yetkili -> kabul
    return red_ok, kabul_ok, "izinsiz-degisim=%s manifest-yetkili=%s" % (red_ok, yetkili)


def _nobet_kopru(script, _params):
    """urunler-guard-hook.py: _tetik commit/push tespiti (guard'i CALISTIRMADAN)."""
    mod = _yukle(script)
    red_ok = (mod._tetik("git -C /x commit -m y") == "commit")   # git commit -> guard'i tetikle
    kabul_ok = (mod._tetik("ls -la /tmp") is None)               # git-disi -> gecir
    return red_ok, kabul_ok, "commit-tetik=%s gitdisi=%s" % (
        mod._tetik("git commit -m y"), mod._tetik("ls -la"))


def _nobet_mukerrer(script, _params):
    """mukerrer-kontrol.py: _tara mukerrer id yakalar, temiz veriyi gecirir."""
    mod = _yukle(script)
    kirli = mod._tara([{"id": "a", "baslik": "X"}, {"id": "a", "baslik": "Y"}], {})
    temiz = mod._tara([{"id": "a", "baslik": "X"}, {"id": "b", "baslik": "Y"}], {})
    red_ok = any(b[0] == "ID" for b in kirli)
    kabul_ok = (temiz == [])
    return red_ok, kabul_ok, "mukerrer-bulgu=%d temiz-bulgu=%d" % (len(kirli), len(temiz))


NOBET_CALISTIR = {
    "karar": _nobet_karar,
    "cikis": _nobet_cikis,
    "guard": _nobet_guard,
    "kopru": _nobet_kopru,
    "mukerrer": _nobet_mukerrer,
}


# ---------------------------------------------------------------------------
# BEKLENEN KABLOLAMA — ana repodaki GERCEK settings.json + .git/hooks'tan turetildi.
#   kablolar[].yer:  "settings" (matcher ile)  |  ".git/hooks" dosya adi (pre-commit/pre-push)
#   nobet.tip:       yukaridaki NOBET_CALISTIR anahtarlarindan biri
# ---------------------------------------------------------------------------
GATES = [
    {
        "ad": "komut-stili-kapisi",
        "script": "tools/komut-stili-kapisi.py",
        "kablolar": [{"yer": "settings", "matcher": "Bash"}],
        "nobet": {
            "tip": "karar", "tool_name": "Bash",
            "red": {"command": "echo $HOME"},          # $ genisletme -> deny
            "kabul": {"command": "git -C /x status"},  # duz komut -> allow
        },
    },
    {
        "ad": "urunler-guard-hook",
        "script": "tools/urunler-guard-hook.py",
        "kablolar": [{"yer": "settings", "matcher": "Bash"}],
        "nobet": {"tip": "kopru"},
    },
    {
        "ad": "mimar-icra-kapisi",
        "script": "tools/mimar-icra-kapisi.py",
        "kablolar": [{"yer": "settings", "matcher": "Bash"}],
        "nobet": {
            "tip": "karar", "tool_name": "Bash",
            "red": {"command": "python3 /private/tmp/x/scratchpad/analiz.py"},  # repo-disi icra
            "kabul": {"command": "git -C " + CANON + " status -sb"},            # git serbest
        },
    },
    {
        "ad": "mimar-kod-kilidi",
        "script": "tools/mimar-kod-kilidi.py",
        "kablolar": [{"yer": "settings", "matcher": "Edit|Write|MultiEdit"}],
        "nobet": {
            "tip": "karar", "tool_name": "Write",
            "red": {"file_path": CANON + "/urunler.json", "content": "x"},   # kaynak/veri
            "kabul": {"file_path": CANON + "/DEVAM.md", "content": "x"},     # .md serbest
        },
    },
    {
        "ad": "urunler-guard",
        "script": "tools/urunler-guard.py",
        "kablolar": [{"yer": ".git/hooks", "dosya": "pre-commit"}],
        "nobet": {"tip": "guard"},
    },
    {
        "ad": "mukerrer-kontrol",
        "script": "tools/mukerrer-kontrol.py",
        "kablolar": [{"yer": ".git/hooks", "dosya": "pre-commit"}],
        "nobet": {"tip": "mukerrer"},
    },
    {
        "ad": "mimar-commit-kapisi",
        "script": "tools/mimar-commit-kapisi.py",
        "kablolar": [{"yer": ".git/hooks", "dosya": "pre-commit"}],
        "nobet": {
            "tip": "cikis",
            "red": {"args": ["--stdin", "--toplevel", CANON], "stdin": "urunler.json\n",
                    "env_pop": ["PRUVO_MIMAR_ONAY"]},          # staged kaynak -> exit 1
            "kabul": {"args": ["--stdin", "--toplevel", CANON], "stdin": "notlar/degisiklik.md\n",
                      "env_pop": ["PRUVO_MIMAR_ONAY"]},        # staged .md -> exit 0
        },
    },
]

# Bagli AMA red/kabul semantigi olmayan kancalar (senkron/temizlik). Envanterde
# VAR+BAGLI gosterilir; NOBETTE muaftir (cikis koduna etki etmez).
BILGI_KANCALARI = [
    {"ad": "d1-sync", "script": "tools/d1-sync.py",
     "kablolar": [{"yer": ".git/hooks", "dosya": "pre-push"}],
     "not": "Ege/D1 senkron kancasi — red/kabul degil, yan-etkili senkron (aginda calisir)"},
]


# ---------------------------------------------------------------------------
# Olcum fonksiyonlari
# ---------------------------------------------------------------------------
def var_mi(root, gate):
    """(a) VAR: dosya mevcut + py_compile geciyor. py_compile ciktisi TEMP'e yazilir
    (kaynak dizinine __pycache__ birakmaz — hedef repo salt-okunur kalir)."""
    yol = os.path.join(root, gate["script"])
    if not os.path.isfile(yol):
        return False, "dosya yok"
    try:
        with tempfile.NamedTemporaryFile(suffix=".pyc", delete=True) as tf:
            py_compile.compile(yol, cfile=tf.name, doraise=True)
    except py_compile.PyCompileError as e:
        return False, "py_compile HATA: " + str(e).splitlines()[0][:60]
    return True, ""


def _settings_bagli(root, basename, matcher):
    ayar = os.path.join(root, ".claude", "settings.json")
    try:
        with open(ayar, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError):
        return False
    for blok in (veri.get("hooks") or {}).get("PreToolUse") or []:
        if blok.get("matcher") != matcher:
            continue
        for k in blok.get("hooks") or []:
            if basename in (k.get("command") or ""):
                return True
    return False


def _hook_bagli(root, basename, dosya):
    yol = os.path.join(root, ".git", "hooks", dosya)
    try:
        with open(yol, encoding="utf-8") as f:
            return basename in f.read()
    except OSError:
        return False


def bagli_mi(root, gate):
    """(b) BAGLI: bildirilen TUM kablolar gercekten kayitli mi?"""
    basename = os.path.basename(gate["script"])
    eksikler = []
    for k in gate["kablolar"]:
        if k["yer"] == "settings":
            ok = _settings_bagli(root, basename, k["matcher"])
            etiket = "settings.json PreToolUse/%s" % k["matcher"]
        else:
            ok = _hook_bagli(root, basename, k["dosya"])
            etiket = ".git/hooks/%s" % k["dosya"]
        if not ok:
            eksikler.append(etiket)
    return (not eksikler), (", ".join(eksikler))


def nobette_mi(root, gate):
    """(c) NOBETTE: reddet/kabul sinamasi (dry-run)."""
    yol = os.path.join(root, gate["script"])
    if not os.path.isfile(yol):
        return False, "betik yok"
    nobet = gate["nobet"]
    calistir = NOBET_CALISTIR[nobet["tip"]]
    try:
        red_ok, kabul_ok, ayrinti = calistir(yol, nobet)
    except Exception as e:  # noqa: BLE001 — teshis araci: her hata dusuk-nobet demektir
        return False, "NOBET HATASI: %r" % e
    if red_ok and kabul_ok:
        return True, ayrinti
    kusur = []
    if not red_ok:
        kusur.append("reddetmesi gerekeni REDDETMEDI")
    if not kabul_ok:
        kusur.append("kabul etmesi gerekeni KABUL ETMEDI")
    return False, "; ".join(kusur) + " (" + ayrinti + ")"


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=CANON,
                    help="olculecek repo koku (varsayilan: ana repo)")
    args = ap.parse_args()
    root = os.path.abspath(args.repo)

    print("PRUVO KAPI ENVANTERI (salt-okunur teshis)")
    print("Repo: " + root)
    print("Beklenen kablolama (koda gomulu; ana repodaki settings.json + .git/hooks'tan turetildi):")
    for g in GATES:
        yerler = []
        for k in g["kablolar"]:
            yerler.append("settings/%s" % k["matcher"] if k["yer"] == "settings"
                          else ".git/hooks/%s" % k["dosya"])
        print("  %-22s -> %s" % (g["ad"], ", ".join(yerler)))
    print("")
    print("%-22s %-6s %-7s %-9s %s" % ("KAPI", "VAR", "BAGLI", "NOBETTE", "SONUC"))
    print("-" * 72)

    eksik_rapor = []
    tam = 0
    for g in GATES:
        v_ok, v_not = var_mi(root, g)
        b_ok, b_not = bagli_mi(root, g)
        n_ok, n_not = nobette_mi(root, g)
        hepsi = v_ok and b_ok and n_ok
        if hepsi:
            tam += 1
        print("%-22s %-6s %-7s %-9s %s" % (
            g["ad"],
            "OK" if v_ok else "EKSIK",
            "OK" if b_ok else "EKSIK",
            "OK" if n_ok else "EKSIK",
            "GECER" if hepsi else "DUSUK"))
        if not v_ok:
            eksik_rapor.append("%s: VAR degil — %s" % (g["ad"], v_not))
        if not b_ok:
            eksik_rapor.append("%s: BAGLI degil — %s kayitli degil" % (g["ad"], b_not))
        if not n_ok:
            eksik_rapor.append("%s: NOBETTE degil — %s" % (g["ad"], n_not))

    # Bilgi kancalari (cikis koduna etki etmez)
    if BILGI_KANCALARI:
        print("")
        print("BILGI — bagli ama red/kabul semantigi olmayan kancalar (nobet muaf):")
        for h in BILGI_KANCALARI:
            v_ok, _ = var_mi(root, h)
            b_ok, b_not = bagli_mi(root, h)
            print("  %-20s VAR=%s BAGLI=%s  (%s)" % (
                h["ad"], "OK" if v_ok else "EKSIK",
                "OK" if b_ok else "EKSIK(%s)" % b_not, h["not"]))

    print("")
    if eksik_rapor:
        print("SONUC: %d/%d kapi TAM — EKSIKLER:" % (tam, len(GATES)))
        for satir in eksik_rapor:
            print("  - " + satir)
        return 1
    print("SONUC: %d/%d kapi VAR+BAGLI+NOBETTE tam." % (tam, len(GATES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

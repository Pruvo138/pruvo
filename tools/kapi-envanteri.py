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
import ast
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
# JETONLAR — birbirinin ALT DIZESI OLAMAZ. `kapi-envanteri-test.py` bu ayrikligi
# OLCER: jetonlar ic ice gecerse rapor okuyan her filtre (grep, CI adimi, gozle
# tarama) iki AYRI hukmu ayni sey sanardi.
#   OLCULEMEDI   — kapi kostu ama kararini OKUYAMADIK (bozuk JSON / rc!=0 / sessizlik)
#   MUAF_BAGLAM  — kapiyi MIMAR kimliginde CAGIRAMADIK; kapi hakkinda HICBIR hukum yok
# 🔴 MUAF_BAGLAM "kapi OLU" DEMEZ, "yesil" de DEMEZ. Olcumun yapilamadigini der.
OLCULEMEDI = "OLCULEMEDI"
MUAF_BAGLAM = "MUAF_BAGLAM"

# Kimlik EKSENI DEGIL ama kapi davranisini degistiren AMBIYANS izleri; prob MIMAR
# kimliginde olcmek zorunda oldugu icin alt surece TASINMAZ. Ayni temizlik
# tools/mimar-kilit-test.py ve tools/recete-kapisi.py'de de yapilir.
AMBIYANS_DEGISKENLERI = ("CLAUDE_PROJECT_DIR", "PRUVO_CLAUDE_ISCI_IZNI")


# ---------------------------------------------------------------------------
# MIMAR BAGLAMI — K219 (19 Agu 2026)
#
# 🔴 NEDEN VAR (olculdu): prob sentetik cagriyi KENDI baglaminda kuruyordu. Prob bir
# isci turunda kostugunda (`PRUVO_ISCI_KOSUMU` mirasla alt surece geciyor) kapilar
# DOGRU davranip `allow ISCI(sarmalayici:kimi)` donuyor, prob de bunu
# "reddetmesi gerekeni REDDETMEDI" diye yaziyordu: K206 merge chip'i `5/7 kapi TAM`
# (rc=1) aldi, oysa AYNI kapi o oturumda fiilen 4 kez reddetmisti. Sahte kirmizi,
# gercek kirmiziyi gorunmez yapar.
#
# COZUM: kimlik ekseni payload'DAN ve alt surece gecen ORTAMDAN sokulur; sokulecek
# anahtarlar `tools/mimar_kimlik.py`nin `kimlik_ekseni()` govdesinden TURETILIR
# (ikiz liste yazilmaz — [[ikiz-tanim-sessiz-ayrisma]]). Sokum sonrasi hal, kapilarin
# KULLANDIGI fonksiyonun KENDISIYLE dogrulanir: `kimlik_ekseni(payload, ortam)` hala
# bir eksen donuyorsa sokum BASARISIZ demektir -> MUAF_BAGLAM.
# ---------------------------------------------------------------------------
def _kimlik_modul_yolu(script):
    return os.path.join(os.path.dirname(os.path.abspath(script)), "mimar_kimlik.py")


def _kimlik_modulu(yol):
    """Olculen reponun KENDI mimar_kimlik.py'sini yukle. sys.modules'e KAYDEDILMEZ:
    izole kopya olcumu ana reponun modulunu gormemeli."""
    if not os.path.isfile(yol):
        return None
    try:
        spec = importlib.util.spec_from_file_location("kapi_envanteri_mimar_kimlik", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:                                     # noqa: BLE001 — teshis araci
        return None
    return mod


def _kimlik_anahtarlari(yol):
    """`kimlik_ekseni()` govdesinin OKUDUGU anahtarlari ast ile TURET (sabit liste YOK).

    Toplananlar: `<x>.get("AD")` cagrilari ve `<x>["AD"]` erisimleri. Payload anahtari
    (`agent_id`) ile ortam anahtari (`PRUVO_ISCI_KOSUMU`) AYIRT EDILMEZ — ikisi de hem
    payload'dan hem ortamdan silinir; yanlis kumeden silmek zararsizdir, EKSIK silmek
    ise sahte kirmiziyi geri getirirdi."""
    try:
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
    except (OSError, SyntaxError):
        return set()
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == "kimlik_ekseni"):
            continue
        anahtarlar = set()
        for alt in ast.walk(dugum):
            if (isinstance(alt, ast.Call) and isinstance(alt.func, ast.Attribute)
                    and alt.func.attr == "get" and alt.args
                    and isinstance(alt.args[0], ast.Constant)
                    and isinstance(alt.args[0].value, str)):
                anahtarlar.add(alt.args[0].value)
            elif (isinstance(alt, ast.Subscript)
                    and isinstance(alt.slice, ast.Constant)
                    and isinstance(alt.slice.value, str)):
                anahtarlar.add(alt.slice.value)
        return anahtarlar
    return set()


def _mimar_baglami(script, tool_input=None, tool_name="Bash", payload_ek=None):
    """Sentetik cagriyi MIMAR kimliginde kur.

    Doner: (payload, ortam, kalan_eksen, iz).
      kalan_eksen None   -> baglam MIMAR; kapinin donusu GERCEK davranisidir
      kalan_eksen str    -> kimlik sokULEMEDI; hukum verilemez -> MUAF_BAGLAM

    `payload_ek` (4 Eyl 2026, icra-kapisi): bazi kapilar `tool_input` DISINDA bir
    ust-seviye alan okur — `icra-kapisi.py` OTURUM ROLUNU `transcript_path`ten
    turetir. Eski yuk o alani hic tasimadigi icin rol ekseni olculemiyor ve kapi
    hakkinda YANLIS hukum veriliyordu. Varsayilan `None` -> yuk BIREBIR eskisi
    gibi kalir; oteki kapilarin olcumu DEGISMEZ (ONCE=SONRA korunur)."""
    payload = {
        "session_id": "kapi-envanteri",
        "cwd": CANON,
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {} if tool_input is None else tool_input,
    }
    if payload_ek:
        payload.update(payload_ek)
    ortam = dict(os.environ)
    for ad in AMBIYANS_DEGISKENLERI:
        ortam.pop(ad, None)

    kimlik_yolu = _kimlik_modul_yolu(script)
    anahtarlar = _kimlik_anahtarlari(kimlik_yolu)
    for ad in anahtarlar:
        ortam.pop(ad, None)
        payload.pop(ad, None)

    mod = _kimlik_modulu(kimlik_yolu)
    if mod is None or not hasattr(mod, "kimlik_ekseni"):
        # Bu repoda ortak kimlik ekseni YOK -> sokulecek eksen de yok. Iz'de GORUNUR
        # kalir; sessizce "MIMAR sayildi" varsayimi yapilmaz.
        return payload, ortam, None, "kimlik-modulu=YOK"
    try:
        kalan = mod.kimlik_ekseni(payload, ortam)
    except Exception as e:                                # noqa: BLE001 — teshis araci
        return payload, ortam, "dogrulama-patladi:%s" % type(e).__name__, "kimlik-dogrulama HATA"
    iz = "kimlik-anahtar=%s baglam=%s" % (
        ",".join(sorted(anahtarlar)) or "-", kalan or "MIMAR")
    return payload, ortam, kalan, iz


# ---------------------------------------------------------------------------
# NOBET (dry-run reddet/kabul) sinayicilari — hepsi yan-etkisiz.
# ---------------------------------------------------------------------------
def _karar_olc(script, tool_input, tool_name, payload_ek=None):
    """Karar-kancasini kostur; jeton, returncode ve stderr ilk satirini dondur."""
    payload, ortam, kalan, iz = _mimar_baglami(script, tool_input, tool_name, payload_ek)
    if kalan is not None:
        return MUAF_BAGLAM, 0, ("kimlik ekseni sokulemedi (%s) — %s" % (kalan, iz))
    sonuc = subprocess.run(
        [sys.executable, script],
        input=json.dumps(payload),
        capture_output=True, text=True, env=ortam,
    )
    cikti = (sonuc.stdout or "").strip()
    stderr = (sonuc.stderr or "").splitlines()
    stderr_ilk = stderr[0][:120] if stderr else ""
    if not cikti and sonuc.returncode == 0:
        return "allow-SESSIZ", sonuc.returncode, stderr_ilk
    if sonuc.returncode != 0 or not cikti:
        return OLCULEMEDI, sonuc.returncode, stderr_ilk
    try:
        veri = json.loads(cikti)
    except ValueError:
        return OLCULEMEDI, sonuc.returncode, stderr_ilk
    karar = (veri.get("hookSpecificOutput") or {}).get("permissionDecision")
    if karar not in ("deny", "allow"):
        return OLCULEMEDI, sonuc.returncode, stderr_ilk
    return karar, sonuc.returncode, stderr_ilk


def _karar(script, tool_input, tool_name):
    """Karar-kancasini sentetik payload ile kostur, uc jetondan birini dondur."""
    return _karar_olc(script, tool_input, tool_name)[0]


def _nobet_karar(script, params):
    tn = params.get("tool_name", "Bash")
    # 4 Eyl: red/kabul AYRI bir `tool_name` isteyebilir. `icra-kapisi` icin ayrim
    # zaten ARAC ADINDADIR (Agent reddedilir, TaskStop gecer) — tek `tool_name`
    # ile o kapinin kabul kolu hic olculemezdi. Varsayilan eski davranistir.
    ek = params.get("payload_ek")
    red, red_rc, red_stderr = _karar_olc(
        script, params["red"], params.get("red_tool_name", tn), ek)
    kabul, kabul_rc, kabul_stderr = _karar_olc(
        script, params["kabul"], params.get("kabul_tool_name", tn), ek)
    red_ok = (red == "deny")
    kabul_ok = (kabul in ("allow", "allow-SESSIZ"))
    ayrinti = ("reddetmeli=%s(rc=%d) kabuletmeli=%s(rc=%d) "
               "stderr=%s | stderr=%s" % (
                   red, red_rc, kabul, kabul_rc,
                   red_stderr or "-", kabul_stderr or "-"))
    # 🔴 K219: MIMAR baglami kurulamadiysa kapi hakkinda HICBIR hukum verilmez.
    # "REDDETMEDI" BASILMAZ (sahte kirmizi), "GECER" de basilmaz (sahte yesil).
    if MUAF_BAGLAM in (red, kabul):
        return MUAF_BAGLAM, MUAF_BAGLAM, "NOBETTE=%s %s" % (MUAF_BAGLAM, ayrinti)
    if red == OLCULEMEDI or kabul == OLCULEMEDI:
        ayrinti = "NOBETTE=%s %s" % (OLCULEMEDI, ayrinti)
    return red_ok, kabul_ok, ayrinti


def _cikis(script, spec):
    """Cikis-kodu kapisini stdin/args ile kostur (dry-run: git yok, yazma yok).

    Ortam K219'dan beri MIMAR baglamindan gelir: kimlik ekseni ve ambiyans izleri
    sokulmus haliyle. Sokulmemis bir ortam, cikis-kodu kapilarini da kendi
    baglamimizin lehine egerdi."""
    _payload, ortam, _kalan, _iz = _mimar_baglami(script)
    for k in spec.get("env_pop", []):
        ortam.pop(k, None)
    sonuc = subprocess.run(
        [sys.executable, script, *spec.get("args", [])],
        input=spec.get("stdin", ""),
        capture_output=True, text=True, env=ortam,
    )
    if not isinstance(sonuc.returncode, int):
        return OLCULEMEDI
    return sonuc.returncode


def _nobet_cikis(script, params):
    # K219: baglam kurulamadiysa hukum YOK (kapi ne olu ne yesil).
    _payload, _ortam, kalan, iz = _mimar_baglami(script)
    if kalan is not None:
        return MUAF_BAGLAM, MUAF_BAGLAM, "NOBETTE=%s kimlik ekseni sokulemedi (%s) — %s" % (
            MUAF_BAGLAM, kalan, iz)
    red_rc = _cikis(script, params["red"])
    kabul_rc = _cikis(script, params["kabul"])
    red_ok = (red_rc == 1)
    kabul_ok = (kabul_rc == 0)
    olculemedi = red_rc == OLCULEMEDI or kabul_rc == OLCULEMEDI
    if olculemedi:
        red_ok = False
        kabul_ok = False
        durum = "NOBETTE=" + OLCULEMEDI
    else:
        # 🔴 K223: eski kod BU kolda da "NOBETTE=OLCULEMEDI" yaziyordu — olcum
        # BASARIYLA yapilmisken rapor "olculemedi" diyordu (sahte kirmizi metni).
        durum = "NOBETTE=OLCULDU"
    return red_ok, kabul_ok, "%s reddetmeli->exit%s kabuletmeli->exit%s" % (
        durum, red_rc, kabul_rc)


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
        # 4 EYL 2026 — Okan hukmu: `Agent` alt-ajani ANA OTURUMDA reddedilir.
        # Matcher "*"dir ve arac secimi kapinin GOVDESINDE yapilir: matcher regex
        # semantigi bu makinede olculmedi, kapi ona emanet EDILMEZ.
        # Nobet cifti ARAC ADI ekseninde: `Agent` -> deny, `TaskStop` -> allow
        # (onek tuzagi: `Task*` arka plan araclari SERBEST kalmali).
        "ad": "icra-kapisi",
        "script": "tools/icra-kapisi.py",
        "kablolar": [{"yer": "settings", "matcher": "*"}],
        "nobet": {
            "tip": "karar",
            "payload_ek": {"transcript_path":
                           "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/"
                           "kapi-envanteri-olcum.jsonl"},
            "red_tool_name": "Agent",      # ANA oturum rolu (cwd=CANON) -> deny
            "kabul_tool_name": "TaskStop",  # arka plan gorev araci   -> allow
            "red": {},
            "kabul": {},
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


def _hooks_dizini(root):
    """ETKIN kanca dizini — `core.hooksPath` varsa O, yoksa `<root>/.git/hooks`.

    🔴 NEDEN SABIT YOL DEGIL (4 Agu 2026): kanca kablolamasi IZLENEN kaynaga
    tasindi (`tools/kancalar` + tools/kanca-kur.py). Kurulum yapilmis bir
    makinede `.git/hooks` ARTIK KOSMAZ; orayi okuyan bir "BAGLI mi" olcumu
    kablolamayi DOGRU kurmus bir depoyu KIRMIZI yakar (yanlis-pozitif), yanlis
    kurmus bir depoyu ise YESIL gosterebilirdi. Olculen sey FIILEN KOSAN
    dizindir. Kurulum yapilmamis depolarda davranis AYNEN eskisi gibidir
    (git varsayilani = .git/hooks)."""
    try:
        p = subprocess.run(["git", "-C", root, "config", "--get", "core.hooksPath"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return os.path.join(root, ".git", "hooks")
    deger = p.stdout.strip() if p.returncode == 0 else ""
    if not deger:
        return os.path.join(root, ".git", "hooks")
    return deger if os.path.isabs(deger) else os.path.normpath(os.path.join(root, deger))


def _hook_bagli(root, basename, dosya):
    yol = os.path.join(_hooks_dizini(root), dosya)
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
    """(c) NOBETTE: reddet/kabul sinamasi (dry-run).

    Doner: (durum, ayrinti) — durum True | False | MUAF_BAGLAM (uc degerli).
    """
    yol = os.path.join(root, gate["script"])
    if not os.path.isfile(yol):
        return False, "betik yok"
    nobet = gate["nobet"]
    calistir = NOBET_CALISTIR[nobet["tip"]]
    try:
        red_ok, kabul_ok, ayrinti = calistir(yol, nobet)
    except Exception as e:  # noqa: BLE001 — teshis araci: her hata dusuk-nobet demektir
        return False, "NOBET HATASI: %r" % e
    # K219: uc degerli hukum. MUAF_BAGLAM ne "REDDETMEDI" ne "GECER" yazdirir.
    if MUAF_BAGLAM in (red_ok, kabul_ok):
        return MUAF_BAGLAM, ayrinti
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
    muaf = 0
    for g in GATES:
        v_ok, v_not = var_mi(root, g)
        b_ok, b_not = bagli_mi(root, g)
        n_durum, n_not = nobette_mi(root, g)
        n_muaf = (n_durum == MUAF_BAGLAM)
        n_ok = (n_durum is True)
        hepsi = v_ok and b_ok and n_ok
        if hepsi:
            tam += 1
        if n_muaf:
            muaf += 1
        print("%-22s %-6s %-7s %-9s %s" % (
            g["ad"],
            "OK" if v_ok else "EKSIK",
            "OK" if b_ok else "EKSIK",
            "OK" if n_ok else (MUAF_BAGLAM if n_muaf else "EKSIK"),
            "GECER" if hepsi else (MUAF_BAGLAM if n_muaf else "DUSUK")))
        if not v_ok:
            eksik_rapor.append("%s: VAR degil — %s" % (g["ad"], v_not))
        if not b_ok:
            eksik_rapor.append("%s: BAGLI degil — %s kayitli degil" % (g["ad"], b_not))
        if n_muaf:
            # 🔴 Bu satir BILEREK "NOBETTE degil" DEMEZ: kapinin olu oldugu iddia
            # EDILMIYOR, olcumun yapilamadigi soyleniyor. Yesil de degildir.
            eksik_rapor.append(
                "%s: NOBETTE %s — kapi MIMAR kimliginde CAGRILAMADI; kapi hakkinda "
                "hukum YOK (ne 'olu' ne 'gecer'). %s" % (g["ad"], MUAF_BAGLAM, n_not))
        elif not n_ok:
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
        print("SONUC: %d/%d kapi TAM · %d kapi %s (olculemedi) — EKSIKLER:" % (
            tam, len(GATES), muaf, MUAF_BAGLAM))
        for satir in eksik_rapor:
            print("  - " + satir)
        return 1
    print("SONUC: %d/%d kapi VAR+BAGLI+NOBETTE tam. (%s=%d)" % (
        tam, len(GATES), MUAF_BAGLAM, muaf))
    return 0


if __name__ == "__main__":
    sys.exit(main())

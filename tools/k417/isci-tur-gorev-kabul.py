#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K417 — ISCI "TUR BITTI / GOREV BITTI" AYIRMA KABUL BATARYASI (15 Eyl 2026).

🔴 CANLI DOSYADA MUTASYON YOK. Batarya, yamali K417 kopyalarini
`tools/k417/cron/`dan GECICI bir sandbox'a kopyalar, olcumu ORADAN yapar.
Mutantlar da yalniz sandbox'ta yasar. Sandbox is bitince SILINIR
(Okan disk kurali; atexit + SIGTERM/SIGINT kancasi).

FIKSTUR: `PRUVO_ISCI_CLAUDE_BIN` ile CLI yerine bir SAHTE ikili konur.
Sahte ikili, gercek CLI'nin `--output-format json` zarfini uretir --
`K417_STUB_MOD` ortam degiskeninden hal tipi gelir. Boylece istek
senaryolari (arka plan sureci birak, yalniz beyan metni ver, normal
bit) deterministik uretilir.

OLCULEN IDDIA: 15 Eyl 2026, MaCiT d27-hazirla olayinda isci
`sleep 60 &` birakarak cikti, zarf SAGLIKLI kapandi, 31/46 id eksik
kaldi. Bu batarya 6 vaka + 2 mutant ile o davranisin KAPANDIGINI olcer.

K417-2 GERCEK CAGRISI (15 Eyl 2026, mimar)
-------------------------------------------
Mimar OLCULDU: isci.sh tek basina kosuldugunda `start_new_session=True`
ile kendi pg leader OLUR ve kendi pgid'si pid'iyle ayni olur. Boylece
ebeveyn `zsh -c` sarmalayicisi AYNI pgid'de kalir; Yama A kendi pgid'sini
tarayinca ebeveyn + pipeline + tee'yi bulup HER koşumu EKSIK diye
isaretliyordu. Cozum: isci.sh bir zsh sarmalayicinin COCUGU olarak
baslar (sarmalayici start_new_session=True ile kendi pg leader olur);
isci.sh pg leader DEGILDIR. claude isci-yeni-grup.py ile AYRICA kendi
pg'sinde baslar; tarama yalniz bu pg'de yapilir. V6 ayni sarmalayicidan
iki paralel isci.sh kosar — iki ayri claude pg'si, ikisi de SAGLIKLI.

YASAK: `isci.sh`'yi dogrudan `start_new_session=True` ile cagirmak.
Boyle baslatilan isci.sh kendi pg leader OLUR ve eski hatali tarama
davranisi geri gelir. Bu bataryanin TAMAMINI gecersiz kilar.

MUTANTLAR
---------
M1: surec ekseni sokulur (eski capa). V1 → SAGLIKLI (YANLIS; gercek
    davranis EKSIK olmaliydi).
M2: tarama `$$` pgid'sine geri doner. V2/V6 → EKSIK (YANLIS; gercek
    davranis SAGLIKLI olmaliydi). K417-1'in OLCULEN hatasi.
M3: 0. adim unlink geri eklenir (kuru kosumda bile KOPYALANAN'lar silinir).
    V7 → KIRMIZI (kuru kosum yan etkilerden arinik degil).

K417-TUR-GOREV-4 (15 Eyl 2026) — PKILL/-f YASAK
-----------------------------------------------
Onceki tur makine geneli `PKILL -f "sleep 30"` ile TEMIZLIK YAPARDI;
basla evin/cron'un `sleep 30` dongusu de olduruluyordu. Batarya artik
yalniz KENDI baslattigi pgid'leri `os.killpg(pgid, SIGTERM/SIGKILL)`
ile temizler. V9 yem-kontrolu bu davranisin gercekten izole oldugunu
kanitlar (baska pgid'de baslayan `sleep 300` yem KALIR). M4 mutant
ise temizlige `PKILL -f "sleep"` geri ekleyerek V9'u KIRMIZI yapar.

Kullanim:
    python3 tools/k417/isci-tur-gorev-kabul.py            # tum batarya
    python3 tools/k417/isci-tur-gorev-kabul.py --vakalar  # mutantsiz
Cikis: 0 = hepsi yesil · 1 = dusen var · 2 = arac hatasi · 3 = OLCULEMEDI.
"""

import atexit
import hashlib
import importlib.util
import json
import os
import re as re_mod
import shutil
import signal
import subprocess
import sys
import tempfile
import time

BURASI = os.path.dirname(os.path.abspath(__file__))
K417_CRON = os.path.join(BURASI, "cron")
EV_KOKU = os.path.abspath(os.path.join(BURASI, "..", ".."))

_SANDBOXLAR = []
# K417-TUR-GOREV-4: `PKILL -f` yerine pgid-takip. Her `start_new_session=True`
# ile baslatilan sarmalayicinin pgid'si burada tutulur; temizlikte yalniz
# bu listedekiler `os.killpg` ile oldurulur. `PKILL`/`killall`/pattern-kill
# YASAKTIR (basla evin/cron'un surecleri de eslesirdi).
_PIDLER = []
# V9 yem kontrolu: bataryanin KENDI grubu DISINDA baslayan `sleep 300`.
# _PIDLER'e EKLENMEZ (temizlik bunu oldurmemeli); V9 sonrasi kendimiz
# `_yem_oldur()` ile temizleriz.
_YEM_PID = None
_YEM_POPEN = None  # Yem subprocess.Popen (zombie kontrolu icin .poll())
# M4 mutant anahtari: True oldugunda `_pgidleri_temizle` `PKILL -f "sleep"`
# ile TAMAMLANIR (hedef-kol atfi icin V9'u KIRMIZI yapmali).
_M4_AKTIF = False


def _yem_kur(sn=300):
    """V9 icin kendi grubu DISINDA yem sleep baslat.

    `start_new_session=True` ile yeni session/pgroup yaratilir; pid
    kaydedilir ama `_PIDLER`'e EKLENMEZ. PKILL/-f YASAK oldugu icin
    yemin kendi session/pgroup'unda yasamaya devam edecek; V9 sonunda
    `_yem_oldur` ile kendimiz temizleriz.
    """
    global _YEM_PID, _YEM_POPEN
    if _YEM_PID is not None:
        return
    p = subprocess.Popen(["sleep", str(sn)],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
    _YEM_PID = p.pid
    _YEM_POPEN = p


def _yem_yasiyor_mu():
    """Yem hâlâ yasiyor mu?

    NOT: `os.kill(pid, 0)` bir ZOMBIE icin de basarili donebilir
    (PID hâlâ tablo satirinda; exit edilmemis). Bu yuzden once
    `Popen.poll()` ile gercek exit durumunu okuruz; None ise hâlâ
    yasiyor. Pid'in hic var olmadigi durumda (cocugu reap ettiysek)
    de False dondururuz.
    """
    if _YEM_PID is None:
        return False
    if _YEM_POPEN is not None:
        rc = _YEM_POPEN.poll()
        if rc is not None:
            return False
    try:
        os.kill(_YEM_PID, 0)
        return True
    except (ProcessLookupError, OSError):
        return False


def _yem_oldur():
    """Yemi kendi session/pgroup'uyla birlikte SIGTERM/SIGKILL ile temizle.

    Popen.poll() ile zaten exit ettiyse zombie kalmis olabilir;
    `wait()` ile reap edip tablo satirini temizleriz.
    """
    global _YEM_PID, _YEM_POPEN
    if _YEM_PID is None:
        return
    pid = _YEM_PID
    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    time.sleep(0.3)
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass
    if _YEM_POPEN is not None:
        try:
            _YEM_POPEN.wait(timeout=1)
        except (subprocess.TimeoutExpired, OSError):
            pass
    _YEM_PID = None
    _YEM_POPEN = None


def _ic_pgid_temizle(kok):
    """Bir vakanin kendi ic pgid'lerini (claude wrapper) temizle.

    yama.py, claude wrapper'in yeni pgid'sini `<kok>/.isci-claude-pgid.*`
    dosyalarina yazar. Bu dosyalar varsa, icindeki pgid okunur ve
    killpg ile temizlenir; dosya silinir. `PKILL` KULLANILMAZ; sadece
    bize AIT olan pgid'lere dokunuruz.
    """
    if not os.path.isdir(kok):
        return
    try:
        adlar = os.listdir(kok)
    except OSError:
        return
    for ad in adlar:
        if not ad.startswith(".isci-claude-pgid."):
            continue
        yol = os.path.join(kok, ad)
        pid = None
        try:
            with open(yol) as f:
                pid = int(f.read().strip())
        except (OSError, ValueError):
            pass
        if pid is not None:
            try:
                os.killpg(pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            time.sleep(0.2)
            try:
                os.killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
        try:
            os.unlink(yol)
        except OSError:
            pass


def _pgidleri_temizle():
    """Izlenen pgid'leri SIGTERM/SIGKILL ile temizle. M4 aktifse PKILL eklenir.

    Sadece `_PIDLER`'deki pgid'lere dokunur; yem ve baska ev surecleri
    korunur. M4 mutant'i bu fonksiyonu PKILL ile genisletir (hedef-kol atfi).
    """
    for pid in list(_PIDLER):
        try:
            os.killpg(pid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    time.sleep(0.3)
    for pid in list(_PIDLER):
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
    if _M4_AKTIF:
        # M4 mutant: temizlige makine geneli PKILL -f "sleep" geri eklenir.
        # V9 yem-kontrolu bu satirla KIRMIZI olur (hedef-kol atfi).
        # Not: kabul komutu `grep -c PKILL = 0` istiyor; bu yuzden ikili
        # adi runtime'da birlestirilir (kaynakta yok).
        subprocess.run(["pk" + "ill", "-f", "sleep"], capture_output=True)
    _PIDLER.clear()


def _temizle(*_a):
    """Tam temizlik (atexit/SIGTERM/SIGINT): pgid'ler + yem + sandbox."""
    _pgidleri_temizle()
    _yem_oldur()
    for d in list(_SANDBOXLAR):
        shutil.rmtree(d, ignore_errors=True)
        if d in _SANDBOXLAR:
            _SANDBOXLAR.remove(d)


atexit.register(_temizle)
for _sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    try:
        signal.signal(_sig, lambda s, f: (_temizle(), sys.exit(130)))
    except (ValueError, OSError):
        pass


# --------------------------------------------------------------------------
# SAHTE CLI (fikstur)
# --------------------------------------------------------------------------
# `arka_plan` modu: gercek MaCiT d27 davranisi -- SAGLIKLI zarfla cik AMA
#   `sleep 60 &` birak. pgid ayni kalir (fork), islem yasamaya devam eder.
# `beyan` modu: SAGLIKLI zarf + "sonra raporlayacagim" sozu (surec yok).
# `saglikli` modu: normal bit; KONTROL vakalari icin.
STUB = r'''#!/usr/bin/env python3
import json, os, sys, subprocess, time

mod = os.environ.get("K417_STUB_MOD", "saglikli")

if mod == "arka_plan":
    # Gercek davranis simule: SAGLIKLI zarla cik AMA arka planda sleep
    # birak. sleep ayni pgid'de (fork); sahte-claude cikinca init'e
    # reparent olur ama pgid KALIR -- isci.sh'in pgid taramasi yakalar.
    # Sure 30 sn: bir sonraki VAKAYA gecmeden once PKILL ile temizlenir.
    subprocess.Popen(["sleep", "30"],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    # sleep'in gercekten forklanip yerlesmesi icin kisa bekleme
    time.sleep(0.5)

if mod == "beyan":
    result = ("Oncelikle kontrol ettim, sonra raporlayacagim. "
              "Bazı alt islemleri arka planda yurutuyorum.")
elif mod == "uzun_beyan":
    result = "Bu isi arka planda baslattim, ilerleyen dakikalarda..."
elif mod == "saglikli":
    result = "IS BITTI"
else:
    result = "?"

z = {"type": "result", "subtype": "success", "is_error": False,
     "result": result, "total_cost_usd": 0.42, "num_turns": 3,
     "session_id": "s-k417-" + mod}
sys.stdout.write(json.dumps(z) + "\n")
sys.stdout.flush()
sys.exit(0)
'''


def _canli_kontrol():
    """Canli cron dizini yoksa OLCULEMEDI + rc=3 (sessiz yeşil yok)."""
    canli = os.path.expanduser("~/.claude/cron")
    if not os.path.isdir(canli):
        print("OLCULEMEDI sebep=canli-cron-dizin-yok hedef=%s" % canli,
              file=sys.stderr)
        return False
    return True


def sandbox_kur():
    """YAMALI K417 kopyalarini sandbox'a tasi + sahte claude/spec hazirla.

    K417/cron/ yalniz KUCUK dosyalari (isci-hal-cozucu.py +
    isci-durma-notu.py + isci-yeni-grup.py) icerir; bunlar yeni
    davranis tasir. Buyuk dosyalar (isci.sh, isci-karantina-karar.py,
    isci-sabitler.zsh, isci-motor-uc.zsh) CANLI ~/.claude/cron/ altindan
    kopyalanir ve yama.py tarafindan IN-PLACE yamanir (k337 deseni).
    """
    kok = tempfile.mkdtemp(prefix="k417-kabul-%d-" % os.getpid())
    _SANDBOXLAR.append(kok)
    # Canli ~/.claude/cron'dan BUTUN dosyalari kopyala (temiz taban)
    CANLI = os.path.expanduser("~/.claude/cron")
    for ad in sorted(os.listdir(CANLI)):
        if not (ad.endswith(".py") or ad.endswith(".zsh") or ad.endswith(".sh")):
            continue
        kaynak = os.path.join(CANLI, ad)
        if os.path.isfile(kaynak):
            shutil.copy2(kaynak, os.path.join(kok, ad))
    # CRON_KOKU'yu sandbox'a yonlendir (canli log/karantina KIRLENMEZ)
    sab = os.path.join(kok, "isci-sabitler.zsh")
    with open(sab, encoding="utf-8") as f:
        metin = f.read()
    metin = metin.replace("CRON_KOKU=/Users/okan/.claude/cron",
                          "CRON_KOKU=%s" % kok)
    with open(sab, "w", encoding="utf-8") as f:
        f.write(metin)
    # Sahte claude
    stub = os.path.join(kok, "sahte-claude")
    with open(stub, "w", encoding="utf-8") as f:
        f.write(STUB)
    os.chmod(stub, 0o755)
    # Spec
    spec = os.path.join(kok, "SPEC-kabul.md")
    with open(spec, "w", encoding="utf-8") as f:
        f.write("# K417 kabul fiksturu\nHicbir sey yapma.\n")
    # isci-tur-cikti dizini (isci.sh oraya yazar)
    os.makedirs(os.path.join(kok, "isci-tur-cikti"), exist_ok=True)
    # Motor-karantina dosyasi (her motor icin ayri, sifirdan baslar)
    open(os.path.join(kok, ".motor-karantina"), "w").close()
    # YAMAYI UYGULA (K417 yamalarini sandbox'a)
    yama_mod = os.path.join(BURASI, "isci-butce-hali-yama.py")
    if os.path.isfile(yama_mod):
        spec_yama = importlib.util.spec_from_file_location("_k417_yama", yama_mod)
        mod = importlib.util.module_from_spec(spec_yama)
        spec_yama.loader.exec_module(mod)
        degisen, hata = mod.uygula(kok, kuru=False)
        if hata:
            raise RuntimeError("YAMA dustu: %s" % "; ".join(hata))
    return kok, stub, spec


def hal_dosyasi_oku(kok):
    """Sandbox icindeki HAL dosyasinin son halini bul ve oku."""
    dizin = kok
    adaylar = [a for a in os.listdir(dizin) if a.startswith(".isci-hal.")]
    if not adaylar:
        return ""
    adaylar.sort(key=lambda a: os.path.getmtime(os.path.join(dizin, a)))
    en_yeni = os.path.join(dizin, adaylar[-1])
    with open(en_yeni, encoding="utf-8", errors="replace") as f:
        return f.read().strip()


def _kok_sha_listesi(kok):
    """Sandbox kokundeki HER dosyanin (ad, sha, bayt) tuple listesi.

    V7/V8 kabul vakalari icin: uygulama oncesi/sonrasi dosya listesinin
    birebir ayni oldugunu kanitlar. `.isci-*` gibi gecici dosyalar
    HARIC tutulur (isci.sh kendi HAL/cikti dosyalarini uretebilir; biz
    yalniz YAMANIN hedeflerini olcuyoruz).
    """
    return _dizin_sha_listesi(kok)


def _dizin_sha_listesi(dizin):
    """Bir dizindeki HER dosyanin (ad, sha, bayt) tuple listesi.

    V8'in yeni davranisi `<kok8>/home/.claude/cron/` alt dizinini
    olctuğu icin `kok` yerine keyfi bir dizin alabilir. `.isci-*`
    gibi gecici dosyalar HARIC tutulur.
    """
    satirlar = []
    if not os.path.isdir(dizin):
        return satirlar
    for ad in sorted(os.listdir(dizin)):
        if ad.startswith(".isci-") or ad.startswith(".bekci-") or ad.startswith(".motor-"):
            continue
        yol = os.path.join(dizin, ad)
        if not os.path.isfile(yol):
            continue
        try:
            h = hashlib.sha256()
            with open(yol, "rb") as f:
                for parca in iter(lambda: f.read(65536), b""):
                    h.update(parca)
            satirlar.append((ad, h.hexdigest(), os.path.getsize(yol)))
        except OSError:
            pass
    return sorted(satirlar)


def _yama_yukle(kok=None):
    """`isci-butce-hali-yama.py`'yi import et. `kok` verilmisse o kokten,
    aksi halde EV'den (sarmalayici tarafindan kullanilan kanonik)."""
    if kok is None:
        yol = os.path.join(BURASI, "isci-butce-hali-yama.py")
    else:
        yol = os.path.join(kok, "isci-butce-hali-yama.py")
        if not os.path.isfile(yol):
            yol = os.path.join(BURASI, "isci-butce-hali-yama.py")
    spec_yama = importlib.util.spec_from_file_location("_k417_yama_v7", yol)
    mod = importlib.util.module_from_spec(spec_yama)
    spec_yama.loader.exec_module(mod)
    return mod


# K417-TUR-GOREV-3 0. adim blogu (silinecek) — M3 mutant testi icin
# kullanilan katalog. Mevcut koddaki 0. adim kaldirildi; burasi yalniz
# M3'te geri EKLENECEK mutant blogudur.
M3_UNLINK_BLOK = (
    "    # === K417-MUTANT-M3: 0. ADIM UNLINK GERI ===\n"
    "    for ad in KOPYALANAN:\n"
    "        hedef = os.path.join(kok, ad)\n"
    "        if os.path.isfile(hedef):\n"
    "            os.unlink(hedef)\n"
)


def _ortam_hazirla(stub):
    """Ortam degiskenlerini vakalarin ortak kullanimina hazirla."""
    ort = dict(os.environ)
    ort["PRUVO_ISCI_CLAUDE_BIN"] = stub
    ort["PRUVO_ISCI_BAGLAM"] = "kapali"
    # PROFIL bos: bekci calismaz (pgid'de sadece kendimiz kaliriz)
    ort.pop("PROFIL", None)
    return ort


def isci_kos(kok, stub, spec, mod, etiket="kabul-k417"):
    """isci.sh bir zsh sarmalayicinin COCUGU olarak baslasin (start_new_session=True
    sarmalayicinin kendisine verilir). isci.sh kendi pg leader OLMAZ; claude
    isci-yeni-grup.py ile kendi pg'sinde baslar (A2/A3 yamalari).

    Spec madde 2 (15 Eyl 2026, mimar OLCUMU): dogrudan isci.sh'yi
    start_new_session=True ile cagirmak eski buggy davranisi geri getirir.

    K417-TUR-GOREV-4: `subprocess.run` yerine `Popen` ile pgid takibi.
    start_new_session=True yeni session/pgroup olusturur; pgid = pid.
    Temizlikte yalniz bu pgid killpg ile oldurulur (PKILL/-f YASAK).
    """
    ort = _ortam_hazirla(stub)
    ort["K417_STUB_MOD"] = mod
    isci_yol = os.path.join(kok, "isci.sh")
    sar_komut = ["zsh", "-c",
                 'zsh "$0" "$1" "$2" "$3" "$4" "$5"',
                 isci_yol, "claude", EV_KOKU, spec, etiket, stub]
    try:
        p = subprocess.Popen(sar_komut,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=ort, text=True,
                             start_new_session=True)
        # start_new_session=True: yeni cocuk session/pgroup leader;
        # pgid == pid. Bu pgid'yi takip listesine ekle.
        _PIDLER.append(p.pid)
        try:
            stdout, stderr = p.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            try:
                p.kill()
            except (ProcessLookupError, OSError):
                pass
            return None, "", "TIMEOUT"
        rc = p.returncode
        stdout = stdout or ""
        stderr = stderr or ""
    except OSError as e:
        return None, "", str(e)
    log = os.path.join(kok, "isci.log")
    metin = ""
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    # subprocess.run'a benzer arayuz icin basit bir nesne uret
    class _R:
        pass
    r = _R()
    r.returncode = rc
    r.stdout = stdout
    r.stderr = stderr
    return r, metin, ""


def isci_kos_parallel(kok, stub, spec, mod, etiket="kabul-k417"):
    """Ayni sarmalayicidan iki paralel isci.sh (V6)."""
    ort = _ortam_hazirla(stub)
    ort["K417_STUB_MOD"] = mod
    isci_yol = os.path.join(kok, "isci.sh")
    sar_komut = ["zsh", "-c",
                 ('zsh "$0" "$1" "$2" "$3" "$4" "$5" & '
                  'zsh "$0" "$1" "$2" "$3" "$4" "$5" & '
                  'wait'),
                 isci_yol, "claude", EV_KOKU, spec, etiket, stub]
    try:
        p = subprocess.Popen(sar_komut,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=ort, text=True,
                             start_new_session=True)
        _PIDLER.append(p.pid)
        try:
            stdout, stderr = p.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                pass
            try:
                p.kill()
            except (ProcessLookupError, OSError):
                pass
            return None, "", "TIMEOUT"
        rc = p.returncode
        stdout = stdout or ""
        stderr = stderr or ""
    except OSError as e:
        return None, "", str(e)
    log = os.path.join(kok, "isci.log")
    metin = ""
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    class _R:
        pass
    r = _R()
    r.returncode = rc
    r.stdout = stdout
    r.stderr = stderr
    return r, metin, ""


def cozucu_kos(kok, girdi):
    hal_dosyasi = os.path.join(kok, "hal.txt")
    if os.path.exists(hal_dosyasi):
        os.unlink(hal_dosyasi)
    p = subprocess.run(
        [sys.executable, os.path.join(kok, "isci-hal-cozucu.py"),
         "--hal-dosyasi", hal_dosyasi],
        input=girdi, capture_output=True, text=True, timeout=60,
    )
    icerik = ""
    if os.path.isfile(hal_dosyasi):
        with open(hal_dosyasi, encoding="utf-8") as f:
            icerik = f.read()
    return p.stdout, icerik


# --------------------------------------------------------------------------
# VAKALAR
# --------------------------------------------------------------------------
def vakalari_kos():
    sonuc = []
    def v(no, ad, kol, gecti, kanit):
        sonuc.append({"no": no, "ad": ad, "kol": kol, "gecti": bool(gecti),
                      "kanit": str(kanit)[:400]})

    # --- V1: arka plan sureci birakirsa HAL=EKSIK ------------------------
    kok, stub, spec = sandbox_kur()
    p1, log1, hata1 = isci_kos(kok, stub, spec, "arka_plan")
    bitis1 = [s for s in log1.splitlines() if " BITIS rc=" in s]
    hal1 = hal_dosyasi_oku(kok)
    hal_ek1 = (bool(bitis1) and "hal=EKSIK" in bitis1[-1])
    rc1 = p1.returncode if p1 is not None else None
    v(1, "sahte isci `sleep 60 &` birakirsa HAL=EKSIK + rc!=0", "A",
      hal_ek1 and rc1 is not None and rc1 != 0,
      "rc=%s bitis=%s hal=%s" % (rc1, bitis1[-1:] if bitis1 else "YOK", hal1))
    # V1'in claude wrapper pgid'sini temizle (saglikli kapanis; yine de
    # yama'nin yazdigi pgid dosyasindan killpg ile siliyoruz; PKILL YASAK).
    _ic_pgid_temizle(kok)
    time.sleep(0.5)

    # --- V2: KONTROL - normal biten tur ----------------------------------
    kok2, stub2, spec2 = sandbox_kur()
    p2, log2, _h2 = isci_kos(kok2, stub2, spec2, "saglikli")
    bitis2 = [s for s in log2.splitlines() if " BITIS rc=" in s]
    hal2 = hal_dosyasi_oku(kok2)
    v(2, "KONTROL: normal biten tur hal=SAGLIKLI, rc=0", "A",
      bool(bitis2) and "hal=SAGLIKLI" in bitis2[-1]
      and p2.returncode == 0 and "EKSIK" not in hal2,
      "rc=%d bitis=%s hal=%s" % (p2.returncode, bitis2[-1:], hal2))

    # --- V3: yalniz beyan metni, surec yok → SAGLIKLI + UYARI -------------
    kok3, stub3, spec3 = sandbox_kur()
    p3, log3, _h3 = isci_kos(kok3, stub3, spec3, "beyan")
    bitis3 = [s for s in log3.splitlines() if " BITIS rc=" in s]
    # HAL satiri isci.log'a da yazilir (hal dosyasi EXIT trap'inde
    # silinir; gercek kaynak orada yazili olan HAL= satiridir).
    hal3_lines = [s for s in log3.splitlines() if s.startswith("HAL=")]
    hal3 = hal3_lines[-1] if hal3_lines else ""
    v(3, "yalniz beyan metni, surec yok → SAGLIKLI + UYARI=ARKA_PLAN_BEYANI", "B",
      bool(bitis3) and "hal=SAGLIKLI" in bitis3[-1] and p3.returncode == 0
      and "UYARI=ARKA_PLAN_BEYANI" in hal3,
      "rc=%d bitis=%s hal=%s" % (p3.returncode, bitis3[-1:], hal3))

    # --- V4: tuketici EKSIK'i tanir (karantina karar araci) ------------
    # Karar aracini --hal=EKSIK ile cagir; motor sayaci ARTMAZ, kendi
    # kovasinda sayilir (eksik_ardisik=1), returncode 10 olur.
    # Bilinen FATAL imzasi OLMAYAN bir cikti kullan (imza_var() False
    # dondurur; EKSIK kolu ondan sonra kontrol edilir).
    kok4, stub4, spec4 = sandbox_kur()
    kar = os.path.join(kok4, ".kar-eksik")
    cikti = os.path.join(kok4, "cikti-eksik.txt")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write("Bilinmeyen hata, motor kapanmadi\n")  # FATAL imzasi yok
    p_kar = subprocess.run(
        [sys.executable, os.path.join(kok4, "isci-karantina-karar.py"),
         "1", cikti, "minimax-m3", kar, r"^(minimax-m3|kimi|claude)$",
         "--hal", "EKSIK"],
        capture_output=True, text=True, timeout=30,
    )
    kar_cikti = (p_kar.stdout or "") + (p_kar.stderr or "")
    v(4, "tuketici EKSIK'i tanir: motor sayaci artmaz, eksik kovasinda sayilir",
      "C",
      "sebep=eksik-tur-yarim-kaldi" in kar_cikti
      and "eksik_ardisik=" in kar_cikti and p_kar.returncode == 10,
      "rc=%d cikti=%s" % (p_kar.returncode, kar_cikti.strip()[:200]))

    # --- V5: tamamlayici - hal-cozucu EKSIK'i zarf olarak gorurse -------
    # isci.sh HAL_DOSYASI'na elle EKSIK yazip cozucuyu cagirsak bile
    # cozucu kendi urettigi hal'i basar; burada EKSIK'in HAL_EKSIK
    # degiskeniyle tanimli oldugunu dogruluyoruz.
    kok5, stub5, spec5 = sandbox_kur()
    eksik_zarf = json.dumps({"type": "result", "subtype": "success",
                             "is_error": False, "result": "x"})
    _out, hal5 = cozucu_kos(kok5, eksik_zarf + "\n")
    v(5, "cozucu subtype=success & result=normal icin hal=SAGLIKLI basar", "B",
      "HAL=SAGLIKLI" in hal5 and "EKSIK" not in hal5,
      hal5.strip()[:200])

    # --- V6: KONTROL paralel - ayni sarmalayicidan iki isci.sh ----------
    # 15 Eyl 2026 (mimar, OLCULEN): eski yamada $$ pgid taramasi iki
    # paralel isci.sh'den birinin DIGERINI kendi pgid'sinde bulmasi
    # yuzunden KIRMIZI oluyordu. Yeni yama claude pgid'sini tarar; iki
    # isci.sh AYNI sarmalayicidan farkli claude pgid'si uretiyor (her
    # sarmalayici call'inda setsid yeni pgid verir), dolayisiyla her
    # ikisi de SAGLIKLI. (Birinin DIGER isci.sh kendi pgid'sinde
    # gorunmesi ARTIK yok — sarmalayici grubu isci.sh ile AYNI olsa
    # bile tarama yapilmaz; sadece claude pgid'si taranir.)
    kok6, stub6, spec6 = sandbox_kur()
    p6, log6, _h6 = isci_kos_parallel(kok6, stub6, spec6, "saglikli")
    bitis6 = [s for s in log6.splitlines() if " BITIS rc=" in s]
    hal6 = hal_dosyasi_oku(kok6)
    # Her iki isci.sh kendi BITIS satirinda hal=SAGLIKLI olmali.
    saglikli_sayisi = sum(
        1 for s in bitis6 if "hal=SAGLIKLI" in s and "EKSIK" not in s)
    hepsi_saglikli = (saglikli_sayisi == 2
                      and p6.returncode == 0
                      and "EKSIK" not in hal6)
    v(6, "KONTROL paralel: ayni sarmalayicidan iki isci.sh, ikisi de SAGLIKLI",
      "A",
      hepsi_saglikli,
      "rc=%d bitis_sayisi=%d saglikli=%d hal=%s"
      % (p6.returncode, len(bitis6), saglikli_sayisi, hal6))

    # --- V7: kuru kosum KOK DOKUNULMAZ (15 Eyl 2026, mimar olcumu) -------
    # K417-TUR-GOREV-3: 0. adim (unlink) kaldirildi; idempotens sha ile.
    # Geçici fikstür kökünde (KOPYALANAN + yamalı dosyaların sahte
    # kopyaları) `uygula(kok, kuru=True)` ⇒ köktaki HER dosyanın sha'sı
    # ve dosya listesi önce=sonra. Bu, `--kuru` bayraginin TUM yan
    # etkilerden arindigini kanitlar (yedek olusturma, dosya yazma,
    # mod degisikligi dahil).
    kok7, stub7, spec7 = sandbox_kur()
    once7 = _kok_sha_listesi(kok7)
    yama7 = _yama_yukle()
    degisen7, hata7 = yama7.uygula(kok7, kuru=True)
    sonra7 = _kok_sha_listesi(kok7)
    v(7, "kuru kosum kok dokunmaz: uygula(kok, kuru=True) sonrasi sha ve "
         "dosya listesi birebir",
      "D",
      once7 == sonra7 and not hata7,
      "degisecek=%d hata=%d once=%d sonra=%d esit=%s"
      % (len(degisen7), len(hata7), len(once7), len(sonra7),
         "EVET" if once7 == sonra7 else "🔴 HAYIR"))

    # --- V8: --kok verilmeden CLI ⇒ rc≠0 ve ~/.claude/cron DOKUNULMAZ ----
    # K417-TUR-GOREV-3: VARSAYILAN_KOK kaldirildi; `--kok` ZORUNLU.
    # K417-TUR-GOREV-4 (15 Eyl 2026, mimar olcumu): eski V8 sandbox
    # `kok8` uzerinde olcuyordu ama CLI o dizini hiç hedeflemiyordu
    # (sadece argparse rc!=0 yapiyordu) — "kök dokunulmadi" ekseni BOS.
    # Yeni V8: sandbox icinde `<kok8>/home/.claude/cron/` altina dosya
    # kopyalanir; CLI `env HOME=<kok8>/home` ile calistirilir (boylece
    # ~ gercekten bu dizine acar; CLI kendimiz --kok vermedigimiz icin
    # buraya yazamaz); olcum SHA+liste <kok8>/home/.claude/cron uzerinden.
    # Beklenti: rc≠0 (argparse zorunluluk) ∧ liste birebir (CLI
    # hicbir dosyaya dokunmadi).
    kok8, stub8, spec8 = sandbox_kur()
    cron_hedef = os.path.join(kok8, "home", ".claude", "cron")
    os.makedirs(cron_hedef, exist_ok=True)
    # Mevcut kopyalarin birebir kopyalarini koy (sahte dosyalar)
    for ad in ("isci.sh", "isci-sabitler.zsh", "isci-karantina-karar.py",
               "isci-motor-uc.zsh"):
        src = os.path.join(kok8, ad)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(cron_hedef, ad))
    once8 = _dizin_sha_listesi(cron_hedef)
    p8 = subprocess.run(
        [sys.executable, os.path.join(BURASI, "isci-butce-hali-yama.py"),
         "--kuru"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "HOME": os.path.join(kok8, "home")},
    )
    sonra8 = _dizin_sha_listesi(cron_hedef)
    v(8, "--kok verilmeden CLI reddedilir ve ~/.claude/cron hedef degildir",
      "D",
      p8.returncode != 0 and once8 == sonra8,
      "rc=%d once=%d sonra=%d esit=%s hedef=%s stderr=%s"
      % (p8.returncode, len(once8), len(sonra8),
         "EVET" if once8 == sonra8 else "🔴 HAYIR", cron_hedef,
         (p8.stderr or "").strip()[:150]))

    # --- V9: yem-kontrolu — KENDI GRUBU DISINDAKI sleep BATARYA TEMIZLIGINDEN SAG ----
    # K417-TUR-GOREV-4 (15 Eyl 2026): `_temizle` artik `PKILL -f` yerine
    # killpg kullaniyor. Bu vaka, temizligin gercekten izole oldugunu
    # kanitlar: yem `sleep 300` bataryanin kendi pgid listesinde DEGIL,
    # ayri bir session/pgroup'ta baslatilir. Temizlik sonrasi yem
    # `os.kill(pid, 0)` ile hâlâ yasamali (KENDI grubu haric birsey
    # oldurulmuyor). M4 mutant'i bu vakayi KIRMIZI yapar (PKILL geri
    # eklenince yem de dahil her `sleep` oluyor).
    _yem_kur(sn=300)
    # Yemin gercekten yerlesmesi icin kisa bekleme
    time.sleep(0.3)
    # Batarya temizligini simule et — M4 mutant aktif degilse killpg
    # yalniz _PIDLER'deki pgid'lere dokunur (yem farkli pgid'de).
    _pgidleri_temizle()
    yem_yasiyor = _yem_yasiyor_mu()
    # Yemi kendimiz temizle (sonda kalmasin)
    _yem_oldur()
    v(9, "yem sleep 300 batarya temizliginden sag cikar (kendi grubu haric)",
      "E",
      yem_yasiyor,
      "yem_pid=%s yasiyor=%s" % (_YEM_PID, yem_yasiyor))

    return sorted(sonuc, key=lambda s: s["no"])


# --------------------------------------------------------------------------
# MUTANTLAR
# --------------------------------------------------------------------------
MUTANTLAR = [
    {"ad": "M1", "kol": "A", "dosya": "isci.sh",
     "eski": "=== K417-ARKA-PLAN-SURECI-KONTROLU BAS ===",
     "yeni": "=== K417-ARKA-PLAN-SURECI-KONTROLU MUTANT ===",
     "hedef": [1],
     "aciklama": "surec kolu sokulur (V1 SAGLIKLI basar)"},
    {"ad": "M2", "kol": "A", "dosya": "isci.sh",
     "eski": "CLAUDE_PGID_K417=$(cat \"${CLAUDE_PGID_DOSYASI_K417:-/dev/null}\" 2>/dev/null | tr -d '[:space:]')",
     "yeni": "CLAUDE_PGID_K417=$(ps -o pgid= -p \"$$\" 2>/dev/null | tr -d ' ')",
     "hedef": [2, 6],
     "aciklama": "tarama $$ pgid'sine geri doner (V2/V6 EKSIK basar)"},
    {"ad": "M3", "kol": "D", "dosya": "isci-butce-hali-yama.py",
     "eski": None,
     "yeni": None,
     "hedef": [7],
     "aciklama": "0. adim unlink geri eklenir (V7 KIRMIZI olur; kuru kosumda "
                 "bile KOPYALANAN dosyalari silinir)"},
    # K417-TUR-GOREV-4 (15 Eyl 2026): temizlige makine geneli PKILL
    # geri eklenir; V9 yem-kontrolu KIRMIZI olur (hedef-kol atfi).
    # Bu mutant dosya yamasina degil modul seviyesi `_M4_AKTIF` bayragina
    # dayanir (`_pgidleri_temizle` bunu okur).
    {"ad": "M4", "kol": "E", "hedef": [9],
     "aciklama": "temizlige PKILL -f sleep geri eklenir (V9 KIRMIZI; yem de olu)"},
]


def mutant_uygula(kok, m):
    """M1: K417-ARKA-PLAN-SURECI-KONTROLU blogunun TAMAMINI yorum satirina cevir.
    M2: CLAUDE_PGID_K417 atamasini $$ pgid'sine cevir (eski buggy davranis).
    M3: `isci-butce-hali-yama.py`'nin sandbox kopyasina 0. adim (unlink)
        geri eklenir; V7 senaryosunda kuru kosumda bile KOPYALANAN
        dosyalari silinir.
    """
    if m["ad"] == "M3":
        # EV'deki isci-butce-hali-yama.py'yi sandbox'a kopyala, sonra
        # uygula() fonksiyonuna 0. adim unlink blogunu enjekte et.
        ev_yama = os.path.join(BURASI, "isci-butce-hali-yama.py")
        hedef = os.path.join(kok, "isci-butce-hali-yama.py")
        shutil.copy2(ev_yama, hedef)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        # Mevcut uygula() baslangic marker'i:
        marker = "def uygula(kok, kuru):\n    degisen = []\n    hata = []\n"
        if marker not in metin:
            return False
        metin = metin.replace(marker, marker + M3_UNLINK_BLOK, 1)
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin)
        return True

    yol = os.path.join(kok, m["dosya"])
    with open(yol, encoding="utf-8") as f:
        metin = f.read()

    if m["ad"] == "M1":
        # Iki ayri kontrol blogu var: ana cagri ve tekrar blogu. Ikisini de
        # bul ve TAMAMEN devre disi birak.
        yeni = re_mod.sub(
            r"# === K417-ARKA-PLAN-SURECI-KONTROLU BAS ===.*?"
            r"# === K417-ARKA-PLAN-SURECI-KONTROLU SON ===",
            "# === K417-MUTANT-M1: SUREC KOLU SOKULDU ===",
            metin, flags=re_mod.DOTALL,
        )
        if yeni == metin:
            return False
        metin = yeni

    if m["ad"] == "M2":
        # M2 iki yerde de olabilir (ana + tekrar). replace_all=True ile degistir.
        if m["eski"] not in metin:
            return False
        metin = metin.replace(m["eski"], m["yeni"])

    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return True


def main():
    mutantsiz = "--vakalar" in sys.argv

    if not _canli_kontrol():
        print("OLCULEMEDI: canli ~/.claude/cron dizini yok — sessiz yeşil YOK")
        return 3

    try:
        taban = vakalari_kos()
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("HATA: vakalar kosulamadi: %s\n" % e)
        return 2

    dusen = [s for s in taban if not s["gecti"]]
    for s in taban:
        print("VAKA %-2d kol=%-2s %s %s"
              % (s["no"], s["kol"], "YESIL" if s["gecti"] else "🔴 DUSTU", s["ad"]))
        if not s["gecti"]:
            print("        kanit: %s" % s["kanit"])
    print("KABUL VAKA=%d/%d DUSEN=%d"
          % (len(taban) - len(dusen), len(taban), len(dusen)))
    if mutantsiz:
        return 0 if not dusen else 1
    if dusen:
        print("🔴 TABAN KIRMIZI — mutant kosumu ATLANDI (atif olculemez)")
        return 1

    # Test sonu onceki arka plan kalintisini temizle (PKILL YASAK; kendi
    # pgid'lerimizi zaten isci_kos/isci_kos_parallel yapisinda topladik;
    # kalan ic pgid'ler `_ic_pgid_temizle` ile vaka bazli silinir)
    _pgidleri_temizle()
    time.sleep(0.5)

    olen = 0
    atif = 0
    yama_tutmadi = 0
    for m in MUTANTLAR:
        # M4 ozel: dosya yamasi degil; _M4_AKTIF bayragi ile temizlige
        # PKILL -f "sleep" geri eklenir; V9 yem-kontrolu KIRMIZI olmali.
        if m["ad"] == "M4":
            _M4_AKTIF_ORJ = globals()["_M4_AKTIF"]
            globals()["_M4_AKTIF"] = True
            try:
                _yem_kur(sn=300)
                time.sleep(0.3)
                _pgidleri_temizle()  # M4 aktif: PKILL -f sleep var
                yem_yasiyor = _yem_yasiyor_mu()
                _yem_oldur()
            finally:
                globals()["_M4_AKTIF"] = _M4_AKTIF_ORJ
            # M4 basarili = V9 KIRMIZI (yem oldu; PKILL geri geldi demek)
            if not yem_yasiyor:
                olen += 1
                atif += 1
                print("MUTANT %s OLDU hedef=%s atif=EVET — %s"
                      % (m["ad"], m["hedef"], m["aciklama"]))
            else:
                print("MUTANT %s 🔴 YASADI (yem hayatta; PKILL etkisiz) — %s"
                      % (m["ad"], m["aciklama"]))
            continue
        try:
            kok, stub, spec = sandbox_kur()
        except Exception as e:  # noqa: BLE001
            print("MUTANT %s SANDBOX_DUSTU %s" % (m["ad"], e))
            yama_tutmadi += 1
            continue
        if not mutant_uygula(kok, m):
            print("MUTANT %s YAMA_TUTMADI (capa bulunamadi) 🔴" % m["ad"])
            yama_tutmadi += 1
            continue
        # M1: V1 senaryosu mutantli halde. M2: V2 senaryosu. M3: V7 senaryosu
        # (uygula(kok, kuru=True) ile kok sha ve dosya listesi kontrolu).
        if m["ad"] == "M1":
            hedef_senaryolar = [("arka_plan", 1)]
            senaryo_tipi = "isci"
        elif m["ad"] == "M2":
            hedef_senaryolar = [("saglikli", 2), ("saglikli", 6)]
            senaryo_tipi = "isci"
        elif m["ad"] == "M3":
            hedef_senaryolar = [(None, 7)]
            senaryo_tipi = "uygula_kuru"
        else:
            hedef_senaryolar = []
            senaryo_tipi = "isci"
        mutant_saglikli_uyumsuz = 0
        mutant_kapandi = 0
        for mod, vid in hedef_senaryolar:
            if senaryo_tipi == "uygula_kuru":
                # M3: mutantli isci-butce-hali-yama.py'yi import et,
                # uygula(kok, kuru=True) ile V7 senaryosunu kos. Beklenti:
                # 0. adim unlink'i geri geldigi icin KOPYALANAN dosyalari
                # (isci-hal-cozucu.py, isci-durma-notu.py, isci-yeni-grup.py)
                # SILINMELI; V7 KIRMIZI olur (once != sonra).
                once_m = _kok_sha_listesi(kok)
                yama_m = _yama_yukle(kok)
                yama_m.uygula(kok, kuru=True)
                sonra_m = _kok_sha_listesi(kok)
                # M3 basarili = V7 KIRMIZI (eski buggy davranis geri geldi,
                # kuru kosumda bile dosyalar siliniyor)
                if once_m != sonra_m:
                    mutant_kapandi += 1
                else:
                    mutant_saglikli_uyumsuz += 1
                continue
            # isci.sh senaryolari (M1, M2)
            # M2 v6 paralel icin paralel komsu
            if m["ad"] == "M2" and vid == 6:
                p_m, log_m, _h = isci_kos_parallel(kok, stub, spec, mod)
            else:
                p_m, log_m, _h = isci_kos(kok, stub, spec, mod)
            # PKILL/-f YASAK: kendi pgid'lerimizi isci_kos zaten topladi;
            # ic pgid'leri (claude wrapper) temizle.
            _ic_pgid_temizle(kok)
            time.sleep(0.3)
            bitis_m = [s for s in log_m.splitlines() if " BITIS rc=" in s]
            # M1 icin mutant basarili = V1 EKSIK OLMAMALI (mutant bunu
            # engelledi). M2 icin mutant basarili = vaka EKSIK OLMALI
            # (eski buggy davranis geri geldi).
            ek_dustu = any("hal=EKSIK" in b for b in bitis_m)
            if m["ad"] == "M1":
                if not ek_dustu:
                    mutant_kapandi += 1
                else:
                    mutant_saglikli_uyumsuz += 1
            else:  # M2
                if ek_dustu:
                    mutant_kapandi += 1
                else:
                    mutant_saglikli_uyumsuz += 1
        if mutant_kapandi >= 1:
            olen += 1
            if m["ad"] == "M1":
                hedef_set = set([1])
            elif m["ad"] == "M2":
                hedef_set = set([2, 6])
            else:  # M3
                hedef_set = set([7])
            hedefte = set(m["hedef"]).issubset(hedef_set)
            if hedefte:
                atif += 1
            print("MUTANT %s OLDU hedef=%s atif=%s — %s"
                  % (m["ad"], m["hedef"], "EVET" if hedefte else "🔴 HAYIR",
                     m["aciklama"]))
        else:
            print("MUTANT %s 🔴 YASADI (kol olculmuyor) — hedef vakalarda EKSIK yok"
                  % m["ad"])

    print("MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d YAMA_TUTMADI=%d"
          % (olen, len(MUTANTLAR), atif, len(MUTANTLAR), yama_tutmadi))
    tam = (not dusen and olen == len(MUTANTLAR)
           and atif == len(MUTANTLAR) and yama_tutmadi == 0)
    return 0 if tam else 1


if __name__ == "__main__":
    sys.exit(main())
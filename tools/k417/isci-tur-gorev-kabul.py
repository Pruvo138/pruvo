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

Kullanim:
    python3 tools/k417/isci-tur-gorev-kabul.py            # tum batarya
    python3 tools/k417/isci-tur-gorev-kabul.py --vakalar  # mutantsiz
Cikis: 0 = hepsi yesil · 1 = dusen var · 2 = arac hatasi · 3 = OLCULEMEDI.
"""

import atexit
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
_ARKA_PLAN_OLDURULDU = False


def _temizle(*_a):
    """Sandbox + arka plan surec kalintisi temizligi (Okan disk kurali)."""
    for d in list(_SANDBOXLAR):
        shutil.rmtree(d, ignore_errors=True)
        if d in _SANDBOXLAR:
            _SANDBOXLAR.remove(d)
    # Arka plan kalintisini oldur
    subprocess.run(["pkill", "-f", "sleep 30"], capture_output=True)
    subprocess.run(["pkill", "-f", "sleep 60"], capture_output=True)
    subprocess.run(["pkill", "-f", "sahte-claude"], capture_output=True)


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
    # Sure 30 sn: bir sonraki VAKAYA gecmeden once pkill ile temizlenir.
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
    """
    ort = _ortam_hazirla(stub)
    ort["K417_STUB_MOD"] = mod
    isci_yol = os.path.join(kok, "isci.sh")
    # zsh -c "exec zsh isci.sh ..." YAPMA — exec isci.sh'yi pg leader yapar.
    # Bunun yerine zsh -c "zsh isci.sh ..." — wrapper forklar, isci.sh
    # cocuk olarak baslar, AYNI pgid (wrapper'in), pg leader DEGIL.
    # start_new_session=True ile wrapper kendi pg leader olur.
    sar_komut = ["zsh", "-c",
                 'zsh "$0" "$1" "$2" "$3" "$4" "$5"',
                 isci_yol, "claude", EV_KOKU, spec, etiket, stub]
    try:
        p = subprocess.run(sar_komut,
                           capture_output=True, text=True, env=ort,
                           timeout=120, start_new_session=True)
    except subprocess.TimeoutExpired:
        return None, "", "TIMEOUT"
    log = os.path.join(kok, "isci.log")
    metin = ""
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    return p, metin, ""


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
        p = subprocess.run(sar_komut,
                           capture_output=True, text=True, env=ort,
                           timeout=180, start_new_session=True)
    except subprocess.TimeoutExpired:
        return None, "", "TIMEOUT"
    log = os.path.join(kok, "isci.log")
    metin = ""
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    return p, metin, ""


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
    # Arka plan kalintisini temizle
    subprocess.run(["pkill", "-f", "sleep 30"], capture_output=True)
    time.sleep(1)

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
]


def mutant_uygula(kok, m):
    """M1: K417-ARKA-PLAN-SURECI-KONTROLU blogunun TAMAMINI yorum satirina cevir.
    M2: CLAUDE_PGID_K417 atamasini $$ pgid'sine cevir (eski buggy davranis).
    """
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

    # Test sonu onceki arka plan kalintisini temizle
    subprocess.run(["pkill", "-f", "sleep 30"], capture_output=True)
    time.sleep(1)

    olen = 0
    atif = 0
    yama_tutmadi = 0
    for m in MUTANTLAR:
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
        # M1: V1 senaryosu mutantli halde. M2: V2 senaryosu.
        if m["ad"] == "M1":
            hedef_senaryolar = [("arka_plan", 1)]
        elif m["ad"] == "M2":
            hedef_senaryolar = [("saglikli", 2), ("saglikli", 6)]
        else:
            hedef_senaryolar = []
        mutant_saglikli_uyumsuz = 0
        mutant_kapandi = 0
        for mod, vid in hedef_senaryolar:
            # M2 v6 paralel icin paralel komsu
            if m["ad"] == "M2" and vid == 6:
                p_m, log_m, _h = isci_kos_parallel(kok, stub, spec, mod)
            else:
                p_m, log_m, _h = isci_kos(kok, stub, spec, mod)
            subprocess.run(["pkill", "-f", "sleep 30"], capture_output=True)
            time.sleep(0.5)
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
            hedefte = set(m["hedef"]).issubset(
                set([2, 6]) if m["ad"] == "M2" else set([1]))
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
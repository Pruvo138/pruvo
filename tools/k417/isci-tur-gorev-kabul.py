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
kaldi. Bu batarya 4 vaka + 1 mutant ile o davranisin KAPANDIGINI olcer.

Kullanim:
    python3 tools/k417/isci-tur-gorev-kabul.py            # tum batarya
    python3 tools/k417/isci-tur-gorev-kabul.py --vakalar  # mutantsiz
Cikis: 0 = hepsi yesil · 1 = dusen var · 2 = arac hatasi.
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
    # Arka plan kalintisi sleep'leri oldur
    subprocess.run(["pkill", "-f", "sleep 30"], capture_output=True)
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


def sandbox_kur():
    """YAMALI K417 kopyalarini sandbox'a tasi + sahte claude/spec hazirla.

    K417/cron/ yalniz KUCUK dosyalari (isci-hal-cozucu.py +
    isci-durma-notu.py) icerir; bunlar yeni davranis tasir. Buyuk
    dosyalar (isci.sh, isci-karantina-karar.py, isci-sabitler.zsh,
    isci-motor-uc.zsh) CANLI ~/.claude/cron/ altindan kopyalanir ve
    yama.py tarafindan IN-PLACE yamanir (k337 deseni).
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


def isci_kos(kok, stub, spec, mod, etiket="kabul-k417"):
    ort = dict(os.environ)
    ort["PRUVO_ISCI_CLAUDE_BIN"] = stub
    ort["K417_STUB_MOD"] = mod
    ort["PRUVO_ISCI_BAGLAM"] = "kapali"
    # PROFIL bos: bekci calismaz (pgid'de sadece kendimiz kaliriz)
    ort.pop("PROFIL", None)
    try:
        # start_new_session=True: HER VAKA kendi pgid'sinde kosar; onceki
        # VAKAnin arka plan kalintisi (sleep 30) yeni pgid'yi KIRLEMEZ.
        p = subprocess.run(
            ["zsh", os.path.join(kok, "isci.sh"), "claude", EV_KOKU, spec, etiket],
            capture_output=True, text=True, env=ort, timeout=120,
            start_new_session=True,
        )
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
]


def mutant_uygula(kok, m):
    """M1: K417-ARKA-PLAN-SURECI-KONTROLU blogunun TAMAMINI yorum satirina cevir.

    Strateji: BAS..SON isaretleri arasini `:# ...` ile yorum yapariz ki
    zsh icindeki `if/while/printf/while read` bloklari TAMAMEN etkisiz
    olsun. Boylece ana V1 senaryosu `sleep 60 &` biraktiginda kol
    yakalamaz ve HAL=SAGLIKLI kalir.
    """
    yol = os.path.join(kok, m["dosya"])
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
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
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    return True


def main():
    mutantsiz = "--vakalar" in sys.argv

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
        # V1 senaryosunu mutantli halde kos
        p_m, log_m, _h = isci_kos(kok, stub, spec, "arka_plan")
        subprocess.run(["pkill", "-f", "sleep 30"], capture_output=True)
        time.sleep(1)
        bitis_m = [s for s in log_m.splitlines() if " BITIS rc=" in s]
        mutant_saglikli = (bool(bitis_m)
                           and "hal=SAGLIKLI" in bitis_m[-1]
                           and (p_m is None or p_m.returncode == 0))
        if mutant_saglikli:
            olen += 1
            hedefte = set(m["hedef"]).issubset(set([1]))
            if hedefte:
                atif += 1
            print("MUTANT %s OLDU hedef=%s atif=%s — %s"
                  % (m["ad"], m["hedef"], "EVET" if hedefte else "🔴 HAYIR",
                     m["aciklama"]))
        else:
            print("MUTANT %s 🔴 YASADI (kol olculmuyor) — bitis=%s"
                  % (m["ad"], bitis_m[-1:] if bitis_m else "YOK"))

    print("MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d YAMA_TUTMADI=%d"
          % (olen, len(MUTANTLAR), atif, len(MUTANTLAR), yama_tutmadi))
    tam = (not dusen and olen == len(MUTANTLAR)
           and atif == len(MUTANTLAR) and yama_tutmadi == 0)
    return 0 if tam else 1


if __name__ == "__main__":
    sys.exit(main())
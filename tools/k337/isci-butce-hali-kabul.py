#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K337 — BUTCE TAVANI HAL YAMASI KABUL BATARYASI (28 Agu 2026).

🔴 CANLI DOSYADA MUTASYON YOK. Batarya, `~/.claude/cron/`daki kurulu
kopyalari GECICI bir sandbox'a kopyalar, yamayi ORAYA uygular ve olcumu
ORADAN yapar. Mutantlar da yalniz sandbox'ta yasar. Sandbox is bitince
SILINIR (Okan disk kurali; atexit + SIGTERM/SIGINT kancasi).

FIKSTUR: `PRUVO_ISCI_CLAUDE_BIN` ile CLI yerine bir SAHTE ikili konur.
Sahte ikili, gercek CLI'nin `--output-format json` zarfini uretir --
`subtype` alani K337_STUB_HAL ortam degiskeninden gelir. Boylece butce
kesintisi ISTENDIGI ANDA, para harcamadan, deterministik uretilir.

Kullanim:
    python3 tools/k337/isci-butce-hali-kabul.py            # tum batarya
    python3 tools/k337/isci-butce-hali-kabul.py --vakalar  # mutantsiz
Cikis: 0 = hepsi yesil · 1 = dusen var · 2 = arac hatasi.
"""

import atexit
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
CRON_KOKU = os.path.expanduser("~/.claude/cron")
EV_KOKU = os.path.abspath(os.path.join(BURASI, "..", ".."))

_SANDBOXLAR = []


def _temizle(*_a):
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


def yama_modulu():
    yol = os.path.join(BURASI, "isci-butce-hali-yama.py")
    spec = importlib.util.spec_from_file_location("k337_yama", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# SAHTE CLI (fikstur)
# --------------------------------------------------------------------------
STUB = r'''#!/usr/bin/env python3
import json, os, sys
hal = os.environ.get("K337_STUB_HAL", "saglikli")
argv = sys.argv[1:]
# Kapanis cagrisi (`-r <oturum>`) METIN kipindedir: zarf BASILMAZ.
if "-r" in argv:
    sys.stdout.write("kapanis cagrisi kostu\n")
    sys.exit(0)
if "--output-format" not in argv:
    sys.stdout.write("metin kipi\n")
    sys.exit(0)
if hal == "motor":
    # GERCEK motor arizasi: CLI olumcul hata bicimi + kota ifadesi.
    sys.stdout.write("API Error: 429 rate_limit_error\n")
    sys.exit(1)
if hal == "butce+kota":
    sys.stdout.write("API Error: 429 rate_limit_error\n")
    zarf = {"type": "result", "subtype": "error_max_budget_usd",
            "is_error": True, "result": "Error: Exceeded USD budget (10)",
            "total_cost_usd": 10.0, "num_turns": 42, "session_id": "s-butce-kota"}
    sys.stdout.write(json.dumps(zarf) + "\n")
    sys.exit(1)
if hal == "zarfsiz":
    sys.stdout.write("hicbir zarf yok, duz metin\n")
    sys.exit(1)
ZARFLAR = {
  "saglikli": {"subtype": "success", "is_error": False,
               "result": "IS BITTI", "total_cost_usd": 0.42, "num_turns": 7},
  "butce":    {"subtype": "error_max_budget_usd", "is_error": True,
               "result": "Error: Exceeded USD budget (10)",
               "total_cost_usd": 10.0, "num_turns": 118},
  "turtavani": {"subtype": "error_max_turns", "is_error": True,
                "result": "Error: Reached max turns (45)",
                "total_cost_usd": 3.1, "num_turns": 45},
  "icra":     {"subtype": "error_during_execution", "is_error": True,
               "result": "Execution error", "total_cost_usd": 1.0,
               "num_turns": 3},
  "yenihal":  {"subtype": "error_gelecekte_eklenen_hal", "is_error": True,
               "result": "bilinmeyen", "total_cost_usd": 0.5, "num_turns": 2},
}
z = dict(ZARFLAR.get(hal, ZARFLAR["saglikli"]))
z["type"] = "result"
z["session_id"] = "s-" + hal
sys.stdout.write(json.dumps(z) + "\n")
sys.exit(0 if z["subtype"] == "success" and not z["is_error"] else 1)
'''


def sandbox_kur(yama):
    kok = tempfile.mkdtemp(prefix="k337-kabul-%d-" % os.getpid())
    _SANDBOXLAR.append(kok)
    for ad in sorted(os.listdir(CRON_KOKU)):
        if ad.startswith("."):
            continue                      # sirlar ve durum dosyalari DISARIDA
        if not (ad.endswith(".py") or ad.endswith(".zsh") or ad.endswith(".sh")):
            continue
        kaynak = os.path.join(CRON_KOKU, ad)
        if os.path.isfile(kaynak):
            shutil.copy2(kaynak, os.path.join(kok, ad))
    # sabitler: CRON_KOKU sandbox'a cevrilir (canli log/karantina KIRLENMEZ)
    sab = os.path.join(kok, "isci-sabitler.zsh")
    with open(sab, encoding="utf-8") as f:
        metin = f.read()
    metin = metin.replace("CRON_KOKU=/Users/okan/.claude/cron",
                          "CRON_KOKU=%s" % kok)
    with open(sab, "w", encoding="utf-8") as f:
        f.write(metin)
    # sahte CLI
    stub = os.path.join(kok, "sahte-claude")
    with open(stub, "w", encoding="utf-8") as f:
        f.write(STUB)
    os.chmod(stub, 0o755)
    # spec
    spec = os.path.join(kok, "SPEC-kabul.md")
    with open(spec, "w", encoding="utf-8") as f:
        f.write("# K337 kabul fiksturu\nHicbir sey yapma.\n")
    # yama UYGULANIR
    degisen, hata = yama.uygula(kok, kuru=False)
    if hata:
        raise RuntimeError("sandbox yamasi dustu: %s" % hata)
    return kok, stub, spec


def isci_kos(kok, stub, spec, hal, etiket="kabul-k337"):
    ort = dict(os.environ)
    ort["PRUVO_ISCI_CLAUDE_BIN"] = stub
    ort["K337_STUB_HAL"] = hal
    ort["PRUVO_ISCI_BAGLAM"] = "kapali"
    p = subprocess.run(
        ["zsh", os.path.join(kok, "isci.sh"), "claude", EV_KOKU, spec, etiket],
        capture_output=True, text=True, env=ort, timeout=300,
    )
    log = os.path.join(kok, "isci.log")
    metin = ""
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    return p, metin


def karantina_kos(kok, rc, cikti_metni, motor, hal=None, dosya=None):
    """isci-karantina-karar.py'yi sandbox'ta kosar; (rc, stdout) doner."""
    cikti = os.path.join(kok, "kar-cikti.txt")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write(cikti_metni)
    kar = dosya or os.path.join(kok, ".motor-karantina")
    argv = [sys.executable, os.path.join(kok, "isci-karantina-karar.py"),
            str(rc), cikti, motor, kar, r"^(minimax-m3|kimi|claude)$"]
    if hal is not None:
        argv += ["--hal", hal]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return p.returncode, (p.stdout or "") + (p.stderr or ""), kar


def cozucu_kos(kok, girdi):
    hal_dosyasi = os.path.join(kok, "hal.txt")
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
def vakalari_kos(kok, stub, spec, gurultu=True):
    sonuc = []

    def v(no, ad, kol, gecti, kanit):
        sonuc.append({"no": no, "ad": ad, "kol": kol, "gecti": bool(gecti),
                      "kanit": str(kanit)[:400]})

    # --- Kol A: HAL jetonu -------------------------------------------------
    p_b, log_b = isci_kos(kok, stub, spec, "butce")
    v(1, "butce fiksturunde HAL=BUTCE_TAVANI basilir", "A",
      "TUR_HALI=BUTCE_TAVANI" in log_b,
      [s for s in log_b.splitlines() if s.startswith("TUR_HALI=")][-1:])
    bitis = [s for s in log_b.splitlines() if " BITIS rc=" in s]
    v(2, "BITIS satiri butce kesintisini sirаdan rc=1'den AYIRIR", "A",
      bool(bitis) and "hal=BUTCE_TAVANI" in bitis[-1], bitis[-1:])

    # --- Kol B: durma notu -------------------------------------------------
    notlar = []
    dizin = os.path.join(kok, "isci-tur-cikti")
    if os.path.isdir(dizin):
        notlar = [os.path.join(dizin, a) for a in os.listdir(dizin)
                  if a.endswith(".durma-notu.md")]
    baytlar = [os.path.getsize(n) for n in notlar]
    v(4, "butce kesintisinde DURMA NOTU dosyasi uretilir (bayt>0)", "B",
      len(notlar) == 1 and baytlar and baytlar[0] > 0,
      "adet=%d baytlar=%s" % (len(notlar), baytlar))
    v(5, "kapanis yordami butce kolunda ATESLENIR", "B",
      "KAPANIS_KOLU=BUTCE_TAVANI" in log_b
      and "KAPANIS_YORDAMI hal=BUTCE_TAVANI" in log_b,
      [s for s in log_b.splitlines() if s.startswith("KAPANIS")])

    with open(os.path.join(kok, "isci.sh"), encoding="utf-8") as f:
        isci_metni = f.read()
    notu_uret = isci_metni.count("isci-durma-notu.py")
    prompt = len(re.findall(r"^\s*KAPANIS_PROMPTU=", isci_metni, re.M))
    sebep = len(re.findall(r"^\s*KAPANIS_HALI=[A-Z]", isci_metni, re.M))
    v(6, "kapanis yordami TEK KOPYA (not=1, prompt=1, sebep atamasi=2)", "B",
      notu_uret == 1 and prompt == 1 and sebep == 2,
      "not_uretimi=%d prompt=%d sebep_atamasi=%d"
      % (notu_uret, prompt, sebep))

    v(7, "INGILIZCE dizge kolu SILINDI (ikinci kol birakilmadi)", "A",
      isci_metni.count("grep -Eq 'Exceeded USD budget'") == 0,
      "dizge_kolu=%d" % isci_metni.count("grep -Eq 'Exceeded USD budget'"))

    # --- Kontrol yonu: saglikli tur -----------------------------------------
    kok2, stub2, spec2 = sandbox_kur(vakalari_kos.yama)
    p_s, log_s = isci_kos(kok2, stub2, spec2, "saglikli")
    bitis_s = [s for s in log_s.splitlines() if " BITIS rc=" in s]
    v(3, "KONTROL: saglikli tur hal=SAGLIKLI, kapanis kolu ATESLENMEZ", "A",
      bool(bitis_s) and "hal=SAGLIKLI" in bitis_s[-1]
      and "KAPANIS_KOLU=yok" in log_s
      and "BUTCE_TAVANI" not in log_s,
      (bitis_s[-1:], [s for s in log_s.splitlines()
                      if s.startswith("KAPANIS_KOLU")]))

    # --- Kol C: karantina ---------------------------------------------------
    kar = os.path.join(kok, ".kar-butce")
    son = ""
    for _ in range(3):
        rc, son, _y = karantina_kos(kok, 1, "Error: Exceeded USD budget (10)\n",
                                    "minimax-m3", hal="BUTCE_TAVANI", dosya=kar)
    yazildi = os.path.isfile(kar) and "minimax-m3" in open(kar).read()
    v(8, "3 ardisik BUTCE kesintisi motoru KARANTINAYA SOKMAZ", "C",
      (not yazildi) and "butce_ardisik=3" in son and "ardisik=0" in son, son.strip())

    kar2 = os.path.join(kok, ".kar-motor")
    son2 = ""
    for _ in range(3):
        rc2, son2, _y = karantina_kos(kok, 1, "API Error: 429 rate_limit_error\n",
                                      "minimax-m3", hal="ICRA_HATASI", dosya=kar2)
    yazildi2 = os.path.isfile(kar2) and "minimax-m3" in open(kar2).read()
    v(9, "3 ardisik GERCEK motor hatasi KARANTINAYA SOKAR", "C",
      yazildi2, son2.strip())

    # sayac SIFIRLANMAZ: 2 gercek + 1 butce + 1 gercek => ardisik 3 => karantina
    kar3 = os.path.join(kok, ".kar-karisik")
    for _ in range(2):
        karantina_kos(kok, 1, "duz metin hata\n", "kimi",
                      hal="ICRA_HATASI", dosya=kar3)
    karantina_kos(kok, 1, "Error: Exceeded USD budget (10)\n", "kimi",
                  hal="BUTCE_TAVANI", dosya=kar3)
    rc3, son3, _y = karantina_kos(kok, 1, "duz metin hata\n", "kimi",
                                  hal="ICRA_HATASI", dosya=kar3)
    yazildi3 = os.path.isfile(kar3) and "kimi" in open(kar3).read()
    v(10, "butce kesintisi motor sayacini SIFIRLAMAZ (2+butce+1 => karantina)",
      "C", yazildi3 and "ardisik-basarisiz-imzasiz3" in son3, son3.strip())

    kar4 = os.path.join(kok, ".kar-eski")
    son4 = ""
    for _ in range(3):
        rc4, son4, _y = karantina_kos(kok, 1, "duz metin hata\n", "claude",
                                      hal=None, dosya=kar4)
    v(11, "GERIYE UYUM: --hal'siz eski cagri bicimi eski davranisi verir", "C",
      os.path.isfile(kar4) and "claude" in open(kar4).read(), son4.strip())

    kar5 = os.path.join(kok, ".kar-maske")
    son5 = ""
    for _ in range(1):
        rc5, son5, _y = karantina_kos(
            kok, 1, "API Error: 429 rate_limit_error\n", "minimax-m3",
            hal="BUTCE_TAVANI", dosya=kar5)
    v(15, "butce hali GERCEK kota imzasini MASKELEMEZ", "C",
      os.path.isfile(kar5) and "minimax-m3" in open(kar5).read(), son5.strip())

    # --- Cozucu: fail-closed ve metin korumasi ------------------------------
    _o, hal_dosya = cozucu_kos(kok, "hicbir zarf yok\n")
    v(12, "zarf YOKSA fail-closed HAL=OLCULEMEDI (saglikli UYDURULMAZ)", "A",
      "HAL=OLCULEMEDI" in hal_dosya, hal_dosya.strip())

    yeni = json.dumps({"type": "result", "subtype": "error_yeni_hal",
                       "is_error": True, "result": "x"})
    _o, hal_dosya = cozucu_kos(kok, yeni + "\n")
    v(13, "TANINMAYAN subtype sessizce SAGLIKLI sayilmaz", "A",
      "HAL=BILINMEYEN_HAL" in hal_dosya, hal_dosya.strip())

    # --- Idempotens + durum durustlugu (K320 sinifi) -----------------------
    isci_yolu = os.path.join(kok, "isci.sh")
    kar_yolu = os.path.join(kok, "isci-karantina-karar.py")
    with open(isci_yolu, "rb") as f:
        once_isci = f.read()
    with open(kar_yolu, "rb") as f:
        once_kar = f.read()
    vakalari_kos.yama.uygula(kok, kuru=False)      # IKINCI kez uygula
    with open(isci_yolu, "rb") as f:
        sonra_isci = f.read()
    with open(kar_yolu, "rb") as f:
        sonra_kar = f.read()
    esit, _ks = vakalari_kos.yama.kopya_durumu(kok)
    kurulu, eksik, _ys = vakalari_kos.yama.yama_durumu(kok)
    v(16, "IKINCI kosum BIREBIR ayni dosyayi birakir + --durum EKSIK=0", "A",
      once_isci == sonra_isci and once_kar == sonra_kar and eksik == 0
      and esit == len(vakalari_kos.yama.KOPYALANAN),
      "isci_esit=%s kar_esit=%s kurulu=%d eksik=%d kopya_esit=%d"
      % (once_isci == sonra_isci, once_kar == sonra_kar, kurulu, eksik, esit))

    metin_zarf = json.dumps({"type": "result", "subtype": "success",
                             "is_error": False, "result": "INSAN METNI 123",
                             "total_cost_usd": 1, "num_turns": 2})
    cikti, hal_dosya = cozucu_kos(
        kok, "stderr teshis satiri\n" + metin_zarf + "\n")
    v(14, "insan metni ve stderr teshisleri AYNEN korunur", "A",
      "INSAN METNI 123" in cikti and "stderr teshis satiri" in cikti,
      cikti.strip()[:200])

    return sorted(sonuc, key=lambda s: s["no"])


# --------------------------------------------------------------------------
# MUTANTLAR
# --------------------------------------------------------------------------
MUTANTLAR = [
    {"ad": "M1", "kol": "A", "dosya": "isci-hal-cozucu.py",
     "eski": '"error_max_budget_usd": "BUTCE_TAVANI",',
     "yeni": '"error_max_budget_usd": "SAGLIKLI",',
     "hedef": [1, 2],
     "aciklama": "HAL jetonu kolu kaldirilir (butce = saglikli sayilir)"},
    {"ad": "M2", "kol": "B", "dosya": "isci.sh",
     "eski": 'if [[ -z "$KAPANIS_HALI" && "$TUR_HALI" == BUTCE_TAVANI ]]; then',
     "yeni": 'if [[ -z "$KAPANIS_HALI" && "$TUR_HALI" == ASLA_OLMAZ ]]; then',
     "hedef": [4, 5],
     "aciklama": "durma notu kolu kaldirilir (butce kolu atesleMEZ)"},
    {"ad": "M3", "kol": "C", "dosya": "isci-karantina-karar.py",
     "eski": "    if hal == BUTCE_HALI and rc != 0 and not karar:",
     "yeni": "    if False and hal == BUTCE_HALI and rc != 0 and not karar:",
     "hedef": [8],
     "aciklama": "karantina ayrimi kaldirilir (butce yine ariza sayilir)"},
    {"ad": "M4", "kol": "C", "dosya": "isci-karantina-karar.py",
     "eski": "        _motor_ardisik = int(ardisik_oku(karantina_dosyasi).get(motor) or 0)",
     "yeni": "        _motor_ardisik = ardisik_guncelle(karantina_dosyasi, motor, False)",
     "hedef": [10],
     "aciklama": "butce kesintisi motor sayacini SIFIRLAR (gecmis dususler silinir)"},
    {"ad": "M5", "kol": "A", "dosya": "isci.sh",
     "eski": "BITIS rc=$CLAUDE_RC sure=$SURE hal=$TUR_HALI ===",
     "yeni": "BITIS rc=$CLAUDE_RC sure=$SURE ===",
     "hedef": [2],
     "aciklama": "BITIS satirindan hal jetonu kaldirilir"},
    {"ad": "M6", "kol": "A", "dosya": "isci-hal-cozucu.py",
     "eski": "    HAL_OLCULEMEDI = ",
     "yeni": "    HAL_OLCULEMEDI = ",
     "hedef": [], "kontrol": True,
     "aciklama": "KONTROL: yorum degisikligi — hicbir vaka DUSMEMELI"},
]


def mutant_uygula(kok, m):
    yol = os.path.join(kok, m["dosya"])
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    if m.get("kontrol"):
        yeni = metin.replace("# --- TEK KAYNAK: CLI subtype",
                             "# --- (kontrol mutanti) TEK KAYNAK: CLI subtype", 1)
        if yeni == metin:
            return False
        metin = yeni
    else:
        if metin.count(m["eski"]) != 1:
            return False
        metin = metin.replace(m["eski"], m["yeni"], 1)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return True


def main():
    mutantsiz = "--vakalar" in sys.argv
    yama = yama_modulu()
    vakalari_kos.yama = yama

    try:
        kok, stub, spec = sandbox_kur(yama)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("HATA: sandbox kurulamadi: %s\n" % e)
        return 2

    taban = vakalari_kos(kok, stub, spec)
    dusen = [s for s in taban if not s["gecti"]]
    for s in taban:
        print("VAKA %-2d kol=%-2s %s %s"
              % (s["no"], s["kol"], "YESIL" if s["gecti"] else "🔴 DUSTU",
                 s["ad"]))
        if not s["gecti"]:
            print("        kanit: %s" % s["kanit"])
    print("KABUL VAKA=%d/%d DUSEN=%d" % (len(taban) - len(dusen), len(taban),
                                         len(dusen)))
    if mutantsiz:
        return 0 if not dusen else 1
    if dusen:
        print("🔴 TABAN KIRMIZI — mutant kosumu ATLANDI (atif olculemez)")
        return 1

    olen = 0
    atif = 0
    yama_tutmadi = 0
    kontrol_yesil = 0
    for m in MUTANTLAR:
        try:
            m_kok, m_stub, m_spec = sandbox_kur(yama)
        except Exception as e:  # noqa: BLE001
            print("MUTANT %s SANDBOX_DUSTU %s" % (m["ad"], e))
            yama_tutmadi += 1
            continue
        if not mutant_uygula(m_kok, m):
            print("MUTANT %s YAMA_TUTMADI (capa bulunamadi) 🔴" % m["ad"])
            yama_tutmadi += 1
            continue
        sonuc = vakalari_kos(m_kok, m_stub, m_spec)
        m_dusen = sorted(s["no"] for s in sonuc if not s["gecti"])
        if m.get("kontrol"):
            if not m_dusen:
                kontrol_yesil += 1
                print("MUTANT %s KONTROL=YESIL (dusen kume bos) — %s"
                      % (m["ad"], m["aciklama"]))
            else:
                print("MUTANT %s KONTROL 🔴 dusen=%s — %s"
                      % (m["ad"], m_dusen, m["aciklama"]))
            continue
        if m_dusen:
            olen += 1
            hedefte = set(m["hedef"]).issubset(set(m_dusen))
            if hedefte:
                atif += 1
            print("MUTANT %s OLDU dusen=%s hedef=%s atif=%s — %s"
                  % (m["ad"], m_dusen, m["hedef"],
                     "EVET" if hedefte else "🔴 HAYIR", m["aciklama"]))
        else:
            print("MUTANT %s 🔴 YASADI (kol olculmuyor) — %s"
                  % (m["ad"], m["aciklama"]))

    oldurulecek = [m for m in MUTANTLAR if not m.get("kontrol")]
    kontroller = [m for m in MUTANTLAR if m.get("kontrol")]
    print("MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d KONTROL=%d/%d YAMA_TUTMADI=%d"
          % (olen, len(oldurulecek), atif, len(oldurulecek),
             kontrol_yesil, len(kontroller), yama_tutmadi))
    tam = (not dusen and olen == len(oldurulecek) and atif == len(oldurulecek)
           and kontrol_yesil == len(kontroller) and yama_tutmadi == 0)
    return 0 if tam else 1


if __name__ == "__main__":
    sys.exit(main())

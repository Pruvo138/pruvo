#!/usr/bin/env python3
"""claude-api motoru kabul testi (10 Eki 2026 — tarif-rutin-api §1).

`~/.claude/cron/isci.sh` + `isci-motor-uc.zsh` ciftinin `claude-api` kolunu
IZOLE bir CRON_KOKU'da, SAHTE `claude` ikilisi ve YEREL HTTP fiksturuyle
(127.0.0.1; ag YOK) kosarak olcer. Gercek anahtar dosyasi OKUNMAZ: uc dosyasinin
izole kopyasinda anahtar yolu gecici dosyaya, uc adresi fiksture CIVILENIR.

VAKALAR
  anahtar-yok     dosya yok             -> rc=1 HAL=MOTOR-YOK, claude cagrilmaz
  izin-644        dosya 644             -> rc=1 HAL=ANAHTAR-IZIN, claude cagrilmaz
  sahte-anahtar   600 + ANTHROPIC_API_KEY=<sahte>
                  -> rc=0; komut ortaminda anahtar VAR, argv (claude + ebeveyn)
                     ve kok agacinda/tur ciktisinda/stdout'ta deger 0; fikstur
                     anahtari ALDI; model Haiku; log'da MOTOR= MODEL= USD= GUN= AY=
  ham-bicim       600 + tek ham satir   -> rc=0, anahtar ortamda
  butce-kirpma    gun=4,00              -> --max-budget-usd 1.00
  gun-tavani      gun=5,00              -> rc=1 HAL=TAVAN, claude cagrilmaz
  ay-tavani       ay=150,00             -> rc=1 HAL=TAVAN, claude cagrilmaz
  sonnet-basligi  [MOTOR: claude-api:sonnet] -> model BIREBIR MODEL_SONNET
  gecersiz-model  [MOTOR: claude-api:opus]   -> rc=2, claude cagrilmaz
KREDI-BITTI KOLU (12 Eki 2026 — BaBa 13:2x F; vaka adlari V1..V7 spec'teki sira)
  V1 motor-yok-temiz     dosya yok   -> rc=1, TEK HAL=MOTOR-YOK satiri, sayac YOK
  V2 motor-yok-sifir     0 bayt 600  -> ayni
  V3 kredi-bitti         uc 400 "credit balance is too low" -> rc=1, TEK
                         HAL=KREDI-BITTI satiri, isaret 600, KUTU_SATIRI stderr,
                         claude TEK kez (tekrar YOK)
  V4 kredi-isaret-var    V3'ten sonra ikinci cagri -> rc=1 sebep=isaret-var,
                         sahte claude IKINCI KEZ CAGRILMADI
  V5 kredi-basarili      200 -> rc=0, isaret OLUSMAZ
  V5b kredi-metinde-imza basarili tur sonuc METNINDE imza -> isaret OLUSMAZ
  V6 kredi-sizinti       V3 senaryosu: sahte anahtar log/stderr/kok grep = 0
  V7 m3-regresyon        isaret VARKEN minimax-m3: rc=0, model/taban/varsayilan
                         modeller/sikistirma penceresi + argv iskeleti BIREBIR
  (model kimligi onekle DEGIL birebir olculur: 10 Eki isci tarifteki kimligi
   eski Haiku + var olmayan `claude-sonnet-5` ile degistirmisti, onek testi
   ikisini de GECIRIYORDU.)
MUTANTLAR (izole kopyaya uygulanir; her biri en az 1 vakayi KIRMIZI yakmali)
  izin-kontrolu-kalkar  -> izin-644 KIRMIZI
  tavan-kontrolu-kalkar -> gun-tavani KIRMIZI
  deger-loga-sizar      -> sahte-anahtar KIRMIZI
  haiku-kimligi-eskir   -> sahte-anahtar KIRMIZI
  sonnet-kimligi-eskir  -> sonnet-basligi KIRMIZI
  M1 kredi-imzasi-kalkar   -> kredi-bitti KIRMIZI
  M2 isaret-onkontrolu-kalkar -> kredi-isaret-var KIRMIZI
  M3 claudea-dusus-eklenir -> kredi-isaret-var KIRMIZI (YEDEK YOK, Okan 6 Eyl)

ON KOSUL: canli isci hatti (`~/.claude/cron`) CI kosucusunda YOKTUR -> ONKOSUL_YOK
+ KABUL=OLCULEMEDI, rc=3 (yesil DEMEZ). Hukum YEREL kosumda okunur; muafiyet
gerekcesi `tools/ci-kapsam-test.py` IZIN_LISTESI'nde.

Kullanim: python3 tools/claude-api-motor-test.py [--isci <isci.sh>] [--uc <isci-motor-uc.zsh>]
(varsayilan: canli dosyalar; atomik degisimden ONCE aday kopyaya karsi kosulur).
"""
import argparse
import datetime
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

GERCEK_CRON = "/Users/okan/.claude/cron"
GERCEK_ANAHTAR = "/Users/okan/.config/pruvo/anthropic-isci.env"
GERCEK_UC_URL = "https://api.anthropic.com"
MOTOR = "claude-api"
SAHTE_DEGER = "sk-ant-TEST-SAHTE-0000"
SAHTE_OZET = hashlib.sha256(SAHTE_DEGER.encode()).hexdigest()
SAYAC_ADI = ".claude-api-sayac.json"
ISARET_ADI = ".claude-api-kredi-bitti"
M3_DEGER = "mm-TEST-SAHTE-M3-0000"
M3_MODEL = "MiniMax-M3[1m]"
M3_TABAN = "https://api.minimax.io/anthropic"
# m3 kolunun komut satiri iskeleti (oturum kimligi degeri haric) — 12 Eki
# degisiminden ONCEKI govdeye karsi olculdu; birebir korunur (V7).
M3_ARGV = ["-p", "--permission-mode", "bypassPermissions", "--output-format", "json",
           "--session-id", "<uuid>"]
KREDI_GOVDE = json.dumps({"type": "error", "error": {
    "type": "invalid_request_error",
    "message": "Your credit balance is too low to access the Anthropic API. "
               "Please go to Plans & Billing to upgrade or purchase credits."}})
MODEL_HAIKU = "claude-haiku-5-5"
MODEL_SONNET = "claude-sonnet-5-5"

# Izole kokte BAGLANMAYANLAR: yeniden yazilan govde + kosumun YAZDIGI durum
# dosyalari (gercek log/karantina/sayac/tur ciktisi KIRLETILMEZ).
YAZILAN = {"isci.sh", "isci-sabitler.zsh", "isci-motor-uc.zsh", "isci.log",
           "isci-tur-cikti", "isci-onerileri.md", ".motor-karantina",
           "isci-karantina.log", "baglam-olcum.tsv", ".minimax-anahtar",
           SAYAC_ADI, ".ci-token", ".claude-api-kredi-bitti"}
ONEKLER = ("profil-", ".isci-", ".bekci-", "isci.log.")

# Mutant capalari: capa tutmazsa hukum VERILMEZ (fail-closed).
MUTANTLAR = {
    "izin-kontrolu-kalkar": ("uc",
        ' || "$izin" != "600:$(id -un)" ]]', " ]]", "izin-644"),
    "tavan-kontrolu-kalkar": ("isci",
        "      motor_tavan_kontrol\n", "      :\n", "gun-tavani"),
    "deger-loga-sizar": ("uc",
        "    API_KEY=${deger:-$ham}\n",
        '    API_KEY=${deger:-$ham}\n    echo "ANAHTAR=$API_KEY" >> "$LOG"\n',
        "sahte-anahtar"),
    "haiku-kimligi-eskir": ("uc",
        "MOTOR_MODEL[claude-api]=" + MODEL_HAIKU + "\n",
        "MOTOR_MODEL[claude-api]=claude-haiku-4-5-20251001\n", "sahte-anahtar"),
    "sonnet-kimligi-eskir": ("uc",
        "sonnet " + MODEL_SONNET + ")", "sonnet claude-sonnet-5)", "sonnet-basligi"),
    # --- KREDI-BITTI kolu (M1..M3) ---
    "kredi-imzasi-kalkar": ("uc",
        "    if print -r -- \"$metin\" | grep -Eiq -- \"$CLAUDE_API_KREDI_IMZA\"; then\n",
        "    if false; then\n", "kredi-bitti"),
    "isaret-onkontrolu-kalkar": ("uc",
        '  if [[ -e "$CLAUDE_API_ISARET" || -L "$CLAUDE_API_ISARET" ]]; then\n',
        "  if false; then\n", "kredi-isaret-var"),
    "claudea-dusus-eklenir": ("uc",
        "    exit 1   # KREDI-BITTI: isaret var, YEDEK YOK\n",
        "    BASE_URL=; ISTENEN_MOTOR=claude; LOG_MOTOR=claude\n", "kredi-isaret-var"),
}
KREDI_MUTANTLARI = ("kredi-imzasi-kalkar", "isaret-onkontrolu-kalkar", "claudea-dusus-eklenir")

SAHTE_CLAUDE = r'''#!/usr/bin/env python3
# Sahte claude: GERCEK API CAGRISI YAPMAZ; yerel fiksture tek istek atar.
import hashlib, json, os, subprocess, sys, urllib.error, urllib.request
OZET = "%(ozet)s"
anahtar = os.environ.get("ANTHROPIC_API_KEY", "")
argvler = [" ".join(sys.argv)]
try:
    argvler.append(subprocess.run(["ps", "-o", "args=", "-p", str(os.getppid())],
                                  capture_output=True, text=True).stdout)
except Exception:
    pass
kayit = {
    "anahtar_ortamda": hashlib.sha256(anahtar.encode()).hexdigest() == OZET,
    "argv_temiz": all("TEST-SAHTE" not in a for a in argvler),
    "model": os.environ.get("ANTHROPIC_MODEL", ""),
    "taban": os.environ.get("ANTHROPIC_BASE_URL", ""),
    "argv": [a for a in sys.argv[1:] if not a.startswith("ISCI BAGLAMI")][-12:],
    "varsayilan": [os.environ.get("ANTHROPIC_DEFAULT_%%s_MODEL" %% k, "")
                   for k in ("SONNET", "OPUS", "HAIKU")],
    "pencere": os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW", ""),
    "m3_anahtar": os.environ.get("ANTHROPIC_API_KEY", "") == "%(m3)s",
    "uc_durum": None,
}
hata_govde = None
# Ag YOK: yalniz yerel fikstur cagrilir (m3/dogal kolun gercek ucu ARANMAZ).
if not kayit["taban"].startswith("http://127.0.0.1:"):
    kayit["uc_durum"] = "ATLANDI"
else:
  try:
    istek = urllib.request.Request(
        kayit["taban"] + "/v1/messages", method="POST",
        data=json.dumps({"model": kayit["model"], "max_tokens": 8,
                         "messages": [{"role": "user", "content": "x"}]}).encode(),
        headers={"x-api-key": anahtar, "content-type": "application/json",
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(istek, timeout=10) as y:
        kayit["uc_durum"] = y.status
  except urllib.error.HTTPError as e:
    kayit["uc_durum"] = e.code
    hata_govde = e.read().decode("utf-8", "replace")
  except Exception as e:
    kayit["uc_durum"] = "HATA:" + type(e).__name__
with open("%(yakala)s", "a") as f:
    f.write(json.dumps(kayit) + "\n")
if hata_govde is not None:
    # CLI'nin 4xx bicimi: stderr'de `API Error: <kod> <govde>`, zarf is_error.
    sys.stderr.write("API Error: %%s %%s\n" %% (kayit["uc_durum"], hata_govde))
    print(json.dumps({"type": "result", "subtype": "success", "is_error": True,
                      "total_cost_usd": 0, "num_turns": 1,
                      "result": "Credit balance is too low", "session_id": "sahte"}))
    sys.exit(1)
print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                  "total_cost_usd": 0.0123, "num_turns": 1,
                  "result": os.environ.get("SAHTE_SONUC_METNI", "ok"),
                  "session_id": "sahte"}))
'''


class Fikstur(http.server.BaseHTTPRequestHandler):
    """Yerel Messages ucu: anahtari DEGERIYLE degil OZETIYLE kaydeder."""
    kayitlar = []
    durum = 200

    def do_POST(self):
        uzunluk = int(self.headers.get("content-length") or 0)
        govde = self.rfile.read(uzunluk)
        try:
            model = json.loads(govde).get("model")
        except Exception:
            model = None
        anahtar = self.headers.get("x-api-key") or ""
        Fikstur.kayitlar.append({
            "yol": self.path, "model": model,
            "anahtar_dogru": hashlib.sha256(anahtar.encode()).hexdigest() == SAHTE_OZET})
        yanit = json.dumps({"type": "message", "content": [],
                            "usage": {"input_tokens": 1, "output_tokens": 1}}).encode()
        if Fikstur.durum != 200:
            yanit = KREDI_GOVDE.encode()
        self.send_response(Fikstur.durum)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(yanit)))
        self.end_headers()
        self.wfile.write(yanit)

    def log_message(self, *a):
        pass


def izole_kur(tmp, isci_kaynak, uc_kaynak, uc_url, mutant=None):
    kok = os.path.join(tmp, "cron")
    os.makedirs(kok)
    for ad in os.listdir(GERCEK_CRON):
        if ad in YAZILAN or ad.startswith(ONEKLER) or ".yedek-" in ad:
            continue
        try:
            os.symlink(os.path.join(GERCEK_CRON, ad), os.path.join(kok, ad))
        except OSError:
            pass
    with open(os.path.join(GERCEK_CRON, "isci-sabitler.zsh"), encoding="utf-8") as f:
        sabit = f.read()
    civili = sabit.replace("CRON_KOKU=" + GERCEK_CRON, "CRON_KOKU=" + kok, 1)
    if civili == sabit:
        return None, "SABITLER_CAPASI_TUTMADI"
    with open(os.path.join(kok, "isci-sabitler.zsh"), "w", encoding="utf-8") as f:
        f.write(civili)

    with open(isci_kaynak, encoding="utf-8") as f:
        isci = f.read()
    with open(uc_kaynak, encoding="utf-8") as f:
        uc = f.read()
    anahtar_yolu = os.path.join(tmp, "anahtar.env")
    for capa in (GERCEK_ANAHTAR, GERCEK_UC_URL):
        if uc.count(capa) != 1:
            return None, "UC_CAPASI_TUTMADI:" + capa
    uc = uc.replace(GERCEK_ANAHTAR, anahtar_yolu).replace(GERCEK_UC_URL, uc_url)
    if mutant:
        hedef, eski, yeni, _ = MUTANTLAR[mutant]
        metin = isci if hedef == "isci" else uc
        if metin.count(eski) != 1:
            return None, "MUTANT_CAPASI_TUTMADI:" + mutant
        metin = metin.replace(eski, yeni, 1)
        if hedef == "isci":
            isci = metin
        else:
            uc = metin
    with open(os.path.join(kok, "isci.sh"), "w", encoding="utf-8") as f:
        f.write(isci)
    os.chmod(os.path.join(kok, "isci.sh"), 0o755)
    with open(os.path.join(kok, "isci-motor-uc.zsh"), "w", encoding="utf-8") as f:
        f.write(uc)
    os.chmod(os.path.join(kok, "isci-motor-uc.zsh"), 0o600)
    open(os.path.join(kok, "isci.log"), "w").close()
    os.makedirs(os.path.join(kok, "isci-tur-cikti"))
    return kok, None


def anahtar_yaz(tmp, icerik, izin):
    yol = os.path.join(tmp, "anahtar.env")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)
    os.chmod(yol, izin)


def sayac_yaz(kok, gun_usd, ay_usd):
    simdi = datetime.datetime.now()
    veri = {"gun": {simdi.strftime("%Y-%m-%d"): gun_usd},
            "ay": {simdi.strftime("%Y-%m"): ay_usd}, "son": []}
    yol = os.path.join(kok, SAYAC_ADI)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f)
    os.chmod(yol, 0o600)


def kos(tmp, kok, baslik, motor=MOTOR, ek_ortam=None):
    yakala = os.path.join(tmp, "claude-cagrildi.jsonl")
    sahte = os.path.join(tmp, "claude")
    with open(sahte, "w", encoding="utf-8") as f:
        f.write(SAHTE_CLAUDE % {"ozet": SAHTE_OZET, "yakala": yakala, "m3": M3_DEGER})
    os.chmod(sahte, 0o755)
    ev = os.path.join(tmp, "ev")
    os.makedirs(ev, exist_ok=True)
    spec = os.path.join(tmp, "spec.md")
    with open(spec, "w", encoding="utf-8") as f:
        f.write(baslik + "# GECICI TEST SPEC — is YAPMAZ (claude-api-motor-test)\n")
    tur = os.path.join(tmp, "tur-cikti.log")
    ortam = dict(os.environ)
    for ad in ("ANTHROPIC_API_KEY", "PRUVO_CLAUDE_ISCI_IZNI", "PRUVO_ISCI_BUTCE_USD"):
        ortam.pop(ad, None)
    ortam["PRUVO_ISCI_CLAUDE_BIN"] = sahte
    ortam["PRUVO_ISCI_TUR_CIKTI"] = tur
    ortam.pop("SAHTE_SONUC_METNI", None)
    ortam.update(ek_ortam or {})
    p = subprocess.run([os.path.join(kok, "isci.sh"), motor, ev, spec, "kabul-claude-api"],
                       capture_output=True, text=True, env=ortam, timeout=300)
    kayit = []
    if os.path.exists(yakala):
        with open(yakala, encoding="utf-8") as f:
            kayit = [json.loads(s) for s in f if s.strip()]
    with open(os.path.join(kok, "isci.log"), encoding="utf-8", errors="replace") as f:
        log = f.read()
    return {"rc": p.returncode, "cikti": (p.stdout or "") + (p.stderr or ""),
            "log": log, "claude": kayit, "tur": tur}


def sizinti_say(kok, ek_yollar, ek_metin):
    """Kok agacindaki (sembolik baglar HARIC) + ek dosyalardaki sahte deger sayisi."""
    say = ek_metin.count(SAHTE_DEGER)
    yollar = list(ek_yollar)
    for dizin, _, dosyalar in os.walk(kok, followlinks=False):
        yollar += [os.path.join(dizin, d) for d in dosyalar]
    for yol in yollar:
        if os.path.islink(yol) or not os.path.isfile(yol):
            continue
        try:
            with open(yol, "rb") as f:
                say += f.read().count(SAHTE_DEGER.encode())
        except OSError:
            pass
    return say


def durdu(s, hal):
    """Kapi kolu: rc=1 + HAL basildi + claude CAGRILMADI."""
    return (s["rc"] == 1 and ("HAL=" + hal) in s["log"] and not s["claude"],
            "rc=%d hal=%s claude_cagri=%d" % (s["rc"], ("HAL=" + hal) in s["log"], len(s["claude"])))


def vaka_kos(ad, isci_kaynak, uc_kaynak, uc_url, mutant=None):
    tmp = tempfile.mkdtemp(prefix="claude-api-test-")
    try:
        kok, hata = izole_kur(tmp, isci_kaynak, uc_kaynak, uc_url, mutant)
        if hata:
            return None, hata
        if ad in KREDI_VAKALARI:
            return kredi_vaka(ad, tmp, kok)
        tam = "ANTHROPIC_API_KEY=" + SAHTE_DEGER + "\n"
        baslik = ""
        if ad == "izin-644":
            anahtar_yaz(tmp, tam, 0o644)
        elif ad == "ham-bicim":
            anahtar_yaz(tmp, "# yorum\n" + SAHTE_DEGER + "\n", 0o600)
        elif ad != "anahtar-yok":
            anahtar_yaz(tmp, tam, 0o600)
        if ad == "gun-tavani":
            sayac_yaz(kok, 5.00, 5.00)
        elif ad == "ay-tavani":
            sayac_yaz(kok, 0.0, 150.00)
        elif ad == "butce-kirpma":
            sayac_yaz(kok, 4.00, 4.00)
        if ad == "sonnet-basligi":
            baslik = "[MOTOR: claude-api:sonnet]\n"
        elif ad == "gecersiz-model":
            baslik = "[MOTOR: claude-api:opus]\n"
        Fikstur.kayitlar = []
        s = kos(tmp, kok, baslik)
        c = s["claude"][0] if s["claude"] else {}

        if ad == "anahtar-yok":
            return durdu(s, "MOTOR-YOK")
        if ad == "izin-644":
            return durdu(s, "ANAHTAR-IZIN")
        if ad in ("gun-tavani", "ay-tavani"):
            return durdu(s, "TAVAN")
        if ad == "gecersiz-model":
            ok = s["rc"] == 2 and not s["claude"] and "HAL=MODEL-GECERSIZ" in s["log"]
            return ok, "rc=%d claude_cagri=%d" % (s["rc"], len(s["claude"]))
        if ad == "sonnet-basligi":
            ok = s["rc"] == 0 and c.get("model") == MODEL_SONNET
            return ok, "rc=%d model=%s" % (s["rc"], c.get("model"))
        if ad == "ham-bicim":
            ok = s["rc"] == 0 and c.get("anahtar_ortamda") is True
            return ok, "rc=%d anahtar_ortamda=%s" % (s["rc"], c.get("anahtar_ortamda"))
        if ad == "butce-kirpma":
            argv = c.get("argv", [])
            i = argv.index("--max-budget-usd") if "--max-budget-usd" in argv else -1
            butce = argv[i + 1] if 0 <= i < len(argv) - 1 else None
            return (s["rc"] == 0 and butce == "1.00"), "rc=%d butce=%s" % (s["rc"], butce)
        if ad == "sahte-anahtar":
            siz = sizinti_say(kok, [s["tur"]], s["cikti"])
            fik = Fikstur.kayitlar[0] if Fikstur.kayitlar else {}
            sayac = {}
            yol = os.path.join(kok, SAYAC_ADI)
            if os.path.exists(yol):
                with open(yol, encoding="utf-8") as f:
                    sayac = json.load(f)
            gun = sayac.get("gun", {}).get(datetime.datetime.now().strftime("%Y-%m-%d"))
            log_satiri = any(l.startswith("MOTOR=claude-api MODEL=" + MODEL_HAIKU + " ")
                             and " USD=0.0123 GUN=0.0123 AY=0.0123 " in l
                             for l in s["log"].splitlines())
            ok = (s["rc"] == 0 and c.get("anahtar_ortamda") is True
                  and c.get("argv_temiz") is True and c.get("uc_durum") == 200
                  and fik.get("anahtar_dogru") is True and fik.get("yol") == "/v1/messages"
                  and c.get("model") == MODEL_HAIKU
                  and siz == 0 and gun == 0.0123 and log_satiri)
            return ok, ("rc=%d anahtar_ortamda=%s argv_temiz=%s fikstur_anahtar=%s "
                        "model=%s sahte_deger_grep=%d sayac_gun=%s log_satiri=%s"
                        % (s["rc"], c.get("anahtar_ortamda"), c.get("argv_temiz"),
                           fik.get("anahtar_dogru"), c.get("model"), siz, gun, log_satiri))
        return None, "BILINMEYEN_VAKA"
    finally:
        guvenli_sil(tmp)


def hal_satirlari(log, hal):
    return [l for l in log.splitlines() if ("HAL=" + hal + " ") in l]


def isaret_durumu(kok):
    """(var_mi, izin_sekizli|None) — isaret dosyasi sembolik bag DEGIL."""
    yol = os.path.join(kok, ISARET_ADI)
    if not os.path.lexists(yol):
        return False, None
    return True, oct(os.lstat(yol).st_mode & 0o777)


def kredi_vaka(ad, tmp, kok):
    tam = "ANTHROPIC_API_KEY=" + SAHTE_DEGER + "\n"
    sayac_yolu = os.path.join(kok, SAYAC_ADI)
    if ad in ("motor-yok-temiz", "motor-yok-sifir"):
        if ad == "motor-yok-sifir":
            anahtar_yaz(tmp, "", 0o600)
        s = kos(tmp, kok, "")
        satir = hal_satirlari(s["log"], "MOTOR-YOK")
        sayac_var = os.path.exists(sayac_yolu)
        isaret, _ = isaret_durumu(kok)
        ok = (s["rc"] == 1 and len(satir) == 1 and not s["claude"]
              and not sayac_var and not isaret and "KREDI-BITTI" not in s["log"])
        return ok, "rc=%d motor_yok_satiri=%d claude_cagri=%d sayac_dosyasi=%s isaret=%s" % (
            s["rc"], len(satir), len(s["claude"]), sayac_var, isaret)

    if ad == "m3-regresyon":
        with open(os.path.join(kok, ".minimax-anahtar"), "w", encoding="utf-8") as f:
            f.write(M3_DEGER + "\n")
        os.chmod(os.path.join(kok, ".minimax-anahtar"), 0o600)
        with open(os.path.join(kok, ISARET_ADI), "w", encoding="utf-8") as f:
            f.write("2026-10-12T00:00:00Z\n")
        os.chmod(os.path.join(kok, ISARET_ADI), 0o600)
        s = kos(tmp, kok, "", motor="minimax-m3")
        c = s["claude"][0] if s["claude"] else {}
        argv = list(c.get("argv", []))
        if "--session-id" in argv and argv.index("--session-id") + 1 < len(argv):
            argv[argv.index("--session-id") + 1] = "<uuid>"
        ok = (s["rc"] == 0 and len(s["claude"]) == 1 and c.get("model") == M3_MODEL
              and c.get("taban") == M3_TABAN and c.get("varsayilan") == [M3_MODEL] * 3
              and c.get("pencere") == "1000000" and c.get("m3_anahtar") is True
              and argv == M3_ARGV and "KREDI-BITTI" not in s["log"]
              and "KUTU_SATIRI" not in s["cikti"])
        return ok, "rc=%d claude_cagri=%d model=%s taban=%s varsayilan=%s pencere=%s argv=%s" % (
            s["rc"], len(s["claude"]), c.get("model"), c.get("taban"),
            c.get("varsayilan"), c.get("pencere"), argv)

    anahtar_yaz(tmp, tam, 0o600)
    if ad in ("kredi-bitti", "kredi-sizinti", "kredi-isaret-var"):
        Fikstur.durum = 400
        try:
            s = kos(tmp, kok, "")
        finally:
            Fikstur.durum = 200
        satir = hal_satirlari(s["log"], "KREDI-BITTI")
        isaret, izin = isaret_durumu(kok)
        kutu = [l for l in s["cikti"].splitlines() if l.startswith("KUTU_SATIRI: claude-api KREDI-BITTI ")]
        if ad == "kredi-sizinti":
            siz = sizinti_say(kok, [s["tur"]], s["cikti"])
            return (siz == 0 and len(satir) == 1), "sahte_deger_grep=%d kredi_satiri=%d" % (siz, len(satir))
        ilk = (s["rc"] == 1 and len(satir) == 1 and " rc=1" in satir[0]
               and " motor=claude-api " in satir[0] and " etiket=kabul-claude-api " in satir[0]
               and isaret and izin == "0o600" and len(kutu) == 1 and len(s["claude"]) == 1
               and s["claude"][0].get("uc_durum") == 400 and "TEKRAR 1/1" not in s["log"])
        tur_hali = [l[len("TUR_HALI="):] for l in s["log"].splitlines() if l.startswith("TUR_HALI=")]
        detay = ("rc=%d kredi_satiri=%d isaret=%s izin=%s kutu_satiri=%d claude_cagri=%d "
                 "tekrar=%s tur_hali=%s" % (
                     s["rc"], len(satir), isaret, izin, len(kutu), len(s["claude"]),
                     "TEKRAR 1/1" in s["log"], ",".join(tur_hali) or "yok"))
        if ad == "kredi-bitti":
            return ilk, detay
        if not ilk:
            # On kosul (V3 senaryosu) tutmadi: isaret elle konur ki V4 YALNIZ
            # on-kontrolu olcsun (V3 kirmizisi V4'u maskelemesin).
            with open(os.path.join(kok, ISARET_ADI), "w", encoding="utf-8") as f:
                f.write("2026-10-12T00:00:00Z\n")
            os.chmod(os.path.join(kok, ISARET_ADI), 0o600)
        once = len(s["claude"])
        s2 = kos(tmp, kok, "")
        satir2 = hal_satirlari(s2["log"], "KREDI-BITTI")
        isaret_satiri = [l for l in satir2 if " sebep=isaret-var " in l]
        ok = (s2["rc"] == 1 and len(s2["claude"]) == once and len(isaret_satiri) == 1
              and os.path.exists(os.path.join(kok, ISARET_ADI)))
        return ok, "ikinci_rc=%d isaret_var_satiri=%d sahte_claude_ikinci_cagri=%d" % (
            s2["rc"], len(isaret_satiri), len(s2["claude"]) - once)

    if ad in ("kredi-basarili", "kredi-metinde-imza"):
        ek = None
        if ad == "kredi-metinde-imza":
            ek = {"SAHTE_SONUC_METNI": "Rapor: credit balance is too low / billing 402 "
                                       "invalid_request_error vakasi olculdu."}
        s = kos(tmp, kok, "", ek_ortam=ek)
        isaret, _ = isaret_durumu(kok)
        ok = (s["rc"] == 0 and not isaret and "KREDI-BITTI" not in s["log"]
              and "KUTU_SATIRI" not in s["cikti"] and len(s["claude"]) == 1)
        return ok, "rc=%d isaret=%s claude_cagri=%d" % (s["rc"], isaret, len(s["claude"]))
    return None, "BILINMEYEN_VAKA"


def guvenli_sil(yol):
    gercek = os.path.realpath(yol)
    if not os.path.basename(gercek).startswith("claude-api-test-"):
        print("TEMIZLIK_ATLANDI: " + gercek)
        return
    for korunan in (GERCEK_CRON, os.path.expanduser("~/dev")):
        if gercek == korunan or gercek.startswith(korunan + os.sep):
            print("TEMIZLIK_ATLANDI: korunan " + gercek)
            return
    shutil.rmtree(gercek, ignore_errors=True)


VAKALAR = ("anahtar-yok", "izin-644", "sahte-anahtar", "ham-bicim", "butce-kirpma",
           "gun-tavani", "ay-tavani", "sonnet-basligi", "gecersiz-model")
KREDI_VAKALARI = ("motor-yok-temiz", "motor-yok-sifir", "kredi-bitti", "kredi-isaret-var",
                  "kredi-basarili", "kredi-metinde-imza", "kredi-sizinti", "m3-regresyon")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--isci", default=os.path.join(GERCEK_CRON, "isci.sh"))
    ap.add_argument("--uc", default=os.path.join(GERCEK_CRON, "isci-motor-uc.zsh"))
    ap.add_argument("--vaka", action="append", default=[],
                    help="yalniz bu vaka(lar) — teshis; KABUL hukmu VERILMEZ")
    a = ap.parse_args()
    if not os.path.isdir(GERCEK_CRON) or not os.path.isfile(a.isci):
        print("ONKOSUL_YOK: canli isci hatti yok (" + GERCEK_CRON + ")")
        print("KABUL=OLCULEMEDI (0 vaka) — bu kapi YEREL kosulur, CI'da DEGIL")
        return 3

    sunucu = http.server.HTTPServer(("127.0.0.1", 0), Fikstur)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    uc_url = "http://127.0.0.1:%d" % sunucu.server_address[1]
    vaka_sonuc, mutant_sonuc = [], []
    if a.vaka:
        try:
            for ad in a.vaka:
                gecti, detay = vaka_kos(ad, a.isci, a.uc, uc_url)
                print("VAKA=%s %s SONUC=%s" % (ad, detay, "GECTI" if gecti else "KALDI"))
        finally:
            sunucu.shutdown()
        print("KABUL=HUKUMSUZ (--vaka teshis kosumu)")
        return 4
    try:
        for ad in VAKALAR + KREDI_VAKALARI:
            gecti, detay = vaka_kos(ad, a.isci, a.uc, uc_url)
            vaka_sonuc.append(gecti is True)
            print("VAKA=%s %s SONUC=%s" % (ad, detay, "GECTI" if gecti else "KALDI"))
        for mutant, (_, _, _, hedef_vaka) in MUTANTLAR.items():
            gecti, detay = vaka_kos(hedef_vaka, a.isci, a.uc, uc_url, mutant)
            # Mutant OLDU = hedef vaka KIRMIZI (gecti False). None = capa
            # tutmadi -> hukum yok, KALDI sayilir.
            oldu = gecti is False
            mutant_sonuc.append(oldu)
            print("MUTANT=%s hedef=%s %s SONUC=%s" % (
                mutant, hedef_vaka, detay, "OLDU" if oldu else "YASADI"))
    finally:
        sunucu.shutdown()
    hukum = "GECTI" if all(vaka_sonuc) and all(mutant_sonuc) else "KALDI"
    k_vaka = vaka_sonuc[len(VAKALAR):]
    k_mutant = [m for ad, m in zip(MUTANTLAR, mutant_sonuc) if ad in KREDI_MUTANTLARI]
    print("KREDI-BITTI VAKA=%d/%d MUTANT=%d/%d" % (
        sum(k_vaka), len(k_vaka), sum(k_mutant), len(k_mutant)))
    print("KABUL=%s VAKA=%d/%d MUTANT=%d/%d (%d/%d vaka, %d/%d mutant oldu)" % (
        hukum, sum(vaka_sonuc), len(vaka_sonuc), sum(mutant_sonuc), len(mutant_sonuc),
        sum(vaka_sonuc), len(vaka_sonuc), sum(mutant_sonuc), len(mutant_sonuc)))
    return 0 if hukum == "GECTI" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""EMEKLI ISCI MOTORUNUN ADI — HIJYEN NOBETCISI (KraL-AdSupurmesi-05Eyl, kalem 5).

Okan emri (5 Eyl 2026): "bu bizde yok · onu nerde gordiysen ismini sil."

🔴 BU NOBETCI IKI YONLUDUR — ve ikinci yon birincisinden ONEMLIDIR.

  YON 1 (yayilma):  ad, IZIN VERILEN dosyalarin DISINDA gorunurse KIRMIZI.
  YON 2 (silinme):  yasagi ISIRTAN CAPALAR kaybolursa KIRMIZI.

YON 2 neden var: bu adin bazi gecisleri bir ATIF degil bir YASAK KAYDIDIR.
`os.path.basename(argv0) == "codex"` satiri, emekli motorun cagrilmasini
REDDEDEN TEK esleme noktasidir. Onu "temizlik" diye silmek adi ortadan
kaldirir ama YASAGI DA kaldirir — emekli motor sessizce yeniden mesru olur.
Bu yuzden tek yonlu bir `grep == 0` nobetcisi BU ISTE OLU BIR NOBETCIDIR:
yesil yanarken korumayi kaldirmis olabilir.

Bu yuzden hukum "sifir gecis" DEGIL, **NON-GROWTH + CAPA SAGLIGI**:
  * izinli dosyalarda gecis sayisi CIVILENMIS tavani ASAMAZ (yayilma durur),
  * izinli olmayan HER dosya KIRMIZI (yeni sizinti durur),
  * her capa metni YERINDE DURMALI (yasak canli kalir).

Kosum:  python3 tools/emekli-motor-adi-nobetcisi.py [--ayrinti]
Cikti son satiri:  ADI_NOBETI HUKUM=<GECTI|KIRMIZI> ...
"""
import os
import subprocess
import sys

AD = "codex"
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AYRINTI = "--ayrinti" in sys.argv

# ============================ MENZIL (BaBa civiledi) ============================
# 6 evin CLAUDE.md + DEVAM + skills/ + tools/*.py + .claude/*.py
EVLER = ("pruvo", "pruvo-pazarlama", "pruvo-bot", "pruvo-hasat", "pruvo-jenerator")
DEV = os.path.expanduser("~/dev")
SKILLS = os.path.expanduser("~/.claude/skills")

# ===================== (b) IZIN VERILEN DOSYALAR — NON-GROWTH =====================
# Her satir: yol -> (TAVAN, o dosyanin adi NEDEN tasidigi).
# 🔴 TAVANI YUKSELTMEK BIR KARARDIR. Yukseltiyorsan (a)/(b) siniflamasini
#    kapanisa YAZ; sessizce buyutmek supurmeyi geri alir.
IZINLI = {
    # --- yasagin ESLEME noktasi ve KIMLIK kaydi ---
    "tools/mimar-icra-kapisi.py": (5, "argv0 esleme satiri + daraltmanin gerekce yorumlari"),
    "tools/mimar_kimlik.py": (2, "EMEKLI_ISCI_MOTORLARI kimlik kaydi + emekli model kimligi"),
    "tools/k316/tk-yama.py": (1, "ayni kimlik kaydinin yama kopyasi"),
    # --- yasagin FIKSTUR yuzeyi: 'reddediliyor' olcmek icin adi YAZMAK gerekir ---
    "tools/mimar-kilit-test.py": (64, "yasagin negatif/yanlis-pozitif vaka komutlari"),
    "tools/mimar-kapi-mutasyon-test.py": (20, "mutant yamalari CANLI GOVDEYE birebir esitlenir"),
    "tools/k260/nobet-kat-kovasi-test.py": (3, "goc kaydi fiksturu (emekli kat adi)"),
    "tools/n4b/b4-kur.py": (4, "bayat kayit fiksturu: dosyadaki GERCEK dizgeye eslesir"),
    # --- ucuncu taraf MAKINE ADRESI: bizim adlandirmamiz degil, degistirilemez ---
    "tools/thing-icerik.py": (3, "ikili yolu + oturum/kimlik dizini"),
    "tools/parity-backfill.py": (1, "ikili yolu"),
    "tools/yetkinlik/kosum.py": (2, "ikili yolu + oturum dokumu glob'u"),
    "tools/yedekle.py": (4, "yedek disi birakilan ucuncu taraf dizin adlari"),
    # --- nobetcinin KENDISI: aradigi jetonu tasimak ZORUNDA ---
    # [[kurucu-kendi-kapisina-takilir]] — ilk kosumda kendini KIRMIZI yakti.
    "tools/emekli-motor-adi-nobetcisi.py": (6, "nobetcinin aradigi jeton + capa metinleri"),
    "tools/emekli-motor-adi-nobetcisi-test.py": (6, "mutant yuku: nobetciyi KIRMIZI yakan vakalar"),
    # --- 🔴 ODEV (KraL kapatamaz: kardes evin AGACI, ustelik KIRLI) ---
    # 5 Eyl olcumu: iki evde de calisma agaci KIRLI (mimarlarinin commit'lenmemis
    # isi var), o yuzden KraL DOKUNMADI. Tek satirlik duzeltme kutuya YAZILDI.
    # Sahibi kapatinca TAVANI 0 YAP — tavan burada bir BORCTUR, muafiyet degil.
    "pruvo-hasat/CLAUDE.md": (1, "ODEV: L115 muafiyet anahtari eski adda (sahibi commit'ler)"),
    "pruvo-pazarlama/CLAUDE.md": (1, "ODEV: L66 muafiyet anahtari eski adda (sahibi commit'ler)"),
}

# ===================== YON 2: YASAGI ISIRTAN CAPALAR =====================
# Bu metinler DURMALI. Biri kaybolursa yasak delinmis demektir.
CAPALAR = (
    ("tools/mimar-icra-kapisi.py", 'os.path.basename(argv0) == "codex"',
     "emekli motor cagrisinin TEK esleme noktasi"),
    ("tools/mimar_kimlik.py", 'EMEKLI_ISCI_MOTORLARI = ("codex"',
     "emekli motor KIMLIK kaydi (red metinleri bundan turer)"),
    ("tools/mimar-icra-kapisi.py", "isci-muafiyet:",
     "yeni muafiyet anahtari (eski ad RED'e dustu)"),
)


def _dosyalar():
    """Menzildeki dosyalari doner: (mutlak_yol, rapor_adi)."""
    for ev in EVLER:
        # 🔴 `DEVAM-ARSIV.md` MENZIL DISIDIR: git disi TARIHSEL defterdir; gecmis
        # turlarin metnini yeniden yazmak KAYDI TAHRIF eder. Menzil BaBa'nin
        # civiledigi haliyle CANLI belgelerdir.
        for ad in ("CLAUDE.md", "DEVAM.md"):
            y = os.path.join(DEV, ev, ad)
            if os.path.exists(y):
                yield y, "%s/%s" % (ev, ad)
    for kok, dizinler, dosyalar in os.walk(SKILLS):
        dizinler[:] = [d for d in dizinler if not d.startswith(".")]
        for d in dosyalar:
            yield os.path.join(kok, d), "skills/" + os.path.relpath(
                os.path.join(kok, d), SKILLS)
    for alt in ("tools", ".claude"):
        for kok, dizinler, dosyalar in os.walk(os.path.join(KOK, alt)):
            dizinler[:] = [d for d in dizinler if d not in ("worktrees", "__pycache__")]
            for d in dosyalar:
                if d.endswith(".py") and ".yedek-" not in d:
                    y = os.path.join(kok, d)
                    yield y, os.path.relpath(y, KOK)


def _sayim(yol):
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            return sum(1 for satir in f if AD in satir.lower())
    except OSError:
        return 0


ihlal, buyume, capa_dusen, izinli_gorulen = [], [], [], {}
for yol, ad in _dosyalar():
    n = _sayim(yol)
    if not n:
        continue
    if ad in IZINLI:
        tavan, _ = IZINLI[ad]
        izinli_gorulen[ad] = n
        if n > tavan:
            buyume.append((ad, n, tavan))
    else:
        ihlal.append((ad, n))

for ad, capa, neden in CAPALAR:
    yol = os.path.join(KOK, ad)
    try:
        govde = open(yol, encoding="utf-8", errors="replace").read()
    except OSError:
        govde = ""
    if capa not in govde:
        capa_dusen.append((ad, capa, neden))

if AYRINTI:
    print("--- izinli dosyalar (gecis/tavan) ---")
    for ad, (tavan, neden) in sorted(IZINLI.items()):
        print("   %-42s %3d/%-3d  %s" % (ad, izinli_gorulen.get(ad, 0), tavan, neden))
for ad, n in sorted(ihlal):
    print("🔴 IZINSIZ DOSYADA AD: %s (%d gecis)" % (ad, n))
for ad, n, tavan in sorted(buyume):
    print("🔴 TAVAN ASILDI: %s %d > %d" % (ad, n, tavan))
for ad, capa, neden in capa_dusen:
    print("🔴 YASAK CAPASI DUSTU: %s :: %s  (%s)" % (ad, capa[:46], neden))

hukum = "GECTI" if not (ihlal or buyume or capa_dusen) else "KIRMIZI"
print("ADI_NOBETI HUKUM=%s IHLAL=%d TAVAN_ASIMI=%d CAPA_DUSEN=%d IZINLI_DOSYA=%d"
      % (hukum, len(ihlal), len(buyume), len(capa_dusen), len(IZINLI)))
sys.exit(0 if hukum == "GECTI" else 1)

#!/usr/bin/env python3
"""Makine olursa kaybolacak yeri-doldurulamaz yerel dosyalari Drive'a yedekler.
Drive yolu tools/drive_yolu.py ile cozulur (kayitli .stl-backup-dir bayatsa kendini duzeltir).
Hedef: <Pruvo>/backup/  (memory klasoru + global skill'ler + .urun-kaynaklari.json + baglam .md'leri).

SIRLAR — IKI AYRI REJIM, KARISTIRMA:
  1. REPO KOKUNDEKI SANCAKLI SIR LISTESI (.thingiverse-token, .r2-credentials.json, ...):
     VARSAYILAN yedeklenmez; "--sirlar" ile ayni ozel Drive'a dahil edilir (klasoru PAYLASMA!).
  2. ~/.claude/skills AGACI: burada sir OLMAMASI gerekir; agac vetted degil (elle duzenlenen,
     git disi bir alan) -> ad kara-listesi + ad deseni + ICERIK imzasi ile KOSULSUZ elenir.
     Bu filtre "--sirlar" ile ACILMAZ: sancakli liste bilinen 5 dosyadir, skills agaci degil.
     Elenen her dosya SEBEBIYLE raporlanir (sessiz atlamak yok). Icerik imzasi bulunursa
     yalniz IMZA SINIFI basilir — eslesen metin ASLA ekrana/loga yazilmaz.

BAYAT SIR NOBETI: bu filtre 26 Tem'de eklendi; ondan onceki surum skills agacini FILTRESIZ
copytree ile kopyaliyordu. Hedefte elenmis bir dosyanin ESKI kopyasi duruyorsa gurultulu
uyarilir; "--sir-temizle" ile silinir (varsayilan SILMEZ — yedekten veri silmek elle onaylanir).

Kullanim:
    python3 tools/yedekle.py              # sirsiz (memory + skills + kaynak haritasi + .md)
    python3 tools/yedekle.py --kuru       # KURU KOSUM: ne kopyalanacagini listeler, YAZMAZ
    python3 tools/yedekle.py --sirlar     # + token + r2 creds (repo kokundeki sancakli liste)
    python3 tools/yedekle.py --sir-temizle  # hedefteki bayat sir kopyalarini SIL
"""
import fnmatch
import os
import re
import shutil
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
MEMORY = os.path.expanduser("~/.claude/projects/-Users-okan-dev-pruvo/memory")
SKILLS = os.path.expanduser("~/.claude/skills")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_yolu

BAYRAKLAR = {"--kuru", "--dry-run", "--sirlar", "--sir-temizle", "-h", "--help"}

# ---- GURULTU (turetilmis; sir DEGIL, sadece yedege deger etmez) --------------
GURULTU_DIZIN = {"__pycache__", ".git", "node_modules", ".venv", ".mypy_cache", ".pytest_cache"}
GURULTU_DOSYA = ("*.pyc", "*.pyo", ".DS_Store")

# ---- SIR NOBETI (skills agacinda kosulsuz) ----------------------------------
# Tam ad kara listesi: repoda bilinen sir dosyalari + CNAME (mimar emri: yedek paketine girmez).
SIR_ADLARI = {
    ".r2-credentials.json", ".thingiverse-token", ".stl-backup-dir",
    ".onizleme-kapat-anahtar", "cname", ".env", ".netrc", ".npmrc", ".pypirc",
    "credentials", "id_rsa", "id_ed25519", "id_ecdsa",
}
# Ad desenleri (kucuk harfe indirgenmis ad uzerinde fnmatch).
SIR_DESENLERI = (
    "*credential*", "*secret*", "*token*", "*passwd*", "*password*", "*apikey*",
    "*api-key*", "*api_key*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "*.keystore", "*.ppk", ".env.*", "*.env", "id_rsa*", "id_ed25519*", "*.asc",
)
# Icerik imzalari: YUKSEK SINYAL olanlar (yanlis-pozitif ucuz degil ama fail-closed sectik).
# (etiket, regex) -- rapora YALNIZ etiket girer, eslesen metin GIRMEZ.
SIR_IMZALARI = (
    ("ozel anahtar blogu", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS/R2 erisim anahtari", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub jetonu", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("Slack jetonu", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Anthropic API anahtari", re.compile(r"sk-ant-api[0-9]{2}-[A-Za-z0-9_\-]{20,}")),
    ("Google API anahtari", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Cloudflare global key alani", re.compile(
        r"\"(?:secret_access_key|access_key_id|api_token|apiToken)\"\s*:\s*\"[^\"]{16,}\"")),
)
ICERIK_TARAMA_SINIRI = 2 * 1024 * 1024  # 2 MiB'den buyuk dosyanin yalniz basi taranir


def _gurultu_mu(ad):
    return any(fnmatch.fnmatch(ad, d) for d in GURULTU_DOSYA)


def _icerik_imzasi(yol):
    """Dosya icinde yuksek-sinyal kimlik imzasi varsa ETIKETINI dondurur, yoksa None.
    Okunamayan dosya -> fail-closed: 'okunamadi' etiketi (yedege ALINMAZ)."""
    try:
        with open(yol, "rb") as f:
            ham = f.read(ICERIK_TARAMA_SINIRI)
    except Exception as e:
        return "okunamadi (%s)" % type(e).__name__
    if b"\0" in ham[:8192]:
        return None  # ikili dosya: imza taramasi anlamsiz (gurultu zaten elenmis olur)
    metin = ham.decode("utf-8", "ignore")
    for etiket, kalip in SIR_IMZALARI:
        if kalip.search(metin):
            return etiket
    return None


def sir_sebebi(yol, ad):
    """Dosya sir sayiliyorsa INSANA OKUNUR sebep, degilse None.
    Sebep metni ASLA sirrin kendisini icermez (yalniz kural/imza sinifi)."""
    dusuk = ad.lower()
    if dusuk in SIR_ADLARI:
        return "ad kara listede"
    for desen in SIR_DESENLERI:
        if fnmatch.fnmatch(dusuk, desen):
            return "ad deseni: %s" % desen
    imza = _icerik_imzasi(yol)
    if imza:
        return "icerik imzasi: %s" % imza
    return None


def skills_plani(kok=None):
    """~/.claude/skills agacini tarar.

    Doner: (dahil, haric, gurultu)
      dahil   : [koke gorece yol]           -> yedege GIRER
      haric   : [(gorece yol, sebep)]       -> SIR nobeti eledi
      gurultu : [gorece yol]                -> turetilmis (pyc/.DS_Store), sessizce atlanir
    """
    kok = SKILLS if kok is None else kok
    dahil, haric, gurultu = [], [], []
    if not os.path.isdir(kok):
        return dahil, haric, gurultu
    for dizin, altlar, dosyalar in os.walk(kok):
        altlar[:] = sorted(a for a in altlar if a not in GURULTU_DIZIN)
        for ad in sorted(dosyalar):
            tam = os.path.join(dizin, ad)
            gor = os.path.relpath(tam, kok)
            if os.path.islink(tam):
                # symlink hedefi agac disina cikabilir (sir sizma yolu) -> alinmaz.
                haric.append((gor, "symlink (hedefi agac disina cikabilir)"))
                continue
            if _gurultu_mu(ad):
                gurultu.append(gor)
                continue
            sebep = sir_sebebi(tam, ad)
            if sebep:
                haric.append((gor, sebep))
                continue
            dahil.append(gor)
    return sorted(dahil), sorted(haric), sorted(gurultu)


def skills_yaz(kok, hedef, dahil, haric, sir_temizle=False):
    """Plani hedefe yazar (idempotent: ayni dosya uzerine yazilir, mukerrer yigilmaz).

    Doner: (yazilan_sayisi, bayat_sir_yollari)
    bayat_sir: ELENMIS bir dosyanin hedefte duran ESKI kopyasi (filtresiz surumden kalma).
    """
    yazilan = 0
    for gor in dahil:
        kaynak = os.path.join(kok, gor)
        varis = os.path.join(hedef, gor)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        shutil.copy2(kaynak, varis)
        yazilan += 1
    bayat = []
    for gor, _sebep in haric:
        varis = os.path.join(hedef, gor)
        if os.path.exists(varis):
            bayat.append(varis)
            if sir_temizle:
                os.remove(varis)
    return yazilan, bayat


def _agac_dosyalari(kok):
    """Kuru kosum listelemesi icin: kokun altindaki tum dosyalar (gorece, sirali)."""
    cikti = []
    if not os.path.isdir(kok):
        return cikti
    for dizin, _altlar, dosyalar in os.walk(kok):
        for ad in dosyalar:
            cikti.append(os.path.relpath(os.path.join(dizin, ad), kok))
    return sorted(cikti)


def _repo_dosyalari(sirlar):
    """Repo kokunden yedeklenecek dosya adlari (varsayilan + --sirlar sancakli listesi)."""
    adlar = [".urun-kaynaklari.json", "CLAUDE.md", "DEVAM.md", "DEVAM-ARSIV.md"]
    if sirlar:
        adlar += [".thingiverse-token", ".r2-credentials.json", ".stl-backup-dir",
                  ".onizleme-kapat-anahtar", ".mukerrer-istisna.json"]
    return [a for a in adlar
            if os.path.exists(os.path.join(ROOT, a)) and not os.path.islink(os.path.join(ROOT, a))]


def main():
    # --help yedekleme BASLATMASIN (denetim 2026-07-15: --help dogrudan yaziyordu).
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__.strip())
        return 0
    # BILINMEYEN BAYRAK = FAIL-CLOSED. Yazim hatasi ("--kuruu") sessizce GERCEK yedek
    # baslatmasin; ayni sinif hata --help'te bir kez yasandi.
    bilinmeyen = [a for a in sys.argv[1:] if a not in BAYRAKLAR]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        print("Gecerli: " + ", ".join(sorted(BAYRAKLAR)), file=sys.stderr)
        return 2

    kuru = ("--kuru" in sys.argv) or ("--dry-run" in sys.argv)
    sirlar = "--sirlar" in sys.argv
    sir_temizle = "--sir-temizle" in sys.argv

    dahil, haric, gurultu = skills_plani()

    # ---- KURU KOSUM: hicbir sey yazma, sadece plani bas -------------------
    if kuru:
        pruvo_drive = drive_yolu.pruvo_dizini(sessiz=True)
        hedef = os.path.join(pruvo_drive, "backup") if pruvo_drive else None
        print("KURU KOSUM — hicbir dosya YAZILMADI.")
        print("Hedef: " + (hedef or "(Drive COZULEMEDI — gercek kosumda yedek ALINMAZ)"))
        mem = _agac_dosyalari(MEMORY)
        print("-" * 70)
        print("[memory] %d dosya  <- %s" % (len(mem), MEMORY))
        for g in mem:
            print("    memory/" + g)
        print("[skills] %d dosya  <- %s" % (len(dahil), SKILLS))
        for g in dahil:
            print("    skills/" + g)
        print("[skills-HARIC (sir nobeti)] %d dosya" % len(haric))
        for g, sebep in haric:
            print("    skills/%s   -> ELENDI: %s" % (g, sebep))
        print("[skills-gurultu (turetilmis)] %d dosya" % len(gurultu))
        for g in gurultu:
            print("    skills/" + g)
        repo = _repo_dosyalari(sirlar)
        print("[repo] %d dosya%s" % (len(repo), "  (--sirlar ACIK)" if sirlar else ""))
        for a in repo:
            print("    " + a)
        print("-" * 70)
        print("TOPLAM YEDEKLENECEK: %d dosya (memory %d + skills %d + repo %d)"
              % (len(mem) + len(dahil) + len(repo), len(mem), len(dahil), len(repo)))
        if haric:
            print("SIR NOBETI: %d dosya paket DISINDA birakilacak." % len(haric))
        return 0

    # ---- GERCEK KOSUM ----------------------------------------------------
    # Drive yolunu drive_yolu cozer: bayatsa kendi duzeltir, mount yoksa uyarip None doner.
    # None'da DURUYORUZ — eskiden makedirs Drive yerine sahte yerel klasor yaratip "yedeklendi" diyordu.
    pruvo_drive = drive_yolu.pruvo_dizini()           # .../Pruvo
    if not pruvo_drive:
        print("Yedek ALINMADI — Drive yolu cozulemedi (yukaridaki uyariya bak).")
        return 1
    backup = os.path.join(pruvo_drive, "backup")
    os.makedirs(os.path.join(backup, "memory"), exist_ok=True)

    # memory klasoru
    if os.path.isdir(MEMORY):
        shutil.copytree(MEMORY, os.path.join(backup, "memory"), dirs_exist_ok=True)
        print("yedek: memory/ ->", os.path.join(backup, "memory"))

    # ~/.claude/skills/ — global skill'ler (merge-kapisi dahil) GIT DISINDA tutuluyor
    # (mimar karari 21 Tem: repoya tasinmayacak) -> TEK kopya bu makinede. Yedeklenmezse
    # disk kaybinda SKILL.md + dal-olc.py + kabul-test.py (davranissal batarya) topluca gider.
    # Artik copytree DEGIL dosya-dosya: her dosya sir nobetinden gecer (bkz. sir_sebebi).
    if os.path.isdir(SKILLS):
        hedef = os.path.join(backup, "skills")
        yazilan, bayat = skills_yaz(SKILLS, hedef, dahil, haric, sir_temizle=sir_temizle)
        print("yedek: skills/ -> %s  (%d dosya)" % (hedef, yazilan))
        for g, sebep in haric:
            print("  SIR NOBETI — paket DISI: skills/%s  (%s)" % (g, sebep))
        for yol in bayat:
            if sir_temizle:
                print("  BAYAT SIR KOPYASI SILINDI: " + yol)
            else:
                print("  ⚠️ BAYAT SIR KOPYASI hedefte DURUYOR: " + yol
                      + "   (silmek icin: python3 tools/yedekle.py --sir-temizle)")
    else:
        print("NOT: %s yok -> skill yedegi ATLANDI." % SKILLS)

    # Sirsiz kaynak haritasi + ajan baglam dosyalari. HEPSI GITIGNORE'DA (repo public, icerik
    # ticari gizli) -> git'te KOPYASI YOK, yani bu makine olurse tamamen kaybolurlardi.
    # (AGENTS.md kopyalanmaz: CLAUDE.md'ye symlink, ayri dosya degil.)
    for ad in _repo_dosyalari(sirlar=False):
        shutil.copy2(os.path.join(ROOT, ad), os.path.join(backup, ad))
        print("yedek:", ad)

    if sirlar:
        for name in (".thingiverse-token", ".r2-credentials.json", ".stl-backup-dir",
                     ".onizleme-kapat-anahtar", ".mukerrer-istisna.json"):
            p = os.path.join(ROOT, name)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(backup, name))
                print("yedek (SIR):", name)
        print("NOT: bu klasoru kimseyle PAYLASMA — sir icerir.")

    print("bitti ->", backup)
    return 0


if __name__ == "__main__":
    sys.exit(main())

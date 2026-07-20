#!/usr/bin/env python3
"""PreToolUse kilidi (Edit|Write|MultiEdit): mimar oturumu kaynak/veri dosyasini
degistiremez VE calistirilabilir betik YAZAMAZ.

20 Tem guclendirmesi (KraL teshisi): eski surum yalnizca REPO ICINDEKI dosyalari
denetliyordu; scratchpad muafiyeti (".md spec yazsin diye" konmustu) keyfi program
yazarligina donusmustu — mimar /private/tmp/.../scratchpad/ altina .py yaziyor, sonra
Bash'ten 'python3 /tam/yol.py' ile kosturuyordu; repoya tek satir girmedigi icin kilit
hic yanmiyordu. Artik calistirilabilir uzanti KONUMDAN BAGIMSIZ reddedilir.
Ikinci ayak: tools/mimar-icra-kapisi.py (Bash) — repo disi betigi kosturmayi engeller.

20 Tem KALIBRASYONU — KIMLIK EKSENI (olculmus ariza: kapi mesru MUHENDIS ajanlarini da
kilitliyordu; 4 kez mesru isi engelledi, bir isci sed'e kacti = kapi guvenligi AZALTTI):
  * PreToolUse stdin JSON'unda `agent_id` DOLU ise cagri bir ALT AJANDAN gelmistir →
    kapi (cekirdek liste disinda) hicbir sey yapmaz.
  * agent_id kabuktan/env'den/cwd'den BESLENMEZ; Claude Code process'i icinde uretilir.
    cwd (cd ile kayar), agent_type (alt ajanin sectigi ad) ve env eksenleri BILEREK
    kullanilmaz — hepsi kaydirilabilir sinyaldir.
  * CEKIRDEK liste kimlikten BAGIMSIZDIR: ana repodaki kapi/kablo dosyalari kimse
    tarafindan degistirilemez. Kapi bakimi zaten WORKTREE'de yapilir; worktree
    kopyalari serbesttir.

MUAF KALAN (bilerek — kapatirsan mimarin isi durur):
  * .md her yerde (spec, DEVAM.md, hafiza, RAPOR-MIMARA) — mimarin ASIL isi
  * scratchpad'de VERI/NOT dosyalari (.txt/.json — commit mesaji, olcum notu)
  * worktree'ler: /Users/okan/dev/pruvo/.claude/worktrees/ ONEKI + git'e KAYITLI
    worktree kokleri (or. /private/tmp/pruvo-toka-jenerator) — mesru muhendis alani

BILINEN BYPASS (kapi disiplin cihazidir, hapishane DEGIL — memory/kapi-disiplin-ilkesi.md;
kayitli olmasi sart):
  * UZANTISIZ (shebang'li) betik yazimi: yasak ICRA_UZANTILARI listesine dayanir, yani
    uzantisiz bir ad (or. Write ile "analiz" + shebang) YAKALANMAZ. Bu yuzden "calistirilabilir
    betik YAZAMAZ" iddiasi TAM DEGIL — kapsam uzanti-tabanlidir. Ayni kök, icra kapisinin
    uzantisiz +x dosyayi dogrudan cagrida kacirmasiyla birdir. Kapatilmadi: uzanti listesini
    genisletmek veri/not dosyasi adlarinda yanlis-pozitif riski (disiplin cihazi, sinir degil).
  * 'git worktree add /private/tmp/x' TEK komutla kalici muaf bolge acar (yeni kok
    .git/worktrees'e kaydolur → worktree_ici() true doner). BILEREK kapatilmadi:
    git yonetimi mimarin kapisidir. Olcum: 'git worktree list' cikti sayisi.
  * agent_id DOLU cagri (alt ajan) CEKIRDEK disinda hicbir kurala tabi degildir.
"""
import json
import os
import sys

# Calistirilabilir uzantilar: KONUMDAN BAGIMSIZ yasak (scratchpad dahil).
ICRA_UZANTILARI = (
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".sh", ".bash", ".zsh", ".command",
)

REPO_ONEKI = "/Users/okan/dev/pruvo/"
WT_ONEK = "/Users/okan/dev/pruvo/.claude/worktrees/"
GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"

# ANA REPODAKI kapi + kablo dosyalari: KIMLIKTEN BAGIMSIZ kilitli. Isci de degistiremez.
# (Kapi bakim isi worktree'de yapilir; oradaki kopya serbesttir — vaka 72.)
# NOT: bu BILINCLI bir yanlis-pozitiftir; "isci bloklanmis" diye sokulmemeli.
# 20 Tem ONARIMI: liste NOBETCILERI de kapsar. Olculmus acik — eski liste yalnizca
# kapilarin KENDISINI koruyordu; kapiyi YALANCI yapan yol nobetciden geciyordu:
# kabul testini/mutasyon takimini/envanteri sessizce degistiren biri kapiyi hic
# ellemeden yesil yakar. urunler-guard + .git/hooks/pre-commit ayni sinifta: veri
# duzleminin ve commit zincirinin canli kablosu.
# MALIYET OLCUMU: bu genisletme HICBIR mesru ana-checkout isci vakasini bloklamaz —
# kaynak isi zaten ana checkout'ta COMMIT'lenemez (commit kapisi), worktree kopyasi
# serbesttir (vaka 72), ve pre-commit hook'u Write ile degil kurucu araciyla kurulur.
CEKIRDEK = {
    "/Users/okan/dev/pruvo/.claude/settings.json",
    "/Users/okan/dev/pruvo/.claude/settings.local.json",
    "/Users/okan/dev/pruvo/tools/mimar-kod-kilidi.py",
    "/Users/okan/dev/pruvo/tools/mimar-icra-kapisi.py",
    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi.py",
    "/Users/okan/dev/pruvo/tools/mimar-kapi-kur.py",
    "/Users/okan/dev/pruvo/tools/mimar-kilit-test.py",
    # NOBETCILER (kapiyi yalanci yapabilen dosyalar)
    "/Users/okan/dev/pruvo/tools/mimar-kapi-mutasyon-test.py",
    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi-test.py",
    "/Users/okan/dev/pruvo/tools/mimar-commit-kapisi-mutasyon.py",
    "/Users/okan/dev/pruvo/tools/kapi-envanteri.py",
    "/Users/okan/dev/pruvo/tools/urunler-guard.py",
    # CANLI KABLO
    "/Users/okan/dev/pruvo/.git/hooks/pre-commit",
    # CANLI PreToolUse/Bash ZINCIRI (20 Tem, B8): ikisi de settings.json'da KAYITLI ve
    # calisiyor; pre-commit'in kendi yorumu urunler-guard-hook.py'yi "birincil koruma"
    # diye adlandirir. CEKIRDEK'te olmadiklari icin tek Write ile susturulabiliyorlardi.
    # MALIYET OLCULDU: hicbir mesru isci vakasi bloklanmaz — ikisi de tools/*.py yani
    # KAYNAK'tir, ana checkout'ta zaten commit'lenemez (commit kapisi; env=worker
    # kaynagi acmaz), gelistirme yolu worktree'dir ve worktree kopyalari SERBEST kalir.
    "/Users/okan/dev/pruvo/tools/urunler-guard-hook.py",
    "/Users/okan/dev/pruvo/tools/komut-stili-kapisi.py",
}


def kimlik(girdi):
    aid = girdi.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return "ISCI"
    return "MIMAR"


def iz_bas(etiket):
    """ALLOW kararinda stderr'e TEK SATIR iz. stdout BOS kalir — allow karari
    stdout'a JSON olarak BASILMAZ ki zincirdeki baska kapilarin deny'ini ezmesin.
    Bu iz sayesinde kabul testi 'kapi kostu ve izin verdi' ile 'kapi yok/coktu'
    durumunu ayirt edebilir (eski fail-open korlugu)."""
    try:
        sys.stderr.write("MIMAR-KAPISI allow " + etiket + "\n")
    except Exception:
        pass


def kayitli_worktree_kokleri():
    """.git/worktrees/*/gitdir dosyalarindan worktree koklerini okur.
    Icerik '<kok>/.git' → dirname = kok. HATA olursa BOS kume (eski/dar davranisa
    dus, asla cokme)."""
    kokler = set()
    try:
        for ad in os.listdir(GIT_WORKTREE_KAYIT):
            gitdir = os.path.join(GIT_WORKTREE_KAYIT, ad, "gitdir")
            try:
                with open(gitdir, encoding="utf-8") as f:
                    icerik = f.read().strip()
            except Exception:
                continue
            if not icerik:
                continue
            kok = os.path.normpath(os.path.dirname(icerik))
            if kok and kok != "/":
                kokler.add(kok)
    except Exception:
        return set()
    return kokler


def worktree_ici(yol):
    """ONEK + KAYIT birlesimi.
    ONEK tek basina yetmez: kayitli ama repo DISINDAKI worktree'ler var
    (olculdu: /private/tmp/pruvo-toka-jenerator).
    KAYIT tek basina yetmez: diskte canli ama kayitsiz mesru dizinler var
    (olculdu: .claude/worktrees/toka-fizik-analiz).
    Eski surum burada ALT-DIZE testi yapiyordu ('/.claude/worktrees/' in fp) →
    '/tmp/x/.claude/worktrees/kotu.py' gibi SAHTE yollar muafti (vaka 80/81)."""
    yol = os.path.normpath(yol)
    if yol.startswith(WT_ONEK):
        return True
    for kok in kayitli_worktree_kokleri():
        if yol == kok or yol.startswith(kok + "/"):
            return True
    return False


def reddet(gerekce):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": gerekce,
        }
    }, ensure_ascii=False))
    sys.exit(0)


try:
    girdi = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# NOT (20 Tem, mimar sorusu (a)): burada bir ara "cwd/CLAUDE_PROJECT_DIR worktree
# icindeyse TAM MUAF" seklinde bir OTURUM muafiyeti vardi. KALDIRILDI — cwd kaydirilabilir
# bir sinyal (kabuk cwd'si cagrilar arasi kalici, 'cd' makine olarak engellenmiyor, gercek
# worktree dizinleri diskte duruyor) → "cd <worktree>" tek komutluk muafiyet anahtari olurdu.
# Kimlik ekseni (agent_id) bunun yerini alir: kaydirilamaz, cunku kabuktan beslenmez.
fp = (girdi.get("tool_input") or {}).get("file_path") or ""
if not fp:
    sys.exit(0)

fp = os.path.normpath(fp)

# 0) CEKIRDEK: ana repodaki kapi/kablo dosyalari — KIMLIKTEN BAGIMSIZ deny.
if fp in CEKIRDEK:
    reddet(
        "MİMAR KAPISI — kapı/kablo dosyaları ana repoda kilitlidir (kimlikten bağımsız). "
        "Kapı işini KENDİ WORKTREE'NDE yap; oradaki kopya serbesttir."
    )

# 1) KIMLIK: agent_id doluysa cagri ALT AJANDAN gelir → mesru muhendis, kural uygulanmaz.
if kimlik(girdi) == "ISCI":
    iz_bas("ISCI")
    sys.exit(0)

# 2) Worktree'ler (Agent isolation:worktree) mesru muhendistir — TAM muaf.
#    Bu kontrol icra-uzantisi kontrolunden ONCE gelmeli: muhendis .py yazabilmeli.
#    agent_id ekseni bir surumde olurse sistem BURAYA duser (bugunku bilinen davranis),
#    "her sey mimar" felaketine degil.
if worktree_ici(fp):
    iz_bas("MIMAR-worktree")
    sys.exit(0)

# 3) Calistirilabilir betik yazarligi: KONUMDAN BAGIMSIZ yasak (bugunku asil acik).
if fp.lower().endswith(ICRA_UZANTILARI):
    reddet(
        "MİMAR KOD-KİLİDİ — ÇALIŞTIRILABİLİR BETİK YAZARLIĞI YASAK (konumdan bağımsız, "
        "20 Tem): mimar kod yazmaz, kod YAZDIRIR. Scratchpad dahil hiçbir yere "
        ".py/.js/.mjs/.ts/.sh yazamazsın. ÇÖZÜM: (a) işi MÜHENDİS/USTA/MARABA'ya delege et "
        "(Agent aracı: model opus/sonnet + isolation worktree + background) ya da Codex'e ver; "
        "(b) isteğini .md SPEC'ine yaz — kural + çalıştırılabilir KABUL TESTİ dahil; "
        "(c) ölçmek istiyorsan repodaki MEVCUT aracı koştur (node tools/parite-test.js, "
        "python3 tools/d1-sync.py --durum, python3 tools/durum.py). "
        "İZİNLİ: *.md her yerde, scratchpad'de .txt/.json not/veri, worktree'ler. "
        "MÜHENDİSSEN: betiğini scratchpad'e değil KENDİ WORKTREE'NE yaz "
        "(/Users/okan/dev/pruvo/.claude/worktrees/<dal>/...) — orası muaf, kalıcı ve denetlenebilir."
    )

# 4) Not/spec/veri dosyalari: serbest (mimarin asil isi).
if fp.endswith(".md"):
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)

# 5) Scratchpad muafiyeti YALNIZ veri/not dosyalari icin (betikler yukarida elendi).
if fp.startswith("/private/tmp/") and "/scratchpad/" in fp:
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)
if "/scratchpad/" in fp and "/claude-" in fp:
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)

# 6) Repo disindaki diger dosyalar (hafiza dosyalari vb.) bu kilidin konusu degil.
if not fp.startswith(REPO_ONEKI):
    iz_bas("MIMAR-kural-yok")
    sys.exit(0)

basename = os.path.basename(fp)
blocked = (
    fp.endswith(".html")
    or fp.endswith(".css")
    or fp.endswith(".sql")
    or basename == "urunler.json"
    or basename == ".urun-kaynaklari.json"
    or fp.endswith("/.claude/settings.json")
    or fp.endswith("/.claude/settings.local.json")
    # Kapilar kendilerini korur. (Uzanti kurali ve CEKIRDEK zaten yakalar; acik kayit =
    #  regresyon kalkani: uzanti listesi bir gun daralirsa kapilar yine korunur.)
    or basename == "mimar-kod-kilidi.py"
    or basename == "mimar-icra-kapisi.py"
)

if blocked:
    reddet(
        "MİMAR KOD-KİLİDİ (Okan 18 Tem): kaynak/veri dosyasına Edit/Write YASAK — işi "
        "Codex'e ya da worktree worker'a DELEGE et, spec'i .md dosyasına yaz. Kilidin "
        "kendisini de değiştiremezsin. İzinli: *.md, scratchpad'de veri/not dosyaları, "
        "worktree'ler."
    )
iz_bas("MIMAR-kural-yok")
sys.exit(0)

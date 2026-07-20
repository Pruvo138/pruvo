#!/usr/bin/env python3
"""PreToolUse kilidi (Edit|Write|MultiEdit): mimar oturumu kaynak/veri dosyasini
degistiremez VE calistirilabilir betik YAZAMAZ.

20 Tem guclendirmesi (KraL teshisi): eski surum yalnizca REPO ICINDEKI dosyalari
denetliyordu; scratchpad muafiyeti (".md spec yazsin diye" konmustu) keyfi program
yazarligina donusmustu — mimar /private/tmp/.../scratchpad/ altina .py yaziyor, sonra
Bash'ten 'python3 /tam/yol.py' ile kosturuyordu; repoya tek satir girmedigi icin kilit
hic yanmiyordu. Artik calistirilabilir uzanti KONUMDAN BAGIMSIZ reddedilir.
Ikinci ayak: tools/mimar-icra-kapisi.py (Bash) — repo disi betigi kosturmayi engeller.

MUAF KALAN (bilerek — kapatirsan mimarin isi durur):
  * .md her yerde (spec, DEVAM.md, hafiza, RAPOR-MIMARA) — mimarin ASIL isi
  * scratchpad'de VERI/NOT dosyalari (.txt/.json — commit mesaji, olcum notu)
  * /.claude/worktrees/ alti — mesru muhendis alani
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
# Kural artik TAMAMEN YOL-TABANLI: muhendis betigini KENDI WORKTREE'SINE yazar (asagidaki
# yol muafiyeti), scratchpad'e degil. Boylece kimin yazdigini tahmin etmeye gerek kalmaz.
fp = (girdi.get("tool_input") or {}).get("file_path") or ""
if not fp:
    sys.exit(0)

fp = os.path.normpath(fp)

# 1) Worktree worker'lari (Agent isolation:worktree) mesru muhendistir — TAM muaf.
#    normpath sayesinde ../ ile worktree disina cikan yol bu kontrolu gecemez (guvenli).
#    Bu kontrol icra-uzantisi kontrolunden ONCE gelmeli: muhendis .py yazabilmeli.
if "/.claude/worktrees/" in fp:
    sys.exit(0)

# 2) Calistirilabilir betik yazarligi: KONUMDAN BAGIMSIZ yasak (bugunku asil acik).
if fp.lower().endswith(ICRA_UZANTILARI):
    reddet(
        "MİMAR KOD-KİLİDİ — ÇALIŞTIRILABİLİR BETİK YAZARLIĞI YASAK (konumdan bağımsız, "
        "20 Tem): mimar kod yazmaz, kod YAZDIRIR. Scratchpad dahil hiçbir yere "
        ".py/.js/.mjs/.ts/.sh yazamazsın. ÇÖZÜM: (a) işi MÜHENDİS/USTA/MARABA'ya delege et "
        "(Agent aracı: model opus/sonnet + isolation worktree + background) ya da Codex'e ver; "
        "(b) isteğini .md SPEC'ine yaz — kural + çalıştırılabilir KABUL TESTİ dahil; "
        "(c) ölçmek istiyorsan repodaki MEVCUT aracı koştur (node tools/parite-test.js, "
        "python3 tools/d1-sync.py --durum, python3 tools/durum.py). "
        "İZİNLİ: *.md her yerde, scratchpad'de .txt/.json not/veri, /.claude/worktrees/ altı. "
        "MÜHENDİSSEN: betiğini scratchpad'e değil KENDİ WORKTREE'NE yaz "
        "(/Users/okan/dev/pruvo/.claude/worktrees/<dal>/...) — orası muaf, kalıcı ve denetlenebilir."
    )

# 3) Not/spec/veri dosyalari: serbest (mimarin asil isi).
if fp.endswith(".md"):
    sys.exit(0)

# 4) Scratchpad muafiyeti YALNIZ veri/not dosyalari icin (betikler yukarida elendi).
if fp.startswith("/private/tmp/") and "/scratchpad/" in fp:
    sys.exit(0)
if "/scratchpad/" in fp and "/claude-" in fp:
    sys.exit(0)

# 5) Repo disindaki diger dosyalar (hafiza dosyalari vb.) bu kilidin konusu degil.
if not fp.startswith(REPO_ONEKI):
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
    # Kapilar kendilerini korur. (Uzanti kurali zaten yakalar; acik kayit = regresyon kalkani:
    #  uzanti listesi bir gun daralirsa kapilar yine korunur.)
    or basename == "mimar-kod-kilidi.py"
    or basename == "mimar-icra-kapisi.py"
)

if blocked:
    reddet(
        "MİMAR KOD-KİLİDİ (Okan 18 Tem): kaynak/veri dosyasına Edit/Write YASAK — işi "
        "Codex'e ya da worktree worker'a DELEGE et, spec'i .md dosyasına yaz. Kilidin "
        "kendisini de değiştiremezsin. İzinli: *.md, scratchpad'de veri/not dosyaları, "
        "/.claude/worktrees/ altı."
    )
sys.exit(0)

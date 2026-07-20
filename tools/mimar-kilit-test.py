#!/usr/bin/env python3
"""Kabul testi: mimar kapilari (Write kilidi + Bash icra kapisi).

Her vaka kancaya GERCEK PreToolUse JSON'unu stdin'den besler ve ciktidaki
permissionDecision'a bakar. "Bakildi iyi gorunuyor" kabul degildir.

Kullanim:
    python3 tools/mimar-kilit-test.py                # repodaki kancalari test eder
    python3 tools/mimar-kilit-test.py /baska/tools   # izole kopyayi (mutasyon) test eder

Cikis kodu 0 = hepsi gecti, 1 = en az bir vaka basarisiz.
"""
import json
import os
import subprocess
import sys

TOOLS = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(
    os.path.abspath(__file__))

KILIT = os.path.join(TOOLS, "mimar-kod-kilidi.py")
ICRA = os.path.join(TOOLS, "mimar-icra-kapisi.py")

SCRATCH = "/private/tmp/claude-501/-Users-okan-dev-pruvo/2e8fe6f5-3e87-4e14-bc4d-d1447c25ea61/scratchpad"
REPO = "/Users/okan/dev/pruvo"
HAFIZA = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory"

# (no, beklenen, arac, hedef, aciklama)
VAKALAR = [
    (1, "deny", "Write", SCRATCH + "/analiz.py",
     "YENI: scratchpad'e betik yazarligi"),
    (2, "deny", "Write", REPO + "/tools/yeni.py",
     "regresyon: repo icine .py"),
    (3, "deny", "Write", REPO + "/urunler.json",
     "regresyon: urun verisi"),
    (4, "deny", "Write", REPO + "/tools/mimar-kod-kilidi.py",
     "kendini koruma (kilit)"),
    (5, "deny", "Write", REPO + "/tools/mimar-icra-kapisi.py",
     "kendini koruma (icra kapisi)"),
    (6, "deny", "Bash", "python3 " + SCRATCH + "/analiz.py",
     "YENI: kendi betigini kosturma"),
    (7, "allow", "Write", REPO + "/DEVAM.md",
     ".md her yerde serbest"),
    (8, "allow", "Write", SCRATCH + "/commit-msg.txt",
     "scratchpad veri/not dosyasi"),
    (9, "allow", "Write", HAFIZA + "/yeni-ders.md",
     "hafiza .md"),
    (10, "allow", "Write", REPO + "/.claude/worktrees/agent-x/tools/hepsi.py",
     "worktree muaf (muhendis alani)"),
    (11, "allow", "Bash", "node " + REPO + "/tools/parite-test.js",
     "mevcut repo araci (parite)"),
    (12, "allow", "Bash", "python3 " + REPO + "/tools/d1-sync.py --durum",
     "mevcut repo araci (D1 durum)"),
    (13, "allow", "Bash", "git -C " + REPO + " status -sb",
     "git durum"),
    (14, "allow", "Bash", "git -C " + REPO + " merge filan-dal",
     "MERGE = mimarin kapisi"),
    (15, "allow", "Bash", "curl -s https://pruvo3d.com/",
     "salt-okunur canli dogrulama"),
]

# Spec disi ama porozite kapatan ek vakalar (raporda ayri bolum).
EK_VAKALAR = [
    (16, "deny", "Bash", "python3 -c \"import json;print(1)\"",
     "satir-ici kod (betik yazmadan icra)"),
    (17, "deny", "Bash", "cat " + SCRATCH + "/x.py | python3",
     "stdin'den kod okutma"),
    (18, "deny", "Bash", "bash -lc \"ls -la\"",
     "kabuk satir-ici kod"),
    (19, "deny", "Write", SCRATCH + "/analiz.sh",
     "scratchpad'e kabuk betigi"),
    (20, "deny", "Bash", SCRATCH + "/analiz.sh",
     "repo disi betigi dogrudan cagirma"),
    (21, "allow", "Bash", "node --check " + REPO + "/secenekler.js",
     "sozdizimi denetimi (yargi)"),
    (22, "allow", "Bash", "python3 " + REPO + "/tools/durum.py",
     "durum panosu"),
    (23, "allow", "Bash", "git -C " + REPO + " worktree list",
     "worktree yonetimi"),
    (24, "allow", "Bash", "grep -rn WHATSAPP " + REPO + "/index.html",
     "arama/okuma"),
    (25, "allow", "Bash", "codex exec \"specteki isi yap\"",
     "Codex'e delegasyon"),
    (26, "allow", "Write", REPO + "/tools/paket-yeni-is.md",
     "muhendislik paketi (spec)"),
    (27, "allow", "Bash", "python3 " + REPO + "/tools/parite-ege.js",
     "repo araci (uzanti farketmez)"),
]

# Devir mektubu §4 MERGE PROSEDURU + §7 acik isler: mimarin uctan uca kosturmasi
# gereken KOMUTLARIN TAMAMI. Hepsi allow olmali — kapi mimari felc etmemeli.
MERGE_VAKALARI = [
    (31, "allow", "Bash", "git -C " + REPO + " fetch origin", "§4.1 fetch"),
    (32, "allow", "Bash", "git -C " + REPO + " merge-base main worktree-dal", "§4.2 kapsam"),
    (33, "allow", "Bash", "git -C " + REPO + " diff --stat abc123 HEAD", "§4.2 diff"),
    (34, "allow", "Bash", "git -C " + REPO + " merge-tree --write-tree --name-only main dal",
     "§4.3 cakisma denetimi"),
    (35, "allow", "Bash", "git -C " + REPO + " push origin main", "§4.6 push"),
    (36, "allow", "Bash", "gh run list --limit 1", "§4.7 deploy durumu"),
    (37, "allow", "Bash", "curl -sI https://pruvo3d.com/", "§4.7 canonical URL olcumu"),
    (38, "allow", "Bash", "git -C " + REPO + " worktree remove --force " + REPO + "/.claude/worktrees/agent-x",
     "§4.8 temizlik"),
    (39, "allow", "Bash", "python3 tools/gitignore-kapisi.py --yaz", "§7.1 ignore blogu (goreli yol)"),
    (40, "allow", "Bash", "python3 " + REPO + "/tools/filament-test.py", "§7.2 filament testi"),
    (41, "allow", "Bash", "python3 " + REPO + "/tools/olculmemis-siparis.py", "§7.4 siparis kapisi"),
    (42, "allow", "Bash", "node " + REPO + "/tools/parite-ege.js", "arama paritesi (Ege)"),
    (43, "allow", "Bash", "python3 tools/durum.py", "§2 durum panosu (goreli yol)"),
    (44, "allow", "Bash", "git -C " + REPO + " branch -D worktree-dal", "§4.8 dal silme"),
]

# MUHENDIS AKISI — artik OTURUM muafiyeti YOK (cwd kaydirilabilir sinyaldi, kaldirildi).
# Muhendisin serbestligi YOL-tabanli: betigini kendi worktree'sine yazar ve oradan kosturur.
# Ayni komutlar worktree cwd'sinden de ayni sonucu vermeli — muafiyet cwd'ye BAGLI DEGIL.
WORKTREE = REPO + "/.claude/worktrees/agent-x"
MUHENDIS_VAKALARI = [
    (28, "allow", "Write", WORKTREE + "/tools/analiz.py",
     "muhendis betigini WORKTREE'sine yazar"),
    (29, "allow", "Bash", "python3 " + WORKTREE + "/tools/analiz.py",
     "muhendis worktree betigini kosturur"),
    (30, "deny", "Write", SCRATCH + "/analiz.py",
     "worktree cwd'si MUAFIYET VERMEZ (cd ile kacis kapali)"),
    (45, "deny", "Bash", "python3 " + SCRATCH + "/analiz.py",
     "worktree cwd'si MUAFIYET VERMEZ (cd ile kacis kapali)"),
]

# Mimar sorusu (b) + enjeksiyon yuzeyleri.
MODUL_VAKALARI = [
    (46, "deny", "Bash", "python3 -m pip install requests",
     "-m pip: kurulum betigi kosturur"),
    (47, "deny", "Bash", "python3 -m timeit -s \"import os\" \"pass\"",
     "-m timeit -s: keyfi kod"),
    (48, "deny", "Bash", "python3 -m http.server 8000",
     "-m http.server: disari acar"),
    (49, "deny", "Bash", "python3 -m pdb " + REPO + "/tools/durum.py",
     "-m pdb: etkilesimli keyfi icra"),
    (50, "allow", "Bash", "python3 -m json.tool " + REPO + "/tools/taban-fiyatlar.js",
     "-m json.tool: izinli okuma/bicimlendirme"),
    (51, "deny", "Bash", "node --require=" + SCRATCH + "/kanca.js " + REPO + "/tools/parite-test.js",
     "bayraga gomulu repo-disi betik"),
    (52, "deny", "Bash", "PYTHONPATH=" + SCRATCH + " python3 " + REPO + "/tools/d1-sync.py --durum",
     "PYTHONPATH ile kod enjeksiyonu"),
    (53, "deny", "Bash", "NODE_OPTIONS=--require=" + SCRATCH + "/k.js node " + REPO + "/tools/parite-test.js",
     "NODE_OPTIONS ile kod enjeksiyonu"),
    (54, "allow", "Bash", "PRUVO_URUN_AI_IZNI=1 python3 " + REPO + "/tools/thing-codex.py",
     "zararsiz env atamasi ENGELLENMEZ"),
]


def kancayi_kostur(arac, hedef, cwd=REPO):
    if arac == "Bash":
        kanca = ICRA
        tool_input = {"command": hedef}
    else:
        kanca = KILIT
        tool_input = {"file_path": hedef, "content": "x"}
    payload = {
        "session_id": "test",
        "cwd": cwd,
        "hook_event_name": "PreToolUse",
        "tool_name": arac,
        "tool_input": tool_input,
    }
    ortam = dict(os.environ)
    ortam.pop("CLAUDE_PROJECT_DIR", None)
    sonuc = subprocess.run(
        [sys.executable, kanca],
        input=json.dumps(payload),
        capture_output=True, text=True, env=ortam,
    )
    cikti = sonuc.stdout.strip()
    if not cikti:
        return "allow", ""
    try:
        veri = json.loads(cikti)
    except Exception:
        return "PARSE-HATASI", cikti[:120]
    hso = veri.get("hookSpecificOutput") or {}
    return hso.get("permissionDecision", "allow"), (hso.get("permissionDecisionReason") or "")[:80]


def kume_kostur(baslik, vakalar, cwd=REPO):
    print("")
    print("=" * 78)
    print(baslik)
    print("=" * 78)
    print("{:<4} {:<7} {:<7} {:<6} {:<42}".format("No", "Beklenen", "Olculen", "Sonuc", "Vaka"))
    print("-" * 78)
    basarisiz = []
    for no, beklenen, arac, hedef, aciklama in vakalar:
        olculen, _ = kancayi_kostur(arac, hedef, cwd)
        gecti = (olculen == beklenen)
        if not gecti:
            basarisiz.append((no, beklenen, olculen, aciklama))
        print("{:<4} {:<7} {:<7} {:<6} {:<42}".format(
            no, beklenen, olculen, "OK" if gecti else "KIRMIZI", aciklama[:42]))
    return basarisiz


def main():
    for yol in (KILIT, ICRA):
        if not os.path.exists(yol):
            print("EKSIK KANCA: " + yol)
            sys.exit(1)

    b1 = kume_kostur("ZORUNLU 15 VAKA (mimar spec'i) — cwd: ana checkout (MIMAR)", VAKALAR)
    b2 = kume_kostur("EK VAKALAR (porozite kapatma) — cwd: ana checkout (MIMAR)", EK_VAKALAR)
    b3 = kume_kostur("DEVIR MEKTUBU MERGE PROSEDURU — hepsi gecmeli", MERGE_VAKALARI)
    b4 = kume_kostur("MUHENDIS AKISI — cwd: worktree (muafiyet YOK, yol-tabanli)",
                     MUHENDIS_VAKALARI, WORKTREE)
    b5 = kume_kostur("MODUL/ENJEKSIYON YUZEYI — cwd: ana checkout", MODUL_VAKALARI)

    basarisiz = b1 + b2 + b3 + b4 + b5
    print("")
    toplam = (len(VAKALAR) + len(EK_VAKALAR) + len(MERGE_VAKALARI)
              + len(MUHENDIS_VAKALARI) + len(MODUL_VAKALARI))
    if basarisiz:
        print("SONUC: {}/{} gecti — KIRMIZI vakalar:".format(toplam - len(basarisiz), toplam))
        for no, beklenen, olculen, aciklama in basarisiz:
            print("  vaka {}: beklenen={} olculen={} ({})".format(no, beklenen, olculen, aciklama))
        sys.exit(1)
    print("SONUC: {}/{} vaka GECTI.".format(toplam, toplam))
    sys.exit(0)


main()

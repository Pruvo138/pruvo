#!/usr/bin/env python3
"""Makine olursa kaybolacak yeri-doldurulamaz yerel dosyalari Drive'a yedekler.
Drive yolu tools/drive_yolu.py ile cozulur (kayitli .stl-backup-dir bayatsa kendini duzeltir).
Hedef: <Pruvo>/backup/  (memory klasoru + .urun-kaynaklari.json).

Sirlar (.thingiverse-token, .r2-credentials.json) VARSAYILAN olarak yedeklenmez;
"--sirlar" argumaniyla ayni ozel Drive'a dahil edilir (klasoru paylasma!).

Kullanim:
    python3 tools/yedekle.py            # sadece sirsiz (memory + kaynak haritasi)
    python3 tools/yedekle.py --sirlar   # + token + r2 creds
"""
import os, sys, shutil

ROOT = os.path.join(os.path.dirname(__file__), "..")
MEMORY = os.path.expanduser("~/.claude/projects/-Users-okan-dev-pruvo/memory")
SKILLS = os.path.expanduser("~/.claude/skills")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_yolu


def main():
    # --help yedekleme BASLATMASIN (denetim 2026-07-15: --help dogrudan yaziyordu).
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__.strip()); return
    # Drive yolunu drive_yolu cozer: bayatsa kendi duzeltir, mount yoksa uyarip None doner.
    # None'da DURUYORUZ — eskiden makedirs Drive yerine sahte yerel klasor yaratip "yedeklendi" diyordu.
    pruvo_drive = drive_yolu.pruvo_dizini()           # .../Pruvo
    if not pruvo_drive:
        print("Yedek ALINMADI — Drive yolu cozulemedi (yukaridaki uyariya bak)."); return
    backup = os.path.join(pruvo_drive, "backup")
    os.makedirs(os.path.join(backup, "memory"), exist_ok=True)

    # memory klasoru
    if os.path.isdir(MEMORY):
        shutil.copytree(MEMORY, os.path.join(backup, "memory"), dirs_exist_ok=True)
        print("yedek: memory/ ->", os.path.join(backup, "memory"))

    # ~/.claude/skills/ — global skill'ler (merge-kapisi dahil) GIT DISINDA tutuluyor
    # (mimar karari 21 Tem: repoya tasinmayacak) -> TEK kopya bu makinede. Yedeklenmezse
    # disk kaybinda SKILL.md + dal-olc.py + kabul-test.py (davranissal batarya) topluca gider.
    # Sir icermez, --sirlar'a bagli DEGIL. __pycache__ kopyalanmaz (turetilmis gurultu).
    if os.path.isdir(SKILLS):
        shutil.copytree(SKILLS, os.path.join(backup, "skills"), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))
        print("yedek: skills/ ->", os.path.join(backup, "skills"))

    # sirsiz kaynak haritasi
    src = os.path.join(ROOT, ".urun-kaynaklari.json")
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(backup, ".urun-kaynaklari.json"))
        print("yedek: .urun-kaynaklari.json")

    # Ajan baglam dosyasi + yarim kalan is notu. IKISI DE GITIGNORE'DA (repo public, icerik
    # ticari gizli) -> git'te KOPYASI YOK, yani bu makine olurse tamamen kaybolurlardi.
    # CLAUDE.md artik butun araclarin (Claude Code, Codex, ...) tek kural kaynagi; DEVAM.md
    # olculmus sayilari ve yarim isi tutuyor. Sir icermezler, --sirlar'a bagli DEGIL.
    # (AGENTS.md kopyalanmaz: CLAUDE.md'ye symlink, ayri dosya degil.)
    for ad in ("CLAUDE.md", "DEVAM.md", "DEVAM-ARSIV.md"):
        p = os.path.join(ROOT, ad)
        if os.path.exists(p) and not os.path.islink(p):
            shutil.copy2(p, os.path.join(backup, ad))
            print("yedek:", ad)

    if "--sirlar" in sys.argv:
        for name in (".thingiverse-token", ".r2-credentials.json", ".stl-backup-dir",
                     ".onizleme-kapat-anahtar", ".mukerrer-istisna.json"):
            p = os.path.join(ROOT, name)
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(backup, name))
                print("yedek (SIR):", name)
        print("NOT: bu klasoru kimseyle PAYLASMA — sir icerir.")

    print("bitti ->", backup)


if __name__ == "__main__":
    main()

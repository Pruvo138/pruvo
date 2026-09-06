#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kapi-envanteri-zincir-mutasyon.py — ZINCIR KOLUNUN mutasyon bataryasi.

NEDEN VAR (6 Eyl 2026, BaBa 15:1xZ hukmunun (c) maddesi + kapanis sarti):
`kapi-envanteri.py`'ye "dolayli kablolamayi bir kat izle" kolu eklendi. Bir kolun
SAYIYI dogru basmasi onun OLCTUGUNU kanitlamaz — bu batarya kolun UC ayri sekilde
YANILMADIGINI olcer. Hepsi IZOLE KOPYADA kosar:

  M1  POZITIF KONTROL — bagli bir giris noktasinin KOD duzlemine GERCEK bir cagri
      eklenir. Kol bunu GORMELI (kapi BAGLI olmali). Gormezse kol OLUDUR: 5/8'i
      8/8 yapmayan bir kol, "hep EKSIK basan" sabit bir cikti olurdu.
  M2  KORLUK KONTROLU (asil mutant) — ayni ad yalnizca YORUM ve DOCSTRING olarak
      eklenir. Kol bunu GORMEMELI. Gorurse kol tam da BaBa'nin `grep -c` hatasini
      tekrar eder: bir SILINME KAYDINI "kurulu" diye okur → SAHTE YESIL.
  M3  KOPARMA — CALISAN bir kablo (komut-stili-kapisi/settings) sokulur. Envanter
      KIRMIZI yanmali (o kapi DUSUK, toplam duser). Yesil kalirsa yeni menzil kordur.
  M4  KABUK DUZLEMI — kanca dosyasinda ad yalniz `#` yorumunda ise GORULMEMELI
      (canli `pre-commit`teki `... SILINDI` satirinin ta kendisi).

🔴 SILME YASAGI: batarya hicbir gercek ev yolunu silmez/degistirmez. Izole kopya
`shutil.copytree` ile `tempfile.mkdtemp()` altina kurulur ve TemporaryDirectory
baglaminda kendiliginden dusar; `rm -rf`/`rmtree`/`unlink` cagrisi ve gercek ev
yolu YUKU YOKTUR ([[kosum-sabiti-sahtenin-menzilinde-kalmamali]]).

Kullanim:
    python3 tools/kapi-envanteri-zincir-mutasyon.py
Cikis 0 = 4 mutantin dordu de BEKLENEN sonucu verdi (+ taban kontrolu).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import git_ortami                                             # noqa: E402

BU = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BU)              # bu worktree'nin koku
ENVANTER = os.path.join(BU, "kapi-envanteri.py")


# 🔴 SENTETIK KABLOLAMA — MAKINEYE CAPALANMAZ (6 Eyl 2026).
# `.claude/settings.json` git'te IZLENMEZ (CLAUDE.md: "kanca kablolamasi commit
# EDILMEZ"), yani CI kosucusunda YOKTUR. Makinenin dosyasi kopyalansaydi batarya
# Okan'in diskini olcerdi: yerelde yesil, CI'da kirmizi — ve ters kolda YANLIS
# YESIL ([[iki-kollu-govde-tek-sabite-capalanirsa-kosucunun-diskini-olcer]]).
# Bu yuzden kablolama BURADA URETILIR: batarya her makinede AYNI tabani olcer.
SENTETIK_SETTINGS = {
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [
                {"type": "command",
                 "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/komut-stili-kapisi.py"'}]},
            {"matcher": "Bash", "hooks": [
                {"type": "command",
                 "command": 'python3 "${CLAUDE_PROJECT_DIR:-.}/tools/urunler-guard-hook.py"'}]},
            {"matcher": "*", "hooks": [
                {"type": "command", "command": "python3 tools/icra-kapisi.py"}]},
        ]
    }
}


def _kur(gecici):
    """Izole kopya: olculecek repo iskeleti. Envanterin OKUDUGU duzlemler kurulur
    (tools kopyasi + SENTETIK settings.json + sentetik kanca dizini)."""
    kopya = os.path.join(gecici, "repo")
    os.makedirs(os.path.join(kopya, ".claude"))
    shutil.copytree(os.path.join(KOK, "tools"), os.path.join(kopya, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    with open(os.path.join(kopya, ".claude", "settings.json"), "w",
              encoding="utf-8") as f:
        json.dump(SENTETIK_SETTINGS, f, indent=2)
    # Sentetik git: KANONIK yardimci zorunlu (`tools/fikstur-git-sizinti-kapisi.py`
    # dogrudan `git init` cagrisini KIRMIZI yakar) — miras GIT_* adlari temizlenir,
    # kimlik hicbir config dosyasina yazilmaz.
    git_ortami.sentetik_git(kopya, "init", "-q", check=True,
                            capture_output=True, text=True)
    kdiz = os.path.join(kopya, ".git", "pruvo-kancalar")
    os.makedirs(kdiz, exist_ok=True)
    shutil.copy2(os.path.join(KOK, "tools", "kancalar", "pre-commit"),
                 os.path.join(kdiz, "pre-commit"))
    git_ortami.sentetik_git(kopya, "config", "core.hooksPath", ".git/pruvo-kancalar",
                            check=True, capture_output=True, text=True)
    return kopya


def _olc(kopya):
    """Envanteri izole kopya uzerinde kosur. Doner: (tam_sayi, rc, ciktida_bagli_kapilar)."""
    p = subprocess.run([sys.executable, ENVANTER, "--repo", kopya],
                       capture_output=True, text=True, timeout=600)
    cikti = p.stdout + p.stderr
    m = re.search(r"SONUC: (\d+)/(\d+) kapi", cikti)
    tam = int(m.group(1)) if m else -1
    bagli = set()
    for satir in cikti.splitlines():
        alanlar = satir.split()
        if len(alanlar) >= 5 and alanlar[1] in ("OK", "EKSIK") and alanlar[2] in ("OK", "EKSIK"):
            if alanlar[2] == "OK":
                bagli.add(alanlar[0])
    return tam, p.returncode, bagli, cikti


def _yaz(yol, metin):
    with open(yol, "a", encoding="utf-8") as f:
        f.write(metin)


VAKALAR = []


def vaka(ad, aciklama, hazirla, beklenen):
    VAKALAR.append((ad, aciklama, hazirla, beklenen))


# --- M1: POZITIF KONTROL — gercek cagri eklenir ---------------------------
def _m1(kopya):
    # `icra-kapisi.py` settings.json'da BAGLI bir giris noktasidir. Govdesine
    # GERCEK bir alt-surec cagrisi eklenir (kod duzlemi).
    _yaz(os.path.join(kopya, "tools", "icra-kapisi.py"),
         '\n\ndef _zincir_denemesi():\n'
         '    import subprocess as _sp\n'
         '    return _sp.run(["python3", "tools/mimar-kod-kilidi.py"])\n')


vaka("M1 POZITIF KONTROL", "bagli giris noktasina GERCEK cagri -> gorulmeli",
     _m1, lambda taban, sonuc: "mimar-kod-kilidi" in sonuc[2])


# --- M2: KORLUK KONTROLU — yalniz yorum + docstring -----------------------
def _m2(kopya):
    _yaz(os.path.join(kopya, "tools", "icra-kapisi.py"),
         '\n\n# mimar-kod-kilidi.py burada SILINDI (29 Agu) — bu bir YORUMDUR\n'
         'def _proza():\n'
         '    """Govde tools/mimar-kod-kilidi.py ile BIREBIR AYNI — KOPYALANDI."""\n'
         '    return 0\n')


vaka("M2 KORLUK KONTROLU", "yalniz YORUM+DOCSTRING -> GORULMEMELI (sahte yesil kolu)",
     _m2, lambda taban, sonuc: "mimar-kod-kilidi" not in sonuc[2])


# --- M3: KOPARMA — calisan kablo sokulur ----------------------------------
def _m3(kopya):
    yol = os.path.join(kopya, ".claude", "settings.json")
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    for blok in (veri.get("hooks") or {}).get("PreToolUse") or []:
        blok["hooks"] = [k for k in (blok.get("hooks") or [])
                         if "komut-stili-kapisi.py" not in (k.get("command") or "")]
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, indent=2)


vaka("M3 KOPARMA", "calisan kablo sokulur -> envanter KIRMIZI yanmali",
     _m3, lambda taban, sonuc: ("komut-stili-kapisi" not in sonuc[2]
                                and sonuc[0] < taban[0] and sonuc[1] != 0))


# --- M4: KABUK DUZLEMI — kanca yorumu -------------------------------------
def _m4(kopya):
    _yaz(os.path.join(kopya, ".git", "pruvo-kancalar", "pre-commit"),
         '\n# mimar-commit-kapisi.py SILINDI — bu satir YORUMDUR, cagri DEGIL\n')


vaka("M4 KABUK YORUMU", "kanca dosyasinda yalniz `#` yorumu -> GORULMEMELI",
     _m4, lambda taban, sonuc: "mimar-commit-kapisi" not in sonuc[2])


def main():
    print("ZINCIR KOLU MUTASYON BATARYASI — izole kopya, silme YOK")
    print("Olculen envanter: " + ENVANTER)
    with tempfile.TemporaryDirectory() as g:
        kopya = _kur(g)
        taban = _olc(kopya)
        print("\nTABAN (mutantsiz izole kopya): %d/8 kapi TAM · rc=%d" % (taban[0], taban[1]))
        print("  BAGLI cikan kapilar: %s" % ", ".join(sorted(taban[2])))
        if taban[0] < 0:
            print("🔴 TABAN OKUNAMADI — batarya hukum veremez")
            print(taban[3][-1500:])
            return 1

    gecti = 0
    for ad, aciklama, hazirla, beklenen in VAKALAR:
        with tempfile.TemporaryDirectory() as g:
            kopya = _kur(g)
            t = _olc(kopya)
            hazirla(kopya)
            s = _olc(kopya)
            ok = beklenen(t, s)
        gecti += 1 if ok else 0
        print("\n%-22s %s" % (ad, "OLDU (beklenen)" if ok else "🔴 YASADI (KOL KOR)"))
        print("  ne olcer : %s" % aciklama)
        print("  taban    : %d/8 rc=%d" % (t[0], t[1]))
        print("  mutantli : %d/8 rc=%d" % (s[0], s[1]))

    print("\nSONUC: %d/%d mutant BEKLENEN sonucu verdi." % (gecti, len(VAKALAR)))
    return 0 if gecti == len(VAKALAR) else 1


if __name__ == "__main__":
    sys.exit(main())

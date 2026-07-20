#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kabul testi: tools/kapi-envanteri.py (koruma-kapisi envanteri).

Ne dogrular:
  1) Envanter ana repoya karsi kosar ve EN AZ 5 kapi listeler.
  2) Izole kopya (git archive -> scratchpad + settings.json/.git-hooks kopyasi) kurulur;
     SAGLAM kopyada envanter exit 0 verir (kontrol: kopya sadik).
  3) KIRMIZI-MUTASYON: kopyada TEK bir kablo sokulunce (settings.json PreToolUse/Bash
     zincirinden komut-stili-kapisi kaydi silinir) envanter exit 1 verir VE yalniz o kapi
     BAGLI-EKSIK isaretlenir; dokunulmayan kapilar hala GECER.
  4) IKINCI MUTASYON: bir git-hook kablosu (pre-commit'teki mukerrer-kontrol referansi)
     kopuk hale getirilince envanter yine exit 1 verir.

ANA REPONUN settings.json / .git-hooks dosyalarina DOKUNMAZ — yalniz OKUR ve KOPYALAR.
Butun mutasyon scratchpad'deki izole kopyada yapilir.

Cikis kodu 0 = hepsi gecti, 1 = en az bir kabul basarisiz.
"""
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

MAIN = "/Users/okan/dev/pruvo"
ENV_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # bu worktree'nin koku
ENVANTER = os.path.join(ENV_KOK, "tools", "kapi-envanteri.py")


def envanter_kostur(repo):
    """Envanteri --repo <repo> ile kostur. (returncode, stdout+stderr) dondur."""
    ortam = dict(os.environ)
    for k in ("CLAUDE_PROJECT_DIR", "PRUVO_MIMAR_ONAY"):
        ortam.pop(k, None)
    sonuc = subprocess.run(
        [sys.executable, ENVANTER, "--repo", repo],
        capture_output=True, text=True, env=ortam,
    )
    return sonuc.returncode, (sonuc.stdout or "") + (sonuc.stderr or "")


def izole_kopya_kur(dst):
    """MAIN'in HEAD'indeki tools/ agacini git archive ile ac; canli (gitignore'lu)
    kablolama dosyalarini (settings.json + .git/hooks) uzerine kopyala. MAIN salt-okunur."""
    os.makedirs(dst, exist_ok=True)
    tar_yol = dst + ".tar"
    subprocess.run(
        ["git", "-C", MAIN, "archive", "--format=tar", "-o", tar_yol, "HEAD", "tools"],
        check=True, capture_output=True,
    )
    with tarfile.open(tar_yol) as t:
        t.extractall(dst, filter="data")
    os.remove(tar_yol)

    os.makedirs(os.path.join(dst, ".claude"), exist_ok=True)
    shutil.copy(os.path.join(MAIN, ".claude", "settings.json"),
                os.path.join(dst, ".claude", "settings.json"))

    os.makedirs(os.path.join(dst, ".git", "hooks"), exist_ok=True)
    for h in ("pre-commit", "pre-push"):
        kaynak = os.path.join(MAIN, ".git", "hooks", h)
        if os.path.isfile(kaynak):
            shutil.copy(kaynak, os.path.join(dst, ".git", "hooks", h))


def mutasyon_settings_kablo_sok(copy, gate_basename):
    """settings.json PreToolUse/Bash zincirinden gate_basename kaydini SIL (kablo sok)."""
    yol = os.path.join(copy, ".claude", "settings.json")
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    for blok in veri["hooks"]["PreToolUse"]:
        if blok.get("matcher") == "Bash":
            blok["hooks"] = [h for h in blok["hooks"]
                             if gate_basename not in (h.get("command") or "")]
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def mutasyon_hook_kablo_sok(copy, dosya, gate_basename):
    """.git/hooks/<dosya> icindeki gate_basename referansini kopuk hale getir."""
    yol = os.path.join(copy, ".git", "hooks", dosya)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    kopuk = gate_basename.replace(".py", "-KOPUK.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin.replace(gate_basename, kopuk))


def main():
    kontroller = []  # (ad, gecti_bool, ayrinti)

    if not os.path.isfile(ENVANTER):
        print("EKSIK: " + ENVANTER)
        return 1

    # --- 1) Ana repo: kosar + en az 5 kapi listeler ---
    ana_rc, ana_out = envanter_kostur(MAIN)
    satir_sayisi = ana_out.count("GECER") + ana_out.count("DUSUK")
    kontroller.append((
        "ana repo: envanter kosar + >=5 kapi listeler",
        satir_sayisi >= 5,
        "listelenen kapi satiri=%d, exit=%d" % (satir_sayisi, ana_rc),
    ))
    kontroller.append((
        "ana repo: mevcut durumda tum kapilar nobette (exit 0)",
        ana_rc == 0,
        "exit=%d (0 beklenir; degilse gercek bir kapi dusuktur)" % ana_rc,
    ))

    kok = tempfile.mkdtemp(prefix="kapi-envanteri-izole-")
    try:
        # --- 2) Saglam izole kopya: baseline exit 0 (kontrol) ---
        copy = os.path.join(kok, "repo")
        izole_kopya_kur(copy)
        base_rc, base_out = envanter_kostur(copy)
        kontroller.append((
            "izole kopya SAGLAM: baseline exit 0",
            base_rc == 0,
            "exit=%d (kopya sadik degilse mutasyon kaniti gecersiz olurdu)" % base_rc,
        ))

        # --- 3) KIRMIZI-MUTASYON: settings.json'dan komut-stili kablosu sokulur ---
        copy_m1 = os.path.join(kok, "repo-m1")
        izole_kopya_kur(copy_m1)
        mutasyon_settings_kablo_sok(copy_m1, "komut-stili-kapisi.py")
        m1_rc, m1_out = envanter_kostur(copy_m1)
        # komut-stili satiri DUSUK olmali, dokunulmayan bir kapi (mimar-icra) hala GECER olmali
        komut_dusuk = ("komut-stili-kapisi" in m1_out
                       and any(s.strip().startswith("komut-stili-kapisi") and "DUSUK" in s
                               for s in m1_out.splitlines()))
        icra_gecer = any(s.strip().startswith("mimar-icra-kapisi") and "GECER" in s
                         for s in m1_out.splitlines())
        kontroller.append((
            "KIRMIZI-MUTASYON (settings kablo sok): exit 1",
            m1_rc == 1,
            "exit=%d (saglam kopya 0 idi -> mutasyon 1'e cevirdi)" % m1_rc,
        ))
        kontroller.append((
            "mutasyon HEDEFLI: yalniz komut-stili dusuk, mimar-icra hala GECER",
            komut_dusuk and icra_gecer,
            "komut-stili-dusuk=%s mimar-icra-gecer=%s" % (komut_dusuk, icra_gecer),
        ))
        kontroller.append((
            "mutasyon ciktisi 'BAGLI degil' gerekcesini yaziyor",
            "BAGLI degil" in m1_out and "komut-stili-kapisi" in m1_out,
            "eksik listesi net",
        ))

        # --- 4) IKINCI MUTASYON: git-hook kablosu (pre-commit/mukerrer) kopuk ---
        copy_m2 = os.path.join(kok, "repo-m2")
        izole_kopya_kur(copy_m2)
        mutasyon_hook_kablo_sok(copy_m2, "pre-commit", "mukerrer-kontrol.py")
        m2_rc, m2_out = envanter_kostur(copy_m2)
        mukerrer_dusuk = any(s.strip().startswith("mukerrer-kontrol") and "DUSUK" in s
                             for s in m2_out.splitlines())
        kontroller.append((
            "IKINCI MUTASYON (git-hook kablo sok): exit 1 + mukerrer dusuk",
            m2_rc == 1 and mukerrer_dusuk,
            "exit=%d mukerrer-dusuk=%s" % (m2_rc, mukerrer_dusuk),
        ))
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    # --- Ozet ---
    print("=" * 74)
    print("KAPI-ENVANTERI KABUL TESTI")
    print("=" * 74)
    basarisiz = 0
    for ad, gecti, ayrinti in kontroller:
        print("[%s] %s" % ("OK  " if gecti else "KIRMIZI", ad))
        print("        -> " + ayrinti)
        if not gecti:
            basarisiz += 1
    print("-" * 74)
    if basarisiz:
        print("SONUC: %d/%d kontrol gecti — %d KIRMIZI." % (
            len(kontroller) - basarisiz, len(kontroller), basarisiz))
        return 1
    print("SONUC: %d/%d kontrol GECTI." % (len(kontroller), len(kontroller)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

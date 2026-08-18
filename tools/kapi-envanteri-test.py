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
import importlib.util
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

MAIN = "/Users/okan/dev/pruvo"
ENV_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # bu worktree'nin koku
ENVANTER = os.path.join(ENV_KOK, "tools", "kapi-envanteri.py")


def probe_yukle(yol):
    spec = importlib.util.spec_from_file_location("k141_probe", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fikstur_yaz(kok):
    os.makedirs(kok, exist_ok=True)
    fikstur = {}
    kaynak = {
        "V1": 'import json; print(json.dumps({"hookSpecificOutput": {"permissionDecision": "deny"}}))',
        "V2": 'import json; print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))',
        "V3": 'pass',
        "V4": 'import sys; sys.stderr.write("K141-V4-STDERR\\n"); sys.exit(1)',
        "V5": 'print("K141-bozuk-json")',
        "V4RC": 'import json, sys; print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}})); sys.exit(1)',
    }
    for ad, govde in kaynak.items():
        yol = os.path.join(kok, ad + ".py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env python3\n" + govde + "\n")
        fikstur[ad] = yol
    return fikstur


def tek_karar(mod, yol):
    return mod._karar_olc(yol, {}, "Bash")


def mutant_kopya(kok, ad, eski, yeni):
    yol = os.path.join(kok, ad + ".py")
    with open(ENVANTER, encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(eski) != 1:
        raise AssertionError("mutasyon capa metni benzersiz degil: " + ad)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(eski, yeni))
    return yol


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


# 🔴 `ENV_KOK` (bu worktree'nin koku), `MAIN` DEGIL: konvansiyon DALIN kendi
# agacinda olculmeli — yoksa dalda eklenen konvansiyon disi bir nobetci ancak
# MERGE'ten sonra gorunur ve sabit mutlak yol CI'da hic cozulmez
# ([[sabit-mutlak-yol-yerelde-yesil]]).
def main():
    kontroller = []  # (ad, gecti_bool, ayrinti)
    vakalar = []
    mutantlar = []
    kontroller_k141 = []

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
        "ana repo: envanter rc olculdu",
        ana_rc in (0, 1),
        "exit=%d" % ana_rc,
    ))

    kok = tempfile.mkdtemp(prefix="kapi-envanteri-izole-")
    try:
        # --- 2) Saglam izole kopya: baseline exit 0 (kontrol) ---
        copy = os.path.join(kok, "repo")
        izole_kopya_kur(copy)
        base_rc, base_out = envanter_kostur(copy)
        kontroller.append((
            "izole kopya SAGLAM: baseline ana repo ile ayni",
            base_rc == ana_rc,
            "exit=%d ana-exit=%d (kopya sadikligi)" % (base_rc, ana_rc),
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
        icra_gecer = any(s.strip().startswith("mimar-icra-kapisi") and "DUSUK" in s
                         for s in m1_out.splitlines())
        kontroller.append((
            "KIRMIZI-MUTASYON (settings kablo sok): exit 1",
            m1_rc == 1,
            "exit=%d (saglam kopya ana rc ile ayni; mutasyon 1'e cevirdi)" % m1_rc,
        ))
        kontroller.append((
            "mutasyon HEDEFLI: komut-stili dusuk, mimar-icra durumu korunuyor",
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

        # --- 5) K141 sentetik karar vakalari ---
        fikstur = fikstur_yaz(os.path.join(kok, "fikstur"))
        probe = probe_yukle(ENVANTER)
        beklenen = {
            "V1": "deny",
            "V2": "allow",
            "V3": "OLCULEMEDI",
            "V4": "OLCULEMEDI",
            "V5": "OLCULEMEDI",
        }
        for ad, jeton in beklenen.items():
            olcum = tek_karar(probe, fikstur[ad])
            stderr_ok = ad != "V4" or "K141-V4-STDERR" in olcum[2]
            gecti = olcum[0] == jeton and stderr_ok
            vakalar.append((ad, gecti, "jeton=%s rc=%s stderr=%s" % olcum))
            kontroller.append(("%s karar vakasi" % ad, gecti, vakalar[-1][2]))

        # --- 6) K141 mutant bataryasi: her mutant tek davranisi oldurur ---
        m1 = mutant_kopya(
            kok, "mutant-m1",
            'if sonuc.returncode != 0 or not cikti:\n        return "OLCULEMEDI", sonuc.returncode, stderr_ilk',
            'if not cikti:\n        return "allow", sonuc.returncode, stderr_ilk',
        )
        m1_probe = probe_yukle(m1)
        m1_red = tek_karar(m1_probe, fikstur["V3"])[0] == "allow"
        mutantlar.append(("M1", m1_red, "V3 dusuruldu=%s" % m1_red))

        m2 = mutant_kopya(
            kok, "mutant-m2",
            'if sonuc.returncode != 0 or not cikti:\n        return "OLCULEMEDI", sonuc.returncode, stderr_ilk',
            'if not cikti:\n        return "OLCULEMEDI", sonuc.returncode, stderr_ilk',
        )
        m2_probe = probe_yukle(m2)
        m2_red = tek_karar(m2_probe, fikstur["V4RC"])[0] == "allow"
        mutantlar.append(("M2", m2_red, "V4 returncode vakasi dusuruldu=%s" % m2_red))

        m3 = mutant_kopya(
            kok, "mutant-m3",
            'if eksik_rapor:\n',
            'if False and eksik_rapor:\n',
        )
        m3_sonuc = subprocess.run(
            [sys.executable, m3, "--repo", MAIN],
            capture_output=True, text=True,
        )
        m3_red = ana_rc != 0 and m3_sonuc.returncode == 0
        mutantlar.append(("M3", m3_red, "OLCULEMEDI rc0 mutant=%s" % m3_red))
        for ad, gecti, ayrinti in mutantlar:
            kontroller.append((ad + " mutant", gecti, ayrinti))

        # --- 7) Yanlis-pozitif nobetcisi ---
        k1 = tek_karar(probe, fikstur["V2"])[0] == "allow"
        kontroller_k141.append(("K1", k1, "V2 allow=%s" % k1))
        kapsam = tuple(g["ad"] for g in probe.GATES)
        beklenen_kapsam = (
            "komut-stili-kapisi", "urunler-guard-hook", "mimar-icra-kapisi",
            "mimar-kod-kilidi", "urunler-guard", "mukerrer-kontrol",
            "mimar-commit-kapisi",
        )
        k2 = kapsam == beklenen_kapsam
        kontroller_k141.append(("K2", k2, "kapsam-korundu=%s" % k2))
        for ad, gecti, ayrinti in kontroller_k141:
            kontroller.append((ad + " kontrol", gecti, ayrinti))
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
        print("VAKA=%d DUSEN=%d MUTANT=%d/3 KONTROL=%d/2" % (
            len(vakalar), sum(not x[1] for x in vakalar),
            sum(x[1] for x in mutantlar), sum(x[1] for x in kontroller_k141)))
        return 1
    print("SONUC: %d/%d kontrol GECTI." % (len(kontroller), len(kontroller)))
    print("VAKA=%d DUSEN=%d MUTANT=%d/3 KONTROL=%d/2" % (
        len(vakalar), sum(not x[1] for x in vakalar),
        sum(x[1] for x in mutantlar), sum(x[1] for x in kontroller_k141)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

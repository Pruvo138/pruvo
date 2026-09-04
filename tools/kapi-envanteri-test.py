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
        "V3b": 'import sys; sys.exit(1)',
        "V6": 'pass',
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


def envanter_kostur(repo, ek_env=None, betik=None):
    """Envanteri --repo <repo> ile kostur. (returncode, stdout+stderr) dondur.

    `ek_env` ile ISCI baglami simule edilir (K219): `PRUVO_ISCI_KOSUMU` mirasla alt
    surece gecerse kapilar `allow ISCI(...)` doner; prob bunu "REDDETMEDI" diye
    yazmamali. Taban kosumda o degisken BILEREK silinir ki mimar/isci farki OLCULEBILIR
    olsun (yoksa cagiran oturumun ambiyansi olcumu belirlerdi)."""
    ortam = dict(os.environ)
    for k in ("CLAUDE_PROJECT_DIR", "PRUVO_MIMAR_ONAY",
              "PRUVO_ISCI_KOSUMU", "PRUVO_CLAUDE_ISCI_IZNI"):
        ortam.pop(k, None)
    if ek_env:
        ortam.update(ek_env)
    sonuc = subprocess.run(
        [sys.executable, betik or ENVANTER, "--repo", repo],
        capture_output=True, text=True, env=ortam,
    )
    return sonuc.returncode, (sonuc.stdout or "") + (sonuc.stderr or "")


def _kapi_satiri(cikti, kapi_adi):
    """Envanter tablosundaki O kapinin satiri (girintisiz, kapi adiyla BASLAYAN).
    Bulunamazsa "" — cagiran taraf bunu KIRMIZI sayar."""
    for satir in cikti.splitlines():
        if satir.startswith(kapi_adi + " ") or satir.rstrip() == kapi_adi:
            return satir
    return ""


def _kapi_rapor_satirlari(cikti, kapi_adi):
    """EKSIKLER listesindeki (girintili "  - <kapi>: ...") satirlar."""
    return [s for s in cikti.splitlines() if s.strip().startswith("- " + kapi_adi + ":")]


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

    # Prob modulu ERKEN yuklenir: kapi adlari (GATES) ve jetonlar (OLCULEMEDI /
    # MUAF_BAGLAM) tablodan TURETILSIN, teste elle kopyalanmasin.
    probe = probe_yukle(ENVANTER)
    KAPI_ADLARI = tuple(g["ad"] for g in probe.GATES)

    # --- 1) Ana repo: kosar + en az 5 kapi listeler ---
    ana_rc, ana_out = envanter_kostur(MAIN)
    satir_sayisi = sum(1 for s in ana_out.splitlines()
                       if any(s.startswith(ad + " ") for ad in KAPI_ADLARI))
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
        icra_gecer = any(s.strip().startswith("mimar-icra-kapisi") and "GECER" in s
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
        beklenen = {
            "V1": "deny",
            "V2": "allow",
            "V3": "allow-SESSIZ",
            "V3b": "OLCULEMEDI",
            "V4": "OLCULEMEDI",
            "V5": "OLCULEMEDI",
        }
        for ad, jeton in beklenen.items():
            olcum = tek_karar(probe, fikstur[ad])
            stderr_ok = ad != "V4" or "K141-V4-STDERR" in olcum[2]
            gecti = olcum[0] == jeton and stderr_ok
            vakalar.append((ad, gecti, "jeton=%s rc=%s stderr=%s" % olcum))
            kontroller.append(("%s karar vakasi" % ad, gecti, vakalar[-1][2]))

        v6_red_ok, v6_kabul_ok, v6_ayrinti = probe._nobet_karar(
            fikstur["V6"], {"red": {}, "kabul": {}, "tool_name": "Bash"})
        v6_gecti = (not v6_red_ok) and v6_kabul_ok
        vakalar.append(("V6", v6_gecti, "red-ekseni gecmedi=%s ayrinti=%s" % (
            not v6_red_ok, v6_ayrinti)))
        kontroller.append(("V6 red ekseni sessiz izin red degil", v6_gecti, vakalar[-1][2]))

        # --- 6) K141 mutant bataryasi: her mutant tek davranisi oldurur ---
        m1 = mutant_kopya(
            kok, "mutant-m1",
            'if not cikti and sonuc.returncode == 0:\n        return "allow-SESSIZ", sonuc.returncode, stderr_ilk',
            'if False and not cikti and sonuc.returncode == 0:\n        return "allow-SESSIZ", sonuc.returncode, stderr_ilk',
        )
        m1_probe = probe_yukle(m1)
        m1_red = tek_karar(m1_probe, fikstur["V3"])[0] == "OLCULEMEDI"
        mutantlar.append(("M1", m1_red, "V3 dusuruldu=%s" % m1_red))

        m2 = mutant_kopya(
            kok, "mutant-m2",
            'if sonuc.returncode != 0 or not cikti:\n        return OLCULEMEDI, sonuc.returncode, stderr_ilk',
            'if not cikti:\n        return OLCULEMEDI, sonuc.returncode, stderr_ilk',
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
            [sys.executable, m3, "--repo", copy_m1],
            capture_output=True, text=True,
        )
        m3_red = m1_rc == 1 and m3_sonuc.returncode == 0
        mutantlar.append(("M3", m3_red, "DUSUK raporu rc0 mutant=%s" % m3_red))

        m4 = mutant_kopya(
            kok, "mutant-m4",
            'red_ok = (red == "deny")',
            'red_ok = (red in ("deny", "allow-SESSIZ"))',
        )
        m4_probe = probe_yukle(m4)
        m4_red = m4_probe._nobet_karar(
            fikstur["V6"], {"red": {}, "kabul": {}, "tool_name": "Bash"})[0]
        mutantlar.append(("M4", m4_red, "V6 dusuruldu=%s" % m4_red))

        m5 = mutant_kopya(
            kok, "mutant-m5",
            'if not cikti and sonuc.returncode == 0:',
            'if not cikti:',
        )
        m5_probe = probe_yukle(m5)
        m5_red = tek_karar(m5_probe, fikstur["V3b"])[0] == "allow-SESSIZ"
        mutantlar.append(("M5", m5_red, "V3b dusuruldu=%s" % m5_red))

        m6 = mutant_kopya(
            kok, "mutant-m6",
            'kabul_ok = (kabul in ("allow", "allow-SESSIZ"))',
            'kabul_ok = (kabul == "allow")',
        )
        m6_probe = probe_yukle(m6)
        m6_red = not m6_probe._nobet_karar(
            fikstur["V3"], {"red": {}, "kabul": {}, "tool_name": "Bash"})[1]
        mutantlar.append(("M6", m6_red, "V3 dusuruldu=%s" % m6_red))
        # --- 6b) K219: PROB KENDI BAGLAMINI DEGIL, KAPININ MIMAR DAVRANISINI OLCER ---
        # 🔴 OLCULMUS KUSUR: prob sentetik cagriyi kendi baglaminda kuruyordu. Bir isci
        # turunda kostugunda `PRUVO_ISCI_KOSUMU` mirasla alt surece geciyor, kapilar
        # DOGRU davranip `allow ISCI(sarmalayici:kimi)` donuyor, prob de bunu
        # "reddetmesi gerekeni REDDETMEDI" diye yaziyordu (K206 merge chip'i: `5/7 kapi
        # TAM`, rc=1 — oysa AYNI kapi o oturumda fiilen 4 kez reddetmisti).
        ISCI_ENV = {"PRUVO_ISCI_KOSUMU": "kimi"}
        KIMLIK_KAPILARI = ("mimar-icra-kapisi", "mimar-kod-kilidi")

        isci_rc, isci_out = envanter_kostur(MAIN, ek_env=ISCI_ENV)
        kontroller.append((
            "K219-a: hukum BAGLAMDAN BAGIMSIZ — ISCI kosumunun rc'si MIMAR kosumuyla AYNI",
            isci_rc == ana_rc,
            "isci-exit=%d mimar-exit=%d" % (isci_rc, ana_rc),
        ))
        for kapi in KIMLIK_KAPILARI:
            m_satir = _kapi_satiri(ana_out, kapi)
            i_satir = _kapi_satiri(isci_out, kapi)
            i_reddetmedi = any("REDDETMEDI" in s
                               for s in _kapi_rapor_satirlari(isci_out, kapi))
            kontroller.append((
                "K219-a: %s — ISCI baglaminda 'REDDETMEDI' BASILMAZ, satir MIMAR "
                "baglamiyla BIREBIR ayni" % kapi,
                bool(i_satir) and i_satir == m_satir and not i_reddetmedi,
                "isci=%r mimar=%r reddetmedi=%s" % (i_satir.strip(), m_satir.strip(),
                                                    i_reddetmedi),
            ))
            kontroller.append((
                "K219-b: %s — MIMAR baglaminda NOBETTE TAM (GECER)" % kapi,
                "GECER" in m_satir,
                "satir=%r" % m_satir.strip(),
            ))
        kontroller.append((
            "K219-b: MIMAR baglaminda ana repo envanteri rc=0 (taban olcumu)",
            ana_rc == 0,
            "exit=%d — kirmiziysa gerekce EKSIKLER listesindedir" % ana_rc,
        ))

        # NEGATIF: GERCEKTEN olu bir kapi (her cagriya `allow`) hala KIRMIZI kalmali ve
        # "REDDETMEDI" YAZMALI — MUAF_BAGLAM'a KACMAMALI. Bu, K219 onariminin kapiyi
        # gevsetmedigini olcer (sahte yesil, sahte kirmizidan beterdir).
        olu_red_ok, olu_kabul_ok, olu_ayrinti = probe._nobet_karar(
            fikstur["V2"], {"red": {}, "kabul": {}, "tool_name": "Bash"})
        kontroller.append((
            "K219-c NEGATIF: her cagriya allow diyen OLU kapi hala KIRMIZI "
            "(MUAF_BAGLAM'a KACMAZ)",
            olu_red_ok is False and olu_kabul_ok is True
            and probe.MUAF_BAGLAM not in olu_ayrinti,
            "red_ok=%r kabul_ok=%r ayrinti=%s" % (olu_red_ok, olu_kabul_ok, olu_ayrinti),
        ))

        # MUAF_BAGLAM vakasi: izole kopyanin kimlik eksenine SOKULEMEZ bir kol eklenir
        # (ne payload ne ortam ile kapatilabilir). Prob "kapi olu" DEMEMELI, "yesil" de.
        copy_muaf = os.path.join(kok, "repo-muaf")
        izole_kopya_kur(copy_muaf)
        kimlik_yolu = os.path.join(copy_muaf, "tools", "mimar_kimlik.py")
        with open(kimlik_yolu, encoding="utf-8") as f:
            kimlik_kaynak = f.read()
        muaf_capa = '    aid = girdi.get("agent_id")'
        muaf_kuruldu = kimlik_kaynak.count(muaf_capa) == 1
        if muaf_kuruldu:
            with open(kimlik_yolu, "w", encoding="utf-8") as f:
                f.write(kimlik_kaynak.replace(
                    muaf_capa,
                    '    if os.path.exists(os.sep):\n'
                    '        return "sokulemez-eksen"\n' + muaf_capa, 1))
        muaf_rc, muaf_out = envanter_kostur(copy_muaf, ek_env=ISCI_ENV)
        muaf_satirlar = [_kapi_satiri(muaf_out, k) for k in KIMLIK_KAPILARI]
        kontroller.append((
            "K219-d: kimlik ekseni SOKULEMEZ -> jeton %s; 'REDDETMEDI' BASILMAZ, "
            "rc de YESIL degil" % probe.MUAF_BAGLAM,
            muaf_kuruldu and muaf_rc == 1
            and all(probe.MUAF_BAGLAM in s for s in muaf_satirlar)
            and "REDDETMEDI" not in muaf_out,
            "capa=%s exit=%d satirlar=%r" % (
                muaf_kuruldu, muaf_rc, [s.strip() for s in muaf_satirlar]),
        ))
        kontroller.append((
            "K219-e: jeton AYRIKLIGI — %s ⊄ %s ve tersi (biri digerinin alt dizesi "
            "olamaz)" % (probe.MUAF_BAGLAM, probe.OLCULEMEDI),
            probe.MUAF_BAGLAM not in probe.OLCULEMEDI
            and probe.OLCULEMEDI not in probe.MUAF_BAGLAM,
            "MUAF_BAGLAM=%r OLCULEMEDI=%r" % (probe.MUAF_BAGLAM, probe.OLCULEMEDI),
        ))

        # M7/M8 — K219'un IKI kolu, HER BIRI KENDI HEDEF KOLUNU ayri kanitlar ([[K182]]).
        m7 = mutant_kopya(
            kok, "mutant-m7",
            "    for ad in anahtarlar:\n        ortam.pop(ad, None)\n"
            "        payload.pop(ad, None)",
            "    for ad in ():\n        ortam.pop(ad, None)\n"
            "        payload.pop(ad, None)",
        )
        _m7_rc, m7_out = envanter_kostur(MAIN, ek_env=ISCI_ENV, betik=m7)
        m7_satirlar = [_kapi_satiri(m7_out, k) for k in KIMLIK_KAPILARI]
        m7_red = all(probe.MUAF_BAGLAM in s for s in m7_satirlar)
        mutantlar.append((
            "M7", m7_red,
            "HEDEF KOL=kimlik SOKUMU. Taban: ISCI baglaminda iki kimlik kapisi GECER "
            "(%r). Mutant: %s (%r)" % (
                [_kapi_satiri(isci_out, k).split()[-1] for k in KIMLIK_KAPILARI],
                probe.MUAF_BAGLAM, [s.split()[-1] if s else "" for s in m7_satirlar])))

        m8 = mutant_kopya(
            kok, "mutant-m8",
            "    if kalan is not None:\n        return MUAF_BAGLAM, 0, (",
            "    if False and kalan is not None:\n        return MUAF_BAGLAM, 0, (",
        )
        _m8_rc, m8_out = envanter_kostur(copy_muaf, ek_env=ISCI_ENV, betik=m8)
        m8_satirlar = [_kapi_satiri(m8_out, k) for k in KIMLIK_KAPILARI]
        m8_red = ("REDDETMEDI" in m8_out
                  and not any(probe.MUAF_BAGLAM in s for s in m8_satirlar))
        mutantlar.append((
            "M8", m8_red,
            "HEDEF KOL=kimlik DOGRULAMASI. Taban: sokulemez eksende hukum %s. "
            "Mutant: sahte kirmizi geri geldi (REDDETMEDI=%s, %s=%s)" % (
                probe.MUAF_BAGLAM, "REDDETMEDI" in m8_out, probe.MUAF_BAGLAM,
                any(probe.MUAF_BAGLAM in s for s in m8_satirlar))))

        for ad, gecti, ayrinti in mutantlar:
            kontroller.append((ad + " mutant", gecti, ayrinti))

        # --- 7) Yanlis-pozitif nobetcisi ---
        k1 = tek_karar(probe, fikstur["V2"])[0] == "allow"
        kontroller_k141.append(("K1", k1, "V2 allow=%s" % k1))
        kapsam = tuple(g["ad"] for g in probe.GATES)
        # 🔴 KAPSAM CIVISI — gevsetilmez, YENIDEN CIVILENIR. Bu demet envanterin
        # kapsam tabanini SAYIYLA baglar; yeni bir kapi eklendiginde burasi
        # BILEREK guncellenir, aksi halde kapsam sessizce kayar
        # ([[batarya-kapsam-tabani-sayiyla-civilenir]]).
        # 4 Eyl 2026: `icra-kapisi` eklendi (Okan hukmu — ANA oturumda `Agent`
        # alt-ajani reddi). 7 -> 8. SIRA da baglayicidir.
        beklenen_kapsam = (
            "komut-stili-kapisi", "urunler-guard-hook", "mimar-icra-kapisi",
            "icra-kapisi",
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
        print("VAKA=%d DUSEN=%d MUTANT=%d/%d KONTROL=%d/2" % (
            len(vakalar), sum(not x[1] for x in vakalar),
            sum(x[1] for x in mutantlar), len(mutantlar),
            sum(x[1] for x in kontroller_k141)))
        return 1
    print("SONUC: %d/%d kontrol GECTI." % (len(kontroller), len(kontroller)))
    print("VAKA=%d DUSEN=%d MUTANT=%d/%d KONTROL=%d/2" % (
        len(vakalar), sum(not x[1] for x in vakalar),
        sum(x[1] for x in mutantlar), len(mutantlar),
        sum(x[1] for x in kontroller_k141)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

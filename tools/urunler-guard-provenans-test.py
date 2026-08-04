#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/urunler-guard-provenans-test.py — urunler-guard'in PROVENANS + FAIL-LOUD kabulu.

NE OLCER (4 Agu 2026 olayi): bir muhendis worktree'sinde `origin/main` dala merge
edilirken guard, merge'in GETIRDIGI guncel katalogu dalin BAYAT haline SESSIZCE
GERI SARDI (5 ekleme / 11 silme; bir uründen `lisans` blogu + gorsel dustu).
Cikis kodu 0, stdout/stderr BOS — HICBIR KAPI CALMADI. Bu test o olayi GERCEK git
depolari uzerinde yeniden kurar ve iki ilkeyi OLCER:

  ILKE 1 PROVENANS  — merge getirisi izinsiz degisim DEGILDIR (P*, M*).
  ILKE 2 FAIL-LOUD  — provenans cozulemiyorsa SESSIZ MUTASYON degil RED (B*, E1).

🔴 YANLIS-POZITIF BUTCESI — dort eksen de burada olculur:
  KORUMA KORELMEDI   K1 K2   (izinsiz degisim/silme HALA yakalaniyor)
  MESRU PARTI GECER  N1 K3   (yeni urun partisi + beyanli duzeltme GECER)
  MERGE GETIRISI     P1..P5 M1 M2 M3
  BELIRSIZ DURDURUR  B1..B5

GERCEK VERIYE DOKUNMAZ: her senaryo kendi gecici git deposunu kurar; fikstur
urunleri SAHTEDIR (gercek katalogdan kopyalanmaz). Sabit GIT_*_DATE kullanilir.
Ag YOK.

KABUL = CIKIS KODU DEGIL, BASILAN IDDIA SAYISI: her kosumda TAM 22 `IDDIA:`
satiri basilir (olculemeyen iddia KIRMIZI + "OLCULEMEDI" olarak basilir, sayi
DUSMEZ — cokme kirmiziyla karismaz).

Kullanim:
    python3 tools/urunler-guard-provenans-test.py
    python3 tools/urunler-guard-provenans-test.py --kaynak <mutasyonlu-guard.py>
    python3 tools/urunler-guard-provenans-test.py --kaynak-kopru <mutasyonlu-kopru.py>
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
VARSAYILAN_GUARD = os.path.join(TOOLS, "urunler-guard.py")
VARSAYILAN_KOPRU = os.path.join(TOOLS, "urunler-guard-hook.py")

ISO = "2026-08-04T12:00:00+0000"

# --------------------------------------------------------------------------
# IDDIA DEFTERI — kodlar SABIT ve SIRALIDIR; sayi hicbir kosumda degismez.
# --------------------------------------------------------------------------
KODLAR = [
    ("P1", "merge replay: katalog BYTE-ESIT kalir (geri sarma YOK)"),
    ("P2", "merge replay: lisans blogu (atif) KORUNUR"),
    ("P3", "merge replay: gorsel sayisi KORUNUR"),
    ("P4", "merge replay: aciklama uzunlugu KORUNUR"),
    ("P5", "merge replay: guard rc=0"),
    ("M1", "merge: main'in SILDIGI urun geri EKLENMEZ"),
    ("M2", "merge: main'in EKLEDIGI yeni urun dokunulmaz kalir"),
    ("M3", "merge: manifest-BEYANLI duzeltme KORUNUR"),
    ("K1", "KORUMA: merge DISI izinsiz alan degisimi HEAD'e geri sarilir"),
    ("K2", "KORUMA: merge DISI izinsiz silme geri EKLENIR"),
    ("K3", "YP: merge DISI manifest-beyanli degisim KORUNUR"),
    ("N1", "YP: mesru parti (yeni urun BASA) dokunulmadan GECER + sira korunur"),
    ("G1", "GORUNURLUK: geri sarma stderr'e urun+alan adiyla BASILIR"),
    ("B1", "FAIL-LOUD: merge'de iki ebeveyne de uymayan hal -> rc!=0"),
    ("B2", "FAIL-LOUD: o halde katalog BYTE-ESIT kalir (sessiz mutasyon YOK)"),
    ("B3", "FAIL-LOUD: WT BOZUK JSON -> rc!=0 ve dosya BYTE-ESIT"),
    ("B4", "FAIL-LOUD: MERGE_HEAD katalogu okunamiyor -> rc!=0"),
    ("B5", "FAIL-LOUD: red GEREKCESI stderr'e basilir"),
    ("B6", "FAIL-LOUD: guard'in KENDI beklenmedik hatasi -> rc!=0 (fail-open YOK)"),
    ("E1", "CIKIS[ZORLA]: surec env'inde PRUVO_GUARD_ZORLA=1 -> rc=0, veri YINE degismez"),
    ("E2", "CIKIS[MANIFEST]: beyan edilen degisim -> rc=0 ve WT hali AYNEN kalir"),
    ("E3", "CIKIS[EBEVEYN]: ebeveynin hali AYNEN secilince -> rc=0, byte-esit"),
    ("E4", "IKIZ TANIM: basilan metin CIKIS_YOLLARI'nin HER kodunu tasir + "
           "yaniltici komut-onu env bicimi UYARIYLA isaretli"),
    ("H1", "KOPRU: guard rc!=0 -> PreToolUse rc=2 (git komutu BLOKLANIR)"),
    ("H2", "KOPRU: guard rc=0 -> PreToolUse rc=0 (mesru commit gecer)"),
    ("H3", "KOPRU: git-disi komut -> rc=0 VE guard HIC kosmaz (log yazilmaz)"),
]

DEFTER = {}


def iddia(kod, kosul, ayrinti=""):
    DEFTER[kod] = (bool(kosul), ayrinti)


# --------------------------------------------------------------------------
# SAHTE FIKSTUR — gercek katalogdan KOPYALANMAZ. Olayin iki Berlingo urununun
# SEKLINI (lisans blogu + coklu gorsel + uzun aciklama) tasir, verisini DEGIL.
# --------------------------------------------------------------------------
def _urun(uid, gorsel=1, lisans=False, aciklama="kisa aciklama", fiyat="100 TL"):
    p = {
        "id": uid,
        "kategori": "Otomobil",
        "marka": ["Sahtemarka"],
        "baslik": "Sahte Parca %s" % uid,
        "aciklama": aciklama,
        "fiyat": fiyat,
        "gorseller": ["https://media.pruvo3d.com/urunler/%s-%d.jpg" % (uid, i + 1)
                      for i in range(gorsel)],
    }
    if lisans:
        p["lisans"] = {"tasarimci": "sahte-tasarimci", "tur": "GNU GPL v2.0"}
    return p


BAYAT = _urun("sahte-tavan-kilidi", gorsel=1, lisans=False,
              aciklama="bayat kisa aciklama")
GUNCEL = _urun("sahte-tavan-kilidi", gorsel=2, lisans=True,
               aciklama="guncel, cok daha uzun ve duzeltilmis aciklama metni")
IKINCI = _urun("sahte-tavan-kutusu-kilidi", gorsel=2, lisans=True,
               aciklama="ikinci urunun aciklamasi")


# --------------------------------------------------------------------------
# GIT / DEPO YARDIMCILARI
# --------------------------------------------------------------------------
def _env():
    return dict(os.environ,
                GIT_AUTHOR_DATE=ISO, GIT_COMMITTER_DATE=ISO,
                GIT_AUTHOR_NAME="Kabul", GIT_AUTHOR_EMAIL="kabul@pruvo.test",
                GIT_COMMITTER_NAME="Kabul", GIT_COMMITTER_EMAIL="kabul@pruvo.test")


def g(kok, *a):
    p = subprocess.run(["git", "-C", kok, *a], capture_output=True,
                       text=True, env=_env())
    return p.returncode, p.stdout + p.stderr


def yaz_katalog(kok, liste):
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=2)


def oku_katalog(kok):
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        return json.load(f)


def sha(kok, ad="urunler.json"):
    with open(os.path.join(kok, ad), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def kur_depo(guard, kopru, katalog):
    d = tempfile.mkdtemp(prefix="guard-provenans-")
    os.makedirs(os.path.join(d, "tools"))
    shutil.copy(guard, os.path.join(d, "tools", "urunler-guard.py"))
    shutil.copy(kopru, os.path.join(d, "tools", "urunler-guard-hook.py"))
    g(d, "init", "-q", "-b", "main")
    g(d, "config", "user.email", "kabul@pruvo.test")
    g(d, "config", "user.name", "Kabul")
    g(d, "config", "commit.gpgsign", "false")
    yaz_katalog(d, katalog)
    g(d, "add", "-A")
    g(d, "commit", "-q", "--no-verify", "-m", "A taban katalog")
    return d


def kur_merge(guard, kopru, taban, main_katalog):
    """dal BAYAT kalir, main ILERLER, sonra main dala merge edilir (commit'siz)."""
    d = kur_depo(guard, kopru, taban)
    g(d, "branch", "dal")
    yaz_katalog(d, main_katalog)
    g(d, "add", "-A")
    g(d, "commit", "-q", "--no-verify", "-m", "B main guncel katalog")
    g(d, "checkout", "-q", "dal")
    with open(os.path.join(d, "dal-isi.md"), "w") as f:
        f.write("dalin kendi isi\n")
    g(d, "add", "-A")
    g(d, "commit", "-q", "--no-verify", "-m", "C dal isi")
    rc, out = g(d, "merge", "--no-commit", "--no-ff", "main")
    return d, rc, out


def kos_guard(kok, tetik="commit", ek_env=None):
    env = _env()
    env.pop("PRUVO_GUARD_ZORLA", None)
    if ek_env:
        env.update(ek_env)
    p = subprocess.run([sys.executable, os.path.join(kok, "tools", "urunler-guard.py"),
                        "--tetik", tetik],
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def kos_kopru(kok, komut):
    env = _env()
    env.pop("PRUVO_GUARD_ZORLA", None)
    girdi = json.dumps({"tool_name": "Bash", "tool_input": {"command": komut}})
    p = subprocess.run([sys.executable, os.path.join(kok, "tools", "urunler-guard-hook.py")],
                       input=girdi, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def _canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def cikis_yolu_kodlari(guard_yolu):
    """OLCULEN guard kaynagindan CIKIS_YOLLARI kodlarini oku (ikiz tanim capasi).

    Basilan metin bu listeden TUREMELI; liste ile metin ayrisirsa E4 KIRMIZI yanar.
    Liste hic yoksa () doner -> E4 yine KIRMIZI (fail-closed yon).
    """
    try:
        spec = importlib.util.spec_from_file_location("_olculen_guard", guard_yolu)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return tuple(k for k, _t in getattr(m, "CIKIS_YOLLARI", ()))
    except Exception:
        return ()


def manifest_yaz(kok, obj):
    with open(os.path.join(kok, ".urunler-duzelt-izin.json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------
# SENARYOLAR
# --------------------------------------------------------------------------
def senaryo_merge_replay(guard, kopru):
    """P1-P5 — 4 Agu olayinin BIREBIR replayi (sahte fikstur uzerinde)."""
    d, mrc, mout = kur_merge(guard, kopru, [BAYAT], [GUNCEL])
    if mrc != 0:
        iddia("P1", False, "merge kurulamadi: %s" % mout.strip())
        return
    once_sha = sha(d)
    once = oku_katalog(d)
    rc, _o, _e = kos_guard(d)
    sonra_sha = sha(d)
    sonra = oku_katalog(d)
    iddia("P1", once_sha == sonra_sha,
          "sha once=%s sonra=%s" % (once_sha[:12], sonra_sha[:12]))
    iddia("P2", "lisans" in sonra[0],
          "lisans var mi: once=%s sonra=%s" % ("lisans" in once[0], "lisans" in sonra[0]))
    iddia("P3", len(sonra[0]["gorseller"]) == 2,
          "gorsel once=%d sonra=%d" % (len(once[0]["gorseller"]), len(sonra[0]["gorseller"])))
    iddia("P4", len(sonra[0]["aciklama"]) == len(GUNCEL["aciklama"]),
          "aciklama once=%d sonra=%d" % (len(once[0]["aciklama"]), len(sonra[0]["aciklama"])))
    iddia("P5", rc == 0, "rc=%d" % rc)


def senaryo_merge_silme_ve_ekleme(guard, kopru):
    """M1 — main SILDI; M2 — main EKLEDI."""
    yeni_urun = _urun("sahte-main-yenisi", gorsel=3)
    d, mrc, mout = kur_merge(guard, kopru,
                             [BAYAT, IKINCI],           # taban: iki urun
                             [yeni_urun, BAYAT])        # main: IKINCI silindi, yeni eklendi
    if mrc != 0:
        iddia("M1", False, "merge kurulamadi: %s" % mout.strip())
        iddia("M2", False, "merge kurulamadi")
        return
    rc, _o, _e = kos_guard(d)
    sonra = {p["id"]: p for p in oku_katalog(d)}
    iddia("M1", IKINCI["id"] not in sonra,
          "silinen urun geri geldi mi: %s (rc=%d)" % (IKINCI["id"] in sonra, rc))
    iddia("M2", rc == 0 and sonra.get(yeni_urun["id"]) == yeni_urun,
          "rc=%d aynen duruyor mu: %s" % (rc, sonra.get(yeni_urun["id"]) == yeni_urun))


def senaryo_merge_beyanli(guard, kopru):
    """M3 — merge halinde manifest-beyanli duzeltme KORUNUR."""
    yeni_urun = _urun("sahte-main-yenisi", gorsel=3)
    d, mrc, mout = kur_merge(guard, kopru, [BAYAT], [yeni_urun, BAYAT])
    if mrc != 0:
        iddia("M3", False, "merge kurulamadi: %s" % mout.strip())
        return
    kat = oku_katalog(d)
    for p in kat:
        if p["id"] == BAYAT["id"]:
            p["fiyat"] = "777 TL"
    yaz_katalog(d, kat)
    manifest_yaz(d, {BAYAT["id"]: {"fiyat": "777 TL"}})
    rc, _o, err = kos_guard(d)
    sonra = {p["id"]: p for p in oku_katalog(d)}
    iddia("M3", rc == 0 and sonra[BAYAT["id"]]["fiyat"] == "777 TL",
          "rc=%d fiyat=%r" % (rc, sonra.get(BAYAT["id"], {}).get("fiyat")))


def senaryo_koruma_degisim(guard, kopru):
    """K1 + G1 — merge DISI izinsiz alan degisimi geri sarilir VE GORUNUR basilir."""
    d = kur_depo(guard, kopru, [GUNCEL])
    kat = oku_katalog(d)
    kat[0]["fiyat"] = "9999 TL"
    kat[0].pop("lisans", None)
    yaz_katalog(d, kat)
    rc, _o, err = kos_guard(d)
    sonra = oku_katalog(d)
    iddia("K1", sonra[0]["fiyat"] == GUNCEL["fiyat"] and "lisans" in sonra[0],
          "fiyat=%r lisans=%s rc=%d" % (sonra[0]["fiyat"], "lisans" in sonra[0], rc))
    iddia("G1", GUNCEL["id"] in err and "fiyat" in err and "lisans" in err,
          "stderr=%r" % err[:220])


def senaryo_koruma_silme(guard, kopru):
    """K2 — merge DISI izinsiz silme geri EKLENIR."""
    d = kur_depo(guard, kopru, [GUNCEL, IKINCI])
    yaz_katalog(d, [GUNCEL])
    rc, _o, _e = kos_guard(d)
    sonra = {p["id"]: p for p in oku_katalog(d)}
    iddia("K2", IKINCI["id"] in sonra and sonra[IKINCI["id"]] == IKINCI,
          "geri geldi mi=%s rc=%d" % (IKINCI["id"] in sonra, rc))


def senaryo_beyanli_degisim(guard, kopru):
    """K3 — merge DISI manifest-beyanli degisim KORUNUR (yanlis-pozitif yok)."""
    d = kur_depo(guard, kopru, [GUNCEL])
    kat = oku_katalog(d)
    kat[0]["fiyat"] = "555 TL"
    yaz_katalog(d, kat)
    manifest_yaz(d, {GUNCEL["id"]: {"fiyat": "555 TL"}})
    rc, _o, _e = kos_guard(d)
    sonra = oku_katalog(d)
    iddia("K3", rc == 0 and sonra[0]["fiyat"] == "555 TL",
          "rc=%d fiyat=%r" % (rc, sonra[0]["fiyat"]))


def senaryo_mesru_parti(guard, kopru):
    """N1 — MaCiT deseni: yeni urun BASA eklenir, hicbir sey degismez."""
    d = kur_depo(guard, kopru, [GUNCEL, IKINCI])
    yeni = [_urun("sahte-parti-a", gorsel=4), _urun("sahte-parti-b", gorsel=3),
            GUNCEL, IKINCI]
    yaz_katalog(d, yeni)
    once_sha = sha(d)
    rc, _o, err = kos_guard(d)
    sonra = oku_katalog(d)
    iddia("N1", rc == 0 and sha(d) == once_sha
          and [p["id"] for p in sonra] == [p["id"] for p in yeni],
          "rc=%d byte_esit=%s sira=%s" % (rc, sha(d) == once_sha,
                                          [p["id"] for p in sonra]))


def senaryo_belirsiz(guard, kopru):
    """B1 + B2 + B5 + E1 — merge'de iki ebeveyne de uymayan hal."""
    d, mrc, mout = kur_merge(guard, kopru, [BAYAT], [GUNCEL])
    if mrc != 0:
        for k in ("B1", "B2", "B5", "E1"):
            iddia(k, False, "merge kurulamadi: %s" % mout.strip())
        return
    kat = oku_katalog(d)
    kat[0]["fiyat"] = "3.THIRD-STATE TL"   # ne HEAD'de ne MERGE_HEAD'de olan hal
    yaz_katalog(d, kat)
    once_sha = sha(d)
    rc, _o, err = kos_guard(d)
    iddia("B1", rc != 0, "rc=%d" % rc)
    iddia("B2", sha(d) == once_sha,
          "sha once=%s sonra=%s" % (once_sha[:12], sha(d)[:12]))
    iddia("B5", BAYAT["id"] in err and "VERI DEGISTIRILMEDI" in err,
          "stderr=%r" % err[:220])
    zrc, _zo, _ze = kos_guard(d, ek_env={"PRUVO_GUARD_ZORLA": "1"})
    iddia("E1", zrc == 0 and sha(d) == once_sha,
          "zorla rc=%d byte_esit=%s" % (zrc, sha(d) == once_sha))

    # E4 — IKIZ TANIM CAPASI: basilan metin CIKIS_YOLLARI'ndan TUREMELI. Guard'in
    # (olculen kopyanin) kendi listesi okunur; her kod ciktida GORUNMELI. Ayrica
    # yaniltici "PRUVO_GUARD_ZORLA=1 git commit" bicimi UYARI olmadan gecmemeli.
    kodlar = cikis_yolu_kodlari(guard)
    hepsi_basildi = bool(kodlar) and all(("[%s]" % k) in err for k in kodlar)
    uyari_var = "CALISMAZ" in err and "harness" in err
    iddia("E4", hepsi_basildi and uyari_var,
          "kodlar=%s hepsi_basildi=%s uyari=%s" % (kodlar, hepsi_basildi, uyari_var))

    # E2 — BELGELENEN [MANIFEST] YOLU: WT'deki degisen alanlari beyan et -> GECER.
    d2, mrc2, _m2 = kur_merge(guard, kopru, [BAYAT], [GUNCEL])
    if mrc2 != 0:
        iddia("E2", False, "merge kurulamadi")
    else:
        kat2 = oku_katalog(d2)
        kat2[0]["fiyat"] = "3.THIRD-STATE TL"
        yaz_katalog(d2, kat2)
        beyan = {k: v for k, v in kat2[0].items()
                 if k != "id" and _canon(v) != _canon(BAYAT.get(k, None))}
        manifest_yaz(d2, {kat2[0]["id"]: beyan})
        e2_sha = sha(d2)
        rc2, _o2, _e2 = kos_guard(d2)
        iddia("E2", rc2 == 0 and sha(d2) == e2_sha,
              "rc=%d byte_esit=%s beyan_alan=%d" % (rc2, sha(d2) == e2_sha, len(beyan)))

    # E3 — BELGELENEN [EBEVEYN] YOLU: ucuncu hal yerine EBEVEYNIN halini AYNEN sec.
    d3, mrc3, _m3 = kur_merge(guard, kopru, [BAYAT], [GUNCEL])
    if mrc3 != 0:
        iddia("E3", False, "merge kurulamadi")
    else:
        kat3 = oku_katalog(d3)
        kat3[0]["fiyat"] = "3.THIRD-STATE TL"
        yaz_katalog(d3, kat3)
        yaz_katalog(d3, [dict(GUNCEL)])      # MERGE_HEAD ebeveyninin hali, AYNEN
        e3_sha = sha(d3)
        rc3, _o3, _e3 = kos_guard(d3)
        iddia("E3", rc3 == 0 and sha(d3) == e3_sha,
              "rc=%d byte_esit=%s" % (rc3, sha(d3) == e3_sha))


def senaryo_bozuk_wt(guard, kopru):
    """B3 — WT BOZUK JSON: eskiden SESSIZ atlanirdi."""
    d = kur_depo(guard, kopru, [GUNCEL])
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        f.write('[{"id": "sahte-bozuk", ')   # kapatilmamis JSON
    once_sha = sha(d)
    rc, _o, _e = kos_guard(d)
    iddia("B3", rc != 0 and sha(d) == once_sha,
          "rc=%d byte_esit=%s" % (rc, sha(d) == once_sha))


def senaryo_ebeveyn_okunamiyor(guard, kopru):
    """B4 — MERGE_HEAD var ama o commit'te urunler.json YOK."""
    d = kur_depo(guard, kopru, [GUNCEL])
    g(d, "checkout", "-q", "--orphan", "bos")
    g(d, "rm", "-q", "-rf", ".")
    with open(os.path.join(d, "OKUBENI.md"), "w") as f:
        f.write("katalogsuz dal\n")
    g(d, "add", "-A")
    g(d, "commit", "-q", "--no-verify", "-m", "katalogsuz")
    rc0, bos_sha = g(d, "rev-parse", "HEAD")
    g(d, "checkout", "-q", "-f", "main")
    rc1, gitdir = g(d, "rev-parse", "--absolute-git-dir")
    if rc0 != 0 or rc1 != 0:
        iddia("B4", False, "kurulum basarisiz rc0=%d rc1=%d" % (rc0, rc1))
        return
    with open(os.path.join(gitdir.strip(), "MERGE_HEAD"), "w") as f:
        f.write(bos_sha.strip() + "\n")
    rc, _o, err = kos_guard(d)
    iddia("B4", rc != 0, "rc=%d stderr=%r" % (rc, err[:160]))


def senaryo_kendi_hatasi(guard, kopru):
    """B6 — guard'in KENDI beklenmedik hatasi: eskiden SESSIZCE exit 0 verirdi.

    Kilit yolunu DIZIN yaparak `open(LOCK, "w")` bir IsADirectoryError firlatir;
    bu, guard'in ongordugu hallerden hicbiri DEGILDIR -> koruma KOSMAMISTIR.
    """
    d = kur_depo(guard, kopru, [GUNCEL])
    os.makedirs(os.path.join(d, ".urunler.lock"), exist_ok=True)
    kat = oku_katalog(d)
    kat[0]["fiyat"] = "1234 TL"
    yaz_katalog(d, kat)
    rc, _o, err = kos_guard(d)
    iddia("B6", rc != 0, "rc=%d stderr=%r" % (rc, err[:160]))


def senaryo_kopru(guard, kopru):
    """H1 H2 H3 — IZLENEN kopru guard'in hukmunu TASIYOR mu."""
    # H1: guard REDDEDEN hal (B1 kurulumu)
    d, mrc, _m = kur_merge(guard, kopru, [BAYAT], [GUNCEL])
    if mrc == 0:
        kat = oku_katalog(d)
        kat[0]["fiyat"] = "3.THIRD-STATE TL"
        yaz_katalog(d, kat)
        rc, _o, err = kos_kopru(d, "git -C /x commit -m deneme")
        iddia("H1", rc == 2, "rc=%d stderr=%r" % (rc, err[:180]))
    else:
        iddia("H1", False, "merge kurulamadi")
    # H2: temiz depo, mesru commit GECER
    d2 = kur_depo(guard, kopru, [GUNCEL])
    rc2, _o2, err2 = kos_kopru(d2, "git commit -m temiz")
    iddia("H2", rc2 == 0, "rc=%d stderr=%r" % (rc2, err2[:180]))
    # H3: AYRI TAZE depo — git-disi komutta guard'in HIC kosmadigi log'un
    # YOKLUGUYLA olculur (yalnizca rc=0 bakmak bu ekseni oldurulemez kilardi).
    d3 = kur_depo(guard, kopru, [GUNCEL])
    rc3, _o3, _e3 = kos_kopru(d3, "ls -la /tmp")
    log_var = os.path.exists(os.path.join(d3, ".urunler-guard.log"))
    iddia("H3", rc3 == 0 and not log_var, "rc=%d guard_log=%s" % (rc3, log_var))


SENARYOLAR = [
    senaryo_merge_replay,
    senaryo_merge_silme_ve_ekleme,
    senaryo_merge_beyanli,
    senaryo_koruma_degisim,
    senaryo_koruma_silme,
    senaryo_beyanli_degisim,
    senaryo_mesru_parti,
    senaryo_belirsiz,
    senaryo_bozuk_wt,
    senaryo_ebeveyn_okunamiyor,
    senaryo_kendi_hatasi,
    senaryo_kopru,
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak", default=VARSAYILAN_GUARD,
                    help="olculecek urunler-guard.py (mutasyon turu icin)")
    ap.add_argument("--kaynak-kopru", default=VARSAYILAN_KOPRU,
                    help="olculecek urunler-guard-hook.py (mutasyon turu icin)")
    a = ap.parse_args()

    print("URUNLER-GUARD PROVENANS + FAIL-LOUD KABULU")
    print("  guard : %s" % a.kaynak)
    print("  kopru : %s" % a.kaynak_kopru)

    for fn in SENARYOLAR:
        try:
            fn(a.kaynak, a.kaynak_kopru)
        except Exception as e:          # senaryo cokerse iddialar OLCULEMEDI kalir
            print("  ! senaryo %s coktu: %r" % (fn.__name__, e))

    kirmizi = 0
    for kod, aciklama in KODLAR:
        if kod in DEFTER:
            ok, ayrinti = DEFTER[kod]
        else:
            ok, ayrinti = False, "OLCULEMEDI"
        if not ok:
            kirmizi += 1
        print("IDDIA: %s %s %s%s" % (kod, "YESIL" if ok else "KIRMIZI", aciklama,
                                     ("  |  " + ayrinti) if ayrinti else ""))
    print("TOPLAM: iddia=%d kirmizi=%d" % (len(KODLAR), kirmizi))
    return 0 if kirmizi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

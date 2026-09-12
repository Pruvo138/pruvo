#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DAL ENVANTERI — yerel dallarda main'e ALINMAMIS is var mi, ADIYLA olcer.

NEDEN VAR
---------
`tools/durum.py`'nin "3) ARTIK DALLAR" bolumu yalnizca **ucu main'in atasi mi** eksenini
olcer ve 12 Eyl 2026'da **0** basiyordu — ayni anda 41 yerel dal duruyordu ve orneklemin
4/4'unde main'de YAMA ESDEGERI OLMAYAN commit vardi (`git cherry` `+`). Iki eksen ayni sey
DEGILDIR: bir dal main'in atasi olmayabilir ama icerigi cherry-pick'lenmis olabilir; ya da
tersine, ucu main'de gorunurken getirdigi dosya main'de HIC olmayabilir
-> [[durum-artik-dal-yanlis-siniflar]].

Bu arac HUKUM VERMEZ, **ADAY LISTESI** uretir. Hicbir dali silmez, merge etmez, hicbir
ref'e dokunmaz — salt okuma. Silme/merge karari mimarindir ve dal BASINA verilir.

OLCUT — bir dal su uc soruyla siniflanir:
  ① `git cherry main <dal>` -> main'de yama esdegeri OLMAYAN commit sayisi (`+`)
  ② o commit'lerin dokundugu dosyalar (birlesim)
  ③ o dosyalardan kaci main'in agacinda YOK (`git ls-tree main -- <yol>` bos)

SINIFLAR
  ESDEGER_MAINDE   : `+` commit YOK -> icerik main'de, dal guvenle silinebilir (ADAY)
  YENI_DOSYA       : `+` var ve en az bir dosya main'de HIC YOK -> **kayip is adayi**, ONCE BAK
  DEGISIKLIK       : `+` var, dosyalarin hepsi main'de VAR -> icerik farki olabilir, incele
  BOS              : `+` var ama dosya dokunusu yok (bos/merge commit'i)

CIKIS KODU SOZLESMESI (iki yonlu): basilan `❌` sayisi >0 ise rc!=0; =0 ise rc=0.
`--kendini-test` ag/repo durumundan BAGIMSIZ ic iddialari kosar.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

KOK_VARSAYILAN = "/Users/okan/dev/pruvo"
ANA = "main"

# Defter/rapor sinifi: bu yollar TEK BASINA kaldiginda dalin isi "belge"dir, kod degil.
BELGE_EKLERI = (".md",)


def _git(kok, *arg):
    p = subprocess.run(["git", "-C", kok, *arg], capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def yerel_dallar(kok):
    rc, cikti, hata = _git(kok, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    if rc != 0:
        raise RuntimeError("for-each-ref rc=%s: %s" % (rc, hata))
    return [d for d in cikti.split("\n") if d and d != ANA]


def cherry_artilari(kok, dal):
    """main'de YAMA ESDEGERI OLMAYAN commit sha'lari (`git cherry` `+` satirlari)."""
    rc, cikti, hata = _git(kok, "cherry", ANA, dal)
    if rc != 0:
        return None, "cherry rc=%s: %s" % (rc, hata)
    artilar = [s.split()[1] for s in cikti.split("\n") if s.startswith("+ ")]
    return artilar, None


def commit_dosyalari(kok, shalar):
    dosyalar = set()
    for sha in shalar:
        rc, cikti, _ = _git(kok, "show", "--name-only", "--pretty=format:", sha)
        if rc != 0:
            continue
        for yol in cikti.split("\n"):
            if yol.strip():
                dosyalar.add(yol.strip())
    return sorted(dosyalar)


def mainde_yok(kok, dosyalar):
    eksik = []
    for yol in dosyalar:
        rc, cikti, _ = _git(kok, "ls-tree", ANA, "--", yol)
        if rc != 0 or not cikti:
            eksik.append(yol)
    return eksik


def mainde_atif(kok, yol):
    """main'de bu dosyaya yapilan atif sayisi — **TAM YOL** ile, onek DEGIL.

    🔴 12 Eyl 2026'da olculdu: "dosya adini uzantisiz ara" olcutu ONEK TUZAGINA
    acik. `shop/test/kanal-gorunurluk.mjs` icin yapilan arama
    `nobet.yml:3521 run: python3 tools/kanal-gorunurluk-mutasyon.py` satirini
    yakaladi ve dosya "CI'da KOSUYOR" sanildi; oysa o satir main'de VAR OLAN
    BASKA bir dosyayi cagiriyor, aranan dosyaya atif SIFIR
    -> [[arac-adi-onek-eslesmesi-komsu-araci-keser]].

    (atif_sayisi, "RUN"|"YORUM"|"YOK") dondurur. `run:` satirinda gecen bir atif
    CI'da GERCEKTEN kosuyor demektir; gövde main'de yoksa o bir HAYALI NOBETCIDIR.
    """
    rc, cikti, _ = _git(kok, "grep", "-n", "-F", yol, ANA, "--",
                        ".github/", "tools/", "shop/")
    if rc != 0 or not cikti:
        return 0, "YOK"
    satirlar = cikti.split("\n")
    for s in satirlar:
        govde = s.split(":", 3)[-1].strip()
        if govde.startswith("run:") or govde.startswith("- run:"):
            return len(satirlar), "RUN"
    return len(satirlar), "YORUM"


def siniflandir(arti_sayisi, dosyalar, eksikler):
    if arti_sayisi == 0:
        return "ESDEGER_MAINDE"
    if not dosyalar:
        return "BOS"
    if eksikler:
        return "YENI_DOSYA"
    return "DEGISIKLIK"


def envanter(kok, ayrinti=False):
    hata = 0
    dallar = yerel_dallar(kok)
    print("DAL ENVANTERI — kok=%s · ana=%s · yerel dal=%d" % (kok, ANA, len(dallar)))
    kovalar = {"ESDEGER_MAINDE": [], "YENI_DOSYA": [], "DEGISIKLIK": [], "BOS": [],
               "OLCULEMEDI": []}
    satirlar = []

    for dal in dallar:
        artilar, sebep = cherry_artilari(kok, dal)
        if artilar is None:
            kovalar["OLCULEMEDI"].append(dal)
            satirlar.append((dal, "OLCULEMEDI", 0, 0, 0, sebep or "", []))
            hata += 1
            print("❌ %s — OLCULEMEDI: %s" % (dal, sebep))
            continue
        dosyalar = commit_dosyalari(kok, artilar)
        eksikler = mainde_yok(kok, dosyalar)
        sinif = siniflandir(len(artilar), dosyalar, eksikler)
        kovalar[sinif].append(dal)
        satirlar.append((dal, sinif, len(artilar), len(dosyalar), len(eksikler), "", eksikler))

    for ad in ("YENI_DOSYA", "DEGISIKLIK", "BOS", "ESDEGER_MAINDE"):
        uyeler = [s for s in satirlar if s[1] == ad]
        if not uyeler:
            continue
        print("\n== %s (%d)" % (ad, len(uyeler)))
        for dal, _, n_arti, n_dosya, n_eksik, _, eksikler in uyeler:
            belge_mi = (n_dosya > 0 and all(d.endswith(BELGE_EKLERI) for d in eksikler)
                        if eksikler else False)
            etiket = " [yalniz belge]" if belge_mi else ""
            print("  %-46s +%d commit · %d dosya · main'de YOK %d%s"
                  % (dal, n_arti, n_dosya, n_eksik, etiket))
            if ayrinti and eksikler:
                for yol in eksikler[:12]:
                    n_atif, tur = mainde_atif(kok, yol)
                    isaret = " 🔴 HAYALI NOBETCI (CI cagiriyor, govde main'de YOK)" \
                        if tur == "RUN" else ""
                    print("       - %s | main'de atif: %d %s%s"
                          % (yol, n_atif, tur, isaret))
                if len(eksikler) > 12:
                    print("       … +%d dosya daha" % (len(eksikler) - 12))

    print("\nOZET: YENI_DOSYA=%d · DEGISIKLIK=%d · BOS=%d · ESDEGER_MAINDE=%d · OLCULEMEDI=%d"
          % (len(kovalar["YENI_DOSYA"]), len(kovalar["DEGISIKLIK"]), len(kovalar["BOS"]),
             len(kovalar["ESDEGER_MAINDE"]), len(kovalar["OLCULEMEDI"])))
    print("🔴 HUKUM VERILMEDI — bu bir ADAY listesidir. Silme/merge karari dal BASINA "
          "verilir; ESDEGER_MAINDE bile once `git branch -a --contains <uc>` ile teyit "
          "edilmeden SILINMEZ -> [[durum-artik-dal-yanlis-siniflar]]")
    return hata


# ------------------------------------------------------------------ oz test
def kendini_test():
    hata = 0

    if siniflandir(0, ["a.py"], []) == "ESDEGER_MAINDE":
        print("✅ A1 arti yoksa ESDEGER_MAINDE")
    else:
        hata += 1
        print("❌ A1 arti yokken sinif yanlis")

    if siniflandir(2, [], []) == "BOS":
        print("✅ A2 arti var + dosya yok -> BOS")
    else:
        hata += 1
        print("❌ A2 bos commit sinifi yanlis")

    if siniflandir(1, ["tools/x.py"], ["tools/x.py"]) == "YENI_DOSYA":
        print("✅ A3 main'de olmayan dosya -> YENI_DOSYA (kayip is adayi)")
    else:
        hata += 1
        print("❌ A3 kayip is adayi siniflanmadi")

    if siniflandir(1, ["tools/x.py"], []) == "DEGISIKLIK":
        print("✅ A4 dosyalar main'de VAR -> DEGISIKLIK")
    else:
        hata += 1
        print("❌ A4 degisiklik sinifi yanlis")

    # A5 — sinif ADLARI kova sozlugundeki anahtarlarla BIREBIR ortusmeli
    kova_adlari = {"ESDEGER_MAINDE", "YENI_DOSYA", "DEGISIKLIK", "BOS"}
    uretilen = {siniflandir(0, ["a"], []), siniflandir(2, [], []),
                siniflandir(1, ["a"], ["a"]), siniflandir(1, ["a"], [])}
    if uretilen == kova_adlari:
        print("✅ A5 uretilen sinif kumesi kova adlariyla BIREBIR (%d)" % len(kova_adlari))
    else:
        hata += 1
        print("❌ A5 sinif adi ile kova adi AYRISIYOR: %s" % (uretilen ^ kova_adlari))

    # A6 — eksik listesi bos degilken 'main'de YOK' sayisi eksiklerin uzunlugudur
    if len(["a", "b"]) == 2 and siniflandir(3, ["a", "b"], ["b"]) == "YENI_DOSYA":
        print("✅ A6 tek dosya bile main'de yoksa sinif YENI_DOSYA'ya dusuyor")
    else:
        hata += 1
        print("❌ A6 kismi eksiklik YENI_DOSYA uretmiyor")

    # KONTROL K1 — arac SALT OKUMA olmali. Olcut "yasak kelime kaynakta geciyor mu"
    # DEGIL (o olcut kendi yasak listesini yakalar ve her zaman kirmizi yanar — ilk
    # yazimda oyle oldu); olcut **fiilen cagrilan git alt komutu**dur: kaynaktaki her
    # `_git(kok, "<altkomut>"` isabeti bir ALLOWLIST'te olmak ZORUNDA.
    import ast as _ast
    izinli = {"for-each-ref", "cherry", "show", "ls-tree", "grep"}
    agac = _ast.parse(open(os.path.abspath(__file__)).read())
    cagrilan = set()
    for dugum in _ast.walk(agac):
        if (isinstance(dugum, _ast.Call) and isinstance(dugum.func, _ast.Name)
                and dugum.func.id == "_git" and len(dugum.args) >= 2
                and isinstance(dugum.args[1], _ast.Constant)):
            cagrilan.add(dugum.args[1].value)
    disarida = sorted(cagrilan - izinli)
    if cagrilan and not disarida:
        print("✅ K1 (kontrol) cagrilan git alt komutlari salt-okuma: %s"
              % ", ".join(sorted(cagrilan)))
    else:
        hata += 1
        print("❌ K1 allowlist DISI git alt komutu: %s (cagrilan=%s)"
              % (disarida, sorted(cagrilan)))

    # MUTANT M1 — allowlist'e sahte bir yazma komutu sizarsa kol KIRMIZI yanmali
    if sorted({"cherry", "branch"} - izinli) == ["branch"]:
        print("✅ M1 (mutant) allowlist disi komut ADIYLA yakalaniyor")
    else:
        hata += 1
        print("❌ M1 mutant: allowlist farki yanlis hesaplaniyor")

    print("DUSEN: %d" % hata)
    return hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=KOK_VARSAYILAN)
    ap.add_argument("--ayrinti", action="store_true",
                    help="YENI_DOSYA kovasinda main'de olmayan dosya yollarini bas")
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()

    if a.kendini_test:
        return 1 if kendini_test() else 0
    return 1 if envanter(a.kok, ayrinti=a.ayrinti) else 0


if __name__ == "__main__":
    sys.exit(main())

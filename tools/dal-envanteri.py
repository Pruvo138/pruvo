#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DAL ENVANTERI — yerel VE uzak dallarda main'e ALINMAMIS is var mi, ADIYLA olcer.

NEDEN VAR
---------
`tools/durum.py`'nin "3) ARTIK DALLAR" bolumu yalnizca **ucu main'in atasi mi** eksenini
olcer ve 12 Eyl 2026'da **0** basiyordu — ayni anda 41 yerel dal duruyordu ve orneklemin
4/4'unde main'de YAMA ESDEGERI OLMAYAN commit vardi (`git cherry` `+`). Iki eksen ayni sey
DEGILDIR: bir dal main'in atasi olmayabilir ama icerigi cherry-pick'lenmis olabilir; ya da
tersine, ucu main'de gorunurken getirdigi dosya main'de HIC olmayabilir
-> [[durum-artik-dal-yanlis-siniflar]].

OLCUM EVRENI = YEREL ∪ UZAK (23 Eyl 2026, KraL-Tamirci-23Eyl)
--------------------------------------------------------------
Ilk surum yalniz `refs/heads/` okuyordu. Sabah spec'inin merge kuyrugu ise `git branch -a`
= yerel ∪ uzak ad kumesidir. OLCULDU (23 Eyl): yerel **45** dal, uzak **56**, birlesim
**76** -> **31 dal YALNIZ uzakta** ve araca HIC gorunmuyordu; 6'si main'de hic olmayan
dosya tasiyordu (kayip is adayi). Mekanizma: cip dalini iter, sonra worktree temizligi
YEREL dali siler — is uzakta kalir, envanterden duser. Artik her ad bir kez olculur:
  * yalniz yerel      -> `<ad>`            (konum Y)
  * yalniz uzak       -> `origin/<ad>`     (konum U)
  * ikisi, uc AYNI    -> `<ad>` BIR kez    (konum Y+U) — ayni commit iki kez sayilmaz
  * ikisi, uc FARKLI  -> IKI ref de        (konum Y≠ / U≠) — farkli is ayri olculur
Arac FETCH YAPMAZ (salt okuma); uzak ref'lerin tazeligi son fetch zamanindan basilir.

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
`--kendini-test` ag/repo durumundan BAGIMSIZ ic iddialari kosar (fikstur depo GECICI
dizinde kurulur). `--mutasyon` her mutanti aracin IZOLE kopyasinda kosar; canli govdeye
dokunmaz.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import time

KOK_VARSAYILAN = "/Users/okan/dev/pruvo"
ANA = "main"
UZAK = "origin"

# Defter/rapor sinifi: bu yollar TEK BASINA kaldiginda dalin isi "belge"dir, kod degil.
BELGE_EKLERI = (".md",)

# Git baglam scrub'i + sentetik fikstur depolari TEK KAYNAKTAN (`tools/git_ortami.py`).
# Mutasyon turu bu dosyanin KOPYASINI gecici dizinde kosar ve orada `git_ortami.py` YOKTUR;
# kopyayi kosan harness kanonik `tools/`u `PRUVO_KANONIK_TOOLS` ile SOYLER.
TOOLS_DIZINI = os.path.dirname(os.path.realpath(__file__))
for _aday in (os.environ.get("PRUVO_KANONIK_TOOLS") or "", TOOLS_DIZINI,
              os.path.join(KOK_VARSAYILAN, "tools")):
    if _aday and os.path.isfile(os.path.join(_aday, "git_ortami.py")):
        sys.path.insert(0, _aday)
        break
from git_ortami import git_ortami, sentetik_git  # noqa: E402


def _git(kok, *arg):
    # Miras alinan GIT_DIR/GIT_INDEX_FILE (kanca baglami) `-C kok` hedefini ezmesin.
    p = subprocess.run(["git", "-C", kok, *arg], capture_output=True, text=True,
                       env=git_ortami())
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def ad_coz(refname, onek):
    """Tam ref adindan dal adini cikarir; ana dal ve `HEAD` olcum disidir (None)."""
    if not refname.startswith(onek):
        return None
    ad = refname[len(onek):]
    if not ad or ad in (ANA, "HEAD"):
        return None
    return ad


def ref_haritasi(kok, onek):
    """{dal adi: uc sha} — `onek` altindaki ref'ler (orn. refs/heads/, refs/remotes/origin/)."""
    rc, cikti, hata = _git(kok, "for-each-ref", "--format=%(refname) %(objectname)", onek)
    if rc != 0:
        raise RuntimeError("for-each-ref %s rc=%s: %s" % (onek, rc, hata))
    harita = {}
    for satir in cikti.split("\n"):
        if not satir.strip():
            continue
        refname, sha = satir.split()
        ad = ad_coz(refname, onek)
        if ad is not None:
            harita[ad] = sha
    return harita


def olcum_hedefleri(yerel, uzak):
    """Birlesim yerel ∪ uzak -> [(ad, [(ref, konum), ...]), ...] (ada gore sirali).

    Uc AYNIYSA ayni commit iki kez sayilmaz (tek ref, Y+U); uc FARKLIYSA iki ref de olculur.
    """
    hedefler = []
    for ad in sorted(set(yerel) | set(uzak)):
        y, u = yerel.get(ad), uzak.get(ad)
        if y and u:
            refler = [(ad, "Y+U")] if y == u else [(ad, "Y≠"), (UZAK + "/" + ad, "U≠")]
        elif y:
            refler = [(ad, "Y")]
        else:
            refler = [(UZAK + "/" + ad, "U")]
        hedefler.append((ad, refler))
    return hedefler


def uzak_tazelik(kok):
    """Son fetch'ten bu yana dakika (FETCH_HEAD mtime); olculemezse None."""
    rc, ortak, _ = _git(kok, "rev-parse", "--git-common-dir")
    if rc != 0 or not ortak:
        return None
    yol = os.path.join(ortak if os.path.isabs(ortak) else os.path.join(kok, ortak),
                       "FETCH_HEAD")
    try:
        return int((time.time() - os.path.getmtime(yol)) // 60)
    except OSError:
        return None


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
    yerel = ref_haritasi(kok, "refs/heads/")
    uzak = ref_haritasi(kok, "refs/remotes/%s/" % UZAK)
    hedefler = olcum_hedefleri(yerel, uzak)
    ikisi = set(yerel) & set(uzak)
    uc_farkli = sum(1 for ad in ikisi if yerel[ad] != uzak[ad])
    olculecek = [(ref, konum) for _, refler in hedefler for ref, konum in refler]
    print("DAL ENVANTERI — kok=%s · ana=%s · yerel dal=%d · uzak dal=%d · birlesim=%d "
          "(yalniz-yerel %d · yalniz-uzak %d · ikisi %d, uc farkli %d) · olculen ref=%d"
          % (kok, ANA, len(yerel), len(uzak), len(hedefler), len(set(yerel) - set(uzak)),
             len(set(uzak) - set(yerel)), len(ikisi), uc_farkli, len(olculecek)))
    dakika = uzak_tazelik(kok)
    if dakika is None:
        print("🟠 UZAK REF TAZELIGI: OLCULEMEDI (FETCH_HEAD yok) — arac FETCH YAPMAZ; "
              "uzak dallar son cekildigi haliyle olculur")
    else:
        print("UZAK REF TAZELIGI: son fetch %d dk once (arac FETCH YAPMAZ — salt okuma)"
              % dakika)
    kovalar = {"ESDEGER_MAINDE": [], "YENI_DOSYA": [], "DEGISIKLIK": [], "BOS": [],
               "OLCULEMEDI": []}
    satirlar = []

    for dal, konum in olculecek:
        artilar, sebep = cherry_artilari(kok, dal)
        if artilar is None:
            kovalar["OLCULEMEDI"].append(dal)
            satirlar.append((dal, "OLCULEMEDI", 0, 0, 0, sebep or "", [], konum))
            hata += 1
            print("❌ %s — OLCULEMEDI: %s" % (dal, sebep))
            continue
        dosyalar = commit_dosyalari(kok, artilar)
        eksikler = mainde_yok(kok, dosyalar)
        sinif = siniflandir(len(artilar), dosyalar, eksikler)
        kovalar[sinif].append(dal)
        satirlar.append((dal, sinif, len(artilar), len(dosyalar), len(eksikler), "", eksikler,
                         konum))

    for ad in ("YENI_DOSYA", "DEGISIKLIK", "BOS", "ESDEGER_MAINDE"):
        uyeler = [s for s in satirlar if s[1] == ad]
        if not uyeler:
            continue
        print("\n== %s (%d)" % (ad, len(uyeler)))
        for dal, _, n_arti, n_dosya, n_eksik, _, eksikler, konum in uyeler:
            belge_mi = (n_dosya > 0 and all(d.endswith(BELGE_EKLERI) for d in eksikler)
                        if eksikler else False)
            etiket = " [yalniz belge]" if belge_mi else ""
            print("  %-46s %-3s +%d commit · %d dosya · main'de YOK %d%s"
                  % (dal, konum, n_arti, n_dosya, n_eksik, etiket))
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
    izinli = {"for-each-ref", "cherry", "show", "ls-tree", "grep", "rev-parse"}
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

    # ---- OLCUM EVRENI = YEREL ∪ UZAK (23 Eyl 2026) --------------------------------
    hedef = dict(olcum_hedefleri({"a": "1", "ikiz": "5", "ayri": "7"},
                                 {"b": "2", "ikiz": "5", "ayri": "8"}))

    # A7 — yalniz uzaktaki dal olcume GIRER (ilk surumun kor noktasi)
    if hedef.get("b") == [(UZAK + "/b", "U")]:
        print("✅ A7 yalniz-uzak dal origin/<ad> olarak olculuyor (konum U)")
    else:
        hata += 1
        print("❌ A7 yalniz-uzak dal olcum disinda kaldi: %s" % hedef.get("b"))

    # A8 — ikisinde de ayni uc -> TEK ref (ayni commit iki kez sayilmaz)
    if hedef.get("ikiz") == [("ikiz", "Y+U")]:
        print("✅ A8 uc AYNI -> tek ref, konum Y+U")
    else:
        hata += 1
        print("❌ A8 ayni uc iki kez olculuyor ya da hic: %s" % hedef.get("ikiz"))

    # A9 — ikisinde farkli uc -> IKI ref de olculur (uzaktaki farkli is kaybolmaz)
    if hedef.get("ayri") == [("ayri", "Y≠"), (UZAK + "/ayri", "U≠")]:
        print("✅ A9 uc FARKLI -> yerel ve uzak AYRI olculuyor")
    else:
        hata += 1
        print("❌ A9 farkli uclu dalin bir ucu olcum disinda: %s" % hedef.get("ayri"))

    # A10 — POZITIF KONTROL: yalniz yereldeki dal eskisi gibi olculur (onarim eskiyi bozmadi)
    if hedef.get("a") == [("a", "Y")] and sorted(hedef) == ["a", "ayri", "b", "ikiz"]:
        print("✅ A10 (kontrol) yalniz-yerel dal eskisi gibi olculuyor; birlesim 4 ad")
    else:
        hata += 1
        print("❌ A10 yalniz-yerel dal ya da birlesim bozuldu: %s" % sorted(hedef.items()))

    # A11 — ana dal ve HEAD olcum disi; onek disi ref yok sayilir
    beklenen = {("refs/remotes/origin/HEAD", None), ("refs/remotes/origin/main", None),
                ("refs/heads/main", None), ("refs/remotes/origin/claude/x", "claude/x"),
                ("refs/tags/v1", None)}
    olcek = {(r, ad_coz(r, "refs/remotes/origin/" if "remotes" in r else "refs/heads/"))
             for r, _ in beklenen}
    if olcek == beklenen:
        print("✅ A11 main/HEAD/onek-disi ref olcum disi, alt klasorlu ad korunuyor")
    else:
        hata += 1
        # key=str: None ile str karsilastirmasi TypeError verir ve KIRMIZI yol cokerdi
        # (MU4 mutanti ilk kosumda tam olarak bunu yakaladi).
        print("❌ A11 ref adi cozumu yanlis: %s" % sorted(olcek ^ beklenen, key=str))

    # KONTROL K2 — fikstur yardimcisi gecici dizin DISINDA git KOSTURMAZ (FILO DERSI:
    # test yuku gercek ev yoluna yazamaz). Yuk VAR OLMAYAN bir yoldur; koruma dusurse
    # bile hicbir gercek depoya dokunulmaz.
    try:
        _fikstur_git("/var-olmayan-dal-envanteri-yolu", "init")
        sonuc = "CALISTI"
    except RuntimeError as exc:
        sonuc = "RED" if "DISINDA" in str(exc) else "BASKA: %s" % str(exc)[:60]
    except Exception as exc:  # noqa: BLE001 — korumasiz yol baska hata firlatir
        sonuc = "BASKA: %s" % type(exc).__name__
    if sonuc == "RED":
        print("✅ K2 (kontrol) fikstur git'i gecici dizin disinda REDDEDILIYOR")
    else:
        hata += 1
        print("❌ K2 fikstur korumasi calismadi (%s)" % sonuc)

    hata += _fikstur_testi()

    print("DUSEN: %d" % hata)
    return hata


def _fikstur_git(dizin, *arg):
    """Fikstur depo komutu — YALNIZ gecici dizinde (gercek ev yoluna asla yazmaz)."""
    gercek = os.path.realpath(dizin)
    if not gercek.startswith(os.path.realpath(tempfile.gettempdir()) + os.sep):
        raise RuntimeError("fikstur gecici dizin DISINDA: %s" % gercek)
    p = sentetik_git(gercek, *arg, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("fikstur git %s rc=%s: %s" % (arg, p.returncode, p.stderr.strip()))
    return p.stdout.strip()


def _fikstur_yaz(depo, g, dosya, metin):
    with open(os.path.join(depo, dosya), "w", encoding="utf-8") as f:
        f.write(metin)
    g("add", dosya)
    g("commit", "-q", "-m", dosya)
    return g("rev-parse", "HEAD")


def _fikstur_testi():
    """F1-F3 — gercek bir (gecici) depoda envanter uctan uca.

    Depo: main + origin/main + origin/HEAD (sembolik) ve dort dal —
      yerel-is  : yalniz yerel                       -> Y
      uzak-is   : itildi, YEREL DALI SILINDI          -> U   (23 Eyl'de olculen kor nokta)
      ikiz-is   : yerel ve uzak AYNI uc               -> Y+U (tek ref)
      ayri-is   : uzak 1 commit, yerel 1 commit ONDE  -> Y≠ + U≠ (iki ref)
    """
    hata = 0
    with tempfile.TemporaryDirectory(prefix="dal-envanteri-") as tmp:
        depo = os.path.join(tmp, "depo")
        os.makedirs(depo)
        g = lambda *a: _fikstur_git(depo, *a)  # noqa: E731
        g("init")
        ana = _fikstur_yaz(depo, g, "taban.txt", "taban\n")
        g("update-ref", "refs/remotes/origin/main", ana)
        g("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        for dal in ("yerel-is", "uzak-is", "ikiz-is", "ayri-is"):
            g("checkout", "-q", "-b", dal, "main")
            uc = _fikstur_yaz(depo, g, dal + ".txt", dal + "\n")
            if dal != "yerel-is":
                g("update-ref", "refs/remotes/origin/" + dal, uc)
        _fikstur_yaz(depo, g, "ayri-is-yerel.txt", "yalniz yerelde\n")  # ayri-is: yerel onde
        g("checkout", "-q", "main")
        g("branch", "-q", "-D", "uzak-is")  # itildi, yerel dal temizlendi (olculen vaka)

        tampon = io.StringIO()
        with contextlib.redirect_stdout(tampon):
            rc_hata = envanter(depo)
        cikti = tampon.getvalue()

    # satir -> (konum, "+N") — bosluk dolgusundan BAGIMSIZ alan ayrismasi
    satir = {s.split()[0]: (s.split()[1], s.split()[2]) for s in cikti.split("\n")
             if s.startswith("  ") and len(s.split()) > 2}
    if (satir.get("origin/uzak-is") == ("U", "+1") and "== YENI_DOSYA (5)" in cikti
            and "yerel dal=3 · uzak dal=3" in cikti):
        print("✅ F1 fikstur depo: yerel dali silinmis itilmis is origin/uzak-is olarak "
              "YENI_DOSYA'da")
    else:
        hata += 1
        print("❌ F1 fikstur depo: yalniz-uzak dal envanterde YOK ya da yanlis siniflandi")
    if ("birlesim=4" in cikti and "olculen ref=5" in cikti and "origin/HEAD" not in cikti
            and satir.get("ikiz-is") == ("Y+U", "+1") and "origin/ikiz-is" not in satir
            and rc_hata == 0):
        print("✅ F2 fikstur depo: 4 ad / 5 ref (ikiz tek sayildi), origin/HEAD olcum disi, "
              "rc=0")
    else:
        hata += 1
        print("❌ F2 fikstur depo: birlesim/ref sayimi ya da HEAD dislamasi yanlis")
    if satir.get("ayri-is") == ("Y≠", "+2") and satir.get("origin/ayri-is") == ("U≠", "+1"):
        print("✅ F3 fikstur depo: farkli uclu dalin yerel (+2) ve uzak (+1) ucu AYRI olculdu")
    else:
        hata += 1
        print("❌ F3 fikstur depo: farkli uclu dalin bir ucu olcum disinda")
    if hata:
        print("\n".join("      | " + s for s in cikti.split("\n") if s.strip()))
    return hata


# ------------------------------------------------------------------ mutasyon
# (kod, eski metin, yeni metin, bu mutanti OLDURMESI gereken iddialar)
MUTANTLAR = (
    ("MU1 birlesim yalniz yerel",
     "for ad in sorted(set(yerel) | set(uzak)):", "for ad in sorted(set(yerel)):",
     {"A7", "F1"}),
    ("MU2 ayni uc iki kez sayilir",
     '[(ad, "Y+U")] if y == u else', '[(ad, "Y≠"), (UZAK + "/" + ad, "U≠")] if y == u else',
     {"A8", "F2"}),
    ("MU3 farkli uclu dalin uzagi duser",
     'else [(ad, "Y≠"), (UZAK + "/" + ad, "U≠")]', 'else [(ad, "Y≠")]',
     {"A9", "F3"}),
    ("MU4 HEAD olcume sizar",
     'if not ad or ad in (ANA, "HEAD"):', "if not ad or ad == ANA:",
     {"A11", "F2"}),
    ("MU5 fikstur korumasi duser",
     "if not gercek.startswith(os.path.realpath(tempfile.gettempdir()) + os.sep):",
     "if False:",
     {"K2"}),
)


MUTASYON_SINIRI = "# " + "-" * 66 + " mutasyon"


def mutasyon():
    tam = open(os.path.abspath(__file__), encoding="utf-8").read()
    # Capalar YALNIZ sinirdan ONCEKI govdede aranir: MUTANTLAR tablosu capa metnini
    # kendisi de tasir, orada aranirsa her capa 2 kez sayilir ve hicbir mutant uygulanmaz.
    sinir = tam.index(MUTASYON_SINIRI)
    kaynak, kuyruk = tam[:sinir], tam[sinir:]
    ortam = dict(os.environ, PRUVO_KANONIK_TOOLS=TOOLS_DIZINI)
    hata = 0
    with tempfile.TemporaryDirectory(prefix="dal-envanteri-mut-") as tmp:
        def kos(govde, ad):
            yol = os.path.join(tmp, ad)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(govde)
            p = subprocess.run([sys.executable, yol, "--kendini-test"], capture_output=True,
                               text=True, env=ortam, cwd=tmp)
            dusen = {s.split()[1] for s in p.stdout.split("\n") if s.startswith("❌ ")}
            return p.returncode, dusen, p.stdout + p.stderr

        rc, dusen, cikti = kos(tam, "kontrol.py")
        if rc == 0 and not dusen:
            print("✅ KONTROL mutasyonsuz kopya rc=0, DUSEN 0 (harness kopyayi kosabiliyor)")
        else:
            hata += 1
            print("❌ KONTROL mutasyonsuz kopya KIRMIZI (rc=%s, dusen=%s) — mutant sonuclari "
                  "OLCULEMEDI\n%s" % (rc, sorted(dusen), cikti[-800:]))
            print("MUTANT=%d OLEN=0 SURVIVOR=OLCULEMEDI" % len(MUTANTLAR))
            return hata

        olen = 0
        for kod, eski, yeni, beklenen in MUTANTLAR:
            adet = kaynak.count(eski)
            if adet != 1:
                hata += 1
                print("❌ %s UYGULANMADI — capa %d kez geciyor (1 olmali)" % (kod, adet))
                continue
            govde = kaynak.replace(eski, yeni) + kuyruk
            if govde == tam:
                hata += 1
                print("❌ %s UYGULANMADI — mutant govde tabanla BAYT BAYT ayni" % kod)
                continue
            rc, dusen, cikti = kos(govde, "mutant.py")
            if "Traceback" in cikti:
                # Coken kopya "oldu" SAYILMAZ: rc!=0 ama hicbir iddia olculmedi.
                hata += 1
                print("❌ %s COKTU — iddia olculmedi, oldu sayilmaz:\n%s"
                      % (kod, cikti[-600:]))
                continue
            eksik = beklenen - dusen
            if rc != 0 and not eksik:
                olen += 1
                print("✅ %s OLDU — rc=%s, dusen iddialar %s (beklenen %s)"
                      % (kod, rc, sorted(dusen), sorted(beklenen)))
            else:
                hata += 1
                print("❌ %s YASADI — rc=%s, dusen %s, dusmesi gereken ama dusmeyen %s"
                      % (kod, rc, sorted(dusen), sorted(eksik)))
    print("MUTANT=%d OLEN=%d SURVIVOR=%d" % (len(MUTANTLAR), olen, len(MUTANTLAR) - olen))
    return hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=KOK_VARSAYILAN)
    ap.add_argument("--ayrinti", action="store_true",
                    help="YENI_DOSYA kovasinda main'de olmayan dosya yollarini bas")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--mutasyon", action="store_true",
                    help="birlesim kollarini IZOLE kopyada oldur, --kendini-test yakaliyor mu")
    a = ap.parse_args()

    if a.kendini_test:
        return 1 if kendini_test() else 0
    if a.mutasyon:
        return 1 if mutasyon() else 0
    return 1 if envanter(a.kok, ayrinti=a.ayrinti) else 0


if __name__ == "__main__":
    sys.exit(main())

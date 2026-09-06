#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — d1-sync KILIT YOLU MENZILI (K361 ardil onarimi, 4 Eyl 2026).

  python3 tools/d1-kilit-yolu-mutasyon.py

NE OLCER: `tools/d1-sync.py --kendini-test` bataryasindaki KILIT DUZLEMI kollarinin
(V85* turetim · V86* TEK UCUS · V87* YAZICI kolu · V88 fail-closed · V89* menzil)
IDDIA TASIYIP TASIMADIGINI. Her mutant, onarilan davranisin BIR kolunu bozar; batarya
o kolu ADIYLA kirmiziya cevirmezse iddia OLUDUR.

NEDEN GEREKLI (olculen ariza): K361 `wrangler()`in basina TEK UCUS kilidi koydu; kilit
yolu `git rev-parse` ALT SURECI ile cozuluyordu ve kabul fiksturleri `subprocess.run`u
sahteledigi icin sahte, kilit sorgusunu da YUTTU. Bes vaka kendi iddiasina gelmeden
`sys.exit` ile oldu, `--kendini-test` 137/5 kirmiziya dustu, CI `serit-a2` failure oldu
ve `deploy`+`yayin` SKIP ile YAYIN IKI TUR DURDU. Onarim yolu DOSYA SISTEMINDEN turetir.
Bu surucu, onarimin kendisinin nobetsiz kalmadigini olcer.

IZOLASYON (🔴 mutant CANLI govdeye UYGULANMAZ): her mutant, gecici bir SENTETIK depo
kokunun (`git init`) `tools/` dizinine yazilan KOPYAYA uygulanir. Sentetik kok, gercek
deponun tepe girdilerine SEMBOLIK BAG ile bakar (kopyalanan tek gercek dosya d1-sync.py
mutantidir) — boylece batarya butun girdilerini bulur, CANLI depo ise ne yazilir ne
kilitlenir. Kosum sonunda canli dosyanin sha256'si TABANLA KIYASLANIR.

ATIF: bir mutantin "oldurdugu" kol, TABAN kosumunda YESIL olup mutant kosumunda KIRMIZI
olan koldur (ONCE=SONRA kume farki). Taban da AYNI sentetik duzlemde olculur; duzlemin
kendi gurultusu (varsa) boylece hukumden DUSER.

CAPA BAYATLIGI: capa bulunamazsa COKULMEZ, KAYDEDILIR ([[capa-cokmesi-arkasindaki-
capalari-gizler]]) — arkadaki capalar da ayni kosumda olculur, rc yine 1 kalir.
"""

import collections
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
# 🔴 SENTETIK GIT TEK KAPIDAN (`tools/git_ortami.py`): miras alinan GIT_* baglami
# cagri yerinde DEGIL kanonik yardimcinin icinde temizlenir; `git init` ilk dal adi
# da orada civilenir (CI git 2.55 `master`, Okan'in makinesi `main` uretir).
# `try/except ImportError -> yerel kopya` YAZILMAZ: o dusus yolu ikizin ta kendisidir.
sys.path.insert(0, TOOLS)
from git_ortami import sentetik_git  # noqa: E402

CANLI = os.path.join(TOOLS, "d1-sync.py")

# Yalniz bu turun ekledigi/onardigi kollar hukum tasir. Baska bir kolun kirmiziya
# donmesi de RAPORLANIR (yan hasar), ama atif bu onekler uzerinden okunur.
MENZIL_ONEK = ("V85", "V86", "V87", "V88", "V89")

# Bir kolu degil, bataryanin IZOLASYON KAPISINI hedefleyen mutantlar bu adi kullanir:
# beklenen sonuc "bir iddia kirmizi yandi" degil, "kapi bataryayi SESLI durdurdu"dur.
KAPI_HEDEFI = "KAPI:KENDINI-TEST-IZOLASYON"
KAPI_DAMGASI = "KENDINI-TEST KILIT IZOLASYONU KURULAMADI"

# (ad, capa, yeni, beklenen_kollar)  beklenen_kollar=() -> KONTROL (hicbir kol olmemeli)
MUTANTLAR = [
    ("M1 linked worktree `commondir` OKUNMUYOR (her worktree AYRI inode kilitler)",
     '    ortak_dosya = os.path.join(gitdir, "commondir")\n'
     "    if os.path.isfile(ortak_dosya):",
     '    ortak_dosya = os.path.join(gitdir, "commondir")\n'
     "    if False and os.path.isfile(ortak_dosya):",
     ("V85b",)),

    ("M2 bozuk `.git` isaretcisi FAIL-CLOSED degil (var olmayan gitdir kabul edilir)",
     "        if not os.path.isdir(gitdir):\n"
     "            return None",
     "        if False:\n"
     "            return None",
     ("V85d",)),

    ("M3 KILIT YOLU YINE ALT SUREC ACIYOR (4 Eyl arizasinin ta kendisi)",
     "        ortak = _ortak_git_dizini(KOK)",
     '        _p = subprocess.run(["git", "-C", KOK, "rev-parse", "--git-common-dir"],\n'
     "                            capture_output=True, text=True, timeout=10)\n"
     "        ortak = (_p.stdout or '').strip() or None\n"
     "        if ortak and not os.path.isabs(ortak):\n"
     "            ortak = os.path.normpath(os.path.join(KOK, ortak))",
     ("V89",)),

    ("M4 yol TURETILEMEYINCE fail-closed DEGIL (sessizce koke duser)",
     '    if not ortak:\n'
     '        sys.exit("!! D1 YAZICI KILIDI OLCULEMEDI (git common-dir bulunamadi) — "\n'
     '                 "yazma fail-closed DURDU.\\n   kok=%s" % KOK)',
     "    if not ortak:\n"
     "        ortak = KOK",
     ("V88",)),

    ("M5 TEK UCUS kilidi wrangler() cagrisinda HIC ALINMIYOR",
     "    if not _YEREL_KILIT_SAHIBI:\n"
     '        kilit = yazici_kilidi_al(bekleme_sn=OKUYUCU_BEKLEME_SN, kol="ARAC")',
     "    if False:\n"
     '        kilit = yazici_kilidi_al(bekleme_sn=OKUYUCU_BEKLEME_SN, kol="ARAC")',
     ("V86", "V86d")),

    ("M6 YAZICI kolu `D1 yazici kilidi ALINDI` satirini BASMIYOR",
     '    if kol == "YAZICI" or duyuruldu:',
     "    if False:",
     ("V87b",)),

    # M7'nin oldurdugu sey bir IDDIA KOLU degil, IZOLASYON KAPISIDIR: civileme kalkinca
    # batarya CANLI depo inode'unu kilitleyecegi icin kapi bataryayi BASTAN durdurur.
    # Dogru skor "kol dustu" degil "kapi SESLI durdurdu"dur — bu yuzden ayri hedef adi.
    ("M7 kilit BATARYAYA CIVILENMIYOR (fikstur CANLI depo inode'unu kilitlerdi)",
     "    _KILIT_YOLU_ONBELLEK[0] = _kt_kilit\n",
     "",
     (KAPI_HEDEFI,)),

    ("KONTROL-1 `_ortak_git_dizini` yerel degisken adi degisti (davranis notr)",
     "    ortak_dosya = os.path.join(gitdir, \"commondir\")\n"
     "    if os.path.isfile(ortak_dosya):\n"
     "        with open(ortak_dosya, \"r\", encoding=\"utf-8\", errors=\"replace\") as f:",
     "    _ortak_yol = os.path.join(gitdir, \"commondir\")\n"
     "    if os.path.isfile(_ortak_yol):\n"
     "        with open(_ortak_yol, \"r\", encoding=\"utf-8\", errors=\"replace\") as f:",
     ()),

    ("KONTROL-2 fikstur kilit dizininin onek metni degisti (davranis notr)",
     'tempfile.mkdtemp(prefix="pruvo-d1-kt-kilit-")',
     'tempfile.mkdtemp(prefix="pruvo-d1-kt-kilitK2-")',
     ()),
]

BAYAT_CAPALAR = []
# 🔴 KOL KIMLIGI TAM ADDIR, ID DEGIL: bu bataryada IKI id CIFT KULLANILIYOR (olculdu:
# `V75b` ve `V76` ikiser kez basiliyor). Id'ye anahtarlanan bir sozluk ikinci kolu
# EZER ve o kolu olduren mutant "hayatta" gorunur ([[ad-iki-rolde-mutanti-golgeler]]).
# Bu yuzden GECTI satirinin TAM metni sayilir (Counter — mukerrer ad da dogru sayilir);
# id yalniz atif/menzil etiketi icin ADIN ILK JETONUNDAN okunur.
_GECTI = re.compile(r"^  GECTI  (.+?)\s*$", re.M)


def sentetik_kok_kur(gecici):
    """Gercek depoya SEMBOLIK BAG'la bakan, kendi `.git`i olan sentetik kok."""
    kok = os.path.join(gecici, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    p = sentetik_git(gecici, "init", "-q", kok, capture_output=True, text=True)
    if p.returncode != 0 or not os.path.isfile(os.path.join(kok, ".git", "config")):
        raise SystemExit("!! SENTETIK KOK KURULAMADI (rc=%s) — fail-closed." % p.returncode)
    for ad in os.listdir(KOK):
        if ad in (".git", "tools"):
            continue
        os.symlink(os.path.join(KOK, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        if ad == "d1-sync.py":
            continue
        os.symlink(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    return kok


def kollari_oku(kok):
    """Bataryayi KOS; GECTI kollarinin TAM ADLARINI (Counter) + rc + ham cikti dondur."""
    hedef = os.path.join(kok, "tools", "d1-sync.py")
    p = subprocess.run([sys.executable, hedef, "--kendini-test"],
                       capture_output=True, text=True, cwd=kok)
    return (collections.Counter(_GECTI.findall(p.stdout)), p.returncode,
            (p.stdout + p.stderr))


def kol_id(ad):
    return ad.split()[0] if ad.split() else ad


def dusenler(taban_gecti, mutant_gecti):
    """TABANDA yesil olup mutantta yesil OLMAYAN kollar (mukerrer ad dahil sayilir)."""
    dus = []
    for ad, adet in taban_gecti.items():
        eksik = adet - mutant_gecti.get(ad, 0)
        for _ in range(max(0, eksik)):
            dus.append(ad)
    return sorted(dus)


def govdeyi_yaz(kok, metin):
    with open(os.path.join(kok, "tools", "d1-sync.py"), "w", encoding="utf-8") as f:
        f.write(metin)


def sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def ana():
    canli_sha_once = sha256(CANLI)
    with open(CANLI, encoding="utf-8") as f:
        kaynak = f.read()

    gecici = tempfile.mkdtemp(prefix="pruvo-d1-kilit-mut-")
    oldur_ok = kontrol_ok = 0
    olduren = [m for m in MUTANTLAR if m[3]]
    kontrol = [m for m in MUTANTLAR if not m[3]]
    yama_tutmadi = ulasmadi = atif_tam = 0
    try:
        kok = sentetik_kok_kur(gecici)
        govdeyi_yaz(kok, kaynak)
        taban, taban_rc, taban_ham = kollari_oku(kok)
        taban_adet = sum(taban.values())
        print("── TABAN (sentetik duzlem, mutasyonsuz) ──")
        print("TABAN: GECTI=%d (benzersiz ad=%d) rc=%d"
              % (taban_adet, len(taban), taban_rc))
        if taban_rc != 0 or taban_adet == 0:
            print("!! TABAN KIRMIZI/BOS — mutasyon turu OLCEMEZ (fail-closed).")
            print(taban_ham[-2000:])
            return 1
        menzil_taban = sorted({kol_id(a) for a in taban
                               if kol_id(a).startswith(MENZIL_ONEK)})
        print("   menzil kollari (TABANDA YESIL): %d — %s"
              % (len(menzil_taban), ", ".join(menzil_taban)))

        for ad, capa, yeni, beklenen in MUTANTLAR:
            sayi = kaynak.count(capa)
            if sayi != 1:
                BAYAT_CAPALAR.append("%s — capa sayisi=%d" % (ad, sayi))
                print("!! %s — CAPA BULUNAMADI/COGUL (yama TUTMADI)" % ad)
                yama_tutmadi += 1
                continue
            govdeyi_yaz(kok, kaynak.replace(capa, yeni, 1))
            kollar, rc, ham = kollari_oku(kok)
            if beklenen == (KAPI_HEDEFI,):
                if rc != 0 and KAPI_DAMGASI in ham and not kollar:
                    oldur_ok += 1
                    atif_tam += 1
                    print("OLDURDU %s — IZOLASYON KAPISI SESLI DURDURDU (rc=%d, iddia "
                          "basilmadi): %s" % (ad, rc, KAPI_HEDEFI))
                else:
                    print("!! %s — HAYATTA/ATIFSIZ (rc=%d, damga=%s, iddia=%d)"
                          % (ad, rc, KAPI_DAMGASI in ham, sum(kollar.values())))
                continue
            if not kollar:
                print("!! %s — BATARYA HIC KOL BASMADI (mutant ULASMADI/COKTU)" % ad)
                print(ham[-800:])
                ulasmadi += 1
                continue
            dusen = dusenler(taban, kollar)
            dusen_id = [kol_id(a) for a in dusen]
            if beklenen:
                eksik = [b for b in beklenen if b not in dusen_id]
                if dusen and not eksik:
                    oldur_ok += 1
                    atif_tam += 1
                    yan = [i for i in dusen_id if i not in beklenen]
                    print("OLDURDU %s — KIRMIZI=%d, hedef kollar dustu: %s%s"
                          % (ad, len(dusen), ",".join(beklenen),
                             ("  (yan hasar: %s)" % ",".join(yan)) if yan else ""))
                else:
                    print("!! %s — HAYATTA/ATIFSIZ (dusen=%s, beklenen=%s)"
                          % (ad, ",".join(dusen_id) or "YOK", ",".join(beklenen)))
            else:
                if dusen:
                    print("!! %s — KONTROL OLDURDU (esdeger olmali): %s"
                          % (ad, ",".join(dusen_id)))
                else:
                    kontrol_ok += 1
                    print("KONTROL YESIL %s (GECTI=%d, tabanla BIREBIR)"
                          % (ad, sum(kollar.values())))
        govdeyi_yaz(kok, kaynak)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    canli_sha_sonra = sha256(CANLI)
    print("\nMUTANT=%d/%d OLDUREN=%d/%d KONTROL=%d/%d YAMA_TUTMADI=%d ULASMADI=%d "
          "HEDEF_KOL_ATFI=%d/%d"
          % (oldur_ok + kontrol_ok, len(MUTANTLAR), oldur_ok, len(olduren),
             kontrol_ok, len(kontrol), yama_tutmadi, ulasmadi, atif_tam, len(olduren)))
    print("CANLI SHA256 ONCE=%s SONRA=%s — %s"
          % (canli_sha_once[:16], canli_sha_sonra[:16],
             "ESIT (canli govdeye DOKUNULMADI)"
             if canli_sha_once == canli_sha_sonra else "🔴 DEGISTI"))
    if BAYAT_CAPALAR:
        print("BAYAT CAPALAR:")
        for b in BAYAT_CAPALAR:
            print("  - " + b)
    tamam = (oldur_ok == len(olduren) and kontrol_ok == len(kontrol)
             and not BAYAT_CAPALAR and not yama_tutmadi and not ulasmadi
             and canli_sha_once == canli_sha_sonra)
    print("mutasyon turu %s." % ("TEMIZ" if tamam else "🔴 KIRMIZI"))
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(ana())

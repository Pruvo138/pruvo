#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ev-sahip-kapisi.py — N2 (A): KIRMIZI KOSUMUN SAHIBINI MAKINECE BUL.

Okan'in vakasi (birebir): "MaCiT 100-100 urun ekliyor, iletiyi gormedi, isine
devam etti; tamirat yapilmadigi icin tum mimarlar MaCiT'i bekledi."
HUKUM: **mesaj kacar, KAPI kacmaz.** Kapinin kacmamasi icin once kirmizinin
SAHIBI deterministik olarak bilinmelidir. LLM YOK, tahmin YOK.

  kirmizi kosum -> headSha -> degisen dosyalar -> serit -> EV

TEK KAYNAK
----------
Yol->ev eslemesi YALNIZ `tools/ev-serit-haritasi.tsv`de yasar. Bu dosya o
haritanin TEK okuyucusudur; `gozcu.py` ve `parti-kapisi.py` kendi listelerini
TUTMAZ, buradan TURETIR (importlib). Ikinci kopya YASAK
([[ikiz-tanim-sessiz-ayrisma]]).

Kademeli ikinci kaynak DEGIL, DAHA SPESIFIK kaynak: `tools/sahiplik-
haritasi.tsv` bir KAPI/NOBET BETIGININ evini insan karariyla atar. O dosyada
TAM YOL olarak gecen bir betik icin onun EV'i gecerlidir (yol-oneki tahminini
EZER). Iki harita ayni soruyu iki kez yanitlamaz: biri betik-duzeyi ATAMA,
digeri yol-duzeyi TUREME.

DORT KOL (her birinin MUTANTI ve HEDEF KOL ATFI vardir — K182)
--------------------------------------------------------------
  N2A-TEK         tek ev eslesti          -> SAHIP = o ev
  N2A-COK         >=2 ev eslesti          -> SAHIP = KraL, SEBEP=cok-seritli
  N2A-ARTIK       eslesmeyen yol var      -> SAHIP = KraL, SEBEP=eslesmeyen
                                             (ARTIK KOVA — "varsayilan" DEGIL)
  N2A-OLCULEMEDI  harita/git okunamadi    -> SAHIP = KraL, SEBEP=olculemedi
                                             (FAIL-CLOSED: sessiz yesil YOK)

ORTAK duzlem (DEVAM.md, README.md, CLAUDE.md...) ev kumesine SAYILMAZ: tek
basina "cok-seritli" URETMEZ ama "eslesmeyen" de SAYILMAZ. Yalniz ORTAK dosya
degistiyse SEBEP=ortak-duzlem ve SAHIP=KraL (son mercii).

KABUL (calistirilabilir)
------------------------
  python3 tools/ev-sahip-kapisi.py --kendini-test
    son satir + rc=0:
      MUTANT=5/5 HEDEF_KOL_ATFI=5/5 KONTROL=3/3

  python3 tools/ev-sahip-kapisi.py --sha <sha>
    son satir: SAHIP=<ev> SEBEP=<sebep> SERIT=<...> DOSYA=<n>

  python3 tools/ev-sahip-kapisi.py --dosyalar urunler.json
    ayni son satir bicimi (git'siz, dogrudan yol listesiyle).

Cikis kodu: 0 = hukum verildi · 2 = OLCULEMEDI (fail-closed).
"""

import argparse
import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile


# ---- sabitler -----------------------------------------------------------------
HARITA_RELATIF = "tools/ev-serit-haritasi.tsv"
BETIK_HARITA_RELATIF = "tools/sahiplik-haritasi.tsv"

# ORTAK = hicbir evin tekelinde olmayan duzlem. Ev kumesine SAYILMAZ.
ORTAK_EV = "ORTAK"

# Bilinen evler (ORTAK haric). Haritada bunlarin disinda bir EV gorulurse
# satir BOZUK sayilir — sessizce yutulmaz (fail-closed).
BILINEN_EVLER = ("KraL", "MaCiT", "HocA", "ArTisT", "TeKiN")

# Son mercii / artik kova. "varsayilan" DEGIL: SEBEP her zaman yazilir.
SON_MERCII = "KraL"

# Kol jetonlari — cikti satirinda ve mutant dogrulamada kullanilir. Kol ATIFI
# SEBEP alaninda tasinir; her mutant YALNIZ kendi kolunu kirmizi yakmalidir.
N2A_TEK_JETON        = "N2A-TEK"
N2A_COK_JETON        = "N2A-COK"
N2A_ARTIK_JETON      = "N2A-ARTIK"
N2A_OLCULEMEDI_JETON = "N2A-OLCULEMEDI"
N2A_BETIK_JETON      = "N2A-BETIK"

SEBEP_TEK        = "tek-serit"
SEBEP_COK        = "cok-seritli"
SEBEP_ARTIK      = "eslesmeyen"
SEBEP_ORTAK      = "ortak-duzlem"
SEBEP_OLCULEMEDI = "olculemedi"

SEBEP_KOLU = {
    SEBEP_TEK:        N2A_TEK_JETON,
    SEBEP_COK:        N2A_COK_JETON,
    SEBEP_ARTIK:      N2A_ARTIK_JETON,
    SEBEP_ORTAK:      N2A_ARTIK_JETON,   # ortak-duzlem de artik kovanin kolu
    SEBEP_OLCULEMEDI: N2A_OLCULEMEDI_JETON,
}

MUTANT_HEDEF = {
    "M1": N2A_TEK_JETON,
    "M2": N2A_COK_JETON,
    "M3": N2A_ARTIK_JETON,
    "M4": N2A_OLCULEMEDI_JETON,
    "M5": N2A_BETIK_JETON,
}

RC_HUKUM = 0
RC_OLCULEMEDI = 2


# ------------------------------------------------------------------------------
# YARDIMCILAR
# ------------------------------------------------------------------------------
def repo_kok(baslangic=None):
    """Bu betigin bulundugu depo kokunu doner (tools/'un ust dizini)."""
    if baslangic:
        return os.path.abspath(baslangic)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _normalize(yol):
    """Yolu depo-koku-goreli POSIX bicime cevirir. `./` ve ters bolu temizlenir."""
    if not isinstance(yol, str):
        return ""
    y = yol.strip().replace("\\", "/")
    while y.startswith("./"):
        y = y[2:]
    return y.lstrip("/")


# ------------------------------------------------------------------------------
# HARITA YUKLEME (TEK KAYNAK)
# ------------------------------------------------------------------------------
def harita_yukle(kok=None, *, mutant=None):
    """`tools/ev-serit-haritasi.tsv`yi okur.

    Return: (satirlar, hata). `satirlar` = [(oncelik, desen, serit, ev, sira)]
    ONCELIK'e gore BUYUKTEN kucuge, esitlikte dosya sirasina gore sirali.

    FAIL-CLOSED: dosya yoksa / okunamazsa / TEK bir veri satiri bile
    uretilemezse `hata` dolu doner ve cagiran OLCULEMEDI'ye duser.
    M4 mutanti bu kolu FAIL-OPEN yapar (bos harita ile devam) — yakalanmali.
    """
    kok = repo_kok(kok)
    yol = os.path.join(kok, HARITA_RELATIF)
    try:
        with open(yol, encoding="utf-8") as f:
            ham = f.read()
    except Exception as e:
        if mutant == "M4":
            # FAIL-OPEN mutanti: harita okunamadi ama "bos harita" ile devam.
            return [], None
        return [], "harita okunamadi: %s (%r)" % (yol, e)

    satirlar = []
    bozuk = 0
    for sira, satir in enumerate(ham.splitlines()):
        if not satir.strip() or satir.lstrip().startswith("#"):
            continue
        parcalar = satir.split("\t")
        if len(parcalar) < 4:
            bozuk += 1
            continue
        onc_ham, desen, serit, ev = (p.strip() for p in parcalar[:4])
        if onc_ham.upper() == "ONCELIK":     # baslik satiri
            continue
        try:
            oncelik = int(onc_ham)
        except ValueError:
            bozuk += 1
            continue
        if not desen or not ev:
            bozuk += 1
            continue
        if ev != ORTAK_EV and ev not in BILINEN_EVLER:
            bozuk += 1
            continue
        satirlar.append((oncelik, desen, serit, ev, sira))

    if not satirlar:
        if mutant == "M4":
            return [], None
        return [], "harita BOS ya da tumuyle bozuk: %s (bozuk satir=%d)" % (yol, bozuk)

    satirlar.sort(key=lambda r: (-r[0], r[4]))
    return satirlar, None


def betik_harita_yukle(kok=None, *, mutant=None):
    """`tools/sahiplik-haritasi.tsv`den {TAM_YOL: EV} sozlugu uretir.

    Bu harita YOL-ONEKI tahminini EZER (daha spesifik: insan atamasi).
    Okunamazsa BOS doner ve hukum yol-oneki haritasindan verilir — burasi
    bilerek fail-open: betik atamasi bir INCELIK, temel hukum degil.
    M5 mutanti bu kolu tumuyle devre disi birakir.
    """
    if mutant == "M5":
        return {}
    kok = repo_kok(kok)
    yol = os.path.join(kok, BETIK_HARITA_RELATIF)
    out = {}
    try:
        with open(yol, encoding="utf-8") as f:
            ham = f.read()
    except Exception:
        return out
    for satir in ham.splitlines():
        if not satir.strip() or satir.lstrip().startswith("#"):
            continue
        p = satir.split("\t")
        if len(p) < 3:
            continue
        betik_yolu = _normalize(p[1])
        ev = p[2].strip()
        if not betik_yolu or ev not in BILINEN_EVLER:
            continue
        out[betik_yolu] = ev
    return out


# ------------------------------------------------------------------------------
# TEK DOSYA -> EV
# ------------------------------------------------------------------------------
def dosya_evi(yol, satirlar, betik_harita=None):
    """Bir yolu (EV, SERIT, KAYNAK) uclusune cozer; eslesmezse (None, None, None).

    KAYNAK: "betik" (sahiplik-haritasi.tsv atamasi) | "harita" (yol oneki).
    """
    y = _normalize(yol)
    if not y:
        return (None, None, None)
    if betik_harita:
        ev = betik_harita.get(y)
        if ev:
            return (ev, "betik", "betik")
    for _onc, desen, serit, ev, _sira in satirlar:
        if fnmatch.fnmatchcase(y, desen):
            return (ev, serit, "harita")
    return (None, None, None)


# ------------------------------------------------------------------------------
# KARAR FONKSIYONU — dort kol
# ------------------------------------------------------------------------------
def sahip_bul(dosyalar, *, kok=None, mutant=None):
    """Degisen dosya listesinden SAHIP evi turetir.

    Return: {"SAHIP", "SEBEP", "KOL", "SERITLER", "EVLER", "DOSYA",
             "ESLESMEYEN", "HATA", "AYRINTI"}
    """
    sonuc = {"SAHIP": SON_MERCII, "SEBEP": SEBEP_OLCULEMEDI,
             "KOL": N2A_OLCULEMEDI_JETON, "SERITLER": [], "EVLER": [],
             "DOSYA": 0, "ESLESMEYEN": [], "HATA": None, "AYRINTI": []}

    satirlar, hata = harita_yukle(kok, mutant=mutant)
    if hata:
        sonuc["HATA"] = hata
        return sonuc
    if not isinstance(dosyalar, (list, tuple)) or not dosyalar:
        sonuc["HATA"] = "degisen dosya listesi BOS (headSha cozulemedi?)"
        return sonuc

    betik_harita = betik_harita_yukle(kok, mutant=mutant)

    evler = set()
    seritler = set()
    eslesmeyen = []
    ortak_var = False
    ayrinti = []
    temiz = [_normalize(d) for d in dosyalar if _normalize(d)]
    for d in temiz:
        ev, serit, kaynak = dosya_evi(d, satirlar, betik_harita)
        ayrinti.append((d, ev or "-", serit or "-", kaynak or "-"))
        if ev is None:
            eslesmeyen.append(d)
            continue
        if ev == ORTAK_EV:
            ortak_var = True
            continue
        evler.add(ev)
        if serit:
            seritler.add(serit)

    sonuc["DOSYA"] = len(temiz)
    sonuc["EVLER"] = sorted(evler)
    sonuc["SERITLER"] = sorted(seritler)
    sonuc["ESLESMEYEN"] = eslesmeyen
    sonuc["AYRINTI"] = ayrinti

    if not temiz:
        sonuc["HATA"] = "yol listesi normalize sonrasi BOS"
        return sonuc

    # --- N2A-ARTIK: eslesmeyen yol varsa hukum ARTIK KOVA'dir --------------
    # Bu kol N2A-COK'tan ONCE gelir: harita boslugu, cok-seritlilik
    # goruntusunun ARKASINA SAKLANMAMALIDIR (boslugu gormek istiyoruz).
    if eslesmeyen and mutant != "M3":
        sonuc["SAHIP"] = SON_MERCII
        sonuc["SEBEP"] = SEBEP_ARTIK
        sonuc["KOL"] = N2A_ARTIK_JETON
        return sonuc

    # --- N2A-COK: >=2 ev ---------------------------------------------------
    if len(evler) >= 2:
        if mutant == "M2":
            # M2: cok-seritli vakayi ILK eve yikar (son mercii kolu olur).
            sonuc["SAHIP"] = sorted(evler)[0]
            sonuc["SEBEP"] = SEBEP_TEK
            sonuc["KOL"] = N2A_TEK_JETON
            return sonuc
        sonuc["SAHIP"] = SON_MERCII
        sonuc["SEBEP"] = SEBEP_COK
        sonuc["KOL"] = N2A_COK_JETON
        return sonuc

    # --- N2A-TEK: tam 1 ev -------------------------------------------------
    if len(evler) == 1:
        if mutant == "M1":
            # M1: tek-serit kolu oldurulur — her sey cok-seritli sayilir.
            sonuc["SAHIP"] = SON_MERCII
            sonuc["SEBEP"] = SEBEP_COK
            sonuc["KOL"] = N2A_COK_JETON
            return sonuc
        sonuc["SAHIP"] = sorted(evler)[0]
        sonuc["SEBEP"] = SEBEP_TEK
        sonuc["KOL"] = N2A_TEK_JETON
        return sonuc

    # --- yalniz ORTAK duzlem ------------------------------------------------
    if ortak_var:
        sonuc["SAHIP"] = SON_MERCII
        sonuc["SEBEP"] = SEBEP_ORTAK
        sonuc["KOL"] = N2A_ARTIK_JETON
        return sonuc

    # --- buraya M3 mutantiyla dusulur (eslesmeyen yutuldu) ------------------
    if mutant == "M3":
        sonuc["SAHIP"] = SON_MERCII
        sonuc["SEBEP"] = SEBEP_TEK          # sessiz yesil: bosluk GORUNMEZ
        sonuc["KOL"] = N2A_TEK_JETON
        return sonuc

    sonuc["SEBEP"] = SEBEP_ARTIK
    sonuc["KOL"] = N2A_ARTIK_JETON
    return sonuc


# ------------------------------------------------------------------------------
# GIT: sha -> degisen dosyalar
# ------------------------------------------------------------------------------
def commit_dosyalari(kok, sha, *, timeout=20):
    """`git show --name-only` ile bir commit'in degistirdigi yollari doner.

    Return: (dosyalar, hata). Merge commit'lerde `-m --first-parent` ile ilk
    ebeveyne gore fark alinir (merge'un BOS gorunmesi engellenir).
    """
    if not sha or not isinstance(sha, str):
        return [], "sha bos"
    git = shutil.which("git")
    if not git:
        return [], "git bulunamadi"
    komut = [git, "-C", kok, "show", "--pretty=format:", "--name-only",
             "-m", "--first-parent", sha]
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return [], "git cagrisi basarisiz: %r" % e
    if p.returncode != 0:
        return [], "git rc=%d: %s" % (p.returncode, (p.stderr or "").strip()[:200])
    out = []
    gorulen = set()
    for satir in (p.stdout or "").splitlines():
        y = _normalize(satir)
        if y and y not in gorulen:
            gorulen.add(y)
            out.append(y)
    if not out:
        return [], "commit BOS gorunuyor (degisen dosya yok): %s" % sha
    return out, None


def kirmizi_sahibi(kok, sha, *, mutant=None):
    """Kirmizi kosumun headSha'sindan SAHIP hukmunu turetir. TEK GIRIS NOKTASI:
    gozcu.py ve parti-kapisi.py bu fonksiyonu cagirir, kendi mantigini YAZMAZ."""
    dosyalar, hata = commit_dosyalari(kok, sha)
    if hata:
        return {"SAHIP": SON_MERCII, "SEBEP": SEBEP_OLCULEMEDI,
                "KOL": N2A_OLCULEMEDI_JETON, "SERITLER": [], "EVLER": [],
                "DOSYA": 0, "ESLESMEYEN": [], "HATA": hata, "AYRINTI": []}
    return sahip_bul(dosyalar, kok=kok, mutant=mutant)


def hukum_satiri(s):
    """Makine-okur tek satir. Kabul testleri BU satiri arar."""
    return ("SAHIP=%s SEBEP=%s KOL=%s SERIT=%s EV_SAYISI=%d DOSYA=%d "
            "ESLESMEYEN=%d") % (
        s["SAHIP"], s["SEBEP"], s["KOL"],
        ",".join(s["SERITLER"]) or "-", len(s["EVLER"]),
        s["DOSYA"], len(s["ESLESMEYEN"]))


# ------------------------------------------------------------------------------
# KENDINI-TEST — 5 mutant + hedef kol atfi + 3 kontrol
# ------------------------------------------------------------------------------
# Sentetik vakalar: (ad, dosyalar, beklenen_sahip, beklenen_sebep)
VAKALAR = (
    ("veri",        ["urunler.json", "urun-kaynaklari.json"], "MaCiT", SEBEP_TEK),
    ("worker",      ["worker/src/index.js"],                  "HocA",  SEBEP_TEK),
    ("jenerator",   ["jenerator/uret.py"],                    "TeKiN", SEBEP_TEK),
    ("pazarlama",   ["sitemap.xml"],                          "ArTisT", SEBEP_TEK),
    ("site",        ["index.html", "tools/build.py"],         "KraL",  SEBEP_TEK),
    ("cok-seritli", ["urunler.json", "worker/src/index.js"],  "KraL",  SEBEP_COK),
    ("artik",       ["bilinmeyen-dizin/dosya.txt"],           "KraL",  SEBEP_ARTIK),
    ("ortak",       ["DEVAM.md"],                             "KraL",  SEBEP_ORTAK),
)


def _vaka_kos(kok, mutant=None):
    """Tum vakalari kosar; {vaka_adi: sonuc} doner."""
    return {ad: sahip_bul(dosyalar, kok=kok, mutant=mutant)
            for ad, dosyalar, _b_sahip, _b_sebep in VAKALAR}


def _normal_dogru_mu(sonuclar):
    """Mutantsiz kosumda TUM vakalar beklendigi gibi mi?"""
    for ad, _d, b_sahip, b_sebep in VAKALAR:
        s = sonuclar.get(ad) or {}
        if s.get("SAHIP") != b_sahip or s.get("SEBEP") != b_sebep:
            return False, "%s: SAHIP=%s SEBEP=%s (beklenen %s/%s)" % (
                ad, s.get("SAHIP"), s.get("SEBEP"), b_sahip, b_sebep)
    return True, "8/8 vaka beklendigi gibi"


def _kol_kirmizi_mi(normal, mutantli, kol):
    """Bir KOLUN mutantla kirildigini ve DIGER kollarin ayakta kaldigini olcer.

    Return: (hedef_kirmizi, yan_eksen_yesil, ayrinti)
      hedef_kirmizi  : bu kolu kullanan EN AZ BIR vaka mutantla degisti
      yan_eksen_yesil: bu kolu KULLANMAYAN vakalarin HICBIRI degismedi
    """
    hedef_kirmizi = False
    yan_bozulan = []
    for ad, _d, _bs, _bsb in VAKALAR:
        n = normal.get(ad) or {}
        m = mutantli.get(ad) or {}
        ayni = (n.get("SAHIP") == m.get("SAHIP") and n.get("SEBEP") == m.get("SEBEP"))
        if n.get("KOL") == kol:
            if not ayni:
                hedef_kirmizi = True
        else:
            if not ayni:
                yan_bozulan.append(ad)
    return hedef_kirmizi, (not yan_bozulan), ",".join(yan_bozulan) or "-"


def kendini_test(kok):
    """5 mutant + hedef kol atfi + 3 kontrol. Her mutant YALNIZ kendi kolunu
    kirmizi yakmali; yan eksen yesil kalmali (K182)."""
    print("N2A EV SAHIP KAPISI — KENDINI-TEST")
    print("depo koku: %s" % kok)
    print("harita   : %s" % os.path.join(kok, HARITA_RELATIF))
    print("")

    normal = _vaka_kos(kok, mutant=None)
    dogru, mesaj = _normal_dogru_mu(normal)
    print("TABAN (mutantsiz): %s" % mesaj)
    for ad, _d, _bs, _bsb in VAKALAR:
        print("  %-12s %s" % (ad, hukum_satiri(normal[ad])))
    print("")
    if not dogru:
        print("TABAN KIRMIZI — mutant olcumu ANLAMSIZ.")
        print("MUTANT=0/5 HEDEF_KOL_ATFI=0/5 KONTROL=0/3")
        return 1

    mutant_sayaci = 0
    atif_sayaci = 0
    for ad in sorted(MUTANT_HEDEF):
        kol = MUTANT_HEDEF[ad]
        print("MUTANT %s -> hedef kol %s" % (ad, kol))
        if ad == "M4":
            # M4 (fail-open) yalniz harita OKUNAMADIGINDA gorunur: gecici bos
            # bir depo kokunde kosulur (harita YOK).
            gecici = tempfile.mkdtemp(prefix="n2a-m4-")
            try:
                os.makedirs(os.path.join(gecici, "tools"), exist_ok=True)
                normal_yok = sahip_bul(["urunler.json"], kok=gecici, mutant=None)
                mutantli_yok = sahip_bul(["urunler.json"], kok=gecici, mutant="M4")
                hedef_kirmizi = (normal_yok["KOL"] == N2A_OLCULEMEDI_JETON
                                 and mutantli_yok["KOL"] != N2A_OLCULEMEDI_JETON)
                # yan eksen: harita VARKEN M4 hicbir seyi degistirmemeli
                mutantli_var = _vaka_kos(kok, mutant="M4")
                _hk, yan_yesil, yan = _kol_kirmizi_mi(normal, mutantli_var, kol)
                print("  haritasiz kok: normal KOL=%s | mutant KOL=%s"
                      % (normal_yok["KOL"], mutantli_yok["KOL"]))
                print("  yan eksen (harita VAR): bozulan=%s" % yan)
            finally:
                shutil.rmtree(gecici, ignore_errors=True)
        else:
            mutantli = _vaka_kos(kok, mutant=ad)
            hedef_kirmizi, yan_yesil, yan = _kol_kirmizi_mi(normal, mutantli, kol)
            degisenler = [v for v, _d, _bs, _bsb in VAKALAR
                          if (normal[v]["SAHIP"], normal[v]["SEBEP"])
                          != (mutantli[v]["SAHIP"], mutantli[v]["SEBEP"])]
            print("  degisen vakalar: %s" % (",".join(degisenler) or "-"))
            print("  yan eksen bozulan: %s" % yan)
            if ad == "M5":
                # M5 (betik haritasi devre disi) yol-oneki haritasiyla AYNI
                # sonucu verebilir; kolun GERCEKTEN oldugunu ayri olcuyoruz:
                # sahiplik-haritasi.tsv'de KraL DISI eve atanmis bir tools/
                # betigi bul ve o yolu vakaya sok.
                bh = betik_harita_yukle(kok)
                aday = None
                for yol_, ev_ in sorted(bh.items()):
                    if yol_.startswith("tools/") and ev_ != "KraL":
                        aday = (yol_, ev_)
                        break
                if aday:
                    yol_, ev_ = aday
                    n5 = sahip_bul([yol_], kok=kok, mutant=None)
                    m5 = sahip_bul([yol_], kok=kok, mutant="M5")
                    hedef_kirmizi = (n5["SAHIP"] == ev_ and m5["SAHIP"] != ev_)
                    print("  betik atamasi: %s -> normal SAHIP=%s | mutant SAHIP=%s "
                          "(beklenen ev=%s)" % (yol_, n5["SAHIP"], m5["SAHIP"], ev_))
                else:
                    hedef_kirmizi = False
                    print("  betik atamasi: KraL disi tools/ betigi BULUNAMADI "
                          "— kol OLCULEMEDI")

        if hedef_kirmizi:
            mutant_sayaci += 1
            print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
        else:
            print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        if hedef_kirmizi and yan_yesil:
            atif_sayaci += 1
            print("  ATIF : hedef kol kirmizi + yan eksen YESIL")
        else:
            print("  ATIF : KUSUR (hedef kol ya da yan eksen tutmadi)")
        print("")

    # --- KONTROLLER --------------------------------------------------------
    kontrol = 0

    # K1: bos dosya listesi -> OLCULEMEDI (sessiz KraL DEGIL)
    k1 = sahip_bul([], kok=kok)
    k1_ok = (k1["SEBEP"] == SEBEP_OLCULEMEDI and k1["KOL"] == N2A_OLCULEMEDI_JETON)
    print("KONTROL K1 bos liste -> OLCULEMEDI: %s (%s)"
          % ("GECTI" if k1_ok else "KUSUR", hukum_satiri(k1)))
    kontrol += 1 if k1_ok else 0

    # K2: cok-seritli hukmunde SEBEP acikca yazilir (spec §2 sarti)
    k2 = sahip_bul(["urunler.json", "worker/src/index.js"], kok=kok)
    k2_metin = hukum_satiri(k2)
    k2_ok = ("SAHIP=KraL" in k2_metin and "SEBEP=cok-seritli" in k2_metin)
    print("KONTROL K2 cok-seritli SEBEP yazar: %s (%s)"
          % ("GECTI" if k2_ok else "KUSUR", k2_metin))
    kontrol += 1 if k2_ok else 0

    # K3: ORTAK dosya tek basina cok-seritli URETMEZ (veri + DEVAM.md -> MaCiT)
    k3 = sahip_bul(["urunler.json", "DEVAM.md"], kok=kok)
    k3_ok = (k3["SAHIP"] == "MaCiT" and k3["SEBEP"] == SEBEP_TEK)
    print("KONTROL K3 ORTAK duzlem evi bozmaz: %s (%s)"
          % ("GECTI" if k3_ok else "KUSUR", hukum_satiri(k3)))
    kontrol += 1 if k3_ok else 0

    print("")
    print("MUTANT=%d/5 HEDEF_KOL_ATFI=%d/5 KONTROL=%d/3"
          % (mutant_sayaci, atif_sayaci, kontrol))
    return 0 if (mutant_sayaci == 5 and atif_sayaci == 5 and kontrol == 3) else 1


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--sha", help="kirmizi kosumun headSha'si")
    ap.add_argument("--dosyalar", nargs="+", help="dogrudan yol listesi (git'siz)")
    ap.add_argument("--kok", help="depo koku (varsayilan: bu betigin deposu)")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--harita", action="store_true", help="yuklu haritayi bas")
    args = ap.parse_args(argv)

    kok = repo_kok(args.kok)

    if args.kendini_test:
        return kendini_test(kok)

    if args.harita:
        satirlar, hata = harita_yukle(kok)
        if hata:
            print("HATA: %s" % hata)
            print("HARITA_SATIR=0")
            return RC_OLCULEMEDI
        for onc, desen, serit, ev, _s in satirlar:
            print("%4d  %-32s %-12s %s" % (onc, desen, serit, ev))
        print("HARITA_SATIR=%d" % len(satirlar))
        return RC_HUKUM

    if args.sha:
        s = kirmizi_sahibi(kok, args.sha)
    elif args.dosyalar:
        s = sahip_bul(args.dosyalar, kok=kok)
    else:
        ap.print_help()
        return RC_OLCULEMEDI

    print("N2A EV SAHIP KAPISI")
    for yol, ev, serit, kaynak in s["AYRINTI"]:
        print("  %-48s -> EV=%-8s SERIT=%-10s KAYNAK=%s" % (yol, ev, serit, kaynak))
    if s["HATA"]:
        print("HATA: %s" % s["HATA"])
    print(hukum_satiri(s))
    return RC_OLCULEMEDI if s["SEBEP"] == SEBEP_OLCULEMEDI else RC_HUKUM


if __name__ == "__main__":
    sys.exit(main())

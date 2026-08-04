#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""diriltme-kapisi.py — SESSIZ GERI GITME nobetcisi (IKI EKSEN, TEK GECMIS TARAMASI).

🔴 DOKTRIN (bu dosyanin varlik sebebi, tek cumle):
    `urunler.json` cakismasi SATIR-DUZEYI MERGE ile COZULMEZ; urun verisi tasinacaksa
    TEMIZ DAL + YALNIZ KOD DOSYALARI, veri `tools/duzelt.py` ile.

Kapi IKI ekseni AYNI TEK gecmis taramasindan besler:
  EKSEN 1 — KAYIT (id): gecmiste SILINMIS bir urun id'si geri gelmis mi.
  EKSEN 2 — ALAN     : HEM ONCE HEM SONRA var olan bir kaydin bir ALANI, gecmiste
                       GORULMUS VE SONRA TERK EDILMIS bir degere donmus mu.

⚠️ NEDEN TEK DOSYA / TEK GECIS (KraL karari, 30 Tem): silinmis-id kumesini tureten
gecmis taramasi (801 commit, ~70 MB diff) ZATEN kosuyor. Ikinci bir nobetci dosyasi =
ikinci CI adimi = ikinci 70 MB tarama. Alan ekseni bu yuzden AYRI DOSYA DEGIL, ayni
`git log` cikti akisindan beslenen IKINCI EKSENDIR.

--------------------------------------------------------------------------------
EKSEN 1 — KAYIT (id) DIRILTMESI
--------------------------------------------------------------------------------
OLCULEN GERCEK OLAY (30 Tem): bir mühendis dali main'e alinirken `urunler.json`'un
SATIR-DUZEYI 3-YOLLU MERGE'i, main'in BILEREK sildigi 2 kaydi GERI DIRILTTI. Biri
YASAK TUR (olcekli maket/model), biri dogrudan emirle silinmisti. Ustune
`tools/urunler-guard.py` YAPISI GEREGI "HEAD'de olup calisma agacindan silinmis urunu
geri ekler" oldugu icin elle yapilan duzeltme IKI KEZ ezildi (15068 -> 15070).

IDDIA: <taban> durumunda GECMISTE SILINMIS olan bir urun id'si <yeni> durumunda GERI
GELMISSE -> KIRMIZI. YENI id eklemek SERBESTTIR (MaCiT'in normal ekleme akisi kapiyi
HIC tetiklemez, bkz. V9/V10 yanlis-pozitif nobetleri).

SILINMIS ID KUMESI GIT GECMISINDEN TURETILIR (ELLE LISTE TUTULMAZ — bayatlar):
    git log -U0 -p --first-parent --format='%H' <taban> -- urunler.json
  * `+` satirlarinda gorulen HER id = "bu id bir zamanlar katalogda VARDI" (ever_seen).
    Dosyanin ilk hali de bir `+` blogu oldugu icin baslangic icerigi de kapsanir.
  * silinmis = ever_seen - <taban>'daki id'ler.
  * `--first-parent`: bu depoda tek yayin hatti main'dir; merge commit'in diffi ILK
    ebeveynine gore alinir -> bir dalda yapilip merge edilen silme de gorunur, ayni
    diff IKI KEZ sayilmaz. Siralama/yeniden dizme sonucu ETKILEMEZ.

--------------------------------------------------------------------------------
EKSEN 2 — ALAN GERILEMESI (30 Tem'de IKINCI KEZ olculen sinif)
--------------------------------------------------------------------------------
OLCULEN GERCEK OLAY (30 Tem, ayni gun): bir dalin tepesi, main'in yaptigi KAPAK
GORSELI duzeltmesini geri aliyordu. `git merge-tree --write-tree main <dal>` sonucunda
`...-p1-v2.jpg` sayisi 1 -> 0 dusuyordu. Kayit SILINMEMISTI, id ekseni bunu GORMEZ;
sayi tutar, sema tutar, mukerrer yoktur. Tek sapan sey bir ALANIN eski degerine
donmus olmasidir -> site YANLIS gosterir, hicbir yerde alarm calmaz.

IDDIA: bir kayit HEM tabanda HEM yenide varsa ve kapsamdaki bir ALANININ yenideki
degeri, O KAYDIN gecmisinde `+` olarak GORULMUS ve `-` olarak TERK EDILMIS bir deger
ise -> KIRMIZI.
  * ILERI YON (gecmiste HIC gorulmemis yeni deger) -> YESIL.
  * Alan hic degismemisse -> YESIL.
  * Alanin SIRASI degisip icerigi ayni kalmissa (or. gorseller yeniden dizilmis)
    -> YESIL: karsilastirma NORMALLESTIRILMIS SATIR KUMESI uzerinden yapilir.
  * BASKA bir kaydin terk ettigi deger HUKUM URETMEZ (attribution kayda ozeldir).

KAPSAM ALANLARI — SABIT LISTE (`KAPSAM_ALANLARI`), "tum alanlar" DEGIL:
    gorseller · fiyat · eski_fiyat · baslik · aciklama · kategori · lisans · parametrik
  Gerekce: hepsi (a) MUSTERIYE GORUNUR ya da TICARI/HUKUKI (fiyat, lisans atfi),
  (b) ELLE ya da `duzelt.py` ile yazilan TEK-YAZARLI kararlardir — yani bir merge'in
  sessizce geri alabilecegi seylerdir.
KAPSAM DISI ve NEDENI (kapsami buyutmek pozitif nobetciyi oldurur,
[[kapi-kapsam-genisletme-tuzagi]]):
  * `id` — EKSEN 1'in konusu; burada tekrar olculse cift alarm uretirdi.
  * `marka` — TOPLU normalize edilen dizi (marka listesi/limit araclari yeniden yazar);
    ileri-geri salinimi MESRUDUR, kapiya girerse surekli sahte-kirmizi uretir.
  * `konfigur`, `tavsiyeFilament` — TURETILMIS artefaktlar; jeneratör/filament araclari
    toplu yeniden uretir ([[konfigur-artefakt-yenileme]]). Eski degere donmeleri bir
    KARARIN geri alinmasi degil, bir HESABIN yeniden kosmasidir.

📌 BEYAN EDILEN SINIR — ALAN SILINMESI OLCULMEZ: yenide alan HIC YOKSA (tabanda vardi)
  bu eksen hukum VERMEZ, `BILGI` satiri basar (A16/A16b). Sebep: "gecmiste bu kayitta
  bu alan YOK MUYDU" bilgisi satir-diffinden TURETILEMEZ; uydurmak yerine ACIKCA
  olculmedigi soylenir. Silme sinifi `urunler-guard.py` + EKSEN 1 kapsamindadir.

ATTRIBUTION (bir diff satiri HANGI kaydin?) — `-U0` diffinde alan satiri kendi id'sini
  TASIMAZ. Cozum: git'in HUNK BASLIGI FONKSIYON BAGLAMI, `xfuncname` ile `"id"`
  satirina ayarlanir (`core.attributesFile` GECICI bir dosyaya yazilir, DEPO KIRLETILMEZ):
      @@ -353 +353 @@     "id": "capa-serit-dekoratif-figur",
  Hunk ICINDE gorulen bir `"id"` satiri baglami gunceller; `-` ve `+` taraflari AYRI
  baglam tasir (git once tum `-` sonra tum `+` satirlarini basar, ikisi de kendi
  dosyasinin satir sirasindadir).
  ⚠️ git hunk basligini ~80 bayta KISALTIR (olculdu: katalogdaki 7 id bu siniri asiyor).
  KESIK baglam ADAY id'lere ONEK ile cozulur; onek BIRDEN COK adaya uyarsa hukum
  verilmez -> OLCULEMEDI (belirsiz baglam sessizce YESIL SAYILMAZ).

📏 OLCULEN MALIYET + BEYAN EDILEN SINIR (ornekleme YOK — sessiz ornekleme YASAK):
  30 Tem, ana depo, TAM gecmis: 801 commit `urunler.json`'a dokunmus, uretilen diff
  ~70 MB, 28.679 hunk (28.035'i fonksiyon baglamli). Sure: ADAYSIZ 4,2 s ·
  ADAYLI (xfuncname acik) 5,2 s. Turetilen kume: ever_seen 16.058 · HEAD ~15.037
  · SILINMIS ~990. (Ornek silinmis: `1980-renault-re-20-turbo-model-araba` — tam da
  YASAK olcekli-maket sinifi.)
  SINIR: gecmis TAM taranir; ornekleme / "son N commit" kisitlamasi YOKTUR. TEK beyan
  edilen optimizasyon: ADAY ALAN YOKSA (hicbir kayitta kapsamli alan degismemisse)
  xfuncname yapilandirmasi EKLENMEZ — attribution'a ihtiyac olmadigi icin. Bu, olculen
  ~1 s'lik farki normal CI yolundan kaldirir ve raporda `attribution: funcname
  ACIK/KAPALI` olarak BASILIR (V0c bunu iddia eder). Cikti satir satir akitilir
  (70 MB bellege alinmaz). `--azami-sure` ile bir tavan verilebilir; tavan asilirsa
  kapi YESIL demez, **OLCULEMEDI** (rc 2) der.

🔴 FAIL-CLOSED — "olculemedi" ASLA yesil sayilmaz (rc 2):
  * depo SIG (shallow) klonlanmissa gecmis YOKTUR -> OLCULEMEDI. CI'da bu KRITIKTIR:
    `actions/checkout@v4` VARSAYILAN OLARAK `fetch-depth: 1` (sig) klonlar. deploy.yml'de
    checkout adimina `fetch-depth: 0` KONULMUSTUR; biri onu kaldirirsa bu kapi SESSIZCE
    yesile donmez, KIRMIZI/OLCULEMEDI ile bagirir.
  * `git` cagrilamiyorsa / `urunler.json` ayristirilamiyorsa -> OLCULEMEDI.
  * id satiri BEKLENMEYEN girintide gorulurse -> OLCULEMEDI. Olculen invariant (30 Tem,
    TAM gecmis): `urunler.json`'daki her `"id"` satiri ya 2 ya 4 bosluk girintilidir ve
    DAIMA ust duzey urun anahtaridir. Kapi bunu VARSAYMAZ, her koşumda OLCER.
  * ADAY ALAN VARKEN hicbir hunk fonksiyon baglami TASIMIYORSA -> OLCULEMEDI. Sebep:
    attribution calismiyorsa alan ekseni SESSIZCE olur ve kapi yesil yanardi (A13).
  * KESIK hunk baglami BIRDEN COK aday id'ye uyuyorsa -> OLCULEMEDI (A14).

MESRU GERI ALMA NASIL AYIRT EDILIR (kodda: `izin_oku` + `kapi`):
  Beyan dosyasi **`.diriltme-izin.json`** (depo KOKU, IZLENEN) — `{"<anahtar>": "gerekce"}`.
  ANAHTAR BICIMI:
    * EKSEN 1 (kayit): `"<id>"`            or. `"1980-renault-re-20-turbo-model-araba"`
    * EKSEN 2 (alan) : `"<id>#<alan>"`     or. `"capa-serit-dekoratif-figur#gorseller"`
    * EKSEN 2 TOPLU  : `"<id>#*"` (o kaydin TUM alanlari) · `"*#<alan>"` (o alanin TUM
      kayitlari). ⚠️ NEDEN VAR — OLCULEN VAKA: `1606e166` "fiyat duzeltmesi: yanlis
      kapsam geri alindi" commit'i 11.573 kayitta fiyati BILEREK eski degerine dondurdu
      (bir onceki toplu fiyat-tabani commit'inin yanlis kapsami). Bu, tanim geregi
      GERCEK bir gerileme (kapi HAKLI yaniyor) ama 11.573 satirlik beyan yazilamaz ->
      pratikte kacis YOLU OLMAZDI ve kapi TUM EKIBIN yayinini kalici durdururdu. Toplu
      beyan bu yuzden vardir: kural GEVSETILMEZ, geri alma BEYAN EDILIR.
      🔴 `"*"` ve `"*#*"` (her seyi kapatan blanket anahtar) KABUL EDILMEZ — bir kapiyi
      tek satirla oldurmenin yolu OLMAMALIDIR (A19). EKSEN 1'de (kayit diriltmesi)
      JOKER YOKTUR: toplu diriltme tam da felaket sinifidir.
  Urun id'leri kebab-case'dir ve `#` ICERMEZ -> iki bicim CAKISMAZ, TEK dosya yeter
  (YENI IZIN DOSYASI ACILMAZ).
  ⚠️ NEDEN `.urunler-sil-izin.json` DEGIL: `duzelt.py --sil`in urettigi o manifest
  (ve `.urunler-duzelt-izin.json`) `.gitignore`DADIR -> CI checkout'unda YOKTUR; onu
  dayanak yapmak kapiyi CI'da HIC calismaz hale getirirdi. Beyan IZLENEN olmak
  zorundadir ki inceleme (review) ve gecmis onu gorsun.
  Gerekcesiz/bos beyan KABUL EDILMEZ (V6 · A6). Beyan edilmis ama artik hukum uretmeyen
  girisler BILGI olarak basilir, KIRMIZI YAPILMAZ: bir geri alma merge edildikten sonra
  girdi dogal olarak "bayat"lasir ve onu kirmizi saymak KALICI SAHTE-KIRMIZI uretirdi
  (bu kapi deploy.yml'de continue-on-error'SUZ kosar; tek sahte-kirmizi TUM EKIBIN
  yayinini durdurur — [[kapi-kapsam-eksen-secimi]]).

🔴 SALT-OKUNUR: bu kapi `urunler.json`'a ASLA yazmaz, hicbir repo dosyasina dokunmaz.
  Gecici `attributes` dosyasi DEPO DISINA (tempfile) yazilir ve silinir. Kabul testi
  koşum oncesi/sonrasi `git status --porcelain` + `urunler.json` sha256 esitligini KENDI
  olcer (V14/V14b/V17). Kapiya bir yazma sokan mutasyon bu vakalari KIRMIZI yakar.

KULLANIM:
    python3 tools/diriltme-kapisi.py                  # CI/commit kipi: HEAD^1 -> HEAD
    python3 tools/diriltme-kapisi.py --calisma-agaci  # HEAD -> calisma agaci (push oncesi)
    python3 tools/diriltme-kapisi.py --taban main --yeni <dal>   # merge oncesi on-test
    python3 tools/diriltme-kapisi.py --kendini-test   # POZITIF+NEGATIF kabul (ag YOK)

CIKIS KODLARI: 0 = YESIL · 1 = KIRMIZI (diriltme / alan gerilemesi) · 2 = OLCULEMEDI.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
URUNLER_ADI = "urunler.json"
IZIN_ADI = ".diriltme-izin.json"

YESIL, KIRMIZI, OLCULEMEDI = 0, 1, 2

# TEK KAYNAK: hem gecmis taramasi hem girinti nobeti bu deseni kullanir.
# Grup 1 = +/- · Grup 2 = girinti · Grup 3 = id.
ID_SATIRI = re.compile(r'^([-+])([ \t]*)"id"\s*:\s*"([^"]*)"')
# Hunk basligindaki FONKSIYON BAGLAMI. git bunu ~80 bayta KISALTABILIR -> kapanis
# tirnagi olmayabilir; `kesik` bayragi bu yuzden AYRICA olculur (bkz. `_baglam_coz`).
FUNC_ID = re.compile(r'^([ \t]*)"id"\s*:\s*"([^"]*)')
HUNK_BASI = re.compile(r'^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@ ?(.*)$')
# 30 Tem'de TAM gecmiste OLCULEN girintiler (ust duzey urun anahtari; eski cag 2, yeni cag 4).
BEKLENEN_GIRINTI = ("  ", "    ")

# EKSEN 2 kapsami — SABIT liste; gerekce ve kapsam DISI alanlarin nedeni dosya
# basligindadir. "Tum alanlar" YAPILMAZ (gurultu + maliyet + olu pozitif nobetci).
# `eski_fiyat` FIYAT EKSENIYLE AYNI SINIF: musteriye gorunur + TICARI (yaniltici
# indirim), elle/`duzelt.py` ile yazilan TEK-YAZARLI karar, TURETILMIS artefakt DEGIL.
# Bir merge onu eski degerine dondururse site bitmis bir kampanyayi gostermeye devam
# eder ve hicbir yerde alarm calmaz -> kapsama girer.
KAPSAM_ALANLARI = ("gorseller", "fiyat", "eski_fiyat", "baslik", "aciklama", "kategori",
                   "lisans", "parametrik")
# Alan degerinin JSON serilestirmesinden atilan SAF YAPISAL satirlar.
YAPISAL_SATIRLAR = frozenset(("{", "}", "[", "]"))
# git `xfuncname` deseni: ust duzey `"id"` satiri (POSIX ERE — `[[:space:]]` tasinabilir).
XFUNCNAME = '^[[:space:]]*"id": .*$'
YOK = object()   # "alan hic yok" ile "alan degeri None" ayrimi icin nobetci deger


class Olculemedi(Exception):
    """Gecmis/dosya/attribution okunamadi -> yesil SAYILMAZ, rc 2."""


# ---------------------------------------------------------------- git yardimcilari
def _git(depo, *args, **kw):
    p = subprocess.run(["git", "-C", depo, *args], capture_output=True, text=True,
                       errors="replace", **kw)
    return p.returncode, p.stdout, p.stderr


def depo_kok(verilen=None):
    """Depo koku: verilen > bu dosyanin dizini > cwd. Kapinin BIR KOPYASI depo disina
    (or. scratchpad'e) konup mutasyon icin kosuldugunda ikinci dal devreye girer."""
    if verilen:
        return os.path.abspath(verilen)
    for aday in (TOOLS, os.getcwd()):
        rc, out, _ = _git(aday, "rev-parse", "--show-toplevel")
        if rc == 0 and out.strip():
            return out.strip()
    raise Olculemedi("git deposu bulunamadi (ne %s ne cwd bir git agaci)" % TOOLS)


def sig_mi(depo):
    rc, out, _ = _git(depo, "rev-parse", "--is-shallow-repository")
    if rc != 0:
        raise Olculemedi("`git rev-parse --is-shallow-repository` calismadi")
    return out.strip() == "true"


def rev_var_mi(depo, rev):
    rc, _o, _e = _git(depo, "rev-parse", "--verify", "--quiet", rev + "^{commit}")
    return rc == 0


def kayitlar_revden(depo, rev):
    """(idler, kayitlar) — <rev>:urunler.json. kayitlar = {id: {kapsam alani: deger}}."""
    rc, out, err = _git(depo, "show", rev + ":" + URUNLER_ADI)
    if rc != 0:
        raise Olculemedi("`git show %s:%s` okunamadi: %s"
                         % (rev, URUNLER_ADI, err.strip()[:200]))
    return kayitlar_metinden(out, "%s:%s" % (rev, URUNLER_ADI))


def kayitlar_dosyadan(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return kayitlar_metinden(f.read(), yol)
    except OSError as e:
        raise Olculemedi("%s okunamadi: %s" % (yol, e))


def kayitlar_metinden(metin, etiket):
    """Yalniz KAPSAM_ALANLARI saklanir — 13 MB katalogun TAMAMINI bellekte IKI KEZ
    tutmak gereksizdir ve kapsam disi alanlar bu kapiyi HIC ilgilendirmez."""
    try:
        govde = json.loads(metin)
    except ValueError as e:
        raise Olculemedi("%s ayristirilamadi (bozuk JSON): %s" % (etiket, e))
    if not isinstance(govde, list):
        raise Olculemedi("%s bir DIZI degil (%s)" % (etiket, type(govde).__name__))
    idler = set()
    kayitlar = {}
    for u in govde:
        if isinstance(u, dict) and isinstance(u.get("id"), str) and u["id"]:
            uid = u["id"]
            idler.add(uid)
            kayitlar[uid] = {a: u[a] for a in KAPSAM_ALANLARI if a in u}
    return idler, kayitlar


def idler_revden(depo, rev):
    return kayitlar_revden(depo, rev)[0]


def idler_dosyadan(yol):
    return kayitlar_dosyadan(yol)[0]


# ---------------------------------------------------------------- ALAN yardimcilari
def satir_normalle(ham):
    """Diff satiri <-> serilestirilmis alan satiri ORTAK bicimi: bastaki/sondaki bosluk
    ve SON VIRGUL atilir. Boylece bir degerin dizideki YERI degisince (virgulun gelip
    gitmesi) SAHTE fark uretilmez."""
    s = ham.strip()
    if s.endswith(","):
        s = s[:-1].rstrip()
    return s


def alan_satirlari(alan, deger):
    """Bir alanin `urunler.json` icinde uretecegi NORMALLESTIRILMIS satir kumesi.
    Dosya `json.dump(..., indent=2)` ile yazildigi icin girinti degisir ama normalize
    edilmis govde satirlari BIREBIR ayni olur."""
    ham = json.dumps({alan: deger}, ensure_ascii=False, indent=2).splitlines()
    out = set()
    for s in ham[1:-1]:                       # dis `{` ve `}` atilir
        n = satir_normalle(s)
        if n and n not in YAPISAL_SATIRLAR:
            out.add(n)
    return out


def adaylari_turet(taban_kayitlar, yeni_kayitlar):
    """SAF: (adaylar, silinen_alanlar) — ag/dosya YOK.

    adaylar        : {(id, alan): frozenset(GERI GELME ADAYI SATIRLAR)} — yenide olup
                     tabanda OLMAYAN satirlar. Yalniz HEM tabanda HEM yenide var olan
                     kayitlara bakilir (yeni kayit eklemek SERBEST = EKSEN 1'in konusu).
    silinen_alanlar: [(id, alan)] — tabanda var, yenide YOK. BEYAN EDILEN SINIR: hukum
                     verilmez (bkz. dosya basligi), yalniz BILGI olarak basilir."""
    adaylar = {}
    silinen = []
    for uid in sorted(taban_kayitlar.keys() & yeni_kayitlar.keys()):
        t = taban_kayitlar[uid]
        y = yeni_kayitlar[uid]
        for alan in KAPSAM_ALANLARI:
            tv = t.get(alan, YOK)
            yv = y.get(alan, YOK)
            if tv is YOK and yv is YOK:
                continue
            if tv is not YOK and yv is not YOK and tv == yv:
                continue
            if yv is YOK:
                silinen.append((uid, alan))
                continue
            t_satir = set() if tv is YOK else alan_satirlari(alan, tv)
            fark = alan_satirlari(alan, yv) - t_satir
            if fark:
                adaylar[(uid, alan)] = frozenset(fark)
    return adaylar, silinen


def aday_satirlari_idye(adaylar):
    """{id: set(aday satir)} — gecmis taramasinin HIZLI on-elemesi."""
    out = {}
    for (uid, _alan), satirlar in adaylar.items():
        out.setdefault(uid, set()).update(satirlar)
    return out


def izin_eslesir(uid, alan, izinli):
    """SAF: EKSEN 2 anahtari beyan edilmis mi. Tam anahtar > kayit jokeri > alan jokeri.
    Blanket `"*"` / `"*#*"` BURADA DEGIL, `izin_oku`da REDDEDILIR (asla izinli'ye girmez)."""
    return ("%s#%s" % (uid, alan) in izinli
            or "%s#*" % uid in izinli
            or "*#%s" % alan in izinli)


def alan_gerilemeleri_bul(adaylar, arti_gorulen, eksi_gorulen, izinli):
    """SAF karar (EKSEN 2 mutasyon hedefi): (gerileme, beyanli).

    Bir aday satir ancak AYNI KAYDIN gecmisinde HEM `+` (GORULMUS) HEM `-` (TERK
    EDILMIS) olarak gorulmusse gerileme kanitidir. BASKA bir kaydin gecmisinde
    gorulmus olmasi HUKUM URETMEZ (A15/A17e)."""
    gerileme, beyanli = [], []
    for (uid, alan) in sorted(adaylar):
        kanit = sorted(s for s in adaylar[(uid, alan)]
                       if (uid, s) in arti_gorulen and (uid, s) in eksi_gorulen)
        if not kanit:
            continue
        anahtar = "%s#%s" % (uid, alan)
        hedef = beyanli if izin_eslesir(uid, alan, izinli) else gerileme
        hedef.append((anahtar, kanit))
    return gerileme, beyanli


# ---------------------------------------------------------------- gecmis turetme
def gecmiste_gorulen(depo, rev, azami_sure=None, aday_satirlar=None):
    """(ever_seen, arti_gorulen, eksi_gorulen, olcumler) — TEK GECIS, IKI EKSEN.

    <rev>'in BIRINCI-EBEVEYN gecmisinde:
      * EKSEN 1: `+` satirinda gorulen TUM urun id'leri (ever_seen)
      * EKSEN 2: aday (id, satir) ciftlerinin `+` / `-` olarak gorulup gorulmedigi
    Cikti AKITILIR (70 MB bellege alinmaz).

    FAIL-CLOSED: beklenmeyen girinti · attribution yoksa · kesik baglam belirsizse."""
    aday_satirlar = aday_satirlar or {}
    aday_var = bool(aday_satirlar)
    attr_yolu = None
    komut = ["git", "-C", depo]
    if aday_var:
        # Attribution GEREKLI -> hunk basligina `"id"` satirini koydur. Attributes
        # dosyasi DEPO DISINA yazilir; kapi salt-okunurdur.
        fd, attr_yolu = tempfile.mkstemp(prefix="pruvo-diriltme-attr-", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("%s diff=pruvojson\n" % URUNLER_ADI)
        komut += ["-c", "core.attributesFile=" + attr_yolu,
                  "-c", "diff.pruvojson.xfuncname=" + XFUNCNAME]
    komut += ["log", "-U0", "-p", "--no-color", "--first-parent", "--format=%H",
              rev, "--", URUNLER_ADI]

    t0 = time.time()
    try:
        p = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, errors="replace", bufsize=1024 * 1024)
    except OSError as e:
        if attr_yolu and os.path.exists(attr_yolu):
            os.remove(attr_yolu)
        raise Olculemedi("git log calistirilamadi: %s" % e)

    ever, cikan = set(), set()
    arti_gorulen, eksi_gorulen = set(), set()
    satir_sayisi = hunk = hunk_baglamli = 0
    bayt = 0
    ctx_arti = ctx_eksi = None
    onek_onbellek = {}

    def _baglam_coz(ham, kesik):
        """KESIK hunk basligini ADAY id'lere ONEKLE cozer. Belirsizse FAIL-CLOSED."""
        if not kesik:
            return ham
        if ham in onek_onbellek:
            return onek_onbellek[ham]
        esler = [k for k in aday_satirlar if k.startswith(ham)]
        if len(esler) > 1:
            raise Olculemedi(
                "KESIK hunk baglami (...%r) BIRDEN COK aday id'ye uyuyor (%s) — hangi "
                "kayda ait oldugu BELIRSIZ; belirsiz baglam YESIL SAYILMAZ"
                % (ham[-40:], ", ".join(sorted(esler)[:3])))
        c = esler[0] if esler else None
        onek_onbellek[ham] = c
        return c

    try:
        for satir in p.stdout:
            bayt += len(satir)
            if satir.startswith("@@"):
                hb = HUNK_BASI.match(satir)
                if hb:
                    hunk += 1
                    baglam = hb.group(1)
                    ctx_arti = ctx_eksi = None
                    if baglam.strip():
                        hunk_baglamli += 1
                        if aday_var:
                            fm = FUNC_ID.match(baglam)
                            if fm:
                                if fm.group(1) not in BEKLENEN_GIRINTI:
                                    p.kill()
                                    raise Olculemedi(
                                        "BEKLENMEYEN hunk baglam GIRINTISI (%r) — "
                                        "attribution GUVENILMEZ. Baglam: %s"
                                        % (fm.group(1), baglam.strip()[:120]))
                                kesik = not baglam[fm.end():].startswith('"')
                                ctx_arti = ctx_eksi = _baglam_coz(fm.group(2), kesik)
                continue
            m = ID_SATIRI.match(satir)
            if m:
                if m.group(2) not in BEKLENEN_GIRINTI:
                    p.kill()
                    raise Olculemedi(
                        "BEKLENMEYEN id GIRINTISI (%r) — bu kapinin ayikcalayicisi ust duzey "
                        "urun anahtarini tanimiyor olabilir; kendi olcumune GUVENMEZ. Satir: %s"
                        % (m.group(2), satir.strip()[:120]))
                satir_sayisi += 1
                if m.group(1) == "+":
                    ever.add(m.group(3))
                    ctx_arti = m.group(3)
                else:
                    cikan.add(m.group(3))
                    ctx_eksi = m.group(3)
            elif aday_var:
                bas = satir[:1]
                if bas == "+" and not satir.startswith("+++"):
                    ctx, hedef = ctx_arti, arti_gorulen
                elif bas == "-" and not satir.startswith("---"):
                    ctx, hedef = ctx_eksi, eksi_gorulen
                else:
                    if satir.startswith("diff --git"):
                        ctx_arti = ctx_eksi = None
                    continue
                if ctx is not None:
                    kume = aday_satirlar.get(ctx)
                    if kume:
                        n = satir_normalle(satir[1:])
                        if n in kume:
                            hedef.add((ctx, n))
            if azami_sure and (time.time() - t0) > azami_sure:
                p.kill()
                raise Olculemedi(
                    "gecmis taramasi %.0f s tavanini asti — kume EKSIK olurdu, sessiz "
                    "ornekleme YAPILMAZ" % azami_sure)
    finally:
        try:
            p.stdout.close()
        except Exception:
            pass
        hata = p.stderr.read() if p.stderr else ""
        try:
            p.stderr.close()
        except Exception:
            pass
        p.wait()
        if attr_yolu and os.path.exists(attr_yolu):
            os.remove(attr_yolu)
    if p.returncode not in (0, -9):
        raise Olculemedi("git log basarisiz (rc=%s): %s" % (p.returncode, hata.strip()[:200]))
    if aday_var and hunk > 0 and hunk_baglamli == 0:
        raise Olculemedi(
            "ADAY ALAN VAR ama hicbir hunk fonksiyon baglami TASIMIYOR (%d hunk) — "
            "attribution CALISMIYOR, alan ekseni SESSIZCE olu kalirdi. Muhtemel sebep: "
            "depo `.gitattributes` dosyasi `%s` icin diff surucusunu eziyor ya da git "
            "surumu `xfuncname` desteklemiyor. Bu durum YESIL SAYILMAZ."
            % (hunk, URUNLER_ADI))
    return ever, arti_gorulen, eksi_gorulen, {
        "sure_sn": round(time.time() - t0, 2),
        "diff_mb": round(bayt / 1e6, 1),
        "id_satiri": satir_sayisi,
        "ever_seen": len(ever),
        "cikan": len(cikan),
        "hunk": hunk,
        "hunk_baglamli": hunk_baglamli,
        "funcname": "ACIK" if aday_var else "KAPALI (aday alan yok)",
    }


# ---------------------------------------------------------------- beyan
def izin_oku(depo):
    """(izinli_anahtarlar, bilgi, hatalar) — `.diriltme-izin.json`.

    ANAHTAR: EKSEN 1 icin `"<id>"`, EKSEN 2 icin `"<id>#<alan>"` / `"<id>#*"` /
    `"*#<alan>"` (urun id'leri kebab-case'dir, `#` ICERMEZ -> cakisma yok).
    FAIL-CLOSED: dosya BOZUKSA hata (yesil sayilmaz) · BOS GEREKCELI giris KABUL
    EDILMEZ · BLANKET (`"*"`, `"*#*"`) anahtar KABUL EDILMEZ: bir kapiyi tek satirla
    olduren joker OLMAMALIDIR."""
    yol = os.path.join(depo, IZIN_ADI)
    if not os.path.exists(yol):
        return set(), [], []
    try:
        with open(yol, encoding="utf-8") as f:
            govde = json.load(f)
    except (OSError, ValueError) as e:
        return set(), [], ["%s okunamadi/ayristirilamadi: %s" % (IZIN_ADI, e)]
    if not isinstance(govde, dict):
        return set(), [], ["%s bir SOZLUK degil ({anahtar: gerekce} bekleniyor)" % IZIN_ADI]
    izinli, bilgi, hatalar = set(), [], []
    for anahtar, gerekce in sorted(govde.items()):
        if not isinstance(gerekce, str) or not gerekce.strip():
            hatalar.append("%s GEREKCESIZ giris: %r -> beyan gerekce ISTER "
                           "(bos gerekce muafiyet SAYILMAZ)" % (IZIN_ADI, anahtar))
            continue
        if anahtar.strip() in ("*", "*#*", "#*"):
            hatalar.append("%s BLANKET beyan: %r -> bir kapiyi TEK SATIRLA olduren "
                           "joker KABUL EDILMEZ; `<id>`, `<id>#<alan>`, `<id>#*` ya da "
                           "`*#<alan>` yaz" % (IZIN_ADI, anahtar))
            continue
        izinli.add(anahtar)
        bilgi.append((anahtar, gerekce.strip()[:110]))
    return izinli, bilgi, hatalar


# ---------------------------------------------------------------- KAPI (SAF karar)
def dirilenleri_bul(silinmis, yeni_idler, izinli):
    """SAF karar (EKSEN 1 mutasyon hedefi): (dirilen, beyanli) — ag/dosya YOK."""
    geri_gelen = silinmis & yeni_idler
    dirilen = sorted(geri_gelen - izinli)
    beyanli = sorted(geri_gelen & izinli)
    return dirilen, beyanli


def kapi(depo=None, taban=None, yeni_rev=None, yeni_dosya=None, azami_sure=None):
    """(durum, satirlar, olcumler). durum: "YESIL" | "KIRMIZI" | "OLCULEMEDI"."""
    satirlar = []
    olcumler = {}
    try:
        depo = depo_kok(depo)
        if sig_mi(depo):
            raise Olculemedi(
                "depo SIG (shallow) klonlanmis -> silinmis-id kumesi TURETILEMEZ. "
                "CI'da cozum: actions/checkout adimina `fetch-depth: 0`. "
                "Bu durum YESIL SAYILMAZ.")

        # --- taban / yeni cozumleme
        if yeni_dosya is None and yeni_rev is None:
            if not rev_var_mi(depo, "HEAD"):
                raise Olculemedi("HEAD yok (bos depo)")
            yeni_rev = "HEAD"
            if taban is None:
                taban = "HEAD^1" if rev_var_mi(depo, "HEAD^1") else None
        if taban is None and yeni_dosya is not None:
            taban = "HEAD"
        if taban is None:
            satirlar.append(("BILGI", "-", "tabanin ebeveyni YOK (ilk commit) -> "
                                           "karsilastirilacak onceki durum yok"))
            return "YESIL", satirlar, olcumler
        if not rev_var_mi(depo, taban):
            raise Olculemedi("taban revizyonu cozulemedi: %s" % taban)

        taban_idler, taban_kayitlar = kayitlar_revden(depo, taban)
        if yeni_dosya is not None:
            yeni_idler, yeni_kayitlar = kayitlar_dosyadan(yeni_dosya)
        else:
            yeni_idler, yeni_kayitlar = kayitlar_revden(depo, yeni_rev)

        # --- EKSEN 2 adaylari gecmis taramasindan ONCE turetilir: TEK GECIS onlarla
        #     beslenir (ikinci bir 70 MB tarama ACILMAZ — KraL karari).
        adaylar, silinen_alanlar = adaylari_turet(taban_kayitlar, yeni_kayitlar)
        aday_satirlar = aday_satirlari_idye(adaylar)

        ever, arti_gorulen, eksi_gorulen, olcumler = gecmiste_gorulen(
            depo, taban, azami_sure, aday_satirlar)
        silinmis = ever - taban_idler

        izinli, izin_bilgi, izin_hatalari = izin_oku(depo)
        olcumler.update({
            "depo": depo, "taban": taban,
            "yeni": yeni_dosya if yeni_dosya is not None else yeni_rev,
            "taban_id": len(taban_idler), "yeni_id": len(yeni_idler),
            "silinmis": len(silinmis), "beyan": len(izinli),
            "aday_alan": len(adaylar), "aday_kayit": len(aday_satirlar),
            "silinen_alan": len(silinen_alanlar),
        })
        if izin_hatalari:
            for h in izin_hatalari:
                satirlar.append(("BEYAN", "-", h))

        dirilen, beyanli = dirilenleri_bul(silinmis, yeni_idler, izinli)
        gerileme, alan_beyanli = alan_gerilemeleri_bul(
            adaylar, arti_gorulen, eksi_gorulen, izinli)
        olcumler["yeni_eklenen"] = len(yeni_idler - taban_idler)
        olcumler["dirilen"] = len(dirilen)
        olcumler["beyanli_dirilme"] = len(beyanli)
        olcumler["alan_gerilemesi"] = len(gerileme)
        olcumler["beyanli_alan"] = len(alan_beyanli)

        for uid in dirilen:
            satirlar.append(("DIRILTME", uid,
                             "GECMISTE SILINMIS bu id geri geldi — satir-duzeyi merge "
                             "kurbani olabilir; yasak-tur urun canliya donebilir"))
        for anahtar, kanit in gerileme:
            satirlar.append(("GERILEME", anahtar,
                             "alan GECMISTE GORULMUS ve TERK EDILMIS bir degere donmus "
                             "-> %s" % (" | ".join(k[:70] for k in kanit[:3]))))
        for uid in beyanli:
            satirlar.append(("BEYANLI", uid, "diriltme %s'de gerekceyle beyan edilmis"
                             % IZIN_ADI))
        for anahtar, _kanit in alan_beyanli:
            satirlar.append(("BEYANLI", anahtar,
                             "alan gerilemesi %s'de gerekceyle beyan edilmis" % IZIN_ADI))
        for uid, alan in silinen_alanlar:
            satirlar.append(("BILGI", "%s#%s" % (uid, alan),
                             "alan yenide YOK — BEYAN EDILEN SINIR: alan SILINMESI bu "
                             "eksende OLCULMEZ (yokluk satir-diffinden turetilemez)"))
        kullanilan = set(beyanli)
        for anahtar, _kanit in alan_beyanli:
            b_uid, _s, b_alan = anahtar.partition("#")
            for aday in (anahtar, "%s#*" % b_uid, "*#%s" % b_alan):
                if aday in izinli:
                    kullanilan.add(aday)
        for anahtar, gerekce in izin_bilgi:
            if anahtar not in kullanilan:
                satirlar.append(("BILGI", anahtar,
                                 "%s girisi su an hukum uretmiyor (bayat olabilir): %s"
                                 % (IZIN_ADI, gerekce)))
        if dirilen or gerileme or izin_hatalari:
            return "KIRMIZI", satirlar, olcumler
        return "YESIL", satirlar, olcumler
    except Olculemedi as e:
        satirlar.append(("OLCULEMEDI", "-", str(e)))
        return "OLCULEMEDI", satirlar, olcumler


DURUM_KOD = {"YESIL": YESIL, "KIRMIZI": KIRMIZI, "OLCULEMEDI": OLCULEMEDI}


def rapor(durum, satirlar, olcumler):
    print("DIRILTME KAPISI — kayit diriltmesi (EKSEN 1) + alan gerilemesi (EKSEN 2)")
    if olcumler:
        print("  depo / taban / yeni    : %s | %s -> %s" % (
            olcumler.get("depo", "?"), olcumler.get("taban", "?"), olcumler.get("yeni", "?")))
        print("  gecmis taramasi (TEK)  : %s id satiri, %s MB diff, %s s "
              "(TAM gecmis — ornekleme YOK)" % (
                  olcumler.get("id_satiri", "?"), olcumler.get("diff_mb", "?"),
                  olcumler.get("sure_sn", "?")))
        print("  attribution            : funcname %s · %s hunk (%s baglamli)" % (
            olcumler.get("funcname", "?"), olcumler.get("hunk", "?"),
            olcumler.get("hunk_baglamli", "?")))
        print("  bir zamanlar var olan  : %s id" % olcumler.get("ever_seen", "?"))
        print("  tabanda duran          : %s id" % olcumler.get("taban_id", "?"))
        print("  SILINMIS (yasak kume)  : %s id" % olcumler.get("silinmis", "?"))
        print("  yenide duran           : %s id  (yeni eklenen: %s — SERBEST)" % (
            olcumler.get("yeni_id", "?"), olcumler.get("yeni_eklenen", "?")))
        print("  EKSEN 2 kapsam alanlari: %s" % ", ".join(KAPSAM_ALANLARI))
        print("  EKSEN 2 aday           : %s (id,alan) cifti / %s kayit · yenide "
              "silinen alan: %s (OLCULMEZ)" % (
                  olcumler.get("aday_alan", "?"), olcumler.get("aday_kayit", "?"),
                  olcumler.get("silinen_alan", "?")))
        print("  ALAN GERILEMESI        : %s" % olcumler.get("alan_gerilemesi", "?"))
        print("  beyan (%s)  : %s giris" % (IZIN_ADI, olcumler.get("beyan", 0)))
    for sinif, uid, aciklama in satirlar:
        print("    %-10s %-46s %s" % (sinif, uid, aciklama))
    print("----------------------------------------------------------------------")
    if durum == "YESIL":
        print("SONUC: YESIL ✅  — gecmiste silinmis urun geri gelmemis VE kapsamdaki "
              "hicbir alan terk edilmis bir degere donmemis.")
    elif durum == "KIRMIZI":
        print("SONUC: KIRMIZI ❌  — SESSIZ GERI GITME (kayit diriltmesi ve/veya alan "
              "gerilemesi).")
        print("  DOKTRIN: urunler.json cakismasi satir-duzeyi merge ile COZULMEZ.")
        print("  COZUM: 1) dali main'e MERGE ETME; yalniz KOD dosyalarini tasi")
        print("         2) urun verisi degisecekse: python3 tools/duzelt.py ...")
        print("         3) geri alma GERCEKTEN mesruysa %s'a GEREKCEYLE yaz:" % IZIN_ADI)
        print("            kayit ekseni -> \"<id>\" · alan ekseni -> \"<id>#<alan>\"")
    else:
        print("SONUC: ⚪ OLCULEMEDI — gecmis/attribution turetilemedi; parite "
              "KANITLANMADI (sessiz yesil verilmez).")
    return DURUM_KOD[durum]


# ---------------------------------------------------------------- kendini test
def _kos(depo, *args, **kw):
    rc, out, err = _git(depo, *args, **kw)
    if rc != 0:
        raise RuntimeError("git %s -> rc=%d %s" % (" ".join(args), rc, err))
    return out


def _urun(uid, kategori="Marin", **ek):
    u = {"id": uid, "kategori": kategori, "marka": [], "baslik": uid,
         "aciklama": "test", "fiyat": "100 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}
    u.update(ek)
    return u


def _yaz(depo, ogeler, girinti=4):
    """<girinti> = urun ANAHTARLARININ girintisi (gercek dosyada: yeni cag 4, eski cag 2).
    <ogeler> ogesi str ise varsayilan urun, dict ise oldugu gibi yazilir."""
    yol = os.path.join(depo, URUNLER_ADI)
    urunler = [_urun(o) if isinstance(o, str) else o for o in ogeler]
    with open(yol, "w", encoding="utf-8") as f:
        if girinti == 4:
            json.dump(urunler, f, ensure_ascii=False, indent=2)
        else:
            govde = ",\n".join(json.dumps(u, ensure_ascii=False, indent=2) for u in urunler)
            f.write("[\n" + govde + "\n]")
        f.write("\n")


def _commit(depo, mesaj):
    _kos(depo, "add", "-A")
    _kos(depo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", mesaj)


def _depo_kur(kok, ad):
    depo = os.path.join(kok, ad)
    os.makedirs(depo)
    _kos(depo, "init", "-q", "-b", "main")
    return depo


def _gorsel(uid, n):
    return "https://media.pruvo3d.com/urunler/%s-%d.jpg" % (uid, n)


def kendini_test():
    """POZITIF + NEGATIF vakalar. Her iddia icin IKI YON de olculur (yalniz pozitif =
    olu nobetci). Ag YOK; sentetik gecici git depolari, CANLI VERIYE DOKUNULMAZ."""
    ham = ["DIRILTME KAPISI — KENDINI TEST (offline, sentetik git depolari)"]
    kirmizi = 0

    def iddia(ad, kosul, detay=""):
        nonlocal kirmizi
        if kosul:
            ham.append("    ✅ " + ad)
        else:
            kirmizi += 1
            ham.append("    ❌ " + ad + (" — " + str(detay) if detay else ""))

    with tempfile.TemporaryDirectory(prefix="pruvo-diriltme-") as kok:
        # ---- ORTAK TARIH: a,b,c eklendi -> b BILEREK silindi (yasak tur) -> d eklendi
        def temel_depo(ad, girinti=4):
            d = _depo_kur(kok, ad)
            _yaz(d, ["a", "b", "c"], girinti)
            _commit(d, "ilk katalog")
            _yaz(d, ["a", "c"], girinti)
            _commit(d, "b silindi (yasak tur: olcekli maket)")
            _yaz(d, ["a", "c", "d"], girinti)
            _commit(d, "d eklendi")
            return d

        # ======================= EKSEN 1 — KAYIT DIRILTMESI =======================
        # V0 — kume turetmenin KENDISI dogru mu (nobetin dayanagi)
        d0 = temel_depo("v0")
        ever, _ar, _ek, olc0 = gecmiste_gorulen(d0, "HEAD")
        taban = idler_revden(d0, "HEAD")
        iddia("V0 silinmis kume gecmisten TURETILIYOR (elle liste YOK): {b}",
              (ever - taban) == {"b"}, sorted(ever - taban))
        iddia("V0b ever_seen dosyanin ILK halini de kapsiyor (a,b,c,d)",
              ever == {"a", "b", "c", "d"}, sorted(ever))
        iddia("V0c ADAYSIZ koşumda funcname KAPALI (beyan edilen maliyet "
              "optimizasyonu — sessiz DEGIL, raporda basilir)",
              olc0.get("funcname", "").startswith("KAPALI"), olc0.get("funcname"))

        # V1 POZITIF — dirilen id -> KIRMIZI
        d1 = temel_depo("v1")
        _yaz(d1, ["a", "c", "d", "b"])
        _commit(d1, "b geri geldi (diriltme)")
        du, sa, _ = kapi(depo=d1)
        iddia("V1 [POZITIF] dirilen id -> KIRMIZI (rc 1)",
              du == "KIRMIZI" and DURUM_KOD[du] == 1, du)
        iddia("V1b teshis id'yi ADIYLA soyluyor",
              any(s[1] == "b" and s[0] == "DIRILTME" for s in sa), sa)

        # V2 NEGATIF — YENI id eklemek SERBEST
        d2 = temel_depo("v2")
        _yaz(d2, ["a", "c", "d", "e"])
        _commit(d2, "e eklendi (yeni id)")
        du, _s, _o = kapi(depo=d2)
        iddia("V2 [NEGATIF] YENI id eklenmesi -> YESIL", du == "YESIL", du)

        # V3 NEGATIF — hic degismemis dosya
        d3 = temel_depo("v3")
        with open(os.path.join(d3, "README.md"), "w") as f:
            f.write("x\n")
        _commit(d3, "urunler.json'a dokunmayan commit")
        du, _s, _o = kapi(depo=d3)
        iddia("V3 [NEGATIF] urunler.json hic degismemis -> YESIL", du == "YESIL", du)

        # V4 NEGATIF — silinmis SILINMIS kaldi
        d4 = temel_depo("v4")
        _yaz(d4, ["a", "c", "d", "e", "f"])
        _commit(d4, "iki yeni urun")
        du, _s, o4 = kapi(depo=d4)
        iddia("V4 [NEGATIF] silinmis id geri gelmedi -> YESIL", du == "YESIL", du)
        iddia("V4b yasak kume BOSALMADI (nobetin dayanagi hala duruyor)",
              o4.get("silinmis") == 1, o4.get("silinmis"))

        # V5 NEGATIF — BEYANLI mesru geri-ekleme (duzelt.py yolu)
        d5 = temel_depo("v5")
        _yaz(d5, ["a", "c", "d", "b"])
        with open(os.path.join(d5, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"b": "lisansi duzeltildi, KraL onayiyla geri alindi"}, f)
        _commit(d5, "b beyanla geri alindi")
        du, sa, _o = kapi(depo=d5)
        iddia("V5 [NEGATIF] gerekceli beyan -> YESIL (mesru geri-ekleme yolu)",
              du == "YESIL", du)
        iddia("V5b beyanli dirilme raporda GORUNUR (sessiz gecmez)",
              any(s[0] == "BEYANLI" and s[1] == "b" for s in sa), sa)

        # V6 POZITIF — GEREKCESIZ beyan kacis deligi OLMAZ
        d6 = temel_depo("v6")
        _yaz(d6, ["a", "c", "d", "b"])
        with open(os.path.join(d6, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"b": "   "}, f)
        _commit(d6, "b bos gerekceyle")
        du, sa, _o = kapi(depo=d6)
        iddia("V6 [POZITIF] BOS GEREKCELI beyan muafiyet SAYILMAZ -> KIRMIZI",
              du == "KIRMIZI", du)
        iddia("V6b tani gerekcesizligi soyluyor",
              any(s[0] == "BEYAN" for s in sa), sa)

        # V7 FAIL-CLOSED — SIG (shallow) depo
        d7 = temel_depo("v7")
        _yaz(d7, ["a", "c", "d", "b"])
        _commit(d7, "b geri geldi")
        sig = os.path.join(kok, "v7-sig")
        _kos(kok, "clone", "-q", "--depth", "1", "file://" + d7, sig)
        du, sa, _o = kapi(depo=sig)
        iddia("V7 [FAIL-CLOSED] SIG depo -> OLCULEMEDI (rc 2), ASLA yesil",
              du == "OLCULEMEDI" and DURUM_KOD[du] == 2, du)
        iddia("V7b tani `fetch-depth: 0` cozumunu soyluyor",
              any("fetch-depth" in s[2] for s in sa), sa)

        # V8 POZITIF — OLCULEN 30 TEM VAKASININ BIREBIR YENIDEN KURULUMU
        d8 = _depo_kur(kok, "v8")
        _yaz(d8, ["a", "b", "c"])
        _commit(d8, "ilk katalog")
        _kos(d8, "checkout", "-q", "-b", "muhendis")
        _yaz(d8, ["a", "b", "c", "x"])
        _commit(d8, "dalda x eklendi")
        _kos(d8, "checkout", "-q", "main")
        _yaz(d8, ["a", "c"])
        _commit(d8, "b silindi (yasak tur: olcekli maket)")
        _yaz(d8, ["a", "c", "d"])
        _commit(d8, "d eklendi")
        _kos(d8, "checkout", "-q", "muhendis")
        _git(d8, "-c", "user.email=t@t", "-c", "user.name=t", "merge", "main")  # cakisir
        _yaz(d8, ["a", "b", "c", "x"])                       # "dalin tarafi korunarak" cozum
        _commit(d8, "main birlestirildi: cakisma dalin tarafi korunarak cozuldu")
        _kos(d8, "checkout", "-q", "main")
        with open(os.path.join(d8, "tools.py"), "w") as f:   # main ilerledi (ff ENGELLENIR)
            f.write("# main tarafinda kod degisikligi\n")
        _commit(d8, "main'de kod degisikligi (urunler.json'a DOKUNULMADI)")
        _kos(d8, "-c", "user.email=t@t", "-c", "user.name=t",
             "merge", "-q", "muhendis", "-m", "dal alindi")
        du, sa, o8 = kapi(depo=d8)
        iddia("V8 [POZITIF] dal->main MERGE'i silinmis b'yi diriltti -> KIRMIZI",
              du == "KIRMIZI" and any(s[0] == "DIRILTME" and s[1] == "b" for s in sa),
              (du, sa))
        iddia("V8b tek suclu b: yeni gelen x DIRILTME sayilmaz (yeni id serbest)",
              o8.get("dirilen") == 1, (o8.get("dirilen"), sa))

        # V9 NEGATIF — MaCiT tipi TOPLU ekleme partisi (yanlis-pozitif nobeti)
        d9 = temel_depo("v9")
        parti = ["a", "c", "d"] + ["yeni-urun-%03d" % i for i in range(60)]
        _yaz(d9, parti)
        _commit(d9, "60 urun eklendi (MaCiT normal ekleme partisi)")
        du, sa, o9 = kapi(depo=d9)
        iddia("V9 [NEGATIF] 60'lik toplu ekleme partisi kapiyi TETIKLEMEZ -> YESIL",
              du == "YESIL" and o9.get("yeni_eklenen") == 60, (du, o9.get("yeni_eklenen")))
        iddia("V9b toplu ekleme HIC aday alan uretmez (alan ekseni BEDAVA)",
              o9.get("aday_alan") == 0, o9.get("aday_alan"))

        # V10 POZITIF — 2 BOSLUK girintili ESKI cag bicimi de ayristirilir
        d10 = temel_depo("v10", girinti=2)
        _yaz(d10, ["a", "c", "d", "b"], girinti=2)
        _commit(d10, "b geri geldi (eski 2-bosluk bicim)")
        du, _s, _o = kapi(depo=d10)
        iddia("V10 [POZITIF] 2-bosluk girintili ESKI bicimde de diriltme goruluyor",
              du == "KIRMIZI", du)

        # V11 FAIL-CLOSED — BEKLENMEYEN girinti: kapi KENDI ayikcalayicisina GUVENMEZ.
        d11 = temel_depo("v11")
        with open(os.path.join(d11, URUNLER_ADI), "w", encoding="utf-8") as f:
            json.dump([_urun(u) for u in ["a", "c", "d"]], f, ensure_ascii=False, indent=4)
            f.write("\n")
        _commit(d11, "beklenmeyen girinti (anahtarlar 8 bosluk) — JSON GECERLI")
        du, sa, _o = kapi(depo=d11, taban="HEAD")
        iddia("V11 [FAIL-CLOSED] BEKLENMEYEN id girintisi -> OLCULEMEDI (yesil DEGIL)",
              du == "OLCULEMEDI" and any(s[0] == "OLCULEMEDI" and "GIRINTI" in s[2]
                                         for s in sa), (du, sa))

        # V17 SALT-OKUNURLUK (SENTETIK) — kapi kostugu deponun urunler.json'una DOKUNMAZ.
        d17 = temel_depo("v17")
        yol17 = os.path.join(d17, URUNLER_ADI)
        with open(yol17, "rb") as f:
            once17 = hashlib.sha256(f.read()).hexdigest()
        _rc, once_p17, _e = _git(d17, "status", "--porcelain")
        kapi(depo=d17)
        with open(yol17, "rb") as f:
            sonra17 = hashlib.sha256(f.read()).hexdigest()
        _rc, sonra_p17, _e = _git(d17, "status", "--porcelain")
        iddia("V17 SALT-OKUNUR (sentetik): urunler.json sha256 + porcelain degismedi",
              once17 == sonra17 and once_p17 == sonra_p17,
              (once17[:12], sonra17[:12], once_p17, sonra_p17))

        # V17b SALT-OKUNUR — ALAN EKSENI acikken de (gecici attributes dosyasi DEPO
        # DISINA yazilir; depoya sizan bir yazma bu vakayi kirmizi yakar).
        d17b = temel_depo("v17b")
        _yaz(d17b, [_urun("a", fiyat="999 TL"), "c", "d"])
        _commit(d17b, "a'nin fiyati degisti (aday alan uretir)")
        yol17b = os.path.join(d17b, URUNLER_ADI)
        with open(yol17b, "rb") as f:
            once17b = hashlib.sha256(f.read()).hexdigest()
        _rc, once_p17b, _e = _git(d17b, "status", "--porcelain")
        _du, _sa, o17b = kapi(depo=d17b)
        with open(yol17b, "rb") as f:
            sonra17b = hashlib.sha256(f.read()).hexdigest()
        _rc, sonra_p17b, _e = _git(d17b, "status", "--porcelain")
        iddia("V17b SALT-OKUNUR (alan ekseni ACIK): sha256 + porcelain degismedi, "
              "gecici attributes dosyasi depoya SIZMADI",
              once17b == sonra17b and once_p17b == sonra_p17b == "",
              (once17b[:12], sonra17b[:12], once_p17b, sonra_p17b))
        iddia("V17c alan ekseni acikken funcname yapilandirmasi ACIK",
              o17b.get("funcname") == "ACIK", o17b.get("funcname"))

        # V12 POZITIF — diriltme + ayni commit'te yeni id: yeni id yesil SATIN ALMAZ
        d12 = temel_depo("v12")
        _yaz(d12, ["a", "c", "d", "b", "yepyeni"])
        _commit(d12, "diriltme + yeni urun ayni commit'te")
        du, sa, o12 = kapi(depo=d12)
        iddia("V12 [POZITIF] yeni id ile birlikte gelen diriltme yine KIRMIZI",
              du == "KIRMIZI" and o12.get("dirilen") == 1 and o12.get("yeni_eklenen") == 2,
              (du, o12.get("dirilen"), o12.get("yeni_eklenen")))

        # V13 — SAF karar fonksiyonu (mutasyon hedefi) yuk tasiyor mu
        iddia("V13 saf karar: silinmis&yeni -> dirilen",
              dirilenleri_bul({"b"}, {"a", "b"}, set()) == (["b"], []))
        iddia("V13b saf karar: beyanli olan dirilen SAYILMAZ",
              dirilenleri_bul({"b"}, {"a", "b"}, {"b"}) == ([], ["b"]))

        # ======================== EKSEN 2 — ALAN GERILEMESI ========================
        # ORTAK TARIH: kayit `a` ILERI duzeltildi (fiyat 100->250, baslik, kapak
        # gorseli -1 -> -1-v2). Kayit `b` hic dokunulmadi ve fiyati BASKA (500 TL).
        A_ESKI = _gorsel("a", 1)
        A_V2 = "https://media.pruvo3d.com/urunler/a-1-v2.jpg"
        A_IKI = _gorsel("a", 2)

        def alan_depo(ad):
            d = _depo_kur(kok, ad)
            _yaz(d, [_urun("a", gorseller=[A_ESKI, A_IKI]), _urun("b", fiyat="500 TL")])
            _commit(d, "ilk katalog")
            _yaz(d, [_urun("a", fiyat="250 TL", baslik="A yeni baslik",
                           gorseller=[A_V2, A_IKI]),
                     _urun("b", fiyat="500 TL")])
            _commit(d, "a duzeltildi: fiyat + baslik + kapak gorseli v2 (ILERI yon)")
            return d

        def _a(depo, **ek):
            """HEAD'deki `a` kaydi uzerine <ek> uygulanir; `b` degismeden yazilir."""
            a = _urun("a", fiyat="250 TL", baslik="A yeni baslik", gorseller=[A_V2, A_IKI])
            a.update(ek)
            _yaz(depo, [a, _urun("b", fiyat="500 TL")])

        # A1 POZITIF — fiyat ESKI degerine dondu
        a1 = alan_depo("a1")
        _a(a1, fiyat="100 TL")
        _commit(a1, "merge kurbani: a'nin fiyati eski degerine dondu")
        du, sa, o = kapi(depo=a1)
        iddia("A1 [POZITIF] alan ESKI degerine dondu -> KIRMIZI (rc 1)",
              du == "KIRMIZI" and DURUM_KOD[du] == 1
              and any(s[0] == "GERILEME" and s[1] == "a#fiyat" for s in sa), (du, sa))
        iddia("A1b teshis anahtari `<id>#<alan>` bicimindedir ve TEK gerileme sayar",
              o.get("alan_gerilemesi") == 1, (o.get("alan_gerilemesi"), sa))

        # A2 NEGATIF — ILERI yon: gecmiste HIC gorulmemis YENI deger
        a2 = alan_depo("a2")
        _a(a2, fiyat="400 TL")
        _commit(a2, "a'nin fiyati yeni bir degere cikti (ILERI yon)")
        du, sa, o = kapi(depo=a2)
        iddia("A2 [NEGATIF] alan YENI (hic gorulmemis) degere degisti -> YESIL "
              "(aday URETILDI ama hukum YOK)",
              du == "YESIL" and o.get("aday_alan") == 1, (du, o.get("aday_alan"), sa))

        # A3 NEGATIF — alan hic degismedi
        a3 = alan_depo("a3")
        with open(os.path.join(a3, "README.md"), "w") as f:
            f.write("x\n")
        _commit(a3, "urunler.json'a dokunulmadi")
        du, _s, o = kapi(depo=a3)
        iddia("A3 [NEGATIF] alan HIC degismedi -> YESIL, aday 0",
              du == "YESIL" and o.get("aday_alan") == 0, (du, o.get("aday_alan")))

        # A4 POZITIF — 30 Tem'in IKINCI olayi: `-v2` kapak gorseli gerilemesi
        a4 = alan_depo("a4")
        _a(a4, gorseller=[A_ESKI, A_IKI])
        _commit(a4, "merge kurbani: kapak gorseli v2'den eski dosyaya dondu")
        du, sa, _o = kapi(depo=a4)
        iddia("A4 [POZITIF] `-v2` kapak gorseli gerilemesi -> KIRMIZI",
              du == "KIRMIZI" and any(s[0] == "GERILEME" and s[1] == "a#gorseller"
                                      for s in sa), (du, sa))

        # A5 NEGATIF — BEYANLI (gerekceli) alan geri almasi
        a5 = alan_depo("a5")
        _a(a5, fiyat="100 TL")
        with open(os.path.join(a5, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"a#fiyat": "kampanya bitti, eski fiyata KraL onayiyla donuldu"}, f)
        _commit(a5, "fiyat beyanla geri alindi")
        du, sa, _o = kapi(depo=a5)
        iddia("A5 [NEGATIF] `<id>#<alan>` gerekceli beyan -> YESIL", du == "YESIL", du)
        iddia("A5b beyanli alan geri almasi raporda GORUNUR (sessiz gecmez)",
              any(s[0] == "BEYANLI" and s[1] == "a#fiyat" for s in sa), sa)

        # A6 POZITIF — BOS GEREKCELI alan beyani muafiyet SAYILMAZ
        a6 = alan_depo("a6")
        _a(a6, fiyat="100 TL")
        with open(os.path.join(a6, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"a#fiyat": "  "}, f)
        _commit(a6, "fiyat bos gerekceyle geri alindi")
        du, sa, _o = kapi(depo=a6)
        iddia("A6 [POZITIF] BOS GEREKCELI alan beyani -> KIRMIZI",
              du == "KIRMIZI" and any(s[0] == "BEYAN" for s in sa), (du, sa))

        # A7 FAIL-CLOSED — gecmis okunamiyor (SIG depo) + GERCEK alan gerilemesi
        a7 = alan_depo("a7")
        _a(a7, fiyat="100 TL")
        _commit(a7, "fiyat geriledi")
        a7sig = os.path.join(kok, "a7-sig")
        _kos(kok, "clone", "-q", "--depth", "1", "file://" + a7, a7sig)
        du, sa, _o = kapi(depo=a7sig)
        iddia("A7 [FAIL-CLOSED] gecmis okunamadi + alan gerilemesi -> OLCULEMEDI (rc 2)",
              du == "OLCULEMEDI" and DURUM_KOD[du] == 2, (du, sa))

        # A8 NEGATIF — baslik ILERI duzeltildi
        a8 = alan_depo("a8")
        _a(a8, baslik="A daha da yeni baslik")
        _commit(a8, "baslik ileri yonde duzeltildi")
        du, _s, o = kapi(depo=a8)
        iddia("A8 [NEGATIF] baslik ILERI duzeltmesi -> YESIL", du == "YESIL", (du, o))

        # A9 NEGATIF — gorseller YENIDEN DIZILDI (kume ayni) -> aday bile uretmez
        a9 = alan_depo("a9")
        _a(a9, gorseller=[A_IKI, A_V2])
        _commit(a9, "gorseller yeniden dizildi (icerik ayni)")
        du, _s, o = kapi(depo=a9)
        iddia("A9 [NEGATIF] alan SIRASI degisti, icerik ayni -> YESIL + aday 0",
              du == "YESIL" and o.get("aday_alan") == 0, (du, o.get("aday_alan")))

        # A10 POZITIF — alan gerilemesi + ayni commit'te YENI urun: yesil SATIN ALMAZ
        a10 = alan_depo("a10")
        _yaz(a10, [_urun("a", fiyat="100 TL", baslik="A yeni baslik",
                         gorseller=[A_V2, A_IKI]),
                   _urun("b", fiyat="500 TL"), _urun("yepyeni")])
        _commit(a10, "fiyat geriledi + yeni urun eklendi")
        du, _s, o = kapi(depo=a10)
        iddia("A10 [POZITIF] yeni urun ile birlikte gelen alan gerilemesi yine KIRMIZI",
              du == "KIRMIZI" and o.get("alan_gerilemesi") == 1
              and o.get("yeni_eklenen") == 1,
              (du, o.get("alan_gerilemesi"), o.get("yeni_eklenen")))

        # A11 POZITIF — LISANS ATFI geriledi (ticari/hukuki sinif)
        a11 = _depo_kur(kok, "a11")
        _yaz(a11, [_urun("a", lisans={"tasarimci": "eski-kayit", "tur": "CC BY 4.0"}), "b"])
        _commit(a11, "ilk katalog")
        _yaz(a11, [_urun("a", lisans={"tasarimci": "dogru-kayit", "tur": "CC BY 4.0"}), "b"])
        _commit(a11, "lisans atfi duzeltildi")
        _yaz(a11, [_urun("a", lisans={"tasarimci": "eski-kayit", "tur": "CC BY 4.0"}), "b"])
        _commit(a11, "merge kurbani: lisans atfi eski hatali degere dondu")
        du, sa, _o = kapi(depo=a11)
        iddia("A11 [POZITIF] lisans atfi gerilemesi -> KIRMIZI",
              du == "KIRMIZI" and any(s[0] == "GERILEME" and s[1] == "a#lisans"
                                      for s in sa), (du, sa))

        # A12 NEGATIF — KAPSAM DISI alan (marka) geriledi: kapi SUSAR (kapsam SABIT)
        a12 = _depo_kur(kok, "a12")
        _yaz(a12, [_urun("a", marka=["EskiMarka"]), "b"])
        _commit(a12, "ilk katalog")
        _yaz(a12, [_urun("a", marka=["YeniMarka"]), "b"])
        _commit(a12, "marka normalize edildi")
        _yaz(a12, [_urun("a", marka=["EskiMarka"]), "b"])
        _commit(a12, "marka eski degerine dondu (KAPSAM DISI)")
        du, _s, o = kapi(depo=a12)
        iddia("A12 [NEGATIF] KAPSAM DISI alan (marka) gerilemesi -> YESIL + aday 0",
              du == "YESIL" and o.get("aday_alan") == 0, (du, o.get("aday_alan")))

        # A13 FAIL-CLOSED — ATTRIBUTION calismiyor (depo .gitattributes diff surucusunu eziyor)
        a13 = alan_depo("a13")
        with open(os.path.join(a13, ".gitattributes"), "w", encoding="utf-8") as f:
            f.write("urunler.json diff=surucusuz\n")
        _a(a13, fiyat="100 TL")
        _commit(a13, "fiyat geriledi ama attribution ezildi")
        du, sa, _o = kapi(depo=a13)
        iddia("A13 [FAIL-CLOSED] hunk baglami YOK -> OLCULEMEDI (sessiz YESIL degil)",
              du == "OLCULEMEDI" and any("baglami TASIMIYOR" in s[2] for s in sa),
              (du, sa))

        # A14 FAIL-CLOSED — KESIK hunk baglami BIRDEN COK adaya uyuyor
        onek = "cok-uzun-urun-kimligi-" + ("z" * 200)
        u1, u2 = onek + "-birinci", onek + "-ikinci"
        a14 = _depo_kur(kok, "a14")
        _yaz(a14, [_urun(u1, fiyat="100 TL"), _urun(u2, fiyat="100 TL")])
        _commit(a14, "ilk katalog")
        _yaz(a14, [_urun(u1, fiyat="250 TL"), _urun(u2, fiyat="250 TL")])
        _commit(a14, "fiyatlar guncellendi")
        _yaz(a14, [_urun(u1, fiyat="100 TL"), _urun(u2, fiyat="100 TL")])
        _commit(a14, "fiyatlar eski degerine dondu (KESIK baglam)")
        du, sa, _o = kapi(depo=a14)
        iddia("A14 [FAIL-CLOSED] KESIK hunk baglami BELIRSIZ -> OLCULEMEDI",
              du == "OLCULEMEDI" and any("KESIK hunk baglami" in s[2] for s in sa),
              (du, sa))

        # A15 NEGATIF — ATTRIBUTION KAYDA OZEL: baska kaydin terk ettigi deger susar
        a15 = alan_depo("a15")
        _yaz(a15, [_urun("a", fiyat="250 TL", baslik="A yeni baslik",
                         gorseller=[A_V2, A_IKI]),
                   _urun("b", fiyat="100 TL")])
        _commit(a15, "b'nin fiyati a'nin gecmiste terk ettigi degere esitlendi")
        du, sa, o = kapi(depo=a15)
        iddia("A15 [NEGATIF] BASKA kaydin terk ettigi deger gerileme SAYILMAZ -> YESIL",
              du == "YESIL" and o.get("aday_alan") == 1, (du, o.get("aday_alan"), sa))

        # A16 BEYAN EDILEN SINIR — alan SILINMESI olculmez ama SESSIZ de gecmez
        a16 = alan_depo("a16")
        a16_a = _urun("a", fiyat="250 TL", baslik="A yeni baslik",
                      gorseller=[A_V2, A_IKI])
        a16_a.pop("aciklama")
        _yaz(a16, [a16_a, _urun("b", fiyat="500 TL")])
        _commit(a16, "aciklama alani silindi")
        du, sa, o = kapi(depo=a16)
        iddia("A16 [SINIR] alan SILINMESI hukum uretmez -> YESIL",
              du == "YESIL" and o.get("silinen_alan") == 1, (du, o.get("silinen_alan")))
        iddia("A16b sinir SESSIZ degil: BILGI satiri olarak BASILIR",
              any(s[0] == "BILGI" and s[1] == "a#aciklama" for s in sa), sa)

        # A18 NEGATIF — TOPLU beyan `*#<alan>`: OLCULEN `1606e166` sinifi (11.573 kayitta
        # fiyat BILEREK geri alindi). Kural gevsetilmez, geri alma BEYAN EDILIR.
        a18 = alan_depo("a18")
        _a(a18, fiyat="100 TL")
        with open(os.path.join(a18, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"*#fiyat": "yanlis kapsamli toplu fiyat degisikligi bilerek geri "
                                  "alindi (KraL karari)"}, f)
        _commit(a18, "toplu fiyat geri alma, beyanli")
        du, sa, _o = kapi(depo=a18)
        iddia("A18 [NEGATIF] `*#<alan>` gerekceli TOPLU beyan -> YESIL",
              du == "YESIL" and any(s[0] == "BEYANLI" and s[1] == "a#fiyat" for s in sa),
              (du, sa))

        # A18b POZITIF — joker YALNIZ beyan edilen ALANI kapsar; baska alan hala KIRMIZI
        a18b = alan_depo("a18b")
        _a(a18b, fiyat="100 TL", gorseller=[A_ESKI, A_IKI])
        with open(os.path.join(a18b, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"*#fiyat": "yalniz fiyat geri alindi"}, f)
        _commit(a18b, "fiyat beyanli, gorsel beyansiz geriledi")
        du, sa, o = kapi(depo=a18b)
        iddia("A18b [POZITIF] `*#fiyat` jokeri `gorseller` gerilemesini KAPATMAZ",
              du == "KIRMIZI" and o.get("alan_gerilemesi") == 1
              and any(s[0] == "GERILEME" and s[1] == "a#gorseller" for s in sa),
              (du, o.get("alan_gerilemesi"), sa))

        # A18c NEGATIF — `<id>#*` jokeri: o KAYDIN tum alanlari beyanli
        a18c = alan_depo("a18c")
        _a(a18c, fiyat="100 TL", gorseller=[A_ESKI, A_IKI])
        with open(os.path.join(a18c, IZIN_ADI), "w", encoding="utf-8") as f:
            json.dump({"a#*": "bu kaydin tamami bilerek eski haline dondaruldu"}, f)
        _commit(a18c, "kayit bazli toplu geri alma, beyanli")
        du, sa, o = kapi(depo=a18c)
        iddia("A18c [NEGATIF] `<id>#*` gerekceli beyan o kaydin TUM alanlarini kapsar",
              du == "YESIL" and o.get("beyanli_alan") == 2, (du, o.get("beyanli_alan"), sa))

        # A19 POZITIF — BLANKET beyan (`*` / `*#*`) KABUL EDILMEZ: kapiyi tek satirla
        # olduren joker OLMAMALIDIR.
        for blanket in ("*", "*#*"):
            a19 = alan_depo("a19-" + blanket.replace("*", "y").replace("#", "-"))
            _a(a19, fiyat="100 TL")
            with open(os.path.join(a19, IZIN_ADI), "w", encoding="utf-8") as f:
                json.dump({blanket: "her seyi kapat"}, f)
            _commit(a19, "blanket beyan denemesi")
            du, sa, _o = kapi(depo=a19)
            iddia("A19 [POZITIF] BLANKET beyan %r KABUL EDILMEZ -> KIRMIZI" % blanket,
                  du == "KIRMIZI" and any(s[0] == "BEYAN" and "BLANKET" in s[2]
                                          for s in sa), (du, sa))

        # A17 — SAF karar/turetim fonksiyonlari (EKSEN 2 mutasyon hedefleri)
        adaylar17, silinen17 = adaylari_turet(
            {"x": {"fiyat": "100 TL"}}, {"x": {"fiyat": "250 TL"}})
        iddia("A17 saf turetim: degisen alan aday olur",
              adaylar17 == {("x", "fiyat"): frozenset({'"fiyat": "250 TL"'})}
              and not silinen17, (adaylar17, silinen17))
        iddia("A17b saf turetim: yalniz YENIDE olan kayit aday DEGIL (EKSEN 1'in konusu)",
              adaylari_turet({}, {"x": {"fiyat": "250 TL"}}) == ({}, []))
        iddia("A17c saf karar: `+` VE `-` gorulmusse gerileme",
              alan_gerilemeleri_bul({("x", "fiyat"): frozenset({"L"})},
                                    {("x", "L")}, {("x", "L")}, set())
              == ([("x#fiyat", ["L"])], []))
        iddia("A17d saf karar: yalniz `+` gorulmus (TERK EDILMEMIS) -> gerileme DEGIL",
              alan_gerilemeleri_bul({("x", "fiyat"): frozenset({"L"})},
                                    {("x", "L")}, set(), set()) == ([], []))
        iddia("A17e saf karar: BASKA kaydin gecmisi hukum uretmez",
              alan_gerilemeleri_bul({("x", "fiyat"): frozenset({"L"})},
                                    {("y", "L")}, {("y", "L")}, set()) == ([], []))
        iddia("A17f saf karar: beyanli anahtar gerileme SAYILMAZ",
              alan_gerilemeleri_bul({("x", "fiyat"): frozenset({"L"})},
                                    {("x", "L")}, {("x", "L")}, {"x#fiyat"})
              == ([], [("x#fiyat", ["L"])]))
        iddia("A17g satir normallestirme SON VIRGULU atar (dizideki yer degisimi "
              "SAHTE fark uretmez)",
              satir_normalle('      "u1",') == satir_normalle('      "u1"') == '"u1"')
        iddia("A17i saf beyan eslesmesi: tam anahtar · `<id>#*` · `*#<alan>` eslesir, "
              "ilgisiz joker ESLESMEZ",
              izin_eslesir("x", "fiyat", {"x#fiyat"})
              and izin_eslesir("x", "fiyat", {"x#*"})
              and izin_eslesir("x", "fiyat", {"*#fiyat"})
              and not izin_eslesir("x", "fiyat", {"y#*", "*#gorseller", "x"}))
        # ⚠️ CIVI BILEREK: kapsam degisirse bu iddia KIRMIZI yanar ve ELLE ONAY ister
        # (kapsam sessizce ne buyur ne kucultulur). 31 Tem: `eski_fiyat` eklendi —
        # fiyat ekseniyle AYNI sinif (musteriye gorunur + ticari; yaniltici indirim).
        iddia("A17h kapsam SABIT liste (8 alan) — 'tum alanlar' DEGIL",
              KAPSAM_ALANLARI == ("gorseller", "fiyat", "eski_fiyat", "baslik", "aciklama",
                                  "kategori", "lisans", "parametrik"),
              KAPSAM_ALANLARI)

    # ---- GERCEK DEPO ayagi: salt-okunurluk + yanlis-pozitif kanaryasi + iki eksen
    try:
        gercek = depo_kok()
        urunler_yolu = os.path.join(gercek, URUNLER_ADI)

        def _sha():
            h = hashlib.sha256()
            with open(urunler_yolu, "rb") as f:
                for blok in iter(lambda: f.read(1 << 20), b""):
                    h.update(blok)
            return h.hexdigest()

        once_sha = _sha()
        _rc, once_porc, _e = _git(gercek, "status", "--porcelain")
        du, _s, o14 = kapi(depo=gercek)
        sonra_sha = _sha()
        _rc, sonra_porc, _e = _git(gercek, "status", "--porcelain")
        iddia("V14 SALT-OKUNUR: urunler.json sha256 koşum oncesi==sonrasi",
              once_sha == sonra_sha, (once_sha[:12], sonra_sha[:12]))
        iddia("V14b SALT-OKUNUR: `git status --porcelain` degismedi",
              once_porc == sonra_porc)
        gercek_ever, _ar, _ek, _o = gecmiste_gorulen(gercek, "HEAD")
        _rc, gercek_metin, gercek_hata = _git(gercek, "show", "HEAD:" + URUNLER_ADI)
        if _rc != 0:
            raise Olculemedi("gercek katalog HEAD'den okunamadi: %s" % gercek_hata[:200])
        gercek_govde = json.loads(gercek_metin)
        gercek_head = {u["id"] for u in gercek_govde
                       if isinstance(u, dict) and isinstance(u.get("id"), str)}
        gercek_silinmis = sorted(gercek_ever - gercek_head)
        gecici = os.path.join(tempfile.gettempdir(), "pruvo-diriltme-gercek.json")

        def _gecici_kapi(govde):
            """urunler.json'a DOKUNULMAZ — kopya GECICI dosyaya yazilir."""
            try:
                with open(gecici, "w", encoding="utf-8") as f:
                    json.dump(govde, f, ensure_ascii=False, indent=2)
                return kapi(depo=gercek, taban="HEAD", yeni_dosya=gecici)
            finally:
                if os.path.exists(gecici):
                    os.remove(gecici)

        # V15 YANLIS-POZITIF KANARYASI: HEAD^1 -> HEAD'in YESIL oldugunu varsaymak
        # bayat bir fiksturdur; HEAD mesru bir geri alma commit'i de olabilir. Gercek
        # katalogun degismemis HEAD anlik goruntusu ise her HEAD'de kanonik NEGATIF vakadir.
        du15, sa15, o15 = _gecici_kapi(gercek_govde)
        iddia("V15 [NEGATIF] GERCEK katalogun degismemis HEAD anlik goruntusu -> YESIL "
              "(kapi 'hep kirmizi' degil; silinmis kume %s id)" % o15.get("silinmis"),
              du15 == "YESIL" and o15.get("aday_alan") == 0,
              (du15, o15, sa15[:3]))

        # V16 POZITIF, GERCEK KATALOG: gercekten silinmis bir id GERI KONULURSA yanar.
        if not gercek_silinmis:
            iddia("V16 [POZITIF] GERCEK silinmis kume BOS -> vaka kurulamadi", False)
        else:
            kurban = gercek_silinmis[0]
            du16, sa16, o16 = _gecici_kapi(gercek_govde + [_urun(kurban)])
            iddia("V16 [POZITIF] GERCEK katalogda silinmis %r geri konunca -> KIRMIZI"
                  % kurban,
                  du16 == "KIRMIZI" and any(s[0] == "DIRILTME" and s[1] == kurban
                                            for s in sa16),
                  (du16, o16.get("dirilen")))

        # ---- A20/A21 GERCEK KATALOG, ALAN EKSENI: `-vN` kapak gorseli duzeltmesi.
        #   A20 [POZITIF] duzeltmenin GERI ALINMASI (merge kurbani)      -> KIRMIZI
        #   A21 [NEGATIF] AYNI kaydin ILERI yonde yeniden duzeltilmesi   -> YESIL
        # Fikstur GERCEK gecmisten turetilir; sabit SHA / urun adi GOMULMEZ (bayatlar).
        vn = re.compile(r"^(?P<kok>.+?)-v(?P<n>\d+)(?P<uzanti>\.[A-Za-z0-9]+)$")
        hedef = None
        for u in gercek_govde:
            if not isinstance(u, dict) or not isinstance(u.get("gorseller"), list):
                continue
            for i, g in enumerate(u["gorseller"]):
                if not isinstance(g, str):
                    continue
                m = vn.match(g)
                if not m:
                    continue
                n = int(m.group("n"))
                onceki = (m.group("kok") + m.group("uzanti") if n == 2
                          else "%s-v%d%s" % (m.group("kok"), n - 1, m.group("uzanti")))
                hedef = (u["id"], i, onceki, g)
                break
            if hedef:
                break
        if not hedef:
            iddia("A20/A21 GERCEK `-vN` gorsel duzeltmesi katalogda BULUNAMADI -> "
                  "fikstur kurulamadi (sessiz gecilmez)", False)
        else:
            uid, i, onceki, simdiki = hedef

            def _govde_ile(yeni_url):
                out = []
                for u in gercek_govde:
                    if isinstance(u, dict) and u.get("id") == uid:
                        k = dict(u)
                        gs = list(k["gorseller"])
                        gs[i] = yeni_url
                        k["gorseller"] = gs
                        out.append(k)
                    else:
                        out.append(u)
                return out

            du20, sa20, o20 = _gecici_kapi(_govde_ile(onceki))
            iddia("A20 [POZITIF] GERCEK katalogda `%s` -> `%s` gerilemesi KIRMIZI"
                  % (os.path.basename(simdiki), os.path.basename(onceki)),
                  du20 == "KIRMIZI"
                  and any(s[0] == "GERILEME" and s[1] == uid + "#gorseller"
                          for s in sa20),
                  (du20, o20.get("alan_gerilemesi"), sa20[:3]))
            uz = simdiki.rsplit(".", 1)
            ileri = uz[0] + "-ileri-fikstur." + uz[1]
            du21, sa21, o21 = _gecici_kapi(_govde_ile(ileri))
            iddia("A21 [NEGATIF] AYNI kaydin ILERI yonde (duzelt.py) yeniden "
                  "duzeltilmesi -> YESIL (mesru duzeltme BLOKLANMAZ)",
                  du21 == "YESIL" and o21.get("aday_alan") == 1,
                  (du21, o21.get("aday_alan"), sa21[:3]))
    except Exception as e:                                   # pragma: no cover
        kirmizi += 1
        ham.append("    ❌ GERCEK depo olcumu yapilamadi — %r" % (e,))

    print("\n".join(ham))
    print("----------------------------------------------------------------------")
    print("IDDIA SAYISI: %d" % len([s for s in ham if s.strip()[:1] in ("✅", "❌")]))
    if kirmizi == 0:
        print("SONUC: YESIL ✅ (kendini test) — POZITIF ve NEGATIF yonler ayri ayri olculdu.")
        return 0
    print("SONUC: KIRMIZI ❌ — %d iddia kaldi" % kirmizi)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--depo", help="depo koku (varsayilan: bu dosyanin deposu / cwd)")
    ap.add_argument("--taban", help="onceki durum (varsayilan: HEAD^1)")
    ap.add_argument("--yeni", dest="yeni_rev", help="yeni durum revizyonu (varsayilan: HEAD)")
    ap.add_argument("--calisma-agaci", action="store_true",
                    help="yeni durum = calisma agacindaki urunler.json (taban HEAD)")
    ap.add_argument("--azami-sure", type=float, default=None,
                    help="gecmis taramasi icin saniye tavani; asilirsa OLCULEMEDI")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    a = ap.parse_args()
    if a.kendini:
        return kendini_test()
    yeni_dosya = None
    if a.calisma_agaci:
        yeni_dosya = os.path.join(depo_kok(a.depo), URUNLER_ADI)
    durum, satirlar, olcumler = kapi(depo=a.depo, taban=a.taban, yeni_rev=a.yeni_rev,
                                     yeni_dosya=yeni_dosya, azami_sure=a.azami_sure)
    return rapor(durum, satirlar, olcumler)


if __name__ == "__main__":
    sys.exit(main())

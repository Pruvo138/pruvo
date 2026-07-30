#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/icra-suzgeci.py — "BU KABUK SATIRI GERCEKTEN <X>'i ICRA EDIYOR MU" TEK KAYNAGI.

NEDEN VAR (30 Tem yargi turu, OLCULEN 4 SESSIZ KACIS YOLU): CI nobetcilerinin
"cagri duruyor mu" olcumu DUZ METIN uzerinden yapiliyordu. Metin "duruyor" dedigi
halde CI'da HICBIR SEY olculmeyen dort yol geciciler kopyada olculdu ve DORT
denetci de rc=0 verdi (tam ham cikti RAPOR-MIMARA.md'de):

  1. `run: python3 tools/ci-kapsam-test.py --help`   -> argparse kullanim metnini
     basip exit 0; kapi hala "kosuluyor" sayiyordu.
  2. `run: echo python3 tools/ci-kapsam-test.py --kendini-test` -> `echo` MENSIYONU
     duz `in` aramasinda "cagri" sayiliyordu.
  3. `"jenerator/hacim.js" in deploy_metni` (jenerator/test/kabul.py TEST 4) -> satir
     yoruma alinsa ya da `echo`'ya cevrilse iddia HALA True.
  4. `"konfigur-test.py" in adim and "run:" in adim`
     (tools/konfigur-nobet-mutasyon.py) -> ayni sinif; rapor "BLOKLAYICI" yaziyordu.

BU DOSYA NE YAPAR: bir KABUK SATIRINI gercek bir sozcuk ayiricisiyla (`shlex`,
POSIX kipi, `punctuation_chars`) jetonlar, `&&`/`||`/`;`/`|` ayiraclarindan
segmentlere boler ve her segmentin BASINDAKI komutu bulur. Boylece
"metin geciyor mu" sorusu "komut GERCEKTEN kosuluyor mu" sorusuna cevrilir.

🔴 AYRISTIRICI TAKLIDI YOK ([[mimar-kapi-parser-taklidi]]): `shlex` standart
kutuphanenin GERCEK kabuk sozcuk ayiricisidir; elle tirnak/jeton mantigi
YAZILMAZ (bu depoda TUR 3'te elle yazilan tirnak ayristiricisi mesru yazimlari
sahte-KIRMIZI yakmisti). YAML ekseni de taklit edilmez: ayristirma
tools/is-akisi-kapisi.py'nin GERCEK YAML kolundan (PyYAML / ruby-psych) gelir,
bu dosya yalnizca KABUK eksenini sahiplenir.

🔴 UC DURUMLU HUKUM (yanlis-pozitif TUM ekibin yayinini durdurur,
[[kapi-kapsam-eksen-secimi]]): fonksiyonlar `EVET` / `HAYIR` / `OLCULEMEDI`
dondurur. Jetonlama patlarsa (dengesiz tirnak vb.) hukum `OLCULEMEDI`'dir ve
tuketiciler onu "bugunku davranis" (yani cagri SAYILIR) gibi ele alir ->
yeni bir sahte-kirmizi yuzeyi ACILMAZ. Yalnizca EMIN olunan olumsuzluk
(kara listedeki bayrak / mensiyon komutu / baska betik) isirir.

TEK KAYNAK SOZLESMESI (kopyalama = drift):
  * tools/ci-kapsam-test.py       -> `onek_re`, `anlamli_cagri` (KABUK ekseni)
  * tools/is-akisi-kapisi.py      -> `anlamli_cagri`, `etkili_arguman`,
                                     `birlestir_devam` (YAML ekseni kendisinde)
  * jenerator/test/kabul.py       -> is-akisi-kapisi.etkili_mensiyon uzerinden
  * tools/konfigur-nobet-mutasyon.py -> is-akisi-kapisi.etkili_kapi_cagrilari

Bu dosya kesif predikatlarina (tools/*-test.py · test-*.py · *-kapisi.py)
BILEREK UYMAZ: kosulabilir bir kabul testi DEGIL, kutuphanedir -> CI kapsam
kapisinin muhasebesine girmez. Kendi nobetciligi tuketicilerinin kabul
testlerindedir (govdesi no-op yapilinca / cagrisi silinince KIRMIZI).
"""
import os
import re
import shlex

# ---------------------------------------------------------------------------
# HUKUM SABITLERI
# ---------------------------------------------------------------------------
EVET = "EVET"
HAYIR = "HAYIR"
OLCULEMEDI = "OLCULEMEDI"

# ---- KARA LISTE 1 — ICRA SAYILMAYAN BAYRAKLAR ------------------------------
# 🔴 BEYAZ LISTE DEGIL KARA LISTE (mimar hukmu): "hangi bayraklar gecerli" diye
# saymak imkansizdir (her betigin kendi bayraklari var) ve her eksik giris sahte
# KIRMIZI uretir. Bunun yerine "cagriyi ANLAMSIZ kilan" SONLU kume yazilir.
# Kumeye girme olcutu: bayrak, betigin OLCUM govdesini HIC kosturmadan surecin
# exit 0 vermesine yol acar.
ICRA_DISI_BAYRAKLAR = {
    "--help": "argparse/commander yalniz KULLANIM metnini basar ve exit 0 verir; "
              "hicbir iddia olculmez (olculdu: 30 Tem, delik 1)",
    "-h": "`--help` kisaltmasi (argparse varsayilani); ayni davranis",
    "--version": "yalniz surum dizesini basar, exit 0; olcum govdesi kosmaz",
    "-V": "`--version` kisa bicimi (BUYUK V). Kucuk `-v` BILEREK LISTEDE DEGIL: "
          "cogu araçta 'verbose' demektir ve GERCEK olcum yapan bir cagri olabilir",
    "--usage": "kullanim metni basar, exit 0",
}
# ⚠️ LISTEYE EKLENMEYENLER + GEREKCE (bilincli):
#   `-v` / `--verbose`  -> olcum KOSAR, yalniz ciktisi ayrintilanir
#   `--dry-run` / `-n`  -> bu depoda GERCEK iddia olcen kiplerde de kullanilir
#                          (or. d1-sync.py --durum sinifi); anlamsiz DEGIL
#   `--kendini-test`    -> tam tersine, olcumun TA KENDISI
#   `--deploy` / `--dizin` / `--paket` / `--anahat` -> girdi/kip secer, olcum kosar

# ---- KARA LISTE 2 — MENSIYON KOMUTLARI -------------------------------------
# Argumanini YAZDIRAN / OKUYAN, ama ICRA ETMEYEN komutlar. Bir kapi yolu bu
# komutlarin argumaninda geciyorsa "cagri" DEGIL "mensiyon"dur.
MENSIYON_KOMUTLARI = {
    "echo": "argumani stdout'a basar, icra etmez (olculdu: 30 Tem, delik 3)",
    "printf": "bicimli basar, icra etmez",
    "print": "basar, icra etmez",
    ":": "kabuk no-op yerlesigi; daima 0 doner",
    "true": "daima 0 doner",
    "false": "daima 1 doner; argumanini icra etmez",
    "cat": "dosya ICERIGINI basar",
    "head": "dosya basini basar",
    "tail": "dosya sonunu basar",
    "grep": "metin ARAR, icra etmez",
    "egrep": "grep varyanti",
    "fgrep": "grep varyanti",
    "rg": "ripgrep — metin arar",
    "sed": "metin donusturur",
    "awk": "metin isler",
    "wc": "sayar",
    "ls": "listeler",
    "stat": "dosya bilgisi basar",
    "file": "dosya turu basar",
    "test": "kosul degerlendirir",
    "[": "`test` yerlesigi",
    "which": "yol cozer",
    "type": "komut turu basar",
}

# ---- SAYDAM SARMALAYICILAR — asil komuta gecmek icin soyulur ---------------
SAYDAM_SARMALAYICILAR = frozenset((
    "env", "command", "exec", "nice", "nohup", "time", "stdbuf", "xvfb-run",
    "setsid", "ionice",
))

# ---- KABUK -c SARMALAYICILARI — arguman DIZESI komuttur (icine inilir) -----
KABUK_ADLARI = frozenset(("bash", "sh", "zsh", "dash", "ksh"))

# ---- YORUMLAYICILAR — "<yorumlayici> <betik>" bicimi ----------------------
# Uzantidan yorumlayici turetme (ci-kapsam-test.py'nin eski YORUMLAYICI tablosu
# BURAYA TASINDI — orada kopya BIRAKILMADI).
UZANTI_YORUMLAYICI = {".py": "python3", ".js": "node", ".mjs": "node", ".cjs": "node"}
PYTHON_RE = re.compile(r"^python(?:2|3)?(?:\.\d+)?$")
NODE_RE = re.compile(r"^node(?:js)?$")
# Yorumlayici bayraklarindan DEGER alanlar (bir sonraki jeton bayragin degeridir,
# betik yolu DEGILDIR).
DEGERLI_YORUMLAYICI_BAYRAKLARI = frozenset(("-X", "--check-hash-based-pycs",
                                            "-W", "--max-old-space-size"))
# Betik YOLU yerine SATIR-ICI KOD / MODUL kosturan bayraklar -> "<yol> cagrisi" DEGIL.
KOD_BAYRAKLARI = frozenset(("-c", "-m", "-e", "--eval", "-p", "--print", "--input-type"))

ATAMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Kabuk ayiraclari (shlex punctuation_chars bunlari ayri jeton yapar).
AYIRAC_JETONLARI = frozenset(("&&", "||", ";", "|", "&", ";;", "|&", "(", ")",
                              "{", "}", "\n"))
# Yonlendirme jetonlari — arguman DEGIL (kara liste taramasinda atlanir).
YONLENDIRME_JETONLARI = frozenset((">", ">>", "<", "<<", "<<<", "2>", "2>>", "&>",
                                   ">&", "|&"))


def yorumlayici_adi(yol):
    """<yol> hangi yorumlayiciyla kosulur? Bilinmeyen uzanti -> python3 (fail-closed:
    eslesme DARALIR, yani dosya 'kosulmuyor' sayilir ve kapsam kapisi konusur)."""
    return UZANTI_YORUMLAYICI.get(os.path.splitext(yol)[1], "python3")


def onek_re(yol):
    """TEK KAYNAK — 'bu komut govdesi <yol>'u kosuyor' KABA metin capasi.

    Komut govdesi '<yorumlayici> <yol>' ile BASLAMALI; negatif ileri-bakis
    (?![\\w./-]) uzun bir baska yolun on-eki olarak yanlis eslesmeyi engeller ve
    '<yol> --bayrak' biciminde BAYRAKLI cagriyi DOGRU eslestirir.

    ⚠️ Bu capa YALNIZ ADAY BULUR ("bu satirda bu yol geciyor olabilir");
    "cagri ANLAMLI mi" hukmunu `anlamli_cagri()` verir. Ikisi ayri katmandir:
    capa GENIS ve ucuz, hukum DAR ve jetonlu. (Eskiden tek katman vardi ve
    `--help` mutanti capadan gecip 'kosuluyor' sayiliyordu.)"""
    return re.compile(r"^" + yorumlayici_adi(yol) + r"\s+" + re.escape(yol)
                      + r"(?![\w./-])")


def birlestir_devam(metin):
    """Kabuk SATIR DEVAMLARINI (`\\` ile biten satir) birlestir; satir listesi dondur.

    NEDEN SART: `run: |` blogunda mesru bir cagri
        python3 tools/x-test.py \\
            --bayrak
    biciminde yazilabilir (olculdu: bu depoda MESRU bicim listesinde). Satir bazli
    gezen bir suzgec bunu iki YARIM satir gorur ve cagriyi KACIRIR -> sahte KIRMIZI.
    """
    satirlar = []
    tampon = ""
    for ham in metin.splitlines():
        s = ham.rstrip()
        if s.endswith("\\") and not s.endswith("\\\\"):
            tampon += s[:-1] + " "
            continue
        satirlar.append(tampon + ham)
        tampon = ""
    if tampon:
        satirlar.append(tampon)
    return satirlar


def kabuk_yorumu_mu(satir):
    """strip() sonrasi `#` ile basliyor mu (kabuk yorumu -> ICRA DEGIL)."""
    return satir.strip().startswith("#")


def jetonla(satir):
    """(segmentler, hata) — <satir>'i kabuk segmentlerine ayir.

    segmentler: [[jeton, ...], ...] — `&&`/`||`/`;`/`|` ayiraclarindan bolunmus.
    hata: jetonlama patlarsa (dengesiz tirnak vb.) tani metni; o halde segmentler None
    ve hukum OLCULEMEDI olur (fail-open: bugunku davranis korunur)."""
    lx = shlex.shlex(satir, posix=True, punctuation_chars=True)
    lx.whitespace_split = True
    try:
        jetonlar = list(lx)
    except ValueError as e:
        return None, "jetonlama basarisiz (%s)" % e
    segmentler = []
    cari = []
    for j in jetonlar:
        if j in AYIRAC_JETONLARI:
            if cari:
                segmentler.append(cari)
            cari = []
            continue
        cari.append(j)
    if cari:
        segmentler.append(cari)
    return segmentler, None


def _yol_esit(jeton, yol):
    """<jeton> repo-goreli <yol>'u mu gosteriyor? `./` oneki ve fazladan `/` normalize
    edilir; MUTLAK yol ya da baska bir dizinden gorece yol EslesMEZ (dar tutulur)."""
    if not jeton or jeton.startswith("-"):
        return False
    return os.path.normpath(jeton) == os.path.normpath(yol)


def _onekleri_soy(jetonlar):
    """Bastaki ORTAM ATAMALARINI (`FOO=bar`) ve SAYDAM SARMALAYICILARI soy."""
    j = list(jetonlar)
    sarmalayici_gorulen = False
    while j:
        bas = j[0]
        if ATAMA_RE.match(bas):
            j.pop(0)
            continue
        if os.path.basename(bas) in SAYDAM_SARMALAYICILAR:
            j.pop(0)
            sarmalayici_gorulen = True
            continue
        if sarmalayici_gorulen and bas.startswith("-"):
            # `env -i` / `stdbuf -oL` gibi sarmalayici bayraklari
            j.pop(0)
            continue
        break
    return j


def _kara_bayraklar(argumanlar):
    """<argumanlar> icindeki ICRA_DISI_BAYRAKLAR (sirali, tekrarsiz)."""
    bulunan = []
    for a in argumanlar:
        if a in YONLENDIRME_JETONLARI:
            continue
        if a in ICRA_DISI_BAYRAKLAR and a not in bulunan:
            bulunan.append(a)
    return bulunan


def _segment_hukmu(jetonlar, yol, derinlik=0):
    """(hukum, sebep, argumanlar) — TEK bir kabuk segmenti <yol>'u ICRA EDIYOR mu."""
    j = _onekleri_soy(jetonlar)
    if not j:
        return None, None, None  # ilgisiz segment (yalniz atama vb.)
    bas = j[0]
    ad = os.path.basename(bas)

    # (1) MENSIYON komutu — argumaninda yol gecse bile ICRA DEGIL.
    # `_yol_esit` YANINDA duz alt-dize de bakilir: `echo 'python3 tools/x.py --bayrak'`
    # yaziminda TIRNAKLI komutun TAMAMI TEK jetondur, yani yol jetona ESIT degil ICINDE
    # gecer. (Hukum ya HAYIR ya ilgisiz olacagi icin tuketici davranisi ayni; fark
    # TANININ okunurlugundadir — mimar "neden kirmizi" sorusunu ciktidan cevaplayabilsin.)
    if ad in MENSIYON_KOMUTLARI:
        if any(_yol_esit(t, yol) or yol in t for t in j[1:]):
            return HAYIR, ("`%s` MENSIYON komutu: %s" % (ad, MENSIYON_KOMUTLARI[ad])), None
        return None, None, None

    # (1b) TEK JETONLUK SARMAL — jetonun KENDISI bir komut satiri.
    # OLCULDU (yanlis-pozitif senaryosu F12): `run: "python3 tools/x.py --bayrak"`
    # MESRU bir YAML cift-tirnakli skalardir. Metin duzleminde calisan tuketici
    # (ci-kapsam-test.py) `run:` onekini soyunca elinde TIRNAKLI dize kalir; shlex
    # tirnagi cozup BIR jeton uretir -> bas komut "python3 ..." dizesinin TAMAMI olur
    # ve cagri GORUNMEZ hale gelirdi (sahte KIRMIZI, TUR 3 tuzaginin ayni sinifi).
    # KURAL: tek jeton + icinde BOSLUK varsa o jeton ancak TIRNAKTAN gelmis olabilir;
    # `bash -c "<komut>"` ile AYNI muamele goruр komut olarak yeniden jetonlanir.
    # Bu YAML BICIMI TAHMINI DEGILDIR — jeton sayisi + bosluk olcumudur.
    if len(j) == 1 and derinlik < 3 and (" " in bas or "\t" in bas):
        ic_segmentler, ic_hata = jetonla(bas)
        if ic_hata:
            return OLCULEMEDI, ic_hata, None
        if not (len(ic_segmentler) == 1 and ic_segmentler[0] == j):
            for seg in ic_segmentler:
                h, s, a = _segment_hukmu(seg, yol, derinlik + 1)
                if h is not None:
                    return h, s, a
        return None, None, None

    # (2) `bash -c "<komut>"` — arguman DIZESI komuttur, icine in.
    if ad in KABUK_ADLARI and derinlik < 3:
        for i, t in enumerate(j[1:], 1):
            if t == "-c" and i + 1 < len(j):
                ic_segmentler, ic_hata = jetonla(j[i + 1])
                if ic_hata:
                    return OLCULEMEDI, ic_hata, None
                for seg in ic_segmentler:
                    h, s, a = _segment_hukmu(seg, yol, derinlik + 1)
                    if h is not None:
                        return h, s, a
                return None, None, None
        return None, None, None

    # (3) betik DOGRUDAN kosuluyor (`tools/x.py --bayrak`, shebang ile)
    if _yol_esit(bas, yol):
        argumanlar = j[1:]
        kara = _kara_bayraklar(argumanlar)
        if kara:
            return HAYIR, _kara_tani(kara), argumanlar
        return EVET, None, argumanlar

    # (4) `<yorumlayici> [yorumlayici-bayraklari] <betik> [argumanlar]`
    if not (PYTHON_RE.match(ad) or NODE_RE.match(ad)):
        return None, None, None
    i = 1
    while i < len(j) and j[i].startswith("-"):
        if j[i] in KOD_BAYRAKLARI:
            return None, None, None  # satir-ici kod / modul -> "<yol> cagrisi" DEGIL
        if j[i] in DEGERLI_YORUMLAYICI_BAYRAKLARI:
            i += 2
            continue
        i += 1
    if i >= len(j):
        return None, None, None  # yorumlayiciya betik verilmemis (REPL)
    if not _yol_esit(j[i], yol):
        return None, None, None  # BASKA bir betik
    argumanlar = j[i + 1:]
    kara = _kara_bayraklar(argumanlar)
    if kara:
        return HAYIR, _kara_tani(kara), argumanlar
    return EVET, None, argumanlar


def _kara_tani(kara):
    return "ICRA-DISI BAYRAK %s -> %s" % (
        ", ".join("`%s`" % b for b in kara),
        "; ".join(ICRA_DISI_BAYRAKLAR[b] for b in kara))


def anlamli_cagri(satir, yol):
    """(hukum, sebep, argumanlar) — <satir> <yol>'u ANLAMLI olarak icra ediyor mu?

    hukum:
      EVET       -> gercek, olcum yapan bir cagri (argumanlar listesi doner)
      HAYIR      -> cagri GORUNUYOR ama anlamsiz (kara liste bayragi / mensiyon
                    komutu); `sebep` tani metnidir
      OLCULEMEDI -> jetonlama patladi; tuketici bugunku davranisi korur (SAYAR)
      None       -> satir bu yolla ILGISIZ (aday degil)

    🔴 Kabuk YORUMU cagirici tarafindan (kabuk_yorumu_mu / YAML suzgeci) elenmis
    varsayilir; bu fonksiyon yorum satirini da jetonlar (shlex `#`'i yer) ve
    ilgisiz doner."""
    if not satir or not satir.strip():
        return None, None, None
    if kabuk_yorumu_mu(satir):
        return None, None, None
    segmentler, hata = jetonla(satir)
    if segmentler is None:
        # FAIL-OPEN (bilincli): jetonlanamayan satirda "cagri YOK" demek sahte
        # KIRMIZI uretir ve bu kapilar continue-on-error'SUZ kosar. Kaba capa
        # eslesiyorsa OLCULEMEDI, degilse ilgisiz.
        if onek_re(yol).match(satir.strip()):
            return OLCULEMEDI, hata, None
        return None, None, None
    sonuc = (None, None, None)
    for seg in segmentler:
        hukum, sebep, argumanlar = _segment_hukmu(seg, yol)
        if hukum == EVET:
            return EVET, None, argumanlar
        if hukum is not None and sonuc[0] is None:
            sonuc = (hukum, sebep, argumanlar)
    return sonuc


def cagri_sayilir(satir, yol):
    """BUGUNKU DAVRANISI KORUYAN kolaylik: cagri "duruyor" sayilir mi?
    EVET ve OLCULEMEDI -> True · HAYIR -> False · ilgisiz -> False."""
    hukum, _, _ = anlamli_cagri(satir, yol)
    return hukum in (EVET, OLCULEMEDI)


def etkili_arguman(satir, aranan):
    """(hukum, sebep) — <aranan> metni <satir>'da GERCEK bir komutun ARGUMANI mi?

    jenerator/test/kabul.py TEST 4'un ihtiyaci: "deploy.yml hacim.js'i GERCEKTEN
    kopyaliyor mu". `cp jenerator/hacim.js ... _site/jenerator/` -> EVET;
    `echo cp jenerator/hacim.js ...` / yoruma alinmis satir -> HAYIR/ilgisiz.

    Kapsam DAR: yalnizca komut BASI mensiyon komutu mu diye bakar; komutun
    SEMANTIGI (kopyaliyor mu, siliyor mu) DENETLENMEZ."""
    if not satir or not satir.strip() or kabuk_yorumu_mu(satir):
        return None, None
    segmentler, hata = jetonla(satir)
    if segmentler is None:
        if aranan in satir:
            return OLCULEMEDI, hata
        return None, None
    sonuc = (None, None)
    for seg in segmentler:
        j = _onekleri_soy(seg)
        if not j:
            continue
        ad = os.path.basename(j[0])
        if not any(aranan == t or aranan in t for t in j[1:]):
            continue
        if ad in MENSIYON_KOMUTLARI:
            if sonuc[0] is None:
                sonuc = (HAYIR, "`%s` MENSIYON komutu: %s"
                         % (ad, MENSIYON_KOMUTLARI[ad]))
            continue
        return EVET, None
    return sonuc

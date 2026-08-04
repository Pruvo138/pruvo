#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-kablolama-nobeti.py — KABLOLAMA + CIKIS-KODU-YUTMA nobetcisi.

Bu nobetci tools/kanca-nobeti.py'nin OLCMEDIGI eksenleri sahiplenir:

  🔴 EKSEN Y (YUTMA) — bir kanca beklenen araci CAGIRIYOR olabilir ve yine de
     HICBIR SEYI BLOKLAMIYOR olabilir. 4 Agu 2026'da olculen hal tam buydu:
         python3 "$guard" --tetik commit >/dev/null 2>&1 || true
     `tools/urunler-guard.py` FAIL-LOUD bir nobetciye cevrilmisti ama `|| true`
     cikis kodunu, `>/dev/null 2>&1` ise GEREKCEYI yutuyordu. kanca-nobeti.py bu
     satiri "cagri VAR" diye YESIL sayar — ve HAKLIDIR, onun ekseni cagrinin
     VARLIGIDIR. "Cagri var" ile "cagri BLOKLUYOR" AYRI IDDIALARDIR.

  🔴 EKSEN K (KABLOLAMA) — kancalar izlenen `tools/kancalar` kaynagindan
     ORTAK `.git/pruvo-kancalar/` altina KURULUR (tools/kanca-kur.py) ve
     `core.hooksPath` oraya baglanir. Bagli degilse depodaki fail-closed kod
     FIILEN kosmaz.

  🔴 EKSEN S (SAPMA) — kurulan kopya izlenen kaynagin SURETIDIR ve elle
     duzenlenebilir. Sapma sessiz kalirsa "depoda fail-closed, makinede
     fail-open" hali geri doner; bu, secilen tasarimin BEDELIDIR ve karsiligi
     bu eksendir (bayt-esitligi).

  🔴 EKSEN G (GEREKCE) — bloklamak fail-loud'un YARISIDIR. Kanca reddedince
     KENDI gerekcesini de basmalidir; basmazsa commit sessizce durur, mimar
     nedenini goremez ve `--no-verify`ye yonelir.

AYRI DOSYA, IKIZ TANIM YOK: kanca/arac tablosu tools/kanca-nobeti.py'deki
BEKLENEN'dir, kurulum sabitleri tools/kanca-kur.py'dedir; ikisi de IMPORT
edilir. Bu dosya yalnizca her (kanca, arac) cifti icin BIR POLITIKA ekler:
FAIL-CLOSED mi, yoksa BEYAN EDILMIS FAIL-OPEN mi. Tablolar AYRISIRSA hukum
KIRMIZI'dir ([[ikiz-tanim-sessiz-ayrisma]]).

🔴 MESRU FAIL-OPEN KIRILMAZ: bazi kanca bloklari BILINCLI olarak fail-open'dir
(yedek, posta kutusu arsivi, D1 senkronu — hepsi HIJYEN/SENKRON, YAYIN KAPISI
DEGIL). Kor bir "hicbir kancada `|| true` olmasin" kurali bu uc mesru blogu
kirmizi yakar ve her push'u durdururdu. Eksen bu yuzden ADIM ekseninde degil
(kanca, arac) ekseninde kurulur ve politika tablosu GEREKCE ISTER.

═══════════════════════════════════════════════════════════════════════════════
🔴 HANGI AGAC YARGILANIR (KUSUR 2 onarimi, mimar iadesi)
═══════════════════════════════════════════════════════════════════════════════
Ilk surum kablolamayi YALNIZ ANA CHECKOUT'a gore cozuyordu. OLCULDU ki bu,
kapatilmaya calisilan sessizligi yeniden uretir: kancalari OLU olan bir
worktree'nin ICINDEN kosturuldugunda nobetci `rc=0, 13 eksen 13 yesil` veriyordu
— cunku baktigi agac o agac DEGILDI.

ARTIK: eksenler NEREDEN KOSTURULDUYSA O AGACIN hali uzerinden olculur
(`etkin_hookspath(kaynak_kok)`), cunku `core.hooksPath` worktree BASINA
override edilebilir (`config.worktree`) ve fiilen kosan sey odur.

🔴 IZOLE AGAC MESRUDUR — YANLIS-POZITIF URETILMEZ: Claude Code'un izole
worktree'si kendi `config.worktree`sinde `core.hooksPath = /dev/null` TASIYABILIR
ve bu DOGRUDUR (izole agacta ana deponun kancalari kosmamalidir). Bu hal
KASITLI IZOLASYON olarak raporlanir ve kirmizi YAKMAZ.
  ⚠️ MUAFIYET DAR: yalnizca (a) deger TAM OLARAK `/dev/null` ISE ve (b) kaynak
  bir `config.worktree` DOSYASI ISE. Ayni deger PAYLASILAN `.git/config`ten
  geliyorsa bu, 1 Agu'ta olculen OLAYIN TA KENDISIDIR -> KIRMIZI. Muafiyetin
  DARLIGI kabul testinde tek degiskenli KONTROL iddiasiyla olculur.

═══════════════════════════════════════════════════════════════════════════════
IKI HAL — GELISTIRICI vs CI (yanlis-pozitif butcesi)
═══════════════════════════════════════════════════════════════════════════════
Kablolama `core.hooksPath`te yasar; `.git/` COMMIT EDILMEZ -> CI checkout'unda
ASLA kurulu degildir. Eksen K'yi CI'da kirmizi yakmak her yayini durdururdu;
sessizce yesil saymak ise fail-open'i geri getirirdi. Ikisi de yanlis:

  * VARSAYILAN (gelistirici/yerel): eksen K ve S OLCULUR. Kurulu degilse KIRMIZI
    + "python3 tools/kanca-kur.py" tarifi (gecis durustlugu).
  * `--ci`: eksen K ve S OLCULEMEDI olarak ILAN EDILIR (raporda GORUNUR) ve
    cikis kodunu ETKILEMEZ. CI'da olculen sey IZLENEN KAYNAKTIR: govdeler
    fail-closed mi, gerekce basiliyor mu, cagrilar duruyor mu, dosyalar git
    INDEKSINDE 100755 mi.
    ⚠️ MUAFIYET DAR: `--ci` yalnizca `_CI_MUAF_EKSENLER` kumesindeki eksenlerin
    OLCULEMEDI'sini affeder. BASKA bir eksen OLCULEMEDI olursa (or. kanca
    dosyasi okunamiyor) cikis yine SIFIR-DISIDIR. Muafiyetin darligi kabul
    testinde AYRI bir iddiayla olculur ([[maskeleme-kismi-kapatma]]).

Kullanim:
    python3 tools/kanca-kablolama-nobeti.py            # yerel hukum (rc 0/1)
    python3 tools/kanca-kablolama-nobeti.py --ci       # kaynak hukmu
    python3 tools/kanca-kablolama-nobeti.py --sessiz
    python3 tools/kanca-kablolama-nobeti.py --depo <yol>
"""
import importlib.util
import os
import re
import stat
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))

YESIL = "YESIL"
KIRMIZI = "KIRMIZI"
OLCULEMEDI = "OLCULEMEDI"
ISARET = {YESIL: "✅", KIRMIZI: "🔴", OLCULEMEDI: "⚪"}

# 🔴 KENDI SOZLESMESI — kabul testi bunu okur. Bir sabit/fonksiyon yeniden
# adlandirilirsa test COKMEK yerine KIRMIZI yakabilsin diye burada ILAN edilir
# (cokme kirmizi SAYILMAZ: o eksen OLCULMEMIS demektir).
SOZLESME = ("FAIL_CLOSED", "FAIL_OPEN", "YUTMA_DESENLERI", "GEREKCE_CAPALARI",
            "_CI_MUAF_EKSENLER", "EKSEN_KABLOLAMA", "EKSEN_SAPMA", "denetle",
            "genel_hal", "cikis_kodu", "yutma_hukmu", "bloklama_hukmu",
            "izole_agac_mi")

EKSEN_KABLOLAMA = "k) kablolama"
EKSEN_SAPMA = "s) sapma (kurulu kopya vs kaynak)"

# 🔴 `--ci` MUAFIYETININ TAM KAPSAMI. Genisletmek = gercek arizalarin CI'da
# sessizce gecmesi. Kabul testi bu kumenin DARLIGINI ayrica olcer.
_CI_MUAF_EKSENLER = frozenset({EKSEN_KABLOLAMA, EKSEN_SAPMA})

_NOBET_SOZLESME = ("BEKLENEN", "ana_checkout", "etkin_hookspath", "hooks_dizini",
                   "suzgec_yukle", "cagri_hukmu", "_etkili_satirlar",
                   "_yol_onekini_normalize", "_kosulsuz_exit_indeksi", "_git")

_KUR_SOZLESME = ("KANCA_DIZINI", "BEKLENEN_KANCALAR", "KURULU_DIZIN_ADI",
                 "kurulu_dizin", "sapma")


# ---------------------------------------------------------------------------
# POLITIKA — her (kanca, arac) cifti icin: BLOKLAMALI MI?
# ---------------------------------------------------------------------------
FAIL_CLOSED = {
    ("pre-commit", "tools/urunler-guard.py"):
        "katalog provenans guard'i FAIL-LOUD'dur (bozuk JSON / cozulemeyen "
        "provenans / izinsiz degisim -> sifir-disi). Cikis kodu yutulursa "
        "koruma SIFIRLANIR — 4 Agu 2026'da olculen delik tam budur.",
    ("pre-commit", "tools/mukerrer-kontrol.py"):
        "mukerrer id/baslik/kaynak linki commit'i BLOKLAR; yutulursa mukerrer "
        "urun katalogda yayina cikar.",
    ("pre-commit", "tools/mimar-commit-kapisi.py"):
        "mimar kod-kilidi backstop'u; yutulursa ana repodan onaysiz kaynak/veri "
        "commit'i gecer.",
    ("commit-msg", "tools/commit-mesaji-kapisi.py"):
        "commit MESAJI yazildiktan sonra degistirilemez (depo PUBLIC) -> tek "
        "onleyici yuzey budur; yutulursa tedarikci kimligi kalici olarak sizar.",
    ("pre-push", "tools/gecmis-geri-donus-kapisi.py"):
        "temizlenmis sizintiyi geri getiren itmeyi DURDURUR; yutulursa gecmis "
        "temizligi ucuncu kez geri doner ve hicbir yerde alarm calmaz.",
}

FAIL_OPEN = {
    ("pre-push", "tools/yedekle.py"):
        "Drive yedegi — yedek alinamazsa push DEVAM eder (blokta 'exit' YOK); "
        "tazelik ayrica tools/durum.py '7) YEDEK TAZELIGI'nde gorunur.",
    ("pre-push", "tools/kutu-arsivle.py"):
        "posta kutusu tavan arsivi — hijyen araci; kilit baskasindayken bile "
        "push durmamali.",
    ("pre-push", "tools/d1-sync.py"):
        "D1 senkronu — patlarsa site yayini durmasin; diff bekledigi icin bir "
        "sonraki push kendiliginden tekrar dener.",
}

# 🔴 EKSEN G: her fail-closed kanca REDDEDINCE kendi gerekcesini de BASMALIDIR.
# Capalar kanca govdesinin `echo` bloklarindadir.
GEREKCE_CAPALARI = {
    "pre-commit": ("COMMIT DURDURULDU", "COMMIT ENGELLENDI"),
    "commit-msg": ("COMMIT DURDURULDU",),
    "pre-push": ("PUSH DURDURULDU",),
}

# ---------------------------------------------------------------------------
# CIKIS KODU / GEREKCE YUTAN KABUK DEYIMLERI
# 🔴 BILINEN SINIR (KACAMAKSIZ): KAPALI bir listedir. Amaci "her kacisi
# yakalamak" degil, OLCULEN kacisi ve en yakin akrabalarini fail-closed hale
# getirmektir — DISIPLIN CIHAZI, KAFES DEGIL ([[kapi-disiplin-ilkesi]]).
# Ikinci kol EKSEN B'dir (rc FIILEN kontrol ediliyor mu).
# ---------------------------------------------------------------------------
YUTMA_DESENLERI = (
    (re.compile(r"\|\|\s*true(\s|$|;)"), "`|| true` — sifir-disi cikis YUTULUYOR"),
    (re.compile(r"\|\|\s*:(\s|$|;)"), "`|| :` — sifir-disi cikis YUTULUYOR"),
    (re.compile(r"\|\|\s*/bin/true(\s|$|;)"), "`|| /bin/true` — cikis YUTULUYOR"),
    (re.compile(r"\|\|\s*exit\s+0(\s|$|;)"), "`|| exit 0` — hata BASARIYA cevriliyor"),
    (re.compile(r"\|\|\s*echo\b"), "`|| echo` — hata yalniz MESAJA cevriliyor, blok YOK"),
    (re.compile(r"(?<![>&])&\s*$"), "satir `&` ile bitiyor — arka plana atiliyor, rc BEKLENMIYOR"),
    (re.compile(r"[^0-9<>]>\s*/dev/null"), "stdout `/dev/null`a atiliyor — GEREKCE gorunmez"),
    (re.compile(r"2>\s*/dev/null"), "stderr `/dev/null`a atiliyor — GEREKCE gorunmez"),
    (re.compile(r">\s*/dev/null\s+2>&1"), "stdout+stderr yutuluyor — GEREKCE gorunmez"),
)

_EXIT_NONZERO_RE = re.compile(r"\bexit\s+([1-9]\d*)\b")
_RC_YAKALA_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=\$\?\s*$")
_IF_DEGIL_RE = re.compile(r"^\s*(if|elif)\s+!\s")
_ILERI_PENCERE = 12
_RC_PENCERE = 3


class Olculemedi(Exception):
    """Olcum yapilamadi — YESIL SAYILMAZ."""


def _modul(ad, dosya, sozlesme):
    yol = os.path.join(TOOLS, dosya)
    if not os.path.exists(yol):
        raise Olculemedi("%s YOK -> bu nobetci onun tablosunu/yardimcilarini "
                         "kullanir, olcum yapilamaz (fail-closed)" % dosya)
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        raise Olculemedi("%s yuklenemedi (%s: %s)" % (dosya, type(e).__name__, e))
    for isim in sozlesme:
        if not hasattr(mod, isim):
            raise Olculemedi("%s icinde %s YOK -> sozlesme degismis (fail-closed)"
                             % (dosya, isim))
    return mod


def nobet_modulu():
    return _modul("pruvo_kanca_nobeti_kablolama", "kanca-nobeti.py", _NOBET_SOZLESME)


def kur_modulu():
    return _modul("pruvo_kanca_kur_kablolama", "kanca-kur.py", _KUR_SOZLESME)


# ---------------------------------------------------------------------------
# EKSEN D — POLITIKA TABLOSU ile BEKLENEN AYRISMIS MI?
# ---------------------------------------------------------------------------
def drift_bulgulari(nobet):
    beklenen = set()
    for kanca, araclar in nobet.BEKLENEN:
        for arac, _gerekce in araclar:
            beklenen.add((kanca, arac))
    politika = set(FAIL_CLOSED) | set(FAIL_OPEN)

    cakisma = set(FAIL_CLOSED) & set(FAIL_OPEN)
    if cakisma:
        return [("d) politika tutarliligi", KIRMIZI,
                 "ayni cift HEM fail-closed HEM fail-open ilan edilmis: %s"
                 % sorted(cakisma))]
    eksik = beklenen - politika
    fazla = politika - beklenen
    if eksik or fazla:
        parca = []
        if eksik:
            parca.append("BEKLENEN'de olup politikada OLMAYAN: %s" % sorted(eksik))
        if fazla:
            parca.append("politikada olup BEKLENEN'de OLMAYAN (bayat): %s" % sorted(fazla))
        return [("d) politika/BEKLENEN ayrismasi", KIRMIZI, "; ".join(parca))]
    return [("d) politika/BEKLENEN ayrismasi", YESIL,
             "%d cift TAM ESIT (%d fail-closed, %d beyan edilmis fail-open)"
             % (len(beklenen), len(FAIL_CLOSED), len(FAIL_OPEN)))]


# ---------------------------------------------------------------------------
# EKSEN Y + B
# ---------------------------------------------------------------------------
def _cagri_satiri(nobet, suzgec, govde, hedef):
    etkili = nobet._etkili_satirlar(govde, suzgec)
    for i, islenmis, ham in etkili:
        satir = nobet._yol_onekini_normalize(islenmis, hedef)
        hukum, _sebep, _arg = suzgec.anlamli_cagri(satir, hedef)
        if hukum == suzgec.EVET:
            return i, satir, ham, etkili
    return None, None, None, etkili


def yutma_hukmu(satir):
    """(yutuyor_mu, tani) — cagri satiri cikis kodunu/gerekceyi yutuyor mu?"""
    for desen, tarif in YUTMA_DESENLERI:
        if desen.search(satir):
            return True, tarif
    return False, None


def bloklama_hukmu(etkili, indeks, ham):
    """(bloklu_mu, tani) — cagrinin rc'si sifir-disi cikisa BAGLANIYOR mu?

    Uc mesru bicim (hepsi gercek kanca govdelerinde OLCULDU):
      (i)   `python3 X || exit 1`
      (ii)  `if ! python3 X; then ... exit 1 ... fi`
      (iii) `python3 X` + `rc=$?` + `... exit 1`"""
    if _EXIT_NONZERO_RE.search(ham):
        return True, None
    sonrakiler = [(i, isl, h) for i, isl, h in etkili if i > indeks]
    if _IF_DEGIL_RE.match(ham):
        for _i, _isl, h in sonrakiler[:_ILERI_PENCERE]:
            if _EXIT_NONZERO_RE.search(h):
                return True, None
        return False, ("`if !` blogu var ama sonraki %d satirda sifir-disi `exit` "
                       "YOK -> hata yalniz raporlaniyor, islem DURMUYOR" % _ILERI_PENCERE)
    rc_yakalandi = any(_RC_YAKALA_RE.match(h) for _i, _isl, h in sonrakiler[:_RC_PENCERE])
    if rc_yakalandi:
        for _i, _isl, h in sonrakiler[:_ILERI_PENCERE]:
            if _EXIT_NONZERO_RE.search(h):
                return True, None
        return False, ("cikis kodu `$?` ile yakalaniyor ama sonraki %d satirda "
                       "sifir-disi `exit` YOK -> rc okunup ATILIYOR" % _ILERI_PENCERE)
    return False, ("cagrinin cikis kodu HICBIR YERDE kontrol edilmiyor (`|| exit`, "
                   "`if !` ya da `rc=$?` YOK) -> arac reddetse bile islem DEVAM eder")


# ---------------------------------------------------------------------------
# EKSEN K — KABLOLAMA (KOSTURULDUGU AGACIN hali)
# ---------------------------------------------------------------------------
def izole_agac_mi(deger, kaynak):
    """Bu agac KASITLI olarak izole mi (Claude Code worktree izolasyonu)?

    🔴 MUAFIYET DAR: yalnizca deger TAM OLARAK `/dev/null` VE kaynak bir
    `config.worktree` dosyasi ise. Ayni deger PAYLASILAN `.git/config`ten
    geliyorsa 1 Agu'ta olculen OLAYIN TA KENDISIDIR -> muaf DEGIL."""
    if deger is None:
        return False
    if os.path.normpath(deger.strip()) != os.path.normpath("/dev/null"):
        return False
    dosya = (kaynak or "").replace("file:", "")
    return os.path.basename(dosya) == "config.worktree"


def kablolama_bulgusu(nobet, kur, kaynak_kok, ci):
    if ci:
        return (EKSEN_KABLOLAMA, OLCULEMEDI,
                "CI checkout'unda `core.hooksPath` KURULU DEGILDIR (`.git/` "
                "commit edilmez) -> bu eksen CI'da OLCULEMEZ ve cikis kodunu "
                "ETKILEMEZ. Yerelde: python3 tools/kanca-kablolama-nobeti.py")
    try:
        deger, kaynak, tani = nobet.etkin_hookspath(kaynak_kok)
    except Exception as e:
        return (EKSEN_KABLOLAMA, OLCULEMEDI, "etkin deger okunamadi (%s)" % e)
    if tani:
        return (EKSEN_KABLOLAMA, OLCULEMEDI, tani)

    if izole_agac_mi(deger, kaynak):
        return (EKSEN_KABLOLAMA, YESIL,
                "KASITLI IZOLE AGAC: core.hooksPath=/dev/null ve kaynak bu "
                "worktree'nin config.worktree'si -> ana deponun kancalari burada "
                "KOSMAMALIDIR (mesru). [kaynak: %s]" % (kaynak or "?"))
    try:
        beklenen = kur.kurulu_dizin(kaynak_kok)
    except Exception as e:
        return (EKSEN_KABLOLAMA, OLCULEMEDI, "kurulu dizin cozulemedi (%s)" % e)

    if deger is None:
        return (EKSEN_KABLOLAMA, KIRMIZI,
                "core.hooksPath AYARLI DEGIL -> git hala `.git/hooks`u kosar; "
                "izlenen kaynaktan kurulan kancalar DEVREDE DEGIL. "
                "Kur: python3 tools/kanca-kur.py")
    ham = deger.strip()
    cozulen = ham if os.path.isabs(ham) else os.path.normpath(
        os.path.join(kaynak_kok, ham))
    if os.path.normpath(cozulen) != os.path.normpath(beklenen):
        return (EKSEN_KABLOLAMA, KIRMIZI,
                "core.hooksPath KURULU dizini gostermiyor: %r -> %s (beklenen %s) "
                "[kaynak: %s]" % (ham, cozulen, beklenen, kaynak or "?"))
    if not os.path.isdir(cozulen):
        return (EKSEN_KABLOLAMA, KIRMIZI,
                "core.hooksPath VAR OLMAYAN dizini gosteriyor: %s -> BU AGACTA "
                "HICBIR KANCA KOSMAZ (sessiz)" % cozulen)
    return (EKSEN_KABLOLAMA, YESIL,
            "core.hooksPath = %s [kaynak: %s]" % (cozulen, kaynak or "?"))


def sapma_bulgusu(nobet, kur, ana_kok, kaynak_kok, ci):
    """Kurulan kopya IZLENEN kaynakla bayt-esit mi?"""
    if ci:
        return (EKSEN_SAPMA, OLCULEMEDI,
                "CI checkout'unda kurulu kopya YOKTUR -> bu eksen CI'da OLCULEMEZ "
                "ve cikis kodunu ETKILEMEZ.")
    try:
        deger, kaynak, tani = nobet.etkin_hookspath(kaynak_kok)
    except Exception as e:
        return (EKSEN_SAPMA, OLCULEMEDI, "etkin deger okunamadi (%s)" % e)
    if tani:
        return (EKSEN_SAPMA, OLCULEMEDI, tani)
    if izole_agac_mi(deger, kaynak):
        return (EKSEN_SAPMA, YESIL, "kasitli izole agac -> kurulu kopya ILGISIZ")
    if deger is None:
        return (EKSEN_SAPMA, OLCULEMEDI, "kablolama kurulu degil (bkz. eksen k)")
    ham = deger.strip()
    kurulu = ham if os.path.isabs(ham) else os.path.normpath(
        os.path.join(kaynak_kok, ham))

    # 🔴 KAYNAK REFERANSI: once KOSTURULDUGU agac, sonra ANA checkout. Eski bir
    # commit'teki agacta `tools/kancalar` bulunmayabilir — bu, kancalarin OLU
    # oldugu anlamina GELMEZ (kurulu kopya ortak `.git` altindadir), yalnizca
    # sapmanin O AGACTAN olculemedigi anlamina gelir.
    kaynak_dizin = None
    for aday in (kaynak_kok, ana_kok):
        aday_dizin = os.path.join(aday, kur.KANCA_DIZINI)
        if os.path.isdir(aday_dizin):
            kaynak_dizin = aday_dizin
            break
    if kaynak_dizin is None:
        return (EKSEN_SAPMA, OLCULEMEDI,
                "izlenen kanca kaynagi ne bu agacta ne ana checkout'ta bulundu "
                "-> sapma karsilastirilamaz")
    try:
        sapanlar = kur.sapma(kaynak_dizin, kurulu)
    except Exception as e:
        return (EKSEN_SAPMA, OLCULEMEDI, "sapma olculemedi (%s)" % e)
    if sapanlar:
        return (EKSEN_SAPMA, KIRMIZI,
                "kurulu kopya IZLENEN kaynaktan SAPMIS: %s -> depoda fail-closed "
                "ama makinede BASKA bir kod kosuyor. Tazele: python3 "
                "tools/kanca-kur.py" % ", ".join(sapanlar))
    return (EKSEN_SAPMA, YESIL, "kurulu kopya %s ile BAYT-ESIT" % kaynak_dizin)


# ---------------------------------------------------------------------------
# EKSEN M — GIT INDEKSINDE x-BITI
# ---------------------------------------------------------------------------
def _indeks_modlari(kur, kok):
    """({ad: mod}, tani) — <kok> indeksindeki izlenen kanca modlari."""
    try:
        p = subprocess.run(["git", "-C", kok, "ls-files", "-s", kur.KANCA_DIZINI],
                           capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return None, "git ls-files kosturulamadi: %s" % e
    if p.returncode != 0:
        return None, "git ls-files rc=%d: %s" % (p.returncode, p.stderr.strip()[:120])
    modlar = {}
    for satir in p.stdout.splitlines():
        parcalar = satir.split(None, 3)
        if len(parcalar) < 4:
            continue
        modlar[os.path.basename(parcalar[3].strip())] = parcalar[0]
    return modlar, None


def indeks_modu_bulgulari(kur, kaynak_kok, ana_kok, ci):
    """Izlenen kancalar git INDEKSINDE 100755 mi?

    🔴 NEDEN: x-biti CALISMA AGACINDA dogru olsa bile INDEKSTE 100644 ise TAZE
    BIR KLONDA kancalar x-bitsiz iner ve git onlari SESSIZCE atlar.

    🔴 HANGI AGAC: bu eksen DEPONUN bir ozelligidir, belli bir checkout'un
    degil. Eski bir commit'teki worktree `tools/kancalar` TASIMAYABILIR ve bu
    MESRUDUR (kurulu kopya ortak `.git` altindadir, kancalar yine kosar) —
    orada KIRMIZI yakmak yanlis-pozitif olurdu. Bu yuzden yerel halde once
    KOSTURULDUGU agac, sonra ANA checkout denenir. `--ci` halinde ise checkout
    ZATEN izlenen kaynagi tasimalidir -> yoklugu KIRMIZI'dir."""
    modlar, tani = _indeks_modlari(kur, kaynak_kok)
    if modlar is not None and not modlar and not ci:
        ana_modlar, ana_tani = _indeks_modlari(kur, ana_kok)
        if ana_modlar:
            modlar, tani = ana_modlar, ana_tani
    if modlar is None:
        return [("m) indeks modu", OLCULEMEDI, tani)]
    if not modlar:
        if ci:
            return [("m) indeks modu", KIRMIZI,
                     "%s indekste HIC izlenmiyor -> taze klonda kanca INMEZ"
                     % kur.KANCA_DIZINI)]
        return [("m) indeks modu", OLCULEMEDI,
                 "%s ne bu agacin ne ana checkout'un indeksinde -> indeks modu "
                 "bu makineden OLCULEMEDI" % kur.KANCA_DIZINI)]
    bulgular = []
    for ad in kur.BEKLENEN_KANCALAR:
        mod = modlar.get(ad)
        if mod is None:
            bulgular.append(("m) indeks %s" % ad, KIRMIZI,
                             "indekste YOK -> taze klonda bu kanca inmez"))
        elif mod != "100755":
            bulgular.append(("m) indeks %s" % ad, KIRMIZI,
                             "indeks modu %s (100755 degil) -> taze klonda x-bitsiz "
                             "iner, git SESSIZCE atlar" % mod))
        else:
            bulgular.append(("m) indeks %s" % ad, YESIL, "100755"))
    return bulgular


# ---------------------------------------------------------------------------
# GOVDE KAYNAGI
# ---------------------------------------------------------------------------
def govde_dizini(nobet, kur, kaynak_kok, ci):
    """(dizin, hal, tani) — govdelerin okunacagi dizin.

    ci=True  -> CARI AGACTAKI izlenen kaynak (tools/kancalar).
    ci=False -> KOSTURULDUGU AGACIN etkin kanca dizini (FIILEN kosan kod)."""
    if ci:
        yol = os.path.join(kaynak_kok, kur.KANCA_DIZINI)
        if not os.path.isdir(yol):
            return None, OLCULEMEDI, "izlenen kanca dizini YOK: %s" % yol
        return yol, YESIL, None
    deger, kaynak, tani = nobet.etkin_hookspath(kaynak_kok)
    if tani:
        return None, OLCULEMEDI, tani
    if izole_agac_mi(deger, kaynak):
        return None, YESIL, "kasitli izole agac -> govde yargilanmaz"
    dizin, hal, hata = nobet.hooks_dizini(kaynak_kok, deger)
    if hal == "OLU":
        return None, KIRMIZI, hata
    if hal == "OLCULEMEDI":
        return None, OLCULEMEDI, hata
    return dizin, YESIL, None


# ---------------------------------------------------------------------------
# DENETIM
# ---------------------------------------------------------------------------
def denetle(kok, ci=False, kaynak_kok=None):
    """[(eksen, hal, mesaj)] — tum eksenlerin hukmu (fail-closed).

    `kok`        = ANA CHECKOUT (sapma icin ikincil kaynak referansi).
    `kaynak_kok` = KOSTURULDUGU AGAC — eksen K, S ve govdeler ONUN uzerinden
                   olculur (KUSUR 2 onarimi). Verilmezse `kok` kullanilir."""
    kaynak_kok = kaynak_kok or kok
    try:
        nobet = nobet_modulu()
        kur = kur_modulu()
    except Olculemedi as e:
        return [("modul", OLCULEMEDI, str(e))]
    try:
        suzgec = nobet.suzgec_yukle()
    except Exception as e:
        return [("suzgec", OLCULEMEDI, str(e))]

    bulgular = list(drift_bulgulari(nobet))
    bulgular.append(kablolama_bulgusu(nobet, kur, kaynak_kok, ci))
    bulgular.append(sapma_bulgusu(nobet, kur, kok, kaynak_kok, ci))
    bulgular.extend(indeks_modu_bulgulari(kur, kaynak_kok, kok, ci))

    dizin, hal, tani = govde_dizini(nobet, kur, kaynak_kok, ci)
    if dizin is None:
        bulgular.append(("govde kaynagi", hal, tani))
        if hal != YESIL:      # izole agacta govde eksenleri ILGISIZDIR
            for (kanca, arac) in sorted(FAIL_CLOSED):
                bulgular.append(("y) %s -> %s" % (kanca, arac), OLCULEMEDI,
                                 "kanca dizini cozulemedi (bkz. govde kaynagi)"))
        return bulgular
    bulgular.append(("govde kaynagi", YESIL, dizin))

    # --- EKSEN G: GEREKCE GORUNURLUGU (fail-loud'un yarisi) ------------------
    for kanca in sorted({k for k, _a in FAIL_CLOSED}):
        capalar = GEREKCE_CAPALARI.get(kanca, ())
        yol = os.path.join(dizin, kanca)
        if not capalar or not os.path.isfile(yol):
            continue
        try:
            govde = open(yol, encoding="utf-8", errors="replace").read()
        except OSError as e:
            bulgular.append(("g) %s gerekce" % kanca, OLCULEMEDI, "okunamadi: %s" % e))
            continue
        if not any(c in govde for c in capalar):
            bulgular.append(("g) %s gerekce" % kanca, KIRMIZI,
                             "kanca REDDEDINCE kendi gerekcesini BASMIYOR (%s "
                             "capalarindan hicbiri govdede YOK) -> islem sessizce "
                             "durur, mimar nedenini goremez ve `--no-verify`ye "
                             "yonelir" % " / ".join(capalar)))
        else:
            bulgular.append(("g) %s gerekce" % kanca, YESIL,
                             "reddetme gerekcesi BASILIYOR"))

    for (kanca, arac) in sorted(FAIL_CLOSED):
        eksen = "y) %s -> %s" % (kanca, arac)
        yol = os.path.join(dizin, kanca)
        if not os.path.isfile(yol):
            bulgular.append((eksen, KIRMIZI, "kanca dosyasi YOK: %s" % yol))
            continue
        try:
            st = os.stat(yol)
            govde = open(yol, encoding="utf-8", errors="replace").read()
        except OSError as e:
            bulgular.append((eksen, OLCULEMEDI, "okunamadi: %s" % e))
            continue
        if not (st.st_mode & stat.S_IXUSR):
            bulgular.append((eksen, KIRMIZI,
                             "kanca calistirilabilir DEGIL -> git SESSIZCE atlar"))
            continue

        indeks, satir, ham, etkili = _cagri_satiri(nobet, suzgec, govde, arac)
        if indeks is None:
            bulgular.append((eksen, KIRMIZI,
                             "govdede %s'i ICRA EDEN satir YOK -> koruma tamamen "
                             "kayip [%s]" % (arac, FAIL_CLOSED[(kanca, arac)][:70])))
            continue
        exit_i = nobet._kosulsuz_exit_indeksi(etkili)
        if exit_i is not None and indeks > exit_i:
            bulgular.append((eksen, KIRMIZI,
                             "cagri (satir %d) ONCESINDE girintisiz KOSULSUZ `exit` "
                             "var (satir %d) -> HIC kosmaz" % (indeks + 1, exit_i + 1)))
            continue
        yutuyor, tani_y = yutma_hukmu(satir)
        if yutuyor:
            bulgular.append((eksen, KIRMIZI,
                             "satir %d FAIL-OPEN: %s [kaybolan koruma: %s]"
                             % (indeks + 1, tani_y, FAIL_CLOSED[(kanca, arac)][:90])))
            continue
        bloklu, tani_b = bloklama_hukmu(etkili, indeks, ham)
        if not bloklu:
            bulgular.append((eksen, KIRMIZI,
                             "satir %d FAIL-OPEN: %s [kaybolan koruma: %s]"
                             % (indeks + 1, tani_b, FAIL_CLOSED[(kanca, arac)][:90])))
            continue
        bulgular.append((eksen, YESIL, "satir %d fail-closed (rc bloka bagli)"
                         % (indeks + 1)))
    return bulgular


def genel_hal(bulgular):
    """🔴 FAIL-CLOSED: OLCULEMEDI asla YESIL'e YUVARLANMAZ."""
    if any(h == KIRMIZI for _e, h, _m in bulgular):
        return KIRMIZI
    if any(h == OLCULEMEDI for _e, h, _m in bulgular):
        return OLCULEMEDI
    return YESIL


def cikis_kodu(bulgular, ci):
    """Cikis kodu.

    🔴 `--ci` MUAFIYETI DARDIR: yalnizca `_CI_MUAF_EKSENLER` kumesindeki
    eksenlerin OLCULEMEDI'si affedilir (CI'da kablolama/kurulu kopya ZATEN
    olamaz). BASKA bir eksenin OLCULEMEDI'si fail-closed'dir — aksi halde
    "olcemedim" diyen her gercek ariza CI'da sessizce gecerdi
    ([[maskeleme-kismi-kapatma]])."""
    if any(h == KIRMIZI for _e, h, _m in bulgular):
        return 1
    for eksen, hal, _m in bulgular:
        if hal != OLCULEMEDI:
            continue
        if ci and eksen in _CI_MUAF_EKSENLER:
            continue
        return 1
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    kok = None
    if "--depo" in argv:
        i = argv.index("--depo")
        if i + 1 >= len(argv):
            print("HATA: --depo bir yol bekler", file=sys.stderr)
            return 2
        kok = argv[i + 1]
        del argv[i:i + 2]
    ci = "--ci" in argv
    sessiz = "--sessiz" in argv
    bilinmeyen = [a for a in argv if a not in ("--ci", "--sessiz")]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    try:
        nobet = nobet_modulu()
    except Olculemedi as e:
        print("⚪ OLCULEMEDI: %s" % e)
        return 1
    baslangic = os.path.abspath(kok) if kok else os.path.dirname(TOOLS)
    ana_kok, tani = nobet.ana_checkout(baslangic)
    if ana_kok is None:
        print("⚪ OLCULEMEDI: %s" % tani)
        return 1
    rc0, ust, _e = nobet._git(baslangic, "rev-parse", "--path-format=absolute",
                              "--show-toplevel")
    kaynak_kok = ust if rc0 == 0 and ust else ana_kok

    try:
        bulgular = denetle(ana_kok, ci=ci, kaynak_kok=kaynak_kok)
    except Exception as e:
        print("⚪ OLCULEMEDI: denetim patladi (%s: %s)" % (type(e).__name__, e))
        return 1

    hal = genel_hal(bulgular)
    rc = cikis_kodu(bulgular, ci)
    if not sessiz:
        print("KANCA KABLOLAMA NOBETI — yargilanan agac: %s   (ana: %s) [%s]"
              % (kaynak_kok, ana_kok,
                 "CI hali: kaynak" if ci else "yerel hal: fiilen kosan"))
        for eksen, h, mesaj in bulgular:
            print("  %s %-46s %s" % (ISARET[h], eksen, mesaj))
        kirmizi = sum(1 for _e, h, _m in bulgular if h == KIRMIZI)
        olcusuz = sum(1 for _e, h, _m in bulgular if h == OLCULEMEDI)
        print("\n%d eksen: %d yesil, %d kirmizi, %d olculemedi"
              % (len(bulgular), len(bulgular) - kirmizi - olcusuz, kirmizi, olcusuz))
    print("SONUC: %s (cikis %d)" % (hal, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())

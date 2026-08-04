#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-kablolama-nobeti.py — KABLOLAMA + CIKIS-KODU-YUTMA nobetcisi.

Bu nobetci tools/kanca-nobeti.py'nin OLCMEDIGI iki ekseni sahiplenir:

  🔴 EKSEN Y (YUTMA) — bir kanca beklenen araci CAGIRIYOR olabilir ve yine de
     HICBIR SEYI BLOKLAMIYOR olabilir. 4 Agu 2026'da olculen hal tam buydu:
         python3 "$guard" --tetik commit >/dev/null 2>&1 || true
     `tools/urunler-guard.py` FAIL-LOUD bir nobetciye cevrilmisti (sifir-disi
     cikis + stderr'e gerekce) ama `|| true` cikis kodunu, `>/dev/null 2>&1` ise
     GEREKCEYI yutuyordu. tools/kanca-nobeti.py bu satiri "cagri VAR" diye YESIL
     sayar — ve HAKLIDIR, onun ekseni cagrinin VARLIGIDIR. "Cagri var" ile
     "cagri BLOKLUYOR" AYRI IDDIALARDIR; ikincisi burada olculur.

  🔴 EKSEN K (KABLOLAMA) — kancalar artik `.git/hooks` altinda (commit
     EDILMEYEN, tek makinede yasayan) kopyalar degil, IZLENEN `tools/kancalar`
     kaynagidir; `core.hooksPath` oraya bagli DEGILSE depodaki fail-closed kod
     FIILEN kosmaz. Kurulum: tools/kanca-kur.py.

AYRI DOSYA, IKIZ TANIM YOK: kanca/arac tablosu tools/kanca-nobeti.py'deki
BEKLENEN'dir ve buradan IMPORT edilir. Bu dosya yalnizca her (kanca, arac)
cifti icin BIR POLITIKA ekler: FAIL-CLOSED mi, yoksa BEYAN EDILMIS FAIL-OPEN mi.
Iki tablo AYRISIRSA (birinde olup digerinde olmayan cift) hukum KIRMIZI'dir —
sessiz ayrisma yasak ([[ikiz-tanim-sessiz-ayrisma]]).

🔴 MESRU FAIL-OPEN KIRILMAZ: bu depoda bazi kanca bloklari BILINCLI olarak
fail-open'dir ve oyle kalmalidir (yedek, posta kutusu arsivi, D1 senkronu —
hepsi HIJYEN/SENKRON, YAYIN KAPISI DEGIL; patlarlarsa push durmamalidir).
Kor bir "hicbir kancada `|| true` olmasin" kurali bu uc mesru blogu kirmizi
yakar ve her push'u durdururdu. Bu yuzden eksen ADIM ekseninde degil
(kanca, arac) ekseninde kurulur ve politika tablosu GEREKCE ISTER.

═══════════════════════════════════════════════════════════════════════════════
IKI HAL — GELISTIRICI vs CI (yanlis-pozitif butcesi)
═══════════════════════════════════════════════════════════════════════════════
Kablolama `core.hooksPath`'te yasar; `.git/` COMMIT EDILMEZ -> CI checkout'unda
kablolama ASLA KURULU DEGILDIR. Eksen K'yi CI'da kirmizi yakmak her yayini
durdururdu; sessizce yesil saymak ise fail-open'i geri getirirdi. Ikisi de yanlis:

  * VARSAYILAN (gelistirici/yerel): eksen K OLCULUR. Kablolama kurulu degilse
    KIRMIZI + "python3 tools/kanca-kur.py" tarifi. Gecis durustlugu budur —
    kurulum betigi kosturulmadikca koruma kosmaz ve bu GORUNUR olur.
  * `--ci`: eksen K OLCULEMEDI olarak ILAN EDILIR (sessizce atlanmaz, raporda
    ⚪ satiri olarak GORUNUR) ve cikis kodunu ETKILEMEZ. CI'da olculen sey
    IZLENEN KAYNAGIN kendisidir: govdeler fail-closed mi, cagrilar duruyor mu,
    dosyalar git INDEKSINDE 100755 mi (x-biti indekse yazilmazsa taze klonda
    git kancalari SESSIZCE atlar — bu eksen yalniz CI'da anlamlidir).

GOVDE KAYNAGI: varsayilan halde ETKIN kanca dizini (fiilen KOSAN kod) yargilanir;
`--ci` halinde izlenen `tools/kancalar`. Kablolama kurulu degilken izlenen
kaynagi yargilamak SAHTE YESIL olurdu (depoda kod fail-closed, makinede kosan
`.git/hooks` fail-open) -> varsayilan hal daima fiilen kosani olcer.

Kullanim:
    python3 tools/kanca-kablolama-nobeti.py            # yerel hukum (rc 0/1)
    python3 tools/kanca-kablolama-nobeti.py --ci       # kaynak hukmu (K = OLCULEMEDI)
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

# tools/kanca-nobeti.py'den ODUNC ALINAN sozlesme. Biri kaybolursa/adi degisirse
# bu nobetci OLCEMEZ -> YESIL SAYMAZ, OLCULEMEDI der (fail-closed).
_NOBET_SOZLESME = ("BEKLENEN", "ana_checkout", "etkin_hookspath", "hooks_dizini",
                   "suzgec_yukle", "cagri_hukmu", "_etkili_satirlar",
                   "_yol_onekini_normalize", "_kosulsuz_exit_indeksi")

# tools/kanca-kur.py'den ODUNC ALINAN sozlesme (izlenen dizin adi TEK KAYNAK).
_KUR_SOZLESME = ("KANCA_DIZINI", "BEKLENEN_KANCALAR")


# ---------------------------------------------------------------------------
# POLITIKA — her (kanca, arac) cifti icin: BLOKLAMALI MI?
# Cift kumesi tools/kanca-nobeti.py :: BEKLENEN ile TAM ESIT olmak ZORUNDADIR.
# ---------------------------------------------------------------------------
# FAIL-CLOSED: arac sifir-disi donerse islem DURMALI ve GEREKCE GORUNMELI.
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

# BEYAN EDILMIS FAIL-OPEN: bunlar HIJYEN/SENKRON'dur, YAYIN KAPISI DEGIL.
# Patlamalari islemi DURDURMAMALIDIR; `|| true` / cikti yutma burada MESRUDUR
# ve bu nobetci onlara DOKUNMAZ.
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

# ---------------------------------------------------------------------------
# CIKIS KODU / GEREKCE YUTAN KABUK DEYIMLERI
# 🔴 BILINEN SINIR (KACAMAKSIZ): bu KAPALI bir listedir. Amaci "her kacisi
# yakalamak" degil, OLCULEN kacisi ([[|| true]]) ve en yakin akrabalarini
# fail-closed hale getirmektir — DISIPLIN CIHAZI, KAFES DEGIL
# ([[kapi-disiplin-ilkesi]]). Ikinci bir kol EKSEN B'dir (rc FIILEN kontrol
# ediliyor mu): deyimi listeden kacirsa bile rc kontrolu yoksa B kirmizi yanar.
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

# EKSEN B: cagrinin rc'si FIILEN kontrol edilip sifir-disi cikisa baglaniyor mu?
_EXIT_NONZERO_RE = re.compile(r"\bexit\s+([1-9]\d*)\b")
_RC_YAKALA_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=\$\?\s*$")
_IF_DEGIL_RE = re.compile(r"^\s*(if|elif)\s+!\s")
_ILERI_PENCERE = 12          # `if ! ... ; then ... exit 1 ; fi` blogu icin
_RC_PENCERE = 3              # cagriyi izleyen `rc=$?` icin


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
    """[(eksen, hal, mesaj)] — iki tablo TAM ESIT degilse KIRMIZI."""
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
            parca.append("BEKLENEN'de olup politikada OLMAYAN (politikasiz cagri "
                         "sessizce olculmez): %s" % sorted(eksik))
        if fazla:
            parca.append("politikada olup BEKLENEN'de OLMAYAN (bayat giris): %s"
                         % sorted(fazla))
        return [("d) politika/BEKLENEN ayrismasi", KIRMIZI, "; ".join(parca))]
    return [("d) politika/BEKLENEN ayrismasi", YESIL,
             "%d cift TAM ESIT (%d fail-closed, %d beyan edilmis fail-open)"
             % (len(beklenen), len(FAIL_CLOSED), len(FAIL_OPEN)))]


# ---------------------------------------------------------------------------
# EKSEN Y + B — cagri satiri BLOKLUYOR mu?
# ---------------------------------------------------------------------------
def _cagri_satiri(nobet, suzgec, govde, hedef):
    """(indeks, islenmis, ham, etkili) — hedefi ICRA EDEN ilk satir.

    Hukum tools/icra-suzgeci.py'nindir (yorum/`echo`/`--help` mensiyonlari
    cagri SAYILMAZ); burada yalniz kabuk on-islemesi odunc alinir."""
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
      (i)   `python3 X || exit 1`                      -> satirin kendisinde
      (ii)  `if ! python3 X; then ... exit 1 ... fi`   -> ileri pencerede
      (iii) `python3 X` + `rc=$?` + `... exit 1`       -> rc yakalama + pencere
    Hicbiri yoksa cagri kosuyor ama SONUCU KIMSEYI DURDURMUYOR demektir."""
    if _EXIT_NONZERO_RE.search(ham):
        # (i) `... || exit 1` ya da `... ; exit 1` ayni satirda
        return True, None

    # Cagriyi izleyen etkili satirlar (kaynak sirasina gore)
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
# GOVDE KAYNAGI
# ---------------------------------------------------------------------------
def govde_dizini(nobet, kur, kok, kaynak_kok, ci):
    """(dizin, hal, tani) — govdelerin okunacagi dizin.

    ci=True  -> CARI AGACTAKI izlenen kaynak (tools/kancalar): CI checkout'unda
                kablolama kurulu olmadigi icin fiilen kosan bir dizin YOKTUR.
    ci=False -> ANA CHECKOUT'un ETKIN kanca dizini: makinede FIILEN kosan kod
                yargilanir. (Izlenen kaynagi yargilamak, kablolama kurulu
                degilken SAHTE YESIL uretirdi: depoda fail-closed, makinede
                `.git/hooks` fail-open.)"""
    if ci:
        yol = os.path.join(kaynak_kok, kur.KANCA_DIZINI)
        if not os.path.isdir(yol):
            return None, OLCULEMEDI, "izlenen kanca dizini YOK: %s" % yol
        return yol, YESIL, None
    deger, _kaynak, tani = nobet.etkin_hookspath(kok)
    if tani:
        return None, OLCULEMEDI, tani
    dizin, hal, hata = nobet.hooks_dizini(kok, deger)
    if hal == "OLU":
        return None, KIRMIZI, hata
    if hal == "OLCULEMEDI":
        return None, OLCULEMEDI, hata
    return dizin, YESIL, None


# ---------------------------------------------------------------------------
# EKSEN K — KABLOLAMA
# ---------------------------------------------------------------------------
def kablolama_bulgusu(nobet, kur, kok, ci):
    if ci:
        return ("k) kablolama", OLCULEMEDI,
                "CI checkout'unda `core.hooksPath` KURULU DEGILDIR (`.git/` "
                "commit edilmez) -> bu eksen CI'da OLCULEMEZ ve cikis kodunu "
                "ETKILEMEZ. Yerelde: python3 tools/kanca-kablolama-nobeti.py")
    try:
        deger, kaynak, tani = nobet.etkin_hookspath(kok)
    except Exception as e:
        return ("k) kablolama", OLCULEMEDI, "etkin deger okunamadi (%s)" % e)
    if tani:
        return ("k) kablolama", OLCULEMEDI, tani)
    beklenen = os.path.join(kok, kur.KANCA_DIZINI)
    if deger is None:
        return ("k) kablolama", KIRMIZI,
                "core.hooksPath AYARLI DEGIL -> git hala `.git/hooks`u kosar; "
                "IZLENEN fail-closed kancalar DEVREDE DEGIL. Kur: "
                "python3 tools/kanca-kur.py")
    ham = deger.strip()
    cozulen = ham if os.path.isabs(ham) else os.path.normpath(os.path.join(kok, ham))
    if os.path.normpath(cozulen) != os.path.normpath(beklenen):
        return ("k) kablolama", KIRMIZI,
                "core.hooksPath IZLENEN dizini gostermiyor: %r -> %s (beklenen %s) "
                "[kaynak: %s]" % (ham, cozulen, beklenen, kaynak or "?"))
    return ("k) kablolama", YESIL,
            "core.hooksPath = %r -> %s [kaynak: %s]" % (ham, cozulen, kaynak or "?"))


# ---------------------------------------------------------------------------
# EKSEN M — GIT INDEKSINDE x-BITI (yalniz CI'da anlamli)
# ---------------------------------------------------------------------------
def indeks_modu_bulgulari(kur, kok):
    """Izlenen kancalar git INDEKSINDE 100755 mi?

    🔴 NEDEN: x-biti CALISMA AGACINDA dogru olsa bile INDEKSTE 100644 ise TAZE
    BIR KLONDA kancalar x-bitsiz iner ve git onlari SESSIZCE atlar. Bu eksen
    ancak izlenen indekste olculebilir ve ag gerektirmez -> CI'da anlamlidir."""
    try:
        p = subprocess.run(["git", "-C", kok, "ls-files", "-s", kur.KANCA_DIZINI],
                           capture_output=True, text=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return [("m) indeks modu", OLCULEMEDI, "git ls-files kosturulamadi: %s" % e)]
    if p.returncode != 0:
        return [("m) indeks modu", OLCULEMEDI,
                 "git ls-files rc=%d: %s" % (p.returncode, p.stderr.strip()[:120]))]
    modlar = {}
    for satir in p.stdout.splitlines():
        parcalar = satir.split(None, 3)
        if len(parcalar) < 4:
            continue
        modlar[os.path.basename(parcalar[3].strip())] = parcalar[0]
    if not modlar:
        return [("m) indeks modu", KIRMIZI,
                 "%s indekste HIC izlenmiyor -> taze klonda kanca INMEZ, "
                 "kablolama bos dizini gosterir" % kur.KANCA_DIZINI)]
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
# DENETIM
# ---------------------------------------------------------------------------
def denetle(kok, ci=False, kaynak_kok=None):
    """[(eksen, hal, mesaj)] — tum eksenlerin hukmu (fail-closed).

    IKI KOK, IKI SORU (karistirmak sahte hukum uretir):
      * `kok`        = ANA CHECKOUT. Kablolama (eksen K) ORADA yasar ve yerel
        halde FIILEN KOSAN kanca dizini de ondan cozulur.
      * `kaynak_kok` = CARI AGAC. Izlenen kaynagin (eksen M, ve `--ci` halinde
        govdeler) yargilandigi yer. Bir worktree'de calisan muhendis KENDI
        dalindaki kancalari degistirir; onlari ana checkout'ta aramak yanlis
        KIRMIZI uretirdi. Verilmezse `kok` kullanilir."""
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
    bulgular.append(kablolama_bulgusu(nobet, kur, kok, ci))
    bulgular.extend(indeks_modu_bulgulari(kur, kaynak_kok))

    dizin, hal, tani = govde_dizini(nobet, kur, kok, kaynak_kok, ci)
    if dizin is None:
        bulgular.append(("govde kaynagi", hal, tani))
        for (kanca, arac) in sorted(FAIL_CLOSED):
            bulgular.append(("y) %s -> %s" % (kanca, arac), OLCULEMEDI,
                             "kanca dizini cozulemedi (bkz. govde kaynagi)"))
        return bulgular
    bulgular.append(("govde kaynagi", YESIL, dizin))

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

        bulgular.append((eksen, YESIL, "satir %d fail-closed (rc bloka bagli, "
                                       "gerekce gorunur)" % (indeks + 1)))
    return bulgular


def genel_hal(bulgular):
    """🔴 FAIL-CLOSED: OLCULEMEDI asla YESIL'e YUVARLANMAZ."""
    if any(h == KIRMIZI for _e, h, _m in bulgular):
        return KIRMIZI
    if any(h == OLCULEMEDI for _e, h, _m in bulgular):
        return OLCULEMEDI
    return YESIL


def cikis_kodu(bulgular, ci):
    """Cikis kodu. `--ci` halinde eksen K'nin OLCULEMEDI'si cikisi ETKILEMEZ
    (CI'da kablolama zaten kurulu olamaz — yanlis-pozitif butcesi); DIGER her
    OLCULEMEDI fail-closed'dir."""
    if any(h == KIRMIZI for _e, h, _m in bulgular):
        return 1
    for eksen, hal, _m in bulgular:
        if hal != OLCULEMEDI:
            continue
        if ci and eksen == "k) kablolama":
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
        print("KANCA KABLOLAMA NOBETI — ana=%s kaynak=%s (%s)"
              % (ana_kok, kaynak_kok,
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

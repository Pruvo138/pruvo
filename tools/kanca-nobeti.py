#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/kanca-nobeti.py — ANA CHECKOUT'TA GIT KANCALARI GERCEKTEN ETKIN MI?

🔴 NEDEN VAR (31 Tem / 1 Agu OLCULEN OLAY): ana checkout'un `.git/config`'ine
`core.hooksPath = /dev/null` sizmisti (mtime 00:39). Sonuc: ana agacta HICBIR git
kancasi kosmadi —
  * pre-commit urun GUARD'i + mukerrer kontrolu + mimar kod-kilidi,
  * pre-push YEDEK blogu + posta kutusu ARSIVLEYICISI,
  * ve en pahalisi pre-push D1 SENKRONU (Ege urunleri D1'DEN okur; senkron kosmazsa
    site yeni urunu gosterir, EGE GOREMEZ = sessiz satis kaybi; bu sinifta 367
    urunluk kayip zaten olculdu).
Olay SESSIZDI: hicbir kapi kirmizi yakmadi, tek belirti "posta kutusu budanmamis"
gibi DOLAYLI izlerdi. Sessiz-hata sinifinin tanimi budur -> nobetci sart.

🔴 NEDEN CI YETMEZ: CI checkout'u AYRI bir makinede/klonda yapilir ve ANA
CHECKOUT'un `.git/config`'ini GORMEZ (`.git/` zaten commit'lenmez). Bu eksen
YALNIZ YERELDE olculebilir. Bu yuzden nobetci iki YEREL yoldan atesler:
  1. `tools/durum.py` -> "8) GIT KANCALARI" (mimarlarin rutin panosu);
  2. `tools/yedek-hook-kur.py` -> kurulum/geri-yukleme BITTIKTEN sonra dogrular
     (kur -> DOGRULA halkasi kapanir; "kurdum sandim" hali kirmizi yanar).
CI'ya baglanan sey bu nobetcinin KENDI KABUL TESTIDIR (tools/kanca-nobeti-test.py),
cunku onun fikstürleri SENTETIK depolardir ve her makinede aynidir.

OLCULEN EKSENLER (hepsi FAIL-CLOSED — olculemeyen sey YESIL DEGILDIR):
  (a) core.hooksPath: /dev/null · bos · var olmayan/dizin-olmayan yol  -> KIRMIZI.
      ETKIN deger okunur (`git -C <ana> config --get`), yalniz `.git/config`
      GREP'LENMEZ: olculdu (DENEY 4) ki `git config --worktree` ANA checkout'ta
      kosunca deger `.git/config.worktree`'ye yazilir, `.git/config` TERTEMIZ
      kalir ve ana checkout yine de OLUDUR. Grep'e dayanan nobetci bunu KACIRIR.
  (b) beklenen kancalar (pre-commit, pre-push) MEVCUT + CALISTIRILABILIR + BOS DEGIL.
      (git bos ya da x-bitsiz kancayi sessizce atlar -> "dosya duruyor" yetmez.)
  (c) kanca GOVDESI beklenen cagrilari GERCEKTEN icra ediyor mu. 🔴 Bu depoda
      [[nobetci-cagri-satiri-nobetsiz]] diye bilinen tuzak vardir: duz `in`
      aramasi, YORUMA alinmis ya da `echo` ile MENSIYONA cevrilmis bir cagriyi
      "duruyor" sayar. O yuzden hukum tools/icra-suzgeci.py'ye (TEK KAYNAK,
      shlex tabanli) devredilir; bu dosya yalniz KABUK ON-ISLEMEsini sahiplenir
      (degisken cozumu + `$(...)` acilimi + kabuk anahtar kelimeleri).
  (d) OLCUM YAPILAMIYORSA (git yok, config okunamiyor, suzgec yuklenemiyor,
      hooks dizini okunamiyor) hukum OLCULEMEDI'dir ve cikis KODU 1'dir.
  (e) GOVDE NOTRLESTIRME: beklenen cagridan ONCE, girintisiz (ust duzey) ve
      KOSULSUZ bir `exit` varsa cagri satiri "duruyor" ama HIC KOSMAZ -> KIRMIZI.
      (Tum cagri satirlari yerinde dururken kancayi olduren en ucuz mutant budur.)

🔴 IZOLE WORKTREE MESRUDUR — YANLIS-POZITIF URETILMEZ: Claude Code'un izole
worktree'si kendi `config.worktree`'sinde `core.hooksPath = /dev/null` TASIR ve
bu DOGRUDUR (izole agacta ana deponun kancalari kosmamalidir). Nobetci nerede
kosarsa kossun ONCE ANA CHECKOUT'u bulur (`--git-common-dir`'in dizini) ve
YALNIZ onu yargilar; cari worktree'nin override'i hukme GIRMEZ. Bu, kabul
testinde VAKA 6 olarak KOSARAK kanitlanir.

KOK NEDEN (sentetik depolarda GERCEK git ile olculdu, tools/kanca-nobeti-test.py):
  * `git config --worktree ...` extensions.worktreeConfig KAPALIYKEN rc=128 verir.
  * Bir izolasyon araci bu hatadan sonra BAYRAKSIZ `git config core.hooksPath
    /dev/null`'a duserse deger PAYLASILAN `.git/config`'e yazilir (rc=0, UYARI YOK)
    ve ANA CHECKOUT + TUM worktree'ler ayni anda olur. Olculen olay tam budur.
  * Onarim deponun DISINDADIR (izolasyonu kuran harness reponun kodu degildir) ->
    burada yapilabilecek sey TESPIT + GORUNURLUK'tur. Istege bagli `--onar`
    YALNIZ paylasilan config'teki oldurucu degeri kaldirir (varsayilan KAPALI:
    bir nobetci kendiliginden config yazmaz).

Kullanim:
    python3 tools/kanca-nobeti.py                 # ANA checkout'u yargila (rc 0/1)
    python3 tools/kanca-nobeti.py --sessiz        # yalniz SONUC satiri
    python3 tools/kanca-nobeti.py --depo <yol>    # baska bir checkout'u yargila (test/tani)
    python3 tools/kanca-nobeti.py --onar          # paylasilan config'teki oldurucu
                                                  # core.hooksPath'i KALDIR (opt-in)
"""
import os
import re
import shlex
import stat
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))

YESIL = "YESIL"
KIRMIZI = "KIRMIZI"
OLCULEMEDI = "OLCULEMEDI"

# ---- BEKLENEN KANCALAR + ICLERINDE FIILEN KOSMASI GEREKEN ARACLAR -----------
# Bir giris eklemek/cikarmak = kapinin kapsamini degistirmek. Gerekce ZORUNLU:
# gerekcesiz giris hem bu dosyanin okurunu hem kabul testini yaniltir.
BEKLENEN = (
    ("pre-commit", (
        ("tools/urunler-guard.py",
         "urun verisi self-healing guard (izinsiz urunler.json degisimi HEAD'e geri alinir)"),
        ("tools/mukerrer-kontrol.py",
         "mukerrer id/baslik/kaynak linki commit'i BLOKLAR"),
        ("tools/mimar-commit-kapisi.py",
         "mimar kod-kilidi git backstop (ana repodan onaysiz kaynak/veri commit'i)"),
    )),
    ("pre-push", (
        ("tools/yedekle.py",
         "Drive yedegi (--gerekliyse); kosmazsa yedek SESSIZCE bayatlar"),
        ("tools/kutu-arsivle.py",
         "ortak posta kutusu tavan arsivi; kosmazsa kutu budanmaz"),
        ("tools/d1-sync.py",
         "D1 senkronu — EN PAHALISI: kosmazsa site urunu gosterir, EGE GOREMEZ"),
    )),
    # 1 Agu 2026 eklendi (kurucu: tools/commit-mesaji-hook-kur.py).
    # GEREKCE: depo PUBLIC ve commit MESAJI yazildiktan sonra DEGISTIRILEMEZ —
    # push'tan sonra tek onarim tarihce yeniden yazimi + force-push'tur. Yani bu
    # eksenin butun degeri ONLEMEDIR; kanca sessizce olurse koruma SIFIRLANIR ve
    # hicbir yerde alarm calmaz (olculen olay: 5 commit mesajinda tedarikci/satici
    # kimligi public'e cikti, icerik ekseninde vurus 0'di).
    ("commit-msg", (
        ("tools/commit-mesaji-kapisi.py",
         "commit mesajinda tedarikci/satici kimligi -> COMMIT DURUR (fail-closed); "
         "mesaj ekseninin TEK onleyici koludur, CI kolu yalniz gorunurluktur"),
    )),
)

# `$(...)` / backtick ACILIMI ve degisken cozumu icin:
ATAMA_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
DEGISKEN_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
# Komut konumundaki KABUK ANAHTAR KELIMELERI: `if ! python3 x.py` gercek bir
# cagridir ama suzgec segmentin BASINDAKI komuta bakar -> `if`/`!` soyulmazsa
# cagri GORUNMEZ olur (sahte YESIL degil, sahte KIRMIZI; yine de yanlistir).
# ⚠️ `^\s*` SART: gercek pre-push'ta cagri BLOK ICINDE ve GIRINTILIDIR
#    ("  if ! python3 ... yedekle.py"); girintiye izin vermeyen ilk surum bu
#    MESRU satiri kacirip sahte KIRMIZI yakti (kosarak olculdu).
ANAHTAR_RE = re.compile(
    r"(^\s*|[;&|(]\s*)((?:(?:if|elif|while|until|then|do|else|!)\s+)+)")
# Girintisiz + KOSULSUZ `exit` (govde notrlestirme ekseni). `... && exit 0` ya da
# `... || exit 0` KOSULLUDUR ve bu desene UYMAZ (satirin TAMAMI `exit` olmali).
KOSULSUZ_EXIT_RE = re.compile(r"^exit(?:\s+\d+)?\s*$")

_SUZGEC_SOZLESME = ("anlamli_cagri", "birlestir_devam", "EVET", "HAYIR", "OLCULEMEDI")


def suzgec_yukle():
    """tools/icra-suzgeci.py'yi MODUL olarak yukle — FAIL-CLOSED.

    Suzgec yoksa/sozlesmesi degismisse bu kapi `--help` / `echo` / yorum sinifi
    sessiz kacislari GOREMEZ; o halde YESIL SAYMAZ, RuntimeError yukseltir."""
    import importlib.util
    yol = os.path.join(TOOLS, "icra-suzgeci.py")
    if not os.path.exists(yol):
        raise RuntimeError(
            "tools/icra-suzgeci.py YOK -> 'gercek icra mi' suzgeci yuklenemedi; "
            "kanca govdesi ekseni OLCULEMEZ (fail-closed).")
    spec = importlib.util.spec_from_file_location("pruvo_icra_suzgeci_kanca", yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_icra_suzgeci_kanca"] = mod
    spec.loader.exec_module(mod)
    for ad in _SUZGEC_SOZLESME:
        if not hasattr(mod, ad):
            raise RuntimeError("tools/icra-suzgeci.py'de %s YOK -> suzgec sozlesmesi "
                               "degismis (fail-closed)" % ad)
    return mod


# =========================== ANA CHECKOUT'U BUL ==============================

def _git(cwd, *args):
    """(rc, stdout, stderr) — git yoksa rc=127 ve tani (fail-closed cagirici)."""
    try:
        p = subprocess.run(["git", "-C", cwd] + list(args),
                           capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return 127, "", "git binary'si PATH'te YOK"
    except subprocess.TimeoutExpired:
        return 124, "", "git 30 sn icinde yanit vermedi"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def ana_checkout(baslangic=None):
    """(yol, tani) — <baslangic> nerede olursa olsun ANA checkout'un koku.

    `--git-common-dir` linked worktree'de de ANA deponun `.git`'ini gosterir;
    ana checkout onun dizinidir. Bare depoda / git disi dizinde (None, tani)."""
    baslangic = baslangic or os.path.dirname(TOOLS)
    rc, cikti, hata = _git(baslangic, "rev-parse", "--path-format=absolute",
                           "--git-common-dir")
    if rc != 0 or not cikti:
        return None, "ana checkout bulunamadi (git rev-parse rc=%d): %s" % (rc, hata or "?")
    ortak = cikti
    if os.path.basename(ortak) != ".git":
        return None, "ortak git dizini '.git' ile bitmiyor (bare depo?): %s" % ortak
    return os.path.dirname(ortak), None


# =========================== EKSEN (a): hooksPath ============================

def etkin_hookspath(kok):
    """(deger, kaynak, tani) — ANA checkout icin ETKIN core.hooksPath.

    deger None + tani None  -> ayar YOK (git varsayilani <ortak>/hooks) = SAGLIKLI.
    ⚠️ `.git/config` GREP'LENMEZ: system/global/`.git/config`/`.git/config.worktree`
    katmanlarinin BILESKESI okunur (DENEY 4: `--worktree` ile ana checkout'u
    olduren deger `.git/config`'de HIC gorunmez)."""
    rc, cikti, hata = _git(kok, "config", "--show-origin", "--get", "core.hooksPath")
    if rc == 1 and not cikti:
        return None, None, None                      # ayar yok -> varsayilan
    if rc != 0:
        return None, None, "core.hooksPath okunamadi (rc=%d): %s" % (rc, hata or "?")
    if "\t" in cikti:
        kaynak, _sep, deger = cikti.partition("\t")
    else:
        kaynak, deger = "?", cikti
    return deger, kaynak, None


def hooks_dizini(kok, deger):
    """(dizin, hal, tani) — hukum verilecek kanca dizini.

    hal: "varsayilan" | "ozel" | "OLU" (hal OLU ise dizin None ve tani doludur)."""
    if deger is None:
        rc, cikti, hata = _git(kok, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if rc != 0 or not cikti:
            return None, "OLCULEMEDI", "ortak git dizini bulunamadi: %s" % (hata or "?")
        return os.path.join(cikti, "hooks"), "varsayilan", None

    ham = deger.strip()
    if not ham:
        return None, "OLU", ("core.hooksPath BOS -> git hicbir kanca dizini bulamaz; "
                             "TUM kancalar sessizce kosmaz")
    if os.path.normpath(ham) == os.path.normpath("/dev/null"):
        return None, "OLU", ("core.hooksPath = /dev/null -> TUM kancalar sessizce "
                             "DEVRE DISI (olculen olayin ta kendisi)")
    yol = ham if os.path.isabs(ham) else os.path.normpath(os.path.join(kok, ham))
    if not os.path.exists(yol):
        return None, "OLU", ("core.hooksPath var olmayan yolu gosteriyor: %s -> "
                             "hicbir kanca kosmaz" % yol)
    if not os.path.isdir(yol):
        return None, "OLU", ("core.hooksPath bir DIZIN degil: %s -> hicbir kanca "
                             "kosmaz" % yol)
    return yol, "ozel", None


# ===================== EKSEN (c): GOVDE GERCEKTEN CAGIRIYOR MU ================

def _komut_ikamesini_ac(metin):
    """`$(...)` ve backtick'leri AYIRACA cevirerek ICINDEKI komutu gorunur kilar.

    NEDEN: pre-push'ta kutu arsivleyicisi
        pruvo_kutu_cikti=$(python3 "$pruvo_kok/tools/kutu-arsivle.py" 2>&1)
    biciminde cagrilir. `$(...)`'i tek bir yer-tutucuya indirgeyen naif bir
    on-isleme bu GERCEK cagriyi YOK EDER (sahte KIRMIZI). Burada `$(` ve eslesen
    `)` birer `;` ayiracina cevrilir; icerideki komut normal bir segment olur."""
    cikti = []
    derinlik = 0
    i = 0
    while i < len(metin):
        if metin.startswith("$(", i):
            cikti.append(" ; ")
            derinlik += 1
            i += 2
            continue
        if metin[i] == ")" and derinlik:
            cikti.append(" ; ")
            derinlik -= 1
            i += 1
            continue
        if metin[i] == "`":
            cikti.append(" ; ")
            i += 1
            continue
        cikti.append(metin[i])
        i += 1
    return "".join(cikti)


def _ikame_yer_tutucu(metin):
    """Degisken DEGERI icin: `$(...)`/backtick -> tek bosluksuz yer tutucu.

    Deger tarafinda icerideki komut ILGISIZDIR; onemli olan `root=$(git
    rev-parse --show-toplevel)` gibi bir KOK ONEKININ tek sozcuk kalmasidir
    (aksi halde deger bosluk icerir ve yol on-eki normalize edilemez)."""
    metin = re.sub(r"\$\([^()]*\)", "PRUVOIKAME", metin)
    metin = re.sub(r"`[^`]*`", "PRUVOIKAME", metin)
    return metin


def _atama_haritasi(satirlar):
    """Kabuk degisken atamalarini {ad: deger} olarak topla (sirali, ozyinelemeli)."""
    harita = {}
    for ham in satirlar:
        if ham.strip().startswith("#"):
            continue
        m = ATAMA_RE.match(ham)
        if not m:
            continue
        ad, deger = m.group(1), _ikame_yer_tutucu(m.group(2))
        try:
            jetonlar = shlex.split(deger, posix=True)
        except ValueError:
            jetonlar = deger.split()
        harita[ad] = _degisken_coz(jetonlar[0], harita) if jetonlar else ""
    return harita


def _degisken_coz(metin, harita, tur=6):
    """`$ad` / `${ad}` genislet; bilinmeyen degisken OLDUGU GIBI birakilir."""
    for _ in range(tur):
        yeni = DEGISKEN_RE.sub(
            lambda m: harita.get(m.group(1) or m.group(2), m.group(0)), metin)
        if yeni == metin:
            return yeni
        metin = yeni
    return metin


def _anahtar_kelimeleri_soy(satir):
    """Komut konumundaki `if`/`!`/`while`/`then` ... anahtar kelimelerini soy."""
    for _ in range(6):
        yeni = ANAHTAR_RE.sub(lambda m: m.group(1), satir)
        if yeni == satir:
            return yeni
        satir = yeni
    return satir


def _yol_onekini_normalize(satir, hedef):
    """`<herhangi-bir-onek>/tools/x.py` -> `tools/x.py` (repo-goreli bicime indir)."""
    desen = re.compile(r"(?:[^\s'\";|&<>()]*/)?" + re.escape(hedef))
    return desen.sub(hedef, satir)


def _etkili_satirlar(govde, suzgec):
    """(indeks, islenmis_satir, ham_satir) — yorumlar elenmis, on-islenmis satirlar."""
    ham_satirlar = suzgec.birlestir_devam(govde)
    harita = _atama_haritasi(ham_satirlar)
    sonuc = []
    for i, ham in enumerate(ham_satirlar):
        if not ham.strip() or ham.strip().startswith("#"):
            continue
        s = _komut_ikamesini_ac(ham)
        s = _degisken_coz(s, harita)
        s = _anahtar_kelimeleri_soy(s)
        sonuc.append((i, s, ham))
    return sonuc


def _kosulsuz_exit_indeksi(etkili):
    """Girintisiz + kosulsuz ilk `exit` satirinin indeksi (yoksa None).

    Girintili `exit` bir blok icindedir (kosulludur); `... || exit 0` da
    kosulludur -> ikisi de govdeyi NOTRLESTIRMEZ."""
    for i, _islenmis, ham in etkili:
        if ham[:1].isspace():
            continue
        if KOSULSUZ_EXIT_RE.match(ham.strip()):
            return i
    return None


def cagri_hukmu(govde, hedef, suzgec):
    """(hukum, tani) — <govde> <hedef>'i GERCEKTEN icra ediyor mu?

    YESIL / KIRMIZI / OLCULEMEDI. Hukum tools/icra-suzgeci.py'nindir; burada
    yalniz KABUK ON-ISLEMESI (degisken, `$(...)`, anahtar kelime, yol oneki)
    yapilir."""
    try:
        etkili = _etkili_satirlar(govde, suzgec)
    except Exception as e:                                # pragma: no cover
        return OLCULEMEDI, "govde on-islenemedi (%s: %s)" % (type(e).__name__, e)

    exit_i = _kosulsuz_exit_indeksi(etkili)
    bulgu = None
    for i, islenmis, _ham in etkili:
        satir = _yol_onekini_normalize(islenmis, hedef)
        hukum, sebep, _arg = suzgec.anlamli_cagri(satir, hedef)
        if hukum == suzgec.EVET:
            if exit_i is not None and i > exit_i:
                return KIRMIZI, ("cagri var (satir %d) ama ONCESINDE girintisiz "
                                 "KOSULSUZ `exit` var (satir %d) -> govde "
                                 "NOTRLESTIRILMIS, cagri HIC kosmaz"
                                 % (i + 1, exit_i + 1))
            return YESIL, None
        if hukum == suzgec.OLCULEMEDI and bulgu is None:
            bulgu = (OLCULEMEDI, "satir %d jetonlanamadi: %s" % (i + 1, sebep))
        elif hukum == suzgec.HAYIR and bulgu is None:
            bulgu = (KIRMIZI, "satir %d cagri GIBI gorunuyor ama icra DEGIL: %s"
                              % (i + 1, sebep))
    if bulgu:
        return bulgu
    return KIRMIZI, ("govdede %s'i ICRA EDEN satir YOK (silinmis ya da yoruma "
                     "alinmis olabilir)" % hedef)


# ================================ DENETIM ====================================

def denetle(kok, suzgec=None):
    """[(eksen, hal, mesaj)] — ANA checkout icin tum eksenlerin hukmu."""
    bulgular = []
    if suzgec is None:
        try:
            suzgec = suzgec_yukle()
        except Exception as e:
            return [("suzgec", OLCULEMEDI, str(e))]

    deger, kaynak, tani = etkin_hookspath(kok)
    if tani:
        return [("a) core.hooksPath", OLCULEMEDI, tani)]

    dizin, hal, hata = hooks_dizini(kok, deger)
    if hal == "OLU":
        bulgular.append(("a) core.hooksPath", KIRMIZI,
                         "%s   [kaynak: %s]" % (hata, kaynak or "?")))
        # Kanca dizini yoksa (b)/(c) OLCULEMEZ — yesil sayilmaz, ilan edilir.
        for ad, _araclar in BEKLENEN:
            bulgular.append(("b) %s" % ad, OLCULEMEDI,
                             "hooks dizini cozulemedi (bkz. eksen a)"))
        return bulgular
    if hal == "OLCULEMEDI":
        return [("a) core.hooksPath", OLCULEMEDI, hata)]

    if deger is None:
        bulgular.append(("a) core.hooksPath", YESIL,
                         "ayar YOK -> git varsayilani: %s" % dizin))
    else:
        bulgular.append(("a) core.hooksPath", YESIL,
                         "ozel dizin GECERLI: %s   [kaynak: %s]" % (dizin, kaynak or "?")))

    for ad, araclar in BEKLENEN:
        yol = os.path.join(dizin, ad)
        if not os.path.exists(yol):
            bulgular.append(("b) %s" % ad, KIRMIZI,
                             "kanca YOK: %s -> hic kosmaz" % yol))
            continue
        try:
            st = os.stat(yol)
            govde = open(yol, encoding="utf-8", errors="replace").read()
        except OSError as e:
            bulgular.append(("b) %s" % ad, OLCULEMEDI, "okunamadi: %s" % e))
            continue
        if not (st.st_mode & stat.S_IXUSR):
            bulgular.append(("b) %s" % ad, KIRMIZI,
                             "calistirilabilir DEGIL (x-biti yok) -> git sessizce atlar"))
            continue
        if not govde.strip():
            bulgular.append(("b) %s" % ad, KIRMIZI,
                             "kanca BOS -> hicbir kapi kosmaz"))
            continue
        bulgular.append(("b) %s" % ad, YESIL,
                         "mevcut + calistirilabilir (%d bayt)" % st.st_size))
        for hedef, gerekce in araclar:
            hukum, tani2 = cagri_hukmu(govde, hedef, suzgec)
            if hukum == YESIL:
                bulgular.append(("c) %s -> %s" % (ad, hedef), YESIL, gerekce))
            else:
                bulgular.append(("c) %s -> %s" % (ad, hedef), hukum,
                                 "%s   [kaybolan koruma: %s]" % (tani2, gerekce)))
    return bulgular


def genel_hal(bulgular):
    if any(h == KIRMIZI for _e, h, _m in bulgular):
        return KIRMIZI
    if any(h == OLCULEMEDI for _e, h, _m in bulgular):
        return OLCULEMEDI
    return YESIL


ISARET = {YESIL: "✅", KIRMIZI: "🔴", OLCULEMEDI: "⚪"}


def satirlar(kok=None, onek="  "):
    """tools/durum.py icin basilabilir satirlar (pano ASLA patlamaz)."""
    try:
        if kok is None:
            kok, tani = ana_checkout()
            if kok is None:
                return ["%s⚪ ÖLÇÜLEMEDİ: %s" % (onek, tani)]
        bulgular = denetle(kok)
    except Exception as e:                                # pragma: no cover
        return ["%s⚪ ÖLÇÜLEMEDİ: kanca nobeti kosturulamadi (%s)"
                % (onek, type(e).__name__)]
    hal = genel_hal(bulgular)
    cikti = ["%sana checkout: %s" % (onek, kok)]
    if hal == YESIL:
        cikti.append("%s✅ kancalar ETKIN — %d eksen yesil" % (onek, len(bulgular)))
        return cikti
    for eksen, h, mesaj in bulgular:
        if h == YESIL:
            continue
        cikti.append("%s%s %s: %s" % (onek, ISARET[h], eksen, mesaj))
    cikti.append("%s   ayrinti/onarim: python3 tools/kanca-nobeti.py" % onek)
    if hal == OLCULEMEDI:
        cikti.append("%s   (ÖLÇÜLEMEDİ 'sorun yok' DEMEK DEGILDIR)" % onek)
    return cikti


# ================================ ONARIM =====================================

def onar(kok):
    """(yapildi, mesaj) — PAYLASILAN config'teki OLDURUCU core.hooksPath'i kaldir.

    🔴 OPT-IN: bir nobetci kendiliginden config YAZMAZ. Yalnizca deger fiilen
    oldurucuysa (/dev/null · bos · var olmayan yol) ve kaynak ana checkout'un
    config'i / config.worktree'siyse kaldirilir; MESRU ozel bir hooksPath'e
    ya da global/system katmanina DOKUNULMAZ."""
    deger, kaynak, tani = etkin_hookspath(kok)
    if tani:
        return False, "OLCULEMEDI: " + tani
    if deger is None:
        return False, "core.hooksPath zaten YOK — yapacak bir sey yok"
    _d, hal, _hata = hooks_dizini(kok, deger)
    if hal != "OLU":
        return False, "core.hooksPath oldurucu DEGIL (%s) — DOKUNULMADI" % deger
    kaynak_dosya = (kaynak or "").replace("file:", "")
    if os.path.basename(kaynak_dosya) not in ("config", "config.worktree"):
        return False, ("deger depo-disi bir katmandan geliyor (%s) — nobetci "
                       "global/system config'e DOKUNMAZ; elle kaldir" % kaynak)
    kapsam = "--worktree" if kaynak_dosya.endswith("config.worktree") else "--local"
    rc, _o, e = _git(kok, "config", kapsam, "--unset", "core.hooksPath")
    if rc != 0:
        return False, "unset basarisiz (rc=%d): %s" % (rc, e)
    return True, ("core.hooksPath KALDIRILDI (%s, kaynak %s) — kancalar yeniden etkin"
                  % (kapsam, kaynak_dosya))


# ================================= MAIN ======================================

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
    sessiz = "--sessiz" in argv
    onarim = "--onar" in argv
    gecerli = ("--sessiz", "--onar")
    bilinmeyen = [a for a in argv if a not in gecerli]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    if kok is None:
        kok, tani = ana_checkout()
        if kok is None:
            print("⚪ OLCULEMEDI: %s" % tani)
            print("SONUC: OLCULEMEDI (fail-closed -> cikis 1)")
            return 1
    kok = os.path.abspath(kok)

    if onarim:
        yapildi, mesaj = onar(kok)
        print("ONARIM: %s" % mesaj)
        if not yapildi and mesaj.startswith("OLCULEMEDI"):
            return 1

    try:
        bulgular = denetle(kok)
    except Exception as e:
        print("⚪ OLCULEMEDI: denetim patladi (%s: %s)" % (type(e).__name__, e))
        print("SONUC: OLCULEMEDI (fail-closed -> cikis 1)")
        return 1

    hal = genel_hal(bulgular)
    if not sessiz:
        print("KANCA NOBETI — ana checkout: %s" % kok)
        for eksen, h, mesaj in bulgular:
            print("  %s %-42s %s" % (ISARET[h], eksen, mesaj))
        kirmizi = sum(1 for _e, h, _m in bulgular if h == KIRMIZI)
        olcusuz = sum(1 for _e, h, _m in bulgular if h == OLCULEMEDI)
        print("\n%d eksen: %d yesil, %d kirmizi, %d olculemedi"
              % (len(bulgular), len(bulgular) - kirmizi - olcusuz, kirmizi, olcusuz))
    print("SONUC: %s%s" % (hal, "" if hal == YESIL else " (fail-closed -> cikis 1)"))
    return 0 if hal == YESIL else 1


if __name__ == "__main__":
    sys.exit(main())

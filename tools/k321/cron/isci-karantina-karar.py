#!/usr/bin/env python3
# K156 (17 Agu 2026): karantina tetigi motorun KENDI imzasina baglanir.
# Eski tetik: cikti metninde "usage limit|quota exceeded|rate limit|..." aranirdi.
# Bu, motorun kendi arizasini baska motorun ariza metnini RAPORlayan basarili
# turdan ayirt etmiyordu. Yeni tetik uc kosulu da ZORUNLU ister:
#   1) rc != 0 (tur kendisi dustu)
#   2) ciktida satir basindan itibaren CLI olumcul hata bicimine uyan VE
#      ayni satirda kota ifadesi tasiyan bir satir olmali
#      (markdown onekleri "- "/"  > "/"  | "/"  ` "/"  #" YAKALANMAZ)
#   3) motor kapal kumede olmali (regex isci.sh'den ARGUMAN olarak gelir,
#      ikiz tanim yok)
#
# Kullanim:
#   isci-karantina-karar.py [--ev <ev_koku|ev_adi>] <rc> <cikti_dosyasi> <motor>
#                           <karantina_dosyasi> <motor_regex> [--kuru] [--hal <AD>]
# Cikis kodu: 0 = karantina YAZILDI, 10 = yazilmadi (imza yok), 2 = hata.
# Stdout: TEK makine-okunur satir:
#   KARANTINA_KARAR motor=<m> rc=<rc> imza=<var|yok|gecici> yazildi=<evet|hayir|kuru> sebep=<...>

import json
import os
import re
import sys
import tempfile
import time

# --- yardimci regex'ler (tek kaynak) -----------------------------------
FATAL_RE = re.compile(
    r'^[ \t]*(?:Failed to authenticate\.[ \t]*)?'
    r'API Error:[ \t]*(?:[^\n]*?)(401|402|403|429)\b'
)
KOTA_RE = re.compile(
    r'(usage limit|quota exceeded|rate limit|insufficient balance|'
    r'too many requests|rate_limit_error|permission_error)',
    re.IGNORECASE,
)

# 🔴 KOL C (27 Agu 2026, KraL-NobetTuru-27Agu) — OLCUT MESAJI DA OKUR.
# OLCULDU: 27 Agu'da 13 ardisik `motor=claude rc=1` kosumunun TAMAMINDA
# `yazildi=hayir sebep=fatal-satir-yok` basildi. Ekranda duran metin:
#   "Your organization has disabled Claude subscription access for Claude
#    Code . Use an Anthropic API key instead, or ask your admin to enable
#    access"
# Bu metinde ne `API Error: ...401/403` bicimi (FATAL_RE) ne de bir kota
# ifadesi (KOTA_RE) vardir -> tek karantina kaydi yazilmadi ve hat ayni olu
# motoru saatlerce yeniden denedi. "fatal satir yok" TEK EKSEN OLAMAZ.
#
# Bu eksen KALICI ERISIM/YETKI reddini tanir. Kota imzasindan FARKI: kota
# gecicidir, erisim reddi degildir -- ama tek seferlik bir sebeke/CLI
# hatasini karantinaya cevirmemek icin ARDISIK ESIGE baglanir.
ERISIM_RE = re.compile(
    r'(organization has disabled|ask your admin to enable|'
    r'subscription access for claude code|not authorized|unauthorized|'
    r'access denied|forbidden)',
    re.IGNORECASE,
)

# Kac ARDISIK basarisiz kosumdan sonra erisim reddi karantina yazar.
# 1 OLAMAZ: tek seferlik rc!=0 karantina URETMEMELIDIR (yanlis pozitif yasagi).
ERISIM_ARDISIK_ESIGI = 3

# 🔴 KOL D (27 Agu 2026, isci-karantina-durum.py'nin ESLIGI) — Kol C yalniz
# BILINEN imzalari (kota, erisim reddi) tanir. Yarinki hata metni bu
# regex'lerin HICBIRINE uymayabilir ve ayni sessiz-13-ardisik-deneme
# deseni baska bir cikti metniyle TEKRAR eder. Bu esik o kor noktayi
# kapatir: imza NE OLURSA OLSUN, ayni motor ARDISIK bu kadar basarisiz
# olursa karantinaya yazilir -- "genel olarak basarisiz" ekseni. 1
# OLAMAZ (ayni gerekce: tek seferlik rc!=0 yanlis pozitif yasagi).
GENEL_ARDISIK_ESIGI = ERISIM_ARDISIK_ESIGI

# 🔴 K414 (14 Eyl 2026, cip KraL-Tamirci-14Eyl) — KOL D FILO HUKMUDUR, TEK
# EVIN DIZISI FILO HUKMU DEGILDIR.
# OLCULDU (13 Eyl 18:56-19:05Z, isci.log): ArTisT (`pruvo-pazarlama`) ayni
# anda paralel baslattigi uc m3 turunun ucu de `API Error: Response stalled
# mid-stream` ile `rc=1` dustu; sayac motor basina TEK oldugu icin
# `ardisik-basarisiz-imzasiz3` yazildi ve m3 TUM FILODA 6 saat kilitlendi
# (yedek motor yok -> 6 is `KARANTINA_ATLANDI`). Ayni pencerede baska evlerin
# m3 turlari saglikliydi. Iki sinif kusuru vardi, ikisi de SAYIYLA degil
# EKSENLE kapanir (esigi 3->N yukseltmek tekil yamadir, YASAK):
#   (1) EV EKSENI -- Kol D yalniz dizi en az FILO_EV_ESIGI farkli evden
#       geliyorsa yazar. Ev, worktree yolundan SAHIBI evin adina indirgenir
#       (`ev_kanonik`): ayni evin iki worktree'si IKI ev SAYILMAZ.
#       Tek evin uzun dizisi icin ayri kol durur: wa-gozcu 27 Agu vakasi
#       (motoru o an kullanan TEK ev, 13 ardisik dusus) sessiz kalmasin diye
#       TEK_EV_UZUN_DIZI_ESIGI'nde tek ev de yazar. Iki sayi da GENEL esikten
#       TURER; yeni bagimsiz sabit yoktur.
#   (2) SINIF EKSENI -- gecici akis kopmasi (KOL F, asagida) motor arizasi
#       sayilmaz.
FILO_EV_ESIGI = 2
TEK_EV_UZUN_DIZI_ESIGI = 2 * GENEL_ARDISIK_ESIGI

# 🔴 KOL F (14 Eyl 2026, K414) — GECICI AKIS KOPMASI MOTOR ARIZASI DEGILDIR.
# Saglayici/ag tarafinda yarida kalan cevap (stall, 5xx/529, baglanti
# kopmasi) motorun HESABINDAN ya da YETKISINDEN soz etmez. Kural K337'nin
# butce koluyla ayni UC HALLIDIR:
#   - gecici dusus motorun `ardisik` sayacini ARTIRMAZ
#   - SIFIRLAMAZ da (o turda motor sagligi olculmedi; birikmis gercek
#     dususleri silmek [[varlik-beyani-silmeyi-ifade-edemez]] olur)
#   - kendi kovasinda (`__gecici__`) GORUNUR ve kendi, daha yuksek esigini
#     tasir: gercek bir saglayici cokusu BIRDEN FAZLA evde tekrarlar; o zaman
#     yine yazar. Tek evin gecici dizisi (paralel fan-out) ASLA filo hukmu
#     vermez -- gecici kovanin tek-ev kolu yoktur.
# Imza FATAL_RE ile ayni alinti disiplinini tasir: satir basina capalidir,
# markdown onekli rapor alintisi YAKALANMAZ.
GECICI_RE = re.compile(
    r'^[ \t]*API Error:[ \t]*(?:'
    r'Response stalled mid-stream'
    r'|(?:500|502|503|504|529)\b'
    r'|Connection error'
    r'|Request timed out'
    r')',
    re.IGNORECASE,
)
GECICI_KOVASI = "__gecici__"
GECICI_EV_KOVASI = "__gecici_ev__"
EV_KOVASI = "__evler__"
GECICI_ARDISIK_ESIGI = 2 * GENEL_ARDISIK_ESIGI

# 🔴 KOL E (28 Agu 2026, K337 — cip KraL-K337Butce-28Agu) — BUTCE TAVANI
# MOTOR ARIZASI DEGILDIR.
# OLCULDU: 28 Agu'da iki tur butce tavaninda kesildi ve IKISI DE bu araca
# sirаdan `rc=1` olarak geldi; `sebep=fatal-satir-yok ardisik=2` basildi.
# Yani PARA bitmesi MOTOR sagligina yazildi ve birincil motor 3'luk esigin
# bir adim onune geldi. Ucuncu ardisik uzun is motoru 6 saat yakacakti.
#
# Kural IKI YONLUDUR ve arasinda bir UCUNCU HAL vardir:
#   - butce kesintisi motorun `ardisik` sayacini ARTIRMAZ (ariza degil)
#   - ama SIFIRLAMAZ da: o turda motor sagligi HIC OLCULMEDI; sifir
#     yazmak birikmis GERCEK dususleri siler
#     ([[varlik-beyani-silmeyi-ifade-edemez]]).
#   - kesinti kendi kovasinda (`__butce__`) GORUNUR; sessizce yutulmaz.
# 🔴 Kova YALNIZ hal GERCEKTEN BUTCE_TAVANI iken acilir. Hal bos/taninmaz
# ise eski davranis BIREBIR durur -- gevsetme YOK
# ([[emir-ariza-kovasina-duserse-hat-kendi-kendine-kirmizi-yanar]]).
BUTCE_HALI = "BUTCE_TAVANI"
EKSIK_HALI = "EKSIK"
EKSIK_KOVASI = "__eksik__"
BUTCE_KOVASI = "__butce__"

KULLANIM = (
    "Kullanim: isci-karantina-karar.py [--ev <ev_koku|ev_adi>] <rc> "
    "<cikti_dosyasi> <motor> <karantina_dosyasi> <motor_regex> [--kuru] "
    "[--hal <AD>]\n"
)


def ev_kanonik(deger):
    """Ev koku/adi -> SAHIBI evin adi. Bilinmiyorsa "?".

    Worktree yolu (`<ev>/.claude/worktrees/<ad>` ya da `.git` dosyasi
    `gitdir: <ev>/.git/worktrees/<ad>` olan dizin) sahibi evin adina
    indirgenir: ayni evin paralel worktree'leri FILO hukmunde TEK ev sayilir.
    Yol degil duz ad verilirse aynen doner. Alt surec (git) CAGRILMAZ.
    """
    if not deger or not deger.strip():
        return "?"
    deger = deger.strip()
    if "/" not in deger:
        return deger
    yol = os.path.abspath(os.path.expanduser(deger)).rstrip("/")
    return _worktree_sahibi(yol) or os.path.basename(yol) or "?"


def _worktree_sahibi(yol):
    git_dosyasi = os.path.join(yol, ".git")
    if os.path.isfile(git_dosyasi):
        try:
            with open(git_dosyasi, encoding="utf-8", errors="replace") as f:
                ilk = f.readline().strip()
        except OSError:
            ilk = ""
        if ilk.startswith("gitdir:"):
            hedef = ilk[len("gitdir:"):].strip()
            if "/.git/worktrees/" in hedef:
                return os.path.basename(hedef.split("/.git/worktrees/", 1)[0].rstrip("/"))
    if "/.claude/worktrees/" in yol + "/":
        return os.path.basename(yol.split("/.claude/worktrees/", 1)[0].rstrip("/"))
    return ""


def butce_oku(karantina_dosyasi, motor):
    """Motorun ardisik BUTCE kesintisi sayisi (motor sayacindan AYRI)."""
    kova = ardisik_oku(karantina_dosyasi).get(BUTCE_KOVASI)
    if not isinstance(kova, dict):
        return 0
    try:
        return int(kova.get(motor) or 0)
    except (TypeError, ValueError):
        return 0


def butce_guncelle(karantina_dosyasi, motor, artir):
    """Butce kovasini gunceller. MOTOR sayacina DOKUNMAZ.

    `artir=False` kovayi sifirlar (tur saglikli bittiginde).
    """
    veri = ardisik_oku(karantina_dosyasi)
    kova = veri.get(BUTCE_KOVASI)
    if not isinstance(kova, dict):
        kova = {}
    try:
        onceki = int(kova.get(motor) or 0)
    except (TypeError, ValueError):
        onceki = 0
    yeni = (onceki + 1) if artir else 0
    kova[motor] = yeni
    veri[BUTCE_KOVASI] = kova
    _sayac_yaz(karantina_dosyasi, veri)
    return yeni


def _sayac_yolu(karantina_dosyasi):
    return karantina_dosyasi + ".ardisik.json"


def ardisik_oku(karantina_dosyasi):
    try:
        with open(_sayac_yolu(karantina_dosyasi), encoding="utf-8") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def _kova_listesi(veri, kova_adi, motor):
    kova = veri.get(kova_adi)
    if not isinstance(kova, dict):
        return []
    liste = kova.get(motor)
    return sorted(set(str(x) for x in liste)) if isinstance(liste, list) else []


def _kova_liste_yaz(veri, kova_adi, motor, liste):
    kova = veri.get(kova_adi)
    if not isinstance(kova, dict):
        kova = {}
    kova[motor] = sorted(set(liste))
    veri[kova_adi] = kova


def evler_oku(karantina_dosyasi, motor):
    """Motorun SUREN imzasiz/erisim dizisine katilan farkli evler."""
    return _kova_listesi(ardisik_oku(karantina_dosyasi), EV_KOVASI, motor)


def gecici_oku(karantina_dosyasi, motor):
    """(sayi, evler) — motorun SUREN gecici akis kopmasi dizisi."""
    veri = ardisik_oku(karantina_dosyasi)
    kova = veri.get(GECICI_KOVASI)
    try:
        sayi = int(kova.get(motor) or 0) if isinstance(kova, dict) else 0
    except (TypeError, ValueError):
        sayi = 0
    return sayi, _kova_listesi(veri, GECICI_EV_KOVASI, motor)


def gecici_guncelle(karantina_dosyasi, motor, ev):
    """Gecici kovayi bir artirir, evi ekler. MOTOR sayacina DOKUNMAZ."""
    veri = ardisik_oku(karantina_dosyasi)
    kova = veri.get(GECICI_KOVASI)
    if not isinstance(kova, dict):
        kova = {}
    try:
        onceki = int(kova.get(motor) or 0)
    except (TypeError, ValueError):
        onceki = 0
    kova[motor] = onceki + 1
    veri[GECICI_KOVASI] = kova
    evler = _kova_listesi(veri, GECICI_EV_KOVASI, motor) + [ev]
    _kova_liste_yaz(veri, GECICI_EV_KOVASI, motor, evler)
    _sayac_yaz(karantina_dosyasi, veri)
    return onceki + 1, sorted(set(evler))


def ardisik_guncelle(karantina_dosyasi, motor, basarisiz, ev=None):
    """Motorun ardisik basarisizlik sayacini atomik gunceller ve YENI degeri doner.

    `basarisiz=False` (rc==0) sayaci SIFIRLAR -- motor iyilesince esik
    kendiliginden duser ([[silme-sayaci-diskten-dogrulanmali]]).
    """
    veri = ardisik_oku(karantina_dosyasi)
    yeni = (int(veri.get(motor) or 0) + 1) if basarisiz else 0
    veri[motor] = yeni
    if basarisiz and ev:
        _kova_liste_yaz(veri, EV_KOVASI, motor,
                        _kova_listesi(veri, EV_KOVASI, motor) + [ev])
    # 🔴 K337: saglikli tur BUTCE kovasini da sifirlar -- iki sayac da
    # ayni "iyilesince duser" disiplinine tabidir.
    if not basarisiz:
        kova = veri.get(BUTCE_KOVASI)
        if isinstance(kova, dict) and kova.get(motor):
            kova[motor] = 0
            veri[BUTCE_KOVASI] = kova
        # 🔴 K414: saglikli tur dizinin EV kumesini ve gecici kovayi da
        # sifirlar -- eski dizinin evi yeni diziye FILO hukmu tasimasin.
        _kova_liste_yaz(veri, EV_KOVASI, motor, [])
        gkova = veri.get(GECICI_KOVASI)
        if isinstance(gkova, dict) and gkova.get(motor):
            gkova[motor] = 0
            veri[GECICI_KOVASI] = gkova
        _kova_liste_yaz(veri, GECICI_EV_KOVASI, motor, [])
    _sayac_yaz(karantina_dosyasi, veri)
    return yeni


def filo_hukmu(ardisik, evler, esik, tek_ev_esigi):
    """Ardisik dizi FILO capinda karantina hukmu uretir mi? (bool)

    `tek_ev_esigi` 0 ise tek ev ASLA yetmez (gecici kova).
    """
    if ardisik >= esik and len(evler) >= FILO_EV_ESIGI:
        return True
    if tek_ev_esigi and ardisik >= tek_ev_esigi:
        return True
    return False


def _sayac_yaz(karantina_dosyasi, veri):
    """Sayac sozlugunu ATOMIK yazar (tek kaynak: iki sayac da bunu kullanir)."""
    yol = _sayac_yolu(karantina_dosyasi)
    dizin = os.path.dirname(yol) or "."
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".ardisik.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(veri, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except FileNotFoundError:
            pass
        raise


def erisim_reddi_var(rc, cikti_yolu):
    """(bool, sebep) — KALICI erisim/yetki reddi imzasi var mi?

    FATAL_RE'den BAGIMSIZDIR: bu metinler CLI'nin `API Error:` bicimini
    KULLANMAZ, duz proza olarak basilir. Bu yuzden satir basi bicimi
    ARANMAZ; metnin TAMAMINDA imza aranir.
    """
    if rc == 0:
        return (False, "rc0")
    try:
        with open(cikti_yolu, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    except OSError as e:
        return (False, "cikti-okunamadi:" + type(e).__name__)
    if ERISIM_RE.search(metin):
        return (True, "erisim-reddi")
    return (False, "erisim-imzasi-yok")


def gecici_akis_var(rc, cikti_yolu):
    """bool — rc!=0 turda satir basina capali GECICI akis kopmasi imzasi var mi?"""
    if rc == 0:
        return False
    try:
        with open(cikti_yolu, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    except OSError:
        return False
    for satir in metin.splitlines():
        if GECICI_RE.search(satir):
            return True
    return False


def imza_var(rc: int, cikti_yolu: str) -> tuple:
    """Yan etkisiz karar fonksiyonu. Test dogrudan cagirir.

    Dondurur: (bool, sebep_str).
      bool True  -> karantina yazilmali
      bool False -> yazilmamali (sebep ile)
    """
    if rc == 0:
        return (False, "rc0-alinti")
    try:
        with open(cikti_yolu, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    except OSError as e:
        return (False, "cikti-okunamadi:" + type(e).__name__)
    for satir in metin.splitlines():
        # FATAL_RE satirin TAMAMINDA aranir; KOTA_RE AYNI satirda olmali.
        # ^[ \t]* YALNIZ bosluga izin verir -> "- " / "> " / "| " / "` "
        # / "#" gibi markdown onekleriyle baslayan alinti satirlari ESLESMEZ.
        if FATAL_RE.search(satir) and KOTA_RE.search(satir):
            return (True, "fatal-satir-var")
    return (False, "fatal-satir-yok")


def _yaz(motor: str, karantina_dosyasi: str) -> None:
    """Mevcut karantina dosyasina motor=<epoch> ekler (dedup + atomik).

    Ayni motorun eski satiri dusurulur; yalnizca gecici dosyaya yazip
    os.replace ile atomik degistirir. Hata olursa gecici dosya silinir.
    umask cagiran tarafindan 077 yapilir.
    """
    simdi = int(time.time())
    try:
        with open(karantina_dosyasi, encoding="utf-8") as f:
            satirlar = [s.strip() for s in f.read().splitlines() if s.strip()]
    except FileNotFoundError:
        satirlar = []
    yeni = [s for s in satirlar if s.split() and s.split()[0] != motor]
    yeni.append("%s %d" % (motor, simdi))
    dizin = os.path.dirname(karantina_dosyasi)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".motor-karantina.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(yeni) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, karantina_dosyasi)
    except BaseException:
        try:
            os.unlink(gecici)
        except FileNotFoundError:
            pass
        raise


def main(argv):
    # 🔴 K414: `--ev <ev_koku|ev_adi>` argv'nin HERHANGI bir yerinde durabilir
    # ve konumsal argumanlardan ONCE ayiklanir. Verilmezse ev "?" sayilir:
    # tek bilinmeyen ev FILO hukmu icin YETMEZ (yalniz tek-ev uzun dizi kolu).
    argv = list(argv)
    ev_deger = None
    if "--ev" in argv:
        i = argv.index("--ev")
        if i + 1 >= len(argv) or argv.count("--ev") > 1:
            sys.stderr.write(KULLANIM)
            return 2
        ev_deger = argv[i + 1]
        del argv[i:i + 2]
    # 🔴 K337: `--hal <AD>` eklendi. Konumsal 5 arguman DEGISMEDI; eski
    # cagri bicimi (5 arguman [+ --kuru]) BIREBIR calisir -- hal
    # verilmezse eski davranis aynen durur.
    bayraklar = argv[6:]
    kuru = "--kuru" in bayraklar
    hal = ""
    if "--hal" in bayraklar:
        i = bayraklar.index("--hal")
        if i + 1 < len(bayraklar):
            hal = bayraklar[i + 1]
    tanimli = set()
    for j, b in enumerate(bayraklar):
        if b == "--kuru":
            tanimli.add(j)
        elif b == "--hal":
            tanimli.add(j)
            tanimli.add(j + 1)
    if len(argv) < 6 or any(j not in tanimli for j in range(len(bayraklar))):
        sys.stderr.write(KULLANIM)
        return 2
    rc_str, cikti_yolu, motor, karantina_dosyasi, motor_regex = argv[1:6]
    try:
        rc = int(rc_str)
    except ValueError:
        sys.stderr.write("HATA: rc tamsayi degil: %r\n" % rc_str)
        return 2
    if not os.path.isfile(cikti_yolu):
        sys.stderr.write("HATA: cikti dosyasi yok: %s\n" % cikti_yolu)
        return 2
    # Motor kapali kumede mi? isci.sh'den regex arguman olarak gelir
    # (ikiz tanim YOK). re.fullmatch ile motorun TAMAMINI esle.
    try:
        kume_rx = re.compile(motor_regex)
    except re.error as e:
        sys.stderr.write("HATA: motor_regex gecersiz: %s\n" % e)
        return 2
    if not kume_rx.fullmatch(motor):
        print(
            "KARANTINA_KARAR motor=%s rc=%d imza=yok yazildi=hayir sebep=motor-kume-disi"
            % (motor, rc)
        )
        return 10
    karar, sebep = imza_var(rc, cikti_yolu)
    # 🔴 KOL E (K337): BUTCE TAVANI motor arizasi degildir.
    # Ucuncu kova YALNIZ hal GERCEKTEN BUTCE_TAVANI iken ve rc!=0 iken
    # acilir. `karar` True ise (bilinen KOTA/FATAL imzasi ayrica VAR)
    # butce kolu onu MASKELEMEZ -- normal akisa devam edilir.
    if hal == EKSIK_HALI and rc != 0 and not karar:
        # K417 (15 Eyl 2026): EKSIK motor arizasi degildir; kendi kovasinda
        # sayilir, motor sayacina DOKUNMAZ (BUTCE_HALI deseniyle ayni).
        _motor_ardisik = int(ardisik_oku(karantina_dosyasi).get(motor) or 0)
        if kuru:
            _eksik_ardisik = butce_oku(karantina_dosyasi, motor) + 1
        else:
            _eksik_ardisik = butce_guncelle(karantina_dosyasi, motor, True)
        print(
            "KARANTINA_KARAR motor=%s rc=%d hal=%s imza=%s yazildi=hayir "
            "sebep=eksik-tur-yarim-kaldi ardisik=%d "
            "eksik_ardisik=%d"
            % (motor, rc, hal, sebep, _motor_ardisik, _eksik_ardisik)
        )
        return 10
    if hal == BUTCE_HALI and rc != 0 and not karar:
        _motor_ardisik = int(ardisik_oku(karantina_dosyasi).get(motor) or 0)
        if kuru:
            _butce_ardisik = butce_oku(karantina_dosyasi, motor) + 1
        else:
            _butce_ardisik = butce_guncelle(karantina_dosyasi, motor, True)
        print(
            "KARANTINA_KARAR motor=%s rc=%d hal=%s imza=%s yazildi=hayir "
            "sebep=butce-tavani-motor-arizasi-degil ardisik=%d "
            "butce_ardisik=%d"
            % (motor, rc, hal, sebep, _motor_ardisik, _butce_ardisik)
        )
        return 10
    ev = ev_kanonik(ev_deger)
    # 🔴 KOL F (K414): gecici akis kopmasi. Bilinen KOTA/FATAL imzasi ya da
    # KALICI erisim reddi ayrica VARSA gecici kol onlari MASKELEMEZ.
    if (not karar and gecici_akis_var(rc, cikti_yolu)
            and not erisim_reddi_var(rc, cikti_yolu)[0]):
        if kuru:
            _ardisik, _evler = gecici_oku(karantina_dosyasi, motor)
            _ardisik, _evler = _ardisik + 1, sorted(set(_evler + [ev]))
        else:
            _ardisik, _evler = gecici_guncelle(karantina_dosyasi, motor, ev)
        if filo_hukmu(_ardisik, _evler, GECICI_ARDISIK_ESIGI, 0):
            karar, sebep = True, "gecici-akis-kopmasi-filo-ardisik%d" % _ardisik
        else:
            print(
                "KARANTINA_KARAR motor=%s rc=%d imza=gecici yazildi=hayir "
                "sebep=gecici-akis-kopmasi-motor-arizasi-degil ardisik=%d "
                "evler=%d ev=%s"
                % (motor, rc, _ardisik, len(_evler), ev)
            )
            return 10
    else:
        # 🔴 KOL C: ardisik sayac HER kosumda guncellenir (rc==0 SIFIRLAR).
        # Kuru kosumda diske dokunmayiz; sayac yalnizca OKUNUR.
        if kuru:
            _ardisik = int(ardisik_oku(karantina_dosyasi).get(motor) or 0)
            _evler = evler_oku(karantina_dosyasi, motor)
            if rc != 0:
                _ardisik, _evler = _ardisik + 1, sorted(set(_evler + [ev]))
            else:
                _ardisik, _evler = 0, []
        else:
            _ardisik = ardisik_guncelle(karantina_dosyasi, motor, rc != 0, ev)
            _evler = evler_oku(karantina_dosyasi, motor)
        if not karar:
            # Ikinci eksen: KALICI erisim/yetki reddi. Tek seferlik rc!=0
            # karantina URETMEZ -- ancak esige ulasan ARDISIK dizide yazar.
            _erisim, _erisim_sebep = erisim_reddi_var(rc, cikti_yolu)
            if _erisim and _ardisik >= ERISIM_ARDISIK_ESIGI:
                karar, sebep = True, "%s-ardisik%d" % (_erisim_sebep, _ardisik)
            elif _erisim:
                print(
                    "KARANTINA_KARAR motor=%s rc=%d imza=var yazildi=hayir "
                    "sebep=%s-esik-alti(%d/%d)"
                    % (motor, rc, _erisim_sebep, _ardisik, ERISIM_ARDISIK_ESIGI)
                )
                return 10
            elif rc != 0 and filo_hukmu(_ardisik, _evler, GENEL_ARDISIK_ESIGI, TEK_EV_UZUN_DIZI_ESIGI):
                # Kol D: bilinen imza yok AMA dizi filo hukmu esigini asti
                # (en az iki ev, ya da tek evin uzun dizisi -- K414).
                karar, sebep = True, "ardisik-basarisiz-imzasiz%d" % _ardisik
    if not karar:
        print(
            "KARANTINA_KARAR motor=%s rc=%d imza=yok yazildi=hayir sebep=%s ardisik=%d "
            "evler=%d ev=%s"
            % (motor, rc, sebep, _ardisik, len(_evler), ev)
        )
        return 10
    if kuru:
        print(
            "KARANTINA_KARAR motor=%s rc=%d imza=var yazildi=kuru sebep=%s ardisik=%d evler=%d"
            % (motor, rc, sebep, _ardisik, len(_evler))
        )
        return 0
    try:
        _yaz(motor, karantina_dosyasi)
    except OSError as e:
        sys.stderr.write("HATA: karantina yazilamadi: %s\n" % e)
        return 2
    print(
        "KARANTINA_KARAR motor=%s rc=%d imza=var yazildi=evet sebep=%s ardisik=%d evler=%d ev=%s"
        % (motor, rc, sebep, _ardisik, len(_evler), ev)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

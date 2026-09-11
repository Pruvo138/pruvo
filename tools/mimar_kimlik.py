#!/usr/bin/env python3
"""Mimar kapilarinin ortak, fail-closed ISCI kimlik ekseni."""
import os


# Kapali kume: bos ya da gelecekte eklenecek bilinmeyen bir motor kapiyi acmaz.
# 🔴 BU KUME "KIMLIK TANIMA" ICINDIR, "IS DAGITIMI" ICIN DEGIL: emekli motorlarin
# ESKI turlari da isci sayilmali (kimligi geriye donuk tanimak zorundayiz).
#
# 🔴 7 EYL 2026 — "kimi" BU SATIRDA BILEREK DURUYOR (KraL; emirden SAPMA, adiyla
# yaziliyor). Okan/BaBa emri "ISCI_MOTORLARI ve CANLI_ISCI_MOTORLARI'ndan kimi
# cikar" diyordu; AYNI cumle "kimlik tanimada gecerli kalir" da diyordu. Bu
# depoda kimlik tanimasini VEREN kume TAM OLARAK BURASIDIR; ikisi ayni anda
# saglanamaz. Emrin ISLEVSEL amaci -- "yeni is YOLLANMAZ" -- kumeden cikarmakla
# DEGIL, EMEKLI_ISCI_MOTORLARI'na almakla saglanir. Emsal AYNI dosyadadir:
# `deepseek-*` 15 Agu'da emekli oldu ve bu satirda DURUYOR.
# Cikarsaydik iki OLCULU zarar olurdu:
#   (1) `mimar-icra-kapisi.py` once "bilinmeyen motor" koluna duserdi; EMEKLI
#       kolunun ACIK GEREKCELI reddi kimi icin OLU kalirdi
#       ([[yeni-kol-onceki-kolun-golgesinde-olur]]).
#   (2) 4 Eyl'deki gercek kimi kosumunun kimligi geriye donuk KAYBOLURDU.
# Yeni is akisi zaten `isci.sh` GECERLI_MOTORLAR'dan cikarilarak KAPATILDI.
ISCI_MOTORLARI = ("minimax-m3", "kimi", "deepseek-pro", "deepseek-flash", "claude")

# 🔴 YENI IS BU KUMEYE GONDERILIR. Sira ANLAMLIDIR: [0] birincil.
#
# 🔴 7 EYL 2026 — OKAN KARARI (6 Eyl 17:4x, BaBa kutuya yazdi): YEDEK MOTOR
# IPTAL EDILDI, `minimax-m3` TEK MOTOR. Bu kume artik TEK ELEMANLIDIR.
# Dayanak (olculmus): iptal edilen yedek omrunde 1 kosum (4 Eyl) yaparken m3
# 92 kosum + 3 gunluk cron + kabul kosumlari tasidi; 20 Agu'da ayni yedek 11
# karantina + 21 kez 403 "usage limit" yemis ve gun sonunda hala kapaliydi.
# Abonelik iptali OKAN KAPISI'dir (panel, Okan'in eli) — kod tarafi burasidir.
#
# 🔴 YEDEK YOKTUR: m3 duserse kosum DURUR, Claude'a DUSMEZ. Bu hukmun MAKINEDEKI
# karsiligi `~/.claude/cron/isci.sh` MOTOR-YOK KAPISI'dir (uc anahtari yoksa
# rc=1 + `HAL=MOTOR-YOK`); olcen kol `tools/motor-yok-kapisi-test.py` (3 kol:
# mutant + kontrol + kapi-kaldirildi). `PRUVO_CLAUDE_ISCI_IZNI` o kolu ACMAZ.
#
# 🔴 m3 DE 9 EYL RAPORUNDA ORAN >=1,5 TUTMAZSA IPTAL (Okan, ayni karar).
#
# NEDEN AYRI BIR KUME (olculdu 17 Agu 2026, KraL): CI nobetinin dagitim tablosu
# (`~/.claude/cron/nobet-kapi.py`) uc kata is yolluyordu — `emekli motor`, `deepseek-pro`,
# `deepseek-flash` — ve **ucu de 15 Agu'da EMEKLI edilmisti**; dahasi VARSAYILAN kat
# `deepseek-pro` idi, yani jetonu eslesmeyen HER kalem emekli bir kuyruga dusuyordu.
# Sonuc: nobet 76 tur boyunca is "dagitti" ama hicbiri kosmadi (`ONARIM=0` `KAPANAN=0`,
# `USTUSTE_ONARIMSIZ=63`). Bir kati emekli etmek o kata ATANMIS isleri tasimiyor
# ([[goc-yolu-eski-kapiya-takilir]]); goc icin dagitimin CANLI kumeden turemesi sart.
CANLI_ISCI_MOTORLARI = ("minimax-m3",)

# Emekli: yeni is YOLLANMAZ. Kimlik tanimada gecerli kalir.
# 🔴 7 Eyl 2026: "kimi" BU KUMEYE ALINDI (Okan karari 6 Eyl). Yani ona artik
# YENI IS YOLLANMAZ -- `mimar-icra-kapisi.py` emekli kolu ACIK GEREKCEYLE
# reddeder -- ama ESKI turleri hala ISCI sayilir. Ayni gun uc ve nabiz
# yuzeyleri de kaldirildi: `isci.sh` GECERLI_MOTORLAR'dan CIKTI,
# `isci-motor-uc.zsh` uc ayarlari SILINDI, crontab nabiz satirlari SILINDI.
# 🔴 ILK ELEMAN DEGISMEZ, YENI AD SONA EKLENIR:
# `tools/emekli-motor-adi-nobetcisi.py` bu satirin BASINA (tanim + ilk ad)
# dizge capasi atmistir; sirayi bozmak o nobetciyi "YASAK KAYDI DUSTU" diye
# kirmizi yakar. Ayni nobetci bu dosyadaki emekli ad gecisine NON-GROWTH
# tavan da uygular — buraya aciklama yazarken adi TEKRARLAMA.
EMEKLI_ISCI_MOTORLARI = ("codex", "deepseek-pro", "deepseek-flash", "kimi")

# === 17 AGU 2026 (K159): emekli motor SURELI PENCERESI KIMLIK KAYNAGI ===
# Okan karari: emekli motor 17->20 AGU arasinda kapali kumeden CIKTI; 20->22 AGU kapali; 22 AGU
# kimi donunce yeni karar. Pencere bitis TARIH olarak sabit; kapilar bu degerden turetilir
# ([[ikiz-tanim-sessiz-ayrisma]] — kapiya ELLE gomulmez).
# Bu tarihten SONRA emekli motor yeniden KAPALI sayilir (sessiz kalicilasma engeli:
# [[goc-yolu-eski-kapiya-takilir]]).
EMEKLI_MOTOR_IZINLI_MODELLER = (
    "gpt-5.6-luna",        # birincil alt model
    "gpt-5.6-terra",       # ikincil
    "gpt-5.4-mini",        # ucuz alternatif
    "gpt-5.3-codex-spark", # ucuz alternatif
)
EMEKLI_MOTOR_YASAK_MODELLER = frozenset({"gpt-5.6-sol"})  # amiral — Okan "sol kullanmayin" emri
EMEKLI_MOTOR_PENCERE_BITIS = "2026-08-20"  # dahil; bu tarihten SONRA emekli motor yeniden KAPALI


# === 19 AGU 2026 (K214): TURETIM YUZEYI — GOMULU IKIZ TANIM YASAGI ===
# OLCULEN KUSUR: tools/mimar-kapi-kur.py listeyi kendi govdesine GOMUYOR ve 13 Agu'da
# BES karde eve o DONMUS kopyayi kurmustu (kimi YOK, emekli deepseek VAR). Yani tek
# kaynak burasiydi ama KURULAN kopya buradan TUREMIYORDU ([[ikiz-tanim-sessiz-ayrisma]]).
# COZUM: kurulan blogun METNI de, imzasi da BURADA uretilir; kurucu yalnizca yapistirir.
# Ucuncu bir renderer YAZILMAZ — yoksa ikiz tanim bir kat yukari tasinmis olurdu.
# 🔴 NOBETCI YOK (ACIK KALEM, 11 Eyl 2026): eski satir motor-tek-kaynak-kapisi.py'yi
# nobetci diye anip "ayni fonksiyonlarla yeniden uretip karsilastirir" diyordu;
# O DOSYA YOK (ca8c3815 supurmesi). Kurulu kopyanin buradan TUREYIP turemedigi
# bugun OLCULMUYOR — yani K214'un kapattigi ariza yeniden acilabilir ve kimse gormez.
MOTOR_BLOK_BAS = "# === PRUVO MOTOR KUMESI (TURETILDI — mimar_kimlik.py) BASLANGIC ==="
MOTOR_BLOK_SON = "# === PRUVO MOTOR KUMESI (TURETILDI) BITIS ==="

# Turetilen adlar: kurulu kopyada BU UCU ve imza satiri bulunur.
MOTOR_TURETILEN_ADLAR = (
    "ISCI_MOTORLARI", "CANLI_ISCI_MOTORLARI", "EMEKLI_ISCI_MOTORLARI")
MOTOR_IMZA_ADI = "ISCI_MOTOR_KAYNAK_IMZASI"


def motor_kumeleri():
    """Turetilen adlarin kanonik (ad -> tuple) eslemesi. TEK okuma noktasi."""
    return {
        "ISCI_MOTORLARI": tuple(ISCI_MOTORLARI),
        "CANLI_ISCI_MOTORLARI": tuple(CANLI_ISCI_MOTORLARI),
        "EMEKLI_ISCI_MOTORLARI": tuple(EMEKLI_ISCI_MOTORLARI),
    }


def motor_imzasi():
    """Kumelerin KANONIK imzasi (sha256/16). Yorum/bosluk degisimi imzayi OYNATMAZ —
    imza DEGERI baglar, dosyayi degil: aksi halde her yorum duzenlemesi bes evi
    'sapmis' gosterir ve nobetci gurultuye bogulup guvenilmez olurdu."""
    import hashlib
    govde = ";".join(
        ad + "=" + ",".join(motor_kumeleri()[ad]) for ad in MOTOR_TURETILEN_ADLAR)
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()[:16]


# === K259 (24 AGU 2026): ISCI DAMGASI ICERIKTEN TURETILIR ===
# OLCULEN KUSUR (K259): ISCI_DAMGA kurucuya ELLE yazili sabit bir dize idi ve kaynak
# kumeler degisse bile damga degismiyordu — boylece dagitici 'ZATEN TAM' diyip kurulu
# kopyaya HIC dokunmuyor, 4 kardes ev 4 GUNDUR bayat kaliyordu ([[emir-canliligi-
# kurulu-kopyadan-olculur]]). Mimar hukmu: damga, enjekte edilen ISCI blogunun
# ICERIGINDEN (motor_blogu_kaynagi() ciktisinin sha256/12) turetilir; icerik degisince
# damga KENDILIGINDEN degisir. Elle yazilan surum dizesi damga olarak KULLANILMAZ.
def isci_damgasi():
    """ISCI-SARMALAYICI blok damgasi: motor_blogu_kaynagi() ciktisinin sha256 ilk 12 hanesi.

    Icerikten turetildigi icin tek kaynak (CANLI/EMEKLI/ISCI kumeleri) degisince damga
    kendiliginden degisir; 'ZATEN TAM' karari artik icerik esitligine baglidir, damga
    esitligine degil. Idempotent: ayni icerik icin ayni damga."""
    import hashlib
    return hashlib.sha256(motor_blogu_kaynagi().encode("utf-8")).hexdigest()[:12]


def motor_blogu_kaynagi():
    """Kurulu kopyaya YAPISTIRILACAK Python blogunun metni (marker'lar DAHIL)."""
    satirlar = [
        MOTOR_BLOK_BAS,
        "# 🔴 TURETILDI — ELLE DUZENLEME YOK. Tek kaynak: tools/mimar_kimlik.py.",
        "# Degistirmek icin kaynagi duzenle, sonra su komutu kostur:",
        # 🔴 20 AGU (K250): EV-GORELI YAZIM. Bu iki satir enjekte edilen blogun ICINDE
        # yasar ve K250'den beri kardes evlerin COMMIT'LENEN kapi dosyasina iniyor —
        # yani makineye cakili "/Users/<ad>/..." yolu oralarda hem YANLIS olurdu hem de
        # kullanici adi tasirdi. Satirlar SALT YORUM (davranis yok); imza da yalnizca
        # motor kumelerinden turer, dolayisiyla bu degisiklik sapma URETMEZ.
        # 🔴 11 EYL 2026: bu iki satir ADI GECEN IKI DOSYAYI da gosteriyordu ve IKISI DE
        # ca8c3815 ile SILINDI (mimar-kapi-kur.py = kurucu, motor-tek-kaynak-kapisi.py =
        # sapma nobetcisi). Yani KURULU her kapinin basinda, okuyana var olmayan bir
        # kurucu ve var olmayan bir nobetci gosteren iki satir duruyordu. Satirlar
        # DURUST hale getirildi; imza yalnizca motor kumelerinden turedigi icin bu
        # degisiklik SAPMA URETMEZ (ustteki K250 notu).
        "#   KURUCU YOK (acik kalem): blogu elle guncelle, kaynak tools/mimar_kimlik.py.",
        "# SAPMA NOBETCISI YOK (acik kalem): kurulu kopya kaynaktan TUREDI mi OLCULMUYOR.",
    ]
    kumeler = motor_kumeleri()
    for ad in MOTOR_TURETILEN_ADLAR:
        satirlar.append(ad + " = " + repr(kumeler[ad]))
    satirlar.append(MOTOR_IMZA_ADI + ' = "' + motor_imzasi() + '"')
    satirlar.append(MOTOR_BLOK_SON)
    return "\n".join(satirlar) + "\n"


def emekli_motor_mu(motor):
    """Motor EMEKLI mi? Bilinmeyen ad EMEKLI DEGILDIR (onu kapali-kume kolu reddeder);
    burada 'emekli' TANINAN ama IS VERILMEYEN kati isaretler."""
    return motor in EMEKLI_ISCI_MOTORLARI


def emekli_gerekcesi(motor):
    """Emekli kata is yollama reddinin ACIK gerekcesi (sessiz kabul YASAK)."""
    return (
        "EMEKLI motor (" + str(motor)[:24] + "): bu kata YENI IS YOLLANMAZ. "
        "Kimlik tanimada gecerli kalir (eski turlar isci sayilir), ama dagitim "
        "CANLI kumeden yapilir — canli kume: " + " / ".join(CANLI_ISCI_MOTORLARI) +
        " (birincil: " + CANLI_ISCI_MOTORLARI[0] + "). Emekli kume: " +
        " / ".join(EMEKLI_ISCI_MOTORLARI) + "."
    )


def canli_motor_mu(motor):
    """Yeni is bu motora gonderilebilir mi? Bilinmeyen ad FAIL-CLOSED (False)."""
    return motor in CANLI_ISCI_MOTORLARI


def canli_kata_goc(motor):
    """Emekli/bilinmeyen kati CANLI birincil kata tasir; canli kati AYNEN dondurur.

    Fail-closed yon BILEREK: tanimadigi adi 'zaten canli' saymaz, birincile goc ettirir —
    aksi halde yazim hatasi tasiyan bir kat adi sessizce is-gonderilmeyen kuyruk olurdu.
    """
    return motor if canli_motor_mu(motor) else CANLI_ISCI_MOTORLARI[0]


# === 27 AGU 2026 (K318) — OTURUM ROL EKSENI (KIMLIK EKSENINDEN AYRIDIR) =========
#
# OLCULEN ARIZA (uc ev, ucuncu tekrar): `mimar-icra-kapisi` yalnizca KIMLIK olcuyordu
# (agent_id / PRUVO_ISCI_KOSUMU). Bir CIP OTURUMU (kendi worktree'sinde acilmis ayri
# Claude oturumu) bu iki eksenin ikisini de TASIMAZ — yani kapi onu "mimarin ANA
# oturumu" sayip `python3` kosumunu REDDEDIYORDU. Bedeli sayiyla: pruvo-hasat main
# tepesi `1bea450d` = "Marin x MakerWorld ekleme dilim-1 BLOKE kaydi (mimar-icra-kapisi
# python3 kosumunu bu iscide reddediyor)"; ayni sinif BMW x CGTrader dilim-3'te (K291)
# tekrarladi; hat haftalardir duruyor, islenen urun 0. Yani kapi, korumak icin var
# oldugu duzenin (mimar YARGILAR, cip ICRA EDER) tam olarak ICRA ayagini kesiyordu.
#
# 🔴 SINIR DUZELTMESIDIR, GEVSETME DEGIL: mimarin ANA oturumu AYNEN reddedilmeye devam
# eder. Degisen tek sey, kapinin artik "kim" (kimlik) yaninda "NEREDEN" (rol) sorusunu
# da sormasidir.
#
# 🔴 NEDEN `transcript_path` — VE NEDEN `cwd` DEGIL:
#   20 Tem'de tam da bu muafiyet `cwd` uzerine kurulmus ve KALDIRILMISTI, cunku cwd
#   KAYDIRILABILIR bir sinyaldir: kabuk cwd'si cagrilar arasi kalicidir, `cd` makine
#   olarak engellenmez ve gercek worktree dizinleri diskte durur — yani "cd <worktree>"
#   TEK KOMUTLUK bir muafiyet anahtari olurdu. O teshis DOGRUDUR ve burada KORUNUR:
#   cwd bu fonksiyonda HIC OKUNMAZ.
#   `transcript_path` ise oturum ACILIRKEN damgalanir; oturumun kendi kostudugu hicbir
#   komut (cd, env atamasi, dosya yazimi) onu oynatamaz. Yani BEYAN degil OLCUMDUR.
#   Karsilastirma da ADA gore degil KAYDA gore yapilir: aday, git'in `.git/worktrees/`
#   kaydindaki GERCEK worktree koklerinin damgasiyla TAM BILESEN ESITLIGI ile aranir
#   (alt-dize DEGIL) — "…claude-worktrees…" gecen uydurma bir ad kapiyi ACMAZ.
#   Ana checkout hicbir zaman worktree olarak KAYITLI olmadigi icin ANA oturum bu
#   eksende yapisal olarak eslesemez.
#
# 🔴 FAIL-CLOSED: `transcript_path` yoksa/okunamiyorsa, kayit kumesi bossa ya da hicbir
#   kok eslesmiyorsa donus `None`'dur ve `None` = ANA = RED tarafi. "OLCULEMEDI" bir
#   gecis gerekcesi DEGILDIR ([[olculemedi-bypass-degil-menzil-daraltmasi]]).
#
# 🔴 TEK KAYNAK: rol sorusunun cevabi YALNIZ burada uretilir. Kapilar bu fonksiyonu
#   CAGIRIR; kendi govdelerinde ikinci bir "cip mi" testi TASIMAZ
#   ([[ikiz-tanim-sessiz-ayrisma]]). Muafiyet LISTESI yoktur ve eklenmez — care liste
#   degil EKSENDIR ([[tekil-yama-sinifi-kapatmaz]]).
#
# 🔴 KIMLIK EKSENIYLE BIRLESTIRILMEZ: `kimlik_ekseni()` "bu cagri bir ISCI'den mi
#   geliyor" sorusunu yanitlar ve ISCI kapidan TAM muaftir. `rol_ekseni()` ise
#   "bu OTURUM mimarin ana oturumu mu, yoksa cip/worktree oturumu mu" sorusunu
#   yanitlar ve cip TAM muaf DEGILDIR (Okan emirlerini tasiyan kollar cipte de kosar).
#   Iki fonksiyonu tek yuklemeye indirmek, cipe Claude-isci yasagini SESSIZCE acar
#   ([[ad-iki-rolde-mutanti-golgeler]]).
ROL_KANALI = "transcript_path"


def _proje_damgasi(yol):
    """Claude Code'un proje-dizini damgasi: alfanumerik OLMAYAN her karakter '-'.

    Olculdu (27 Agu, canli oturum): `/Users/okan/dev/pruvo/.claude/worktrees/
    busy-ishizaka-73d101` -> `-Users-okan-dev-pruvo--claude-worktrees-busy-ishizaka-73d101`
    ve `/Users/okan/dev/pruvo` -> `-Users-okan-dev-pruvo`. Damga KAYIPLIDIR (farkli
    yollar ayni damgaya dusebilir) ama ADAYLARIN HEPSI git'e kayitli mesru worktree
    kokleridir; kayipli eslesmenin acabilecegi tek sey yine kayitli bir koktur."""
    return "".join(k if k.isalnum() else "-" for k in yol)


def rol_ekseni(girdi, worktree_kokleri):
    """OTURUM ROLU — TEK KAYNAK. Doner: eslesen worktree koku (str) ya da ``None``.

    ``None`` IKI hali birden ifade eder ve IKISI DE RED tarafidir:
      * oturum mimarin ANA oturumudur, ya da
      * rol OLCULEMEDI (transcript damgasi yok / kayit okunamadi / eslesme yok).
    Cagiran bu ikisini ayirt etmeye CALISMAZ; ayirt etmek "olculemedi"yi bir gecis
    gerekcesine cevirmenin kapisi olurdu.
    """
    yol = girdi.get(ROL_KANALI)
    if not isinstance(yol, str) or not yol.strip():
        return None
    if not worktree_kokleri:
        return None
    # TAM BILESEN esitligi: alt-dize testi degil. '/a/b/-Users-...-wt-ek/x.jsonl'
    # gibi damgayi ICINDE gecirenler eslesmez.
    bilesenler = set(yol.split("/"))
    for kok in sorted(worktree_kokleri):
        if not kok:
            continue
        adaylar = {_proje_damgasi(kok)}
        try:
            adaylar.add(_proje_damgasi(os.path.realpath(kok)))
        except OSError:
            pass
        if adaylar & bilesenler:
            return kok
    return None


ISCI_KOSUM_KANALI = "PRUVO_ISCI_KOSUMU"


def kimlik_ekseni(girdi, ortam=None):
    """Kimlik kaynagini dondur; ``None`` her zaman MIMAR demektir."""
    aid = girdi.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return "agent_id"
    cevre = os.environ if ortam is None else ortam
    motor = cevre.get(ISCI_KOSUM_KANALI)
    if motor in ISCI_MOTORLARI:
        return "sarmalayici:" + motor
    return None


# === 🔴 11 EYL 2026 — KAPI BATARYALARI ICIN KIMLIK EKSENI CIVISI ==============
# OLCULEN ARIZA (iki AYRI bataryada, birebir uretildi):
#   tools/tikayici-kaldirma-test.py  temiz ortam -> ❌ 0  · isci ortami -> ❌ 13
#   tools/icra-kapisi-test.py        temiz ortam -> 43/43 · isci ortami -> 40/43
# Sebep TEK: `kimlik_ekseni` yukarida `agent_id`'ye EK OLARAK CEVRE DEGISKENINI
# okur. Bir batarya kapiyi alt surec olarak cagirdiginda cevre MIRAS ALINIR; bir
# m3 iscisinden kosuldugunda kapi `main()` basinda ISCI muaf cikar ve "RED KALIR"
# vakalari DOGAL olarak GECER. Yani batarya, olcmeyi iddia ettigi kurali degil
# KOSUCUSUNUN KIMLIGINI olcer ([[iki-kollu-govde-tek-sabite-capalanirsa-kosucunun-diskini-olcer]]).
#
# 🔴 NEDEN BURADA, HER BATARYADA DEGIL: ayni yardimciyi iki test dosyasina
# KOPYALAMAK, kimlik kanali degistiginde sessizce ayrisan bir IKIZ uretirdi
# ([[ikiz-tanim-sessiz-ayrisma]]) — ustelik kanal adi (`PRUVO_ISCI_KOSUMU`) ZATEN
# bu modulun sirridir. Civi, kimligi TANIMLAYAN modulde durur; bataryalar onu
# IMPORT eder, yeniden YAZMAZ. Olculmus emsal: `icra-kapisi-test.py:271` bu
# temizligi TEK bir vaka icin elle yapmisti, kalan uc vaka capali kalmisti —
# kismi civi, civisizlik kadar sessizdir.
def kapi_cevresi(kimlik="MIMAR", ortam=None):
    """Kapi alt surecine verilecek CEVRE — kimlik ekseni BURADA civilenir.

    kimlik="MIMAR": `PRUVO_ISCI_KOSUMU` SILINIR. "Temiz ortam varsaymak" DEGIL,
        ortami KURMAKTIR: batarya bir isciden kosulsa bile mimar kolunu olcer.
    kimlik="ISCI" : ayni degisken KAPALI KUMEDEN turetilmis bir motora set edilir
        (ad elle yazilmaz). Kume bos ise ``None`` doner — cagiran bunu
        OLCULEMEDI olarak islemelidir, sessiz yesil DEGIL.
    """
    e = dict(os.environ if ortam is None else ortam)
    e.pop(ISCI_KOSUM_KANALI, None)
    if kimlik == "ISCI":
        if not ISCI_MOTORLARI:
            return None
        e[ISCI_KOSUM_KANALI] = ISCI_MOTORLARI[0]
    return e

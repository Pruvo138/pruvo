#!/usr/bin/env python3
"""Mimar kapilarinin ortak, fail-closed ISCI kimlik ekseni."""
import os


# Kapali kume: bos ya da gelecekte eklenecek bilinmeyen bir motor kapiyi acmaz.
# 🔴 BU KUME "KIMLIK TANIMA" ICINDIR, "IS DAGITIMI" ICIN DEGIL: emekli motorlarin
# ESKI turlari da isci sayilmali (kimligi geriye donuk tanimak zorundayiz).
ISCI_MOTORLARI = ("minimax-m3", "kimi", "deepseek-pro", "deepseek-flash", "claude")

# 🔴 YENI IS BU KUMEYE GONDERILIR (CLAUDE.md kanonu: minimax-m3 BIRINCIL · kimi YEDEK).
# Sira ANLAMLIDIR: [0] birincil, [1] yedek.
#
# 🔴 20 AGU 2026 — OKAN KARARI: SIRA TERS CEVRILDI (abonelikler AYNI kaldi).
# Dayanak (`tools/yetkinlik/sonuclar/kral-yetkinlik-20agu.md`): YETENEK ucurumu YOK
# (m3 16/18 · kimi 18/18); ayrisma SUREKLILIKTE. Kimi 20 Agu'da 11 karantina + 21 kez
# 403 "usage limit for this billing cycle" yedi ve gun sonunda HALA kapaliydi; m3 0/0.
# Ayni 7 gunde m3 kimi'nin ~8 kati ham baglam isledi (m3 1188 tur / 4,19B · kimi 1025
# tur / 523M, kimi medyani 500 = turlarin cogu kapida oldu). Kimi'nin kotasini yiyen
# sinif toplu urun ekleme dilimleridir. KAPALI KUME DEGISMEDI — degisen yalniz SIRA.
#
# NEDEN AYRI BIR KUME (olculdu 17 Agu 2026, KraL): CI nobetinin dagitim tablosu
# (`~/.claude/cron/nobet-kapi.py`) uc kata is yolluyordu — `codex`, `deepseek-pro`,
# `deepseek-flash` — ve **ucu de 15 Agu'da EMEKLI edilmisti**; dahasi VARSAYILAN kat
# `deepseek-pro` idi, yani jetonu eslesmeyen HER kalem emekli bir kuyruga dusuyordu.
# Sonuc: nobet 76 tur boyunca is "dagitti" ama hicbiri kosmadi (`ONARIM=0` `KAPANAN=0`,
# `USTUSTE_ONARIMSIZ=63`). Bir kati emekli etmek o kata ATANMIS isleri tasimiyor
# ([[goc-yolu-eski-kapiya-takilir]]); goc icin dagitimin CANLI kumeden turemesi sart.
CANLI_ISCI_MOTORLARI = ("minimax-m3", "kimi")

# Emekli: yeni is YOLLANMAZ. Kimlik tanimada gecerli kalir.
EMEKLI_ISCI_MOTORLARI = ("codex", "deepseek-pro", "deepseek-flash")

# === 17 AGU 2026 (K159): CODEX SURELI PENCERESI KIMLIK KAYNAGI ===
# Okan karari: codex 17->20 AGU arasinda kapali kumeden CIKTI; 20->22 AGU kapali; 22 AGU
# kimi donunce yeni karar. Pencere bitis TARIH olarak sabit; kapilar bu degerden turetilir
# ([[ikiz-tanim-sessiz-ayrisma]] — kapiya ELLE gomulmez).
# Bu tarihten SONRA codex yeniden KAPALI sayilir (sessiz kalicilasma engeli:
# [[goc-yolu-eski-kapiya-takilir]]).
CODEX_IZINLI_MODELLER = (
    "gpt-5.6-luna",        # birincil alt model
    "gpt-5.6-terra",       # ikincil
    "gpt-5.4-mini",        # ucuz alternatif
    "gpt-5.3-codex-spark", # ucuz alternatif
)
CODEX_YASAK_MODELLER = frozenset({"gpt-5.6-sol"})  # amiral — Okan "sol kullanmayin" emri
CODEX_PENCERE_BITIS = "2026-08-20"  # dahil; bu tarihten SONRA codex yeniden KAPALI


# === 19 AGU 2026 (K214): TURETIM YUZEYI — GOMULU IKIZ TANIM YASAGI ===
# OLCULEN KUSUR: tools/mimar-kapi-kur.py listeyi kendi govdesine GOMUYOR ve 13 Agu'da
# BES karde eve o DONMUS kopyayi kurmustu (kimi YOK, emekli deepseek VAR). Yani tek
# kaynak burasiydi ama KURULAN kopya buradan TUREMIYORDU ([[ikiz-tanim-sessiz-ayrisma]]).
# COZUM: kurulan blogun METNI de, imzasi da BURADA uretilir; kurucu yalnizca yapistirir,
# nobetci (tools/motor-tek-kaynak-kapisi.py) ayni fonksiyonlarla yeniden uretip karsilastirir.
# Ucuncu bir renderer YAZILMAZ — yoksa ikiz tanim bir kat yukari tasinmis olurdu.
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
        "#   python3 ~/dev/pruvo/tools/mimar-kapi-kur.py --isci-kapisi --uygula",
        "# Sapma nobetcisi: python3 ~/dev/pruvo/tools/motor-tek-kaynak-kapisi.py",
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


def kimlik_ekseni(girdi, ortam=None):
    """Kimlik kaynagini dondur; ``None`` her zaman MIMAR demektir."""
    aid = girdi.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return "agent_id"
    cevre = os.environ if ortam is None else ortam
    motor = cevre.get("PRUVO_ISCI_KOSUMU")
    if motor in ISCI_MOTORLARI:
        return "sarmalayici:" + motor
    return None

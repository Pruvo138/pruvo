#!/usr/bin/env python3
"""Mimar kapilarinin ortak, fail-closed ISCI kimlik ekseni."""
import os


# Kapali kume: bos ya da gelecekte eklenecek bilinmeyen bir motor kapiyi acmaz.
# 🔴 BU KUME "KIMLIK TANIMA" ICINDIR, "IS DAGITIMI" ICIN DEGIL: emekli motorlarin
# ESKI turlari da isci sayilmali (kimligi geriye donuk tanimak zorundayiz).
ISCI_MOTORLARI = ("minimax-m3", "kimi", "deepseek-pro", "deepseek-flash", "claude")

# 🔴 YENI IS BU KUMEYE GONDERILIR (CLAUDE.md kanonu: kimi BIRINCIL · minimax-m3 YEDEK).
# Sira ANLAMLIDIR: [0] birincil, [1] yedek.
#
# NEDEN AYRI BIR KUME (olculdu 17 Agu 2026, KraL): CI nobetinin dagitim tablosu
# (`~/.claude/cron/nobet-kapi.py`) uc kata is yolluyordu — `codex`, `deepseek-pro`,
# `deepseek-flash` — ve **ucu de 15 Agu'da EMEKLI edilmisti**; dahasi VARSAYILAN kat
# `deepseek-pro` idi, yani jetonu eslesmeyen HER kalem emekli bir kuyruga dusuyordu.
# Sonuc: nobet 76 tur boyunca is "dagitti" ama hicbiri kosmadi (`ONARIM=0` `KAPANAN=0`,
# `USTUSTE_ONARIMSIZ=63`). Bir kati emekli etmek o kata ATANMIS isleri tasimiyor
# ([[goc-yolu-eski-kapiya-takilir]]); goc icin dagitimin CANLI kumeden turemesi sart.
CANLI_ISCI_MOTORLARI = ("kimi", "minimax-m3")

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

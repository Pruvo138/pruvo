#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K337 — BUTCE TAVANI HAL YAMASI (28 Agu 2026, cip KraL-K337Butce-28Agu).

Hedef dosyalar `~/.claude/cron/` altindadir (repoda KOPYASI YOKTUR); bu
yuzden yama repoda YASAR, kurulu kopyaya UYGULANIR ve olcum KURULU
KOPYADAN yapilir ([[emir-canliligi-kurulu-kopyadan-olculur]]).

--------------------------------------------------------------------------
OLCULEN VAKA (iddia degil; 28 Agu 2026, canli `isci.log`'dan okundu)
--------------------------------------------------------------------------
Bugun IKI tur butce tavaninda kesildi:
  14:27:05Z etiket=onarim-sinif-kapisi-28agu   BITIS rc=1 sure=672  TUR=118
  14:51:53Z etiket=onarim-sinif-kapisi-d1-28agu BITIS rc=1 sure=1404 TUR=196
Ikisinde de `butce_vuruldu=1`, ve:
  ① `BITIS rc=1` sirаdan bir dusuşten AYIRT EDILEMIYOR (hal jetonu YOK).
  ② DURMA NOTU 0 dosya -- kapanis yordami YALNIZ `BEKCI=KESTI` (tur
     tavani) kolunda atesliyordu.
  ③ `KARANTINA_KARAR ... sebep=fatal-satir-yok ardisik=2` -- yani iki
     butce kesintisi BIRINCIL MOTORU esigin (3) bir adim onune getirdi.
     Para bitmesi motor arizasi olarak puanlandi.

--------------------------------------------------------------------------
DORT KOL
--------------------------------------------------------------------------
A) HAL JETONU — DIZGE DEGIL HAL  (isci.sh + isci-hal-cozucu.py)
   Eski kol `grep -Eq 'Exceeded USD budget'` ile INGILIZCE CUMLEYI
   okuyordu (K321'in birebir sinifi). Kurulu CLI ikilisi okundu: o cumle
   bir RENDER'dir; halin ADI `error_max_budget_usd`'dir ve
   `--output-format json` zarfinda `subtype` alaninda MAKINE-OKUNUR
   basilir. Tur artik o zarftan gecer; insan metni AYNEN korunur.
   `BITIS` satiri `hal=<AD>` tasir; `BUTCE_VURULDU` tetigi de dizgeden
   ALINIP hale baglanir (dizge kolu SILINIR, ikinci kol birakilmaz).

B) DURMA NOTU — TEK YORDAM, IKI SEBEP  (isci.sh + isci-durma-notu.py)
   Kapanis blogu TASINMADI ve KOPYALANMADI: yalnizca GIRISI
   genellestirildi. Sebep (`KAPANIS_HALI`) iki koldan gelebilir --
   `BEKCI=KESTI` (tur tavani) ya da `TUR_HALI=BUTCE_TAVANI` -- ama
   yordam TEKTIR. Deterministik yari diske BAYT>0 bir not yazar; LLM
   kapanis cagrisi onu ZENGINLESTIRIR, yerine GECMEZ. Kapanis cagrisi
   artik ana turun tavanini degil kendi tavanini kullanir
   (`PRUVO_ISCI_KAPANIS_BUTCE_USD`, varsayilan 2.00) -- butce kolunda
   ana tavan zaten dolmustur, ve bir not yazmak tam tur butcesi istemez.
   🔴 Kabul bataryasi KOPYA SAYAR: not uretimi 1, kapanis promptu 1,
   sebep atamasi 2 (iki kol).

C) KARANTINA — BUTCE MOTOR ARIZASI DEGIL  (isci-karantina-karar.py)
   `--hal` alinir. `hal=BUTCE_TAVANI` iken motorun `ardisik` sayaci
   ARTMAZ **ve SIFIRLANMAZ** -- o turda motor sagligi OLCULMEDI; sifir
   yazmak gercek ardisik dusuşleri SILER. Kesinti kendi kovasinda
   (`__butce__`) GORUNUR. 🔴 Ucuncu kova YALNIZ hal GERCEKTEN
   BUTCE_TAVANI iken acilir; hal bos/taninmaz ise eski davranis BIREBIR
   durur ([[emir-ariza-kovasina-duserse-hat-kendi-kendine-kirmizi-yanar]]
   ucuncu-kova disiplini). Bilinen KOTA/FATAL imzasi ayrica bulunduysa
   butce kolu onu MASKELEMEZ -- karantina yine yazilir.

D) URETEN TEMIZLER  (isci.sh)
   Durma notlari da tur ciktilari gibi budanir (en yeni 60).

Kullanim:
    python3 tools/k337/isci-butce-hali-yama.py --kuru     # yazmadan olc
    python3 tools/k337/isci-butce-hali-yama.py            # uygular
    python3 tools/k337/isci-butce-hali-yama.py --durum    # kurulu mu
    python3 tools/k337/isci-butce-hali-yama.py --kok DIZIN --durum
Cikis: 0 = tum kollar KURULU · 1 = eksik/dusen · 2 = arac hatasi.
"""

import argparse
import hashlib
import os
import shutil
import sys
import time

VARSAYILAN_KOK = os.path.expanduser("~/.claude/cron")
REPO_CRON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cron")

# Kurulacak YENI dosyalar: repo KANONIK kaynaktir, kurulu kopya birebir
# ayni olmalidir (kabul (6) bunu SHA ile olcer).
KOPYALANAN = ("isci-hal-cozucu.py", "isci-durma-notu.py")


# --------------------------------------------------------------------------
# YAMALAR — her biri (dosya, capa, yeni, isaret, kol)
#   capa   : kurulu kopyada TAM 1 kez gecmeli
#   yeni   : capanin yerine yazilacak metin
#   isaret : uygulanmis halde dosyada BIREBIR gecen dizge (idempotens)
# 🔴 K320 dersi: `isaret` `capa`nin ICINDE olmamali, yoksa yama her
#    kosumda yeniden uygulanip icerigi COGALTIR.
# --------------------------------------------------------------------------

ISCI = "isci.sh"
KARANTINA = "isci-karantina-karar.py"

YAMALAR = []


def _y(dosya, capa, yeni, isaret, kol, aciklama):
    YAMALAR.append({
        "dosya": dosya, "capa": capa, "yeni": yeni, "isaret": isaret,
        "kol": kol, "aciklama": aciklama,
    })


# --- A1: ana cagri json zarfindan ve cozucuden gecer ----------------------
_y(ISCI,
   'CLAUDE_BAYRAKLAR=(--permission-mode bypassPermissions --max-budget-usd "$BUTCE_USD")',
   'CLAUDE_BAYRAKLAR=(--permission-mode bypassPermissions --max-budget-usd "$BUTCE_USD" --output-format json)',
   'CLAUDE_BAYRAKLAR=(--permission-mode bypassPermissions --max-budget-usd "$BUTCE_USD" --output-format json)',
   "A", "ana cagri makine-okunur zarf ister (subtype = HAL)")

_y(ISCI,
   'CLAUDE_BAYRAKLAR_2=(--permission-mode bypassPermissions --max-budget-usd "$BUTCE_USD")',
   'CLAUDE_BAYRAKLAR_2=(--permission-mode bypassPermissions --max-budget-usd "$BUTCE_USD" --output-format json)',
   'CLAUDE_BAYRAKLAR_2=(--permission-mode bypassPermissions --max-budget-usd "$BUTCE_USD" --output-format json)',
   "A", "tekrar cagrisi da ayni zarftan gecer")

_y(ISCI,
   'env "${CLAUDE_ENV[@]}" "$CLAUDE_BIN" -p "$ISCI_TALIMAT_PROMPTU" "${CLAUDE_BAYRAKLAR[@]}" 2>&1 | tee -a "$LOG" "$CIKTI_DOSYASI" "$TUR_CIKTI"',
   'env "${CLAUDE_ENV[@]}" "$CLAUDE_BIN" -p "$ISCI_TALIMAT_PROMPTU" "${CLAUDE_BAYRAKLAR[@]}" 2>&1 | python3 "$CRON_KOKU/isci-hal-cozucu.py" --hal-dosyasi "$HAL_DOSYASI" | tee -a "$LOG" "$CIKTI_DOSYASI" "$TUR_CIKTI"',
   '"$CRON_KOKU/isci-hal-cozucu.py" --hal-dosyasi "$HAL_DOSYASI" | tee -a "$LOG" "$CIKTI_DOSYASI" "$TUR_CIKTI"\nCLAUDE_RC=${pipestatus[1]}\nbekci_durdur',
   "A", "ana cagri cozucuden gecer (pipestatus[1] hala claude'un rc'si)")

_y(ISCI,
   'env "${CLAUDE_ENV[@]}" "$CLAUDE_BIN" -p "$ISCI_TALIMAT_PROMPTU" "${CLAUDE_BAYRAKLAR_2[@]}" 2>&1 | tee -a "$LOG" "$CIKTI_DOSYASI" "$TUR_CIKTI"',
   'env "${CLAUDE_ENV[@]}" "$CLAUDE_BIN" -p "$ISCI_TALIMAT_PROMPTU" "${CLAUDE_BAYRAKLAR_2[@]}" 2>&1 | python3 "$CRON_KOKU/isci-hal-cozucu.py" --hal-dosyasi "$HAL_DOSYASI" | tee -a "$LOG" "$CIKTI_DOSYASI" "$TUR_CIKTI"',
   '"${CLAUDE_BAYRAKLAR_2[@]}" 2>&1 | python3 "$CRON_KOKU/isci-hal-cozucu.py"',
   "A", "tekrar cagrisi da cozucuden gecer")

# --- A2: HAL dosyasi acilir ve trap'e girer ------------------------------
_y(ISCI,
   """BEKCI_CIKTI=$(mktemp "$CRON_KOKU/.bekci-cikti.XXXXXX") || {
  echo "HATA: Bekci cikti dosyasi olusturulamadi" >&2
  exit 2
}
chmod 600 "$BEKCI_CIKTI\"""",
   """BEKCI_CIKTI=$(mktemp "$CRON_KOKU/.bekci-cikti.XXXXXX") || {
  echo "HATA: Bekci cikti dosyasi olusturulamadi" >&2
  exit 2
}
chmod 600 "$BEKCI_CIKTI"

# === K337-HAL-DOSYASI BAS ===
# Turun HALI (CLI subtype'i) buraya yazilir. FAIL-OPEN: acilamazsa tur
# yine kosar, hal OLCULEMEDI olur -- "saglikli" UYDURULMAZ.
HAL_DOSYASI=$(mktemp "$CRON_KOKU/.isci-hal.XXXXXX") || HAL_DOSYASI=
[[ -n "$HAL_DOSYASI" ]] && chmod 600 "$HAL_DOSYASI"
# === K337-HAL-DOSYASI SON ===""",
   "=== K337-HAL-DOSYASI BAS ===",
   "A", "hal durum dosyasi acilir")

_y(ISCI,
   """trap 'rm -f "$CIKTI_DOSYASI" "$BEKCI_CIKTI"; [[ -n "${BEKCI_PID:-}" ]] && kill -TERM "$BEKCI_PID" 2>/dev/null' EXIT HUP INT TERM""",
   """trap 'rm -f "$CIKTI_DOSYASI" "$BEKCI_CIKTI" "${HAL_DOSYASI:-/dev/null}"; [[ -n "${BEKCI_PID:-}" ]] && kill -TERM "$BEKCI_PID" 2>/dev/null' EXIT HUP INT TERM""",
   """rm -f "$CIKTI_DOSYASI" "$BEKCI_CIKTI" "${HAL_DOSYASI:-/dev/null}\"""",
   "A", "hal dosyasi da temizlenir (uretn temizler)")

# --- A3: HAL okunur -------------------------------------------------------
_y(ISCI,
   """# Tur tavani kesildiyse (16 Agu 2026, spec-tur-tavani madde 3.3): kapanis""",
   """# === K337-HAL-OKU BAS ===
# Turun HALI cozucunun yazdigi durum dosyasindan OKUNUR. Dosya yoksa /
# bossa FAIL-CLOSED: OLCULEMEDI (sifir ya da SAGLIKLI uydurulmaz).
TUR_HALI=OLCULEMEDI
if [[ -n "${HAL_DOSYASI:-}" && -s "$HAL_DOSYASI" ]]; then
  TUR_HALI=$(sed -n 's/^HAL=\\([^ ]*\\).*/\\1/p' "$HAL_DOSYASI" | tail -1)
  [[ -z "${TUR_HALI//[[:space:]]/}" ]] && TUR_HALI=OLCULEMEDI
fi
echo "TUR_HALI=$TUR_HALI" >> "$LOG"
# Kapanis cagrisinin KENDI tavani: bir durma noktasi yazmak icin tam
# turun butcesi gerekmez, ve butce kolunda ana tavan ZATEN dolmustur.
KAPANIS_BUTCE_USD="${PRUVO_ISCI_KAPANIS_BUTCE_USD:-2.00}"
# === K337-HAL-OKU SON ===

# Tur tavani kesildiyse (16 Agu 2026, spec-tur-tavani madde 3.3): kapanis""",
   "=== K337-HAL-OKU BAS ===",
   "A", "hal okunur + kapanis cagrisinin kendi tavani")

# --- B: kapanis kolu TEK YORDAM, IKI SEBEP -------------------------------
# 🔴 Blok TASINMADI ve KOPYALANMADI: yalnizca GIRISI genellestirildi, boylece
# ikinci bir kapanis uygulamasi DOGMAZ (kabul bataryasi kopya sayar).
_y(ISCI,
   """if [[ -s "$BEKCI_CIKTI" ]]; then
  SON_BEKCI=$(tail -1 "$BEKCI_CIKTI" 2>/dev/null || echo "")
  if [[ "$SON_BEKCI" == BEKCI=KESTI* && -n "$OTURUM_ID" ]]; then
    KAPANIS_TAVANI=5""",
   """# 🔴 K337 — KAPANIS KOLU: TEK YORDAM, IKI SEBEP.
# ONCEDEN bu blok YALNIZ tur tavani kolunda ateslenirdi; butce
# kesintisinde HIC durma notu uretilmiyordu (taban: 2 kesinti / 0 not).
KAPANIS_HALI=
KAPANIS_SEBEBI=
BEKCI_TUR=
if [[ -s "$BEKCI_CIKTI" ]]; then
  SON_BEKCI=$(tail -1 "$BEKCI_CIKTI" 2>/dev/null || echo "")
  if [[ "$SON_BEKCI" == BEKCI=KESTI* ]]; then
    KAPANIS_HALI=TUR_TAVANI
    KAPANIS_SEBEBI="tur tavani ${TUR_TAVANI} asildi"
    BEKCI_TUR=$(echo "$SON_BEKCI" | sed -n 's/.*tur=\\([0-9]*\\).*/\\1/p')
  fi
  unset SON_BEKCI
fi
if [[ -z "$KAPANIS_HALI" && "$TUR_HALI" == BUTCE_TAVANI ]]; then
  KAPANIS_HALI=BUTCE_TAVANI
  KAPANIS_SEBEBI="butce tavani ${BUTCE_USD} USD doldu"
fi
echo "KAPANIS_KOLU=${KAPANIS_HALI:-yok} hal=$TUR_HALI" >> "$LOG"
# (1) DETERMINISTIK yari: cagri hic kosmasa/dusse bile diskte BAYT>0 not kalir.
if [[ -n "$KAPANIS_HALI" ]]; then
  KAPANIS_NOTU="${TUR_CIKTI%.log}.durma-notu.md"
  [[ "$KAPANIS_NOTU" == "$TUR_CIKTI" ]] && KAPANIS_NOTU="$TUR_CIKTI.durma-notu.md"
  python3 "$CRON_KOKU/isci-durma-notu.py" \\
      --hedef "$KAPANIS_NOTU" --hal "$KAPANIS_HALI" --ev "$EV_KOKU" \\
      --etiket "$ETIKET" --spec "$SPEC_DOSYASI" --oturum "$OTURUM_ID" \\
      --tur-cikti "$TUR_CIKTI" --rc "$CLAUDE_RC" --sure "$SURE" \\
      --butce "$BUTCE_USD" >> "$LOG" 2>&1
  KAPANIS_NOT_RC=$?
  echo "KAPANIS_YORDAMI hal=$KAPANIS_HALI sebep=$KAPANIS_SEBEBI not=$KAPANIS_NOTU not_rc=$KAPANIS_NOT_RC" >> "$LOG"
fi
# (2) LLM yarisi: deterministik notu ZENGINLESTIRIR, YERINE GECMEZ.
if [[ -n "$KAPANIS_HALI" && -n "$OTURUM_ID" ]]; then
    KAPANIS_TAVANI=5""",
   "🔴 K337 — KAPANIS KOLU: TEK YORDAM, IKI SEBEP.",
   "B", "kapanis kolunun GIRISI genellestirilir (iki sebep, tek yordam)")

_y(ISCI,
   'KAPANIS_PROMPTU="Tur tavanina ulasildi, kosum kesildi. YENI IS YAPMA',
   'KAPANIS_PROMPTU="Kosum KESILDI (sebep: $KAPANIS_SEBEBI). Deterministik durma notu $KAPANIS_NOTU dosyasinda duruyor, onu OKU ve TEKRAR ETME. YENI IS YAPMA',
   'KAPANIS_PROMPTU="Kosum KESILDI (sebep: $KAPANIS_SEBEBI).',
   "B", "kapanis promptu sebebi ve deterministik notu tasir")

_y(ISCI,
   'KAPANIS_BAYRAKLAR=(--permission-mode bypassPermissions --max-budget-usd "$BUTCE_USD" -r "$OTURUM_ID")',
   'KAPANIS_BAYRAKLAR=(--permission-mode bypassPermissions --max-budget-usd "$KAPANIS_BUTCE_USD" -r "$OTURUM_ID")',
   '--max-budget-usd "$KAPANIS_BUTCE_USD" -r "$OTURUM_ID")',
   "B", "kapanis cagrisi ana turun tavanini DEGIL kendi tavanini kullanir")

_y(ISCI,
   """    BEKCI_TUR=$(echo "$SON_BEKCI" | sed -n 's/.*tur=\\([0-9]*\\).*/\\1/p')
    echo "TUR_TAVANI_KESTI tur=${BEKCI_TUR:-?} tavan=$TUR_TAVANI kapanis_rc=$KAPANIS_RC" >> "$LOG"
    unset BEKCI_PID_KAPANIS BEKCI_CIKTI_KAPANIS KAPANIS_PROMPTU KAPANIS_BAYRAKLAR KAPANIS_RC KAPANIS_TAVANI BEKCI_TUR
  fi
  unset SON_BEKCI
fi""",
   """    [[ "$KAPANIS_HALI" == TUR_TAVANI ]] && echo "TUR_TAVANI_KESTI tur=${BEKCI_TUR:-?} tavan=$TUR_TAVANI kapanis_rc=$KAPANIS_RC" >> "$LOG"
    echo "KAPANIS_CAGRISI hal=$KAPANIS_HALI kapanis_rc=$KAPANIS_RC" >> "$LOG"
    unset BEKCI_PID_KAPANIS BEKCI_CIKTI_KAPANIS KAPANIS_PROMPTU KAPANIS_BAYRAKLAR KAPANIS_RC KAPANIS_TAVANI
fi
unset KAPANIS_HALI KAPANIS_SEBEBI KAPANIS_NOTU KAPANIS_NOT_RC BEKCI_TUR""",
   'echo "KAPANIS_CAGRISI hal=$KAPANIS_HALI kapanis_rc=$KAPANIS_RC"',
   "B", "kapanis kolunun kapanisi hale gore basilir (eski satir korunur)")

# --- A4: BITIS satiri hali TASIR ------------------------------------------
_y(ISCI,
   'echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) BITIS rc=$CLAUDE_RC sure=$SURE ===" >> "$LOG"',
   'echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) BITIS rc=$CLAUDE_RC sure=$SURE hal=$TUR_HALI ===" >> "$LOG"',
   'BITIS rc=$CLAUDE_RC sure=$SURE hal=$TUR_HALI ===',
   "A", "BITIS satiri butce kesintisini sirаdan rc=1'den AYIRIR")

# --- A5: BUTCE_VURULDU tetigi DIZGEDEN ALINIP HALE baglanir ---------------
_y(ISCI,
   """BUTCE_VURULDU=0
if (( CLAUDE_RC != 0 )) && [[ -s "$CIKTI_DOSYASI" ]] \\
    && grep -Eq 'Exceeded USD budget' "$CIKTI_DOSYASI" 2>/dev/null; then
  BUTCE_VURULDU=1
fi""",
   """# 🔴 K337: bu kolun ESKI tetigi INGILIZCE CUMLEYI (`Exceeded USD
# budget`) okuyordu -- saglayici metni degisince kor kalirdi (K321
# sinifi). Artik CLI'nin KENDI durum adindan (subtype
# `error_max_budget_usd` -> HAL=BUTCE_TAVANI) turer. Dizge kolu
# SILINDI; ikinci kol BIRAKILMADI.
BUTCE_VURULDU=0
if [[ "$TUR_HALI" == BUTCE_TAVANI ]]; then
  BUTCE_VURULDU=1
fi""",
   "🔴 K337: bu kolun ESKI tetigi INGILIZCE CUMLEYI",
   "A", "telemetri tetigi de dizgeden HALE gecer")

# --- C: karantina cagrisi hali TASIR --------------------------------------
_y(ISCI,
   """  KARANTINA_KARAR_CIKTISI=$(python3 "$CRON_KOKU/isci-karantina-karar.py" "$CLAUDE_RC" "$CIKTI_DOSYASI" \\
      "$LOG_MOTOR" "$KARANTINA_DOSYASI" "$KARANTINA_MOTORLAR_REGEX" 2>&1)""",
   """  KARANTINA_KARAR_CIKTISI=$(python3 "$CRON_KOKU/isci-karantina-karar.py" "$CLAUDE_RC" "$CIKTI_DOSYASI" \\
      "$LOG_MOTOR" "$KARANTINA_DOSYASI" "$KARANTINA_MOTORLAR_REGEX" --hal "$TUR_HALI" 2>&1)""",
   '"$KARANTINA_MOTORLAR_REGEX" --hal "$TUR_HALI" 2>&1)',
   "C", "karantina karari turun HALINI de okur")

# --- D: ureten temizler — durma notlari da budanir ------------------------
_y(ISCI,
   """if [[ -d "$TUR_CIKTI_DIZINI" ]]; then
  B7_ESKILER=("$TUR_CIKTI_DIZINI"/*.log(Nom[61,-1]))
  if (( ${#B7_ESKILER} )); then
    rm -f "${B7_ESKILER[@]}"
  fi
  unset B7_ESKILER
fi""",
   """if [[ -d "$TUR_CIKTI_DIZINI" ]]; then
  B7_ESKILER=("$TUR_CIKTI_DIZINI"/*.log(Nom[61,-1]))
  if (( ${#B7_ESKILER} )); then
    rm -f "${B7_ESKILER[@]}"
  fi
  unset B7_ESKILER
  # 🔴 K337-D: durma notlari da ayni tavana tabidir -- yoksa `.md`
  # dosyalari `*.log` budamasinin MENZILI DISINDA sinirsiz birikirdi
  # (Okan disk kurali: makinede iz birakma, ureten temizler).
  K337_ESKI_NOTLAR=("$TUR_CIKTI_DIZINI"/*.durma-notu.md(Nom[61,-1]))
  if (( ${#K337_ESKI_NOTLAR} )); then
    rm -f "${K337_ESKI_NOTLAR[@]}"
  fi
  unset K337_ESKI_NOTLAR
fi""",
   "# 🔴 K337-D: durma notlari da ayni tavana tabidir",
   "D", "durma notlari budanir")

# --- C: karantina karar aracinin kendisi ---------------------------------
_y(KARANTINA,
   "GENEL_ARDISIK_ESIGI = ERISIM_ARDISIK_ESIGI",
   '''GENEL_ARDISIK_ESIGI = ERISIM_ARDISIK_ESIGI

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
BUTCE_KOVASI = "__butce__"


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
    return yeni''',
   "BUTCE_KOVASI = \"__butce__\"",
   "C", "butce kovasi ve okuyucu/yazici")

_y(KARANTINA,
   '''    veri = ardisik_oku(karantina_dosyasi)
    yeni = (int(veri.get(motor) or 0) + 1) if basarisiz else 0
    veri[motor] = yeni
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
    return yeni''',
   '''    veri = ardisik_oku(karantina_dosyasi)
    yeni = (int(veri.get(motor) or 0) + 1) if basarisiz else 0
    veri[motor] = yeni
    # 🔴 K337: saglikli tur BUTCE kovasini da sifirlar -- iki sayac da
    # ayni "iyilesince duser" disiplinine tabidir.
    if not basarisiz:
        kova = veri.get(BUTCE_KOVASI)
        if isinstance(kova, dict) and kova.get(motor):
            kova[motor] = 0
            veri[BUTCE_KOVASI] = kova
    _sayac_yaz(karantina_dosyasi, veri)
    return yeni


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
        raise''',
   "def _sayac_yaz(karantina_dosyasi, veri):",
   "C", "atomik yazici tek kaynaga alinir + saglikli tur butce kovasini sifirlar")

_y(KARANTINA,
   '''def main(argv):
    if len(argv) not in (6, 7):
        sys.stderr.write(
            "Kullanim: isci-karantina-karar.py <rc> <cikti_dosyasi> "
            "<motor> <karantina_dosyasi> <motor_regex> [--kuru]\\n"
        )
        return 2
    rc_str, cikti_yolu, motor, karantina_dosyasi, motor_regex = argv[1:6]
    kuru = (len(argv) == 7 and argv[6] == "--kuru")''',
   '''def main(argv):
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
        sys.stderr.write(
            "Kullanim: isci-karantina-karar.py <rc> <cikti_dosyasi> "
            "<motor> <karantina_dosyasi> <motor_regex> [--kuru] "
            "[--hal <AD>]\\n"
        )
        return 2
    rc_str, cikti_yolu, motor, karantina_dosyasi, motor_regex = argv[1:6]''',
   'bayraklar = argv[6:]',
   "C", "--hal bayragi ayristirilir (eski cagri bicimi korunur)")

_y(KARANTINA,
   '''    karar, sebep = imza_var(rc, cikti_yolu)
    # 🔴 KOL C: ardisik sayac HER kosumda guncellenir (rc==0 SIFIRLAR).
    # Kuru kosumda diske dokunmayiz; sayac yalnizca OKUNUR.''',
   '''    karar, sebep = imza_var(rc, cikti_yolu)
    # 🔴 KOL E (K337): BUTCE TAVANI motor arizasi degildir.
    # Ucuncu kova YALNIZ hal GERCEKTEN BUTCE_TAVANI iken ve rc!=0 iken
    # acilir. `karar` True ise (bilinen KOTA/FATAL imzasi ayrica VAR)
    # butce kolu onu MASKELEMEZ -- normal akisa devam edilir.
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
    # 🔴 KOL C: ardisik sayac HER kosumda guncellenir (rc==0 SIFIRLAR).
    # Kuru kosumda diske dokunmayiz; sayac yalnizca OKUNUR.''',
   "KOL E (K337): BUTCE TAVANI motor arizasi degildir.",
   "C", "butce hali motor sayacini ARTIRMAZ, kendi kovasinda gorunur")


# --------------------------------------------------------------------------
def sha(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(65536), b""):
            h.update(parca)
    return h.hexdigest()


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def kopya_durumu(kok):
    """Repo kanonik YENI dosyalar ile kurulu kopyayi SHA ile karsilastirir."""
    satirlar = []
    esit = 0
    for ad in KOPYALANAN:
        kaynak = os.path.join(REPO_CRON, ad)
        hedef = os.path.join(kok, ad)
        if not os.path.isfile(kaynak):
            satirlar.append("KOPYA %s KAYNAK_YOK" % ad)
            continue
        k_sha = sha(kaynak)
        if not os.path.isfile(hedef):
            satirlar.append("KOPYA %s KURULU_YOK repo_sha=%s" % (ad, k_sha[:12]))
            continue
        h_sha = sha(hedef)
        if k_sha == h_sha:
            esit += 1
            satirlar.append("KOPYA %s ESIT sha=%s bayt=%d"
                            % (ad, k_sha[:12], os.path.getsize(hedef)))
        else:
            satirlar.append("KOPYA %s AYRISTI repo=%s kurulu=%s"
                            % (ad, k_sha[:12], h_sha[:12]))
    return esit, satirlar


def yama_durumu(kok):
    kurulu, eksik, satirlar = 0, 0, []
    icerikler = {}
    for y in YAMALAR:
        yol = os.path.join(kok, y["dosya"])
        if yol not in icerikler:
            try:
                icerikler[yol] = _oku(yol)
            except OSError as e:
                icerikler[yol] = None
                satirlar.append("DOSYA_OKUNAMADI %s (%s)"
                                % (y["dosya"], type(e).__name__))
        metin = icerikler[yol]
        if metin is None:
            eksik += 1
            continue
        n_isaret = metin.count(y["isaret"])
        n_capa = metin.count(y["capa"])
        if n_isaret == 1:
            kurulu += 1
            satirlar.append("YAMA kol=%s %s KURULU (%s)"
                            % (y["kol"], y["dosya"], y["aciklama"]))
        elif n_isaret > 1:
            eksik += 1
            satirlar.append("YAMA kol=%s %s COGALMIS isaret=%d 🔴"
                            % (y["kol"], y["dosya"], n_isaret))
        elif n_capa == 1:
            eksik += 1
            satirlar.append("YAMA kol=%s %s EKSIK (capa yerinde, yama YOK)"
                            % (y["kol"], y["dosya"]))
        else:
            eksik += 1
            satirlar.append("YAMA kol=%s %s CAPA_YOK capa_sayisi=%d 🔴"
                            % (y["kol"], y["dosya"], n_capa))
    return kurulu, eksik, satirlar


def uygula(kok, kuru):
    degisen = []
    hata = []
    # 1) YENI dosyalar: repo -> kurulu (birebir kopya)
    for ad in KOPYALANAN:
        kaynak = os.path.join(REPO_CRON, ad)
        hedef = os.path.join(kok, ad)
        if not os.path.isfile(kaynak):
            hata.append("KAYNAK_YOK %s" % kaynak)
            continue
        varsa_esit = os.path.isfile(hedef) and sha(hedef) == sha(kaynak)
        if varsa_esit:
            continue
        if kuru:
            degisen.append("KOPYALANACAK %s" % ad)
            continue
        if os.path.isfile(hedef):
            shutil.copy2(hedef, hedef + ".yedek-k337-%d" % int(time.time()))
        shutil.copy2(kaynak, hedef)
        os.chmod(hedef, 0o755)
        degisen.append("KOPYALANDI %s sha=%s" % (ad, sha(hedef)[:12]))

    # 2) Yamalar
    dosyalar = sorted({y["dosya"] for y in YAMALAR})
    for dosya in dosyalar:
        yol = os.path.join(kok, dosya)
        try:
            metin = _oku(yol)
        except OSError as e:
            hata.append("OKUNAMADI %s (%s)" % (dosya, type(e).__name__))
            continue
        onceki = metin
        for y in YAMALAR:
            if y["dosya"] != dosya:
                continue
            if metin.count(y["isaret"]) >= 1:
                continue                       # zaten kurulu (idempotens)
            n = metin.count(y["capa"])
            if n != 1:
                hata.append("CAPA_SAYISI kol=%s %s capa=%d (1 bekleniyordu)"
                            % (y["kol"], dosya, n))
                continue
            metin = metin.replace(y["capa"], y["yeni"], 1)
            degisen.append("YAMALANDI kol=%s %s (%s)"
                           % (y["kol"], dosya, y["aciklama"]))
        if metin != onceki and not kuru:
            shutil.copy2(yol, yol + ".yedek-k337-%d" % int(time.time()))
            gecici = yol + ".k337-yeni"
            with open(gecici, "w", encoding="utf-8") as f:
                f.write(metin)
            os.chmod(gecici, os.stat(yol).st_mode & 0o777)
            os.replace(gecici, yol)
    return degisen, hata


def geri_al(kok):
    """En YENI `.yedek-k337-*` kopyasindan yamalanan dosyalari geri yukler.

    🔴 K320 dersi: geri-alma bir YORDAM KUSURUNU MASKELEMEK icin
    kullanilmaz -- idempotens ayrica olculur (kabul vaka 16). Bu kol
    yalniz yamanin KENDISI degistiginde temiz bir taban icindir.
    """
    satirlar = []
    for dosya in sorted({y["dosya"] for y in YAMALAR}):
        yol = os.path.join(kok, dosya)
        yedekler = sorted(
            a for a in os.listdir(kok)
            if a.startswith(dosya + ".yedek-k337-")
        )
        if not yedekler:
            satirlar.append("GERI_ALINAMADI %s YEDEK_YOK" % dosya)
            continue
        kaynak = os.path.join(kok, yedekler[-1])
        shutil.copy2(kaynak, yol)
        satirlar.append("GERI_ALINDI %s <- %s sha=%s"
                        % (dosya, yedekler[-1], sha(yol)[:12]))
    return satirlar


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--kok", default=VARSAYILAN_KOK)
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--durum", action="store_true")
    ap.add_argument("--geri-al", dest="geri_al", action="store_true")
    ns = ap.parse_args()

    kok = os.path.abspath(os.path.expanduser(ns.kok))
    if not os.path.isdir(kok):
        sys.stderr.write("HATA: kok dizin yok: %s\n" % kok)
        return 2

    if ns.geri_al:
        for s in geri_al(kok):
            print("  " + s)
        return 0

    if not ns.durum:
        degisen, hata = uygula(kok, ns.kuru)
        for s in degisen:
            print("  " + s)
        for s in hata:
            print("  🔴 " + s)
        if ns.kuru:
            print("KURU KOSUM (yazilmadi) degisecek=%d hata=%d"
                  % (len(degisen), len(hata)))
            return 0 if not hata else 1

    esit, kopya_satirlari = kopya_durumu(kok)
    kurulu, eksik, yama_satirlari = yama_durumu(kok)
    for s in kopya_satirlari + yama_satirlari:
        print("  " + s)
    print("DURUM kok=%s KOPYA_ESIT=%d/%d YAMA_KURULU=%d EKSIK=%d"
          % (kok, esit, len(KOPYALANAN), kurulu, eksik))
    return 0 if (eksik == 0 and esit == len(KOPYALANAN)) else 1


if __name__ == "__main__":
    sys.exit(main())

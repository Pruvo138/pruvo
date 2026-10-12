#!/bin/zsh
# AGIR-IS KAPISI (13 Eki 2026, BaBa 02:4x hukmu) — agir araclar (Blender `-b`,
# mutant bataryasi, render) isci semaforundan GECER.
#
# NEDEN: 02:30'da Blender `-b` %541 CPU ile semafor DISINDA kostu, 1 dk yuku 37
# oldu. isci-semafor.py yalniz isci.sh'yi kapsiyordu; bu sarmalayici agir isi
# AYNI slot kokune (`~/.claude/cron/isci-slot`) baglar ve makinenin TAMAMINI
# (3 slotun 3'unu) ATOMIK alir: agir is koşarken yeni isci baslamaz, isciler
# koşarken agir is baslamaz.
#
# KULLANIM: agir-is.sh [--etiket X] -- <komut…>
#   * `isci-semafor.py al --adet 3 --yuk-esik 8 --tavan-sn 3600 --satir-sn 120
#     --tur agir` — 1 dk yuku >8 iken ya da slot/sira yoksa BEKLER; 120 sn'de bir
#     isci.log'a `=== .. HAL=BEKLIYOR tur=agir .. etiket=.. sira=.. bekleme_dk=..
#     sebep=slot|yuk|sira yuk=.. ===` satiri.
#   * Tavan (60 dk) -> `HAL=KUYRUK-TAVAN tur=agir` satiri (yardimcidan) + rc=1.
#   * Slot alininca komutu kosar, komutun rc'sini AYNEN doner. EXIT/INT/TERM
#     trap'i slotlari birakir (TERM/INT komuta da iletilir; rc 128+n).
#   * Ic ice: bir isci.sh kosumunun icinden cagrildiysa (PRUVO_ISCI_SEMAFOR_SAHIBI
#     canli) o isci zaten 1 slot tutar; agir is KALAN (SINIR-1) slotu alir —
#     aksi halde isci kendi slotunu bekleyerek tavana kadar kilitlenirdi.
#   * FAIL-OPEN: yardimci yok / ic hata -> `SEMAFOR=OLCULEMEDI` satiri, komut
#     yine kosar (isci.sh ile ayni).
#
# Kaynak: pruvo tools/agir-is.sh · kurulu kopya ~/.claude/cron/agir-is.sh
# BIREBIR · kabul tools/agir-is-test.py (hermetik).
# Test kancalari (yalniz test): AGIR_IS_CRON_KOKU AGIR_IS_SEMAFOR
# AGIR_IS_SLOT_KOKU AGIR_IS_LOG AGIR_IS_ARALIK_SN AGIR_IS_IZLE_SN
# AGIR_IS_SATIR_SN AGIR_IS_TAVAN_SN.

AGIR_CRON_KOKU="${AGIR_IS_CRON_KOKU:-$HOME/.claude/cron}"
AGIR_SEMAFOR="${AGIR_IS_SEMAFOR:-$AGIR_CRON_KOKU/isci-semafor.py}"
AGIR_SLOT_KOKU="${AGIR_IS_SLOT_KOKU:-$AGIR_CRON_KOKU/isci-slot}"
AGIR_LOG="${AGIR_IS_LOG:-$AGIR_CRON_KOKU/isci.log}"
AGIR_SINIR=3
AGIR_YUK_ESIK=8
AGIR_TAVAN_SN="${AGIR_IS_TAVAN_SN:-3600}"
AGIR_SATIR_SN="${AGIR_IS_SATIR_SN:-120}"

ETIKET=etiketsiz
while (( $# )); do
  case "$1" in
    --etiket) ETIKET="$2"; shift 2 ;;
    --etiket=*) ETIKET="${1#--etiket=}"; shift ;;
    --) shift; break ;;
    *) echo "KULLANIM: agir-is.sh [--etiket X] -- <komut…>" >&2; exit 2 ;;
  esac
done
if (( $# == 0 )); then
  echo "KULLANIM: agir-is.sh [--etiket X] -- <komut…>" >&2
  exit 2
fi

AGIR_ADET=$AGIR_SINIR
ICICE=
if [[ "${PRUVO_ISCI_SEMAFOR_SAHIBI:-}" == <-> ]] && kill -0 "$PRUVO_ISCI_SEMAFOR_SAHIBI" 2>/dev/null; then
  AGIR_ADET=$(( AGIR_SINIR - 1 ))
  ICICE=" icice_sahip=$PRUVO_ISCI_SEMAFOR_SAHIBI"
fi

BEKLEYEN_PID=
TUTULUYOR=0
KOMUT_PID=
agir_birak() {
  [[ -n "$BEKLEYEN_PID" ]] && kill -TERM "$BEKLEYEN_PID" 2>/dev/null
  BEKLEYEN_PID=
  if (( TUTULUYOR == 1 )); then
    TUTULUYOR=0
    python3 "$AGIR_SEMAFOR" birak --sahip $$ --slot-koku "$AGIR_SLOT_KOKU" >/dev/null 2>&1
  fi
  return 0
}
agir_sinyal() {   # $1 = sinyal adi, $2 = numara
  [[ -n "$KOMUT_PID" ]] && kill -"$1" "$KOMUT_PID" 2>/dev/null
  agir_birak
  exit $(( 128 + $2 ))
}
trap 'agir_birak' EXIT
trap 'agir_sinyal TERM 15' TERM
trap 'agir_sinyal INT 2' INT

if [[ -f "$AGIR_SEMAFOR" ]]; then
  ek=()
  [[ -n "${AGIR_IS_ARALIK_SN:-}" ]] && ek+=(--aralik-sn "$AGIR_IS_ARALIK_SN")
  [[ -n "${AGIR_IS_IZLE_SN:-}" ]] && ek+=(--izle-sn "$AGIR_IS_IZLE_SN")
  python3 "$AGIR_SEMAFOR" al --sahip $$ --log "$AGIR_LOG" --slot-koku "$AGIR_SLOT_KOKU" \
    --sinir "$AGIR_SINIR" --adet "$AGIR_ADET" --yuk-esik "$AGIR_YUK_ESIK" \
    --tavan-sn "$AGIR_TAVAN_SN" --satir-sn "$AGIR_SATIR_SN" --tur agir \
    --motor agir-is --ev "${PWD:t}" --etiket "$ETIKET" "${ek[@]}" &
  BEKLEYEN_PID=$!
  wait $BEKLEYEN_PID
  SEMAFOR_RC=$?
  BEKLEYEN_PID=
  if (( SEMAFOR_RC == 0 )); then
    TUTULUYOR=1
  elif (( SEMAFOR_RC == 64 )); then
    exit 1   # HAL=KUYRUK-TAVAN tur=agir satiri + stderr yardimcidan
  else
    echo "SEMAFOR=OLCULEMEDI tur=agir rc=$SEMAFOR_RC etiket=$ETIKET$ICICE pid=$$ (fail-open)" >> "$AGIR_LOG"
  fi
else
  echo "SEMAFOR=OLCULEMEDI tur=agir sebep=yardimci-bulunamadi etiket=$ETIKET$ICICE pid=$$ (fail-open)" >> "$AGIR_LOG"
fi

# Arka plan + wait: TERM/INT trap'i komut kosarken HEMEN calisir (slot birakilir).
"$@" <&0 &
KOMUT_PID=$!
wait $KOMUT_PID
KOMUT_RC=$?
KOMUT_PID=
exit $KOMUT_RC

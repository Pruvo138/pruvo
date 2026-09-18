#!/bin/zsh
# PRUVO :07 CI + TAMIRCI nobeti — tek giris noktasi.
#
# 14 Agu 2026 (nobet-onarim-bacagi): tur akisi artik nobet-kapi.py'de.
# Sebep: metin ("DUZELT" + "DAGIT") ZATEN yaziliydi ama zorlayan OLCU yoktu;
# son 7 gunde 167 tur kostu, ONARIM_YAPAN=0, hepsi rc=0 + yesil rapor verdi.
# nobet-kapi.py sirasiyla: H7 kilit -> H5 motor zinciri -> nobet turu (isci.sh)
# -> H4 geri-iz -> H2 fan-out -> H1 tur kabul kapisi (rc!=0 = ONARIMSIZ_TUR).
# Motor/profil/guven kurulumu TEK KAYNAKTA: isci.sh (bu dosyada kopyasi YOK).
# Kabul testi: python3 /Users/okan/.claude/cron/nobet-kabul-test.py
#
# 🔴 19 Agu 2026 — N1 "gozcu kablolama" (Okan emri: "sozde degil ozde calissin").
# ONCE: bu betik crontab'ta `7 * * * *` ile KOSULSUZ tur aciyordu — CI yesil olsa
# da gunde 24 LLM turu. Gozcu (gozcu.py) DOGRU karari 17 Agu'dan beri uretiyordu
# ama TUKETICISI YOKTU.
# SIMDI: once `nobet-tetik.py --karar` kosar (deterministik, SIFIR jeton).
#
# 🔴 28 Agu 2026 — OKAN EMRI: LLM TUR-ACMA KOLU KAPATILDI (cip
# KraL-NobetVeSirKolu-28Agu). Okan: "bensiz calisan, sorun cikarmayan sistem".
# 🔴 BU DOSYANIN IDDIASI DAR: "nobet kapisinin tur cagrisi bu dosyada YOKTUR."
# "LLM turu 0" iddiasi BURADA OLCULMEZ — emrin ENFORCER'i `nobet-kapi.py`
# govdesidir (her cagirani tek bogazdan kapatir: bu betik + `gozcu.py:831,857`).
# Buradaki kaldirma, govde zaten kapatirken islevsiz kalan CAGRININ TEMIZLIGIDIR
# (bir dal eksilir). Ayni iddiayi iki yerde olcen iki test BIRAKILMAZ.
# Tetik + seviye hukmu + loglama AYNEN kalir; tetigin karari
# `tetik_karari=AC|ACMA` alaninda tasinir, `acilan_tur` DAIMA 0'dir.
# 🔴 FAIL-CLOSED'IN KIRMIZI AYAGI DURUR: tetik kapisi BILINMEYEN rc dondururse
# hukum KIRMIZI olur (tur ACILMAZ). "Kapiyi kosamadim" sessizce "yesil" DEMEK
# DEGILDIR.
# Kabul testi: python3 /Users/okan/.claude/cron/nobet-tetik-test.py  (J bolumu bu
# betigi GERCEKTEN kosar ve nobet-kapi cagrilarini SAYAR — iddia degil olcum).
export PATH="/Users/okan/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Yollar env ile ezilebilir — YALNIZ kabul testi icin. Cron'da hicbiri set edilmez.
KOK="${PRUVO_NOBET_KOK:-/Users/okan/.claude/cron}"
LOG="${PRUVO_NOBET_LOG:-$KOK/ci-nobeti.log}"
EV="${PRUVO_NOBET_EV:-/Users/okan/dev/pruvo}"
TETIK="${PRUVO_NOBET_TETIK:-$KOK/nobet-tetik.py}"
KAPI="${PRUVO_NOBET_KAPI:-$KOK/nobet-kapi.py}"

cd "$EV" || exit 1

# 🔴 KOL A4 (27 Agu 2026, cip KraL-NobetTuru-27Agu) — NOBET_HUKUM_KOLU=A4
# Tetigin ciktisi ARTIK YAKALANIR: loga aynen duser (bicim degismedi) ve
# `sebep=` jetonu hukum adina TEK KAYNAK olur. ONCE bu cikti dogrudan loga
# akiyordu; kabuk sebebi HIC gormuyor, rc=11'in BES ayri kolunu tek sabit
# adla ("SEVIYE_KIRMIZI") basiyordu.
TETIK_CIKTISI=$(python3 "$TETIK" --karar 2>&1)
TETIK_RC=$?
if [[ -n "$TETIK_CIKTISI" ]]; then
  printf '%s\n' "$TETIK_CIKTISI" >> "$LOG"
fi
# Son `TUR ACILIYOR/ACILMADI` satirindaki `sebep=` degeri. Birden fazla satir
# varsa (or. once `KALP BAYAT`) SONUNCUSU gecerlidir: karari o satir tasir.
TETIK_SEBEBI=$(printf '%s\n' "$TETIK_CIKTISI" | awk '/^TUR ACIL/ { for (i = 1; i <= NF; i++) if ($i ~ /^sebep=/) { sub(/^sebep=/, "", $i); s = $i } } END { if (s != "") print s }')

# 🔴 KOL HALI kabukta TURETILMEZ, tetigin SATIRINDAN OKUNUR (sart ①: jeton
# literali kabukta YOK). Alan yoksa `OLCULEMEDI` — fail-closed: eski bir tetik
# ya da bozuk bir satir sessizce "ACIK" DEMEZ.
KOL_HALI=$(printf '%s\n' "$TETIK_CIKTISI" | awk '/^TUR ACIL/ { for (i = 1; i <= NF; i++) if ($i ~ /^kol_hali=/) { sub(/^kol_hali=/, "", $i); s = $i } } END { if (s != "") print s }')
KOL_HALI=${KOL_HALI:-OLCULEMEDI}

# Cikis kodu sozlesmesi TEK KAYNAK: nobet-tetik.py RC_* sabitleri.
#   0 = AC/yesil · 1 = AC/KIRMIZI · 10 = ACMA/yesil · 11 = ACMA/KIRMIZI
# 🔴 KOL A (27 Agu 2026, KraL-NobetTuru-27Agu) — NOBET_HUKUM_KOLU=A
# ONCE: `NOBET_RC=0` diye INIT edilir, kapi HIC kosmasa bile `nobet_rc=0`
# BASILIRDI. Okuyan (Okan + mimar) "nobet_rc=0 ama BITIS rc=1" celiskisini
# gordu ve hatta "kirmizi gorunen saglikli hat" hukmu verildi. Iki AYRI
# eksen (tetik kapisi / nobet kapisi) tek satirda ayirt EDILEMIYORDU.
# SIMDI: (1) kosmayan kapi SAYI BASMAZ -> `nobet_rc=KOSMADI`;
#        (2) tur hukmu TEK isimli degerdir ve `SON_RC` ONDAN TURER;
#        (3) her eksen KENDI ADIYLA basilir.
# Degismezlik (kabul bunu civiler): HUKUM=TEMIZ <=> SON_RC=0.
ACILACAK=0
KIRMIZI=0
TETIK_SINIFI=TEMIZ
case $TETIK_RC in
  0)  ACILACAK=1 ;;
  1)  ACILACAK=1; KIRMIZI=1; TETIK_SINIFI=${TETIK_SEBEBI:-TETIK_SEBEBI_OKUNAMADI} ;;
  10) ;;
  11) KIRMIZI=1; TETIK_SINIFI=${TETIK_SEBEBI:-TETIK_SEBEBI_OKUNAMADI} ;;
  *)  ACILACAK=1; KIRMIZI=1; TETIK_SINIFI=TETIK_BILINMEYEN_RC
      echo "UYARI: TETIK KAPISI BILINMEYEN rc=$TETIK_RC — FAIL-CLOSED: hukum KIRMIZI (LLM tur kolu KAPALI, tur ACILMAZ)." >> "$LOG" ;;
esac

# 🔴 CAGRI YERI KALDIRILDI — OKAN EMRI, 28 Agu 2026
# (cip KraL-NobetVeSirKolu-28Agu). ONCE burada `if (( ACILACAK ))` kolu vardi ve
# tetigin "AC" karari bir LLM turu ACIYORDU. 🔴 O ZAMAN "tek cagri yeri" sanildi;
# OLCULDU, DEGILMIS: `gozcu.py:831,857` de `nobet-kapi --tur` cagiriyor. Emrin
# ENFORCER'i bu yuzden govdededir (`nobet-kapi.py`); burasi yalnizca artik
# islevsiz kalan CAGRIYI kaldirir. Okan: "bensiz calisan, sorun cikarmayan sistem".
# SIMDI: tetik AYNEN kosar, ciktisi AYNEN loga duser, sebep ayiklama ve rc
# siniflamasi (0/1/10/11/bilinmeyen) DEGISMEDI — ama bu hat tur ACMAZ.
# Tetigin karari KAYBOLMAZ: `tetik_karari=AC|ACMA` alani onu tasir.
# `acilan_tur` ise DAIMA 0'dir; bu alan bir IDDIADIR ve kabul onu GERCEKTEN
# sayilan cagri ile KIYASLAR (parite) — beklenti elle yazilmaz, TURETILIR.
# Kabul (YALNIZ cagri yeri ekseni): nobet-tetik-test.py J7 (cagriyi SAYAR) +
#        tools/nobet-uc-kol-kabul.py A10 + mutant M-A5-cagri-yeri-geri-kondu.
# 🔴 "KOSMADI" bir SAYI DEGILDIR: kosmayan kapinin rc'si YOKTUR, 0 DEGILDIR.
NOBET_RC=KOSMADI
if (( ACILACAK )); then TETIK_KARARI=AC; else TETIK_KARARI=ACMA; fi
ACILAN_TUR=0

# TEK HUKUM. `ONARIMSIZ_TUR` kolu KALDIRILDI: kapi hic kosmadigi icin o kol
# ERISILEMEZ hale geldi, ve erisilemeyen kol bir bakim noktasidir.
if (( KIRMIZI )); then
  HUKUM=$TETIK_SINIFI
  SON_RC=1
else
  HUKUM=TEMIZ
  SON_RC=0
fi

# 🔴 BITIS SATIRININ BICIMI SOZLESMEDIR — tuketici `tools/t1-kiyas.py:34`
# (`_RE_ESKI_BITIS`) `BITIS` ile `rc=<n>` arasinda BASKA ALAN OLMAMASINI ve
# `rc=<n>`den sonra dogrudan `===` gelmesini bekler. Yeni alanlar araya konunca
# desen eslesmiyor ve tuketici "eski hat hic kosmadi" diyor: KIRMIZI YANMAZ,
# SAYI SIFIRLANIR. Bu yuzden teshis alanlari AYRI SATIRA yazilir (t1-kiyas o
# satirlari zaten BITIS'in bolgesi icinde okur). Kabul: nobet-tetik-test.py J5.
echo "TETIK_HUKMU tetik_rc=$TETIK_RC acilan_tur=$ACILAN_TUR nobet_rc=$NOBET_RC hukum=$HUKUM tetik_karari=$TETIK_KARARI kol_hali=$KOL_HALI" >> "$LOG"
# Tek satirlik makine hukmu — Okan'in kabul olcutu ("HUKUM=TEMIZ ve rc=0")
# bu satirla BITIS satiri arasindaki BLOKTAN okunur; logdaki elle yazilmis
# HUKUM= satirlari bu bloga giremez.
echo "HUKUM=$HUKUM" >> "$LOG"
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) BITIS rc=$SON_RC ===" >> "$LOG"
if (( SON_RC != 0 )); then
  echo "UYARI: Tur KIRMIZI (seviye kirmizi / gozcu turu URETMEDI / tetik kapisi okunamadi); olculemedi != yesil." >> "$LOG"
fi
exit $SON_RC

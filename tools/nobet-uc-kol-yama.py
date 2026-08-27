#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K320 — NOBET HATTI UC KOL YAMASI (27 Agu 2026, cip KraL-NobetTuru-27Agu).

Okan'in 27 Agu 15:10 emrinin 3. kalemi + mimarin ayni hatta olctugu kor nokta.
Hedef dosyalar `~/.claude/cron/` altindadir (repoda KOPYASI YOKTUR); bu yuzden
yama repoda YASAR, kurulu kopyaya UYGULANIR ve olcum KURULU KOPYADAN yapilir
([[emir-canliligi-kurulu-kopyadan-olculur]]).

--------------------------------------------------------------------------
OLCULEN VAKA (iddia degil; 27 Agu 2026, canli dosyalardan okundu)
--------------------------------------------------------------------------
`ci-nobeti.log` 00:07-12:07 arasi 13 ardisik saat `BITIS rc=1`, hepsinde:
    TUR ACILMADI sebep=GOZCU_URETMEDI_OLCULEMEDI KIRMIZI=1
    TETIK_HUKMU tetik_rc=11 acilan_tur=0 nobet_rc=0      <-- rc=1 ile CELISIR
Zincir (her halkasi tek tek okundu):
  1. Okan 26 Agu DONDURMA emri -> `nobet-kapi.py:2052` `_dondu=True`
     -> `dagitilan` YAPISAL olarak 0.
  2. `tur_hukmu()` (nobet-kapi.py:1005) "acik kalem var + dagitilan 0" halini
     KOSULSUZ `ONARIMSIZ_TUR/rc=1` sayar. Rapora 26 Agu'dan beri yazilan
     `DONDURMA_ISIRDI=1` satirinin TUKETICISI YOKTUR (yazan=1 okuyan=0).
     -> EMIR, hattin kendi arizasi gibi puanlanir.
  3. `nobet-kapi.py main() --tur-kapat` (2390) YALNIZ `rapor`u basar;
     `KOSUM_HUKMU=` jetonunu HIC basmaz. Jeton `--tur` yolunda (2329) ve
     `_tur_dustu`ta (1957) var, `--tur-kapat` yolunda YOK.
  4. `gozcu.py:818-820` DEFTER_DAGITIM turunda tam da `--tur-kapat`i kosar ve
     ciktida `KOSUM_HUKMU=` ARAR -> bulamaz -> fail-closed `OLCULEMEDI`.
     Yani "okuyan var, YAZAN yok" -- (2)nin aynasi.
  5. `uretken_mi()` beyaz listesi OLCULEMEDI'yi uretken saymaz -> gozcu rc=1.
  6. `nobet-tetik.py:236` -> `GOZCU_URETMEDI_OLCULEMEDI` + kirmizi -> rc=11.
  7. `ci-nobeti.sh` rc=11'i `KIRMIZI=1` yapar, ama `NOBET_RC` 0'da INIT kalir
     (kapi HIC kosmadi) ve `nobet_rc=0` diye BASILIR -> okuyan "saglikli hat
     neden kirmizi?" der. Iki AYRI eksen tek satirda karisir.

🔴 Bu 13 saatin HICBIRI `motor=claude` katiyla ilgili DEGILDIR: ayni desen dun
11:07/12:07'de ve bugun 00:07'den beri, ilk `motor=claude` dususunden (09:07)
SAATLER ONCE vardir.

--------------------------------------------------------------------------
UC KOL
--------------------------------------------------------------------------
A) rc ile HUKUM CELISMEZ  (ci-nobeti.sh)
   - `nobet_rc` KOSMAYAN kapi icin SAYI BASMAZ -> `KOSMADI`.
   - Tur hukmu TEK isimli degerden turer (`HUKUM=`), `SON_RC` o hukumden
     TURETILIR. `HUKUM=TEMIZ` <=> `rc=0` degismezligi kabulle civilenir.
   - Iki eksen (tetik / nobet-kapi) AYRI ADLARLA basilir.
B) `icra_hal=KOSTU_DUSTU` SEBEBI ADIYLA BASILIR  (nobet-kapi.py + gozcu.py)
   - B1 `tur_hukmu` UCUNCU KOVA: bayrak ISIRDIYSA `DAGITIM_DONDURULDU/rc=0`.
     ISIRMADIYSA (ADAY=0) eski `ONARIMSIZ_TUR/rc=1` AYNEN durur -> gevsetme YOK.
   - B2 cagri yeri `DONDURMA_ISIRDI` bilgisini GECIRIR (satirin tuketicisi).
   - B3 `--tur-kapat` kendi `KOSUM_HUKMU=` jetonunu BASAR.
   - B4 `gozcu.py` dusen icranin sebebini `icra_sebep` olarak ADIYLA kaydeder;
     `OLCULEMEDI` bir sebep DEGIL, olcum eksikligidir -> menzil daraltilir.
C) KARANTINA OLCUTU MESAJI DA OKUR  (isci-karantina-karar.py)
   - Bugun 13 ardisik `motor=claude rc=1` koşumunun TAMAMINDA
     `yazildi=hayir sebep=fatal-satir-yok` basildi; ekranda duran metin:
       "Your organization has disabled Claude subscription access for Claude
        Code . Use an Anthropic API key instead, or ask your admin to enable
        access"
     `FATAL_RE` `API Error: ...401|402|403|429` ister, `KOTA_RE` kota ifadesi
     ister; bu metinde IKISI DE YOK -> tek kayit yazilmadi.
   - Cozum: ERISIM/YETKI reddi AYRI bir taninan imza olur, ve YANLIS POZITIF
     olmasin diye ARDISIK esige baglanir (tek seferlik rc!=0 karantina URETMEZ).
D) IMZA TANINMASA DA ARDISIK ESIK YAZAR  (isci-karantina-karar.py)
   - 🔴 27 Agu 2026 MIMAR HUKMU. Kol C yalniz BILINEN imzalari tanir; C'nin
     ilk surumu bunun yanina "taninmayan metin ASLA yazmaz" diye bir KONTROL
     koymustu. O kontrol, ayni gun OLCULEN korlugu KURAL HALINE getiriyordu
     (13 ardisik `rc=1`, hepsinde `sebep=fatal-satir-yok`, sifir kayit).
   - Kural IKI YONLUDUR: TEK seferlik taninmayan dusus YAZMAZ; ESIK kez
     ARDISIK taninmayan dusus YAZAR ve sebep ADIYLA gecer
     (`ardisik-basarisiz-imzasiz<n>`).
   - Esik `GENEL_ARDISIK_ESIGI`dir ve TEK KAYNAKTAN turer
     (`= ERISIM_ARDISIK_ESIGI`); ne vakaya ne yamaya SAYI kopyalanir.
   - Bu kol 27 Agu'da kurulu kopyaya ELLE kondu, repoda tasiyicisi YOKTU;
     D0/D0b/D1 kalemleri o boslugu kapatir (idempotent, iki yonlu).

Kullanim:
    python3 tools/nobet-uc-kol-yama.py --kuru     # yazmadan farki basar
    python3 tools/nobet-uc-kol-yama.py            # uygular (yedekle)
    python3 tools/nobet-uc-kol-yama.py --durum    # kurulu kopya yamali mi
    python3 tools/nobet-uc-kol-yama.py --kok DIZIN --durum   # baska agac
Cikis: 0 = tum kollar KURULU · 1 = eksik/duşen · 2 = arac hatasi.
"""

import argparse
import os
import shutil
import sys
import time

VARSAYILAN_KOK = os.environ.get("PRUVO_NOBET_KOK") or os.path.join(
    os.path.expanduser("~"), ".claude", "cron")

CRON = VARSAYILAN_KOK
SH = KAPI = GOZCU = KARANTINA = None


def kok_ayarla(kok):
    """Yamanin uygulanacagi KOKU ve dort hedef adini yeniden baglar.

    `--kok` (27 Agu 2026): kabul bataryasiyla AYNI eksen. Hermetik bir
    kopyaya uygulayip olcebilmek icin gerekli; bayraksiz davranis
    DEGISMEZ (kurulu kopya)."""
    global CRON, SH, KAPI, GOZCU, KARANTINA
    CRON = kok
    SH = os.path.join(CRON, "ci-nobeti.sh")
    KAPI = os.path.join(CRON, "nobet-kapi.py")
    GOZCU = os.path.join(CRON, "gozcu.py")
    KARANTINA = os.path.join(CRON, "isci-karantina-karar.py")


kok_ayarla(VARSAYILAN_KOK)


# ==========================================================================
# KOL A — ci-nobeti.sh
# ==========================================================================
A_CAPA = '''ACILACAK=0
KIRMIZI=0
case $TETIK_RC in
  0)  ACILACAK=1 ;;
  1)  ACILACAK=1; KIRMIZI=1 ;;
  10) ;;
  11) KIRMIZI=1 ;;
  *)  ACILACAK=1; KIRMIZI=1
      echo "UYARI: TETIK KAPISI BILINMEYEN rc=$TETIK_RC — FAIL-CLOSED: tur ACILIYOR, hukum KIRMIZI." >> "$LOG" ;;
esac

NOBET_RC=0
if (( ACILACAK )); then
  python3 "$KAPI" --tur >> "$LOG" 2>&1
  NOBET_RC=$?
fi

SON_RC=$NOBET_RC
if (( KIRMIZI )) && (( SON_RC == 0 )); then
  SON_RC=1
fi
'''

A_YENI = '''# 🔴 KOL A (27 Agu 2026, KraL-NobetTuru-27Agu) — NOBET_HUKUM_KOLU=A
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
  1)  ACILACAK=1; KIRMIZI=1; TETIK_SINIFI=TETIK_KIRMIZI ;;
  10) ;;
  11) KIRMIZI=1; TETIK_SINIFI=SEVIYE_KIRMIZI ;;
  *)  ACILACAK=1; KIRMIZI=1; TETIK_SINIFI=TETIK_BILINMEYEN_RC
      echo "UYARI: TETIK KAPISI BILINMEYEN rc=$TETIK_RC — FAIL-CLOSED: tur ACILIYOR, hukum KIRMIZI." >> "$LOG" ;;
esac

# 🔴 "KOSMADI" bir SAYI DEGILDIR: kosmayan kapinin rc'si YOKTUR, 0 DEGILDIR.
NOBET_RC=KOSMADI
NOBET_KIRMIZI=0
if (( ACILACAK )); then
  python3 "$KAPI" --tur >> "$LOG" 2>&1
  NOBET_RC=$?
  if (( NOBET_RC != 0 )); then KOL_A_NOBET_KIRMIZI=1; NOBET_KIRMIZI=1; fi
fi

# TEK HUKUM. Agirlik sirasi: kosan kapinin dususu > tetik ekseninin kirmizisi.
if (( NOBET_KIRMIZI )); then
  HUKUM=ONARIMSIZ_TUR
  SON_RC=$NOBET_RC
elif (( KIRMIZI )); then
  HUKUM=$TETIK_SINIFI
  SON_RC=1
else
  HUKUM=TEMIZ
  SON_RC=0
fi
'''

A_CAPA2 = '''echo "TETIK_HUKMU tetik_rc=$TETIK_RC acilan_tur=$ACILACAK nobet_rc=$NOBET_RC" >> "$LOG"
'''

# ==========================================================================
# KOL A4 — HUKUM ADI TETIGIN KENDI `sebep=` JETONUNDAN TURER
# ==========================================================================
# OLCULEN VAKA (ci-nobeti.log, 27 Agu 2026 13:07Z-20:07Z, sekiz ardisik tur):
#   yedi tur `tetik_rc=11` verdi. Bu yedinin ic dagilimi:
#       sebep=ESKALASYON_ACIK            5 tur (13:07 14:07 16:07 18:07 19:07)
#       sebep=GOZCU_URETMEDI_OLCULEMEDI  1 tur (17:07)
#       sebep=SEVIYE_KIRMIZI_2           1 tur (20:07)
#   ve YEDISI DE `HUKUM=SEVIYE_KIRMIZI` basti.
# KOK NEDEN: `TETIK_SINIFI` rc=11 icin SABIT yaziliydi, ve o sabit rc=11
# ureten BES kolun (`GOZCU_URETMEDI_*`, `ESKALASYON_ACIK`, `SEVIYE_KIRMIZI_n`,
# `SEVIYE_OLCULEMEDI`, `OLCULEMEDI`) YALNIZ BIRININ adiydi. Kabuk tarafinda
# rc -> ad sozlugu vardi, ama sozluk `nobet-tetik.py`nin kol kumesiyle
# ESLESMIYORDU; ikisi sessizce ayristi ([[ayni-alan-iki-hukum-biri-sessiz]]).
# OLCULEN ZARAR: okuyan `HUKUM=SEVIYE_KIRMIZI` adini gorup adin isaret ettigi
# alani (kalpteki `kirmizi_toplam`) dogruladi, tutmayinca "kalp `eskalasyon_acik=0`
# diyor ama hat kirmizi -- iki duzlem birbirini yalanliyor" hukmu verildi.
# Yalanlayan DUZLEM DEGILDI, ADDI ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]],
# [[ad-iki-rolde-mutanti-golgeler]]).
# SIMDI: ad TEK KAYNAKTAN okunur -- tetigin KENDI bastigi `sebep=` jetonundan.
# Kabukta guncellenecek sozluk YOKTUR; `nobet-tetik.py`ye yeni bir kol eklenince
# adi kendiliginden dogru basilir.
# IKI EKSEN AYRI KALIR: `tetik_rc` (0/1/10/11) KAPALI SINIF kumesidir ve
# gruplama/sayim onun uzerinden yapilir; `HUKUM` ATESLEYEN KOLUN ADIDIR.
# FAIL-CLOSED: `sebep=` okunamazsa ad `TETIK_SEBEBI_OKUNAMADI`dir. Sessizce
# eski sabite DUSULMEZ -- dusulseydi korluk tam olarak geri gelirdi.
A4_CAPA = '''python3 "$TETIK" --karar >> "$LOG" 2>&1
TETIK_RC=$?
'''

A4_YENI = '''# 🔴 KOL A4 (27 Agu 2026, cip KraL-NobetTuru-27Agu) — NOBET_HUKUM_KOLU=A4
# Tetigin ciktisi ARTIK YAKALANIR: loga aynen duser (bicim degismedi) ve
# `sebep=` jetonu hukum adina TEK KAYNAK olur. ONCE bu cikti dogrudan loga
# akiyordu; kabuk sebebi HIC gormuyor, rc=11'in BES ayri kolunu tek sabit
# adla ("SEVIYE_KIRMIZI") basiyordu.
TETIK_CIKTISI=$(python3 "$TETIK" --karar 2>&1)
TETIK_RC=$?
if [[ -n "$TETIK_CIKTISI" ]]; then
  printf '%s\\n' "$TETIK_CIKTISI" >> "$LOG"
fi
# Son `TUR ACILIYOR/ACILMADI` satirindaki `sebep=` degeri. Birden fazla satir
# varsa (or. once `KALP BAYAT`) SONUNCUSU gecerlidir: karari o satir tasir.
TETIK_SEBEBI=$(printf '%s\\n' "$TETIK_CIKTISI" | awk '/^TUR ACIL/ { for (i = 1; i <= NF; i++) if ($i ~ /^sebep=/) { sub(/^sebep=/, "", $i); s = $i } } END { if (s != "") print s }')
'''

A4B_CAPA = '''  1)  ACILACAK=1; KIRMIZI=1; TETIK_SINIFI=TETIK_KIRMIZI ;;
  10) ;;
  11) KIRMIZI=1; TETIK_SINIFI=SEVIYE_KIRMIZI ;;
'''

A4B_YENI = '''  1)  ACILACAK=1; KIRMIZI=1; TETIK_SINIFI=${TETIK_SEBEBI:-TETIK_SEBEBI_OKUNAMADI} ;;
  10) ;;
  11) KIRMIZI=1; TETIK_SINIFI=${TETIK_SEBEBI:-TETIK_SEBEBI_OKUNAMADI} ;;
'''

A_YENI2 = '''echo "TETIK_HUKMU tetik_rc=$TETIK_RC acilan_tur=$ACILACAK nobet_rc=$NOBET_RC hukum=$HUKUM" >> "$LOG"
# Tek satirlik makine hukmu — Okan'in kabul olcutu ("HUKUM=TEMIZ ve rc=0")
# bu satirla BITIS satiri arasindaki BLOKTAN okunur; logdaki elle yazilmis
# HUKUM= satirlari bu bloga giremez.
echo "HUKUM=$HUKUM" >> "$LOG"
'''


# ==========================================================================
# KOL B — nobet-kapi.py (B1,B2,B3) + gozcu.py (B4)
# ==========================================================================
B1_CAPA = '''def tur_hukmu(acik_kalem, kapanan, dagitilan, tasinan=0, mevcut_hukum=None):
    """H1 + 15 Agu supurme kapisi: sessiz yesil bir daha mumkun degil."""
    onarim = kapanan + dagitilan
    if acik_kalem > 0 and kapanan == 0 and dagitilan == 0:
        rc, hukum = 1, "ONARIMSIZ_TUR"
    elif acik_kalem == 0:
        rc, hukum = 0, "TEMIZ"
    else:
        rc, hukum = 0, "ONARIM_ILERLIYOR"
    # Model turunun olctugu ARIZA hukmu kapinin daha sonraki eksenlerince EZILMEZ.
    if (mevcut_hukum or "").startswith("ARIZA"):
        return 1, mevcut_hukum
    # ONARIMSIZ_SUPURME, ONARIMSIZ_TUR'dan agirdir; gercek bir ARIZA/agir hukum
    # varsa onu EZMEZ. Bilinmeyen hukumler de hafif varsayilmaz (fail-closed).
    hafif_hukumler = {"ONARIMSIZ_TUR", "TEMIZ", "ONARIM_ILERLIYOR"}
'''

B1_YENI = '''def tur_hukmu(acik_kalem, kapanan, dagitilan, tasinan=0, mevcut_hukum=None,
              dondurma_isirdi=False):
    """H1 + 15 Agu supurme kapisi: sessiz yesil bir daha mumkun degil.

    🔴 KOL B1 (27 Agu 2026, KraL-NobetTuru-27Agu) — UCUNCU KOVA.
    OLCULDU: Okan'in 26 Agu DONDURMA emri `dagitilan`i YAPISAL olarak 0'da
    tutuyor; bu kol ise "acik kalem var + hicbir sey dagitilmadi" halini
    KOSULSUZ `ONARIMSIZ_TUR/rc=1` sayiyordu. Sonuc: 27 Agu 00:07-12:07 arasi
    13 ardisik saat `BITIS rc=1` -- hicbiri gercek ariza degil, hepsi EMRIN
    KENDISI. "Emirle dagitmadi" ile "dagitacakti, DAGITAMADI" AYNI KOVAYA
    giremez ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).

    `DONDURMA_ISIRDI=1` satiri 26 Agu'dan beri rapora YAZILIYORDU; uretimde
    OKUYAN YOKTU (`yazan=1 okuyan=0` -> [[kapinin-menzili-cagri-yeridir]]).
    `dondurma_isirdi` parametresi o satirin TUKETICISIDIR.

    🔴 GEVSETME DEGIL: bayrak ISIRMADIYSA (`ADAY=0` -- ortada dagitilacak
    kalem zaten yoktu) eski hukum AYNEN durur ve tur KIRMIZI kapanir. Kabul
    bataryasinin KONTROL vakasi tam olarak budur.
    """
    onarim = kapanan + dagitilan
    if acik_kalem > 0 and kapanan == 0 and dagitilan == 0:
        if dondurma_isirdi:
            rc, hukum = 0, "DAGITIM_DONDURULDU"
        else:
            rc, hukum = 1, "ONARIMSIZ_TUR"
    elif acik_kalem == 0:
        rc, hukum = 0, "TEMIZ"
    else:
        rc, hukum = 0, "ONARIM_ILERLIYOR"
    # Model turunun olctugu ARIZA hukmu kapinin daha sonraki eksenlerince EZILMEZ.
    if (mevcut_hukum or "").startswith("ARIZA"):
        return 1, mevcut_hukum
    # ONARIMSIZ_SUPURME, ONARIMSIZ_TUR'dan agirdir; gercek bir ARIZA/agir hukum
    # varsa onu EZMEZ. Bilinmeyen hukumler de hafif varsayilmaz (fail-closed).
    # 🔴 DAGITIM_DONDURULDU da HAFIFTIR: dondurma emri, "onarmadan alarm
    # kanalini susturma" (ONARIMSIZ_SUPURME) kapisini KALDIRMAZ -- o kapi
    # dondurma altinda da ISIRMALIDIR.
    hafif_hukumler = {"ONARIMSIZ_TUR", "TEMIZ", "ONARIM_ILERLIYOR",
                      "DAGITIM_DONDURULDU"}
'''

B2_CAPA = '''    rc, hukum = tur_hukmu(acik, kapanan, dagitilan, tasinan=tasinan,
                          mevcut_hukum=mevcut_hukum)
'''

B2_YENI = '''    # 🔴 KOL B2: `DONDURMA_ISIRDI=1` satirinin TUKETICISI. Bayrak yalniz
    # GERCEKTEN engelledi ise (aday>0) hukum ucuncu kovaya duser.
    _dondurma_isirdi = bool(_dondu and _aday)
    rc, hukum = tur_hukmu(acik, kapanan, dagitilan, tasinan=tasinan,
                          mevcut_hukum=mevcut_hukum,
                          dondurma_isirdi=_dondurma_isirdi)
'''

B3_CAPA = '''    if args.tur_kapat:
        sonuc = tur_kapat()
        print(sonuc["rapor"])
        return sonuc["rc"]
'''

B3_YENI = '''    if args.tur_kapat:
        sonuc = tur_kapat()
        print(sonuc["rapor"])
        # 🔴 KOL B3 (27 Agu 2026): bu yol `KOSUM_HUKMU=` jetonunu HIC
        # basmiyordu. Jeton `--tur` yolunda (kosum hukmu satiri) ve
        # `_tur_dustu`ta VARDI, burada YOKTU. `gozcu.py` DEFTER_DAGITIM
        # turunda tam da bu yolu kosar ve ciktida o jetonu ARAR; bulamayinca
        # fail-closed `OLCULEMEDI` yazar ve tur KIRMIZI kapanir.
        # "Okuyan var, YAZAN yok" -- olcum eksikligi, ariza DEGIL.
        # Fail-closed korunur: rc!=0 iken jeton ASLA TEMIZ olmaz.
        print("KOSUM_HUKMU=%s MOTOR_RC=- TUR_HUKMU=%s" % (
            "TEMIZ" if sonuc["rc"] == 0 else "DAGITIM_BACAGI_DUSTU",
            sonuc.get("hukum") or "-"))
        sys.stdout.flush()
        return sonuc["rc"]
'''

B4_CAPA = '''_TUR_HALI_DESENI = re.compile(r"(?<![A-Za-z0-9_])TUR_HALI\\s*=\\s*([A-Z_]+)")
'''

B4_YENI = '''_TUR_HALI_DESENI = re.compile(r"(?<![A-Za-z0-9_])TUR_HALI\\s*=\\s*([A-Z_]+)")

# 🔴 KOL B4 (27 Agu 2026, KraL-NobetTuru-27Agu)
# `icra_hal=KOSTU_DUSTU` kalbe yaziliyordu ama SEBEBI hicbir yere
# yazilmiyordu: `icra_cikti` yakalanip ATILIYOR ([[gozcu.py]] `tur_kosucu`
# ciktisi yalniz jeton taramasinda kullaniliyordu). Okuyan elinde tek
# "sebep" olarak `OLCULEMEDI` kaliyordu -- ki o bir SEBEP DEGIL, olcum
# EKSIKLIGIDIR. Bu kol menzili daraltir: dusen icranin hukmu, sureç rc'si
# ve son anlamli satirin imzasi ADIYLA kaydedilir.
_ICRA_HUKUM_DESENI = re.compile(r"(?<![A-Za-z0-9_])HUKUM\\s*=\\s*([A-Z][A-Z0-9_]*)")


def icra_sebebini_ayikla(icra_hal, icra_rc, cikti, tavan=80):
    """(sebep_str) — dusen icranin sebebi ADIYLA.

    Sira: (1) ciktidaki SON makine `HUKUM=` degeri; (2) yoksa son bos
    olmayan satirin kisaltilmis imzasi. Ikisi de yoksa `CIKTI_BOS`.
    Hicbir kolda cikplak `OLCULEMEDI` DONMEZ -- her hal bir MENZIL bildirir.
    """
    if icra_hal != "KOSTU_DUSTU":
        return "-"
    metin = cikti or ""
    eslesme = _ICRA_HUKUM_DESENI.findall(metin)
    if eslesme:
        return "HUKUM=%s rc=%s" % (eslesme[-1], icra_rc)
    satirlar = [s.strip() for s in metin.splitlines() if s.strip()]
    if not satirlar:
        return "CIKTI_BOS rc=%s" % (icra_rc,)
    imza = satirlar[-1]
    if len(imza) > tavan:
        imza = imza[:tavan] + "..."
    return "SON_SATIR=%r rc=%s" % (imza, icra_rc)
'''

B4B_CAPA = '''    if icra_hal == "KOSTU_DUSTU":
        rc = max(rc, 1)
'''

B4B_YENI = '''    # 🔴 KOL B4: dusen icranin sebebi ADIYLA hesaplanir (kalbe + insan satirina).
    icra_sebep = icra_sebebini_ayikla(icra_hal, icra_rc, icra_cikti)
    if icra_hal == "KOSTU_DUSTU":
        rc = max(rc, 1)
'''

B4C_CAPA = '''        "icra_hal": icra_hal,      # B6: uc hal UC deger
'''

B4C_YENI = '''        "icra_hal": icra_hal,      # B6: uc hal UC deger
        "icra_sebep": icra_sebep,  # KOL B4: KOSTU_DUSTU'nun SEBEBI, adiyla
'''

B4D_CAPA = '''            "TESLIM_KANCA=%s TESLIM_KALP=%.1fh TESLIM_OLU=%s") % (
'''

B4D_YENI = '''            "TESLIM_KANCA=%s TESLIM_KALP=%.1fh TESLIM_OLU=%s "
            "ICRA_HAL=%s ICRA_SEBEP=%s") % (
'''

# 🔴 B4d format dizgesine IKI yeni `%s` ekler; ARGUMAN listesi de AYNI yamada
# uzatilmalidir, yoksa `kalp_satiri` TypeError ile duser. Iki capa TEK yamada
# tutulmaz (ayri konumlar) ama ikisi de zorunludur: biri gecip digeri
# duserse `--durum` EKSIK gosterir ve kabul bataryasi B4-2 vakasinda kirmizi
# yanar ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
B4E_CAPA = '''        kalp.get("bekci_teslim_olu") or "-",
    )
'''

B4E_YENI = '''        kalp.get("bekci_teslim_olu") or "-",
        kalp.get("icra_hal") or "-",
        kalp.get("icra_sebep") or "-",
    )
'''


# ==========================================================================
# KOL C — isci-karantina-karar.py
# ==========================================================================
C_CAPA = '''KOTA_RE = re.compile(
    r'(usage limit|quota exceeded|rate limit|insufficient balance|'
    r'too many requests|rate_limit_error|permission_error)',
    re.IGNORECASE,
)
'''

C_YENI = '''KOTA_RE = re.compile(
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


def _sayac_yolu(karantina_dosyasi):
    return karantina_dosyasi + ".ardisik.json"


def ardisik_oku(karantina_dosyasi):
    try:
        with open(_sayac_yolu(karantina_dosyasi), encoding="utf-8") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        return {}


def ardisik_guncelle(karantina_dosyasi, motor, basarisiz):
    """Motorun ardisik basarisizlik sayacini atomik gunceller ve YENI degeri doner.

    `basarisiz=False` (rc==0) sayaci SIFIRLAR -- motor iyilesince esik
    kendiliginden duser ([[silme-sayaci-diskten-dogrulanmali]]).
    """
    veri = ardisik_oku(karantina_dosyasi)
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
    return yeni


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
'''

C2_CAPA = '''import os
import re
import sys
import tempfile
import time
'''

C2_YENI = '''import json
import os
import re
import sys
import tempfile
import time
'''

C3_CAPA = '''    karar, sebep = imza_var(rc, cikti_yolu)
    if not karar:
        print(
            "KARANTINA_KARAR motor=%s rc=%d imza=yok yazildi=hayir sebep=%s"
            % (motor, rc, sebep)
        )
        return 10
'''

C3_YENI = '''    karar, sebep = imza_var(rc, cikti_yolu)
    # 🔴 KOL C: ardisik sayac HER kosumda guncellenir (rc==0 SIFIRLAR).
    # Kuru kosumda diske dokunmayiz; sayac yalnizca OKUNUR.
    if kuru:
        _ardisik = int(ardisik_oku(karantina_dosyasi).get(motor) or 0)
        if rc != 0:
            _ardisik += 1
    else:
        _ardisik = ardisik_guncelle(karantina_dosyasi, motor, rc != 0)
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
    if not karar:
        print(
            "KARANTINA_KARAR motor=%s rc=%d imza=yok yazildi=hayir sebep=%s ardisik=%d"
            % (motor, rc, sebep, _ardisik)
        )
        return 10
'''


# ==========================================================================
# KOL D — imza TANINMASA DA ardisik esik yazar (27 Agu 2026, mimar hukmu)
# ==========================================================================
# 🔴 NEDEN REPODA: bu kol 27 Agu'da kurulu kopyaya ELLE kondu ve repoda
# HICBIR tasiyicisi yoktu (`grep -c GENEL_ARDISIK_ESIGI` -> 0). Yani yama
# temiz bir kopyaya uygulansa kol GELMEZ, `--durum` ise "hepsi KURULU"
# derdi: yazan var, tasiyan yok. Bu iki kalem o bosluğu kapatir.
#
# 🔴 TEK KAYNAK: esik SAYISI burada TEKRAR YAZILMAZ. `GENEL_ARDISIK_ESIGI`
# degeri `ERISIM_ARDISIK_ESIGI`den TURER; ayni rolu tasiyan iki literal
# sessizce ayrisir ve "esigi degistirdim" diyen onarim yarisini kacirir.
# Kabul bataryasi da adi MODULDEN okur, sayiyi kopyalamaz.
D0_CAPA = '''# Kac ARDISIK basarisiz kosumdan sonra erisim reddi karantina yazar.
# 1 OLAMAZ: tek seferlik rc!=0 karantina URETMEMELIDIR (yanlis pozitif yasagi).
ERISIM_ARDISIK_ESIGI = 3
'''

D0_YENI = '''# Kac ARDISIK basarisiz kosumdan sonra erisim reddi karantina yazar.
# 1 OLAMAZ: tek seferlik rc!=0 karantina URETMEMELIDIR (yanlis pozitif yasagi).
ERISIM_ARDISIK_ESIGI = 3

# 🔴 KOL D (27 Agu 2026) — Kol C yalniz BILINEN imzalari (kota, erisim
# reddi) tanir. Yarinki hata metni bu regex'lerin HICBIRINE uymayabilir ve
# ayni sessiz-13-ardisik-deneme deseni baska bir cikti metniyle TEKRAR
# eder. Bu esik o kor noktayi kapatir: imza NE OLURSA OLSUN, ayni motor
# ARDISIK bu kadar basarisiz olursa karantinaya yazilir.
# Deger TEKRAR YAZILMAZ, yukaridaki TEK KAYNAKTAN turer.
GENEL_ARDISIK_ESIGI = ERISIM_ARDISIK_ESIGI
'''

# D0b: kurulu kopyada kol ZATEN vardi ama esik IKINCI BIR LITERAL olarak
# yaziliydi (`= 3`). Bu kalem onu tek kaynaga indirir; temiz kopyada D0
# zaten dogru bicimi kurdugu icin ZATEN_KURULU gecer (idempotent).
D0B_CAPA = '''GENEL_ARDISIK_ESIGI = 3
'''

D0B_YENI = '''GENEL_ARDISIK_ESIGI = ERISIM_ARDISIK_ESIGI
'''

D1_CAPA = '''        elif _erisim:
            print(
                "KARANTINA_KARAR motor=%s rc=%d imza=var yazildi=hayir "
                "sebep=%s-esik-alti(%d/%d)"
                % (motor, rc, _erisim_sebep, _ardisik, ERISIM_ARDISIK_ESIGI)
            )
            return 10
'''

D1_YENI = '''        elif _erisim:
            print(
                "KARANTINA_KARAR motor=%s rc=%d imza=var yazildi=hayir "
                "sebep=%s-esik-alti(%d/%d)"
                % (motor, rc, _erisim_sebep, _ardisik, ERISIM_ARDISIK_ESIGI)
            )
            return 10
        elif rc != 0 and _ardisik >= GENEL_ARDISIK_ESIGI:
            # 🔴 KOL D: bilinen imza YOK ama ayni motor ardisik esigi asti.
            # Sebep ADIYLA gecer -- "imza taninmadi, ardisik n". TEK
            # seferlik rc!=0 buraya DUSMEZ (esik >= 2), yanlis pozitif yok.
            karar, sebep = True, "ardisik-basarisiz-imzasiz%d" % _ardisik
'''


YAMALAR = [
    ("A",  "SH",      A_CAPA,   A_YENI,   "NOBET_HUKUM_KOLU=A"),
    ("A2", "SH",      A_CAPA2,  A_YENI2,  'hukum=$HUKUM'),
    # A3: ilk surumun OLU DEGISKENI (`KOL_A_NOBET_KIRMIZI`) atilir. Hicbir yerde
    # okunmuyordu; kapi dosyasinda okunmayan degisken birakmak, bu evde tam da
    # kacindigimiz "yazan var okuyan yok" desenidir.
    ("A3", "SH",
     "  if (( NOBET_RC != 0 )); then KOL_A_NOBET_KIRMIZI=1; NOBET_KIRMIZI=1; fi\n",
     "  if (( NOBET_RC != 0 )); then NOBET_KIRMIZI=1; fi\n",
     "if (( NOBET_RC != 0 )); then NOBET_KIRMIZI=1; fi"),
    # A4/A4b: hukum ADI tetigin `sebep=` jetonundan turer (yukaridaki blogun
    # gerekcesi + olculen 7 turluk dagilim). SIRA: A4 ciktiyi yakalar, A4b
    # o degiskeni TUKETIR -- ters sirada A4b'nin okudugu degisken YOK olur.
    ("A4", "SH",     A4_CAPA,  A4_YENI,  "TETIK_CIKTISI="),
    ("A4b", "SH",    A4B_CAPA, A4B_YENI, "TETIK_SEBEBI:-TETIK_SEBEBI_OKUNAMADI"),
    ("B1", "KAPI",      B1_CAPA,  B1_YENI,  "dondurma_isirdi=False"),
    ("B2", "KAPI",      B2_CAPA,  B2_YENI,  "_dondurma_isirdi = bool"),
    ("B3", "KAPI",      B3_CAPA,  B3_YENI,  "DAGITIM_BACAGI_DUSTU"),
    ("B4", "GOZCU",     B4_CAPA,  B4_YENI,  "def icra_sebebini_ayikla"),
    ("B4b", "GOZCU",    B4B_CAPA, B4B_YENI, "icra_sebep = icra_sebebini_ayikla"),
    ("B4c", "GOZCU",    B4C_CAPA, B4C_YENI, '"icra_sebep": icra_sebep'),
    ("B4d", "GOZCU",    B4D_CAPA, B4D_YENI, "ICRA_HAL=%s ICRA_SEBEP=%s"),
    ("B4e", "GOZCU",    B4E_CAPA, B4E_YENI, 'kalp.get("icra_sebep") or "-"'),
    ("C2", "KARANTINA", C2_CAPA,  C2_YENI,  "import json"),
    ("C",  "KARANTINA", C_CAPA,   C_YENI,   "ERISIM_ARDISIK_ESIGI"),
    # 🔴 ISARET METINDE BIREBIR GECMELIDIR. Ilk surumde `erisim-esik-alti`
    # yazmistim; kodda o dizge `%s-esik-alti(%d/%d)` bicimindedir ve BIREBIR
    # GECMEZ -> yama UYGULANDIGI HALDE `--durum` "CAPA_YOK" dedi (sahte eksik).
    ("C3", "KARANTINA", C3_CAPA,  C3_YENI,  "-esik-alti(%d/%d)"),
    # --- KOL D: C/C3'un URETTIGI metne dayanir, o yuzden SIRADA SONRA gelir.
    ("D0",  "KARANTINA", D0_CAPA,  D0_YENI,  "GENEL_ARDISIK_ESIGI"),
    ("D0b", "KARANTINA", D0B_CAPA, D0B_YENI,
     "GENEL_ARDISIK_ESIGI = ERISIM_ARDISIK_ESIGI"),
    ("D1",  "KARANTINA", D1_CAPA,  D1_YENI,  "ardisik-basarisiz-imzasiz"),
]


def _yol(anahtar):
    """YAMALAR tablosundaki ANAHTARI kosum anindaki gercek yola cevirir."""
    return {"SH": SH, "KAPI": KAPI, "GOZCU": GOZCU,
            "KARANTINA": KARANTINA}[anahtar]


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def _yedekle(yol, damga):
    hedef = "%s.yedek-nobetucKol-%s" % (yol, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def durum():
    """Her kol icin (ad, KURULU|EKSIK|CAPA_YOK|CAPA_COK) doner."""
    sonuc = []
    onbellek = {}
    for ad, anahtar, capa, _yeni, isaret in YAMALAR:
        yol = _yol(anahtar)
        if yol not in onbellek:
            try:
                onbellek[yol] = _oku(yol)
            except OSError as e:
                onbellek[yol] = None
                sonuc.append((ad, yol, "DOSYA_YOK:%s" % type(e).__name__))
                continue
        metin = onbellek[yol]
        if metin is None:
            sonuc.append((ad, yol, "DOSYA_YOK"))
            continue
        if isaret in metin:
            sonuc.append((ad, yol, "KURULU"))
            continue
        n = metin.count(capa)
        if n == 0:
            sonuc.append((ad, yol, "CAPA_YOK"))
        elif n > 1:
            sonuc.append((ad, yol, "CAPA_COK=%d" % n))
        else:
            sonuc.append((ad, yol, "EKSIK"))
    return sonuc


def uygula(kuru=False):
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    uygulanan, atlanan, dusen = 0, 0, 0
    yedekler = set()
    icerik = {}
    for ad, anahtar, capa, yeni, isaret in YAMALAR:
        yol = _yol(anahtar)
        if yol not in icerik:
            try:
                icerik[yol] = _oku(yol)
            except OSError as e:
                print("KOL %-4s DOSYA_YOK %s (%s)" % (ad, yol, e))
                dusen += 1
                icerik[yol] = None
                continue
        metin = icerik[yol]
        if metin is None:
            dusen += 1
            continue
        if isaret in metin:
            print("KOL %-4s ZATEN_KURULU isaret=%r" % (ad, isaret))
            atlanan += 1
            continue
        n = metin.count(capa)
        if n != 1:
            # 🔴 Capa TEK olmali: 0 -> hedef degisti (bayat yama),
            # >1 -> hangi kopyaya vurdugumuz BELIRSIZ. Ikisi de RED.
            print("KOL %-4s CAPA_SAYISI=%d (1 bekleniyor) -> UYGULANMADI" % (ad, n))
            dusen += 1
            continue
        icerik[yol] = metin.replace(capa, yeni, 1)
        print("KOL %-4s UYGULANDI %s" % (ad, os.path.basename(yol)))
        uygulanan += 1
    if not kuru and uygulanan:
        for yol, metin in icerik.items():
            if metin is None:
                continue
            yedek = _yedekle(yol, damga)
            yedekler.add(yedek)
            _yaz(yol, metin)
    print("YAMA UYGULANAN=%d ZATEN=%d DUSEN=%d KURU=%d YEDEK=%d damga=%s"
          % (uygulanan, atlanan, dusen, int(kuru), len(yedekler), damga))
    for y in sorted(yedekler):
        print("YEDEK %s" % y)
    return 0 if dusen == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kuru", action="store_true", help="yazmadan uygula/farki bas")
    ap.add_argument("--durum", action="store_true", help="kurulu kopya yamali mi")
    ap.add_argument("--kok", default=None, metavar="DIZIN",
                    help="yamanin uygulanacagi AGAC (varsayilan: kurulu kopya "
                         "~/.claude/cron). Hermetik bir kopyayi yamalayip "
                         "olcmek icin; bayraksiz davranis DEGISMEZ.")
    args = ap.parse_args(argv)
    if args.kok:
        kok = os.path.abspath(os.path.expanduser(args.kok))
        if not os.path.isdir(kok):
            print("HATA: --kok dizini YOK: %s" % kok)
            return 2
        kok_ayarla(kok)
    print("KOK: %s (%s)" % (CRON, "BAYRAKLA" if args.kok else "VARSAYILAN/kurulu"))
    if args.durum:
        kotu = 0
        for ad, yol, hal in durum():
            print("KOL %-4s %-12s %s" % (ad, hal, os.path.basename(yol)))
            if hal != "KURULU":
                kotu += 1
        print("DURUM KURULU=%d EKSIK=%d" % (len(YAMALAR) - kotu, kotu))
        return 0 if kotu == 0 else 1
    return uygula(kuru=args.kuru)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# kosucu-gecici-agac.sh — foto koşucusunu origin/main'in GECICI arşivinden kosar.
#
# NEDEN: launchd ANA CHECKOUT'tan kosuyor; ana checkout kirli/geride kalinca main'deki
# onarim canliya inmiyordu (3. vaka, 14 Eki 2026). Okan kurali (disk izi YOK) kalici
# ikinci checkout istemiyor -> gecici agac. OLCUM (21 Eki 23:5x): kuyruk %99 BOS
# (8665 BOS / 3 ISLEDI / 99 OLCULEMEDI) olmasina ragmen 2 ajan x 30 kosum/saat ~ 4 GB/saat
# yazip siliyordu. BU SARMALAYICI artik uc adimda:
#   1. ANA checkout'tan origin/main'i FETCH eder (duserse mevcut origin/main ile devam)
#   2. KUYRUK YOKLAMASI: yalniz 4 dosyayi (~232 KB) arsivleyip `--kuyruk-yokla` kosar
#      (D1 sorgusu, tam kosucunun sorgu kumesiyle AYNI). IS YOKSA agac HIC ACILMAZ:
#      `HAL=BOS rc=0`. Yoklama OLCULEMEZSE `HAL=OLCULEMEDI rc=4` + agac YOK, is KUYRUKTA
#      (fail-closed). IS VARSA tam agac (69 MB) acilir ve KOSULAN asil betik calisir.
#   3. BOS BOS GERI CEKILME: 3+ ardışık BOS'tan sonra yoklama araligi 120 sn yerine
#      600 sn olur (durum dosyasi D_KOK altinda, git disi; IS gorulunce 120'ye doner).
#      launchd plist'ine DOKUNMAZ (StartInterval=120 sabit; erken donus ile eslenir).
# Dizinler `.noindex` ile biter (Spotlight indekslemez), ayni SHA icin YENIDEN KULLANILIR,
# SHA degisince eskisi silinir. Cikista dizin OLCEP silinir (AGAC_BOSTA=0) ve log'a
# `AGAC=<D|YOK> SHA=<kisa> SILINDI=<KB> RC=<rc>` satiri EKLENIR.
#
# ENV (override):
#   PRUVO_KOSUCU_ANA       : ana checkout yolu (varsayilan /Users/okan/dev/pruvo)
#   PRUVO_KOSUCU_D_KOK     : gecici kok (varsayilan /private/tmp)
#   PRUVO_KOSUCU_D_DESEN   : dizin oneki (varsayilan pruvo-kosucu-)
#   PRUVO_KOSUCU_BOS_ESIK  : kac ardışık BOS sonrasi geri cekilme (varsayilan 3)
#   PRUVO_KOSUCU_ARALIK    : dolu kuyruk yoklama araligi sn (varsayilan 120)
#   PRUVO_KOSUCU_ARALIK_BOS: bos kuyruk yoklama araligi sn (varsayilan 600)
# KABUL: rc, ic betikle ayni; log satiri SON yazilir (cikis ici).
#   `--kuyruk-yokla` BOS -> ic rc 10; bu ASLA disari sizmaz (sarmalayici rc=0 verir).
set -euo pipefail
shopt -s nullglob

ANA_KOK="${PRUVO_KOSUCU_ANA:-/Users/okan/dev/pruvo}"
D_KOK="${PRUVO_KOSUCU_D_KOK:-/private/tmp}"
D_DESEN="${PRUVO_KOSUCU_D_DESEN:-pruvo-kosucu-}"
BOS_ESIK="${PRUVO_KOSUCU_BOS_ESIK:-3}"
ARALIK="${PRUVO_KOSUCU_ARALIK:-120}"
ARALIK_BOS="${PRUVO_KOSUCU_ARALIK_BOS:-600}"
YOKLAMA_BOS_RC=10

# dosya mtime (sn) — BSD `stat -f %m`, GNU `stat -c %Y`; bilinmeyende 0 (silinir).
_mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }
# Yoklama icin gereken TEK dosyalar (tam agac 69 MB; bunlar ~232 KB).
YOKLAMA_DOSYALAR=(tools/foto-uretec-kosucu.py shop/wrangler.toml shop/wrangler.onizleme.toml foto-uretim-veri.js)

# --log <yol> argumanini OKU ve ic betige AYNEN GECIR: kosucunun HAL=/RED satirlari
# log'a yazmaya devam eder (14 Eki olcumu: TPU kontrast RED'i yalniz bu logda gorundu);
# sarmalayici ayni dosyaya kendi AGAC= satirini EKLER.
LOG_YOL=""
ARGS=()
HEDEF="canli"
while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--log" && -n "${2:-}" ]]; then
        LOG_YOL="$2"
        ARGS+=("$1" "$2")
        shift 2
        continue
    fi
    ARGS+=("$1")
    shift
done
for ((i = 0; i < ${#ARGS[@]}; i++)); do
    if [[ "${ARGS[$i]}" == "--hedef" && -n "${ARGS[$((i + 1))]:-}" ]]; then
        HEDEF="${ARGS[$((i + 1))]}"
    fi
done

# FETCH (duserse mevcut origin/main ile devam)
FETCH_NOT=""
if ! git -C "$ANA_KOK" fetch -q origin main 2>/dev/null; then
    FETCH_NOT="FETCH=DUSTU"
fi
SHA="$(git -C "$ANA_KOK" rev-parse origin/main 2>/dev/null || echo YOK)"
SHA_KISA="${SHA:0:9}"

# Dizin adlari: D_KOK/<onek>-<hedef>-<sha9>.noindex (`.noindex` = Spotlight indekslemez).
# Kuyruk durumu dosyasi ayni kokte, git disi, KUCUK: "bos=<n> son=<epoch>".
mkdir -p "$D_KOK"
DURUM="$D_KOK/$D_DESEN-durum-$HEDEF.txt"
D="$D_KOK/$D_DESEN-$HEDEF-$SHA_KISA.noindex"
YARI=""

# Cikis: olc + sil + log satiri yaz (hata olsa da). AGAC= yalniz agac GERCEKTEN acildiysa.
TMP_KB=0
AGAC_LOG="YOK"
temizle() {
    local rc=$?
    set +e
    local olcum=""
    if [[ -d "$D" ]]; then
        olcum="$D"
    elif [[ -n "$YARI" && -d "$YARI" ]]; then
        olcum="$YARI"
    fi
    if [[ -n "$olcum" ]]; then
        TMP_KB=$(du -sk "$olcum" 2>/dev/null | awk '{print $1}') || TMP_KB=0
    fi
    if [[ -n "$YARI" ]]; then rm -rf "$YARI"; fi
    if [[ -n "$D" ]]; then rm -rf "$D"; fi
    if [[ -n "$LOG_YOL" ]]; then
        {
            printf '%s AGAC=%s SHA=%s SILINDI=%dKB RC=%d %s\n' \
                "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$AGAC_LOG" "$SHA_KISA" "${TMP_KB:-0}" "$rc" "$FETCH_NOT"
        } >> "$LOG_YOL" 2>/dev/null || true
    fi
}
trap temizle EXIT

# Eski (baska SHA) agaclar: bu ajanin kendi oneki+hedeften, 600 sn'den eski olanlar SILINIR
# (cagisan kardes kosumun agacini yememek icin yas payi). Ayni SHA -> yeniden KULLANILIR.
SIMDI="$(date +%s)"
for eski in "$D_KOK/$D_DESEN-$HEDEF-"*.noindex; do
    [[ "$eski" == "$D" ]] && continue
    (( SIMDI - $(_mtime "$eski") < 600 )) && continue
    rm -rf "$eski"
done

# --- BOS BOS GERI CEKILME (durum dosyasi; launchd plist'ine dokunulmaz)
BOS_SAYISI=0
BOS_SON=0
if [[ -f "$DURUM" ]]; then
    # satir: "bos=<n> son=<epoch>" (yazilma hatasi -> sifir sayilir, fail-closed YOK)
    # BSD sed `\b` desteklemez; BRE sinif karsiligi kullanilir (satiri bizim yaziyoruz).
    BOS_SAYISI="$(sed -n 's/.*bos=\([0-9][0-9]*\).*/\1/p' "$DURUM" | head -1)"
    BOS_SON="$(sed -n 's/.*son=\([0-9][0-9]*\).*/\1/p' "$DURUM" | head -1)"
    BOS_SAYISI="${BOS_SAYISI:-0}"
    BOS_SON="${BOS_SON:-0}"
fi
# Geri cekilme YALNIZ bos>=BOS_ESIK iken: 120 sn'lik taban aralik launchd'in StartInterval'i ile
# gelir (plist'e dokunulmaz); 600 sn'lik aralik ise bu erken donusle bir gorunur.
# is gorulunce bos=0 -> ertesi tick yine yoklar (120'ye donus).
if (( BOS_SAYISI >= BOS_ESIK && SIMDI - BOS_SON < ARALIK_BOS )); then
    # YOKLAMA YAPILMAZ: agac acilmaz, D1 cagrisi olmaz, is kuyrukta kalir.
    printf 'KOSUCU_ERTELENDI bos=%d aralik=%ds kalan_sn=%d\n' \
        "$BOS_SAYISI" "$ARALIK_BOS" "$((ARALIK_BOS - SIMDI + BOS_SON))"
    printf 'HAL=BOS rc=0\n'
    exit 0
fi

durum_yaz() {
    printf 'bos=%s son=%s\n' "$1" "$(date +%s)" > "$DURUM"
}

# --- ASIM 1: yalniz yoklama dosyalarini arsivle (~232 KB). `.tamam` varsa tam agac zaten var.
arsivle() {
    local isaret="$1"
    shift
    if [[ -f "$D/$isaret" ]]; then
        return 0
    fi
    rm -rf "$D"
    YARI="$(mktemp -d "$D_KOK/$D_DESEN-yari-XXXXXX")"
    if ! git -C "$ANA_KOK" archive "$SHA" -- "$@" | tar -x -C "$YARI"; then
        return 1
    fi
    : > "$YARI/$isaret"
    mv "$YARI" "$D"
    YARI=""
    return 0
}

AGAC_LOG="$D"
arsivle ".yoklama" "${YOKLAMA_DOSYALAR[@]}"
YOKLAMA_RC=0
python3 "$D/tools/foto-uretec-kosucu.py" "${ARGS[@]}" --kuyruk-yokla || YOKLAMA_RC=$?

BOS_ERKEN_CIKIS=0
case "$YOKLAMA_RC" in
    0)
        # IS VAR: sayaci sifirla (aralik 120'ye doner) ve tam agaci ac.
        durum_yaz 0
        arsivle ".tamam"
        ;;
    "$YOKLAMA_BOS_RC")
        # IS YOK: sayaci artir; asagida agaci BIRAKIP cikar (SILINDI=<kucuk>KB loglanir).
        durum_yaz "$((BOS_SAYISI + 1))"
        BOS_ERKEN_CIKIS=1
        ;;
    *)
        # OLCULEMEDI (rc=4) veya beklenmeyen hata: fail-closed — IS KUYRUKTA KALIR.
        # Sayac ILERLETILMEZ (yoklama yeniden denenir, geri cekilme buyutulmez).
        exit "$YOKLAMA_RC"
        ;;
esac
if [[ "$BOS_ERKEN_CIKIS" == "1" ]]; then
    exit 0
fi

# Git-disi gereken yollari ana checkout'a ISARET et (kopyalama YOK).
# shop/node_modules ana checkout'ta VARSA ve gecici kokte YOKSA semlink et;
# npx --prefix SHOP wrangler yoksa zaten wrangler'i indirir (kosucu davranisi degismez).
if [[ -d "$ANA_KOK/shop/node_modules" && ! -e "$D/shop/node_modules" ]]; then
    ln -s "$ANA_KOK/shop/node_modules" "$D/shop/node_modules"
fi

# Kos (ARGS bos olabilir — set -u altinda "${ARR[@]}" bos dizide unbound sayilir)
RC=0
if [[ ${#ARGS[@]} -gt 0 ]]; then
    python3 "$D/tools/foto-uretec-kosucu.py" "${ARGS[@]}" || RC=$?
else
    python3 "$D/tools/foto-uretec-kosucu.py" || RC=$?
fi
exit $RC
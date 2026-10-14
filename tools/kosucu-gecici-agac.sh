#!/usr/bin/env bash
# kosucu-gecici-agac.sh — foto koşucusunu origin/main'in GECICI arşivinden kosar.
#
# NEDEN: launchd ANA CHECKOUT'tan kosuyor; ana checkout kirli/geride kalinca main'deki
# onarim canliya inmiyordu (3. vaka, 14 Eki 2026). Okan kurali (disk izi YOK) kalici
# ikinci checkout istemiyor -> her kosumda gecici agac. Bu sarmalayici:
#   1. ANA checkout'tan origin/main'i FETCH eder (duserse mevcut origin/main'le devam)
#   2. Gecici dizin acar (mktemp), git archive ile dosyalari oraya cikarir
#   3. Git-disi gereken yollari (shop/node_modules) ANA checkout'a symlink eder (KOPYA YOK)
#   4. KOSULAN asil betigi gecici dizinden calistirir, ic rc'yi aynen disari verir
#   5. Cikista dizini OLCEP siler + log'a "AGAC=<D> SHA=<kisa> SILINDI=<KB>" satirini ekler
#
# ENV (override):
#   PRUVO_KOSUCU_ANA       : ana checkout yolu (varsayilan /Users/okan/dev/pruvo)
#   PRUVO_KOSUCU_D_KOK     : gecici kok (varsayilan /private/tmp)
#   PRUVO_KOSUCU_D_DESEN   : mktemp sablonu (varsayilan pruvo-kosucu-XXXXXX)
# KABUL: rc, ic betikle ayni; log satiri SON yazilir (cikis ici).
set -euo pipefail

ANA_KOK="${PRUVO_KOSUCU_ANA:-/Users/okan/dev/pruvo}"
D_KOK="${PRUVO_KOSUCU_D_KOK:-/private/tmp}"
D_DESEN="${PRUVO_KOSUCU_D_DESEN:-pruvo-kosucu-XXXXXX}"

# --log <yol> argumanini AYIR (sarmalayici log'a kendi satiri ekler; ic betige VERMEZ).
LOG_YOL=""
ARGS=()
while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--log" && -n "${2:-}" ]]; then
        LOG_YOL="$2"
        shift 2
        continue
    fi
    ARGS+=("$1")
    shift
done

# FETCH (duserse mevcut origin/main ile devam)
FETCH_NOT=""
if ! git -C "$ANA_KOK" fetch -q origin main 2>/dev/null; then
    FETCH_NOT="FETCH=DUSTU"
fi
SHA="$(git -C "$ANA_KOK" rev-parse origin/main 2>/dev/null || echo YOK)"
SHA_KISA="${SHA:0:9}"

# Gecici dizin (ebeveyn dizin yoksa olustur — /private/tmp her zaman var; test override'i
# kendi tmpdir'ini yeni acmis olabilir)
mkdir -p "$D_KOK"
D="$(mktemp -d "$D_KOK/$D_DESEN")"

# Cikis: olc + sil + log satiri yaz (hata olsa da)
TMP_KB=0
temizle() {
    local rc=$?
    set +e
    if [[ -d "$D" ]]; then
        TMP_KB=$(du -sk "$D" 2>/dev/null | awk '{print $1}')
        rm -rf "$D"
    fi
    if [[ -n "$LOG_YOL" ]]; then
        {
            printf '%s AGAC=%s SHA=%s SILINDI=%dKB RC=%d %s\n' \
                "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$D" "$SHA_KISA" "$TMP_KB" "$rc" "$FETCH_NOT"
        } >> "$LOG_YOL" 2>/dev/null || true
    fi
}
trap temizle EXIT

# Arsivi ac
git -C "$ANA_KOK" archive "$SHA" | tar -x -C "$D"

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
#!/bin/sh
# ISCI PUSH KAPISI (21 Eki 2026, BaBa 14:1x (2) — MAKINE KAPISI).
# OLCULEN VAKA: bir isci spec'teki "main'e push etme" METIN yasagini deldi (hasat
# `c2c82514`). Metin yasagi isciyi baglamaz; bu kapi baglar.
#
# Kural: `isci.sh` her isci kosumunda `PRUVO_ISCI_KOSUMU` (motor adi) ve
# `PRUVO_ISCI_ETIKET` kurar (isci.sh CLAUDE_ENV). Push yalniz su iki halde gecer:
#   (a) `PRUVO_ISCI_KOSUMU` BOS  -> isci kosumu degil (mimar/insan push'u), kapi DOKUNMAZ
#   (b) `ISCI_PUSH_IZNI` == `PRUVO_ISCI_ETIKET` (ikisi de dolu) -> mimar bu etiketli
#       kosuma push iznini spec/cagrida ACIKCA verdi
# Aksi (izin yok / bos etiket / farkli etiket) -> rc=1, PUSH DURUR. Izin ETIKETE baglidir:
# baska bir isci kosumundan miras kalan izin bu kosumu acmaz.
#
# Cagiran: tools/kancalar/pre-push (0- bolumu). Olcer: tools/isci-push-kapisi-test.py.
# stdin'e DOKUNMAZ (pre-push ref listesini sonraki bloklar okur).

if [ -z "${PRUVO_ISCI_KOSUMU:-}" ]; then
  exit 0
fi

if [ -n "${ISCI_PUSH_IZNI:-}" ] && [ -n "${PRUVO_ISCI_ETIKET:-}" ] \
    && [ "$ISCI_PUSH_IZNI" = "$PRUVO_ISCI_ETIKET" ]; then
  echo "ISCI_PUSH_KAPISI=GECTI motor=$PRUVO_ISCI_KOSUMU etiket=$PRUVO_ISCI_ETIKET (izin acik)" >&2
  exit 0
fi

echo "!! PUSH DURDURULDU — ISCI PUSH KAPISI: isci kosumu (motor=$PRUVO_ISCI_KOSUMU etiket=${PRUVO_ISCI_ETIKET:-BOS}) push izni yok (ISCI_PUSH_IZNI=${ISCI_PUSH_IZNI:-BOS})." >&2
echo "   Isci push ETMEZ; commit'i birakir, mimar push eder. Izin gerekiyorsa mimar spec/cagrida ISCI_PUSH_IZNI=<etiket> verir." >&2
exit 1

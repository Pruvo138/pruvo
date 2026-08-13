# Dağıtım sonrası iki kırmızı — icra raporu

- `python3 tools/isci-kapisi-dagitim-kaniti.py` — rc=0 — `KANIT: 5/5 kardes evin KOPYASINDA enjeksiyon + canli fikstur GECTI`
- `python3 tools/isci-kapisi-dagitim-kaniti.py --bozuk-damga-test` — rc=0 — `BOZUK DAMGA NEGATIF NOBETI: ev=BaBa durum=ZATEN TAM damga=YOK sonuc=KIRMIZI`
- `python3 tools/mimar-kapi-6ev-test.py` — rc=0 — `SONUC: 222/222 vaka GECTI (6 ev x 37 vaka).`
- `python3 tools/mimar-kilit-test.py` — rc=0 — `SONUC: 269/269 vaka GECTI (cevre-atlanan 0, sizinti yok).`
- `python3 tools/mimar-kapi-mutasyon-test.py` — rc=0 — `SONUC: 53/53 mutant beklenen isareti verdi (48 kural mutasyonu KIRMIZI + 3 kontrol mutanti YESIL + 2 cevre-ariza enjeksiyonu).`
- `python3 tools/ci-kapsam-test.py` — rc=0 — `SONUC: YESIL ✅  — her kabul testi ya kosuluyor ya gerekceli muaf.`

IKI KIRMIZI: dagitim-kaniti=0 6ev=0 vaka=222 kilit=0 mutasyon=0

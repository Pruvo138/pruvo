#!/usr/bin/env python3
# ⛔ ÇAĞIRMA — EMEKLİ (Okan 18 Tem: Cults3D rate-limit/429 yüzünden çıkarıldı)
"""KABUL TESTI — cults3d-api.py `satilabilir()` FAIL-CLOSED beyaz-liste davranisi.

Cults3D bir PAZAR: ucretsiz CC + UCRETLI/satici icerigi. Yanlis satarsak telif ihlali. fail-closed
beyaz liste SART: sadece CC-BY / BY-SA / BY-ND / CC0(kanonik cc0) + MIT/GPL/BSD satilabilir; Cults
tescilli + NC + tanimadigimiz HER lisans -> satilamaz.

Girdi tablosu artik CANLI OLCUM'den (2026-07-18, kimlikli GraphQL; 320+ urun tarandi). GERCEK kodlar
resmi dok'un VARSAYIMINDAN farkli cikti — bu tablo gerceklige gore duzeltildi:
  * Ozel-kullanim kodu  cults_pu  ("CULTS PU - Private Use")   — eski varsayim yanlislikla cults_cu diyordu.
  * Ticari kod          cults_cu  ("CULTS CU - Commercial Use") + cults_cu_nd ("... No Derivative").
    Bu, satin ALINDIGINDA alicisina ticari hak verir; BIZ satin almadigimiz icin fail-closed False.
  * "cults_su" (varsayilan dok'ta gecen) CANLI VERIDE YOK.
  * CC0 kodu  cc_pddc  ("CC0 - Creative Commons public domain") — 'cc0' DEGIL.
    NOT: cc_pddc'de Cults kendi bayragi allowsCommercialUse=FALSE veriyor; gate KOD formunu (uretimde
    lisans_str code'u tercih eder) False donduruyor = fail-closed, guvenli. Ad formu 'cc0' tokeni ile
    True donuyor (evrensel CC0 hukmu) = KOD ile AD CELISIYOR; bu bir YARGI maddesi (mimara raporlandi),
    gate KENDILIGINDEN DEGISTIRILMEDI. Uretim yolu (code) reddettigi icin CC0 urunleri pratikte atlanir.

Kosum:  python3 tools/cults3d-lisans-test.py
Cikti:  tum satirlar 'ok', son satir 'TUM TESTLER GECTI' (basarisizsa exit 1 + neyin patladigi).

ONCE-KIRMIZI kaniti (scratchpad/redfirst_evidence.py): KASITLI FAIL-OPEN bir satilabilir()
(NC disinda her seyi True) bu GERCEK string'lerde 7 satirda KIRMIZI yaniyor (cults_pu/cults_cu/
cults_cu_nd + kod+ad formlari + cc_pddc). Gercek gate hepsini False donduruyor. Ayrica "cc_by_nd"yi
bloklayan (ND'yi eleyen) ya da cults_pu'yu geciren bir kapi da KIRMIZI olurdu."""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_API = os.path.join(_HERE, "cults3d-api.py")
_spec = importlib.util.spec_from_file_location("cults3d_api", _API)
c3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c3)

# (license girdisi, beklenen satilabilir?, beklenen cc_turu, aciklama)
# GERCEK string'ler: 2026-07-18 canli GraphQL olcumu (code + name(locale:EN)) — probe ciktisi rapor+
# scratchpad'te. Uretimde gate girdisi lisans_str(c) = 'code' (her urunde mevcut olctu).
CASES = [
    # --- SATILAMAZ: Cults tescilli (GERCEK kodlar; hepsi "cults" tokeni -> fail-closed) ---
    ("cults_pu",                                          False, None, "CULTS PU - Private Use kodu (VARSAYILAN/en yaygin; kisisel)"),
    ("CULTS PU - Private Use",                            False, None, "CULTS PU - Private Use ADI (kisisel, ticari degil)"),
    ("cults_cu",                                          False, None, "CULTS CU - Commercial Use kodu (satin ALMADIK -> fail-closed)"),
    ("CULTS CU - Commercial Use",                         False, None, "CULTS CU - Commercial Use ADI (dosyayi biz satin almadik)"),
    ("cults_cu_nd",                                       False, None, "CULTS CU-ND - Commercial Use - No Derivative kodu"),
    ("CULTS CU-ND - Commercial Use - No Derivative",      False, None, "CULTS CU-ND ADI (satin alinmadi)"),
    ("cults_su",                                          False, None, "GELECEK-KORUMA: canli veride YOK ama her cults_* -> fail-closed"),
    # --- SATILAMAZ: NonCommercial (GERCEK kod + name) ---
    ("cc_by_nc",                                          False, None, "CC BY-NC kodu"),
    ("cc_by_nc_sa",                                       False, None, "CC BY-NC-SA kodu"),
    ("cc_by_nc_nd",                                       False, None, "CC BY-NC-ND kodu"),
    ("CC BY-NC - Attribution - Non commercial",           False, None, "NC ADI (canli name formu)"),
    ("CC BY-NC-SA - Attribution - Non commercial - Share alike", False, None, "NC-SA ADI"),
    ("CC BY-NC-ND - Attribution - Non commercial - No derivatives", False, None, "NC-ND ADI"),
    # --- SATILAMAZ: CC0'in GERCEK Cults kodu = cc_pddc; Cults allowsCommercialUse=False ---
    #     Uretim yolu (code) -> False = fail-closed. Ad formu 'cc0' tokeni ile True (asagida, celiski notu).
    ("cc_pddc",                                          False, None, "CC0 GERCEK kodu (cc_pddc); Cults acu=False -> gate KOD formu reddeder (fail-closed)"),
    # --- SATILAMAZ: bos / bilinmeyen ---
    ("",                                                 False, None, "bos -> bilinmiyor -> atla"),
    (None,                                               False, None, "None -> atla"),
    ("All Rights Reserved",                              False, None, "taninmayan -> FAIL-CLOSED"),
    ("uydurma-lisans",                                   False, None, "taninmayan -> FAIL-CLOSED"),

    # --- SATILABILIR: GERCEK ticari-serbest lisanslar (canli code + name; hepsi Cults acu=True) ---
    ("cc_by",                                            True,  "CC BY 4.0",    "CC BY - Attribution kodu (acu=True)"),
    ("CC BY - Attribution",                              True,  "CC BY 4.0",    "CC BY ADI"),
    ("cc_by_sa",                                         True,  "CC BY-SA 4.0", "CC BY-SA kodu (acu=True)"),
    ("CC BY-SA - Attribution - Share alike",             True,  "CC BY-SA 4.0", "CC BY-SA ADI"),
    ("cc_by_nd",                                         True,  "CC BY-ND 4.0", "CC BY-ND kodu (ND SATILABILIR; acu=True)"),
    ("CC BY-ND - Attribution - No derivatives",          True,  "CC BY-ND 4.0", "CC BY-ND ADI"),
    ("mit",                                              True,  None,           "MIT License kodu (canli goruldu; acu=True)"),
    ("MIT License",                                      True,  None,           "MIT License ADI"),
    ("cc0",                                              True,  None,           "kanonik cc0 tokeni (Cults'ta cc_pddc gelir; birim testi olarak beyaz-liste)"),

    # --- CELISKI (YARGI): cc_pddc AD formu 'cc0' tokeni tasidigi icin True doner (evrensel CC0 hukmu),
    #     ama Cults kendi bayragi allowsCommercialUse=False. KOD formu (uretim yolu) yukarida False.
    #     Bu satir MEVCUT davranisi PINLER; gate degistirilmedi, celiski mimara raporlandi. ---
    ("CC0 - Creative Commons public domain",             True,  None,           "CELISKI: ad 'cc0' tokeni -> True; KOD (uretim) False; mimara raporlandi"),
]


def main():
    fails = []
    for lic, bek_sat, bek_cc, aciklama in CASES:
        try:
            sat = c3.satilabilir(lic)
            cc = c3.cc_turu(lic)
        except Exception as e:                                   # noqa: BLE001
            fails.append((lic, "PATLADI %r" % e, aciklama))
            print("  PATLADI  %-46r -> %r" % (lic, e))
            continue
        ok_sat = (sat == bek_sat)
        ok_cc = (cc == bek_cc)
        durum = "ok" if (ok_sat and ok_cc) else "HATA"
        if not (ok_sat and ok_cc):
            fails.append((lic, "sat=%s(bek %s) cc=%r(bek %r)" % (sat, bek_sat, cc, bek_cc), aciklama))
        print("  %-4s %-48r sat=%-5s cc=%-12r  # %s"
              % (durum, lic, sat, cc, aciklama))

    print()
    if fails:
        print("BASARISIZ — %d/%d senaryo yanlis:" % (len(fails), len(CASES)))
        for lic, ne, aciklama in fails:
            print("  x %r -> %s  (%s)" % (lic, ne, aciklama))
        sys.exit(1)
    print("TUM TESTLER GECTI (%d senaryo)." % len(CASES))


if __name__ == "__main__":
    main()

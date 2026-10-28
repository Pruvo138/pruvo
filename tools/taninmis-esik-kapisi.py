#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TANINMIS ESIK kapisi — katalogda >= ESIK urunu olup marka sayfasi DOGMAYAN marka.

OLCULEN SINIF (25 Eki 2026, iki vaka ayni gun): elle tutulan liste katalogun gerisinde
kaliyor ve kimse gormuyor.
  1) /marka/{zontes,keeway,bajaj,sym}/ 404 — MaCiT 24 Eki'de 34 motosiklet parcasi ekledi,
     markalar index.html TANINMIS_MARKALAR'a girmedigi icin sayfa uretilmedi.
  2) /marka/mv-agusta/ 404 — MaCiT 25 Eki'de 5 MV Agusta urunu ekledi, ayni sebep;
     ancak YAYINDAN SONRA elle olculunce goruldu.
Marka sayfasi evreni = TANINMIS_MARKALAR ∪ cip evreni (`cip_evreni_markalari`), esik
`marka_model_build.ESIK`. Bu arac evrenin DISINDA kalan ama esigi asan markalari sayar.

NE OLCER (kopya mantik YOK — jeneratorun KENDI fonksiyonlari):
  urun basina `marka[]` her eleman `evren.katla` ile katlanir (marka_uyelikleri ile ayni
  katlama), tekil marka -> urun kumesi. Esik >= ESIK ∧ taninmis_mi() degil ∧ cip evreninde
  degil -> ACIK.

MANDAL (BaBa tik 159 ③, 25 Eki 2026): TABAN = o gunku ACIK kumesi, ADLA civili.
  K1 YENI GIREN — ACIK'ta olup TABAN'da olmayan marka -> KIRMIZI (MV Agusta vakasini
     yayindan ONCE yakalardi). Cozum: markayi TANINMIS'e al (kurasyon) ya da veriyi duzelt.
  K2 TABAN BAYAT (oz-temizlik) — TABAN'da olup artik ACIK olmayan ad (sayfa kazandi /
     katalogdan dustu) -> KIRMIZI; ayni commit'te TABAN'dan silinir. Taban YALNIZ kuculur.
  ESIK jeneratorden okunur (`marka_model_build.ESIK`) — ikinci ESIK tanimi YOK.
  MUTANT (her kosumda): M1 TABAN'dan bir ad cikar -> K1 KIRMIZI · M2 TABAN'a olmayan bir ad
  eklenir -> K2 KIRMIZI. Mutant YESIL kalirsa kapi olcmuyor -> rc=1.

Kullanim:
    python3 tools/taninmis-esik-kapisi.py            # K1 + K2 + mutantlar
    python3 tools/taninmis-esik-kapisi.py --rapor    # yalniz ACIK listesi (hukum yok)
rc=0 hepsi gecti · rc=1 bir madde dustu · rc=2 OLCULEMEDI (kurulum coktu).
"""
import importlib.util
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")

# 🔴 TABAN — 25 Eki 2026, BaBa tik 159/160 hukmunun (a) sinifi: gercek marka, sayfasiz, TANINMIS
# partilerini (PARTI 1: 7 · PARTI 2: 15) bekliyor. (b) sinifi (VW/PSA/VAG/Cayenne/Boxster/
# Ssangyong) MaCiT `uyum` hijyeniyle kaynakta kapandi, MV Agusta TANINMIS'e girdi -> tabanda YOK.
# Her parti merge'unde girdigi adlar AYNI commit'te buradan silinir (K2 zorlar). Hedef: bos.
TABAN = frozenset({
    # PARTI 1 (7) TANINMIS'e girdi, 25 Eki — K2 geregi buradan silindi.
    # `Indian Motorcycle` (PARTI 2) da silindi: MaCiT `009065d8` 14 kaydi sozluk kanonu
    # `Indian`'a tasidi (K2 bayat) ve `Indian` ayni dalda TANINMIS'e girdi (K1 yeni) — 25 Eki.
    # PARTI 2
    "Puch", "Genesis", "Bentley", "GMC", "Motec", "Simrad", "Bavaria",
    "AeroPress", "Keurig", "Moccamaster", "Roland", "Weinsberg", "Tracker", "Ninja",
    # 26 Eki 2026 (BaBa tik 201b): MaCiT SG1 4 kayit (katalog 40925) Segway'i esigin ustune
    # cikardi (marka[] 5) -> K1 kirmizi (nobet 40273881039 hijyen-a2). Sayfa dogumu PARTI 2'de.
    "Segway",
    # 27 Eki 2026 (BaBa tik 214 (B)/(C) + 231 (D)): MaCiT NU1 5 kayit NIU'yu esigin ustune
    # cikardi; tek marka sayfa dogumu RED -> sayfa PARTI 2'de. Veri ile AYNI birlestirmede iner.
    "NIU",
    # 27 Eki 2026 (BaBa tik 248 (C)): MaCiT JW1 1 kayit Jawa'yi esigin ustune cikardi (K1
    # yakaladi); sayfa dogumu PARTI 2'de. Veri ile AYNI birlestirmede iner (NIU yolu).
    "Jawa",
    # 27 Eki 2026 (BaBa tik 253 (B)): MaCiT ES2 9 kayit (Daewoo 5 · Scion 6 · Mahindra 4) uc
    # markayi esigin ustune cikardi (K1 yakaladi); sayfa dogumu PARTI 2'de, veriyle AYNI merge.
    "Daewoo",
    "Scion",
    "Mahindra",
    # 27 Eki 2026 (BaBa tik 258 (B)): MaCiT ES3 10 kayit (Anet 3 · Bialetti 6 · Fiamma 4 ·
    # Huter 3 · Zelmer 4) bes markayi esigin ustune cikardi; sayfa dogumu PARTI 2'de.
    "Anet",
    "Bialetti",
    "Fiamma",
    "Huter",
    "Zelmer",
    # 27 Eki 2026 (BaBa tik 267 (D)): MaCiT ES4+ES5+ES6 64 kayit tek dalda; on iki marka
    # esigin ustune cikti (Bafang 4 · Jura 4 · Line 6 4 · Minn Kota 4 · Old Town 4 · Pioneer 4 ·
    # Prusa 4 · Saeco 4 · Flashforge 3 · Lowrance 3 · Mazzer 3 · Skyteam 3); sayfa dogumu PARTI 2'de.
    "Bafang",
    "Flashforge",
    "Jura",
    "Line 6",
    "Lowrance",
    "Mazzer",
    "Minn Kota",
    "Old Town",
    "Pioneer",
    "Prusa",
    "Saeco",
    "Skyteam",
    # 27 Eki 2026 (BaBa tik 269): MaCiT ES7 11 kayit ayni tek dala alindi; uc marka esigin
    # ustune cikti (Rode 4 · Aukey 3 · Quechua 3); sayfa dogumu PARTI 2'de.
    "Aukey",
    "Quechua",
    "Rode",
    # 28 Eki 2026 (BaBa tik 275 A): MaCiT ES8 5 kayit sozluk 22 dalina alindi; Baofeng esigin
    # ustune cikti (4); sayfa dogumu PARTI 2'de.
    "Baofeng",
    # 28 Eki 2026 (BaBa tik 275): MaCiT ES9+ES10 20 kayit (17 TV + Geo 3) sozluk 23 dalina
    # alindi; on marka esigin ustune cikti (K1 10); sayfa dogumu PARTI 2'de.
    "Briggs & Stratton",
    "Geo",
    "Itiwit",
    "Kayo",
    "Lavazza",
    "Magic Bullet",
    "Massey Ferguson",
    "Pössl",
    "Speeduino",
    "Yanmar",
})


def olculemedi(sebep):
    print("OLCULEMEDI: %s" % sebep)
    sys.exit(2)


def yukle():
    sys.path.insert(0, TOOLS)
    sp = importlib.util.spec_from_file_location("mm_esik", os.path.join(TOOLS, "marka_model_build.py"))
    mm = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mm)
    with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    with open(os.path.join(KOK, "index.html"), encoding="utf-8") as f:
        index_html = f.read()
    return mm, urunler, index_html


def acik_markalar(mm, urunler, index_html):
    """Doner: [(marka, urun_sayisi)] — esigi asan, sayfa evreninin DISINDAKI markalar."""
    evren = mm.MarkaEvreni(index_html)
    ek = set(mm.cip_evreni_markalari(urunler, index_html))
    kume = {}
    for p in urunler:
        pid = p.get("id")
        if not pid:
            continue
        # marka[] dizisi MODEL adlarini da tasir (["Mazda","MX-5"]) — her eleman sayilirsa
        # 948 "ACIK" cikar, cogu model (olculdu 25 Eki). Marka adayi = marka[0].
        m0 = ((p.get("marka") or [None])[0] or "").strip()
        kan = evren.katla(m0) if m0 else None
        if kan:
            kume.setdefault(kan, set()).add(pid)
    return sorted(((m, len(ids)) for m, ids in kume.items()
                   if len(ids) >= mm.ESIK and not evren.taninmis_mi(m) and m not in ek),
                  key=lambda t: (-t[1], t[0]))


def hukum(acik_adlar, taban):
    """Doner: (yeni_giren, bayat) — K1 ve K2'nin listeleri."""
    return sorted(acik_adlar - taban), sorted(taban - acik_adlar)


def main():
    try:
        mm, urunler, index_html = yukle()
        acik = acik_markalar(mm, urunler, index_html)
    except Exception as e:                                    # noqa: BLE001
        olculemedi("kurulum coktu: %r" % (e,))
    print("TANINMIS_ESIK katalog=%d ESIK=%d ACIK=%d TABAN=%d"
          % (len(urunler), mm.ESIK, len(acik), len(TABAN)))
    for m, n in acik:
        print("  ACIK %-28s %d urun%s" % (m, n, "" if m in TABAN else "  <- YENI"))
    if "--rapor" in sys.argv[1:]:
        sys.exit(0)

    adlar = {m for m, _n in acik}
    yeni, bayat = hukum(adlar, TABAN)
    hatalar = []
    if yeni:
        hatalar.append("K1 YENI GIREN (esigi asti, sayfasi yok, tabanda yok): %s — TANINMIS'e "
                       "al ya da veriyi duzelt" % ", ".join(yeni))
    if bayat:
        hatalar.append("K2 TABAN BAYAT (artik ACIK degil): %s — TABAN'dan sil" % ", ".join(bayat))
    print("K1 yeni=%d · K2 bayat=%d" % (len(yeni), len(bayat)))

    # MUTANTLAR — ayni olcum, degistirilmis taban; hukum fonksiyonu KIRMIZI basmali.
    ornek = sorted(TABAN & adlar)
    if ornek:
        m1_yeni, _ = hukum(adlar, TABAN - {ornek[0]})
        m1 = ornek[0] in m1_yeni
        print("M1 (TABAN -%s): %s" % (ornek[0], "KIRMIZI (beklenen)" if m1 else "YESIL (KUSUR)"))
    else:
        m1 = False
        print("M1 KURULAMADI: TABAN ∩ ACIK bos")
    sahte = "__TANINMIS_ESIK_MUTANT__"
    _, m2_bayat = hukum(adlar, TABAN | {sahte})
    m2 = sahte in m2_bayat
    print("M2 (TABAN +sahte): %s" % ("KIRMIZI (beklenen)" if m2 else "YESIL (KUSUR)"))
    if not (m1 and m2):
        hatalar.append("MUTANT YESIL kaldi — kapi olcmuyor")

    for h in hatalar:
        print("  KIRMIZI:", h)
    print("SONUC=%s" % ("GECTI" if not hatalar else "KALDI"))
    sys.exit(0 if not hatalar else 1)


if __name__ == "__main__":
    main()

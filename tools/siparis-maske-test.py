#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SIPARISLER.PY MUSTERI VERISI MASKELEME NOBETCISI (kisisel veri / sizinti ekseni).

    python3 tools/siparis-maske-test.py

NEDEN VAR: repo PUBLIC. `tools/siparisler.py` canli D1'den musteri ADI ve
TELEFONUNU okur. 31 Tem'e kadar bu degerler EKRANA HAM basiliyordu, buna ragmen
`tools/siparisler-test.py` docstring'i "telefon maskelenerek basilir" DIYORDU
(beyan-davranis celiskisi; TEST 6 o ciktinin ilk 25 satirini stdout'a dokuyordu).
Davranis duzeltildi -> bu nobetci duzeltmenin GERI ALINAMAZLIGINI olcer.

FIKSTURLE calisir: canli D1'e, aga, `npx`'e DOKUNMAZ (`siparisler.wrangler_sorgu`
monkeypatch'lenir). `siparisler.py`'ye test-ozel arka kapi EKLENMEZ; TTY enjeksiyonu
`siparisler._tty` monkeypatch'iyle yapilir.

  1. maskele_ad / maskele_tel birim vakalari (bos, tek harf, kisa, +90'li, cok kelimeli)
  2. format_siparis(fikstur) VARSAYILAN -> HAM ad/tel YOK, MASKELI bicimler VAR
  3. UCTAN UCA SIZINTI TARAYICI — main([]) ciktisinda fiksturun HICBIR kisisel
     degeri (ham / kelime / telefonun son-4 disindaki basamak dizisi) GECMEZ
  4. `--acik` + TTY YOK -> cikti MASKELI + stderr'de tek satir uyari (FAIL-CLOSED)
  5. `--acik` + TTY VAR -> cikti HAM (pozitif eksen: maskeleme "her seyi yildiza
     cevir" gibi anlamsiz bir seye donuserse bu eksen kirmizi yanar)
  6. KIRMIZI-MUTASYON KANITI — maskeleme SOKULMUS kopya tempdir'e yazilir,
     importlib ile yuklenir, (3)'teki AYNI tarayici uygulanir: SIZINTI BULMALI.
     Bulamazsa nobetci OLU demektir -> KIRMIZI.
  7. OZ-NOBETCI — suite_butunlugu() pozitif+negatif eksende olculur; eksik/mukerrer/
     beyan-disi kayit KIRMIZI. Bu dosyada govde bosaltma (hollowing) fail-open'i YOK.
"""
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import siparisler  # noqa: E402

SONUC = []

# BEYAN: hangi testlerin KAYIT ETMESI zorunlu. Bir testin cagrisi silinir /
# govdesi no-op edilirse "kirmizi yok" diye YESIL yanmasin diye vardir.
BEKLENEN = (1, 2, 3, 4, 5, 6, 7)


def suite_butunlugu(sonuc, beklenen):
    """(hatalar) — SAF fonksiyon; oz-nobetci (TEST 7) bunu POZITIF+NEGATIF surer."""
    hatalar = []
    gorulen = [s[0] for s in sonuc]
    eksik = [n for n in beklenen if n not in gorulen]
    mukerrer = sorted(set(str(n) for n in gorulen if gorulen.count(n) > 1))
    fazla = sorted(set(str(n) for n in gorulen if n not in beklenen))
    if eksik:
        hatalar.append("SUITE EKSIK: %s numarali test(ler) hic KAYIT ETMEDI -> govdesi "
                       "silinmis/atlanmis olabilir; 'kirmizi yok' YESIL DEMEK DEGILDIR"
                       % ", ".join(str(n) for n in eksik))
    if mukerrer:
        hatalar.append("SUITE MUKERRER: %s numarasi birden fazla kayit etti"
                       % ", ".join(mukerrer))
    if fazla:
        hatalar.append("SUITE BEYAN DISI: %s numarali test BEKLENEN demetinde yok "
                       "(test eklendiyse demeti guncelle)" % ", ".join(fazla))
    return hatalar


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("OK" if gecti else "FAIL", no, ad,
                                    (" | " + detay) if detay else ""), flush=True)


# ------------------------------------------------------------------ fikstur
# UYARI: fiksturdeki kisisel degerlerin KELIMELERI ciktinin baska bir yerinde
# (urun basligi, siparis no, tutar) GECMEMELI — yoksa tarayici sahte-kirmizi yanar.
# Urun basliklari bu yuzden bilerek "Test"/"Musteri"/"Ayse" icermez.
FIKSTUR = [
    {
        "siparis_no": "PR-260101-000001-AAA",
        "tarih": "2026-01-01T10:00:00.000Z",
        "durum": "odendi",
        "odeme_yontemi": "kart",
        "tutar_kurus": 12345,
        "kargo_kurus": 25000,
        "kdv_kurus": 6111,
        "musteri_ad": "Test Musteri",
        "musteri_tel": "5551112233",
        "urunler": json.dumps([{
            "id": "braket-govdesi",
            "baslik": "Braket Govdesi",
            "malzeme": "PLA",
            "renk": "Kirmizi",
            "adet": 3,
            "tutar_kurus": 12345,
        }]),
    },
    {
        "siparis_no": "PR-260102-000002-BBB",
        "tarih": "2026-01-02T08:30:00.000Z",
        "durum": "bekliyor",
        "odeme_yontemi": "havale",
        "tutar_kurus": 40000,
        "kargo_kurus": 0,
        "kdv_kurus": 8000,
        "musteri_ad": "Ayse",
        "musteri_tel": "+905559998877",
        "urunler": json.dumps([{
            "id": "kapak-somunu",
            "baslik": "Kapak Somunu",
            "malzeme": "PETG",
            "renk": "Siyah",
            "adet": 1,
            "tutar_kurus": 40000,
        }]),
    },
]

# Yeni bir kisisel kolon eklenirse SADECE buraya eklemek yeter — tarayici GENELDIR.
KISISEL_ALANLAR = ("musteri_ad", "musteri_tel")


def _aranan_parcalar(deger):
    """Bir kisisel degerden ARANACAK sizinti imzalarini uretir.

    (a) ham degerin kendisi (buyuk/kucuk harf duyarsiz — 'musteri:' etiketiyle
        cakismaz cunku etiket tek basina tam adi icermez),
    (b) >=2 harfli her KELIME (harf duyarli; 'Musteri' ile etiket 'musteri:'
        birbirine karismasin diye),
    (c) rakam dizisinin SON-4 DISINDAKI oneki (>=5 hane varsa) — maskeleme
        yalniz son 4'u acik birakir, onek ciktida ASLA olmamali.
    """
    deger = (deger or "").strip()
    if not deger:
        return []
    parcalar = [("ham deger", deger, False)]
    for kelime in deger.split():
        if len(kelime) >= 2 and kelime != deger:
            parcalar.append(("kelime", kelime, True))
    rakam = "".join(c for c in deger if c.isdigit())
    if len(rakam) >= 5:
        parcalar.append(("rakam oneki (son-4 disi)", rakam[:-4], True))
    return parcalar


def sizinti_tara(metin, satirlar):
    """(bulgular) — GENEL sizinti tarayicisi. TEST 3 ve TEST 6 AYNISINI kullanir.

    Fiksturdeki her satirin her KISISEL alani icin uretilen imzalari metinde arar.
    Bulunan her imza bir SIZINTI bulgusu doner (bos liste = temiz)."""
    bulgular = []
    dusuk = metin.lower()
    for i, row in enumerate(satirlar, 1):
        for alan in KISISEL_ALANLAR:
            for tur, imza, harf_duyarli in _aranan_parcalar(row.get(alan)):
                if not imza:
                    continue
                gecti = (imza in metin) if harf_duyarli else (imza.lower() in dusuk)
                if gecti:
                    bulgular.append("satir %d / %s / %s: %r ciktida GECIYOR"
                                    % (i, alan, tur, imza))
    return bulgular


def _kos_main(modul, argv, tty=None):
    """(stdout, stderr) — modulun main()'ini fiksturle kosar. AG YOK: wrangler_sorgu
    ve (istenirse) _tty monkeypatch'lenir, sonra ESKI degerler geri konur."""
    eski_sorgu = modul.wrangler_sorgu
    eski_tty = modul._tty
    cikti, hata = io.StringIO(), io.StringIO()
    modul.wrangler_sorgu = lambda sql: [dict(r) for r in FIKSTUR]
    if tty is not None:
        modul._tty = lambda: tty
    try:
        with redirect_stdout(cikti), redirect_stderr(hata):
            modul.main(argv)
    finally:
        modul.wrangler_sorgu = eski_sorgu
        modul._tty = eski_tty
    return cikti.getvalue(), hata.getvalue()


# ------------------------------------------------------------------ testler

def test_1_birim():
    vakalar = [
        ("maskele_ad(None)", siparisler.maskele_ad(None), "-"),
        ("maskele_ad('')", siparisler.maskele_ad(""), "-"),
        ("maskele_ad('   ')", siparisler.maskele_ad("   "), "-"),
        ("maskele_ad('Test Musteri')", siparisler.maskele_ad("Test Musteri"), "T*** M***"),
        ("maskele_ad('Ayse')", siparisler.maskele_ad("Ayse"), "A***"),
        ("maskele_ad('A')", siparisler.maskele_ad("A"), "A***"),
        ("maskele_ad('Ali Veli Deli')", siparisler.maskele_ad("Ali Veli Deli"),
         "A*** V*** D***"),
        ("maskele_tel(None)", siparisler.maskele_tel(None), "-"),
        ("maskele_tel('')", siparisler.maskele_tel(""), "-"),
        ("maskele_tel('5551112233')", siparisler.maskele_tel("5551112233"), "******2233"),
        ("maskele_tel('+905551112233')", siparisler.maskele_tel("+905551112233"),
         "*********2233"),
        ("maskele_tel('123') (4 haneden kisa -> tamami *)",
         siparisler.maskele_tel("123"), "***"),
    ]
    kotu = ["%s -> %r (beklenen %r)" % (ad, gorulen, bek)
            for ad, gorulen, bek in vakalar if gorulen != bek]
    kayit(1, "maskele_ad / maskele_tel birim vakalari", not kotu,
          ("BOZUK=%s" % kotu) if kotu else "%d/%d vaka" % (len(vakalar), len(vakalar)))


def test_2_format_varsayilan_maskeli():
    hatalar = []
    for i, row in enumerate(FIKSTUR, 1):
        blok = siparisler.format_siparis(row)          # VARSAYILAN — bayrak YOK
        for alan in KISISEL_ALANLAR:
            if (row[alan] or "").strip() in blok:
                hatalar.append("satir %d: HAM %s blokta GECIYOR" % (i, alan))
        for beklenen in (siparisler.maskele_ad(row["musteri_ad"]),
                         siparisler.maskele_tel(row["musteri_tel"])):
            if beklenen not in blok:
                hatalar.append("satir %d: maskeli %r blokta YOK" % (i, beklenen))
    kayit(2, "format_siparis VARSAYILAN maskeli (ham yok, maskeli var)", not hatalar,
          ("BULGU=%s" % hatalar) if hatalar else "2 fikstur satiri")


def test_3_uctan_uca_sizinti():
    cikti, hata = _kos_main(siparisler, [])
    bulgular = sizinti_tara(cikti + hata, FIKSTUR)
    saglik = "PRUVO SIPARISLER" in cikti and "Toplam: 2 siparis" in cikti
    kayit(3, "uctan uca: main([]) ciktisinda SIFIR kisisel deger",
          not bulgular and saglik,
          ("SIZINTI=%s" % bulgular) if bulgular
          else ("" if saglik else "cikti beklenen bicimde degil (tarayici bos metni "
                                  "taramis olabilir)"))


def test_4_acik_tty_yok_fail_closed():
    cikti, hata = _kos_main(siparisler, ["--acik"], tty=False)
    bulgular = sizinti_tara(cikti, FIKSTUR)
    uyari_var = siparisler.UYARI_ACIK_YOKSAYILDI in hata
    kayit(4, "--acik + TTY YOK -> maskeli + stderr uyarisi (fail-closed)",
          not bulgular and uyari_var,
          ("SIZINTI=%s" % bulgular) if bulgular
          else ("" if uyari_var else "stderr'de uyari YOK: %r" % hata[-200:]))


def test_5_acik_tty_var_ham():
    cikti, _hata = _kos_main(siparisler, ["--acik"], tty=True)
    eksik = []
    for row in FIKSTUR:
        for alan in KISISEL_ALANLAR:
            if row[alan] not in cikti:
                eksik.append("%s=%r" % (alan, row[alan]))
    kayit(5, "--acik + TTY VAR -> ham ad/tel GERCEKTEN basiliyor (pozitif eksen)",
          not eksik, ("EKSIK=%s" % eksik) if eksik else "4/4 ham deger")


# ---------------------------------------------------------- kirmizi mutasyon
# Maskeleme govdelerini KIMLIK fonksiyonuna cevirir. Capa TUTMAZSA (kaynak
# degismis) SESSIZ ATLAMA YOK -> KIRMIZI.
MUTASYONLAR = (
    (re.compile(r"^def maskele_ad\(ad\):\n(?:[ \t].*\n|[ \t]*\n)*", re.M),
     'def maskele_ad(ad):\n    return ad or "-"\n\n\n'),
    (re.compile(r"^def maskele_tel\(tel\):\n(?:[ \t].*\n|[ \t]*\n)*", re.M),
     'def maskele_tel(tel):\n    return tel or "-"\n\n\n'),
)


def test_6_kirmizi_mutasyon():
    kaynak_yolu = os.path.join(TOOLS, "siparisler.py")
    with open(kaynak_yolu, encoding="utf-8") as f:
        kaynak = f.read()

    mutant_kaynak = kaynak
    for kalip, yeni in MUTASYONLAR:
        mutant_kaynak, n = kalip.subn(yeni, mutant_kaynak, count=1)
        if n != 1:
            kayit(6, "kirmizi-mutasyon: maske sokulmus kopyada sizinti goruluyor", False,
                  "MUTASYON CAPASI TUTMADI (%r) — siparisler.py degismis; nobetci "
                  "sessizce ATLAMAZ" % kalip.pattern)
            return

    gecici = tempfile.mkdtemp(prefix="pruvo-maske-mutant-")
    try:
        mutant_yolu = os.path.join(gecici, "siparisler_mutant.py")
        with open(mutant_yolu, "w", encoding="utf-8") as f:
            f.write(mutant_kaynak)
        spec = importlib.util.spec_from_file_location("siparisler_mutant", mutant_yolu)
        mut = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mut)

        # mutant GERCEKTEN sokulmus mu (yoksa "sizinti yok" anlamsiz olurdu)
        if (mut.maskele_ad("Test Musteri") != "Test Musteri"
                or mut.maskele_tel("5551112233") != "5551112233"):
            kayit(6, "kirmizi-mutasyon: maske sokulmus kopyada sizinti goruluyor", False,
                  "mutant KIMLIK degil (ad=%r tel=%r) — mutasyon islememis"
                  % (mut.maskele_ad("Test Musteri"), mut.maskele_tel("5551112233")))
            return

        cikti, hata = _kos_main(mut, [])
        bulgular = sizinti_tara(cikti + hata, FIKSTUR)   # TEST 3'un AYNI tarayicisi
        kayit(6, "kirmizi-mutasyon: maske sokulmus kopyada sizinti goruluyor",
              bool(bulgular),
              ("%d bulgu" % len(bulgular)) if bulgular
              else "NOBETCI OLU: maske sokulmus kopyada bile sizinti GORMUYOR")
    finally:
        sys.modules.pop("siparisler_mutant", None)
        shutil.rmtree(gecici, ignore_errors=True)


def test_7_oz_nobetci(beklenen):
    tam = [(n, "sentetik", True) for n in beklenen]
    eksikli = [v for v in tam if v[0] != 3]
    vakalar = [
        ("negatif: tam kume temiz -> hata YOK",
         suite_butunlugu(tam, beklenen) == []),
        ("pozitif: bir test hic kayit etmezse -> SUITE EKSIK",
         any("SUITE EKSIK" in h for h in suite_butunlugu(eksikli, beklenen))),
        ("pozitif: ayni numara iki kez kayit ederse -> SUITE MUKERRER",
         any("SUITE MUKERRER" in h for h in suite_butunlugu(tam + [tam[0]], beklenen))),
        ("pozitif: beyan disi numara -> SUITE BEYAN DISI",
         any("SUITE BEYAN DISI" in h
             for h in suite_butunlugu(tam + [("z9", "sentetik", True)], beklenen))),
        ("pozitif: tarayici SAHTE-TEMIZ degil (ham fikstur metni -> bulgu)",
         bool(sizinti_tara("musteri: Test Musteri | 5551112233", FIKSTUR))),
        ("negatif: maskeli metin -> tarayici TEMIZ",
         sizinti_tara("musteri: T*** M*** | ******2233\nmusteri: A*** | *********8877",
                      FIKSTUR) == []),
    ]
    kotu = [ad for ad, iyi in vakalar if not iyi]
    kayit(7, "oz-nobetci: suite_butunlugu + sizinti_tara pozitif+negatif eksende",
          not kotu, ("BOZUK=%s" % kotu) if kotu else "%d/%d eksen" % (len(vakalar),
                                                                     len(vakalar)))


def main():
    print("SIPARIS MASKELEME NOBETCISI (fiksturle — canli D1'e DOKUNMAZ)")
    print("=" * 66)
    test_1_birim()
    test_2_format_varsayilan_maskeli()
    test_3_uctan_uca_sizinti()
    test_4_acik_tty_yok_fail_closed()
    test_5_acik_tty_var_ham()
    test_6_kirmizi_mutasyon()
    test_7_oz_nobetci(BEKLENEN)
    print("=" * 66)
    hatalar = suite_butunlugu(SONUC, BEKLENEN)
    for h in hatalar:
        print("  BULGU — %s" % h)
    basarisiz = [s for s in SONUC if not s[2]]
    print("SONUC: %d/%d GECTI%s" % (len(SONUC) - len(basarisiz), len(SONUC),
                                     " | SUITE BUTUNLUGU KIRMIZI" if hatalar else ""))
    return 1 if (basarisiz or hatalar) else 0


if __name__ == "__main__":
    sys.exit(main())

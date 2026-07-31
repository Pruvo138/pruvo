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

OLCUT KANALDIR, ALAN DEGIL: TTY disina (boru, `>` yonlendirme, `2>&1`,
capture_output, CI) ham musteri verisi ve musteri serbest metni CIKMAZ — stdout
da stderr de dahil. Tarayici hem stdout'u hem stderr'i tarar.

  1. maskele_ad / maskele_tel birim vakalari (bos, tek harf, kisa, +90'li, cok kelimeli)
  2. format_siparis(fikstur) VARSAYILAN -> HAM ad/tel YOK, MASKELI bicimler VAR
  3. UCTAN UCA SIZINTI TARAYICI — main([]) stdout+stderr'inde fiksturun HICBIR
     kisisel degeri (ham / kelime / telefonun son-4 disindaki basamak dizisi) GECMEZ
  4. `--acik` + TTY YOK -> cikti MASKELI + stderr'de tek satir uyari (FAIL-CLOSED)
  5. `--acik` + TTY VAR -> cikti HAM (pozitif eksen: maskeleme "her seyi yildiza
     cevir" gibi anlamsiz bir seye donuserse bu eksen kirmizi yanar)
  6. KIRMIZI-MUTASYON KANITI — IKI mutant kopya tempdir'e yazilir, importlib ile
     yuklenir, (3)'teki AYNI tarayici uygulanir; HER IKISINDE de SIZINTI BULUNMALI:
       (A) maskeleme sokulmus (maskele_ad/maskele_tel -> KIMLIK)
       (B) KANAL kapisi sokulmus (`_tty()` -> her zaman True)
     Bulamazsa nobetci OLU demektir -> KIRMIZI.
  7. OZ-NOBETCI — suite_butunlugu() pozitif+negatif eksende olculur; eksik/mukerrer/
     beyan-disi kayit KIRMIZI.
  8. `parametre_detay` (musteri SERBEST METNI, maskelenemez) TTY yokken ciktida
     HIC YOK (yer tutucu var) / TTY varken VAR (pozitif eksen).
  9. `wrangler_sorgu` HATA YOLLARI — ham dokum (SELECT sonucunun ham JSON'u) TTY
     yokken sizmiyor ve teshis KORUNUYOR / TTY varken siziyor (pozitif eksen).

🔴 BEYAN SINIRI (curutucu olctu, kabul edildi): buradaki oz-nobetci CAGRI SILME
fail-open'ini kapatir — bir testin cagrisi silinir ya da govdesi no-op edilirse
`suite_butunlugu()` KIRMIZI yakar. Ama bir testin cagrisi VE `BEKLENEN` demetindeki
numarasi BIRLIKTE silinirse suite YESIL kalir (olculdu: TEST 4 + `--acik` kapisi
sokumu -> rc=0). Bu, tasarimin KABUL EDILEN SINIRIDIR: beyani dusurmek iki satirlik
bir duzenlemedir ve DIFF'TE GORUNUR. "Bu dosyada hicbir bosaltma fail-open'i yok"
DEMEK YANLIS OLUR.
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
BEKLENEN = (1, 2, 3, 4, 5, 6, 7, 8, 9)


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
            # MUSTERI SERBEST METNI — icine bilerek ad+telefon konuldu.
            "parametre_detay": "Kaziyacak yazi: Kemal Ozturk 5327776655",
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

# Yeni bir kisisel alan eklenirse SADECE bu IKI demete yazmak yeter — tarayici GENELDIR.
KISISEL_ALANLAR = ("musteri_ad", "musteri_tel")            # siparis satiri kolonlari
# Kalem (urunler JSON) icindeki MUSTERI SERBEST METNI alanlari: maskelenemez, TTY
# disinda HIC BASILMAZ. `baslik` BILEREK YOK — o KATALOG verisidir (urunler.json'dan
# gelir), musteri metni degildir.
KALEM_KISISEL_ALANLAR = ("parametre_detay",)


def _kisisel_degerler(row):
    """(alan, deger) ciftleri — satir kolonlari + kalem (urunler JSON) alanlari."""
    for alan in KISISEL_ALANLAR:
        yield alan, row.get(alan)
    try:
        kalemler = json.loads(row.get("urunler") or "[]")
    except (ValueError, TypeError):
        kalemler = []
    if not isinstance(kalemler, list):
        kalemler = []
    for k in kalemler:
        if not isinstance(k, dict):
            continue
        for alan in KALEM_KISISEL_ALANLAR:
            yield "urunler[].%s" % alan, k.get(alan)


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
    """(bulgular) — GENEL sizinti tarayicisi. TEST 3/4/6/8/9 AYNISINI kullanir.

    `metin` STDOUT + STDERR birlestirilmis olarak verilir (kanal kurali her ikisini
    de kapsar). Fiksturdeki her satirin her KISISEL alani icin uretilen imzalari arar.
    Bulunan her imza bir SIZINTI bulgusu doner (bos liste = temiz)."""
    bulgular = []
    dusuk = metin.lower()
    for i, row in enumerate(satirlar, 1):
        for alan, deger in _kisisel_degerler(row):
            for tur, imza, harf_duyarli in _aranan_parcalar(deger):
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
    bulgular = sizinti_tara(cikti + hata, FIKSTUR)   # STDERR de taranir (kanal kurali)
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
# IKI ayri kapi, IKI ayri mutant. Capa TUTMAZSA (kaynak degismis) SESSIZ ATLAMA
# YOK -> KIRMIZI. (A) maskeleme govdelerini KIMLIK'e cevirir; (B) KANAL kapisini
# soker (`_tty()` her zaman True) -> parametre_detay TTY disinda da basilir.
MUTANT_A = "A: maskeleme sokuldu (maskele_ad/maskele_tel -> KIMLIK)"
MUTANT_B = "B: kanal kapisi sokuldu (_tty -> her zaman True)"

MUTANTLAR = (
    (MUTANT_A, (
        (re.compile(r"^def maskele_ad\(ad\):\n(?:[ \t].*\n|[ \t]*\n)*", re.M),
         'def maskele_ad(ad):\n    return ad or "-"\n\n\n'),
        (re.compile(r"^def maskele_tel\(tel\):\n(?:[ \t].*\n|[ \t]*\n)*", re.M),
         'def maskele_tel(tel):\n    return tel or "-"\n\n\n'),
    )),
    (MUTANT_B, (
        (re.compile(r"^def _tty\(\):\n(?:[ \t].*\n|[ \t]*\n)*", re.M),
         'def _tty():\n    return True\n\n\n'),
    )),
)


def _mutant_gercekten_sokuldu(ad, mut):
    """(ok, aciklama) — mutant beklenen sekilde BOZULDU mu. Bozulmadiysa
    "sizinti yok" hukmu anlamsiz olurdu -> fail-closed."""
    if ad == MUTANT_A:
        a, t = mut.maskele_ad("Test Musteri"), mut.maskele_tel("5551112233")
        if a != "Test Musteri" or t != "5551112233":
            return False, "mutant KIMLIK degil (ad=%r tel=%r)" % (a, t)
        return True, ""
    # MUTANT_B: StringIO'ya yonlendirilmis stdout'ta ORIJINAL False doner, mutant True
    with redirect_stdout(io.StringIO()):
        deger = mut._tty()
    if deger is not True:
        return False, "mutant _tty() StringIO altinda %r dondu (True bekleniyordu)" % deger
    return True, ""


def test_6_kirmizi_mutasyon():
    kaynak_yolu = os.path.join(TOOLS, "siparisler.py")
    with open(kaynak_yolu, encoding="utf-8") as f:
        kaynak = f.read()

    ozet, kotu = [], []
    for ad, mutasyonlar in MUTANTLAR:
        mutant_kaynak = kaynak
        capa_bozuk = None
        for kalip, yeni in mutasyonlar:
            mutant_kaynak, n = kalip.subn(yeni, mutant_kaynak, count=1)
            if n != 1:
                capa_bozuk = ("MUTASYON CAPASI TUTMADI (%r) — siparisler.py degismis; "
                              "nobetci sessizce ATLAMAZ" % kalip.pattern)
                break
        if capa_bozuk:
            kotu.append("%s -> %s" % (ad, capa_bozuk))
            continue

        gecici = tempfile.mkdtemp(prefix="pruvo-maske-mutant-")
        modul_adi = "siparisler_mutant_%d" % len(ozet)
        try:
            mutant_yolu = os.path.join(gecici, modul_adi + ".py")
            with open(mutant_yolu, "w", encoding="utf-8") as f:
                f.write(mutant_kaynak)
            spec = importlib.util.spec_from_file_location(modul_adi, mutant_yolu)
            mut = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mut)

            ok, neden = _mutant_gercekten_sokuldu(ad, mut)
            if not ok:
                kotu.append("%s -> %s" % (ad, neden))
                continue

            cikti, hata = _kos_main(mut, [])
            bulgular = sizinti_tara(cikti + hata, FIKSTUR)   # TEST 3'un AYNI tarayicisi
            if bulgular:
                ozet.append("%s: %d bulgu" % (ad[:1], len(bulgular)))
            else:
                kotu.append("%s -> NOBETCI OLU: sokulmus kopyada bile sizinti GORMUYOR"
                            % ad)
        finally:
            sys.modules.pop(modul_adi, None)
            shutil.rmtree(gecici, ignore_errors=True)

    kayit(6, "kirmizi-mutasyon: sokulmus IKI kopyada da sizinti goruluyor",
          not kotu, ("BOZUK=%s" % kotu) if kotu else " · ".join(ozet))


# ------------------------------------------------- KANAL EKSENI (yeni, 2. tur)

def test_8_parametre_detay_kanali():
    """MUSTERI SERBEST METNI maskelenemez -> TTY disinda HIC BASILMAZ."""
    ham_detay = json.loads(FIKSTUR[0]["urunler"])[0]["parametre_detay"]
    ttysiz, ttysiz_hata = _kos_main(siparisler, [], tty=False)
    ttyli, _ = _kos_main(siparisler, [], tty=True)
    hatalar = []
    if ham_detay in (ttysiz + ttysiz_hata):
        hatalar.append("TTY YOK iken parametre_detay BASILDI")
    if "parametre detayi:" not in ttysiz:
        hatalar.append("TTY YOK iken YER TUTUCU yok — alan sessizce dusmus olabilir "
                       "(Okan detayin VARLIGINI gormeli)")
    if ham_detay not in ttyli:
        hatalar.append("TTY VAR iken parametre_detay BASILMIYOR — pozitif eksen "
                       "('alani tumden sil' cozumu buradan gecemez)")
    kayit(8, "parametre_detay: TTY disinda YOK (yer tutucu), TTY'de VAR",
          not hatalar, ("BULGU=%s" % hatalar) if hatalar else "3/3 eksen")


class _SahteP:
    """subprocess.CompletedProcess yerine gecen asgari nesne (AG YOK)."""

    def __init__(self, stdout, stderr="", returncode=1):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


class _SahteSubprocess:
    def __init__(self, p):
        self._p = p

    def run(self, *a, **k):
        return self._p


# Fiksturun HAM JSON'u — gercek wrangler ciktisinin sekli (icinde musteri_ad/tel var).
HAM_BASARISIZ = json.dumps([{"success": False, "results": FIKSTUR}])
HAM_COZULEMEZ = "[BOZUK-JSON " + json.dumps([{"success": True, "results": FIKSTUR}])


def _hata_yolu_mesaji(stdout, tty):
    """wrangler_sorgu'yu sahte cikti ile kosar, sys.exit mesajini string dondurur."""
    eski_sp, eski_tty = siparisler.subprocess, siparisler._tty
    siparisler.subprocess = _SahteSubprocess(_SahteP(stdout))
    siparisler._tty = lambda: tty
    try:
        siparisler.wrangler_sorgu("SELECT 1")
        return ""
    except SystemExit as e:
        return str(e)
    finally:
        siparisler.subprocess = eski_sp
        siparisler._tty = eski_tty


def test_9_hata_yolu_kanali():
    """`ham[-2000:]` dokumu SELECT SONUCUDUR — TTY disina cikmamali, teshis kalmali."""
    hatalar = []
    yollar = (("wrangler sorgusu basarisiz:", HAM_BASARISIZ),
              ("wrangler ciktisi cozulemedi:", HAM_COZULEMEZ))
    for baslik, ham in yollar:
        ttysiz = _hata_yolu_mesaji(ham, False)
        ttyli = _hata_yolu_mesaji(ham, True)
        etiket = baslik.split()[-1].rstrip(":")
        if baslik not in ttysiz:
            hatalar.append("%s: beklenen hata yoluna girilmedi (mesaj=%r)"
                           % (etiket, ttysiz[:80]))
            continue
        bulgu_ttysiz = sizinti_tara(ttysiz, FIKSTUR)
        if bulgu_ttysiz:
            hatalar.append("%s: TTY YOK iken %d SIZINTI (%s)"
                           % (etiket, len(bulgu_ttysiz), bulgu_ttysiz[0]))
        if "tani:" not in ttysiz or "exit=" not in ttysiz or "bayt" not in ttysiz:
            hatalar.append("%s: TTY YOK iken TESHIS kayboldu (hata sinifi/exit/bayt "
                           "sayisi basilmali)" % etiket)
        if not sizinti_tara(ttyli, FIKSTUR):
            hatalar.append("%s: TTY VAR iken ham dokum YOK — pozitif eksen ('dokumu "
                           "tumden sil' cozumu buradan gecemez)" % etiket)
    kayit(9, "wrangler hata yollari: ham dokum TTY disina CIKMIYOR, teshis KALIYOR",
          not hatalar, ("BULGU=%s" % hatalar) if hatalar else "2 yol × 3 eksen")


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
    test_8_parametre_detay_kanali()
    test_9_hata_yolu_kanali()
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

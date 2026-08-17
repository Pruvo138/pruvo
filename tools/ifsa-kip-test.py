#!/usr/bin/env python3
r"""ifsa-kip-test.py — URETIM-SURECI IFSASI: KIP EKSENI kabul testi + mutasyon bataryasi.

NE OLCER (iki dosya, TEK sozlesme):
  * tools/denetim-kapisi.py — 17 Agu 2026'da eklenen KIP genislemesi:
      B1  `_SUREC_TOKEN_RE` += malzemeden|malzemeyle|malzemesiyle
      B2  SERT kural `uretim-kipi-basil`
      B3  SERT kural `baski-surec-cekimi`
  * tools/ifsa-metin-onar.py — Okan onayli (17 Agu) kalip tablosu.

🔴 NEDEN AYRI DOSYA (ve neden denetim-kapisi --kendini-test'e EKLENMEDI):
`denetim-kapisi.py --kendini-test` bataryasi `_IFSA_DESEN_ARA` capasina nisanli.
O bataryaya AYNI metinli yeni kollar eklemek capayi IKIZLER ve mutasyon olu bir kola
nisanlanir — bu depoda bir kez olculdu ve yayini durdurdu ([[yeni-kol-mutasyon-capasini-ikizler]]).
Yeni sinif KENDI capasiyla, KENDI dosyasinda olculur.

🔴 EN ONEMLI IDDIA — IKIZ-TANIM KAPISI (bolum D):
Kapi ile onarim araci AYRI dosyalarda AYNI gercegi (neyin ifsa oldugunu) tanimlar; ikisi
sessizce ayrisabilir ([[ikiz-tanim-sessiz-ayrisma]]). D bolumu her POZITIF vakayi once
onarim aracindan gecirir, SONRA kapiya sorar: **kapi SERT dememeli**. Kapiya yeni bir
sinif eklenip onarim tablosuna karsiligi yazilmazsa bu test KIRMIZI yanar.

CIKIS: 0 = hepsi gecti · 1 = en az bir iddia KIRMIZI.
Kullanim:
    python3 tools/ifsa-kip-test.py
"""
import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

_GECEN = 0
_KALAN = []


def _yukle(dosya, ad):
    s = importlib.util.spec_from_file_location(ad, os.path.join(TOOLS, dosya))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def iddia(baslik, kosul, ayrinti=""):
    global _GECEN
    if kosul:
        _GECEN += 1
    else:
        _KALAN.append("%s%s" % (baslik, (" — " + ayrinti) if ayrinti else ""))


def _sert(dk, metin, baslik=""):
    """Kapinin bu metin icin urettigi SERT kural adlari."""
    r = dk.kapi_ifsa({"baslik": baslik, "aciklama": metin})
    return sorted({s["kural"] for s in r["sert"]})


# =============================================================================
# VAKALAR — hepsi 17 Agu 2026'da CANLI katalogda GORULMUS metinlerden turetildi.
# =============================================================================
# (etiket, metin, o vakayi yakalamasi BEKLENEN kapi kurali)
POZITIF = (
    ("K1 malzemeden basilir",
     "Sert malzemeden basılır.", "baski-fiili"),
    ("K1b darbeye dayanikli",
     "Darbeye dayanıklı sert malzemeden basılır.", "baski-fiili"),
    ("K1c malzemeyle",
     "Gövde dayanıklı malzemeyle basılır.", "baski-fiili"),
    ("K2 malzemeden basilmasi",
     "Esnek malzemeden basılması önerilir.", "baski-fiili"),
    ("K3a saglam",
     "İnce ama sağlam basılır.", "uretim-kipi-basil"),
    ("K3b sadik",
     "Orijinal ölçülere sadık basılır.", "uretim-kipi-basil"),
    ("K4 basilmadan once",
     "Ölçek basılmadan önce araca göre kalibre edilmelidir.", "uretim-kipi-basil"),
    ("K5a dekoratif baski modeli",
     "1958 model Vespa Piaggio 400'ün dekoratif baskı modeli.", "baski-surec-cekimi"),
    ("K5b baski sonrasi",
     "Baskı sonrası tolerans ayarı gerekebilir.", "baski-surec-cekimi"),
    ("K5c test baskisi",
     "Ölçüsel doğruluğu test baskısıyla teyit edilmiş yedek parçadır.",
     "baski-surec-cekimi"),
    ("K5d baskiyla uretilen",
     "Baskıyla üretilen cam ve gövde takımı.", "baski-surec-cekimi"),
    ("K5e baskida olcek",
     "Tek STL; baskıda ölçek serbest.", "baski-surec-cekimi"),
    ("K5f baski muhafaza",
     "Sigorta kutusu için baskı muhafazadır.", "baski-surec-cekimi"),
    ("K5g baskida marka",
     "Baskıda marka logosu taşımaz.", "baski-surec-cekimi"),
)

# YANLIS-POZITIF NOBETI: bunlarin HICBIRI SERT olmamali (press = BASMA, basinc = KUVVET).
NEGATIF = (
    ("press dugme", "Panik düğmesine yanlışlıkla basılmasını önler."),
    ("press tus", "Cepte veya çantada yanlışlıkla basılan anahtar tuşlarını önler."),
    ("press ayak", "Ayakla basılan geniş yüzeyli pedal koruyucusudur."),
    ("press parmak", "Geniş başlığı parmakla rahat basılır."),
    ("press fitil", "Fitil hafifçe çekilir, sonra fitil yerine basılır."),
    ("basinc otur", "Hafif baskıyla yuvasına oturtur."),
    ("basinc balata", "Debriyaj baskı balatası merkezleme aletidir."),
    ("basinc yay", "Yay baskısı sayesinde yerinde durur."),
    ("basinc su", "Su baskınına karşı kabloları korur."),
    ("basinc takoz", "Kaporta baskı takozu, üst kapaklar ve montaj şablonundan oluşur."),
    ("basinc yuzey", "Geniş pad, muhafazanın gövdeye baskı yapan yüzeyini büyütür."),
    # 🔴 B1'IN ACTIGI YANLIS-POZITIF YUZEYI — TAM BURASI OLCULUR:
    # `malzemeden` artik bir SUREC JETONU. Ayni cumlede hem malzeme tumleci hem de
    # BASILAN NESNE varsa cumle BASMA'dir; kapiyi SERT yakmamali. Bu vaka M4 mutantinin
    # da capasidir (press suzgeci oldurulunce BU cumle SERT olur).
    ("press + malzeme jetonu", "Yumuşak malzemeden yapılan pedala rahatça basılır."),
)

# ONARIM TABLOSU — (etiket, girdi, beklenen cikti)
ONARIM = (
    ("O1", "Sert malzemeden basılır.", "Sert malzemeden üretilir."),
    ("O2", "Darbeye dayanıklı sert malzemeden basılır.",
     "Darbeye dayanıklı sert malzemeden üretilir."),
    ("O3", "Esnek malzemeden basılması önerilir.", "Esnek malzemeden üretilmesi önerilir."),
    ("O4", "İnce ama sağlam basılır.", "İnce ama sağlam üretilir."),
    ("O5", "Ölçek basılmadan önce araca göre kalibre edilmelidir.",
     "Ölçek üretilmeden önce araca göre kalibre edilmelidir."),
    ("O6", "1958 model Vespa'nın dekoratif baskı modeli.",
     "1958 model Vespa'nın dekoratif modeli."),
    ("O7", "Baskı sonrası tolerans ayarı gerekebilir.",
     "Üretim sonrası tolerans ayarı gerekebilir."),
    ("O8", "Baskıyla üretilen cam ve gövde takımı.", "Özel üretilen cam ve gövde takımı."),
    ("O9", "Tek STL; baskıda ölçek serbest.", "Tek STL; üretimde ölçek serbest."),
    # DOKUNULMAZ — press/basinc
    ("O10", "Panik düğmesine yanlışlıkla basılmasını önler.", None),
    ("O11", "Geniş başlığı parmakla rahat basılır.", None),
    ("O12", "Hafif baskıyla yuvasına oturtur.", None),
    ("O13", "Yay baskısı sayesinde yerinde durur.", None),
)


def kos():
    global _GECEN, _KALAN
    _GECEN, _KALAN = 0, []
    dk = _yukle("denetim-kapisi.py", "dk_ifsa_kip")
    onar = _yukle("ifsa-metin-onar.py", "onar_ifsa_kip")

    # === A) KAPI — POZITIF (yeni kip sinifi SERT olmali) =============================
    for etiket, metin, beklenen in POZITIF:
        kurallar = _sert(dk, metin)
        iddia("A/%s SERT" % etiket, beklenen in kurallar,
              "beklenen kural %r, gorulen %s" % (beklenen, kurallar or "SERT YOK"))

    # === B) KAPI — YANLIS-POZITIF NOBETI ============================================
    # Bir kapiyi genisletmenin bedeli budur: genisleme MESRU kaydi kirmizi yakarsa
    # urun akisi durur. Her negatif vaka canli katalogdan alindi.
    for etiket, metin in NEGATIF:
        kurallar = _sert(dk, metin)
        iddia("B/%s SERT DEGIL" % etiket, not kurallar,
              "beklenmeyen SERT: %s" % kurallar)

    # === C) ONARIM ARACI — kalip dogrulugu ==========================================
    for etiket, girdi, beklenen in ONARIM:
        cikti, _ = onar.onar_metin(girdi)
        hedef = girdi if beklenen is None else beklenen
        iddia("C/%s onarim" % etiket, cikti == hedef,
              "beklenen %r, gorulen %r" % (hedef, cikti))

    # C-EK1: otomatik uretilen OLCU SATIRI onarimdan SAG cikmali (duzelt.py'nin
    # aciklama_koru'su ikinci bir agdir ama arac zaten dusurmemeli).
    olculu = "Sert malzemeden basılır.\nYaklaşık dış ölçüler: 49 × 49 × 29 mm."
    cikti, _ = onar.onar_metin(olculu)
    iddia("C/olcu satiri korunur", "Yaklaşık dış ölçüler: 49 × 49 × 29 mm." in cikti,
          "gorulen %r" % cikti)

    # C-EK2 🔴 TURKCE UNLU UYUMU (gelistirmede YAKALANMIS gercek kusur):
    # `basıl` KALIN, `üretil` INCE siralidir. Eki oldugu gibi tasiyan bir donusum
    # ("bas[ıi]l(...)" -> "üretil\1") 216 canli aciklamaya "üretilır" yazardi.
    # Iddia: hicbir cikti KALIN ekli bozuk bicim URETMEZ.
    bozuk = re.compile(r"üretil(?:[ıa]r|maz|mad|mas|acak|an\b|ab[ıi]l)", re.UNICODE)
    for _e, girdi, _b in ONARIM:
        c, _ = onar.onar_metin(girdi)
        iddia("C/unlu uyumu %r" % girdi[:28], bozuk.search(c) is None,
              "KALIN ekli bozuk bicim: %r" % c)

    # C-EK3: BUYUK HARF. Kapi metni tr_lower'layip bakar, arac CANLI metni aynen yazar;
    # kucuk-harf duyarli bir desen cumle BASINDAKI bicimi kacirir ve iki taraf ayrisir.
    c, _ = onar.onar_metin("Baskı sonrası tolerans ayarı gerekebilir.")
    iddia("C/buyuk harf geri yazilir", c == "Üretim sonrası tolerans ayarı gerekebilir.",
          "gorulen %r" % c)

    # C-EK4 FAIL-CLOSED: kalip tablosunda OLMAYAN bir kip YANLIS onarilmaz, DOKUNULMAZ.
    # (Kapsam disi kip "bozuk yazilmis" degil "onarilmamis" olmali; ELLE kovasi gorur.)
    ozel = "Parça basıldıysa yüzey zımparalanır."
    c, uyg = onar.onar_metin(ozel)
    iddia("C/bilinmeyen kip DOKUNULMAZ", c == ozel and not uyg,
          "gorulen %r (kalip %s)" % (c, uyg))

    # === D) IKIZ-TANIM KAPISI (bu dosyanin ASIL isi) ================================
    # Kapinin SERT dedigi her POZITIF vaka, onarim aracindan gectikten SONRA KIP
    # EKSENINDEN temiz cikmali. Kapiya yeni bir KIP sinifi eklenip onarim tablosuna
    # karsiligi yazilmazsa burasi KIRMIZI yanar -> iki tanim SESSIZCE ayrisamaz.
    #
    # ⚠️ KAPSAM BILEREK KIP EKSENIYLE SINIRLI (KIP_KURALLARI): onarim tablosu 'baskı/
    #   basıl-' dilini onarir, TUM ifsa siniflarini DEGIL. Ornek: "Tek STL; baskıda ölçek
    #   serbest." onarildiktan sonra `dosya-ifsasi` (STL) kuralindan HALA SERT'tir — ve
    #   OYLE OLMALI; o ayri bir ihlal sinifi, ayri bir is. Iddiayi "hic SERT kalmasin"
    #   diye yazmak, kapsam disi bir sinifi bu tablonun sirtina yikar ve ya testi kalici
    #   kirmizi tutar ya da (daha kotusu) tabloyu alakasiz sinifa genisletmeye zorlar
    #   ([[kapi-kapsam-genisletme-tuzagi]]).
    # TEK KAYNAK: kume onarim aracindan gelir (test KENDI kopyasini TUTMAZ). Ayrica
    # her adin kapida GERCEKTEN var oldugu iddia edilir — bir kural yeniden adlandirilirsa
    # bu liste sessizce bayatlamasin ([[jeton-listesi-kapsam-kaniti-degildir]]).
    KIP_KURALLARI = onar.KIP_KURALLARI
    _kapi_adlari = {t[0] for t in dk._IFSA_SERT_RE} | {"baski-fiili"}   # baski-fiili konjonksiyon kolunda
    iddia("D/KIP_KURALLARI kapida GERCEKTEN var", KIP_KURALLARI <= _kapi_adlari,
          "kapida olmayan: %s" % sorted(KIP_KURALLARI - _kapi_adlari))
    for etiket, metin, _bek in POZITIF:
        onarilmis, _ = onar.onar_metin(metin)
        kalan = [k for k in _sert(dk, onarilmis) if k in KIP_KURALLARI]
        iddia("D/%s onarim sonrasi KIP-TEMIZ" % etiket, not kalan,
              "onarim sonrasi hala SERT: %s — metin %r" % (kalan, onarilmis))

    # D-EK: cumle sinirlari TEK KAYNAK. Iki dosyada desen ayrisirsa 'ayni cumle'
    # tanimi kayar; kapinin mesru saydigini onarim araci bozabilir (ya da tersi).
    iddia("D/cumle sinirlari BIREBIR ayni",
          onar._CUMLE_SON_RE.pattern == dk._CUMLE_SON_RE.pattern,
          "onar=%r kapi=%r" % (onar._CUMLE_SON_RE.pattern, dk._CUMLE_SON_RE.pattern))

    # === E) OKAN YASAKLARI KODA BAGLI MI ============================================
    # (yorum notu yeterli DEGIL — davranis iddia edilir)
    iddia("E/onarim araci YALNIZ metin alani yazar",
          tuple(onar.YAZILABILIR_ALANLAR) == ("baslik", "aciklama"),
          "gorulen %r" % (onar.YAZILABILIR_ALANLAR,))
    for yasak in ("fiyat", "lisans", "uyelik", "tasarimci", "gorseller", "parametrik"):
        iddia("E/%s alanina DOKUNMAZ" % yasak, yasak not in onar.YAZILABILIR_ALANLAR)
    # URUN SILMEZ: uretilen her islem 'alan'+'deger' tasir, 'sil' TASIMAZ.
    ornek = {"id": "x", "aciklama": "Sert malzemeden basılır."}
    islemler, _kal, _kalinti = onar.urun_onar(ornek)
    iddia("E/uretilen islemler SILME TASIMAZ",
          bool(islemler) and all(set(i) == {"id", "alan", "deger"} for i in islemler),
          "gorulen %r" % (islemler,))
    kaynak = open(os.path.join(TOOLS, "ifsa-metin-onar.py"), encoding="utf-8").read()
    iddia("E/kaynakta --sil / --evet-sil cagrisi YOK",
          '"--sil"' not in kaynak and "--evet-sil" not in kaynak.split('"""', 2)[-1])

    # === G) KARMA CUMLE SINIFI (CI kolunda OLCULMUS gercek kusur) ===================
    # Ayni cumlede hem KIP ihlali hem BASKA bir ihlal varsa yarim onarim, oteki ihlalin
    # `gerekce` metnini degistirir; `--commit-farki` onu "bu itmenin GETIRDIGI" sanar ve
    # TUM EKIBIN yayinini durdurur (olculdu: `cup-holder-100mm-dacia-logan-2009` tek
    # basina rc=1 verdi). Kural: boyle kayda HIC DOKUNULMAZ.
    karma_urun = {
        "id": "zz-karma-cumle",
        "baslik": "",
        "aciklama": ("Baskı sonrası tolerans ayarı için STL editörü ile montaj boşluğu "
                     "düzenlenebilir.\nYaklaşık dış ölçüler: 40 × 30 × 10 mm."),
    }
    sert_fn = onar._kapi_sert()
    # (a) fikstur GERCEKTEN karma mi — capa bayatlarsa test bos yere yesil yanmasin
    _k = _sert(dk, karma_urun["aciklama"])
    iddia("G/fikstur GERCEKTEN karma", "baski-surec-cekimi" in _k and "dosya-ifsasi" in _k,
          "gorulen kurallar: %s" % _k)
    # (b) ham kalip motoru cumleyi DEGISTIRIR (yani atlama, 'zaten eslesmiyor' DEGIL)
    ham, _ = onar.onar_metin(karma_urun["aciklama"])
    iddia("G/ham kalip cumleyi degistirirdi", ham != karma_urun["aciklama"])
    # (c) ...ama YAN IHLAL IMZASI kaydigi icin arac DOKUNMAZ
    _islem, _kal, _onarilmis = onar.urun_onar(karma_urun)
    iddia("G/yan ihlal imzasi KAYIYOR",
          onar._yan_ihlal_imzasi(sert_fn, karma_urun)
          != onar._yan_ihlal_imzasi(sert_fn, _onarilmis))
    _isl, _sy, _elle, _dok, _karma = onar._tara([karma_urun])
    iddia("G/karma cumle ATLANDI (islem uretilmedi)", not _isl and _karma == 1,
          "islem=%r karma=%r" % (_isl, _karma))
    iddia("G/karma cumle ELLE'de GORUNUR (sessiz atlama YOK)",
          any(uid == "zz-karma-cumle" for uid, _kur in _elle), "elle=%r" % (_elle,))
    # (d) KONTROL: karma OLMAYAN kayit hala onarilir (atlama asiri genellemedi mi)
    temiz_urun = {"id": "zz-temiz", "baslik": "", "aciklama": "Sert malzemeden basılır."}
    _isl2, _sy2, _e2, _dok2, _karma2 = onar._tara([temiz_urun])
    iddia("G/KONTROL karma olmayan kayit ONARILIR",
          len(_isl2) == 1 and _karma2 == 0 and _isl2[0]["deger"] == "Sert malzemeden üretilir.",
          "islem=%r karma=%r" % (_isl2, _karma2))

    # === F) MUTASYON BATARYASI ======================================================
    # Her mutant: uretim kodundaki BIR kolu OLDUR -> ilgili iddia SESSIZ kalirsa test
    # o kolu OLCMUYOR demektir. Mutasyon YALNIZ BELLEKTE; diske mutant YAZILMAZ
    # ([[mutasyon-diske-yazma-tuzagi]]).
    mutant_sonuc = []

    def _mutant(ad, kur, geri, kanit):
        """kur() -> mutasyonu uygular; kanit() -> True ise iddia SESSIZ (mutant yakalanmadi)."""
        try:
            capa_tuttu = kur()
            if not capa_tuttu:
                mutant_sonuc.append((ad, "CAPA TUTMADI"))
                return
            mutant_sonuc.append((ad, "SESSIZ" if kanit() else "YAKALANDI"))
        finally:
            geri()

    # M1: B1 (_SUREC_TOKEN_RE'deki malzeme jetonlari) oldurulurse A/K1 SESSIZ kalmali
    _eski_token = dk._SUREC_TOKEN_RE

    def _m1_kur():
        yeni = _eski_token.pattern.replace("|malzemeden|malzemeyle|malzemesiyle", "")
        if yeni == _eski_token.pattern:
            return False                        # capa bayat: jetonlar desende YOK
        dk._SUREC_TOKEN_RE = re.compile(yeni, re.UNICODE)
        return True

    _mutant("M1 B1 malzeme jetonu",
            _m1_kur,
            lambda: setattr(dk, "_SUREC_TOKEN_RE", _eski_token),
            lambda: "baski-fiili" in _sert(dk, "Sert malzemeden basılır."))

    # M2/M3: yeni SERT kurallari tek tek oldurulur
    _eski_sert = dk._IFSA_SERT_RE

    def _kural_kaldir(ad):
        def kur():
            yeni = tuple(t for t in _eski_sert if t[0] != ad)
            if len(yeni) == len(_eski_sert):
                return False                    # capa bayat: kural adi DEGISMIS
            dk._IFSA_SERT_RE = yeni
            return True
        return kur

    _mutant("M2 uretim-kipi-basil",
            _kural_kaldir("uretim-kipi-basil"),
            lambda: setattr(dk, "_IFSA_SERT_RE", _eski_sert),
            lambda: bool(_sert(dk, "İnce ama sağlam basılır.")))

    _mutant("M3 baski-surec-cekimi",
            _kural_kaldir("baski-surec-cekimi"),
            lambda: setattr(dk, "_IFSA_SERT_RE", _eski_sert),
            lambda: bool(_sert(dk, "Baskı sonrası tolerans ayarı gerekebilir.")))

    # M4: kapinin PRESS suzgeci oldurulurse press vakasi SERT olmali (suzgec CANLI mi)
    #
    # 🔴 CAPA SECIMI OLCUMLE DUZELTILDI (17 Agu, ilk turda M4 SESSIZ dondu):
    #   Ilk capa "Panik düğmesine yanlışlıkla basılmasını önler." idi. O cumlede press
    #   suzgeci OLDURULSE BILE sonuc degismiyor — cunku cumlede SUREC JETONU yok, yani
    #   konjonksiyon kolu zaten SERT demiyor, UYARI diyor. Yani mutant OLU BIR KOLA
    #   nisanlanmisti ve "suzgec olculuyor" izlenimi veriyordu ([[fikstur-degeri-mutasyon-koru]]).
    #   Dogru capa, suzgecin GERCEKTEN tek koruma oldugu cumledir: hem SUREC JETONU
    #   (`malzemeden`) hem BASILAN NESNE (`pedal`) tasiyan cumle.
    _eski_press = dk._PRESS_RE
    _M4_CAPA = "Yumuşak malzemeden yapılan pedala rahatça basılır."

    def _m4_kur():
        if _sert(dk, _M4_CAPA):
            return False        # capa bayat: cumle saglam kodda ZATEN SERT
        dk._PRESS_RE = re.compile(r"(?!)", re.UNICODE)   # hicbir seye eslesmeyen desen
        return True

    _mutant("M4 press suzgeci",
            _m4_kur,
            lambda: setattr(dk, "_PRESS_RE", _eski_press),
            lambda: not _sert(dk, _M4_CAPA))

    # M5: onarim aracinin FIIL kalibi oldurulurse C/O1 SESSIZ kalmali
    _eski_derli = onar._DERLI

    def _m5_kur():
        yeni = tuple(t for t in _eski_derli if t[0] != "fiil/basılır")
        if len(yeni) == len(_eski_derli):
            return False                        # capa bayat: kalip adi DEGISMIS
        onar._DERLI = yeni
        return True

    _mutant("M5 onarim fiil kalibi",
            _m5_kur,
            lambda: setattr(onar, "_DERLI", _eski_derli),
            lambda: onar.onar_metin("Sert malzemeden basılır.")[0] == "Sert malzemeden üretilir.")

    # M6: onarim aracinin PRESS korumasi oldurulurse C/O10 (dokunulmaz) SESSIZ kalmali
    def _m6_kur():
        bos = re.compile(r"(?!)", re.UNICODE)
        yeni = tuple((ad, rx, k, bos) for ad, rx, k, _g in _eski_derli)
        onar._DERLI = yeni
        return True

    _mutant("M6 onarim press korumasi",
            _m6_kur,
            lambda: setattr(onar, "_DERLI", _eski_derli),
            lambda: onar.onar_metin("Panik düğmesine yanlışlıkla basılmasını önler.")[0]
            == "Panik düğmesine yanlışlıkla basılmasını önler.")

    # M7: KARMA CUMLE korumasi oldurulurse G vakasi SESSIZ kalmali. Bu mutant, CI kolunu
    # bloklayan gercek kusurun geri gelmesini yakalar.
    _eski_imza = onar._yan_ihlal_imzasi

    def _m7_kur():
        onar._yan_ihlal_imzasi = lambda _fn, _u: frozenset()   # imza DAIMA esit -> koruma olur
        return True

    _mutant("M7 karma cumle korumasi",
            _m7_kur,
            lambda: setattr(onar, "_yan_ihlal_imzasi", _eski_imza),
            lambda: onar._tara([karma_urun])[4] == 1)

    for ad, hal in mutant_sonuc:
        iddia("F/%s mutanti YAKALANDI" % ad, hal == "YAKALANDI", "sonuc=%s" % hal)

    # KONTROL: mutasyonlardan sonra uretim kodu ESKI HALINE dondu mu (yan etki nobeti)
    iddia("F/KONTROL uretim kodu geri yuklendi",
          dk._SUREC_TOKEN_RE is _eski_token and dk._IFSA_SERT_RE is _eski_sert
          and dk._PRESS_RE is _eski_press and onar._DERLI is _eski_derli
          and onar._yan_ihlal_imzasi is _eski_imza)
    iddia("F/KONTROL mutasyon sonrasi A/K1 hala YESIL",
          "baski-fiili" in _sert(dk, "Sert malzemeden basılır."))

    # === RAPOR =====================================================================
    print("=== IFSA KIP TESTI ===")
    print("  GECEN  : %d" % _GECEN)
    print("  KALAN  : %d" % len(_KALAN))
    print("  MUTANT : %d/%d YAKALANDI"
          % (sum(1 for _a, h in mutant_sonuc if h == "YAKALANDI"), len(mutant_sonuc)))
    for m in _KALAN:
        print("  ❌ %s" % m, file=sys.stderr)
    return 1 if _KALAN else 0


if __name__ == "__main__":
    sys.exit(kos())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — `uyum` ekseni (marka / model / motor / yil / oem) SESSIZ hata uretemez.

  python3 tools/uyum-kapisi.py              # kabul (CI'da bloklayici)
  python3 tools/uyum-kapisi.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/uyum-kapisi.py --kok /yol   # modulu BASKA agactan oku (mutasyon kopyasi)

NEDEN VAR (tools/paket-uyum-ekseni.md): musteri bir marka/model sayfasina girdiginde ona
uyan TUM urunleri gormeli. Bunun icin urunun NEYE UYDUGU yapilandirilmis bir alanda
durmali. Alan yanlis acilirsa hata SESSIZDIR: sahte bir marka sayfasi acilir ya da urun
hicbir sayfada gorunmez — iki halde de alarm calmaz.

OLCULEN DORT SESSIZ-HATA SINIFI:
  S SOZLUK  Marka kumesi KAPALI olmazsa "V.Penta / VolvoPenta / Volvo Penta" ikizi dogar
            ve ayni gercek uc ayri sayfaya bolunur. Kume ICINDE de ikiz olamaz.
  V SEMA    Bicimsiz/sozluk disi/ters yil araligi tasiyan kayit partiden gecerse veri
            bozulur; sessizce KIRPILAN bir deger ise katalog ile D1'i AYIRIR (bu depoda
            `altkategori`de OLCULDU: ' Elektrik' rc=0 gecmis, D1'e 'Elektrik' gitmisti).
  K IKIZ    `marka` ile `uyum[].marka` ayni gercegi IKI yerde tutar; biri elle degisince
    TANIM   sessizce ayrisir. `marka` TURETILIR (paket §2.1).
  A KATALOG Gercek 16.874 kaydin 13.040'inda `uyum` DOLU (backfill girdi; sayi kosumda
            OLCULUR, capa DEGIL). Kapi bu sayiyi her kosumda basar ki katalog buyudukce
            regresyon gorunur olsun.

CANLI D1'e / wrangler'a / AGA DOKUNMAZ. urunler.json yalnizca OKUNUR.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

GERCEK_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🔴 IDDIA TABANI = bu kapinin KOSMASI GEREKEN en az iddia sayisi (kosum ici sayi sarti
# commit'ler arasi kapsam kaybini GORMEZ; bkz. kabul() sonundaki capa). DUSURMEK ancak
# iddianin neden kaldirildigini yazan AYNI commit'te mesrudur; ARTIS serbesttir.
IDDIA_TABANI = 39

gecen = [0]
kalan = [0]


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + str(detay)[:400] if detay else ""))


def yukle(kok, ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(kok, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _urun(uyum=None, marka=None, **ek):
    """Sentetik kayit. `uyum` verilmezse alan HIC eklenmez (eski kayit hali)."""
    u = {"id": "uyum-test", "baslik": "Deneme urun", "kategori": "Otomobil",
         "marka": ["Ford"] if marka is None else marka, "fiyat": "100 TL",
         "aciklama": "deneme",
         "gorseller": ["https://media.pruvo3d.com/urunler/x-1.jpg"]}
    if uyum is not None:
        u["uyum"] = uyum
    u.update(ek)
    return u


def _guvenli(fn, *a):
    """Cagriyi COKMEDEN olc: (deger, coktu_mu)."""
    try:
        return fn(*a), False
    except Exception as e:  # noqa: BLE001 — cokme YOK iddiasi tam olarak burada olculur
        return "COKTU: %r" % (e,), True


# ══════════════════════════════════════════════════════════════════════════════════
def kabul(kok, katalog_yolu=None):
    A = yukle(kok, "arama", "arama.py")

    # ══ S EKSENI — SOZLUGUN KENDI SAGLIGI ═════════════════════════════════════════
    print("\n[S] SOZLUK — kapali kume tutarli, ikizsiz, denetlenebilir")
    izinli, uretici, elenen = A.UYUM_MARKA_IZINLI, A.URETICI_MARKA, A.UYUM_MARKA_ELENEN
    dogrula("S1 uc kume PARCALI AYRIK (bir jeton hem uyum markasi hem uretici/elenen "
            "olamaz — yargi tek yerde durur)",
            not (izinli & uretici) and not (izinli & elenen) and not (uretici & elenen),
            "izinli∩uretici=%s izinli∩elenen=%s uretici∩elenen=%s"
            % (sorted(izinli & uretici), sorted(izinli & elenen),
               sorted(uretici & elenen)))
    eki = A.UYUM_MARKA_MIMAR_EKI
    ureki = A.URETICI_MARKA_MIMAR_EKI
    tum_eki = eki | ureki
    birlesim = izinli | uretici | elenen
    yargilanan = birlesim - tum_eki
    # 🔴 S2 SAYI DEGIL KIMLIK KORUR. Yalniz buyukluk sabitlenseydi bir jetonu ELENEN'den
    # IZINLI'ye TASIMAK gorunmez olurdu (birlesim sabit, ayriklik bozulmuyor, ikiz yok) —
    # bagimsiz curutucu tam bunu yapti (`Turbo`) ve kapi YESIL kalmisti. Artik yargilanmis
    # BOLUMLEMENIN imzasi olculuyor; mesru genisleme (MIMAR EKI) imzaya GIRMEZ, yani
    # dogru yoldan buyume kapiyi kirmizi yakmaz.
    _imza = A.uyum_yargi_imzasi()
    _boy = tuple(len(b) for b in A.uyum_yargi_bolumleri())
    dogrula("S2 BUDAMA KIMLIGI: yargilanmis bolumlemenin (izinli−eki, uretici−eki, "
            "elenen) IMZASI donmus degerle birebir — elenen bir jeton izinli kumeye "
            "TASINAMAZ; bolum buyuklukleri %s ve toplam %d oneriye esit"
            % (A.UYUM_MARKA_YARGI_SAYILARI, A.UYUM_MARKA_ONERI_SAYISI),
            _imza == A.UYUM_MARKA_YARGI_IMZA
            and _boy == A.UYUM_MARKA_YARGI_SAYILARI
            and len(yargilanan) == A.UYUM_MARKA_ONERI_SAYISI,
            "imza=%s beklenen=%s | boy=%s beklenen=%s | toplam=%d"
            % (_imza, A.UYUM_MARKA_YARGI_IMZA, _boy, A.UYUM_MARKA_YARGI_SAYILARI,
               len(yargilanan)))
    dogrula("S7 MIMAR EKI'nin HER uyesi KENDI kumesinin alt kumesi ve kumeler ayrik "
            "(uyum eki %d jeton, uretici eki %d jeton) — denetimsiz genisleme yolu YOK"
            % (len(eki), len(ureki)),
            eki <= izinli and ureki <= uretici and not (eki & ureki)
            and not (eki & elenen) and not (ureki & elenen),
            "uyum_eki_disi=%s uretici_eki_disi=%s"
            % (sorted(eki - izinli), sorted(ureki - uretici)))
    bicimsiz = [d for d in birlesim
                if not isinstance(d, str) or not d or d.strip() != d]
    dogrula("S3 kumelerin HER degeri KANONIK (metin, bos degil, bas/son bosluksuz)",
            not bicimsiz, bicimsiz[:5])
    katlanan = {}
    for d in sorted(izinli | uretici):
        katlanan.setdefault(A.model_normalize(d), []).append(d)
    ikiz_kume = {k: v for k, v in katlanan.items() if len(v) > 1}
    dogrula("S4 SOZLUK ICI IKIZ YOK: iki uye AYNI normalize degere DUSMUYOR "
            "(`Mini`/`MINI`, `SsangYong`/`Ssangyong` gibi cift kayit kumeye giremez)",
            not ikiz_kume, ikiz_kume)
    sizan = [d for d in uretici if A.uyum_marka_kanonik(d)]
    dogrula("S5 URETICI markalari uyum ekseninde GECERSIZ (%d deger: buji/tutya/dolgu/"
            "boya/kablo ureticisi 'uyum markasi' diye SAHTE sayfa acamaz)" % len(uretici),
            not sizan, sizan)
    elenen_sizan = [d for d in elenen if A.uyum_marka_kanonik(d)]
    dogrula("S6 ELENEN jetonlarin hicbiri kabul EDILMIYOR (%s ...)"
            % ", ".join(sorted(elenen)[:4]), not elenen_sizan, elenen_sizan)
    print("  OLCUM: uyum markasi %d · uretici %d · elenen %d · toplam %d"
          % (len(izinli), len(uretici), len(elenen), len(birlesim)))

    # ══ V EKSENI — SPEC §4 KABUL EKSENLERI (1..10) ════════════════════════════════
    print("\n[V] SEMA — spec §4'un on ekseni")

    # V1 kapali kume
    icerden = [d for d in ("Ford", "Volkswagen", "Mercedes", "Tofaş", "Volvo",
                           "Volvo Penta", "Yanmar", "Fiat", "Vauxhall", "Johnson Pump",
                           "GoPro", "Raspberry Pi", "Kia", "Smart")
               if A.uyum_marka_kanonik(d) != d]
    disardan = [d for d in ("Focus", "F-150", "NGK", "Teleflex", "Bosch", "PSA", "VAG",
                            "Alpine", "Brodit", "Gurtner", "Sierra", "Johnson",
                            "Uydurma Marka", "")
                if A.uyum_marka_kanonik(d) != ""]
    dogrula("V1 kapali kumedeki marka KABUL, kume disi marka RED",
            not icerden and not disardan, "kabul edilmeyen=%s / sizan=%s"
            % (icerden, disardan))

    # V2 yakin yazim — SESSIZ KIRPMA YOK
    _yakin = ("Fordd", "ford", "FORD", " Ford", "Ford ", " Ford ", "\tFord", "Ford\n",
              "For d", "Ｆord")
    _sizan_yakin = [d for d in _yakin if A.uyum_marka_kanonik(d) != ""]
    dogrula("V2 YAKIN yazim RED (%d fikstur: harf hatasi, kucuk/buyuk, bas/son bosluk, "
            "sekme, tam-genislik homoglifi) — sessiz kirpma YOK" % len(_yakin),
            not _sizan_yakin, _sizan_yakin)

    # V3 alan opsiyonel
    dogrula("V3 `uyum` YOK / None / [] -> GECERLI (alan opsiyonel; bugun katalogun "
            "TAMAMI boyle — yanlis-pozitif 16.874 kaydi bloklamaz)",
            A.uyum_sebebi(_urun()) is None
            and A.uyum_sebebi(_urun(uyum=None)) is None
            and A.uyum_sebebi(_urun(uyum=[])) is None
            and A.uyum_kanonik(_urun()) == []
            and A.uyum_sebebi({}) is None,
            (A.uyum_sebebi(_urun()), A.uyum_sebebi(_urun(uyum=[]))))

    # V4 bozuk tip — RED, COKME YOK
    _bozuk = ["Ford", 5, 3.5, True, {"marka": "Ford"}, ["Ford"], [None], [[{"marka": "Ford"}]],
              [{"marka": "Ford"}, "Ford"], [{"marka": ["Ford"]}], [{"marka": "Ford",
                                                                   "yıl": [2003, 2015]}]]
    _v4_red, _v4_cokme = [], []
    for v in _bozuk:
        u = _urun(uyum=v)
        s, c1 = _guvenli(A.uyum_sebebi, u)
        k, c2 = _guvenli(A.uyum_kanonik, u)
        if c1 or c2:
            _v4_cokme.append((v, s, k))
        elif s is None or k != []:
            _v4_red.append((v, s, k))
    dogrula("V4 BOZUK tip RED ve COKME YOK (%d fikstur: metin/sayi/bool/sozluk/"
            "ic-ice dizi/karisik dizi/liste-marka/taninmayan anahtar)" % len(_bozuk),
            not _v4_red and not _v4_cokme,
            "reddedilmeyen=%s cokme=%s" % (_v4_red[:3], _v4_cokme[:3]))

    # V5 yil
    _yil_ok = ([2003, 2015], [2015, 0], [], [1900, 1900], [2015, 2015])
    _yil_red = ([2015], ["2015", "2020"], [2020, 2003], [2015, 2020, 2025],
                [0, 2015], [True, False], [2015.0, 2020.0], "2015", {"bas": 2015},
                [1899, 2000], [2015, 2101], [None, None])
    _yil_kalan = [v for v in _yil_ok if A.uyum_yil_sebebi(v) is not None]
    _yil_sizan = [v for v in _yil_red if A.uyum_yil_sebebi(v) is None]
    dogrula("V5 `yil`: %d gecerli bicim KABUL ([bas,son] · [bas,0] acik uc · []), "
            "%d gecersiz bicim RED (tek elemanli, metin, TERS aralik, acik BAS, bool, "
            "ondalik, aralik disi)" % (len(_yil_ok), len(_yil_red)),
            not _yil_kalan and not _yil_sizan,
            "kabul edilmeyen=%s / sizan=%s" % (_yil_kalan, _yil_sizan))

    # V6 K5 ikiz kapisi
    _dolu = [{"marka": "Ford", "model": "Focus", "motor": "", "yil": [2003, 2015],
              "oem": "3580310"},
             {"marka": "Volvo", "model": "XC60", "motor": "", "yil": [], "oem": ""}]
    # TURETME KURALI (2 Agu, mimar): marka = tekillestir(uyum[].marka + uyum[].model).
    _turetilmis = _urun(uyum=_dolu, marka=["Ford", "Focus", "Volvo", "XC60"])
    _yalniz_marka = _urun(uyum=_dolu, marka=["Ford", "Volvo"])       # ESKI kural
    _bozuk_marka = _urun(uyum=_dolu, marka=["Ford", "Focus", "Volvo", "Uydurma"])
    _eksik_marka = _urun(uyum=_dolu, marka=["Ford"])
    _sira_kaymis = _urun(uyum=_dolu, marka=["Focus", "Ford", "Volvo", "XC60"])
    _eski_kayit = _urun(marka=["Ford", "Focus"])
    dogrula("V6 K5 IKIZ KAPISI: `uyum` dolu + `marka` TURETILMIS -> yesil; `marka` elle "
            "bozuk / eksik / sirasi kaymis / ESKI kuralla (yalniz marka) yazilmis -> "
            "KIRMIZI; `uyum` bos + `marka` elle yazili -> yesil (eski kayit regresyonu 0)",
            A.uyum_sebebi(_turetilmis) is None
            and A.uyum_sebebi(_yalniz_marka) is not None
            and A.uyum_sebebi(_bozuk_marka) is not None
            and A.uyum_sebebi(_eksik_marka) is not None
            and A.uyum_sebebi(_sira_kaymis) is not None
            and A.uyum_sebebi(_eski_kayit) is None,
            (A.uyum_sebebi(_turetilmis), A.uyum_sebebi(_yalniz_marka),
             A.uyum_sebebi(_eski_kayit)))

    # V12 — TURETME KURALININ ICERIGI (mimar maddesi (a)): turetilen `marka` HEM marka
    # HEM model jetonlarini tasimali. Tasimasaydi backfill iner inmez model jetonlari
    # haystack()'ten duser ve arama SESSIZCE daralirdi.
    _t = A.marka_uyumdan_turet(_turetilmis)
    _sadece_model = A.marka_uyumdan_turet(
        _urun(uyum=[{"marka": "Ford", "model": "Focus"}], marka=["Ford", "Focus"]))
    _modelsiz = A.marka_uyumdan_turet(
        _urun(uyum=[{"marka": "Ford"}], marka=["Ford"]))
    _mukerrer = A.marka_uyumdan_turet(
        _urun(uyum=[{"marka": "Ford", "model": "Focus"},
                    {"marka": "Ford", "model": "Fiesta"}],
              marka=["Ford", "Focus", "Fiesta"]))
    dogrula("V12 TURETME = tekillestir(marka + model): sira ONCE marka SONRA model; "
            "modelsiz oge yalniz markayi verir; ayni marka IKI kez tekrarlanmaz "
            "(`motor`/`oem` GIRMEZ — arama metnini genisletip pariteyi ters yone kaydirmaz)",
            _t == ["Ford", "Focus", "Volvo", "XC60"]
            and _sadece_model == ["Ford", "Focus"]
            and _modelsiz == ["Ford"]
            and _mukerrer == ["Ford", "Focus", "Fiesta"]
            and A.marka_uyumdan_turet(
                _urun(uyum=[{"marka": "Ford", "model": "Focus", "motor": "1.6",
                             "oem": "12345"}], marka=["Ford", "Focus"]))
            == ["Ford", "Focus"],
            (_t, _sadece_model, _modelsiz, _mukerrer))

    # V13 — `Volvo` ve `Volvo Penta` AYRI EV SAHIPLERI (otomobil vs deniz motoru).
    dogrula("V13 `Volvo` ile `Volvo Penta` AYRI kanonik deger VE normalize anahtarlari "
            "CAKISMIYOR (`Penta` ekini yutan bir katlama iki uyum evrenini tek sayfaya "
            "yigardi); `Yanmar` da kumede",
            A.uyum_marka_kanonik("Volvo") == "Volvo"
            and A.uyum_marka_kanonik("Volvo Penta") == "Volvo Penta"
            and A.uyum_marka_kanonik("Yanmar") == "Yanmar"
            and A.model_normalize("Volvo") != A.model_normalize("Volvo Penta")
            and A.marka_uyumdan_turet(
                _urun(uyum=[{"marka": "Volvo Penta", "model": "D2-55"},
                            {"marka": "Yanmar", "model": "3YM30"}],
                      marka=["Volvo Penta", "D2-55", "Yanmar", "3YM30"]))
            == ["Volvo Penta", "D2-55", "Yanmar", "3YM30"],
            (A.model_normalize("Volvo"), A.model_normalize("Volvo Penta")))

    # V14 — PAKET §2'nin KENDI ORNEGI artik gecmeli (onceki turda REDDEDILIYORDU).
    _paket_ornegi = _urun(
        uyum=[{"marka": "Volvo Penta", "model": "D2-55", "motor": "", "yil": [2003, 2015],
               "oem": "3580310"},
              {"marka": "Yanmar", "model": "3YM30", "motor": "", "yil": [], "oem": ""}],
        marka=["Volvo Penta", "D2-55", "Yanmar", "3YM30"])
    dogrula("V14 paket §2'nin ORNEK KAYDI oldugu gibi KABUL ediliyor (amiral kullanim "
            "durumu: Okan'in talebindeki iki ornekten biri birebir `Volvo Penta`)",
            A.uyum_sebebi(_paket_ornegi) is None
            and A.uyum_kanonik(_paket_ornegi) == _paket_ornegi["uyum"],
            A.uyum_sebebi(_paket_ornegi))

    # V15 — V13'un kardesi: COK KELIMELI marka adinin ILK kelimesi ayri bir jeton DEGILDIR.
    dogrula("V15 `Johnson Pump` ile `Johnson` AYRI jetonlardir: normalize anahtarlari "
            "cakismiyor (`johnsonpump` != `johnson`), `Johnson` kumede YOK ve model olarak "
            "da GECMEZ — ilk kelimeyi yutan bir katlama iki uyum evrenini birlestirirdi",
            A.uyum_marka_kanonik("Johnson Pump") == "Johnson Pump"
            and A.uyum_marka_kanonik("Johnson") == ""
            and A.model_normalize("Johnson Pump") != A.model_normalize("Johnson")
            and A.uyum_marka_kanonik("Raspberry") == ""
            and A.model_normalize("Raspberry Pi") != A.model_normalize("Raspberry"),
            (A.model_normalize("Johnson Pump"), A.model_normalize("Johnson")))

    # V16 — MARKA/MODEL SINIRINDAKI IKIZ. Kumeye `Kia`/`Smart` girdi; katalogda `KIA`,
    # `SMART` yazimlari da var. Kural olmasaydi `marka: "Kia"` + `model: "KIA"` ayni
    # gercegi IKI alanda tutar ve iki ayri sayfa uretirdi.
    _varyant = ("KIA", "SMART", "MINI", "Citroën", "Ikea", "BaoFeng", "Ssangyong",
                "Ford", "ford", "F O R D", "Volvo Penta")
    _varyant_sizan = [
        v for v in _varyant
        if A.uyum_sebebi(_urun(uyum=[{"marka": "Ford", "model": v}],
                               marka=["Ford", v])) is None]
    _mesru_model = ("Focus", "F-150", "Berlingo", "D2-55", "Sprinter", "206+", "K5")
    _mesru_red = [m for m in _mesru_model if A.marka_varyanti_sebebi("model", m)]
    dogrula("V16 MARKA/MODEL SINIRI: kapali kumedeki bir markanin YAZIM VARYANTI model/"
            "motor alanina yazilamaz (%d fikstur RED) ve %d mesru model bundan "
            "ETKILENMIYOR — olculen yanlis-pozitif 0"
            % (len(_varyant), len(_mesru_model)),
            not _varyant_sizan and not _mesru_red,
            "sizan=%s yanlis-pozitif=%s" % (_varyant_sizan, _mesru_red))

    # V17 — MUKERRER OGE. Kural kodda VARDI ama HICBIR iddia onu olcmuyordu: bagimsiz
    # curutucu kontrolu tamamen sildi ve kapi YESIL kaldi (X7). Olculmeyen kural, kural
    # degildir. Mukerrer oge kartezyen sisme ve yanlis "kac araca uyuyor" sayisi uretir.
    _mukerrer_uyum = [
        [{"marka": "Ford", "model": "Focus"}, {"marka": "Ford", "model": "Focus"}],
        [{"marka": "Ford"}, {"marka": "Ford"}],
        [{"marka": "Ford", "yil": [2003, 2015]}, {"marka": "Ford", "yil": [2003, 2015]}],
        [{"marka": "Ford", "model": "Focus"}, {"marka": "Volvo"},
         {"marka": "Ford", "model": "Focus"}],
    ]
    _mukerrer_sizan = [
        v for v in _mukerrer_uyum
        if A.uyum_sebebi(_urun(uyum=v, marka=A.marka_uyumdan_turet({"uyum": v}))) is None]
    # Yanlis-pozitif nobeti: AYNI markanin FARKLI modelleri mukerrer DEGILDIR.
    _farkli = [{"marka": "Ford", "model": "Focus"}, {"marka": "Ford", "model": "Fiesta"}]
    _farkli_red = A.uyum_sebebi(
        _urun(uyum=_farkli, marka=["Ford", "Focus", "Fiesta"])) is not None
    dogrula("V17 MUKERRER OGE: birebir ayni `uyum` ogesi iki kez yazilamaz (%d fikstur "
            "RED) ama ayni markanin FARKLI modelleri KABUL — kartezyen sisme ve yanlis "
            "'kac araca uyuyor' sayisi uretilemez" % len(_mukerrer_uyum),
            not _mukerrer_sizan and not _farkli_red,
            "sizan=%s farkli_model_reddedildi=%s" % (_mukerrer_sizan[:2], _farkli_red))

    # V7 model normalizasyonu
    _ayni = (("F-150", "F150"), ("XSR 700", "XSR700"), ("ID.Buzz", "ID Buzz"),
             ("Zoé", "Zoe"), ("RAV4", "Rav-4"), ("C-Max", "C-MAX"))
    _ayri = (("Focus", "Focuss"), ("F-150", "F-250"), ("Golf", "Golf Plus"),
             ("E46", "E64"))
    _n = A.model_normalize
    _ayni_kalan = [p for p in _ayni if _n(p[0]) != _n(p[1]) or not _n(p[0])]
    _ayri_kalan = [p for p in _ayri if _n(p[0]) == _n(p[1])]
    dogrula("V7 model normalizasyonu: %d ikiz cifti AYNI anahtara iniyor, %d farkli "
            "model AYRI kaliyor" % (len(_ayni), len(_ayri)),
            not _ayni_kalan and not _ayri_kalan,
            "birlesmeyen=%s / yanlis birlesen=%s" % (_ayni_kalan, _ayri_kalan))

    # V8 kanonik ozdeslik — katalog metni == D1 metni
    _ozdes_fikstur = [
        _urun(uyum=_dolu, marka=["Ford", "Focus", "Volvo", "XC60"]),
        _urun(uyum=[{"marka": "Ford"}], marka=["Ford"]),
        _urun(uyum=[{"marka": "Mercedes", "model": "W203", "yil": [2000, 0]}],
              marka=["Mercedes", "W203"]),
        _urun(uyum=[{"marka": "Tofaş", "model": "Şahin", "oem": "85.12.345/A"}],
              marka=["Tofaş", "Şahin"]),
    ]
    _ayrisan, _paylasan = [], []
    for u in _ozdes_fikstur:
        k = A.uyum_kanonik(u)
        if k != u["uyum"]:
            _ayrisan.append((u["uyum"], k))
        if any(a is b for a in k for b in u["uyum"]):
            _paylasan.append(u["uyum"])
    # 🔴 DERIN KOPYA OLCUMU FAIL-CLOSED, COKMEYLE DEGIL. Onceki hali `_mut[0]` yaziyordu:
    # `uyum_kanonik` BOS liste dondurdugunde (fail-closed reddettiginde) IndexError firlatip
    # kabul kosumunu ORTASINDA olduruyordu — geriye kalan 16 iddia HIC OLCULMUYOR, cikis
    # kodu yine 1 oldugu icin "kapi yakaladi" gibi gorunuyordu. Bagimsiz curutucude
    # OLCULDU: M9/M10 mutantlarinda iddia sayisi 36 -> 20'ye dustu ve bu "kirmizi" bir
    # OLCUM DEGILDI ([[hukum-yanlis-birimde]] · [[mutasyon-kaniti-yeniden-uretilebilir]]).
    # Simdi bos cikti COKME degil KIRMIZI uretir: iddia adiyla yanar, kalan iddialar olculur.
    _mut = A.uyum_kanonik(_ozdes_fikstur[0])
    _derin_kopya = bool(_mut)
    if _mut:
        _mut[0]["marka"] = "BOZULDU"
        _derin_kopya = _ozdes_fikstur[0]["uyum"][0]["marka"] == "Ford"
    dogrula("V8 KANONIK OZDESLIK: kabul edilen %d kayitta `uyum_kanonik` ciktisi katalog "
            "degeriyle BIREBIR AYNI ve DERIN KOPYA (cagiran ciktiyi bozarsa katalog "
            "bozulmaz) — altkategori'de olculen sessiz ayrismanin tekrari yok"
            % len(_ozdes_fikstur),
            not _ayrisan and not _paylasan and _derin_kopya,
            "ayrisan=%s paylasilan-referans=%s derin_kopya=%s%s"
            % (_ayrisan[:2], _paylasan[:2], _derin_kopya,
               " (kanonik cikti BOS — kayit REDDEDILDI, derin kopya OLCULEMEDI)"
               if not _mut else ""))

    # V9 fail-closed yonu — urun KAYBOLMAZ
    _gecersiz = _urun(uyum=[{"marka": "Uydurma Marka", "model": "X"}], marka=["Ford"])
    dogrula("V9 FAIL-CLOSED: gecersiz `uyum` -> [] (D1'e ham sizmaz) ama urunun DIGER "
            "alanlari DOKUNULMAZ kalir — urun kendi kategorisinde bulunur, KAYBOLMAZ",
            A.uyum_kanonik(_gecersiz) == []
            and _gecersiz["kategori"] == "Otomobil"
            and _gecersiz["marka"] == ["Ford"]
            and A.uyum_kanonik(_urun(uyum="bozuk")) == []
            and A.uyum_kanonik(_urun(uyum=[{"marka": "Ford", "yil": [2020, 2003]}],
                                     marka=["Ford"])) == [],
            A.uyum_kanonik(_gecersiz))

    # V10 enjeksiyon
    _enjeksiyon = ["<script>alert(1)</script>", "' OR 1=1--", '";DROP TABLE urunler;--',
                   "Ford<b>", "${jndi:ldap://x}", "Focus&amp;", "a\nb", "a\x00b",
                   "Фord", "../../etc/passwd", "%27%20OR", "Focus';--",
                   "..", "Focus/../Golf", "/etc/passwd", "Focus.", ".Focus", "-", "+",
                   "Focus  Golf", "..\\Golf", "Ｆocus"]
    _marka_sizan = [v for v in _enjeksiyon if A.uyum_marka_kanonik(v) != ""]
    _model_sizan = [v for v in _enjeksiyon if A._serbest_sebebi("model", v) is None]
    _cikti_sizan = []
    for v in _enjeksiyon:
        # 🔴 `marka` alani BILEREK TURETILMIS deger ile doldurulur: dolduruimasaydi kayit
        # K5 ikiz kapisindan reddedilir ve V10 "enjeksiyon yakalandi" diye YESIL yanardi
        # — oysa yakalayan enjeksiyon kurali DEGIL ikiz kapisi olurdu (yanlis sebeple
        # gecen test). Boylece reddi yalnizca beyaz liste uretebilir.
        for u in (_urun(uyum=[{"marka": v}], marka=[v]),
                  _urun(uyum=[{"marka": "Ford", "model": v}], marka=["Ford", v]),
                  _urun(uyum=[{"marka": "Ford", "oem": v}], marka=["Ford"])):
            k, c = _guvenli(A.uyum_kanonik, u)
            if c or k != []:
                _cikti_sizan.append((v, k))
    dogrula("V10 ENJEKSIYON: %d fikstur (HTML/SQL/JNDI/NUL/satir sonu/Kiril homoglifi/"
            "yol gecisi) marka VE model/oem alaninda RED; `uyum_kanonik` ciktisina "
            "sizinti 0" % len(_enjeksiyon),
            not _marka_sizan and not _model_sizan and not _cikti_sizan,
            "marka=%s model=%s cikti=%s"
            % (_marka_sizan[:3], _model_sizan[:3], _cikti_sizan[:3]))

    # V11 kapi gereginden DAR degil (yanlis-pozitif nobeti)
    _mesru = [
        _urun(uyum=[{"marka": "Ford", "model": "F-150", "motor": "5.0", "yil": [2015, 0],
                     "oem": "FL3Z-9F792-A"}], marka=["Ford", "F-150"]),
        _urun(uyum=[{"marka": "Citroen", "model": "Berlingo"},
                    {"marka": "Peugeot", "model": "Partner"}],
              marka=["Citroen", "Berlingo", "Peugeot", "Partner"]),
        _urun(uyum=[{"marka": "Mercedes", "model": "Sprinter", "yil": [2006, 2018]}],
              marka=["Mercedes", "Sprinter"]),
        _urun(uyum=[{"marka": "Kärcher", "model": "K5"}], marka=["Kärcher", "K5"]),
        _urun(uyum=[{"marka": "Land Rover", "model": "Defender 110"}],
              marka=["Land Rover", "Defender 110"]),
        # OLCULEN GERCEK VERI: '206+' katalogda gecen bir Peugeot modeli. '+' AYIRAC
        # DEGIL EK oldugu icin konum kurali onu kesmez — yol gecisi kapanirken mesru
        # model sonegi hayatta kalir.
        _urun(uyum=[{"marka": "Peugeot", "model": "206+"}], marka=["Peugeot", "206+"]),
    ]
    _mesru_red = [(u["uyum"], A.uyum_sebebi(u)) for u in _mesru
                  if A.uyum_sebebi(u) is not None]
    dogrula("V11 YANLIS-POZITIF YOK: %d mesru kayit (tire/nokta/bogumlu OEM, coklu uyum, "
            "acik uc yil, Turkce harf, bosluklu model, '+' sonekli model) KABUL"
            % len(_mesru), not _mesru_red, _mesru_red[:3])

    # ══ A EKSENI — GERCEK KATALOG ══════════════════════════════════════════════════
    print("\n[A] KATALOG — urunler.json (yalniz OKUNUR)")
    with open(katalog_yolu or os.path.join(GERCEK_KOK, "urunler.json"),
              encoding="utf-8") as f:
        katalog = json.load(f)
    ihlal, uyumlu, kanonik_ayrisan = [], 0, []
    model_ham = {}
    for u in katalog:
        if not isinstance(u, dict):
            continue
        sebep = A.uyum_sebebi(u)
        if sebep:
            ihlal.append((u.get("id"), sebep))
            continue
        if u.get("uyum"):
            uyumlu += 1
            if A.uyum_kanonik(u) != u["uyum"]:
                kanonik_ayrisan.append(u.get("id"))
            for oge in u["uyum"]:
                for alan in ("model", "motor"):
                    ham = oge.get(alan)
                    if isinstance(ham, str) and ham.strip():
                        model_ham.setdefault(A.model_normalize(ham), set()).add(ham)
    dogrula("A1 katalogtaki HICBIR kayit `uyum` semasini ihlal etmiyor", not ihlal,
            ihlal[:5])
    # 🔴 A2 ARTIK BAGIMSIZ. Onceki hali A1'in `ihlal` bayragini TEKRAR okuyordu — ayni
    # kosulu iki kez sayan bir TOTOLOJI, iddia sayisini sisirir ve hicbir sey olcmez.
    # Simdi K5 ekseni AYRI bir kod yolundan (`marka_uyumdan_turet` DOGRUDAN, `uyum_sebebi`
    # uzerinden DEGIL) taraniyor ve tarayicinin fiilen calistigi POZITIF KONTROL ile
    # kanitlaniyor: kataloga bilerek bozuk bir kayit eklenir, tarama TAM ONU bulmali
    # (bulamazsa tarama bos calisiyordur ve "0 ihlal" YALANDIR).
    _k5_poz = _urun(uyum=[{"marka": "Ford", "model": "Focus"}], marka=["BOZUK"])
    _k5_poz["id"] = "K5-POZITIF-KONTROL"
    _k5_ihlal = [u.get("id") for u in list(katalog) + [_k5_poz]
                 if isinstance(u, dict) and u.get("uyum")
                 and u.get("marka") != A.marka_uyumdan_turet(u)]
    dogrula("A2 K5 TARAMASI (A1'den BAGIMSIZ kod yolu): `uyum` dolu %d gercek kayitta "
            "`marka` == turetilen VE tarayici fiilen calisiyor — sentetik bozuk kayit "
            "TAM OLARAK yakalaniyor (pozitif kontrol)" % uyumlu,
            _k5_ihlal == ["K5-POZITIF-KONTROL"], _k5_ihlal[:5])
    dogrula("A3 KABUL EDILEN her kayitta katalog metni == D1 metni (urunler.json ile D1 "
            "SESSIZCE ayrisamaz)", not kanonik_ayrisan, kanonik_ayrisan[:5])
    model_ikiz = {k: sorted(v) for k, v in model_ham.items() if len(v) > 1}
    dogrula("A4 MODEL IKIZI YOK: ayni normalize degere DUSEN 2+ ham model yazimi yok "
            "(`F-150`/`F150` ayni araci IKI sayfaya bolemez)", not model_ikiz, model_ikiz)

    # A5 — GERCEK VERI REGRESYONU (mimar maddesi (c)). Fikstur DEGIL: katalogun kendi
    # `marka` dizileri alinir, backfill'in yazacagi `uyum` sentezlenir ve turetilen
    # `marka`nin BUGUNKU deger ile BIREBIR ayni oldugu olculur. Ayni olmazsa arama metni
    # (haystack/ege_govde `marka`yi okur) backfill gunu SESSIZCE kayar.
    # 🔴 SENTEZ KURALI, OLCULEN VERIDEN DOGDU: `marka` dizisi HER ZAMAN [marka, model]
    # degil. Katalogda [marka, MARKA] kayitlari da var (olculdu: `["Tohatsu","Mercury"]`,
    # `["Volvo Penta","Mercruiser"]` — bir parcanin IKI markaya uymasi). Naif "ilk eleman
    # marka, kalanlar model" sentezi bu kayitlari model-varyanti kapisina (V16) carptirdi.
    # Dogru sentez: sozlukteki her jeton KENDI ogesini acar, sozluk disi jeton bir onceki
    # markanin modeli olur. Backfill'in yapmasi gereken de tam olarak budur.
    def _sentezle(ham):
        s = []
        for x in ham:
            if A.uyum_marka_kanonik(x):
                s.append({"marka": x})
            elif not s:
                return None                      # marka ile BASLAMAYAN dizi: ELE kalir
            elif s[-1].get("model"):
                s.append({"marka": s[-1]["marka"], "model": x})
            else:
                s[-1]["model"] = x
        return s

    ornek, ele, ele_mukerrer, ayrisan_gercek, red_gercek = 0, 0, 0, [], []
    for u in katalog:
        if not isinstance(u, dict) or not isinstance(u.get("marka"), list):
            continue
        ham = u["marka"]
        if not 1 <= len(ham) <= 3 or not all(isinstance(x, str) for x in ham):
            continue
        if not A.uyum_marka_kanonik(ham[0]):
            continue
        if any(A._serbest_sebebi("model", x) is not None for x in ham[1:]):
            continue
        # 🔴 MUKERRER JETON = HAZIRLIKSIZLIK, IHLAL DEGIL (bagimsiz curutucu olctu).
        # `["Ford","Focus","Ford"]` gibi bir dizi TURETMEYLE geri uretilemez: turetme
        # TEKILLESTIRIR, yani girdi zaten temsil edilemez. Bu kayit "ayrisma" DEGILDIR,
        # backfill'in ELE alacagi bir girdidir.
        # NEDEN BLOKLAMAMALI: bu kapi `build` isinde kosuyor ve `deploy` ona `needs` ile
        # bagli — tek bir mukerrer jetonlu urun BES EVIN yayinini birden durdururdu.
        # `tools/urun-ekle.py`'de `marka` tekillestirmesi YOK, yani bu bir zaman meselesi.
        # Bu adimin TUKETICISI YOK: henuz kimsenin yazmadigi bir alanin HAZIRLIK olcumu
        # yayin durdurma yetkisine sahip olamaz. Bloklayan sey IHLAL olmali.
        if len(set(ham)) != len(ham):
            ele_mukerrer += 1
            continue
        # 🔴 ELE BUCKETI (olculen, gizlenmiyor): dizide KANONIK OLMAYAN bir marka yazimi
        # varsa (`Citroën`, `KIA`, `MINI`, `SMART`, `Ikea`, `BaoFeng`, `Ssangyong`)
        # backfill o kaydi OTOMATIK yazamaz — jetonun once kanonige cevrilmesi gerekir.
        # Sayilir ve RAPORLANIR; sessizce "kapsam disi" sayilmaz.
        if any(not A.uyum_marka_kanonik(x) and A.marka_varyanti_sebebi("model", x)
               for x in ham):
            ele += 1
            continue
        sentez = _sentezle(ham)
        if sentez is None:
            continue
        aday = dict(u, uyum=sentez)
        ornek += 1
        if A.marka_uyumdan_turet(aday) != ham:
            ayrisan_gercek.append((u.get("id"), ham, A.marka_uyumdan_turet(aday)))
        if A.uyum_sebebi(aday) is not None:
            red_gercek.append((u.get("id"), ham, A.uyum_sebebi(aday)))
    dogrula("A5 GERCEK VERI REGRESYONU: %d gercek kayitta backfill'in yazacagi `uyum`dan "
            "turetilen `marka`, BUGUNKU `marka` degeriyle BIREBIR ayni ve kapidan geciyor "
            "(arama metni backfill gunu kaymaz — parite riski 0). ELE: %d kanonik olmayan "
            "marka yazimi + %d mukerrer jeton — SAYILIR, RAPORLANIR, BLOKLAMAZ"
            % (ornek, ele, ele_mukerrer),
            ornek > 0 and not ayrisan_gercek and not red_gercek,
            "ornek=%d ele=%d ele_mukerrer=%d ayrisan=%s red=%s"
            % (ornek, ele, ele_mukerrer, ayrisan_gercek[:3], red_gercek[:3]))

    # BACKFILL HAZIRLIGI — sayi, iddia degil. Mevcut `marka` jetonlarinin ne kadari
    # bugunku sozlukten/serbest metin kuralindan gecerdi?
    jetonlar = set()
    for u in katalog:
        if isinstance(u, dict) and isinstance(u.get("marka"), list):
            for x in u["marka"]:
                if isinstance(x, str) and x.strip():
                    jetonlar.add(x)
    marka_gecen = sum(1 for j in jetonlar if A.uyum_marka_kanonik(j))
    model_gecen = sum(1 for j in jetonlar if A._serbest_sebebi("model", j) is None)
    print("  OLCUM: %d kayit · `uyum` dolu %d · sema ihlali %d · katalog!=D1 %d · "
          "model ikizi %d" % (len(katalog), uyumlu, len(ihlal), len(kanonik_ayrisan),
                              len(model_ikiz)))
    print("  BACKFILL HAZIRLIGI: %d tekil `marka` jetonu · sozlukten gecen %d · "
          "model kuralindan gecen %d · ikisinden de gecmeyen %d"
          % (len(jetonlar), marka_gecen, model_gecen,
             sum(1 for j in jetonlar if not A.uyum_marka_kanonik(j)
                 and A._serbest_sebebi("model", j) is not None)))

    # ══ B EKSENI — BILESIK MARKA ADI (tools/paket-bilesik-marka.md) ═══════════════
    # `Mercedes-Benz` -> `Mercedes` (Okan hukmu). AYRI kural sinifi: yazim varyanti DEGIL,
    # kanonik markayi ICEREN bilesik ad. Asil risk KANONIKLESTIRMENIN KENDISI DEGIL, onun
    # arama metninde acacagi SESSIZ DELIKTIR (`marka` haystack()'e girer).
    print("\n[B] BILESIK MARKA ADI — kapali tablo + arama jetonu kaybi YOK")

    dogrula("B1 OKAN'IN TAM ESLEMESI: `Mercedes-Benz` -> `Mercedes`, deger tabloya TABI "
            "(sebebi None DEGIL) ve tablo TEK TOHUM — icerigi donmus, sessiz genisleme "
            "kapiyi KIRMIZI yakar",
            A.bilesik_marka_kanonik("Mercedes-Benz") == "Mercedes"
            and A.bilesik_marka_sebebi("Mercedes-Benz") is not None
            and dict(A.BILESIK_MARKA_KANONIK) == {"Mercedes-Benz": "Mercedes"},
            "kanonik=%r sebep=%r tablo=%r"
            % (A.bilesik_marka_kanonik("Mercedes-Benz"),
               A.bilesik_marka_sebebi("Mercedes-Benz"),
               dict(A.BILESIK_MARKA_KANONIK)))

    # B2 — UYDURMA ESLEME YOK. Fikstürler BILEREK tabloya BENZER (kanonik markayi ICEREN
    # bilesik adlar) ama tabloda YOKLAR: "tablo hic okunmadi, hep icerdigi markayi
    # dondurdu" mutanti bu fikstürden GECEMEZ ([[fikstur-degeri-mutasyon-koru]]).
    _b2 = ["Mercedes Voranta", "Volvo Pentax", "Ford Torenta", "Mercedes", "Sprinter", ""]
    _b2_bozan = [v for v in _b2 if A.bilesik_marka_kanonik(v) != v
                 or A.bilesik_marka_sebebi(v) is not None]
    _b2_tip = [v for v in (5, None, ["Mercedes-Benz"], {"a": 1})
               if A.bilesik_marka_kanonik(v) != v or A.bilesik_marka_sebebi(v) is not None]
    dogrula("B2 TABLODA OLMAYAN bilesik ad DEGISMEDEN doner (%d fikstur, biri BILEREK "
            "tabloya benzeyen uydurma bilesik ad) ve metin OLMAYAN deger de aynen doner "
            "— uydurma esleme YOK, cokme YOK" % len(_b2),
            not _b2_bozan and not _b2_tip, "bozan=%s tip=%s" % (_b2_bozan, _b2_tip))

    # B3 — GENEL NORMALIZASYON YASAGI. Bu jetonlarin HEPSI olculen katalog verisidir
    # (`206+` Peugeot modeli, `D2-55` Volvo Penta motoru, `K5` Kärcher modeli). "Tire kirp"
    # / "sonek soy" turu bir kural onlari yer ve arama sonucu hicbir kirmizi yanmadan kaybolur.
    _b3 = ["F-150", "Rolls-Royce", "D2-55", "206+", "K5", "C-Max", "ID.Buzz", "XSR 700"]
    _b3_bozan = [v for v in _b3 if A.bilesik_marka_kanonik(v) != v
                 or A.bilesik_marka_sebebi(v) is not None]
    dogrula("B3 GENEL NORMALIZASYON YOK: %d mesru jeton (tireli/noktali/sonekli — hepsi "
            "OLCULEN katalog verisi) DOKUNULMADAN geciyor" % len(_b3),
            not _b3_bozan, _b3_bozan)

    # B4 — 7'LI CAPA NOBETI (fail-closed). MaCiT'in kova ayrimi bu sayiya dayanir: kume
    # kayarsa "Kova2 = 4 kayit" olcumu sessizce yanlislanir. Sayi DEGIL KIMLIK dondurulur
    # (S2 dersi: sayiyi sabit tutup uyeyi degistirmek gorunmez kalirdi).
    # 🔴 8. UYE GELDI ve GITTI (26 Agu 2026, K302 kahve eki): `AeroPress` IZINLI'ye girince
    # katalogdaki `"Aeropress"` (1 kayit) varyant sayilip capa 7->8 cikti; AYNI GUN o kayit
    # kanoniklestirildi (`3c4ff3bb`, urunler.json 1 satir) -> katalogda `"Aeropress"` 0 ·
    # `"AeroPress"` 4 OLCULDU ve uye capadan DUSTU. Bu, yukaridaki notun ONGORDUGU fail-loud
    # inistir (kume kaydi, capa bagirdi): kume 7'ye indi, capa da 7'ye indirildi. Uye ELLE
    # geri EKLENMEZ; katalogda varyant yeniden dogarsa capa yine KIRMIZI yakar.
    _b4_capa = {"BaoFeng", "Citroën", "Ikea", "KIA", "MINI", "SMART", "Ssangyong"}
    _b4_jeton = set()
    for u in katalog:
        if isinstance(u, dict) and isinstance(u.get("marka"), list):
            for x in u["marka"]:
                if isinstance(x, str) and x.strip():
                    _b4_jeton.add(x)
    _b4_olculen = {j for j in _b4_jeton
                   if not A.uyum_marka_kanonik(j) and A.marka_varyanti_sebebi("model", j)}
    dogrula("B4 YAZIM VARYANTI CAPASI: `marka_varyanti_sebebi()` gercek katalogda TAM 7 "
            "jeton yakaliyor ve KIMLIKLERI donmus deger ile birebir — sayi ya da uye "
            "kayarsa fail-closed KIRMIZI",
            _b4_olculen == _b4_capa and len(_b4_olculen) == 7,
            "olculen(%d)=%s fazla=%s eksik=%s"
            % (len(_b4_olculen), sorted(_b4_olculen), sorted(_b4_olculen - _b4_capa),
               sorted(_b4_capa - _b4_olculen)))

    # B5 — IKI KURAL SINIFI, IKI BAGIMSIZ KOD YOLU. Biri digerinin bayragini okusaydi tek
    # kod yolunu iki kez olcerdik ve bu IKI IDDIA olmazdi ([[beyan-edilmis-survivor]]).
    # Olcut DAVRANISSAL: varyant yolu bilesik adi GORMEZ, bilesik yolu yazim varyantini GORMEZ.
    _b5_varyant_bilesigi = [v for v in ("Mercedes-Benz", "Rolls-Royce", "Mercedes Voranta")
                            if A.marka_varyanti_sebebi("model", v) is not None]
    _b5_bilesik_varyanti = [v for v in ("KIA", "SMART", "MINI", "Citroën", "Ikea",
                                        "BaoFeng", "Ssangyong")
                            if A.bilesik_marka_kanonik(v) != v]
    dogrula("B5 BAGIMSIZ KOD YOLU: yazim-varyanti kurali bilesik adi YAKALAMIYOR (3 "
            "fikstur) ve bilesik-ad tablosu 7 yazim varyantinin HICBIRINI katlamiyor — "
            "iki sinif tek capada erimiyor",
            not _b5_varyant_bilesigi and not _b5_bilesik_varyanti,
            "varyant_bilesigi_yakaladi=%s bilesik_varyanti_katladi=%s"
            % (_b5_varyant_bilesigi, _b5_bilesik_varyanti))

    # B6 — 🔴 ARAMA JETONU KAYBI (paketin varlik sebebi). Iki yonlu olculur:
    #  (a) ham yazim baslikta duruyorsa kanoniklestirme kayipsizdir -> TAKMA EKLENMEZ
    #      (gereksiz genisleme de bir davranis degisikligidir),
    #  (b) ham yazim YALNIZ `marka`daysa duz kanoniklestirme jetonu DUSURUR -> takma
    #      EKLENIR ve kanoniklestirilmis kayit `Mercedes-Benz` sorgusuyla HALA BULUNUR.
    _b6_baslikli = _urun(marka=["Mercedes-Benz", "Sprinter"])
    _b6_baslikli["baslik"] = "Mercedes-Benz Sprinter kalorifer kanal adaptoru"
    _b6_ciplak = _urun(marka=["Mercedes-Benz", "Sprinter"])
    _b6_ciplak["baslik"] = "Mercedes Sprinter kalorifer kanal adaptoru"
    _b6_ciplak["aciklama"] = "Sprinter kalorifer kanali icin adaptor"
    _b6_ilgisiz = _urun(marka=["Ford", "Focus"])
    # 🔴 KONUM-1 VAKASI (olculen kor nokta, 2 Agu): yukaridaki fikstürlerin HEPSI bilesik
    # adi `marka[0]`da tasiyordu. Gercek katalogda bilesik adi IKINCI sirada tasiyan 1
    # kayit var (`['BMW', 'Mercedes-Benz']`, duz eslemede jetonunu KAYBEDENLERDEN biri).
    # Fikstür kor oldugu icin "kanoniklestirme yalniz marka[0]'a uygulanir" mutanti (M23)
    # HICBIR iddiayi yakmadan SAG KALIYORDU ([[fikstur-degeri-mutasyon-koru]]).
    _b6_ikinci = _urun(marka=["BMW", "Mercedes-Benz"])
    _b6_ikinci["baslik"] = "BMW Mercedes uyumlu ic trim klipsi"
    _b6_ikinci["aciklama"] = "Ic trim klipsi"
    _b6_a = A.bilesik_marka_kanoniklestir(_b6_baslikli)
    _b6_b = A.bilesik_marka_kanoniklestir(_b6_ciplak)
    _b6_c = A.bilesik_marka_kanoniklestir(_b6_ilgisiz)
    _b6_d = A.bilesik_marka_kanoniklestir(_b6_ikinci)
    # Kanoniklestirilmis kayitlarda sorgu HALA buluyor mu? (site uclusuyle olculur)
    _b6_bulunuyor = [
        A.arama_jetonu_korunuyor(dict(_b6_baslikli, marka=_b6_a), "Mercedes-Benz"),
        A.arama_jetonu_korunuyor(dict(_b6_ciplak, marka=_b6_b), "Mercedes-Benz"),
        A.arama_jetonu_korunuyor(dict(_b6_ikinci, marka=_b6_d), "Mercedes-Benz"),
    ]
    # NEGATIF KONTROL: mekanizma OLMASAYDI (duz esleme) ikinci kayit KAYBOLURDU. Bu
    # olculmezse "kayip yok" iddiasi bos olabilir (fikstur zaten kaybetmiyordur).
    _b6_duz = A.arama_jetonu_korunuyor(dict(_b6_ciplak, marka=["Mercedes", "Sprinter"]),
                                       "Mercedes-Benz")
    dogrula("B6 ARAMA PARITESI: kanoniklestirilmis kayitta `Mercedes-Benz` sorgusu urunu "
            "HALA BULUYOR (jeton kaybi 0); ham yazim baslikta duruyorsa takma EKLENMEZ "
            "(arama yuzeyi genislemez), yalniz `marka`daysa takma EKLENIR; bilesik ad "
            "`marka[0]` DEGIL IKINCI sirada olsa da katlanir; bilesik ad tasimayan kayit "
            "BIREBIR degismez; duz esleme ayni kaydi KAYBEDIYOR (negatif kontrol)",
            _b6_a == ["Mercedes", "Sprinter"]
            and _b6_b == ["Mercedes", "Sprinter", "Mercedes-Benz"]
            and _b6_c == ["Ford", "Focus"]
            and _b6_d == ["BMW", "Mercedes", "Mercedes-Benz"]
            and all(_b6_bulunuyor) and not _b6_duz,
            "baslikli=%s ciplak=%s ilgisiz=%s konum1=%s bulunuyor=%s duz_esleme_buluyor=%s"
            % (_b6_a, _b6_b, _b6_c, _b6_d, _b6_bulunuyor, _b6_duz))

    # 🔴 B7 = B6'nin GERCEK-VERI BIRIMI (mutasyon duzleminde AYRI EKSEN DEGIL; olculdu 2 Agu).
    # B7'yi TEK BASINA kirmizi yakan ayirt edici mutant URETILEMEDI: B7'nin B6'dan fazlasi
    # bir VERI iddiasidir (katalogda bilesik ad tasiyan kayit VAR, hicbirinin jetonu
    # kaybolmuyor) ve mutasyon KODU degistirir. Dokundugu kod yolu B6'nin capaladigi yolun
    # ALT KUMESIDIR — B6 mekanizmanin CIKTI LISTESINI birebir capalar, B7 yalnizca jetonun
    # korunmasini. Bu yuzden mutasyon surucusunde M20 ikisini BIRLIKTE beyan eder
    # ([[beyan-edilmis-survivor]]); iddia olarak burada KALIR cunku gercek veri uzerinde
    # (sentetik fikstürun goremeyecegi katalog buyumesine karsi) bagimsiz nobet tutar.
    # B7 — GERCEK KATALOG TARAMASI. Sayi iddia DEGIL (katalog her gun buyuyor, dondurulmus
    # bir sayi yayin durdururdu) — IDDIA sudur: bilesik ad tasiyan HER GERCEK kayit,
    # kanoniklestirmeden SONRA da `Mercedes-Benz` sorgusuyla bulunur. Tarayicinin fiilen
    # calistigi POZITIF KONTROL ile kanitlanir (A2 deseni): sentetik, jetonu KESIN kaybeden
    # bir kayit listeye katilir ve tarama TAM ONU "duz eslemede kaybeder" diye isaretlemeli.
    _b7_poz = _urun(marka=["Mercedes-Benz"])
    _b7_poz["id"] = "B7-POZITIF-KONTROL"
    _b7_poz["baslik"] = "Kanal adaptoru"
    _b7_poz["aciklama"] = "Kanal adaptoru"
    _b7_tasiyan, _b7_duz_kayip, _b7_kalan_kayip = [], [], []
    for u in list(katalog) + [_b7_poz]:
        if not isinstance(u, dict) or not isinstance(u.get("marka"), list):
            continue
        ham_liste = [x for x in u["marka"] if A.bilesik_marka_sebebi(x) is not None]
        if not ham_liste:
            continue
        _b7_tasiyan.append(u.get("id"))
        duz = []
        for x in u["marka"]:
            k = A.bilesik_marka_kanonik(x)
            if k not in duz:
                duz.append(k)
        yeni = A.bilesik_marka_kanoniklestir(u)
        for ham in ham_liste:
            if not A.arama_jetonu_korunuyor(dict(u, marka=duz), ham):
                _b7_duz_kayip.append(u.get("id"))
            if not A.arama_jetonu_korunuyor(dict(u, marka=yeni), ham):
                _b7_kalan_kayip.append(u.get("id"))
    _b7_bas = sum(1 for u in katalog if isinstance(u, dict)
                  and isinstance(u.get("marka"), list) and u["marka"]
                  and A.bilesik_marka_sebebi(u["marka"][0]) is not None)
    dogrula("B7 KATALOG TARAMASI: bilesik ad tasiyan %d gercek kayitta kanoniklestirme "
            "sonrasi arama jetonu kaybi 0 VE tarayici fiilen calisiyor — duz eslemede "
            "kaybeden sentetik kayit TAM OLARAK yakalaniyor (pozitif kontrol)"
            % (len(_b7_tasiyan) - 1),
            "B7-POZITIF-KONTROL" in _b7_duz_kayip and not _b7_kalan_kayip
            and len(_b7_tasiyan) > 1,
            "tasiyan=%d duz_kayip=%s kalan_kayip=%s"
            % (len(_b7_tasiyan), _b7_duz_kayip[:6], _b7_kalan_kayip[:6]))
    print("  OLCUM (bilesik ad): `marka` ICINDE tasiyan %d kayit · `marka[0]` olan %d "
          "(MaCiT 'marka-basi' kovasi) · duz eslemenin arama jetonunu DUSURDUGU %d · "
          "mekanizmadan sonra kalan kayip %d"
          % (len(_b7_tasiyan) - 1, _b7_bas,
             len([i for i in _b7_duz_kayip if i != "B7-POZITIF-KONTROL"]),
             len(_b7_kalan_kayip)))

    # ══ B8/B9/B10 — TABLONUN BUYUME OLCUTU (2. tur) ═══════════════════════════════
    # B1 tablonun ICERIGINI donduruyor ama "yeni bir giris DOGRU MU" sorusunu SORMUYORDU:
    # capa guncellenerek herhangi bir jeton eklenebilirdi ve kapi yalnizca "tablo degisti"
    # derdi. Asagidaki uc eksen o bosluğu kapatir ve UCU DE gercek katalogda olculur.
    K = yukle(kok, "marka_katla", "marka_katla.py")

    # 🔴 BICIM SUZGECI EN BASTA — anlam eksenleri (B8/B10) yalniz BICIMI TANINAN kayitlari
    # okur, BICIM ihlali ayri bir eksende (B9) KIRMIZI yanar. Ters sira olculen bir delikti:
    # `("Pajero Mini": (None, "AYRISMA"))` bicimsiz kaydi B8'de `markaKatla(t) == None`
    # karsilastirmasina duser, False uretir ve "sorun yok" denirdi (rc=0, SESSIZ).
    def _red_sinif(sinif):
        return [(t, v[0]) for t, v in A.BILESIK_MARKA_REDDEDILEN.items()
                if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str)
                and v[0].strip() and v[1] == sinif]

    # B8 — SITE UYUMU (AYRISMA NOBETI). Tablo, katalogu ve D1'i sitenin KENDI kuratorlu
    # katlamasiyla (index.html markaKatla) CELISKIYE sokamaz. Celisirse musteri sitede bir
    # sey, Ege'de baskasini gorur ve hicbir alarm calmaz — bu evin en pahali sessiz hatasi.
    # Eksen BOS DEGIL: AYRISMA sinifindaki olculen 4 aday tam da bu olcutten DUSUYOR
    # (tek yonlu olsaydi "her sey gecer" diyen olu bir nobetci olurdu).
    _b8_tablo_bozan = [(k, v, K.markaKatla(k)) for k, v in A.BILESIK_MARKA_KANONIK.items()
                       if K.markaKatla(k) != v]
    _b8_ayrisma = _red_sinif("AYRISMA")
    _b8_ayrisma_bozan = [(t, h) for t, h in _b8_ayrisma if K.markaKatla(t) == h]
    dogrula("B8 SITE UYUMU: tablonun HER girisini site (index.html markaKatla) ZATEN ayni "
            "kanonik markaya katliyor — tablo katalog/D1'i sitenin hukmuyle AYRISTIRAMAZ; "
            "AYRISMA sinifindaki %d olculen aday ise bu olcutten DUSUYOR (eksen bos degil)"
            % len(_b8_ayrisma),
            not _b8_tablo_bozan and not _b8_ayrisma_bozan and len(_b8_ayrisma) > 0,
            "tablo_bozan=%s ayrisma_bozan=%s" % (_b8_tablo_bozan, _b8_ayrisma_bozan))

    # B9 — REDDEDILEN ADAY CAPASI. Yargilanip ELENEN bir jeton sessizce tabloya sizamaz ve
    # kumeden sessizce dusemez (UYUM_MARKA_ELENEN deseni; S2 dersi: SAYI degil KIMLIK).
    # Ayrica kayit KIRLETILEMEZ: her uye gercekten "kanonik marka iceren bilesik ad"
    # sinifinda olmali, yoksa red kumesi ilgisiz jetonlarla sisirilip capayi anlamsizlastirir.
    _b9_kesisim = sorted(set(A.BILESIK_MARKA_KANONIK) & set(A.BILESIK_MARKA_REDDEDILEN))
    _b9_imza = A.bilesik_red_imzasi()
    # 🔴 BICIM FAIL-CLOSED (olculen delik, 2 Agu): once yalnizca SINIF alani olculuyordu,
    # bu yuzden `("Pajero Mini": (None, "AYRISMA"))` gibi TIPI BOZUK bir kayit kapidan
    # SESSIZCE geciyordu (rc=0) — B8 `markaKatla(t) == None` karsilastirmasinda False
    # uretip "sorun yok" diyordu. Kayit BICIMI taninmiyorsa varsayilana DUSULMEZ, KIRMIZI
    # yanar. (Hedefin KAPALI MARKA KUMESINDE olmasi BILEREK SART DEGIL: hedef alani B8/B10'un
    # anlam ekseni; buraya baglansaydi o eksenlerin ayirt edici mutantlari B9'a da carpar
    # ve uc iddia tek kod yoluna duserdi.)
    _b9_sinif = sorted(
        t for t, v in A.BILESIK_MARKA_REDDEDILEN.items()
        if not (isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str)
                and v[0].strip() and v[1] in A.BILESIK_RED_SINIFLARI))
    _b9_bilesensiz = sorted(t for t in A.BILESIK_MARKA_REDDEDILEN
                            if not A.bilesik_ad_bileseni(t))
    # Tarayici TERS yonde de dogru olmali: kanonik markanin KENDISI aday DEGILDIR
    # (`Volvo Penta`/`Land Rover` cok kelimeli KANONIK markalardir — [[uyum-marka-mimar-eki]]
    # onlari AYRI ev sahibi ilan etti). Bu yon olculmezse "her uye bilesik-ad sinifinda"
    # iddiasi bosalir: her seyi aday sayan bir tarayici da onu YESIL gecirirdi.
    _b9_yanlis_aday = sorted(
        m for m in ("Volvo Penta", "Land Rover", "Alfa Romeo", "Black and Decker",
                    "Mercedes", "Rolls-Royce", "F-150", "206+")
        if A.bilesik_ad_bileseni(m))
    # FAIL-CLOSED: reddi KAYDA GECIRMEK bir ESLEME YARATMAMALI.
    _b9_sizan = sorted(t for t in A.BILESIK_MARKA_REDDEDILEN
                       if A.bilesik_marka_kanonik(t) != t
                       or A.bilesik_marka_sebebi(t) is not None)
    dogrula("B9 REDDEDILEN CAPASI: %d yargilanmis aday jetonun KIMLIGI donmus imza ile "
            "birebir, tablo ile kesisim YOK, her uye kapali sinif kumesinden ve gercekten "
            "bilesik-ad sinifinda (ters yon: 8 kanonik/mesru jeton aday SAYILMIYOR); "
            "reddi kayda gecirmek ESLEME YARATMIYOR (fail-closed)"
            % A.BILESIK_RED_SAYISI,
            _b9_imza == A.BILESIK_RED_IMZA
            and len(A.BILESIK_MARKA_REDDEDILEN) == A.BILESIK_RED_SAYISI
            and not _b9_kesisim and not _b9_sinif and not _b9_bilesensiz
            and not _b9_yanlis_aday and not _b9_sizan,
            "imza=%s beklenen=%s sayi=%d kesisim=%s sinif=%s bilesensiz=%s "
            "yanlis_aday=%s sizan=%s"
            % (_b9_imza, A.BILESIK_RED_IMZA, len(A.BILESIK_MARKA_REDDEDILEN),
               _b9_kesisim, _b9_sinif, _b9_bilesensiz, _b9_yanlis_aday, _b9_sizan))

    # B10 — 🔴 YANLIS-POZITIF KAPISI (bu turun asil kapisi). Iki yonlu:
    #  (a) FAYDASIZ sinifinin YAPISAL olcutu: jeton "<kanonik marka> <model>" bicimindedir
    #      (site onu zaten ayni markaya katliyor ve jeton markanin onekiyle basliyor) ->
    #      bilesik MARKA ADI degil MODEL jetonudur, tabloya girmez. Olcut YAPISALDIR,
    #      katalog sayisina bagli DEGIL: bagli olsaydi kardes mimarin her yeni partisi bu
    #      kapiyi kirmizi yakip TUM ekibin yayinini durdurabilirdi.
    #  (b) NEGATIF OLCUM: tablo gercek kataloga uygulandiginda, katalogun TAM kelime
    #      dagarciginda sonucu DEGISEN sorgu sayisi 0 olmali. Bu, "benzin -> benz" turu
    #      olculmus sisme vakasinin tekrarini kapatan eksendir; ORNEKLEME YOK, dagarcigin
    #      tamami taranir. Tarayici OLU DEGIL: sisme URETEN sentetik bir esleme ayni
    #      tarayiciyla olculur ve YAKALANMALI (pozitif kontrol).
    _b10_faydasiz = _red_sinif("FAYDASIZ")
    _b10_yapisal_bozan = [
        (t, h, K.markaKatla(t)) for t, h in _b10_faydasiz
        if K.markaKatla(t) != h or t == h
        or not A.model_normalize(t).startswith(A.model_normalize(h))]

    # Dagarcik = katalogun TUM arama metni jetonlari (>=3 harf). Sorgu tarafi `tokenlar()`
    # ile kok alir; bir sorgunun sonucu YALNIZ `marka` dizisi degisen kayitlar uzerinden
    # kayabilir (digerlerinin katkisi ONCE/SONRA ozdes) -> sapma orada olculur.
    _b10_hs0 = [A.haystack(u) for u in katalog if isinstance(u, dict)]
    _b10_dagarcik = set()
    for _hs in _b10_hs0:
        for _w in _hs.split():
            _w = _w.strip(".,;:()[]/\"'!?")
            if len(_w) >= 3:
                _b10_dagarcik.add(_w)
    # Turkce carpisma adaylari ELLE eklenir: `benzin` sorgusu `benz` kokune iner ve
    # `Mercedes-Benz` yazimina ALT-DIZE olarak carpar — olculmus tuzagin ta kendisi.
    _b10_dagarcik |= {"benzin", "benzer", "benzeri", "benzinli", "mini", "minik",
                      "mercedes", "mercedes-benz", "rover", "renault"}
    _b10_kok = {}
    for _q in _b10_dagarcik:
        _tk = A.tokenlar(_q)
        if len(_tk) == 1:
            _b10_kok.setdefault(_tk[0], []).append(_q)
    _b10_enuzun = max(len(_k) for _k in _b10_kok)

    def _b10_sapma(kayitlar, yeni_markalar):
        """Sorgu sonucu ONCE/SONRA degisen sorgular — {sorgu: sapma}."""
        idx = [i for i in range(len(kayitlar))
               if list(kayitlar[i].get("marka") or []) != yeni_markalar[i]]
        eski = {i: A.haystack(kayitlar[i]) for i in idx}
        yeni = {i: A.haystack(dict(kayitlar[i], marka=yeni_markalar[i])) for i in idx}
        adaylar = set()
        for i in idx:
            for metin in (eski[i], yeni[i]):
                n = len(metin)
                for a in range(n):
                    for L in range(3, min(_b10_enuzun, n - a) + 1):
                        p = metin[a:a + L]
                        if p in _b10_kok:
                            adaylar.add(p)
        sapma = {}
        for _k in adaylar:
            for _q in _b10_kok[_k]:
                tk = A.tokenlar(_q)
                d = sum(int(all(t in yeni[i] for t in tk))
                        - int(all(t in eski[i] for t in tk)) for i in idx)
                if d:
                    sapma[_q] = d
        return len(idx), sapma

    _b10_gercek = [u for u in katalog if isinstance(u, dict)]
    _b10_deg, _b10_sap = _b10_sapma(
        _b10_gercek, [A.bilesik_marka_kanoniklestir(u) for u in _b10_gercek])
    # POZITIF KONTROL — tarayici FIILEN calisiyor mu? Sentetik kayit `Mercedes` jetonunu
    # HICBIR yerinde tasimiyor; kanoniklestirme onu arama metnine SOKAR -> `mercedes`
    # sorgusu SISER ve tarayici bunu YAKALAMALI. Yakalamiyorsa yukaridaki "sapma 0"
    # hukmu BOS bir yesildir ([[nobetci-fikstur-sekli]]).
    _b10_poz = _urun(marka=["Sahte-Bilesik Ad"])
    _b10_poz["baslik"] = "Kanal adaptoru"
    _b10_poz["aciklama"] = "Kanal adaptoru"
    _b10_poz["id"] = "b10-pozitif-kontrol"
    _b10_pdeg, _b10_psap = _b10_sapma([_b10_poz], [["Mercedes"]])
    dogrula("B10 YANLIS-POZITIF KAPISI: FAYDASIZ sinifindaki %d aday YAPISAL olcutle "
            "'<marka> <model>' jetonu (tabloya giremez) VE tablo gercek kataloga "
            "uygulandiginda %d kaydin `marka`si degisirken katalogun TAM dagarciginda "
            "(%d sorgu) sonucu degisen sorgu 0 — sisme YOK; tarayici olu degil, sisme "
            "ureten sentetik esleme YAKALANIYOR"
            % (len(_b10_faydasiz), _b10_deg, len(_b10_dagarcik)),
            not _b10_yapisal_bozan and not _b10_sap and len(_b10_faydasiz) > 0
            and _b10_pdeg == 1 and _b10_psap.get("mercedes", 0) > 0,
            "yapisal_bozan=%s sapma=%s pozitif_kontrol=%s"
            % (_b10_yapisal_bozan, sorted(_b10_sap.items())[:8],
               sorted(_b10_psap.items())[:4]))
    # OLCUM (BLOKLAMAZ): katalog buyudukce yeni bir bilesik aday dogabilir. Sayi kapiya
    # baglanmaz — baglansaydi kardes mimarin her yeni partisi yayini durdurabilirdi; ama
    # GORUNUR kalir ki bir sonraki tur onu yargilasin.
    _b10_aday = set()
    for u in katalog:
        if isinstance(u, dict) and isinstance(u.get("marka"), list):
            for j in u["marka"]:
                if isinstance(j, str) and A.bilesik_ad_bileseni(j):
                    _b10_aday.add(j)
    print("  OLCUM (buyume olcutu): bilesen tasiyan tekil jeton %d · tabloda %d · "
          "reddedilen %d (AYRISMA %d / FAYDASIZ %d) · siniflandirilmamis %s"
          % (len(_b10_aday), len(A.BILESIK_MARKA_KANONIK),
             len(A.BILESIK_MARKA_REDDEDILEN), len(_b8_ayrisma), len(_b10_faydasiz),
             sorted(_b10_aday - set(A.BILESIK_MARKA_KANONIK)
                    - set(A.BILESIK_MARKA_REDDEDILEN))))
    print("  OLCUM (fayda): tablo %s · FAYDASIZ sinifinin kazanci %s"
          % (["%s->%s +%d" % (k, v, A.bilesik_marka_fayda_kazanci(katalog, k, v))
              for k, v in A.BILESIK_MARKA_KANONIK.items()],
             sorted({A.bilesik_marka_fayda_kazanci(katalog, t, h)
                     for t, h in _b10_faydasiz})))

    # 🔴 IDDIA TABANI — KOSUMLAR ARASI CAPA (commit'ler arasi sessiz kapsam kaybi kapisi).
    # Mutasyon surucusunun sayi sarti yalnizca TEK KOSUM icindedir: taban her seferinde
    # M00'da yeniden olculdugu icin, bir iddia SILINIP commit'lenirse hem kabul hem
    # mutasyon YESIL kalirdi (bagimsiz curutucu S1'i silerek gosterdi: 35 GECTI, rc=0).
    # YALNIZ DUSUS kirmizi yakar; ARTIS serbesttir — mesru iddia eklemek bloklanmamali.
    _toplam = gecen[0] + kalan[0]
    _taban_dustu = _toplam < IDDIA_TABANI
    if _taban_dustu:
        print("\n  🔴 IDDIA TABANI DUSTU: olculen %d < beklenen %d (IDDIA_TABANI) — bir "
              "kabul iddiasi SESSIZCE kayboldu. Iddia silmek mesruysa IDDIA_TABANI'ni "
              "AYNI commit'te dusur ve gerekcesini yaz." % (_toplam, IDDIA_TABANI))
    elif _toplam > IDDIA_TABANI:
        print("\n  OLCUM: iddia sayisi %d, taban %d — ARTIS serbest (IDDIA_TABANI'ni "
              "yukselt ki capa ilerlesin)." % (_toplam, IDDIA_TABANI))
    print("\nSONUC: %s — gecen %d · kalan %d · iddia %d (taban %d)"
          % ("YESIL" if kalan[0] == 0 and not _taban_dustu else "KIRMIZI",
             gecen[0], kalan[0], _toplam, IDDIA_TABANI))
    return 0 if (kalan[0] == 0 and not _taban_dustu) else 1


# ── CIFT YONLU MUTASYON ─────────────────────────────────────────────────────────────
# KAYIT: (kod, dosya, eski, yeni, beyan, olcut, aciklama)
#
# 🔴 BEYAN = MUTANTIN KIRMIZI YAKACAGI IDDIA KODLARI. "kirmizi yandi" YETMEZ: HANGI
#    iddianin yandigi olculur ve BEYANLA karsilastirilir. Beyansiz surucu yalnizca
#    "en az bir sey kirmizi" der; yarin fazladan bir iddiayi dusuren bir mutant
#    SESSIZCE gecerdi ([[beyan-edilmis-survivor]] · [[mutasyon-kaniti-yeniden-uretilebilir]]).
#    beyan == []  -> KONTROL MUTANTI (YESIL beklenir; kapinin gereginden genis olmadigi).
#
# 🔴 OLCUT, HER KAYDIN KENDI ALANINDA (tools/duzelt-uyum-mutasyon.py ile AYNI mekanizma):
#    ESIT -> kirmizi kume BEYANA TAM ESIT. Fazladan kirmizi da KUSURDUR. TEK IZINLI OLCUT.
#    Baska bir deger yazilirsa surucu kaydi mutasyon KOSULMADAN reddeder (fail-closed).
#    🔴 GEVSEK OLCUT (beyan ⊆ kirmizi) BILEREK YOK: bagimsiz curutucu boyle bir kacis
#    kapisini TEK KELIMELIK bir "gerekce" yazarak asti ve 6 beyansiz kirmiziyi gizledi.
#    Metin arayan bir garanti, garanti DEGILDIR. Fazladan kirmizi mesruysa BEYANA YAZILIR
#    — o zaten ESIT'in kendisidir.
#
# Capa kayarsa tur KIRMIZI yanar ve mutant SAYILMAZ — "capa bulunamadi" ASLA yesil degildir.
# Iddia SAYISI da her kosumda taban ile karsilastirilir: sayi duserse mutant kapiyi
# COKERTMISTIR ve o "kirmizi" bir OLCUM DEGILDIR ([[hukum-yanlis-birimde]]).
MUTANTLAR = [
    ("M1", "arama.py",
     '    if deger not in UYUM_MARKA_IZINLI:\n        return ""\n', "",
     ["S5", "S6", "V1", "V2", "V15", "V10", "B4"], "ESIT",
     "V1: kapali kume kontrolu kalkar -> her marka kabul, sahte marka sayfasi acilir"),
    ("M2", "arama.py",
     "    if deger not in UYUM_MARKA_IZINLI:",
     "    if deger.strip() not in UYUM_MARKA_IZINLI:", ["V2"], "ESIT",
     "V2: strip() uyelik testinin ICINE girer -> ' Ford' kabul (bu depoda `altkategori`de "
     "GERCEKTEN yasanmis hata: katalog ham, D1 kirpilmis)"),
    ("M3", "arama.py",
     re.compile(r"    turetilen = marka_uyumdan_turet\(u\)\n.*?"
                r"TURETILIR\" % \(mevcut, turetilen\)\)\n", re.S), "", ["V6"], "ESIT",
     "V6: K5 ikiz kontrolu kalkar -> `marka` ile `uyum` sessizce ayrisir"),
    ("M4", "arama.py",
     '    m = norm(m)\n    m = "".join(c for c in unicodedata.normalize("NFKD", m)\n'
     "                if not unicodedata.combining(c))\n"
     '    return _MODEL_AYIRAC_RE.sub("", m)\n', "    return m\n",
     ["V7", "V16", "B4", "B9", "B10"], "ESIT",
     "V7: model normalizasyonu KIMLIK fonksiyonu olur -> `F-150`/`F150` iki ayri sayfa; "
     "ayni normalizasyon marka/model sinirini (V16), yazim-varyanti capasini (B4), bilesen "
     "tarayicisini (B9) ve FAYDASIZ onek olcutunu (B10) da besledigi icin o iddialar AYNI "
     "kod yolundan birlikte duser"),
    ("M5", "arama.py",
     "    if uyum_sebebi(u) is not None:\n        return []\n", "",
     ["V4", "V9", "V10"], "ESIT",
     "V9/V10: kanonik FAIL-OPEN olur -> gecersiz/enjekte deger D1'e HAM gider (V4 bozuk "
     "tip fikstürü de ayni fail-open'dan gecer)"),
    ("M6", "arama.py",
     '    if son < bas:\n        return "yil araligi TERS: [%d, %d]" % (bas, son)\n', "",
     ["V5", "V9"], "ESIT",
     "V5: `yil` aralik kontrolu kalkar -> [2020, 2003] gecer (V9 fail-closed iddiasi ayni "
     "ters araligi fikstür olarak kullanir)"),
    ("M7", "arama.py",
     "        for deger in jetonlar:\n"
     "            if deger and deger not in turetilen:\n"
     "                turetilen.append(deger)\n",
     "        for aday in jetonlar:\n"
     "            if aday and aday not in turetilen:\n"
     "                turetilen.append(aday)\n", [], "ESIT",
     "KONTROL MUTANTI: davranisi DEGISTIRMEYEN yeniden adlandirma — kapi bicimi degil "
     "DAVRANISI olcuyor mu?"),
    # EK MUTANT (spec disi, olculen kusurdan dogdu): V10 bu turda GERCEKTEN kirmizi yandi
    # ('../../etc/passwd' karakter beyaz listesinden gecmisti). Kusuru kapatan kural da
    # mutasyonla olculmeli, yoksa yarin sessizce geri alinabilir.
    ("M8", "arama.py",
     re.compile(r"    if d\[0\] in UYUM_SERBEST_AYIRAC or d\[-1\] in UYUM_SERBEST_AYIRAC:"
                r"\n.*?% \(ad, onceki \+ simdiki\)\)\n", re.S), "", ["V10"], "ESIT",
     "V10: ayirac KONUM kurali kalkar -> '../../etc/passwd' model/oem alanindan GECER"),
    # M9 — mimar maddesi (b): turetme ESKI kurala (yalniz marka) donerse KIRMIZI.
    # Bu mutant tam olarak "sessiz arama kaybi" senaryosudur: kod calisir, kapi eski
    # haliyle yesil yanardi, ama backfill gunu `Focus` haystack'ten duserdi.
    ("M9", "arama.py",
     '        jetonlar = (uyum_marka_kanonik(oge.get("marka")),\n'
     '                    model_metin(oge.get("model")))\n',
     '        jetonlar = (uyum_marka_kanonik(oge.get("marka")),)\n',
     ["V6", "V8", "V11", "V12", "V13", "V14", "V17", "A1", "A2", "A5"], "ESIT",
     "V6/V12/A5: turetme YALNIZ markaya doner -> model jetonlari `marka`dan ve dolayisiyla "
     "haystack'ten SESSIZCE duser. GENIS BEYAN: K5 ikiz kapisi turetilen `marka`yi "
     "REDDETTIGI icin `uyum_kanonik` bos doner ve model jetonu tasiyan HER fikstür "
     "(V8/V11/V13/V14/V17) ile gercek katalog taramalari (A1/A2/A5) ayni kablodan duser"),
    # M10 — turetme sirasi ters cevrilir (model once). Davranis DEGISIR: bugunku
    # ["marka","model"] dizilimi bozulur, ama arama metni ayni kalir -> yalniz sira
    # ekseni kirmizi yanmali (ayrismanin SIRA bileseni de olculuyor mu?).
    ("M10", "arama.py",
     '        jetonlar = (uyum_marka_kanonik(oge.get("marka")),\n'
     '                    model_metin(oge.get("model")))\n',
     '        jetonlar = (model_metin(oge.get("model")),\n'
     '                    uyum_marka_kanonik(oge.get("marka")))\n',
     ["V6", "V8", "V11", "V12", "V13", "V14", "V17", "A1", "A2", "A5"], "ESIT",
     "V12/A5: turetme SIRASI ters (model once) -> `marka` dizilimi bugunkunden kayar; "
     "kume M9 ile AYNIDIR cunku red yine K5 ikiz kapisindan gelir"),
    # M11 — marka/model sinirindaki ikiz kapisi kalkar. `Kia` kumedeyken `KIA` model
    # olarak gecer ve ayni gercek IKI ayri sayfa uretir.
    ("M11", "arama.py",
     re.compile(r"    for ad in \(\"model\", \"motor\"\):\n"
                r"        sebep = marka_varyanti_sebebi\(ad, oge\.get\(ad\)\)\n"
                r"        if sebep:\n            return sebep\n"), "", ["V16"], "ESIT",
     "V16: marka/model sinirindaki ikiz kapisi kalkar -> `KIA` model olarak GECER"),
    # ── BAGIMSIZ CURUTUCUDEN GELEN IKI MUTANT (2 Agu). Ikisi de ONCE SAG KALMISTI;
    # kapinin o turdeki iddialari onlari gormuyordu. Kural degisti, mutantlar KALICI.
    # M12 capasi ELENEN literalinin ICINDEKI jetona bakiyor (kume buyudugunde/kuculdugunde
    # de eslesir); mutant jetonu ELENEN'den CIKARIP IZINLI'ye TASIR — birlesim SABIT kalir.
    ("M12", "arama.py",
     re.compile(r'("Toplife", )"Turbo", ("Victoria",\n\}\))'),
     '\\1\\2\nUYUM_MARKA_IZINLI = frozenset(UYUM_MARKA_IZINLI | {"Turbo"})',
     ["S2"], "ESIT",
     "S2: ELENEN'den cikarilan jeton IZINLI'ye TASINIR (birlesim SABIT kalir) -> sayi "
     "korumasi bunu GORMUYORDU, kimlik korumasi goruyor"),
    ("M13", "arama.py",
     re.compile(r"    imzalar = \[json\.dumps.*?len\(set\(imzalar\)\)\)\n", re.S), "",
     ["V17"], "ESIT",
     "V17: MUKERRER oge kontrolu tamamen silinir -> ayni uyum ogesi iki kez yazilabilir"),
    # ── BILESIK MARKA ADI (tools/paket-bilesik-marka.md). B1/B3/B4/B5/B6 icin TEK-KIRMIZI
    # mutant: her eksen TEK BASINA olculebiliyor mu, yoksa iddialar birbirinin bayragini mi
    # okuyor? ([[beyan-edilmis-survivor]] — zincirden gecen iddia katmanlarin VEYA'sini olcer.)
    ("M14", "arama.py",
     'BILESIK_MARKA_KANONIK = {\n    "Mercedes-Benz": "Mercedes",\n}\n',
     'BILESIK_MARKA_KANONIK = {\n    "Mercedes-Benz": "Mercedes",\n'
     '    "Mercedes-AMG": "Mercedes",\n}\n', ["B1"], "ESIT",
     "B1: kapali tabloya DENETIMSIZ ikinci giris — Okan yalniz TEK eslemeyi verdi; tablo "
     "sessizce buyurse her bilesik ad tartisilmadan katlanirdi"),
    ("M15", "arama.py",
     "    return BILESIK_MARKA_KANONIK.get(deger, deger)\n",
     '    for _m in UYUM_MARKA_IZINLI:\n        if deger.startswith(_m + " "):\n'
     "            return _m\n    return BILESIK_MARKA_KANONIK.get(deger, deger)\n",
     ["B2", "B9"], "ESIT",
     "B2: TABLO HIC OKUNMADAN 'icerdigi markayi dondur' kurali — uydurma bilesik ad "
     "(`Mercedes Voranta`) sessizce `Mercedes`e katlanir. B9 de KIRMIZI ve bu DOGRUDUR: "
     "reddi KAYDA GECIRMEK esleme yaratmamali; mutant altinda REDDEDILEN jetonlar "
     "(`Peugeot 205`, `Volvo 240` ...) fiilen eslenir — B9'un fail-closed yonu tam bunu olcer"),
    ("M16", "arama.py",
     "    return BILESIK_MARKA_KANONIK.get(deger, deger)\n",
     '    return BILESIK_MARKA_KANONIK.get(deger, deger.rstrip("+"))\n', ["B3"], "ESIT",
     "B3: GENEL NORMALIZASYON (sonek soyma) — olculen mesru jeton `206+` yenir ve o "
     "Peugeot modeli aramadan hicbir kirmizi yanmadan duser"),
    ("M17", "arama.py",
     "_UYUM_MARKA_ANAHTARLARI = frozenset(model_normalize(m) for m in UYUM_MARKA_IZINLI)\n",
     "_UYUM_MARKA_ANAHTARLARI = frozenset(model_normalize(m)\n"
     "                                    for m in UYUM_MARKA_IZINLI | URETICI_MARKA)\n",
     ["A1", "B4"], "ESIT",
     "B4: yazim-varyanti anahtar kumesi URETICI markalarina genisler -> capa 7'den 21'e "
     "kayar ve MaCiT'in kova ayrimi sessizce yanlislanir (A1 gercek katalog taramasi ayni "
     "genislemeyi ihlal olarak gorur)"),
    ("M18", "arama.py",
     "    return BILESIK_MARKA_KANONIK.get(deger, deger)\n",
     "    if deger not in BILESIK_MARKA_KANONIK:\n        for _m in UYUM_MARKA_IZINLI:\n"
     "            if model_normalize(_m) == model_normalize(deger):\n"
     "                return _m\n    return BILESIK_MARKA_KANONIK.get(deger, deger)\n",
     ["B5", "B10"], "ESIT",
     "B5: bilesik-ad yolu YAZIM VARYANTI yoluna delege eder (iki kural sinifi tek capada "
     "erir) -> `KIA` bilesik tablodan `Kia`ya katlanir, iki iddia TEK kod yoluna duser. "
     "B10 de KIRMIZI ve bu DOGRUDUR: delege edilen yol gercek katalogda 7 yazim varyantini "
     "katlar, arama metni degisir ve NEGATIF OLCUM sapmayi YAKALAR (sisme/erime 0 degil)"),
    ("M19", "arama.py",
     "        if not arama_jetonu_korunuyor(aday, ham) and ham not in yeni:\n",
     "        if ham not in yeni:\n", ["B6"], "ESIT",
     "B6: arama takmasi KOSULSUZ eklenir -> jeton zaten korunuyorken arama yuzeyi "
     "GENISLER (gereksiz genisleme de olculmemis bir davranis degisikligidir)"),
    # 🔴 M20 — B6 ve B7 BIRLIKTE beyan edilir (mimar maddesi 2, sik (b); OLCULDU 2 Agu):
    # B7'yi TEK BASINA yakan AYIRT EDICI mutant URETILEMEDI, cunku B7'nin B6'dan FAZLASI
    # bir VERI iddiasidir (gercek katalogda bilesik ad tasiyan kayit VAR ve hicbirinin
    # arama jetonu kaybolmuyor) — mutasyon KODU degistirir, veriyi degil. B7'nin dokundugu
    # kod yolu B6'nin capaladigi yolun ALT KUMESIDIR: B6 mekanizmanin CIKTI LISTESINI
    # birebir capalar, B7 yalnizca jetonun korunmasini olcer. Olculen kanit (uc aday
    # kopyada kosuldu, hicbiri repoda kalmadi):
    #   * takma BASA eklenir -> yalniz B6 kirmizi (B7 yesil): B6 kesinlikle daha duyarli;
    #   * tarayici uyelik testi yerine esleme sonucuna bakar -> ikisi de YESIL;
    #   * B7'yi tek basina yakan TEK sey `len(marka) >= 2` gibi KEYFI bir esikti — uydurma
    #     mutantla ayri iddia ureltilmez ([[beyan-edilmis-survivor]]: ayirt edici mutant
    #     yoksa eksen AYRI iddia sayilmaz).
    # Sonuc: B7 kapida AYRI iddia olarak KALIR (gercek veri uzerinde bagimsiz nobet tutar)
    # ama mutasyon duzleminde B6'nin GERCEK-VERI BIRIMIDIR ve birlikte beyan edilir.
    ("M20", "arama.py",
     "        if not arama_jetonu_korunuyor(aday, ham) and ham not in yeni:\n"
     "            yeni.append(ham)\n", "        continue\n", ["B6", "B7", "B10"], "ESIT",
     "B6+B7 (BIRLIKTE beyan): takma HIC eklenmez -> duz esleme geri gelir ve "
     "`Mercedes-Benz` sorgusu 5 gercek kaydi SESSIZCE kaybeder (paketin varlik sebebi olan "
     "hata). B7 ayirt edici mutanti YOK; B6'nin gercek-veri birimidir. B10 de KIRMIZI ve bu "
     "DOGRUDUR: kaybolan `mercedes-benz` yazimi `benz` kokune inen sorgulari da dusurur — "
     "NEGATIF OLCUM sapmayi BAGIMSIZ olarak (dagarcik taramasiyla) yakalar"),
    # M23 — bagimsiz curutucude OLCULEN SAG KALAN: kanoniklestirme yalniz `marka[0]`'a
    # uygulanirsa (MaCiT'in "marka-basi" kovasi akil yurutmesi) hicbir iddia yanmiyordu.
    # Gercek katalogda bilesik adi 0'DAN BASKA konumda tasiyan 1 kayit var
    # (`['BMW', 'Mercedes-Benz']`) ve B6 fikstürlerinin HEPSI bilesik adi 0'da tasiyordu —
    # yani fikstür kor noktaydi. B6 fikstürune konum-1 vakasi eklendi, mutant KALICI.
    ("M23", "arama.py",
     "    for m in marka:\n        k = bilesik_marka_kanonik(m)\n",
     "    for _i, m in enumerate(marka):\n"
     "        k = bilesik_marka_kanonik(m) if _i == 0 else m\n", ["B6"], "ESIT",
     "B6: kanoniklestirme yalniz `marka[0]`'a uygulanir -> bilesik adi ikinci sirada "
     "tasiyan gercek kayit (`['BMW', 'Mercedes-Benz']`) HIC katlanmaz"),
    ("M21", "arama.py",
     "    for m in marka:\n        k = bilesik_marka_kanonik(m)\n"
     "        if k != m:\n            dusen.append(m)\n"
     "        if k not in yeni:\n            yeni.append(k)\n",
     "    for ad in marka:\n        kan = bilesik_marka_kanonik(ad)\n"
     "        if kan != ad:\n            dusen.append(ad)\n"
     "        if kan not in yeni:\n            yeni.append(kan)\n", [], "ESIT",
     "KONTROL MUTANTI: davranisi DEGISTIRMEYEN yeniden adlandirma — B ekseni bicimi degil "
     "DAVRANISI mi olcuyor?"),
    ("M22", "arama.py",
     'BILESIK_MARKA_KANONIK = {\n    "Mercedes-Benz": "Mercedes",\n}\n',
     'BILESIK_MARKA_KANONIK = dict([("Mercedes-Benz", "Mercedes")])\n', [], "ESIT",
     "KONTROL MUTANTI: tablo AYNI icerikle baska sozdiziminde kurulur — kapi tablonun "
     "METNINI degil ICERIGINI mi olcuyor?"),
    # ── TABLONUN BUYUME OLCUTU (B8/B9/B10) ─────────────────────────────────────────
    # Uc eksen BILEREK AYRI alanlara baglandi ki her biri TEK BASINA yakilabilsin:
    # B8 red kaydinin HEDEF alanini (AYRISMA sinifi), B9 ANAHTAR kumesini, B10 hedef
    # alanini (FAYDASIZ sinifi) okur. Tek imzaya baglanmis olsalardi bir mutant hepsini
    # birden yakar ve ucu AYRI iddia olmaktan cikardi ([[beyan-edilmis-survivor]]).
    ("M24", "arama.py",
     '    "Formula Renault": ("Renault", "AYRISMA"),\n',
     '    "Formula Renault": ("Formula Renault", "AYRISMA"),\n', ["B8"], "ESIT",
     "B8: AYRISMA sinifindaki bir adayin hedefi, sitenin ONU KATLADIGI degere esitlenir -> "
     "'site bu adayi katlamiyor' negatif yonu COKER ve eksen 'her sey gecer' diyen OLU bir "
     "nobetciye doner (tek yonlu olcum tuzagi)"),
    ("M25", "arama.py",
     '    "Range Rover": ("Rover", "AYRISMA"),\n', "", ["B9"], "ESIT",
     "B9: yargilanip ELENEN bir aday kumeden SESSIZCE dusurulur -> yarin ayni jeton "
     "'yeni kesif' diye tabloya girebilir ve `Range Rover` bir Land Rover parcasini AYRI "
     "bir marque olan `Rover` sayfasina baglar"),
    ("M26", "arama.py",
     '    "Volvo 240": ("Volvo", "FAYDASIZ"),\n',
     '    "Volvo 240": ("Mercedes", "FAYDASIZ"),\n', ["B10"], "ESIT",
     "B10: FAYDASIZ sinifinin YAPISAL olcutu (jeton hedef markanin onekiyle baslar ve site "
     "onu ayni markaya katlar) bozulur -> '<marka> <model>' jetonu ile GERCEK bir bilesik "
     "ad arasindaki ayrim kaybolur"),
    ("M27", "arama.py",
     '    if model_normalize(deger) in _UYUM_MARKA_ANAHTARLARI:\n        return ()\n',
     "", ["B9"], "ESIT",
     "B9: kanonik markanin KENDISI (`Volvo Penta`, `Land Rover`) 'bilesik aday' sayilir -> "
     "tarama ayri ev sahibi ilan edilmis jetonlari geri katlamaya davet eder ve red "
     "kumesinin 'gercekten bilesik-ad sinifinda' iddiasi anlamsizlasir"),
    # M29 — OLCULEN DELIGIN KALICI NOBETCISI: bicim suzgeci EN BASA alinmadan once bu kayit
    # kapidan SESSIZCE geciyordu (rc=0). B8 `markaKatla(t) == None` karsilastirmasinda False
    # uretip "sorun yok" diyordu; bicimi taninmayan kayit varsayilana DUSUYORDU.
    ("M29", "arama.py",
     '    "Pajero Mini": ("Mini", "AYRISMA"),\n',
     '    "Pajero Mini": (None, "AYRISMA"),\n', ["B9"], "ESIT",
     "B9: red kaydinin BICIMI bozulur (hedef metin degil) -> kayit taninmiyorsa varsayilana "
     "DUSULMEZ, KIRMIZI yanar; anlam eksenleri (B8/B10) bicimsiz kaydi hic okumaz"),
    ("M28", "arama.py",
     "BILESIK_RED_SINIFLARI = (\"AYRISMA\", \"FAYDASIZ\")\n",
     "BILESIK_RED_SINIFLARI = (\"AYRISMA\", \"FAYDASIZ\", \"BELIRSIZ\")\n", [], "ESIT",
     "KONTROL MUTANTI: kapali sinif kumesine KULLANILMAYAN bir sinif eklenir — kapi "
     "kumenin BOYUNU mu yoksa uyelerin FIILEN kullandigi siniflari mi olcuyor? (bugun "
     "hicbir uye BELIRSIZ tasimadigi icin davranis DEGISMEZ)"),
]

# 🔴 marka_katla.py B8/B10'un SITE UYUMU eksenini besler (index.html'in kuratorlu marka
# katlamasinin TEK KAYNAK Python portu). Mutant KOPYAYA uygulanacagi icin bu dosya da
# kopyaya girmeli; ayrica modul yuklenirken index.html'i AYRISTIRDIGI icin _kopya_kur
# o dosyayi da baglar. Eksik kalsaydi M00 kontrolu ImportError ile KIRMIZI yanar ve tum
# mutant sonuclari YALANCI olurdu (harness bozuklugu, mutant degil).
KOPYALANAN = ["arama.py", "marka_katla.py"]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _kopya_kur():
    tmp = tempfile.mkdtemp(prefix="pruvo-uyum-mut-")
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in KOPYALANAN:
        shutil.copy2(os.path.join(GERCEK_KOK, "tools", ad), os.path.join(tmp, "tools", ad))
    os.symlink(os.path.join(GERCEK_KOK, "urunler.json"), os.path.join(tmp, "urunler.json"))
    # marka_katla.py TANINMIS_MARKALAR'i index.html'den PARSE eder (kopya tutmaz) —
    # kopya agacinda da ayni dosyayi gormeli.
    os.symlink(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    return tmp


def _kok_kostur(tmp):
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", tmp],
                          capture_output=True, text=True)


def _mutasyon_uygula(metin, eski, yeni):
    if isinstance(eski, re.Pattern):
        esler = list(eski.finditer(metin))
        if len(esler) != 1:
            return None, len(esler)
        m = esler[0]
        return metin[:m.start()] + m.expand(yeni) + metin[m.end():], 1
    sayi = metin.count(eski)
    if sayi != 1:
        return None, sayi
    return metin.replace(eski, yeni), 1


def _capa_metni(eski):
    return eski.pattern if isinstance(eski, re.Pattern) else eski


OLCUTLER = ("ESIT",)


def _iddia_kodlari(cikti):
    """Kosum ciktisindan (kirmizi_kod_kumesi, tum_kod_listesi).

    Iddia adinin ILK jetonu kodudur ("KALDI B7 KATALOG..." -> "B7"). Kod okunamiyorsa
    satir SAYILIR ama isimsiz kalir — beyan karsilastirmasi o zaman eksik yakar.
    Toplam iddia sayisi = len(tum_kod_listesi).
    """
    kirmizi, tum = set(), []
    for satir in cikti.splitlines():
        s = satir.strip()
        for bas, kirmizi_mi in (("GECTI ", False), ("KALDI ", True)):
            if s.startswith(bas):
                parcalar = s[len(bas):].split()
                tum.append(parcalar[0] if parcalar else "?")
                if kirmizi_mi and parcalar:
                    kirmizi.add(parcalar[0])
    return kirmizi, tum


def _beyan_kapisi():
    """Kayitlarin KENDI sekli fail-closed dogrulanir: bilinmeyen olcut mutasyon
    KOSULMADAN reddedilir. Tek izinli olcut ESIT'tir; gevsek bir olcut YOKTUR, cunku
    "gerekce yazdim" demek gerekce OLMASINI saglamiyordu (metin araniyordu, yargi degil)."""
    hatalar = []
    kodlar = set()
    for kayit in MUTANTLAR:
        if len(kayit) != 7:
            hatalar.append("%r: kayit 7 alanli olmali (kod, dosya, eski, yeni, beyan, "
                           "olcut, aciklama)" % (kayit[0],))
            continue
        kod, _dosya, _eski, _yeni, beyan, olcut, _aciklama = kayit
        if kod in kodlar:
            hatalar.append("%s: MUKERRER mutant kodu" % kod)
        kodlar.add(kod)
        if olcut not in OLCUTLER:
            hatalar.append("%s: bilinmeyen olcut %r — TEK izinli olcut: %s (gevsek olcut "
                           "YOK: fazladan kirmizi mesruysa BEYANA yazilir)"
                           % (kod, olcut, ", ".join(OLCUTLER)))
        if not isinstance(beyan, list) or any(not isinstance(b, str) for b in beyan):
            hatalar.append("%s: beyan iddia KODLARINDAN olusan bir liste olmali" % kod)
    return hatalar


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    print("    KABUL = CIKIS KODU DEGIL: (1) iddia SAYISI taban ile ayni, (2) KIRMIZI "
          "IDDIA KODLARI mutantin BEYANIYLA olcute gore uyusuyor.")
    once = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    basarisiz = []

    sekil_hatalari = _beyan_kapisi()
    if sekil_hatalari:
        print("\nMUTASYON SONUCU: OLCULEMEDI — mutant kayitlari BOZUK:")
        for h in sekil_hatalari:
            print("  - " + h)
        return 1

    # M00 MUTASYONSUZ KONTROL (ZORUNLU ON-KOSUL): kopya agaci mutasyonsuz halde YESIL
    # vermezse harness BOZUKTUR ve butun "KIRMIZI" sonuclari YALANCIDIR (mutant degil,
    # cokme olculur). Olculmus vaka: eksik bir kopya dosyasi 14 mutantin 14'unu ayni
    # ImportError ile "olduruldu" gosterebilir. TABAN IDDIA SAYISI da burada OLCULUR
    # (capa DEGIL): her mutant kosumu bu sayiyla karsilastirilir.
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    t_kirmizi, t_kodlar = _iddia_kodlari((p0.stdout or "") + (p0.stderr or ""))
    taban_iddia = len(t_kodlar)
    kontrol_ok = p0.returncode == 0 and not t_kirmizi and taban_iddia > 0
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s (harness saglam mi) | TABAN IDDIA "
          "SAYISI = %d" % ("OK  " if kontrol_ok else "HATA",
                           "YESIL" if kontrol_ok else "KIRMIZI", taban_iddia))
    if not kontrol_ok:
        print("     " + (p0.stderr or p0.stdout).strip().splitlines()[-1][:300])
        shutil.rmtree(tmp0, ignore_errors=True)
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk, mutant sonuclari YALANCI.")
        return 1
    shutil.rmtree(tmp0, ignore_errors=True)

    uygulanan = 0
    matris = []
    tek_kirmizi = {}
    for kod, dosya, eski, yeni, beyan, olcut, aciklama in MUTANTLAR:
        beklenen = "KIRMIZI" if beyan else "YESIL"
        etiket = beklenen + ("/" + olcut if beyan else "")
        tmp = _kopya_kur()
        hedef = os.path.join(tmp, "tools", dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        mutant, sayi = _mutasyon_uygula(metin, eski, yeni)
        if mutant is None:
            basarisiz.append("%s CAPA BAYAT (%d kez eslesti, 1 olmali) %s: %s"
                             % (kod, sayi, dosya, _capa_metni(eski)[:70]))
            print("  HATA %s [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI | %s"
                  % (kod, etiket, dosya, sayi, aciklama))
            matris.append((kod, etiket, "-", "-", "-", ",".join(beyan) or "-"))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        if mutant == metin:
            basarisiz.append("%s MUTANT UYGULANMADI (metin DEGISMEDI) %s" % (kod, dosya))
            print("  HATA %s [%s] %s -> MUTANT UYGULANMADI | EKSEN OLCULMEDI | %s"
                  % (kod, etiket, dosya, aciklama))
            matris.append((kod, etiket, "-", "-", "-", ",".join(beyan) or "-"))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(mutant)
        uygulanan += 1
        p = _kok_kostur(tmp)
        cikti = (p.stdout or "") + (p.stderr or "")
        kirmizi, kodlar = _iddia_kodlari(cikti)
        iddia = len(kodlar)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        # 🔴 IDDIA SAYISI SARTI: mutant kabul testini COKERTEREK de rc!=0 verebilir
        # (IndexError/ImportError). Sayi duserse geri kalan iddialar HIC OLCULMEMISTIR ve
        # o "kirmizi" bir OLCUM DEGILDIR ([[hukum-yanlis-birimde]]).
        sayi_ok = (iddia == taban_iddia)
        notlar = []
        if not sayi_ok:
            notlar.append("IDDIA SAYISI TUTMUYOR (%s/%d) -> mutant kapiyi COKERTMIS; bu "
                          "'kirmizi' OLCUM DEGIL" % (iddia, taban_iddia))
        if beyan:
            eksik = [b for b in beyan if b not in kirmizi]
            fazla = sorted(kirmizi - set(beyan))
            if eksik:
                notlar.append("EKSIK: %s (mutant SAG KALDI)" % ",".join(eksik))
            if fazla:
                notlar.append("BEYAN DISI FAZLA KIRMIZI: %s (ya beyan ya iddia yanlis)"
                              % ",".join(fazla))
            gecti = (sayi_ok and goruldu == "KIRMIZI" and bool(kirmizi)
                     and not eksik and not fazla)
            if len(kirmizi) == 1:
                tek_kirmizi.setdefault(sorted(kirmizi)[0], []).append(kod)
        else:
            if kirmizi:
                notlar.append("KONTROL MUTANTI KIRMIZI YAKTI: %s (kapi bicimi olcuyor "
                              "olabilir)" % ",".join(sorted(kirmizi)))
            gecti = sayi_ok and goruldu == "YESIL" and not kirmizi
        if not gecti:
            basarisiz.append("%s %s: beklenen %s [%s] beyan=%s, olculen kirmizi=%s%s"
                             % (kod, dosya, beklenen, olcut, ",".join(beyan) or "-",
                                ",".join(sorted(kirmizi)) or "-",
                                (" | " + " | ".join(notlar)) if notlar else ""))
        print("  %s %s [%s] %s -> %s (iddia %s/%d · kirmizi %s)%s | %s"
              % ("OK  " if gecti else "HATA", kod, etiket, dosya, goruldu, iddia,
                 taban_iddia, ",".join(sorted(kirmizi)) or "-",
                 ("  ⚠️ " + " ⚠️ ".join(notlar)) if notlar else "", aciklama))
        if not gecti:
            for s in cikti.splitlines()[-6:]:
                print("        " + s.strip()[:150])
        matris.append((kod, etiket, str(p.returncode), "%s/%d" % (iddia, taban_iddia),
                       ",".join(sorted(kirmizi)) or "-", ",".join(beyan) or "-"))
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n  --- MUTASYON MATRISI (beyan ↔ olculen) ---")
    print("  %-5s %-15s %-6s %-9s %-28s %s"
          % ("kod", "beklenti", "cikis", "iddia", "olculen kirmizi", "beyan"))
    for satir in matris:
        print("  %-5s %-15s %-6s %-9s %-28s %s" % satir)

    # OLCUM (iddia DEGIL): hangi eksenin TEK BASINA yakilabilir mutanti var? Eksigi kapiyi
    # kirmizi yakmaz — ama "su eksen ayri iddia mi" tartismasi bu tablo ile yurutulur
    # ([[beyan-edilmis-survivor]]).
    print("\n  OLCUM — TEK-KIRMIZI HARITASI (ayirt edici mutanti OLAN eksenler): %s"
          % (", ".join("%s<-%s" % (e, ",".join(k))
                       for e, k in sorted(tek_kirmizi.items())) or "YOK"))

    # 🔴 KAPSAMIN NEREDE BITTIGI GORUNUR OLSUN (bloklamaz — SESSIZ de kalmaz): hicbir
    # mutantin beyaninda gecmeyen iddianin mutasyon kaniti YOKTUR; "kapi bu ekseni
    # olcuyor" hukmu o iddia icin OLCULMEMISTIR ([[beyan-edilmis-survivor]]).
    beyanlanan = set()
    for _k, _d, _e, _y, _beyan, _o, _a in MUTANTLAR:
        beyanlanan |= set(_beyan)
    kapsanmayan = [k for k in t_kodlar if k not in beyanlanan]
    print("  OLCUM — HICBIR MUTANT BEYANINDA GECMEYEN IDDIA: %d/%d (%s)"
          % (len(kapsanmayan), taban_iddia, ",".join(kapsanmayan) or "-"))

    sonra = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    bozuk = [d for d in once if once[d] != sonra[d]]
    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(once), "DEGISMEDI ✔" if not bozuk else "DEGISTI ✘ %s" % bozuk))
    if bozuk:
        basarisiz.append("CANLI DOSYA DEGISTI: %s" % bozuk)
    print("  MUTANT FIILEN UYGULANDI: %d/%d (capasi bayat olan mutant OLCULMEMIS sayilir)"
          % (uygulanan, len(MUTANTLAR)))
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz),
                                                             len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d mutant BEYANINA UYDU (iddia sayisi %d, hepsinde "
          "SABIT) ✔" % (len(MUTANTLAR), len(MUTANTLAR), taban_iddia))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK,
                    help="modulu bu agactan oku (mutasyon kopyasi)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="cift yonlu mutasyon olcumu (elle; canli dosyaya DOKUNMAZ)")
    ap.add_argument("--katalog", default=None,
                    help="A ekseni katalogunu BASKA dosyadan oku (sentetik vaka olcumu; "
                         "varsayilan gercek urunler.json)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== UYUM KAPISI (kok: %s%s)"
          % (a.kok, " · katalog: %s" % a.katalog if a.katalog else ""))
    return kabul(a.kok, a.katalog)


if __name__ == "__main__":
    sys.exit(main())

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
  A KATALOG Gercek 16.874 kayit: bugun `uyum` dolu kayit YOK; kapi bu sayiyi OLCER ki
            ilk parti girdiginde regresyon gorunur olsun.

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
def kabul(kok):
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
    dogrula("S2 BUDAMA ARITMETIGI: (izinli + uretici + elenen) − mimar eki == oneri "
            "sayisi (%d) — elenen jeton sessizce geri sizamaz, ONERISIZ jeton yalnizca "
            "MIMAR EKI'nde ADIYLA kayitli olarak girebilir"
            % A.UYUM_MARKA_ONERI_SAYISI,
            len(yargilanan) == A.UYUM_MARKA_ONERI_SAYISI,
            "(%d + %d + %d) − %d = %d" % (len(izinli), len(uretici), len(elenen),
                                          len(tum_eki), len(yargilanan)))
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
    _mut = A.uyum_kanonik(_ozdes_fikstur[0])
    _mut[0]["marka"] = "BOZULDU"
    dogrula("V8 KANONIK OZDESLIK: kabul edilen %d kayitta `uyum_kanonik` ciktisi katalog "
            "degeriyle BIREBIR AYNI ve DERIN KOPYA (cagiran ciktiyi bozarsa katalog "
            "bozulmaz) — altkategori'de olculen sessiz ayrismanin tekrari yok"
            % len(_ozdes_fikstur),
            not _ayrisan and not _paylasan
            and _ozdes_fikstur[0]["uyum"][0]["marka"] == "Ford",
            "ayrisan=%s paylasilan-referans=%s" % (_ayrisan[:2], _paylasan[:2]))

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
    with open(os.path.join(GERCEK_KOK, "urunler.json"), encoding="utf-8") as f:
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
    dogrula("A2 K5: `uyum` dolu her kayitta `marka` TURETILMIS degere esit "
            "(uyumlu kayit: %d)" % uyumlu, not ihlal)
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

    ornek, ele, ayrisan_gercek, red_gercek = 0, 0, [], []
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
            "(arama metni backfill gunu kaymaz — parite riski 0); %d kayit KANONIK OLMAYAN "
            "marka yazimi tasidigi icin ELE ayrildi" % (ornek, ele),
            ornek > 0 and not ayrisan_gercek and not red_gercek,
            "ornek=%d ele=%d ayrisan=%s red=%s"
            % (ornek, ele, ayrisan_gercek[:3], red_gercek[:3]))

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

    print("\nSONUC: %s — gecen %d · kalan %d"
          % ("YESIL" if kalan[0] == 0 else "KIRMIZI", gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


# ── CIFT YONLU MUTASYON ─────────────────────────────────────────────────────────────
# KIRMIZI beklenen = oldurucu mutant (kapi yakalamali) · YESIL beklenen = ILGISIZ
# degisiklik (kapinin gereginden genis olmadiginin kaniti). Capa kayarsa tur KIRMIZI
# yanar ve mutant SAYILMAZ — "capa bulunamadi" ASLA yesil degildir.
MUTANTLAR = [
    ("M1", "arama.py",
     '    if deger not in UYUM_MARKA_IZINLI:\n        return ""\n', "", "KIRMIZI",
     "V1: kapali kume kontrolu kalkar -> her marka kabul, sahte marka sayfasi acilir"),
    ("M2", "arama.py",
     "    if deger not in UYUM_MARKA_IZINLI:",
     "    if deger.strip() not in UYUM_MARKA_IZINLI:", "KIRMIZI",
     "V2: strip() uyelik testinin ICINE girer -> ' Ford' kabul (bu depoda `altkategori`de "
     "GERCEKTEN yasanmis hata: katalog ham, D1 kirpilmis)"),
    ("M3", "arama.py",
     re.compile(r"    turetilen = marka_uyumdan_turet\(u\)\n.*?"
                r"TURETILIR\" % \(mevcut, turetilen\)\)\n", re.S), "", "KIRMIZI",
     "V6: K5 ikiz kontrolu kalkar -> `marka` ile `uyum` sessizce ayrisir"),
    ("M4", "arama.py",
     '    m = norm(m)\n    m = "".join(c for c in unicodedata.normalize("NFKD", m)\n'
     "                if not unicodedata.combining(c))\n"
     '    return _MODEL_AYIRAC_RE.sub("", m)\n', "    return m\n", "KIRMIZI",
     "V7: model normalizasyonu KIMLIK fonksiyonu olur -> `F-150`/`F150` iki ayri sayfa"),
    ("M5", "arama.py",
     "    if uyum_sebebi(u) is not None:\n        return []\n", "", "KIRMIZI",
     "V9/V10: kanonik FAIL-OPEN olur -> gecersiz/enjekte deger D1'e HAM gider"),
    ("M6", "arama.py",
     '    if son < bas:\n        return "yil araligi TERS: [%d, %d]" % (bas, son)\n', "",
     "KIRMIZI", "V5: `yil` aralik kontrolu kalkar -> [2020, 2003] gecer"),
    ("M7", "arama.py",
     "        for deger in jetonlar:\n"
     "            if deger and deger not in turetilen:\n"
     "                turetilen.append(deger)\n",
     "        for aday in jetonlar:\n"
     "            if aday and aday not in turetilen:\n"
     "                turetilen.append(aday)\n", "YESIL",
     "KONTROL MUTANTI: davranisi DEGISTIRMEYEN yeniden adlandirma — kapi bicimi degil "
     "DAVRANISI olcuyor mu?"),
    # EK MUTANT (spec disi, olculen kusurdan dogdu): V10 bu turda GERCEKTEN kirmizi yandi
    # ('../../etc/passwd' karakter beyaz listesinden gecmisti). Kusuru kapatan kural da
    # mutasyonla olculmeli, yoksa yarin sessizce geri alinabilir.
    ("M8", "arama.py",
     re.compile(r"    if d\[0\] in UYUM_SERBEST_AYIRAC or d\[-1\] in UYUM_SERBEST_AYIRAC:"
                r"\n.*?% \(ad, onceki \+ simdiki\)\)\n", re.S), "", "KIRMIZI",
     "V10: ayirac KONUM kurali kalkar -> '../../etc/passwd' model/oem alanindan GECER"),
    # M9 — mimar maddesi (b): turetme ESKI kurala (yalniz marka) donerse KIRMIZI.
    # Bu mutant tam olarak "sessiz arama kaybi" senaryosudur: kod calisir, kapi eski
    # haliyle yesil yanardi, ama backfill gunu `Focus` haystack'ten duserdi.
    ("M9", "arama.py",
     '        jetonlar = (uyum_marka_kanonik(oge.get("marka")),\n'
     '                    model_metin(oge.get("model")))\n',
     '        jetonlar = (uyum_marka_kanonik(oge.get("marka")),)\n', "KIRMIZI",
     "V6/V12/A5: turetme YALNIZ markaya doner -> model jetonlari `marka`dan ve dolayisiyla "
     "haystack'ten SESSIZCE duser"),
    # M10 — turetme sirasi ters cevrilir (model once). Davranis DEGISIR: bugunku
    # ["marka","model"] dizilimi bozulur, ama arama metni ayni kalir -> yalniz sira
    # ekseni kirmizi yanmali (ayrismanin SIRA bileseni de olculuyor mu?).
    ("M10", "arama.py",
     '        jetonlar = (uyum_marka_kanonik(oge.get("marka")),\n'
     '                    model_metin(oge.get("model")))\n',
     '        jetonlar = (model_metin(oge.get("model")),\n'
     '                    uyum_marka_kanonik(oge.get("marka")))\n', "KIRMIZI",
     "V12/A5: turetme SIRASI ters (model once) -> `marka` dizilimi bugunkunden kayar"),
    # M11 — marka/model sinirindaki ikiz kapisi kalkar. `Kia` kumedeyken `KIA` model
    # olarak gecer ve ayni gercek IKI ayri sayfa uretir.
    ("M11", "arama.py",
     re.compile(r"    for ad in \(\"model\", \"motor\"\):\n"
                r"        sebep = marka_varyanti_sebebi\(ad, oge\.get\(ad\)\)\n"
                r"        if sebep:\n            return sebep\n"), "", "KIRMIZI",
     "V16: marka/model sinirindaki ikiz kapisi kalkar -> `KIA` model olarak GECER"),
]

KOPYALANAN = ["arama.py"]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _kopya_kur():
    tmp = tempfile.mkdtemp(prefix="pruvo-uyum-mut-")
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in KOPYALANAN:
        shutil.copy2(os.path.join(GERCEK_KOK, "tools", ad), os.path.join(tmp, "tools", ad))
    os.symlink(os.path.join(GERCEK_KOK, "urunler.json"), os.path.join(tmp, "urunler.json"))
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


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    once = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    basarisiz = []

    # M00 MUTASYONSUZ KONTROL (ZORUNLU ON-KOSUL): kopya agaci mutasyonsuz halde YESIL
    # vermezse harness BOZUKTUR ve butun "KIRMIZI" sonuclari YALANCIDIR (mutant degil,
    # cokme olculur). Olculmus vaka: eksik bir kopya dosyasi 14 mutantin 14'unu ayni
    # ImportError ile "olduruldu" gosterebilir.
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    kontrol_ok = p0.returncode == 0
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s (harness saglam mi)"
          % ("OK  " if kontrol_ok else "HATA", "YESIL" if kontrol_ok else "KIRMIZI"))
    if not kontrol_ok:
        print("     " + (p0.stderr or p0.stdout).strip().splitlines()[-1][:300])
        shutil.rmtree(tmp0, ignore_errors=True)
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk, mutant sonuclari YALANCI.")
        return 1
    shutil.rmtree(tmp0, ignore_errors=True)

    uygulanan = 0
    for ad, dosya, eski, yeni, beklenen, aciklama in MUTANTLAR:
        tmp = _kopya_kur()
        hedef = os.path.join(tmp, "tools", dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        mutant, sayi = _mutasyon_uygula(metin, eski, yeni)
        if mutant is None:
            basarisiz.append("%s CAPA BAYAT (%d kez eslesti, 1 olmali) %s: %s"
                             % (ad, sayi, dosya, _capa_metni(eski)[:70]))
            print("  HATA %s [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI | %s"
                  % (ad, beklenen, dosya, sayi, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        if mutant == metin:
            basarisiz.append("%s MUTANT UYGULANMADI (metin DEGISMEDI) %s" % (ad, dosya))
            print("  HATA %s [%s] %s -> MUTANT UYGULANMADI | EKSEN OLCULMEDI | %s"
                  % (ad, beklenen, dosya, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(mutant)
        uygulanan += 1
        p = _kok_kostur(tmp)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        isaret = "OK  " if goruldu == beklenen else "HATA"
        if goruldu != beklenen:
            basarisiz.append("%s %s: beklenen %s, goruldu %s" % (ad, dosya, beklenen,
                                                                 goruldu))
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        # 🔴 KIRMIZI YETMEZ, ADLI IDDIA SART: mutant COKEREK de rc!=0 verebilir (import/
        # sozdizimi hatasi). O "olduruldu" DEGIL "olculemedi"dir.
        if goruldu == "KIRMIZI" and beklenen == "KIRMIZI" and not oldu:
            basarisiz.append("%s %s: KIRMIZI ama HICBIR iddia KALDI demedi — mutant "
                             "oldurulmedi, kapi COKTU (yalanci kanit)" % (ad, dosya))
        print("  %s %s [%s] %s -> %s (%d iddia kirmizi) | %s"
              % (isaret, ad, beklenen, dosya, goruldu, len(oldu), aciklama))
        for s in oldu[:3]:
            print("        " + s[:150])
        shutil.rmtree(tmp, ignore_errors=True)

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
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK,
                    help="modulu bu agactan oku (mutasyon kopyasi)")
    ap.add_argument("--mutasyon", action="store_true",
                    help="cift yonlu mutasyon olcumu (elle; canli dosyaya DOKUNMAZ)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== UYUM KAPISI (kok: %s)" % a.kok)
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())

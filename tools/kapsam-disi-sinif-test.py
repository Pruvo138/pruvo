#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kapsam-disi-sinif-test.py — kapsam-disi-sinif-kapisi.py KABUL + MUTANT bataryasi.

KABUL SORUSU (her kol icin): "bu satiri silsem hangi iddia kirmizi yanar?"
Her mutant, rc'nin degismesiyle YETINMEZ; hedef kolun ADINI ciktida ARAR
([[isci-yesil-tablo-ic-olcumu-bosaltir]], K182). rc borusuz okunur
([[boru-rc-isci-olcumunu-yalanlar]]).

IZOLASYON: her kol, gecici bir dizinde kurulan SENTETIK EV'de kosar; canli govde
HIC yamanmaz ([[mutant-canli-govdede-yasamaz]]). Kapi alt surec olarak, kendi
kopyasindan, PYTHONDONTWRITEBYTECODE=1 ile calistirilir.
🔴 YIKICI YUK YOK: silinen tek sey tempfile.mkdtemp()'in kendi urettigi dizindir
ve silmeden ONCE gettempdir() altinda oldugu DOGRULANIR; hicbir gercek ev yolu
silme menzilinde degildir (BaBa FILO DERSI, 4 Eyl).

K0 KANARYASI SART: mutasyonsuz sentetik ev YESIL olmalidir. Olmazsa oncedeki bir
fail-closed kol hedef kolu MASKELIYOR demektir ve batarya olcum degil, gurultudur
([[fail-closed-kol-arkasindaki-kolu-maskeler]]).

FIKSTUR SINIRI (acikca beyan): turetme kaynagi GERCEK `tools/sayfalar.py`dir
(kopyalanir, kirpilmaz) — yani sinifin tanimi gercek metinden okunur. Katalog ise
INDIRGENMIS fikstur: gercek `urunler.json`dan yalniz bu eksene giren kayitlar
(muafiyet sicili + taban kuyrugu + BaBa'nin 7 Eyl'de gizledigi 5 kayit) cekilir.
Kapinin O(n) taramasi kayit sayisindan bagimsizdir; indirgeme 31 MB'lik dosyayi
her kol icin kopyalamamak icindir, iddiayi daraltmak icin degil.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_BU = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(_BU)
KAPI_ADI = "kapsam-disi-sinif-kapisi.py"
TABAN_ADI = "kapsam-disi-taban.json"

# BaBa 7 Eyl KARAR 1 ile gizlenen 5 kayit — YER GERCEGI (ground truth) replay'i
# bunlar uzerinden yapilir: gizlilik kaldirilinca kapi TAM BU 5'i yakalamalidir.
KARAR1_BESLI = [
    "evinrude-johnson-1979-6hp-su-impelleri",
    "british-seagull-su-pompasi-impelleri",
    "90mm-su-jeti-pompa-pervanesi",
    "dis-motor-impeller-pompasi-rotoru",
    "trolling-motor-impelleri",
]

_gecti, _kaldi = [], []


def _bildir(ad, ok, ayrinti=""):
    (_gecti if ok else _kaldi).append(ad)
    print("%s %s%s" % ("  ok  " if ok else " KALDI", ad,
                       ("  — " + ayrinti) if ayrinti else ""))


def _kapi_kaynagi():
    with open(os.path.join(_BU, KAPI_ADI), encoding="utf-8") as f:
        return f.read()


def _sentetik_ev(kok, kapi_src=None, taban=None, urunler=None, sayfalar_src=None):
    """Gecici dizinde tam calisir bir ev kurar; verilen parcalar MUTASYONDUR."""
    os.makedirs(os.path.join(kok, "tools"), exist_ok=True)
    with open(os.path.join(kok, "tools", KAPI_ADI), "w", encoding="utf-8") as f:
        f.write(kapi_src if kapi_src is not None else _kapi_kaynagi())
    if sayfalar_src is None:
        shutil.copyfile(os.path.join(_BU, "sayfalar.py"),
                        os.path.join(kok, "tools", "sayfalar.py"))
    else:
        with open(os.path.join(kok, "tools", "sayfalar.py"), "w",
                  encoding="utf-8") as f:
            f.write(sayfalar_src)
    with open(os.path.join(kok, "tools", TABAN_ADI), "w", encoding="utf-8") as f:
        json.dump(taban if taban is not None else _gercek_taban(), f,
                  ensure_ascii=False, indent=2)
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(urunler if urunler is not None else _fikstur_katalog(), f,
                  ensure_ascii=False)
    return kok


def _gercek_taban():
    with open(os.path.join(_BU, TABAN_ADI), encoding="utf-8") as f:
        return json.load(f)


_KATALOG_ONBELLEK = {}


def _fikstur_katalog():
    """Gercek katalogtan bu eksenin kayitlarini ceker (indirgenmis fikstur)."""
    if "v" in _KATALOG_ONBELLEK:
        return [dict(u) for u in _KATALOG_ONBELLEK["v"]]
    kapi = _kapi_yukle()
    istenen = set(kapi.MUAFIYET_SICILI) | set(_gercek_taban()["kuyruk"]) \
        | set(KARAR1_BESLI)
    with open(os.path.join(EV, "urunler.json"), encoding="utf-8") as f:
        tum = json.load(f)
    secilen = [u for u in tum if u.get("id") in istenen]
    _KATALOG_ONBELLEK["v"] = secilen
    return [dict(u) for u in secilen]


_MODUL_ONBELLEK = {}


def _kapi_yukle():
    """Canli kapiyi modul olarak yukler (yalniz saf fonksiyon/sabit okumak icin)."""
    if "m" in _MODUL_ONBELLEK:
        return _MODUL_ONBELLEK["m"]
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "kapsam_disi_sinif_kapisi_test_kopya", os.path.join(_BU, KAPI_ADI))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _MODUL_ONBELLEK["m"] = m
    return m


def _kosu(kok):
    """(rc, cikti) — kapiyi sentetik evde alt surec olarak kosar. Boru YOK."""
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run(
        [sys.executable, os.path.join(kok, "tools", KAPI_ADI), "--ev", kok],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ortam)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def _gecici_ev():
    d = tempfile.mkdtemp(prefix="kapsam-disi-sinif-mutant-")
    # 🔴 EMNIYET: silme menzili yalnizca gettempdir() altidir.
    assert os.path.realpath(d).startswith(os.path.realpath(tempfile.gettempdir())), d
    return d


def _temizle(d):
    if os.path.realpath(d).startswith(os.path.realpath(tempfile.gettempdir())):
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
def t_k0_kanaryasi():
    """K0 — mutasyonsuz sentetik ev YESIL olmali (maskeleme yok)."""
    d = _gecici_ev()
    try:
        _sentetik_ev(d)
        rc, cikti = _kosu(d)
        _bildir("K0 kanaryasi: mutasyonsuz sentetik ev YESIL",
                rc == 0 and "TEMIZ" in cikti and "YENI 0" in cikti,
                "rc=%d" % rc)
        # turetmenin gercekten metinden ciktigini ADIYLA olc (bos/kisa devre degil)
        _bildir("K0: turetme metinden geldi (alias 'impeller' + sivi 'sintine')",
                "impeller" in cikti and "sintine" in cikti)
    finally:
        _temizle(d)


def t_m1_gorunur_impeller_kaydi():
    """M1 — GORUNUR bir impeller kaydi eklenirse kapi KIRMIZI yanmali (YON 1)."""
    d = _gecici_ev()
    try:
        kat = _fikstur_katalog()
        kat.insert(0, {
            "id": "mutant-gorunur-sintine-pompasi-impelleri",
            "baslik": "Sintine Pompası İmpelleri (mutant)",
            "aciklama": "Sintine pompasının su çarkı; sıvı taşıyan pompa impelleri.",
            "kategori": "Marin", "fiyat": "500 TL", "gorseller": [],
        })
        _sentetik_ev(d, urunler=kat)
        rc, cikti = _kosu(d)
        _bildir("M1: gorunur impeller kaydi -> rc=1 (YON 1 celiski)", rc == 1,
                "rc=%d" % rc)
        # HEDEF KOLU OLDURDUGUNU AYRICA KANITLA: kolun ADI + kaydin ID'si ciktida
        _bildir("M1: hedef kol ADIYLA yandi ('YON 1' + mutant id)",
                "YON 1" in cikti
                and "mutant-gorunur-sintine-pompasi-impelleri" in cikti)
        _bildir("M1: sessiz yesile DUSMEDI ('TEMIZ' basmadi)", "TEMIZ" not in cikti)
    finally:
        _temizle(d)


def t_m2_durust_sinir_metni_okunamaz():
    """M2 — durust-sinir maddesi okunamazsa birebir OLCULEMEDI, YESIL DEGIL."""
    d = _gecici_ev()
    try:
        with open(os.path.join(_BU, "sayfalar.py"), encoding="utf-8") as f:
            src = f.read()
        kapi = _kapi_yukle()
        t = kapi.turet(os.path.join(_BU, "sayfalar.py"))
        assert t is not None, "on-kosul: canli turetme calisiyor olmali"
        # Maddeyi bozan EN KUCUK mutasyon: kapsam-disi kolunun capasini dusur.
        bozuk = src.replace("kapsamımızın dışındadır", "kapsam icinde degerlendirilir")
        assert bozuk != src, "mutasyon uygulanamadi (capa metni bulunamadi)"
        _sentetik_ev(d, sayfalar_src=bozuk)
        rc, cikti = _kosu(d)
        _bildir("M2: durust-sinir maddesi cozulemez -> rc=3", rc == 3, "rc=%d" % rc)
        _bildir("M2: birebir 'OLCULEMEDI' basildi", "OLCULEMEDI" in cikti)
        _bildir("M2: sessiz yesile DUSMEDI ('TEMIZ' basmadi)", "TEMIZ" not in cikti)
        _bildir("M2: 'neyi olcmek kapatir' yazildi",
                "NEYI OLCMEK KAPATIR" in cikti)
    finally:
        _temizle(d)


def t_m3_taban_kuyrugu_buyutulemez():
    """M3 — NON-GROWTH: taban kuyruguna id eklenerek kapi susturulamaz (YON 2)."""
    d = _gecici_ev()
    try:
        kat = _fikstur_katalog()
        kat.insert(0, {
            "id": "mutant-kuyruga-kacirilan-impeller",
            "baslik": "Deniz Suyu Pompası İmpelleri (mutant)",
            "aciklama": "Sıvı taşıyan pompa çarkı.",
            "kategori": "Marin", "fiyat": "500 TL", "gorseller": [],
        })
        taban = _gercek_taban()
        taban["kuyruk"] = list(taban["kuyruk"]) + ["mutant-kuyruga-kacirilan-impeller"]
        _sentetik_ev(d, urunler=kat, taban=taban)
        rc, cikti = _kosu(d)
        _bildir("M3: kuyruk tavani asildi -> rc=2 (YON 2)", rc == 2, "rc=%d" % rc)
        _bildir("M3: hedef kol ADIYLA yandi ('NON-GROWTH' + 'taban kuyrugu')",
                "NON-GROWTH" in cikti and "taban kuyrugu" in cikti)
        _bildir("M3: sessiz yesile DUSMEDI", "TEMIZ" not in cikti)
    finally:
        _temizle(d)


def t_m4_sicil_dolgusu():
    """M4 — muafiyet siciline SINIF DISI (dolgu) id yazilamaz (YON 2)."""
    d = _gecici_ev()
    try:
        src = _kapi_kaynagi()
        capa = 'SICIL_TAVANI = 4'
        assert capa in src, "mutasyon capasi bulunamadi"
        bozuk = src.replace(
            'MUAFIYET_SICILI = {',
            'MUAFIYET_SICILI = {\n    "mutant-dolgu-hicbir-yerde-yok": "dolgu",',
            1).replace(capa, 'SICIL_TAVANI = 5', 1)
        assert bozuk != src, "mutasyon uygulanamadi"
        _sentetik_ev(d, kapi_src=bozuk)
        rc, cikti = _kosu(d)
        _bildir("M4: sinif disi sicil kaydi -> rc=2 (YON 2)", rc == 2, "rc=%d" % rc)
        _bildir("M4: hedef kol ADIYLA yandi ('OLU/DOLGU' + dolgu id)",
                "OLU/DOLGU" in cikti and "mutant-dolgu-hicbir-yerde-yok" in cikti)
    finally:
        _temizle(d)


def t_m5_yer_gercegi_replay():
    """M5 — ONARIM ONCESI hal: KARAR 1'in 5 kaydi gorunurken kapi TAM 5'i yakalar.

    BaBa'nin civiledigi kabul kolunun ta kendisi: sinif kolu, tekil duzeltmeden
    ONCEKI gercegi bagimsiz olarak yeniden uretebiliyor mu?
    """
    d = _gecici_ev()
    try:
        kat = _fikstur_katalog()
        for u in kat:
            if u.get("id") in KARAR1_BESLI:
                u.pop("gizli", None)          # onarimi GERI AL (yalniz fiksturde)
        _sentetik_ev(d, urunler=kat)
        rc, cikti = _kosu(d)
        _bildir("M5: onarim-oncesi hal -> rc=1", rc == 1, "rc=%d" % rc)
        eksik = [i for i in KARAR1_BESLI if i not in cikti]
        _bildir("M5: KARAR 1'in 5 kaydinin 5'i de ADIYLA yakalandi",
                not eksik, "eksik: %s" % (eksik or "yok"))
        _bildir("M5: tam olarak 5 YENI kayit (fazla/eksik yok)",
                "YENI GORUNUR kayit" in cikti and "): 5 YENI" in cikti)
    finally:
        _temizle(d)


def t_m6_alias_ampuller_regresyonu():
    """M6 — alias kalibi 'ampuller' YAKALAMAMALI, 'empeller' YAKALAMALI.

    OLCULMUS REGRESYON: kalip once TUM seslileri sinifa aldigi icin Turkce
    'ampuller' sozcugunu yakalamis ve 40'tan fazla far/ampul kaydini yanlis
    pozitif kirmiziya yakmisti. Bu kol o hatanin geri gelmesini olcer.
    """
    kapi = _kapi_yukle()
    t = kapi.turet(os.path.join(_BU, "sayfalar.py"))
    if t is None or t.bos_mu():
        _bildir("M6: turetme calisiyor (on-kosul)", False, "OLCULEMEDI")
        return
    var_amp, _ = t.sinifta_mi("H7 LED Far Ampulü Adaptörü — ampuller icin")
    var_emp, _ = t.sinifta_mi("Volvo Penta empeller yuvasi")
    var_imp, _ = t.sinifta_mi("Su pompasi impelleri")
    _bildir("M6: 'ampuller' sinifa GIRMEZ (yanlis pozitif regresyonu)", not var_amp)
    _bildir("M6: 'empeller' sinifa GIRER (yazim varyanti)", var_emp)
    _bildir("M6: 'impeller' sinifa GIRER", var_imp)


def t_m7_islev_sozcuklerinde_parca_adi_yok():
    """M7 — ISLEV_SOZCUKLERI'ne bir PARCA adi yazmak kapiyi korlestirirdi."""
    kapi = _kapi_yukle()
    t = kapi.turet(os.path.join(_BU, "sayfalar.py"))
    if t is None or t.bos_mu():
        _bildir("M7: turetme calisiyor (on-kosul)", False, "OLCULEMEDI")
        return
    carpisma = [p for p in t.parca if p in kapi.ISLEV_SOZCUKLERI]
    _bildir("M7: islev sozcukleri hicbir PARCA jetonunu yutmuyor",
            not carpisma, "carpisan: %s" % (carpisma or "yok"))
    _bildir("M7: turetme BOS degil (alias/parca/sivi hepsi dolu)",
            bool(t.alias) and bool(t.parca) and bool(t.sivi),
            "alias=%d parca=%d sivi=%d" % (len(t.alias), len(t.parca), len(t.sivi)))


def t_m8_taban_dosyasi_bozuksa():
    """M8 — taban dosyasi okunamazsa OLCULEMEDI, sessiz yesil DEGIL."""
    d = _gecici_ev()
    try:
        _sentetik_ev(d)
        with open(os.path.join(d, "tools", TABAN_ADI), "w", encoding="utf-8") as f:
            f.write("{ bu gecerli json degil")
        rc, cikti = _kosu(d)
        _bildir("M8: bozuk taban dosyasi -> rc=3", rc == 3, "rc=%d" % rc)
        _bildir("M8: birebir 'OLCULEMEDI' basildi + 'TEMIZ' basmadi",
                "OLCULEMEDI" in cikti and "TEMIZ" not in cikti)
    finally:
        _temizle(d)


def t_canli_ev_yesil():
    """CANLI ev bugun YESIL olmali (kapi main'de kimsenin yayinini durdurmuyor)."""
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, os.path.join(_BU, KAPI_ADI)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ortam)
    cikti = p.stdout.decode("utf-8", "replace")
    _bildir("CANLI: gercek ev rc=0 (YENI celiski 0)",
            p.returncode == 0 and "YENI 0" in cikti, "rc=%d" % p.returncode)
    _bildir("CANLI: KARAR 1'in 5 kaydinin hicbiri artik GORUNUR degil",
            not any(i in cikti for i in KARAR1_BESLI))


def main():
    print("=" * 74)
    print("KAPSAM-DISI SINIF KAPISI — kabul + mutant bataryasi")
    print("=" * 74)
    for fn in (t_k0_kanaryasi, t_m1_gorunur_impeller_kaydi,
               t_m2_durust_sinir_metni_okunamaz, t_m3_taban_kuyrugu_buyutulemez,
               t_m4_sicil_dolgusu, t_m5_yer_gercegi_replay,
               t_m6_alias_ampuller_regresyonu,
               t_m7_islev_sozcuklerinde_parca_adi_yok,
               t_m8_taban_dosyasi_bozuksa, t_canli_ev_yesil):
        print("")
        print("--- %s" % (fn.__doc__ or fn.__name__).splitlines()[0])
        fn()
    print("")
    print("=" * 74)
    print("SONUC: %d iddia GECTI, %d KALDI" % (len(_gecti), len(_kaldi)))
    for k in _kaldi:
        print("  KALDI: %s" % k)
    return 1 if _kaldi else 0


if __name__ == "__main__":
    sys.exit(main())

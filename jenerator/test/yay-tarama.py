#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAY AILESI DETERMINISTIK HACIM TARAMASI (fiyat ekseni).

NEDEN VAR: `dogrula.py` her kosumda RASTGELE tohum kullanir (dogrula.py:500).
Yesil bir kosum "bu tohumda kirmizi yok" demektir, "aile temiz" DEMEZ — yay
ailesinin ucgen kolundaki %3,96'lik sapma tam bu yuzden haftalarca gorunmedi
(olculdu 2026-08-03; tekrar: `dogrula.py yay --set 10 --seed 280903`, set9).
Bu surucu RASTGELE SET KULLANMAZ: semadan turetilen KURAL TABANLI izgarayi
bastan sona tarar, dal (secim parametreleri) basina EN KOTU sapmayi basar.

YER-GERCEGI TEK KAYNAKTAN: OpenSCAD render hacmi `dogrula.py`nin kendi
fonksiyonlariyla olculur (scad_hacim/js_hacimler/openscad_yolu). Ikinci bir
olcum yolu YAZILMAZ — ikiz tanim sessizce ayrisir.

🔴 OLCUM ARACI KONUSUNU DEGISTIREMEZ (3 Agu 2026, curutucu bulgusu D1): eski
surum olcumden ONCE `birlestir.py` kosturuyordu; bu, fiyat yolunun okudugu
`jenerator/hacim.js`te YASAYAN bir ayrismayi OLCMUYOR, SESSIZCE SILIYORDU
(hacim.js'e +%5 mutasyon konup tarama kosuldugunda hukum YESIL kaldi ve mutasyon
diskten kayboldu). Bugun: govde uretilir AMA gecici dizine; diskteki hacim.js
ile AYRISIYORSA surucu OLCMEDEN DURUR (cikis 4) ve HICBIR SEY YAZMAZ.

IZGARA IKI KATMANLI (3 Agu 2026, curutucu bulgusu D4):
  (K) KAPSAM izgarasi — semadan turetilen tam kartezyen (tum enum degerleri ×
      her sayisal eksenin min/orta/max'i). MANTIKSAL nokta sayisi budur ve JS
      tarafi bu noktalarin HEPSINDE hesaplanir.
  (I) INCE izgara — OLCULEREK canli bulunan eksenler sema cozunurlugune kadar
      sikilastirilir; butce (--butce) bunlara harcanir.
RENDER PAYLASIMI: bir eksenin o dalda render'i DEGISTIRMEDIGI OLCULMUSSE
(prob: min/orta/max ya da enumun tum degerleri), yalniz o eksende farklilasan
mantiksal noktalar AYNI renderi paylasir. Bu depoda olculdu: 810 mantiksal
kapsam noktasi 42 BENZERSIZ geometriye iniyor (dalga kolunda dis_cap/
serbest_boy/tel_capi OLU, spiral kolunda dalga_formu/dalga_boyu OLU).
FAIL-CLOSED: olculemeyen eksen OLU SAYILMAZ, paylasima girmez.
JS tarafi PAYLASILMAZ — hacim.js'in OLU bir eksene bagimli olmasi KIRMIZI yakar.

RENDER ONBELLEGI: yer-gercegi AYNI girdide AYNIDIR; anahtar
`sha256(uretim modeli) | OpenSCAD surumu | tam -D bayrak listesi`dir — model ya
da OpenSCAD degisirse onbellek KENDILIGINDEN gecersizlesir. Her renderdan sonra
atomik yazilir (kosum yarida kesilse kaldigi yerden devam eder), repo DISINDADIR.
OLCULEN MALIYET (3 Agu 2026, `--paralel 8`, BOS onbellek): kapsam taramasinin
tamami 110 render / 65,5 sn = 0,60 sn/render; kapsam+ince tam kosum 530 benzersiz
geometri ≈ 5-6 dk. ("810 render ≈ 50 dk" beyani YANLISTI: ne render sayisi ne de
birim sure oyleydi.)

Kullanim:
  python3 yay-tarama.py                     # kapsam + ince izgara
  python3 yay-tarama.py --butce 400 --paralel 8
  python3 yay-tarama.py --ince-yok          # yalniz kapsam izgarasi
  python3 yay-tarama.py --yogunluk-eksen dalga_boyu=81
  python3 yay-tarama.py --onbellek yok
  python3 yay-tarama.py --kendini-test      # OpenSCAD/node/ag GEREKMEZ

Cikis kodu: 0 = en kotu <= sinir · 1 = sinir asildi · 3 = OLCULEMEDI (yesil
sayilmaz) · 4 = hacim.js aile kaynaklariyla AYRISIK (olcum YAPILMADI).
"""
import argparse
import contextlib
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TEST_DIR)
import dogrula  # noqa: E402  (yer-gercegi yolu TEK KAYNAK)

VARSAYILAN_SINIR = 1.0          # mimar hukmu; kendini-test bunu CAPA olarak olcer
VARSAYILAN_BUTCE = 800          # ince izgaraya ayrilan benzersiz render tavani
OLCULEMEDI_KODU = 3
AYRISMA_KODU = 4
HACIM_JS = os.path.join(os.path.dirname(TEST_DIR), "hacim.js")


# ---- IZGARA (semadan turetilir) --------------------------------------------
def sayi_izgarasi(p, yogunluk):
    """min..max arasi `yogunluk` adet nokta; hepsi sema adim izgarasina oturur.
    min ve max DAIMA icerdedir (uc noktalar en kotu sapmanin tipik yeridir);
    yogunluk<2 kolunda ALT SINIR alinir (orta nokta degil — kendini-test I5d)."""
    alt = float(p["min"])
    ust = float(p["max"])
    adim = float(p.get("adim") or 1)
    n = int(math.floor((ust - alt) / adim + 0.5))
    if yogunluk < 2 or n <= 0:
        return [round(alt, 6)]
    degerler = []
    for k in range(yogunluk):
        oran = k / float(yogunluk - 1)
        basamak = int(math.floor(n * oran + 0.5))
        deger = round(alt + basamak * adim, 6)
        if deger not in degerler:
            degerler.append(deger)
    return sorted(degerler)


def sema_basamak_sayisi(p):
    """Semanin KENDI cozunurlugu: min..max arasi kac ayrik deger var."""
    adim = float(p.get("adim") or 1)
    return int(math.floor((float(p["max"]) - float(p["min"])) / adim + 0.5)) + 1


def secim_degerleri(p):
    return [x["deger"] if isinstance(x, dict) else x for x in p["secenekler"]]


def izgara_uret(sema, yogunluk, eksen_yogunluk=None):
    """Semadan KURAL TABANLI tam izgara (kartezyen carpim).

    `eksen_yogunluk` = {parametre_adi: yogunluk} — tek tek eksenleri
    sikilastirmak icin. Enum eksenleri HER ZAMAN tam taranir, kisilamaz."""
    eksen_yogunluk = eksen_yogunluk or {}
    eksenler = []
    for p in sema["parametreler"]:
        tip = p.get("tip", "sayi")
        if tip == "secim":
            degerler = secim_degerleri(p)
        elif tip == "sayi":
            degerler = sayi_izgarasi(p, eksen_yogunluk.get(p["ad"], yogunluk))
        elif tip == "metin":
            degerler = [p.get("varsayilan", "")]
        else:
            sys.exit("bilinmeyen parametre tipi: %s (%s)" % (tip, p["ad"]))
        eksenler.append((p["ad"], degerler))
    setler = [{}]
    for ad, degerler in eksenler:
        yeni = []
        for taban in setler:
            for d in degerler:
                kopya = dict(taban)
                kopya[ad] = d
                yeni.append(kopya)
        setler = yeni
    return setler


def dal_anahtari(sema, sset):
    """Dal = TUM secim parametrelerinin degeri (semadan turetilir, elle yazilmaz)."""
    return tuple(sset[p["ad"]] for p in sema["parametreler"]
                 if p.get("tip", "sayi") == "secim")


def taban_set(sema):
    """Prob tabani: her sayisal eksen min'de, her enum ilk degerinde."""
    s = {}
    for p in sema["parametreler"]:
        tip = p.get("tip", "sayi")
        if tip == "secim":
            s[p["ad"]] = secim_degerleri(p)[0]
        elif tip == "sayi":
            s[p["ad"]] = round(float(p["min"]), 6)
        else:
            s[p["ad"]] = p.get("varsayilan", "")
    return s


# ---- D1: OLCTUGU DOSYANIN UZERINE YAZMAMA — AYRISMA KAPISI -----------------
def uretilen_hacim_govdesi():
    """`birlestir.py`nin URETECEGI govde — CIKTI gecici dizine yonlendirilerek.
    Birlestirme mantigi TEKRAR YAZILMAZ (ikiz tanim uretmeyiz) ve diskteki
    hacim.js'e DOKUNULMAZ. -> (govde|None, tani|None)"""
    try:
        import birlestir
    except Exception as e:                                   # noqa: BLE001
        return None, "birlestir.py ice aktarilamadi: %s" % e
    tmpd = tempfile.mkdtemp(prefix="pruvo-yay-govde-")
    hedef = os.path.join(tmpd, "hacim.js")
    eski = birlestir.CIKTI
    birlestir.CIKTI = hedef
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            birlestir.main()
        with io.open(hedef, "r", encoding="utf-8") as f:
            return f.read(), None
    except SystemExit as e:
        return None, "birlestir.py DURDU (cikis %s)" % (e.code,)
    except Exception as e:                                   # noqa: BLE001
        return None, "birlestir.py hata: %s" % e
    finally:
        birlestir.CIKTI = eski
        shutil.rmtree(tmpd, ignore_errors=True)


def diskteki_hacim_govdesi(yol=HACIM_JS):
    if not os.path.isfile(yol):
        return None
    with io.open(yol, "r", encoding="utf-8") as f:
        return f.read()


def hacim_govdesi_hukmu(uretilen, diskteki):
    """SAF HUKUM: fiyat yolunun okudugu govde, aile kaynaklarindan URETILEN
    govdeyle ayni mi? FAIL-CLOSED — uretilemeyen/okunamayan govde YESIL DEGIL."""
    if uretilen is None:
        return False, "uretilecek govde ALINAMADI (birlestir.py)"
    if diskteki is None:
        return False, "hacim.js diskte YOK/okunamiyor — fiyat yolunun govdesi bilinmiyor"
    if uretilen != diskteki:
        return False, ("AYRISMA: hacim.js, aile kaynaklarindan uretilen govdeyle AYNI "
                       "DEGIL (%d bayt disk / %d bayt uretilen). Olcum YAPILMADI — bir "
                       "olcum araci konusunu DEGISTIREMEZ. Once ayrismanin sebebini "
                       "bulun (elle duzenlenmis hacim.js? bayat kopya?), sonra "
                       "birlestir.py kosup taramayi tekrarlayin."
                       % (len(diskteki), len(uretilen)))
    return True, "hacim.js aile kaynaklariyla OZDES (%d bayt)" % len(uretilen)


# ---- D4: OLU EKSEN OLCUMU + RENDER PAYLASIMI -------------------------------
def esit_hacim(a, b, tolerans=1e-9):
    if a is None or b is None or not a:
        return False
    return abs(a - b) / abs(a) <= tolerans


def eksen_hukmu(degerler):
    """degerler: bir eksenin TUM prob noktalarindaki hacimler [hacim|None].
    -> 'OLU' | 'CANLI' | 'OLCULEMEDI'. FAIL-CLOSED: olculemeyen eksen OLU
    SAYILMAZ (render paylasimina girmez, CANLI gibi islenir)."""
    if len(degerler) < 2:
        return "OLCULEMEDI"
    if any(d is None or not d for d in degerler):
        return "OLCULEMEDI"
    ilk = degerler[0]
    return "OLU" if all(esit_hacim(ilk, d) for d in degerler[1:]) else "CANLI"


def render_anahtari_seti(sset, olu_eksenler, taban):
    """Render PAYLASIM seti: OLU olctugumuz eksenler taban degerine cekilir.
    Mantiksal nokta DEGISMEZ; yalniz hangi renderin paylasildigi degisir."""
    kopya = dict(sset)
    for ad in olu_eksenler:
        kopya[ad] = taban[ad]
    return kopya


def ince_yogunluk(canli_sayisi, butce_payi):
    """k canli eksene butce_payi noktalik butce -> eksen basina yogunluk."""
    if canli_sayisi <= 0 or butce_payi < 2:
        return 1
    return max(2, int(math.floor(butce_payi ** (1.0 / canli_sayisi))))


# ---- HUKUM (saf fonksiyon) --------------------------------------------------
def ozet(sonuclar, sinir):
    """sonuclar: [(dal, sset, js, ref|None)] -> (tablo, en_kotu|None, olculemedi, cikis).

    FAIL-CLOSED: olculemeyen tek nokta bile YESIL SAYILMAZ; hic olcum yoksa da
    yesil DEGILDIR (sifir olculen set = yesil, bu depoda yasanmis bir delik)."""
    dallar = {}
    olculemedi = []
    for dal, sset, js, ref in sonuclar:
        kayit = dallar.setdefault(dal, {"en_kotu": None, "set": None, "adet": 0,
                                        "olculemedi": 0})
        if ref is None or not ref:
            kayit["olculemedi"] += 1
            olculemedi.append((dal, sset))
            continue
        sapma = abs(js - ref) / ref * 100.0
        kayit["adet"] += 1
        if kayit["en_kotu"] is None or sapma > kayit["en_kotu"]:
            kayit["en_kotu"] = sapma
            kayit["set"] = (sset, js, ref)
    tablo = []
    en_kotu = None
    for dal in sorted(dallar, key=lambda d: tuple(str(x) for x in d)):
        k = dallar[dal]
        tablo.append((dal, k["en_kotu"], k["set"], k["adet"], k["olculemedi"]))
        if k["en_kotu"] is not None and (en_kotu is None or k["en_kotu"] > en_kotu):
            en_kotu = k["en_kotu"]
    if olculemedi or en_kotu is None:
        cikis = OLCULEMEDI_KODU
    elif en_kotu > sinir:
        cikis = 1
    else:
        cikis = 0
    return tablo, en_kotu, olculemedi, cikis


def tabloyu_bas(tablo, en_kotu, olculemedi, sinir, cikis):
    print("\n%-28s %10s %8s %12s  %s" % ("DAL", "EN KOTU %", "NOKTA", "OLCULEMEDI",
                                         "EN KOTU SET"))
    for dal, ek, kayit, adet, olcx in tablo:
        ad = "/".join(str(x) for x in dal)
        if ek is None:
            print("%-28s %10s %8d %12d  -" % (ad, "OLCULEMEDI", adet, olcx))
            continue
        sset, js, ref = kayit
        detay = ", ".join("%s=%s" % (k, v) for k, v in sorted(sset.items())
                          if k not in dal and not isinstance(v, str))
        print("%-28s %10.3f %8d %12d  js=%.1f scad=%.1f  (%s)" % (
            ad, ek, adet, olcx, js, ref, detay))
    if olculemedi:
        print("\nOLCULEMEDI %d nokta — YESIL SAYILMAZ." % len(olculemedi))
    print("\nSINIR=%.2f" % sinir)
    print("ENKOTU=%s" % ("OLCULEMEDI" if en_kotu is None else "%.3f" % en_kotu))
    print("HUKUM=%s (cikis %d)" % (
        {0: "YESIL", 1: "KIRMIZI", OLCULEMEDI_KODU: "OLCULEMEDI",
         AYRISMA_KODU: "AYRISMA"}[cikis], cikis))


# ---- OLCUM ARKA UCU (kendini-test bunu degistirir) -------------------------
class Olcum(object):
    """GERCEK olcum: js tarafi hacim-eval.js, yer-gercegi OpenSCAD — ikisi de
    dogrula.py'nin kendi fonksiyonlari."""

    def __init__(self, esleme, scad_yol, openscad):
        self.esleme = esleme
        self.scad_yol = scad_yol
        self.openscad = openscad
        self.tmpdir = None

    def kimlik(self):
        with io.open(self.scad_yol, "rb") as f:
            ozet_ = hashlib.sha256(f.read()).hexdigest()
        try:
            proc = subprocess.run([self.openscad, "--version"],
                                  capture_output=True, timeout=60)
            surum = (proc.stdout + proc.stderr).decode("utf-8", "replace").strip()
        except Exception as e:                               # noqa: BLE001
            surum = "surum-okunamadi:%s" % e
        return "%s|%s" % (ozet_, surum)

    def anahtar(self, sset):
        return " ".join(dogrula.d_bayraklari(self.esleme, sset))

    def js(self, fonksiyon, setler):
        return dogrula.js_hacimler(fonksiyon, setler)

    def scad(self, sset, etiket):
        return dogrula.scad_hacim(self.openscad, self.scad_yol, self.esleme,
                                  sset, self.tmpdir, etiket)


# ---- RENDER ONBELLEGI -------------------------------------------------------
def onbellek_yukle(yol, kimlik):
    if not yol or not os.path.exists(yol):
        return {}
    try:
        with io.open(yol, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except Exception:                                        # noqa: BLE001
        return {}
    if veri.get("kimlik") != kimlik:
        return {}
    return veri.get("kayit") or {}


def onbellek_yaz(yol, kimlik, kayit):
    if not yol:
        return
    gecici = "%s.tmp.%d" % (yol, os.getpid())
    with io.open(gecici, "w", encoding="utf-8") as f:
        f.write(json.dumps({"kimlik": kimlik, "kayit": kayit}, ensure_ascii=False))
    os.replace(gecici, yol)


# ---- KOSUM ------------------------------------------------------------------
def tara(aile, yogunluk, sinir, onbellek_yolu, paralel, eksen_yogunluk=None,
         butce=VARSAYILAN_BUTCE, ince=True, olcum=None, hacim_kapisi=True):
    # 🔴 D1 — OLCMEDEN ONCE: fiyat yolunun okudugu govde aile kaynaklariyla ozdes mi?
    if hacim_kapisi:
        uretilen, tani = uretilen_hacim_govdesi()
        ok, hukum_tani = hacim_govdesi_hukmu(uretilen, diskteki_hacim_govdesi())
        print("hacim.js kapisi: %s%s" % (hukum_tani, "" if tani is None else
                                         "  [%s]" % tani))
        if not ok:
            print("\nENKOTU=OLCULMEDI")
            print("HUKUM=AYRISMA (cikis %d)" % AYRISMA_KODU)
            return AYRISMA_KODU

    import fcntl
    kilit = open(os.path.join(TEST_DIR, ".dogrula-kilit"), "w")
    fcntl.flock(kilit, fcntl.LOCK_EX)

    esleme = dogrula.yukle(os.path.join(dogrula.ESLEME_DIR, aile + ".json"))
    sema = dogrula.yukle(os.path.join(dogrula.URUN_DIR, esleme["urunId"] + ".json"))
    if sema.get("hacimFormulu") != esleme["fonksiyon"]:
        sys.exit("%s: sema.hacimFormulu != esleme.fonksiyon" % aile)
    if olcum is None:
        scad_yol = os.path.join(dogrula.scad_dizini(), esleme["scad"])
        if not os.path.exists(scad_yol):
            sys.exit("uretim modeli dosyasi yok: %s" % scad_yol)
        olcum = Olcum(esleme, scad_yol, dogrula.openscad_yolu())

    kimlik = olcum.kimlik()
    kayit = onbellek_yukle(onbellek_yolu, kimlik)
    sayac = {"render": 0}
    tmp = tempfile.mkdtemp(prefix="pruvo-yay-tarama-")
    olcum.tmpdir = tmp

    def render(setler, etiket_on):
        """Onbellekte OLMAYAN benzersiz setleri paralel render eder."""
        import threading
        from concurrent.futures import ThreadPoolExecutor
        sira = []
        gorulen = set()
        for s in setler:
            a = olcum.anahtar(s)
            if a in kayit or a in gorulen:
                continue
            gorulen.add(a)
            sira.append((a, s))
        if not sira:
            return
        kilit_onb = threading.Lock()
        bitti = [0]

        def kos(kalem):
            i, (a, s) = kalem
            ref = olcum.scad(s, "%s-%s-%d" % (aile, etiket_on, i))
            with kilit_onb:
                bitti[0] += 1
                sayac["render"] += 1
                if ref is not None:
                    kayit[a] = ref
                    onbellek_yaz(onbellek_yolu, kimlik, kayit)
                if bitti[0] % 25 == 0 or bitti[0] == len(sira):
                    print("  ... %s render %d/%d" % (etiket_on, bitti[0], len(sira)))
                    sys.stdout.flush()
            return ref

        with ThreadPoolExecutor(max_workers=max(1, paralel)) as havuz:
            list(havuz.map(kos, list(enumerate(sira))))

    try:
        # ---- 1) PROB: hangi eksen OLU, hangisi CANLI (OLCULEREK) -------------
        taban = taban_set(sema)
        secim_adlari = [p["ad"] for p in sema["parametreler"]
                        if p.get("tip", "sayi") == "secim"]
        sayi_parametreleri = [p for p in sema["parametreler"]
                              if p.get("tip", "sayi") == "sayi"]
        enum_sema = {"parametreler": [p for p in sema["parametreler"]
                                      if p.get("tip", "sayi") == "secim"]}
        dallar = izgara_uret(enum_sema, 2)

        prob_setleri = []
        for dal in dallar:
            for p in sayi_parametreleri:
                for deger in sayi_izgarasi(p, 3):
                    s = dict(taban)
                    s.update(dal)
                    s[p["ad"]] = deger
                    prob_setleri.append(s)
        render(prob_setleri, "prob")
        prob_renderi = sayac["render"]

        def hacim_of(s):
            return kayit.get(olcum.anahtar(s))

        olu_sayisal = {}
        for dal in dallar:
            anahtar = tuple(dal[a] for a in secim_adlari)
            olu = []
            for p in sayi_parametreleri:
                degerler = []
                for deger in sayi_izgarasi(p, 3):
                    s = dict(taban)
                    s.update(dal)
                    s[p["ad"]] = deger
                    degerler.append(hacim_of(s))
                if eksen_hukmu(degerler) == "OLU":
                    olu.append(p["ad"])
            olu_sayisal[anahtar] = olu

        olu_enum = {}
        for ad in secim_adlari:
            digerleri = [a for a in secim_adlari if a != ad]
            alt = {"parametreler": [p for p in sema["parametreler"]
                                    if p["ad"] in digerleri]}
            baglamlar = izgara_uret(alt, 2) if digerleri else [{}]
            enum_degerleri = secim_degerleri(
                [p for p in sema["parametreler"] if p["ad"] == ad][0])
            for baglam in baglamlar:
                degerler = []
                for v in enum_degerleri:
                    s = dict(taban)
                    s.update(baglam)
                    s[ad] = v
                    degerler.append(hacim_of(s))
                olu_enum[(ad, tuple(sorted(baglam.items())))] = (
                    eksen_hukmu(degerler) == "OLU")

        def olu_eksenler(sset):
            olu = []
            for ad in secim_adlari:
                baglam = tuple(sorted((a, sset[a]) for a in secim_adlari if a != ad))
                if olu_enum.get((ad, baglam)):
                    olu.append(ad)
            anahtar = tuple(taban[a] if a in olu else sset[a] for a in secim_adlari)
            return olu + list(olu_sayisal.get(anahtar, []))

        print("OLU EKSEN OLCUMU (prob renderi %d):" % prob_renderi)
        for dal in dallar:
            s0 = dict(taban)
            s0.update(dal)
            olu = olu_eksenler(s0)
            print("  %-24s OLU: %s" % ("/".join(str(dal[a]) for a in secim_adlari),
                                       ", ".join(olu) if olu else "-"))
        sys.stdout.flush()

        # ---- 2) KAPSAM izgarasi + INCE izgara --------------------------------
        setler = izgara_uret(sema, yogunluk, eksen_yogunluk)
        kapsam_adedi = len(setler)
        if ince:
            gruplar = {}
            for dal in dallar:
                s0 = dict(taban)
                s0.update(dal)
                pay = tuple(sorted(render_anahtari_seti(
                    s0, olu_eksenler(s0), taban).items()))
                gruplar.setdefault(pay, s0)
            butce_payi = max(2, butce // max(1, len(gruplar)))
            for s0 in gruplar.values():
                olu = olu_eksenler(s0)
                canli = [p for p in sayi_parametreleri if p["ad"] not in olu]
                if not canli:
                    continue
                d0 = ince_yogunluk(len(canli), butce_payi)
                yog = dict((p["ad"], min(sema_basamak_sayisi(p), d0)) for p in canli)
                alt = {"parametreler": [p for p in sema["parametreler"]
                                        if p["ad"] in yog]}
                for nokta in izgara_uret(alt, 1, yog):
                    yeni = dict(s0)
                    yeni.update(nokta)
                    setler.append(yeni)

        gorulen = set()
        benzersiz = []
        for s in setler:
            imza = tuple(sorted(s.items()))
            if imza in gorulen:
                continue
            gorulen.add(imza)
            benzersiz.append(s)
        setler = benzersiz

        pay_setleri = [render_anahtari_seti(s, olu_eksenler(s), taban) for s in setler]
        pay_benzersiz = []
        gorulen = set()
        for s in pay_setleri:
            a = olcum.anahtar(s)
            if a in gorulen:
                continue
            gorulen.add(a)
            pay_benzersiz.append(s)

        print("izgara: %d kapsam + %d ince = %d MANTIKSAL nokta -> %d BENZERSIZ "
              "geometri (render paylasimi %.1fx)" % (
                  kapsam_adedi, len(setler) - kapsam_adedi, len(setler),
                  len(pay_benzersiz), len(setler) / float(max(1, len(pay_benzersiz)))))
        print("onbellek=%s · sinir=%%%.2f · butce=%d · paralel=%d" % (
            onbellek_yolu or "yok", sinir, butce, paralel))
        sys.stdout.flush()

        render(pay_benzersiz, "izgara")

        # ---- 3) JS TARAFI: HER MANTIKSAL NOKTADA (paylasim YOK) --------------
        js = olcum.js(esleme["fonksiyon"], setler)
        sonuclar = []
        for i, s in enumerate(setler):
            sonuclar.append((dal_anahtari(sema, s), s, js[i],
                             kayit.get(olcum.anahtar(pay_setleri[i]))))
        tablo, en_kotu, olculemedi, cikis = ozet(sonuclar, sinir)
        print("\nyeni render: %d · benzersiz geometri: %d · mantiksal nokta: %d" % (
            sayac["render"], len(pay_benzersiz), len(setler)))
        tabloyu_bas(tablo, en_kotu, olculemedi, sinir, cikis)
        return cikis
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- KENDINI TEST (OpenSCAD/node GEREKTIRMEZ) -------------------------------
class SahteOlcum(object):
    """kendini-test olcum arka ucu: js ve yer-gercegi BILINEN degerler."""

    def __init__(self, gercek, js_carpani=1.0):
        self.gercek = gercek
        self.js_carpani = js_carpani
        self.tmpdir = None

    def kimlik(self):
        return "sahte-kimlik"

    def anahtar(self, sset):
        return json.dumps(sorted(sset.items()), ensure_ascii=False)

    def js(self, fonksiyon, setler):
        return [self.gercek(s) * self.js_carpani for s in setler]

    def scad(self, sset, etiket):
        return self.gercek(sset)


def kendini_test():
    """Surucunun KENDI mantigi — UC yon: (a) izgara semayi TAM tariyor mu ·
    (b) saf hukum fail-closed mi · (c) `tara()` KOLU: hukmu O veriyor, iddia
    edilmeden birakilamaz (curutucu bu kolda 3 kontrol mutanti sag birakti)."""
    vakalar = []

    def bekle(ad, kosul, detay=""):
        vakalar.append((ad, bool(kosul), detay))

    sema = {"parametreler": [
        {"ad": "tip", "tip": "secim", "secenekler": [
            {"deger": "a"}, {"deger": "b"}, {"deger": "c"}]},
        {"ad": "form", "tip": "secim", "secenekler": ["x", "y"]},
        {"ad": "boy", "tip": "sayi", "min": 40, "max": 120, "adim": 1},
        {"ad": "kalinlik", "tip": "sayi", "min": 1.5, "max": 4, "adim": 0.5},
    ]}

    izgara = izgara_uret(sema, 3)
    bekle("I1 kartezyen tam (3*2*3*3)", len(izgara) == 54, "adet=%d" % len(izgara))
    bekle("I2 secim: TUM enum degerleri taraniyor",
          set(s["tip"] for s in izgara) == set(["a", "b", "c"]) and
          set(s["form"] for s in izgara) == set(["x", "y"]),
          "tip=%s form=%s" % (sorted(set(s["tip"] for s in izgara)),
                              sorted(set(s["form"] for s in izgara))))
    boylar = sorted(set(s["boy"] for s in izgara))
    bekle("I3 sayi: min/orta/max icerde", boylar == [40.0, 80.0, 120.0], "%s" % boylar)
    kal = sorted(set(s["kalinlik"] for s in izgara))
    izgarada = all(abs((v - 1.5) / 0.5 - round((v - 1.5) / 0.5)) < 1e-9 for v in kal)
    bekle("I4 sayi: uc noktalar + TUM degerler adim izgarasinda",
          kal[0] == 1.5 and kal[-1] == 4.0 and len(kal) == 3 and izgarada, "%s" % kal)
    yogun = sorted(set(s["boy"] for s in izgara_uret(sema, 5)))
    bekle("I5 yogunluk artinca izgara SIKLASIR",
          len(yogun) == 5 and yogun[0] == 40.0 and yogun[-1] == 120.0, "%s" % yogun)
    tek = izgara_uret(sema, 1, {"boy": 9})
    boy9 = sorted(set(s["boy"] for s in tek))
    bekle("I5b tek eksen sikilastirilir, digerleri seyrek kalir",
          len(boy9) == 9 and boy9[0] == 40.0 and boy9[-1] == 120.0 and
          len(set(s["kalinlik"] for s in tek)) == 1 and len(tek) == 3 * 2 * 9,
          "boy=%s adet=%d" % (boy9, len(tek)))
    bekle("I5c eksen sikistirmasi ENUM eksenlerini KISMAZ (kor tarama olmaz)",
          set(s["tip"] for s in tek) == set(["a", "b", "c"]) and
          set(s["form"] for s in tek) == set(["x", "y"]))
    bekle("I5d yogunluk<2 kolunda ALT SINIR alinir (orta nokta DEGIL)",
          sayi_izgarasi(sema["parametreler"][2], 1) == [40.0] and
          sayi_izgarasi(sema["parametreler"][3], 1) == [1.5],
          "%s / %s" % (sayi_izgarasi(sema["parametreler"][2], 1),
                       sayi_izgarasi(sema["parametreler"][3], 1)))
    bekle("I5e taban set: her sayisal eksende min, her enumda ilk deger",
          taban_set(sema) == {"tip": "a", "form": "x", "boy": 40.0, "kalinlik": 1.5},
          "%s" % taban_set(sema))
    bekle("I5f sema cozunurlugu (basamak sayisi) dogru",
          sema_basamak_sayisi(sema["parametreler"][2]) == 81 and
          sema_basamak_sayisi(sema["parametreler"][3]) == 6,
          "%s / %s" % (sema_basamak_sayisi(sema["parametreler"][2]),
                       sema_basamak_sayisi(sema["parametreler"][3])))
    bekle("I6 dal anahtari = TUM secim parametreleri",
          dal_anahtari(sema, izgara[0]) == (izgara[0]["tip"], izgara[0]["form"]),
          "%s" % (dal_anahtari(sema, izgara[0]),))

    d1 = ("a", "x")
    d2 = ("b", "y")
    hepsi_yesil = [(d1, {"boy": 40}, 100.0, 100.4), (d2, {"boy": 40}, 100.0, 100.2)]
    tablo, ek, olcx, cikis = ozet(hepsi_yesil, 1.0)
    bekle("H1 temiz kosum YESIL + en kotu dogru dal",
          cikis == 0 and abs(ek - 0.3984) < 1e-3 and len(tablo) == 2,
          "cikis=%s enkotu=%s" % (cikis, ek))
    tablo, ek, olcx, cikis = ozet(
        hepsi_yesil + [(d1, {"boy": 120}, 100.0, 102.5)], 1.0)
    bekle("H2 sinir asilinca KIRMIZI", cikis == 1 and ek > 2.4,
          "cikis=%s enkotu=%s" % (cikis, ek))
    tablo, ek, olcx, cikis = ozet(
        hepsi_yesil + [(d1, {"boy": 120}, 100.0, None)], 1.0)
    bekle("H3 tek olculemeyen nokta YESIL SAYILMAZ (digerleri yesilken)",
          cikis == OLCULEMEDI_KODU and len(olcx) == 1, "cikis=%s" % cikis)
    tablo, ek, olcx, cikis = ozet(
        hepsi_yesil + [(d1, {"boy": 120}, 100.0, 0.0)], 1.0)
    bekle("H4 sifir referans hacim YESIL SAYILMAZ (0'a bolme yerine OLCULEMEDI)",
          cikis == OLCULEMEDI_KODU, "cikis=%s" % cikis)
    tablo, ek, olcx, cikis = ozet([], 1.0)
    bekle("H5 hic olcum yoksa YESIL DEGIL (sifir set = yesil deligi)",
          cikis == OLCULEMEDI_KODU and ek is None, "cikis=%s enkotu=%s" % (cikis, ek))
    tablo, ek, olcx, cikis = ozet(
        [(d1, {"boy": 40}, 100.0, 100.4), (d1, {"boy": 120}, 100.0, 100.9)], 1.0)
    bekle("H6 dal basina EN KOTU (ortalama degil) raporlanir",
          abs(tablo[0][1] - 0.8920) < 1e-3, "dal en kotu=%s" % tablo[0][1])
    tablo, ek, olcx, cikis = ozet(
        [(d1, {"boy": 40}, 100.0, 100.4), (d2, {"boy": 40}, 100.0, None)], 1.0)
    bekle("H7 bir dal tumden olculemedi -> tabloda OLCULEMEDI satiri + cikis 3",
          cikis == OLCULEMEDI_KODU and
          any(satir[1] is None for satir in tablo), "tablo=%s" % (tablo,))

    tmp = tempfile.mkdtemp(prefix="pruvo-yay-onbellek-")
    yol = os.path.join(tmp, "onb.json")
    onbellek_yaz(yol, "kimlik-A", {"-D x=1": 123.0})
    bekle("O1 ayni kimlikte onbellek okunur",
          onbellek_yukle(yol, "kimlik-A") == {"-D x=1": 123.0},
          "%s" % onbellek_yukle(yol, "kimlik-A"))
    bekle("O2 kimlik degisince onbellek TUMDEN gecersiz (model/OpenSCAD degisti)",
          onbellek_yukle(yol, "kimlik-B") == {}, "%s" % onbellek_yukle(yol, "kimlik-B"))
    with io.open(yol, "w", encoding="utf-8") as _f:
        _f.write("{bozuk")
    bekle("O3 bozuk onbellek dosyasi COKERTMEZ, bos sayilir",
          onbellek_yukle(yol, "kimlik-A") == {})
    bekle("O4 onbellek dosyasi yoksa bos",
          onbellek_yukle(os.path.join(tmp, "yok.json"), "kimlik-A") == {})
    shutil.rmtree(tmp, ignore_errors=True)

    # --- D1: OLCTUGU DOSYANIN UZERINE YAZMAMA (ayrisma kapisi) ---
    bekle("A1 ozdes govde -> kapi ACIK", hacim_govdesi_hukmu("abc", "abc")[0] is True)
    bekle("A2 AYRISIK govde -> kapi KAPALI (olcum yok, uzerine yazma yok)",
          hacim_govdesi_hukmu("abc", "abX")[0] is False,
          hacim_govdesi_hukmu("abc", "abX")[1][:48])
    bekle("A3 govde URETILEMEDI -> YESIL DEGIL (fail-closed)",
          hacim_govdesi_hukmu(None, "abc")[0] is False)
    bekle("A4 hacim.js diskte YOK -> YESIL DEGIL (fail-closed)",
          hacim_govdesi_hukmu("abc", None)[0] is False)
    disk_once = diskteki_hacim_govdesi()
    uretilen, tani = uretilen_hacim_govdesi()
    bekle("A5 govde uretimi diskteki hacim.js'e DOKUNMAZ (gecici dizine yazar)",
          uretilen is not None and diskteki_hacim_govdesi() == disk_once,
          "tani=%s" % (tani,))
    bekle("A6 bu depoda hacim.js aile kaynaklariyla OZDES",
          hacim_govdesi_hukmu(uretilen, disk_once)[0] is True,
          hacim_govdesi_hukmu(uretilen, disk_once)[1][:60])

    # --- D4: OLU EKSEN HUKMU (fail-closed) ---
    bekle("E1 tum problar esit -> OLU", eksen_hukmu([10.0, 10.0, 10.0]) == "OLU")
    bekle("E2 farkli prob -> CANLI", eksen_hukmu([10.0, 10.5, 10.0]) == "CANLI")
    bekle("E3 olculemeyen prob OLU SAYILMAZ (render paylasimina girmez)",
          eksen_hukmu([10.0, None, 10.0]) == "OLCULEMEDI")
    bekle("E4 sifir hacimli prob OLU SAYILMAZ", eksen_hukmu([0.0, 0.0]) == "OLCULEMEDI")
    bekle("E5 tek prob -> hukum verilmez", eksen_hukmu([10.0]) == "OLCULEMEDI")
    bekle("E6 render paylasimi YALNIZ olu ekseni taban degerine ceker",
          render_anahtari_seti({"a": 1, "b": 2, "c": 3}, ["b"],
                               {"a": 9, "b": 9, "c": 9}) == {"a": 1, "b": 9, "c": 3})
    bekle("E7 butce canli eksen sayisina gore bolunur",
          ince_yogunluk(1, 100) == 100 and ince_yogunluk(3, 100) == 4,
          "%s / %s" % (ince_yogunluk(1, 100), ince_yogunluk(3, 100)))

    # --- D3: `tara()` KOLU ---
    bekle("T0 VARSAYILAN_SINIR mimar hukmunde (1.0) CAPALI",
          abs(VARSAYILAN_SINIR - 1.0) < 1e-12, "%s" % VARSAYILAN_SINIR)

    kok = tempfile.mkdtemp(prefix="pruvo-yay-tara-")
    eski_esleme, eski_urun = dogrula.ESLEME_DIR, dogrula.URUN_DIR
    try:
        dogrula.ESLEME_DIR = os.path.join(kok, "esleme")
        dogrula.URUN_DIR = os.path.join(kok, "urunler")
        os.makedirs(dogrula.ESLEME_DIR)
        os.makedirs(dogrula.URUN_DIR)
        t_sema = {"id": "sentetik", "hacimFormulu": "sentetik", "parametreler": [
            {"ad": "tip", "tip": "secim", "secenekler": ["p", "q"]},
            {"ad": "boy", "tip": "sayi", "min": 10, "max": 30, "adim": 10},
            {"ad": "olu", "tip": "sayi", "min": 1, "max": 3, "adim": 1},
        ]}
        t_esleme = {"urunId": "sentetik", "scad": "yok.scad", "fonksiyon": "sentetik",
                    "esleme": {"tip": "tip", "boy": "boy", "olu": "olu"}}
        with io.open(os.path.join(dogrula.URUN_DIR, "sentetik.json"), "w",
                     encoding="utf-8") as f:
            f.write(json.dumps(t_sema))
        with io.open(os.path.join(dogrula.ESLEME_DIR, "sentetik.json"), "w",
                     encoding="utf-8") as f:
            f.write(json.dumps(t_esleme))

        def gercek(s):
            # `olu` ekseni yer-gercegini DEGISTIRMEZ; boy ve tip degistirir.
            return 100.0 + s["boy"] + (0.0 if s["tip"] == "p" else 50.0)

        def kos_tara(js_carpani, sinir=VARSAYILAN_SINIR, ince=False):
            cikti = io.StringIO()
            with contextlib.redirect_stdout(cikti):
                kod = tara("sentetik", 3, sinir, None, 1, ince=ince,
                           olcum=SahteOlcum(gercek, js_carpani), hacim_kapisi=False)
            return kod, cikti.getvalue()

        def enkotu_satiri(cikti):
            return [s for s in cikti.splitlines() if s.startswith("ENKOTU")]

        kod, cikti = kos_tara(1.0)
        bekle("T1 tara(): js == yer-gercegi -> YESIL (cikis 0)",
              kod == 0 and "ENKOTU=0.000" in cikti, enkotu_satiri(cikti))
        kod, cikti = kos_tara(1.005)
        bekle("T2 tara(): VARSAYILAN sinir uygulanir — %0.5 sapma YESIL",
              kod == 0 and "ENKOTU=0.500" in cikti, enkotu_satiri(cikti))
        kod, cikti = kos_tara(1.015)
        bekle("T3 tara(): VARSAYILAN sinir uygulanir — %1.5 sapma KIRMIZI",
              kod == 1 and "ENKOTU=1.500" in cikti, enkotu_satiri(cikti))
        kod, cikti = kos_tara(0.5)
        bekle("T4 tara(): sapma js/scad SIRASINI korur (js yarisi -> %50; "
              "yer degistirse %100 olurdu)",
              kod == 1 and "ENKOTU=50.000" in cikti, enkotu_satiri(cikti))
        kod, cikti = kos_tara(1.0, ince=True)
        bekle("T5 tara(): OLU eksen OLCULEREK bulunur, render PAYLASILIR",
              kod == 0 and "OLU: olu" in cikti,
              [s for s in cikti.splitlines() if "OLU:" in s])
        bekle("T6 tara(): mantiksal nokta > benzersiz geometri (JS her noktada, "
              "render paylasimli)",
              "MANTIKSAL nokta" in cikti and "BENZERSIZ geometri" in cikti,
              [s for s in cikti.splitlines() if "MANTIKSAL" in s])

        cikti = io.StringIO()
        eski_fn = globals()["diskteki_hacim_govdesi"]
        globals()["diskteki_hacim_govdesi"] = lambda yol=HACIM_JS: "AYRISIK GOVDE"
        try:
            with contextlib.redirect_stdout(cikti):
                kod = tara("sentetik", 3, VARSAYILAN_SINIR, None, 1, ince=False,
                           olcum=SahteOlcum(gercek, 1.0), hacim_kapisi=True)
        finally:
            globals()["diskteki_hacim_govdesi"] = eski_fn
        bekle("T7 tara(): hacim.js AYRISIKSA OLCUM YAPILMAZ (cikis 4, tablo yok)",
              kod == AYRISMA_KODU and "HUKUM=AYRISMA" in cikti.getvalue() and
              "ENKOTU=0.000" not in cikti.getvalue(),
              [s for s in cikti.getvalue().splitlines() if s.startswith("HUKUM")])

        cikti = io.StringIO()
        eski_fn = globals()["uretilen_hacim_govdesi"]
        globals()["uretilen_hacim_govdesi"] = lambda: (None, "sahte hata")
        try:
            with contextlib.redirect_stdout(cikti):
                kod = tara("sentetik", 3, VARSAYILAN_SINIR, None, 1, ince=False,
                           olcum=SahteOlcum(gercek, 1.0), hacim_kapisi=True)
        finally:
            globals()["uretilen_hacim_govdesi"] = eski_fn
        bekle("T8 tara(): govde URETILEMEZSE olcum YAPILMAZ (birlestir hatasi "
              "yutulamaz)",
              kod == AYRISMA_KODU and "HUKUM=AYRISMA" in cikti.getvalue(),
              [s for s in cikti.getvalue().splitlines() if s.startswith("HUKUM")])
    finally:
        dogrula.ESLEME_DIR, dogrula.URUN_DIR = eski_esleme, eski_urun
        shutil.rmtree(kok, ignore_errors=True)

    kirmizi = [v for v in vakalar if not v[1]]
    print("YAY TARAMA SURUCUSU — KENDINI TEST: %d/%d YESIL" % (
        len(vakalar) - len(kirmizi), len(vakalar)))
    for ad, yesil, detay in vakalar:
        print("  %s %-60s %s" % ("+" if yesil else "-", ad, detay if not yesil else ""))
    return 1 if kirmizi else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aile", default="yay")
    ap.add_argument("--yogunluk", type=int, default=3,
                    help="KAPSAM izgarasinda her sayisal eksen icin nokta sayisi")
    ap.add_argument("--sinir", type=float, default=VARSAYILAN_SINIR,
                    help="kabul siniri (%%). Allowlist esigi 1.0 (mimar hukmu).")
    ap.add_argument("--butce", type=int, default=VARSAYILAN_BUTCE,
                    help="INCE izgaraya ayrilan benzersiz render tavani")
    ap.add_argument("--ince-yok", action="store_true",
                    help="yalniz KAPSAM izgarasi (canli-eksen ince taramasi yok)")
    ap.add_argument("--onbellek", default=os.path.join(
        tempfile.gettempdir(), "pruvo-yay-tarama-onbellek.json"),
        help="render onbellegi yolu ('yok' -> onbelleksiz)")
    ap.add_argument("--paralel", type=int, default=4,
                    help="es zamanli render sayisi (sonucu DEGISTIRMEZ, sureyi kisaltir)")
    ap.add_argument("--yogunluk-eksen", action="append", default=[], metavar="AD=N",
                    help="tek bir sayisal ekseni sikilastir (or. dalga_boyu=81)")
    ap.add_argument("--kendini-test", action="store_true")
    args = ap.parse_args()
    if args.kendini_test:
        sys.exit(kendini_test())
    eksen = {}
    for kalem in args.yogunluk_eksen:
        if "=" not in kalem:
            sys.exit("--yogunluk-eksen bicimi: AD=N (alinan: %r)" % kalem)
        ad, deger = kalem.split("=", 1)
        eksen[ad] = int(deger)
    onbellek = None if args.onbellek == "yok" else args.onbellek
    sys.exit(tara(args.aile, args.yogunluk, args.sinir, onbellek, args.paralel,
                  eksen, args.butce, not args.ince_yok))


if __name__ == "__main__":
    main()

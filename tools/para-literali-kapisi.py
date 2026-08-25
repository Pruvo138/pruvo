#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PARA LITERALI KAPISI (K107) — SINIF NOBETCISI.

NEDEN VAR — OLCULMUS KESINTI (K106, 15 Agu 2026): `tools/eski-fiyat-test.py`
fiksturu `eski_fiyat="1.200 TL"` (120.000 kurus) SABIT yaziyordu. Malzeme
politikasi PETG'den ABS'e cevrilince ayni fiksturun ILAN tutari 110.500 ->
136.000 kurusa cikti; eski fiyat ilanin ALTINDA kaldi, `eski_fiyat_html` onu
-- DOGRU davranarak -- basmayi birakti, test KIRMIZI yandi, `serit-a2` kirmizi
oldu, `deploy` isi `needs` zinciriyle SKIPPED kaldi ve CANLI SITE 7,5 SAAT
main'in gerisinde kaldi. Kural bozulmamisti; FIKSTUR bayatlamisti.

O vakaya TEKIL YAMA uygulandi (`_gecerli_vaka()` artik `build.ilan_kurus`'tan
turetiyor) ama SINIFI koruyan nobetci YOKTU -> ayni hata baska fiksturde
tekrar eder ([[tekil-yama-sinifi-kapatmaz]]). Bu kapi o sinifi olcer.

═══════════════════════════════════════════════════════════════════════════
HUKUM (tek cumle)
═══════════════════════════════════════════════════════════════════════════
Bir kabul fiksturu, POLITIKA-TUREVLI bir kiyasa giren para degerini SABIT
LITERAL olarak tasiyorsa UYARILIR. Kanonik turetme fonksiyonundan
(`ilan_kurus` / `vitrin_kurus` / `_birim_kurus`) turetilen fikstur YESIL gecer.

═══════════════════════════════════════════════════════════════════════════
🔴 KAPI KENDI KANONIK KUMESINI ELLE TUTMAZ — `build.py`'DEN TURETIR
═══════════════════════════════════════════════════════════════════════════
Elle liste de ad deseni de bir defterdir ve BAYATLAR
([[kapsam-evrenini-cagri-grafindan-turet]]). Bu yuzden:

  TURETME      : `_birim_kurus` TOHUMUNDAN cagri grafiyla kapatilir — bir
                 `build.py` fonksiyonu, `Return` degerinin altinda kumeden
                 birine cagri tasiyorsa TURETME'dir (ilan_kurus, vitrin_kurus,
                 cip_kurus ... otomatik gelir). `build.py` `_birim_kurus`
                 govdesinde "🔴 TEK TURETME NOKTASI" diyor; tohum odur.
  KIYAS_YUZEYI : bir `Compare` dugumunun operandi TURETME cagrisina (ya da
                 TURETME cagrisindan atanmis yerel ada) dayaniyorsa o fonksiyon
                 TOHUM YUZEYDIR; ustune TRANSITIF CAGIRANLARI eklenir
                 (`eski_fiyat_html` -> `render_product` ...).

Iki kume de FAIL-CLOSED capalarla dogrulanir (asagida `CAPA_*`): yapi
degisirse kapi sessizce DARALMAZ, `OLCULEMEDI` (rc=2) verir.

═══════════════════════════════════════════════════════════════════════════
🔴 YANLIS-POZITIF NOBETI — HUKMU URETIM FONKSIYONUNUN KENDISI VERIR
═══════════════════════════════════════════════════════════════════════════
Bu depoda kapilar `continue-on-error`'suz kosuyor: yanlis-pozitif TUM EKIBIN
yayinini durdurur ([[kapi-disiplin-ilkesi]]). Bu yuzden kapi "para literali
gordum" diye UYARMAZ. Bir fiksturun politikaya BAGLI olup olmadigini KENDI
regex'iyle degil, URETIM FONKSIYONUNU IKI YONLU DURTEREK olcer:

    taban   = <tohum yuzey>(fikstur)
    ×3 / ÷3 : `build._birim_kurus` gecici olarak olceklenir
    cikti DEGISIYORSA  -> fiksturun hukmu POLITIKAYA BAGLI  -> UYARI
    cikti AYNI KALIYORSA -> politika-BAGIMSIZ               -> YESIL

Bu tek olcum, elle yazilacak butun istisnalari GEREKSIZ kilar ve ikinci bir
para ayristiricisi yazmadigi icin ikiz tanim uretmez
([[ikiz-tanim-sessiz-ayrisma]]):
  * `eski_fiyat="800 TL"` (guncelin ALTINDA)  -> iki yonde de ""   -> YESIL
  * `eski_fiyat="1200 USD"` / bozuk / XSS      -> iki yonde de ""   -> YESIL
  * `parametrik`/`konfigur` urunu              -> iki yonde de ""   -> YESIL
  * `eski_fiyat` HIC YOK                       -> iki yonde de ""   -> YESIL
  * degeri `ilan_kurus`'tan TUREYEN fikstur    -> deger SABIT DEGIL -> YESIL
  * `eski_fiyat="1.200 TL"` SABIT + gecerli    -> cikti DEGISIR     -> UYARI

🔴 IKI YON SART: durtme tek yonlu (yalniz ×3) olsaydi, K106'nin ZATEN kirilmis
hali (eski fiyat ilanin ALTINDA kalmis fikstur) ×3'te de "" verip AYNI kalir
ve kapi kendi dogus vakasini KACIRIRDI. ÷3 o yonu acar.

═══════════════════════════════════════════════════════════════════════════
KAPSAM / MENZIL
═══════════════════════════════════════════════════════════════════════════
Evren AD DESENINDEN degil CAGRI GRAFINDAN gelir: `tools/**/*.py` icinde bir
KIYAS_YUZEYI adini ANAN her dosya taranir; icindeki her KIYAS_YUZEYI cagrisinin
0. argumani statik olarak fikstur sozlugune indirgenir (dict literali · yerel
ad · ayni dosyadaki yardimci fonksiyon, derinlik <= 3). SABIT OLMAYAN deger
kumeye GIRMEZ -> turetilen fikstur yapisal olarak politika-bagimsizdir.

Cagri yeri: `.github/workflows/nobet.yml` :: job `serit-b` (yayini BLOKLAMAZ).
Defterdeki plan bunu soyluyor: iki tur temiz gorulunce serit A'ya alinabilir.
`python3 tools/ci-kapsam-test.py` bu baglantiyi olcer — yorum satiri "kosuyor"
saymaz ([[kapinin-menzili-cagri-yeridir]]).

KULLANIM
  python3 tools/para-literali-kapisi.py              # canli tarama (rc 0/1/2)
  python3 tools/para-literali-kapisi.py --kendini-test   # 8 fikstur, hermetik
  python3 tools/para-literali-kapisi.py --mutasyon       # 5 mutant + 1 kontrol
"""

import ast
import io
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
BUILD_YOLU = os.path.join(TOOLS, "build.py")

# ---- FAIL-CLOSED CAPALAR ---------------------------------------------------
# 🔴 Kume TURETILIYOR; ama turetimin YAPISAL VARSAYIMI capalarla olculur.
# build.py'de turetme noktasi tasinir/yeniden adlandirilirsa kapi SESSIZCE
# bosalmak yerine OLCULEMEDI (rc=2) verir ([[kapi-uretici-dili-degisince-korlesir]]).
TOHUM_TURETME = "_birim_kurus"
CAPA_TURETME = ("_birim_kurus", "ilan_kurus", "vitrin_kurus")
CAPA_KIYAS = ("eski_fiyat_html", "render_product")

# Para BICIMI — YALNIZ RAPORLAMA/AYIKLAMA icin (hukum bu regex'ten CIKMAZ;
# hukmu yukaridaki durtme olcumu verir). Bu yuzden gevsek olmasi zararsizdir.
PARA_BICIMI = re.compile(r"[0-9][0-9.,]*\s*(?:TL|TRY|₺)", re.I)

COZUM_DERINLIGI = 3
DURTME_KATSAYILARI = (3.0, 1.0 / 3.0)

# Taranmayacak yollar: kapinin KENDISI (kendi docstring'indeki ornekler
# fikstur degildir) + arsiv + build.py (uretim kaynagi, fikstur degil).
HARIC_YOLLAR = ("tools/para-literali-kapisi.py", "tools/build.py")
HARIC_ONEKLER = ("tools/arsiv/",)


# ===========================================================================
# 1) BUILD.PY'DEN KANONIK KUMELERI TURET (AST — kod CALISTIRMADAN)
# ===========================================================================
def _ust_fonksiyonlar(agac):
    """build.py'nin MODUL DUZEYI fonksiyonlari: {ad: FunctionDef}."""
    return {d.name: d for d in agac.body
            if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _cagri_adlari(dugum):
    """Bir alt agacta cagrilan TUM adlar (`f(...)` ve `mod.f(...)` -> "f")."""
    adlar = set()
    for alt in ast.walk(dugum):
        if isinstance(alt, ast.Call):
            f = alt.func
            if isinstance(f, ast.Name):
                adlar.add(f.id)
            elif isinstance(f, ast.Attribute):
                adlar.add(f.attr)
    return adlar


def turetme_kumesi(fonksiyonlar):
    """TURETME = TOHUM + `Return` degerinde kumeye cagri tasiyan fonksiyonlar.

    `Return` sarti KASITLI: `eski_fiyat_html` govdesinde `ilan_kurus(p)`
    CAGIRIR ama onu DONDURMEZ — o bir KIYAS yuzeyidir, turetme degil. Sart
    `Call` duzeyine gevsetilseydi iki kume BIRBIRINE KARISIR ve kapi kendi
    hedefini turetme sanip susardi."""
    kume = {TOHUM_TURETME} if TOHUM_TURETME in fonksiyonlar else set()
    for _ in range(len(fonksiyonlar) + 1):
        eklendi = False
        for ad, fn in fonksiyonlar.items():
            if ad in kume:
                continue
            for alt in ast.walk(fn):
                if isinstance(alt, ast.Return) and alt.value is not None:
                    if _cagri_adlari(alt.value) & kume:
                        kume.add(ad)
                        eklendi = True
                        break
        if not eklendi:
            break
    return kume


def _turetilmis_yerel_adlar(fn, turetme):
    """Govde icinde TURETME cagrisindan atanan yerel adlar (`_ilan = ilan_kurus(p)`)."""
    adlar = set()
    for alt in ast.walk(fn):
        if isinstance(alt, ast.Assign) and _cagri_adlari(alt.value) & turetme:
            for hedef in alt.targets:
                if isinstance(hedef, ast.Name):
                    adlar.add(hedef.id)
        elif isinstance(alt, ast.AnnAssign) and alt.value is not None:
            if _cagri_adlari(alt.value) & turetme:
                if isinstance(alt.target, ast.Name):
                    adlar.add(alt.target.id)
    return adlar


def kiyas_tohumlari(fonksiyonlar, turetme):
    """TOHUM YUZEY: bir `Compare` operandi TURETME degerine dayanan fonksiyon.

    `eski_fiyat_html` bunun tam ornegi:  `_ilan = ilan_kurus(p)` ... `kurus <= _ilan`
    Operand bir CAGRI degil bir AD oldugu icin yalniz alt-agac taramasi YETMEZ;
    yerel ad haritasi olmadan kapi kendi dogus vakasini bulamazdi."""
    tohumlar = set()
    for ad, fn in fonksiyonlar.items():
        yerel = _turetilmis_yerel_adlar(fn, turetme)
        for alt in ast.walk(fn):
            if not isinstance(alt, ast.Compare):
                continue
            operandlar = [alt.left] + list(alt.comparators)
            for op in operandlar:
                if _cagri_adlari(op) & turetme:
                    tohumlar.add(ad)
                    break
                if any(isinstance(x, ast.Name) and x.id in yerel
                       for x in ast.walk(op)):
                    tohumlar.add(ad)
                    break
            if ad in tohumlar:
                break
    return tohumlar


def _ilk_parametre(fn):
    args = fn.args.posonlyargs + fn.args.args if hasattr(fn.args, "posonlyargs") \
        else fn.args.args
    return args[0].arg if args else None


def kiyas_yuzeyi(fonksiyonlar, tohumlar):
    """TOHUM + URUNU GECIREN transitif cagiranlari.

    🔴 KAPSAM SINIRI KASITLI VE OLCULMUS BIR KARARDIR. "Cagiran = yuzey" diye
    duz transitif kapatma yapilsaydi kume `main`/`uret` gibi URUN ALMAYAN
    fonksiyonlari da yutardi; o adlar HER dosyada gectigi icin evren tum depoya
    sisip anlamsiz "fikstur"ler uretirdi ([[kapi-kapsam-genisletme-tuzagi]]).

    Sart: cagiran, kumeden bir uyeyi KENDI ILK PARAMETRESIYLE cagirmali —
    yani urun sozlugu o fonksiyondan GECIYOR olmali. `render_product(p, ...)`
    icinde `eski_fiyat_html(p)` vardir ve `p` render_product'in ilk
    parametresidir -> yuzeye girer. `main()` icindeki `render_product(u, ...)`
    ise dongu degiskenidir -> GIRMEZ."""
    kume = set(tohumlar)
    for _ in range(len(fonksiyonlar) + 1):
        eklendi = False
        for ad, fn in fonksiyonlar.items():
            if ad in kume:
                continue
            ilk = _ilk_parametre(fn)
            if ilk is None:
                continue
            for alt in ast.walk(fn):
                if not isinstance(alt, ast.Call) or not alt.args:
                    continue
                f = alt.func
                cagrilan = f.id if isinstance(f, ast.Name) else (
                    f.attr if isinstance(f, ast.Attribute) else None)
                if cagrilan in kume and isinstance(alt.args[0], ast.Name) \
                        and alt.args[0].id == ilk:
                    kume.add(ad)
                    eklendi = True
                    break
        if not eklendi:
            break
    return kume


def kanonik_kumeler(kaynak=None):
    """(turetme, tohumlar, yuzey, olculemedi_sebepleri)."""
    if kaynak is None:
        with io.open(BUILD_YOLU, encoding="utf-8") as f:
            kaynak = f.read()
    agac = ast.parse(kaynak)
    fonksiyonlar = _ust_fonksiyonlar(agac)
    turetme = turetme_kumesi(fonksiyonlar)
    ham_tohumlar = kiyas_tohumlari(fonksiyonlar, turetme)
    yuzey = kiyas_yuzeyi(fonksiyonlar, ham_tohumlar)

    # DURTME TOHUMLARI: probu YALNIZ tek-argumanli tohumlarla kosariz. Arity
    # uyusmazligini `TypeError` yakalayarak elemek, fonksiyonun ICINDEN gelen
    # gercek bir `TypeError`i da sessizce yutardi ([[fail-slow-fail-opendir]]);
    # ayrim burada, IMZADAN yapilir.
    tohumlar = {a for a in ham_tohumlar
                if len(fonksiyonlar[a].args.args) == 1
                and not fonksiyonlar[a].args.defaults}

    sebepler = []
    if ham_tohumlar and not tohumlar:
        sebepler.append(
            "KIYAS TOHUMU VAR ama HICBIRI tek argumanli degil (%s) — durtme "
            "probu kosturulamaz." % ", ".join(sorted(ham_tohumlar)))
    eksik_t = [a for a in CAPA_TURETME if a not in turetme]
    if eksik_t:
        sebepler.append(
            "TURETME KUMESI CAPAYI TASIMIYOR (eksik: %s) — `build.py`'de para "
            "turetme noktasi tasinmis/yeniden adlandirilmis olabilir; kapi "
            "sessizce daralmak yerine OLCULEMEDI diyor." % ", ".join(eksik_t))
    eksik_k = [a for a in CAPA_KIYAS if a not in yuzey]
    if eksik_k:
        sebepler.append(
            "KIYAS YUZEYI CAPAYI TASIMIYOR (eksik: %s) — politika-turevli kiyas "
            "baska bir fonksiyona tasinmis olabilir." % ", ".join(eksik_k))
    return turetme, tohumlar, yuzey, sebepler


# ===========================================================================
# 2) FIKSTUR INDIRGEME (cagri yerinden statik sozluk)
# ===========================================================================
class Cozumleyici(object):
    """Bir dosyadaki cagri argumanini SABIT deger sozlugune indirger.

    🔴 SABIT OLMAYAN DEGER KUMEYE GIRMEZ. Bu, "turetilen fikstur yesil gecer"
    kuralinin YAPISAL karsiligidir: `p["eski_fiyat"] = _tl_metni(ilan_kurus(p))`
    gibi bir deger anahtari DUSURUR, fikstur o eksende politika-bagimsiz olur
    ve durtme testi onu hic yakmaz. Ayri bir "muafiyet listesi" gerekmez."""

    def __init__(self, agac):
        self.agac = agac
        self.fonksiyonlar = {d.name: d
                             for d in ast.walk(agac)
                             if isinstance(d, (ast.FunctionDef,
                                               ast.AsyncFunctionDef))}

    # -- yardimcilar --------------------------------------------------------
    @staticmethod
    def _sabit(dugum):
        """(bulundu, deger) — yalniz gercek sabitler."""
        if isinstance(dugum, ast.Constant):
            return True, dugum.value
        return False, None

    def _dict_indirge(self, dugum):
        fx, dusen = {}, set()
        for anahtar, deger in zip(dugum.keys, dugum.values):
            if not isinstance(anahtar, ast.Constant) or \
                    not isinstance(anahtar.value, str):
                continue
            var, dg = self._sabit(deger)
            if var:
                fx[anahtar.value] = dg
            else:
                dusen.add(anahtar.value)
        return fx, dusen

    def _govde_sabitleri(self, fn):
        """Bir yardimci fonksiyonun TABAN fiksturu: govdesindeki dict literalleri
        + `p["k"] = <sabit>` atamalari. Sabit olmayan atama anahtari DUSURUR."""
        fx, dusen = {}, set()
        for alt in ast.walk(fn):
            if isinstance(alt, ast.Dict):
                a, d = self._dict_indirge(alt)
                fx.update(a)
                dusen |= d
            elif isinstance(alt, ast.Assign):
                for hedef in alt.targets:
                    if isinstance(hedef, ast.Subscript) and \
                            isinstance(hedef.slice, ast.Constant) and \
                            isinstance(hedef.slice.value, str):
                        var, dg = self._sabit(alt.value)
                        if var:
                            fx[hedef.slice.value] = dg
                        else:
                            dusen.add(hedef.slice.value)
        for k in dusen:
            fx.pop(k, None)
        return fx, dusen

    def _cagri_indirge(self, dugum, derinlik):
        """`_urun(eski_fiyat="800 TL")` -> taban govde sabitleri + kwargs."""
        f = dugum.func
        ad = f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else None)
        if ad is None or ad not in self.fonksiyonlar:
            return None, set()
        fx, dusen = self._govde_sabitleri(self.fonksiyonlar[ad])
        for kw in dugum.keywords:
            if kw.arg is None:          # **ek — icerigi cagri yerinde bilinmez
                continue
            var, dg = self._sabit(kw.value)
            if var:
                fx[kw.arg] = dg
            else:
                fx.pop(kw.arg, None)
                dusen.add(kw.arg)
        return fx, dusen

    def _ad_indirge(self, ad, kapsam, cagri_satiri, derinlik):
        """Kapsamda `ad`a yapilan SON atamayi (cagri satirindan ONCE) coz."""
        secili = None
        alt_atamalar = {}
        for dugum in ast.walk(kapsam):
            if isinstance(dugum, ast.Assign):
                satir = getattr(dugum, "lineno", 0)
                if satir >= cagri_satiri:
                    continue
                for hedef in dugum.targets:
                    if isinstance(hedef, ast.Name) and hedef.id == ad:
                        if secili is None or satir > secili[0]:
                            secili = (satir, dugum.value)
                    elif isinstance(hedef, ast.Subscript) and \
                            isinstance(hedef.value, ast.Name) and \
                            hedef.value.id == ad and \
                            isinstance(hedef.slice, ast.Constant) and \
                            isinstance(hedef.slice.value, str):
                        alt_atamalar[hedef.slice.value] = (satir, dugum.value)
        if secili is None:
            return None, set()
        fx, dusen = self.indirge(secili[1], kapsam, cagri_satiri, derinlik + 1)
        if fx is None:
            return None, dusen
        for anahtar, (_satir, deger) in alt_atamalar.items():
            var, dg = self._sabit(deger)
            if var:
                fx[anahtar] = dg
            else:
                fx.pop(anahtar, None)
                dusen.add(anahtar)
        return fx, dusen

    # -- giris --------------------------------------------------------------
    def indirge(self, dugum, kapsam, cagri_satiri, derinlik=0):
        if derinlik > COZUM_DERINLIGI:
            return None, set()
        if isinstance(dugum, ast.Dict):
            return self._dict_indirge(dugum)
        if isinstance(dugum, ast.Call):
            return self._cagri_indirge(dugum, derinlik)
        if isinstance(dugum, ast.Name):
            return self._ad_indirge(dugum.id, kapsam, cagri_satiri, derinlik)
        return None, set()


def _kapsam_haritasi(agac):
    """Her dugume en yakin fonksiyon/modul kapsamini isaretle."""
    harita = {}

    def gez(dugum, kapsam):
        for alt in ast.iter_child_nodes(dugum):
            yeni = alt if isinstance(alt, (ast.FunctionDef,
                                           ast.AsyncFunctionDef)) else kapsam
            harita[alt] = yeni
            gez(alt, yeni)
    harita[agac] = agac
    gez(agac, agac)
    return harita


def dosya_fiksturleri(yol, kaynak, yuzey):
    """[(satir, fonksiyon_adi, fikstur, dusen_anahtarlar)] — cozulemeyen atlanir.

    Ikinci donus: cozulemeyen cagri sayisi (raporda BASILIR — sessiz kirpma
    "hepsini kapsadim" diye okunur)."""
    try:
        agac = ast.parse(kaynak)
    except SyntaxError:
        return None, 0
    harita = _kapsam_haritasi(agac)
    cozumleyici = Cozumleyici(agac)
    bulgular, cozulemeyen = [], 0
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Call) or not dugum.args:
            continue
        f = dugum.func
        ad = f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else None)
        if ad not in yuzey:
            continue
        kapsam = harita.get(dugum, agac)
        fx, dusen = cozumleyici.indirge(dugum.args[0], kapsam,
                                        getattr(dugum, "lineno", 0) + 1)
        if fx is None:
            cozulemeyen += 1
            continue
        bulgular.append((getattr(dugum, "lineno", 0), ad, fx, dusen))
    return bulgular, cozulemeyen


# ===========================================================================
# 3) POLITIKA DURTMESI — hukmu URETIM fonksiyonu verir
# ===========================================================================
def build_modulu():
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import build                                     # noqa: E402
    return build


def _tohum_ciktilari(build, tohumlar, fx):
    """Tek argumanli tohum yuzeylerin bu fikstur icin ciktisi."""
    cikti = []
    for ad in sorted(tohumlar):
        fn = getattr(build, ad, None)
        if fn is None:
            continue
        try:
            cikti.append((ad, repr(fn(dict(fx)))))
        except TypeError:
            continue                                 # arity != 1 -> tohum degil
        except Exception as exc:                     # noqa: BLE001
            cikti.append((ad, "HATA:%s" % type(exc).__name__))
    return cikti


def politikaya_bagli_mi(build, tohumlar, fx):
    """🔴 KAPININ CEKIRDEGI. `_birim_kurus` IKI YONLU olceklenince tohum
    yuzeylerin ciktisi DEGISIYOR mu? Degisiyorsa fiksturun hukmu politikaya
    baglidir -> sabit literal K106'nin tekrari demektir.

    Olcekleme TEK TURETME NOKTASINDA yapilir: `ilan_kurus`/`vitrin_kurus`
    modul global'i uzerinden cagirdigi icin yama ikisini de kapsar."""
    taban = _tohum_ciktilari(build, tohumlar, fx)
    if not taban:
        return False, taban
    orijinal = build._birim_kurus
    try:
        for katsayi in DURTME_KATSAYILARI:
            def sahte(p, malzeme, _k=katsayi, _o=orijinal):
                deger = _o(p, malzeme)
                return None if deger is None else max(1, int(deger * _k))
            build._birim_kurus = sahte
            if _tohum_ciktilari(build, tohumlar, fx) != taban:
                return True, taban
    finally:
        build._birim_kurus = orijinal
    return False, taban


def sabit_para_anahtarlari(fx):
    """Fiksturdeki SABIT + para bicimli deger anahtarlari (raporlama)."""
    return sorted(k for k, v in fx.items()
                  if isinstance(v, str) and PARA_BICIMI.search(v))


# ===========================================================================
# 4) TARAMA
# ===========================================================================
def taranacak_dosyalar(kok):
    yollar = []
    for dizin, alt_dizinler, dosyalar in os.walk(os.path.join(kok, "tools")):
        alt_dizinler[:] = [d for d in alt_dizinler if d != "__pycache__"]
        for ad in dosyalar:
            if not ad.endswith(".py"):
                continue
            tam = os.path.join(dizin, ad)
            rel = os.path.relpath(tam, kok).replace(os.sep, "/")
            if rel in HARIC_YOLLAR or rel.startswith(HARIC_ONEKLER):
                continue
            yollar.append((rel, tam))
    return sorted(yollar)


def tara(kok=None, build=None, kumeler=None):
    """(satirlar, rc) — rc 0 YESIL · 1 UYARI · 2 OLCULEMEDI."""
    kok = kok or ROOT
    satirlar = []
    turetme, tohumlar, yuzey, sebepler = kumeler or kanonik_kumeler()
    if sebepler:
        satirlar.append("PARA LITERALI KAPISI — OLCULEMEDI")
        satirlar.extend("  ⚪ " + s for s in sebepler)
        satirlar.append("SONUC: OLCULEMEDI")
        return satirlar, 2

    if build is None:
        try:
            build = build_modulu()
        except Exception as exc:                     # noqa: BLE001
            satirlar.append("PARA LITERALI KAPISI — OLCULEMEDI")
            satirlar.append("  ⚪ build.py ice aktarilamadi: %s: %s"
                            % (type(exc).__name__, exc))
            satirlar.append("SONUC: OLCULEMEDI")
            return satirlar, 2

    uyarilar, dosya_sayisi, cagri_sayisi, fikstur_sayisi, cozulemeyen = \
        [], 0, 0, 0, 0
    ayrist_hatasi = []
    for rel, tam in taranacak_dosyalar(kok):
        with io.open(tam, encoding="utf-8", errors="replace") as f:
            kaynak = f.read()
        if not any(ad in kaynak for ad in yuzey):
            continue
        dosya_sayisi += 1
        bulgular, atlanan = dosya_fiksturleri(rel, kaynak, yuzey)
        if bulgular is None:
            ayrist_hatasi.append(rel)
            continue
        cozulemeyen += atlanan
        cagri_sayisi += len(bulgular) + atlanan
        for satir, yuzey_adi, fx, _dusen in bulgular:
            fikstur_sayisi += 1
            anahtarlar = sabit_para_anahtarlari(fx)
            if not anahtarlar:
                continue
            bagli, _taban = politikaya_bagli_mi(build, tohumlar, fx)
            if bagli:
                uyarilar.append((rel, satir, yuzey_adi, anahtarlar,
                                 {k: fx[k] for k in anahtarlar}))

    satirlar.append("PARA LITERALI KAPISI (K107) — kabul fiksturunde politika-"
                    "turevli kiyasa giren SABIT para degeri")
    satirlar.append("  TURETME kumesi : %s" % ", ".join(sorted(turetme)))
    satirlar.append("  KIYAS TOHUMLARI: %s" % ", ".join(sorted(tohumlar)))
    satirlar.append("  KIYAS YUZEYI   : %d fonksiyon" % len(yuzey))
    for rel, satir, yuzey_adi, anahtarlar, degerler in uyarilar:
        satirlar.append(
            "  ⚠️  %s:%d — `%s(...)` fiksturunun hukmu POLITIKAYA BAGLI ama "
            "para degeri SABIT: %s"
            % (rel, satir, yuzey_adi,
               ", ".join("%s=%r" % (k, degerler[k]) for k in anahtarlar)))
        satirlar.append(
            "      COZUM: degeri kiyasin KENDI kaynagindan turet "
            "(`build.ilan_kurus(p)` / `build.vitrin_kurus(p)`) + pay ekle. "
            "K106'da bu sinif yayini 7,5 saat durdurdu.")
    for rel in ayrist_hatasi:
        satirlar.append("  ⚪ AYRISTIRILAMADI (kapsam disi kaldi): %s" % rel)
    satirlar.append(
        "PARA_LITERALI_KAPISI DOSYA=%d CAGRI=%d FIKSTUR=%d UYARI=%d "
        "COZULEMEYEN=%d AYRISTIRILAMAYAN=%d"
        % (dosya_sayisi, cagri_sayisi, fikstur_sayisi, len(uyarilar),
           cozulemeyen, len(ayrist_hatasi)))
    if ayrist_hatasi:
        satirlar.append("SONUC: OLCULEMEDI")
        return satirlar, 2
    satirlar.append("SONUC: %s" % ("KIRMIZI" if uyarilar else "YESIL"))
    return satirlar, (1 if uyarilar else 0)


# ===========================================================================
# 5) KENDINI-TEST — hermetik fiksturler (repoya YAZMAZ)
# ===========================================================================
# 🔴 FIKSTUR SECIMI: 3 YAKALAMA + 5 YANLIS-POZITIF NOBETI. Yanlis-pozitif kolu
# olmayan bir kapi bu depoda kabul EDILEMEZ: bloklayici seride tasindiginda
# tek yanlis-pozitif tum ekibin yayinini durdurur ([[kapi-disiplin-ilkesi]]).
_ORTAK_BASLIK = (
    "def _urun(**ek):\n"
    "    p = {'id': 'x', 'kategori': 'Otomobil', 'fiyat': '850 TL'}\n"
    "    p.update(ek)\n"
    "    return p\n"
    "\n"
    "def render_product(p, hepsi):\n"
    "    return ''\n"
    "\n")

FIKSTURLER = (
    # (ad, dosya govdesi, UYARI beklentisi, gerekce)
    ("Y1 sabit gecerli indirim (K106'nin BIREBIR sekli)",
     _ORTAK_BASLIK + "def kos():\n"
     "    p = _urun(eski_fiyat='1.200 TL')\n"
     "    render_product(p, [p])\n", True,
     "eski fiyat gecerli + SABIT -> hukum ilan_kurus'a bagli"),

    ("Y2 dogrudan dict literali",
     _ORTAK_BASLIK + "def kos():\n"
     "    render_product({'fiyat': '850 TL', 'eski_fiyat': '1.200 TL'}, [])\n",
     True, "yardimci olmadan da yakalanmali"),

    ("Y3 yerel ad + alt atama",
     _ORTAK_BASLIK + "def kos():\n"
     "    p = {'fiyat': '850 TL'}\n"
     "    p['eski_fiyat'] = '1.200 TL'\n"
     "    render_product(p, [p])\n", True,
     "ad cozumu + subscript atamasi"),

    ("N1 YANLIS-POZITIF NOBETI — deger ilan_kurus'tan TUREYOR",
     _ORTAK_BASLIK + "import build\n"
     "def kos():\n"
     "    p = _urun()\n"
     "    p['eski_fiyat'] = _tl(build.ilan_kurus(p) + 35000)\n"
     "    render_product(p, [p])\n", False,
     "MESRU fikstur YESIL gecmeli — kapinin varlik sarti"),

    ("N2 YANLIS-POZITIF NOBETI — eski fiyat guncelin ALTINDA",
     _ORTAK_BASLIK + "def kos():\n"
     "    p = _urun(eski_fiyat='800 TL')\n"
     "    render_product(p, [p])\n", False,
     "negatif vaka: politikadan BAGIMSIZ olarak reddedilir"),

    ("N3 YANLIS-POZITIF NOBETI — baska para birimi",
     _ORTAK_BASLIK + "def kos():\n"
     "    p = _urun(eski_fiyat='1200 USD')\n"
     "    render_product(p, [p])\n", False,
     "ayristirici zaten reddediyor; politika devreye GIRMIYOR"),

    ("N4 YANLIS-POZITIF NOBETI — parametrik urun (erken cikis)",
     _ORTAK_BASLIK + "def kos():\n"
     "    p = _urun(eski_fiyat='1.200 TL', parametrik=True)\n"
     "    render_product(p, [p])\n", False,
     "parametrik/konfigur kolu politikayi hic sormaz"),

    ("N5 YANLIS-POZITIF NOBETI — ilgisiz rutin dosya (eski_fiyat YOK)",
     _ORTAK_BASLIK + "def kos():\n"
     "    p = _urun()\n"
     "    render_product(p, [p])\n", False,
     "para literali (fiyat) VAR ama kiyas ekseni ATIL -> yesil"),
)


def _fikstur_kokunu_kur(gecici, govde):
    """Sentetik `tools/` agaci — CANLI REPOYA DOKUNMAZ."""
    tools = os.path.join(gecici, "tools")
    os.makedirs(tools, exist_ok=True)
    with io.open(os.path.join(tools, "sentetik-fikstur-test.py"),
                 "w", encoding="utf-8") as f:
        f.write(govde)
    return gecici


def kendini_test(build=None, kumeler=None, tara_fn=None):
    tara_fn = tara_fn or tara
    if kumeler is None:
        kumeler = kanonik_kumeler()
    if kumeler[3]:
        return 2, ["OLCULEMEDI: " + s for s in kumeler[3]], {}
    if build is None:
        build = build_modulu()

    hatalar, hukumler = [], {}
    gecici = tempfile.mkdtemp(prefix="k107-fikstur-")
    try:
        for ad, govde, uyari_bekleniyor, gerekce in FIKSTURLER:
            kok = os.path.join(gecici, re.sub(r"[^A-Za-z0-9]", "_", ad))
            os.makedirs(kok, exist_ok=True)
            _fikstur_kokunu_kur(kok, govde)
            satirlar, rc = tara_fn(kok=kok, build=build, kumeler=kumeler)
            uyardi = (rc == 1)
            hukumler[ad] = uyardi
            if uyardi != uyari_bekleniyor:
                hatalar.append(
                    "%s: UYARI=%s beklenen=%s (%s)\n      %s"
                    % (ad, uyardi, uyari_bekleniyor, gerekce,
                       "\n      ".join(satirlar[-3:])))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)   # 🧹 makinede iz birakma
    return (1 if hatalar else 0), hatalar, hukumler


# ===========================================================================
# 6) MUTASYON — IKI YONLU, her mutant hedef kolu AYRICA kanitlar
# ===========================================================================
# 🔴 K182: "mutant yakalandi" YETMEZ; mutantin HANGI KOLU oldurdugu de
# olculur. Her mutant icin (a) YAKALANDI mi, (b) HANGI fiksturlerin hukmu
# degisti, (c) bu degisim mutantin HEDEF KOLUYLA ortusuyor mu yazilir.
#
# YON 1 (TESPIT kolu oldurulur): Y1/Y2/Y3 sessizlesmeli.
# YON 2 (YANLIS-POZITIF BASTIRMA kolu oldurulur): N2..N5 kirmiziya donmeli.
# Iki yon de sart: yalniz YON 1 olculseydi, kapinin FP kolu tamamen olu olsa
# bile mutant tablosu YESIL kalirdi ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).

def _mutant_sabit_kor(cozumleyici_sinifi):
    """M1 — TESPIT KOLU: hicbir deger SABIT sayilmaz."""
    class M(cozumleyici_sinifi):
        @staticmethod
        def _sabit(dugum):
            return False, None
    return M


def _mutant_durtme_hep_bagli(build, tohumlar):
    """M2 — YANLIS-POZITIF BASTIRMA KOLU: her fikstur politikaya bagli sayilir."""
    def sahte(_build, _tohumlar, _fx):
        return True, []
    return sahte


def _mutant_durtme_hep_bagimsiz(build, tohumlar):
    """M3 — TESPIT KOLU: hicbir fikstur politikaya bagli sayilmaz."""
    def sahte(_build, _tohumlar, _fx):
        return False, []
    return sahte


MUTANTLAR = (
    ("M1 SABIT tespiti oldu (`_sabit` daima False)", "TESPIT",
     ("Y1", "Y2", "Y3")),
    ("M2 durtme daima BAGLI (yanlis-pozitif bastirma kolu oldu)", "FP",
     ("N2", "N3", "N4", "N5")),
    ("M3 durtme daima BAGIMSIZ (hukum kolu oldu)", "TESPIT",
     ("Y1", "Y2", "Y3")),
    ("M4 KIYAS YUZEYI bosaltildi (cagri yeri taramasi oldu)", "TESPIT",
     ("Y1", "Y2", "Y3")),
    ("M5 yardimci-fonksiyon hopu oldu (yalniz dict literali cozulur)", "TESPIT",
     ("Y1",)),
)

KONTROL_MUTANTI = "K0 no-op (para bicimi regex'ine zararsiz alternatif eklendi)"


def _kolla_tara(sabit_sinifi=None, durtme=None, yuzey_bos=False,
                cagri_hopu_yok=False, para_bicimi=None):
    """Mutasyon icin `tara`nin kablolarini gecici olarak degistiren sarmalayici."""
    global Cozumleyici, politikaya_bagli_mi, PARA_BICIMI
    eski = (Cozumleyici, politikaya_bagli_mi, PARA_BICIMI)

    def geri_al():
        globals()["Cozumleyici"] = eski[0]
        globals()["politikaya_bagli_mi"] = eski[1]
        globals()["PARA_BICIMI"] = eski[2]

    if sabit_sinifi is not None:
        globals()["Cozumleyici"] = sabit_sinifi
    if durtme is not None:
        globals()["politikaya_bagli_mi"] = durtme
    if para_bicimi is not None:
        globals()["PARA_BICIMI"] = para_bicimi
    if cagri_hopu_yok:
        class M(eski[0]):
            def _cagri_indirge(self, dugum, derinlik):
                return None, set()
        globals()["Cozumleyici"] = M
    return geri_al


def mutasyon():
    kumeler = kanonik_kumeler()
    if kumeler[3]:
        return 2, ["OLCULEMEDI: " + s for s in kumeler[3]]
    build = build_modulu()
    turetme, tohumlar, yuzey, sebepler = kumeler

    taban_rc, taban_hata, taban_hukum = kendini_test(build=build,
                                                     kumeler=kumeler)
    satirlar = []
    if taban_rc != 0:
        satirlar.append("🔴 TABAN KIRMIZI — mutasyon olculemez:")
        satirlar.extend("   " + h for h in taban_hata)
        return 2, satirlar

    def hukum_ozeti(yeni):
        return {ad.split()[0]: yeni[ad] for ad in yeni}

    taban_kisa = hukum_ozeti(taban_hukum)
    yakalanan = 0

    for etiket, kol, hedef_onekler in MUTANTLAR:
        kod = etiket.split()[0]
        if kod == "M1":
            geri = _kolla_tara(sabit_sinifi=_mutant_sabit_kor(Cozumleyici))
        elif kod == "M2":
            geri = _kolla_tara(durtme=_mutant_durtme_hep_bagli(build, tohumlar))
        elif kod == "M3":
            geri = _kolla_tara(
                durtme=_mutant_durtme_hep_bagimsiz(build, tohumlar))
        elif kod == "M4":
            geri = _kolla_tara()
            kumeler_m = (turetme, tohumlar, set(), [])
        elif kod == "M5":
            geri = _kolla_tara(cagri_hopu_yok=True)
        try:
            k = kumeler_m if kod == "M4" else kumeler
            rc, hatalar, hukum = kendini_test(build=build, kumeler=k)
        finally:
            geri()
            if kod == "M4":
                del kumeler_m
        kisa = hukum_ozeti(hukum)
        degisen = sorted(a for a in kisa if kisa[a] != taban_kisa.get(a))
        hedef_isabet = [a for a in degisen if a.startswith(hedef_onekler)]
        disari_tasan = [a for a in degisen if not a.startswith(hedef_onekler)]
        if rc == 0:
            satirlar.append("  ❌ %s — MUTANT SAG KALDI (kapi kor)" % etiket)
            continue
        if not hedef_isabet:
            satirlar.append("  ❌ %s — kirmizi yandi ama HEDEF KOL (%s) "
                            "degismedi: degisen=%s" % (etiket, kol, degisen))
            continue
        yakalanan += 1
        satirlar.append("  ✅ %s [kol=%s] — hedef fiksturler dondu: %s%s"
                        % (etiket, kol, ", ".join(hedef_isabet),
                           (" · yan etki: %s" % ", ".join(disari_tasan))
                           if disari_tasan else ""))

    # ---- KONTROL MUTANTI: davranisi DEGISTIRMEMELI -------------------------
    geri = _kolla_tara(para_bicimi=re.compile(
        r"[0-9][0-9.,]*\s*(?:TL|TRY|₺|ZZZ_OLMAYAN_BIRIM)", re.I))
    try:
        k_rc, _k_hata, k_hukum = kendini_test(build=build, kumeler=kumeler)
    finally:
        geri()
    kontrol_ok = (k_rc == 0 and hukum_ozeti(k_hukum) == taban_kisa)
    satirlar.append("  %s %s — %s"
                    % ("✅" if kontrol_ok else "❌", KONTROL_MUTANTI,
                       "davranis DEGISMEDI (duzenek gercekten hedefi olcuyor)"
                       if kontrol_ok else
                       "davranis DEGISTI -> mutant tablosu GURULTU olcuyor"))

    satirlar.append("MUTANT=%d/%d KONTROL=%d/1"
                    % (yakalanan, len(MUTANTLAR), 1 if kontrol_ok else 0))
    tam = (yakalanan == len(MUTANTLAR) and kontrol_ok)
    satirlar.append("SONUC: %s" % ("YESIL" if tam else "KIRMIZI"))
    return (0 if tam else 1), satirlar


# ===========================================================================
def main():
    argv = sys.argv[1:]
    if "--kendini-test" in argv:
        rc, hatalar, hukumler = kendini_test()
        print("PARA LITERALI KAPISI — KENDINI TEST (%d fikstur: %d yakalama + "
              "%d yanlis-pozitif nobeti)"
              % (len(FIKSTURLER),
                 sum(1 for f in FIKSTURLER if f[2]),
                 sum(1 for f in FIKSTURLER if not f[2])))
        for ad, _g, bekleniyor, gerekce in FIKSTURLER:
            gercek = hukumler.get(ad)
            isaret = "✅" if gercek == bekleniyor else "❌"
            print("  %s %-58s UYARI=%s  (%s)"
                  % (isaret, ad[:58], gercek, gerekce))
        for h in hatalar:
            print("  ❌ " + h)
        print("VAKA=%d/%d" % (len(FIKSTURLER) - len(hatalar), len(FIKSTURLER)))
        print("SONUC: %s" % ("YESIL" if rc == 0 else
                             ("OLCULEMEDI" if rc == 2 else "KIRMIZI")))
        return rc
    if "--mutasyon" in argv:
        rc, satirlar = mutasyon()
        print("PARA LITERALI KAPISI — MUTASYON (IKI YONLU: TESPIT kolu + "
              "YANLIS-POZITIF BASTIRMA kolu)")
        for s in satirlar:
            print(s)
        return rc
    satirlar, rc = tara()
    for s in satirlar:
        print(s)
    return rc


if __name__ == "__main__":
    sys.exit(main())

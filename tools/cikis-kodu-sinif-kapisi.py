#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SINIF KAPISI — "GOVDE KIRMIZI DIYORSA CIKIS KODU SIFIR OLAMAZ" (ve tersi).

=== NEDEN VAR (olculmus, 11 Eyl 2026) ===
Bu, bu evde UCUNCU kez ayni sinifta cikan arizadir; tekil yama YASAK, SINIF kapisi
yazilir ([[ucuncu-tekrar-sinif-kapisi]]).

  1. `tools/mimar-kapi-mutasyon-test.py` — "SONUC: KIRMIZI ... 39 mutasyon" basarken
     rc=0 sanildi ve is o varsayimla acildi. 🔴 KOSULARAK CURUTULDU: gercek rc **1**.
     Yanlis sayinin nereden geldigi de sinifin bir parcasi: rc bir BORUNUN ardindan
     okunursa borunun rc'si okunur ([[boru-rc-isci-olcumunu-yalanlar]]).
  2. `tools/ci-kapsam-test.py` — iki bacakli bataryada 13 ❌ basilirken rc=0 idi
     ([[vaka-sayisi-ekseni-cikis-kodu-eksenini-olcmez]]).
  3. Ayni tur: kabul bataryalari `SONUC: KIRMIZI` basip rc=0 ile CI'dan `success`
     gecebiliyordu — "yesil yanan olu test".

ORTAK SINIF: **cikis kodu govdenin sonucunu tasimiyor.** Bu kapi o sozlesmeyi
STATIK olarak (AST) olcer; bataryalari KOSTURMAZ (biri ~8 dk surer, CI'da her
push'ta kosturulamaz — olcum ucuz olmazsa kapatilir).

=== NE OLCER ===
Kayitli her dosyada, `print("SONUC: KIRMIZI ...")` (ya da `SONUC: OLCULEMEDI`)
cagrisindan SONRA, AYNI ifade blogunda (ya da onu iceren bloklar zincirinde) ilk
karsilasilan `sys.exit(X)` / `return X` degeri SIFIR OLMAMALI. Simetrik olarak
`SONUC: YESIL` sonrasi ilk cikis SIFIR OLMALI.

=== NE OLCMEZ (durust sinir) ===
* Dinamik yol: govde gercekten o dali KOSUYOR mu — olculmez. Statik sozlesme,
  "kirmizi dali rc=0 ile bitiyor" turunden bir YAZIM hatasini yakalar; erisilemez
  bir dali yakalamaz.
* Cikis degeri sabit degilse (degisken/ifade) hukum verilmez: `OLCULEMEDI` sayilir
  ve AYRI basilir — sessizce YESIL SAYILMAZ ([[fail-closed-kol-arkasindaki-kolu-
  maskeler]]).
* Kayit disi dosyalar taranmaz; KAYIT bu dosyadadir ve genisletilebilir.

KOSUM: `python3 tools/cikis-kodu-sinif-kapisi.py` (offline, dosya YAZMAZ, ~0,2 s)
KABUL: `python3 tools/cikis-kodu-sinif-kapisi.py --kendini-test`
CI:    `.github/workflows/nobet.yml::serit-b`
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🔴 KAYIT — sozlesmeyi tasimasi ZORUNLU bataryalar. Genisletilebilir; KISALTILAMAZ
# (kisaltma, kapiyi kapatmanin sessiz yoludur — [[tuketici-yazilirken-tum-okuyucular-
# sayilir]]). Dosya YOKSA kapi OLCULEMEDI basar, yesil saymaz.
KAYIT = (
    "mimar-kapi-mutasyon-test.py",
    "mimar-kilit-test.py",
    "hayali-nobetci-kapisi.py",
    "tikayici-kaldirma-test.py",
    "deploy-aclik-kapisi.py",
    "ic-rapor-adi-kapisi.py",
)

KIRMIZI_ONEKLERI = ("SONUC: KIRMIZI", "SONUC: OLCULEMEDI")
YESIL_ONEKLERI = ("SONUC: YESIL",)


def _ilk_dizge(dugum):
    """print(...) ilk argumaninin BASINDAKI sabit dizgeyi dondurur (yoksa None).

    `"a" + b`, `"a" % x`, f-string ve `"a".format(...)` bicimleri de okunur — govde
    metni bu evde bu dort bicimde yaziliyor; yalniz saf Constant arayan bir kol
    vakalarin cogunu SESSIZCE atlardi.
    """
    while True:
        if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str):
            return dugum.value
        if isinstance(dugum, ast.BinOp):           # "a" + x   /   "a" % x
            dugum = dugum.left
            continue
        if isinstance(dugum, ast.JoinedStr):       # f"..."
            if dugum.values and isinstance(dugum.values[0], ast.Constant):
                return dugum.values[0].value
            return None
        if (isinstance(dugum, ast.Call) and isinstance(dugum.func, ast.Attribute)
                and dugum.func.attr == "format"):  # "a".format(...)
            dugum = dugum.func.value
            continue
        return None


def _print_oneki(ifade):
    """Bir ifade `print("SONUC: ...")` ise o oneki dondurur, degilse None."""
    if not isinstance(ifade, ast.Expr) or not isinstance(ifade.value, ast.Call):
        return None
    cagri = ifade.value
    if not (isinstance(cagri.func, ast.Name) and cagri.func.id == "print"):
        return None
    if not cagri.args:
        return None
    return _ilk_dizge(cagri.args[0])


def _cikis_degeri(ifade):
    """`sys.exit(X)` / `exit(X)` / `return X` ise (True, X|None) dondurur.

    X sabit degilse deger None olur -> cagiran taraf OLCULEMEDI sayar.
    """
    hedef = None
    if isinstance(ifade, ast.Return):
        hedef = ifade.value
    elif isinstance(ifade, ast.Expr) and isinstance(ifade.value, ast.Call):
        c = ifade.value
        ad = (c.func.attr if isinstance(c.func, ast.Attribute)
              else (c.func.id if isinstance(c.func, ast.Name) else ""))
        if ad != "exit":
            return (False, None)
        hedef = c.args[0] if c.args else ast.Constant(value=0)
    else:
        return (False, None)
    if hedef is None:
        return (True, 0)                      # ciplak `return` -> None -> rc 0
    if isinstance(hedef, ast.Constant) and isinstance(hedef.value, int):
        return (True, hedef.value)
    return (True, None)                       # sabit degil -> OLCULEMEDI


def _blok_tara(govde, zincir, bulgular):
    """Bir ifade listesinde SONUC print'i ile onu izleyen ilk cikisi eslestirir."""
    bekleyen = None                            # (satir, sinif)
    for ifade in govde:
        onek = _print_oneki(ifade)
        if onek is not None:
            if onek.startswith(KIRMIZI_ONEKLERI):
                bekleyen = (ifade.lineno, "KIRMIZI")
            elif onek.startswith(YESIL_ONEKLERI):
                bekleyen = (ifade.lineno, "YESIL")
        if bekleyen is not None:
            cikis_mi, deger = _cikis_degeri(ifade)
            if cikis_mi:
                bulgular.append((bekleyen[0], bekleyen[1], deger))
                bekleyen = None
                continue
        # Ic bloklar AYRI taranir; ustteki bekleyen onlara TASINMAZ (yanlis eslesme
        # uretirdi: iki farkli dalin print'i ve cikisi birbirine baglanirdi).
        for alan in ("body", "orelse", "finalbody"):
            ic = getattr(ifade, alan, None)
            if isinstance(ic, list) and ic and isinstance(ic[0], ast.stmt):
                _blok_tara(ic, zincir + [ifade.lineno], bulgular)
        for tutucu in getattr(ifade, "handlers", []) or []:
            _blok_tara(tutucu.body, zincir + [ifade.lineno], bulgular)
    if bekleyen is not None:
        # print var, ayni blokta cikis YOK -> fonksiyon sonuna dusuyor olabilir.
        bulgular.append((bekleyen[0], bekleyen[1], "CIKIS-YOK"))


def tara(yollar):
    """[(dosya, satir, sinif, deger)] — sozlesme ihlalleri + olculemeyenler."""
    ihlal = []
    olculemedi = []
    eksik = []
    sayim = 0
    for yol in yollar:
        if not os.path.exists(yol):
            eksik.append(os.path.basename(yol))
            continue
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read(), filename=yol)
        bulgular = []
        # 🔴 TEK GECIS: `_blok_tara` her ifadenin `body/orelse/finalbody` alanlarina
        # ZATEN iner — FunctionDef de bir ifadedir. Ayrica bir `ast.walk` ile
        # fonksiyonlari ikinci kez taramak HER IDDIAYI CIFTLERDI (olculdu: 10 fikstur,
        # hepsi 2x); ciftlenen sayi "daha cok koruma" gibi okunur, oysa ayni dali iki
        # kez sayan bir kapidir ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).
        _blok_tara(agac.body, [], bulgular)
        ad = os.path.basename(yol)
        for satir, sinif, deger in bulgular:
            sayim += 1
            if deger is None or deger == "CIKIS-YOK":
                olculemedi.append((ad, satir, sinif, deger))
            elif sinif == "KIRMIZI" and deger == 0:
                ihlal.append((ad, satir, sinif, deger))
            elif sinif == "YESIL" and deger != 0:
                ihlal.append((ad, satir, sinif, deger))
    return ihlal, olculemedi, eksik, sayim


def main(argv):
    if "--kendini-test" in argv:
        return kendini_test()
    yollar = [a for a in argv if a.endswith(".py")]
    if not yollar:
        yollar = [os.path.join(KOK, "tools", a) for a in KAYIT]
    ihlal, olculemedi, eksik, sayim = tara(yollar)
    for ad, satir, sinif, deger in ihlal:
        print("IHLAL %s:%d  govde=%s  cikis=%s" % (ad, satir, sinif, deger))
    for ad, satir, sinif, deger in olculemedi:
        print("OLCULEMEDI %s:%d  govde=%s  cikis=%s" % (ad, satir, sinif, deger))
    for ad in eksik:
        print("EKSIK DOSYA %s (kayitta var, diskte YOK)" % ad)
    print("")
    print("IDDIA=%d  IHLAL=%d  OLCULEMEDI=%d  EKSIK_DOSYA=%d"
          % (sayim, len(ihlal), len(olculemedi), len(eksik)))
    if ihlal:
        print("SONUC: KIRMIZI — %d yerde cikis kodu govdenin sonucunu TASIMIYOR."
              % len(ihlal))
        return 1
    if eksik or olculemedi:
        print("SONUC: OLCULEMEDI — %d eksik dosya + %d sabit-olmayan cikis; hukum "
              "GUVENILIR DEGIL." % (len(eksik), len(olculemedi)))
        return 2
    print("SONUC: YESIL — %d SONUC dali, hepsinde cikis kodu govdeyle uyumlu." % sayim)
    return 0


# ===========================================================================
# KENDINI TEST — fikstur + mutasyon. Mutantlar YALNIZ gecici kopyalarda kosar;
# GERCEK batarya dosyalarina DOKUNULMAZ, gercek ev yolunda hicbir sey SILINMEZ.
# ===========================================================================

FIKSTURLER = {
    "G1-kirmizi-rc1": ('import sys\ndef f():\n    print("SONUC: KIRMIZI - x")\n'
                       '    sys.exit(1)\n', 0, 0, "kirmizi -> rc1: SOZLESME TAM"),
    "G2-kirmizi-rc0": ('import sys\ndef f():\n    print("SONUC: KIRMIZI - x")\n'
                       '    sys.exit(0)\n', 1, 0, "🔴 kirmizi -> rc0: FAIL-OPEN"),
    "G3-yesil-rc0": ('import sys\ndef f():\n    print("SONUC: YESIL - x")\n'
                     '    sys.exit(0)\n', 0, 0, "yesil -> rc0: SOZLESME TAM"),
    "G4-yesil-rc1": ('import sys\ndef f():\n    print("SONUC: YESIL - x")\n'
                     '    sys.exit(1)\n', 1, 0, "🔴 yesil -> rc1: TERS YON"),
    "G5-degisken": ('import sys\ndef f():\n    print("SONUC: KIRMIZI - x")\n'
                    '    sys.exit(kod)\n', 0, 1, "sabit degil -> OLCULEMEDI"),
    "G6-return": ('def f():\n    print("SONUC: KIRMIZI - x")\n    return 0\n',
                  1, 0, "return 0 de cikis kodudur"),
    "G7-bicimli": ('import sys\ndef f():\n    print("SONUC: KIRMIZI - %d" % n)\n'
                   '    sys.exit(0)\n', 1, 0, "'%' bicimli metin de okunur"),
    "G8-format": ('import sys\ndef f():\n    print("SONUC: KIRMIZI {}".format(n))\n'
                  '    sys.exit(0)\n', 1, 0, "'.format()' bicimi de okunur"),
    "G9-ic-blok": ('import sys\ndef f():\n    if x:\n'
                   '        print("SONUC: KIRMIZI - x")\n        sys.exit(0)\n',
                   1, 0, "ic blok (if govdesi) de taranir"),
    "G10-sonucsuz": ('import sys\ndef f():\n    print("hicbir sey")\n    sys.exit(0)\n',
                     0, 0, "SONUC dali YOK -> iddia YOK"),
}

MUTANTLAR = (
    ("MC1-kirmizi-kolu-olur",
     'elif sinif == "KIRMIZI" and deger == 0:',
     'elif False:',
     "G2-kirmizi-rc0", "G4-yesil-rc1",
     "kirmizi kolu olurse FAIL-OPEN fikstur yesillenir"),
    ("MC2-yesil-kolu-olur",
     'elif sinif == "YESIL" and deger != 0:',
     'elif False:',
     "G4-yesil-rc1", "G2-kirmizi-rc0",
     "ters yon kolu olurse yesil/rc1 gorunmez"),
    ("MC3-olculemedi-yutulur",
     'if deger is None or deger == "CIKIS-YOK":',
     'if False:',
     "G5-degisken", "G1-kirmizi-rc1",
     "sabit-olmayan cikis yutulursa OLCULEMEDI sifira duser (sahte yesil)"),
    ("MC4-bicim-kolu-olur",
     'if isinstance(dugum, ast.BinOp):           # "a" + x   /   "a" % x',
     'if False:',
     "G7-bicimli", "G1-kirmizi-rc1",
     "'%' bicimli metin okunmazsa o dal GORUNMEZ olur"),
    ("MC5-ic-blok-kolu-olur",
     'if isinstance(ic, list) and ic and isinstance(ic[0], ast.stmt):',
     'if False:',
     "G9-ic-blok", "G1-kirmizi-rc1",
     "ic bloklar taranmazsa if/try icindeki dallar GORUNMEZ"),
    ("MCK-KONTROL-bicimsel",
     'print("IHLAL %s:%d  govde=%s  cikis=%s"',
     'print("IHLAL %s:%d govde=%s cikis=%s"',
     None, None,
     "KONTROL: yalniz bicim degisir -> hicbir fikstur bozulmamali"),
)

META_MUTANTLARI = (
    ("MEC1-rc-kolu-duzlesir",
     '              % len(ihlal))\n        return 1',
     '              % len(ihlal))\n        return 0',
     "IHLAL>0 iken rc=0 -> B1 kolu yakalamali"),
)


def _kopya_kur(dizin, eski=None, yeni=None):
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        govde = f.read()
    if eski is not None:
        ayrac = "\nMUTANTLAR = ("
        icra, tablo = govde.split(ayrac, 1)
        if icra.count(eski) != 1:
            raise AssertionError("CAPA ICRA GOVDESINDE TEK DEGIL (%d): %r"
                                 % (icra.count(eski), eski[:60]))
        govde = icra.replace(eski, yeni) + ayrac + tablo
    yol = os.path.join(dizin, "kapi-kopya.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde)
    return yol


def _kos(kapi, fikstur):
    p = subprocess.run([sys.executable, kapi, fikstur], capture_output=True, text=True)
    ihlal = olculemedi = -1
    for s in p.stdout.splitlines():
        if s.startswith("IDDIA="):
            for parca in s.split():
                if parca.startswith("IHLAL="):
                    ihlal = int(parca.split("=")[1])
                elif parca.startswith("OLCULEMEDI="):
                    olculemedi = int(parca.split("=")[1])
    return ihlal, olculemedi, p.returncode


def kendini_test():
    gecici = tempfile.mkdtemp(prefix="cikis-kodu-kabul-")
    basarisiz = []
    iddia = 0
    try:
        fx = {}
        for ad, (govde, _bi, _bo, _a) in FIKSTURLER.items():
            yol = os.path.join(gecici, "fx", ad + ".py")
            os.makedirs(os.path.dirname(yol), exist_ok=True)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(govde)
            fx[ad] = yol
        taban = _kopya_kur(gecici)

        for ad, (_g, b_ihlal, b_olc, aciklama) in FIKSTURLER.items():
            ihlal, olc, _rc = _kos(taban, fx[ad])
            iddia += 1
            tamam = ihlal == b_ihlal and olc == b_olc
            print("A %-18s ihlal=%d/%d olculemedi=%d/%d  %s  %s"
                  % (ad, ihlal, b_ihlal, olc, b_olc, "GECTI" if tamam else "❌", aciklama))
            if not tamam:
                basarisiz.append("A/" + ad)

        # B: CIKIS KODU IKI YONLU CIVILI — ①'in ta kendisi.
        ihlal, _olc, rc = _kos(taban, fx["G2-kirmizi-rc0"])
        iddia += 1
        tamam = ihlal > 0 and rc != 0
        print("B1 ihlal>0 -> rc!=0   ihlal=%d rc=%d  %s" % (ihlal, rc,
                                                            "GECTI" if tamam else "❌"))
        if not tamam:
            basarisiz.append("B1")
        ihlal, olc, rc = _kos(taban, fx["G1-kirmizi-rc1"])
        iddia += 1
        tamam = ihlal == 0 and olc == 0 and rc == 0
        print("B2 ihlal=0 -> rc=0    ihlal=%d rc=%d  %s" % (ihlal, rc,
                                                            "GECTI" if tamam else "❌"))
        if not tamam:
            basarisiz.append("B2")

        for ad, eski, yeni, hedef, komsu, aciklama in MUTANTLAR:
            d = os.path.join(gecici, "mut", ad)
            os.makedirs(d, exist_ok=True)
            mut = _kopya_kur(d, eski, yeni)
            iddia += 1
            if hedef is None:
                bozulan = [f_ad for f_ad, (_g, bi, bo, _a) in FIKSTURLER.items()
                           if _kos(mut, fx[f_ad])[:2] != (bi, bo)]
                tamam = not bozulan
                print("C %-24s KONTROL bozulan=%d  %s  %s"
                      % (ad, len(bozulan), "GECTI" if tamam else "❌", aciklama))
            else:
                h = _kos(mut, fx[hedef])[:2]
                k = _kos(mut, fx[komsu])[:2]
                oldu = h != FIKSTURLER[hedef][1:3]
                yasadi = k == FIKSTURLER[komsu][1:3]
                tamam = oldu and yasadi
                print("C %-24s hedef(%s)=%s komsu(%s)=%s  %s  %s"
                      % (ad, hedef, "OLDU" if oldu else "YASADI", komsu,
                         "YESIL" if yasadi else "BOZULDU",
                         "GECTI" if tamam else "❌", aciklama))
            if not tamam:
                basarisiz.append("C/" + ad)

        for ad, eski, yeni, aciklama in META_MUTANTLARI:
            d = os.path.join(gecici, "meta", ad)
            os.makedirs(d, exist_ok=True)
            mut = _kopya_kur(d, eski, yeni)
            ihlal, _olc, rc = _kos(mut, fx["G2-kirmizi-rc0"])
            iddia += 1
            tamam = ihlal > 0 and rc == 0
            print("D %-24s ihlal=%d rc=%d  %s  %s"
                  % (ad, ihlal, rc, "GECTI (B1 yakalar)" if tamam else "❌", aciklama))
            if not tamam:
                basarisiz.append("D/" + ad)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("")
    if basarisiz:
        print("SONUC: KIRMIZI — %d/%d iddia dustu: %s"
              % (len(basarisiz), iddia, ", ".join(basarisiz)))
        return 1
    print("SONUC: YESIL — %d iddia kosuldu (%d fikstur + 2 cikis-kodu kolu + %d mutant "
          "(1'i KONTROL) + %d meta mutant)."
          % (iddia, len(FIKSTURLER), len(MUTANTLAR), len(META_MUTANTLARI)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

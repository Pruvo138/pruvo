#!/usr/bin/env python3
"""B8 KABUL BATARYASI — turun sayac etkisi TEK KAPIDAN gecer mi?

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B8 (K241 UCUNCU yuzeyi).
KANONIK KAYNAK: pruvo deposu `tools/n4b/nobet-sayac-cikis-yollari-test.py`.

KOSUM:  python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
KABUL:  son satir `KABUL=GECTI (n/n vaka)` ve rc=0.
CAGRI YERI: `testler.py` PAKETLER listesi.

OLCULEN KABUL MADDELERI
  1) tur kosar + onarim uretir -> sayac 0'a duser        -> S1 + S3d (+ mutant N4)
  2) tur kosar + DUSER (SURE_TAVANI dahil) -> sayac +1   -> S2 E2/E3/E4
  3) tur ATLANDI (kilit dolu) -> sayac DEGISMEZ          -> S2 E1
  4) Mutant: erken `return` sayaci yeniden atlarsa KIRMIZI -> S4 N1
  5) Cikis yollari ENVANTERI, sayi CIVILI                -> S3

🔴 KABUL-1'IN ATIF ZINCIRI (durustluk notu): pozitif kol TAM ENTEGRASYONLA
(gercek `tur_kapat` + gercek defter) DEGIL, UC HALKALI olcumle kanitlanir:
  (a) S1  — kapinin KOSTU_ONARDI semantigi sayaci GERCEKTEN sifirliyor,
  (b) S3c — `ustuste_onarimsiz_guncelle` modulde TEK yerden cagriliyor
            (yani `tur_kapat`'in baska bir yolu YOK),
  (c) S3d — `tur_kapat` kapiya `onarim > 0` kosuluyla KOSTU_ONARDI veriyor,
  (d) N4  — o kosul bozulunca S3d KIRMIZI yaniyor (kol OLU degil).
Tam entegrasyon icin defter/geri-iz fiksturu gerekir; AYRI KALEM olarak bildirildi.
"""

import ast
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")

CIVILI_RETURN = 5          # tur_kos cikis yolu sayisi — CIVILI

VAKALAR = []


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-34s BEKLENEN=%-18s OLCULEN=%-18s SONUC=%s"
          % (vid, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


def modul_yukle(yol, ad):
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


def sayac_yaz(yol, deger):
    with open(yol, "w", encoding="utf-8") as dosya:
        json.dump({"ustuste_onarimsiz": deger}, dosya)


def sayac_oku(yol):
    try:
        with open(yol, encoding="utf-8") as dosya:
            return int(json.load(dosya).get("ustuste_onarimsiz", -1))
    except (OSError, ValueError, TypeError):
        return -1


# ===========================================================================
# S1 — KAPININ KENDISI (saf, uc hal)
# ===========================================================================

def bolum_s1(kapi, tmp, ek=""):
    print("--- BOLUM S1%s: TEK KAPI SEMANTIGI ---" % ek)
    yol = os.path.join(tmp, "s1%s.json" % ek)

    sayac_yaz(yol, 7)
    yeni, yazildi = kapi.tur_sayacini_kaydet("KOSTU_ONARDI", 2, yol=yol)
    vaka("S1a-onardi-sifirlar%s" % ek, "0,True", "%s,%s" % (yeni, yazildi))
    vaka("S1b-onardi-diskte%s" % ek, 0, sayac_oku(yol))

    sayac_yaz(yol, 7)
    yeni, yazildi = kapi.tur_sayacini_kaydet("KOSTU_DUSTU", 0, yol=yol)
    vaka("S1c-dustu-artirir%s" % ek, "8,True", "%s,%s" % (yeni, yazildi))
    vaka("S1d-dustu-diskte%s" % ek, 8, sayac_oku(yol))

    sayac_yaz(yol, 7)
    yeni, yazildi = kapi.tur_sayacini_kaydet("ATLANDI", 0, yol=yol)
    vaka("S1e-atlandi-degismez%s" % ek, "7,False", "%s,%s" % (yeni, yazildi))
    vaka("S1f-atlandi-diskte%s" % ek, 7, sayac_oku(yol))

    try:
        kapi.tur_sayacini_kaydet("BILINMEYEN", 0, yol=yol)
        hal = "SESSIZ_GECTI"
    except ValueError:
        hal = "ValueError"
    except Exception as hata:                       # noqa: BLE001
        hal = type(hata).__name__
    vaka("S1g-bilinmeyen-hal%s" % ek, "ValueError", hal)


# ===========================================================================
# S2 — tur_kos CIKIS YOLLARI (uctan uca, sahte bagimliliklarla)
# ===========================================================================

def _tur_kos_kolu(kapi, tmp, ek, kol, kilit_alindi, motor_var, zincir_sonucu):
    """Bir cikis yolunu kosar; (rc, sayac, stdout) doner."""
    sayac_yolu = os.path.join(tmp, "s2-%s%s.json" % (kol, ek))
    atlanan_yolu = os.path.join(tmp, "s2-atlanan-%s%s.json" % (kol, ek))
    sayac_yaz(sayac_yolu, 7)
    eski = {}
    for ad, deger in (
            ("ONARIMSIZ_SAYAC_YOLU", sayac_yolu),
            ("ATLANAN_SAYAC_YOLU", atlanan_yolu),
            ("kilit_al", lambda: (kilit_alindi, "ONCEKI_TUR_SURUYOR")),
            ("kilit_birak", lambda: True),
            ("_logu_kirp", lambda *a, **k: None),
            ("_defter_satir_sayisi", lambda *a, **k: 0),
            ("karantina_temizle_ve_oku", lambda *a, **k: set()),
            ("karantina_en_eski", lambda *a, **k: None),
            ("motor_ayakta", lambda m: motor_var),
            ("motor_zinciri_kos", lambda *a, **k: zincir_sonucu),
            ("tur_kapat", lambda **k: {"rc": 0, "rapor": "SAHTE_RAPOR"}),
    ):
        eski[ad] = getattr(kapi, ad)
        setattr(kapi, ad, deger)
    tampon = io.StringIO()
    try:
        with contextlib.redirect_stdout(tampon):
            rc = kapi.tur_kos()
    finally:
        for ad, deger in eski.items():
            setattr(kapi, ad, deger)
    return rc, sayac_oku(sayac_yolu), tampon.getvalue()


ZINCIR_TAVAN = {"cikti": "SURE_TAVANI_ASILDI=1 TAVAN_SN=1500\n",
                "denemeler": [], "hukum": "SURE_TAVANI", "motor": "m3"}
ZINCIR_MOTORSUZ = {"cikti": "", "denemeler": [], "hukum": "MOTOR_YOK",
                   "motor": None}
ZINCIR_NORMAL = {"cikti": "KAPANAN=1\nHUKUM=KAPANDI\n", "denemeler": [],
                 "hukum": "KAPANDI", "motor": "m3"}


def bolum_s2(kapi, tmp, ek=""):
    print("--- BOLUM S2%s: tur_kos CIKIS YOLLARI ---" % ek)

    rc, sayac, cikti = _tur_kos_kolu(kapi, tmp, ek, "e1", False, True, ZINCIR_NORMAL)
    vaka("S2-E1-atlandi-rc%s" % ek, 0, rc)
    vaka("S2-E1-atlandi-sayac%s" % ek, 7, sayac)
    vaka("S2-E1-atlandi-jeton%s" % ek, "VAR",
         "VAR" if "TUR_HALI=ATLANDI SEBEP=KILIT_DOLU" in cikti else "YOK")
    vaka("S2-E1-yazilmadi%s" % ek, "VAR",
         "VAR" if "SAYAC_YAZILDI=0" in cikti else "YOK")

    rc, sayac, cikti = _tur_kos_kolu(kapi, tmp, ek, "e2", True, True, ZINCIR_TAVAN)
    vaka("S2-E2-tavan-rc%s" % ek, 1, rc)
    vaka("S2-E2-tavan-sayac%s" % ek, 8, sayac)
    vaka("S2-E2-tavan-jeton%s" % ek, "VAR",
         "VAR" if "TUR_HALI=KOSTU_DUSTU SEBEP=SURE_TAVANI" in cikti else "YOK")

    rc, sayac, cikti = _tur_kos_kolu(kapi, tmp, ek, "e3", True, False, ZINCIR_NORMAL)
    vaka("S2-E3-motoryok-rc%s" % ek, 1, rc)
    vaka("S2-E3-motoryok-sayac%s" % ek, 8, sayac)
    vaka("S2-E3-motoryok-jeton%s" % ek, "VAR",
         "VAR" if "SEBEP=MOTOR_YOK_AYAKTA" in cikti else "YOK")

    rc, sayac, cikti = _tur_kos_kolu(kapi, tmp, ek, "e4", True, True, ZINCIR_MOTORSUZ)
    vaka("S2-E4-zincir-rc%s" % ek, 1, rc)
    vaka("S2-E4-zincir-sayac%s" % ek, 8, sayac)
    vaka("S2-E4-zincir-jeton%s" % ek, "VAR",
         "VAR" if "SEBEP=MOTOR_YOK_ZINCIR" in cikti else "YOK")

    rc, sayac, cikti = _tur_kos_kolu(kapi, tmp, ek, "e5", True, True, ZINCIR_NORMAL)
    vaka("S2-E5-normal-rc%s" % ek, 0, rc)
    vaka("S2-E5-normal-sahte-kapat%s" % ek, "VAR",
         "VAR" if "SAHTE_RAPOR" in cikti else "YOK")


# ===========================================================================
# S3 — CIKIS YOLU ENVANTERI (ast; sayi CIVILI)
# ===========================================================================

def _fonksiyon(agac, ad):
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef) and dugum.name == ad:
            return dugum
    return None


def _cagri_say(dugum, ad):
    n = 0
    for alt in ast.walk(dugum):
        if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name) \
                and alt.func.id == ad:
            n += 1
    return n


def bolum_s3(kaynak, ek=""):
    print("--- BOLUM S3%s: CIKIS YOLU ENVANTERI ---" % ek)
    agac = ast.parse(kaynak)
    fn = _fonksiyon(agac, "tur_kos")
    donusler = [d for d in ast.walk(fn)
                if isinstance(d, ast.Return)] if fn else []
    vaka("S3a-return-sayisi%s" % ek, CIVILI_RETURN, len(donusler))

    sabit0 = dustu = kapi_rc = diger = 0
    for d in donusler:
        v = d.value
        if isinstance(v, ast.Constant) and v.value == 0:
            sabit0 += 1
        elif isinstance(v, ast.Call) and isinstance(v.func, ast.Name) \
                and v.func.id == "_tur_dustu":
            dustu += 1
        elif isinstance(v, ast.Subscript):
            kapi_rc += 1
        else:
            diger += 1
    vaka("S3b-return-bicimleri%s" % ek, "0:1 dustu:3 kapi:1 diger:0",
         "0:%d dustu:%d kapi:%d diger:%d" % (sabit0, dustu, kapi_rc, diger))

    # S3c — sayac yazicisi modulde TEK yerden cagriliyor mu?
    yazici = 0
    sahip = "-"
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef):
            n = _cagri_say(dugum, "ustuste_onarimsiz_guncelle")
            if n:
                yazici += n
                sahip = dugum.name
    vaka("S3c-tek-yazici%s" % ek, "1@tur_sayacini_kaydet",
         "%d@%s" % (yazici, sahip))

    # S3d — tur_kapat kapiya onarim>0 kosuluyla ugruyor mu?
    kapat = _fonksiyon(agac, "tur_kapat")
    ifade = "-"
    if kapat:
        for alt in ast.walk(kapat):
            if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name) \
                    and alt.func.id == "tur_sayacini_kaydet" and alt.args:
                ilk = alt.args[0]
                if isinstance(ilk, ast.IfExp) \
                        and isinstance(ilk.body, ast.Constant) \
                        and isinstance(ilk.orelse, ast.Constant):
                    ifade = "%s/%s" % (ilk.body.value, ilk.orelse.value)
                else:
                    ifade = "kosulsuz:%s" % ast.dump(ilk)[:24]
                break
    vaka("S3d-tur_kapat-onarim-kolu%s" % ek, "KOSTU_ONARDI/KOSTU_DUSTU", ifade)

    # S3e — tur_kos icinde kapiya DOGRUDAN tek cagri (ATLANDI kolu)
    vaka("S3e-tur_kos-dogrudan-cagri%s" % ek, 1,
         _cagri_say(fn, "tur_sayacini_kaydet") if fn else -1)


# ===========================================================================
# S4 — MUTANTLAR
# ===========================================================================

def sayim():
    return sum(1 for *_x, g in VAKALAR if g), len(VAKALAR)


def mutant_kaynak_kos(ad, kaynak, tmp, hedef_onek, yan_onek):
    """Mutant kaynagi ayri modul olarak yukleyip S1+S2+S3'u yeniden kosar."""
    isaret = len(VAKALAR)
    yol = os.path.join(CRON_KOKU, ".b8-mutant-%s.py" % ad.split("-")[0].lower())
    try:
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(kaynak)
        mod = modul_yukle(yol, "b8_mutant_%s" % ad.split("-")[0].lower())
        bolum_s1(mod, tmp, ek="-%s" % ad)
        bolum_s2(mod, tmp, ek="-%s" % ad)
        bolum_s3(kaynak, ek="-%s" % ad)
    finally:
        try:
            os.remove(yol)
        except OSError:
            pass
        for artik in (yol + "c", yol.replace(".py", ".pyc")):
            try:
                os.remove(artik)
            except OSError:
                pass
    return _atif(ad, isaret, hedef_onek, yan_onek)


def _atif(ad, isaret, hedef_onek, yan_onek):
    yeni = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    hedef = [v for v in yeni if any(v[0].startswith(o) for o in hedef_onek)]
    yan = [v for v in yeni if any(v[0].startswith(o) for o in yan_onek)]
    hedef_oldu = bool(hedef) and all(not v[3] for v in hedef)
    yan_yesil = bool(yan) and all(v[3] for v in yan)
    print("MUTANT=%-28s HEDEF_KOL=%-7s (%d vaka) YAN_EKSEN=%-8s (%d vaka)"
          % (ad, "OLDU" if hedef_oldu else "YASADI", len(hedef),
             "YESIL" if yan_yesil else "KIRMIZI", len(yan)))
    return hedef_oldu, yan_yesil


def bolum_s4(kapi, kaynak, tmp):
    print("--- BOLUM S4: MUTANTLAR ---")
    sonuclar = []

    # N1 — erken `return` sayaci yeniden ATLIYOR (asil arizanin geri gelmesi)
    n1 = kaynak.replace('return _tur_dustu("SURE_TAVANI")', "return 1", 1)
    sonuclar.append(("N1-erken-return-atlar",) + mutant_kaynak_kos(
        # 🔴 `S2-E2-tavan-rc` HEDEF DEGIL: mutant sonrasi da rc=1 doner (kol
        # dogru sayiyla YASAR). Hedefe konsaydi mutant "YASADI" gorunurdu —
        # [[ad-iki-rolde-mutanti-golgeler]]. Asil olen SAYAC ve JETON.
        "N1-erken-return-atlar", n1, tmp,
        ("S2-E2-tavan-sayac", "S2-E2-tavan-jeton", "S3b"),
        ("S1", "S2-E1", "S2-E2-tavan-rc", "S2-E3", "S2-E4", "S2-E5",
         "S3a", "S3c", "S3d", "S3e")))

    # N3 — TEK KAPI delindi: tur_kapat yazicIyi DOGRUDAN cagiriyor
    n3 = kaynak.replace(
        '        ustuste_onarimsiz, _ = tur_sayacini_kaydet(   # B8 TEK KAPI\n'
        '            "KOSTU_ONARDI" if onarim > 0 else "KOSTU_DUSTU", onarim)\n',
        "        ustuste_onarimsiz = ustuste_onarimsiz_guncelle(onarim)\n", 1)
    sonuclar.append(("N3-tek-kapi-delindi",) + mutant_kaynak_kos(
        "N3-tek-kapi-delindi", n3, tmp,
        ("S3c", "S3d"), ("S1", "S2", "S3a", "S3b", "S3e")))

    # N4 — tur_kapat onarim kolu bozuldu (pozitif kol OLU olmasin)
    n4 = kaynak.replace('"KOSTU_ONARDI" if onarim > 0 else "KOSTU_DUSTU"',
                        '"KOSTU_DUSTU"', 1)
    sonuclar.append(("N4-onarim-kolu-bozuldu",) + mutant_kaynak_kos(
        "N4-onarim-kolu-bozuldu", n4, tmp,
        ("S3d",), ("S1", "S2", "S3a", "S3b", "S3c", "S3e")))

    # N2 — ATLANDI turu de sayiliyor (calisma zamani yamasi)
    isaret = len(VAKALAR)
    asil = kapi.tur_sayacini_kaydet

    def bozuk(hal, onarim=0, yaz=True, yol=None):
        if hal == "ATLANDI":
            return kapi.ustuste_onarimsiz_guncelle(0, yol), True
        return asil(hal, onarim, yaz, yol)
    kapi.tur_sayacini_kaydet = bozuk
    try:
        bolum_s2(kapi, tmp, ek="-N2-atlanan-sayiliyor")
    finally:
        kapi.tur_sayacini_kaydet = asil
    sonuclar.append(("N2-atlanan-sayiliyor",) + _atif(
        "N2-atlanan-sayiliyor", isaret,
        ("S2-E1-atlandi-sayac", "S2-E1-yazilmadi"),
        ("S2-E2", "S2-E3", "S2-E4", "S2-E5")))

    # K0 — KONTROL MUTANTI: kaynak DEGISMEDEN ayni mutasyon harness'inden
    # gecer. Amac: kirmiziyi mutasyonun mu harness'in mi urettigini ayirmak.
    isaret = len(VAKALAR)
    yol = os.path.join(CRON_KOKU, ".b8-mutant-k0.py")
    try:
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(kaynak)
        mod = modul_yukle(yol, "b8_mutant_k0")
        bolum_s1(mod, tmp, ek="-K0")
        bolum_s2(mod, tmp, ek="-K0")
        bolum_s3(kaynak, ek="-K0")
    finally:
        try:
            os.remove(yol)
        except OSError:
            pass
    k0 = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    k0_yesil = all(v[3] for v in k0)
    print("MUTANT=%-28s HEDEF_KOL=%-7s (%d vaka)"
          % ("K0-kontrol", "YESIL" if k0_yesil else "KIRMIZI", len(k0)))
    return sonuclar, k0_yesil, len(k0)


# ===========================================================================

def main():
    try:
        with open(NOBET_KAPI, encoding="utf-8") as dosya:
            kaynak = dosya.read()
    except OSError as hata:
        print("KABUL=KALDI (nobet-kapi.py okunamadi: %s)" % hata)
        return 2
    kapi = modul_yukle(NOBET_KAPI, "b8_nobet_kapi")
    if not hasattr(kapi, "tur_sayacini_kaydet"):
        print("KABUL=KALDI (B8 yamasi KURULU DEGIL: tur_sayacini_kaydet yok)")
        return 2

    tmp = tempfile.mkdtemp(prefix="b8-sayac-")
    try:
        bolum_s1(kapi, tmp)
        bolum_s2(kapi, tmp)
        bolum_s3(kaynak)
        mutantlar, k0_yesil, k0_n = bolum_s4(kapi, kaynak, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen, toplam = sayim()
    m_gecen = sum(1 for _, h, y in mutantlar if h and y)
    print("MUTANT=%d/%d  HEDEF_KOL_ATFI=%d/%d  KONTROL=%d/%d"
          % (m_gecen, len(mutantlar),
             sum(1 for _, h, _y in mutantlar if h), len(mutantlar),
             k0_n if k0_yesil else 0, k0_n))
    print("TOPLAM=%d GECTI=%d KALDI=%d" % (toplam, gecen, toplam - gecen))
    if not k0_yesil:
        print("KABUL=OLCULEMEDI (K0 kontrol mutanti kirmizi — batarya kararsiz)")
        return 3
    if gecen == toplam and m_gecen == len(mutantlar):
        print("KABUL=GECTI (%d/%d vaka)" % (gecen, toplam))
        return 0
    print("KABUL=KALDI (%d/%d vaka, %d/%d mutant)"
          % (gecen, toplam, m_gecen, len(mutantlar)))
    return 1


if __name__ == "__main__":
    sys.exit(main())

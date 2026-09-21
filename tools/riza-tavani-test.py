#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/riza-tavani-olc.py (OCI riza tavani olcumu).

KABUL SORUSU: "bu satiri silsem hangi iddia kirmizi yanar?"
Cevap her vaka icin ADIYLA yazildi. Test IKI kola ayrilir:

  A) VAKALAR — araci DEGISTIRMEDEN, fikstur uzerinde davranis olcer.
     Asil iddia: **SESSIZ "%0" YOK**. Payda 0 iken arac 0.0% BASMAZ, rc!=0 + HAL= ile DURUR.
  B) MUTANTLAR — araci IZOLE KOPYADA bozar, KIRMIZI yanmasini bekler.
     Kopya `tempfile.mkdtemp` altinda; GERCEK EV YOLUNA DOKUNULMAZ, silinen yalnizca
     testin KENDI urettigi gecici dizindir (FILO DERSI 4 Eyl: yuk yikici olamaz).

Kosum (borusuz):  python3 tools/riza-tavani-test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(ROOT, "tools", "riza-tavani-olc.py")

# Temiz fikstur: 4 paid (2 tik kimlikli, 3 rizali, 2 tamamlandi/1 tikli) + 2 organik.
# Sayilar ELLE cikarildi -> beklenen degerler asagida SABIT; govde degisirse test yanar.
TEMIZ = [
    {"src": "GS", "durum": "tamamlandi", "rizali": 1, "tik_kimlikli": 1},
    {"src": "GS", "durum": "tamamlandi", "rizali": 0, "tik_kimlikli": 0},
    {"src": "GS", "durum": "iptal", "rizali": 1, "tik_kimlikli": 1},
    {"src": "GS", "durum": "bekliyor", "rizali": 1, "tik_kimlikli": 0},
    {"src": "OG", "durum": "tamamlandi", "rizali": 1, "tik_kimlikli": 0},
    {"src": "OG", "durum": "iptal", "rizali": 0, "tik_kimlikli": 0},
]
BEKLENEN_TEMIZ = {
    "PAYDA_PAID_SIPARIS=4": "payda = paid siparis sayisi",
    "PAY_TIK_KIMLIKLI=2": "pay = tik kimligi SAKLANMIS paid siparis",
    "TAVAN_SIMDI=50.0%": "bugunku tavan = 2/4",
    "RIZALI_PAID=3": "riza vekili (ga_client_id) sayisi",
    "TAVAN_OCI2=75.0%": "OCI#2 sonrasi ulasilabilir tavan = 3/4",
    "PAID_TAMAMLANDI=2": "tamamlanmis paid siparis",
    "TAVAN_TAMAMLANDI=50.0%": "tamamlanmislarda tavan = 1/2",
    "ORGANIK_RIZA_ORANI=50.0%": "organik karsilastirma ekseni = 1/2",
    "HAL=TAMAM": "temiz kolda HAL jetonu TAMAM",
}

# (ad, satirlar, beklenen_rc, beklenen_HAL, oldurulen_iddia)
VAKALAR = [
    ("V1 payda SIFIR -> sessiz %0 YOK",
     [r for r in TEMIZ if r["src"] != "GS"], 3, "HAL=PAYDA-SIFIR",
     "paid siparis yokken arac 0.0% BASARSA bu satir olur"),
    ("V2 bos girdi -> payda SIFIR",
     [], 3, "HAL=PAYDA-SIFIR",
     "bos liste sessizce %0 sayilirsa bu satir olur"),
    ("V3 zorunlu alan eksik",
     [{"src": "GS", "durum": "tamamlandi", "rizali": 1}], 5, "HAL=ALAN-EKSIK",
     "eksik alan 0 varsayilirsa pay SESSIZCE duser"),
    ("V4 satir sozluk degil",
     ["REF:GS-AA-BBBB"], 5, "HAL=GIRDI-BICIMI",
     "bicim denetimi kalkarsa arac TypeError ile ciplak coker, HAL basmaz"),
]


def kos(arac, fikstur_satirlari=None, ek=None, cwd=None):
    """Araci ALT SUREC olarak kosar; (rc, stdout+stderr) doner. rc BORUSUZ okunur."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(fikstur_satirlari if fikstur_satirlari is not None else [], f)
        fy = f.name
    try:
        cmd = [sys.executable, arac, "--fikstur", fy] + (ek or [])
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    finally:
        os.unlink(fy)


def izole_kopya(tmp):
    """Araci gecici dizine kopyalar. MUTANT CANLI GOVDEDE YASAMAZ: bozulan dosya
    repodaki degil, BU kopyadir."""
    hedef_tools = os.path.join(tmp, "tools")
    os.makedirs(hedef_tools, exist_ok=True)
    hedef = os.path.join(hedef_tools, "riza-tavani-olc.py")
    shutil.copyfile(ARAC, hedef)
    return hedef


def mutasyonla(yol, eski, yeni):
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(eski) != 1:
        raise AssertionError("MUTANT CAPASI BAYAT: %r govdede %d kez gecti (1 bekleniyordu) — "
                             "capa kaynaktan tazelenmeli" % (eski, govde.count(eski)))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni))


# (ad, capa, yerine, mod, jeton, fikstur, oldurulen_iddia)
#   mod "VAR" -> mutant KIRMIZI yanarken bu HAL jetonunu BASMALI
#   mod "YOK" -> mutant kirmizi yanar ama jeton BASILMAMALI; jetonu basan TEMIZ GOVDEDIR
#                (esdeger vaka V3 ile ciftlenir: ayni girdide canli govde jetonu BASAR)
MUTANTLAR = [
    ("M1 PAYDA kaynagi bozuldu (paid oneki yanlis)",
     'PAID_SRC = "GS"', 'PAID_SRC = "XX"', "VAR", "HAL=PAYDA-SIFIR", None,
     "payda kaynagi sapinca arac sessizce %0 basarsa bu mutant YESIL kalirdi"),
    ("M2 PAY kaynagi bozuldu (paid disi satirlar da paya sayildi)",
     'pay = sum(1 for r in paid if int(r["tik_kimlikli"]) == 1)',
     'pay = sum(1 for r in satirlar if int(r["tik_kimlikli"]) == 1) + payda',
     "VAR", "HAL=PAY-PAYDADAN-BUYUK", None,
     "pay>payda denetimi kalkarsa tavan %100'u asar ve kimse gormez"),
    ("M3 alan denetimi kaldirildi",
     'ZORUNLU_ALANLAR = ("src", "durum", "rizali", "tik_kimlikli")',
     'ZORUNLU_ALANLAR = ()',
     "YOK", "HAL=ALAN-EKSIK", [{"src": "GS", "durum": "tamamlandi", "rizali": 1}],
     "denetim kalkinca arac ciplak KeyError ile coker ve HAL= jetonu HIC basilmaz — "
     "cagiran kol arizayi SINIFLANDIRAMAZ"),
]


def main():
    hata = []
    gecen = 0

    # ── A) VAKALAR — canli govde, fikstur uzerinde davranis ──────────────────
    rc, cikti = kos(ARAC, TEMIZ)
    if rc != 0:
        hata.append("T0 TEMIZ KOL: rc=%d (0 bekleniyordu)\n%s" % (rc, cikti))
    else:
        gecen += 1
    for jeton, iddia in BEKLENEN_TEMIZ.items():
        if jeton in cikti:
            gecen += 1
        else:
            hata.append("T0 temiz kol jetonu YOK: %s  (iddia: %s)" % (jeton, iddia))

    for ad, satirlar, brc, bhal, iddia in VAKALAR:
        rc, cikti = kos(ARAC, satirlar)
        if rc == brc and bhal in cikti:
            gecen += 1
        else:
            hata.append("%s: rc=%d (bek %d) HAL bekleniyordu %r\n%s\n  iddia: %s"
                        % (ad, rc, brc, bhal, cikti[:400], iddia))
        # 🔴 SESSIZ %0 YASAGI — kirmizi kolda ORAN SATIRI HIC BASILMAMALI.
        if "TAVAN_SIMDI=" in cikti:
            hata.append("%s: KIRMIZI kolda TAVAN_SIMDI= satiri basildi — sessiz oran sizintisi"
                        % ad)
        else:
            gecen += 1

    # Pencere ekseni (fail-closed, D1'e dokunmadan)
    rc, cikti = kos(ARAC, TEMIZ, ek=["--baslangic", "2026-09-21", "--bitis", "2026-09-01"])
    if rc == 6 and "HAL=PENCERE-TERS" in cikti:
        gecen += 1
    else:
        hata.append("V5 ters pencere: rc=%d (bek 6)\n%s" % (rc, cikti[:300]))

    # ── B) MUTANTLAR — IZOLE KOPYA ──────────────────────────────────────────
    tmp = tempfile.mkdtemp(prefix="riza-tavani-mutant-")
    try:
        # Negatif kontrol: kopya BOZULMADAN temiz kolda YESIL olmali; olmazsa mutant
        # kirmizisi "kopya zaten cokuyor"dan gelir ve hicbir sey olcmez.
        kopya = izole_kopya(tmp)
        rc, cikti = kos(kopya, TEMIZ)
        if rc == 0 and "TAVAN_SIMDI=50.0%" in cikti:
            gecen += 1
        else:
            hata.append("NEGATIF KONTROL: bozulmamis kopya YESIL degil (rc=%d)\n%s"
                        % (rc, cikti[:400]))

        # 🔴 FAIL-CLOSED GIRDI UCU: kopyanin kokunde tools/d1-sync.py YOKTUR; --fikstur
        # verilmeden kosuldugunda arac SESSIZ BOS LISTEYE DUSMEMELI, HAL= ile DURMALI.
        # Bu kol CANLI D1'e DOKUNMAZ (uc zaten erisilemez).
        p = subprocess.run([sys.executable, kopya], capture_output=True, text=True,
                           timeout=120)
        ck = (p.stdout or "") + (p.stderr or "")
        if p.returncode == 2 and "HAL=D1-ERISILEMEDI" in ck and "TAVAN_SIMDI=" not in ck:
            gecen += 1
        else:
            hata.append("V6 D1 ucu erisilemez: rc=%d (bek 2), HAL=D1-ERISILEMEDI "
                        "bekleniyordu\n%s" % (p.returncode, ck[:400]))

        for ad, capa, yerine, mod, jeton, fik, iddia in MUTANTLAR:
            k = izole_kopya(tmp)
            try:
                mutasyonla(k, capa, yerine)
            except AssertionError as e:
                hata.append("%s: %s" % (ad, e))
                continue
            girdi = TEMIZ if fik is None else fik
            rc, cikti = kos(k, girdi)
            var = jeton in cikti
            oldu = rc != 0 and (var if mod == "VAR" else not var)
            if oldu:
                gecen += 1
            else:
                hata.append("%s: MUTANT HAYATTA (rc=%d, jeton %r %s, beklenen %s)\n%s\n"
                            "  iddia: %s"
                            % (ad, rc, jeton, "VAR" if var else "YOK", mod,
                               cikti[:400], iddia))
            # "YOK" modunda ciftleme SART: ayni girdide CANLI govde jetonu BASMALI,
            # yoksa mutant degil girdinin kendisi olcuyor olurdu.
            if mod == "YOK":
                rc2, cikti2 = kos(ARAC, girdi)
                if rc2 != 0 and jeton in cikti2:
                    gecen += 1
                else:
                    hata.append("%s CIFTLEME: canli govde ayni girdide %r basmadi "
                                "(rc=%d) — mutant kanitini tasiyan eksen YOK"
                                % (ad, jeton, rc2))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.exists(tmp):
            hata.append("TEMIZLIK: gecici dizin silinemedi: %s" % tmp)

    print("VAKA_GECEN=%d  VAKA_HATA=%d" % (gecen, len(hata)))
    for h in hata:
        print("KIRMIZI: %s" % h)
    if hata:
        print("HAL=KIRMIZI")
        return 1
    print("HAL=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())

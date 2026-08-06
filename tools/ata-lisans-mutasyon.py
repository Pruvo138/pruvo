#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — tools/ata-lisans-test.py GERCEKTEN olcuyor mu?

"Batarya kostum" ANLATISI KANIT DEGILDIR; surucu REPODA durur ve yeniden kosulabilir
([[mutasyon-kaniti-yeniden-uretilebilir]]). Kabul = cikis kodu degil, HER MUTANTIN
BEKLENEN ISARETI + KIRMIZI mutantta DUSEN IDDIANIN DOGRU iddia oldugu.

🔴 NEDEN BU KADAR MUTANT VAR: onceki batarya 3 oldurucu ile "gecti" diyordu ama bagimsiz
curutucu 12 SESSIZ GECIS olctu — batarya KENDI DELIGINI GORMUYORDU
([[beyan-edilmis-survivor]]). Artik her delik (D1..D12) icin AYRI bir oldurucu mutant vardir
ve her biri o delige ait D-IDDIASINI dusurmelidir. Mutantin sadece "kirmizi yakmasi" YETMEZ:
BASARISIZ dokumu o delige ait etiketi ICERMELIDIR.

🔴 CANLI AGACA ASLA DOKUNMAZ: tools/ gecici bir dizine KOPYALANIR, mutasyon KOPYAYA
uygulanir, test KOPYADAN kosulur ([[mutasyon-diske-yazma-tuzagi]]).

KONTROL MUTANTLARI (gurultu makinesi olmadigimizin kaniti): gercek ama KAPSAM DISI
davranis/sabit degisiklikleri YESIL kalmalidir.

Kosum:  python3 tools/ata-lisans-mutasyon.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
KAPI_ADI = "ata-lisans-kapisi.py"
TEST_ADI = "ata-lisans-test.py"

# (ad, aranan, yerine, beklenen_isaret, kanit_metni)
MUTANTLAR = [
    # ---------------- eksen: HOST cozumlemesi (kapinin yeni ekseni) ----------------
    ("OLD-01 host korlugu",
     '            if host == h or host.endswith("." + h):',
     '            if True:',
     "KIRMIZI", "AYIRT EDICI"),
    ("OLD-02 yargi tersine",
     '    if not satilabilir_ile(lisans_metni, adaptor.satilabilir):',
     '    if satilabilir_ile(lisans_metni, adaptor.satilabilir):',
     "KIRMIZI", "POZITIF"),

    # ---------------- D1: turev detayi None -> sessiz "ata yok" ----------------
    ("OLD-03 (D1) turev detayi None sessiz gecer",
     '        out = [_sonuc(DURUM_KALICI, "turev detayi YOK (API null / kayit silinmis-gizli)")]',
     '        out = [_sonuc(DURUM_ALAN_YOK, "turev detayi YOK -> ata yok sayildi")]',
     "KIRMIZI", "D1"),

    # ---------------- D2: ata alan adlari ----------------
    ("OLD-04 (D2) ata alan listesi TEK ada iner",
     'ATA_ALANLARI = ("originals", "remixParents", "derivedFrom", "ancestors",\n'
     '                "originalDesigns", "remixOf")',
     'ATA_ALANLARI = ("originals",)',
     "KIRMIZI", "D2"),

    # ---------------- D3: sekil varyasyonlari ----------------
    ("OLD-05 (D3a) dict/string ata sekli atlanir",
     '        elif isinstance(ham, (dict, str)):\n'
     '            elemanlar = [ham]                           # tekil sekil de COZULUR, atlanmaz',
     '        elif isinstance(ham, (dict, str)):\n'
     '            continue',
     "KIRMIZI", "D3a"),
    ("OLD-06 (D3c) taninmayan ata sekli sessiz gecer",
     "            hatalar.append(\"ata alani '%s' TANINMAYAN sekilde (%s)\" "
     "% (alan, type(ham).__name__))",
     '            pass',
     "KIRMIZI", "D3c"),
    ("OLD-07 (D3d) zarf acilmaz",
     '        icler = [d[k] for k in ZARF_ANAHTARLARI if isinstance(d.get(k), dict)]',
     '        icler = []',
     "KIRMIZI", "D3d"),
    ("OLD-08 (D3e) BOS turev detayi 'ata yok' sayilir",
     '        if not isinstance(acik, dict) or not acik:\n'
     '            out = [_sonuc(DURUM_KALICI, "turev detayi BOS (zarf acildiktan sonra da)")]',
     '        if False:\n'
     '            out = [_sonuc(DURUM_KALICI, "turev detayi BOS (zarf acildiktan sonra da)")]',
     "KIRMIZI", "D3e"),

    # ---------------- D4: tek alanda coklu URL ----------------
    ("OLD-09 (D4) yalniz ILK ata URL'sine bakilir",
     '    return [{"link": u, "license": lis, "kimlik_alani": kim, "alan": alan} for u in urller]',
     '    return [{"link": urller[0], "license": lis, "kimlik_alani": kim, "alan": alan}]',
     "KIRMIZI", "D4"),

    # ---------------- D5: zincir ----------------
    ("OLD-10 (D5a) zincir ozyinelemesi kapali",
     '        for ust in ustler:\n'
     '            out.extend(ata_yargi(ust, defter, gs, adaptor, derinlik + 1, gorulen))',
     '        for ust in ustler:\n'
     '            pass',
     "KIRMIZI", "D5a"),
    ("OLD-11 (D5b) derinlik tavani fail-OPEN",
     '        if derinlik >= DERINLIK_TAVANI:',
     '        if False:',
     "KIRMIZI", "D5b"),

    # ---------------- D6: gomulu lisans sozlugu ----------------
    ("OLD-12 (D6) gomulu lisans TEK sozlukle yargilanir",
     '    if gomulu and not coklu_sozluk_satilabilir(gomulu, kaynak_adaptor):',
     '    if gomulu and not genel_satilabilir(gomulu):',
     "KIRMIZI", "D6"),
    # VETO'nun KENDI BASINA olculebilmesi icin ayirt edici fikstur gerekir: alt sozluklerin
    # HICBIRININ yakalamadigi ama ticari kullanimi kapatan serbest-metin yazimlar
    # ("... not for commercial use", "... Premium License"). Onlar olmadan bu mutant
    # yasardi = beyan edilmis survivor.
    ("OLD-13 NC/tescilli VETOSU tamamen kaldirilir",
     '    if not isinstance(ham, str):\n        return True',
     '    if True:\n        return False\n    if not isinstance(ham, str):\n        return True',
     "KIRMIZI", "yanlis-negatif"),

    # ---------------- D7 / D12: hata siniflandirmasi ----------------
    ("OLD-14 (D7) timeout KALICI kovasina duser",
     '    except (socket.timeout, TimeoutError):\n'
     '        raise GeciciHata("okuma timeout")\n'
     '    except ValueError:',
     '    except (socket.timeout, TimeoutError):\n'
     '        raise KaliciHata("okuma timeout")\n'
     '    except ValueError:',
     "KIRMIZI", "D7"),
    ("OLD-15 (D12) bozuk JSON GECICI sayilir",
     '        raise KaliciHata("bozuk JSON / gecersiz deger")',
     '        raise GeciciHata("bozuk JSON / gecersiz deger")',
     "KIRMIZI", "D12"),

    # ---------------- D8: kapsam ayrimi ----------------
    ("OLD-16 (D8) kapsam kovalari birlestirilir",
     '        elif not ad.ata_destegi:\n            olculmedi_adaptorlu.append(urun_id)',
     '        elif not ad.ata_destegi:\n            olculmedi_adaptorsuz.append(urun_id)',
     "KIRMIZI", "D8"),
    ("OLD-17 (D8) OLCULMEMIS kapsam rc'yi 2'ye cekmez",
     '    if kapsam and (kapsam.get("olculmedi_adaptorlu") or kapsam.get("olculmedi_adaptorsuz")\n'
     '                   or kapsam.get("taranmadi")):\n        return 2',
     '    if False:\n        return 2',
     "KIRMIZI", "D8"),

    # ---------------- D9: izlenebilirlik ----------------
    ("OLD-18 (D9) sonuclarda urun kimligi set edilmez",
     '    for s in out:\n'
     '        s["urun"] = urun_id                     # her sonuc IZLENEBILIR olmali (ALAN-YOK dahil)',
     '    for s in out:\n'
     '        s.setdefault("urun", None)',
     "KIRMIZI", "D9"),

    # ---------------- D11: ust kademe sekil hatasi ----------------
    ("OLD-19 (D11b) ust kademe sekil hatasi yutulur",
     '        for h in sekil_hatalari:\n'
     '            out.append(_sonuc(DURUM_KALICI, "ust kademe: " + h, ata, host, kimlik, None,',
     '        for h in []:\n'
     '            out.append(_sonuc(DURUM_KALICI, "ust kademe: " + h, ata, host, kimlik, None,',
     "KIRMIZI", "D11b"),

    # ---------------- kimlik cikarimi: API bicimi (canli kuru kosumda olculdu) ----------------
    ("OLD-20 kimlik cikariminda API bicimi taninmaz",
     '        if parca.lower() in ("things", "thing") and i + 1 < len(parcalar):',
     '        if False:',
     "KIRMIZI", "kendini-test"),

    # ---------------- KONTROL (yanlis-pozitif olmadigi kaniti) ----------------
    ("KONTROL-1 ilgisiz davranis (kuru kosum tavani)",
     'ap.add_argument("--limit", type=int, default=40,',
     'ap.add_argument("--limit", type=int, default=41,',
     "YESIL", None),
    ("KONTROL-2 ilgisiz metin (rapor basligi)",
     'yaz("ATA-LISANS KAPISI — RAPOR KIPI (veri YAZILMAZ, silme UYGULANMAZ)")',
     'yaz("ATA-LISANS KAPISI — rapor (kontrol mutanti)")',
     "YESIL", None),
    ("KONTROL-3 ilgisiz sabit (zarf anahtar kumesi genisler)",
     'ZARF_ANAHTARLARI = ("data", "result", "response", "payload", "design", "model")',
     'ZARF_ANAHTARLARI = ("data", "result", "response", "payload", "design", "model", "zarf")',
     "YESIL", None),
]


def _agac_kur(tmp):
    """Gecici KOPYA agaci: tools/ + kapinin 'yazmaz' iddiasini olcebilmesi icin
    veri kokunde iki taklit dosya (icerikleri onemsiz; olculen sey DEGISMEMELERI)."""
    hedef_tools = os.path.join(tmp, "tools")
    shutil.copytree(_HERE, hedef_tools)
    _pycache_temizle(hedef_tools)
    with open(os.path.join(tmp, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([{"id": "uydurma", "baslik": "uydurma"}], f)
    with open(os.path.join(tmp, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
        json.dump({"uydurma": {"kaynak": "uydurma", "link": ""}}, f)
    return hedef_tools


def _pycache_temizle(kok):
    """🔴 OLCULEN TUZAK: bytecode onbellegi kaynagi (boyut + saniye cozunurluklu mtime) ile
    dogrular. AYNI UZUNLUKTA bir mutasyon ("KaliciHata"->"GeciciHata") ayni saniye icinde
    yazilirsa onbellek GECERLI sanilir ve MUTASYON UYGULANMAZ — bir onceki mutantin kodu
    kosar, kirmizi yanar ama YANLIS iddia duser. Bu surucude tam olarak bu olctu (OLD-14/15).
    Cozum: kopyada __pycache__ YOK + alt sureclerde bytecode yazimi KAPALI."""
    for dizin, altlar, _dosyalar in os.walk(kok):
        for alt in list(altlar):
            if alt == "__pycache__":
                shutil.rmtree(os.path.join(dizin, alt), ignore_errors=True)
                altlar.remove(alt)


def _kos(tools_dizin):
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"       # bkz _pycache_temizle
    r = subprocess.run([sys.executable, "-B", os.path.join(tools_dizin, TEST_ADI)],
                       capture_output=True, text=True, env=ortam)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    hatalar = []
    with tempfile.TemporaryDirectory() as tmp:
        tools_dizin = _agac_kur(tmp)
        kapi_yol = os.path.join(tools_dizin, KAPI_ADI)
        with open(kapi_yol, encoding="utf-8") as f:
            temiz_kaynak = f.read()

        # 0) TABAN: mutasyonsuz kopya YESIL + SESSIZ_GECIS=0 olmali
        rc, cikti = _kos(tools_dizin)
        if rc != 0 or "SESSIZ_GECIS=0" not in cikti:
            print("TABAN KIRMIZI — mutasyonsuz kopya gecmedi (rc=%d)" % rc)
            print(cikti[-3000:])
            return 2
        print("  ok   TABAN (mutasyonsuz kopya) YESIL · SESSIZ_GECIS=0")

        for ad, aranan, yerine, beklenen, kanit in MUTANTLAR:
            adet = temiz_kaynak.count(aranan)
            if adet != 1:
                hatalar.append("%s: capa %d kez gecti (1 olmali) — surucu BAYAT" % (ad, adet))
                print("  HATA %-52s capa sayisi=%d" % (ad, adet))
                continue
            with open(kapi_yol, "w", encoding="utf-8") as f:
                f.write(temiz_kaynak.replace(aranan, yerine))
            rc, cikti = _kos(tools_dizin)
            olculen = "YESIL" if rc == 0 else "KIRMIZI"
            coktu = ("Traceback" in cikti and "BASARISIZ" not in cikti)
            dokum = cikti.split("BASARISIZ", 1)[1] if "BASARISIZ" in cikti else ""
            kanit_ok = True if not kanit else (kanit in dokum)
            ok = (olculen == beklenen) and not coktu and kanit_ok
            if not ok:
                hatalar.append("%s: beklenen %s, olculen %s%s%s"
                               % (ad, beklenen, olculen, " (COKTU)" if coktu else "",
                                  "" if kanit_ok else " (dusen iddia %r DEGIL)" % kanit))
            print("  %-4s %-52s beklenen=%-7s olculen=%-7s%s%s"
                  % ("ok" if ok else "HATA", ad, beklenen, olculen,
                     " COKTU" if coktu else "", "" if kanit_ok else " KANIT-YOK"))
            with open(kapi_yol, "w", encoding="utf-8") as f:
                f.write(temiz_kaynak)

    oldurucu = sum(1 for m in MUTANTLAR if m[3] == "KIRMIZI")
    kontrol = len(MUTANTLAR) - oldurucu
    print("")
    if hatalar:
        print("MUTASYON BATARYASI BASARISIZ — %d/%d mutant beklenen isareti VERMEDI:"
              % (len(hatalar), len(MUTANTLAR)))
        for h in hatalar:
            print("  x %s" % h)
        return 1
    print("MUTASYON BATARYASI GECTI — oldurucu %d/%d KIRMIZI, kontrol %d/%d YESIL."
          % (oldurucu, oldurucu, kontrol, kontrol))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TERK EDILMIS 'bekliyor' SUPURMESI — mutasyon bataryasi (ONCE-KIRMIZI KANITI).

    python3 tools/terk-supurme-mutasyon.py

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir. Calisma agacindaki shop/src/index.js'e
DOKUNULMAZ (desen kardesi: tools/havale-onay-mutasyon.py). Kabul testi ayna icinde
`PRUVO_INDEX_KAYNAK` ile mutantli dosyaya bakar.

NE OLCER — her mutant icin IKI EKSEN AYRI AYRI:
  (a) HEDEF KOL   : mutantin oldurmesi GEREKEN iddia(lar) GERCEKTEN kirmizi yandi mi?
  (b) YAN EKSEN   : yasamasi GEREKEN iddialar YESIL kaldi mi? (mutant IZOLE mi?)
Mutantin "yasamasi" kol saglam DEMEK DEGILDIR, kol OLCULEMEDI demektir
([[ad-iki-rolde-mutanti-golgeler]]) — bu yuzden hedef kol atfi ayrica basilir.

🔴 BIR MUTANT BIRDEN COK IDDIAYI OLDUREBILIR ve bu kusur DEGILDIR; kusur, oldurdugunu
BEYAN ETMEMEKTIR. Ornek: M1 (beyaz liste genisler) yalniz (e)'yi degil (s) sayac
sozlesmesini ve (g) ikinci tur iddiasini da oldurur — cunku kapsam disi satirlar her
turda yeniden secilir. Beyan edilmeyen olum, yan eksen kirilmasi olarak KIRMIZI doner.

🔴 UST USTE BINEN KATMAN UYARISI ([[d1-arama-tuzaklari]] "iki katman birbirinin testini
maskeler"): supurmenin kapsam beyaz listesi TEK sabittir (TERK_KAYNAK_DURUM) ama UC yerde
okunur — SELECT + iki UPDATE'in CAS kosulu. Bu yuzden M1 tek basina 'havale-bekliyor'u
IPTAL ETTIREMEZ (CAS onu yine tutar); M1'in olculebilir hasari satirin SECILMESIDIR ve
kabul testi tam da bunu iddia eder ("retrieve BILE DENENMEDI"). Kapsam ihlalini yalnizca
durum degisiminden olcen bir test, bu mutanti KACIRIRDI.

CAPA DISIPLINI: her mutantin dayanak metni kaynakta TEKIL olmalidir. Tekil degilse ya da
hic bulunmuyorsa mutant ATLANMAZ — `HARNESS BAYAT` olarak KAYDEDILIR ve batarya KIRMIZI
doner ([[capa-cokmesi-arkasindaki-capalari-gizler]]). Sessiz atlama YOK.

CIKIS KODU: 0 hepsi beklendigi gibi · 1 en az bir mutant kacti / harness bayat.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEDEF_BAGIL = os.path.join("shop", "src", "index.js")
TEST_BAGIL = os.path.join("shop", "test", "terk-supurme.mjs")

TUM_IDDIALAR = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "s"]

# (kimlik, aciklama, eski_metin, yeni_metin, oldurmesi_gerekenler)
# `yasamasi gerekenler` TURETILIR: TUM_IDDIALAR - oldurmesi_gerekenler. Ikinci bir elle
# yazilmis liste, sessizce ayrisan ikinci bir hukum olurdu ([[ayni-alan-iki-hukum-biri-sessiz]]).
MUTANTLAR = [
    (
        "M1_HAVALE",
        "kapsam beyaz listesi GENISLER: SELECT 'havale-bekliyor'u da alir "
        "(gercek siparis supurmeye girer)",
        " musteri_notu FROM siparisler WHERE durum = ? AND tarih < ?"
        " ORDER BY tarih ASC LIMIT ?",
        " musteri_notu FROM siparisler WHERE (durum = ? OR durum = 'havale-bekliyor')"
        " AND tarih < ? ORDER BY tarih ASC LIMIT ?",
        # (e) dinamik kapsam kaniti · (j) STATIK kapsam kaniti ("'havale-bekliyor' supurme
        # govdesinde HEDEF olarak GECMEZ") · (g)+(s) her turda yeniden secilen satirin
        # idempotens ve sayac sozlesmesini bozmasi.
        ["e", "g", "j", "s"],
    ),
    (
        "M2_KOR",
        "FAIL-CLOSED DUSER: retrieve ULASILAMADIGINDA satir iptal koluna akar "
        "(kor iptal = parayi gorunmez yapma)",
        '    if (h.hal === "altyapi-hatasi") { sonuc.ulasilamadi++; continue; }',
        '    if (false) { sonuc.ulasilamadi++; continue; }  /* MUTANT: fail-closed dusuruldu */',
        ["d", "g", "s"],
    ),
    (
        "M3_ESIK",
        "TERK ESIGI 0'a duser (24 saatten YENI satirlar da supurmeye girer)",
        "export const TERK_ESIK_SAAT = 24;",
        "export const TERK_ESIK_SAAT = 0;",
        ["a", "j", "s"],
    ),
    (
        "M4_IDEM",
        "'odendi' CAS kosulu (durum <> 'odendi') KALKAR -> supurme + callback ayni satirda "
        "Purchase'i IKI KEZ sayar",
        '    "UPDATE siparisler SET durum = \'odendi\', iyzico_odeme_id = ?, '
        'durum_gecmisi = ?" +\n    " WHERE token = ? AND durum <> \'odendi\'"',
        '    "UPDATE siparisler SET durum = \'odendi\', iyzico_odeme_id = ?, '
        'durum_gecmisi = ?" +\n    " WHERE token = ?"',
        ["h"],
    ),
    (
        "K0_KONTROL",
        "ILGISIZ kol: tek turda islenecek satir tavani 200 -> 199",
        "const TERK_TUR_TAVANI = 200;",
        "const TERK_TUR_TAVANI = 199;",
        [],
    ),
]

# Aynaya kopyalanacak agac (havale-onay harness'iyle AYNI gerekce: shop/src/konfigur.js
# kok konfigur.js'i `../../konfigur.js` diye, index.js `../../secenekler.js`'i import eder;
# semalar.js jenerator/urunler/*.json okur). wrangler.toml `shop/` altindadir (kabul testi
# [triggers] iddiasi icin OKUR).
AYNA_AGACI = ("shop", "jenerator", "secenekler.js", "konfigur.js", "package.json")


def ayna_kur(hedef_dizin):
    """Depoyu aynaya kopyalar (yalniz testin ihtiyac duydugu agac)."""
    for bagil in AYNA_AGACI:
        kaynak = os.path.join(KOK, bagil)
        if not os.path.exists(kaynak):
            continue
        varis = os.path.join(hedef_dizin, bagil)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        if os.path.isdir(kaynak):
            shutil.copytree(kaynak, varis, symlinks=True)
        else:
            shutil.copy2(kaynak, varis)


def testi_kos(ayna, kaynak_yolu):
    """Kabul testini ayna icinde kosar. Doner (rc, olen_iddialar_kumesi, ham_cikti)."""
    ortam = dict(os.environ)
    ortam["PRUVO_INDEX_KAYNAK"] = kaynak_yolu
    p = subprocess.run(
        ["node", os.path.join(ayna, TEST_BAGIL)],
        cwd=ayna, env=ortam, capture_output=True, text=True)
    cikti = (p.stdout or "") + (p.stderr or "")
    olen = set()
    m = re.search(r"^OLEN_IDDIALAR=(.*)$", cikti, re.M)
    if m and m.group(1).strip() and m.group(1).strip() != "-":
        olen = set(x for x in m.group(1).strip().split(",") if x)
    return p.returncode, olen, cikti


def main():
    kaynak_tam = os.path.join(KOK, HEDEF_BAGIL)
    if not os.path.exists(kaynak_tam):
        print("HATA: %s yok" % HEDEF_BAGIL)
        return 1
    ham = open(kaynak_tam, encoding="utf-8").read()

    # --- HARNESS TAZELIK KONTROLU (capalar TEKIL mi?) --------------------------
    bayat = []
    for kimlik, _aciklama, eski, _yeni, _oldur in MUTANTLAR:
        n = ham.count(eski)
        if n != 1:
            bayat.append("%s: dayanak metni %d kez geciyor (TEKIL olmali)" % (kimlik, n))
    if bayat:
        print("HARNESS BAYAT — mutasyon dayanaklari kaynakla ortusmuyor:")
        for s in bayat:
            print("  ✗ " + s)
        print("SONUC: KIRMIZI (mutantlar KOSMADI — sessiz atlama YOK)")
        return 1

    gecici = tempfile.mkdtemp(prefix="terk-supurme-mutasyon-")
    hatalar = []
    atif_satirlari = []
    try:
        # --- TABAN: mutasyonsuz ayna YESIL olmali ------------------------------
        taban = os.path.join(gecici, "taban")
        os.makedirs(taban)
        ayna_kur(taban)
        rc, olen, cikti = testi_kos(taban, os.path.join(taban, HEDEF_BAGIL))
        print("TABAN (mutasyonsuz ayna): rc=%d olen=%s" % (rc, sorted(olen) or "-"))
        if rc != 0:
            print(cikti[-4000:])
            print("SONUC: KIRMIZI (taban ayna zaten kirmizi — mutant atfi ANLAMSIZ)")
            return 1

        # --- MUTANTLAR ---------------------------------------------------------
        for kimlik, aciklama, eski, yeni, oldur in MUTANTLAR:
            yasa = [i for i in TUM_IDDIALAR if i not in oldur]
            dizin = os.path.join(gecici, kimlik)
            os.makedirs(dizin)
            ayna_kur(dizin)
            yol = os.path.join(dizin, HEDEF_BAGIL)
            metin = open(yol, encoding="utf-8").read()
            if metin.count(eski) != 1:
                hatalar.append("%s: aynada dayanak TEKIL degil" % kimlik)
                continue
            open(yol, "w", encoding="utf-8").write(metin.replace(eski, yeni))

            rc, olen, cikti = testi_kos(dizin, yol)
            hedef_tam = [i for i in oldur if i in olen]
            hedef_kacan = [i for i in oldur if i not in olen]
            yan_kirilan = [i for i in yasa if i in olen]

            print("\n%s — %s" % (kimlik, aciklama))
            print("  rc=%d  olen=%s" % (rc, sorted(olen) or "-"))
            print("  (a) HEDEF KOL : beklenen=%s  olen=%s  KACAN=%s"
                  % (oldur or "-", hedef_tam or "-", hedef_kacan or "-"))
            print("  (b) YAN EKSEN : yasamasi gereken=%s  KIRILAN=%s"
                  % (yasa or "-", yan_kirilan or "-"))
            atif_satirlari.append("%s -> %s" % (kimlik, ",".join(hedef_tam) or "-"))

            # 🔴 rc=3 "OLCULEMEDI"dir (modul yuklenemedi), "mutant oldurdu" DEGIL.
            if rc == 3:
                hatalar.append("%s: test OLCULEMEDI (rc=3, modul yuklenemedi) — "
                               "mutant atfi ANLAMSIZ" % kimlik)
                continue
            if hedef_kacan:
                hatalar.append("%s: HEDEF KOL KACTI %s (mutant hayatta kaldi -> kol OLCULEMEDI)"
                               % (kimlik, hedef_kacan))
            if yan_kirilan:
                hatalar.append("%s: YAN EKSEN KIRILDI %s (mutant IZOLE DEGIL)"
                               % (kimlik, yan_kirilan))
            if not oldur and rc != 0:
                hatalar.append("%s: KONTROL mutanti iddia OLDURDU (olen=%s) — batarya "
                               "ilgisiz degisikligi de kirmizi yakiyor" % (kimlik, sorted(olen)))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    # --- CALISMA AGACI DOKUNULMADI MI? ----------------------------------------
    simdi = open(kaynak_tam, encoding="utf-8").read()
    if simdi != ham:
        hatalar.append("CALISMA AGACI DEGISTI — mutant diskte kaldi (asla olmamali)")
    print("\nCALISMA AGACI: shop/src/index.js BASTAKIYLE AYNI: %s" % (simdi == ham))
    print("HEDEF_KOL_ATFI: " + " | ".join(atif_satirlari))

    kotu = len([h for h in hatalar if "KACTI" in h or "KIRILDI" in h
                or "KONTROL" in h or "OLCULEMEDI" in h])
    print("MUTANT=%d/%d" % (len(MUTANTLAR) - kotu, len(MUTANTLAR)))
    if hatalar:
        print("SONUC: KIRMIZI")
        for h in hatalar:
            print("  ✗ " + h)
        return 1
    print("SONUC: YESIL ✅ — 4 hedef mutant OLDU, kontrol mutanti hicbir iddiayi OLDURMEDI")
    return 0


if __name__ == "__main__":
    sys.exit(main())

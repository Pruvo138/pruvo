#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K252 — SIPARIS DURUM SECICI mutasyon bataryasi (ONCE-KIRMIZI KANITI).

    python3 tools/siparis-durum-mutasyon.py

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir. Calisma agacindaki shop/src/yonet.js'e
DOKUNULMAZ (desen kardesleri: tools/panel-kaynak-mutasyon.py · yonet-cerez-mutasyon.py).
Ayna, deponun shop/ + secenekler.js agacinin kopyasidir; kabul testi ayna icinde
`PRUVO_YONET_KAYNAK` ile mutantli dosyaya bakar.

NE OLCER — her mutant icin IKI EKSEN AYRI AYRI:
  (a) HEDEF KOL   : mutantin oldurmesi GEREKEN iddia(lar) GERCEKTEN kirmizi yandi mi?
  (b) YAN EKSEN   : yasamasi GEREKEN iddialar YESIL kaldi mi? (mutant IZOLE mi?)
Mutantin "yasamasi" kol saglam DEMEK DEGILDIR, kol OLCULEMEDI demektir
([[ad-iki-rolde-mutanti-golgeler]]) — bu yuzden hedef kol atfi ayrica basilir.

CAPA DISIPLINI: her mutantin dayanak metni kaynakta TEKIL olmalidir. Tekil degilse
ya da hic bulunmuyorsa mutant ATLANMAZ — `HARNESS BAYAT` olarak KAYDEDILIR ve batarya
KIRMIZI doner ([[capa-cokmesi-arkasindaki-capalari-gizler]] · K105). Sessiz atlama YOK.

CIKIS KODU: 0 hepsi beklendigi gibi · 1 en az bir mutant kacti / harness bayat.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEDEF_BAGIL = os.path.join("shop", "src", "yonet.js")
TEST_BAGIL = os.path.join("shop", "test", "siparis-durum-secici.mjs")

# (kimlik, aciklama, eski_metin, yeni_metin, oldurmesi_gerekenler, yasamasi_gerekenler)
MUTANTLAR = [
    (
        "M1_DARLIK",
        "/durum'daki 'kargolandi' reddi KALDIRILIR (darlik acilir)",
        '  if (hedef === "kargolandi") { return { ok: false, hata: "kargo-ucunu-kullan" }; }',
        '  if (hedef === "kargolandi") { return { ok: true }; }',
        ["③"],
        ["①", "②", "④"],
    ),
    (
        "M2_TAHSILAT",
        "'odendi' hedefinin 'yalniz geri alma' sarti KALDIRILIR (tahsilat yalani kapisi acilir)",
        '  if (hedef === "odendi" && ODENDI_GERI_ALMA.includes(mevcut)) { return { ok: true }; }',
        '  if (hedef === "odendi") { return { ok: true }; }',
        ["④"],
        ["⑤"],
    ),
    (
        "M3_IKIZ_LISTE",
        "panele ELLE fazladan bir durum eklenir (ikinci liste dogar)",
        " var secenekler=s.izinli_gecisler.map(function(d){",
        ' var secenekler=s.izinli_gecisler.concat(["kargolandi"]).map(function(d){',
        ["⑦"],
        ["①", "②", "③"],
    ),
    (
        "K0_KONTROL",
        "ILGISIZ kol bozulur (rozet rengi) — hicbir iddia OLMEMELI",
        ".rozet.tamamlandi{background:#dcfce7;color:#166534}",
        ".rozet.tamamlandi{background:#000000;color:#ffffff}",
        [],
        ["①", "②", "③", "④", "⑤", "⑥", "⑦"],
    ),
]


# Aynaya kopyalanacak agac. 🔴 KOK `konfigur.js` ZORUNLUDUR: shop/src/konfigur.js onu
# `../../konfigur.js` diye import eder; eksikse ayna ERR_MODULE_NOT_FOUND ile kirilir ve
# batarya "taban ayna kirmizi" deyip HICBIR mutanti kosmaz (bu turda olculdu).
AYNA_AGACI = ("shop", "jenerator", "secenekler.js", "konfigur.js", "package.json")


def ayna_kur(hedef_dizin):
    """Depoyu aynaya kopyalar (yalniz testin ihtiyac duydugu agac)."""
    for bagil in AYNA_AGACI:
        kaynak = os.path.join(KOK, bagil)
        if not os.path.exists(kaynak):
            continue
        varis = os.path.join(hedef_dizin, bagil)
        if os.path.isdir(kaynak):
            shutil.copytree(kaynak, varis, symlinks=True)
        else:
            shutil.copy2(kaynak, varis)


def testi_kos(ayna, kaynak_yolu):
    """Kabul testini ayna icinde kosar. Doner (rc, olen_iddialar_kumesi, son_satirlar)."""
    ortam = dict(os.environ)
    ortam["PRUVO_YONET_KAYNAK"] = kaynak_yolu
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
    for kimlik, _aciklama, eski, _yeni, _oldur, _yasa in MUTANTLAR:
        n = ham.count(eski)
        if n != 1:
            bayat.append("%s: dayanak metni %d kez geciyor (TEKIL olmali)" % (kimlik, n))
    if bayat:
        print("HARNESS BAYAT — mutasyon dayanaklari kaynakla ortusmuyor:")
        for s in bayat:
            print("  ✗ " + s)
        print("SONUC: KIRMIZI (mutantlar KOSMADI — sessiz atlama YOK)")
        return 1

    gecici = tempfile.mkdtemp(prefix="k252-mutasyon-")
    hatalar = []
    try:
        # --- TABAN: mutasyonsuz ayna YESIL olmali ------------------------------
        taban = os.path.join(gecici, "taban")
        os.makedirs(taban)
        ayna_kur(taban)
        rc, olen, cikti = testi_kos(taban, os.path.join(taban, HEDEF_BAGIL))
        print("TABAN (mutasyonsuz ayna): rc=%d olen=%s" % (rc, sorted(olen) or "-"))
        if rc != 0:
            print(cikti[-3000:])
            print("SONUC: KIRMIZI (taban ayna zaten kirmizi — mutant atfi ANLAMSIZ)")
            return 1

        # --- MUTANTLAR ---------------------------------------------------------
        for kimlik, aciklama, eski, yeni, oldur, yasa in MUTANTLAR:
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
    print("\nCALISMA AGACI: shop/src/yonet.js BASTAKIYLE AYNI: %s" % (simdi == ham))

    print("\nMUTANT=%d/%d" % (len(MUTANTLAR) - len([h for h in hatalar if "KACTI" in h
                                                    or "KIRILDI" in h or "KONTROL" in h]),
                             len(MUTANTLAR)))
    if hatalar:
        print("SONUC: KIRMIZI")
        for h in hatalar:
            print("  ✗ " + h)
        return 1
    print("SONUC: YESIL ✅ — 3 hedef mutant OLDU, kontrol mutanti hicbir iddiayi OLDURMEDI")
    return 0


if __name__ == "__main__":
    sys.exit(main())

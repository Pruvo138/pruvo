#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K284 — HAVALE ONAY UCU mutasyon bataryasi (ONCE-KIRMIZI KANITI).

    python3 tools/havale-onay-mutasyon.py

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir. Calisma agacindaki shop/src/yonet.js'e
DOKUNULMAZ (desen kardesi: tools/siparis-durum-mutasyon.py). Ayna, deponun testin
ihtiyac duydugu agacinin kopyasidir; kabul testi ayna icinde `PRUVO_YONET_KAYNAK` ile
mutantli dosyaya bakar.

NE OLCER — her mutant icin IKI EKSEN AYRI AYRI:
  (a) HEDEF KOL   : mutantin oldurmesi GEREKEN iddia(lar) GERCEKTEN kirmizi yandi mi?
  (b) YAN EKSEN   : yasamasi GEREKEN iddialar YESIL kaldi mi? (mutant IZOLE mi?)
Mutantin "yasamasi" kol saglam DEMEK DEGILDIR, kol OLCULEMEDI demektir
([[ad-iki-rolde-mutanti-golgeler]]) — bu yuzden hedef kol atfi ayrica basilir.

🔴 ONEMLI (dogru beklenti yazmak): bir mutant BIRDEN COK iddiayi oldurebilir ve bu bir
kusur DEGILDIR — kusur, oldurdugunu BEYAN ETMEMEKTIR. Ornek: M3 (gecis sarti hep true)
yalniz (b)'yi degil (e)'yi de oldurur, cunku idempotens iddiasinin tasiyicisi "ikinci
cagri artik gecerli DEGIL" olgusudur. Beyan edilmeyen olum, yan eksen kirilmasi olarak
KIRMIZI doner.

CAPA DISIPLINI: her mutantin dayanak metni kaynakta TEKIL olmalidir. Tekil degilse
ya da hic bulunmuyorsa mutant ATLANMAZ — `HARNESS BAYAT` olarak KAYDEDILIR ve batarya
KIRMIZI doner ([[capa-cokmesi-arkasindaki-capalari-gizler]]). Sessiz atlama YOK.

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
TEST_BAGIL = os.path.join("shop", "test", "havale-onay.mjs")

# (kimlik, aciklama, eski_metin, yeni_metin, oldurmesi_gerekenler, yasamasi_gerekenler)
MUTANTLAR = [
    (
        "M1_OLCUM",
        "havaleOlcumu() cagrisi DUSURULUR (havale cirosu yine Meta/GA4'e gitmez)",
        '    havaleOlcumu(env, ctx, { ...s, durum: "odendi" });',
        '    void 0;  /* MUTANT: olcum cagrisi dusuruldu */',
        ["d", "e"],
        ["a", "b", "c", "f", "h", "i", "j"],
    ),
    (
        "M2_DELIL",
        "BOS referans reddi KALDIRILIR (referanssiz 'odendi' mumkun olur)",
        '  if (!ref || ref.length > DEKONT_REF_ENCOK) '
        '{ return yjson({ hata: "dekont-ref" }, 400); }',
        '  if (ref.length > DEKONT_REF_ENCOK) '
        '{ return yjson({ hata: "dekont-ref" }, 400); }',
        ["a"],
        ["b", "c", "d", "e", "f", "h", "i", "j"],
    ),
    (
        "M3_GENIS",
        "havaleGecisiGecerli HER durumdan true doner (dar uc genisler)",
        'function havaleGecisiGecerli(mevcut) {\n  return mevcut === "havale-bekliyor";\n}',
        'function havaleGecisiGecerli(mevcut) {\n  return true || mevcut;\n}',
        ["b", "e"],
        ["a", "c", "d", "f", "h", "i", "j"],
    ),
    (
        "M4_ILKE",
        "/durum'un odeme ekseni reddi ACILIR (K252 tahsilat yalani kapisi duser)",
        '  if (hedef === "odendi" && ODENDI_GERI_ALMA.includes(mevcut)) '
        '{ return { ok: true }; }',
        '  if (hedef === "odendi") { return { ok: true }; }',
        ["f"],
        ["a", "b", "c", "d", "e", "h", "i", "j"],
    ),
    (
        "M5_PANEL",
        "havale onay formu HER kartta basilir (dar panel kolu genisler)",
        ' if(s.durum==="havale-bekliyor"){',
        ' if(true||s.durum==="havale-bekliyor"){',
        ["j"],
        ["a", "b", "c", "d", "e", "f", "h", "i"],
    ),
    (
        "K0_KONTROL",
        "ILGISIZ kol bozulur (rozet rengi) — hicbir iddia OLMEMELI",
        ".rozet.tamamlandi{background:#dcfce7;color:#166534}",
        ".rozet.tamamlandi{background:#000000;color:#ffffff}",
        [],
        ["a", "b", "c", "d", "e", "f", "h", "i", "j"],
    ),
]

# Aynaya kopyalanacak agac.
#  * shop/jenerator/secenekler.js/konfigur.js/package.json: K252 harness'iyle AYNI gerekce
#    (shop/src/konfigur.js kok konfigur.js'i `../../konfigur.js` diye import eder).
#  * tools/d1-sema.sql + tools/d1-sync.py: (h) SEMA PARITESI iddiasi bu iki dosyayi OKUR;
#    eksikse test exit 3 (OLCULEMEDI) verir ve taban ayna kirmizi olur.
AYNA_AGACI = ("shop", "jenerator", "secenekler.js", "konfigur.js", "package.json",
              os.path.join("tools", "d1-sema.sql"), os.path.join("tools", "d1-sync.py"))


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

    gecici = tempfile.mkdtemp(prefix="k284-mutasyon-")
    hatalar = []
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

            # 🔴 rc=3 "OLCULEMEDI"dir (kaynak capasi dustu), "mutant oldurdu" DEGIL:
            # o halde iddia kumesi hic basilmaz ve atif YALAN olurdu.
            if rc == 3:
                hatalar.append("%s: test OLCULEMEDI (rc=3, kaynak capasi dustu) — "
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
    print("\nCALISMA AGACI: shop/src/yonet.js BASTAKIYLE AYNI: %s" % (simdi == ham))

    kotu = len([h for h in hatalar if "KACTI" in h or "KIRILDI" in h
                or "KONTROL" in h or "OLCULEMEDI" in h])
    print("\nMUTANT=%d/%d" % (len(MUTANTLAR) - kotu, len(MUTANTLAR)))
    if hatalar:
        print("SONUC: KIRMIZI")
        for h in hatalar:
            print("  ✗ " + h)
        return 1
    print("SONUC: YESIL ✅ — 5 hedef mutant OLDU, kontrol mutanti hicbir iddiayi OLDURMEDI")
    return 0


if __name__ == "__main__":
    sys.exit(main())

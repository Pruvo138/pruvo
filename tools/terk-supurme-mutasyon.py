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
IYZICO_BAGIL = os.path.join("shop", "src", "iyzico.js")
TEST_BAGIL = os.path.join("shop", "test", "terk-supurme.mjs")

# 🔴 MUTASYONA ACIK TUM DOSYALAR. Capa tazeligi ve "calisma agaci degismedi" kontrolu
# BUNUN uzerinden doner; tek dosyaya bakan bir kontrol, ikinci dosyaya sizan mutanti
# GORMEZDI ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).
MUTASYON_DOSYALARI = (HEDEF_BAGIL, IYZICO_BAGIL)

# k/q/r: K358 (31 Agu 2026) — kesin-basarisiz UCUNCU SINIF (pozitif), kume DISINDA kalan
# her seyin FAIL-CLOSED kalmasi (emniyet cekirdegi), ve IKINCI TUKETICI `/donus`.
TUM_IDDIALAR = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "n", "p", "q", "r", "s"]

# (kimlik, aciklama, eski_metin, yeni_metin, oldurmesi_gerekenler, hedef_dosya)
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
        # (n) K356 neden-logu kolu sayacin fail-closed sozlesmesini de iddia eder
        # (ulasilamadi=1 / degisen=0) -> bu mutant orayi da oldurur ve BEYAN EDILIR.
        # (q) K358 EMNIYET kolunun TAM HEDEFI: kume disinda kalan her sey fail-closed kalmali;
        # fail-closed dusunce bilinmeyen kod / det-yok satirlari IPTAL'e akar.
        # (k) karisik turun sayac iddiasi (iptal=3) da olur: fail-closed satirlar da iptal olur.
        ["d", "g", "k", "n", "q", "s"],
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
    # ---------------------------------------------------------------- K356 (31 Agu 2026)
    # Neden-logu kolu (n) + gizlilik kolu (p). Dordu de "kol GERCEKTEN isiriyor mu"yu ayri
    # bir yoldan sorar: alan dusmesi · satirin tamamen dusmesi · IZINLI alanin DEGERINE
    # sizinti · maskenin devre disi kalmasi.
    (
        "M5_ALAN",
        "K356 NEDEN LOGU KORELIR: errorCode/errorMessage alanlari olcum satirindan DUSER "
        "(satir basilir ama 'neden' yine yazilmaz — bu tam da onarilan hal)",
        "               atlandi: kesin ? \"kesin-basarisiz\" : \"retrieve-hatasi\",\n"
        "               errorCode: hataKodu(det), errorMessage: hataMetni(det, token) });",
        "               atlandi: kesin ? \"kesin-basarisiz\" : \"retrieve-hatasi\" });"
        "  /* MUTANT: neden alanlari dusuruldu */",
        # (p) de oldurulur: gizlilik kolu 'errorMessage YAZILDI ama maskeli' diye iddia eder;
        # alan hic yoksa o iddia da olur. BEYAN EDILIR (sessiz coklu olum yasak).
        # (k) K358: kesin-basarisiz kolu da errorCode'u iyzico'nun DONDURDUGU kod diye iddia eder.
        ["k", "n", "p"],
    ),
    (
        "M5b_SATIR",
        "K356 LOG SATIRI TAMAMEN DUSER: 'altyapi-hatasi' kolunda olcumLog HIC cagrilmaz "
        "(sessiz bosluk — 'kol kosmadi' ile 'alan yoktu' ayni goruntuye coker)",
        "    olcumLog({ olay: \"Purchase\", siparis_no: siparis.siparis_no, kaynak: \"kart\",\n"
        "               atlandi: kesin ? \"kesin-basarisiz\" : \"retrieve-hatasi\",\n"
        "               errorCode: hataKodu(det), errorMessage: hataMetni(det, token) });",
        "    /* MUTANT: olcum satiri tamamen dusuruldu */",
        # K358: bu TEK satir artik UC halin de olcum izidir -> k/q/r'nin `atlandi` iddialari
        # da onunla birlikte olur (satir hic basilmayinca "hangi hal?" cevapsiz kalir).
        ["k", "n", "p", "q", "r"],
    ),
    (
        "M6_SIZINTI",
        "KISISEL KOLON LOGA SIZAR: musteri e-postasi IZINLI bir alanin (errorMessage) "
        "DEGERINE eklenir — beyaz liste alan ADINI korur, DEGERINI degil",
        "errorCode: hataKodu(det), errorMessage: hataMetni(det, token) });",
        "errorCode: hataKodu(det),\n"
        "               errorMessage: hataMetni(det, token) + \" \" + siparis.musteri_eposta });",
        # (n) de olur: neden-logu kolu errorMessage'in iyzico'nun DONDURDUGU metne birebir
        # esit oldugunu iddia eder; kuyruga eklenen e-posta o esitligi bozar.
        ["n", "p"],
    ),
    (
        "M6b_MASKE",
        "TOKEN MASKESI DEVRE DISI: iyzico ham govdeyi echo edince odeme token'i logda "
        "ACIK yazilir (sitede kart formu yok ama token oturum sirridir)",
        "  if (g.length >= MASKE_ASGARI) { s = s.split(g).join(\"***\"); }",
        "  if (false) { s = s.split(g).join(\"***\"); }  /* MUTANT: maske devre disi */",
        ["p"],
        IYZICO_BAGIL,
    ),
    # ---------------------------------------------------------------- K358 (31 Agu 2026)
    # KESIN-BASARISIZ UCUNCU SINIF. Dordu de yuklemin UC kosulunu (det VAR + iyzico "failure"
    # BEYAN ETTI + kod KAPALI kumede) AYRI AYRI kirar; her biri hangi iddiayi oldurdugunu
    # ADIYLA beyan eder ([[k182]]: "kirmizi geldi" kanit DEGIL).
    (
        "MK1_KUME_GENIS",
        "🔴 KAPALI KUME ACILIR: yuklem 'cevap veren HER failure kesin basarisizdir'a doner "
        "(kor iptal sinifi — bilinmeyen/bos kod da IPTAL edilir)",
        "  return IYZICO_KESIN_BASARISIZ.includes(hataKodu(det));",
        "  return true;  /* MUTANT: kume genisledi, cevap veren her failure kesin sayilir */",
        # (q) HEDEF: bilinmeyen kod / bos kod / kod-alani-yok artik fail-closed KALMAZ.
        # Yan olumler BEYAN EDILIR: (d)+(n)+(p) 1001/HTTP-400 gibi GERCEK altyapi hatalarini
        # da kesin sayar, (g)+(s) o satirlar iptal olunca sayac+idempotens sozlesmesi kayar,
        # (k) karisik turda iptal 3 yerine 4 olur, (r) /donus'ta 1001 de 'basarisiz' yazar.
        ["d", "g", "k", "n", "p", "q", "r", "s"],
        IYZICO_BAGIL,
    ),
    (
        "MK2_KUME_BOS",
        "KUME BOSALTILIR: 5122/10054/10057 artik uye degil -> ucuncu sinif kaybolur, "
        "her sey eski iki kovali hale doner",
        "  \"5122\",   // token'a ait odeme kaydi HIC YOK -> musteri sayfayi kapatti, "
        "para ortada degil\n"
        "  \"10054\",  // son kullanma tarihi hatali -> kart REDDEDILDI, tahsilat yok\n"
        "  \"10057\",  // kart sahibi bu islemi yapamaz -> kart REDDEDILDI, tahsilat yok\n",
        "  /* MUTANT: kume bosaltildi */\n",
        # (k) HEDEF: 5122/10054/10057 artik 'iptal' olmaz. (r) /donus'ta da 'basarisiz'
        # yerine 'incele'+Telegram'a doner. (p) gizlilik kolunun KESIN-BASARISIZ vakasi
        # (token maskesi + PII damgasi) olculecek kolu bulamaz — kume bosalinca o kol YOK.
        # (q) YASAR ve bu MK1'in TERSI kanittir: fail-closed davranis kume bosken de korunur.
        ["k", "p", "r"],
        IYZICO_BAGIL,
    ),
    (
        "MK3_DET_YOK",
        "🔴 `det` YOKLUGU da KESIN sayilir: retrieve HIC CEVAP VERMEDIGINDE (ag kopmasi) "
        "siparis iptal edilir — tam da kacinilan kor iptal",
        "  if (!det) { return false; }",
        "  if (!det) { return true; }  /* MUTANT: cevap YOKKEN de kesin basarisiz */",
        # (q) HEDEF: 'det-yok' vakasi + yuklemin dogrudan iddiasi. (k) karisik turun
        # sayac iddiasi da olur (det-yok satiri iptal'e akinca iptal=4 / ulasilamadi=1).
        ["k", "q"],
        IYZICO_BAGIL,
    ),
    (
        "MK4_STATUS_GEVSEK",
        "iyzico'nun 'failure' BEYANI ARANMAZ: kodun kumede olmasi TEK BASINA yeter "
        "(taninmayan bir govdeden gelen kod da iptal ettirir)",
        "  if (det.status !== \"failure\") { return false; }",
        "  if (false) { return false; }  /* MUTANT: status kosulu dusuruldu */",
        # (q) HEDEF: 'status-yok-kod-kumede' + 'status-baska-kod-kumede' vakalari ve
        # yuklemin dogrudan iddiasi. Baska hicbir eksen etkilenmez (izole mutant).
        ["q"],
        IYZICO_BAGIL,
    ),
    (
        "MK0_KONTROL",
        "ILGISIZ/ESDEGER kol: uyelik sinamasi `includes` yerine `indexOf(...) >= 0` ile "
        "yazilir (DAVRANIS AYNI). Kabul testinin dizge degil DAVRANIS olctugunu gosterir",
        "  return IYZICO_KESIN_BASARISIZ.includes(hataKodu(det));",
        "  return IYZICO_KESIN_BASARISIZ.indexOf(hataKodu(det)) >= 0;",
        [],
        IYZICO_BAGIL,
    ),
    (
        "K0_KONTROL",
        "ILGISIZ kol: tek turda islenecek satir tavani 200 -> 199",
        "const TERK_TUR_TAVANI = 200;",
        "const TERK_TUR_TAVANI = 199;",
        [],
    ),
    (
        "K1_KONTROL_IYZICO",
        "ILGISIZ kol (IKINCI DOSYA): hata metni log tavani 200 -> 199. iyzico.js'e uygulanan "
        "mutasyonun kendi basina kirmizi yakmadigini gosterir (M6b'nin atfi anlamli kalsin)",
        "const METIN_TAVANI = 200;",
        "const METIN_TAVANI = 199;",
        [],
        IYZICO_BAGIL,
    ),
]

# 5'li eski girdiler HEDEF_BAGIL'i varsayar; 6. eleman hedefi ACIKCA soyler.
MUTANTLAR = [(m + (HEDEF_BAGIL,)) if len(m) == 5 else m for m in MUTANTLAR]

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
    ham = {}
    for bagil in MUTASYON_DOSYALARI:
        tam = os.path.join(KOK, bagil)
        if not os.path.exists(tam):
            print("HATA: %s yok" % bagil)
            return 1
        ham[bagil] = open(tam, encoding="utf-8").read()

    # --- HARNESS TAZELIK KONTROLU (capalar TEKIL mi?) --------------------------
    bayat = []
    for kimlik, _aciklama, eski, _yeni, _oldur, hedef in MUTANTLAR:
        n = ham[hedef].count(eski)
        if n != 1:
            bayat.append("%s: dayanak metni %s icinde %d kez geciyor (TEKIL olmali)"
                         % (kimlik, hedef, n))
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
        for kimlik, aciklama, eski, yeni, oldur, hedef in MUTANTLAR:
            yasa = [i for i in TUM_IDDIALAR if i not in oldur]
            dizin = os.path.join(gecici, kimlik)
            os.makedirs(dizin)
            ayna_kur(dizin)
            yol = os.path.join(dizin, hedef)
            metin = open(yol, encoding="utf-8").read()
            if metin.count(eski) != 1:
                hatalar.append("%s: aynada dayanak TEKIL degil (%s)" % (kimlik, hedef))
                continue
            open(yol, "w", encoding="utf-8").write(metin.replace(eski, yeni))

            # Kabul testi DAIMA index.js'i yukler; mutasyon iyzico.js'e uygulansa bile
            # zincir aynanin icinden gecer (index.js -> ./iyzico.js), yani mutant CANLI
            # govdede yasar ([[mutant-canli-govdede-yasamaz]]).
            rc, olen, cikti = testi_kos(dizin, os.path.join(dizin, HEDEF_BAGIL))
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
    # 🔴 MUTASYONA ACIK HER DOSYA icin ayri ayri: tek dosyaya bakan kontrol, ikinci dosyaya
    # kalan mutanti gormezdi ve "temiz" der gecerdi.
    dokunulmadi = True
    for bagil in MUTASYON_DOSYALARI:
        simdi = open(os.path.join(KOK, bagil), encoding="utf-8").read()
        ayni = (simdi == ham[bagil])
        if not ayni:
            dokunulmadi = False
            hatalar.append("CALISMA AGACI DEGISTI (%s) — mutant diskte kaldi "
                           "(asla olmamali)" % bagil)
        print("\nCALISMA AGACI: %s BASTAKIYLE AYNI: %s" % (bagil, ayni))
    print("CALISMA AGACI DOKUNULMADI: %s" % dokunulmadi)
    print("HEDEF_KOL_ATFI: " + " | ".join(atif_satirlari))

    kotu = len([h for h in hatalar if "KACTI" in h or "KIRILDI" in h
                or "KONTROL" in h or "OLCULEMEDI" in h])
    print("MUTANT=%d/%d" % (len(MUTANTLAR) - kotu, len(MUTANTLAR)))
    if hatalar:
        print("SONUC: KIRMIZI")
        for h in hatalar:
            print("  ✗ " + h)
        return 1
    # Sayi ELLE YAZILMAZ: kontrol mutantlarinin sayisi degistiginde metin sessizce yalan
    # soylerdi. Hedefli/kontrol ayrimi MUTANTLAR listesinden TURETILIR.
    hedefli = len([m for m in MUTANTLAR if m[4]])
    kontrol = len(MUTANTLAR) - hedefli
    print("SONUC: YESIL ✅ — %d hedef mutant OLDU, %d kontrol mutanti hicbir iddiayi OLDURMEDI"
          % (hedefli, kontrol))
    return 0


if __name__ == "__main__":
    sys.exit(main())

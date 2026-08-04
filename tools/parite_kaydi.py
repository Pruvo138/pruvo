#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/parite_kaydi.py — URETILEBILIRLIK PARITE KAYDI: TEK SOZLESME (yazar + okuyucu).

NEDEN VAR
---------
2026-08-03'e kadar kural suydu: "semasinda `kisitlar` blogu olan aile SATILAMAZ."
Kural dogruydu ama ONCULU eksikti: kisit blogu "bu kutunun HER noktasi uretilebilir
DEGIL" der; kutunun DARALTILMIS halinin tamamen uretilebilir oldugu AYRI bir olcumdur.
O olcum yapilinca aile satilabilir olur. Yeni oncul:

    kisit VAR **ve** YESIL+TAZE parite kaydi YOK   =>  satilamaz
    kisit VAR **ve** YESIL+TAZE parite kaydi VAR   =>  satilabilir

Bu dosya o "parite kaydi"nin TEK sozlesmesidir. YAZAR
jenerator/test/rulman-uretilebilirlik-olcum.py --parite --kayit-yaz;
OKUYUCU tools/onizleme-vaat-kapisi.py (A3). Iki taraf da BU modulu cagirir —
ikinci bir yorumlayici kod yolu YOK ([[ikiz-tanim-sessiz-ayrisma]]).

🔴 MUAFIYET MUTANTSIZ YAZILIRSA KAPI SESSIZCE KORELIR. Bu modul bir SATIS KAPISINI
GEVSETIR (para tahsil edilen allowlist'e aile sokar), o yuzden "yesil kayit" tanimi
COK EKSENLIDIR ve her eksen TEK BASINA kirmizi yakabilir olmali
([[beyan-edilmis-survivor]]). Eksenler:

  1. tehlikeliKova == 0     (sema KABUL + motor RET kovasi bos)
  2. olculenNokta >= esik   (olculmemis sifir yesil sayilmaz, [[hukum-yanlis-birimde]])
  3. cozulmeyen == 0        (cokup hukum verilemeyen nokta kalmadi)
  4. motorOzet == onizleme/derleyici/paket-parmakizi.json'daki ozet
                            (motor degistiyse kayit BAYAT — olcum baska bir kati olcmustu)
  5. semaKisitOzeti == CANLI semanin `kisitlar` blogunun ozeti
                            (kisit degistiyse kayit BAYAT — olcum baska bir kutuyu olcmustu)
  5b. semaKutuOzeti == CANLI semanin PARAMETRE KUTUSUNUN ozeti (min/max/adim/secenekler)
                            🔴 2026-08-04'te OLCULEN FAIL-OPEN: kayit `ilanEdilenIzgara`yi
                            YAZIYORDU ama kapi onu canli semayla KARSILASTIRMIYORDU. Yani
                            `kisitlar` blogu AYNEN dururken bir parametrenin `max`i
                            buyutulunce (or. dis_cap 60 -> 100) kayit hala "yesil+taze"
                            sayiliyor, HIC OLCULMEMIS bir bolge sessizce satisa aciliyordu.
                            Kutu ozeti kayda girer ve canliyla ayrisirsa kayit BAYATTIR.
  6. kontrolMutantlari: M1/M2/M3 tehlikeli nokta URETMIS (>0), M4 uretmemis (==0)
                            (bataryasiz kayit = "0 gordum" iddiasinin korlugu olculmemis)

HUKUM SINIFLARI — ucu de YESIL DEGILDIR, ama AYRI SEYLERDIR:
  YESIL       kayit var, alti eksen de tuttu.
  KIRMIZI     kayit OKUNDU ama bir eksen tutmadi (yok · bayat · esik alti · sahte).
              Bu bir OLCULMUS anlasmazliktir -> A3 kirmizi yanar.
  OLCULEMEDI  kayit ya da parmakizi kaynagi OKUNAMADI (dosya yok/bozuk/sozlesme disi).
              Hukum VERILEMEZ -> cagiran taraf A3'u HIC BASMAZ (fail-closed).

Kayit dosyasi (IZLENEN): jenerator/test/uretilebilirlik-parite.json
Motor parmakizi kaynagi (IZLENEN): onizleme/derleyici/paket-parmakizi.json
  — motorun .scad KAYNAGI gitignore'ludur, ama ICERIK OZETI izlenen bu dosyada durur;
    boylece kapi gizli paket OLMADAN da bayatligi olcebilir (CI fresh checkout dahil).
"""
import hashlib
import io
import json
import os

KAYIT_YOLU = ("jenerator", "test", "uretilebilirlik-parite.json")
PARMAKIZI_YOLU = ("onizleme", "derleyici", "paket-parmakizi.json")
KISIT_ALANI = "kisitlar"
KAYIT_SURUMU = 1

# Bir kaydin TASIMASI ZORUNLU alanlari (eksikse sozlesme disi -> OLCULEMEDI).
ZORUNLU_ALANLAR = (
    "surucu", "mod", "olculenNokta", "tehlikeliKova", "cozulmeyen",
    "kovalar", "kontrolMutantlari", "motorDosya", "motorOzet",
    "semaUrunId", "semaKisitOzeti", "semaKutuOzeti", "ilanEdilenIzgara", "tarih",
)
# Bir parametrenin OLCULEN IZGARASINI belirleyen alanlar (etiket/aciklama/birim/
# varsayilan izgarayi DEGISTIRMEZ -> ozete GIRMEZ; yoksa her metin duzeltmesi
# yayini durdururdu). Bu liste, olcum surucusundeki eksen turetmesinin (rulman-
# uretilebilirlik-olcum.py `eksenler`) okudugu alanlarin AYNISIDIR.
KUTU_ALANLARI = ("ad", "tip", "min", "max", "adim")
# Kontrol mutantlarinin BEYAN EDILMESI gereken adlari + beklenen isaret.
# ">0" = mutant tehlikeli nokta URETMELI (kapi genislemeyi goruyor)
# "==0" = mutant tehlikeli nokta URETMEMELI (kapi daralmayi tehlike sanmiyor)
KONTROL_MUTANT_BEKLENTISI = {"M1": ">0", "M2": ">0", "M3": ">0", "M4": "==0"}

YESIL, KIRMIZI, OLCULEMEDI = "YESIL", "KIRMIZI", "OLCULEMEDI"


def kisit_ozeti(sema):
    """CANLI semanin `kisitlar` blogunun kanonik ozeti (tek kanonik bicim).

    Blok YOKSA da bir ozet uretilir (bos liste ile ayni degil): kayit "kisitsiz
    kutuyu olctum" diyemesin."""
    blok = sema.get(KISIT_ALANI, None)
    ham = json.dumps(blok, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()


def kutu_imzasi(sema):
    """CANLI semanin PARAMETRE KUTUSUNUN kanonik imzasi (liste).

    Her parametre icin izgarayi belirleyen alanlar: sayi -> min/max/adim,
    secim -> secenek DEGERLERI. Parametre sirasi ozete girmesin diye `ad`a gore
    siralanir (sira izgarayi degistirmez, yalnizca tarama duzenini)."""
    imza = []
    for p in sema.get("parametreler") or []:
        if not isinstance(p, dict):
            imza.append({"TANINMAYAN": repr(type(p).__name__)})
            continue
        kayit = {a: p.get(a) for a in KUTU_ALANLARI if a in p}
        kayit.setdefault("tip", "sayi")
        sec = p.get("secenekler")
        if isinstance(sec, list):
            kayit["secenekler"] = [s.get("deger") if isinstance(s, dict) else s for s in sec]
        imza.append(kayit)
    imza.sort(key=lambda k: str(k.get("ad")))
    return imza


def kutu_ozeti(sema):
    """kutu_imzasi'nin sha256'si — kayit ile canli sema TEK bu fonksiyondan turer."""
    ham = json.dumps(kutu_imzasi(sema), sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"))
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()


def ilan_edilen_izgara(sema):
    """Semanin ILAN ETTIGI toplam nokta sayisi (izgara buyuklugu) — None: hesaplanamaz.

    Kutu ozetinden BAGIMSIZ ikinci eksen: ozet 'ayni mi' der, bu sayi 'ne kadar
    buyudu' der ve kayittaki `ilanEdilenIzgara` ile karsilastirilir."""
    toplam = 1
    for p in sema.get("parametreler") or []:
        if not isinstance(p, dict):
            return None
        tip = p.get("tip", "sayi")
        if tip == "sayi":
            try:
                n = int(round((float(p["max"]) - float(p["min"])) / float(p["adim"]))) + 1
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                return None
            if n < 1:
                return None
            toplam *= n
        elif tip == "secim":
            sec = p.get("secenekler")
            if not isinstance(sec, list) or not sec:
                return None
            toplam *= len(sec)
        else:
            return None
    return toplam


def dosya_ozeti(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _json_oku(yol):
    with io.open(yol, encoding="utf-8") as f:
        return json.load(f)


def parmakizi_oku(kok, motor_dosya):
    """(ozet, hata) — motor .scad'inin IZLENEN paket parmakizindaki ozeti."""
    yol = os.path.join(kok, *PARMAKIZI_YOLU)
    if not os.path.exists(yol):
        return None, "paket parmakizi dosyasi YOK: %s" % "/".join(PARMAKIZI_YOLU)
    try:
        d = _json_oku(yol)
    except (ValueError, OSError) as e:
        return None, "paket parmakizi okunamadi/bozuk: %s" % e
    dosyalar = d.get("dosyalar")
    if not isinstance(dosyalar, dict):
        return None, "paket parmakizi `dosyalar` blogu TANINMADI"
    ozet = dosyalar.get(motor_dosya)
    if not isinstance(ozet, str) or not ozet:
        return None, ("paket parmakizinda `%s` girdisi YOK (motor paketten dusmus "
                      "ya da kayit olmayan bir motoru gosteriyor)" % motor_dosya)
    return ozet, ""


def kayit_oku(kok):
    """(kayitlar, hata) — {aile: girdi}. hata bos degilse kayitlar None (OLCULEMEDI)."""
    yol = os.path.join(kok, *KAYIT_YOLU)
    if not os.path.exists(yol):
        return None, "parite kaydi dosyasi YOK: %s" % "/".join(KAYIT_YOLU)
    try:
        d = _json_oku(yol)
    except (ValueError, OSError) as e:
        return None, "parite kaydi okunamadi/bozuk: %s" % e
    if not isinstance(d, dict):
        return None, "parite kaydi kok nesne degil (%s)" % type(d).__name__
    if d.get("surum") != KAYIT_SURUMU:
        return None, "parite kaydi surumu TANINMADI (%r, beklenen %d)" % (
            d.get("surum"), KAYIT_SURUMU)
    kayitlar = d.get("aileler")
    if not isinstance(kayitlar, dict):
        return None, "parite kaydi `aileler` blogu TANINMADI"
    for aile, girdi in sorted(kayitlar.items()):
        if not isinstance(girdi, dict):
            return None, "`aileler.%s` nesne degil (%s)" % (aile, type(girdi).__name__)
        eksik = [a for a in ZORUNLU_ALANLAR if a not in girdi]
        if eksik:
            return None, "`aileler.%s` sozlesme disi: eksik alan %s" % (aile, eksik)
        if not isinstance(girdi.get("kontrolMutantlari"), dict):
            return None, "`aileler.%s`.kontrolMutantlari nesne degil" % aile
    return kayitlar, ""


def girdi_dogrula(kok, aile, sema, en_az_nokta, kayitlar=None):
    """(hukum, sebep) — hukum: YESIL | KIRMIZI | OLCULEMEDI.

    `sema` CANLI sema sozlugu (kisit ozeti ONDAN turer, kayittan DEGIL)."""
    if kayitlar is None:
        kayitlar, hata = kayit_oku(kok)
        if kayitlar is None:
            return OLCULEMEDI, hata
    girdi = kayitlar.get(aile)
    if girdi is None:
        return KIRMIZI, ("`%s` ailesi icin parite kaydi YOK — sema kisitli bir aile "
                         "OLCUMSUZ satisa acilmis" % aile)

    beklenen_ozet, hata = parmakizi_oku(kok, girdi.get("motorDosya"))
    if beklenen_ozet is None:
        return OLCULEMEDI, "%s: %s" % (aile, hata)

    sorunlar = []
    if girdi.get("semaUrunId") != sema.get("id"):
        sorunlar.append("kayit BASKA urunu gosteriyor (kayit=%r, canli=%r)"
                        % (girdi.get("semaUrunId"), sema.get("id")))
    if girdi.get("motorOzet") != beklenen_ozet:
        sorunlar.append("BAYAT: motor parmakizi tutmuyor (kayit=%s… paket=%s…) — olcum "
                        "BASKA bir motorda yapilmis"
                        % (str(girdi.get("motorOzet"))[:12], beklenen_ozet[:12]))
    canli_kisit = kisit_ozeti(sema)
    if girdi.get("semaKisitOzeti") != canli_kisit:
        sorunlar.append("BAYAT: sema `kisitlar` ozeti tutmuyor (kayit=%s… canli=%s…) — "
                        "olcum BASKA bir parametre kutusunu olcmus"
                        % (str(girdi.get("semaKisitOzeti"))[:12], canli_kisit[:12]))
    # 🔴 KUTU EKSENI (5b): kisit AYNEN dururken bir parametrenin min/max/adim'i
    # degistiyse olcum ARTIK BASKA bir kutuyu olcmustur. Bu eksen olmadan
    # "dis_cap max 60 -> 100" gibi bir GENISLETME kapiyi rc=0 birakiyordu.
    canli_kutu = kutu_ozeti(sema)
    if girdi.get("semaKutuOzeti") != canli_kutu:
        sorunlar.append("BAYAT: sema PARAMETRE KUTUSU ozeti tutmuyor (kayit=%s… canli=%s…) — "
                        "aralik/adim degismis, olcum OLCULMEMIS bir bolgeyi kapsamiyor"
                        % (str(girdi.get("semaKutuOzeti"))[:12], canli_kutu[:12]))
    # Ikinci, BAGIMSIZ eksen: ilan edilen izgara buyuklugu. Ozet hesaplanamayan bir
    # semada (bozuk alan) ozet yine de bir deger uretir; bu sayi None olur -> hukum
    # VERILEMEZ (OLCULEMEDI), "esit" VARSAYILMAZ.
    canli_izgara = ilan_edilen_izgara(sema)
    if canli_izgara is None:
        return OLCULEMEDI, ("%s: canli semanin ilan edilen izgarasi HESAPLANAMADI "
                            "(parametre tipi/araligi taninmadi) — kayit tazeligi olculemez"
                            % aile)
    if girdi.get("ilanEdilenIzgara") != canli_izgara:
        sorunlar.append("BAYAT: ilan edilen izgara tutmuyor (kayit=%r, canli=%d) — "
                        "olcum BASKA buyuklukte bir kutuyu olcmus"
                        % (girdi.get("ilanEdilenIzgara"), canli_izgara))
    tehlikeli = girdi.get("tehlikeliKova")
    if not isinstance(tehlikeli, int) or tehlikeli != 0:
        sorunlar.append("tehlikeli kova (sema KABUL + motor RET) = %r, 0 DEGIL" % (tehlikeli,))
    cozulmeyen = girdi.get("cozulmeyen")
    if not isinstance(cozulmeyen, int) or cozulmeyen != 0:
        sorunlar.append("cozulmeyen (hukum verilemeyen) nokta = %r, 0 DEGIL" % (cozulmeyen,))
    nokta = girdi.get("olculenNokta")
    if not isinstance(nokta, int) or nokta < en_az_nokta:
        sorunlar.append("olculen nokta %r < esik %d — sifira yakin olcumle satis acilamaz"
                        % (nokta, en_az_nokta))
    mut = girdi.get("kontrolMutantlari") or {}
    for ad, isaret in sorted(KONTROL_MUTANT_BEKLENTISI.items()):
        v = mut.get(ad)
        if not isinstance(v, int):
            sorunlar.append("kontrol mutanti %s beyan EDILMEMIS (deger=%r)" % (ad, v))
        elif isaret == ">0" and v <= 0:
            sorunlar.append("kontrol mutanti %s tehlikeli nokta URETMEDI (%d) — olcum "
                            "genislemeye KOR, '0 gordum' iddiasi kanit degil" % (ad, v))
        elif isaret == "==0" and v != 0:
            sorunlar.append("kontrol mutanti %s (DAR kontrol) tehlikeli nokta uretti (%d) — "
                            "olcum daralmayi tehlike saniyor" % (ad, v))
    if sorunlar:
        return KIRMIZI, "%s: %s" % (aile, " | ".join(sorunlar))
    return YESIL, ("%s: %d nokta, tehlikeli kova 0, kutu %d nokta (ozet %s…), motor "
                   "%s(%s…), mutant M1=%d M2=%d M3=%d M4=%d, %s"
                   % (aile, nokta, canli_izgara, canli_kutu[:12], girdi.get("motorDosya"),
                      beklenen_ozet[:12], mut.get("M1"), mut.get("M2"),
                      mut.get("M3"), mut.get("M4"), girdi.get("tarih")))


def kayit_yaz(kok, aile, girdi, aciklama=None):
    """Kaydi YERINDE gunceller (baska ailelerin girdisi KORUNUR)."""
    yol = os.path.join(kok, *KAYIT_YOLU)
    if os.path.exists(yol):
        d = _json_oku(yol)
    else:
        d = {"surum": KAYIT_SURUMU, "aciklama": aciklama or "", "aileler": {}}
    d["surum"] = KAYIT_SURUMU
    if aciklama:
        d["aciklama"] = aciklama
    d.setdefault("aileler", {})[aile] = girdi
    with io.open(yol, "w", encoding="utf-8") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return yol

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — `marka_arama` kabul testi GERCEK ihlali yakiyor mu?

  Kapi: tools/marka-arama-d1-test.py

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]) — surucu repoda durur, kabul CIKIS KODU degil
OLCULEN IDDIA SAYISI + ISARET SARTIDIR (cokme kirmiziyla karisir).

BU KAPININ EN BUYUK RISKI TOTOLOJIDIR: kolonun degeri de, testin REFERANSI da ayni
yuklemden (arama.marka_sorgusu_esler) turer. Referans BASKA BIR GOVDEDEN
(marka-invaryant-kapisi.olc) alinarak bu risk daraltildi; asagidaki OLDURUCU mutantlar
kalan yuzeyi olcer:
  * yuklemi SERBEST METNE ceviren mutant (M1) — bugunku uc davranisi. Kolon "Havalandirma"yi
    Haval'a baglar, "Mandali"yi MAN'a. Kirmizi yanmazsa kapi HICBIR SEY olcmuyor demektir.
  * `marka_arama = marka_kanon` yapan mutant (M2) — BASLIK kolu FIILEN olculuyor mu.
  * TERSI (M3): yalniz baslik kolu — `marka_arama ⊇ marka_kanon` sozlesmesi FIILEN olculuyor mu.
  * sema/plan/fail-closed eksenleri (M4-M8) — her biri kendi iddiasini TEK BASINA dusurur
    ([[beyan-edilmis-survivor]]: katmanlarin VEYA'si degil, TEKIL eksen olculur).
KONTROL mutantlari iddia edilmeyen eksende YESIL kalmali — yoksa kapi "her degisiklige
kirmizi yanan" bir gurultu kaynagidir, nobetci degil.

CAPA DISIPLINI: her mutant capasinin kaynak dosyada TAM BIR KEZ gecmesi SART. Gecmezse
sonuc "YESIL" degil "CAPA-YOK"tur (mutant uygulanamadan yesil sayilmasi, bataryayi sessizce
kor ederdi).

🔴 CAPA KOMSUNUN DEGERINE CIVILENMEZ — TURETILIR (6 Eyl 2026, olculdu). M7'nin capasi
`ZORUNLU_KOLONLAR` listesinin O GUNKU UCLU yazimina SABIT DIZGE olarak civiliydi; liste iki
kolon buyuyunce (`tavsiye_filament`, `boy_secenekleri`) capa `CAPA-YOK(0)` verdi ve mutant
AYLARCA HIC UYGULANMADI — yani `Marka arama D1 kolonu` adimini koruyan eksen SESSIZCE OLUYDU.
Yeni sabit dizge cakmak ayni sinifi bir sonraki buyumede geri getirirdi
([[capa-turetme-altyapisi-kullanilmadan-kaldi]] · [[kopya-turetilemiyorsa-bayatlik-olculemez]]).
COZUM: capa bir FONKSIYONDUR — kaynagin KENDISINDEN `(eski, yeni)` cifti turetir. Turetemezse
donus None'dir ve batarya o mutanti ADIYLA `CAPA-COZULMEDI` diye KIRMIZI yakar; sessiz 0 YOK.
Turetici capasinin kendi bataryasi: `python3 tools/marka-arama-mutasyon.py --kendini-test`
(sentetik olarak BUYUTULMUS kolon listesinde capanin hala cozuldugunu IZOLE kopyada olcer).

NASIL: mutant DAIMA KOPYAYA uygulanir (gercek agac degismez). ROOT'un tamami gecici bir
dizine SYMLINK'lenir, mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi
O AYNADAN kosulur.

Calistir:  python3 tools/marka-arama-mutasyon.py
"""
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_ADI = "marka-arama-d1-test.py"

# Bunun altina dusen kosum "yesil/kirmizi" degil COKME'dir. Saglam kosum 54 GECTI basar;
# en cok iddia dusuren OLDURUCU (M1, yuklemi serbest metne cevirir) 35'in ustunde kalir.
# Esik, kapinin erken cikip birkac kontrol basarak "kirmizi" gorunmesini AYIRT ETMEK icindir.
TABAN_GECTI = 30

# `ZORUNLU_KOLONLAR = [ ... ]` atamasini SATIR OLARAK yakalar. Listenin ICERIGI hakkinda
# hicbir sey VARSAYMAZ — uzunlugu da, uyelerini de kaynaktan okur.
_ZORUNLU_KOLONLAR_RE = re.compile(r"^ZORUNLU_KOLONLAR = (\[[^\]\n]*\])$", re.M)


def m7_capa(taban):
    """M7 CAPASI — TURETILIR (sabit dizge DEGIL).

    `d1-sync.py`'deki `ZORUNLU_KOLONLAR` atamasini kaynaktan cozer ve ayni listeye
    `marka_arama` EKLEYEN yazimi uretir. Liste buyudugunde/kuculdugunde capa kendini
    yeniden turetir; bayatlamaz.

    None doner (=> batarya ADIYLA `CAPA-COZULMEDI` KIRMIZI yakar, sessiz 0 YOK) su
    hallerde:
      * atama satiri BULUNAMADI ya da BIRDEN COK bulundu  -> capa cozulemez
      * saga literal liste olarak AYRISTIRILAMADI          -> capa cozulemez
      * `marka_arama` LISTEDE ZATEN VAR                    -> mutant NO-OP olurdu; no-op
        mutant "kirmizi yanmadi" diye degil "hicbir sey degistirmedi" diye yesil kalir,
        bu da beyan edilmis survivor'dir ([[mutant-canli-govdede-yasamaz]]).
    """
    bulunan = _ZORUNLU_KOLONLAR_RE.findall(taban)
    if len(bulunan) != 1:
        return None
    eski = _ZORUNLU_KOLONLAR_RE.search(taban).group(0)
    try:
        liste = ast.literal_eval(bulunan[0])
    except (ValueError, SyntaxError):
        return None
    if not isinstance(liste, list) or not liste:
        return None
    if not all(isinstance(x, str) for x in liste):
        return None
    if "marka_arama" in liste:
        return None
    yeni = "ZORUNLU_KOLONLAR = [%s]" % ", ".join(
        '"%s"' % k for k in list(liste) + ["marka_arama"])
    return eski, yeni


# (ad, dosya [TOOLS'a gore], eski, yeni, beklenen[, eksen])
# `eski` bir DIZGE ya da bir TURETICI FONKSIYON olabilir. Fonksiyonsa `(eski, yeni)` cifti
# kaynaktan cozulur (`yeni` alani o zaman None yazilir) — bkz. m7_capa.
# `eksen` (istege bagli 6.): mutant KIRMIZI yanmakla kalmayip O IDDIAYI dusurmeli. Yoksa
# "kirmizi yandi" hukmu katmanlarin VEYA'sidir ve tekil eksen olculmemis olur
# ([[beyan-edilmis-survivor]]) — eksen verilirse KALDI satirlarindan biri onu ICERMELI.
MUTANTLAR = [
    # ── OLDURUCU: yuklemin KENDISI ──────────────────────────────────────────────
    ("OLDURUCU M1 YUKLEMI SERBEST METNE CEVIR (bugunku uc davranisi: alt-dize)",
     "d1-sync.py",
     "        deger = [m for m in adaylar\n"
     "                 if arama.marka_sorgusu_esler(m, uyeler, baslik_uyum)]",
     "        deger = [m for m in evren.taninmis\n"
     "                 if arama.esles(arama.haystack(u), arama.tokenlar(m))]",
     "KIRMIZI"),
    ("OLDURUCU M2 marka_arama = marka_kanon (BASLIK kolunu at)",
     "d1-sync.py",
     "        adaylar = list(uyeler) + [m for m in baslik_uyum if m not in uyeler]",
     "        adaylar = list(uyeler)", "KIRMIZI"),
    ("OLDURUCU M3 UYELIK kolunu at (yalniz baslik) — ⊇ sozlesmesi olculuyor mu",
     "d1-sync.py",
     "        adaylar = list(uyeler) + [m for m in baslik_uyum if m not in uyeler]",
     "        adaylar = list(baslik_uyum)", "KIRMIZI"),
    ("OLDURUCU M4 COK KELIMELI MARKAYI BOL — pencere 1 kelime (Land Rover -> Rover)",
     "arama.py",
     "        for k in range(min(MARKA_BASLIK_AZAMI_KELIME, n - i), 0, -1):",
     "        for k in range(min(1, n - i), 0, -1):", "KIRMIZI"),
    # ── OLDURUCU: senkron makinesi ──────────────────────────────────────────────
    ("OLDURUCU M5 PLAN NO-OP — hedefli UPDATE uretilmesin (kolon SONSUZA DEK '[]')",
     "d1-sync.py",
     "    return sema_plan(\"marka_arama\", urunler, aramalar, mevcut_arama, izleme,\n"
     "                     varsayilan=\"[]\")",
     "    return []", "KIRMIZI"),
    ("OLDURUCU M6 SEMA SIRASI KAPISINI AC — SELECT kolonu KOSULSUZ istesin",
     "d1-sync.py",
     "                + (\", marka_arama\" if marka_arama_kolonu else \"\"))",
     "                + \", marka_arama\")", "KIRMIZI"),
    # 🔴 CAPA TURETILIR: liste her buyudugunde sabit dizge bayatlar ve mutant sessizce
    # uygulanmaz olur (6 Eyl 2026'da tam bu oldu). `m7_capa` listeyi KAYNAKTAN okur.
    ("OLDURUCU M7 KOLONU ZORUNLU YAP (yoklugu TUM senkronu dusurur)",
     "d1-sync.py", m7_capa, None, "KIRMIZI"),
    ("OLDURUCU M8 FAIL-CLOSED'I AC — tek kaynak okunamayinca SESSIZ bos harita don",
     "d1-sync.py",
     "    mmb, evren, ek, sebep = marka_kaynaklari(urunler)\n"
     "    if sebep:\n"
     "        return {}, sebep\n"
     "    ek_normlu = mmb.ek_marka_normlu(ek)",
     "    mmb, evren, ek, sebep = marka_kaynaklari(urunler)\n"
     "    if sebep:\n"
     "        return {}, None\n"
     "    ek_normlu = mmb.ek_marka_normlu(ek)", "KIRMIZI"),
    ("OLDURUCU M9 ALTER DEFAULT'unu '' YAP (uc JSON.parse'i kosulsuz uygulayamaz)",
     "d1-sync.py",
     "    (\"marka_arama\", \"TEXT NOT NULL DEFAULT '[]'\"),",
     "    (\"marka_arama\", \"TEXT NOT NULL DEFAULT ''\"),", "KIRMIZI"),
    ("OLDURUCU M10 KATLAMAYI KAPAT — uyelik ham degerden dogsun (Volvo Penta artik Volvo degil)",
     "marka_model_build.py",
     "        kan = evren.katla((x or \"\").strip())",
     "        kan = (x or \"\").strip()", "KIRMIZI"),
    # ── ALIAS KOLU (5 Agu, mimar hukmu) ─────────────────────────────────────────
    # Uc `?q=Vauxhall` sorgusunu ancak kolondan cozebilir; alias kolu duserse musteri
    # 493 urunluk bir markayi canli aramada HIC bulamaz ve hicbir sey kirmizi yanmaz.
    ("OLDURUCU M11 ALIAS KOLUNU DUSUR (uc `?q=Vauxhall` sorgusunu cozemez, 493 urun kaybolur)",
     "d1-sync.py",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger:\n"
     "                    deger.append(a)",
     "        pass", "KIRMIZI"),
    # ALT KUME TUZAGI: alias'i YALNIZ `marka[]`inda o yazim GECEN satirlara eklemek
    # "calisiyor gibi" gorunur (kolon Vauxhall degerini TASIR) ama kume SITENINKINDEN
    # KUCUKTUR -> tam da kapatmaya calistigimiz ayrisma geri gelir. AL1/AL2 bunu yakalamali.
    ("OLDURUCU M12 ALIAS'i ALT KUMEYE BAGLA (yalniz `marka[]`inda alias YAZAN satirlar)",
     "d1-sync.py",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger:\n"
     "                    deger.append(a)",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger and a in (u.get(\"marka\") or []):\n"
     "                    deger.append(a)", "KIRMIZI"),
    ("OLDURUCU M13 ALIAS TABLOSUNU BOSALT (tek kaynak okunmasin)",
     "d1-sync.py",
     "    for alias in sorted(getattr(evren, \"marka_alias\", None) or ()):",
     "    for alias in sorted(()):", "KIRMIZI"),
    # ── AL3 KABUL EVRENI (5 Agu, mimar hukmu) ───────────────────────────────────
    # AL3'un evreni kanonik ∪ alias ∪ KAPALI MARKA KUMESI'dir. Bu IKI mutant, evrenin
    # GENISLETILMESI ile GEVSETILMESI arasindaki farki TEK BASINA olcer:
    #   M14  uc kaynagin HICBIRINDE olmayan UYDURMA ad -> AL3 KIRMIZI kalmali (fail-open degil)
    #   K4   kapali kumede OLAN ama bugun URUNU OLMAYAN ad -> AL3 YESIL (genisletmenin ta kendisi)
    # Ikisi de AYNI yere ayni bicimde deger enjekte eder; tek fark ADIN KAYNAKTA OLMASI.
    ("OLDURUCU M14 KOLONA UYDURMA MARKA ADI SOK (uc kaynagin hicbirinde YOK)",
     "d1-sync.py",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger:\n"
     "                    deger.append(a)\n"
     "        if deger:",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger:\n"
     "                    deger.append(a)\n"
     "        if deger:\n"
     "            deger.append(\"Zzyzx Motorworks\")", "KIRMIZI", "AL3"),
    # K4 GERCEK DUNYA VAKASI: urunun KENDI `marka` dizisinde YAZAN, kapali kumeye MIMAR
    # KARARIYLA girmis bir ad kolona sizar (suzgecten dusmustu). Bu, sozluk her
    # genisletildiginde yasanan HAL — eski AL3 bunu "veri kusuru" sanip kirmizi yakiyordu.
    # 🔴 K1 EKSENI TEMIZ KALIR: ad, o urunun KENDI kolonuna girdigi icin "ham jeton kolonda
    # gecmiyor" ihlali DOGMAZ; yani bu kontrol YALNIZ AL3 eksenini yoklar.
    ("KONTROL K4 KAPALI KUMEDEKI ADI URUNUN KENDI KOLONUNA SOK (genisletilen evren)",
     "d1-sync.py",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger:\n"
     "                    deger.append(a)\n"
     "        if deger:",
     "        for m in list(deger):\n"
     "            for a in alias_ters.get(m, ()):\n"
     "                if a not in deger:\n"
     "                    deger.append(a)\n"
     "        for _t in (u.get(\"marka\") or []):\n"
     "            _t = (_t or \"\").strip()\n"
     "            if _t in arama.UYUM_MARKA_IZINLI and _t not in deger:\n"
     "                deger.append(_t)\n"
     "        if deger:", "YESIL"),
    # ── KONTROL: iddia edilmeyen eksen / davranissiz yazim ──────────────────────
    ("KONTROL K1 davranissiz yazim (harita = {} -> dict())",
     "d1-sync.py",
     "    harita = {}\n    for u in urunler:\n"
     "        if not isinstance(u, dict):\n            continue\n"
     "        uid = u.get(\"id\")\n        if not uid:\n            continue\n"
     "        uyeler = mmb.marka_uyelikleri(u.get(\"marka\") or [], evren, ek)\n"
     "        baslik_uyum = arama.baslik_marka_uyumlari(u.get(\"baslik\"), kanon)",
     "    harita = dict()\n    for u in urunler:\n"
     "        if not isinstance(u, dict):\n            continue\n"
     "        uid = u.get(\"id\")\n        if not uid:\n            continue\n"
     "        uyeler = mmb.marka_uyelikleri(u.get(\"marka\") or [], evren, ek)\n"
     "        baslik_uyum = arama.baslik_marka_uyumlari(u.get(\"baslik\"), kanon)",
     "YESIL"),
    ("KONTROL K2 iddia edilmeyen eksen (sema aciklama metni)",
     "d1-sema.sql",
     "  -- MARKA ARAMA UYELIGI (5 Agu 2026)",
     "  -- MARKA ARAMA UYELIGI  (5 Agu 2026)", "YESIL"),
    ("KONTROL K3 davranissiz yazim (baslik jetonlamasinda uyumlar = [] -> list())",
     "arama.py",
     "    uyumlar = []\n    i, n = 0, len(kel)",
     "    uyumlar = list()\n    i, n = 0, len(kel)", "YESIL"),
]


def kendini_test():
    """TURETICI CAPANIN KENDI BATARYASI — mutantlari kosmaz, yalnizca `m7_capa`yi olcer.

    Merkez iddia: kolon listesi BUYUDUGUNDE capa hala cozulur (bayatlamaz). Iddialar
    GERCEK `d1-sync.py`ye degil, tmp'ye yazilip geri okunan IZOLE KOPYAlara uygulanir;
    gercek ev yoluna hicbir yazma/silme YOK.
    """
    iddia = []

    def ONA(kosul, ad, ek=""):
        iddia.append((bool(kosul), ad, ek))

    tmp = tempfile.mkdtemp(prefix="m7-capa-kendini-test-")
    try:
        kaynak_yolu = os.path.join(TOOLS, "d1-sync.py")
        gercek = open(kaynak_yolu, encoding="utf-8").read()

        def izole(metin, etiket):
            """Metni tmp'ye YAZ, geri OKU, capayi o kopyaya uygula (izolasyon kaniti)."""
            yol = os.path.join(tmp, "d1-sync-%s.py" % etiket)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin)
            return m7_capa(open(yol, encoding="utf-8").read())

        # ── V1 GERCEK KAYNAK: capa COZULUR ve tam bir kez eslesir ────────────────
        c1 = m7_capa(gercek)
        ONA(c1 is not None, "V1 gercek `d1-sync.py`de capa COZULDU (CAPA-YOK degil)")
        eski1 = None
        if c1:
            eski1, yeni1 = c1
            ONA(gercek.count(eski1) == 1,
                "V1b turetilen capa kaynakta TAM BIR KEZ gecer", "sayi=%d" % gercek.count(eski1))
            kaynak_liste = ast.literal_eval(eski1.split(" = ", 1)[1])
            yeni_liste = ast.literal_eval(yeni1.split(" = ", 1)[1])
            ONA(yeni_liste == kaynak_liste + ["marka_arama"],
                "V1c mutant listeyi KORUYUP `marka_arama` EKLER (kolon SILMEZ)",
                repr(yeni_liste))
            ONA(len(kaynak_liste) >= 3,
                "V1d kaynak listesi bos degil (%d kolon okundu)" % len(kaynak_liste))

        # ── V2 SENTETIK BUYUME: liste bir kolon daha alinca capa HALA cozulur ────
        # Kabul sartinin ta kendisi: bayatlama sinifi geri gelirse BU iddia kirmizi yanar.
        if eski1 is None:
            # V1 dustuyse turetilmis capa yok; sonraki iddialar OLCULEMEZ (yesil SAYILMAZ).
            ONA(False, "V2-V6 OLCULEMEDI: V1 dustugu icin turetilmis capa yok")
            eski1 = "ZORUNLU_KOLONLAR = []"
        buyumus = gercek.replace(
            eski1, eski1[:-1] + ', "sentetik_kolon_k380"]', 1)
        ONA(buyumus != gercek, "V2a sentetik buyume IZOLE kopyaya uygulandi")
        c2 = izole(buyumus, "buyumus")
        ONA(c2 is not None,
            "V2 BUYUMUS listede capa HALA COZULDU (sabit dizge olsaydi CAPA-YOK olurdu)")
        if c2:
            eski2, yeni2 = c2
            ONA(buyumus.count(eski2) == 1, "V2b buyumus kopyada capa TAM BIR KEZ gecer")
            yeni2_liste = ast.literal_eval(yeni2.split(" = ", 1)[1])
            ONA("sentetik_kolon_k380" in yeni2_liste,
                "V2c yeni kolon KORUNDU (capa eski uclu yazimi geri yazmiyor)", repr(yeni2_liste))
            ONA("marka_arama" in yeni2_liste, "V2d `marka_arama` yine EKLENDI")
            ONA(compile(buyumus.replace(eski2, yeni2, 1), "<m7>", "exec") is not None,
                "V2e mutasyona ugramis kaynak PYTHON olarak DERLENIR (bozuk metin uretmiyor)")

        # ── V3-V6 FAIL-CLOSED: cozulemeyen her hal None doner (sessiz yesil YOK) ─
        ONA(izole(gercek.replace(eski1 + "\n", "", 1), "atamasiz") is None,
            "V3 atama SILINMISSE capa None (batarya ADIYLA kirmizi yanar)")
        ONA(izole(gercek.replace(eski1, eski1[:-1] + ', "marka_arama"]', 1), "zaten") is None,
            "V4 `marka_arama` LISTEDE ZATEN varsa None (NO-OP mutant kutsanmaz)")
        ONA(izole(gercek + "\n" + eski1 + "\n", "ikili") is None,
            "V5 atama IKI KEZ geciyorsa None (belirsiz capa yesil sayilmaz)")
        ONA(izole(gercek.replace(eski1, "ZORUNLU_KOLONLAR = [*_TABAN]", 1), "literalsiz") is None,
            "V6 sag taraf LITERAL degilse None (ayristirilamayan capa yesil sayilmaz)")

        # ── V7 NON-GROWTH NOBETI: M7 capasi TEKRAR sabit dizgeye cevrilirse kirmizi ─
        m7 = [m for m in MUTANTLAR if m[0].startswith("OLDURUCU M7 ")]
        ONA(len(m7) == 1, "V7a batarya M7 mutantini TAM BIR KEZ tasiyor")
        ONA(bool(m7) and callable(m7[0][2]),
            "V7 M7 capasi TURETICI FONKSIYON (sabit dizgeye geri cevrilirse bu iddia duser)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nM7 TURETICI CAPA — KENDINI TEST")
    kaldi = 0
    for tamam, ad, ek in iddia:
        kaldi += 0 if tamam else 1
        print("   %s %s%s" % ("GECTI" if tamam else "KALDI", ad,
                              ("\n      " + str(ek)) if (ek and not tamam) else ""))
    print("\nIDDIA: %d gecti | %d KALDI" % (len(iddia) - kaldi, kaldi))
    if kaldi:
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅")
    return 0


# (ad, eski, yeni, beklenen, eksen) — hedef kapi: `--kendini-test`.
# Her OLDURUCU, capa turetiminin BIR yuklemini bozar ve o iddiayi ADIYLA dusurmelidir;
# "kirmizi yandi" tek basina yeterli DEGILDIR ([[beyan-edilmis-survivor]]).
#
# 🔴 TABLO KIRPILIR — YOKSA CAPA KENDI ICINDE COGALIR. Mutant metinleri bu dosyanin
# ICINDE durdugu icin, capa dizgesi hem GOVDEDE hem TABLODA gecer: ilk kosumda olculdu
# `CAPA-YOK(5)` / `CAPA-YOK(2)` — yani hicbir mutant uygulanamadi
# ([[kurucu-capa-yeni-icinde-cogaltir]]). Kopya uretilirken asagidaki iki nobetci satirin
# ARASI bosaltilir; bu yuzden ikisi de AYNEN korunmali.
# >>> CAPA-MUTANT-TABLOSU-BASI <<<
CAPA_MUTANTLARI = [
    ("OLDURUCU N1 CAPAYI TEKRAR SABIT DIZGEYE CEVIR (bayatlama sinifinin ta kendisi)",
     "    bulunan = _ZORUNLU_KOLONLAR_RE.findall(taban)",
     "    return ('ZORUNLU_KOLONLAR = [\"tur\", \"stokta\", \"uyum\"]',\n"
     "            'ZORUNLU_KOLONLAR = [\"tur\", \"stokta\", \"uyum\", \"marka_arama\"]')\n"
     "    bulunan = _ZORUNLU_KOLONLAR_RE.findall(taban)", "KIRMIZI", "V1b"),
    ("OLDURUCU N2 NO-OP MUTANT URET (yeni == eski: hicbir sey degistirmez)",
     "    yeni = \"ZORUNLU_KOLONLAR = [%s]\" % \", \".join(\n"
     "        '\"%s\"' % k for k in list(liste) + [\"marka_arama\"])",
     "    yeni = eski", "KIRMIZI", "V1c"),
    ("OLDURUCU N3 KOLONU EKLEME, LISTEYI EZ (buyumus kolonlar SILINIR)",
     "    yeni = \"ZORUNLU_KOLONLAR = [%s]\" % \", \".join(\n"
     "        '\"%s\"' % k for k in list(liste) + [\"marka_arama\"])",
     "    yeni = 'ZORUNLU_KOLONLAR = [\"tur\", \"stokta\", \"uyum\", \"marka_arama\"]'",
     "KIRMIZI", "V2c"),
    ("OLDURUCU N4 BELIRSIZ CAPAYI KABUL ET (iki atama varken de coz)",
     "    if len(bulunan) != 1:\n        return None",
     "    if len(bulunan) < 1:\n        return None", "KIRMIZI", "V5"),
    ("OLDURUCU N5 NO-OP KAPISINI KALDIR (`marka_arama` zaten varken de mutant uret)",
     "    if \"marka_arama\" in liste:\n        return None",
     "    if False:\n        return None", "KIRMIZI", "V4"),
    ("OLDURUCU N6 COZULEMEYENDE SESSIZ CIFT DON (fail-open: CAPA-COZULMEDI hic yanmaz)",
     "    bulunan = _ZORUNLU_KOLONLAR_RE.findall(taban)\n"
     "    if len(bulunan) != 1:\n        return None",
     "    bulunan = _ZORUNLU_KOLONLAR_RE.findall(taban)\n"
     "    if len(bulunan) != 1:\n        return (\"ZORUNLU_KOLONLAR\", \"ZORUNLU_KOLONLAR\")",
     "KIRMIZI", "V3"),
    ("KONTROL O1 iddia edilmeyen eksen (yorum metni)",
     "    None doner (=> batarya ADIYLA `CAPA-COZULMEDI` KIRMIZI yakar, sessiz 0 YOK) su",
     "    None doner (=> batarya ADIYLA `CAPA-COZULMEDI` KIRMIZI yakar; sessiz 0 YOK) su",
     "YESIL", None),
    ("KONTROL O2 davranissiz yazim (`list(liste)` -> dilim kopyasi)",
     "        '\"%s\"' % k for k in list(liste) + [\"marka_arama\"])",
     "        '\"%s\"' % k for k in liste[:] + [\"marka_arama\"])", "YESIL", None),
]
# >>> CAPA-MUTANT-TABLOSU-SONU <<<


def capa_mutasyonu():
    """TURETICI CAPANIN MUTASYON BATARYASI — hedef kapi: `--kendini-test`.

    🔴 MUTANT IZOLE KOPYADA ve BENZERSIZ ADLA kosar, `-B` (dont_write_bytecode) ile.
    Bu evde olculdu: ayni ada yazilan mutantlarda CPython bytecode onbellegi ikinci
    mutanta BIRINCININ kodunu kosturuyor ve sahte "KACTI" uretiyordu. Gercek ev yoluna
    hicbir yazma/silme YOK.
    """
    kaynak = os.path.abspath(__file__)
    ham = open(kaynak, encoding="utf-8").read()
    # 🔴 NOBETCI DIZGESI PARCALI YAZILIR: butun halde yazilsaydi BU SATIRLARIN KENDISI de
    # eslesir ve sayim 1 yerine 2 cikardi (aracin kendi metni kendi capasini cogaltir —
    # ilk kosumda tam bu oldu, kirpma "yapilamaz" dedi).
    bas = ">>> CAPA-MUTANT-" + "TABLOSU-BASI <<<"
    son = ">>> CAPA-MUTANT-" + "TABLOSU-SONU <<<"
    if ham.count(bas) != 1 or ham.count(son) != 1:
        print("\nSONUC: KIRMIZI ❌  (tablo nobetci satirlari bulunamadi — kirpma YAPILAMAZ)")
        return 1
    # Tabloyu BOSALT: capa dizgeleri artik yalnizca GOVDEDE gecer, tam bir kez.
    taban = (ham[:ham.index(bas)] + bas + "\nCAPA_MUTANTLARI = []\n# " + son
             + ham[ham.index(son) + len(son):])
    tmp = tempfile.mkdtemp(prefix="m7-capa-mutasyon-")
    sonuc = []
    try:
        # AYNA: mutant, `d1-sync.py`yi kendi TOOLS'undan cozer -> tools/ symlink aynasi.
        ayna = os.path.join(tmp, "tools")
        os.makedirs(ayna)
        for ad_ in os.listdir(TOOLS):
            os.symlink(os.path.join(TOOLS, ad_), os.path.join(ayna, ad_))
        for i, (ad, eski, yeni, beklenen, eksen) in enumerate(CAPA_MUTANTLARI):
            if taban.count(eski) != 1:
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            # 🔴 BENZERSIZ AD: ayni ada yazilan mutantlarda CPython bytecode onbellegi
            # sahte "KACTI" uretiyor (bu evde olculdu). `-B` ayrica .pyc yazmayi kapatir.
            yol = os.path.join(ayna, "m7-mutant-%d-%d.py" % (i, os.getpid()))
            with open(yol, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run([sys.executable, "-B", yol, "--kendini-test"],
                               capture_output=True, text=True, cwd=tmp)
            cikti = r.stdout + r.stderr
            m = re.search(r"^IDDIA: (\d+) gecti \| (\d+) KALDI", cikti, re.M)
            if not m:
                gozlem = "COKME(IDDIA satiri YOK: %s)" % cikti.strip().split("\n")[-1][:80]
            else:
                gecti, kaldi = int(m.group(1)), int(m.group(2))
                gozlem = "KIRMIZI" if kaldi else "YESIL"
                if eksen and gozlem == "KIRMIZI":
                    dusen = re.findall(r"^ *KALDI (.*)$", cikti, re.M)
                    if not any(s.startswith(eksen + " ") for s in dusen):
                        gozlem = "EKSEN-YOK(%s dusmedi)" % eksen
                gozlem += " (gecti=%d KALDI=%d%s)" % (
                    gecti, kaldi, " eksen=" + eksen if eksen else "")
            sonuc.append((ad, beklenen, gozlem))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nM7 TURETICI CAPA — MUTASYON (hedef kapi: --kendini-test)")
    kalan = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-78s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


def ayna_kur(tmp):
    """ROOT'un SALT OKUNUR aynasi: tools/ gercek bir dizin (icindekiler symlink), digerleri
    dogrudan symlink. Kapi kendi TOOLS/ROOT'unu bu aynadan cozer."""
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        os.symlink(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    return kok


def main():
    tmp = tempfile.mkdtemp(prefix="marka-arama-mutasyon-")
    sonuc = []
    try:
        for mutant in MUTANTLAR:
            ad, dosya, eski, yeni, beklenen = mutant[:5]
            eksen = mutant[5] if len(mutant) > 5 else None
            kaynak_yolu = os.path.normpath(os.path.join(TOOLS, dosya))
            taban = open(kaynak_yolu, encoding="utf-8").read()
            if callable(eski):
                # TURETILEN CAPA: cozulemezse ADIYLA KIRMIZI — sessiz "0" DEGIL.
                cozum = eski(taban)
                if cozum is None:
                    sonuc.append((ad, beklenen,
                                  "CAPA-COZULMEDI(%s: capa %s kaynagindan turetilemedi)"
                                  % (ad.split()[1] if len(ad.split()) > 1 else "?", dosya)))
                    continue
                eski, yeni = cozum
            if taban.count(eski) != 1:
                # 🔴 CAPA TAM BIR KEZ ESLESMELI. Kaymissa "mutant uygulanamadi" YESIL
                # sayilmaz; kanit OLCULEMEDI'dir.
                sonuc.append((ad, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            kok = ayna_kur(os.path.join(tmp, str(len(sonuc))))
            hedef = os.path.normpath(os.path.join(kok, "tools", dosya))
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(taban.replace(eski, yeni, 1))
            r = subprocess.run([sys.executable, os.path.join(kok, "tools", KAPI_ADI)],
                               capture_output=True, text=True, cwd=kok)
            cikti = r.stdout + r.stderr
            fail = len(re.findall(r"^ *KALDI ", cikti, re.M))
            gecti = len(re.findall(r"^ *GECTI ", cikti, re.M))
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d: %s)" % (r.returncode,
                                               cikti.strip().split("\n")[-1][:90])
            elif r.returncode == 1 and fail == 0:
                gozlem = "COKME(kirmizi ama olculen iddia yok)"
            elif gecti < TABAN_GECTI:
                gozlem = "COKME(olculen GECTI sayisi dusuk: %d)" % gecti
            else:
                gozlem = "KIRMIZI" if r.returncode == 1 else "YESIL"
            if eksen and gozlem == "KIRMIZI":
                # TEKIL EKSEN SARTI: kirmizi yeterli DEGIL, O iddia dusmus olmali.
                dusen = re.findall(r"^ *KALDI (.*)$", cikti, re.M)
                if not any(eksen in s for s in dusen):
                    gozlem = "EKSEN-YOK(%s dusmedi)" % eksen
            sonuc.append((ad, beklenen, "%s (KALDI=%d GECTI=%d%s)"
                          % (gozlem, fail, gecti, " eksen=%s" % eksen if eksen else "")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapi: tools/%s)" % KAPI_ADI)
    kalan = 0
    for ad, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-86s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU kirmizi, her KONTROL yesil)"
          % len(sonuc))
    return 0


if __name__ == "__main__":
    if "--kendini-test" in sys.argv[1:]:
        sys.exit(kendini_test())
    if "--mutasyon" in sys.argv[1:]:
        sys.exit(capa_mutasyonu())
    sys.exit(main())

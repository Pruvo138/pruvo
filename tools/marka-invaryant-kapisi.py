#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA INVARYANT KAPISI — "sayfa ile arama AYNI urunu gostermeli" (TABAN CIVILI).

OKAN HUKMU: "TUM markalarda sayfa ve arama urun adetlerinin ayni olmasi." Bu kapi o
hukmun tek tek yama DEGIL, INVARYANT olarak olculdugu yerdir.

═══ NE OLCULUR ═══════════════════════════════════════════════════════════════════
Her kanonik marka `b` icin UC kume kurulur ve ikili farklari sayilir:

  SAYFA  (b)  /marka/<slug>/ sayfasinin gosterdigi urunler.
              KAYNAK: marka_model_build.gruplandir + marka_urun_sayisi (TEK KAYNAK —
              ikinci bir toplama formulu YAZILMAZ; S ekseni bunu kilitler).
  FILTRE (b)  Uctaki (Worker) `?marka=b` kolunun DONDURDUGU kume — D1 `marka_kanon`
              uyeligi. Kolon sayfa/cip ile AYNI marka_uyelikleri kaynagindan turer;
              aksan/bosluk/kasa katlamasi ikinci bir govde acmadan uygulanir.
  ARAMA  (b)  `?q=b` kolunun donduru kume. Marka ADIYLA yapilan sorgu artik SERBEST METIN
              DEGIL, GECIS KURALIDIR (arama.marka_sorgusu_esler): UYELIK ∪ BASLIKTA TAM
              KELIME. Marka OLMAYAN sorgu (jant kapagi, mentese) eskisi gibi serbest
              metindir — bu kapi onu `arama.esles` ile olcmeye devam eder.

  FILTRE_KAYIP(b) = |SAYFA − FILTRE|   🔴 MUSTERI CIPE BASINCA URUNU KAYBEDER
  FILTRE_FAZLA(b) = |FILTRE − SAYFA|   (yapisal olarak 0 olmali — asagida)
  ARAMA_KAYIP (b) = |SAYFA − ARAMA|    🔴 URUN SAYFADA VAR, ARAMADA YOK
  ARAMA_FAZLA (b) = |ARAMA − SAYFA|    (gurultu ekseni — BLOKLAMAZ, bkz. ne_olculmedi)

═══ MODEL AGA CIKMAZ ══════════════════════════════════════════════════════════════
Kapi CI'da deterministik olmak zorunda oldugu icin uc davranisini YEREL PORTLA modeller.
`?marka=` modeli D1'e senkronlanan kanonik uyelik hedefidir; canli kolonun tazeligi ayri
`d1-sync.py --durum` olcumudur. Tarihsel ham-esitlik modeli 4 Agu 2026'da canliyla
128/128 eslesmisti; kanonik kolon bu kayip sinifini kapatmak icin sonradan eklendi:

    hedef `?marka=`             ↔  D1 `marka_kanon` uyeligi
    canli `?q=`     (128 marka)  ↔  o gunku SERBEST METIN portu   : 128/128 BIREBIR
    canli marka sayfasi adedi    ↔  marka_urun_sayisi             : 128/128 BIREBIR

🔴 `?q=` SATIRI 5 AGU 2026'DA BILEREK KOPARILDI: marka sorgusu bu depoda uyelik yuklemine
baglandi, canli Worker (HocA deposu) hala serbest metin kosuyor. Yani ARAMA modeli artik
CANLI `?q=` KOLUNU DEGIL, deponun KANONIK YUKLEMINI olcer; uc benimseyene kadar ikisi
AYRIDIR ve bu ne_olculmedi()'de HER KOSUMDA ilan edilir.

Model canliyla AYRISABILIR (uc kodu bu depoda DEGIL) — bu sinir ne_olculmedi()'de ACIKCA
ILAN EDILIR.

═══ NEDEN TABAN CIVILI (mevcut borc bloklamaz, REGRESYON bloklar) ═════════════════
Olculen borc (5 Agu): FILTRE_KAYIP 9 marka / 120 kalem · ARAMA_KAYIP 0 (marka sorgusu
uyelige baglandiktan sonra; oncesinde 2 marka / 4 kalem idi).
Bu borcu bugun kirmizi yakan bir kapi TUM ekibin yayinini durdururdu ve borcu KAPATMAZDI
([[kapi-birikimi-yayin-gecikmesi]]). Bu yuzden bugunku degerler `marka-invaryant-taban.json`
dosyasina MARKA MARKA civilenir; kapi yalnizca sayi TABANIN USTUNE CIKARSA kirmizi yanar.

🔴 CIRCIR (ratchet) — DUSUS DE KIRMIZIDIR: olculen deger tabanin ALTINA inerse kapi
DURUR ve tabanin guncellenmesini ister. Gerekcesi [[beyan-edilmis-survivor]]: taban
gevsek kalirsa borc kapandiktan SONRA aynen geri gelebilir ve kapi YESIL yanar — yani
kapinin tek degeri (civi) kaybolur. Dusus URUN EKLEMEYLE OLUSMAZ (yeni urun bir markanin
kaybini artirabilir, azaltamaz); yalnizca ONARIM ya da urun SILME dusurur, ikisi de
kasitlidir. Cozum tek satir: `python3 tools/marka-invaryant-kapisi.py --taban-yaz`.

🔴 NEDEN AGREGE DEGIL MARKA MARKA: toplam, tekil ekseni gizler ([[hukum-yanlis-birimde]]).
Volvo 106 → 96 inerken Ford 0 → 10 ciksa toplam AYNI kalir ve kapi YESIL yanardi.

🔴 NEDEN ADET DEGIL KUME: "sayfa 726 · arama 734" gibi bir SAYI farki, iki kumenin
birbirini kismen kacirdigini gizler (Opel'de olculdu: adet farki −4, ama sayfada olup
aramada OLMAYAN 3 + aramada olup sayfada olmayan 7). Kume farki iki YONU AYRI olcer.

═══ TOTOLOJI TUZAGI VE CAPALAR ════════════════════════════════════════════════════
Iki ucu da AYNI sonuc kumesinden turetirsek kapi HER ZAMAN yesil yanar. Bes savunma:
  1. FILTRE urunleri HAM `marka[]`dan AYRI AYRI yurutup ortak marka_uyelikleri kanonuna
     baglar; sentetik aksan fiksturu ham esitlige geri donusu katalogdan bagimsiz yakalar.
  2. POZITIF CAPA: adi civili, katlama OLMADAN uye OLAMAYACAK 5 gercek urun, kendi
     markasinin HEM sayfasinda HEM aramasinda BULUNMALI ve katalogda TAM BIR KEZ gecmeli.
     Katlama kapatilirsa capalar SAYFA kumesinden duser -> kapi kirmizi.
  3. S EKSENI: kurulan SAYFA kumesinin buyuklugu, deponun kanonik sayma fonksiyonu
     (marka_urun_sayisi) ile BIREBIR esit olmali — ikinci bir toplama formulu dogamaz.
  4. 🔴 UYUM CAPASI (marka sorgusu gecis kuralina OZEL). Marka sorgusu uyelige baglaninca
     ARAMA ⊇ SAYFA YAPISAL hale gelir: ARAMA_KAYIP ekseni artik TOTOLOJIDIR (bkz.
     ne_olculmedi). Onun yerine, baslikta markayi TAM KELIME tasiyip UYELIGI OLMAYAN gercek
     urunler civilenir; her biri ARAMADA VAR ama SAYFADA YOK olmalidir. "srch = sayfa"
     totolojisi de, "saf uyelige gec" gerilemesi de bu capayi dusurur -> kapi kirmizi.
  5. 🔴 GURULTU CAPASI: serbest metnin markaya YANLIS BAGLADIGI urunler (Havalandirma ->
     "Haval", Mandali -> "MAN", 43mm -> "3M") ARAMADA OLMAMALI. Marka sorgusu serbest metne
     GERI cevrilirse bu capalar ARAMADA belirir -> kapi kirmizi.
Mutasyon kaniti REPODA KOSULABILIR: tools/marka-invaryant-mutasyon.py
([[mutasyon-kaniti-yeniden-uretilebilir]] — anlatilan batarya kanit DEGILDIR).

Calistir:  python3 tools/marka-invaryant-kapisi.py        (0 yesil · 1 kirmizi · 2 olculemedi)
           python3 tools/marka-invaryant-kapisi.py --taban-yaz     (tabani YENIDEN yaz)
           python3 tools/marka-invaryant-kapisi.py --modul /gecici/mutant.py   (mutasyon)
"""
import argparse
import importlib.util
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

TABAN_VARSAYILAN = os.path.join(TOOLS, "marka-invaryant-taban.json")

# ── POZITIF CAPA ────────────────────────────────────────────────────────────────
# (urun id, kanonik marka, katlamanin TURU). Her biri OLCULDU (4 Agu): urunun `marka`
# dizisi kanonik adi HAM olarak TASIMAZ -> uyelik yalnizca katlamayla dogar. Bes ayri
# katlama mekanizmasi secildi ki tek bir mekanizmayi kapatan mutant capayi kacirmasin.
CAPALAR = [
    ("sierra-hava-filtresi-18-7908", "Volvo", "onek katlamasi (Volvo Penta -> Volvo)"),
    ("peugeot-citroen-2-pinli-elektrik-konnektoru", "Citroen", "aksan (Citroen yazimi)"),
    ("black-decker-zimpara-vakum-adaptoru", "Black+Decker", "ayirac (and/& /+ tek bicim)"),
    ("hyundai-ve-kia-g-s-paneli-klipsi", "Kia", "buyuk/kucuk harf (KIA -> Kia)"),
    ("datsun-mido-far-arka-kapagi", "Datsun", "onek katlamasi (Datsun MiDo -> Datsun)"),
]

# ── UYUM CAPASI — DINAMIK SECIM (sabit id CIVILENMEZ) ───────────────────────────
# 🔴 NEDEN SABIT ID DEGIL (olculen, YAPISAL sorun): bu capalarin havuzu "baslikta markayi TAM
# KELIME anip uyeligi OLMAYAN urunler"dir ve o havuz VERI PARTILERIYLE SURekli BOSALIR —
# tam da amaci budur (MaCiT'in uyelik partisi ARAMA_FAZLA'yi 6.503 -> 504 -> 75'e indirdi).
# Sabit id civilenirse capa BAYATLAR ve kapi iki kotu secenekten birine dusUr:
#   (1) sahte KIRMIZI yakip tum ekibin yayinini durdurur (5 Agu'da AYNEN yasandi: MaCiT'in
#       partisi capa urunlerine uyelik yazdi, kapi birlesmis agacta 3 FAIL verdi), ya da
#   (2) capa elle "guncellenip" iddia sessizce kaybolur.
# COZUM: capa KOSUM ANINDA olculen havuzdan DETERMINISTIK secilir (asagida).
#
# 🔴 HAVUZ `srch - sayfa`DAN DEGIL, VERI ILISKISINDEN (baslik_uyum \ uyelik) KURULUR.
# Sebep KENDINI-DOGRULAMA tuzagi: havuzu ARAMA kumesinden turetseydik, ARAMA'yi bozan bir
# mutant (ornegin `srch = set(sayfa)`) havuzu da BOSALTIR ve kapi "olculemedi" deyip
# gecerdi. Veri iliskisi mutanttan BAGIMSIZDIR: mutant altinda havuz DOLU kalir, capa
# "aramada VAR" iddiasi KIRMIZI yanar.
UYUM_CAPA_ADEDI = 3      # kac capa secilir (ayarlanabilir; artirmak iddiayi guclendirir)
UYUM_CAPA_ASGARI = 3     # CIVILI TABAN: bu sayidan az capa OLCULDUYSE iddia YOK sayilir.
#                          ADEDI'den AYRI durur: ADEDI'yi 0'a indiren bir mutant, kendi
#                          esigini de dusurerek sessizce yesil gecemesin.

# ── SEMANTIK FIKSTUR — KATALOGDAN BAGIMSIZ (bayatlamaz) ─────────────────────────
# 🔴 Dinamik capanin bilinen zayifligi: mutasyona UYUM SAGLAR. Jetonlama kuralini bozan bir
# mutant (onek katlamasini metne sizdirmak, cok kelimeli markayi bolmek) havuzun ICERIGINI
# degistirir ve dinamik secim yeni havuzdan yine gecerli capalar secer. O yuzden jetonlama
# SEMANTIGI sabit dizgelerle civilenir — bunlarin katalogla HICBIR bagi yoktur, veri partisi
# bayatlatamaz. (baslik, ICERMELI, ICERMEMELI, ne kanitlar)
BASLIK_FIKSTURLERI = [
    ("Land Rover Defender Kapi Kolu Kapagi", ["Land Rover"], ["Rover"],
     "UZUN-ONCE: bigram tutunca tekil 'Rover' URETILMEZ (farkli marque)"),
    ("Rover 75 Torpido Klipsi", ["Rover"], [],
     "KONTROL: 'Land' oneki YOKKEN tekil Rover DOGAR (kural 'Rover'i hep ezmek degil)"),
    ("Sierra 18-8076 Yamaha Mercury Ortak Tip Benzin Fisi", ["Yamaha", "Mercury"], [],
     "ONEK KATLAMASI METINDE YOK: bitisik ikinci marka jetonu YUTULMAZ"),
    ("Alfa Romeo 156 Vites Topuzu", ["Alfa Romeo"], [],
     "COK KELIMELI marka BUTUN kalir"),
    ("Suzuki Samurai Kalorifer Havalandirma Dugmesi", [], ["Haval"],
     "MORFOLOJIK GURULTU: 'Havalandirma' TAM KELIME 'Haval' DEGILDIR"),
    ("Bagaj Ici 43mm Kece Montaj Aleti", [], ["3M"],
     "ALT-DIZE GURULTUSU: '43mm' icindeki '3m' marka DEGILDIR"),
]

# ── KALICI KIRMIZI (yapisal kayip; taban mekanizmasi DISI, her kosumda KIRMIZI) ─
# Spec K140 hükmu: model jetonlari evren DISINA dusurulunce kalan KIRMIZI yalniz GERCEK
# kayiplari gosterir. Bu liste o gercek kayiplardan taban mekanizmasiyla SUSMAYACAK olanlari
# barindirir. Hukuk gerekcesi ([[beyan-edilmis-survivor]]): taban circiri borc kapandiktan
# sonra geri gelmeyi engeller — bu liste "geri gelmemesini istemedigimiz borc" degil,
# "GERCEK BIR AÇIK" — yani /marka/<X>/ sayfasinin olmasi/yayinda olmasi gerekip de
# olmayan urun. Rover: sayfa uretiminin tekil "Rover" icin acilmamis olmasi + cip
# evreniyle eszamanli sayfa uretiminin kapatilmis olmasi; onarim ayri kalem ([[k140-spec]]).
KALICI_KIRMIZI = {
    "ARAMA_KAYIP": {"Rover"},       # gercek kayip: rover sayfasi yok, urun kayboluyor
}

# ── GURULTU CAPASI (serbest metne geri donusu yakar) ────────────────────────────
# (urun id, kanonik marka, gurultu sinifi). Her biri BUGUN serbest metin `?q=<marka>`
# sonucunda CIKIYOR ve HICBIRI o markayla ilgili DEGIL. Marka sorgusu uyelige baglandiktan
# sonra ARAMADA OLMAMALI.
#
# 🔴 K140 KAYNAK DEGISIMI: 3M artik evren DISI (TANINMIS_MARKALAR'a dahil degil); eski
# alt-dize capasinin ("43mm" -> "3M") bir karsiligi yok, cunku evrende olmayan marka
# icin ARAMA zaten bos. Bu sutun kaldirildi: ayni alt-dize riski "Acer" (iceride "acer"
# gecmez) ya da "Anker" ("anker" icinde "nker" alt-dizesi) ile kapansa da 3M-katlamasi
# YOK. Kalan 3 capa yeterli — serbest metne GERI donusu uc ayri gurultu sinifinda yakalar.
GURULTU_CAPALARI = [
    ("suzuki-samurai-kalorifer-havalandirma-dugmesi", "Haval",
     "morfolojik (Havalandirma -> 'haval')"),
    ("nissan-altima-torpido-gozu-mandali", "MAN", "morfolojik (Mandali -> 'man')"),
    ("land-rover-defender-orta-konsol-govdesi-1997-2000", "Rover",
     "farkli marque ayni ad (Land Rover -> 'Rover'; UZUN-ONCE kurali keser)"),
]

FAILS = []
BILGI = []


def kontrol(ad, kosul):
    if kosul:
        print("  PASS  " + ad)
    else:
        FAILS.append(ad)
        print("  FAIL  " + ad)


def olculemedi(sebep):
    print("\nSONUC: OLCULEMEDI ❓  " + sebep)
    sys.exit(2)


def ne_olculmedi():
    """BEYAN — bu kapinin GORMEDIGI eksenler. Sessiz kalmasin diye HER kosumda basilir."""
    print("\nNE OLCULMEDI (beyan):")
    print("  1. CANLI UC KODU. Worker (`?marka=` / `?q=` kollari) BU DEPODA DEGIL. Kapi")
    print("     D1 `marka_kanon` HEDEFINI ve yerel arama portunu modeller; canli kolon/uc")
    print("     degisirse model SESSIZCE ayrisabilir. O ekseni ancak")
    print("     canli olcum kapatir (ag cagrisi CI'da deterministik degildir).")
    print("  2. ARAMA_FAZLA (aramada SAYFADAN FAZLA cikan urun) BLOKLAMAZ, yalnizca BASILIR.")
    print("     Marka sorgusu uyelige baglandiktan sonra bu sayi artik GURULTU degil, GECIS")
    print("     BORCUDUR: baslikta markayi TAM KELIME anip `marka[]` uyeligi olmayan gercek")
    print("     urunler (Sierra/Teleflex marin parcalari, GoPro/TomTom aparatlari). Veri")
    print("     tarafi tamamlandikca kendiliginden erir; KATALOG BUYUDUKCE de artar, o")
    print("     yuzden civilenmez (her urun partisi kapiyi kirmizi yakardi).")
    print("     🔴 AYNI SAYI UYUM CAPA HAVUZUDUR ve TUKENMESI BEKLENIR (6.503 -> 504 -> 75).")
    print("     Havuz UYUM_CAPA_ASGARI'nin altina inince kapi YESIL DEMEZ, OLCULEMEDI der;")
    print("     o an insan karari gerekir: ekseni emekli et ya da FIKSTURlerle surdur.")
    print("  3. 🔴 ARAMA_KAYIP EKSENI ARTIK TOTOLOJIYE YAKINDIR. Marka sorgusu UYELIK ∪")
    print("     BASLIK oldugundan ARAMA ⊇ SAYFA yapisaldir; bu eksenin 0 olmasi bir SONUC")
    print("     degil, kurulusun sonucudur. Gercek olcum yuku UYUM/GURULTU CAPALARINA ve")
    print("     Q eksenine (marka sorgusunun kablolu olmasi) tasinmistir.")
    print("  4. D1 `marka_kanon` KOLONUNUN CANLI DEGERI. Kapi urunler.json'dan turetilen")
    print("     HEDEF degeri olcer; canli D1'de ne yazdigini OLCMEZ (o `d1-sync --durum`).")
    print("  5. 🔴 UCTAKI `?q=` KOLU HENUZ GECIS KURALINI UYGULAMIYOR. Worker (pruvo-bot,")
    print("     HocA deposu) `hs` kolonunda alt-dize aramasi yapmaya DEVAM eder; bu depo")
    print("     yalnizca kanonik yuklemi (arama.marka_sorgusu_esler) ve istemci yolunu")
    print("     (index.html MARKA SORGUSU blogu) tasir. Uc benimseyene kadar CANLI `?q=`")
    print("     sonuclari bu kapinin modelinden AYRIDIR — o eksen ancak canli olcum kapatir.")


# ── kaynaklar ───────────────────────────────────────────────────────────────────
def modul_yukle(yol):
    spec = importlib.util.spec_from_file_location("mmb_invaryant", yol)
    if spec is None:
        olculemedi("marka_model_build modulu yuklenemedi: %s" % yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def olc(mmb, arama, urunler, index_html):
    """Uc kumeyi kur. Doner: (veri, kumeler, serbeste_dusen, uyelik, baslik_uyum, kanon).
    kumeler = {marka: (sayfa, filtre, arama)}; serbeste_dusen = MARKA SORGUSU olarak
    TANINMAYIP serbest metne dusen kanonik markalar (0 olmali). `uyelik`/`baslik_uyum`
    urun basina iki AYRI kaynaktir ve UYUM CAPA HAVUZU onlardan kurulur (bkz. blok basi);
    `kanon` fikstur olcumunun kullandigi TEK KAYNAK marka-adi yargisidir.

    🔴 K140-ONARIM KAYNAK DEGISIMI: evren `cip_evreni_markalari()` EKLEMELI — gercek
    markalar (Sierra, NGK, Aprilia, Ducati, ...) `marka[0]`'da BIRINCIL olarak tasindigi
    icin evrene girer. Model jetonlari (1290/690/MT-07/...) urunde HER ZAMAN `marka[1+]`
    olarak IKINCIL — `marka_only` bos, sonraki satir onlari dogal olarak evren DISINA
    iter. Single source: `marka_uyelikleri`/`birincil_marka` (marka_model_build.py).
    Elle istisna listesi YASAK ([[ikiz-tanim-sessiz-ayrisma]]); M4 kapinin tek kaynagi
    izledigini olcer, M18 ikiz tanimi tetikler.
    """
    evren = mmb.MarkaEvreni(index_html)
    ek = mmb.cip_evreni_markalari(urunler, index_html)
    veri = mmb.gruplandir(urunler, evren, ek)
    # ONARIM A: model jetonlari ikincil-only ise evren DISI. `marka_only` bos olan kova
    # katalogda HICBIR urunun birincil markasi degil → gercek marka DEGIL, model/parca
    # kodu. Filtre marka_uyelikleri'nin marka[0] kolunu okur; single source (ek elle liste
    # YASAK). Bu satir sayesinde 7 model jetonu "kendiliginden" evren DISI. TAN'da olan
    # markalar her durumda tutulur (kuratorluk karari zaten orada).
    tan = set(evren.taninmis)
    veri = {m: d for m, d in veri.items() if m in tan or d["marka_only"]}

    # "Bu dizge bir MARKA ADI mi" yargisi TEK KAYNAKTAN (mmb.marka_adi_kanonu -> index.html
    # markaKatla portu + cip evreni). Bellek: ayni jeton katalog boyunca binlerce kez sorulur.
    ek_normlu = mmb.ek_marka_normlu(ek)
    _bellek = {}

    def kanon(dizge):
        if dizge not in _bellek:
            _bellek[dizge] = mmb.marka_adi_kanonu(dizge, evren, ek_normlu)
        return _bellek[dizge]

    hs = [(p.get("id"), arama.haystack(p)) for p in urunler]
    # 🔴 K140 KAYNAK DEGISIMI: _hedef_markalar artik marka_only VEYA ikincil iceren
    # markalari kapsar. Eski K133 filtresi (yalniz marka_only>0) model jetonlarini elemek
    # icin DARALTMISTI — fakat K140 ile model jetonlari zaten evren DISI (TANINMIS listesinde
    # olmadiklari icin `veri`'ye girmez). Bu genisletme Google/Huawei/Pontiac/Siemens gibi
    # "ikincil-only" markalarin baslik-uyelik kapsamina girmesini saglar (aksi halde
    # /marka/<X>/ sayfasinda gorunen urun ?marka=<X> filtresinde YOK — yapisal drift).
    _hedef_markalar = sorted(m for m, d in veri.items()
                              if d.get("marka_only") or d.get("ikincil"))
    _ad_kanonu, _azami_ad = mmb.baslik_uyelik_hazirlik(_hedef_markalar, evren)
    # URUN BASINA UC AYRI KAYNAK (gECis kuralinin iki kolu + filtre zenginlestirme):
    #   uyelik_sorgu = marka_model_build.marka_uyelikleri (marka[] DEN — UZUN-ONCE yok)
    #   baslik_uyum  = baslikta TAM KELIME marka uyumu (arama.baslik_marka_uyumlari;
    #                  UZUN-ONCE SINIFINDAN — Land Rover bigram tutunca tekil Rover URETILMEZ)
    #   uyelik_filtre = uyelik_sorgu + baslik_uyelikleri (FAZ 1B, sayfa kovasinin yaptigi
    #                   ayni islem, 23 model jetonu HARIC). UZUN-ONCE YOK (baslik_uyelikleri
    #                   kendi yapisinin parcasi); ANCAK `baslik_uyelikleri` YALNIZ FILTRE
    #                   icin kullanilir, ARAMA icin DEGIL — ARAMA uzun-once'yi `baslik_uyum`
    #                   uzerinden alir.
    uyelik_sorgu, uyelik_filtre, baslik_uyum = {}, {}, {}
    for p in urunler:
        pid = p.get("id")
        if not pid:
            continue
        uyeler = mmb.marka_uyelikleri(p.get("marka") or [], evren, ek)
        if not uyeler:
            continue
        uyelik_sorgu[pid] = list(uyeler)
        # FAZ 1B: baslik_uyelikleri (KANONIK - sayfa kovasinin yaptigi ayni islem). Ikinci
        # bir govde YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]); 23 model jetonu (marka_only==0)
        # HARIC tutulur → kendi marka sayfasi ayri yapisal soru olarak kalir.
        filtre_uyeler = list(uyeler)
        for kan in mmb.baslik_uyelikleri(p, evren, _ad_kanonu, _azami_ad, ek):
            if kan not in filtre_uyeler:
                filtre_uyeler.append(kan)
        uyelik_filtre[pid] = filtre_uyeler
        baslik_uyum[pid] = arama.baslik_marka_uyumlari(p.get("baslik"), kanon)

    kumeler, serbeste_dusen = {}, []
    for marka, d in veri.items():
        sayfa = set()
        for kaynak in ([g["urunler"] for g in d["gruplar"].values()]
                       + [d["marka_only"], d.get("ikincil", [])]):
            for p in kaynak:
                if p.get("id"):
                    sayfa.add(p["id"])
        # UCTAKI `?marka=` KOLU — D1 `marka_kanon` uyeligi. Hedef kolon
        # marka_uyelikleri ∪ baslik_uyelikleri'nden turetilir (K133, SPEC ADIM-2);
        # sayfa/cip/arama ayni kanonik katlamayi kullanir. Urunler TEK TEK yurur;
        # `filtre = sayfa` gibi sonuc-kumesi totolojisi kurulmaz.
        filtre = {pid for pid in uyelik_filtre if marka in uyelik_filtre[pid]}
        # `?q=<marka>` KOLU — MARKA SORGUSU ise gecis kurali, degilse serbest metin.
        # ARAMA K1224 (K133): uyelik_sorgu (marka_uyelikleri) + baslik_uyum (UZUN-ONCE)
        # ile calisir. baslik_uyelikleri (sayfa kovasi ile ayni) FILTREYE eklenir ama
        # ARAMAYA eklenmez — uzun-once olmadan «Rover» -> «Land Rover» bigraminda
        # tekil «Rover» URETILIR, GURULTU CAPASI (Rover-Land Rover) bozulur.
        kanon_marka = arama.marka_sorgu_kanonu(marka, kanon)
        if kanon_marka:
            srch = {pid for pid in uyelik_sorgu
                    if arama.marka_sorgusu_esler(kanon_marka, uyelik_sorgu[pid], baslik_uyum[pid])}
        else:
            serbeste_dusen.append(marka)
            tok = arama.tokenlar(marka)
            srch = {i for i, h in hs if i and arama.esles(h, tok)}
        kumeler[marka] = (sayfa, filtre, srch)
    return veri, kumeler, serbeste_dusen, uyelik_sorgu, baslik_uyum, kanon


def taban_kur(veri, kumeler, katalog):
    fk, ff, ak, af = {}, {}, {}, {}
    for marka, (sayfa, filtre, srch) in kumeler.items():
        if sayfa - filtre:
            fk[marka] = len(sayfa - filtre)
        if filtre - sayfa:
            ff[marka] = len(filtre - sayfa)
        if sayfa - srch:
            ak[marka] = len(sayfa - srch)
        if srch - sayfa:
            af[marka] = len(srch - sayfa)
    return {
        "_not": ("MARKA INVARYANT TABANI — bugunku BORC buraya civilendi; kapi yalnizca "
                 "sayi ARTARSA kirmizi yanar. Dusus de kirmizidir (circir): borc "
                 "kapandiktan sonra sessizce geri gelmesin. Guncelleme: "
                 "python3 tools/marka-invaryant-kapisi.py --taban-yaz"),
        "_olcum": ("12 Agu 2026 · katalog %d urun · `?marka=` hedefi D1 `marka_kanon` "
                   "uyeligidir; canli kolon tazeligi bu kapinin disinda d1-sync --durum ile "
                   "olculur. `?q=` kolu ARTIK CANLIYI MODELLEMEZ — marka sorgusu bu depoda "
                   "uyelik yuklemine baglandi (uc henuz benimsemedi)."
                   % katalog),
        "marka_sayisi": len(veri),
        "filtre_kayip": dict(sorted(fk.items())),
        "filtre_fazla": dict(sorted(ff.items())),
        "arama_kayip": dict(sorted(ak.items())),
        "arama_fazla_toplam_BLOKLAMAZ": sum(af.values()),
    }


def eksen_karsilastir(ad, olculen, taban):
    """Bir ekseni MARKA MARKA tabanla karsilastir. Doner: (artan, azalan) listeleri."""
    artan, azalan = [], []
    for marka in sorted(set(olculen) | set(taban)):
        o, t = olculen.get(marka, 0), taban.get(marka, 0)
        if o > t:
            artan.append((marka, t, o))
        elif o < t:
            azalan.append((marka, t, o))
    return artan, azalan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modul", default=os.path.join(TOOLS, "marka_model_build.py"),
                    help="marka_model_build.py yolu (mutasyon kaniti icin)")
    ap.add_argument("--taban", default=TABAN_VARSAYILAN)
    ap.add_argument("--taban-yaz", action="store_true",
                    help="olculen degerleri TABAN dosyasina yaz (circir guncellemesi)")
    a = ap.parse_args()

    try:
        import arama                                              # noqa: PLC0415
        mmb = modul_yukle(a.modul)
        with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
    except SystemExit:
        raise
    except Exception as e:                                        # noqa: BLE001
        olculemedi("kaynaklar okunamadi (%s: %s)" % (type(e).__name__, e))

    try:
        (veri, kumeler, serbeste_dusen,
         uyelik, baslik_uyum, kanon) = olc(mmb, arama, urunler, index_html)
    except SystemExit as e:
        olculemedi("olcum kosulamadi (SystemExit: %s)" % (e.code,))
    except Exception as e:                                        # noqa: BLE001
        olculemedi("olcum kosulamadi (%s: %s)" % (type(e).__name__, e))
    if not veri:
        olculemedi("marka evreni BOS — katlama/kuratorluk tek kaynagi okunamamis olabilir")

    olculen = taban_kur(veri, kumeler, len(urunler))

    if a.taban_yaz:
        with open(a.taban, "w", encoding="utf-8") as f:
            json.dump(olculen, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        print("TABAN YAZILDI: %s" % a.taban)
        return 0

    try:
        with open(a.taban, encoding="utf-8") as f:
            taban = json.load(f)
    except Exception as e:                                        # noqa: BLE001
        olculemedi("taban dosyasi okunamadi (%s) — 'taban yok' YESIL DEGILDIR: %s"
                   % (a.taban, e))

    # ── BASLIK SAYILARI (mimar formatı) ──────────────────────────────────────────
    fk, ff = olculen["filtre_kayip"], olculen["filtre_fazla"]
    ak = olculen["arama_kayip"]
    af_top = olculen["arama_fazla_toplam_BLOKLAMAZ"]
    filtre_marka = len(set(fk) | set(ff))
    filtre_kalem = sum(fk.values()) + sum(ff.values())
    arama_marka = len([m for m, (s, _f, r) in kumeler.items() if s ^ r])
    arama_kalem = sum(ak.values()) + af_top
    print("MARKA=%d FILTRE_FARK=%d/%d ARAMA_FARK=%d/%d"
          % (len(veri), filtre_marka, filtre_kalem, arama_marka, arama_kalem))
    print("  ayrinti: FILTRE_KAYIP=%d/%d · FILTRE_FAZLA=%d/%d · ARAMA_KAYIP=%d/%d · "
          "ARAMA_FAZLA(bloklamaz)=%d"
          % (len(fk), sum(fk.values()), len(ff), sum(ff.values()),
             len(ak), sum(ak.values()), af_top))
    print("  katalog: %d urun · kanonik marka: %d" % (len(urunler), len(veri)))
    # GECIS BORCU marka marka (bloklamaz, ama gorunmez kalmasin: veri tarafi kapandikca erir)
    borc = sorted(((len(r - s), m) for m, (s, _f, r) in kumeler.items() if r - s), reverse=True)
    if borc:
        print("  gecis borcu (ARAMA_FAZLA) ilk 8: %s"
              % ", ".join("%s+%d" % (m, n) for n, m in borc[:8]))
    print()

    # ── S) TEK KAYNAK: sayfa kumesi = deponun kanonik sayma fonksiyonu ───────────
    sapan_s = [m for m, (sayfa, _f, _r) in kumeler.items()
               if len(sayfa) != mmb.marka_urun_sayisi(veri[m])]
    kontrol("S: SAYFA kumesi buyuklugu = marka_urun_sayisi (ikinci toplama formulu YOK; "
            "sapan: %d %s)" % (len(sapan_s), sapan_s[:4]), not sapan_s)

    # ── C) POZITIF CAPA — kapinin totolojiye dusmedigi ────────────────────────────
    kimlik_sayaci = {}
    for p in urunler:
        pid = p.get("id")
        if pid:
            kimlik_sayaci[pid] = kimlik_sayaci.get(pid, 0) + 1
    for pid, marka, tur in CAPALAR:
        if kimlik_sayaci.get(pid, 0) != 1:
            kontrol("CAPA %s (%s): katalogda TAM BIR KEZ gecmeli (bulunan: %d)"
                    % (pid, tur, kimlik_sayaci.get(pid, 0)), False)
            continue
        uc = kumeler.get(marka)
        if uc is None:
            kontrol("CAPA %s: '%s' markasi evrende YOK" % (pid, marka), False)
            continue
        sayfa, _filtre, srch = uc
        kontrol("CAPA %s -> /marka/%s/ SAYFASINDA (%s)" % (pid, marka, tur), pid in sayfa)
        kontrol("CAPA %s -> '%s' ARAMASINDA" % (pid, marka), pid in srch)

    # ── Q) MARKA SORGUSU KABLOLU MU ──────────────────────────────────────────────
    # Her kanonik marka adi MARKA SORGUSU olarak taninmali; taninmayan HER marka sessizce
    # eski serbest metin koluna duser (ve o markada gurultu geri gelir).
    kontrol("Q: her kanonik marka adi MARKA SORGUSU olarak taniniyor (serbeste dusen: %d %s)"
            % (len(serbeste_dusen), serbeste_dusen[:4]), not serbeste_dusen)

    # ── A) AKSAN FIKSTURU — sayfa/cip/arama AYNI kanonik uyelikte ───────────────
    # Katalogdaki gercek Citroen kayitlarina civilenmez: veri sahibi alanlari duzelttiginde
    # nobetci kaybolmasin. Uc kume ayri yuklemlerle kurulur, ortak olan yalniz kanondur.
    fx_id = "fx-citroen-aksan"
    evren_fx = mmb.MarkaEvreni(index_html)
    fx_uyelik = mmb.marka_uyelikleri(["Citroën"], evren_fx, ())
    fx_sayfa = {fx_id} if "Citroen" in fx_uyelik else set()
    fx_cip = {fx_id} if "Citroen" in fx_uyelik else set()
    fx_arama = ({fx_id} if arama.marka_sorgusu_esler("Citroen", fx_uyelik, []) else set())
    kontrol("AKSAN FIKSTURU Citroën -> Citroen: SAYFA/CIP/ARAMA AYNI kume %s"
            % sorted(fx_sayfa), fx_sayfa == fx_cip == fx_arama == {fx_id})

    # ── F) SEMANTIK FIKSTUR — jetonlama kurali (katalogdan BAGIMSIZ, bayatlamaz) ─────
    for baslik, icermeli, icermemeli, kanit in BASLIK_FIKSTURLERI:
        try:
            bulunan = arama.baslik_marka_uyumlari(baslik, kanon)
        except Exception as e:                                    # noqa: BLE001
            olculemedi("FIKSTUR olculemedi (%s: %s)" % (type(e).__name__, e))
        eksik = [m for m in icermeli if m not in bulunan]
        sizan = [m for m in icermemeli if m in bulunan]
        kontrol("FIKSTUR %s | %s -> %s (eksik: %s · sizan: %s)"
                % (kanit, baslik[:46], bulunan, eksik or "-", sizan or "-"),
                not eksik and not sizan)

    # ── U) UYUM CAPASI — DINAMIK SECIM (havuz: baslikta TAM KELIME, uyelik YOK) ──────
    # Havuz VERI ILISKISINDEN kurulur (ARAMA kumesinden DEGIL — bkz. blok basi).
    kova = {}
    for pid in sorted(baslik_uyum):
        uy = uyelik.get(pid) or ()
        for marka in baslik_uyum[pid]:
            if marka not in uy and marka in kumeler:
                kova.setdefault(marka, []).append(pid)
    for marka in kova:
        kova[marka].sort()
    havuz_kalem = sum(len(v) for v in kova.values())

    # FAIL-CLOSED: havuz tukendiyse hukum "OLCULEMEDI"dir, sessiz YESIL DEGIL.
    # Bu, kapinin MESRU son durumu da olabilir (veri tarafi tamamen kapaninca havuz 0'a
    # iner) — o zaman bile karar INSANIN: ekseni emekli etmek ya da fiksturlerle surdurmek.
    if havuz_kalem < UYUM_CAPA_ASGARI:
        olculemedi("UYUM CAPA HAVUZU TUKENDI (kalem: %d < asgari %d). Havuz 'baslikta TAM "
                   "KELIME marka anip uyeligi OLMAYAN urunler'dir; bosalmasi ya gecis "
                   "kuralinin BASLIK kolunun KOPTUGUNU ya da veri tarafinin TAMAMEN "
                   "kapandigini gosterir. Ikisi de sessizce gecilemez."
                   % (havuz_kalem, UYUM_CAPA_ASGARI))

    # DETERMINISTIK SECIM: markalar kanonik siraya gore, her turda her markadan BIRER capa
    # (marka cesitliligi maksimum, sira girdiye BAGLI degil -> koşumlar arasi oynamaz).
    secim = []
    for tur in range(max((len(v) for v in kova.values()), default=0)):
        for marka in sorted(kova):
            if len(secim) >= UYUM_CAPA_ADEDI:
                break
            if tur < len(kova[marka]):
                secim.append((marka, kova[marka][tur]))
        if len(secim) >= UYUM_CAPA_ADEDI:
            break

    print("  UYUM CAPA HAVUZU: %d kalem / %d marka -> secilen %d (deterministik: kanonik "
          "marka sirasi, marka basina ilk id)" % (havuz_kalem, len(kova), len(secim)))
    kontrol("U0: en az %d UYUM CAPASI OLCULDU (iddia sessizce kaybolamaz; secilen: %d)"
            % (UYUM_CAPA_ASGARI, len(secim)), len(secim) >= UYUM_CAPA_ASGARI)
    for marka, pid in secim:
        sayfa, _filtre, srch = kumeler[marka]
        uy, bs = uyelik.get(pid) or [], baslik_uyum.get(pid) or []
        # 1) GECIS KURALI bu urunu GERCEKTEN eslestiriyor mu (uretim yuklemi kosulur)
        kontrol("UYUM CAPASI %s x '%s' -> gecis kurali ESLESTIRIYOR (uyelik YOK, baslik VAR)"
                % (pid, marka), arama.marka_sorgusu_esler(marka, uy, bs))
        # 2) ARAMA kumesinde GORUNUYOR mu (kapinin kurdugu kume ile uretim yuklemi ayni mi)
        kontrol("UYUM CAPASI %s x '%s' -> ARAMA kumesinde" % (pid, marka), pid in srch)
        # 3) SAYFADA (K140 EVREN KAYNAGI DEGISIMI, 17 Agu 2026: evren YALNIZ
        # TANINMIS_MARKALAR'dan turer, model jetonlari evren DISI). FAZ 1B (15
        # Agu 2026, K133B) sayfayi uyelik ∪ baslik_uyum bilesiminden kurar; capanin
        # uyeligi YOK ama baslik_uyum'u VAR => FAZ 1B ikincil'e ekler, sayfada
        # OLMALI. Eski "pid not in sayfa" assertion'i FAZ 1B'nin oncesindeki
        # "sayfa = uyelik" varsayimina yazilmisti; yeni bileske sayfa kuralini
        # dogrular. Capa havuzu yine baslik_uyum \ uyelik (totoloji degil: FAZ 1B
        # kirilirsa — yani baslik_uyum ikincil'e eklenmezse — capanin sayfada
        # OLMAMASINI beklemek gerekirdi, kapi KIRMIZI yakardı).
        kontrol("UYUM CAPASI %s x '%s' -> /marka/ SAYFASINDA (FAZ 1B: uyelik+baslik)"
                % (pid, marka), pid in sayfa)

    # ── G) GURULTU CAPASI — serbest metnin yanlis bagladigi urun ARAMADA OLMAMALI ──
    for pid, marka, sinif in GURULTU_CAPALARI:
        if kimlik_sayaci.get(pid, 0) != 1:
            kontrol("GURULTU CAPASI %s (%s): katalogda TAM BIR KEZ gecmeli (bulunan: %d)"
                    % (pid, sinif, kimlik_sayaci.get(pid, 0)), False)
            continue
        uc = kumeler.get(marka)
        if uc is None:
            kontrol("GURULTU CAPASI %s: '%s' markasi evrende YOK" % (pid, marka), False)
            continue
        _sayfa, _filtre, srch = uc
        kontrol("GURULTU CAPASI %s -> '%s' ARAMASINDA DEGIL (%s)" % (pid, marka, sinif),
                pid not in srch)

    # ── T) TABAN KARSILASTIRMASI (bloklayici uc eksen) ───────────────────────────
    # KALICI_KIRMIZI kayitlari taban mekanizmasinin DISINDA — onlar K asamasinda olculur.
    # Burada "artan" listesi yalniz taban mekanizmasiyla susturulan markalardan olusur.
    print()
    kopuk = False
    for ad, olc_e, tab_e in (("FILTRE_KAYIP", fk, taban.get("filtre_kayip", {})),
                             ("FILTRE_FAZLA", ff, taban.get("filtre_fazla", {})),
                             ("ARAMA_KAYIP", ak, taban.get("arama_kayip", {}))):
        kalici = KALICI_KIRMIZI.get(ad, ())
        olc_e_filt = {m: n for m, n in olc_e.items() if m not in kalici}
        tab_e_filt = {m: n for m, n in tab_e.items() if m not in kalici}
        artan, azalan = eksen_karsilastir(ad, olc_e_filt, tab_e_filt)
        kontrol("%s: hicbir markada TABANIN USTUNE cikmadi (artan: %d %s)"
                % (ad, len(artan), artan[:4]), not artan)
        if azalan:
            kopuk = True
            print("       ↓ %s tabanin ALTINDA (%d marka): %s"
                  % (ad, len(azalan), azalan[:6]))
        kontrol("%s: taban GUNCEL (circir — dusus de kirmizidir; azalan: %d)"
                % (ad, len(azalan)), not azalan)

    # ── K) KALICI KIRMIZI — yapisal kayip; taban mekanizmasi DISI ─────────────────
    # Spec K140: bu kayitlar HER KOSUMDA KIRMIZI kalmali (susturmak basarisizlik).
    # Kural: KALICI_KIRMIZI'daki marka eksende >0 gorunmeli. 0'a dusmesi = onarim yapildi
    # ya da veri sessizce kayboldu — ikisi de kapiyi durdurur.
    #
    # ONARIM B (M16 KORLESME): liste bosaltilinca kapinin susturmasi gizlenmemeli. Kural
    # kendini KORUMALI: KALICI_KIRMIZI'daki her ogE eksende ACIK olmali (susturmak =
    # basarisizlik) + eksendeki HER kayip KALICI_KIRMIZI'da BEKLENIYOR olmali. Boylece M16
    # (`KALICI_KIRMIZI'dan Rover dusur`) beklenmeyen_kayip olarak FAIL uretir; liste
    # bosaldiginda kapinin YESIL gecmesi imkansiz olur.
    kalici_eksiler = []
    kalici_hala_acik = []
    for ad, eksen in (("ARAMA_KAYIP", ak),):
        for m in KALICI_KIRMIZI.get(ad, ()):
            n = eksen.get(m, 0)
            if n <= 0:
                kalici_eksiler.append((ad, m, n))
            else:
                kalici_hala_acik.append((ad, m, n))
    beklenen_acik = KALICI_KIRMIZI.get("ARAMA_KAYIP", ())
    beklenmeyen_kayip = sorted((m, n) for m, n in ak.items()
                               if n > 0 and m not in beklenen_acik)
    # KAPI KIRMIZI kalmali — acik olan KALICI KIRMIZI kayitlari FAIL uretir (susturma yok).
    kontrol("K: KALICI KIRMIZI (%d kayit) eksende hala ACIK (susturma yok: %s)"
            % (len(kalici_hala_acik), kalici_hala_acik),
            not kalici_hala_acik)
    kontrol("K: KALICI KIRMIZI sayisi 0'a dusmedi (kapali: %s; 0 = onarim ya da sessiz "
            "kayip — ikisi de kirmizi)" % kalici_eksiler, not kalici_eksiler)
    kontrol("K: eksendeki HER kayip KALICI_KIRMIZI'da BEKLENIYOR olmali (M16 korlesme — "
            "beklenmeyen: %s)" % beklenmeyen_kayip,
            not beklenmeyen_kayip)

    if taban.get("marka_sayisi") != len(veri):
        BILGI.append("marka evreni degisti: taban %s -> olculen %d (taban --taban-yaz ile "
                     "tazelenmeli)" % (taban.get("marka_sayisi"), len(veri)))
    BILGI.append("ARAMA_FAZLA taban %s -> olculen %d (BLOKLAMAZ — gurultu kesimi ayri faz)"
                 % (taban.get("arama_fazla_toplam_BLOKLAMAZ"), af_top))

    for b in BILGI:
        print("  BILGI " + b)
    ne_olculmedi()
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldi)" % len(FAILS))
        if kopuk:
            print("   Taban bayatsa tek satirlik cozum: "
                  "python3 tools/marka-invaryant-kapisi.py --taban-yaz")
        return 1
    print("\nSONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

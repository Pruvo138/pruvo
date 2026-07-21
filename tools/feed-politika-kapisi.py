#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""feed-politika-kapisi.py — Google Merchant POLITIKA jetonu nobetcisi (IKI KATMANLI).

NEDEN VAR: Merchant Center politika redlerinin girdisi feed'deki <title> VE <description>
metinleridir (aciklama da feed'e giriyor — build.render_merchant_feed). Red alan kalem
yayindan duser = sessiz satis kaybi.

🔴 TASARIM DERSI (2. tur, olculdu — 1. tur kapisi BOYLE OLMAMALIYDI):
Ilk tasarimda jeton listesi TAHMINE dayaniyordu ("kullук", "cakmak", "susturucu" gibi
kelimeler riskli SAYILDI). Tam katalogda olculdu: 86 "ihlal"in 71'i SIRADAN TURKCE OTOMOTIV
PARCA ADIYDI — "Toyota 4Runner Arka Küllük İptal Kapağı", "12V Çakmaklık Soketi Kapağı",
"emniyet kemeri uyarı susturucu" (ses yalitimi), "Kapı Kilidi Susturucu Aparatı". Kapi
deploy.yml'de build/yayin/D1'den ONCE ve continue-on-error YOK -> bu aileden YENI bir urun
eklendiginde TUM YAYIN blokelenirdi. Ustelik bu 71 kalemin Merchant'ta gercekten reddedildigi
HIC OLCULMEMISTI, VARSAYILMISTI.

Bu yuzden kapi IKIYE ayrildi:

  1) BLOKLAYICI katman (cikis 1) — jetonlari YALNIZ olculmus/bildirilmis GERCEK Merchant
     reddinden turer VE bloklamanin bedeli tasinabilir olmalidir. Bugun 3 jeton; tam katalogda
     7 isabet, YANLIS-POZITIF 0 (7'sinin de musteriye gorunen metninde acikca e-sigara/vape
     adi geciyor; tek tek denetlendi). Bilinen borc tools/feed-politika-taban.json'da;
     YENI borc KIRMIZI yakar.

🔴 "dürbün" NEDEN BLOKLAYICI DEGIL (S4 turu, MIMAR KARARI — kanit YETMEZ, BEDEL de olculur):
Jetonun arkasinda gercek bir Merchant reddi VAR (durbun koruyucu kapak seti) ama bu kapi
deploy.yml'de yayindan ONCE kosar ve continue-on-error YOKTUR: "dürbün" gecen MESRU bir
Marin/Kamera urunu (or. "Marin el dürbünü tutucu", "tekne dürbün yuvası") eklendigi an TUM
EKIBIN yayini durur. Olculdu (2026-07-22, 7769 kalem): "dürbün"un tam katalogdaki TEK isabeti
zaten tabanda yazili olan schmidt-bender kaydidir; "durbun" (diakritiksiz) 0 isabet. Yani
jetonu RAPOR katmanina tasimanin BUGUNKU koruma kaybi SIFIR, yanlis-pozitif riski ise gercek
ve olculebilir. Jeton RAPOR'da sayilmaya devam eder (maruziyet gorunur kalir) ve _NEGATIF
nobetcisine mesru bir durbun metni fikstur olarak konuldu -> biri onu tekrar BLOKLAYICI'ya
tasirsa kapi KENDINI kirmizi yakar.

  2) RAPOR katmani (DAIMA cikis 0) — supheli ama KANITSIZ jetonlar. Sayi + ornek basar,
     CI'yi ASLA kirmaz. Maruziyet gorunur kalir, yayin durmaz. Bir jeton buradan
     BLOKLAYICI'ya ancak GERCEK bir red bildirimiyle tasinir.

🔴 RATCHET VERI DUZLEMININ SAHIBINI KILITLEMEZ (ders 2): eski tasarimda tabani buyutmek
hem JSON'u hem koddaki bir sha256 sabitini AYNI commit'te degistirmeyi gerektiriyordu ->
urun duzleminin sahibi (MaCiT) kendi isini acamiyordu. Yeni tasarim: taban dosyasi TEK
YAZARLI ve KOD SABITI GEREKTIRMEDEN guncellenir. Taban BUYUMESI gurultulu bir uyari uretir
(cikis 0) ama KILITLEMEZ; taban KUCULMESI (borc odendi) serbest ve sessizdir.

🔴 BORCUN AGIRLASMASI YINE KIRMIZI (ders 3): tabandaki her kaydin "jeton" kumesi de
dondurulmustur. Tabandaki bir urun kaydinda OLMAYAN YENI bir bloklayici jeton kazanirsa
kapi KIRMIZI yanar (eski surumde "jeton" alani imzaya girmiyordu ve HIC KULLANILMIYORDU ->
tabandaki urune ikinci bir jeton eklense bile kapi YESIL kaliyordu).

KAPSAM: feed'e GERCEKTEN giren kalemler (render_merchant_feed ciktisi ayristirilir;
parametrik/fiyatsiz/gorselsiz urun zaten feed disi -> Merchant onlari gormez, taranmaz).

AG'A CIKMAZ, DOSYAYA YAZMAZ. Cikis: 0 = yesil, 1 = kirmizi.
Calistir:  python3 tools/feed-politika-kapisi.py
Tanilama:  --urunler <kopya.json>  --taban <kopya.json>  --liste  --rapor-tam
"""
import argparse
import html as _html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# build.py MODUL olarak import edilir (komut olarak KOSTURULMAZ: build.py main()'i izlenen
# statik sayfalari YERINDE yeniden yazar -> calisma agacini kirletir).
import build  # noqa: E402

TABAN_YOL = os.path.join(HERE, "feed-politika-taban.json")

# ---------------------------------------------------------------- 1) BLOKLAYICI jetonlar
# 🔴 BU LISTEYE JETON EKLEMENIN IKI SARTI VAR (ikisi de gerekli):
#   (a) KANIT: Merchant Center'dan (ya da ArTisT'in panel raporundan) gelen GERCEK bir red
#       kaydi. "Bu kelime bana riskli geldi" YETMEZ — 1. turda oyle yapildi ve 71 mesru
#       otomotiv parcasi yanlis-pozitif oldu.
#   (b) BEDEL: jetonun MESRU bir urun adinda gecme ihtimali olculmus ve dusuk olmali. Kapi
#       yayindan ONCE + continue-on-error YOK -> tek yanlis-pozitif TUM EKIBIN yayinini
#       durdurur. Kanit var ama bedel yuksekse jeton RAPOR katmanina gider ("dürbün" boyle
#       tasindi, bkz ustteki not).
# Her jetonun yaninda: kanit sinifi + bugunku katalog isabeti + yanlis-pozitif sayisi.
BLOKLAYICI = {
    "elektronik sigara":
        "DOGRUDAN KANIT — Merchant tutun politikasi reddi (bildirilen 3 urun). "
        "Katalog isabeti 5, yanlis-pozitif 0. BEDEL: mesru bir yedek parca adinda "
        "'elektronik sigara' tam ifadesi gecmez (olculdu: 5 isabetin 5'i gercek e-sigara urunu).",
    "e-sigara":
        "AYNI IFADENIN tireli yazimi (kacis yolu kapatma). Katalog isabeti 0.",
    "vape":
        "AYNI URUN AILESI — reddedilen kalemler 'Nord AIO' (bir vape cihazi) standi; "
        "urunun adini 'vape' diye yazmak ayni politikaya girer. Katalog isabeti 2 "
        "(ikisi de gercek vape standi), yanlis-pozitif 0. BEDEL: 'vape' Turkce bir parca "
        "adinda gecmez (yabanci marka/urun adi).",
}

# ---------------------------------------------------------------- 2) RAPOR jetonlari
# 🔴 BUNLAR CI'YI KIRMAZ. Supheli ama Merchant reddi KANITLANMAMIS ifadeler. Cogu bugun
# mesru Turkce otomotiv parca adidir; bloklayici yapmak yayini durdurur (olculdu: 71 kalem).
# Buradaki bir jeton, GERCEK bir red bildirimi gelirse BLOKLAYICI'ya tasinir.
RAPOR = {
    "küllük": "tutun aksesuari cagrisimi — AMA katalogdaki 45 isabetin tamami arac ici "
              "'kullук iptal kapagi / haznesi / ici duzenleyici' (mesru yedek parca)",
    "kulluk": "'kullук'un diakritiksiz yazimi",
    "çakmak": "tutun aksesuari cagrisimi — AMA katalogdaki 26 isabetin tamami 12V "
              "'cakmaklik soketi/paneli/kapagi' (arac elektrik prizi, mesru parca)",
    "cakmak": "'cakmak'in diakritiksiz yazimi",
    "sigara": "tek basina 'sigara' — 'elektronik sigara' disindaki isabetler mesru "
              "(or. 'bardaklik ici sigara ve cihaz tutucu')",
    "dürbün": "KANITLI red var (Merchant silah politikasi, durbun koruyucu kapak seti) AMA "
              "BLOKLAMA BEDELI YUKSEK: mesru Marin/Kamera urunu ('el durbunu tutucu', "
              "'tekne durbun yuvasi') tum ekibin yayinini durdurur. Olculdu 2026-07-22: tam "
              "katalogda TEK isabet ve o da zaten tabanda -> bloklayici olmasinin BUGUNKU "
              "koruma katkisi 0. Yeni bir durbun urunu gelirse burada SAYILIR, gorunur kalir.",
    "durbun": "'dürbün'un diakritiksiz yazimi (katalog isabeti 0)",
    "tütün": "tutun urunu (diakritikli tek form; diakritiksiz 'tutun' TARANMAZ -> "
             "'tutunma/tutunuz' fiiliyle carpisiyor, olculdu: 31 yanlis pozitif)",
    "puro": "tutun urunu cagrisimi",
    "nargile": "tutun urunu cagrisimi",
    "shisha": "tutun urunu cagrisimi",
    "susturucu": "silah susturucusu cagrisimi — AMA katalogdaki 10 isabetin tamami "
                 "'emniyet kemeri ikaz susturucu' / 'kapi kilidi susturucu' / 'turbo "
                 "susturucu' (ses yalitimi, mesru parca)",
    "silah": "acik silah ifadesi",
    "tüfek": "acik silah ifadesi",
    "şarjör": "silah parcasi",
    "fişek": "muhimmat",
    "airsoft": "silah replikasi",
    "nişangah": "silah nisangahi",
    "esrar": "uyusturucu cagrisimi",
    "bong": "uyusturucu aksesuari",
    "uyuşturucu": "acik uyusturucu ifadesi",
}

TR_KUCUK = {ord(u"I"): u"ı", ord(u"İ"): u"i"}
HARF = u"a-zçğıöşü0-9"


def _derle(jetonlar):
    # Jeton KELIME BASINDA baslamali (onunde harf/rakam olmamali) ama Turkce ekleri tolere
    # etmeli ('durbunleriniz', 'sigarasi'). '-' sinir sayilir: 'e-sigara' yakalanir.
    return {j: re.compile(u"(?<![%s])%s[%s]*" % (HARF, re.escape(j), HARF), re.U)
            for j in jetonlar}


_D_BLOK = _derle(BLOKLAYICI)
_D_RAPOR = _derle(RAPOR)


def kucult(s):
    """Turkce-duyarli kucultme (I->ı, İ->i), sonra standart lower()."""
    return (s or "").translate(TR_KUCUK).lower()


def varyantlar(s):
    """Aranacak KUCUK-HARF varyantlari (benzersiz, sirali).

    🔴 IKI CEVRIM DE GEREKLI (S4 turu, olculdu): jetonlar ASCII 'i' ile yazilir (sigara,
    elektronik sigara). Turkce cevrim I->ı yaptigi icin BUYUK HARFLE ve NOKTASIZ I ile yazilmis
    bir baslik ("ELEKTRONIK SIGARA TUTUCU" — ALL-CAPS baslikta cok yaygin) TR cevrimden
    'elektronık sıgara' cikar ve jetona ESLESMEZ: sessiz bir KACIS YOLU. Standart lower()
    ise 'İ'yi 'i̇' (i + birlesen nokta) yapar, o da TR cevrimle yakalanir. Ikisini birden
    taramak her iki yazimi da kapatir.
    BEDEL OLCULDU (2026-07-22, 7769 feed kalemi): ASCII varyantinin EKLEDIGI bloklayici
    isabet = 0 (yani yeni yanlis-pozitif YOK), kapattigi kacis yolu gercek."""
    tr = kucult(s)
    duz = (s or "").lower()
    return [tr] if tr == duz else [tr, duz]


def bloklayici_bul(metin):
    """Metindeki BLOKLAYICI jetonlari (kanonik ad) sirali/benzersiz dondurur."""
    vs = varyantlar(metin)
    return [j for j in BLOKLAYICI if any(_D_BLOK[j].search(v) for v in vs)]


def rapor_bul(metin):
    """Metindeki RAPOR (bloklamayan) jetonlarini dondurur."""
    vs = varyantlar(metin)
    return [j for j in RAPOR if any(_D_RAPOR[j].search(v) for v in vs)]


# ---------------------------------------------------------------- feed tarama
_ITEM = re.compile(r"<item>(.*?)</item>", re.S)
_ALAN = {ad: re.compile(r"<%s>(.*?)</%s>" % (ad, ad), re.S)
         for ad in ("g:id", "title", "description")}


class KismiTaramaHatasi(Exception):
    """Feed'in TAMAMI taranamadi -> kapi hukum veremez (fail-closed)."""


def feed_kalemleri(products):
    """render_merchant_feed ciktisini ayristirip (gid, title, description) dondurur.

    🔴 Feed METNI taranir, urunler.json alanlari DEGIL: build.marka_temiz() feed metnini
    degistiriyor ve kirpma (title 150 / description 5000) uyguluyor; Merchant'in GORDUGU
    metin budur. Kaynak alani tarasaydik kapi Merchant'tan sapardi.

    🔴 KISMI TARAMA = KIRMIZI (S5 turu, olculdu — bu SESSIZ YESILDI): render_merchant_feed
    kac kalem urettigini ZATEN donduruyordu (_n) ama deger ATILIYORDU. <item> ayristirmasi
    kirpilirsa/bozulursa (kirpma, regex sapmasi, XML bicimi degisimi) kapi kalan kalemleri
    TERTEMIZ bulur ve cikis 0 verir; ne self-check ne mutasyon harness'i bunu gorurdu.
    Olculdu: feed'in ilk N kalemine kirpan bir mutasyonla 3000. siradaki GERCEK bir vape
    urunu SESSIZCE geciyordu. Kapi neyi TARADIGINI bilmiyorsa hukum VEREMEZ."""
    xml, _n = build.render_merchant_feed(products)
    kalemler = []
    for govde in _ITEM.findall(xml):
        al = {}
        for ad, pat in _ALAN.items():
            m = pat.search(govde)
            al[ad] = _html.unescape(m.group(1)) if m else ""
        kalemler.append((al["g:id"], al["title"], al["description"]))
    if len(kalemler) != _n:
        raise KismiTaramaHatasi(
            "KISMI TARAMA: feed %d kalem uretti, ayristirmadan %d kalem cikti. Taranmayan "
            "%d kalemde politika ihlali OLABILIR -> kapi hukum veremez (fail-closed). "
            "Sebep: <item> ayristirmasi kirpilmis / regex feed bicimiyle uyusmuyor."
            % (_n, len(kalemler), abs(_n - len(kalemler))))
    return kalemler


def _tara(products, bulucu):
    """(kayitlar, feed_kalem_sayisi). kayit: {'gid','id','baslik','baslik_jeton',
    'aciklama_jeton','jeton'}  (id = GERCEK urun id'si; feed g:id kisaltilmis olabilir)."""
    gid_pid = {}
    for p in products:
        gid_pid[build.feed_id(p["id"])] = p["id"]
    out = []
    kalemler = feed_kalemleri(products)
    for gid, title, desc in kalemler:
        jb = bulucu(title)
        ja = bulucu(desc)
        if jb or ja:
            out.append({"gid": gid, "id": gid_pid.get(gid, gid), "baslik": title,
                        "baslik_jeton": jb, "aciklama_jeton": ja,
                        "jeton": sorted(set(jb) | set(ja))})
    return out, len(kalemler)


def ihlalleri_topla(products):
    """BLOKLAYICI katman taramasi. Feed TEK KEZ render edilir (~0,7 sn)."""
    return _tara(products, bloklayici_bul)


def rapor_topla(products):
    """RAPOR katmani taramasi (cikis kodunu ETKILEMEZ)."""
    return _tara(products, rapor_bul)


# ---------------------------------------------------------------- olu-nobetci onlemi
# 🔴 Ratchet kapisinin TEK dogal yonu yesildir — jeton listesi bosalsa, regex bozulsa ya da
# <description> taramasi dusse kapi SESSIZCE yesil kalirdi. Ayrica ters yonde de nobet
# gerekir: BLOKLAYICI listesi yine tahminle GENISLETILIRSE (1. turun hatasi) mesru otomotiv
# parcalari bloke edilir ve TUM EKIBIN yayini durur. Bu yuzden hem POZITIF hem NEGATIF
# sentetik nobetciler her kosumda kosar.
_POZITIF = [
    ("Toyota Nord AIO Elektronik Sigara Standı", "elektronik sigara"),
    ("Renault Laguna E-Sigara Tutucu", "e-sigara"),
    ("Toyota Nord AIO vape standı", "vape"),
    # 🔴 BUYUK HARF + NOKTALI İ: kucult()'un TR_KUCUK cevrimi (İ->i) olmazsa standart lower()
    # 'İ'yi 'i̇' (i + U+0307 birlesen nokta) yapar ve 'elektronik sigara' ESLESMEZ.
    # (Eski yorum "buyuk harf + Turkce I" DIYORDU ama nobetci metninde ne I ne İ vardi ->
    #  TR_KUCUK cevrimi HIC sinanmiyordu; S4 turunda duzeltildi.)
    ("RENAULT LAGUNA ELEKTRONİK SİGARA TUTUCU", "elektronik sigara"),
    # 🔴 BUYUK HARF + NOKTASIZ ASCII I: TR cevrim I->ı yaptigi icin bu metin YALNIZ duz
    # lower() varyantiyla yakalanir (bkz varyantlar()). Varyantlardan biri dusurulurse
    # bu iki satirdan biri KIRMIZI yanar.
    ("CITROEN C4 ELEKTRONIK SIGARA DUZENLEYICI", "elektronik sigara"),
    ("TOYOTA NORD AIO VAPE STANDI", "vape"),
]

# RAPOR katmaninin POZITIF nobetcileri (bu katman CI'yi kirmaz ama SESSIZCE olebilir;
# olurse maruziyet sayaci sifir gosterir ve "temizlendi" sanilir).
_RAPOR_POZITIF = [
    ("Toyota 4Runner Arka Küllük İptal Kapağı", "küllük"),
    # 'dürbün' BLOKLAYICI'dan buraya tasindi (bkz ustteki karar notu) — RAPOR'da da
    # yakalanmazsa jeton tumden kaybolmus olur, o yuzden nobetcisi burada.
    ("Schmidt & Bender 1.5-6x42 Dürbün Koruyucu Kapak Seti", "dürbün"),
    ("Nikon durbun ayak plakasi", "durbun"),
]

# 🔴 YANLIS-POZITIF NOBETCISI — hepsi KATALOGDAKI GERCEK, MESRU otomotiv parca metinleridir.
# Biri bile bloklanirsa kapi KENDINI KIRMIZI yakar; yani "riskli gorunen kelimeyi listeye
# ekleyelim" refleksi CI'da degil, burada patlar. (1. turda bu urunlerin 71 tanesi
# "ihlal" sayilmisti.)
_NEGATIF = [
    "Dacia Duster çakmaklık soketi kapağı",
    "Volkswagen Çakmaklık Soketi Kapağı",
    "BMW E46 Küllük İçi 12V Çakmaklık Anahtar Paneli",
    "Toyota 4Runner Arka Küllük İptal Kapağı",
    "Suzuki Ignis emniyet kemeri uyarı susturucu",
    "Audi ve Volkswagen Uyumlu Kapı Kilidi Susturucu Aparatı",
    "Mercedes OM642 Turbo Susturucu Parçası",
    "Toyota 4Runner arka tutamak — tutunma kolu",
    "Volkswagen dizel yakıt tabancası adaptörü",
    "Skoda Octavia Bardaklık İçi Sigara ve Cihaz Tutucu",
    # 🔴 S4 KILIDI — "dürbün" BLOKLAYICI'ya GERI TASINIRSA bu iki satir kapiyi kendi
    # kosumunda kirmizi yakar. Ikisi de MESRU urun metnidir (Marin/Kamera katalogumuzun
    # dogal genislemesi): dürbün'un bloklayici olmasi bunlarin eklendigi gun TUM EKIBIN
    # yayinini durdururdu. Kanit vardi ama BEDEL tasinamazdi (bkz dosya basi karar notu).
    "Marin el dürbünü tutucu",
    "Tekne konsolu durbun yuvasi",
]

# 🔴 IKI TARAMA YOLU DA AYRI AYRI NOBETLI (S4): kapinin girdisi feed'in <title> VE
# <description> alanlaridir. Tek bir "kirli urun" fiksturu IKISINI BIRDEN kirli yaptigi
# icin bir yolun bulucusu oldurulse bile digeri kalemi yakalar ve nobetci YESIL kalirdi
# (olculdu: baslik bulucusu oldurulunce GERCEK bir vape urunu SESSIZCE geciyordu).
# Bu yuzden fiksturler ASIMETRIK: her birinde YALNIZ bir yol kirli.
# (etiket, baslik, aciklama, KIRLI_olmasi_gereken_alan, TEMIZ_olmasi_gereken_alan)
_ASIMETRIK = [
    ("ACIKLAMA", "Nobetci test parcasi",
     "Bu metin vape kelimesi tasir; baslik temizdir.", "aciklama_jeton", "baslik_jeton"),
    ("BASLIK", "Nobetci vape standi",
     "Bu aciklama tamamen temizdir, hicbir politika jetonu tasimaz.",
     "baslik_jeton", "aciklama_jeton"),
]

# 🔴 FIKSTURLERIN KENDISI DE NOBETLI (S5 turu — bu UC LISTE tek satirla KORLESTIRILEBILIYORDU):
# yukaridaki nobetciler bir listeyi gezerek calisir. Liste bosaltilirsa ("_NEGATIF = []") ya da
# onu gezen dongu oldurulurse ("for metin in []:") hicbir nobetci kosmaz, _kendini_dogrula()
# bos hata listesi doner ve kapi SESSIZCE YESIL yanar — ustelik o an BLOKLAYICI listesine
# kanitsiz bir jeton eklenmis olsa bile. Bu yuzden her fikstur icin IKI olcum yapilir:
#   (a) TABAN: liste bugunku boyutunun ALTINA dusemez  -> liste bosaltmayi yakalar.
#   (b) SAYAC: nobetci dongusu listedeki HER kalem icin GERCEKTEN kosmus olmali
#              -> donguyu oldurmeyi yakalar (liste dolu kalir, sayac 0'da kalir).
# Fikstur BUYUMESI serbesttir (taban asgaridir); KUCULMESI kirmizidir.
_FIKSTURLER = (
    ("_POZITIF", _POZITIF, 6),
    ("_RAPOR_POZITIF", _RAPOR_POZITIF, 3),
    ("_NEGATIF", _NEGATIF, 12),
    ("_ASIMETRIK", _ASIMETRIK, 2),
)


def kurallari_uygula(ihlal, taban):
    """R1 + R2 kurallarini uygular. ihlal: {id: kayit}, taban: {id: set(jeton)}.
    Doner: hata metinleri listesi.

    🔴 AYRI FONKSIYON OLMASININ SEBEBI: bu iki kural bugunku katalogda HIC ATESLENMIYOR
    (bugun yeni ihlal yok). Yani kurali silmek/etkisizlestirmek CI'da SESSIZ kalirdi —
    kapi yesil yanmaya devam ederdi. _kendini_dogrula() bu fonksiyonu her kosumda SENTETIK
    girdiyle cagirip kurallarin HÂLÂ ates ettigini kanitlar."""
    hata = []
    # R1 — YENI IHLAL: tabanda OLMAYAN bir id bloklayici jeton tasiyorsa KIRMIZI.
    for pid in sorted(set(ihlal) - set(taban)):
        k = ihlal[pid]
        nerede = []
        if k.get("baslik_jeton"):
            nerede.append("baslik:" + "/".join(k["baslik_jeton"]))
        if k.get("aciklama_jeton"):
            nerede.append("aciklama:" + "/".join(k["aciklama_jeton"]))
        hata.append("YENI POLITIKA IHLALI: %s  [%s]  — %s"
                    % (pid, "; ".join(nerede), (k.get("baslik") or "")[:70]))
    # R2 — BORC AGIRLASAMAZ: tabandaki bir id, kaydinda OLMAYAN yeni bir jeton kazandiysa.
    for pid in sorted(set(ihlal) & set(taban)):
        yeni_jeton = sorted(set(ihlal[pid]["jeton"]) - taban[pid])
        if yeni_jeton:
            hata.append(
                "TABANDAKI URUN YENI JETON KAZANDI: %s  [+%s]  (kayitli: %s)  — %s"
                % (pid, "/".join(yeni_jeton), "/".join(sorted(taban[pid])) or "-",
                   (ihlal[pid].get("baslik") or "")[:60]))
    return hata


def _sentetik_kayit(pid, jetonlar):
    return {pid: {"gid": pid, "id": pid, "baslik": "sentetik",
                  "baslik_jeton": list(jetonlar), "aciklama_jeton": [],
                  "jeton": sorted(set(jetonlar))}}


def _kendini_dogrula():
    """Kapinin kendi olcum zincirini sinar. Hata listesi dondurur (bos = saglam)."""
    hata = []
    sayac = {ad: 0 for ad, _l, _t in _FIKSTURLER}   # her nobetci dongusunun GERCEK kosum sayisi
    # R1/R2 kurallari HÂLÂ ates ediyor mu (bugunku katalogda ateslenmedikleri icin
    # silinmeleri/etkisizlestirilmeleri aksi hâlde SESSIZ kalirdi).
    if not kurallari_uygula(_sentetik_kayit("sentetik-yeni", ["vape"]), {}):
        hata.append("R1 KURALI OLDU: tabanda OLMAYAN sentetik ihlal KIRMIZI uretmedi — "
                    "yeni borc artik durdurulmuyor.")
    if not kurallari_uygula(_sentetik_kayit("sentetik-taban", ["vape", "e-sigara"]),
                            {"sentetik-taban": {"vape"}}):
        hata.append("R2 KURALI OLDU: tabandaki sentetik urun YENI jeton kazandigi hâlde "
                    "KIRMIZI uretmedi — borc sessizce agirlasabilir.")
    if kurallari_uygula(_sentetik_kayit("sentetik-taban", ["vape"]),
                        {"sentetik-taban": {"vape"}}):
        hata.append("R1/R2 ASIRI HEVESLI: tabanda YAZILI ve jetonu DEGISMEMIS sentetik urun "
                    "KIRMIZI uretti — bilinen borc yayini durdurur hâle gelmis.")
    # Taban ayristirmasi R2'nin TEK girdisi; bozulursa R2 sessizce olur (kural kodu yerinde
    # gorunur ama her jeton "zaten kayitli" sayilir).
    _sent_taban = {"kok": [{"id": "sx", "jeton": ["vape"]}, {"id": "sy", "jeton": []}]}
    if taban_ayristir(_sent_taban) != {"sx": {"vape"}, "sy": set()}:
        hata.append("TABAN AYRISTIRMASI BOZUK: sentetik taban {sx:[vape], sy:[]} -> %r "
                    "(beklenen {'sx':{'vape'},'sy':set()}) — R2 kurali kor kalir."
                    % (taban_ayristir(_sent_taban),))
    ortak = sorted(set(BLOKLAYICI) & set(RAPOR))
    if ortak:
        hata.append("JETON KATMAN CAKISMASI: %s hem BLOKLAYICI hem RAPOR listesinde — "
                    "bir jeton ya bloklar ya raporlar." % ", ".join(ortak))
    for metin, beklenen in _POZITIF:
        sayac["_POZITIF"] += 1
        bulunan = bloklayici_bul(metin)
        if beklenen not in bulunan:
            hata.append("POZITIF NOBETCI DUSTU: %r icinde %r bulunamadi (bulunan=%s) — "
                        "bloklayici jeton listesi/regex bozulmus, kapi artik hicbir seyi "
                        "yakalamiyor olabilir" % (metin, beklenen, bulunan or "-"))
    for metin in _NEGATIF:
        sayac["_NEGATIF"] += 1
        bulunan = bloklayici_bul(metin)
        if bulunan:
            hata.append(
                "🔴 YANLIS POZITIF: %r MESRU bir otomotiv parca metnidir ama %s jeton(lar)i "
                "BLOKLADI. Bu kapi deploy.yml'de yayindan ONCE ve continue-on-error YOK -> "
                "boyle bir jeton TUM EKIBIN push'unu durdurur. Jetonu BLOKLAYICI'dan cikar, "
                "gerekiyorsa RAPOR katmanina koy." % (metin, bulunan))
    # RAPOR katmani yasiyor mu (o da sessizce olebilir; olurse maruziyet gorunmez olur).
    for metin, beklenen in _RAPOR_POZITIF:
        sayac["_RAPOR_POZITIF"] += 1
        if beklenen not in rapor_bul(metin):
            hata.append("RAPOR KATMANI DUSTU: %r icinde %r rapor jetonu bulunamadi — "
                        "maruziyet sayaci artik hicbir seyi saymiyor olabilir."
                        % (metin, beklenen))
    # ASIMETRIK fiksturler (tanimi + gerekcesi _ASIMETRIK yaninda).
    for etiket, baslik, aciklama, kirli, temiz in _ASIMETRIK:
        sayac["_ASIMETRIK"] += 1
        sentetik = [{"id": "nobetci-sentetik-%s" % etiket.lower(), "kategori": "Tamirat",
                     "marka": [], "baslik": baslik, "aciklama": aciklama, "fiyat": "100 TL",
                     "gorseller": ["https://media.pruvo3d.com/urunler/nobetci-1.jpg"]}]
        bulundu, _ = ihlalleri_topla(sentetik)
        if not (bulundu and bulundu[0][kirli] and not bulundu[0][temiz]):
            hata.append(
                "%s YOLU DUSTU: yalniz <%s> icinde jeton tasiyan sentetik kalem yakalanmadi "
                "(sonuc=%r) — feed'in bu alani artik taranmiyor, o alandan gelen GERCEK bir "
                "politika ihlali SESSIZCE gecer."
                % (etiket, "title" if etiket == "BASLIK" else "description", bulundu))
    # 🔴 EN SON: nobetcilerin KENDISI kosmus mu (bkz _FIKSTURLER notu). Bu iki olcum olmadan
    # yukaridaki uc dongunun UCU DE tek satirla korlestirilebiliyordu ve kapi YESIL yaniyordu.
    for ad, liste, taban in _FIKSTURLER:
        if len(liste) < taban:
            hata.append("FIKSTUR KUCULDU: %s bugun %d kayit, asgari %d olmali — nobetci "
                        "fiksturu bosaltilirsa o nobetci hicbir seyi olcmez ve kapi SESSIZCE "
                        "yesil yanar. (Buyutmek serbest; kucultmek kirmizidir.)"
                        % (ad, len(liste), taban))
        if sayac[ad] != len(liste):
            hata.append("NOBETCI DONGUSU KOSMADI: %s listesinde %d kayit var ama nobetci "
                        "%d kez kostu — donguyu olduren bir degisiklik fiksturu KOR birakti."
                        % (ad, len(liste), sayac[ad]))
    return hata


# ---------------------------------------------------------------- taban
def taban_ayristir(t):
    """Taban SOZLUGUNDEN {id: set(jeton)} cikarir (saf fonksiyon — dosya okumaz).

    🔴 AYRI FONKSIYON: R2 (borc agirlasamaz) kuralinin tek girdisi bu kumelerdir. Ayristirma
    bozulursa (or. jeton alani yok sayilip her kayda TUM bloklayici jetonlar verilirse) R2
    SESSIZCE oler — kural kodu duruyor gibi gorunur ama bir sey yakalayamaz. _kendini_dogrula()
    bunu sentetik bir taban sozluguyle her kosumda sinar."""
    kayit = {}
    for k in t.get("kok", []):
        if isinstance(k, dict):
            kayit[k["id"]] = set(k.get("jeton") or [])
        else:                                    # duz id listesi (eski bicim) -> jetonsuz
            kayit[k] = set()
    return kayit


def taban_yukle(yol=None):
    """Doner (ham, {id: set(jeton)}, kok_baslangic)."""
    with open(yol or TABAN_YOL, encoding="utf-8") as f:
        t = json.load(f)
    kayit = taban_ayristir(t)
    return t, kayit, int(t.get("kok_baslangic", len(kayit)))


def main():
    ap = argparse.ArgumentParser(description="Merchant feed politika jetonu kapisi (2 katmanli)")
    ap.add_argument("--urunler", help="alternatif urunler.json (mutasyon/tanilama; CI kullanmaz)")
    ap.add_argument("--taban", help="alternatif taban dosyasi (mutasyon/tanilama)")
    ap.add_argument("--liste", action="store_true", help="bloklayici ihlalleri tek tek bas")
    ap.add_argument("--rapor-tam", action="store_true", help="rapor katmanindaki her kalemi bas")
    args = ap.parse_args()

    with open(args.urunler or build.JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)

    _t, taban, kok_baslangic = taban_yukle(args.taban)

    try:
        ihlaller, kalem_sayisi = ihlalleri_topla(products)
        hatalar = list(_kendini_dogrula())  # R0 — olu/asiri-hevesli nobetci onlemi
        rapor, _ = rapor_topla(products)
    except KismiTaramaHatasi as e:
        # R0' — FAIL-CLOSED: feed'in tamami taranamadiysa "ihlal yok" DEMEK YASAK.
        print("FEED POLITIKA KAPISI")
        print("  ❌ " + str(e))
        print("-" * 78)
        print("SONUC: KIRMIZI ❌  (1 sorun) — kapi feed'in TAMAMINI goremedi, hukum veremez.")
        return 1
    ihlal = {i["id"]: i for i in ihlaller}
    uyarilar = []

    hatalar += kurallari_uygula(ihlal, taban)     # R1 (yeni borc) + R2 (borc agirlasamaz)

    # W1 — TABAN BUYUDU: engellemez (veri duzleminin sahibi kendi isini acabilsin), GURULTULU uyarir.
    if len(taban) > kok_baslangic:
        eklenen = [k.get("id") for k in _t.get("kok", [])
                   if isinstance(k, dict) and k.get("eklendi")]
        uyarilar.append(
            "⚠️  TABAN BUYUDU: baslangic %d -> bugun %d kayit (+%d). Bu KIRMIZI DEGIL "
            "(veri duzleminin sahibi kendi isini acabilsin) ama borc BUYUYOR. "
            "'eklendi' damgasi tasiyan kayitlar: %s"
            % (kok_baslangic, len(taban), len(taban) - kok_baslangic,
               ", ".join(eklenen) if eklenen else "(damgasiz — kayitlara \"eklendi\" yaz)"))

    # Hijyen (OLUMCUL DEGIL): borcu odenmis ama tabandan silinmemis kayitlar.
    odenmis = sorted(set(taban) - set(ihlal))
    # Hijyen: tabandaki kayitlarin jetonlari artik BLOKLAYICI listesinde mi.
    bilinmeyen = sorted({j for js in taban.values() for j in js} - set(BLOKLAYICI))

    print("FEED POLITIKA KAPISI — 2 katmanli (bloklayici + rapor)")
    print("  Feed kalemi           : %d" % kalem_sayisi)
    print("  Bloklayici jeton      : %d  (%s)" % (len(BLOKLAYICI), ", ".join(BLOKLAYICI)))
    print("  Taban (bilinen borc)  : %d kayit   (baslangic %d)" % (len(taban), kok_baslangic))
    print("  Bugun bloklayici ihlal: %d urun" % len(ihlal))
    if odenmis:
        print("  ℹ️  Artik ihlal etmeyen %d kayit tabandan SILINEBILIR (borc kuculur): %s"
              % (len(odenmis), ", ".join(odenmis[:5]) + (" ..." if len(odenmis) > 5 else "")))
    if bilinmeyen:
        print("  ℹ️  Tabanda artik BLOKLAYICI olmayan jeton(lar) yazili: %s" % ", ".join(bilinmeyen))
    if args.liste:
        print("-" * 78)
        for i in sorted(ihlaller, key=lambda x: x["id"]):
            print("  %s | baslik=%s | aciklama=%s | %s"
                  % (i["id"], ",".join(i["baslik_jeton"]) or "-",
                     ",".join(i["aciklama_jeton"]) or "-", i["baslik"][:60]))

    # ------------------------------------------------------------ RAPOR katmani (cikis 0)
    dagilim = {}
    for r in rapor:
        for j in r["jeton"]:
            dagilim.setdefault(j, []).append(r)
    print("-" * 78)
    print("RAPOR KATMANI — BLOKLAMAZ (kanitsiz suphe; cikis kodunu ETKILEMEZ)")
    print("  Etkilenen kalem: %d / %d" % (len(rapor), kalem_sayisi))
    for j in sorted(dagilim, key=lambda x: -len(dagilim[x])):
        ornek = dagilim[j][0]["baslik"][:52]
        print("    %-12s %4d kalem   or. %s" % (j, len(dagilim[j]), ornek))
    if args.rapor_tam:
        for r in sorted(rapor, key=lambda x: x["id"]):
            print("      %s | %s | %s" % (r["id"], ",".join(r["jeton"]), r["baslik"][:60]))
    print("  (Bir jeton BLOKLAYICI'ya ancak GERCEK bir Merchant reddiyle tasinir.)")

    print("-" * 78)
    for u in uyarilar:
        print("  " + u)
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("-" * 78)
        print("SONUC: KIRMIZI ❌  (%d sorun)  — metni duzelt (urun duzlemi: tools/duzelt.py, "
              "MaCiT) ya da kabul ediliyorsa tools/feed-politika-taban.json'a kaydi ekle."
              % len(hatalar))
        return 1
    print("SONUC: YESIL ✅  — yeni/agirlasan bloklayici politika ihlali yok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

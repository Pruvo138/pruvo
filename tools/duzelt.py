#!/usr/bin/env python3
"""duzelt.py — MEVCUT bir urunun alanini BILEREK degistirmenin TEK yetkili yolu.

urunler-guard.py, HEAD'de var olan urunlerin herhangi bir alani degistiginde onu
otomatik HEAD'e geri dondurur. Mesru bir duzeltme (or. bir urunun fiyatini/
kategorisini bilerek degistirmek) yapmak icin bu araci kullan: degisikligi
.urunler.lock altinda urunler.json'a yazar VE guard'in izin vermesi icin
deger-bagli bir "duzeltme izni" manifesti (.urunler-duzelt-izin.json) uretir.

Guard yalnizca working-tree'deki yeni deger manifeste yazilan deger ile BIREBIR
esitse o alanin degismesine izin verir; beyan disi hicbir alani gecirmez.

Kullanim:
  python3 tools/duzelt.py <id> --alan fiyat --deger "500 TL"
  python3 tools/duzelt.py <id> --alan fiyat --deger "500 TL" --alan kategori --deger Elektronik
  python3 tools/duzelt.py <id> --alan marka --deger '["BMW","Mini"]'   # liste/sozluk icin JSON

Deger cozumleme: '[' veya '{' ile baslayan degerler JSON olarak (liste/sozluk)
ayristirilir; digerleri duz metin kabul edilir (fiyat "500 TL" gibi).
'id' alani degistirilemez.

--alan aciklama ICIN OZEL KORUMA (hem tek-urun hem --toplu kipte):
Otomatik uretilen "Yaklaşık dış ölçüler: A × B × C mm." satiri STL'den TURETILMIS
veridir; reword onu sessizce dusuremez.
  * yeni metinde olcu satiri YOKSA -> eskideki satir yeni metnin SONUNA eklenir.
  * yeni metin KENDI olcu satirini tasiyorsa -> yenisi kazanir, ciftleme YOK.
  * sayisal olcu tasimayan placeholder ("… : yok.") geri yazilmaz.
Ne korunduysa/ne dustuyse "ACIKLAMA KORUMA (id=…)" blogunda ACIKCA basilir
(KORUNDU / DEGISTI / DUSTU / BILGI) — kayip artik sessiz degil. Satis/CTA
bosluk-doldurucu satirlari BILEREK kapsam disidir (uretilebilir prose): korunmaz,
yalnizca raporlanir. Kabul testi: tools/duzelt-toplu-test.py bolum (f).

GORSEL-KOKEN KAPISI (hem tek-urun hem --toplu kipte, YAZIMDAN HEMEN ONCE):
Kategori "Skan Art" (figur/ozgun urun) + gorselli bir urunun `gorseller`i degisiyorsa
YA DA urun bu yazimla Skan Art'a cevriliyorsa, gorsellerin GERCEK STL'den turedigine
dair koken manifesti ARANIR; yoksa/supheliyse HICBIR SEY yazilmaz (exit 4).
Kural + manifest semasi + beyan edilen sinirlar: tools/gorsel_koken.py.
Platform kategorileri (Otomobil/Marin/...) HIC degerlendirilmez.

URUNU TAMAMEN SILMEK icin (or. yanlislikla eklenmis logo/telif riskli urun):
  python3 tools/duzelt.py <id> --sil "kisa gerekce"
Bu, urunu urunler.json'dan kaldirir VE id'yi .urunler-sil-izin.json'a yazar ki
guard onu HEAD'den geri eklemesin. --sil, --alan/--deger ile BIRLIKTE kullanilmaz.

TICARI HAL ALANLARI (`tur` + `gorselsiz`) — GERI ALINABILIR AMA SAVRULAMAZ:
Gorsel muafiyeti beyani (`"gorselsiz": true`, yalniz `tur == "fiziksel"` kaydinda gecerli)
bu araca acildi; yoksa bayrak bir kez konunca mesru yoldan geri alinamiyordu (tek yonlu
kapi = tuzak). Kurallar TICARI HAL KAPISI'nda (bkz. _ticari_hal_ihlalleri, cikis kodu 6):
  * `tur` yalniz kanonik sinif dizesini alir; ozel uretime DONUS `--alan-sil tur` iledir.
  * `gorselsiz` yalniz boolean true alir; beyani kaldirmak `--alan-sil gorselsiz` iledir.
  * `gorselsiz` yalniz HAZIR TICARI MAL sinifindaki ve GERCEKTEN gorselsiz kayitta durur.
  * 🔴 SINIF ATLAMASI (hazir mal <-> ozel uretim) --gerekce ZORUNLU tutar ve
    `.urunler-guard.log`a "ticari-hal: ..." satiri olarak yazilir. Gecis fiyat carpanini
    (secenekler.js) ve cayma hakki rejimini degistirir; gerekcesiz oynatilamaz.
Ornek — muafiyet beyanini ve sinifi birlikte geri al:
  python3 tools/duzelt.py <id> --alan-sil gorselsiz --alan-sil tur \
      --gerekce "yanlis siniflandirilmisti; ozel uretim"

UYUM KAPISI (`uyum` = urunun NEYE UYDUGU; hem tek-urun hem --toplu kipte, cikis kodu 7):
`uyum` alani bu araca acildi (MaCiT'in backfill partileri mesru yoldan yazilabilsin diye).
Alan `marka` ile AYNI gercegi anlatir ve ikisi SESSIZCE ayrisabilir; bu yuzden:
  * `marka` ELLE YAZILMAZ, `uyum`dan TURETILIR — turetimi arama.marka_uyumdan_turet()
    yapar ve duzelt.py onu AYNI islemde (ayni kilit, ayni yazim) kendisi yazar.
  * Ayni cagrida hem `uyum` hem `marka` verilmesi REDDEDILIR (iki kaynak yarisamaz).
  * Yazimdan HEMEN ONCE, YAZIM SONRASI durumda, yalnizca bu cagrinin DOKUNDUGU kayitlar
    icin arama.uyum_sebebi() kosulur; tek bir ihlal cagrinin TAMAMINI reddeder ve
    urunler.json byte-esit kalir (gorsel-koken/altkategori kapilariyla AYNI sozlesme).
  * `--alan-sil uyum` GECERLIDIR ve `marka`ya DOKUNMAZ (eski kayit sekline donus mesrudur).
Kural + sema arama.py'de TEK kaynak olarak yasar; katalog geneli eksen tools/uyum-kapisi.py.
Kabul testi: tools/duzelt-uyum-test.py · curutme: tools/duzelt-uyum-mutasyon.py.

BIR ALANI TAMAMEN KALDIRMAK icin (or. public JSON'da durmamasi gereken alan):
  python3 tools/duzelt.py <id> --alan-sil uyelik
Manifeste {"__alan_sil__": true} sentineli yazilir; guard alanin working-tree'de
YOK olmasini mesru sayar. --alan/--deger ile ayni cagrida birlestirilebilir.

TOPLU (BATCH) KIP — N urun / N alan TEK cagrida, TEK kilit, TEK yazim:
  python3 tools/duzelt.py --toplu islemler.json
islemler.json semasi (ya duz dizi ya da {"islemler": [...]} sarmali):
  [
    {"id": "urun-a", "alan": "fiyat",  "deger": "500 TL"},
    {"id": "urun-a", "alan": "marka",  "deger": ["BMW", "Mini"]},
    {"id": "urun-b", "alan-sil": "uyelik"},
    {"id": "urun-c", "sil": "kisa gerekce"}
  ]
Her islem TEK eylem tasir: ("alan"+"deger") | "alan-sil" | "sil".
CLI'den farkli olarak "deger" HAM JSON degeridir ('[' ile baslama kurali YOK):
liste liste, sozluk sozluk, metin metin olarak yazilir.

ATOMIKLIK: butun islemler ONCE dogrulanir (sema + izinli alan + catisma + id
katalogda var mi). Herhangi biri gecersizse HICBIRI uygulanmaz, urunler.json'a
DOKUNULMAZ, exit != 0 ve reddedilen her islem gerekcesiyle basilir. Hepsi
gecerliyse tek flock altinda tek json.load + tek _atomic_write yapilir; guard
izin manifesti (ve gerekiyorsa silme manifesti) ayni kilit icinde guncellenir —
yani toplu kip de tek-urun kipiyle AYNI guard/koruma yolundan gecer.
"""
import argparse
import datetime
import fcntl
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# GORSEL-KOKEN DOGRULAMASI (bkz tools/gorsel_koken.py): figur/ozgun urunun (kategori
# "Skan Art") sayfa gorselleri gercek STL'den turemis olmali. duzelt.py `gorseller` ve
# `kategori` alanlarini degistirebildigi icin cipasiz gorsel yayinlamanin GERCEK
# yoludur. Import KOSULSUZ: modul kaybolursa betik ACILISTA coker (sessiz fail-open
# yok — bir nobetci "dosyasi yoksa gecer" olamaz).
_gkspec = importlib.util.spec_from_file_location(
    "gorsel_koken", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "gorsel_koken.py"))
gk = importlib.util.module_from_spec(_gkspec)
_gkspec.loader.exec_module(gk)
# ALT KATEGORI TAKSONOMISI: izinli (kategori, altkategori) kumesi + tedarikci IMZA nobeti
# tools/arama.py'de TEK kaynak olarak yasar (ayni fonksiyon urun_hash'i ve D1 kolonunu da
# besler). Import gk ile AYNI sebeple KOSULSUZ: modul kaybolursa betik ACILISTA coker —
# bir nobetci "dosyasi yoksa gecer" olamaz.
_arspec = importlib.util.spec_from_file_location(
    "arama", os.path.join(os.path.dirname(os.path.abspath(__file__)), "arama.py"))
arama = importlib.util.module_from_spec(_arspec)
_arspec.loader.exec_module(arama)
URUNLER = os.path.join(ROOT, "urunler.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
MANIFEST = os.path.join(ROOT, ".urunler-duzelt-izin.json")
MANIFEST_SIL = os.path.join(ROOT, ".urunler-sil-izin.json")
LOG = os.path.join(ROOT, ".urunler-guard.log")

# `eski_fiyat`: OPSIYONEL ustu cizili indirim gosterimi (tools/build.py
# eski_fiyat_gosterim). Mesru bir urun alanidir -> guard onu "kirlilik" saymasin ve
# kampanya bitince `--alan-sil eski_fiyat` ile temizlenebilsin. PARA YOLU DEGIL:
# tahsil edilen tutar `fiyat`tan turer.
#
# `altkategori`: kategori ICINDEKI daraltma etiketi (opsiyonel). Alan katalogda 100 kayitta
# DOLUYDU ama duzelt.py'nin izinli listesinde OLMADIGI icin mesru yoldan ne duzeltilebiliyor
# ne doldurulabiliyordu. KOR KABUL YOK: deger BOS olabilir (alan opsiyonel), doluysa kaydin
# `kategori` degeriyle TUTARLI olmak ve tedarikci IMZA nobetinden gecmek ZORUNDA —
# dogrulama _altkategori_ihlalleri() (yazimdan HEMEN ONCE, gorsel-koken kapisi deseni).
# `tur` + `gorselsiz`: TICARI HAL alanlari (bkz. _ticari_hal_ihlalleri).
# NEDEN IZINLI LISTEYE GIRDILER (olculdu 1 Agu): 724a69b2 ile gorsel zorunluluguna dar bir
# istisna acildi — `"gorselsiz": true` + `tur == "fiziksel"` olan urun gorselsiz eklenebilir.
# Ama iki alan da bu listede OLMADIGI icin bayrak bir kez konunca MESRU YOLDAN GERI
# ALINAMIYORDU: yanlis beyan edilmis bir kayit ancak elle temizlikle duzeliyordu (ayni
# sinif bu depoda daha once iki kez cikti). Tek-yonlu kapi, kapi degil tuzaktir.
#
# 🔴 SERBEST DEGIL — SINIF ATLAMASI GEREKCE ISTER: hazir mal <-> ozel uretim gecisi PARA
# ve CAYMA HAKKI demektir (secenekler.js `tur`u okuyup malzeme/renk carpanini 1,00'e
# sabitler; fiziksel malda cayma rejimi farklidir). Bu yuzden alanlar serbestce degil
# _ticari_hal_ihlalleri()'nin kurallariyla degisir ve sinif degistiren her yazim
# --gerekce ZORUNLU tutar + `.urunler-guard.log`a izlenebilir sekilde yazilir.
#
# ⚠️ TOPLU BACKFILL YOLU ACILMADI: tools/parti-kontrol.py bu iki alanin BACKFILL'de
# degismesini KIRMIZI saymaya devam ediyor ve o kural GEVSETILMEDI. Acilan sey urun-basi,
# beyanli, manifeste bagli ve loglu TEKIL duzeltmedir — sessiz toplu kayma degil.
# `uyum`: urunun NEYE UYDUGU (marka/model/motor/yil/oem dizisi; sema arama.py'de TEK
# kaynak). NEDEN IZINLI LISTEYE GIRDI (olculdu 2 Agu): alan sozlukleri + katalog ekseni
# (tools/uyum-kapisi.py) main'e indi ve 13.040 temiz kayit yazilmayi bekliyordu, ama
# `uyum` bu listede OLMADIGI icin ilk parti rc=2 aldi ve atomik dogrulama yuzunden
# HICBIR SEY yazilmadi (dogru davranis — ama yol kapali demekti).
# 🔴 SERBEST DEGIL: `uyum` yazan her cagri `marka`yi da BERABERINDE yazar ve o deger
# ELLE VERILEMEZ (bkz. _uyum_marka_turet / _uyum_marka_catismasi / _uyum_ihlalleri).
DEGISTIRILEBILIR = {"kategori", "marka", "baslik", "aciklama", "fiyat", "eski_fiyat",
                    "gorseller", "lisans", "konfigur", "altkategori",
                    "tur", "gorselsiz", "uyum", "tavsiyeFilament"}

UYUM_ALANI = "uyum"
MARKA_ALANI = "marka"
TAVSIYE_FILAMENT_ALANI = "tavsiyeFilament"

# --alan altkategori (ya da --alan kategori) ihlalinde donen cikis kodu. gorsel-koken
# kapisinin 4'unden AYRI: cagiran (insan ya da betik) hangi kapinin reddettigini cikis
# kodundan ayirt edebilsin.
RC_ALTKATEGORI = 5
# TICARI HAL kapisi (tur/gorselsiz) ihlalinde donen cikis kodu — altkategorininkinden AYRI.
RC_TICARI_HAL = 6
# UYUM kapisi (uyum + ondan TURETILEN marka) ihlalinde donen cikis kodu. Dordu de AYRI
# olmak ZORUNDA: cagiran (MaCiT'in parti betigi) hangi kapinin reddettigini yalnizca
# cikis kodundan ayirt edebilir — "rc != 0" hepsini tek kovaya yigardi ve parti
# betikleri yanlis kapiyi onarmaya calisirdi.
RC_UYUM = 7

GORSELSIZ_BAYRAK = "gorselsiz"
TUR_ALANI = "tur"
TICARI_HAL_ALANLARI = {TUR_ALANI, GORSELSIZ_BAYRAK}


def _tur_gecerli_acik_deger(v):
    """`tur` icin ACIK (hazir ticari mal) degeri mi?

    "fiziksel" dizesi BURADA YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]): deger,
    arama.tur_kanonik'ten GECIP KENDINE donuyorsa kanonik sinif dizesidir. Boylece
    "Fiziksel" / " fiziksel" / "fiziksel-degil" gibi taninmayan degerler (tur_kanonik
    onlari "" yapar) kendiliginden REDDEDILIR ve kural parti-kontrol.py / build.py /
    secenekler.py ile ayni tek kaynaktan turer."""
    return isinstance(v, str) and v != "" and arama.tur_kanonik({TUR_ALANI: v}) == v

# --- ACIKLAMA KORUMA: otomatik uretilen OLCU SATIRI ---------------------------
# MaCiT dilim-30 (olculmus kayip): denetim kapisi yanlis-pozitifi yuzunden bir urunun
# aciklamasi `--alan aciklama` ile yeniden yazildi; STL bbox'indan TURETILMIS
# "Yaklaşık dış ölçüler: A × B × C mm." satiri sessizce dustu ve ikinci bir duzelt.py
# cagrisiyla ELLE geri konmak zorunda kalindi. Kayip SESSIZ: urun canliya olcusuz cikar,
# kimse fark etmez, musteri eksik bilgiyle siparis verir.
#
# Neden bu satir OZEL (ve neden yalniz bu otomatik korunur):
#   * Uretilmis VERI'dir — reword'u yazan (insan ya da model) bu sayilari yeniden
#     turetemez; kaynagi STL'dir. Kaybi geri alinamaz bilgi kaybidir.
#   * Katalogta 14794 urunun 12262'si tasiyor (olculdu, 30 Tem) -> reword yolunun
#     ana carpisma yuzeyi.
# KAPSAM DISI (bilincli, asagida _KAPSAM_DISI_KALIPLAR): "Sipariş için …",
#   "- Dayanıklı malzemeyle özel üretilir.", "- Siparişe göre özel tasarım üretimle
#   hazırlanır." gibi satis/CTA bosluk-doldurucu satirlar. Bunlar VERI degil, uretilebilir
#   PROSE; her reword'de otomatik geri yapistirmak mesru duzeltmeyi (or. bayat CTA'yi
#   kaldirmayi) IMKANSIZ kilardi. Otomatik korunmaz ama SESSIZ de dusmez: raporlanir.
#   `lisans` alani aciklamada DEGIL ayri bir alandir; --alan aciklama onu zaten etkilemez.
#
# Desen: denetim-kapisi.py `_OLCU_RE` ile AYNI kural (capa + AYNI SATIRDA <sayi>…mm).
# Bilincli KOPYA, import DEGIL: duzelt.py urun verisinin tek mesru yazma yolu; denetim
# kapisinin adaptor zincirine (printables/makerworld/cults/mmf) bagimli olmasi, bir
# adaptor bozuldugunda duzeltme yolunu da kilitlerdi. Kayma riskini duzelt-toplu-test.py
# (f8) iki deseni ayni fikstur uzerinde karsilastirarak yakalar.
_OLCU_PREFIX = r"Yakla[şs][ıi]k\s+d[ıi][şs]\s+[öo]l[çc][üu]ler"
_OLCU_RE = re.compile(_OLCU_PREFIX + r"[^\n]*?\d[\d\s.,×xX*+-]*mm\b", re.UNICODE)
_OLCU_CAPA_RE = re.compile(_OLCU_PREFIX, re.UNICODE)
_LISTE_ISARETI_RE = re.compile(r"^\s*[-•*]\s*")
_KAPSAM_DISI_KALIPLAR = (
    re.compile(r"^\s*[-•*]?\s*Sipari[şs] i[çc]in\b", re.UNICODE),
    re.compile(r"^\s*[-•*]?\s*Sipari[şs]e g[öo]re\b", re.UNICODE),
    re.compile(r"^\s*[-•*]?\s*Dayan[ıi]kl[ıi] malzemeyle\b", re.UNICODE),
)


def _satirlar(metin):
    return [s for s in metin.split("\n") if s.strip()] if isinstance(metin, str) else []


def _gercek_olcu_satirlari(metin):
    """Capa + AYNI SATIRDA sayi/mm tasiyan (yani GERCEK olcu bildiren) satirlar."""
    return [s for s in _satirlar(metin) if _OLCU_RE.search(s)]


def _capali_olcu_satirlari(metin):
    return [s for s in _satirlar(metin) if _OLCU_CAPA_RE.search(s)]


def _norm(s):
    return " ".join(s.split())


def aciklama_koru(eski, yeni):
    """(korunmus_yeni_metin, rapor) — reword'de otomatik olcu satirini KORU.

    Kurallar:
      * yeni metinde GERCEK olcu satiri VARSA  -> yeni kazanir, ek YOK (ciftleme yok).
      * yoksa ve eskide VARSA                  -> eski satir(lar) yeni metnin SONUNA eklenir
                                                  (liste isareti temizlenir).
      * capasi olup sayisiz placeholder ("… : yok.") -> geri yazilmaz (veri tasimiyor),
                                                  ama rapora DUSTU olarak girer.
    Rapor: (DURUM, SINIF, DETAY) uclusu listesi; cagiran basar. Bir satir sessizce
    dusmez — korunduysa KORUNDU, dusuruldu ise DUSTU/DEGISTI olarak gorunur.
    """
    rapor = []
    if not isinstance(yeni, str) or not isinstance(eski, str) or eski == yeni:
        return yeni, rapor

    sonuc = yeni
    eski_gercek = _gercek_olcu_satirlari(eski)
    yeni_gercek = _gercek_olcu_satirlari(yeni)
    yeni_norm = {_norm(s) for s in yeni_gercek}

    if yeni_gercek:
        for s in eski_gercek:
            if _norm(s) not in yeni_norm:
                rapor.append(("DEGISTI", "olcu satiri",
                              "eski \"%s\" -> yeni metnin KENDI olcu satiri kazandi "
                              "(\"%s\"); ciftleme yapilmadi"
                              % (_norm(s), _norm(yeni_gercek[0]))))
    elif eski_gercek:
        eklenecek = []
        for s in eski_gercek:
            t = _LISTE_ISARETI_RE.sub("", s).strip()
            if t not in eklenecek:
                eklenecek.append(t)
        sonuc = yeni.rstrip("\n") + "\n" + "\n".join(eklenecek)
        for t in eklenecek:
            rapor.append(("KORUNDU", "olcu satiri",
                          "\"%s\" yeni metinde YOKTU -> sona eklendi" % t))

    # capasi olup sayisiz (placeholder) olcu satirlari: geri yazilmaz, ama raporlanir.
    yeni_capali = {_norm(s) for s in _capali_olcu_satirlari(yeni)}
    for s in _capali_olcu_satirlari(eski):
        if _OLCU_RE.search(s):
            continue
        if _norm(s) not in yeni_capali:
            rapor.append(("DUSTU", "olcu placeholder",
                          "\"%s\" sayisal olcu TASIMIYOR -> geri yazilmadi" % _norm(s)))

    # kapsam disi (satis/CTA) satirlari: otomatik korunmaz, ama SESSIZ de dusmez.
    yeni_tum = {_norm(s) for s in _satirlar(yeni)}
    for s in _satirlar(eski):
        if _norm(s) in yeni_tum or _OLCU_CAPA_RE.search(s):
            continue
        if any(k.search(s) for k in _KAPSAM_DISI_KALIPLAR):
            rapor.append(("DUSTU", "satis/CTA satiri",
                          "\"%s\" (kapsam disi: otomatik korunmaz)" % _norm(s)))

    kayip = sum(1 for s in _satirlar(eski)
                if _norm(s) not in yeni_tum and not _OLCU_CAPA_RE.search(s)
                and not any(k.search(s) for k in _KAPSAM_DISI_KALIPLAR))
    if kayip:
        rapor.append(("BILGI", "serbest metin",
                      "eski aciklamanin %d satiri yeni metinde YOK (reword — korunmaz)"
                      % kayip))
    return sonuc, rapor


def _rapor_bas(uid, rapor):
    if not rapor:
        return
    print("ACIKLAMA KORUMA (id=%s):" % uid)
    for durum, sinif, detay in rapor:
        print("  %-8s %-18s %s" % (durum, sinif, detay))
        if durum in ("KORUNDU", "DEGISTI"):
            _log("aciklama-koruma: %s -> %s %s | %s" % (uid, durum, sinif, detay))


def _aciklama_koru_uygula(urun, alanlar):
    """alanlar['aciklama'] varsa korumayi uygula (yerinde); rapor dondur."""
    if "aciklama" not in alanlar:
        return []
    yeni, rapor = aciklama_koru(urun.get("aciklama"), alanlar["aciklama"])
    alanlar["aciklama"] = yeni
    return rapor


def _altkategori_ihlalleri(urunler, idler):
    """YAZIM SONRASI durumda, BU CAGRININ dokundugu kayitlarin (kategori, altkategori)
    tutarliligini olcer. Ihlal listesi dondurur (bos = temiz).

    NEDEN "yazim sonrasi durum": ayni cagri hem `kategori`yi hem `altkategori`yi
    degistirebilir (ya da yalniz kategoriyi degistirip mevcut altkategoriyi GECERSIZ
    birakabilir). Alanlari tek tek, birbirinden bagimsiz dogrulamak o ikinci deligi
    ACIK birakirdi; kayit UYGULANDIKTAN SONRAKI haliyle olculur.

    NEDEN "yalniz dokunulan kayitlar": katalogun TAMAMINI dogrulamak, bu cagriyla
    ILGISIZ eski bir ihlal yuzunden mesru bir duzeltmeyi bloklardi (kapi kapsam ekseni).
    Tum katalog ekseni AYRI ve kalicidir: tools/altkategori-kapisi.py.
    """
    ihlaller = []
    for u in urunler:
        if not isinstance(u, dict) or u.get("id") not in idler:
            continue
        sebep = arama.altkategori_sebebi(u.get("kategori"), u.get("altkategori"))
        if sebep:
            ihlaller.append((u.get("id"), u.get("kategori"), u.get("altkategori"), sebep))
    return ihlaller


def _altkategori_rapor(ihlaller, kaynak):
    satirlar = ["HATA: ALT KATEGORI KAPISI — %s REDDEDILDI (hicbir sey yazilmadi)." % kaynak]
    for uid, kat, alt, sebep in ihlaller:
        satirlar.append("  - id=%s: kategori=%r altkategori=%r -> %s" % (uid, kat, alt, sebep))
    satirlar.append("  Izinli kume (tools/arama.py ALTKATEGORI_IZINLI — katalogta FIILEN "
                    "kullanilan esleslerden dondurulmus):")
    for k in sorted(arama.ALTKATEGORI_IZINLI):
        satirlar.append("    %s -> %s" % (k, ", ".join(arama.ALTKATEGORI_IZINLI[k])))
    satirlar.append("  Alan OPSIYONEL: bos deger ('') ya da --alan-sil altkategori GECERLIDIR.")
    satirlar.append("  Kumeyi genisletmek MIMAR karari: arama.py ALTKATEGORI_IZINLI elle "
                    "guncellenir (yeni deger imza nobetinden de gecmelidir).")
    return "\n".join(satirlar)


def _uyum_marka_catismasi(setler, alan_silmeler):
    """Ayni cagrida hem `uyum` YAZIP hem `marka`ya DOKUNAN id'leri dondurur (bos = temiz).

    NEDEN RED (ikiz tanim yasaginin yazma yolundaki hali): `marka` ile `uyum` AYNI gercegi
    tutar. Ikisi de elle verilebilseydi cagri iki kaynak tasirdi ve hangisinin kazandigi
    kod SIRASINA baglı olurdu — bugun turetim kazanir, yarin biri satiri kaydirir ve elle
    yazilan deger sessizce kataloga yerlesir. Kural tek yonlu: `uyum` yazilir, `marka`
    ONDAN TURETILIR. Cagiran `marka`yi da yazmak istiyorsa niyeti belirsizdir -> RC_UYUM.

    `--alan-sil marka` de catisma sayilir: turetim `marka`yi yazar, silme onu ayni cagrida
    geri alirdi. (O hal zaten _uyum_ihlalleri'nde K5 ile fail-closed yakalanir; burada
    ANLASILIR bir hatayla, dogru kapi kodu ile reddedilir.)
    """
    catisan = []
    for uid, alanlar in setler.items():
        if UYUM_ALANI not in alanlar:
            continue
        if MARKA_ALANI in alanlar or MARKA_ALANI in (alan_silmeler.get(uid) or []):
            catisan.append(uid)
    return sorted(catisan)


def _uyum_catisma_rapor(uidler, kaynak):
    satirlar = ["HATA: UYUM KAPISI — %s REDDEDILDI (hicbir sey yazilmadi)." % kaynak]
    for uid in uidler:
        satirlar.append("  - id=%s: ayni cagrida hem `uyum` hem `marka` verildi "
                        "(ya da `marka` silindi) — IKI KAYNAK YARISAMAZ" % uid)
    satirlar.append("  Kural: `uyum` yazilir, `marka` ondan TURETILIR "
                    "(arama.marka_uyumdan_turet). `marka` islemini cagridan CIKAR.")
    satirlar.append("  `marka`yi bagimsiz duzeltmek istiyorsan o kayda `uyum` YAZMA "
                    "(uyumu bos kayitta `marka` serbesttir).")
    return "\n".join(satirlar)


def _uyum_marka_turet(setler):
    """`uyum` YAZAN her isleme, ondan TURETILEN `marka`yi AYNI islemde ENJEKTE eder.

    Doner: {id: turetilen_marka} — yalnizca turetimin FIILEN kostugu kayitlar.

    🔴 NEDEN `setler`E ENJEKSIYON (ve neden dogrudan kayda yazim DEGIL): turetilen deger
    hem urunler.json'a hem GUARD IZIN MANIFESTINE gitmek zorundadir. Manifest `setler`den
    uretildigi icin, kayda dogrudan yazsaydik guard beyan disi bir `marka` degisimi gorup
    onu HEAD'e geri alirdi — yani turetim sessizce ETKISIZ kalirdi (aciklama korumasinin
    yazimdan ONCE kosmasiyla AYNI gerekce).

    TURETIM TEK KAYNAKTAN: arama.marka_uyumdan_turet. Burada yeniden yazilsaydi iki tanim
    sessizce ayrisir ve `marka` — ki haystack araciligiyla ARAMA METNIDIR — kapi yesilken
    bozulurdu ([[ikiz-tanim-sessiz-ayrisma]]).

    BOS/BICIMSIZ `uyum` TURETIM KOSMAZ: `[]` yazmak "bu kaydin uyumu yok" demektir ve
    eski kayit sekline donustur (--alan-sil uyum ile ayni anlam) -> `marka`ya DOKUNULMAZ.
    Turetseydik `marka` = [] olur ve mevcut arama metni SESSIZCE silinirdi. Liste OLMAYAN
    (bozuk tip) degerde de turetim kosmaz; o degeri _uyum_ihlalleri zaten reddeder.
    """
    turetilenler = {}
    for uid, alanlar in setler.items():
        deger = alanlar.get(UYUM_ALANI)
        if not isinstance(deger, list) or not deger:
            continue
        turetilen = arama.marka_uyumdan_turet({UYUM_ALANI: deger})
        alanlar[MARKA_ALANI] = turetilen
        turetilenler[uid] = turetilen
    return turetilenler


def _uyum_ihlalleri(urunler, idler):
    """YAZIM SONRASI durumda, BU CAGRININ dokundugu kayitlarin `uyum` alanini (ve ondan
    turetilen `marka` ikizini) olcer. Ihlal listesi dondurur (bos = temiz).

    _altkategori_ihlalleri ile AYNI iki gerekce:
      * "yazim sonrasi durum": ayni cagri hem `uyum`u hem `marka`yi (turetim yoluyla)
        degistirir; alanlari tek tek dogrulamak K5 ikiz ekseni ACIK birakirdi.
      * "yalniz dokunulan kayitlar": katalogun TAMAMINI dogrulamak, bu cagriyla ILGISIZ
        eski bir ihlal yuzunden mesru bir duzeltmeyi bloklardi (kapi kapsam ekseni).
        Tum katalog ekseni AYRI ve kalicidir: tools/uyum-kapisi.py.
    """
    ihlaller = []
    for u in urunler:
        if not isinstance(u, dict) or u.get("id") not in idler:
            continue
        sebep = arama.uyum_sebebi(u)
        if sebep:
            ihlaller.append((u.get("id"), sebep))
    return ihlaller


def _uyum_rapor(ihlaller, kaynak):
    satirlar = ["HATA: UYUM KAPISI — %s REDDEDILDI (hicbir sey yazilmadi)." % kaynak]
    for uid, sebep in ihlaller:
        satirlar.append("  - id=%s: %s" % (uid, sebep))
    satirlar.append("  Sema (tools/arama.py): uyum = [{\"marka\": KAPALI kumeden ZORUNLU, "
                    "\"model\"/\"motor\"/\"oem\": opsiyonel metin, \"yil\": [bas, son]}]")
    satirlar.append("  `marka` ELLE YAZILMAZ: `uyum` doluyken duzelt.py onu "
                    "arama.marka_uyumdan_turet ile AYNI islemde kendisi yazar.")
    satirlar.append("  Alan OPSIYONEL: bos deger ([]) ya da --alan-sil uyum GECERLIDIR "
                    "(eski kayit sekline donus; `marka`ya DOKUNULMAZ).")
    satirlar.append("  Kapali marka kumesini genisletmek MIMAR karari: arama.py "
                    "UYUM_MARKA_IZINLI + MIMAR EKI elle guncellenir.")
    return "\n".join(satirlar)


def _gorsel_var(u):
    """Kayitta KULLANILABILIR gorsel var mi? (bos dize/None gorsel sayilmaz — build.py
    images_of ile AYNI karar)."""
    g = u.get("gorseller")
    return isinstance(g, list) and any(isinstance(x, str) and x for x in g)


def _ticari_hal_ihlalleri(onceki_hal, urunler, idler, gerekceler):
    """TICARI HAL KAPISI — `tur` / `gorselsiz` alanlarinin YAZIM SONRASI durumunu olcer.

    [(uid, sebep), ...] dondurur (bos = temiz). Alanlarin duzelt.py'ye acilmasinin sebebi
    bayragin TEK YONLU olmamasidir; bu kapi da "geri alinabilir ama savrulamaz" dengesini
    kurar. Kurallar (hepsi FAIL-CLOSED, hepsi YAZIM SONRASI kayit uzerinde):

      T1  `tur` alani varsa DEGERI kanonik sinif dizesi olmali (_tur_gecerli_acik_deger).
          Ozel uretime DONUS bos dize ile DEGIL `--alan-sil tur` ile yapilir: ayni durumun
          iki temsili ("alan yok" ve "") olsaydi okuyan taraflar sessizce ayrisirdi.
      T2  `gorselsiz` alani varsa DEGERI gercek boolean True olmali. Beyani KALDIRMAK
          `--alan-sil gorselsiz` iledir; `false` yazmak ucuncu bir durum uretirdi
          (parti-kontrol yalnizca `is True`yi beyan sayar).
      T3  `gorselsiz` beyani YALNIZ hazir ticari malda durabilir (arama.tur_kanonik ile
          olculur). Ozel uretim urununde muafiyet zaten dogmuyor; kaydin uzerinde ASILI
          kalan bayrak yarin sinif degisince SESSIZCE muafiyet acardi.
      T4  `gorselsiz` beyani YALNIZ gercekten gorselsiz kayitta durabilir. Gorselli bir
          kayitta bayrak celiskilidir ve gorseller sonradan bosaltilirsa uyuyan muafiyeti
          uyandirir.
      T5  🔴 SINIF ATLAMASI (hazir mal <-> ozel uretim) --gerekce ZORUNLU tutar. Bu gecis
          PARA ve CAYMA HAKKI yolunu degistirir (secenekler.js `tur`u okuyup malzeme/renk
          carpanini 1,00'e sabitler). Gerekce `.urunler-guard.log`a yazilir -> degisiklik
          izlenebilir; "kim, ne zaman, neden" kaydi olmadan sinif oynatilamaz.

    NEDEN "yalniz dokunulan kayitlar": _altkategori_ihlalleri ile AYNI gerekce — katalogun
    tamamini dogrulamak, bu cagriyla ILGISIZ eski bir ihlal yuzunden mesru bir duzeltmeyi
    bloklardi (kapi kapsam ekseni). Tum katalog ekseni parti-kontrol.py'nin isidir.
    """
    ihlaller = []
    for u in urunler:
        if not isinstance(u, dict) or u.get("id") not in idler:
            continue
        uid = u.get("id")

        if TUR_ALANI in u and not _tur_gecerli_acik_deger(u.get(TUR_ALANI)):
            ihlaller.append((uid, "T1 `tur` degeri kanonik sinif dizesi degil: %r "
                                 "(ozel uretime donmek icin: --alan-sil tur)"
                             % (u.get(TUR_ALANI),)))

        bayrak_var = GORSELSIZ_BAYRAK in u
        if bayrak_var and u.get(GORSELSIZ_BAYRAK) is not True:
            ihlaller.append((uid, "T2 `gorselsiz` yalniz gercek boolean true olabilir: %r "
                                 "(beyani kaldirmak icin: --alan-sil gorselsiz)"
                             % (u.get(GORSELSIZ_BAYRAK),)))
        elif bayrak_var:
            if not arama.tur_kanonik(u):
                ihlaller.append((uid, "T3 `gorselsiz` beyani yalniz hazir ticari malda "
                                     "durabilir; kaydin sinifi ozel uretim "
                                     "(bayragi da kaldir: --alan-sil gorselsiz)"))
            if _gorsel_var(u):
                ihlaller.append((uid, "T4 `gorselsiz` beyani gorselli kayitta duramaz "
                                     "(gorseller: %d adet)" % len(u.get("gorseller") or [])))

        eski = onceki_hal.get(uid)
        yeni = arama.tur_kanonik(u)
        if eski is not None and eski != yeni and not (gerekceler.get(uid) or "").strip():
            ihlaller.append(
                (uid, "T5 TICARI SINIF ATLAMASI (%s -> %s) --gerekce ZORUNLU: bu gecis "
                      "fiyat carpanini ve cayma hakki rejimini degistirir"
                 % (eski or "ozel uretim", yeni or "ozel uretim")))
    return ihlaller


def _ticari_hal_rapor(ihlaller, kaynak):
    satirlar = ["HATA: TICARI HAL KAPISI — %s REDDEDILDI (hicbir sey yazilmadi)." % kaynak]
    for uid, sebep in ihlaller:
        satirlar.append("  - id=%s: %s" % (uid, sebep))
    satirlar.append("  `tur` ve `gorselsiz` MESRU olarak geri alinabilir; kural: acik deger,")
    satirlar.append("  bayrak yalniz gorselsiz hazir malda, sinif atlamasi --gerekce ister.")
    return "\n".join(satirlar)


def _hal_haritasi(urunler, idler):
    """{id: kanonik_tur} — YAZIM ONCESI ticari sinif anlik goruntusu (T5 icin)."""
    return {u.get("id"): arama.tur_kanonik(u) for u in urunler
            if isinstance(u, dict) and u.get("id") in idler}


def _log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f:
            f.write("[%s] %s\n" % (ts, msg))
    except OSError:
        pass


def _parse_deger(raw, alan=None):
    s = raw.strip()
    if s[:1] in ("[", "{"):
        return json.loads(s)  # liste/sozluk
    # TICARI HAL alanlari BEYAN alanlaridir: `gorselsiz` GERCEK boolean true olmak
    # ZORUNDA (parti-kontrol `is True` arar). CLI'da her deger duz metne dusseydi
    # `--alan gorselsiz --deger true` "true" DIZESI yazar ve kapi onu hakli olarak
    # reddederdi -> alan CLI'dan hic konulamazdi (yeni bir tek-yonlu kapi). Bu yuzden
    # SADECE bu alanlarda deger once JSON olarak cozulmeye calisilir:
    #   true -> True (gecerli) · false/1/[] -> gecerli JSON ama kapi REDDEDER (T2)
    #   fiziksel/evet -> JSON degil, duz metin kalir (tur icin dogru, gorselsiz icin T2)
    # Baska hicbir alanin cozumlemesi degismez ("500 TL", basliklar, ... aynen metin).
    if alan in TICARI_HAL_ALANLARI:
        try:
            return json.loads(s)
        except ValueError:
            return raw
    return raw  # duz metin (fiyat, baslik, kategori, ...)


def _alan_tip_hatasi(alan, deger):
    """Izinli ama yapisal olan alanlar icin dar tip sozlesmesi; None = gecerli.

    `tavsiyeFilament` katalogda bos olmayan metin dizisi, filament_ortak.py ile
    secenekler.js de onu dizi olarak geziyor. Serbest metin acmak iki tuketiciyi
    sessizce ayirir. Malzeme adlarini burada kapali kumeye baglamiyoruz: tuketici
    taninmayan adi bilerek fail-closed `taninmayan` kolunda raporlar.
    """
    if alan == TAVSIYE_FILAMENT_ALANI:
        if (not isinstance(deger, list) or not deger
                or not all(isinstance(x, str) and x.strip() for x in deger)):
            return ("'%s' alani bos olmayan string ogelerden olusan bir dizi olmali; "
                    "ornek: [\"ASA\"]" % TAVSIYE_FILAMENT_ALANI)
    return None


def _atomic_write(path, obj):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _sil(args):
    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
        idx = next((i for i, p in enumerate(urunler)
                    if isinstance(p, dict) and p.get("id") == args.id), None)
        if idx is None:
            print("HATA: '%s' id'li urun urunler.json'da yok." % args.id, file=sys.stderr)
            return 1
        urunler.pop(idx)
        _atomic_write(URUNLER, urunler)

        sil_izin = []
        if os.path.exists(MANIFEST_SIL):
            try:
                with open(MANIFEST_SIL, encoding="utf-8") as f:
                    s = json.load(f)
                if isinstance(s, list):
                    sil_izin = s
            except ValueError:
                sil_izin = []
        if args.id not in sil_izin:
            sil_izin.append(args.id)
        _atomic_write(MANIFEST_SIL, sil_izin)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    _log("sil: %s -> kaldirildi (%s) (silme manifestine yazildi)" % (args.id, args.sil))
    print("Silindi: %s  (gerekce: %s)" % (args.id, args.sil))
    print("Guard bu silmeyi manifest sayesinde gecirir; commit sonrasi post-commit "
          "hook manifesti temizler.")
    return 0


def _manifest_oku(path, bos):
    """Var olan manifesti oku; yoksa/bozuksa `bos` tipini dondur."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, type(bos)):
                return m
        except ValueError:
            pass
    return bos


def _toplu_cozumle(yol):
    """islem.json -> (setler, alan_silmeler, urun_silmeler, gerekceler, hatalar).

    Yalnizca SEMA/izin/catisma dogrulamasi yapar (katalogtan bagimsiz);
    id'nin katalogda var olup olmadigi kilit altinda ayrica denetlenir.

    `gerekce`: OPSIYONEL anahtar; yalnizca TICARI SINIF atlamasinda ZORUNLU hale gelir
    (kararı _ticari_hal_ihlalleri verir, burasi sadece tasir). Ayni id icin birden fazla
    islemde verilirse ilk BOS OLMAYAN deger kullanilir — cagrinin o urune dair tek
    gerekcesi vardir.
    """
    hatalar = []
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except OSError as e:
        return {}, {}, {}, {}, ["islem dosyasi okunamadi: %s" % e]
    except ValueError as e:
        return {}, {}, {}, {}, ["islem dosyasi gecerli JSON degil: %s" % e]

    if isinstance(veri, dict) and "islemler" in veri:
        veri = veri["islemler"]
    if not isinstance(veri, list):
        return {}, {}, {}, {}, ["islem dosyasi bir dizi (ya da {\"islemler\": [...]}) olmali"]
    if not veri:
        return {}, {}, {}, {}, ["islem dosyasi bos"]

    setler, alan_silmeler, urun_silmeler, gerekceler = {}, {}, {}, {}
    for n, islem in enumerate(veri, 1):
        etiket = "islem #%d" % n
        if not isinstance(islem, dict):
            hatalar.append("%s: obje degil (%r)" % (etiket, islem))
            continue
        uid = islem.get("id")
        if not isinstance(uid, str) or not uid.strip():
            hatalar.append("%s: gecerli 'id' yok" % etiket)
            continue
        etiket = "%s (id=%s)" % (etiket, uid)

        eylem = [k for k in ("alan", "alan-sil", "sil") if k in islem]
        if len(eylem) != 1:
            hatalar.append("%s: tam olarak BIR eylem olmali "
                           "('alan'+'deger' | 'alan-sil' | 'sil'); bulunan: %s"
                           % (etiket, eylem or "hicbiri"))
            continue
        fazla = set(islem) - {"id", "alan", "deger", "alan-sil", "sil", "not", "gerekce"}
        if fazla:
            hatalar.append("%s: bilinmeyen anahtar(lar): %s"
                           % (etiket, ", ".join(sorted(fazla))))
            continue
        if "gerekce" in islem:
            g = islem["gerekce"]
            if not isinstance(g, str):
                hatalar.append("%s: 'gerekce' metin olmali (%r)" % (etiket, g))
                continue
            if g.strip() and not (gerekceler.get(uid) or "").strip():
                gerekceler[uid] = g

        if eylem[0] == "alan":
            alan = islem.get("alan")
            if "deger" not in islem:
                hatalar.append("%s: 'alan' verildi ama 'deger' yok" % etiket)
                continue
            if alan == "id":
                hatalar.append("%s: 'id' alani degistirilemez" % etiket)
                continue
            if alan not in DEGISTIRILEBILIR:
                hatalar.append("%s: bilinmeyen/izinsiz alan: %s (izinli: %s)"
                               % (etiket, alan, ", ".join(sorted(DEGISTIRILEBILIR))))
                continue
            tip_hatasi = _alan_tip_hatasi(alan, islem["deger"])
            if tip_hatasi:
                hatalar.append("%s: %s" % (etiket, tip_hatasi))
                continue
            onceki = setler.get(uid, {})
            if alan in onceki and json.dumps(onceki[alan], sort_keys=True) != \
                    json.dumps(islem["deger"], sort_keys=True):
                hatalar.append("%s: '%s' alani ayni cagrida FARKLI degerle iki kez verildi"
                               % (etiket, alan))
                continue
            setler.setdefault(uid, {})[alan] = islem["deger"]
        elif eylem[0] == "alan-sil":
            alan = islem.get("alan-sil")
            if not isinstance(alan, str) or not alan.strip():
                hatalar.append("%s: 'alan-sil' bir alan adi olmali" % etiket)
                continue
            if alan == "id":
                hatalar.append("%s: 'id' alani kaldirilamaz" % etiket)
                continue
            alan_silmeler.setdefault(uid, [])
            if alan not in alan_silmeler[uid]:
                alan_silmeler[uid].append(alan)
        else:  # sil
            gerekce = islem.get("sil")
            if not isinstance(gerekce, str) or not gerekce.strip():
                hatalar.append("%s: 'sil' kisa bir gerekce metni olmali" % etiket)
                continue
            urun_silmeler[uid] = gerekce

    # Catismalar: ayni alan hem set hem alan-sil; ya da urun silinirken alan islemi.
    for uid, alanlar in alan_silmeler.items():
        for alan in alanlar:
            if alan in setler.get(uid, {}):
                hatalar.append("id=%s: '%s' hem 'alan' hem 'alan-sil' ile verilemez"
                               % (uid, alan))
    for uid in urun_silmeler:
        if uid in setler or uid in alan_silmeler:
            hatalar.append("id=%s: 'sil' ayni id icin alan islemleriyle birlestirilemez" % uid)

    return setler, alan_silmeler, urun_silmeler, gerekceler, hatalar


def _toplu(yol):
    setler, alan_silmeler, urun_silmeler, gerekceler, hatalar = _toplu_cozumle(yol)
    if hatalar:
        print("HATA: toplu islem REDDEDILDI — hicbir sey yazilmadi.", file=sys.stderr)
        for h in hatalar:
            print("  - %s" % h, file=sys.stderr)
        return 2

    # UYUM/MARKA CATISMASI — kilitten ONCE: hicbir dosya acilmadan reddedilir, cikis kodu
    # RC_UYUM (2 DEGIL) ki cagiran "sema hatasi" ile "iki kaynak yarisi"ni ayirt edebilsin.
    catisma = _uyum_marka_catismasi(setler, alan_silmeler)
    if catisma:
        print(_uyum_catisma_rapor(catisma, "toplu islem"), file=sys.stderr)
        return RC_UYUM

    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
        eski_harita = gk.harita(urunler)   # koken kapisi icin YAZIM ONCESI durum
        idx_by_id = {}
        for i, p in enumerate(urunler):
            if isinstance(p, dict) and "id" in p:
                idx_by_id.setdefault(p["id"], i)

        yok = [uid for uid in list(setler) + list(alan_silmeler) + list(urun_silmeler)
               if uid not in idx_by_id]
        if yok:
            print("HATA: toplu islem REDDEDILDI — hicbir sey yazilmadi.", file=sys.stderr)
            for uid in sorted(set(yok)):
                print("  - id=%s: urunler.json'da boyle bir urun YOK" % uid, file=sys.stderr)
            return 1

        # --- BURADAN SONRASI YAZIM: tum dogrulamalar gecti. ---
        # Tek-urun kipiyle AYNI aciklama korumasi (ayni delik, ayni yama); yazimdan
        # ONCE, boylece manifest de korunmus degeri tasir.
        aciklama_raporlari = {}
        # T5 icin YAZIM ONCESI ticari sinif anlik goruntusu (tek-urun kipiyle AYNI kural).
        eski_hal = _hal_haritasi(urunler, set(setler) | set(alan_silmeler))
        # UYUM -> MARKA TURETIMI: yazimdan ONCE, `setler` uzerinde. Boylece turetilen
        # `marka` hem urunler.json'a hem guard izin manifestine AYNI deger olarak gider.
        turetilen_marka = _uyum_marka_turet(setler)
        for uid, alanlar in setler.items():
            r = _aciklama_koru_uygula(urunler[idx_by_id[uid]], alanlar)
            if r:
                aciklama_raporlari[uid] = r
        for uid, alanlar in setler.items():
            for alan, deger in alanlar.items():
                urunler[idx_by_id[uid]][alan] = deger
        for uid, alanlar in alan_silmeler.items():
            for alan in alanlar:
                urunler[idx_by_id[uid]].pop(alan, None)
        if urun_silmeler:
            urunler = [p for p in urunler
                       if not (isinstance(p, dict) and p.get("id") in urun_silmeler)]
        # GORSEL-KOKEN KAPISI — TEK yazimdan HEMEN ONCE, ayni kilit altinda.
        # Ihlal -> hicbir sey yazilmaz (urunler.json byte-esit kalir, izin manifesti
        # de olusmaz); toplu kipin "ya hep ya hic" sozlesmesi korunur.
        koken = gk.denetle(eski_harita, gk.harita(urunler), ROOT)
        if koken:
            print("HATA: toplu islem REDDEDILDI — hicbir sey yazilmadi.", file=sys.stderr)
            print(gk.rapor_metni(koken, "duzelt.py --toplu"), file=sys.stderr)
            return 4
        # ALT KATEGORI KAPISI — koken kapisiyla AYNI yer: TEK yazimdan HEMEN ONCE, ayni
        # kilit altinda. Ihlal -> urunler.json byte-esit kalir, izin manifesti OLUSMAZ
        # (toplu kipin "ya hep ya hic" sozlesmesi korunur).
        alt_ihlal = _altkategori_ihlalleri(
            urunler, set(setler) | set(alan_silmeler))
        if alt_ihlal:
            print(_altkategori_rapor(alt_ihlal, "toplu islem"), file=sys.stderr)
            return RC_ALTKATEGORI
        # TICARI HAL KAPISI — ayni yer, ayni "ya hep ya hic" sozlesmesi.
        hal_ihlal = _ticari_hal_ihlalleri(
            eski_hal, urunler, set(setler) | set(alan_silmeler), gerekceler)
        if hal_ihlal:
            print("HATA: toplu islem REDDEDILDI — hicbir sey yazilmadi.", file=sys.stderr)
            print(_ticari_hal_rapor(hal_ihlal, "toplu islem"), file=sys.stderr)
            return RC_TICARI_HAL
        # UYUM KAPISI — ayni yer (TEK yazimdan HEMEN ONCE), ayni kilit, ayni "ya hep ya
        # hic" sozlesmesi. Partinin TEK bir kirli kaydi TUM partiyi dusurur.
        uyum_ihlal = _uyum_ihlalleri(urunler, set(setler) | set(alan_silmeler))
        if uyum_ihlal:
            print("HATA: toplu islem REDDEDILDI — hicbir sey yazilmadi.", file=sys.stderr)
            print(_uyum_rapor(uyum_ihlal, "toplu islem"), file=sys.stderr)
            return RC_UYUM
        yeni_hal = _hal_haritasi(urunler, set(setler) | set(alan_silmeler))
        _atomic_write(URUNLER, urunler)  # TEK yazim

        if setler or alan_silmeler:
            manifest = _manifest_oku(MANIFEST, {})
            for uid, alanlar in setler.items():
                manifest.setdefault(uid, {})
                for alan, deger in alanlar.items():
                    manifest[uid][alan] = deger
            for uid, alanlar in alan_silmeler.items():
                manifest.setdefault(uid, {})
                for alan in alanlar:
                    manifest[uid][alan] = {"__alan_sil__": True}
            _atomic_write(MANIFEST, manifest)

        if urun_silmeler:
            sil_izin = _manifest_oku(MANIFEST_SIL, [])
            for uid in urun_silmeler:
                if uid not in sil_izin:
                    sil_izin.append(uid)
            _atomic_write(MANIFEST_SIL, sil_izin)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    n_alan = sum(len(v) for v in setler.values()) + sum(len(v) for v in alan_silmeler.values())
    n_urun = len(set(list(setler) + list(alan_silmeler)) | set(urun_silmeler))
    for uid in sorted(aciklama_raporlari):
        _rapor_bas(uid, aciklama_raporlari[uid])
    for uid in sorted(turetilen_marka):
        # Turetim SESSIZ olmasin: cagiran `marka`yi vermedi ama kataloga bir `marka`
        # yazildi — hangi degerin nereden geldigi ciktida ve logda gorunur.
        _log("uyum-turetim: %s -> marka=%s (uyum'dan TURETILDI, elle verilmedi)"
             % (uid, json.dumps(turetilen_marka[uid], ensure_ascii=False)))
        print("MARKA TURETILDI (uyum'dan): %s  -> %s"
              % (uid, json.dumps(turetilen_marka[uid], ensure_ascii=False)))
    for uid in sorted(set(list(setler) + list(alan_silmeler))):
        ozet = ", ".join("%s=%s" % (a, json.dumps(v, ensure_ascii=False))
                         for a, v in sorted(setler.get(uid, {}).items()))
        ek = ", ".join("%s=KALDIRILDI" % a for a in sorted(alan_silmeler.get(uid, [])))
        ozet = (ozet + ", " + ek) if (ozet and ek) else (ozet or ek)
        _log("toplu-duzelt: %s -> %s (izin manifestine yazildi)" % (uid, ozet))
        if yeni_hal.get(uid) != eski_hal.get(uid):
            hal_metni = "%s -> %s" % (eski_hal.get(uid) or "ozel uretim",
                                      yeni_hal.get(uid) or "ozel uretim")
            _log("ticari-hal: %s : %s (gerekce: %s)"
                 % (uid, hal_metni, (gerekceler.get(uid) or "").strip()))
            print("TICARI SINIF DEGISTI: %s : %s  (gerekce: %s)"
                  % (uid, hal_metni, (gerekceler.get(uid) or "").strip()))
        print("Duzeltildi: %s  (%s)" % (uid, ozet))
    for uid, gerekce in sorted(urun_silmeler.items()):
        _log("toplu-sil: %s -> kaldirildi (%s) (silme manifestine yazildi)" % (uid, gerekce))
        print("Silindi: %s  (gerekce: %s)" % (uid, gerekce))
    print("TOPLU: %d urun, %d alan islemi, %d silme — TEK kilit + TEK yazim."
          % (n_urun, n_alan, len(urun_silmeler)))
    print("Guard bu degisiklikleri manifest sayesinde gecirir; commit sonrasi post-commit "
          "hook manifesti temizler.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id", nargs="?",
                    help="degistirilecek/silinecek MEVCUT urun id'si")
    ap.add_argument("--toplu", metavar="ISLEM_JSON",
                    help="N urun/N alani TEK kilit + TEK yazimda uygula "
                         "(tek-urun argumanlariyla birlikte kullanilmaz)")
    ap.add_argument("--alan", action="append",
                    help="degistirilecek alan adi (tekrarlanabilir)")
    ap.add_argument("--deger", action="append",
                    help="yeni deger (her --alan icin bir tane; JSON icin [ veya { ile basla)")
    ap.add_argument("--sil", metavar="GEREKCE",
                    help="urunu TAMAMEN kaldir (--alan/--deger ile birlikte kullanilmaz); "
                         "deger kisa bir gerekce metnidir (log icin)")
    ap.add_argument("--alan-sil", action="append", dest="alan_sil",
                    help="urunden bu ALANI tamamen kaldir (tekrarlanabilir); "
                         "'id' kaldirilamaz")
    ap.add_argument("--gerekce", metavar="METIN",
                    help="TICARI SINIF (hazir mal <-> ozel uretim) degistiren yazimlarda "
                         "ZORUNLU kisa gerekce; .urunler-guard.log'a yazilir")
    args = ap.parse_args()

    if args.toplu is not None:
        if (args.id or args.alan or args.deger or args.sil is not None or args.alan_sil
                or args.gerekce is not None):
            print("HATA: --toplu tek-urun argumanlariyla (id/--alan/--deger/--sil/"
                  "--alan-sil/--gerekce) birlikte kullanilamaz. Toplu kipte gerekce "
                  "islemin kendi \"gerekce\" anahtarindadir.", file=sys.stderr)
            return 2
        return _toplu(args.toplu)

    if args.id is None:
        print("HATA: urun id'si gerekli (ya da --toplu <islem.json>).", file=sys.stderr)
        return 2

    if args.sil is not None:
        if args.alan or args.deger or args.alan_sil:
            print("HATA: --sil, --alan/--deger/--alan-sil ile birlikte kullanilamaz.",
                  file=sys.stderr)
            return 2
        return _sil(args)

    if not (args.alan or args.alan_sil):
        print("HATA: --alan/--deger, --alan-sil veya --sil gerekli.", file=sys.stderr)
        return 2
    if len(args.alan or []) != len(args.deger or []):
        print("HATA: --alan ve --deger sayisi esit olmali.", file=sys.stderr)
        return 2

    degisiklikler = {}
    for alan, deger in zip(args.alan or [], args.deger or []):
        if alan == "id":
            print("HATA: 'id' alani degistirilemez.", file=sys.stderr)
            return 2
        if alan not in DEGISTIRILEBILIR:
            print("HATA: bilinmeyen/izinsiz alan: %s (izinli: %s)"
                  % (alan, ", ".join(sorted(DEGISTIRILEBILIR))), file=sys.stderr)
            return 2
        try:
            degisiklikler[alan] = _parse_deger(deger, alan)
        except ValueError as e:
            print("HATA: '%s' alaninin degeri JSON olarak cozumlenemedi: %s" % (alan, e),
                  file=sys.stderr)
            return 2
        tip_hatasi = _alan_tip_hatasi(alan, degisiklikler[alan])
        if tip_hatasi:
            print("HATA: %s" % tip_hatasi, file=sys.stderr)
            return 2

    silinecek_alanlar = []
    for alan in args.alan_sil or []:
        if alan == "id":
            print("HATA: 'id' alani kaldirilamaz.", file=sys.stderr)
            return 2
        if alan in degisiklikler:
            print("HATA: '%s' hem --alan hem --alan-sil ile verilemez." % alan,
                  file=sys.stderr)
            return 2
        silinecek_alanlar.append(alan)

    # UYUM/MARKA CATISMASI — toplu kiple AYNI kural, AYNI cikis kodu, kilitten ONCE.
    catisma = _uyum_marka_catismasi({args.id: degisiklikler},
                                    {args.id: silinecek_alanlar})
    if catisma:
        print(_uyum_catisma_rapor(catisma, "duzeltme"), file=sys.stderr)
        return RC_UYUM

    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
        eski_harita = gk.harita(urunler)   # koken kapisi icin YAZIM ONCESI durum
        idx = next((i for i, p in enumerate(urunler)
                    if isinstance(p, dict) and p.get("id") == args.id), None)
        if idx is None:
            print("HATA: '%s' id'li urun urunler.json'da yok." % args.id, file=sys.stderr)
            return 1

        # aciklama reword'unde otomatik uretilen olcu satirini KORU (sessiz kayip yok).
        # Koruma YAZIMDAN ONCE calisir; boylece hem urunler.json'a hem guard izin
        # manifestine AYNI (korunmus) deger gider -> guard degisikligi geri almaz.
        aciklama_raporu = _aciklama_koru_uygula(urunler[idx], degisiklikler)
        eski_hal = _hal_haritasi(urunler, {args.id})   # T5 icin YAZIM ONCESI sinif
        # UYUM -> MARKA TURETIMI: toplu kiple AYNI fonksiyon, AYNI yer (yazimdan ve
        # manifestten ONCE) -> iki kip arasinda ikinci bir turetim mantigi DOGMAZ.
        turetilen_marka = _uyum_marka_turet({args.id: degisiklikler})

        # SADECE beyan edilen alanlari degistir; beyan disina dokunma.
        for alan, deger in degisiklikler.items():
            urunler[idx][alan] = deger
        for alan in silinecek_alanlar:
            urunler[idx].pop(alan, None)
        # GORSEL-KOKEN KAPISI — yazimdan HEMEN ONCE, ayni kilit altinda. Ihlal ->
        # ne urunler.json ne guard izin manifesti yazilir (degisiklik yalniz bellekte
        # kalir ve atilir).
        koken = gk.denetle(eski_harita, gk.harita(urunler), ROOT)
        if koken:
            print(gk.rapor_metni(koken, "duzelt.py"), file=sys.stderr)
            return 4
        # ALT KATEGORI KAPISI — yazimdan HEMEN ONCE, ayni kilit altinda. Ihlal -> ne
        # urunler.json ne izin manifesti yazilir (degisiklik yalniz bellekte kalir).
        alt_ihlal = _altkategori_ihlalleri(urunler, {args.id})
        if alt_ihlal:
            print(_altkategori_rapor(alt_ihlal, "duzeltme"), file=sys.stderr)
            return RC_ALTKATEGORI
        # TICARI HAL KAPISI — ayni yer, ayni kilit, ayni "hicbir sey yazilmaz" sozlesmesi.
        hal_ihlal = _ticari_hal_ihlalleri(eski_hal, urunler, {args.id},
                                          {args.id: args.gerekce})
        if hal_ihlal:
            print(_ticari_hal_rapor(hal_ihlal, "duzeltme"), file=sys.stderr)
            return RC_TICARI_HAL
        # UYUM KAPISI — ayni yer, ayni kilit, ayni "hicbir sey yazilmaz" sozlesmesi.
        uyum_ihlal = _uyum_ihlalleri(urunler, {args.id})
        if uyum_ihlal:
            print(_uyum_rapor(uyum_ihlal, "duzeltme"), file=sys.stderr)
            return RC_UYUM
        yeni_hal = _hal_haritasi(urunler, {args.id})   # kilit ALTINDA, yazilan haliyle
        _atomic_write(URUNLER, urunler)

        # Guard icin deger-bagli izin manifesti (birikimli).
        manifest = {}
        if os.path.exists(MANIFEST):
            try:
                with open(MANIFEST, encoding="utf-8") as f:
                    m = json.load(f)
                if isinstance(m, dict):
                    manifest = m
            except ValueError:
                manifest = {}
        manifest.setdefault(args.id, {})
        for alan, deger in degisiklikler.items():
            manifest[args.id][alan] = deger
        for alan in silinecek_alanlar:
            manifest[args.id][alan] = {"__alan_sil__": True}
        _atomic_write(MANIFEST, manifest)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    _rapor_bas(args.id, aciklama_raporu)
    for uid in sorted(turetilen_marka):
        _log("uyum-turetim: %s -> marka=%s (uyum'dan TURETILDI, elle verilmedi)"
             % (uid, json.dumps(turetilen_marka[uid], ensure_ascii=False)))
        print("MARKA TURETILDI (uyum'dan): %s  -> %s"
              % (uid, json.dumps(turetilen_marka[uid], ensure_ascii=False)))
    ozet = ", ".join("%s=%s" % (a, json.dumps(v, ensure_ascii=False))
                     for a, v in degisiklikler.items())
    if silinecek_alanlar:
        ek = ", ".join("%s=KALDIRILDI" % a for a in silinecek_alanlar)
        ozet = (ozet + ", " + ek) if ozet else ek
    _log("duzelt: %s -> %s (izin manifestine yazildi)" % (args.id, ozet))
    # SINIF ATLAMASI AYRI SATIR: gerekce ve yon `.urunler-guard.log`ta izlenebilir kalsin.
    if yeni_hal.get(args.id) != eski_hal.get(args.id):
        _hal_metni = "%s -> %s" % (eski_hal.get(args.id) or "ozel uretim",
                                   yeni_hal.get(args.id) or "ozel uretim")
        _log("ticari-hal: %s : %s (gerekce: %s)"
             % (args.id, _hal_metni, (args.gerekce or "").strip()))
        print("TICARI SINIF DEGISTI: %s  (gerekce: %s)"
              % (_hal_metni, (args.gerekce or "").strip()))
    print("Duzeltildi: %s  (%s)" % (args.id, ozet))
    print("Guard bu degisikligi manifest sayesinde gecirir; commit sonrasi post-commit "
          "hook manifesti temizler.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

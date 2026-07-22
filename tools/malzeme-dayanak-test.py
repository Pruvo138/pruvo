#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MALZEME DAYANAK KAPISI (kalici nobetci)

Kural (Okan, 21 Tem 2026): YAYINLANAN her yuzeyde MALZEME SINIFI olarak anilan her ad
tools/filamentler.json envanterinde DAYANAGI olmalidir. Uretemedigimiz/tedarik
edemedigimiz bir sinifi metinde vaat etmek ticari beyan riskidir.

🔴 KARAR KAYDI (kodun TURETEMEDIGI kisim; bagimsiz curutucunun bakacagi yer):
  ~/.claude/projects/-Users-okan-dev-pruvo/memory/malzeme-envanteri-beyan-karari.md
  (Okan 21 Tem 2026, pencereyle alindi — DAYANAK_KARAR_KAYDI sabiti). "Envanterde yok"
  ile "uretemiyoruz" arasindaki farki yalniz Okan'in karari ayirir; kod bunu uyduramaz.
  Kayittaki uygulama kurali AYNEN: "Dayanak kaydi YALNIZ onaylanan TAM ADI mesrulastirir
  (PA6-GF); ciplak PA6'yi ya da kuresel GF ekini ACMAMALI."

TARANAN GOVDE KAYNAKLARI
  A) landing         : sayfalar.CONTENT_PAGES — govde + baslik + meta
  B) ege-bilgi.md    : WhatsApp botu Ege'nin bilgi dosyasi (bot bu metni musteriye aktarir)
  C) statik-gorunur  : sss / gizlilik / hakkimizda / iletisim — GORUNUR metin
  D) statik-jsonld   : ayni 4 sayfanin JSON-LD bloklari (Google'in makineyle okudugu
                       acceptedAnswer metinleri). OLCULDU: sss/index.html'de
                       "Parcalar hangi malzemeden uretiliyor?" cevabi PA6+GF / PA12+GF /
                       POM adlarini FIILEN vaat ediyor — JSON-LD ayri bir yayin yuzeyidir.
Rapor "kaynak: <ad>" kirilimiyla basar; hangi govdeden geldigi gorunur.

⚠️ DUZELTME (KraL tur-4): "JSON-LD main'de UYARI'ydi, burada KIRMIZI'ya katilastirildi"
  iddiasi YANLISTI. OLCULDU (main 16d24a67 gercek repo verisiyle kosuldu, cikti aynen):
      "Taranan sayfa: 80 (+ ege-bilgi.md ek kaynak)"
  main JSON-LD'ye HIC bakmiyordu (ne UYARI ne KIRMIZI) ve 4 statik sayfayi hic taramiyordu.
  Yani C+D YENI yayin yuzeyleridir, var olan bir uyarinin katilastirilmasi DEGIL.

Nasil calisir
  1) tools/filamentler.json OKUNUR; envanter adlari ORADAN TURETILIR (kodda liste
     sabitlenmez -> tek kaynak). IKI AYRI DUZLEM vardir ve BIRBIRINE KARISMAZ:
       - "filamentler" = SATIS/URETIM envanteri. "ad" + "uzunAd" alanlarindan polimer
         jetonlari ayiklanir; "-" oncesi taban polimer de bu duzleme girer
         (orn. "Karbon katkili (PETG-CF/PA-CF)" -> PETG-CF, PA-CF, PETG, PA).
         Kuresel taban + kuresel takviye eki kumeleri YALNIZ buradan doldurulur.
       - "_dayanakMalzemeler" = BEYAN DAYANAGI (satista degil, siparis uzerine hizli
         tedarik: PA6-GF / PA12-GF / POM). 🔴 SART-1: bu kayitlar kuresel kumelere
         DOKULMEZ; yalnizca kaydin kendi "ad" alanindaki TAM AD (kanonik: buyuk harf,
         "+" -> "-") mesrulastirilir. Sonuc olculebilir:
             "PA6-CF ile uretiyoruz"  -> KIRMIZI (ciplak PA6 tabani acilmadi)
             ciplak "PA6 ile uretiyoruz" -> KIRMIZI (tam ad degil)
             "PETG-GF"                -> UYARI (kuresel GF eki acilmadi, sessizlesmez)
             "PA6-GF" / "PA6+GF"      -> YESIL (onayli tam ad)
         Onceki turda bu kayitlar kuresel taban+ek kumelerine doluyordu; olculen bedel:
         onaylanmamis PA-GF sinifi 77 landing sayfasinda SESSIZCE dayanakli sayiliyordu.
  2) Metinde gecen polimer sinifi adaylari LEKSIK bir sozlukle bulunur (bu sozluk
     envanter DEGIL; dunyadaki filament sinifi adlarinin listesi). Takviye ayraci olarak
     "-" ve "+" ikisi de kabul edilir (yayindaki gercek yazim "PA6+GF"). Her adayin
     TABAN polimeri satis envanterinde yoksa (ve tam adi dayanak listesinde degilse)
     KIRMIZI.
  3) Takviye eki (-CF / -GF) taban polimerden ayri degerlendirilir: taban
     envanterdeyse kapi KIRMIZI yakmaz, ama envanterde adi gecmeyen takviye eki
     UYARI olarak basilir (mimar karari bekler).

🟡 PA-GF UYARISI — SESSIZCE KAYBOLAMAZ (SART-2, KraL tur-4 karari)
  OLCULDU: landing govdelerinin 77'sinde "PA-CF / PA-GF" gecer. main bu yuzden
  "UYARI: PA-GF takviye eki 'GF' envanterde adlandirilmamis - 77 sayfa" basiyordu.
  KARAR: uyari GERI GELDI (secenek a), cunku karar kaydinda onaylanan adlar YALNIZ
  PA6-GF / PA12-GF / POM'dur; ciplak "PA-GF" (herhangi bir naylon + cam elyaf) onaylanmis
  DEGILDIR — onu dayanakli saymak Okan'in kararini kod eliyle GENISLETMEK olurdu.
  Uyari BLOKLAYICI degildir (main'de de degildi; 77 sayfayi CI'da kirmiziya cevirmek tum
  ekibin yayinini yanlis-pozitifle durdururdu) — metin duzeltmesi ArTisT/Okan duzlemidir.
  Fikstur F17 mekanizmayi kilitler: bir dayanak TAM ADI kuresel eki acarsa KIRMIZI.

🔴 BILINEN KOR NOKTA — V6 (KAPATILMADI, bilincli; adiyla yaziliyor)
  Mutasyon: filamentler.json'dan YALNIZ {"ad":"PETG"} kaydini silmek kapiyi YESIL birakir.
  Sebep: taban jetonu bilesik addan da turer ("Karbon katkili (PETG-CF/PA-CF)" -> PETG).
  Neden kapatilmadi (OLCULDU): "taban yalniz kaydin kendi ciplak adindan turesin" kurali
  ciplak PA'yi dayanaksiz yapar; ciplak PA bugun 3 govdede geciyor (sss gorunur + ayni
  sayfanin JSON-LD'si + ege-bilgi.md; yazim "naylon"/"PA") -> kapi ANINDA KIRMIZI yanar ve
  TUM EKIBIN yayini durur. "PA (naylon) satiyor muyuz?" sorusu Okan kapisidir, kodun
  turetebilecegi bir sey degil. Bu kor nokta ancak envanterde acik bir "ciplak ad" alani
  (or. {"ad":"PETG","ciplakSatilir":true}) veya Okan'in PA karari ile kapanir.

🔴 YASAKLI MALZEME KARA LISTESI (KARA_LISTE) — envanterle SUSTURULAMAZ
  Curutucu kanitladi: dayanak-kaydi mekanizmasi ayni zamanda bir SUSTURMA deligidir —
  filamentler.json'a {"ad":"PC","satista":false} eklenince "PC uretiyoruz" vaadi
  sessizce YESIL yanabiliyordu. Kara listedeki bir ad, taranan HERHANGI bir govdede
  VEYA filamentler.json'un ICINDE gecerse kapi KIRMIZI yakar; envanterde kaydi olsa
  BILE. Her ad icin "kim/ne zaman karar verdi" kodda yazilidir.

🔴 NEGATIF BAGLAM ELEYICISI YOK (bilincli karar, KraL tur 2)
  Onceki turda "ayni satirda olumsuzlama varsa eslesmeyi ele" diye bir eleyici
  denenmisti; curutucu OLCTU: "- PC ile üretim yok; ama isterse müşteriye PEEK ile
  üretip gönderiyoruz." satiri eleyiciyle YESIL yaniyordu — duz bir ticari vaat
  KACIYORDU. Eleyici GELMEDI. Olculdu (21 Tem, main HEAD 16d24a67): bugunku
  ege-bilgi.md'nin yasak listesi (NBR / FKM-Viton / EPDM / silikon / metal / cam)
  LEKSIK sozlukte GECMIYOR -> haksiz kirmizi YOK, eleyiciye ihtiyac YOK.
  Fikstur F4 bu karari kalici olarak kilitler (eleyici geri gelirse KIRMIZI).

📄 KAPSAM NOBETI — SAYI DEGIL VARLIK (KraL tur-7; tur-5/6 kararlarinin genellemesi)
  SAYI/KARAKTER TABANI bu kapida YASAK SINIFTIR: "landing >= 50", "statik-jsonld >= 2",
  "sizinti ciktisi >= 3" ve "sss JSON-LD >= 1200 karakter" tabanlarinin DORDU de ayri
  turlarda ayni yanlis-pozitifi uretti — mesru bir icerik/SEO kararinda kapi KIRMIZI
  yanip TUM EKIBIN yayinini durduruyordu (tur-7'de sss'ten FAQPage blogunu kaldirmak
  bile EXIT=1 idi; FAQ rich result emekliligi mesru karardir). Bugunku kural tek tip:
  - ZORUNLU_KAYNAKLAR'daki her kaynak en az 1 govde uretmeli -> yoksa KIRMIZI
    (kaynagi koddan SILEN mutasyonun nobeti; icerik BOYUTU kapinin isi degil).
  - BEKLENEN_JSONLD sayfasinin blogu kaybolursa UYARI (bloklamaz).
  - SIZINTI kapsami AD BAZLI (tur-6): kod tarafindan URETILEN iki DEGISMEZ cikti
    (public /filament-veri.js govdesi + ege-malzeme.py blogu) ZORUNLU; landing
    /malzeme-rehberi/ ciktisi kaybolursa UYARI. Bkz. ZORUNLU_SIZINTI_CIKTILARI,
    sizinti_kapsam(), fiksturler F12c + F20a-F20d; varlik davranisi D4 ile uctan uca.

DRIFT NOBETI: tools/ege-malzeme.py'nin BELLEKTE urettigi blok, ege-bilgi.md'deki
isaretciler arasindaki blokla BIREBIR ayni olmali. filamentler.json degisip
ege-bilgi.md guncellenmezse bot sessizce bayatlar -> KIRMIZI. (Dosyaya YAZILMAZ.)
Fikstur F18 bu nobeti UCTAN UCA kilitler (gecici dizinde sahte ege-malzeme.py + sahte
ege-bilgi.md): taze blok YESIL, bayat blok KIRMIZI, dosya/modul yoksa fail-closed.

SIZINTI KAPISI: "_dayanakMalzemeler" kayitlari satis kalemi DEGILDIR ->
"satista": false zorunlu, "tedarik" zorunlu, fiyat/katsayi/site alani YASAK
(Okan'in kilitli katsayi listesi disina cikilmaz). "_" onekli anahtar oldugu icin
build.py'nin urettigi public /filament-veri.js'e TASINMAZ ve ref["filamentler"]
uzerinde donen tum ureticiler (urun sayfasi cipleri, /malzeme-rehberi/,
tools/ege-malzeme.py) bu kayitlari GORMEZ -> ege-bilgi.md byte-ozdes kalir.

IC NOBETCI (--ic-nobetci ile tek basina da kosar; normal kosumda da HER SEFER calisir):
Bu kapinin KENDI davranislarini bellekte-fikstur ile kilitler (BEKLENEN_KONTROL_SAYISI
kontrol). Sebep: gercek veri zaten temiz oldugu icin, kapinin kodundan bir yetenegi
(kara liste / JSON-LD taramasi + hata mesajindaki SLUG / dayanak TAM-AD kapsami / dayanak
alan dogrulamasi / negatif-eleyici YOKLUGU / kaynak kapsami / DRIFT nobeti) SILEN bir
mutasyon gercek veride YESIL kalirdi. Fikstur nobetcileri o mutasyonlari oldurur.
OLCULDU (tur-4, mutasyon KOPYAYA uygulandi — canli dosyaya DEGIL): 9 mutasyonun 9'u
olduruldu; V6 (yukarida adiyla yazili kor nokta) beklendigi gibi hayatta kaldi.
OLCULDU (tur-6, KOPYADA): 11 mutasyonun 10'u olduruldu + 1 mesru degisim (landing slug'i)
dogru sekilde YESIL+UYARI verdi.

🔌 KABLO NOBETI — DAVRANIS FIKSTURLERI D1-D9 (tur-7 acti, tur-8 tekil kablolara indi)
  Ic nobetci fonksiyonlari TEK TEK kilitler ama onlari EXIT KODUNA/RAPORA baglayan
  kablolar nobetsizdi — OLCULDU: "kapsam_hata.extend(s_hata)" -> "extend([])" TEK JETON
  mutasyonu 49/49 fiksturu YESIL birakiyordu; tur-8'de curutucu 3 kablo daha olctu
  (sizinti/drift/envanter-kara "kirmizi = True" satirlari — ihlal BASILIP EXIT=0).
  davranis_nobetci() main()'i gecici dizinde sahte veri setiyle UCTAN UCA kosturur
  (stdout + exit kodu yakalar; gercek dosyalara DOKUNMAZ):
  D1 temiz=YESIL (sss JSON-LD'siz + kaynaklar URL'sinde 'pc') · D2 dayanaksiz vaat ·
  D3 zorunlu sizinti ciktisi eksik (extend kablosu) · D4 landing bos (varlik kontrolu) ·
  D5 kara liste envanter kaydi+sayfa (iki agiz) · D6 YALNIZ sizinti · D7 YALNIZ drift ·
  D8 YALNIZ envanter-kara · D9 ic_hata-yalniz nobetci kablosu (or->and mutasyonu).
  ⚠️ KALAN SINIF (adiyla, V6 gelenegi):
  1) GIRIS NOKTASI OZ-NOTRLEME — main() cagrisina davranis=False gecen / nobetci
     cagrilarini komple silen mutasyonu hicbir kapi kendi icinden yakalayamaz (kapi
     disiplin cihazidir, guvenlik siniri degil); bagimsiz curutucu + review duzlemi.
  2) TERMINAL DONUS JETONU (indirgenemez sinif; tur-9'da or->and kaydinin yerini
     aldi — curutucu YEDEK KABLO ile or->and'in fiksturle OLDUGUNU olctu, eski
     oz-maskeleme kaydi curudu ve kablo eklendi): main() sonundaki "return 1" ->
     "return 0" jetonu HER fiksturu deler — D fiksturleri ic kosumun DONUS DEGERINI
     olcer ve mutasyon donus yolunun KENDISIDIR; alarm basilir (❌ satirlari) ama
     dis cikis da ayni jetonla 0'a duser. Giris-noktasi oz-notrleme (1) ile ayni
     aile: kapinin SON cikis jetonu kapinin icinden nobetlenemez; mutasyon-kaniti
     kosumu + bagimsiz curutucu denetimi duzlemi.

🔴 FIKSTUR SIMETRISI (tur-5 ORNEK, tur-6 SINIF): dayanak fiksturleri gercek
  filamentler.json kayitlariyla AYNI ALANLARI tasir ("uzunAd" dahil). Aksi halde
  envanteri_coz'a dayanak "uzunAd"ini kuresel taban/ek kumesine doken bir "simetri"
  refactor'u 34/34 fiksturu YESIL gecerek SART-1 ile SART-2'yi ayni anda geri aliyordu
  (ciplak "PA6 ile uretiyoruz" KIRMIZI'dan YESIL'e donuyordu). F10b/F10c bunu oldurur.
  tur-6: simetri artik TEK ORNEK degil SINIF olarak kapali — SATIS fiksturleri de gercek
  alan setini tasir (_f_kayit: kisa/uzun/isiDetay/kisaEtiket/isiDayanimi/uv/su/darbe) ve
  ust duzey kardes anahtarlar (_aciklama / kategoriTavsiye / kaynaklar) fiksturde VARDIR.
  Kalici cozum ayrica KOD tarafinda: ENVANTER_OKUNAN_ALANLAR BEYAZ LISTESI (yalniz
  ad + uzunAd okunur), fikstur F19a (sabit) + F19b (davranis). OLCULDU (tur-6, KOPYADA):
  "aciklama metninden besleme" mutasyonu ONCE 40/40 YESIL geciyordu, SIMDI 10 fiksturu
  birden KIRMIZI yakiyor; beyaz listeyi delip alani DOGRUDAN okuyan varyant 6 fiksturu.
🔴 FIKSTUR KAPSAMI KODDA (tur-5): fikstur ad kumesi + kontrol sayisi artik
  BEKLENEN_FIKSTUR_ADLARI / BEKLENEN_KONTROL_SAYISI sabitlerinde KILITLI ve F0-kapsam
  fiksturu her kosumda dogrular; bir fikstur blogunu silen mutasyon KIRMIZI yanar
  (once sayi yalnizca bu docstring'de yaziyordu -> F16'yi silen mutasyon 29 kontrolle
  YESIL kaliyordu).

Fail-closed: filamentler.json / ege-bilgi.md / statik sayfa okunamaz-bozuksa,
JSON-LD ayristirilamazsa, beklenen bir kaynak bos gelirse KIRMIZI.
Bayraklar (mutasyon testi GERCEK dosyalari BOZMASIN diye tempfile kopyada kossun):
  --filament YOL  --ege YOL  --statik-kok DIZIN  --ege-malzeme YOL  --landing-kapali
Cikis: 0 = temiz, 1 = dayanaksiz ad / kara liste ihlali / kapsam / drift / okuma hatasi.
"""
import argparse
import collections
import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile

KOK = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(KOK)
sys.path.insert(0, KOK)

FILAMENT_JSON = os.path.join(KOK, "filamentler.json")
EGE_MD = os.path.join(ROOT, "ege-bilgi.md")
EGE_MALZEME_PY = os.path.join(KOK, "ege-malzeme.py")
STATIK_SAYFALAR = ["sss", "gizlilik", "hakkimizda", "iletisim"]
DAYANAK_ANAHTARI = "_dayanakMalzemeler"
DAYANAK_YASAK_ALAN = ["fiyat", "fiyatTL", "katsayi", "fiyatKatsayisi", "site",
                      "kategoriTavsiye"]
# Ticari beyanin dayanagini veren OKAN KARARI kodda degil, hafizada durur (kod bir
# ticari karari turetemez). Bagimsiz curutucu "bu beyanin kaynagi nerede?" diye
# sordugunda bakilacak tek yer:
DAYANAK_KARAR_KAYDI = ("~/.claude/projects/-Users-okan-dev-pruvo/memory/"
                       "malzeme-envanteri-beyan-karari.md")

# Envanter IKI AYRI DUZLEM (bkz. modul basligi SART-1):
#   tam/taban/ekler -> YALNIZ "filamentler" (satis/uretim) duzleminden
#   dayanak_tam     -> "_dayanakMalzemeler" kayitlarinin KANONIK TAM ADLARI
#                      (kuresel taban/ek kumelerine DOKULMEZ)
Envanter = collections.namedtuple(
    "Envanter", "tam taban ekler dayanak_tam dayanak_adlar")

# ---------------------------------------------------------------- KARA LISTE
# Kodda SABIT. Envantere kayit eklenerek susturulamaz (bkz. modul basligi).
# ad -> (kim/ne zaman karar verdi, gerekce)
KARA_LISTE = {
    "PC": ("Okan, 21 Tem 2026 (KraL tur-2 talimatiyla iletildi)",
           "Polikarbonat (PC) URETMIYORUZ ve tedarik dayanagi da YOK. Bu ad hicbir "
           "yayin yuzeyinde gecemez; filamentler.json'a kayit eklenerek SUSTURULAMAZ."),
}

# LEKSIK sozluk = "dunyada filament/polimer sinifi olarak kullanilan adlar".
# Envanteri TEMSIL ETMEZ; envanter filamentler.json'dan turetilir.
KISALTMALAR = [
    "PLA", "PETG", "PET", "PCTG", "ASA", "ABS", "TPU", "TPE", "PC", "PA",
    "PA6", "PA11", "PA12", "POM", "PP", "PE", "PVC", "PVA", "PEEK", "PEI",
    "ULTEM", "PPS", "PPSU", "PSU", "PMMA", "HIPS", "PVDF", "PBT", "SAN", "PSU",
]
TAKVIYE_EKLERI = ["CF", "GF", "CF15", "GF30", "GF25"]
# Turkce tam adlar -> kisaltma karsiligi
TAM_ADLAR = {
    "polikarbonat": "PC",
    "poliamid": "PA",
    "poliamit": "PA",
    "naylon": "PA",
    "nylon": "PA",
    "polipropilen": "PP",
    "polietilen": "PE",
    "poliasetal": "POM",
    "akrilik": "PMMA",
}
# Adayin hemen ardindan gelirse: musterinin mevcut sistemi anlatiliyor demektir.
URUN_SISTEM_KELIMELERI = ["dograma", "doğrama", "pencere", "kapi", "kapı", "panjur",
                          "profil", "sineklik", "cam", "kasa"]

TR_HARF = "0-9A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû"

# 🔴 KAPSAM NOBETI = VARLIK KONTROLU (KraL tur-7; SAYI/KARAKTER TABANI YASAK SINIF).
# Onceki turlarin "landing >= 50 govde" ve "sss JSON-LD >= 1200 karakter" tabanlari,
# daha once reddedilen desenin ta kendisiydi: mesru bir icerik kucultmesi/SEO karari
# tum ekibin yayinini durdurabilirdi. Yeni kural: asagidaki kaynaklarin HER BIRI en az
# 1 govde uretti mi? Bir kaynagi koddan SILEN mutasyon burada olur (gercek veri temiz
# oldugu icin kaynak silinince kapi aksi halde sessizce YESIL kalirdi); icerik BOYUTU
# kapinin isi DEGILDIR. Kablo davranisi D4 fiksturuyle uctan uca kilitli.
ZORUNLU_KAYNAKLAR = ("landing", "ege-bilgi.md", "statik-gorunur")

# JSON-LD blogu bugun OLAN sayfalar (olculdu: sss + iletisim; gizlilik/hakkimizda'da YOK).
# Blok kaybolursa UYARI — KIRMIZI DEGIL (KraL tur-7): FAQPage rich result'i emekli edip
# blogu KALDIRMAK mesru bir SEO karari, yayini durduramaz. JSON-LD tarama YETENEGI
# bellekte F5a/F5b/F6 fiksturleriyle kilitlidir; var olan bloklar yine taranir ve
# icindeki dayanaksiz ad KIRMIZI yakar.
BEKLENEN_JSONLD = ("sss", "iletisim")

# 🔴 SIZINTI KAPSAMI da SAYI DEGIL AD BAZLI (KraL tur-6; ustteki VARLIK modeliyle ayni sinif).
# Eski kural "sizinti taramasi >= 3 cikti gormeli" idi; bu, ayni turda REDDEDILEN SAYI TABANI
# deseninin ta kendisiydi (statik-jsonld tabani 2 -> mesru bir SEO duzenlemesi TUM EKIBIN
# yayinini durduruyordu). Ucuncu cikti /malzeme-rehberi/ bir LANDING sayfasidir: ArTisT/KraL
# o slug'i yeniden adlandirdiginda ya da sayfayi birlestirdiginde sayi 3'ten 2'ye duser ve
# kapi, hicbir sizinti olmadigi halde KIRMIZI yanardi. Yeni kural:
#   ZORUNLU_SIZINTI_CIKTILARI  -> kaybolursa KIRMIZI (bu iki cikti DEGISMEZ: biri build.py'nin
#       public /filament-veri.js govdesi, digeri ege-malzeme.py'nin urettigi blok; ikisi de
#       kod tarafindan URETILIR, icerik kararlarindan bagimsizdir)
#   BEKLENEN_SIZINTI_CIKTILARI -> zorunlu olmayan cikti (landing /malzeme-rehberi/) kaybolursa
#       UYARI, bloklamaz.
# Bu ikili, "uretimler listesini kirp -> kapi kanit uretmeden YESIL kalsin" mutasyonunu
# oldurmeye yeter: iki DEGISMEZ ciktinin biri dusunce KIRMIZI yanar (fikstur F20).
SIZINTI_CIKTI_FILAMENT_JS = "public /filament-veri.js govdesi"
SIZINTI_CIKTI_EGE_BLOK = "ege-malzeme.py uretilen blok"
SIZINTI_CIKTI_MALZEME_REHBERI = "/malzeme-rehberi/ sayfasi"
MALZEME_REHBERI_SLUG = "malzeme-rehberi"
ZORUNLU_SIZINTI_CIKTILARI = (SIZINTI_CIKTI_FILAMENT_JS, SIZINTI_CIKTI_EGE_BLOK)
BEKLENEN_SIZINTI_CIKTILARI = ZORUNLU_SIZINTI_CIKTILARI + (SIZINTI_CIKTI_MALZEME_REHBERI,)

# 🔴 ENVANTER BEYAZ LISTESI (KraL tur-6 — "aciklama metninden besleme" mutasyon SINIFI).
# envanteri_coz SATIS kayitlarindan YALNIZ bu alanlari okur. Gercek filamentler.json
# kayitlari ayrica kisa/uzun/isiDetay/kisaEtiket/isiDayanimi/uv/su/darbe tasir ve bu
# metinlerde POLIMER ADI GECER (or. isiDetay: "PETG-CF ~70°C"). Bu alanlardan birini
# kuresel taban/ek kumesine dokmek SART-1 + SART-2'yi AYNI ANDA geri alir: ciplak PA6 ve
# kuresel GF eki sessizce "dayanakli" olur. Beyaz liste hem KOD tarafinda tek gecit,
# hem de fikstur F19 tarafindan kilitlidir (fiksturler gercek kayit alan setini tasir).
ENVANTER_OKUNAN_ALANLAR = ("ad", "uzunAd")


def kanonik_ad(ad):
    """Malzeme tam adini KANONIK bicime getirir: buyuk harf, "+" ayraci "-" olur,
    bosluklar atilir. Yayindaki gercek yazim "PA6+GF", envanterdeki ad "PA6-GF" —
    ikisi AYNI sinif; ayrac farki bir dayanagi gecersiz kilmamali."""
    return re.sub(r"\s+", "", (ad or "").upper()).replace("+", "-")


def _jeton_ayikla(metin):
    """filamentler.json ad/uzunAd alanindan polimer jetonlarini ayiklar.
    Tek harfli jetonlar (°C'deki 'C' gibi) polimer adi degildir; elenir."""
    ham = re.findall(r"[A-Z][A-Z0-9]*(?:[-+][A-Z]{2}[0-9]{0,2})?", metin or "")
    ham = [kanonik_ad(j) for j in ham]
    return set(j for j in ham if len(j.split("-")[0]) >= 2)


def dayanak_dogrula(dayanak):
    """_dayanakMalzemeler kayitlari SATIS KALEMI DEGILDIR; sizinti kapisi.
    Hatada ValueError firlatir (fail-closed). -> ad listesi"""
    if not isinstance(dayanak, list):
        raise ValueError("filamentler.json: '%s' liste degil" % DAYANAK_ANAHTARI)
    adlar = []
    for kayit in dayanak:
        if not isinstance(kayit, dict) or not kayit.get("ad"):
            raise ValueError("%s: 'ad' alani olmayan kayit" % DAYANAK_ANAHTARI)
        if kayit.get("satista") is not False:
            raise ValueError('%s["%s"]: "satista": false ZORUNLU (satis kalemi degil)'
                             % (DAYANAK_ANAHTARI, kayit["ad"]))
        if not kayit.get("tedarik"):
            raise ValueError('%s["%s"]: "tedarik" alani ZORUNLU (dayanagin ne oldugu yazilmali)'
                             % (DAYANAK_ANAHTARI, kayit["ad"]))
        for yasak in DAYANAK_YASAK_ALAN:
            if yasak in kayit:
                raise ValueError(
                    '%s["%s"]: "%s" alani YASAK — fiyat katsayisi Okan\'in kilitli '
                    "listesindedir, dayanak kaydi satis kalemi degildir"
                    % (DAYANAK_ANAHTARI, kayit["ad"], yasak))
        adlar.append(kayit["ad"])
    return adlar


def envanteri_coz(veri):
    """Ayristirilmis filamentler.json sozlugu -> Envanter(tam, taban, ekler,
    dayanak_tam, dayanak_adlar). Fail-closed: hata halinde ValueError/KeyError.

    🔴 SART-1 (karar kaydi: DAYANAK_KARAR_KAYDI): "_dayanakMalzemeler" kayitlari
    kuresel taban/ek kumelerine DOKULMEZ. Dayanak kaydi YALNIZ kendi kanonik TAM
    ADINI mesrulastirir; ciplak tabani (PA6) ve kuresel eki (GF) ACMAZ.

    🔴 BEYAZ LISTE: satis kaydindan YALNIZ ENVANTER_OKUNAN_ALANLAR okunur. Aciklama
    alanlari (kisa/uzun/isiDetay/kisaEtiket) polimer adi TASIR; onlari beslemek
    SART-1 + SART-2'yi geri alir. Ust duzey kardes anahtarlar (_aciklama,
    kategoriTavsiye, kaynaklar) da OKUNMAZ."""
    kayitlar = veri["filamentler"]
    if not kayitlar:
        raise ValueError("filamentler.json: 'filamentler' listesi bos")
    dayanak = veri.get(DAYANAK_ANAHTARI, [])
    dayanak_adlar = dayanak_dogrula(dayanak)

    tam = set()
    for kayit in kayitlar:  # YALNIZ satis/uretim duzlemi
        for alan in ENVANTER_OKUNAN_ALANLAR:  # BEYAZ LISTE — baska alan OKUNMAZ
            tam |= _jeton_ayikla(kayit.get(alan, ""))
    taban, ekler = set(), set()
    for jeton in tam:
        parca = jeton.split("-")
        taban.add(parca[0])
        if len(parca) > 1:
            ekler.add(parca[1])
    if not taban:
        raise ValueError("filamentler.json: polimer jetonu turetilemedi")
    # Dayanak: kaydin "ad" alanindaki TAM AD (kanonik). "uzunAd" BILEREK
    # kullanilmaz — "Cam elyaf takviyeli naylon (PA6-GF)" icindeki "naylon" ciplak
    # PA'yi mesrulastirmaya kalkardi.
    dayanak_tam = set(kanonik_ad(ad) for ad in dayanak_adlar)
    return Envanter(tam, taban, ekler, dayanak_tam, dayanak_adlar)


def envanteri_oku(yol=None):
    """Geriye donuk API — dosyadan okur."""
    with io.open(yol or FILAMENT_JSON, encoding="utf-8") as fp:
        return envanteri_coz(json.load(fp))


# ------------------------------------------------------------------ aday bulucu
def _html_soy(html):
    duz = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", duz)


def _aday_deseni():
    kis = sorted(set(KISALTMALAR), key=len, reverse=True)
    ekler = "|".join(sorted(set(TAKVIYE_EKLERI), key=len, reverse=True))
    tam = "|".join(sorted(TAM_ADLAR, key=len, reverse=True))
    # Takviye ayraci "-" VE "+": yayindaki gercek yazim "PA6+GF" (sss/hakkimizda),
    # envanterdeki kanonik ad "PA6-GF". Ayrac farki dayanagi gecersiz kilmamali;
    # OLCULDU (87 govde, eski/yeni desen eslesme-eslesme karsilastirildi): "+" kabulu
    # 3 govdede 5 eslesmeyi kanonize eder — statik-gorunur/sss (PA6, PA12),
    # statik-jsonld/sss (PA6, PA12), statik-gorunur/hakkimizda (PA6) — ve BASKA HICBIR
    # eslesmeyi degistirmez (ek grubu yalniz CF/GF ailesini kabul eder).
    return re.compile(
        r"(?<![%s])(?:(?P<kisa>%s)(?:[-+](?P<ek>%s))?|(?P<tam>%s))(?![%s])"
        % (TR_HARF, "|".join(kis), ekler, tam, TR_HARF),
        re.IGNORECASE,
    )


ADAY_DESENI = _aday_deseni()


def _urun_sistemi_mi(metin, bitis):
    """Adayin hemen ardindaki kelime musterinin mevcut sistemini mi anlatiyor?
    ("PVC dograma / PVC pencere" = musterinin sistemi, bizim malzeme vaadimiz degil.)
    Olculen ayrisma (main'den devralindi): PVC 3/3 sayfa elendi, PC 75/75 yakalandi."""
    kalan = metin[bitis:bitis + 40].strip().lower()
    ilk = re.split(r"[^%s]+" % TR_HARF, kalan)
    ilk = ilk[0] if ilk else ""
    return bool(ilk) and any(ilk.startswith(k) for k in URUN_SISTEM_KELIMELERI)


def adaylari_bul(metin):
    """metinde gecen malzeme sinifi adaylarini (kisa, ek, ham) uclusu olarak uretir.
    ham = metinde FIILEN gecen yazim (or. 'polikarbonat' -> kisa 'PC').
    🔴 OLUMSUZLAMA/NEGATIF BAGLAM ELEYICISI YOKTUR (bilincli — modul basligina bak)."""
    for eslesme in ADAY_DESENI.finditer(metin):
        if eslesme.group("tam"):
            ham = eslesme.group("tam")
            kisa = TAM_ADLAR[ham.lower()]
            ek = None
        else:
            ham = eslesme.group("kisa")
            kisa = ham.upper()
            # Kisaltmalar BUYUK harfle yazilir; "pet"/"san"/"pvc pencere" gibi
            # kucuk harfli kullanim genellikle Turkce-Ingilizce bir kelimedir ->
            # yanlis-pozitif kapisi. OLCULDU (21 Tem, 87 govde): bu sart bugun
            # SADECE 2 eslesme eliyor, ikisi de "pvc pencere".
            # 🔴 ISTISNA — KARA LISTE: en yuksek bahisli kural buyuk/kucuk harfe
            # takilmasin ("pc ile üretiyoruz" da vaattir). OLCULDU: taranan 87
            # govdenin hicbirinde kucuk harfli "pc" YOK -> yanlis-pozitif maliyeti 0.
            if ham != ham.upper() and kisa not in KARA_LISTE:
                continue
            ek = (eslesme.group("ek") or "").upper() or None
        if _urun_sistemi_mi(metin, eslesme.end()):
            continue
        yield kisa, ek, ham


def sayfa_adaylari(metin):
    """Geriye donuk API: metinde gecen malzeme sinifi adaylari -> {(kisaltma, ek)}"""
    return set((kisa, ek) for kisa, ek, _ham in adaylari_bul(metin))


# ------------------------------------------------------------- govde kaynaklari
def govdeler_landing():
    """kaynak A: sayfalar.CONTENT_PAGES — govde + baslik + meta."""
    import sayfalar
    for slug, baslik, meta, fn in sayfalar.CONTENT_PAGES:
        yield ("landing", slug, _html_soy(fn()) + " . " + baslik + " . " + meta)


def govdeler_ege(yol):
    """kaynak B: ege-bilgi.md (WhatsApp botunun bilgi dosyasi). Fail-closed: bos -> hata."""
    with io.open(yol, encoding="utf-8") as f:
        icerik = f.read()
    if not icerik.strip():
        raise ValueError("ege-bilgi.md bos")
    yield ("ege-bilgi.md", os.path.basename(yol), _html_soy(icerik))


def jsonld_metinleri(ham, kaynak_adi=None):
    """HTML'deki JSON-LD bloklarindaki TUM string degerler (acceptedAnswer dahil).
    -> (blok listesi, metin listesi). Fail-closed: blok ayristirilamazsa ValueError.

    kaynak_adi: hata mesajina yazilacak SAYFA KIMLIGI (slug + dosya yolu). Bu kapi
    CI'da tum ekibin yayinini durdurur; "JSON-LD ayristirilamadi" mesaji 4 sayfadan
    HANGISI oldugunu soylemezse mimar/isci hatayi ariyor -> slug ZORUNLU bilgi."""
    metinler = []
    bloklar = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        ham, flags=re.S | re.I)
    for sira, blok in enumerate(bloklar, 1):
        try:
            veri = json.loads(blok)
        except Exception as hata:
            raise ValueError(
                "JSON-LD ayristirilamadi [%s · %d/%d. blok]: %s | blok basi: %s"
                % (kaynak_adi or "kaynak bilinmiyor", sira, len(bloklar), hata,
                   " ".join(blok.split())[:120]))

        def gez(dugum):
            if isinstance(dugum, dict):
                for deger in dugum.values():
                    gez(deger)
            elif isinstance(dugum, list):
                for deger in dugum:
                    gez(deger)
            elif isinstance(dugum, str):
                metinler.append(dugum)
        gez(veri)
    return bloklar, metinler


def govdeler_statik(kok):
    """kaynak C + D: 4 statik sayfa — GORUNUR metin ve JSON-LD AYRI govdeler.
    Okuma/ayristirma hatasi HANGI SAYFA oldugunu soyleyerek yukselir (SART-3)."""
    for slug in STATIK_SAYFALAR:
        yol = os.path.join(kok, slug, "index.html")
        try:
            with io.open(yol, encoding="utf-8") as f:
                ham = f.read()
        except Exception as hata:
            raise ValueError("statik sayfa okunamadi [%s · %s]: %s" % (slug, yol, hata))
        gorunur = re.sub(r"<(script|style)\b.*?</\1>", " ", ham, flags=re.S | re.I)
        yield ("statik-gorunur", slug, _html_soy(gorunur))
        bloklar, metinler = jsonld_metinleri(ham, "%s · %s" % (slug, yol))
        if bloklar:
            yield ("statik-jsonld", slug, " . ".join(metinler))


# ------------------------------------------------------------------- drift nobeti
def _modul_yukle(yol):
    spec = importlib.util.spec_from_file_location("ege_malzeme_modul", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def blok_karsilastir(uretilen, icerik, basla, bitir):
    """(tamam_mi, mesaj) — isaretciler arasi blok uretilenle BIREBIR mi?"""
    if basla not in icerik or bitir not in icerik:
        return False, "ege-bilgi.md'de FILAMENT-REF isaretcileri YOK"
    mevcut = icerik[icerik.index(basla):icerik.index(bitir) + len(bitir)]
    if mevcut == uretilen:
        return True, ("ege-bilgi.md FILAMENT-REF blogu ege-malzeme.py ciktisiyla "
                      "BIREBIR (%d karakter)" % len(mevcut))
    fark = next((i for i in range(min(len(mevcut), len(uretilen)))
                 if mevcut[i] != uretilen[i]), min(len(mevcut), len(uretilen)))
    return False, ("blok BAYAT: ilk fark %d. karakterde | dosya=%r | uretilen=%r"
                   % (fark, mevcut[fark:fark + 60], uretilen[fark:fark + 60]))


def drift_kontrolu(ege_yol, ege_malzeme_yol):
    """ege-malzeme.py'nin BELLEKTE urettigi blok == ege-bilgi.md'deki blok mu?
    Dosyaya YAZMAZ. -> (tamam_mi, mesaj, uretilen_blok)
    Fail-closed: modul yuklenemez / dosya okunamazsa (False, sebep, None).
    (main() bu fonksiyonu CAGIRIR — mantik satir-ici tekrarlanmaz.)"""
    try:
        modul = _modul_yukle(ege_malzeme_yol)
        uretilen = modul.bolum_uret()
        with io.open(ege_yol, encoding="utf-8") as f:
            icerik = f.read()
    except Exception as hata:
        return False, "drift kontrolu kosulamadi -> %s" % hata, None
    tamam, mesaj = blok_karsilastir(uretilen, icerik, modul.BASLA, modul.BITIR)
    return tamam, mesaj, uretilen


# ------------------------------------------------------------------ degerlendirme
def degerlendir(kaynaklar, env):
    """kaynaklar: [(kaynak, slug, metin), ...] · env: Envanter
    -> (ozet, dayanaksiz, kara_ihlal, ek_uyarisi)

    Siralama (SART-1):
      1) kara liste  -> KIRMIZI (envanter/dayanak EZILEMEZ)
      2) TAM AD dayanak listesinde mi (PA6-GF) -> temiz. YALNIZ tam ad; ciplak taban
         (PA6) ve kuresel ek (GF) bu yolla ACILMAZ.
      3) taban SATIS envanterinde degil -> KIRMIZI
      4) ek SATIS envanterinde adlandirilmamis -> UYARI (bloklamaz)"""
    ozet = {}            # kaynak -> {"govde": n, "adlar": set(), "metin": karakter}
    dayanaksiz = {}      # kisaltma -> [(kaynak, slug, ham), ...]
    kara_ihlal = {}      # kisaltma -> [(kaynak, slug, ham), ...]
    ek_uyarisi = {}      # (kisaltma, ek) -> ["kaynak/slug", ...]
    for kaynak, slug, metin in kaynaklar:
        sayac = ozet.setdefault(kaynak, {"govde": 0, "adlar": set(), "metin": 0})
        sayac["govde"] += 1
        sayac["metin"] += len(metin)
        for kisa, ek, ham in adaylari_bul(metin):
            tam_ad = kisa if not ek else "%s-%s" % (kisa, ek)
            sayac["adlar"].add(tam_ad)
            if kisa in KARA_LISTE:
                # 🔴 KARA LISTE ENVANTERI EZER: kayit olsa bile KIRMIZI.
                kara_ihlal.setdefault(kisa, []).append((kaynak, slug, ham))
            elif tam_ad in env.dayanak_tam:
                continue          # onaylanan TAM AD — dayanakli
            elif kisa not in env.taban:
                dayanaksiz.setdefault(kisa, []).append((kaynak, slug, ham))
            elif ek and ek not in env.ekler:
                ek_uyarisi.setdefault((kisa, ek), []).append("%s/%s" % (kaynak, slug))
    return ozet, dayanaksiz, kara_ihlal, ek_uyarisi


def dayanak_taban_jetonlari(dayanak_adlar):
    """['PA6-GF', 'POM'] -> {'PA6', 'POM'} (taban polimer jetonlari)."""
    return set(ad.split("-")[0].upper() for ad in dayanak_adlar)


def dayanak_sizintisi(dayanak_adlar, uretimler):
    """SIZINTI KONTROLU (calistirilabilir kanit): "_dayanakMalzemeler" kayitlari
    SATIS/URETIM duzlemine SIZMAMALI. uretimler = [(uretim adi, uretilen metin), ...]
    (public /filament-veri.js govdesi, ege-malzeme.py'nin urettigi blok,
    /malzeme-rehberi/ sayfasi). Bir dayanak adi bu ciktilarin BIRINDE gorunurse
    -> sizinti. -> {uretim adi: [jeton, ...]}"""
    hedef = dayanak_taban_jetonlari(dayanak_adlar)
    sizinti = {}
    for ad, metin in uretimler:
        gorulen = set(kisa for kisa, _ek in sayfa_adaylari(metin))
        ortak = sorted(gorulen & hedef)
        if DAYANAK_ANAHTARI in (metin or ""):
            ortak.append(DAYANAK_ANAHTARI)
        if ortak:
            sizinti[ad] = ortak
    return sizinti


def sizinti_kapsam(uretim_adlari, landing_acik=True):
    """SIZINTI taramasinin KAPSAMI yeterli mi? -> (kapsam_hatalari, uyarilar)

    KAPSAM NOBETIYLE AYNI BICIM — AD BAZLI, SAYI TABANI YOK:
      - ZORUNLU_SIZINTI_CIKTILARI'ndan biri eksik -> KIRMIZI (kod tarafindan uretilen,
        icerik kararindan bagimsiz DEGISMEZ ciktilar)
      - BEKLENEN ama zorunlu olmayan cikti (landing /malzeme-rehberi/) eksik -> UYARI
    landing_acik=False (yalniz --landing-kapali olcum kosumu) -> landing kaynakli cikti
    zaten taranmaz, uyari da basilmaz (her kosumda gurultu olurdu)."""
    gorulen = set(uretim_adlari)
    hatalar = []
    for ad in ZORUNLU_SIZINTI_CIKTILARI:
        if ad not in gorulen:
            hatalar.append(
                "ZORUNLU sizinti ciktisi '%s' taranmadi (uretim listesi kirpilmis ya da "
                "cikti uretilemiyor) — bu cikti kod tarafindan URETILIR, icerik kararindan "
                "bagimsizdir; eksikligi kapinin kanit uretmedigi anlamina gelir" % ad)
    uyarilar = []
    if landing_acik:
        for ad in BEKLENEN_SIZINTI_CIKTILARI:
            if ad in ZORUNLU_SIZINTI_CIKTILARI or ad in gorulen:
                continue
            uyarilar.append(
                "KAPSAM - sizinti taramasinda '%s' ciktisi YOK/kaldirilmis (bloklamaz: "
                "landing slug'i yeniden adlandirilmis olabilir; zorunlu cikti(lar): %s)"
                % (ad, ", ".join(ZORUNLU_SIZINTI_CIKTILARI)))
    return hatalar, uyarilar


def ek_uyari_satirlari(ek_uyarisi):
    """SART-2 UYARISININ RAPORU — satirlari URETIR (yazdirmaz) ki fiksturlenebilsin.

    🔴 Bu fonksiyon BILEREK main()'den ayrilmistir (KraL tur-6): rapor main icinde
    satir-ici bir "if ek_uyarisi:" blogundayken, blogu susturan mutasyon 40/40 YESIL
    geciyordu — yani "F17 bunu KIRMIZI yakar" iddiasi OLCULEREK YANLIS cikti (F17
    degerlendir()'in DONDURDUGU sozlugu kontrol eder, RAPORU degil). Artik rapor
    metnini fikstur F21 kilitler."""
    if not ek_uyarisi:
        return ["UYARI yok: adlandirilmamis takviye eki gecmiyor"]
    satirlar = []
    for (kisa, ek), yerler in sorted(ek_uyarisi.items()):
        # govde = benzersiz kaynak/slug (main'in "77 sayfa" sayimiyla ayni taban),
        # eslesme = ham gecis sayisi (ayni sayfada birden fazla olabilir).
        satirlar.append(
            "UYARI: %s-%s takviye eki '%s' SATIS envanterinde adlandirilmamis "
            "(taban %s dayanakli, ama '%s-%s' onaylanan dayanak TAM ADLARI "
            "arasinda YOK) - %d govde / %d eslesme: %s"
            % (kisa, ek, ek, kisa, kisa, ek, len(set(yerler)), len(yerler),
               ", ".join(sorted(set(yerler))[:4])))
    satirlar.append("  (UYARI bloklamaz — metin duzeltmesi/onay ArTisT+Okan duzlemi; "
                    "karar kaydi: %s)" % DAYANAK_KARAR_KAYDI)
    return satirlar


def kara_liste_envanterde(veri):
    """filamentler.json KAYITLARININ ad/uzunAd alanlarinda kara listedeki bir ad var mi?
    (Susturma deliginin ikinci agzi: envantere kayit ekleyip kapiyi kandirma.)
    🔴 HAM METIN TARANMAZ (KraL tur-7): 'kaynaklar' altindaki bir URL'de "pc" gecmesi
    ihlal DEGILDIR — ihlal, PC'yi bir KAYIT olarak envantere sokmaktir. Dayanak
    kayitlari da taranir: {"ad":"PC","satista":false} ile susturma YINE KIRMIZI."""
    bulunan = {}
    for kayit in list(veri.get("filamentler", [])) + list(veri.get(DAYANAK_ANAHTARI, [])):
        for alan in ENVANTER_OKUNAN_ALANLAR:
            for kisa, _ek, ham in adaylari_bul(str(kayit.get(alan, ""))):
                if kisa in KARA_LISTE:
                    bulunan.setdefault(kisa, set()).add(ham)
    return bulunan


# ------------------------------------------------------------ IC NOBETCI (fikstur)
# 🔴 IC NOBETCI KAPSAMI KODDA KILITLI (KraL tur-5). Onceden fikstur sayisi YALNIZ
# docstring'de yaziyordu -> F16 blogunu silen tek mutasyon kapiyi 29 kontrolle YESIL
# birakiyordu. Fikstur F0-kapsam bu iki sabiti her kosumda dogrular; yeni fikstur
# eklemek BILINCLI bir hareket olsun diye ikisi de ELLE guncellenir.
BEKLENEN_FIKSTUR_ADLARI = frozenset({
    "F0-kapsam", "F1", "F2", "F3", "F4",
    "F5a", "F5b", "F6", "F7", "F8", "F8-pozitif", "F9",
    "F10a", "F10b", "F10c", "F11a", "F11b", "F11c", "F12a", "F12b", "F12c",
    "F13a", "F13b", "F14", "F15",
    "F16a", "F16b", "F16c", "F16d", "F16e", "F17",
    "F18a", "F18b", "F18c",
    "F19a", "F19b", "F20a", "F20b", "F20c", "F20d", "F21a", "F21b",
})
BEKLENEN_KONTROL_SAYISI = 49  # F8 7 kez, F9 2 kez kosar -> ad sayisindan buyuk


# 🔴 FIKSTUR SIMETRISI — SINIF olarak kapali (KraL tur-6). Onceki turda yalniz "uzunAd"
# ornegi kapatilmisti; gercek filamentler.json kayitlari ayrica kisa/uzun/isiDetay/
# kisaEtiket/isiDayanimi/uv/su/darbe TASIR ve ust duzeyde _aciklama / kategoriTavsiye /
# kaynaklar vardir. Fiksturler yalniz {"ad": ...} tasidigi surece "aciklama metninden de
# besle" mutasyonu fiksturde HICBIR SEY DEGISTIRMEZ -> YESIL gecer ve SART-1 + SART-2'yi
# geri alir (olculdu). Asagidaki alanlar GERCEK KAYIT SETIYLE ayni; aciklama alanlari
# BILEREK yabanci polimer adi tasir (POM/PC/PEEK/PA6-GF) — beyaz liste delinirse
# F19 + F4 + F10b + F16c + F17 ANINDA KIRMIZI yanar.
_F_ACIKLAMA_JETONLARI = ("POM", "PC", "PEEK", "PA6-GF")
_F_KARDES_ANAHTARLAR = {
    "olcut": "ısı dayanımı (HDT @ 0.45 MPa)",
    "kaynaklar": ["https://ornek.invalid/POM-PEEK-PC"],
    "_aciklama": "Fikstur ust duzey aciklamasi: POM, PC ve PEEK adlari BILEREK gecer; "
                 "envanteri_coz bu anahtari OKUMAZ.",
    "kategoriTavsiye": {"Otomobil": [{"ad": "PEEK"}, {"ad": "POM"}]},
}


def _f_kayit(ad, **fazladan):
    """GERCEK filamentler.json satis kaydiyla AYNI ALAN SETINI tasiyan fikstur kaydi.
    Beyaz liste disindaki alanlar yabanci polimer adi tasir (bkz. _F_ACIKLAMA_JETONLARI)."""
    kayit = {
        "ad": ad,
        "site": True,
        "kisaEtiket": "fikstur etiketi",
        "isiDayanimi": "~55-60°C",
        "uv": "Düşük", "su": "Düşük", "darbe": "Düşük-orta",
        "kisa": "Fikstur kisa metni: POM ile de üretiyoruz.",
        "uzun": "Fikstur uzun metni: PC ve PEEK ile üretip gönderiyoruz.",
        "isiDetay": "PA6-GF ~120°C; tasiyicisi guclu turler daha yuksek",
    }
    kayit.update(fazladan)
    return kayit


def _f_envanter(veri=None):
    """Fikstur envanteri — GERCEK dosyayla SIMETRIK (kayit alan seti + kardes anahtarlar)."""
    veri = dict(veri or {"filamentler": [_f_kayit("PLA"), _f_kayit("PETG")]})
    for anahtar, deger in _F_KARDES_ANAHTARLAR.items():
        veri.setdefault(anahtar, deger)
    return envanteri_coz(veri)


def ic_nobetci():
    """Kapinin KENDI yeteneklerini bellekte-fikstur ile kilitler.
    -> (hata listesi, kosulan kontrol sayisi). Dosyaya BAKMAZ, dosyaya YAZMAZ."""
    hata = []
    sayac = [0]
    kosulan = []

    def kontrol(ad, kosul, ayrinti=""):
        sayac[0] += 1
        kosulan.append(ad)
        if not kosul:
            hata.append("%s %s" % (ad, ayrinti))

    # F1 — KARA LISTE ENVANTERI EZER (envantere kayit ekleyip susturma deligi)
    env = _f_envanter({"filamentler": [_f_kayit("PLA"), _f_kayit("PC")]})
    _o, dayanaksiz, kara, _e = degerlendir(
        [("fikstur", "F1", "Talep ederseniz PC ile üretip gönderiyoruz.")], env)
    kontrol("F1", "PC" in kara and "PC" not in dayanaksiz,
            "envanterde PC kaydi varken kara liste ihlali YAKALANMADI "
            "(kara=%s dayanaksiz=%s)" % (sorted(kara), sorted(dayanaksiz)))

    # F2/F3 — KARA LISTE envanter KAYITLARINDA (ad/uzunAd) yakalanir; ham metin TARANMAZ
    # (tur-7): 'kaynaklar' URL'sinde "pc" gecmesi ihlal degildir, kayit olarak sokmak ihlaldir.
    kontrol("F2", "PC" in kara_liste_envanterde({"filamentler": [{"ad": "PC"}]})
            and "PC" in kara_liste_envanterde(
                {"filamentler": [{"ad": "X", "uzunAd": "Polikarbonat (PC)"}]})
            and "PC" in kara_liste_envanterde(
                {"filamentler": [], DAYANAK_ANAHTARI: [{"ad": "PC"}]}),
            "envanter kaydinin ad/uzunAd alanindaki PC yakalanmadi (dayanak dahil)")
    kontrol("F3", not kara_liste_envanterde(
                {"filamentler": [{"ad": "PETG"}],
                 "kaynaklar": ["https://ornek.invalid/pc-malzeme-rehberi"]}),
            "kayit-disi ham metin ('kaynaklar' URL'sindeki 'pc') yanlis-pozitif yakti")

    # F4 — NEGATIF BAGLAM ELEYICISI YOK (curutucunun kacirdigi gercek vaka)
    env = _f_envanter()
    _o, dayanaksiz, kara, _e = degerlendir(
        [("fikstur", "F4",
          "- PC ile üretim yok; ama isterse müşteriye PEEK ile üretip gönderiyoruz.")],
        env)
    kontrol("F4", "PC" in kara and "PEEK" in dayanaksiz,
            "olumsuzlama iceren satirdaki vaat KACTI (negatif eleyici geri gelmis olabilir) "
            "kara=%s dayanaksiz=%s" % (sorted(kara), sorted(dayanaksiz)))

    # F14 — TAM AD haritasi: Turkce tam ad da malzeme beyanidir ("polikarbonat" -> PC)
    _o, d14, k14, _e = degerlendir(
        [("fikstur", "F14a", "İhtiyaç halinde polikarbonat ile üretiyoruz.")], env)
    _o, d14b, _k, _e = degerlendir(
        [("fikstur", "F14b", "Poliasetal ile de üretiyoruz.")], env)
    kontrol("F14", "PC" in k14 and not d14 and "POM" in d14b,
            "tam ad haritasi bozuk (polikarbonat->%s/%s · poliasetal->%s)"
            % (sorted(k14), sorted(d14), sorted(d14b)))

    # F5 — JSON-LD taramasi: ad YALNIZ acceptedAnswer icinde olsa da bulunur
    html = ('<html><body><p>temiz gorunur metin</p>'
            '<script type="application/ld+json">'
            '{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"soru",'
            '"acceptedAnswer":{"@type":"Answer","text":"POM ve PEEK ile üretiyoruz."}}]}'
            '</script></body></html>')
    bloklar, metinler = jsonld_metinleri(html)
    kontrol("F5a", len(bloklar) == 1 and any("PEEK" in m for m in metinler),
            "JSON-LD string degerleri ayiklanmadi (metin=%r)" % metinler)
    _o, dayanaksiz, _k, _e = degerlendir(
        [("statik-jsonld", "F5", " . ".join(metinler))], env)
    kontrol("F5b", "PEEK" in dayanaksiz and "POM" in dayanaksiz,
            "JSON-LD icindeki dayanaksiz ad yakalanmadi (%s)" % sorted(dayanaksiz))

    # F6 — bozuk JSON-LD fail-closed + hata mesaji SLUG'i SOYLER (SART-3)
    # Bu kapi CI'da tum ekibin yayinini durdurur; "hangi sayfa" bilgisi olmadan
    # mesaj 4 sayfa arasinda arama yaptirir.
    try:
        jsonld_metinleri('<script type="application/ld+json">{bozuk</script>',
                         "sss · /repo/sss/index.html")
        kontrol("F6", False, "bozuk JSON-LD sessizce gecti (fail-closed degil)")
    except ValueError as e:
        kontrol("F6", "sss" in str(e) and "/repo/sss/index.html" in str(e),
                "JSON-LD hata mesajinda slug/dosya YOK: %s" % e)

    # F7 — URUN/SISTEM eleyicisi: yanlis-pozitif yok ama vaat KACMIYOR
    _o, d1, _k, _e = degerlendir([("fikstur", "F7a", "PVC doğrama profili takarız.")],
                                 env)
    _o, d2, _k, _e = degerlendir([("fikstur", "F7b", "PVC ile üretim yapıyoruz.")],
                                 env)
    kontrol("F7", not d1 and "PVC" in d2,
            "urun/sistem eleyicisi bozuk (dograma=%s vaat=%s)" % (sorted(d1), sorted(d2)))

    # F8 — dayanak kaydi sizinti kapisi (negatif + pozitif)
    for kotu, neden in [
            ({"ad": "POM", "tedarik": "x"}, "satista alani yok"),
            ({"ad": "POM", "satista": True, "tedarik": "x"}, "satista true"),
            ({"ad": "POM", "satista": False}, "tedarik yok"),
            ({"ad": "POM", "satista": False, "tedarik": "x", "fiyat": "1 TL"}, "fiyat alani"),
            ({"ad": "POM", "satista": False, "tedarik": "x", "katsayi": 1.2}, "katsayi alani"),
            ({"ad": "POM", "satista": False, "tedarik": "x", "site": True}, "site alani"),
            ({"satista": False, "tedarik": "x"}, "ad yok")]:
        try:
            dayanak_dogrula([kotu])
            kontrol("F8", False, "dayanak kaydi REDDEDILMEDI (%s): %r" % (neden, kotu))
        except ValueError:
            kontrol("F8", True)
    try:
        dayanak_dogrula([{"ad": "POM", "satista": False, "tedarik": "siparis uzerine"}])
        kontrol("F8-pozitif", True)
    except ValueError as e:
        kontrol("F8-pozitif", False, "gecerli dayanak kaydi reddedildi: %s" % e)

    # F9 — envanter fail-closed
    for kotu, neden in [({"filamentler": []}, "bos liste"),
                        ({"filamentler": [{"ad": "PLA"}], DAYANAK_ANAHTARI: {}},
                         "dayanak liste degil")]:
        try:
            envanteri_coz(kotu)
            kontrol("F9", False, "bozuk envanter kabul edildi (%s)" % neden)
        except (ValueError, KeyError):
            kontrol("F9", True)

    # F10 — 🔴 SART-1 KILIDI (karar kaydi: DAYANAK_KARAR_KAYDI)
    # Dayanak kaydi YALNIZ kendi TAM ADINI mesrulastirir; kuresel taban/ek kumelerine
    # DOKULMEZ. Onceki tur bunu ihlal ediyordu (PA6-GF kaydi ciplak PA6 tabanini ve
    # kuresel GF ekini aciyordu) -> onaylanmamis PA-GF sinifi sessizce dayanakli oldu.
    #
    # 🔴 FIKSTUR GERCEK VERIYLE SIMETRIK OLMALI (KraL tur-5, "ayni sinif kalinti"):
    # gercek filamentler.json'daki _dayanakMalzemeler kayitlarinin UCUNDE DE "uzunAd"
    # alani VAR. Fikstur kayitlarinda yoksa, envanteri_coz'a "dayanak uzunAd'ini da
    # kuresel taban/ek kumesine dok" diyen 6 satirlik bir "simetri" refactor'u fiksturde
    # HICBIR SEY DEGISTIRMEZ -> 34/34 YESIL gecer ve SART-1 ile SART-2'yi AYNI ANDA geri
    # alir (ciplak "PA6 ile uretiyoruz" KIRMIZI'dan YESIL'e doner). uzunAd bu yuzden
    # gercek veriyle AYNI SEKILDE fikstureledir; F10b/F10c o refactor'u ANINDA oldurur.
    env10 = _f_envanter(
        {"filamentler": [_f_kayit("PLA"), _f_kayit("PETG")],
         DAYANAK_ANAHTARI: [{"ad": "PA6-GF",
                             "uzunAd": "Cam elyaf takviyeli naylon (PA6-GF)",
                             "satista": False, "tedarik": "siparis uzerine"},
                            {"ad": "POM", "uzunAd": "Poliasetal (POM)",
                             "satista": False, "tedarik": "siparis uzerine"}]})
    kontrol("F10a", env10.dayanak_tam == {"PA6-GF", "POM"}
            and env10.dayanak_adlar == ["PA6-GF", "POM"],
            "dayanak TAM AD kumesi yanlis: %s" % sorted(env10.dayanak_tam))
    kontrol("F10b", "PA6" not in env10.taban and "GF" not in env10.ekler
            and "POM" not in env10.taban,
            "🔴 SART-1 IHLALI: dayanak kaydi (ad/uzunAd) kuresel taban/ek kumesine "
            "DOKULDU (taban=%s ek=%s) — 'simetri' refactor'u ciplak PA6'yi ve kuresel "
            "GF ekini ACAR" % (sorted(env10.taban), sorted(env10.ekler)))
    # F10c — uzunAd'daki TURKCE tam ad da sizmamali: "Cam elyaf takviyeli naylon (PA6-GF)"
    # icindeki "naylon" ciplak PA'yi mesrulastirmaya kalkarsa vaat sessizce YESIL yanar.
    _o, d10c, _k, _e = degerlendir(
        [("fikstur", "F10c", "Naylon ile üretip gönderiyoruz.")], env10)
    kontrol("F10c", d10c.get("PA"),
            "dayanak uzunAd'indaki Turkce ad ('naylon') ciplak PA'yi MESRULASTIRDI: %s"
            % sorted(d10c))

    # F16 — SART-1'in DAVRANIS kilidi: 5 fikstur, beklenen/gercek
    #   "PA6-CF"  -> KIRMIZI (onaylanmayan takviye; ciplak PA6 tabani acilmadi)
    #   ciplak PA6-> KIRMIZI (tam ad degil)
    #   "PETG-GF" -> UYARI   (kuresel GF eki acilmadi -> SESSIZLESMEZ)
    #   "PA6-GF"  -> TEMIZ   (onayli tam ad)
    #   "PA6+GF"  -> TEMIZ   (yayindaki gercek yazim; ayrac farki dayanagi bozmaz)
    def _f16(metin):
        _oz, dsz, kra, eku = degerlendir([("fikstur", "F16", metin)], env10)
        return sorted(dsz), sorted(kra), sorted(eku)
    d_cf, _k, _e = _f16("PA6-CF ile üretiyoruz.")
    d_ciplak, _k, _e = _f16("PA6 ile üretiyoruz.")
    d_petg, _k, e_petg = _f16("PETG-GF ile üretiyoruz.")
    d_gf, _k, e_gf = _f16("PA6-GF ile üretiyoruz.")
    d_arti, _k, e_arti = _f16("PA6+GF ile üretiyoruz.")
    kontrol("F16a", d_cf == ["PA6"], "PA6-CF KIRMIZI degil: %s" % d_cf)
    kontrol("F16b", d_ciplak == ["PA6"], "ciplak PA6 KIRMIZI degil: %s" % d_ciplak)
    kontrol("F16c", not d_petg and e_petg == [("PETG", "GF")],
            "PETG-GF SESSIZLESTI (kuresel GF eki acilmis olabilir): dayanaksiz=%s uyari=%s"
            % (d_petg, e_petg))
    kontrol("F16d", not d_gf and not e_gf,
            "onayli TAM AD PA6-GF gereksiz yere isaretlendi: dayanaksiz=%s uyari=%s"
            % (d_gf, e_gf))
    kontrol("F16e", not d_arti and not e_arti,
            "yayindaki yazim PA6+GF onayli tam adla eslesmedi: dayanaksiz=%s uyari=%s"
            % (d_arti, e_arti))

    # F17 — SART-2 kilidi: bir dayanak TAM ADI (PA6-GF) BASKA bir tabanin ayni ekini
    # (PA-GF) SESSIZCE mesrulastiramaz. Gercek vaka: main 77 landing govdesinde
    # "UYARI: PA-GF ... - 77 sayfa" basiyordu; onceki turda bu uyari SESSIZCE kayboldu.
    # (Dayanak kaydi burada da gercek veriyle SIMETRIK — "uzunAd" alani VAR; bkz. F10.)
    envPA = _f_envanter(
        {"filamentler": [_f_kayit("PLA"),
                         _f_kayit("Karbon Katkılı",
                                  uzunAd="Karbon katkılı (PETG-CF/PA-CF)")],
         DAYANAK_ANAHTARI: [{"ad": "PA6-GF",
                             "uzunAd": "Cam elyaf takviyeli naylon (PA6-GF)",
                             "satista": False, "tedarik": "siparis uzerine"}]})
    _o, d17, _k, e17 = degerlendir(
        [("landing", "F17", "cam fiber takviyeli PA-CF / PA-GF kullanırız.")], envPA)
    kontrol("F17", e17.get(("PA", "GF")) and not d17 and not e17.get(("PA", "CF")),
            "SART-2: PA-GF uyarisi SESSIZLESTI (dayanaksiz=%s uyari=%s)"
            % (sorted(d17), sorted(e17)))

    # F11 — drift karsilastirmasi (ozdes / farkli / isaretcisiz)
    kontrol("F11a", blok_karsilastir("<A>x<B>", "once <A>x<B> sonra", "<A>", "<B>")[0],
            "ozdes blok DRIFT sayildi")
    kontrol("F11b", not blok_karsilastir("<A>y<B>", "once <A>x<B> sonra", "<A>", "<B>")[0],
            "farkli blok drift SAYILMADI")
    kontrol("F11c", not blok_karsilastir("<A>x<B>", "isaretcisiz metin", "<A>", "<B>")[0],
            "isaretci yoklugu drift SAYILMADI")

    # F13 — SIZINTI dedektoru gercekten atesliyor (ve temizde yanlis-pozitif yok)
    adlar13 = ["PA6-GF", "PA12-GF", "POM"]
    kontrol("F13a", dayanak_taban_jetonlari(adlar13) == {"PA6", "PA12", "POM"},
            "dayanak taban jetonu turetilemedi: %s" % dayanak_taban_jetonlari(adlar13))
    kirli = dayanak_sizintisi(adlar13, [("sahte cikti", "Ürün POM ile üretilir.")])
    temiz = dayanak_sizintisi(adlar13, [("sahte cikti", "Ürün PETG ile üretilir.")])
    anahtar = dayanak_sizintisi(adlar13, [("sahte cikti", '{"%s":[]}' % DAYANAK_ANAHTARI)])
    kontrol("F13b", kirli and not temiz and anahtar,
            "sizinti dedektoru bozuk (kirli=%s temiz=%s anahtar=%s)"
            % (kirli, temiz, anahtar))

    # F15 — BUYUK-HARF sarti duruyor (yanlis-pozitif kapisi) AMA kara listede
    #       buyuk/kucuk harf ayrimi YOK (en yuksek bahisli kural kacmasin)
    _o, d15a, k15a, _e = degerlendir(
        [("fikstur", "F15a", "Müşteri pet şişe kapağı için parça istedi.")], env)
    _o, d15b, _k, _e = degerlendir(
        [("fikstur", "F15b", "PET esaslı malzemeyle üretiyoruz.")], env)
    _o, _d, k15c, _e = degerlendir(
        [("fikstur", "F15c", "İsterseniz pc ile de üretiyoruz.")], env)
    kontrol("F15", not d15a and not k15a and "PET" in d15b and "PC" in k15c,
            "buyuk-harf sarti / kara liste harf duyarsizligi bozuk "
            "(kucuk pet=%s · buyuk PET=%s · kucuk pc kara=%s)"
            % (sorted(d15a), sorted(d15b), sorted(k15c)))

    # F12 — kapsam nobeti VARLIK KONTROLU olarak kilitli (tur-7): sayi/karakter tabani
    # geri getiren ya da zorunlu kaynak listesini kirpan mutasyon burada olur.
    kontrol("F12a", ZORUNLU_KAYNAKLAR == ("landing", "ege-bilgi.md", "statik-gorunur"),
            "ZORUNLU_KAYNAKLAR kirpilmis/degismis: %r" % (ZORUNLU_KAYNAKLAR,))
    # F12b — JSON-LD kaybi UYARI kalmali (KIRMIZI degil): FAQPage blogunu kaldirmak
    # mesru SEO karari. BEKLENEN listesi de sessizce bosaltilamaz (uyari susardi).
    kontrol("F12b", BEKLENEN_JSONLD == ("sss", "iletisim")
            and "statik-jsonld" not in ZORUNLU_KAYNAKLAR,
            "JSON-LD kapsami bozuk (BEKLENEN listesi degismis ya da statik-jsonld "
            "zorunlu yapilmis): BEKLENEN_JSONLD=%r ZORUNLU_KAYNAKLAR=%r"
            % (BEKLENEN_JSONLD, ZORUNLU_KAYNAKLAR))
    # F12c — SIZINTI kapsami da SAYI DEGIL AD BAZLI kalmali (KraL tur-6). Zorunlu kume
    # yalniz KOD TARAFINDAN URETILEN iki degismez ciktidir; landing kaynakli
    # /malzeme-rehberi/ ZORUNLU YAPILAMAZ (mesru slug degisimi tum ekibin yayinini
    # durdururdu) ama BEKLENEN kumeden de CIKARILAMAZ (uyari susardi).
    kontrol("F12c",
            tuple(ZORUNLU_SIZINTI_CIKTILARI) == (SIZINTI_CIKTI_FILAMENT_JS,
                                                 SIZINTI_CIKTI_EGE_BLOK)
            and SIZINTI_CIKTI_MALZEME_REHBERI not in ZORUNLU_SIZINTI_CIKTILARI
            and SIZINTI_CIKTI_MALZEME_REHBERI in BEKLENEN_SIZINTI_CIKTILARI
            and set(ZORUNLU_SIZINTI_CIKTILARI) <= set(BEKLENEN_SIZINTI_CIKTILARI),
            "sizinti kapsam kumesi bozuk (zorunlu gevsemis / landing ciktisi zorunlu "
            "yapilmis / beklenen kumeden dusmus): ZORUNLU=%r BEKLENEN=%r"
            % (ZORUNLU_SIZINTI_CIKTILARI, BEKLENEN_SIZINTI_CIKTILARI))

    # F18 — DRIFT nobeti UCTAN UCA (KraL tur-5 eki).
    # Bugune kadar YALNIZ karsilastirici (blok_karsilastir, F11) fikstureleniyordu;
    # drift_kontrolu'nun KENDISI — modul yukleme + bolum_uret() cagrisi + dosya okuma —
    # hicbir nobetciyle kilitli DEGILDI. Tek satirlik bir mutasyon (or. "uretilen = icerik"
    # ya da "return True, ...") bayat ege-bilgi.md'yi YESIL yakar -> Ege SESSIZCE bayatlar
    # (site gosterir, bot eski malzeme listesini anlatir).
    # Gecici dizinde SAHTE ege-malzeme.py + SAHTE ege-bilgi.md; GERCEK dosyalara DOKUNMAZ.
    sahte_modul = ("BASLA = '<!-- A -->'\n"
                   "BITIR = '<!-- B -->'\n"
                   "def bolum_uret():\n"
                   "    return BASLA + '\\nPLA / PETG\\n' + BITIR\n")
    with tempfile.TemporaryDirectory() as gecici:
        py_yol = os.path.join(gecici, "sahte-ege-malzeme.py")
        md_taze = os.path.join(gecici, "taze-ege-bilgi.md")
        md_bayat = os.path.join(gecici, "bayat-ege-bilgi.md")
        with io.open(py_yol, "w", encoding="utf-8") as f:
            f.write(sahte_modul)
        with io.open(md_taze, "w", encoding="utf-8") as f:
            f.write("giris\n<!-- A -->\nPLA / PETG\n<!-- B -->\nson\n")
        with io.open(md_bayat, "w", encoding="utf-8") as f:
            f.write("giris\n<!-- A -->\nPLA / ABS\n<!-- B -->\nson\n")
        t_taze, m_taze, blok_taze = drift_kontrolu(md_taze, py_yol)
        t_bayat, m_bayat, _b = drift_kontrolu(md_bayat, py_yol)
        t_dosyasiz, m_dosyasiz, _b = drift_kontrolu(
            os.path.join(gecici, "olmayan.md"), py_yol)
        t_modulsuz, m_modulsuz, _b = drift_kontrolu(
            md_taze, os.path.join(gecici, "olmayan.py"))
    kontrol("F18a", t_taze and blok_taze == "<!-- A -->\nPLA / PETG\n<!-- B -->",
            "uctan uca drift: TAZE blok drift sayildi ya da uretilen blok dondurulmedi "
            "(%s | blok=%r)" % (m_taze, blok_taze))
    kontrol("F18b", not t_bayat and "BAYAT" in m_bayat,
            "uctan uca drift: BAYAT ege-bilgi.md YESIL yandi (%s)" % m_bayat)
    kontrol("F18c", not t_dosyasiz and not t_modulsuz,
            "uctan uca drift FAIL-CLOSED degil (md yok -> %s · ege-malzeme.py yok -> %s)"
            % (m_dosyasiz, m_modulsuz))

    # F19 — 🔴 ENVANTER BEYAZ LISTESI (KraL tur-6; "aciklama metninden besleme" SINIFI).
    # F19a sabiti, F19b DAVRANISI kilitler: beyaz listeyi delen bir mutasyon (or.
    # kayit.get("kisa") / "uzun" / "isiDetay" eklemek, ya da json.dumps(veri) taramak)
    # fikstur kayitlarinda ARTIK bir sey DEGISTIRIR, cunku fiksturler gercek kayit alan
    # setini tasir (bkz. _f_kayit). Eskiden fiksturler yalniz {"ad": ...} tasidigi icin
    # ayni mutasyon 40/40 YESIL geciyordu.
    kontrol("F19a", tuple(ENVANTER_OKUNAN_ALANLAR) == ("ad", "uzunAd"),
            "envanter BEYAZ LISTESI degismis/gevsetilmis: %r"
            % (ENVANTER_OKUNAN_ALANLAR,))
    env19 = _f_envanter()
    kacak19 = sorted((set(env19.tam) | set(env19.taban) | set(env19.ekler))
                     & set(_F_ACIKLAMA_JETONLARI + ("GF", "PA6")))
    kontrol("F19b", not kacak19,
            "🔴 BEYAZ LISTE DELINDI: aciklama alanlarindaki yabanci jetonlar kuresel "
            "kumeye SIZDI (%s) — tam=%s taban=%s ek=%s"
            % (kacak19, sorted(env19.tam), sorted(env19.taban), sorted(env19.ekler)))

    # F20 — 🔴 SIZINTI KAPSAM NOBETI DAVRANISI (KraL tur-6). Eski "cikti sayisi >= 3"
    # SAYI TABANI, /malzeme-rehberi/ slug'i degisince YANLIS-POZITIF veriyordu; yeni
    # kural VARLIK modeliyle ayni bicimde AD BAZLIDIR. Bu fikstur hem yanlis-pozitifin
    # geri gelmedigini (F20b) hem de kapinin gercekten bir sey ISTEDIGINI (F20c/F20d)
    # kanitlar; "uretimler listesini kirp" mutasyonu buradan gecemez.
    h20a, u20a = sizinti_kapsam(BEKLENEN_SIZINTI_CIKTILARI)
    kontrol("F20a", not h20a and not u20a,
            "tam kapsamda yanlis-pozitif (hata=%s uyari=%s)" % (h20a, u20a))
    h20b, u20b = sizinti_kapsam(ZORUNLU_SIZINTI_CIKTILARI)
    kontrol("F20b", not h20b and len(u20b) == 1
            and SIZINTI_CIKTI_MALZEME_REHBERI in u20b[0],
            "landing ciktisi (/malzeme-rehberi/) yoklugu BLOKLADI ya da SESSIZ kaldi — "
            "reddedilen SAYI TABANI deseni geri gelmis olabilir (hata=%s uyari=%s)"
            % (h20b, u20b))
    h20c, _u = sizinti_kapsam([SIZINTI_CIKTI_EGE_BLOK, SIZINTI_CIKTI_MALZEME_REHBERI])
    h20d, _u = sizinti_kapsam([SIZINTI_CIKTI_FILAMENT_JS, SIZINTI_CIKTI_MALZEME_REHBERI])
    kontrol("F20c", len(h20c) == 1 and SIZINTI_CIKTI_FILAMENT_JS in h20c[0],
            "filament-veri.js govdesi taranmadigi halde KIRMIZI yanmadi: %s" % h20c)
    kontrol("F20d", len(h20d) == 1 and SIZINTI_CIKTI_EGE_BLOK in h20d[0],
            "ege-malzeme blogu taranmadigi halde KIRMIZI yanmadi: %s" % h20d)

    # F21 — 🔴 SART-2 UYARISININ RAPORU (KraL tur-6). Iddia edilen "F17 bunu KIRMIZI
    # yakar" korumasi OLCULEREK YANLISLANDI: raporu susturan mutasyon 40/40 geciyordu.
    # Artik uretilen SATIR METNI fikstureli.
    s21 = ek_uyari_satirlari({("PA", "GF"): ["landing/a", "landing/b", "landing/a"]})
    kontrol("F21a", any(s.startswith("UYARI: PA-GF") and "2 govde / 3 eslesme" in s
                        for s in s21)
            and any("bloklamaz" in s for s in s21),
            "SART-2 UYARI RAPORU susturulmus/bozulmus: %r" % (s21,))
    kontrol("F21b", ek_uyari_satirlari({}) == ["UYARI yok: adlandirilmamis takviye eki "
                                               "gecmiyor"],
            "bos uyari halinde 'UYARI yok' satiri uretilmedi: %r"
            % (ek_uyari_satirlari({}),))

    # F0 — 🔴 IC NOBETCININ KENDI KAPSAM KILIDI (KraL tur-5 eki).
    # Fikstur sayisi/ad kumesi bugune kadar YALNIZ docstring'de yaziyordu: F16 blogunu
    # silen TEK mutasyon kapiyi 29 kontrolle YESIL birakiyordu (kimse sayiya bakmaz).
    # Artik ad kumesi + sayi KODDA kilitli; bir fikstur blogunu silen/susturan mutasyon
    # burada KIRMIZI yanar.
    calisan = set(kosulan) | {"F0-kapsam"}
    eksik = sorted(BEKLENEN_FIKSTUR_ADLARI - calisan)
    fazla = sorted(calisan - BEKLENEN_FIKSTUR_ADLARI)
    kontrol("F0-kapsam",
            not eksik and not fazla and sayac[0] + 1 == BEKLENEN_KONTROL_SAYISI,
            "IC NOBETCI KAPSAMI DEGISTI — eksik fikstur=%s · fazla=%s · kontrol=%d "
            "(beklenen %d). Bir fikstur blogu silinmis/susturulmus olabilir; yeni fikstur "
            "eklediysen BEKLENEN_FIKSTUR_ADLARI + BEKLENEN_KONTROL_SAYISI'ni BILEREK guncelle."
            % (eksik, fazla, sayac[0] + 1, BEKLENEN_KONTROL_SAYISI))
    return hata, sayac[0]


# ------------------------------------------------- DAVRANIS NOBETCISI (main uctan uca)
# 🔴 KABLO NOBETI (KraL tur-7). Ic nobetci fonksiyonlari TEK TEK kilitler ama onlari
# EXIT KODUNA/RAPORA baglayan kablolar nobetsizdi — OLCULDU: "kapsam_hata.extend(s_hata)"
# -> "extend([])" TEK JETON mutasyonu 49/49 fiksturu YESIL birakiyordu. Bu nobetci
# main()'i gecici dizinde sahte veri setiyle UCTAN UCA kosturur (stdout + exit kodu
# yakalar); GERCEK dosyalara DOKUNMAZ. Ozyineleme main(..., davranis=False) ile kesilir.
BEKLENEN_DAVRANIS_ADLARI = frozenset(
    {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"})

_D_MODUL_TEMIZ = ("BASLA = '<!-- FILAMENT-REF -->'\n"
                  "BITIR = '<!-- /FILAMENT-REF -->'\n"
                  "def bolum_uret():\n"
                  "    return BASLA + '\\nPLA / PETG\\n' + BITIR\n")
# D3: bolum_uret() patlar -> drift KIRMIZI + ege_blok None -> ZORUNLU sizinti ciktisi
# 'ege-malzeme.py uretilen blok' taranamaz -> sizinti_kapsam hata dondurmek ZORUNDA.
_D_MODUL_BOZUK = _D_MODUL_TEMIZ.replace(
    "    return BASLA + '\\nPLA / PETG\\n' + BITIR",
    "    raise RuntimeError('blok uretilemedi')")


def _d_yaz(yol, icerik):
    with io.open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)


def _d_kurulum(gecici, filament=None, sss_govde="", modul=_D_MODUL_TEMIZ):
    """Gecici dizinde sahte veri seti kurar -> main() argv listesi (landing KAPALI;
    landing'i acmak isteyen fikstur son elemani atar). sss'te JSON-LD BILEREK YOK
    (FAQPage'i kaldirmak mesru — D1 bunun YESIL kaldigini kanitlar)."""
    filament = filament or {
        "filamentler": [{"ad": "PLA"}, {"ad": "PETG"}],
        # M4a kaniti: kayit-DISI ham metinde ("kaynaklar" URL'si) 'pc' gecmesi ihlal degil
        "kaynaklar": ["https://ornek.invalid/pc-malzeme-rehberi"],
    }
    _d_yaz(os.path.join(gecici, "filamentler.json"),
           json.dumps(filament, ensure_ascii=False))
    _d_yaz(os.path.join(gecici, "ege-malzeme.py"), modul)
    _d_yaz(os.path.join(gecici, "ege-bilgi.md"),
           "giris\n<!-- FILAMENT-REF -->\nPLA / PETG\n<!-- /FILAMENT-REF -->\nson\n")
    for slug in STATIK_SAYFALAR:
        os.makedirs(os.path.join(gecici, slug))
        govde = sss_govde if slug == "sss" else ""
        _d_yaz(os.path.join(gecici, slug, "index.html"),
               "<html><body><p>PLA ve PETG ile uretim. %s</p></body></html>" % govde)
    return ["--filament", os.path.join(gecici, "filamentler.json"),
            "--ege", os.path.join(gecici, "ege-bilgi.md"),
            "--ege-malzeme", os.path.join(gecici, "ege-malzeme.py"),
            "--statik-kok", gecici, "--landing-kapali"]


def _d_kostur(argv):
    """main()'i UCTAN UCA kosturur -> (exit_kodu, stdout metni)."""
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        kod = main(argv, davranis=False)
    return kod, tampon.getvalue()


def davranis_nobetci():
    """main()'i uctan uca kosturan davranis fiksturleri -> (hata listesi, fikstur sayisi)."""
    hata = []
    kosulan = []

    def kontrol(ad, kosul, ayrinti=""):
        kosulan.append(ad)
        if not kosul:
            hata.append("%s %s" % (ad, ayrinti))

    with tempfile.TemporaryDirectory() as gecici:
        # D1 — TEMIZ kurulum YESIL + iki YANLIS-POZITIF SINIFI kapali: sss JSON-LD'siz
        # (sart-2/M2) ve 'kaynaklar' URL'sinde 'pc' (sart-4/M4a). JSON-LD yoklugu UYARI
        # basmali (sessizlesmez) ama bloklamamali.
        d1 = os.path.join(gecici, "d1")
        os.makedirs(d1)
        kod, cikti = _d_kostur(_d_kurulum(d1))
        kontrol("D1", kod == 0 and "SONUC: YESIL" in cikti and "UYARI: KAPSAM" in cikti,
                "temiz kurulum YESIL degil ya da JSON-LD yoklugu UYARI basmadi "
                "(kod=%d, son satirlar: %r)"
                % (kod, cikti.strip().splitlines()[-4:]))

        # D2 — dayanaksiz vaat KIRMIZI (degerlendir -> exit kablosu)
        d2 = os.path.join(gecici, "d2")
        os.makedirs(d2)
        kod, cikti = _d_kostur(_d_kurulum(
            d2, sss_govde="PEEK ile üretip gönderiyoruz."))
        kontrol("D2", kod == 1 and "'PEEK' filamentler.json envanterinde YOK" in cikti,
                "dayanaksiz vaat (PEEK) EXIT=1 + KIRMIZI rapor uretmedi (kod=%d)" % kod)

        # D3 — 🔴 M1 KABLOSU: ZORUNLU sizinti ciktisi eksikken kapsam hatasi RAPORA/EXIT'e
        # ULASMALI. "extend([])" mutasyonu tam bu satiri yutar; iddia SPESIFIK KAPSAM
        # satirindadir (drift ayrica KIRMIZI olur, exit tek basina ayirt etmez).
        d3 = os.path.join(gecici, "d3")
        os.makedirs(d3)
        kod, cikti = _d_kostur(_d_kurulum(
            d3, modul=_D_MODUL_BOZUK,
            filament={"filamentler": [{"ad": "PLA"}, {"ad": "PETG"}],
                      DAYANAK_ANAHTARI: [{"ad": "POM", "satista": False,
                                          "tedarik": "siparis uzerine"}]}))
        kontrol("D3", kod == 1 and "ZORUNLU sizinti ciktisi" in cikti
                and ("KIRMIZI: KAPSAM - ZORUNLU sizinti ciktisi '%s'"
                     % SIZINTI_CIKTI_EGE_BLOK) in cikti,
                "ZORUNLU sizinti ciktisi eksikken KAPSAM hatasi rapora ULASMADI (kod=%d) "
                "— 'kapsam_hata.extend(s_hata)' kablosu kopmus olabilir" % kod)

        # D4 — VARLIK KONTROLU davranisi (sart-3/M3): landing kaynagi hic govde uretmezse
        # KIRMIZI. sayfalar.CONTENT_PAGES gecici bosaltilir, landing ACIK kosulur;
        # tek olcut "en az 1 govde" (sayi tabani YOK).
        import sayfalar
        d4 = os.path.join(gecici, "d4")
        os.makedirs(d4)
        argv4 = _d_kurulum(d4)[:-1]  # --landing-kapali atildi -> landing ACIK
        eski_sayfalar = sayfalar.CONTENT_PAGES
        sayfalar.CONTENT_PAGES = []
        try:
            kod, cikti = _d_kostur(argv4)
        finally:
            sayfalar.CONTENT_PAGES = eski_sayfalar
        kontrol("D4", kod == 1 and "kaynak 'landing' hic govde uretmedi" in cikti,
                "landing kaynagi bos kaldigi halde VARLIK kontrolu KIRMIZI yakmadi "
                "(kod=%d)" % kod)

        # D5 — M4b: {"ad":"PC"} envanter kaydi + sayfada "PC ile üretiyoruz" YINE KIRMIZI
        # (kara liste envanter kaydiyla SUSTURULAMAZ — uctan uca; iki agiz da yanmali).
        d5 = os.path.join(gecici, "d5")
        os.makedirs(d5)
        kod, cikti = _d_kostur(_d_kurulum(
            d5, sss_govde="İsterseniz PC ile üretiyoruz.",
            filament={"filamentler": [{"ad": "PLA"}, {"ad": "PC"}]}))
        kontrol("D5", kod == 1 and "filamentler.json ICINDE" in cikti
                and "govdede geciyor" in cikti,
                "kara liste PC (envanter kaydi + sayfa vaadi) iki agizdan KIRMIZI "
                "yakmadi (kod=%d)" % kod)

        # D6-D9 — 🔴 TEKIL EXIT KABLOLARI (KraL tur-8). Curutucu olctu: D5 iki agzi
        # BIRLIKTE test ettigi icin "kirmizi = True" satirini TEK bloktan silen jeton
        # mutasyonlari (sizinti/drift/envanter-kara/nobetci) ihlal mesajini BASIP
        # EXIT=0 donuyordu. Her kablo artik TEK ihlalli fiksturle ayri kilitli.

        # D6 — YALNIZ sizinti ihlali -> EXIT=1. Dayanak POM, public govdeye
        # (kategoriTavsiye — envanteri_coz bu anahtari OKUMAZ ama public dump'ta durur)
        # sizdirilmis; baska hicbir ihlal yok.
        d6 = os.path.join(gecici, "d6")
        os.makedirs(d6)
        kod, cikti = _d_kostur(_d_kurulum(
            d6, filament={"filamentler": [{"ad": "PLA"}, {"ad": "PETG"}],
                          "kategoriTavsiye": [{"ad": "POM"}],
                          DAYANAK_ANAHTARI: [{"ad": "POM", "satista": False,
                                              "tedarik": "siparis uzerine"}]}))
        kontrol("D6", kod == 1 and "KIRMIZI: SIZINTI" in cikti,
                "TEK sizinti ihlali EXIT=1 vermedi (kod=%d) — sizinti->exit kablosu "
                "('kirmizi = True') kopmus olabilir" % kod)

        # D7 — YALNIZ drift ihlali -> EXIT=1. Bayat blok AYNI malzeme adlarini tasir
        # ('PLA / PETG eski') ki dayanaksiz-ad KIRMIZI'si karisip kabloyu maskelemesin.
        d7 = os.path.join(gecici, "d7")
        os.makedirs(d7)
        argv7 = _d_kurulum(d7)
        _d_yaz(os.path.join(d7, "ege-bilgi.md"),
               "giris\n<!-- FILAMENT-REF -->\nPLA / PETG eski\n"
               "<!-- /FILAMENT-REF -->\nson\n")
        kod, cikti = _d_kostur(argv7)
        kontrol("D7", kod == 1 and "blogu filamentler.json'dan bayat" in cikti,
                "TEK drift ihlali EXIT=1 vermedi (kod=%d) — drift->exit kablosu "
                "kopmus olabilir" % kod)

        # D8 — YALNIZ envanter-kara ihlali -> EXIT=1. Susturma ataginin kendisi
        # ({"ad":"PC"} dayanak kaydi) sayfa vaadi OLMADAN da tek basina KIRMIZI;
        # 'govdede geciyor' YOKLUGU sayfa-agzinin karismadigini kanitlar.
        d8 = os.path.join(gecici, "d8")
        os.makedirs(d8)
        kod, cikti = _d_kostur(_d_kurulum(
            d8, filament={"filamentler": [{"ad": "PLA"}, {"ad": "PETG"}],
                          DAYANAK_ANAHTARI: [{"ad": "PC", "satista": False,
                                              "tedarik": "siparis uzerine"}]}))
        kontrol("D8", kod == 1 and "filamentler.json ICINDE" in cikti
                and "govdede geciyor" not in cikti,
                "TEK envanter-kara ihlali EXIT=1 vermedi ya da sayfa-agzi karisti "
                "(kod=%d) — envanter-kara->exit kablosu kopmus olabilir" % kod)

        # D9 — NOBETCI kablosu: ic_hata-YALNIZ hal EXIT=1 olmali. D kosumlarinda
        # dav_hata DAIMA bos (davranis=False, ozyineleme kesimi) -> "or"->"and"
        # mutasyonu tam bu fiksturde olur. Ic nobetci gecici sabit bozmayla (F12a)
        # kirmiziya dusurulur; finally geri koyar, sonraki fiksturler etkilenmez.
        d9 = os.path.join(gecici, "d9")
        os.makedirs(d9)
        argv9 = _d_kurulum(d9)
        eski_zk = ZORUNLU_KAYNAKLAR
        globals()["ZORUNLU_KAYNAKLAR"] = ("landing",)
        try:
            kod, cikti = _d_kostur(argv9)
        finally:
            globals()["ZORUNLU_KAYNAKLAR"] = eski_zk
        kontrol("D9", kod == 1 and "NOBETCI FIKSTURLERI basarisiz (ic=1" in cikti,
                "ic_hata-yalniz hal EXIT=1 vermedi (kod=%d) — 'if ic_hata or dav_hata' "
                "kablosu bozulmus olabilir (or->and?)" % kod)

    eksik = sorted(BEKLENEN_DAVRANIS_ADLARI - set(kosulan))
    fazla = sorted(set(kosulan) - BEKLENEN_DAVRANIS_ADLARI)
    if eksik or fazla:
        hata.append("DAVRANIS NOBETCISI KAPSAMI DEGISTI — eksik=%s · fazla=%s "
                    "(fikstur blogu silinmis olabilir; bilerek degistirdiysen "
                    "BEKLENEN_DAVRANIS_ADLARI'ni guncelle)" % (eksik, fazla))
    return hata, len(kosulan)


# ---------------------------------------------------------------------- ana akis
def main(argv=None, davranis=True):
    ap = argparse.ArgumentParser(description="PRUVO malzeme dayanak kapisi")
    ap.add_argument("--filament", default=FILAMENT_JSON)
    ap.add_argument("--ege", default=EGE_MD)
    ap.add_argument("--statik-kok", default=ROOT)
    ap.add_argument("--ege-malzeme", default=EGE_MALZEME_PY)
    ap.add_argument("--landing-kapali", action="store_true",
                    help="yalniz olcum/hizli kosum icin; CI'da KULLANILMAZ")
    ap.add_argument("--ic-nobetci", action="store_true",
                    help="YALNIZ fikstur nobetcilerini kosar (gercek dosyalara bakmaz)")
    args = ap.parse_args(argv)

    ic_hata, ic_sayi = ic_nobetci()
    print("IC NOBETCI (bellekte fikstur): %d kontrol, %d hata" % (ic_sayi, len(ic_hata)))
    for h in ic_hata:
        print("  ❌ " + h)
    dav_hata = []
    if davranis and not args.ic_nobetci:
        dav_hata, dav_sayi = davranis_nobetci()
        print("DAVRANIS NOBETCISI (main uctan uca, gecici dizinde): %d fikstur, %d hata"
              % (dav_sayi, len(dav_hata)))
        for h in dav_hata:
            print("  ❌ " + h)
    if args.ic_nobetci:
        print("SONUC: %s" % ("KIRMIZI ❌" if ic_hata else "YESIL ✅"))
        return 1 if ic_hata else 0

    try:
        with io.open(args.filament, encoding="utf-8") as fp:
            filament_veri = json.load(fp)
        env = envanteri_coz(filament_veri)
    except Exception as hata:  # fail-closed
        print("KIRMIZI: filamentler.json okunamadi -> %s" % hata)
        return 1
    dayanak_adlar = env.dayanak_adlar

    print("Envanter/SATIS (%s): tam=%s taban=%s takviye=%s"
          % (os.path.basename(args.filament), sorted(env.tam),
             sorted(env.taban), sorted(env.ekler) or "-"))
    print("Dayanak kaydi (SATISTA DEGIL, siparis uzerine tedarik) — YALNIZ bu TAM ADLAR "
          "mesrudur, ciplak taban/kuresel ek ACILMAZ: %s"
          % (", ".join(sorted(env.dayanak_tam)) or "-"))
    print("  karar kaydi: %s" % DAYANAK_KARAR_KAYDI)
    print("Kara liste (envanterle SUSTURULAMAZ): %s" % ", ".join(sorted(KARA_LISTE)))

    kaynaklar = []
    try:
        if not args.landing_kapali:
            kaynaklar.extend(govdeler_landing())
        kaynaklar.extend(govdeler_ege(args.ege))
        kaynaklar.extend(govdeler_statik(args.statik_kok))
    except Exception as hata:  # fail-closed
        print("KIRMIZI: govde kaynagi okunamadi -> %s" % hata)
        return 1

    ozet, dayanaksiz, kara_ihlal, ek_uyarisi = degerlendir(kaynaklar, env)

    for kaynak in sorted(ozet):
        v = ozet[kaynak]
        print("kaynak: %-16s govde=%-3d metin=%-7d malzeme adi (%d): %s"
              % (kaynak, v["govde"], v["metin"], len(v["adlar"]), sorted(v["adlar"])))
    print("Taranan govde TOPLAM: %d" % sum(v["govde"] for v in ozet.values()))

    # --- kapsam nobeti: VARLIK kontrolu (bir kaynagi silen mutasyon burada olur;
    #     sayi/karakter tabani YASAK SINIF — bkz. ZORUNLU_KAYNAKLAR + D4) ---
    kapsam_hata = []
    for kaynak in ZORUNLU_KAYNAKLAR:
        if kaynak == "landing" and args.landing_kapali:
            continue  # landing yalniz olcum kosumunda bilerek kapatilir
        if not ozet.get(kaynak, {}).get("govde", 0):
            kapsam_hata.append("kaynak '%s' hic govde uretmedi "
                               "(kaynak koddan silinmis/susturulmus olabilir)" % kaynak)
    # JSON-LD kaybi UYARI — KIRMIZI DEGIL (FAQPage'i emekli etmek mesru SEO karari;
    # tarama YETENEGI bellekte F5/F6 ile kilitli, var olan blok yine taranir).
    jsonld_var = set(slug for kaynak, slug, _m in kaynaklar
                     if kaynak == "statik-jsonld")
    for slug in BEKLENEN_JSONLD:
        if slug not in jsonld_var:
            print("UYARI: KAPSAM - '%s' sayfasinin JSON-LD blogu YOK/kaldirilmis "
                  "(bloklamaz: rich result emekliligi mesru SEO karari)" % slug)

    envanter_kara = kara_liste_envanterde(filament_veri)

    # UYARI = bloklamaz, ama SESSIZ de kalmaz (SART-2). Rapor metni ek_uyari_satirlari()
    # icinde uretilir ve fikstur F21 tarafindan KILITLIDIR (main'deki satir-ici blok
    # nobetsizdi: susturan mutasyon 40/40 YESIL geciyordu — olculdu, KraL tur-6).
    for satir in ek_uyari_satirlari(ek_uyarisi):
        print(satir)

    drift_tamam, drift_mesaj, ege_blok = drift_kontrolu(args.ege, args.ege_malzeme)
    print("DRIFT (ege-malzeme.py <-> ege-bilgi.md): %s - %s"
          % ("TAMAM" if drift_tamam else "KIRMIZI", drift_mesaj))

    # --- SIZINTI KONTROLU: dayanak kaydi URETIM duzlemine gecmis mi? ---
    # (Talimat sarti: dayanak kayitlari filamentler.json'i tuketen HICBIR ciktiyi
    #  degistirmemeli. Burada calistirilabilir kanit uretilir.)
    sizinti = {}
    if dayanak_adlar:
        # build.py'nin /filament-veri.js icin kullandigi AYNI ifade (public govde)
        public_govde = json.dumps(
            {k: v for k, v in filament_veri.items()
             if not k.startswith("_") and k != "kaynaklar"},
            ensure_ascii=False)
        uretimler = [(SIZINTI_CIKTI_FILAMENT_JS, public_govde)]
        if ege_blok is not None:
            uretimler.append((SIZINTI_CIKTI_EGE_BLOK, ege_blok))
        for kaynak, slug, metin in kaynaklar:
            if kaynak == "landing" and slug == MALZEME_REHBERI_SLUG:
                uretimler.append((SIZINTI_CIKTI_MALZEME_REHBERI, metin))
        sizinti = dayanak_sizintisi(dayanak_adlar, uretimler)
        print("SIZINTI (dayanak kaydi -> uretim duzlemi): %s - %d cikti tarandi (%s)"
              % ("KIRMIZI" if sizinti else "TEMIZ", len(uretimler),
                 ", ".join(ad for ad, _m in uretimler)))
        # Sizinti taramasi SESSIZCE bosalmasin (cikti listesi kirpilirsa kapi kanit
        # uretmeden yesil kalirdi). SAYI TABANI DEGIL, AD BAZLI -> bkz. sizinti_kapsam.
        s_hata, s_uyari = sizinti_kapsam((ad for ad, _m in uretimler),
                                         landing_acik=not args.landing_kapali)
        kapsam_hata.extend(s_hata)
        for u in s_uyari:
            print("UYARI: " + u)

    kirmizi = False
    if ic_hata or dav_hata:
        print("")
        print("KIRMIZI: NOBETCI FIKSTURLERI basarisiz (ic=%d · davranis=%d) — kapinin "
              "KENDI yetenegi bozulmus (yukaridaki ❌ satirlari)"
              % (len(ic_hata), len(dav_hata)))
        kirmizi = True
    # YEDEK KABLO (tur-9, curutucu olcumuyle eklendi): ustteki blokta or->and jetonu
    # OZ-MASKELIYORDU — D9 mutasyonu yakalar (❌ basilir) ama alarm ayni kirik
    # kablodan gecemezdi (EXIT=0). Bagimsiz ikinci kablo alarmi tasir; tek basina
    # yanlis-pozitif uretmez (olculdu: temiz agacta EXIT=0).
    if dav_hata:
        kirmizi = True

    if envanter_kara:
        print("")
        for kisa, hamlar in sorted(envanter_kara.items()):
            kim, gerekce = KARA_LISTE[kisa]
            print("KIRMIZI: KARA LISTE '%s' filamentler.json ICINDE geciyor (jeton: %s)"
                  % (kisa, ", ".join(sorted(hamlar))))
            print("    karar: %s — %s" % (kim, gerekce))
        kirmizi = True

    if kara_ihlal:
        print("")
        for kisa, yerler in sorted(kara_ihlal.items(), key=lambda x: -len(x[1])):
            kim, gerekce = KARA_LISTE[kisa]
            print("KIRMIZI: KARA LISTE '%s' %d govdede geciyor "
                  "(envanterde kaydi olsa BILE gecerli degil)" % (kisa, len(yerler)))
            print("    karar: %s — %s" % (kim, gerekce))
            for kaynak, slug, ham in sorted(set(yerler))[:12]:
                print("    %s :: %s (jeton: %s)" % (kaynak, slug, ham))
            if len(set(yerler)) > 12:
                print("    ... (+%d govde)" % (len(set(yerler)) - 12))
        kirmizi = True

    if dayanaksiz:
        print("")
        for kisa, yerler in sorted(dayanaksiz.items(), key=lambda x: -len(x[1])):
            print("KIRMIZI: '%s' filamentler.json envanterinde YOK - %d govde:"
                  % (kisa, len(yerler)))
            for kaynak, slug, ham in sorted(set(yerler))[:12]:
                print("    %s :: %s (jeton: %s)" % (kaynak, slug, ham))
            if len(set(yerler)) > 12:
                print("    ... (+%d govde)" % (len(set(yerler)) - 12))
        kirmizi = True

    if kapsam_hata:
        print("")
        for h in kapsam_hata:
            print("KIRMIZI: KAPSAM - " + h)
        kirmizi = True

    if sizinti:
        print("")
        for ad, jetonlar in sorted(sizinti.items()):
            print("KIRMIZI: SIZINTI - dayanak kaydi '%s' ciktisina gecmis: %s"
                  % (ad, ", ".join(jetonlar)))
        print("    Dayanak kayitlari YALNIZ beyan dayanagidir; satis/uretim duzlemine "
              "girmez (fiyat katsayisi Okan'da kilitli).")
        kirmizi = True

    if not drift_tamam:
        print("")
        print("KIRMIZI: ege-bilgi.md MALZEME blogu filamentler.json'dan bayat "
              "(cozum: python3 tools/ege-malzeme.py)")
        kirmizi = True

    if kirmizi:
        print("")
        print("SONUC: KIRMIZI ❌ (dayanaksiz=%d · kara-liste govde=%d · envanter-kara=%d "
              "· kapsam=%d · sizinti=%d · drift=%s · nobetci=%d+%d)"
              % (len(dayanaksiz), len(kara_ihlal), len(envanter_kara), len(kapsam_hata),
                 len(sizinti), "KIRMIZI" if not drift_tamam else "tamam",
                 len(ic_hata), len(dav_hata)))
        return 1

    print("SONUC: YESIL ✅ - dayanaksiz malzeme 0 / %d govde, kara liste ihlali yok, "
          "drift yok" % sum(v["govde"] for v in ozet.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

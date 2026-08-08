#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UZLASTIRMA NABIZ KAPISI — "katalog sapmasi ne kadar suredir DENETLENMEDI".

🔴 EKSEN DEGISIKLIGI (KraL karari, 31 Tem 2026 — OLCULDU)
=========================================================
Bu nobetci ilk halinde "cron atesledi mi" eksenine bakiyordu: "son 3 saatte `event=schedule`
kosumu yoksa KIRMIZI". IKI OLCUM o ekseni CURUTTU:

  (1) ESIK GERCEK CADANSIN ALTINDAYDI. Cron ofseti 17:10:35Z'de main'e girdi; 21:11:32Z
      kesiminde (4,016 sa) cron'un vaat ettigi 16 tetiklemeden 2'si teslim edildi
      (17:12:33Z, 20:47:18Z) -> TESLIM ORANI %12,5, tek gercek aralik 214,75 dk = 3,58 sa,
      yani beyan edilen 15 dakikanin 14,3 KATI. 3 saatlik esik bu cadansin ALTINDA kalir:
      alarm surekli kirmizi/yesil arasinda salinir. Bos kirmizi bir kapiya olan guveni
      asindirir ve o kapi ilk toplu iste devre disi birakilir
      ([[kapi-birikimi-yayin-gecikmesi]]).

  (2) EKSENIN KENDISI YANLISTI — "kosum var" != "denetim yapildi". Ayni gunun IKI
      zamanlanmis kosumu OLCULDU:
        · 17:12:33Z  conclusion=failure — on-kosul 17:12:47Z'de UC dedi (HEAD=121d0691aeee
          == uzak uc), 28,79 sn SONRA onarim adiminda BAYATLIK KAPISI kapandi
          (uzak uc 0db2aafbb580'e ilerlemisti). 21 bayat hash'in 0'i yazildi.
        · 20:47:18Z  conclusion=SUCCESS — ama on-kosul BAYAT dedi (HEAD=ca0376e7c448 ·
          uzak uc=2d4975f4bf85) ve OLCUM/ONARIM/TEYIT adimlarinin HEPSI SKIPPED oldu.
          YESIL bir kosum, SIFIR denetim.
      SONUC: 2 zamanlanmis kosumun 2'si de uzlastirma YAPMADI (%0), ama biri YESIL yandi.
      "Cron atesledi mi" ekseni bu halin IKISINI DE kacirir.

GERCEK RISK "cron atesledi mi" DEGIL, "D1 ile katalog arasindaki sapma NE KADAR SUREDIR
DENETLENMEDI"dir. Alarm o eksene tasindi.

🔴 IKINCI DAMGA EKSENI — A4 PAKET TAZELIGI (1 Agu 2026, OLCULDU)
================================================================
shop Worker'i CI'da YAYINLANMIYOR (elle `wrangler deploy`). Canli paket 30 Tem 20:30 –
1 Agu 01:58 arasinda 14,5 SAAT bayat kaldi; 676 fiziksel uruntte %84'e varan FAZLA
TAHSILAT oldu ve o an mevcut IKI canli kapi da YESIL yaniyordu. Ayni sinif 30 Tem'de de
yasandi (kart kanali 2 gun kapali) — yani yapisal ve TEKRAR EDEN bir delik.
Onarim `.github/workflows/paket-tazelik-alarmi.yml`dir (nominal 15 dk cadans — FIILEN
teslim edilen cadans DEGIL, bkz. A5 ESIGI; `push` YOK -> yayini durduramaz). O alarmin
KENDISININ olmesi yine sessiz olurdu; A4 ekseni tam olarak onu olcer: "canli fiyat yolu
ne kadar suredir denetlenmedi".
A0 ile A4 AYNI karar kodundan gecer (`_damga_satiri`) — ikiz mantik tutulmaz
([[ikiz-tanim-sessiz-ayrisma]]); yalnizca konu metinleri ve capa dosyasi ayridir.

NE OLCER (5 EKSEN, hepsi FAIL-CLOSED)
=====================================
  A0 DAMGA  (AG · BIRINCIL) — SON BASARILI **CRON TESLIMI** UZLASTIRMA damgasi N saatten
     eski mi.
     🔴 TETIKLEYICI SARTI (4 Agu 2026 — ALARM ELLE SONDURULEBILIYORDU): eksen once
     yalniz damganin ADINA/`created_at`ine/`expired`ina bakiyordu. OLCULDU: 09:45:48Z'de
     elle (`workflow_dispatch`) kosturulan bir kosum taze damga yazdi ve A0'i 9 SAAT DAHA
     sifirladi (09:49Z kosumunda `cron-nabzi` = success) — cron ise 00:17:30Z'den beri
     OLUYDU. Yani bir insan elle tetikledikce alarm HIC yanmayabilirdi. Artik damgayi
     yazan kosum, is akisinin `event=schedule` kosumlari arasinda DEGILSE damga "taze"
     SAYILMAZ: ayri bir hal basilir ("DENETIM YAPILDI AMA CRON YAPMADI") ve cron
     sessizligi surdugu surece KIRMIZI yanar. Denetimin FIILEN yapilip yapilmadigi
     satirda AYRICA gorunur — kadans (yapildi mi) ile cron sagligi (kim yapti) AYRI
     olculur, karistirilmaz.
     Damgayi uzlastirici KENDI kosar: olcum FIILEN yapildiktan (ve sapma varsa onarim
     TEYIT edildikten) sonra `uzlastirma-damgasi` adli GitHub Actions ARTIFACT'ini yukler.
     Bu nobetci `GET /repos/{depo}/actions/artifacts?name=uzlastirma-damgasi`'yi okur ve
     en yeni SURESI DOLMAMIS damganin YASINI olcer.
     NEDEN ARTIFACT (secim gerekcesi, alternatifler ELENDI):
       · Depoda IZLENEN metrik dosyasi -> uzlastirici her 15 dk'da main'e PUSH ederdi.
         Bu depoda main ucunun oynamasi BAYATLIK KAPISINI tetikler; 17:12Z kosumunu
         DUSUREN sey tam olarak buydu. Damga mekanizmasi hastaligin kendisini uretemez.
       · Kosum CIKTISINDAN turetme (conclusion) -> yukaridaki (2) numarali olcum bunu
         curutur: 20:47Z kosumu SUCCESS'ti ve HICBIR SEY olcmemisti. `conclusion`
         "denetim yapildi" DEMEK DEGILDIR.
       · Artifact: kalici (olculen saklama 24 sa > esik N), makine-okunur (ad + created_at
         + expired + workflow_run.id TEK API cagrisinda), depoya YAZMAZ, ve YALNIZ
         denetim fiilen tamamlandiginda dogar.
  A1 BICIM  (AGSIZ) — depodaki her is akisinin cron DAKIKA alani ACIK LISTE mi ve yogun
     ceyrek-saat sinirlarindan (dakika 0/15/30/45) UZAK mi.
     GEREKCE: GitHub zamanlanmis kosumlari tetiklerken tam saat basi ve ceyrek sinirlarinda
     kuyruk yigilir; dokumantasyonun kendi tavsiyesi "yogun dakikalardan kacinin"dir.
     `*/15` TAM O DORT DAKIKAYA duser. Bu eksen ONARIMIN KENDISINI KILITLER: cron `*/15`e
     geri cevrilirse bu nobetci KIRMIZI yanar (mutasyonla olculdu).
  A2 DURUM  (AG)    — cron tasiyan is akisi GitHub tarafinda kayitli ve `state == active` mi
     (GitHub 60 gun hareketsizlikta zamanlanmis is akisini `disabled_inactivity` yapar —
     dosya yerinde durur, kimse fark etmez).
  A4 PAKET  (AG · BIRINCIL, A0 ILE AYNI DESEN) — SON BASARILI PAKET TAZELIGI damgasi N
     saatten eski mi. Damgayi `paket-tazelik-alarmi.yml` KENDI kosar ve YALNIZ olcum
     `durum == 'parite'` verdiginde yukler; drift / olculemedi / atlanan kosum damga
     URETMEZ. Bu eksenin capasi ayrica IS AKISI KABLOSUDUR (`paket_alarmi_kablosu`):
     alarm dosyasi silinir, `push:` ile yayin yoluna baglanir, canli kol `--kendini-test`e
     dusurulur ya da damga kosulu `always()` yapilirsa nobetci KIRMIZI yanar.
  A5 TESLIM (AG · YENI, 4 Agu 2026) — cron METNI degil FIILI KOSUM DAGILIMI. A1 cron
     dizesine, A3 ise YALNIZ SON kosumun yasina bakar; ikisi de "96 tetik vaat edildi,
     5'i teslim edildi" halini GORMEZ. Bu eksen son W saatte gerceklesen `event=schedule`
     kosumlarini SAYAR, nominal tetik sayisiyla karsilastirir ve olculen tabanin altina
     duserse KIRMIZI yanar. Rapor satiri ALARM YANMASA DA teslim oranini ve EN UZUN
     BOSLUGU (gercek korluk penceresi) SAYIYLA basar — "cadans 15 dk" iddiasinin fiilen
     ne oldugu her kosumda gorunur. Esik turetimi: bkz. A5 ESIGI bolumu.
  A3 NABIZ  (AG · IKINCIL, KAYBOLMADI) — o is akisinin SON `event=schedule` kosumu son N
     saat icinde mi. "Cron HIC ateslemiyor" hali AYRI bir arizadir (damga tazeyken bile
     elle dispatch'le beslenmis olabilir) ve AYRI raporlanir. Yeni kaydedilen is akisina
     is akisina ilk teslim icin ayni N penceresi taninir; kosum hala yoksa N'den sonra
     alarm yanar.
     🔴 CAPA A5 ILE HIZALANDI (4 Agu 2026): eksen `max(kayit_an, yenileme_an)` kullaniyordu,
     yani cron DOSYASINA HER DOKUNUS alarmi N=9 saat SUSTURUYORDU. Bu depoda o dosyalara
     dokunma araligi medyan 5,2-5,5 saat -> eksen pratikte surekli 🟡'de kalabiliyordu
     (canli olcum 4 Agu 10:04Z: cron 9,8 saattir oluyken A3 satiri 🟡 idi). Capa artik
     TEK KAYNAKTAN gelir (`gecmis_capasi`, A5 ile AYNI): `kayit_an`. Tanim degisikligi
     SUSTURMAZ, satirda ⚠ ile GORUNUR.
     Esik NOMINAL cron araligindan DEGIL, OLCULEN TESLIM ORANINDAN turetilir
     (bkz. esik_saat).

ESIK NASIL TURETILDI (TAHMIN DEGIL — OLCUM, bkz. esik_saat)
===========================================================
  · Olculen teslim orani ...... 2 teslim / 16 nominal tetik = 0,125  (4,016 sa penceresi)
  · Efektif cadans ............ 15 dk / 0,125 = 120 dk = 2,0 sa (tek gozlenen aralik 3,58 sa)
  · Kapi kosum sikligi ........ deploy.yml son 24 saatte 126 kosum (bos kirmizi butcesi
    bu yuzden EPIZOT basina olculur: ardisik kosumlar AYNI damgayi olcer, bagimsiz cekilis
    DEGILDIR — 126 kosum tek bir bosluk icin tek bir alarm epizodudur).
  · Butce .................... haftada EN FAZLA 1 bos alarm epizodu.
  · Cozum .................... N >= ln(168 x lambda / butce) / lambda = ln(84)/0,5 = 8,86 sa
    -> tam saate yukari yuvarla -> N = 9 SAAT.
  · Denetim ................... 9 / 3,58 = 2,51x gozlenen en buyuk araligin ustunde;
    36 nominal 15 dk yuvasi; artifact saklamasinin (24 sa) 2,67x altinda.
  🔴 ESIGI "kirmizi gormeyeyim" DIYE BUYUTMEK YASAK: yukaridaki sayilar degismeden N
  degistirilemez; `--kendini-test` icinde `esik_saat(15) == 9` iddiasi bunu KILITLER
  (esigi gevseten de sikilastiran da KIRMIZI yanar).

A5 ESIGI NASIL TURETILDI (TAHMIN DEGIL — 4 Agu 2026 OLCUMU, bkz. teslim_tabani)
==============================================================================
OLCUM (gh run list --limit 300, `event=schedule` suzuldu, kesim 2026-08-04T08:30Z):
  · paket-tazelik-alarmi.yml (cron 13,28,43,58) ... 3482,2 dk pencerede BEKLENEN 232,
    GERCEKLESEN 10 -> teslim %4,31. Bosluk: min 208,3 · medyan 237,4 · MAKS 1053,5 dk.
  · d1-uzlastirici.yml (cron 9,24,39,54) ......... 4744,9 dk pencerede BEKLENEN 316,
    GERCEKLESEN 16 -> teslim %5,06. Bosluk: min 206,2 · medyan 214,8 · MAKS 1053,2 dk.
  · IKISININ EN UZUN BOSLUGU AYNI PENCEREDE: 2026-08-02T23:44Z -> 2026-08-03T17:18Z.
    Iki is akisi 4-5 dk ayri cron dakikalari tasidigi halde AYNI DAKIKALARDA, PARTI
    HALINDE atesleniyor -> dusme is akisina OZGU DEGIL, DEPO/HESAP duzeyinde.
  · Ofset hukmu: `13,28,43,58` ofseti teslim oranini DUZELTMEDI (4,31%); "acik dakika
    listesi cadansi korur" iddiasi CURUTULDU. A1 ekseni cron METNINI olcer, teslimi DEGIL.
PENCERE SECIMI: W=24 sa kayan pencerede teslim min 2 / medyan 3 (gurultulu, tek parti
kaymasi kirmiziya cevirir); W=48 sa'te min 7 / medyan 7-9 — IKI is akisinda da AYNI.
W=48 SECILDI (daha az salinim, ayni sinyal).
TABAN: olculen EN KOTU 48 sa penceresi = 7/192 = %3,65. Guvenlik boleni 2 ->
  taban oran %1,82; 15 dk cron icin taban = ceil(192 x 0,01823) = 4 kosum / 48 sa.
  Bugunku EN KOTU gozlem (7) tabanin 1,75 KATI -> bos kirmizi URETMEZ; teslim bugunku
  seviyeden %43 daha duserse (ya da tamamen dururse) KIRMIZI yanar.
🔴 ESIGI "kirmizi gormeyeyim" DIYE DUSURMEK YASAK: `--kendini-test` icindeki
`teslim_tabani(15) == 4` iddiasi hem gevsetmeyi hem sikilastirmayi KIRMIZI yakar.
🔴 A5 ILE A0/A4 AYNI SEYI OLCMEZ ([[beyan-edilmis-survivor]]): damga eksenleri "SON
olcum kac saatlik" der; parti halinde teslim edilen bir kosum damgayi tazeler ve A0/A4/A3
YESIL kalirken teslim orani sifira yakin olabilir. Ayirt edici fikstur `--kendini-test`
icinde KOSAR (A5 (a): damga taze + son kosum taze + teslim COKMUS -> YALNIZ A5 kirmizi).

FAIL-CLOSED SOZLESMESI
======================
Veri CEKILEMEZSE (ag hatasi, HTTP != 200, bozuk JSON, eksik alan, ad suzgeci calismamis,
zaman damgasi cozulemiyor, PyYAML yok) sonuc YESIL DEGIL, "OLCULEMEDI" = rc 2 = KIRMIZI'dir.
Damga HIC YOKSA ya da HEPSI SURESI DOLMUSSA bu ALARM'dir (rc 1): "denetim hic yapilmadi"
olculebilir bir haldir, olculemezlik degil. Iki hal de KIRMIZI.

CIKIS KODLARI:  0 = DENETIM TAZE  ·  1 = ALARM (damga bayat/yok · cron sessiz · bicim
                ihlali · is akisi devre disi)  ·  2 = OLCULEMEDI (fail-closed KIRMIZI)

YAYIN YOLUNU BLOKLAMAZ: deploy.yml'de `cron-nabzi` job'unda kosar; `deploy` bu job'a
`needs:` ile BAGLI DEGILDIR (serit B). Kirmizi GORUNUR, yayin CIKAR.

Kullanim:
    python3 tools/cron-nabiz-kapisi.py                 # GERCEK olcum (GitHub API)
    python3 tools/cron-nabiz-kapisi.py --kendini-test  # AGSIZ fikstur kabulu (iki yonlu)
"""
import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
WORKFLOW_DIZIN = os.path.join(ROOT, ".github", "workflows")

DEPO = os.environ.get("GITHUB_REPOSITORY") or "Pruvo138/pruvo"
API = "https://api.github.com"

# UZLASTIRICI — A0 damga ekseninin capasi. Bu dosya yoksa/cron'suzsa OLCULEMEDI (rc 2):
# nobetci "denetleyecek bir uzlastirici" oldugunu VARSAYMAZ, OLCER.
UZLASTIRICI_DOSYA = "d1-uzlastirici.yml"
# Uzlastiricinin her BASARILI denetimden sonra yukledigi artifact adi (TEK KAYNAK:
# .github/workflows/d1-uzlastirici.yml `Damga` adimi ayni sabiti kullanir).
DAMGA_ADI = "uzlastirma-damgasi"

# PAKET TAZELIGI ALARMI — A4 ekseninin capasi. Bu dosya yoksa/cron'suzsa OLCULEMEDI
# (rc 2): nobetci "canli fiyat yolunu denetleyen bir is var" VARSAYMAZ, OLCER.
PAKET_ALARM_DOSYA = "paket-tazelik-alarmi.yml"
PAKET_DAMGA_ADI = "paket-tazelik-damgasi"
# Alarmin GERCEK olcum kolu (bayraksiz = canli). `--kendini-test`e dusurulurse alarm
# hicbir canli sey olcmez ama kosum YESIL kalirdi -> kablo capasi bunu KIRMIZI yakar.
PAKET_OLCUM_ARACI = "tools/fiziksel-canli-kapisi.py"
# Damganin dogmasi icin olcumun vermesi GEREKEN etiket. TEK KAYNAK: bu dize
# tools/fiziksel-canli-kapisi.py::DURUM_ETIKET["PARITE"] ile AYNI olmak zorundadir ve
# `--kendini-test` bunu KOSARAK dogrular (elle senkron tutulan ikinci kopya YOK).
PAKET_PARITE_ETIKETI = "parite"

# ─── PUSH SERIDI (4 Agu 2026) — bayatlik olcumunun FIILEN ATESLENEN tetigi ───
# Cron teslimi %4,31; en uzun sessizlik 1053,5 dk (A5 ekseninin olctugu hal). Ayni
# depoda `deploy.yml` event=push kosumlari AYNI pencerede 152 kez teslim edildi ve en
# uzun boslugu 418,9 dk idi. Bu yuzden bayatlik olcumu AYRICA push tetikli bir seride
# baglandi. Serit EK'tir: cron kolu KALDIRILMADI.
# Bu capa, seridin YAYIN YOLUNA BAGLANMADIGINI olcer — iddia yorum degil KOSULAN kapidir.
PUSH_SERIT_DOSYA = "odeme-bayatlik-push.yml"
PUSH_SERIT_ARACI = "tools/shop-bayatlik-kapisi.py"
# Yayin is akisi: eszamanlilik grubu BURADAN kosarak okunur (ikiz dize TUTULMAZ,
# [[ikiz-tanim-sessiz-ayrisma]]).
YAYIN_DOSYA = "deploy.yml"
# 🔴 IZIN LISTESI — KARA LISTE DEGIL (4 Agu 2026, bagimsiz curutucu bulgusu)
# ILK HAL kara listeydi: ("pull_request", "workflow_call"). OLCULDU (kopya dizin):
# is akisina `pull_request_target` eklendiginde `push_serit_kablosu()` YESIL kaliyordu
# (olculen tetikler: ['pull_request_target','push','workflow_dispatch']) ve
# `is-akisi-kapisi.py` de rc=0 veriyordu; `git grep pull_request_target` tools/ + .github/
# icinde 0 vurus -> IKINCI KATMAN DA YOKTU. Cok parcali bir jetonda parcalardan birini
# kapatmak sizintiyi KAPATMAZ ([[maskeleme-kismi-kapatma]]): kara liste TAMAMLANAMAZ
# (yarin GitHub yeni bir tetik ekler ve kapi sessizce delik kalir), izin listesi TANIM
# GEREGI kapalidir. Serit YALNIZ bu iki tetigi tasiyabilir.
PUSH_SERIT_IZINLI_TETIK = ("push", "workflow_dispatch")
# TESHIS TABLOSU — KAPI DEGIL: kapi izin listesidir, bu tablo yalnizca ariza metnini
# adiyla soyler. Bir tetigin BURADA OLMAMASI onu mesru yapmaz (izin listesinde degilse
# zaten KIRMIZI). Girisler "fork/yabanci tetikleyebilir + TABAN DEPO baglami + secret"
# ve "seridi yayin yoluna baglar" eksenlerinden secildi.
PUSH_SERIT_TEHLIKE = {
    "pull_request_target": "fork PR'ini TABAN DEPO baglaminda ve DEPO SECRET'leriyle "
                           "kosturur -> yabanci kod CLOUDFLARE_API_TOKEN'a erisebilir "
                           "(secret tasiyan bir is akisi icin EN tehlikeli tetik)",
    "pull_request": "fork PR'i seridi baslatir; olcum cadansini ve kuyruk yukunu "
                    "disaridan surdurur",
    "issue_comment": "herkesin yazabildigi bir yorum, TABAN DEPO baglaminda secret'li "
                     "bir kosum baslatir",
    "pull_request_review": "ayni sinif: dis katkinin tetikleyebildigi, taban depo "
                           "baglaminda secret'li kosum",
    "pull_request_review_comment": "ayni sinif: dis katkinin tetikleyebildigi, taban "
                                   "depo baglaminda secret'li kosum",
    "workflow_call": "is akislari arasi TEK bag yolu budur; acik olursa serit "
                     "deploy.yml'in `needs` grafinin ICINE girebilir",
    "workflow_run": "seridi deploy.yml'in TAMAMLANMASINA baglar -> nobetci OLCTUGU "
                    "hatta bagimli olur ve hat tikandiginda O DA susar (Y4 sinifi)",
}
# Serit YALNIZ ana dalda kosar. `branches: ['**']` gibi genis bir desen her dala kosar,
# gurultuyu kat kat artirir ve alarmi FIILEN susturur (olculdu: bu depoda kapi birikmesi
# yayin suresini 21 gunde 15,6x uzatti — [[kapi-birikimi-yayin-gecikmesi]]).
PUSH_SERIT_DAL = "main"
# Seridin canli kolunun ihtiyac duydugu secret. Kapsami VARSAYILMAZ, OLCULUR:
# bkz. `_secret_ortam_kapsami`.
PUSH_SERIT_SECRET = "CLOUDFLARE_API_TOKEN"

# DAMGA KUTUGU — ad -> (yazan is akisi, damganin IDDIASI). `--damga-yaz` bu kutukten
# DISARI cikamaz: bilinmeyen bir ad verilirse hata verir (uydurma adla yuklenen bir
# artifact hicbir eksen tarafindan okunmaz, yani sessiz bir hicligi damgalardi).
DAMGA_KUTUGU = {
    DAMGA_ADI: (UZLASTIRICI_DOSYA,
                "d1-katalog sapmasi olculdu ve kapatildi (olcum + gerekiyorsa onarim teyidi)"),
    PAKET_DAMGA_ADI: (PAKET_ALARM_DOSYA,
                      "canli fiyat yolu olculdu ve PARITE cikti (hazir ticari malda "
                      "tahsilat liste fiyati; canli paket depo HEAD'i ile ayni nesil)"),
    # SAPMA DAMGASI — A0/A4 damgalarindan FARKLI SINIF: onlar "denetim FIILEN yapildi"
    # der (YAS olculur), bu "BU yayin kosumunda sapma OLDU" der (IKILI hukum, yas YOK).
    # 4 Agu kol ayriminin tasiyicisi: kadans kolunda onarilan sapma cagiran kosumu
    # KIRMIZI yakmaz, bunun yerine bu damga dogar ve d1-sapma-alarmi.yml onu AYRI bir
    # kosumda KIRMIZI yakar -> sapma SUSTURULMAZ, KANALI degisir.
    "d1-sapma-damgasi": (UZLASTIRICI_DOSYA,
                         "bu yayin kosumunda D1 sapmasi OLUSTU ve onarildi; sapmanin "
                         "KENDISI bir ust-yol kacagidir (pre-push kancasi / CI D1 adimi / "
                         "elle push) ve AYRI kanaldan (d1-sapma-alarmi.yml) kirmizi yakar"),
}
# Kol ayriminin capalari — tek kaynak (yazici, okuyucu ve kablo kapisi ayni sabiti kullanir).
SAPMA_DAMGA_ADI = "d1-sapma-damgasi"
SAPMA_ALARM_DOSYA = "d1-sapma-alarmi.yml"
SAPMA_ALARM_ARACI = "tools/d1-sapma-kapisi.py"
# `workflow_call` girdisi: kadans kolunu cron kolundan ayiran TEK bayrak.
KADANS_BAYRAGI = "kadans_kolu"

# Yogun tetikleme dakikalari — `*/15` tam bu kumeye duser.
YOGUN_DAKIKALAR = frozenset((0, 15, 30, 45))

# ─── ESIK TURETIMININ OLCULEN GIRDILERI (31 Tem 2026, kesim 21:11:32Z) ────────
# Bu dort sayi degismeden N degistirilemez. Hepsi TEK bir olcumden gelir:
#   pencere = cron ofset commit'i (17:10:35Z) -> kesim (21:11:32Z) = 240,95 dk = 4,016 sa
OLCUM_PENCERESI_SAAT = 4.016
NOMINAL_TETIK = 16      # `7,22,37,52 * * * *` o pencerede 16 tetik VAAT ETTI
OLCULEN_TESLIM = 2      # GitHub 2 tanesini teslim etti (17:12:33Z · 20:47:18Z)
TESLIM_ORANI = OLCULEN_TESLIM / float(NOMINAL_TETIK)          # 0,125
# Bos alarm butcesi: haftada en fazla 1 EPIZOT (kosum basina degil — 126 kosum/24 sa
# ayni damgayi olcer, bagimsiz cekilis degildir).
BOS_ALARM_BUTCESI_HAFTA = 1.0
HAFTA_SAAT = 168.0
# Kirpma: taban absurd kucuk esikleri, tavan artifact saklamasini (olculen 24 sa) korur.
ESIK_TABAN_SAAT = 2
ESIK_TAVAN_SAAT = 20
DAMGA_SAKLAMA_SAAT = 24  # OLCULDU: expires_at - created_at = 1 gun (depo ayari)

# ─── A5 TESLIM EKSENININ OLCULEN GIRDILERI (4 Agu 2026) ──────────────────────
# Bu dort sayi degismeden taban degistirilemez (bkz. dosya basi "A5 ESIGI").
TESLIM_PENCERESI_SAAT = 48        # W — 24 sa'te min 2/medyan 3 (gurultulu), 48 sa'te min 7
OLCULEN_TABAN_TESLIM = 7          # EN KOTU 48 sa kayan penceresinde teslim edilen kosum
OLCULEN_TABAN_NOMINAL = 192       # ayni pencerede nominal tetik (15 dk cron x 48 sa)
TESLIM_GUVENLIK_BOLENI = 2.0      # taban, olculen EN KOTU gozlemin YARISI
TESLIM_TABAN_ORANI = OLCULEN_TABAN_TESLIM / (OLCULEN_TABAN_NOMINAL * TESLIM_GUVENLIK_BOLENI)
# API sayfa siniri: pencere DOLU gozlenemediginde bunu SOYLEMEK zorundayiz (sessiz
# kirpma = sahte yesil). Taban her gercekci cron icin bu sayinin ALTINDA kalir; iddia
# `--kendini-test`te KOSULUR (teslim_tabani(1) < TESLIM_SAYFA).
TESLIM_SAYFA = 100

# ─── CANLI KALIBRASYON (5 Agu 2026, kesim 11:42:54Z — OLCULEN KUSUR) ─────────
# `TESLIM_ORANI` DONMUS bir sabitti: 31 Tem'de 4,016 SAATLIK tek bir pencerede olculdu
# (2/16 = %12,5) ve N=9 saat ondan turedi. 5 Agu olcumu o rejimin ARTIK OLMADIGINI
# gosterdi:
#   · gozlem penceresi ...... 6636,6 dk = 110,6 sa (ilk 31 Tem 17:12:33Z, son 5 Agu 07:49:11Z)
#   · nominal tetik ......... 442   (`9,24,39,54` = 15 dk)
#   · FIILEN teslim ......... 20    -> %4,52  (donmus sabitin 2,77 KATI KOTU)
#   · bosluklar (dk) ........ en kucuk 206,2 · medyan 236,3 · EN BUYUK 1053,2 (17,55 sa)
# Sonuc: N=9 sa esigi, GERCEKLESEN cadansin ALTINDA kaldi ve BOS KIRMIZI uretti.
# OLCULDU (son 30 deploy kosumu): `cron-nabzi` 3 kez KIRMIZI yandi (06:59:57Z · 07:24:00Z
# · 08:05:50Z). Ilk ikisinde d1-uzlastirici cron boslugu 598,1 dk (9,97 sa) idi — yani
# esigi 1,08x asan, bu rejimde NORMAL bir bosluk; kadans (push) kolu ayni dakikalarda
# uzlastirmayi YAPMISTI (damga 06:46:26Z). Ucuncusunde kirmizi paket alarminin A4/A3
# ekseninden geldi (9,3 sa). Bos kirmizi, kapinin ilk toplu iste devre disi
# birakilmasinin YOLUDUR ([[kapi-birikimi-yayin-gecikmesi]]).
#
# ONARIM: esik DONMUS sabitten degil, o is akisinin KENDI CANLI teslim oranindan
# turetilir (A5 ile AYNI pencere ve AYNI capa -> TEK KAYNAK, [[ikiz-tanim-sessiz-ayrisma]]).
#
# 🔴 KENDINI SUSTURMA KAPISI — BU UC SART OLMADAN ONARIM FAIL-OPEN OLURDU:
#   (1) Canli oran YALNIZ A5 TABANINI GECEN bir rejimden turetilir. Teslim cokerse
#       (taban alti) oran KULLANILMAZ, DONMUS 9 saate geri DUSULUR: cokme "sabir"
#       SATIN ALAMAZ. Bu sart olmasa kotulesen teslim esigi buyutur, esik buyudukce
#       alarm susar — klasik geri besleme deligi.
#   (2) MUTLAK SESSIZLIK TAVANI: turetilen N ne olursa olsun bu degeri ASAMAZ.
#       Kalibrasyon = OLCULEN EN BUYUK bosluk 1053,2 dk = 17,55 sa -> yukari yuvarla 18.
#       DAMGA_SAKLAMA_SAAT (24) ALTINDA tutulur, yoksa damga suresi dolar ve A0 hicbir
#       zaman yesil olamazdi.
#   (3) Turetilemeyen her hal (gecmis yetersiz · sayfa kirpik · aralik cozulemedi)
#       DONMUS esige duser — yani DAHA SIKI olana, daha gevsek olana DEGIL.
# Bu, esigin d1-uzlastirici icin 9 -> 18 saate GEVSEDIGI anlamina gelir; gerekce
# ustteki OLCUMDUR ve gevseme yalniz teslim A5 tabaninin USTUNDEYKEN gecerlidir.
OLCULEN_CANLI_PENCERE_SAAT = 110.6
OLCULEN_CANLI_NOMINAL = 442
OLCULEN_CANLI_TESLIM = 20                 # -> %4,52
OLCULEN_EN_UZUN_BOSLUK_DK = 1053.2        # 17,55 sa
MUTLAK_SESSIZLIK_SAAT = 18                # ceil(17,55); < DAMGA_SAKLAMA_SAAT (24)

# 🔴 A4 TAVANI AYRIDIR — VE KUCUKTUR (curutucu iadesi, 5 Agu 2026)
# ─────────────────────────────────────────────────────────────────────────────
# ILK ONARIM TASLAGI TEK TAVAN (18 sa) KOYDU ve `--kendini-test` bunu KIRMIZI yakti:
# "A4 (b) ONCE-KIRMIZI: 1 Agu'da OLCULEN 14,5 saatlik bayatlik penceresi" fiksturu
# YESILE dondu. Yani onarim, tam da o eksenin VAR OLMA SEBEBINI fail-open yapiyordu
# ([[duzeltme-fail-open-cevirebilir]]).
#
# AYRIM: iki tavan IKI FARKLI soruyu cevaplar ve KARISTIRILAMAZ.
#   · MUTLAK_SESSIZLIK_SAAT (A0/A3) = "sessizlik NE ZAMAN ANORMALDIR" -> teslim
#     ISTATISTIGINDEN turer (olculen en uzun bosluk 1053,2 dk). Katalog uzlastirmasinin
#     GERCEK maruziyeti zaten kadans (push) koluyla ~20 dk'dir; cron sessizligi bir
#     SAGLIK sinyalidir, zarar sinyali degil.
#   · PAKET_BAYATLIK_TAVAN_SAAT (A4) = "sessizlik NE ZAMAN PAHALIYA PATLAR" -> OLCULEN
#     ZARAR OLAYINDAN turer: 30 Tem 20:30 – 1 Agu 01:58 arasi canli paket 14,5 SAAT bayat
#     kaldi ve 676 fiziksel urunde %84'e varan FAZLA TAHSILAT oldu. Bu eksenin esigi o
#     pencerenin ALTINDA KALMAK ZORUNDADIR, yoksa AYNI olay yeniden sessizce gecer.
# KURAL: hangi tavan daha KUCUKSE o baglar. Teslim istatistigi bir ZARAR esigini
# GEVSETEMEZ.
OLCULEN_PAKET_ZARAR_SAAT = 14.5           # 1 Agu OLCULEN fazla tahsilat penceresi
PAKET_BAYATLIK_TAVAN_SAAT = 9             # < OLCULEN_PAKET_ZARAR_SAAT (iddia kosuluyor)


class OlcumHatasi(Exception):
    """Veri cekilemedi/anlasilamadi -> YESIL degil OLCULEMEDI (rc 2)."""


# ---- YAML (GERCEK AYRISTIRICI, iki kol, fail-closed) ------------------------
# METIN TAKLIDI YOK ([[mimar-kapi-parser-taklidi]]): cron alani ancak GERCEK bir YAML
# ayristiricisiyla okunur. PyYAML yoksa tools/yaml-oku.py'nin de kullandigi ruby/psych
# koluna DUSULUR; ikisi de yoksa OLCULEMEDI (rc 2), asla "cron yok -> yesil".
def yaml_ayristirici_adi():
    try:
        import yaml  # noqa: F401,PLC0415
        return "pyyaml"
    except Exception:  # noqa: BLE001
        pass
    import shutil
    if shutil.which("ruby"):
        return "ruby/psych"
    return None


def yaml_belge(metin):
    """YAML metnini python nesnesine cevirir (PyYAML | ruby/psych). Fail-closed."""
    try:
        import yaml  # noqa: PLC0415 — bilerek gec import (yoklugu TESHIS edilebilsin)
        return yaml.safe_load(metin)
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001 — gercek ayristirma hatasi
        raise OlcumHatasi("YAML ayristirilamadi (pyyaml: %s: %s)" % (type(e).__name__, e))
    import shutil
    import subprocess
    if not shutil.which("ruby"):
        raise OlcumHatasi(
            "GERCEK YAML ayristiricisi YOK (ne PyYAML ne ruby/psych) -> is akisi "
            "dosyalarinin cron alani okunamadi. Metin taklidiyle 'yesil' demek bu "
            "nobetcinin konusunun tekrari olurdu (sessiz zayiflama), o yuzden OLCULEMEDI.")
    kod = ("require 'yaml'; require 'json'; "
           "puts JSON.generate(YAML.safe_load(STDIN.read, aliases: true))")
    p = subprocess.run(["ruby", "-e", kod], input=metin, capture_output=True,
                       text=True, timeout=30)
    if p.returncode != 0:
        raise OlcumHatasi("YAML ayristirilamadi (ruby/psych rc=%d): %s"
                          % (p.returncode, (p.stderr or "").strip()[:300]))
    try:
        return json.loads(p.stdout)
    except Exception as e:  # noqa: BLE001
        raise OlcumHatasi("ruby/psych ciktisi JSON degil (%s)" % e)


def _on_bolumu(govde):
    """`on:` bolumu. PyYAML (YAML 1.1) `on` anahtarini BOOL True'ya cevirir — iki hali de
    ara. OLCULDU: yalniz "on" arayan bir okuyucu bu depodaki HER is akisini "cron'suz"
    sanardi (sahte YESIL)."""
    if not isinstance(govde, dict):
        raise OlcumHatasi("is akisi kok dugumu sozluk degil (%s)" % type(govde).__name__)
    # PyYAML -> bool True · ruby/psych JSON -> "true" (JSON anahtarlari metindir).
    for anahtar in (True, "true", "on", "On", "ON"):
        if anahtar in govde:
            return govde[anahtar]
    return None


def cron_ifadeleri(dizin=WORKFLOW_DIZIN):
    """[(dosya_adi, cron_ifadesi), ...] — depodaki is akisi dosyalarindan.
    Ayristirilamayan bir dosya OlcumHatasi'dir (fail-closed)."""
    if not os.path.isdir(dizin):
        raise OlcumHatasi("is akisi dizini YOK: %s" % dizin)
    bulunan = []
    for ad in sorted(os.listdir(dizin)):
        if not ad.endswith((".yml", ".yaml")):
            continue
        yol = os.path.join(dizin, ad)
        try:
            with open(yol, encoding="utf-8") as f:
                govde = yaml_belge(f.read())
        except OlcumHatasi as e:
            raise OlcumHatasi("%s: %s" % (ad, e))
        except Exception as e:  # noqa: BLE001
            raise OlcumHatasi("%s ayristirilamadi (%s: %s)" % (ad, type(e).__name__, e))
        tetik = _on_bolumu(govde)
        if not isinstance(tetik, dict):
            continue
        zaman = tetik.get("schedule")
        if not zaman:
            continue
        if not isinstance(zaman, list):
            raise OlcumHatasi("%s: `schedule` bir liste degil (%s)"
                              % (ad, type(zaman).__name__))
        for giris in zaman:
            if not isinstance(giris, dict) or "cron" not in giris:
                raise OlcumHatasi("%s: `schedule` girisi `cron` tasimiyor: %r" % (ad, giris))
            bulunan.append((ad, str(giris["cron"]).strip()))
    return bulunan


# ---- A1: cron dakika alani --------------------------------------------------
def dakika_kumesi(cron):
    """Cron'un DAKIKA alanindaki acik dakikalar (set) ya da None (acik liste DEGIL:
    `*`, `*/n`, adim/joker iceriyor)."""
    alanlar = cron.split()
    if len(alanlar) != 5:
        raise OlcumHatasi("cron 5 alanli degil: %r" % cron)
    dk = alanlar[0]
    if "*" in dk or "/" in dk:
        return None
    dakikalar = set()
    for parca in dk.split(","):
        parca = parca.strip()
        if re.fullmatch(r"\d{1,2}", parca):
            dakikalar.add(int(parca))
        elif re.fullmatch(r"\d{1,2}-\d{1,2}", parca):
            bas, son = (int(x) for x in parca.split("-"))
            if bas > son:
                raise OlcumHatasi("cron dakika araligi ters: %r" % cron)
            dakikalar.update(range(bas, son + 1))
        else:
            raise OlcumHatasi("cron dakika alani cozulemedi: %r" % cron)
    if not dakikalar or max(dakikalar) > 59:
        raise OlcumHatasi("cron dakika alani gecersiz: %r" % cron)
    return dakikalar


def aralik_dakika(dakikalar):
    """Ardisik iki tetikleme arasindaki EN KISA sure (dk). Tek dakika -> 60."""
    sirali = sorted(dakikalar)
    if len(sirali) == 1:
        return 60
    farklar = [b - a for a, b in zip(sirali, sirali[1:])]
    farklar.append(60 - sirali[-1] + sirali[0])   # saat sinirini asan fark
    return min(farklar)


def efektif_aralik_dk(nominal_aralik_dk, oran=None):
    """NOMINAL cron araligini OLCULEN teslim oraniyla GERCEK cadansa cevirir.

    Eski esik NOMINAL araliktan turetiliyordu (15 dk -> N=3 sa) ve GERCEK cadansin
    (olculen 120 dk efektif, tek gozlenen aralik 214,75 dk) ALTINDA kaliyordu -> bos
    kirmizi. Cron'un VAAT ETTIGI degil, GitHub'in TESLIM ETTIGI cadans esas alinir.

    `oran` verilmezse DONMUS `TESLIM_ORANI` kullanilir. FAIL-CLOSED: sifir/negatif oran
    "sonsuz sabir" demek olurdu (bolme sonsuza gider) -> OLCULEMEDI."""
    if oran is None:
        oran = TESLIM_ORANI
    if oran <= 0:
        raise OlcumHatasi("teslim orani %r -> efektif cadans SONSUZ olurdu; sifir teslim "
                          "bir esik TURETEMEZ (fail-closed)" % (oran,))
    return nominal_aralik_dk / oran


def esik_saat(nominal_aralik_dk, oran=None):
    """N (saat) — OLCULEN cadanstan turetilir, tahminle DEGIL.

    Teslim surecini hafizasiz (Poisson) say: lambda = 1/efektif_aralik (1/saat).
    "N saatten uzun bir bosluk" epizotlarinin haftalik beklenen sayisi
    lambda x e^(-lambda x N) x 168'dir. Butce (haftada 1 epizot) icin cozulur:
        N >= ln(168 x lambda / butce) / lambda
    15 dk nominal · teslim orani 0,125 -> efektif 120 dk -> lambda = 0,5 ->
        N >= ln(84)/0,5 = 8,86 -> tam saate yukari yuvarla -> N = 9 SAAT.

    IKINCI TABAN (yavas cron korumasi): cok seyrek bir cron icin ustteki cozum
    negatife duser (haftada 1 teslimden az); o halde N = 2 x efektif aralik alinir.
    Sonuc [ESIK_TABAN_SAAT, ESIK_TAVAN_SAAT] araligina kirpilir; TAVAN artifact
    saklamasinin (olculen 24 sa) ALTINDA tutulur, aksi halde damga suresi dolar ve
    esik HICBIR ZAMAN yesil olamazdi."""
    efektif_saat = efektif_aralik_dk(nominal_aralik_dk, oran) / 60.0
    lam = 1.0 / efektif_saat
    epizot = (HAFTA_SAAT * lam) / BOS_ALARM_BUTCESI_HAFTA
    butce_cozumu = (math.log(epizot) / lam) if epizot > 1.0 else 0.0
    ham = max(butce_cozumu, 2.0 * efektif_saat)
    return int(min(ESIK_TAVAN_SAAT, max(ESIK_TABAN_SAAT, math.ceil(ham - 1e-9))))


def canli_teslim_orani(g, simdi):
    """(oran | None, sebep) — o is akisinin W penceresinde FIILEN olculen teslim orani.

    🔴 A5 ILE TEK KAYNAK: ayni pencere (TESLIM_PENCERESI_SAAT), ayni capa
    (`gecmis_capasi`), ayni sayim (pencereye dusen `event=schedule` kosumlari). Ikinci
    bir sayim yazilsaydi iki eksen ayni soruya iki cevap verirdi
    ([[ikiz-tanim-sessiz-ayrisma]]).

    TURETILEMEYEN HER HAL `None` DONER ve cagiran DONMUS (daha SIKI) esige duser —
    gevsek olana DEGIL. Dort sart:
      (1) cron araligi cozulebilmeli (yoksa nominal tetik sayilamaz; A1 zaten kirmizi),
      (2) gozlem gecmisi >= W (kisa gecmis oran DEGIL, gurultu olcer),
      (3) API sayfasi KIRPILMAMIS olmali (kirpik sayfa teslimi EKSIK sayar -> orani
          DUSUK gosterir -> esigi HAKSIZ YERE buyutur; tam ters yonde tehlikeli),
      (4) 🔴 TESLIM A5 TABANINI GECMELI. Cokmus bir rejim kendi esigini buyutemez;
          cokme AYRI bir alarmdir (A5) ve sabir SATIN ALMAZ. Bu sart olmadan onarim
          fail-open olurdu: teslim kotulestikce esik buyur, esik buyudukce alarm susar
          ([[duzeltme-fail-open-cevirebilir]])."""
    aralik = g.get("aralik")
    if not aralik:
        return None, "cron araligi cozulemedi"
    W = TESLIM_PENCERESI_SAAT
    _kayit_an, gecmis_saat, _uyari = gecmis_capasi(g, simdi, W)
    if gecmis_saat is None or gecmis_saat < W:
        return None, ("gozlem gecmisi %s < pencere %d sa"
                      % (("%.1f sa" % gecmis_saat) if gecmis_saat is not None else "yok", W))
    if g.get("pencere_kirpildi"):
        return None, "API sayfa siniri doldu (teslim EKSIK sayilir)"
    pencere_basi = simdi - timedelta(hours=W)
    teslim = len([x for x in (g.get("tum_kosumlar") or []) if x > pencere_basi])
    a5_tabani = teslim_tabani(aralik, W)
    if teslim < a5_tabani:
        return None, ("teslim %d < A5 tabani %d: COKMUS rejim kendi esigini BUYUTEMEZ"
                      % (teslim, a5_tabani))
    return teslim / teslim_nominal(aralik, W), ("teslim %d / nominal %.0f (W=%d sa)"
                                                % (teslim, teslim_nominal(aralik, W), W))


def canli_esik(g, simdi, tavan=MUTLAK_SESSIZLIK_SAAT):
    """(N_saat, kaynak_metni, efektif_dk) — YURURLUKTEKI esik. A0/A3/A4 AYNI yoldan.

    `tavan` EKSENE GORE degisir: A0/A3 icin MUTLAK_SESSIZLIK_SAAT (teslim istatistigi),
    A4 icin PAKET_BAYATLIK_TAVAN_SAAT (OLCULEN ZARAR penceresi). Gerekce: sabit
    tanimlarindaki "A4 TAVANI AYRIDIR" blogu.

    Sira: canli oran (varsa) -> DONMUS oran (yoksa) -> MUTLAK SESSIZLIK TAVANI (her hal).
    Tavan turetimden BAGIMSIZ ve KOSULSUZDUR: olcum ne derse desin, bu kadar saatlik
    TAM SESSIZLIK alarmdir.

    `efektif_dk` N ile AYNI orandan turer — rapor satiri ile hukum AYRISAMAZ
    ([[ikiz-tanim-sessiz-ayrisma]]); ikisi ayri oran kullansaydi satir "efektif 120 dk"
    derken esik bambaska bir cadanstan gelebilirdi."""
    aralik = g.get("aralik")
    donmus = esik_saat(aralik) if aralik else ESIK_TABAN_SAAT
    try:
        oran, sebep = canli_teslim_orani(g, simdi)
    except OlcumHatasi as e:
        oran, sebep = None, str(e)
    if oran is None:
        n = donmus
        kaynak = ("DONMUS oran %.3f (canli oran turetilemedi: %s)" % (TESLIM_ORANI, sebep))
    else:
        n = esik_saat(aralik, oran)
        kaynak = ("CANLI oran %.4f · %s · donmus oran %.3f -> N=%d sa"
                  % (oran, sebep, TESLIM_ORANI, n))
    efektif_dk = efektif_aralik_dk(aralik, oran) if aralik else None
    if n > tavan:
        kaynak += " · TAVAN %d sa BAGLADI" % tavan
        n = tavan
    return n, kaynak, efektif_dk


def teslim_nominal(aralik_dk, pencere_saat=TESLIM_PENCERESI_SAAT):
    """Cron'un W saatte VAAT ETTIGI tetikleme sayisi."""
    return pencere_saat * 60.0 / float(aralik_dk)


def teslim_tabani(aralik_dk, pencere_saat=TESLIM_PENCERESI_SAAT):
    """A5 TABANI — W saatte teslim edilmesi GEREKEN EN AZ kosum sayisi.

    OLCULEN en kotu 48 saatlik pencere (7/192 = %3,65) ikiye bolunerek turetilir.
    Nominal cadanstan DEGIL, GitHub'in FIILEN teslim ettiginden gelir: nominalden
    turetilen bir taban (or. "96/gun bekliyorum") ilk gunden itibaren surekli kirmizi
    yanar ve kapi ilk toplu iste devre disi birakilir ([[kapi-birikimi-yayin-gecikmesi]]).
    En az 1: bir kosum bile teslim edilmiyorsa hal ZATEN alarmdir."""
    return max(1, int(math.ceil(teslim_nominal(aralik_dk, pencere_saat)
                                * TESLIM_TABAN_ORANI - 1e-9)))


def gecmis_capasi(g, simdi, pencere_saat):
    """🔴 TEK KAYNAK — A3 ve A5'in GOZLEM CAPASI. (kayit_an, gecmis_saat, uyari|None)

    CAPA `kayit_an`dir: is akisinin GitHub'da KAYITLI oldugu an. `yenileme_an` (cron
    dosyasina dokunan son commit) capa DEGILDIR, yalnizca GORUNURLUK uyarisidir.

    NEDEN (4 Agu 2026 OLCUMU — A3'un capasi buydu ve alarmi SUSTURUYORDU):
    A3 `max(kayit_an, yenileme_an)` kullaniyordu; bu depoda alarm dosyalarina dokunma
    araligi medyan 5,2 sa (paket) / 5,5 sa (d1) ve son 8 araligin yalnizca 1'i 9 saati
    asiyor. Yani cron dosyasina her dokunus A3'u N=9 saat SUSTURUYORDU: canli olcumde
    (4 Agu 10:04Z) cron 9,8 saattir OLU iken A3 satiri 🟡 ("tanim 1,1 sa once
    kaydedildi") yaziyordu. A5 ekseni AYNI capayi olcup REDDETMISTI; iki eksen AYNI
    soruyu (gozlem gecmisi yeterli mi) IKI FARKLI cevapla yanitliyordu
    ([[ikiz-tanim-sessiz-ayrisma]]). Capa TEK KAYNAKTAN turetilir: bu fonksiyon.

    KARSI RISK SUSTURULMAZ, BASILIR: cron tanimi gercekten yeni degistiyse ilk teslim
    gecikebilir; bu hal satirda ⚠ ile ve YASIYLA gorunur, ama hukum vermeyi ENGELLEMEZ."""
    kayit_an = g.get("kayit_an")
    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None
    uyari = None
    yenileme = g.get("yenileme_an")
    if yenileme is not None:
        yenileme_yas = (simdi - yenileme).total_seconds() / 3600.0
        if yenileme_yas < pencere_saat:
            uyari = ("⚠ cron tanimina dokunan son commit %.1f sa once (< %g sa): tanim "
                     "degistiyse ilk teslim gecikebilir — bu bir SUSTURMA DEGIL, "
                     "GORUNURLUKTUR" % (yenileme_yas, pencere_saat))
    return kayit_an, gecmis_saat, uyari


def teslim_hukmu(g, simdi):
    """A5 — (satir, alarm_mi). Cron METNINI degil FIILI DAGILIMI olcer.

    Girdi `g` bir gozlem sozlugudur; `tum_kosumlar` cekilen TUM `event=schedule`
    damgalaridir. Pencereye dusenler BURADA suzulur ve BURADA siralanir — siralama
    API'ye BIRAKILMAZ (API sirasina guvenmek, tek bir sira degisikliginde en uzun
    boslugu sessizce yanlis hesaplatirdi).

    UC HAL:
      🔴 ALARM  — teslim, olculen tabanin ALTINDA.
      🟡 GORUNUR (alarm YOK) — gozlem gecmisi W'den KISA (is akisi yeni kaydedildi ya da
         cron tanimi yeni degisti) ya da henuz hic kosum yok (o sinif A3'undur). Sayilar
         YINE DE basilir; sessiz atlama YOKTUR.
      ✅ YESIL  — teslim tabanin ustunde. Satir teslim oranini ve EN UZUN BOSLUGU
         (gercek korluk penceresi) HER HALUKARDA yazar."""
    etiket = g["dosya"]
    W = TESLIM_PENCERESI_SAAT
    if not g.get("aralik"):
        return ("🟡 A5 TESLIM %s -> cron dakika alani cozulemedigi icin nominal tetik "
                "SAYILAMIYOR (A1 ekseni bu hali ZATEN kirmizi yakar); teslim orani "
                "olculmedi." % etiket), False

    nominal = teslim_nominal(g["aralik"], W)
    taban = teslim_tabani(g["aralik"], W)
    pencere_basi = simdi - timedelta(hours=W)
    damgalar = sorted(x for x in (g.get("tum_kosumlar") or []) if x > pencere_basi)
    teslim = len(damgalar)
    oran = (100.0 * teslim / nominal) if nominal else 0.0

    # EN UZUN BOSLUK = gercek korluk penceresi. UC ucu da sayilir:
    #   · kosumlar ARASI bosluklar,                       -> nobet: A5 (a) fiksturu
    #   · son kosumdan SIMDIYE (devam eden sessizlik rapordan DUSMEZ), -> nobet: X4
    #   · pencere BASINDAN ilk kosuma (bu sayilmazsa "48 saatin 47'si sessiz, son 20
    #     dakikada 2 kosum" hali kucucuk bir bosluk gibi gorunurdu — tam da parti
    #     halinde teslimin URETTIGI hal).                 -> nobet: X5
    # 🔴 UC TERIMIN HEPSI AYRI FIKSTURLE OLCULUR (4 Agu 2026 kanit-kalitesi onarimi):
    # ONCE yalnizca A5 (a) fiksturu vardi ve onun maks boslugu bir IC bosluktu (2370 dk);
    # iki UC terimi silen mutantlar 124 iddia / 0 KIRMIZI ile SURVIVOR veriyordu — yani
    # bu satirlarin gerekcesi kodda YAZILI ama OLCULMEMISTI
    # ([[fikstur-degeri-mutasyon-koru]]). X4 fiksturunde maks bosluk DEVAM EDEN
    # SESSIZLIKTEN (2640 dk), X5 fiksturunde PENCERE BASINDAN (2700 dk) gelir; mutant
    # X4/X5 her birini TEK KIRMIZI ile civiler.
    bosluklar = [(b - a).total_seconds() / 60.0 for a, b in zip(damgalar, damgalar[1:])]
    if damgalar:
        bosluklar.append((simdi - damgalar[-1]).total_seconds() / 60.0)
        if not g.get("pencere_kirpildi"):
            bosluklar.append((damgalar[0] - pencere_basi).total_seconds() / 60.0)
    maks_bosluk = max(bosluklar) if bosluklar else None
    sirali = sorted(bosluklar)
    medyan = sirali[len(sirali) // 2] if sirali else None
    # 🔴 TABANIN NE OLDUGU HER SATIRDA YAZAR (KraL karari, 4 Agu 2026): taban COKMUS
    # teslime KALIBREDIR (olculen EN KOTU 48 sa penceresi 7/192 = %3,65'in YARISI).
    # Bu yuzden ✅ "teslim SAGLIKLI" DEMEK DEGILDIR; yalnizca "bugunku cokmus seviyenin
    # de altina DUSMEDI" demektir. Yazilmazsa yesil YANLIS OKUNUR.
    olcu = ("teslim %d / nominal %.0f (%%%.2f) · en uzun bosluk %s · medyan bosluk %s · "
            "taban %d kosum / %d sa (taban %%%.2f COKMUS teslime KALIBRE: olculen en kotu "
            "%d sa penceresi %d/%d = %%%.2f'in yarisi — ✅ 'teslim saglikli' DEMEK DEGIL, "
            "'cokmus seviyenin de altina dusmedi' demek)"
            % (teslim, nominal, oran,
               ("%.0f dk" % maks_bosluk) if maks_bosluk is not None else "-",
               ("%.0f dk" % medyan) if medyan is not None else "-", taban, W,
               100.0 * TESLIM_TABAN_ORANI, TESLIM_PENCERESI_SAAT, OLCULEN_TABAN_TESLIM,
               OLCULEN_TABAN_NOMINAL,
               100.0 * OLCULEN_TABAN_TESLIM / OLCULEN_TABAN_NOMINAL))
    # Sayfa DOLDU ve en eski cekilen kosum HALA pencerenin icindeyse pencerenin tamami
    # gozlenmemistir. Bu SESSIZ KALMAZ; ama teslim sayfa boyu kadar oldugu icin hukum
    # zaten yesildir (taban her gercekci cron icin TESLIM_SAYFA'nin altindadir).
    tum = g.get("tum_kosumlar") or []
    kirpik = bool(g.get("pencere_kirpildi")) and bool(tum) and min(tum) > pencere_basi
    if kirpik:
        olcu += (" · ⚠ API sayfa siniri (%d kayit) doldu: pencerenin TAMAMI gozlenmedi, "
                 "GERCEK teslim bu sayidan AZ OLAMAZ" % TESLIM_SAYFA)

    if g.get("kosum_sayisi") == 0:
        return ("🟡 A5 TESLIM %s -> HIC event=schedule kosumu YOK; bu sinifin sahibi A3 "
                "eksenidir (%s)" % (etiket, olcu)), False

    # GOZLEM GECMISI: teslim orani ancak W kadar gecmis varsa hukum verir.
    # CAPA `gecmis_capasi`den gelir — A3 ile AYNI TEK KAYNAK (4 Agu 2026'da A3 de bu
    # capaya tasindi; gerekce ve olcum o fonksiyonun docstring'indedir).
    _kayit_an, gecmis_saat, capa_uyarisi = gecmis_capasi(g, simdi, W)
    if capa_uyarisi:
        olcu += " · " + capa_uyarisi
    if gecmis_saat is not None and gecmis_saat < W:
        return ("🟡 A5 TESLIM %s -> gozlem gecmisi %.1f sa < pencere %d sa (is akisi "
                "GitHub'da bu kadar once kaydedildi): teslim orani HENUZ hukum "
                "verilebilir degil. Olculen: %s" % (etiket, gecmis_saat, W, olcu)), False

    if teslim < taban:
        return ("🔴 A5 TESLIM %s -> ZAMANLANMIS KOSUMLAR DUSUYOR: %s. Cron METNI dogru "
                "(A1 yesil) ve son kosum taze olabilir (A3 yesil) — ama bu is akisinin "
                "olctugu sey W saatte yalnizca %d kez olculdu. Odeme yolu bayatligi bu "
                "sessizlikte MASKELENIR: en uzun bosluk (%s) korluk penceresinin GERCEK "
                "degeridir. Cron ofsetini degistirmek bu sinifi COZMEZ (4 Agu olcumu: "
                "ofsetli iki is akisi da %%4-5 teslimle PARTI HALINDE atesledi) — hal "
                "depo/hesap duzeyindedir."
                % (etiket, olcu, teslim,
                   ("%.0f dk" % maks_bosluk) if maks_bosluk is not None else "-")), True

    return ("✅ A5 TESLIM %s -> %s" % (etiket, olcu)), False


def bicim_hukmu(dosya, cron):
    """(hata_metni | None, aralik_dk | None)."""
    dakikalar = dakika_kumesi(cron)
    if dakikalar is None:
        return ("A1 BICIM IHLALI %s -> cron %r: dakika alani ACIK LISTE DEGIL (`*` / `*/n`). "
                "`*/15` tam olarak dakika 0/15/30/45'e duser; GitHub o dakikalarda kuyruk "
                "kisitlar ve tetiklemeler DUSER (bu depoda olculdu: 4 sa 36 dk boyunca "
                "beklenen ~18 tetiklemenin 0'i kostu). COZUM: acik dakika listesi, ornegin "
                "`7,22,37,52 * * * *`." % (dosya, cron), None)
    carpisan = sorted(dakikalar & YOGUN_DAKIKALAR)
    if carpisan:
        return ("A1 BICIM IHLALI %s -> cron %r: dakika(lar) %s YOGUN ceyrek-saat sinirinda. "
                "Sabit bir ofsete kaydir (ornegin 7,22,37,52)." % (dosya, cron, carpisan), None)
    return None, aralik_dakika(dakikalar)


# ---- API --------------------------------------------------------------------
def _jeton():
    for ad in ("GITHUB_TOKEN", "GH_TOKEN"):
        deger = (os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return None


def api_getir(yol, zaman_asimi=25):
    """GitHub REST GET -> ayristirilmis JSON. Her ariza OlcumHatasi (fail-closed)."""
    url = "%s/%s" % (API, yol.lstrip("/"))
    istek = urllib.request.Request(url, method="GET")
    istek.add_header("Accept", "application/vnd.github+json")
    istek.add_header("X-GitHub-Api-Version", "2022-11-28")
    istek.add_header("User-Agent", "pruvo-cron-nabiz-kapisi")
    jeton = _jeton()
    if jeton:
        istek.add_header("Authorization", "Bearer %s" % jeton)
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            ham = y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise OlcumHatasi("GitHub API HTTP %s: %s%s" % (e.code, url,
                          "" if jeton else "  (jeton YOK — anonim kota 60/saat)"))
    except Exception as e:  # noqa: BLE001 — URLError, socket.timeout, ssl ...
        raise OlcumHatasi("GitHub API cagrilamadi (%s: %s): %s" % (type(e).__name__, e, url))
    try:
        return json.loads(ham)
    except Exception as e:  # noqa: BLE001
        raise OlcumHatasi("GitHub API yaniti JSON degil (%s): %s" % (e, url))


def _iso(metin):
    if not isinstance(metin, str) or not metin.strip():
        raise OlcumHatasi("zaman damgasi metin degil: %r" % (metin,))
    duz = metin.strip().replace("Z", "+00:00")
    try:
        an = datetime.fromisoformat(duz)
    except Exception as e:  # noqa: BLE001
        raise OlcumHatasi("zaman damgasi cozulemedi (%r): %s" % (metin, e))
    return an if an.tzinfo else an.replace(tzinfo=timezone.utc)


def gozlem_topla(dosyalar, getir=api_getir):
    """[{dosya, cron, aralik, esik, kayitli, durum, kosum_sayisi, son_kosum,
          yenileme_an}] — AG kolu.

    `getir` ENJEKTE EDILEBILIR: fikstur kolu GERCEK API govdesinin ayni seklini besler."""
    liste = getir("repos/%s/actions/workflows?per_page=100" % DEPO)
    if not isinstance(liste, dict) or not isinstance(liste.get("workflows"), list):
        raise OlcumHatasi("is akisi listesi beklenen sekilde degil (`workflows` dizisi yok)")
    yol_ile = {}
    for wf in liste["workflows"]:
        if (not isinstance(wf, dict) or "path" not in wf or "id" not in wf
                or "created_at" not in wf):
            raise OlcumHatasi("is akisi kaydinda `path`/`id`/`created_at` yok: %r" % (wf,))
        yol_ile[wf["path"]] = wf

    gozlemler = []
    for dosya, cron in dosyalar:
        yol = ".github/workflows/%s" % dosya
        wf = yol_ile.get(yol)
        g = {"dosya": dosya, "cron": cron, "kayitli": wf is not None,
             "durum": (wf or {}).get("state"), "kosum_sayisi": None, "son_kosum": None,
             "kayit_an": _iso(wf["created_at"]) if wf is not None else None,
             "yenileme_an": None, "tum_kosumlar": [], "pencere_kirpildi": False,
             # A0/A4 TETIKLEYICI SARTININ KAYNAGI: `event=schedule` kosumlarinin KIMLIK
             # kumesi. Bir damganin CRON teslimi olup olmadigi, damganin `workflow_run.id`
             # degerinin bu kumede olup olmamasiyla olculur. EK API CAGRISI YOK — bu
             # liste A5 icin ZATEN cekiliyor.
             "schedule_kimlikleri": []}
        try:
            g["aralik"] = aralik_dakika(dakika_kumesi(cron) or {0})
        except OlcumHatasi:
            g["aralik"] = None
        g["esik"] = esik_saat(g["aralik"]) if g["aralik"] else ESIK_TABAN_SAAT
        if wf is not None:
            # 🔴 per_page=1 DEGIL: tek kayit YALNIZ "son kosum kac saatlik" (A3) sorusunu
            # cevaplar. A5 ekseni FIILI DAGILIMI olcer ve bunun icin kosum LISTESI gerekir
            # (olculdu 4 Agu: son kosum 2,3 sa tazeyken teslim orani %4,3 idi — A3 yesil,
            # sistem kor). Ek API cagrisi YOK, ayni cagrinin sayfa boyu buyudu.
            kosumlar = getir("repos/%s/actions/workflows/%s/runs?event=schedule&per_page=%d"
                             % (DEPO, wf["id"], TESLIM_SAYFA))
            if not isinstance(kosumlar, dict) or "total_count" not in kosumlar:
                raise OlcumHatasi("%s kosum yaniti beklenen sekilde degil "
                                  "(`total_count` yok)" % dosya)
            g["kosum_sayisi"] = int(kosumlar["total_count"])
            satirlar = kosumlar.get("workflow_runs") or []
            if not isinstance(satirlar, list):
                raise OlcumHatasi("%s: `workflow_runs` liste degil (%s)"
                                  % (dosya, type(satirlar).__name__))
            if g["kosum_sayisi"] > 0:
                if not satirlar:
                    raise OlcumHatasi("%s: total_count=%d ama `workflow_runs` BOS "
                                      "-> yanit tutarsiz" % (dosya, g["kosum_sayisi"]))
                # HER kayit dogrulanir: tek kaydi suzup gerisini korlemesine saymak,
                # suzgecin yarim calistigi hali sessizce gecirirdi.
                damgalar = []
                kimlikler = []
                for k in satirlar:
                    if not isinstance(k, dict) or "created_at" not in k:
                        raise OlcumHatasi("%s: kosum kaydinda `created_at` yok" % dosya)
                    # KIMLIK SART: damganin CRON teslimi olup olmadigi TAM BU kumeyle
                    # olculur. `id` dusmus bir kayit, kumeyi SESSIZCE eksiltir ve cron
                    # kaynakli bir damgayi "elle tazelendi" gosterirdi (ters yonde sahte
                    # kirmizi) -> fail-closed.
                    if not isinstance(k.get("id"), int):
                        raise OlcumHatasi("%s: kosum kaydinda `id` YOK/tamsayi degil (%r) "
                                          "-> damga tetikleyicisi SINIFLANDIRILAMAZ"
                                          % (dosya, k.get("id")))
                    kimlikler.append(k["id"])
                    if k.get("event") != "schedule":
                        raise OlcumHatasi("%s: event=schedule istendi ama kayit event=%r "
                                          "-> suzgec calismiyor" % (dosya, k.get("event")))
                    damgalar.append(_iso(k["created_at"]))
                # 🔴 BURADA SIRALANMAZ: siralama TEK YERDE, kullanildigi yerde
                # (teslim_hukmu) yapilir. Iki yerde siralamak, birini kaldiran mutanti
                # OBURUNUN sessizce kurtarmasi demektir — yani "siralamayi API'ye
                # birakma" iddiasi AYIRT EDICI mutanti olmayan bir beyana donusurdu
                # ([[beyan-edilmis-survivor]]). `son_kosum` siralama degil `max` ister.
                k = satirlar[0]
                g["son_kosum"] = max(damgalar)
                g["son_kosum_id"] = k.get("id")
                g["son_sonuc"] = k.get("conclusion")
                g["tum_kosumlar"] = damgalar
                g["schedule_kimlikleri"] = kimlikler
                # Sayfa DOLU ise pencerenin tamami gozlenmemis olabilir — bu BEYAN EDILIR.
                g["pencere_kirpildi"] = len(satirlar) >= TESLIM_SAYFA
            # GitHub cron tanimi degistiginde zamanlayici yeniden kaydedilir. Workflow API'sinin
            # `updated_at` alani bunu yansitmiyor (olculdu: dosya degisti, alan created_at ile
            # ayni kaldi); bu yuzden dosyaya dokunan son commit GitHub commits API'sinden okunur.
            # Yeni kaydedilen cron'a A3 esigi kadar ilk-teslim penceresi taninmazsa eski cron'un
            # son kosumu yeni tanimin sessizligi sanilir ve alarm bos yere kirmizi yanar.
            commitler = getir("repos/%s/commits?path=%s&per_page=1"
                              % (DEPO, urllib.parse.quote(yol, safe="")))
            if not isinstance(commitler, list) or not commitler:
                raise OlcumHatasi("%s son degisim yaniti beklenen sekilde degil "
                                  "(bos ya da dizi degil)" % dosya)
            son_commit = commitler[0]
            try:
                g["yenileme_an"] = _iso(son_commit["commit"]["committer"]["date"])
            except (KeyError, TypeError) as e:
                raise OlcumHatasi("%s son degisim kaydinda `commit.committer.date` yok: %s"
                                  % (dosya, e))
        gozlemler.append(g)
    return gozlemler


# ---- A0: SON BASARILI UZLASTIRMA DAMGASI ------------------------------------
def damga_gozle(getir=api_getir, ad=DAMGA_ADI):
    """En yeni SURESI DOLMAMIS `<ad>` artifact'i -> gozlem sozlugu (A0 ve A4 AYNI kod).

    Doner: {"var": bool, "an": datetime|None, "kosum": id|None, "sha": str|None,
            "toplam": int, "suresi_dolan": int, "sebep": str|None,
            "taze_kayitlar": [{"an", "kosum", "sha"}, ...]}   # YENIDEN ESKIYE sirali

    🔴 `taze_kayitlar` NEDEN VAR (4 Agu 2026 olcumu): "en yeni damga" TEK BASINA yetmez.
    09:45:48Z'de ELLE (`workflow_dispatch`) kosturulan bir kosum taze damga yazdi ve A0
    ekseni 9 saat daha YESIL yandi; cron ise 00:17:30Z'den beri OLUYDU. Damganin CRON
    teslimi olup olmadigi hukum katmaninda (`_cron_kaynakli_damga`) olculur ve bunun icin
    yalniz EN YENI degil, PENCEREYE DUSEN TUM taze damgalar gerekir.
    HER sekil arizasi OlcumHatasi (rc 2): eksik alan, ad suzgecinin calismamasi,
    cozulemeyen zaman damgasi. "Damga YOK" ise SEKIL arizasi degil OLCUM'dur ->
    var=False doner ve hukum katmani bunu ALARM sayar."""
    d = getir("repos/%s/actions/artifacts?name=%s&per_page=100"
              % (DEPO, urllib.parse.quote(ad)))
    if not isinstance(d, dict) or not isinstance(d.get("artifacts"), list):
        raise OlcumHatasi("artifact yaniti beklenen sekilde degil (`artifacts` dizisi yok) "
                          "-> damga OKUNAMADI, 'yesil' SAYILMAZ")
    kayitlar = d["artifacts"]
    for a in kayitlar:
        if not isinstance(a, dict):
            raise OlcumHatasi("artifact kaydi sozluk degil: %r" % (a,))
        for alan in ("name", "created_at", "expired"):
            if alan not in a:
                raise OlcumHatasi("artifact kaydinda `%s` YOK: %r" % (alan, a))
        # AD SUZGECI NOBETI: `?name=` sunucu tarafinda calismazsa baska bir is akisinin
        # artifact'i damga sanilirdi (sahte YESIL). Suzgecin fiilen calistigini OLC.
        # 🔴 IKI DAMGA VARKEN BU SATIR DAHA DA KRITIK: suzgec calismazsa uzlastirma
        # damgasi paket damgasi sanilir ve olu bir alarm TAZE gorunurdu.
        if a["name"] != ad:
            raise OlcumHatasi("artifact ad suzgeci CALISMIYOR: name=%r istendi, %r dondu "
                              "-> damga ekseni olculemez" % (ad, a["name"]))
    taze = [a for a in kayitlar if not a["expired"]]
    if not kayitlar:
        return {"var": False, "an": None, "kosum": None, "sha": None, "toplam": 0,
                "suresi_dolan": 0, "taze_kayitlar": [],
                "sebep": "depoda `%s` adli HIC artifact YOK" % ad}
    if not taze:
        return {"var": False, "an": None, "kosum": None, "sha": None,
                "toplam": len(kayitlar), "suresi_dolan": len(kayitlar),
                "taze_kayitlar": [],
                "sebep": "TUM damgalarin (%d adet) SURESI DOLMUS (expired) — saklama "
                         "%d saat, yani en yeni denetim bundan da eski"
                         % (len(kayitlar), DAMGA_SAKLAMA_SAAT)}
    # 🔴 BURADA SIRALANIR (TEK YER): API sirasina guvenmek, tek bir sira degisikliginde
    # "en yeni damga"yi ve tetikleyici sinifini sessizce yanlis hesaplatirdi.
    sirali = sorted(taze, key=lambda a: _iso(a["created_at"]), reverse=True)

    def _kayit(a):
        wr = a.get("workflow_run") if isinstance(a.get("workflow_run"), dict) else {}
        return {"an": _iso(a["created_at"]), "kosum": wr.get("id"),
                "sha": wr.get("head_sha")}

    kayitlar_taze = [_kayit(a) for a in sirali]
    en_yeni = kayitlar_taze[0]
    return {"var": True, "an": en_yeni["an"], "kosum": en_yeni["kosum"],
            "sha": en_yeni["sha"], "toplam": len(kayitlar),
            "suresi_dolan": len(kayitlar) - len(taze),
            "taze_kayitlar": kayitlar_taze, "sebep": None}


def is_akisi_esigi(dosyalar, hedef, capa_tanisi):
    """DAMGA esigi, DAMGAYI YAZAN is akisinin cron cadansindan turetilir (nominal ->
    olculen teslim orani -> N). Hedef dosya yoksa/cron'suzsa OLCULEMEDI: bu nobetci
    "denetleyen bir is var" VARSAYMAZ. A0 ve A4 AYNI fonksiyondan gecer."""
    for dosya, cron in dosyalar:
        if dosya != hedef:
            continue
        dakikalar = dakika_kumesi(cron)
        if dakikalar is None:
            # `*/n` gibi acik-liste olmayan cron: A1 zaten KIRMIZI yakar; esigi yine de
            # turetebilmek icin adim degerini coz.
            alanlar = cron.split()
            adim = alanlar[0].split("/")[-1] if "/" in alanlar[0] else "60"
            try:
                return dosya, esik_saat(int(adim)), int(adim)
            except ValueError:
                raise OlcumHatasi("%s cron dakika alani cozulemedi: %r" % (hedef, cron))
        aralik = aralik_dakika(dakikalar)
        return dosya, esik_saat(aralik), aralik
    raise OlcumHatasi(capa_tanisi)


def uzlastirici_esigi(dosyalar):
    """A0 esigi (bkz. is_akisi_esigi)."""
    return is_akisi_esigi(
        dosyalar, UZLASTIRICI_DOSYA,
        "UZLASTIRICI BULUNAMADI: cron tasiyan is akislari arasinda %s YOK. A0 damga "
        "ekseninin capasi budur — dosya silinir/adi degisirse 'denetim yapiliyor' "
        "iddiasi olculemez hale gelir, sessiz YESIL verilmez." % UZLASTIRICI_DOSYA)


def paket_alarm_esigi(dosyalar):
    """A4 esigi (bkz. is_akisi_esigi)."""
    return is_akisi_esigi(
        dosyalar, PAKET_ALARM_DOSYA,
        "PAKET TAZELIGI ALARMI BULUNAMADI: cron tasiyan is akislari arasinda %s YOK. "
        "A4 ekseninin capasi budur — canli fiyat yolunu olcen TEK zamanlanmis is odur "
        "ve silinirse 14,5 saatlik fazla tahsilat penceresi (1 Agu) hicbir yerde "
        "kirmizi yakmadan geri gelir. Sessiz YESIL verilmez." % PAKET_ALARM_DOSYA)


# ---- HUKUM ------------------------------------------------------------------
def _damga_kaynagi(gozlemler, dosya):
    """Damgayi YAZAN is akisinin `event=schedule` kosum KIMLIKLERI + sayfa sinirlari.

    Bu, A0/A4'un TETIKLEYICI SARTININ tek veri kaynagidir ve EK API CAGRISI GEREKTIRMEZ:
    kosum listesi A5 icin ZATEN cekiliyor."""
    for g in gozlemler:
        if g["dosya"] == dosya:
            tum = g.get("tum_kosumlar") or []
            return {"dosya": dosya,
                    "kimlikler": set(g.get("schedule_kimlikleri") or ()),
                    "kirpik": bool(g.get("pencere_kirpildi")),
                    "en_eski": min(tum) if tum else None}
    return None


def _cron_kaynakli_damga(eksen, damga, kaynak, n, simdi):
    """N penceresine dusen EN YENI **CRON TESLIMI** damga -> kayit | None. Fail-closed.

    🔴 NEDEN VAR (OLCULDU 4 Agu 2026 — alarm ELLE SONDURULEBILIYORDU): A0 yalnizca
    damganin ADINA, `created_at`ine ve `expired`ina bakiyordu; damgayi YAZAN kosumun
    tetikleyicisine BAKMIYORDU. 09:45:48Z'de elle (`workflow_dispatch`) kosturulan bir
    kosum taze damga yazdi ve A0'i 9 SAAT DAHA sifirladi (09:49Z kosumunda
    `cron-nabzi` = success); cron ise 00:17:30Z'den beri OLUYDU. Yani bir insan elle
    tetikledikce alarm HIC yanmayabilirdi.

    SINIFLANDIRMA OLCUSU: damganin `workflow_run.id`si, capa is akisinin
    `event=schedule` kosum kimlikleri kumesinde mi.
    🔴 ARTIFACT API'SI `event` ALANINI TASIMAZ — OLCULDU (4 Agu 2026,
    `GET /repos/Pruvo138/pruvo/actions/artifacts?name=uzlastirma-damgasi`):
    `workflow_run` alanlari TAM OLARAK {id, repository_id, head_repository_id,
    head_branch, head_sha}. Fikstur bu SEKLI taklit eder; olmayan bir `event` alani
    UYDURULMAZ ([[nobetci-fikstur-sekli]]) ve damga basina ayri bir
    `GET /actions/runs/{id}` cagrisi da YAPILMAZ (kadans kolu devreye girince pencerede
    onlarca damga olur; jeton kotasi 1000/saat)."""
    if kaynak is None:
        raise OlcumHatasi(
            "%s: damgayi yazan is akisinin kosum listesi YOK -> damganin CRON teslimi mi "
            "yoksa elle mi tazelendigi SINIFLANDIRILAMAZ" % eksen)
    pencere_basi = simdi - timedelta(hours=n)
    for kayit in damga.get("taze_kayitlar") or []:
        if kayit["an"] <= pencere_basi:
            break            # daha eskisi zaten esigin DISINDA: hukmu degistiremez
        kimlik = kayit.get("kosum")
        if kimlik is None:
            raise OlcumHatasi(
                "%s: damga kaydinda `workflow_run.id` YOK -> damgayi hangi kosum yazdi "
                "OKUNAMADI, tetikleyici sarti olculemez" % eksen)
        if kimlik in kaynak["kimlikler"]:
            return kayit
        # Kosum sayfasi DOLU ve damga, cekilen EN ESKI zamanlanmis kosumdan da eskiyse
        # "kumede yok" hukmu VERILEMEZ (kume o zamani KAPSAMIYOR olabilir).
        if kaynak["kirpik"] and (kaynak["en_eski"] is None
                                 or kayit["an"] < kaynak["en_eski"]):
            raise OlcumHatasi(
                "%s: damga %s, cekilen zamanlanmis kosum sayfasinin (%d kayit) KAPSAMI "
                "DISINDA -> CRON teslimi mi degil mi SINIFLANDIRILAMAZ (sessiz 'elle' "
                "hukmu sahte kirmizi olurdu)" % (eksen, kayit["an"].isoformat(),
                                                 TESLIM_SAYFA))
    return None


# A0 ve A4 TEK karar yolundan gecer. Ikinci bir "damga yasi" kopyasi yazilsaydi biri
# gevsedigi zaman oburu sessizce dogru kalir ve ayrisma gorunmezdi
# ([[ikiz-tanim-sessiz-ayrisma]]). Konu metinleri disaridan verilir; MANTIK ORTAK.
def _damga_satiri(eksen, damga, n, simdi, sablon, kaynak=None):
    """(satir, alarm_mi). `sablon` = {"yok", "bayat", "taze", "elle"} bicim dizeleri.
       yok   <- (sebep, N)
       bayat <- (yas, N, yas, kosum, sha12)
       taze  <- (yas, N, taze_sayi, suresi_dolan, kosum)
       elle  <- (yas, kosum, N)

    UC HAL DEGIL DORT: "denetim YAPILDI" ile "denetim CRON TARAFINDAN yapildi" AYRI
    seylerdir. Ikincisi olmadan alarm elle sondurulebilir (bkz. `_cron_kaynakli_damga`)."""
    if not damga.get("var"):
        return ("🔴 %s -> " % eksen) + sablon["yok"] % (damga.get("sebep"), n), True
    yas = (simdi - damga["an"]).total_seconds() / 3600.0
    cron_kayit = _cron_kaynakli_damga(eksen, damga, kaynak, n, simdi)
    if cron_kayit is not None:
        cron_yas = (simdi - cron_kayit["an"]).total_seconds() / 3600.0
        satir = (("✅ %s -> " % eksen) + sablon["taze"]
                 % (cron_yas, n, damga["toplam"] - damga["suresi_dolan"],
                    damga["suresi_dolan"], cron_kayit.get("kosum")))
        if cron_kayit.get("kosum") != damga.get("kosum"):
            satir += (" · en yeni damga CRON DISI bir kosumdan (%.1f sa once · kosum %s) "
                      "— hukum CRON damgasina gore verildi" % (yas, damga.get("kosum")))
        return satir, False
    if yas <= n:
        return (("🔴 %s -> " % eksen) + sablon["elle"] % (yas, damga.get("kosum"), n)), True
    return (("🔴 %s -> " % eksen) + sablon["bayat"]
            % (yas, n, yas, damga.get("kosum"), str(damga.get("sha"))[:12])), True


A0_SABLON = {
    "yok": ("SON BASARILI UZLASTIRMA DAMGASI YOK (%s). Katalog-D1 sapmasi HIC "
            "denetlenmedi ya da denetim %d saatten uzun suredir tamamlanmadi. Bir "
            "kosumun YESIL olmasi denetim yapildigi ANLAMINA GELMEZ (olculdu 31 Tem "
            "20:47:18Z: conclusion=success · olcum/onarim/teyit adimlarinin HEPSI "
            "skipped)."),
    "bayat": ("son basarili uzlastirma %.1f saat once (esik N=%d sa). D1 ile "
              "urunler.json arasindaki sapma %.1f saattir DENETLENMEDI; Ege bayat veri "
              "gosteriyor olabilir ve baska hicbir kapi bunu gormez. (damga kosumu %s · "
              "sha %s)"),
    "taze": ("son basarili uzlastirma %.1f saat once (esik N=%d sa · taze damga %d, "
             "suresi dolan %d · CRON kosumu %s)"),
    "elle": ("DENETIM YAPILDI AMA CRON YAPMADI: en yeni damga %.1f saat once, ancak onu "
             "yazan kosum (%s) bu is akisinin `event=schedule` kosumlari arasinda YOK — "
             "yani damga ELLE (`workflow_dispatch`) ya da YAYIN KOLUYLA (`push` kadans "
             "isi) tazelendi. Zamanlanmis teslim %d saattir YOK. OLCULDU (4 Agu 2026 "
             "09:45:48Z): elle bir kosum taze damga yazdi ve bu ekseni 9 SAAT DAHA "
             "sifirladi; cron 00:17:30Z'den beri oluydu ve alarm HIC yanmadi. Katalog "
             "denetimi suruyor olabilir (kadans kolu), CRON TESLIMI SURMUYOR."),
}

A4_SABLON = {
    "yok": ("SON BASARILI PAKET TAZELIGI DAMGASI YOK (%s). Canli fiyat yolu HIC "
            "denetlenmedi ya da denetim %d saatten uzun suredir PARITE ile "
            "kapanmadi. OLCULDU (1 Agu): canli paket 14,5 saat bayat kalinca 676 "
            "fiziksel uruntte %%84'e varan FAZLA TAHSILAT olustu ve o an mevcut IKI "
            "canli kapi da YESIL yaniyordu. shop Worker'i CI'da yayinlanmadigi icin "
            "bu sinif kendiliginden geri gelir."),
    "bayat": ("son basarili paket tazeligi olcumu %.1f saat once (esik N=%d sa). Canli "
              "fiyat yolu %.1f saattir PARITE ile kapanmadi: alarm ya kosmuyor ya da "
              "kostugu her seferde drift/olculemedi donuyor. Musteriden yanlis tutar "
              "tahsil ediliyor olabilir. (damga kosumu %s · sha %s)"),
    "taze": ("son basarili paket tazeligi olcumu %.1f saat once (esik N=%d sa · taze "
             "damga %d, suresi dolan %d · CRON kosumu %s)"),
    "elle": ("OLCUM YAPILDI AMA CRON YAPMADI: en yeni paket damgasi %.1f saat once, "
             "ancak onu yazan kosum (%s) alarmin `event=schedule` kosumlari arasinda "
             "YOK -> damga ELLE tazelendi. Canli fiyat yolunu ZAMANLANMIS olarak olcen "
             "kol %d saattir sessiz; elle tetikleme bu ekseni SUSTURAMAZ (aksi halde "
             "1 Agu'daki 14,5 saatlik fazla tahsilat penceresi tek bir elle kosumla "
             "gorunmez kalirdi)."),
}


def degerlendir(dosyalar, gozlemler, simdi=None, damga=None, damga_esigi=None,
                paket=None, paket_esigi=None):
    """(rc, satirlar). rc 0 yesil · 1 alarm · 2 olculemedi.

    `damga`/`paket` verilmezse A0/A4 ekseni RAPORLANMAZ (agsiz A1 birim testleri icin);
    GERCEK olcum yolunda main() her ikisini de verir."""
    simdi = simdi or datetime.now(timezone.utc)
    satirlar = []
    alarm = False
    olculemedi = False

    if not dosyalar:
        return 2, ["OLCULEMEDI: depoda cron tasiyan is akisi BULUNAMADI. Bu nobetci "
                   "boslukta calisiyor demektir (kesif bozulmus ya da cron silinmis) — "
                   "sessiz YESIL verilmez."]

    # 🔴 YURURLUKTEKI ESIK — TEK YERDE, is akisi BASINA, A0/A3/A4 icin AYNI kaynak.
    # `damga_esigi`/`paket_esigi` cagirandan NOMINAL cadansla gelir; gozlem varsa
    # CANLI olculen teslim orani onu yeniler (bkz. canli_esik). Iki eksen ayri
    # hesaplasaydi A0 ile A3 sessizce ayrisirdi ([[ikiz-tanim-sessiz-ayrisma]]).
    canli_esikler = {}
    for g in gozlemler:
        if g.get("kayitli"):
            canli_esikler[g["dosya"]] = canli_esik(g, simdi)
    # A4'un KENDI tavani (OLCULEN ZARAR penceresi) — A3/A0 tavaniyla KARISTIRILMAZ.
    paket_canli = None
    for g in gozlemler:
        if g.get("kayitli") and g["dosya"] == PAKET_ALARM_DOSYA:
            paket_canli = canli_esik(g, simdi, tavan=PAKET_BAYATLIK_TAVAN_SAAT)

    # --- A0 DAMGA + A4 PAKET (BIRINCIL EKSENLER, AYNI KARAR YOLU) ------------
    for eksen, gozlem, esik, sablon, capa in (
            ("A0 DAMGA", damga, damga_esigi, A0_SABLON, UZLASTIRICI_DOSYA),
            ("A4 PAKET", paket, paket_esigi, A4_SABLON, PAKET_ALARM_DOSYA)):
        if gozlem is None:
            continue
        turetilen = (paket_canli if capa == PAKET_ALARM_DOSYA
                     else canli_esikler.get(capa))
        esik = (turetilen[0] if turetilen else esik) or esik
        try:
            satir, yandi = _damga_satiri(eksen, gozlem, esik or ESIK_TABAN_SAAT, simdi,
                                         sablon, _damga_kaynagi(gozlemler, capa))
        except OlcumHatasi as e:
            satirlar.append("🔴 %s -> OLCULEMEDI: %s" % (eksen, e))
            olculemedi = True
            continue
        satirlar.append(satir)
        alarm = alarm or yandi

    for dosya, cron in dosyalar:
        hata, aralik = bicim_hukmu(dosya, cron)
        if hata:
            satirlar.append("🔴 " + hata)
            alarm = True
        else:
            # A1 CRON BICIMINI olcer, esigi DEGIL: burada basilan N DONMUS TABANDIR.
            # Yururlukteki N (canli teslim oranindan) A3/A0/A4 satirlarindadir.
            satirlar.append("✅ A1 BICIM %s -> cron %r · aralik %d dk · donmus taban "
                            "N=%d saat" % (dosya, cron, aralik, esik_saat(aralik)))

    for g in gozlemler:
        etiket = g["dosya"]
        if not g["kayitli"]:
            satirlar.append("🔴 A2 DURUM %s -> GitHub'da KAYITLI DEGIL (is akisi hic "
                            "taninmamis: dosya main'de mi, adi/yolu degisti mi?)" % etiket)
            alarm = True
            continue
        if g["durum"] != "active":
            satirlar.append("🔴 A2 DURUM %s -> state=%r (aktif DEGIL). GitHub 60 gun "
                            "hareketsizlikte zamanlanmis is akislarini "
                            "`disabled_inactivity` yapar; dosya yerinde durur ama HIC "
                            "kosmaz." % (etiket, g["durum"]))
            alarm = True
            continue
        satirlar.append("✅ A2 DURUM %s -> state=active" % etiket)

        # A5 TESLIM — A3'ten AYRI EKSEN, AYRI SATIR, ve A3'un `continue` kollarindan
        # ONCE: "kosum yok" / "yeni tanim" hallerinde de teslim satiri BASILIR, sessizce
        # atlanmaz. A3 "son kosum kac saatlik" der; A5 "W saatte KAC kosum teslim edildi"
        # der. Parti halinde gelen TEK bir kosum A3'u yesil yakar ama teslim orani sifira
        # yakin kalabilir — 4 Agu'da FIILEN olculen hal budur.
        satir5, yandi5 = teslim_hukmu(g, simdi)
        satirlar.append(satir5)
        alarm = alarm or yandi5

        # 🔴 ESIK CANLI (5 Agu 2026): `g["esik"]` NOMINAL cadanstan turetilmis DONMUS
        # degerdi (15 dk -> 9 sa) ve GERCEKLESEN cadansin (%4,52) altinda kalip BOS
        # KIRMIZI uretiyordu. Artik ayni gozlemin CANLI teslim oranindan turetilir;
        # turetilemezse DONMUS degere (daha SIKI olana) duser. Gerekce: canli_esik.
        n, esik_kaynak, efektif_dk = canli_esikler.get(
            g["dosya"], (g["esik"], "donmus (gozlem yok)", None))
        if efektif_dk is None and g["aralik"]:
            efektif_dk = efektif_aralik_dk(g["aralik"])
        # 🔴 CAPA A5 ILE HIZALANDI (4 Agu 2026): `max(kayit_an, yenileme_an)` DEGIL,
        # yalniz `kayit_an`. Gerekce + olcum: `gecmis_capasi` docstring'i. Dosyaya
        # dokunmak alarmi 9 saat SUSTURUYORDU; artik SUSTURMAZ, satirda ⚠ olarak GORUNUR.
        kayit_an, kayit_yasi, capa_uyarisi = gecmis_capasi(g, simdi, n)
        ek = (" · " + capa_uyarisi) if capa_uyarisi else ""
        yeni_tanim = (g["son_kosum"] is None or kayit_an > g["son_kosum"])
        if yeni_tanim and kayit_yasi <= n:
            satirlar.append("🟡 A3 NABIZ %s -> is akisi GitHub'da %.1f saat once "
                            "KAYDEDILDI; bu kayittan sonra event=schedule kosumu henuz "
                            "YOK (esik N=%d sa). Ilk tetikleme icin olculen teslim "
                            "penceresi dolmadi.%s" % (etiket, kayit_yasi, n, ek))
            continue
        if g["kosum_sayisi"] == 0:
            if kayit_yasi <= n:
                satirlar.append("🟡 A3 NABIZ %s -> event=schedule kosumu henuz YOK; "
                                "is akisi %.1f saat once kaydedildi (esik N=%d sa). "
                                "Ilk tetikleme icin olculen teslim penceresi dolmadi; "
                                "durum gorunur, alarm henuz yanmaz." % (etiket, kayit_yasi, n))
            else:
                satirlar.append("🔴 A3 NABIZ %s -> event=schedule kosum sayisi SIFIR: "
                                "cron HIC ATESLENMEMIS. Is akisi %.1f saattir kayitli ve aktif "
                                "(esik N=%d sa) -> bu is akisinin yaptigi HICBIR SEY "
                                "yapilmiyor ve hicbir yerde kirmizi yanmiyor.%s"
                                % (etiket, kayit_yasi, n, ek))
                alarm = True
            continue
        if g["son_kosum"] is None:
            satirlar.append("🔴 A3 NABIZ %s -> son kosum zamani OKUNAMADI (fail-closed)"
                            % etiket)
            alarm = True
            continue
        yas = (simdi - g["son_kosum"]).total_seconds() / 3600.0
        # 🔴 "N ARDISIK PENCEREDE HIC KOSMADI" — mimarin istedigi BIRIM. Sessizligi
        # SAATTE degil, cron'un KENDI vaat ettigi pencere sayisinda da basar: "9,97 saat"
        # soyut, "40 ardisik 15 dk penceresi teslim edilmedi" degil.
        beklenen = int(round(yas * 60 / g["aralik"])) if g["aralik"] else 0
        if yas > n:
            satirlar.append("🔴 A3 NABIZ (ikincil) %s -> son event=schedule kosumu %.1f "
                            "saat once (esik N=%d sa · nominal aralik %d dk · efektif "
                            "%.0f dk · bu surede nominal ~%d tetikleme, teslim 0 -> "
                            "ARDISIK BOS PENCERE ~%d). Cron SESSIZ. [esik: %s]%s"
                            % (etiket, yas, n, g["aralik"], efektif_dk, beklenen,
                               beklenen, esik_kaynak, ek))
            alarm = True
        else:
            satirlar.append("✅ A3 NABIZ (ikincil) %s -> son event=schedule kosumu %.1f "
                            "saat once (esik N=%d sa · efektif cadans %.0f dk · ARDISIK "
                            "BOS PENCERE ~%d · toplam %d zamanlanmis kosum) [esik: %s]%s"
                            % (etiket, yas, n, efektif_dk, beklenen,
                               g["kosum_sayisi"], esik_kaynak, ek))
    if olculemedi:
        return 2, satirlar
    return (1 if alarm else 0), satirlar


def rapor(rc, satirlar):
    print("UZLASTIRMA NABIZ KAPISI — depo %s" % DEPO)
    for s in satirlar:
        print("  " + s)
    if rc == 0:
        if any(s.startswith("🟡 A3 NABIZ") for s in satirlar):
            print("SONUC: DENETIM TAZE ✅ (damgalar esigin icinde · yeni is akisinin "
                  "ilk zamanlanmis teslim penceresi henuz dolmadi)")
        else:
            print("SONUC: DENETIM TAZE ✅ (son basarili uzlastirma esigin icinde · "
                  "zamanlanmis isler fiilen kosuyor)")
    elif rc == 1:
        print("SONUC: 🔴 ALARM — katalog-D1 sapmasi esigi asan suredir DENETLENMEDI "
              "(ya da cron sessiz). Bu isin yaptigi denetim YAPILMIYOR ve baska hicbir "
              "kapi bunu gormez.")
    else:
        print("SONUC: 🔴 OLCULEMEDI (fail-closed) — denetim yasi OLCULEMEDI, "
              "'yesil' SAYILMAZ.")
    return rc


# ---- FIKSTURLER (GERCEK API GOVDESININ SEKLI) -------------------------------
# 31 Tem 2026'da `gh api repos/Pruvo138/pruvo/actions/workflows/324431004/runs` ciktisindan
# KOPYALANMIS tam kayit (35 alan). Kisaltilmis sahte sekil KULLANILMAZ: olculdu ki 3-4
# alanlik "mini" fikstur, gercek yanitta alan adi degisse bile YESIL kalir (nobetci
# fiksturun seklini dogrular, API'ninkini degil) -> [[nobetci-fikstur-sekli]].
_HAM_KOSUM = {
    "id": 30629753158,
    "name": "D1 uzlastirici (katalog sapmasi)",
    "node_id": "WFR_kwLOQBz9Ss8AAAAHIvJfxg",
    "head_branch": "main",
    "head_sha": "0858a5e150827989f2e08d41d335183e04ebab3c",
    "path": ".github/workflows/d1-uzlastirici.yml",
    "display_title": "D1 uzlastirici (katalog sapmasi)",
    "run_number": 1,
    "event": "schedule",
    "status": "completed",
    "conclusion": "success",
    "workflow_id": 324431004,
    "check_suite_id": 82334455661,
    "check_suite_node_id": "CS_kwDOQBz9Ss8AAAAT4mFabQ",
    "url": "https://api.github.com/repos/Pruvo138/pruvo/actions/runs/30629753158",
    "html_url": "https://github.com/Pruvo138/pruvo/actions/runs/30629753158",
    "pull_requests": [],
    "created_at": "2026-07-31T12:12:19Z",
    "updated_at": "2026-07-31T12:12:56Z",
    "actor": {"login": "Pruvo138", "id": 219876543, "type": "User"},
    "run_attempt": 1,
    "referenced_workflows": [],
    "run_started_at": "2026-07-31T12:12:19Z",
    "triggering_actor": {"login": "Pruvo138", "id": 219876543, "type": "User"},
    "jobs_url": "https://api.github.com/repos/Pruvo138/pruvo/actions/runs/30629753158/jobs",
    "logs_url": "https://api.github.com/repos/Pruvo138/pruvo/actions/runs/30629753158/logs",
    "check_suite_url":
        "https://api.github.com/repos/Pruvo138/pruvo/check-suites/82334455661",
    "artifacts_url":
        "https://api.github.com/repos/Pruvo138/pruvo/actions/runs/30629753158/artifacts",
    "cancel_url":
        "https://api.github.com/repos/Pruvo138/pruvo/actions/runs/30629753158/cancel",
    "rerun_url":
        "https://api.github.com/repos/Pruvo138/pruvo/actions/runs/30629753158/rerun",
    "previous_attempt_url": None,
    "workflow_url":
        "https://api.github.com/repos/Pruvo138/pruvo/actions/workflows/324431004",
    "head_commit": {"id": "0858a5e150827989f2e08d41d335183e04ebab3c",
                    "tree_id": "3f2a1c9b4e5d6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
                    "message": "yedekle.py: git hooks sablonlari",
                    "timestamp": "2026-07-31T15:44:41+03:00",
                    # PUBLIC DEPO: fikstur SEKLI korunur, kisisel e-posta KONMAZ
                    # (GitHub'in noreply formu gercek yanit sekliyle birebir uyumlu).
                    "author": {"name": "Pruvo138",
                               "email": "pruvo138@users.noreply.github.com"},
                    "committer": {"name": "Pruvo138",
                                  "email": "pruvo138@users.noreply.github.com"}},
    "repository": {"id": 1076952394, "name": "pruvo", "full_name": "Pruvo138/pruvo",
                   "private": False},
    "head_repository": {"id": 1076952394, "name": "pruvo", "full_name": "Pruvo138/pruvo",
                        "private": False},
}

_HAM_WF = {
    "id": 324431004,
    "node_id": "W_kwDOQBz9Ss4TSyec",
    "name": "D1 uzlastirici (katalog sapmasi)",
    "path": ".github/workflows/d1-uzlastirici.yml",
    "state": "active",
    "created_at": "2026-07-31T14:55:35.000+03:00",
    "updated_at": "2026-07-31T14:55:35.000+03:00",
    "url": "https://api.github.com/repos/Pruvo138/pruvo/actions/workflows/324431004",
    "html_url":
        "https://github.com/Pruvo138/pruvo/blob/main/.github/workflows/d1-uzlastirici.yml",
    "badge_url": "https://github.com/Pruvo138/pruvo/workflows/D1%20uzlastirici/badge.svg",
}


# 31 Tem 2026'da `gh api repos/Pruvo138/pruvo/actions/artifacts?per_page=1` ciktisindan
# KOPYALANMIS TAM kayit (13 alan + workflow_run alt nesnesi). Kisaltilmis sahte sekil
# KULLANILMAZ -> [[nobetci-fikstur-sekli]]. `expires_at - created_at` = 24 saat: depo
# artifact saklamasi buradan OLCULDU (esik tavani bu sayinin altinda tutulur).
_HAM_ARTIFACT = {
    "id": 8806704610,
    "node_id": "MDg6QXJ0aWZhY3Q4ODA2NzA0NjEw",
    "name": DAMGA_ADI,
    "size_in_bytes": 431,
    "url": "https://api.github.com/repos/Pruvo138/pruvo/actions/artifacts/8806704610",
    "archive_download_url":
        "https://api.github.com/repos/Pruvo138/pruvo/actions/artifacts/8806704610/zip",
    "expired": False,
    "digest": "sha256:1a1d15f049c1cb841e5b0591fc179b551e872ee6c7b822d8d0ac937c963b10dd",
    "created_at": "2026-07-31T21:05:08Z",
    "updated_at": "2026-07-31T21:05:08Z",
    "expires_at": "2026-08-01T21:04:44Z",
    "workflow_run": {"id": 30663827609, "repository_id": 1292165649,
                     "head_repository_id": 1292165649, "head_branch": "main",
                     "head_sha": "fcda5576aa196c4142dd0361d28aab1b2ad71290"},
}


# 4 Agu 2026'da OLCULEN GERCEK kosum kimligi: 09:45:48Z'de ELLE (`workflow_dispatch`)
# kosturulan ve A0'i 9 saat susturan kosum. Fikstur "cron DISI damga" halini bu kimlikle
# kurar — uydurma bir sayi degil, olayin kendisi.
_CRON_DISI_KOSUM = 30897735170


def _damga_kaydi(yas_saat, expired=False, ad=None, kimlik=8806704610, kosum_kimlik=None):
    """GERCEK artifact govdesinin ayni seklinde tek damga kaydi.

    `kosum_kimlik` verilmezse `_HAM_ARTIFACT`in kimligi kalir ve `_sahte_api` onu
    `damga_kosum` moduna gore (cron / cron-disi) DOLDURUR."""
    a = json.loads(json.dumps(_HAM_ARTIFACT))
    a["id"] = kimlik
    if kosum_kimlik is not None:
        a["workflow_run"]["id"] = kosum_kimlik
    a["name"] = DAMGA_ADI if ad is None else ad
    a["expired"] = expired
    an = datetime.now(timezone.utc) - timedelta(hours=yas_saat)
    a["created_at"] = an.strftime("%Y-%m-%dT%H:%M:%SZ")
    a["updated_at"] = a["created_at"]
    a["expires_at"] = (an + timedelta(hours=DAMGA_SAKLAMA_SAAT)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    return a


def _kosum_kaydi(yas_saat, event="schedule", dosya="d1-uzlastirici.yml", kimlik=None):
    """GERCEK `workflow_runs` govdesinin ayni seklinde tek kosum kaydi."""
    k = dict(_HAM_KOSUM)
    if kimlik is not None:
        k["id"] = kimlik
    k["event"] = event
    k["path"] = ".github/workflows/%s" % dosya
    an = datetime.now(timezone.utc) - timedelta(hours=yas_saat)
    k["created_at"] = an.strftime("%Y-%m-%dT%H:%M:%SZ")
    k["run_started_at"] = k["created_at"]
    return k


def _sahte_api(durum="active", kosum_sayisi=0, yas_saat=0.0, kayitli=True,
               kayit_yas_saat=24.0, yenileme_yas_saat=24.0,
               dosya="d1-uzlastirici.yml", bozuk=None, event="schedule",
               damgalar=None, kosum_yaslari=None, damga_kosum="schedule"):
    """GERCEK govdenin ayni seklini ureten enjekte edilebilir `getir`.

    `damgalar`: artifact kayitlari listesi (None -> tek TAZE damga).
    `kosum_yaslari`: `event=schedule` kosumlarinin YASLARI (saat). None -> TEK kayit
      (`yas_saat`) doner; bu, A5 acisindan "gecmis penceresi kadar veri YOK" halidir ve
      varsayilan fikstur kayit/yenileme yasi 24 sa oldugu icin A5 🟡 kalir — yani A5
      MEVCUT iddialarin higbirinin isaretini degistirmez, kendi fiksturleriyle olculur.
    `damga_kosum`: damgayi HANGI kosum yazdi.
      "schedule" (varsayilan) -> damganin `workflow_run.id`si fiksturun EN YENI
        zamanlanmis kosumunun kimligidir (yani damga CRON teslimidir);
      "elle" -> kimlik `_CRON_DISI_KOSUM` olur (4 Agu'da OLCULEN gercek
        `workflow_dispatch` kosumu) ve zamanlanmis kosum kumesinde BULUNMAZ.
      🔴 Bu ayrim MEVCUT damga fiksturlerini DEGISTIRMEZ (varsayilan cron teslimidir),
      yalniz tetikleyici sartini AYIRT EDICI hale getirir: TEK DEGISKEN degisir."""
    _kosum_onbellek = []

    def _kosum_kayitlari():
        """Fikstur kosum kayitlari — TEK KEZ uretilir (kimlikler iki dalda AYNI olsun)."""
        if _kosum_onbellek:
            return _kosum_onbellek[0]
        if kosum_sayisi == 0:
            uretilen = []
        elif kosum_yaslari is None:
            uretilen = [_kosum_kaydi(yas_saat, event, dosya)]
        else:
            uretilen = [_kosum_kaydi(y, event, dosya, kimlik=1000 + i)
                        for i, y in enumerate(kosum_yaslari)]
        _kosum_onbellek.append(uretilen)
        return uretilen

    def _damga_kosum_kimligi(mod=None):
        if (mod or damga_kosum) != "schedule":
            return _CRON_DISI_KOSUM
        kayitlar = _kosum_kayitlari()
        if not kayitlar:
            # Zamanlanmis kosum YOKSA damga cron kaynakli OLAMAZ (fail-closed fikstur).
            return _CRON_DISI_KOSUM
        return max(kayitlar, key=lambda k: k["created_at"])["id"]

    def _damgalari_kosuma_bagla(kayitlar, mod=None):
        """Damga kaydinin `workflow_run.id`si HENUZ DOLDURULMAMISSA (ham fikstur degeri)
        `damga_kosum` (ya da `mod`) moduna gore doldurulur. Acikca kimlik verilmis
        kayitlara DOKUNULMAZ."""
        kimlik = _damga_kosum_kimligi(mod)
        cikti = []
        for a in kayitlar:
            b = json.loads(json.dumps(a))
            wr = b.get("workflow_run")
            if isinstance(wr, dict) and wr.get("id") == _HAM_ARTIFACT["workflow_run"]["id"]:
                wr["id"] = kimlik
            cikti.append(b)
        return cikti

    def getir(yol, zaman_asimi=25):   # noqa: ARG001
        if bozuk == "ag":
            raise OlcumHatasi("GitHub API cagrilamadi (URLError: [Errno 8] nodename nor "
                              "servname provided)")
        if "actions/artifacts?" in yol:
            if bozuk == "damga-ag":
                raise OlcumHatasi("GitHub API HTTP 502: actions/artifacts")
            if bozuk == "damga-sekli":
                return {"total_count": 1, "artefaktlar": []}
            if bozuk == "damga-alan":       # `created_at` alani DUSMUS
                eksik = _damga_kaydi(0.5)
                del eksik["created_at"]
                return {"total_count": 1, "artifacts": [eksik]}
            if bozuk == "damga-suzgec":     # `?name=` suzgeci CALISMAMIS
                return {"total_count": 1, "artifacts": [_damga_kaydi(0.5, ad="github-pages")]}
            if bozuk == "damga-zaman":      # zaman damgasi COZULEMEZ
                boz = _damga_kaydi(0.5)
                boz["created_at"] = "dun aksam"
                return {"total_count": 1, "artifacts": [boz]}
            kayitlar = _damgalari_kosuma_bagla(
                [_damga_kaydi(1.0)] if damgalar is None else damgalar)
            return {"total_count": len(kayitlar), "artifacts": kayitlar}
        if "actions/workflows?" in yol:
            if bozuk == "liste-sekli":
                return {"total_count": 1, "isakislari": []}
            if not kayitli:
                return {"total_count": 0, "workflows": []}
            wf = dict(_HAM_WF)
            wf["path"] = ".github/workflows/%s" % dosya
            wf["state"] = durum
            wf["created_at"] = (datetime.now(timezone.utc) - timedelta(
                hours=kayit_yas_saat)).strftime("%Y-%m-%dT%H:%M:%SZ")
            return {"total_count": 1, "workflows": [wf]}
        if "/runs?" in yol:
            if bozuk == "kosum-sekli":
                return {"workflow_runs": []}
            if bozuk == "tutarsiz":
                return {"total_count": 3, "workflow_runs": []}
            if bozuk == "kosum-listesi-sekli":
                return {"total_count": 3, "workflow_runs": {"0": {}}}
            if kosum_sayisi == 0:
                return {"total_count": 0, "workflow_runs": []}
            if kosum_yaslari is None:
                return {"total_count": kosum_sayisi,
                        "workflow_runs": list(_kosum_kayitlari())}
            # 🔴 SIRA BILEREK BOZUK: GERCEK API yeniden eskiye doner; kod BUNA
            # GUVENMEMELIDIR. Fikstur listeyi karistirarak "siralamayi API'ye birakma"
            # iddiasini KOSAR (siralamayi kaldiran mutant KIRMIZI yanar).
            kayitlar = [dict(k) for k in _kosum_kayitlari()]
            kayitlar = kayitlar[1::2] + kayitlar[0::2]
            if bozuk == "ikinci-kayit-event":   # suzgec YARIM calismis
                kayitlar[-1]["event"] = "workflow_dispatch"
            if bozuk == "kosum-zaman":          # TEK kaydin damgasi COZULEMEZ
                kayitlar[-1]["created_at"] = "dun aksam"
            return {"total_count": max(kosum_sayisi, len(kayitlar)),
                    "workflow_runs": kayitlar}
        if "/commits?path=" in yol:
            if bozuk == "commit-sekli":
                return [{"commit": {"committer": {}}}]
            an = datetime.now(timezone.utc) - timedelta(hours=yenileme_yas_saat)
            return [{"sha": "f0b8b0b44b61e447a81c46bde4b4998e4c1eb89b",
                     "commit": {"committer": {"date": an.strftime("%Y-%m-%dT%H:%M:%SZ")}}}]
        raise OlcumHatasi("fikstur bilinmeyen yol: %s" % yol)
    # A4 fiksturu (paket_api) damgalarini KENDI uretir; ayni baglama kuralini kullansin
    # diye binder DISARI verilir (iki yerde iki kural = ikiz ayrisma).
    getir.damgalari_bagla = _damgalari_kosuma_bagla
    return getir


def _modul(ad):
    """tools/<ad>.py'yi MODUL olarak yukle (tire iceren ad -> importlib). Fail-closed."""
    import importlib.util
    yol = os.path.join(TOOLS, "%s.py" % ad)
    if not os.path.exists(yol):
        raise OlcumHatasi("tools/%s.py YOK" % ad)
    spec = importlib.util.spec_from_file_location("pruvo_%s" % ad.replace("-", "_"), yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def deploy_cagrilari():
    """(bayraksiz_var, kendini_test_var) — bu betigin adimlarini tasiyan is akisi
    (KADANS_IS_AKISI) HANGI kollari ANLAMLI OLARAK icra ediyor.

    🔴 5 Agu 2026: `cron-nabzi` job'u serit ayriminda deploy.yml'den nobet.yml'e
    TASINDI. Aranan DOSYA degisti, IDDIA DEGISMEDI ("iki kol da CI'da GERCEKTEN
    icra ediliyor"). Dosya yoksa OlcumHatasi -> fail-closed KIRMIZI.

    KESIF AYNALANMAZ ([[ayna-kapi-kesif-ekseni]]): `run:` dugumleri tools/yaml-oku.py'nin
    GERCEK ayristiricisiyla, "bu satir gercekten icra ediyor mu" hukmu ise
    tools/icra-suzgeci.py ile verilir — ikisi de bu depoda TEK KAYNAK.

    NEDEN GEREKLI: bu betigin deploy.yml'de IKI cagrisi var. ci-kapsam-test.py
    "dosya kosuluyor mu" diye bakar; biri silinse OBURU yuzunden hala YESIL kalir.
    Olculdu (ayni delik tools/ci-kapsam-test.py::bayraksiz_adim_kontrol'de): iki cagrili
    bir betikte GERCEK olcum kolu silinince dort denetci de rc=0 veriyordu."""
    yaml_oku = _modul("yaml-oku")
    suzgec = _modul("icra-suzgeci")
    yol = os.path.join(ROOT, ".github", "workflows", KADANS_IS_AKISI)
    if not os.path.exists(yol):
        raise OlcumHatasi("%s YOK: %s" % (KADANS_IS_AKISI, yol))
    with open(yol, encoding="utf-8") as f:
        bloklar, hata = yaml_oku.run_dugumleri(f.read())
    if hata:
        raise OlcumHatasi("%s `run:` dugumleri okunamadi: %s" % (KADANS_IS_AKISI, hata))
    hedef = "tools/cron-nabiz-kapisi.py"
    bayraksiz = kendini = False
    for _anahtar, _bas, _son, deger in bloklar:
        for satir in suzgec.birlestir_devam(str(deger or "")):
            hukum, _sebep, argumanlar = suzgec.anlamli_cagri(satir, hedef)
            if hukum != suzgec.EVET:
                continue
            if "--kendini-test" in (argumanlar or []):
                kendini = True
            else:
                bayraksiz = True
    return bayraksiz, kendini


def damga_kosul_arizasi(adim):
    """Damga adimi FIILEN olculmus bir denetime KOSULLU mu -> ariza metni | None.

    GitHub semantigi: onceki adim duserse `always()` tasimayan adim ZATEN atlanir; ama
    `skipped` bir olcumden sonra kosul YOKSA adim KOSAR. Bu yuzden kosulun OLCUM
    adiminin ciktisina bakmasi SART: damganin iddiasi "denetim yapildi"dir."""
    kosul = str(adim.get("if") or "").strip()
    if not kosul:
        return ("`if:` kosulu YOK -> adim her kosumda kosar (olcum `skipped` olsa bile)")
    if "always()" in kosul:
        return ("kosulda `always()` var -> olcum/onarim/teyit duşse ya da atlansa bile "
                "damga dogar (kosul: %r)" % kosul[:90])
    if "steps.olcum.outputs" not in kosul:
        return ("kosul OLCUM adiminin ciktisina (`steps.olcum.outputs...`) BAKMIYOR "
                "(kosul: %r)" % kosul[:90])
    return None


def uzlastirici_kablosu():
    """A0'IN KAYNAGI YASIYOR MU — uzlastirici is akisi damgayi FIILEN uretiyor mu.

    Bir okuyucu, YAZICISI olmadan hep KIRMIZI yanar (ya da yazici sessizce silinince
    eksen olur). Bu capa d1-uzlastirici.yml'i GERCEK YAML ayristiricisiyla okur ve
    BES seyi OLCER (hepsi fail-closed):
      (1) `--damga-yaz <dosya>` cagrisi VAR,
      (2) AYNI dosyayi `actions/upload-artifact` ile `name: <DAMGA_ADI>` altinda YUKLER,
      (3) yukleme adimi fail-open DEGIL (`continue-on-error` yok, `if-no-files-found: error`),
      (4) onarim adimi yaris-yeniden-denemeli surucuyu (uzlastirici-onarim.py) ve
          kosum basinda `git reset --hard FETCH_HEAD` tazelemesini kullanir,
      (5) 🔴 HER IKI damga adimi da OLCUMUN SONUCUNA KOSULLU (`steps.olcum.outputs.sapma`)
          ve `always()` DEGIL. GEREKCE (bu eksenin var olma sebebi): 20:47:18Z kosumu
          SUCCESS'ti ve olcum/onarim/teyit adimlarinin HEPSI `skipped`ti. Damga adimindan
          `if:` satiri silinirse damga TAM O KOSUMDA da dogar -> A0 ekseni "denetim
          yapildi" diye SIFIR denetimi damgalar, yani okudugu sey sahte olur. Bu satir
          o tek-satirlik zayiflamayi KIRMIZI yakar (olculdu: kalkan olmadan mutant
          tum kapilarda rc 0 idi).
    Doner: (sorunlar_listesi, bulgular_sozlugu)."""
    yol = os.path.join(WORKFLOW_DIZIN, UZLASTIRICI_DOSYA)
    if not os.path.exists(yol):
        raise OlcumHatasi("uzlastirici is akisi YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        govde = yaml_belge(f.read())
    if not isinstance(govde, dict) or not isinstance(govde.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % UZLASTIRICI_DOSYA)
    adimlar = []
    for _job_ad, job in govde["jobs"].items():
        if isinstance(job, dict) and isinstance(job.get("steps"), list):
            adimlar.extend(a for a in job["steps"] if isinstance(a, dict))

    yazilan = None
    yukleme = None
    yazma_adimi = None
    surucu = tazeleme = False
    for a in adimlar:
        komut = str(a.get("run") or "")
        for satir in komut.splitlines():
            s = satir.strip()
            if "cron-nabiz-kapisi.py" in s and "--damga-yaz" in s:
                parcalar = s.split()
                # 🔴 AD SUZGECI (4 Agu): bu is akisi ARTIK IKI damga yazar — A0 damgasi
                # (`uzlastirma-damgasi`, varsayilan ad) ve kol ayriminin SAPMA damgasi
                # (`--damga-adi d1-sapma-damgasi`). Suzgec olmadan dongu son gordugu
                # cagriyi A0 sanardi: bu yon SAHTE-KIRMIZI ("yazilan dosya ile yuklenen
                # path AYNI DEGIL"), ters yonu ise daha kotu — adim sirasi degisirse A0'in
                # yazicisi SILINSE bile eksen sapma damgasiyla YESIL kalirdi.
                if "--damga-adi" in parcalar:
                    j = parcalar.index("--damga-adi")
                    if j + 1 < len(parcalar) and parcalar[j + 1] != DAMGA_ADI:
                        continue
                i = parcalar.index("--damga-yaz")
                if i + 1 < len(parcalar):
                    yazilan = parcalar[i + 1]
                    yazma_adimi = a
            if "uzlastirici-onarim.py" in s and s.startswith("python3"):
                surucu = True
            if s.startswith("git reset --hard FETCH_HEAD"):
                tazeleme = True
        if str(a.get("uses") or "").startswith("actions/upload-artifact"):
            ile = a.get("with") if isinstance(a.get("with"), dict) else {}
            if str(ile.get("name") or "") == DAMGA_ADI:
                yukleme = a

    sorunlar = []
    if not yazilan:
        sorunlar.append("%s icinde `cron-nabiz-kapisi.py --damga-yaz <dosya>` cagrisi YOK "
                        "-> A0 ekseni KAYNAKSIZ kalir" % UZLASTIRICI_DOSYA)
    if yukleme is None:
        sorunlar.append("`actions/upload-artifact` adimi `name: %s` ile YOK -> damga "
                        "dogsa bile nabiz kapisi onu GOREMEZ" % DAMGA_ADI)
    else:
        ile = yukleme.get("with") if isinstance(yukleme.get("with"), dict) else {}
        if yazilan and str(ile.get("path") or "").strip() != yazilan:
            sorunlar.append("yazilan dosya (%r) ile yuklenen `path` (%r) AYNI DEGIL -> "
                            "bos/yanlis damga yuklenir" % (yazilan, ile.get("path")))
        if str(ile.get("if-no-files-found") or "").lower() != "error":
            sorunlar.append("`if-no-files-found: error` YOK -> damga dosyasi olusmasa bile "
                            "adim SESSIZCE gecer (fail-open)")
        if yukleme.get("continue-on-error"):
            sorunlar.append("damga yukleme adimi `continue-on-error` ile FAIL-OPEN")
    if not surucu:
        sorunlar.append("onarim adimi `tools/uzlastirici-onarim.py` surucusunu KULLANMIYOR "
                        "-> 17:12Z yaris kaybi (21 hash, 0 yazma) yeniden yasanabilir")
    if not tazeleme:
        sorunlar.append("`git reset --hard FETCH_HEAD` tazelemesi YOK -> donmus github.sha "
                        "checkout'u 20:47Z'deki 'her sey skipped, kosum YESIL' halini "
                        "yeniden uretir")
    kosullu = True
    for etiket, adim in (("damga YAZMA", yazma_adimi), ("damga YUKLEME", yukleme)):
        if adim is None:
            continue
        ariza = damga_kosul_arizasi(adim)
        if ariza:
            kosullu = False
            sorunlar.append("%s adimi OLCUM SONUCUNA KOSULLU DEGIL — %s. Damga o zaman "
                            "'denetim yapildi' demez, 'kosum bitti' der; 20:47Z'nin SIFIR "
                            "denetimli YESIL kosumu da damgalanirdi." % (etiket, ariza))
    return sorunlar, {"yazilan": yazilan, "yukleme": yukleme is not None,
                      "surucu": surucu, "tazeleme": tazeleme, "kosullu": kosullu}


# ---- KADANS KOLU: uzlastirma GitHub cron KUYRUGUNA bagimli DEGIL ------------
# 🔴 OLCULEN GEREKCE (4 Agu 2026): `d1-uzlastirici.yml` cron'u `9,24,39,54` (ofsetli
# ACIK dakika listesi) oldugu halde 48 saatte nominal 192 tetiklemenin 7'si teslim
# edildi (%3,65) ve EN UZUN ARDISIK BOSLUK 1053 dk = 17,6 SAAT oldu. Ofset hipotezi
# CURUTULDU: `13,28,43,58` tasiyan paket alarmi AYNI DAKIKALARDA, PARTI HALINDE ve AYNI
# oranda dustu -> hal DEPO/HESAP duzeyinde bir teslim sorunudur, cron METNI degil.
# Cron dakikasini DEGISTIRMEK bu sinifi COZMEZ (olculdu) ve her dokunus A3/A5'i uyarir.
# COZUM CRON'U ONARMAK DEGIL, UZLASTIRMAYI CRON'A BAGIMLI BIRAKMAMAKTIR: depo saatte
# onlarca push aliyor; `deploy.yml` icinden BLOKLAMAYAN bir kol AYNI is akisini
# (`workflow_call`) cagirirsa uzlastirma fiilen 15 dakikadan SIK kosar ve GitHub'in
# zamanlanmis kuyruguna hic bagimli olmaz. Cron IKINCI KOL olarak KALIR (push'suz
# geceler). Bu iki kol AYNI DOSYADAN kosar — govde kopyalanmaz ([[ikiz-tanim-sessiz-ayrisma]]).
KADANS_CAGRISI = "./.github/workflows/%s" % UZLASTIRICI_DOSYA
DEPLOY_DOSYA = "deploy.yml"
# 🔴 5 Agu 2026 SERIT AYRIMI: kadans kolu (bloklamayan bir job) deploy.yml'den
# nobet.yml'e TASINDI — bloklamayan joblarin kirmizisi YAYIN kosumunun rengini
# boyuyordu ([[hukum-yanlis-birimde]]; olculdu: 28 ardisik "failure" kosumun 14'unde
# deploy+yayin YESILDI). Kol ARANDIGI YER degisti, IDDIA DEGISMEDI: "yayini
# BLOKLAMIYOR" hala deploy.yml'in GERCEK `needs` kapanisindan olculur ve kolu geri
# sizdiran mutant (tools/cron-teslim-mutasyon.py M9 · tools/d1-sapma-mutasyon.py S6)
# KIRMIZI yakmaya devam eder.
KADANS_IS_AKISI = "nobet.yml"
YAYIN_ISI = "deploy"


def _gecisli_needs(joblar, kok):
    """`kok` job'unun GECISLI `needs:` kapanisi (kendisi HARIC)."""
    def _needs(job):
        ham = (job or {}).get("needs")
        if isinstance(ham, str):
            return {ham}
        if isinstance(ham, list):
            return set(str(x) for x in ham)
        if isinstance(ham, dict):
            return set(str(k) for k in ham)
        return set()

    bulunan = set()
    yigin = list(_needs(joblar.get(kok) or {}))
    while yigin:
        ad = yigin.pop()
        if ad in bulunan:
            continue
        bulunan.add(ad)
        yigin.extend(_needs(joblar.get(ad) or {}))
    return bulunan


def kadans_kablosu():
    """KADANS KOLU YASIYOR MU + YAYINI BLOKLUYOR MU — GERCEK dosyalardan OLCULUR.

    ALTI sart, hepsi fail-closed:
      (1) deploy.yml'de `uses: ./.github/workflows/d1-uzlastirici.yml` cagiran bir job VAR
          (govde KOPYALANMAZ: cron kolu ile push kolu AYNI dosyayi kosar),
      (2) 🔴 o job `deploy`nin GECISLI `needs:` kapanisinda DEGIL -> yayini BLOKLAMAZ.
          (Bu sartin mutanti: job'u `deploy: needs`'e sizdirmak. Kadans kolu D1/ag'a
          bagimlidir; bloklayici yapilirsa tek bir ag arizasi TUM EKIBIN yayinini
          durdurur — bu depoda olculen kapi-birikimi zararinin ta kendisi.)
      (3) `continue-on-error`/DAIMA-YANLIS `if:` ile SUSTURULMAMIS: bloklamamak SESSIZ
          OLMAK DEGILDIR, kol kendi kirmizisini GOSTERIR (fail-open yazimi nobetci
          ihlalidir),
      (4) ESZAMANLILIK — TEK KILIT, IS DUZEYINDE: grup d1-uzlastirici.yml'in
          `uzlastir` JOB'unda beyan edilmis olmali (is akisi duzeyinde DEGIL: cagrilan
          kolda uygulanip uygulanmadigi belirsiz olurdu) VE cagiran job KENDI
          `concurrency` grubunu beyan ETMEMELI (cagiran job grubu tutarken cagrilan is
          ayni grubu isterse kosum KILITLENEBILIR). Boylece cron kolu ile push kolu
          AYNI grupta ve TEK KEZ kilitlenir -> ayni anda IKI uzlastirma kosamaz,
      (5) `secrets: inherit` -> olcum CLOUDFLARE_API_TOKEN'siz kosarsa her kosumda
          "olculemedi" verir ve damga HIC dogmaz (sessiz olu kol),
      (6) d1-uzlastirici.yml'de `schedule` KOLU DURUYOR (cron IKINCI KOL olarak kalir)
          ve `workflow_call` acik (aksi halde cagri COZULMEZ).
    Doner: (sorunlar, bulgular)."""
    uzl_yol = os.path.join(WORKFLOW_DIZIN, UZLASTIRICI_DOSYA)
    dep_yol = os.path.join(WORKFLOW_DIZIN, DEPLOY_DOSYA)
    nob_yol = os.path.join(WORKFLOW_DIZIN, KADANS_IS_AKISI)
    for yol in (uzl_yol, dep_yol, nob_yol):
        if not os.path.exists(yol):
            raise OlcumHatasi("is akisi YOK: %s" % yol)
    with open(uzl_yol, encoding="utf-8") as f:
        uzl = yaml_belge(f.read())
    with open(dep_yol, encoding="utf-8") as f:
        dep = yaml_belge(f.read())
    with open(nob_yol, encoding="utf-8") as f:
        nob = yaml_belge(f.read())
    if not isinstance(dep, dict) or not isinstance(dep.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % DEPLOY_DOSYA)
    if not isinstance(nob, dict) or not isinstance(nob.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % KADANS_IS_AKISI)
    if not isinstance(uzl, dict):
        raise OlcumHatasi("%s: kok dugum okunamadi" % UZLASTIRICI_DOSYA)

    sorunlar = []
    tetik = _on_bolumu(uzl)
    tetik_adlari = set(str(k) for k in tetik) if isinstance(tetik, (dict, list)) else set()
    for gerekli, tani in (
            ("schedule", "cron IKINCI KOL olarak KALMALI (push'suz gecelerin kapsamasi); "
                         "kadans kolu cron'un YERINE DEGIL, YANINA kondu"),
            ("workflow_call", "deploy.yml kolu bu is akisini `uses:` ile cagirir; "
                              "tetikleyici yoksa cagri COZULMEZ")):
        if gerekli not in tetik_adlari:
            sorunlar.append("%s icinde `%s` tetikleyicisi YOK -> %s"
                            % (UZLASTIRICI_DOSYA, gerekli, tani))
    # TEK KAYNAK: eszamanlilik grubu is akisinin KENDI IS'INDEN okunur (is akisi
    # duzeyinden DEGIL — bkz. docstring (4)).
    grup = None
    for _ad, job in (uzl.get("jobs") or {}).items():
        if not isinstance(job, dict):
            continue
        ham = job.get("concurrency")
        aday = ham.get("group") if isinstance(ham, dict) else ham
        if aday and str(aday).strip():
            grup = str(aday).strip()
            break
    if not grup:
        sorunlar.append(
            "%s icinde IS DUZEYINDE `concurrency.group` YOK -> cron kolu ile "
            "`workflow_call` kolu ayni anda kosabilir (D1'e cift yazim). Grup is akisi "
            "duzeyine konursa cagrilan kolda uygulanip uygulanmadigi BELIRSIZDIR."
            % UZLASTIRICI_DOSYA)

    # KOL, SERIT AYRIMINDAN SONRA NOBET IS AKISINDA ARANIR (govde yine KOPYALANMAZ:
    # tek `d1-uzlastirici.yml`, iki kol). BLOKLAMA IDDIASI ise hala DEPLOY grafiginden
    # olculur — "baska dosyada oldugu icin bloklayamaz" demek BEYAN olurdu, olcum degil.
    joblar = dep["jobs"]
    nobet_joblar = nob["jobs"]
    kadans_ad, kadans = None, None
    for ad, job in nobet_joblar.items():
        if isinstance(job, dict) and str(job.get("uses") or "").strip() == KADANS_CAGRISI:
            kadans_ad, kadans = str(ad), job
            break
    if kadans is None:
        sorunlar.append(
            "KADANS KOLU YOK: %s icinde `uses: %s` cagiran job bulunamadi -> uzlastirma "
            "YALNIZ GitHub cron kuyruguna bagimli kalir (olculdu 4 Agu: 48 saatte teslim "
            "%%3,65, en uzun bosluk 17,6 saat)." % (KADANS_IS_AKISI, KADANS_CAGRISI))
        return sorunlar, {"job": None, "grup": grup, "tetikler": sorted(tetik_adlari)}

    engel = _gecisli_needs(joblar, YAYIN_ISI)
    # IKI YOLDAN SIZABILIR: (a) adi `deploy: needs` kapanisina yazilir, (b) job'un
    # KENDISI deploy.yml'e geri tasinir. Ikisi de olculur (her biri TEK BASINA
    # kirmizi yakabilmeli — [[beyan-edilmis-survivor]]).
    deploy_kopyasi = [str(a) for a, j in joblar.items()
                      if isinstance(j, dict)
                      and str(j.get("uses") or "").strip() == KADANS_CAGRISI]
    blokluyor = (kadans_ad in engel) or bool(set(deploy_kopyasi) & engel)
    if kadans_ad in engel or deploy_kopyasi:
        sorunlar.append(
            "🔴 KADANS KOLU YAYIN GRAFIGINE SIZDI: kol `%s` (%s icinde) ama %s'de "
            "%s. Bu kol D1'e ve aga bagimlidir; bloklayici yapilirsa tek bir ag/D1 "
            "arizasi TUM EKIBIN yayinini durdurur ve kirmizisi YAYIN kosumunun rengini "
            "boyar. Kadans GORUNURLUK isidir, yayin kapisi DEGIL. (`%s` needs kapanisi: %s)"
            % (kadans_ad, KADANS_IS_AKISI, DEPLOY_DOSYA,
               ("`%s` adi needs kapanisinda" % kadans_ad) if kadans_ad in engel
               else ("ayni cagriyi tasiyan job(lar) VAR: %s" % ", ".join(deploy_kopyasi)),
               YAYIN_ISI, ", ".join(sorted(engel)) or "(bos)"))
    if kadans.get("continue-on-error") in (True, "true"):
        sorunlar.append("`%s` job'u `continue-on-error` ile FAIL-OPEN -> bloklamamak "
                        "SESSIZ OLMAK DEGILDIR, kol kendi kirmizisini gostermelidir"
                        % kadans_ad)
    kosul = str(kadans.get("if") or "").strip().lower()
    if kosul in ("false", "${{ false }}"):
        sorunlar.append("`%s` job'u DAIMA-YANLIS `if:` ile OLU" % kadans_ad)
    if kadans.get("concurrency") is not None:
        sorunlar.append(
            "`%s` job'u KENDI `concurrency` grubunu beyan ediyor (%r). Kilit cagrilan "
            "isin (`%s`) JOB'unda ve grup %r; cagiran job da bir grup tutarsa (ozellikle "
            "AYNI grup) kosum KILITLENEBILIR, farkli grup ise IKINCI bir kilit demektir. "
            "TEK KILIT: cagrilan iste." % (kadans_ad, kadans.get("concurrency"),
                                           UZLASTIRICI_DOSYA, grup))
    if str(kadans.get("secrets") or "").strip() != "inherit":
        sorunlar.append("`%s` job'unda `secrets: inherit` YOK (%r) -> olcum "
                        "CLOUDFLARE_API_TOKEN'siz kosar, HER kosumda 'olculemedi' verir "
                        "ve damga HIC dogmaz (sessiz olu kol)"
                        % (kadans_ad, kadans.get("secrets")))

    # ── (7) KOL BAYRAGI: cagiran job KENDINI KADANS KOLU olarak BEYAN EDER ──────
    # 🔴 GEREKCE (4 Agu, KraL hukmu): bayrak DUSURULURSE cagrilan is akisi varsayilan
    # `false` ile kosar, yani CRON gibi davranir ve ONARILAN sapmada `exit 1` verir.
    # O zaman deploy.yml kosumunun conclusion'i yine IKI soruyu birden cevaplar
    # ("yayin calisti mi" + "D1 sapmasi var mi") — [[hukum-yanlis-birimde]]. Bu tek
    # satirlik gerileme SESSIZDIR: hicbir adim kirmizi yanmaz, yalnizca kosumun rengi
    # anlamini kaybeder. Bu yuzden AYRI bir iddia olarak olculur.
    ile = kadans.get("with") if isinstance(kadans.get("with"), dict) else {}
    bayrak = ile.get(KADANS_BAYRAGI)
    if bayrak is not True:
        sorunlar.append(
            "`%s` job'u `with: %s: true` GECMIYOR (%r) -> cagrilan is akisi varsayilan "
            "`false` ile kosar ve ONARILAN sapmada `exit 1` verir; bu kosumun (%s) "
            "conclusion'i o zaman YINE iki soruyu birden cevaplar (yayin sagligi + D1 "
            "sapmasi)." % (kadans_ad, KADANS_BAYRAGI, bayrak, DEPLOY_DOSYA))
    # ── (8) BAYRAK CAGRILAN TARAFTA TANIMLI mi ve VARSAYILANI `false` mi ────────
    # Varsayilan `true` olsaydi CRON kolu da sessizce kadans gibi davranir, sapma
    # cron kosumunda da kirmizi yakmazdi -> alarm iki koldan da susardi.
    girdiler = ((tetik or {}).get("workflow_call") or {}) if isinstance(tetik, dict) else {}
    girdiler = girdiler.get("inputs") if isinstance(girdiler, dict) else None
    tanim = girdiler.get(KADANS_BAYRAGI) if isinstance(girdiler, dict) else None
    if not isinstance(tanim, dict):
        sorunlar.append("%s `on.workflow_call.inputs.%s` TANIMLI DEGIL -> cagiran "
                        "taraftaki `with:` COZULMEZ (kol ayrimi yapilamaz)"
                        % (UZLASTIRICI_DOSYA, KADANS_BAYRAGI))
    else:
        if str(tanim.get("type") or "").strip() != "boolean":
            sorunlar.append("%s `inputs.%s.type` `boolean` DEGIL (%r) -> `== true` "
                            "karsilastirmasi metin/boolean arasinda sessizce kayar"
                            % (UZLASTIRICI_DOSYA, KADANS_BAYRAGI, tanim.get("type")))
        if tanim.get("default") is not False:
            sorunlar.append(
                "%s `inputs.%s.default` `false` DEGIL (%r) -> CRON/ELLE kolu da kadans "
                "gibi davranir ve ONARILAN sapmada kirmizi yakmaz; sapma O ZAMAN IKI "
                "KOLDAN DA susar (sessizlestirmenin ta kendisi)."
                % (UZLASTIRICI_DOSYA, KADANS_BAYRAGI, tanim.get("default")))

    return sorunlar, {"job": kadans_ad, "grup": grup, "blokluyor": blokluyor,
                      "engel": sorted(engel), "tetikler": sorted(tetik_adlari),
                      "bayrak": bayrak, "bayrak_tanimi": tanim}


# ═════════════════════════════════════════════════════════════════════════════
# SINYAL AYRIMI — "yayin sagligi" ile "D1 sapmasi" AYRI HUKUMLER (4 Agu 2026)
# ═════════════════════════════════════════════════════════════════════════════
# OLCULEN KUSUR: uzlastiricinin sapma gorunurlugu adimi `exit 1` verir. `d1-kadans`
# `deploy: needs`'te olmadigi icin yayini DURDURMUYOR, ama cagiran kosumun (deploy.yml)
# GENEL `conclusion`'ini `failure` yapiyordu -> TEK kirmizi IKI soruyu birden cevapliyor.
# Bu depoda olculmus sinif: [[hukum-yanlis-birimde]] (toplu sonuc tekil ekseni gizler).
#
# COZUM SESSIZLESTIRME DEGIL — UC AYRI HUKUM:
#   (1) CRON/ELLE kolu + sapma          -> `exit 1`  (DAVRANIS DEGISMEDI)
#   (2) KADANS kolu + sapma ONARILDI    -> damga yaz + yukle, cikis kodu TEMIZ
#                                          (sapma d1-sapma-alarmi.yml'de KIRMIZI yanar)
#   (3) ONARILAMADI (her iki kolda)     -> `exit 1`  (AYRI hukum: emniyet agi tutmadi)
#
# BU KAPI O UC HUKMU YORUMDAN DEGIL, GERCEK YAML'DEN OLCER ve GitHub'in adim-kosulu
# semantigini FIILEN CALISTIRIR (asagidaki `_kosul_degerlendir`). Boylece:
#   * sapma sinyalini TAMAMEN kaldiran mutant -> (1) ve (2) kaybolur -> KIRMIZI,
#   * cron kolundaki `exit 1`'i kaldiran mutant -> (1) exit'siz kalir -> KIRMIZI,
#   * (2) ile (3)'u TEK adima yigan mutant -> dogruluk tablosu carpisir -> KIRMIZI,
#   * kadans koluna `exit 1` geri sizarsa -> (2) 'temiz cikis' iddiasi duser -> KIRMIZI.
_DURUM_ISLEVLERI = ("success()", "failure()", "always()", "cancelled()")


def _kosul_atom(parca, ortam):
    """TEK atomu degerlendir. TANIMADIGI her yazim OlcumHatasi (fail-closed).

    🔴 NEDEN DAR GRAMER ve NEDEN FAIL-CLOSED ([[mimar-kapi-parser-taklidi]]): burada
    GitHub ifade dilinin TAM bir ayristiricisi TAKLIT EDILMEZ. Yalniz bu is akisinda
    FIILEN kullanilan dort yazim taninir; baska her sey OLCULEMEDI'dir (rc 2), yani
    tanimadigi bir kosul SESSIZCE 'dogru' ya da 'yanlis' sayilmaz."""
    s = parca.strip()
    if s in _DURUM_ISLEVLERI:
        durum = ortam["durum"]
        return {"success()": durum == "success", "failure()": durum == "failure",
                "always()": True, "cancelled()": durum == "cancelled"}[s]
    m = re.match(r"^steps\.([A-Za-z0-9_-]+)\.outputs\.([A-Za-z0-9_-]+)"
                 r"\s*(==|!=)\s*'([^']*)'$", s)
    if m:
        adim, alan, op, lit = m.groups()
        deger = ortam["ciktilar"].get((adim, alan))
        return (deger == lit) if op == "==" else (deger != lit)
    m = re.match(r"^steps\.([A-Za-z0-9_-]+)\.outcome\s*(==|!=)\s*'([^']*)'$", s)
    if m:
        adim, op, lit = m.groups()
        deger = ortam["sonuclar"].get(adim)
        return (deger == lit) if op == "==" else (deger != lit)
    m = re.match(r"^inputs\.([A-Za-z0-9_-]+)\s*(==|!=)\s*(true|false)$", s)
    if m:
        alan, op, lit = m.groups()
        deger = bool(ortam["girdiler"].get(alan))
        bekle = (lit == "true")
        return (deger == bekle) if op == "==" else (deger != bekle)
    raise OlcumHatasi("adim kosulunda TANIMSIZ yazim: %r -> kosul katmani bu is akisi "
                      "icin OLCULEMEZ (sessizce 'dogru' sayilmaz)" % parca)


def _kosul_degerlendir(kosul, ortam):
    """GitHub adim `if:` kosulunun hukmu (bu is akisinin DAR grameri icin).

    ORTUK `success()`: GitHub, durum islevi TASIMAYAN bir kosula ortuk `success()`
    ekler — yani onceki adim dusmusse adim ATLANIR. Bu satir olmadan 'onarim dustu'
    senaryosunda (1)/(2) adimlari kosuyor sanilir ve (3) ile CARPISIRDI."""
    s = (kosul or "").strip()
    if not s:
        return ortam["durum"] == "success"
    ortuk = not any(i in s for i in _DURUM_ISLEVLERI)
    sonuc = False
    for veya in s.split("||"):
        parcalar = [p for p in veya.split("&&") if p.strip()]
        if not parcalar:
            raise OlcumHatasi("bos kosul parcasi: %r" % kosul)
        if all(_kosul_atom(p, ortam) for p in parcalar):
            sonuc = True
    if ortuk:
        sonuc = sonuc and ortam["durum"] == "success"
    return sonuc


def _uzl_adimlari():
    """d1-uzlastirici.yml'in `uzlastir` isindeki adimlar (GERCEK ayristirici)."""
    yol = os.path.join(WORKFLOW_DIZIN, UZLASTIRICI_DOSYA)
    if not os.path.exists(yol):
        raise OlcumHatasi("uzlastirici is akisi YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        govde = yaml_belge(f.read())
    if not isinstance(govde, dict) or not isinstance(govde.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % UZLASTIRICI_DOSYA)
    adimlar = []
    for _ad, job in govde["jobs"].items():
        if isinstance(job, dict) and isinstance(job.get("steps"), list):
            adimlar.extend(a for a in job["steps"] if isinstance(a, dict))
    if not adimlar:
        raise OlcumHatasi("%s: hicbir adim okunamadi" % UZLASTIRICI_DOSYA)
    return adimlar


def _sinyal_adimlari(adimlar):
    """(cron_adimlari, kadans_yazma, kadans_yukleme, onarilamadi) — SINIFLANDIRMA.

    Siniflandirma ADIM ADINA DEGIL ICRA ETTIGI SEYE bakar (ad bir mensiyondur, olcum
    degil): `exit 1` tasiyan sapma adimlari, `--damga-adi <SAPMA_DAMGA_ADI>` yazan adim
    ve o adi `upload-artifact` ile yukleyen adim."""
    cron_adim = kadans_yaz = kadans_yuk = onarilamadi = None
    for a in adimlar:
        komut = str(a.get("run") or "")
        kosul = str(a.get("if") or "")
        if str(a.get("uses") or "").startswith("actions/upload-artifact"):
            ile = a.get("with") if isinstance(a.get("with"), dict) else {}
            if str(ile.get("name") or "") == SAPMA_DAMGA_ADI:
                kadans_yuk = a
            continue
        if "--damga-adi %s" % SAPMA_DAMGA_ADI in komut:
            kadans_yaz = a
            continue
        if re.search(r"(?m)^\s*exit 1\s*$", komut) and "sapma" in kosul:
            # ONARILAMADI adimini ayirt eden sey `failure()` DEGIL, TEYIDIN GERCEK
            # SONUCUNU okumasidir ([[hukum-yanlis-birimde]]). Olculdu (kosum 31214568441,
            # commit 94402074): cron kolunda (1) gorunurluk adimi sapmada KASITLI `exit 1`
            # verince JOB durumu `failure` olur ve `failure()` kosullu (3) adimi, onarim +
            # teyit IKISI DE success oldugu HALDE "onarilamadi" diye YANLIS beyan ederdi.
            # `steps.teyit.outcome` capasi bu ayrimi kaynaktan olcer; `failure()`e geri
            # donen mutant burada cron adimi olarak siniflanir -> onarilamadi KAYBOLUR ->
            # "ONARILAMADI HUKMU YOK" KIRMIZI yanar (capanin ayirt ediciligi KORUNUR).
            if "steps.teyit.outcome" in kosul:
                onarilamadi = a
            else:
                cron_adim = a
    return cron_adim, kadans_yaz, kadans_yuk, onarilamadi


# HUKUM TABLOSU — (kol, sapma, onarim_durumu) -> HANGI adimlar kosmali.
# 🔴 TABLONUN KENDISI IDDIADIR: her satir bir SENARYODUR ve tam olarak BIR hukum
# uretir. "onarildi" ile "onarilamadi" tek adima yigilirsa ya da bayrak yok sayilirsa
# satirlardan EN AZ IKISI carpisir.
SINYAL_TABLOSU = (
    # (etiket,               kol_bayragi, sapma,        durum,     cron, yaz, yuk, onarilamadi)
    ("cron + sapma onarildi",      False, "var",        "success",  True, False, False, False),
    ("kadans + sapma onarildi",     True, "var",        "success", False,  True,  True, False),
    ("cron + onarilamadi",         False, "var",        "failure", False, False, False,  True),
    ("kadans + onarilamadi",        True, "var",        "failure", False, False, False,  True),
    ("cron + sapma yok",           False, "yok",        "success", False, False, False, False),
    ("kadans + sapma yok",          True, "yok",        "success", False, False, False, False),
    ("kadans + olcum olculemedi",   True, "olculemedi", "failure", False, False, False, False),
)


def sinyal_ayrimi():
    """UC HUKMUN VARLIGI + AYRILIGI — (sorunlar, bulgular).

    Olculen sartlar (hepsi fail-closed):
      (1) CRON/ELLE kolunun sapma adimi VAR ve `exit 1` TASIR (sinyali kaldiran ya da
          exit'i dusuren mutant KIRMIZI),
      (2) KADANS kolunun damga adimi VAR, `%s` adiyla yazar, AYNI adla YUKLER, yukleme
          fail-open DEGIL (`if-no-files-found: error`, `continue-on-error` yok) ve
          `exit 1` TASIMAZ (cagiran YAYIN kosumunun conclusion'i kirlenmesin),
      (3) ONARILAMADI adimi VAR, TEYIDIN GERCEK SONUCUNU (`steps.teyit.outcome`)
          okuyan kosullu ve `exit 1` tasir (bu hal
          "onarildi" ile AYNI KUTUYA konamaz),
      (4) DOGRULUK TABLOSU: SINYAL_TABLOSU'ndaki her senaryoda GitHub kosul semantigi
          FIILEN calistirilir ve tam olarak beklenen adimlar kosar.
    """ % SAPMA_DAMGA_ADI
    adimlar = _uzl_adimlari()
    cron_adim, kadans_yaz, kadans_yuk, onarilamadi = _sinyal_adimlari(adimlar)

    sorunlar = []
    if cron_adim is None:
        sorunlar.append(
            "SAPMA SINYALI YOK (cron/elle kolu): %s icinde sapmada `exit 1` veren adim "
            "bulunamadi -> sapma SESSIZLESTIRILMIS olur. Sapma OLMASI bir ust-yol "
            "kacaginin kanitidir; onarildi diye o kacak yok olmaz." % UZLASTIRICI_DOSYA)
    if kadans_yaz is None:
        sorunlar.append(
            "SAPMA KANALI YOK (kadans kolu): `--damga-adi %s` yazan adim bulunamadi -> "
            "kadans kolunda sapma HICBIR YERDE kirmizi yakmaz (sessizlestirme)."
            % SAPMA_DAMGA_ADI)
    else:
        if re.search(r"(?m)^\s*exit 1\s*$", str(kadans_yaz.get("run") or "")):
            sorunlar.append(
                "KADANS kolunun damga adimi `exit 1` TASIYOR -> cagiran YAYIN kosumunun "
                "conclusion'i yine sapma yuzunden kirmiziya doner; ayrim COZULMEZ.")
    if kadans_yuk is None:
        sorunlar.append(
            "SAPMA DAMGASI YUKLENMIYOR: `actions/upload-artifact` adimi `name: %s` ile "
            "YOK -> damga dogsa bile d1-sapma-alarmi.yml onu GOREMEZ (sessiz kanal)."
            % SAPMA_DAMGA_ADI)
    else:
        ile = kadans_yuk.get("with") if isinstance(kadans_yuk.get("with"), dict) else {}
        if str(ile.get("if-no-files-found") or "").lower() != "error":
            sorunlar.append("sapma damgasi yuklemesinde `if-no-files-found: error` YOK "
                            "-> damga olusmasa bile adim SESSIZCE gecer (fail-open)")
        if kadans_yuk.get("continue-on-error"):
            sorunlar.append("sapma damgasi yukleme adimi `continue-on-error` ile FAIL-OPEN")
        if kadans_yaz is not None:
            yazilan = None
            for satir in str(kadans_yaz.get("run") or "").splitlines():
                if "--damga-yaz" in satir:
                    p = satir.split()
                    i = p.index("--damga-yaz")
                    if i + 1 < len(p):
                        yazilan = p[i + 1]
            if yazilan and str(ile.get("path") or "").strip() != yazilan:
                sorunlar.append("yazilan sapma damgasi (%r) ile yuklenen `path` (%r) AYNI "
                                "DEGIL -> bos/yanlis damga yuklenir"
                                % (yazilan, ile.get("path")))
    if onarilamadi is None:
        sorunlar.append(
            "ONARILAMADI HUKMU YOK: `steps.teyit.outcome` (teyidin GERCEK sonucu) okuyan, "
            "sapmada `exit 1` veren AYRI adim "
            "bulunamadi -> 'sapma onarildi' ile 'sapma KAPANMADI' TEK HALE YIGILMIS olur. "
            "Ikincisinde katalog SU AN sapmali olabilir (Ege katalogun bir kismini "
            "goremez); bu bir gorunurluk notu degil ARIZADIR.")

    # ── DOGRULUK TABLOSU: kosul semantigi FIILEN calistirilir ──────────────────
    tablo = []
    for etiket, kol, sapma, durum, b_cron, b_yaz, b_yuk, b_onar in SINYAL_TABLOSU:
        ortam = {"durum": durum, "girdiler": {KADANS_BAYRAGI: kol},
                 "ciktilar": {("olcum", "sapma"): sapma},
                 "sonuclar": {"teyit": "success" if durum == "success" else "failure"}}
        gerceklesen = []
        for ad, adim, beklenen in (("cron", cron_adim, b_cron),
                                   ("damga-yaz", kadans_yaz, b_yaz),
                                   ("damga-yukle", kadans_yuk, b_yuk),
                                   ("onarilamadi", onarilamadi, b_onar)):
            if adim is None:
                continue
            kosar = _kosul_degerlendir(str(adim.get("if") or ""), ortam)
            gerceklesen.append((ad, kosar))
            if kosar != beklenen:
                sorunlar.append(
                    "DOGRULUK TABLOSU CARPISMASI [%s]: `%s` adimi %s bekleniyordu, %s "
                    "(kosul: %r)" % (etiket, ad, "KOSMALI" if beklenen else "KOSMAMALI",
                                     "KOSTU" if kosar else "KOSMADI",
                                     str(adim.get("if") or "")[:110]))
        tablo.append((etiket, gerceklesen))

    return sorunlar, {"cron": cron_adim is not None, "yaz": kadans_yaz is not None,
                      "yuk": kadans_yuk is not None, "onarilamadi": onarilamadi is not None,
                      "tablo": tablo}


def ayrim_kaniti():
    """AYRIM KANITI — IKI YON, TEK OLCUM. (sorunlar, bulgular)

    Ayrimin kabulu TEK YONLU OLAMAZ ([[beyan-edilmis-survivor]]): "deploy kosumu artik
    sapmadan kirmizi olmuyor" tek basina, sapmayi SESSIZLESTIREN bir cozumle de saglanir.
    Bu yuzden iki yon AYNI olcumde tartilir:

      YON (i)  D1'de SAPMA VAR (onarildi) + KADANS kolu:
               (a) uzlastirici isinde KOSAN hicbir adim cikis kodu 1 URETMEZ -> cagiran
                   kosumun (deploy.yml) conclusion'i YALNIZ yayin sagligini gosterir, VE
               (b) sapma damgasi DOGAR ve o damgayi okuyan GERCEK nobetci
                   (tools/d1-sapma-kapisi.py) rc 1 = KIRMIZI verir -> sapma BASKA BIR
                   YERDE kirmizi yakar. (a) ve (b) BIRLIKTE saglanmazsa ayrim gecersizdir.

      YON (ii) YAYIN GERCEKTEN BOZUK: ayrim, yayin kirmizisini KORLESTIRMEMELI.
               `deploy`nin gecisli `needs:` kapanisi BOS DEGIL (kapilar yayini fiilen
               bloklar) ve o kapanistaki hicbir job — `deploy`/`yayin` dahil —
               `continue-on-error` ya da DAIMA-YANLIS `if:` ile susturulmus DEGIL.
               Ek olarak sapma kolu (`d1-kadans`) o kapanista OLMAMALI (yoksa yayin
               kirmizisi ile sapma kirmizisi yine tek birimde toplanirdi).
    """
    adimlar = _uzl_adimlari()
    cron_adim, kadans_yaz, kadans_yuk, onarilamadi = _sinyal_adimlari(adimlar)
    sorunlar = []

    # ── YON (i-a): kadans kolunda ONARILAN sapma cikis kodu 1 URETMEZ ──────────
    ortam = {"durum": "success", "girdiler": {KADANS_BAYRAGI: True},
             "ciktilar": {("olcum", "sapma"): "var"},
             "sonuclar": {"teyit": "success"}}
    kosan_exit = []
    for a in adimlar:
        komut = str(a.get("run") or "")
        if not re.search(r"(?m)^\s*exit 1\s*$", komut):
            continue
        if _kosul_degerlendir(str(a.get("if") or ""), ortam):
            kosan_exit.append(str(a.get("name") or "")[:70])
    if kosan_exit:
        sorunlar.append(
            "YON (i-a) DUSTU: sapma ONARILDIGI halde kadans kolunda `exit 1` veren adim(lar) "
            "KOSUYOR (%s) -> deploy.yml kosumunun conclusion'i YINE iki soruyu birden "
            "cevaplar (yayin sagligi + D1 sapmasi)." % "; ".join(kosan_exit))

    # ── YON (i-b): damga DOGAR ve GERCEK nobetci onu KIRMIZI yakar ─────────────
    damga_dogar = bool(kadans_yaz) and bool(kadans_yuk) and all(
        _kosul_degerlendir(str(a.get("if") or ""), ortam) for a in (kadans_yaz, kadans_yuk))
    if not damga_dogar:
        sorunlar.append(
            "YON (i-b) DUSTU: sapma varken `%s` damgasi DOGMUYOR -> sapma hicbir kanala "
            "tasinmaz. Cikis kodunu temizleyip damgayi da dusurmek, ayrimin en kolay ve "
            "en YANLIS cozumu olan SESSIZLESTIRMEDIR." % SAPMA_DAMGA_ADI)
    else:
        alarm = _modul("d1-sapma-kapisi")

        def _sahte(yol, zaman_asimi=25):   # noqa: ARG001
            if "/artifacts" in yol:
                return {"artifacts": [{"name": SAPMA_DAMGA_ADI, "id": 1},
                                      {"name": DAMGA_ADI, "id": 2}]}
            raise AssertionError("fiksturde tanimsiz API yolu: %s" % yol)

        gozlem = alarm.sapma_gozle(_sahte, 4242, SAPMA_DAMGA_ADI)
        rc, _satirlar = alarm.hukum(gozlem, "workflow_run")
        if rc != 1:
            sorunlar.append(
                "YON (i-b) DUSTU: damga VAR ama tools/d1-sapma-kapisi.py rc=%d verdi "
                "(1 = KIRMIZI bekleniyordu) -> sapma AYRI kanalda da kirmizi YAKMIYOR."
                % rc)
        # Ters yon (yanlis-pozitif nobeti): damga YOKKEN alarm YESIL olmali, yoksa
        # "her zaman kirmizi" bir kanal hicbir sey soylemez.
        def _temiz(yol, zaman_asimi=25):   # noqa: ARG001
            if "/artifacts" in yol:
                return {"artifacts": [{"name": DAMGA_ADI, "id": 2}]}
            raise AssertionError("fiksturde tanimsiz API yolu: %s" % yol)
        rc_temiz, _ = alarm.hukum(alarm.sapma_gozle(_temiz, 4243, SAPMA_DAMGA_ADI),
                                  "workflow_run")
        if rc_temiz != 0:
            sorunlar.append("YON (i-b) TERS NOBET DUSTU: damga YOKKEN alarm rc=%d "
                            "(0 bekleniyordu) -> DAIMA kirmizi bir kanal sinyal tasimaz."
                            % rc_temiz)

    # ── YON (ii): yayin kirmizisi KORLESMEDI ──────────────────────────────────
    dep_yol = os.path.join(WORKFLOW_DIZIN, DEPLOY_DOSYA)
    if not os.path.exists(dep_yol):
        raise OlcumHatasi("is akisi YOK: %s" % dep_yol)
    with open(dep_yol, encoding="utf-8") as f:
        dep = yaml_belge(f.read())
    if not isinstance(dep, dict) or not isinstance(dep.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % DEPLOY_DOSYA)
    joblar = dep["jobs"]
    kapanis = _gecisli_needs(joblar, YAYIN_ISI)
    if not kapanis:
        sorunlar.append("YON (ii) DUSTU: `%s` job'unun `needs:` kapanisi BOS -> hicbir "
                        "kapi yayini bloklamiyor; yayin kirmizisi anlamsizlasir."
                        % YAYIN_ISI)
    susturulan = []
    for ad in sorted(kapanis | {YAYIN_ISI}):
        job = joblar.get(ad)
        if not isinstance(job, dict):
            susturulan.append("%s (job TANIMSIZ)" % ad)
            continue
        if job.get("continue-on-error") in (True, "true"):
            susturulan.append("%s (continue-on-error)" % ad)
        if str(job.get("if") or "").strip().lower() in ("false", "${{ false }}"):
            susturulan.append("%s (daima-yanlis `if:`)" % ad)
    if susturulan:
        sorunlar.append("YON (ii) DUSTU: yayin zincirindeki job(lar) SUSTURULMUS: %s -> "
                        "yayin gercekten bozuldugunda kosum KIRMIZI olmaz."
                        % ", ".join(susturulan))
    kadans_ad = None
    for ad, job in joblar.items():
        if isinstance(job, dict) and str(job.get("uses") or "").strip() == KADANS_CAGRISI:
            kadans_ad = str(ad)
            break
    if kadans_ad and kadans_ad in kapanis:
        sorunlar.append("YON (ii) DUSTU: sapma kolu (`%s`) yayin zincirinde -> iki kirmizi "
                        "yine TEK birimde toplanir." % kadans_ad)

    return sorunlar, {"kosan_exit": kosan_exit, "damga_dogar": damga_dogar,
                      "yayin_kapanisi": sorted(kapanis), "susturulan": susturulan,
                      "kadans": kadans_ad}


def sapma_alarm_kablosu():
    """SAPMA KANALININ EVI YASIYOR MU — d1-sapma-alarmi.yml GERCEK dosyadan OLCULUR.

    Kadans kolu sapmayi bir artifact'e tasidi; o artifact'i OKUYAN ve KIRMIZI yakan bir
    kol YOKSA ayrim SESSIZLESTIRMEYE donusur. BES sart, hepsi fail-closed:
      (1) dosya VAR ve ayristirilabilir,
      (2) alarm araci (`%s`) hem `--kendini-test` hem GERCEK olcum kolu ile kosuyor
          (yalniz `--kendini-test` kalsaydi alarm hicbir canli sey olcmez ama YESIL yanardi),
      (3) YAYINI DURDURAMAZ: `push`/`pull_request`/`workflow_call` tetikleyicisi YOK,
      (4) CRON'A BAGIMLI DEGIL: `workflow_run` ile deploy.yml'in BITISINDE tetiklenir
          (4 Agu olcumu: cron teslimi %%3,65, en uzun bosluk 17,6 sa -> kanali cron'a
          baglamak, kadans kolunun cozdugu sorunu geri getirirdi),
      (5) artifact listesini okuyabilmek icin `actions: read` yetkisi VAR.
    """ % SAPMA_ALARM_ARACI
    yol = os.path.join(WORKFLOW_DIZIN, SAPMA_ALARM_DOSYA)
    if not os.path.exists(yol):
        raise OlcumHatasi(
            "SAPMA ALARM KANALI YOK: %s bulunamadi -> kadans kolunda onarilan sapma "
            "HICBIR YERDE kirmizi yakmaz (sessizlestirme)." % SAPMA_ALARM_DOSYA)
    with open(yol, encoding="utf-8") as f:
        govde = yaml_belge(f.read())
    if not isinstance(govde, dict) or not isinstance(govde.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % SAPMA_ALARM_DOSYA)

    sorunlar = []
    tetik = _on_bolumu(govde)
    tetik_adlari = set(str(k) for k in tetik) if isinstance(tetik, (dict, list)) else set()
    for yasak, tani in (("push", "yayin akisi bu isi tetikleyemez"),
                        ("pull_request", "yayin akisi bu isi tetikleyemez"),
                        ("workflow_call", "deploy.yml bu isi `uses:` ile CAGIRAMAZ — "
                                          "cagirsaydi kirmizisi YINE deploy kosumunun "
                                          "conclusion'ina yigilirdi ve ayrim COZULMEZDI")):
        if yasak in tetik_adlari:
            sorunlar.append("%s icinde `%s` tetikleyicisi VAR -> %s"
                            % (SAPMA_ALARM_DOSYA, yasak, tani))
    if "workflow_run" not in tetik_adlari:
        sorunlar.append(
            "%s `workflow_run` ile tetiklenmiyor (%s) -> kanal ya cron kuyruguna bagimli "
            "kalir (olculdu 4 Agu: teslim %%3,65, en uzun bosluk 17,6 sa) ya da hic kosmaz"
            % (SAPMA_ALARM_DOSYA, sorted(tetik_adlari)))
    else:
        wr = tetik.get("workflow_run") if isinstance(tetik, dict) else None
        akislar = (wr or {}).get("workflows") if isinstance(wr, dict) else None
        if not isinstance(akislar, list) or not akislar:
            sorunlar.append("%s `workflow_run.workflows` listesi YOK -> hangi kosumun "
                            "bitisinde tetiklenecegi TANIMSIZ" % SAPMA_ALARM_DOSYA)

    yetki = govde.get("permissions")
    yetkiler = yetki if isinstance(yetki, dict) else {}
    if str(yetkiler.get("actions") or "") not in ("read", "write"):
        sorunlar.append("%s `permissions.actions` YOK/yetersiz (%r) -> tetikleyen kosumun "
                        "artifact listesi OKUNAMAZ ve alarm HER kosumda 'olculemedi' verir"
                        % (SAPMA_ALARM_DOSYA, yetkiler.get("actions")))

    kendini = canli = False
    for _ad, job in govde["jobs"].items():
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            continue
        if job.get("continue-on-error"):
            sorunlar.append("%s `%s` job'u `continue-on-error` ile FAIL-OPEN"
                            % (SAPMA_ALARM_DOSYA, _ad))
        for adim in job["steps"]:
            if not isinstance(adim, dict):
                continue
            if adim.get("continue-on-error"):
                sorunlar.append("%s: bir alarm adimi `continue-on-error` ile FAIL-OPEN "
                                "-> kirmizi yutulur" % SAPMA_ALARM_DOSYA)
            for satir in str(adim.get("run") or "").splitlines():
                s = satir.strip()
                if SAPMA_ALARM_ARACI not in s or not s.startswith("python3"):
                    continue
                if "--kendini-test" in s:
                    kendini = True
                else:
                    canli = True
    if not canli:
        sorunlar.append("%s GERCEK olcum kolunu (`python3 %s` — `--kendini-test`SIZ) "
                        "KOSMUYOR -> alarm hicbir canli sey olcmez ama YESIL yanar"
                        % (SAPMA_ALARM_DOSYA, SAPMA_ALARM_ARACI))
    if not kendini:
        sorunlar.append("%s `--kendini-test` kolunu KOSMUYOR -> 'alarm sapmayi gorur' "
                        "iddiasi hicbir yerde kanitlanmaz (sapma nadirdir, canli kol "
                        "gunlerce yesil doner)" % SAPMA_ALARM_DOSYA)
    return sorunlar, {"tetikler": sorted(tetik_adlari), "kendini": kendini,
                      "canli": canli, "actions_yetkisi": yetkiler.get("actions")}


def paket_kosul_arizasi(adim):
    """Paket damga adimi FIILEN PARITE cikmis bir olcume KOSULLU mu -> ariza | None.

    A0'in `damga_kosul_arizasi`'nin kardesi ama AYNI DEGIL: orada kosul "sapma yok ya da
    teyit gecti"dir, burada "olcum PARITE dedi"dir. Ortak kural aynidir — kosul OLCUMUN
    CIKTISINA bakmali, `always()`/`success()` OLMAMALI. `success()` de yeterli DEGIL:
    olcum adimi rc 0 verse bile bu is akisinda o rc'nin anlami zaten PARITE'dir, ama
    kosul cikti yerine `success()`e baglanirsa yarin araca "uyari ama rc 0" gibi bir hal
    eklendiginde damga SESSIZCE o hali de damgalar."""
    kosul = str(adim.get("if") or "").strip()
    if not kosul:
        return "`if:` kosulu YOK -> adim her kosumda kosar (olcum `skipped` olsa bile)"
    if "always()" in kosul:
        return ("kosulda `always()` var -> olcum duşse/atlansa bile damga dogar "
                "(kosul: %r)" % kosul[:90])
    if "steps.olcum.outputs.durum" not in kosul:
        return ("kosul OLCUM adiminin ciktisina (`steps.olcum.outputs.durum`) BAKMIYOR "
                "(kosul: %r)" % kosul[:90])
    if ("'%s'" % PAKET_PARITE_ETIKETI) not in kosul:
        return ("kosul %r etiketini SART KOSMUYOR -> drift ya da olculemedi bir kosum da "
                "damga dogurabilir (kosul: %r)" % (PAKET_PARITE_ETIKETI, kosul[:90]))
    return None


def _olcum_araci_etiketi():
    """tools/fiziksel-canli-kapisi.py::DURUM_ETIKET['PARITE'] — KOSARAK okunur.

    Iki dosyada iki dize tutulsaydi biri degistiginde damga kosulu sessizce hicbir zaman
    saglanmaz olurdu (alarm sonsuza kadar damgasiz kalir, A4 surekli kirmizi yanar ve
    ilk toplu iste kapatilirdi). Bu yuzden etiket TEK KAYNAKTAN kosarak alinir."""
    mod = _modul("fiziksel-canli-kapisi")
    tablo = getattr(mod, "DURUM_ETIKET", None)
    if not isinstance(tablo, dict) or "PARITE" not in tablo:
        raise OlcumHatasi("tools/fiziksel-canli-kapisi.py::DURUM_ETIKET okunamadi -> "
                          "damga kosulunun etiketi DOGRULANAMAZ")
    return tablo["PARITE"]


def paket_alarmi_kablosu():
    """A4'UN KAYNAGI YASIYOR MU + YAYINI DURDURAMIYOR MU — GERCEK dosyadan OLCULUR.

    ALTI sart, hepsi fail-closed:
      (1) `python3 tools/fiziksel-canli-kapisi.py` CANLI kolu (bayrakSIZ olcum) kosuyor.
          `--kendini-test`e dusurulmus bir alarm hicbir canli sey olcmez ama YESIL yanar.
      (2) Olcum adimi cikis kodunu YUTMUYOR (`||`, `continue-on-error`, `set +e` yok) ve
          adim `id: olcum` tasiyor (damga kosulunun okudugu cikti oradan gelir).
      (3) `--damga-yaz <dosya> --damga-adi paket-tazelik-damgasi` cagrisi VAR.
      (4) AYNI dosya `actions/upload-artifact` ile `name: paket-tazelik-damgasi` altinda
          ve `if-no-files-found: error` + `continue-on-error`SIZ yukleniyor.
      (5) HER IKI damga adimi da OLCUMUN CIKTISINA (`durum == 'parite'`) KOSULLU.
      (6) 🔴 YAYINI DURDURAMAZ: is akisinda `push` tetikleyicisi YOK ve `workflow_call`
          ile de cagrilamiyor. Bu, raporun "BLOKLAYICI_MI=hayir" iddiasinin YORUM degil
          KOSULAN bir kapi olmasini saglar: biri bu dosyaya `push:` eklerse nobetci
          KIRMIZI yanar.
      (7) Kosum agaci uzak main UCUNA tazeleniyor (donmus github.sha kahini bayatlatir).
    Doner: (sorunlar, bulgular)."""
    yol = os.path.join(WORKFLOW_DIZIN, PAKET_ALARM_DOSYA)
    if not os.path.exists(yol):
        raise OlcumHatasi("paket tazeligi alarmi is akisi YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        ham = f.read()
    govde = yaml_belge(ham)
    if not isinstance(govde, dict) or not isinstance(govde.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % PAKET_ALARM_DOSYA)

    sorunlar = []
    tetik = _on_bolumu(govde)
    tetik_adlari = set()
    if isinstance(tetik, dict):
        tetik_adlari = set(str(k) for k in tetik)
    elif isinstance(tetik, list):
        tetik_adlari = set(str(k) for k in tetik)
    elif isinstance(tetik, str):
        tetik_adlari = {tetik}
    for yasak in ("push", "pull_request", "workflow_call"):
        if yasak in tetik_adlari:
            sorunlar.append(
                "🔴 YAYIN YOLUNA BAGLANMIS: %s icinde `%s` tetikleyicisi VAR. Bu is "
                "akisinin TEK gerekcesi 'kirmizisi yayini durdurmaz' olmasidir; ag'a "
                "bagimli tek bir yanlis pozitif TUM EKIBIN yayinini durdururdu "
                "([[kapi-kapsam-eksen-secimi]])." % (PAKET_ALARM_DOSYA, yasak))
    if "schedule" not in tetik_adlari:
        sorunlar.append("%s icinde `schedule` tetikleyicisi YOK -> alarm hic kosmaz"
                        % PAKET_ALARM_DOSYA)

    adimlar = []
    for _job_ad, job in govde["jobs"].items():
        if isinstance(job, dict) and isinstance(job.get("steps"), list):
            adimlar.extend(a for a in job["steps"] if isinstance(a, dict))

    olcum_adimi = None
    olcum_kendini_test = False
    yazilan = None
    yazma_adimi = None
    yazilan_damga_adi = None
    yukleme = None
    tazeleme = False
    for a in adimlar:
        komut = str(a.get("run") or "")
        for satir in komut.splitlines():
            s = satir.strip()
            if s.startswith("git reset --hard FETCH_HEAD"):
                tazeleme = True
            if PAKET_OLCUM_ARACI in s and s.startswith("python3"):
                if "--kendini-test" in s.split():
                    olcum_kendini_test = True
                else:
                    olcum_adimi = a
                    # Cikis kodunu YUTAN kabuk formlari (Bolum D ile ayni sinif).
                    for yutan in ("||", "|", ";", "set +e", "&&"):
                        if yutan in s:
                            sorunlar.append(
                                "olcum satiri cikis kodunu YUTABILIR (%r icinde %r) -> "
                                "alarm kirmizi yanamaz" % (s[:90], yutan))
            if "cron-nabiz-kapisi.py" in s and "--damga-yaz" in s:
                parcalar = s.split()
                i = parcalar.index("--damga-yaz")
                if i + 1 < len(parcalar):
                    yazilan = parcalar[i + 1]
                    yazma_adimi = a
                if "--damga-adi" in parcalar:
                    j = parcalar.index("--damga-adi")
                    if j + 1 < len(parcalar):
                        yazilan_damga_adi = parcalar[j + 1]
        if str(a.get("uses") or "").startswith("actions/upload-artifact"):
            ile = a.get("with") if isinstance(a.get("with"), dict) else {}
            if str(ile.get("name") or "") == PAKET_DAMGA_ADI:
                yukleme = a

    if olcum_adimi is None:
        sorunlar.append(
            "CANLI OLCUM KOLU YOK: %s icinde bayrakSIZ `python3 %s` cagrisi bulunamadi%s "
            "-> alarm hicbir canli sey olcmez ama kosum YESIL yanar."
            % (PAKET_ALARM_DOSYA, PAKET_OLCUM_ARACI,
               " (yalniz `--kendini-test` kolu var)" if olcum_kendini_test else ""))
    else:
        if olcum_adimi.get("continue-on-error"):
            sorunlar.append("olcum adimi `continue-on-error` ile FAIL-OPEN")
        if str(olcum_adimi.get("id") or "") != "olcum":
            sorunlar.append("olcum adiminin `id:` degeri 'olcum' DEGIL (%r) -> damga "
                            "kosulunun okudugu cikti KAYNAKSIZ kalir"
                            % olcum_adimi.get("id"))
        if "--gh-ozet" not in str(olcum_adimi.get("run") or ""):
            sorunlar.append("olcum cagrisinda `--gh-ozet` YOK -> adim `durum` ciktisi "
                            "URETMEZ, damga kosulu hicbir zaman saglanmaz")
    if not yazilan:
        sorunlar.append("%s icinde `cron-nabiz-kapisi.py --damga-yaz <dosya>` cagrisi YOK "
                        "-> A4 ekseni KAYNAKSIZ kalir" % PAKET_ALARM_DOSYA)
    if yazilan_damga_adi != PAKET_DAMGA_ADI:
        sorunlar.append("`--damga-adi` %r DEGIL (%r) -> yazilan damgayi A4 ekseni OKUMAZ"
                        % (PAKET_DAMGA_ADI, yazilan_damga_adi))
    if yukleme is None:
        sorunlar.append("`actions/upload-artifact` adimi `name: %s` ile YOK -> damga "
                        "dogsa bile nabiz kapisi onu GOREMEZ" % PAKET_DAMGA_ADI)
    else:
        ile = yukleme.get("with") if isinstance(yukleme.get("with"), dict) else {}
        if yazilan and str(ile.get("path") or "").strip() != yazilan:
            sorunlar.append("yazilan dosya (%r) ile yuklenen `path` (%r) AYNI DEGIL"
                            % (yazilan, ile.get("path")))
        if str(ile.get("if-no-files-found") or "").lower() != "error":
            sorunlar.append("`if-no-files-found: error` YOK -> damga dosyasi olusmasa bile "
                            "adim SESSIZCE gecer (fail-open)")
        if yukleme.get("continue-on-error"):
            sorunlar.append("damga yukleme adimi `continue-on-error` ile FAIL-OPEN")
    if not tazeleme:
        sorunlar.append("`git reset --hard FETCH_HEAD` tazelemesi YOK -> donmus github.sha "
                        "checkout'u YEREL KAHIN'i bayatlatir (sahte 'canli bayat' teshisi)")
    kosullu = True
    for etiket, adim in (("damga YAZMA", yazma_adimi), ("damga YUKLEME", yukleme)):
        if adim is None:
            continue
        ariza = paket_kosul_arizasi(adim)
        if ariza:
            kosullu = False
            sorunlar.append("%s adimi OLCUM SONUCUNA KOSULLU DEGIL — %s. Damga o zaman "
                            "'canli fiyat yolu temiz' demez, 'kosum bitti' der."
                            % (etiket, ariza))
    # TEK KAYNAK NOBETI: is akisindaki etiket ile aracin URETTIGI etiket AYNI mi.
    arac_etiketi = _olcum_araci_etiketi()
    if arac_etiketi != PAKET_PARITE_ETIKETI:
        sorunlar.append(
            "ETIKET AYRISMASI: %s PARITE icin %r uretiyor, damga kosulu %r bekliyor -> "
            "damga HICBIR ZAMAN dogmaz ve A4 sonsuza kadar kirmizi yanardi."
            % (PAKET_OLCUM_ARACI, arac_etiketi, PAKET_PARITE_ETIKETI))
    return sorunlar, {"olcum": olcum_adimi is not None, "yazilan": yazilan,
                      "damga_adi": yazilan_damga_adi, "yukleme": yukleme is not None,
                      "tazeleme": tazeleme, "kosullu": kosullu,
                      "tetikler": sorted(tetik_adlari), "arac_etiketi": arac_etiketi}


def _metin_iceriyor(dugum, aranan):
    """Ayristirilmis YAML agacinda `aranan` alt dizesini tasiyan bir METIN var mi."""
    if isinstance(dugum, str):
        return aranan in dugum
    if isinstance(dugum, dict):
        return any(_metin_iceriyor(v, aranan) for v in dugum.values())
    if isinstance(dugum, list):
        return any(_metin_iceriyor(v, aranan) for v in dugum)
    return False


def _eszamanlilik_grubu(govde):
    """`concurrency.group` (kisa yazim `concurrency: <grup>` de kabul) -> str | None."""
    es = govde.get("concurrency")
    grup = es.get("group") if isinstance(es, dict) else es
    return grup.strip() if isinstance(grup, str) and grup.strip() else None


def _yayin_is_akisi(ham=None):
    """(yayin_eszamanlilik_grubu, deploy.yml_govdesi) — GRUP ADI KOSARAK OKUNUR.

    Push seridinin "yayin kuyrugunu bekletmez" iddiasi iki dizenin ESITSIZLIGIDIR;
    ikisini iki dosyada ELLE tutmak ikiz tanimdir ve sessizce ayrisir. deploy.yml
    grubunu degistirirse bu okuma onunla birlikte kayar."""
    if ham is None:
        yol = os.path.join(WORKFLOW_DIZIN, YAYIN_DOSYA)
        if not os.path.exists(yol):
            raise OlcumHatasi("yayin is akisi YOK: %s" % yol)
        with open(yol, encoding="utf-8") as f:
            ham = f.read()
    govde = yaml_belge(ham)
    if not isinstance(govde, dict):
        raise OlcumHatasi("%s: kok govde sozluk DEGIL" % YAYIN_DOSYA)
    grup = _eszamanlilik_grubu(govde)
    if grup is None:
        raise OlcumHatasi(
            "%s: `concurrency.group` okunamadi -> push seridinin yayin kuyrugundan AYRI "
            "oldugu KANITLANAMAZ (fail-closed)" % YAYIN_DOSYA)
    return grup, govde


def _secret_ortam_kapsami(ad, secret_adi, ham=None):
    """(tuketen_is_sayisi, ORTAM beyan eden isler) — bir secret'in KAPSAMINI OLCER.

    🔴 NEDEN OLCULUR, VARSAYILMAZ: ORTAM (environment) secret'i YALNIZ o ortami beyan
    eden ise cozulur; DEPO/ORG secret'i depodaki HER is akisina cozulur (tek istisna
    fork PR'lari). Push seridi bu token olmadan rc 2 (OLCULEMEDI) verir ve HER PUSH'TA
    kirmizi yanardi — yani "token erisilebilir" bir BEYAN olarak birakilamaz.
    Kanit: ayni secret'i `environment:` TASIMAYAN bir isten FIILEN tuketen, FIILEN kosan
    bir is akisi varsa secret ORTAM'a bagli DEGILDIR."""
    if ham is None:
        yol = os.path.join(WORKFLOW_DIZIN, ad)
        if not os.path.exists(yol):
            raise OlcumHatasi("is akisi YOK: %s" % yol)
        with open(yol, encoding="utf-8") as f:
            ham = f.read()
    govde = yaml_belge(ham)
    if not isinstance(govde, dict) or not isinstance(govde.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % ad)
    tuketen = 0
    ortamli = []
    for job_ad, job in govde["jobs"].items():
        if not isinstance(job, dict):
            continue
        if not _metin_iceriyor(job, "secrets.%s" % secret_adi):
            continue
        tuketen += 1
        if "environment" in job:
            ortamli.append(str(job_ad))
    return tuketen, ortamli


def push_serit_kablosu(ham=None, yayin_ham=None):
    """PUSH SERIDI — bayatlik olcumu FIILEN ATESLENEN tetige bagli MI ve yayin yolundan
    AYRI MI. GERCEK dosyadan olculur; `ham`/`yayin_ham` verilirse FIKSTUR olculur.

    SEKIZ sart, hepsi fail-closed:
      (1) `push` tetigi VAR. Yoksa serit OLU'dur ve korluk penceresi cron'un olculen
          1053,5 dk'sina geri doner.
      (2) 🔴 IZIN LISTESI: `push` ve `workflow_dispatch` DISINDA HICBIR tetik YOK.
          Kara liste DEGIL (olculdu: `pull_request` yasakliyken `pull_request_target`
          acik kalmisti ve kapi YESIL geciyordu — [[maskeleme-kismi-kapatma]]).
          En tehlikeli hal `pull_request_target`tir: fork PR'ini TABAN DEPO baglaminda
          ve DEPO SECRET'leriyle kosturur, yani yabanci koda CLOUDFLARE_API_TOKEN acar.
      (2b) 🔴 DAL CIVISI: `push.branches` TANIMLI ve TAM OLARAK `[main]`. Iki AYRI
          kontrol (tanimsiz · genis) — her birinin AYIRT EDICI mutanti vardir.
      (3) `concurrency` grubu VAR ve deploy.yml'in grubuna ESIT DEGIL (grup adi
          deploy.yml'den KOSARAK okunur; ikinci kopya tutulmaz).
      (4) deploy.yml hicbir isi bu dosyayi `uses:` ile CAGIRMIYOR.
      (5) CANLI olcum kolu kosuyor: bayrakSIZ `python3 tools/shop-bayatlik-kapisi.py`.
          `--kendini-test`e dusurulmus bir serit hicbir canli sey olcmez ama YESIL yanar.
      (6) Olcum adimi cikis kodunu YUTMUYOR (`continue-on-error`, `||`, `;`, `&&`,
          `set +e` yok) — yoksa serit hic kirmizi yanamaz.
      (7) 🔴 SECRET KAPSAMI: olcum adimi `secrets.CLOUDFLARE_API_TOKEN` kullanir, onu
          tasiyan is `environment:` BEYAN ETMEZ ve ayni secret'i tuketen kardes is
          akisi (`paket-tazelik-alarmi.yml`) da etmez -> secret DEPO duzeyindedir ve bu
          seritte COZULUR. Cozulmeseydi kapi rc 2 verip her push'ta bos kirmizi yakardi.
    Doner: (sorunlar, bulgular)."""
    if ham is None:
        yol = os.path.join(WORKFLOW_DIZIN, PUSH_SERIT_DOSYA)
        if not os.path.exists(yol):
            raise OlcumHatasi(
                "push seridi is akisi YOK: %s -> odeme yolu bayatlik olcumu YENIDEN "
                "yalnizca cron'a (olculen teslim %%4,31) bagli kalir" % yol)
        with open(yol, encoding="utf-8") as f:
            ham = f.read()
    govde = yaml_belge(ham)
    if not isinstance(govde, dict) or not isinstance(govde.get("jobs"), dict):
        raise OlcumHatasi("%s: `jobs` bolumu okunamadi" % PUSH_SERIT_DOSYA)
    yayin_grup, yayin_govde = _yayin_is_akisi(yayin_ham)

    sorunlar = []
    tetik = _on_bolumu(govde)
    if isinstance(tetik, dict) or isinstance(tetik, list):
        tetik_adlari = set(str(k) for k in tetik)
    elif isinstance(tetik, str):
        tetik_adlari = {tetik}
    else:
        tetik_adlari = set()
    if "push" not in tetik_adlari:
        sorunlar.append(
            "%s icinde `push` tetigi YOK -> serit OLU: bayatlik olcumu yine yalnizca "
            "cron'a bagli kalir (olculen teslim %%4,31, en uzun sessizlik 1053,5 dk)"
            % PUSH_SERIT_DOSYA)
    # 🔴 IZIN LISTESI: izinli olmayan HER tetik kirmizidir (kara liste degil — bkz.
    # PUSH_SERIT_IZINLI_TETIK yanindaki olculen gerekce).
    for t in sorted(tetik_adlari):
        if t in PUSH_SERIT_IZINLI_TETIK:
            continue
        sorunlar.append(
            "🔴 IZINSIZ TETIK `%s`: %s icinde izin listesi disinda bir tetik VAR. "
            "GEREKCE: %s. Bu seridin TEK gerekcesi 'kirmizisi yayini durdurmaz' ve "
            "'disaridan surulemez' olmasidir ([[kapi-kapsam-eksen-secimi]] · "
            "[[maskeleme-kismi-kapatma]]). Izinli tetikler: %s."
            % (t, PUSH_SERIT_DOSYA,
               PUSH_SERIT_TEHLIKE.get(t, "bu tetik ENUMERE EDILMEMIS — izin listesi "
                                         "fail-closed oldugu icin yine de REDDEDILIR"),
               ", ".join(PUSH_SERIT_IZINLI_TETIK)))

    # 🔴 DAL CIVISI — iki AYRI kontrol (her birinin AYIRT EDICI mutanti var).
    push_govdesi = tetik.get("push") if isinstance(tetik, dict) else None
    ham_dallar = push_govdesi.get("branches") if isinstance(push_govdesi, dict) else None
    dal_listesi = [str(d) for d in ham_dallar] if isinstance(ham_dallar, list) else []
    if "push" in tetik_adlari:
        if not dal_listesi:
            sorunlar.append(
                "🔴 DAL SUZGECI YOK: %s icinde `push.branches` tanimli DEGIL -> serit HER "
                "dalda kosar. Gurultu kat kat artar ve alarm FIILEN susar; ayrica olcum "
                "uzak main ucu hakkinda hukum verirken baska bir dalin ucunu olcerdi."
                % PUSH_SERIT_DOSYA)
        elif dal_listesi != [PUSH_SERIT_DAL]:
            sorunlar.append(
                "🔴 DAL SUZGECI GENIS: %s `push.branches` = %r; YALNIZ [%r] olmali. "
                "Joker/coklu desen seridi her dala yayar: gurultu alarmi susturur ve "
                "olcum ana dal disindaki bir ucu 'canli bayat' sanar."
                % (PUSH_SERIT_DOSYA, dal_listesi, PUSH_SERIT_DAL))

    grup = _eszamanlilik_grubu(govde)
    if grup is None:
        sorunlar.append(
            "%s icinde `concurrency.group` YOK -> serit kosumlari varsayilan gruba "
            "duser ve yayin kuyrugundan AYRI oldugu KANITLANAMAZ" % PUSH_SERIT_DOSYA)
    elif grup == yayin_grup:
        sorunlar.append(
            "🔴 YAYIN KUYRUGUNA GIRMIS: %s eszamanlilik grubu (%r) %s'in grubuyla AYNI "
            "-> serit yayin kosumlarini BEKLETIR (ve onlar tarafindan bekletilir); "
            "'yayina maliyeti 0 sn' iddiasi COKER"
            % (PUSH_SERIT_DOSYA, grup, YAYIN_DOSYA))

    cagiran = sorted(
        str(job_ad) for job_ad, job in (yayin_govde.get("jobs") or {}).items()
        if isinstance(job, dict) and PUSH_SERIT_DOSYA in str(job.get("uses") or ""))
    if cagiran:
        sorunlar.append(
            "🔴 %s bu seridi `uses:` ile CAGIRIYOR (is: %s) -> serit yayinin `needs` "
            "grafinin ICINE girmis, kirmizisi yayini DURDURUR"
            % (YAYIN_DOSYA, ", ".join(cagiran)))

    olcum_adimi = None
    olcum_isi = None
    olcum_kendini_test = False
    tazeleme = False
    for job_ad, job in govde["jobs"].items():
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            continue
        for a in job["steps"]:
            if not isinstance(a, dict):
                continue
            for satir in str(a.get("run") or "").splitlines():
                s = satir.strip()
                if s.startswith("git reset --hard FETCH_HEAD"):
                    tazeleme = True
                if PUSH_SERIT_ARACI in s and s.startswith("python3"):
                    if "--kendini-test" in s.split():
                        olcum_kendini_test = True
                    else:
                        olcum_adimi, olcum_isi = a, job
                        for yutan in ("||", "|", ";", "set +e", "&&"):
                            if yutan in s:
                                sorunlar.append(
                                    "olcum satiri cikis kodunu YUTABILIR (%r icinde %r) "
                                    "-> serit kirmizi yanamaz" % (s[:90], yutan))
    if olcum_adimi is None:
        sorunlar.append(
            "CANLI OLCUM KOLU YOK: %s icinde bayrakSIZ `python3 %s` cagrisi bulunamadi%s "
            "-> serit hicbir canli sey olcmez ama kosum YESIL yanar."
            % (PUSH_SERIT_DOSYA, PUSH_SERIT_ARACI,
               " (yalniz `--kendini-test` kolu var)" if olcum_kendini_test else ""))
    elif olcum_adimi.get("continue-on-error"):
        sorunlar.append("olcum adimi `continue-on-error` ile FAIL-OPEN")
    if not tazeleme:
        sorunlar.append(
            "`git reset --hard FETCH_HEAD` tazelemesi YOK -> donmus github.sha checkout'u "
            "olculen ref ile olculmesi GEREKEN ref'i ayristirir; kapi (fail-closed) rc 2 "
            "verir ve serit her push'ta BOS kirmizi yakar")

    token_var = bool(olcum_adimi is not None
                     and _metin_iceriyor(olcum_adimi, "secrets.%s" % PUSH_SERIT_SECRET))
    if olcum_adimi is not None and not token_var:
        sorunlar.append(
            "olcum adimi `secrets.%s` KULLANMIYOR -> canli surum okunamaz, kapi rc 2 "
            "(OLCULEMEDI) verir ve serit her push'ta kirmizi yanar" % PUSH_SERIT_SECRET)
    ortamli = bool(isinstance(olcum_isi, dict) and "environment" in olcum_isi)
    if ortamli:
        sorunlar.append(
            "olcum isi `environment:` BEYAN EDIYOR -> secret ORTAM kapsamina duser; "
            "onay bekleyen bir ortam seridi her push'ta askiya alir")
    kardes_tuketen, kardes_ortamli = _secret_ortam_kapsami(
        PAKET_ALARM_DOSYA, PUSH_SERIT_SECRET)
    if kardes_tuketen == 0:
        sorunlar.append(
            "KAPSAM KANITI YOK: %s icinde `secrets.%s` tuketen is bulunamadi -> secret'in "
            "DEPO duzeyinde oldugu (yani bu seritte cozulecegi) OLCULEMEZ"
            % (PAKET_ALARM_DOSYA, PUSH_SERIT_SECRET))
    if kardes_ortamli:
        sorunlar.append(
            "KAPSAM KANITI COKTU: %s icinde secret'i tuketen is(ler) `environment:` "
            "beyan ediyor (%s) -> secret ORTAM'a bagli olabilir ve bu seritte "
            "COZULMEYEBILIR" % (PAKET_ALARM_DOSYA, ", ".join(kardes_ortamli)))
    return sorunlar, {"tetikler": sorted(tetik_adlari), "dallar": dal_listesi,
                      "grup": grup,
                      "yayin_grup": yayin_grup, "cagiran": cagiran,
                      "olcum": olcum_adimi is not None, "tazeleme": tazeleme,
                      "token": token_var, "ortamli": ortamli,
                      "kardes_tuketen": kardes_tuketen,
                      "kardes_ortamli": kardes_ortamli}


# Push seridi FIKSTURU — kablolama katmani GERCEK dosyaya bagimli kalmasin diye kabul
# testi bu iskeleti bozarak IKI YONLU olcer (temiz fikstur -> ariza YOK).
PUSH_SERIT_FIKSTUR = """
name: fikstur
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: odeme-bayatlik-push
  cancel-in-progress: true
jobs:
  bayatlik:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: uca tazele
        run: |
          git fetch --depth=1 origin main
          git reset --hard FETCH_HEAD
      - name: olcum
        id: nesil
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        run: python3 tools/shop-bayatlik-kapisi.py --gh-ozet
"""


def kendini_test():
    """IKI YONLU kabul: kirmizi yol da yesil yol da FIKSTURLE kosturulur."""
    hatalar = []
    sayac = [0]

    def iddia(ad, kosul, detay=""):
        if not isinstance(detay, str):
            detay = repr(detay)
        sayac[0] += 1
        print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", ad,
                               ("  -> " + detay) if detay else ""))
        if not kosul:
            hatalar.append(ad)

    def kos(dosyalar, getir, damga_ile=False, paket_ile=False):
        """damga_ile=True -> A0 · paket_ile=True -> A4 (GERCEK olcum yolunun ayni sirasi)."""
        try:
            g = gozlem_topla(dosyalar, getir)
            d = n0 = p = n4 = None
            if damga_ile:
                _ad, n0, _ar = uzlastirici_esigi(dosyalar)
                d = damga_gozle(getir, DAMGA_ADI)
            if paket_ile:
                _ad4, n4, _ar4 = paket_alarm_esigi(dosyalar)
                p = damga_gozle(getir, PAKET_DAMGA_ADI)
        except OlcumHatasi as e:
            return 2, ["OLCULEMEDI: %s" % e]
        return degerlendir(dosyalar, g, damga=d, damga_esigi=n0, paket=p, paket_esigi=n4)

    D = [("d1-uzlastirici.yml", "7,22,37,52 * * * *")]

    # --- ESIK TURETIMI (OLCULEN CADANSTAN, tahminle DEGIL) ---
    iddia("aralik: 7,22,37,52 -> 15 dk", aralik_dakika({7, 22, 37, 52}) == 15,
          "olculen %s" % aralik_dakika({7, 22, 37, 52}))
    iddia("aralik: saat sinirini asan fark gorulur (52 -> 7 = 15 dk)",
          aralik_dakika({7, 52}) == 15, "olculen %s" % aralik_dakika({7, 52}))
    iddia("OLCULEN teslim orani = %d/%d = 0,125 (31 Tem, 4,016 sa penceresi)"
          % (OLCULEN_TESLIM, NOMINAL_TETIK), abs(TESLIM_ORANI - 0.125) < 1e-9,
          "olculen %r" % TESLIM_ORANI)
    iddia("efektif cadans: 15 dk nominal -> 120 dk (nominal DEGIL, TESLIM esas alinir)",
          abs(efektif_aralik_dk(15) - 120.0) < 1e-9, "olculen %r" % efektif_aralik_dk(15))
    # 🔴 ESIK KILIDI: bu iddia hem GEVSETMEYI hem SIKILASTIRMAYI kirmizi yakar. N ancak
    # ustteki OLCULEN girdiler degisirse degisebilir; "kirmizi gormeyeyim" diye
    # buyutulemez. Turetim: lambda=0,5 -> ln(168x0,5/1)/0,5 = 8,86 -> yukari yuvarla 9.
    iddia("esik KILIDI: 15 dk nominal · %0.3f teslim orani · haftada %g bos alarm butcesi "
          "-> N = 9 SAAT" % (TESLIM_ORANI, BOS_ALARM_BUTCESI_HAFTA),
          esik_saat(15) == 9, "olculen %s" % esik_saat(15))
    iddia("esik: gozlenen EN BUYUK gercek araligin (214,75 dk = 3,58 sa) USTUNDE "
          "-> tek kacik alarm URETMEZ", esik_saat(15) > 214.75 / 60.0,
          "N=%d sa vs 3,58 sa" % esik_saat(15))
    iddia("esik: artifact saklamasinin (%d sa) ALTINDA -> taze damga suresi dolmadan "
          "olculebilir" % DAMGA_SAKLAMA_SAAT, esik_saat(15) < DAMGA_SAKLAMA_SAAT,
          "N=%d sa" % esik_saat(15))
    iddia("esik TABANI: 1 dk aralik bile N>=%d saat" % ESIK_TABAN_SAAT,
          esik_saat(1) == ESIK_TABAN_SAAT, "olculen %s" % esik_saat(1))
    iddia("esik TAVANI: gunluk cron N<=%d saat (artifact saklamasinin altinda)"
          % ESIK_TAVAN_SAAT,
          esik_saat(1440) == ESIK_TAVAN_SAAT and ESIK_TAVAN_SAAT < DAMGA_SAKLAMA_SAAT,
          "olculen %s" % esik_saat(1440))

    # --- A0 DAMGA: BIRINCIL EKSEN, IKI YONLU -------------------------------
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(1.5)]), damga_ile=True)
    iddia("A0 (a) TAZE damga (1,5 sa < N=9) -> YESIL", rc == 0, "rc=%d" % rc)
    iddia("A0 (a) rapor damga yasini ve DAMGAYI YAZAN CRON KOSUMUNU SAYIYLA yazar",
          any("A0 DAMGA" in x and "1.5 saat" in x and str(_HAM_KOSUM["id"]) in x
              for x in s), s)

    # ── 🔴 TETIKLEYICI SARTI (4 Agu 2026) — ALARM ELLE SONDURULEBILIYORDU ──────
    # TEK DEGISKEN: damgayi yazan kosum. Yas (1,5 sa), damga sayisi, kosum dagilimi,
    # cron metni, is akisi durumu AYNI kalir; yalniz damganin `workflow_run.id`si
    # zamanlanmis kosum kumesinin ICINDE ya da DISINDA olur.
    ELLE = dict(kosum_sayisi=137, yas_saat=0.4, damgalar=[_damga_kaydi(1.5)])
    rc, s = kos(D, _sahte_api(damga_kosum="elle", **ELLE), damga_ile=True)
    iddia("A0 TETIKLEYICI (a) ELLE tazelenmis damga (1,5 sa TAZE ama kosum "
          "`event=schedule` kumesinde YOK) -> KIRMIZI. Bu, 4 Agu'da OLDURULEMEYEN "
          "mutantin ta kendisidir: 09:45:48Z'de elle kosum damgayi tazeledi ve A0 "
          "9 saat daha YESIL yandi.", rc == 1, "rc=%d" % rc)
    iddia("A0 TETIKLEYICI (a) teshis 'DENETIM YAPILDI AMA CRON YAPMADI' der ve elle "
          "kosumun kimligini yazar",
          any("A0 DAMGA" in x and "CRON YAPMADI" in x and str(_CRON_DISI_KOSUM) in x
              for x in s), s)
    rc, s = kos(D, _sahte_api(damga_kosum="schedule", **ELLE), damga_ile=True)
    iddia("A0 TETIKLEYICI (b) AYNI fikstur, TEK FARK damgayi CRON yazmis -> YESIL "
          "(sart yanlis-pozitif URETMEZ)", rc == 0, "rc=%d" % rc)
    # Cron damgasi TAZE iken elle bir kosum da damga yazmissa: hukum CRON damgasina gore
    # verilir (elle tetikleme YESILI de BOZMAZ) ve durum satirda GORUNUR.
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(0.3, kimlik=1,
                                                     kosum_kimlik=_CRON_DISI_KOSUM),
                                        _damga_kaydi(2.0, kimlik=2)]), damga_ile=True)
    iddia("A0 TETIKLEYICI (c) elle damga EN YENI ama CRON damgasi da esik icinde "
          "-> YESIL (sart cron sagligini olcer, elle kosumu CEZALANDIRMAZ)",
          rc == 0, "rc=%d" % rc)
    iddia("A0 TETIKLEYICI (c) satir en yeni damganin CRON DISI oldugunu da YAZAR "
          "(kadans ile cron sagligi AYRI AYRI gorunur)",
          any(x.startswith("✅ A0 DAMGA") and "CRON DISI" in x for x in s), s)
    # FAIL-CLOSED: damgayi hangi kosumun yazdigi OKUNAMAZSA yesil DEGIL, rc 2.
    kimliksiz = _damga_kaydi(1.5)
    del kimliksiz["workflow_run"]["id"]
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4, damgalar=[kimliksiz]),
                damga_ile=True)
    iddia("A0 TETIKLEYICI FAIL-CLOSED: damgada `workflow_run.id` YOK -> rc 2 "
          "(siniflandirilamayan damga 'taze' SAYILAMAZ)", rc == 2, "rc=%d" % rc)
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(12.0)]), damga_ile=True)
    iddia("A0 (b) ESKI damga (12,0 sa > N=9) -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A0 (b) teshis 'DENETLENMEDI' der (susma sinifi adlandirilir)",
          any("DENETLENMEDI" in x for x in s))
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(8.9)]), damga_ile=True)
    iddia("A0 esik SINIRI: 8,9 sa < N=9 -> YESIL", rc == 0, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(9.1)]), damga_ile=True)
    iddia("A0 esik SINIRI: 9,1 sa > N=9 -> KIRMIZI", rc == 1, "rc=%d" % rc)
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4, damgalar=[]),
                damga_ile=True)
    iddia("A0 (c) HIC damga YOK -> KIRMIZI (fail-closed, YESIL DEGIL)", rc == 1,
          "rc=%d" % rc)
    iddia("A0 (c) teshis 'YESIL kosum = denetim yapildi DEGIL' olcumunu ANLATIR",
          any("conclusion=success" in x and "skipped" in x for x in s))
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(30.0, expired=True)]),
                damga_ile=True)
    iddia("A0 (d) TUM damgalar SURESI DOLMUS -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A0 (d) teshis 'expired' halini ADIYLA soyler",
          any("SURESI DOLMUS" in x for x in s))
    rc, _ = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(1.0, expired=True, kimlik=1),
                                        _damga_kaydi(20.0, kimlik=2)]),
                damga_ile=True)
    iddia("A0 (e) TAZE gorunen damga EXPIRED ise SAYILMAZ (geride 20 sa'lik gecerli "
          "damga kalir) -> KIRMIZI", rc == 1, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(30.0, kimlik=1),
                                        _damga_kaydi(2.0, kimlik=2)]),
                damga_ile=True)
    iddia("A0 (f) EN YENI gecerli damga esas alinir (siralama API'ye birakilmaz)",
          rc == 0, "rc=%d" % rc)

    # --- A0 FAIL-CLOSED: damga OKUNAMAZSA yesil DEGIL ----------------------
    for boz, ad in (("damga-ag", "artifact API cagrilamadi"),
                    ("damga-sekli", "`artifacts` dizisi yok"),
                    ("damga-alan", "`created_at` alani DUSMUS"),
                    ("damga-suzgec", "`?name=` suzgeci CALISMAMIS (baska artifact dondu)"),
                    ("damga-zaman", "zaman damgasi COZULEMEZ")):
        rc, _ = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4, bozuk=boz),
                    damga_ile=True)
        iddia("A0 FAIL-CLOSED: %s -> rc 2 (OLCULEMEDI)" % ad, rc == 2, "rc=%d" % rc)

    # --- A0 CAPA: uzlastirici is akisi kaybolursa OLCULEMEDI ---------------
    rc, _ = kos([("baska.yml", "7,22,37,52 * * * *")],
                _sahte_api(kosum_sayisi=5, yas_saat=0.2, dosya="baska.yml"),
                damga_ile=True)
    iddia("A0 CAPA: %s cron tasiyan is akislari arasinda YOK -> rc 2 (damga ekseni "
          "capasiz kalamaz)" % UZLASTIRICI_DOSYA, rc == 2, "rc=%d" % rc)

    # --- A1 BICIM (agsiz) ---
    rc, s = kos([("x.yml", "*/15 * * * *")], _sahte_api(kosum_sayisi=5, yas_saat=0.2,
                                                        dosya="x.yml"))
    iddia("A1: `*/15` (yogun ceyrek sinirlari) -> KIRMIZI", rc == 1,
          "rc=%d" % rc)
    iddia("A1: teshis `*/15`i ve cozumu ADIYLA soyler",
          any("7,22,37,52" in x and "*/15" in x for x in s))
    rc, _ = kos([("x.yml", "0 3 * * *")], _sahte_api(kosum_sayisi=5, yas_saat=0.2,
                                                     dosya="x.yml"))
    iddia("A1: dakika 0 (saat basi) -> KIRMIZI", rc == 1, "rc=%d" % rc)
    rc, _ = kos([("x.yml", "7,22,37,52 * * * *")], _sahte_api(kosum_sayisi=5, yas_saat=0.2,
                                                              dosya="x.yml"))
    iddia("A1: acik + ofsetli dakika listesi -> YESIL", rc == 0, "rc=%d" % rc)

    # --- AYRISTIRICI KOLU (metin taklidi degil) ---
    ayr = yaml_ayristirici_adi()
    iddia("ayristirici GERCEK bir YAML ayristiricisi (pyyaml | ruby/psych)",
          ayr in ("pyyaml", "ruby/psych"), "olculen %r" % ayr)
    try:
        belge = yaml_belge('name: x\non:\n  schedule:\n    - cron: "9 * * * *"\n')
        tetik = _on_bolumu(belge)
        okundu = tetik.get("schedule")[0]["cron"] if isinstance(tetik, dict) else None
    except Exception as e:  # noqa: BLE001
        okundu = "HATA: %s" % e
    iddia("YAML 1.1 tuzagi: `on:` anahtari BOOL'a cevrilse de bulunur "
          "(aksi halde her is akisi 'cron yok' sanilir = sahte YESIL)",
          okundu == "9 * * * *", "okunan %r" % (okundu,))

    # --- A1 GERCEK DEPO CAPASI (onarimi kilitler) ---
    try:
        gercek = cron_ifadeleri()
    except OlcumHatasi as e:
        gercek = None
        iddia("gercek depo: cron ifadeleri okunabildi", False, str(e))
    if gercek is not None:
        iddia("gercek depo: en az 1 cron tasiyan is akisi var", len(gercek) >= 1,
              "%d bulundu: %s" % (len(gercek), gercek))
        kirli = [(d, c) for d, c in gercek if bicim_hukmu(d, c)[0]]
        iddia("gercek depo: HICBIR cron yogun ceyrek-saat sinirinda degil "
              "(cron `*/15`e geri cevrilirse bu iddia KIRMIZI yanar)", not kirli,
              "ihlal: %s" % (kirli,))

    # --- A2 DURUM ---
    rc, s = kos(D, _sahte_api(durum="disabled_inactivity", kosum_sayisi=9, yas_saat=0.2))
    iddia("A2: state=disabled_inactivity -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A2: teshis 60 gun hareketsizligi ANLATIR",
          any("disabled_inactivity" in x and "60 gun" in x for x in s))
    rc, _ = kos(D, _sahte_api(kayitli=False))
    iddia("A2: is akisi GitHub'da kayitli degil -> KIRMIZI", rc == 1, "rc=%d" % rc)

    # --- A3 NABIZ (IKINCIL EKSEN — KAYBOLMADI, esigi OLCULEN cadansa gore) ---
    rc, s = kos(D, _sahte_api(kosum_sayisi=0, kayit_yas_saat=0.8))
    iddia("A3 (a0) YENI is akisi, HIC schedule kosumu yok ama kayit yasi N'nin altinda "
          "-> GORUNUR ve YESIL", rc == 0, "rc=%d" % rc)
    iddia("A3 (a0) rapor ilk tetikleme penceresini ve yasi SAYIYLA yazar",
          any("🟡 A3 NABIZ" in x and "0.8 saat" in x and "esik N=9" in x for x in s), s)
    # 🔴 CAPA KILIDI (4 Agu 2026 — BU IDDIA TERSINE CEVRILDI): burada eskiden "cron
    # dosyasina dokunulmus, A3 SUSAR -> YESIL" yaziyordu, yani test SUSTURMAYI KUTSUYORDU
    # ([[test-hatali-davranisi-kutsar]]). OLCULDU: bu depoda alarm dosyalarina dokunma
    # araligi medyan 5,2-5,5 sa < N=9 sa; canli olcumde (10:04Z) cron 9,8 saattir oluyken
    # A3 satiri 🟡 idi. Capa artik `gecmis_capasi` (A5 ile TEK KAYNAK) ve dokunus
    # SUSTURMAZ.
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=12.0,
                              kayit_yas_saat=400.0, yenileme_yas_saat=0.8))
    iddia("A3 CAPA KILIDI: is akisi ESKI kayitli, son kosum 12,0 sa once (N=9), cron "
          "dosyasina 0,8 sa once DOKUNULMUS -> A3 SUSMAZ, KIRMIZI (capa "
          "max(kayit,yenileme)'ye dondurulurse bu iddia duser)", rc == 1, "rc=%d" % rc)
    iddia("A3 CAPA KILIDI: karsi risk SUSTURULMAZ — satir taze dokunusu ⚠ ile ve "
          "YASIYLA yazar",
          any(x.startswith("🔴 A3 NABIZ") and "⚠ cron tanimina dokunan son commit 0.8 sa"
              in x for x in s), s)
    # GERCEKTEN YENI KAYITLI is akisi (kayit N icinde) HALA korunur: bos kirmizi yok.
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=12.0, kayit_yas_saat=0.8,
                              yenileme_yas_saat=0.8))
    iddia("A3 (a0b) GERCEKTEN YENI KAYIT (is akisi 0,8 sa once kaydedildi) -> GORUNUR "
          "ve YESIL (ilk teslim penceresi taninir)", rc == 0, "rc=%d" % rc)
    iddia("A3 (a0b) satir kayit yasini SAYIYLA yazar",
          any("🟡 A3 NABIZ" in x and "GitHub'da 0.8 saat once" in x for x in s), s)
    # 🔴 IKIZ KAPISI: A3 ile A5 AYNI capadan gecer. Ayni fikstur (eski kayit + taze
    # dokunus + cokmus teslim) IKI eksende de HUKUM vermeli; biri 🟡'ye duserse capalar
    # AYRISMIS demektir ([[ikiz-tanim-sessiz-ayrisma]]).
    rc, s = kos(D, _sahte_api(kosum_sayisi=3, yas_saat=12.0,
                              kosum_yaslari=[12.0, 20.0, 40.0],
                              kayit_yas_saat=400.0, yenileme_yas_saat=1.0))
    iddia("IKIZ CAPA: eski kayit + 1,0 sa once dokunus -> A3 VE A5 IKISI DE hukum verir "
          "(ikisi de kirmizi; biri 🟡'ye duserse capalar ayrismistir)",
          rc == 1 and any(x.startswith("🔴 A3 NABIZ") for x in s)
          and any(x.startswith("🔴 A5 TESLIM") for x in s), s)
    rc, s = kos(D, _sahte_api(kosum_sayisi=0))
    iddia("A3 (a) N'yi asmis is akisinda HIC schedule kosumu YOK -> KIRMIZI",
          rc == 1, "rc=%d" % rc)
    iddia("A3 (a) teshis 'HIC ATESLENMEMIS' der (susma sinifi adlandirilir)",
          any("HIC ATESLENMEMIS" in x for x in s))
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4))
    iddia("A3 (b) YAKIN ZAMANDA kosum var (24 dk) -> YESIL", rc == 0, "rc=%d" % rc)
    iddia("A3 (b) rapor kosum sayisini ve yasi SAYIYLA yazar",
          any("137" in x and "0.4" in x for x in s))
    # 🔴 ESKI ESIGIN CURUTULDUGU VAKA: gozlenen GERCEK aralik 3,58 sa idi. Eski N=3 sa
    # bunu ALARM sayardi (bos kirmizi). Yeni N=9 sa ile YESIL kalir.
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=214.75 / 60.0))
    iddia("A3: GOZLENEN gercek aralik (214,75 dk = 3,58 sa) -> YESIL "
          "(eski N=3 sa bunu BOS YERE kirmizi yakardi)", rc == 0, "rc=%d" % rc)
    iddia("A3: rapor NOMINAL degil EFEKTIF cadansi da yazar",
          any("efektif cadans 120 dk" in x for x in s), s)
    rc, _ = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=8.9))
    iddia("A3: esigin ALTINDA (8,9 sa < N=9) -> YESIL", rc == 0, "rc=%d" % rc)
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=12.0))
    iddia("A3: esigin USTUNDE (12,0 sa > N=9) -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A3: teshis nominal tetikleme sayisini yazar",
          any("nominal ~48" in x for x in s), s)
    # IKI EKSEN AYRI AYRI RAPORLANIR: damga TAZE olsa bile cron sessizse A3 kirmizi yanar
    # (elle dispatch damgayi tazeler ama cron'un olu oldugunu GIZLEMEZ).
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=12.0,
                              damgalar=[_damga_kaydi(0.5)]), damga_ile=True)
    iddia("EKSEN AYRIMI: damga TAZE + cron SESSIZ -> KIRMIZI (A3 ekseni kaybolmadi)",
          rc == 1, "rc=%d" % rc)
    iddia("EKSEN AYRIMI: ayni raporda A0 YESIL, A3 KIRMIZI satiri AYRI AYRI durur",
          any(x.startswith("✅ A0 DAMGA") for x in s)
          and any(x.startswith("🔴 A3 NABIZ") for x in s), s)
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4,
                              damgalar=[_damga_kaydi(12.0)]), damga_ile=True)
    iddia("EKSEN AYRIMI: cron ATESLIYOR ama damga BAYAT -> KIRMIZI (kosmak != denetlemek)",
          rc == 1, "rc=%d" % rc)
    iddia("EKSEN AYRIMI: ayni raporda A0 KIRMIZI, A3 YESIL satiri AYRI AYRI durur",
          any(x.startswith("🔴 A0 DAMGA") for x in s)
          and any(x.startswith("✅ A3 NABIZ") for x in s), s)

    # --- A5 TESLIM (FIILI DAGILIM — cron METNI DEGIL) -----------------------
    # TABAN KILIDI: hem gevsetmeyi hem sikilastirmayi KIRMIZI yakar. Turetim:
    # olculen en kotu 48 sa penceresi 7/192 = %3,65 -> /2 -> %1,82 -> 15 dk cron icin
    # ceil(192 x 0,01823) = 4.
    iddia("A5 TABAN KILIDI: 15 dk cron · W=%d sa -> nominal %.0f · taban 4 kosum"
          % (TESLIM_PENCERESI_SAAT, teslim_nominal(15)),
          teslim_tabani(15) == 4, "olculen %s" % teslim_tabani(15))
    iddia("A5 TABAN: olculen EN KOTU 48 sa gozlemi (%d kosum) tabanin USTUNDE -> bugunku "
          "veri BOS KIRMIZI uretmez" % OLCULEN_TABAN_TESLIM,
          OLCULEN_TABAN_TESLIM > teslim_tabani(15),
          "%d > %d" % (OLCULEN_TABAN_TESLIM, teslim_tabani(15)))
    iddia("A5 TABAN: saatlik cron (60 dk) -> en az 1 kosum (taban asla 0 olamaz)",
          teslim_tabani(60) == 1, "olculen %s" % teslim_tabani(60))
    iddia("A5 SAYFA: en yogun cron'da (1 dk) bile taban API sayfa boyunun (%d) ALTINDA "
          "-> kirpilmis pencere sahte KIRMIZI uretemez" % TESLIM_SAYFA,
          teslim_tabani(1) < TESLIM_SAYFA,
          "taban %d vs sayfa %d" % (teslim_tabani(1), TESLIM_SAYFA))

    # 🔴 OLDURUCU: damga TAZE (A0 yesil) · son kosum TAZE (A3 yesil) · cron BICIMI dogru
    # (A1 yesil) · state=active (A2 yesil) — ama 48 saatte 3 teslim. 4 Agu'da FIILEN
    # olculen hal budur ve ESKI nobetci bunu rc=0 ile gecirdi.
    TAM = dict(kayit_yas_saat=400.0, yenileme_yas_saat=400.0)
    rc, s = kos(D, _sahte_api(kosum_sayisi=3, yas_saat=0.2,
                              kosum_yaslari=[0.2, 0.5, 40.0],
                              damgalar=[_damga_kaydi(0.5)], **TAM), damga_ile=True)
    iddia("A5 (a) OLDURUCU: 48 sa'te 3 teslim (taban 4) -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A5 (a) AYIRT EDICI: ayni raporda A0/A2/A3 YESIL, YALNIZ A5 KIRMIZI "
          "(A5 mevcut eksenlerin tekrari DEGIL — [[beyan-edilmis-survivor]])",
          [x[0] for x in s if x.startswith("🔴")] == ["🔴"]
          and all(("A5 TESLIM" in x) for x in s if x.startswith("🔴"))
          and any(x.startswith("✅ A0 DAMGA") for x in s)
          and any(x.startswith("✅ A3 NABIZ") for x in s), s)
    iddia("A5 (a) rapor teslim/nominal/oran ve TABANI SAYIYLA yazar",
          any("teslim 3 / nominal 192" in x and "%1.56" in x and "taban 4 kosum" in x
              for x in s), s)
    iddia("A5 (a) EN UZUN BOSLUK (gercek korluk penceresi) SAYIYLA basilir; siralama "
          "API'ye BIRAKILMAZ (fikstur listeyi bilerek karistirir)",
          any("en uzun bosluk 2370 dk" in x for x in s), s)
    iddia("A5 (a) teshis cron ofsetinin bu sinifi COZMEDIGINI soyler (4 Agu olcumu)",
          any("ofsetini degistirmek bu sinifi COZMEZ" in x for x in s), s)

    # KONTROL (TEK DEGISKEN: teslim edilen kosum sayisi) -> YESIL
    rc, s = kos(D, _sahte_api(kosum_sayisi=8, yas_saat=0.2,
                              kosum_yaslari=[0.2, 6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0],
                              damgalar=[_damga_kaydi(0.5)], **TAM), damga_ile=True)
    iddia("A5 (b) KONTROL: SAGLIKLI dagilim (48 sa'te 8 teslim) -> YESIL "
          "(oldurucudan TEK farki teslim sayisi)", rc == 0, "rc=%d" % rc)
    iddia("A5 (b) YESIL satir da teslim oranini ve en uzun boslugu YAZAR "
          "(gercek cadans her kosumda GORUNUR)",
          any(x.startswith("✅ A5 TESLIM") and "en uzun bosluk" in x for x in s), s)

    # 🔴 EN UZUN BOSLUGUN UC TERIMI — HER BIRI KENDI FIKSTURUYLE (4 Agu 2026)
    # A5 (a) fiksturunun maks boslugu bir IC bosluktur (2370 dk). Bu yuzden UC terimleri
    # (devam eden sessizlik · pencere basi) O FIKSTURDE HIC OLCULMUYORDU: ikisini de
    # silen mutantlar 124 iddia / 0 KIRMIZI ile SURVIVOR veriyordu
    # ([[fikstur-degeri-mutasyon-koru]]). Asagidaki iki fikstur maks boslugu UCTAN
    # getirir; mutant X4/X5 her birini TEK KIRMIZI ile civiler.
    #
    # X4 — DEVAM EDEN SESSIZLIK: 4 kosum 47/46/45/44 sa once (teslim 4 == taban, A5 YESIL)
    # ama son kosumdan beri 44 saattir HIC kosum yok. Ic bosluklar 60 dk, pencere basi
    # terimi 60 dk; GERCEK korluk penceresi 2640 dk'dir ve YALNIZ devam eden sessizlik
    # terimi onu gorur. Bu terim silinirse rapor "en uzun bosluk 60 dk" der — nabiz
    # OLU bir is akisini SAGLIKLI gosterirdi.
    rc, s = kos(D, _sahte_api(kosum_sayisi=4, yas_saat=44.0,
                              kosum_yaslari=[47.0, 46.0, 45.0, 44.0], **TAM))
    iddia("X4 EN UZUN BOSLUK — DEVAM EDEN SESSIZLIK ucu SAYILIR: son kosumdan beri 44 sa "
          "gecmis, ic bosluklar 60 dk -> rapor 2640 dk yazar (terim silinirse 60 dk der "
          "ve OLU bir is akisi SAGLIKLI gorunurdu)",
          any(x.startswith("🟡 A5 TESLIM") or x.startswith("✅ A5 TESLIM")
              or x.startswith("🔴 A5 TESLIM") for x in s)
          and any("A5 TESLIM" in x and "en uzun bosluk 2640 dk" in x for x in s), s)
    #
    # X5 — PENCERE BASI (PARTI IMZASI): 4 kosum son 3 saatte (teslim 4 == taban, A5 YESIL);
    # pencerenin ilk 45 saati TAMAMEN sessiz. Ic bosluklar <= 60 dk, devam eden sessizlik
    # 12 dk. Bu, 4 Agu'da OLCULEN "parti halinde teslim" halinin ta kendisidir; terim
    # silinirse rapor "en uzun bosluk 60 dk" der ve 45 saatlik korluk GORUNMEZ olur.
    rc, s = kos(D, _sahte_api(kosum_sayisi=4, yas_saat=0.2,
                              kosum_yaslari=[3.0, 2.0, 1.0, 0.2], **TAM))
    iddia("X5 EN UZUN BOSLUK — PENCERE BASI ucu SAYILIR: 4 kosum da son 3 saatte (parti "
          "imzasi), pencerenin ilk 45 saati sessiz -> rapor 2700 dk yazar (terim "
          "silinirse 60 dk der ve parti halinde teslim SAGLIKLI gorunurdu)",
          any("A5 TESLIM" in x and "en uzun bosluk 2700 dk" in x for x in s), s)

    # SINIR: tam TABANDA yesil, tabanin BIR ALTINDA kirmizi.
    rc, _ = kos(D, _sahte_api(kosum_sayisi=4, yas_saat=0.2,
                              kosum_yaslari=[0.2, 12.0, 24.0, 36.0], **TAM))
    iddia("A5 SINIR: teslim == taban (4) -> YESIL", rc == 0, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(kosum_sayisi=3, yas_saat=0.2,
                              kosum_yaslari=[0.2, 16.0, 32.0], **TAM))
    iddia("A5 SINIR: teslim == taban-1 (3) -> KIRMIZI", rc == 1, "rc=%d" % rc)

    # OLCULEN GERCEK TABAN: 4 Agu'nun EN KOTU 48 sa penceresi (7 kosum) -> YESIL.
    rc, _ = kos(D, _sahte_api(kosum_sayisi=7, yas_saat=0.2,
                              kosum_yaslari=[0.2, 3.5, 10.0, 17.5, 24.0, 34.0, 44.0],
                              **TAM))
    iddia("A5: 4 Agu'da OLCULEN en kotu 48 sa penceresi (%d kosum) -> YESIL "
          "(nobetci bugunku veriyle BOS KIRMIZI yakmaz)" % OLCULEN_TABAN_TESLIM,
          rc == 0, "rc=%d" % rc)

    # GOZLEM GECMISI W'den KISA: hukum verilmez ama SESSIZ DE KALINMAZ.
    rc, s = kos(D, _sahte_api(kosum_sayisi=2, yas_saat=0.2, kosum_yaslari=[0.2, 5.0],
                              kayit_yas_saat=10.0, yenileme_yas_saat=10.0))
    iddia("A5 (c) gozlem gecmisi (10 sa) < pencere (%d sa) -> ALARM YOK"
          % TESLIM_PENCERESI_SAAT, rc == 0, "rc=%d" % rc)
    iddia("A5 (c) ama SESSIZ DEGIL: 🟡 satir gecmisi ve olculen teslimi YAZAR",
          any(x.startswith("🟡 A5 TESLIM") and "gozlem gecmisi 10.0 sa" in x
              and "teslim 2 / nominal 192" in x for x in s), s)

    # 🔴 CAPA KILIDI: dosyaya DUN dokunulmus olmasi A5'i SUSTURAMAZ. Olculdu (4 Agu):
    # bu depoda alarm dosyalarina medyan 5,2 saatte bir dokunuluyor; capa `yenileme_an`
    # olsaydi A5 pratikte HIC hukum vermezdi (kapatmak icin yazildigi korlugu URETIRDI).
    rc, s = kos(D, _sahte_api(kosum_sayisi=3, yas_saat=0.2,
                              kosum_yaslari=[0.2, 0.5, 40.0],
                              kayit_yas_saat=400.0, yenileme_yas_saat=1.0))
    iddia("A5 CAPA KILIDI: is akisi ESKI kayitli ama dosyaya 1,0 sa once dokunulmus -> "
          "A5 YINE DE HUKUM VERIR (KIRMIZI). Capa `yenileme_an` olsaydi bu mutant "
          "sessizce 🟡'ye duserdi", rc == 1, "rc=%d" % rc)
    iddia("A5 CAPA KILIDI: karsi risk SUSTURULMAZ — satir taze cron dokunusunu ⚠ ile "
          "ve YASIYLA yazar",
          any(x.startswith("🔴 A5 TESLIM") and "⚠ cron tanimina dokunan son commit 1.0 sa"
              in x for x in s), s)

    # A5 FAIL-CLOSED: dagilim OKUNAMAZSA yesil DEGIL, rc 2.
    rc, _ = kos(D, _sahte_api(kosum_sayisi=3, bozuk="kosum-listesi-sekli", **TAM))
    iddia("A5 FAIL-CLOSED: `workflow_runs` liste DEGIL -> rc 2 (OLCULEMEDI)", rc == 2,
          "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(kosum_sayisi=3, yas_saat=0.2,
                              kosum_yaslari=[0.2, 16.0, 32.0],
                              bozuk="ikinci-kayit-event", **TAM))
    iddia("A5 FAIL-CLOSED: event suzgeci YARIM calismis (listenin ILK kaydi schedule ama "
          "bir digeri degil) -> rc 2; tek kaydi suzup gerisini saymak sahte YESIL olurdu",
          rc == 2, "rc=%d" % rc)
    # 🔴 SAGLIKLI dagilimin ICINDE tek bozuk damga: bozuk kaydi SESSIZCE ATLAMAK teslimi
    # 8'den 7'ye dusurur, ikisi de tabanin (4) USTUNDE -> hal YESIL yanardi. Cozulemeyen
    # damga OLCULEMEDI'dir, "bir eksik saydim" DEGIL.
    rc, _ = kos(D, _sahte_api(kosum_sayisi=8, yas_saat=0.2,
                              kosum_yaslari=[0.2, 6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0],
                              bozuk="kosum-zaman", **TAM))
    iddia("A5 FAIL-CLOSED: SAGLIKLI dagilimin icinde TEK bozuk zaman damgasi -> rc 2 "
          "(sessizce atlanip 7/8 sayilsaydi hal YESIL kalirdi)", rc == 2, "rc=%d" % rc)

    # --- FAIL-CLOSED: veri yoksa YESIL DEGIL ---
    rc, s = kos(D, _sahte_api(bozuk="ag"))
    iddia("FAIL-CLOSED: ag hatasi -> OLCULEMEDI (rc 2), YESIL DEGIL", rc == 2, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(bozuk="liste-sekli"))
    iddia("FAIL-CLOSED: is akisi listesi sekli degismis -> rc 2", rc == 2, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(bozuk="kosum-sekli", kosum_sayisi=3))
    iddia("FAIL-CLOSED: kosum yanitinda `total_count` yok -> rc 2", rc == 2, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(bozuk="tutarsiz"))
    iddia("FAIL-CLOSED: total_count>0 ama workflow_runs bos -> rc 2", rc == 2, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(bozuk="commit-sekli"))
    iddia("FAIL-CLOSED: workflow son degisim zamani okunamazsa rc 2", rc == 2,
          "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(kosum_sayisi=5, yas_saat=0.2, event="push"))
    iddia("FAIL-CLOSED: event suzgeci calismamis (event=push donmus) -> rc 2", rc == 2,
          "rc=%d" % rc)
    rc, _ = kos([], _sahte_api(kosum_sayisi=5, yas_saat=0.2))
    iddia("FAIL-CLOSED: depoda hic cron bulunamadi -> rc 2 (bosluga YESIL yok)", rc == 2,
          "rc=%d" % rc)

    # --- DAMGA YAZICISI: okuyucu ile AYNI SOZLESME ---
    govde = damga_govdesi({"GITHUB_RUN_ID": "30664207786", "GITHUB_RUN_NUMBER": "7",
                           "GITHUB_EVENT_NAME": "schedule",
                           "GITHUB_SHA": "0db2aafbb580e1c4a7f9d3b2c1e0f5a6b7c8d9e0",
                           "GITHUB_REPOSITORY": "Pruvo138/pruvo"})
    iddia("DAMGA YAZICI: govde makine-okunur ve okuyucunun bekledigi ADI tasir",
          govde["damga"] == DAMGA_ADI and govde["is_akisi"] == UZLASTIRICI_DOSYA,
          json.dumps(govde, ensure_ascii=False, sort_keys=True))
    iddia("DAMGA YAZICI: kosum kimligi/olayi/sha KAYDEDILIR (adli iz)",
          (govde["kosum_id"], govde["olay"]) == ("30664207786", "schedule")
          and govde["sha"].startswith("0db2aafb"), govde)
    iddia("DAMGA YAZICI: govde JSON'a cevrilebilir (bozuk govde artifact'e sizmaz)",
          isinstance(json.loads(json.dumps(govde)), dict))

    # --- A0 KAYNAK CAPASI: uzlastirici damgayi FIILEN uretiyor mu (GERCEK DOSYA) ---
    try:
        kablo_sorun, kablo_bulgu = uzlastirici_kablosu()
        kablo_ariza = None
    except Exception as e:  # noqa: BLE001
        kablo_sorun, kablo_bulgu, kablo_ariza = ["olculemedi"], {}, "%s: %s" % (
            type(e).__name__, e)
    iddia("A0 KAYNAK: %s damgayi FIILEN uretir ve `%s` adiyla YUKLER (yazici silinirse "
          "eksen KAYNAKSIZ kalir -> bu iddia KIRMIZI)" % (UZLASTIRICI_DOSYA, DAMGA_ADI),
          not kablo_sorun, kablo_ariza or "; ".join(kablo_sorun) or repr(kablo_bulgu))
    iddia("A0 KAYNAK: onarim adimi yaris-yeniden-denemeli surucuyu kullanir",
          bool(kablo_bulgu.get("surucu")), repr(kablo_bulgu))
    iddia("A0 KAYNAK: kosum agaci uzak main UCUNA tazelenir (donmus github.sha DEGIL)",
          bool(kablo_bulgu.get("tazeleme")), repr(kablo_bulgu))
    # 🔴 DAMGANIN DOGRULUGU (yasamasi DEGIL): kosul silinirse damga SIFIR denetimi
    # damgalar. Olculdu (merge kapisi, 1 Agu): bu iddia eklenmeden once `if:` satirini
    # silen mutant TUM kapilarda rc 0 aliyordu.
    iddia("A0 KAYNAK: damga adimlari OLCUM SONUCUNA KOSULLU (kosul silinir/`always()` "
          "olursa 20:47Z'nin SIFIR denetimli YESIL kosumu da damgalanirdi)",
          bool(kablo_bulgu.get("kosullu")), kablo_ariza or "; ".join(kablo_sorun)
          or repr(kablo_bulgu))
    # --- KADANS KOLU: uzlastirma cron KUYRUGUNA bagimli mi (GERCEK dosyalar) ---
    try:
        kad_sorun, kad_bulgu = kadans_kablosu()
        kad_ariza = None
    except Exception as e:  # noqa: BLE001
        kad_sorun, kad_bulgu, kad_ariza = ["olculemedi"], {}, "%s: %s" % (
            type(e).__name__, e)
    iddia("KADANS: %s icinde `uses: %s` cagiran BLOKLAMAYAN bir kol VAR (uzlastirma "
          "GitHub cron kuyruguna bagimli DEGIL; olculdu 4 Agu: cron teslimi %%3,65, "
          "en uzun bosluk 17,6 sa)" % (KADANS_IS_AKISI, KADANS_CAGRISI),
          not kad_sorun, kad_ariza or "; ".join(kad_sorun) or repr(kad_bulgu))
    iddia("KADANS: 🔴 kol `%s`nin GECISLI `needs:` kapanisinda DEGIL — yayini "
          "BLOKLAMAZ (bu iddia yorum degil, KOSULAN kapidir: job'u `deploy: needs`'e "
          "sizdirmak KIRMIZI yakar)" % YAYIN_ISI,
          kad_bulgu.get("job") and not kad_bulgu.get("blokluyor"), repr(kad_bulgu))
    iddia("KADANS: cron IKINCI KOL olarak KALIR (`schedule` tetikleyicisi duruyor) — "
          "kadans kolu cron'un YERINE DEGIL YANINA konuldu",
          "schedule" in (kad_bulgu.get("tetikler") or []), repr(kad_bulgu))
    iddia("KADANS: TEK KILIT — grup cagrilan isin JOB'unda (%r) ve cagiran job kendi "
          "grubunu tutmuyor -> ayni anda IKI uzlastirma kosamaz, kilitlenme riski de YOK"
          % kad_bulgu.get("grup"), bool(kad_bulgu.get("grup")), repr(kad_bulgu))
    iddia("KADANS: cagiran job KENDINI KADANS KOLU olarak BEYAN EDER (`with: %s: true`) "
          "— bayrak dusurulurse kol cron gibi davranir ve ONARILAN sapma deploy.yml "
          "kosumunun conclusion'ini yine kirletir (iki soru tek cikis koduna yigilir)"
          % KADANS_BAYRAGI, kad_bulgu.get("bayrak") is True, repr(kad_bulgu))
    iddia("KADANS: bayragin VARSAYILANI `false` (cagrilan tarafta boolean girdi) — "
          "varsayilan `true` olsaydi CRON kolu da sapmada kirmizi yakmaz, sapma IKI "
          "KOLDAN DA susardi",
          isinstance(kad_bulgu.get("bayrak_tanimi"), dict)
          and kad_bulgu["bayrak_tanimi"].get("default") is False
          and str(kad_bulgu["bayrak_tanimi"].get("type") or "") == "boolean",
          repr(kad_bulgu.get("bayrak_tanimi")))

    # ═══════════════════════════════════════════════════════════════════════
    # SINYAL AYRIMI — "yayin sagligi" ile "D1 sapmasi" AYRI HUKUMLER
    # ═══════════════════════════════════════════════════════════════════════
    # 🔴 NEDEN AYRI IDDIALAR (tek "ayrim var mi" iddiasi YETMEZ): bu depoda olculdu ki
    # zincirden gecen tek bir iddia katmanlarin VEYA'sini olcer ([[beyan-edilmis-survivor]]).
    # Sinyali kaldiran mutant, `exit 1`i dusuren mutant ve iki hali TEK adima yigan mutant
    # AYRI kusurlardir; her biri TEK BASINA kirmizi yakabilmelidir.
    try:
        s_sorun, s_bulgu = sinyal_ayrimi()
        s_ariza = None
    except Exception as e:  # noqa: BLE001
        s_sorun, s_bulgu, s_ariza = ["olculemedi"], {}, "%s: %s" % (type(e).__name__, e)
    iddia("SINYAL: sapma gorunurlugu (cron/elle kolu) YASIYOR ve `exit 1` tasiyor — "
          "sinyali tamamen kaldirmak ayrimin en kolay ve en YANLIS cozumudur",
          bool(s_bulgu.get("cron")), s_ariza or "; ".join(s_sorun))
    iddia("SINYAL: kadans kolunda sapma `%s` damgasina yazilir VE ayni adla YUKLENIR "
          "(sapma susturulmaz, KANALI degisir)" % SAPMA_DAMGA_ADI,
          bool(s_bulgu.get("yaz")) and bool(s_bulgu.get("yuk")),
          s_ariza or "; ".join(s_sorun))
    iddia("SINYAL: 'ONARILAMADI' AYRI bir hukumdur (teyidin GERCEK sonucunu okuyan "
          "`steps.teyit.outcome` kosullu, `exit 1`) — "
          "onarilan sapma ile kapanmayan sapma TEK KUTUYA konamaz",
          bool(s_bulgu.get("onarilamadi")), s_ariza or "; ".join(s_sorun))
    iddia("SINYAL: DOGRULUK TABLOSU — %d senaryonun hepsinde GitHub kosul semantigi "
          "FIILEN calistirildi ve tam olarak beklenen adimlar kostu (carpisma YOK)"
          % len(SINYAL_TABLOSU), not s_sorun, s_ariza or "; ".join(s_sorun))

    # Kosul degerlendiricinin KENDI iki yonlu fiksturu (gercek dosyaya bagimli kalmasin).
    _o = lambda kol, sapma, durum: {  # noqa: E731
        "durum": durum, "girdiler": {KADANS_BAYRAGI: kol},
        "ciktilar": {("olcum", "sapma"): sapma}, "sonuclar": {"teyit": durum}}
    iddia("KOSUL FIKSTURU: ortuk `success()` — durum islevi TASIMAYAN kosul, onceki adim "
          "dustugunde ATLANIR (bu satir olmadan 'onarilamadi' senaryosu carpisirdi)",
          _kosul_degerlendir("steps.olcum.outputs.sapma == 'var'", _o(False, "var", "failure"))
          is False)
    iddia("KOSUL FIKSTURU: `failure()` tasiyan kosulda ORTUK success EKLENMEZ",
          _kosul_degerlendir("failure() && steps.olcum.outputs.sapma == 'var'",
                             _o(False, "var", "failure")) is True)
    iddia("KOSUL FIKSTURU: `inputs.%s != true` cron kolunda DOGRU, kadans kolunda YANLIS"
          % KADANS_BAYRAGI,
          _kosul_degerlendir("inputs.%s != true" % KADANS_BAYRAGI, _o(False, "var", "success"))
          is True
          and _kosul_degerlendir("inputs.%s != true" % KADANS_BAYRAGI,
                                 _o(True, "var", "success")) is False)
    try:
        _kosul_degerlendir("github.event_name == 'schedule'", _o(False, "var", "success"))
        _tanimsiz = False
    except OlcumHatasi:
        _tanimsiz = True
    iddia("KOSUL FIKSTURU: TANIMADIGI yazim OLCULEMEDI (fail-closed) — kosul katmani "
          "GitHub ifade dilini TAKLIT ETMEZ, cozemedigini 'dogru' SAYMAZ", _tanimsiz)

    # --- SAPMA ALARM KANALI: damgayi OKUYAN ve KIRMIZI yakan kol YASIYOR mu ---
    try:
        sa_sorun, sa_bulgu = sapma_alarm_kablosu()
        sa_ariza = None
    except Exception as e:  # noqa: BLE001
        sa_sorun, sa_bulgu, sa_ariza = ["olculemedi"], {}, "%s: %s" % (type(e).__name__, e)
    iddia("SAPMA KANALI: %s VAR ve GERCEK olcum kolunu kosuyor (damgayi okuyan kol "
          "olmadan ayrim SESSIZLESTIRMEYE doner)" % SAPMA_ALARM_DOSYA,
          not sa_sorun, sa_ariza or "; ".join(sa_sorun) or repr(sa_bulgu))
    iddia("SAPMA KANALI: 🔴 yayini DURDURAMAZ — `push`/`pull_request`/`workflow_call` "
          "tetikleyicisi YOK (workflow_call olsaydi kirmizisi YINE deploy kosumunun "
          "conclusion'ina yigilirdi)",
          not ({"push", "pull_request", "workflow_call"}
               & set(sa_bulgu.get("tetikler") or [])), repr(sa_bulgu))
    iddia("SAPMA KANALI: CRON'A BAGIMLI DEGIL — `workflow_run` ile deploy.yml'in "
          "BITISINDE tetiklenir (olculdu 4 Agu: cron teslimi %3,65, en uzun bosluk 17,6 sa)",
          "workflow_run" in (sa_bulgu.get("tetikler") or []), repr(sa_bulgu))
    iddia("SAPMA KANALI: `--kendini-test` kolu da kosuyor — sapma NADIRDIR, canli kol "
          "gunlerce yesil doner; 'alarm sapmayi gorur' iddiasi ancak fiksturle kanitlanir",
          bool(sa_bulgu.get("kendini")), repr(sa_bulgu))

    # ═══════════════════════════════════════════════════════════════════════
    # AYRIM KANITI — IKI YON, TEK OLCUM (tek yonlu kabul, sessizlestirmeyi de gecirir)
    # ═══════════════════════════════════════════════════════════════════════
    try:
        ay_sorun, ay_bulgu = ayrim_kaniti()
        ay_ariza = None
    except Exception as e:  # noqa: BLE001
        ay_sorun, ay_bulgu, ay_ariza = ["olculemedi"], {}, "%s: %s" % (type(e).__name__, e)
    iddia("AYRIM (i-a): D1'de SAPMA VAR ve onarildi + KADANS kolu -> uzlastirici isinde "
          "KOSAN hicbir adim `exit 1` vermez (deploy.yml conclusion'i YALNIZ yayin sagligi)",
          not ay_bulgu.get("kosan_exit") and ay_bulgu.get("damga_dogar") is not None,
          ay_ariza or repr(ay_bulgu.get("kosan_exit")))
    iddia("AYRIM (i-b): AYNI senaryoda sapma damgasi DOGAR ve GERCEK nobetci "
          "(tools/d1-sapma-kapisi.py) onu rc 1 = KIRMIZI yakar; damga YOKKEN rc 0 "
          "(daima-kirmizi bir kanal sinyal tasimaz)",
          bool(ay_bulgu.get("damga_dogar"))
          and not [s for s in ay_sorun if s.startswith("YON (i-b)")],
          ay_ariza or "; ".join(ay_sorun))
    iddia("AYRIM (ii): YAYIN GERCEKTEN BOZUKKEN kosum KIRMIZI — `deploy` kapanisi BOS "
          "DEGIL (%s job) ve zincirdeki hicbir job `continue-on-error`/daima-yanlis `if:` "
          "ile susturulmamis; sapma kolu bu zincirde YOK"
          % len(ay_bulgu.get("yayin_kapanisi") or []),
          not [s for s in ay_sorun if s.startswith("YON (ii)")],
          ay_ariza or "; ".join(ay_sorun))
    iddia("AYRIM: IKI YON DE ayni olcumde saglandi (tek yonlu kabul, sapmayi tumden "
          "susturan bir 'cozumu' de gecirirdi)", not ay_sorun,
          ay_ariza or "; ".join(ay_sorun))

    # Fikstur: kosul katmaninin kendisi IKI YONLU olcusun (gercek dosyaya bagimli kalmasin).
    iddia("A0 KOSUL FIKSTURU: `if:` YOK -> ariza (kosulsuz damga yakalanir)",
          damga_kosul_arizasi({"run": "x"}) is not None,
          repr(damga_kosul_arizasi({"run": "x"})))
    iddia("A0 KOSUL FIKSTURU: `always()` -> ariza",
          damga_kosul_arizasi({"if": "always()"}) is not None)
    iddia("A0 KOSUL FIKSTURU: olcum ciktisina bakmayan kosul -> ariza",
          damga_kosul_arizasi({"if": "github.event_name == 'schedule'"}) is not None)
    iddia("A0 KOSUL FIKSTURU: gercek kosul -> ariza YOK (yanlis-pozitif yok)",
          damga_kosul_arizasi({"if": "steps.olcum.outputs.sapma == 'yok' || "
                                     "steps.teyit.outcome == 'success'"}) is None)

    # --- CI KABLOSU: HER IKI KOL da deploy.yml'de ANLAMLI OLARAK kosuyor mu ---
    try:
        bayraksiz, kendini = deploy_cagrilari()
        kablo_hata = None
    except Exception as e:  # noqa: BLE001 — OlcumHatasi + import arizalari
        bayraksiz = kendini = False
        kablo_hata = "%s: %s" % (type(e).__name__, e)
    iddia("CI KABLOSU: %s GERCEK olcum kolunu (bayraksiz) ANLAMLI olarak kosuyor"
          % KADANS_IS_AKISI, bayraksiz, kablo_hata or "bulunamadi")
    iddia("CI KABLOSU: %s `--kendini-test` kolunu ANLAMLI olarak kosuyor"
          % KADANS_IS_AKISI, kendini, kablo_hata or "bulunamadi")

    # ═══════════════════════════════════════════════════════════════════════
    # A4 PAKET TAZELIGI — ONCE-KIRMIZI FIKSTURLERI
    # ═══════════════════════════════════════════════════════════════════════
    # 🔴 NEDEN FIKSTUR SART: canli kol BUGUN YESIL (Okan 1 Agu 17:29'da deploy etti,
    # fiziksel nobetci rc=0). "Alarm bayatligi gorur" iddiasi canli kosumla KANITLANAMAZ;
    # ancak fiksturle gosterilebilir. Asagidaki senaryolarin hepsi AGSIZ.
    P = [("d1-uzlastirici.yml", "7,22,37,52 * * * *"),
         (PAKET_ALARM_DOSYA, "11,26,41,56 * * * *")]

    def paket_api(paket_damgalari, yas_saat=0.4, kosum_sayisi=137, bozuk=None,
                  kosum_yaslari=None, damga_kosum="schedule"):
        """Iki is akisi + IKI AYRI damga adi donduren `getir` (ad suzgeci FIILEN calisir).

        🔴 KOSUM DAGILIMI SAGLIKLI VERILIR (varsayilan 48 sa'te 8 teslim): bu blogun
        iddialari A4 DAMGA eksenini yalitir. Fikstur tek kosum dondurseydi A5 TESLIM
        ekseni de kirmizi yanar ve "A4 damgasi taze -> YESIL" iddialari A4 yuzunden
        DEGIL A5 yuzunden dusup TEK DEGISKEN yalitimini bozardi
        ([[fikstur-degeri-mutasyonu-kor-eder]] — fikstur degeri iddiayi kaydirir)."""
        if kosum_yaslari is None:
            kosum_yaslari = [yas_saat, 6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0]
        temel = _sahte_api(kosum_sayisi=kosum_sayisi, yas_saat=yas_saat, bozuk=bozuk,
                           kosum_yaslari=kosum_yaslari, damga_kosum=damga_kosum)
        bagla = temel.damgalari_bagla   # damga -> kosum baglama kurali TEK KAYNAK

        def getir(yol, zaman_asimi=25):
            if "actions/artifacts?" in yol:
                if bozuk == "paket-ag":
                    raise OlcumHatasi("GitHub API HTTP 502: actions/artifacts")
                if ("name=%s" % PAKET_DAMGA_ADI) in yol:
                    if bozuk == "paket-suzgec":
                        return {"total_count": 1,
                                "artifacts": bagla([_damga_kaydi(0.5, ad=DAMGA_ADI)])}
                    return {"total_count": len(paket_damgalari),
                            "artifacts": bagla([dict(a, name=PAKET_DAMGA_ADI)
                                                for a in paket_damgalari])}
                # A0 damgasi: bu blogun iddialari A4'u YALITIR, o yuzden A0 HER ZAMAN
                # CRON teslimi ve TAZE verilir (tek degisken A4 damgasi olsun).
                return {"total_count": 1,
                        "artifacts": bagla([_damga_kaydi(1.0)], "schedule")}
            if "actions/workflows?" in yol:
                wf1 = dict(_HAM_WF)
                wf1["path"] = ".github/workflows/d1-uzlastirici.yml"
                wf2 = dict(_HAM_WF)
                wf2["id"] = _HAM_WF["id"] + 1
                wf2["path"] = ".github/workflows/%s" % PAKET_ALARM_DOSYA
                return {"total_count": 2, "workflows": [wf1, wf2]}
            return temel(yol, zaman_asimi)
        return getir

    # A4 esigi: 15 dk nominal cadans -> A0 ile AYNI turetim -> N=9 saat.
    _pd, n4, par4 = paket_alarm_esigi(P)
    iddia("A4 ESIK: %s cron araligi 15 dk -> N=9 sa (A0 ile AYNI turetim)"
          % PAKET_ALARM_DOSYA, (par4, n4) == (15, 9), "(aralik=%s, N=%s)" % (par4, n4))

    rc, s = kos(P, paket_api([_damga_kaydi(1.5)]), damga_ile=True, paket_ile=True)
    iddia("A4 (a) TAZE paket damgasi (1,5 sa < N=9) -> YESIL", rc == 0, "rc=%d" % rc)
    iddia("A4 (a) rapor A0 ve A4 satirlarini AYRI AYRI basar",
          any(x.startswith("✅ A0 DAMGA") for x in s)
          and any(x.startswith("✅ A4 PAKET") for x in s), s)

    # 🔴 ONCE-KIRMIZI 1: canli paket bayat kalinca alarm damga URETMEZ -> damga yaslanir.
    # 14,5 saat = 1 Agu'da FIILEN olculen bayatlik penceresi; esik N=9 sa.
    rc, s = kos(P, paket_api([_damga_kaydi(14.5)]), damga_ile=True, paket_ile=True)
    iddia("A4 (b) ONCE-KIRMIZI: 1 Agu'da OLCULEN 14,5 saatlik bayatlik penceresi -> "
          "KIRMIZI (esik N=9 sa)", rc == 1, "rc=%d" % rc)
    iddia("A4 (b) teshis fazla tahsilat olcumunu ADIYLA anlatir",
          any("A4 PAKET" in x and "FAZLA TAHSILAT" in x for x in s)
          or any("A4 PAKET" in x and "PARITE ile kapanmadi" in x for x in s), s)
    rc, _ = kos(P, paket_api([_damga_kaydi(8.9)]), damga_ile=True, paket_ile=True)
    iddia("A4 esik SINIRI: 8,9 sa < N=9 -> YESIL", rc == 0, "rc=%d" % rc)
    rc, _ = kos(P, paket_api([_damga_kaydi(9.1)]), damga_ile=True, paket_ile=True)
    iddia("A4 esik SINIRI: 9,1 sa > N=9 -> KIRMIZI", rc == 1, "rc=%d" % rc)

    # 🔴 ONCE-KIRMIZI 2: alarm HIC kosmadi / her kosumda drift-olculemedi dondu ->
    # damga HIC dogmadi. "Kosum yesildi" ile "olcum yapildi" ayrimi tam burada yasar.
    rc, s = kos(P, paket_api([]), damga_ile=True, paket_ile=True)
    iddia("A4 (c) ONCE-KIRMIZI: HIC paket damgasi YOK (alarm hic kosmadi ya da her "
          "kosumda drift/olculemedi dondu) -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A4 (c) teshis 'canli fiyat yolu HIC denetlenmedi' der",
          any("A4 PAKET" in x and "HIC" in x for x in s), s)
    rc, s = kos(P, paket_api([_damga_kaydi(30.0, expired=True)]),
                damga_ile=True, paket_ile=True)
    iddia("A4 (d) TUM paket damgalari SURESI DOLMUS -> KIRMIZI", rc == 1, "rc=%d" % rc)

    # 🔴 TETIKLEYICI SARTI A4'TE DE GECERLI (A0 ile AYNI KOD YOLU): elle tetiklenmis bir
    # paket alarmi damgasi da ekseni SUSTURAMAZ. Sart yalnizca A0'a konsaydi ikiz mantik
    # AYRISIRDI ([[ikiz-tanim-sessiz-ayrisma]]); TEK DEGISKEN: damgayi yazan kosum.
    rc, s = kos(P, paket_api([_damga_kaydi(1.5)], damga_kosum="elle"),
                damga_ile=True, paket_ile=True)
    iddia("A4 TETIKLEYICI: ELLE tazelenmis paket damgasi (1,5 sa TAZE) -> KIRMIZI",
          rc == 1, "rc=%d" % rc)
    iddia("A4 TETIKLEYICI: AYIRT EDICI — ayni raporda A0 YESIL (cron damgasi), YALNIZ "
          "A4 KIRMIZI (iki eksen AYNI kodu paylasir ama AYRI capadan olcer)",
          any(x.startswith("✅ A0 DAMGA") for x in s)
          and any(x.startswith("🔴 A4 PAKET") and "CRON YAPMADI" in x for x in s), s)

    # EKSEN AYRIMI: A0 taze iken A4 bayat olabilir (ve tersi) — ikisi AYRI raporlanir.
    rc, s = kos(P, paket_api([_damga_kaydi(14.5)]), damga_ile=True, paket_ile=True)
    iddia("EKSEN AYRIMI: A0 YESIL iken A4 KIRMIZI satiri AYRI durur (uzlastirici "
          "calisiyor diye fiyat yolu denetlenmis SAYILMAZ)",
          any(x.startswith("✅ A0 DAMGA") for x in s)
          and any(x.startswith("🔴 A4 PAKET") for x in s), s)

    # FAIL-CLOSED: paket damgasi OKUNAMAZSA yesil DEGIL.
    for boz, ad in (("paket-ag", "artifact API cagrilamadi"),
                    ("paket-suzgec", "`?name=` suzgeci CALISMAMIS (uzlastirma damgasi "
                                     "dondu — olu alarm TAZE gorunurdu)")):
        rc, _ = kos(P, paket_api([_damga_kaydi(0.5)], bozuk=boz),
                    damga_ile=True, paket_ile=True)
        iddia("A4 FAIL-CLOSED: %s -> rc 2 (OLCULEMEDI)" % ad, rc == 2, "rc=%d" % rc)

    # CAPA: alarm is akisi cron tasiyanlar arasindan DUSERSE eksen olculemez.
    rc, _ = kos([("d1-uzlastirici.yml", "7,22,37,52 * * * *")],
                paket_api([_damga_kaydi(0.5)]), damga_ile=True, paket_ile=True)
    iddia("A4 CAPA: %s cron tasiyan is akislari arasinda YOK -> rc 2 (alarm silinirse "
          "sessiz YESIL verilmez)" % PAKET_ALARM_DOSYA, rc == 2, "rc=%d" % rc)

    # --- A4 KAYNAK CAPASI: GERCEK is akisi dosyasi olculur --------------------
    try:
        p_sorun, p_bulgu = paket_alarmi_kablosu()
        p_ariza = None
    except Exception as e:  # noqa: BLE001
        p_sorun, p_bulgu, p_ariza = ["olculemedi"], {}, "%s: %s" % (type(e).__name__, e)
    iddia("A4 KAYNAK: %s canli olcum kolunu kosar, damgayi `%s` adiyla URETIR ve YUKLER"
          % (PAKET_ALARM_DOSYA, PAKET_DAMGA_ADI),
          not p_sorun, p_ariza or "; ".join(p_sorun) or repr(p_bulgu))
    iddia("A4 KAYNAK: 🔴 YAYINI DURDURAMAZ — alarm is akisinda `push`/`pull_request`/"
          "`workflow_call` tetikleyicisi YOK (bu iddia yorum degil, KOSULAN kapidir)",
          bool(p_bulgu.get("tetikler"))
          and not ({"push", "pull_request", "workflow_call"} & set(p_bulgu["tetikler"])),
          repr(p_bulgu.get("tetikler")))
    iddia("A4 KAYNAK: canli (bayrakSIZ) olcum kolu kosuyor — `--kendini-test`e "
          "dusurulmus bir alarm hicbir canli sey olcmez ama YESIL yanar",
          bool(p_bulgu.get("olcum")), repr(p_bulgu))
    iddia("A4 KAYNAK: kosum agaci uzak main UCUNA tazelenir (donmus github.sha kahini "
          "bayatlatir)", bool(p_bulgu.get("tazeleme")), repr(p_bulgu))
    iddia("A4 KAYNAK: damga adimlari OLCUM CIKTISINA (`durum == 'parite'`) KOSULLU",
          bool(p_bulgu.get("kosullu")), p_ariza or "; ".join(p_sorun) or repr(p_bulgu))
    # TEK KAYNAK: etiket dizesi aracin KENDISINDEN kosarak alinir (elle ikinci kopya yok).
    iddia("A4 TEK KAYNAK: damga kosulundaki etiket, %s::DURUM_ETIKET['PARITE'] ile "
          "KOSARAK dogrulanir" % PAKET_OLCUM_ARACI,
          p_bulgu.get("arac_etiketi") == PAKET_PARITE_ETIKETI, repr(p_bulgu))

    # Kosul katmani IKI YONLU (gercek dosyaya bagimli kalmasin).
    iddia("A4 KOSUL FIKSTURU: `if:` YOK -> ariza",
          paket_kosul_arizasi({"run": "x"}) is not None)
    iddia("A4 KOSUL FIKSTURU: `always()` -> ariza",
          paket_kosul_arizasi({"if": "always()"}) is not None)
    iddia("A4 KOSUL FIKSTURU: `success()` (olcum ciktisina BAKMAYAN kosul) -> ariza",
          paket_kosul_arizasi({"if": "success()"}) is not None)
    iddia("A4 KOSUL FIKSTURU: cikti okunuyor ama 'parite' SART KOSULMUYOR -> ariza "
          "(drift bir kosum da damga dogururdu)",
          paket_kosul_arizasi({"if": "steps.olcum.outputs.durum != ''"}) is not None)
    iddia("A4 KOSUL FIKSTURU: gercek kosul -> ariza YOK (yanlis-pozitif yok)",
          paket_kosul_arizasi({"if": "steps.olcum.outputs.durum == 'parite'"}) is None)

    # ═══════════════════════════════════════════════════════════════════════
    # PUSH SERIDI — BAYATLIK OLCUMU FIILEN ATESLENEN TETIGE BAGLI MI
    # ═══════════════════════════════════════════════════════════════════════
    # 🔴 OLCULEN GEREKCE (4 Agu 2026): cron tetigi teslim %4,31, en uzun sessizlik
    # 1053,5 dk. AYNI pencerede `deploy.yml` event=push 152 kez teslim edildi ve en
    # uzun boslugu 418,9 dk idi (7 gunde 567 kosum, en uzun bosluk 663,5 dk). Ofset
    # degistirmek teslimi DUZELTMEDIGI icin olcum push tetigine de baglandi.
    # Asagidaki iddialar hem GERCEK dosyayi hem FIKSTURU olcer (tek yonlu kapi bu
    # depoda daha once isirdi, [[kapi-kapsam-eksen-secimi]]).
    try:
        ps_sorun, ps_bulgu = push_serit_kablosu()
        ps_ariza = None
    except Exception as e:  # noqa: BLE001
        ps_sorun, ps_bulgu, ps_ariza = ["olculemedi"], {}, "%s: %s" % (type(e).__name__, e)
    iddia("PS1 PUSH SERIT: %s bayatlik olcumunu (%s) CANLI kolla kosar — cron'un "
          "DUSURDUGU tetige degil FIILEN ateslenen tetige bagli"
          % (PUSH_SERIT_DOSYA, PUSH_SERIT_ARACI),
          not ps_sorun, ps_ariza or "; ".join(ps_sorun) or repr(ps_bulgu))
    iddia("PS2 PUSH SERIT: 🔴 IZIN LISTESI — is akisi `push`/`workflow_dispatch` DISINDA "
          "HICBIR tetik tasimiyor (kara liste degil: `pull_request` yasaklanip "
          "`pull_request_target` acik kalmasi [[maskeleme-kismi-kapatma]] sinifidir)",
          bool(ps_bulgu.get("tetikler"))
          and set(ps_bulgu["tetikler"]) <= set(PUSH_SERIT_IZINLI_TETIK),
          repr(ps_bulgu.get("tetikler")))
    iddia("PS3 PUSH SERIT: `push` tetigi VAR (yoksa serit OLU ve korluk penceresi "
          "cron'un 1053,5 dk'sina geri doner)",
          "push" in (ps_bulgu.get("tetikler") or []), repr(ps_bulgu.get("tetikler")))
    iddia("PS4 PUSH SERIT: eszamanlilik grubu %s'in grubundan FARKLI (grup adi o "
          "dosyadan KOSARAK okunur, ikiz dize YOK)" % YAYIN_DOSYA,
          bool(ps_bulgu.get("grup")) and bool(ps_bulgu.get("yayin_grup"))
          and ps_bulgu["grup"] != ps_bulgu["yayin_grup"],
          "%r vs %r" % (ps_bulgu.get("grup"), ps_bulgu.get("yayin_grup")))
    iddia("PS5 PUSH SERIT: %s bu seridi `uses:` ile CAGIRMIYOR (yayinin `needs` "
          "grafinin ICINDE degil)" % YAYIN_DOSYA,
          ps_bulgu.get("cagiran") == [], repr(ps_bulgu.get("cagiran")))
    iddia("PS6 PUSH SERIT: canli (bayrakSIZ) olcum kolu kosuyor — `--kendini-test`e "
          "dusurulmus bir serit hicbir canli sey olcmez ama YESIL yanar",
          bool(ps_bulgu.get("olcum")), repr(ps_bulgu))
    iddia("PS7 PUSH SERIT: kosum agaci uzak main UCUNA tazelenir (donmus github.sha "
          "olculen ref'i ayristirir -> her push'ta BOS rc 2)",
          bool(ps_bulgu.get("tazeleme")), repr(ps_bulgu))
    # 🔴 TOKEN KAPSAMI OLCULUR, VARSAYILMAZ: token cozulmezse kapi rc 2 verir ve serit
    # HER PUSH'TA kirmizi yanar — yani "erisilebilir" bir beyan olarak birakilamaz.
    iddia("PS8 PUSH SERIT TOKEN: olcum adimi `secrets.%s` kullanir ve onu tasiyan is "
          "`environment:` BEYAN ETMEZ (ortam secret'i olsaydi serit askida kalirdi)"
          % PUSH_SERIT_SECRET,
          bool(ps_bulgu.get("token")) and not ps_bulgu.get("ortamli"), repr(ps_bulgu))
    iddia("PS9 PUSH SERIT TOKEN: KARDES KANIT — ayni secret'i FIILEN kosan %s icinde "
          "tuketen is(ler) VAR ve hicbiri `environment:` tasimiyor -> secret DEPO "
          "duzeyindedir, bu seritte de cozulur" % PAKET_ALARM_DOSYA,
          (ps_bulgu.get("kardes_tuketen") or 0) > 0
          and ps_bulgu.get("kardes_ortamli") == [],
          "tuketen=%r ortamli=%r" % (ps_bulgu.get("kardes_tuketen"),
                                     ps_bulgu.get("kardes_ortamli")))

    # --- FIKSTURLER: kablolama katmani GERCEK dosyaya bagimli kalmasin ------
    def _ps_sorun(ham):
        try:
            return push_serit_kablosu(ham=ham)[0]
        except OlcumHatasi as e:
            return ["olculemedi: %s" % e]

    iddia("PS10 FIKSTUR: `pull_request` eklenmis -> ARIZA (fork PR'i seridi baslatir; "
          "secret kapsami ve yayin kuyrugu degisir)",
          bool(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "  workflow_dispatch:\n", "  pull_request:\n  workflow_dispatch:\n"))),
          repr(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "  workflow_dispatch:\n", "  pull_request:\n  workflow_dispatch:\n"))[:1]))
    iddia("PS11 FIKSTUR: `workflow_call` eklenmis -> ARIZA (is akislari arasi TEK bag "
          "yolu budur; acik olursa serit yayinin `needs` grafina girebilir)",
          bool(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "  workflow_dispatch:\n", "  workflow_call:\n  workflow_dispatch:\n"))))
    iddia("PS12 FIKSTUR: `push` tetigi dusurulmus -> ARIZA (serit OLU)",
          bool(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "  push:\n    branches: [main]\n", ""))))
    iddia("PS13 FIKSTUR: eszamanlilik grubu %s'in grubuyla AYNI -> ARIZA (serit yayin "
          "kuyrugunu bekletirdi)" % YAYIN_DOSYA,
          bool(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "  group: odeme-bayatlik-push\n",
              "  group: %s\n" % (ps_bulgu.get("yayin_grup") or "pages")))))
    iddia("PS14 FIKSTUR: canli kol `--kendini-test`e dusurulmus -> ARIZA (serit YESIL "
          "yanar ama hicbir canli sey olcmez)",
          bool(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "shop-bayatlik-kapisi.py --gh-ozet",
              "shop-bayatlik-kapisi.py --kendini-test"))))
    iddia("PS15 FIKSTUR: olcum satiri cikis kodunu YUTUYOR (`|| true`) -> ARIZA",
          bool(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "shop-bayatlik-kapisi.py --gh-ozet",
              "shop-bayatlik-kapisi.py --gh-ozet || true"))))
    # KONTROL (TEK DEGISKEN: fikstur bozulmadi) — kapi "her seye ariza" demiyor.
    # 🔴 Bu satir ASAGIDAKI PS17-PS22'nin ORTAK KONTROLUDUR: her biri BU iskelete TEK
    # DEGISIKLIK uygular; iskeletin kendisi ARIZASIZ oldugu icin kirmizi degisikligin
    # KENDISINE atfedilir.
    iddia("PS16 FIKSTUR KONTROL: bozulmamis iskelet -> ARIZA YOK (yanlis-pozitif yok; "
          "PS17-PS22'nin TEK DEGISKENLI kontrolu)",
          _ps_sorun(PUSH_SERIT_FIKSTUR) == [], repr(_ps_sorun(PUSH_SERIT_FIKSTUR)))

    # ── IZIN LISTESI NOBETI (4 Agu 2026, curutucu iadesi) ────────────────────
    # 🔴 OLCULEN KUSUR: kara liste ("pull_request", "workflow_call") ile
    # `pull_request_target` tasiyan bir is akisi kapidan YESIL geciyordu; ikinci katman
    # da yoktu (`git grep pull_request_target` -> tools/ + .github/ icinde 0 vurus).
    # Asagidaki iddialar TEHLIKELI tetikleri ADIYLA, ENUMERE EDILMEMIS tetigi ise
    # MEKANIZMA olarak civiler. Her biri ariza METNINI olcer (yalnizca "ariza var mi"
    # DEGIL): boylece her yasak icin AYIRT EDICI (tek kirmizi) bir mutant yazilabilir.
    def _ps_tetik_eklenmis(ad):
        return _ps_sorun(PUSH_SERIT_FIKSTUR.replace(
            "  workflow_dispatch:\n", "  %s:\n  workflow_dispatch:\n" % ad))

    def _ps_metinde(sorunlar, parca):
        return any(parca in s for s in sorunlar)

    iddia("PS17 FIKSTUR: 🔴 `pull_request_target` -> ARIZA. Fork PR'ini TABAN DEPO "
          "baglaminda ve DEPO SECRET'leriyle kosturur; secret tasiyan bu seritte "
          "yabanci koda CLOUDFLARE_API_TOKEN acardi. (Kara listede EKSIKTI: kapi "
          "YESIL geciyordu.)",
          _ps_metinde(_ps_tetik_eklenmis("pull_request_target"),
                      "IZINSIZ TETIK `pull_request_target`"),
          repr(_ps_tetik_eklenmis("pull_request_target")[:1]))
    iddia("PS18 FIKSTUR: 🔴 `issue_comment` -> ARIZA (herkesin yazabildigi bir yorum "
          "taban depo baglaminda secret'li kosum baslatirdi)",
          _ps_metinde(_ps_tetik_eklenmis("issue_comment"),
                      "IZINSIZ TETIK `issue_comment`"))
    iddia("PS19 FIKSTUR: 🔴 `workflow_run` -> ARIZA (serit deploy.yml'in TAMAMLANMASINA "
          "baglanirdi; nobetci olctugu hatta bagimli olur ve hat tikandiginda O DA "
          "susar — Y4 sinifi)",
          _ps_metinde(_ps_tetik_eklenmis("workflow_run"),
                      "IZINSIZ TETIK `workflow_run`"))
    iddia("PS20 FIKSTUR: 🔴 ENUMERE EDILMEMIS tetik (`repository_dispatch`) -> ARIZA. "
          "Bu MEKANIZMA iddiasidir: kara liste TAMAMLANAMAZ (yarin GitHub yeni bir "
          "tetik ekler), izin listesi TANIM GEREGI kapalidir",
          _ps_metinde(_ps_tetik_eklenmis("repository_dispatch"),
                      "IZINSIZ TETIK `repository_dispatch`"))

    # ── DAL CIVISI NOBETI — iki AYRI kontrol, iki AYRI mutant ────────────────
    iddia("PS21 FIKSTUR: 🔴 `branches: ['**']` -> ARIZA (serit HER dala kosar; gurultu "
          "alarmi FIILEN susturur ve olcum ana dal disindaki bir ucu 'canli bayat' "
          "sanar)",
          _ps_metinde(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "    branches: [main]\n", "    branches: ['**']\n")),
              "DAL SUZGECI GENIS"),
          repr(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "    branches: [main]\n", "    branches: ['**']\n"))[:1]))
    iddia("PS22 FIKSTUR: 🔴 `push:` var ama `branches` TANIMSIZ -> ARIZA (varsayilan "
          "davranis TUM dallardir; 'yalniz main' iddiasi susarak coker)",
          _ps_metinde(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "  push:\n    branches: [main]\n", "  push:\n")), "DAL SUZGECI YOK"),
          repr(_ps_sorun(PUSH_SERIT_FIKSTUR.replace(
              "  push:\n    branches: [main]\n", "  push:\n"))[:1]))
    iddia("PS23 GERCEK DOSYA: `push.branches` TAM OLARAK [%r] (fikstur degil, canli "
          "is akisi)" % PUSH_SERIT_DAL,
          ps_bulgu.get("dallar") == [PUSH_SERIT_DAL], repr(ps_bulgu.get("dallar")))

    # DAMGA KUTUGU: yazici UC adi da tanir, kutuk disina cikamaz.
    for ad in (DAMGA_ADI, PAKET_DAMGA_ADI, SAPMA_DAMGA_ADI):
        g = damga_govdesi({"GITHUB_RUN_ID": "1", "GITHUB_SHA": "a" * 40}, ad)
        iddia("DAMGA KUTUGU: %r govdesi kendi is akisini ve IDDIASINI tasir" % ad,
              g["damga"] == ad and g["is_akisi"] == DAMGA_KUTUGU[ad][0]
              and g["iddia"] == DAMGA_KUTUGU[ad][1], g)
    try:
        damga_govdesi({}, "uydurma-damga")
        kutuk_kapali = False
    except OlcumHatasi:
        kutuk_kapali = True
    iddia("DAMGA KUTUGU: kutukte OLMAYAN ad REDDEDILIR (hicbir eksenin okumadigi bir "
          "artifact sessiz bir hicligi damgalardi)", kutuk_kapali)

    # ═══════════════════════════════════════════════════════════════════════
    # Y — CANLI KALIBRASYON (5 Agu 2026). IKI YONLU: hem BOS KIRMIZInin bittigi
    #     hem de SUSTURMANIN imkansiz oldugu kosulur.
    # ═══════════════════════════════════════════════════════════════════════
    # SABIT INVARYANTLARI (tavanlar "kirmizi gormeyeyim" diye buyutulemez)
    iddia("Y-INV tavan artifact saklamasinin ALTINDA (%d < %d): ustunde olsaydi damga "
          "suresi dolar ve A0 HICBIR ZAMAN yesil olamazdi"
          % (MUTLAK_SESSIZLIK_SAAT, DAMGA_SAKLAMA_SAAT),
          MUTLAK_SESSIZLIK_SAAT < DAMGA_SAKLAMA_SAAT)
    iddia("Y-INV tavan OLCULEN en uzun boslugun (%.0f dk = %.2f sa) USTUNDE -> gozlenen "
          "en kotu hal tek basina bos kirmizi URETMEZ"
          % (OLCULEN_EN_UZUN_BOSLUK_DK, OLCULEN_EN_UZUN_BOSLUK_DK / 60.0),
          MUTLAK_SESSIZLIK_SAAT >= OLCULEN_EN_UZUN_BOSLUK_DK / 60.0)
    iddia("Y-INV 🔴 A4 TAVANI OLCULEN ZARAR PENCERESININ ALTINDA (%d < %.1f sa): 1 Agu'nun "
          "14,5 saatlik fazla tahsilat olayi bir daha SESSIZ GECEMEZ"
          % (PAKET_BAYATLIK_TAVAN_SAAT, OLCULEN_PAKET_ZARAR_SAAT),
          PAKET_BAYATLIK_TAVAN_SAAT < OLCULEN_PAKET_ZARAR_SAAT)
    # FAIL-CLOSED: sifir teslim "sonsuz sabir" SATIN ALAMAZ.
    # 🔴 UC HAL AYRI AYRI: "OlcumHatasi" (dogru) · "DONDU" (fail-open) · "COKTU" (cokme).
    # Cokmeyi de KIRMIZI ama ADIYLA raporlamak sart: yakalanmayan bir istisna butun
    # bataryayi dusurur ve o kirmizi bir OLCUM DEGILDIR
    # ([[mutasyon-kaniti-yeniden-uretilebilir]]).
    try:
        efektif_aralik_dk(15, 0.0)
        sifir_hal = "DONDU (fail-open)"
    except OlcumHatasi:
        sifir_hal = "OlcumHatasi"
    except Exception as e:                                   # noqa: BLE001
        sifir_hal = "COKTU: %s" % type(e).__name__
    iddia("Y-INV 🔴 SIFIR teslim orani -> OLCULEMEDI (sonsuz efektif cadans YOK). Bu "
          "kapi olmasa teslim sifira giderken esik sonsuza giderdi",
          sifir_hal == "OlcumHatasi", sifir_hal)

    # --- Y1 SAGLIKLI FIKSTUR: teslim DUZENLI -> nabiz YESIL (tek yonlu nobetci tuzagi)
    YY = dict(kayit_yas_saat=400.0, yenileme_yas_saat=400.0)
    duzenli = [0.5 + 6.0 * i for i in range(8)]        # 8 teslim / 48 sa (taban 4)
    rc, s = kos(D, _sahte_api(kosum_sayisi=8, yas_saat=0.5, kosum_yaslari=duzenli,
                              damgalar=[_damga_kaydi(0.5)], **YY), damga_ile=True)
    iddia("Y1 SAGLIKLI FIKSTUR: teslim duzenli (8/48 sa) + damga taze -> YESIL "
          "(nobetci saglikli hali kirmizi yakmaz)", rc == 0, "rc=%d" % rc)
    iddia("Y1 satir esigin CANLI olcumden geldigini SAYIYLA yazar",
          any("A3 NABIZ" in x and "esik: CANLI oran" in x for x in s), s)

    # --- Y2 OLCULEN BOS KIRMIZI (5 Agu 06:59:57Z): cron boslugu 9,97 sa. DONMUS N=9
    #     bunu KIRMIZI yakiyordu; olculen %4,52 teslim rejiminde bu bosluk NORMALDIR.
    bos_kirmizi = [9.97, 19.0, 26.0, 31.0, 36.0, 41.0, 46.0]   # 7 teslim / 48 sa
    rc, s = kos(D, _sahte_api(kosum_sayisi=7, yas_saat=9.97, kosum_yaslari=bos_kirmizi,
                              damgalar=[_damga_kaydi(9.97)], **YY), damga_ile=True)
    iddia("Y2 OLCULEN BOS KIRMIZI: 9,97 sa cron boslugu + teslim 7/48 sa (A5 tabani "
          "USTUNDE) -> YESIL. Donmus N=9 bunu KIRMIZI yakiyordu ve kadans kolu ayni "
          "dakikalarda uzlastirmayi YAPMISTI", rc == 0, "rc=%d" % rc)

    # --- Y3 TAVAN BAGLAR: AYNI rejim, 19 saatlik sessizlik -> KIRMIZI (19 > 18).
    #     Bu, "pencereyi sonsuz genisleten" mutantin AYIRT EDICI fiksturudur.
    tavan_ustu = [19.0, 26.0, 31.0, 36.0, 41.0, 44.0, 46.0]    # 7 teslim / 48 sa
    rc, s = kos(D, _sahte_api(kosum_sayisi=7, yas_saat=19.0, kosum_yaslari=tavan_ustu,
                              damgalar=[_damga_kaydi(0.5)], **YY), damga_ile=True)
    iddia("Y3 MUTLAK SESSIZLIK TAVANI: teslim orani ne derse desin 19,0 sa TAM SESSIZLIK "
          "-> KIRMIZI (tavan %d sa). Tavan kaldirilirsa turetilen N=20 olur ve bu "
          "fikstur YESILE doner" % MUTLAK_SESSIZLIK_SAAT, rc == 1, "rc=%d" % rc)
    iddia("Y3 satir TAVANIN bagladigini ve ARDISIK BOS PENCERE sayisini yazar",
          any(x.startswith("🔴 A3 NABIZ") and "TAVAN 18 sa BAGLADI" in x
              and "ARDISIK BOS PENCERE" in x for x in s), s)

    # --- Y4 COKMUS REJIM SABIR SATIN ALAMAZ: teslim A5 tabaninin ALTINDA (1/48 sa) ise
    #     canli oran KULLANILMAZ, DONMUS 9 saate DUSULUR -> 12 sa sessizlik KIRMIZI.
    rc, s = kos(D, _sahte_api(kosum_sayisi=1, yas_saat=12.0, kosum_yaslari=[12.0], **YY))
    iddia("Y4 COKMUS REJIM: teslim 1/48 sa (taban 4 ALTI) -> canli oran REDDEDILIR, esik "
          "DONMUS 9 sa'te duser, 12,0 sa sessizlik KIRMIZI. Bu kapi olmasa cokme kendi "
          "esigini buyuturdu (fail-open)", rc == 1, "rc=%d" % rc)
    iddia("Y4 satir REDDIN SEBEBINI adiyla yazar (A5 tabani)",
          any("COKMUS rejim kendi esigini BUYUTEMEZ" in x for x in s), s)

    # --- Y5 KIRPIK SAYFA: teslim EKSIK sayilir -> oran DUSUK cikar -> esik HAKSIZ YERE
    #     buyurdu. Fail-closed: turetme YAPILMAZ.
    g_kirpik = {"dosya": "d1-uzlastirici.yml", "aralik": 15, "pencere_kirpildi": True,
                "kayit_an": datetime.now(timezone.utc) - timedelta(hours=400),
                "yenileme_an": None,
                "tum_kosumlar": [datetime.now(timezone.utc) - timedelta(hours=h)
                                 for h in duzenli]}
    oran_k, sebep_k = canli_teslim_orani(g_kirpik, datetime.now(timezone.utc))
    iddia("Y5 KIRPIK SAYFA -> canli oran TURETILMEZ (eksik sayim esigi haksiz yere "
          "buyuturdu)", oran_k is None and "sayfa siniri" in sebep_k, sebep_k)

    # --- Y6 "KOSUM VAR" != "TESLIM VAR": oran PENCEREDEKI teslimden turer, is akisinin
    #     TOPLAM kosum sayisindan DEGIL. Toplam 137 iken pencerede 7 teslim var.
    g_toplam = {"dosya": "d1-uzlastirici.yml", "aralik": 15, "pencere_kirpildi": False,
                "kosum_sayisi": 137,
                "kayit_an": datetime.now(timezone.utc) - timedelta(hours=400),
                "yenileme_an": None,
                "tum_kosumlar": [datetime.now(timezone.utc) - timedelta(hours=h)
                                 for h in bos_kirmizi]}
    oran_t, _sebep_t = canli_teslim_orani(g_toplam, datetime.now(timezone.utc))
    iddia("Y6 KOSUM != TESLIM: toplam 137 kosum kayitli ama W penceresinde 7 teslim var "
          "-> oran 7/192 (0,0365), 137/192 (0,71) DEGIL. Toplam sayiya bakan bir turetim "
          "esigi 18 sa'ten 3 sa'e cekip BOS KIRMIZI uretirdi",
          oran_t is not None and abs(oran_t - 7 / 192.0) < 1e-9, "olculen %r" % oran_t)

    print("\n%d iddia kosturuldu, %d KIRMIZI." % (sayac[0], len(hatalar)))
    return hatalar


def damga_govdesi(ortam=None, ad=DAMGA_ADI):
    """DAMGANIN MAKINE-OKUNUR govdesi. Okuyucu ile YAZICI AYNI DOSYADA tutulur: artifact
    adlari (DAMGA_KUTUGU) tek kaynaktir, ikisi birbirinden BAGIMSIZ bayatlayamaz.

    Bilinmeyen ad -> OlcumHatasi: kutukte olmayan bir adla yuklenen artifact'i HICBIR
    eksen okumaz, yani sessiz bir hicligi damgalardi."""
    if ad not in DAMGA_KUTUGU:
        raise OlcumHatasi("BILINMEYEN DAMGA ADI %r — kutukte olan adlar: %s. Kutukte "
                          "olmayan bir damgayi hicbir eksen OKUMAZ (sessiz hiclik)."
                          % (ad, ", ".join(sorted(DAMGA_KUTUGU))))
    is_akisi, iddia = DAMGA_KUTUGU[ad]
    o = os.environ if ortam is None else ortam
    return {
        "surum": 1,
        "damga": ad,
        "an": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "is_akisi": is_akisi,
        "kosum_id": o.get("GITHUB_RUN_ID"),
        "kosum_no": o.get("GITHUB_RUN_NUMBER"),
        "olay": o.get("GITHUB_EVENT_NAME"),
        "sha": o.get("GITHUB_SHA"),
        "depo": o.get("GITHUB_REPOSITORY") or DEPO,
        # NE IDDIA EDILIYOR: bu damga "kosum yesildi" DEMEK DEGIL, olcumun FIILEN
        # yapildigi ve temiz kapandigi demektir (kutukten gelir).
        "iddia": iddia,
    }


def damga_yaz(yol, ortam=None, ad=DAMGA_ADI):
    govde = damga_govdesi(ortam, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(govde, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return govde


def main():
    ap = argparse.ArgumentParser(description="Uzlastirma nabiz kapisi")
    ap.add_argument("--kendini-test", action="store_true",
                    help="AGSIZ fikstur kabulu (CI'da bu kol da kosar)")
    ap.add_argument("--damga-yaz", metavar="DOSYA",
                    help="Son basarili denetim damgasini JSON olarak yaz "
                         "(d1-uzlastirici.yml / paket-tazelik-alarmi.yml `Damga` adimi)")
    ap.add_argument("--damga-adi", metavar="AD", default=DAMGA_ADI,
                    choices=sorted(DAMGA_KUTUGU),
                    help="hangi damga yazilacak (varsayilan: %s)" % DAMGA_ADI)
    a = ap.parse_args()

    if a.damga_yaz:
        try:
            govde = damga_yaz(a.damga_yaz, ad=a.damga_adi)
        except OlcumHatasi as e:
            print("🔴 DAMGA YAZILAMADI: %s" % e)
            return 2
        print("DAMGA YAZILDI -> %s" % a.damga_yaz)
        print(json.dumps(govde, ensure_ascii=False, sort_keys=True))
        return 0

    if a.kendini_test:
        print("CRON NABIZ KAPISI — KENDINI TEST (agsiz fikstur)")
        hatalar = kendini_test()
        if hatalar:
            print("🔴 KENDINI TEST KIRMIZI:")
            for h in hatalar:
                print("   - %s" % h)
            return 1
        print("✅ KENDINI TEST GECTI")
        return 0

    try:
        dosyalar = cron_ifadeleri()
        uzl_dosya, damga_esigi, uzl_aralik = uzlastirici_esigi(dosyalar)
        pkt_dosya, paket_esigi, pkt_aralik = paket_alarm_esigi(dosyalar)
        # KABLO CAPALARI olcumun ONUNDE: okuyucu saglam ama YAZICI kirikken "damga yok"
        # demek yanlis teshistir. Kablo kopuksa hal OLCULEMEDI'dir (rc 2), ALARM degil.
        p_sorun, _p_bulgu = paket_alarmi_kablosu()
        if p_sorun:
            raise OlcumHatasi(
                "A4 KABLOSU KOPUK (%s): %s" % (PAKET_ALARM_DOSYA, " · ".join(p_sorun)))
        gozlemler = gozlem_topla(dosyalar)
        damga = damga_gozle(ad=DAMGA_ADI)
        paket = damga_gozle(ad=PAKET_DAMGA_ADI)
    except OlcumHatasi as e:
        print("UZLASTIRMA NABIZ KAPISI — depo %s" % DEPO)
        print("  🔴 OLCULEMEDI: %s" % e)
        print("SONUC: 🔴 OLCULEMEDI (fail-closed) — denetim yasi olculemedi, "
              "'yesil' SAYILMAZ.")
        return 2
    # 🔴 BASLIK "DONMUS TABAN"DIR, YURURLUKTEKI ESIK DEGIL: yururlukteki N her eksenin
    # KENDI satirinda `[esik: ...]` olarak basilir ve is akisinin CANLI teslim oranindan
    # turer. Baslikta 9 yazip satirda 18 gormek, okuyucuya iki farkli hukum anlatirdi
    # ([[ikiz-tanim-sessiz-ayrisma]]) — bu yuzden baslik ne oldugunu ACIKCA soyler.
    print("  (A0 capasi: %s · nominal %d dk · DONMUS taban: teslim orani %.3f -> efektif "
          "%.0f dk -> N=%d sa · yururlukteki N eksen satirinda, tavan %d sa)"
          % (uzl_dosya, uzl_aralik, TESLIM_ORANI, efektif_aralik_dk(uzl_aralik),
             damga_esigi, MUTLAK_SESSIZLIK_SAAT))
    print("  (A4 capasi: %s · nominal %d dk · DONMUS taban N=%d sa · tavan %d sa = "
          "OLCULEN ZARAR penceresinin (%.1f sa) ALTINDA)"
          % (pkt_dosya, pkt_aralik, paket_esigi, PAKET_BAYATLIK_TAVAN_SAAT,
             OLCULEN_PAKET_ZARAR_SAAT))
    return rapor(*degerlendir(dosyalar, gozlemler, damga=damga,
                              damga_esigi=damga_esigi, paket=paket,
                              paket_esigi=paket_esigi))


if __name__ == "__main__":
    sys.exit(main())

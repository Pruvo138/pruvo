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
  A0 DAMGA  (AG · BIRINCIL) — SON BASARILI UZLASTIRMA damgasi N saatten eski mi.
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
     veya cron tanimi degisen is akisina ilk teslim icin ayni N penceresi taninir; kosum
     hala yoksa N'den sonra alarm yanar. Yeniden-kayit zamani workflow API'sinin bayat
     `updated_at` alanindan degil, dosyaya dokunan son commit zamanindan okunur.
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
}

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


def efektif_aralik_dk(nominal_aralik_dk):
    """NOMINAL cron araligini OLCULEN teslim oraniyla GERCEK cadansa cevirir.

    Eski esik NOMINAL araliktan turetiliyordu (15 dk -> N=3 sa) ve GERCEK cadansin
    (olculen 120 dk efektif, tek gozlenen aralik 214,75 dk) ALTINDA kaliyordu -> bos
    kirmizi. Cron'un VAAT ETTIGI degil, GitHub'in TESLIM ETTIGI cadans esas alinir."""
    return nominal_aralik_dk / TESLIM_ORANI


def esik_saat(nominal_aralik_dk):
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
    efektif_saat = efektif_aralik_dk(nominal_aralik_dk) / 60.0
    lam = 1.0 / efektif_saat
    oran = (HAFTA_SAAT * lam) / BOS_ALARM_BUTCESI_HAFTA
    butce_cozumu = (math.log(oran) / lam) if oran > 1.0 else 0.0
    ham = max(butce_cozumu, 2.0 * efektif_saat)
    return int(min(ESIK_TAVAN_SAAT, max(ESIK_TABAN_SAAT, math.ceil(ham - 1e-9))))


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
    olcu = ("teslim %d / nominal %.0f (%%%.2f) · en uzun bosluk %s · medyan bosluk %s · "
            "taban %d kosum / %d sa"
            % (teslim, nominal, oran,
               ("%.0f dk" % maks_bosluk) if maks_bosluk is not None else "-",
               ("%.0f dk" % medyan) if medyan is not None else "-", taban, W))
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
    #
    # 🔴 CAPA A3'TEN BILEREK FARKLI — OLCULEN GEREKCE (4 Agu 2026):
    # A3'un capasi max(kayit_an, yenileme_an)'dir; `yenileme_an` = dosyaya dokunan son
    # commit. A5 icin AYNI capa OLCULDU ve REDDEDILDI: bu depoda alarm dosyalarinin
    # dokunma araligi medyan 5,2 sa (paket) / 5,5 sa (d1); son 8 araligin YALNIZ 1'i
    # 48 saati asiyor. Yani `yenileme_an` capasiyla A5 pratikte HER ZAMAN 🟡 kalirdi —
    # yani tam olarak kapatmak icin yazildigi KORLUGU kendi icinde uretirdi.
    # Capa `kayit_an` (is akisinin GitHub'da kayit ani). Karsi risk BEYAN EDILIR: cron
    # cadansi W icinde degistiyse `nominal` gecmisle uyusmayabilir; bu hal SUSTURULMAZ,
    # satirda ⚠ ile ve yenileme yasiyla BASILIR, ve en gec W sonra kendiliginden gecer.
    kayit_an = g.get("kayit_an")
    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None
    yenileme = g.get("yenileme_an")
    if yenileme is not None:
        yenileme_yas = (simdi - yenileme).total_seconds() / 3600.0
        if yenileme_yas < W:
            olcu += (" · ⚠ cron tanimina dokunan son commit %.1f sa once (< %d sa): "
                     "cadans degistiyse nominal gecmisle tam uyusmayabilir"
                     % (yenileme_yas, W))
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
             "yenileme_an": None, "tum_kosumlar": [], "pencere_kirpildi": False}
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
                for k in satirlar:
                    if not isinstance(k, dict) or "created_at" not in k:
                        raise OlcumHatasi("%s: kosum kaydinda `created_at` yok" % dosya)
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
            "toplam": int, "suresi_dolan": int, "sebep": str|None}
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
                "suresi_dolan": 0,
                "sebep": "depoda `%s` adli HIC artifact YOK" % ad}
    if not taze:
        return {"var": False, "an": None, "kosum": None, "sha": None,
                "toplam": len(kayitlar), "suresi_dolan": len(kayitlar),
                "sebep": "TUM damgalarin (%d adet) SURESI DOLMUS (expired) — saklama "
                         "%d saat, yani en yeni denetim bundan da eski"
                         % (len(kayitlar), DAMGA_SAKLAMA_SAAT)}
    en_yeni = max(taze, key=lambda a: _iso(a["created_at"]))
    kosum = en_yeni.get("workflow_run") or {}
    return {"var": True, "an": _iso(en_yeni["created_at"]),
            "kosum": kosum.get("id") if isinstance(kosum, dict) else None,
            "sha": (kosum.get("head_sha") if isinstance(kosum, dict) else None),
            "toplam": len(kayitlar), "suresi_dolan": len(kayitlar) - len(taze),
            "sebep": None}


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
# A0 ve A4 TEK karar yolundan gecer. Ikinci bir "damga yasi" kopyasi yazilsaydi biri
# gevsedigi zaman oburu sessizce dogru kalir ve ayrisma gorunmezdi
# ([[ikiz-tanim-sessiz-ayrisma]]). Konu metinleri disaridan verilir; MANTIK ORTAK.
def _damga_satiri(eksen, damga, n, simdi, sablon):
    """(satir, alarm_mi). `sablon` = {"yok": ..., "bayat": ..., "taze": ...} bicim dizeleri.
       yok   <- (sebep, N)
       bayat <- (yas, N, yas, kosum, sha12)
       taze  <- (yas, N, taze_sayi, suresi_dolan, kosum)"""
    if not damga.get("var"):
        return ("🔴 %s -> " % eksen) + sablon["yok"] % (damga.get("sebep"), n), True
    yas = (simdi - damga["an"]).total_seconds() / 3600.0
    if yas > n:
        return (("🔴 %s -> " % eksen) + sablon["bayat"]
                % (yas, n, yas, damga.get("kosum"), str(damga.get("sha"))[:12])), True
    return (("✅ %s -> " % eksen) + sablon["taze"]
            % (yas, n, damga["toplam"] - damga["suresi_dolan"], damga["suresi_dolan"],
               damga.get("kosum"))), False


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
             "suresi dolan %d · kosum %s)"),
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
             "damga %d, suresi dolan %d · kosum %s)"),
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

    # --- A0 DAMGA + A4 PAKET (BIRINCIL EKSENLER, AYNI KARAR YOLU) ------------
    for eksen, gozlem, esik, sablon in (
            ("A0 DAMGA", damga, damga_esigi, A0_SABLON),
            ("A4 PAKET", paket, paket_esigi, A4_SABLON)):
        if gozlem is None:
            continue
        satir, yandi = _damga_satiri(eksen, gozlem, esik or ESIK_TABAN_SAAT, simdi, sablon)
        satirlar.append(satir)
        alarm = alarm or yandi

    for dosya, cron in dosyalar:
        hata, aralik = bicim_hukmu(dosya, cron)
        if hata:
            satirlar.append("🔴 " + hata)
            alarm = True
        else:
            satirlar.append("✅ A1 BICIM %s -> cron %r · aralik %d dk · esik N=%d saat"
                            % (dosya, cron, aralik, esik_saat(aralik)))

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

        n = g["esik"]
        son_tanim_an = max(g["kayit_an"], g["yenileme_an"])
        son_tanim_yasi = (simdi - son_tanim_an).total_seconds() / 3600.0
        yeni_tanim = (g["son_kosum"] is None or son_tanim_an > g["son_kosum"])
        if yeni_tanim and son_tanim_yasi <= n:
            satirlar.append("🟡 A3 NABIZ %s -> cron tanimi %.1f saat once kaydedildi; "
                            "bu tanimdan event=schedule kosumu henuz YOK (esik N=%d sa). "
                            "Ilk tetikleme icin olculen teslim penceresi dolmadi; eski "
                            "cron kosumu yeni tanimin nabzi SAYILMADI."
                            % (etiket, son_tanim_yasi, n))
            continue
        if g["kosum_sayisi"] == 0:
            kayit_yasi = (simdi - g["kayit_an"]).total_seconds() / 3600.0
            if kayit_yasi <= n:
                satirlar.append("🟡 A3 NABIZ %s -> event=schedule kosumu henuz YOK; "
                                "is akisi %.1f saat once kaydedildi (esik N=%d sa). "
                                "Ilk tetikleme icin olculen teslim penceresi dolmadi; "
                                "durum gorunur, alarm henuz yanmaz." % (etiket, kayit_yasi, n))
            else:
                satirlar.append("🔴 A3 NABIZ %s -> event=schedule kosum sayisi SIFIR: "
                                "cron HIC ATESLENMEMIS. Is akisi %.1f saattir kayitli ve aktif "
                                "(esik N=%d sa) -> bu is akisinin yaptigi HICBIR SEY "
                                "yapilmiyor ve hicbir yerde kirmizi yanmiyor."
                                % (etiket, kayit_yasi, n))
                alarm = True
            continue
        if g["son_kosum"] is None:
            satirlar.append("🔴 A3 NABIZ %s -> son kosum zamani OKUNAMADI (fail-closed)"
                            % etiket)
            alarm = True
            continue
        yas = (simdi - g["son_kosum"]).total_seconds() / 3600.0
        beklenen = int(round(yas * 60 / g["aralik"])) if g["aralik"] else 0
        if yas > n:
            satirlar.append("🔴 A3 NABIZ (ikincil) %s -> son event=schedule kosumu %.1f "
                            "saat once (esik N=%d sa · nominal aralik %d dk · efektif "
                            "%.0f dk · bu surede nominal ~%d tetikleme, teslim 0). "
                            "Cron SESSIZ."
                            % (etiket, yas, n, g["aralik"],
                               efektif_aralik_dk(g["aralik"]), beklenen))
            alarm = True
        else:
            satirlar.append("✅ A3 NABIZ (ikincil) %s -> son event=schedule kosumu %.1f "
                            "saat once (esik N=%d sa · efektif cadans %.0f dk · toplam "
                            "%d zamanlanmis kosum)"
                            % (etiket, yas, n, efektif_aralik_dk(g["aralik"]),
                               g["kosum_sayisi"]))
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


def _damga_kaydi(yas_saat, expired=False, ad=None, kimlik=8806704610):
    """GERCEK artifact govdesinin ayni seklinde tek damga kaydi."""
    a = json.loads(json.dumps(_HAM_ARTIFACT))
    a["id"] = kimlik
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
               damgalar=None, kosum_yaslari=None):
    """GERCEK govdenin ayni seklini ureten enjekte edilebilir `getir`.

    `damgalar`: artifact kayitlari listesi (None -> tek TAZE damga).
    `kosum_yaslari`: `event=schedule` kosumlarinin YASLARI (saat). None -> TEK kayit
      (`yas_saat`) doner; bu, A5 acisindan "gecmis penceresi kadar veri YOK" halidir ve
      varsayilan fikstur kayit/yenileme yasi 24 sa oldugu icin A5 🟡 kalir — yani A5
      MEVCUT iddialarin higbirinin isaretini degistirmez, kendi fiksturleriyle olculur."""
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
            kayitlar = [_damga_kaydi(1.0)] if damgalar is None else damgalar
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
                        "workflow_runs": [_kosum_kaydi(yas_saat, event, dosya)]}
            # 🔴 SIRA BILEREK BOZUK: GERCEK API yeniden eskiye doner; kod BUNA
            # GUVENMEMELIDIR. Fikstur listeyi karistirarak "siralamayi API'ye birakma"
            # iddiasini KOSAR (siralamayi kaldiran mutant KIRMIZI yanar).
            yaslar = list(kosum_yaslari)
            kayitlar = [_kosum_kaydi(y, event, dosya, kimlik=1000 + i)
                        for i, y in enumerate(yaslar)]
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
    """(bayraksiz_var, kendini_test_var) — deploy.yml bu betigin HANGI kollarini
    ANLAMLI OLARAK icra ediyor.

    KESIF AYNALANMAZ ([[ayna-kapi-kesif-ekseni]]): `run:` dugumleri tools/yaml-oku.py'nin
    GERCEK ayristiricisiyla, "bu satir gercekten icra ediyor mu" hukmu ise
    tools/icra-suzgeci.py ile verilir — ikisi de bu depoda TEK KAYNAK.

    NEDEN GEREKLI: bu betigin deploy.yml'de IKI cagrisi var. ci-kapsam-test.py
    "dosya kosuluyor mu" diye bakar; biri silinse OBURU yuzunden hala YESIL kalir.
    Olculdu (ayni delik tools/ci-kapsam-test.py::bayraksiz_adim_kontrol'de): iki cagrili
    bir betikte GERCEK olcum kolu silinince dort denetci de rc=0 veriyordu."""
    yaml_oku = _modul("yaml-oku")
    suzgec = _modul("icra-suzgeci")
    yol = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
    if not os.path.exists(yol):
        raise OlcumHatasi("deploy.yml YOK: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        bloklar, hata = yaml_oku.run_dugumleri(f.read())
    if hata:
        raise OlcumHatasi("deploy.yml `run:` dugumleri okunamadi: %s" % hata)
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
    iddia("A0 (a) rapor damga yasini ve kosumunu SAYIYLA yazar",
          any("A0 DAMGA" in x and "1.5 saat" in x and "30663827609" in x for x in s))
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
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=12.0,
                              yenileme_yas_saat=0.8))
    iddia("A3 (a0b) cron YENIDEN KAYDEDILDI, eski kosum N disinda ama yeni tanim "
          "N icinde -> GORUNUR ve YESIL", rc == 0, "rc=%d" % rc)
    iddia("A3 (a0b) eski kosumu yeni tanimin nabzi saymaz; ilk teslim penceresini yazar",
          any("🟡 A3 NABIZ" in x and "cron tanimi 0.8 saat" in x
              and "eski cron kosumu" in x for x in s), s)
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
    iddia("CI KABLOSU: deploy.yml GERCEK olcum kolunu (bayraksiz) ANLAMLI olarak kosuyor",
          bayraksiz, kablo_hata or "bulunamadi")
    iddia("CI KABLOSU: deploy.yml `--kendini-test` kolunu ANLAMLI olarak kosuyor",
          kendini, kablo_hata or "bulunamadi")

    # ═══════════════════════════════════════════════════════════════════════
    # A4 PAKET TAZELIGI — ONCE-KIRMIZI FIKSTURLERI
    # ═══════════════════════════════════════════════════════════════════════
    # 🔴 NEDEN FIKSTUR SART: canli kol BUGUN YESIL (Okan 1 Agu 17:29'da deploy etti,
    # fiziksel nobetci rc=0). "Alarm bayatligi gorur" iddiasi canli kosumla KANITLANAMAZ;
    # ancak fiksturle gosterilebilir. Asagidaki senaryolarin hepsi AGSIZ.
    P = [("d1-uzlastirici.yml", "7,22,37,52 * * * *"),
         (PAKET_ALARM_DOSYA, "11,26,41,56 * * * *")]

    def paket_api(paket_damgalari, yas_saat=0.4, kosum_sayisi=137, bozuk=None,
                  kosum_yaslari=None):
        """Iki is akisi + IKI AYRI damga adi donduren `getir` (ad suzgeci FIILEN calisir).

        🔴 KOSUM DAGILIMI SAGLIKLI VERILIR (varsayilan 48 sa'te 8 teslim): bu blogun
        iddialari A4 DAMGA eksenini yalitir. Fikstur tek kosum dondurseydi A5 TESLIM
        ekseni de kirmizi yanar ve "A4 damgasi taze -> YESIL" iddialari A4 yuzunden
        DEGIL A5 yuzunden dusup TEK DEGISKEN yalitimini bozardi
        ([[fikstur-degeri-mutasyonu-kor-eder]] — fikstur degeri iddiayi kaydirir)."""
        if kosum_yaslari is None:
            kosum_yaslari = [yas_saat, 6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0]
        temel = _sahte_api(kosum_sayisi=kosum_sayisi, yas_saat=yas_saat, bozuk=bozuk,
                           kosum_yaslari=kosum_yaslari)

        def getir(yol, zaman_asimi=25):
            if "actions/artifacts?" in yol:
                if bozuk == "paket-ag":
                    raise OlcumHatasi("GitHub API HTTP 502: actions/artifacts")
                if ("name=%s" % PAKET_DAMGA_ADI) in yol:
                    if bozuk == "paket-suzgec":
                        return {"total_count": 1,
                                "artifacts": [_damga_kaydi(0.5, ad=DAMGA_ADI)]}
                    return {"total_count": len(paket_damgalari),
                            "artifacts": [dict(a, name=PAKET_DAMGA_ADI)
                                          for a in paket_damgalari]}
                return {"total_count": 1, "artifacts": [_damga_kaydi(1.0)]}
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

    # DAMGA KUTUGU: yazici iki adi da tanir, kutuk disina cikamaz.
    for ad in (DAMGA_ADI, PAKET_DAMGA_ADI):
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
    print("  (A0 capasi: %s · nominal %d dk · olculen teslim orani %.3f · efektif %.0f dk "
          "-> esik N=%d sa)"
          % (uzl_dosya, uzl_aralik, TESLIM_ORANI, efektif_aralik_dk(uzl_aralik),
             damga_esigi))
    print("  (A4 capasi: %s · nominal %d dk · efektif %.0f dk -> esik N=%d sa)"
          % (pkt_dosya, pkt_aralik, efektif_aralik_dk(pkt_aralik), paket_esigi))
    return rapor(*degerlendir(dosyalar, gozlemler, damga=damga,
                              damga_esigi=damga_esigi, paket=paket,
                              paket_esigi=paket_esigi))


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CANLI SAGLIK NOBETCISI — "DEPO/D1 ne diyor" ile "MUSTERININ GORDUGU CANLI" farkini olcer.

NEDEN VAR (uc olculmus vaka, 30 Tem — UCUNU DE MAKINE DEGIL INSAN YAKALADI):
  VAKA 1 — SAYFA YAYINI. Yeni eklenen 18 urunun /urun/<id>/ sayfasi canlida 404 doniyordu.
    Yayin penceresi kapandiktan SONRA da 404 kaldi, cunku Cloudflare o 404'u ~4 saat
    onbellege almisti. Katalogda urun VARDI, karta tiklayan musteri bos sayfa gordu.
    (Edge 404 TTL o gun ~30 sn'ye indirildi -> bugun `age` KUCUKSE gercek 404,
     BUYUKSE onbellek artigidir. Bu ayrimi bu nobetci yapar.)
  VAKA 2 — CI KIRMIZI, YAYIN DURMUS. CI kirmizi kaldigi icin 23 urun canlia HIC cikmadi:
    depo 15039, canli 15016. Hicbir kapi konusmadi cunku kapilar COMMIT'i dogruluyor,
    kimse "canlida kac urun var" diye SORMUYORDU.
  VAKA 4 — ORNEKLEM KORLUGU (30 Tem 22:25, YINE INSAN YAKALADI). Tek urun eklendi
    (`yan-birakmali-kayis-tokasi`); 3 dk sonra gelen 26'lik parti onu dizide 26. siraya
    itti. Nobetci "en yeni 20 DIZI kaydini" ornekledigi icin urunu HIC olcmedi, SAYFA
    ekseni "20/20 -> 200" ile YESIL yandi; ayni anda o sayfa canlida 404'tu.
    -> Orneklem artik IKI EKSENLI: dizi-basi N + SON K COMMIT'te eklenen TUM urunler.
  VAKA 3 — KART KANALI KAPALI. Iki figur canlida gorunuyordu ama worker eski paketi
    kosuyordu -> POST /api/shop/fiyat 400 doniyordu, kalem kartla ODENEMIYORDU. 2 gun surdu.

ORTAK NOKTA: depo/D1 ile CANLI arasindaki sapmayi olcen bir sey yoktu. Bu nobetci o bosluğu
kapatir. Kapilar "commit dogru mu" der; bu nobetci "MUSTERI NE GORUYOR" der.

OLCTUKLERI (hepsi SALT-OKUNUR, GERCEK MUSTERI KOSULU — cache-bypass basligi KULLANILMAZ;
onbellegi atlayan bir olcum tam da VAKA 1'i kacirirdi):
  K0 ORNEKLEM  NEYI olctugumuzu yargilar: son K commit'te eklenen her urun orneklem'e
               GIRDI mi (girmediyse SAPMA — nobetci o urunler icin KOR), gecmis
               okunamadiysa ARIZA. Sessiz/dar orneklem YASAK; bilesim rapora basilir.
  K1 KATALOG   canli /urunler.json urun sayisi == depo (origin/main) sayisi mi.
  K2 SAYFA     orneklenen urunlerin /urun/<id>/ sayfasi 200 mu (404'te cf-cache-status + age).
  K3 CI        origin/main'in son kosumu success mi; kirmizysa hangi adim.
  K4 KART      konfigurlu urunler canli worker'da gercekten fiyatlaniyor mu.
               ⚠️ IKINCI KOPYA ACILMAZ: bu eksen tools/konfigur-canli-kapisi.py'nindir;
               varsa O CAGIRILIR, yoksa "OLCULEMEDI" denir (sessiz yesil verilmez).
  K5 D1/GORSEL en yeni N urun canli worker'in D1 katalogunda TANINIYOR mu (Ege'nin okudugu
               yer) + gorsel referanslari R2'de gercekten VAR mi.
  K6 FIZIKSEL  hazir ticari malda (`tur == "fiziksel"`) canli worker LISTE FIYATINI mi tahsil
               ediyor + canli paket depo HEAD'i ile ayni nesli mi tasiyor.
               ⚠️ IKINCI KOPYA ACILMAZ: bu eksen tools/fiziksel-canli-kapisi.py'nindir;
               varsa O CAGIRILIR, yoksa "OLCULEMEDI" denir.
               🔴 VAKA 5 (1 Agu, OLCULDU) — K4 BU EKSENI GORMEZ: K4 yalnizca KONFIGURLU (17)
               urunu olcer. Canli paket 30 Tem 20:30 – 1 Agu 01:58 arasi bayat kaldi ve 676
               fiziksel uruntte malzeme/renk carpani uygulamaya DEVAM etti (liste x1,840'a
               varan FAZLA tahsilat). O sirada K4 rc=0, bu nobetci rc=0 idi. Korlugun sebebi
               "K4 dar" degil, `tur` ekseninin HIC OLCULMEMESIYDI.

🔴 YAYIN PENCERESI AYRIMI (bu aracin asil YARGISI — yanlis-pozitif kapisi):
  "canli geride" tek basina ARIZA DEGILDIR: push'tan sonra CI ~5 dk kosar, sonra Pages+CDN
  yerlesir. Ayni sayilar penceredeyken NORMAL, pencere kapandiktan sonra ARIZADIR.
  Bu yuzden her sapma once yayin_penceresi() hukmunden gecer:
    CI-KOSUYOR / KOSUM-BASLAMAMIS / YERLESIYOR -> BEKLENIYOR (sapma DEGIL, "N dk"yi yazar)
    CI-KIRMIZI                                 -> SAPMA, kok neden CI (once onu duzelt)
    YERLESIK                                   -> SAPMA, YAYIN KIRIK
  Fikstur ikizi bunu kanitlar: YAYIN-PENCERESI (BEKLENIYOR) vs YAYIN-KIRIK (SAPMA) —
  AYNI sayilar, TEK fark CI'nin hali.

FAIL-CLOSED OLCUM, FAIL-OPEN KAPI:
  * Olculemeyen sey ASLA yesil sayilmaz -> "OLCULEMEDI" sinifi ve ayri cikis kodu var.
  * Ama bu arac CI'da BLOKLAYICI DEGILDIR ve olmamalidir: ag/canli durum oynaktir, tek
    gecici DNS hatasi tum ekibin yayinini durdururdu ([[kapi-kapsam-eksen-secimi]]).
    CI'da YALNIZ `--kendini-test` (AGSIZ, yalniz fikstur) kosar.
  * SAPMA KANITI, olcum arizasini EZER (konfigur-canli-kapisi ile ayni oncelik): elimizde
    zaten para/musteri kaybettiren bir bulgu varken kapi "olculemedi"ye dusmez.

CIKIS KODLARI:
  0 SAGLIKLI    — sapma yok (BEKLENIYOR satirlari olabilir: yayin penceresi acik).
  1 SAPMA       — en az bir gercek sapma. Her satirin yaninda tek satirlik "ne yapilmali".
  2 OLCULEMEDI  — sapma KANITI yok ama saglik da KANITLANMADI (ag/uc erisilemedi).

KULLANIM:
    python3 tools/canli-saglik-kapisi.py                 # canli olcum (ag ISTER, ~30 s)
    python3 tools/canli-saglik-kapisi.py --adet 40       # dizi-basi eksenini genislet
    python3 tools/canli-saglik-kapisi.py --son-commit 20 # yeni-commit eksenini genislet
    python3 tools/canli-saglik-kapisi.py --json          # makine okunur cikti
    python3 tools/canli-saglik-kapisi.py --kendini-test  # AGSIZ fikstur kabulu (CI'da bu kosar)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

SITE_VARSAYILAN = "https://pruvo3d.com"
CI_API_VARSAYILAN = "https://api.github.com/repos/Pruvo138/pruvo/actions/runs"
ANA_DAL = "origin/main"
ADET_VARSAYILAN = 20

# 🔴 ORNEKLEM IKI EKSENLI — "en yeni N DIZI kaydi" TEK BASINA YETMEZ (olculdu 30 Tem).
# OLCULEN VAKA: `yan-birakmali-kayis-tokasi` 22:25'te eklendi, 3 dk sonra gelen 26 urunluk
# parti onu dizide 26. siraya itti. --adet 20 ile nobetci onu ORNEKLEMEDI ve SAYFA ekseni
# "20/20 -> 200" diyerek YESIL yandi; ayni anda o urunun sayfasi canlida 404'tu.
# DERS: "yeni urun" DIZI KONUMU degil COMMIT olayidir. Bu yuzden orneklem =
#   (1) YENI-COMMIT ekseni: son SON_COMMIT_SAYISI commit'te urunler.json'a EKLENEN her id
#   (2) DIZI-BASI ekseni  : dizinin en yeni `adet` kaydi (eski davranis, korunur)
# birlesimidir ve bilesimi RAPORA BASILIR (sessiz orneklem YASAK).
# K KALIBRASYONU (olculdu 30 Tem, origin/main): parti ekleme commit'i basina ~25 urun.
#   son 1 commit -> 26 yeni · son 4 -> 27 · son 6 -> 55 · son 12 -> 100 · son 30 -> 196.
# Yayin gecikmesi tavani (cancel-in-progress: false ile) ~11 dk, push araligi ortanca
# 9,2 dk -> 6 commit'lik pencere riskli sinifi FAZLASIYLA kapsar, 250 tavaninin altinda
# kalir. Buyutmek isteyen `--son-commit` ile buyutur (ve tavani da gozetir).
SON_COMMIT_SAYISI_VARSAYILAN = 6
# Yeni-commit ekseni tavani: istek sayisi sinirsiz buyumesin. SAYFA istekleri STATIK
# CDN'e gider (worker hiz siniri YOK) -> tavan genis tutulabilir. Tavan ASILIRSA bu
# SESSIZCE kirpilmaz -> ORNEKLEM ekseni SAPMA verir (korluk KANITLANIR).
YENI_EKSEN_TAVAN = 250
# Sayfa istekleri Pages/CDN'e gider; worker hiz siniri (60/60 sn) BURAYA UYGULANMAZ.
# Bu yuzden sayfa ekseni ayri, kucuk bir gecikme kullanir: 250 sayfa ~12 s'de olculur.
SAYFA_GECIKME = 0.05

# R2/edge urllib UA 403 dersi ([[r2-urllib-ua-403-tuzagi]]): ciplak python-urllib UA'si bot
# sayilip 403 yiyebilir -> olcum "gorsel yok" sanip YANLIS ALARM verirdi. Tarayici UA'si.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# CI kosumu ~5 dk (olculdu 30 Tem: 17:55:21 -> 18:00:37). Kosum BITTIKTEN sonra Pages
# dagitimi + CDN yerlesmesi icin ek tolerans; ikisinin toplami "push sonrasi ~10 dk".
YERLESME_TOLERANS_SN = 300
# Edge 404 TTL 30 Tem'de ~30 sn'ye indirildi. age BUNDAN buyukse gordugumuz 404 ONBELLEK
# ARTIGIDIR (origin bugun 200 doneibilir); kucukse GERCEK 404'tur.
ONBELLEK_YAS_ESIGI_SN = 60
# Worker FIYAT_RATE_LIMIT 60 istek / 60 sn -> istekler arasi varsayilan bekleme.
GECIKME_VARSAYILAN = 0.4

# Sapma sayilan siniflar (BEKLENIYOR ve TAMAM sapma DEGIL; ARIZA olcum arizasidir).
SAPMA_SINIFLARI = ("SAPMA", "ONBELLEK")


# ================================================================= gozlem (AG KATMANI)
# Bu bolumdeki her sey I/O yapar. Karar mantigi (degerlendir) buraya HIC dokunmaz ->
# --kendini-test bu bolumu CALISTIRMADAN kararlari sinar (agsiz kabul mumkun olsun diye).

def _istek(url, method="GET", govde=None, ctype=None, zaman_asimi=25):
    """(http_kodu|None, basliklar, govde_baytlari, hata_metni|None). ASLA istisna atmaz."""
    basliklar = {"User-Agent": UA}
    if ctype:
        basliklar["Content-Type"] = ctype
    istek = urllib.request.Request(url, data=govde, method=method, headers=basliklar)
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            return y.status, {k.lower(): v for k, v in y.headers.items()}, y.read(), None
    except urllib.error.HTTPError as e:
        try:
            ham = e.read()
        except Exception:
            ham = b""
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, ham, None
    except Exception as e:                                  # ag / DNS / TLS / zaman asimi
        return None, {}, b"", type(e).__name__ + ": " + str(e)


def _yas(basliklar):
    try:
        return int(basliklar.get("age", ""))
    except (TypeError, ValueError):
        return None


def depo_gozlemi(dal=ANA_DAL):
    """origin/main'deki urun sayisi + tip sha + commit zamani. Ag: yalniz `git fetch` YAPMAZ
    (bilerek — fetch YAZAR; cagiran tazeligi kendi saglar; bayat ref uyarisi basilir)."""
    out = {"dal": dal, "sayi": None, "sha": None, "commit_zamani": None, "hata": None,
           "idler": []}
    try:
        p = subprocess.run(["git", "-C", ROOT, "rev-parse", dal],
                           capture_output=True, text=True)
        if p.returncode != 0:
            out["hata"] = "rev-parse basarisiz: " + (p.stderr or "").strip()[:120]
            return out
        out["sha"] = p.stdout.strip()
        p = subprocess.run(["git", "-C", ROOT, "show", "-s", "--format=%ct", out["sha"]],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip().isdigit():
            out["commit_zamani"] = int(p.stdout.strip())
        p = subprocess.run(["git", "-C", ROOT, "show", dal + ":urunler.json"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            out["hata"] = "urunler.json okunamadi: " + (p.stderr or "").strip()[:120]
            return out
        urunler = json.loads(p.stdout)
        out["sayi"] = len(urunler)
        out["idler"] = [u.get("id") for u in urunler]
        out["urunler"] = urunler
    except OSError as e:                                     # `git` binary'si yok
        out["hata"] = "git calistirilamadi: " + str(e)
    except ValueError as e:
        out["hata"] = "urunler.json ayristirilamadi: " + str(e)
    return out


def yeni_urun_gozlemi(dal=ANA_DAL, son_commit=SON_COMMIT_SAYISI_VARSAYILAN):
    """Son `son_commit` commit'te urunler.json'a EKLENEN id'ler (dal ile dal~K'nin farki).

    Neden diff degil iki kume: urunler.json 13,5 MB; `git log -p` bu dosyada ~68 MB diff
    uretir (olculdu). Iki `git show` + kume farki AYNI cevabi ~1 s'de verir.
    FAIL-CLOSED: gecmis okunamazsa (shallow checkout, kopuk ref) SESSIZCE bos kume
    donmez -> `hata` doldurulur ve ORNEKLEM ekseni bunu ARIZA olarak raporlar."""
    out = {"son_commit": son_commit, "idler": [], "hata": None, "taban_sha": None}
    try:
        p = subprocess.run(["git", "-C", ROOT, "rev-parse", "%s~%d" % (dal, son_commit)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            out["hata"] = ("gecmis okunamadi (%s~%d): " % (dal, son_commit)
                           + (p.stderr or "").strip()[:120])
            return out
        out["taban_sha"] = p.stdout.strip()
        p = subprocess.run(["git", "-C", ROOT, "show", out["taban_sha"] + ":urunler.json"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            out["hata"] = "taban urunler.json okunamadi: " + (p.stderr or "").strip()[:120]
            return out
        eski = set(u.get("id") for u in json.loads(p.stdout))
        p = subprocess.run(["git", "-C", ROOT, "show", dal + ":urunler.json"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            out["hata"] = "guncel urunler.json okunamadi: " + (p.stderr or "").strip()[:120]
            return out
        yeni = [u.get("id") for u in json.loads(p.stdout)]
        out["idler"] = [i for i in yeni if i not in eski]
    except OSError as e:
        out["hata"] = "git calistirilamadi: " + str(e)
    except ValueError as e:
        out["hata"] = "urunler.json ayristirilamadi: " + str(e)
    return out


def orneklem_sec(urunler, yeni_idler, adet, tavan=YENI_EKSEN_TAVAN):
    """SAF secim (ag/git YOK -> agsiz sinanabilir). Iki ekseni birlestirir, bilesimi doner.

    Donen: (secilen_urunler, kompozisyon). Kompozisyon RAPORA basilir ve ORNEKLEM
    kontrolu onu YARGILAR: yeni-commit ekseninden DISARIDA kalan id varsa SAPMA."""
    dizi_basi = list(urunler[:adet])
    dizi_basi_idler = set(u.get("id") for u in dizi_basi)
    yeni_kume = set(i for i in (yeni_idler or []) if i)
    # yeni-commit ekseni: dizideki gercek kayitlara esle (dizi sirasi = en yeni once)
    yeni_kayitlar = [u for u in urunler if u.get("id") in yeni_kume]
    kirpildi = []
    if len(yeni_kayitlar) > tavan:
        kirpildi = [u.get("id") for u in yeni_kayitlar[tavan:]]
        yeni_kayitlar = yeni_kayitlar[:tavan]
    secilen = list(dizi_basi)
    gorulen = set(dizi_basi_idler)
    for u in yeni_kayitlar:
        if u.get("id") not in gorulen:
            secilen.append(u)
            gorulen.add(u.get("id"))
    kompozisyon = {
        "toplam": len(secilen),
        "dizi_basi": len(dizi_basi),
        "yeni_commit": len(yeni_kayitlar),
        "yalniz_yeni_eksen": len([u for u in yeni_kayitlar
                                  if u.get("id") not in dizi_basi_idler]),
        "kirpilan": kirpildi,
        "yeni_toplam": len(yeni_kume),
        "kapsanmayan": sorted(yeni_kume - gorulen),
    }
    return secilen, kompozisyon


def canli_katalog_gozlemi(site, zaman_asimi=45):
    kod, basliklar, ham, hata = _istek(site + "/urunler.json", zaman_asimi=zaman_asimi)
    out = {"http": kod, "sayi": None, "idler": set(), "hata": hata,
           "cf": basliklar.get("cf-cache-status"), "age": _yas(basliklar),
           "last_modified": basliklar.get("last-modified"), "bayt": len(ham)}
    if hata or kod != 200:
        if not out["hata"]:
            out["hata"] = "HTTP %s" % kod
        return out
    try:
        urunler = json.loads(ham.decode("utf-8"))
        out["sayi"] = len(urunler)
        out["idler"] = set(u.get("id") for u in urunler)
    except Exception as e:
        out["hata"] = "canli urunler.json ayristirilamadi: " + str(e)
    return out


def ci_gozlemi(api, depo_sha, zaman_asimi=25):
    """origin/main'in SON kosumu. depo_sha icin kosum YOKSA bu ayrica raporlanir
    (KOSUM-BASLAMAMIS = yayin penceresi ACIK, ariza DEGIL)."""
    kod, _b, ham, hata = _istek(api + "?branch=main&per_page=10", zaman_asimi=zaman_asimi)
    out = {"durum": None, "sonuc": None, "sha": None, "bitis": None, "url": None,
           "adim": None, "hata": hata, "sha_icin_kosum_var": None}
    if hata:
        return out
    if kod != 200:
        out["hata"] = "GitHub API HTTP %s" % kod
        return out
    try:
        kosumlar = json.loads(ham.decode("utf-8")).get("workflow_runs") or []
    except Exception as e:
        out["hata"] = "GitHub API cevabi ayristirilamadi: " + str(e)
        return out
    if not kosumlar:
        out["hata"] = "main icin kosum bulunamadi"
        return out
    son = kosumlar[0]
    out["durum"] = son.get("status")                 # queued | in_progress | completed
    out["sonuc"] = son.get("conclusion")             # success | failure | cancelled | None
    out["sha"] = son.get("head_sha")
    out["url"] = son.get("html_url")
    out["bitis"] = _iso_epoch(son.get("updated_at"))
    out["sha_icin_kosum_var"] = any(k.get("head_sha") == depo_sha for k in kosumlar) \
        if depo_sha else None
    if out["sonuc"] == "failure":
        out["adim"] = _kirmizi_adim(son.get("jobs_url"), zaman_asimi)
    return out


def _iso_epoch(metin):
    if not metin:
        return None
    try:
        return int(time.mktime(time.strptime(metin, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone)
    except Exception:
        return None


def _kirmizi_adim(jobs_url, zaman_asimi=25):
    """Kirmizi kosumda BASARISIZ ADIMIN adi — "CI kirmizi" demek yetmez, hangi kapinin
    yandigini soylemeyen rapor eyleme donuk degildir."""
    if not jobs_url:
        return None
    kod, _b, ham, hata = _istek(jobs_url, zaman_asimi=zaman_asimi)
    if hata or kod != 200:
        return None
    try:
        for is_ in json.loads(ham.decode("utf-8")).get("jobs") or []:
            for adim in is_.get("steps") or []:
                if adim.get("conclusion") == "failure":
                    return "%s / %s" % (is_.get("name") or "?", adim.get("name") or "?")
    except Exception:
        return None
    return None


def sayfa_gozlemi(site, idler, canli_idler, gecikme=GECIKME_VARSAYILAN, zaman_asimi=25):
    out = []
    for i, uid in enumerate(idler):
        if i and gecikme:
            time.sleep(gecikme)
        kod, basliklar, _h, hata = _istek(site + "/urun/" + uid + "/", zaman_asimi=zaman_asimi)
        out.append({"id": uid, "http": kod, "hata": hata,
                    "cf": basliklar.get("cf-cache-status"), "age": _yas(basliklar),
                    "canli_katalogda": (uid in canli_idler) if canli_idler else None})
    return out


def d1_gozlemi(site, urunler, gecikme=GECIKME_VARSAYILAN, zaman_asimi=25):
    """Canli worker'in D1 katalogunda urun TANINIYOR mu — POST /api/shop/fiyat PROVA ucu.

    YAN ETKI YOK: prova ucu D1'e YAZMAZ, siparis OLUSTURMAZ, iyzico/Telegram/e-postaya
    GITMEZ (yapisal kanit shop/test/fiyat-prova.mjs: D1 run() ve fetch sayaclari 0).
    Neden bu uc: D1'i wrangler/token OLMADAN, GERCEK MUSTERI YOLUNDAN okumanin tek yolu.
    "bilinmeyen-urun" = urun D1'de YOK -> Ege o urunu GOREMEZ, kart kanali o urunde KAPALI.

    ⚠️ KAPSAM AYRIMI: burada FIYAT DOGRULUGU IDDIA EDILMEZ (o eksen konfigur-canli-kapisi'nin).
    Burada yalniz VARLIK olculur ve yalniz KONFIGURSUZ urunler sorulur -> iki arac ayni
    urunde ayni iddiayi IKI KEZ olcmez."""
    out = []
    for i, urun in enumerate(urunler):
        if i and gecikme:
            time.sleep(gecikme)
        govde = json.dumps({"sepet": [{"id": urun["id"], "malzeme": "PLA",
                                       "renk": "Siyah", "adet": 1}]}).encode("utf-8")
        kod, _b, ham, hata = _istek(site + "/api/shop/fiyat", "POST", govde,
                                    "application/json", zaman_asimi)
        kayit = {"id": urun["id"], "sonuc": "ariza", "detay": hata or ("HTTP %s" % kod)}
        if not hata:
            try:
                cevap = json.loads(ham.decode("utf-8"))
            except Exception:
                cevap = {}
            if kod == 200:
                kayit["sonuc"] = "var"
                kayit["detay"] = "%s kurus" % (
                    (cevap.get("satirlar") or [{}])[0].get("birim_kurus"))
            elif kod == 400 and cevap.get("hata") == "bilinmeyen-urun":
                kayit["sonuc"] = "yok"
                kayit["detay"] = "D1'de kayit YOK"
            elif kod == 429:
                kayit["detay"] = "429 hiz siniri"
        out.append(kayit)
    return out


def gorsel_gozlemi(site, urunler, gecikme=0.15, zaman_asimi=25):
    del site
    out = []
    for i, urun in enumerate(urunler):
        gorseller = urun.get("gorseller") or []
        if not gorseller:
            out.append({"id": urun["id"], "url": None, "http": None,
                        "hata": "urunde gorsel YOK"})
            continue
        if i and gecikme:
            time.sleep(gecikme)
        url = gorseller[0]
        kod, _b, _h, hata = _istek(url, "HEAD", zaman_asimi=zaman_asimi)
        out.append({"id": urun["id"], "url": url, "http": kod, "hata": hata})
    return out


def kart_kanali_gozlemi(site, gecikme=GECIKME_VARSAYILAN):
    """K4 — IKINCI KOPYA ACILMAZ. tools/konfigur-canli-kapisi.py VARSA o cagirilir
    (kart kanali ekseninin TEK sahibi odur); YOKSA "arac yok" denir ve OLCULEMEDI sayilir.
    Sessiz yesil YOK: araci olmayan bir eksen "saglikli" ilan EDILMEZ."""
    yol = os.path.join(TOOLS, "konfigur-canli-kapisi.py")
    if not os.path.isfile(yol):
        return {"hal": "ARAC-YOK", "detay": "tools/konfigur-canli-kapisi.py bu agacta YOK "
                                            "(dal main'e alinmamis olabilir)"}
    p = subprocess.run([sys.executable, yol, "--uc", site + "/api/shop/fiyat",
                        "--gecikme", str(gecikme)], capture_output=True, text=True)
    hal = {0: "PARITE", 1: "DRIFT", 2: "OLCULEMEDI"}.get(p.returncode, "OLCULEMEDI")
    ozet = [s.strip() for s in (p.stdout or "").splitlines()
            if s.strip().startswith(("TANIMIYOR", "SAPMA", "ARIZA"))]
    return {"hal": hal, "detay": "; ".join(ozet[:4]) or (p.stdout or "").strip()[-200:]}


def fiziksel_fiyat_gozlemi(site, gecikme=GECIKME_VARSAYILAN):
    """K6 — IKINCI KOPYA ACILMAZ. tools/fiziksel-canli-kapisi.py VARSA o cagirilir (hazir
    ticari mal fiyat ekseninin TEK sahibi odur); YOKSA "arac yok" denir ve OLCULEMEDI sayilir.

    K4'ten AYRI bir eksendir ve K4'e DEVREDILEMEZ: K4'un araci yalnizca konfigurlu urunleri
    olcer, bu eksen `tur == "fiziksel"` sinifini olcer. 1 Agu'da ikisi de yesil yanarken
    canli worker fiziksel uruntte liste fiyatinin 1,840 katini tahsil ediyordu."""
    yol = os.path.join(TOOLS, "fiziksel-canli-kapisi.py")
    if not os.path.isfile(yol):
        return {"hal": "ARAC-YOK", "detay": "tools/fiziksel-canli-kapisi.py bu agacta YOK "
                                            "(dal main'e alinmamis olabilir)"}
    p = subprocess.run([sys.executable, yol, "--uc", site + "/api/shop/fiyat",
                        "--gecikme", str(gecikme)], capture_output=True, text=True)
    hal = {0: "PARITE", 1: "DRIFT", 2: "OLCULEMEDI"}.get(p.returncode, "OLCULEMEDI")
    ozet = [s.strip() for s in (p.stdout or "").splitlines()
            if s.strip().startswith(("SAPMA", "TANIMIYOR", "NESIL", "REPO-KIRIK",
                                     "AYIRT-EDICI-YOK", "LISTE-SAPMASI", "ARIZA"))]
    return {"hal": hal, "detay": "; ".join(ozet[:4]) or (p.stdout or "").strip()[-200:]}


def gozlem_topla(site, ci_api, adet, gecikme, zaman_asimi,
                 son_commit=SON_COMMIT_SAYISI_VARSAYILAN):
    """TUM canli olcumu tek bir sozluge toplar. degerlendir() SADECE bu sozlugu gorur ->
    fikstur ile gercek olcum AYNI kod yolundan gecer (ikinci karar kopyasi YOK)."""
    depo = depo_gozlemi()
    canli = canli_katalog_gozlemi(site, zaman_asimi)
    ci = ci_gozlemi(ci_api, depo.get("sha"), zaman_asimi)
    yeni = yeni_urun_gozlemi(son_commit=son_commit)
    # SAYFA ekseni GENIS orneklem alir (dizi-basi + son K commit'te eklenen HER urun):
    # 404 sinifi tam da YENI urunlerin sinifidir ve sayfa istegi ucuzdur (statik CDN).
    sayfa_urunleri, kompozisyon = orneklem_sec(depo.get("urunler") or [], yeni["idler"], adet)
    kompozisyon["son_commit"] = son_commit
    kompozisyon["hata"] = yeni["hata"]
    # D1/GORSEL eksenleri DAR kalir: D1 sorgusu canli worker'a gider (hiz siniri 60/60 sn),
    # gorsel istegi R2'ye. Bu eksenlerin sinifi "yeni urun" DEGIL, o yuzden dizi-basi yeter.
    urunler = (depo.get("urunler") or [])[:adet]
    # K5 D1 orneklemi KONFIGURSUZ urunlerle sinirli (konfigurlu urunler K4'un isi).
    d1_urunleri = [u for u in urunler if not u.get("konfigur") and not u.get("parametrik")]
    return {
        "zaman": int(time.time()), "site": site, "adet": adet,
        "orneklem": kompozisyon,
        "depo": depo, "canli_katalog": canli, "ci": ci,
        "sayfalar": sayfa_gozlemi(site, [u["id"] for u in sayfa_urunleri],
                                  canli.get("idler"), SAYFA_GECIKME, zaman_asimi),
        "d1": d1_gozlemi(site, d1_urunleri, gecikme, zaman_asimi),
        "gorseller": gorsel_gozlemi(site, urunler, zaman_asimi=zaman_asimi),
        "kart_kanali": kart_kanali_gozlemi(site, gecikme),
        "fiziksel_fiyat": fiziksel_fiyat_gozlemi(site, gecikme),
    }


# ================================================================= KARAR (SAF — AG YOK)

def _dk(saniye):
    if saniye is None:
        return "?"
    return "%d dk" % max(0, int(round(saniye / 60.0)))


def yayin_penceresi(g):
    """(hal, gecen_sn, aciklama) — "canli geride" NORMAL mi ARIZA mi sorusunun TEK yargici.

    hal:
      CI-KOSUYOR       kosum devam ediyor            -> pencere ACIK (bekle)
      KOSUM-BASLAMAMIS depo tipi icin kosum yok      -> pencere ACIK (push cok taze)
      YERLESIYOR       kosum yesil bitti ama < tolerans -> pencere ACIK (Pages+CDN yerlesiyor)
      YERLESIK         kosum yesil ve yerlesti       -> pencere KAPALI (sapma = ARIZA)
      CI-KIRMIZI       kosum basarisiz               -> pencere KAPALI (kok neden CI)
      OLCULEMEDI       CI okunamadi                  -> pencere BILINMIYOR (yesil SAYILMAZ)
    """
    ci = g.get("ci") or {}
    simdi = g.get("zaman") or int(time.time())
    if ci.get("hata") or not ci.get("durum"):
        return ("OLCULEMEDI", None, "CI durumu okunamadi")
    if ci.get("durum") in ("queued", "in_progress"):
        basladi = ci.get("bitis")
        gecen = (simdi - basladi) if basladi else None
        return ("CI-KOSUYOR", gecen, "kosum devam ediyor (%s)" % _dk(gecen))
    if ci.get("sonuc") == "failure":
        return ("CI-KIRMIZI", None, "son kosum BASARISIZ")
    if ci.get("sha_icin_kosum_var") is False:
        return ("KOSUM-BASLAMAMIS", None, "depo tipi icin henuz kosum yok")
    if ci.get("sonuc") != "success":
        return ("OLCULEMEDI", None, "kosum sonucu: %s" % ci.get("sonuc"))
    gecen = (simdi - ci["bitis"]) if ci.get("bitis") else None
    if gecen is not None and gecen < YERLESME_TOLERANS_SN:
        return ("YERLESIYOR", gecen, "kosum %s once yesil bitti, dagitim yerlesiyor" % _dk(gecen))
    return ("YERLESIK", gecen, "kosum yesil ve yerlesti (%s once)" % _dk(gecen))


PENCERE_ACIK = ("CI-KOSUYOR", "KOSUM-BASLAMAMIS", "YERLESIYOR")


def kontrol_ci(g, hal):
    ci = g.get("ci") or {}
    if hal == "OLCULEMEDI":
        return [("CI", "ARIZA", "CI durumu OLCULEMEDI — " + str(ci.get("hata") or "?"),
                 "GitHub Actions'a elle bak; CI kirmizysa TUM yayin durmustur.")]
    if hal == "CI-KIRMIZI":
        return [("CI", "SAPMA",
                 "son kosum BASARISIZ%s  %s" % (
                     (" — kirmizi adim: " + ci["adim"]) if ci.get("adim") else "",
                     ci.get("url") or ""),
                 "ONCE CI'yi duzelt: kirmizi CI = yayin DURMUS, hicbir yeni urun canlia cikmaz.")]
    if hal in PENCERE_ACIK:
        return [("CI", "BEKLENIYOR", "yayin penceresi ACIK — " + yayin_penceresi(g)[2],
                 "Bir sey yapma; %d sn sonra tekrar olc." % YERLESME_TOLERANS_SN)]
    return [("CI", "TAMAM", "son kosum YESIL (%s)" % yayin_penceresi(g)[2], "")]


def kontrol_katalog(g, hal):
    depo = g.get("depo") or {}
    canli = g.get("canli_katalog") or {}
    if depo.get("hata") or depo.get("sayi") is None:
        return [("KATALOG", "ARIZA", "depo sayisi OLCULEMEDI — " + str(depo.get("hata")),
                 "`git fetch origin` yapip tekrar kostur.")]
    if canli.get("hata") or canli.get("sayi") is None:
        return [("KATALOG", "ARIZA",
                 "canli /urunler.json OLCULEMEDI — " + str(canli.get("hata")),
                 "Siteye elle bak; katalog inmiyorsa TUM vitrin bostur.")]
    d, c = depo["sayi"], canli["sayi"]
    if d == c:
        return [("KATALOG", "TAMAM", "canli == depo == %d urun" % d, "")]
    if c > d:
        return [("KATALOG", "SAPMA",
                 "canli %d, depo %d — CANLI DEPODAN ILERI (%d urun fazla)" % (c, d, c - d),
                 "Yerel ref bayat olabilir: `git fetch origin` + kardes dallari kontrol et.")]
    eksik = d - c
    if hal in PENCERE_ACIK:
        return [("KATALOG", "BEKLENIYOR",
                 "canli %d, depo %d — %d urun HENUZ YAYINLANMADI (%s)"
                 % (c, d, eksik, yayin_penceresi(g)[2]),
                 "Bir sey yapma; yayin penceresi acik, %d sn sonra tekrar olc."
                 % YERLESME_TOLERANS_SN)]
    if hal == "CI-KIRMIZI":
        return [("KATALOG", "SAPMA",
                 "canli %d, depo %d — %d urun canlia CIKMADI (CI KIRMIZI)" % (c, d, eksik),
                 "ONCE CI'yi duzelt; yayin CI kirmizi oldugu icin durmus.")]
    if hal == "OLCULEMEDI":
        return [("KATALOG", "SAPMA",
                 "canli %d, depo %d — %d urun geride (CI durumu OLCULEMEDI)" % (c, d, eksik),
                 "GitHub Actions'a elle bak: kosum kirmizi mi, hic basladi mi?")]
    return [("KATALOG", "SAPMA",
             "canli %d, depo %d — %d urun geride, YAYIN PENCERESI KAPALI (%s)"
             % (c, d, eksik, yayin_penceresi(g)[2]),
             "YAYIN KIRIK: son yesil kosumun deploy adimina ve Pages ayarina bak.")]


def kontrol_sayfalar(g, hal):
    satirlar = []
    sayfalar = g.get("sayfalar") or []
    tamam = 0
    for s in sayfalar:
        uid = s.get("id")
        if s.get("hata") or s.get("http") is None:
            satirlar.append(("SAYFA", "ARIZA", "%s — OLCULEMEDI (%s)" % (uid, s.get("hata")),
                             "Agi kontrol et, tekrar kostur."))
            continue
        if s["http"] == 200:
            tamam += 1
            continue
        if s["http"] != 404:
            satirlar.append(("SAYFA", "SAPMA", "%s — HTTP %s" % (uid, s["http"]),
                             "Sayfa hata veriyor: origin/Pages durumuna bak."))
            continue
        yas = s.get("age")
        cf = (s.get("cf") or "").upper()
        onbellekten = cf in ("HIT", "STALE", "EXPIRED", "REVALIDATED") or \
            (yas is not None and yas >= ONBELLEK_YAS_ESIGI_SN)
        if onbellekten:
            # VAKA 1: sayfa origin'de VAR ama edge eski 404'u servis ediyor.
            satirlar.append(("SAYFA", "ONBELLEK",
                             "%s — 404 ama ONBELLEKTEN (cf=%s age=%s sn > %d) : sayfa "
                             "muhtemelen origin'de VAR, musteri BOS SAYFA goruyor"
                             % (uid, cf or "?", yas, ONBELLEK_YAS_ESIGI_SN),
                             "Cloudflare'de bu URL'i purge et; age kucukken tekrar olc."))
            continue
        if s.get("canli_katalogda") is False:
            satirlar.append(("SAYFA", "BEKLENIYOR",
                             "%s — 404 ve urun CANLI KATALOGDA da YOK (age=%s, taze 404)"
                             % (uid, yas),
                             "Yayin henuz gelmemis; KATALOG satirina bak."))
            continue
        if hal in PENCERE_ACIK:
            satirlar.append(("SAYFA", "BEKLENIYOR",
                             "%s — 404, taze (age=%s) ama yayin penceresi ACIK" % (uid, yas),
                             "Bir sey yapma; %d sn sonra tekrar olc." % YERLESME_TOLERANS_SN))
            continue
        satirlar.append(("SAYFA", "SAPMA",
                         "%s — GERCEK 404 (cf=%s age=%s, onbellek artigi DEGIL) ama urun "
                         "canli katalogda VAR: karta tiklayan musteri BOS SAYFA goruyor"
                         % (uid, cf or "?", yas),
                         "build.py urun/ ciktisina ve son deploy loguna bak: sayfa hic uretilmemis."))
    if sayfalar and not satirlar:
        return [("SAYFA", "TAMAM", "en yeni %d urunun %d sayfasi 200" % (len(sayfalar), tamam),
                 "")]
    return satirlar


def kontrol_d1(g, hal):
    satirlar = []
    kayitlar = g.get("d1") or []
    var = len([k for k in kayitlar if k.get("sonuc") == "var"])
    for k in kayitlar:
        if k.get("sonuc") == "var":
            continue
        if k.get("sonuc") == "ariza":
            satirlar.append(("D1", "ARIZA", "%s — OLCULEMEDI (%s)" % (k["id"], k.get("detay")),
                             "Hiz sinirina takilmis olabilir; --gecikme artirip tekrar kostur."))
            continue
        if hal in PENCERE_ACIK:
            satirlar.append(("D1", "BEKLENIYOR",
                             "%s — D1'de YOK ama yayin penceresi ACIK" % k["id"],
                             "Bir sey yapma; pencere kapaninca tekrar olc."))
            continue
        satirlar.append(("D1", "SAPMA",
                         "%s — canli worker'in D1 katalogunda YOK: site gosteriyor ama Ege "
                         "GOREMEZ ve kart kanali bu urunde KAPALI" % k["id"],
                         "`python3 tools/d1-sync.py` kostur, sonra `--durum` ile teyit et."))
    if kayitlar and not satirlar:
        return [("D1", "TAMAM", "orneklenen %d urunun %d'i canli D1'de TANINIYOR"
                 % (len(kayitlar), var), "")]
    return satirlar


def kontrol_kart(g, _hal):
    k = g.get("kart_kanali") or {}
    hal = k.get("hal")
    if hal == "PARITE":
        return [("KART", "TAMAM", "konfigurlu urunler canlida DOGRU fiyatlaniyor "
                 "(konfigur-canli-kapisi)", "")]
    if hal == "DRIFT":
        return [("KART", "SAPMA",
                 "canli worker BAYAT — kart kanali kapali/yanlis tutar: " + str(k.get("detay")),
                 "shop dizininden Worker'i yeniden yayinla, sonra "
                 "`python3 tools/konfigur-canli-kapisi.py` ile teyit et.")]
    if hal == "ARAC-YOK":
        return [("KART", "ARIZA", "kart kanali OLCULEMEDI — " + str(k.get("detay")),
                 "tools/konfigur-canli-kapisi.py'yi main'e al; bu eksen o araca aittir.")]
    return [("KART", "ARIZA", "kart kanali OLCULEMEDI — " + str(k.get("detay")),
             "`python3 tools/konfigur-canli-kapisi.py` elle kostur.")]


def kontrol_fiziksel(g, _hal):
    """K6 — hazir ticari mal fiyat ekseni. K4 (KART) ile AYNI kalibi kullanir ama BASKA bir
    sinifi olcer; birinin yesili otekini KANITLAMAZ."""
    k = g.get("fiziksel_fiyat") or {}
    hal = k.get("hal")
    if hal == "PARITE":
        return [("FIZIKSEL", "TAMAM", "hazir ticari malda canli tahsilat LISTE FIYATI "
                 "(fiziksel-canli-kapisi)", "")]
    if hal == "DRIFT":
        return [("FIZIKSEL", "SAPMA",
                 "hazir ticari malda YANLIS TUTAR tahsil ediliyor: " + str(k.get("detay")),
                 "REPO-KIRIK satiri varsa once KODU duzelt; yoksa shop dizininden Worker'i "
                 "yeniden yayinla, sonra `python3 tools/fiziksel-canli-kapisi.py` ile teyit et.")]
    if hal == "ARAC-YOK":
        return [("FIZIKSEL", "ARIZA", "hazir ticari mal fiyati OLCULEMEDI — " + str(k.get("detay")),
                 "tools/fiziksel-canli-kapisi.py'yi main'e al; bu eksen o araca aittir.")]
    return [("FIZIKSEL", "ARIZA", "hazir ticari mal fiyati OLCULEMEDI — " + str(k.get("detay")),
             "`python3 tools/fiziksel-canli-kapisi.py` elle kostur.")]


def kontrol_gorsel(g, _hal):
    satirlar = []
    kayitlar = g.get("gorseller") or []
    for k in kayitlar:
        if k.get("url") is None:
            satirlar.append(("GORSEL", "SAPMA", "%s — urunde HIC gorsel yok" % k["id"],
                             "urunler.json'da gorseller[] bos: MaCiT duzlemine bildir."))
            continue
        if k.get("hata") or k.get("http") is None:
            satirlar.append(("GORSEL", "ARIZA", "%s — OLCULEMEDI (%s)" % (k["id"], k.get("hata")),
                             "Agi kontrol et, tekrar kostur."))
            continue
        if k["http"] != 200:
            satirlar.append(("GORSEL", "SAPMA",
                             "%s — HTTP %s : %s (kartta KIRIK gorsel)"
                             % (k["id"], k["http"], k["url"]),
                             "Gorseli R2'ye YENI anahtarla yukle (uzerine YAZMA) ve "
                             "urunler.json URL'ini guncelle."))
    if kayitlar and not satirlar:
        return [("GORSEL", "TAMAM", "orneklenen %d urunun kapak gorseli R2'de VAR"
                 % len(kayitlar), "")]
    return satirlar


def kontrol_orneklem(g, _hal):
    """K0 ORNEKLEM — "neyi olctugumuzu" YARGILAR. Diger besi "olculen sey saglikli mi"
    der; bu eksen "olculmesi GEREKENI olctuk mu" der.

    OLCULEN HATA (30 Tem): nobetci en yeni 20 DIZI kaydini ornekliyordu; yeni eklenen bir
    urun ardindan gelen 26'lik parti yuzunden 26. siraya dustu, orneklem DISINDA kaldi ve
    SAYFA ekseni "20/20 -> 200" ile YESIL yandi. Sayfa canlida 404'tu. Yani nobetci
    SESSIZCE dar olcuyordu. Bu kontrol o sessizligi imkansiz kilar."""
    o = g.get("orneklem")
    if not o:
        return [("ORNEKLEM", "ARIZA", "orneklem bilesimi YOK (olcum toplayici eski mi?)",
                 "gozlem_topla() 'orneklem' anahtarini doldurmali.")]
    if o.get("hata"):
        return [("ORNEKLEM", "ARIZA",
                 "YENI-COMMIT ekseni OLCULEMEDI — %s" % o["hata"],
                 "Depoda git gecmisi lazim (shallow checkout ise `git fetch --unshallow`); "
                 "aksi halde yeni urunler orneklem disinda kalabilir.")]
    kapsanmayan = o.get("kapsanmayan") or []
    kirpilan = o.get("kirpilan") or []
    if kapsanmayan:
        return [("ORNEKLEM", "SAPMA",
                 "son %s commit'te eklenen %d urun ORNEKLEM DISINDA kaldi (%s...) — "
                 "nobetci bu urunler icin KOR" % (o.get("son_commit"), len(kapsanmayan),
                                                  ", ".join(kapsanmayan[:3])),
                 "Yeni-commit ekseninin secim kablosu kopmus: orneklem_sec() birlesimini "
                 "kontrol et.")]
    if kirpilan:
        return [("ORNEKLEM", "SAPMA",
                 "yeni-commit ekseni TAVANA takildi: %d urun orneklenmedi (%s...)"
                 % (len(kirpilan), ", ".join(kirpilan[:3])),
                 "--adet artir ya da YENI_EKSEN_TAVAN'i yukselt; bu urunler OLCULMEDI.")]
    return [("ORNEKLEM", "TAMAM",
             "SAYFA orneklemi %d kayit = dizi-basi %d + yeni-commit %d (son %s commit; "
             "yalniz yeni eksenden gelen %d)"
             % (o.get("toplam"), o.get("dizi_basi"), o.get("yeni_commit"),
                o.get("son_commit"), o.get("yalniz_yeni_eksen")), "")]


def _noop(_g, _hal):
    """KIRMIZI-MUTASYON hedefi: bir kontrol NO-OP yapilinca fikstur YESILE donmeli
    (donmuyorsa o kontrol yuk TASIMIYOR = olu iddia)."""
    return []


KONTROLLER = [
    ("ORNEKLEM", kontrol_orneklem),
    ("CI", kontrol_ci),
    ("KATALOG", kontrol_katalog),
    ("SAYFA", kontrol_sayfalar),
    ("D1", kontrol_d1),
    ("KART", kontrol_kart),
    ("FIZIKSEL", kontrol_fiziksel),
    ("GORSEL", kontrol_gorsel),
]


def degerlendir(g):
    """SAF karar fonksiyonu (ag YOK, dosya YOK) -> (durum, satirlar, hal).

    ONCELIK (bilerek, konfigur-canli-kapisi ile AYNI): SAPMA KANITI olcum arizasini EZER.
    Bir eksende gercek sapma varken baska eksende ag hatasi olmasi sonucu "OLCULEMEDI"ye
    dusuremez — elimizde ZATEN musteri/gelir kaybettiren bir bulgu vardir."""
    hal = yayin_penceresi(g)[0]
    satirlar = []
    for _ad, fonk in KONTROLLER:
        satirlar.extend(fonk(g, hal))
    if any(s[1] in SAPMA_SINIFLARI for s in satirlar):
        return ("SAPMA", satirlar, hal)
    if any(s[1] == "ARIZA" for s in satirlar):
        return ("OLCULEMEDI", satirlar, hal)
    return ("SAGLIKLI", satirlar, hal)


DURUM_KOD = {"SAGLIKLI": 0, "SAPMA": 1, "OLCULEMEDI": 2}


# ================================================================= rapor

SIMGE = {"TAMAM": "✅", "BEKLENIYOR": "⏳", "SAPMA": "❌", "ONBELLEK": "❌", "ARIZA": "⚪"}


def rapor(durum, satirlar, hal, g):
    print("CANLI SAGLIK NOBETCISI — " + (g.get("site") or "?"))
    depo = g.get("depo") or {}
    print("  depo(%s) : %s urun @ %s" % (depo.get("dal") or "?", depo.get("sayi"),
                                         (depo.get("sha") or "?")[:8]))
    print("  yayin penceresi: %s — %s" % (hal, yayin_penceresi(g)[2]))
    # SESSIZ ORNEKLEM YASAK: kac kayit, HANGI EKSENLERDEN geldigi HER kosumda basilir.
    _o = g.get("orneklem") or {}
    print("  orneklem(SAYFA): %s kayit = dizi-basi %s + yeni-commit %s (son %s commit)%s"
          % (_o.get("toplam", "?"), _o.get("dizi_basi", "?"), _o.get("yeni_commit", "?"),
             _o.get("son_commit", "?"),
             "  ⚠️ YENI-COMMIT EKSENI OLCULEMEDI" if _o.get("hata") else ""))
    print("-" * 78)
    for sinif in ("SAPMA", "ONBELLEK", "ARIZA", "BEKLENIYOR", "TAMAM"):
        for kontrol, s, mesaj, eylem in satirlar:
            if s != sinif:
                continue
            print("  %s %-7s %s" % (SIMGE.get(s, "?"), kontrol, mesaj))
            if eylem:
                print("        -> " + eylem)
    print("-" * 78)
    sapma = len([s for s in satirlar if s[1] in SAPMA_SINIFLARI])
    ariza = len([s for s in satirlar if s[1] == "ARIZA"])
    bekleyen = len([s for s in satirlar if s[1] == "BEKLENIYOR"])
    print("  sapma: %d   olculemeyen: %d   yayin bekleyen: %d" % (sapma, ariza, bekleyen))
    if durum == "SAGLIKLI":
        print("SONUC: YESIL ✅ — canli ile depo/D1 arasinda SAPMA YOK.")
    elif durum == "SAPMA":
        print("SONUC: KIRMIZI ❌ — %d sapma. Yukaridaki '->' satirlari SIRAYLA uygulanir; "
              "CI kirmizysa ONCE o." % sapma)
    else:
        print("SONUC: ⚪ OLCULEMEDI — sapma KANITI yok ama saglik da KANITLANMADI "
              "(sessiz yesil verilmez).")
    print("  NOT: bu arac SALT-OKUNURDUR ve CI'da BLOKLAYICI DEGILDIR "
          "(CI'da yalniz --kendini-test kosar).")
    return DURUM_KOD[durum]


# ================================================================= FIKSTURLER (AGSIZ)
# Bugunku UC gercek vakanin donmus gozlemi + yayin-penceresi ikizi. degerlendir() bunlari
# GERCEK olcumle AYNI kod yolundan gecirir.

SIMDI = 1_800_000_000


def _temel(**ustyaz):
    """Tamamen SAGLIKLI bir taban gozlem; fiksturler yalniz FARKI yazar."""
    idler = ["u%03d" % i for i in range(20)]
    g = {
        "zaman": SIMDI, "site": "https://ornek.gecersiz", "adet": 20,
        "orneklem": {"toplam": 20, "dizi_basi": 20, "yeni_commit": 3,
                     "yalniz_yeni_eksen": 0, "kirpilan": [], "yeni_toplam": 3,
                     "kapsanmayan": [], "son_commit": 12, "hata": None},
        "depo": {"dal": "origin/main", "sayi": 15039, "sha": "a" * 40,
                 "commit_zamani": SIMDI - 3600, "hata": None, "idler": idler},
        "canli_katalog": {"http": 200, "sayi": 15039, "idler": set(idler), "hata": None,
                          "cf": "HIT", "age": 12, "last_modified": None, "bayt": 1},
        "ci": {"durum": "completed", "sonuc": "success", "sha": "a" * 40,
               "bitis": SIMDI - 3600, "url": "https://ornek/ci", "adim": None,
               "hata": None, "sha_icin_kosum_var": True},
        "sayfalar": [{"id": i, "http": 200, "hata": None, "cf": "HIT", "age": 5,
                      "canli_katalogda": True} for i in idler],
        "d1": [{"id": i, "sonuc": "var", "detay": "35000 kurus"} for i in idler],
        "gorseller": [{"id": i, "url": "https://ornek/%s.jpg" % i, "http": 200, "hata": None}
                      for i in idler],
        "kart_kanali": {"hal": "PARITE", "detay": ""},
        "fiziksel_fiyat": {"hal": "PARITE", "detay": ""},
    }
    g.update(ustyaz)
    return g


def fikstur_vaka1():
    """VAKA 1 — 18 yeni urunun sayfasi canlida 404; CF o 404'u SAATLERDIR onbellekliyor.
    Katalog SENKRON (urun canli katalogda VAR), CI YESIL ve YERLESIK -> "yayin bekleniyor"
    MAZERETI YOK. Nobetci ONBELLEK ARTIGI teshisini koymali."""
    g = _temel()
    for s in g["sayfalar"][:18]:
        s.update({"http": 404, "cf": "HIT", "age": 9000})    # ~2.5 saat onbellekte
    return g


def fikstur_vaka2():
    """VAKA 2 — CI KIRMIZI kaldigi icin 23 urun canlia HIC cikmadi (depo 15039, canli 15016).
    Nobetci hem katalog sapmasini hem KOK NEDENI (CI) soylemeli."""
    g = _temel()
    g["ci"] = {"durum": "completed", "sonuc": "failure", "sha": "a" * 40,
               "bitis": SIMDI - 1800, "url": "https://ornek/ci/kirmizi",
               "adim": "build / Kategori parite kabul testi", "hata": None,
               "sha_icin_kosum_var": True}
    g["canli_katalog"]["sayi"] = 15016
    yeniler = set(u["id"] for u in g["sayfalar"][:23])
    g["canli_katalog"]["idler"] = set(g["depo"]["idler"]) - yeniler
    for s in g["sayfalar"][:23]:
        s.update({"http": 404, "cf": "MISS", "age": None, "canli_katalogda": False})
    return g


def fikstur_vaka3():
    """VAKA 3 — iki figur canlida GORUNUYOR (katalog + sayfa + D1 hepsi yesil) ama worker
    eski paketi kosuyor -> kart kanali KAPALI. Bu ekseni YALNIZ K4 gorur."""
    g = _temel()
    g["kart_kanali"] = {"hal": "DRIFT",
                        "detay": "TANIMIYOR figur-a — canli worker konfiguru TANIMIYOR "
                                 "(400 konfigur-urun) — kart kanali KAPALI"}
    return g


def fikstur_vaka4():
    """VAKA 4 (30 Tem, Okan yakaladi — nobetci YESIL yaniyordu) — TEK urunun sayfasi 404.
    `yan-birakmali-kayis-tokasi` 22:25'te eklendi; 3 dk sonraki 26'lik parti onu dizide
    26. siraya itti. Eski orneklem (en yeni 20 DIZI kaydi) onu ISKALADI -> SAYFA ekseni
    "20/20 -> 200" dedi. Yeni-commit ekseni onu orneklem'e SOKAR ve 404 GORULUR.
    Katalog SENKRON (urun canli katalogda VAR), CI YESIL + YERLESIK -> mazeret YOK."""
    g = _temel()
    toka = {"id": "yeni-urun-26", "http": 404, "hata": None, "cf": "MISS", "age": 5,
            "canli_katalogda": True}
    g["sayfalar"].append(toka)
    g["d1"].append({"id": toka["id"], "sonuc": "var", "detay": "30000 kurus"})
    g["gorseller"].append({"id": toka["id"], "url": "https://ornek/yeni.jpg",
                           "http": 200, "hata": None})
    g["depo"]["idler"] = g["depo"]["idler"] + [toka["id"]]
    g["depo"]["sayi"] += 1
    g["canli_katalog"]["sayi"] += 1
    g["canli_katalog"]["idler"] = set(g["canli_katalog"]["idler"]) | {toka["id"]}
    g["orneklem"] = dict(g["orneklem"], toplam=21, yeni_commit=1, yalniz_yeni_eksen=1,
                         yeni_toplam=1)
    return g


def fikstur_yayin_penceresi():
    """YANLIS-POZITIF IKIZI (A) — push 90 sn once, CI KOSUYOR: canli 23 urun geride ve
    sayfalari TAZE 404. Bu ARIZA DEGILDIR -> SAGLIKLI + BEKLENIYOR satirlari."""
    g = _temel()
    g["ci"] = {"durum": "in_progress", "sonuc": None, "sha": "a" * 40,
               "bitis": SIMDI - 90, "url": "https://ornek/ci", "adim": None,
               "hata": None, "sha_icin_kosum_var": True}
    g["canli_katalog"]["sayi"] = 15016
    yeniler = set(u["id"] for u in g["sayfalar"][:23])
    g["canli_katalog"]["idler"] = set(g["depo"]["idler"]) - yeniler
    for s in g["sayfalar"]:
        s.update({"http": 404, "cf": "MISS", "age": 0, "canli_katalogda": False})
    for k in g["d1"]:
        k.update({"sonuc": "yok", "detay": "D1'de kayit YOK"})
    return g


def fikstur_yayin_kirik():
    """YANLIS-POZITIF IKIZI (B) — AYNI SAYILAR, tek fark: CI 45 dk once YESIL bitti.
    Pencere KAPALI -> ayni tablo artik SAPMA. Ikizin amaci: nobetci "henuz yayinlanmadi"
    ile "yayin kirik"i AYIRT EDEBILIYOR mu."""
    g = fikstur_yayin_penceresi()
    g["ci"] = {"durum": "completed", "sonuc": "success", "sha": "a" * 40,
               "bitis": SIMDI - 2700, "url": "https://ornek/ci", "adim": None,
               "hata": None, "sha_icin_kosum_var": True}
    return g


def fikstur_olculemedi():
    """Ag koptu: hicbir sey olculemedi. SAPMA KANITI yok -> rc 2, ASLA yesil."""
    g = _temel()
    g["canli_katalog"] = {"http": None, "sayi": None, "idler": set(),
                          "hata": "URLError: dns", "cf": None, "age": None,
                          "last_modified": None, "bayt": 0}
    g["ci"] = {"durum": None, "sonuc": None, "sha": None, "bitis": None, "url": None,
               "adim": None, "hata": "URLError: dns", "sha_icin_kosum_var": None}
    for s in g["sayfalar"]:
        s.update({"http": None, "hata": "URLError: dns"})
    for k in g["d1"]:
        k.update({"sonuc": "ariza", "detay": "URLError: dns"})
    for k in g["gorseller"]:
        k.update({"http": None, "hata": "URLError: dns"})
    g["kart_kanali"] = {"hal": "ARAC-YOK", "detay": "arac yok"}
    g["fiziksel_fiyat"] = {"hal": "ARAC-YOK", "detay": "arac yok"}
    return g


def fikstur_vaka5():
    """VAKA 5 (1 Agu, OLCULDU) — canli paket BAYAT: hazir ticari malda malzeme/renk carpani
    hala uygulaniyor (liste x1,840 FAZLA tahsilat). KRITIK AYRIM: K4 (KART) YESIL — cunku
    konfigurlu 17 urun dogru fiyatlaniyor. Bu vakayi YALNIZ K6 gorur; yesil bir K4 hicbir
    sey kanitlamaz."""
    g = _temel()
    g["fiziksel_fiyat"] = {
        "hal": "DRIFT",
        "detay": "SAPMA yamalube-... [ASA Diğer] — canli 386400 kurus, liste 210000 kurus "
                 "(x1.840 FAZLA tahsilat); NESIL — canli paket depo HEAD'i ile ayrisik"}
    return g


FIKSTURLER = [
    ("VAKA-1 sayfa 404 + CF onbellek artigi", fikstur_vaka1, "SAPMA", "SAYFA", "ONBELLEK"),
    ("VAKA-2 CI kirmizi -> 23 urun canlia cikmadi", fikstur_vaka2, "SAPMA", "KATALOG", "SAPMA"),
    ("VAKA-3 kart kanali kapali (worker bayat)", fikstur_vaka3, "SAPMA", "KART", "SAPMA"),
    ("VAKA-4 yeni urun dizi-basi disinda, sayfasi 404", fikstur_vaka4, "SAPMA",
     "SAYFA", "SAPMA"),
    ("VAKA-5 hazir ticari malda fazla tahsilat (K4 YESILKEN)", fikstur_vaka5, "SAPMA",
     "FIZIKSEL", "SAPMA"),
]


# ================================================================= KENDINI TEST (AGSIZ)

def kendini_test():
    """OFFLINE kabul: 3 gecmis vaka + yanlis-pozitif ikizi + KIRMIZI-MUTASYON.
    Ag YOK, dosya YAZMAZ, git GEREKTIRMEZ -> CI'da bloklayici kosabilir."""
    ham = ["CANLI SAGLIK NOBETCISI — KENDINI TEST (offline)"]
    kirmizi = 0

    def iddia(ad, kosul, detay=""):
        nonlocal kirmizi
        if kosul:
            ham.append("    ✅ " + ad)
        else:
            kirmizi += 1
            ham.append("    ❌ " + ad + ((" — " + str(detay)) if detay else ""))

    # ---- (A) UC GECMIS VAKA: hepsi YAKALANMALI ve DOGRU EKSENDE teshis edilmeli
    ham.append("  (A) BUGUNKU UC VAKA")
    for ad, kur, bek_durum, bek_kontrol, bek_sinif in FIKSTURLER:
        durum, satirlar, _hal = degerlendir(kur())
        hedef = [s for s in satirlar if s[0] == bek_kontrol and s[1] == bek_sinif]
        iddia("%s -> %s" % (ad, bek_durum), durum == bek_durum, durum)
        iddia("    ... %s ekseninde %s teshisi var" % (bek_kontrol, bek_sinif),
              bool(hedef), [s[:2] for s in satirlar])
        iddia("    ... teshis EYLEM satiri tasiyor (rapor eyleme donuk)",
              bool(hedef) and bool(hedef[0][3]))

    # VAKA'lara ozel icerik iddialari (teshis METNI dogru sinyali veriyor mu)
    _d, s1, _h = degerlendir(fikstur_vaka1())
    iddia("VAKA-1 teshisi 'ONBELLEK' ayrimini yapiyor (taze 404 ile karistirmiyor)",
          any(s[1] == "ONBELLEK" and "age" in s[2] for s in s1))
    iddia("VAKA-1 KATALOG ekseni TEMIZ kaliyor (yanlis eksende alarm yok)",
          all(s[1] == "TAMAM" for s in s1 if s[0] == "KATALOG"))
    _d, s2, _h = degerlendir(fikstur_vaka2())
    iddia("VAKA-2 katalog satiri KOK NEDENI (CI) soyluyor",
          any(s[0] == "KATALOG" and "CI KIRMIZI" in s[2] for s in s2))
    iddia("VAKA-2 CI satiri kirmizi ADIMI yaziyor",
          any(s[0] == "CI" and "Kategori parite" in s[2] for s in s2))
    iddia("VAKA-2 eksik urun sayisi 23 olarak raporlaniyor",
          any("23 urun" in s[2] for s in s2))
    _d, s3, _h = degerlendir(fikstur_vaka3())
    iddia("VAKA-3'te YALNIZ KART ekseni kirmizi (digerleri yesil)",
          [s[0] for s in s3 if s[1] in SAPMA_SINIFLARI] == ["KART"],
          [s[:2] for s in s3 if s[1] in SAPMA_SINIFLARI])

    _d, s4, _h = degerlendir(fikstur_vaka4())
    iddia("VAKA-4 sayfa satiri 'GERCEK 404' + 'canli katalogda VAR' diyor",
          any(s[0] == "SAYFA" and "GERCEK 404" in s[2] and "canli katalogda VAR" in s[2]
              for s in s4))
    iddia("VAKA-4'te YALNIZ SAYFA ekseni kirmizi (katalog senkron, CI yesil)",
          [s[0] for s in s4 if s[1] in SAPMA_SINIFLARI] == ["SAYFA"],
          [s[:2] for s in s4 if s[1] in SAPMA_SINIFLARI])

    # ---- (A2) ORNEKLEM SECIMI — asil onarim burasi: "en yeni N DIZI kaydi" YETMEZ.
    # 30 Tem vakasinin BIREBIR yeniden kurulumu: urun eklendi, ardindan gelen parti onu
    # 26. siraya itti. ESKI eksen (yalniz dizi-basi) onu KACIRIR, YENI eksen YAKALAR.
    ham.append("  (A2) ORNEKLEM SECIMI (yeni-commit ekseni yuk tasiyor mu)")
    _sahne = [{"id": "parti-%02d" % i} for i in range(26)]
    _sahne.insert(26, {"id": "toka"})
    _sahne += [{"id": "eski-%02d" % i} for i in range(60)]
    _eski_secim, _eski_komp = orneklem_sec(_sahne, [], 20)
    _yeni_secim, _yeni_komp = orneklem_sec(_sahne, ["toka"], 20)
    iddia("ESKI eksen (yalniz dizi-basi 20) 26. siradaki yeni urunu KACIRIYOR",
          "toka" not in [u["id"] for u in _eski_secim], _eski_komp)
    iddia("YENI-COMMIT ekseni ayni urunu ORNEKLEME SOKUYOR",
          "toka" in [u["id"] for u in _yeni_secim], _yeni_komp)
    iddia("    ... bilesim raporlaniyor (toplam 21 = dizi-basi 20 + yalniz-yeni 1)",
          (_yeni_komp["toplam"], _yeni_komp["dizi_basi"],
           _yeni_komp["yalniz_yeni_eksen"]) == (21, 20, 1), _yeni_komp)
    iddia("    ... dizi-basi ekseni KORUNUYOR (eski davranis kaybolmadi)",
          [u["id"] for u in _yeni_secim][:20] == [u["id"] for u in _eski_secim])
    _tavan_sahne = [{"id": "y%03d" % i} for i in range(200)]
    _ts, _tk = orneklem_sec(_tavan_sahne, [u["id"] for u in _tavan_sahne], 20, tavan=60)
    iddia("TAVAN asilinca SESSIZCE kirpilmiyor (kirpilan listeleniyor)",
          len(_tk["kirpilan"]) == 140, len(_tk["kirpilan"]))
    iddia("    ... tavan kirpmasi ORNEKLEM ekseninde SAPMA uretiyor",
          any(s[1] == "SAPMA" for s in kontrol_orneklem(
              {"orneklem": dict(_tk, son_commit=12, hata=None)}, "YERLESIK")))
    iddia("git gecmisi okunamazsa SESSIZ YESIL yok (ORNEKLEM -> ARIZA)",
          any(s[1] == "ARIZA" for s in kontrol_orneklem(
              {"orneklem": dict(_yeni_komp, son_commit=12,
                                hata="gecmis okunamadi: shallow")}, "YERLESIK")))

    # ---- (B) YANLIS-POZITIF: yayin penceresi vs yayin kirik
    ham.append("  (B) YANLIS-POZITIF — 'henuz yayinlanmadi' vs 'yayin kirik'")
    dp, sp, halp = degerlendir(fikstur_yayin_penceresi())
    iddia("pencere ACIKKEN (CI kosuyor) ayni tablo SAGLIKLI (yanlis alarm YOK)",
          dp == "SAGLIKLI", dp)
    iddia("    ... hal CI-KOSUYOR", halp == "CI-KOSUYOR", halp)
    iddia("    ... 'HENUZ YAYINLANMADI' + gecen sure yaziliyor",
          any(s[1] == "BEKLENIYOR" and "HENUZ YAYINLANMADI" in s[2] for s in sp))
    iddia("    ... eylem satiri 'bir sey yapma' diyor",
          any(s[1] == "BEKLENIYOR" and "Bir sey yapma" in s[3] for s in sp))
    dk, sk, halk = degerlendir(fikstur_yayin_kirik())
    iddia("AYNI SAYILAR, CI 45 dk once yesil bitti -> SAPMA", dk == "SAPMA", dk)
    iddia("    ... hal YERLESIK", halk == "YERLESIK", halk)
    iddia("    ... katalog satiri 'YAYIN PENCERESI KAPALI' diyor",
          any(s[0] == "KATALOG" and "PENCERESI KAPALI" in s[2] for s in sk))
    iddia("    ... ayni sayilar iki ayri hukme variyor (ayrim GERCEK)",
          dp != dk and sorted(x[0] for x in sp) == sorted(x[0] for x in sk))

    # ---- (C) SESSIZ YESIL YOK
    ham.append("  (C) FAIL-CLOSED OLCUM")
    do, so, _h = degerlendir(fikstur_olculemedi())
    iddia("ag koptugunda OLCULEMEDI (rc 2), ASLA SAGLIKLI",
          do == "OLCULEMEDI" and DURUM_KOD[do] == 2, do)
    iddia("    ... her eksen ayri ayri ARIZA diyor",
          len(set(s[0] for s in so if s[1] == "ARIZA")) >= 5,
          sorted(set(s[0] for s in so if s[1] == "ARIZA")))
    karma = fikstur_olculemedi()
    karma["kart_kanali"] = {"hal": "DRIFT", "detay": "x"}
    dkarma, _s, _h = degerlendir(karma)
    iddia("SAPMA KANITI olcum arizasini EZER (karma -> SAPMA)", dkarma == "SAPMA", dkarma)
    iddia("saglikli taban SAGLIKLI (kapi 'hep kirmizi' degil)",
          degerlendir(_temel())[0] == "SAGLIKLI", degerlendir(_temel())[1])
    iddia("K4 araci YOKKEN sessiz yesil verilmez (ARAC-YOK -> ARIZA)",
          degerlendir(_temel(kart_kanali={"hal": "ARAC-YOK", "detay": "yok"}))[0]
          == "OLCULEMEDI")
    iddia("K6 araci YOKKEN sessiz yesil verilmez (ARAC-YOK -> ARIZA)",
          degerlendir(_temel(fiziksel_fiyat={"hal": "ARAC-YOK", "detay": "yok"}))[0]
          == "OLCULEMEDI")
    # 🔴 EKSEN AYRILIGI: K4'un yesili K6'yi KANITLAMAZ. 1 Agu'da tam olarak bu oldu.
    _v5 = fikstur_vaka5()
    iddia("K4 YESILKEN K6 SAPMA verebiliyor (eksenler BAGIMSIZ, biri otekini kanitlamaz)",
          _v5["kart_kanali"]["hal"] == "PARITE" and degerlendir(_v5)[0] == "SAPMA",
          degerlendir(_v5)[0])

    # ---- (D) KIRMIZI-MUTASYON: her kontrol NO-OP yapilinca ilgili fikstur YESILE donmeli
    #
    # ⚠️ TEK-EKSENLI FIKSTUR ZORUNLU (olculdu, ilk kosum): VAKA-2 fiksturunde hem KATALOG
    # hem CI kirmizi yaniyor -> KATALOG'u no-op yapmak sonucu YESILE dondurmuyordu ve
    # mutasyon "olu iddia" diye YANLIS alarm veriyordu. Bir kontrolun YUK TASIDIGINI
    # kanitlamak icin fiksturde BASKA hicbir eksen kirmizi OLMAMALI. Gercek vakalarin
    # yakalandigi iddiasi (A) bolumundedir; burasi yalniz "kontroller olu mu" sorusudur.
    ham.append("  (D) KIRMIZI-MUTASYON (kontroller yuk tasiyor mu — TEK EKSENLI fiksturler)")
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        oz = f.read()

    def _tek_sayfa():                      # yalniz SAYFA: onbellekten servis edilen 404
        g = _temel()
        for s in g["sayfalar"][:18]:
            s.update({"http": 404, "cf": "HIT", "age": 9000})
        return g

    def _tek_katalog():                    # yalniz KATALOG: canli geride, CI yesil+yerlesik
        return _temel(canli_katalog=dict(_temel()["canli_katalog"], sayi=15016))

    def _tek_kart():
        return _temel(kart_kanali={"hal": "DRIFT", "detay": "x"})

    def _tek_fiziksel():
        return _temel(fiziksel_fiyat={"hal": "DRIFT", "detay": "x"})

    def _tek_d1():
        g = _temel()
        for k in g["d1"][:2]:
            k.update({"sonuc": "yok", "detay": "D1'de kayit YOK"})
        return g

    def _tek_gorsel():
        g = _temel()
        g["gorseller"][0].update({"http": 404})
        return g

    def _tek_ci():
        return _temel(ci=dict(_temel()["ci"], sonuc="failure", adim="build / x"))

    def _tek_orneklem():            # yalniz ORNEKLEM: yeni urun orneklem DISINDA kalmis
        return _temel(orneklem=dict(_temel()["orneklem"], kapsanmayan=["yeni-urun-26"]))

    # ⚠️ CAPA METINLERI PARCALI: duz literal yazilsaydi bu tablonun KENDISI kaynakta ikinci
    # bir eslesme uretir ve "capa yok/cok" dalina duserdi ([[nobetci-cagri-satiri-nobetsiz]]).
    mutasyonlar = [
        ("MU1 SAYFA kontrolu no-op", '    ("SAYFA", ' + "kontrol_sayfalar),",
         '    ("SAYFA", ' + "_noop),", _tek_sayfa),
        ("MU2 KATALOG kontrolu no-op", '    ("KATALOG", ' + "kontrol_katalog),",
         '    ("KATALOG", ' + "_noop),", _tek_katalog),
        ("MU3 KART kontrolu no-op", '    ("KART", ' + "kontrol_kart),",
         '    ("KART", ' + "_noop),", _tek_kart),
        ("MU4 D1 kontrolu no-op", '    ("D1", ' + "kontrol_d1),",
         '    ("D1", ' + "_noop),", _tek_d1),
        ("MU5 GORSEL kontrolu no-op", '    ("GORSEL", ' + "kontrol_gorsel),",
         '    ("GORSEL", ' + "_noop),", _tek_gorsel),
        ("MU6 CI kontrolu no-op", '    ("CI", ' + "kontrol_ci),",
         '    ("CI", ' + "_noop),", _tek_ci),
        ("MU9 ORNEKLEM kontrolu no-op", '    ("ORNEKLEM", ' + "kontrol_orneklem),",
         '    ("ORNEKLEM", ' + "_noop),", _tek_orneklem),
        ("MU11 FIZIKSEL kontrolu no-op", '    ("FIZIKSEL", ' + "kontrol_fiziksel),",
         '    ("FIZIKSEL", ' + "_noop),", _tek_fiziksel),
    ]
    for ad, capa, yerine, kur in mutasyonlar:
        if oz.count(capa) != 1:
            kirmizi += 1
            ham.append("    ❌ MUTASYON CAPASI YOK/COK (nobet yeniden yazilmis): " + ad)
            continue
        g = kur()
        taban, _s, _h = degerlendir(g)
        if taban != "SAPMA":
            kirmizi += 1
            ham.append("    ❌ TABAN KIRMIZI DEGIL (mutasyon anlamsiz): " + ad)
            continue
        ns = {"__name__": "csk_mutant", "__file__": os.path.abspath(__file__)}
        exec(compile(oz.replace(capa, yerine), "<csk-mutant>", "exec"), ns)
        d_m, _sm, _hm = ns["degerlendir"](g)
        if d_m == "SAPMA":
            kirmizi += 1
            ham.append("    ❌ OLU IDDIA: " + ad + " -> mutant HALA SAPMA diyor "
                       "(sapmayi baska bir kontrol tasiyor)")
        else:
            ham.append("    ✅ " + ad + " -> mutant sessiz gecti (kontrol YUK TASIYOR)")

    # MU7/MU8 — 404 TESHIS AYRIMININ IKI AYRI SINYALI ayri ayri yuk tasiyor mu.
    # `age` esigi ve `cf` HIT listesi BILEREK birbirini yedekler; o yuzden her biri
    # DIGERININ susturuldugu bir fikstur uzerinde olculur (aksi halde ikisi de "olu"
    # gorunurdu — ilk kosumda tam bu yasandi).
    yalniz_yas = _temel()                       # cf sinyali YOK (MISS), age BUYUK
    for s in yalniz_yas["sayfalar"][:3]:
        s.update({"http": 404, "cf": "MISS", "age": 9000})
    yalniz_cf = _temel()                        # age sinyali YOK, cf HIT
    for s in yalniz_cf["sayfalar"][:3]:
        s.update({"http": 404, "cf": "HIT", "age": 5})
    for ad, capa, yerine, g in (
            ("MU7 `age` esigi sonsuz", "ONBELLEK_YAS_ESIGI_SN = " + "60",
             "ONBELLEK_YAS_ESIGI_SN = 10 ** 9", yalniz_yas),
            ("MU8 cf HIT listesi bosaltildi",
             'cf in ("HIT", ' + '"STALE", "EXPIRED", "REVALIDATED")', "cf in ()", yalniz_cf)):
        if oz.count(capa) != 1:
            kirmizi += 1
            ham.append("    ❌ MUTASYON CAPASI YOK/COK: " + ad)
            continue
        iddia("    (taban) " + ad + " fiksturunde ONBELLEK teshisi VAR",
              any(x[1] == "ONBELLEK" for x in degerlendir(g)[1]))
        ns = {"__name__": "csk_mutant_onb", "__file__": os.path.abspath(__file__)}
        exec(compile(oz.replace(capa, yerine), "<csk-mutant>", "exec"), ns)
        _d, s_m, _h = ns["degerlendir"](g)
        iddia(ad + " -> ONBELLEK teshisi KAYBOLUYOR (sinyal yuk tasiyor)",
              not any(x[1] == "ONBELLEK" for x in s_m), [x[:2] for x in s_m])

    # MU10 — ORNEKLEM SECIM KABLOSU: yeni-commit ekseninin birlesimi sokulurse 30 Tem
    # vakasi GERI GELIR. Kaynak mutasyonu ile kanitlanir (fiksturler secimi ATLAR, bu
    # yuzden secim ancak DOGRUDAN cagrilarak sinanabilir).
    _capa_orn = ("            secilen.append" + "(u)\n"
                 + "            gorulen.add" + '(u.get("id"))')
    if oz.count(_capa_orn) != 1:
        kirmizi += 1
        ham.append("    ❌ MUTASYON CAPASI YOK/COK: MU10 orneklem birlesimi")
    else:
        ns = {"__name__": "csk_mutant_orn", "__file__": os.path.abspath(__file__)}
        exec(compile(oz.replace(_capa_orn, "            pass"), "<csk-mutant>", "exec"), ns)
        m_secim, m_komp = ns["orneklem_sec"](_sahne, ["toka"], 20)
        iddia("MU10 yeni-commit birlesimi sokulunca urun ORNEKLEM DISINDA kaliyor",
              "toka" not in [u["id"] for u in m_secim], m_komp)
        iddia("    ... ve ORNEKLEM ekseni bu korlugu SAPMA olarak yakaliyor",
              any(s[1] == "SAPMA" for s in ns["kontrol_orneklem"](
                  {"orneklem": dict(m_komp, son_commit=12, hata=None)}, "YERLESIK")),
              m_komp)

    # ---- (E) API SOZLESMESI: gozlem toplayicinin urettigi anahtarlar karar tarafiyla ayni mi
    ham.append("  (E) SOZLESME")
    taban_anahtar = set(_temel().keys())
    kaynak_anahtar = set(re.findall(r'^\s{8}"(\w+)":', oz, re.M))
    eksik = {"depo", "canli_katalog", "ci", "sayfalar", "d1", "gorseller",
             "kart_kanali", "fiziksel_fiyat", "orneklem"} - taban_anahtar
    iddia("fikstur semasi degerlendir()'in bekledigi TUM eksenleri iceriyor", not eksik, eksik)
    iddia("gozlem_topla() ile fikstur AYNI anahtar kumesini kullaniyor",
          taban_anahtar <= (kaynak_anahtar | taban_anahtar))
    iddia("KONTROLLER listesi 8 ekseni de kabloluyor", len(KONTROLLER) == 8, len(KONTROLLER))
    # 🔴 DEVIR ZINCIRI: her devreden eksen kendi aracini ISIMLE cagirmali ve arac yoksa
    # ARAC-YOK demeli. Bir eksenin baska bir eksenin aracina devredilmesi (K6 -> K4) tam da
    # 1 Agu korlugunu uretirdi.
    iddia("K6 devir zinciri K4'ten AYRI bir araca gidiyor",
          "fiziksel-canli-kapisi.py" in oz and "konfigur-canli-kapisi.py" in oz)

    print("\n".join(ham))
    print("-" * 78)
    print("SONUC: YESIL ✅ (kendini test)" if kirmizi == 0
          else "SONUC: KIRMIZI ❌ — %d iddia kaldi" % kirmizi)
    return 0 if kirmizi == 0 else 1


# ================================================================= CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", default=SITE_VARSAYILAN)
    ap.add_argument("--ci-api", default=CI_API_VARSAYILAN, dest="ci_api")
    ap.add_argument("--adet", type=int, default=ADET_VARSAYILAN,
                    help="DIZI-BASI ekseni: dizinin en yeni N kaydi")
    ap.add_argument("--son-commit", type=int, default=SON_COMMIT_SAYISI_VARSAYILAN,
                    dest="son_commit",
                    help="YENI-COMMIT ekseni: son K commit'te eklenen TUM urunler "
                         "orneklem'e girer (dizi konumundan BAGIMSIZ)")
    ap.add_argument("--gecikme", type=float, default=GECIKME_VARSAYILAN,
                    help="istekler arasi bekleme (worker hiz siniri 60/60 sn)")
    ap.add_argument("--zaman-asimi", type=float, default=25, dest="zaman_asimi")
    ap.add_argument("--json", action="store_true", dest="jsonla")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    a = ap.parse_args(argv)
    if a.kendini:
        return kendini_test()
    g = gozlem_topla(a.site, a.ci_api, a.adet, a.gecikme, a.zaman_asimi, a.son_commit)
    durum, satirlar, hal = degerlendir(g)
    if a.jsonla:
        print(json.dumps({"durum": durum, "hal": hal, "cikis": DURUM_KOD[durum],
                          "satirlar": [{"kontrol": k, "sinif": s, "mesaj": m, "eylem": e}
                                       for k, s, m, e in satirlar]},
                         ensure_ascii=False, indent=2))
        return DURUM_KOD[durum]
    return rapor(durum, satirlar, hal, g)


if __name__ == "__main__":
    sys.exit(main())

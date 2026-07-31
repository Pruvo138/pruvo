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

NE OLCER (4 EKSEN, hepsi FAIL-CLOSED)
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
  A3 NABIZ  (AG · IKINCIL, KAYBOLMADI) — o is akisinin SON `event=schedule` kosumu son N
     saat icinde mi. "Cron HIC ateslemiyor" hali AYRI bir arizadir (damga tazeyken bile
     elle dispatch'le beslenmis olabilir) ve AYRI raporlanir. Esigi artik NOMINAL cron
     araligindan DEGIL, OLCULEN TESLIM ORANINDAN turetilir (bkz. esik_saat).

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
    """[{dosya, cron, aralik, esik, kayitli, durum, kosum_sayisi, son_kosum}] — AG kolu.

    `getir` ENJEKTE EDILEBILIR: fikstur kolu GERCEK API govdesinin ayni seklini besler."""
    liste = getir("repos/%s/actions/workflows?per_page=100" % DEPO)
    if not isinstance(liste, dict) or not isinstance(liste.get("workflows"), list):
        raise OlcumHatasi("is akisi listesi beklenen sekilde degil (`workflows` dizisi yok)")
    yol_ile = {}
    for wf in liste["workflows"]:
        if not isinstance(wf, dict) or "path" not in wf or "id" not in wf:
            raise OlcumHatasi("is akisi kaydinda `path`/`id` yok: %r" % (wf,))
        yol_ile[wf["path"]] = wf

    gozlemler = []
    for dosya, cron in dosyalar:
        yol = ".github/workflows/%s" % dosya
        wf = yol_ile.get(yol)
        g = {"dosya": dosya, "cron": cron, "kayitli": wf is not None,
             "durum": (wf or {}).get("state"), "kosum_sayisi": None, "son_kosum": None}
        try:
            g["aralik"] = aralik_dakika(dakika_kumesi(cron) or {0})
        except OlcumHatasi:
            g["aralik"] = None
        g["esik"] = esik_saat(g["aralik"]) if g["aralik"] else ESIK_TABAN_SAAT
        if wf is not None:
            kosumlar = getir("repos/%s/actions/workflows/%s/runs?event=schedule&per_page=1"
                             % (DEPO, wf["id"]))
            if not isinstance(kosumlar, dict) or "total_count" not in kosumlar:
                raise OlcumHatasi("%s kosum yaniti beklenen sekilde degil "
                                  "(`total_count` yok)" % dosya)
            g["kosum_sayisi"] = int(kosumlar["total_count"])
            satirlar = kosumlar.get("workflow_runs") or []
            if g["kosum_sayisi"] > 0:
                if not satirlar:
                    raise OlcumHatasi("%s: total_count=%d ama `workflow_runs` BOS "
                                      "-> yanit tutarsiz" % (dosya, g["kosum_sayisi"]))
                k = satirlar[0]
                if not isinstance(k, dict) or "created_at" not in k:
                    raise OlcumHatasi("%s: kosum kaydinda `created_at` yok" % dosya)
                if k.get("event") != "schedule":
                    raise OlcumHatasi("%s: event=schedule istendi ama kayit event=%r "
                                      "-> suzgec calismiyor" % (dosya, k.get("event")))
                g["son_kosum"] = _iso(k["created_at"])
                g["son_kosum_id"] = k.get("id")
                g["son_sonuc"] = k.get("conclusion")
        gozlemler.append(g)
    return gozlemler


# ---- A0: SON BASARILI UZLASTIRMA DAMGASI ------------------------------------
def damga_gozle(getir=api_getir):
    """En yeni SURESI DOLMAMIS `uzlastirma-damgasi` artifact'i -> gozlem sozlugu.

    Doner: {"var": bool, "an": datetime|None, "kosum": id|None, "sha": str|None,
            "toplam": int, "suresi_dolan": int, "sebep": str|None}
    HER sekil arizasi OlcumHatasi (rc 2): eksik alan, ad suzgecinin calismamasi,
    cozulemeyen zaman damgasi. "Damga YOK" ise SEKIL arizasi degil OLCUM'dur ->
    var=False doner ve hukum katmani bunu ALARM sayar."""
    d = getir("repos/%s/actions/artifacts?name=%s&per_page=100"
              % (DEPO, urllib.parse.quote(DAMGA_ADI)))
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
        if a["name"] != DAMGA_ADI:
            raise OlcumHatasi("artifact ad suzgeci CALISMIYOR: name=%r istendi, %r dondu "
                              "-> damga ekseni olculemez" % (DAMGA_ADI, a["name"]))
    taze = [a for a in kayitlar if not a["expired"]]
    if not kayitlar:
        return {"var": False, "an": None, "kosum": None, "sha": None, "toplam": 0,
                "suresi_dolan": 0,
                "sebep": "depoda `%s` adli HIC artifact YOK" % DAMGA_ADI}
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


def uzlastirici_esigi(dosyalar):
    """A0 esigi UZLASTIRICININ cron cadansindan turetilir (nominal -> olculen teslim
    orani -> N). Uzlastirici dosyasi yoksa/cron'suzsa OLCULEMEDI: bu nobetci
    "denetleyen bir is var" VARSAYMAZ."""
    for dosya, cron in dosyalar:
        if dosya != UZLASTIRICI_DOSYA:
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
                raise OlcumHatasi("uzlastirici cron dakika alani cozulemedi: %r" % cron)
        aralik = aralik_dakika(dakikalar)
        return dosya, esik_saat(aralik), aralik
    raise OlcumHatasi(
        "UZLASTIRICI BULUNAMADI: cron tasiyan is akislari arasinda %s YOK. A0 damga "
        "ekseninin capasi budur — dosya silinir/adi degisirse 'denetim yapiliyor' "
        "iddiasi olculemez hale gelir, sessiz YESIL verilmez." % UZLASTIRICI_DOSYA)


# ---- HUKUM ------------------------------------------------------------------
def degerlendir(dosyalar, gozlemler, simdi=None, damga=None, damga_esigi=None):
    """(rc, satirlar). rc 0 yesil · 1 alarm · 2 olculemedi.

    `damga` verilmezse A0 ekseni RAPORLANMAZ (agsiz A1 birim testleri icin);
    GERCEK olcum yolunda main() her zaman verir."""
    simdi = simdi or datetime.now(timezone.utc)
    satirlar = []
    alarm = False
    olculemedi = False

    if not dosyalar:
        return 2, ["OLCULEMEDI: depoda cron tasiyan is akisi BULUNAMADI. Bu nobetci "
                   "boslukta calisiyor demektir (kesif bozulmus ya da cron silinmis) — "
                   "sessiz YESIL verilmez."]

    # --- A0 DAMGA (BIRINCIL EKSEN) -------------------------------------------
    if damga is not None:
        n0 = damga_esigi if damga_esigi else ESIK_TABAN_SAAT
        if not damga.get("var"):
            satirlar.append(
                "🔴 A0 DAMGA -> SON BASARILI UZLASTIRMA DAMGASI YOK (%s). Katalog-D1 "
                "sapmasi HIC denetlenmedi ya da denetim %d saatten uzun suredir "
                "tamamlanmadi. Bir kosumun YESIL olmasi denetim yapildigi ANLAMINA "
                "GELMEZ (olculdu 31 Tem 20:47:18Z: conclusion=success · olcum/onarim/"
                "teyit adimlarinin HEPSI skipped)." % (damga.get("sebep"), n0))
            alarm = True
        else:
            yas0 = (simdi - damga["an"]).total_seconds() / 3600.0
            if yas0 > n0:
                satirlar.append(
                    "🔴 A0 DAMGA -> son basarili uzlastirma %.1f saat once (esik N=%d sa). "
                    "D1 ile urunler.json arasindaki sapma %.1f saattir DENETLENMEDI; "
                    "Ege bayat veri gosteriyor olabilir ve baska hicbir kapi bunu gormez. "
                    "(damga kosumu %s · sha %s)"
                    % (yas0, n0, yas0, damga.get("kosum"), str(damga.get("sha"))[:12]))
                alarm = True
            else:
                satirlar.append(
                    "✅ A0 DAMGA -> son basarili uzlastirma %.1f saat once (esik N=%d sa · "
                    "taze damga %d, suresi dolan %d · kosum %s)"
                    % (yas0, n0, damga["toplam"] - damga["suresi_dolan"],
                       damga["suresi_dolan"], damga.get("kosum")))

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

        n = g["esik"]
        if g["kosum_sayisi"] == 0:
            satirlar.append("🔴 A3 NABIZ %s -> event=schedule kosum sayisi SIFIR: cron "
                            "HIC ATESLENMEMIS. Dosya main'de ve is akisi aktif oldugu "
                            "halde tek bir zamanlanmis kosum yok -> bu is akisinin "
                            "yaptigi HICBIR SEY yapilmiyor ve hicbir yerde kirmizi "
                            "yanmiyor." % etiket)
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


def _sahte_api(durum="active", kosum_sayisi=0, yas_saat=0.0, kayitli=True,
               dosya="d1-uzlastirici.yml", bozuk=None, event="schedule",
               damgalar=None):
    """GERCEK govdenin ayni seklini ureten enjekte edilebilir `getir`.

    `damgalar`: artifact kayitlari listesi (None -> tek TAZE damga)."""
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
            return {"total_count": 1, "workflows": [wf]}
        if "/runs?" in yol:
            if bozuk == "kosum-sekli":
                return {"workflow_runs": []}
            if bozuk == "tutarsiz":
                return {"total_count": 3, "workflow_runs": []}
            if kosum_sayisi == 0:
                return {"total_count": 0, "workflow_runs": []}
            k = dict(_HAM_KOSUM)
            k["event"] = event
            k["path"] = ".github/workflows/%s" % dosya
            an = datetime.now(timezone.utc) - timedelta(hours=yas_saat)
            k["created_at"] = an.strftime("%Y-%m-%dT%H:%M:%SZ")
            k["run_started_at"] = k["created_at"]
            return {"total_count": kosum_sayisi, "workflow_runs": [k]}
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

    def kos(dosyalar, getir, damga_ile=False):
        """damga_ile=True -> A0 ekseni de olculur (GERCEK olcum yolunun ayni sirasi)."""
        try:
            g = gozlem_topla(dosyalar, getir)
            d = n0 = None
            if damga_ile:
                _ad, n0, _ar = uzlastirici_esigi(dosyalar)
                d = damga_gozle(getir)
        except OlcumHatasi as e:
            return 2, ["OLCULEMEDI: %s" % e]
        return degerlendir(dosyalar, g, damga=d, damga_esigi=n0)

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
    rc, s = kos(D, _sahte_api(kosum_sayisi=0))
    iddia("A3 (a) HIC schedule kosumu YOK -> KIRMIZI", rc == 1, "rc=%d" % rc)
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

    # --- FAIL-CLOSED: veri yoksa YESIL DEGIL ---
    rc, s = kos(D, _sahte_api(bozuk="ag"))
    iddia("FAIL-CLOSED: ag hatasi -> OLCULEMEDI (rc 2), YESIL DEGIL", rc == 2, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(bozuk="liste-sekli"))
    iddia("FAIL-CLOSED: is akisi listesi sekli degismis -> rc 2", rc == 2, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(bozuk="kosum-sekli", kosum_sayisi=3))
    iddia("FAIL-CLOSED: kosum yanitinda `total_count` yok -> rc 2", rc == 2, "rc=%d" % rc)
    rc, _ = kos(D, _sahte_api(bozuk="tutarsiz"))
    iddia("FAIL-CLOSED: total_count>0 ama workflow_runs bos -> rc 2", rc == 2, "rc=%d" % rc)
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

    print("\n%d iddia kosturuldu, %d KIRMIZI." % (sayac[0], len(hatalar)))
    return hatalar


def damga_govdesi(ortam=None):
    """DAMGANIN MAKINE-OKUNUR govdesi. Okuyucu ile YAZICI AYNI DOSYADA tutulur: artifact
    adi (DAMGA_ADI) tek kaynaktir, ikisi birbirinden BAGIMSIZ bayatlayamaz."""
    o = os.environ if ortam is None else ortam
    return {
        "surum": 1,
        "damga": DAMGA_ADI,
        "an": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "is_akisi": UZLASTIRICI_DOSYA,
        "kosum_id": o.get("GITHUB_RUN_ID"),
        "kosum_no": o.get("GITHUB_RUN_NUMBER"),
        "olay": o.get("GITHUB_EVENT_NAME"),
        "sha": o.get("GITHUB_SHA"),
        "depo": o.get("GITHUB_REPOSITORY") or DEPO,
        # NE IDDIA EDILIYOR: bu damga "kosum yesildi" DEMEK DEGIL, "D1-katalog sapmasi
        # FIILEN olculdu ve (sapma varsa) onarim TEYIT edildi" demektir.
        "iddia": "d1-katalog sapmasi olculdu ve kapatildi (olcum + gerekiyorsa onarim teyidi)",
    }


def damga_yaz(yol, ortam=None):
    govde = damga_govdesi(ortam)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(govde, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return govde


def main():
    ap = argparse.ArgumentParser(description="Uzlastirma nabiz kapisi")
    ap.add_argument("--kendini-test", action="store_true",
                    help="AGSIZ fikstur kabulu (CI'da bu kol da kosar)")
    ap.add_argument("--damga-yaz", metavar="DOSYA",
                    help="Son basarili uzlastirma damgasini JSON olarak yaz "
                         "(d1-uzlastirici.yml `Damga` adimi kullanir)")
    a = ap.parse_args()

    if a.damga_yaz:
        govde = damga_yaz(a.damga_yaz)
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
        gozlemler = gozlem_topla(dosyalar)
        damga = damga_gozle()
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
    return rapor(*degerlendir(dosyalar, gozlemler, damga=damga,
                              damga_esigi=damga_esigi))


if __name__ == "__main__":
    sys.exit(main())

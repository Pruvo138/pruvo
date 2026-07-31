#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CRON NABIZ KAPISI — "zamanlanmis is HIC kosmadi" sessizligini GORUNUR kilar.

NEDEN VAR (OLCULDU, 31 Tem 2026)
================================
`.github/workflows/d1-uzlastirici.yml` icinde `*/15 * * * *` cron'u vardi; dosya main'de,
is akisi `state: active`, depo hareketli. BUNA RAGMEN:

    gh api repos/Pruvo138/pruvo/actions/runs?event=schedule  ->  total_count = 0

Cron dosyaya girdikten 4 sa 36 dk sonra BEKLENEN ~18 tetiklemenin SIFIRI kosmustu. Ayni gun
D1'de 56 kayitta icerik ekseni BAYAT bulundu ve ELLE senkronlandi — uzlastirici kossaydi o
sapma sessiz kalmazdi.

🔴 SINIF: KOSMAYAN BIR UZLASTIRICI HICBIR YERDE KIRMIZI YAKMAZ. Kirilan bir kapi CI'yi
kirmiziya boyar; HIC ATESLENMEYEN bir zamanlanmis is ise "yesil" bile uretmez — GORUNMEZ.
Bu depoda olculen sessiz-hata sinifinin ta kendisi. Bu nobetci o bosluga bakar: is akisinin
KOSMUS OLMASINI olcer, VAR OLMASINI degil.

NE OLCER (3 EKSEN, hepsi FAIL-CLOSED)
=====================================
  A1 BICIM  (AGSIZ) — depodaki her is akisinin cron DAKIKA alani ACIK LISTE mi ve yogun
     ceyrek-saat sinirlarindan (dakika 0/15/30/45) UZAK mi.
     GEREKCE: GitHub zamanlanmis kosumlari tetiklerken tam saat basi ve ceyrek sinirlarinda
     kuyruk yigilir; dokumantasyonun kendi tavsiyesi "yogun dakikalardan kacinin"dir.
     `*/15` TAM O DORT DAKIKAYA duser. Bu eksen ONARIMIN KENDISINI KILITLER: cron `*/15`e
     geri cevrilirse bu nobetci KIRMIZI yanar (mutasyonla olculdu).
  A2 DURUM  (AG)    — cron tasiyan is akisi GitHub tarafinda kayitli ve `state == active` mi
     (GitHub 60 gun hareketsizlikta zamanlanmis is akisini `disabled_inactivity` yapar —
     dosya yerinde durur, kimse fark etmez).
  A3 NABIZ  (AG)    — o is akisinin SON `event=schedule` kosumu son N SAAT icinde mi.
     N cron ARALIGINDAN TURETILIR (bkz. esik_saat): N = 12 x aralik, [2, 24] saate kirpilir.
     15 dk araliginda N = 3 SAAT = beklenen 12 tetikleme. GEREKCE: GitHub'in kendi gecikmesi
     yogun anlarda on dakikalari bulabilir (tekil kacislar NORMALDIR, alarm degildir); ama
     ust uste 12 pencerenin SIFIRI kosmussa bu jitter DEGIL, ARIZADIR.
     `total_count == 0` (hic kosmamis) A3'un en agir halidir ve AYRI teshis basar.

FAIL-CLOSED SOZLESMESI
======================
Veri CEKILEMEZSE (ag hatasi, HTTP != 200, bozuk JSON, eksik alan, PyYAML yok) sonuc YESIL
DEGIL, "OLCULEMEDI" = rc 2 = KIRMIZI'dir. Bir nabiz nobetcisinin fail-open olmasi kendi
konusunun tekrari olurdu: olculemeyen nabiz, olmayan nabizdan ayirt edilemez.

CIKIS KODLARI:  0 = NABIZ VAR  ·  1 = ALARM (cron sessiz / bicim ihlali / devre disi)
                2 = OLCULEMEDI (fail-closed KIRMIZI)

YAYIN YOLUNU BLOKLAMAZ: deploy.yml'de `cron-nabzi` job'unda kosar; `deploy` bu job'a
`needs:` ile BAGLI DEGILDIR (serit B). Kirmizi GORUNUR, yayin CIKAR.

Kullanim:
    python3 tools/cron-nabiz-kapisi.py                 # GERCEK olcum (GitHub API)
    python3 tools/cron-nabiz-kapisi.py --kendini-test  # AGSIZ fikstur kabulu (iki yonlu)
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
WORKFLOW_DIZIN = os.path.join(ROOT, ".github", "workflows")

DEPO = os.environ.get("GITHUB_REPOSITORY") or "Pruvo138/pruvo"
API = "https://api.github.com"

# Yogun tetikleme dakikalari — `*/15` tam bu kumeye duser.
YOGUN_DAKIKALAR = frozenset((0, 15, 30, 45))
# N = ESIK_CARPANI x aralik; [ESIK_TABAN, ESIK_TAVAN] saate kirpilir.
ESIK_CARPANI = 12
ESIK_TABAN_SAAT = 2
ESIK_TAVAN_SAAT = 24


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


def esik_saat(aralik_dk):
    """N (saat) = ESIK_CARPANI x aralik, [TABAN, TAVAN] saate kirpilir."""
    ham = (ESIK_CARPANI * aralik_dk) / 60.0
    return int(min(ESIK_TAVAN_SAAT, max(ESIK_TABAN_SAAT, round(ham))))


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


# ---- HUKUM ------------------------------------------------------------------
def degerlendir(dosyalar, gozlemler, simdi=None):
    """(rc, satirlar). rc 0 yesil · 1 alarm · 2 olculemedi."""
    simdi = simdi or datetime.now(timezone.utc)
    satirlar = []
    alarm = False

    if not dosyalar:
        return 2, ["OLCULEMEDI: depoda cron tasiyan is akisi BULUNAMADI. Bu nobetci "
                   "boslukta calisiyor demektir (kesif bozulmus ya da cron silinmis) — "
                   "sessiz YESIL verilmez."]

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
            satirlar.append("🔴 A3 NABIZ %s -> son event=schedule kosumu %.1f saat once "
                            "(esik N=%d sa · aralik %d dk · bu surede beklenen ~%d "
                            "tetikleme, olculen 0). Cron SESSIZ."
                            % (etiket, yas, n, g["aralik"], beklenen))
            alarm = True
        else:
            satirlar.append("✅ A3 NABIZ %s -> son event=schedule kosumu %.1f saat once "
                            "(esik N=%d sa · toplam %d zamanlanmis kosum)"
                            % (etiket, yas, n, g["kosum_sayisi"]))
    return (1 if alarm else 0), satirlar


def rapor(rc, satirlar):
    print("CRON NABIZ KAPISI — depo %s" % DEPO)
    for s in satirlar:
        print("  " + s)
    if rc == 0:
        print("SONUC: NABIZ VAR ✅ (zamanlanmis isler fiilen kosuyor)")
    elif rc == 1:
        print("SONUC: 🔴 ALARM — zamanlanmis is sessiz/kacik. Bu is akisinin yaptigi is "
              "YAPILMIYOR ve baska hicbir kapi bunu gormez.")
    else:
        print("SONUC: 🔴 OLCULEMEDI (fail-closed) — nabiz OLCULEMEDI, 'yesil' SAYILMAZ.")
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
                    "author": {"name": "Okan Gemalmaz", "email": "gemalmaz@me.com"},
                    "committer": {"name": "Okan Gemalmaz", "email": "gemalmaz@me.com"}},
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


def _sahte_api(durum="active", kosum_sayisi=0, yas_saat=0.0, kayitli=True,
               dosya="d1-uzlastirici.yml", bozuk=None, event="schedule"):
    """GERCEK govdenin ayni seklini ureten enjekte edilebilir `getir`."""
    def getir(yol, zaman_asimi=25):   # noqa: ARG001
        if bozuk == "ag":
            raise OlcumHatasi("GitHub API cagrilamadi (URLError: [Errno 8] nodename nor "
                              "servname provided)")
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


def kendini_test():
    """IKI YONLU kabul: kirmizi yol da yesil yol da FIKSTURLE kosturulur."""
    hatalar = []
    sayac = [0]

    def iddia(ad, kosul, detay=""):
        sayac[0] += 1
        print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", ad,
                               ("  -> " + detay) if detay else ""))
        if not kosul:
            hatalar.append(ad)

    def kos(dosyalar, getir):
        try:
            g = gozlem_topla(dosyalar, getir)
        except OlcumHatasi as e:
            return 2, ["OLCULEMEDI: %s" % e]
        return degerlendir(dosyalar, g)

    D = [("d1-uzlastirici.yml", "7,22,37,52 * * * *")]

    # --- ESIK TURETIMI ---
    iddia("aralik: 7,22,37,52 -> 15 dk", aralik_dakika({7, 22, 37, 52}) == 15,
          "olculen %s" % aralik_dakika({7, 22, 37, 52}))
    iddia("aralik: saat sinirini asan fark gorulur (52 -> 7 = 15 dk)",
          aralik_dakika({7, 52}) == 15, "olculen %s" % aralik_dakika({7, 52}))
    iddia("esik: 15 dk aralik -> N=3 saat (12 tetikleme)", esik_saat(15) == 3,
          "olculen %s" % esik_saat(15))
    iddia("esik TABANI: 1 dk aralik bile N>=%d saat" % ESIK_TABAN_SAAT,
          esik_saat(1) == ESIK_TABAN_SAAT, "olculen %s" % esik_saat(1))
    iddia("esik TAVANI: gunluk cron N<=%d saat" % ESIK_TAVAN_SAAT,
          esik_saat(1440) == ESIK_TAVAN_SAAT, "olculen %s" % esik_saat(1440))

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

    # --- A3 NABIZ: IKI YONLU ANA KANIT ---
    rc, s = kos(D, _sahte_api(kosum_sayisi=0))
    iddia("A3 (a) HIC schedule kosumu YOK -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A3 (a) teshis 'HIC ATESLENMEMIS' der (susma sinifi adlandirilir)",
          any("HIC ATESLENMEMIS" in x for x in s))
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=0.4))
    iddia("A3 (b) YAKIN ZAMANDA kosum var (24 dk) -> YESIL", rc == 0, "rc=%d" % rc)
    iddia("A3 (b) rapor kosum sayisini ve yasi SAYIYLA yazar",
          any("137" in x and "0.4" in x for x in s))
    rc, _ = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=2.9))
    iddia("A3: esigin ALTINDA (2,9 sa < N=3) -> YESIL", rc == 0, "rc=%d" % rc)
    rc, s = kos(D, _sahte_api(kosum_sayisi=137, yas_saat=5.0))
    iddia("A3: esigin USTUNDE (5,0 sa > N=3) -> KIRMIZI", rc == 1, "rc=%d" % rc)
    iddia("A3: teshis beklenen tetikleme sayisini yazar",
          any("beklenen ~20" in x for x in s))

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


def main():
    ap = argparse.ArgumentParser(description="Cron nabiz kapisi")
    ap.add_argument("--kendini-test", action="store_true",
                    help="AGSIZ fikstur kabulu (CI'da bu kol da kosar)")
    a = ap.parse_args()

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
        gozlemler = gozlem_topla(dosyalar)
    except OlcumHatasi as e:
        print("CRON NABIZ KAPISI — depo %s" % DEPO)
        print("  🔴 OLCULEMEDI: %s" % e)
        print("SONUC: 🔴 OLCULEMEDI (fail-closed) — nabiz olculemedi, 'yesil' SAYILMAZ.")
        return 2
    return rapor(*degerlendir(dosyalar, gozlemler))


if __name__ == "__main__":
    sys.exit(main())

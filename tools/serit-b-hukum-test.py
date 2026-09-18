#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K339 + K339-EK — SERIT B **HUKUM ORANI** KAPISI (politika + sayac; fail-closed)

NE OLCER (iki eksen, ikisi de CALISTIRILABILIR):

  POLITIKA (P1..P5) — `.github/workflows/nobet.yml` AYRISTIRILIR (metin grep'i DEGIL,
    gercek YAML): eszamanlilik sozlesmesi UC KOLLU mu, `cancel-in-progress: false` mi,
    HEAD garantili hukum kolu (`schedule` tetigi) duruyor mu, push kolu SHA/run_id
    TASIMIYOR mu (G9 korumasi — bkz. asagi), ve K339-EK'in yorum blogu OLCEN BIR KOLA
    bagli mi.

  SAYAC (S1..S7) — `hukum_ozeti()`: bir kosum listesinden **hukum ureten kosum orani**
    ve **kac kosumdur hukum alinamadi** (HUKUMSUZ_SERI) sayilir. `cancelled` HUKUM
    DEGILDIR; `OLCULEMEDI` kovasina duser ve o kova ADIYLA basilir. Fiksturler
    K339/K339-EK'in KENDI tabanlarini (12'de 8 · 25'te 0) ve 16 Eyl 2026'da olculen
    guncel pencereyi tasir.

🔴 NEDEN VAR (K339-EK, mimar karari 7 Eyl 2026): olcut **HEAD GARANTILI HUKUM**'dur,
SHA kapsamasi DEGIL. `push` kolunun tek sabit kovasi BILEREK duruyor (maliyet korumasi);
`tools/is-akisi-kapisi.py :: G9` push kolunun `github.` SHA/run_id tasimasini KIRMIZI
yakar ve bu kalemde o onarim YASAKTIR. Geriye kalan tek is, K339 kabul ②'nin istedigi
SAYAC idi: "kac kosumdur hukum alinamadi" HER kosumda ADIYLA basilir; **0 ile n AYNI
satirdan okunur** (sessiz sifir yasak). Bu dosya o sayaci kurar ve esigi HEAD garantili
kola (schedule) baglar — push kolunun orani BILGI olarak basilir, rc'yi belirlemez.

🔴 K339-EK ⑥: nobet.yml'deki "kuyrukta cancelled" yorumu 2026-08-28'e kadar arizayi
DOGRU tarif edip YANLIS siniflamisti ("geri bildirim gecikmesi"), ve hicbir kol ona
bagli degildi — bu yuzden ariza iki kez yeniden kesfedildi. P5 o yorumu BU DOSYAYA
capalar: atif ya da zarar sinifi cumlesi yorumdan dusurulurse kapi KIRMIZI yanar.

CANLI KOL: `--canli` verilirse GitHub Actions API'sinden son N kosum okunur ve ayni
sayac GERCEK veriyle basilir. Ag/jeton/ayristirma arizasi SESSIZ YESIL degil `rc=2
OLCULEMEDI`dir. `--canli` YOKKEN kol ADIYLA "KOSULMADI" basar (sessiz atlama yok).

Calistir:
  python3 tools/serit-b-hukum-test.py                 # politika + sayac fiksturleri
  python3 tools/serit-b-hukum-test.py --canli         # + GERCEK kosum listesi (jeton ister)
  python3 tools/serit-b-hukum-test.py --mutasyon      # mutasyon bataryasi (kopyada)

Cikis: 0 YESIL · 1 KIRMIZI · 2 OLCULEMEDI (fail-closed)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
IS_AKISI = os.path.join(ROOT, ".github", "workflows", "nobet.yml")
DEPO = "Pruvo138/pruvo"
API = "https://api.github.com"
IS_AKISI_ADI = "Nöbet şeridi (SERIT B — yayını BLOKLAMAZ)"

# HUKUM = tamamlanmis ve YARGI ureten sonuc. `cancelled` YOKTUR (K339 kabul ①);
# `skipped`/`stale`/`timed_out` de hukum degildir — `timed_out` bir kolun ASILDIGINI
# soyler, seridin hukmunu DEGIL ([[fail-slow-fail-opendir]]).
HUKUM_SONUCLARI = ("success", "failure")

# 🔴 ESIK TABANI OLCULDU (16 Eyl 2026, `gh run list --limit 200`, pencere
# 11 Eyl 18:28Z → 16 Eyl 11:32Z): HEAD garantili kol (`schedule`) 20 kosumun
# 18'inde hukum uretti = %90. Iki iptal 13-14 Eyl'de AYNI SHA'da (bda9ccab) ve
# uzun suren bir turun arkasinda kuyruga girdigi icin dustu. Esik %80: olculen
# tabanin ALTINDA (bir iptal daha kaldirir) ama ikinci bir cift iptali YAKALAR.
ESIK_HEAD_ORANI = 0.80
# Bu sayinin altinda pencere "olculecek kadar kosum yok" demektir -> OLCULEMEDI.
ASGARI_HEAD_KOSUM = 5
# HEAD garantili hukum kolu (K373, 2 Eyl 2026) — `schedule` tetigi.
HEAD_KOLU = "schedule"


class OlcumHatasi(Exception):
    """Olcum YAPILAMADI (fail-closed). YESIL degil, KIRMIZI da degil: rc=2."""


# ── SAYAC ────────────────────────────────────────────────────────────────────
def hukum_ozeti(kosumlar):
    """[{event, conclusion, status}] -> hukum orani + HUKUMSUZ_SERI ozeti.

    Donen sozlukte her sayi ADIYLA durur; cagiran hicbirini turetmek zorunda degil.
    `hukumsuz_seri` = EN YENI kosumdan geriye dogru, hukum URETMEYEN tamamlanmis
    kosum sayisi ("kac kosumdur hukum alinamadi"). Liste EN YENI ONCE sirali gelir
    (gh/API varsayilani)."""
    if not isinstance(kosumlar, list):
        raise OlcumHatasi("kosum listesi liste degil: %r" % (type(kosumlar).__name__,))
    kollar = {}
    toplam = tamamlanan = hukum = iptal = bekleyen = 0
    for k in kosumlar:
        if not isinstance(k, dict):
            raise OlcumHatasi("kosum kaydi sozluk degil: %r" % (k,))
        kol = (k.get("event") or "").strip() or "BILINMEYEN"
        sonuc = (k.get("conclusion") or "").strip()
        durum = (k.get("status") or "").strip()
        d = kollar.setdefault(kol, {"toplam": 0, "tamamlanan": 0, "hukum": 0,
                                    "iptal": 0, "bekleyen": 0})
        toplam += 1
        d["toplam"] += 1
        if not sonuc or durum not in ("completed", ""):
            if not sonuc:
                bekleyen += 1
                d["bekleyen"] += 1
                continue
        tamamlanan += 1
        d["tamamlanan"] += 1
        if sonuc in HUKUM_SONUCLARI:
            hukum += 1
            d["hukum"] += 1
        else:
            if sonuc == "cancelled":
                iptal += 1
                d["iptal"] += 1
    seri = 0
    for k in kosumlar:
        sonuc = (k.get("conclusion") or "").strip()
        if not sonuc:
            continue                      # henuz bitmemis kosum seriyi KIRMAZ, saymaz
        if sonuc in HUKUM_SONUCLARI:
            break
        seri += 1
    for d in kollar.values():
        d["oran"] = (d["hukum"] / d["tamamlanan"]) if d["tamamlanan"] else None
    return {
        "toplam": toplam, "tamamlanan": tamamlanan, "hukum": hukum,
        "iptal": iptal, "bekleyen": bekleyen,
        "oran": (hukum / tamamlanan) if tamamlanan else None,
        "hukumsuz_seri": seri,
        "kollar": kollar,
    }


def sayac_satiri(ozet, etiket):
    """🔴 K339 kabul ②: sayac HER kosumda ADIYLA basilir ve **0 ile n AYNI satirdan
    okunur**. Sifiri atlayan bir yazim (or. `if seri: print(...)`) ayni gizlemeyi
    uretirdi — o yuzden burada kosul YOKTUR."""
    oran = ozet["oran"]
    return ("SAYAC[%s]: HUKUMSUZ_SERI=%d  HUKUM=%d/%d  ORAN=%s  IPTAL(OLCULEMEDI)=%d  "
            "BEKLEYEN=%d" % (etiket, ozet["hukumsuz_seri"], ozet["hukum"],
                             ozet["tamamlanan"],
                             "OLCULEMEDI" if oran is None else "%.0f%%" % (oran * 100),
                             ozet["iptal"], ozet["bekleyen"]))


def head_esigi_gecti(ozet):
    """HEAD garantili kolun (schedule) hukum orani esigi geciyor mu?
    True/False; kol penceresi olcecek kadar dolu degilse None (OLCULEMEDI)."""
    d = ozet["kollar"].get(HEAD_KOLU) or {}
    if d.get("tamamlanan", 0) < ASGARI_HEAD_KOSUM:
        return None
    return d["oran"] >= ESIK_HEAD_ORANI


def kol_satirlari(ozet):
    cikti = []
    for kol in sorted(ozet["kollar"]):
        d = ozet["kollar"][kol]
        cikti.append("    KOL[%s]: hukum=%d/%d oran=%s iptal(OLCULEMEDI)=%d bekleyen=%d"
                     % (kol, d["hukum"], d["tamamlanan"],
                        "OLCULEMEDI" if d["oran"] is None else "%.0f%%" % (d["oran"] * 100),
                        d["iptal"], d["bekleyen"]))
    return cikti


# ── FIKSTURLER (tabanlar KALEMDEN ve OLCUMDEN gelir, uydurma YOK) ────────────
def _kosumlar(*gruplar):
    """(event, conclusion|None, adet) -> kosum listesi (EN YENI ONCE)."""
    liste = []
    for event, sonuc, adet in gruplar:
        for _ in range(adet):
            liste.append({"event": event, "conclusion": sonuc,
                          "status": "completed" if sonuc else "queued"})
    return liste


# K339-EK ⑦ REGRESYON TABANI — nobet.yml yorumunun KENDI sayisi: "son 12 SERIT B
# kosumunun 8'i kuyrukta cancelled oldu" (yorum, 10 Agu 2026).
F_YORUM = _kosumlar(("push", "cancelled", 8), ("push", "failure", 3),
                    ("push", "success", 1))
# K339 TABANI (28 Agu 2026, kalem metni): son 25 kosum — 0 success · 15 cancelled ·
# 8 failure · 2 pending.
F_K339 = _kosumlar(("push", None, 2), ("push", "cancelled", 15), ("push", "failure", 8))
# 16 Eyl 2026 OLCUMU (`gh run list --workflow "<serit b>" --limit 200`, pencere
# 11 Eyl 18:28Z → 16 Eyl 11:32Z): push 179 (57 hukum · 120 iptal · 2 bekleyen) ·
# schedule 20 (18 hukum · 2 iptal) · workflow_dispatch 1 (1 hukum).
F_BUGUN = _kosumlar(("push", None, 2), ("push", "cancelled", 120),
                    ("push", "failure", 50), ("push", "success", 7),
                    ("schedule", "cancelled", 2), ("schedule", "failure", 16),
                    ("schedule", "success", 2), ("workflow_dispatch", "failure", 1))
# K339 kabul ③ MUTANT VAKASI: ardisik iki push -> ikisi de kuyrukta iptal.
F_ARDISIK_IPTAL = _kosumlar(("push", "cancelled", 2), ("push", "failure", 1))
# K339 kabul ③ KONTROL: iptal OLMAYAN tek kosum -> hukum NORMAL okunur.
F_TEK_HUKUM = _kosumlar(("push", "failure", 1))
# ESIK OLU MU kolu (S8): HEAD garantili kolun orani esigin ALTINDA (6/10 = %60).
F_HEAD_DUSUK = _kosumlar(("schedule", "cancelled", 4), ("schedule", "failure", 5),
                         ("schedule", "success", 1))


# ── POLITIKA (nobet.yml) ─────────────────────────────────────────────────────
def is_akisi_oku(yol):
    try:
        import yaml
    except ImportError as e:  # noqa: BLE001
        raise OlcumHatasi("pyyaml yok (%s): is akisi GERCEK ayristiriciyla okunamadi" % e)
    try:
        ham = open(yol, encoding="utf-8").read()
    except OSError as e:
        raise OlcumHatasi("is akisi okunamadi (%s): %s" % (e, yol))
    try:
        veri = yaml.safe_load(ham)
    except Exception as e:  # noqa: BLE001
        raise OlcumHatasi("is akisi YAML ayrisamadi (%s): %s" % (e, yol))
    if not isinstance(veri, dict):
        raise OlcumHatasi("is akisi kok dugumu sozluk degil: %s" % yol)
    return ham, veri


def _tetikler(veri):
    # YAML 1.1: cikarilmamis `on` anahtari True'ya coker.
    for anahtar in ("on", True):
        if anahtar in veri:
            return veri[anahtar] or {}
    raise OlcumHatasi("is akisinda `on:` blogu YOK")


def politika_iddialari(yol):
    """[(ad, tamam_mi, aciklama)] — P1..P5."""
    ham, veri = is_akisi_oku(yol)
    iddia = []
    esz = veri.get("concurrency") or {}
    if not isinstance(esz, dict):
        raise OlcumHatasi("`concurrency` blogu sozluk degil: %r" % (esz,))
    grup = str(esz.get("group") or "")

    # P1 — UC KOL: dispatch KENDI kovasi (run_id) · schedule AYRI SABIT kova ·
    # push sabit kova. Tek sabit kova = K339'un kok nedeni.
    dispatch_kolu = "workflow_dispatch" in grup and "run_id" in grup
    schedule_kolu = "schedule" in grup
    ifade = "${{" in grup
    iddia.append((
        "P1 eszamanlilik grubu UC KOLLU (dispatch=run_id · schedule=ayri sabit kova · "
        "push=sabit kova)",
        bool(ifade and dispatch_kolu and schedule_kolu),
        "group=%r" % (grup[:160],)))

    # P2 — `cancel-in-progress: false`: `true` ard arda push'ta alarmi SESSIZLESTIRIR.
    ciprogress = esz.get("cancel-in-progress", None)
    iddia.append((
        "P2 cancel-in-progress: false (kosan nobet ard arda push'ta OLDURULMEZ)",
        ciprogress is False,
        "cancel-in-progress=%r" % (ciprogress,)))

    # P3 — HEAD GARANTILI HUKUM KOLU: `schedule` tetigi VAR ve kadansi <= 4 saat.
    tetikler = _tetikler(veri)
    sched = (tetikler or {}).get("schedule") if isinstance(tetikler, dict) else None
    cronlar = [str((c or {}).get("cron") or "") for c in (sched or [])
               if isinstance(c, dict)]
    saat_adimi = None
    for c in cronlar:
        m = re.match(r"^\s*\S+\s+\*/(\d+)\s", c)
        if m:
            saat_adimi = int(m.group(1))
    iddia.append((
        "P3 HEAD garantili hukum kolu: `schedule` tetigi VAR ve kadans <= 4 saat",
        bool(cronlar) and saat_adimi is not None and saat_adimi <= 4,
        "cron=%r saat_adimi=%r" % (cronlar, saat_adimi)))

    # P4 — PUSH KOLU SHA/run_id TASIMAZ. Bu kalemde push kuyrugunu bolmek YASAK
    # (tools/is-akisi-kapisi.py :: G9, olculmus maliyet gerekcesi). Burada AYNI
    # yasak SERIT B ozelinde civilenir: "onarim" diye push kolunu SHA'ya baglayan
    # bir degisiklik bu kapidan da gecemez.
    push_dali = grup.split("||")[-1]
    iddia.append((
        "P4 push kolu SHA/run_id TASIMAZ (G9 maliyet korumasi; bu kalemde onarim YASAK)",
        ("github.sha" not in push_dali) and ("run_id" not in push_dali),
        "push_dali=%r" % (push_dali.strip()[:80],)))

    # P5 (K339-EK ⑥) — yorem blogu OLCEN KOLA bagli: hem bu dosyaya ATIF tasir,
    # hem zarar sinifini DOGRU yazar ("hukum orani"; "yalnizca gecikme" DEGIL).
    atif = "OLCEN KOL -> tools/serit-b-hukum-test.py" in ham
    sinif = "hukum ureten kosum orani" in ham.lower()
    iddia.append((
        "P5 (K339-EK ⑥) kuyruk-iptali yorumu OLCEN KOLA bagli (atif + zarar sinifi)",
        bool(atif and sinif),
        "atif=%s zarar_sinifi_cumlesi=%s" % (atif, sinif)))
    return iddia


# ── CANLI KOL ────────────────────────────────────────────────────────────────
def _jeton():
    for ad in ("GITHUB_TOKEN", "GH_TOKEN"):
        deger = (os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return None


def api_getir(yol, zaman_asimi=25):
    url = "%s/%s" % (API, yol.lstrip("/"))
    istek = urllib.request.Request(url, method="GET")
    istek.add_header("Accept", "application/vnd.github+json")
    istek.add_header("X-GitHub-Api-Version", "2022-11-28")
    istek.add_header("User-Agent", "pruvo-serit-b-hukum-test")
    jeton = _jeton()
    if jeton:
        istek.add_header("Authorization", "Bearer %s" % jeton)
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            ham = y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise OlcumHatasi("GitHub API HTTP %s: %s%s" % (e.code, url,
                          "" if jeton else "  (jeton YOK — anonim kota 60/saat)"))
    except Exception as e:  # noqa: BLE001
        raise OlcumHatasi("GitHub API cagrilamadi (%s: %s): %s" % (type(e).__name__, e, url))
    try:
        return json.loads(ham)
    except Exception as e:  # noqa: BLE001
        raise OlcumHatasi("GitHub API yaniti JSON degil (%s): %s" % (e, url))


def canli_kosumlar(adet=100, getir=api_getir):
    """SERIT B is akisinin son `adet` kosumu (EN YENI ONCE). `getir` ENJEKTE
    EDILEBILIR: fikstur kolu GERCEK govde seklini besler."""
    liste = getir("repos/%s/actions/workflows?per_page=100" % DEPO)
    akislar = (liste or {}).get("workflows")
    if not isinstance(akislar, list):
        raise OlcumHatasi("is akisi listesi cozulemedi (govde sekli beklenenden farkli)")
    hedef = [w for w in akislar if (w or {}).get("name") == IS_AKISI_ADI]
    if not hedef:
        raise OlcumHatasi("SERIT B is akisi API listesinde YOK: %r" % (IS_AKISI_ADI,))
    kimlik = hedef[0].get("id")
    govde = getir("repos/%s/actions/workflows/%s/runs?per_page=%d"
                  % (DEPO, kimlik, min(int(adet), 100)))
    kosumlar = (govde or {}).get("workflow_runs")
    if not isinstance(kosumlar, list):
        raise OlcumHatasi("kosum listesi cozulemedi (govde sekli beklenenden farkli)")
    return [{"event": k.get("event"), "conclusion": k.get("conclusion"),
             "status": k.get("status")} for k in kosumlar]


# ── KAPI ─────────────────────────────────────────────────────────────────────
def kosum(yol, canli, getir=api_getir):
    fail, gecen = 0, 0
    cikti = []

    def iddia(ad, tamam, not_=""):
        nonlocal fail, gecen
        if tamam:
            gecen += 1
            cikti.append("  PASS %s%s" % (ad, ("  [%s]" % not_) if not_ else ""))
        else:
            fail += 1
            cikti.append("  FAIL %s  [%s]" % (ad, not_))

    cikti.append("POLITIKA (nobet.yml eszamanlilik sozlesmesi)")
    for ad, tamam, not_ in politika_iddialari(yol):
        iddia(ad, tamam, not_)

    cikti.append("SAYAC (fikstur kolu — tabanlar K339/K339-EK kaleminden ve 16 Eyl olcumunden)")
    o_yorum = hukum_ozeti(F_YORUM)
    cikti.append("  " + sayac_satiri(o_yorum, "K339-EK yorum tabani 10 Agu"))
    iddia("S1 yorum tabani (12'de 8 iptal) hukum orani %33 olarak okunur",
          o_yorum["tamamlanan"] == 12 and o_yorum["hukum"] == 4,
          "hukum=%d/%d" % (o_yorum["hukum"], o_yorum["tamamlanan"]))

    o_k339 = hukum_ozeti(F_K339)
    cikti.append("  " + sayac_satiri(o_k339, "K339 tabani 28 Agu"))
    iddia("S2 K339 tabani (25 kosum · 0 success) hukum uretmeyen seriyi SIFIR-DISI basar",
          o_k339["hukum"] == 8 and o_k339["iptal"] == 15 and o_k339["hukumsuz_seri"] > 0,
          "hukum=%d iptal=%d seri=%d" % (o_k339["hukum"], o_k339["iptal"],
                                         o_k339["hukumsuz_seri"]))

    o_bugun = hukum_ozeti(F_BUGUN)
    cikti.append("  " + sayac_satiri(o_bugun, "16 Eyl 2026 olcumu n=200"))
    cikti.extend(kol_satirlari(o_bugun))
    iddia("S3 16 Eyl penceresi: toplam hukum orani %38, push kolu %32 (BILGI — rc'yi "
          "belirlemez)",
          o_bugun["hukum"] == 76 and o_bugun["tamamlanan"] == 198,
          "hukum=%d/%d" % (o_bugun["hukum"], o_bugun["tamamlanan"]))

    o_ardisik = hukum_ozeti(F_ARDISIK_IPTAL)
    iddia("S4 MUTANT VAKASI (K339 ③): ardisik iki push iptali -> OLCULEMEDI kovasi "
          "dolar VE sayac artar",
          o_ardisik["iptal"] == 2 and o_ardisik["hukumsuz_seri"] == 2,
          sayac_satiri(o_ardisik, "ardisik-iptal"))

    o_tek = hukum_ozeti(F_TEK_HUKUM)
    iddia("S5 KONTROL (K339 ③): iptal OLMAYAN tek kosumda hukum NORMAL okunur (kol "
          "her seyi OLCULEMEDI'ye ceviren tikac DEGIL)",
          o_tek["hukum"] == 1 and o_tek["hukumsuz_seri"] == 0 and o_tek["iptal"] == 0,
          sayac_satiri(o_tek, "tek-hukum"))

    # S6 — SESSIZ SIFIR YASAGI: 0 ile n AYNI satirdan okunur.
    s_sifir, s_dolu = sayac_satiri(o_tek, "x"), sayac_satiri(o_ardisik, "x")
    iddia("S6 (K339 ②) sayac satiri 0 ile n icin AYNI bicimde basilir (sessiz sifir yok)",
          "HUKUMSUZ_SERI=0" in s_sifir and "HUKUMSUZ_SERI=2" in s_dolu,
          "sifir=%r" % (s_sifir.split("  ")[0],))

    # S7 — HEAD GARANTILI KOL ESIGI (mimar karari 7 Eyl: olcut budur).
    iddia("S7 HEAD garantili kol (%s) 16 Eyl fiksturunde esigi GECER (>= %.0f%%)"
          % (HEAD_KOLU, ESIK_HEAD_ORANI * 100),
          head_esigi_gecti(o_bugun) is True,
          "oran=%s" % ((o_bugun["kollar"].get(HEAD_KOLU) or {}).get("oran"),))

    # S8 — ESIK OLU MU? Esigin ALTINDA bir HEAD kolu fiksturu KIRMIZI okunmali.
    # Bu kol olmadan `ESIK_HEAD_ORANI`'yi 0'a indiren bir degisiklik sessizce
    # gecerdi (mutant M8 tam bunu dener).
    o_dusuk = hukum_ozeti(F_HEAD_DUSUK)
    cikti.append("  " + sayac_satiri(o_dusuk, "HEAD kolu esik-alti fiksturu"))
    iddia("S8 esik OLU DEGIL: HEAD kolu %%60 oranli fiksturde esik DUSER"
          % (),
          head_esigi_gecti(o_dusuk) is False,
          "oran=%s esik=%.2f" % ((o_dusuk["kollar"].get(HEAD_KOLU) or {}).get("oran"),
                                 ESIK_HEAD_ORANI))

    cikti.append("CANLI KOL (gercek kosum listesi)")
    if not canli:
        # 🔴 Sessiz atlama YOK: kol ADIYLA "kosulmadi" basar.
        cikti.append("  KOSULMADI: --canli verilmedi (CI kolu: nobet.yml :: cron-nabzi "
                     "job'u, `actions: read` + GITHUB_TOKEN)")
    else:
        kosumlar = canli_kosumlar(getir=getir)      # OlcumHatasi -> rc=2
        ozet = hukum_ozeti(kosumlar)
        cikti.append("  " + sayac_satiri(ozet, "CANLI n=%d" % ozet["toplam"]))
        cikti.extend(kol_satirlari(ozet))
        head = ozet["kollar"].get(HEAD_KOLU) or {}
        hukum_var = head_esigi_gecti(ozet)
        if hukum_var is None:
            raise OlcumHatasi(
                "CANLI: HEAD garantili kol (%s) penceresinde tamamlanmis kosum %d < %d "
                "-> oran OLCULEMEZ (sessiz yesil YOK)"
                % (HEAD_KOLU, head.get("tamamlanan", 0), ASGARI_HEAD_KOSUM))
        iddia("S9 CANLI: HEAD garantili kol (%s) hukum orani >= %.0f%%"
              % (HEAD_KOLU, ESIK_HEAD_ORANI * 100),
              hukum_var,
              "oran=%.0f%% (%d/%d)" % (head["oran"] * 100, head["hukum"],
                                       head["tamamlanan"]))

    print("\n".join(cikti))
    print("\n%d iddia kosturuldu (PASS=%d FAIL=%d)" % (gecen + fail, gecen, fail))
    if fail:
        print("SONUC: KIRMIZI ❌  (%d iddia dustu)" % fail)
        return 1
    print("SONUC: YESIL ✅")
    return 0


# ── MUTASYON BATARYASI ───────────────────────────────────────────────────────
# Her mutant IZOLE KOPYAYA uygulanir: gercek nobet.yml ve gercek tools/ agaci
# DEGISMEZ. Hedef kol ADIYLA yazilir ([[hedef-kol-atfi]]).
KENDI = os.path.basename(os.path.abspath(__file__))
# Bunun ALTINA dusen mutant kosumu "kirmizi" degil COKME'dir: kapi erken cikip
# birkac iddia basarak "olduruldum" gorunmesin. Saglam kosumda 13 iddia basilir
# (P1..P5 + S1..S8; CANLI kol `--canli` olmadan iddia BASMAZ, ADIYLA "kosulmadi" der).
TABAN_IDDIA = 13
MUTANTLAR = [
    ("OLDURUCU M1 (P1 · K339 kok nedeni) eszamanlilik grubunu SABIT TEK KOVAYA dondur",
     "is-akisi",
     "  group: nobet-serit-b-${{ github.event_name == 'workflow_dispatch' && "
     "github.run_id || github.event_name == 'schedule' && 'schedule' || 'push' }}",
     "  group: nobet-serit-b", "KIRMIZI", "P1"),
    ("OLDURUCU M2 (P2) cancel-in-progress: true — ard arda push alarmi SESSIZLESTIRIR",
     "is-akisi",
     "  cancel-in-progress: false\n\njobs:",
     "  cancel-in-progress: true\n\njobs:", "KIRMIZI", "P2"),
    ("OLDURUCU M3 (P3) HEAD garantili hukum kolunu kaldir (schedule tetigi)",
     "is-akisi",
     "  schedule:\n    - cron: \"47 */4 * * *\"",
     "  # schedule kaldirildi (mutant)", "KIRMIZI", "P3"),
    ("OLDURUCU M4 (P4 · G9) push kolunu SHA'ya bagla (bu kalemde YASAK onarim)",
     "is-akisi",
     "&& 'schedule' || 'push' }}",
     "&& 'schedule' || github.sha }}", "KIRMIZI", "P4"),
    ("OLDURUCU M5 (P5 · K339-EK ⑥) yorumdan OLCEN KOL atfini dusur",
     "is-akisi",
     "OLCEN KOL -> tools/serit-b-hukum-test.py",
     "OLCEN KOL -> (yok)", "KIRMIZI", "P5"),
    # 🔴 KENDI KAYNAGINI mutasyona ugratan capalar TEK SATIR OLAMAZ: tablodaki
    # dizge kaynakta birebir dursaydi `count(eski)` 2 olur ve mutant "CAPA-YOK"a
    # duserdi. O yuzden her capa GERCEK bir satir sonu (`\n`) tasir — tabloda
    # kacisli (`\n`), kaynakta gercek — ve dosyada TEK kez eslesir.
    ("OLDURUCU M6 (S1/S2) `cancelled`'i HUKUM say — K339 kabul ①'i bozar",
     "kendi",
     'HUKUM_SONUCLARI = ("success", "failure")\n',
     'HUKUM_SONUCLARI = ("success", "failure", "cancelled")\n', "KIRMIZI", "S1"),
    ("OLDURUCU M7 (S4/S6) HUKUMSUZ_SERI sayacini DAIMA 0 bas (sessiz sifir)",
     "kendi",
     "    seri = 0\n    for k in kosumlar:",
     "    seri = 0\n    for k in []:", "KIRMIZI", "S4"),
    ("OLDURUCU M8 (S8) HEAD garantili kol esigini 0'a indir — esik OLU MU?",
     "kendi",
     "ESIK_HEAD_ORANI = 0.80\n",
     "ESIK_HEAD_ORANI = 0.00\n", "KIRMIZI", "S8"),
    ("KONTROL K1 is akisinda davranissiz yazim (yorum bosluğu) — YESIL kalmali",
     "is-akisi",
     "concurrency:\n  group: nobet-serit-b-",
     "concurrency:\n\n  group: nobet-serit-b-", "YESIL", "-"),
    ("KONTROL K2 kendi kaynaginda davranissiz yazim (bos sozluk yazimi) — YESIL kalmali",
     "kendi",
     "    kollar = {}\n",
     "    kollar = dict()\n", "YESIL", "-"),
]


def mutasyon():
    tmp = tempfile.mkdtemp(prefix="serit-b-hukum-mutasyon-")
    sonuc = []
    try:
        taban_akis = open(IS_AKISI, encoding="utf-8").read()
        taban_kendi = open(os.path.abspath(__file__), encoding="utf-8").read()
        for ad, hedef, eski, yeni, beklenen, kol in MUTANTLAR:
            taban = taban_akis if hedef == "is-akisi" else taban_kendi
            if taban.count(eski) != 1:
                # Capa kaymis: "uygulanamadi" YESIL sayilmaz.
                sonuc.append((ad, kol, beklenen, "CAPA-YOK(%d)" % taban.count(eski)))
                continue
            oda = os.path.join(tmp, str(len(sonuc)))
            os.makedirs(oda)
            akis_yolu = os.path.join(oda, "nobet.yml")
            kendi_yolu = os.path.join(oda, KENDI)
            with open(akis_yolu, "w", encoding="utf-8") as f:
                f.write(taban_akis.replace(eski, yeni, 1) if hedef == "is-akisi"
                        else taban_akis)
            with open(kendi_yolu, "w", encoding="utf-8") as f:
                f.write(taban_kendi.replace(eski, yeni, 1) if hedef == "kendi"
                        else taban_kendi)
            r = subprocess.run([sys.executable, kendi_yolu, "--is-akisi", akis_yolu],
                               capture_output=True, text=True, cwd=oda)
            cikti = r.stdout + r.stderr
            fail = len(re.findall(r"^ *FAIL ", cikti, re.M))
            gecen = len(re.findall(r"^ *PASS ", cikti, re.M))
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d: %s)" % (r.returncode,
                                               cikti.strip().split("\n")[-1][:90])
            elif r.returncode == 1 and fail == 0:
                gozlem = "COKME(kirmizi ama olculen iddia yok)"
            elif gecen + fail < TABAN_IDDIA:
                gozlem = "COKME(olculen iddia sayisi dusuk: %d)" % (gecen + fail)
            elif r.returncode == 1 and kol != "-" and not re.search(
                    r"^ *FAIL %s" % re.escape(kol.split("/")[0]), cikti, re.M):
                # HEDEF-KOL ATFI: kirmizi DOGRU kolda mi? Baska bir kol dustuyse
                # mutant "olduruldu" sayilmaz.
                gozlem = "YANLIS-KOL(hedef=%s, dusen=%s)" % (
                    kol, ",".join(re.findall(r"^ *FAIL (\S+)", cikti, re.M))[:60])
            else:
                gozlem = "KIRMIZI" if r.returncode == 1 else "YESIL"
            sonuc.append((ad, kol, beklenen, "%s (FAIL=%d PASS=%d)" % (gozlem, fail, gecen)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kapi: tools/%s · is akisi: %s)"
          % (KENDI, os.path.relpath(IS_AKISI, ROOT)))
    kalan = 0
    for ad, kol, beklenen, gozlem in sonuc:
        tamam = gozlem.startswith(beklenen)
        kalan += 0 if tamam else 1
        print("  %s  %-86s hedef-kol=%-12s beklenen=%s  gozlenen=%s"
              % ("OK  " if tamam else "KALDI", ad, kol, beklenen, gozlem))
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen sonucu vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU hedef kolunda kirmizi, her "
          "KONTROL yesil)" % len(sonuc))
    return 0


def main():
    ap = argparse.ArgumentParser(description="SERIT B hukum orani kapisi (K339/K339-EK)")
    ap.add_argument("--is-akisi", default=IS_AKISI, help="olculecek is akisi dosyasi")
    ap.add_argument("--canli", action="store_true",
                    help="GERCEK kosum listesini GitHub API'sinden oku")
    ap.add_argument("--mutasyon", action="store_true", help="mutasyon bataryasi")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    try:
        return kosum(a.is_akisi, a.canli)
    except OlcumHatasi as e:
        print("OLCULEMEDI: %s" % e)
        print("SONUC: OLCULEMEDI ⛔  (fail-closed; sessiz yesil YOK)")
        return 2


if __name__ == "__main__":
    sys.exit(main())

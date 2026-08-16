#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN YASI NOBETCISI — "main'de yayina GIRMEMIS en eski commit KAC SAATTIR bekliyor?"

NEDEN VAR (15-16 Agu 2026, OLCULDU — bu nobetci bir olayin faturasidir)
=======================================================================
Yayin **15 Agu 14:02'den 16 Agu ~12:00'ye kadar (~21 saat) KAPALIYDI** ve
HICBIR NOBETCI GORMEDI. Son basarili dagitim `268da994`; uzerine **22 commit**
birikti (K117 model kanonu, uc urun partisi, ic link hatti) ve hicbiri musteriye
gitmedi. Bes ev calisti, kimse fark etmedi.

🔴 SESSIZLIGIN MEKANIGI: `deploy.yml`'de `deploy` isi
`needs: [build, serit-a2, serit-a3, serit-a4]` ile fail-closed baglidir. Onlardan
biri kirmizi olunca `deploy` **SKIPPED** olur — ve **SKIPPED SESSIZDIR**:
  * kosumun kendi `conclusion`'i cogu zaman `success`/`failure` olarak okunur,
  * GitHub "yayin yapilmadi" diye AYRI bir bildirim URETMEZ,
  * kirmizi CI listesinde tek bir satir olarak kaybolur.
Yani **kosumun yesili yayin DEMEK DEGILDIR**. Bu betik bu yuzden kosum
`conclusion`'ina BAKMAZ; `github-pages` ORTAMINA DUSEN GERCEK DAGITIM KAYDINI
okur (yoksa yayin OLMAMISTIR — beyan degil, kayit).

🔴 NEDEN "SON DAGITIMIN YASI" DEGIL DE "YAYINA GIRMEMIS EN ESKI COMMIT'IN YASI"
==============================================================================
Sessiz gece = kusur DEGILDIR. main hic ilerlemediyse dagitimin 30 saatlik olmasi
saglikli bir durumdur; boyle bir esik her sakin gece yanlis alarm verir ve
kanikstirir. Olculen kusur "dagitim eski" degil **"main ilerledi, canli KALDI"**
idi. Olculen buyukluk bu yuzden:

    yas = simdi − (dagitilan SHA'dan SONRAKI EN ESKI commit'in tarihi)

  * main == dagitilan SHA  -> yas TANIMSIZ degil, **0**; ne kadar zaman gecerse
    gecsin YESIL (yayinlanacak bir sey yok).
  * main ilerledi          -> saat isler; TAVAN_SAAT'i asinca KIRMIZI.
  * Ara commit'ler tek tek dagitilmaz (Pages `concurrency` ara kosumlari iptal
    eder, agaci dagitir) — bu yuzden **commit SAYISI tek basina kirmizi degildir**
    (saglikli bir yigin da 12 commit birikebilir); sayi RAPORLANIR, hukum YASTAN.

🔴 PENCERE-GORELI OLCUM YASAK ([[pencere-goreli-alarm-kendini-sonduruyor]])
==========================================================================
"Son N kosumun icinde basarili dagitim var mi" bicimindeki her olcum kendini
sondurur: yayin uzun sure kapali kalinca basarili dagitim pencereden CIKAR ve
alarm "olculemedi"ye ya da sessiz yesile duser. Burada olcu MUTLAK ZAMANDIR
(UTC damgalari) ve dagitim kaydi bulunamazsa hukum **rc 2**'dir, yesil DEGIL.

CIKIS KODLARI (fail-closed)
===========================
  rc 0  ACIK        — canli main ucuyla ayni, ya da bekleyen en eski commit taze.
  rc 1  BAYAT       — yayina girmemis en eski commit TAVAN_SAAT'ten yasli.
  rc 2  OLCULEMEDI  — jeton/API/kayit yok, dagitilan SHA main gecmisinde degil,
                      tarih ayristirilamadi, saat geriye kacmis. **SESSIZ YESIL DEGIL.**

KAPSAM SINIRI (bilerek DAR)
===========================
Bu nobetci "yayin AKTI MI" sorusunu sorar. "Yayinlanan sayfa musteride ACIK MI"
`tools/yayin-erisim-nobeti.py`; "D1 taslak yigini" `tools/yayin-gecikme-nobeti.py`.
🔴 Ikisi de bu sinifi GORMEZ: erisim nobetcisi kumeyi main AGACINDAN turetir ve
canli sitemap'te henuz olmayan 404'leri ROLLOUT sayar — yani yayin tamamen
durdugunda tam olarak SESSIZLESIR. Bu betik o kor noktanin karsiligidir.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

# ═══════════════════════════════════════════════════════════════════ SABITLER
# 🔴 TEK KAYNAK — ESIK. Olculen olay 21 saat surdu; 3 saat o pencereyi 7x daraltir
# ve saglikli en uzun yayin turundan (kuyruk + D1 yazici lease bekleyisi dahil
# olculen en kotu tur ~35 dk) hala ~5x genistir: gecici yavaslama KIRMIZI YAKMAZ.
TAVAN_SAAT = 3.0

# Pages dagitimlarinin dustugu ortam adi. Kayit YOKSA yayin OLMAMISTIR.
ORTAM = "github-pages"

# Bir dagitimin "yayin oldu" sayilmasi icin durum kaydinda aranan tek deger.
# `inactive`/`in_progress`/`failure`/`error` YAYIN DEGILDIR (fail-closed).
BASARI_DURUMU = "success"

API_TABAN = "https://api.github.com"
ZAMAN_ASIMI = 20
UA = "pruvo-yayin-yasi-nobetcisi"

# Dagitim listesinde geriye dogru en fazla kac kayit yoklanir. Yalniz API
# maliyeti icindir: TUKENIRSE hukum rc 2'dir (sessiz yesil DEGIL).
DAGITIM_TAVANI = 50

SINIF_RC = {"ACIK": 0, "BAYAT": 1, "OLCULEMEDI": 2}


class OlcumHatasi(Exception):
    """Olculemedi -> YESIL degil, rc 2."""


# ═════════════════════════════════════════════════════════════ ZAMAN (SAF)
def zaman_ayristir(metin):
    """ISO-8601 UTC damgasi -> aware datetime. Ayristirilamazsa OlcumHatasi."""
    if not isinstance(metin, str) or not metin.strip():
        raise OlcumHatasi("zaman damgasi BOS")
    ham = metin.strip()
    if ham.endswith("Z"):
        ham = ham[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(ham)
    except ValueError:
        raise OlcumHatasi("zaman damgasi ayristirilamadi: %r" % metin)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def _sure_metni(saniye):
    if saniye is None:
        return "-"
    dk = int(round(saniye / 60.0))
    return "%d sa %02d dk" % (dk // 60, dk % 60)


# ═════════════════════════════════════════════════════════════ HUKUM (SAF)
def degerlendir(dagitim, kiyas, simdi, tavan_saat=TAVAN_SAAT):
    """(sinif, rc, satirlar, ozet) — AG YOK, saf fonksiyon.

    `dagitim`: {"sha", "olusma"(datetime), "id"} — son BASARILI Pages dagitimi.
    `kiyas`  : {"durum", "ileri", "geri", "en_eski"(datetime|None), "en_eski_sha"}
               — dagitilan SHA ile dalin ucu arasindaki fark (GitHub compare).
    `simdi`  : olcum ani (aware datetime).
    """
    ozet = {"dagitim_sha": (dagitim or {}).get("sha"),
            "dagitim_yasi_sn": None, "bekleyen": None, "yas_sn": None,
            "tavan_sn": tavan_saat * 3600.0, "en_eski_sha": None, "durum": None}

    if not dagitim or not dagitim.get("sha") or not dagitim.get("olusma"):
        return ("OLCULEMEDI", 2,
                ["🔴 %s ortaminda BASARILI dagitim kaydi YOK -> yayin akip akmadigi "
                 "OLCULEMEDI (bos kayit 'yayin acik' DEMEK DEGILDIR)." % ORTAM], ozet)

    durum = (kiyas or {}).get("durum")
    ozet["durum"] = durum
    ozet["dagitim_yasi_sn"] = (simdi - dagitim["olusma"]).total_seconds()
    ileri = (kiyas or {}).get("ileri")
    ozet["bekleyen"] = ileri

    # 🔴 DAGITILAN SHA DALIN GECMISINDE DEGIL: force-push / yabanci dal / bozuk
    # kiyas. Bu durumda "kac commit geride" sorusunun ANLAMI YOK -> rc 2.
    if durum in ("behind", "diverged"):
        return ("OLCULEMEDI", 2,
                ["🔴 dagitilan SHA (%s) dalin gecmisinde DEGIL (compare durumu: %s) -> "
                 "yayin yasi tanimsiz. Force-push ya da yabanci dal dagitimi olabilir."
                 % (str(ozet["dagitim_sha"])[:8], durum)], ozet)
    if durum not in ("identical", "ahead"):
        return ("OLCULEMEDI", 2,
                ["🔴 kiyas durumu BILINMIYOR (%r) -> hukum verilemez." % (durum,)], ozet)

    if durum == "identical" or ileri == 0:
        ozet["yas_sn"] = 0.0
        return ("ACIK", 0,
                ["✔ canli dagitim dalin ucuyla AYNI (%s) — yayina girmemis commit YOK."
                 % str(ozet["dagitim_sha"])[:8],
                 "   son dagitim yasi: %s (main ilerlemedigi surece bu SAYI KUSUR DEGIL)."
                 % _sure_metni(ozet["dagitim_yasi_sn"])], ozet)

    if not isinstance(ileri, int) or ileri < 0:
        return ("OLCULEMEDI", 2,
                ["🔴 bekleyen commit sayisi okunamadi (%r) -> hukum verilemez." % (ileri,)],
                ozet)

    en_eski = (kiyas or {}).get("en_eski")
    if en_eski is None:
        return ("OLCULEMEDI", 2,
                ["🔴 %d commit yayina girmemis ama EN ESKISININ TARIHI okunamadi -> "
                 "yas olculemedi (tarihsiz bekleyen commit 'taze' SAYILMAZ)." % ileri],
                ozet)

    yas = (simdi - en_eski).total_seconds()
    ozet["yas_sn"] = yas
    ozet["en_eski_sha"] = (kiyas or {}).get("en_eski_sha")

    # 🔴 SAAT GERIYE KACMIS / GELECEK TARIHLI COMMIT: negatif yas bir OLCUM
    # arizasidir; "cok taze" diye yesile cevrilmez.
    if yas < 0:
        return ("OLCULEMEDI", 2,
                ["🔴 bekleyen en eski commit GELECEK tarihli (yas %.0f sn) -> saat/damga "
                 "arizasi, hukum verilemez." % yas], ozet)

    kim = "%s%s" % (str(ozet["en_eski_sha"] or "")[:8],
                    "" if ozet["en_eski_sha"] else "(sha yok)")
    if yas >= ozet["tavan_sn"]:
        return ("BAYAT", 1,
                ["🔴 YAYIN BAYAT: %d commit yayina girmemis; en eskisi (%s) **%s**tir "
                 "bekliyor (tavan %.1f sa)."
                 % (ileri, kim, _sure_metni(yas), tavan_saat),
                 "   son basarili dagitim: %s · %s once."
                 % (str(ozet["dagitim_sha"])[:8], _sure_metni(ozet["dagitim_yasi_sn"])),
                 "   🔴 `deploy` isi SKIPPED olmus olabilir (needs zinciri kirmizi): "
                 "kosum listesinde YESIL gorunur ama YAYIN AKMAZ."], ozet)

    return ("ACIK", 0,
            ["✔ %d commit yayin sirasinda; en eskisi (%s) %s bekliyor — tavan %.1f sa."
             % (ileri, kim, _sure_metni(yas), tavan_saat),
             "   son basarili dagitim: %s · %s once."
             % (str(ozet["dagitim_sha"])[:8], _sure_metni(ozet["dagitim_yasi_sn"]))], ozet)


# ═══════════════════════════════════════════════════════════ API (KENAR KATMAN)
def _jeton(cevre=None):
    cevre = os.environ if cevre is None else cevre
    for ad in ("GITHUB_TOKEN", "GH_TOKEN"):
        d = (cevre.get(ad) or "").strip()
        if d:
            return d
    try:
        p = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                           timeout=15)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.strip()
    except Exception:                                           # noqa: BLE001
        pass
    raise OlcumHatasi("GitHub jetonu YOK (GITHUB_TOKEN/GH_TOKEN/`gh auth token`) -> "
                      "dagitim kaydi okunamaz")


def _depo(cevre=None, kok=ROOT):
    cevre = os.environ if cevre is None else cevre
    d = (cevre.get("GITHUB_REPOSITORY") or "").strip()
    if d:
        return d
    try:
        p = subprocess.run(["git", "-C", kok, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=15)
        m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?\s*$", p.stdout or "")
        if p.returncode == 0 and m:
            return m.group(1)
    except Exception:                                           # noqa: BLE001
        pass
    raise OlcumHatasi("depo adi cozulemedi (GITHUB_REPOSITORY yok, origin okunamadi)")


def _api(yol, jeton, taban=API_TABAN, zaman_asimi=ZAMAN_ASIMI):
    """GET -> ayristirilmis JSON. Her arizada OlcumHatasi (asla sessiz bos liste)."""
    istek = urllib.request.Request(
        taban.rstrip("/") + yol,
        headers={"Authorization": "Bearer %s" % jeton,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            return json.loads(y.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raise OlcumHatasi("API %s -> HTTP %s" % (yol, e.code))
    except Exception as e:                                      # noqa: BLE001
        raise OlcumHatasi("API %s -> %s: %s" % (yol, type(e).__name__, e))


def son_basarili_dagitim(depo, jeton, api=None, ortam=ORTAM, tavan=DAGITIM_TAVANI):
    """github-pages ortamindaki SON BASARILI dagitim -> {"sha","olusma","id"}.

    🔴 Kosum `conclusion`'ina BAKILMAZ: olculen olayda `deploy` isi SKIPPED iken
    kosum listesi yaniltici gorunuyordu. Tek kanit DAGITIM DURUM KAYDIDIR."""
    api = api or (lambda yol: _api(yol, jeton))
    kayitlar = api("/repos/%s/deployments?environment=%s&per_page=%d"
                   % (depo, ortam, min(tavan, 100)))
    if not isinstance(kayitlar, list):
        raise OlcumHatasi("dagitim listesi beklenmedik bicimde (%s)" % type(kayitlar).__name__)
    if not kayitlar:
        raise OlcumHatasi("%s ortaminda HIC dagitim kaydi yok" % ortam)
    for kayit in kayitlar[:tavan]:
        durumlar = api("/repos/%s/deployments/%s/statuses?per_page=100"
                       % (depo, kayit.get("id")))
        if not isinstance(durumlar, list):
            raise OlcumHatasi("dagitim %s durum listesi bozuk" % kayit.get("id"))
        if any((d or {}).get("state") == BASARI_DURUMU for d in durumlar):
            return {"sha": kayit.get("sha"), "id": kayit.get("id"),
                    "olusma": zaman_ayristir(kayit.get("created_at"))}
    raise OlcumHatasi("son %d dagitim kaydinin HICBIRI '%s' durumuna ulasmamis -> "
                      "yayin akmiyor (ya da pencere yetersiz): rc 2"
                      % (min(len(kayitlar), tavan), BASARI_DURUMU))


def kiyasla(depo, jeton, taban_sha, dal="main", api=None):
    """compare(taban_sha...dal) -> {"durum","ileri","geri","en_eski","en_eski_sha"}."""
    api = api or (lambda yol: _api(yol, jeton))
    c = api("/repos/%s/compare/%s...%s" % (depo, taban_sha, dal))
    if not isinstance(c, dict) or "status" not in c:
        raise OlcumHatasi("compare yaniti bozuk")
    commitler = c.get("commits") or []
    en_eski = None
    en_eski_sha = None
    if commitler:
        ilk = commitler[0] or {}
        en_eski_sha = ilk.get("sha")
        cd = ((ilk.get("commit") or {}).get("committer") or {}).get("date")
        if cd:
            en_eski = zaman_ayristir(cd)
    return {"durum": c.get("status"), "ileri": c.get("ahead_by"),
            "geri": c.get("behind_by"), "en_eski": en_eski, "en_eski_sha": en_eski_sha}


def olc(dal="main", tavan_saat=TAVAN_SAAT, cevre=None, simdi=None):
    """Uctan uca olcum -> (sinif, rc, satirlar, ozet). OlcumHatasi'ni rc 2'ye cevirir."""
    simdi = simdi or datetime.now(timezone.utc)
    try:
        jeton = _jeton(cevre)
        depo = _depo(cevre)
        dagitim = son_basarili_dagitim(depo, jeton)
        kiyas = kiyasla(depo, jeton, dagitim["sha"], dal=dal)
    except OlcumHatasi as e:
        return ("OLCULEMEDI", 2, ["🔴 OLCULEMEDI: %s" % e],
                {"dagitim_sha": None, "yas_sn": None, "bekleyen": None,
                 "tavan_sn": tavan_saat * 3600.0, "durum": None,
                 "dagitim_yasi_sn": None, "en_eski_sha": None})
    return degerlendir(dagitim, kiyas, simdi, tavan_saat=tavan_saat)


# ═══════════════════════════════════════════════════════════════════ RAPOR
def gh_ozet_yaz(sinif, ozet, satirlar):
    """GitHub kosum ozeti + step output. Yan etkisi YOK: env yoksa sessiz."""
    cikti = os.environ.get("GITHUB_OUTPUT")
    if cikti:
        with open(cikti, "a", encoding="utf-8") as f:
            f.write("durum=%s\n" % sinif.lower())
            f.write("bekleyen=%s\n" % (ozet.get("bekleyen") if ozet.get("bekleyen")
                                       is not None else ""))
            f.write("yas_sn=%s\n" % (int(ozet["yas_sn"]) if ozet.get("yas_sn")
                                     is not None else ""))
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write("## Yayin yasi nobeti — %s\n\n" % sinif)
            f.write("* yayina girmemis commit: **%s** · en eskisinin yasi: **%s** · "
                    "tavan: **%.1f sa**\n"
                    % (ozet.get("bekleyen"), _sure_metni(ozet.get("yas_sn")),
                       (ozet.get("tavan_sn") or 0) / 3600.0))
            f.write("* son basarili `%s` dagitimi: `%s` (%s once)\n\n"
                    % (ORTAM, str(ozet.get("dagitim_sha") or "-")[:8],
                       _sure_metni(ozet.get("dagitim_yasi_sn"))))
            for s in satirlar:
                f.write("%s\n" % s)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Yayin yasi nobetcisi")
    ap.add_argument("--dal", default="main")
    ap.add_argument("--tavan-saat", type=float, default=TAVAN_SAAT)
    ap.add_argument("--gh-ozet", action="store_true",
                    help="GitHub kosum ozeti + step output yaz")
    a = ap.parse_args(argv)

    sinif, rc, satirlar, ozet = olc(dal=a.dal, tavan_saat=a.tavan_saat)
    print("YAYIN YASI NOBETCISI — %s" % sinif)
    for s in satirlar:
        print(s)
    print("SONUC: %s (rc=%d)" % (sinif, rc))
    if a.gh_ozet:
        gh_ozet_yaz(sinif, ozet, satirlar)
    return rc


if __name__ == "__main__":
    sys.exit(main())

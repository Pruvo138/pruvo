#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EDGE_KATALOG FLIP — GO/NO-GO HAZIRLIK KAPISI (tek komut, salt-okuma).

    python3 tools/edge-flip-hazirlik.py

Politika: tools/edge-katalog-tetik.md. Birincil metrik = urunler.json dizi uzunlugu.
Esikler: 10.000 HAZIRLIK / 12.000 FLIP / 14.000 MECBURI.

BU ARAC FLIP YAPMAZ. index.html'deki EDGE_KATALOG bayragini yalnizca OKUR (degistirmez).
Asil flip (false->true) MUHENDIS elinden gecer; bu kapi sadece "bugun flip'e hazir miyiz?"
sorusunu adim-adim OLCEREK cevaplar ve genel GO / NO-GO verir.

Flip provasi (edge-katalog-tetik.md §"Flip provasi" sirasi):
  1. [HocA/Okan kapisi] Worker /katalog ucu CANLI mi (anlamli JSON)
  2. node faz3-sayfalama.js + faz3-gecikme.js yesil mi
  3. node parite-test.js + parite-ege.js yesil mi (CDN onbellek: nonce ile)
  4. python3 d1-sync.py --durum exit 0 mi (fail-loud drift teyidi)
  5. index.html EDGE_KATALOG guncel degeri (OKUNUR, degistirilmez)

SALT-OKUMA GUVENCESI:
  - urunler.json / .urun-kaynaklari.json / index.html YALNIZCA okunur.
  - d1-sync.py SADECE --durum ile calisir (asla yazma yolu).
  - worker'a yalniz GET atilir; her cagride zaman asimi vardir.
  - build.py ve enjeksiyon-kapisi.py HIC cagrilmaz (checkout'u kirletirler).

MIMARI: adim-degerlendirme MANTIGI saf fonksiyonlardadir (girdi -> PASS/FAIL/BLOKLU),
canli I/O'dan bagimsiz. Boylece kabul testi (edge-flip-hazirlik-test.py) agsiz kosar.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")
INDEX = os.path.join(KOK, "index.html")
D1_SYNC = os.path.join(KOK, "tools", "d1-sync.py")
PARITE_EGE = os.path.join(KOK, "tools", "parite-ege.js")
PARITE_SITE = os.path.join(KOK, "tools", "parite-test.js")
FAZ3_SAYFALAMA = os.path.join(KOK, "tools", "faz3-sayfalama.js")
FAZ3_GECIKME = os.path.join(KOK, "tools", "faz3-gecikme.js")

# ── Esikler (edge-katalog-tetik.md) ──────────────────────────────────────────
ESIK_HAZIRLIK = 10000
ESIK_FLIP = 12000
ESIK_MECBURI = 14000

# ── Bant adlari (test bunlari kelimesi kelimesine karsilastirir) ──────────────
BANT_HAZIRLIK_ALTI = "hazırlık-altı"
BANT_FLIP_ALTI = "flip-altı"
BANT_FLIP_ERISILDI = "flip-erişildi"
BANT_MECBURI = "mecburi"

# ── Durum sabitleri ───────────────────────────────────────────────────────────
PASS = "PASS"
FAIL = "FAIL"
BLOKLU = "BLOKLU"

# Zaman asimlari (saniye)
ZA_WORKER = 15
ZA_D1 = 90
ZA_NODE = 300

BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# ═══════════════════════════════════════════════════════════════════════════════
# SAF FONKSIYONLAR — canli I/O YOK. Girdi al -> karar dondur. Test bunlari cagirir.
# Karar bicimi: (durum, kim, detay)   kim = None | "HocA" | "Okan"
# ═══════════════════════════════════════════════════════════════════════════════

def bant_hesapla(katalog_sayisi):
    """urunler.json uzunlugundan (bant, flip_mesafe) dondurur. flip_mesafe = 12.000'e
    kalan urun (>=12.000 ise 0). SAF."""
    try:
        n = int(katalog_sayisi)
    except (TypeError, ValueError):
        return (None, None)
    if n < ESIK_HAZIRLIK:
        bant = BANT_HAZIRLIK_ALTI
    elif n < ESIK_FLIP:
        bant = BANT_FLIP_ALTI
    elif n < ESIK_MECBURI:
        bant = BANT_FLIP_ERISILDI
    else:
        bant = BANT_MECBURI
    mesafe = max(0, ESIK_FLIP - n)
    return (bant, mesafe)


def deg_boyut(katalog_sayisi, d1_sayisi=None):
    """Adim 1 (boyut). FLIP esigine (12.000) ULASILDI mi? SAF.
    PASS  = bant flip-erisildi / mecburi (>=12.000)
    FAIL  = altinda (organik buyume beklenir; kimsenin 'blok'u degil)."""
    bant, mesafe = bant_hesapla(katalog_sayisi)
    if bant is None:
        return (FAIL, None, "katalog sayisi okunamadi")
    d1_not = ""
    if d1_sayisi is not None:
        d1_not = " | D1=%s" % d1_sayisi
    detay = "katalog=%s bant=%s flip'e kalan=%s%s" % (katalog_sayisi, bant, mesafe, d1_not)
    if bant in (BANT_FLIP_ERISILDI, BANT_MECBURI):
        return (PASS, None, detay)
    return (FAIL, None, detay + " (12.000 flip esigi erisilmedi)")


def deg_worker(durum_kodu, json_obj, ag_hata=False):
    """Adim 'worker /katalog'. Ege Worker'in /katalog ucu CANLI + anlamli JSON mu? SAF.
    Uc ayri repoda (pruvo-bot / HocA) ve deploy Okan/HocA kapisi -> canli degilse
    BLOKLU(HocA). 200 ama gecersiz govde -> FAIL (deploy var ama bozuk)."""
    if ag_hata or durum_kodu is None:
        return (BLOKLU, "HocA",
                "/katalog'a ulasilamadi (ag hatasi/zaman asimi) — uc canli degil")
    if durum_kodu in (403, 404):
        return (BLOKLU, "HocA",
                "/katalog HTTP %d — uc henuz deploy DEGIL (ayri repo pruvo-bot)" % durum_kodu)
    if durum_kodu != 200:
        return (FAIL, None, "/katalog HTTP %d (beklenmeyen)" % durum_kodu)
    if not isinstance(json_obj, dict) or ("urunler" not in json_obj and "toplam" not in json_obj):
        return (FAIL, None, "/katalog 200 dondu ama anlamli JSON degil (urunler/toplam yok)")
    return (PASS, None, "/katalog 200 + anlamli JSON (toplam=%s)" % json_obj.get("toplam"))


def deg_komut(dosya_var, exit_kodu, cikti=""):
    """faz3 / parite adimlari. Dosya yoksa BLOKLU; exit 0 -> PASS, exit 2/3 -> BLOKLU
    (OLCULEMEDI), diger nonzero -> FAIL. SAF.

    🔴 CIKIS KODU SOZLESMESI TEK KAYNAKTADIR: tools/parite-ortak.js dosya basindaki
    "CIKIS KODU SOZLESMESI" blogu (tablo burada TEKRARLANMAZ). Bu dosyanin sozlesmedeki
    YERI:  exit 3 -> BLOKLU (ATLANDI/OLCULEMEDI: GERILEME DEGIL, kimseyi suclamaz; ama
    GO da VERMEZ). Gerekce: yonetici ilke "olculemeyen hicbir sey YESILE donusemez" —
    PASS yazmak, parite KANITLANMADAN flip'e GO demek olurdu. FAIL yazmak ise yanlis
    suclama olur (kapi kirmizi yanar, kimse kodda bir sey bulamaz). BLOKLU tam olarak
    "1 > 3 > 0" siralamasinin ortasidir: FAIL > BLOKLU > PASS.
    exit 2 = "OLCULEMEDI/KOSULAMADI" bu depoda YERLESIK sozlesme:
      - faz3-gecikme.js : uc cevap vermiyor VEYA yanitta worker-ici sure alani yok
      - parite-ege.js   : bot kaynagi yok / fonksiyon yeniden adlandirilmis
    Eslemenin dordu birden tools/parite-sozlesme-test.py ile TEK TEK olculur.
    """
    if not dosya_var:
        return (BLOKLU, None, "test dosyasi bulunamadi")
    if exit_kodu == 0:
        return (PASS, None, "exit 0")
    if exit_kodu is None:
        return (FAIL, None, "kosum tamamlanmadi (zaman asimi/hata)")
    if exit_kodu == 2:
        return (BLOKLU, "HocA",
                "exit 2 — OLCULEMEDI (uc cevap vermiyor / yanitta alan yok); gerileme DEGIL")
    if exit_kodu == 3:
        return (BLOKLU, None, "exit 3 — ATLANDI/OLCULEMEDI: %s; gerileme DEGIL "
                              "(aciklanamayan ayrisim olsa exit 1 olurdu), ama parite "
                              "KANITLANMADIGI icin GO da VERMEZ" % parite3_neden(cikti))
    return (FAIL, None, "exit %s" % exit_kodu)


def parite3_neden(cikti):
    """exit 3'un GORUNUR sebebi, OLCULEN kanittan turetilir. SAF.

    ⚠️ 'checkout bayat' KESIN HUKUM olarak yazilmaz: ayni imza D1'deki YETIM satirdan da
    cikar (parite-ortak.js 'TESHIS DURUSTLUGU'). Sirasi ONEMLI: sert arizalar once."""
    c = cikti or ""
    if "FIKSTUR MODU" in c:
        return "FIKSTUR MODU (test-only env) — kanonik katalog/uc olculmedi"
    if "WAF/UA" in c:
        return "WAF/UA duvari (403) — canli uc olculemedi"
    if "HIZ SINIRI" in c:
        return "hiz siniri (429) — yeniden denemeler tukendi"
    if "ZAMAN ASIMI" in c:
        return "zaman asimi — canli uc susuyor"
    if "TAVAN" in c:
        return "supurme tavani asildi — 'yerel ⊆ D1' kaniti uretilemedi"
    m = re.search(r"D1 FAZLALIGI: yerel=(\d+) < canli=(\d+) \| fazla=(\d+)", c)
    if m:
        return ("katalog farki: yerel %s < canli %s (D1'de %s fazla satir); sebep AYIRT "
                "EDILEMEDI — dal bayat ya da D1'de yetim satir"
                % (m.group(1), m.group(2), m.group(3)))
    if "SENKRON GEC" in c:
        return "katalog farki (senkron gecikmesi ya da yetim satir)"
    return "olculemedi (sebep cikti'da bulunamadi)"


def deg_d1(exit_kodu, cikti=""):
    """Adim d1-durum. python3 d1-sync.py --durum exit 0 mi? SAF.
    Cikti'da kimlik hatasi (token D1 yetkisi yok) gorulurse -> BLOKLU(Okan);
    aksi nonzero -> FAIL (D1 drift: Ege bayat katalog gorur)."""
    c = cikti or ""
    if "KIMLIK HATASI" in c or "code: 10000" in c or "code 10000" in c or "Authentication error" in c:
        return (BLOKLU, "Okan",
                "D1 token'i D1'e erisemiyor (Account > D1 > Edit gerekli)")
    if exit_kodu == 0:
        return (PASS, None, "exit 0 — D1 == urunler.json benzersiz id")
    if exit_kodu is None:
        return (FAIL, None, "d1-sync --durum tamamlanmadi (zaman asimi)")
    return (FAIL, None, "exit %s — D1 senkron DRIFT (Ege bayat katalog gorebilir)" % exit_kodu)


def deg_bayrak(deger):
    """Adim bayrak. index.html EDGE_KATALOG guncel degerini raporlar (DEGISTIRMEZ). SAF.
    None (bulunamadi) -> FAIL. false -> PASS (flip oncesi normal). true -> PASS (zaten acik)."""
    if deger is None:
        return (FAIL, None, "EDGE_KATALOG index.html'de bulunamadi/okunamadi")
    if deger is False:
        return (PASS, None, "EDGE_KATALOG=false (flip oncesi normal; asil flip muhendis eliyle)")
    return (PASS, None, "EDGE_KATALOG=true (flip ZATEN yapilmis)")


def genel_karar(adimlar):
    """adimlar = [(ad, durum, kim, detay), ...]. Tumu PASS -> 'GO', aksi 'NO-GO'. SAF."""
    for a in adimlar:
        durum = a[1]
        if durum != PASS:
            return "NO-GO"
    return "GO"


def blokajlar(adimlar):
    """NO-GO ise engelleyen adimlarin (ad, durum, kim) listesi. SAF."""
    out = []
    for a in adimlar:
        ad, durum, kim = a[0], a[1], a[2]
        if durum != PASS:
            out.append((ad, durum, kim))
    return out


def ege_origin_turet(parite_ege_kaynak, env_ara_uc=None):
    """Ege Worker origin'ini parite-ege.js kaynagindan TURET (o test zaten Ege worker'ina
    vuruyor). parite-ege.js cozumunu birebir taklit eder: process.env.ARA_UC || <default>.
    Doner: 'https://host' (path/query kirpilmis) veya None. SAF."""
    base = env_ara_uc or None
    if not base:
        m = re.search(r'ARA_UC\s*\|\|\s*"([^"]+)"', parite_ege_kaynak or "")
        if not m:
            return None
        base = m.group(1)
    try:
        p = urlparse(base)
    except (ValueError, TypeError):
        return None
    if not p.scheme or not p.netloc:
        return None
    return p.scheme + "://" + p.netloc


def bayrak_deger_ayikla(index_metin):
    """index.html metninden 'var EDGE_KATALOG = true/false;' degerini ayiklar.
    Doner: True / False / None (bulunamadi). SAF."""
    m = re.search(r'\bEDGE_KATALOG\s*=\s*(true|false)\b', index_metin or "")
    if not m:
        return None
    return m.group(1) == "true"


# ═══════════════════════════════════════════════════════════════════════════════
# CANLI I/O KATMANI — her biri try/except; hicbir sey mutasyona ugramaz.
# ═══════════════════════════════════════════════════════════════════════════════

def oku_katalog_sayisi():
    """urunler.json dizi uzunlugu (salt-okuma). Hata -> None."""
    try:
        with open(URUNLER, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, list):
            return len(d)
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return None


def oku_bayrak():
    """index.html'den EDGE_KATALOG degeri (salt-okuma). Hata -> None."""
    try:
        with open(INDEX, encoding="utf-8") as f:
            return bayrak_deger_ayikla(f.read())
    except OSError:
        return None


def oku_kaynak(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def vur_worker(origin, sayfa=1, zaman_asimi=ZA_WORKER):
    """origin + /katalog?sayfa=1 GET (yalniz OKUMA). Doner: (durum_kodu, json_obj, ag_hata, ham).
    Zaman asimi + browser UA (Cloudflare WAF urllib UA'sina 403 verir) + cache-bust nonce."""
    if not origin:
        return (None, None, True, "origin turetilemedi")
    import time as _t
    nonce = "%d-%d" % (int(_t.time() * 1000), os.getpid())
    url = "%s/katalog?sayfa=%d&_nonce=%s" % (origin, sayfa, nonce)
    req = urllib.request.Request(url, headers={
        "User-Agent": BROWSER_UA,
        "Cache-Control": "no-cache",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=zaman_asimi) as r:
            kod = r.getcode()
            ham = r.read().decode("utf-8", "replace")
        try:
            obj = json.loads(ham)
        except (json.JSONDecodeError, ValueError):
            obj = None
        return (kod, obj, False, ham[:200])
    except urllib.error.HTTPError as e:
        return (e.code, None, False, "HTTP %d" % e.code)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return (None, None, True, str(e))
    except Exception as e:  # savunma: hicbir sey kapiyi cokertmesin
        return (None, None, True, "beklenmeyen: %s" % e)


def kost_d1_durum(zaman_asimi=ZA_D1):
    """python3 tools/d1-sync.py --durum (SALT-OKUMA yol). Doner: (exit, cikti, d1_sayisi)."""
    if not os.path.exists(D1_SYNC):
        return (None, "d1-sync.py yok", None)
    try:
        p = subprocess.run(
            [sys.executable, D1_SYNC, "--durum"],
            cwd=KOK, capture_output=True, text=True, timeout=zaman_asimi,
        )
        cikti = (p.stdout or "") + (p.stderr or "")
        d1 = None
        m = re.search(r"D1 urun sayisi:\s*(\d+)", cikti)
        if m:
            d1 = int(m.group(1))
        return (p.returncode, cikti, d1)
    except subprocess.TimeoutExpired:
        return (None, "zaman asimi (%ss) — wrangler yanit vermedi" % zaman_asimi, None)
    except Exception as e:
        return (None, "d1-sync calistirilamadi: %s" % e, None)


def kost_node(dosya, env_ek=None, ek_argv=None, zaman_asimi=ZA_NODE):
    """node <dosya> [argv] calistir. Doner: (dosya_var, exit, cikti)."""
    if not os.path.exists(dosya):
        return (False, None, "dosya yok")
    komut = ["node", dosya]
    if ek_argv:
        komut += [str(x) for x in ek_argv]
    ort = dict(os.environ)
    if env_ek:
        ort.update(env_ek)
    try:
        p = subprocess.run(
            komut, cwd=KOK, capture_output=True, text=True,
            timeout=zaman_asimi, env=ort,
        )
        return (True, p.returncode, (p.stdout or "") + (p.stderr or ""))
    except subprocess.TimeoutExpired:
        return (True, None, "zaman asimi (%ss)" % zaman_asimi)
    except Exception as e:
        return (True, None, "calistirilamadi: %s" % e)


# ═══════════════════════════════════════════════════════════════════════════════
# ORKESTRASYON
# ═══════════════════════════════════════════════════════════════════════════════

def son_satir(cikti):
    """Bir test ciktisindan en anlamli (SONUC) satiri kisaca yakala — rapora ozet icin."""
    if not cikti:
        return ""
    satirlar = [s.strip() for s in cikti.strip().splitlines() if s.strip()]
    for s in reversed(satirlar):
        if "SONUC" in s or "✅" in s or "❌" in s or "GECTI" in s or "KALDI" in s:
            return s
    return satirlar[-1] if satirlar else ""


def main():
    print("═" * 74)
    print("EDGE_KATALOG FLIP — HAZIRLIK KAPISI (salt-okuma; flip YAPILMAZ)")
    print("politika: tools/edge-katalog-tetik.md")
    print("═" * 74)

    adimlar = []  # (ad, durum, kim, detay)

    # ── Origin turet (parite-ege.js icinden) ──────────────────────────────────
    ege_kaynak = oku_kaynak(PARITE_EGE) or ""
    origin = ege_origin_turet(ege_kaynak, os.environ.get("ARA_UC"))
    ara_uc = (origin + "/ara") if origin else None
    print("\nEge worker origin (parite-ege.js'ten turetildi): %s" % (origin or "TURETILEMEDI"))

    # ── Ornek (isteğe bagli hizlandirma) — default: tam/kanonik kosum ──────────
    ornek = os.environ.get("EDGE_FLIP_ORNEK")
    parite_argv = [ornek] if (ornek and ornek.isdigit()) else None
    if parite_argv:
        print("NOT: EDGE_FLIP_ORNEK=%s — parite testleri ORNEKLE kosuyor (kanonik=tam)." % ornek)

    # ── Adim 1: BOYUT ─────────────────────────────────────────────────────────
    katalog = oku_katalog_sayisi()
    d1_exit, d1_cikti, d1_sayisi = kost_d1_durum()
    durum, kim, detay = deg_boyut(katalog, d1_sayisi)
    adimlar.append(("1. boyut (urunler.json)", durum, kim, detay))

    # ── Adim 2: WORKER /katalog CANLI MI ──────────────────────────────────────
    w_kod, w_json, w_aghata, w_ham = vur_worker(origin)
    durum, kim, detay = deg_worker(w_kod, w_json, w_aghata)
    adimlar.append(("2. worker /katalog canli", durum, kim, detay))

    # ── Adim 3: faz3-sayfalama + faz3-gecikme (canli worker uce karsi) ─────────
    faz3_env = {}
    if origin:
        faz3_env["KATALOG_UC"] = origin + "/katalog"
        faz3_env["EDGE_UC"] = origin
    var, ex, cikti = kost_node(FAZ3_SAYFALAMA, env_ek=faz3_env)
    durum, kim, detay = deg_komut(var, ex)
    if durum == FAIL and origin:
        detay += " (worker /katalog canli degilse bu beklenir — bkz. adim 2)"
    adimlar.append(("3a. faz3-sayfalama.js", durum, kim, detay + " | " + son_satir(cikti)))

    var, ex, cikti = kost_node(FAZ3_GECIKME, env_ek=faz3_env)
    durum, kim, detay = deg_komut(var, ex)
    if durum == FAIL and origin:
        detay += " (worker /katalog canli degilse bu beklenir — bkz. adim 2)"
    adimlar.append(("3b. faz3-gecikme.js", durum, kim, detay + " | " + son_satir(cikti)))

    # ── Adim 4: parite-test (site) + parite-ege (Ege) ─────────────────────────
    parite_env = {"ARA_UC": ara_uc} if ara_uc else {}
    var, ex, cikti = kost_node(PARITE_SITE, env_ek=parite_env, ek_argv=parite_argv)
    durum, kim, detay = deg_komut(var, ex, cikti)
    adimlar.append(("4a. parite-test.js (site)", durum, kim, detay + " | " + son_satir(cikti)))

    var, ex, cikti = kost_node(PARITE_EGE, env_ek=parite_env, ek_argv=parite_argv)
    durum, kim, detay = deg_komut(var, ex, cikti)
    adimlar.append(("4b. parite-ege.js (Ege)", durum, kim, detay + " | " + son_satir(cikti)))

    # ── Adim 5 (bilgi): d1-sync --durum ───────────────────────────────────────
    durum, kim, detay = deg_d1(d1_exit, d1_cikti)
    adimlar.append(("5. d1-sync.py --durum", durum, kim, detay))

    # ── Adim 6: EDGE_KATALOG bayragi (OKUNUR, degistirilmez) ──────────────────
    bayrak = oku_bayrak()
    durum, kim, detay = deg_bayrak(bayrak)
    adimlar.append(("6. EDGE_KATALOG bayragi", durum, kim, detay))

    # ── Rapor ──────────────────────────────────────────────────────────────────
    isaret = {PASS: "✅", FAIL: "❌", BLOKLU: "⛔"}
    print("\nADIM DURUMLARI:")
    print("-" * 74)
    for ad, durum, kim, detay in adimlar:
        etiket = durum + (("(%s)" % kim) if kim else "")
        print("  %s %-26s %-12s %s" % (isaret.get(durum, "?"), ad, etiket, detay))
    print("-" * 74)

    karar = genel_karar(adimlar)
    bloklar = blokajlar(adimlar)
    if karar == "GO":
        print("\n🟢 GENEL KARAR: GO — tum adimlar PASS. Flip provasi sonraki adima gecebilir.")
    else:
        print("\n🔴 GENEL KARAR: NO-GO — asagidaki adim(lar) engelliyor:")
        for ad, durum, kim in bloklar:
            nerede = (" -> BLOKLU: %s" % kim) if kim else ""
            print("     • %s [%s]%s" % (ad, durum, nerede))
        hoca = [b for b in bloklar if b[2] == "HocA"]
        okan = [b for b in bloklar if b[2] == "Okan"]
        if hoca:
            print("   HocA'da bloklu: Worker /katalog ucunun canliya deploy edilmesi (pruvo-bot).")
        if okan:
            print("   Okan'da bloklu: D1 token yetkisi / deploy kapisi.")

    print("\n(Bu arac hicbir dosyayi degistirmedi; flip = ayri, muhendis eliyle yapilan adim.)")
    sys.exit(0 if karar == "GO" else 1)


if __name__ == "__main__":
    main()

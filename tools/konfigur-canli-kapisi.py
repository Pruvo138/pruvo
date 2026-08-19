#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFIGUR CANLI KAPISI — "canli worker ne TAHSIL EDER" ile "urunler.json ne DIYOR" farkini olcer.

NEDEN VAR (iki olculmus vaka, 30 Tem):
  VAKA 1 — ARTEFAKT GUNCEL, WORKER ESKI. KaaN'in iki figuru eklendi, shop/src/konfigurlar.js
    uretildi ve commit'lendi, ama Worker ELLE deploy edilmedi. Katalog kapilari YESILDI
    (artefakt bayat degil), urunler canlida gorunuyordu; POST /api/shop/fiyat ise 400
    "konfigur-urun" donuyordu -> kart kanali KAPALI, siparis WhatsApp'a dustu. 2 gun surdu,
    hicbir kapi konusmadi cunku hicbir kapi CANLI worker'a bakmiyordu.
  VAKA 2 — URUNLER.JSON GUNCEL, ARTEFAKT ESKI. Capa Heykeli eklendi, artefakt uretilmedi.
    Worker o urunu hic tanimadigi icin FAIL-CLOSED 400 verir (konfigur-beklenen.js) —
    ama artefakt bir onceki surumden BAYATSA (or. fiyat capasi degistiyse) worker ESKI
    capayla tahsil eder ve bu SESSIZDIR: musteri 736 TL yerine 500 TL oder.

BU KAPI NE OLCER: her konfigurlu urun icin canli /api/shop/fiyat PROVA ucuna varsayilan
  konfigurasyonla (varsayilan boy + varsayilan malzeme, adet 1) sorar ve donen BIRIM KURUSU
  urunler.json'daki konfigur objesinden YERELDE hesaplanan kurusla karsilastirir.
  Yani KAYNAK DEGIL SONUC olculur: "musteriden ne tahsil edilecek". Bu yuzden olcum
  konfigur verisinin worker'a HANGI YOLDAN gittiginden BAGIMSIZDIR — bugun bundle
  artefakti (shop/src/konfigurlar.js), yarin D1 kolonu olsa da AYNI kapi calisir.

  🔴 Bu kapi, artefakt kapisinin (tools/konfigur-bundle-kapisi.py) GORMEDIGI ekseni olcer:
  o kapi "repo ici iki dosya tutarli mi" der; bu kapi "CANLIDA ne oluyor" der. VAKA 1'i
  YALNIZCA bu kapi yakalar.

YAN ETKI YOK: /api/shop/fiyat PROVA ucudur — D1'e YAZMAZ, siparis OLUSTURMAZ, iyzico'ya
  GITMEZ, Telegram/e-posta GONDERMEZ, olcum olayi GONDERMEZ. Bu yapisal olarak
  shop/test/fiyat-prova.mjs'te kanitlanir (D1 run() ve fetch sayaclari 0). Kapi yalnizca
  POST atar; hicbir sey yazmaz, hicbir sir okumaz.

CIKIS KODLARI (ucu de ANLAMLI — "olculemedi" ASLA yesil sayilmaz):
  0 PARITE      — her konfigurlu urunde canli kurus yerel hesapla BIREBIR.
  1 DRIFT       — en az bir urun canlida TANINMIYOR (400) ya da KURUSU SAPIYOR.
                  Onarim: shop dizininden Worker'i yeniden yayinla (Okan/KraL kapisi).
  2 OLCULEMEDI  — ag/uc erisilemedi, 429 (hiz siniri) ya da bozuk cevap. Drift KANITI YOK,
                  ama parite de KANITLANMADI -> sessiz yesil VERILMEZ.

KULLANIM:
    python3 tools/konfigur-canli-kapisi.py                  # canli olcum (ag ISTER)
    python3 tools/konfigur-canli-kapisi.py --uc https://.../api/shop/fiyat
    python3 tools/konfigur-canli-kapisi.py --kendini-test   # OFFLINE karar mantigi + mutasyon
"""
import argparse
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
URUNLER_VARSAYILAN = os.path.join(ROOT, "urunler.json")
UC_VARSAYILAN = "https://pruvo3d.com/api/shop/fiyat"

# R2 urllib UA 403 dersi ([[r2-urllib-ua-403-tuzagi]]): ciplak python-urllib UA'si edge
# tarafindan bot sayilip 403 yiyebilir -> tarayici UA'si kullanilir.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _modul(ad, dosya):
    """tools/ altindaki tireli dosya adlarini modul olarak yukler (import edilemez adlar)."""
    spec = importlib.util.spec_from_file_location(ad, os.path.join(TOOLS, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- yerel beklenti
def beklenen_kurus(urunler_yolu=URUNLER_VARSAYILAN):
    """{id: (birim_kurus, istek_govdesi)} — urunler.json'daki konfigur objesinden YERELDE
    hesaplanan varsayilan konfigurasyon fiyati + o fiyati sormak icin gereken prova sepeti.

    TEK KAYNAK: harita cikarma + sema dogrulama tools/konfigur-bundle-kapisi.py'den
    (konfigur_haritasi -> bozuk sema fail-closed), fiyat cekirdegi tools/build.py'den
    (konfigur_fiyat_kurus -> /konfigur.js JS cekirdeginin CI'da kurusu kurusuna
    dogrulanan Python aynasi). Bu dosyada UCUNCU bir kopya YOKTUR."""
    kbk = _modul("kbk", "konfigur-bundle-kapisi.py")
    build = _modul("pruvo_build", "build.py")
    with open(urunler_yolu, encoding="utf-8") as f:
        urunler = json.load(f)
    harita = kbk.konfigur_haritasi(urunler)
    out = {}
    for uid, konf in harita.items():
        malzemeler = konf["malzemeler"]
        ad = konf.get("varsayilanMalzeme")
        mal = next((m for m in malzemeler if m.get("ad") == ad), malzemeler[0])
        boy = konf["boyutMm"]["varsayilan"]
        renkler = konf.get("renkler") or ["Siyah"]
        kurus = build.konfigur_fiyat_kurus(konf, boy, mal["katsayi"])
        out[uid] = (int(kurus), {"sepet": [{
            "id": uid, "malzeme": mal["ad"], "renk": renkler[0], "adet": 1,
            "parametreler": {"boy_mm": boy},
        }]})
    return out


# ---------------------------------------------------------------- canli okuma
def _prova(uc, govde, zaman_asimi=15):
    """Tek prova istegi. Doner: ("ok", kurus) | ("400", hata_kodu) | ("hata", metin).

    Ag/HTTP katmani BURADA izole — karar mantigi (karsilastir) bu fonksiyonu SAHTELEYEREK
    offline sinanabilir; ikinci bir kod yolu yoktur."""
    ham = json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(uc, data=ham, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            veri = json.loads(y.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            veri = json.loads(e.read().decode("utf-8"))
        except Exception:
            return ("hata", "HTTP %d (govde okunamadi)" % e.code)
        if e.code == 429:
            return ("hata", "429 hiz siniri")
        if e.code == 400:
            return ("400", str(veri.get("hata") or "?"))
        return ("hata", "HTTP %d: %s" % (e.code, veri.get("hata") or "?"))
    except Exception as e:                                   # ag/DNS/TLS/zaman asimi
        return ("hata", type(e).__name__ + ": " + str(e))
    satirlar = veri.get("satirlar")
    if not isinstance(satirlar, list) or len(satirlar) != 1:
        return ("hata", "beklenmeyen cevap bicimi")
    k = satirlar[0].get("birim_kurus")
    if not isinstance(k, int):
        return ("hata", "birim_kurus sayisal degil")
    return ("ok", k)


def canli_oku(beklenenler, uc, gecikme=0.35, prova=_prova):
    """{id: sonuc} — her konfigurlu urun icin bir prova. `prova` disaridan verilebilir
    (kendini-test sahte katmani kullanir)."""
    out = {}
    for i, (uid, (_kurus, govde)) in enumerate(sorted(beklenenler.items())):
        if i and gecikme:
            time.sleep(gecikme)          # FIYAT_RATE_LIMIT 60/60 sn — 17 urun ~6 s
        out[uid] = prova(uc, govde)
    return out


# ---------------------------------------------------------------- karar (SAF)
def karsilastir(beklenenler, canli):
    """SAF karar fonksiyonu (ag YOK) -> (durum, satirlar).
    durum: "PARITE" | "DRIFT" | "OLCULEMEDI"   satirlar: [(sinif, id, aciklama)]

    SINIF ONCELIGI (bilerek): DRIFT KANITI, olcum arizasini EZER. Bir urun 400 verirken
    baska bir urunde ag hatasi olmasi kapiyi "olculemedi"ye dusuremez — elimizde ZATEN
    para kaybettiren bir bulgu var."""
    satirlar = []
    drift = 0
    ariza = 0
    for uid in sorted(beklenenler):
        bek = beklenenler[uid][0]
        sonuc = canli.get(uid)
        if sonuc is None:
            ariza += 1
            satirlar.append(("ARIZA", uid, "canli sonuc YOK"))
            continue
        tur, deger = sonuc
        if tur == "400":
            drift += 1
            if deger == "bilinmeyen-urun":
                satirlar.append(("TANIMIYOR", uid,
                                 "canli worker urunu D1'de BULAMIYOR (katalog senkronu eksik)"))
            else:
                satirlar.append(("TANIMIYOR", uid,
                                 "canli worker konfiguru TANIMIYOR (400 " + deger +
                                 ") — kart kanali KAPALI, kalem WhatsApp'a duser"))
        elif tur == "ok":
            if deger != bek:
                drift += 1
                fark = deger - bek
                satirlar.append(("SAPMA", uid,
                                 "canli %d kurus, urunler.json %d kurus (fark %+d kurus = "
                                 "%s tahsilat)" % (deger, bek, fark,
                                                   "EKSIK" if fark < 0 else "FAZLA")))
            else:
                satirlar.append(("TAMAM", uid, "%d kurus (birebir)" % deger))
        else:
            ariza += 1
            satirlar.append(("ARIZA", uid, "olculemedi — " + str(deger)))
    if drift:
        return ("DRIFT", satirlar)
    if ariza:
        return ("OLCULEMEDI", satirlar)
    return ("PARITE", satirlar)


DURUM_KOD = {"PARITE": 0, "DRIFT": 1, "OLCULEMEDI": 2}


def rapor(durum, satirlar, uc, sessiz=False):
    if sessiz:
        return DURUM_KOD[durum]
    tamam = len([s for s in satirlar if s[0] == "TAMAM"])
    print("KONFIGUR CANLI KAPISI")
    print("  uc        : " + uc)
    print("  urunler.json konfigurlu urun : %d" % len(satirlar))
    print("  canli worker DOGRU fiyatliyor: %d" % tamam)
    print("  tanimayan: %d   fiyati sapan: %d   olculemeyen: %d" % (
        len([s for s in satirlar if s[0] == "TANIMIYOR"]),
        len([s for s in satirlar if s[0] == "SAPMA"]),
        len([s for s in satirlar if s[0] == "ARIZA"])))
    for sinif, uid, aciklama in satirlar:
        if sinif != "TAMAM":
            print("    %-9s %s — %s" % (sinif, uid, aciklama))
    print("----------------------------------------------------------------------")
    if durum == "PARITE":
        print("SONUC: YESIL ✅  — canli worker ile urunler.json BIREBIR; deploy GEREKMIYOR.")
    elif durum == "DRIFT":
        print("SONUC: KIRMIZI ❌  — CANLI WORKER BAYAT: yukaridaki kalemler ya kartla")
        print("  odenemiyor ya da YANLIS tutarla odeniyor.")
        print("  COZUM (Okan/KraL kapisi — canli odeme yolu):")
        print("    1) python3 tools/konfigur-bundle-kapisi.py --yaz   (artefakt bayatsa)")
        print("    2) shop dizininden Worker'i yeniden yayinla")
        print("    3) bu kapiyi tekrar kostur -> YESIL olmali")
    else:
        print("SONUC: ⚪ OLCULEMEDI — parite KANITLANMADI (sessiz yesil verilmez).")
        print("  Ag/uc erisilemedi ya da hiz sinirina takildi; tekrar kostur.")
    return DURUM_KOD[durum]


# ---------------------------------------------------------------- kendini test
def _sahte(harita):
    """id -> sonuc sozlugunden sahte prova katmani uretir (govdedeki id'ye bakar)."""
    def prova(_uc, govde):
        return harita[govde["sepet"][0]["id"]]
    return prova


def kendini_test():
    """OFFLINE kabul: karar mantigi + KIRMIZI-MUTASYON + yanlis-pozitif. Ag YOK, dosya YAZMAZ."""
    ham = ["KONFIGUR CANLI KAPISI — KENDINI TEST (offline)"]
    kirmizi = 0

    def bek(n):
        return {("u%d" % i): (1000 + i, {"sepet": [{"id": "u%d" % i}]}) for i in range(n)}

    def kos(beklenenler, sonuclar, karar=karsilastir):
        return karar(beklenenler, {k: v for k, v in sonuclar.items()})

    def iddia(ad, kosul, detay=""):
        nonlocal kirmizi
        if kosul:
            ham.append("    ✅ " + ad)
        else:
            kirmizi += 1
            ham.append("    ❌ " + ad + (" — " + detay if detay else ""))

    # ---- (A) KARAR MANTIGI
    b3 = bek(3)
    d, s = kos(b3, {"u0": ("ok", 1000), "u1": ("ok", 1001), "u2": ("ok", 1002)})
    iddia("S1 hepsi birebir -> PARITE (rc 0)", d == "PARITE" and DURUM_KOD[d] == 0, d)

    d, s = kos(b3, {"u0": ("ok", 1000), "u1": ("400", "konfigur-urun"), "u2": ("ok", 1002)})
    iddia("S2 bir urun canlida TANINMIYOR (400) -> DRIFT (rc 1)", d == "DRIFT", d)
    iddia("S2 teshis 'kart kanali KAPALI' diyor",
          any("KAPALI" in a for k, _, a in s if k == "TANIMIYOR"))

    # 🔴 VAKA 2 SINIFI: artefakt/worker eski capayla tahsil ediyor -> SESSIZ EKSIK TAHSILAT.
    d, s = kos(b3, {"u0": ("ok", 1000), "u1": ("ok", 50000), "u2": ("ok", 1002)})
    iddia("S3 fiyat SAPMASI (eski capa) -> DRIFT (rc 1)", d == "DRIFT", d)
    iddia("S3 teshis farki KURUSLA ve YONUYLE soyluyor",
          any("fark" in a and ("FAZLA" in a or "EKSIK" in a) for k, _, a in s if k == "SAPMA"))
    d, s = kos(b3, {"u0": ("ok", 1000), "u1": ("ok", 500), "u2": ("ok", 1002)})
    iddia("S3b eksik tahsilat yonu EKSIK diye etiketleniyor",
          any("EKSIK tahsilat" in a for k, _, a in s if k == "SAPMA"))

    d, s = kos(b3, {"u0": ("hata", "ag"), "u1": ("hata", "ag"), "u2": ("hata", "ag")})
    iddia("S4 ag hatasi -> OLCULEMEDI (rc 2), ASLA yesil", d == "OLCULEMEDI" and
          DURUM_KOD[d] == 2, d)

    d, s = kos(b3, {"u0": ("hata", "ag"), "u1": ("400", "konfigur-urun"), "u2": ("ok", 1002)})
    iddia("S5 ariza + drift karisik -> DRIFT (kanit arizayi ezer)", d == "DRIFT", d)

    d, s = kos(b3, {"u0": ("ok", 1000), "u1": ("hata", "429 hiz siniri"), "u2": ("ok", 1002)})
    iddia("S6 429 -> OLCULEMEDI (yanlis DRIFT alarmi degil)", d == "OLCULEMEDI", d)

    d, s = kos({}, {})
    iddia("S7 konfigurlu urun YOK -> PARITE (bos katalog kapiyi yakmaz)", d == "PARITE", d)

    d, s = kos(b3, {"u0": ("ok", 1000), "u2": ("ok", 1002)})
    iddia("S8 cevabi HIC gelmeyen urun -> OLCULEMEDI (sessiz atlanmaz)",
          d == "OLCULEMEDI", d)

    d, s = kos(b3, {"u0": ("ok", 1000), "u1": ("400", "bilinmeyen-urun"), "u2": ("ok", 1002)})
    iddia("S9 'bilinmeyen-urun' AYRI teshis (D1 katalog senkronu)",
          d == "DRIFT" and any("D1" in a for k, _, a in s if k == "TANIMIYOR"))

    # ---- (B) HTTP KATMANI: kod->sinif eslemesi (sahte urlopen ile, ag YOK)
    import io

    class _SahteHata(urllib.error.HTTPError):
        def __init__(self, kod, govde):
            super().__init__("u", kod, "x", {}, io.BytesIO(json.dumps(govde).encode()))

    gercek = urllib.request.urlopen
    vakalar = [
        ("400 konfigur-urun -> ('400', ...)", _SahteHata(400, {"hata": "konfigur-urun"}), "400"),
        ("429 -> ('hata', ...) (drift SAYILMAZ)", _SahteHata(429, {"hata": "cok-istek"}), "hata"),
        ("500 -> ('hata', ...)", _SahteHata(500, {"hata": "sunucu-hatasi"}), "hata"),
    ]
    for ad, hata, beklenen_tur in vakalar:
        def _patlat(*a, **k):
            raise hata
        urllib.request.urlopen = _patlat
        try:
            tur, _ = _prova("http://ornek/uc", {"sepet": [{"id": "u0"}]})
        finally:
            urllib.request.urlopen = gercek
        iddia("HTTP " + ad, tur == beklenen_tur, tur)

    # ---- (C) KIRMIZI-MUTASYON: nobet NO-OP yapilinca ilgili senaryo YESILE donmeli
    # (donmuyorsa o senaryo bu satirlari OLCMUYOR demektir = olu iddia).
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        oz = f.read()
    # ⚠️ CAPA METINLERI PARCALI YAZILIR: capa duz literal olsaydi bu tablonun KENDISI
    # kaynakta ikinci bir eslesme uretir ve "capa yok/cok" dalina duserdi (olculdu).
    mutasyonlar = [
        ("MU1 fiyat karsilastirmasi olduruldu (sapma gorulmez)",
         "            if deger " + "!= bek:", "            if False:",
         b3, {"u0": ("ok", 1000), "u1": ("ok", 50000), "u2": ("ok", 1002)}),
        ("MU2 400 kolu olduruldu (tanimayan urun drift sayilmaz)",
         '        if tur ' + '== "400":', "        if False:",
         b3, {"u0": ("ok", 1000), "u1": ("400", "konfigur-urun"), "u2": ("ok", 1002)}),
        ("MU3 ariza -> PARITE'ye cevrildi (sessiz yesil)",
         '    if ariza:\n        return ("OLCULEMEDI", satirlar)', "    if False:\n        pass",
         b3, {"u0": ("hata", "ag"), "u1": ("hata", "ag"), "u2": ("hata", "ag")}),
    ]
    for ad, capa, yerine, mb, ms in mutasyonlar:
        if oz.count(capa) != 1:
            kirmizi += 1
            ham.append("    ❌ MUTASYON CAPASI YOK/COK (nobet yeniden yazilmis): " + ad)
            continue
        ns = {"__name__": "kck_mutant", "__file__": os.path.abspath(__file__)}
        exec(compile(oz.replace(capa, yerine), "<kck-mutant>", "exec"), ns)
        d_m, _ = ns["karsilastir"](mb, ms)
        if d_m == "DRIFT":
            kirmizi += 1
            ham.append("    ❌ OLU IDDIA: " + ad + " -> mutant HALA DRIFT diyor")
        else:
            ham.append("    ✅ " + ad + " -> mutant sessiz gecti (nobet YUK TASIYOR)")

    # ---- (D) YANLIS-POZITIF: gercek katalogla yerel beklenti kurulabiliyor mu + tam
    # parite senaryosu YESIL kaliyor mu (kapi "hep kirmizi" olamaz).
    try:
        gercek_bek = beklenen_kurus()
        sahte = {uid: ("ok", kurus) for uid, (kurus, _) in gercek_bek.items()}
        d, _ = karsilastir(gercek_bek, sahte)
        iddia("D1 gercek katalog (%d konfigurlu urun) tam parite -> YESIL" % len(gercek_bek),
              d == "PARITE", d)
        eksik = [uid for uid, (k, g) in gercek_bek.items()
                 if not (k > 0) or g["sepet"][0]["id"] != uid]
        iddia("D2 her urunun yerel kurusu > 0 ve prova sepeti kendi id'siyle kuruluyor",
              not eksik, str(eksik[:3]))
    except SystemExit as e:
        kirmizi += 1
        ham.append("    ❌ D: yerel beklenti kurulamadi (konfigur semasi bozuk?) — " + str(e))

    print("\n".join(ham))
    print("----------------------------------------------------------------------")
    print("SONUC: YESIL ✅ (kendini test)" if kirmizi == 0
          else "SONUC: KIRMIZI ❌ — %d iddia kaldi" % kirmizi)
    return 0 if kirmizi == 0 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uc", default=UC_VARSAYILAN)
    ap.add_argument("--urunler", default=URUNLER_VARSAYILAN)
    ap.add_argument("--gecikme", type=float, default=0.35,
                    help="istekler arasi bekleme (FIYAT_RATE_LIMIT 60/60 sn)")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    a = ap.parse_args()
    if a.kendini:
        return kendini_test()
    beklenenler = beklenen_kurus(a.urunler)
    canli = canli_oku(beklenenler, a.uc, a.gecikme)
    durum, satirlar = karsilastir(beklenenler, canli)
    return rapor(durum, satirlar, a.uc)


if __name__ == "__main__":
    sys.exit(main())

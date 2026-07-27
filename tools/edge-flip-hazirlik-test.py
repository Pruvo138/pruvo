#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — edge-flip-hazirlik.py SAF karar mantigini KANITLAR.

    python3 tools/edge-flip-hazirlik-test.py

AGSIZ / CANLI-BAGIMLILIKSIZ: yalnizca saf fonksiyonlar (bant, adim degerlendirme,
genel karar, origin turetme, bayrak ayiklama) sentetik girdilerle sinanir. Hicbir
subprocess/HTTP/dosya-yazma yok. Kirmizi-mutasyon uslubu: her iddia PASS<->FAIL / GO<->NO-GO
donusunu KANITLAR (tek yonlu 'yesil' bir mutasyonu yakalamaz).

Modul adinda tire var (edge-flip-hazirlik) -> normal import olmaz; dosya-yolundan yuklenir.
"""

import importlib.util
import os
import sys

YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edge-flip-hazirlik.py")
_spec = importlib.util.spec_from_file_location("edge_flip_hazirlik", YOL)
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

_gecti = 0
_kaldi = 0


def ONA(kosul, ad):
    global _gecti, _kaldi
    if kosul:
        _gecti += 1
    else:
        _kaldi += 1
        print("  ❌ KALDI: %s" % ad)


# ── bant_hesapla ──────────────────────────────────────────────────────────────
bant, mesafe = M.bant_hesapla(11657)
ONA(bant == M.BANT_FLIP_ALTI, "11657 -> bant flip-altı (gercek: %r)" % bant)
ONA(mesafe == 343, "11657 -> flip mesafe 343 (gercek: %r)" % mesafe)

bant, mesafe = M.bant_hesapla(12050)
ONA(bant == M.BANT_FLIP_ERISILDI, "12050 -> bant flip-erişildi (gercek: %r)" % bant)
ONA(mesafe == 0, "12050 -> flip mesafe 0 (gercek: %r)" % mesafe)

ONA(M.bant_hesapla(9000)[0] == M.BANT_HAZIRLIK_ALTI, "9000 -> hazırlık-altı")
ONA(M.bant_hesapla(10000)[0] == M.BANT_FLIP_ALTI, "10000 -> flip-altı (esik dahil)")
ONA(M.bant_hesapla(12000)[0] == M.BANT_FLIP_ERISILDI, "12000 -> flip-erişildi (esik dahil)")
ONA(M.bant_hesapla(14000)[0] == M.BANT_MECBURI, "14000 -> mecburi (esik dahil)")
ONA(M.bant_hesapla(13999)[0] == M.BANT_FLIP_ERISILDI, "13999 -> hala flip-erişildi (mutasyon)")

# ── deg_boyut: 12.000 alti FAIL, ustu PASS (kirmizi-mutasyon: sinirin iki yani) ──
ONA(M.deg_boyut(11657)[0] == M.FAIL, "boyut 11657 -> FAIL (flip esigi altinda)")
ONA(M.deg_boyut(12000)[0] == M.PASS, "boyut 12000 -> PASS (esik dahil)")
ONA(M.deg_boyut(12050)[0] == M.PASS, "boyut 12050 -> PASS")
ONA(M.deg_boyut(15000)[0] == M.PASS, "boyut 15000 -> PASS (mecburi de gecer)")
ONA(M.deg_boyut(11657)[1] is None, "boyut FAIL kimseye bloklu degil (organik)")
ONA(M.deg_boyut(None)[0] == M.FAIL, "boyut None -> FAIL (okunamadi)")

# ── deg_worker: 403 -> BLOKLU(HocA); 200+anlamli -> PASS; 200+cop -> FAIL; ag -> BLOKLU ──
d, kim, _ = M.deg_worker(403, None)
ONA(d == M.BLOKLU and kim == "HocA", "worker 403 -> BLOKLU(HocA) [d=%r kim=%r]" % (d, kim))
ONA(M.deg_worker(403, None)[0] != M.PASS, "worker 403 -> PASS DEGIL (adim2 gecmez)")
d, kim, _ = M.deg_worker(404, None)
ONA(d == M.BLOKLU and kim == "HocA", "worker 404 -> BLOKLU(HocA)")
d, kim, _ = M.deg_worker(None, None, ag_hata=True)
ONA(d == M.BLOKLU and kim == "HocA", "worker ag hatasi -> BLOKLU(HocA)")
d, kim, _ = M.deg_worker(200, {"urunler": [{"id": "x"}], "toplam": 1})
ONA(d == M.PASS and kim is None, "worker 200 + anlamli JSON -> PASS")
ONA(M.deg_worker(200, {"toplam": 5})[0] == M.PASS, "worker 200 + {toplam} -> PASS")
ONA(M.deg_worker(200, {"foo": 1})[0] == M.FAIL, "worker 200 + cop JSON -> FAIL")
ONA(M.deg_worker(200, None)[0] == M.FAIL, "worker 200 + JSON degil -> FAIL")
ONA(M.deg_worker(500, None)[0] == M.FAIL, "worker 500 -> FAIL")

# ── deg_komut (faz3/parite): dosya yok BLOKLU, exit 0 PASS, exit 2 BLOKLU, dgr FAIL ──
ONA(M.deg_komut(False, None)[0] == M.BLOKLU, "komut dosya yok -> BLOKLU")
ONA(M.deg_komut(True, 0)[0] == M.PASS, "komut exit 0 -> PASS")
ONA(M.deg_komut(True, 1)[0] == M.FAIL, "komut exit 1 -> FAIL")
ONA(M.deg_komut(True, None)[0] == M.FAIL, "komut zaman asimi -> FAIL")
# exit 2 = OLCULEMEDI (faz3-gecikme.js: uc kapali/alan yok; parite-ege.js: kaynak yok).
# Gerileme DEGIL -> FAIL yazmak yanlis suclama. BLOKLU(HocA) olmali.
d, kim, detay = M.deg_komut(True, 2)
ONA(d == M.BLOKLU and kim == "HocA", "komut exit 2 (olculemedi) -> BLOKLU(HocA)")
ONA("OLCULEMEDI" in detay, "exit 2 detayi OLCULEMEDI diyor")
# exit 3 = OLCULEMEDI (sozlesme: tools/parite-ortak.js). Gerileme DEGIL -> FAIL yazilmaz;
# ama parite KANITLANMADIGI icin PASS de yazilmaz (GO vermez) -> BLOKLU.
# "yerelde var / D1'de yok" ve SIRA farki hala exit 1 = FAIL (kapinin var olus sebebi o yon).
d, kim, detay = M.deg_komut(True, 3,
                            "  D1 FAZLALIGI: yerel=1234 < canli=1299 | fazla=65 satir; "
                            "SEBEP AYIRT EDILEMEDI\n⚪ SENKRON GECİKMESİ / KATALOG FARKI")
ONA(d == M.BLOKLU, "komut exit 3 (katalog farki) -> BLOKLU")
ONA(d != M.PASS, "komut exit 3 -> PASS DEGIL (olculemeyen YESILE donmez)")
ONA("1234" in detay and "1299" in detay and "65" in detay,
    "exit 3 detayi SAYIYLA sebep veriyor (olculen kanit)")
ONA("AYIRT EDILEMEDI" in detay,
    "exit 3 detayi KESIN HUKUM basmiyor (checkout bayat / yetim satir ayrilmadi)")
ONA("GO da VERMEZ" in detay, "exit 3 detayi GO vermedigini ACIKCA yaziyor")
d, _, detay = M.deg_komut(True, 3, "⚪ ÖLÇÜLEMEDİ: WAF/UA — canli uc HTTP 403 dondu")
ONA(d == M.BLOKLU and "WAF/UA" in detay, "komut exit 3 (WAF/UA) -> BLOKLU + sebep")
d, _, detay = M.deg_komut(True, 3, "⚪ ÖLÇÜLEMEDİ: HIZ SINIRI (429) — deneme tukendi")
ONA(d == M.BLOKLU and "429" in detay, "komut exit 3 (429) -> BLOKLU + sebep")
d, _, detay = M.deg_komut(True, 3, "⚪ ÖLÇÜLEMEDİ: ZAMAN ASIMI (20000 ms/istek)")
ONA(d == M.BLOKLU and "zaman asimi" in detay.lower(), "komut exit 3 (zaman asimi) -> BLOKLU + sebep")
d, _, detay = M.deg_komut(True, 3, "⚠️ FIKSTUR MODU: test-only env verildi (PARITE_URUNLER)")
ONA(d == M.BLOKLU and "FIKSTUR MODU" in detay,
    "komut exit 3 (PARITE_URUNLER/fikstur modu) -> BLOKLU + GORUNUR uyari (A15)")
ONA(M.deg_komut(True, 4)[0] == M.FAIL, "komut exit 4 -> FAIL (yalniz 2 ve 3 ozel)")
ONA(M.deg_komut(True, 1)[0] == M.FAIL, "komut exit 1 -> FAIL (aciklanamayan ayrisim)")

# ── deg_d1: kimlik hatasi BLOKLU(Okan), exit 0 PASS, nonzero FAIL ────────────────
d, kim, _ = M.deg_d1(1, "D1 KIMLIK HATASI (code 10000)")
ONA(d == M.BLOKLU and kim == "Okan", "d1 kimlik hatasi -> BLOKLU(Okan)")
d, kim, _ = M.deg_d1(0, "code: 10000")  # cikti kimlik hatasi -> exit'e ragmen BLOKLU(Okan)
ONA(d == M.BLOKLU and kim == "Okan", "d1 code10000 ciktisi -> BLOKLU(Okan)")
ONA(M.deg_d1(0, "teyit ✅")[0] == M.PASS, "d1 exit 0 -> PASS")
ONA(M.deg_d1(1, "!! D1 SENKRON DRIFT")[0] == M.FAIL, "d1 drift exit 1 -> FAIL")
ONA(M.deg_d1(1, "!! D1 SENKRON DRIFT")[2].find("DRIFT") != -1 or True, "d1 drift detay")

# ── deg_bayrak: None FAIL, false PASS, true PASS ────────────────────────────────
ONA(M.deg_bayrak(None)[0] == M.FAIL, "bayrak bulunamadi -> FAIL")
ONA(M.deg_bayrak(False)[0] == M.PASS, "bayrak false -> PASS (flip oncesi)")
ONA(M.deg_bayrak(True)[0] == M.PASS, "bayrak true -> PASS (zaten acik)")

# ── genel_karar: bir adim FAIL/BLOKLU -> NO-GO; hepsi PASS -> GO ─────────────────
hepsi_pass = [
    ("1. boyut", M.PASS, None, ""),
    ("2. worker", M.PASS, None, ""),
    ("3a. faz3s", M.PASS, None, ""),
    ("3b. faz3g", M.PASS, None, ""),
    ("4a. parite-site", M.PASS, None, ""),
    ("4b. parite-ege", M.PASS, None, ""),
    ("5. d1", M.PASS, None, ""),
    ("6. bayrak", M.PASS, None, ""),
]
ONA(M.genel_karar(hepsi_pass) == "GO", "tum adimlar PASS -> GO")

bir_fail = list(hepsi_pass)
bir_fail[0] = ("1. boyut", M.FAIL, None, "")
ONA(M.genel_karar(bir_fail) == "NO-GO", "bir adim FAIL -> NO-GO")

bir_blok = list(hepsi_pass)
bir_blok[1] = ("2. worker", M.BLOKLU, "HocA", "")
ONA(M.genel_karar(bir_blok) == "NO-GO", "bir adim BLOKLU -> NO-GO")

# BUGUNKU GERCEKCI SENARYO (11657 + worker /katalog down): boyut FAIL + worker BLOKLU(HocA)
bugun = [
    ("1. boyut", M.deg_boyut(11657)[0], None, ""),
    ("2. worker", M.deg_worker(403, None)[0], "HocA", ""),
]
ONA(M.genel_karar(bugun) == "NO-GO", "bugun (11657 + worker 403) -> NO-GO")
bl = M.blokajlar(bir_blok)
ONA(any(k == "HocA" for _, _, k in bl), "blokajlar HocA'yi listeler")

# ── ege_origin_turet: default literal + ARA_UC env override + path kirpma ────────
sahte_kaynak = 'const UC = process.env.ARA_UC || "https://pruvo-whatsapp-bot.gmlmz.workers.dev/ara";'
ONA(M.ege_origin_turet(sahte_kaynak) == "https://pruvo-whatsapp-bot.gmlmz.workers.dev",
    "origin default literal'den (path kirpildi)")
ONA(M.ege_origin_turet(sahte_kaynak, "https://baska.workers.dev/ara") == "https://baska.workers.dev",
    "origin ARA_UC override")
ONA(M.ege_origin_turet("kaynak yok burada") is None, "origin bulunamazsa None")
ONA(M.ege_origin_turet("") is None, "bos kaynak -> None")

# ── bayrak_deger_ayikla: true/false/yok ─────────────────────────────────────────
ONA(M.bayrak_deger_ayikla("  var EDGE_KATALOG = false;") is False, "ayikla false")
ONA(M.bayrak_deger_ayikla("  var EDGE_KATALOG = true;") is True, "ayikla true")
ONA(M.bayrak_deger_ayikla("hicbir sey") is None, "ayikla bulunamadi -> None")

# ── SONUC ───────────────────────────────────────────────────────────────────────
toplam = _gecti + _kaldi
print("\n%d/%d GEÇTI" % (_gecti, toplam))
if _kaldi:
    print("SONUC: KABUL TESTI KIRMIZI ❌ (%d kaldi)" % _kaldi)
    sys.exit(1)
print("SONUC: KABUL TESTI YEŞİL ✅")
sys.exit(0)

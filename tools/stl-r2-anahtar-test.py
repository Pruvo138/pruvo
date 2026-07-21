#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — stl-r2-yukle.py anahtar kapisi + cok-parcali yukleme yol secimi.

Kapsanan uc kusur (MaCiT olcumu, 21 Tem):
  A) CIFT NOKTA / 403: adi nokta ile biten dosyalar `<ad>..stl` anahtari uretiyordu;
     Cloudflare edge yol-gezinme korumasi 403 donuyordu. Uretilen anahtarda `..` OLMAMALI.
  B) YOL-GEZINME: `..` yol parcasi iceren anahtar REDDEDILMELI (guvenlik kapisi; 403'u
     susturmak yeterli degil).
  C) 300 MiB SINIRI: wrangler tek-parca siniri ustundeki dosya S3 cok-parcali yola,
     altindaki dosya ESKI wrangler yoluna gitmeli (regresyon yok).

GERCEK R2 YAZMA YOKTUR: yukleme yollari monkeypatch ile degistirilir, ag'a cikilmaz,
kimlik dosyasi okunmaz.

    python3 tools/stl-r2-anahtar-test.py     # exit 0 = YESIL
"""

import importlib.util
import os
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "stl_r2_yukle", os.path.join(TOOLS, "stl-r2-yukle.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

hatalar = []


def kontrol(ok, mesaj):
    print(("  ✅ " if ok else "  ❌ ") + mesaj)
    if not ok:
        hatalar.append(mesaj)


# --- (a) CIFT-NOKTA ANAHTARI: 3 gercek dosya adi + olcumde cikan 4. ------------------
print("A) cift-nokta anahtari 403 uretmeyecek bicimde normalize ediliyor mu")
GERCEK_ADLAR = [
    # (dosya adi, onek-esleme icin urun-id, beklenen anahtar)
    ("3859956--VectraCAstraHMerivaB_Lenradfern..stl", "3859956",
     "stl/3859956/VectraCAstraHMerivaB_Lenradfern.stl"),
    ("4488414--skoda_key_emblem..stl", "4488414",
     "stl/4488414/skoda_key_emblem.stl"),
    ("5193899--tamponi_Aktuator_3br..STL", "5193899",
     "stl/5193899/tamponi_Aktuator_3br.stl"),
    ("254529--S.E..STL", "254529", "stl/254529/S.E.stl"),
]
idler = {t[1] for t in GERCEK_ADLAR}
hedefler, hatali, cakisan = M.siniflandir([t[0] for t in GERCEK_ADLAR], idler)
anahtarlar = dict(hedefler)
for ad, _onek, beklenen in GERCEK_ADLAR:
    uretilen = anahtarlar.get(ad)
    kontrol(uretilen == beklenen,
            "%s -> %r (beklenen %r)" % (ad, uretilen, beklenen))
    kontrol(uretilen is not None and ".." not in uretilen,
            "%s anahtarinda cift nokta YOK" % ad)
kontrol(not hatali and not cakisan,
        "4 gercek dosya hatali-ad/cakisan'a DUSMEDI (hatali=%d cakisan=%d)"
        % (len(hatali), len(cakisan)))

# --- (b) YOL-GEZINME REDDI ----------------------------------------------------------
print("B) kotu-niyetli yol-gezinme anahtari REDDEDILIYOR mu")
KOTU = [
    "stl/../../etc/passwd.stl",
    "stl/../gizli.stl",
    "../disari.stl",
    "/mutlak/yol.stl",
    "stl/.././x.stl",
    "stl/x\\y.stl",
    "stl//bos.stl",
    "stl/./x.stl",
]
for k in KOTU:
    try:
        sonuc = M.anahtar_normalize(k)
        kontrol(False, "%r REDDEDILMEDI -> %r" % (k, sonuc))
    except M.AnahtarReddi:
        kontrol(True, "%r reddedildi" % k)

# masum anahtar gecmeli (kapi asiri genis olmasin)
for k, beklenen in (("stl/urun-id/parca.stl", "stl/urun-id/parca.stl"),
                    ("stl/a/b..stl", "stl/a/b.stl")):
    try:
        kontrol(M.anahtar_normalize(k) == beklenen, "masum %r -> %r" % (k, beklenen))
    except M.AnahtarReddi as e:
        kontrol(False, "masum anahtar %r yanlislikla reddedildi: %s" % (k, e))

# siniflandir seviyesinde: yol-gezinme onekli dosya HATALI-AD'a duser, yuklenmez
h2, hatali2, _c2 = M.siniflandir(["..--kotu.stl"], None)
kontrol(not h2 and hatali2 == ["..--kotu.stl"],
        "siniflandir: '..--kotu.stl' yuklenecekler'e GIRMEDI, hatali-ad'a dustu "
        "(hedef=%d hatali=%r)" % (len(h2), hatali2))

# --- (c)+(d) BOYUT ESIGINE GORE YOL SECIMI ------------------------------------------
print("C) 300 MiB esigine gore yukleme yolu secimi (GERCEK YUKLEME YOK)")
secilen = []
eski_wrangler, eski_multipart = M.yukle_wrangler, M.yukle_multipart
M.yukle_wrangler = lambda y, a: secilen.append(("wrangler", a)) or True
M.yukle_multipart = lambda y, a: secilen.append(("multipart", a)) or True
try:
    with tempfile.TemporaryDirectory() as td:
        kucuk = os.path.join(td, "kucuk.stl")
        with open(kucuk, "wb") as f:
            f.write(b"0" * 1024)
        buyuk = os.path.join(td, "buyuk.stl")
        with open(buyuk, "wb") as f:  # seyrek dosya: disk yakmadan boyut uretir
            f.truncate(M.WRANGLER_TEK_PARCA_SINIRI + 1)

        secilen.clear()
        M.yukle(kucuk, "stl/x/kucuk.stl")
        kontrol(secilen == [("wrangler", "stl/x/kucuk.stl")],
                "300 MiB ALTI dosya ESKI wrangler yolunda (secilen=%r)" % secilen)

        secilen.clear()
        M.yukle(buyuk, "stl/x/buyuk.stl")
        kontrol(secilen == [("multipart", "stl/x/buyuk.stl")],
                "300 MiB USTU dosya cok-parcali yolda (secilen=%r)" % secilen)

        # tam sinirdaki dosya HALA wrangler'da (sinir dahil)
        sinir = os.path.join(td, "sinir.stl")
        with open(sinir, "wb") as f:
            f.truncate(M.WRANGLER_TEK_PARCA_SINIRI)
        secilen.clear()
        M.yukle(sinir, "stl/x/sinir.stl")
        kontrol(secilen == [("wrangler", "stl/x/sinir.stl")],
                "tam 300 MiB dosya wrangler yolunda (secilen=%r)" % secilen)
finally:
    M.yukle_wrangler, M.yukle_multipart = eski_wrangler, eski_multipart

# cok-parcali yol boto3/kimlik yoksa SESSIZ GECMEZ (net hata + False)
print("D) cok-parcali yol sessiz basarisizlik yapmiyor mu")


def _patlayan_istemci():
    raise RuntimeError("kimlik yok (test)")


sonuc = M.yukle_multipart("/olmayan/dosya.stl", "stl/x/y.stl", istemci_fn=_patlayan_istemci)
kontrol(sonuc is False, "kimlik/bagimlilik yoksa yukle_multipart False dondu (sessiz True degil)")

print("\nSONUC: " + ("YESIL ✅" if not hatalar else "KIRMIZI ❌ (%d)" % len(hatalar)))
sys.exit(1 if hatalar else 0)

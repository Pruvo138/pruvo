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


# --- (E) YEREL SIL KOLU + (F) DRIVE BIRAK (STL-SIFIR, 6 Eki 2026) ---------------------
# HERMETIK: yalniz gecici dizin; GERCEK stl/, manifest, R2 ve Drive'a dokunulmaz (gonderici
# ve evict sahte). Her vaka (ok, mesaj) doner; ayni vaka kopyadaki MUTANT modulde KIRMIZI
# olmali (kontrol silinince kol oluyor mu).
import hashlib  # noqa: E402
import shutil  # noqa: E402

_dspec = importlib.util.spec_from_file_location("drive_birak", os.path.join(TOOLS, "drive_birak.py"))
DB = importlib.util.module_from_spec(_dspec)
_dspec.loader.exec_module(DB)


def _sahne(adlar):
    d = tempfile.mkdtemp(prefix="stl-yerel-sil-test-")
    for ad in adlar:
        with open(os.path.join(d, ad), "wb") as f:
            f.write(b"solid " + ad.encode() + b"\n")
    return d, os.path.join(d, "manifest.json")


def _kos(mod, d, man, gonderici, **kw):
    silinen = []
    try:
        mod.kos(os.path.join(d, "stl"), {"123"}, man, yukle_fn=gonderici, silinen=silinen, **kw)
        cikis = None
    except SystemExit as e:
        cikis = e
    return silinen, cikis


def _stl_sahne(adlar):
    d, man = _sahne([])
    os.makedirs(os.path.join(d, "stl"))
    for ad in adlar:
        with open(os.path.join(d, "stl", ad), "wb") as f:
            f.write(b"solid " + ad.encode() + b"\n")
    return d, man


def _var(d, ad):
    return os.path.exists(os.path.join(d, "stl", ad))


def vaka_basarili(mod, paralel=1):
    d, man = _stl_sahne(["123--a.stl"])
    try:
        silinen, cikis = _kos(mod, d, man, lambda y, k: True, yerel_sil=True, paralel=paralel)
        ok = cikis is None and not _var(d, "123--a.stl") and silinen == ["123--a.stl"]
        return ok, "yukleme basarili -> yerel SILINDI (paralel=%d, silinen=%r)" % (paralel, silinen)
    finally:
        shutil.rmtree(d)


def vaka_basarisiz(mod, paralel=1):
    d, man = _stl_sahne(["123--a.stl", "123--b.stl"])
    try:
        silinen, cikis = _kos(mod, d, man, lambda y, k: not y.endswith("b.stl"),
                              yerel_sil=True, paralel=paralel)
        ok = (cikis is not None and _var(d, "123--b.stl") and not _var(d, "123--a.stl")
              and silinen == ["123--a.stl"])
        return ok, ("yukleme basarisiz -> o dosya KALDI, basarili komsu silindi, cikis!=0 "
                    "(paralel=%d, silinen=%r)" % (paralel, silinen))
    finally:
        shutil.rmtree(d)


def vaka_sha_degisti(mod):
    d, man = _stl_sahne(["123--a.stl"])

    def gonder_sonra_degistir(yerel, anahtar):
        with open(yerel, "ab") as f:
            f.write(b"degisti\n")
        return True
    try:
        silinen, cikis = _kos(mod, d, man, gonder_sonra_degistir, yerel_sil=True)
        ok = cikis is None and _var(d, "123--a.stl") and silinen == []
        return ok, "yuklemeden sonra sha degisti -> yerel KALDI (silinen=%r)" % silinen
    finally:
        shutil.rmtree(d)


def vaka_kuru(mod):
    d, man = _stl_sahne(["123--a.stl", "123--b.stl"])
    try:
        # a ONCEDEN yuklenmis (manifest sha1 esit) -> kuru olmasa silinirdi; b yuklenecek
        with open(os.path.join(d, "stl", "123--a.stl"), "rb") as f:
            veri = f.read()
        mod.manifest_yaz(man, {"stl/123/a.stl": {"sha1": hashlib.sha1(veri).hexdigest(),
                                                 "boyut": len(veri)}})
        silinen, cikis = _kos(mod, d, man, lambda y, k: True, yerel_sil=True, kuru=True)
        ok = cikis is None and _var(d, "123--a.stl") and _var(d, "123--b.stl") and silinen == []
        return ok, "--kuru -> hicbir yerel dosya silinmedi (silinen=%r)" % silinen
    finally:
        shutil.rmtree(d)


def vaka_yerel_tut(mod):
    d, man = _stl_sahne(["123--a.stl"])
    try:
        silinen, cikis = _kos(mod, d, man, lambda y, k: True, yerel_sil=False)
        ok = cikis is None and _var(d, "123--a.stl") and silinen == []
        return ok, "--yerel-tut (yerel_sil=False) -> yuklendi ama yerel KALDI (silinen=%r)" % silinen
    finally:
        shutil.rmtree(d)


def vaka_hatali_ad(mod):
    d, man = _stl_sahne(["999--x.stl", "123--a.stl"])
    try:
        silinen, cikis = _kos(mod, d, man, lambda y, k: True, yerel_sil=True)
        ok = cikis is None and _var(d, "999--x.stl") and silinen == ["123--a.stl"]
        return ok, "hatali-ad dosya SILINMEDI, eslenen silindi (silinen=%r)" % silinen
    finally:
        shutil.rmtree(d)


def vaka_cli(mod):
    v = mod.arg_ayristir([])
    t = mod.arg_ayristir(["--yerel-tut"])
    s = mod.arg_ayristir(["--yerel-sil"])
    ok = v.yerel_sil is True and t.yerel_sil is False and s.yerel_sil is True
    return ok, "CLI: varsayilan yerel_sil=ACIK, --yerel-tut kapatir (%r/%r/%r)" % (
        v.yerel_sil, t.yerel_sil, s.yerel_sil)


def vaka_drive_ok(dm):
    d = tempfile.mkdtemp(prefix="drive-birak-test-")
    try:
        cagri = []
        yol = os.path.join(d, "x.stl")
        sonuc = dm.yaz_dogrula_birak(yol, b"solid x\n", birak_fn=lambda y: cagri.append(y) or True)
        ok = sonuc == "BIRAKILDI" and cagri == [yol] and open(yol, "rb").read() == b"solid x\n"
        return ok, "drive: yaz+sha256 esit -> evict CAGRILDI (%s)" % sonuc
    finally:
        shutil.rmtree(d)


def vaka_drive_uyusmaz(dm):
    d = tempfile.mkdtemp(prefix="drive-birak-test-")
    eski = dm.sha256_dosya
    try:
        cagri = []
        dm.sha256_dosya = lambda y: "0" * 64  # geri okuma bozuk yazimi taklit eder
        sonuc = dm.yaz_dogrula_birak(os.path.join(d, "x.stl"), b"solid x\n",
                                     birak_fn=lambda y: cagri.append(y) or True)
        ok = sonuc == "UYUSMAZ" and cagri == []
        return ok, "drive: sha256 UYUSMAZ -> evict YOK (%s, cagri=%d)" % (sonuc, len(cagri))
    finally:
        dm.sha256_dosya = eski
        shutil.rmtree(d)


def vaka_drive_birakilamadi(dm):
    d = tempfile.mkdtemp(prefix="drive-birak-test-")
    try:
        sonuc = dm.yaz_dogrula_birak(os.path.join(d, "x.stl"), b"solid x\n", birak_fn=lambda y: False)
        return sonuc == "BIRAKILAMADI", "drive: evict basarisiz -> BIRAKILAMADI (sessiz BIRAKILDI degil)"
    finally:
        shutil.rmtree(d)


def vaka_thing_kablo(kaynak):
    # thing-hazirla import aninda yerel sir/klasor okur (CI'da import edilemez) -> kablo METINDEN.
    ok = ("drive_birak.yaz_dogrula_birak(os.path.join(DRIVE, nm), data)" in kaynak
          and 'open(os.path.join(DRIVE, nm), "wb")' not in kaynak
          and 'open(os.path.join(STLDIR, nm), "wb").write(data)' in kaynak)
    return ok, "thing-hazirla: Drive yazimi yaz_dogrula_birak'tan geciyor, yerel stl/ yazimi aynen"


print("E) yerel sil kolu (stl-r2-yukle --yerel-sil / --yerel-tut)")
VAKALAR_E = [vaka_basarili, lambda m: vaka_basarili(m, 2), vaka_basarisiz,
             lambda m: vaka_basarisiz(m, 2), vaka_sha_degisti, vaka_kuru, vaka_yerel_tut,
             vaka_hatali_ad, vaka_cli]
for v in VAKALAR_E:
    kontrol(*v(M))
print("F) drive birak (thing-hazirla Drive kopyasi evict)")
for v in (vaka_drive_ok, vaka_drive_uyusmaz, vaka_drive_birakilamadi):
    kontrol(*v(DB))
_THING = open(os.path.join(TOOLS, "thing-hazirla.py"), encoding="utf-8").read()
kontrol(*vaka_thing_kablo(_THING))

print("G) mutantlar (kopyada kontrol silinir -> ilgili vaka KIRMIZI olmali)")
_KAYNAK = {"stl": open(os.path.join(TOOLS, "stl-r2-yukle.py"), encoding="utf-8").read(),
           "drive": open(os.path.join(TOOLS, "drive_birak.py"), encoding="utf-8").read()}
MUTANTLAR = [
    # (ad, kaynak, eski, yeni, vaka)
    ("sha-kontrolu-yok", "stl",
     '    if sha1_dosya(yerel) != kayit["sha1"]:\n        return False\n', "", vaka_sha_degisti),
    ("manifest-kaniti-yok", "stl", "yerel_sil_dogrulanmis(yerel, manifest.get(anahtar))",
     'yerel_sil_dogrulanmis(yerel, {"sha1": sha1_dosya(yerel)})', vaka_basarisiz),
    ("manifest-kaniti-yok-paralel", "stl", "yerel_sil_dogrulanmis(yerel, manifest.get(anahtar))",
     'yerel_sil_dogrulanmis(yerel, {"sha1": sha1_dosya(yerel)})', lambda m: vaka_basarisiz(m, 2)),
    ("kuru-korumasi-yok", "stl", "temizle = yerel_sil and not kuru", "temizle = yerel_sil",
     vaka_kuru),
    ("yerel-tut-yok", "stl", "temizle = yerel_sil and not kuru", "temizle = not kuru",
     vaka_yerel_tut),
    ("varsayilan-kapali", "stl", 'action="store_true", default=True,',
     'action="store_true", default=False,', vaka_cli),
    ("drive-sha-kontrolu-yok", "drive",
     '    if sha256_dosya(yol) != hashlib.sha256(data).hexdigest():\n        return "UYUSMAZ"\n',
     "", vaka_drive_uyusmaz),
]
_mdir = tempfile.mkdtemp(prefix="stl-yerel-sil-mutant-")
try:
    for i, (ad, kay, eski, yeni, vaka) in enumerate(MUTANTLAR):
        src = _KAYNAK[kay]
        if src.count(eski) < 1:
            kontrol(False, "mutant %s: capa kaynakta YOK (mutant bayat)" % ad)
            continue
        yol = os.path.join(_mdir, "mutant_%d.py" % i)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(src.replace(eski, yeni))
        sp = importlib.util.spec_from_file_location("mutant_%d" % i, yol)
        mm = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(mm)
        try:
            ok, _ = vaka(mm)
        except Exception as e:  # noqa: BLE001 — mutant cokmesi de KIRMIZI sayilir
            ok = False
            ad += " (cokme: %s)" % type(e).__name__
        kontrol(not ok, "mutant %s -> vaka KIRMIZI" % ad)
    eski_kablo = _THING.replace(
        "drive_birak.yaz_dogrula_birak(os.path.join(DRIVE, nm), data)",
        'open(os.path.join(DRIVE, nm), "wb").write(data)')
    kontrol(not vaka_thing_kablo(eski_kablo)[0], "mutant thing-kablo-eski -> vaka KIRMIZI")
finally:
    shutil.rmtree(_mdir)

print("\nSONUC: " + ("YESIL ✅" if not hatalar else "KIRMIZI ❌ (%d)" % len(hatalar)))
sys.exit(1 if hatalar else 0)

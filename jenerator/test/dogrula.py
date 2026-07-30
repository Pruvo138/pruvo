#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI #1 cekirdegi — hacim.js kapali-form sonucu vs OpenSCAD render hacmi.

Her aile icin: varsayilan set + N rastgele GECERLI set uretir (sema min/max/adim
izgarasinda), hacim.js (node) ve OpenSCAD render STL hacmini karsilastirir.
Sapma > %3 ise KIRMIZI (cikis kodu 1). Ayrica tabanHacimMm3 == fn(varsayilanlar)
(%0.1 tolerans) dogrulanir.

Kullanim:
  python3 dogrula.py oring            # tek aile
  python3 dogrula.py --hepsi          # esleme/ altindaki tum aileler
  python3 dogrula.py oring --set 5 --seed 42
  python3 dogrula.py --kendini-test   # OPENSCAD YASAK NOBETCISI (openscad GEREKTIRMEZ)
Ortam: PRUVO_SCAD_DIR (varsayilan ~/dev/pruvo-jenerator/jeneratorler),
       PRUVO_OPENSCAD (varsayilan /opt/homebrew/bin/openscad),
       PRUVO_OPENSCAD_YASAK=1 -> OpenSCAD CAGRISI YASAK (bkz. asagisi)
"""
import argparse
import io
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
JEN_DIR = os.path.dirname(TEST_DIR)
ESLEME_DIR = os.path.join(TEST_DIR, "esleme")
URUN_DIR = os.path.join(JEN_DIR, "urunler")
SINIR_YUZDE = 3.0
TABAN_TOLERANS = 0.001

sys.path.insert(0, TEST_DIR)
import stl_hacim  # noqa: E402


# ---- OPENSCAD YASAGI — ADA DEGIL COZUMLENMIS HEDEFE BAKAR -------------------
# NEDEN VAR: bu depoda OpenSCAD'in acilista SIGABRT atip PENCERE SPAM'i uretmesi
# olculdu ([[openscad-cokme-pencere-spami]]); "OpenSCAD YOK" siniriyla kosan
# oturumlar (denetim/ci turlari) yasagi PATH'e `openscad` adinda bir shim koyarak
# uyguluyordu. DELIK (madde 33): openscad_yolu() adaylari SIRAYLA MUTLAK YOLDAN
# deniyor (`/opt/homebrew/bin/openscad`, Caskroom glob'u, .app govdesi) ve
# `shutil.which("openscad")` EN SONDA; yani PATH shim'i HIC devreye girmeden
# GERCEK OpenSCAD kosuyordu -> yasak ADA gore eleniyor, MUTLAK YOLLA deliniyor.
#
# BUGUNKU KURAL (fail-closed): yasak PRUVO_OPENSCAD_YASAK ile BEYAN edilir; beyan
# varken her aday COZUMLENIR (sarmal soyma -> PATH cozumu -> realpath) ve
#   EVET        -> hicbir sey kosturulmaz, sifir-disi cikis (3)
#   OLCULEMEDI  -> hedef cozulemedi/jetonlanamadi: YESIL SAYILMAZ, cikis 3
#   HAYIR       -> mesru baska arac (stub/shim), kosmaya IZIN VAR
# Yasak beyan EDILMEMISKEN davranis BIREBIR eskisi gibidir (normal jeneratör
# turlerinde yanlis-pozitif uretmesin diye).
OPENSCAD_YASAK_ORTAM = "PRUVO_OPENSCAD_YASAK"
YASAK_CIKIS_KODU = 3
_OPENSCAD_RE = re.compile(r"openscad", re.I)
# Hedefi GIZLEYEN sarmallar: `env A=1 openscad`, `nohup openscad`, `arch -x86_64 openscad`...
_SARMAL_KOMUTLAR = {"env", "nohup", "command", "nice", "stdbuf", "time", "arch", "exec",
                    "ionice", "setsid", "xargs"}
_KABUK_KOMUTLARI = {"sh", "bash", "zsh", "dash", "ksh", "fish"}


def yasak_aktif():
    """PRUVO_OPENSCAD_YASAK BEYAN edilmis mi? ('', '0', 'hayir', 'false' -> hayir)"""
    return os.environ.get(OPENSCAD_YASAK_ORTAM, "").strip().lower() not in (
        "", "0", "hayir", "false", "kapali")


def _jetonla(komut):
    """Komutu (dize ya da dizi) jetonlara ayir; ayrilamazsa None (-> OLCULEMEDI).

    DIZE kolu SART: yasagin delindigi bicimlerden biri 'yolun sonunda ek arguman'
    (`/usr/local/bin/openscad -o x.stl`) — duz `os.path.exists()` bunu 'yok' sanip
    sessizce atlar, `shlex` ise ILK jetonu gercek hedef olarak verir."""
    if isinstance(komut, (list, tuple)):
        return [str(x) for x in komut]
    try:
        jet = shlex.split(str(komut))
    except ValueError:
        return None
    return jet


def _sarmali_soy(jetonlar, derinlik=0):
    """`env`/`nohup`/`arch`/`sh -c ...` sarmallarini soyup GERCEK hedef jetonu dondur."""
    if derinlik > 4 or not jetonlar:
        return None
    ilk = jetonlar[0]
    taban = os.path.basename(ilk).lower()
    if taban in _KABUK_KOMUTLARI and "-c" in jetonlar[1:]:
        i = jetonlar.index("-c", 1)
        if i + 1 < len(jetonlar):
            ic = _jetonla(jetonlar[i + 1])
            if ic is None:
                return None
            return _sarmali_soy(ic, derinlik + 1)
        return None
    if taban in _SARMAL_KOMUTLAR:
        kalan = []
        for j in jetonlar[1:]:
            if not kalan and ("=" in j or j.startswith("-")):
                continue  # VAR=DEGER atamasi / sarmalin kendi bayragi
            kalan.append(j)
        if not kalan:
            return None
        return _sarmali_soy(kalan, derinlik + 1)
    return ilk


def openscad_hedefi(komut):
    """(hukum, tani, cozulen_yol) — hukum: 'EVET' | 'HAYIR' | 'OLCULEMEDI'.

    'EVET' = bu cagri OpenSCAD'i calistirir (ya da ADI OpenSCAD'i taklit ediyor).
    ADA DEGIL COZUMLENMIS HEDEFE bakar: mutlak yol, sembolik bag (realpath),
    env/kabuk sarmali, buyuk-kucuk harf, yolun sonundaki ek argumanlar."""
    jet = _jetonla(komut)
    if jet is None:
        return "OLCULEMEDI", "komut jetonlanamadi (kapanmamis tirnak?): %r" % (komut,), None
    hedef = _sarmali_soy(jet)
    if not hedef:
        return "OLCULEMEDI", "komutta calistirilabilir hedef bulunamadi: %r" % (komut,), None
    if _OPENSCAD_RE.search(os.path.basename(hedef)):
        # ADI openscad olan her sey (buyuk-kucuk harf farki dahil) yasak kapsamindadir;
        # hedef cozulemese bile YESIL SAYILMAZ (fail-closed).
        return "EVET", "cagrilan adin kendisi openscad: %s" % hedef, hedef
    if os.sep in hedef or hedef.startswith("."):
        mutlak = os.path.abspath(hedef)
    else:
        mutlak = shutil.which(hedef)
        if not mutlak:
            return "OLCULEMEDI", "'%s' PATH'te cozulemedi (hedef bilinmiyor)" % hedef, None
    if not os.path.exists(mutlak):
        return "OLCULEMEDI", "hedef diskte yok, cozulemedi: %s" % mutlak, mutlak
    gercek = os.path.realpath(mutlak)   # sembolik bag zinciri burada cozulur
    if _OPENSCAD_RE.search(gercek):
        return "EVET", "cozumlenen hedef openscad: %s -> %s" % (hedef, gercek), gercek
    return "HAYIR", "openscad degil: %s -> %s" % (hedef, gercek), gercek


def _yasak_cikis(tani):
    sys.stderr.write(
        "OPENSCAD YASAK (%s=%s) — cagri REDDEDILDI, hicbir render kosulmadi.\n"
        "  %s\n"
        "  Bu bir 'yesil' DEGIL: olcum OLCULEMEDI sayilir (cikis %d).\n" % (
            OPENSCAD_YASAK_ORTAM, os.environ.get(OPENSCAD_YASAK_ORTAM, ""),
            tani, YASAK_CIKIS_KODU))
    sys.exit(YASAK_CIKIS_KODU)


def openscad_adaylari():
    """Aday openscad yollari — SIRA KORUNDU (2026-07-16: /Applications/OpenSCAD.app
    kayboldu, brew symlink'i kirik kaldi; Caskroom kopyasi calisiyor)."""
    import glob
    adaylar = [os.environ.get("PRUVO_OPENSCAD"),
               "/opt/homebrew/bin/openscad",
               "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
               os.path.join(TEST_DIR, ".openscad-yerel",
                            "OpenSCAD.app", "Contents", "MacOS", "OpenSCAD")]
    adaylar += sorted(glob.glob(
        "/opt/homebrew/Caskroom/openscad*/*/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
        reverse=True)
    adaylar.append(shutil.which("openscad"))
    return adaylar


def openscad_yolu(adaylar=None):
    adaylar = openscad_adaylari() if adaylar is None else list(adaylar)
    if not yasak_aktif():
        # YASAK BEYAN EDILMEMIS -> davranis birebir eski hali (yanlis-pozitif yok).
        for yol in adaylar:
            if yol and os.path.exists(yol):
                return yol
        sys.exit("openscad bulunamadi (PRUVO_OPENSCAD ayarlayin)")
    for yol in adaylar:
        if not yol:
            continue
        hukum, tani, cozulen = openscad_hedefi(yol)
        if hukum == "EVET":
            _yasak_cikis(tani)
        if hukum == "OLCULEMEDI":
            _yasak_cikis("hedef cozumlenemedi -> supheli sayilir. " + tani)
        if cozulen and os.path.exists(cozulen):
            # mesru (openscad OLMAYAN) arac: kosmaya izin var. Aday ek arguman
            # tasiyorsa cagrilabilir olan COZUMLENEN yoldur.
            return yol if os.path.exists(yol) else cozulen
    _yasak_cikis("yasak aktifken kosulabilecek openscad-disi bir arac bulunamadi")


def scad_dizini():
    yol = os.environ.get(
        "PRUVO_SCAD_DIR",
        os.path.expanduser("~/dev/pruvo-jenerator/jeneratorler"))
    if not os.path.isdir(yol):
        sys.exit("scad dizini yok: %s (PRUVO_SCAD_DIR ayarlayin)" % yol)
    return yol


def yukle(yol):
    with io.open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def rastgele_set(sema, rnd):
    """Sema izgarasinda gecerli rastgele parametre seti (metin -> varsayilan)."""
    s = {}
    for p in sema["parametreler"]:
        tip = p.get("tip", "sayi")
        if tip == "sayi":
            adim = float(p.get("adim") or 1)
            n = int(round((float(p["max"]) - float(p["min"])) / adim))
            s[p["ad"]] = round(float(p["min"]) + rnd.randint(0, n) * adim, 6)
        elif tip == "secim":
            secenekler = [x["deger"] if isinstance(x, dict) else x
                          for x in p["secenekler"]]
            s[p["ad"]] = rnd.choice(secenekler)
        elif tip == "metin":
            s[p["ad"]] = p.get("varsayilan", "")
        else:
            sys.exit("bilinmeyen tip: %s (%s)" % (tip, p["ad"]))
    return s


def varsayilan_set(sema):
    return dict((p["ad"], p["varsayilan"]) for p in sema["parametreler"])


def js_hacimler(fonksiyon, setler):
    istek = json.dumps({"fonksiyon": fonksiyon, "setler": setler},
                       ensure_ascii=False)
    proc = subprocess.run(
        ["node", os.path.join(TEST_DIR, "hacim-eval.js")],
        input=istek.encode("utf-8"), capture_output=True, timeout=60)
    if proc.returncode != 0:
        sys.exit("hacim-eval.js hata: %s" % proc.stderr.decode("utf-8", "replace"))
    return json.loads(proc.stdout.decode("utf-8"))


def d_bayraklari(esleme, sset):
    """Turkce parametre setini OpenSCAD -D bayraklarina cevirir."""
    bayraklar = []
    deger_esleme = esleme.get("deger_esleme") or {}
    for ad, scad_ad in (esleme.get("esleme") or {}).items():
        if ad not in sset:
            sys.exit("eslemede olan '%s' sette yok" % ad)
        deger = sset[ad]
        if ad in deger_esleme:
            deger = deger_esleme[ad][str(deger)]
        bayraklar.append("-D")
        if isinstance(deger, str):
            bayraklar.append('%s="%s"' % (scad_ad, deger.replace('"', '')))
        else:
            bayraklar.append("%s=%s" % (scad_ad, ("%.6f" % float(deger)).rstrip("0").rstrip(".")))
    for scad_ad, deger in (esleme.get("sabit") or {}).items():
        bayraklar.append("-D")
        if isinstance(deger, str):
            bayraklar.append('%s="%s"' % (scad_ad, deger.replace('"', '')))
        else:
            bayraklar.append("%s=%s" % (scad_ad, ("%.6f" % float(deger)).rstrip("0").rstrip(".")))
    return bayraklar


def scad_hacim(openscad, scad_yol, esleme, sset, tmpdir, etiket):
    """Render + hacim. Cokme (SIGABRT vb.) 2 kez yeniden denenir; israrla cokerse
    None doner (aile 'yerel dogrulanamadi' sayilir, CI'da kosulur — mimar karari
    2026-07-16: OpenSCAD snapshot acilista ara ara SIGABRT atiyor).
    GERCEK scad hatasi (stderr'de ERROR:) yeniden DENENMEZ ve testi durdurur —
    yanlis esleme/parametre sessizce atlanamaz."""
    stl = os.path.join(tmpdir, "%s.stl" % etiket)
    komut = [openscad, "-o", stl] + d_bayraklari(esleme, sset) + [scad_yol]
    for deneme in range(3):
        if os.path.exists(stl):
            os.remove(stl)
        proc = subprocess.run(komut, capture_output=True, timeout=600)
        hata_metni = proc.stderr.decode("utf-8", "replace")
        if proc.returncode == 0 and os.path.exists(stl):
            return stl_hacim.hacim(stl)
        if "ERROR:" in hata_metni:
            sys.exit("openscad GERCEK hata (%s):\n%s\n%s" % (
                etiket, " ".join(komut), hata_metni[-2000:]))
        print("  ... openscad cokme/bos cikti (%s, deneme %d/3, kod %s) — tekrar" %
              (etiket, deneme + 1, proc.returncode))
        import time
        time.sleep(1)
    return None


def aile_dogrula(aile, set_sayisi, rnd, openscad, scad_dir):
    esleme = yukle(os.path.join(ESLEME_DIR, aile + ".json"))
    sema = yukle(os.path.join(URUN_DIR, esleme["urunId"] + ".json"))
    if sema.get("hacimFormulu") != esleme["fonksiyon"]:
        sys.exit("%s: sema.hacimFormulu != esleme.fonksiyon" % aile)
    scad_yol = os.path.join(scad_dir, esleme["scad"])
    if not os.path.exists(scad_yol):
        sys.exit("scad dosyasi yok: %s" % scad_yol)

    setler = [varsayilan_set(sema)]
    for _ in range(set_sayisi):
        setler.append(rastgele_set(sema, rnd))
    js = js_hacimler(esleme["fonksiyon"], setler)

    # taban hacim tutarliligi
    taban = float(sema["tabanHacimMm3"])
    if abs(js[0] - taban) / taban > TABAN_TOLERANS:
        print("  %s KIRMIZI: tabanHacimMm3=%.2f ama fn(varsayilan)=%.2f" %
              (aile, taban, js[0]))
        return False

    hepsi_yesil = True
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, sset in enumerate(setler):
            ref = scad_hacim(openscad, scad_yol, esleme, sset, tmpdir,
                             "%s-%d" % (aile, i))
            if ref is None:
                print("  [ATLA] %-8s yerel dogrulanamadi (openscad israrla cokuyor)"
                      " — CI dogrulamasina birakildi" % aile)
                return "atla"
            sapma = abs(js[i] - ref) / ref * 100.0
            durum = "OK " if sapma <= SINIR_YUZDE else "SAP"
            if sapma > SINIR_YUZDE:
                hepsi_yesil = False
            kisa = ", ".join("%s=%s" % (k, v) for k, v in sorted(sset.items()))
            print("  [%s] %-8s set%d  js=%12.1f  scad=%12.1f  sapma=%5.2f%%  (%s)" %
                  (durum, aile, i, js[i], ref, sapma, kisa[:100]))
    return hepsi_yesil


# ---- OPENSCAD YASAK NOBETCISI (openscad GEREKTIRMEZ) -----------------------
def _calistirilabilir_yaz(yol, govde="#!/bin/sh\nexit 0\n"):
    kok = os.path.dirname(yol)
    if kok and not os.path.isdir(kok):
        os.makedirs(kok)
    with io.open(yol, "w", encoding="utf-8") as f:
        f.write(govde)
    os.chmod(yol, 0o755)
    return yol


def kendini_test():
    """m33 NOBETCISI — POZITIF (yasak tutuyor) VE NEGATIF (mesru is durmuyor) yon.

    Tek yon = olu nobetci: yalniz 'openscad KIRMIZI' iddia edilirse, her seyi
    reddeden bir kapi da testi gecer. O yuzden negatif vakalar (mesru arac
    calisir · yasak beyan edilmemisken davranis DEGISMEZ) ayri vakalardir."""
    vakalar = []

    def bekle(ad, kosul, detay=""):
        vakalar.append((ad, bool(kosul), detay))

    def yolu_dene(adaylar):
        """(sonuc, cikis_kodu) — openscad_yolu()'nu yakalayarak kos (stderr yutulur)."""
        import contextlib
        yakala = io.StringIO()
        try:
            with contextlib.redirect_stderr(yakala):
                return openscad_yolu(adaylar), 0
        except SystemExit as e:
            kod = e.code if isinstance(e.code, int) else 1
            return None, kod

    eski_yasak = os.environ.get(OPENSCAD_YASAK_ORTAM)
    eski_path = os.environ.get("PATH", "")
    tmp = tempfile.mkdtemp(prefix="pruvo-yasak-")
    try:
        binn = os.path.join(tmp, "bin")
        arac = os.path.join(tmp, "arac")
        gercek = _calistirilabilir_yaz(os.path.join(binn, "openscad"))
        buyuk = _calistirilabilir_yaz(os.path.join(binn, "OpenSCAD"))
        stub = _calistirilabilir_yaz(os.path.join(arac, "hacim-stub"))
        bag = os.path.join(binn, "scad-baglanti")   # ADI masum, HEDEFI openscad
        os.symlink(gercek, bag)
        bag2 = os.path.join(arac, "render-arac")    # ADI masum, HEDEFI de masum
        os.symlink(stub, bag2)
        # ADI openscad, HEDEFI masum: yasak ALTINDA yine reddedilir — "openscad"
        # adini tasiyan bir shim'in olcumu YESIL yakmasi sessiz-yesil olurdu.
        maskeli = os.path.join(tmp, "karisik", "openscad")
        os.makedirs(os.path.dirname(maskeli))
        os.symlink(stub, maskeli)

        os.environ[OPENSCAD_YASAK_ORTAM] = "1"
        os.environ["PATH"] = binn + os.pathsep + arac + os.pathsep + eski_path

        # --- POZITIF: yasak TUTMALI (hepsi sifir-disi) ---
        for ad, aday in [
                ("P1 duz ad (PATH)", "openscad"),
                ("P2 MUTLAK yol", gercek),
                ("P3 sembolik bag (ad masum, hedef openscad)", bag),
                ("P4 env sarmali", "env FOO=1 openscad"),
                ("P5 kabuk dolayli cagri", "/bin/sh -c 'openscad'"),
                ("P6 farkli buyuk-kucuk harf", buyuk),
                ("P7 yol + ek arguman", gercek + " -o /tmp/yok.stl"),
                ("P8 arch sarmali (mutlak yol)", "arch -x86_64 " + gercek),
                ("P9 ADI openscad, hedefi masum (maskeli shim)", maskeli),
                ("P10 ADI openscad, diskte YOK (sessizce atlanmaz)",
                 os.path.join(tmp, "yok", "openscad"))]:
            hukum, tani, _c = openscad_hedefi(aday)
            _s, kod = yolu_dene([aday])
            bekle(ad, hukum == "EVET" and kod == YASAK_CIKIS_KODU,
                  "hukum=%s kod=%s (%s)" % (hukum, kod, tani))

        # --- OLCULEMEDI: cozulemeyen/supheli cagri YESIL DEGIL ---
        for ad, aday in [
                ("O1 PATH'te cozulemeyen ad", "render-arac-yok-olan"),
                ("O2 jetonlanamayan komut", "render-arac 'kapanmamis"),
                ("O3 diskte olmayan mutlak yol (openscad-disi ad)",
                 os.path.join(tmp, "yok", "render-arac"))]:
            hukum, tani, _c = openscad_hedefi(aday)
            _s, kod = yolu_dene([aday])
            bekle(ad, hukum == "OLCULEMEDI" and kod == YASAK_CIKIS_KODU,
                  "hukum=%s kod=%s (%s)" % (hukum, kod, tani))

        # --- NEGATIF: mesru is DURMAMALI ---
        hukum, tani, _c = openscad_hedefi(stub)
        sonuc, kod = yolu_dene([stub])
        bekle("N1 mesru baska arac (yasak AKTIF) kosabiliyor",
              hukum == "HAYIR" and kod == 0 and sonuc == stub,
              "hukum=%s kod=%s sonuc=%s (%s)" % (hukum, kod, sonuc, tani))

        hukum, _t, _c = openscad_hedefi(bag2)
        sonuc, kod = yolu_dene([bag2])
        bekle("N2 masum sembolik bag (hedef de masum) kosabiliyor",
              hukum == "HAYIR" and kod == 0 and sonuc == bag2,
              "hukum=%s kod=%s sonuc=%s" % (hukum, kod, sonuc))

        # NOT: var olmayan bir aday BILEREK 'atlanmaz' — cozulemeyen hedef
        # OLCULEMEDI'dir (O3). Mesru is durmasin diye kural sudur: ONCE gelen
        # mesru arac secilir, arkasindaki openscad'a HIC bakilmaz.
        sonuc, kod = yolu_dene([stub, gercek])
        bekle("N3 mesru arac ONCE geliyorsa openscad'a hic bakilmaz",
              kod == 0 and sonuc == stub, "kod=%s sonuc=%s" % (kod, sonuc))

        # --- NEGATIF: yasak BEYAN EDILMEMISKEN davranis DEGISMEZ (regresyon capasi) ---
        os.environ.pop(OPENSCAD_YASAK_ORTAM, None)
        sonuc, kod = yolu_dene([gercek])
        bekle("N4 yasak KAPALI iken openscad yolu AYNEN donuyor",
              kod == 0 and sonuc == gercek, "kod=%s sonuc=%s" % (kod, sonuc))
        _s, kod = yolu_dene([os.path.join(tmp, "yok", "hic")])
        bekle("N5 yasak KAPALI + hicbir aday yok -> eski 'bulunamadi' hatasi",
              kod == 1, "kod=%s" % kod)
    finally:
        if eski_yasak is None:
            os.environ.pop(OPENSCAD_YASAK_ORTAM, None)
        else:
            os.environ[OPENSCAD_YASAK_ORTAM] = eski_yasak
        os.environ["PATH"] = eski_path
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)

    kirmizi = [v for v in vakalar if not v[1]]
    print("OPENSCAD YASAK NOBETCISI — %d/%d YESIL" % (len(vakalar) - len(kirmizi),
                                                      len(vakalar)))
    for ad, yesil, detay in vakalar:
        print("  %s %-52s %s" % ("+" if yesil else "-", ad, detay if not yesil else ""))
    return 1 if kirmizi else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aileler", nargs="*", help="aile adi (esleme/<ad>.json)")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--set", type=int, default=3, help="rastgele set sayisi")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--kendini-test", action="store_true",
                    help="openscad yasagi nobetcisi (openscad GEREKTIRMEZ)")
    args = ap.parse_args()

    if args.kendini_test:
        sys.exit(kendini_test())

    # PARALEL GUVENLIK: ayni anda birden cok aile dogrulanabilir (paralel muhendis
    # oturumlari); hacim.js'in yeniden montaji + kosum tek kilit altinda serilestirilir.
    import fcntl
    kilit = open(os.path.join(TEST_DIR, ".dogrula-kilit"), "w")
    fcntl.flock(kilit, fcntl.LOCK_EX)

    # once monte et — hacim.js her zaman aile dosyalarinin guncel birlesimi.
    # Baska bir is aile dosyasini o an yaziyor olabilir -> kisa tekrar dene.
    import time
    for deneme in range(5):
        proc = subprocess.run([sys.executable, os.path.join(TEST_DIR, "birlestir.py")],
                              capture_output=True)
        if proc.returncode == 0:
            break
        time.sleep(2)
    if proc.returncode != 0:
        sys.exit("birlestir.py hata:\n%s%s" % (proc.stdout.decode("utf-8", "replace"),
                                               proc.stderr.decode("utf-8", "replace")))

    if args.hepsi:
        aileler = sorted(f[:-5] for f in os.listdir(ESLEME_DIR)
                         if f.endswith(".json"))
    else:
        aileler = args.aileler
    if not aileler:
        sys.exit("aile verin ya da --hepsi kullanin")

    seed = args.seed if args.seed is not None else random.SystemRandom().randint(0, 10 ** 6)
    print("tohum (tekrar icin --seed %d), sinir <=%%%.1f, rastgele set=%d" %
          (seed, SINIR_YUZDE, args.set))
    rnd = random.Random(seed)
    openscad = openscad_yolu()
    scad_dir = scad_dizini()

    kirmizi, atlanan = [], []
    for aile in aileler:
        sonuc = aile_dogrula(aile, args.set, rnd, openscad, scad_dir)
        if sonuc == "atla":
            atlanan.append(aile)
        elif not sonuc:
            kirmizi.append(aile)
    if atlanan:
        print("YEREL DOGRULANAMAYAN aileler (CI'da kosulacak): %s" % ", ".join(atlanan))
    if kirmizi:
        print("KIRMIZI aileler: %s" % ", ".join(kirmizi))
        sys.exit(1)
    print("YEREL YESIL: %d, CI'YA KALAN: %d" % (len(aileler) - len(atlanan), len(atlanan)))


if __name__ == "__main__":
    main()

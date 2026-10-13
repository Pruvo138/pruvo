#!/usr/bin/env python3
"""Yedek dusus SINIF ekseni: onbellek kuculmesi karantinasiz gecer, urun verisi/bilinmeyen RED.

NEDEN VAR (13 Eki 2026): `.stl-r2-manifest.json` (R2 idempotens ONBELLEGI, yeniden
uretilebilir) Drive kanonigi 2.705.650 B -> canli 158.930 B kuculdu; koruma 220 ARDISIK
kosumu `SINIF=bayt-dususu ATLANAN=1` ile kirmiziya yakti ve gercek dususleri o imzanin
altina gomdu. Onarim `tools/yedekle.py` icinde `DUSUS_OLCULEN_SINIF` +
`DUSUS_ONBELLEK_SINIFI` + `_dusus_sinifi`. Test HERMETIKTIR: gecici "Drive" + gecici kalp
(`DUSUS_KAYIT_LOG` gecici dizine cevrilir); gercek Drive'a / ~/.claude/cron'a DOKUNMAZ.

VAKALAR (her biri GERCEK `_drive_kopyala_karantinali` + `karantina_hukmu_bas` ile; kalp
ARDISIK=7 ile tohumlanir — canli kronik kirmiziyi taklit eder)
  V1 `.stl-r2-manifest.json` %97 kuculur  -> karantina YOK, rc=0, ARDISIK artmaz,
                                             `ONBELLEK_KUCULDU` satiri, kanonik guncel
  V2 `urunler.json` %5'ine kuculur         -> KIRMIZI (karantina + rc=1, ARDISIK=8)
  V3 sinifi bilinmeyen `x.json` esigin altina (%45'ine) kuculur -> KIRMIZI
  V4 onbellek ADLI dosya `jenerator/urunler/` altinda -> KIRMIZI (olculen sinif oncelikli)
MUTANTLAR (izole kopyada; biri bile OLMEZSE test KIRMIZI)
  M1 sinif kontrolu daima "onbellek" -> V2 kirmizi yanmali
  M2 onbellek kumesi BOS             -> V1 kirmizi yanmali
YAPI: onbellek kumesi EK_EVLER["pruvo"] icinde · UCUCU_MANIFESTLER ile kesisim BOS ·
olculen globlar urun verisini taniyor.

Cikis: 0 = VAKA=4/4 MUTANT=2/2 + YAPI · 1 = dustu · 2 = mutant capasi yok (OLCULEMEDI).
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
KANONIK = os.path.join(TOOLS, "yedekle.py")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)   # drive_yolu

TOHUM_ARDISIK = 7

MUTANTLAR = (
    ("M1-sinif-daima-onbellek", "V2",
     "    if _dusus_sinifi(kaynak) != \"onbellek\":\n        return False\n",
     "    if False:\n        return False\n"),
    ("M2-onbellek-kumesi-bos", "V1",
     "_ONBELLEK_KULLANILDI = []\n",
     "DUSUS_ONBELLEK_SINIFI = frozenset()\n_ONBELLEK_KULLANILDI = []\n"),
)


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def json_yaz(yol, n):
    """n kayitli JSON listesi; bayt olcusu kayit sayisiyla dogrusal."""
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump([{"id": "k%05d" % i, "v": "x" * 40} for i in range(n)], f)


def kosum(mod, kok, vaka, goreli, eski_n, yeni_n):
    """Tek dosyalik yedek kosumu. Doner: (rc, karantina, ardisik, cikti, guncel_mi)."""
    tmp = os.path.join(kok, vaka)
    mod.DUSUS_KAYIT_LOG = os.path.join(tmp, "ops", "yedek-dusus.log")
    os.makedirs(os.path.dirname(mod.DUSUS_KAYIT_LOG))
    with open(mod._dusus_kalp_yerel(), "w", encoding="utf-8") as f:
        json.dump({"ardisik": TOHUM_ARDISIK, "gecmis": []}, f)
    for liste in (mod._KORUMA_KARANTINA, mod._KORUMA_AYRINTI, mod._ONBELLEK_KULLANILDI,
                  mod._BEYAN_KULLANILDI, mod._UCUCU_KULLANILDI):
        del liste[:]
    backup = os.path.join(tmp, "drive")
    varis = os.path.join(backup, "ek", "evler", "pruvo", goreli)
    kaynak = os.path.join(tmp, "ev", goreli)
    json_yaz(varis, eski_n)
    json_yaz(kaynak, yeni_n)
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        mod._drive_kopyala_karantinali(kaynak, varis)
        rc = mod.karantina_hukmu_bas(backup)
    kayit = mod._dusus_kaydi_oku(backup)
    return (rc, len(mod._KORUMA_KARANTINA), int(kayit.get("ardisik") or 0),
            tampon.getvalue(), sha(varis) == sha(kaynak))


def vakalar(mod, kok, etiket):
    """Doner: {vaka: gecti_mi}."""
    tmp = os.path.join(kok, etiket)
    s = {}
    rc, kar, ard, cikti, guncel = kosum(mod, tmp, "V1", ".stl-r2-manifest.json", 1000, 30)
    s["V1"] = (rc == 0 and kar == 0 and ard <= TOHUM_ARDISIK and guncel
               and "ONBELLEK_KUCULDU=.stl-r2-manifest.json eski=" in cikti
               and "YEDEK=TAM" in cikti)
    rc, kar, ard, cikti, guncel = kosum(mod, tmp, "V2", "urunler.json", 1000, 50)
    s["V2"] = (rc == 1 and kar == 1 and ard == TOHUM_ARDISIK + 1 and not guncel
               and "ONBELLEK_KUCULDU" not in cikti)
    rc, kar, ard, cikti, guncel = kosum(mod, tmp, "V3", "x.json", 1000, 450)
    s["V3"] = rc == 1 and kar == 1 and not guncel and "ONBELLEK_KUCULDU" not in cikti
    rc, kar, ard, cikti, guncel = kosum(
        mod, tmp, "V4", os.path.join("jenerator", "urunler", ".marka-kapsama.json"), 1000, 30)
    s["V4"] = rc == 1 and kar == 1 and not guncel
    return s


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def yapi_olc(mod):
    kume = set(mod.DUSUS_ONBELLEK_SINIFI)
    return {
        "onbellek-EK_EVLER-icinde": kume <= set(mod.EK_EVLER["pruvo"]),
        "onbellek-ucucu-kesisim-bos": not (kume & set(mod.UCUCU_MANIFESTLER)),
        "olculen-urun-verisi": all(
            mod._dusus_sinifi(y) == "olculen" for y in (
                "/a/urunler.json", "/a/arsiv/urunler-arsiv.json", "/a/.urun-kaynaklari.json",
                "/a/urun-kaynaklari.json", "/a/jenerator/urunler/seri.json")),
        "bilinmeyen-varsayilan": mod._dusus_sinifi("/a/x.json") == "bilinmeyen",
    }


def main():
    kok = tempfile.mkdtemp(prefix="yedek-onbellek-test-")
    rc = 1
    try:
        mod = modul_yukle(KANONIK, "yedekle_onbellek_test_%d" % os.getpid())
        taban = vakalar(mod, kok, "taban")
        for v in sorted(taban):
            print("%s %s" % (v, "GECTI" if taban[v] else "DUSTU"))
        yapi = yapi_olc(mod)
        for k in sorted(yapi):
            print("YAPI %s %s" % (k, "GECTI" if yapi[k] else "DUSTU"))

        olen, olculemedi = 0, False
        kaynak_metin = open(KANONIK, encoding="utf-8").read()
        for ad, hedef_vaka, eski, yeni in MUTANTLAR:
            if kaynak_metin.count(eski) != 1:
                print("MUTANT %s OLCULEMEDI (capa %d kez)" % (ad, kaynak_metin.count(eski)))
                olculemedi = True
                continue
            mdir = os.path.join(kok, ad)
            os.makedirs(mdir)
            with open(os.path.join(mdir, "yedekle.py"), "w", encoding="utf-8") as f:
                f.write(kaynak_metin.replace(eski, yeni))
            mmod = modul_yukle(os.path.join(mdir, "yedekle.py"),
                               "yedekle_onbellek_%s_%d" % (ad.split("-")[0], os.getpid()))
            ms = vakalar(mmod, kok, ad + "-kum")
            oldu = not ms[hedef_vaka]
            olen += 1 if oldu else 0
            print("MUTANT %s hedef=%s %s" % (ad, hedef_vaka,
                                             "OLDU (kirmizi)" if oldu else "HAYATTA"))

        vg = sum(1 for v in taban.values() if v)
        print("VAKA=%d/%d MUTANT=%d/%d" % (vg, len(taban), olen, len(MUTANTLAR)))
        if olculemedi:
            rc = 2
        elif vg == len(taban) and olen == len(MUTANTLAR) and all(yapi.values()):
            rc = 0
    finally:
        shutil.rmtree(kok, ignore_errors=True)
        print("GECICI_SILINDI=%s var=%s" % (kok, os.path.exists(kok)))
    return rc


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Onizleme derleme paketini toplar ve GIZLI R2 bucket'ina yukler.

PAKET = eslem-ozel.json + eslemin isaret ettigi .scad kaynaklari. Ikisi de SIRDIR
(uyelik ureteci kodu/degisken adlari) — public repoya ASLA girmez (gitignore).
Kanonik kopya R2 `pruvo-ozel` bucket'i: CI imaj derlerken oradan ceker
(.github/workflows/onizleme-imaj.yml), boylece sir GitHub'a ugramaz.

PAKETE AYRICA BIZIM ureteclerimiz girer (ACIK_AILELER): pruvo-jenerator .scad'lari
tedarikci kodu DEGILDIR, eslemleri PUBLIC jenerator/test/esleme/ dosyalarindan
uretilir (tek kaynak — test ile onizleme eslemi ayrisamaz). Bu aileler icin sir
katmani yoktur; paket ici eslem dosyasina derleme aninda birlestirilirler.

Kaynaklar (SALT OKUNUR — ana repoya hicbir sey yazilmaz):
  - eslem: <repo>/onizleme/derleyici/eslem-ozel.json (gitignore'lu yerel dosya)
  - .scad: PRUVO_UYELIK_DIR (varsayilan /Users/okan/dev/pruvo/.uyelik-kodlar)
  - bizim .scad: PRUVO_JENERATOR_DIR (vars. ~/dev/pruvo-jenerator/jeneratorler)

Kullanim:
  python3 tools/onizleme-paket-yukle.py --yerel <dizin>   # sadece topla (test/kabul icin)
  python3 tools/onizleme-paket-yukle.py                   # topla + R2'ye yukle
Yukleme yerel wrangler oturumuyla yapilir (token gerekmez):
  npx wrangler r2 object put pruvo-ozel/onizleme/paket-v<N>.tar.gz --file ...
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESLEM_YOL = os.path.join(REPO, "onizleme", "derleyici", "eslem-ozel.json")
BUCKET = "pruvo-ozel"

# BIZIM ureteclerimiz (pruvo-jenerator v2): aile-id -> public test eslem adi.
# Eslem tek kaynagi jenerator/test/esleme/<ad>.json (dogrula.py ile ayni dosya).
ACIK_AILELER = {
    "olcuye-ozel-baglanti-konektor": "konektor",
    "olcuye-ozel-montaj-braketi": "braket",
    "ozel-disli-kramayer-uretimi": "disli",
    # Yeni sari aileler 1. dalga (2026-07-17) — bizim ureteclerimiz
    "olcuye-ozel-hortum-adaptoru": "adaptor",
    "olcuye-ozel-kutu-organizer": "kutu",
    "olcuye-ozel-vidali-kavanoz-tapa": "kavanoz",
}


def acik_eslem_uret(ad):
    """jenerator/test/esleme/<ad>.json -> server.py eslem blogu.
    Sayi parametreleri katsayi-1 dogrusal terim, secim parametreleri
    deger_esleme tablosu (yoksa kimlik tablosu), sabitler aynen."""
    with open(os.path.join(REPO, "jenerator", "test", "esleme",
                           ad + ".json"), encoding="utf-8") as f:
        test_eslem = json.load(f)
    with open(os.path.join(REPO, "jenerator", "urunler",
                           test_eslem["urunId"] + ".json"), encoding="utf-8") as f:
        sema = json.load(f)
    tipler = dict((p["ad"], p) for p in sema["parametreler"])
    sayisal, secim = {}, {}
    deger_esleme = test_eslem.get("deger_esleme") or {}
    for param, scad_ad in (test_eslem.get("esleme") or {}).items():
        tanim = tipler.get(param)
        if tanim is None:
            sys.exit("%s: eslemdeki '%s' semada yok" % (ad, param))
        if tanim.get("tip", "sayi") == "sayi":
            sayisal[scad_ad] = {"terimler": {param: 1}}
        elif tanim["tip"] == "secim":
            tablo = deger_esleme.get(param)
            if tablo is None:  # kimlik: sema degerleri scad'a aynen gider
                tablo = dict((s["deger"] if isinstance(s, dict) else s,
                              s["deger"] if isinstance(s, dict) else s)
                             for s in tanim["secenekler"])
            secim[scad_ad] = {"param": param, "tablo": tablo}
        else:
            sys.exit("%s: '%s' tipi (%s) onizlemeye eslenemez" %
                     (ad, param, tanim["tip"]))
    return test_eslem["urunId"], {
        "scad": test_eslem["scad"],
        "secici": None,
        "ortak": {"sayisal": sayisal, "secim": secim,
                  "sabit": test_eslem.get("sabit") or {}},
        "varyantlar": None,
    }, test_eslem["scad"]


def topla(hedef, uyelik_dir, jenerator_dir):
    if not os.path.exists(ESLEM_YOL):
        sys.exit("eslem-ozel.json yok: %s (gitignore'lu — R2'deki paketten geri alin: "
                 "npx wrangler r2 object get %s/onizleme/paket-v<N>.tar.gz)" %
                 (ESLEM_YOL, BUCKET))
    with open(ESLEM_YOL, encoding="utf-8") as f:
        eslem = json.load(f)
    os.makedirs(hedef, exist_ok=True)
    eksik = []
    for aile, tanim in eslem["aileler"].items():
        scadlar = {tanim["scad"]}
        for varyant in (tanim.get("varyantlar") or {}).values():
            if varyant and varyant.get("scad"):
                scadlar.add(varyant["scad"])  # cift-uretecli aile (vida, yay)
        for scad in sorted(scadlar):
            kaynak = os.path.join(uyelik_dir, scad)
            if not os.path.exists(kaynak):
                eksik.append("%s (%s)" % (scad, aile))
                continue
            shutil.copy2(kaynak, os.path.join(hedef, scad))
    if eksik:
        sys.exit("eksik .scad kaynagi: %s (PRUVO_UYELIK_DIR dogru mu?)" % ", ".join(eksik))
    # bizim uretecler: public eslemden uret + scad'i pruvo-jenerator'den kopyala
    for aile_id, ad in sorted(ACIK_AILELER.items()):
        urun_id, blok, scad = acik_eslem_uret(ad)
        if urun_id != aile_id:
            sys.exit("ACIK_AILELER tutarsiz: %s != %s" % (urun_id, aile_id))
        if aile_id in eslem["aileler"]:
            sys.exit("%s hem eslem-ozel.json'da hem ACIK_AILELER'de" % aile_id)
        eslem["aileler"][aile_id] = blok
        kaynak = os.path.join(jenerator_dir, scad)
        if not os.path.exists(kaynak):
            sys.exit("bizim .scad yok: %s (PRUVO_JENERATOR_DIR dogru mu?)" % kaynak)
        shutil.copy2(kaynak, os.path.join(hedef, scad))
    with open(os.path.join(hedef, "eslem-ozel.json"), "w", encoding="utf-8") as f:
        json.dump(eslem, f, ensure_ascii=False, indent=2)
    return eslem.get("surum", 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", metavar="DIZIN",
                    help="paketi bu dizine topla, YUKLEME (kabul testleri kullanir)")
    ap.add_argument("--uyelik-dir",
                    default=os.environ.get("PRUVO_UYELIK_DIR",
                                           "/Users/okan/dev/pruvo/.uyelik-kodlar"))
    ap.add_argument("--jenerator-dir",
                    default=os.environ.get(
                        "PRUVO_JENERATOR_DIR",
                        os.path.expanduser("~/dev/pruvo-jenerator/jeneratorler")))
    args = ap.parse_args()

    if args.yerel:
        surum = topla(args.yerel, args.uyelik_dir, args.jenerator_dir)
        print("paket toplandi (v%d): %s" % (surum, args.yerel))
        return

    with tempfile.TemporaryDirectory() as tmp:
        paket_dizin = os.path.join(tmp, "paket")
        surum = topla(paket_dizin, args.uyelik_dir, args.jenerator_dir)
        arsiv = os.path.join(tmp, "paket.tar.gz")
        with tarfile.open(arsiv, "w:gz") as tar:
            for ad in sorted(os.listdir(paket_dizin)):
                tar.add(os.path.join(paket_dizin, ad), arcname=ad)
        anahtar = "onizleme/paket-v%d.tar.gz" % surum
        # Yerel wrangler oturumu (token'siz). shell degiskeni yok — komut listesi.
        komut = ["npx", "wrangler", "r2", "object", "put",
                 BUCKET + "/" + anahtar, "--file", arsiv, "--remote"]
        proc = subprocess.run(komut, cwd=REPO, capture_output=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout.decode("utf-8", "replace"))
            sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
            sys.exit("R2 yuklemesi basarisiz (wrangler oturumu acik mi?)")
        print("yuklendi: r2://%s/%s (%d bayt)" %
              (BUCKET, anahtar, os.path.getsize(arsiv)))
        # 'guncel' takma adi: CI hep bunu ceker, surumlu kopya gecmis icin durur.
        komut2 = ["npx", "wrangler", "r2", "object", "put",
                  BUCKET + "/onizleme/paket-guncel.tar.gz", "--file", arsiv, "--remote"]
        proc2 = subprocess.run(komut2, cwd=REPO, capture_output=True)
        if proc2.returncode != 0:
            sys.exit("paket-guncel.tar.gz yuklemesi basarisiz")
        print("yuklendi: r2://%s/onizleme/paket-guncel.tar.gz" % BUCKET)
        # NOT (2026-07-16): ONIZLEME_PAKET_B64 yedegi KALDIRILDI (Okan karari). CI artik
        # paketi dogrudan R2'den ceker: R2_ERISIM_ID/R2_GIZLI_ANAHTAR secret'lari
        # pruvo-ozel'e SALT-OKUMA yetkili 'pruvo-ozel-okuma-ci' token'idir.


if __name__ == "__main__":
    main()

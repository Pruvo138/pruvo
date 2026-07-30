#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Üyelik ürünlerini toplu listeleme / kaldırma güvenlik betiği.

Üyelik tedarikçilerinin modelleri YALNIZCA aylık üyelik aktifken satılabilir.
Üyelik biterse bu ürünler siteden çekilmelidir (lisans ihlali olmasın).

Üyelik bilgisi PUBLIC urunler.json'da DEĞİL, gizli .urun-kaynaklari.json'dadır
(her ürün kaydında "uyelik" anahtarı — ticari mahremiyet, 2026-07-15 taşındı).
Bu betik oradan bulur; istenirse ürünleri tools/duzelt.py --sil ile kaldırır
(guard'ın meşru yolu) ve R2'deki görsellerini siler.

Kullanım:
    python3 tools/uyelik-cek.py                  # sadece LİSTELE (dry-run, güvenli)
    python3 tools/uyelik-cek.py --uygula         # urunler.json'dan KALDIR
    python3 tools/uyelik-cek.py --uygula --r2    # ayrıca R2 görsellerini de sil
    python3 tools/uyelik-cek.py --etiket <ad>    # sadece belirli üyeliği hedefle

Kaldırdıktan sonra: git add urunler.json && commit && push (CI sayfaları yeniden üretir).
NOT: Ücretsiz gear generator üyelik biterse CC BY'a döner — istersen onu kaldırmak yerine
`lisans` alanını geri koyup (atıflı) tutabilirsin.
"""
import os, sys, json, subprocess, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "urunler.json")
KAYNAK_PATH = os.path.join(ROOT, ".urun-kaynaklari.json")
DUZELT = os.path.join(ROOT, "tools", "duzelt.py")
R2_MOD_PATH = os.path.join(ROOT, "tools", "r2-upload.py")


def _r2_modul():
    """tools/r2-upload.py'yi yükle (ad tirelidir, düz import edilemez).
    R5 silme kapısının TEK kopyası orada; burada ikinci kopya AÇILMAZ."""
    spec = importlib.util.spec_from_file_location("r2_upload_mod", R2_MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    args = sys.argv[1:]
    uygula = "--uygula" in args
    r2 = "--r2" in args
    etiket = None
    if "--etiket" in args:
        etiket = args[args.index("--etiket") + 1]

    data = json.load(open(JSON_PATH, encoding="utf-8"))
    kaynak = json.load(open(KAYNAK_PATH, encoding="utf-8"))
    uyelik_by_id = {uid: e.get("uyelik") for uid, e in kaynak.items()
                    if isinstance(e, dict) and e.get("uyelik")}
    hedef = [o for o in data
             if o.get("id") in uyelik_by_id
             and (etiket is None or uyelik_by_id[o["id"]] == etiket)]

    if not hedef:
        print("Üyelik etiketli ürün yok.")
        return

    print("Üyelik etiketli %d ürün:" % len(hedef))
    for o in hedef:
        print("  - %s  [uyelik=%s]  %s" % (o["id"], uyelik_by_id[o["id"]], o.get("baslik", "")))

    if not uygula:
        print("\n(dry-run) Kaldırmak için: python3 tools/uyelik-cek.py --uygula [--r2]")
        return

    if r2:
        import boto3
        cfg = json.load(open(os.path.join(ROOT, ".r2-credentials.json")))
        s3 = boto3.client("s3", endpoint_url=cfg["endpoint"],
                          aws_access_key_id=cfg["access_key"],
                          aws_secret_access_key=cfg["secret"], region_name="auto")
        base = cfg["public_base"] + "/"
        # R5 (30 Tem 2026): silme çağrısının kendi başarısı KANIT DEĞİL — silme sonrası
        # BAĞIMSIZ varlık kontrolü yapılır, nesne hâlâ görünüyorsa RAISE (fail-closed).
        # Eskiden burada koşulsuz "R2 silindi:" basılıyordu = sessiz-hata sınıfı.
        r2mod = _r2_modul()
        var_mi = r2mod.s3_var_mi(s3, cfg["bucket"])
        sil = lambda k: s3.delete_object(Bucket=cfg["bucket"], Key=k)
        for o in hedef:
            for url in o.get("gorseller", []):
                if url.startswith(base):
                    key = url[len(base):]
                    sonuc = r2mod.sil_ve_dogrula(key, var_mi, sil)
                    print("  R2 %s: %s" % (sonuc, key))

    # duzelt.py --sil = guard'in mesru silme yolu (dogrudan json.dump guard'ca geri alinir)
    for o in hedef:
        subprocess.run([sys.executable, DUZELT, o["id"], "--sil", "uyelik bitti"], check=True)
    print("\n%d ürün urunler.json'dan kaldırıldı." % len(hedef))
    print("Şimdi: git add urunler.json && commit && push")


if __name__ == "__main__":
    main()

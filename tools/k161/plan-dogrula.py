#!/usr/bin/env python3
"""K161-ifsa plan dogrulayici — gercek urunler.json'a DOKUNMAZ.

Islemler.json'u TEMPLATE altinda kurulan kopya katalogda uygular, kopyada
denetim-kapisi.py'yi --tum-katalog --envanter ile kosar, TOPLAM VURUS
(ifsa/*) ve kural kirilimini olcer.

Kullanim:
  python3 tools/k161/plan-dogrula.py [<islemler.json>]

Cikti:
  - "ONCE" ve "SONRA" vurus sayilari
  - Hangi kurallardan kac vurus kaldigi
  - Ayni kopyada aciklama DISINDA baska alan degisip degismedigi (baslik disi)
  - rc=0 (butun kontroller OK), rc=2 (vurus > esik), rc=3 (yanlis alan degisimi)
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path("/Users/okan/dev/pruvo")
DEFAULT_ISLEMLER = Path("/Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/islemler.json")
ESIK = 21                        # ifsa/* vurusu icin ust sinir (hedef)
KABUL_DOSYA_ALANLARI = {"aciklama", "baslik"}  # izin verilen alanlar


def calistir(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("islemler", nargs="?", default=str(DEFAULT_ISLEMLER))
    ap.add_argument("--esik", type=int, default=ESIK)
    args = ap.parse_args()
    islemler_path = Path(args.islemler)
    if not islemler_path.exists():
        print(f"HATA: {islemler_path} bulunamadi", file=sys.stderr)
        return 4

    with open(islemler_path, encoding="utf-8") as f:
        islemler_doc = json.load(f)
    islemler = islemler_doc.get("islemler") or []
    print(f"islemler.json: {len(islemler)} kayit")

    # KOPYA KATALOG KUR
    with tempfile.TemporaryDirectory(prefix="k161-dogrula-") as tmp:
        tmp = Path(tmp)
        kopya = tmp / "katalog"
        # urunler.json ve tools/ disinda dosya TASIMA (sir dosyasi yok zaten, ama .env*
        # / *.key gibi kalintilari da tasima; shutil.copytree ignores ile).
        def ignore(_dir, names):
            return [n for n in names if n.startswith(".") and n not in {".claude"}]
        # Sadece urunler.json + tools/ gerekiyor
        shutil.copy(ROOT / "urunler.json", kopya.parent / "urunler.json") if False else None
        kopya.mkdir(parents=True)
        shutil.copy(ROOT / "urunler.json", kopya / "urunler.json")
        shutil.copytree(ROOT / "tools", kopya / "tools",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
        # duzelt.py icin gerekli olan diger dosyalar (varsa) — minimal kapsam:
        # .urun-kaynaklari.json yoksa duzelt.py siklet edebilir; ihtiyacimiz yok cunku
        # duzelt.py'yi --toplu ile calistirip sadece aciklama/baslik degistiriyoruz.
        gerekli = [".urun-kaynaklari.json"]
        for f in gerekli:
            src = ROOT / f
            if src.exists():
                shutil.copy(src, kopya / f)

        # islemler'i kopya icinde uygula — duzelt.py kullanmadan dogrudan (cunku duzelt.py
        # ek kontroller yapar; biz k161 icin sadece alan yazmak istiyoruz)
        with open(kopya / "urunler.json", encoding="utf-8") as f:
            urunler = json.load(f)

        id_index = {u.get("id"): u for u in urunler if isinstance(u, dict)}
        degisim_sayac = {"baslik": 0, "aciklama": 0, "diger": 0}
        tutarsiz = []
        for op in islemler:
            uid = op.get("id")
            alan = op.get("alan")
            yeni = op.get("deger")
            if alan not in KABUL_DOSYA_ALANLARI:
                degisim_sayac["diger"] += 1
                tutarsiz.append((uid, alan, "alan disi"))
                continue
            urun = id_index.get(uid)
            if not urun:
                tutarsiz.append((uid, alan, "id bulunamadi"))
                continue
            if not isinstance(yeni, str):
                tutarsiz.append((uid, alan, "deger str degil"))
                continue
            if alan not in urun:
                tutarsiz.append((uid, alan, "kayitta alan yok"))
                continue
            eski = urun.get(alan)
            if eski == yeni:
                # ayniysa degisim yok; sayac arttirma
                continue
            urun[alan] = yeni
            degisim_sayac[alan] += 1

        if tutarsiz:
            print(f"HATA: {len(tutarsiz)} tutarsiz islem:")
            for t in tutarsiz[:5]:
                print(f"  {t}")
            return 3

        with open(kopya / "urunler.json", "w", encoding="utf-8") as f:
            json.dump(urunler, f, ensure_ascii=False, indent=2)

        print(f"kullanilan dosya: {kopya}")
        print(f"alan degisimi   : {degisim_sayac}")

        # DENETIM — ONCE karsilastirma icin once gercek katalogda ne ciktiyordu?
        # Bu spec'in istegi: ONCE/SONRA vurus sayisi
        # ONCE: rapor dosyasindaki ihlal sayisi
        rapor_path = ROOT / ".thing-cache/denetim-kapisi-rapor.json"
        with open(rapor_path, encoding="utf-8") as f:
            onceden = json.load(f)
        onceden_ifsa = [i for i in onceden["ihlal"] if i["kapi"].startswith("ifsa/")]
        print(f"\nONCE  vurus (rapor): {len(onceden_ifsa)}")

        # SONRA — kopya katalogda denetim calistir
        # --tum-katalog (katalog genelinde) — envanteri acar (her urunu sayar)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(kopya) + os.pathsep + env.get("PYTHONPATH", "")
        # denetim-kapisi.py modulu import — Python 3.14'te sys.path + namespace
        # package kombinasyonu garip davranabildigi icin spec_from_file_location ile
        # yukluyoruz; ama once kopya/tools'un sys.path'te olmasi lazim (git_ortami
        # kardes import). Tools dizinine __init__.py OLMADIGI icin normal import
        # bazen calismiyor.
        sys.path.insert(0, str(kopya / "tools"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "denetim_kapisi", str(kopya / "tools" / "denetim-kapisi.py"))
        dk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dk)
        with open(kopya / "urunler.json", encoding="utf-8") as f:
            kopya_urunler = json.load(f)
        # tum-katalog: tum urunleri yeni gibi isle (HEAD ile ayniymis gibi)
        ids = {u.get("id") for u in kopya_urunler if isinstance(u, dict)}
        rapor_sonra = dk.denetle(kopya_urunler, list(ids), set(ids), {})
        sonra_ifsa = [i for i in rapor_sonra["ihlal"] if i["kapi"].startswith("ifsa/")]
        print(f"SONRA vurus (kopya): {len(sonra_ifsa)}")

        # kural kirilimi
        kirilim = {}
        for it in sonra_ifsa:
            kirilim[it["kapi"]] = kirilim.get(it["kapi"], 0) + 1
        if kirilim:
            print("\nkalan ifsa kirilimi:")
            for k, v in sorted(kirilim.items(), key=lambda kv: -kv[1]):
                print(f"  {v:3d}  {k}")

        # ayrintili ilk 30
        if sonra_ifsa:
            print("\nilk 30 kalan vurus:")
            for it in sonra_ifsa[:30]:
                g = it.get("gerekce", "")[:100]
                print(f"  - [{it['kapi']}] {it['id']}: {g}")

        # UYARI (bloklamaz) sayisi
        uyari_ifsa = [i for i in rapor_sonra.get("eskalasyon", [])
                      if i["kapi"].startswith("ifsa-uyari/")]
        print(f"\nifsa-uyari (bloklamaz): {len(uyari_ifsa)}")

        # muafiyet IZI
        muaf_ifsa = [i for i in rapor_sonra.get("ifsa_muaf", [])
                     if i["kapi"].startswith("ifsa-muaf/")]
        print(f"ifsa-muaf  (iz, hukme girmez): {len(muaf_ifsa)}")

        # HUKUM
        if len(sonra_ifsa) <= args.esik:
            print(f"\nKABUL: ifsa vurus {len(sonra_ifsa)} <= esik {args.esik}")
            return 0
        else:
            print(f"\nRED: ifsa vurus {len(sonra_ifsa)} > esik {args.esik}")
            return 2


if __name__ == "__main__":
    sys.exit(main())

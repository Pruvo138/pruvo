#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urun-arsiv-govdesiz.py — urun silme arsivini GOVDESIZ sekle indirir ve DOGRULAR.

BaBa 20 Eki 13:4x hukmu (1) / Okan kurali 6 Eki ("sil = TAMAMEN silinir, arsiv YOK"):
`arsiv/urunler-arsiv.json` public repoda silinen urunun TAM govdesini (`kayit`) tasiyordu.
Sekil tek kaynakta: tools/urun_arsivi.py.

HER GIRIS ICIN (kayip 0 — dogrulanamayan tek giris varsa HICBIR SEY yazilmaz):
  1. govde_sha256 = eski `kayit`tan hesaplanir;
  2. silme_commit = girisi arsive EKLEYEN commit (silme kapisi silme ile arsiv girisini
     AYNI commit'te sart kosar; 20 Eki olcumu: 42/42 boyle);
  3. KABUL: `git show <silme_commit>^:urunler.json` icindeki kayit govde_sha256'ya ESIT ve
     <silme_commit>'te o id YOK.

KIPLER:
  python3 tools/urun-arsiv-govdesiz.py              kuru: her giris icin bulunan commit
  python3 tools/urun-arsiv-govdesiz.py --uygula     dosyayi govdesiz sekle yazar
  python3 tools/urun-arsiv-govdesiz.py --dogrula    mevcut arsiv: govdeli=0 + her girisin
                                                    govdesi git'ten dogrulanir (rc 0/1)
Cikis: 0 tamam · 1 dogrulanamayan/govdeli giris var · 2 olculemedi.
"""
import argparse
import importlib.util
import json
import os
import sys

TOOLS = os.path.dirname(os.path.realpath(__file__))
_spec = importlib.util.spec_from_file_location("urun_arsivi",
                                               os.path.join(TOOLS, "urun_arsivi.py"))
ua = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ua)



def _depo():
    p = ua._git(os.getcwd(), "rev-parse", "--show-toplevel")
    if p.returncode != 0:
        raise ua.ArsivHatasi("git deposu degil")
    return p.stdout.decode().strip()


def silme_commit_bul(kok, giris):
    """Eski govdeli giris icin dogrulanmis silme commit'i (= girisi arsive EKLEYEN commit;
    silme kapisi ayni commit'i sart kosar) ya da ArsivHatasi."""
    uid, sha = ua.giris_id(giris), ua.giris_sha(giris)
    tasiyan = ua.tasiyan_commit(kok, giris)
    if not tasiyan:
        raise ua.ArsivHatasi("%s: girisi arsive ekleyen commit bulunamadi" % uid)
    if ua.silme_dogrula(kok, uid, sha, tasiyan) is None:
        raise ua.ArsivHatasi("%s: %s urunu dusurmuyor ya da ebeveyn govdesi govde_sha256 "
                             "ile ESLESMIYOR" % (uid, tasiyan[:12]))
    return tasiyan, "ekleyen"


def indir(kok, arsiv):
    """[(yeni_giris, kaynak_etiketi)] ; tek giris dogrulanamazsa ArsivHatasi."""
    cikti = []
    for g in arsiv:
        if ua.sekil_ihlali(g) is None:
            c = ua.silme_commit_coz(kok, g) if g.get("silme_commit") else None
            cikti.append((g, "zaten-govdesiz" + (" %s" % c[:12] if c else "")))
            continue
        if not isinstance(g, dict) or not isinstance(g.get("kayit"), dict):
            raise ua.ArsivHatasi("taninmayan giris sekli: %r" % (g,))
        c, etiket = silme_commit_bul(kok, g)
        yeni = ua.giris_yap(g["kayit"], g.get("yazan"), g.get("kuyruk_id"),
                            g.get("silinme_ts"))
        yeni["silme_commit"] = c
        cikti.append((yeni, "%s %s" % (etiket, c[:12])))
    return cikti


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--dogrula", action="store_true")
    ap.add_argument("--depo")
    a = ap.parse_args(argv)
    try:
        kok = os.path.abspath(a.depo) if a.depo else _depo()
        yol = os.path.join(kok, ua.ARSIV_YOLU)
        with open(yol, encoding="utf-8") as f:
            arsiv = json.load(f)
        if not isinstance(arsiv, list):
            raise ua.ArsivHatasi("%s kok DIZI DEGIL" % ua.ARSIV_YOLU)
        if a.dogrula:
            govdeli = ua.govdeli_girisler(arsiv)
            hatali = []
            for g in arsiv:
                if ua.sekil_ihlali(g):
                    continue
                try:
                    ua.govde_getir(kok, g)
                except ua.ArsivHatasi as e:
                    hatali.append(str(e))
            for i, uid, ihlal in govdeli:
                print("  GOVDELI #%d %s — %s" % (i, uid, ihlal))
            for h in hatali:
                print("  DOGRULANAMADI %s" % h)
            print("ARSIV_DOGRULA: GIRIS=%d GOVDELI=%d DOGRULANAN=%d DOGRULANAMAYAN=%d"
                  % (len(arsiv), len(govdeli), len(arsiv) - len(govdeli) - len(hatali),
                     len(hatali)))
            return 0 if not govdeli and not hatali else 1
        sonuc = indir(kok, arsiv)
        for (g, etiket) in sonuc:
            print("  %-70s %s" % (g["id"], etiket))
        print("INDIRME: GIRIS=%d DOGRULANAN=%d (kayip 0)" % (len(arsiv), len(sonuc)))
        if a.uygula:
            gecici = yol + ".tmp-%d" % os.getpid()
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump([g for g, _ in sonuc], f, ensure_ascii=False, indent=2)
            os.replace(gecici, yol)
            print("YAZILDI: %s (govdesiz)" % ua.ARSIV_YOLU)
        return 0
    except ua.ArsivHatasi as e:
        print("HATA: %s — HICBIR SEY yazilmadi." % e)
        return 1
    except (OSError, ValueError) as e:
        print("OLCULEMEDI: %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())

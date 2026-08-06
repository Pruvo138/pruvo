#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/serit-bolme-mutasyon.py — SERIT BOLUNMESININ CURUTME (mutasyon) ARACI.

NE OLCER: "yayin seridi ikiye bolununce bir kapi SESSIZCE yayin yolundan dustu mu".

NEDEN VAR (5 Agu 2026, OLCULEN OLAY): 4/5 Agu gecesi `serit-a3` kirmizi yandi,
`deploy: needs` zinciri geregi IKI ardisik kosumda `deploy` SKIPPED kaldi ve yayin
74 dakika durdu. Kritik yol olculdu (adim duzeyi, son 6 basarili kosum):
`serit-a3` 968 sn ve tek bir adim (`model-uyelik-kapisi.py --kendini-test`) 440 sn
= %45. O adim `serit-a4` job'una TASINDI.

🔴 BU TASIMANIN SESSIZ HATASI SUDUR: yeni job `deploy: needs` listesine EKLENMEZSE
kapi CI'da GORUNUR (adim kosar, kirmizi yanar) ama YAYINI BLOKLAMAZ — yani koruma
sessizce fail-open olur. Bu arac tam o hali KOSTURARAK olcer; yorumla degil.

YONTEM: kapinin KENDI kesif fonksiyonlari (tools/is-akisi-kapisi.py :: bolum_d ·
bloklayici_kapi_kontrol) GECICI bir is-akisi DIZINI uzerinde kosturulur. Calisma
agacina HICBIR SEY YAZILMAZ ve deploy.yml'in sha256'si kosum sonunda dogrulanir
([[mutasyon-diske-yazma-tuzagi]]).

VARYANTLAR:
  P  PRISTINE  : deploy.yml oldugu gibi                -> bulgu 0 BEKLENIR
  M1 MUTANT    : `serit-a4` `deploy: needs`ten DUSURULDU -> bulgu > 0 (asil sinif)
  M2 MUTANT    : `serit-a3` `deploy: needs`ten DUSURULDU -> bulgu > 0 (POZITIF KONTROL:
                 eksen bu sinifi BOLUNMEDEN ONCE de goruyordu; M1'in kirmizisi yeni bir
                 eksenden degil AYNI eksenden dogar)
  K  KONTROL   : alakasiz alan (`serit-a4.runs-on`) degisir -> bulgu 0 BEKLENIR
                 (yoksa arac "her degisiklige kirmizi yanan" bir gurultu kaynagidir
                 ve M1/M2'nin kirmizisi mutasyona ATFEDILEMEZ)

🔴 KABUL = CIKIS KODU DEGIL, BASTIGI SAYI: her varyantta "olculen kapi cagrisi"
sayisi da basilir ve DEGISMEMESI beklenir — kapi kaybi tam olarak o sayidan okunur
([[kapi-yan-etkisi-gizli-onkosul]]).

Kullanim: python3 tools/serit-bolme-mutasyon.py
Cikis 0 = pristine ve kontrol YESIL · iki mutant KIRMIZI · kapi cagrisi sayisi ayni ·
deploy.yml sha256 degismedi.
"""
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
AKIS_DIZIN = os.path.join(ROOT, ".github", "workflows")
DEPLOY = os.path.join(AKIS_DIZIN, "deploy.yml")

# 🔴 CAPALAR — her biri TAM BIR KEZ eslesmeli; eslesmezse arac HICBIR SEY olcmuyordur.
NEEDS = "    needs: [build, serit-a2, serit-a3, serit-a4]\n"
NEEDS_A4_YOK = "    needs: [build, serit-a2, serit-a3]\n"
NEEDS_A3_YOK = "    needs: [build, serit-a2, serit-a4]\n"
KONTROL_CAPA = "  serit-a4:\n    runs-on: ubuntu-latest\n"
KONTROL_YAZ = "  serit-a4:\n    runs-on: ubuntu-22.04\n"


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _modul(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _dizin_kur(kok_tmp, ad, deploy_metni):
    hedef = os.path.join(kok_tmp, ad)
    shutil.copytree(AKIS_DIZIN, hedef)
    with open(os.path.join(hedef, "deploy.yml"), "w", encoding="utf-8") as f:
        f.write(deploy_metni)
    return hedef


def _capa(metin, capa, ne):
    adet = metin.count(capa)
    if adet != 1:
        raise SystemExit(
            "SURUCU BAYAT: %s capasi %d kez bulundu (tam 1 olmali):\n%r\n"
            "(deploy.yml degismis olabilir — capayi guncelle; yoksa bu arac HICBIR SEY "
            "olcmuyor demektir)" % (ne, adet, capa))


def varyantlar(pristine):
    _capa(pristine, NEEDS, "deploy.needs")
    _capa(pristine, KONTROL_CAPA, "serit-a4 kontrol")
    return (
        ("P  PRISTINE", pristine, False),
        ("M1 serit-a4 `deploy: needs`ten DUSURULDU",
         pristine.replace(NEEDS, NEEDS_A4_YOK, 1), True),
        ("M2 serit-a3 `deploy: needs`ten DUSURULDU (POZITIF KONTROL)",
         pristine.replace(NEEDS, NEEDS_A3_YOK, 1), True),
        ("K  KONTROL: serit-a4.runs-on degisti",
         pristine.replace(KONTROL_CAPA, KONTROL_YAZ, 1), False),
    )


def main():
    if not os.path.exists(DEPLOY):
        print("⚪ OLCULEMEDI — %s YOK" % DEPLOY)
        return 2
    once = sha(DEPLOY)
    with open(DEPLOY, encoding="utf-8") as f:
        pristine = f.read()

    iak = _modul("pruvo_is_akisi_kapisi", os.path.join(TOOLS, "is-akisi-kapisi.py"))
    tmp = tempfile.mkdtemp(prefix="serit-bolme-")
    kusur, iddia, cagrilar = 0, 0, set()
    try:
        for i, (ad, metin, bulgu_bekle) in enumerate(varyantlar(pristine)):
            dizin = _dizin_kur(tmp, "v%d" % i, metin)
            d_ham = iak.bolum_d(dizin)
            d_hatalar, d_cagri = list(d_ham[0]), d_ham[1]
            f_hatalar, f_iddia = iak.bloklayici_kapi_kontrol(dizin)
            f_hatalar = list(f_hatalar)
            toplam = len(d_hatalar) + len(f_hatalar)
            cagrilar.add(d_cagri)
            iddia += 1
            ok = (toplam > 0) if bulgu_bekle else (toplam == 0)
            if not ok:
                kusur += 1
            print("%s %-54s bulgu D=%d F=%d (F iddia %d) · olculen kapi cagrisi=%s -> %s"
                  % ("✔" if ok else "✘", ad, len(d_hatalar), len(f_hatalar), f_iddia,
                     d_cagri, "KIRMIZI" if toplam else "yesil"))
            for h in (d_hatalar + f_hatalar)[:2]:
                print("      " + str(h).replace("\n", " ")[:170])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    iddia += 1
    if len(cagrilar) != 1:
        kusur += 1
    print("\n%s olculen kapi cagrisi TUM varyantlarda AYNI (%s) — serit bolunmesi "
          "olcum yuzeyini KUCULTMEDI"
          % ("✔" if len(cagrilar) == 1 else "✘", ", ".join(str(x) for x in sorted(cagrilar))))

    sonra = sha(DEPLOY)
    iddia += 1
    if once != sonra:
        kusur += 1
    print("%s calisma agacindaki deploy.yml sha256 DEGISMEDI  [%s… -> %s…]"
          % ("✔" if once == sonra else "✘", once[:16], sonra[:16]))

    print("\nSONUC: %d iddia kosuldu · %s"
          % (iddia, "TEMIZ ✅ (fail-open KIRMIZI yaniyor, kontrol YESIL)" if kusur == 0
             else "%d KUSUR 🔴" % kusur))
    return 1 if kusur else 0


if __name__ == "__main__":
    sys.exit(main())

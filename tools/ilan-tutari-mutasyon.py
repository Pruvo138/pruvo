#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ILAN TUTARI KAPISININ MUTASYON NOBETI — kapi OLU mu?

    python3 tools/ilan-tutari-mutasyon.py
    python3 tools/ilan-tutari-mutasyon.py --sadece M-A,M-K

NEDEN AYRI DOSYA: batarya ANLATILMAZ, KOSULUR ([[mutasyon-kaniti-yeniden-uretilebilir]]).
Surucu repoda durur ki hukum her SHA'da yeniden uretilebilsin.

🔴 UC YAPISAL KURAL (hepsi bu depoda ISIRDI):
  1. MUTASYON KOPYAYA UYGULANIR. `tools/` gecici bir koke KOPYALANIR, kokun geri kalani
     SEMBOLIK baglanir (olcum GERCEK katalogla kalir). Canli agaca TEK BAYT yazilmaz ve
     bu, bas/son `agac_damgasi()` ile KANITLANIR. SIGTERM/SIGINT'te bile gecici kok
     silinir, agac temizdir. → [[kapi-yan-etkisi-gizli-onkosul]]
  2. CAPA ELLE YAZILMAZ: hedef fonksiyonun KENDI kaynagindan turetilir (mutasyon_kopya).
     Capa bayatlarsa hukum OLCULEMEDI degil KIRMIZI'dir. → [[ikiz-tanim-sessiz-ayrisma]]
  3. MUTANT `rc` ILE DEGIL, BEKLENEN IDDIA AILESININ IZIYLE kabul edilir. Salt `rc=1`
     "kapi kirmizi yandi" der ama HANGI iddianin yandigini soylemez: alakasiz bir cokme de
     rc=1'dir ve mutant sahte-oldurulmus gorunur. Her mutant kendi `iz` dizesini bekler.

MUTANTLAR (alti OLDURUCU + bir KONTROL):
  M-A  kart metni duz "X TL"ye doner ("…'den baslayan" eki dusuruldu)      -> KIRMIZI
  M-B  markup tabani KART yerine URUN SAYFASI tutarindan turer             -> KIRMIZI
  M-B2 markup tabani kartla AYRI ayristirma kuralina (price_number) doner  -> KIRMIZI
  M-C  urun sayfasinin JS oncesi tutari LISTE tabanina duser               -> KIRMIZI
  M-C2 urun sayfasi tutari AYRISTIRILAMAZ bicime duser (olculemedi kolu)   -> KIRMIZI (rc=2)
  M-D  aralik tavani EN PAHALI malzeme yerine onerilen malzemeden turer    -> KIRMIZI
  M-K  KONTROL: davranisi degistirmeyen yeniden yazim                      -> YESIL
"""
import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import mutasyon_kopya as mk   # noqa: E402

KAPI = "ilan-tutari-kapisi.py"
HEDEF = os.path.join(TOOLS, "build.py")

# (kod, aciklama, kapsam, desen, donusum, beklenen_kirmizi, iz)
#   kapsam  = build.py'deki NITELIK adi (capa onun KENDI kaynagindan turer)
#   desen   = kapsam icinde TEK satira uyan duzenli ifade
#   iz      = kapinin ciktisinda BEKLENEN iddia ailesinin dizesi
MUTANTLAR = [
    ("M-A", "kart metni duz 'X TL'ye dondu (baslangic beyani dustu)",
     "kart_tutar_metni",
     r"return \(tutar_metni \+ BASLAYAN_SONEK\)",
     lambda s: "    return tutar_metni",
     True, "kart metni duz tutar yaziyor"),
    ("M-B", "markup tabani URUN SAYFASI tutarindan turedi (kart ile ayristi)",
     "render_product",
     r"ld_fiyat = ilan_tl_metni\(vitrin_kurus\(p\)\) or pnum",
     lambda s: s.replace("vitrin_kurus(p)", "ilan_kurus(p)"),
     True, "lowPrice != KART tutari"),
    ("M-B2", "markup tabani kartla AYRI ayristirma kuralina dondu (price_number)",
     "render_product",
     r"ld_fiyat = ilan_tl_metni\(vitrin_kurus\(p\)\) or pnum",
     lambda s: s.split("ld_fiyat")[0] + "ld_fiyat = pnum",
     True, "lowPrice != KART tutari"),
    ("M-C", "urun sayfasinin JS oncesi tutari LISTE tabanina dustu",
     "render_product",
     r"baslangic_fiyat = esc\(taban_fiyat_metni\(_ilan_k / 100\.0\)\)",
     lambda s: s.replace("_ilan_k /", "vitrin_kurus(p) /"),
     True, "URUN SAYFASI tutari onerilen malzemeden turemedi"),
    # M-C2 = OLCULEMEDI KOLUNUN BEKCISI. Tutari AYRISTIRILAMAZ bicime dusuren mutant
    # kapiyi "sessiz yesil"e cevirmemeli: hukum OLCULEMEDI'dir ve cikis SIFIR DISI.
    ("M-C2", "urun sayfasi tutari AYRISTIRILAMAZ bicime dustu (olculemedi kolu)",
     "render_product",
     r"baslangic_fiyat = esc\(taban_fiyat_metni\(_ilan_k / 100\.0\)\)",
     lambda s: s.split("baslangic_fiyat")[0] + "baslangic_fiyat = esc(fiyat)",
     True, "sayfadaki gorunur tutar ayristirilamadi"),
    ("M-D", "aralik tavani EN PAHALI malzeme yerine ONERILEN malzemeden turedi",
     "render_product",
     r"ld_yuksek = ilan_tl_metni\(en_yuksek_kurus\(p\)\)",
     lambda s: s.replace("en_yuksek_kurus(p)", "ilan_kurus(p)"),
     True, "highPrice EN PAHALI malzemeden turemedi"),
    ("M-K", "KONTROL: davranisi degistirmeyen yeniden yazim",
     "malzeme_aralikli_mi",
     r'if p\.get\("kategori"\) not in FONKSIYONEL_KATEGORILER:',
     lambda s: '    if not (p.get("kategori") in FONKSIYONEL_KATEGORILER):',
     False, None),
]


def _kos(kok):
    """Kapiyi KOPYA kokte kostur; (rc, cikti) doner."""
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", KAPI), "--ozet"],
                       capture_output=True, text=True, cwd=kok)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sadece", default="", help="virgullu mutant kodu listesi")
    a = ap.parse_args()
    secim = [s.strip() for s in a.sadece.split(",") if s.strip()]

    damga_yollari = [HEDEF, os.path.join(ROOT, "secenekler.js"),
                     os.path.join(ROOT, "index.html"),
                     os.path.join(TOOLS, KAPI)]
    bas_damga = mk.agac_damgasi(damga_yollari)

    gecici = tempfile.mkdtemp(prefix="ilan-tutari-mut-")

    def _sinyal(_s, _f):
        """SIGTERM/SIGINT: gecici kok silinir. Canli agaca zaten yazilmadi (mutant
        yalniz KOPYADA yasar) -> kesilen kosum ARTIK BIRAKMAZ."""
        shutil.rmtree(gecici, ignore_errors=True)
        sys.exit(130)

    signal.signal(signal.SIGTERM, _sinyal)
    signal.signal(signal.SIGINT, _sinyal)

    sapan = []
    try:
        # Capa haritasi TEMIZ dosyadan, mutasyondan ONCE cozulur (bkz. kapsam_haritasi).
        mod = mk.modul_yukle(HEDEF, "ilan_tutari_hedefi")
        harita = mk.kapsam_haritasi(mod, [m[2] for m in MUTANTLAR])
        with open(HEDEF, encoding="utf-8") as f:
            temiz_metin = f.read()

        print("%-5s %-58s %-9s %-9s %s" % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "IZ"))
        for kod, aciklama, kapsam, desen, donusum, kirmizi_bekle, iz in MUTANTLAR:
            if secim and kod not in secim:
                continue
            alt = os.path.join(gecici, kod)
            os.makedirs(alt)
            try:
                kok = mk.kopya_kok(alt)
                try:
                    yeni = mk.mutant_metni(harita, temiz_metin, [(kapsam, desen, donusum)])
                except mk.CapaHatasi as e:
                    sapan.append("%s: CAPA BAYAT/TUTMADI — %s" % (kod, e))
                    print("%-5s %-58s %-9s %-9s %s"
                          % (kod, aciklama[:58], "KIRMIZI" if kirmizi_bekle else "YESIL",
                             "-", "CAPA YOK"))
                    continue
                with open(os.path.join(kok, "tools", "build.py"), "w",
                          encoding="utf-8") as f:
                    f.write(yeni)
                rc, cikti = _kos(kok)
            finally:
                shutil.rmtree(alt, ignore_errors=True)

            iz_var = bool(iz) and (iz in cikti)
            if kirmizi_bekle:
                # 🔴 rc TEK BASINA YETMEZ: beklenen IDDIA AILESININ izi de olmali.
                tamam = (rc != 0) and iz_var
                olculen = "rc=%d%s" % (rc, " +iz" if iz_var else " IZ YOK")
            else:
                # KONTROL: yesil kalmali VE hicbir oldurucu iz dusmemeli.
                kirli = [x[6] for x in MUTANTLAR if x[6] and x[6] in cikti]
                tamam = (rc == 0) and not kirli
                olculen = "rc=%d%s" % (rc, (" KIRLI:%s" % kirli[:1]) if kirli else "")
            if not tamam:
                sapan.append("%s: beklenen %s, olculen %s"
                             % (kod, "KIRMIZI+iz" if kirmizi_bekle else "YESIL", olculen))
            print("%-5s %-58s %-9s %-9s %s"
                  % (kod, aciklama[:58], "KIRMIZI" if kirmizi_bekle else "YESIL",
                     olculen, "OK" if tamam else "SAPTI"))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    son_damga = mk.agac_damgasi(damga_yollari)
    print("\nAGAC DAMGASI: bas=%s son=%s · artik yedek=%d"
          % (bas_damga[0], son_damga[0], len(son_damga[1])))
    if bas_damga != son_damga:
        sapan.append("CANLI AGAC DEGISTI (damga %s -> %s, artik=%s)"
                     % (bas_damga[0], son_damga[0], son_damga[1]))

    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: mutantlarin hepsi beklenen rengi VE izini verdi; canli agac EL DEGMEMIS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
  M-E  ISTEMCI kart tabani `onSecimMalzeme`den turer (curutucunun bozmasi) -> KIRMIZI
  M-K  KONTROL: davranisi degistirmeyen yeniden yazim                      -> YESIL

M-E secenekler.js'i hedefler; `mk.kopya_kok` yalniz `tools/`u KOPYALAR, kokun geri kalani
SEMBOLIK BAGDIR -> bag once KALDIRILIR, yerine mutant dosya YAZILIR (yoksa yazma canli
dosyaya giderdi). Silme kopya kokun icindedir; agac damgasi bunu her kosumda kanitlar.
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
BUILD = os.path.join(TOOLS, "build.py")
SECENEKLER = os.path.join(ROOT, "secenekler.js")

# (kod, aciklama, dosya, kapsam, desen, donusum, beklenen_kirmizi, iz)
#   dosya   = "build" (tools/build.py) | "secenekler" (secenekler.js — ISTEMCI tarafi)
#   kapsam  = o dosyadaki fonksiyon adi (capa onun KENDI kaynagindan turer)
#   desen   = kapsam icinde TEK satira uyan duzenli ifade
#   iz      = kapinin ciktisinda BEKLENEN iddia ailesinin dizesi
MUTANTLAR = [
    ("M-A", "kart metni duz 'X TL'ye dondu (baslangic beyani dustu)",
     "build", "kart_tutar_metni",
     r"return \(tutar_metni \+ BASLAYAN_SONEK\)",
     lambda s: "    return tutar_metni",
     True, "kart metni duz tutar yaziyor"),
    ("M-B", "markup tabani URUN SAYFASI tutarindan turedi (kart ile ayristi)",
     "build", "render_product",
     r"ld_fiyat = ilan_tl_metni\(vitrin_kurus\(p\)\) or pnum",
     lambda s: s.replace("vitrin_kurus(p)", "ilan_kurus(p)"),
     True, "lowPrice != KART tutari"),
    ("M-B2", "markup tabani kartla AYRI ayristirma kuralina dondu (price_number)",
     "build", "render_product",
     r"ld_fiyat = ilan_tl_metni\(vitrin_kurus\(p\)\) or pnum",
     lambda s: s.split("ld_fiyat")[0] + "ld_fiyat = pnum",
     True, "lowPrice != KART tutari"),
    ("M-C", "urun sayfasinin JS oncesi tutari LISTE tabanina dustu",
     "build", "render_product",
     r"baslangic_fiyat = esc\(taban_fiyat_metni\(_ilan_k / 100\.0\)\)",
     lambda s: s.replace("_ilan_k /", "vitrin_kurus(p) /"),
     True, "URUN SAYFASI tutari onerilen malzemeden turemedi"),
    # M-C2 = OLCULEMEDI KOLUNUN BEKCISI. Tutari AYRISTIRILAMAZ bicime dusuren mutant
    # kapiyi "sessiz yesil"e cevirmemeli: hukum OLCULEMEDI'dir ve cikis SIFIR DISI.
    ("M-C2", "urun sayfasi tutari AYRISTIRILAMAZ bicime dustu (olculemedi kolu)",
     "build", "render_product",
     r"baslangic_fiyat = esc\(taban_fiyat_metni\(_ilan_k / 100\.0\)\)",
     lambda s: s.split("baslangic_fiyat")[0] + "baslangic_fiyat = esc(fiyat)",
     True, "sayfadaki gorunur tutar ayristirilamadi"),
    ("M-D", "aralik tavani EN PAHALI malzeme yerine ONERILEN malzemeden turedi",
     "build", "render_product",
     r"ld_yuksek = ilan_tl_metni\(en_yuksek_kurus\(p\)\)",
     lambda s: s.replace("en_yuksek_kurus(p)", "ilan_kurus(p)"),
     True, "highPrice EN PAHALI malzemeden turemedi"),
    # 🔴 M-E = BAGIMSIZ CURUTUCUNUN BULGUSU (12 Agu). Kapinin ILK halinde bu bozma
    # UYGULANDI ve kapi YINE rc=0 verdi: MUSTERININ GORDUGU kart tutarini ISTEMCI
    # uretiyor, kapi ise yapisal veriyi yalniz URETEÇ tabanina karsi olcuyordu ->
    # istemci kart tabanini `onSecimMalzeme`den turetince sayfa 559 TL gosterip markup
    # 430 yaziyor ve HICBIR SEY alarm calmiyordu. Bu, kapinin kapattigi sinifin ta
    # kendisi. Mutant o bozmayi KALICI olarak nobetler; iz eksen 1'in yeni ayagidir.
    ("M-E", "istemci kart tabani ONERILEN malzemeden turedi (curutucunun bozmasi)",
     "secenekler", "vitrinBirimKurus",
     r"return _birimKurus\(urun, vitrinMalzeme\(urun, ref\)\);",
     lambda s: s.replace("vitrinMalzeme(urun, ref)", "onSecimMalzeme(urun, ref)"),
     True, "KART TUTARI (istemci vitrinBirimKurus == ureteç vitrin_kurus)"),
    ("M-K", "KONTROL: davranisi degistirmeyen yeniden yazim",
     "build", "malzeme_aralikli_mi",
     r'if p\.get\("kategori"\) not in FONKSIYONEL_KATEGORILER:',
     lambda s: '    if not (p.get("kategori") in FONKSIYONEL_KATEGORILER):',
     False, None),
]


def _kos(kok):
    """Kapiyi KOPYA kokte kostur; (rc, YESIL-OLMAYAN satirlar) doner.

    🔴 IZ YALNIZ HUKUM DUSUREN SATIRLARDA ARANIR (12 Agu, KONTROL mutanti yakaladi):
    kapinin iddia metni YESILDE de KIRMIZIDA da AYNI cumleyi tasir (yalnizca ✅/❌
    on eki degisir). Ham ciktida dize aramak, iddia GECERKEN de "iz var" der; yani
    mutant kabulu, olculen sey hakkinda HICBIR SEY soylemeyen bir eslesmeyle
    yapilirdi. Bu yuzden yalniz DUSEN iddia (❌) ve OLCULEMEDI (⚠️) satirlari
    doner — iz o kumede aranir."""
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", KAPI), "--ozet"],
                       capture_output=True, text=True, cwd=kok)
    ham = (r.stdout or "") + (r.stderr or "")
    dusen = [s for s in ham.splitlines()
             if s.lstrip().startswith("❌") or "OLCULEMEDI:" in s]
    return r.returncode, "\n".join(dusen)


def _js_kapsam(kaynak, ad):
    """`secenekler.js` icindeki `function <ad>(...) { ... }` govdesi — CAPA ELLE YAZILMAZ,
    dosyanin KENDI metninden dengeli parantezle cikarilir. Bulunamazsa CapaHatasi."""
    bas = kaynak.find("function " + ad + "(")
    if bas < 0:
        raise mk.CapaHatasi("secenekler.js'te `function %s(` YOK (yeniden adlandirilmis?)"
                            % ad)
    if kaynak.find("function " + ad + "(", bas + 1) >= 0:
        raise mk.CapaHatasi("secenekler.js'te `function %s(` birden cok kez tanimli" % ad)
    i = kaynak.find("{", bas)
    derinlik = 0
    for j in range(i, len(kaynak)):
        if kaynak[j] == "{":
            derinlik += 1
        elif kaynak[j] == "}":
            derinlik -= 1
            if derinlik == 0:
                return kaynak[bas:j + 1]
    raise mk.CapaHatasi("secenekler.js'te %s govdesi kapanmiyor" % ad)


def _kopya_koke_js_yaz(kok, metin):
    """Kopya kokteki `secenekler.js` SEMBOLIK BAGDIR (mk.kopya_kok yalniz tools/'u
    kopyalar). Bag KALDIRILIR ve yerine GERCEK dosya yazilir; yoksa yazma CANLI dosyaya
    giderdi. Silme kopya kokun ICINDEDIR, canli agaca dokunmaz."""
    yol = os.path.join(kok, "secenekler.js")
    if os.path.islink(yol) or os.path.exists(yol):
        os.unlink(yol)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sadece", default="", help="virgullu mutant kodu listesi")
    a = ap.parse_args()
    secim = [s.strip() for s in a.sadece.split(",") if s.strip()]

    damga_yollari = [BUILD, SECENEKLER, os.path.join(ROOT, "index.html"),
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
        # Capa haritalari TEMIZ dosyalardan, mutasyondan ONCE cozulur (kapsam_haritasi).
        mod = mk.modul_yukle(BUILD, "ilan_tutari_hedefi")
        with open(BUILD, encoding="utf-8") as f:
            temiz = {"build": f.read()}
        with open(SECENEKLER, encoding="utf-8") as f:
            temiz["secenekler"] = f.read()
        harita = {
            "build": mk.kapsam_haritasi(
                mod, [m[3] for m in MUTANTLAR if m[2] == "build"]),
            "secenekler": {ad: _js_kapsam(temiz["secenekler"], ad)
                           for ad in {m[3] for m in MUTANTLAR if m[2] == "secenekler"}},
        }

        print("%-5s %-58s %-9s %-9s %s" % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "IZ"))
        for kod, aciklama, dosya, kapsam, desen, donusum, kirmizi_bekle, iz in MUTANTLAR:
            if secim and kod not in secim:
                continue
            alt = os.path.join(gecici, kod)
            os.makedirs(alt)
            try:
                kok = mk.kopya_kok(alt)
                try:
                    yeni = mk.mutant_metni(harita[dosya], temiz[dosya],
                                           [(kapsam, desen, donusum)])
                except mk.CapaHatasi as e:
                    sapan.append("%s: CAPA BAYAT/TUTMADI — %s" % (kod, e))
                    print("%-5s %-58s %-9s %-9s %s"
                          % (kod, aciklama[:58], "KIRMIZI" if kirmizi_bekle else "YESIL",
                             "-", "CAPA YOK"))
                    continue
                if dosya == "build":
                    with open(os.path.join(kok, "tools", "build.py"), "w",
                              encoding="utf-8") as f:
                        f.write(yeni)
                else:
                    _kopya_koke_js_yaz(kok, yeni)
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
                kirli = [x[7] for x in MUTANTLAR if x[7] and x[7] in cikti]
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

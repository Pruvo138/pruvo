#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA SAYAÇ KAPISI ÇÜRÜTME BATARYASI — kapı gerçekten yük taşıyor mu?

Her mutant `tools/marka_model_build.py`'nin **KOPYASINA** uygulanır, kapı AYRI BİR
SÜREÇTE o kopya kökten koşturulur; canlı ağaca TEK BAYT yazılmaz. Kabul:
  · ÖLDÜRÜCÜ mutantların HEPSİ kırmızı yakmalı (rc != 0),
  · KONTROL mutantları YEŞİL kalmalı (kapı gürültüye alarm vermiyor),
  · düşen İDDİA AİLE İMZALARI ayrışmalı — iki mutant aynı imzayı düşürüyorsa o eksen
    için ayırt edici kanıt YOKTUR ([[beyan-edilmis-survivor]]),
  · her mutantın KAYNAK İZİ (sha1) tabandan farklı olmalı — aynı uzunlukta mutasyon +
    bytecode önbelleği tuzağı ([[mutasyon-bytecode-onbellegi]]) burada KANITLANIR,
  · canlı ağacın damgası baş=son ve artık `*-yedek` dosyası KALMAMALI.

🔴 İKİ ARIZA BU SÜRÜMDE KAPANDI (12 Ağu 2026, bağımsız çürütücü ölçtü):
  1. **ÇAPALAR BAYATTI.** Üç mutantın (`MARKA_KOVA_SIFIR`, `ESIK_MARKA_SSR`,
     `MARKA_OZEL_DAL`) elle yazılmış çapası 8 Ağu `bolum_ayrimi` refaktöründe kayboldu;
     sürücü `rc=3 OLCULEMEDI` verip HİÇBİR mutantı ölçemez oldu. Fail-closed'dı ama
     kapsam kaybı sessizdi. Artık çapa ELLE YAZILMIYOR: hedef fonksiyonun / JS gövdesi
     sabitinin KENDİ kaynağından TÜRETİLİYOR (`mutasyon_kopya.mutant_metni`) ve
     türetilemezse / dönüşüm etkisiz kalırsa hüküm **KIRMIZI** oluyor.
  2. **ÇALIŞMA AĞACINI KİRLETİYORDU.** Mutant canlı dosyaya yazılıyordu; kesilen bir
     koşum ağaçta `*.mutasyon-yedek` bırakıyor ve KARDEŞ nöbetçileri kırmızı yakıyordu.
     Artık mutasyon KOPYAYA uygulanıyor (bkz. tools/mutasyon_kopya.py).

Kullanım: python3 tools/marka-sayac-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import mutasyon_kopya as mk                                        # noqa: E402

CANLI_HEDEF = os.path.join(TOOLS, "marka_model_build.py")


def _js(dize, yeni):
    """Satır-içi dönüşüm üreteci (çapa TÜRETİLİR, dönüşüm satırın İÇİNDE çalışır;
    satırın şekli değişirse dönüşüm etkisiz kalır ve sürücü KIRMIZI yakar)."""
    return lambda s: s.replace(dize, yeni)


def _sonuna(ek):
    return lambda s: s + ek


def _oncesine(ek):
    return lambda s: ek + s


# (kimlik, öldürücü mü, [(kapsam, desen, donusum), ...])
def mutantlar():
    ad = mk.bir_marka_adi(ROOT)
    fc_kapat = ("_marka_sayfasi", r"if toplam != marka_urun_sayisi\(d\):",
                _js("if toplam !=", "if False and toplam !="))
    kova_capa = ("_marka_sayfasi", r"kova_listeleri = \[g\[\"urunler\"\]", None)
    return [
        # 1) Şerit sayısını YİNE DOM sayımına bağla (düzeltilen kusurun ta kendisi).
        ("SAYAC_YINE_KARTA", True, [
            ("_KAPSAM_JS_GOVDE", r"parça sayısı ölçülemedi",
             _js('toplam === null ? "parça sayısı ölçülemedi" : (toplam + " parça")',
                 'gorunenKart + " parça"'))]),
        # 2) Kanonik toplam model kovalarını YOK SAYSIN (kart birimine düş).
        ("KOVA_TOPLAMI_YOK", True, [
            ("sayfa_kalemleri", r"return _tekil\(kart_urunleri",
             _js(", *list(kova_listeleri)", ""))]),
        # 3) Marka sayfasının kova listesini SIFIRLA (jeneratör fail-closed mı?).
        ("MARKA_KOVA_SIFIR", True, [
            (kova_capa[0], kova_capa[1],
             _js('[g["urunler"] for g in buyuk_gruplar]', "[]"))]),
        # 4) Kategori filtresini kırılıma UYGULAMA (hep tam toplamı bas).
        ("KAPSAM_KIRILIMA_UYGULANMIYOR", True, [
            ("_KAPSAM_JS_GOVDE", r"return tablo\[c\.kategori\]",
             _js("return tablo[c.kategori] || 0;", "return toplam;"))]),
        # 5) Tekilleştirmeyi NO-OP yap (mükerrer kart geri gelir).
        ("TEKIL_NOOP", True, [
            ("_tekil", r"if anahtar in gorulen:", _js("if anahtar in gorulen:", "if False:"))]),
        # 6) Tekilleştirme SIRAYI BOZSUN (id'ye göre sırala).
        ("TEKIL_SIRA_BOZUK", True, [
            ("_tekil", r"^    return out$",
             _js("return out", 'return sorted(out, key=lambda q: q.get("id") or "")'))]),
        # 7) İKİ SAYIYI AYRI KAYNAKTAN türet (beyan cümlesi yerel kolundan doğsun).
        ("IKI_SAYI_AYRI_KAYNAK", True, [
            ("_marka_sayfasi", r'_toplam_bloku\(esc, kalemler, "Bu markada"\)',
             _js("_toplam_bloku(esc, kalemler,", "_toplam_bloku(esc, yerel,"))]),
        # 8) FAIL-CLOSED'ı FAIL-OPEN'a çevir: kırılım okunamazsa kart sayısına düş.
        ("TOPLAM_FAIL_OPEN", True, [
            ("_KAPSAM_JS_GOVDE", r"el\.length !== 1", _js("return null;", "return 0;"))]),
        # 9) SINIF DEĞİL VAKA onarımı (SSR): kanonik toplamı YALNIZ çok-ürünlü markalarda
        #    kur, küçüklerde kart birimine düş; iç fail-closed de susturulur ki sapma
        #    SESSİZ kalsın — kapı yalnız büyük markalara bakıyorsa bu mutant yaşar.
        ("ESIK_MARKA_SSR", True, [
            (kova_capa[0], kova_capa[1],
             _sonuna(" if len(kucuk_urunler) > 120 else []")), fc_kapat]),
        # 10) SINIF DEĞİL VAKA onarımı (istemci): küçük sayfalarda yine kart sayısına düş.
        ("ESIK_MARKA_JS", True, [
            ("_KAPSAM_JS_GOVDE", r"toplam < gorunenKart \|\| toplam < gorunenBag",
             _sonuna("\n    if(gorunenKart < 120){ toplam = gorunenKart; }"))]),
        # 11) MARKA-ÖZEL DAL: onarım tek bir markada çalışsın (sınıf değil vaka onarımı).
        #     Marka adı ÇALIŞMA ANINDA evrenden alınır — bu dosyada sabit marka adı YOK.
        ("MARKA_OZEL_DAL", True, [
            (kova_capa[0], kova_capa[1], _sonuna(' if marka == "%s" else []' % ad)),
            fc_kapat]),
        # --- KONTROL (yeşil kalmalı) ---
        ("KONTROL_JS_YORUM", False, [
            ("_KAPSAM_JS_GOVDE", r"function toplamla\(dok, c\)\{",
             _oncesine("  // kontrol mutanti: davranissiz yorum\n"))]),
        ("KONTROL_ESDEGER_IFADE", False, [
            ("sayfa_kalemleri", r"return _tekil\(kart_urunleri",
             _js("*list(kova_listeleri)", "*tuple(kova_listeleri)"))]),
        ("KONTROL_CSS_BOSLUK", False, [
            ("_MM_CSS", r"\.mm-toplam\{margin:0 0 10px",
             _js("margin:0 0 10px;font-size:14px;", "margin:0 0 10px; font-size:14px; "))]),
    ]


def kapi_kos(kok):
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    shutil.rmtree(os.path.join(kok, "tools", "__pycache__"), ignore_errors=True)
    cp = subprocess.run([sys.executable, "-B",
                         os.path.join(kok, "tools", "marka-sayac-kapisi.py")],
                        capture_output=True, text=True, env=ortam, timeout=3600)
    cikti = cp.stdout + cp.stderr
    iz = (re.search(r"^IZ=(\S+)", cikti, re.M) or [None, "?"])[1]
    aile = (re.search(r"^AILELER=(.*)$", cikti, re.M) or [None, "?"])[1]
    iddia = (re.search(r"^IDDIA=(\S+)", cikti, re.M) or [None, "?"])[1]
    return cp.returncode, iz, aile, iddia


def main():
    damga_bas = mk.agac_damgasi([CANLI_HEDEF])
    tmp = tempfile.mkdtemp(prefix="mm-sayac-mutasyon-")
    old_t = old_g = kon_t = kon_g = 0
    imzalar = {}
    try:
        kok = mk.kopya_kok(tmp)
        hedef = os.path.join(kok, "tools", "marka_model_build.py")
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        mod = mk.modul_yukle(hedef, "mmb_mutasyon_hedefi")
        muts = mutantlar()
        # 🔴 ÇAPALAR BİR KEZ, DOSYA EL DEĞMEMİŞKEN ÇÖZÜLÜR: kapsam kaynağını mutasyon
        # sırasında çözmek çapayı ÖLÇÜLEN ŞEYE bağımlı kılardı (ve `inspect` bayat satır
        # önbelleğinden okuyup patlıyordu). Bundan sonra tüm mutantlar bu haritadan türer.
        harita = mk.kapsam_haritasi(
            mod, [kapsam for _k, _o, ciftler in muts for kapsam, _d, _f in ciftler])

        # ÖN KONTROL: her mutantın çapası TÜRETİLEBİLİYOR ve dönüşümü ETKİLİ mi.
        # 🔴 Bayat çapa artık `OLCULEMEDI` DEĞİL KIRMIZI: kapsam kaybı sessiz kalmaz.
        bozuk = []
        for kimlik, _o, ciftler in muts:
            try:
                mk.mutant_metni(harita, metin, ciftler)
            except mk.CapaHatasi as e:
                bozuk.append("%s: %s" % (kimlik, e))
        if bozuk:
            print("CAPA BAYAT — mutasyon KAPSAMI KAYBOLMUS (KIRMIZI, ölçülemedi DEĞİL):")
            for b in bozuk:
                print("  " + b)
            print("HUKUM=KIRMIZI")
            return 1

        print("== TABAN (mutasyonsuz KOPYA) ==")
        t_rc, t_iz, t_aile, t_iddia = kapi_kos(kok)
        print("taban rc=%d IZ=%s IDDIA=%s AILELER=%s" % (t_rc, t_iz, t_iddia, t_aile))
        if t_rc != 0:
            print("OLCULEMEDI: taban YEŞİL değil, mutasyon ölçülemez.")
            return 3

        for kimlik, oldurucu, ciftler in muts:
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(mk.mutant_metni(harita, metin, ciftler))
            rc, iz, aile, iddia = kapi_kos(kok)
            uygulandi = iz != t_iz and iz != "?"
            if oldurucu:
                old_t += 1
                old_g += 1 if ((rc != 0) and uygulandi) else 0
                imzalar.setdefault(aile, []).append(kimlik)
            else:
                kon_t += 1
                kon_g += 1 if (rc == 0 and uygulandi) else 0
            print("  %-30s %-9s rc=%d uygulandi=%s IDDIA=%s AILELER=%s"
                  % (kimlik, "OLDURUCU" if oldurucu else "KONTROL", rc,
                     "EVET" if uygulandi else "HAYIR", iddia, aile[:90]))
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    damga_son = mk.agac_damgasi([CANLI_HEDEF])
    ayrismayan = sum(len(v) for v in imzalar.values() if len(v) > 1)
    print("\n== HUKUM ==")
    for imza, ks in sorted(imzalar.items()):
        if len(ks) > 1:
            print("  AYRISMAYAN: %s -> %s" % (", ".join(ks), imza[:120]))
    print("AGAC_DAMGASI bas=%s son=%s artik=%s" % (damga_bas[0], damga_son[0], damga_son[1]))
    temiz = damga_bas == damga_son and not damga_son[1]
    print("OLDURUCU=%d/%d  KONTROL=%d/%d  AYRISMAYAN=%d  AGAC_KIRLILIGI=%s"
          % (old_g, old_t, kon_g, kon_t, ayrismayan, "YOK" if temiz else "VAR"))
    tamam = (old_g == old_t and kon_g == kon_t and ayrismayan == 0 and temiz)
    print("HUKUM=" + ("YESIL" if tamam else "KIRMIZI"))
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())

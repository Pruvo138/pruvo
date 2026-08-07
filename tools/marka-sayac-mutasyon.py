#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA SAYAÇ KAPISI ÇÜRÜTME BATARYASI — kapı gerçekten yük taşıyor mu?

Her mutant `tools/marka_model_build.py`'ye UYGULANIR, kapı AYRI BİR SÜREÇTE koşturulur,
sonra kaynak geri alınır. Kabul:
  · ÖLDÜRÜCÜ mutantların HEPSİ kırmızı yakmalı (rc != 0),
  · KONTROL mutantları YEŞİL kalmalı (kapı gürültüye alarm vermiyor),
  · düşen İDDİA AİLE İMZALARI ayrışmalı (ayrışmayan = 0) — iki mutant aynı imzayı
    düşürüyorsa o eksen için ayırt edici kanıt YOKTUR ([[beyan-edilmis-survivor]]),
  · her mutantın KAYNAK İZİ (sha1) tabandan farklı olmalı — aynı uzunlukta mutasyon +
    Python bytecode önbelleği tuzağı ([[mutasyon-bytecode-onbellegi]]) burada KANITLANIR.

Kullanım: python3 tools/marka-sayac-mutasyon.py
"""
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = os.path.join(TOOLS, "marka_model_build.py")
KAPI = os.path.join(TOOLS, "marka-sayac-kapisi.py")

def _bir_marka_adi():
    """Marka-özel dal mutantı için GERÇEK bir marka adı — bu dosyada SABİT marka adı
    tutulmaz (kapının MARKA_LITERAL iddiası bu dosyayı da tarıyor)."""
    with open(os.path.join(os.path.dirname(TOOLS), "index.html"), encoding="utf-8") as f:
        m = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", f.read(), re.S)
    return re.findall(r'"([^"]+)"', m.group(1))[0]


# (kimlik, öldürücü mü, eski_metin, yeni_metin)
MUTANTLAR = [
    # 1) Sayacı YİNE yalnız kartlara bağla (düzeltilen kusurun ta kendisi).
    ("SAYAC_YINE_KARTA", True,
     '(toplam === null ? "parça sayısı ölçülemedi" : (toplam + " parça")))',
     '(gorunenKart + " parça"))'),
    # 2) Kanonik toplam model kovalarını YOK SAYSIN (kart birimine düş).
    ("KOVA_TOPLAMI_YOK", True,
     "    return _tekil(kart_urunleri, *list(kova_listeleri))",
     "    return _tekil(kart_urunleri)"),
    # 3) Model kovası toplamını SIFIRLA (yalnız marka sayfasında; jeneratör fail-closed mı?).
    ("MARKA_KOVA_SIFIR", True,
     '    kalemler = sayfa_kalemleri(diger, [g["urunler"] for g in buyuk_gruplar])',
     "    kalemler = sayfa_kalemleri(diger, [])"),
    # 4) Kategori filtresini kovalara/kırılıma UYGULAMA (hep tam toplamı bas).
    ("KAPSAM_KIRILIMA_UYGULANMIYOR", True,
     "    return sayimla(ham, c);\n  }",
     "    return sayimla(ham, null);\n  }"),
    # 5) Tekilleştirmeyi NO-OP yap (mükerrer kart geri gelir).
    ("TEKIL_NOOP", True,
     "            if anahtar in gorulen:\n                continue\n            gorulen.add(anahtar)\n            out.append(p)",
     "            gorulen.add(anahtar)\n            out.append(p)"),
    # 6) Tekilleştirme SIRAYI BOZSUN (id'ye göre sırala).
    ("TEKIL_SIRA_BOZUK", True,
     "            out.append(p)\n    return out",
     '            out.append(p)\n    return sorted(out, key=lambda q: q.get("id") or "")'),
    # 7) İKİ SAYIYI AYRI KAYNAKTAN türet (meta kalemlerden, rozet/kırılım kartlardan).
    ("IKI_SAYI_AYRI_KAYNAK", True,
     '            + _toplam_bloku(esc, kalemler, "Bu markada")',
     '            + _toplam_bloku(esc, diger, "Bu markada")'),
    # 8) FAIL-CLOSED'ı FAIL-OPEN'a çevir: kırılım okunamazsa kart sayısına düş (sessiz hata).
    ("TOPLAM_FAIL_OPEN", True,
     "    if(!el || el.length !== 1){ return null; }",
     "    if(!el || el.length !== 1){ return 0; }"),
    # 9) SINIF DEĞİL VAKA onarımı (SSR): kanonik toplamı YALNIZ çok-ürünlü markalarda kur,
    #    küçüklerde kart birimine düş. Fail-closed ikiz kontrolü de susturulur ki sapma
    #    SESSİZ kalsın — kapı yalnız büyük markalara bakıyorsa bu mutant hayatta kalır.
    ("ESIK_MARKA_SSR", True,
     '    kalemler = sayfa_kalemleri(diger, [g["urunler"] for g in buyuk_gruplar])\n'
     "    toplam = len(kalemler)",
     '    kalemler = sayfa_kalemleri(diger, [g["urunler"] for g in buyuk_gruplar]\n'
     "                               if len(diger) > 120 else [])\n"
     "    toplam = len(kalemler)\n"
     "    marka_urun_sayisi = (lambda _d, _t=toplam: _t)"),
    # 10) SINIF DEĞİL VAKA onarımı (istemci): küçük sayfalarda yine kart sayısına düş.
    ("ESIK_MARKA_JS", True,
     "    if(toplam !== null && toplam < gorunenKart){ toplam = null; }",
     "    if(toplam !== null && toplam < gorunenKart){ toplam = null; }\n"
     "    if(gorunenKart < 120){ toplam = gorunenKart; }"),
    # --- KONTROL (yeşil kalmalı) ---
    ("KONTROL_JS_YORUM", False,
     "  function toplamla(dok, c){",
     "  // kontrol mutanti: davranissiz yorum\n  function toplamla(dok, c){"),
    ("KONTROL_ESDEGER_IFADE", False,
     "    return _tekil(kart_urunleri, *list(kova_listeleri))",
     "    return _tekil(kart_urunleri, *tuple(kova_listeleri))"),
    ("KONTROL_CSS_BOSLUK", False,
     "  .mm-toplam{margin:0 0 10px;font-size:14px;color:var(--gray-text)}",
     "  .mm-toplam{margin:0 0 10px; font-size:14px; color:var(--gray-text)}"),
]


def kapi_kos():
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    shutil.rmtree(os.path.join(TOOLS, "__pycache__"), ignore_errors=True)
    cp = subprocess.run([sys.executable, "-B", KAPI], capture_output=True, text=True,
                        env=ortam, timeout=1800)
    cikti = cp.stdout + cp.stderr
    iz = (re.search(r"^IZ=(\S+)", cikti, re.M) or [None, "?"])[1]
    aile = (re.search(r"^AILELER=(.*)$", cikti, re.M) or [None, "?"])[1]
    iddia = (re.search(r"^IDDIA=(\S+)", cikti, re.M) or [None, "?"])[1]
    return cp.returncode, iz, aile, iddia


def main():
    with open(HEDEF, "rb") as f:
        asil = f.read()
    metin = asil.decode("utf-8")

    # 11) MARKA-ÖZEL DAL: onarım tek bir markada çalışsın (sınıf değil vaka onarımı).
    #     Marka adı ÇALIŞMA ANINDA index.html evreninden alınır — bu dosyada sabit yok.
    MUTANTLAR.append((
        "MARKA_OZEL_DAL", True,
        '    kalemler = sayfa_kalemleri(diger, [g["urunler"] for g in buyuk_gruplar])\n'
        "    toplam = len(kalemler)",
        '    kalemler = sayfa_kalemleri(diger, [g["urunler"] for g in buyuk_gruplar]\n'
        '                               if marka == "%s" else [])\n'
        "    toplam = len(kalemler)\n"
        "    marka_urun_sayisi = (lambda _d, _t=toplam: _t)" % _bir_marka_adi()))

    # ön kontrol: her mutantın eski metni kaynakta TAM BİR KEZ geçmeli (sessiz no-op yok)
    eksik = [k for k, _o, eski, _y in MUTANTLAR if metin.count(eski) != 1]
    if eksik:
        print("OLCULEMEDI: çapası bulunamayan/çoklu mutant: %s" % ", ".join(eksik))
        return 3

    print("== TABAN ==")
    t_rc, t_iz, t_aile, t_iddia = kapi_kos()
    print("taban rc=%d IZ=%s IDDIA=%s AILELER=%s" % (t_rc, t_iz, t_iddia, t_aile))
    if t_rc != 0:
        print("OLCULEMEDI: taban YEŞİL değil, mutasyon ölçülemez.")
        return 3

    oldurucu_t = oldurucu_g = kontrol_t = kontrol_g = 0
    imzalar = {}
    satirlar = []
    try:
        for kimlik, oldurucu, eski, yeni in MUTANTLAR:
            with open(HEDEF, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni))
            rc, iz, aile, iddia = kapi_kos()
            uygulandi = iz != t_iz and iz != "?"
            if oldurucu:
                oldurucu_t += 1
                oldu = (rc != 0) and uygulandi
                oldurucu_g += 1 if oldu else 0
                imzalar.setdefault(aile, []).append(kimlik)
            else:
                kontrol_t += 1
                kontrol_g += 1 if (rc == 0 and uygulandi) else 0
            satirlar.append("%-30s %-9s rc=%d uygulandi=%s IDDIA=%s AILELER=%s"
                            % (kimlik, "ÖLDÜRÜCÜ" if oldurucu else "KONTROL", rc,
                               "EVET" if uygulandi else "HAYIR", iddia, aile[:90]))
            print("  " + satirlar[-1])
    finally:
        with open(HEDEF, "wb") as f:
            f.write(asil)
        shutil.rmtree(os.path.join(TOOLS, "__pycache__"), ignore_errors=True)

    ayrismayan = sum(len(v) for v in imzalar.values() if len(v) > 1)
    print("\n== HUKUM ==")
    for imza, ks in sorted(imzalar.items()):
        if len(ks) > 1:
            print("  AYRISMAYAN: %s -> %s" % (", ".join(ks), imza[:120]))
    print("OLDURUCU=%d/%d  KONTROL=%d/%d  AYRISMAYAN=%d  TABAN_IDDIA=%s"
          % (oldurucu_g, oldurucu_t, kontrol_g, kontrol_t, ayrismayan, t_iddia))
    tamam = (oldurucu_g == oldurucu_t and kontrol_g == kontrol_t and ayrismayan == 0)
    print("HUKUM=" + ("YESIL" if tamam else "KIRMIZI"))
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())

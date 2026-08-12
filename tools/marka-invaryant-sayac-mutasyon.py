#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SAYFA SAYACI İNVARYANT ÇÜRÜTME BATARYASI — kapı gerçekten yük taşıyor mu?

Ölçülen hüküm (12 Ağu 2026, Okan canlı ekrandan bildirdi — SESSİZ kusur):
    sayfada BEYAN EDİLEN parça sayısı == o yüzeyde ERİŞİLEBİLEN kart sayısı.
Aynı marka için ekranda DÖRT ayrı sayı vardı: beyan 593 · başlık 80 · kapsam beyanı 575 ·
kapsam başlığı 304. Bu batarya, `tools/marka-sayac-kapisi.py`nin o hükmü GERÇEKTEN
ölçtüğünü mutasyonla kanıtlar.

🔴 MUTASYON KOPYAYA UYGULANIR, CANLI DOSYAYA ASLA. Kardeş sürücü
(`marka-sayac-mutasyon.py`) izlenen kaynağı yerinde değiştirdiği için CI'da bloklanmıştı
(ci-kapsam-test.py muafiyet kaydı). Burada her koşum, `tools/` klasörü KOPYALANMIŞ, geri
kalanı sembolik bağlanmış geçici bir depo kökünde yapılır; canlı ağaç HİÇ dokunulmaz ve
bas/son sha256 karşılaştırmasıyla bu KANITLANIR.

Kabul:
  · ÖLDÜRÜCÜ mutantların HEPSİ kırmızı yakmalı (rc != 0),
  · KONTROL mutantları YEŞİL kalmalı (kapı gürültüye alarm vermiyor),
  · düşen İDDİA AİLE İMZALARI ayrışmalı — iki mutant aynı imzayı düşürüyorsa o eksen için
    ayırt edici kanıt YOKTUR ([[beyan-edilmis-survivor]]),
  · her mutantın KAYNAK İZİ (kapının bastığı sha1) tabandan farklı olmalı — aynı uzunlukta
    mutasyon + bytecode önbelleği tuzağı ([[mutasyon-bytecode-onbellegi]]) burada kapanır,
  · canlı `tools/marka_model_build.py`nin sha256'sı başta ve sonda AYNI olmalı.

Kullanım: python3 tools/marka-invaryant-sayac-mutasyon.py
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

# 🔴 KOPYA KÖKÜ + AĞAÇ DAMGASI TEK KAYNAKTAN (tools/mutasyon_kopya.py): üç sürücü de
# aynı gövdeyi kullanır, ikiz tanım sessizce ayrışamaz → [[ikiz-tanim-sessiz-ayrisma]].
import mutasyon_kopya as mk                                        # noqa: E402

CANLI_HEDEF = os.path.join(TOOLS, "marka_model_build.py")


def _bir_marka_adi():
    """Marka-özel dal mutantı için GERÇEK bir marka adı. Bu dosyada SABİT marka adı
    TUTULMAZ: kapının MARKA_LITERAL iddiası bu dosyayı da tarıyor."""
    return mk.bir_marka_adi(ROOT)


# (kimlik, öldürücü mü, eski_metin, yeni_metin)
def mutantlar():
    ad = _bir_marka_adi()
    return [
        # 1) KUSURUN TA KENDİSİ (SSR): başlık yine O AN BASILANI yazsın.
        ("BASLIK_YINE_BASILI", True,
         '+ _bolum_sayaci(esc, kalemler, "erisim") + \')</h2>\')',
         '+ _bolum_sayaci(esc, basili, "erisim") + \')</h2>\')'),
        # 2) BEYAN kolunu boz: beyan cümlesi erişilebilir kümeden değil basılandan doğsun.
        ("BEYAN_BASILIDAN", True,
         '            + _toplam_bloku(esc, kalemler, "Bu markada")',
         '            + _toplam_bloku(esc, basili, "Bu markada")'),
        # 3) KAPSAM KOLU (istemci): başlığa yine GÖRÜNEN DOM DÜĞÜMÜ sayısı yazılsın —
        #    canlıda 575 yerine 304 basan dal tam buydu.
        ("KAPSAM_BASLIGA_DOM", True,
         "    bolumSayaclari(dok, c);",
         '    yazSayim(dok, ".mm-sayim-kart[data-katsay]", gorunenKart);'),
        # 4) FAIL-CLOSED -> FAIL-OPEN: kırılım okunamazsa "—" yerine sayı bas.
        ("BOLUM_FAIL_OPEN", True,
         '      el[i].textContent = saglam ? String(sayimla(ham, c)) : "—";',
         "      el[i].textContent = String(sayimla(ham, c));"),
        # 5) SEMANTİK KAYMASI: alt küme rozetini erişim rozeti ilan et (yalan sayı, aynı
        #    biçimde). Sınıf jetonu ölçülmüyorsa bu mutant hayatta kalır.
        ("ALT_ROZET_ERISIM", True,
         '+ _bolum_sayaci(esc, yerel_kalan, "alt") + \')</h2>\'',
         '+ _bolum_sayaci(esc, yerel_kalan, "erisim") + \')</h2>\''),
        # 6) MODEL SAYFASI: ana bölüm rozeti kuşak bölümünü de saysın (bölümler çakışır,
        #    ekrandaki sayılar sayfa toplamını vermez).
        ("MODEL_BOLUM_CAKISIR", True,
         '            + _bolum_sayaci(esc, ana, "parca") + \')</h2>\'',
         '            + _bolum_sayaci(esc, g["urunler"], "parca") + \')</h2>\''),
        # 7) SINIF DEĞİL VAKA onarımı: başlık YALNIZ tek bir markada doğru sayıyı yazsın.
        #    Marka adı çalışma anında evrenden alınır (bu dosyada sabit yok).
        ("MARKA_OZEL_DAL", True,
         '+ _bolum_sayaci(esc, kalemler, "erisim") + \')</h2>\')',
         '+ _bolum_sayaci(esc, kalemler if marka == "%s" else basili, "erisim")\n'
         "               + ')</h2>')" % ad),
        # --- KONTROL (yeşil kalmalı) ---
        ("KONTROL_YORUM", False,
         "def _bolum_sayaci(esc, urunler, bolum):",
         "# kontrol mutanti: davranissiz yorum\ndef _bolum_sayaci(esc, urunler, bolum):"),
        ("KONTROL_ESDEGER_JS", False,
         '      el[i].textContent = saglam ? String(sayimla(ham, c)) : "—";',
         '      el[i].textContent = saglam ? ("" + sayimla(ham, c)) : "—";'),
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
    canli_bas = mk.agac_damgasi([CANLI_HEDEF])
    tmp = tempfile.mkdtemp(prefix="mm-invaryant-mutasyon-")
    try:
        kok = mk.kopya_kok(tmp)
        hedef = os.path.join(kok, "tools", "marka_model_build.py")
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        muts = mutantlar()
        eksik = [k for k, _o, eski, _y in muts if metin.count(eski) != 1]
        if eksik:
            print("OLCULEMEDI: çapası bulunamayan/çoklu mutant: %s" % ", ".join(eksik))
            return 3

        print("== TABAN (mutasyonsuz KOPYA) ==")
        t_rc, t_iz, t_aile, t_iddia = kapi_kos(kok)
        print("taban rc=%d IZ=%s IDDIA=%s AILELER=%s" % (t_rc, t_iz, t_iddia, t_aile))
        if t_rc != 0:
            print("OLCULEMEDI: taban YEŞİL değil, mutasyon ölçülemez.")
            return 3

        old_t = old_g = kon_t = kon_g = 0
        imzalar = {}
        for kimlik, oldurucu, eski, yeni in muts:
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni))
            rc, iz, aile, iddia = kapi_kos(kok)
            uygulandi = iz != t_iz and iz != "?"
            if oldurucu:
                old_t += 1
                oldu = (rc != 0) and uygulandi
                old_g += 1 if oldu else 0
                imzalar.setdefault(aile, []).append(kimlik)
            else:
                kon_t += 1
                kon_g += 1 if (rc == 0 and uygulandi) else 0
            print("  %-24s %-9s rc=%d uygulandi=%s IDDIA=%s AILELER=%s"
                  % (kimlik, "OLDURUCU" if oldurucu else "KONTROL", rc,
                     "EVET" if uygulandi else "HAYIR", iddia, aile[:100]))
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    canli_son = mk.agac_damgasi([CANLI_HEDEF])
    agac_temiz = canli_bas == canli_son and not canli_son[1]
    ayrismayan = sum(len(v) for v in imzalar.values() if len(v) > 1)
    print("\n== HUKUM ==")
    for imza, ks in sorted(imzalar.items()):
        if len(ks) > 1:
            print("  AYRISMAYAN: %s -> %s" % (", ".join(ks), imza[:120]))
    print("AGAC_DAMGASI bas=%s son=%s artik=%s"
          % (canli_bas[0], canli_son[0], canli_son[1]))
    print("OLDURUCU=%d/%d  KONTROL=%d/%d  AYRISMAYAN=%d  AGAC_KIRLILIGI=%s"
          % (old_g, old_t, kon_g, kon_t, ayrismayan, "YOK" if agac_temiz else "VAR"))
    tamam = (old_g == old_t and kon_g == kon_t and ayrismayan == 0 and agac_temiz)
    print("HUKUM=" + ("YESIL" if tamam else "KIRMIZI"))
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())

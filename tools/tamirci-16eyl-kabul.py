#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""16 Eyl 2026 Tamirci turu — UC SESSIZ-HATA ONARIMININ KABUL KAPISI.

Kaynak: BaBa'nin 16 Eyl 09:1x gunluk olcumu, KraL'a yazilan arac kusurlari.
Her kalem icin (1) ARIZA vakasi KIRMIZI olmali, (2) POZITIF KONTROL yesil
kalmali (kapi "her seye kirmizi" diyerek kabul saglamasin), (3) MUTANT —
onarim IZOLE KOPYADA geri alininca ilgili vaka yeniden KIRMIZI yanmali.

KALEMLER
  ② tools/denetim-kapisi.py  --idler'de TANINMAYAN id sessiz-yesil doner
  ③ tools/urun-ekle.py       lisans_map GPL/LGPL/BSD'de `lisans` alanini yazmaz
  ④ tools/defter-rotasyon.py isaretciye indirme defterin EN GUNCEL blogunu secer

🔴 TEST YUKU YIKICI OLAMAZ (BaBa filo dersi): bu dosyada gercek ev yoluna
yazan/silen tek bir komut yoktur. Mutantlar `tempfile.mkdtemp()` altindaki
IZOLE kopyada kosar; gercek `tools/` agacina yalnizca SYMLINK ile bakilir.

KOSUM:  python3 tools/tamirci-16eyl-kabul.py
        rc=0 -> hepsi gecti · rc=1 -> en az bir iddia KIRMIZI
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
PY = sys.executable or "python3"

RC_ID_BULUNAMADI_BEKLENEN = 5

_sonuc = []


def iddia(ad, gecti, ayrinti=""):
    _sonuc.append((ad, bool(gecti), ayrinti))
    print("  %s %s%s" % ("GECTI " if gecti else "KIRMIZI", ad,
                         (" — " + ayrinti) if ayrinti else ""))
    return bool(gecti)


# ---------------------------------------------------------------- yardimcilar
def _kum_havuzu(mutasyonlu_arac=None, govde=None):
    """IZOLE sandbox: <tmp>/tools/* -> gercek tools'a symlink, <tmp>/urunler.json
    kucuk SENTETIK katalog. `mutasyonlu_arac` verilirse o dosya symlink DEGIL,
    `govde` icerigiyle GERCEK dosya olarak yazilir (mutant CANLI govdede yasamaz)."""
    kum = tempfile.mkdtemp(prefix="tamirci16-")
    os.mkdir(os.path.join(kum, "tools"))
    for ad in os.listdir(TOOLS):
        hedef = os.path.join(kum, "tools", ad)
        if ad == mutasyonlu_arac:
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(govde)
        else:
            os.symlink(os.path.join(TOOLS, ad), hedef)
    katalog = [{
        "id": "kabul-sentetik-urun", "ad": "Kabul Sentetik Urun",
        "kategori": "Tamirat", "fiyat": "250", "marka": ["Genel"],
        "aciklama": "kabul testi icin sentetik kayit", "olcu": "10x10x10 mm",
        "gorseller": ["https://ornek.invalid/g0.jpg"],
    }]
    with open(os.path.join(kum, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(katalog, f, ensure_ascii=False)
    return kum


def _kos(kum, *arg):
    """Borusuz kosum — rc DOGRUDAN okunur ([[boru-rc-isci-olcumunu-yalanlar]])."""
    r = subprocess.run([PY, os.path.join(kum, "tools", "denetim-kapisi.py")] + list(arg),
                       capture_output=True, text=True, cwd=kum)
    return r.returncode, (r.stderr or "") + (r.stdout or "")


def _modul_yukle(ad, yol):
    import importlib.util
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ========================================================== ② denetim-kapisi
def kalem2():
    print("\n② tools/denetim-kapisi.py — --idler taninmayan id FAIL-CLOSED")
    kum = _kum_havuzu()
    try:
        rc, _ = _kos(kum, "--idler", "2881066")
        iddia("②A kaynak-platform id'si rc=%d" % RC_ID_BULUNAMADI_BEKLENEN,
              rc == RC_ID_BULUNAMADI_BEKLENEN, "olculen rc=%d" % rc)
        rc, cikti = _kos(kum, "--idler", "kabul-sentetik-urun,kabul-sentetik-urun")
        iddia("②B virgulle ayrilmis liste fail-closed",
              rc == RC_ID_BULUNAMADI_BEKLENEN and "VIRGULLE" in cikti,
              "olculen rc=%d" % rc)
        rc, _ = _kos(kum, "--idler")
        iddia("②C bos --idler fail-closed", rc == RC_ID_BULUNAMADI_BEKLENEN,
              "olculen rc=%d" % rc)
        rc, _ = _kos(kum, "--idler", "kabul-sentetik-urun", "2881066")
        iddia("②D karisik listede TEK sahte id de bloklar",
              rc == RC_ID_BULUNAMADI_BEKLENEN, "olculen rc=%d" % rc)
        # POZITIF KONTROL: gercek id HALA olculuyor, kapi korlesmedi.
        rc, _ = _kos(kum, "--idler", "kabul-sentetik-urun")
        iddia("②E POZITIF KONTROL gercek id rc!=%d" % RC_ID_BULUNAMADI_BEKLENEN,
              rc != RC_ID_BULUNAMADI_BEKLENEN, "olculen rc=%d" % rc)
    finally:
        shutil.rmtree(kum, ignore_errors=True)

    # MUTANT: onarim geri alinir -> ②A yeniden sessiz-yesil olmali.
    with open(os.path.join(TOOLS, "denetim-kapisi.py"), encoding="utf-8") as f:
        govde = f.read()
    capa = "        yeni_ids = set(istenen)"
    if capa not in govde:
        iddia("②M MUTANT capasi bulundu", False, "capa kayboldu: %r" % capa)
        return
    mutant = govde.replace(
        "        bilinmeyen = [x for x in istenen if x not in katalog_ids]",
        "        bilinmeyen = []")
    kum = _kum_havuzu("denetim-kapisi.py", mutant)
    try:
        rc, _ = _kos(kum, "--idler", "2881066")
        iddia("②M MUTANT (bilinmeyen kontrolu sokuldu) vakayi KIRMIZI yakiyor",
              rc != RC_ID_BULUNAMADI_BEKLENEN,
              "mutantta rc=%d (onarimsiz hal sessiz-yesil olmali)" % rc)
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# ============================================================== ③ urun-ekle
def kalem3():
    print("\n③ tools/urun-ekle.py — lisans_map GPL/LGPL/BSD atif alanini YAZAR")
    ue = _modul_yukle("ue_canli", os.path.join(TOOLS, "urun-ekle.py"))
    vakalar = [
        ("GNU - GPL", True, "GNU GPL"),
        ("GNU - LGPL", True, "LGPL"),
        ("BSD License", True, "BSD"),
    ]
    for lic, bek_sat, bek_tur in vakalar:
        sat, tur = ue.lisans_map(lic)
        iddia("③ %-14s -> lisans.tur=%r" % (lic, bek_tur),
              sat == bek_sat and tur == bek_tur, "olculen=(%r, %r)" % (sat, tur))
    # POZITIF KONTROL: atif GEREKTIRMEYEN ve SATILAMAYAN dallar DEGISMEDI.
    sat, tur = ue.lisans_map("Public Domain (CC0)")
    iddia("③ KONTROL CC0 atifsiz KALIR (tur=None)", sat is True and tur is None,
          "olculen=(%r, %r)" % (sat, tur))
    sat, tur = ue.lisans_map("Creative Commons - Attribution - Noncommercial")
    iddia("③ KONTROL NC SATILAMAZ", sat is False, "olculen=(%r, %r)" % (sat, tur))
    sat, tur = ue.lisans_map("Creative Commons - Attribution")
    iddia("③ KONTROL CC BY bozulmadi", tur == "CC BY 4.0", "olculen tur=%r" % tur)
    # Gizli kaynak kaydinin etiketi GPL'de 'ucretsiz-cc' kovasina DUSMEZ.
    iddia("③ kaynak etiketi GPL -> ucretsiz-gpl-lgpl-bsd",
          ue.kaynak_tur_etiketi("GNU - GPL", "GNU GPL") == "ucretsiz-gpl-lgpl-bsd",
          "olculen=%r" % ue.kaynak_tur_etiketi("GNU - GPL", "GNU GPL"))
    iddia("③ kaynak etiketi CC BY -> ucretsiz-cc",
          ue.kaynak_tur_etiketi("Creative Commons - Attribution", "CC BY 4.0")
          == "ucretsiz-cc")
    iddia("③ kaynak etiketi CC0 -> ucretsiz-cc0",
          ue.kaynak_tur_etiketi("Public Domain (CC0)", None) == "ucretsiz-cc0")

    # MUTANT: GPL dali eski (True, None) haline dondurulur.
    with open(os.path.join(TOOLS, "urun-ekle.py"), encoding="utf-8") as f:
        govde = f.read()
    capa = '        return True, "GNU GPL"'
    if capa not in govde:
        iddia("③M MUTANT capasi bulundu", False, "capa kayboldu: %r" % capa)
        return
    kum = _kum_havuzu("urun-ekle.py", govde.replace(capa, "        return True, None"))
    try:
        mue = _modul_yukle("ue_mutant", os.path.join(kum, "tools", "urun-ekle.py"))
        _, tur = mue.lisans_map("GNU - GPL")
        iddia("③M MUTANT (GPL -> None) vakayi KIRMIZI yakiyor", tur is None,
              "mutantta tur=%r" % tur)
    finally:
        shutil.rmtree(kum, ignore_errors=True)


# ========================================================= ④ defter-rotasyon
def kalem4():
    print("\n④ tools/defter-rotasyon.py — 'en yeni en ustte kalir' invaryanti")
    dr = _modul_yukle("dr_canli", os.path.join(TOOLS, "defter-rotasyon.py"))
    # Vetosuz, KAPALI, yeterince govdeli bir blok: tek degisken KONUMDUR.
    blok = {"baslik": "## 16 Eyl — dilim-42 KAPANDI",
            "govde": ["+2 EKLE, katalog 38219->38221.",
                      "D1 UYUSMAZ:0, CI tam yesil.",
                      "Kampanya toplami 1035 EKLE.",
                      "Havuz 1723, dilim-43 aciliyor."]}
    v0 = dr._indirme_vetosu(blok, sira=0)
    iddia("④A sira=0 (defterin basi) VETOLU", v0 is not None, "veto=%r" % v0)
    v1 = dr._indirme_vetosu(blok, sira=1)
    iddia("④B POZITIF KONTROL ayni blok sira=1'de indirilebilir", v1 is None,
          "veto=%r" % v1)
    v_yok = dr._indirme_vetosu(blok)
    iddia("④C sira verilmeyen (prob) cagri konum vetosu UYGULAMAZ", v_yok is None,
          "veto=%r" % v_yok)

    # MUTANT: konum vetosu sokulur -> ④A yeniden KIRMIZI olmali.
    with open(os.path.join(TOOLS, "defter-rotasyon.py"), encoding="utf-8") as f:
        govde = f.read()
    capa = "    if sira == 0:"
    if capa not in govde:
        iddia("④M MUTANT capasi bulundu", False, "capa kayboldu: %r" % capa)
        return
    kum = _kum_havuzu("defter-rotasyon.py",
                      govde.replace(capa, "    if sira == -999:", 1))
    try:
        mdr = _modul_yukle("dr_mutant", os.path.join(kum, "tools", "defter-rotasyon.py"))
        iddia("④M MUTANT (konum vetosu sokuldu) vakayi KIRMIZI yakiyor",
              mdr._indirme_vetosu(blok, sira=0) is None,
              "mutantta veto=%r" % mdr._indirme_vetosu(blok, sira=0))
    finally:
        shutil.rmtree(kum, ignore_errors=True)


def main():
    print("=" * 74)
    print("TAMIRCI 16 EYL 2026 — KABUL KAPISI (3 sessiz-hata onarimi)")
    print("=" * 74)
    kalem2()
    kalem3()
    kalem4()
    kirmizi = [a for a, g, _ in _sonuc if not g]
    print("\n" + "=" * 74)
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (len(_sonuc), len(_sonuc) - len(kirmizi),
                                            len(kirmizi)))
    for a in kirmizi:
        print("  🔴 " + a)
    print("=" * 74)
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())

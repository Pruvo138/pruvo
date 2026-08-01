#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/commit-mesaji-mutasyon.py — commit mesaji sizinti nobetcisinin CURUTME araci.

NE OLCER: "kabul testi YESIL" demek "nobetci CANLI" demek DEGILDIR. Bu arac nobetciyi
BILEREK bozar ve kabul bataryasinin (`--kendini-test`) GERCEKTEN kirmizi yandigini
olcer. Ayrica ILGISIZ bir degisiklik (yorum/bosluk) YESIL kalmalidir — aksi halde
batarya "her seye kirmizi yanan" gurultulu bir alarma donusmus demektir.

🔴 GUVENLIK: mutasyon KOPYAYA uygulanir. Canli dosyalara DOKUNULMAZ; kosum sonunda
   sha256 esitligi ile KANITLANIR (mutant sizarsa arac KIRMIZI yanar).
🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — tools/ege-bilgi-tavan-mutasyon.py ile ayni desen.

Kullanim: python3 tools/commit-mesaji-mutasyon.py
Cikis 0 = her oldurucu mutant KIRMIZI + her ilgisiz mutant YESIL + canli dosyalar temiz.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "commit-mesaji-kapisi.py")
KUR = os.path.join(TOOLS, "commit-mesaji-hook-kur.py")
OZET = os.path.join(TOOLS, "sizinti-desen-ozetleri.json")


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# (ad, hedef_dosya, eski, yeni, oldurucu_mu)
# "oldurucu" = nobetcinin HUKMUNU ya da KABLOSUNU olduren mutasyon -> batarya KIRMIZI.
MUTANTLAR = (
    ("M1  ad eslesmesi OLDURULDU (ad_isabetleri -> [])", "kapi",
     '    if not kayit:\n        return []\n    uzunluklar =',
     '    if not kayit:\n        return []\n    return []\n    uzunluklar =', True),
    ("M2  alan adi ekseni OLDURULDU (alan_adi_isabetleri -> [])", "kapi",
     '    if not mesaj:\n        return []\n    bulunan = {}',
     '    if not mesaj:\n        return []\n    return []\n    bulunan = {}', True),
    ("M3  normalize OLDURULDU (ham metin doner)", "kapi",
     '    metin = "".join(_ELLE_ESLEM.get(k, k) for k in metin)',
     '    return metin\n    metin = "".join(_ELLE_ESLEM.get(k, k) for k in metin)', True),
    ("M4  sikistirilmis aday akisi KALDIRILDI", "kapi",
     '    jetonlar = bosluklu.split(" ") if bosluklu else []',
     '    return kume\n    jetonlar = bosluklu.split(" ") if bosluklu else []', True),
    ("M5  desen dosyasi yoklugu FAIL-OPEN yapildi", "kapi",
     '    if not os.path.isfile(yol):\n        return None, ("desen ozet dosyasi YOK',
     '    if not os.path.isfile(yol):\n        return {"dongu": 1, "tuz": b"x",'
     ' "desenler": []}, None\n    if False:\n        return None, ("desen ozet dosyasi YOK',
     True),
    ("M6  BOS desen listesi KABUL edildi (fail-open)", "kapi",
     '    if not isinstance(desenler, list) or not desenler:',
     '    if False:', True),
    ("M7  git yorum ayiklama KALDIRILDI (sablon hukme girer)", "kapi",
     '    satirlar = []\n    for satir in (ham or "").splitlines():',
     '    return (ham or "").strip()\n    satirlar = []\n'
     '    for satir in (ham or "").splitlines():', True),
    ("M8  CI maskesi OLDURULDU (host acik yazilir)", "kapi",
     '    etiketler = host.split(".")\n    govde = etiketler[0]',
     '    return host\n    etiketler = host.split(".")\n    govde = etiketler[0]', True),
    ("M9  PUBLIC_ALAN hukmu OLDURULDU (_public_mi -> False)", "kapi",
     'def _public_mi(host):\n    host = host.lower().strip(".")',
     'def _public_mi(host):\n    return False\n    host = host.lower().strip(".")', True),
    ("M10 UZANTI elemesi KALDIRILDI (dosya adlari alan adi sayilir)", "kapi",
     '        if son in UZANTI or son not in TLD:', '        if son not in TLD:', True),
    ("M11 asgari dongu esigi DUSURULDU (ucuz artefakt kabul)", "kapi",
     'ASGARI_DONGU = 5000', 'ASGARI_DONGU = 0', True),
    ("M12 KANCA CAGRI SATIRI SILINDI (blok var, olcum yok)", "kur",
     'if ! python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then\n'
     '  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici kimligi."\n'
     '  exit 1\n'
     'fi\n', 'true\n', True),
    ("M13 KANCA cagrisi YORUMA alindi (nobetci-cagri-satiri-nobetsiz sinifi)", "kur",
     'if ! python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then',
     'if ! echo python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then',
     True),
    ("M14 KANCA `exit 1` -> `exit 0` (fail-open)", "kur",
     '  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici kimligi."\n'
     '  exit 1\n', '  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici'
     ' kimligi."\n  exit 0\n', True),
    ("M15 KANCA fail-closed on-kosulu fail-OPEN yapildi (betik yoksa gec)", "kur",
     '  echo "!! Sizinti kapisi fail-closed\'dir. Kasten atlamak icin: '
     'git commit --no-verify"\n  exit 1\n', '  exit 0\n', True),
    # --- ILGISIZ (kontrol): batarya YESIL kalmali ---
    ("K1  ilgisiz: baslik yorumunda kelime degisti", "kapi",
     "IKI KOL — biri ONLER, digeri GORUNUR KILAR",
     "IKI KOL - biri ONLER, digeri GORUNUR KILAR", False),
    ("K2  ilgisiz: fonksiyon arasina bos satir eklendi", "kapi",
     "\ndef maskele(host):", "\n\ndef maskele(host):", False),
    ("K3  ilgisiz: kurulum betigine yorum satiri eklendi", "kur",
     "def kurulu_mu(yol):", "# ilgisiz yorum\ndef kurulu_mu(yol):", False),
)


def main():
    canli_once = {y: _sha(y) for y in (KAPI, KUR, OZET)}
    sonuclar = []
    for ad, hedef, eski, yeni, oldurucu in MUTANTLAR:
        tmp = tempfile.mkdtemp(prefix="pruvo-cm-mut-")
        try:
            t_tools = os.path.join(tmp, "tools")
            os.makedirs(t_tools)
            for kaynak in (KAPI, KUR, OZET):
                shutil.copy2(kaynak, os.path.join(t_tools, os.path.basename(kaynak)))
            yol = os.path.join(t_tools, os.path.basename(KAPI if hedef == "kapi" else KUR))
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            if eski not in metin:
                sonuclar.append((ad, oldurucu, None, "CAPA BULUNAMADI (mutasyon "
                                                     "uygulanamadi — arac bayat)"))
                continue
            if metin.count(eski) != 1:
                sonuclar.append((ad, oldurucu, None,
                                 "capa %d kez gecti (tek olmali)" % metin.count(eski)))
                continue
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
            p = subprocess.run(
                [sys.executable, os.path.join(t_tools, "commit-mesaji-kapisi.py"),
                 "--kendini-test"], capture_output=True, text=True, timeout=900)
            kirmizi_satirlar = [s.strip() for s in p.stdout.splitlines()
                                if s.strip().startswith("❌")]
            sonuclar.append((ad, oldurucu, p.returncode,
                             "; ".join(kirmizi_satirlar[:3]) or "(kirmizi iddia yok)"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    hatalar = []
    print("MUTANT                                                        BEKLENEN  RC  HUKUM")
    print("-" * 100)
    for ad, oldurucu, rc, tani in sonuclar:
        beklenen = "KIRMIZI" if oldurucu else "YESIL"
        if rc is None:
            hukum = "OLCULEMEDI"
            hatalar.append("%s -> %s" % (ad, tani))
        elif oldurucu:
            hukum = "OLDU ✅" if rc != 0 else "SAG KALDI ❌"
            if rc == 0:
                hatalar.append("%s SAG KALDI (batarya bu mutasyonu GORMUYOR)" % ad)
        else:
            hukum = "YESIL ✅" if rc == 0 else "SAHTE-KIRMIZI ❌"
            if rc != 0:
                hatalar.append("%s ilgisiz degisiklikte KIRMIZI yandi: %s" % (ad, tani))
        print("%-60s  %-8s  %-3s %s" % (ad[:60], beklenen,
                                        "-" if rc is None else rc, hukum))
    canli_sonra = {y: _sha(y) for y in (KAPI, KUR, OZET)}
    for yol in canli_once:
        if canli_once[yol] != canli_sonra[yol]:
            hatalar.append("🔴 CANLI DOSYA DEGISTI (mutant sizdi): %s" % yol)
    print("-" * 100)
    print("canli dosya sha256 esitligi: %s"
          % ("TAM ✅" if canli_once == canli_sonra else "BOZUK ❌"))
    for yol, ozet in sorted(canli_once.items()):
        print("   %-44s %s" % (os.path.basename(yol), ozet[:16]))
    oldu = sum(1 for _a, o, rc, _t in sonuclar if o and rc not in (None, 0))
    oldurucu_sayi = sum(1 for _a, o, _rc, _t in sonuclar if o)
    yesil_k = sum(1 for _a, o, rc, _t in sonuclar if not o and rc == 0)
    kontrol_sayi = sum(1 for _a, o, _rc, _t in sonuclar if not o)
    print("SONUC: oldurucu mutant %d/%d OLDU · ilgisiz kontrol %d/%d YESIL"
          % (oldu, oldurucu_sayi, yesil_k, kontrol_sayi))
    if hatalar:
        print("\nKIRMIZI:")
        for h in hatalar:
            print("  * " + h)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

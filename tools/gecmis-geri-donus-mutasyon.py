#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gecmis-geri-donus-mutasyon.py — GERI-DONUS KAPISININ CURUTME ARACI.

NE OLCER: "kabul testi YESIL" demek "kapi CANLI" demek DEGILDIR. Bu arac kapiyi
BILEREK bozar ve kabul bataryasinin (`--kendini-test`) GERCEKTEN kirmizi yandigini
olcer. ILGISIZ bir degisiklik (yorum/bosluk) ise YESIL kalmalidir — aksi halde
batarya "her seye kirmizi yanan" gurultulu bir alarma donusmus demektir.

🔴 GUVENLIK: mutasyon KOPYAYA uygulanir. Canli dosyalara DOKUNULMAZ; kosum sonunda
   sha256 esitligi ile KANITLANIR (mutant sizarsa arac KIRMIZI yanar).
🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — tools/commit-mesaji-mutasyon.py ile ayni desen.

Kullanim: python3 tools/gecmis-geri-donus-mutasyon.py
Cikis 0 = her oldurucu mutant KIRMIZI + her ilgisiz mutant YESIL + canli dosyalar temiz.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "gecmis-geri-donus-kapisi.py")
KUR = os.path.join(TOOLS, "gecmis-geri-donus-hook-kur.py")
KARDES = os.path.join(TOOLS, "commit-mesaji-kapisi.py")
OZET = os.path.join(TOOLS, "sizinti-desen-ozetleri.json")
URUNLER = os.path.join(ROOT, "urunler.json")


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# (ad, hedef_dosya, eski, yeni, oldurucu_mu)
MUTANTLAR = (
    # --- MENZIL: KAPININ CEKIRDEGI -------------------------------------------
    # 🔴 M1 ARIZANIN TA KENDISIDIR: menzil "yalniz YENI YAZILAN commit'ler"e
    # daraltilirsa, merge ile GERI GELEN eski sizintili commit'ler taranmaz ve
    # temizlik yine sessizce geri doner. Kapinin butun degeri bu satirdadir.
    ("M1  MENZIL 'yalniz yeni yazilanlar'a daraltildi (geri gelen commit gorunmez)",
     "kapi",
     '        if p.returncode == 0:\n            args += ["--not", remote_sha]',
     '        if p.returncode == 0:\n            args += ["--not", "--all"]', True),
    # --- EKSENLER -------------------------------------------------------------
    ("M2  ICERIK EKSENI OLDURULDU (aday kumesi bosaltildi)", "kapi",
     '    olcum["aday"] = len(aday_commit)',
     '    aday_commit = {}\n    olcum["aday"] = len(aday_commit)', True),
    ("M3  MESAJ EKSENI OLDURULDU (kusurlar hukme girmez)", "kapi",
     "        for k in modul.mesaj_kusurlari(modul.mesaj_govdesi(p.stdout), kayit,\n"
     "                                       maskeli=maskeli):",
     "        for k in []:", True),
    # --- FAIL-CLOSED YOLLARI --------------------------------------------------
    ("M4  ADAY BUTCESI fail-OPEN yapildi (buyuk itme sessizce taranmaz)", "kapi",
     "        if len(aday_commit) > butce:", "        if False:", True),
    ("M5  OZET ARTEFAKTI yoklugu fail-OPEN yapildi", "kapi",
     "    kayit, hata = modul.ozet_kaydi_yukle(ozet_yolu)\n    return kayit, hata",
     "    kayit, hata = modul.ozet_kaydi_yukle(ozet_yolu)\n"
     '    return kayit or {"dongu": 5000, "tuz": b"x", "desenler": []}, None', True),
    ("M6  BOZUK pre-push satiri SESSIZCE atlanir", "kapi",
     '        if len(parca) != 4:\n'
     '            hatalar.append("pre-push satiri COZULEMEDI (4 alan bekleniyor): %r"\n'
     "                           % satir[:120])\n            continue",
     "        if len(parca) != 4:\n            continue", True),
    # --- DIFF KAPSAMI ---------------------------------------------------------
    ("M7  MERGE birlesik diff'i KAPATILDI (evil merge kacar)", "kapi",
     '    if n > 1:\n        args.append("-c")',
     '    if False:\n        args.append("-c")', True),
    ("M8  YENIDEN ADLANDIRMA TESPITI ACILDI (rename sizintiyi gizler)", "kapi",
     '"--no-color", "--no-renames",', '"--no-color", "-M",', True),
    ("M9  --root KALDIRILDI (kok commit'in icerigi HIC taranmaz)", "kapi",
     '"--no-renames",\n            "--root"]', '"--no-renames"]', True),
    # --- KANCA KABLOSU --------------------------------------------------------
    ("M10 KANCA CAGRI SATIRI SILINDI (blok var, olcum yok)", "kur",
     'python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push '
     '< "$pruvo_gd_girdi"\npruvo_gd_rc=$?',
     "pruvo_gd_rc=0", True),
    ("M11 KANCA cagrisi YORUMA/echo'ya cevrildi "
     "(nobetci-cagri-satiri-nobetsiz sinifi)", "kur",
     'python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push '
     '< "$pruvo_gd_girdi"',
     'echo python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push '
     '< "$pruvo_gd_girdi"', True),
    ("M12 KANCA `exit 1` -> `exit 0` (fail-open)", "kur",
     '  echo "!! PUSH DURDURULDU — bu itme temizlenmis sizintiyi geri getiriyor '
     '(rc=$pruvo_gd_rc)."\n  exit 1\nfi',
     '  echo "!! PUSH DURDURULDU — bu itme temizlenmis sizintiyi geri getiriyor '
     '(rc=$pruvo_gd_rc)."\n  exit 0\nfi', True),
    ("M13 KANCA fail-closed on-kosulu fail-OPEN yapildi (betik yoksa gec)", "kur",
     '  echo "!! Sizinti kapisi fail-closed\'dir. Kasten atlamak icin: '
     'git push --no-verify"\n  exit 1\nfi',
     "  exit 0\nfi", True),
    # 🔴 M14 SESSIZ REGRESYON: stdin geri verilmezse kapi CALISIR ve YESIL yanar,
    # ama ayni kancadaki D1 SENKRONU bos girdi gorup HIC KOSMAZ -> site urunu
    # gosterir, EGE GOREMEZ. Kapinin kendi hukmunu HIC bozmayan bu mutant yalnizca
    # 11b iddiasiyla yakalanir; iddia silinirse burada gorunur.
    ("M14 STDIN kalan kancaya GERI VERILMIYOR (D1 senkronu sessizce olur)", "kur",
     'exec < "$pruvo_gd_girdi"\nrm -f "$pruvo_gd_girdi"',
     'rm -f "$pruvo_gd_girdi"', True),
    # --- ILGISIZ (kontrol): batarya YESIL kalmali -----------------------------
    ("K1  ilgisiz: baslik yorumunda kelime degisti", "kapi",
     "IKI KOL\n", "IKI  KOL\n", False),
    ("K2  ilgisiz: fonksiyon arasina bos satir eklendi", "kapi",
     "\ndef push_satirlari(metin):", "\n\ndef push_satirlari(metin):", False),
    ("K3  ilgisiz: kurulum betigine yorum satiri eklendi", "kur",
     "def kurulu_mu(yol):", "# ilgisiz yorum\ndef kurulu_mu(yol):", False),
)


def main():
    canli_once = {y: _sha(y) for y in (KAPI, KUR, KARDES, OZET, URUNLER)}
    sonuclar = []
    for ad, hedef, eski, yeni, oldurucu in MUTANTLAR:
        tmp = tempfile.mkdtemp(prefix="pruvo-gd-mut-")
        try:
            t_tools = os.path.join(tmp, "tools")
            os.makedirs(t_tools)
            for kaynak in (KAPI, KUR, KARDES, OZET):
                shutil.copy2(kaynak, os.path.join(t_tools, os.path.basename(kaynak)))
            # urunler.json 14 MB'dir ve HICBIR mutant onu degistirmez -> sembolik bag.
            os.symlink(URUNLER, os.path.join(tmp, "urunler.json"))
            yol = {"kapi": os.path.join(t_tools, os.path.basename(KAPI)),
                   "kur": os.path.join(t_tools, os.path.basename(KUR))}[hedef]
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            if eski not in metin:
                sonuclar.append((ad, oldurucu, None,
                                 "CAPA BULUNAMADI (mutasyon uygulanamadi — arac bayat)"))
                continue
            if metin.count(eski) != 1:
                sonuclar.append((ad, oldurucu, None,
                                 "capa %d kez gecti (tek olmali)" % metin.count(eski)))
                continue
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
            p = subprocess.run(
                [sys.executable, os.path.join(t_tools,
                                              "gecmis-geri-donus-kapisi.py"),
                 "--kendini-test"], capture_output=True, text=True, timeout=1800)
            kirmizi = [s.strip() for s in p.stdout.splitlines()
                       if s.strip().startswith("FAIL")]
            sonuclar.append((ad, oldurucu, p.returncode,
                             "; ".join(kirmizi[:3]) or "(kirmizi iddia yok)"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    hatalar = []
    print("%-64s %-9s %-3s %s" % ("MUTANT", "BEKLENEN", "RC", "HUKUM"))
    print("-" * 100)
    for ad, oldurucu, rc, not_ in sonuclar:
        beklenen = "KIRMIZI" if oldurucu else "YESIL"
        if rc is None:
            hukum, ok = "OLCULEMEDI", False
        elif oldurucu:
            ok = rc != 0
            hukum = "OLDU ✅" if ok else "SAG KALDI ❌"
        else:
            ok = rc == 0
            hukum = "YESIL ✅" if ok else "YANLIS ALARM ❌"
        if not ok:
            hatalar.append((ad, not_))
        print("%-64s %-9s %-3s %s" % (ad[:64], beklenen,
                                      "-" if rc is None else rc, hukum))
    print("-" * 100)

    canli_sonra = {y: _sha(y) for y in canli_once}
    bozuk = [y for y in canli_once if canli_once[y] != canli_sonra[y]]
    if bozuk:
        print("🔴 CANLI DOSYA DEGISTI (mutant sizdi): %s" % bozuk)
        hatalar.append(("canli dosya butunlugu", str(bozuk)))
    else:
        print("canli dosya sha256 esitligi: TAM ✅")
        for y in canli_once:
            print("   %-44s %s" % (os.path.basename(y), canli_once[y][:16]))

    oldurucu_sayi = sum(1 for _, o, _, _ in sonuclar if o)
    olen = sum(1 for (ad, o, rc, _) in sonuclar
               if o and rc is not None and rc != 0)
    ilgisiz_sayi = sum(1 for _, o, _, _ in sonuclar if not o)
    yesil = sum(1 for (ad, o, rc, _) in sonuclar if not o and rc == 0)
    print("SONUC: oldurucu mutant %d/%d OLDU · ilgisiz kontrol %d/%d YESIL"
          % (olen, oldurucu_sayi, yesil, ilgisiz_sayi))
    if hatalar:
        print("\nKIRMIZI:")
        for ad, not_ in hatalar:
            print("  * %s -> %s" % (ad, not_))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

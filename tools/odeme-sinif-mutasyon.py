#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/odeme-sinif-mutasyon.py — TESLIM SURESI SINIF KAPISI MUTASYON BATARYASI.

NE OLCER: tools/odeme-beyani-kapisi.py :: `ARALIK_DESEN` / `DOGRU_ARALIK` / `rakip_bul()`
uclusunun (vaka 6'nin sinif kapisi) 4 oldurucu mutanta karsi kapali olup olmadigini.
KABUL = bu betigin CIKIS KODU: 4 oldurucu mutant KIRMIZI yanmali, kontrol mutanti
(yalniz yorum degisir) YESIL kalmali. rc=0 ancak 5/5 beklenti tutarsa.

    python3 tools/odeme-sinif-mutasyon.py

NEDEN VAR (11 Eyl 2026): vaka 6'nin rakip-aralik deseni LITERAL ALTERNATION idi
(`5-7|3-6|2-4`) ve ayni kapi ayni gerekceyle 3. kez elden gecti (`b72c4f5b`, 28 Agu) —
listede olmayan her yeni aralik sessizce geciyordu. Sinif desenine cevrildi; sinif
kapisinin KENDISI de nobetcisiz kalmasin diye bu batarya yazildi.

🔴 IKI YON DE AYRI VAKA (BaBa sarti): tek yonlu nobetci olu nobetcidir.
  POZITIF kol -> S1: sinif deseni eski literal alternation'a geri donerse `4-8` /
                 `10-14` fiksturleri KACAR, kendini-test KIRMIZI yanmali.
  NEGATIF kol -> S3: "is gunu" baglam sarti dusurulurse `4-8 adet` / `10-14 mm`
                 YANLIS-POZITIF olur, kendini-test KIRMIZI yanmali.
  S2 (kanonik muafiyet silinir) ayrica olculur: muafiyetsiz sinif 491 govdede 11
  YANLIS isabet uretir ve kapi deploy.yml'de `continue-on-error`SIZ kostugu icin
  TUM EKIBIN yayinini durdurur ([[olculemedi-zaten-bagli-kapida-yayin-durdurur]]).

🔴 YONTEM — IZOLE KOPYA (canli govde ASLA yamalanmaz, [[mutant-canli-govdede-yasamaz]]):
kanonik kaynak okunur, yama BELLEKTE uygulanir, sonuc gecici bir dizine
`tools/odeme-beyani-kapisi.py` olarak yazilir ve ALT SUREÇ olarak `--kendini-test` ile
kosturulur. `--kendini-test` kolu sayfa taramasindan ONCE cikar, bu yuzden kopyanin
gercek repo agacinda oturmasi GEREKMEZ. Gecici dizin `finally` ile silinir; kanonik
kaynak hic acilmadigi icin batarya cokse bile agaci kirletemez.

🔴 CAPA TEKLIGI: her yama capasi kanonik kaynakta TAM BIR KEZ gecmeli. Gecmiyorsa
batarya HICBIR SEY olcmuyordur ve rc=2 ile DURUR (sessiz 0-mutant yesili YASAK —
[[fail-closed-kol-arkasindaki-kolu-maskeler]]).
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF_AD = "odeme-beyani-kapisi.py"
HEDEF = os.path.join(TOOLS, HEDEF_AD)

KIRMIZI_IZ = "SONUC: KIRMIZI"
YESIL_IZ = "SONUC: YESIL"

# (ad, eski, yeni, KIRMIZI_beklenir_mi, hangi_fiksturu_oldurur)
MUTANTLAR = [
    ("S1) SINIF deseni eski LITERAL ALTERNATION'a geri dondu (POZITIF kol)",
     'ARALIK_DESEN = re.compile(r"\\b(\\d{1,2}-\\d{1,2})\\s+iş\\s+günü\\b", re.I)',
     'ARALIK_DESEN = re.compile(r"\\b(5-7|3-6|2-4)\\s+iş\\s+günü\\b", re.I)',
     True, "P1 (4-8) · P2 (10-14) · P4 kacar"),

    ("S2) KANONIK MUAFIYET silindi (yanlis-pozitif kolu; 11 isabet / yayin durur)",
     "            if aralik != DOGRU_ARALIK]",
     "            if True]",
     True, "N2 (3-5 kanonik) yanlis yere yanar"),

    ("S3) 'iş günü' BAGLAM sarti dusuruldu (NEGATIF kol)",
     'ARALIK_DESEN = re.compile(r"\\b(\\d{1,2}-\\d{1,2})\\s+iş\\s+günü\\b", re.I)',
     'ARALIK_DESEN = re.compile(r"\\b(\\d{1,2}-\\d{1,2})\\b", re.I)',
     True, "N1 (4-8 adet) · N3 (10-14 mm) yanlis yere yanar"),

    ("S4) TEK KAYNAK capasi kaydirildi (DOGRU_ARALIK 3-5 -> 3-6)",
     'DOGRU_ARALIK = "3-5"',
     'DOGRU_ARALIK = "3-6"',
     True, "N2 rakip sayilir + D1 pozitif desen kanonik metni goremez"),

    ("K)  KONTROL MUTANTI (yalniz yorum degisti) — YESIL kalmali",
     "# ─── TESLİM SÜRESİ: SINIF KAPISI (11 Eyl 2026 — 3. tekrar, tekil yama YASAK) ──────────",
     "# ─── TESLİM SÜRESİ: SINIF KAPISI (11 Eyl 2026 — kontrol mutanti) ──────────",
     False, "hicbir vaka degismez"),
]


def kanonik():
    with open(HEDEF, encoding="utf-8") as f:
        return f.read()


def kostur(kaynak):
    """Yamali kaynagi IZOLE gecici dizinde `--kendini-test` ile kosturur."""
    dizin = tempfile.mkdtemp(prefix="pruvo-odeme-sinif-")
    try:
        kopya = os.path.join(dizin, HEDEF_AD)
        with open(kopya, "w", encoding="utf-8") as f:
            f.write(kaynak)
        p = subprocess.run([sys.executable, kopya, "--kendini-test"],
                           capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


def main():
    kaynak = kanonik()

    # 1) CAPA TEKLIGI — olcmeden once olcerin kendisi olculur.
    kayip = []
    for ad, eski, _yeni, _kirmizi, _oldurur in MUTANTLAR:
        adet = kaynak.count(eski)
        if adet != 1:
            kayip.append("%s -> capa %d kez gecti (1 olmali)" % (ad.split(")")[0], adet))
    if kayip:
        print("CAPA HATASI — batarya HICBIR SEY olcmuyor, DURDU:")
        for s in kayip:
            print("  " + s)
        print("SONUC: OLCULEMEDI (mutant sayisi 0)")
        return 2

    # 2) TABAN — yamasiz kaynak YESIL olmali. Degilse mutant sonuclari hukumsuzdur.
    trc, tcikti = kostur(kaynak)
    print("TABAN (yamasiz kaynak): rc=%d %s" % (trc, YESIL_IZ if YESIL_IZ in tcikti else "YESIL DEGIL"))
    if trc != 0 or YESIL_IZ not in tcikti:
        print(tcikti.strip()[-1500:])
        print("SONUC: OLCULEMEDI (taban kirmizi — mutant hukmu gecersiz)")
        return 2

    # 3) MUTANTLAR
    print("-" * 78)
    basarisiz = []
    for ad, eski, yeni, kirmizi_beklenir, oldurur in MUTANTLAR:
        rc, cikti = kostur(kaynak.replace(eski, yeni, 1))
        kirmizi_oldu = (rc != 0) and (KIRMIZI_IZ in cikti)
        tamam = kirmizi_oldu == kirmizi_beklenir
        print("%s %s" % ("OK  " if tamam else "HATA", ad))
        print("       beklenen=%s  olculen=%s  rc=%d  (%s)" % (
            "KIRMIZI" if kirmizi_beklenir else "YESIL",
            "KIRMIZI" if kirmizi_oldu else "YESIL", rc, oldurur))
        if not tamam:
            basarisiz.append(ad)
            print(cikti.strip()[-800:])

    print("-" * 78)
    oldurucu = sum(1 for m in MUTANTLAR if m[3])
    print("MUTANT: %d (oldurucu %d + kontrol %d)  |  BEKLENTIYE UYAN: %d  |  SAPAN: %d" % (
        len(MUTANTLAR), oldurucu, len(MUTANTLAR) - oldurucu,
        len(MUTANTLAR) - len(basarisiz), len(basarisiz)))
    print("SONUC: %s" % ("KIRMIZI" if basarisiz else "YESIL"))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/odeme-sinif-mutasyon.py — TESLIM SURESI SINIF KAPISI MUTASYON BATARYASI.

NE OLCER: tools/odeme-beyani-kapisi.py :: `ARALIK_DESEN` / `DOGRU_ARALIK` / `rakip_bul()`
uclusunun (vaka 6'nin sinif kapisi) oldurucu mutantlara karsi kapali olup olmadigini.
KABUL = bu betigin CIKIS KODU: her oldurucu mutant BEKLENEN VAKA KUMESINI oldurmeli,
kontrol mutanti (yalniz yorum degisir) hicbir vakaya dokunmamali. rc=0 ancak TUM
beklentiler (kume + rc ekseni) tutarsa.

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

🔴 ATIF OLCULUR, BASILMAZ (11 Eyl 2026 — 2. dilim, bu bataryanin KENDI kusuru):
onceki surum her mutant icin "hangi fiksturu oldurdu"yu SABIT METIN olarak basiyordu
(`oldurur` alani) ve yargisini yalnizca `rc != 0 and "SONUC: KIRMIZI"` uzerine
kuruyordu. Bir mutant YANLIS vakayi oldurse batarya yine `OK` yazardi ve basilan atif
YALAN olurdu — mutantin neyi yamadigi imzasindan okunmaz
([[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]]). Artik her mutant
`BEKLENEN_DUSEN` KUMESI tasir; hedef kapinin `--kendini-test` kolu makine okunur
`DUSEN:` satirini basar ve burada KUME ESITLIGI aranir. Atif artik iddiadir, sus degil.

🔴 CIKIS KODU EKSENI AYRI OLCULUR: vaka sayisi ekseni cikis kodu eksenini OLCMEZ
([[vaka-sayisi-ekseni-cikis-kodu-eksenini-olcmez]]). Her kosumda IKI YON de aranir —
  ❌>0 ⇒ rc≠0   ve   ❌=0 ⇒ rc=0
Bu eksenin kendisi de nobetcisiz kalmasin diye S5 mutanti VAR: deseni bozar **ve**
`sys.exit` kolunu duzlestirir; 3 vaka duserken rc=0 kalir. Batarya bunu TUTARSIZ diye
yakalamak zorundadir — yakalamazsa rc ekseni olu demektir.

🔴 YONTEM — IZOLE KOPYA (canli govde ASLA yamalanmaz, [[mutant-canli-govdede-yasamaz]]):
kanonik kaynak okunur, yama BELLEKTE uygulanir, sonuc gecici bir dizine
`tools/odeme-beyani-kapisi.py` olarak yazilir ve ALT SUREÇ olarak `--kendini-test` ile
kosturulur. `--kendini-test` kolu sayfa taramasindan ONCE cikar, bu yuzden kopyanin
gercek repo agacinda oturmasi GEREKMEZ. Gecici dizin `finally` ile silinir; kanonik
kaynak hic acilmadigi icin batarya cokse bile agaci kirletemez.

🔴 CAPA TEKLIGI: her yama capasi kanonik kaynakta TAM BIR KEZ gecmeli. Gecmiyorsa
batarya HICBIR SEY olcmuyordur ve rc=2 ile DURUR (sessiz 0-mutant yesili YASAK —
[[fail-closed-kol-arkasindaki-kolu-maskeler]]). Ayni fail-closed kural `DUSEN:` /
`HATA_SAYISI:` satirlari icin de gecerlidir: satir YOKSA kume BOS sayilmaz, olcum
GECERSIZ sayilir.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF_AD = "odeme-beyani-kapisi.py"
HEDEF = os.path.join(TOOLS, HEDEF_AD)

KIRMIZI_IZ = "SONUC: KIRMIZI"
YESIL_IZ = "SONUC: YESIL"

# Hedefin makine okunur atif satirlari. Ikisi de FAIL-CLOSED okunur.
DUSEN_DESEN = re.compile(r"^DUSEN:[ \t]*(.*)$", re.M)
SAYI_DESEN = re.compile(r"^HATA_SAYISI:[ \t]*(\d+)[ \t]+VAKA_SAYISI:[ \t]*(\d+)[ \t]*$", re.M)

# Her mutant bir sozluk: yamalar + BEKLENEN DUSEN KUMESI + rc ekseni beklentisi.
#   yamalar        : [(eski, yeni), ...] — her capa kanonik kaynakta TAM 1 kez gecmeli
#   beklenen_dusen : hedefin `DUSEN:` satirinda gorulmesi BEKLENEN vaka ADLARI (kume)
#   rc_tutarli     : bu mutantta "❌>0 ⇔ rc≠0" esitliginin KORUNMASI bekleniyor mu
MUTANTLAR = [
    {
        "ad": "S1) SINIF deseni eski LITERAL ALTERNATION'a geri dondu (POZITIF kol)",
        "yamalar": [
            ('ARALIK_DESEN = re.compile(r"\\b(\\d{1,2}-\\d{1,2})\\s+iş\\s+günü\\b", re.I)',
             'ARALIK_DESEN = re.compile(r"\\b(5-7|3-6|2-4)\\s+iş\\s+günü\\b", re.I)'),
        ],
        "beklenen_dusen": {"P1", "P2", "P4"},
        "rc_tutarli": True,
    },
    {
        "ad": "S2) KANONIK MUAFIYET silindi (yanlis-pozitif kolu; 11 isabet / yayin durur)",
        "yamalar": [
            ("            if aralik != DOGRU_ARALIK]", "            if True]"),
        ],
        "beklenen_dusen": {"N2"},
        "rc_tutarli": True,
    },
    {
        "ad": "S3) 'iş günü' BAGLAM sarti dusuruldu (NEGATIF kol)",
        "yamalar": [
            ('ARALIK_DESEN = re.compile(r"\\b(\\d{1,2}-\\d{1,2})\\s+iş\\s+günü\\b", re.I)',
             'ARALIK_DESEN = re.compile(r"\\b(\\d{1,2}-\\d{1,2})\\b", re.I)'),
        ],
        "beklenen_dusen": {"N1", "N3"},
        "rc_tutarli": True,
    },
    {
        "ad": "S4) TEK KAYNAK capasi kaydirildi (DOGRU_ARALIK 3-5 -> 3-6)",
        "yamalar": [
            ('DOGRU_ARALIK = "3-5"', 'DOGRU_ARALIK = "3-6"'),
        ],
        "beklenen_dusen": {"N2", "D1"},
        "rc_tutarli": True,
    },
    {
        # Bu mutant ATIF kumesini DEGIL, CIKIS KODU eksenini olduruyor: 3 vaka duser
        # ama `sys.exit` duzlestirildigi icin rc=0 kalir. Batarya bunu "rc ekseni
        # TUTARSIZ" diye yakalamazsa, ❌ sayisi dogruyken kirmizilarin cikis koduna
        # hic ulasmadigi sinif geri gelir ([[vaka-sayisi-ekseni-cikis-kodu-eksenini-olcmez]]).
        "ad": "S5) CIKIS KODU kolu duzlestirildi (desen de bozuk: 3 vaka duser, rc=0 kalir)",
        "yamalar": [
            ('ARALIK_DESEN = re.compile(r"\\b(\\d{1,2}-\\d{1,2})\\s+iş\\s+günü\\b", re.I)',
             'ARALIK_DESEN = re.compile(r"\\b(5-7|3-6|2-4)\\s+iş\\s+günü\\b", re.I)'),
            ("    sys.exit(1 if _hata else 0)", "    sys.exit(0)"),
        ],
        "beklenen_dusen": {"P1", "P2", "P4"},
        "rc_tutarli": False,
    },
    {
        "ad": "K)  KONTROL MUTANTI (yalniz yorum degisti) — hicbir vaka DUSMEMELI",
        "yamalar": [
            ("# ─── TESLİM SÜRESİ: SINIF KAPISI (11 Eyl 2026 — 3. tekrar, tekil yama YASAK) ──────────",
             "# ─── TESLİM SÜRESİ: SINIF KAPISI (11 Eyl 2026 — kontrol mutanti) ──────────"),
        ],
        "beklenen_dusen": set(),
        "rc_tutarli": True,
    },
]


def kanonik():
    with open(HEDEF, encoding="utf-8") as f:
        return f.read()


def yamala(kaynak, yamalar):
    for eski, yeni in yamalar:
        kaynak = kaynak.replace(eski, yeni, 1)
    return kaynak


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


def atif_oku(cikti):
    """`DUSEN:` + `HATA_SAYISI:` satirlarini FAIL-CLOSED okur.

    Donus: (dusen_kume, hata_sayisi, gecersiz_sebep). Satir yoksa kume BOS SAYILMAZ —
    olcum GECERSIZ sayilir; yoksa atif satirini hic basmayan bir mutant, hicbir vakayi
    oldurmemis gibi gorunurdu ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
    """
    d = DUSEN_DESEN.search(cikti)
    s = SAYI_DESEN.search(cikti)
    if not d:
        return None, None, "hedef `DUSEN:` satirini basmadi (atif olculemez)"
    if not s:
        return None, None, "hedef `HATA_SAYISI:/VAKA_SAYISI:` satirini basmadi (rc ekseni olculemez)"
    ham = d.group(1).strip()
    kume = set() if ham == "-" else {p.strip() for p in ham.split(",") if p.strip()}
    hata_sayisi = int(s.group(1))
    if len(kume) != hata_sayisi:
        return None, None, ("`DUSEN:` %d ad tasiyor ama HATA_SAYISI=%d — hedefin iki "
                            "satiri birbiriyle celisiyor" % (len(kume), hata_sayisi))
    return kume, hata_sayisi, None


def degerlendir(rc, cikti, beklenen_dusen, rc_tutarli_beklenir):
    """Tek kosumu iki EKSENDE yargilar. Donus: sapma aciklamalari listesi (bos = gecti)."""
    kume, hata_sayisi, gecersiz = atif_oku(cikti)
    if gecersiz:
        return ["OLCULEMEDI: " + gecersiz]

    sapma = []

    # EKSEN 1 — ATIF: hangi iddia oldu? Kume ESITLIGI aranir, "kirmizi yandi" YETMEZ.
    if kume != beklenen_dusen:
        eksik = sorted(beklenen_dusen - kume)
        fazla = sorted(kume - beklenen_dusen)
        sapma.append("ATIF: beklenen={%s} olculen={%s}%s%s" % (
            ",".join(sorted(beklenen_dusen)) or "-", ",".join(sorted(kume)) or "-",
            ("  OLMESI gerekirken YASAYAN: " + ",".join(eksik)) if eksik else "",
            ("  BEKLENMEDEN OLEN: " + ",".join(fazla)) if fazla else ""))

    # EKSEN 2 — CIKIS KODU: iki yon de ayri vaka (❌>0 ⇒ rc≠0 ve ❌=0 ⇒ rc=0).
    rc_tutarli = (hata_sayisi > 0) == (rc != 0)
    if rc_tutarli != rc_tutarli_beklenir:
        sapma.append("RC EKSENI: ❌=%d rc=%d -> %s (beklenen %s)" % (
            hata_sayisi, rc,
            "TUTARLI" if rc_tutarli else "TUTARSIZ",
            "TUTARLI" if rc_tutarli_beklenir else "TUTARSIZ"))

    # Metin izi, rc ile celismemeli (eski surumun tek olcutu buydu; kol olarak DURUR).
    kirmizi_iz = KIRMIZI_IZ in cikti
    if kirmizi_iz != (hata_sayisi > 0):
        sapma.append("METIN IZI: 'SONUC: %s' basildi ama ❌=%d" % (
            "KIRMIZI" if kirmizi_iz else "YESIL", hata_sayisi))

    return sapma


def meta_kol(kaynak):
    """ATIF karsilastiricisinin KENDISI olduruluyor mu? (gorev sarti 3d)

    S1'in yamasi KIRMIZI yakar ve gercek dusen kume {P1,P2,P4}'tur. Ayni kosumu
    KASITLI YANLIS beklenti ({N1}) ile degerlendirdigimizde karsilastirici SAPMA
    bildirmek ZORUNDA. Bildirmiyorsa atif ekseni olu demektir ve batarya, eski
    surumu gibi, yalnizca "kirmizi yandi mi" oluyor.
    """
    rc, cikti = kostur(yamala(kaynak, MUTANTLAR[0]["yamalar"]))
    dogru = degerlendir(rc, cikti, {"P1", "P2", "P4"}, True)
    yanlis = degerlendir(rc, cikti, {"N1"}, True)
    ok = (not dogru) and any(s.startswith("ATIF:") for s in yanlis)
    print("%s M1) ATIF karsilastiricisi CANLI mi (yanlis beklenti SAPMA uretmeli)" % (
        "OK  " if ok else "HATA"))
    print("       dogru beklenti -> %s  |  kasitli yanlis beklenti -> %s" % (
        "sapma yok" if not dogru else "SAPMA(!) " + " ; ".join(dogru),
        "SAPMA yakalandi" if any(s.startswith("ATIF:") for s in yanlis) else "SAPMA YOK(!)"))

    # M2 — FAIL-CLOSED kolu: atif satiri hic basilmazsa kume BOS SAYILMAMALI, olcum
    # GECERSIZ sayilmali. Bu kol olculmezse "atif satirini basmayi unutan" bir hedef,
    # hicbir vakayi oldurmemis gibi gorunur ve kontrol mutantindan ayirt edilemez
    # ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).
    rc2, cikti2 = kostur(kaynak.replace('    print("DUSEN: %s"', '    _sus = ("DUSEN: %s"', 1))
    sapma2 = degerlendir(rc2, cikti2, set(), True)
    ok2 = any(s.startswith("OLCULEMEDI:") for s in sapma2)
    print("%s M2) ATIF satiri YOKKEN olcum GECERSIZ sayiliyor mu (fail-closed)" % (
        "OK  " if ok2 else "HATA"))
    print("       `DUSEN:` basilmiyor -> %s" % (
        sapma2[0] if sapma2 else "SAPMA YOK(!) — bos kume sanildi, fail-OPEN"))
    # Iki meta kolu AYRI raporlanir: birlesik tek bayrak, dusen kolun ADINI yutardi.
    return ([] if ok else ["M1) atif karsilastiricisi"]) + ([] if ok2 else ["M2) atif fail-closed"])


def main():
    kaynak = kanonik()

    # 1) CAPA TEKLIGI — olcmeden once olcerin kendisi olculur.
    kayip = []
    for m in MUTANTLAR:
        for eski, _yeni in m["yamalar"]:
            adet = kaynak.count(eski)
            if adet != 1:
                kayip.append("%s -> capa %d kez gecti (1 olmali): %.60s" % (
                    m["ad"].split(")")[0], adet, eski))
    if kayip:
        print("CAPA HATASI — batarya HICBIR SEY olcmuyor, DURDU:")
        for s in kayip:
            print("  " + s)
        print("SONUC: OLCULEMEDI (mutant sayisi 0)")
        return 2

    # 2) TABAN — yamasiz kaynak YESIL, dusen kume BOS, rc ekseni TUTARLI olmali.
    trc, tcikti = kostur(kaynak)
    tsapma = degerlendir(trc, tcikti, set(), True)
    print("TABAN (yamasiz kaynak): rc=%d %s  atif/rc ekseni: %s" % (
        trc, YESIL_IZ if YESIL_IZ in tcikti else "YESIL DEGIL",
        "TEMIZ" if not tsapma else "SAPMA"))
    if trc != 0 or YESIL_IZ not in tcikti or tsapma:
        for s in tsapma:
            print("  " + s)
        print(tcikti.strip()[-1500:])
        print("SONUC: OLCULEMEDI (taban kirmizi — mutant hukmu gecersiz)")
        return 2

    # 3) MUTANTLAR — her biri ATIF + RC ekseninde ayri ayri yargilanir.
    print("-" * 78)
    basarisiz = []
    for m in MUTANTLAR:
        rc, cikti = kostur(yamala(kaynak, m["yamalar"]))
        sapma = degerlendir(rc, cikti, m["beklenen_dusen"], m["rc_tutarli"])
        print("%s %s" % ("OK  " if not sapma else "HATA", m["ad"]))
        print("       OLDURDUGU IDDIA: {%s}  rc=%d  rc-ekseni=%s" % (
            ",".join(sorted(m["beklenen_dusen"])) or "-", rc,
            "TUTARLI" if m["rc_tutarli"] else "TUTARSIZ (beklenen)"))
        if sapma:
            basarisiz.append(m["ad"])
            for s in sapma:
                print("       " + s)
            print(cikti.strip()[-800:])

    # 4) META — atif ekseninin kendisi olduruluyor mu?
    print("-" * 78)
    basarisiz.extend(meta_kol(kaynak))

    print("-" * 78)
    oldurucu = sum(1 for m in MUTANTLAR if m["beklenen_dusen"] or not m["rc_tutarli"])
    toplam_kol = len(MUTANTLAR) + 2  # mutantlar + M1 + M2
    print("MUTANT: %d (oldurucu %d + kontrol %d) + META 2  |  BEKLENTIYE UYAN: %d/%d  |  SAPAN: %d" % (
        len(MUTANTLAR), oldurucu, len(MUTANTLAR) - oldurucu,
        toplam_kol - len(basarisiz), toplam_kol, len(basarisiz)))
    print("SONUC: %s" % ("KIRMIZI" if basarisiz else "YESIL"))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())

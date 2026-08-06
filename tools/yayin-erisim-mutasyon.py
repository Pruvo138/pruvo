#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/yayin-erisim-test.py'nin CURUTME (mutasyon) araci.

NE OLCER: "kabul testi YESIL" demek "nobetci CANLI" demek DEGILDIR. Bu arac nobetciyi
(ve kablolandigi deploy.yml / alarm is akisini) BILEREK bozar ve kabul testinin
GERCEKTEN kirmizi yandigini — ve HANGI EKSENIN yandigini — olcer.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]):
  * her mutant kosumunda IDDIA SAYISI taban kosumla AYNI olmali — sayi dususu "mutant
    testi cokertti" demektir ve o kirmizi bir OLCUM DEGILDIR (cokme kirmiziyla karisir);
  * kirmizi EKSEN KODLARI kumesi mutantin BEYANIYLA TAM ESIT olmali. Fazladan kirmizi
    da KUSURDUR (gevsek "KAPSAR" olcutu YOKTUR).

🔴 BEYAN EDILMIS SURVIVOR YASAK ([[beyan-edilmis-survivor]]): E1-E7'nin HER BIRI icin
   kirmizi kumesi TAM OLARAK {o eksen} olan en az bir mutant vardir; asagidaki
   "TEK-KIRMIZI HARITASI" bunu KOSARAK dogrular.

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]]). Kosum basinda ve sonunda kaynaklarin sha256'lari
   karsilastirilir.

🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/yayin-erisim-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontroller YESIL + her eksenin tek-kirmizi mutanti
VAR + canli kaynaklar sha256 olarak DEGISMEDI.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

NOBETCI = "tools/yayin-erisim-nobeti.py"
TEST = "tools/yayin-erisim-test.py"
IS_AKISI = "tools/is-akisi-kapisi.py"
DEPLOY = ".github/workflows/deploy.yml"
# 🔴 5 Agu 2026 SERIT AYRIMI: bu kabul testinin adimi (serit B) nobet.yml'e TASINDI.
# Ayna agacta IKISI DE bulunmali: E7 hem "canli kol YAYIN is akisinda kosmuyor"
# (deploy.yml) hem "kabul testi BLOKLAMAYAN seritte kosuyor" (nobet.yml) der.
NOBET = ".github/workflows/nobet.yml"
ALARM = ".github/workflows/yayin-erisim-alarmi.yml"

HEDEFLER = (NOBETCI, TEST, IS_AKISI, DEPLOY, NOBET, ALARM)
DOKUNULMAZ = [os.path.join(ROOT, y) for y in HEDEFLER]

EKSENLER = ("E1", "E2", "E3", "E4", "E5", "E6", "E7")

FAILS = []


def check(mesaj, kosul, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────────────
# MUTANTLAR — (kod, aciklama, hedef, [(bulunacak, yerine), ...], beyan, olcut)
#   beyan: kirmizi beklenen EKSEN kodlari ([] = KONTROL mutanti, YESIL kalmali)
# ─────────────────────────────────────────────────────────────────────────────────────
M1 = ("M1", "🔴 YONTEM HEAD'e cevrildi (3 Agu'da olculen kusur GORUNMEZ olur)",
      NOBETCI, [('\nYONTEM = "GET"\n', '\nYONTEM = "HEAD"\n')], ["E2"], "ESIT")

M2 = ("M2", "404 'acik' sayiliyor (silinmis sayfa yesil yanar)",
      NOBETCI, [("\nACIK_KODLAR = (200,)\n", "\nACIK_KODLAR = (200, 404)\n")],
      ["E3"], "ESIT")

M3 = ("M3", "403 'acik' sayiliyor — hem metot ekseni hem hukum ekseni duser",
      NOBETCI, [("\nACIK_KODLAR = (200,)\n", "\nACIK_KODLAR = (200, 403)\n")],
      # CAPRAZ (gerekce): ayirt edici vaka (E2) da 403 uretir; 403'u acik saymak IKI
      # ekseni birden dusurur — ayrik degiller, ayni fiziksel olguyu olcerler.
      ["E2", "E3"], "ESIT")

M4 = ("M4", "KUME TABANI kaldirildi (collapsed kaynak sessizce 'hepsi acik' olur)",
      NOBETCI, [("\nKUME_TABANI = 250\n", "\nKUME_TABANI = 0\n")], ["E1"], "ESIT")

M5 = ("M5", "/urun/ eksen siniri kalkti (17.000 URL kumeye sizar, ikinci kopya)",
      NOBETCI,
      [('            elif p.startswith("/urun/"):\n                continue'
        '                       # EKSEN SINIRI: canli-saglik-kapisi K2',
        '            elif p.startswith("/urun/"):\n                ust.append(p)'
        '                  # EKSEN SINIRI KALDIRILDI')],
      ["E1"], "ESIT")

M6 = ("M6", "🔴 AG ARIZASI 'ACIK' sayiliyor (fail-closed -> fail-open)",
      NOBETCI,
      [('            return {"yol": yol, "url": url, "sinif": "ARIZA", "kod": None,',
        '            return {"yol": yol, "url": url, "sinif": "ACIK", "kod": 200,')],
      ["E5"], "ESIT")

M7 = ("M7", "OLCUM ARIZASI, KAPALI KANITINI EZIYOR (kanit kayboluyor)",
      NOBETCI,
      [("    if kapali:\n        satirlar.append(\"HUKUM: KAPALI",
        "    if kapali and not ariza:\n        satirlar.append(\"HUKUM: KAPALI")],
      ["E5"], "ESIT")

M8 = ("M8", "HIZ SINIRI devre disi (uc oran sinirina carpar, olcum guvenilmez olur)",
      NOBETCI,
      [("    bekleme = (1.0 / hiz) if hiz and hiz > 0 else 0.0",
        "    bekleme = 0.0")],
      ["E6"], "ESIT")

M9 = ("M9", "SESSIZ ORNEKLEME (kume kirpiliyor ama 'hepsi acik' deniyor)",
      NOBETCI,
      [("    for i, yol in enumerate(yollar):",
        "    for i, yol in enumerate(yollar[:3]):")],
      ["E6"], "ESIT")

M10 = ("M10", "YONLENDIRME HIC IZLENMIYOR (301 -> 200 sayfa KAPALI sanilir)",
       NOBETCI,
       [("    for _adim in range(YONLENDIRME_TAVANI + 1):",
         "    for _adim in range(1):")],
       ["E4"], "ESIT")

M11 = ("M11", "YONLENDIRME RAPORDAN SILINDI (nereye gittigi gorunmez)",
       NOBETCI,
       [('        if k["sinif"] == "YONLENDI":\n            satirlar.append',
         '        if False:\n            satirlar.append')],
       ["E4"], "ESIT")

M12 = ("M12", "🔴 ALARM KOLU YAYIN YOLUNA BAGLANDI (`push` tetikleyicisi eklendi)",
       ALARM,
       [("on:\n  schedule:", "on:\n  push:\n    branches: [main]\n  schedule:")],
       ["E7"], "ESIT")

M13 = ("M13", "ALARM CRON'U YOGUN DAKIKAYA KAYDIRILDI (tetikleme sessizce dusuyor)",
       ALARM, [('- cron: "26 * * * *"', '- cron: "0 * * * *"')], ["E7"], "ESIT")

M14 = ("M14", "nobet.yml'deki kabul testi adimi ETKISIZLESTIRILDI (olu nobetci)",
       NOBET,
       [("        run: python3 tools/yayin-erisim-test.py",
         "        run: python3 tools/yayin-erisim-test.py || true")],
       ["E7"], "ESIT")

M15 = ("M15", "SERIT_B beyani SILINDI (serit degisimi gerekcesiz kaliyor)",
       IS_AKISI,
       [('    ("nobet.yml", "serit-b", "tools/yayin-erisim-test.py"):\n'
         '        "Aracin KENDINI sinamasi: yerel HTTP fikstur sunucusu (dis ag YOK) + kume "',
         '    ("nobet.yml", "serit-b", "tools/yayin-erisim-SILINDI.py"):\n'
         '        "Aracin KENDINI sinamasi: yerel HTTP fikstur sunucusu (dis ag YOK) + kume "')],
       ["E7"], "ESIT")

M16 = ("M16", "KUMEYE ELLE URL GOMULDU (kaynak disi liste sizdi)",
       NOBETCI,
       [('        kaynaklar.append(("K3 site koku (ana sayfa)", 1, True, "/"))\n'
         '        sayfa.append("/")',
         '        kaynaklar.append(("K3 site koku (ana sayfa)", 1, True, "/"))\n'
         '        sayfa.append("/")\n        sayfa.append("/elle-yazilmis-sayfa/")')],
       ["E1"], "ESIT")

# ── KONTROL MUTANTLARI (YESIL kalmali) ──────────────────────────────────────────────
# Surucu "her seye kirmizi yanan" gurultulu bir alarma donusmesin: anlam tasimayan
# degisiklikler bataryayi KIRMIZI yakmamali, yoksa yukaridaki "OLDU" hukumlerinin hicbiri
# mutasyonun kendisine atfedilemez (cokme kirmiziyla karisir).
K1 = ("K1", "ilgisiz: nobetci basligindaki bir kelime degisti",
      NOBETCI, [("KULLANIM\n========", "KULLANIM\n========\n")], [], "ESIT")

K2 = ("K2", "ilgisiz: sabit yanina aciklama yorumu eklendi",
      NOBETCI, [("\nYONLENDIRME_TAVANI = 5\n",
                 "\nYONLENDIRME_TAVANI = 5   # zincir tavani\n")], [], "ESIT")

K3 = ("K3", "ilgisiz: alarm is akisi yorumunda bir kelime degisti",
      ALARM, [("# ══════════════════════════════════════════════════════════════════════════════\n"
               "# CADANS + NABIZ",
               "# ══════════════════════════════════════════════════════════════════════════════\n"
               "# CADANS VE NABIZ")], [], "ESIT")

K4 = ("K4", "ilgisiz: kabul testi baslik metni degisti",
      TEST, [('    print("YAYIN ERISIM NOBETCISI — KABUL TESTI")',
              '    print("YAYIN ERISIM NOBETCISI - KABUL TESTI")')], [], "ESIT")

MUTANTLAR = (M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12, M13, M14, M15, M16,
             K1, K2, K3, K4)
OLCUTLER = ("ESIT",)

IDDIA_RE = re.compile(r"^IDDIA SAYISI:\s*(\d+)\s*$", re.M)
KIRMIZI_RE = re.compile(r"^KIRMIZI IDDIA:\s*(\S+)\s*$", re.M)


def kayitlari_dogrula():
    """Kayitlarin KENDI sekli FAIL-CLOSED suzulur: taninmayan olcut VARSAYILANA DUSMEZ."""
    hata = []
    kodlar = set()
    for kayit in MUTANTLAR:
        if len(kayit) != 6:
            hata.append("%r: kayit 6 alanli olmali" % (kayit[0],))
            continue
        kod, _aciklama, hedef, _degisimler, beyan, olcut = kayit
        if kod in kodlar:
            hata.append("%s: MUKERRER mutant kodu" % kod)
        kodlar.add(kod)
        if olcut not in OLCUTLER:
            hata.append("%s: bilinmeyen olcut %r" % (kod, olcut))
        if hedef not in HEDEFLER:
            hata.append("%s: bilinmeyen hedef %r" % (kod, hedef))
        for b in beyan:
            if b not in EKSENLER:
                hata.append("%s: bilinmeyen eksen kodu %r" % (kod, b))
    return hata


def ayna_kur(hedef):
    """Gecici aynaya KOPYALAR. Kaynak agaca YAZMA YOKTUR."""
    shutil.copytree(os.path.join(ROOT, "tools"), os.path.join(hedef, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "arsiv", "fikstur"),
                    symlinks=False)
    os.makedirs(os.path.join(hedef, ".github", "workflows"))
    for ad in (DEPLOY, NOBET, ALARM):
        shutil.copy2(os.path.join(ROOT, ad), os.path.join(hedef, ad),
                     follow_symlinks=True)
    return hedef


def symlinkleri_bul(kok):
    bulunan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        for ad in altlar + dosyalar:
            y = os.path.join(dizin, ad)
            if os.path.islink(y):
                bulunan.append(os.path.relpath(y, kok))
    return bulunan


def mutasyonla(pristine, degisimler, kod):
    """Mutasyonu METNE uygular. Dayanak yoksa/coklu ise HARNESS BAYATTIR -> gurultulu
    duser; 'olctum' deyip hicbir sey olcmemek en kotu haldir."""
    metin = pristine
    for eski, yeni in degisimler:
        adet = metin.count(eski)
        if adet != 1:
            raise SystemExit(
                "HARNESS BAYAT (%s): mutasyon dayanagi %d kez bulundu (tam 1 olmali):\n%r\n"
                "(kaynak degismis olabilir — mutasyonu guncelle; yoksa bu arac HICBIR SEY "
                "olcmuyor demektir)" % (kod, adet, eski[:200]))
        metin = metin.replace(eski, yeni, 1)
    return metin


def kos(ayna, pristine, mutant=None):
    """Aynayi TEMIZ kaynaklarla YENIDEN KURAR, sonra (varsa) TEK mutanti yazar ve kabul
    testini kosturur. Doner: (cikis_kodu, iddia_sayisi|None, kirmizi_kod_kumesi, kuyruk).

    🔴 HER KOSUMDA TAM YENIDEN YAZIM: yalnizca mutasyonlanan dosyayi yazmak bir onceki
    mutanti aynada BIRAKIR ve sonraki mutantlar iki bozulmayi birden tasir."""
    metinler = dict(pristine)
    if mutant:
        metinler.update(mutant)
    for ad, metin in metinler.items():
        with open(os.path.join(ayna, ad), "w", encoding="utf-8") as f:
            f.write(metin)
    r = subprocess.run([sys.executable, os.path.join(ayna, TEST)],
                       capture_output=True, text=True, timeout=1800)
    cikti = (r.stdout or "") + (r.stderr or "")
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    mk = KIRMIZI_RE.search(cikti)
    ham = mk.group(1) if mk else ""
    kirmizi = set(k for k in ham.split(",") if k and k != "-")
    return r.returncode, iddia, kirmizi, cikti[-1800:]


def main():
    print("YAYIN ERISIM NOBETCISI — MUTASYON (CURUTME) HARNESS'I")
    print("hedef kabul testi: %s (tam takim)" % TEST)

    sekil = kayitlari_dogrula()
    if sekil:
        print("KAYIT SEKLI BOZUK — hicbir mutant kosulmadi:")
        for h in sekil:
            print("  ✘ %s" % h)
        return 1

    canli_once = {y: sha(y) for y in DOKUNULMAZ}
    pristine = {}
    for ad in HEDEFLER:
        with open(os.path.join(ROOT, ad), encoding="utf-8") as f:
            pristine[ad] = f.read()

    print("\n0) KAYNAK SHA256 (kosum BASI)")
    for y in DOKUNULMAZ:
        print("   %-30s %s" % (os.path.basename(y), canli_once[y]))

    tmp = tempfile.mkdtemp(prefix="yayin-erisim-mutasyon-")
    try:
        ayna = ayna_kur(os.path.join(tmp, "ayna"))
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, t_kirmizi, t_kuyruk = kos(ayna, pristine)
        if not check("taban kosumu YESIL (cikis 0, kirmizi iddia 0)",
                     t_rc == 0 and not t_kirmizi,
                     "cikis=%d kirmizi=%s" % (t_rc, sorted(t_kirmizi) or "-")):
            print("\n  --- taban ciktisinin kuyrugu ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: mutant kosumlari ANLAMSIZ olurdu — durduruluyor.")
            return 1
        if not check("taban IDDIA SAYISI okunabildi", t_iddia is not None,
                     "iddia=%s" % t_iddia):
            return 1
        print("   TABAN IDDIA SAYISI = %d  (capa DEGIL: kosumda olculdu)" % t_iddia)

        oldurucu = [m for m in MUTANTLAR if m[4]]
        kontroller = [m for m in MUTANTLAR if not m[4]]
        print("\n2) MUTASYON BATARYASI — %d kosum (%d kirmizi-beklentili, %d kontrol)"
              % (len(MUTANTLAR), len(oldurucu), len(kontroller)))
        matris = []
        tek_kirmizi = {}
        for kod, aciklama, hedef, degisimler, beyan, olcut in MUTANTLAR:
            metin = mutasyonla(pristine[hedef], degisimler, kod)
            rc, iddia, kirmizi, kuyruk = kos(ayna, pristine, {hedef: metin})
            sayi_ok = (iddia == t_iddia)
            if beyan:
                eksik = [b for b in beyan if b not in kirmizi]
                fazla = sorted(kirmizi - set(beyan))
                gecti = sayi_ok and rc == 1 and bool(kirmizi) and not eksik and not fazla
                detay = ("cikis=%d iddia=%s/%d kirmizi=%s olcut=%s"
                         % (rc, iddia, t_iddia, ",".join(sorted(kirmizi)) or "-", olcut))
                if eksik:
                    detay += "  ⚠️ EKSIK: " + ",".join(eksik) + " (mutant SAG KALDI)"
                if fazla:
                    detay += ("  ⚠️ ESIT OLCUTU: BEYAN DISI FAZLA KIRMIZI -> "
                              + ",".join(fazla))
                beklenti = "KIRMIZI/" + olcut
                if len(kirmizi) == 1:
                    tek_kirmizi.setdefault(sorted(kirmizi)[0], []).append(kod)
            else:
                gecti = sayi_ok and rc == 0 and not kirmizi
                detay = ("cikis=%d iddia=%s/%d kirmizi=%s"
                         % (rc, iddia, t_iddia, ",".join(sorted(kirmizi)) or "-"))
                beklenti = "YESIL"
            if not sayi_ok:
                detay += ("  ⚠️ IDDIA SAYISI TUTMUYOR -> mutant testi COKERTMIS olabilir; "
                          "bu 'kirmizi' OLCUM DEGIL")
            check("%-4s [%s] %s" % (kod, beklenti, aciklama), gecti, detay)
            if not gecti:
                print("       --- %s ciktisinin kuyrugu ---\n%s" % (kod, kuyruk))
            matris.append((kod, beklenti, rc, iddia,
                           ",".join(sorted(kirmizi)) or "-", ",".join(beyan) or "-"))
            for y in DOKUNULMAZ:
                if sha(y) != canli_once[y]:
                    check("KAYNAK AGAC DEGISTI (ayna kacagi!) [%s -> %s]"
                          % (kod, os.path.basename(y)), False)

        print("\n   --- MUTASYON MATRISI ---")
        print("   %-5s %-14s %-6s %-9s %-16s %s"
              % ("kod", "beklenti", "cikis", "iddia", "kirmizi", "beyan"))
        for kod, beklenti, rc, iddia, kirmizi, beyan in matris:
            print("   %-5s %-14s %-6d %-9s %-16s %s"
                  % (kod, beklenti, rc, "%s/%d" % (iddia, t_iddia), kirmizi, beyan))

        print("\n3) TEK-KIRMIZI HARITASI — her eksenin TEK BASINA yakilabilir mutanti")
        for eksen in EKSENLER:
            kodlar = tek_kirmizi.get(eksen, [])
            check("%s ekseninin TEK-KIRMIZI mutanti VAR" % eksen, bool(kodlar),
                  "mutant: %s" % (",".join(kodlar) or "YOK — bu eksen AYRI IDDIA "
                                                    "sayilamaz"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n4) KAYNAK DOKUNULMAZLIGI (sha256, kosum SONU)")
    canli_sonra = {y: sha(y) for y in DOKUNULMAZ}
    for y in DOKUNULMAZ:
        check("%s sha256 BASTAKIYLE AYNI (mutant diskte kalmadi)" % os.path.basename(y),
              canli_sonra[y] == canli_once[y],
              "once=%s… sonra=%s…" % (canli_once[y][:16], canli_sonra[y][:16]))

    oldu = sum(1 for m in MUTANTLAR if m[4])
    print("\nSONUC: %d kirmizi-beklentili + %d kontrol mutanti kosuldu; %d eksen olculdu."
          % (oldu, len(MUTANTLAR) - oldu, len(EKSENLER)))
    if FAILS:
        print("KUSUR — %d:" % len(FAILS))
        for h in FAILS:
            print("  ✘ " + h)
        return 1
    print("TUM MUTANTLAR BEYANINA UYDU, KONTROLLER YESIL, HER EKSENIN TEK-KIRMIZI "
          "MUTANTI VAR ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

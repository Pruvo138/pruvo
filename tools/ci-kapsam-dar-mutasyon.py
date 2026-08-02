#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/ci-kapsam-test.py — js/mjs/cjs BAYRAK CIKARIMI (K8) + DAR BAYRAK (K9)
eksenlerinin CURUTME (mutasyon) araci.

NE OLCER: "kapi YESIL" demek "eksen CANLI" demek DEGILDIR. Bu arac ci-kapsam-test.py'yi
BILEREK bozar ve `--kendini-test` bataryasinin GERCEKTEN kirmizi yandigini — ve HANGI
EKSENIN yandigini — olcer.

NEDEN BU IKI EKSEN: ci-kapsam-test.py "yazilmis ama CI'da kosmayan kapi" sinifini
yakalayan META-KAPIDIR; kendi kor noktasi bu sinifi GORUNMEZ kilar. Iki kor nokta
olculdu ve kapatildi:
  K8 — 32 js/mjs/cjs dosyasi icin bayrak cikarimi HIC yapilmiyordu ("olculemedi" kovasi).
  K9 — "dosya cagriliyor mu" soruluyordu; `--kendini-test` gibi bir IC NOBET bayragiyla
       cagrilmak "kosuyor" sayiliyordu. Bu, jenerator/test/kabul.py'nin tam takiminin
       aylarca kosmamasinin ve hacim.js <-> OpenSCAD arasindaki %7,6–%51,2 sapmanin
       gorulmemesinin (sari seride fiyat hacimden turer) SINIFIDIR.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]):
  * her mutant kosumunda IDDIA SAYISI taban kosumla AYNI olmali — sayi dususu "mutant
    testi cokertti" demektir ve o kirmizi bir OLCUM DEGILDIR (cokme kirmiziyla karisir);
  * kirmizi EKSEN KODLARI kumesi mutantin BEYANIYLA karsilastirilir.

🔴 OLCUT, HER MUTANTIN KENDI KAYDINDA — TEK IZINLI DEGER: ESIT. Kirmizi kume BEYANA TAM
   ESIT olmali; FAZLADAN kirmizi da KUSURDUR. Gevsek (KAPSAR) bir olcut YOKTUR.

🔴 BEYAN EDILMIS SURVIVOR YASAK ([[beyan-edilmis-survivor]]): K8 ve K9'un HER BIRI icin
   kirmizi kumesi TAM OLARAK {o eksen} olan en az bir mutant vardir; "TEK-KIRMIZI
   HARITASI" bunu kosumda CALISTIRARAK dogrular.

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]] — `finally` ile geri alma deseni bu evde YASAK).
   Kosum basinda ve sonunda kaynaklarin sha256'lari karsilastirilir.

AYNA NEDEN GIT DEPOSU: ci-kapsam-test.py kesfi `git ls-files` uzerinden yapar (os.walk
DEGIL — [[ayna-kapi-kesif-ekseni]]). Ayna bu yuzden `git init` edilir ve KESFEDILEN tum
dosyalar + is akislari indekse alinir; boylece aynadaki kesif kumesi GERCEK repodakiyle
AYNIDIR ve taban kosumu YESIL olur.

🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/ci-kapsam-dar-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontroller YESIL + K8/K9'un tek-kirmizi mutanti VAR
+ canli kaynaklar sha256 olarak DEGISMEDI.
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

KAPI = "ci-kapsam-test.py"
DEPLOY_REL = os.path.join(".github", "workflows", "deploy.yml")
KAPI_YOL = os.path.join(TOOLS, KAPI)
DEPLOY_YOL = os.path.join(ROOT, DEPLOY_REL)
DOKUNULMAZ = [KAPI_YOL, DEPLOY_YOL]

# Bu turun EKLEDIGI eksenler. K1–K7 miras eksenlerdir; onlarin curutulmesi ayri
# turlarda yapildi ve bu aracin IDDIASI DEGILDIR (fazladan kirmizi yakarlarsa ESIT
# olcutu zaten konusur).
EKSENLER = ("K8", "K9")
# `--kendini-test` bataryasinin TUM eksen kodlari. Bir mutant MIRAS bir ekseni de
# dusurebilir (or. AST kablo nobetcisi K6); ESIT olcutu geregi o da BEYAN EDILMEK
# ZORUNDADIR — beyan edilmeyen fazla kirmizi KUSURDUR. Ama TEK-KIRMIZI HARITASI
# yalniz EKSENLER icin sorulur: bu tur K1–K7'yi IDDIA ETMEZ.
TUM_EKSENLER = ("K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9")

IDDIA_RE = re.compile(r"^IDDIA SAYISI:\s*(\d+)\s*$", re.M)
KIRMIZI_RE = re.compile(r"^KIRMIZI IDDIA:\s*(\S+)\s*$", re.M)

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
# MUTANTLAR — (kod, aciklama, [(bulunacak, yerine), ...], beyan, olcut)
#   hedef DAIMA tools/ci-kapsam-test.py'dir (eksenlerin govdesi orada yasar)
#   beyan: kirmizi beklenen EKSEN kodlari ([] = KONTROL mutanti, YESIL kalmali)
# ─────────────────────────────────────────────────────────────────────────────────────

M1 = ("M1", "K8 GOVDE OLDURME: js bayrak cikarimi DAIMA BOS kume dondurur "
            "(kova sessizce eski 'olculemedi' haline doner)",
      [("    tum = set()\n    for satir in metin.splitlines():\n"
        "        if _JS_SATIR_YORUM_RE.match(satir):",
        "    tum = set()\n    for satir in []:\n"
        "        if _JS_SATIR_YORUM_RE.match(satir):")],
      ["K8"], "ESIT")

# 🔴 M2 TARIHI: ilk yazimda mutasyon `.match(...)` -> `.search(...)` idi ve MUTANT SAG
# KALDI. Sebep OLCULDU: capa `^...$` ile ANKRAJLI oldugu icin iki cagri AYNI hukmu verir
# — yani o "mutant" hicbir sey degistirmeyen bir NO-OP'tu, kusur nobetcide DEGILDI.
# Gercek asiri-genisleme ankrajlarin DUSMESIDIR; asagidaki mutant onu yapar.
M2 = ("M2", "K8 ASIRI GENISLETME: literal capasinin ANKRAJLARI dusuruldu -> prose "
            "icindeki mensiyon da bayrak sayiliyor (uyari katmani uydurma bayraklarla "
            "dolar, kimse bakmaz olur)",
      [(r'_JS_BAYRAK_RE = re.compile(r"^(--[A-Za-z0-9][\w-]*)(?:=.*)?$")',
        r'_JS_BAYRAK_RE = re.compile(r"(--[A-Za-z0-9][\w-]*)(?:=.*)?")')],
      ["K8"], "ESIT")

M3 = ("M3", "K8 SESSIZ IDDIA: js 'ayri kol' ekseni OLCULMEDI yerine BOS KUME "
            "donduruluyor (olculmemis bir olumsuzluk iddia edilir)",
      [("            m = _JS_BAYRAK_RE.match(govde.strip())\n"
        "            if m:\n                tum.add(m.group(1))\n    return tum, None",
        "            m = _JS_BAYRAK_RE.match(govde.strip())\n"
        "            if m:\n                tum.add(m.group(1))\n    return tum, set()")],
      ["K8"], "ESIT")

M4 = ("M4", "K9 EKSEN OLDURME: dar bayrak envanteri DAIMA BOS "
            "(ic-nobetle kosan kabul testi yine 'kosuyor' sayilir — kok kusur geri gelir)",
      [("        if all(dar for _a, _k, dar in cagrilar):\n"
        "            bulgular.append((yol, cagrilar))",
        "        if False and all(dar for _a, _k, dar in cagrilar):\n"
        "            bulgular.append((yol, cagrilar))")],
      ["K9"], "ESIT")

M5 = ("M5", "K9 SAHTE SUCLAMA: 'HER cagri dar' yerine 'HERHANGI BIR cagri dar' "
            "(bayraksiz cagrisi olan mesru testler de suclanir)",
      [("        if all(dar for _a, _k, dar in cagrilar):",
        "        if any(dar for _a, _k, dar in cagrilar):")],
      ["K9"], "ESIT")

M6 = ("M6", "K9 ELLE KACAGI: ELLE tetikli is akisindaki bayraksiz cagri da sayiliyor "
            "(kimse tetiklemezse tam takim yine kosmaz — kacak)",
      [("    for akis_yol, metin, akis_sinifi in akislar:\n"
        "        if otomatik_mi(akis_sinifi):\n"
        "            komutlar.append((akis_yol, _icra_komutlari(metin)))",
        "    for akis_yol, metin, akis_sinifi in akislar:\n"
        "        if True:\n"
        "            komutlar.append((akis_yol, _icra_komutlari(metin)))")],
      ["K9"], "ESIT")

M7 = ("M7", "K9 KUME BUDAMA: DAR_BAYRAKLAR tek jetona daraltildi "
            "(`--ic-nobetci` ile kosan dosyalar sessizce kacar)",
      [('DAR_BAYRAKLAR = frozenset((\n'
        '    "--kendini-test", "--ic-nobetci", "--self-test", "--oz-test", "--kendi-test",\n'
        '))',
        'DAR_BAYRAKLAR = frozenset((\n'
        '    "--kendini-test",\n'
        '))')],
      ["K9"], "ESIT")

# 🔴 M8 TARIHI: ilk yazim `raise SystemExit(1)` ile bloklamayi taklit ediyordu ve
# IDDIA SAYISI None geldi — `SystemExit` `BaseException`tir, `denetle()`'nin
# `except Exception` sarmalindan KACAR ve sureci COKERTIR. Cokme kirmiziyla karisir,
# yani o kosum bir OLCUM DEGILDI ([[mutasyon-kaniti-yeniden-uretilebilir]]). Gercek
# "bloklayici yapma" hamlesi bulguyu `hatalar`a yazmaktir; asagidaki mutant onu yapar.
M8 = ("M8", "🔴 K9 BLOKLAYICIYA CEVIRME: dar bayrak bulgusu `hatalar`a yaziliyor "
            "(bugun 6 gercek dosya var -> TUM ekibin yayini durur)",
      [("            satirlar.extend(uyari_katmani(kesif, dosya_metinleri, bayrak_env,\n"
        "                                          alt_kume_izin, akislar))",
        "            satirlar.extend(uyari_katmani(kesif, dosya_metinleri, bayrak_env,\n"
        "                                          alt_kume_izin, akislar))\n"
        "            for _s in satirlar:\n"
        "                if \"(e) 🔴 DAR BAYRAK\" in _s and not _s.endswith(\": 0\"):\n"
        "                    hatalar.append(\"DAR BAYRAK: \" + _s)")],
      ["K9"], "ESIT")

M9 = ("M9", "🔴 IKI EKSENIN ORTAK KABLOSU: uyari_katmani() js+dar cagrilarini yapmiyor "
            "(govdeler DOGRU cevap verir, ONLARA KIMSE SORMAZ)",
      [("        else:\n            tum, ayri = _js_bayrak_analizi(metin)\n"
        "            olculen_js += 1",
        "        else:\n            tum, ayri = set(), None\n"
        "            olculen_js += 1"),
       ("        dar = dar_bayrak_envanteri(akislar, kesif)",
        "        dar = []")],
      # CAPRAZ (gerekce): TEK bir fonksiyonun (uyari_katmani) IKI cagrisi birden
      # dusuruluyor; her iki YENI eksenin UCTAN UCA kolu da bu cagriya baglidir.
      # K6 (SUZGEC/AST kablo nobetcisi) de MIRAS eksen olarak yanar ve bu DOGRUDUR:
      # kablo tablosuna `uyari_katmani -> (_js_bayrak_analizi, dar_bayrak_envanteri)`
      # girisi tam bu mutasyon icin eklendi. Uc eksen ayrik degil, AYNI kabloyu
      # paylasiyor -> UCU de beyan edilir; olcut yine ESIT (fazlalik KUSURDUR).
      ["K6", "K8", "K9"], "ESIT")

# ---- KONTROL MUTANTLARI (YESIL KALMALI) ------------------------------------
# [[fikstur-degeri-mutasyon-koru]]: kontrol mutanti olmayan bir batarya, "her
# degisiklikte kirmizi yanan" bir nobetciyi de "dogru olcen" sanir.
K1 = ("K1c", "KONTROL: konuyla ILGISIZ yorum satiri eklendi (davranis degismez)",
      [("UYARI_TAVANI = 20",
        "# ilgisiz rutin yorum (kontrol mutanti)\nUYARI_TAVANI = 20")],
      [], "ESIT")

K2 = ("K2c", "KONTROL: dar bayrak kovasinin BASIM TAVANI degisti (hukum degismez, "
             "bugun 6 bulgu var ve tavan 20 -> liste yine tam basilir)",
      [("UYARI_TAVANI = 20", "UYARI_TAVANI = 21")],
      [], "ESIT")

K3 = ("K3c", "KONTROL: js literal capasi backtick YERINE ayni kumeyi farkli sirayla "
             "yaziyor (semantik AYNI) -> YESIL kalmali",
      [("""(['"`])((?:\\\\.|(?!\\1)[^\\\\])*)\\1""",
        """([`'"])((?:\\\\.|(?!\\1)[^\\\\])*)\\1""")],
      [], "ESIT")

MUTANTLAR = (M1, M2, M3, M4, M5, M6, M7, M8, M9, K1, K2, K3)
OLCUTLER = ("ESIT",)


def kayitlari_dogrula():
    """Kayitlarin KENDI sekli fail-closed dogrulanir: bilinmeyen olcut/eksen mutasyon
    KOSULMADAN reddedilir (bozuk kayit sessizce 'gecti' saymasin)."""
    hata = []
    kodlar = set()
    for kayit in MUTANTLAR:
        if len(kayit) != 5:
            hata.append("%r: kayit 5 alanli olmali (kod, aciklama, degisimler, beyan, olcut)"
                        % (kayit[0],))
            continue
        kod, _aciklama, degisimler, beyan, olcut = kayit
        if kod in kodlar:
            hata.append("%s: MUKERRER mutant kodu" % kod)
        kodlar.add(kod)
        if olcut not in OLCUTLER:
            hata.append("%s: bilinmeyen olcut %r — TEK izinli olcut: %s (gevsek olcut "
                        "YOKTUR)" % (kod, olcut, ", ".join(OLCUTLER)))
        if not degisimler:
            hata.append("%s: mutasyon BOS -> hicbir sey olcmez" % kod)
        for b in beyan:
            if b not in TUM_EKSENLER:
                hata.append("%s: bilinmeyen eksen kodu %r" % (kod, b))
    kapsanan = {b for _k, _a, _d, beyan, _o in MUTANTLAR for b in beyan}
    for eksen in EKSENLER:
        if eksen not in kapsanan:
            hata.append("%s ekseni HICBIR mutantta beyan edilmemis -> bu arac o ekseni "
                        "IDDIA EDIYOR ama CURUTMUYOR" % eksen)
    return hata


def izlenen_dosyalar():
    r = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("git ls-files basarisiz: " + r.stderr.strip())
    return r.stdout.splitlines()


def ayna_kur(hedef, yollar):
    """Gecici aynaya KOPYALAR ve `git init` eder. Kaynak agaca YAZMA YOKTUR."""
    os.makedirs(hedef)
    for rel in yollar:
        kaynak = os.path.join(ROOT, rel)
        if not os.path.exists(kaynak):
            continue
        varis = os.path.join(hedef, rel)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        shutil.copy2(kaynak, varis, follow_symlinks=True)
    subprocess.run(["git", "-C", hedef, "init", "-q"], check=True,
                   capture_output=True)
    subprocess.run(["git", "-C", hedef, "add", "-A", "-f"], check=True,
                   capture_output=True)
    return hedef


def symlinkleri_bul(kok):
    bulunan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        if ".git" in altlar:
            altlar.remove(".git")
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
    """Ayna kapiyi TEMIZ kaynakla YENIDEN yazar, sonra (varsa) mutanti yazar ve
    `--kendini-test` bataryasini kosturur.
    Doner: (cikis_kodu, iddia_sayisi|None, kirmizi_kod_kumesi, kuyruk).

    🔴 HER KOSUMDA TAM YENIDEN YAZIM: yalnizca mutasyonlanani yazmak bir onceki mutanti
    aynada BIRAKIR ve sonraki kosumlar iki bozulmayi birden tasir (yalanci 'oldu')."""
    yol = os.path.join(ayna, "tools", KAPI)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(mutant if mutant is not None else pristine)
    r = subprocess.run([sys.executable, yol, "--kendini-test"],
                       capture_output=True, text=True, timeout=1800, cwd=ayna)
    cikti = (r.stdout or "") + (r.stderr or "")
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    mk = KIRMIZI_RE.search(cikti)
    ham = mk.group(1) if mk else ""
    kirmizi = set(k for k in ham.split(",") if k and k != "-")
    return r.returncode, iddia, kirmizi, cikti[-2500:]


def main():
    print("CI KAPSAM KAPISI — js BAYRAK CIKARIMI (K8) + DAR BAYRAK (K9) MUTASYON HARNESS'I")
    print("hedef: tools/ci-kapsam-test.py --kendini-test (9 eksenli batarya)")

    sekil = kayitlari_dogrula()
    if sekil:
        print("KAYIT SEKLI BOZUK — hicbir mutant kosulmadi:")
        for h in sekil:
            print("  ✘ %s" % h)
        return 1

    canli_once = {y: sha(y) for y in DOKUNULMAZ}
    with open(KAPI_YOL, encoding="utf-8") as f:
        pristine = f.read()

    print("\n0) KAYNAK SHA256 (kosum BASI)")
    for y in DOKUNULMAZ:
        print("   %-26s %s" % (os.path.basename(y), canli_once[y]))

    tmp = tempfile.mkdtemp(prefix="ci-kapsam-dar-mutasyon-")
    try:
        ayna = ayna_kur(os.path.join(tmp, "ayna"), izlenen_dosyalar())
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        # --- 1) TABAN -----------------------------------------------------------
        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, t_kirmizi, t_kuyruk = kos(ayna, pristine)
        taban_ok = check("taban kosumu YESIL (cikis 0, kirmizi iddia 0)",
                         t_rc == 0 and not t_kirmizi,
                         "cikis=%d kirmizi=%s" % (t_rc, sorted(t_kirmizi) or "-"))
        if not taban_ok:
            print("\n  --- taban ciktisinin kuyrugu ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: mutant kosumlari ANLAMSIZ olurdu — durduruluyor.")
            return 1
        if not check("taban IDDIA SAYISI okunabildi", t_iddia is not None,
                     "iddia=%s" % t_iddia):
            return 1
        print("   TABAN IDDIA SAYISI = %d  (capa DEGIL: kosumda olculdu)" % t_iddia)

        # --- 2) BATARYA ---------------------------------------------------------
        oldurucu = [m for m in MUTANTLAR if m[3]]
        kontroller = [m for m in MUTANTLAR if not m[3]]
        print("\n2) MUTASYON BATARYASI — %d kosum (%d kirmizi-beklentili, %d kontrol)"
              % (len(MUTANTLAR), len(oldurucu), len(kontroller)))
        matris = []
        tek_kirmizi = {}
        for kod, aciklama, degisimler, beyan, olcut in MUTANTLAR:
            metin = mutasyonla(pristine, degisimler, kod)
            rc, iddia, kirmizi, kuyruk = kos(ayna, pristine, metin)
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
                              + ",".join(fazla) + " (ya beyan ya iddia yanlis)")
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
        print("   %-6s %-14s %-6s %-9s %-16s %s"
              % ("kod", "beklenti", "cikis", "iddia", "kirmizi", "beyan"))
        for kod, beklenti, rc, iddia, kirmizi, beyan in matris:
            print("   %-6s %-14s %-6d %-9s %-16s %s"
                  % (kod, beklenti, rc, "%s/%d" % (iddia, t_iddia), kirmizi, beyan))

        # --- 3) TEK-KIRMIZI HARITASI (beyan edilmis survivor yasagi) ------------
        print("\n3) TEK-KIRMIZI HARITASI — her eksenin TEK BASINA yakilabilir mutanti")
        for eksen in EKSENLER:
            kodlar = tek_kirmizi.get(eksen, [])
            check("%s ekseninin TEK-KIRMIZI mutanti VAR" % eksen, bool(kodlar),
                  "mutant: %s" % (",".join(kodlar) or "YOK — bu eksen AYRI IDDIA "
                                                    "sayilamaz"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 4) KAYNAK DOKUNULMAZLIGI ----------------------------------------------
    print("\n4) KAYNAK DOKUNULMAZLIGI (sha256, kosum SONU)")
    canli_sonra = {y: sha(y) for y in DOKUNULMAZ}
    for y in DOKUNULMAZ:
        check("%s sha256 BASTAKIYLE AYNI (mutant diskte kalmadi)" % os.path.basename(y),
              canli_sonra[y] == canli_once[y],
              "once=%s… sonra=%s…" % (canli_once[y][:16], canli_sonra[y][:16]))

    oldu = sum(1 for m in MUTANTLAR if m[3])
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SILME KARANTINASI CURUTME (mutasyon) BATARYASI — 12 Agu 2026.

NE OLCER: "kabul testi YESIL" hicbir sey KANITLAMAZ; kanit, mantigi BOZUNCA kirmizi
yandigini GORMEKTIR. Bu arac `tools/uzlastirici_karantina.py`nin her kolunu, silme
kolunun d1-sync/onarim kablosunu ve is akisi adimlarini BILEREK bozar; her mutantta
`tools/uzlastirici-karantina-test.py`in GERCEKTEN kirmizi yandigini SAYIYLA olcer.

NEDEN VAR (OLCULEN ZARAR — 11 Agu 2026, kosum 31532464176)
==========================================================
D1 uzlastiricisi 37 MESRU katalog satirini "FAZLA" sanip SILDI (eszamanli bir urun
partisinin D1'e yazdigi, push'u henuz inmemis satirlar). Karantina o silmeyi IKI
GOZLEME yayar. Bu batarya, karantinanin SESSIZCE geri alinabilecegi her tek-satirlik
yolu tek tek kapatir.

🔴 KABUL = CIKIS KODU DEGIL, IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]): her mutant kosumunda iddia sayisi TABAN
   kosumla AYNI olmali. Sayi dusuyorsa mutant testi COKERTMISTIR ve o kirmizi bir OLCUM
   DEGILDIR (cokme kirmiziyla karisir).

🔴 KONTROL MUTANTI SART ([[fikstur-degeri-mutasyon-koru]]): anlam tasimayan degisiklikler
   (yorum metni, ADIM ADI) bataryayi kirmizi yakmamali — yoksa "oldu" hukumlerinin hicbiri
   mutasyona atfedilemez. ADIM ADI kontrolu ayrica bir IDDIADIR: kabul testi adimlari
   ADLARINDAN degil ICRA ETTIKLERI SEYDEN bulmalidir.

🔴 GUVENLIK: mutasyon YALNIZCA gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]]). Kosum basinda/sonunda kaynak sha256 karsilastirilir.

🔴 PYTHONPATH / BYTECODE TUZAGI: alt kosum `PYTHONDONTWRITEBYTECODE=1` ve bos
   `PYTHONPATH` ile kosar. Aksi halde ayni yola ayni saniyede yazilan ayni uzunluktaki
   mutasyon .pyc onbelleginden SERVIS EDILIR ve mutant hic uygulanmamis gorunur
   ([[mutasyon-bytecode-onbellegi]]); PYTHONPATH sizarsa da CANLI modul yuklenir ve
   batarya tautolojiye doner.

Kullanim: python3 tools/uzlastirici-karantina-mutasyon.py
Cikis 0 = her oldurucu mutant KIRMIZI + kontrol mutantlari YESIL + iddia sayilari
korundu + canli kaynaklar sha256 olarak DEGISMEDI.
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

KARANTINA = "tools/uzlastirici_karantina.py"
TEST = "tools/uzlastirici-karantina-test.py"
D1SYNC = "tools/d1-sync.py"
ONARIM = "tools/uzlastirici-onarim.py"
UZL = os.path.join(".github", "workflows", "d1-uzlastirici.yml")
NOBET = os.path.join(".github", "workflows", "nobet.yml")
HEDEFLER = (KARANTINA, D1SYNC, ONARIM, UZL, NOBET)
DOKUNULMAZ = [os.path.join(ROOT, y) for y in (HEDEFLER + (TEST,))]

FAILS = []


def check(mesaj, kosul, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# DAYANAK METINLER — tek yerde. Biri bayatlarsa harness GURULTULU duser.
# ─────────────────────────────────────────────────────────────────────────────
ILK_GOZLEM = (
    "        if not _kayit_gecerli(k):\n"
    "            # (1) ILK GOZLEM (ya da bozuk kayit) -> SILME YOK, karantinaya yaz.\n"
    "            acilan.append(uid)\n"
    "            yeni[uid] = _yeni_kayit(sha, simdi)\n"
    "            continue\n")
SHA_KARSILASTIRMASI = '        if str(k["sha"]).strip() != sha:\n'
OKUNAMADI_DONUSU = (
    '        return {"hukum": "OLCULEMEDI", "silinecek": [], "acilan": sorted(fazla),\n'
    '                "bekleyen": [], "bayat": [], "dusen": [],\n'
    '                "kayitlar": {u: _yeni_kayit(sha, simdi) for u in fazla}, "yaz": True}\n')
DUSME_KOLU = "    dusen = sorted(set(kayitlar) - set(fazla))\n"
BAYATLIK_KOLU = '        if (float(simdi) - float(k["ts"])) > TAZELIK_SN:\n'
MUAF_KUMESI = (
    "    return {u for u, k in kayitlar.items()\n"
    '            if _kayit_gecerli(k) and (float(simdi) - float(k["ts"])) <= TAZELIK_SN}\n')
SURUM_KONTROLU = '    if govde.get("surum") != SURUM:\n'
SHA_GECERLI = '    return isinstance(sha, str) and len(sha.strip()) >= 7\n'

YUKLEME_ADIMI = (
    "      - name: Karantina damgasini yukle (artifact — SONRAKI kosumun ikinci gozlemi)\n"
    "        if: steps.olcum.outputs.sapma == 'yok' || steps.olcum.outputs.sapma == 'var'\n"
    "        uses: actions/upload-artifact@v4\n"
    "        with:\n"
    "          name: d1-karantina-damgasi\n"
    "          path: karantina-damgasi.json\n"
    "          if-no-files-found: error\n")
TEYIT_SATIRI = ("          python3 tools/d1-sync.py --durum "
                "--karantina-damgasi karantina-damgasi.json\n")
INDIRME_ADI = ("      - name: Karantina damgasi — onceki kosumun silme gozlemlerini "
               "indir\n")
KADANS_IZNI = ("    permissions:\n"
               "      contents: read\n")
D1_SILINEN_ATAMASI = '        silinen = list(_kk["silinecek"])\n'
ONARIM_CAGRISI = ('        rc, cikti = kos(["python3", D1_SYNC, "--karantina-damgasi", '
                  "KARANTINA_DAMGASI],\n                        kok)\n")
MUAF_UYGULAMASI = "                karantinali = [u for u in fazla if u in muaf]\n"

# ─────────────────────────────────────────────────────────────────────────────
# MUTANTLAR — (kod, aciklama, HEDEF, [(bul, yerine), ...], kirmizi_bekleniyor)
# ─────────────────────────────────────────────────────────────────────────────
M1 = ("M1", "🔴 ILK GOZLEMDE SIL (karantina esigi 1'den 0'a indi): id ilk kez FAZLA "
            "gorulunce SILINIR -> 11 Agu'nun 37 satiri AYNEN silinir", KARANTINA,
      [(ILK_GOZLEM,
        "        if not _kayit_gecerli(k):\n"
        "            silinecek.append(uid)\n"
        "            continue\n")], True)

M2 = ("M2", "🔴 SHA KARSILASTIRMASI SOKULDU: ikinci gozlem AYNI origin/main ucunda olsa "
            "bile siler -> ucustaki parti tek kosum arayla silinebilir", KARANTINA,
      [(SHA_KARSILASTIRMASI, "        if True:\n")], True)

M3 = ("M3", "🔴 FAIL-OPEN: damga OKUNAMAYINCA 'OLCULEMEDI' yerine SILMEYE devam eder — "
            "'okuyamadim -> sil' yolu ACILIR (kapatilan hatanin ta kendisi)", KARANTINA,
      [(OKUNAMADI_DONUSU,
        '        return {"hukum": "SILINDI", "silinecek": sorted(fazla), "acilan": [],\n'
        '                "bekleyen": [], "bayat": [], "dusen": [],\n'
        '                "kayitlar": {}, "yaz": True}\n')], True)

M4 = ("M4", "🔴 KARANTINADAN DUSME KOLU (K4) SOKULDU: agacta beliren id kayitta KALIR -> "
            "kayit sonsuza kadar yasar ve ilerideki bir SHA degisiminde MESRU satir silinir",
      KARANTINA,
      [(DUSME_KOLU,
        "    yeni.update({u: kayitlar[u] for u in kayitlar if u not in fazla})\n"
        "    dusen = []\n")], True)

M5 = ("M5", "🔴 KAYIT BAYATLIGI KOLU SOKULDU: saatler once yazilmis bir kayit hala "
            "'ikinci gozlem' sayilir -> uzun sessizlikten sonraki ilk kosum MESRU satir siler",
      KARANTINA, [(BAYATLIK_KOLU, "        if False:\n")], True)

M6 = ("M6", "🔴 TEYIT MUAFIYETI BAYAT KAYDA DA ACILDI: `--durum` bayat karantina kaydini "
            "da muaf sayar -> gercek bir sapma 'karantinada' diye SUSTURULUR", KARANTINA,
      [(MUAF_KUMESI,
        "    return {u for u, k in kayitlar.items() if _kayit_gecerli(k)}\n")], True)

M7 = ("M7", "🔴 DAMGA SURUM KONTROLU SOKULDU: sema kaymis/bayat bir damga GECERLI sayilir "
            "-> yanlis alanlarla 'ikinci gozlem' hukmu uretilir", KARANTINA,
      [(SURUM_KONTROLU, "    if False and govde.get(\"surum\") != SURUM:\n")], True)

M8 = ("M8", "🔴 SHA GECERLILIK ESIGI SOKULDU: bos/kirpik SHA gecerli sayilir -> "
            "'ayni mi farkli mi' sorusu SORULAMAZKEN silme yolu ACIK kalir", KARANTINA,
      [(SHA_GECERLI, "    return isinstance(sha, str)\n")], True)

M9 = ("M9", "🔴 DAMGA YUKLEME ADIMI SILINDI: karantina hafizasi kosum sonunda KAYBOLUR -> "
            "her kosum 'ilk gozlem' sanir; silme kolu ASLA calismaz, gercek oksuz satirlar "
            "birikir", UZL, [(YUKLEME_ADIMI, "")], True)

M10 = ("M10", "🔴 TEYIT ADIMI BAYRAGI DUSURULDU: karantinaya alinan id 'onarilamadi' "
              "sayilir -> her karantina acilisinda kosum KIRMIZI olur ve karantina fiilen "
              "GERI ALINIR (silmeye geri donmek icin en kolay bahane)", UZL,
       [(TEYIT_SATIRI, "          python3 tools/d1-sync.py --durum\n")], True)

M11 = ("M11", "🔴 YUKLEME FAIL-OPEN: `if-no-files-found: error` -> `warn`. Damga dogmasa "
              "bile adim SESSIZCE gecer; hafiza kaybi hicbir yerde kirmizi yakmaz", UZL,
       [(YUKLEME_ADIMI, YUKLEME_ADIMI.replace("if-no-files-found: error",
                                              "if-no-files-found: warn"))], True)

M12 = ("M12", "🔴 KADANS KOLUNUN `actions: read` IZNI DUSURULDU: cagrilan is akisinin "
              "jetonu tavanlanir, damga HIC inmez -> push kolunda silme KALICI olarak olu "
              "kalir (sessiz gerileme)", NOBET,
       [("    permissions:\n      contents: read\n"
         "      # 🔴 Cagrilan is akisinin jetonu CAGIRAN JOB'un izinleriyle TAVANLANIR. "
         "Silme\n", "    permissions:\n      contents: read\n      # (izin dusuruldu) "
         "Silme\n"),
        ("      actions: read\n  # ══════", "  # ══════")], True)

M13 = ("M13", "🔴 KARAR HESAPLANIP ATILDI: d1-sync karantina sonucunu `silinen`e ATAMAZ -> "
              "hukum log'a basilir ama DELETE listesi DEGISMEZ (en sinsi hal: log YESIL "
              "gorunur, silme aynen olur)", D1SYNC,
       [(D1_SILINEN_ATAMASI, '        _atilan = list(_kk["silinecek"])\n')], True)

M14 = ("M14", "🔴 SURUCU BAYRAGI DUSURULDU: uzlastirici-onarim.py d1-sync'i "
              "`--karantina-damgasi` OLMADAN cagirir -> karantina kodu repoda DURUR ama "
              "uzlastirici kolunda HIC calismaz", ONARIM,
       [(ONARIM_CAGRISI, '        rc, cikti = kos(["python3", D1_SYNC], kok)\n')], True)

M15 = ("M15", "🔴 MUAFIYET EKSIK KOLUNA SIZDI: `--durum` karantina muafiyetini `eksik` "
              "listesine de uygular -> D1'de GERCEKTEN olmayan urun 'karantinada' diye "
              "yesil gecer (Ege o urunu ONEREMEZ, kimse gormez)", D1SYNC,
       [(MUAF_UYGULAMASI,
         MUAF_UYGULAMASI + "                eksik = [u for u in eksik if u not in muaf]\n")],
       True)

M16 = ("M16", "🔴 SESSIZ UZERINE YAZMA: sapma VAR kolundaki `--temizle-yoksa` `--temizle`ye "
              "cevrildi -> VAR OLAN damga her kosumda EZILIR, ikinci gozlem hafizasi "
              "sifirlanir ve silme kolu SESSIZCE olur (gercek oksuz satirlar birikir)",
       UZL,
       [("        run: python3 tools/uzlastirici_karantina.py --temizle-yoksa "
         "karantina-damgasi.json\n",
         "        run: python3 tools/uzlastirici_karantina.py --temizle "
         "karantina-damgasi.json\n")], True)

# ── KONTROL MUTANTLARI (YESIL kalmali) ──────────────────────────────────────
K1 = ("K1", "ilgisiz: karantina modulundeki bir YORUM metni degistirildi (semantik AYNI)",
      KARANTINA,
      [("    # (4) Karantinadaki id agacta belirdi (artik FAZLA degil) -> kayit DUSER.\n",
        "    # (4) Agacta beliren id icin kayit tutulmaz (yorum guncellendi).\n")], False)

K2 = ("K2", "ilgisiz: is akisi ADIM ADI degistirildi. Bu ayni zamanda bir IDDIADIR — kabul "
            "testi adimlari ADINDAN degil ICRA ETTIGI SEYDEN bulmali (ad bir mensiyondur)",
      UZL, [(INDIRME_ADI, "      - name: Damga indirme (baska bir ad)\n")], False)

K3 = ("K3", "ilgisiz: nobet.yml'e aciklama yorumu eklendi (is akisi semantigi AYNI)",
      NOBET, [("  d1-kadans:\n", "  # kadans kolu — gerekce ustteki blokta\n  d1-kadans:\n")],
      False)

MUTANTLAR = (M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12, M13, M14, M15, M16,
             K1, K2, K3)

IDDIA_RE = re.compile(r"^(\d+) iddia kosturuldu, (\d+) KIRMIZI\.$", re.M)


def ayna_kur(hedef):
    """tools/ + .github/workflows/ tam FIZIKSEL kopya (symlink IZLENIR)."""
    os.makedirs(hedef)
    shutil.copytree(os.path.join(ROOT, "tools"), os.path.join(hedef, "tools"),
                    symlinks=False)
    shutil.copytree(os.path.join(ROOT, ".github", "workflows"),
                    os.path.join(hedef, ".github", "workflows"), symlinks=False)
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
    metin = pristine
    for bul, yerine in degisimler:
        n = metin.count(bul)
        if n != 1:
            raise SystemExit(
                "🔴 HARNESS BAYAT (%s): dayanak metin %d kez bulundu (1 olmali).\n"
                "   Aranan: %r" % (kod, n, bul[:200]))
        metin = metin.replace(bul, yerine, 1)
    return metin


def kos(ayna, metinler):
    """Aynadaki kabul testini kostur -> (rc, iddia, kirmizi, kuyruk)."""
    for rel, metin in metinler.items():
        with open(os.path.join(ayna, rel), "w", encoding="utf-8") as f:
            f.write(metin)
    ortam = dict(os.environ)
    # 🔴 Ayna YOLU her mutantta AYNI -> .pyc onbellegi mutasyonu YUTABILIR.
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    # 🔴 PYTHONPATH sizarsa CANLI tools/ yuklenir ve batarya TAUTOLOJIYE doner.
    ortam.pop("PYTHONPATH", None)
    r = subprocess.run([sys.executable, os.path.join(ayna, TEST),
                        "--tools", os.path.join(ayna, "tools")],
                       cwd=ayna, capture_output=True, text=True, env=ortam)
    cikti = r.stdout + r.stderr
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    kirmizi = int(m.group(2)) if m else None
    return r.returncode, iddia, kirmizi, cikti[-3000:]


def main():
    print("SILME KARANTINASI — CURUTME KOSUMU")
    print("hedefler: %s\n" % ", ".join(HEDEFLER))
    once = {y: sha(y) for y in DOKUNULMAZ}

    pristine = {}
    for _kod, _a, hedef, _d, _k in MUTANTLAR:
        if hedef in pristine:
            continue
        yol = os.path.join(ROOT, hedef)
        if not os.path.exists(yol):
            raise SystemExit("🔴 HARNESS BAYAT: hedef dosya YOK: %s" % hedef)
        with open(yol, encoding="utf-8") as f:
            pristine[hedef] = f.read()

    tmp = tempfile.mkdtemp(prefix="karantina-mutasyon-")
    try:
        ayna = ayna_kur(os.path.join(tmp, "ayna"))
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (canli kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, t_kirmizi, t_kuyruk = kos(ayna, dict(pristine))
        if not check("taban YESIL (cikis 0, kirmizi iddia 0)",
                     t_rc == 0 and t_kirmizi == 0,
                     "cikis=%s kirmizi=%s" % (t_rc, t_kirmizi)):
            print("\n  --- taban ciktisinin kuyrugu ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: mutant kosumlari ANLAMSIZ — durduruluyor.")
            return 1
        check("taban IDDIA SAYISI okunabildi", t_iddia is not None, "iddia=%s" % t_iddia)
        print("   taban iddia sayisi: %s" % t_iddia)

        # CANLILIK CAPASI: aynanin GERCEKTEN mutasyona duyarli oldugunu, canli modulun
        # sizmadigini KANITLA. Anlamsiz bir mutant (dosyayi bozan) kirmizi yakmali.
        print("\n1b) CANLILIK CAPASI (ayna canli modulu YUKLEMIYOR mu)")
        capa = dict(pristine)
        capa[KARANTINA] = pristine[KARANTINA].replace(
            'DAMGA_ADI = "d1-karantina-damgasi"',
            'DAMGA_ADI = "d1-karantina-damgasi"\nraise RuntimeError("CANLILIK CAPASI")', 1)
        c_rc, _c_iddia, _c_kirmizi, _c_kuyruk = kos(ayna, capa)
        check("aynadaki modul BOZULUNCA test DUSER (yani ayna yukleniyor, canli tools "
              "sizmiyor)", c_rc != 0, "cikis=%s" % c_rc)

        print("\n2) MUTANTLAR")
        oldu = 0
        for kod, aciklama, hedef, degisimler, kirmizi_bekleniyor in MUTANTLAR:
            metinler = dict(pristine)
            metinler[hedef] = mutasyonla(pristine[hedef], degisimler, kod)
            rc, iddia, kirmizi, kuyruk = kos(ayna, metinler)
            print("\n  %s [%s] %s" % (kod, os.path.basename(hedef), aciklama))
            ok_sayi = check("%s: iddia sayisi KORUNDU (cokme kirmizisi DEGIL)" % kod,
                            iddia == t_iddia, "taban=%s mutant=%s" % (t_iddia, iddia))
            if kirmizi_bekleniyor:
                ok = check("%s: mutant OLDU (cikis != 0 ve kirmizi iddia > 0)" % kod,
                           rc != 0 and (kirmizi or 0) > 0,
                           "cikis=%s kirmizi=%s" % (rc, kirmizi))
                if ok and ok_sayi:
                    oldu += 1
            else:
                ok = check("%s: KONTROL — mutant YESIL kaldi (gurultu yok)" % kod,
                           rc == 0 and kirmizi == 0,
                           "cikis=%s kirmizi=%s" % (rc, kirmizi))
            if not (ok and ok_sayi):
                print("  --- kuyruk ---\n%s" % kuyruk)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n3) CANLI KAYNAKLAR DEGISMEDI MI")
    for y in DOKUNULMAZ:
        check("sha256 ayni: %s" % os.path.relpath(y, ROOT), sha(y) == once[y])

    oldurucu = sum(1 for m in MUTANTLAR if m[4])
    kontrol = len(MUTANTLAR) - oldurucu
    print("\nOZET: %d oldurucu + %d kontrol mutanti · %d kusur"
          % (oldurucu, kontrol, len(FAILS)))
    print("MUTASYON=%d/%d KONTROL=%s"
          % (oldu, oldurucu, "KIRMIZI" if FAILS else "YESIL"))
    if FAILS:
        print("🔴 CURUTME KIRMIZI:")
        for f in FAILS:
            print("   - %s" % f)
        return 1
    print("✅ CURUTME YESIL: her oldurucu mutant KIRMIZI, kontrol mutantlari YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())

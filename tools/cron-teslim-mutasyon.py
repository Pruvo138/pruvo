#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/cron-nabiz-kapisi.py NABIZ EKSENLERININ CURUTME (mutasyon) araci.

NE OLCER: "kabul testi YESIL" demek "eksen CANLI" demek DEGILDIR. Bu arac eksenleri
BILEREK bozar ve `--kendini-test`in GERCEKTEN kirmizi yandigini SAYIYLA olcer.
Kapsam: A5 TESLIM · A0 TETIKLEYICI SARTI · A3/A5 ORTAK CAPA · KADANS KOLU KABLOSU.
Mutantlar IKI dosyaya uygulanabilir: `tools/cron-nabiz-kapisi.py` ve
`.github/workflows/deploy.yml` (kadans kolunun bloklamama sarti YALNIZ is akisi
dosyasindan olculebilir).

NEDEN VAR (olculen korluk, 4 Agu 2026)
======================================
`paket-tazelik-alarmi.yml` cron'u `13,28,43,58` — gunde 96 zamanlanmis kosum BEKLENIR.
FIILEN olculen: 2,42 gunde 10 kosum (%4,31); en uzun ardisik bosluk 1053,5 dk (17,6 sa).
`d1-uzlastirici.yml` (cron `9,24,39,54`) AYNI oranda dusuyor ve IKISI AYNI DAKIKALARDA,
PARTI HALINDE atesleniyor -> hal is akisina ozgu DEGIL, depo/hesap duzeyinde.
O gun nabiz kapisi rc=0 (YESIL) veriyordu: A1 cron METNINI olcer (teslimi degil), A3
YALNIZ SON kosumun yasina bakar (2,5 sa -> taze), A0/A4 damga yasina bakar (0,8/8,5 sa
-> esik 9 sa'in altinda). Yani "nobetci var ama KOR" sinifi. A5 o boslugu kapatir.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]): her mutant kosumunda IDDIA SAYISI taban
   kosumla AYNI olmali. Sayi dusuyorsa mutant testi COKERTMISTIR ve o kirmizi bir OLCUM
   DEGILDIR (cokme kirmiziyla karisir).

🔴 KONTROL MUTANTI SART ([[fikstur-degeri-mutasyon-koru]]): anlam tasimayan bir degisiklik
   bataryayi kirmizi yakmamali, yoksa "oldu" hukumlerinin hicbiri mutasyona atfedilemez.

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]]). Kosum basinda ve sonunda kaynak sha256 karsilastirilir.

🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/cron-teslim-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontrol YESIL kaldi + iddia sayilari korundu +
canli kaynaklar sha256 olarak DEGISMEDI.
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

KAPI = "tools/cron-nabiz-kapisi.py"
DEPLOY = os.path.join(".github", "workflows", "deploy.yml")
UZLASTIRICI = os.path.join(".github", "workflows", "d1-uzlastirici.yml")
# Mutasyona UGRAYABILEN her canli dosya burada: kosum basinda ve sonunda sha256
# karsilastirilir ([[mutasyon-diske-yazma-tuzagi]]).
HEDEFLER = (KAPI, DEPLOY, UZLASTIRICI)
DOKUNULMAZ = [os.path.join(ROOT, y) for y in HEDEFLER]

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
# MUTANTLAR — (kod, aciklama, HEDEF_DOSYA, [(bulunacak, yerine), ...], kirmizi_mi)
# ─────────────────────────────────────────────────────────────────────────────
M1 = ("M1", "🔴 TABAN KONTROLU NO-OP: `teslim < taban` -> `False` (A5 hicbir zaman "
            "alarm vermez; 4 Agu'daki hal aynen geri gelir)", KAPI,
      [("    if teslim < taban:\n", "    if False:\n")], True)

M2 = ("M2", "🔴 OLCULEMEDI -> YESIL: cozulemeyen zaman damgasi hata yerine SESSIZCE "
            "ATLANIYOR (teslim 8 -> 7, ikisi de tabanin ustunde: hal yesil kalir)", KAPI,
      [('                    damgalar.append(_iso(k["created_at"]))\n',
        '                    try:\n'
        '                        damgalar.append(_iso(k["created_at"]))\n'
        '                    except OlcumHatasi:\n'
        '                        continue\n')], True)

M3 = ("M3", "🔴 ESIK 'kirmizi gormeyeyim' DIYE DUSURULDU (guvenlik boleni 2 -> 8; "
            "15 dk cron tabani 4 -> 1)", KAPI,
      [("TESLIM_GUVENLIK_BOLENI = 2.0", "TESLIM_GUVENLIK_BOLENI = 8.0")], True)

M4 = ("M4", "🔴 ORTAK CAPA `yenileme_an`e cevrildi (A3 + A5 TEK KAYNAK): dosyaya her "
            "dokunus IKI ekseni birden susturur (olculdu: dokunma araligi medyan "
            "5,2-5,5 sa < N=9 sa -> eksenler fiilen OLU)", KAPI,
      [('    kayit_an = g.get("kayit_an")\n'
        '    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None\n',
        '    _capalar = [x for x in (g.get("kayit_an"), g.get("yenileme_an")) if x]\n'
        '    kayit_an = max(_capalar) if _capalar else None\n'
        '    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None\n')],
      True)

M5 = ("M5", "🔴 SIRALAMA API'YE BIRAKILDI: pencere kosumlari siralanmiyor -> EN UZUN "
            "BOSLUK (korluk penceresinin gercek degeri) yanlis hesaplanir", KAPI,
      [("    damgalar = sorted(x for x in (g.get(\"tum_kosumlar\") or []) "
        "if x > pencere_basi)",
        "    damgalar = [x for x in (g.get(\"tum_kosumlar\") or []) if x > pencere_basi]")],
      True)

M6 = ("M6", "🔴 EVET SUZGECI YALNIZ ILK KAYITTA: listenin gerisi korlemesine sayiliyor "
            "(yarim calisan `event=schedule` suzgeci sahte YESIL uretir)", KAPI,
      [("                    if k.get(\"event\") != \"schedule\":\n"
        "                        raise OlcumHatasi(\"%s: event=schedule istendi ama "
        "kayit event=%r \"\n",
        "                    if k.get(\"event\") != \"schedule\" and False:\n"
        "                        raise OlcumHatasi(\"%s: event=schedule istendi ama "
        "kayit event=%r \"\n")],
      True)

# ── 4 AGU 2026'DA OLDURULEMEYEN MUTANTLAR (bu turun sebebi) ─────────────────
M7 = ("M7", "🔴 A0 TETIKLEYICI SARTI NO-OP: damgayi yazan kosumun `event=schedule` "
            "kumesinde olup olmadigina BAKILMIYOR -> elle (`workflow_dispatch`) yazilan "
            "bir damga alarmi 9 saat susturur. 4 Agu 09:45:48Z'de FIILEN olan budur ve "
            "o gun bu mutant OLDURULEMIYORDU.", KAPI,
      [('        if kimlik in kaynak["kimlikler"]:\n            return kayit\n',
        '        if True:\n            return kayit\n')], True)

M8 = ("M8", "🔴 A3 CAPASI ESKI HALINE (max(kayit_an, yenileme_an)) DONDURULDU — YALNIZ "
            "A3 cagri yerinde: cron dosyasina her dokunus A3'u N=9 sa SUSTURUR (canli "
            "olcum 4 Agu 10:04Z: cron 9,8 saattir oluyken A3 satiri 🟡 idi)", KAPI,
      [('        yeni_tanim = (g["son_kosum"] is None or kayit_an > g["son_kosum"])\n',
        '        kayit_an = max(kayit_an, g["yenileme_an"] or kayit_an)\n'
        '        kayit_yasi = (simdi - kayit_an).total_seconds() / 3600.0\n'
        '        yeni_tanim = (g["son_kosum"] is None or kayit_an > g["son_kosum"])\n')],
      True)

M9 = ("M9", "🔴 KADANS KOLU YAYIN YOLUNA SIZDIRILDI: `d1-kadans` job'u `deploy: needs` "
            "listesine eklendi -> D1/ag'a bagimli bir kol TUM EKIBIN yayinini durdurur "
            "(bu depoda olculen kapi-birikimi zarari)", DEPLOY,
      [("    needs: [build, serit-a2, serit-a3]\n",
        "    needs: [build, serit-a2, serit-a3, d1-kadans]\n")], True)

M10 = ("M10", "🔴 ESZAMANLILIK KILIDI SILINDI: uzlastiran isin `concurrency` grubu "
              "kaldirildi -> cron kolu ile push kolu AYNI ANDA kosabilir (D1'e cift "
              "yazim penceresi acilir)", UZLASTIRICI,
       [("    concurrency:\n      group: d1-uzlastirici\n      cancel-in-progress: false\n",
         "")], True)

M12 = ("M12", "🔴 KILITLENME RISKI: cagiran job da AYNI eszamanlilik grubunu tutuyor "
              "(cagiran job grubu tutarken cagrilan is ayni grubu ister -> kosum "
              "kilitlenebilir); kilit TEK YERDE olmali", DEPLOY,
       [("  d1-kadans:\n    uses: ./.github/workflows/d1-uzlastirici.yml\n",
         "  d1-kadans:\n    concurrency:\n      group: d1-uzlastirici\n"
         "      cancel-in-progress: false\n"
         "    uses: ./.github/workflows/d1-uzlastirici.yml\n")], True)

M11 = ("M11", "🔴 CRON IKINCI KOLU SILINDI ('kadans yetiyor' varsayimi): push'suz gecede "
              "uzlastirma HIC kosmaz ve A0/A3 capasi da kaybolur", UZLASTIRICI,
       [('  schedule:\n    - cron: "9,24,39,54 * * * *"\n',
         "  # cron KALDIRILDI (mutant)\n")], True)

# ── KONTROL MUTANTLARI (YESIL kalmali) ──────────────────────────────────────
K1 = ("K1", "ilgisiz: A5 sabitinin yanina aciklama yorumu eklendi", KAPI,
      [("TESLIM_SAYFA = 100", "TESLIM_SAYFA = 100   # GitHub sayfa boyu")], False)

K2 = ("K2", "ilgisiz: deploy.yml'de kadans job'unun USTUNE yorum satiri eklendi "
            "(is akisi semantigi DEGISMEZ)", DEPLOY,
      [("  d1-kadans:\n    uses:", "  # kadans kolu — gerekce ustteki blokta\n"
                                   "  d1-kadans:\n    uses:")], False)

K3 = ("K3", "ilgisiz: olculen elle-kosum kimliginin yanina aciklama yorumu eklendi", KAPI,
      [("_CRON_DISI_KOSUM = 30897735170",
        "_CRON_DISI_KOSUM = 30897735170   # 4 Agu 09:45:48Z")], False)

MUTANTLAR = (M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12, K1, K2, K3)

IDDIA_RE = re.compile(r"^(\d+) iddia kosturuldu, (\d+) KIRMIZI\.$", re.M)


def ayna_kur(hedef):
    """tools/ + .github/workflows/ tam kopya. Symlink IZLENIR (fiziksel kopya)."""
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
    """Mutasyonu METNE uygular. Dayanak yoksa/coklu ise HARNESS BAYATTIR -> gurultulu
    duser; 'olctum' deyip hicbir sey olcmemek en kotu haldir."""
    metin = pristine
    for bul, yerine in degisimler:
        n = metin.count(bul)
        if n != 1:
            raise SystemExit(
                "🔴 HARNESS BAYAT (%s): dayanak metin %d kez bulundu (1 olmali).\n"
                "   Aranan: %r" % (kod, n, bul[:120]))
        metin = metin.replace(bul, yerine, 1)
    return metin


def kos(ayna, metinler):
    """Aynadaki kapiyi `--kendini-test` ile kostur -> (rc, iddia, kirmizi, kuyruk).

    `metinler` = {gorece_yol: icerik} — mutasyon KAPI'ya da is akisi dosyasina da
    uygulanabilir (kadans kolunun bloklamama sarti yalniz deploy.yml'den olculur)."""
    for rel, metin in metinler.items():
        with open(os.path.join(ayna, rel), "w", encoding="utf-8") as f:
            f.write(metin)
    r = subprocess.run([sys.executable, os.path.join(ayna, KAPI), "--kendini-test"],
                       cwd=ayna, capture_output=True, text=True)
    cikti = r.stdout + r.stderr
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    kirmizi = int(m.group(2)) if m else None
    return r.returncode, iddia, kirmizi, cikti[-2500:]


def main():
    print("NABIZ EKSENLERI — CURUTME (mutasyon) KOSUMU")
    print("hedefler: %s\n" % ", ".join(HEDEFLER))
    once = {y: sha(y) for y in DOKUNULMAZ}

    pristine = {}
    for kod, _a, hedef, _d, _k in MUTANTLAR:
        if hedef in pristine:
            continue
        yol = os.path.join(ROOT, hedef)
        if not os.path.exists(yol):
            raise SystemExit("🔴 HARNESS BAYAT (%s): hedef dosya YOK: %s" % (kod, hedef))
        with open(yol, encoding="utf-8") as f:
            pristine[hedef] = f.read()

    tmp = tempfile.mkdtemp(prefix="cron-teslim-mutasyon-")
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

        print("\n2) MUTANTLAR")
        for kod, aciklama, hedef, degisimler, kirmizi_bekleniyor in MUTANTLAR:
            metinler = dict(pristine)
            metinler[hedef] = mutasyonla(pristine[hedef], degisimler, kod)
            rc, iddia, kirmizi, kuyruk = kos(ayna, metinler)
            print("\n  %s [%s] %s" % (kod, hedef, aciklama))
            # 🔴 ISARET SARTI: iddia sayisi degismemeli. Dusmusse mutant testi COKERTMIS
            # demektir ve o kirmizi bir olcum degildir.
            ok_sayi = check("%s: iddia sayisi KORUNDU (cokme kirmizisi DEGIL)" % kod,
                            iddia == t_iddia, "taban=%s mutant=%s" % (t_iddia, iddia))
            if kirmizi_bekleniyor:
                ok = check("%s: mutant OLDU (cikis != 0 ve kirmizi iddia > 0)" % kod,
                           rc != 0 and (kirmizi or 0) > 0,
                           "cikis=%s kirmizi=%s" % (rc, kirmizi))
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
    if FAILS:
        print("🔴 CURUTME KIRMIZI:")
        for f in FAILS:
            print("   - %s" % f)
        return 1
    print("✅ CURUTME GECTI — her oldurucu mutant KIRMIZI yandi, kontrol mutantlari "
          "YESIL kaldi (A5 TESLIM · A0 TETIKLEYICI · A3/A5 ORTAK CAPA · KADANS KOLU).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

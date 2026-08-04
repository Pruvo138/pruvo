#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/cron-nabiz-kapisi.py — A5 TESLIM ekseni + PUSH SERIDI kablo capasinin
CURUTME (mutasyon) araci.

NE OLCER: "kabul testi YESIL" demek "eksen CANLI" demek DEGILDIR. Bu arac o eksenleri
BILEREK bozar ve `--kendini-test`in GERCEKTEN kirmizi yandigini SAYIYLA olcer.

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
DOKUNULMAZ = [os.path.join(ROOT, KAPI)]

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
# MUTANTLAR — (kod, aciklama, [(bulunacak, yerine), ...], kirmizi_beklenir_mi[, beyan])
#
# 🔴 BESINCI ALAN = BEYAN EDILEN KIRMIZI EKSEN KUMESI (4 Agu 2026'da eklendi).
#    Onceki hal yalnizca "kirmizi > 0" olcuyordu; o olcut bir mutantin BEKLENMEDIK bir
#    ekseni dusurmesini ve "oldurucu" sayilmasini engellemez ([[beyan-edilmis-survivor]]).
#    Beyan verilen mutantlarda kirmizi eksen kumesi BEYANA TAM ESIT olmalidir (gevsek
#    "kapsar" olcutu YOK). Beyan `None` ise yalnizca eski isaret sarti uygulanir.
#    Eksen kodu = `[FAIL]` satirinin ILK SOZCUGUDUR (A5/PS10/X4 ... gibi).
# ─────────────────────────────────────────────────────────────────────────────
M1 = ("M1", "🔴 TABAN KONTROLU NO-OP: `teslim < taban` -> `False` (A5 hicbir zaman "
            "alarm vermez; 4 Agu'daki hal aynen geri gelir)",
      [("    if teslim < taban:\n", "    if False:\n")], True, None)

M2 = ("M2", "🔴 OLCULEMEDI -> YESIL: cozulemeyen zaman damgasi hata yerine SESSIZCE "
            "ATLANIYOR (teslim 8 -> 7, ikisi de tabanin ustunde: hal yesil kalir)",
      [('                    damgalar.append(_iso(k["created_at"]))\n',
        '                    try:\n'
        '                        damgalar.append(_iso(k["created_at"]))\n'
        '                    except OlcumHatasi:\n'
        '                        continue\n')], True, None)

M3 = ("M3", "🔴 ESIK 'kirmizi gormeyeyim' DIYE DUSURULDU (guvenlik boleni 2 -> 8; "
            "15 dk cron tabani 4 -> 1)",
      [("TESLIM_GUVENLIK_BOLENI = 2.0", "TESLIM_GUVENLIK_BOLENI = 8.0")], True, None)

M4 = ("M4", "🔴 CAPA `yenileme_an`e cevrildi: dosyaya her dokunus A5'i 48 sa SUSTURUR "
            "(olculdu: dokunma araligi medyan 5,2 sa -> eksen fiilen OLU)",
      [('    kayit_an = g.get("kayit_an")\n'
        '    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None\n',
        '    _capalar = [x for x in (g.get("kayit_an"), g.get("yenileme_an")) if x]\n'
        '    kayit_an = max(_capalar) if _capalar else None\n'
        '    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None\n')],
      True, None)

M5 = ("M5", "🔴 SIRALAMA API'YE BIRAKILDI: pencere kosumlari siralanmiyor -> EN UZUN "
            "BOSLUK (korluk penceresinin gercek degeri) yanlis hesaplanir",
      [("    damgalar = sorted(x for x in (g.get(\"tum_kosumlar\") or []) "
        "if x > pencere_basi)",
        "    damgalar = [x for x in (g.get(\"tum_kosumlar\") or []) if x > pencere_basi]")],
      True, None)

M6 = ("M6", "🔴 EVET SUZGECI YALNIZ ILK KAYITTA: listenin gerisi korlemesine sayiliyor "
            "(yarim calisan `event=schedule` suzgeci sahte YESIL uretir)",
      [("                    if k.get(\"event\") != \"schedule\":\n"
        "                        raise OlcumHatasi(\"%s: event=schedule istendi ama "
        "kayit event=%r \"\n",
        "                    if k.get(\"event\") != \"schedule\" and False:\n"
        "                        raise OlcumHatasi(\"%s: event=schedule istendi ama "
        "kayit event=%r \"\n")],
      True, None)

# ── EN UZUN BOSLUGUN UC TERIMLERI (4 Agu 2026 kanit-kalitesi onarimi) ───────
# 🔴 NEDEN EKLENDI: "en uzun bosluk" UC ucu sayar (ic bosluklar · devam eden sessizlik ·
# pencere basi) ve kod bunlari satir satir gerekcelendiriyordu — ama TEK A5 fiksturunun
# maks boslugu bir IC bosluktu (2370 dk). Bagimsiz curutucu olctu: iki UC terimini silen
# mutantlar 124 iddia / 0 KIRMIZI ile SURVIVOR veriyordu; yani "1053,5 dk korluk
# penceresinin GERCEK degeridir" iddiasinin hesabi OLCULMEMISTI
# ([[fikstur-degeri-mutasyon-koru]]). Kapiya X4/X5 fiksturleri eklendi; bu iki mutant
# onlarin AYIRT EDICI oldugunu (TEK KIRMIZI) kanitlar.
X4 = ("X4", "🔴 DEVAM EDEN SESSIZLIK ucu SILINDI: son kosumdan SIMDIYE kadar gecen sure "
            "bosluk sayilmiyor -> 44 saattir HIC kosmayan bir is akisi 'en uzun bosluk "
            "60 dk' diye SAGLIKLI raporlanir",
      [("        bosluklar.append((simdi - damgalar[-1]).total_seconds() / 60.0)\n", "")],
      True, {"X4"})

X5 = ("X5", "🔴 PENCERE BASI ucu GIZLENDI: ilk kosumdan ONCEKI sessizlik bosluk "
            "sayilmiyor -> 'pencerenin 45 saati sessiz, son 3 saatte 4 kosum' (PARTI "
            "HALINDE teslim, 4 Agu'da OLCULEN hal) kucucuk bir bosluk gibi gorunur",
      [("        if not g.get(\"pencere_kirpildi\"):\n"
        "            bosluklar.append((damgalar[0] - pencere_basi).total_seconds() / 60.0)",
        "        if False:\n"
        "            bosluklar.append((damgalar[0] - pencere_basi).total_seconds() / 60.0)")],
      True, {"X5"})

# ── PUSH SERIDI KABLO CAPASI (4 Agu 2026) ───────────────────────────────────
# Bayatlik olcumu artik cron'a EK olarak push tetikli `odeme-bayatlik-push.yml`
# seridinde de kosuyor. O seridin "yayini durdurmaz + disaridan surulemez" ozelligi
# BEYAN DEGIL, KOSULAN bir kapidir (`push_serit_kablosu`).
#
# 🔴 ILK TURDA KUSURLU IDI (bagimsiz curutucu iadesi): kapi bir KARA LISTE tutuyordu
# ("pull_request", "workflow_call") ve `pull_request_target` ACIK KALMISTI — o tetigi
# tasiyan bir is akisi kapidan YESIL geciyordu. Kara liste TAMAMLANAMAZ
# ([[maskeleme-kismi-kapatma]]); kapi IZIN LISTESINE cevrildi. Asagidaki mutantlar izin
# listesini TEK TEK genisletir: her biri BIR fiksturu — ve YALNIZ onu — kirmizi yakar.
# Mutanti OLMAYAN bir yasak yine BEYAN'dir; bu yuzden her yasak tetigin bir satiri var.
def _izin(*ekler):
    return [('PUSH_SERIT_IZINLI_TETIK = ("push", "workflow_dispatch")',
             'PUSH_SERIT_IZINLI_TETIK = ("push", "workflow_dispatch", %s)'
             % ", ".join('"%s"' % e for e in ekler))]


X6 = ("X6", "🔴 IZIN LISTESI GENISLETILDI: `pull_request` mesru sayiliyor (fork PR'i "
            "seridi baslatir; olcum cadansini ve kuyruk yukunu disaridan surdurur)",
      _izin("pull_request"), True, {"PS10"})

X7 = ("X7", "🔴 BLOKE EDEN KUSURUN NOBETI: `pull_request_target` mesru sayiliyor — fork "
            "PR'ini TABAN DEPO baglaminda ve DEPO SECRET'leriyle kosturur, yani yabanci "
            "koda CLOUDFLARE_API_TOKEN acar (ilk turda kapi bu tetikte YESIL geciyordu)",
      _izin("pull_request_target"), True, {"PS17"})

X8 = ("X8", "🔴 `issue_comment` mesru sayiliyor (herkesin yazabildigi bir yorum taban "
            "depo baglaminda secret'li kosum baslatir)",
      _izin("issue_comment"), True, {"PS18"})

X9 = ("X9", "🔴 `workflow_run` mesru sayiliyor (serit deploy.yml'in TAMAMLANMASINA "
            "baglanir; nobetci olctugu hatta bagimli olur — Y4 sinifi)",
      _izin("workflow_run"), True, {"PS19"})

X10 = ("X10", "🔴 MEKANIZMA NOBETI: ENUMERE EDILMEMIS bir tetik (`repository_dispatch`) "
              "izin listesine giriyor -> izin listesinin fail-closed'ligi coker",
       _izin("repository_dispatch"), True, {"PS20"})

X11 = ("X11", "🔴 DAL CIVISI (GENIS desen kolu) NO-OP: `branches: ['**']` kabul edilir "
              "-> serit HER dala kosar, gurultu alarmi FIILEN susturur",
       [("        elif dal_listesi != [PUSH_SERIT_DAL]:\n", "        elif False:\n")],
       True, {"PS21"})

X12 = ("X12", "🔴 DAL CIVISI (TANIMSIZ kolu) NO-OP: `push.branches` hic tanimli "
              "olmadiginda (varsayilan = TUM dallar) ariza URETILMEZ",
       [("        if not dal_listesi:\n", "        if False:\n")], True, {"PS22"})

X13 = ("X13", "🔴 `workflow_call` mesru sayiliyor (is akislari arasi TEK bag yolu; serit "
              "deploy.yml'in `needs` grafinin ICINE girebilir)",
       _izin("workflow_call"), True, {"PS11"})

# ── KONTROL MUTANTI (YESIL kalmali) ─────────────────────────────────────────
K1 = ("K1", "ilgisiz: A5 sabitinin yanina aciklama yorumu eklendi",
      [("TESLIM_SAYFA = 100", "TESLIM_SAYFA = 100   # GitHub sayfa boyu")], False, set())

MUTANTLAR = (M1, M2, M3, M4, M5, M6, X4, X5,
             X6, X7, X8, X9, X10, X11, X12, X13, K1)

IDDIA_RE = re.compile(r"^(\d+) iddia kosturuldu, (\d+) KIRMIZI\.$", re.M)
# Kirmizi EKSEN kodu = `[FAIL]` satirinin ilk sozcugu (kapinin `iddia()` bicimi).
EKSEN_RE = re.compile(r"^  \[FAIL\] (\S+)", re.M)


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


def kos(ayna, kaynak_metni):
    """Aynadaki kapiyi `--kendini-test` ile kostur -> (rc, iddia, kirmizi, eksenler, kuyruk)."""
    yol = os.path.join(ayna, KAPI)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak_metni)
    r = subprocess.run([sys.executable, yol, "--kendini-test"],
                       cwd=ayna, capture_output=True, text=True)
    cikti = r.stdout + r.stderr
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    kirmizi = int(m.group(2)) if m else None
    return r.returncode, iddia, kirmizi, set(EKSEN_RE.findall(cikti)), cikti[-2500:]


def main():
    print("A5 TESLIM EKSENI + PUSH SERIDI KABLO CAPASI — CURUTME (mutasyon) KOSUMU")
    print("hedef: %s\n" % KAPI)
    once = {y: sha(y) for y in DOKUNULMAZ}

    with open(os.path.join(ROOT, KAPI), encoding="utf-8") as f:
        pristine = f.read()

    tmp = tempfile.mkdtemp(prefix="cron-teslim-mutasyon-")
    try:
        ayna = ayna_kur(os.path.join(tmp, "ayna"))
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (canli kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, t_kirmizi, _t_eksen, t_kuyruk = kos(ayna, pristine)
        if not check("taban YESIL (cikis 0, kirmizi iddia 0)",
                     t_rc == 0 and t_kirmizi == 0,
                     "cikis=%s kirmizi=%s" % (t_rc, t_kirmizi)):
            print("\n  --- taban ciktisinin kuyrugu ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: mutant kosumlari ANLAMSIZ — durduruluyor.")
            return 1
        check("taban IDDIA SAYISI okunabildi", t_iddia is not None, "iddia=%s" % t_iddia)
        print("   taban iddia sayisi: %s" % t_iddia)

        print("\n2) MUTANTLAR")
        for kod, aciklama, degisimler, kirmizi_bekleniyor, beyan in MUTANTLAR:
            metin = mutasyonla(pristine, degisimler, kod)
            rc, iddia, kirmizi, eksenler, kuyruk = kos(ayna, metin)
            print("\n  %s %s" % (kod, aciklama))
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
            # 🔴 BEYAN SARTI: kirmizi EKSEN kumesi beyana TAM ESIT olmali. Fazladan
            # kirmizi da kusurdur — "oldurucu" hukmu o zaman baska bir eksene aittir.
            ok_beyan = True
            if beyan is not None:
                ok_beyan = check(
                    "%s: kirmizi EKSEN kumesi beyana TAM ESIT (%s)"
                    % (kod, sorted(beyan) or "BOS"),
                    eksenler == beyan,
                    "olculen=%s beyan=%s" % (sorted(eksenler) or "-", sorted(beyan) or "-"))
            print("     olculen kirmizi eksen: %s" % (sorted(eksenler) or "-"))
            if not (ok and ok_sayi and ok_beyan):
                print("  --- kuyruk ---\n%s" % kuyruk)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n3) CANLI KAYNAKLAR DEGISMEDI MI")
    for y in DOKUNULMAZ:
        check("sha256 ayni: %s" % os.path.relpath(y, ROOT), sha(y) == once[y])

    oldurucu = sum(1 for m in MUTANTLAR if m[3])
    kontrol = len(MUTANTLAR) - oldurucu
    print("\nOZET: %d oldurucu + %d kontrol mutanti · %d kusur"
          % (oldurucu, kontrol, len(FAILS)))
    if FAILS:
        print("🔴 CURUTME KIRMIZI:")
        for f in FAILS:
            print("   - %s" % f)
        return 1
    print("✅ CURUTME GECTI — olculen eksenler her oldurucu mutanti KIRMIZI yakiyor, "
          "beyanli mutantlarin kirmizi kumesi beyana TAM ESIT, kontrol mutanti YESIL "
          "kaliyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

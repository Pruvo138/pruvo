#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — pre-push YEDEK BLOGU (tools/yedek-hook-kur.py).

NEDEN VAR — bu blogun iki oldurucu bozulma bicimi var, ikisi de SESSIZ:
  (A) FAIL-CLOSED'a kaymak: yedek patlar/Drive yoktur, blok exit!=0 doner ve PUSH DURUR.
      Yayini durduran bir yedek kabul edilemez (D1 senkron blogunun emsali de fail-open).
  (B) OLU KONUM: blok, D1 blogunun `exit 0`'larindan SONRAYA kayarsa cogu push'ta HIC
      CALISMAZ — hook "kurulu" gorunur, yedek yine alinmaz (tam da 26 Tem'de yasanan
      "arac dogru, kimse kosmuyor" hatasinin otomasyon kilikli hali).
Ikisinin de kaniti asagida; (A) icin Drive'i ERISILEMEZ yapan gercek bir mutasyonla.

🔴 BOLUM 6-7 — TETIK NOBETI (31 Tem): kancaya bagli her arac icin "cagriliyor mu" sorusu
    METINLE degil ICRAYLA olculur. Bolum 6 BOS bir git deposunda kancayi GERCEK kurulum
    yoluyla kurar, GERCEK bir `git push` kosar ve aracin yerine konan NOBETCININ iz
    birakip birakmadigina bakar; Bolum 7 kanca KALDIRILINCA ayni izin URETILMEDIGINI
    olcer (tek yonlu nobetci = olu nobetci). `--mutasyon` kancadan cagri metnini KOPYADA
    silip Bolum 6-7'nin KIRMIZI yandigini kanitlar (canli dosyaya mutant BIRAKILMAZ).

🔴 BOLUM 3-4 — K308 (27 Agu): "uyari basildi" iddiasi BOS BEYANDIR. Yedek cagrisi
    `>/dev/null 2>&1` ile susturuldugu surece rc!=0'in SEBEBI hicbir yere dusmez ve
    kullanici sonucu gosteren bir panoya yonlendirilir. Bolum 3 artik SEBEBIN push
    ciktisina ULASTIGINI olcer (uyari DISINDA anlamli satir + o satirin ARACIN kendi
    tani metni oldugu atfi) ve push'un YINE GECTIGINI ayrica dogrular; Bolum 4 basarili
    yedekte ciktinin SESSIZ kaldigini olcer. `--mutasyon`un (c) mutanti yutma desenini
    geri getirir ve Bolum 3'un KIRMIZI yandigini, (k) kontrol mutanti ise ayni bolumun
    YESIL kaldigini kanitlar.

🔴 BOLUM 5c — AYRISMA NOBETI: kurucunun `BLOK` sablonu ile izlenen
    `tools/kancalar/pre-push` blogu BIREBIR ayni mi. Olculen olay: `db0e16e2` (9 Agu)
    kurucudaki gercek cagriyi `$(true)` yapmis, izlenen kanca dogru kalmisti — iki
    kopya sessizce ayristi ve kurucuyu kosan makinede hijyen araci HIC KOSMAZDI.

Kosum:  python3 tools/yedek-hook-test.py
        python3 tools/yedek-hook-test.py --yalniz-tetik
        python3 tools/yedek-hook-test.py --yalniz-yedek-tani
        python3 tools/yedek-hook-test.py --mutasyon
"""
import argparse
import fcntl
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from git_ortami import sentetik_git
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
KUR = os.path.join(TOOLS, "yedek-hook-kur.py")
YEDEKLE = os.path.join(TOOLS, "yedekle.py")


def _yedek_kok_adi():
    """Yedek kok klasorunun adi — TEK KAYNAK `yedekle.py::YEDEK_KOK_ADI`.

    🔴 NEDEN TURETILIYOR (27 Agu 2026, olculdu): burada kok adi DIZE LITERALI olarak
    yaziliydi. `86e7a035` (14 Agu) gercek degeri `backup-v2` yapti ama bu dosyayi
    kapsamadi (o commit'in kendi menzili yedekle.py + durum.py idi) ->
    "damga yazildi (yedek gercekten kosdu)" iddiasi 13 gundur var OLMAYAN bir yola
    bakiyor ve KIRMIZI yaniyordu. Sayi kopyalanirsa kaynagindan ayrisir; FAIL-LOUD:
    sabit okunamazsa varsayilan UYDURULMAZ.
    """
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import yedekle as _y
    return _y.YEDEK_KOK_ADI

# Drive'i ERISILEMEZ yapan mutasyon: yedekle.py'nin cozucusu daima None doner.
DRIVE_STUB = ('DESEN = "/olmayan-mount/*/STL"\n'
              'def stl_dizini(sessiz=False):\n    return None\n'
              'def pruvo_dizini(sessiz=False):\n    return None\n')

# Kancanin cagirdigi ARACIN yerine konan nobetci: cagrilirsa iz birakir + ANLAMLI satir
# basar (kancanin "gorunur cikti" iddiasi da boylece ICRAYLA olculur).
KUTU_NOBETCI = (
    "#!/usr/bin/env python3\n"
    "import os, sys\n"
    "kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
    "open(os.path.join(kok, 'IZ-KUTU-ARSIVLE'), 'a').write('ates\\n')\n"
    "print('KUTU  : sahte')\n"
    "print('YAZILDI: 7 blok / 91 satir arsive tasindi')\n"
    "sys.exit(0)\n")

# Mutasyon capasi: kancadaki ICRA metni. Silinirse kanca kurulu KALIR ama arac KOSMAZ —
# tam da bu testin yakalamasi gereken sessiz hata.
CAGRI_METNI = 'python3 "$pruvo_kok/tools/kutu-arsivle.py" 2>&1'

SONUC = []


def kontrol(ad, ok, ayrinti=""):
    SONUC.append((ad, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + ad + (("  — " + ayrinti) if ayrinti else ""))
    return bool(ok)


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sahte_repo(td, drive_erisilebilir):
    """Gecici git deposu: tools/yedekle.py gercek, drive_yolu STUB."""
    kok = os.path.join(td, "repo")
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(YEDEKLE, os.path.join(kok, "tools", "yedekle.py"))
    govde = DRIVE_STUB
    if drive_erisilebilir:
        hedef = os.path.join(td, "drive", "Pruvo")
        os.makedirs(hedef)
        govde = ('DESEN = "/olmayan-mount/*/STL"\n'
                 'def stl_dizini(sessiz=False):\n    return %r\n'
                 'def pruvo_dizini(sessiz=False):\n    return %r\n'
                 % (os.path.join(hedef, "STL"), hedef))
    with open(os.path.join(kok, "tools", "drive_yolu.py"), "w") as f:
        f.write(govde)
    sentetik_git(kok, "init", "-q", capture_output=True)
    return kok


def hook_kos(kok, hook_metni):
    """Hook'u sahte repo icinde, pre-push stdin bicimiyle kosar."""
    yol = os.path.join(kok, "pre-push")
    with open(yol, "w") as f:
        f.write(hook_metni)
    os.chmod(yol, 0o755)
    return subprocess.run(
        ["sh", yol, "origin", "git@example.invalid:yok/yok.git"],
        input="refs/heads/dal aaa refs/heads/dal bbb\n",
        capture_output=True, text=True, cwd=kok)


def kanca_kum_havuzu(td, kur_yolu):
    """BOS bir git deposu + bare uzak + kutu-arsivle NOBETCISI. (kok, uzak) doner.

    Depo BOS (tools/ disinda dosya yok) -> kancanin yedek kolu dosya bulamayip atlar;
    olculen sey YALNIZ kutu-arsivle cagrisidir."""
    kok = os.path.join(td, "depo")
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy2(kur_yolu, os.path.join(kok, "tools", "yedek-hook-kur.py"))
    shutil.copy2(os.path.join(TOOLS, "git_ortami.py"),
                 os.path.join(kok, "tools", "git_ortami.py"))
    # Kurulum araci artik kurdugunun FIILEN etkin oldugunu kanca nobetcisiyle
    # dogruluyor (kur -> DOGRULA halkasi) -> nobetci + ortak icra suzgeci kum
    # havuzunda da BULUNMALI; yoksa dogrulama fail-closed "OLCULEMEDI" verir ve
    # bu testte olculen sey kurulum degil eksik fikstur olurdu.
    for _ad in ("kanca-nobeti.py", "icra-suzgeci.py"):
        _kaynak = os.path.join(TOOLS, _ad)
        if os.path.isfile(_kaynak):
            shutil.copy2(_kaynak, os.path.join(kok, "tools", _ad))
    with open(os.path.join(kok, "tools", "kutu-arsivle.py"), "w") as f:
        f.write(KUTU_NOBETCI)
    sentetik_git(kok, "init", "-q", "-b", "main", check=True,
                  capture_output=True, kimlik_ad="t", kimlik_eposta="t@t")
    uzak = os.path.join(td, "uzak.git")
    sentetik_git(td, "init", "-q", "--bare", uzak, check=True, capture_output=True)
    sentetik_git(kok, "remote", "add", "origin", uzak, check=True)
    return kok, uzak


def kum_kur(kok, *bayraklar):
    return subprocess.run(
        [sys.executable, os.path.join(kok, "tools", "yedek-hook-kur.py")] + list(bayraklar),
        capture_output=True, text=True, cwd=kok)


def kum_commit_push(kok, ad):
    """GERCEK commit + GERCEK push (kancayi taklit etmeden ATESLER)."""
    with open(os.path.join(kok, ad), "w") as f:
        f.write(ad + "\n")
    subprocess.run(["git", "-C", kok, "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", kok, "commit", "-q", "-m", ad], check=True,
                   capture_output=True)
    return subprocess.run(["git", "-C", kok, "push", "origin", "main"],
                          capture_output=True, text=True)


def bolum_tetik(kur_yolu):
    """6) BOS depoda GERCEK push araci ATESLIYOR mu · 7) kanca yokken ATESLEMIYOR mu."""
    print("\n6) TETIK — bos depoda kanca kurulur, GERCEK push araci ATESLER")
    with tempfile.TemporaryDirectory() as td:
        kok, _uzak = kanca_kum_havuzu(td, kur_yolu)
        iz = os.path.join(kok, "IZ-KUTU-ARSIVLE")
        kontrol("6a taze depoda kanca YOK (testin ONCULU)",
                not os.path.isfile(os.path.join(kok, ".git", "hooks", "pre-push")))
        k = kum_kur(kok)
        kontrol("6b kurulum rc=0", k.returncode == 0,
                (k.stdout + k.stderr).strip()[-70:])
        kanca = os.path.join(kok, ".git", "hooks", "pre-push")
        kontrol("6c pre-push kuruldu + CALISTIRILABILIR",
                os.path.isfile(kanca) and os.access(kanca, os.X_OK))
        r = kum_commit_push(kok, "a.txt")
        kontrol("6d push GECTI (fail-open: kanca push'u DURDURMAZ)", r.returncode == 0,
                "rc=%d %s" % (r.returncode, (r.stderr or "").strip()[-90:]))
        kontrol("6e 🔴 ARAC GERCEKTEN ATESLEDI (nobetci iz birakti)", os.path.isfile(iz))
        kontrol("6f aracin ANLAMLI ciktisi push'ta GORUNUR",
                "YAZILDI:" in (r.stdout + r.stderr))
        kontrol("6g ANLAMSIZ satirlar SUZULDU (her push'a gurultu basilmaz)",
                "KUTU  : sahte" not in (r.stdout + r.stderr))

    print("\n7) NEGATIF KONTROL — kanca KALDIRILINCA arac ATESLEMEZ")
    with tempfile.TemporaryDirectory() as td:
        kok, _uzak = kanca_kum_havuzu(td, kur_yolu)
        kum_kur(kok)
        r1 = kum_commit_push(kok, "a.txt")
        iz = os.path.join(kok, "IZ-KUTU-ARSIVLE")
        kontrol("7a on kosul: kanca KURULUYKEN iz VAR", os.path.isfile(iz),
                "rc=%d" % r1.returncode)
        if os.path.isfile(iz):
            os.unlink(iz)
        s = kum_kur(kok, "--kaldir")
        kontrol("7b --kaldir rc=0", s.returncode == 0, (s.stdout + s.stderr).strip()[-60:])
        r2 = kum_commit_push(kok, "b.txt")
        kontrol("7c push YINE GECTI", r2.returncode == 0, "rc=%d" % r2.returncode)
        kontrol("7d 🔴 kanca YOKKEN iz URETILMEDI (nobetci tek yonlu/olu degil)",
                not os.path.isfile(iz))


def bolum_yedek_tani(kur_yolu):
    """3-4) K308 — YEDEK basarisizliginin SEBEBI push ciktisinda GORUNUYOR mu?

    🔴 OLCULEN OLAY (27 Agu 2026, mimarin kendi push'u): kanca birebir
        `!! YEDEK alinamadi (push DEVAM ediyor) — kontrol: python3 tools/durum.py`
    bastı ve SEBEP hicbir yere dusmedi — cunku cagri `>/dev/null 2>&1` ile
    susturulmustu. Kullanici `durum.py`ye yonlendiriliyor, pano ise SONUCU
    (YARIM KALMIS YEDEK) gosteriyor, SEBEBI degil. "Uyari basildi" iddiasi bu yuzden
    YETMEZ: uyarinin ARKASINDA tani var mi diye SORULUR.

    IKI YON birlikte olculur ve ikisi de bloklayicidir:
      (3) yedek PATLADIGINDA -> sebep GORUNUR **ve** push YINE GECER (fail-open bozulmadi)
      (4) yedek BASARILIYKEN -> cikti SESSIZ (her push'a gurultu basilmaz)
    """
    kur = modul_yukle(kur_yolu, "yedek_hook_kur_tani")
    blok_hook = "#!/bin/sh\n" + kur.BLOK + "\n"

    print("\n3) K308 — Drive erisilemez: SEBEP gorunur mu, push yine gecer mi?")
    with tempfile.TemporaryDirectory() as td:
        kok = sahte_repo(td, drive_erisilebilir=False)
        r = hook_kos(kok, blok_hook)
        cikti = (r.stdout or "") + (r.stderr or "")
        kontrol("3a Drive yokken hook exit 0 (PUSH DURMAZ — fail-open DEGISMEDI)",
                r.returncode == 0, "rc=%d %s" % (r.returncode, r.stderr.strip()[:100]))
        kontrol("3b basarisizlik SESSIZ degil (uyari basildi)",
                "YEDEK alinamadi" in cikti, cikti.strip()[:90])
        kontrol("3c uyari rc'yi ADIYLA tasiyor (bos beyan degil)",
                "rc=" in cikti.split("YEDEK alinamadi")[1][:60]
                if "YEDEK alinamadi" in cikti else False,
                cikti.strip()[:120])

        # Mutasyonun ISIRDIGINI ve SEBEP METNINI ayni anda olc: ayni yedekle.py
        # dogrudan cagrilinca hem patlar hem kendi tanisini basar.
        d = subprocess.run([sys.executable, os.path.join(kok, "tools", "yedekle.py"),
                            "--gerekliyse"], capture_output=True, text=True, cwd=kok)
        kontrol("3d MUTASYON ISIRIYOR: yedekle.py tek basina exit!=0 veriyor",
                d.returncode != 0, "rc=%d" % d.returncode)
        tani_satirlari = [s.strip() for s in ((d.stdout or "") + (d.stderr or "")
                                              ).splitlines() if s.strip()]
        # 🔴 ASIL IDDIA: aracin KENDI tani satirlarindan EN AZ BIRI push ciktisinda.
        # "Uyari var" degil, "SEBEP ULASTI" olculur.
        ulasan = [s for s in tani_satirlari if s and s in cikti]
        # 3e — ANA IDDIA (deterministik): uyari satirinin DISINDA en az bir anlamli
        # satir push ciktisina dustu. Yutma deseni geri gelirse bu SIFIRA duser.
        ek_satir = [s.strip() for s in cikti.splitlines()
                    if s.strip() and "YEDEK alinamadi" not in s]
        kontrol("3e 🔴 SEBEP PUSH CIKTISINA ULASTI (uyari DISINDA anlamli satir var)",
                bool(ek_satir), "ek_satir=%d | ornek: %s"
                % (len(ek_satir), (ek_satir[0][:70] if ek_satir else "-")))
        # 3f — ATIF: o satir gercekten ARACIN kendi tanisi mi (baska bir gurultu degil).
        kontrol("3f o satir yedekle.py'nin KENDI tani metni (hedef-kol atfi)",
                bool(ulasan),
                "tani_satiri=%d ulasan=%d | ornek: %s"
                % (len(tani_satirlari), len(ulasan),
                   (tani_satirlari[-1][:70] if tani_satirlari else "-")))

    print("\n4) KONTROL — Drive erisilebilirken cikti SESSIZ olmali")
    with tempfile.TemporaryDirectory() as td:
        kok = sahte_repo(td, drive_erisilebilir=True)
        r = hook_kos(kok, blok_hook)
        cikti = (r.stdout or "") + (r.stderr or "")
        kontrol("4a hook exit 0", r.returncode == 0, "rc=%d" % r.returncode)
        kontrol("4b uyari YOK (yedek basarili)", "YEDEK alinamadi" not in cikti,
                cikti.strip()[:90])
        kontrol("4c tani kuyrugu da BASILMADI (basarida gurultu yok)",
                "!! YEDEK" not in cikti, cikti.strip()[:90])
        damga = os.path.join(td, "drive", "Pruvo", _yedek_kok_adi(), ".son-yedek.json")
        kontrol("4d damga yazildi (yedek gercekten kosdu)", os.path.isfile(damga),
                "kok=%s" % _yedek_kok_adi())


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# K308 mutasyon capasi: SEBEBI gorunur kilan kol. Yutma desenine geri donulunce
# rc korunur (uyari yine basilir) ama TANI KUYRUGU BOSALIR -> Bolum 3 KIRMIZI yanmali.
# Capa TEK SATIRDIR ve kacis dizisi TASIMAZ (bayat capa riskini dusurur).
YEDEK_YAKALAMA = ('pruvo_yedek_cikti=$(python3 "$pruvo_kok/tools/yedekle.py" '
                  '--gerekliyse 2>&1)')
YEDEK_YUTMA = ('pruvo_yedek_cikti=$(python3 "$pruvo_kok/tools/yedekle.py" '
               '--gerekliyse >/dev/null 2>&1)')


def mutasyon_turu():
    """CIFT YONLU: her mutant KOPYAYA uygulanir, HEDEF BOLUMU kosar, canli dosya DEGISMEZ.

    Her satirda `mod` alani var — mutantin hangi bolumu oldurdugu ACIKCA yazilir.
    Bir mutant "genel suite kirmizi oldu" diye degil, HEDEF KOLUNUN bolumu kirmizi
    yandigi icin oldurulmus sayilir ([[K182]] hedef-kol atfi).
    """
    canli_once = sha(KUR)
    with open(KUR, encoding="utf-8") as f:
        kaynak = f.read()
    eksik = []
    if kaynak.count(CAGRI_METNI) != 1:
        eksik.append("%r -> %d kez" % (CAGRI_METNI, kaynak.count(CAGRI_METNI)))
    if kaynak.count(YEDEK_YAKALAMA) != 1:
        eksik.append("%r -> %d kez" % (YEDEK_YAKALAMA, kaynak.count(YEDEK_YAKALAMA)))
    if eksik:
        print("❌ MUTASYON CAPASI KAYIP (1 bekleniyordu): " + " | ".join(eksik))
        return 1

    mutantlar = [
        ("a", "--yalniz-tetik", "KANCA CAGRI METNI SILINDI (kutu-arsivle.py hic kosmuyor)",
         kaynak.replace(CAGRI_METNI, "true"), "KIRMIZI"),
        ("c", "--yalniz-yedek-tani",
         "🔴 K308 YUTMA DESENI GERI GETIRILDI (>/dev/null 2>&1) — sebep bosalir",
         kaynak.replace(YEDEK_YAKALAMA, YEDEK_YUTMA), "KIRMIZI"),
        ("b", "--yalniz-tetik", "ILGISIZ degisiklik (yorum satirina bosluk)",
         kaynak.replace("# IDEMPOTENT + UCUZ:", "#  IDEMPOTENT + UCUZ:"), "YESIL"),
        ("k", "--yalniz-yedek-tani",
         "KONTROL: ILGISIZ degisiklik — yedek tani bolumu YESIL KALMALI",
         kaynak.replace("# IDEMPOTENT + UCUZ:", "#  IDEMPOTENT + UCUZ:"), "YESIL"),
    ]
    sonuc = []
    with tempfile.TemporaryDirectory() as td:
        for kod, mod, ad, govde, beklenen in mutantlar:
            print("\n" + "-" * 78)
            print("MUTANT %s) [%s] %s" % (kod, mod, ad))
            if govde == kaynak:
                print("❌ mutant kaynagi DEGISTIRMEDI (capa bayat)")
                sonuc.append(False)
                continue
            kopya = os.path.join(td, "mutant-%s.py" % kod)
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(govde)
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__), mod, "--kur", kopya],
                capture_output=True, text=True)
            gorulen = "KIRMIZI" if r.returncode != 0 else "YESIL"
            ok = gorulen == beklenen
            sonuc.append(ok)
            print("  -> %s (beklenen %s)  rc=%d" % (gorulen, beklenen, r.returncode))
            for satir in r.stdout.splitlines():
                if satir.strip().startswith("❌"):
                    print("     " + satir.strip()[:120])

    canli_sonra = sha(KUR)
    print("\n" + "=" * 78)
    print("canli tools/yedek-hook-kur.py sha256 (ONCE) : %s" % canli_once)
    print("canli tools/yedek-hook-kur.py sha256 (SONRA): %s" % canli_sonra)
    if canli_once != canli_sonra:
        print("❌ CANLI ARAC DEGISTI (mutant sizdi!)")
        return 1
    print("✅ canli arac sha256 ESIT — mutant sizmadi")
    kirmizi = sonuc.count(False)
    print("MUTASYON: %d/%d beklendigi gibi" % (len(sonuc) - kirmizi, len(sonuc)))
    return 1 if kirmizi else 0


def main():
    ap = argparse.ArgumentParser(description="pre-push kanca blogu kabul testi")
    ap.add_argument("--kur", default=KUR, help="test edilecek kurulum betigi (mutant icin)")
    ap.add_argument("--yalniz-tetik", action="store_true",
                    help="yalniz Bolum 6-7 (tetik nobeti) kosulur")
    ap.add_argument("--yalniz-yedek-tani", action="store_true",
                    help="yalniz Bolum 3-4 (K308: sebep gorunur mu + kontrol) kosulur")
    ap.add_argument("--mutasyon", action="store_true",
                    help="cift yonlu mutasyon turu (KOPYA uzerinde)")
    a = ap.parse_args()

    if a.mutasyon:
        return mutasyon_turu()

    if a.yalniz_tetik or a.yalniz_yedek_tani:
        if a.yalniz_tetik:
            bolum_tetik(a.kur)
        if a.yalniz_yedek_tani:
            bolum_yedek_tani(a.kur)
        kirmizi = [ad for ad, ok in SONUC if not ok]
        print("\n" + "=" * 70)
        print("TOPLAM %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
        for ad in kirmizi:
            print("  ❌ " + ad)
        print("SONUC: " + ("KIRMIZI ❌" if kirmizi else "YESIL ✅"))
        return 1 if kirmizi else 0

    kur = modul_yukle(a.kur, "yedek_hook_kur")
    blok_hook = "#!/bin/sh\n" + kur.BLOK + "\n"

    # ---------------- 1) URETILEN BLOK: idempotens ----------------
    print("\n1) IDEMPOTENS — iki kez kurmak ikinci kopya YIGMAMALI")
    bir, _ = kur.yeni_icerik(None)
    iki, eylem = kur.yeni_icerik(bir)
    kontrol("ikinci kurulum metni DEGISTIRMEDI", bir == iki, eylem)
    kontrol("blok tek kez geciyor", bir.count(kur.BAS) == 1)
    mevcut = "#!/bin/sh\n# D1 blogu\nexit 0\n"
    eklendi, _ = kur.yeni_icerik(mevcut)
    kontrol("mevcut hook'un govdesi KORUNDU", "# D1 blogu" in eklendi)
    kaldirildi, _ = kur.yeni_icerik(eklendi, kaldir=True)
    kontrol("--kaldir blogu cikarir, govde kalir",
            kur.BAS not in kaldirildi and "# D1 blogu" in kaldirildi)

    # ---------------- 2) KONUM — 'exit 0'lardan ONCE ----------------
    print("\n2) OLU KONUM NOBETI — blok erken 'exit 0'lardan ONCE olmali")
    kontrol("uretilen blok ilk 'exit 0'dan once",
            eklendi.index(kur.BAS) < eklendi.index("exit 0"))
    gercek = None
    p = subprocess.run(["git", "-C", TOOLS, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode == 0 and p.stdout.strip():
        yol = os.path.join(p.stdout.strip(), "hooks", "pre-push")
        if os.path.isfile(yol):
            with open(yol, errors="replace") as f:
                gercek = f.read()
    if gercek is None:
        kontrol("bu makinede pre-push kurulu", False, "hook yok — 'python3 tools/yedek-hook-kur.py' kos")
    else:
        kontrol("bu makinede blok KURULU", kur.BAS in gercek)
        if kur.BAS in gercek and "exit 0" in gercek:
            kontrol("kurulu blok ilk 'exit 0'dan ONCE (olu konum degil)",
                    gercek.index(kur.BAS) < gercek.index("exit 0"))
        kontrol("mevcut D1 blogu KORUNMUS", "d1-sync" in gercek)

    # ---------------- 3-4) K308: SEBEP GORUNUR MU + KONTROL ----------------
    bolum_yedek_tani(a.kur)

    # ---------------- 5b) KILIT DOLUYKEN PUSH YOLU (fail-open) ----------------
    # 26 Tem: yedekle.py artik flock aliyor. Kilit baska bir kosumdaysa bu kosum
    # ATLAR — ama push'u ASLA bloklamamali ve "yedek alinamadi" diye HATA da
    # basmamali (atlama bir hata degil; isi zaten oteki kosum yapiyor).
    print("\n5b) KILIT DOLU — push yolu YINE exit 0, hata gurultusu YOK")
    with tempfile.TemporaryDirectory() as td:
        kok = sahte_repo(td, drive_erisilebilir=True)
        kilit = open(os.path.join(kok, ".yedek.lock"), "a+")
        fcntl.flock(kilit, fcntl.LOCK_EX)
        kilit.write("pid=999999 baslangic=%.3f iso=TEST\n" % time.time())
        kilit.flush()
        r = hook_kos(kok, blok_hook)
        kontrol("kilit doluyken hook exit 0 (PUSH DURMAZ)", r.returncode == 0,
                "rc=%d %s" % (r.returncode, r.stderr.strip()[:100]))
        kontrol("hata uyarisi BASILMADI (atlama hata degil)",
                "YEDEK alinamadi" not in r.stdout, r.stdout.strip()[:90])
        # Atlama HATA DEGILDIR: hook rc=0 gorur, hicbir sey basmaz. Atlamanin
        # gerceklestigini bu yuzden dogrudan betikten dogruluyoruz (K308 sonrasi da
        # boyle: tani kuyrugu YALNIZ rc!=0'da basilir).
        d = subprocess.run([sys.executable, os.path.join(kok, "tools", "yedekle.py"),
                            "--gerekliyse"], capture_output=True, text=True, cwd=kok)
        kontrol("ayni kosum tek basina da ATLIYOR + exit 0",
                d.returncode == 0 and "yedek ATLANDI" in d.stdout,
                "rc=%d %s" % (d.returncode, d.stdout.strip().splitlines()[0][:70]
                              if d.stdout.strip() else ""))
        kontrol("ATLANAN kosum hedefe yedek YAZMADI", "bitti ->" not in d.stdout)
        fcntl.flock(kilit, fcntl.LOCK_UN)
        kilit.close()
        # kilit birakilinca ayni hook normal calisir (regresyon)
        r2 = hook_kos(kok, blok_hook)
        kontrol("kilit birakilinca hook yine exit 0 + yedek alindi",
                r2.returncode == 0 and os.path.isfile(
                    os.path.join(td, "drive", "Pruvo", _yedek_kok_adi(),
                                 ".son-yedek.json")),
                "rc=%d kok=%s" % (r2.returncode, _yedek_kok_adi()))

    # ---------------- 5) BLOK ICINDE 'exit' OLMAMALI ----------------
    print("\n5) YAPISAL — blok push'u kesecek 'exit' ICERMEMELI")
    govde = [s.strip() for s in kur.BLOK.splitlines()
             if s.strip() and not s.strip().startswith("#")]
    kontrol("blokta 'exit' yok", not any(s.startswith("exit") or " exit " in s for s in govde))
    # 🔴 K308: eski iddia "cagri hata YUTUCU ile sarili" idi — yani YUTMAYI SART
    # kosuyordu. Fail-open'in sarti yutmak DEGIL, `exit` etmemektir. Yutma sartı
    # kalkti; yerine "hicbir arac cagrisi ciktisini /dev/null'a atmiyor" iddiasi geldi.
    kontrol("YEDEK cagrisi ciktisini YUTMUYOR (>/dev/null 2>&1 yok)",
            not any("yedekle.py" in s and "/dev/null" in s for s in govde),
            next((s for s in govde if "yedekle.py" in s), "-"))
    kontrol("YEDEK cagrisinin rc'si degiskene ALINIYOR (sebep basilabilsin)",
            any("pruvo_yedek_rc=" in s for s in govde))
    kontrol("HICBIR arac cagrisi /dev/null'a yazmiyor (sinif kapisi)",
            not any("/dev/null 2>&1" in s and "rev-parse" not in s for s in govde),
            next((s for s in govde if "/dev/null 2>&1" in s and "rev-parse" not in s),
                 "-"))

    # ---------------- 5c) K308/K316: KURUCU ile IZLENEN KANCA AYRISMASIN ----------
    # 🔴 OLCULEN OLAY: `db0e16e2` (9 Agu) kurucunun BLOK sablonunda gercek cagriyi
    # `$(true)` yapmis; izlenen `tools/kancalar/pre-push` gercek cagriyi tasimaya
    # devam etmisti. Iki kopya sessizce ayristi -> kurucuyu kosan makinede kanca
    # hijyensiz kurulur ve BU HIC GORUNMEZ. Ayrisma artik OLCULUR.
    print("\n5c) AYRISMA NOBETI — kurucunun BLOK'u ile izlenen kancanin blogu AYNI mi")
    izlenen = os.path.join(os.path.dirname(TOOLS), "tools", "kancalar", "pre-push")
    if not os.path.isfile(izlenen):
        kontrol("izlenen kanca dosyasi bulundu", False, izlenen)
    else:
        with open(izlenen, encoding="utf-8", errors="replace") as f:
            metin = f.read()
        var = kur.BAS in metin and kur.SON in metin
        kontrol("izlenen kancada YEDEK BLOGU isaretleri var", var)
        if var:
            b = metin.index(kur.BAS)
            s = metin.index(kur.SON) + len(kur.SON)
            kontrol("🔴 kurucu BLOK'u ile izlenen kanca blogu BIREBIR AYNI",
                    metin[b:s] == kur.BLOK,
                    "kurucu=%d bayt, izlenen=%d bayt" % (len(kur.BLOK), s - b))

    # ---------------- 5d) YEDEK KOK ADI TEK KAYNAKTAN ---------------------------
    # 🔴 `86e7a035` (14 Agu) kok adini sabite tasidi, degeri `backup-v2` yapti — ama
    # menzili yalniz yedekle.py + durum.py idi; BU AILE kapsam disinda kaldi ve 13 gun
    # var olmayan bir yola bakti. Literal geri gelirse ayni sessiz ayrisma geri gelir.
    print("\n5d) TEK KAYNAK NOBETI — yedek kok adi LITERAL olarak yaziliyor mu")
    kok_adi = _yedek_kok_adi()
    kontrol("yedekle.py::YEDEK_KOK_ADI okunabildi (fail-loud)", bool(kok_adi), kok_adi)
    for dosya in (KUR, os.path.abspath(__file__)):
        with open(dosya, encoding="utf-8", errors="replace") as f:
            govde_metni = f.read()
        # Yol birlesiminde kullanilan dize literali aranir; yorum satirlari ve
        # NOBETCININ KENDI deseni kapsam disi (aksi halde kapi KENDINI yakalar —
        # 27 Agu'da bir kez oldu, kirmizinin sebebi arizanin kendisi degil olcu
        # aletinin kendi metniydi).
        igne = '"' + "back" + 'up"'
        igne2 = "'" + "back" + "up'"
        kotu = [s.strip() for s in govde_metni.splitlines()
                if not s.strip().startswith("#")
                and "TEK-KAYNAK-NOBETI-ISTISNA" not in s
                and (igne in s or igne2 in s)]
        kontrol("%s icinde kok adi DIZE LITERALI yok (tek kaynak: YEDEK_KOK_ADI)"
                % os.path.basename(dosya), not kotu, (kotu[0][:90] if kotu else ""))

    # ---------------- 6-7) TETIK NOBETI (bkz. modul basligi) ----------------
    bolum_tetik(a.kur)

    kirmizi = [a for a, ok in SONUC if not ok]
    print("\n" + "=" * 70)
    print("TOPLAM %d kontrol, %d kirmizi" % (len(SONUC), len(kirmizi)))
    for a in kirmizi:
        print("  ❌ " + a)
    print("SONUC: " + ("KIRMIZI ❌" if kirmizi else "YESIL ✅"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())

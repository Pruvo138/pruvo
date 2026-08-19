#!/usr/bin/env python3
"""merge-kanit.py — merge icin kabul kanit tablosu (BaBa hukmu 18 Agu).

Iki kol:
  --kaydet  : bir merge icin kanit satiri YAZAR. kabul komutunu KENDI kosturur;
              RC ve SON_SATIR elle girilemez (beyan degil olcum).
  --dogrula : dal icin kanit satiri var mi ve RC=0 mi.

Kanit dosyasi repo DISI: ~/.claude/cron/merge-kanit.tsv (public repoya GIRMEZ).
Override: MERGE_KANIT_DOSYASI env var.

Kabul:
  python3 /Users/okan/dev/pruvo/tools/merge-kanit.py --kendini-test
  SON SATIR + rc=0:
    VAKA=8 DUSEN=0 MUTANT=6/6 KONTROL=2/2

Not (K173): shell=True ile FileNotFoundError erisilemez (kabuk 127 doner). Bu
yuzden M3 yeniden yazildi: "komut yok → yazilan rc 127, asla 0 degil" — canli
kolda spesifik deger korunur. M4 (YENI) genel non-zero sozlesmesini nobetler:
"aracin sifir-disi rc'yi 0 diye yazmamali". Ikisi farkli iddia yerlerinden
duser (bkz. dalin kanonik muhendis raporu).

Tuzak iliskisi: [[merge-kanit-tablosu-yok]] · [[commit-mesaji-iddiasi-olcum-degildir]]
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Kanit dosyasinin KALICI yeri (repo DISI; uygunsuz repoya giris yok).
# Override yalniz test/dev icin (env var).
KANIT_DOSYASI = Path(
    os.environ.get(
        "MERGE_KANIT_DOSYASI",
        str(Path.home() / ".claude" / "cron" / "merge-kanit.tsv"),
    )
)

# ⏰ ISO-8601 UTC; tarih CLI bayragi vermeyene otomatik.
# Satir SOZLESMESI (sutun sirasi):
#   TARIH \t DAL \t MERGE_SHA \t MERGE_BASE \t KABUL_KOMUTU \t RC \t SON_SATIR \t MIMAR
ALANLAR = ("TARIH", "DAL", "MERGE_SHA", "MERGE_BASE", "KABUL_KOMUTU", "RC", "SON_SATIR", "MIMAR")
AYIRA = "\t"
YENI_SATIR = "\n"


def kostur_kanit(komut):
    """Kabul komutunu KENDI kosturur; (rc, son_satir) doner.

    rc=None ise kosum ANLAMLI yapilamadi (timeout/genel hata); bu durumda
    SON_SATIR hata iletisini tasir, RC OLCULEMEDI yazilir.
    """
    # Not (K173): shell=True ile subprocess.run /bin/sh uzerinden kosar; bu
    # yuzden FileNotFoundError YALNIZ /bin/sh yoksa olusur (sistem cabuk
    # kullanilamaz halinde). Olu kolu kaldirildi; canli yolda shell "command
    # not found" icin rc=127, timeout/genel hata icin rc=None doner. M3 ve M4
    # canli yolda olculur.
    try:
        islem = subprocess.run(
            komut,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired as e:
        return None, f"zamanaşimi: {e}"
    except Exception as e:
        return None, f"hata: {e}"

    tum = (islem.stdout or "") + (islem.stderr or "")
    son = tum.strip().splitlines()
    son_satir = son[-1] if son else ""
    return islem.returncode, son_satir


def kaydet(tarih, dal, merge_sha, merge_base, kabul_komutu, mimar):
    """Kanit satiri yaz. RC ve SON_SATIR kabul komutunun KENDI kosumundan gelir.

    Bu kol --rc/--son-satir bayragi kabul ETMEZ (argparse'ta yok); beyan yolu
    acilamaz. (M1 — kapi dogrudan ifade).
    """
    rc, son_satir = kostur_kanit(kabul_komutu)

    if rc is None:
        rc_str = "OLCULEMEDI"
        son_satir_str = son_satir  # zaten hata iletisi
    else:
        rc_str = str(rc)
        son_satir_str = son_satir

    KANIT_DOSYASI.parent.mkdir(parents=True, exist_ok=True)
    satir = AYIRA.join([tarih, dal, merge_sha, merge_base, kabul_komutu, rc_str, son_satir_str, mimar])
    with open(KANIT_DOSYASI, "a") as f:
        f.write(satir + YENI_SATIR)

    print(f"yazildi: DAL={dal} RC={rc_str}")
    # kabuk kabulunun kendi rc'si 0 degilse cikisi BOZMA (bu kanit zamanlayici):
    # asil kabul kapisi merge-kapisi tarafinda zaten duruyor; --kaydet yalniz
    # olcum yapar.
    return 0


def dogrula(dal):
    """Dal icin kanit satiri var mi ve RC=0 mi.

    Bos kanit dosyasi / dal bulunamadi / RC != 0 -> OLCULEMEDI + rc=1.
    K2: kanit dosyasi YOKSA arac COKMEZ (exist kontrolu); yine OLCULEMEDI + rc=1.
    """
    if not KANIT_DOSYASI.exists():
        print(f"OLCULEMEDI: kanit dosyasi yok ({KANIT_DOSYASI})")
        return 1

    bulunan = []
    with open(KANIT_DOSYASI) as f:
        for satir in f:
            parcalar = satir.rstrip(YENI_SATIR).split(AYIRA)
            if len(parcalar) >= len(ALANLAR) and parcalar[1] == dal:
                bulunan.append(parcalar)

    if not bulunan:
        print(f"OLCULEMEDI: {dal} icin kanit yok")
        return 1

    # Son kayit baz alinir (birden fazla kosum olabilir; son gecerli).
    son = bulunan[-1]
    rc = son[5]
    if rc == "0":
        print(f"YESIL: {dal} merge kanitli (RC=0, SON_SATIR={son[6]!r})")
        return 0
    else:
        print(f"KIRMIZI: {dal} merge kanitli ama RC={rc} (SON_SATIR={son[6]!r})")
        return 1


# --------------------------- EKSİKLER ---------------------------

def _git_komut(komut_listesi, cwd=None):
    """Yardimci: git komutunu kos, (rc, stdout, stderr) doner."""
    try:
        islem = subprocess.run(
            komut_listesi,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as e:
        return 1, "", str(e)
    return islem.returncode, islem.stdout, islem.stderr


def eksikler(sinir=None):
    """Main'e alinmis ama kaniti olmayan birlesimleri listele.

    * Kanit dosyasi okunamazsa OLCULEMEDI + rc != 0.
    * Geriye donuk satir URETILMEZ; yalnizca sayar/listeler.
    * Pencere baslangici: --sinir veya kanit dosyasindaki en eski tarih.
    """
    if not KANIT_DOSYASI.exists():
        print(f"OLCULEMEDI: kanit dosyasi yok ({KANIT_DOSYASI})")
        return 1

    # Kanit dosyasindan tarihler ve merge SHA'larini oku
    kanit_sha_set = set()
    tarihler = []
    try:
        with open(KANIT_DOSYASI) as f:
            for satir in f:
                parcalar = satir.rstrip(YENI_SATIR).split(AYIRA)
                if len(parcalar) >= len(ALANLAR):
                    kanit_sha_set.add(parcalar[2])
                    tarihler.append(parcalar[0])
    except Exception as e:
        print(f"OLCULEMEDI: kanit dosyasi okunamadi ({e})")
        return 1

    if sinir is None:
        if not tarihler:
            print("OLCULEMEDI: kanit dosyasinda tarih yok, --sinir verin")
            return 1
        sinir = min(tarihler)

    # Git worktree kokunu bul (bu betigin yasadigi agac)
    kok = Path(__file__).resolve().parent.parent

    # Hangi daldan merge'leri cekecegiz? once main, yoksa origin/main
    hedef_dal = None
    for aday in ("main", "origin/main"):
        rc, out, _ = _git_komut(["git", "-C", str(kok), "rev-parse", "--verify", aday])
        if rc == 0 and out.strip():
            hedef_dal = aday
            break
    if hedef_dal is None:
        print("OLCULEMEDI: main / origin/main referansi bulunamadi")
        return 1

    # Merge commit'leri cek
    rc, out, err = _git_komut([
        "git", "-C", str(kok), "log", "--merges",
        f"--since={sinir}", "--format=%H%x09%s", hedef_dal,
    ])
    if rc != 0:
        print(f"OLCULEMEDI: git log --merges basarisiz ({err.strip()})")
        return 1

    birlesimler = {}
    for line in out.strip().splitlines():
        if AYIRA in line:
            sha, baslik = line.split(AYIRA, 1)
            birlesimler[sha] = baslik

    birlesim_sha_set = set(birlesimler.keys())
    kanitsiz_sha_set = birlesim_sha_set - kanit_sha_set
    kanitli_sha_set = birlesim_sha_set & kanit_sha_set

    for sha in sorted(kanitsiz_sha_set):
        baslik = birlesimler.get(sha, "")
        print(f"KANITSIZ: {sha} {baslik}")

    # HEAD kisaltmasi
    rc, head_out, _ = _git_komut(["git", "-C", str(kok), "rev-parse", "--short", "HEAD"])
    head_kisa = head_out.strip() if rc == 0 else "HEAD"
    pencere = f"{sinir}..{head_kisa}"

    toplam = len(birlesim_sha_set)
    kanitli = len(kanitli_sha_set)
    kanitsiz = len(kanitsiz_sha_set)

    print(f"MERGE_KANIT BIRLESIM={toplam} KANITLI={kanitli} KANITSIZ={kanitsiz} PENCERE={pencere}")
    return 0


# --------------------------- KENDINI-TEST ---------------------------

def _kendini_test_alet(script_yolu):
    """6 mutant + 2 kontrolu kara-kutu kosar; sayar.

    VAKA = tum senaryo (mutant + kontrol). DUSEN = senaryo basarisiz.
    MUTANT = mutantlarin YAKALANAN kismi (sistem hatayi geri cevirdi).
    KONTROL = kontrollerin GECTIGI kismi (sistem olculen durumu dogru isledi).
    """
    import shutil
    import uuid

    vaka = 0
    dusen = 0
    mutant = 0
    kontrol = 0

    # Gecici kanit dosyasi (bos basla; K2 sifir-dosya durumunu kosar).
    gecici = Path(tempfile.gettempdir()) / f"merge-kanit-test-{uuid.uuid4().hex}.tsv"
    if gecici.exists():
        gecici.unlink()
    cevre = os.environ.copy()
    cevre["MERGE_KANIT_DOSYASI"] = str(gecici)

    def _kos(*dizi):
        return subprocess.run(
            ["python3", str(script_yolu), *dizi],
            capture_output=True,
            text=True,
            env=cevre,
        )

    def _kur_sentetik_repo(repo_yolu, dallar):
        """Gecici git deposu kur: main + verilen dallar --no-ff merge edilmis.

        KANONIK sentetik git (fikstur-git-sizinti-kapisi sozlesmesi, 19 Agu
        2026): dogrudan subprocess kurulumu miras GIT_* kesif baglamini
        temizlemiyordu; sentetik_git scrub + cwd sabitlemeyi tek yoldan verir.
        """
        from git_ortami import sentetik_git

        def _g(*args):
            return sentetik_git(str(repo_yolu), *args, kimlik_ad="Test",
                                kimlik_eposta="test@pruvo.local",
                                check=True, capture_output=True)

        repo_yolu.mkdir(parents=True, exist_ok=True)
        _g("init")
        _g("config", "user.email", "test@pruvo.local")
        _g("config", "user.name", "Test")
        (repo_yolu / "kok").write_text("kok")
        _g("add", "kok")
        _g("commit", "-m", "kok")
        for dal in dallar:
            _g("checkout", "-b", dal)
            (repo_yolu / f"{dal}.txt").write_text(dal)
            _g("add", f"{dal}.txt")
            _g("commit", "-m", f"{dal} commit")
            _g("checkout", "main")
            _g("merge", "--no-ff", dal, "-m", f"merge {dal}")

    def _sil_repo(repo_yolu):
        shutil.rmtree(repo_yolu, ignore_errors=True)

    try:
        # === KONTROL K2: kanit dosyasi yoksa --dogrula COKMEZ, OLCULEMEDI+rc != 0 ===
        vaka += 1
        r = _kos("--dogrula", "k2-dal")
        if r.returncode != 0 and "OLCULEMEDI" in r.stdout:
            kontrol += 1
        else:
            dusen += 1
            sys.stderr.write(f"K2 FAIL: rc={r.returncode} stdout={r.stdout!r}\n")

        # === MUTANT M1: --kaydet elle RC/SON_SATIR kabul etmemeli ===
        # --rc ve --son-satir bayraklari argparse'ta YOK; bilinmeyen bayrak
        # rc=2 (argparse) verir. MUTANT YAKALANMIS sayilir.
        vaka += 1
        r = _kos(
            "--kaydet",
            "--tarih", "2026-08-18T00:00Z",
            "--dal", "m1-dal",
            "--merge-sha", "sha",
            "--merge-base", "base",
            "--kabul-komutu", "echo OK",
            "--rc", "0",                # elle giris — kabul edilmemeli
            "--son-satir", "manipule",  # elle giris — kabul edilmemeli
            "--mimar", "KraL",
        )
        if r.returncode != 0:
            mutant += 1
        else:
            dusen += 1
            sys.stderr.write(f"M1 FAIL: elle RC kabul edildi (rc=0)\n")

        # === MUTANT M2: --dogrula kanit yokken rc=0 dondurmamali ===
        vaka += 1
        r = _kos("--dogrula", "m2-dal-yok")
        if r.returncode != 0:
            mutant += 1
        else:
            dusen += 1
            sys.stderr.write(f"M2 FAIL: kanit yokken rc=0 dondu\n")

        # === MUTANT M3 (K173 yeniden): kabul komutu YOK → yazilan rc 127, ASLA 0 degil ===
        # Bu, canli koldaki spesifik savunma: shell=True iken "komut yok" → rc=127.
        # Genel non-zero sozlesmesi M4'te (asil nobetci).
        vaka += 1
        r = _kos(
            "--kaydet",
            "--tarih", "2026-08-18T00:00Z",
            "--dal", "m3-dal",
            "--merge-sha", "sha",
            "--merge-base", "base",
            "--kabul-komutu", "this_command_does_not_exist_pruvo_xyz123",
            "--mimar", "KraL",
        )
        dosya_icerik = ""
        if gecici.exists():
            dosya_icerik = gecici.read_text()
        m3_satir = None
        if "m3-dal" in dosya_icerik:
            for line in dosya_icerik.split(YENI_SATIR):
                parcalar = line.split(AYIRA)
                if len(parcalar) >= 6 and parcalar[1] == "m3-dal":
                    m3_satir = parcalar
                    break
        if m3_satir is None:
            dusen += 1
            sys.stderr.write(f"M3 FAIL: m3-dal satiri eslesmedi (kanit yazilmadi)\n")
        elif m3_satir[5] == "127":
            mutant += 1  # IDDIA_M3_RC127: spesifik deger korundu
        elif m3_satir[5] != "0":
            dusen += 1
            sys.stderr.write(f"M3 FAIL: komut yok iken beklenen 127, got {m3_satir[5]!r} (M4 kapisi gecti ama M3 ozelinde 127 sart)\n")
        else:
            dusen += 1
            sys.stderr.write(f"M3 FAIL: komut yok iken rc=0 yazildi (sozlesme bozuk)\n")

        # === MUTANT M4 (K173 YENI): sifir-disi rc ASLA 0 yazilmamali (genel nobetci) ===
        # Bu, "RC uydurulamaz" sozlesmesinin ASIL koruyucusu. Komut 42 ile cikar;
        # M4 mutantlari (kaydet'te rc_str="0" gibi) bu senaryoda kirmizi yakalanir.
        vaka += 1
        r = _kos(
            "--kaydet",
            "--tarih", "2026-08-18T00:00Z",
            "--dal", "m4-dal",
            "--merge-sha", "sha",
            "--merge-base", "base",
            "--kabul-komutu", "exit 42",
            "--mimar", "KraL",
        )
        dosya_icerik = ""
        if gecici.exists():
            dosya_icerik = gecici.read_text()
        m4_satir = None
        if "m4-dal" in dosya_icerik:
            for line in dosya_icerik.split(YENI_SATIR):
                parcalar = line.split(AYIRA)
                if len(parcalar) >= 6 and parcalar[1] == "m4-dal":
                    m4_satir = parcalar
                    break
        if m4_satir is None:
            dusen += 1
            sys.stderr.write(f"M4 FAIL: m4-dal satiri eslesmedi (kanit yazilmadi)\n")
        elif m4_satir[5] == "42":
            mutant += 1  # IDDIA_M4_RC42: genel non-zero deger korundu
        elif m4_satir[5] != "0":
            dusen += 1
            sys.stderr.write(f"M4 FAIL: beklenen 42, got {m4_satir[5]!r}\n")
        else:
            dusen += 1
            sys.stderr.write(f"M4 FAIL: non-zero rc=42 iken 0 yazildi (asil nobetci gecti)\n")

        # === MUTANT M5: --eksikler kanitsiz birlesimi KANITLI saymasin ===
        # Hedef kol: --eksikler KANITSIZ ekseni gercekten olcmeli.
        # Sentetik depoda 2 merge var; kanit dosyasina 1'i yazildi.
        # Dogru davranis: BIRLESIM=2 KANITLI=1 KANITSIZ=1.
        # Mutant (kanitsizi kanitli sayarsa) KANITSIZ=0 verir; bu senaryo onu yakar.
        vaka += 1
        repo_m5 = Path(tempfile.gettempdir()) / f"merge-kanit-repo-m5-{uuid.uuid4().hex}"
        kanit_m5 = Path(tempfile.gettempdir()) / f"merge-kanit-m5-{uuid.uuid4().hex}.tsv"
        try:
            _kur_sentetik_repo(repo_m5, ["m5-f1", "m5-f2"])
            rc_git, out_git, _ = _git_komut(["git", "-C", str(repo_m5), "log", "--merges", "--format=%H", "main"])
            merge_sha_list = out_git.strip().splitlines()
            if len(merge_sha_list) != 2:
                dusen += 1
                sys.stderr.write(f"M5 FAIL: sentetik depoda 2 merge bekleniyordu, {len(merge_sha_list)} var\n")
            else:
                # [1] eski merge -> kanitli, [0] yeni merge -> kanitsiz
                eski_sha = merge_sha_list[1]
                tarih_str = "2026-08-18T00:00Z"
                kanit_satir = AYIRA.join([tarih_str, "m5-dal", eski_sha, "base", "echo OK", "0", "OK", "KraL"])
                kanit_m5.write_text(kanit_satir + YENI_SATIR)
                sentetik_script = repo_m5 / "tools" / "merge-kanit.py"
                sentetik_script.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(script_yolu), str(sentetik_script))
                cevre_m5 = os.environ.copy()
                cevre_m5["MERGE_KANIT_DOSYASI"] = str(kanit_m5)
                r = subprocess.run(
                    ["python3", str(sentetik_script), "--eksikler"],
                    capture_output=True,
                    text=True,
                    env=cevre_m5,
                )
                if r.returncode == 0 and "KANITLI=1" in r.stdout and "KANITSIZ=1" in r.stdout and "BIRLESIM=2" in r.stdout:
                    mutant += 1
                else:
                    dusen += 1
                    sys.stderr.write(f"M5 FAIL: rc={r.returncode} stdout={r.stdout!r}\n")
        finally:
            _sil_repo(repo_m5)
            if kanit_m5.exists():
                kanit_m5.unlink()

        # === MUTANT M6: kanit dosyasi okunamayinca KANITSIZ=0 yazmasin (sessiz sifir) ===
        # Hedef kol: --eksikler OLCULEMEDI ekseni gercekten olcmeli.
        # Kanit dosyasi YOK; dogru davranis: OLCULEMEDI + rc != 0.
        # Mutant (KANITSIZ=0 yazarsa) rc=0 verir; bu senaryo onu yakar.
        vaka += 1
        repo_m6 = Path(tempfile.gettempdir()) / f"merge-kanit-repo-m6-{uuid.uuid4().hex}"
        kanit_m6 = Path(tempfile.gettempdir()) / f"merge-kanit-m6-{uuid.uuid4().hex}.tsv"
        try:
            _kur_sentetik_repo(repo_m6, ["m6-f1"])
            sentetik_script = repo_m6 / "tools" / "merge-kanit.py"
            sentetik_script.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(script_yolu), str(sentetik_script))
            cevre_m6 = os.environ.copy()
            cevre_m6["MERGE_KANIT_DOSYASI"] = str(kanit_m6)
            if kanit_m6.exists():
                kanit_m6.unlink()
            r = subprocess.run(
                ["python3", str(sentetik_script), "--eksikler"],
                capture_output=True,
                text=True,
                env=cevre_m6,
            )
            if r.returncode != 0 and "OLCULEMEDI" in r.stdout:
                mutant += 1
            else:
                dusen += 1
                sys.stderr.write(f"M6 FAIL: rc={r.returncode} stdout={r.stdout!r}\n")
        finally:
            _sil_repo(repo_m6)
            if kanit_m6.exists():
                kanit_m6.unlink()

        # === KONTROL K1: gercek rc=0 uretmis bir kabul icin --dogrula YESIL ===
        vaka += 1
        # onceki mutant kirleri karistirmasin diye sifirla
        if gecici.exists():
            gecici.unlink()
        r = _kos(
            "--kaydet",
            "--tarih", "2026-08-18T00:00Z",
            "--dal", "k1-dal",
            "--merge-sha", "sha",
            "--merge-base", "base",
            "--kabul-komutu", "echo OK",
            "--mimar", "KraL",
        )
        r2 = _kos("--dogrula", "k1-dal")
        if r2.returncode == 0 and "YESIL" in r2.stdout:
            kontrol += 1
        else:
            dusen += 1
            sys.stderr.write(f"K1 FAIL: rc={r2.returncode} stdout={r2.stdout!r}\n")

    finally:
        if gecici.exists():
            try:
                gecici.unlink()
            except OSError:
                pass

    print(f"VAKA={vaka} DUSEN={dusen} MUTANT={mutant}/6 KONTROL={kontrol}/2")
    if dusen > 0:
        sys.exit(1)
    return 0


# --------------------------- CLI ---------------------------

def main():
    p = argparse.ArgumentParser(
        prog="merge-kanit.py",
        description="Merge kabul kanit tablosu (BaBa hukmu, 18 Agu 2026).",
    )
    grup = p.add_mutually_exclusive_group(required=True)
    grup.add_argument("--kaydet", action="store_true", help="Kanit satiri yaz (RC ve SON_SATIR aracin kendi kosumundan gelir).")
    grup.add_argument("--dogrula", metavar="DAL", help="Dal icin kanit dogrula (yesilse rc=0).")
    grup.add_argument("--kendini-test", action="store_true", help="6 mutant + 2 kontrol kosar.")
    grup.add_argument("--eksikler", action="store_true", help="Main'e alinmis ama kaniti olmayan birlesimleri listele.")

    # --kaydet argumanlari. --rc / --son-satir BILINCLI YOK (M1 tuzagi).
    p.add_argument("--tarih", help="ISO-8601 UTC (bos birakirsan simdi).")
    p.add_argument("--dal", help="Branch adi.")
    p.add_argument("--merge-sha", help="Merge commit SHA.")
    p.add_argument("--merge-base", help="Merge base SHA.")
    p.add_argument("--kabul-komutu", help="Kabulun kosulacak kabuk komutu.")
    p.add_argument("--mimar", help="Mimar adi (KraL gibi).")
    p.add_argument("--sinir", help="ISO-8601 UTC; kanit penceresinin baslangici (varsayilan: kanit dosyasindaki en eski satir).")
    args = p.parse_args()

    if args.kendini_test:
        sys.exit(_kendini_test_alet(Path(__file__).resolve()))
    elif args.eksikler:
        sys.exit(eksikler(args.sinir))
    elif args.kaydet:
        zorunlu = ("tarih", "dal", "merge_sha", "merge_base", "kabul_komutu", "mimar")
        eksik = [getattr(args, k) for k in zorunlu if not getattr(args, k)]
        if eksik:
            sys.stderr.write(f"HATA: --kaydet icin --tarih --dal --merge-sha --merge-base --kabul-komutu --mimar zorunlu\n")
            sys.exit(2)
        sys.exit(kaydet(args.tarih, args.dal, args.merge_sha, args.merge_base, args.kabul_komutu, args.mimar))
    elif args.dogrula:
        sys.exit(dogrula(args.dogrula))


if __name__ == "__main__":
    main()

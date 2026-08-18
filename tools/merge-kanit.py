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
    VAKA=<n> DUSEN=0 MUTANT=3/3 KONTROL=2/2

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

    rc=None ise kosum ANLAMLI yapilamadi (FileNotFoundError/timeout/genel hata);
    bu durumda SON_SATIR hata iletisini tasir, RC OLCULEMEDI yazilir.
    """
    try:
        islem = subprocess.run(
            komut,
            shell=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError as e:
        return None, f"shell bulunamadi: {e}"
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


# --------------------------- KENDINI-TEST ---------------------------

def _kendini_test_alet(script_yolu):
    """3 mutant + 2 kontrolu kara-kutu kosar; sayar.

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

        # === MUTANT M3: kabul komutu calismazsa RC=0 yazilmamali ===
        # Komut 127 ile cikar (shell "command not found"); rc != 0.
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
        if "m3-dal" in dosya_icerik:
            for line in dosya_icerik.split(YENI_SATIR):
                parcalar = line.split(AYIRA)
                if len(parcalar) >= 6 and parcalar[1] == "m3-dal":
                    if parcalar[5] != "0":
                        mutant += 1
                    else:
                        dusen += 1
                        sys.stderr.write(f"M3 FAIL: komut calismadi ama RC=0 yazildi\n")
                    break
            else:
                dusen += 1
                sys.stderr.write(f"M3 FAIL: m3-dal satiri eslesmedi\n")
        else:
            dusen += 1
            sys.stderr.write(f"M3 FAIL: kanit dosyasi yazilmadi\n")

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

    print(f"VAKA={vaka} DUSEN={dusen} MUTANT={mutant}/3 KONTROL={kontrol}/2")
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
    grup.add_argument("--kendini-test", action="store_true", help="3 mutant + 2 kontrol kosar.")

    # --kaydet argumanlari. --rc / --son-satir BILINCLI YOK (M1 tuzagi).
    p.add_argument("--tarih", help="ISO-8601 UTC (bos birakirsan simdi).")
    p.add_argument("--dal", help="Branch adi.")
    p.add_argument("--merge-sha", help="Merge commit SHA.")
    p.add_argument("--merge-base", help="Merge base SHA.")
    p.add_argument("--kabul-komutu", help="Kabulun kosulacak kabuk komutu.")
    p.add_argument("--mimar", help="Mimar adi (KraL gibi).")
    args = p.parse_args()

    if args.kendini_test:
        sys.exit(_kendini_test_alet(Path(__file__).resolve()))
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

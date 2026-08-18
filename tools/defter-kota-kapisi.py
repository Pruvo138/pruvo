#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-kota-kapisi.py — DEVAM.md defter kota kapisi (IK EKSEN, K178).

Kullanim:
    python3 tools/defter-kota-kapisi.py [depo-koku]
    python3 tools/defter-kota-kapisi.py --kendini-test

Davranis (IK EKSEN, pre-commit; K178):
    * DEVAM.md INDEX'te (staged) yoksa: sessizce exit 0 (kapsam disi).
    * DEVAM.md INDEX'te varsa ve (satir > 130 VEYA bayt > 12288) ise:
        - stderr'e iki satirlik RED mesaji basar (ASAN_EKSEN=...).
        - sayac dosyasina `RED` satiri yazar.
        - exit 1
    * İki eksen de tavanda veya altinda ise: exit 0.

    TAVAN DEGERLERI: tools/defter-kota-taban.py'dan okunur (TEK KAYNAK).
    Aşan eksen stderr'de adıyla yazılır (SATIR/BAYT/IKISI).

🔴 BYPASS KOLU (`--bypass-kontrol`, pre-push'ta cagrilir) — NEDEN AYRI VAR:
`--no-verify` ile atlanan bir kanca HIC KOSMAZ, yani kendi atlanisini KAYDEDEMEZ.
"RED sayisi" bypass sayisi DEGILDIR (RED, kapinin CALISTIGI haldir). Bypass ancak
SONUCUNDAN anlasilir: kota asilmis bir DEVAM.md **commit'lenmis** ve push'a gelmisse,
kapi ya atlanmistir ya hic kosmamistir. Bu kol o hali sayar:
    * HEAD'deki DEVAM.md (satir > 130 VEYA bayt > 12288) ise sayac dosyasina
      `BYPASS` satiri yazar.
    * 🔴 BLOKLAMAZ (her zaman exit 0): Okan hukmu "yasaklanamaz ama SAYILIR".
Sayac repo DISINDADIR (`~/.claude/cron/defter-kota-bypass.tsv`) — commit'e girmez,
gunluk 15:00 olcumune `DEFTER_KOTA_BYPASS` ekseni olarak okunur.

CI'da kosmaz; kancalar/pre-commit adim 8 (INDEX) + kancalar/pre-push (bypass) cagrisi.

KENDINI-TEST (--kendini-test):
    * Sentetik fiksturlerle M1 (BAYT asimi) + M2 (SATIR asimi) + 2 KONTROL
      (ikisi de tavan altinda, tam tavanda) + M3 (byte kolu mutanti) + M4
      (byte karak olarak sayisi) kosar. Cıktı son satırı:
          FIKSTUR=<n>/<n> MUTANT=<n>/<n>
          DUSEN=<n>
    * Tum vakalar yesil ise DUSEN=0, rc=0.
"""
import datetime
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

# Tek kaynaktan türet: tools/defter-kota-taban.py (kebab-case repo kurali;
# importlib ile yukle). Ikiz [[ikiz-tanim-sessiz-ayrisma]] kapatir.
import importlib.util as _ilu
_TABAN_YOL = os.path.join(TOOLS, "defter-kota-taban.py")
_tab = _ilu.spec_from_file_location("defter_kota_taban", _TABAN_YOL)
_mod = _ilu.module_from_spec(_tab)
_tab.loader.exec_module(_mod)
TAVAN_SATIR = _mod.TAVAN_SATIR
TAVAN_BAYT = _mod.TAVAN_BAYT
tavan_asi_mi = _mod.tavan_asi_mi

SAYAC_YOLU = os.environ.get("PRUVO_DEFTER_KOTA_SAYAC",
                           os.path.expanduser("~/.claude/cron/defter-kota-bypass.tsv"))


def _git(args, kok):
    r = subprocess.run(["git", "-C", kok] + list(args),
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def _devam_stage_de(kok):
    rc, out, _ = _git(["diff", "--cached", "--name-only",
                        "--diff-filter=ACMR", "-z"], kok)
    if rc != 0:
        return None  # OLCULEMEDI
    return "DEVAM.md" in (out.split("\0") if out else [])


def _devam_index_ham(kok):
    """DEVAM.md'nin INDEX blob'unu ham bayt olarak okur.

    UTF-8 bayt sayisi len(ham) ile; satir sayisi splitlines() ile.
    """
    rc, out, _ = _git(["cat-file", "blob", ":DEVAM.md"], kok)
    if rc != 0:
        return None
    if isinstance(out, str):
        return out.encode("utf-8")
    return out


def _devam_olcu_index(kok):
    """(satir, bayt) — biri None ise OLCULEMEDI."""
    ham = _devam_index_ham(kok)
    if ham is None:
        return None, None
    return len(ham.splitlines()), len(ham)


def _sayaç_yaz(kok, satir, bayt, sinif="RED"):
    """Sayac satiri: <ISO>\\t<sinif>\\t<depo>\\t<satir>\\t<bayt>."""
    try:
        os.makedirs(os.path.dirname(SAYAC_YOLU), exist_ok=True)
        with open(SAYAC_YOLU, "a", encoding="utf-8") as f:
            f.write("%s\t%s\t%s\t%d\t%d\n" % (
                datetime.datetime.now().isoformat(), sinif, kok, satir, bayt))
        return True
    except Exception:                                       # noqa: BLE001
        return False


def _devam_head_olcu(kok):
    rc, out, _ = _git(["cat-file", "blob", "HEAD:DEVAM.md"], kok)
    if rc != 0:
        return None, None
    ham = out.encode("utf-8") if isinstance(out, str) else out
    return len(ham.splitlines()), len(ham)


def bypass_kontrol(kok):
    """PUSH kolu — kota asilmis bir DEVAM.md commit'lenmisse BYPASS say. BLOKLAMAZ.

    🔴 Neden bloklamiyor: Okan hukmu "`--no-verify` yasaklanamaz ama SAYILIR".
    Bloklamak, kapiyi zaten atlamis birine ikinci bir duvar cikarmak olurdu; olculen
    ihtiyac SAYIDIR (gunluk 15:00 olcumun `DEFTER_KOTA_BYPASS`)."""
    satir, bayt = _devam_head_olcu(kok)
    if satir is None:
        # Defteri olmayan depo (kardes evler) ya da okunamadi -> sessiz gec, BLOKLAMA.
        return 0
    asi, eksen, _, _ = tavan_asi_mi(satir, bayt)
    if asi:
        _sayaç_yaz(kok, satir, bayt, sinif="BYPASS")
        print("!! DEFTER KOTASI BYPASS SAYILDI — HEAD'deki DEVAM.md %d satir / "
              "%d bayt (tavan satir=%d bayt=%d, ASAN_EKSEN=%s). Push DURDURULMADI, "
              "yalnizca sayildi: %s"
              % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen, SAYAC_YOLU),
              file=sys.stderr)
    return 0


def _hukum_red(satir, bayt, eksen, kok):
    """RED ciktisi; sayac yaz + exit 1 (ana akis)."""
    print("!! DEFTER KOTASI ASILDI — DEVAM.md %d satir / %d bayt "
          "(tavan satir=%d bayt=%d, ASAN_EKSEN=%s)."
          % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen), file=sys.stderr)
    print("!! CARE: python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py "
          "/Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md",
          file=sys.stderr)
    _sayaç_yaz(kok, satir, bayt)
    return 1


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--kendini-test" in argv:
        return _kendini_test()
    if "--bypass-kontrol" in argv:
        argv = [a for a in argv if a != "--bypass-kontrol"]
        return bypass_kontrol(argv[1] if len(argv) > 1 else ROOT)
    kok = argv[1] if argv and len(argv) > 1 else ROOT

    stage_de = _devam_stage_de(kok)
    if stage_de is None:
        print("!! COMMIT DURDURULDU — DEVAM.md stage kontrolu OLCULEMEDI.",
              file=sys.stderr)
        return 1
    if not stage_de:
        return 0

    satir, bayt = _devam_olcu_index(kok)
    if satir is None:
        print("!! COMMIT DURDURULDU — DEVAM.md INDEX blob'u okunamadi.",
              file=sys.stderr)
        return 1

    asi, eksen, _, _ = tavan_asi_mi(satir, bayt)
    if not asi:
        return 0
    return _hukum_red(satir, bayt, eksen, kok)


# ---------------------------------------------------------------------------
# KENDINI-TEST (K178)
# ---------------------------------------------------------------------------
def _kendini_test():
    """Sentetik fiksturlerle M1/M2 + 2 KONTROL + M3 + M4.

    K2 (tam tavan) asagidaki yoruma gorunmez sekilde RED sinifina dahildir
    (tavan DAHIL <=). M3 (byte kolu no-op) ile M1 fiksturu YEŞIL donmeli
    (yani byte kolu gercekten olculuyor). M4 (byte/char karisikligi) icin
    Turkce fikstur gerekir.
    """
    import tempfile

    sonuclar = []
    gecen = 0

    # ---- K1: satir altinda + bayt altinda → YESIL -------------------------
    fikstur = _fikstur_satir_bayt(50, 1000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("K1 YESIL", rc == 0, "satir=%d bayt=%d rc=%d (0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- K2: satir tam tavanda + bayt altinda → YESIL (tavan DAHIL) -------
    fikstur = _fikstur_satir_bayt(TAVAN_SATIR, 2000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("K2 TAM_TAVAN", rc == 0, "satir=%d bayt=%d rc=%d (0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M1: satir altinda + bayt asimda → KIRMIZI, ASAN_EKSEN=BAYT -------
    # M1'in BAYT-OVER satir-UNDER VAKASI burada. M3 izolasyonu icin M1
    # alternatifi (`M1_LOOSE` satir OVER + bayt OVER) asagida; M3 kolu
    # ORADA satir yedek sigortasi ile RED kalir.
    fikstur = _fikstur_satir_bayt(50, TAVAN_BAYT + 1000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("M1 BAYT", rc == 1 and satir <= TAVAN_SATIR and bayt > TAVAN_BAYT,
                      "satir=%d bayt=%d rc=%d (1 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M2: satir asimda + bayt altinda → KIRMIZI, ASAN_EKSEN=SATIR ------
    fikstur = _fikstur_satir_bayt(TAVAN_SATIR + 5, 2000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"])
    sonuclar.append(("M2 SATIR", rc == 1 and satir > TAVAN_SATIR and bayt <= TAVAN_BAYT,
                      "satir=%d bayt=%d rc=%d (1 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M3: byte kolu OLDURULMUS → M1 fiksturu YESIL'e donmeli ----------
    # Bayt kontrolu no-op edilince M1 (byte over, line under) YESIL'e doner;
    # donduyse byte kolu gercekten OLCULDU demektir ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).
    fikstur = _fikstur_satir_bayt(50, TAVAN_BAYT + 1000)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"], bayt_no_op=True)
    sonuclar.append(("M3 BAYT_NO_OP", rc == 0 and satir <= TAVAN_SATIR and bayt > TAVAN_BAYT,
                      "satir=%d bayt=%d rc=%d (mutant yesil; 0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    # ---- M4: byte yerine karak sayisi → Turkce fikstur YESIL'e donmeli ----
    # Turkce 'ş' UTF-8'de 2 bayt, 1 karakter. Byte > tavan, karak < tavan.
    # Karak kolu ile sayinca YESIL; byte kolu ile sayinca KIRMIZI.
    fikstur = _fikstur_turkce(TAVAN_BAYT + 200)
    satir, bayt, rc = _olcule_yardimci(fikstur["yol"], byte_yerine_karakter=True)
    sonuclar.append(("M4 KARAK", rc == 0,
                      "satir=%d bayt=%d rc=%d (mutant yesil; 0 beklenir)" % (satir, bayt, rc)))
    _fikstur_sil(fikstur)

    dusen = 0
    for ad, gecti, detay in sonuclar:
        if gecti:
            gecen += 1
        else:
            dusen += 1
            print("  ✗ %s: %s" % (ad, detay), file=sys.stderr)

    toplam = len(sonuclar)
    print("FIKSTUR=%d/%d MUTANT=%d/%d" % (gecen, toplam, dusen, toplam))
    print("DUSEN=%d" % dusen)
    return 0 if dusen == 0 else 1


def _fikstur_satir_bayt(satir_hedef, bayt_hedef):
    """Hedef satir + bayt sayisina yakin fikstur uretir (yol dict)."""
    import tempfile
    if satir_hedef <= 0:
        raise ValueError("satir_hedef > 0 olmali")
    if bayt_hedef < satir_hedef * 2:
        ortalama = 2
    else:
        ortalama = max(2, (bayt_hedef + satir_hedef - 1) // satir_hedef)
    genis = ortalama - 1  # -1 cunku newline = +1
    if genis < 1:
        genis = 1
    icerik = ("a" * genis + "\n") * satir_hedef
    fd, yol = tempfile.mkstemp(suffix=".md", prefix="k178-fikstur-")
    with os.fdopen(fd, "wb") as f:
        f.write(icerik.encode("utf-8"))
    return {"yol": yol, "satir": satir_hedef, "bayt": len(icerik.encode("utf-8"))}


def _fikstur_turkce(bayt_hedef):
    """Bayt hedefine ulasan Turkce karakterli fikstur. 'ş' 2 bayt.

    Satir sayisi TAVAN_SATIR'in ALTINDA tutulur ki satir ekseni M4 icin
    yalniz bayt eksenindeki fark gorulsun; byte > tavan, char < tavan.
    """
    import tempfile
    satir = max(1, TAVAN_SATIR - 30)  # TAVAN_SATIR-30 = 100
    # 80 'ş' + newline = 160 + 1 = 161 bayt/satir
    icerik = ("ş" * 80 + "\n") * satir
    fd, yol = tempfile.mkstemp(suffix=".md", prefix="k178-fikstur-tr-")
    with os.fdopen(fd, "wb") as f:
        f.write(icerik.encode("utf-8"))
    return {"yol": yol, "satir": satir, "bayt": len(icerik.encode("utf-8"))}


def _fikstur_sil(fikstur):
    try:
        os.unlink(fikstur["yol"])
    except OSError:
        pass


def _olcule_yardimci(yol, byte_yerine_karakter=False, bayt_no_op=False):
    """Dosyayi olc, kapinin ayni hukmu uygula.

    byte_yerine_karakter=True: bayt karsilastirmasi karakter sayisi ile yapilmis
        gibi davran (M4 mutanti).
    bayt_no_op=True: bayt karsilastirmasi >= her zaman True (M3 mutanti).
    """
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError:
        return None, None, 1
    satir = len(ham.splitlines())
    bayt = len(ham)

    satir_as = satir > TAVAN_SATIR
    if bayt_no_op:
        bayt_as = False
    elif byte_yerine_karakter:
        try:
            metin = ham.decode("utf-8")
        except UnicodeDecodeError:
            metin = ""
        bayt_as = len(metin) > TAVAN_BAYT
    else:
        bayt_as = bayt > TAVAN_BAYT

    if satir_as or bayt_as:
        return satir, bayt, 1
    return satir, bayt, 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

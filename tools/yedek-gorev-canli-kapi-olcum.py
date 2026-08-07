#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CANLI OLCUM — gorev agaci GERCEK Drive yedegine giriyor mu, sir GIRMIYOR mu?

Kum havuzu iddiasi tek basina yetmez: gercek ortamda GERCEK hedefe kosulmus bir
olcum ister. Bu betik:
  1. GERCEK ~/.claude/scheduled-tasks icine UC SENTETIK sahte jeton dosyasi koyar
     (gercek jetona DOKUNMAZ, OKUMAZ; ~/.claude/cron'a hic bakmaz).
  2. Gercek yedegi kosar (kilit mesgulse tekrar dener — atlanan kosum "kanit" degildir).
  3. Gorev metinlerinin hedefte BAYT BAYT durdugunu sha256 ile olcer.
  4. Sentetiklerin hedefte HICBIR YERDE olmadigini olcer.
  5. Sentetikleri SILER ve yedegi tekrar kosar; temizligi dogrular.

🔴 SENTETIK ICERIKLER UYDURMADIR. Gercek bir sirrin degeri bu dosyada YOKTUR ve
   hicbir jeton dosyasinin ICERIGI okunmaz/basilmaz.
"""
import hashlib
import os
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
YEDEKLE = os.path.join(TOOLS, "yedekle.py")
sys.path.insert(0, TOOLS)
import drive_yolu                                                    # noqa: E402

GOREVLER = os.path.expanduser("~/.claude/scheduled-tasks")
SENTETIK_DIZIN = os.path.join(GOREVLER, "_sentetik-kapi-testi")

# Parcali kurulur: hicbir KAYNAK SATIRI jeton desenine uymaz, calisma anindaki dize
# yedekle.SIR_IMZALARI "GitHub jetonu" imzasini tetikler.
SAHTE_IMZA = "gh" + "p_" + ("S" * 36)

SENTETIKLER = (
    (".sentetik-gh-token", "SENTETIK-SAHTE-GERCEK-DEGIL\n", "ad + uzantisiz"),
    ("sahte-token.md", "SENTETIK-SAHTE-GERCEK-DEGIL\n", "ad deseni, IZINLI uzanti"),
    ("imza-notu.md", "not\n" + SAHTE_IMZA + "\n", "icerik imzasi, IZINLI uzanti"),
)


def sha(yol):
    try:
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def yedek_kos(etiket, deneme=6):
    """Gercek yedegi kosar. ATLANAN kosum kanit DEGILDIR -> tekrar dener."""
    for i in range(deneme):
        r = subprocess.run([sys.executable, YEDEKLE], capture_output=True, text=True)
        if "yedek ATLANDI" not in r.stdout:
            print("  [%s] kosum %d: rc=%d" % (etiket, i + 1, r.returncode))
            return r
        print("  [%s] kosum %d ATLANDI (kilit mesgul) — tekrar" % (etiket, i + 1))
    print("  [%s] 🔴 kilit hep mesgul — OLCULEMEDI" % etiket)
    return None


def hedef_dosyalari(kok):
    if not os.path.isdir(kok):
        return []
    return [os.path.join(d, a) for d, _alt, adlar in os.walk(kok) for a in adlar]


def main():
    pruvo = drive_yolu.pruvo_dizini(sessiz=True)
    if not pruvo:
        print("🔴 OLCULEMEDI — Drive yolu cozulemedi.")
        return 1
    backup = os.path.join(pruvo, "backup")
    hedef_gorev = os.path.join(backup, "gorev-tanimlari")

    kaynak_skill = sorted(os.path.join(d, a) for d, _alt, adlar in os.walk(GOREVLER)
                          for a in adlar if a == "SKILL.md"
                          and "_sentetik-kapi-testi" not in d)
    print("KAYNAK: %d adet SKILL.md  <- %s" % (len(kaynak_skill), GOREVLER))

    print("\n1) SENTETIK SAHTE JETONLAR YERLESTIRILIYOR (gercek jetona DOKUNULMAZ)")
    os.makedirs(SENTETIK_DIZIN, exist_ok=True)
    for ad, icerik, gerekce in SENTETIKLER:
        with open(os.path.join(SENTETIK_DIZIN, ad), "w", encoding="utf-8") as f:
            f.write(icerik)
        print("  kondu: %-24s (%s)" % (ad, gerekce))

    try:
        print("\n2) GERCEK YEDEK KOSUYOR")
        r = yedek_kos("sentetikli")
        if r is None:
            return 1
        for satir in r.stdout.splitlines():
            if "gorev" in satir.lower() or "DISLANDI" in satir:
                print("  | " + satir.strip())

        print("\n3) GOREV METINLERI HEDEFTE BAYT BAYT MI?")
        tutan = 0
        for k in kaynak_skill:
            gor = os.path.relpath(k, GOREVLER)
            h = os.path.join(hedef_gorev, gor)
            if sha(k) is not None and sha(k) == sha(h):
                tutan += 1
            else:
                print("  ❌ TUTMADI: " + gor)
        print("  GOREV_METNI = %d/%d bayt bayt" % (tutan, len(kaynak_skill)))

        print("\n4) SENTETIK JETONLAR HEDEFTE VAR MI? (tum backup agaci taranir)")
        tum = hedef_dosyalari(backup)
        sizan = [y for y in tum
                 if os.path.basename(y) in [a for a, _i, _g in SENTETIKLER]]
        print("  taranan hedef dosya: %d" % len(tum))
        print("  SIZAN: %d  %s" % (len(sizan), sizan[:5]))
        sir_kapisi = (len(sizan) == 0)
        print("  SIR_DISLAMA = " + ("kanitlandi ✅" if sir_kapisi else "KANITLANMADI 🔴"))
    finally:
        print("\n5) SENTETIKLER SILINIYOR")
        shutil.rmtree(SENTETIK_DIZIN, ignore_errors=True)
        print("  kaynak temiz mi: %s" % (not os.path.exists(SENTETIK_DIZIN)))

    print("\n6) TEMIZLIK SONRASI YEDEK (durum eski haline donsun)")
    yedek_kos("temiz")
    tum = hedef_dosyalari(backup)
    kalan = [y for y in tum if os.path.basename(y) in [a for a, _i, _g in SENTETIKLER]]
    print("  hedefte kalan sentetik: %d" % len(kalan))

    print("\nSONUC: %s" % ("✅ HAZIR" if (sir_kapisi and tutan == len(kaynak_skill)
                                         and not kalan) else "🔴 KIRMIZI"))
    return 0 if (sir_kapisi and tutan == len(kaynak_skill) and not kalan) else 1


if __name__ == "__main__":
    sys.exit(main())

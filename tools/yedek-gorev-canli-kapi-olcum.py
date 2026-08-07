#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CANLI OLCUM — ~/.claude agaclari GERCEK Drive yedegine giriyor mu, sir GIRMIYOR mu?

Kum havuzu iddiasi tek basina yetmez: gercek ortamda GERCEK hedefe kosulmus bir
olcum ister. AGAC_KAPSAMI'ndaki her agac icin:
  1. GERCEK agacin icine SENTETIK sahte jeton dosyalari koyar.
     🔴 GERCEK jetonlara (~/.claude/cron/.ci-token, .gh-token) DOKUNULMAZ, ICERIKLERI
     OKUNMAZ. Onlar zaten yerinde duruyor ve AYRI bir iddia olarak olculur (bkz. 4b).
  2. Gercek yedegi kosar (kilit mesgulse tekrar dener — atlanan kosum KANIT DEGILDIR).
  3. Izinli dosyalarin hedefte BAYT BAYT durdugunu sha256 ile olcer.
  4a. SENTETIKLERIN hedefte hicbir yerde olmadigini olcer.
  4b. GERCEK jeton adlarinin hedefte hicbir yerde olmadigini olcer (ad bazli; icerik
      OKUNMAZ).
  5. Sentetikleri SILER ve yedegi tekrar kosar; temizligi dogrular.

⚠️ SENTETIK ICERIKLER UYDURMADIR; gercek bir sirrin degeri bu dosyada YOKTUR.
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
import yedekle                                                       # noqa: E402

SENTETIK_ALT = "_sentetik-kapi-testi"

# Parcali kurulur: hicbir KAYNAK SATIRI jeton desenine uymaz; calisma anindaki dize
# yedekle.SIR_IMZALARI "GitHub jetonu" imzasini tetikler.
SAHTE_IMZA = "gh" + "p_" + ("S" * 36)
SAHTE_GOVDE = "SENTETIK-SAHTE-GERCEK-DEGIL\n"

# (ad, icerik, hangi katmanin elemesi beklenir)
SENTETIKLER = (
    (".sentetik-ci-token", SAHTE_GOVDE, "sir (ad deseni, uzantisiz)"),
    (".sentetik-gh-token", SAHTE_GOVDE, "sir (ad deseni, uzantisiz)"),
    ("sahte-token.md", SAHTE_GOVDE, "sir (ad deseni, IZINLI uzanti)"),
    ("imza-notu.md", "not\n" + SAHTE_IMZA + "\n", "sir (icerik imzasi, IZINLI uzanti)"),
    ("artik.bin", "zararsiz icerik\n", "allowlist (IZINSIZ uzanti)"),
)

# GERCEK jeton adlari — SADECE AD olarak kullanilir, ICERIKLERI ASLA OKUNMAZ.
GERCEK_JETON_ADLARI = (".ci-token", ".gh-token")


def sha(yol):
    try:
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def yedek_kos(etiket, deneme=6):
    """Gercek yedegi kosar. ATLANAN kosum KANIT DEGILDIR -> tekrar dener."""
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


def agac_olc(kok, hedef_kok, izinli):
    """(dosya_sayisi, bayt) — kaynaktaki IZINLI dosyalarin hedefteki karsiligi."""
    sayi = bayt = tutan = 0
    for dizin, _alt, adlar in os.walk(kok):
        for ad in sorted(adlar):
            if SENTETIK_ALT in dizin:
                continue
            k = os.path.join(dizin, ad)
            if os.path.splitext(ad)[1].lower() not in izinli:
                continue
            if yedekle.sir_sebebi(k, ad):
                continue
            sayi += 1
            try:
                bayt += os.path.getsize(k)
            except OSError:
                pass
            h = os.path.join(hedef_kok, os.path.relpath(k, kok))
            if sha(k) is not None and sha(k) == sha(h):
                tutan += 1
            else:
                print("    ❌ BAYT TUTMADI: " + os.path.relpath(k, kok))
    return sayi, bayt, tutan


def main():
    pruvo = drive_yolu.pruvo_dizini(sessiz=True)
    if not pruvo:
        print("🔴 OLCULEMEDI — Drive yolu cozulemedi.")
        return 1
    backup = os.path.join(pruvo, "backup")

    print("AGAC_KAPSAMI: %d agac" % len(yedekle.AGAC_KAPSAMI))
    for etiket, kok, hedef_klasor, izinli in yedekle.AGAC_KAPSAMI:
        print("  %-6s %-34s -> backup/%-16s izinli: %s"
              % (etiket, kok, hedef_klasor, ", ".join(izinli)))

    print("\n0) ONCESI — hedefte ne var?")
    once = {}
    for etiket, _kok, hedef_klasor, _izinli in yedekle.AGAC_KAPSAMI:
        hk = os.path.join(backup, hedef_klasor)
        dosyalar = hedef_dosyalari(hk)
        b = sum(os.path.getsize(y) for y in dosyalar if os.path.exists(y))
        once[etiket] = (len(dosyalar), b)
        print("  %-6s %4d dosya  %10d bayt" % (etiket, len(dosyalar), b))

    print("\n1) SENTETIK SAHTE JETONLAR YERLESTIRILIYOR")
    print("   (GERCEK jetonlara DOKUNULMAZ; icerikleri OKUNMAZ)")
    konan = []
    for _etiket, kok, _hk, _iz in yedekle.AGAC_KAPSAMI:
        if not os.path.isdir(kok):
            continue
        alt = os.path.join(kok, SENTETIK_ALT)
        os.makedirs(alt, exist_ok=True)
        konan.append(alt)
        for ad, icerik, _gerekce in SENTETIKLER:
            with open(os.path.join(alt, ad), "w", encoding="utf-8") as f:
                f.write(icerik)
        print("  kondu: %s (%d dosya)" % (alt, len(SENTETIKLER)))

    tutan_hepsi = True
    try:
        print("\n2) GERCEK YEDEK KOSUYOR")
        r = yedek_kos("sentetikli")
        if r is None:
            return 1
        for satir in r.stdout.splitlines():
            if "DISLAMA:" in satir or "DISLANDI:" in satir or satir.startswith("yedek: "):
                print("  | " + satir.strip())

        print("\n3) IZINLI DOSYALAR HEDEFTE BAYT BAYT MI?")
        sonra = {}
        for etiket, kok, hedef_klasor, izinli in yedekle.AGAC_KAPSAMI:
            hk = os.path.join(backup, hedef_klasor)
            sayi, bayt, tutan = agac_olc(kok, hk, izinli)
            sonra[etiket] = (sayi, bayt)
            print("  %-6s %d/%d bayt bayt   (%d dosya, %d bayt)"
                  % (etiket, tutan, sayi, sayi, bayt))
            if tutan != sayi:
                tutan_hepsi = False

        print("\n4a) SENTETIK JETONLAR HEDEFTE VAR MI? (TUM backup agaci)")
        tum = hedef_dosyalari(backup)
        sentetik_adlar = [a for a, _i, _g in SENTETIKLER]
        sizan = [y for y in tum if os.path.basename(y) in sentetik_adlar]
        print("  taranan hedef dosya: %d" % len(tum))
        print("  SIZAN: %d  %s" % (len(sizan), sizan[:5]))

        print("\n4b) 🔴 GERCEK JETONLAR HEDEFTE VAR MI? (ad bazli; icerik OKUNMADI)")
        gercek_sizan = [y for y in tum
                        if os.path.basename(y) in GERCEK_JETON_ADLARI]
        for ad in GERCEK_JETON_ADLARI:
            var = os.path.isfile(os.path.join(yedekle.CRON, ad))
            print("  kaynakta %s: %s   hedefte: %s"
                  % (ad, "VAR" if var else "yok",
                     "🔴 VAR" if any(os.path.basename(y) == ad for y in tum) else "YOK ✅"))
        sir_kapisi = (not sizan) and (not gercek_sizan)
        print("  SIR_DISLAMA = " + ("kanitlandi ✅" if sir_kapisi else "KANITLANMADI 🔴"))
        print("\n  ONCE -> SONRA (dosya / bayt):")
        for etiket, _k, _h, _i in yedekle.AGAC_KAPSAMI:
            print("    %-6s %d -> %d dosya   %d -> %d bayt"
                  % (etiket, once[etiket][0], sonra[etiket][0],
                     once[etiket][1], sonra[etiket][1]))
    finally:
        print("\n5) SENTETIKLER SILINIYOR")
        for alt in konan:
            shutil.rmtree(alt, ignore_errors=True)
            print("  silindi: %s  (temiz: %s)" % (alt, not os.path.exists(alt)))

    print("\n6) TEMIZLIK SONRASI YEDEK (durum eski haline donsun)")
    yedek_kos("temiz")
    tum = hedef_dosyalari(backup)
    kalan = [y for y in tum
             if os.path.basename(y) in [a for a, _i, _g in SENTETIKLER]
             or os.path.basename(y) in GERCEK_JETON_ADLARI]
    print("  hedefte kalan sentetik/gercek jeton: %d" % len(kalan))

    hazir = sir_kapisi and tutan_hepsi and not kalan
    print("\nSONUC: %s" % ("✅ HAZIR" if hazir else "🔴 KIRMIZI"))
    return 0 if hazir else 1


if __name__ == "__main__":
    sys.exit(main())

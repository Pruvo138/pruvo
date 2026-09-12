#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`tools/d1-sapma-mutasyon.py` DAYANAK sozlesmesinin KANITI (K62, 12 Agu 2026).

NE OLCER: bataryanin kendisi bir olcum aracidir; onun BAYATLAMASI sessizce olculmeyen
bir bolge dogurur. 7 Agu'da tam bu oldu: ONARILAMADI adiminin kosulu bataryanin icine
ELLE ikinci kez yazilmisti, canli is akisi degisti ve batarya S4'te "HARNESS BAYAT"
deyip DURDU -> S4..S12 + K1..K3 (12 mutant) HIC KOSMADI. Batarya yesil de yansa kirmizi
da yansa o bolge hakkinda HICBIR SEY SOYLEMIYORDU ([[bayat-kabul-testi]]).

🔴 "ONARDIM" BIR IDDIADIR — bu surucu onu CALISTIRILABILIR KANITA cevirir. Anlatilan
batarya kanit degildir ([[mutasyon-kaniti-yeniden-uretilebilir]]); surucu repoda durur.

UC IDDIA (hepsi AYNAda kosar, canli dosyalara DOKUNULMAZ):
  A) TURETME CANLI: ONARILAMADI kosulunun METNI degisir (semantik AYNI kalir, yalniz
     `&&` atomlari yeniden siralanir) -> batarya S4/S5'i YINE kosar ve YINE oldurur.
     ELLE yazilmis dayanak bu aynada SISTEMATIK olarak duserdi; turetilen dayanak duser
     MI diye BAKILMAZ, OLCULUR.
  B) AYRISMA KIRMIZI: bir dayanak metin kaynakta bulunamaz hale gelirse hukum KIRMIZI
     olur (sessizce "atlandi"/yesil'e DONMEZ).
  C) DUVAR YOK: (B) halinde batarya DURMAZ — kalan mutantlar FIILEN kosar ve KAPSAM
     iddiasi eksigi SAYIYLA beyan eder.

Kullanim: python3 tools/d1-sapma-mutasyon-dayanak-kaniti.py
Cikis 0 = uc iddia da dogrulandi.
"""
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
BATARYA = "tools/d1-sapma-mutasyon.py"
UZLASTIRICI = os.path.join(".github", "workflows", "d1-uzlastirici.yml")

# 🔴 CAPALAR ELLE YAZILMAZ — BATARYANIN KENDISINDEN TURETILIR (13 Eyl 2026).
# OLCULDU: burada `SIRA_ONCE` elle yazilmisti (`always() && sapma=='var' && teyit!='success'`);
# `61c5a27b` (K150 dilim-2) kosula `&& steps.onarim.outputs.ertelendi != 'evet'` ekledi
# ve surucu "KANIT SURUCUSU BAYAT: ayna capasi 0 kez bulundu" diye DURDU — batarya
# (`d1-sapma-mutasyon.py`) kosulu zaten canli is akisindan turettigi icin YESILDI; bayatlayan
# yalniz bu surucunun IKINCI KOPYASIYDI ([[ikiz-tanim-sessiz-ayrisma]]).
# COZUM: (A) capasi bataryanin `dayanak_kosul_satiri("onarilamadi")` cevabidir, (B/C)
# capasi bataryanin K1 kontrol mutantinin `bul` metnidir. Batarya ile surucu ARTIK AYNI
# KAYNAKTAN okur; turetme tutmazsa surucu KIRMIZI (rc=1) doner, yesile DONMEZ.
CAPA_SONRA = "      # (1) CRON / ELLE KOLU — davranis degismedi (capa kaydirildi).\n"


def _batarya_modulu():
    spec = importlib.util.spec_from_file_location(
        "d1_sapma_mutasyon_dayanak", os.path.join(ROOT, BATARYA))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def turetilen_capalar():
    """((sira_once, sira_sonra), (capa_once, capa_sonra), hata) — hata doluysa capalar None.

    (A) sira_sonra: `always()` sonrasi `&&` atomlari TERS siralanir (semantik AYNI; GitHub
    ifadelerinde `&&` yan etkisizdir). `||` ya da parantez varsa yeniden siralama semantigi
    degistirebilir -> turetme REDDEDILIR (fail-closed).
    """
    try:
        bat = _batarya_modulu()
    except Exception as e:  # noqa: BLE001 — her yukleme arizasi KIRMIZI'dir
        return None, None, "batarya yuklenemedi (%s: %s)" % (type(e).__name__, e)
    satir, hata = bat.dayanak_kosul_satiri("onarilamadi")
    if satir is None:
        return None, None, "ONARILAMADI kosulu bataryadan turetilemedi: %s" % hata
    girinti = satir[:len(satir) - len(satir.lstrip())]
    govde = satir.strip()[3:].strip()
    if "||" in govde or "(" in govde.replace("always()", ""):
        return None, None, "kosul yalniz `&&` atomlarindan olusmuyor: %r" % govde
    atomlar = [a.strip() for a in govde.split("&&")]
    if len(atomlar) < 3 or atomlar[0] != "always()":
        return None, None, ("yeniden siralanacak `always() && a && b...` bicimi yok: %r"
                            % govde)
    sonra = "%sif: %s\n" % (girinti, " && ".join([atomlar[0]] + atomlar[:0:-1]))
    if sonra == satir:
        return None, None, "ters siralama metni DEGISTIRMEDI (A iddiasi olculemez)"
    k1 = [m for m in bat.MUTANTLAR if m[0] == "K1"]
    if len(k1) != 1 or not k1[0][3]:
        return None, None, "bataryada K1 kontrol mutanti TEK degil"
    capa_once = k1[0][3][0][0]
    return (satir, sonra), (capa_once, CAPA_SONRA), None

KOSAN_RE = re.compile(r"(\d+)/(\d+) FIILEN KOSTU")
FAILS = []


def check(mesaj, kosul, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ayna_kur(kok, degisim):
    """ROOT'un tools/ + .github/workflows/ aynasi; `degisim` = (bul, yerine) ya da None."""
    os.makedirs(kok)
    shutil.copytree(os.path.join(ROOT, "tools"), os.path.join(kok, "tools"),
                    symlinks=False)
    shutil.copytree(os.path.join(ROOT, ".github", "workflows"),
                    os.path.join(kok, ".github", "workflows"), symlinks=False)
    if degisim is not None:
        bul, yerine = degisim
        yol = os.path.join(kok, UZLASTIRICI)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        if metin.count(bul) != 1:
            raise SystemExit("🔴 KANIT SURUCUSU BAYAT: ayna capasi %d kez bulundu "
                             "(1 olmali). Aranan: %r" % (metin.count(bul), bul[:160]))
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin.replace(bul, yerine, 1))
    return kok


def bataryayi_kos(kok):
    r = subprocess.run([sys.executable, os.path.join(kok, BATARYA)],
                       cwd=kok, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def mutant_hukmu(cikti, kod):
    """`kod` mutanti icin bataryanin bastigi (kostu_mu, oldurdu_mu, dayanak_kirmizisi)."""
    kostu = ("  ✔ %s: iddia sayisi KORUNDU" % kod) in cikti
    oldu = ("  ✔ %s: mutant OLDU" % kod) in cikti or \
           ("  ✔ %s: KONTROL — mutant YESIL kaldi" % kod) in cikti
    dayanak_kirmizi = ("  ✘ %s: DAYANAK" % kod) in cikti
    return kostu, oldu, dayanak_kirmizi


def main():
    print("DAYANAK SOZLESMESI KANITI — tools/d1-sapma-mutasyon.py (K62)\n")
    once = {y: sha(os.path.join(ROOT, y)) for y in (BATARYA, UZLASTIRICI)}
    sira, capa, hata = turetilen_capalar()
    if hata:
        print("🔴 KANIT SURUCUSU CAPASI TURETILEMEDI: %s" % hata)
        print("Neyi olcmek kapatir: `python3 tools/d1-sapma-mutasyon.py` YESIL mi — "
              "batarya kosulu turetemiyorsa surucu da turetemez (ayni kaynak).")
        return 1
    tmp = tempfile.mkdtemp(prefix="d1-sapma-dayanak-kaniti-")
    try:
        # ── (A) TURETME CANLI MI ───────────────────────────────────────────────
        print("A) TURETME CANLI: ONARILAMADI kosulunun METNI degisti (semantik AYNI)")
        rc_a, cikti_a = bataryayi_kos(ayna_kur(os.path.join(tmp, "a"), sira))
        m = KOSAN_RE.search(cikti_a)
        kosan_a = int(m.group(1)) if m else -1
        toplam_a = int(m.group(2)) if m else -1
        for kod in ("S4", "S5"):
            kostu, oldu, dayanak_kirmizi = mutant_hukmu(cikti_a, kod)
            check("%s: METNI DEGISMIS kosulda FIILEN KOSTU (dayanak elle yazili DEGIL)"
                  % kod, kostu and not dayanak_kirmizi,
                  "kostu=%s dayanak_kirmizi=%s" % (kostu, dayanak_kirmizi))
            check("%s: yeni metinde de OLDURULDU (mutant KIRMIZI)" % kod, oldu)
        check("A) batarya BUTUNUYLE kostu ve YESIL", rc_a == 0 and kosan_a == toplam_a,
              "cikis=%s kosan=%s/%s" % (rc_a, kosan_a, toplam_a))
        if FAILS:
            print("  --- (A) kuyrugu ---\n%s" % cikti_a[-2500:])

        # ── (B/C) AYRISMA KIRMIZI + DUVAR YOK ─────────────────────────────────
        print("\nB/C) AYRISMA: elle yazili bir dayanak (K1 yorum capasi) kaynaktan silindi")
        rc_b, cikti_b = bataryayi_kos(ayna_kur(os.path.join(tmp, "b"),
                                               capa))
        m = KOSAN_RE.search(cikti_b)
        kosan_b = int(m.group(1)) if m else -1
        toplam_b = int(m.group(2)) if m else -1
        k1_kostu, _k1_oldu, k1_dayanak = mutant_hukmu(cikti_b, "K1")
        check("B) ayrisan dayanak KIRMIZI iddia uretti (sessiz 'atlandi' DEGIL)",
              k1_dayanak and not k1_kostu,
              "dayanak_kirmizi=%s kostu=%s" % (k1_dayanak, k1_kostu))
        check("B) bataryanin HUKMU KIRMIZI (yesile DONMEDI)", rc_b != 0, "cikis=%s" % rc_b)
        # C) DUVAR YOK: K1'den SONRAKI mutantlar (K2, K3) yine fiilen kosmus olmali.
        sonraki = [kod for kod in ("K2", "K3") if mutant_hukmu(cikti_b, kod)[0]]
        check("C) DUVAR YOK: ayrisan dayanaktan SONRAKI mutantlar FIILEN kostu",
              len(sonraki) == 2, "kosan sonraki: %s" % (sonraki or "-"))
        check("C) KAPSAM eksigi SAYIYLA beyan edildi", kosan_b == toplam_b - 1,
              "kosan=%s/%s (beklenen %s)" % (kosan_b, toplam_b, toplam_b - 1))
        check("C) KAPSAM iddiasi KIRMIZI yandi",
              "✘ KAPSAM: her mutant FIILEN kostu" in cikti_b)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nCANLI KAYNAKLAR DEGISMEDI MI")
    for y in (BATARYA, UZLASTIRICI):
        check("sha256 ayni: %s" % y, sha(os.path.join(ROOT, y)) == once[y])

    print("\nOZET: %d kusur" % len(FAILS))
    if FAILS:
        print("🔴 DAYANAK KANITI KIRMIZI:")
        for f in FAILS:
            print("   - %s" % f)
        return 1
    print("✅ DAYANAK KANITI GECTI — (A) kosul dayanagi CANLI dosyadan turiyor, "
          "(B) ayrisma KIRMIZI, (C) ayrisma DUVAR kurmuyor (kalan mutantlar olculuyor).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

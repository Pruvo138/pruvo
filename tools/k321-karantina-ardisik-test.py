#!/usr/bin/env python3
"""K321 KABUL BATARYASI — 13 ardisik `motor=claude rc=1` karantina YAZIYOR MU?

ASIL VAKA (27 Agu 2026, olculdu): `motor=claude` 13 ardisik kosumda `rc=1` dondu ve
karar kolu her seferinde `yazildi=hayir sebep=fatal-satir-yok` bastigi icin karantina
HIC yazilmadi — yani hattin duruma kor kalmasi 13 kosum boyunca surdu. Kusurun sinifi:
hukum TEK EKSENE (ciktida `fatal` satiri var mi) bagliydi; hata MESAJI okunmuyordu ve
"imza yok" hali "sorun yok" ile ayni kovaya dusuyordu.

OLCULEN KANONIK KAYNAK: `~/.claude/cron/isci-karantina-karar.py` (CANLI, SALT OKUMA).
BU BATARYA CANLIYI DEGIL, repodaki BIREBIR KOPYASINI kosar:
    tools/k321/cron/isci-karantina-karar.py
Kopya canliyla ayni `git hash-object` degerinden baslar; bayatlarsa B0 vakasi bunu
ADIYLA basar (CI'da canli ev YOKTUR -> orada B0 `OLCULEMEDI` der, SESSIZ GECMEZ).

VAKALAR
  B0  BAYATLIK  — kopya canliyla birebir mi (canli ev varsa OLCULUR, yoksa OLCULEMEDI)
  B1  ASIL VAKA — 13 ardisik `rc=1` + ciktida `fatal` satiri YOK -> karantina YAZILIR
  B2  KONTROL   — TEK seferlik `rc=1` (ayni kosullar) karantina URETMEZ
  B3  KONTROL   — `rc=0` dizisi sayaci SIFIRLAR (13 basarili kosum karantina yazmaz)
  B4  SINIF     — hukum "fatal satir" eksenine GERI baglanirsa B1 kirmizi yanar
                  (mutant kolu; surucu `--arac <mutant> --yalniz-b1` ile kosar)

KOSUM:  python3 tools/k321-karantina-ardisik-test.py
KABUL:  son satir `K321_KABUL=GECTI` ve rc=0.
"""

import argparse
import hashlib

import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
KOPYA = os.path.join(TOOLS, "k321", "cron", "isci-karantina-karar.py")
CANLI = os.path.expanduser("~/.claude/cron/isci-karantina-karar.py")
MOTOR_REGEX = r"claude|minimax-m3"

SONUC = []


def kayit(ad, gecti, ayrinti=""):
    SONUC.append((ad, gecti, ayrinti))
    isaret = {True: "OK", False: "DUSTU", None: "OLCULEMEDI"}[gecti]
    print("  %-58s %-11s %s" % (ad, isaret, ayrinti))


def git_hash(yol):
    """`git hash-object` ile AYNI deger (blob sha1) — git cagirmadan."""
    with open(yol, "rb") as f:
        veri = f.read()
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(veri))
    h.update(veri)
    return h.hexdigest()


def kos(arac, kok, rc, motor="claude", ev="pruvo", fatal=False):
    """Karar kolunu BIR kez kosar. Doner: (returncode, stdout)."""
    cikti = os.path.join(kok, "cikti.txt")
    with open(cikti, "w", encoding="utf-8") as f:
        f.write("model cevabi\n")
        if fatal:
            f.write("fatal: credit balance is too low\n")
        else:
            # 🔴 ASIL VAKANIN METNI: hata MESAJDA duruyor ama `fatal` KELIMESI yok.
            f.write("API Error: 400 {\"message\":\"insufficient balance\"}\n")
    karantina = os.path.join(kok, "karantina.json")
    r = subprocess.run(
        [sys.executable, arac, "--ev", ev, str(rc), cikti, motor, karantina,
         MOTOR_REGEX],
        capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def karantinada_mi(kok, motor="claude"):
    """Karantina KAYDI duzlemi: duz metin, satir basi `<motor> <epoch>` (bkz. `_yaz`).

    🔴 JSON SANMA: dosyanin adi `.json` olsa da bicim SATIRDIR; JSON ayristiricisi
    kullanan bir olcut HER ZAMAN "yazilmadi" der ve kirmiziyi sessizce YUTAR
    ([[eslesme-anahtari-yanlissa-sifir-bulgu-yesil-sanilir]])."""
    yol = os.path.join(kok, "karantina.json")
    if not os.path.isfile(yol):
        return False
    with open(yol, "r", encoding="utf-8") as f:
        for satir in f:
            parcalar = satir.split()
            if parcalar and parcalar[0] == motor:
                return True
    return False


def dizi_kos(arac, adet, rc, ev="pruvo"):
    """Taze fikstur uzerinde `adet` kosum. Doner: (yazildi_mi, kacinci, son_cikti)."""
    with tempfile.TemporaryDirectory(prefix="pruvo-k321-") as kok:
        son = ""
        for n in range(1, adet + 1):
            _rc, son = kos(arac, kok, rc, ev=ev)
            if karantinada_mi(kok):
                return True, n, son
        return False, None, son


def b0_bayatlik():
    if not os.path.isfile(KOPYA):
        kayit("B0 kopya canliyla BIREBIR", False, "kopya YOK: %s" % KOPYA)
        return
    if not os.path.isfile(CANLI):
        kayit("B0 kopya canliyla BIREBIR", None,
              "canli ev YOK (CI duzlemi) -> kopya hash=%s" % git_hash(KOPYA)[:12])
        return
    c, k = git_hash(CANLI), git_hash(KOPYA)
    kayit("B0 kopya canliyla BIREBIR", c == k,
          "canli=%s kopya=%s" % (c[:12], k[:12]))


def bataryayi_kos(arac):
    # --- B1 ASIL VAKA: 13 ardisik rc=1, ciktida `fatal` YOK.
    yazildi, kacinci, son = dizi_kos(arac, 13, 1)
    kayit("B1 13 ardisik rc=1 (fatal satiri YOK) -> karantina YAZILIR",
          yazildi, ("%d. kosumda yazildi" % kacinci) if yazildi
          else ("13 kosumda YAZILMADI | son: %s" % son.strip().splitlines()[-1:]))

    # --- B2 KONTROL: tek seferlik rc=1 karantina URETMEZ.
    tek, _kac, _s = dizi_kos(arac, 1, 1)
    kayit("B2 KONTROL: TEK seferlik rc=1 karantina URETMEZ", not tek,
          "yazildi=%s" % ("evet" if tek else "hayir"))

    # --- B3 KONTROL: rc=0 dizisi karantina URETMEZ (sayac sifirlanir).
    basarili, _kac, _s = dizi_kos(arac, 13, 0)
    kayit("B3 KONTROL: 13 ardisik rc=0 karantina URETMEZ", not basarili,
          "yazildi=%s" % ("evet" if basarili else "hayir"))
    return yazildi


# --------------------------------------------------------------------- MUTANT
# 🔴 HEDEF KOL ATIFLI: hukum yeniden YALNIZ `fatal` satiri eksenine baglanirsa
# (yani `filo_hukmu` kolu olurse) B1 KIRMIZI yanmali. Capa `main()`in KENDI
# govdesindeki ardisik-esik kosuludur, komsusunda degil.
MUT_CAPA = ("        elif rc != 0 and filo_hukmu(_ardisik, _evler, "
            "GENEL_ARDISIK_ESIGI, TEK_EV_UZUN_DIZI_ESIGI):")
MUT_YAMA = ("        elif False:  # MUTANT: hukum yeniden YALNIZ fatal-satir "
            "eksenine bagli")


def mutant_kur(kok):
    with open(KOPYA, "r", encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(MUT_CAPA) != 1:
        return None, "capa tekil DEGIL (adet=%d)" % kaynak.count(MUT_CAPA)
    yol = os.path.join(kok, "mutant-karar.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(MUT_CAPA, MUT_YAMA, 1))
    return yol, "capa TEK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arac", default=KOPYA,
                    help="olculecek karar kolu (mutant surucusu kullanir)")
    ap.add_argument("--yalniz-b1", action="store_true")
    a = ap.parse_args()

    print("K321 KABUL BATARYASI — OLCULEN_ARAC=%s" % a.arac)
    if not os.path.isfile(a.arac):
        print("HATA: arac YOK -> %s" % a.arac)
        return 2

    if a.yalniz_b1:
        yazildi, kacinci, _s = dizi_kos(a.arac, 13, 1)
        print("B1_YAZILDI=%s KACINCI=%s" % ("evet" if yazildi else "hayir", kacinci))
        return 0 if yazildi else 1

    b0_bayatlik()
    bataryayi_kos(a.arac)

    # --- B4 MUTANT: capa + oldurucu kosum (ayri surec, IZOLE kopya).
    with tempfile.TemporaryDirectory(prefix="pruvo-k321-mut-") as kok:
        mutant, not_ = mutant_kur(kok)
        if not mutant:
            kayit("B4 MUTANT capasi TEK", False, not_)
        else:
            kayit("B4 MUTANT capasi TEK", True, not_)
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__), "--arac", mutant,
                 "--yalniz-b1"], capture_output=True, text=True)
            kayit("B4 MUTANT (fatal-satir eksenine donus) B1'i KIRMIZI yakar",
                  r.returncode != 0, "mutant_rc=%d" % r.returncode)

    gecen = sum(1 for _, g, _ in SONUC if g is True)
    dusen = [ad for ad, g, _ in SONUC if g is False]
    olculemeyen = [ad for ad, g, _ in SONUC if g is None]
    print("VAKA=%d GECTI=%d DUSTU=%d OLCULEMEDI=%d"
          % (len(SONUC), gecen, len(dusen), len(olculemeyen)))
    if dusen:
        print("DUSEN: %s" % ", ".join(dusen))
    # OLCULEMEDI (canli ev yok) CI'da MESRUDUR: kopya hash'i basilir, sessiz gecmez.
    print("K321_KABUL=%s" % ("GECTI" if not dusen else "DUSTU"))
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())

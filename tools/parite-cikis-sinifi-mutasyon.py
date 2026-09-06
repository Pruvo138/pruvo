#!/usr/bin/env python3
"""PARITE CIKIS-KODU SINIFLANDIRMASI — MUTASYON BATARYASI (6 Eyl 2026).

NEYI KORUR
──────────
`tools/parite-ege.js` iki YAPISAL OLARAK FARKLI hali tek `exit 2` kovasina dusuruyordu:
  (a) bot kaynagi YOK        -> ORTAM olgusu (pruvo-bot AYRI depodur; GitHub kosucusunun
                                checkout'unda ASLA bulunmaz, Okan'in makinesinde DAIMA bulunur)
  (b) kaynak VAR, disa-aktarim FONKSIYON DEGIL -> GERCEK GERILEME
Sonuc: `hijyen-a3 / Filament paketi kabul testleri` adimi CI'da SUREKLI kirmizi, yerelde
SUREKLI yesildi — kirmizi, gelistiricinin kostugu yerde HIC uretilemiyordu
([[prob-kendi-baglamini-olcer]] · [[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
ONARIM: (a) -> CIKIS_OLCULEMEDI(3) ADIYLA gorunur sebeple · (b) -> CIKIS_KOSULAMADI(2) KIRMIZI.

🔴 BU BATARYANIN VARLIK SEBEBI: onarim TEK YONLU olsaydi bir BYPASS olurdu. Batarya her
mutant icin HEM "hedef kol oldu mu" HEM "ters yon (gerileme) hala KIRMIZI mi" sorularini
AYRI AYRI olcer; "kirmizi geldi" TEK BASINA delil sayilmaz — hangi IDDIANIN dustugu ADIYLA
eslenir ([[isci-yesil-tablo-ic-olcumu-bosaltir]]).

EMNIYET (FILO DERSI, 4 Eyl): mutant CANLI govdede ASLA kosmaz. Her mutant IZOLE bir tmp
kopyada uygulanir; bu dosyada gercek ev yoluna `rm -rf`/`rmtree`/`unlink` YOKTUR — silinen
tek sey, bu betigin KENDI olusturdugu tempfile.mkdtemp() agacidir.

KOSUM:  python3 tools/parite-cikis-sinifi-mutasyon.py
KABUL:  `OLDURULEN=<n>/<n>  KACAN=0  KONTROL=YESIL` + `HUKUM=YESIL` (rc=0).
FAIL-CLOSED: taban yesil degilse rc=3 (OLCULEMEDI) — mutasyon YESIL sayilmaz.
"""
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
EGE = "parite-ege.js"
FILAMENT = "filament-test.py"
ORTAK = "parite-ortak.js"
SOZLESME = "parite-sozlesme-test.py"

# ── PROB FIKSTURLERI ────────────────────────────────────────────────────────────────
# (b) kolunu tetikleyen bot fikstur'u: BES adin BESI DE TANIMLI (yoksa ESM `export`
# ayristirma aninda patlar ve typeof kapisina HIC ULASILMAZ -> yanlis kolu olcerdik),
# ama `urunAra` FONKSIYON DEGIL. Yani "kaynak VAR, sozlesme KIRIK" hali.
BOT_SOZLESMESI_KIRIK = (
    "function katalogIndeksle(){ return null; }\n"
    "const urunAra = 42;\n"                     # <-- FONKSIYON DEGIL: aranan kusur
    "function sorguKavramlari(){ return []; }\n"
    "function nrm(s){ return s; }\n"
    "function markaSorguKanonu(){ return null; }\n"
)
BOT_YOK = "/var/empty/pruvo-bot-YOK/worker/src/index.js"   # VAR OLMAYAN yol (nobetci yuku)


def _kopya_kur():
    """tools/*.js + gerekli .py'leri IZOLE bir agaca kopyalar. Canli agaca DOKUNMAZ."""
    tmp = tempfile.mkdtemp(prefix="parite-cikis-mutant-")
    hedef = os.path.join(tmp, "tools")
    os.makedirs(hedef)
    # 🔴 TUM .js + .py kopyalanir: eksik bir kardes dosya, mutantin degil ORTAMIN
    # urettigi bir kirmizi dogurur ve "olduruldu" iddiasi YANLIS yerden gelirdi
    # ([[mutant-kopyasi-cokerse-izin-okunur]]).
    for ad in os.listdir(TOOLS):
        if ad.endswith(".js") or ad.endswith(".py"):
            kaynak = os.path.join(TOOLS, ad)
            if os.path.isfile(kaynak):
                shutil.copy2(kaynak, os.path.join(hedef, ad))
    return tmp


def _yamala(tmp, dosya, eski, yeni):
    """Mutasyonu IZOLE kopyaya uygular. Capa bulunamazsa CAPA_YOK (mutant ulasmadi)."""
    yol = os.path.join(tmp, "tools", dosya)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    if eski not in metin:
        return False
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin.replace(eski, yeni, 1))
    return True


# ── PROBLAR: her biri TEK bir kolu olcer, ag/katalog KULLANMAZ ──────────────────────
def prob_kaynak_yok(tmp):
    """(a) kolu: bot kaynagi YOK -> beklenen rc=3 (OLCULEMEDI)."""
    ort = dict(os.environ, PARITE_BOT=BOT_YOK)
    p = subprocess.run(["node", os.path.join(tmp, "tools", EGE), "1"],
                       capture_output=True, text=True, env=ort, cwd=tmp)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def prob_sozlesme_kirik(tmp):
    """(b) kolu: kaynak VAR ama disa-aktarim fonksiyon DEGIL -> beklenen rc=2 (KIRMIZI)."""
    sahte = os.path.join(tmp, "sahte-bot.js")
    with open(sahte, "w", encoding="utf-8") as f:
        f.write(BOT_SOZLESMESI_KIRIK)
    ort = dict(os.environ, PARITE_BOT=sahte)
    p = subprocess.run(["node", os.path.join(tmp, "tools", EGE), "1"],
                       capture_output=True, text=True, env=ort, cwd=tmp)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def prob_eslem_fiksturu(tmp):
    """Tuketici eslemesi (filament-test.py) — agsiz, build'siz fikstur."""
    p = subprocess.run(["python3", os.path.join(tmp, "tools", FILAMENT),
                        "--parite-eslem-testi"], capture_output=True, text=True, cwd=tmp)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def prob_sozlesme_testi(tmp):
    """Tek-kaynak sozlesme kapisi (parite-sozlesme-test.py) — agsiz."""
    p = subprocess.run(["python3", os.path.join(tmp, "tools", SOZLESME)],
                       capture_output=True, text=True, cwd=tmp)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


PROBLAR = {
    "KAYNAK_YOK": (prob_kaynak_yok, 3),
    "SOZLESME_KIRIK": (prob_sozlesme_kirik, 2),
    "ESLEM": (prob_eslem_fiksturu, 0),
    "SOZLESME_KAPISI": (prob_sozlesme_testi, 0),
}

# ── MUTANTLAR ───────────────────────────────────────────────────────────────────────
# hedef = mutantin OLDURMESI BEKLENEN prob adi. Batarya AYRICA "baska bir prob da dustu
# mu" diye bakar: dusen prob kumesi hedefi ICERMIYORSA mutant SAPAN sayilir (kirmizinin
# YANLIS yerden gelmesi delil degildir).
MUTANTLAR = [
    ("M1_kaynak_yok_geri_2ye", EGE, "hedef=KAYNAK_YOK",
     "process.exit(ortak.CIKIS_OLCULEMEDI);",
     "process.exit(ortak.CIKIS_KOSULAMADI);", "KAYNAK_YOK"),
    ("M2_sozlesme_kirik_3e_BYPASS", EGE, "hedef=SOZLESME_KIRIK",
     "process.exit(ortak.CIKIS_KOSULAMADI);",
     "process.exit(ortak.CIKIS_OLCULEMEDI);", "SOZLESME_KIRIK"),
    ("M3_ciplak_sayiyla_cikis", EGE, "hedef=SOZLESME_KAPISI",
     "process.exit(ortak.CIKIS_OLCULEMEDI);", "process.exit(3);", "SOZLESME_KAPISI"),
    ("M4_sebep_kolu_silindi", FILAMENT, "hedef=ESLEM",
     'if "BOT KAYNAGI YOK" in c:', 'if "BOT KAYNAGI YOK" in c and False:', "ESLEM"),
    ("M5_exit3_KIRMIZIya", FILAMENT, "hedef=ESLEM",
     "        return (True, PARITE_ATLANDI, parite_sebep_ayikla(cikti))",
     "        return (False, PARITE_KIRMIZI, parite_sebep_ayikla(cikti))", "ESLEM"),
    ("M6_exit2_ATLANDIya_BYPASS", FILAMENT, "hedef=ESLEM",
     '        return (False, PARITE_KIRMIZI,\n'
     '                "test KOSULAMADI (exit 2) — bot kaynagi VAR ama sozlesmesi KIRIK "',
     '        return (True, PARITE_ATLANDI,\n'
     '                "test KOSULAMADI (exit 2) — bot kaynagi VAR ama sozlesmesi KIRIK "',
     "ESLEM"),
    ("M7_sozlesme_tablosu_bayat", ORTAK, "hedef=SOZLESME_KAPISI",
     "· BOT KAYNAGI YOK (kardes depo bu ortamda MEVCUT DEGIL)",
     "· (ucuncu sinif tabloda YAZILI DEGIL)", "SOZLESME_KAPISI"),
]

# KONTROL mutantlari: davranisi DEGISTIRMEZ -> hicbir prob dusmemeli. Dusuyorsa batarya
# yanlis-pozitif uretiyordur ve OLDURME iddialari da guvenilmez olur.
KONTROLLER = [
    ("K1_yorum_eklendi", EGE,
     "const LIMIT = 1000;", "const LIMIT = 1000; // kontrol mutanti: davranis AYNI"),
    ("K2_atil_sabit", FILAMENT,
     "PARITE_GECTI = \"GECTI\"",
     "PARITE_KONTROL_ATIL = \"kontrol mutanti\"\nPARITE_GECTI = \"GECTI\""),
]


def _tabani_olc():
    tmp = _kopya_kur()
    try:
        sonuc = {}
        for ad, (fn, bek) in PROBLAR.items():
            rc, cik = fn(tmp)
            sonuc[ad] = (rc, rc == bek, cik)
        return sonuc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # yalnizca KENDI mkdtemp agacim


def _dusenler(tmp):
    """Bu mutant altinda BEKLENENDEN SAPAN prob adlarini doner."""
    dusen = []
    for ad, (fn, bek) in PROBLAR.items():
        rc, _cik = fn(tmp)
        if rc != bek:
            dusen.append("%s(rc=%s,bek=%s)" % (ad, rc, bek))
    return dusen


def main():
    print("== TABAN (mutasyonsuz IZOLE kopya) ==")
    taban = _tabani_olc()
    for ad, (rc, ok, _c) in taban.items():
        print("  %-16s rc=%-3s beklenen=%-3s %s"
              % (ad, rc, PROBLAR[ad][1], "✅" if ok else "❌"))
    if not all(ok for _rc, ok, _c in taban.values()):
        print("OLCULEMEDI: taban YESIL degil, mutasyon olculemez.")
        return 3

    print("\n== OLDURUCU MUTANTLAR ==")
    oldurulen, kacan, sapan, capa_yok = 0, [], [], []
    for ad, dosya, etiket, eski, yeni, hedef in MUTANTLAR:
        tmp = _kopya_kur()
        try:
            if not _yamala(tmp, dosya, eski, yeni):
                capa_yok.append(ad)
                print("  %-30s CAPA_YOK 🔴 (mutant ULASMADI — capa bayat)" % ad)
                continue
            dusen = _dusenler(tmp)
            hedef_dustu = any(d.startswith(hedef + "(") for d in dusen)
            if not dusen:
                kacan.append(ad)
                print("  %-30s KACTI 🔴 (%s, hicbir prob dusmedi)" % (ad, etiket))
            elif not hedef_dustu:
                sapan.append(ad)
                print("  %-30s SAPAN 🔴 (%s ama dusen: %s)" % (ad, etiket, ", ".join(dusen)))
            else:
                oldurulen += 1
                print("  %-30s OLDURULDU ✅ %s | dusen: %s" % (ad, etiket, ", ".join(dusen)))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n== KONTROL MUTANTLARI (davranis AYNI -> hicbir prob dusmemeli) ==")
    kontrol_kirli = []
    for ad, dosya, eski, yeni in KONTROLLER:
        tmp = _kopya_kur()
        try:
            if not _yamala(tmp, dosya, eski, yeni):
                kontrol_kirli.append(ad + "(CAPA_YOK)")
                print("  %-30s CAPA_YOK 🔴" % ad)
                continue
            dusen = _dusenler(tmp)
            if dusen:
                kontrol_kirli.append(ad)
                print("  %-30s KIRLI 🔴 (yanlis-pozitif: %s)" % (ad, ", ".join(dusen)))
            else:
                print("  %-30s YESIL ✅ (imza AYNI)" % ad)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "-" * 78)
    print("OLDURULEN=%d/%d  KACAN=%d  SAPAN=%d  CAPA_YOK=%d  KONTROL=%s"
          % (oldurulen, len(MUTANTLAR), len(kacan), len(sapan), len(capa_yok),
             "KIRLI" if kontrol_kirli else "YESIL"))
    hukum = (oldurulen == len(MUTANTLAR) and not kacan and not sapan
             and not capa_yok and not kontrol_kirli)
    print("HUKUM=%s" % ("YESIL" if hukum else "KIRMIZI"))
    return 0 if hukum else 1


if __name__ == "__main__":
    sys.exit(main())

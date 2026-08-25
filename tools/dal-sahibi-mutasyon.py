#!/usr/bin/env python3
"""K50 MUTASYON TAKIMI — olcut ④: HEDEF-KOL ATIFLI mutant.

SORU (K182 dersi): kabul bataryasi yesil yaniyor da, gercekten SAHIPLIK KOLU mu
yarisi kapatiyor, yoksa vaka baska bir sebeple mi geciyor? Cevabi tek yol verir:
kolu OLDUR, fikstur KIRMIZI yansin. Kirmizi yanmiyorsa kol tasiyici DEGILDIR.

Her mutant, oldurdugu kolu ADIYLA atfeder ve HANGI vakanin kirmizi yanmasi
gerektigini ONCEDEN civiler ([[kapanis-olcutu-onceden-civilenir]]). Ayrica:

  * KONTROL KOLU: mutasyonsuz KOPYA da kosulur — yesil yanmali. Yanmazsa hukum
    "mutant yakalandi" DEGIL, "batarya zaten kirmizi" olur ve tum tur ROC'suzdur
    ([[sahte-bagimligin-sekli-negatif-blogu-kutsar]] ile ayni sinif).
  * CAPA NOBETI: her mutasyonun capasi kaynakta TAM 1 kez gecmeli. Gecmiyorsa
    HUKUM=CAPA-COKTU — "mutant hayatta kaldi" diye okunmaz
    ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
  * IZ AYRIMI: her mutantin kirmizi-yaktigi VAKA KUMESI basilir; iki mutant ayni
    izi birakiyorsa batarya o iki kolu birbirinden AYIRT EDEMIYOR demektir.

KOSUM: python3 tools/dal-sahibi-mutasyon.py
Cikis: 0 = KONTROL yesil + tum mutantlar yakalandi; 1 = aksi.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(BURASI, "dal_sahibi.py")
FIKSTUR = os.path.join(BURASI, "dal-sahibi-test.py")

# (ad, kol_atfi, capa, yerine, kirmizi_yanmasi_gereken_vakalar, olcut)
MUTANTLAR = [
    ("M1_SAHIP_KOLU_HEP_BEN",
     "_sahip_mi() — 'kayitli sahip cagiranla ayni mi' kolu",
     "def _sahip_mi(kayit, sahip):\n",
     "def _sahip_mi(kayit, sahip):\n    return True  # MUTANT KOL:SAHIP\n",
     ["K50-2-YARIS-IKINCI-RED"], "②"),

    ("M2_BAYAT_KOLU_HEP_BAYAT",
     "_bayat_mi() — kalp atisi tavani kolu (hep BAYAT)",
     "def _bayat_mi(kayit, simdi):\n",
     "def _bayat_mi(kayit, simdi):\n    return True  # MUTANT KOL:BAYAT-HEP-TRUE\n",
     ["K50-2-YARIS-IKINCI-RED"], "②"),

    ("M3_BAYAT_KOLU_HIC_BAYAT_DEGIL",
     "_bayat_mi() — kalp atisi tavani kolu (hic bayat olmaz = SONSUZ KILIT)",
     "def _bayat_mi(kayit, simdi):\n",
     "def _bayat_mi(kayit, simdi):\n    return False  # MUTANT KOL:BAYAT-HEP-FALSE\n",
     ["K50-7-BAYAT-DEVIR"], "⑤"),

    ("M4_KILIT_KOLU_YOK",
     "_kilit_al() — kayit dosyasi uzerindeki ozel flock (es zamanlilik kolu)",
     "def _kilit_al(fd):\n",
     "def _kilit_al(fd):\n    return True  # MUTANT KOL:KILIT (flock YOK)\n",
     ["K50-3-GERCEK-YARIS"], "②"),

    ("M5_BOZUK_KAYIT_FAIL_OPEN",
     "_bozuk_bayat_mi() — bozuk kaydin fail-CLOSED kolu",
     "def _bozuk_bayat_mi(yol, simdi, tavan_sn):\n",
     "def _bozuk_bayat_mi(yol, simdi, tavan_sn):\n    return True  # MUTANT KOL:BOZUK-FAIL-OPEN\n",
     ["K50-10-BOZUK-TAZE-SAHIPLI"], "YASAK:fail-open"),

    ("M6_ACIK_DEVIR_GEREKCESIZ",
     "komut_devral() — acik devralmanin GEREKCE zorunlulugu kolu",
     '    if not (args.gerekce or "").strip():\n',
     "    if False:  # MUTANT KOL:DEVIR-GEREKCE\n",
     ["K50-9-GEREKCESIZ-DEVIR-RED"], "⑤"),

    ("M7_ORTAK_KOK_WORKTREE_BASINA",
     "_git_ortak_dizin() — kaydi TUM worktree'ler icin TEK koke cozen kol "
     "(oldurulunce kayit worktree BASINA ayrisir = K50'nin ta kendisi)",
     "def _git_ortak_dizin(baslangic):\n",
     "def _git_ortak_dizin(baslangic):\n"
     '    return os.path.join(os.path.abspath(baslangic), ".git")  # MUTANT KOL:ORTAK-KOK\n',
     ["K50-14-ORTAK-KOK-TEK"], "①/②"),
]

YARIS_TEKRAR = 3  # es zamanlilik mutanti (M4) icin: yesil gorursen tekrar dene


def fiksturu_kos(arac_yolu):
    ortam = dict(os.environ)
    ortam["PRUVO_DAL_SAHIBI_YOL"] = arac_yolu
    ortam.pop("PRUVO_DAL_SAHIP_KOK", None)
    p = subprocess.run([sys.executable, FIKSTUR, "--json"],
                       capture_output=True, text=True, env=ortam, timeout=300)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"toplam": 0, "gecen": 0, "vakalar": {},
                "hata": (p.stderr or p.stdout)[-800:]}


def kirmizilar(rapor):
    return sorted(ad for ad, v in (rapor.get("vakalar") or {}).items() if not v.get("gecti"))


def ana():
    with open(ARAC, encoding="utf-8") as f:
        kaynak = f.read()

    tmp = tempfile.mkdtemp(prefix="k50-mutasyon-")
    satirlar = []
    hata_var = False
    izler = {}
    yakalanan = 0
    kontrol_yesil = False
    iz_hukmu = "OLCULMEDI"
    try:
        # ---- KONTROL KOLU: mutasyonsuz kopya YESIL yanmali
        kontrol_yolu = os.path.join(tmp, "kontrol_dal_sahibi.py")
        with open(kontrol_yolu, "w", encoding="utf-8") as f:
            f.write(kaynak)
        kontrol = fiksturu_kos(kontrol_yolu)
        kontrol_yesil = kontrol.get("toplam", 0) > 0 and kontrol["gecen"] == kontrol["toplam"]
        satirlar.append("KONTROL  %s  %s/%s  %s" % (
            "YESIL" if kontrol_yesil else "KIRMIZI",
            kontrol.get("gecen"), kontrol.get("toplam"),
            "" if kontrol_yesil else "kirmizi=%s %s" % (kirmizilar(kontrol),
                                                        kontrol.get("hata", ""))))
        if not kontrol_yesil:
            hata_var = True

        # ---- MUTANTLAR
        yakalanan = 0
        for ad, kol_atfi, capa, yerine, hedef_vakalar, olcut in MUTANTLAR:
            adet = kaynak.count(capa)
            if adet != 1:
                satirlar.append("%-32s CAPA-COKTU  capa %d kez gecti (1 olmali) — KOL=%s"
                                % (ad, adet, kol_atfi))
                hata_var = True
                continue
            mutant_yolu = os.path.join(tmp, ad.lower() + ".py")
            with open(mutant_yolu, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa, yerine, 1))

            rapor = fiksturu_kos(mutant_yolu)
            kirmizi = kirmizilar(rapor)
            deneme = 1
            while (not set(hedef_vakalar) & set(kirmizi)) and deneme < YARIS_TEKRAR:
                # es zamanlilik mutanti tek turda sansla yesil kalabilir; tekrarla
                deneme += 1
                rapor = fiksturu_kos(mutant_yolu)
                kirmizi = kirmizilar(rapor)

            tuttu = bool(set(hedef_vakalar) & set(kirmizi))
            izler[ad] = tuple(kirmizi)
            if tuttu:
                yakalanan += 1
            else:
                hata_var = True
            satirlar.append(
                "%-32s %-8s olcut=%-14s hedef=%s iz=%s deneme=%d\n        KOL=%s"
                % (ad, "YAKALANDI" if tuttu else "KACTI", olcut,
                   ",".join(hedef_vakalar), kirmizi or "[]", deneme, kol_atfi))

        # ---- IZ AYRIMI
        ters = {}
        for ad, iz in izler.items():
            ters.setdefault(iz, []).append(ad)
        ayni = [v for v in ters.values() if len(v) > 1]
        iz_hukmu = "DOGRU" if not ayni else "AYIRT-EDILEMEYEN " + str(ayni)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # DISK KURALI: ureten temizler

    print("K50 MUTASYON TAKIMI — arac=%s" % ARAC)
    for s in satirlar:
        print("  " + s)
    print("K50 MUTANT=%d/%d KONTROL=%s IZ_AYRIMI=%s HUKUM=%s"
          % (yakalanan, len(MUTANTLAR), "YESIL" if kontrol_yesil else "KIRMIZI",
             iz_hukmu, "KIRMIZI" if hata_var else "YESIL"))
    return 1 if hata_var else 0


if __name__ == "__main__":
    sys.exit(ana())

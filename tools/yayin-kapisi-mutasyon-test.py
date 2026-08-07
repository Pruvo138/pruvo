#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN KAPISI — CURUTME + MUTASYON SURUCUSU (elle kosar; ag YOK, D1 YOK, wrangler YOK)

    python3 tools/yayin-kapisi-mutasyon-test.py
    python3 tools/yayin-kapisi-mutasyon-test.py --eski-surum <git-ref>

🔴 ADI NEDEN `-test.py`: `tools/ci-kapsam-test.py` kesfi YALNIZ `<ad>-test.py` /
`test-<ad>.py` / `<ad>-kapisi.py` adlarina bakar. `-mutasyon.py` adiyla bu dosya
kapsam kapisina GORUNMUYORDU (ne kosulan ne KAPSAMSIZ) — yani sessizce curuyebilirdi.
Artik GORUNUR ve IZIN_LISTESI'nde OLCULMUS gerekceyle muaf: A kolu `git show <sha>`
ile ONARIM ONCESI surumu ister, CI'nin sig checkout'unda (fetch-depth varsayilan 1)
o commit ERISILEMEZ -> yapisal CI-kirmizi (R_YOL/R_FTS5 sinifi).

NEDEN VAR ([[mutasyon-kaniti-yeniden-uretilebilir]]): "batarya kostu, hepsi kirmizi yandi"
ANLATIMI KANIT DEGILDIR. Bu surucu repoda durur; kabul, cikis kodu degil BASILAN
IDDIA SAYISI + ISARET SARTIDIR (her mutant AYRI ve BEKLENEN yonde dusmeli).

IKI IS YAPAR:

A. ESKI DAVRANISIN CURUTULMESI (iki yonlu isaret sarti)
   ONARIM ONCESI surumu git'ten cikarir ve AYNI fiksturu iki surume verir:
     fikstur "TASLAK YOK + CANLI KATALOG BOS":
       eski surum -> rc=0 (`success`) ve SIFIR HTTP istegi  == KOR YESIL
       yeni surum -> HUKUM: OLCULEMEDI / BOS YUZEY          == kor yesil KAPANDI
     fikstur "TASLAK YOK + CANLI KATALOGDA 404 VEREN SAYFA":
       eski surum -> rc=0 (arizayi HIC GORMEZ)
       yeni surum -> rc=1 (KIRMIZI)
   Fikstur id'leri UYDURMADIR; gercek katalog/tedarikci/kova adi GECMEZ.

B. MUTASYON BATARYASI (yeni surumun iddialari FIILEN olduruyor mu?)
   Yeni dosyanin bir KOPYASINA tek tek mutasyon uygular ve `--kendini-test` kosar.
   Her mutant AYRI bir iddiayi dusurmeli (KIRMIZI), KONTROL mutanti YESIL kalmali.
   🔴 DISKE YAZMA TUZAKLARI ([[mutasyon-diske-yazma-tuzagi]] · [[mutasyon-bytecode-onbellegi]]):
   her mutant BENZERSIZ dizine + BENZERSIZ dosya adina yazilir, `python3 -B` ile
   (bytecode yazilmaz) kosulur ve mutasyonun FIILEN uygulandigi (kaynak degisti +
   beklenen jeton yok) yazmadan SONRA diskten OKUNARAK dogrulanir.
"""
import argparse
import contextlib
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEDEF = os.path.join(KOK, "tools", "yayin-kapisi.py")
# Onarimdan HEMEN ONCEKI commit (bu dalin tabani). Dal main'e alindiktan sonra da
# gecerli kalir: ref bir SHA'dir, dal adi degil. (bf560ea8 ile bu commit arasinda
# tools/yayin-kapisi.py BAYT AYNIDIR — olculdu: `git diff` bos.)
ESKI_SURUM = "db836975"


def git_cikar(ref, hedef_yol):
    """Bir git ref'inden tools/yayin-kapisi.py'yi cikar. Doner: (True, yol) | (False, sebep)"""
    p = subprocess.run(["git", "-C", KOK, "show", ref + ":tools/yayin-kapisi.py"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return False, "git show basarisiz (%s): %s" % (ref, p.stderr.strip()[:200])
    with open(hedef_yol, "w", encoding="utf-8") as f:
        f.write(p.stdout)
    return True, hedef_yol


def modul_yukle(yol, ad):
    import importlib.util
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# FIKSTUR — UYDURMA veri (gercek katalog id'si / tedarikci / kova adi YOK)
# ═══════════════════════════════════════════════════════════════════════════════
class SahteD1:
    def __init__(self, satirlar):
        self.satirlar = dict(satirlar)
        self.yazilan_sql = []

    def kolon_var_mi(self, tablo, kolon):
        return True

    @staticmethod
    def q(s):
        return "'" + str(s).replace("'", "''") + "'"

    def sorgu(self, sql):
        if "IN (" in sql:
            secili = [i for i in self.satirlar if self.q(i) in sql]
            return [{"results": [{"id": i} for i in sorted(secili)
                                 if int(self.satirlar[i] or 0) == 0]}]
        if "WHERE yayinda=0" in sql:
            return [{"results": [{"id": i} for i, v in sorted(self.satirlar.items())
                                 if int(v or 0) == 0]}]
        raise AssertionError("beklenmeyen sorgu: " + sql)

    def dosya_calistir(self, sql):
        self.yazilan_sql.append(sql)
        for i in list(self.satirlar):
            if self.q(i) in sql and int(self.satirlar[i] or 0) == 0:
                self.satirlar[i] = 1


UYDURMA_CANLI = ["uydurma-parca-%02d" % i for i in range(12)]


def eski_kos(m, d1_satirlari, canli_liste, kod_haritasi):
    """ESKI surumu fiksturle kosar. Ag katmani MONKEYPATCH edilir; gercek istek ATILMAZ
    ve ATILMAYA CALISILDIGI SAYILIR (kor yesil kaniti = 0 istek)."""
    istekler = []

    def sahte_canli_getir(yol, ikili=False):
        istekler.append(yol)
        if yol == "/urunler.json":
            import json
            return 200, json.dumps([{"id": i} for i in canli_liste]).encode("utf-8")
        return kod_haritasi.get(yol, 404), b""

    m.canli_getir = sahte_canli_getir
    m.yerel_idler = lambda: list(canli_liste) + [i for i in d1_satirlari]
    m.DENEME = 1
    m.DENEME_BEKLE = 0
    d1 = SahteD1(d1_satirlari)
    import contextlib
    import io
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = m.komut_yayinla(d1, "curutme")
    return rc, tampon.getvalue(), istekler, d1


def yeni_kos(m, d1_satirlari, canli_liste, kod_haritasi, yas=0):
    """YENI surumu AYNI fiksturle kosar (enjekte edilen IO dikisleriyle).
    prob CIKTI SEKLI gercek yol_kodu()'yla ayni: (kod, yas_sn, govde_isareti)."""
    istekler = []

    def prob(yol, beklenen=200, uid=None):
        istekler.append(yol)
        kod = kod_haritasi.get(yol, 404)
        return kod, None, (True if kod == 200 else None)

    d1 = SahteD1(d1_satirlari)
    import contextlib
    import io
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = m.komut_yayinla(d1, "curutme", prob=prob,
                             canli_kaynak=(lambda: (list(canli_liste), None)),
                             yerel_kaynak=(lambda: list(canli_liste) + list(d1_satirlari)),
                             yas_kaynak=(lambda: yas))
    return rc, tampon.getvalue(), istekler, d1


# ═══════════════════════════════════════════════════════════════════════════════
# MUTASYON BATARYASI
# ═══════════════════════════════════════════════════════════════════════════════
# (ad, [(eski_metin, yeni_metin), ...], beklenen)   beklenen: "KIRMIZI" | "YESIL"(kontrol)
# 🔴 COKLU EDIT DESTEKLI: bazi eksenler ancak IKI yer birlikte bozulunca ayirt edici olur
# (or. "gecici kod listesi" tek basina bozulsa MODELLENMEYEN-kod dali onu yine GECICI
# yapardi -> beyan edilmis survivor). Kac edit uygulandigi raporda gecer.
MUTANTLAR = [
    ("M-A BOS YUZEY hali silinir (eski kor yesil GERI GELIR)",
     [('        return (HUKUM_OLCULEMEDI,\n                "BOS YUZEY:',
       '        return (HUKUM_YESIL,\n                "BOS YUZEY:')], "KIRMIZI"),
    ("M-B nobet satiri (404 tanima izni) kaldirilir",
     [('    if nobet_id:\n        ekle(KAYNAK_NOBET, nobet_id, 404, False)',
       '    if False:\n        ekle(KAYNAK_NOBET, nobet_id, 404, False)')], "KIRMIZI"),
    ("M-C adres bicimi `.html`'e cevrilir (sahte 404 tuzagi)",
     [('    return "/urun/" + uid + "/"',
       '    return "/urun/" + uid + ".html"')], "KIRMIZI"),
    ("M-D gecici/olculemeyen olcum YESIL sayilir (sessiz yesil)",
     [('    if gecici:\n        o, g = gecici[0]',
       '    if gecici and False:\n        o, g = gecici[0]')], "KIRMIZI"),
    ("M-E nobet satiri katalog POZITIFI sayilir (yuzey sisirilir)",
     [('               if s == SINIF_OK and o.get("katalog") and o.get("alinan") == 200\n'
       '               and o.get("govde") is True]',
       '               if s == SINIF_OK and o.get("alinan") == 200\n'
       '               and o.get("govde") is True]')], "KIRMIZI"),
    ("M-F canli katalogun EN YENI kolu kaldirilir (yuzey daralir)",
     [("YENI_N = 5 ", "YENI_N = 0 ")], "KIRMIZI"),
    ("M-G gercek kusur gecici gurultuye yenilir (sira ters)",
     [('    if kirmizi:\n        o, g = kirmizi[0]',
       '    if kirmizi and not gecici:\n        o, g = kirmizi[0]')], "KIRMIZI"),
    # ── 2. TUR: rc SEMANTIGI + gecici/gercek ayrimi ────────────────────────────────
    ("M-I OLCULEMEDI rc'si 0'a dondurulur (kor yesil JOB biriminde GERI GELIR)",
     [("RC_OLCULEMEDI = 2", "RC_OLCULEMEDI = 0")], "KIRMIZI"),
    ("M-J canli-YENI rollout affi TAMAMEN kaldirilir (taze artefaktta bile KIRMIZI)",
     [('    if int(artefakt_yas) < ROLLOUT_ESIK_SN:',
       '    if False and int(artefakt_yas) < ROLLOUT_ESIK_SN:')], "KIRMIZI"),
    ("M-K MODELLENMEYEN kod dali KIRMIZI'ya cevrilir (yanlis-pozitif kapisi acilir)",
     [('    return SINIF_GECICI, "MODELLENMEYEN kod %s (fail-toward-NOTR)" % alinan',
       '    return SINIF_KIRMIZI, "MODELLENMEYEN kod %s (fail-toward-NOTR)" % alinan')],
     "KIRMIZI"),
    ("M-L gecici KOD LISTESI + 5xx dali dusurulur VE fallback KIRMIZI olur (403/429/503 "
     "artik gercek kusur sayilir) [2 edit]",
     [('    if alinan in GECICI_KODLAR or 500 <= int(alinan) <= 599:',
       '    if False and (alinan in GECICI_KODLAR or 500 <= int(alinan) <= 599):'),
      ('    return SINIF_GECICI, "MODELLENMEYEN kod %s (fail-toward-NOTR)" % alinan',
       '    return SINIF_KIRMIZI, "MODELLENMEYEN kod %s (fail-toward-NOTR)" % alinan')],
     "KIRMIZI"),
    ("M-M af TASLAK ve KESIT kollarina da yayilir (kayip kirmizi geri kaybolur)",
     [('    if o.get("kaynak") != KAYNAK_YENI:',
       '    if o.get("kaynak") not in (KAYNAK_YENI, KAYNAK_TASLAK, KAYNAK_KESIT):')],
     "KIRMIZI"),
    # ── 3. TUR: kanit kaybi · yasa bagli af · soft-404 · N siniri · kullanim kodu ───
    ("M-O SINIRSIZ AF geri gelir (yas esigi hic sorgulanmaz -> KALICI 404 ortulur)",
     [('    if int(artefakt_yas) < ROLLOUT_ESIK_SN:',
       '    if True or int(artefakt_yas) < ROLLOUT_ESIK_SN:')], "KIRMIZI"),
    ("M-P yas OLCULEMEZ iken AF VERILIR (fail-open)",
     [('    if artefakt_yas is None:\n        return (SINIF_KIRMIZI,',
       '    if artefakt_yas is None:\n        return (SINIF_GECICI,')], "KIRMIZI"),
    ("M-Q SOFT-404 gormezden gelinir (200 + hata govdesi YESIL sayilir)",
     [('            if isaret is False:', '            if isaret is False and False:')],
     "KIRMIZI"),
    ("M-R govde OLCULEMEDI hali 'saglam' sayilir (fail-open)",
     [('            if isaret is None:', '            if isaret is None and False:')],
     "KIRMIZI"),
    ("M-S kanonik capa sarti kaldirilir (her govde 'gercek urun sayfasi' olur)",
     [('    return urun_capasi(uid, uretici).encode("utf-8") in govde',
       '    return True')], "KIRMIZI"),
    ("M-T KOVA SINIRI geri alinir (yeni-kova tum katalogu yutar -> kucuk katalogda "
     "KIRMIZI sinifi ULASILAMAZ olur)",
     [('    yeni_adet = min(max(0, yeni_n), max(0, n - 1))',
       '    yeni_adet = min(max(0, yeni_n), n)')], "KIRMIZI"),
    ("M-U KANIT KAYBI geri gelir (dokum `finally` icinde CAGRILMAZ)",
     [('            dokum_bas(d["olcumler"], d["hukum"], d["sebep"], d["sayac"],',
       '            None and dokum_bas(d["olcumler"], d["hukum"], d["sebep"], d["sayac"],')],
     "KIRMIZI"),
    ("M-V istisna rc'si 1'e COKER (wrangler arizasi 'site bozuk' sayilir)",
     [('        d["hukum"], d["rc"] = HUKUM_OLCULEMEDI, RC_OLCULEMEDI\n'
       '        d["ariza"] = "%s: %s" % (type(e).__name__, e)',
       '        d["hukum"], d["rc"] = HUKUM_KIRMIZI, RC_KIRMIZI\n'
       '        d["ariza"] = "%s: %s" % (type(e).__name__, e)')], "KIRMIZI"),
    ("M-W KULLANIM hatasi kodu OLCULEMEDI ile ayni kovaya geri konur",
     [("RC_KULLANIM = 64", "RC_KULLANIM = 2")], "KIRMIZI"),
    # ── 4. TUR: capa TEK KAYNAK · yas birimi (age) · esik davranissal capasi ───────
    ("M-X CAPA IKIZI GERI GELIR (uretim yolu build.py'yi DEGIL yerel hesabi kullanir)",
     [('    if uretici is None:\n        uretici, _ = build_capa_ureticisi()',
       '    if uretici is None:\n        uretici = None')], "KIRMIZI"),
    ("M-Y CAPA YEDEGI AYRISIR (yerel_capa bozulur -> esitlik iddiasi KIRMIZI yakar)",
     [('    return SITE + urun_yolu(uid)', '    return SITE + "/u/" + uid')],
     "KIRMIZI"),
    ("M-Z1 `age` TERIMI KALDIRILIR (yas eksik olculur -> af fail-open)",
     [('    return max(0, int((d - m).total_seconds()) + age_sn)',
       '    return max(0, int((d - m).total_seconds()))')], "KIRMIZI"),
    ("M-Z2 `age` YOK hali 0 DEGIL None sayilir (yaygin hal fail-closed'a devrilir)",
     [('        return 0, "age YOK -> 0 varsayildi"',
       '        return None, "age YOK -> 0 varsayildi"')], "KIRMIZI"),
    ("M-Z3 BOZUK `age` 0 sayilir (fail-open: olcemedigini 'iyi' sanar)",
     [('        return None, "age BOZUK (sayi degil: %r) -> yas OLCULEMEZ '
       '(fail-closed)" % ham[:40]',
       '        return 0, "age BOZUK (sayi degil: %r) -> yas OLCULEMEZ '
       '(fail-closed)" % ham[:40]')], "KIRMIZI"),
    ("M-Z4 ESIK 900 -> 3600 (sinir iddiasi GECER, DAVRANISSAL capa dusmeli)",
     [("ROLLOUT_ESIK_SN = 900", "ROLLOUT_ESIK_SN = 3600")], "KIRMIZI"),
    ("M-Z5 `age` notu dokumde BASILMAZ (olcum beyani gizlenir)",
     [('    print("YAS TERIMI (age): %s" % (yas_notu or "OLCULEMEDI (not YOK)"))',
       '    pass  # YAS TERIMI satiri kaldirildi')], "KIRMIZI"),
    ("M-N KONTROL: yalniz dokum basliginin metni degisir (anlam AYNI)",
     [('──── OLCUM DOKUMU (yoklanan sayfa yuzeyi · kol bazinda) ────',
       '──── OLCUM DOKUMU / yoklanan sayfa yuzeyi / kol bazinda ────')], "YESIL"),
]


def mutant_kos(kaynak, ad, editler, sira, tmp_kok):
    """Mutasyon(lar)i BENZERSIZ dizine yazip `python3 -B` ile kosar.
    editler: [(eski_metin, yeni_metin), ...] — her deseni TAM 1 kez bulmak SART.
    Doner: (uygulandi_mi, rc, son_satir, sebep, tamamlandi_mi, dusen_iddia)"""
    mutant = kaynak
    for eski, yeni in editler:
        if mutant.count(eski) != 1:
            return (False, None, "", "desen %d kez bulundu (1 olmali) -> mutasyon "
                    "UYGULANMADI: %r" % (mutant.count(eski), eski[:60]), False, 0, frozenset())
        mutant = mutant.replace(eski, yeni)
    if mutant == kaynak:
        return False, None, "", "kaynak DEGISMEDI", False, 0, frozenset()
    # 🔴 SADIK AGAC: kapi kendi KOK'unu `__file__`den turetir ve `KOK/tools/build.py`yi
    # (capanin TEK KAYNAGI) FIILEN yukler. Mutant ciplak bir tmp dizinine yazilirsa
    # build.py BULUNAMAZ ve capa iddialari HER mutantta (KONTROL dahil) duser — yani
    # sinyal ortama bagli sahte kirmiziya doner ([[parite-testi-olculemedi-basiyor]]).
    # Cozum: mutant `<dizin>/tools/` icine yazilir ve gercek tools/ icerigi oraya
    # SYMLINK'lenir (mutasyon YALNIZ kapinin kopyasinda; digerleri degismez).
    dizin = os.path.join(tmp_kok, "mutant-%02d-%s" % (sira, hashlib.sha1(
        (ad + repr(editler)).encode("utf-8")).hexdigest()[:8]))
    # OLCULDU: build.py'nin IMPORT ZINCIRI (build -> marka_model_build -> model_kanon)
    # `KOK/index.html`i OKUR. Yani sadik agac yalniz tools/ degil KOK'un ust duzeyini de
    # icermeli; yoksa import FileNotFoundError verir ve capa iddialari ORTAM yuzunden
    # duser (mutasyonsuz taban dahil).
    araclar = os.path.join(dizin, "tools")
    os.makedirs(araclar, exist_ok=True)
    for giris in os.listdir(KOK):
        if giris in (".git", "tools"):
            continue
        with contextlib.suppress(OSError):
            os.symlink(os.path.join(KOK, giris), os.path.join(dizin, giris))
    gercek_araclar = os.path.join(KOK, "tools")
    for giris in os.listdir(gercek_araclar):
        hedef = os.path.join(araclar, giris)
        if not os.path.exists(hedef):
            with contextlib.suppress(OSError):
                os.symlink(os.path.join(gercek_araclar, giris), hedef)
    yol = os.path.join(araclar, "kapi_m%02d.py" % sira)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(mutant)
    # 🔴 DISKTEN GERI OKU: mutasyonun FIILEN uygulandigini iddiadan degil dosyadan dogrula.
    # (Ayni uzunluk / ayni saniye / __pycache__ tuzaklari icin: benzersiz dizin+ad, -B.)
    with open(yol, encoding="utf-8") as f:
        diskteki = f.read()
    for eski, yeni in editler:
        if eski in diskteki or yeni not in diskteki:
            return (False, None, "", "diskteki kopyada mutasyon YOK (yazma tuzagi): %r"
                    % eski[:60], False, 0, frozenset())
    p = subprocess.run([sys.executable, "-B", yol, "--kendini-test"],
                       capture_output=True, text=True)
    satirlar = [s for s in p.stdout.strip().splitlines() if s.strip()]
    dusen = [s.strip() for s in p.stdout.splitlines() if "KALDI " in s]
    # 🔴 COKME KIRMIZIYLA KARISMASIN ([[mutasyon-kaniti-yeniden-uretilebilir]]):
    # mutantin rc!=0 olmasi yetmez — suite SONUNA KADAR kosmus ("SONUC:" basmis) ve
    # EN AZ BIR IDDIA fiilen DUSMUS olmali. Aksi halde mutant "COKTU" sayilir.
    tamamlandi = "SONUC:" in p.stdout
    # 🔴 IDDIA KIMLIKLERI: "ayni iddia kumesine dusen mutant cifti" olculebilsin
    # ([[beyan-edilmis-survivor]]: iki mutant ayni kumeyi dusuruyorsa ikisi AYRI eksen
    # DEGILDIR ve "N/N" sayisi eksen sayisini SISIRIR).
    kimlikler = frozenset(d.split("KALDI ", 1)[1].split()[0] for d in dusen
                          if "KALDI " in d)
    return (True, p.returncode, (satirlar[-1] if satirlar else ""),
            "; ".join(d.split("—")[0].strip() for d in dusen[:3]), tamamlandi,
            len(dusen), kimlikler)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eski-surum", default=ESKI_SURUM)
    a = ap.parse_args()

    tmp_kok = tempfile.mkdtemp(prefix="yayin-kapisi-mutasyon-")
    gecen, kalan = [0], [0]

    def dogrula(ad, kosul, detay=""):
        if kosul:
            gecen[0] += 1
            print("  GECTI " + ad)
        else:
            kalan[0] += 1
            print("  KALDI " + ad + (" — " + str(detay) if detay else ""))

    try:
        with open(HEDEF, encoding="utf-8") as f:
            yeni_kaynak = f.read()

        # ── A. ESKI DAVRANISIN CURUTULMESI ────────────────────────────────────────
        print("A. ESKI DAVRANIS (%s) vs YENI — AYNI FIKSTUR" % a.eski_surum)
        eski_yol = os.path.join(tmp_kok, "eski_kapi.py")
        ok, sebep = git_cikar(a.eski_surum, eski_yol)
        if not ok:
            print("  OLCULEMEDI: %s" % sebep)
            kalan[0] += 1
        else:
            with open(eski_yol, encoding="utf-8") as f:
                eski_kaynak = f.read()
            dogrula("A0 iki surum FARKLI dosyadir (bayat kiyas nobeti)",
                    hashlib.sha256(eski_kaynak.encode()).hexdigest()
                    != hashlib.sha256(yeni_kaynak.encode()).hexdigest())
            dogrula("A1 eski surumde BOS YUZEY hali HIC YOK (onarim gercekten yeni)",
                    "BOS YUZEY" not in eski_kaynak and "HUKUM_OLCULEMEDI" not in eski_kaynak)
            eski = modul_yukle(eski_yol, "eski_kapi")
            yeni = modul_yukle(HEDEF, "yeni_kapi")

            # FIKSTUR 1: taslak YOK + canli katalog BOS.
            rc_e, cikti_e, istek_e, _ = eski_kos(eski, {}, [], {})
            dogrula("A2 ESKI + 'taslak yok, katalog bos' -> rc=0 (SUCCESS)", rc_e == 0, rc_e)
            dogrula("A3 ESKI + ayni fikstur -> SIFIR HTTP istegi (hicbir sayfa OLCULMEDI)",
                    istek_e == [], istek_e)
            dogrula("A4 ESKI ciktisi 'TASLAK yok ... exit 0' der; 'OLCULEMEDI' DEMEZ",
                    "TASLAK yok" in cikti_e and "OLCULEMEDI" not in cikti_e,
                    cikti_e.strip()[:160])
            rc_y, cikti_y, istek_y, _ = yeni_kos(yeni, {}, [], {})
            dogrula("A5 YENI + AYNI fikstur -> HUKUM: OLCULEMEDI / BOS YUZEY basar",
                    "BOS YUZEY" in cikti_y and yeni.HUKUM_OLCULEMEDI in cikti_y,
                    cikti_y.strip()[-200:])
            dogrula("A6 YENI + ayni fikstur -> 'KATALOG POZITIF DOGRULANAN SAYFA: 0' basar",
                    "KATALOG POZITIF DOGRULANAN SAYFA: 0" in cikti_y)
            # 🔴 JOB BIRIMI: hukum jetonunu hicbir is akisi tuketmiyor -> karar yuzeyi rc.
            # Onarimin "artik success DEGIL" iddiasi ANCAK burada dogrulanabilir.
            dogrula("A6b JOB BIRIMI: ESKI rc=0 (`success`) · YENI rc=2 (OLCULEMEDI) — "
                    "degisen yalniz stdout metni DEGIL, CIKIS KODU",
                    rc_e == 0 and rc_y == 2, (rc_e, rc_y))
            dogrula("A6c JOB BIRIMI: uc jeton -> uc AYRI rc (yeni surumde)",
                    (yeni.hukum_cikis_kodu(yeni.HUKUM_YESIL),
                     yeni.hukum_cikis_kodu(yeni.HUKUM_KIRMIZI),
                     yeni.hukum_cikis_kodu(yeni.HUKUM_OLCULEMEDI)) == (0, 1, 2),
                    [yeni.hukum_cikis_kodu(h) for h in (yeni.HUKUM_YESIL,
                                                        yeni.HUKUM_KIRMIZI,
                                                        yeni.HUKUM_OLCULEMEDI)])
            dogrula("A6d ESKI surumde rc=2 (OLCULEMEDI) hali HIC YOK",
                    "RC_OLCULEMEDI" not in eski_kaynak)

            # FIKSTUR 2: taslak YOK + canli katalogda 404 veren sayfa.
            # 🔴 KIRILAN ID PLANDAN TURETILIR (sabit indeks YAZILMAZ): kova kurali
            # degisince sabit indeks "hic yoklanmayan" bir sayfaya kayar ve fikstur KOR
            # olur — bu tam olarak 3. turda OLCULDU. Ayrica KESIT kolu secilir: o kolda
            # ROLLOUT AFFI YOKTUR, yani 404 dogrudan KIRMIZI olmali.
            _plan = yeni.olcum_plani([], UYDURMA_CANLI)
            _kesit = [o["id"] for o in _plan if o["kaynak"] == yeni.KAYNAK_KESIT]
            dogrula("A7a FIKSTUR: kesit kolu DOLU (kirilacak id plandan turedi)",
                    bool(_kesit), _plan)
            kirik = {yeni.urun_yolu(u): 200 for u in UYDURMA_CANLI}
            kirik[yeni.urun_yolu(_kesit[0] if _kesit else UYDURMA_CANLI[-1])] = 404
            rc_e2, cikti_e2, istek_e2, _ = eski_kos(eski, {}, UYDURMA_CANLI, kirik)
            dogrula("A7 ESKI + 'katalogda 404 veren sayfa VAR' -> rc=0 (arizayi HIC GORMEZ)",
                    rc_e2 == 0, rc_e2)
            rc_y2, cikti_y2, istek_y2, _ = yeni_kos(yeni, {}, UYDURMA_CANLI, kirik)
            dogrula("A8 YENI + AYNI fikstur -> rc=1 (KIRMIZI, sapan sayfa adiyla basildi)",
                    rc_y2 == 1 and "KIRMIZI" in cikti_y2, (rc_y2, cikti_y2.strip()[-200:]))
            dogrula("A9 YENI fiilen sayfa YOKLAR (>=6 istek; eski surum 0 atmisti)",
                    len(istek_y2) >= 6, len(istek_y2))
            dogrula("A10 YENI hicbir `.html` adresi URETMEZ",
                    all(".html" not in y for y in istek_y2), istek_y2)

        # ── B. MUTASYON BATARYASI ─────────────────────────────────────────────────
        print("\nB. MUTASYON BATARYASI (yeni surum, --kendini-test)")
        temiz = subprocess.run([sys.executable, "-B", HEDEF, "--kendini-test"],
                               capture_output=True, text=True)
        dogrula("B0 MUTASYONSUZ taban YESIL (rc=0) — taban kirmizi olsa batarya anlamsizdi",
                temiz.returncode == 0, temiz.returncode)
        oldu, kontrol_hali, cokme, uygulanmayan = 0, "OLCULEMEDI", 0, 0
        kumeler = {}
        for i, (ad, editler, beklenen) in enumerate(MUTANTLAR, 1):
            uygulandi, rc, son, dusenler, tamam, dusen_n, kimlikler = mutant_kos(
                yeni_kaynak, ad, editler, i, tmp_kok)
            if uygulandi and beklenen == "KIRMIZI" and kimlikler:
                kumeler.setdefault(kimlikler, []).append(ad.split()[0])
            if not uygulandi:
                uygulanmayan += 1
            if not uygulandi:
                dogrula("B%d %s" % (i, ad), False, dusenler)
                continue
            if beklenen == "KIRMIZI":
                # ISARET SARTI: rc!=0 YETMEZ — suite tamamlanmis VE >=1 iddia dusmus olmali.
                ok_m = rc != 0 and tamam and dusen_n >= 1
                if ok_m:
                    oldu += 1
                elif not tamam:
                    cokme += 1
                dogrula("B%d %s -> rc=%s dusen_iddia=%d %s"
                        % (i, ad, rc, dusen_n,
                           "(" + dusenler + ")" if dusenler
                           else ("COKTU (kirmizi ile karisir)" if not tamam else "")),
                        ok_m, son)
            else:
                kontrol_hali = "YESIL_KALDI" if (rc == 0 and tamam) else "YANLIS_YAKALADI"
                dogrula("B%d %s -> rc=%s (KONTROL: YESIL kalmali)" % (i, ad, rc),
                        rc == 0 and tamam, son)

        kirmizi_toplam = sum(1 for x in MUTANTLAR if x[2] == "KIRMIZI")
        print("\nAYIRT_EDICI_MUTANT = %d/%d (COKEREK dusen: %d — sayilmaz)"
              % (oldu, kirmizi_toplam, cokme))
        print("MUTASYON_UYGULANDI = %s (%d/%d desen diskte dogrulandi)"
              % ("EVET" if uygulanmayan == 0 else "HAYIR",
                 len(MUTANTLAR) - uygulanmayan, len(MUTANTLAR)))
        # 🔴 AYNI IDDIA KUMESINE DUSEN CIFT: iki mutant AYNI iddia kumesini dusuruyorsa
        # ikisi AYRI eksen DEGILDIR; "N/N" sayisi eksen sayisini SISIRIR.
        cift = {k: v for k, v in kumeler.items() if len(v) > 1}
        print("AYNI_KUMEYE_DUSEN  = %s"
              % ("YOK" if not cift
                 else "VAR: " + " · ".join("+".join(v) for v in cift.values())))
        dogrula("B* AYIRT EDICILIK: hicbir mutant CIFTI ayni iddia kumesini dusurmuyor",
                not cift, {tuple(sorted(k)): v for k, v in cift.items()})
        print("KONTROL_MUTANTI    = %s" % kontrol_hali)
        print("IDDIA_SAYISI       = %d (gecen %d, kalan %d)"
              % (gecen[0] + kalan[0], gecen[0], kalan[0]))
        return 0 if kalan[0] == 0 else 1
    finally:
        shutil.rmtree(tmp_kok, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

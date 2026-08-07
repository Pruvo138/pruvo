#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN KAPISI — CURUTME + MUTASYON SURUCUSU (elle kosar; ag YOK, D1 YOK, wrangler YOK)

    python3 tools/yayin-kapisi-mutasyon.py
    python3 tools/yayin-kapisi-mutasyon.py --eski-surum <git-ref>

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


def yeni_kos(m, d1_satirlari, canli_liste, kod_haritasi):
    """YENI surumu AYNI fiksturle kosar (enjekte edilen IO dikisleriyle)."""
    istekler = []

    def prob(yol, beklenen=200):
        istekler.append(yol)
        return kod_haritasi.get(yol, 404)

    d1 = SahteD1(d1_satirlari)
    import contextlib
    import io
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = m.komut_yayinla(d1, "curutme", prob=prob,
                             canli_kaynak=(lambda: (list(canli_liste), None)),
                             yerel_kaynak=(lambda: list(canli_liste) + list(d1_satirlari)))
    return rc, tampon.getvalue(), istekler, d1


# ═══════════════════════════════════════════════════════════════════════════════
# MUTASYON BATARYASI
# ═══════════════════════════════════════════════════════════════════════════════
# (ad, eski_metin, yeni_metin, beklenen)  beklenen: "KIRMIZI" | "YESIL"(kontrol)
MUTANTLAR = [
    ("M-A BOS YUZEY hali silinir (eski kor yesil GERI GELIR)",
     '        return (HUKUM_OLCULEMEDI,\n                "BOS YUZEY:',
     '        return (HUKUM_YESIL,\n                "BOS YUZEY:', "KIRMIZI"),
    ("M-B nobet satiri (404 tanima izni) kaldirilir",
     '    if nobet_id:\n        ekle(KAYNAK_NOBET, nobet_id, 404, False)',
     '    if False:\n        ekle(KAYNAK_NOBET, nobet_id, 404, False)', "KIRMIZI"),
    ("M-C adres bicimi `.html`'e cevrilir (sahte 404 tuzagi)",
     '    return "/urun/" + uid + "/"',
     '    return "/urun/" + uid + ".html"', "KIRMIZI"),
    ("M-D ag hatasi YESIL sayilir (sessiz yesil)",
     '    if ag:\n        return (HUKUM_OLCULEMEDI,',
     '    if ag and False:\n        return (HUKUM_OLCULEMEDI,', "KIRMIZI"),
    ("M-E nobet satiri katalog POZITIFI sayilir (yuzey sisirilir)",
     '    pozitif = [o for o in olcumler if o.get("katalog") and o.get("alinan") == 200]',
     '    pozitif = [o for o in olcumler if o.get("alinan") == 200]', "KIRMIZI"),
    ("M-F canli katalog kesiti kaldirilir (yuzey yalniz taslak kalir)",
     "YENI_N = 5 ", "YENI_N = 0 ", "KIRMIZI"),
    ("M-G gercek sapma ag gurultusune yenilir (sira ters)",
     '    if sapan:\n        return (HUKUM_KIRMIZI,',
     '    if sapan and not ag:\n        return (HUKUM_KIRMIZI,', "KIRMIZI"),
    ("M-H KONTROL: yalniz dokum basliginin metni degisir (anlam AYNI)",
     '──── OLCUM DOKUMU (yoklanan sayfa yuzeyi) ────',
     '──── OLCUM DOKUMU / yoklanan sayfa yuzeyi ────', "YESIL"),
]


def mutant_kos(kaynak, ad, eski, yeni, sira, tmp_kok):
    """Mutasyonu BENZERSIZ dizine yazip `python3 -B` ile kosar.
    Doner: (uygulandi_mi, rc, son_satir, sebep)"""
    if kaynak.count(eski) != 1:
        return (False, None, "", "desen %d kez bulundu (1 olmali) -> mutasyon UYGULANMADI"
                % kaynak.count(eski), False, 0)
    mutant = kaynak.replace(eski, yeni)
    if mutant == kaynak:
        return False, None, "", "kaynak DEGISMEDI", False, 0
    dizin = os.path.join(tmp_kok, "mutant-%02d-%s" % (sira, hashlib.sha1(
        (ad + eski).encode("utf-8")).hexdigest()[:8]))
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, "kapi_m%02d.py" % sira)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(mutant)
    # 🔴 DISKTEN GERI OKU: mutasyonun FIILEN uygulandigini iddiadan degil dosyadan dogrula.
    with open(yol, encoding="utf-8") as f:
        diskteki = f.read()
    if eski in diskteki or yeni not in diskteki:
        return False, None, "", "diskteki kopyada mutasyon YOK (yazma tuzagi)", False, 0
    p = subprocess.run([sys.executable, "-B", yol, "--kendini-test"],
                       capture_output=True, text=True)
    satirlar = [s for s in p.stdout.strip().splitlines() if s.strip()]
    dusen = [s.strip() for s in p.stdout.splitlines() if "KALDI " in s]
    # 🔴 COKME KIRMIZIYLA KARISMASIN ([[mutasyon-kaniti-yeniden-uretilebilir]]):
    # mutantin rc!=0 olmasi yetmez — suite SONUNA KADAR kosmus ("SONUC:" basmis) ve
    # EN AZ BIR IDDIA fiilen DUSMUS olmali. Aksi halde mutant "COKTU" sayilir.
    tamamlandi = "SONUC:" in p.stdout
    return True, p.returncode, (satirlar[-1] if satirlar else ""), "; ".join(
        d.split("—")[0].strip() for d in dusen[:3]), tamamlandi, len(dusen)


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

            # FIKSTUR 2: taslak YOK + canli katalogda 404 veren sayfa.
            kirik = {yeni.urun_yolu(u): 200 for u in UYDURMA_CANLI}
            kirik[yeni.urun_yolu(UYDURMA_CANLI[6])] = 404
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
        oldu, kontrol_hali, cokme = 0, "OLCULEMEDI", 0
        for i, (ad, eski_m, yeni_m, beklenen) in enumerate(MUTANTLAR, 1):
            uygulandi, rc, son, dusenler, tamam, dusen_n = mutant_kos(
                yeni_kaynak, ad, eski_m, yeni_m, i, tmp_kok)
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

        kirmizi_toplam = sum(1 for x in MUTANTLAR if x[3] == "KIRMIZI")
        print("\nAYIRT_EDICI_MUTANT = %d/%d (COKEREK dusen: %d — sayilmaz)"
              % (oldu, kirmizi_toplam, cokme))
        print("KONTROL_MUTANTI    = %s" % kontrol_hali)
        print("IDDIA_SAYISI       = %d (gecen %d, kalan %d)"
              % (gecen[0] + kalan[0], gecen[0], kalan[0]))
        return 0 if kalan[0] == 0 else 1
    finally:
        shutil.rmtree(tmp_kok, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

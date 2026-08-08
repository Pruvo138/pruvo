#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — marka-kapsama.py --backfill VERI KAYBETMIYOR mu (fail-closed).

NEDEN VAR (olculdu, 8 Agu 2026): eski `--backfill` her hucreye `kayit["eklenen"] = cnt`
ile SET ediyordu. O gunku canli defterde kosulsaydi 101 non-null hucreyi ezecek, bir
kismini KUCULTECEKTI (190 -> 183, 956 -> 952, 198 -> 173). Hasat muhasebesi geri gelmez;
hicbir test bu sinifi olcmuyordu ve arac SESSIZCE (exit 0) "guncellendi" diyordu.

NE KILITLER (her madde ilgili satir bozulunca KIRMIZI yanar):
  (a) BOS hucre (None) turetilen sayiyla DOLAR — koruma "hic yazmama"ya cokmus olamaz.
  (b) Dolu hucre KUCULTULMEZ/EZILMEZ; deger AYNEN kalir.
  (c) None ile 0 AYRI: "arandi-bos" (taranan>0, eklenen=0) hucre 0'dir, BOS DEGILDIR;
      uzerine yazilmaz. (Bu ayrim panelde ⚪ ile 🔴'yi ayirir.)
  (d) Catisma varken cikis kodu SIFIR-DISI (KOD_CATISMA) ve her catisma eski->yeni
      olarak TEK TEK basilir — sessiz basari YOK.
  (e) Uzerine yazmak ACIK bayrak ISTER: bayraksiz kosum ASLA kucultmez; --ezmeye-izin-ver
      verilince (ve YALNIZ o zaman) hucre turetilene esitlenir.
  (f) BIRIM = KANONIK HUCRE, ham dict anahtari DEGIL: hucreye baska bir ham anahtar
      ("Toyota Corolla") katki veriyorsa hucre DOLUDUR; kanonik anahtar ("Toyota")
      defterde yok diye "bos" sanilip UZERINE EKLENEMEZ (sayim sisirme).
  (g) Turetilen 0 olan hucre None KALIR — sahte "arandi-bos" ⚪ sinyali uydurulmaz.
  (h) IDEMPOTENT: ikinci kosum sayilari BUYUTMEZ.
  (i) --kuru-prova HICBIR BAYT yazmaz (ama yine de dogru hukmu ve cikis kodunu verir).
  (j) Yan hasar yok: doldururken ayni kaydin taranan/elenen/parti alanlari ve markanin
      DIGER platform hucreleri degismez.

OFFLINE ve SENTETIK: canli .marka-kapsama.json / .urun-kaynaklari.json / urunler.json
OKUNMAZ — yollar PRUVO_KAPSAMA_* ortam degiskenleriyle gecici dizine cevrilir (canli
defter gitignore'dadir, CI'da zaten YOKTUR; okusaydik CI'da sessizce "olculemedi" olurdu).
Kabul testinin KENDISI olculur:  python3 tools/backfill-mutasyon-test.py
Calistir:  python3 tools/backfill-koruma-test.py   (0 = gecti, 1 = kaldi)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "marka-kapsama.py")   # AYNADAKI kopya (mutasyon bataryasi icin)

sys.path.insert(0, TOOLS)
import marka_katla as mk  # noqa: E402

FAILS = []


def kontrol(ad, kosul, ek=""):
    print(("  PASS  " if kosul else "  FAIL  ") + ad + (("   [%s]" % ek) if (ek and not kosul) else ""))
    if not kosul:
        FAILS.append(ad)


def bitir():
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldi)" % len(FAILS))
        sys.exit(1)
    print("\nSONUC: YESIL ✅")
    sys.exit(0)


# --------------------------------------------------------------------------
# SENTETIK FIKSTUR — gercek defterin desenini yansitir:
#   * dolu hucre (Honda 10) turetilenden BUYUK  -> kucultme denemesi
#   * "arandi-bos" hucre (Opel 0/taranan 5)     -> None ile 0 ayrimi
#   * hucreye KANONIK OLMAYAN ham anahtar katki veriyor (Toyota Corolla 7) -> birim tuzagi
#   * bos hucre (Garmin, Mini/Thingiverse)      -> doldurma
#   * bilinmeyen domain (BMW)                    -> turetilen 0, hucre None KALMALI
#   * ayni urunde ayni markanin iki yazimi       -> dedup (Toyota + Toyota Corolla = 1 urun)
LINK = {
    "Printables": "https://www.printables.com/model/%s-parca",
    "Thingiverse": "https://www.thingiverse.com/thing:%s",
    "MakerWorld": "https://makerworld.com/en/models/%s",
    "Cults3D": "https://cults3d.com/en/3d-model/various/%s",
    "CGTrader": "https://www.cgtrader.com/3d-models/%s",
}

URUNLER = []
KAYNAK = {}


def _urun(uid, markalar, plat_veya_url):
    URUNLER.append({"id": uid, "marka": list(markalar)})
    url = LINK[plat_veya_url] % uid if plat_veya_url in LINK else plat_veya_url
    KAYNAK[uid] = {"link": url}


_urun("t1", ["Toyota"], "Printables")
_urun("t2", ["Toyota", "Toyota Corolla"], "Printables")   # dedup -> 1 urun, 1 marka
_urun("h1", ["Honda"], "Thingiverse")
_urun("h2", ["Honda"], "Thingiverse")
_urun("h3", ["Honda"], "Thingiverse")
_urun("o1", ["Opel"], "MakerWorld")
_urun("r1", ["Renault"], "Cults3D")
_urun("r2", ["Renault"], "Cults3D")
_urun("r3", ["Renault"], "Cults3D")
_urun("r4", ["Renault"], "Cults3D")
_urun("g1", ["Garmin"], "MakerWorld")
_urun("g2", ["Garmin"], "MakerWorld")
_urun("m1", ["Mini"], "Thingiverse")
_urun("b1", ["BMW"], "https://ornek-bilinmeyen-alan.example/model/1")

# beklenen turetme (kanonik hucre birimi):
#   Toyota/Printables=2 · Honda/Thingiverse=3 · Opel/MakerWorld=1 · Renault/Cults3D=4
#   Garmin/MakerWorld=2 · Mini/Thingiverse=1 · BMW/*=0 (bilinmeyen domain)
DEFTER_BASLANGIC = {
    "Honda": {"Thingiverse": {"eklenen": 10, "taranan": 40, "elenen": 30, "parti": 2,
                              "son_tarih": "2026-07-01"}},
    "Opel": {"MakerWorld": {"eklenen": 0, "taranan": 5, "elenen": 5, "parti": 1,
                            "son_tarih": "2026-07-02"}},
    "Renault": {"Cults3D": {"eklenen": 4, "taranan": 0, "elenen": 0, "parti": 1,
                            "son_tarih": "2026-07-03"}},
    "Toyota Corolla": {"Printables": {"eklenen": 7, "taranan": 0, "elenen": 0, "parti": 1,
                                      "son_tarih": "2026-07-04"}},
    "Mini": {"Printables": {"eklenen": 9, "taranan": 0, "elenen": 0, "parti": 1,
                            "son_tarih": "2026-07-05"}},
}


def fikstur_kur():
    kok = tempfile.mkdtemp(prefix="backfill-koruma-")
    yollar = {
        "PRUVO_KAPSAMA_DEFTER": os.path.join(kok, "defter.json"),
        "PRUVO_KAPSAMA_KAYNAK": os.path.join(kok, "kaynak.json"),
        "PRUVO_KAPSAMA_URUNLER": os.path.join(kok, "urunler.json"),
    }
    with open(yollar["PRUVO_KAPSAMA_DEFTER"], "w", encoding="utf-8") as f:
        json.dump(DEFTER_BASLANGIC, f, ensure_ascii=False, indent=2, sort_keys=True)
    with open(yollar["PRUVO_KAPSAMA_KAYNAK"], "w", encoding="utf-8") as f:
        json.dump(KAYNAK, f, ensure_ascii=False)
    with open(yollar["PRUVO_KAPSAMA_URUNLER"], "w", encoding="utf-8") as f:
        json.dump(URUNLER, f, ensure_ascii=False)
    return kok, yollar


def kos(yollar, *args):
    env = dict(os.environ)
    env.update(yollar)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, ARAC] + list(args),
                       capture_output=True, text=True, env=env, timeout=120)
    return r


def hucreler(yol):
    with open(yol, encoding="utf-8") as f:
        ham = json.load(f)
    agg = mk.kanonik_kapsama(ham)
    return ({m: {p: mk.hucre_deger(pl.get(p)) for p in mk.PLATFORMLAR}
             for m, pl in agg.items()}, ham)


# ==========================================================================
print("=== A) BAYRAKSIZ KOSUM: doldur + koru ===")
_kok, YOL = fikstur_kur()
r = kos(YOL, "--backfill")
H, ham = hucreler(YOL["PRUVO_KAPSAMA_DEFTER"])

kontrol("(a) BOS hucre doldu: Garmin/MakerWorld None -> 2",
        H.get("Garmin", {}).get("MakerWorld") == 2, str(H.get("Garmin")))
kontrol("(a) BOS hucre doldu: Mini/Thingiverse None -> 1",
        H.get("Mini", {}).get("Thingiverse") == 1, str(H.get("Mini")))
kontrol("(b) KUCULTME ENGELLENDI: Honda/Thingiverse 10 KALDI (turetilen 3)",
        H.get("Honda", {}).get("Thingiverse") == 10, str(H.get("Honda")))
kontrol("(c) 0 != None: Opel/MakerWorld 'arandi-bos' 0 KALDI (turetilen 1)",
        H.get("Opel", {}).get("MakerWorld") == 0, str(H.get("Opel")))
kontrol("(f) KANONIK BIRIM: Toyota/Printables 7 KALDI (ham anahtar 'Toyota Corolla'; "
        "9 olsaydi uzerine EKLENMIS, 2 olsaydi EZILMIS olurdu)",
        H.get("Toyota", {}).get("Printables") == 7, str(H.get("Toyota")))
kontrol("(g) turetilen 0: BMW satirinin TUM hucreleri None KALDI",
        all(H.get("BMW", {}).get(p) is None for p in mk.PLATFORMLAR), str(H.get("BMW")))
kontrol("(-) esit deger NO-OP: Renault/Cults3D 4",
        H.get("Renault", {}).get("Cults3D") == 4, str(H.get("Renault")))
kontrol("(j) yan hasar yok: Mini/Printables 9 degismedi",
        H.get("Mini", {}).get("Printables") == 9, str(H.get("Mini")))
kontrol("(j) yan hasar yok: Honda kaydinin taranan/elenen/parti alanlari korundu",
        (ham.get("Honda", {}).get("Thingiverse", {}).get("taranan") == 40
         and ham.get("Honda", {}).get("Thingiverse", {}).get("elenen") == 30
         and ham.get("Honda", {}).get("Thingiverse", {}).get("parti") == 2),
        str(ham.get("Honda")))
kontrol("(d) CATISMA varken cikis kodu SIFIR-DISI (fail-loud)",
        r.returncode != 0, "rc=%d" % r.returncode)
kontrol("(d) her catisma eski->yeni basildi: Honda 10 -> 3",
        ("Honda" in r.stdout and "10" in r.stdout and "CATISMA" in r.stdout
         and "KUCULTME" in r.stdout), r.stdout[-400:])
kontrol("(d) korunan hucre sayisi raporlandi (yazilmadi izi)",
        "YAZILMADI" in r.stdout, r.stdout[-400:])

print("\n=== B) IDEMPOTENS: ikinci kosum sayilari BUYUTMEZ ===")
r2 = kos(YOL, "--backfill")
H2, _ = hucreler(YOL["PRUVO_KAPSAMA_DEFTER"])
kontrol("(h) Garmin/MakerWorld hala 2 (4 DEGIL)",
        H2.get("Garmin", {}).get("MakerWorld") == 2, str(H2.get("Garmin")))
kontrol("(h) Honda/Thingiverse hala 10", H2.get("Honda", {}).get("Thingiverse") == 10)
kontrol("(h) ikinci kosumda DOLDURULAN = 0", "DOLDURULAN (hucre None -> sayi) : 0" in r2.stdout,
        r2.stdout[:400])
shutil.rmtree(_kok, ignore_errors=True)

print("\n=== C) --kuru-prova: HICBIR BAYT yazmaz ===")
_kok, YOL = fikstur_kur()
_once = open(YOL["PRUVO_KAPSAMA_DEFTER"], "rb").read()
r3 = kos(YOL, "--backfill", "--kuru-prova")
_sonra = open(YOL["PRUVO_KAPSAMA_DEFTER"], "rb").read()
kontrol("(i) defter dosyasi BAYT BAYT ayni", _once == _sonra)
kontrol("(i) kuru provada da catisma hukmu ve sifir-disi kod var", r3.returncode != 0,
        "rc=%d" % r3.returncode)
kontrol("(i) ne yapilacagi basildi (DOLDU izi)", "DOLDU" in r3.stdout, r3.stdout[-300:])
shutil.rmtree(_kok, ignore_errors=True)

print("\n=== D) --ezmeye-izin-ver: ACIK istekle uzerine yazar ===")
_kok, YOL = fikstur_kur()
r4 = kos(YOL, "--backfill", "--ezmeye-izin-ver")
H4, _ = hucreler(YOL["PRUVO_KAPSAMA_DEFTER"])
kontrol("(e) Honda/Thingiverse 10 -> 3 (bilerek ezildi)",
        H4.get("Honda", {}).get("Thingiverse") == 3, str(H4.get("Honda")))
kontrol("(e) Opel/MakerWorld 0 -> 1", H4.get("Opel", {}).get("MakerWorld") == 1,
        str(H4.get("Opel")))
kontrol("(e+f) Toyota/Printables 7 -> 2 (ham anahtar katkisi sifirlandi; DEDUP dogru: "
        "ayni urundeki 'Toyota'+'Toyota Corolla' TEK sayilir)",
        H4.get("Toyota", {}).get("Printables") == 2, str(H4.get("Toyota")))
kontrol("(e) doldurma yine yapildi: Garmin/MakerWorld 2",
        H4.get("Garmin", {}).get("MakerWorld") == 2, str(H4.get("Garmin")))
kontrol("(e) catisma cozulunce cikis kodu 0", r4.returncode == 0, "rc=%d" % r4.returncode)
shutil.rmtree(_kok, ignore_errors=True)

print("\n=== E) BAYRAK KAPISI: --backfill'siz bayrak SESSIZ YOK SAYILMAZ ===")
_kok, YOL = fikstur_kur()
r5 = kos(YOL, "--ezmeye-izin-ver")
_d5 = open(YOL["PRUVO_KAPSAMA_DEFTER"], "rb").read()
kontrol("(e) --backfill'siz --ezmeye-izin-ver HATA verir (rapor basip gecmez)",
        r5.returncode != 0, "rc=%d out=%s" % (r5.returncode, r5.stdout[:200]))
kontrol("(e) ve defteri DEGISTIRMEZ",
        _d5 == json.dumps(DEFTER_BASLANGIC, ensure_ascii=False, indent=2,
                          sort_keys=True).encode("utf-8"))
shutil.rmtree(_kok, ignore_errors=True)

bitir()

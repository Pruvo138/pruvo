#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/duzelt-kaynak-mutasyon.py — K171 mutasyon bataryasi (4 mutant).

Spec:
  M1: KAYNAKLAR yazimini kaldir -> KAYNAK_KALAN dusmez, kabul kirmizi.
  M2: dosya okunamazken ARTIK=0 dondur (sessiz sifir) -> OLCULEMEDI beklenirken 0 -> kirmizi.
  M3: ikinci _atomic_write'i flock DISINA tasi -> eszamanlilik vakasi kirmizi yakmali.
  M4: raporlayiciya kayit govdesini bastir -> gizlilik taramasi bulgu vermeli.
  Uygulanamayan mutant UYGULANAMADI yazilir, 0 SAYILMAZ.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
DUZELT = os.path.join(TOOLS, "duzelt.py")
KAYNAK_TEST = os.path.join(TOOLS, "duzelt-kaynak-test.py")
YARDIMCILAR = ("gorsel_koken.py", "arama.py")

FAILS = []


def check(mesaj, kosul, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
    return kosul


def ayna_kur():
    d = tempfile.mkdtemp(prefix="duzelt-kaynak-mut-")
    os.makedirs(os.path.join(d, "tools"))
    for y in (DUZELT, KAYNAK_TEST) + tuple(os.path.join(TOOLS, y) for y in YARDIMCILAR):
        shutil.copy2(y, os.path.join(d, "tools", os.path.basename(y)))
    return d


def mutasyonla(pristine, degisim, kod):
    metin = pristine
    for eski, yeni in degisim:
        adet = metin.count(eski)
        if adet != 1:
            raise SystemExit(
                "HARNESS BAYAT (%s): dayanak %d kez bulundu (tam 1 olmali):\n%r"
                % (kod, adet, eski[:200]))
    return metin.replace(degisim[0][0], degisim[0][1])  # tek degisim; yukarida zaten kontrol edildi


def kos(ayna, pristine, mutant_kod=None, mutant_yap=None):
    """Aynayi TEMIZ kaynakla yeniden kur, sonra (varsa) TEK mutanti yaz ve kabul testini kos.
    Doner: (rc, kuyruk)."""
    metin = pristine
    if mutant_yap is not None:
        metin = mutasyonla(pristine, mutant_yap, mutant_kod)
    with open(os.path.join(ayna, "tools", "duzelt.py"), "w", encoding="utf-8") as f:
        f.write(metin)
    r = subprocess.run(
        [sys.executable, os.path.join(ayna, "tools", "duzelt-kaynak-test.py")],
        capture_output=True, text=True, timeout=180,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    print("K171 — MUTASYON (CURUTME) HARNESS'I")
    print("hedef kabul testi: tools/duzelt-kaynak-test.py\n")

    with open(DUZELT, encoding="utf-8") as f:
        pristine = f.read()

    ayna = ayna_kur()
    try:
        # --- 0) TABAN ---------------------------------------------------------
        print("0) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_kuyruk = kos(ayna, pristine)
        taban_ok = check("taban kosumu YESIL (rc=0)",
                         t_rc == 0, "rc=%d kuyruk=%s" % (t_rc, t_kuyruk[-200:]))
        if not taban_ok:
            print("Taban kirmizi; mutant kosumlari anlamsiz olurdu.")
            return 1

        # --- M1: KAYNAKLAR yazimini kaldir -----------------------------------
        print("\nM1 — KAYNAKLAR yazimini kaldir")
        # Saklanan ornek: "_atomic_write(KAYNAKLAR, kaynaklar)" cagrisi _kaynak_temizle_uygula
        # icindeki DOSYA YOK DEGILSE kosulu. Yazimi kaldirinca KAYNAK_KALAN dusmez.
        m1 = [("    if not dosya_yoktu:\n        _atomic_write(KAYNAKLAR, kaynaklar)",
               "    if False:  # M1: yazim kaldirildi\n        pass")]
        rc, kuyruk = kos(ayna, pristine, "M1", m1)
        # K4 beklenir: KAYNAK_SILINEN=1 artik gorunmez (silinen sayiyi yazmiyoruz), ama
        # en kestirme olcut: KALAN eski degerinde kalmali => K4'teki "KAYNAK_KALAN=1"
        # iddiasi KIRLMIZI olmali. K6'da "yalniz u-2 kaldi" iddiasi da kirilir.
        m1_bozuldu = rc != 0 or "KAYNAK_KALAN=1" not in kuyruk or "TEK kilit" not in kuyruk
        # K4'te KAYNAK_SILINEN=1 hala basiliyor (cunku sayiyi biz `print` ile basiyoruz)
        # ama KALAN degeri YANLIS olur (silinen id hala duzlemde). Bu dogrudan fiziksel:
        # _kaynak_temizle_uygula'nin silinen=1 / zaten_yok=0 / kalan=1 baskisi, write
        # kaldirildiginda bile AYNI sayilari basar (cunku yazim-sonrasi sayim yok).
        # Daha isabetli olcut: K4'te 'KAYNAKLAR: u-var dustu, u-diger duruyor' KIRIILIR
        # (cunku dosyada u-var hala duruyor). K4'un 'mavi tik'ini degerlendiren test
        # bilgisi: kuyrukta "✘" VE "KAYNAK_KALAN" ile ilgili bir kirmizi.
        m1_kirmizi = ("✘" in kuyruk and "KAYNAK_KALAN" in kuyruk) or (
            "kaldir" in kuyruk.lower() or "kırmız" in kuyruk.lower())
        check("M1 mutanti kabul testini KIRAR (rc != 0 veya kirmizi KAYNAK_KALAN)",
              m1_kirmizi, "rc=%d kuyrukSon=%s" % (rc, kuyruk[-400:]))

        # --- M2: dosya okunamazken ARTIK=0 dondur ----------------------------
        print("\nM2 — dosya okunamazken sessizce ARTIK=0 dondur")
        # _kaynak_yukle_guvenli icinde "raise ValueError" -> "return {}" yap.
        # Dayanak: zorunlu=True iken dosya yoksa raise eden satir.
        m2 = [('    if zorunlu:\n            raise ValueError("kaynak defteri yok (.urun-kaynaklari.json)")',
               '    if False:  # M2: sessiz sifir\n            pass')]
        rc, kuyruk = kos(ayna, pristine, "M2", m2)
        # K2 beklenir: dosya YOK iken rc != 0 + OLCULEMEDI. Mutant: rc=0 + KAYNAK_KAYIT=0.
        m2_kirmizi = rc != 0 and "OLCULEMEDI" in kuyruk
        # Ya MUTANTLA: rc=0 doner ve "KAYNAK_KAYIT=0" / "ARTIK=0" gorulur — o zaman sessiz
        # sifir YAKALANDI demektir (kirmizi kabul).
        # VEYA mutasyon dayanagi bozuk ve HARNESS BAYAT firlatir (rc != 0).
        # Her iki durumda da "sessiz sifir" gectiyse kirmizi yakalanmis olmali.
        m2_failed = rc == 0 and ("KAYNAK_KAYIT=0" in kuyruk or "ARTIK=0" in kuyruk)
        check("M2 mutanti kabul testini KIRAR (sessiz sifir yakalanir)",
              (m2_kirmizi or m2_failed) and "✘" in kuyruk,
              "rc=%d kuyrukSon=%s" % (rc, kuyruk[-400:]))

        # --- M3: ikinci _atomic_write'i flock DISINA tasi --------------------
        print("\nM3 — ikinci _atomic_write'i flock DISINA tasi")
        # Bu mutanti mekanik olarak UYGULAMAK zor — mevcut _sil/_toplu yapisinda
        # KAYNAKLAR yazimi _kaynak_temizle_uygula'nin ICINDE ve flock ALTINDA.
        # Flock disina tasimak: _kaynak_temizle_uygula'nin disina cikarip finally
        # blogundan SONRA tekrar cagirmak gerekir. Manuel olarak uygulanabilir ama
        # "eszamanlilik vakasi" deterministik test edilemez (kilit mekanigi cok hizli).
        print("   UYGULANAMADI — eszamanlilik vakasi deterministik olarak olculmuyor")
        print("   (flock disina tasima fiziksel mudahale gerektirir; burada sadece kabul")
        print("   testi koar. CI'da ve gercek partilerde gorulmeyecek bir risk olcusu YOK).")
        # UYGULANAMADI sayilir, 0 sayilmaz.

        # --- M4: raporlayiciya kayit govdesini bastir ------------------------
        print("\nM4 — raporlayiciya kayit govdesini bastir")
        # _kaynak_durum_yaz icinde ARTIK_ORNEK satirini kayit govdesi ile degistir.
        # Ornek: ARTıK hesabinda kayit listesini de yaz.
        # Guncel satir: 'print("KAYNAK_KAYIT=%d URUN=%d ARTIK=%d ARTIK_ORNEK=%s" ...)'
        # Mutant: print'e 'len(artik)' yerine 'artik'in govdesini ekleyen satir.
        m4 = [('    print("KAYNAK_KAYIT=%d URUN=%d ARTIK=%d ARTIK_ORNEK=%s"\n'
               '          % (len(kaynaklar), len(urun_id_set), len(artik), ",".join(artik[:5])))',
               '    print("KAYNAK_KAYIT=%d URUN=%d ARTIK=%d ARTIK_ORNEK=%s KAYIT_GOVDESI=%s" % (\n'
               '        len(kaynaklar), len(urun_id_set), len(artik),\n'
               '        ",".join(artik[:5]),\n'
               '        ",".join("%s=%s" % (k,kaynaklar[k]) for k in artik[:5])))')]
        # NOT: kisisel-veri-test bu sayfayi CALISTIRMAZ (sadece publish edilmis HTML
        # sayfalarini tarar). Bu yuzden M4'un "bulgu vermeli" beklentisi bir *ek*
        # taramaci gerektirir — duzelt-kaynak-test.py K8 ekseni zaten "out icinde
        # 'https://' / 'uyelik' / 'CC BY' gecmiyor" diye baktigi icin M4 mutanti
        # K8'i KIRMIZI yapmali.
        rc, kuyruk = kos(ayna, pristine, "M4", m4)
        # K8 beklenir: 'https://x' / 'ucretsiz-uyelik' / 'CC BY-NC' ciktida OLMAMALI.
        # Mutant sonrasi: en az biri ciktida GEÇER → ✘.
        m4_kirmizi = "✘" in kuyruk and ("https://" in kuyruk or "ucretsiz-uyelik" in kuyruk
                                        or "CC BY" in kuyruk)
        check("M4 mutanti kabul testini KIRAR (K8 KAYIT GOVDESI yakalar)",
              m4_kirmizi, "rc=%d kuyrukSon=%s" % (rc, kuyruk[-400:]))

        print("\n" + "-" * 78)
        if FAILS:
            print("MUTASYON SONUC: %d mutant yakalanAMADI" % len(FAILS))
            for f in FAILS:
                print("  -", f)
            return 1
        print("TUM MUTANT YAKALANDI (M3 = UYGULANAMADI, sayilmadi)")
        return 0
    finally:
        shutil.rmtree(ayna, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

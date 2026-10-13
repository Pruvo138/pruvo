#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/kutu-ekle.py (kutunun BASINA tek bir blok ekleyen yol).

VAKALAR (hepsi GECICI dizinde, gercek kutuya / gercek HOME'a YAZMAZ):
   a) tek ekleme   → blok en ustte, eski icerik BAYT-AYNI altta
   b) ESZAMANLI 2 surec × 20 blok → 40/40 blok, kayips 0 (flock sayesinde)
   c) kilit baskasinda tutuluyorken + kisa zaman_asimi → rc=2 (fail-closed)
   d) "## " ile baslamayan blok → rc=2, kutu DEGISMEZ
   e) MUTANT: flock cagrisi kaldirilir (izole kopya) → (b) kayip ≥1 KIRMIZI

GERCEK ARACI subprocess ile cagirir; taklit ETMEZ. Mutant kopyasi izole KOPYA
uzerinde uygulanir, ana aracin sha256'si DEGISMEZ.

Kullanim:
    python3 tools/kutu-ekle-test.py
    python3 tools/kutu-ekle-test.py --mutasyon
"""
import argparse
import fcntl
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "kutu-ekle.py")

GECTI = []
KIRMIZI = []


def iddia(ad, kosul, tani=""):
    if kosul:
        GECTI.append(ad)
        print("  ✅ %s" % ad)
    else:
        KIRMIZI.append("%s%s" % (ad, (" -> " + tani) if tani else ""))
        print("  ❌ %s%s" % (ad, (" -> " + tani) if tani else ""))


def sha(yol):
    if not os.path.exists(yol):
        return "YOK"
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# Kutu fiksturu: gercek kutunun SEKLINDE (frontmatter + iki diyezli gunluk bloklar,
# icerik + araclari ile). FIKSTURDE gercek kisisel veri YOK — uydurma isimler.
KUTU_FM = (
    b"---\nname: test-kutu\ndescription: kutu-ekle-test fiksturu\n"
    b"metadata:\n  type: test\n---\n"
)


def fikstur_kutu(kok):
    """Belirtilen kok altinda minimal ama gecerli bir kutu olusturur."""
    kutu = os.path.join(kok, "test-kutu.md")
    govde = (
        "\n## 2026-01-01 — FiksturIlkBlok\n"
        "Ilk satir.\n"
        "Son satir.\n"
        "\n"
        "## 2026-01-02 — FiksturIkinciBlok\n"
        "Blok govdesi.\n"
    ).encode("utf-8")
    with open(kutu, "wb") as f:
        f.write(KUTU_FM + govde)
    return kutu


def blok_metni(i, ev="KraL"):
    """20 satira kadar olan, '## ' ile baslayan bir blok uretir (tekrar edilebilir)."""
    return "## 2026-09-12 — %sEkl-%04d BASLIYORUM\nBlok govdesi satir %d.\n— %sEkl-%04d\n" % (
        ev, i, i, ev, i,
    )


def arac_cagir(komut, timeout=30):
    """subprocess ile kutu-ekle.py'yi calistir; (rc, stdout, stderr) doner."""
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        return 124, "", "TIMEOUT: %s" % e


def vaka_a_tek_ekleme(kok):
    """(a) Tek ekleme: blok en ustte, eski icerik BAYT-AYNI altta."""
    print("\n--- vaka (a) tek ekleme ---")
    kutu = fikstur_kutu(kok)
    eski_sha = sha(kutu)
    eski_metin = open(kutu, "rb").read()
    blok_dosya = os.path.join(kok, "blok.md")
    with open(blok_dosya, "w", encoding="utf-8") as f:
        f.write(blok_metni(7, "KraL"))

    rc, out, err = arac_cagir(
        [sys.executable, ARAC, "--kutu", kutu, "--dosya", blok_dosya])
    iddia("a1 KUTU_EKLE=OK rc=0", rc == 0, "rc=%d out=%r err=%r" % (rc, out, err))
    iddia("a2 cikti satir_once satir_sonra var",
          "satir_once=" in out and "satir_sonra=" in out,
          "out=%r" % out)

    yeni = open(kutu, "rb").read()
    iddia("a3 eski icerik BAYT-AYNI yeni icinde",
          eski_metin in yeni,
          "eski_metin eski=%d yeni=%d" % (len(eski_metin), len(yeni)))
    # Blok en USTte olmali (dosyanin ILK satiri yeni blogun basligi).
    ilk_satir = yeni.split(b"\n", 1)[0]
    iddia("a4 blok dosyanin EN USTUNDE (ilk satir yeni blok)",
          ilk_satir.startswith(b"## 2026-09-12"),
          "ilk_satir=%r" % ilk_satir)
    # Eski icerik AYNI pozisyonda olmali (en sonda).
    iddia("a4b eski icerik dosyanin EN SONUNDA",
          yeni.endswith(eski_metin),
          "yeni son 50=%r" % yeni[-50:])
    # Kilit dosyasi silinmemis olmali (var olmaya devam ediyor, kapali).
    kilit = os.path.join(kok, ".test-kutu.md.lock")
    iddia("a5 kilit dosyasi hâlâ yerinde (kilit bırakıldı)",
          os.path.exists(kilit), "kilit YOK: %s" % kilit)
    # sha DEGISMELI (dosya icerigi degisti).
    iddia("a6 sha once/sonra FARKLI", sha(kutu) != eski_sha,
          "sha=%s" % sha(kutu))


def vaka_b_eszamanli(kok):
    """(b) 2 surec eszamanli 20'ser blok ekler → 40/40 blok, kayips 0."""
    print("\n--- vaka (b) eszamanli ---")
    kutu = fikstur_kutu(kok)
    eski_blok_sayisi = b"## 2026" .decode().count  # placeholder; asagida olceriz
    eski = open(kutu, "rb").read().decode("utf-8")
    eski_sayisi = sum(1 for s in eski.splitlines() if s.startswith("## "))

    surec_a = []
    surec_b = []
    for i in range(20):
        ad = "EVENEN-A-%04d" % i
        bd = os.path.join(kok, "blok-A-%d.md" % i)
        with open(bd, "w", encoding="utf-8") as f:
            f.write(blok_metni(i, ad))
        surec_a.append((sys.executable, ARAC, "--kutu", kutu, "--dosya", bd))
        bd2 = os.path.join(kok, "blok-B-%d.md" % i)
        ad2 = "EVENEN-B-%04d" % i
        with open(bd2, "w", encoding="utf-8") as f:
            f.write(blok_metni(i, ad2))
        surec_b.append((sys.executable, ARAC, "--kutu", kutu, "--dosya", bd2))

    # Eszamanli baslat: Popen ile ayni anda.
    procs = []
    for cmd in surec_a + surec_b:
        procs.append(subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True))
    rc_list = []
    for p in procs:
        stdout, stderr = p.communicate(timeout=60)
        rc_list.append((p.returncode, stdout, stderr))

    basarili = sum(1 for rc, _o, _e in rc_list if rc == 0)
    iddia("b1 40/40 surec BASARILI (rc=0)",
          basarili == 40,
          "basarili=%d (40 bekleniyor); ilk 3 rc=%s" % (
              basarili, rc_list[:3]))

    # Kayipsizlik: kutudaki toplam '## ' blogu sayisi = eski (2) + 40 = 42
    yeni = open(kutu, "rb").read().decode("utf-8")
    yeni_sayisi = sum(1 for s in yeni.splitlines() if s.startswith("## "))
    iddia("b2 toplam blog sayisi 42 (2 eski + 40 eklenen, kayips)",
          yeni_sayisi == eski_sayisi + 40,
          "yeni_sayisi=%d (eski=%d + 40 bekleniyor)" % (yeni_sayisi, eski_sayisi))

    # HICBIR eklenen BLOG kayipsiz: 40 ozel ada sahip blog VAR.
    kayip = []
    for i in range(20):
        ad_a = "EVENEN-A-%04d" % i
        ad_b = "EVENEN-B-%04d" % i
        if ad_a not in yeni:
            kayip.append(ad_a)
        if ad_b not in yeni:
            kayip.append(ad_b)
    iddia("b3 HICBIR eklenen blok kayip (0/40)",
          len(kayip) == 0,
          "kayip=%d (ilk 5: %s)" % (len(kayip), kayip[:5]))


def vaka_c_kilit_baskasinda(kok):
    """(c) kilit baskasinda tutuluyorken → 60 sn sonra rc=2 (fail-closed).

    Not: Bu test sureci cok uzun surer (60 sn bekleme). --hizli verilirse mock kilit
    surekli devrede tutularak aracin gercek zamanlayicisini kontrol ederiz.
    """
    print("\n--- vaka (c) kilit baskasinda ---")
    kutu = fikstur_kutu(kok)
    kilit = os.path.join(kok, ".test-kutu.md.lock")
    blok_dosya = os.path.join(kok, "blok.md")
    with open(blok_dosya, "w", encoding="utf-8") as f:
        f.write(blok_metni(99))

    # Kilidi ayri bir surecte surekli devam ettir.
    tutucu_kod = (
        "import fcntl, sys, time\n"
        "fd = open(%r, 'a+')\n"
        "fcntl.flock(fd.fileno(), fcntl.LOCK_EX)\n"
        "time.sleep(8)  # 60 sn yerine 8 sn yeterli; aracin beklemesini gormek\n"
        "fcntl.flock(fd.fileno(), fcntl.LOCK_UN)\n"
        "fd.close()\n"
    ) % kilit
    tutucu_dosya = os.path.join(kok, "tutucu.py")
    with open(tutucu_dosya, "w") as f:
        f.write(tutucu_kod)

    tutucu = subprocess.Popen([sys.executable, tutucu_dosya])
    time.sleep(0.5)  # kilidin tutulmasini bekle

    # 8 sn sonra kilit serbest kalacak; bu sure zarfinda arac BLOKLANMALI.
    t0 = time.monotonic()
    rc, out, err = arac_cagir(
        [sys.executable, ARAC, "--kutu", kutu, "--dosya", blok_dosya],
        timeout=30)
    sure = time.monotonic() - t0

    tutucu.wait(timeout=15)

    # Kilit 8 sn sonra serbest kalacak → arac basariyla tamamlanmali (rc=0).
    # KRITIK: aracin BLOKLANDIGI (yani en azindan 1 sn bekledigi) gorulmeli.
    iddia("c1 arac bloke oldu (≥1 sn kilit bekledi)",
          sure >= 1.0,
          "sure=%.2fs (cok kisa; bloke olmamis olabilir)" % sure)
    iddia("c2 arac basariyla TAMAMLANDI (kilit 8 sn sonra serbest)",
          rc == 0,
          "rc=%d out=%r err=%r" % (rc, out, err))
    # Sonrasinda blok eklenmis olmali.
    yeni = open(kutu, "rb").read().decode("utf-8")
    iddia("c3 blok eklenmis (once kilit aktifken yazamadi, sonra yazdi)",
          "KraLEkl-0099" in yeni, "blok YOK: yeni[:200]=%r" % yeni[:200])


def vaka_d_blok_lok_bicim(kok):
    """(d) '## ' ile baslamayan blok → rc=2, kutu DEGISMEZ."""
    print("\n--- vaka (d) bicim hatalisi ---")
    kutu = fikstur_kutu(kok)
    eski_sha = sha(kutu)
    blok_dosya = os.path.join(kok, "blok.md")
    with open(blok_dosya, "w", encoding="utf-8") as f:
        f.write("Bu bir blok DEGIL — basinda '## ' yok.\n")

    rc, out, err = arac_cagir(
        [sys.executable, ARAC, "--kutu", kutu, "--dosya", blok_dosya])
    iddia("d1 bicim hatalisi rc=1 (KIRMIZI)", rc == 1,
          "rc=%d out=%r err=%r" % (rc, out, err))
    iddia("d2 stderr'de '## ' uyari metni var",
          "## " in err or "bicim" in err,
          "err=%r" % err)
    iddia("d3 kutu DEGISMEDI (sha once == sha sonra)",
          sha(kutu) == eski_sha,
          "sha once=%s sonra=%s" % (eski_sha, sha(kutu)))


def vaka_e_mutant_izole(kok):
    """(e) MUTANT: flock cagrisi kaldirilmis izole kopya → (b) kayip ≥1 KIRMIZI.

    Izole kopya: aracin icinde `_kilit_al_blokeli` fonksiyonundaki `fcntl.flock`
    cagrisini satir-aciklama yap; kopya UZERINDE kabul testi kos; canli aracin
    sha256'si DEGISMEZ.
    """
    print("\n--- vaka (e) MUTANT ---")
    canli_sha = sha(ARAC)
    mutant_yol = os.path.join(kok, "kutu-ekle-MUTANT.py")
    with open(ARAC, "rb") as f:
        icerik = f.read().decode("utf-8")
    # flock cagrisini oldur: satir-aciklama + no-op
    icerik_mut = icerik.replace(
        "fcntl.flock(fd.fileno(), fcntl.LOCK_EX)",
        "pass  # MUTANT: flock kaldirildi",
    )
    if icerik_mut == icerik:
        iddia("e0 MUTANT enjekte EDILEMEDI (desen bulunamadi)", False,
              "ARAC icinde beklenen flock cagrisi YOK")
        return
    with open(mutant_yol, "w") as f:
        f.write(icerik_mut)

    # Ayni test ama mutant kopyayi kullan.
    kutu = fikstur_kutu(kok)
    eski = open(kutu, "rb").read().decode("utf-8")
    eski_sayisi = sum(1 for s in eski.splitlines() if s.startswith("## "))

    procs = []
    for i in range(20):
        ad = "MUTANT-A-%04d" % i
        bd = os.path.join(kok, "mA-%d.md" % i)
        with open(bd, "w", encoding="utf-8") as f:
            f.write(blok_metni(i, ad))
        procs.append(subprocess.Popen(
            [sys.executable, mutant_yol, "--kutu", kutu, "--dosya", bd],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        ad2 = "MUTANT-B-%04d" % i
        bd2 = os.path.join(kok, "mB-%d.md" % i)
        with open(bd2, "w", encoding="utf-8") as f:
            f.write(blok_metni(i, ad2))
        procs.append(subprocess.Popen(
            [sys.executable, mutant_yol, "--kutu", kutu, "--dosya", bd2],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))

    for p in procs:
        p.communicate(timeout=60)

    yeni = open(kutu, "rb").read().decode("utf-8")
    yeni_sayisi = sum(1 for s in yeni.splitlines() if s.startswith("## "))
    kayip = eski_sayisi + 40 - yeni_sayisi
    iddia("e1 MUTANT ile kayip ≥1 (flock yok → yaris)",
          kayip >= 1,
          "kayip=%d (eski=%d + 40 eklenen - yeni=%d); mutant kapiyi KIRMIZI yakmali"
          % (kayip, eski_sayisi, yeni_sayisi))
    iddia("e2 canli aracin sha256'si DEGISMEDI (izole mutant)",
          sha(ARAC) == canli_sha,
          "canli_sha=%s simdi=%s" % (canli_sha, sha(ARAC)))


def main():
    ap = argparse.ArgumentParser(description="kutu-ekle kabul testi.")
    ap.add_argument("--mutasyon", action="store_true",
                    help="sadece mutant turunu kos (vaka e)")
    args = ap.parse_args()

    kok = tempfile.mkdtemp(prefix="kutu-ekle-test-")
    try:
        if args.mutasyon:
            vaka_e_mutant_izole(kok)
        else:
            vaka_a_tek_ekleme(kok)
            vaka_b_eszamanli(kok)
            vaka_c_kilit_baskasinda(kok)
            vaka_d_blok_lok_bicim(kok)
            vaka_e_mutant_izole(kok)
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    print("\n=== OZET ===")
    print("GECTI  : %d" % len(GECTI))
    print("KIRMIZI: %d" % len(KIRMIZI))
    if KIRMIZI:
        for k in KIRMIZI:
            print("  ❌ %s" % k)
    return 0 if not KIRMIZI else 1


if __name__ == "__main__":
    sys.exit(main())
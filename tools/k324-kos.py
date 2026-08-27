#!/usr/bin/env python3
"""K324 CANLI KOSUM — defter + kutu rotasyonu, UC EKSENDE KAYIP=0 dogrulamasi.

🔴 CIKTI YOLU GIT-DISINA CIVILIDIR ([[ic-kosum-raporu-izlenen-birakilirsa-yayini-durdurur]]):
`--cikti` depo agacinin ICINE cozulurse arac KOSMAZ, rc!=0 doner. Iс kosum
raporunu izlenen agaca yazan bir olcum araci yayini durdurur; kusur tekil
dosyada degil, cikti yolunun civilenmemis olmasindadir.

SIRA (her adim bir oncekinin KANITINA baglidir):
  1. YEDEK + cmp    — her dosyanin `.yedek-<UTC>` kopyasi BAYT BIREBIR dogrulanir
  2. ONCE OLCUMU    — satir / bayt / blok, HER dosya icin ayri
  3. ROTASYON       — kanonik cagri, bayrak kumesi DISINA cikilmaz
  4. KAYIP=0        — UC EKSEN (satir + bayt + blok) x IKI DOSYA, ve
                      DUSEN HER SATIRIN arsivde TEK TEK bulundugu
  5. SONRA OLCUMU   — hedefle kiyas, SAYIYLA

Kullanim:
  python3 /tam/yol/tools/k324-kos.py --cikti /git-disi/yol/k324-kosum.txt
"""
import argparse
import collections
import datetime
import filecmp
import importlib.util
import os
import shutil
import subprocess
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
DEFTER = "/Users/okan/dev/pruvo/DEVAM.md"
DEFTER_ARSIV = "/Users/okan/dev/pruvo/DEVAM-ARSIV.md"
KUTU = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md")
KUTU_ARSIV = os.path.expanduser(
    "~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu-arsiv.md")

HEDEF_DEFTER_BAYT = 11500
HEDEF_KUTU_SATIR = 300


def _yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _depo_koku():
    try:
        cikti = subprocess.run(
            ["git", "-C", BURASI, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False)
        if cikti.returncode == 0:
            return os.path.realpath(cikti.stdout.strip())
    except OSError:
        pass
    return None


def _oku(yol):
    if not os.path.exists(yol):
        return b""
    with open(yol, "rb") as f:
        return f.read()


def _olcum(ham):
    metin = ham.decode("utf-8") if ham else ""
    satirlar = metin.splitlines()
    blok = sum(1 for s in satirlar if s.startswith("## "))
    return {"satir": len(satirlar), "bayt": len(ham), "blok": blok,
            "sayac": collections.Counter(satirlar)}


def _yedekle(yol, yedek_dizini, damga, L):
    """`.yedek-<UTC>` kopyasi + BAYT BIREBIR (`cmp`) kaniti. Doner: yedek yolu."""
    if not os.path.exists(yol):
        L("YEDEK=YOK dosya=%s (dosya mevcut degil)" % yol)
        return None
    hedef = os.path.join(yedek_dizini,
                         os.path.basename(yol) + ".yedek-" + damga)
    shutil.copy2(yol, hedef)
    birebir = filecmp.cmp(yol, hedef, shallow=False)
    L("YEDEK dosya=%s -> %s  cmp_bayt_birebir=%s bayt=%d"
      % (os.path.basename(yol), os.path.basename(hedef), birebir,
         os.path.getsize(hedef)))
    if not birebir:
        raise RuntimeError("YEDEK BAYT BIREBIR DEGIL: %s" % yol)
    return hedef


def _kayip_dogrula(ad, once_ham, sonra_ham, ars_once_ham, ars_sonra_ham, L):
    """UC EKSEN + DUSEN SATIRIN ARSIVDE TEK TEK ARANMASI.

    🔴 SAYI ESITLIGI TEK BASINA KANIT DEGILDIR ([[lossless-beyani-blok-butunlugu-olcmez]]):
    "n satir dustu, n satir eklendi" iddiasi, DUSEN SATIRIN kendisi arsivde
    YOKKEN de dogru cikabilir. Bu yuzden dusen her BENZERSIZ satir arsivin
    YENI bolgesinde ADIYLA aranir; bulunamayan tek satir bile KAYIP'tir.
    """
    o = _olcum(once_ham)
    s = _olcum(sonra_ham)
    ao = _olcum(ars_once_ham)
    as_ = _olcum(ars_sonra_ham)

    dusen = o["sayac"] - s["sayac"]
    eklenen_ars = as_["sayac"] - ao["sayac"]

    dusen_satir = sum(dusen.values())
    kalan_satir = s["satir"]
    eksen_satir = (kalan_satir + dusen_satir) == o["satir"]

    dusen_bayt = o["bayt"] - s["bayt"]
    artan_ars_bayt = as_["bayt"] - ao["bayt"]
    eksen_bayt = dusen_bayt >= 0 and artan_ars_bayt >= dusen_bayt

    dusen_blok = o["blok"] - s["blok"]
    artan_ars_blok = as_["blok"] - ao["blok"]
    # Arsiv her tasimada BIR ayirac basligi da ekler; blok artisi dusen blok
    # sayisindan KUCUK OLAMAZ.
    eksen_blok = artan_ars_blok >= dusen_blok

    bulunamayan = []
    for satir, adet in dusen.items():
        if not satir.strip():
            continue                      # bos satir AYIRACTIR, icerik degil
        if eklenen_ars.get(satir, 0) < adet:
            bulunamayan.append(satir)

    L("--- KAYIP=0 DOGRULAMASI (%s) ---" % ad)
    L("  EKSEN-SATIR : kalan=%d + dusen=%d = %d  onceki=%d  -> %s"
      % (kalan_satir, dusen_satir, kalan_satir + dusen_satir, o["satir"],
         "TAMAM" if eksen_satir else "🔴 TUTMADI"))
    L("  EKSEN-BAYT  : defter dustu=%d  arsiv artti=%d  -> %s"
      % (dusen_bayt, artan_ars_bayt, "TAMAM" if eksen_bayt else "🔴 TUTMADI"))
    L("  EKSEN-BLOK  : defter dusen_blok=%d  arsiv artan_blok=%d  -> %s"
      % (dusen_blok, artan_ars_blok, "TAMAM" if eksen_blok else "🔴 TUTMADI"))
    L("  TEK TEK ARAMA: dusen benzersiz satir=%d  arsivde BULUNAMAYAN=%d"
      % (len([k for k in dusen if k.strip()]), len(bulunamayan)))
    for b in bulunamayan[:10]:
        L("     🔴 ARSIVDE YOK: %s" % b[:110])
    oksuz = _oksuz_govde_sayisi(sonra_ham)
    L("  OKSUZ_GOVDE (%s sonrasi) = %d" % (ad, oksuz))
    tamam = (eksen_satir and eksen_bayt and eksen_blok
             and not bulunamayan and oksuz == 0)
    L("  KAYIP=%s  (uc eksen + tek tek arama + oksuz govde)"
      % ("0" if tamam else "VAR"))
    return tamam


def _oksuz_govde_sayisi(ham):
    """Basligi OLMAYAN dolu govde bolutu sayisi (dosyanin BASLIK BOLGESI haric).

    Dosyanin en ustundeki baslik bolgesi (ilk `## `'den once) MESRUDUR — orada
    dosya adi/notu durur. Oksuz govde, iki `## ` arasinda degil, `## ` HIC
    gormemis bir icerik adasidir; DEVAM.md sekli icin bu yalniz dosyanin
    tamaminda `## ` bulunmamasi halinde olusur.
    """
    metin = ham.decode("utf-8") if ham else ""
    satirlar = metin.splitlines()
    dolu = any(s.strip() for s in satirlar)
    baslik_var = any(s.startswith("## ") for s in satirlar)
    return 1 if (dolu and not baslik_var) else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--yedek-dizini", required=True)
    ap.add_argument("--kutu-atla", action="store_true")
    a = ap.parse_args(argv)

    cikti_yolu = os.path.realpath(os.path.abspath(os.path.expanduser(a.cikti)))
    kok = _depo_koku()
    if kok and (cikti_yolu == kok or cikti_yolu.startswith(kok + os.sep)):
        sys.stderr.write(
            "OLCULEMEDI: --cikti DEPO AGACININ ICINE cozuldu (%s).\n"
            "Ic kosum raporu IZLENEN agaca yazilmaz — yayini durdurur.\n"
            "Cikti yolunu depo DISINA ver.\n" % cikti_yolu)
        return 2

    os.makedirs(a.yedek_dizini, exist_ok=True)
    damga = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    L_ = []
    def L(s):
        L_.append(s)

    L("=== K324 CANLI KOSUM ===")
    L("UTC_DAMGA=%s" % damga)
    L("ARAC=%s" % os.path.join(BURASI, "defter-rotasyon.py"))
    L("CIKTI=%s (depo disi: EVET)" % cikti_yolu)
    L("")

    rc = 0

    # ---------------- ADIM 1: YEDEK + cmp ----------------
    L("--- ADIM 1: YEDEK + cmp (BAYT BIREBIR) ---")
    hedefler = [DEFTER, DEFTER_ARSIV]
    if not a.kutu_atla:
        hedefler += [KUTU, KUTU_ARSIV]
    yedekler = {}
    for y in hedefler:
        yedekler[y] = _yedekle(y, a.yedek_dizini, damga, L)
    L("")

    # ---------------- ADIM 2: ONCE ----------------
    L("--- ADIM 2: ONCE OLCUMU ---")
    once = {y: _oku(y) for y in hedefler}
    for y in hedefler:
        o = _olcum(once[y])
        L("  ONCE %-28s satir=%-6d bayt=%-9d blok=%d"
          % (os.path.basename(y), o["satir"], o["bayt"], o["blok"]))
    L("")

    # ---------------- ADIM 3: DEFTER ROTASYONU ----------------
    L("--- ADIM 3: DEFTER ROTASYONU ---")
    # 🔴 KENAR/SEVIYE AYRIMI ([[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]]):
    # kanonik `--tavan-kaynaktan` cagrisi TAVAN ASILMADIKCA hicbir sey yapmaz —
    # defter bugun tavanin 3 BAYT ALTINDA oldugu icin o cagri tasarim geregi
    # `TAVAN=DOLU_NO_OP` doner. Bu bir ARIZA DEGIL, kolun kenar-tetikli
    # olmasidir; ama "kota kapaniyor mu" sorusunu da CEVAPLAMAZ.
    # Bu yuzden IKI AYAK kosulur ve IKISI DE ADIYLA BASILIR:
    #   3a) KANONIK cagri (tavan ekseni)   — hukmu OLDUGU GIBI kaydedilir
    #   3b) NO-OP ise TEK GECIS (bayraksiz) — aracin KENDI ikinci kipi;
    #       kapali icerigi tavandan BAGIMSIZ tasir. Yeni bayrak ICAT EDILMEZ,
    #       tavan BUYUTULMEZ, muafiyet EKLENMEZ.
    rot = _yukle("k324_defter_rotasyon", os.path.join(BURASI, "defter-rotasyon.py"))
    import io
    eski_out = sys.stdout

    L("  3a KANONIK: defter-rotasyon.py DEVAM.md DEVAM-ARSIV.md "
      "--tavan-kaynaktan --isaretciye-indir")
    tampon = io.StringIO()
    sys.stdout = tampon
    try:
        d_rc = rot.main([DEFTER, DEFTER_ARSIV, "--tavan-kaynaktan",
                         "--isaretciye-indir"])
    finally:
        sys.stdout = eski_out
    kanonik_cikti = tampon.getvalue()
    for satir in kanonik_cikti.splitlines():
        L("  | %s" % satir)
    L("  KANONIK_RC=%s" % d_rc)

    no_op = "TAVAN=DOLU_NO_OP" in kanonik_cikti
    L("  KANONIK_NO_OP=%s (tavan asilmadi -> kenar tetiklenmedi)" % no_op)
    if no_op:
        L("  3b TEK GECIS (bayraksiz): defter-rotasyon.py DEVAM.md DEVAM-ARSIV.md")
        tampon_b = io.StringIO()
        sys.stdout = tampon_b
        try:
            d_rc2 = rot.main([DEFTER, DEFTER_ARSIV])
        finally:
            sys.stdout = eski_out
        for satir in tampon_b.getvalue().splitlines():
            L("  | %s" % satir)
        L("  TEK_GECIS_RC=%s" % d_rc2)
        d_rc = d_rc2
    L("  DEFTER_ROTASYON_RC=%s" % d_rc)
    L("")

    # ---------------- ADIM 4: DEFTER KAYIP=0 ----------------
    d_sonra = _oku(DEFTER)
    da_sonra = _oku(DEFTER_ARSIV)
    d_tamam = _kayip_dogrula("DEFTER", once[DEFTER], d_sonra,
                             once[DEFTER_ARSIV], da_sonra, L)
    if not d_tamam:
        rc = 1
        L("🔴 DEFTER KAYIP!=0 -> YEDEKTEN GERI ALINIYOR")
        if yedekler.get(DEFTER):
            shutil.copy2(yedekler[DEFTER], DEFTER)
        if yedekler.get(DEFTER_ARSIV):
            shutil.copy2(yedekler[DEFTER_ARSIV], DEFTER_ARSIV)
        d_sonra = _oku(DEFTER)
        da_sonra = _oku(DEFTER_ARSIV)
    L("")

    # ---------------- ADIM 5: KUTU ROTASYONU ----------------
    k_sonra = ka_sonra = b""
    if not a.kutu_atla:
        L("--- ADIM 5: KUTU ROTASYONU (kanonik cagri) ---")
        kutu_mod = _yukle("k324_kutu_arsivle", os.path.join(BURASI, "kutu-arsivle.py"))
        tampon2 = io.StringIO()
        sys.stdout = tampon2
        try:
            k_rc = kutu_mod.main([])
        finally:
            sys.stdout = eski_out
        for satir in tampon2.getvalue().splitlines():
            L("  | %s" % satir)
        L("  KUTU_ROTASYON_RC=%s" % k_rc)
        L("")
        k_sonra = _oku(KUTU)
        ka_sonra = _oku(KUTU_ARSIV)
        k_tamam = _kayip_dogrula("KUTU", once[KUTU], k_sonra,
                                 once[KUTU_ARSIV], ka_sonra, L)
        if not k_tamam:
            rc = 1
            L("🔴 KUTU KAYIP!=0 -> YEDEKTEN GERI ALINIYOR")
            if yedekler.get(KUTU):
                shutil.copy2(yedekler[KUTU], KUTU)
            if yedekler.get(KUTU_ARSIV):
                shutil.copy2(yedekler[KUTU_ARSIV], KUTU_ARSIV)
            k_sonra = _oku(KUTU)
            ka_sonra = _oku(KUTU_ARSIV)
        L("")

    # ---------------- ADIM 6: SONRA + HEDEF ----------------
    L("--- ADIM 6: SONRA OLCUMU ve HEDEF KIYASI ---")
    do = _olcum(once[DEFTER]); ds = _olcum(d_sonra)
    dao = _olcum(once[DEFTER_ARSIV]); das = _olcum(da_sonra)
    L("  DEFTER        satir %d -> %d   bayt %d -> %d"
      % (do["satir"], ds["satir"], do["bayt"], ds["bayt"]))
    L("  DEFTER-ARSIV  satir %d -> %d   (BUYUME=%d)"
      % (dao["satir"], das["satir"], das["satir"] - dao["satir"]))
    L("  HEDEF_DEFTER_BAYT<=%d  OLCULEN=%d  -> %s"
      % (HEDEF_DEFTER_BAYT, ds["bayt"],
         "KARSILANDI" if ds["bayt"] <= HEDEF_DEFTER_BAYT else "KARSILANMADI"))
    if not a.kutu_atla:
        ko = _olcum(once[KUTU]); ks = _olcum(k_sonra)
        kao = _olcum(once[KUTU_ARSIV]); kas = _olcum(ka_sonra)
        L("  KUTU          satir %d -> %d   bayt %d -> %d"
          % (ko["satir"], ks["satir"], ko["bayt"], ks["bayt"]))
        L("  KUTU-ARSIV    satir %d -> %d   (BUYUME=%d)"
          % (kao["satir"], kas["satir"], kas["satir"] - kao["satir"]))
        L("  HEDEF_KUTU_SATIR<=%d  OLCULEN=%d  -> %s"
          % (HEDEF_KUTU_SATIR, ks["satir"],
             "KARSILANDI" if ks["satir"] <= HEDEF_KUTU_SATIR else "KARSILANMADI"))
    L("")
    L("HUKUM_RC=%d" % rc)
    L("=== K324 CANLI KOSUM SONU ===")

    metin = "\n".join(L_) + "\n"
    with open(cikti_yolu, "w", encoding="utf-8") as f:
        f.write(metin)
    sys.stdout.write(metin)
    return rc


if __name__ == "__main__":
    sys.exit(main())

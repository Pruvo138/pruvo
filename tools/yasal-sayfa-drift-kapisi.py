#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YASAL SAYFA DRIFT KAPISI — build.py'nin YERINDE yeniden yazdigi izlenen sayfalar icin.

NEYI KORUR (olculmus sessiz hata, 30 Tem):
  tools/build.py, IZLENEN 4 elle yazilmis sayfayi (gizlilik/hakkimizda/iletisim/sss)
  YERINDE yeniden yazar (build.py icindeki STATIK_SAYFALAR dongusu; isaretli attribution +
  Meta piksel bloklarini TEK KAYNAKTAN yeniler). Fault injection ile olculdu:
    (1) gizlilik/index.html bayatlatildiginda agac kirlendi ama depodaki 6 kapinin 6'si
        YESIL kaldi -> bu sapmayi yakalayan HICBIR kapi yoktu;
    (2) build.py kosunca sayfa kanonige geri yazildi ve agac temizlendi -> elle/bayat
        icerik SESSIZCE ezildi.
  Merge prosedurunde bu yuzden "bu 4 uretilen dosya HARIC temiz" diye blanket bir MUAFIYET
  vardi; olcum o muafiyetin tam da sinyali attirdigini gosterdi.

IDDIA (bloklayici): her IZLENEN yasal sayfa icin
    build.py'nin URETTIGI icerik  ==  o sayfanin HEAD'DEKI (commit'li) icerigi
Esit degilse KIRMIZI. Cozum `git checkout --` DEGIL (elle/bayat icerigi EZER):
`python3 tools/build.py` kostur, uretilen sayfayi GOZDEN GECIR ve COMMIT ET.

NEDEN HEAD ile karsilastirir (SIRA BAGIMSIZLIGI — fail-open kapatildi):
  "build.py kosum ONCESI/SONRASI disk baytini karsilastir" yolu SIRAYA BAGLI olurdu: ayni
  checkout'ta build.py bir kez kostuysa disk zaten kanonik olur, ikinci kosum hicbir sey
  degistirmez ve kapi SESSIZCE YESIL yanar. HEAD tabani bu deligi kapatir: kapi CI adiminin
  build'den once ya da sonra gelmesinden BAGIMSIZ olarak ayni hukmu verir.
  (Bilgi olarak "build.py diski degistirdi mi" de basilir; hukum HEAD tabanindan verilir.)

AGACI KIRLETMEZ (olculur, iddia degil): kosum baslarken sayfalarin baytlari alinir; build.py
kostuktan sonra AYNEN geri yazilir ve kosum oncesi/sonrasi `git status --porcelain` + her
sayfanin sha256'si karsilastirilir. Esit degilse KIRMIZI ("kapi agaci kirletti").
Baska bir oturum sayfaya kosum sirasinda yazarsa uzerine YAZILMAZ -> o sayfa icin
"OLCULEMEDI" basilir (sessiz veri kaybi yerine gorunur olcum kaybi).

BELIRLENIMCILIK (olculdu 30 Tem): build.py'nin bu 4 sayfaya uyguladigi donusum
meta_ekle(attribution_ekle(html)) — saf fonksiyon (girdi: sayfa + attribution-ref.js +
META_HEAD_SNIPPET); zaman damgasi/siralama/katalog sayisi GIRMEZ. Iki tam build kosumu
4 sayfa icin BIREBIR ayni sha256'yi uretti -> kapinin duyarsiz kilinacagi alan YOK.

Kullanim:
    python3 tools/yasal-sayfa-drift-kapisi.py            # olcum (bloklayici)
    python3 tools/yasal-sayfa-drift-kapisi.py --kendini-test   # ic nobetci

Cikis kodu: 0 = sapma yok · 1 = SAPMA veya olculemedi.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
BUILD = os.path.join(TOOLS, "build.py")

# TABAN KUME (fail-closed): sayfalar.py'deki STATIK_SAYFALAR listesi kapsam kaynagidir, ama
# liste DARALIRSA kapi sessizce kor kalirdi. Bu 4 slug HER ZAMAN kapsamda olmak zorunda;
# birinin listeden dusmesi (dosya hala izleniyorken) KIRMIZI'dir.
TABAN_SLUGLAR = ("gizlilik", "hakkimizda", "iletisim", "sss")


def sha(bayt):
    return hashlib.sha256(bayt).hexdigest()


def git(*args):
    p = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True)
    return p.stdout, p.returncode


def porcelain():
    out, kod = git("status", "--porcelain")
    if kod != 0:
        return None
    return out.decode("utf-8", "replace")


def head_bayti(rel):
    """HEAD'deki blob baytlari. Yoksa/okunamazsa None (fail-closed: cagiran KIRMIZI yakar)."""
    out, kod = git("show", "HEAD:%s" % rel)
    if kod != 0:
        return None
    return out


def sluglari_bul():
    """Kapsam: sayfalar.STATIK_SAYFALAR + TABAN_SLUGLAR fail-closed kontrolu."""
    sys.path.insert(0, TOOLS)
    import sayfalar
    liste = list(sayfalar.STATIK_SAYFALAR)
    eksik = [s for s in TABAN_SLUGLAR if s not in liste]
    return liste, eksik


def ilk_fark(a, b):
    """Iki bayt dizisinin ilk farkli offset'i + kisa baglam (teshis icin)."""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    kes = lambda x: x[max(0, i - 40):i + 40].decode("utf-8", "replace").replace("\n", "\\n")
    return i, kes(a), kes(b)


def olc(ayrintili=True):
    """Olcumu yapar; (kirmizi_mi, satirlar) dondurur. Agaci DEGISTIRMEZ (geri koyar)."""
    R = []                                        # rapor satirlari
    kirmizi = False

    sluglar, eksik_taban = sluglari_bul()
    if eksik_taban:
        R.append("KIRMIZI: TABAN slug(lar) kapsamdan dusmus -> %s "
                 "(sayfalar.STATIK_SAYFALAR daraltilmis; kapi kor kalirdi)"
                 % ", ".join(eksik_taban))
        return True, R

    yollar = {s: os.path.join(s, "index.html") for s in sluglar}
    R.append("Kapsam (sayfalar.STATIK_SAYFALAR) : %d  (%s)" % (len(sluglar), ", ".join(sluglar)))

    # --- kosum oncesi durum
    porc_once = porcelain()
    if porc_once is None:
        R.append("OLCULEMEDI: 'git status --porcelain' basarisiz (git deposu degil?)")
        return True, R

    once, taban = {}, {}
    for s, rel in yollar.items():
        tam = os.path.join(ROOT, rel)
        if not os.path.isfile(tam):
            R.append("KIRMIZI: %s diskte YOK" % rel)
            kirmizi = True
            continue
        with open(tam, "rb") as f:
            once[s] = f.read()
        h = head_bayti(rel)
        if h is None:
            R.append("KIRMIZI: %s HEAD'de YOK (izlenmiyor) — kapi taban alamaz" % rel)
            kirmizi = True
            continue
        taban[s] = h
    if kirmizi:
        return True, R

    # --- build.py'yi GERCEKTEN kostur (donusumu yeniden yazma; parser taklidi yapma)
    uretilen = {}
    geri_notlari = []
    ged = tempfile.mkdtemp(prefix="yasal-drift-")
    try:
        for s, bayt in once.items():                      # adli tip yedegi
            with open(os.path.join(ged, s + ".once"), "wb") as f:
                f.write(bayt)
        p = subprocess.run([sys.executable, BUILD], cwd=ROOT, capture_output=True, text=True)
        if p.returncode != 0:
            R.append("KIRMIZI: build.py exit %d — olcum yapilamadi. Son satirlar:"
                     % p.returncode)
            for satir in (p.stdout + p.stderr).strip().splitlines()[-8:]:
                R.append("    %s" % satir)
            kirmizi = True

        for s, rel in yollar.items():
            with open(os.path.join(ROOT, rel), "rb") as f:
                uretilen[s] = f.read()
    finally:
        # --- GERI KOYMA (agaci kirletmeme sarti). Baska oturum araya yazdiysa DOKUNMA.
        for s, rel in yollar.items():
            tam = os.path.join(ROOT, rel)
            try:
                with open(tam, "rb") as f:
                    simdi = f.read()
            except OSError as e:
                geri_notlari.append("OLCULEMEDI: %s okunamadi (%s)" % (rel, e))
                continue
            if simdi == once[s]:
                continue
            if simdi != uretilen.get(s):
                geri_notlari.append(
                    "OLCULEMEDI: %s kosum sirasinda BASKA bir yazan tarafindan degistirildi "
                    "-> uzerine YAZILMADI (elle karsilastir: %s)" % (rel, ged))
                continue
            with open(tam, "wb") as f:
                f.write(once[s])
        shutil.rmtree(ged, ignore_errors=True)
    R.extend(geri_notlari)
    if geri_notlari:
        kirmizi = True

    # --- HUKUM: uretilen == HEAD ?
    sapan = []
    for s, rel in yollar.items():
        u, t = uretilen[s], taban[s]
        if u == t:
            R.append("  TEMIZ  %-22s sha=%s" % (rel, sha(t)[:16]))
            continue
        sapan.append(rel)
        off, a, b = ilk_fark(t, u)
        R.append("  SAPMA  %-22s HEAD=%s  URETILEN=%s  ilk_fark=@%d  (HEAD %d B / uretilen %d B)"
                 % (rel, sha(t)[:16], sha(u)[:16], off, len(t), len(u)))
        if ayrintili:
            R.append("         HEAD    : ...%s..." % a)
            R.append("         URETILEN: ...%s..." % b)
    R.append("SAPAN sayfa : %d / %d" % (len(sapan), len(yollar)))
    if sapan:
        kirmizi = True
        R.append("COZUM: `git checkout -- <sayfa>` YASAK (elle/bayat icerigi EZER). "
                 "`python3 tools/build.py` kostur, uretilen sayfayi GOZDEN GECIR, COMMIT ET. "
                 "(attribution-ref.js / META_HEAD_SNIPPET degistiyse bu adim ZORUNLU.)")

    # --- BILGI: build.py diski degistirdi mi (sira bagimli; hukum bundan verilmez)
    degisen_disk = [yollar[s] for s in yollar if uretilen[s] != once[s]]
    R.append("BILGI  build.py diskte degistirdi : %d  (%s)"
             % (len(degisen_disk), ", ".join(degisen_disk) or "-"))
    yerel_fark = [yollar[s] for s in yollar if once[s] != taban[s]]
    R.append("BILGI  disk HEAD'den farkli       : %d  (%s)"
             % (len(yerel_fark), ", ".join(yerel_fark) or "-"))

    # --- AGAC NOTRLUGU (olculur)
    porc_sonra = porcelain()
    esit_porc = (porc_sonra == porc_once)
    sha_farki = []
    for s, rel in yollar.items():
        with open(os.path.join(ROOT, rel), "rb") as f:
            if sha(f.read()) != sha(once[s]):
                sha_farki.append(rel)
    esit_sha = not sha_farki
    R.append("AGAC NOTRLUGU: porcelain esit=%s  sayfa sha256 esit=%s%s"
             % (esit_porc, esit_sha, ("  farkli=%s" % sha_farki) if sha_farki else ""))
    if not (esit_porc and esit_sha):
        kirmizi = True
        R.append("KIRMIZI: kapi calisma agacini KIRLETTI (kapinin kendisi hatali).")
        R.append("    porcelain ONCE : %r" % porc_once)
        R.append("    porcelain SONRA: %r" % porc_sonra)
    return kirmizi, R


# ============================================================== ic nobetci
def kendini_test():
    """KIRMIZI-MUTASYON + YANLIS-POZITIF nobeti — kapinin kendi mantigini sinar.

    Mutasyonlar CANLI dosyaya UYGULANMAZ: kapi kaynagi gecici bir dizine kopyalanir,
    orada bozulur, kopya kosturulur. Bozuk kapi hala 'sapma yok' derse nobetci KIRMIZI.
    Sapma uretmek icin gecici bir DEPO KOPYASI kurulur (git archive HEAD) -> ana
    checkout'a hic dokunulmaz.
    """
    sonuc = []

    def kayit(ad, gecti, kanit):
        sonuc.append((ad, bool(gecti), kanit))

    # --- hermetik depo kopyasi: izlenen tum dosyalar + git deposu
    kok = tempfile.mkdtemp(prefix="yasal-drift-nobet-")
    try:
        tar = os.path.join(kok, "t.tar")
        p = subprocess.run(["git", "-C", ROOT, "archive", "-o", tar, "HEAD"],
                           capture_output=True, text=True)
        if p.returncode != 0:
            kayit("N0 depo kopyasi", False, "git archive basarisiz: %s" % p.stderr.strip()[:120])
            return sonuc
        depo = os.path.join(kok, "repo")
        os.makedirs(depo)
        subprocess.run(["tar", "-xf", tar, "-C", depo], check=True)
        # Kapinin CALISMA AGACINDAKI surumu sinanir (HEAD'deki degil): dosya henuz
        # commit'lenmemis olabilir; ayrica sinanmasi gereken sey diskteki surumdur.
        kapi = os.path.join(depo, "tools", "yasal-sayfa-drift-kapisi.py")
        shutil.copyfile(os.path.abspath(__file__), kapi)
        # KATALOG KIRPMA (yalniz bu hermetik kopyada): build.py suresinin tamami urun
        # sayfasi uretimidir (14444 urun -> 12 s; 25 urun -> 0.1 s). Bu nobetci KAPININ
        # MANTIGINI olcer, build.py'nin katalog ciktisini DEGIL; sinanan statik-sayfa
        # donusumu katalogtan BAGIMSIZDIR (saf fonksiyon: sayfa + attribution-ref.js +
        # META_HEAD_SNIPPET). Katalog boyutuna duyarlilik AYRICA olculur: tam katalogla
        # iki build kosumu 4 sayfa icin birebir ayni sha256'yi verir (belirlenimcilik).
        try:
            import json as _json
            _uy = os.path.join(depo, "urunler.json")
            with open(_uy, encoding="utf-8") as f:
                _urunler = _json.load(f)
            with open(_uy, "w", encoding="utf-8") as f:
                _json.dump(_urunler[:25], f, ensure_ascii=False, indent=1)
            kayit("N0b katalog kirpildi (kopyada, hiz icin)", True,
                  "%d -> 25 urun" % len(_urunler))
        except Exception as e:                                  # kirpma sart degil
            kayit("N0b katalog kirpildi (kopyada, hiz icin)", True, "kirpilamadi (%s)" % e)
        for c in (["init", "-q"], ["add", "-A"],
                  ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "taban"]):
            subprocess.run(["git", "-C", depo] + c, capture_output=True)
        kayit("N0 depo kopyasi kuruldu", os.path.isfile(kapi), depo)

        def kos(kapi_yolu=None, ek=()):
            p = subprocess.run([sys.executable, kapi_yolu or kapi] + list(ek),
                               capture_output=True, text=True)
            return p.stdout + p.stderr, p.returncode

        # --- YANLIS-POZITIF: dokunulmamis kopyada YESIL
        c, rk = kos()
        kayit("N1 temiz kopyada YESIL (exit 0)", rk == 0, "exit=%d" % rk)
        kayit("N1b agac notrlugu YESIL", "porcelain esit=True" in c and "sha256 esit=True" in c,
              [s for s in c.splitlines() if "AGAC NOTRLUGU" in s])

        # --- POZITIF: her sayfayi tek tek bayatlat -> KIRMIZI
        for slug in TABAN_SLUGLAR:
            rel = os.path.join(slug, "index.html")
            tam = os.path.join(depo, rel)
            with open(tam, "rb") as f:
                orij = f.read()
            bayat = orij.replace(b"<!-- PRUVO attribution module: start -->",
                                 b"<!-- PRUVO attribution module: start --><!--BAYAT-->", 1)
            with open(tam, "wb") as f:
                f.write(bayat)
            subprocess.run(["git", "-C", depo, "add", rel], capture_output=True)
            subprocess.run(["git", "-C", depo, "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "-m", "bayat"], capture_output=True)
            c, rk = kos()
            kayit("N2/%s bayat sayfa KIRMIZI (exit 1)" % slug,
                  rk == 1 and ("SAPMA  %s" % rel) in c, "exit=%d" % rk)
            with open(tam, "wb") as f:
                f.write(orij)
            subprocess.run(["git", "-C", depo, "add", rel], capture_output=True)
            subprocess.run(["git", "-C", depo, "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-q", "-m", "geri"], capture_output=True)
        c, rk = kos()
        kayit("N2z geri alindiktan sonra tekrar YESIL", rk == 0, "exit=%d" % rk)

        # --- N4 POZITIF (fail-closed kapsam): TABAN slug kapsamdan dusurulurse KIRMIZI.
        # NEDEN: kapsam sayfalar.STATIK_SAYFALAR'dan gelir; liste DARALIRSA kapi o sayfayi
        # hic olcmez ve SESSIZCE yesil yanar (kapsam-daraltma ile kapi oldurme).
        sy = os.path.join(depo, "tools", "sayfalar.py")
        with open(sy, encoding="utf-8") as f:
            sy_orij = f.read()
        eski_liste = 'STATIK_SAYFALAR = ["hakkimizda", "iletisim", "sss", "gizlilik"]'
        if eski_liste in sy_orij:
            with open(sy, "w", encoding="utf-8") as f:
                f.write(sy_orij.replace(
                    eski_liste, 'STATIK_SAYFALAR = ["hakkimizda", "iletisim", "sss"]', 1))
            c, rk = kos()
            kayit("N4 kapsam daraltilinca KIRMIZI (TABAN slug fail-closed)",
                  rk == 1 and "TABAN slug" in c, "exit=%d" % rk)
            with open(sy, "w", encoding="utf-8") as f:
                f.write(sy_orij)
        else:
            kayit("N4 kapsam daraltilinca KIRMIZI (TABAN slug fail-closed)", False,
                  "capa satiri sayfalar.py'de bulunamadi -> vaka KOSULAMADI")

        # --- N5 NEGATIF (yanlis-pozitif nobeti): ISARETLI BLOK DISINDAKI mesru elle
        # duzenleme (hukuki metin/gövde) commit'lenirse kapi YESIL kalmali — build.py o
        # bolgeye DOKUNMAZ. Bu kapi yalniz build.py'nin URETTIGI bolgeyi olcer.
        rel_n5 = os.path.join(TABAN_SLUGLAR[0], "index.html")
        tam_n5 = os.path.join(depo, rel_n5)
        with open(tam_n5, "rb") as f:
            n5_orij = f.read()
        with open(tam_n5, "wb") as f:
            f.write(n5_orij.replace(b"</body>", b"<!-- elle eklenen mesru not -->\n</body>", 1))
        subprocess.run(["git", "-C", depo, "add", rel_n5], capture_output=True)
        subprocess.run(["git", "-C", depo, "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "elle duzenleme"], capture_output=True)
        c, rk = kos()
        kayit("N5 blok DISI mesru elle duzenleme YESIL kaliyor (yanlis-pozitif yok)",
              rk == 0, "exit=%d" % rk)
        with open(tam_n5, "wb") as f:
            f.write(n5_orij)
        subprocess.run(["git", "-C", depo, "add", rel_n5], capture_output=True)
        subprocess.run(["git", "-C", depo, "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "geri"], capture_output=True)

        # --- KIRMIZI-MUTASYON: kapinin GOVDESI bozulunca yakalaniyor mu
        with open(kapi, encoding="utf-8") as f:
            kaynak = f.read()
        rel0 = os.path.join(TABAN_SLUGLAR[0], "index.html")
        tam0 = os.path.join(depo, rel0)
        with open(tam0, "rb") as f:
            orij0 = f.read()
        with open(tam0, "wb") as f:                       # sapma kur (commit'li HEAD bayat)
            f.write(orij0.replace(b"<!-- PRUVO attribution module: start -->",
                                  b"<!-- PRUVO attribution module: start --><!--BAYAT-->", 1))
        subprocess.run(["git", "-C", depo, "add", rel0], capture_output=True)
        subprocess.run(["git", "-C", depo, "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "bayat-m"], capture_output=True)
        c, rk = kos()
        kayit("N3 taban: mutasyonsuz kapi bu sapmayi GORUYOR", rk == 1, "exit=%d" % rk)

        mutasyonlar = [
            ("M1 karsilastirma kaldirildi (u==t her zaman)",
             "        if u == t:", "        if True:"),
            ("M2 hukum no-op (sapan listesi doldurulmuyor)",
             "        sapan.append(rel)", "        pass"),
            ("M3 build.py hic kosturulmuyor",
             "        p = subprocess.run([sys.executable, BUILD], cwd=ROOT, capture_output=True, text=True)",
             "        p = subprocess.run([sys.executable, \"-c\", \"pass\"], cwd=ROOT, capture_output=True, text=True)"),
            ("M4 cikis kodu daima 0",
             "    return kirmizi, R", "    return False, R"),
        ]
        for ad, eski, yeni in mutasyonlar:
            if eski not in kaynak:
                kayit(ad, False, "MUTASYON UYGULANAMADI: capa satiri kaynakta yok -> %r" % eski)
                continue
            mut_yol = os.path.join(kok, "mutant.py")
            with open(mut_yol, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni, 1))
            # mutant, kapi ile AYNI dizinde kosmali (ROOT tureyisi) -> tools/ icine koy
            hedef = os.path.join(depo, "tools", "_mutant-kapi.py")
            shutil.copyfile(mut_yol, hedef)
            c, rk = kos(hedef)
            # MUTANT sapmayi KACIRMALI (exit 0) -> o satirin YUK TASIDIGI kanitlanir.
            # Mutant hala KIRMIZI yaniyorsa satir olu/kapsamsizdir -> nobetci KIRMIZI.
            kayit(ad, rk == 0,
                  "mutant exit=%d (0 = mutasyon sapmayi kaciriyor, satir yuk tasiyor)" % rk)
            os.remove(hedef)
        with open(tam0, "wb") as f:
            f.write(orij0)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return sonuc


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true",
                    help="kapinin kendi mantigini sina (yanlis-pozitif + kirmizi-mutasyon)")
    a = ap.parse_args()

    if a.kendini_test:
        print("YASAL SAYFA DRIFT KAPISI — IC NOBETCI")
        print("=" * 78)
        sonuc = kendini_test()
        dusen = [s for s in sonuc if not s[1]]
        for ad, gecti, kanit in sonuc:
            print("[%s] %-52s %s" % ("YESIL" if gecti else "KIRMIZI", ad, kanit))
        print("-" * 78)
        print("SONUC: %d/%d yesil, %d kirmizi" % (len(sonuc) - len(dusen), len(sonuc), len(dusen)))
        return 1 if dusen else 0

    print("YASAL SAYFA DRIFT KAPISI  (uretilen icerik == HEAD'deki icerik)")
    print("=" * 78)
    kirmizi, satirlar = olc()
    for s in satirlar:
        print(s)
    print("-" * 78)
    print("SONUC: %s" % ("KIRMIZI ❌ — uretilen yasal sayfa HEAD'den SAPIYOR (yukariya bak)"
                         if kirmizi else
                         "YESIL ✅ — build.py'nin urettigi 4 yasal sayfa commit'li halle BIREBIR"))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())

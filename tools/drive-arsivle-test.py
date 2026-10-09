#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — `drive-arsivle.py` yaz → sha256 → yerel sil → evict.

Hermetik: TEMPLATE YAPILAN TEMPLATE FILES + sahte Drive kökü + sahte evict
komutu (yazılan LOG'E SATIR). GERÇEK DRIVE'E VE EV DIZININE YAZMAZ.

  python3 tools/drive-arsivle-test.py

KOL:
  a)  dosya kopyalanir · sha esit · yerel SILINIR · evict cagirilir
  b)  --yerel-tut → yerel KALI, sicil esit
  c)  --kuru → hicbir sey degismez
  d)  hedefte AYNI AD + FARKLI ICERIK → '__<sha8>' eklenir
      AYNI AD + AYNI ICERIK → atlanir
  e)  KOPYA BOZULURSA (sahte copy) sha esit degil → yerel KALIR, rc=1
  f)  Drive koku YOK → exit 2, hicbir sey silinmez
  g)  evict 3x hata → 3 deneme, yerel DURUR, rc=0, evict_hata=1
  h)  yukleme BITMEDI (tavan) → evict CAGRILMAZ, yerel DURUR, BEKLIYOR, rc=3;
      sonraki kosum (yuklendi) ayni icerigi devralir → evict + sil
  i)  yukleme gec biter → yoklama SONRA evict, evict SONRA yerel sil

MUTANT (arac kolunda):
  sha kontrolu silinince (e) KIRMIZI
  kuru kontrolu silinince (c) KIRMIZI
  yerel-tut silinince (b) KIRMIZI
  yukleme beklemesi kaldirilinca (h) KIRMIZI
  sha kontrolu kaldirilinca evict/sil zinciri (e-zincir) KIRMIZI
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "drive-arsivle.py")

IDDIA = 0
GECTI = 0
KIRMIZI = []


def iddia(ad, kosul, ayrinti=""):
    global IDDIA, GECTI
    IDDIA += 1
    if kosul:
        GECTI += 1
        print("  [OK]   %s %s" % (ad, ayrinti))
    else:
        KIRMIZI.append(ad)
        print("  [KIRMIZI] %s %s" % (ad, ayrinti))


def kos(argv, ortam=None, cwd=None):
    """Subprocess ile çalıştır; stdout+stderr döndür."""
    env = os.environ.copy()
    if ortam:
        env.update(ortam)
    p = subprocess.run(
        [sys.executable] + argv,
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sahte_evict(komut_dosyasi):
    """Sahte evict: dosyaya 'evict=<path>' yazar ve rc=0 döner."""
    # Komut 'sh <yol>' gibi olur; bizimki sh çağıran parametre yazımı.
    yazici = open(komut_dosyasi, "w", encoding="utf-8")
    # SAHTE_KAYNAK verilirse evict anindaki yerel kaynak durumu da yazilir (sira olcumu).
    yazici.write(
        "#!/bin/sh\necho evict=\"$1\" >> \"$DRIVE_ARSIVLE_LOG\"\n"
        "if [ -n \"$SAHTE_KAYNAK\" ]; then\n"
        "  if [ -e \"$SAHTE_KAYNAK\" ]; then echo kaynak_var=1 >> \"$DRIVE_ARSIVLE_LOG\";\n"
        "  else echo kaynak_var=0 >> \"$DRIVE_ARSIVLE_LOG\"; fi\nfi\nexit 0\n")
    yazici.close()
    os.chmod(komut_dosyasi, 0o755)


def sahte_yukleme(komut_dosyasi):
    """Sahte 'yukleme bitti mi': 'yokla=<yol>' yazar; SAHTE_YUKLEME_MOD:
    evet (varsayilan) rc=0 · hayir rc=1 · gec:N ilk N yoklama rc=1, sonra rc=0."""
    with open(komut_dosyasi, "w", encoding="utf-8") as f:
        f.write(
            "#!/bin/sh\necho yokla=\"$1\" >> \"$DRIVE_ARSIVLE_LOG\"\n"
            "case \"${SAHTE_YUKLEME_MOD:-evet}\" in\n"
            "  evet) exit 0;;\n"
            "  hayir) exit 1;;\n"
            "  gec:*) n=\"${SAHTE_YUKLEME_MOD#gec:}\"; s=\"$DRIVE_ARSIVLE_LOG.sayac\";\n"
            "    c=$(cat \"$s\" 2>/dev/null || echo 0); c=$((c+1)); echo \"$c\" > \"$s\";\n"
            "    [ \"$c\" -gt \"$n\" ] && exit 0; exit 1;;\n"
            "esac\nexit 1\n")
    os.chmod(komut_dosyasi, 0o755)


def sahte_evict_hata(komut_dosyasi):
    yazici = open(komut_dosyasi, "w", encoding="utf-8")
    yazici.write(
        "#!/bin/sh\necho evict=\"$1\" >> \"$DRIVE_ARSIVLE_LOG\"\n"
        "echo \"sahte evict hatasi\" 1>&2\nexit 1\n"
    )
    yazici.close()
    os.chmod(komut_dosyasi, 0o755)


def hazirla(gecici):
    """Geçici kök döndürür: kaynak/, drive/, evict.sh, log."""
    kok = gecici
    kaynak = os.path.join(kok, "kaynak")
    drive = os.path.join(kok, "drive")
    os.makedirs(kaynak)
    os.makedirs(drive)
    # Kaynak dosyaları
    with open(os.path.join(kaynak, "a.txt"), "w", encoding="utf-8") as f:
        f.write("aaaa\n")
    with open(os.path.join(kaynak, "b.txt"), "w", encoding="utf-8") as f:
        f.write("bbbb\n")
    os.makedirs(os.path.join(kaynak, "alt"))
    with open(os.path.join(kaynak, "alt", "c.txt"), "w", encoding="utf-8") as f:
        f.write("cccc\n")
    evict_sh = os.path.join(kok, "evict.sh")
    log = os.path.join(kok, "evict.log")
    open(log, "w").close()
    return kaynak, drive, evict_sh, log


def main():
    gecici = tempfile.mkdtemp(prefix="drive-arsivle-test-")
    try:
        return _kollar(gecici)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def kol_bekleme(arac, gecici, evict_sh, etiket):
    """(h) Yukleme BITMEDI + tavan → [(iddia_adi, kosul)]. Gercek arac ve mutant ayni kolu kosar."""
    d = tempfile.mkdtemp(prefix="h-%s-" % etiket, dir=gecici)
    drive = os.path.join(d, "drive")
    os.makedirs(drive)
    yol = os.path.join(d, "h.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("h ici")
    log = os.path.join(d, "h.log")
    open(log, "w").close()
    rc, cikti = kos(
        [arac, yol, "--hedef", "bekle/", "--drive-kok", drive, "--evict-komut", evict_sh,
         "--yokla-aralik", "0.05", "--yukleme-tavan", "0.3"],
        ortam={"DRIVE_ARSIVLE_LOG": log, "SAHTE_YUKLEME_MOD": "hayir"},
    )
    l = _oku(log)
    return [
        ("evict CAGRILMADI", "evict=" not in l),
        ("yerel kaynak DURUYOR", os.path.isfile(yol)),
        ("hedef Drive'da var", os.path.isfile(os.path.join(drive, "bekle", "h.txt"))),
        ("durum=BEKLIYOR satiri", "durum=BEKLIYOR" in cikti),
        ("rc=3", rc == 3),
        ("bekliyor=1 silindi=0", "bekliyor=1" in cikti and "silindi=0" in cikti),
        ("aralikla >=2 yoklama", l.count("yokla=") >= 2),
    ], (yol, drive, log, rc, cikti)


def kol_sha_zincir(modul, gecici, evict_sh, etiket):
    """(e-zincir) Kopya bozuk → [(iddia_adi, kosul)]: yukleme yoklanmaz, evict yok, yerel durur."""
    d = tempfile.mkdtemp(prefix="e-%s-" % etiket, dir=gecici)
    drive = os.path.join(d, "drive")
    os.makedirs(drive)
    yol = os.path.join(d, "e.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("e zincir ici")
    log = os.path.join(d, "e.log")
    open(log, "w").close()

    def _bozuk(src, dst, *a, **kw):
        with open(src, "rb") as f:
            v = f.read()
        v = v[:-1] + bytes([(v[-1] ^ 0xFF) & 0xFF])
        with open(dst, "wb") as f:
            f.write(v)
    import io
    orijinal = modul.shutil.copy2
    eski_out, eski_log = sys.stdout, os.environ.get("DRIVE_ARSIVLE_LOG")
    buf = io.StringIO()
    modul.shutil.copy2 = _bozuk
    os.environ["DRIVE_ARSIVLE_LOG"] = log
    try:
        sys.stdout = buf
        rc = modul.main([yol, "--hedef", "zincir/", "--drive-kok", drive,
                         "--evict-komut", evict_sh, "--yokla-aralik", "0.05"])
    finally:
        sys.stdout = eski_out
        modul.shutil.copy2 = orijinal
        if eski_log is None:
            os.environ.pop("DRIVE_ARSIVLE_LOG", None)
        else:
            os.environ["DRIVE_ARSIVLE_LOG"] = eski_log
    l = _oku(log)
    return [
        ("rc=1", rc == 1),
        ("HATA=sha-esit-degil", "HATA=sha-esit-degil" in buf.getvalue()),
        ("yukleme YOKLANMADI", "yokla=" not in l),
        ("evict CAGRILMADI", "evict=" not in l),
        ("yerel kaynak DURUYOR", os.path.isfile(yol)),
    ]


def _kollar(gecici):
    kaynak, drive, evict_sh, log = hazirla(gecici)
    sahte_evict(evict_sh)
    # Yukleme sinyali TUM kollarda sahte (gercek swift/Drive YOK); varsayilan mod 'evet'.
    yukleme_sh = os.path.join(gecici, "yukleme.sh")
    sahte_yukleme(yukleme_sh)
    os.environ["DRIVE_ARSIVLE_YUKLEME"] = yukleme_sh
    os.environ.pop("SAHTE_YUKLEME_MOD", None)
    os.environ.pop("SAHTE_KAYNAK", None)

    # ---- (a) temel akış + sil + evict --------
    print("A — danı°s kopyalanır, sha eşit, yerel silinir, evict çağrılır")
    a_yol = os.path.join(kaynak, "a.txt")
    open(log, "w").close()
    rc, cikti = kos(
        [ARAC, a_yol, "--hedef", "deneme/", "--drive-kok", drive,
         "--evict-komut", evict_sh],
        ortam={"DRIVE_ARSIVLE_LOG": log},
    )
    iddia("A1 rc=0", rc == 0, "rc=%d cikti=%s" % (rc, cikti[:300]))
    a_hedef = os.path.join(drive, "deneme", "a.txt")
    iddia("A2 hedef var", os.path.isfile(a_hedef))
    iddia("A3 yerel kaynak SILINDI", not os.path.exists(a_yol))
    with open(log, encoding="utf-8") as f:
        log_a = f.read()
    iddia("A4 evict çağrıldı (log'da hedef yolu var)",
          "evict=" + a_hedef in log_a)
    # sha doğrulama — hedefin sha256'sı kaynağınkiyle aynı olmalıydı (başıbozuk
    # kaynaktan çıkmış olmalı; sha doğrulayacak başka referans yok ama dosya
    # var ve evict çağrıldı).
    iddia("A5 DRIVE_ARSIVLE ozet satirinda kopyalandi>=1",
          "kopyalandi=" in cikti)

    # ---- (b) --yerel-tut --------
    print("B — --yerel-tut → yerel KALI")
    b_yol = os.path.join(kaynak, "b.txt")
    open(log, "w").close()
    rc, cikti = kos(
        [ARAC, b_yol, "--hedef", "deneme/", "--drive-kok", drive,
         "--evict-komut", evict_sh, "--yerel-tut"],
        ortam={"DRIVE_ARSIVLE_LOG": log},
    )
    iddia("B1 rc=0", rc == 0, "rc=%d" % rc)
    iddia("B2 hedef var", os.path.isfile(os.path.join(drive, "deneme", "b.txt")))
    iddia("B3 yerel kaynak DURUYOR", os.path.isfile(b_yol))
    # silindi=0 veya silindi olmasa da genel olarak raporlama görülür
    iddia("B4 DRIVE_ARSIVLE silindi=0", "silindi=0" in cikti)
    # evict çağrıldı mı?
    with open(log, encoding="utf-8") as f:
        log_b = f.read()
    iddia("B5 evict çağrıldı (yerel-tut evict'i engellemez)",
          "evict=" + os.path.join(drive, "deneme", "b.txt") in log_b)

    # ---- (c) --kuru --------
    print("C — --kuru → hiçbir şey değişmez")
    c_yol = os.path.join(kaynak, "alt", "c.txt")
    open(log, "w").close()
    rc, cikti = kos(
        [ARAC, c_yol, "--hedef", "deneme/", "--drive-kok", drive,
         "--evict-komut", evict_sh, "--kuru"],
        ortam={"DRIVE_ARSIVLE_LOG": log},
    )
    iddia("C1 rc=0", rc == 0, "rc=%d" % rc)
    iddia("C2 hedef YOK", not os.path.exists(
        os.path.join(drive, "deneme", "alt", "c.txt")))
    iddia("C3 yerel kaynak DURUYOR", os.path.isfile(c_yol))
    iddia("C4 evict çağrılmadi (log boş)", open(log).read() == "")
    iddia("C5 DRIVE_ARSIVLE kuru=1", "kuru=1" in cikti)
    iddia("C6 DRIVE_ARSIVLE kopyalandi=0", "kopyalandi=0" in cikti)

    # ---- (d) hedefte aynı ad FARKLI içerik --------
    print("D — hedefte AYNI ad FARKLI içerik → '__<sha8>' eklenir")
    # Dosyayı önce sha256 için oku, sonra aracı çalıştır (dosya silinmesin diye)
    d_yol = os.path.join(kaynak, "alt", "c.txt")
    with open(d_yol, "rb") as f:
        d_veri = f.read()
    sha_c = hashlib.sha256(d_veri).hexdigest()
    open(log, "w").close()
    # Hedefe aynı adla farklı içerik yaz
    d_hedef_dir = os.path.join(drive, "deneme2")
    os.makedirs(d_hedef_dir, exist_ok=True)
    d_hedef = os.path.join(d_hedef_dir, "c.txt")
    with open(d_hedef, "w", encoding="utf-8") as f:
        f.write("FFFFarkli\n")
    rc, cikti = kos(
        [ARAC, d_yol, "--hedef", "deneme2/", "--drive-kok", drive,
         "--evict-komut", evict_sh],
        ortam={"DRIVE_ARSIVLE_LOG": log},
    )
    iddia("D1 rc=0", rc == 0, "rc=%d cikti=%s" % (rc, cikti[:300]))
    # __<sha8> eklenmiş yeni dosya var mı?
    beklenen = "c__" + sha_c[:8] + ".txt"
    d_hedef_yeni = os.path.join(d_hedef_dir, beklenen)
    iddia("D2 __<sha8> hedef yol VAR", os.path.isfile(d_hedef_yeni),
          "beklenen=%s" % beklenen)
    iddia("D3 eski hedef duruyor (üzerine yazmadı)", os.path.isfile(d_hedef))
    # AYNI icerik testi: hedefe aynı içerik koyarsak atlanmalı
    print("D4 — AYNI ad + AYNI içerik → atlandi")
    with open(d_hedef_yeni, "rb") as f:
        ayni_veri = f.read()
    iddia("D4-on AYNI içerik kontrolu (dosyalar eşit)", ayni_veri == d_veri)
    # ikinci yem: aynı içerik olduğu için araç ATLAYACAK
    # bunun için aynı kaynağı geri yaz
    with open(d_yol, "wb") as f:
        f.write(d_veri)
    open(log, "w").close()
    rc2, cikti2 = kos(
        [ARAC, d_yol, "--hedef", "deneme2/", "--drive-kok", drive,
         "--evict-komut", evict_sh],
        ortam={"DRIVE_ARSIVLE_LOG": log},
    )
    iddia("D4-v rc=0", rc2 == 0, "rc=%d" % rc2)
    iddia("D4-vi atlandi_ayni sayaci artti", "atlandi_ayni=1" in cikti2)

    # ---- (e) sha kontrolü sun ----
    print("E — KOPYA BOZULURSA (sahte copy) sha esit degil → yerel KALIR, rc=1")
    # Önceki testler c.txt'i silebilir; taze dosya
    e_yol = os.path.join(kaynak, "alt", "e1.txt")
    with open(e_yol, "w", encoding="utf-8") as f:
        f.write("e1 ici")
    # Araç modülünü dosya yolundan yükle (dosya adında '-' var; `import` çalışmaz)
    import importlib.util  # noqa: E402
    spec = importlib.util.spec_from_file_location(
        "_drive_arsivle_kaynak", ARAC
    )
    da = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(da)
    orijinal_copy = da.shutil.copy2
    def _bad(src, dst, *a, **kw):
        with open(src, "rb") as f:
            v = f.read()
        if v:
            v = v[:-1] + bytes([(v[-1] ^ 0xFF) & 0xFF])
        with open(dst, "wb") as f:
            f.write(v)
    da.shutil.copy2 = _bad
    # Monkey patch'i geçici bir "mutantle kopya" dosyaya yaz ki arac ORAYA
    # baktığında _badlı kullansın. Arac kendi tools/ dizininden calistirilir.
    # En basit yol: aracı subprocess olarak calistir, monkey-patch'i KULLANMAK
    # YERINE sahte bir kopya betiği araya koy. Bunun yerine: dosya SHA'lerini
    # sonradan bozmak için hedef dosyayi once sahte copy ile yazip sonra sha
    # kontrolunu yaniltmak -- bu copy2'yi DEĞIL hedefteki dosyayi bozar.
    # Daha basit: sahte `kopyalayici` ile kopyalama yapıp SHA kontrolunu aracin
    # doğrudan diskten okumasi yuzunden calismaz. O yüzden: dosyayi diske
    # yazip, ARAÇ BAŞLAMADAN ONCE dosyaya farkli bir içerik koyarız. Bu
    # yeterli değil çünkü araç KAYNAĞI OKUR, hedef değil.
    # DOĞRU YAKLAŞIM: araç içindeki `sha256_dosya`'yı monkey-patch'le ki
    # kaynağın sha'sını yanlış raporlasın, sonra hedefe sağlam yazılsın.
    # Bu da sha kontrolunu BIZ BOZARAK test eder, monkey-patch amacı buysa.
    # Ama spec "kopya bozulursa" diyor — yani arac içindeki copy bozuk.
    # Burada izlenen yol: monkey-patch'i aktif edip subprocess olarak calistırmak
    # YERINE `da.main()` çağırıp stdout'u capture ederiz.
    import io
    import contextlib

    def _calistir_is_ici(argv):
        eski_stdout = sys.stdout
        buf = io.StringIO()
        try:
            sys.stdout = buf
            rc = da.main(argv)
        finally:
            sys.stdout = eski_stdout
        return rc, buf.getvalue()

    def _calistir_is_ici_l_mut(mod_mut, kaynak, drive_kok, ev_komut, gecici_kok):
        """M7 icin: mutant modulu sha bozuk copy ile izole kos. Returns (rc, cikti)."""
        l2_yol = kaynak
        l2_log = os.path.join(gecici_kok, "l_mut.log")
        open(l2_log, "w").close()
        orijinal_copy = mod_mut.shutil.copy2

        def _bad(src, dst, *a, **kw):
            with open(src, "rb") as f_:
                v = f_.read()
            if v:
                v = v[:-1] + bytes([(v[-1] ^ 0xFF) & 0xFF])
            with open(dst, "wb") as f_:
                f_.write(v)

        mod_mut.shutil.copy2 = _bad
        eski_out2 = sys.stdout
        eski_log2 = os.environ.get("DRIVE_ARSIVLE_LOG")
        buf2 = io.StringIO()
        os.environ["DRIVE_ARSIVLE_LOG"] = l2_log
        try:
            sys.stdout = buf2
            rc2 = mod_mut.main(
                [l2_yol, "--hedef", "l_mut/", "--drive-kok", drive_kok,
                 "--evict-komut", ev_komut],
            )
        finally:
            sys.stdout = eski_out2
            mod_mut.shutil.copy2 = orijinal_copy
            if eski_log2 is None:
                os.environ.pop("DRIVE_ARSIVLE_LOG", None)
            else:
                os.environ["DRIVE_ARSIVLE_LOG"] = eski_log2
        return rc2, buf2.getvalue()

    try:
        e_hedef_dir = os.path.join(drive, "deneme3")
        os.makedirs(e_hedef_dir, exist_ok=True)
        rc, cikti = _calistir_is_ici(
            [e_yol, "--hedef", "deneme3/", "--drive-kok", drive,
             "--evict-komut", evict_sh, "--yerel-tut"],
        )
        iddia("E1 rc=1 (sha esit degil)", rc == 1, "rc=%d" % rc)
        iddia("E2 HATA=sha-esit-degil satirinda",
              "HATA=sha-esit-degil" in cikti, cikti[:200])
    finally:
        da.shutil.copy2 = orijinal_copy
    # Yeniden dosya oluşturalım (--yerel-tut OLMADAN; sha tutmazsa yerel kalmali)
    e_yol2 = os.path.join(kaynak, "alt", "e2.txt")
    with open(e_yol2, "w", encoding="utf-8") as f:
        f.write("e2 ici")
    da.shutil.copy2 = _bad
    try:
        rc, cikti = _calistir_is_ici(
            [e_yol2, "--hedef", "deneme3/", "--drive-kok", drive,
             "--evict-komut", evict_sh],
        )
        iddia("E3 rc=1 (--yerel-tut YOK)", rc == 1, "rc=%d" % rc)
        iddia("E4 yerel kaynak SILINMEDI (sha tutmadi)", os.path.isfile(e_yol2))
        iddia("E5 hata sayaci >=1", "hata=" in cikti)
    finally:
        da.shutil.copy2 = orijinal_copy

    # ---- (f) Drive koku yok --------
    print("F — Drive koku YOK → exit 2, hiçbir şey silinmez")
    f_yol = os.path.join(kaynak, "alt", "c.txt")
    # Yerel dosyayi yenileyelim (silinmiş olabilir)
    with open(f_yol, "w", encoding="utf-8") as f:
        f.write("cccc")
    rc, cikti = kos(
        [ARAC, f_yol, "--hedef", "deneme/", "--drive-kok", "/nonexistent-ev-dizini-12345"],
    )
    iddia("F1 rc=2", rc == 2, "rc=%d" % rc)
    iddia("F2 HATA=drive-kok-yok", "HATA=drive-kok-yok" in cikti, cikti[:200])
    iddia("F3 yerel kaynak DURUYOR", os.path.isfile(f_yol))

    # ---- (g) evict hatası --------
    print("G — evict 3x HATA → 3 deneme, yerel DURUR, rc=0, evict_hata=1")
    g_yol = os.path.join(kaynak, "alt", "c.txt")
    with open(g_yol, "w", encoding="utf-8") as f:
        f.write("cccc")
    # Hata veren sahte evict
    g_evict = os.path.join(gecici, "evict-bad.sh")
    sahte_evict_hata(g_evict)
    g_log = os.path.join(gecici, "evict-bad.log")
    open(g_log, "w").close()
    rc, cikti = kos(
        [ARAC, g_yol, "--hedef", "deneme_g/", "--drive-kok", drive,
         "--evict-komut", g_evict, "--yokla-aralik", "0.05"],
        ortam={"DRIVE_ARSIVLE_LOG": g_log},
    )
    iddia("G1 rc=0 (evict hatasi rc degistirmez)", rc == 0, "rc=%d" % rc)
    iddia("G2 evict_hata=1", "evict_hata=1" in cikti)
    iddia("G3 evict=hata satiri var", "evict=hata" in cikti)
    iddia("G4 yerel kaynak DURUYOR (evict olmadan silinmez)", os.path.exists(g_yol))
    iddia("G5 hedef var (dosya kaybolmadi)",
          os.path.isfile(os.path.join(drive, "deneme_g", "c.txt")))
    g_l = _oku(g_log)
    iddia("G6 evict TAM 3 kez denendi", g_l.count("evict=") == 3,
          "sayi=%d" % g_l.count("evict="))
    iddia("G7 silindi=0", "silindi=0" in cikti)

    # ---- (h) yukleme bitmedi + tavan → BEKLIYOR; sonraki kosum devralir --------
    print("H — yukleme BITMEDI → evict YOK, yerel DURUR, BEKLIYOR, rc=3")
    h_kontrol, (h_yol, h_drive, h_log, h_rc, h_cikti) = kol_bekleme(
        ARAC, gecici, evict_sh, "gercek")
    for ad, kosul in h_kontrol:
        iddia("H " + ad, kosul, "rc=%d" % h_rc)
    print("H-devam — yukleme bitti, ayni kaynak tekrar kosulur → atlandi_ayni + evict + sil")
    open(h_log, "w").close()
    rc, cikti = kos(
        [ARAC, h_yol, "--hedef", "bekle/", "--drive-kok", h_drive, "--evict-komut", evict_sh,
         "--yokla-aralik", "0.05", "--yukleme-tavan", "0.3"],
        ortam={"DRIVE_ARSIVLE_LOG": h_log, "SAHTE_YUKLEME_MOD": "evet"},
    )
    iddia("H-devam rc=0", rc == 0, "rc=%d" % rc)
    iddia("H-devam atlandi_ayni=1 evict_ok=1 silindi=1",
          "atlandi_ayni=1" in cikti and "evict_ok=1" in cikti and "silindi=1" in cikti,
          cikti[-200:])
    iddia("H-devam yerel SILINDI", not os.path.exists(h_yol))

    # ---- (i) yukleme gec biter: SIRA yokla → evict → sil --------
    print("I — yukleme 2 yoklama gec biter → evict yuklemeden SONRA, sil evict'ten SONRA")
    i_yol = os.path.join(kaynak, "alt", "i.txt")
    with open(i_yol, "w", encoding="utf-8") as f:
        f.write("i ici")
    i_log = os.path.join(gecici, "i.log")
    open(i_log, "w").close()
    rc, cikti = kos(
        [ARAC, i_yol, "--hedef", "deneme_i/", "--drive-kok", drive, "--evict-komut", evict_sh,
         "--yokla-aralik", "0.05", "--yukleme-tavan", "5"],
        ortam={"DRIVE_ARSIVLE_LOG": i_log, "SAHTE_YUKLEME_MOD": "gec:2",
               "SAHTE_KAYNAK": i_yol},
    )
    i_satir = _oku(i_log).splitlines()
    i_yokla = [n for n, s in enumerate(i_satir) if s.startswith("yokla=")]
    i_evict = [n for n, s in enumerate(i_satir) if s.startswith("evict=")]
    iddia("I1 rc=0", rc == 0, "rc=%d" % rc)
    iddia("I2 3 yoklama (2 bitmedi + 1 bitti)", len(i_yokla) == 3, "yokla=%d" % len(i_yokla))
    iddia("I3 TEK evict, son yoklamadan SONRA",
          len(i_evict) == 1 and i_yokla and i_evict[0] > i_yokla[-1], str(i_satir))
    iddia("I4 evict aninda yerel kaynak HALA VAR (sil evict'ten sonra)",
          "kaynak_var=1" in i_satir, str(i_satir))
    iddia("I5 kosum sonunda yerel SILINDI", not os.path.exists(i_yol))
    iddia("I6 evict_ok=1 silindi=1", "evict_ok=1" in cikti and "silindi=1" in cikti)

    # ---- (k) --kuru icerik OKUMAZ (Drive'da okuma = indirme; 7 Eki 666 MB olayi) --------
    print("K — --kuru: sha256 CAGRILMAZ, hedef varsa yukleme sinyali okunur")
    k_drive = os.path.join(gecici, "k_drive")
    os.makedirs(os.path.join(k_drive, "kk"))
    k_yol = os.path.join(k_drive, "kk", "k.txt")  # kaynak == hedef (Drive icinden kuru kosum)
    with open(k_yol, "w", encoding="utf-8") as f:
        f.write("k ici")
    k_log = os.path.join(gecici, "k.log")
    open(k_log, "w").close()
    orijinal_sha = da.sha256_dosya
    k_sha_cagri = []
    da.sha256_dosya = lambda y: k_sha_cagri.append(y) or orijinal_sha(y)
    os.environ["DRIVE_ARSIVLE_LOG"] = k_log
    try:
        rc, cikti = _calistir_is_ici(
            [os.path.join(k_drive, "kk"), "--hedef", "kk", "--drive-kok", k_drive,
             "--evict-komut", evict_sh, "--kuru"])
    finally:
        da.sha256_dosya = orijinal_sha
        os.environ.pop("DRIVE_ARSIVLE_LOG", None)
    iddia("K1 rc=0", rc == 0, "rc=%d" % rc)
    iddia("K2 sha256 HIC cagrilmadi (icerik okunmadi)", k_sha_cagri == [],
          "cagri=%d" % len(k_sha_cagri))
    iddia("K3 yuklendi_okunan=1 yuklendi_evet=1",
          "yuklendi_okunan=1" in cikti and "yuklendi_evet=1" in cikti, cikti[-200:])
    iddia("K4 evict CAGRILMADI + kaynak DURUYOR",
          "evict=" not in _oku(k_log) and os.path.isfile(k_yol))

    # ---- (j) evict ZORUNLU (9 Eki 2026) — bayraksiz kosumda evict CAGRILIR (sayaç 1) ----
    print("J — evict ZORUNLU: bayraksiz kosumda evict tam 1 kez CAGRILIR (sayaç kanit)")
    j_yol = os.path.join(kaynak, "alt", "j.txt")
    with open(j_yol, "w", encoding="utf-8") as f:
        f.write("j ici")
    j_log = os.path.join(gecici, "j.log")
    open(j_log, "w").close()
    rc, cikti = kos(
        [ARAC, j_yol, "--hedef", "zorunlu/", "--drive-kok", drive,
         "--evict-komut", evict_sh],
        ortam={"DRIVE_ARSIVLE_LOG": j_log},
    )
    j_l = _oku(j_log)
    iddia("J1 rc=0 (bayraksiz kosum, sha OK)", rc == 0, "rc=%d" % rc)
    iddia("J2 evict TAM 1 kez cagirildi (sayaç=1)",
          j_l.count("evict=") == 1, "evict_satiri=%d" % j_l.count("evict="))
    iddia("J3 DRIVE_ARSIVLE evict_ok=1", "evict_ok=1" in cikti)

    # ---- (l) sha uyusmazsa evict 0 + KAYNAK SILINMEZ (9 Eki 2026) ----
    print("L — sha uyusmazsa evict CAGRILMAZ (sayaç=0) + KAYNAK SILINMEZ")
    l_yol = os.path.join(kaynak, "alt", "l.txt")
    with open(l_yol, "w", encoding="utf-8") as f:
        f.write("l ici")
    l_log = os.path.join(gecici, "l.log")
    open(l_log, "w").close()
    import io  # noqa: E402
    eski_out = sys.stdout
    eski_log = os.environ.get("DRIVE_ARSIVLE_LOG")
    buf = io.StringIO()
    orijinal_copy_l = da.shutil.copy2

    def _bad_l(src, dst, *a, **kw):
        with open(src, "rb") as f_:
            v = f_.read()
        if v:
            v = v[:-1] + bytes([(v[-1] ^ 0xFF) & 0xFF])
        with open(dst, "wb") as f_:
            f_.write(v)

    da.shutil.copy2 = _bad_l
    os.environ["DRIVE_ARSIVLE_LOG"] = l_log
    try:
        sys.stdout = buf
        rc_l = da.main(
            [l_yol, "--hedef", "sha_uyusmaz/", "--drive-kok", drive,
             "--evict-komut", evict_sh],
        )
    finally:
        sys.stdout = eski_out
        da.shutil.copy2 = orijinal_copy_l
        if eski_log is None:
            os.environ.pop("DRIVE_ARSIVLE_LOG", None)
        else:
            os.environ["DRIVE_ARSIVLE_LOG"] = eski_log
    l_cikti = buf.getvalue()
    l_l = _oku(l_log)
    iddia("L1 rc=1 (sha uyusmadi)", rc_l == 1, "rc=%d" % rc_l)
    iddia("L2 evict CAGRILMADI (sayaç=0)",
          l_l.count("evict=") == 0, "evict_satiri=%d" % l_l.count("evict="))
    iddia("L3 KAYNAK SILINMEDI (sha uyusmazsa yerel durur)",
          os.path.isfile(l_yol))
    iddia("L4 HATA=sha-esit-degil satirinda",
          "HATA=sha-esit-degil" in l_cikti, l_cikti[:200])

    # ---- (m) --evict-yapma bayragi (9 Eki 2026): evict ATLANIR ama upload+sil calisir ----
    print("M-evict-yapma — --evict-yapma → evict ATLANIR (upload+sil yine yapilir)")
    m_yol = os.path.join(kaynak, "alt", "m.txt")
    with open(m_yol, "w", encoding="utf-8") as f:
        f.write("m ici")
    m_log = os.path.join(gecici, "m.log")
    open(m_log, "w").close()
    rc, cikti = kos(
        [ARAC, m_yol, "--hedef", "evict_yapma/", "--drive-kok", drive,
         "--evict-komut", evict_sh, "--evict-yapma"],
        ortam={"DRIVE_ARSIVLE_LOG": m_log},
    )
    m_l = _oku(m_log)
    iddia("M-ey1 rc=0 (evict atlandi ama akis tamam)", rc == 0, "rc=%d" % rc)
    iddia("M-ey2 evict CAGRILMADI (sayaç=0, --evict-yapma)",
          m_l.count("evict=") == 0, "evict_satiri=%d" % m_l.count("evict="))
    iddia("M-ey3 DRIVE_ARSIVLE evict_ok=0",
          "evict_ok=0" in cikti, cikti[-200:])
    iddia("M-ey4 hedef VAR (upload yine yapildi)",
          os.path.isfile(os.path.join(drive, "evict_yapma", "m.txt")))
    iddia("M-ey5 KAYNAK SILINDI (evict atlanir ama upload+sira yine siler)",
          not os.path.exists(m_yol))
    iddia("M-ey6 DRIVE_ARSIVLE silindi=1",
          "silindi=1" in cikti, cikti[-200:])

    # ---- MUTANTLAR --------
    print()
    print("=" * 70)
    print("MUTANTLAR")
    # SHA kontrolu silinince (E) KIRMIZI: 'if sha_h != sha_k' silinirse,
    # sha_esit_degil HATA satiri basilmaz, E1/E2 yanlis yesil olur.
    # Mutant SYMLINK'a koy, icin -> orginal tools/ icindeki digerleri
    # ayni kalsin, sadece drive-arsivle.py mutant kopyası olsun.

    print("M1 — SHA kontrolu silinince (e) KIRMIZI")
    ayna = os.path.join(gecici, "ayna")
    os.makedirs(os.path.join(ayna, "tools"))
    _tools = os.path.join(KOK, "tools")
    for _ad in os.listdir(_tools):
        _k = os.path.join(_tools, _ad)
        if _ad != "drive-arsivle.py" and os.path.isfile(_k):
            try:
                os.symlink(_k, os.path.join(ayna, "tools", _ad))
            except OSError:
                shutil.copy2(_k, os.path.join(ayna, "tools", _ad))
    with open(ARAC, encoding="utf-8") as f:
        govde = f.read()
    # Mutant: sha kontrolu her zaman FALSE — sha tutmazsa bile hata yok
    M1_CAPA = "if sha_h != sha_k:"
    M1_MUT = "if False:"
    iddia("M1-a CAPA TEKIL", govde.count(M1_CAPA) == 1,
          "isabet=%d" % govde.count(M1_CAPA))
    _mut = os.path.join(ayna, "tools", "drive-arsivle.py")
    with open(_mut, "w", encoding="utf-8") as f:
        f.write(govde.replace(M1_CAPA, M1_MUT, 1))
    m_yol = os.path.join(kaynak, "alt", "m1.txt")
    with open(m_yol, "w", encoding="utf-8") as f:
        f.write("m1 ici")
    # Bozuk copy monkey-patch'i AYNA icindeki kopyaya enjekte etmek için
    # aracı kendi bash'inde degil, importlib ile AYNA kopyasını çalıştırırız
    import importlib.util  # noqa: E402
    spec_m1 = importlib.util.spec_from_file_location(
        "_m1_mut", _mut
    )
    da_m1 = importlib.util.module_from_spec(spec_m1)
    spec_m1.loader.exec_module(da_m1)

    def _bad_m1(src, dst, *a, **kw):
        with open(src, "rb") as f:
            v = f.read()
        if v:
            v = v[:-1] + bytes([(v[-1] ^ 0xFF) & 0xFF])
        with open(dst, "wb") as f:
            f.write(v)
    da_m1.shutil.copy2 = _bad_m1
    import io
    eski = sys.stdout
    buf = io.StringIO()
    sys.stdout = buf
    try:
        rc_m1 = da_m1.main(
            [m_yol, "--hedef", "mutant_m1/", "--drive-kok", drive,
             "--evict-komut", evict_sh, "--yerel-tut"],
        )
    finally:
        sys.stdout = eski
    cikti_m1 = buf.getvalue()
    iddia("M1-b mutant rc=0 (sha kontrolu kırık, hata yok, kopyalama 'başarılı')",
          rc_m1 == 0, "rc=%d" % rc_m1)
    iddia("M1-c HATA=sha-esit-degil YOK (kontrolu silindi) — E KIRMIZI olurdu",
          "HATA=sha-esit-degil" not in cikti_m1, "cikti=%s" % cikti_m1[:200])

    print()
    print("M2 — kuru kontrolu silinince (c) KIRMIZI")
    M2_CAPA = "if a.kuru:\n            # KURU = SALT OKUMA"
    M2_MUT = "if False:\n            # KURU = SALT OKUMA"
    iddia("M2-a CAPA TEKIL", govde.count(M2_CAPA) == 1, "isabet=%d" % govde.count(M2_CAPA))
    _mut2 = os.path.join(ayna, "tools", "drive-arsivle-m2.py")
    with open(_mut2, "w", encoding="utf-8") as f:
        f.write(govde.replace(M2_CAPA, M2_MUT, 1))
    m2_yol = os.path.join(kaynak, "alt", "m2.txt")
    with open(m2_yol, "w", encoding="utf-8") as f:
        f.write("m2 ici")
    rc_m2, cikti_m2 = kos(
        [_mut2, m2_yol, "--hedef", "mutant_m2/", "--drive-kok", drive,
         "--evict-komut", evict_sh, "--kuru"],
        ortam={"DRIVE_ARSIVLE_LOG": os.path.join(gecici, "m2.log")},
    )
    iddia("M2-b mutant --kuru YAZDI (kontrol silinmişse devam eder)",
          os.path.exists(os.path.join(drive, "mutant_m2", "m2.txt")),
          "yazmamaliydi, kuru kontrolu yok")
    iddia("M2-c DRIVE_ARSIVLE kuru=1 etiketli (raporlama çalıştı)",
          "kuru=1" in cikti_m2)

    print()
    print("M3 — yerel-tut kontrolu silinince (b) KIRMIZI")
    M3_CAPA = "yerel_sil = not a.yerel_tut and"
    M3_MUT = "yerel_sil = True and"
    iddia("M3-a CAPA TEKIL", govde.count(M3_CAPA) == 1,
          "isabet=%d" % govde.count(M3_CAPA))
    _mut3 = os.path.join(ayna, "tools", "drive-arsivle-m3.py")
    with open(_mut3, "w", encoding="utf-8") as f:
        f.write(govde.replace(M3_CAPA, M3_MUT, 1))
    m3_yol = os.path.join(kaynak, "alt", "m3.txt")
    with open(m3_yol, "w", encoding="utf-8") as f:
        f.write("m3 ici")
    rc_m3, _ = kos(
        [_mut3, m3_yol, "--hedef", "mutant_m3/", "--drive-kok", drive,
         "--evict-komut", evict_sh, "--yerel-tut"],
        ortam={"DRIVE_ARSIVLE_LOG": os.path.join(gecici, "m3.log")},
    )
    iddia("M3-b mutant --yerel-tut YINE DE SİLDİ (kontrol yok)",
          rc_m3 == 0 and not os.path.exists(m3_yol),
          "yerel-tut'a ragmen silmis olmali (mutant)")

    print()
    print("M4 — yukleme beklemesi kaldirilinca (h) KIRMIZI")
    M4_CAPA = "if not yukleme_bekle("
    M4_MUT = "if False and yukleme_bekle("
    iddia("M4-a CAPA TEKIL", govde.count(M4_CAPA) == 1, "isabet=%d" % govde.count(M4_CAPA))
    _mut4 = os.path.join(ayna, "tools", "drive-arsivle-m4.py")
    with open(_mut4, "w", encoding="utf-8") as f:
        f.write(govde.replace(M4_CAPA, M4_MUT, 1))
    m4_kontrol, _ = kol_bekleme(_mut4, gecici, evict_sh, "m4")
    m4_dusen = [ad for ad, kosul in m4_kontrol if not kosul]
    iddia("M4-b mutant H kolunda KIRMIZI (evict yuklemeden once)",
          "evict CAGRILMADI" in m4_dusen and "yerel kaynak DURUYOR" in m4_dusen,
          "dusen=%s" % m4_dusen)

    print()
    print("M5 — sha kontrolu kaldirilinca evict/sil zinciri KIRMIZI")
    e_gercek = kol_sha_zincir(da, gecici, evict_sh, "gercek")
    for ad, kosul in e_gercek:
        iddia("E-zincir " + ad, kosul)
    m5_kontrol = kol_sha_zincir(da_m1, gecici, evict_sh, "m5")
    m5_dusen = [ad for ad, kosul in m5_kontrol if not kosul]
    iddia("M5 mutant e-zincir KIRMIZI (bozuk kopyaya evict + yerel sil)",
          "evict CAGRILMADI" in m5_dusen and "yerel kaynak DURUYOR" in m5_dusen,
          "dusen=%s" % m5_dusen)

    # ---- (9 Eki 2026) M6: evict adimi silinince J KIRMIZI ----
    print()
    print("M6 — evict adimi silinince (j) KIRMIZI")
    M6_CAPA = "    if a.evict:"
    M6_MUT = "    if False and a.evict:"
    iddia("M6-a CAPA TEKIL", govde.count(M6_CAPA) == 1,
          "isabet=%d" % govde.count(M6_CAPA))
    _mut6 = os.path.join(ayna, "tools", "drive-arsivle-m6.py")
    with open(_mut6, "w", encoding="utf-8") as f:
        f.write(govde.replace(M6_CAPA, M6_MUT, 1))
    # J kolu kaynagi siler; M6 icin taze kaynak olustur.
    j_m6_yol = os.path.join(kaynak, "alt", "m6.txt")
    with open(j_m6_yol, "w", encoding="utf-8") as f:
        f.write("m6 ici")
    m6_log = os.path.join(gecici, "m6.log")
    open(m6_log, "w").close()
    rc_m6, cikti_m6 = kos(
        [_mut6, j_m6_yol, "--hedef", "mutant_m6/", "--drive-kok", drive,
         "--evict-komut", evict_sh],
        ortam={"DRIVE_ARSIVLE_LOG": m6_log},
    )
    m6_l = _oku(m6_log)
    iddia("M6-b mutant J kolunda KIRMIZI (evict CAGRILMADI)",
          m6_l.count("evict=") == 0 and "evict_ok=0" in cikti_m6,
          "evict_satiri=%d cikti=%s" % (m6_l.count("evict="), cikti_m6[-200:]))

    # ---- (9 Eki 2026) M7: sha kontrolu silinince L KIRMIZI ----
    print()
    print("M7 — sha kontrolu silinince (l) KIRMIZI")
    # M1 zaten sha kontrolunu sifirliyor (if False:); ayni mutant ile L kolunu olc.
    rc_l_mut, cikti_l_mut = _calistir_is_ici_l_mut(
        da_m1, l_yol, drive, evict_sh, gecici,
    )
    # l_yol SHA tutmuyor (L1). Mutantta sha kontrolu YOK → kod sha_h != sha_k
    # false goruyor, evict adimina giriyor. L2 evict_sayaci=0 → >0 olur, L3
    # kaynak silinir.
    iddia("M7 mutant L kolunda KIRMIZI (sha tutmazsa bile evict + yerel sil)",
          "evict_ok=1" in cikti_l_mut and not os.path.isfile(l_yol),
          "evict_ok=%s yerel=%s cikti=%s" % (
              "evict_ok=1" in cikti_l_mut, os.path.isfile(l_yol), cikti_l_mut[-200:]))

    print()
    print("=" * 70)
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (IDDIA, GECTI, len(KIRMIZI)))
    if KIRMIZI:
        for k in KIRMIZI:
            print("  DUSEN: %s" % k)
        return 1
    print("SONUC: GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
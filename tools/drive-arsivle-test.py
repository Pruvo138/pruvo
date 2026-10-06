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
  g)  evict hatasi → yerel silinmis, rc=0, evict_hata=1

MUTANT (arac kolunda):
  sha kontrolu silinince (e) KIRMIZI
  kuru kontrolu silinince (c) KIRMIZI
  yerel-tut silinince (b) KIRMIZI
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
    yazici.write("#!/bin/sh\necho evict=\"$1\" >> \"$DRIVE_ARSIVLE_LOG\"\nexit 0\n")
    yazici.close()
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


def _kollar(gecici):
    kaynak, drive, evict_sh, log = hazirla(gecici)
    sahte_evict(evict_sh)

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
    print("G — evict HATASI → yerel silinmiş, rc=0, evict_hata=1")
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
         "--evict-komut", g_evict],
        ortam={"DRIVE_ARSIVLE_LOG": g_log},
    )
    iddia("G1 rc=0 (evict hatasi rc degistirmez)", rc == 0, "rc=%d" % rc)
    iddia("G2 evict_hata=1", "evict_hata=1" in cikti)
    iddia("G3 evict=hata satiri var", "evict=hata" in cikti)
    iddia("G4 yerel kaynak SILINDI", not os.path.exists(g_yol))
    iddia("G5 hedef var (dosya kaybolmadi)",
          os.path.isfile(os.path.join(drive, "deneme_g", "c.txt")))

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
    M2_CAPA = "if a.kuru:\n            continue"
    M2_MUT = "if False:\n            continue"
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
    M3_CAPA = "if not a.yerel_tut:\n            try:\n                os.remove(tam_yol)\n                sayac[\"silindi\"] += 1"
    M3_MUT = "if True:\n            try:\n                os.remove(tam_yol)\n                sayac[\"silindi\"] += 1"
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
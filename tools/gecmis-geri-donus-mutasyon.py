#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gecmis-geri-donus-mutasyon.py — GERI-DONUS KAPISININ CURUTME ARACI.

NE OLCER: "kabul testi YESIL" demek "kapi CANLI" demek DEGILDIR. Bu arac kapiyi
BILEREK bozar ve kabul bataryasinin (`--kendini-test`) GERCEKTEN kirmizi yandigini
olcer. ILGISIZ bir degisiklik (yorum/bosluk) ise YESIL kalmalidir — aksi halde
batarya "her seye kirmizi yanan" gurultulu bir alarma donusmus demektir.

🔴 GUVENLIK: mutasyon KOPYAYA uygulanir. Canli dosyalara DOKUNULMAZ; kosum sonunda
   sha256 esitligi ile KANITLANIR (mutant sizarsa arac KIRMIZI yanar).
🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — tools/commit-mesaji-mutasyon.py ile ayni desen.

🔴 KOPYA LISTESI ELLE TUTULMAZ (14 Eki 2026): kapi `git_ortami`'yi KOSULSUZ import
   ediyor ve `bilinen_public_shalar` icin `gecmis-geri-donus-bilinen.json`'i okuyor;
   elle kopya listesi uzamadi -> her mutant kopyasi ImportError ile COKTU. Sonuc:
   K1-K3 "sahte-kirmizi" yandi ve DAHA KOTUSU her oldurucu mutant olcum yuzunden
   degil COKME yuzunden "OLDU" sayildi (batarya KOR). Onarim: (1) bagimliliklar
   kapi+kurucunun import ve dosya adi dizgelerinden TURETILIR; (2) TABAN — mutasyonsuz
   kopya once SONUC N/N yesil vermeli, yoksa arac hukum KURMAZ (cikis 3 = OLCULEMEDI,
   KIRMIZI'dan ayri); (3) mutant ancak batarya HUKME ULASIP kirmizi derse OLDU sayilir;
   cokme OLDU DEGILDIR. Ilgisiz kontrol de taban ile AYNI iddia sayisina ulasmalidir.
   🔴 14 Eki olculen ariza (mimar, 16:3x): K1/K2/K3 (ilgisiz) "YANLIS ALARM",
   M12 capa bayat (`exit 1` satirini kapisi `pruvo_gd_mesaj` fonksiyonuna refactor
   etmisti) — M12 OLCULEMEDI; o satir da onarildi.

Kullanim: python3 tools/gecmis-geri-donus-mutasyon.py
Cikis 0 = her oldurucu mutant KIRMIZI + her ilgisiz mutant YESIL + canli dosyalar temiz.
Cikis 1 = KIRMIZI (mutant sag kaldi/coktu · ilgisiz kontrol kirmizi · canli dosya degisti).
Cikis 3 = OLCULEMEDI (taban kopyasi hukme ulasamadi; mutant hukmu KURULMADI).
"""
import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "gecmis-geri-donus-kapisi.py")
KUR = os.path.join(TOOLS, "gecmis-geri-donus-hook-kur.py")
KARDES = os.path.join(TOOLS, "commit-mesaji-kapisi.py")
OZET = os.path.join(TOOLS, "sizinti-desen-ozetleri.json")
# 14 Eki: `bilinen_public_shalar` env/PRUVO_GD_BILINEN_DOSYA yoksa bu dosyaya geri
# duşer; kopyada YOKSA muafiyet suser ve VAKA 13b'de TABAN dahil HER kosum kirmizi
# doner. Dosya ismi kapinin govdesinde dizge sabiti olarak duruyor -> turetim onu
# yakalar; yine de acik listeye aldik (ciktinin "kopya kumesi" satirinda gorunur).
BILINEN = os.path.join(TOOLS, "gecmis-geri-donus-bilinen.json")
# Kabul bataryasinin J bolumu katalog markalarini `urunler.json`'dan turetir; K bolumu
# `nobet.yml` adim adlarini okur -> mutant agacinda IKISI DE bulunmalidir, yoksa her
# mutant (ilgisiz kontroller dahil) "olcemedim" yuzunden kirmizi yanar ve arac korlesir.
URUNLER = os.path.join(ROOT, "urunler.json")


# `--kendini-test` ciktisinin SONUC satiri: "53 vaka · 0 hata". Toplam vaka sayisi
# taban ile mutant uzerinde AYNI olmali (ilgisiz kontrolun "tamam" diyebilmesi icin).
SONUC_DESEN = re.compile(r"^(\d+) vaka . (\d+) hata\s*$", re.M)
OK_DESEN = re.compile(r"^\s{2}ok\s+", re.M)
FAIL_DESEN = re.compile(r"^\s{2}FAIL\s+", re.M)


def turetilmis_bagimliliklar(kokler=(KAPI, KUR, KARDES)):
    """Kapi + kurucu + kardes kapinin `tools/` icindeki yerel bagimliliklari (gecisli,
    kokler dahil).

    Iki kaynak: (a) `import X` / `from X import` -> `tools/X.py` varsa; (b) govdedeki
    dizge sabiti `tools/` altinda bir DOSYA adiysa (ornek: `git_ortami.py`,
    `gecmis-geri-donus-bilinen.json`, kendini testin sentetik depoya tasikladi modul,
    desen ozet dosyasi).
    """
    gorulen = set()
    kuyruk = [os.path.abspath(k) for k in kokler]
    while kuyruk:
        yol = kuyruk.pop()
        if yol in gorulen:
            continue
        gorulen.add(yol)
        if not yol.endswith(".py"):
            continue
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read(), filename=yol)
        adaylar = set()
        for d in ast.walk(agac):
            if isinstance(d, ast.Import):
                adaylar.update(a.name.split(".")[0] + ".py" for a in d.names)
            elif isinstance(d, ast.ImportFrom) and d.module and not d.level:
                adaylar.add(d.module.split(".")[0] + ".py")
            elif isinstance(d, ast.Constant) and isinstance(d.value, str):
                if d.value and "/" not in d.value and len(d.value) < 128:
                    adaylar.add(d.value)
        for ad in adaylar:
            hedef = os.path.join(TOOLS, ad)
            if os.path.isfile(hedef) and hedef not in gorulen:
                kuyruk.append(hedef)
    return sorted(gorulen)


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# (ad, hedef_dosya, eski, yeni, oldurucu_mu)
# "oldurucu" = nobetcinin HUKMUNU ya da KABLOSUNU olduren mutasyon -> batarya KIRMIZI.
MUTANTLAR = (
    # --- MENZIL: KAPININ CEKIRDEGI -------------------------------------------
    # 🔴 M1 ARIZANIN TA KENDISIDIR: menzil "yalniz YENI YAZILAN commit'ler"e
    # daraltilirsa, merge ile GERI GELEN eski sizintili commit'ler taranmaz ve
    # temizlik yine sessizce geri doner. Kapinin butun degeri bu satirdadir.
    ("M1  MENZIL 'yalniz yeni yazilanlar'a daraltildi (geri gelen commit gorunmez)",
     "kapi",
     '        if p.returncode == 0:\n            args += ["--not", remote_sha]',
     '        if p.returncode == 0:\n            args += ["--not", "--all"]', True),
    # --- EKSENLER -------------------------------------------------------------
    ("M2  ICERIK EKSENI OLDURULDU (aday kumesi bosaltildi)", "kapi",
     '    olcum["aday"] = len(aday_commit)',
     '    aday_commit = {}\n    olcum["aday"] = len(aday_commit)', True),
    ("M3  MESAJ EKSENI OLDURULDU (kusurlar hukme girmez)", "kapi",
     "        for k in modul.mesaj_kusurlari(modul.mesaj_govdesi(p.stdout), kayit,\n"
     "                                       maskeli=maskeli):",
     "        for k in []:", True),
    # --- FAIL-CLOSED YOLLARI --------------------------------------------------
    ("M4  ADAY BUTCESI fail-OPEN yapildi (buyuk itme sessizce taranmaz)", "kapi",
     "        if len(aday_commit) + yeni_sayi > butce:", "        if False:", True),
    ("M5  OZET ARTEFAKTI yoklugu fail-OPEN yapildi", "kapi",
     "    kayit, hata = modul.ozet_kaydi_yukle(ozet_yolu)\n    return kayit, hata",
     "    kayit, hata = modul.ozet_kaydi_yukle(ozet_yolu)\n"
     '    return kayit or {"dongu": 5000, "tuz": b"x", "desenler": []}, None', True),
    ("M6  BOZUK pre-push satiri SESSIZCE atlanir", "kapi",
     '        if len(parca) != 4:\n'
     '            hatalar.append("pre-push satiri COZULEMEDI (4 alan bekleniyor): %r"\n'
     "                           % satir[:120])\n            continue",
     "        if len(parca) != 4:\n            continue", True),
    # --- KIRPMA KOLU (gorunurluk kollarinin butce davranisi) ---
    # 🔴 M15: kirpma "sessiz" hale getirilirse (atlanan sayisi raporlanmazsa) kol
    # DAR kapsamda YESIL yanar ve kimse fark etmez — bu deponun tekrar tekrar
    # olctugu sessiz delik sinifi. 6d bunu yakalamali.
    ("M15 KIRPMA SESSIZLESTIRILDI (atlanan commit sayisi raporlanmaz)", "kapi",
     '            olcum["icerik_atlanan"] = len(shalar) - sira\n            break',
     "            break", True),
    # 🔴 M16: kirpma MESAJ eksenini de kirparsa, force-push sonrasi CI'da mesaj
    # sizintisi gorunmez olur. Mesaj ekseni ucuzdur ve HER ZAMAN tam kapsamalidir.
    ("M16 KIRPMA MESAJ EKSENINI de kirpti (ucuz eksen gereksiz yere daraldi)",
     "kapi",
     "    # --- MESAJ EKSENI ---\n    for sha in shalar:",
     "    # --- MESAJ EKSENI ---\n    for sha in (shalar[:1] if kirp else shalar):",
     True),
    # 🔴 M17: ONLEYICI kol (pre-push) kirpma moduna alinirsa butce asildiginda
    # push DURMAZ ve sizinti gecebilir. Kirpma YALNIZ gorunurluk kollarinda mesru.
    ("M17 PRE-PUSH kolu KIRPMA moduna alindi (onleyici kol fail-open olur)", "kapi",
     "    bulgular, olcum, hata = commitleri_tara(tum_shalar, kayit, modul, kok=kok,\n"
     "                                            maskeli=False, butce=butce)",
     "    bulgular, olcum, hata = commitleri_tara(tum_shalar, kayit, modul, kok=kok,\n"
     "                                            maskeli=False, butce=butce,\n"
     "                                            kirp=True)", True),
    # --- DIFF KAPSAMI ---------------------------------------------------------
    ("M7  MERGE birlesik diff'i KAPATILDI (evil merge kacar)", "kapi",
     '    if n > 1:\n        args.append("-c")',
     '    if False:\n        args.append("-c")', True),
    ("M8  YENIDEN ADLANDIRMA TESPITI ACILDI (rename sizintiyi gizler)", "kapi",
     '"--no-color", "--no-renames",', '"--no-color", "-M",', True),
    ("M9  --root KALDIRILDI (kok commit'in icerigi HIC taranmaz)", "kapi",
     '"--no-renames",\n            "--root"]', '"--no-renames"]', True),
    # --- KANCA KABLOSU --------------------------------------------------------
    ("M10 KANCA CAGRI SATIRI SILINDI (blok var, olcum yok)", "kur",
     'python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push '
     '< "$pruvo_gd_girdi"\npruvo_gd_rc=$?',
     "pruvo_gd_rc=0", True),
    ("M11 KANCA cagrisi YORUMA/echo'ya cevrildi "
     "(nobetci-cagri-satiri-nobetsiz sinifi)", "kur",
     'python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push '
     '< "$pruvo_gd_girdi"',
     'echo python3 "$pruvo_gd_kok/tools/gecmis-geri-donus-kapisi.py" --pre-push '
     '< "$pruvo_gd_girdi"', True),
    # 🔴 M12: capa 14 Eki'de bayatti (kapida inline echo vardi); refactor sonrasi
    # `pruvo_gd_mesaj` fonksiyonu cagiriliyor ve `exit 1` ondan SONRA geliyor.
    # Yeniden capa'lanan satir (yukarida, satir 95) kancanin fail-OPEN davranisini
    # bozar: rc ne olursa olsun `exit 0` donerse `--no-verify` zorunlu olur ve
    # pre-push kapsaminda sizintili merge sessizce gecmis olur.
    ("M12 KANCA `exit 1` -> `exit 0` (fail-open)", "kur",
     '  pruvo_gd_mesaj "$pruvo_gd_rc"\n  exit 1\nfi',
     '  pruvo_gd_mesaj "$pruvo_gd_rc"\n  exit 0\nfi', True),
    ("M13 KANCA fail-closed on-kosulu fail-OPEN yapildi (betik yoksa gec)", "kur",
     '  echo "!! Sizinti kapisi fail-closed\'dir. Kasten atlamak icin: '
     'git push --no-verify"\n  exit 1\nfi',
     "  exit 0\nfi", True),
    # 🔴 M14 SESSIZ REGRESYON: stdin geri verilmezse kapi CALISIR ve YESIL yanar,
    # ama ayni kancadaki D1 SENKRONU bos girdi gorup HIC KOSMAZ -> site urunu
    # gosterir, EGE GOREMEZ. Kapinin kendi hukmunu HIC bozmayan bu mutant yalnizca
    # 11b iddiasiyla yakalanir; iddia silinirse burada gorunur.
    ("M14 STDIN kalan kancaya GERI VERILMIYOR (D1 senkronu sessizce olur)", "kur",
     'exec < "$pruvo_gd_girdi"\nrm -f "$pruvo_gd_girdi"',
     'rm -f "$pruvo_gd_girdi"', True),
    # --- ILGISIZ (kontrol): batarya YESIL kalmali -----------------------------
    ("K1  ilgisiz: baslik yorumunda kelime degisti", "kapi",
     "IKI KOL\n", "IKI  KOL\n", False),
    ("K2  ilgisiz: fonksiyon arasina bos satir eklendi", "kapi",
     "\ndef push_satirlari(metin):", "\n\ndef push_satirlari(metin):", False),
    ("K3  ilgisiz: kurulum betigine yorum satiri eklendi", "kur",
     "def kurulu_mu(yol):", "# ilgisiz yorum\ndef kurulu_mu(yol):", False),
    # --- BILINEN PUBLIC MUAFIYETI (Okan 14 Eki) -----------------------------
    # 🔴 M18: muafiyet filtresi DEVRE DISI kalirsa bilinen listedeki SHA'lar da
    # taranir -> VAKA 13a'da "temiz" beklenirken sizintili SHA rapor edilir ve
    # "13a" iddiasi KIRMIZI yanar. Mevcut muafiyet toptan kalkar; bu da asil
    # hedef: bilinmeyen adli commit'leri de muaf gostermek (fail-open).
    ("M18 BILINEN PUBLIC MUAFIYETI DEVRE DISI (filtre filtrelemez)",
     "kapi",
     '    bilinen = bilinen_public_shalar(bilinen_yolu)\n'
     '    girdi_uzunluk = len(shalar)\n'
     '    # 🔴 BILINEN PUBLIC MUAF: SHA esitlik kumesinden CIKARILIR (Okan 14 Eki). SHA\n'
     '    # disinda hicbir alana bakilmaz; ad/desen/aciklama bilinen dosyada olsa bile\n'
     '    # bu fonksiyon onlara ERISEMIYOR.\n'
     '    shalar = [s for s in shalar if s not in bilinen]\n'
     '    muaf_bilinen_public = girdi_uzunluk - len(shalar)',
     '    bilinen = bilinen_public_shalar(bilinen_yolu)\n'
     '    girdi_uzunluk = len(shalar)\n'
     '    # 🔴 BILINEN PUBLIC MUAF: SHA esitlik kumesinden CIKARILIR (Okan 14 Eki). SHA\n'
     '    # disinda hicbir alana bakilmaz; ad/desen/aciklama bilinen dosyada olsa bile\n'
     '    # bu fonksiyon onlara ERISEMIYOR.\n'
     '    shalar = list(shalar)\n'
     '    muaf_bilinen_public = 0',
     True),
    # 🔴 M19 (BaBa 14 Eki 16:0x, ASIL YON): muafiyet ASIRI genislerse — listede OLMAYAN
    # yeni adli commit de muaf sayilirsa — VAKA 13b ("listede olmayan ENGELLENDI")
    # KIRMIZI yanmali. M18 muafiyetin CALISTIGINI olcer; M19 SINIRINI olcer.
    ("M19 BILINEN PUBLIC MUAFIYETI ASIRI GENIS (listede olmayan da muaf)",
     "kapi",
     '    shalar = [s for s in shalar if s not in bilinen]\n',
     '    shalar = []\n',
     True),
)


def _kos(mutasyon, kopyalar):
    """Bir kopya agacinda kendini testi kosar. mutasyon=None -> TABAN (degismemis).

    Donus: (rc|None, tani, yesil, toplam). rc=None -> mutasyon UYGULANAMADI.
    yesil/toplam None -> batarya SONUC satirina ULASAMADI (cokme/zaman asimi).
    """
    tmp = tempfile.mkdtemp(prefix="pruvo-gd-mut-")
    try:
        t_tools = os.path.join(tmp, "tools")
        os.makedirs(t_tools)
        for kaynak in kopyalar:
            shutil.copy2(kaynak, os.path.join(t_tools, os.path.basename(kaynak)))
        # urunler.json 14,4 MB'dir ve HICBIR mutant onu degistirmez -> kopya yerine
        # sembolik bag (her mutantta ~14 MB gereksiz I/O'dan kacinilir).
        os.symlink(URUNLER, os.path.join(tmp, "urunler.json"))
        if mutasyon is not None:
            hedef, eski, yeni = mutasyon
            yol = {"kapi": os.path.join(t_tools, os.path.basename(KAPI)),
                   "kur": os.path.join(t_tools, os.path.basename(KUR))}[hedef]
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            if eski not in metin:
                return (None, "CAPA BULUNAMADI (mutasyon uygulanamadi — arac bayat)",
                        None, None)
            if metin.count(eski) != 1:
                return (None, "capa %d kez gecti (tek olmali)" % metin.count(eski),
                        None, None)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
        try:
            p = subprocess.run(
                [sys.executable, os.path.join(t_tools, os.path.basename(KAPI)),
                 "--kendini-test"], capture_output=True, text=True, timeout=900)
        except subprocess.TimeoutExpired:
            return -1, "ZAMAN ASIMI (900 sn)", None, None
        m = SONUC_DESEN.findall(p.stdout)
        toplam, hata_say = (int(m[-1][0]), int(m[-1][1])) if m else (None, None)
        ok_say = len(OK_DESEN.findall(p.stdout))
        fail_say = len(FAIL_DESEN.findall(p.stdout))
        # yesil sayisini toplamdan FAIL cikarak hesapla (ciktidaki `ok` satirlari
        # BAZI vakalarda eksik basinabilir; SONUC satiri tek guvenilir kaynak).
        yesil = toplam - hata_say if toplam is not None else None
        if fail_say > 0 or (toplam is not None and hata_say > 0):
            kirmizi_satirlar = [s.strip() for s in p.stdout.splitlines()
                                if s.strip().startswith("FAIL")]
            tani = "; ".join(kirmizi_satirlar[:3]) if kirmizi_satirlar else "(kirmizi var)"
        elif toplam is None:
            son = [s for s in (p.stderr or p.stdout).strip().splitlines() if s.strip()]
            tani = "SONUC satiri yok; son satir: %s" % (son[-1][:160] if son else "-")
        else:
            tani = "(kirmizi iddia yok)"
        return p.returncode, tani, yesil, toplam
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    # Turetim: kapinin govdesinde "git_ortami.py" + "gecmis-geri-donus-bilinen.json"
    # dizgeleri + import'u gecişli olarak kapsanir; OZET acik listeye kalir cunku
    # icinde desen listesi tasinir ve `ozet_kaydi_yukle` onu bir SHA esitlik kapisi
    # olarak dogrudan acar.
    kopyalar = sorted(set(turetilmis_bagimliliklar()) | {OZET, BILINEN})
    izlenen = sorted(set(kopyalar) | {URUNLER})
    canli_once = {y: _sha(y) for y in izlenen}
    print("kopya kumesi (kaynaktan TURETILDI): %s"
          % ", ".join(os.path.basename(k) for k in kopyalar))

    # TABAN: mutasyonsuz kopya hukme ulasip YESIL demezse hicbir mutant hukmu
    # anlamli degildir (cokme "OLDU" sayilir, kontrol "sahte-kirmizi" yanar).
    t_rc, t_tani, t_yesil, t_toplam = _kos(None, kopyalar)
    if t_rc != 0 or t_toplam is None or t_yesil != t_toplam:
        print("⚪ OLCULEMEDI: TABAN kopyasi temiz DEGIL (rc=%s, SONUC=%s/%s): %s"
              % (t_rc, t_yesil, t_toplam, t_tani))
        print("   Kopya agacinda eksik bagimlilik/cevre var; mutant hukmu KURULMADI.")
        return 3
    print("TABAN: rc=0 · %d/%d iddia yesil (mutasyonsuz kopya)" % (t_yesil, t_toplam))

    sonuclar = []
    for ad, hedef, eski, yeni, oldurucu in MUTANTLAR:
        rc, tani, yesil, toplam = _kos((hedef, eski, yeni), kopyalar)
        sonuclar.append((ad, oldurucu, rc, tani, yesil, toplam))

    hatalar = []
    print("MUTANT                                                        BEKLENEN  RC  HUKUM")
    print("-" * 100)
    for ad, oldurucu, rc, tani, yesil, toplam in sonuclar:
        beklenen = "KIRMIZI" if oldurucu else "YESIL"
        if rc is None:
            hukum = "OLCULEMEDI"
            hatalar.append("%s -> %s" % (ad, tani))
        elif toplam is None:
            # Batarya SONUC satirina ulasmadi: cokme bir OLCUM degildir (taban
            # temizdi, yani bu mutant kopyayi calisamaz hale getirdi).
            hukum = "COKTU ❌"
            hatalar.append("%s COKTU (hukme ulasilmadi; cokme OLDU sayilmaz): %s"
                           % (ad, tani))
        elif oldurucu:
            hukum = "OLDU ✅" if rc != 0 else "SAG KALDI ❌"
            if rc == 0:
                hatalar.append("%s SAG KALDI (batarya bu mutasyonu GORMUYOR)" % ad)
        else:
            temiz = rc == 0 and yesil == toplam == t_toplam
            hukum = "YESIL ✅" if temiz else "SAHTE-KIRMIZI ❌"
            if not temiz:
                hatalar.append("%s ilgisiz degisiklikte KIRMIZI yandi (SONUC %s/%s, "
                               "taban %d): %s" % (ad, yesil, toplam, t_toplam, tani))
        print("%-60s  %-8s  %-3s %s" % (ad[:60], beklenen,
                                        "-" if rc is None else rc, hukum))
    canli_sonra = {y: _sha(y) for y in izlenen}
    for yol in canli_once:
        if canli_once[yol] != canli_sonra[yol]:
            hatalar.append("🔴 CANLI DOSYA DEGISTI (mutant sizdi): %s" % yol)
    print("-" * 100)
    print("canli dosya sha256 esitligi: %s"
          % ("TAM ✅" if canli_once == canli_sonra else "BOZUK ❌"))
    for yol, ozet in sorted(canli_once.items()):
        print("   %-44s %s" % (os.path.basename(yol), ozet[:16]))
    oldu = sum(1 for _a, o, rc, _t, _y, top in sonuclar
               if o and rc not in (None, 0) and top is not None)
    oldurucu_sayi = sum(1 for s in sonuclar if s[1])
    yesil_k = sum(1 for _a, o, rc, _t, y, top in sonuclar
                  if not o and rc == 0 and y == top == t_toplam)
    kontrol_sayi = sum(1 for s in sonuclar if not s[1])
    print("SONUC: oldurucu mutant %d/%d OLDU · ilgisiz kontrol %d/%d YESIL"
          % (oldu, oldurucu_sayi, yesil_k, kontrol_sayi))
    if hatalar:
        print("\nKIRMIZI:")
        for h in hatalar:
            print("  * " + h)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
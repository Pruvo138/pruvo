#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — alt kategori (grup) CIP SATIRI: gorunur, tiklanir ve LISTEYI FIILEN DARALTIR.

  python3 tools/altkategori-cip-test.py              # kabul (CI'da bloklayici)
  python3 tools/altkategori-cip-test.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/altkategori-cip-test.py --kok /yol   # BASKA agactan oku (mutasyon icin)

NEDEN VAR (olculdu 2 Agu): `altkategori` VERI yolu (tools/altkategori-kapisi.py) ve URUN
SAYFASI yuzeyi (tools/altkategori-yuzey-test.py) YESILDI; D1'de 16.646 kayit dolu, 60 tekil
ikili, Worker /katalog + /ara degeri hem DONDURUYOR hem TAM ESITLIKLE SUZUYOR. Buna ragmen
ANA SAYFA'da daraltma yuzeyi YOKTU: index.html `altkategori` URL parametresini HIC okumuyor,
cip satiri cizmiyordu. Musteri 60 grubu yalnizca urun sayfasinda ETIKET olarak goruyor,
tiklayip daraltamiyordu.

OLCULEN SESSIZ-HATA SINIFI (bu kapinin varlik sebebi): "cip GORUNUR, TIKLANIR, liste
DEGISMEZ ve hicbir alarm calmaz". DOM'da cip aramak bu sinifi GORMEZ — bu yuzden her
iddianin KONTROL EKSENI vardir: sayi DEGISMELI, uydurma deger 0 DONMELI, donen kayitlarin
DEGERI secilene esit OLMALI.

MIMARI: hukum burada, ICRA tools/altkategori-cip-kosum.js'te (index.html'in GERCEK inline
scripti node:vm'de calisir; kod kopyalanmaz). Kosum dosyasi bilerek "-test.js" ADINDA
DEGIL: ci-kapsam kesfi ikinci bir CI girisi beklemesin, CI girisi TEK ve bu dosya olsun.

IKI MOD DA OLCULUR: edge (EDGE_KATALOG=true, CANLI hal — parametre Worker'a gider) ve
yerel (bayrak false, geri donus yolu — filtre istemcide kosar). Tek modda olculseydi
oteki yol sessizce fail-open kalirdi.

AGA CIKMAZ, DISKE YAZMAZ: fetch sahtedir, index.html yalnizca OKUNUR.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)
KOSUM = os.path.join(DIR, "altkategori-cip-kosum.js")

# 🔴 IDDIA SAYISI SOZLESMESI (olcut ESIT, ">=" DEGIL): kosum dosyasindan bir iddia
# SESSIZCE dusurulurse ya da bir mod hic kosmazsa kapi KIRMIZI yanar. Sayi degisecekse
# BILEREK degistirilir (yeni iddia eklenince burasi da guncellenir).
BEKLENEN_IDDIA = 34


def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kabul(kok):
    kaldi = []

    def dogrula(ad, kosul, detay=""):
        if kosul:
            print("  GECTI %s%s" % (ad, (" — " + detay) if detay else ""))
        else:
            kaldi.append(ad)
            print("  KALDI %s%s" % (ad, (" — " + detay) if detay else ""))

    arama = _modul(os.path.join(kok, "tools", "arama.py"), "arama_cip")
    izinli = {k: list(v) for k, v in arama.ALTKATEGORI_IZINLI.items()}
    toplam_deger = sum(len(v) for v in izinli.values())
    print("  IZINLI KUME: %d kategori / %d deger (tek kaynak: arama.ALTKATEGORI_IZINLI)"
          % (len(izinli), toplam_deger))

    # --- A) URETILEN BLOK TAZE MI (metin ekseni) -----------------------------
    # Kosum dosyasi CALISMA ZAMANI degerini olcer; bu iddia BLOK ISARETCILERININ
    # ve uretecin yerinde oldugunu olcer (uretec silinir/isaretci kayarsa yakalanir).
    veri = _modul(os.path.join(kok, "tools", "altkategori-veri.py"), "altveri_cip")
    with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
        index_metin = f.read()
    mevcut = veri.blok_oku(index_metin)
    beklenen = veri.blok_uret(izinli)
    dogrula("A URETILEN BLOK TAZE (index.html <-> arama.ALTKATEGORI_IZINLI)",
            mevcut is not None and mevcut == beklenen,
            "blok YOK" if mevcut is None else ("ayrisma" if mevcut != beklenen else "birebir"))

    # --- B..) DAVRANIS KOSUMU (node) -----------------------------------------
    fd, izinli_yol = tempfile.mkstemp(prefix="pruvo-altkat-izinli-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(izinli, f, ensure_ascii=False)
    try:
        p = subprocess.run(["node", KOSUM, "--kok", kok, "--izinli", izinli_yol],
                           capture_output=True, text=True)
    finally:
        os.unlink(izinli_yol)

    if p.returncode != 0 or not p.stdout.strip():
        # FAIL-CLOSED: kosum kosmadiysa YESIL SAYILMAZ.
        print("  KALDI KOSUM CALISTIRILAMADI — rc=%d" % p.returncode)
        print("     " + ((p.stderr or "").strip().splitlines() or [""])[-1][:400])
        kaldi.append("KOSUM CALISTIRILAMADI")
        return 1

    try:
        sonuc = json.loads(p.stdout)
    except ValueError as e:
        print("  KALDI KOSUM CIKTISI COZULEMEDI — %s" % e)
        return 1

    iddialar = sonuc.get("iddialar", [])
    for it in iddialar:
        dogrula(it["ad"], it["gecti"], it.get("detay", ""))

    # 🔴 KAPSAM NOBETCISI (olcut ESIT): iddia sayisi sozlesmeyle BIREBIR esit olmali.
    dogrula("Z IDDIA SAYISI SOZLESMESI (== %d)" % BEKLENEN_IDDIA,
            len(iddialar) == BEKLENEN_IDDIA, "kosan=%d" % len(iddialar))

    toplam = len(iddialar) + 2
    if kaldi:
        print("\nSONUC: %d/%d iddia KALDI" % (len(kaldi), toplam))
        return 1
    print("\nSONUC: %d/%d iddia GECTI ✔" % (toplam, toplam))
    return 0


# ---------------------------------------------------------------- MUTASYON
# (dosya, eski, yeni, beklenen, aciklama)
MUTANTLAR = [
    ("index.html",
     'var altOk = activeAlt === "Tümü" || (p.altkategori || "") === activeAlt;',
     'var altOk = true;', "KIRMIZI",
     "FILTREYI KALDIR (yerel): cip tiklanir, liste DEGISMEZ — bu paketin ana sessiz hatasi"),
    ("index.html",
     'if(activeAlt !== "Tümü"){ p.set("altkategori", activeAlt); }',
     'if(false){ p.set("altkategori", activeAlt); }', "KIRMIZI",
     "EDGE PARAMETRESINI DUSUR: Worker suzmez, canlida liste daralmaz"),
    ("index.html", 'if(alt){ activeAlt = alt; }', 'if(false){ activeAlt = alt; }', "KIRMIZI",
     "URL OKUMASINI KALDIR: paylasilan link/urun sayfasi donusu secimi tasimaz"),
    ("index.html",
     'var altVar = activeCat !== "Tümü" &&\n                   (altListesi(activeCat).length > 0 || activeAlt !== "Tümü");',
     'var altVar = activeCat !== "Tümü";', "KIRMIZI",
     "CIP SATIRINI HER KATEGORIDE GOSTER: alt kategorisi olmayanda BOS KUTU"),
    ("index.html",
     'var anaGorunum = activeCat === "Tümü" && query.trim() === "" &&\n                     activeBrand === "Tümü" && activeAlt === "Tümü";',
     'var anaGorunum = activeCat === "Tümü" && query.trim() === "" && activeBrand === "Tümü";',
     "KIRMIZI",
     "ANA GORUNUM SARTINDAN activeAlt'i DUSUR: ?altkategori=X tam katalogu gosterir (fail-open)"),
    ("index.html",
     'if(activeAlt !== "Tümü"){ params.set("altkategori", activeAlt); }',
     'if(false){ params.set("altkategori", activeAlt); }', "KIRMIZI",
     "URL YAZMAYI KALDIR: secim paylasilamaz, round-trip kirilir"),
    ("index.html",
     'activeAlt = (deger === activeAlt) ? "Tümü" : deger;   // tekrar tık = temizle',
     'activeAlt = deger;', "KIRMIZI",
     "TEMIZLEME YOLUNU KALDIR: secili gruptan cikilamaz"),
    ("index.html",
     'if(activeAlt !== "Tümü" && altListesi(activeCat).indexOf(activeAlt) === -1){\n          activeAlt = "Tümü";\n        }',
     'if(false){ activeAlt = "Tümü"; }', "KIRMIZI",
     "KATEGORI DEGISINCE GRUBU DUSURME: yeni kategoride tanimsiz grup TAKILI kalir -> 0 urun"),
    ("index.html",
     'activeCat = "Tümü"; activeBrand = "Tümü"; activeAlt = "Tümü";',
     'activeCat = "Tümü"; activeBrand = "Tümü";', "KIRMIZI",
     "POPSTATE SIFIRLAMASINDAN activeAlt'i DUSUR: geri tusundan sonra URL ile gorunum ayrisir"),
    ("arama.py", '        "Filtreler",\n', '        "Filtrelerr",\n', "KIRMIZI",
     "IKIZ AYRISMASI: izinli kume degisir, uretilen blok BAYAT kalir"),
    # --- KONTROL MUTANTLARI (YESIL bekleniyor) — iddialar ILGISIZ degisikliklere
    # PINLENMIS mi? Yesil kalmazlarsa kapi asiri-baglanmistir ([[kapi-kapsam-eksen-secimi]]).
    ("index.html", '.brand-btn:hover{border-color:var(--navy-2)}',
     '.brand-btn:hover{border-color:var(--gray-line)}', "YESIL",
     "ILGISIZ: cip hover rengi — davranisa DOKUNMAZ"),
    ("index.html", 'var PAGE_SIZE = 24;', 'var PAGE_SIZE = 12;', "YESIL",
     "ILGISIZ: sayfa boyu — iddialar sayfalama sabitine PINLENMEMELI"),
    ("arama.py", 'ALTKATEGORI_AZAMI_KELIME = 4', 'ALTKATEGORI_AZAMI_KELIME = 5', "YESIL",
     "ILGISIZ: imza nobetinin kelime tavani — cip yuzeyine DOKUNMAZ"),
]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _hedef(tmp, dosya):
    return os.path.join(tmp, "tools", dosya) if dosya.endswith(".py") \
        else os.path.join(tmp, dosya)


def _kopya_kur():
    """index.html + tools/ KOPYALANIR (mutant oraya yazilir), kalani SYMLINK."""
    tmp = tempfile.mkdtemp(prefix="pruvo-altkat-cip-mut-")
    shutil.copytree(os.path.join(GERCEK_KOK, "tools"), os.path.join(tmp, "tools"))
    shutil.copy2(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", "index.html", ".git", ".claude"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))
    return tmp


def _kok_kostur(tmp):
    return subprocess.run([sys.executable, os.path.abspath(__file__), "--kok", tmp],
                          capture_output=True, text=True)


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    izlenen = [os.path.join(GERCEK_KOK, "index.html"),
               os.path.join(GERCEK_KOK, "tools", "arama.py"),
               os.path.join(GERCEK_KOK, "tools", "altkategori-cip-kosum.js")]
    once = {y: _sha(y) for y in izlenen}
    basarisiz = []

    # M00 MUTASYONSUZ KONTROL — harness saglam mi (yoksa tum KIRMIZI'lar YALANCI).
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s"
          % ("OK  " if p0.returncode == 0 else "HATA",
             "YESIL" if p0.returncode == 0 else "KIRMIZI"))
    if p0.returncode != 0:
        for s in (p0.stdout or "").splitlines():
            if s.strip().startswith("KALDI"):
                print("     " + s.strip()[:200])
        print("     " + ((p0.stderr or "").strip().splitlines() or [""])[-1][:300])
        shutil.rmtree(tmp0, ignore_errors=True)
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk.")
        return 1
    shutil.rmtree(tmp0, ignore_errors=True)

    uygulanan = 0
    for i, (dosya, eski, yeni, beklenen, aciklama) in enumerate(MUTANTLAR, 1):
        tmp = _kopya_kur()
        hedef = _hedef(tmp, dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        sayi = metin.count(eski)
        # 🔴 CAPA KAYMASI = KIRMIZI, "gecti" DEGIL: eslesmeyen capa o ekseni OLCMEMISTIR.
        if sayi != 1:
            basarisiz.append("M%02d CAPA BAYAT (%d eslesme) %s" % (i, sayi, dosya))
            print("  HATA M%02d [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI | %s"
                  % (i, beklenen, dosya, sayi, aciklama))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(metin.replace(eski, yeni, 1))
        uygulanan += 1
        p = _kok_kostur(tmp)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        if goruldu != beklenen:
            basarisiz.append("M%02d %s: beklenen %s, goruldu %s" % (i, dosya, beklenen, goruldu))
        # 🔴 KIRMIZI YETMEZ, ADLI IDDIA SART: mutant COKEREK de rc!=0 verebilir.
        if goruldu == "KIRMIZI" and beklenen == "KIRMIZI" and not oldu:
            basarisiz.append("M%02d %s: KIRMIZI ama HICBIR iddia KALDI demedi (cokme)" % (i, dosya))
        print("  %s M%02d [%s] %s -> %s (%d iddia kirmizi) | %s"
              % ("OK  " if goruldu == beklenen else "HATA", i, beklenen, dosya, goruldu,
                 len(oldu), aciklama))
        for s in oldu[:3]:
            print("        " + s[:160])
        shutil.rmtree(tmp, ignore_errors=True)

    sonra = {y: _sha(y) for y in izlenen}
    bozuk = [os.path.basename(y) for y in once if once[y] != sonra[y]]
    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(once), "DEGISMEDI ✔" if not bozuk else "DEGISTI ✘ %s" % bozuk))
    if bozuk:
        basarisiz.append("CANLI DOSYA DEGISTI: %s" % bozuk)
    print("  MUTANT FIILEN UYGULANDI: %d/%d" % (uygulanan, len(MUTANTLAR)))
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz), len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK, help="agac (mutasyon kopyasi icin)")
    ap.add_argument("--mutasyon", action="store_true", help="cift yonlu mutasyon (elle)")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== ALT KATEGORI CIP SATIRI KAPISI (kok: %s)" % a.kok)
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())

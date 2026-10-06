#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DRIVE-ARSIVLE — PRUVO evlerinde SILINMEK ISTENMEYEN dosyaları Drive'a gönderir.

KULLANAN KIM
├── KraL: STL önizleme · hasrap · render artiklari
├── TeKiN: parametrik STL/3MF ön-üretim
├── MaCiT: hasat ara çıktıları (render, gsel)
└── (vitrin) Mehmet: vitrin ürün DıŞı ham dosyaları

NE ZAMAN KULLANILIR
├── Ürün Dışı + büyük + tekrar-üretilebilir DEĞİL → bu araç
├── Ürün STL/3MF/görsel (vitrin) → R2 (tools/stl-r2-yukle.py)
├── transkript / chrome önbelleği → kural kapsamı dışı (silinir, arşivlenmez)
└── Drive'a yazıp yerel kopya şişmesini istemiyorsan → EVICT adımı otomatik

YAPAR (her dosya için):
  kaynak SHA-256  = sha256(kaynak)
  hedef yolu      = <drive-kök>/<--hedef>/<göreli-yol>
  aynı ad + aynı içerik → KOPYALAMA ATLA (sha karşılaştırma)
  aynı ad + FARKLI içerik → hedefe '__<sha256[:8]>' SON EKİ EKLE
  hedef sha256 != kaynak sha256 → satır 'sha-esit-degil', KAYNAK SİLİNMEZ, rc=1
  sha eşit + --yerel-tut yoksa → KAYNAK SİL
  sha eşit + evict çağrısı → Foundation `evictUbiquitousItem`
  evict hatası → satıra 'evict=hata', dosya kaybolmaz, rc DEĞİŞMEZ
  --kuru → hiçbir şey yapma, ne yapacağını bas

CIKTI:
  DRIVE_ARSIVLE dosya=<n> kopyalandi=<n> atlandi_ayni=<n> silindi=<n>
              evict_ok=<n> evict_hata=<n> hata=<n> bayt=<b> kuru=<0|1>

ORNEKLER:
  python3 tools/drive-arsivle.py /Users/aha/arac/STL --hedef STL-arsiv/stl-yerel-6eki/
  python3 tools/drive-arsivle.py /tmp/dosya.zip --hedef tek-dosyalar /kokum --kuru
  python3 tools/drive-arsivle.py /tmp/dosya.zip --hedef tek-dosyalar --yerel-tut
"""
import argparse
import hashlib
import os
import shlex
import shutil
import subprocess
import sys

VARSAYILAN_DRIVE_KOK = (
    "/Users/okan/Library/CloudStorage/"
    "GoogleDrive-info@pruvo3d.com/Ortak Drive'lar/PRUVO/Pruvo/arsiv"
)
# Evict Foundation `FileManager.default.evictUbiquitousItem(at:)`. `swift -e` ile
# tek satır; hata rc=0 döner ve stderr'e yazar — yutulmaz, dosya kaybolmaz.
VARSAYILAN_EVICT_KOMUT = (
    "swift -e "
    "'import Foundation;"
    "let p = URL(fileURLWithPath: CommandLine.arguments[1]);"
    "try FileManager.default.evictUbiquitousItem(at: p);"
    "print(\"ok\")'"
)
EVICT_ENV = "DRIVE_ARSIVLE_EVICT"


def sha256_dosya(yol):
    """Bir dosyanın sha256 özetini hesaplar."""
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(parc)
    return h.hexdigest()


def kaynaklari_topla(kaynak_yol):
    """[(mutlak_yol, goreeli_yol)] — düz dosya tek eleman; dizin dolaşılır.

    Tek dosya → göreli yol = dosya adı (basename). Böylece `--hedef deneme/`
    ile hedef `deneme/<ad>` olur; aksi halde `deneme/` (dizin) kalır.
    """
    if os.path.isfile(kaynak_yol):
        return [(kaynak_yol, os.path.basename(kaynak_yol))]
    if os.path.isdir(kaynak_yol):
        out = []
        for kok, _, dosyalar in os.walk(kaynak_yol):
            for ad in dosyalar:
                tam = os.path.join(kok, ad)
                gore = os.path.relpath(tam, start=kaynak_yol)
                out.append((tam, gore))
        return out
    return []


def hedef_yolu_coz(drive_kok, hedef_alt, goreeli, sha_kaynak):
    """(hedef_yol, atla) — hedef yolunu çöz.

    Davranış sırası (4 vaka):
      1) muhtemel (uzantısız) VAR ve aynı içerikte → döndür, atla=True
      2) suffixed (önceki çakışma) VAR ve aynı içerikte → döndür, atla=True
      3) muhtemel VAR ve FARKLI içerikte → suffix'li döndür, atla=False
      4) muhtemel yok → muhtemel'i döndür, atla=False

    Çağıran: atla=True ise kopyalama/silme ATLANIR; evict yine de çağrılır
    (yerel önbellek şişmesini engellemek için).
    """
    muhtemel = os.path.join(drive_kok, hedef_alt, goreeli)
    ad, uzanti = os.path.splitext(muhtemel)
    suffixed = ad + "__" + sha_kaynak[:8] + uzanti

    if os.path.exists(suffixed) and sha256_dosya(suffixed) == sha_kaynak:
        return suffixed, True
    if os.path.exists(muhtemel) and sha256_dosya(muhtemel) == sha_kaynak:
        return muhtemel, True
    if os.path.exists(muhtemel):
        return suffixed, False
    return muhtemel, False


def evict_cagir(komut, yol, log):
    """Foundation `evictUbiquitousItem(at:)` çağırır; hata loglanır, rc DEĞİŞMEZ.

    `komut` iki biçimden biri olabilir:
      1) '{yol}' placeholder içeren tek satır string (shlex.quote ile güvenli)
      2) komut + ' ' + <argüman> bicimini (aynı şekilde shlex.quote)

    Boşluklu / tırnaklı yol (özel: `Ortak Drive'lar/...`) shlex.quote ile
    KORUNUR — komut string'i shell=True ile calistirildiginda kelimelere
    yanlış bölünmez.
    """
    if "{yol}" in komut:
        k = komut.format(yol=shlex.quote(yol))
    else:
        k = komut + " " + shlex.quote(yol)
    try:
        proc = subprocess.run(
            k, shell=True, capture_output=True, text=True, timeout=60
        )
        if proc.returncode == 0:
            log.append("evict=ok")
            return True
        log.append("evict=hata rc=%d stderr=%s" % (
            proc.returncode, (proc.stderr or "").strip()[:200]))
        return False
    except subprocess.TimeoutExpired:
        log.append("evict=hata tip=TimeoutExpired")
        return False
    except OSError as e:
        log.append("evict=hata tip=%s" % type(e).__name__)
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="DRIVE-ARSIVLE: yaz -> sha256 -> yerel sil -> evict"
    )
    ap.add_argument("kaynak", help="dosya veya dizin")
    ap.add_argument("--hedef", required=True,
                    help="Drive kökü ALTINDAKI alt yol (örn: STL-arsiv/stl-yerel-6eki/)")
    ap.add_argument("--drive-kok", default=VARSAYILAN_DRIVE_KOK,
                    help="varsayilan: %s" % VARSAYILAN_DRIVE_KOK)
    ap.add_argument("--yerel-tut", action="store_true",
                    help="kaynak kopyalandiktan sonra SILINMESIN")
    ap.add_argument("--kuru", action="store_true",
                    help="hicbir sey yazmaz/silmez; ne yapacagini basar")
    ap.add_argument("--evict-komut", default=os.environ.get(
        EVICT_ENV, VARSAYILAN_EVICT_KOMUT),
        help="evict komutu (test enjekte eder); '{yol}' placeholder'i veya "
                         "komut + argüman bicimi")
    a = ap.parse_args(argv)

    kok = a.drive_kok
    if not os.path.isdir(kok):
        print("HATA=drive-kok-yok kok=%s" % kok, file=sys.stderr)
        return 2
    # Kokun kendisini OLUŞTURMUYORUZ — sadece altındaki hedef klasörünü yazarız.

    if not os.path.exists(a.kaynak):
        print("HATA=kaynak-yok kaynak=%s" % a.kaynak, file=sys.stderr)
        return 2

    liste = kaynaklari_topla(a.kaynak)
    if not liste:
        print("HATA=kaynak-bos kaynak=%s" % a.kaynak, file=sys.stderr)
        return 2

    sayac = {
        "dosya": 0, "kopyalandi": 0, "atlandi_ayni": 0, "silindi": 0,
        "evict_ok": 0, "evict_hata": 0, "hata": 0, "bayt": 0,
    }
    hata_var = False

    print("# drive-arsivle kok=%s hedef=%s kaynak=%s kuru=%d yerel_tut=%d" % (
        kok, a.hedef, a.kaynak, int(bool(a.kuru)), int(bool(a.yerel_tut))))
    print("# dosya_sayisi=%d" % len(liste))

    for tam_yol, gore in liste:
        sayac["dosya"] += 1
        sha_k = sha256_dosya(tam_yol)
        hedef, atla = hedef_yolu_coz(kok, a.hedef, gore, sha_k)
        boyut = os.path.getsize(tam_yol)
        rel = os.path.relpath(hedef, kok)

        # AYNI içerik (muhtemel/suffix aynı içerikte) → ATLA
        if atla:
            sayac["atlandi_ayni"] += 1
            print("dosya=%s sha=%s hedef=%s durum=atlandi_ayni" % (
                gore, sha_k[:8], rel))
            if not a.yerel_tut and not a.kuru:
                try:
                    os.remove(tam_yol)
                    sayac["silindi"] += 1
                except OSError as e:
                    print("dosya=%s durum=silme-hata tip=%s"
                          % (gore, type(e).__name__), file=sys.stderr)
                    sayac["hata"] += 1
                    hata_var = True
                    continue
            log = []
            if not a.kuru:
                if evict_cagir(a.evict_komut, hedef, log):
                    sayac["evict_ok"] += 1
                else:
                    sayac["evict_hata"] += 1
            for l in log:
                print("dosya=%s %s" % (gore, l))
            continue

        # Yeni yazma (adı, ÇAKıŞMADA farklı içerikse kıyara eklenmiş)
        print("dosya=%s sha=%s hedef=%s durum=kopyala bayt=%d" % (
            gore, sha_k[:8], rel, boyut))
        if a.kuru:
            continue

        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        try:
            shutil.copy2(tam_yol, hedef)
        except OSError as e:
            print("dosya=%s durum=kopyala-hata tip=%s"
                  % (gore, type(e).__name__), file=sys.stderr)
            sayac["hata"] += 1
            hata_var = True
            continue

        sha_h = sha256_dosya(hedef)
        if sha_h != sha_k:
            print("dosya=%s HATA=sha-esit-degil kaynak=%s hedef=%s" % (
                gore, sha_k[:8], sha_h[:8]))
            # Kaynak SİLİNMEZ (veri kaybı).
            sayac["hata"] += 1
            hata_var = True
            continue

        sayac["kopyalandi"] += 1
        sayac["bayt"] += boyut

        if not a.yerel_tut:
            try:
                os.remove(tam_yol)
                sayac["silindi"] += 1
            except OSError as e:
                print("dosya=%s durum=silme-hata tip=%s"
                      % (gore, type(e).__name__), file=sys.stderr)
                sayac["hata"] += 1
                hata_var = True
                continue

        log = []
        if evict_cagir(a.evict_komut, hedef, log):
            sayac["evict_ok"] += 1
        else:
            sayac["evict_hata"] += 1
        for l in log:
            print("dosya=%s %s" % (gore, l))

    print("DRIVE_ARSIVLE dosya=%d kopyalandi=%d atlandi_ayni=%d silindi=%d "
          "evict_ok=%d evict_hata=%d hata=%d bayt=%d kuru=%d" % (
              sayac["dosya"], sayac["kopyalandi"], sayac["atlandi_ayni"],
              sayac["silindi"], sayac["evict_ok"], sayac["evict_hata"],
              sayac["hata"], sayac["bayt"], int(bool(a.kuru))))
    return 1 if hata_var else 0


if __name__ == "__main__":
    sys.exit(main())
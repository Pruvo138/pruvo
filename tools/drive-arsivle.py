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

SIRA ZORUNLU (7 Eki 2026 — evict yükleme bitmeden çağrılınca 6/6 `evict_hata`,
  9 Eki — `--evict` bayraksız kosumda ZORUNLU; sha-teyitsiz dosya EVICT EDILMEZ):
  1) kopyala  2) sha256 eşit  3) YÜKLEME BİTTİ Mİ yokla (`drive_birak.yuklendi_mi`,
  --yokla-aralik sn arayla, koşum başına --yukleme-tavan sn; tavan tüm kopyalar
  bittikten SONRA başlar, yüklemeler paralel ilerler)  4) evict (3 deneme)  5) yerel sil
  yükleme tavana kadar bitmezse → satır 'BEKLIYOR', evict YOK, KAYNAK SİLİNMEZ, rc=3
                                   (sonraki koşum aynı içeriği 'atlandi_ayni' ile devralır)
  evict 3 denemede olmazsa      → 'evict=hata', KAYNAK SİLİNMEZ, rc DEĞİŞMEZ
  kaynak == hedef (aynı dosya)  → KAYNAK ASLA SİLİNMEZ
  --evict-yapma                 → evict ATLANIR (upload+sha+yukleme_bekle+yerel_sil
                                   yine calisir); sha-teyitsiz dosya YINE EVICT EDILMEZ
  --kuru → hiçbir şey yazmaz/silmez/evict etmez ve dosya İÇERİĞİ OKUMAZ (Drive'da okuma
           = indirme); hedef varsa yalnız yükleme sinyalini (metadata) OKUR

CIKTI:
  DRIVE_ARSIVLE dosya=<n> kopyalandi=<n> atlandi_ayni=<n> silindi=<n>
              evict_ok=<n> evict_hata=<n> hata=<n> bayt=<b> kuru=<0|1>
              bekliyor=<n> yuklendi_okunan=<n> yuklendi_evet=<n>
RC: 0 tamam · 1 hata (sha/kopya/silme) · 2 argüman/kök · 3 BEKLIYOR (yükleme bitmedi)

ORNEKLER:
  python3 tools/drive-arsivle.py /Users/aha/arac/STL --hedef STL-arsiv/stl-yerel-6eki/
  python3 tools/drive-arsivle.py /tmp/dosya.zip --hedef tek-dosyalar /kokum --kuru
  python3 tools/drive-arsivle.py /tmp/dosya.zip --hedef tek-dosyalar --yerel-tut
"""
import argparse
import os
import shlex
import shutil
import subprocess
import sys

# TEK KAYNAK: evict + sha256 `drive_birak.py`'de yasar; burada ikinci kopya YOK.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drive_birak import (  # noqa: E402
    evict as drive_evict, sha256_dosya, yuklendi_mi as drive_yuklendi_mi, yukleme_bekle)
import time  # noqa: E402

VARSAYILAN_DRIVE_KOK = (
    "/Users/okan/Library/CloudStorage/"
    "GoogleDrive-info@pruvo3d.com/Ortak Drive'lar/PRUVO/Pruvo/arsiv"
)
# Varsayilan evict = `drive_birak.evict`. `--evict-komut` / env YALNIZ test enjeksiyonu
# icindir (sahte shell betigi); verilmezse Foundation cagrisi drive_birak'tan gelir.
EVICT_ENV = "DRIVE_ARSIVLE_EVICT"
# Ayni kural yukleme sinyali icin: `--yukleme-komut` / env YALNIZ test (rc=0 = yuklendi).
YUKLEME_ENV = "DRIVE_ARSIVLE_YUKLEME"
EVICT_DENEME = 3
RC_BEKLIYOR = 3


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

    Çağıran: atla=True ise kopyalama ATLANIR; yükleme bekle → evict → yerel sil
    sırası yine işler (önceki koşumun BEKLIYOR satırını böyle devralır).
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
    """Evict çağırır; hata loglanır, rc DEĞİŞMEZ.

    `komut` None → `drive_birak.evict` (varsayılan, tek kaynak).

    `komut` iki biçimden biri olabilir:
      1) '{yol}' placeholder içeren tek satır string (shlex.quote ile güvenli)
      2) komut + ' ' + <argüman> bicimini (aynı şekilde shlex.quote)

    Boşluklu / tırnaklı yol (özel: `Ortak Drive'lar/...`) shlex.quote ile
    KORUNUR — komut string'i shell=True ile calistirildiginda kelimelere
    yanlış bölünmez.
    """
    if komut is None:
        if drive_evict(yol):
            log.append("evict=ok")
            return True
        log.append("evict=hata kaynak=drive_birak")
        return False
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


def yuklendi_cagir(komut, yol):
    """Yukleme bitti mi? True | False | None (okunamadi).

    `komut` None → `drive_birak.yuklendi_mi` (varsayilan, tek kaynak). Test enjeksiyonu:
    komut rc=0 → yuklendi, rc!=0 → bitmedi (evict_cagir ile ayni '{yol}' bicimleri).
    """
    if komut is None:
        return drive_yuklendi_mi(yol)
    if "{yol}" in komut:
        k = komut.format(yol=shlex.quote(yol))
    else:
        k = komut + " " + shlex.quote(yol)
    try:
        proc = subprocess.run(k, shell=True, capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return proc.returncode == 0


def _ayni_dosya(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def birak_ve_sil(a, is_, sayac, son_an):
    """SIRA: yukleme bitti mi → evict (EVICT_DENEME) → yerel sil. Doner: hata var mi.

    `--evict` bayragi False ise evict ATLANIR (yukleme_bekle + yerel_sil yine yapilir;
    sha-esit-degil zaten ust katmanda erken cikiyor).
    """
    gore, tam_yol, hedef, yerel_sil = is_
    if not yukleme_bekle(hedef, son_an, a.yokla_aralik,
                         yokla_fn=lambda y: yuklendi_cagir(a.yukleme_komut, y)):
        sayac["bekliyor"] += 1
        print("dosya=%s durum=BEKLIYOR (yukleme bitmedi; evict YOK, yerel SILINMEDI)" % gore)
        return False
    log = []
    tamam = True
    if a.evict:
        tamam = False
        for deneme in range(1, EVICT_DENEME + 1):
            if evict_cagir(a.evict_komut, hedef, log):
                tamam = True
                break
            if deneme < EVICT_DENEME:
                time.sleep(a.yokla_aralik)
        for l in log:
            print("dosya=%s %s" % (gore, l))
        if not tamam:
            sayac["evict_hata"] += 1
            print("dosya=%s durum=evict-%dx-hata (yerel SILINMEDI)" % (gore, EVICT_DENEME))
            return False
        sayac["evict_ok"] += 1
    if yerel_sil:
        try:
            os.remove(tam_yol)
            sayac["silindi"] += 1
        except OSError as e:
            print("dosya=%s durum=silme-hata tip=%s"
                  % (gore, type(e).__name__), file=sys.stderr)
            sayac["hata"] += 1
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="DRIVE-ARSIVLE: yaz -> sha256 -> yukleme bekle -> evict -> yerel sil"
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
    # 🔴 9 Eki 2026 — evict ZORUNLU (bayraksiz kosumda da; sha teyitsiz dosya
    # EVICT EDILMEZ): `--evict` VARSAYILAN True; `--evict-yapma` ile kapatilir
    # (yukleme+sha+yukleme_bekle + yerel_sil YINE calisir, evict atlanir).
    # `--kuru` ile birlikte anlamsizdir (kuru hicbir sey yapmaz).
    ap.add_argument("--evict", action="store_true", default=True, dest="evict",
                    help="evict adimi ZORUNLU (varsayilan=True; --evict-yapma ile atla)")
    ap.add_argument("--evict-yapma", action="store_false", dest="evict",
                    help="evict adimini ATLA (upload+sha+yukleme_bekle+yerel_sil yine yapilir)")
    ap.add_argument("--evict-komut", default=os.environ.get(EVICT_ENV),
        help="evict komutu (YALNIZ test enjekte eder; verilmezse drive_birak.evict); "
             "'{yol}' placeholder'i veya komut + argüman bicimi")
    ap.add_argument("--yukleme-komut", default=os.environ.get(YUKLEME_ENV),
        help="yukleme-bitti-mi komutu (YALNIZ test; rc=0 = yuklendi); "
             "verilmezse drive_birak.yuklendi_mi")
    ap.add_argument("--yokla-aralik", type=float, default=10.0,
                    help="yukleme yoklama araligi sn (varsayilan 10)")
    ap.add_argument("--yukleme-tavan", type=float, default=600.0,
                    help="kosum basina yukleme bekleme tavani sn (varsayilan 600)")
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
        "bekliyor": 0, "yuklendi_okunan": 0, "yuklendi_evet": 0,
    }
    hata_var = False
    bekleyen = []  # [(gore, tam_yol, hedef, yerel_sil)] — sha esit, yukleme+evict sirasi bekler

    print("# drive-arsivle kok=%s hedef=%s kaynak=%s kuru=%d yerel_tut=%d evict=%d" % (
        kok, a.hedef, a.kaynak, int(bool(a.kuru)), int(bool(a.yerel_tut)), int(bool(a.evict))))
    print("# dosya_sayisi=%d" % len(liste))

    # ---- ASAMA 1: kopyala + sha256 dogrula (evict/silme YOK) ----
    for tam_yol, gore in liste:
        sayac["dosya"] += 1
        if a.kuru:
            # KURU = SALT OKUMA: dosya ICERIGI OKUNMAZ. Drive'da sha256 okumak indirilmemis
            # dosyayi INDIRIR (7 Eki olculdu: 225 dosya / 666 MB). Yalniz stat + yukleme
            # sinyali (metadata) okunur; atla/kopyala karari sha'siz verilemez → 'hedef-var'.
            hedef = os.path.join(kok, a.hedef, gore)
            if os.path.exists(hedef):
                y = yuklendi_cagir(a.yukleme_komut, hedef)
                if y is not None:
                    sayac["yuklendi_okunan"] += 1
                    sayac["yuklendi_evet"] += int(y)
                print("dosya=%s hedef=%s durum=hedef-var yuklendi=%s" % (
                    gore, os.path.relpath(hedef, kok), "?" if y is None else int(y)))
            else:
                print("dosya=%s hedef=%s durum=kopyala bayt=%d" % (
                    gore, os.path.relpath(hedef, kok), os.path.getsize(tam_yol)))
            continue
        sha_k = sha256_dosya(tam_yol)
        hedef, atla = hedef_yolu_coz(kok, a.hedef, gore, sha_k)
        boyut = os.path.getsize(tam_yol)
        rel = os.path.relpath(hedef, kok)

        # AYNI içerik (muhtemel/suffix aynı içerikte) → kopya ATLA; yukleme+evict+sil sirasi yine
        if atla:
            sayac["atlandi_ayni"] += 1
            print("dosya=%s sha=%s hedef=%s durum=atlandi_ayni" % (
                gore, sha_k[:8], rel))
        else:
            # Yeni yazma (adı, ÇAKıŞMADA farklı içerikse kıyara eklenmiş)
            print("dosya=%s sha=%s hedef=%s durum=kopyala bayt=%d" % (
                gore, sha_k[:8], rel, boyut))

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
                # Kaynak SİLİNMEZ (veri kaybı), evict YOK.
                sayac["hata"] += 1
                hata_var = True
                continue

            sayac["kopyalandi"] += 1
            sayac["bayt"] += boyut

        # Kaynak hedefin KENDISIYSE (Drive icinden kosum) asla silinmez.
        yerel_sil = not a.yerel_tut and not _ayni_dosya(tam_yol, hedef)
        bekleyen.append((gore, tam_yol, hedef, yerel_sil))

    # ---- ASAMA 2: yukleme bitti mi → evict → yerel sil (tavan simdi baslar) ----
    son_an = time.monotonic() + a.yukleme_tavan
    for is_ in bekleyen:
        if birak_ve_sil(a, is_, sayac, son_an):
            hata_var = True

    print("DRIVE_ARSIVLE dosya=%d kopyalandi=%d atlandi_ayni=%d silindi=%d "
          "evict_ok=%d evict_hata=%d hata=%d bayt=%d kuru=%d "
          "bekliyor=%d yuklendi_okunan=%d yuklendi_evet=%d" % (
              sayac["dosya"], sayac["kopyalandi"], sayac["atlandi_ayni"],
              sayac["silindi"], sayac["evict_ok"], sayac["evict_hata"],
              sayac["hata"], sayac["bayt"], int(bool(a.kuru)),
              sayac["bekliyor"], sayac["yuklendi_okunan"], sayac["yuklendi_evet"]))
    if hata_var:
        return 1
    return RC_BEKLIYOR if sayac["bekliyor"] else 0


if __name__ == "__main__":
    sys.exit(main())

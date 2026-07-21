#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel stl/ klasorundeki uretim dosyalarini OZEL R2 kovasina (pruvo-ozel) yukler.

COK-PARCA TASARIMI (mimar duzeltme turu, 17 Tem aksam): bir urunun BIRDEN COK parca
dosyasi olabilir — istisna degil NORM (stl/'de ~6.100 dosya `<id>--<parca>.stl` adli).
  <urun-id>--<parca>.stl  ->  r2: stl/<urun-id>/<parca>.stl
  <urun-id>.stl           ->  r2: stl/<urun-id>/<urun-id>.stl  (tekli ad da klasore normalize)
Uzanti kucuk harfe cevrilir (.STL -> .stl); parca adinin harf buyuklugu korunur.
Onek urunler.json id listesiyle DOGRULANIR: listede yoksa HATALI-AD raporuna (tahmin YOK).

KAYNAK-ID ESLEMESI (mimar duzeltme turu, 17 Tem gece). KOK NEDEN: 9.075 dosyanin oneki
urun-id DEGIL kaynak-id (Thingiverse sayisal / Printables `prNNN`) — eski toplu STL
indirmesi urun-id'ye gore degil kaynak sisteme gore adlandirmisti. Onek idler'de yoksa,
gizli `.urun-kaynaklari.json` (ANA repo koku, gitignore'lu, SALT-OKUNUR) kaydindaki
`link` alanindan cikarilan kaynak-id -> urun-id sozlugune bakilir:
  thingiverse.com/thing:<sayi>      -> kaynak-id = "<sayi>"
  printables.com/model/<sayi>-...   -> kaynak-id = "pr<sayi>"
Bir kaynak-id BIRDEN FAZLA urune bagliysa TAHMIN EDILMEZ — o dosyalar "cakisan" raporuna
duser, yuklenmez (hatali-ad'dan AYRI sayilir). Eslenirse R2 anahtari
stl/<urun-id>/<orijinal-dosya-adi> olur (orijinal ad KORUNUR, sadece uzanti kucultulur) —
boylece kaynak-id iz olarak dosya adinda kalir. Gizli dosya bulunamazsa (worktree, baska
makine) esleme BOS doner — davranis eskisiyle AYNI (kaynak-id'li dosyalar hatali-ad'da kalir).

IDEMPOTENS — YEREL MANIFEST (mimar duzeltme turu). KOK NEDEN DERSI: wrangler'da
`r2 object list` / `head` alt komutu YOK; ilk surum listeyi sessizce bos alip HER kosumda
her seyi yeniden yukluyordu (canli kosumda yakalandi: 2. kosum atlandi=0). Cozum:
gitignore'lu `.stl-r2-manifest.json` (repo koku) anahtar -> {sha1, boyut} tutar; ikisi de
ayni ise atlanir (SHA kiyasi: ayni boyutlu farkli icerik de yakalanir). Manifest her
basarili yuklemeden SONRA atomik yazilir (kesilen kosum kaldigi yerden devam eder).
Manifest silinirse dosyalar yeniden yuklenir (zararsiz: ayni anahtarin ustune yazar).

PARALEL YUKLEME (mimar mikro paketi, 17 Tem gece). KOK NEDEN: her dosya icin AYRI
`npx wrangler r2 object put` sureci aciliyor, sirali ~6 sn/dosya -> 8.784 dosyalik parti
~14 saat. Cozum: `--paralel N` (varsayilan 6; 1 = eski sirali davranis birebir) N eszamanli
yukleyici calistirir -> ~1-1,5 saate iner. MANIFEST YARIS KORUMASI — TEK YAZICI TASARIMI:
yukleyici is parcaciklari manifeste ASLA yazmaz; yalnizca kosum baslangicindaki SALT-OKUNUR
snapshot'i okur (atla-kontrolu). Manifeste sadece ANA is parcacigi (havuzu suren) her basarili
sonuc geldikce atomik yazar -> iki yazicinin ayni anda yazmasi IMKANSIZ, kayit kaybi olmaz
(.urun-kaynaklari.json'da yasanan 259-kayip sinifi bu tasarimla dislanir; test-baski-senkron.py
neg-kontrolu serilestirilmemis yazimanin kaybettigini deterministik kanitlar). Kesinti aninda
en fazla "ucustaki" (yuklenmis ama sonucu henuz islenmemis) dosyalar manifeste girmez -> sonraki
kosum onlari yeniden yukler (zararsiz); ONCEKI kayitlar asla silinmez.

ANAHTAR NORMALIZASYONU + YOL-GEZINME KAPISI (mimar paketi G1, 21 Tem — MaCiT TALEP 2).
KOK NEDEN: adi nokta ile biten dosyalar (`<ad>..stl`) anahtarda cift nokta uretiyor; wrangler
anahtari URL yoluna HAM gomdugu icin Cloudflare edge yol-gezinme korumasi 403 donuyor —
4 dosya (MaCiT 3 bildirdi, olcumde 4. cikti: `254529--S.E..STL`) yukleme+dogrulama bacagini
gecemiyor, dolayisiyla silinemiyor. SECIM (a) percent-encode DEGIL (b) NORMALIZE, gerekcesi
OLCULDU: `.stl-r2-manifest.json` (10.074 kayit) icinde `..` gecen anahtar sayisi = 0 -> hicbir
YUKLENMIS nesne bu bicimde degil, normalizasyon KIRICI DEGIL. Ayrica (a) wrangler'in kendi
kodlamasina bagimli kalir (kor nokta), (b) ise anahtari deterministik + test edilebilir kilar.
Normalizasyon SUS-PAYI DEGIL GUVENLIK KAPISI: `..`/`.` yol parcasi, mutlak yol, ters bolu ve
NUL bayti REDDEDILIR (hatali-ad'a duser, yuklenmez); parca ici arka arkaya noktalar TEKE
indirilir ve parcanin bas/son noktalari kirpilir.

COK-PARCALI (MULTIPART) YUKLEME (mimar paketi G1, 21 Tem — MaCiT TALEP 1). KOK NEDEN:
`wrangler r2 object put` tek-parca sinirinda patliyor ("Wrangler only supports uploading files
up to 300 MiB in size") -> olcumde 5 dosya (682/637/467/383/341 MB, toplam ~2,4 GB) R2'ye
CIKAMIYOR. Cozum: 300 MiB USTU dosyalar S3 API (boto3, R2 S3-uyumlu ucnokta) uzerinden
cok-parcali yuklenir; 300 MiB ALTI dosyalar ESKI wrangler yolunda birebir kalir (regresyon
yok, token gerekmez). Kimlik gitignore'lu `.r2-credentials.json`'dan okunur (endpoint +
access_key + secret); SIR LOGLANMAZ. DIKKAT: o dosyadaki `bucket` alani MEDYA kovasi
(`pruvo-media`) — burada KULLANILMAZ, hedef kova sabit `pruvo-ozel`. boto3 ya da kimlik yoksa
NET hata basilir (sessiz basarisizlik YOK).

  python3 tools/stl-r2-yukle.py            # yerel stl/ -> r2 pruvo-ozel/stl/<id>/<parca> (paralel 6)
  python3 tools/stl-r2-yukle.py --paralel 1  # eski sirali davranis (tek yukleyici)
  python3 tools/stl-r2-yukle.py --kuru     # yalniz ne yapacagini soyle (yukleme/manifest yok)
  python3 tools/stl-r2-yukle.py --dizin X  # farkli kaynak klasor

Yukleme yerel wrangler oturumuyla (npx wrangler r2 object put ... --remote) — token gerekmez.
Sonda "yuklendi / atlandi / hatali-ad" sayimi basilir. ZIP YOK (280 MB'lik dosyalar var;
worker'da sikistirma yapilmaz — yonetim sayfasi parcalari tek tek indirir).
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKET = "pruvo-ozel"
PREFIX = "stl"
UZANTILAR = (".stl", ".3mf")
MANIFEST = os.path.join(REPO, ".stl-r2-manifest.json")
KAYNAKLAR = os.path.join(REPO, ".urun-kaynaklari.json")
KIMLIK = os.path.join(REPO, ".r2-credentials.json")

# wrangler'in tek-parca `r2 object put` siniri. Bu boyutun USTUNDEKI dosyalar S3 API ile
# cok-parcali yuklenir (bkz. modul basligindaki COK-PARCALI YUKLEME notu).
WRANGLER_TEK_PARCA_SINIRI = 300 * 1024 * 1024   # 300 MiB
PARCA_BOYU = 64 * 1024 * 1024                    # cok-parcali yuklemede parca boyu


class AnahtarReddi(ValueError):
    """R2 anahtari guvenlik kapisindan gecemedi (yol-gezinme / gecersiz karakter)."""


def anahtar_normalize(anahtar):
    """R2 anahtarini normalize eder; TEHLIKELI anahtari REDDEDER (AnahtarReddi firlatir).

    SAF fonksiyon. Iki isi ayri sirayla yapar — sira ONEMLI:
      1) GUVENLIK KAPISI (once): mutlak yol (`/` ile baslar), bos/`.`/`..` yol parcasi,
         ters bolu (`\\`) ve NUL bayti REDDEDILIR. Normalizasyondan ONCE bakilir; yoksa
         `..` parcasi noktalar sadelestirilerek kapidan sizardi.
      2) NORMALIZASYON (sonra): her yol parcasinda arka arkaya gelen noktalar TEKE indirilir
         (`ad..stl` -> `ad.stl`), parcanin basindaki/sonundaki noktalar kirpilir. Cloudflare
         edge'in 403 dondurdugu cift-nokta bicimi boylece hic olusmaz.
    Normalizasyon bir parcayi bosaltirsa (or. `...`) anahtar REDDEDILIR (tahmin edilmez)."""
    if not isinstance(anahtar, str) or not anahtar:
        raise AnahtarReddi("bos ya da metin olmayan anahtar")
    if "\x00" in anahtar:
        raise AnahtarReddi("anahtarda NUL bayti")
    if "\\" in anahtar:
        raise AnahtarReddi("anahtarda ters bolu: " + anahtar)
    if anahtar.startswith("/"):
        raise AnahtarReddi("mutlak yol anahtari: " + anahtar)
    parcalar = anahtar.split("/")
    temiz = []
    for p in parcalar:
        if p == "" or p == "." or p == "..":
            raise AnahtarReddi("gecersiz yol parcasi (%r) — yol-gezinme: %s" % (p, anahtar))
        yeni = re.sub(r"\.{2,}", ".", p).strip(".")
        if not yeni:
            raise AnahtarReddi("normalizasyon sonrasi bos yol parcasi (%r): %s" % (p, anahtar))
        temiz.append(yeni)
    return "/".join(temiz)

_THING_DESENI = re.compile(r"thingiverse\.com/thing:(\d+)")
_PRINTABLES_DESENI = re.compile(r"printables\.com/model/(\d+)")


def urun_idleri():
    """urunler.json'daki gecerli id kumesi (onek dogrulamasi icin)."""
    try:
        with open(os.path.join(REPO, "urunler.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return {u.get("id") for u in d if isinstance(u, dict) and u.get("id")}


def _kaynak_id_cikar(link):
    """link URL'sinden dosya-onek bicimindeki kaynak-id'yi cikarir: Thingiverse sayisal
    ("1002858"), Printables "pr<sayi>". Baska kaynaklar (CGTrader, kendi ureticimiz,
    MakerWorld, GitHub...) icin None doner — yerel STL adlandirmasi bu ikisi disinda
    kaynak-id onegi kullanmadi (bkz. modul basligindaki KAYNAK-ID ESLEMESI notu)."""
    if not isinstance(link, str):
        return None
    m = _THING_DESENI.search(link)
    if m:
        return m.group(1)
    m = _PRINTABLES_DESENI.search(link)
    if m:
        return "pr" + m.group(1)
    return None


def kaynak_esleme(gizli_kayit):
    """SAF fonksiyon. gizli .urun-kaynaklari.json icerigini (urun-id -> {"link":..., ...})
    alir, (esle, cakisan) dondurur:
    - esle: kaynak-id -> urun-id, YALNIZCA o kaynak-id TEK bir urune bagliysa.
    - cakisan: birden fazla urune bagli kaynak-id kumesi — TAHMIN EDILMEZ, esle'ye GIRMEZ,
      cagiran taraf bu dosyalari ayri ("cakisan") raporlar, yuklemez."""
    adaylar = {}
    if isinstance(gizli_kayit, dict):
        for urun_id, kayit in gizli_kayit.items():
            if not isinstance(kayit, dict):
                continue
            kid = _kaynak_id_cikar(kayit.get("link"))
            if kid:
                adaylar.setdefault(kid, set()).add(urun_id)
    esle, cakisan = {}, set()
    for kid, urunler in adaylar.items():
        if len(urunler) == 1:
            esle[kid] = next(iter(urunler))
        else:
            cakisan.add(kid)
    return esle, cakisan


def kaynak_esleme_yukle(yol):
    """Diskten gizli kaydi okuyup kaynak_esleme() uygular. Dosya yoksa/bozuksa (worktree'de
    YOK, CI, baska makine) BOS esleme+cakisan doner — davranis eskisiyle AYNI kalir
    (kaynak-id onekli dosyalar hatali-ad'da kalir, sessizce atlanmaz)."""
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}, set()
    return kaynak_esleme(d)


def siniflandir(dosyalar, idler, kaynak_esle=None, kaynak_cakisan=None):
    """Dosya adlarini ([(ad, r2_anahtari)], hatali_ad, cakisan_ad) olarak ayirir. SAF fonksiyon.
    - `<id>--<parca>.stl` -> stl/<id>/<parca>.stl ; `<id>.stl` -> stl/<id>/<id>.stl
    - onek id listesinde yoksa: kaynak_esle'de TEKIL karsiligi varsa oraya yonlendirilir
      (r2 anahtari stl/<eslenen-id>/<orijinal-dosya-adi>, orijinal ad KORUNUR); onek
      kaynak_cakisan'daysa (birden fazla urune bagli) cakisan_ad'a duser (TAHMIN YOK,
      yuklenmez); hicbiri degilse HATALI-AD (eskisi gibi).
    - parca adi bossa HATALI-AD (tahmin edilmez)
    - .stl/.3mf disi uzantilar sessizce atlanir
    - uretilen anahtar anahtar_normalize()'den gecer: cift nokta sadelesir (`ad..stl` ->
      `ad.stl`, Cloudflare 403'unun kok nedeni), yol-gezinme (`..`) iceren anahtar
      REDDEDILIR -> HATALI-AD (yuklenmez)"""
    kaynak_esle = kaynak_esle or {}
    kaynak_cakisan = kaynak_cakisan or set()
    hedefler, hatali_ad, cakisan_ad = [], [], []
    for ad in dosyalar:
        kok, uz = os.path.splitext(ad)
        if uz.lower() not in UZANTILAR:
            continue
        if "--" in kok:
            onek, parca = kok.split("--", 1)
        else:
            onek, parca = kok, kok
        if not parca:
            hatali_ad.append(ad)
            continue
        if idler is not None and onek not in idler:
            if onek in kaynak_cakisan:
                cakisan_ad.append(ad)
                continue
            eslenen_id = kaynak_esle.get(onek)
            if eslenen_id is None:
                hatali_ad.append(ad)
                continue
            ham = PREFIX + "/" + eslenen_id + "/" + kok + uz.lower()
        else:
            ham = PREFIX + "/" + onek + "/" + parca + uz.lower()
        # ANAHTAR KAPISI: cift-nokta normalize edilir, yol-gezinme REDDEDILIR (hatali-ad'a
        # duser -> yuklenmez, tahmin edilmez). Bkz. modul basligi ANAHTAR NORMALIZASYONU.
        try:
            hedefler.append((ad, anahtar_normalize(ham)))
        except AnahtarReddi:
            hatali_ad.append(ad)
    return hedefler, hatali_ad, cakisan_ad


def sha1_dosya(yol):
    h = hashlib.sha1()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def manifest_oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def manifest_yaz(yol, manifest):
    # Atomik yazim: yarim yazilmis manifest sonraki kosumun idempotensini bozmasin.
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, sort_keys=True)
    os.replace(gecici, yol)


def yukle_wrangler(yerel, anahtar):
    """ESKI YOL — 300 MiB altindaki dosyalar icin birebir korunur (yerel wrangler oturumu,
    token gerekmez)."""
    komut = ["npx", "wrangler", "r2", "object", "put", BUCKET + "/" + anahtar,
             "--file", yerel, "--remote"]
    p = subprocess.run(komut, cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write((p.stdout or "") + (p.stderr or ""))
        return False
    return True


def _s3_istemci(kimlik_yol=KIMLIK):
    """R2 S3-uyumlu istemcisi. Eksik bagimlilik/kimlik NET hata verir (sessiz basarisizlik
    YASAK). 🔴 SIR LOGLANMAZ: hata metinlerinde yalnizca ALAN ADI gecer, deger GECMEZ.
    NOT: kimlik dosyasindaki `bucket` alani MEDYA kovasidir — burada KULLANILMAZ, hedef kova
    modul sabiti BUCKET (`pruvo-ozel`)."""
    try:
        import boto3  # yerel bagimlilik; yoksa asagida net hata
    except ImportError as e:
        raise RuntimeError(
            "cok-parcali yukleme icin boto3 gerekli ama kurulu degil "
            "(pip3 install boto3) — 300 MiB ustu dosyalar wrangler ile YUKLENEMEZ") from e
    try:
        with open(kimlik_yol, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise RuntimeError(
            "R2 kimlik dosyasi okunamadi: %s (cok-parcali yukleme icin gerekli)" % kimlik_yol
        ) from e
    eksik = [alan for alan in ("endpoint", "access_key", "secret") if not cfg.get(alan)]
    if eksik:
        raise RuntimeError("R2 kimlik dosyasinda eksik alan(lar): %s" % ", ".join(eksik))
    return boto3.client("s3", endpoint_url=cfg["endpoint"],
                        aws_access_key_id=cfg["access_key"],
                        aws_secret_access_key=cfg["secret"], region_name="auto")


def yukle_multipart(yerel, anahtar, istemci_fn=_s3_istemci):
    """YENI YOL — 300 MiB USTU dosyalar (wrangler tek-parca sinirini asanlar) S3 API ile
    cok-parcali yuklenir. Basarisizlikta NET hata basar ve False doner (sessiz gecis YOK)."""
    try:
        from boto3.s3.transfer import TransferConfig
        s3 = istemci_fn()
        ayar = TransferConfig(multipart_threshold=WRANGLER_TEK_PARCA_SINIRI,
                              multipart_chunksize=PARCA_BOYU, use_threads=True)
        s3.upload_file(yerel, BUCKET, anahtar, Config=ayar)
        return True
    except Exception as e:  # noqa: BLE001 — kok neden kullaniciya AYNEN gosterilir
        sys.stderr.write("COK-PARCALI YUKLEME BASARISIZ (%s): %s\n" % (anahtar, e))
        return False


def yukle(yerel, anahtar):
    """Boyuta gore yol secer: 300 MiB ve alti -> wrangler (eski davranis birebir),
    ustu -> S3 cok-parcali. Bkz. modul basligindaki COK-PARCALI YUKLEME notu."""
    try:
        boyut = os.path.getsize(yerel)
    except OSError as e:
        sys.stderr.write("dosya boyutu okunamadi (%s): %s\n" % (yerel, e))
        return False
    if boyut > WRANGLER_TEK_PARCA_SINIRI:
        return yukle_multipart(yerel, anahtar)
    return yukle_wrangler(yerel, anahtar)


def _isle(dizin, ad, anahtar, snapshot, gonderici):
    """Tek dosyayi isleyen YUKLEYICI is parcacigi govdesi. Manifeste YAZMAZ (tek-yazici
    tasarim): yalnizca `snapshot` (kosum basi salt-okunur manifest kopyasi) ile atla-kontrolu
    yapar. (durum, ad, anahtar, veri) doner:
      ("atlandi", ...)  -> snapshot'ta ayni sha1+boyut var, yuklenmedi
      ("yuklendi", ..., {sha1,boyut}) -> basarili yukleme; ANA is parcacigi manifeste yazar
      ("hata", ...)     -> gonderici False dondu"""
    yerel = os.path.join(dizin, ad)
    boyut = os.path.getsize(yerel)
    ozet = sha1_dosya(yerel)
    kayit = snapshot.get(anahtar)
    if kayit and kayit.get("sha1") == ozet and kayit.get("boyut") == boyut:
        return ("atlandi", ad, anahtar, None)
    if not gonderici(yerel, anahtar):
        return ("hata", ad, anahtar, None)
    return ("yuklendi", ad, anahtar, {"sha1": ozet, "boyut": boyut})


def kos(dizin, idler, manifest_yol, kuru=False, yukle_fn=None, kaynak_esle=None,
        kaynak_cakisan=None, paralel=1):
    """Ana is akisi (test edilebilir): (yuklendi, atlandi, hatali_ad, cakisan_ad) dondurur.
    kuru=True: yukleme YOK, manifest'e yazma YOK — yuklenecekler sayilir/basilir.
    kaynak_esle/kaynak_cakisan: kaynak_esleme()'den gelen sozlukce/kume (bkz. siniflandir).
    paralel: eszamanli yukleyici sayisi (varsayilan 1 = sirali/eski davranis birebir; >1 ise
    N is parcacigi yukler, manifeste yalnizca ANA is parcacigi tek-yazici olarak yazar -> yaris
    yok). kuru VEYA paralel<=1 iken sirali yol kullanilir (byte-birebir eski davranis)."""
    gonderici = yukle_fn or yukle
    dosyalar = sorted(os.listdir(dizin))
    hedefler, hatali_ad, cakisan_ad = siniflandir(dosyalar, idler, kaynak_esle, kaynak_cakisan)
    manifest = manifest_oku(manifest_yol)
    yuklendi = atlandi = 0

    if kuru or paralel <= 1:
        # SIRALI YOL — eski davranis birebir korunur (tek yukleyici, sirali manifest yazimi).
        for ad, anahtar in hedefler:
            yerel = os.path.join(dizin, ad)
            boyut = os.path.getsize(yerel)
            ozet = sha1_dosya(yerel)
            kayit = manifest.get(anahtar)
            if kayit and kayit.get("sha1") == ozet and kayit.get("boyut") == boyut:
                atlandi += 1
                continue
            if kuru:
                print("YUKLENECEK: %s -> r2://%s/%s (%d B)" % (ad, BUCKET, anahtar, boyut))
                yuklendi += 1
                continue
            if not gonderici(yerel, anahtar):
                sys.exit("R2 yuklemesi basarisiz (wrangler oturumu acik mi?): " + anahtar)
            manifest[anahtar] = {"sha1": ozet, "boyut": boyut}
            manifest_yaz(manifest_yol, manifest)  # her yuklemeden sonra — kesinti guvenli
            print("yuklendi: r2://%s/%s (%d B)" % (BUCKET, anahtar, boyut))
            yuklendi += 1
        return yuklendi, atlandi, hatali_ad, cakisan_ad

    # PARALEL YOL — N yukleyici, TEK YAZICI. Yukleyiciler `snapshot`i SALT-OKUR (degismez
    # kopya); manifeste yalnizca bu (ana) is parcacigi as_completed sirasiyla atomik yazar.
    # Boylece iki yazicinin ayni anda yazmasi imkansiz -> kayit kaybi yok (bkz. modul basligi).
    snapshot = dict(manifest)
    hata_anahtar = None
    with ThreadPoolExecutor(max_workers=paralel) as havuz:
        gelecekler = [havuz.submit(_isle, dizin, ad, anahtar, snapshot, gonderici)
                      for ad, anahtar in hedefler]
        for gel in as_completed(gelecekler):
            durum, ad, anahtar, veri = gel.result()
            if durum == "atlandi":
                atlandi += 1
            elif durum == "yuklendi":
                manifest[anahtar] = veri
                manifest_yaz(manifest_yol, manifest)  # TEK YAZICI (ana) — atomik, kesinti guvenli
                print("yuklendi: r2://%s/%s (%d B)" % (BUCKET, anahtar, veri["boyut"]))
                yuklendi += 1
            else:  # "hata"
                hata_anahtar = hata_anahtar or anahtar
    if hata_anahtar is not None:
        sys.exit("R2 yuklemesi basarisiz (wrangler oturumu acik mi?): " + hata_anahtar)
    return yuklendi, atlandi, hatali_ad, cakisan_ad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dizin", default=os.path.join(REPO, "stl"))
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    ap.add_argument("--paralel", type=int, default=6,
                    help="eszamanli yukleyici sayisi (varsayilan 6; 1 = sirali/eski davranis)")
    ap.add_argument("--kaynaklar", default=KAYNAKLAR,
                    help="gizli kaynak-id->urun-id kaydi (varsayilan: ana repo koku; "
                         "worktree/baska makinede yoksa esleme BOS kalir)")
    a = ap.parse_args()

    if not os.path.isdir(a.dizin):
        sys.exit("kaynak klasor yok: " + a.dizin)

    idler = urun_idleri()  # None = urunler.json okunamadi (onek kontrolu atlanir)
    kaynak_esle, kaynak_cakisan = kaynak_esleme_yukle(a.kaynaklar)
    yuklendi, atlandi, hatali_ad, cakisan_ad = kos(
        a.dizin, idler, MANIFEST, kuru=a.kuru,
        kaynak_esle=kaynak_esle, kaynak_cakisan=kaynak_cakisan,
        paralel=max(1, a.paralel))

    print("\nOZET: yuklendi=%d atlandi=%d hatali-ad=%d cakisan=%d (kaynak: %s%s)"
          % (yuklendi, atlandi, len(hatali_ad), len(cakisan_ad), a.dizin,
             ", --kuru" if a.kuru else ""))
    if cakisan_ad:
        print("CAKISAN KAYNAK-ID (%d dosya; onek gizli kayitta BIRDEN FAZLA urune bagli —"
              " TAHMIN EDILMEDI, yuklenmedi, elle karar verilmeli):" % len(cakisan_ad))
        for ad in cakisan_ad[:40]:
            print("  - " + ad)
        if len(cakisan_ad) > 40:
            print("  ... (+%d dosya daha)" % (len(cakisan_ad) - 40))
    if hatali_ad:
        print("HATALI AD (%d dosya; onek urunler.json id'si DEGIL, gizli kaynak eslemesinde de"
              " YOK ya da parca adi bos — TAHMIN EDILMEDI, once urun-id'ye adlandirilmali):"
              % len(hatali_ad))
        for ad in hatali_ad[:40]:
            print("  - " + ad)
        if len(hatali_ad) > 40:
            print("  ... (+%d dosya daha)" % (len(hatali_ad) - 40))


if __name__ == "__main__":
    main()

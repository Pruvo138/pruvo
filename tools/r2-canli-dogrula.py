#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r2-canli-dogrula.py — KOVA-GENEL CANLI R2 dogrulama araci (salt okuma; --sil haric).

NEDEN VAR (15 Eki 2026): ozel kova `pruvo-ozel` icin S3 liste/okuma kimligi YOK (jeton
AccessDenied). Bu yuzden iki arac kordu:
  * `tools/stl-r2-yukle.py --yerel-sil` yalniz YEREL MANIFESTE bakar — manifest bir beyandir,
    R2'deki nesnenin kaniti DEGILDIR (hukum: yerel STL yalniz R2'de CANLI dogrulaninca silinir).
  * `tools/r2-upload.py` `sil_ve_dogrula`/`s3_var_mi` bu kovada kor; `wrangler r2 object delete`
    OLMAYAN anahtara da "Delete complete." basar (yalanci pozitif).
Cozum: yeni sir YOK — yerel wrangler oturumuyla anahtar basina `r2 object get` -> govde
gecici dosyaya iner, sha1+boyut olculur, gecici dosya HEMEN silinir.

CANLI OLCULMUS WRANGLER DAVRANISI (wrangler 4.151.0, 15 Eki 2026 — tahmin degil):
  * var olan anahtar        : rc=0, cikti "Download complete.", --file dolu.
  * olmayan anahtar         : rc=1, cikti "✘ [ERROR] The specified key does not exist.",
                              --file 0 BAYTLA OLUSTURULUR (dosya varligi kanit DEGILDIR).
  * OLMAYAN KOVA            : `object get` BIREBIR AYNI "The specified key does not exist."
                              basar (rc=1) — anahtar-yok ile kova-yok AYIRT EDILEMEZ.
                              => KOVA ON-KAPISI: once `r2 bucket info <kova>` rc=0 + "name: <kova>"
                              olmali; olmazsa HICBIR anahtar sorulmaz, hepsi OLCULEMEDI.
  * gecersiz kimlik         : rc=1, "Authentication failed"/"Invalid format for Authorization
                              header" — not-found metni YOK -> OLCULEMEDI.
  Not-found karari rc VE metin BIRLIKTE verilir (rc==1 + not-found metni + --file bos/yok);
  belirsiz her hal OLCULEMEDI'dir, ASLA "yok"/"silindi" degildir. "var" karari da rc==0 +
  "Download complete." + bos olmayan govde ister.

KIPLER
  stl  yerel stl/ <-> R2 esitligi. Anahtar eslemesi `tools/stl-r2-yukle.py` ile BIREBIR
       (o modulun siniflandir/kaynak_esleme_yukle/urun_idleri/sha1_dosya fonksiyonlari
       importlib ile ICE AKTARILIR — kopya yok). Siniflar:
         ESIT       canli nesne var, sha1 VE boyut esit
         FARKLI     canli nesne var, sha1 ya da boyut farkli
         YOK        canli not-found (kova on-kapisi acikken)
         OLCULEMEDI rc/metin belirsiz, zaman asimi, yerel dosya okunamadi ...
         HATALI_AD  esleme yok / cakisan kaynak-id / anahtar kapisi reddi (get CAGRILMAZ)
       Manifest (`.stl-r2-manifest.json`) YALNIZ BILGI (MANIFEST=<n>); siniflandirmada
       KULLANILMAZ. `--sil` (vars. KAPALI): yalniz BU koşumda ESIT cikan yerel dosyalari,
       silmeden hemen once yerel sha1 yeniden olculup ayni ise siler.
  yok  silme sonrasi kanit: `--anahtar-dosyasi` (satir basina bir anahtar; bos ve # satirlari
       atlanir). SILINDI_KANITLI (canli not-found) · HALA_VAR · OLCULEMEDI. Bu kip HICBIR
       sey silmez/yazmaz (yalniz istenirse --rapor).

rc (iki kip): hepsi hedef sinifta (ESIT / SILINDI_KANITLI) -> 0 ·
  FARKLI / YOK / HATALI_AD / HALA_VAR varsa -> 1 · aksi halde OLCULEMEDI varsa -> 2.
  `yok` kipinde bos anahtar listesi -> 2 (olculecek bir sey yok).

DISK (Okan kurali — makinede iz birakma): indirmeler `tempfile.mkdtemp` altina, her biri
hash'lendikten hemen sonra silinir; wrangler gunlugu de WRANGLER_LOG_PATH ile ayni gecici
dizine yonlendirilir; kosum sonunda gecici dizin butunuyle silinir (hata/kesintide de).

  python3 tools/r2-canli-dogrula.py stl --dizin /Users/okan/dev/pruvo/stl --paralel 6 --rapor r.txt
  python3 tools/r2-canli-dogrula.py stl --sil                       # yalniz ESIT olanlari sil
  python3 tools/r2-canli-dogrula.py yok --anahtar-dosyasi silinen.txt --kova pruvo-ozel
"""

import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS = os.path.dirname(os.path.abspath(__file__))
VARSAYILAN_KOVA = "pruvo-ozel"
NOT_FOUND_METNI = "The specified key does not exist."
INDIRME_TAMAM = "Download complete."
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

ESIT, FARKLI, YOK, OLCULEMEDI, HATALI_AD = "ESIT", "FARKLI", "YOK", "OLCULEMEDI", "HATALI_AD"
SILINDI_KANITLI, HALA_VAR = "SILINDI_KANITLI", "HALA_VAR"
STL_SINIFLAR = (ESIT, FARKLI, YOK, OLCULEMEDI, HATALI_AD)
YOK_SINIFLAR = (SILINDI_KANITLI, HALA_VAR, OLCULEMEDI)

# sonda() sonuclari
S_VAR, S_YOK, S_BELIRSIZ = "VAR", "YOK", "BELIRSIZ"


def _modul_yukle(ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(TOOLS, dosya))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sha1(yol):
    h = hashlib.sha1()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


class Wrangler:
    """`npx wrangler` cagrilari. Govdeyi gecici dizine indirir, olcer, HEMEN siler."""

    def __init__(self, kova, cwd, gecici, zaman_asimi):
        self.kova = kova
        self.cwd = cwd
        self.gecici = gecici
        self.zaman_asimi = zaman_asimi
        self._sayac = 0
        self._kilit = threading.Lock()
        self.ortam = dict(os.environ)
        # wrangler gunlugu ~/.wrangler/logs'a DEGIL gecici dizine (kosum sonu silinir).
        self.ortam["WRANGLER_LOG_PATH"] = os.path.join(gecici, "wrangler-log")

    def _kos(self, argv):
        try:
            p = subprocess.run(["npx", "wrangler"] + argv, cwd=self.cwd, capture_output=True,
                               text=True, timeout=self.zaman_asimi, env=self.ortam)
        except subprocess.TimeoutExpired:
            return None, "zaman asimi (%d sn)" % self.zaman_asimi
        except OSError as e:
            return None, "npx calismadi: %s" % e
        return p.returncode, _ANSI.sub("", (p.stdout or "") + (p.stderr or ""))

    def kova_acik_mi(self):
        """KOVA ON-KAPISI. (True, '') ya da (False, sebep). Olculdu: olmayan kovada
        `object get` de "key does not exist" basar — bu kapi olmadan kova adi hatasi
        TUM anahtarlari sahte "yok/silindi" yapardi."""
        rc, metin = self._kos(["r2", "bucket", "info", self.kova])
        if rc != 0:
            return False, "bucket info rc=%s: %s" % (rc, _ozet(metin))
        if not re.search(r"^name:\s*%s\s*$" % re.escape(self.kova), metin, re.M):
            return False, "bucket info ciktisinda 'name: %s' yok: %s" % (self.kova, _ozet(metin))
        return True, ""

    def sonda(self, anahtar):
        """(S_VAR, sha1, boyut) | (S_YOK, None, None) | (S_BELIRSIZ, None, sebep)."""
        with self._kilit:
            self._sayac += 1
            hedef = os.path.join(self.gecici, "g%07d.bin" % self._sayac)
        try:
            rc, metin = self._kos(["r2", "object", "get", self.kova + "/" + anahtar,
                                   "--remote", "--file", hedef])
            dolu = os.path.isfile(hedef) and os.path.getsize(hedef) > 0
            if rc == 0 and INDIRME_TAMAM in metin and NOT_FOUND_METNI not in metin:
                if not dolu:
                    # 0 bayt: wrangler hata halinde de 0 baytlik dosya olusturur -> kanit degil.
                    return S_BELIRSIZ, None, "rc=0 ama govde bos/yok"
                return S_VAR, _sha1(hedef), os.path.getsize(hedef)
            if rc == 1 and NOT_FOUND_METNI in metin and not dolu:
                return S_YOK, None, None
            return S_BELIRSIZ, None, "rc=%s: %s" % (rc, _ozet(metin))
        finally:
            if os.path.lexists(hedef):
                os.remove(hedef)


def _ozet(metin):
    satirlar = [s.strip() for s in (metin or "").splitlines() if s.strip()]
    hata = [s for s in satirlar if "ERROR" in s or "rror" in s or "failed" in s.lower()]
    return (" | ".join((hata or satirlar)[-2:]))[:240] or "(bos cikti)"


def _havuz(isler, fn, paralel, etiket):
    """isler listesini paralel isler; sonuclari ayni sirayla dondurur."""
    sonuc = [None] * len(isler)
    with ThreadPoolExecutor(max_workers=max(1, paralel)) as havuz:
        gel = {havuz.submit(fn, x): i for i, x in enumerate(isler)}
        bitti = 0
        for g in as_completed(gel):
            sonuc[gel[g]] = g.result()
            bitti += 1
            if bitti % 100 == 0 or bitti == len(isler):
                sys.stderr.write("%s ilerleme %d/%d\n" % (etiket, bitti, len(isler)))
    return sonuc


def _rapor_yaz(yol, siniflar, kayitlar):
    with open(yol, "w", encoding="utf-8") as f:
        for sinif in siniflar:
            secili = [k for k in kayitlar if k[0] == sinif]
            f.write("## %s (%d)\n" % (sinif, len(secili)))
            for k in secili:
                f.write("\t".join(str(x) for x in k[1:] if x not in (None, "")) + "\n")


def _rc(sayim, kirmizi):
    if any(sayim[s] for s in kirmizi):
        return 1
    if sayim[OLCULEMEDI]:
        return 2
    return 0


def _veri_kok():
    vk = _modul_yukle("veri_kok", "veri_kok.py")
    _kod, veri, _uyari = vk.cozumle(os.path.join(TOOLS, "r2-canli-dogrula.py"))
    return veri


def kip_stl(a, w):
    yuk = _modul_yukle("stl_r2_yukle", "stl-r2-yukle.py")
    veri = _veri_kok()
    # urun_idleri() modul REPO'sunu okur; veri koku (ana kopya) urunler.json'una yonlendir.
    yuk.REPO = veri
    idler = yuk.urun_idleri()
    kaynak_esle, kaynak_cakisan = yuk.kaynak_esleme_yukle(
        a.kaynaklar or os.path.join(veri, ".urun-kaynaklari.json"))
    manifest_n = len(yuk.manifest_oku(a.manifest or os.path.join(veri, ".stl-r2-manifest.json")))
    if not os.path.isdir(a.dizin):
        sys.exit("kaynak klasor yok: " + a.dizin)
    dosyalar = sorted(os.listdir(a.dizin))
    hedefler, hatali, cakisan = yuk.siniflandir(dosyalar, idler, kaynak_esle, kaynak_cakisan)

    # kayit = (sinif, yerel ad, r2 anahtari, yerel sha1, aciklama)
    kayitlar = [(HATALI_AD, ad, "", "", "esleme yok / anahtar reddi") for ad in hatali]
    kayitlar += [(HATALI_AD, ad, "", "", "cakisan kaynak-id") for ad in cakisan]

    kova_acik, sebep = w.kova_acik_mi()
    if not kova_acik:
        print("KOVA_KAPISI=KAPALI kova=%s sebep=%s — hicbir anahtar sorulmadi" % (w.kova, sebep))

    def isle(hedef):
        ad, anahtar = hedef
        yerel = os.path.join(a.dizin, ad)
        if not kova_acik:
            return (OLCULEMEDI, ad, anahtar, "", "kova on-kapisi kapali")
        try:
            y_sha, y_boyut = yuk.sha1_dosya(yerel), os.path.getsize(yerel)
        except OSError as e:
            return (OLCULEMEDI, ad, anahtar, "", "yerel okunamadi: %s" % e)
        durum, r_sha, r_boyut = w.sonda(anahtar)
        if durum == S_YOK:
            return (YOK, ad, anahtar, y_sha, "canli not-found")
        if durum != S_VAR:
            return (OLCULEMEDI, ad, anahtar, y_sha, r_boyut)
        esit = (r_sha == y_sha and r_boyut == y_boyut)
        if esit:
            return (ESIT, ad, anahtar, y_sha, "")
        return (FARKLI, ad, anahtar, y_sha,
                "yerel %s/%d r2 %s/%d" % (y_sha, y_boyut, r_sha, r_boyut))

    kayitlar += _havuz(hedefler, isle, a.paralel, "stl")
    sayim = {s: sum(1 for k in kayitlar if k[0] == s) for s in STL_SINIFLAR}
    toplam = len(hedefler) + len(hatali) + len(cakisan)

    sorunlu = [k for k in kayitlar if k[0] in (FARKLI, YOK, OLCULEMEDI)]
    for k in sorunlu[:20]:
        print("  %-10s %s -> %s %s" % (k[0], k[1], k[2], k[4]))
    if len(sorunlu) > 20:
        print("  ... (+%d satir daha; tam liste --rapor)" % (len(sorunlu) - 20))
    if a.rapor:
        _rapor_yaz(a.rapor, STL_SINIFLAR, kayitlar)

    print("R2_DOGRULA KIP=stl ESIT=%d FARKLI=%d YOK=%d OLCULEMEDI=%d HATALI_AD=%d TOPLAM=%d "
          "MANIFEST=%d" % (sayim[ESIT], sayim[FARKLI], sayim[YOK], sayim[OLCULEMEDI],
                           sayim[HATALI_AD], toplam, manifest_n))

    if a.sil:
        silinen, bayt = 0, 0
        for k in kayitlar:
            if k[0] != ESIT:
                continue
            yerel = os.path.join(a.dizin, k[1])
            try:
                # silmeden hemen once yerel govde yeniden olculur (kosum sirasinda degistiyse KALIR)
                if yuk.sha1_dosya(yerel) != k[3]:
                    continue
                boyut = os.path.getsize(yerel)
                os.remove(yerel)
            except OSError:
                continue
            silinen += 1
            bayt += boyut
        kalan = sum(1 for ad in os.listdir(a.dizin)
                    if os.path.splitext(ad)[1].lower() in yuk.UZANTILAR)
        print("SILINDI=%d GB=%.2f KALAN=%d" % (silinen, bayt / 1e9, kalan))

    return _rc(sayim, (FARKLI, YOK, HATALI_AD))


def kip_yok(a, w):
    yuk = _modul_yukle("stl_r2_yukle", "stl-r2-yukle.py")
    with open(a.anahtar_dosyasi, encoding="utf-8") as f:
        anahtarlar = [s.strip() for s in f if s.strip() and not s.strip().startswith("#")]

    kova_acik, sebep = w.kova_acik_mi()
    if not kova_acik:
        print("KOVA_KAPISI=KAPALI kova=%s sebep=%s — hicbir anahtar sorulmadi" % (w.kova, sebep))

    def isle(anahtar):
        if not kova_acik:
            return (OLCULEMEDI, anahtar, "kova on-kapisi kapali")
        try:
            if yuk.anahtar_normalize(anahtar) != anahtar:
                return (OLCULEMEDI, anahtar, "anahtar normal bicimde degil (sorulmadi)")
        except yuk.AnahtarReddi as e:
            return (OLCULEMEDI, anahtar, "anahtar kapisi reddi: %s" % e)
        durum, r_sha, ek = w.sonda(anahtar)
        if durum == S_YOK:
            return (SILINDI_KANITLI, anahtar, "")
        if durum == S_VAR:
            return (HALA_VAR, anahtar, "sha1=%s boyut=%d" % (r_sha, ek))
        return (OLCULEMEDI, anahtar, ek)

    kayitlar = _havuz(anahtarlar, isle, a.paralel, "yok")
    sayim = {s: sum(1 for k in kayitlar if k[0] == s) for s in YOK_SINIFLAR}
    for k in [k for k in kayitlar if k[0] != SILINDI_KANITLI][:20]:
        print("  %-15s %s %s" % k)
    if a.rapor:
        _rapor_yaz(a.rapor, YOK_SINIFLAR, kayitlar)
    print("R2_DOGRULA KIP=yok SILINDI_KANITLI=%d HALA_VAR=%d OLCULEMEDI=%d"
          % (sayim[SILINDI_KANITLI], sayim[HALA_VAR], sayim[OLCULEMEDI]))
    if not anahtarlar:
        print("anahtar listesi bos — olculecek bir sey yok")
        return 2
    return _rc(sayim, (HALA_VAR,))


def arg_ayristir(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    alt = ap.add_subparsers(dest="kip", required=True)
    ortak = argparse.ArgumentParser(add_help=False)
    ortak.add_argument("--kova", default=VARSAYILAN_KOVA)
    ortak.add_argument("--paralel", type=int, default=6)
    ortak.add_argument("--rapor", help="sinif basina anahtar listesi yazilacak dosya")
    ortak.add_argument("--zaman-asimi", dest="zaman_asimi", type=int, default=900,
                       help="get basina saniye (vars. 900; asilirsa OLCULEMEDI)")
    s = alt.add_parser("stl", parents=[ortak], help="yerel stl/ <-> R2 esitligi")
    s.add_argument("--dizin", default=None, help="yerel STL dizini (vars. <veri-koku>/stl)")
    s.add_argument("--sil", action="store_true",
                   help="YALNIZ bu kosumda ESIT cikan yerel dosyalari sil (vars. KAPALI)")
    s.add_argument("--kaynaklar", default=None, help="gizli kaynak kaydi (vars. veri koku)")
    s.add_argument("--manifest", default=None, help="yalniz bilgi icin sayilir (vars. veri koku)")
    y = alt.add_parser("yok", parents=[ortak], help="silme sonrasi canli not-found kaniti")
    y.add_argument("--anahtar-dosyasi", dest="anahtar_dosyasi", required=True)
    return ap.parse_args(argv)


def main(argv=None):
    a = arg_ayristir(argv)
    if a.kip == "stl" and not a.dizin:
        a.dizin = os.path.join(_veri_kok(), "stl")
    gecici = tempfile.mkdtemp(prefix="r2-canli-dogrula-")
    try:
        w = Wrangler(a.kova, _veri_kok(), gecici, a.zaman_asimi)
        rc = kip_stl(a, w) if a.kip == "stl" else kip_yok(a, w)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())

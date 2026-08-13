#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/katalog-alan-kapisi.py — katalog semasi + commit ani alan kapisi.

    python3 tools/katalog-alan-kapisi.py        # INDEX ekseni (TEK kip, varsayilan)

CIKIS KODLARI (fail-closed):  0 = YESIL · 1 = KIRMIZI (ihlal) · 2 = OLCULEMEDI.
OLCULEMEDI YESIL SAYILMAZ — kanca commit'i DURDURUR.

KATALOG GENELI EKSENI: index'teki HER kaydin HER alani, tools/arama.py icindeki
KATALOG_ALAN_TIPLERI semasindan dogrulanir. Kapsam elle sayilmaz; bilinmeyen alan
`TIP TANIMI YOK` diye KIRMIZI yanar. Bu eksen HEAD ile index ayni olsa bile kosar.

═══════════════════════════════════════════════════════════════════════════════
NEDEN VAR (OLCULDU 8 AGU 2026 — yayini 3,5+ saat kapatti)
═══════════════════════════════════════════════════════════════════════════════
Toplu ekleme yolu `urunler.json`a DOGRUDAN yaziyor ve `tools/duzelt.py`nin IKI
fail-closed kapisini birden ATLIYOR:
    _altkategori_ihlalleri()  ->  arama.altkategori_sebebi(kategori, altkategori)
    _uyum_ihlalleri()         ->  arama.uyum_sebebi(urun)   (K5 IKIZ tanimi dahil)
Bir partide 5 kayit bozuk main'e girdi (1 izinsiz `altkategori`, 5 elle yazilmis
`marka` ikizi). Ariza SAATLER SONRA CI'da gorundu ve deploy ATLANDI. Yani yazim
yolunda hicbir kol yoktu: kapilar YALNIZ duzelt.py'nin ICINDE ve YALNIZ CI'da
yasiyordu. Bu kapi ihlali COMMIT ANINDA durdurur -> repoya HIC girmez.

Ek olculen bosluk: `tools/kancalar/` altinda hicbir kancada `altkategori` gecmiyordu.

═══════════════════════════════════════════════════════════════════════════════
TEK KAYNAK — IKINCI TANIM YOK
═══════════════════════════════════════════════════════════════════════════════
Dogrulama YALNIZ `tools/arama.py`deki KANONIK fonksiyonlardan gelir:
    arama.altkategori_sebebi(kategori, altkategori)
    arama.uyum_sebebi(urun)
Izinli kume / sema / imza nobeti / K5 ikiz karsilastirmasi BURADA YENIDEN
YAZILMAZ. Ozellikle `marka` ile turetilenin karsilastirmasi AYRICA yapilmaz:
`uyum_sebebi` onu ZATEN icerir. Ikinci bir kopya sessizce ayrisir ve ayrisma
DAIMA gevsek yonde olur ([[ikiz-tanim-sessiz-ayrisma]]).

═══════════════════════════════════════════════════════════════════════════════
OLCUM EKSENI = INDEX (staged) — CALISMA AGACI DEGIL
═══════════════════════════════════════════════════════════════════════════════
Taban  : `git cat-file blob HEAD:urunler.json`
Yeni   : `git cat-file blob <index blob'u>`   (`git ls-files -s -- urunler.json`)

DEGISEN KAYIT = index'teki, KANONIK JSON GOVDESI HEAD'in govde kumesinde
BULUNMAYAN kayit. Bu tanim iki hali birden kapsar: (a) yeni id, (b) ayni id
farkli govde. Kaydin YERI degisip govdesi aynen kaldiysa DEGISMEMIS sayilir
(siralama commit'i bloklamaz).

🔴 TUZAK [[kanca-stage-disi-agaci-tarar]]: TUM calisma agaci / TUM katalog
YARGILANMAZ. Paylasilan checkout'ta baska bir mimarin YARIM partisi herkesin
commit'ini kilitlerdi. Katalog geneli eksen AYRI ve kalicidir:
`tools/altkategori-kapisi.py` + `tools/uyum-kapisi.py` (CI).

🔴 KAPSAM ile ON-ELEME AYNI EKSEN ([[kabul-araligi-karsilastirma-araligi]]):
"urunler.json degisti mi" sorusu da INDEX ekseninde sorulur (HEAD blob oid'i ile
index blob oid'i karsilastirilir). Kabukta `git diff --quiet HEAD` ile on-eleme
yapilsaydi CALISMA AGACI ekseni acilir ve iki eksen sessizce ayrisirdi:
calisma agacinda temiz ama index'te bozuk bir kayit ATLANIRDI.
ATLAMA SESSIZ DEGIL: nedeni her seferinde stderr'e BASILIR.

═══════════════════════════════════════════════════════════════════════════════
🔴 IKI AYRI GIT TUZAGI — IKISI AYRI AYRI OLCULUR (bkz. tools/katalog-alan-kapisi-test.py)
═══════════════════════════════════════════════════════════════════════════════
(1) DEPO KOKU `git rev-parse --show-toplevel` ILE COZULMEZ, `__file__`DAN TURER.
    Kanca ortami MUTLAK bir `GIT_DIR` ihrac eder ve `GIT_WORK_TREE` bostur; bu
    halde git depo KESFINI ATLAR ve CARI DIZINI agacin tepesi kabul eder. O
    yuzden `git -C <depo>/tools rev-parse --show-toplevel` linked worktree
    kancasinda `<depo>/tools` doner (YANLIS) — bu depoda olculdu ve kapinin
    KENDISINI atlatmayi normallestirdi ([[kanca-git-dir-kok-cozumu]]).
    ROOT = `__file__`in dizininin ust dizini: ortamdan BAGIMSIZ, daima dogru.
    Nobeti: IDDIA-KOK (gercek worktree + gercek kanca).

(2) AMA GIT CAGRILARININ ORTAMI TEMIZLENMEZ. `GIT_INDEX_FILE` commit'in FIILEN
    kullandigi index'i gosterir ve bu her zaman `$GIT_DIR/index` DEGILDIR:
    `git commit <yol>` ve `git commit -a` GECICI bir index kurar ve kancaya onu
    ihrac eder. Ortami temizleseydik kapi DISKTEKI index'i okur, commit ise
    BASKA bir agaci yazardi — yani kapi yanlis nesneyi yargilardi.
    Bu yuzden bu dosyada git baglam degiskenlerini silen bir kume YOKTUR
    (tools/git_ortami.py'nin scrub'i BILEREK kullanilmaz; o modul kok'u
    KESIFLE cozen kapilar icindir, bu kapi kok'u kesifle COZMEZ).
    Nobeti: IDDIA-INDEX (alternatif GIT_INDEX_FILE + ayirt edici kontrol).

═══════════════════════════════════════════════════════════════════════════════
GEVSETME YOK
═══════════════════════════════════════════════════════════════════════════════
Env bayragi YOK, istisna dosyasi YOK, muafiyet listesi YOK. Bilincli atlama
zaten `git commit --no-verify`dir; kapinin KENDISI delik acmaz.
"""
import importlib.util
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True  # mutasyon kopyalari __pycache__ birakmasin

RC_YESIL = 0
RC_KIRMIZI = 1
RC_OLCULEMEDI = 2

DOSYA = "urunler.json"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAMA_YOLU = os.path.join(ROOT, "tools", "arama.py")


class Olculemedi(Exception):
    """Olcum yapilamadi -> YESIL SAYILMAZ (rc 2)."""


def _yaz(satir=""):
    sys.stderr.write(satir.rstrip("\n") + "\n")


def _git_metin(*args):
    """Kucuk ciktili git cagrisi. ORTAM TEMIZLENMEZ (bkz. modul docstring'i (2))."""
    try:
        return subprocess.run(["git", "-C", ROOT, *args], capture_output=True,
                              text=True, errors="replace")
    except OSError as e:
        raise Olculemedi("git calistirilamadi (%s: %s)" % (type(e).__name__, e))


def _git_bayt(*args):
    """Blob okuyan git cagrisi (ikili). ORTAM TEMIZLENMEZ."""
    try:
        return subprocess.run(["git", "-C", ROOT, *args], capture_output=True)
    except OSError as e:
        raise Olculemedi("git calistirilamadi (%s: %s)" % (type(e).__name__, e))


def arama_yukle():
    """KANONIK dogrulama modulu. Yuklenemezse OLCULEMEDI — sessiz gecis YOK."""
    if not os.path.exists(ARAMA_YOLU):
        raise Olculemedi("tools/arama.py YOK -> kanonik dogrulama kaynagi kayip")
    try:
        spec = importlib.util.spec_from_file_location("arama", ARAMA_YOLU)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        raise Olculemedi("tools/arama.py yuklenemedi (%s: %s)" % (type(e).__name__, e))
    for ad in ("altkategori_sebebi", "uyum_sebebi", "katalog_tip_ihlalleri",
               "KATALOG_ALAN_TIPLERI"):
        if not hasattr(mod, ad):
            raise Olculemedi("arama.%s YOK -> sozlesme degismis (fail-closed)" % ad)
    return mod


def _blob_oid(*args):
    """`git rev-parse --verify --quiet <hedef>` -> oid ya da None."""
    p = _git_metin("rev-parse", "--verify", "--quiet", *args)
    if p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip()
    return None


def index_oid():
    """urunler.json'un INDEX'teki blob oid'i; None = index'te YOK."""
    p = _git_metin("ls-files", "-s", "--", DOSYA)
    if p.returncode != 0:
        raise Olculemedi("`git ls-files -s -- %s` rc=%d: %s"
                         % (DOSYA, p.returncode, p.stderr.strip()[:200]))
    satir = p.stdout.strip()
    if not satir:
        return None
    parca = satir.split()
    if len(parca) < 2:
        raise Olculemedi("`git ls-files -s` ciktisi ayristirilamadi: %r" % satir[:120])
    return parca[1]


def kayitlar(oid, etiket):
    """Blob oid'inden kayit listesi. Bozuk JSON / okunamayan blob -> OLCULEMEDI."""
    p = _git_bayt("cat-file", "blob", oid)
    if p.returncode != 0:
        raise Olculemedi("%s blob'u okunamadi (oid=%s)" % (etiket, oid[:12]))
    try:
        veri = json.loads(p.stdout.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise Olculemedi("%s icindeki %s ayristirilamadi (%s: %s)"
                         % (etiket, DOSYA, type(e).__name__, str(e)[:200]))
    if not isinstance(veri, list):
        raise Olculemedi("%s icindeki %s bir DIZI degil (%s)"
                         % (etiket, DOSYA, type(veri).__name__))
    return veri


def _govde(u):
    return json.dumps(u, sort_keys=True, ensure_ascii=False)


def degisen_kayitlar(index_kayit, head_kayit):
    """INDEX ekseninde DEGISEN kayitlar (yeni id VEYA govdesi farkli id)."""
    taban = {_govde(u) for u in head_kayit}
    return [u for u in index_kayit if _govde(u) not in taban]


def ihlalleri_olc(arama, degisenler):
    """[(id, alan, mevcut_deger, kanonik_sebep), ...] — bos liste = TEMIZ.

    IKI EKSEN AYRI AYRI olculur ve ikisi de HER kayitta kosar (kisa devre YOK):
    tek bir "ikisi birden bozuk" vaka iki ekseni birden olcmez, katmanlarin
    VEYA'sini olcer ([[beyan-edilmis-survivor]]).
    """
    ihlaller = []
    for u in degisenler:
        if not isinstance(u, dict):
            ihlaller.append((None, "kayit", u,
                             "kayit bir JSON OBJESI degil (%s)" % type(u).__name__))
            continue
        uid = u.get("id")
        try:
            alt_sebep = arama.altkategori_sebebi(u.get("kategori"), u.get("altkategori"))
        except Exception as e:
            raise Olculemedi("arama.altkategori_sebebi cokti (id=%r, %s: %s)"
                             % (uid, type(e).__name__, e))
        if alt_sebep:
            ihlaller.append((uid, "altkategori", u.get("altkategori"), alt_sebep))
        try:
            uyum_sebep = arama.uyum_sebebi(u)
        except Exception as e:
            raise Olculemedi("arama.uyum_sebebi cokti (id=%r, %s: %s)"
                             % (uid, type(e).__name__, e))
        if uyum_sebep:
            ihlaller.append((uid, "uyum/marka", u.get("marka"), uyum_sebep))
    return ihlaller


def rapor(ihlaller, degisen_sayisi, tip_ihlali_sayisi):
    """duzelt.py'nin _altkategori_rapor / _uyum_rapor tonu (id + alan + sebep + yol)."""
    satirlar = ["HATA: KATALOG ALAN KAPISI — COMMIT/YAYIN REDDEDILDI (index ekseni; "
                "degisen kayit: %d, tip sapmasi: %d, toplam ihlal: %d)."
                % (degisen_sayisi, tip_ihlali_sayisi, len(ihlaller))]
    for uid, alan, deger, sebep in ihlaller:
        satirlar.append("  - id=%s [%s] mevcut=%r" % (uid, alan, deger))
        satirlar.append("      -> %s" % sebep)
    satirlar.append("  altkategori/uyum alanlarinin TEK yetkili yazma yolu tools/duzelt.py'dir; kural "
                    "tools/arama.py'de TEK kaynaktir (elle sema kopyalanmaz):")
    satirlar.append("      python3 tools/duzelt.py <id> --alan altkategori --deger \"...\"")
    satirlar.append("      python3 tools/duzelt.py <id> --alan-sil altkategori")
    satirlar.append("      python3 tools/duzelt.py <id> --alan uyum --deger '[{\"marka\": \"...\"}]'")
    satirlar.append("  🔴 `marka` ELLE YAZILMAZ: `uyum` doluyken duzelt.py onu AYNI islemde "
                    "arama.marka_uyumdan_turet ile KENDISI yazar.")
    satirlar.append("  Alan tiplerinin tek kaynagi arama.KATALOG_ALAN_TIPLERI; `fiyat` "
                    "JSON string olmali; beklenen ornek='430 TL' (parametrik seri icin "
                    "bos string gecerlidir).")
    satirlar.append("  Izinli kumeler: arama.ALTKATEGORI_IZINLI · arama.UYUM_MARKA_IZINLI "
                    "(genisletmek MIMAR karari).")
    satirlar.append("  Kapiyi BILINCLI atlamak: git commit --no-verify (kapinin kendi "
                    "muafiyet listesi YOKTUR).")
    return "\n".join(satirlar)


def olc():
    """Hukum: (rc, ozet_satiri). Fail-closed — her olculemez hal Olculemedi atar."""
    arama = arama_yukle()

    head_var = _blob_oid("HEAD") is not None
    ind_oid = index_oid()
    if ind_oid is None:
        raise Olculemedi("%s INDEX'te YOK (izlenmiyor ya da silinmesi stage'lenmis)"
                         % DOSYA)

    head_oid = _blob_oid("HEAD:" + DOSYA) if head_var else None
    index_kayit = kayitlar(ind_oid, "INDEX")
    tip_ihlalleri = arama.katalog_tip_ihlalleri(index_kayit)

    if head_oid == ind_oid:
        if tip_ihlalleri:
            _yaz(rapor(tip_ihlalleri, 0, len(tip_ihlalleri)))
            return RC_KIRMIZI, ("KIRMIZI: katalog=%d kayit, tip sapmasi=%d; "
                                "altkategori/uyum icin degisen kayit=0."
                                % (len(index_kayit), len(tip_ihlalleri)))
        return RC_YESIL, ("ATLANDI: %s INDEX'te HEAD'e gore DEGISMEDI; katalog "
                          "genelinde %d kayit/%d alan tipi dogrulandi, sapma YOK."
                          % (DOSYA, len(index_kayit), len(arama.KATALOG_ALAN_TIPLERI)))

    head_kayit = kayitlar(head_oid, "HEAD") if head_oid else []
    if head_oid is None:
        _yaz("-- HEAD'de %s YOK (ilk commit ya da yeni dosya): index'teki TUM kayitlar "
             "YENI sayilir." % DOSYA)

    degisenler = degisen_kayitlar(index_kayit, head_kayit)
    if not degisenler:
        if tip_ihlalleri:
            _yaz(rapor(tip_ihlalleri, 0, len(tip_ihlalleri)))
            return RC_KIRMIZI, ("KIRMIZI: katalog=%d kayit, tip sapmasi=%d; "
                                "DEGISEN KAYIT yok (yalniz siralama/bicim)."
                                % (len(index_kayit), len(tip_ihlalleri)))
        return RC_YESIL, ("ATLANDI: %s degisti ama DEGISEN KAYIT yok (yalniz siralama/"
                          "bicim); katalog genelinde %d kayit/%d alan tipi dogrulandi, "
                          "sapma YOK."
                          % (DOSYA, len(index_kayit), len(arama.KATALOG_ALAN_TIPLERI)))

    alan_ihlalleri = ihlalleri_olc(arama, degisenler)
    ihlaller = tip_ihlalleri + alan_ihlalleri
    if ihlaller:
        _yaz(rapor(ihlaller, len(degisenler), len(tip_ihlalleri)))
        return RC_KIRMIZI, ("KIRMIZI: katalog=%d kayit, tip sapmasi=%d; "
                            "%d degisen kayitta altkategori/uyum ihlali=%d."
                            % (len(index_kayit), len(tip_ihlalleri), len(degisenler),
                               len(alan_ihlalleri)))
    return RC_YESIL, ("YESIL: katalog genelinde %d kayit/%d alan tipi + %d degisen "
                      "kayitta altkategori/uyum/marka dogrulandi; ihlal YOK."
                      % (len(index_kayit), len(arama.KATALOG_ALAN_TIPLERI),
                         len(degisenler)))


def main(argv):
    if len(argv) > 1:
        _yaz("KATALOG ALAN KAPISI — TEK kip vardir (index ekseni), arguman almaz; "
             "verilen: %r" % (argv[1:],))
        return RC_OLCULEMEDI
    # Kok satiri HER KOSUMDA, her seyden ONCE basilir: kok nobeti (IDDIA-KOK) bunu okur
    # ve import/git patlasa bile olculebilir olmali.
    _yaz("KATALOG ALAN KAPISI — olculen agac = %s" % ROOT)
    try:
        rc, ozet = olc()
    except Olculemedi as e:
        _yaz("!! OLCULEMEDI (rc=%d, YESIL SAYILMAZ): %s" % (RC_OLCULEMEDI, e))
        return RC_OLCULEMEDI
    _yaz(ozet)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))

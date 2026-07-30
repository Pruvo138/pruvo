#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gorsel_koken.py — GORSEL-KOKEN DOGRULAMASI, GERCEK YAYIM YOLUNDA.

NE KORUR
--------
Bir FIGUR/ozgun urunun (kategori == "Skan Art") SAYFA GORSELLERI, o gorsellerin
GERCEK URUN STL'inden turedigine dair KOKEN KAYDI olmadan urunler.json'a GIREMEZ.
2026-07-28'de iki boga figurunun sayfa gorselleri gercek STL yerine metinden
uretildi ve urunle ortusmedi; hata SESSIZ (kimse fark etmez, musteri yanlis
gorselle siparis verir) ve LISANS/TELIF yuzu var (depo PUBLIC).

NEDEN BU DOSYA VAR (U2 — DEVAM.md madde 10)
-------------------------------------------
Ilk nobetci `pruvo-jenerator/.claude/gorsel-koken-kapisi.py` idi: bir Claude Code
PreToolUse HOOK'u, matcher `Edit|Write|MultiEdit`, YALNIZ KaaN'in oturum
ayarlarinda kayitli (`pruvo-jenerator/.claude/settings.json:75`). Yani:
  * urunler.json'a python ile yazan HICBIR yol (urun-ekle.py merge_safe,
    duzelt.py, printables/makerworld/cgt-ekle) kapiyi TETIKLEMIYORDU;
  * pruvo deposunun kendi `.claude/settings.json`'inda kayit YOK -> KraL/MaCiT
    oturumunda Edit araciyla yazim bile kapisiz;
  * hook yalnizca "manifest var mi + dosyalar diskte var mi" diye bakiyordu ->
    1 BAYTLIK bir "x" dosyasi gecerli `taban_render` sayiliyordu.
Bu modul dogrulamayi ARACIN kendisinden alip URUNUN CANLIYA CIKTIGI YAZIM
NOKTASINA (flock altinda, _atomic_write'tan HEMEN ONCE) tasir.

TETIK (dar tutulur; yanlis-pozitif MaCiT'in gunluk parti zincirini durdurur)
---------------------------------------------------------------------------
Yeni durumda kategori == "Skan Art" VE gorseller BOS DEGIL olan bir urun icin,
su UC durumdan biri varsa tetiklenir:
  1. urun katalogda YOK (yeni ekleme),
  2. `gorseller` listesi eskisinden FARKLI (gorsel degisimi),
  3. urun eskiden Skan Art DEGILDI (kategori bu yazimda Skan Art'a cevrildi).
(3) hook'ta YOKTU: kategoriyi Skan Art'a cevirmek, gorsellere hic dokunmadan
figur sayfa gorseli yayinlamanin sessiz yoluydu.
DEGISMEYEN kayitlar HIC degerlendirilmez -> bugun canli olan 14993 kaydin hicbiri
kirmizi yanmaz (olculdu; `--denetim` ile tekrar uretilebilir).

FAIL YONU: tetik yakalandiysa FAIL-CLOSED (eksik/supheli manifest -> YAZIM YOK,
istisna). Tetik yoksa dokunmaz. Modul yuklenemezse cagiran betik acilista
COKER (sessiz fail-open yok) — bkz urun-ekle.py / duzelt.py import blogu.

MANIFEST (tek kaynak; semantigi KaaN'in duzlemi)
------------------------------------------------
  <koken-dizini>/<urun-id>.json
  { "kaynak_stl": "/…/gercek-urun.stl",
    "kaynak_stl_sha256": "<istege bagli; verilirse DOGRULANIR>",
    "gorseller": [ { "dosya": "<yayinlanan R2 anahtari / dosya adi / tam URL>",
                     "taban_render": "/…/render-p1.png",
                     "sha256": "<istege bagli; verilirse taban_render icin DOGRULANIR>" } ] }
Koken dizini arama sirasi: $GORSEL_KOKEN_DIR -> <kok>/urun-gorsel-koken ->
<kok>/../pruvo-jenerator/urun-gorsel-koken (manifestler KaaN'in deposunda yasar).

BEYAN — BU KAPININ KAPATMADIGI YOLLAR (ölçüldü, bilerek acik birakildi)
-----------------------------------------------------------------------
  * `tools/printables-ekle.py:213`, `tools/makerworld-ekle.py:208`,
    `tools/cgt-ekle.py:204` — ayni `merge_safe` deseni, KAPISIZ. Bu is emrinin
    kapsami disindaydilar (MaCiT/platform betikleri). Baglama: bu modulu import
    edip merge_safe icinde `zorla(...)` cagirmak — urun-ekle.py ile birebir ayni
    iki satir. Bugun gercek risk DUSUK: uc betik de platform kategorisi uretir,
    "Skan Art" uretmez.
  * `tools/urunler-guard.py:202` — yalnizca HEAD'e GERI ALIR (yeni icerik
    yayinlamaz), kapiya ihtiyaci yok.
  * Claude `Edit|Write|MultiEdit` araciyla dogrudan urunler.json yazimi — bu
    modul python yolunu korur; arac yolunu KaaN'in hook'u korur (yalniz onun
    oturumunda). pruvo `.claude/settings.json`'a hook eklemek KraL/mimar karari.
  * R2'ye YUKLENEN BAYTIN taban_render ile hash-esitligi DOGRULANMAZ: yayinlanan
    bayt R2'de yasar, yerelde yoktur; ag'a cikmadan kanitlanamaz. Bu modul
    manifest<->DISK kanitini baglar (STL gercekten STL mi, render gercekten
    gorsel mi, beyan edilen sha256 tutuyor mu). Tam bayt baglama ancak yukleme
    aninda (r2-upload) yapilabilir — ayri kalem.
"""
import hashlib
import json
import os

KATEGORI = "Skan Art"

# 1 BAYTLIK "x" dosyasi hook'ta gecerli taban_render sayiliyordu; gercek bir STL
# render'i asla bu kadar kucuk olmaz.
ASGARI_RENDER_BAYT = 1024
ASGARI_STL_BAYT = 134          # binary STL: 80 baslik + 4 sayac + en az 1 ucgen (50)
_OKU_BAYT = 8192

_GORSEL_SIHIR = (
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
    (b"II*\x00", "TIFF"),
    (b"MM\x00*", "TIFF"),
)


class KokenIhlali(Exception):
    """Tetik yakalandi ama koken kaniti eksik/supheli -> YAZIM YAPILMAZ."""

    def __init__(self, ihlaller, kaynak=""):
        self.ihlaller = list(ihlaller)
        self.kaynak = kaynak
        Exception.__init__(self, rapor_metni(self.ihlaller, kaynak))


# --------------------------------------------------------------- yardimcilar
def harita(urunler):
    """[urun, ...] -> {id: urun-KOPYASI} (id'siz/gecersiz kayitlar atlanir).

    Her kayit SIG kopyalanir: cagiran "yazim oncesi" haritayi alip sonra ayni liste
    uzerinde alan atamasi yapabilsin diye. Referans dondurseydik eski==yeni olur,
    tetik (2)/(3) SESSIZCE hic ateslemezdi.
    """
    h = {}
    for p in urunler or []:
        if isinstance(p, dict) and isinstance(p.get("id"), str) and p["id"]:
            h.setdefault(p["id"], dict(p))
    return h


def manifest_dizinleri(kok):
    """Koken manifestlerinin ARANDIGI dizinler, oncelik sirasiyla."""
    adaylar = []
    env = os.environ.get("GORSEL_KOKEN_DIR")
    if isinstance(env, str) and env.strip():
        adaylar.append(os.path.normpath(env.strip()))
    kok = os.path.normpath(kok)
    adaylar.append(os.path.join(kok, "urun-gorsel-koken"))
    # Manifestler KaaN'in deposunda (ozgun urun duzlemi) yasar.
    adaylar.append(os.path.join(os.path.dirname(kok), "pruvo-jenerator",
                                "urun-gorsel-koken"))
    teklesmis = []
    for a in adaylar:
        if a not in teklesmis:
            teklesmis.append(a)
    return teklesmis


def manifest_dizini(kok):
    for d in manifest_dizinleri(kok):
        if os.path.isdir(d):
            return d
    return None


def _coz(yol, kok):
    if not isinstance(yol, str) or not yol.strip():
        return None
    y = os.path.expanduser(yol.strip())
    if not os.path.isabs(y):
        y = os.path.join(kok, y)
    return os.path.normpath(y)


def _sha256(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def _stl_gecerli(yol):
    """(ok, sebep) — dosya GERCEKTEN bir STL mi (binary sayac tutarli ya da ASCII
    facet/vertex tasiyor). Yeniden adlandirilmis bos/sahte dosya gecmesin."""
    try:
        boyut = os.path.getsize(yol)
    except OSError as e:
        return False, "okunamadi (%s)" % str(e)[:60]
    if boyut < ASGARI_STL_BAYT:
        return False, "%d bayt — gecerli bir STL olamaz (asgari %d)" % (boyut, ASGARI_STL_BAYT)
    try:
        with open(yol, "rb") as f:
            bas = f.read(_OKU_BAYT)
    except OSError as e:
        return False, "okunamadi (%s)" % str(e)[:60]
    if len(bas) >= 84:
        n = int.from_bytes(bas[80:84], "little")
        if n > 0 and 84 + 50 * n == boyut:
            return True, "binary STL, %d ucgen" % n
    dusuk = bas.lower()
    if dusuk.lstrip().startswith(b"solid") and b"facet" in dusuk and b"vertex" in dusuk:
        return True, "ASCII STL"
    return False, "ne binary (ucgen sayaci boyutla tutmuyor) ne ASCII STL (facet/vertex yok)"


def _gorsel_gecerli(yol):
    """(ok, sebep) — dosya GERCEKTEN bir raster gorsel mi + anlamli buyuklukte mi."""
    try:
        boyut = os.path.getsize(yol)
    except OSError as e:
        return False, "okunamadi (%s)" % str(e)[:60]
    if boyut < ASGARI_RENDER_BAYT:
        return False, ("%d bayt — gercek bir STL render'i degil (asgari %d; "
                       "1 baytlik yer tutucu bu kapidan gecemez)"
                       % (boyut, ASGARI_RENDER_BAYT))
    try:
        with open(yol, "rb") as f:
            bas = f.read(16)
    except OSError as e:
        return False, "okunamadi (%s)" % str(e)[:60]
    for sihir, ad in _GORSEL_SIHIR:
        if bas.startswith(sihir):
            return True, ad
    if bas.startswith(b"RIFF") and bas[8:12] == b"WEBP":
        return True, "WEBP"
    return False, "raster gorsel imzasi yok (PNG/JPEG/GIF/TIFF/WEBP degil)"


def _kapsayan(url, manifest_gorseller):
    """Yayinlanan gorsel URL'ine karsilik gelen manifest girisi (yoksa None).

    Esleme: TAM esitlik | '/'+dosya ile bitme | basename esitligi. Hook'taki
    ciplak `url.endswith(dosya)` KALDIRILDI: "1.jpg" gibi bir manifest girisi
    "…-g11.jpg" gibi ALAKASIZ bir URL'i kapsiyor gorunuyordu.
    """
    if not isinstance(url, str) or not url:
        return None
    ub = os.path.basename(url.rstrip("/"))
    for mg in manifest_gorseller:
        if not isinstance(mg, dict):
            continue
        dosya = mg.get("dosya")
        if not isinstance(dosya, str) or not dosya.strip():
            continue
        dosya = dosya.strip()
        if url == dosya or url.endswith("/" + dosya.lstrip("/")):
            return mg
        if ub and os.path.basename(dosya.rstrip("/")) == ub:
            return mg
    return None


# ------------------------------------------------------------------- tetik
def tetikleyenler(eski, yeni):
    """{id:urun} eski/yeni -> koken kaniti GEREKEN urun id'leri (sirali)."""
    tetik = []
    for pid, u in (yeni or {}).items():
        if not isinstance(u, dict) or u.get("kategori") != KATEGORI:
            continue
        g = u.get("gorseller")
        if not g:
            continue
        e = (eski or {}).get(pid)
        if not isinstance(e, dict):
            tetik.append(pid)                     # 1. yeni urun
        elif e.get("gorseller") != g:
            tetik.append(pid)                     # 2. gorseller degisti
        elif e.get("kategori") != KATEGORI:
            tetik.append(pid)                     # 3. kategori Skan Art'a cevrildi
    return sorted(tetik)


# -------------------------------------------------------------- dogrulama
def manifest_dogrula(pid, gorseller, kok):
    """(sebep, kanit) — sebep None ise GECER; degilse BLOCK gerekcesi."""
    dizin = manifest_dizini(kok)
    if dizin is None:
        return ("'%s': koken manifest DIZINI bulunamadi (aranan: %s)"
                % (pid, " | ".join(manifest_dizinleri(kok)))), []
    yol = os.path.join(dizin, pid + ".json")
    if not os.path.isfile(yol):
        return "'%s' urunu icin koken manifesti YOK (%s)" % (pid, yol), []
    try:
        with open(yol, encoding="utf-8") as f:
            man = json.load(f)
    except (OSError, ValueError) as e:
        return "'%s' manifesti okunamadi/parse edilemiyor (%s): %s" % (pid, yol, str(e)[:80]), []
    if not isinstance(man, dict):
        return "'%s' manifesti gecersiz (ust seviye JSON nesnesi degil)" % pid, []

    kanit = []
    stl = _coz(man.get("kaynak_stl"), kok)
    if stl is None:
        return "'%s' manifestinde 'kaynak_stl' alani yok/gecersiz" % pid, kanit
    if not os.path.isfile(stl):
        return "'%s' kaynak_stl diskte YOK (%s)" % (pid, stl), kanit
    ok, sebep = _stl_gecerli(stl)
    if not ok:
        return "'%s' kaynak_stl gecerli bir STL DEGIL (%s): %s" % (pid, stl, sebep), kanit
    kanit.append("kaynak_stl %s (%s)" % (os.path.basename(stl), sebep))
    beyan = man.get("kaynak_stl_sha256")
    if isinstance(beyan, str) and beyan.strip():
        gercek = _sha256(stl)
        if gercek.lower() != beyan.strip().lower():
            return ("'%s' kaynak_stl SHA256 manifestteki beyanla TUTMUYOR "
                    "(beyan %s… / disk %s…)" % (pid, beyan.strip()[:12], gercek[:12])), kanit
        kanit.append("kaynak_stl sha256 DOGRULANDI")
    else:
        kanit.append("kaynak_stl sha256 BEYAN EDILMEMIS (yalniz varlik+bicim dogrulandi)")

    man_g = man.get("gorseller")
    if not isinstance(man_g, list) or not man_g:
        return "'%s' manifestinde 'gorseller' listesi yok/bos" % pid, kanit

    for url in (gorseller or []):
        eslesme = _kapsayan(url, man_g)
        if eslesme is None:
            return ("'%s' urununde yayinlanan bir gorsel manifestte KAPSANMIYOR (%s)"
                    % (pid, str(url)[:120])), kanit
        tr = _coz(eslesme.get("taban_render"), kok)
        if tr is None:
            return ("'%s' gorseli icin 'taban_render' alani yok/gecersiz (%s)"
                    % (pid, str(url)[:120])), kanit
        if not os.path.isfile(tr):
            return ("'%s' gorseli icin taban_render (STL render) diskte YOK (%s)"
                    % (pid, tr)), kanit
        ok, sebep = _gorsel_gecerli(tr)
        if not ok:
            return ("'%s' gorseli icin taban_render gecerli bir gorsel DEGIL (%s): %s"
                    % (pid, tr, sebep)), kanit
        beyan = eslesme.get("sha256")
        if isinstance(beyan, str) and beyan.strip():
            gercek = _sha256(tr)
            if gercek.lower() != beyan.strip().lower():
                return ("'%s' gorseli icin taban_render SHA256 beyanla TUTMUYOR (%s: "
                        "beyan %s… / disk %s…)"
                        % (pid, os.path.basename(tr), beyan.strip()[:12], gercek[:12])), kanit
            kanit.append("%s -> %s (%s, sha256 DOGRULANDI)"
                         % (os.path.basename(str(url)), os.path.basename(tr), sebep))
        else:
            kanit.append("%s -> %s (%s, sha256 beyan edilmemis)"
                         % (os.path.basename(str(url)), os.path.basename(tr), sebep))
    return None, kanit


def denetle(eski, yeni, kok):
    """-> [(pid, sebep), ...] · bos liste = GECER."""
    ihlaller = []
    for pid in tetikleyenler(eski, yeni):
        sebep, _kanit = manifest_dogrula(pid, (yeni.get(pid) or {}).get("gorseller"), kok)
        if sebep is not None:
            ihlaller.append((pid, sebep))
    return ihlaller


def rapor_metni(ihlaller, kaynak=""):
    satirlar = ["🔴 GORSEL-KOKEN KAPISI — YAZIM YAPILMADI%s."
                % (" (%s)" % kaynak if kaynak else "")]
    satirlar.append("   Figur/ozgun urun (kategori '%s') sayfa gorseli GERCEK STL'den "
                    "turemeli (STL -> render -> istenirse restyle);" % KATEGORI)
    satirlar.append("   metinden cipasiz gorsel yayinlanamaz. Eksik koken kaniti:")
    for pid, sebep in ihlaller:
        satirlar.append("     - %s" % sebep)
    satirlar.append("   Manifest sablonu: <koken-dizini>/<urun-id>.json")
    satirlar.append('     {"kaynak_stl": "/…/gercek-urun.stl", "gorseller": '
                    '[{"dosya": "<r2-anahtar|dosya-adi|URL>", '
                    '"taban_render": "/…/render-p1.png", "sha256": "<istege bagli>"}]}')
    return "\n".join(satirlar)


def zorla(eski, yeni, kok, kaynak=""):
    """Ihlal varsa KokenIhlali firlatir (cagiran HICBIR SEY yazmadan cikar)."""
    ihlaller = denetle(eski, yeni, kok)
    if ihlaller:
        raise KokenIhlali(ihlaller, kaynak)
    return True


# ------------------------------------------------------------------- CLI
def _denetim(kok):
    """Gercek katalog uzerinde iki olcum:
      (1) DEGISIKLIK YOK kosumu -> tetik 0, kirmizi 0 (MaCiT'in gunluk zinciri).
      (2) HER kayit yeniden yayinlanacakmis gibi -> koken kaniti olmayanlar
          (latent kirmizi; bugun canliya dokunmaz, gorseli yeniden yayinlanirsa yanar).
    """
    urunler_yol = os.path.join(kok, "urunler.json")
    with open(urunler_yol, encoding="utf-8") as f:
        urunler = json.load(f)
    h = harita(urunler)
    print("katalog: %s" % urunler_yol)
    print("kayit  : %d" % len(urunler))
    print("koken dizini aranan sirasiyla:")
    for d in manifest_dizinleri(kok):
        print("   %-4s %s" % ("VAR" if os.path.isdir(d) else "yok", d))

    print("\n(1) DEGISIKLIK YOK kosumu (eski == yeni; gercek yayim yolunun taban durumu)")
    tetik = tetikleyenler(h, h)
    ihlal = denetle(h, h, kok)
    print("    tetiklenen: %d | KIRMIZI: %d" % (len(tetik), len(ihlal)))

    print("\n(2) HER kayit YENIDEN YAYINLANIYOR kosumu (eski = bos katalog)")
    tetik2 = tetikleyenler({}, h)
    print("    tetiklenen: %d (kategori '%s' + gorselli)" % (len(tetik2), KATEGORI))
    kirmizi = []
    for pid in tetik2:
        sebep, kanit = manifest_dogrula(pid, h[pid].get("gorseller"), kok)
        if sebep is None:
            print("    YESIL  %s" % pid)
            for k in kanit:
                print("             %s" % k)
        else:
            kirmizi.append((pid, sebep))
            print("    KIRMIZI %s" % pid)
            print("             %s" % sebep)
    print("\n    latent KIRMIZI: %d / %d" % (len(kirmizi), len(tetik2)))
    kats = {}
    for p in urunler:
        kats[p.get("kategori")] = kats.get(p.get("kategori"), 0) + 1
    disi = sum(v for k, v in kats.items() if k != KATEGORI)
    print("    kapsam disi (tetiklenmeyen) kayit: %d" % disi)
    return 0


if __name__ == "__main__":
    import sys
    _kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--kok" in sys.argv:
        _kok = os.path.abspath(sys.argv[sys.argv.index("--kok") + 1])
    if "--denetim" in sys.argv:
        sys.exit(_denetim(_kok))
    print(__doc__)
    print("Kullanim: python3 tools/gorsel_koken.py --denetim [--kok <depo>]")

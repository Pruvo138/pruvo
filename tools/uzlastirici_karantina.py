#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KARANTINA — D1 uzlastiricisinin SILME kolunu IKI GOZLEME yayan hakem.

NEDEN VAR (OLCULDU, 11 Agu 2026 — kosum 31532464176, head c8b0451e)
====================================================================
Uzlastirici agaci uzak main ucuna tazeledi (25.827 urun), D1'de 25.864 satir gordu,
aradaki **37 satiri "FAZLA" sayip SILDI** ve silmeyi geri-okumayla dogruladi:

    hash UYUSMAZ: 0 | D1'de EKSIK: 0 | D1'de FAZLA: 37
    silinen: 37
    GERI-OKUMA DOGRULANDI: 37 satirin ... silinmesi D1'de teyit edildi

Silinen 37 satir COP DEGILDI: eszamanli bir urun partisinin D1'e YAZDIGI mesru
satirlardi; o partinin git push'u henuz uca inmemisti. Uzlastirici katalogun
ILERISINI "sapma" sanip geri aldi. Ayni desen 31502177931'de de gorulmustu
(`FAZLA: 41` -> uc tazelenince 0), yani "FAZLA" olcumu DUZENLI olarak gecici bir
YARIS PENCERESINI olcuyor.

`d1-sync.py --bayatlik` kapisi DOGRU calisti ama YANLIS SORUYU sordu: agacin git'e
gore bayatligini olcer; buradaki hal `D1'in git'ten ILERI olmasi`dir ve o yon
kapinin ekseninde YOKTUR.

ASIMETRI — iki yonun riski AYNI DEGIL
=====================================
  EKSIK (D1'de yok, agacta var) -> EKLEME. Yanlissa fazladan satir; Ege gosterir; zarar KUCUK.
  FAZLA (D1'de var, agacta yok) -> SILME.  Yanlissa canli katalog satiri GIDER; Ege GOREMEZ.
Emniyet agi bu iki yonu ayni cesaretle isliyordu. Bu modul YALNIZ silme kolunu tutar.

KURAL — KARANTINA (silmeyi KALDIRMAK degil)
===========================================
Silme kolunu tamamen kapatmak COZUM DEGIL: gercek oksuz satirlar birikirse D1 ile
katalog KALICI ayrisir. Bu yuzden silme IKI GOZLEME yayilir:

  1. ILK GOZLEM  -> SILME YOK. id karantinaya yazilir (id + gozlem zamani + o anki
     `origin/main` SHA'si).
  2. IKINCI GOZLEM, FARKLI `origin/main` SHA'sinda -> SILINIR. Farkli SHA demek, aradaki
     pencerede main ILERLEDI demektir; "ucustaki parti" aciklamasi CURUR (o parti inmis olurdu).
  3. AYNI SHA'da ikinci gozlem -> SILINMEZ. Main hic ilerlemediyse ucustaki parti hala
     ucusta olabilir.
  4. Karantinadaki id AGACTA BELIRIRSE karantinadan DUSER (kayit temizlenir, silinmez).
  5. Damga OKUNAMIYORSA (artifact yok / bozuk / suresi dolmus) hukum FAIL-CLOSED:
     SILME YAPILMAZ ve `OLCULEMEDI` basilir. "Okuyamadim -> sil" yolu ACILMAZ.

  🔴 BAYATLIK (TAZELIK_SN): kaydin kendisi de bayatlar. Iki kosum arasinda saatler
  gecerse (cron teslimi olculdu: en uzun bosluk 17,6 saat) eski bir kayit, ARADA baska
  sebeplerle ilerlemis bir SHA ile eslesip "ikinci gozlem" gibi gorunurdu. TAZELIK_SN'den
  eski kayit GECERSIZDIR ve id YENIDEN karantinaya alinir (silme YOK). Yon her zaman
  guvenli tarafa: suphede SILME.

  🔴 DAMGA NEDEN ARTIFACT, DEPODA IZLENEN DOSYA DEGIL: uzlastirici her kosumda main'e
  push etseydi main'in ucu surekli oynardi — 17:12Z kosumunu DUSUREN sey tam olarak main
  ucunun yazma penceresinde ilerlemesiydi. Damga mekanizmasi, olcmesi gereken hastaligi
  URETEMEZ.

`EKSIK` ve `hash UYUSMAZ` kollari bu modulden ETKILENMEZ — onlar ekleme/guncellemedir.

Kullanim (CLI — is akisi adimlari):
    python3 tools/uzlastirici_karantina.py --indir karantina-damgasi.json
    python3 tools/uzlastirici_karantina.py --temizle karantina-damgasi.json
Kutuphane olarak (d1-sync.py):
    uygula(fazla, yol, sha)          -> silinecek id'ler + hukum (damgayi da yazar)
    karantinadaki(yol)               -> --durum'un teyit kolunda muaf tutulacak id'ler
"""
import argparse
import json
import os
import sys
import time
import zipfile

ARAC = os.path.basename(os.path.abspath(__file__))

# Artifact adi (is akisi `upload-artifact`/`download` adimlari BU adi kullanir) ve
# is akisi calisma dizinindeki kanonik dosya adi. IKISI DE TEK KAYNAK: kabul testi
# .github/workflows/d1-uzlastirici.yml'i BU sabitlere karsi olcer, boylece ad
# sessizce ayrisamaz ([[ikiz-tanim-sessiz-ayrisma]]).
DAMGA_ADI = "d1-karantina-damgasi"
DAMGA_DOSYA = "karantina-damgasi.json"
SURUM = 1

# Kayit tazeligi. Artifact saklamasi bu depoda 24 saat olculdu; kayit ondan UZUN
# yasayamaz (yasasaydi zaten indirilemezdi) — esik onunla ayni tutuldu.
TAZELIK_SN = 24 * 3600

# 🔴 FAIL-CLOSED IMZASI. `uzlastirici-onarim.py` bu metni ciktida arar ve kosumu
# "KARANTINA OLCULEMEDI" (rc 4) olarak kapatir — yeniden DENEMEZ (tekrar okumak
# damgayi var etmez). Metin degisirse tools/uzlastirici-karantina-test.py'deki IMZA
# CAPASI KIRMIZI yanar; imza sessizce bayatlayamaz.
OKUNAMADI_IMZASI = "!! KARANTINA DAMGASI OKUNAMADI:"

DEPO = os.environ.get("GITHUB_REPOSITORY") or "Pruvo138/pruvo"
API = "https://api.github.com"


# ---------------------------------------------------------------------------
# DAMGA G/C
# ---------------------------------------------------------------------------
def _sha_gecerli(sha):
    """origin/main ucu SHA'si karsilastirilabilir mi (kisa/bos/None -> HAYIR)."""
    return isinstance(sha, str) and len(sha.strip()) >= 7


def _kayit_gecerli(k):
    return (isinstance(k, dict) and _sha_gecerli(k.get("sha"))
            and isinstance(k.get("ts"), (int, float)))


def _yeni_kayit(sha, simdi):
    return {"sha": sha.strip(), "ts": float(simdi)}


def damga_oku(yol):
    """Doner: (kayitlar|None, sebep). None = OKUNAMADI (fail-closed: silme YOK).

    Bos ama GECERLI bir damga ({} kayit) OKUNAMADI DEGILDIR — o "hic gozlem yok"
    demektir ve ilk gozlem kolunu (K1) besler."""
    if not yol:
        return None, "damga yolu verilmedi"
    if not os.path.exists(yol):
        return None, "damga dosyasi YOK: %s (artifact inmedi / hic uretilmedi)" % yol
    try:
        with open(yol, encoding="utf-8") as f:
            govde = json.load(f)
    except Exception as e:                                        # noqa: BLE001
        return None, "damga JSON olarak okunamadi (%s): %s" % (type(e).__name__, e)
    if not isinstance(govde, dict):
        return None, "damga kok dugumu sozluk DEGIL: %s" % type(govde).__name__
    if govde.get("surum") != SURUM:
        return None, "damga surumu uyusmuyor (beklenen %r, bulunan %r)" % (
            SURUM, govde.get("surum"))
    kayitlar = govde.get("kayitlar")
    if not isinstance(kayitlar, dict):
        return None, "damgada `kayitlar` sozlugu YOK/bozuk"
    return kayitlar, "damga okundu (%d kayit)" % len(kayitlar)


def damga_yaz(yol, kayitlar, sha, simdi=None):
    """Damgayi ATOMIK yaz (gecici dosya + os.replace) — yarim JSON dogmaz."""
    simdi = time.time() if simdi is None else simdi
    govde = {"surum": SURUM, "damga": DAMGA_ADI, "yazan": "tools/" + ARAC,
             "yazma_ts": float(simdi), "sha": (sha or "").strip(),
             "kayitlar": kayitlar}
    gecici = yol + ".gecici"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(govde, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(gecici, yol)
    return govde


# ---------------------------------------------------------------------------
# HAKEM — SAF FONKSIYON (ag YOK, disk YOK, saat ENJEKTE EDILIR)
# ---------------------------------------------------------------------------
def karar(fazla, kayitlar, sha, simdi):
    """FAZLA id'lerin hangisi SILINIR — saf hakem.

    fazla    : bu kosumda "D1'de var, agacta yok" olculen id'ler
    kayitlar : damgadaki {id: {"sha","ts"}} — None ise damga OKUNAMADI
    sha      : SU ANKI `origin/main` ucu
    simdi    : epoch saniye (enjekte edilir; test saati sabitler)

    Doner: {"hukum","silinecek","acilan","bekleyen","bayat","dusen","kayitlar","yaz"}
      hukum: OLCULEMEDI | SILINDI | ACILDI | BEKLIYOR | TEMIZ
      yaz  : yeni damga diske YAZILMALI mi (SHA olculemediyse HAYIR — bozuk kayit dogmasin)
    """
    fazla = list(dict.fromkeys(fazla or []))

    # (5) DAMGA OKUNAMADI -> FAIL-CLOSED. Silme YOK. Yeni damga yine de yazilir:
    # bu bir ILK GOZLEM tescilidir (bootstrap), hukum yine de OLCULEMEDI'dir ve
    # yuksek sesle basilir. Silmeyi acan hicbir yol buradan gecmez.
    if kayitlar is None:
        if not _sha_gecerli(sha):
            return {"hukum": "OLCULEMEDI", "silinecek": [], "acilan": [], "bekleyen": [],
                    "bayat": [], "dusen": [], "kayitlar": {}, "yaz": False}
        return {"hukum": "OLCULEMEDI", "silinecek": [], "acilan": sorted(fazla),
                "bekleyen": [], "bayat": [], "dusen": [],
                "kayitlar": {u: _yeni_kayit(sha, simdi) for u in fazla}, "yaz": True}

    # SHA olculemediyse "ayni mi farkli mi" sorusu SORULAMAZ -> fail-closed.
    if not _sha_gecerli(sha):
        return {"hukum": "OLCULEMEDI", "silinecek": [], "acilan": [], "bekleyen": [],
                "bayat": [], "dusen": [], "kayitlar": dict(kayitlar), "yaz": False}

    sha = sha.strip()
    silinecek, acilan, bekleyen, bayat = [], [], [], []
    yeni = {}
    for uid in fazla:
        k = kayitlar.get(uid)
        if not _kayit_gecerli(k):
            # (1) ILK GOZLEM (ya da bozuk kayit) -> SILME YOK, karantinaya yaz.
            acilan.append(uid)
            yeni[uid] = _yeni_kayit(sha, simdi)
            continue
        if (float(simdi) - float(k["ts"])) > TAZELIK_SN:
            # BAYAT KAYIT -> ikinci gozlem SAYILMAZ, yeniden karantinaya alinir.
            bayat.append(uid)
            acilan.append(uid)
            yeni[uid] = _yeni_kayit(sha, simdi)
            continue
        if str(k["sha"]).strip() != sha:
            # (2) FARKLI SHA'da ikinci gozlem -> "ucustaki parti" aciklamasi CURUDU.
            silinecek.append(uid)
            continue
        # (3) AYNI SHA -> main ilerlemedi; parti hala ucusta olabilir. BEKLE.
        bekleyen.append(uid)
        yeni[uid] = k

    # (4) Karantinadaki id agacta belirdi (artik FAZLA degil) -> kayit DUSER.
    dusen = sorted(set(kayitlar) - set(fazla))

    if silinecek:
        hukum = "SILINDI"
    elif acilan:
        hukum = "ACILDI"
    elif bekleyen:
        hukum = "BEKLIYOR"
    else:
        hukum = "TEMIZ"
    return {"hukum": hukum, "silinecek": sorted(silinecek), "acilan": sorted(acilan),
            "bekleyen": sorted(bekleyen), "bayat": sorted(bayat), "dusen": dusen,
            "kayitlar": yeni, "yaz": True}


def hukum_satirlari(k, sebep=""):
    """Karar sozlugunden CI logunda basilan satirlar (makine-okunur anahtarlar)."""
    s = ["KARANTINA_HUKUM=%s" % k["hukum"],
         "KARANTINA_ACILDI=%d" % len(k["acilan"]),
         "KARANTINA_SILINDI=%d" % len(k["silinecek"]),
         "KARANTINA_BEKLEYEN=%d" % len(k["bekleyen"]),
         "KARANTINA_DUSEN=%d" % len(k["dusen"]),
         "KARANTINA_BAYAT=%d" % len(k["bayat"])]
    if k["acilan"]:
        s.append("   karantinaya alinan (BU KOSUMDA SILINMEZ): "
                 + ", ".join(k["acilan"][:10])
                 + (" ... (+%d)" % (len(k["acilan"]) - 10) if len(k["acilan"]) > 10 else ""))
    if k["silinecek"]:
        s.append("   ikinci gozlem FARKLI origin/main SHA'sinda -> SILINIYOR: "
                 + ", ".join(k["silinecek"][:10])
                 + (" ... (+%d)" % (len(k["silinecek"]) - 10)
                    if len(k["silinecek"]) > 10 else ""))
    if k["hukum"] == "OLCULEMEDI":
        s = [OKUNAMADI_IMZASI + " " + (sebep or "sebep bilinmiyor"),
             "   FAIL-CLOSED: bu kosumda HICBIR satir SILINMEDI. 'Okuyamadim -> sil' yolu",
             "   ACIK OLSAYDI, 11 Agu'da 37 mesru katalog satirini silen hal aynen "
             "tekrarlanirdi.",
             ] + s
    return s


# ---------------------------------------------------------------------------
# UYGULAMA KOLU — d1-sync.py buradan cagirir
# ---------------------------------------------------------------------------
def uygula(fazla, yol, sha, simdi=None, yaz=print):
    """Damgayi oku -> karar ver -> damgayi yaz -> hukmu bas. Doner: karar sozlugu."""
    simdi = time.time() if simdi is None else simdi
    kayitlar, sebep = damga_oku(yol)
    k = karar(fazla, kayitlar, sha, simdi)
    k["sebep"] = sebep
    for satir in hukum_satirlari(k, sebep):
        yaz(satir)
    if k["yaz"]:
        try:
            damga_yaz(yol, k["kayitlar"], sha, simdi)
        except Exception as e:                                    # noqa: BLE001
            # Damga yazilamazsa SILME KARARI DA GECERSIZDIR: silinen id bir daha
            # gozlenmeyecegi icin kayit kaybi silmeyi "ilk gozlem"e geri dondururdu.
            # Fail-closed: silme listesi BOSALTILIR.
            yaz("%s damga YAZILAMADI (%s: %s) -> silme IPTAL"
                % (OKUNAMADI_IMZASI, type(e).__name__, e))
            k["hukum"] = "OLCULEMEDI"
            k["silinecek"] = []
    return k


def karantinadaki(yol, simdi=None):
    """`--durum` teyit kolunun MUAF tutacagi id'ler (gecerli + TAZE kayitlar).

    Damga okunamiyorsa BOS kume doner: muafiyet KANIT ISTER, yoklugu muafiyet degildir."""
    simdi = time.time() if simdi is None else simdi
    kayitlar, _sebep = damga_oku(yol)
    if not kayitlar:
        return set()
    return {u for u, k in kayitlar.items()
            if _kayit_gecerli(k) and (float(simdi) - float(k["ts"])) <= TAZELIK_SN}


# ---------------------------------------------------------------------------
# CLI — is akisi adimlari
# ---------------------------------------------------------------------------
def _jeton():
    for ad in ("GITHUB_TOKEN", "GH_TOKEN"):
        deger = (os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return None


def _yonlendirme_elegi():
    """`Authorization`i ANA MAKINE (host) DEGISIMINDE dusuren yonlendirme isleyicisi.

    NEDEN VAR (OLCULDU, 12 Agu 2026 — kosum 31592377276, rc=4)
    ==========================================================
    Damga indirme adimi UC ARDISIK kosumda 401 aldi:

        KARANTINA DAMGASI INDIRILEMEDI (HTTPError: HTTP Error 401: Server failed to
        authenticate the request...) -> bu kosumda SILME YAPILMAZ (fail-closed).

    Artifact VARDI ve suresi DOLMAMISTI (id 9139248461, created 11:20:31Z). Hal
    "artifact yok" degil, "indirme kimlik dogrulamada dusuyor" idi:
    `archive_download_url` GitHub tarafindan **302** ile IMZALI (SAS) bir blob
    adresine yonlendirilir; urllib'in varsayilan `HTTPRedirectHandler`'i orijinal
    basliklari — `Authorization` DAHIL — hedefe AYNEN tasir. Imzali adres kendi
    imzasiyla yetkilendirir; ustune bir de `Authorization` gorunce 401 basar
    ("Server failed to authenticate the request" tam olarak o depolamanin metnidir).

    🔴 ARIZA SESSIZDI: `indir()` False donuyor ama CLI kolu 0 ile cikiyor, adim
    YESIL kaliyordu. OLCULDU: karantina indigi 12 Agu 00:10Z'den 11:33Z'ye kadar
    adimin kostugu 22 kosumun 0'inda "KARANTINA DAMGASI INDI" satiri BASMADI —
    yani silme kolu dogdugu gunden beri HIC calismadi (her kosum OLCULEMEDI).

    🔴 DUZELTME NEDEN HOST EKSENINDE, "her yonlendirmede dusur" DEGIL: jeton her
    yonlendirmede dusurulseydi GitHub'in KENDI ic yonlendirmeleri yetkisiz kalir
    ve listeleme cagrisi bu kez 401 verirdi. Sozlesme iki cumledir: host
    DEGISIRSE dusur, AYNI host'a yonlendirmede KORU. Ikisi de K8'de olculur.
    """
    import urllib.parse
    import urllib.request

    class _HostDegisimindeJetonuDusur(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            yeni = urllib.request.HTTPRedirectHandler.redirect_request(
                self, req, fp, code, msg, headers, newurl)
            if yeni is None:
                return None
            eski_host = (urllib.parse.urlsplit(req.full_url).hostname or "").lower()
            yeni_host = (urllib.parse.urlsplit(yeni.full_url).hostname or "").lower()
            if eski_host != yeni_host:
                yeni.remove_header("Authorization")
            return yeni

    return _HostDegisimindeJetonuDusur()


def _api_getir(yol, ham=False, zaman_asimi=30):
    import urllib.error
    import urllib.request
    url = yol if yol.startswith("http") else "%s/%s" % (API, yol.lstrip("/"))
    istek = urllib.request.Request(url, method="GET")
    istek.add_header("Accept", "application/vnd.github+json")
    istek.add_header("X-GitHub-Api-Version", "2022-11-28")
    istek.add_header("User-Agent", "pruvo-uzlastirici-karantina")
    jeton = _jeton()
    if jeton:
        istek.add_header("Authorization", "Bearer %s" % jeton)
    # Varsayilan acici DEGIL: jetonu capraz-host yonlendirmede dusuren aciciyi kur.
    acici = urllib.request.build_opener(_yonlendirme_elegi())
    with acici.open(istek, timeout=zaman_asimi) as y:
        veri = y.read()
    return veri if ham else json.loads(veri.decode("utf-8", "replace"))


def indir(hedef, getir=_api_getir, yaz=print):
    """EN TAZE `d1-karantina-damgasi` artifact'ini indir -> hedef dosyaya yaz.

    Doner: True (indi) | False (yok/inmedi). ARIZA YUTULMAZ ama KOSUMU DUSURMEZ:
    damga inmezse bir sonraki adim FAIL-CLOSED `OLCULEMEDI` verir ve HICBIR SEY
    SILINMEZ — yani "indiremedim" hali zaten en guvenli yone dusuyor, ustelik
    GORUNUR (hukum satiri OLCULEMEDI basar)."""
    try:
        govde = getir("repos/%s/actions/artifacts?name=%s&per_page=100"
                      % (DEPO, DAMGA_ADI))
        adaylar = [a for a in (govde.get("artifacts") or [])
                   if not a.get("expired") and a.get("archive_download_url")]
        if not adaylar:
            yaz("KARANTINA DAMGASI YOK: `%s` adiyla suresi dolmamis artifact bulunamadi "
                "(ilk kosum ya da saklama suresi doldu)." % DAMGA_ADI)
            return False
        adaylar.sort(key=lambda a: str(a.get("created_at") or ""), reverse=True)
        en_taze = adaylar[0]
        zip_ham = getir(en_taze["archive_download_url"], ham=True)
        gecici = hedef + ".zip"
        with open(gecici, "wb") as f:
            f.write(zip_ham)
        with zipfile.ZipFile(gecici) as z:
            adlar = [n for n in z.namelist() if n.endswith(".json")]
            if not adlar:
                yaz("KARANTINA DAMGASI BOZUK: artifact zip'inde .json YOK (%s)"
                    % ", ".join(z.namelist()[:5]))
                os.remove(gecici)
                return False
            with open(hedef, "wb") as f:
                f.write(z.read(adlar[0]))
        os.remove(gecici)
        yaz("KARANTINA DAMGASI INDI: %s (artifact #%s · %s)"
            % (hedef, en_taze.get("id"), en_taze.get("created_at")))
        return True
    except Exception as e:                                        # noqa: BLE001
        yaz("KARANTINA DAMGASI INDIRILEMEDI (%s: %s) -> bu kosumda SILME YAPILMAZ "
            "(fail-closed)." % (type(e).__name__, e))
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description="D1 uzlastirici silme karantinasi")
    ap.add_argument("--indir", metavar="YOL", default=None,
                    help="en taze karantina damgasi artifact'ini YOL'a indir")
    ap.add_argument("--temizle", metavar="YOL", default=None,
                    help="BOS damga yaz (sapma YOK: hicbir id FAZLA degil -> karantina bos)")
    # NEDEN AYRI BAYRAK: onarim kolunda d1-sync damgayi YAZAR — ama silinecek aday
    # YOKKEN erken donebilir ("degisiklik yok") ve dosya HIC dogmayabilir. O zaman
    # `if-no-files-found: error` tasiyan yukleme adimi kosumu KIRMIZI yakardi. Bu
    # bayrak yalnizca DOSYA YOKKEN bos damga tescil eder; VAR OLAN damgayi ASLA
    # EZMEZ (ezseydi biriken ikinci-gozlem hafizasi her kosumda sifirlanir ve silme
    # kolu sessizce olurdu -> [[sessiz-uzerine-yazma-yasak]]).
    ap.add_argument("--temizle-yoksa", dest="temizle_yoksa", metavar="YOL", default=None,
                    help="damga dosyasi YOKSA bos damga yaz; VARSA DOKUNMA")
    ap.add_argument("--sha", default=None, help="--temizle ile yazilacak origin/main ucu")
    ap.add_argument("--goster", metavar="YOL", default=None,
                    help="damgayi oku ve ozetini bas (teshis)")
    a = ap.parse_args(argv)
    if a.indir:
        indir(a.indir)
        return 0
    if a.temizle:
        damga_yaz(a.temizle, {}, a.sha or "")
        print("KARANTINA DAMGASI TEMIZLENDI (sapma yok -> 0 kayit): %s" % a.temizle)
        return 0
    if a.temizle_yoksa:
        if os.path.exists(a.temizle_yoksa):
            print("KARANTINA DAMGASI ZATEN VAR — DOKUNULMADI (ustune yazmak ikinci "
                  "gozlem hafizasini silerdi): %s" % a.temizle_yoksa)
            return 0
        damga_yaz(a.temizle_yoksa, {}, a.sha or "")
        print("KARANTINA DAMGASI YOKTU — bos damga tescil edildi: %s" % a.temizle_yoksa)
        return 0
    if a.goster:
        kayitlar, sebep = damga_oku(a.goster)
        print(sebep)
        if kayitlar:
            for uid, k in sorted(kayitlar.items()):
                print("   %s : sha=%s ts=%s" % (uid, str(k.get("sha"))[:12], k.get("ts")))
        return 0 if kayitlar is not None else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

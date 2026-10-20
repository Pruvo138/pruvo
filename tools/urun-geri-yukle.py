#!/usr/bin/env python3
"""urun-geri-yukle.py — silinen TEK urunu git gecmisinden tabana GERI yukler.

BAGLAM (Okan emri 2 Eyl 2026 + BaBa cercevesi (2): silme GERI ALINABILIR olmali;
BaBa 20 Eki: public arsivde GOVDE YOK): silme yollari (panel "Sil" -> panel-uygulayici,
izinli `duzelt.py --sil`) arsiv/urunler-arsiv.json'a yalniz GOVDESIZ iz yazar
(id + silinme_ts + silme_commit + govde_sha256; sekil tools/urun_arsivi.py). Govde
silme commit'inin EBEVEYNINDEDIR: `git show <silme_commit>^:urunler.json`.
Yordamin tamami: tools/urun-silme-yordami.md.

NE YAPAR (tek cagri, tek kilit):
  1. Arsivdeki EN YENI girisi bulur (ayni id birden fazla silinmisse son silinen) ve
     govdeyi `<silme_commit>^:urunler.json`dan alir (silme_commit bos ise girisi arsive
     ekleyen commit'ten turetilir); govde govde_sha256 ile ESLESMEZSE hicbir sey
     yazilmaz (GOVDE_DOGRULANAMADI, rc!=0).
  2. urunler.json'a BASA ekler (yeni urun kurali: dizi basi) — id zaten tabandaysa
     HICBIR SEY yazmaz (ZATEN_TABANDA, rc!=0).
  3. .diriltme-izin.json'a id-duzeyinde beyan yazar: diriltme-kapisi (EKSEN 1,
     "silinmis id geri geldi") beyanla YESIL kalir — kapi GEVSETILMEZ, kapinin
     kendi beyan yolu kullanilir (BaBa (4)).
  4. Arsiv kaydina DOKUNMAZ (arsiv append-only tarihtir; ayni urun ileride yeniden
     silinirse yeni kayit eklenir).

GUARD ILE ILISKI: geri yuklenen id HEAD'e gore YENI iddir -> urunler-guard yeni
id'yi serbest birakir, manifest gerekmez. Yazim biciminde ikinci kopya YOKTUR:
_atomic_write duzelt.py'den IMPORT edilir (bayt-bicim paritesi).

SONRAKI ADIMLAR (arac yazdirir, kendisi commit/push YAPMAZ — merge/push hukmu
mimarin): git add urunler.json .diriltme-izin.json -> commit -> push. Pre-push
kancasi D1 senkronunu, CI deploy sitemap/feed/sayfa uretimini kendisi yapar.

KIPLER:
  python3 tools/urun-geri-yukle.py <id> [--gerekce "kisa gerekce"]
  python3 tools/urun-geri-yukle.py --kendini-test

TEST DIKISI (canli kosumda KAPALI): URUN_GERI_KOK=<yol> repo koku yerine fikstur
(git deposu olmali: govde git gecmisinden gelir).
"""
import argparse
import datetime
import fcntl
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ARAC_YOLU = os.path.abspath(__file__)
VARSAYILAN_KOK = os.path.dirname(os.path.dirname(ARAC_YOLU))
ARSIV_GORELI = os.path.join("arsiv", "urunler-arsiv.json")


def _modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _urun_arsivi():
    # Arsiv sekli + git cozumleyici TEK kaynak (tools/urun_arsivi.py).
    return _modul_yukle(os.path.join(VARSAYILAN_KOK, "tools", "urun_arsivi.py"),
                        "pruvo_urun_arsivi_gy")


def _duzelt():
    # _atomic_write TEK kaynaktan (duzelt.py) gelir — yazim bicimi ayrisamaz.
    return _modul_yukle(os.path.join(VARSAYILAN_KOK, "tools", "duzelt.py"),
                        "pruvo_duzelt_gy")


def simdi_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def geri_yukle(uid, gerekce):
    kok = os.environ.get("URUN_GERI_KOK") or VARSAYILAN_KOK
    arsiv_yolu = os.path.join(kok, ARSIV_GORELI)
    urunler_yolu = os.path.join(kok, "urunler.json")
    izin_yolu = os.path.join(kok, ".diriltme-izin.json")
    kilit_yolu = os.path.join(kok, ".urunler.lock")

    if not os.path.exists(arsiv_yolu):
        print("HATA: arsiv dosyasi yok: %s" % arsiv_yolu, file=sys.stderr)
        return 1
    with open(arsiv_yolu, encoding="utf-8") as f:
        arsiv = json.load(f)
    ua = _urun_arsivi()
    adaylar = [e for e in arsiv if ua.giris_id(e) == uid]
    if not adaylar:
        print("HATA: ARSIVDE_YOK — '%s' arsivde bulunamadi (%d kayit tarandi)."
              % (uid, len(arsiv)), file=sys.stderr)
        return 1
    aday = adaylar[-1]  # ayni id birden fazla silinmisse EN YENI silinen kazanir
    try:
        govde, silme_commit = ua.govde_getir(kok, aday)
    except ua.ArsivHatasi as e:
        print("HATA: GOVDE_DOGRULANAMADI — %s; hicbir sey yazilmadi." % e, file=sys.stderr)
        return 1

    dz = _duzelt()
    lockf = open(kilit_yolu, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(urunler_yolu, encoding="utf-8") as f:
            urunler = json.load(f)
        if any(isinstance(p, dict) and p.get("id") == uid for p in urunler):
            print("HATA: ZATEN_TABANDA — '%s' urunler.json'da zaten var; hicbir sey "
                  "yazilmadi." % uid, file=sys.stderr)
            return 1
        once = len(urunler)
        urunler.insert(0, govde)  # yeni urun kurali: dizi BASINA
        dz._atomic_write(urunler_yolu, urunler)

        # Diriltme beyani — kapinin KENDI beyan yolu (kapi gevsetilmez).
        izin = {}
        if os.path.exists(izin_yolu):
            with open(izin_yolu, encoding="utf-8") as f:
                izin = json.load(f)
        izin[uid] = ("Mimar karari (tools/urun-geri-yukle.py, %s): silme izinden geri "
                     "yukleme (silinme_ts=%s, kuyruk_id=%s, silme_commit=%s). %s"
                     % (simdi_utc(), aday.get("silinme_ts", "?"),
                        aday.get("kuyruk_id", "?"), silme_commit[:12],
                        (gerekce or "").strip())).strip()
        gecici = izin_yolu + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(izin, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(gecici, izin_yolu)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    print("GERI_YUKLENDI: %s  (katalog %d -> %d; dizi basina eklendi; govde %s^:urunler.json, "
          "sha256 dogrulandi)" % (uid, once, once + 1, silme_commit[:12]))
    print("Diriltme beyani yazildi: .diriltme-izin.json['%s']" % uid)
    print("Arsiv kaydina DOKUNULMADI (append-only tarih).")
    print("SONRAKI ADIMLAR (mimar): git add urunler.json .diriltme-izin.json && "
          "commit && push  — pre-push D1 senkronu + CI deploy gerisini yapar.")
    return 0


# ── kendini-test ─────────────────────────────────────────────────────────────────

def _kos(uid, kok, gerekce=None):
    ort = dict(os.environ)
    ort["URUN_GERI_KOK"] = kok
    komut = [sys.executable, ARAC_YOLU, uid]
    if gerekce:
        komut += ["--gerekce", gerekce]
    p = subprocess.run(komut, env=ort, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def _fg(dizin, *args):
    sys.path.insert(0, os.path.join(VARSAYILAN_KOK, "tools"))
    from git_ortami import sentetik_git
    p = sentetik_git(dizin, *args, ayarlar=("-c", "commit.gpgsign=false",
                                            "-c", "core.hooksPath=/var/empty/yok"),
                     capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout.strip()


def _jyaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def kendini_test():
    vaka, dusen = 0, []

    def ol(ad, kosul, detay=""):
        nonlocal vaka
        vaka += 1
        if kosul:
            print("  OK   " + ad)
        else:
            print("  HATA %s %s" % (ad, str(detay)[:300]))
            dusen.append(ad)

    ua = _urun_arsivi()
    tmp = tempfile.mkdtemp(prefix="urun-geri-test-")
    try:
        KAYIT_ESKI = {"id": "test-sil", "kategori": "Ofis", "baslik": "Eski Surum",
                      "aciklama": "a", "fiyat": "90 TL", "marka": [], "uyum": [],
                      "gorseller": ["https://media.pruvo3d.com/urunler/ts-1.jpg"]}
        KAYIT_YENI = dict(KAYIT_ESKI, baslik="Yeni Surum", fiyat="100 TL")
        KALAN = [{"id": "kalan-a", "baslik": "Kalan A"},
                 {"id": "kalan-b", "baslik": "Kalan B"}]
        kok = os.path.join(tmp, "fikstur")
        os.makedirs(os.path.join(kok, "arsiv"))
        _fg(kok, "init", "-q")
        uyol = os.path.join(kok, "urunler.json")
        ayol = os.path.join(kok, ARSIV_GORELI)
        # Gercek silme gecmisi: ESKI surum silinir (giris 1, silme_commit DOLU sonradan),
        # geri gelir, YENI surum olarak tekrar silinir (giris 2, silme_commit BOS).
        _jyaz(uyol, [KAYIT_ESKI] + KALAN)
        _jyaz(ayol, [])
        _fg(kok, "add", "-A")
        _fg(kok, "commit", "-q", "-m", "taban")
        g1 = ua.giris_yap(KAYIT_ESKI, "panel-uygulayici", 1, "2026-09-01T00:00:00Z")
        _jyaz(uyol, KALAN)
        _jyaz(ayol, [g1])
        _fg(kok, "add", "-A")
        _fg(kok, "commit", "-q", "-m", "sil 1")
        sil1 = _fg(kok, "rev-parse", "HEAD")
        g1["silme_commit"] = sil1
        _jyaz(uyol, [KAYIT_YENI] + KALAN)
        _jyaz(ayol, [g1])
        _fg(kok, "add", "-A")
        _fg(kok, "commit", "-q", "-m", "geri + duzenleme")
        g2 = ua.giris_yap(KAYIT_YENI, "panel-uygulayici", 2, "2026-09-02T00:00:00Z")
        _jyaz(uyol, KALAN)
        _jyaz(ayol, [g1, g2])
        _fg(kok, "add", "-A")
        _fg(kok, "commit", "-q", "-m", "sil 2")
        with open(os.path.join(kok, ".diriltme-izin.json"), "w", encoding="utf-8") as f:
            json.dump({"baska-urun#fiyat": "onceki beyan"}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        with open(ayol, "rb") as f:
            arsiv_b = f.read()
        ol("V0 fikstur arsivi GOVDESIZ (sekil ihlali 0, 'baslik' yok)",
           not ua.govdeli_girisler(json.loads(arsiv_b)) and b"baslik" not in arsiv_b)

        # V1: geri yukleme — basa eklenir, EN YENI silinen surum git'ten gelir, beyan yazilir.
        rc, cikti = _kos("test-sil", kok, "kobay geri yukleme provasi")
        with open(uyol, encoding="utf-8") as f:
            taban = json.load(f)
        with open(os.path.join(kok, ".diriltme-izin.json"), encoding="utf-8") as f:
            izin = json.load(f)
        ol("V1a rc=0 + katalog 2->3", rc == 0 and len(taban) == 3, cikti)
        ol("V1b kayit DIZI BASINDA ve EN YENI silinen surum (git gecmisinden)",
           taban[0] == KAYIT_YENI, json.dumps(taban[0], ensure_ascii=False))
        ol("V1c komsu kayitlar ayni sirada",
           taban[1]["id"] == "kalan-a" and taban[2]["id"] == "kalan-b")
        ol("V1d diriltme beyani yazildi + onceki beyan KORUNDU",
           "test-sil" in izin and "kuyruk_id=2" in izin["test-sil"]
           and izin.get("baska-urun#fiyat") == "onceki beyan",
           json.dumps(izin, ensure_ascii=False))
        with open(ayol, "rb") as f:
            ol("V1e arsiv dosyasina DOKUNULMADI (byte-esit)", f.read() == arsiv_b)

        # V2: id zaten tabanda -> rc!=0, urunler.json BYTE-esit.
        with open(uyol, "rb") as f:
            once_b = f.read()
        rc, cikti = _kos("test-sil", kok)
        with open(uyol, "rb") as f:
            sonra_b = f.read()
        ol("V2 ZATEN_TABANDA -> rc!=0 + taban byte-esit",
           rc != 0 and "ZATEN_TABANDA" in cikti and once_b == sonra_b, cikti)

        # V3: arsivde olmayan id -> rc!=0, hicbir dosya degismez.
        rc, cikti = _kos("hic-olmayan-urun", kok)
        with open(uyol, "rb") as f:
            v3_b = f.read()
        ol("V3 ARSIVDE_YOK -> rc!=0 + taban byte-esit",
           rc != 0 and "ARSIVDE_YOK" in cikti and v3_b == once_b, cikti)

        # V4: govde_sha256 git'teki govdeyle ESLESMEZ -> fail-closed, taban byte-esit.
        _jyaz(uyol, KALAN)
        with open(uyol, "rb") as f:
            v4_once = f.read()
        bozuk = [g1, dict(g2, govde_sha256="0" * 64)]
        _jyaz(ayol, bozuk)
        rc, cikti = _kos("test-sil", kok)
        with open(uyol, "rb") as f:
            v4_sonra = f.read()
        ol("V4 parmak izi eslesmez -> GOVDE_DOGRULANAMADI rc!=0 + taban byte-esit",
           rc != 0 and "GOVDE_DOGRULANAMADI" in cikti and v4_once == v4_sonra, cikti)

        # V5: DOLU silme_commit yolu — ilk silinen (ESKI) surum <silme_commit>^'den gelir.
        _jyaz(ayol, [g1])
        rc, cikti = _kos("test-sil", kok)
        with open(uyol, encoding="utf-8") as f:
            taban5 = json.load(f)
        ol("V5 silme_commit dolu -> govde %s^:urunler.json (ESKI surum)" % sil1[:8],
           rc == 0 and taban5[0] == KAYIT_ESKI, cikti)

        print("SONUC: VAKA=%d DUSEN=%d" % (vaka, len(dusen)))
        return 0 if not dusen else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("id", nargs="?", help="geri yuklenecek urun id'si")
    ap.add_argument("--gerekce", default="", help="beyana eklenecek kisa gerekce")
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    if not a.id:
        ap.print_help()
        return 2
    return geri_yukle(a.id, a.gerekce)


if __name__ == "__main__":
    sys.exit(main())

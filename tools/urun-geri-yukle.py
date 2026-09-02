#!/usr/bin/env python3
"""urun-geri-yukle.py — arsiv/urunler-arsiv.json'dan TEK urunu tabana GERI yukler.

BAGLAM (Okan emri 2 Eyl 2026 + BaBa cercevesi (2): silme GERI ALINABILIR olmali):
panelin "Sil (arsive)" yolu (yonet.js /urun-sil -> panel_ustyazim alan='sil' ->
tools/panel-uygulayici.py -> duzelt --toplu {"id","sil"}) taban kaydini YOK ETMEZ;
TAM kaydi arsiv/urunler-arsiv.json'a tasir. Bu arac o kaydi tabana geri getirir.
Yordamin tamami: tools/urun-silme-yordami.md.

NE YAPAR (tek cagri, tek kilit):
  1. Arsivdeki EN YENI kaydi bulur (ayni id birden fazla silinmisse son silinen).
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

TEST DIKISI (canli kosumda KAPALI): URUN_GERI_KOK=<yol> repo koku yerine fikstur.
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
    adaylar = [e for e in arsiv
               if isinstance(e, dict) and isinstance(e.get("kayit"), dict)
               and e["kayit"].get("id") == uid]
    if not adaylar:
        print("HATA: ARSIVDE_YOK — '%s' arsivde bulunamadi (%d kayit tarandi)."
              % (uid, len(arsiv)), file=sys.stderr)
        return 1
    aday = adaylar[-1]  # ayni id birden fazla silinmisse EN YENI silinen kazanir

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
        urunler.insert(0, aday["kayit"])  # yeni urun kurali: dizi BASINA
        dz._atomic_write(urunler_yolu, urunler)

        # Diriltme beyani — kapinin KENDI beyan yolu (kapi gevsetilmez).
        izin = {}
        if os.path.exists(izin_yolu):
            with open(izin_yolu, encoding="utf-8") as f:
                izin = json.load(f)
        izin[uid] = ("Mimar karari (tools/urun-geri-yukle.py, %s): panel silme "
                     "arsivinden geri yukleme (silinme_ts=%s, kuyruk_id=%s). %s"
                     % (simdi_utc(), aday.get("silinme_ts", "?"),
                        aday.get("kuyruk_id", "?"), (gerekce or "").strip())).strip()
        gecici = izin_yolu + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(izin, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(gecici, izin_yolu)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    print("GERI_YUKLENDI: %s  (katalog %d -> %d; dizi basina eklendi)"
          % (uid, once, once + 1))
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

    tmp = tempfile.mkdtemp(prefix="urun-geri-test-")
    try:
        KAYIT_ESKI = {"id": "test-sil", "kategori": "Ofis", "baslik": "Eski Surum",
                      "aciklama": "a", "fiyat": "90 TL", "marka": [], "uyum": [],
                      "gorseller": ["https://media.pruvo3d.com/urunler/ts-1.jpg"]}
        KAYIT_YENI = dict(KAYIT_ESKI, baslik="Yeni Surum", fiyat="100 TL")
        TABAN = [{"id": "kalan-a", "baslik": "Kalan A"},
                 {"id": "kalan-b", "baslik": "Kalan B"}]
        kok = os.path.join(tmp, "fikstur")
        os.makedirs(os.path.join(kok, "arsiv"))
        with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump(TABAN, f, ensure_ascii=False, indent=2)
        with open(os.path.join(kok, ARSIV_GORELI), "w", encoding="utf-8") as f:
            json.dump([
                {"silinme_ts": "2026-09-01T00:00:00Z", "yazan": "panel-uygulayici",
                 "kuyruk_id": 1, "kayit": KAYIT_ESKI},
                {"silinme_ts": "2026-09-02T00:00:00Z", "yazan": "panel-uygulayici",
                 "kuyruk_id": 2, "kayit": KAYIT_YENI},
            ], f, ensure_ascii=False, indent=2)
        with open(os.path.join(kok, ".diriltme-izin.json"), "w", encoding="utf-8") as f:
            json.dump({"baska-urun#fiyat": "onceki beyan"}, f, ensure_ascii=False, indent=2)
            f.write("\n")

        # V1: geri yukleme — basa eklenir, EN YENI arsiv kaydi kazanir, beyan yazilir.
        rc, cikti = _kos("test-sil", kok, "kobay geri yukleme provasi")
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            taban = json.load(f)
        with open(os.path.join(kok, ".diriltme-izin.json"), encoding="utf-8") as f:
            izin = json.load(f)
        ol("V1a rc=0 + katalog 2->3", rc == 0 and len(taban) == 3, cikti)
        ol("V1b kayit DIZI BASINDA ve EN YENI arsiv surumu",
           taban[0] == KAYIT_YENI, json.dumps(taban[0], ensure_ascii=False))
        ol("V1c komsu kayitlar ayni sirada",
           taban[1]["id"] == "kalan-a" and taban[2]["id"] == "kalan-b")
        ol("V1d diriltme beyani yazildi + onceki beyan KORUNDU",
           "test-sil" in izin and "kuyruk_id=2" in izin["test-sil"]
           and izin.get("baska-urun#fiyat") == "onceki beyan",
           json.dumps(izin, ensure_ascii=False))
        with open(os.path.join(kok, ARSIV_GORELI), encoding="utf-8") as f:
            ol("V1e arsiv dosyasina DOKUNULMADI (2 kayit durur)",
               len(json.load(f)) == 2)

        # V2: id zaten tabanda -> rc!=0, urunler.json BYTE-esit.
        with open(os.path.join(kok, "urunler.json"), "rb") as f:
            once_b = f.read()
        rc, cikti = _kos("test-sil", kok)
        with open(os.path.join(kok, "urunler.json"), "rb") as f:
            sonra_b = f.read()
        ol("V2 ZATEN_TABANDA -> rc!=0 + taban byte-esit",
           rc != 0 and "ZATEN_TABANDA" in cikti and once_b == sonra_b, cikti)

        # V3: arsivde olmayan id -> rc!=0, hicbir dosya degismez.
        rc, cikti = _kos("hic-olmayan-urun", kok)
        with open(os.path.join(kok, "urunler.json"), "rb") as f:
            v3_b = f.read()
        ol("V3 ARSIVDE_YOK -> rc!=0 + taban byte-esit",
           rc != 0 and "ARSIVDE_YOK" in cikti and v3_b == once_b, cikti)

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

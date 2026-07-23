#!/usr/bin/env python3
"""duzelt.py — MEVCUT bir urunun alanini BILEREK degistirmenin TEK yetkili yolu.

urunler-guard.py, HEAD'de var olan urunlerin herhangi bir alani degistiginde onu
otomatik HEAD'e geri dondurur. Mesru bir duzeltme (or. bir urunun fiyatini/
kategorisini bilerek degistirmek) yapmak icin bu araci kullan: degisikligi
.urunler.lock altinda urunler.json'a yazar VE guard'in izin vermesi icin
deger-bagli bir "duzeltme izni" manifesti (.urunler-duzelt-izin.json) uretir.

Guard yalnizca working-tree'deki yeni deger manifeste yazilan deger ile BIREBIR
esitse o alanin degismesine izin verir; beyan disi hicbir alani gecirmez.

Kullanim:
  python3 tools/duzelt.py <id> --alan fiyat --deger "500 TL"
  python3 tools/duzelt.py <id> --alan fiyat --deger "500 TL" --alan kategori --deger Elektronik
  python3 tools/duzelt.py <id> --alan marka --deger '["BMW","Mini"]'   # liste/sozluk icin JSON

Deger cozumleme: '[' veya '{' ile baslayan degerler JSON olarak (liste/sozluk)
ayristirilir; digerleri duz metin kabul edilir (fiyat "500 TL" gibi).
'id' alani degistirilemez.

URUNU TAMAMEN SILMEK icin (or. yanlislikla eklenmis logo/telif riskli urun):
  python3 tools/duzelt.py <id> --sil "kisa gerekce"
Bu, urunu urunler.json'dan kaldirir VE id'yi .urunler-sil-izin.json'a yazar ki
guard onu HEAD'den geri eklemesin. --sil, --alan/--deger ile BIRLIKTE kullanilmaz.

BIR ALANI TAMAMEN KALDIRMAK icin (or. public JSON'da durmamasi gereken alan):
  python3 tools/duzelt.py <id> --alan-sil uyelik
Manifeste {"__alan_sil__": true} sentineli yazilir; guard alanin working-tree'de
YOK olmasini mesru sayar. --alan/--deger ile ayni cagrida birlestirilebilir.

TOPLU (BATCH) KIP — N urun / N alan TEK cagrida, TEK kilit, TEK yazim:
  python3 tools/duzelt.py --toplu islemler.json
islemler.json semasi (ya duz dizi ya da {"islemler": [...]} sarmali):
  [
    {"id": "urun-a", "alan": "fiyat",  "deger": "500 TL"},
    {"id": "urun-a", "alan": "marka",  "deger": ["BMW", "Mini"]},
    {"id": "urun-b", "alan-sil": "uyelik"},
    {"id": "urun-c", "sil": "kisa gerekce"}
  ]
Her islem TEK eylem tasir: ("alan"+"deger") | "alan-sil" | "sil".
CLI'den farkli olarak "deger" HAM JSON degeridir ('[' ile baslama kurali YOK):
liste liste, sozluk sozluk, metin metin olarak yazilir.

ATOMIKLIK: butun islemler ONCE dogrulanir (sema + izinli alan + catisma + id
katalogda var mi). Herhangi biri gecersizse HICBIRI uygulanmaz, urunler.json'a
DOKUNULMAZ, exit != 0 ve reddedilen her islem gerekcesiyle basilir. Hepsi
gecerliyse tek flock altinda tek json.load + tek _atomic_write yapilir; guard
izin manifesti (ve gerekiyorsa silme manifesti) ayni kilit icinde guncellenir —
yani toplu kip de tek-urun kipiyle AYNI guard/koruma yolundan gecer.
"""
import argparse
import datetime
import fcntl
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
MANIFEST = os.path.join(ROOT, ".urunler-duzelt-izin.json")
MANIFEST_SIL = os.path.join(ROOT, ".urunler-sil-izin.json")
LOG = os.path.join(ROOT, ".urunler-guard.log")

DEGISTIRILEBILIR = {"kategori", "marka", "baslik", "aciklama", "fiyat", "gorseller",
                    "lisans", "konfigur"}


def _log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f:
            f.write("[%s] %s\n" % (ts, msg))
    except OSError:
        pass


def _parse_deger(raw):
    s = raw.strip()
    if s[:1] in ("[", "{"):
        return json.loads(s)  # liste/sozluk
    return raw  # duz metin (fiyat, baslik, kategori, ...)


def _atomic_write(path, obj):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _sil(args):
    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
        idx = next((i for i, p in enumerate(urunler)
                    if isinstance(p, dict) and p.get("id") == args.id), None)
        if idx is None:
            print("HATA: '%s' id'li urun urunler.json'da yok." % args.id, file=sys.stderr)
            return 1
        urunler.pop(idx)
        _atomic_write(URUNLER, urunler)

        sil_izin = []
        if os.path.exists(MANIFEST_SIL):
            try:
                with open(MANIFEST_SIL, encoding="utf-8") as f:
                    s = json.load(f)
                if isinstance(s, list):
                    sil_izin = s
            except ValueError:
                sil_izin = []
        if args.id not in sil_izin:
            sil_izin.append(args.id)
        _atomic_write(MANIFEST_SIL, sil_izin)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    _log("sil: %s -> kaldirildi (%s) (silme manifestine yazildi)" % (args.id, args.sil))
    print("Silindi: %s  (gerekce: %s)" % (args.id, args.sil))
    print("Guard bu silmeyi manifest sayesinde gecirir; commit sonrasi post-commit "
          "hook manifesti temizler.")
    return 0


def _manifest_oku(path, bos):
    """Var olan manifesti oku; yoksa/bozuksa `bos` tipini dondur."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, type(bos)):
                return m
        except ValueError:
            pass
    return bos


def _toplu_cozumle(yol):
    """islem.json -> (setler, alan_silmeler, urun_silmeler, hatalar).

    Yalnizca SEMA/izin/catisma dogrulamasi yapar (katalogtan bagimsiz);
    id'nin katalogda var olup olmadigi kilit altinda ayrica denetlenir.
    """
    hatalar = []
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except OSError as e:
        return {}, {}, {}, ["islem dosyasi okunamadi: %s" % e]
    except ValueError as e:
        return {}, {}, {}, ["islem dosyasi gecerli JSON degil: %s" % e]

    if isinstance(veri, dict) and "islemler" in veri:
        veri = veri["islemler"]
    if not isinstance(veri, list):
        return {}, {}, {}, ["islem dosyasi bir dizi (ya da {\"islemler\": [...]}) olmali"]
    if not veri:
        return {}, {}, {}, ["islem dosyasi bos"]

    setler, alan_silmeler, urun_silmeler = {}, {}, {}
    for n, islem in enumerate(veri, 1):
        etiket = "islem #%d" % n
        if not isinstance(islem, dict):
            hatalar.append("%s: obje degil (%r)" % (etiket, islem))
            continue
        uid = islem.get("id")
        if not isinstance(uid, str) or not uid.strip():
            hatalar.append("%s: gecerli 'id' yok" % etiket)
            continue
        etiket = "%s (id=%s)" % (etiket, uid)

        eylem = [k for k in ("alan", "alan-sil", "sil") if k in islem]
        if len(eylem) != 1:
            hatalar.append("%s: tam olarak BIR eylem olmali "
                           "('alan'+'deger' | 'alan-sil' | 'sil'); bulunan: %s"
                           % (etiket, eylem or "hicbiri"))
            continue
        fazla = set(islem) - {"id", "alan", "deger", "alan-sil", "sil", "not"}
        if fazla:
            hatalar.append("%s: bilinmeyen anahtar(lar): %s"
                           % (etiket, ", ".join(sorted(fazla))))
            continue

        if eylem[0] == "alan":
            alan = islem.get("alan")
            if "deger" not in islem:
                hatalar.append("%s: 'alan' verildi ama 'deger' yok" % etiket)
                continue
            if alan == "id":
                hatalar.append("%s: 'id' alani degistirilemez" % etiket)
                continue
            if alan not in DEGISTIRILEBILIR:
                hatalar.append("%s: bilinmeyen/izinsiz alan: %s (izinli: %s)"
                               % (etiket, alan, ", ".join(sorted(DEGISTIRILEBILIR))))
                continue
            onceki = setler.get(uid, {})
            if alan in onceki and json.dumps(onceki[alan], sort_keys=True) != \
                    json.dumps(islem["deger"], sort_keys=True):
                hatalar.append("%s: '%s' alani ayni cagrida FARKLI degerle iki kez verildi"
                               % (etiket, alan))
                continue
            setler.setdefault(uid, {})[alan] = islem["deger"]
        elif eylem[0] == "alan-sil":
            alan = islem.get("alan-sil")
            if not isinstance(alan, str) or not alan.strip():
                hatalar.append("%s: 'alan-sil' bir alan adi olmali" % etiket)
                continue
            if alan == "id":
                hatalar.append("%s: 'id' alani kaldirilamaz" % etiket)
                continue
            alan_silmeler.setdefault(uid, [])
            if alan not in alan_silmeler[uid]:
                alan_silmeler[uid].append(alan)
        else:  # sil
            gerekce = islem.get("sil")
            if not isinstance(gerekce, str) or not gerekce.strip():
                hatalar.append("%s: 'sil' kisa bir gerekce metni olmali" % etiket)
                continue
            urun_silmeler[uid] = gerekce

    # Catismalar: ayni alan hem set hem alan-sil; ya da urun silinirken alan islemi.
    for uid, alanlar in alan_silmeler.items():
        for alan in alanlar:
            if alan in setler.get(uid, {}):
                hatalar.append("id=%s: '%s' hem 'alan' hem 'alan-sil' ile verilemez"
                               % (uid, alan))
    for uid in urun_silmeler:
        if uid in setler or uid in alan_silmeler:
            hatalar.append("id=%s: 'sil' ayni id icin alan islemleriyle birlestirilemez" % uid)

    return setler, alan_silmeler, urun_silmeler, hatalar


def _toplu(yol):
    setler, alan_silmeler, urun_silmeler, hatalar = _toplu_cozumle(yol)
    if hatalar:
        print("HATA: toplu islem REDDEDILDI — hicbir sey yazilmadi.", file=sys.stderr)
        for h in hatalar:
            print("  - %s" % h, file=sys.stderr)
        return 2

    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
        idx_by_id = {}
        for i, p in enumerate(urunler):
            if isinstance(p, dict) and "id" in p:
                idx_by_id.setdefault(p["id"], i)

        yok = [uid for uid in list(setler) + list(alan_silmeler) + list(urun_silmeler)
               if uid not in idx_by_id]
        if yok:
            print("HATA: toplu islem REDDEDILDI — hicbir sey yazilmadi.", file=sys.stderr)
            for uid in sorted(set(yok)):
                print("  - id=%s: urunler.json'da boyle bir urun YOK" % uid, file=sys.stderr)
            return 1

        # --- BURADAN SONRASI YAZIM: tum dogrulamalar gecti. ---
        for uid, alanlar in setler.items():
            for alan, deger in alanlar.items():
                urunler[idx_by_id[uid]][alan] = deger
        for uid, alanlar in alan_silmeler.items():
            for alan in alanlar:
                urunler[idx_by_id[uid]].pop(alan, None)
        if urun_silmeler:
            urunler = [p for p in urunler
                       if not (isinstance(p, dict) and p.get("id") in urun_silmeler)]
        _atomic_write(URUNLER, urunler)  # TEK yazim

        if setler or alan_silmeler:
            manifest = _manifest_oku(MANIFEST, {})
            for uid, alanlar in setler.items():
                manifest.setdefault(uid, {})
                for alan, deger in alanlar.items():
                    manifest[uid][alan] = deger
            for uid, alanlar in alan_silmeler.items():
                manifest.setdefault(uid, {})
                for alan in alanlar:
                    manifest[uid][alan] = {"__alan_sil__": True}
            _atomic_write(MANIFEST, manifest)

        if urun_silmeler:
            sil_izin = _manifest_oku(MANIFEST_SIL, [])
            for uid in urun_silmeler:
                if uid not in sil_izin:
                    sil_izin.append(uid)
            _atomic_write(MANIFEST_SIL, sil_izin)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    n_alan = sum(len(v) for v in setler.values()) + sum(len(v) for v in alan_silmeler.values())
    n_urun = len(set(list(setler) + list(alan_silmeler)) | set(urun_silmeler))
    for uid in sorted(set(list(setler) + list(alan_silmeler))):
        ozet = ", ".join("%s=%s" % (a, json.dumps(v, ensure_ascii=False))
                         for a, v in sorted(setler.get(uid, {}).items()))
        ek = ", ".join("%s=KALDIRILDI" % a for a in sorted(alan_silmeler.get(uid, [])))
        ozet = (ozet + ", " + ek) if (ozet and ek) else (ozet or ek)
        _log("toplu-duzelt: %s -> %s (izin manifestine yazildi)" % (uid, ozet))
        print("Duzeltildi: %s  (%s)" % (uid, ozet))
    for uid, gerekce in sorted(urun_silmeler.items()):
        _log("toplu-sil: %s -> kaldirildi (%s) (silme manifestine yazildi)" % (uid, gerekce))
        print("Silindi: %s  (gerekce: %s)" % (uid, gerekce))
    print("TOPLU: %d urun, %d alan islemi, %d silme — TEK kilit + TEK yazim."
          % (n_urun, n_alan, len(urun_silmeler)))
    print("Guard bu degisiklikleri manifest sayesinde gecirir; commit sonrasi post-commit "
          "hook manifesti temizler.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id", nargs="?",
                    help="degistirilecek/silinecek MEVCUT urun id'si")
    ap.add_argument("--toplu", metavar="ISLEM_JSON",
                    help="N urun/N alani TEK kilit + TEK yazimda uygula "
                         "(tek-urun argumanlariyla birlikte kullanilmaz)")
    ap.add_argument("--alan", action="append",
                    help="degistirilecek alan adi (tekrarlanabilir)")
    ap.add_argument("--deger", action="append",
                    help="yeni deger (her --alan icin bir tane; JSON icin [ veya { ile basla)")
    ap.add_argument("--sil", metavar="GEREKCE",
                    help="urunu TAMAMEN kaldir (--alan/--deger ile birlikte kullanilmaz); "
                         "deger kisa bir gerekce metnidir (log icin)")
    ap.add_argument("--alan-sil", action="append", dest="alan_sil",
                    help="urunden bu ALANI tamamen kaldir (tekrarlanabilir); "
                         "'id' kaldirilamaz")
    args = ap.parse_args()

    if args.toplu is not None:
        if args.id or args.alan or args.deger or args.sil is not None or args.alan_sil:
            print("HATA: --toplu tek-urun argumanlariyla (id/--alan/--deger/--sil/"
                  "--alan-sil) birlikte kullanilamaz.", file=sys.stderr)
            return 2
        return _toplu(args.toplu)

    if args.id is None:
        print("HATA: urun id'si gerekli (ya da --toplu <islem.json>).", file=sys.stderr)
        return 2

    if args.sil is not None:
        if args.alan or args.deger or args.alan_sil:
            print("HATA: --sil, --alan/--deger/--alan-sil ile birlikte kullanilamaz.",
                  file=sys.stderr)
            return 2
        return _sil(args)

    if not (args.alan or args.alan_sil):
        print("HATA: --alan/--deger, --alan-sil veya --sil gerekli.", file=sys.stderr)
        return 2
    if len(args.alan or []) != len(args.deger or []):
        print("HATA: --alan ve --deger sayisi esit olmali.", file=sys.stderr)
        return 2

    degisiklikler = {}
    for alan, deger in zip(args.alan or [], args.deger or []):
        if alan == "id":
            print("HATA: 'id' alani degistirilemez.", file=sys.stderr)
            return 2
        if alan not in DEGISTIRILEBILIR:
            print("HATA: bilinmeyen/izinsiz alan: %s (izinli: %s)"
                  % (alan, ", ".join(sorted(DEGISTIRILEBILIR))), file=sys.stderr)
            return 2
        try:
            degisiklikler[alan] = _parse_deger(deger)
        except ValueError as e:
            print("HATA: '%s' alaninin degeri JSON olarak cozumlenemedi: %s" % (alan, e),
                  file=sys.stderr)
            return 2

    silinecek_alanlar = []
    for alan in args.alan_sil or []:
        if alan == "id":
            print("HATA: 'id' alani kaldirilamaz.", file=sys.stderr)
            return 2
        if alan in degisiklikler:
            print("HATA: '%s' hem --alan hem --alan-sil ile verilemez." % alan,
                  file=sys.stderr)
            return 2
        silinecek_alanlar.append(alan)

    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
        idx = next((i for i, p in enumerate(urunler)
                    if isinstance(p, dict) and p.get("id") == args.id), None)
        if idx is None:
            print("HATA: '%s' id'li urun urunler.json'da yok." % args.id, file=sys.stderr)
            return 1

        # SADECE beyan edilen alanlari degistir; beyan disina dokunma.
        for alan, deger in degisiklikler.items():
            urunler[idx][alan] = deger
        for alan in silinecek_alanlar:
            urunler[idx].pop(alan, None)
        _atomic_write(URUNLER, urunler)

        # Guard icin deger-bagli izin manifesti (birikimli).
        manifest = {}
        if os.path.exists(MANIFEST):
            try:
                with open(MANIFEST, encoding="utf-8") as f:
                    m = json.load(f)
                if isinstance(m, dict):
                    manifest = m
            except ValueError:
                manifest = {}
        manifest.setdefault(args.id, {})
        for alan, deger in degisiklikler.items():
            manifest[args.id][alan] = deger
        for alan in silinecek_alanlar:
            manifest[args.id][alan] = {"__alan_sil__": True}
        _atomic_write(MANIFEST, manifest)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    ozet = ", ".join("%s=%s" % (a, json.dumps(v, ensure_ascii=False))
                     for a, v in degisiklikler.items())
    if silinecek_alanlar:
        ek = ", ".join("%s=KALDIRILDI" % a for a in silinecek_alanlar)
        ozet = (ozet + ", " + ek) if ozet else ek
    _log("duzelt: %s -> %s (izin manifestine yazildi)" % (args.id, ozet))
    print("Duzeltildi: %s  (%s)" % (args.id, ozet))
    print("Guard bu degisikligi manifest sayesinde gecirir; commit sonrasi post-commit "
          "hook manifesti temizler.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

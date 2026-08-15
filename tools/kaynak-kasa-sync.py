#!/usr/bin/env python3
"""Git-disindaki kaynak kayitlarini yalniz yerelden ayri D1 kasasina diff-upsert eder.

Kasa hicbir Worker binding'i kullanmaz. Bu arac hesap kimligi, token veya D1 UUID'si
tutmaz; wrangler'in yerel oturumuyla veritabani ADINI cozer.
"""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile


KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_AD = "pruvo-kaynak-kasa"
TABLO = "kaynak_kasa"
# Tek INSERT 100 kaydi gecmez (D1 ifade tavanina pay); ayni wrangler dosyasinda 10
# ayri INSERT tasinarak surec-baslatma maliyeti 10'da 1'e iner, toplam govde sinirli kalir.
SQL_PARCA = 100
DOSYA_PARCA = 1000


def ana_repo():
    p = subprocess.run(
        ["git", "-C", KOK, "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        raise RuntimeError("ana repo cozulmedi")
    return os.path.dirname(p.stdout.strip().rstrip("/"))


def yerel_oku():
    kok = ana_repo()
    yol = os.path.join(kok, ".urun-kaynaklari.json")
    kilit_yolu = os.path.join(kok, ".urunler.lock")
    if not os.path.isfile(kilit_yolu):
        raise RuntimeError("paylasilan kaynak kilidi yok")
    with open(kilit_yolu, "r+") as kilit:
        fcntl.flock(kilit.fileno(), fcntl.LOCK_SH)
        try:
            with open(yol, "r", encoding="utf-8") as f:
                veri = json.load(f)
        finally:
            fcntl.flock(kilit.fileno(), fcntl.LOCK_UN)
    if not isinstance(veri, dict) or not veri:
        raise RuntimeError("yerel kaynak haritasi bos/gecersiz")
    return {
        str(urun_id): json.dumps(kayit, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"))
        for urun_id, kayit in veri.items()
    }


def komut(args):
    p = subprocess.run(["npx", "--yes", "wrangler@4"] + args, cwd=KOK,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("wrangler rc=%d" % p.returncode)
    return p.stdout


def json_cikti(metin):
    try:
        return json.loads(metin)
    except json.JSONDecodeError:
        # `--file --json` bazi wrangler surumlerinde JSON zarfindan once ilerleme
        # satiri basar. Icerigi loglamadan ilk gecerli liste/nesne zarfi tara.
        cozucu = json.JSONDecoder()
        for n, karakter in enumerate(metin):
            if karakter not in "[{":
                continue
            try:
                veri, _son = cozucu.raw_decode(metin[n:])
            except json.JSONDecodeError:
                continue
            if isinstance(veri, (list, dict)):
                return veri
        raise RuntimeError("wrangler JSON ciktisi cozulmedi")


def db_var_mi():
    veri = json_cikti(komut(["d1", "list", "--json"]))
    return any(isinstance(satir, dict) and satir.get("name") == DB_AD for satir in veri)


def db_olustur():
    if db_var_mi():
        print("KASA=var")
        return "var"
    # `d1 create` JSON bayragi sunmuyor; ciktidaki UUID'yi bilerek okumuyor/basmiyoruz.
    # Basari, ardindan adla yeniden listeleyerek dogrulanir.
    komut(["d1", "create", DB_AD])
    if not db_var_mi():
        raise RuntimeError("kasa olusturma geri-okumasi basarisiz")
    print("KASA=kuruldu")
    return "kuruldu"


def d1(args):
    return json_cikti(komut(["d1", "execute", DB_AD, "--remote", "--json"] + args))


def sql_dosyasi(sql):
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False,
                                     encoding="utf-8") as f:
        f.write(sql)
        yol = f.name
    try:
        return d1(["--file", yol])
    finally:
        os.unlink(yol)


def q(deger):
    return "'" + str(deger).replace("'", "''") + "'"


def sema_kur():
    sql = (
        "CREATE TABLE IF NOT EXISTS kaynak_kasa ("
        "urun_id TEXT PRIMARY KEY NOT NULL,"
        "kayit_json TEXT NOT NULL,"
        "guncellendi TEXT NOT NULL);"
    )
    d1(["--command", sql])


def sonuclar(zarf):
    satirlar = []
    if not isinstance(zarf, list):
        raise RuntimeError("D1 sonucu liste degil")
    for parca in zarf:
        if not isinstance(parca, dict) or parca.get("success") is False:
            raise RuntimeError("D1 sorgusu basarisiz")
        satirlar.extend(parca.get("results") or [])
    return satirlar


def kasa_oku():
    satirlar = sonuclar(d1(["--command", "SELECT urun_id,kayit_json FROM kaynak_kasa;"]))
    return {str(satir["urun_id"]): satir["kayit_json"] for satir in satirlar}


def parcalar(liste, boyut):
    return [liste[n:n + boyut] for n in range(0, len(liste), boyut)]


def yaz_sql(yerel, kimlikler):
    ifadeler = []
    for grup in parcalar(kimlikler, SQL_PARCA):
        degerler = ["(%s,%s,datetime('now'))" % (q(urun_id), q(yerel[urun_id]))
                    for urun_id in grup]
        ifadeler.append(
            "INSERT INTO kaynak_kasa (urun_id,kayit_json,guncellendi) VALUES\n" +
            ",\n".join(degerler) +
            "\nON CONFLICT(urun_id) DO UPDATE SET "
            "kayit_json=excluded.kayit_json,guncellendi=excluded.guncellendi;")
    return "\n".join(ifadeler)


def sil_sql(kimlikler):
    return "DELETE FROM kaynak_kasa WHERE urun_id IN (%s);" % ",".join(q(x) for x in kimlikler)


def durum(yerel):
    sema_kur()
    satirlar = sonuclar(d1(["--command", "SELECT COUNT(*) AS sayi FROM kaynak_kasa;"]))
    if len(satirlar) != 1:
        raise RuntimeError("kasa sayisi olculemedi")
    kasa = int(satirlar[0]["sayi"])
    fark = len(yerel) - kasa
    print("YEREL_KAYIT=%d KASA_KAYIT=%d FARK=%d" % (len(yerel), kasa, fark))
    return 0 if fark == 0 else 1


def senkronla(yerel, kuru=False):
    sema_kur()
    uzak = kasa_oku()
    if uzak and len(yerel) < len(uzak) * 0.50:
        raise RuntimeError("yerel kayit sayisi kasaya gore ciddi dustu; silme reddedildi")
    yazilacak = sorted(urun_id for urun_id, govde in yerel.items()
                      if uzak.get(urun_id) != govde)
    silinecek = sorted(set(uzak) - set(yerel))
    print("YEREL_KAYIT=%d KASA_ONCE=%d UPSERT=%d SIL=%d" %
          (len(yerel), len(uzak), len(yazilacak), len(silinecek)))
    if kuru:
        return 0
    for parca in parcalar(yazilacak, DOSYA_PARCA):
        sql_dosyasi(yaz_sql(yerel, parca))
    for parca in parcalar(silinecek, DOSYA_PARCA):
        sql_dosyasi(sil_sql(parca))
    uzak_son = kasa_oku()
    farkli = sum(1 for urun_id, govde in yerel.items() if uzak_son.get(urun_id) != govde)
    fazla = len(set(uzak_son) - set(yerel))
    print("KASA_KAYIT=%d ICERIK_FARK=%d FAZLA=%d" % (len(uzak_son), farkli, fazla))
    return 0 if farkli == 0 and fazla == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--durum", action="store_true")
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--sema", action="store_true")
    ap.add_argument("--olustur", action="store_true")
    a = ap.parse_args()
    try:
        kasa = db_olustur() if a.olustur else ("var" if db_var_mi() else "yok")
        if kasa == "yok":
            raise RuntimeError("kasa yok; once --olustur")
        yerel = yerel_oku()
        if a.sema:
            sema_kur()
            print("SEMA=hazir YEREL_KAYIT=%d" % len(yerel))
            return 0
        if a.durum:
            return durum(yerel)
        return senkronla(yerel, kuru=a.kuru)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as e:
        print("KASA_HATA=%s NEDEN=%s" % (type(e).__name__, str(e)), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

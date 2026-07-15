#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urunler.json -> Cloudflare D1 (katalog + arama indeksi). FAZ 1.

  python3 tools/d1-sync.py --sema     # semayi kur (bir kez / degisince)
  python3 tools/d1-sync.py            # DIFF-UPSERT: sadece degisen/yeni/silinen
  python3 tools/d1-sync.py --kuru     # hicbir sey yazma, ne yapacagini soyle
  python3 tools/d1-sync.py --durum    # D1'deki urun sayisi + son senkron

*** NEDEN DIFF-UPSERT SART ***
D1 ucretsiz katmanda GUNDE 100.000 SATIR YAZMA siniri var (okuma 100M, depolama 5 GB
— onlar bol). Her push'ta tam rebuild yazilirsa 50k urunde 2 rebuild limiti bitirir,
D1 hata dondurmeye baslar ve ARAMA COKER. Bu yuzden ürünün icerik ozeti (hash)
tutulur; ozeti degismeyen urune DOKUNULMAZ. Gunde ~600 yeni urun = ~600 yazma.

*** SIRA (seq) TUZAGI ***
Yeni urun urunler.json'un BASINA eklenir; dizi indeksini sira yapsaydik her eklemede
TUM urunlerin sirasi kayar, hepsi "degismis" gorunur ve her push tam rebuild olurdu
(yukaridaki limit tam da bu yuzden patlardi). Onun yerine her urune ilk eklendiginde
SABIT bir seq verilir; ORDER BY seq DESC = katalog sirasi (en yeni ustte).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arama

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")

# DB'yi ADIYLA degil UUID'siyle cagiriyoruz: boylece wrangler.toml GEREKMEZ ve bu betik
# hem burada hem GitHub Actions'ta (pruvo-bot repo'su orada yok) AYNI yoldan calisir.
# Actions'ta kimlik: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID ortam degiskenleri;
# yerelde: wrangler'in kendi oturumu (npx wrangler login).
DB = "3d99d15e-2342-4c23-9c2d-cb266f19c1ee"  # pruvo-katalog

# Tek wrangler cagrisina konacak azami ifade sayisi (istek boyutu makul kalsin).
PARCA = 400


def wrangler(args, girdi_dosya=None):
    """wrangler d1 execute calistir, JSON sonucu dondur."""
    komut = ["npx", "--yes", "wrangler@4", "d1", "execute", DB, "--remote", "--json"] + args
    p = subprocess.run(komut, cwd=KOK, capture_output=True, text=True)
    ham = (p.stdout or "") + (p.stderr or "")

    # En sik hata: token'in D1 yetkisi yok. Ham wrangler ciktisi bunu anlatmiyor
    # ("cozulemedi" deyip gecmek, sonraki oturuma sebebi kaybettiriyor) — acikca soyle.
    if "code: 10000" in ham or "Authentication error" in ham:
        sys.exit(
            "D1 KIMLIK HATASI (code 10000) — token D1'e erisemiyor.\n"
            "  Cloudflare panel > My Profile > API Tokens > CLOUDFLARE_API_TOKEN >\n"
            "  Permissions'a **Account > D1 > Edit** ekle. (Mevcut token cache-purge\n"
            "  icin uretilmis, yalnizca zone yetkisi var.)\n"
            "  Site ve Ege bundan ETKILENMEZ; yalnizca D1 katalogu eskir."
        )

    i = p.stdout.find("[")
    if i == -1:
        sys.exit("wrangler cikti vermedi:\n" + ham[-2000:])
    try:
        return json.loads(p.stdout[i:])
    except json.JSONDecodeError:
        sys.exit("wrangler ciktisi cozulemedi:\n" + ham[-2000:])


def sorgu(sql):
    return wrangler(["--command", sql])


def dosya_calistir(sql_metin):
    """Uzun SQL'i gecici dosyaya yazip calistir; (rows_written, rows_read) dondur."""
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as f:
        f.write(sql_metin)
        yol = f.name
    try:
        sonuc = wrangler(["--file", yol])
        yaz = oku = 0
        for r in sonuc:
            m = r.get("meta") or {}
            yaz += m.get("rows_written") or 0
            oku += m.get("rows_read") or 0
        return yaz, oku
    finally:
        os.unlink(yol)


def q(s):
    """SQL metin sabiti — tek tirnak kacisi."""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def urunleri_oku():
    with open(URUNLER, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        sys.exit("urunler.json dizi degil")
    return d


def d1_mevcut():
    """D1'deki {id: hash} + en buyuk seq."""
    r = sorgu("SELECT id, hash FROM urunler")
    satirlar = (r[0].get("results") or []) if r else []
    mevcut = {s["id"]: s["hash"] for s in satirlar}
    r2 = sorgu("SELECT COALESCE(MAX(seq), 0) AS m FROM urunler")
    mseq = ((r2[0].get("results") or [{}])[0] or {}).get("m") or 0
    return mevcut, int(mseq)


def satir_sql(u, seq, hs, h):
    """Tek urun icin upsert. ON CONFLICT -> rid/seq korunur (FTS rowid'i sabit kalir)."""
    g = (u.get("gorseller") or [None])[0]
    return (
        "INSERT INTO urunler (id,hash,seq,baslik,kategori,marka,fiyat,gorsel,parametrik,hs) VALUES ("
        + ",".join([
            q(u["id"]), q(h), str(seq), q(u.get("baslik") or ""), q(u.get("kategori") or ""),
            q(json.dumps(u.get("marka") or [], ensure_ascii=False)), q(u.get("fiyat") or ""),
            q(g), "1" if u.get("parametrik") else "0", q(hs),
        ])
        + ") ON CONFLICT(id) DO UPDATE SET hash=excluded.hash, baslik=excluded.baslik, "
        "kategori=excluded.kategori, marka=excluded.marka, fiyat=excluded.fiyat, "
        "gorsel=excluded.gorsel, parametrik=excluded.parametrik, hs=excluded.hs;"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sema", action="store_true", help="semayi kur")
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    ap.add_argument("--durum", action="store_true", help="D1 durumu")
    a = ap.parse_args()

    if a.sema:
        with open(SEMA, encoding="utf-8") as f:
            yaz, _ = dosya_calistir(f.read())
        print("sema kuruldu (yazilan satir: %d)" % yaz)
        return

    if a.durum:
        r = sorgu("SELECT COUNT(*) AS n FROM urunler")
        n = ((r[0].get("results") or [{}])[0] or {}).get("n")
        r = sorgu("SELECT anahtar, deger FROM senkron")
        print("D1 urun sayisi:", n)
        for s in (r[0].get("results") or []):
            print("  %s = %s" % (s["anahtar"], s["deger"]))
        return

    urunler = urunleri_oku()
    mevcut, mseq = d1_mevcut()
    print("urunler.json: %d urun | D1: %d urun" % (len(urunler), len(mevcut)))

    # TERS gez: dizinin BASI en yeni -> en yuksek seq alsin (ORDER BY seq DESC = katalog sirasi).
    yeni, degisen = [], []
    gorulen = set()
    sonraki = mseq
    for u in reversed(urunler):
        uid = u.get("id")
        if not uid or uid in gorulen:
            continue
        gorulen.add(uid)
        h = arama.urun_hash(u)
        eski = mevcut.get(uid)
        if eski == h:
            continue  # DEGISMEMIS -> yazma yok
        hs = arama.haystack(u)
        if eski is None:
            sonraki += 1
            yeni.append(satir_sql(u, sonraki, hs, h))
        else:
            degisen.append(satir_sql(u, 0, hs, h))  # seq ON CONFLICT'te korunur

    silinen = [i for i in mevcut if i not in gorulen]
    print("yeni: %d | degisen: %d | silinen: %d | dokunulmayan: %d"
          % (len(yeni), len(degisen), len(silinen), len(gorulen) - len(yeni) - len(degisen)))

    if a.kuru:
        print("(--kuru: hicbir sey yazilmadi)")
        return
    if not yeni and not degisen and not silinen:
        print("degisiklik yok — D1'e yazilmadi ✅")
        return

    ifadeler = []
    for parca in [silinen[i:i + PARCA] for i in range(0, len(silinen), PARCA)]:
        ifadeler.append("DELETE FROM urunler WHERE id IN (%s);" % ",".join(q(i) for i in parca))
    ifadeler += degisen + yeni

    top_yaz = 0
    for i in range(0, len(ifadeler), PARCA):
        yaz, _ = dosya_calistir("\n".join(ifadeler[i:i + PARCA]))
        top_yaz += yaz
        print("  parca %d/%d — yazilan satir: %d"
              % (i // PARCA + 1, (len(ifadeler) + PARCA - 1) // PARCA, yaz))

    yaz, _ = dosya_calistir(
        "INSERT INTO senkron (anahtar,deger) VALUES ('urun_sayisi',%s) "
        "ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger;" % q(str(len(gorulen)))
    )
    top_yaz += yaz

    print("TOPLAM yazilan satir: %d (D1 gunluk sinir: 100.000)" % top_yaz)
    if top_yaz > 100000:
        print("!! UYARI: bu tek calisma gunluk yazma limitini asti.")


if __name__ == "__main__":
    main()

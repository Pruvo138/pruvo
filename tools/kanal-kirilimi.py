#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KANAL KIRILIMI RAPORU — siparisler hangi kanaldan/kampanyadan geldi (adet + ciro).

    python3 tools/kanal-kirilimi.py                          # son 30 gun (canli D1, SALT OKUMA)
    python3 tools/kanal-kirilimi.py --baslangic 2026-08-01 --bitis 2026-09-01
    python3 tools/kanal-kirilimi.py --json                    # makine okunur cikti
    python3 tools/kanal-kirilimi.py --sqlite /yol/fikstur.db  # yerel SQLite uzerinden (kabul testi)
    python3 tools/kanal-kirilimi-test.py                      # kabul bataryasi (D1'e DOKUNMAZ)

Cikis kodu: 0 = olculdu · 2 = OLCULEMEDI (fail-closed) · 1 = arac hatasi.

*** SALT OKUMA ***
Bu arac D1'e YALNIZ SELECT/PRAGMA gonderir. Tek D1 istemcisi `tools/d1-sync.py`
(KANONIK okuyucu) ithal edilerek kullanilir — ikinci bir wrangler sarmalayicisi
YAZILMAZ; yazilsaydi biri surum/auth/hata-tanisi konusunda otekinden ayrisir ve
"okuyamadim"i sessizce "veri yok"a cevirebilirdi.

*** KISISEL VERI ***
SELECT listesinde musteri_ad / musteri_tel / musteri_eposta / musteri_adres / musteri_notu
YOKTUR ve siparis_no da CEKILMEZ (kirilim icin gerekmiyor). `atif` govdesinden yalnizca
sinifi belirleyen alanlar okunur; `ga_client_id`/`fbp`/`fbc` ne okunur ne basilir
(kanal-sinifi.js beyaz listesi). Cikti bir kirilim TABLOSUDUR, kayit dokumu DEGIL.

*** 🔴 DORT KOVA — UCUNCUYU/DORDUNCUYU YUTMA ***
Kova listesi de siniflandirma da shop/src/kanal-sinifi.js'ten gelir; bu dosyada elle
yazilmis IKINCI bir kova/esik/etiket listesi YOKTUR. Panelin siparis kartina bastigi
etiket ile buradaki kova AYNI govdeden turer — biri degisirse oteki de degisir.
`atif-yok` AYRI ve ADIYLA GORUNUR bir kovadir: onu sessizce `site-organik`e katlamak,
olculmemis trafigi organik ROI'ye yazar ve raporun TAMAMINI yalan yapar.

*** 🔴 FAIL-CLOSED ***
  * `siparisler.kanal` kolonu canlida YOKSA (goc kosmadi): HUKUM=OLCULEMEDI, rc=2.
    "Kolon yok, demek ki hepsi site" CIKARIMI YASAKTIR — o cikarim, hic olculmemis bir
    kirilimi olculmus gibi gosterir ve yanlisligi hicbir yerde alarm calmaz.
  * Siniflanamayan kanal degeri (yarin eklenecek 'instagram' gibi) tasiyan satir varsa:
    kova sayilarina KATILMAZ, AYRI `OLCULEMEDI` satirinda gorunur ve rc=2. Kirilim
    eksikse "eksik" demek, sessizce tam gibi basmaktan iyidir.
"""
import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SINIFLANDIRICI = os.path.join(KOK, "shop", "src", "kanal-sinifi.js")

HUKUM_OK = "OLCULDU"
HUKUM_OLCULEMEDI = "OLCULEMEDI"

# 🔴 CIROYA GIREN DURUMLAR — ACIK KARAR, ciktida da BEYAN EDILIR.
# 'odendi' ve SONRASI. Disarida kalanlar ve NEDEN:
#   bekliyor / havale-bekliyor : para HENUZ gelmedi (terk edilmis odeme cogunlukla burada)
#   basarisiz / iptal          : para gelmedi ya da geri dondu
#   incele                     : odeme ekseninde ASKIDA (yonet.js ODEME_DURUMLARI) — ciro sayilamaz
# Ciro = tutar_kurus + kargo_kurus (KDV DAHIL tahsilat; shop/src/index.js'in her yerinde
# `beklenenTahsilat` bu ikisinin toplamidir — ucuncu bir tanim URETILMEZ).
CIRO_DURUMLARI = ("odendi", "uretimde", "kargolandi", "tamamlandi")


# ---------------------------------------------------------------- KANONIK D1 OKUYUCU
def _d1_modulu():
    """tools/d1-sync.py'yi modul olarak yukle (tire yuzunden duz `import` calismaz).

    KANONIK okuyucu BUDUR: wrangler cagrisi, hata tanisi, "supheliyi basari sayma"
    kurallari orada TEK yerde yasar."""
    sys.path.insert(0, os.path.join(KOK, "tools"))
    yol = os.path.join(KOK, "tools", "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync_kanal", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def canli_sorgucu():
    """Canli D1 icin sorgu fonksiyonu: sql -> satir sozlukleri listesi."""
    d1 = _d1_modulu()

    def sor(sql):
        sonuc = d1.sorgu(sql)
        # wrangler --json: [{results: [...]}]
        if isinstance(sonuc, list) and sonuc:
            return sonuc[0].get("results") or []
        return []
    return sor


def sqlite_sorgucu(yol):
    """Yerel SQLite dosyasi icin AYNI arayuz (kabul fiksturu + elde tutulan kopya).

    Bu bir test iskelesi DEGIL, aracin teslim edilen bir koludur: kova sayimi, ciro
    kurali, kolon kapisi ve siniflandirma her iki kolda da AYNI govdeden gecer — yalnizca
    satirlarin nereden geldigi degisir."""
    import sqlite3

    def sor(sql):
        baglanti = sqlite3.connect("file:%s?mode=ro" % yol, uri=True)
        try:
            baglanti.row_factory = sqlite3.Row
            return [dict(r) for r in baglanti.execute(sql).fetchall()]
        finally:
            baglanti.close()
    return sor


# ---------------------------------------------------------------- SINIFLANDIRMA (TEK KAYNAK)
_SURUCU = """
import { kanalSinifi, KOVALAR, KOVA_ETIKET } from %s;
let ham = "";
process.stdin.on("data", (p) => { ham += p; });
process.stdin.on("end", () => {
  const satirlar = JSON.parse(ham);
  process.stdout.write(JSON.stringify({
    kovalar: KOVALAR,
    etiketler: KOVA_ETIKET,
    siniflar: satirlar.map((s) => kanalSinifi(s)),
  }));
});
"""


def siniflandir(satirlar, siniflandirici=None):
    """Satirlari KANONIK govdeye (shop/src/kanal-sinifi.js) siniflandirt.

    🔴 Python'da IKINCI bir yuklem YAZILMAZ. Burada yapilan is yalnizca tasima:
    satirlar node'a verilir, kova adlari + etiketler + satir basina sinif geri alinir.
    Bu yuzden kanal-sinifi.js'i bozan bir mutant HEM panel HEM rapor kabul testini
    kirmizi yakar; tek testi yakan bir degisiklik "tek kaynak" olmadigini gosterir.

    Doner: (kovalar, etiketler, siniflar) — `siniflar[i]` None ise OLCULEMEDI.
    """
    js = siniflandirici or SINIFLANDIRICI
    if not os.path.exists(js):
        raise SystemExit("siniflandirici bulunamadi: %s" % js)
    govde = _SURUCU % json.dumps("file://" + js)
    dizin = tempfile.mkdtemp(prefix="kanal-kirilimi-")
    surucu = os.path.join(dizin, "surucu.mjs")
    try:
        with open(surucu, "w", encoding="utf-8") as f:
            f.write(govde)
        p = subprocess.run(["node", surucu], input=json.dumps(satirlar),
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise SystemExit("siniflandirici dustu (rc=%s):\n%s" % (p.returncode, p.stderr[-2000:]))
        veri = json.loads(p.stdout)
    finally:
        # URETEN TEMIZLER: gecici surucu iz birakmaz.
        try:
            os.remove(surucu)
        except OSError:
            pass
        try:
            os.rmdir(dizin)
        except OSError:
            pass
    return veri["kovalar"], veri["etiketler"], veri["siniflar"]


# ---------------------------------------------------------------- OLCUM
def kanal_kolonu_var_mi(sor):
    """PRAGMA ile OLC — varsayma. Doner True/False."""
    satirlar = sor("PRAGMA table_info(siparisler);")
    adlar = {str(r.get("name") or "") for r in satirlar}
    if not adlar:
        # Tablo hic yok / PRAGMA bos: bu da OLCULEMEDI'dir, "kolon yok" DEGIL.
        return None
    return "kanal" in adlar


def satirlari_getir(sor, baslangic, bitis):
    """SALT OKUMA. Kisisel veri kolonlari SELECT'e ALINMAZ."""
    sql = (
        "SELECT kanal, atif, durum, tutar_kurus, kargo_kurus FROM siparisler"
        " WHERE tarih >= '%s' AND tarih < '%s';" % (baslangic, bitis)
    )
    return sor(sql)


def kirilim(satirlar, kovalar, siniflar):
    """Kova -> {adet, ciro_kurus, ciro_disi_adet}. Kovalarin TAMAMI doner (0 olsa bile)."""
    ozet = {k: {"adet": 0, "ciro_kurus": 0, "ciro_disi_adet": 0} for k in kovalar}
    olculemedi = {"adet": 0, "ciro_kurus": 0, "ciro_disi_adet": 0, "kanallar": {}}
    for satir, sinif in zip(satirlar, siniflar):
        hedef = ozet[sinif] if sinif in ozet else olculemedi
        if sinif not in ozet:
            ad = str(satir.get("kanal") or "(bos)")
            olculemedi["kanallar"][ad] = olculemedi["kanallar"].get(ad, 0) + 1
        hedef["adet"] += 1
        if str(satir.get("durum") or "") in CIRO_DURUMLARI:
            hedef["ciro_kurus"] += int(satir.get("tutar_kurus") or 0)
            hedef["ciro_kurus"] += int(satir.get("kargo_kurus") or 0)
        else:
            hedef["ciro_disi_adet"] += 1
    return ozet, olculemedi


def olc(sor, baslangic, bitis, siniflandirici=None):
    """Tam olcum. Doner: rapor sozlugu (`hukum` alani OLCULDU / OLCULEMEDI)."""
    rapor = {"baslangic": baslangic, "bitis": bitis,
             "ciro_durumlari": list(CIRO_DURUMLARI), "hukum": HUKUM_OK, "sebep": ""}
    var = kanal_kolonu_var_mi(sor)
    if var is None:
        rapor["hukum"] = HUKUM_OLCULEMEDI
        rapor["sebep"] = "siparisler tablosu okunamadi (PRAGMA bos)"
        return rapor
    if not var:
        # 🔴 BURADA 'site' VARSAYMA YOK. Goc kosmadiysa kirilim OLCULEMEZ.
        rapor["hukum"] = HUKUM_OLCULEMEDI
        rapor["sebep"] = ("siparisler.kanal kolonu YOK (goc kosmadi) — kirilim olculemez; "
                          "'hepsi site' CIKARIMI YASAK. Cozum: python3 tools/d1-sync.py --sema")
        return rapor
    satirlar = satirlari_getir(sor, baslangic, bitis)
    kovalar, etiketler, siniflar = siniflandir(
        [{"kanal": s.get("kanal"), "atif": s.get("atif")} for s in satirlar], siniflandirici)
    ozet, olculemedi = kirilim(satirlar, kovalar, siniflar)
    rapor["kovalar"] = kovalar
    rapor["etiketler"] = etiketler
    rapor["kirilim"] = ozet
    rapor["olculemedi"] = olculemedi
    rapor["toplam_adet"] = len(satirlar)
    if olculemedi["adet"]:
        rapor["hukum"] = HUKUM_OLCULEMEDI
        rapor["sebep"] = ("%d satirin kanali siniflandirilamadi (%s) — kirilim EKSIK"
                          % (olculemedi["adet"],
                             ", ".join(sorted(olculemedi["kanallar"]))))
    return rapor


# ---------------------------------------------------------------- CIKTI
def tl(kurus):
    return "%.2f TL" % (kurus / 100.0)


def yazdir(rapor):
    print("KANAL KIRILIMI  %s .. %s  (bitis HARIC)" % (rapor["baslangic"], rapor["bitis"]))
    # 🔴 CIRO KURALI CIKTIDA BEYAN EDILIR — okuyan hangi durumlarin sayildigini
    # raporun kendisinden bilsin, kaynak koda gitmek zorunda kalmasin.
    print("CIRO KURALI: durum ∈ {%s} · ciro = tutar + kargo (KDV dahil)"
          % ", ".join(rapor["ciro_durumlari"]))
    print("             'bekliyor'/'havale-bekliyor'/'basarisiz'/'incele'/'iptal' CIROYA GIRMEZ")
    if "kirilim" not in rapor:
        print("HUKUM=%s  %s" % (rapor["hukum"], rapor["sebep"]))
        return
    print("")
    print("%-24s %8s %16s %14s" % ("KOVA", "ADET", "CIRO", "ciro disi"))
    toplam_adet = 0
    toplam_ciro = 0
    for kova in rapor["kovalar"]:
        v = rapor["kirilim"][kova]
        toplam_adet += v["adet"]
        toplam_ciro += v["ciro_kurus"]
        print("%-24s %8d %16s %14d"
              % (kova, v["adet"], tl(v["ciro_kurus"]), v["ciro_disi_adet"]))
    o = rapor["olculemedi"]
    # 🔴 OLCULEMEDI SATIRI DAIMA BASILIR (0 olsa bile): "hic olmadi" ile "hic olcmedim"
    # ayni ekrana cokmesin.
    print("%-24s %8d %16s %14d  %s"
          % ("OLCULEMEDI", o["adet"], tl(o["ciro_kurus"]), o["ciro_disi_adet"],
             ("kanal: " + ", ".join(sorted(o["kanallar"]))) if o["kanallar"] else ""))
    print("%-24s %8d %16s" % ("TOPLAM (kovalar)", toplam_adet, tl(toplam_ciro)))
    print("")
    print("HUKUM=%s%s" % (rapor["hukum"], ("  " + rapor["sebep"]) if rapor["sebep"] else ""))


def _bugun():
    return datetime.datetime.now(datetime.timezone.utc).date()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Siparis kanal/kampanya kirilimi (SALT OKUMA)")
    ap.add_argument("--baslangic", help="YYYY-MM-DD (dahil); varsayilan: 30 gun once")
    ap.add_argument("--bitis", help="YYYY-MM-DD (HARIC); varsayilan: yarin")
    ap.add_argument("--sqlite", help="canli D1 yerine yerel SQLite dosyasi (salt okuma)")
    ap.add_argument("--json", action="store_true", help="makine okunur cikti")
    a = ap.parse_args(argv)

    bitis = a.bitis or (_bugun() + datetime.timedelta(days=1)).isoformat()
    baslangic = a.baslangic or (_bugun() - datetime.timedelta(days=30)).isoformat()
    sor = sqlite_sorgucu(a.sqlite) if a.sqlite else canli_sorgucu()
    rapor = olc(sor, baslangic, bitis)
    if a.json:
        print(json.dumps(rapor, ensure_ascii=False, indent=1, sort_keys=True))
    else:
        yazdir(rapor)
    return 0 if rapor["hukum"] == HUKUM_OK else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KANAL KIRILIM RAPORU — siparisler hangi kanaldan/hangi reklamdan geldi (adet + ciro).

  python3 tools/kanal-kirilim-raporu.py
  python3 tools/kanal-kirilim-raporu.py --baslangic 2026-08-01 --bitis 2026-08-31

NE ISE YARAR: `siparisler.atif` (utm_* / ref) ve `siparisler.kanal` verisi TOPLANIYORDU
ama hicbir yerde GORUNMUYORDU — panelde basilmiyor, tools/ altinda okuyan bir raporlayici
yoktu. Bu rapor o veriyi kovalara ayirir: reklam parasinin karsiligini gorunur kilar.

🔴 SINIFLAMA BURADA YAZILI DEGIL. Kovalar, etiketler, ciro durumlari ve kanal/atif
yargisinin TAMAMI shop/src/kanal-sinif.mjs'ten gelir (tools/kanal-sinif-cli.mjs koprusu
ile). Yonetim panelinin "Kaynak" satiri da AYNI fonksiyondan turer; boylece ekranin
"organik" dedigi siparis raporda da organiktir. Python tarafinda ikinci bir sozluk
ACILMAZ ([[ayni-alan-iki-hukum-biri-sessiz]]).

🔴 FAIL-CLOSED — `kanal` KOLONU YOKSA HUKUM `OLCULEMEDI` (rc=3, sifir-disi).
"Kolon yok, demek hepsi site" cikarimi YASAKTIR: goc kosmadan once de WhatsApp
siparisleri bu tabloda olabilir; hepsini 'site' saymak site ROI'sini sessizce sisirir.
Ayni sinif: [[iki-kovali-siniflama-ucuncu-sinifi-yutar]].

🔒 GIZLILIK: rapor MUSTERI ALANI OKUMAZ (ad/tel/eposta/adres SELECT'e GIRMEZ) ve
ga_client_id/fbp/fbc'yi BASMAZ (kanal-sinif.mjs pozitif beyaz-listesi). Ciktida siparis
NUMARASI da yoktur — bu bir TOPLAM raporudur, kisi raporu degil.

CANLI D1'e YAZMA YOK: yalnizca SELECT + PRAGMA (tools/d1-sync.py kanonik istemcisi;
ikinci wrangler sarmalayicisi yazilmadi).

CIKIS KODU: 0 rapor uretildi · 2 kullanim/ortam hatasi · 3 OLCULEMEDI (fail-closed).
"""
import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
KOPRU = os.path.join(TOOLS, "kanal-sinif-cli.mjs")

RC_TAMAM = 0
RC_ORTAM = 2
RC_OLCULEMEDI = 3

def tarih_gecerli(deger):
    """🔴 KALIP YETMEZ, TAKVIM GEREKIR. Ilk surumde `^\\d{4}-\\d{2}-\\d{2}$` kullanildi ve
    `--baslangic 2026-13-01` (13. ay) SUZGECTEN GECTI: SQL dizge kiyasi hicbir satirla
    eslesmedi, rapor da "HUKUM=TAMAM · 0 satir" bastı. Yani yazim hatasi, "o aralikta
    siparis yok" gibi GORUNDU — sessiz sifir, yanlis sayidan beter. Takvim dogrulamasi
    bunu kullanim hatasina (rc=2) cevirir."""
    try:
        datetime.date.fromisoformat(deger)
        return True
    except ValueError:
        return False


# ── KANONIK D1 ISTEMCISI (tools/d1-sync.py) ───────────────────────────────────
# Modul adi tire tasiyor -> duz `import` calismaz (ara-maliyet-kapisi.py ile ayni desen).
def d1_modulu():
    yol = os.path.join(TOOLS, "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync_kanal_raporu", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # SOZLESME SEMBOLLERI: adlari degisirse burasi PATLAR (sessizce eski yola dusmez).
    for ad in ("sorgu", "kolon_var_mi"):
        if not hasattr(mod, ad):
            raise RuntimeError("d1-sync.py `%s` sunmuyor" % ad)
    return mod


# ── KOVA SOZLUGU (JS TEK KAYNAGINDAN) ─────────────────────────────────────────
def sozluk():
    """Kova adlari/etiketleri + ciro durumlari — shop/src/kanal-sinif.mjs'ten."""
    p = subprocess.run(["node", KOPRU, "--sozluk"], cwd=KOK,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("kova sozlugu alinamadi (rc=%s): %s"
                           % (p.returncode, (p.stderr or "")[-300:]))
    return json.loads(p.stdout)


def siniflandir(satirlar):
    """Satirlari TEK node cagrisiyla siniflandir. Girdi/cikti ayni sirada, ayni uzunlukta."""
    if not satirlar:
        return []
    girdi = json.dumps([
        # Kopruye YALNIZ karar icin gereken 4 alan gider; musteri alani hic tasinmaz.
        # `kanal` anahtari YOKSA gonderilmez -> JS tarafi 'kanal-olculemedi' der.
        {k: s[k] for k in ("kanal", "atif", "durum", "tutar_kurus", "kargo_kurus")
         if k in s and s[k] is not None}
        for s in satirlar
    ], ensure_ascii=False)
    p = subprocess.run(["node", KOPRU, "--sinifla"], cwd=KOK, input=girdi,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("siniflama koprusu dustu (rc=%s): %s"
                           % (p.returncode, (p.stderr or "")[-300:]))
    sonuc = json.loads(p.stdout)
    if len(sonuc) != len(satirlar):
        raise RuntimeError("siniflama uzunlugu uyusmuyor: %d girdi / %d cikti"
                           % (len(satirlar), len(sonuc)))
    return sonuc


# ── D1 OKUMASI ────────────────────────────────────────────────────────────────
def d1_satirlari(d1, baslangic, bitis):
    """(satirlar, kanal_kolonu_var). 🔴 KOLON MERDIVENI YOK (yonet.js'teki OKUMA
    yolundan bilerek AYRI): panel goc oncesi de ayakta kalmali, RAPOR ise yanlis
    sayidansa HIC SAYI vermemelidir. Kolon yoksa SELECT bile kurulmaz."""
    if not d1.kolon_var_mi("siparisler", "kanal"):
        return [], False
    kosullar = []
    if baslangic:
        kosullar.append("tarih >= '%s'" % baslangic)
    if bitis:
        # `tarih` ISO damgasi (2026-08-31T12:00:00Z) -> gun SONUNA kadar kapsa diye
        # bitis gununun kendisi DAHIL: '<= <bitis>T23:59:59Z' yerine '< ertesi gun'
        # yazmak yerine dizge kiyasi ile gun sonunu acikca yaziyoruz.
        kosullar.append("tarih <= '%sT23:59:59Z'" % bitis)
    nere = (" WHERE " + " AND ".join(kosullar)) if kosullar else ""
    # 🔒 Musteri alanlari (ad/tel/eposta/adres) BILEREK SELECT'E GIRMEZ.
    sql = ("SELECT tarih, durum, tutar_kurus, kargo_kurus, kanal, atif"
           " FROM siparisler%s ORDER BY tarih" % nere)
    r = d1.sorgu(sql)
    return ((r[0].get("results") or []) if r else []), True


# ── HUKUM (SAF — I/O YOK; test bunu DOGRUDAN cagirir) ─────────────────────────
def hukum(satirlar, kanal_kolonu_var, siniflar, soz, aralik_metni):
    """Rapor metnini + cikis kodunu uret. Saftir: ayni girdi -> ayni cikti."""
    satir = []
    ekle = satir.append
    ekle("KANAL KIRILIM RAPORU — pruvo siparisleri")
    ekle("=" * 70)
    ekle("Tarih araligi : %s" % aralik_metni)

    if not kanal_kolonu_var:
        # 🔴 FAIL-CLOSED. Sayi URETILMEZ — yanlis sayi, sayisizliktan kotudur.
        ekle("")
        ekle("HUKUM=OLCULEMEDI  SEBEP=siparisler.kanal KOLONU CANLI D1'DE YOK")
        ekle("")
        ekle("  `kanal` kolonu olmadan bir siparisin site mi WhatsApp mi oldugu")
        ekle("  BILINEMEZ. 'Kolon yok, demek hepsi site' cikarimi bu raporda YASAKTIR:")
        ekle("  site kovasini olculmemis WhatsApp siparisleriyle sisirirdi.")
        # 🔴 `ISCIYE:` isareti ZORUNLU (1 Eyl 2026, KraL-Tamirci-1Eyl). `recete-kapisi.py`
        # her CARE/COZUM recetesini `mimar-icra-kapisi`ne SORAR: mimar tarafinda serbest
        # python cagrilari kapali bir kumedir ve `d1-sync.py --sema` o kumede DEGILDIR.
        # Isaretsiz hali RECETE-RED uretiyordu, yani kapi "bu care mimarin
        # KOSAMAYACAGI bir komut" diyerek `serit-b`yi kirmiziya yakiyordu (CI kosumu
        # 33445049998: `RECETE=9 REDDEDILEN=1`). Isaret, kararin OKUDUGU TEK KAYNAKTAN
        # turer ve komutu ucuz kata devreder — kardes araclarin (sema-bundle-kapisi,
        # konfigur-bundle-kapisi, yasal-sayfa-drift-kapisi) kullandigi ayni idiom.
        # Goc ADDITIVE + idempotenttir (mevcut tabloda CREATE atlanir, eksik kolon
        # ALTER ile tamamlanir) — yine de canli D1'e dokundugu icin kosum karari
        # mimarin/Okan'in kalir; bu isaret yalnizca receteyi KOSULABILIR yapar.
        ekle("  COZUM: ISCIYE: python3 tools/d1-sync.py --sema")
        ekle("  (kanal kolonu gocu) kosulsun, sonra bu rapor tekrar calistirilsin.")
        ekle("  KOVA ADI (gorunur kalsin diye): %s" % soz["kova_kanal_olculemedi"])
        return "\n".join(satir), RC_OLCULEMEDI

    ciro_durumlari = soz["ciro_durumlari"]
    ekle("Toplam siparis: %d satir" % len(satirlar))
    if not satirlar:
        # SESSIZ SIFIR YASAK: bos tablo "hic siparis yok" ile "aralik/suzgec yanlis"i
        # ayni bos ekrana dusururdu. Durum ACIKCA yazilir (hata DEGIL, ama gorunur).
        ekle("  ⚠️ BU ARALIKTA HIC SIPARIS YOK — tablo bos degil, ARALIK bos.")
        ekle("     (Tarih suzgecini genislet ya da bayraksiz kos: tum siparisler.)")
    ekle("")
    ekle("BEYAN — CIROYA HANGI DURUMLAR GIRIYOR (karar acik yazilir):")
    ekle("  GIRER : %s" % ", ".join(ciro_durumlari))
    ekle("  GIRMEZ: bekliyor, havale-bekliyor, incele, basarisiz, iptal")
    ekle("          ('bekliyor' odeme bitmedi · 'iptal' vazgecildi -> ciroyu sisirirdi)")
    ekle("  CIRO   = tutar_kurus + kargo_kurus (musterinin odedigi TAHSILAT;")
    ekle("           shop/src/index.js beklenenTahsilat ile AYNI formul)")
    ekle("")

    # Kovalari HER ZAMAN TAM listeyle bas (sifir olani da). Basilmayan kova, var
    # olmayan kovadan ayirt edilemez -> okuyan "o durum hic olmadi" saniyor.
    sayac = {k: {"adet": 0, "ciro_adet": 0, "ciro_kurus": 0, "sebepler": {}}
             for k in soz["kovalar"]}
    bilinmeyen_kova = {}
    for s in siniflar:
        kova = s.get("kova")
        hedef = sayac.get(kova)
        if hedef is None:
            # JS'e YENI bir kova eklenip Python tarafi guncellenmezse burasi GORUNUR
            # olur (sessizce bir kovaya yazilmaz) — [[yeni-hal-cozucunun-varsayilan-kovasina-duser]].
            bilinmeyen_kova[kova] = bilinmeyen_kova.get(kova, 0) + 1
            continue
        hedef["adet"] += 1
        sebep = s.get("sebep") or "-"
        hedef["sebepler"][sebep] = hedef["sebepler"].get(sebep, 0) + 1
        if s.get("ciroya_girer"):
            hedef["ciro_adet"] += 1
            hedef["ciro_kurus"] += int(s.get("tahsilat_kurus") or 0)

    ekle("%-24s %8s %10s %16s" % ("KOVA", "ADET", "CIRO_ADET", "CIRO (TL)"))
    ekle("-" * 70)
    t_adet = t_ciro_adet = t_ciro = 0
    for kova in soz["kovalar"]:
        v = sayac[kova]
        ekle("%-24s %8d %10d %16s"
             % (kova, v["adet"], v["ciro_adet"], tl(v["ciro_kurus"])))
        t_adet += v["adet"]
        t_ciro_adet += v["ciro_adet"]
        t_ciro += v["ciro_kurus"]
    ekle("-" * 70)
    ekle("%-24s %8d %10d %16s" % ("TOPLAM", t_adet, t_ciro_adet, tl(t_ciro)))

    ekle("")
    ekle("TESHIS — hangi eksenden karar cikti (kova basina sebep dagilimi):")
    for kova in soz["kovalar"]:
        v = sayac[kova]
        if not v["adet"]:
            continue
        detay = ", ".join("%s=%d" % (a, n)
                          for a, n in sorted(v["sebepler"].items(),
                                             key=lambda x: (-x[1], x[0])))
        ekle("  %-24s %s" % (kova, detay))

    rc = RC_TAMAM
    if bilinmeyen_kova:
        ekle("")
        ekle("HUKUM=OLCULEMEDI  SEBEP=SINIFLAYICI TANIMADIGIM KOVA DONDU")
        for k, n in sorted(bilinmeyen_kova.items()):
            ekle("  bilinmeyen kova %r -> %d satir (hicbir toplama KATILMADI)" % (k, n))
        ekle("  Kova listesi shop/src/kanal-sinif.mjs KOVALAR'dan gelir; oraya yeni")
        ekle("  kova eklendiyse bu rapor onu tanimadan sayi URETMEZ.")
        rc = RC_OLCULEMEDI
    else:
        ekle("")
        ekle("HUKUM=TAMAM  (kova sayisi=%d · siniflanan satir=%d)"
             % (len(soz["kovalar"]), len(siniflar)))
    return "\n".join(satir), rc


def tl(kurus):
    k = max(0, int(kurus or 0))
    return "%d,%02d" % (k // 100, k % 100)


def main():
    ap = argparse.ArgumentParser(description="Kanal kirilim raporu (adet + ciro).")
    ap.add_argument("--baslangic", default="", help="YYYY-MM-DD (dahil)")
    ap.add_argument("--bitis", default="", help="YYYY-MM-DD (dahil)")
    a = ap.parse_args()

    for ad, deger in (("--baslangic", a.baslangic), ("--bitis", a.bitis)):
        if deger and not tarih_gecerli(deger):
            print("KULLANIM HATASI: %s GECERLI bir takvim gunu olmali (YYYY-MM-DD) "
                  "— verilen: %r" % (ad, deger))
            return RC_ORTAM
    if a.baslangic and a.bitis and a.baslangic > a.bitis:
        print("KULLANIM HATASI: --baslangic > --bitis")
        return RC_ORTAM

    aralik = "%s .. %s" % (a.baslangic or "(basi yok)", a.bitis or "(sonu yok)")

    try:
        soz = sozluk()
    except Exception as e:
        print("HUKUM=OLCULEMEDI  SEBEP=kova sozlugu alinamadi: %s" % e)
        return RC_OLCULEMEDI
    try:
        d1 = d1_modulu()
        satirlar, kolon_var = d1_satirlari(d1, a.baslangic, a.bitis)
    except SystemExit as e:
        # d1-sync.py wrangler hatasinda sys.exit eder; rapor onu OLCULEMEDI'ye cevirir
        # (sessizce bos liste ile devam etmek "0 siparis" YALANINI uretirdi).
        print("HUKUM=OLCULEMEDI  SEBEP=D1 okunamadi (d1-sync cikti: %s)" % e)
        return RC_OLCULEMEDI
    except Exception as e:
        print("HUKUM=OLCULEMEDI  SEBEP=D1 okunamadi: %s" % e)
        return RC_OLCULEMEDI

    try:
        siniflar = siniflandir(satirlar) if kolon_var else []
    except Exception as e:
        print("HUKUM=OLCULEMEDI  SEBEP=siniflama yapilamadi: %s" % e)
        return RC_OLCULEMEDI

    metin, rc = hukum(satirlar, kolon_var, siniflar, soz, aralik)
    print(metin)
    return rc


if __name__ == "__main__":
    sys.exit(main())

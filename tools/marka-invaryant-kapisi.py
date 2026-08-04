#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA INVARYANT KAPISI — "sayfa ile arama AYNI urunu gostermeli" (TABAN CIVILI).

OKAN HUKMU: "TUM markalarda sayfa ve arama urun adetlerinin ayni olmasi." Bu kapi o
hukmun tek tek yama DEGIL, INVARYANT olarak olculdugu yerdir.

═══ NE OLCULUR ═══════════════════════════════════════════════════════════════════
Her kanonik marka `b` icin UC kume kurulur ve ikili farklari sayilir:

  SAYFA  (b)  /marka/<slug>/ sayfasinin gosterdigi urunler.
              KAYNAK: marka_model_build.gruplandir + marka_urun_sayisi (TEK KAYNAK —
              ikinci bir toplama formulu YAZILMAZ; S ekseni bunu kilitler).
  FILTRE (b)  Uctaki (Worker) `?marka=b` kolunun DONDURDUGU kume — HAM STRING ESITLIGI:
              `b in (urun.marka or [])`. Katlama YOK (uc `markaKatla` CAGIRMIYOR).
  ARAMA  (b)  Serbest metin `?q=b` kolunun donduru kume — arama.haystack/tokenlar/esles
              (site `filtered()` portu; KATI AND + ALT-DIZE).

  FILTRE_KAYIP(b) = |SAYFA − FILTRE|   🔴 MUSTERI CIPE BASINCA URUNU KAYBEDER
  FILTRE_FAZLA(b) = |FILTRE − SAYFA|   (yapisal olarak 0 olmali — asagida)
  ARAMA_KAYIP (b) = |SAYFA − ARAMA|    🔴 URUN SAYFADA VAR, ARAMADA YOK
  ARAMA_FAZLA (b) = |ARAMA − SAYFA|    (gurultu ekseni — BLOKLAMAZ, bkz. ne_olculmedi)

═══ MODEL AGA CIKMAZ — AMA CANLIYLA BIR KEZ ESLESTIRILDI ═════════════════════════
Kapi CI'da deterministik olmak zorunda oldugu icin uc davranisini YEREL PORTLA modeller.
Modelin canliyla ayni sonucu verdigi 4 Agu 2026'da OLCULDU (katalog 18.080 urun,
128 kanonik marka; canli olcum bagimsiz bir olcum iscisi tarafindan pruvo3d.com uzerinden
alindi ve `marka-canli-edge.tsv` olarak kaydedildi):

    canli `?marka=` (128 marka)  ↔  buradaki HAM-ESITLIK modeli   : 128/128 BIREBIR
    canli `?q=`     (128 marka)  ↔  buradaki arama.py portu       : 128/128 BIREBIR
    canli marka sayfasi adedi    ↔  marka_urun_sayisi             : 128/128 BIREBIR

Yani "sayfa 726 · cip 620" gibi 9 markadaki 120 kalemlik kayip bu modelde BIREBIR yeniden
uretildi. Model canliyla AYRISABILIR (uc kodu bu depoda DEGIL) — bu sinir ne_olculmedi()'de
ACIKCA ILAN EDILIR.

═══ NEDEN TABAN CIVILI (mevcut borc bloklamaz, REGRESYON bloklar) ═════════════════
Olculen borc (4 Agu): FILTRE_KAYIP 9 marka / 120 kalem · ARAMA_KAYIP 2 marka / 4 kalem.
Bu borcu bugun kirmizi yakan bir kapi TUM ekibin yayinini durdururdu ve borcu KAPATMAZDI
([[kapi-birikimi-yayin-gecikmesi]]). Bu yuzden bugunku degerler `marka-invaryant-taban.json`
dosyasina MARKA MARKA civilenir; kapi yalnizca sayi TABANIN USTUNE CIKARSA kirmizi yanar.

🔴 CIRCIR (ratchet) — DUSUS DE KIRMIZIDIR: olculen deger tabanin ALTINA inerse kapi
DURUR ve tabanin guncellenmesini ister. Gerekcesi [[beyan-edilmis-survivor]]: taban
gevsek kalirsa borc kapandiktan SONRA aynen geri gelebilir ve kapi YESIL yanar — yani
kapinin tek degeri (civi) kaybolur. Dusus URUN EKLEMEYLE OLUSMAZ (yeni urun bir markanin
kaybini artirabilir, azaltamaz); yalnizca ONARIM ya da urun SILME dusurur, ikisi de
kasitlidir. Cozum tek satir: `python3 tools/marka-invaryant-kapisi.py --taban-yaz`.

🔴 NEDEN AGREGE DEGIL MARKA MARKA: toplam, tekil ekseni gizler ([[hukum-yanlis-birimde]]).
Volvo 106 → 96 inerken Ford 0 → 10 ciksa toplam AYNI kalir ve kapi YESIL yanardi.

🔴 NEDEN ADET DEGIL KUME: "sayfa 726 · arama 734" gibi bir SAYI farki, iki kumenin
birbirini kismen kacirdigini gizler (Opel'de olculdu: adet farki −4, ama sayfada olup
aramada OLMAYAN 3 + aramada olup sayfada olmayan 7). Kume farki iki YONU AYRI olcer.

═══ TOTOLOJI TUZAGI VE POZITIF CAPA ═══════════════════════════════════════════════
Iki ucu da AYNI fonksiyondan turetirsek kapi HER ZAMAN yesil yanar. Uc savunma:
  1. FILTRE modeli BILEREK baska bir yuklem kullanir (ham esitlik) — katlama CAGIRMAZ.
  2. POZITIF CAPA: adi civili, katlama OLMADAN uye OLAMAYACAK 5 gercek urun, kendi
     markasinin HEM sayfasinda HEM aramasinda BULUNMALI ve katalogda TAM BIR KEZ gecmeli.
     Katlama kapatilirsa capalar SAYFA kumesinden duser -> kapi kirmizi.
  3. S EKSENI: kurulan SAYFA kumesinin buyuklugu, deponun kanonik sayma fonksiyonu
     (marka_urun_sayisi) ile BIREBIR esit olmali — ikinci bir toplama formulu dogamaz.
Mutasyon kaniti REPODA KOSULABILIR: tools/marka-invaryant-mutasyon.py
([[mutasyon-kaniti-yeniden-uretilebilir]] — anlatilan batarya kanit DEGILDIR).

Calistir:  python3 tools/marka-invaryant-kapisi.py        (0 yesil · 1 kirmizi · 2 olculemedi)
           python3 tools/marka-invaryant-kapisi.py --taban-yaz     (tabani YENIDEN yaz)
           python3 tools/marka-invaryant-kapisi.py --modul /gecici/mutant.py   (mutasyon)
"""
import argparse
import importlib.util
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

TABAN_VARSAYILAN = os.path.join(TOOLS, "marka-invaryant-taban.json")

# ── POZITIF CAPA ────────────────────────────────────────────────────────────────
# (urun id, kanonik marka, katlamanin TURU). Her biri OLCULDU (4 Agu): urunun `marka`
# dizisi kanonik adi HAM olarak TASIMAZ -> uyelik yalnizca katlamayla dogar. Bes ayri
# katlama mekanizmasi secildi ki tek bir mekanizmayi kapatan mutant capayi kacirmasin.
CAPALAR = [
    ("sierra-hava-filtresi-18-7908", "Volvo", "onek katlamasi (Volvo Penta -> Volvo)"),
    ("peugeot-citroen-2-pinli-elektrik-konnektoru", "Citroen", "aksan (Citroen yazimi)"),
    ("black-decker-zimpara-vakum-adaptoru", "Black+Decker", "ayirac (and/& /+ tek bicim)"),
    ("hyundai-ve-kia-g-s-paneli-klipsi", "Kia", "buyuk/kucuk harf (KIA -> Kia)"),
    ("datsun-mido-far-arka-kapagi", "Datsun", "onek katlamasi (Datsun MiDo -> Datsun)"),
]

FAILS = []
BILGI = []


def kontrol(ad, kosul):
    if kosul:
        print("  PASS  " + ad)
    else:
        FAILS.append(ad)
        print("  FAIL  " + ad)


def olculemedi(sebep):
    print("\nSONUC: OLCULEMEDI ❓  " + sebep)
    sys.exit(2)


def ne_olculmedi():
    """BEYAN — bu kapinin GORMEDIGI eksenler. Sessiz kalmasin diye HER kosumda basilir."""
    print("\nNE OLCULMEDI (beyan):")
    print("  1. CANLI UC KODU. Worker (`?marka=` / `?q=` kollari) BU DEPODA DEGIL. Kapi")
    print("     onun davranisini YEREL PORTLA modeller. Model 4 Agu'da canliyla 128/128")
    print("     eslesti; uc kodu degisirse model SESSIZCE ayrisabilir. O ekseni ancak")
    print("     canli olcum kapatir (ag cagrisi CI'da deterministik degildir).")
    print("  2. ARAMA_FAZLA (serbest metinde SAYFADAN FAZLA cikan urun; bugun 6.449 kalem)")
    print("     BLOKLAMAZ, yalnizca BASILIR. Sebep: bu sayi gurultu kesimi fazinin isidir")
    print("     (Havalandirma->'Haval', Mandali->'MAN', 33mm->'3M') ve KATALOG BUYUDUKCE")
    print("     kendiliginden artar — civilenseydi her urun partisi kapiyi kirmizi yakardi.")
    print("     Bu paket serbest metin arama semantigine DOKUNMAZ (mimar sinirı).")
    print("  3. D1 `marka_kanon` KOLONUNUN CANLI DEGERI. Kapi urunler.json'dan turetilen")
    print("     HEDEF degeri olcer; canli D1'de ne yazdigini OLCMEZ (o `d1-sync --durum`).")


# ── kaynaklar ───────────────────────────────────────────────────────────────────
def modul_yukle(yol):
    spec = importlib.util.spec_from_file_location("mmb_invaryant", yol)
    if spec is None:
        olculemedi("marka_model_build modulu yuklenemedi: %s" % yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def olc(mmb, arama, urunler, index_html):
    """Uc kumeyi kur. Doner: (veri, {marka: (sayfa, filtre, arama)} kume uclusu)."""
    evren = mmb.MarkaEvreni(index_html)
    ek = mmb.cip_evreni_markalari(urunler, index_html)
    veri = mmb.gruplandir(urunler, evren, ek)

    hs = [(p.get("id"), arama.haystack(p)) for p in urunler]
    kumeler = {}
    for marka, d in veri.items():
        sayfa = set()
        for kaynak in ([g["urunler"] for g in d["gruplar"].values()]
                       + [d["marka_only"], d.get("ikincil", [])]):
            for p in kaynak:
                if p.get("id"):
                    sayfa.add(p["id"])
        # UCTAKI `?marka=` KOLU — HAM STRING ESITLIGI (katlama YOK). Bu yuklem BILEREK
        # sayfa yukleminden BAGIMSIZ yazildi (totoloji tuzagi).
        filtre = {p["id"] for p in urunler
                  if p.get("id") and marka in (p.get("marka") or [])}
        tok = arama.tokenlar(marka)
        srch = {i for i, h in hs if i and arama.esles(h, tok)}
        kumeler[marka] = (sayfa, filtre, srch)
    return veri, kumeler


def taban_kur(veri, kumeler, katalog):
    fk, ff, ak, af = {}, {}, {}, {}
    for marka, (sayfa, filtre, srch) in kumeler.items():
        if sayfa - filtre:
            fk[marka] = len(sayfa - filtre)
        if filtre - sayfa:
            ff[marka] = len(filtre - sayfa)
        if sayfa - srch:
            ak[marka] = len(sayfa - srch)
        if srch - sayfa:
            af[marka] = len(srch - sayfa)
    return {
        "_not": ("MARKA INVARYANT TABANI — bugunku BORC buraya civilendi; kapi yalnizca "
                 "sayi ARTARSA kirmizi yanar. Dusus de kirmizidir (circir): borc "
                 "kapandiktan sonra sessizce geri gelmesin. Guncelleme: "
                 "python3 tools/marka-invaryant-kapisi.py --taban-yaz"),
        "_olcum": ("4 Agu 2026 · katalog %d urun · canli uc ile 128/128 birebir eslesti "
                   "(marka sayfasi / ?marka= / ?q= ucu ayri ayri)" % katalog),
        "marka_sayisi": len(veri),
        "filtre_kayip": dict(sorted(fk.items())),
        "filtre_fazla": dict(sorted(ff.items())),
        "arama_kayip": dict(sorted(ak.items())),
        "arama_fazla_toplam_BLOKLAMAZ": sum(af.values()),
    }


def eksen_karsilastir(ad, olculen, taban):
    """Bir ekseni MARKA MARKA tabanla karsilastir. Doner: (artan, azalan) listeleri."""
    artan, azalan = [], []
    for marka in sorted(set(olculen) | set(taban)):
        o, t = olculen.get(marka, 0), taban.get(marka, 0)
        if o > t:
            artan.append((marka, t, o))
        elif o < t:
            azalan.append((marka, t, o))
    return artan, azalan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modul", default=os.path.join(TOOLS, "marka_model_build.py"),
                    help="marka_model_build.py yolu (mutasyon kaniti icin)")
    ap.add_argument("--taban", default=TABAN_VARSAYILAN)
    ap.add_argument("--taban-yaz", action="store_true",
                    help="olculen degerleri TABAN dosyasina yaz (circir guncellemesi)")
    a = ap.parse_args()

    try:
        import arama                                              # noqa: PLC0415
        mmb = modul_yukle(a.modul)
        with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
    except SystemExit:
        raise
    except Exception as e:                                        # noqa: BLE001
        olculemedi("kaynaklar okunamadi (%s: %s)" % (type(e).__name__, e))

    try:
        veri, kumeler = olc(mmb, arama, urunler, index_html)
    except SystemExit as e:
        olculemedi("olcum kosulamadi (SystemExit: %s)" % (e.code,))
    except Exception as e:                                        # noqa: BLE001
        olculemedi("olcum kosulamadi (%s: %s)" % (type(e).__name__, e))
    if not veri:
        olculemedi("marka evreni BOS — katlama/kuratorluk tek kaynagi okunamamis olabilir")

    olculen = taban_kur(veri, kumeler, len(urunler))

    if a.taban_yaz:
        with open(a.taban, "w", encoding="utf-8") as f:
            json.dump(olculen, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        print("TABAN YAZILDI: %s" % a.taban)
        return 0

    try:
        with open(a.taban, encoding="utf-8") as f:
            taban = json.load(f)
    except Exception as e:                                        # noqa: BLE001
        olculemedi("taban dosyasi okunamadi (%s) — 'taban yok' YESIL DEGILDIR: %s"
                   % (a.taban, e))

    # ── BASLIK SAYILARI (mimar formatı) ──────────────────────────────────────────
    fk, ff = olculen["filtre_kayip"], olculen["filtre_fazla"]
    ak = olculen["arama_kayip"]
    af_top = olculen["arama_fazla_toplam_BLOKLAMAZ"]
    filtre_marka = len(set(fk) | set(ff))
    filtre_kalem = sum(fk.values()) + sum(ff.values())
    arama_marka = len([m for m, (s, _f, r) in kumeler.items() if s ^ r])
    arama_kalem = sum(ak.values()) + af_top
    print("MARKA=%d FILTRE_FARK=%d/%d ARAMA_FARK=%d/%d"
          % (len(veri), filtre_marka, filtre_kalem, arama_marka, arama_kalem))
    print("  ayrinti: FILTRE_KAYIP=%d/%d · FILTRE_FAZLA=%d/%d · ARAMA_KAYIP=%d/%d · "
          "ARAMA_FAZLA(bloklamaz)=%d"
          % (len(fk), sum(fk.values()), len(ff), sum(ff.values()),
             len(ak), sum(ak.values()), af_top))
    print("  katalog: %d urun · kanonik marka: %d" % (len(urunler), len(veri)))
    print()

    # ── S) TEK KAYNAK: sayfa kumesi = deponun kanonik sayma fonksiyonu ───────────
    sapan_s = [m for m, (sayfa, _f, _r) in kumeler.items()
               if len(sayfa) != mmb.marka_urun_sayisi(veri[m])]
    kontrol("S: SAYFA kumesi buyuklugu = marka_urun_sayisi (ikinci toplama formulu YOK; "
            "sapan: %d %s)" % (len(sapan_s), sapan_s[:4]), not sapan_s)

    # ── C) POZITIF CAPA — kapinin totolojiye dusmedigi ────────────────────────────
    kimlik_sayaci = {}
    for p in urunler:
        pid = p.get("id")
        if pid:
            kimlik_sayaci[pid] = kimlik_sayaci.get(pid, 0) + 1
    for pid, marka, tur in CAPALAR:
        if kimlik_sayaci.get(pid, 0) != 1:
            kontrol("CAPA %s (%s): katalogda TAM BIR KEZ gecmeli (bulunan: %d)"
                    % (pid, tur, kimlik_sayaci.get(pid, 0)), False)
            continue
        uc = kumeler.get(marka)
        if uc is None:
            kontrol("CAPA %s: '%s' markasi evrende YOK" % (pid, marka), False)
            continue
        sayfa, _filtre, srch = uc
        kontrol("CAPA %s -> /marka/%s/ SAYFASINDA (%s)" % (pid, marka, tur), pid in sayfa)
        kontrol("CAPA %s -> '%s' ARAMASINDA" % (pid, marka), pid in srch)

    # ── T) TABAN KARSILASTIRMASI (bloklayici uc eksen) ───────────────────────────
    print()
    kopuk = False
    for ad, olc_e, tab_e in (("FILTRE_KAYIP", fk, taban.get("filtre_kayip", {})),
                             ("FILTRE_FAZLA", ff, taban.get("filtre_fazla", {})),
                             ("ARAMA_KAYIP", ak, taban.get("arama_kayip", {}))):
        artan, azalan = eksen_karsilastir(ad, olc_e, tab_e)
        kontrol("%s: hicbir markada TABANIN USTUNE cikmadi (artan: %d %s)"
                % (ad, len(artan), artan[:4]), not artan)
        if azalan:
            kopuk = True
            print("       ↓ %s tabanin ALTINDA (%d marka): %s"
                  % (ad, len(azalan), azalan[:6]))
        kontrol("%s: taban GUNCEL (circir — dusus de kirmizidir; azalan: %d)"
                % (ad, len(azalan)), not azalan)

    if taban.get("marka_sayisi") != len(veri):
        BILGI.append("marka evreni degisti: taban %s -> olculen %d (taban --taban-yaz ile "
                     "tazelenmeli)" % (taban.get("marka_sayisi"), len(veri)))
    BILGI.append("ARAMA_FAZLA taban %s -> olculen %d (BLOKLAMAZ — gurultu kesimi ayri faz)"
                 % (taban.get("arama_fazla_toplam_BLOKLAMAZ"), af_top))

    for b in BILGI:
        print("  BILGI " + b)
    ne_olculmedi()
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldi)" % len(FAILS))
        if kopuk:
            print("   Taban bayatsa tek satirlik cozum: "
                  "python3 tools/marka-invaryant-kapisi.py --taban-yaz")
        return 1
    print("\nSONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

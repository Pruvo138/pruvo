#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marka tek-sayfa davranış testinin çift yönlü mutasyon bataryası.

Her öldürücü mutant yalnız üretim koduna uygulanır ve
``tools/marka-artim-test.py`` tarafından kırmızı yakılması beklenir. Kontrol
mutantları davranışı korur ve yeşil kalmalıdır. Mutasyon diske yazılmadan önce
ve sonra SHA-256 ölçülür; her turda kaynak bayt-birebir geri alınır.

Kullanım: python3 tools/marka-sayfa-mutasyon.py [--dokum]
"""
import atexit
import hashlib
import io
import os
import re
import shutil
import signal
import subprocess
import sys
import time


TOOLS = os.path.dirname(os.path.realpath(__file__))
KOK = os.path.dirname(TOOLS)
HEDEF = os.path.realpath(os.path.join(TOOLS, "marka_model_build.py"))
DAVRANIS = os.path.realpath(os.path.join(TOOLS, "marka-artim-test.py"))
YEDEK = HEDEF + ".marka-sayfa-mutasyon-yedek"


def oldurucu(kimlik, ne_degisti, hedef, ciftler):
    return {"id": kimlik, "dosya": "tools/marka_model_build.py",
            "ne_degisti": ne_degisti, "beklenen": "OLDURUCU",
            "hedef": hedef, "ciftler": ciftler}


def kontrol(kimlik, ne_degisti, ciftler):
    return {"id": kimlik, "dosya": "tools/marka_model_build.py",
            "ne_degisti": ne_degisti, "beklenen": "KONTROL",
            "hedef": "davranış korunur; 20/20 yeşil kalmalı", "ciftler": ciftler}


MUTANTLAR = [
    oldurucu(
        "M01_KART_KUMESI_DAR",
        "Artım yükü bütün marka kalemleri yerine yalnız SSR'de basılı kalemlere daraltıldı.",
        "TÜM parçalar: A10/A11/A14e/A14f",
        [('               model_uyelik.get(p.get("id")) or []] for p in kalemler],',
          '               model_uyelik.get(p.get("id")) or []] for p in basili],')]),
    oldurucu(
        "M02_CIP_NAVIGASYON",
        "Model çipi sayfa içi filtre yerine model adresine yönlendirildi.",
        "sayfa-içi çip: A4/A5",
        [('        e.preventDefault();\n        var ix = parseInt(this.getAttribute("data-mm"), 10);',
          '        g.location.replace(this.getAttribute("href"));\n'
          '        var ix = parseInt(this.getAttribute("data-mm"), 10);')]),
    oldurucu(
        "M03_MARKA_ESLEME_GEVSEK",
        "Toyota üyeliği olan her ürün ayrıca Honda marka sayfasına sızdırıldı.",
        "yanlış marka 0",
        [('    return uyeler\n\n\ndef ek_marka_normlu',
          '    if "Toyota" in uyeler and "Honda" not in uyeler:\n'
          '        uyeler.append("Honda")\n'
          '    return uyeler\n\n\ndef ek_marka_normlu')]),
    oldurucu(
        "M04_MUKERRER_AYIKLAMA_YOK",
        "Kimlik tekilleştirmesi ve onu önceleyen iç kimlik freni kaldırıldı.",
        "mükerrer id 0",
        [('            if anahtar in gorulen:\n                continue',
          '            if False and anahtar in gorulen:\n                continue'),
         ('    if sayilar["kart"] + sayilar["kova"] != sayilar["toplam"]:',
          '    if False and sayilar["kart"] + sayilar["kova"] != sayilar["toplam"]:'),
         ('    if toplam != marka_urun_sayisi(d):',
          '    if False and toplam != marka_urun_sayisi(d):')]),
    oldurucu(
        "M05_GECERSIZ_ID_FILTRESI_YOK",
        "SSR kart üretimindeki boş/geçersiz ürün kimliği filtresi kaldırıldı.",
        "ölü/geçersiz id 0",
        [('    parts = [_kart(ctx, p, attr_of(p) if attr_of else "") for p in urunler if p.get("id")]',
          '    parts = [_kart(ctx, p, attr_of(p) if attr_of else "") for p in urunler]')]),
    oldurucu(
        "M06_SAYFA_SAYACI_AYRISTI",
        "Marka kart başlığındaki görünür sayı gerçek SSR kart sayısından bir artırıldı.",
        "başlık sayısı = çip/toplam tutarlılığı",
        [("               + '<span class=\"mm-sayim-kart\">' + str(len(basili)) + '</span>)</h2>')",
          "               + '<span class=\"mm-sayim-kart\">' + str(len(basili) + 1) + '</span>)</h2>')")]),
    oldurucu(
        "M07_EDGE_YERINE_TUM_KATALOG",
        "Kart teslim yolu /katalog?ids= yerine /urunler.json olarak değiştirildi.",
        "edge teslim yolu/ağırlık: A14b",
        [('EDGE_KATALOG_YOLU = "/katalog?ids="',
          'EDGE_KATALOG_YOLU = "/urunler.json"')]),
    oldurucu(
        "M08_PARTI_TAVANI_1000",
        "Edge istek parti tavanı 100 kimlikten 1000 kimliğe çıkarıldı.",
        "100'lük parti: A14d",
        [('EDGE_PARTI = 100          # /katalog?ids= tek istekte en çok 100 id (ana sayfa da 100 kullanıyor)',
          'EDGE_PARTI = 1000         # mutant: edge tavanı bozuldu')]),
    oldurucu(
        "M09_ILK_ACILISTA_FETCH",
        "DOMContentLoaded kurulurken kullanıcı eylemi olmadan parça yükü çekildi.",
        "ilk açılışta istek yok: A14a",
        [('    var katalog = {};        // id -> edge kaydı (yalnız ÇEKİLENLER; tüm katalog İNMEZ)',
          '    var katalog = {};        // id -> edge kaydı (yalnız ÇEKİLENLER; tüm katalog İNMEZ)\n'
          '    fetch(man.yuk);           // mutant: kullanıcı eyleminden önce istek')]),
    oldurucu(
        "M10_TUMUNU_GOSTER_OLU",
        "Tümünü göster ve kaydırma girişinde artım koşulsuz durduruldu.",
        "TÜM parçalar: A10/A11/A12/A13/A14c-d-e-f",
        [('    function devam(hepsi){\n      if(mesgul){ return; }',
          '    function devam(hepsi){\n      if(true){ return; }')]),
    oldurucu(
        "M11_MODEL_FILTRESI_OLU",
        "Model filtresi girişinde işlem koşulsuz durduruldu.",
        "sayfa-içi filtre: A6/A7/A8/A9",
        [('    function filtreUygula(ix){\n      if(mesgul){ return; }',
          '    function filtreUygula(ix){\n      if(true){ return; }')]),
    oldurucu(
        "M12_MODEL_ESLEME_TERS",
        "Model üyeliği süzgeci üyeleri almak yerine üye olmayanları aldı.",
        "doğru model kalemleri: A7/A14e/A14f",
        [('         && (kayit[2] || []).indexOf(modelIx) === -1){ continue; }',
          '         && (kayit[2] || []).indexOf(modelIx) !== -1){ continue; }')]),
    oldurucu(
        "M13_ARTIM_ISARETI_YOK",
        "İstemcinin çizdiği kartlardan data-artim işareti kaldırıldı.",
        "çizilen kart kimliği: A13",
        [("                               mmAttr(kayit) + ' data-artim=\"\"'));",
          "                               mmAttr(kayit)));" )]),
    oldurucu(
        "M14_DUGME_GIZLENMIYOR",
        "Tüm kartlar çizilince Tümünü göster düğmesini gizleyen atama kaldırıldı.",
        "tamamlanma durumu: A12",
        [('          if(dugme && cizilen >= kalemler.length){ dugme.style.display = "none"; }',
          '          if(false && dugme && cizilen >= kalemler.length){ dugme.style.display = "none"; }')]),
    oldurucu(
        "M15_PARTILEME_YOK",
        "Eksik kimliklerin tamamı tek edge isteğine konarak partileme atlandı.",
        "100'lük parti: A14d",
        [('      var partiler = partile(eksik, man.parti);',
          '      var partiler = [eksik];')]),
    oldurucu(
        "M16_GEREKENDEN_FAZLA_ID",
        "Tümünü göster isteği kalan dilim yerine basılı kimlikleri de yeniden istedi.",
        "yalnız gereken id: A14e/A14f",
        [('        var dilim = kalemler.slice(cizilen, cizilen + adet);',
          '        var dilim = kalemler.slice(0, cizilen + adet);')]),
    oldurucu(
        "M17_FILTRE_DURUMU_YANLIS",
        "Etkin model filtresinin kullanıcı durum metninden filtre bilgisi çıkarıldı.",
        "filtre durumu: A8",
        [('          if(durum){ durum.textContent = kalemler.length + " parça (model filtresi etkin)"; }',
          '          if(durum){ durum.textContent = kalemler.length + " parça"; }')]),
    oldurucu(
        "M18_AKTIF_CIP_ISARETI_YOK",
        "Seçili model çipine mm-aktif sınıfı eklenmesi kaldırıldı.",
        "aktif çip: A9",
        [('        cipler[i].className = "mm-model-btn" + (kendi ? " mm-aktif" : "");',
          '        cipler[i].className = "mm-model-btn";')]),
    kontrol(
        "K01_YORUM",
        "Üretim sabitinin yanına yalnız açıklayıcı yorum eklendi.",
        [('MARKA_KART_N = 80', 'MARKA_KART_N = 80  # kontrol mutantı: davranış aynı')]),
    kontrol(
        "K02_BOSLUK",
        "Eşdeğer atamada yalnız gereksiz parantez eklendi.",
        [('  var PARTI = 60;               // her artımda çizilecek kart sayısı',
          '  var PARTI = (60);               // her artımda çizilecek kart sayısı')]),
    kontrol(
        "K03_ESDEGER_IFADE",
        "Boş eksik-kimlik denetimi eşdeğer uzunluk karşılaştırmasıyla yazıldı.",
        [('      if(!eksik.length){ return Promise.resolve(true); }',
          '      if(eksik.length === 0){ return Promise.resolve(true); }')]),
]


def sha256_bayt(b):
    return hashlib.sha256(b).hexdigest()


def oku_bayt():
    with open(HEDEF, "rb") as f:
        return f.read()


def yaz_bayt(b):
    with open(HEDEF, "wb") as f:
        f.write(b)
    ileri = time.time() + 2
    os.utime(HEDEF, (ileri, ileri))
    shutil.rmtree(os.path.join(TOOLS, "__pycache__"), ignore_errors=True)


def uygula(taban, mutant):
    metin = taban.decode("utf-8")
    for eski, yeni in mutant["ciftler"]:
        adet = metin.count(eski)
        if adet != 1:
            raise RuntimeError("%s anchor adedi %d (1 olmali): %r"
                               % (mutant["id"], adet, eski[:100]))
        metin = metin.replace(eski, yeni, 1)
    return metin.encode("utf-8")


def iddia_etiketi(satir):
    govde = satir.strip()[6:].split(" — ", 1)[0].strip()
    return govde.split(" ", 1)[0]


def kostur():
    shutil.rmtree(os.path.join(TOOLS, "__pycache__"), ignore_errors=True)
    cp = subprocess.run([sys.executable, DAVRANIS], cwd=KOK, capture_output=True,
                        text=True, timeout=1800, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    cikti = (cp.stdout or "") + (cp.stderr or "")
    m = re.search(r"IDDIA=(\d+)/(\d+) DUSEN=(\d+)", cikti)
    dusen = [iddia_etiketi(x) for x in cikti.splitlines() if x.strip().startswith("DUSEN ")]
    cokme = ("Traceback (most recent call last)" in cikti or cp.returncode not in (0, 1)
             or m is None)
    return {"rc": cp.returncode, "cikti": cikti, "iddia": tuple(map(int, m.groups())) if m else None,
            "dusen": dusen, "cokme": cokme}


_GERI = {"bitti": False, "taban": None}


def geri_al(*_args):
    if _GERI["bitti"] or _GERI["taban"] is None:
        return
    try:
        yaz_bayt(_GERI["taban"])
        _GERI["bitti"] = True
        if os.path.exists(YEDEK):
            os.remove(YEDEK)
    except Exception as e:  # noqa: BLE001
        print("GERI_ALMA_HATASI: %r; yedek=%s" % (e, YEDEK))


def durumlandir(mutant, sonuc, taban_toplam):
    tam_olcum = sonuc["iddia"] is not None and sonuc["iddia"][1] == taban_toplam
    if sonuc["cokme"] or not tam_olcum:
        return "COKME"
    if mutant["beklenen"] == "KONTROL":
        return "YESIL" if sonuc["rc"] == 0 and not sonuc["dusen"] else "KIRMIZI"
    if sonuc["rc"] == 1 and sonuc["dusen"]:
        return "OLDU"
    if sonuc["rc"] == 0 and not sonuc["dusen"]:
        return "HAYATTA KALDI"
    return "COKME"


def main():
    dokum = "--dokum" in sys.argv[1:]
    if os.path.exists(YEDEK):
        print("OLCULEMEDI: onceki kosum yedegi duruyor: %s" % YEDEK)
        return 3
    taban = oku_bayt()
    taban_sha = sha256_bayt(taban)
    with open(YEDEK, "wb") as f:
        f.write(taban)
    _GERI["taban"] = taban
    atexit.register(geri_al)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, lambda *_a: (geri_al(), sys.exit(130)))
        except Exception:  # noqa: BLE001
            pass

    taban_sonuc = kostur()
    if (taban_sonuc["rc"] != 0 or taban_sonuc["iddia"] is None
            or taban_sonuc["iddia"][0] != taban_sonuc["iddia"][1]):
        print("OLCULEMEDI: taban davranis testi yesil degil (rc=%s iddia=%r)"
              % (taban_sonuc["rc"], taban_sonuc["iddia"]))
        geri_al()
        return 3
    taban_toplam = taban_sonuc["iddia"][1]
    print("TABAN RC=%d IDDIA=%d/%d SHA256=%s DAVRANIS=%s"
          % (taban_sonuc["rc"], taban_sonuc["iddia"][0], taban_toplam,
             taban_sha, DAVRANIS))

    sonuclar = []
    geri_hatasi = 0
    try:
        for mutant in MUTANTLAR:
            kayit = dict(mutant)
            try:
                mutant_bayt = uygula(taban, mutant)
                once_sha = sha256_bayt(oku_bayt())
                yaz_bayt(mutant_bayt)
                sonra_sha = sha256_bayt(oku_bayt())
                if once_sha != taban_sha or sonra_sha == once_sha:
                    raise RuntimeError("mutasyon SHA kaniti gecersiz once=%s sonra=%s"
                                       % (once_sha, sonra_sha))
                sonuc = kostur()
                kayit.update(sonuc)
                kayit["uygulandi"] = sonra_sha != once_sha
                kayit["gerceklesen"] = durumlandir(mutant, sonuc, taban_toplam)
            except Exception as e:  # noqa: BLE001
                kayit.update({"rc": 2, "cikti": repr(e), "iddia": None, "dusen": [],
                              "cokme": True, "uygulandi": False, "gerceklesen": "COKME"})
            finally:
                yaz_bayt(taban)
                geri_sha = sha256_bayt(oku_bayt())
                kayit["geri_alindi"] = geri_sha == taban_sha
                if not kayit["geri_alindi"]:
                    geri_hatasi += 1
            sonuclar.append(kayit)
            print("%-28s beklenen=%-9s gercek=%-14s rc=%s iddia=%s dusen=%s uygulandi=%s geri=%s"
                  % (mutant["id"], mutant["beklenen"], kayit["gerceklesen"],
                     kayit["rc"], kayit["iddia"], ",".join(kayit["dusen"]) or "-",
                     kayit["uygulandi"], kayit["geri_alindi"]))
            if dokum and kayit["gerceklesen"] == "COKME":
                print(kayit["cikti"][-1200:])
    finally:
        geri_al()

    oldurucular = [x for x in sonuclar if x["beklenen"] == "OLDURUCU"]
    kontroller = [x for x in sonuclar if x["beklenen"] == "KONTROL"]
    oldurulen = [x for x in oldurucular if x["gerceklesen"] == "OLDU"]
    hayatta = [x for x in oldurucular if x["gerceklesen"] == "HAYATTA KALDI"]
    kontrol_yesil = [x for x in kontroller if x["gerceklesen"] == "YESIL"]
    cokme = [x for x in sonuclar if x["gerceklesen"] == "COKME"]

    print("\nOZET")
    print("TABAN_RC=%d" % taban_sonuc["rc"])
    print("TABAN_IDDIA=%d" % taban_toplam)
    print("OLDURUCU_TOPLAM=%d" % len(oldurucular))
    print("OLDURUCU_TUTAN=%d" % len(oldurulen))
    print("HAYATTA_KALAN=%d" % len(hayatta))
    print("KONTROL_TOPLAM=%d" % len(kontroller))
    print("KONTROL_YESIL=%d" % len(kontrol_yesil))
    print("COKME=%d" % len(cokme))
    print("GERI_ALMA_HATASI=%d" % geri_hatasi)
    print("\nid | dosya | ne degisti | beklenen | gerceklesen | dusen iddia")
    for x in sonuclar:
        print("%s | %s | %s | %s | %s | %s"
              % (x["id"], x["dosya"], x["ne_degisti"], x["beklenen"],
                 x["gerceklesen"], ",".join(x["dusen"]) or "-"))
    if hayatta:
        print("\nHAYATTA KALANLAR")
        for x in hayatta:
            print("%s | hedef=%s" % (x["id"], x["hedef"]))

    # Batarya boşluğu bulursa da çalıştırılabilir ölçüm başarıyla tamamlanmıştır; rc=1
    # yalnız aracın kendi kabul hükmünü kırmızı yapar. Çökme/geri-alma her durumda rc=2.
    if cokme or geri_hatasi:
        return 2
    if hayatta or len(kontrol_yesil) != len(kontroller):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

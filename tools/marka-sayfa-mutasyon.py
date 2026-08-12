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
import subprocess
import sys
import tempfile
import time


TOOLS = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, TOOLS)

import mutasyon_kopya as mk                                        # noqa: E402

# 🔴 MUTASYON KOPYAYA UYGULANIR, CANLI AGACA ASLA (12 Agu 2026). Eski tasarimda mutant
# canli `tools/marka_model_build.py`ye yaziliyor, diske yedek birakilip atexit/sinyal
# kancalariyla geri aliniyordu; kesilen bir kosum agacta yedek birakiyor ve KARDES
# nobetciyi kirmizi yakiyordu (kardes surucude OLCULDU: artik yedek yuzunden
# marka-model-test.py rc=1). Artik `tools/` gecici bir koke KOPYALANIR ve canli agacin
# DEGISMEDIGI bas/son damgayla KANITLANIR — "geri aldim" beyani kanit sayilmaz.
CANLI_HEDEF = os.path.join(TOOLS, "marka_model_build.py")
KOPYA = {"kok": None, "hedef": None, "davranis": None}


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
        # 🔴 ÇAPA TAZELENDİ (12 Ağu 2026): başlık artık O AN BASILAN kartı (`basili`)
        # değil ERİŞİLEBİLİR kart yüzeyini (`kalemler`) beyan ediyor ve sayıyı kendi
        # kategori kırılımından türetiyor. MUTANTIN NİYETİ AYNI KALDI: başlık sayısı
        # gerçek kümeden BİR fazla olsun (kırılımıyla birlikte, yani "sayı ile kırılım
        # ayrı kaynaktan" mutantından ayırt edilebilir bir off-by-one).
        "Marka kart başlığındaki sayı erişilebilir kart yüzeyinden bir artırıldı.",
        "başlık sayısı = çip/toplam tutarlılığı",
        [("               + _bolum_sayaci(esc, kalemler, \"erisim\") + ')</h2>')",
          "               + _bolum_sayaci(esc, kalemler + kalemler[:1], \"erisim\") "
          "+ ')</h2>')")]),
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
    with open(KOPYA["hedef"], "rb") as f:
        return f.read()


def yaz_bayt(b):
    with open(KOPYA["hedef"], "wb") as f:
        f.write(b)
    ileri = time.time() + 2
    os.utime(KOPYA["hedef"], (ileri, ileri))
    shutil.rmtree(os.path.join(KOPYA["kok"], "tools", "__pycache__"), ignore_errors=True)


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
    shutil.rmtree(os.path.join(KOPYA["kok"], "tools", "__pycache__"), ignore_errors=True)
    cp = subprocess.run([sys.executable, KOPYA["davranis"]], cwd=KOPYA["kok"],
                        capture_output=True,
                        text=True, timeout=1800, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    cikti = (cp.stdout or "") + (cp.stderr or "")
    m = re.search(r"IDDIA=(\d+)/(\d+) DUSEN=(\d+)", cikti)
    dusen = [iddia_etiketi(x) for x in cikti.splitlines() if x.strip().startswith("DUSEN ")]
    cokme = ("Traceback (most recent call last)" in cikti or cp.returncode not in (0, 1)
             or m is None)
    return {"rc": cp.returncode, "cikti": cikti, "iddia": tuple(map(int, m.groups())) if m else None,
            "dusen": dusen, "cokme": cokme}


def geri_al(*_args):
    """Kopya kokte tabana don. (Canli agac zaten HIC yazilmiyor; bu yalnizca bir sonraki
    mutantin TEMIZ tabandan turemesini saglar.)"""
    if _GERI["taban"] is not None and KOPYA["hedef"]:
        yaz_bayt(_GERI["taban"])


_GERI = {"bitti": False, "taban": None}


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
    # 🔴 CANLI AGAC DAMGASI: bas/son esit olmali ve artik `*-yedek` kalmamali.
    damga_bas = mk.agac_damgasi([CANLI_HEDEF])
    tmp = tempfile.mkdtemp(prefix="mm-sayfa-mutasyon-")
    KOPYA["kok"] = mk.kopya_kok(tmp)
    KOPYA["hedef"] = os.path.join(KOPYA["kok"], "tools", "marka_model_build.py")
    KOPYA["davranis"] = os.path.join(KOPYA["kok"], "tools", "marka-artim-test.py")
    atexit.register(lambda: shutil.rmtree(tmp, ignore_errors=True))
    taban = oku_bayt()
    taban_sha = sha256_bayt(taban)
    _GERI["taban"] = taban

    taban_sonuc = kostur()
    if (taban_sonuc["rc"] != 0 or taban_sonuc["iddia"] is None
            or taban_sonuc["iddia"][0] != taban_sonuc["iddia"][1]):
        print("OLCULEMEDI: taban davranis testi yesil degil (rc=%s iddia=%r)"
              % (taban_sonuc["rc"], taban_sonuc["iddia"]))
        return 3
    taban_toplam = taban_sonuc["iddia"][1]
    print("TABAN RC=%d IDDIA=%d/%d SHA256=%s DAVRANIS=%s"
          % (taban_sonuc["rc"], taban_sonuc["iddia"][0], taban_toplam,
             taban_sha, KOPYA["davranis"]))

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
    damga_son = mk.agac_damgasi([CANLI_HEDEF])
    agac_temiz = damga_bas == damga_son and not damga_son[1]
    print("AGAC_DAMGASI=%s->%s artik=%s" % (damga_bas[0], damga_son[0], damga_son[1]))
    print("AGAC_KIRLILIGI=%s" % ("YOK" if agac_temiz else "VAR"))
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
    if cokme or geri_hatasi or not agac_temiz:
        return 2
    if hayatta or len(kontrol_yesil) != len(kontroller):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

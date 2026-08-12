#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — `model_kanon` zinciri gercek ihlali yakiyor mu?

  python3 tools/model-kanon-mutasyon.py

NEDEN REPODA DURUYOR: anlatilan batarya kanit DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]). Surucu iki kapiyi birden surer:
  * tools/model-kanon-d1-test.py  — kanonik MODEL turetimi (kusak katlamasi, gosterim,
                                    deger evreni, fail-closed, olcek).
  * tools/uyum-kapisi.py          — KAPALI MARKA SOZLUGUNUN kapaliligi (S2 kimlik nobeti).

🔴 KABUL CIKIS KODU DEGIL, KIRMIZI IDDIA KODLARININ KUMESIDIR ([[hukum-yanlis-birimde]]).
Sebep olculdu: `uyum-kapisi.py` bu dalda ZATEN kirmizi (A1 — sozluk acildi, 7 katalog
kaydinin `uyum[].model` alani hala marka adi tasiyor; duzeltme MaCiT'in duzleminde).
Cikis koduna baksaydik o kapidaki HER mutant "olduruldu" gorunurdu. Bunun yerine her
kapinin MUTASYONSUZ KIRMIZI KODLARI once olculur (taban) ve mutantin ONU TAM OLARAK
hangi kodlarla buyuttugune bakilir.

🔴 COKME KIRMIZIYLA KARISTIRILMAZ: rc 0/1 disi ya da olculen IDDIA SAYISI tabandan farkli
kosum COKME sayilir — coken mutant "oldurulmus" DEGILDIR.

NASIL: mutant DAIMA KOPYAYA uygulanir. ROOT'un tamami gecici bir dizine SYMLINK'lenir,
mutasyona ugrayan TEK dosya gercek kopyayla degistirilir ve kapi O AYNADAN kosulur.
Gercek agaca HICBIR SEY yazilmaz; CANLI D1'e / aga DOKUNULMAZ.

Kabul: her OLDURUCU beyan ettigi KODLARI kirmizi yakar (ne eksik ne fazla) + her KONTROL
taban kod kumesini DEGISTIRMEZ.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI_MODEL = "model-kanon-d1-test.py"
KAPI_UYUM = "uyum-kapisi.py"

# (kod, kapi, dosya, eski, yeni, beyan_kod_listesi, aciklama)
# beyan = TABANA EKLENEN kirmizi iddia kodlari. Bos liste = KONTROL (taban degismemeli).
MUTANTLAR = [
    ("M1", KAPI_MODEL, "marka_model_build.py",
     "            for taban, _etiket in evren.kusak_tabanlari(kan, t):",
     "            for taban, _etiket in ():",
     ["B6", "C5"],
     "KUSAK/VARYANT KATLAMASI KAPATILIR — `Fiesta ST` artik Fiesta kovasina, `T4` "
     "Transporter'a girmez; kolon ucun zaten kacirdigini kacirir. 🔴 C4 BILEREK BEYANDA "
     "DEGIL ve bu OLCULDU: katlama SAYFA kumesini de kucultur, yani sayfa<->suzgec farki "
     "yine 0 cikar (C4 bu mutanta KOR). Ekseni tutan sey POZITIF CAPALAR'dir (B6/C5) — "
     "tam da totoloji tuzagina karsi konuldular"),
    ("M2", KAPI_MODEL, "d1-sync.py",
     '            for p in g["urunler"]:',
     '            for p in g["ana"]:',
     ["B6", "C4", "C5"],
     "kolon YALNIZ TAM ESLESEN uyeleri yazar (katlananlari atlar) — ucun tam-esitlikle "
     "kacirdiginin AYNISINI kacirir; 'kolon var ama ise yaramaz' hali"),
    ("M3", KAPI_MODEL, "d1-sync.py",
     '            ad = g.get("display")',
     '            ad = g.get("canon")',
     ["B6", "B7", "C4", "C5"],
     "KANONIK GOSTERIM yerine ic anahtar yazilir ('fserisi', 'fiesta') — cip/sayfa "
     "etiketi ile uc degeri AYRISIR, her model cipi OLU UC olur"),
    ("M4", KAPI_MODEL, "d1-sync.py",
     '    return sema_plan("model_kanon", urunler, kanonlar, mevcut_kanon, izleme,\n'
     '                     varsayilan="[]")',
     '    return sema_plan("model_kanon", urunler, kanonlar, mevcut_kanon, izleme)',
     ["C2"],
     "OLCEK KAPISI kalkar: kolon varsayilani '[]' yerine '' varsayilir -> model kovasi "
     "disindaki ~9.600 urune HER senkronda bos UPDATE dogar"),
    ("M5", KAPI_MODEL, "d1-sync.py",
     '    except Exception as e:                                         # noqa: BLE001\n'
     '        return {}, "%s: %s" % (type(e).__name__, e)\n'
     "    if not evren.taninmis:\n"
     '        return {}, "marka evreni BOS (index.html TANINMIS_MARKALAR okunamamis)"\n'
     "    if not veri:",
     '    except Exception as e:                                         # noqa: BLE001\n'
     "        return {}, None\n"
     "    if not evren.taninmis:\n"
     '        return {}, "marka evreni BOS (index.html TANINMIS_MARKALAR okunamamis)"\n'
     "    if not veri:",
     ["E1"],
     "FAIL-CLOSED YONU TERSINE DONER: tek kaynak okunamayinca 'sebep' yerine BOS harita "
     "+ None doner -> senkron atlanmaz, TUM katalog '[]' olur (katalog capinda sessiz kayip)"),
    ("M6", KAPI_MODEL, "d1-sync.py",
     "    return ({uid: json.dumps(sorted(adlar), ensure_ascii=False, "
     'separators=(",", ":"))',
     "    return ({uid: json.dumps(list(adlar), ensure_ascii=False, "
     'separators=(",", ":"))',
     ["B3"],
     "SIRA DETERMINIZMI kalkar (kume yineleme sirasi) -> ayni katalogda metin degisir, "
     "her senkron sahte UPDATE uretir (D1 thrash)"),
    # 🔴 CAPA BILEREK KUMENIN BASINDA: mutant, sozluge SONRADAN eklenen adlardan (C grubu)
    # BAGIMSIZ olmali — yoksa sozluk kalemi ayri bir commit'te tutulup geri alindiginda
    # bu mutant "CAPA-YOK" verir ve kapalilik nobeti OLCULEMEZ hale gelirdi.
    ("M7", KAPI_UYUM, "arama.py",
     "UYUM_MARKA_IZINLI = frozenset({\n"
     '    "Abus", "Alfa Romeo",',
     "UYUM_MARKA_IZINLI = frozenset({\n"
     '    "Voranta",\n    "Abus", "Alfa Romeo",',
     ["S2"],
     "KAPALILIK NOBETI: sozluge MIMAR EKI'ne yazilmadan uydurma bir ad ('Voranta') "
     "eklenir -> yargilanmis bolumleme buyur, S2 kimlik imzasi KIRILMALI"),
    # ── 12 AGU HUKUMLERININ IKI KOLU: B7 aynasi bunlari GERCEKTEN gorüyor mu? ──────
    # 🔴 NEDEN BURADALAR: iki kol `yayimlanir_mi`ye 47b6734d'de eklendi, B7'nin BAGIMSIZ
    # aynasina eklenmedi ve kapi 5 gun KIRMIZI kalip YAYINI DURDURDU
    # ([[ikiz-tanim-sessiz-ayrisma]]). Ayna simdi hizalandi; asagidaki iki mutant aynanin
    # kollari HALA gordugunu KANITLAR — hizalama "yesile boyama" DEGILDIR.
    ("M8", KAPI_MODEL, "marka_model_build.py",
     '    if g.get("yabanci_marka"):\n        return False\n',
     '    if False:\n        return False\n',
     ["B7", "B8"],
     "GURULTU SINIFI KAPATILIR: `Hyundai|Genesis` gibi AYRI MARKA etiketleri yeniden "
     "sayfa/kolon evrenine girer — uc `?model=Genesis` mimarin KAPATTIGI sayfayi geri acar"),
    ("M9", KAPI_MODEL, "marka_model_build.py",
     "            or (sahip is not None and sahip == _canon(marka)))",
     "            or (sahip is None and sahip == _canon(marka)))",
     ["B8"],
     "(d) JETON SAHIPLIGI KOLU OLDURULUR: envanterde olmayan ama katalogda sahibi belli "
     "sabit Alfa Romeo|Giulietta tanigi yeniden sayfasiz/kolonsuz kalir — canli katalog "
     "partileri tanigi sonduremez ([[envanter-drift-parti-basina]])"),
    ("K1", KAPI_MODEL, "d1-sync.py",
     "    toplam = {}\n", "    toplam = dict()\n", [],
     "KONTROL: davranisi degistirmeyen yazim — kapi gurultu kaynagi olmamali"),
    ("K2", KAPI_MODEL, KAPI_MODEL,
     "NE OLCULMEDI (beyan):", "NE OLCULMEDI (beyan) :", [],
     "KONTROL: iddia edilmeyen eksen (kapinin beyan metni)"),
    ("K3", KAPI_UYUM, "arama.py",
     "# 🔴 REDDEDILEN ADAYLAR", "# 🔴 REDDEDILEN ADAYLAR (kayit)", [],
     "KONTROL: yalniz yorum satiri — kapali kume kimligi DEGISMEZ"),
]

# Yalniz iki uretim-hukmu mutanti icin kod adi yetmez: B7'nin beklenen fark YONU da
# gorunmeli. Boylece ilgisiz bir B7 kirilmasi mutanti oldurulmus gibi gosteremez.
BEKLENEN_IZ = {"M8": "fazla=", "M9": "fikstur_d=0/1"}


def ayna_kur(tmp):
    """ROOT'un SALT OKUNUR aynasi: tools/ gercek bir dizin (icindekiler symlink), digerleri
    dogrudan symlink. Kapi kendi TOOLS/ROOT'unu bu aynadan cozer."""
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        os.symlink(os.path.join(TOOLS, ad), os.path.join(kok, "tools", ad))
    return kok


def iddia_kodlari(cikti):
    """(kirmizi_kod_kumesi, toplam_iddia_sayisi). Kod = iddia adinin ILK jetonu."""
    kirmizi, toplam = set(), 0
    for satir in cikti.splitlines():
        s = satir.strip()
        for bas, kirmizi_mi in (("GECTI ", False), ("KALDI ", True)):
            if s.startswith(bas):
                p = s[len(bas):].split()
                toplam += 1
                if kirmizi_mi and p:
                    kirmizi.add(p[0])
    return kirmizi, toplam


def kos(kok, kapi):
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", kapi)],
                       capture_output=True, text=True, cwd=kok)
    return r, (r.stdout or "") + (r.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="model-kanon-mutasyon-")
    try:
        # ── TABAN: mutasyonsuz aynada her kapinin KIRMIZI KOD KUMESI + iddia sayisi ──
        taban = {}
        kok0 = ayna_kur(os.path.join(tmp, "taban"))
        for kapi in (KAPI_MODEL, KAPI_UYUM):
            r, cikti = kos(kok0, kapi)
            kirmizi, adet = iddia_kodlari(cikti)
            taban[kapi] = (kirmizi, adet)
            print("  TABAN %-24s rc=%d · iddia=%d · KIRMIZI kod=%s"
                  % (kapi, r.returncode, adet, sorted(kirmizi) or "-"))
            if adet == 0:
                print("\nMUTASYON SONUCU: OLCULEMEDI — %s hic iddia basmadi (harness bozuk, "
                      "butun sonuclar YALANCI olurdu)." % kapi)
                return 2

        sonuc = []
        for kod, kapi, dosya, eski, yeni, beyan, aciklama in MUTANTLAR:
            kaynak_yolu = os.path.join(TOOLS, dosya)
            metin = open(kaynak_yolu, encoding="utf-8").read()
            if metin.count(eski) != 1:
                # 🔴 "mutant uygulanamadi" YESIL sayilmaz — kanit OLCULEMEDI'dir.
                sonuc.append((kod, kapi, beyan, "CAPA-YOK(%d)" % metin.count(eski),
                              aciklama))
                continue
            kok = ayna_kur(os.path.join(tmp, kod))
            hedef = os.path.join(kok, "tools", dosya)
            os.unlink(hedef)
            with open(hedef, "w", encoding="utf-8") as f:
                f.write(metin.replace(eski, yeni, 1))
            r, cikti = kos(kok, kapi)
            kirmizi, adet = iddia_kodlari(cikti)
            t_kirmizi, t_adet = taban[kapi]
            if r.returncode not in (0, 1):
                gozlem = "COKME(rc=%d: %s)" % (r.returncode,
                                               cikti.strip().split("\n")[-1][:70])
            elif adet != t_adet:
                gozlem = "COKME(iddia sayisi %d != taban %d)" % (adet, t_adet)
            else:
                yeni_kirmizi = kirmizi - t_kirmizi
                kaybolan = t_kirmizi - kirmizi
                if kaybolan:
                    gozlem = "COKME(taban kirmizisi KAYBOLDU: %s)" % sorted(kaybolan)
                elif yeni_kirmizi == set(beyan) and (kod not in BEKLENEN_IZ or
                                                      BEKLENEN_IZ[kod] in cikti):
                    gozlem = "UYDU(%s)" % (sorted(yeni_kirmizi) or "taban degismedi")
                else:
                    iz = BEKLENEN_IZ.get(kod)
                    iz_notu = " iz-yok=%s" % iz if iz and iz not in cikti else ""
                    gozlem = "SAPTI(gozlenen=%s%s)" % (sorted(yeni_kirmizi) or "-", iz_notu)
            sonuc.append((kod, kapi, beyan, gozlem, aciklama))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nMUTASYON SONUCU (kabul: cikis kodu DEGIL, KIRMIZI IDDIA KODLARI)")
    kalan = 0
    for kod, kapi, beyan, gozlem, aciklama in sonuc:
        tamam = gozlem.startswith("UYDU")
        kalan += 0 if tamam else 1
        print("  %s %-3s [%s] beyan=%-22s %s"
              % ("OK   " if tamam else "KALDI", kod, kapi, sorted(beyan) or "KONTROL",
                 gozlem))
        print("        %s" % aciklama)
    if kalan:
        print("\nSONUC: KIRMIZI ❌  (%d mutant beklenen kod kumesini vermedi)" % kalan)
        return 1
    print("\nSONUC: YESIL ✅  (%d mutant: her OLDURUCU beyan ettigi kodlari yakti, her "
          "KONTROL tabani degistirmedi)" % len(sonuc))
    return 0


if __name__ == "__main__":
    sys.exit(main())

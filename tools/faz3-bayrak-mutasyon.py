#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SÜRÜCÜSÜ — `tools/faz3-bayrak.js` TEST 7 (zarif bozulma) körlük ölçümü.

  python3 tools/faz3-bayrak-mutasyon.py

🔴 NEDEN VAR (ölçüldü 12 Ağu 2026): TEST 7'nin "yedek sonuçlar sorguyla eşleşiyor"
iddiası ELLE yazılmış bir substring kuralıydı; `index.html::markaSorgusuEsler` 5 Ağu'da
(a522cb14) ÜYELİK ∪ BAŞLIKTA TAM KELİME yüklemine bağlanınca iddia bayat aynaya döndü ve
`serit-a3`i kırmızı yakıp `deploy`u SKIPPED bıraktı. Onarım iddiayı sitenin KANONİK
eşleştiricisine bağladı — ama kabul ile kıyas AYNI fonksiyondan gelince ortaya TOTOLOJİ
RİSKİ çıkar: yüklem bozulursa iki taraf birlikte kayar ve kapı kör kalır.

Bu sürücü o körlüğü ÖLÇER: kapının ölçtüğü GERÇEK mantığa (kanonik eşleştirici + yedek
yolun kendisi) üç ayrı mutant uygular ve her mutantta kapının KIRMIZI yanmasını —
üstelik BEKLENEN EKSENDE kırmızı yanmasını — şart koşar. Toplu rc yetmez
([[hukum-yanlis-birimde]]): her mutantın hangi iddiayı düşürdüğü ayrı ayrı aranır.

🔴 BEKLEME EKSENİ (13 Eyl 2026): 12 Eyl'de kapının 4 sabit uykusu `bekleKosul`a
çevrildi (8b8f847d) — CI yükünde 80 ms boyamaya yetmiyordu ve render iddiaları BOŞ
DOM'a bakıyordu. Bu eksenin mutantı yoktu. ÖLÇÜLDÜ (yerel, 5'er koşum):
  * tavan 3000 → 0 TEK BAŞINA: 5/5 rc=0, 0 ❌ — önündeki SABIT `await bekle(80)`
    yüksüz makinede boyamayı zaten bitiriyor ve tavanı MASKELİYOR. Saf tavan mutantı
    ayırt edici DEĞİL (sonucu koşucunun yüküne bağlı = belirlenimci değil).
  * sabit uyku kaldırılmış + tavan 0: 5/5 rc=1, her koşumda AYNI 12 ❌ küme; 4 çağrı
    yerinin 4 render iddiası (`IZ_IDDIALARI`) içinde.
  * sabit uyku kaldırılmış + tavan 3000 (canlı): 5/5 rc=0 → kırmızı TAVANDAN gelir,
    uykunun kaldırılmasından DEĞİL. (sabit uykulu + tavan 6000: 5/5 rc=0.)
Bu yüzden bekleme mutantı ve kontrolü kapının KOPYASINDA iki dönüşümü birlikte yapar:
her `await bekleKosul(` çağrısından hemen önceki sabit `await bekle(n);` kaldırılır
(maske), tavan varsayılanı değiştirilir (mutant 0 · kontrol 2×canlı). Mutant iz şartı:
rc≠0 VE `IZ_IDDIALARI`nın HEPSİ `❌` satırı olarak basılmış. Kontrol şartı: rc=0 ve
0 ❌. Canlı tavan ≤0 ise eksen zaten BOZUKTUR → KÖR (rc=1), çapa hatası değil.
TERS KANIT: bu blok eklenmeden önce batarya yalnız `index.html`i mutasyona uğratıyordu
(dc9a4d6b koşumu: 3/3, bekleme satırı 0) ve canlı tavan 0'a düşse kapı 5/5 YEŞİL
kaldığı için taban da yeşil kalır → batarya rc=0 = bu kusura KÖR.

CANLI AĞACA TEK BAYT YAZILMAZ ([[kapi-yan-etkisi-gizli-onkosul]]): mutasyon
`tools/mutasyon_kopya.py::kopya_kok` ile kurulan geçici köke uygulanır; orada `tools/`
ve `index.html` GERÇEK KOPYADIR, `urunler.json` / `ozet.json` / `taban-fiyatlar.js` /
`secenekler.js` sembolik bağdır (ölçüm gerçek katalogda kalır). Ağacın değişmediği
baş/son `agac_damgasi()` ile KANITLANIR.

ÇAPA ELLE YAZILMAZ ([[mutasyon-kaniti-yeniden-uretilebilir]]): hedef gövdeler
`index.html`den FONKSİYON ADIYLA ayıklanır; bekleme çapaları `faz3-bayrak.js`in
`bekleKosul` imzasından ve `await bekleKosul(` çağrı yerlerinden türer; iz adlarının
her biri kaynakta tam bir kez `kontrol("<ad>"` olarak geçmek zorundadır. Ayıklama
tutmazsa ya da dönüşüm etkisiz kalırsa hüküm OLCULEMEDI değil KIRMIZI'dır (rc=3).

ÇIKIŞ: rc=0 tüm mutantlar yakalandı ve kontrol yeşil · rc=1 en az bir mutant KAÇTI
ya da kontrol düştü (kapı kör / mutant ayırt edici değil) · rc=3 çapa/kurulum bozuk.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from mutasyon_kopya import (CapaHatasi, agac_damgasi, kopya_kok,  # noqa: E402
                            mutant_metni)

INDEX = os.path.join(ROOT, "index.html")
KAPI = os.path.join(TOOLS, "faz3-bayrak.js")


def js_fonksiyon(src, ad):
    """`index.html`ten `function <ad>(...)` gövdesini AYIKLA — çapa addan türer.

    Fail-closed: bulunamazsa ya da gövde dosyada tam bir kez geçmiyorsa CapaHatasi."""
    imza = "\n  function %s(" % ad
    i = src.find(imza)
    if i == -1:
        raise CapaHatasi("index.html'de function %s( YOK (yeniden adlandirildi mi?)" % ad)
    j = src.index("{", i)
    derinlik = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            derinlik += 1
        elif src[k] == "}":
            derinlik -= 1
            if derinlik == 0:
                govde = src[i + 1:k + 1]
                if src.count(govde) != 1:
                    raise CapaHatasi("%s govdesi kaynakta %d kez geciyor (1 olmali)"
                                     % (ad, src.count(govde)))
                return govde
    raise CapaHatasi("%s govdesinin kapanisi bulunamadi" % ad)


# (kapsam, desen, donusum, beklenen KIRMIZI eksen, aciklama)
MUTANTLAR = [
    ("markaSorgusuEsler", r"return markaUyeMi",
     lambda s: s.replace("markaUyeMi(p, hedefMarka) || ", ""),
     # 🔴 6 Eyl — EKSEN ATFI KOSMASI GARANTI OLAN IDDIAYA BAGLANDI.
     #   Eski atif `uyeligi olan HER urun sonucta` idi; o iddia
     #   `yedekEslesmeKontrolu` icinde, EDGE HAVUZU verisine bagli kosar
     #   (`markaSorgusu === null` -> hic kosmaz). 6 Eyl'de havuzda ayirt edici uye
     #   0'a dustu, iddia kosmadi ve mutant "KACTI" yazildi — OYSA kapi KIRMIZI
     #   yaniyordu, yalnizca BASKA (ve garantili) eksende: UYELIK EKSENI ANKRAJI.
     #   Yani kacan sey koruma degil ATIFTI. Atif artik TAM KATALOG ankrajina
     #   baglidir; o kol veri tesadufune bagli DEGILDIR, kurulamazsa KIRMIZI yanar.
     "BASLIGINDA GECMEYEN her urun marka",
     "5 Agu ONCESI davranis: marka sorgusu YALNIZ baslikta tam kelime arar "
     "(uyelik kolu dusuruldu) — kapinin BAYAT halinin ta kendisi"),
    ("aramaPlaniEsler", r"return markaSorgusuEsler",
     lambda s: s.replace("return markaSorgusuEsler(p, plan.kanon);", "return true;"),
     "GERCEKTEN daraltiyor",
     "kanonik eslestirici marka sorgusunda HEP TRUE: iddia ile kiyas birlikte "
     "kaysaydi kapi kor kalirdi"),
    ("edgeYedek", r"if\(plan\.kanon \|\| plan\.tokens\.length\)",
     lambda s: s.replace("if(plan.kanon || plan.tokens.length){", "if(false){"),
     "KANONIK eslestiricinin verdigi kume",
     "yedek yol serbest metni HIC SUZMUYOR: musteri Worker cokunce alakasiz "
     "kartlarla kalirdi"),
]

# ── BEKLEME EKSENI (faz3-bayrak.js::bekleKosul) ───────────────────────────────
BEKLE_IMZA = re.compile(
    r"^const bekleKosul = async \(kosul, tavanMs = (\d+), adimMs = \d+\) => \{$", re.M)
SABIT_UYKU = re.compile(r"await bekle\(\d+\);")
# Mutantta HEPSI kirmizi basilmali: her biri bir `await bekleKosul(` cagri yerinin
# render iddiasidir (TEST 2 · 2b · 6c · 6). Biri eksikse kirmizi YANLIS eksenden gelmistir.
IZ_IDDIALARI = (
    "kartlar cizildi",
    "Jeneratör kategorisi cizildi",
    "edge /katalog?kategori=Jeneratör cizildi",
    "ana sayfada 4 parametrik kart EN USTTE",
)


class BeklemeBozuk(Exception):
    """Canli tavan zaten <=0: eksen BOZUK — cap hatasi degil, KOR (rc=1)."""


def canli_tavan(src):
    imzalar = BEKLE_IMZA.findall(src)
    if len(imzalar) != 1:
        raise CapaHatasi("faz3-bayrak.js'te bekleKosul imzasi %d kez (1 olmali)"
                         % len(imzalar))
    return int(imzalar[0])


def bekleme_metni(src, yeni_tavan):
    """Kapi kaynaginda (1) tavan varsayilanini `yeni_tavan` yap, (2) her
    `await bekleKosul(` cagrisindan hemen onceki sabit `await bekle(n);`i kaldir.

    Onceki satira yururken bos ve `//` yorum satirlari atlanir; varilan satir sabit
    uyku DEGILSE CapaHatasi (maske varsayimi bayatladi)."""
    canli = canli_tavan(src)
    if yeni_tavan == canli:
        raise CapaHatasi("tavan donusumu ETKISIZ (%d -> %d)" % (canli, yeni_tavan))
    imza = BEKLE_IMZA.search(src).group(0)
    yeni_imza = imza.replace("tavanMs = %d," % canli, "tavanMs = %d," % yeni_tavan, 1)
    satirlar = src.replace(imza, yeni_imza, 1).split("\n")
    maske = 0
    for i, satir in enumerate(satirlar):
        if "await bekleKosul(" not in satir:
            continue
        j = i - 1
        while j >= 0 and (not satirlar[j].strip() or satirlar[j].strip().startswith("//")):
            j -= 1
        if j < 0 or not re.match(r"^\s*" + SABIT_UYKU.pattern, satirlar[j]):
            raise CapaHatasi("bekleKosul cagrisi (satir %d) oncesinde sabit "
                             "`await bekle(n);` YOK" % (i + 1))
        satirlar[j] = SABIT_UYKU.sub("", satirlar[j], count=1)
        maske += 1
    if maske == 0:
        raise CapaHatasi("faz3-bayrak.js'te `await bekleKosul(` cagrisi YOK")
    return "\n".join(satirlar), maske


def iz_capalari_dogrula(src):
    for ad in IZ_IDDIALARI:
        n = src.count('kontrol("%s"' % ad)
        if n != 1:
            raise CapaHatasi("iz iddiasi %r kaynakta %d kez (1 olmali)" % (ad, n))


def kapi_kos(kok):
    p = subprocess.run(["node", os.path.join(kok, "tools", "faz3-bayrak.js")],
                       cwd=kok, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def kirmizi_satirlar(cikti):
    return [s.strip() for s in cikti.splitlines() if s.strip().startswith("❌")]


def main():
    damga0 = agac_damgasi([INDEX, KAPI])
    ham = open(INDEX, encoding="utf-8").read()
    kapi_ham = open(KAPI, encoding="utf-8").read()
    try:
        harita = {ad: js_fonksiyon(ham, ad) for ad, _, _, _, _ in MUTANTLAR}
        tavan = canli_tavan(kapi_ham)
        if tavan <= 0:
            raise BeklemeBozuk("canli bekleKosul tavani %d" % tavan)
        kontrol_kapi, maske = bekleme_metni(kapi_ham, 2 * tavan)
        mutant_kapi, _ = bekleme_metni(kapi_ham, 0)
        iz_capalari_dogrula(kapi_ham)
    except CapaHatasi as e:
        print("OLCULEMEDI (capa): %s" % e)
        return 3
    except BeklemeBozuk as e:
        print("SONUC: KOR — %s: bekleme ekseni BOZUK (render iddialari bos DOM'a bakar)" % e)
        return 1

    tmp = tempfile.mkdtemp(prefix="faz3-mutasyon-")
    yakalanan, kacan, kontrol_dusen = 0, [], []
    try:
        kok = kopya_kok(tmp)
        # index.html KOPYA olmali: kopya_kok onu SEMBOLIK bagliyor, uzerine yazmak
        # CANLI dosyayi bozardi. Bagi sok, gercek kopyayi koy.
        hedef_index = os.path.join(kok, "index.html")
        os.unlink(hedef_index)
        shutil.copyfile(INDEX, hedef_index)
        # faz3-bayrak.js KOPYADIR (kopya_kok tools/'u kopyalar) — bekleme mutanti buraya.
        hedef_kapi = os.path.join(kok, "tools", "faz3-bayrak.js")
        if os.path.islink(hedef_kapi):
            print("OLCULEMEDI: kopya kokte faz3-bayrak.js sembolik bag — yazilamaz")
            return 3

        # BUILD ARTEFAKTI ONKOSULU (S7 onarimi, 19 Agu 2026): kapinin okudugu
        # ozet.json + taban-fiyatlar.js BUILD ARTEFAKTIdir, git'e girmez —
        # CI runner'inda ve taze klonda YOKTUR; kapi onsuz exit(1) verir ve
        # surucu "taban kirmizi" OLCULEMEDI'ye duserdi. Ayna fiksturlerini
        # GERCEK build koduyla kurar (sekil tek kaynakta kalsin diye elle
        # kopya DEGIL build.py bayraklari; --sadece-ozet'i vitrin-kabul.js de
        # kullanir). KOPYADAKI build.py cagrilir: onun ROOT'u AYNA kokudur,
        # --sadece-taban da oraya yazar — canli agaca bayt gitmez. Canli
        # agacta artefakt VARSA kopya_kok'un sembolik bagi onu gosterir ve o
        # kalem atlanir.
        for bayraklar, yol in (
                (["--sadece-ozet", "--cikti", os.path.join(kok, "ozet.json")],
                 os.path.join(kok, "ozet.json")),
                (["--sadece-taban"], os.path.join(kok, "taban-fiyatlar.js"))):
            if os.path.exists(yol):
                continue
            uret = subprocess.run(
                [sys.executable, os.path.join(kok, "tools", "build.py")] +
                bayraklar, cwd=kok, capture_output=True, text=True)
            if uret.returncode != 0 or not os.path.exists(yol):
                print("OLCULEMEDI: onkosul fiksturu kurulamadi (build.py %s "
                      "rc=%d)" % (bayraklar[0], uret.returncode))
                print((uret.stdout + uret.stderr).strip()[-400:])
                return 3
            print("onkosul: %s aynada uretildi (build.py %s, %d bayt)"
                  % (os.path.basename(yol), bayraklar[0],
                     os.path.getsize(yol)))

        rc, cikti = kapi_kos(kok)
        if rc != 0:
            print("OLCULEMEDI: MUTASYONSUZ kopyada kapi zaten KIRMIZI (rc=%d) — "
                  "mutant hukmu verilemez" % rc)
            print("\n".join(kirmizi_satirlar(cikti)[:5]))
            return 3
        print("taban: mutasyonsuz kopyada kapi YESIL (rc=0)")

        for ad, desen, donusum, eksen, aciklama in MUTANTLAR:
            try:
                mutant = mutant_metni(harita, ham, [(ad, desen, donusum)])
            except CapaHatasi as e:
                print("OLCULEMEDI (capa/%s): %s" % (ad, e))
                return 3
            open(hedef_index, "w", encoding="utf-8").write(mutant)
            try:
                rc, cikti = kapi_kos(kok)
            finally:
                shutil.copyfile(INDEX, hedef_index)
            kirmizi = kirmizi_satirlar(cikti)
            eksende = [s for s in kirmizi if eksen in s]
            if rc != 0 and eksende:
                yakalanan += 1
                print("  YAKALANDI %-20s rc=%d — %s" % (ad, rc, eksende[0][:110]))
            else:
                kacan.append(ad)
                print("  KACTI     %-20s rc=%d (beklenen eksen: %r) — %s"
                      % (ad, rc, eksen, aciklama))
                if kirmizi:
                    print("            gorulen kirmizi: %s" % kirmizi[0][:110])

        # BEKLEME EKSENI — once KONTROL: dusuyorsa mutantin kirmizisi ayirt edici DEGIL.
        print("bekleme ekseni: canli tavan %d ms, maskelenen sabit uyku %d" % (tavan, maske))
        open(hedef_kapi, "w", encoding="utf-8").write(kontrol_kapi)
        try:
            rc, cikti = kapi_kos(kok)
        finally:
            shutil.copyfile(KAPI, hedef_kapi)
        kirmizi = kirmizi_satirlar(cikti)
        ad = "bekleKosul-tavan%d" % (2 * tavan)
        if rc == 0 and not kirmizi:
            print("  KONTROL   %-20s rc=0 YESIL (uykusuz, davranis-notr)" % ad)
        else:
            kontrol_dusen.append(ad)
            print("  KONTROL-DUSTU %-16s rc=%d, %d kirmizi — mutant AYIRT EDICI DEGIL"
                  % (ad, rc, len(kirmizi)))
            if kirmizi:
                print("            gorulen kirmizi: %s" % kirmizi[0][:110])

        ad = "bekleKosul-tavan0"
        if kontrol_dusen:
            kacan.append(ad)
            print("  KACTI     %-20s (kontrol dustugu icin hukum verilmedi)" % ad)
        else:
            open(hedef_kapi, "w", encoding="utf-8").write(mutant_kapi)
            try:
                rc, cikti = kapi_kos(kok)
            finally:
                shutil.copyfile(KAPI, hedef_kapi)
            kirmizi = set(kirmizi_satirlar(cikti))
            eksik = [a for a in IZ_IDDIALARI if "❌ " + a not in kirmizi]
            if rc != 0 and not eksik:
                yakalanan += 1
                print("  YAKALANDI %-20s rc=%d — iz %d/%d render iddiasi: %s"
                      % (ad, rc, len(IZ_IDDIALARI), len(IZ_IDDIALARI),
                         " · ".join(IZ_IDDIALARI)))
            else:
                kacan.append(ad)
                print("  KACTI     %-20s rc=%d — dusmeyen render iddiasi: %s"
                      % (ad, rc, " · ".join(eksik) or "(yok; rc=0)"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    damga1 = agac_damgasi([INDEX, KAPI])
    print("\nagac damgasi: %s -> %s" % (damga0, damga1))
    if damga0 != damga1:
        print("OLCULEMEDI: CANLI AGAC DEGISTI — hukum verilemez")
        return 3
    print("MUTASYON: %d/%d yakalandi · KONTROL: %d/1 yesil"
          % (yakalanan, len(MUTANTLAR) + 1, 1 - len(kontrol_dusen)))
    if kacan:
        print("SONUC: KOR — kacan mutant(lar): %s" % ", ".join(kacan))
        return 1
    print("SONUC: KIRMIZI-YANDI (tum mutantlar beklenen eksende yakalandi, kontrol yesil)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

CANLI AĞACA TEK BAYT YAZILMAZ ([[kapi-yan-etkisi-gizli-onkosul]]): mutasyon
`tools/mutasyon_kopya.py::kopya_kok` ile kurulan geçici köke uygulanır; orada `tools/`
ve `index.html` GERÇEK KOPYADIR, `urunler.json` / `ozet.json` / `taban-fiyatlar.js` /
`secenekler.js` sembolik bağdır (ölçüm gerçek katalogda kalır). Ağacın değişmediği
baş/son `agac_damgasi()` ile KANITLANIR.

ÇAPA ELLE YAZILMAZ ([[mutasyon-kaniti-yeniden-uretilebilir]]): hedef gövdeler
`index.html`den FONKSİYON ADIYLA ayıklanır; ayıklama tutmazsa ya da dönüşüm etkisiz
kalırsa hüküm OLCULEMEDI değil KIRMIZI'dır (rc=3).

ÇIKIŞ: rc=0 tüm mutantlar yakalandı · rc=1 en az bir mutant KAÇTI (kapı kör) ·
rc=3 çapa/kurulum bozuk (ölçülemedi).
"""
import os
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
     "uyeligi olan HER urun sonucta",
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


def kapi_kos(kok):
    p = subprocess.run(["node", os.path.join(kok, "tools", "faz3-bayrak.js")],
                       cwd=kok, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def kirmizi_satirlar(cikti):
    return [s.strip() for s in cikti.splitlines() if s.strip().startswith("❌")]


def main():
    damga0 = agac_damgasi([INDEX, KAPI])
    ham = open(INDEX, encoding="utf-8").read()
    try:
        harita = {ad: js_fonksiyon(ham, ad) for ad, _, _, _, _ in MUTANTLAR}
    except CapaHatasi as e:
        print("OLCULEMEDI (capa): %s" % e)
        return 3

    tmp = tempfile.mkdtemp(prefix="faz3-mutasyon-")
    yakalanan, kacan = 0, []
    try:
        kok = kopya_kok(tmp)
        # index.html KOPYA olmali: kopya_kok onu SEMBOLIK bagliyor, uzerine yazmak
        # CANLI dosyayi bozardi. Bagi sok, gercek kopyayi koy.
        hedef_index = os.path.join(kok, "index.html")
        os.unlink(hedef_index)
        shutil.copyfile(INDEX, hedef_index)

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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    damga1 = agac_damgasi([INDEX, KAPI])
    print("\nagac damgasi: %s -> %s" % (damga0, damga1))
    if damga0 != damga1:
        print("OLCULEMEDI: CANLI AGAC DEGISTI — hukum verilemez")
        return 3
    print("MUTASYON: %d/%d yakalandi" % (yakalanan, len(MUTANTLAR)))
    if kacan:
        print("SONUC: KOR — kacan mutant(lar): %s" % ", ".join(kacan))
        return 1
    print("SONUC: KIRMIZI-YANDI (tum mutantlar beklenen eksende yakalandi)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

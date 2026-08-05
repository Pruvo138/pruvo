#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ege-bilgi.md "MALZEME KAPSAMI" bolumunu tools/filamentler.json'dan uretir/gunceller.

Kullanim:  python3 tools/ege-malzeme.py

NEDEN: Ege'nin malzeme anlatimi ile sitedeki filament rehberi AYNI referanstan
beslensin (tek kaynak) — ikisi asla celismesin. Bolum, dosyadaki isaretciler
arasina yazilir; isaretci yoksa (ilk calisma) "### MALZEME KAPSAMI" basligindan
bir sonraki "## " basligina kadar olan blok isaretcili blokla DEGISTIRILIR.
Dosyanin geri kalanina DOKUNULMAZ. Idempotent: ayni girdiyle ikinci calisma
dosyayi degistirmez. (ege-bilgi.md public — sir icermez; pruvo-bot reposuna dokunmaz.)
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filament_ortak

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EGE = os.path.join(ROOT, "ege-bilgi.md")
# 🔴 ISARETCI METNI DE TAVAN BUTCESINDEN YER (5 Agu): bu iki yorum satiri Ege'nin
# gordugu metne AYNEN girer (bot ham .md ceker, markdown RENDER ETMEZ) ama Ege'ye
# hicbir OLGU tasimaz — bakimci notudur. Eski BASLA 105 UTF-16 birimiydi; "kaynak
# tools/filamentler.json" isareti buradan KALKTI ve yukaridaki modul docstring'inde
# (satir 3) DURUYOR -> bakimci bilgisi kaybolmadi, Ege'nin butcesinden 33 birim dondu.
BASLA = "<!-- FILAMENT-REF-BASLA · URETILIR: tools/ege-malzeme.py · ELLE DUZENLEME -->"
BITIR = "<!-- FILAMENT-REF-BITIR -->"


def _isi_yuvasi(f):
    """Kalem satirinin UCUNCU yuvasi. Deger SAYISAL sicaklik degilse basina 'ısı ' konur.

    🔴 NEDEN (5 Agu, bagimsiz curutucu bulgusu): eski bicimde her kalemde " — ısı DEGER — "
    yaziyordu; sikistirmada " — ısı " ayraci dustu ve yuva "(ETIKET, DEGER)" oldu. Alti
    kalemin BESINDE deger sayisal ("~55-60°C") oldugu icin yuva kendini anlatiyor, ama
    Karbon kaleminin degeri "taşıyıcıya göre" -> "(En yüksek mukavemet, taşıyıcıya göre)"
    okunusu "MUKAVEMET taşıyıcıya göre" cagrisimi veriyordu. Bu, iki satir asagidaki
    "karbon katkı ISI dayanımını ARTIRMAZ ... mukavemet/sertlik için öner" kuralinin TERSI
    anlama gelir. Kural veri-guduml u: '°' tasimayan her degere onek konur, Karbon'a ozel
    dallanma YAZILMAZ (ozel dallanma yeni bir kalemde sessizce bayatlardi)."""
    isi = f["isiDayanimi"]
    return isi if "°" in isi else "ısı " + isi


def bolum_uret():
    ref = filament_ortak.referans()
    satirlar = []
    for f in ref["filamentler"]:
        if not f.get("site"):
            continue
        # BICIM (5 Agu): "- **AD** (ETIKET) — ısı DEGER — KISA" -> "- **AD** (ETIKET,
        # DEGER): KISA". Iskele 21 -> 14 birim; "ısı " oneki DUSTU cunku ustteki grup
        # basligi olcutu zaten adiyla soyluyor ("ısı = HDT @ 0.45 MPa") ve deger °C
        # tasiyor. OLGU KAYBI YOK: ad · etiket · isi araligi · kisa metin AYNEN duruyor,
        # yalnizca ayiraclar kisaldi. Kalem BASINA -6/-7 birim -> yeni filament eklemenin
        # MARJINAL maliyeti de duser (bu isin asil amaci: tavan payi tek seferlik
        # acilmasin, EGIM de dussun).
        satirlar.append("- **%s** (%s, %s): %s"
                        % (f.get("uzunAd") or f["ad"], f["kisaEtiket"],
                           _isi_yuvasi(f), f["kisa"]))
    ozel_satirlar = []
    for f in ref["filamentler"]:
        if f.get("site"):
            continue
        # 🔴 TEKRAR ETMEYEN KUYRUK (27 Tem): "standart siparis akisinda YOK, WhatsApp ozel
        # talebiyle degerlendirilir — uretim kararidir, kosulu netlestir" kuyrugu ESKIDEN
        # HER kalemde tekrar ediliyordu. Kuyruk ARTIK bir kez, asagidaki GRUP BASLIGINDA
        # duruyor. OLCULDU (UTF-16 birimi): tam kuyruk 110 x 2 dongu kalemi (ABS, Karbon)
        # + kisa varyanti 37 x 1 (asagidaki Naylon satiri) = 257 kalkti, grup basligi 88
        # buyudu -> NET 169. Tekrarlar ESIT DEGILDI: Naylon satiri kuyrugun yalnizca son
        # cumlesini tasiyordu — "3 esit tekrar" diye okuma.
        # NEDEN onemli: ege-bilgi.md Ege'nin HER mesajinda prompta enjekte edilir ve
        # pruvo-bot/worker/src/index.js icinde .slice(0, 6000) ile UTF-16 birimi uzerinden
        # KESILIR (sessizce, log yok) -> tekrar hem her mesajin butcesini hem tavan payini
        # yiyor. Olculdu: bu tekillestirme dosyayi 5761 -> 5592 u16'ya indirdi, tavan payi
        # 239 -> 408 (nobetci tools/ege-bilgi-tavan-test.py, GUVENLIK_MARJI=400 esigi asildi).
        # ⚠️ "+ [DEVRET]" HER KALEMDE KALIR (grup basligina TASINMADI): jeton sayisi
        # bilerek 7'de sabit tutuldu ve devret refleksi kalem duzeyinde gorunur kaldi.
        ozel_satirlar.append(
            "- **%s** (%s, %s) — [DEVRET]"
            % (f.get("uzunAd") or f["ad"], f["kisaEtiket"], _isi_yuvasi(f)))

    # Kategori -> varsayilan tavsiye ozeti (ayni listeyi paylasanlar gruplanir)
    gruplar, sira = {}, []
    for kat, liste in ref["kategoriTavsiye"].items():
        anahtar = repr(liste)
        if anahtar not in gruplar:
            gruplar[anahtar] = ([], liste)
            sira.append(anahtar)
        gruplar[anahtar][0].append(kat)
    oneriler = []
    for anahtar in sira:
        katlar, liste = gruplar[anahtar]
        parca = liste[0]["ad"]
        for t in liste[1:]:
            # .lower() KULLANMA: Python "Isınan"->"isınan" yapar (Turkce I/ı hatasi)
            parca += "; %s %s" % (t.get("not") or "alternatif", t["ad"])
        oneriler.append("%s → %s" % ("/".join(katlar), parca))

    return "\n".join([
        BASLA,
        # SIKISTIRMA (5 Agu, 289 -> 236 birim). JETON JETON KORUNAN OLGULAR:
        #   "özel üretim filamentleri" · "Ege SADECE bu aileden" · "seçenek sunar" ·
        #   "adını da söyleyebilir" · "sitede doğrudan sipariş edilen" (= standart aile
        #   tanimi) · "dürüst değerleri" · "HDT @ 0.45 MPa" · "yaklaşık aralık" ·
        #   "abartma, taahhüt sayılır".
        # 🔴 "uygun olanı önerebilir" GERI KONDU (5 Agu, curutucu): sikistirmada bu ONERME
        #   IZNI "seçenek sunar" ile ayni sayilip dusurulmustu. Degiller: "sunar" secenegi
        #   ONUNE KOYAR, "önerebilir" ARALARINDAN SECIP TAVSIYE ETME iznidir. Izin
        #   dustugunde Ege'nin asiri temkinli davranmasi (secenekleri sayip tavsiye
        #   vermemesi) mumkun; izin tek tek verilir, ortuk BIRAKILMAZ.
        "Malzememiz = özel üretim **filamentleri**; Ege SADECE bu aileden seçenek sunar, uygun "
        "olanı önerebilir, adını da söyleyebilir. Standart aile (sitede doğrudan sipariş edilen) "
        "ve dürüst değerleri (ısı = HDT @ 0.45 MPa, yaklaşık aralık; abartma, taahhüt sayılır):",
    ] + satirlar + [
        "",
        # GRUP BASLIGI = kalemlerden HOISTLANMIS ortak kuyruk (yukaridaki nota bak).
        # "hepsi" kelimesi KASITLI: kuralin asagidaki HER kaleme uygulandigini modele
        # acikca soyler (kuyruk kalemlerden kalktigi icin kapsam ortuk BIRAKILMAZ).
        # SIKISTIRMA (5 Agu, 165 -> 143): "standart ailenin dışında" ile "standart
        # sipariş akışında YOK" AYNI iddianin iki yazimidir — "standart aile"nin tanimi
        # ustteki giris satirinda "sitede doğrudan sipariş edilen" olarak veriliyor.
        # Ikisi TEK cumlede birlestirildi; "hepsi" · "WhatsApp özel talebi" · "üretim
        # kararıdır" · "koşulu netleştir" jetonlari AYNEN duruyor.
        "Mühendislik malzemeleri — hepsi standart sipariş akışının DIŞINDA; WhatsApp özel "
        "talebiyle değerlendirilir, üretim kararıdır, koşulu netleştir:",
    ] + ozel_satirlar + [
        "- **Daha yüksek ısı / mukavemet:** Naylon (PA) ve elyaf katkılı türler tedarik "
        "edilebilir — [DEVRET]",
        "",
        # "Kategoriye göre varsayılan tavsiyemiz: " -> "Kategori varsayılanı: " (-17):
        # ayni haritanin basligi, ayni iddia. Harita GOVDESINE dokunulmadi.
        "Kategori varsayılanı: " + " · ".join(oneriler) + ".",
        # 🔴 EVSIZ KALAN JETONLARIN YENI EVI (5 Agu). ege-bilgi.md'deki elle yazili
        # "## Malzeme / dayanım rehberi" govdesi (277 birim) KALDIRILDI cunku icerdigi
        # kullanim->ozellik haritasi ("iç mekan → standart · dış/güneş → UV+havaya
        # dayanıklı · yağmur/su/nem → suya dayanıklı · yük/darbe → tok+sağlam") artik
        # ASAGIDAKI filament listesinin kisaEtiket/kisa alanlarinda ve kategori
        # haritasinda DAHA YUKSEK COZUNURLUKLE duruyor (o satir, Ege'nin malzeme ADI
        # ANAMADIGI donemden kalma bir fosildi; kural 77517392 ile tersine dondu).
        # AMA uc jeton BASKA HICBIR YERDE gecmiyordu; KIRPILMADI, buraya TASINDI:
        #   (1) "kullanım yerine göre seç"  (2) "deniz/tuzlu su → su+tuza dirençli"
        #   (3) "Emin değilsen uydurma: araştırıp döneceğini söyle + [DEVRET]"
        # Dorduncu jeton "motor/ısı → kaç dereceye dayanmalı sor" asagidaki KRITIK
        # satirina tasindi ("motor/yüksek ısı" + zaten duran "kaç derece").
        "Seçimi kullanım yerine göre yap; deniz/tuzlu su → su+tuza dirençli olanı seç. "
        "Emin değilsen uydurma: araştırıp döneceğini söyle + [DEVRET].",
        "ÖNEMLİ: karbon katkı ISI dayanımını ARTIRMAZ, taşıyıcınınkini korur (PETG-CF ~70°C); "
        "karbonu mukavemet/sertlik için öner, ısıda taşıyıcıya bak.",
        "",
        # SIKISTIRMA (5 Agu, 200 -> 160). "Bunlar bizim sürecimizde YOK" + "sunulması
        # yakışık almaz, yalan söz olur" -> "sürecimizde YOK, sunmak yalan söz olur":
        # "yakışık almaz" ile "yalan söz olur" AYNI normatif iddianin iki yazimiydi;
        # gucu YUKSEK olan tutuldu. YASAK LISTESI (NBR · FKM/Viton · EPDM · silikon ·
        # metal · cam) AYNEN duruyor — malzeme-dayanak-test.py bu jetonlari olcuyor,
        # kirpilmalari kapiyi da korlestirirdi.
        # NOT: "malzeme" kelimesi BILEREK GERI KONDU (8 birim). Yasagin oznesi ("filament
        # DIŞI ne?") ortuk birakilmaz — bu satir kapsam yasaginin ANA capasi; 8 birim
        # ugruna belirsizlestirmek kirpma yasaginin tam olarak yasakladigi seydir.
        "**ASLA filament DIŞI malzeme sunma/taahhüt etme** — sürecimizde YOK, sunmak yalan söz olur: "
        "kalıp/döküm KAUÇUK-elastomer (NBR, FKM/Viton, EPDM, silikon), metal, cam vb.",
        "",
        # 🔴 1 Agu: "uygun filamenti + fiyati belirleyip ILETECEGINI soyle" KALDIRILDI.
        # Okan'in kurali: fiyati VE uretilebilirlik/malzeme kararini Okan/ekip verir;
        # Ege KOSULU toplar, karari DEVREDER, "ileteceğim" DEMEZ. Satirin geri kalani
        # (kosul toplama + "Kesin performans garantisi verme") KORUNDU.
        # SIKISTIRMA (5 Agu): iki cumle tek cumleye indi; "motor/" jetonu KALDIRILAN
        # rehber satirindan BURAYA tasindi (yukaridaki nota bak). Korunan jetonlar:
        # yakıt · yağ · kimyasal teması · yüksek ısı · gıda · yüksek yük · "üretim
        # kararıdır" · hangi sıvı/yakıt · sürekli mi ara sıra mı · kaç derece · esnek mi
        # sert mi · "araştırıp döneceğini söyle + [DEVRET]" · "Malzeme ve fiyat kararı
        # bizde" · "Kesin performans garantisi verme".
        "- Malzemenin KRİTİK olduğu işte (yakıt/yağ/kimyasal teması, motor/yüksek ısı, gıda, "
        "yüksek yük) bir filamentin şartı karşılayıp karşılamadığı ÜRETİM KARARIDIR: koşulu net "
        "topla (hangi sıvı/yakıt · sürekli mi ara sıra mı · kaç derece · esnek mi sert mi), "
        "araştırıp döneceğini söyle + [DEVRET]. Malzeme ve fiyat kararı bizde; kesin performans "
        "garantisi verme.",
        # 🔴 GERI ALINDI (5 Agu, bagimsiz curutucu — TEK BLOKLAYICI bulgu).
        # Sikistirma turunda bu satirin kuyrugu "ama filament-dışı bir malzemeyi çözüm diye
        # sunma" -> "ama çözüm DAİMA filament olsun" yapilmisti. YANLIS: ikisi ayni iddia
        # DEGIL. Ilki bir YASAK (filament-disi malzemeyi COZUM DIYE sunma), ikincisi MUTLAK
        # bir OLUMLU HUKUM (cozum daima filament olacak) ve ayni belgenin l.10'undaki
        # ONAYLI istisnasiyla CELISIR:
        #   "TEK İSTİSNA — GÖMME SOMUN: ... hazır gömme somun (threaded/heat-set insert)
        #    yuvası açıp somunu oturturuz; rahatça sun."
        # Gomme somun METALDIR. Eski yazim celismiyordu (somun "cozum diye sunulan malzeme"
        # degil, bizim parcamiza oturttugumuz baglanti elemani); yeni yazim istisnasiz oldugu
        # icin ONAYLANMIS bir satisi reddettirebilir. Ustelik l.10'un tasarimi "yasak +
        # ISTISNASI BITISIK" iken bu ucuncu mutlak hukum ondan UZAKTA ve istisnasiz duruyordu;
        # iki zit talimat AYNI prompta gidince cevap RASTGELELESIR ve hicbir alarm calmaz.
        # DERS: sikistirma yalniz iddia DUSUREBILIR diye denetlenmisti; iddia EKLEYEBILDIGI
        # olculdu -> denetim artik EKLENEN jetonlari da tabloluyor.
        "- Uzmanlığını doğru soruları sorarak göster; eğitici olabilirsin (\"yanlış malzeme yakıtta "
        "şişer/bozulur, o yüzden koşulu netleştiriyorum\") ama filament-dışı bir malzemeyi çözüm "
        "diye sunma.",
        BITIR,
    ])


def main():
    with io.open(EGE, encoding="utf-8") as f:
        icerik = f.read()
    blok = bolum_uret()

    if BASLA in icerik and BITIR in icerik:
        yeni = re.sub(re.escape(BASLA) + r".*?" + re.escape(BITIR), lambda m: blok,
                      icerik, count=1, flags=re.S)
    else:
        # Ilk calisma: "MALZEME KAPSAMI" basligindan sonraki "## " basligina kadar degistir.
        # Baslik SEVIYESI serbest (`##+`): 5 Agu'da ust baslik ("## Malzeme / dayanım
        # rehberi") govdesiz kaldigi icin kaldirildi ve bu baslik ### -> ## seviyesine
        # cikti. Seviyeyi sabitleyen eski desen o anda SESSIZCE eslesmez olurdu.
        m = re.search(r"(##+ MALZEME KAPSAMI[^\n]*\n).*?(?=^## )", icerik, flags=re.S | re.M)
        if not m:
            sys.exit("ege-bilgi.md'de 'MALZEME KAPSAMI' bolumu bulunamadi — dosyaya dokunulmadi.")
        yeni = icerik[:m.start()] + m.group(1) + blok + "\n\n" + icerik[m.end():]

    if yeni == icerik:
        print("ege-bilgi.md zaten guncel (degisiklik yok).")
        return
    with io.open(EGE, "w", encoding="utf-8") as f:
        f.write(yeni)
    print("ege-bilgi.md MALZEME KAPSAMI bolumu filamentler.json'dan guncellendi.")


if __name__ == "__main__":
    main()

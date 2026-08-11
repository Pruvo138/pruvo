#!/usr/bin/env python3
"""FAZ 1 — ozet.json BAYT ATIFI + katalogla BÜYÜME EĞİMİ (yalnız ÖLÇÜM).

`tools/paket-ozet-butce.md` FAZ 1: hangi kolun (a: kart temsili / b: markalar haritası)
ne kazandırdığı **bugünkü artefakttan** ölçülmeden kod yazılmaz. Bu betik hiçbir üretim
dosyasını DEĞİŞTİRMEZ, ağa ÇIKMAZ, rastgelelik kullanmaz.

Ölçtükleri:
  1) ozet.json'un her ÜST DÜZEY anahtarının bayt payı. Atıf, artefaktın GERÇEK
     baytıyla birebir uyuşmalıdır (fark 0 değilse BEYAN edilir, gizlenmez).
  2) Her anahtarın katalogla büyüme eğimi: özet EN AZ İKİ farklı katalog boyutunda
     GERÇEK build koduyla (build.render_ozet) yeniden üretilir, eğim ürün başına
     bayt olarak hesaplanır. Eğim TAHMİN EDİLMEZ, iki ölçüm noktasından türetilir.
     İki kırpma modu ayrı ölçülür:
       kuyruk = katalogun ESKİ ucu (yeni ürün başa eklendiği için tarihsel yakınsama)
       bas    = katalogun YENİ ucu (bugünkü kart metinleriyle üst sınır)
  3) Kol (a) tavanı: kart temsilinde bugün TEKRAR EDEN/atılabilir bayt. Merdivenin her
     basamağı KAYIPSIZ bir temsil dönüşümüdür ve kazanç TAHMİN değil, dönüştürülmüş
     artefaktın gerçek serileştirmesinden ÖLÇÜLÜR. Dönüşümler yalnız bu betiğin
     belleğinde yapılır; build.py'ye dokunulmaz.
  4) Kol (b) tavanı: `markalar` haritasının büyüklüğü, marka dağılımı, kayıpsız
     interning kazancı ve eşikle kırpma eğrisi (hangi eşik ne kazandırır, karşılığında
     kaç marka çipi düşer).

Kullanım:  python3 tools/ozet-bayt-atifi.py [--json <yol>]
Çıkış kodu 0 = ölçüm tamam; 2 = atıf artefaktla uyuşmadı (ölçüm güvenilmez).
"""

import contextlib
import io
import json
import os
import sys
import zlib

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
KATALOG = os.path.join(KOK, "urunler.json")


def build_modulu():
    """tools/build.py'yi MODÜL olarak yükle — özetin şekli TEK KAYNAKTA kalsın.
    (Kendi kopyasını hesaplayan ölçüm, ölçtüğü şeyden sessizce ayrışır.)"""
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import build  # noqa: E402
    return build


def dump(v):
    """build.render_ozet ile BİREBİR aynı serileştirme (ayrışırsa atıf yanlış olur)."""
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def bayt(s):
    return len(s.encode("utf-8"))


# --------------------------------------------------------------- 1) anahtar bayt atıfı
def anahtar_paylari(metin):
    """Her üst düzey anahtarın payı = "anahtar":deger + kendi ayırıcı virgülü.
    Çerçeve (süslü parantez) ayrı kalem. Toplam artefaktın baytına EŞİT olmalı."""
    ozet = json.loads(metin)          # py3.7+: anahtar sırası artefaktla aynı
    anahtarlar = list(ozet)
    paylar = {}
    for i, k in enumerate(anahtarlar):
        seg = dump(k) + ":" + dump(ozet[k])
        if i < len(anahtarlar) - 1:
            seg += ","
        paylar[k] = bayt(seg)
    cerceve = 2                        # '{' + '}'
    toplam = bayt(metin)
    fark = toplam - (sum(paylar.values()) + cerceve)
    return ozet, paylar, cerceve, toplam, fark


# ----------------------------------------------------------------- kart yardımcıları
def kart_kesitleri(ozet):
    """Kart TAŞIYAN üst düzey kesitler (sırayla) — (ad, liste) çiftleri."""
    kesitler = [("parametrik", ozet["parametrik"])]
    for kat in ozet["bloklar"]:
        kesitler.append(("bloklar/" + kat, ozet["bloklar"][kat]))
    kesitler.append(("yeni", ozet["yeni"]))
    return kesitler


def tum_kartlar(ozet):
    kartlar = []
    for _, liste in kart_kesitleri(ozet):
        kartlar.extend(liste)
    return kartlar


def alan_paylari(ozet):
    """Kart dizilerinde ALAN başına bayt (değer + kendi ayırıcısı)."""
    alanlar = ozet["kartAlanlari"]
    pay = {a: 0 for a in alanlar}
    bos_yer = 0        # ara konumdaki null dolgu
    yapisal = 0        # köşeli parantez + virgül
    for kart in tum_kartlar(ozet):
        yapisal += 2 + max(0, len(kart) - 1)
        for i, v in enumerate(kart):
            b = bayt(dump(v))
            pay[alanlar[i]] += b
            if v is None:
                bos_yer += b
    return pay, bos_yer, yapisal


# ------------------------------------------------- 3) kol (a): kart temsili merdiveni
def ortak_onek(degerler):
    if not degerler:
        return ""
    onek = degerler[0]
    for d in degerler[1:]:
        while not d.startswith(onek):
            onek = onek[:-1]
            if not onek:
                return ""
    return onek


def kart_temsili_uygula(ozet, secenekler):
    """ozet'in KAYIPSIZ dönüştürülmüş bir kopyasını üretir (yalnız ölçüm için).

    secenekler: alt küme of {"gorsel_onek","kategori_indeks","marka_indeks",
                             "metin_havuzu","tekil_kart"}
    Her dönüşüm için gereken başlık (tablo) artefakta EKLENİR, yani maliyeti
    kazancın içinde sayılır. Kart DEĞERLERİ korunur — yalnız temsil değişir.
    """
    yeni = dict(ozet)
    alanlar = list(ozet["kartAlanlari"])
    i_kat = alanlar.index("kategori")
    i_marka = alanlar.index("marka")
    i_gorsel = alanlar.index("gorsel")
    i_baslik = alanlar.index("baslik")
    i_aciklama = alanlar.index("aciklama")

    kesitler = kart_kesitleri(ozet)

    onek = ""
    if "gorsel_onek" in secenekler:
        gorseller = [k[i_gorsel] for _, l in kesitler for k in l
                     if len(k) > i_gorsel and isinstance(k[i_gorsel], str)]
        onek = ortak_onek(gorseller)

    kat_indeks = {k: i for i, k in enumerate(ozet["kategoriler"])}

    marka_adlari = []
    if "marka_indeks" in secenekler:
        gorulen = {}
        for _, liste in kesitler:
            for k in liste:
                if len(k) > i_marka and isinstance(k[i_marka], list):
                    for m in k[i_marka]:
                        if m not in gorulen:
                            gorulen[m] = len(marka_adlari)
                            marka_adlari.append(m)
        marka_indeks = gorulen
    else:
        marka_indeks = {}

    def kart_donustur(kart):
        k = list(kart)
        if "gorsel_onek" in secenekler and onek and len(k) > i_gorsel \
                and isinstance(k[i_gorsel], str):
            k[i_gorsel] = k[i_gorsel][len(onek):]
        if "kategori_indeks" in secenekler and len(k) > i_kat \
                and k[i_kat] in kat_indeks:
            k[i_kat] = kat_indeks[k[i_kat]]
        if "marka_indeks" in secenekler and len(k) > i_marka \
                and isinstance(k[i_marka], list):
            k[i_marka] = [marka_indeks[m] for m in k[i_marka]]
        return k

    donusmus = [(ad, [kart_donustur(k) for k in liste]) for ad, liste in kesitler]

    # METİN HAVUZU: iki ve daha fazla kartta AYNI geçen başlık/açıklama tek kez taşınır.
    metinler = []
    if "metin_havuzu" in secenekler:
        sayac = {}
        for _, liste in donusmus:
            for k in liste:
                for idx in (i_baslik, i_aciklama):
                    if len(k) > idx and isinstance(k[idx], str) and k[idx]:
                        sayac[k[idx]] = sayac.get(k[idx], 0) + 1
        havuz = {}
        for _, liste in donusmus:
            for k in liste:
                for idx in (i_baslik, i_aciklama):
                    if len(k) > idx and isinstance(k[idx], str) and k[idx] \
                            and sayac[k[idx]] > 1:
                        if k[idx] not in havuz:
                            havuz[k[idx]] = len(metinler)
                            metinler.append(k[idx])
                        k[idx] = havuz[k[idx]]

    # TEKİL KART: kesitler arası (ve içi) birebir aynı kart tek kez taşınır, kesitler
    # tam sayı referans tutar.
    kart_tablosu = []
    if "tekil_kart" in secenekler:
        indeks = {}
        yeni_kesitler = []
        for ad, liste in donusmus:
            refler = []
            for k in liste:
                anahtar = dump(k)
                if anahtar not in indeks:
                    indeks[anahtar] = len(kart_tablosu)
                    kart_tablosu.append(k)
                refler.append(indeks[anahtar])
            yeni_kesitler.append((ad, refler))
        donusmus = yeni_kesitler

    yeni["parametrik"] = donusmus[0][1]
    yeni["bloklar"] = {ad.split("/", 1)[1]: liste for ad, liste in donusmus[1:-1]}
    yeni["yeni"] = donusmus[-1][1]
    if "gorsel_onek" in secenekler and onek:
        yeni["gorselOnEk"] = onek
    if "marka_indeks" in secenekler:
        yeni["markaAdlari"] = marka_adlari
    if "metin_havuzu" in secenekler:
        yeni["metinler"] = metinler
    if "tekil_kart" in secenekler:
        yeni["kartlar"] = kart_tablosu
    return yeni


def kart_temsili_geri(yeni, secenekler, alanlar):
    """A merdiveninin TERSİ — dönüşümün gerçekten KAYIPSIZ olduğunu kanıtlar.

    Kanıtsız "kayıpsız" iddiası, mimara olmayan bir tavan gösterirdi: tavan tablosu
    yalnız bu geri dönüşüm orijinal kartları BİREBİR verirse yayımlanır.
    """
    i_kat = alanlar.index("kategori")
    i_marka = alanlar.index("marka")
    i_gorsel = alanlar.index("gorsel")
    i_baslik = alanlar.index("baslik")
    i_aciklama = alanlar.index("aciklama")
    kat_adlari = list(yeni["kategoriler"])
    onek = yeni.get("gorselOnEk", "")
    marka_adlari = yeni.get("markaAdlari", [])
    metinler = yeni.get("metinler", [])
    tablo = yeni.get("kartlar", [])

    kesitler = [("parametrik", yeni["parametrik"])]
    for kat in yeni["bloklar"]:
        kesitler.append(("bloklar/" + kat, yeni["bloklar"][kat]))
    kesitler.append(("yeni", yeni["yeni"]))

    geri = []
    for ad, liste in kesitler:
        kartlar = []
        for oge in liste:
            k = list(tablo[oge]) if "tekil_kart" in secenekler else list(oge)
            if "metin_havuzu" in secenekler:
                for idx in (i_baslik, i_aciklama):
                    if len(k) > idx and isinstance(k[idx], int):
                        k[idx] = metinler[k[idx]]
            if "marka_indeks" in secenekler and len(k) > i_marka \
                    and isinstance(k[i_marka], list):
                k[i_marka] = [marka_adlari[i] for i in k[i_marka]]
            if "kategori_indeks" in secenekler and len(k) > i_kat \
                    and isinstance(k[i_kat], int):
                k[i_kat] = kat_adlari[k[i_kat]]
            if "gorsel_onek" in secenekler and len(k) > i_gorsel \
                    and isinstance(k[i_gorsel], str):
                k[i_gorsel] = onek + k[i_gorsel]
            kartlar.append(k)
        geri.append((ad, kartlar))
    return geri


KOL_A_MERDIVEN = [
    ("A0 bugunku temsil (v2 sabit sirali dizi)", set()),
    ("A1 + gorsel ortak oneki basliga", {"gorsel_onek"}),
    ("A2 + kategori adi -> kategoriler indeksi", {"gorsel_onek", "kategori_indeks"}),
    ("A3 + marka adi -> marka tablosu indeksi",
     {"gorsel_onek", "kategori_indeks", "marka_indeks"}),
    ("A4 + tekrar eden baslik/aciklama metin havuzu",
     {"gorsel_onek", "kategori_indeks", "marka_indeks", "metin_havuzu"}),
    ("A5 + kesitler arasi tekil kart tablosu",
     {"gorsel_onek", "kategori_indeks", "marka_indeks", "metin_havuzu", "tekil_kart"}),
]


# ------------------------------------------------------- 4) kol (b): markalar haritası
def marka_interning(markalar):
    """KAYIPSIZ: marka ADI yerine global marka tablosunda indeks (çip kaybı YOK)."""
    adlar = []
    indeks = {}
    for kat in markalar:
        for m in markalar[kat]:
            if m not in indeks:
                indeks[m] = len(adlar)
                adlar.append(m)
    yeni = {kat: {str(indeks[m]): a for m, a in markalar[kat].items()} for kat in markalar}
    return yeni, adlar


def marka_kirp(markalar, esik):
    """KAYIPLI: adet < esik olan (kategori, marka) kaydı düşer."""
    return {kat: {m: a for m, a in markalar[kat].items() if a >= esik}
            for kat in markalar}


def marka_cipleri(markalar):
    cipler = set()
    for kat in markalar:
        cipler.update(markalar[kat])
    return cipler


def marka_global(markalar):
    """KISMİ KAYIP: kategori kırılımı düşer, çip EVRENİ ve global sayaç kalır."""
    g = {}
    for kat in markalar:
        for m, a in markalar[kat].items():
            g[m] = g.get(m, 0) + a
    return g


# ------------------------------------------------------------------------------ akış
def sessiz_render(build, urunler):
    """render_ozet'in UYARI çıktısı ölçüm tablosunu kirletmesin (sayısı raporlanır)."""
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        metin = build.render_ozet(urunler)
    return metin, tampon.getvalue().strip()


def yuzde(pay, toplam):
    return 100.0 * pay / toplam if toplam else 0.0


def main():
    build = build_modulu()
    with open(KATALOG, encoding="utf-8") as f:
        urunler = json.load(f)
    n_tam = len(urunler)

    tam_metin, tam_uyari = sessiz_render(build, urunler)
    ozet, paylar, cerceve, toplam, fark = anahtar_paylari(tam_metin)

    print("=" * 78)
    print("FAZ 1 — ozet.json BAYT ATIFI  (katalog %d urun, uretim %s)"
          % (n_tam, ozet.get("uretim")))
    print("=" * 78)
    print("artefakt (build.render_ozet, tam katalog): %d bayt (%.1f KB)"
          % (toplam, toplam / 1024.0))
    print("OZET_BUTCE: %d bayt | doluluk %%%.1f | kalan pay %d bayt"
          % (build.OZET_BUTCE, yuzde(toplam, build.OZET_BUTCE),
             build.OZET_BUTCE - toplam))
    if tam_uyari:
        print("render UYARI: %s" % tam_uyari.replace("\n", " | "))
    print("zlib -9 (referans, tavan DEGIL): %d bayt"
          % len(zlib.compress(tam_metin.encode("utf-8"), 9)))
    print()

    # --- 2) büyüme eğimi: iki kırpma modu × iki alt boyut
    noktalar = {}
    for mod in ("kuyruk", "bas"):
        for bolen in (2, 4):
            n = n_tam // bolen
            alt = urunler[:n] if mod == "bas" else urunler[n_tam - n:]
            metin, _ = sessiz_render(build, alt)
            o, p, _, t, f = anahtar_paylari(metin)
            noktalar[(mod, n)] = (p, t, f, len(tum_kartlar(o)))

    n_yari = n_tam // 2
    n_ceyrek = n_tam // 4

    print("-" * 78)
    print("ANAHTAR BASINA BAYT + BUYUME EGIMI (bayt/urun)")
    print("-" * 78)
    print("%-14s %10s %7s %10s %10s %10s %10s"
          % ("anahtar", "bayt", "%", "yari(kuy)", "egim(kuy)", "yari(bas)", "egim(bas)"))
    egimler = {}
    for k in paylar:
        p_kuy = noktalar[("kuyruk", n_yari)][0].get(k, 0)
        p_bas = noktalar[("bas", n_yari)][0].get(k, 0)
        e_kuy = (paylar[k] - p_kuy) / float(n_tam - n_yari)
        e_bas = (paylar[k] - p_bas) / float(n_tam - n_yari)
        egimler[k] = (e_kuy, e_bas)
        print("%-14s %10d %6.1f%% %10d %10.3f %10d %10.3f"
              % (k, paylar[k], yuzde(paylar[k], toplam), p_kuy, e_kuy, p_bas, e_bas))
    print("%-14s %10d %6.1f%% %10s %10s %10s %10s"
          % ("(cerceve {})", cerceve, yuzde(cerceve, toplam), "-", "-", "-", "-"))
    print("%-14s %10d %6.1f%%   ATIF FARKI: %d bayt %s"
          % ("TOPLAM", sum(paylar.values()) + cerceve,
             yuzde(sum(paylar.values()) + cerceve, toplam), fark,
             "(uyusuyor)" if fark == 0 else "(UYUSMUYOR — olcum guvenilmez)"))
    print()
    for mod, isim in (("kuyruk", "ESKI uc"), ("bas", "YENI uc")):
        print("toplam artefakt %s: tam %d B | yari(%d urun) %d B | ceyrek(%d urun) %d B"
              " | egim %.3f B/urun (yari->tam)"
              % (isim, toplam, n_yari, noktalar[(mod, n_yari)][1],
                 n_ceyrek, noktalar[(mod, n_ceyrek)][1],
                 (toplam - noktalar[(mod, n_yari)][1]) / float(n_tam - n_yari)))

    # 🔴 EĞİM YORUMU İÇİN KART SAYISI: havuzlar (bloklar/yeni) SABİT ADETLİ. Kart sayısı
    # üç boyutta da aynıysa o kesitin bayt oynaması BÜYÜME değil METİN BİLEŞİMİ gürültüsüdür;
    # eşik bu gürültüden türetilirse yanlış kol seçtirir.
    print("kart ADEDI (parametrik+bloklar+yeni): tam %d | kuyruk yari %d / ceyrek %d"
          " | bas yari %d / ceyrek %d"
          % (len(tum_kartlar(ozet)), noktalar[("kuyruk", n_yari)][3],
             noktalar[("kuyruk", n_ceyrek)][3], noktalar[("bas", n_yari)][3],
             noktalar[("bas", n_ceyrek)][3]))
    print("3 NOKTALI EGIM (ceyrek->yari, yari->tam) — dogrusalliktan sapma gorulsun:")
    for k in ("markalar", "parametrik", "kategoriler", "bloklar", "yeni"):
        satir = []
        for mod in ("kuyruk", "bas"):
            p4 = noktalar[(mod, n_ceyrek)][0].get(k, 0)
            p2 = noktalar[(mod, n_yari)][0].get(k, 0)
            satir.append("%s: %.3f -> %.3f"
                         % (mod, (p2 - p4) / float(n_yari - n_ceyrek),
                            (paylar[k] - p2) / float(n_tam - n_yari)))
        print("   %-13s %s" % (k, " | ".join(satir)))
    print()

    print("-" * 78)
    print("KESIT BASINA KART ADEDI + BAYT")
    print("-" * 78)
    for ad, liste in kart_kesitleri(ozet):
        b = bayt(dump(liste))
        print("   %-22s %5d kart | %8d B | kart basi %6.1f B"
              % (ad, len(liste), b, (b / float(len(liste)) if liste else 0.0)))
    print()

    # --- kart yüzeyi künyesi
    kartlar = tum_kartlar(ozet)
    tekil = {dump(k) for k in kartlar}
    a_pay, bos_yer, yapisal = alan_paylari(ozet)
    kart_bayt = sum(a_pay.values()) + yapisal
    print("-" * 78)
    print("KART YUZEYI (parametrik + bloklar + yeni)")
    print("-" * 78)
    print("kart ornegi: %d | TEKIL kart: %d | mukerrer ornek: %d"
          % (len(kartlar), len(tekil), len(kartlar) - len(tekil)))
    print("kart bayti (alanlar + yapisal): %d bayt = artefaktin %%%.1f'i"
          % (kart_bayt, yuzde(kart_bayt, toplam)))
    for a in ozet["kartAlanlari"]:
        if a_pay.get(a):
            print("   %-16s %8d B (%%%.1f kart yuzeyi)"
                  % (a, a_pay[a], yuzde(a_pay[a], kart_bayt)))
    print("   %-16s %8d B  (ara konumdaki null dolgu)" % ("(null)", bos_yer))
    print("   %-16s %8d B  (kose parantez + virgul)" % ("(yapisal)", yapisal))
    alanlar = ozet["kartAlanlari"]
    for ad in ("baslik", "aciklama", "gorsel", "id"):
        i = alanlar.index(ad)
        degerler = [k[i] for k in kartlar if len(k) > i and isinstance(k[i], str)]
        print("   TEKRAR: %-10s %d ornek -> %d tekil deger (mukerrer %d)"
              % (ad, len(degerler), len(set(degerler)),
                 len(degerler) - len(set(degerler))))
    # ÖRTÜŞME: `yeni` kesitindeki kartların kaçı ZATEN blok havuzlarında var? Bu kalem
    # kol (a)'nın en büyük tek parçasıdır ve KOŞULLUDUR (yeni ürünlerin kategorisine bağlı),
    # yani "bugün %100" ölçümü yarın için garanti değildir — temsil iki hali de taşımalı.
    blok_kartlari = set()
    for ad, liste in kart_kesitleri(ozet):
        if ad.startswith("bloklar/") or ad == "parametrik":
            blok_kartlari.update(dump(k) for k in liste)
    yeni_ort = [k for k in ozet["yeni"] if dump(k) in blok_kartlari]
    print("ORTUSME: 'yeni' %d kartin %d'i havuzlarda ZATEN var (%%%.1f) -> %d B tekrar"
          % (len(ozet["yeni"]), len(yeni_ort),
             yuzde(len(yeni_ort), len(ozet["yeni"])),
             sum(bayt(dump(k)) + 1 for k in yeni_ort)))
    gorseller = [k[alanlar.index("gorsel")] for k in kartlar
                 if len(k) > alanlar.index("gorsel")
                 and isinstance(k[alanlar.index("gorsel")], str)]
    print("gorsel ortak onek: %r (%d bayt x %d kart)"
          % (ortak_onek(gorseller), bayt(ortak_onek(gorseller)), len(gorseller)))
    print()

    # --- 3) kol (a) tavanı
    print("-" * 78)
    print("KOL (a) TAVANI — kart temsilinde KAYIPSIZ kazanc merdiveni")
    print("-" * 78)
    a0 = None
    kol_a_tavan = 0
    asil = [(ad, [list(k) for k in liste]) for ad, liste in kart_kesitleri(ozet)]
    for ad, sec in KOL_A_MERDIVEN:
        donusmus = kart_temsili_uygula(ozet, sec)
        b = bayt(dump(donusmus))
        # KAYIPSIZLIK KANITI: geri dönüşüm orijinal kartları BİREBİR vermeli.
        geri = kart_temsili_geri(json.loads(dump(donusmus)), sec, ozet["kartAlanlari"])
        if geri != asil:
            print("HATA: '%s' basamagi KAYIPSIZ DEGIL — bu tavan yayimlanamaz." % ad)
            return 2
        if a0 is None:
            a0 = b
        print("%-46s %8d B | kazanc %7d B (%%%.1f) | geri-donusum ESIT"
              % (ad, b, a0 - b, yuzde(a0 - b, a0)))
        kol_a_tavan = a0 - b
    print("KOL_A_TAVAN (A5 kumulatif, kayipsiz, tablo maliyeti dahil): %d bayt"
          % kol_a_tavan)
    # TEK BAŞINA kazanç: kümülatif merdiven, sonraki basamağın kazancını önceki
    # basamağa BAĞLI gösterir (A4 ile A5 aynı kökten — mükerrer kart — beslenir).
    # FAZ 2 kapsamı en küçük seçilecekse marjinal değil TEK BAŞINA değer gerekir.
    print("TEK BASINA (her donusum yalnizca kendisi):")
    for etiket, sec in (("gorsel ortak onek", {"gorsel_onek"}),
                        ("kategori indeks", {"kategori_indeks"}),
                        ("marka indeks", {"marka_indeks"}),
                        ("metin havuzu", {"metin_havuzu"}),
                        ("tekil kart tablosu", {"tekil_kart"}),
                        ("onek + tekil kart (ikili)", {"gorsel_onek", "tekil_kart"})):
        b = bayt(dump(kart_temsili_uygula(ozet, sec)))
        print("   %-22s %8d B | kazanc %7d B (%%%.1f)"
              % (etiket, b, a0 - b, yuzde(a0 - b, a0)))
    # BÜTÇE HAM bayt üzerinden tanımlı; ama kullanıcıya inen bayt CDN'de sıkıştırılmış.
    # Tekrarları gzip zaten yiyorsa kazanç bütçede görünür, ISTEMCIDE gorunmez — iki
    # ekseni ayrı raporla, birini ötekinin yerine sayma.
    a5 = dump(kart_temsili_uygula(ozet, KOL_A_MERDIVEN[-1][1]))
    z0 = len(zlib.compress(tam_metin.encode("utf-8"), 9))
    z5 = len(zlib.compress(a5.encode("utf-8"), 9))
    print("GZIP EKSENI (bilgi): A0 %d B -> A5 %d B | kazanc %d B (%%%.1f)"
          % (z0, z5, z0 - z5, yuzde(z0 - z5, z0)))
    print()

    # --- 4) kol (b) tavanı
    markalar = ozet["markalar"]
    m_bayt = paylar["markalar"]
    kayit = sum(len(markalar[k]) for k in markalar)
    tekil_marka = marka_cipleri(markalar)
    print("-" * 78)
    print("KOL (b) TAVANI — markalar haritasi")
    print("-" * 78)
    print("bayt: %d (%%%.1f artefakt) | kategori: %d | (kategori,marka) kaydi: %d"
          " | TEKIL marka: %d"
          % (m_bayt, yuzde(m_bayt, toplam), len(markalar), kayit, len(tekil_marka)))
    print("MUTLAK tavan (harita tamamen kaldirilirsa, TUM cipler kaybolur): %d bayt"
          % m_bayt)
    ic, adlar = marka_interning(markalar)
    ic_bayt = bayt(dump("markalar") + ":" + dump(ic) + ","
                   + dump("markaAdlari") + ":" + dump(adlar))
    print("B1 KAYIPSIZ interning (global marka tablosu + indeks anahtar, cip kaybi YOK):"
          " %d B -> kazanc %d B (%%%.1f)%s"
          % (ic_bayt, m_bayt - ic_bayt, yuzde(m_bayt - ic_bayt, m_bayt),
             "  ⛔ NEGATIF: marka adlari kategoriler arasi neredeyse HIC tekrar etmiyor"
             if ic_bayt >= m_bayt else ""))
    glob = marka_global(markalar)
    g_bayt = bayt(dump("markalar") + ":" + dump(glob) + ",")
    print("B1b KISMI KAYIP (kategori kirilimi duser, cip evreni + global sayac kalir):"
          " %d B -> kazanc %d B (%%%.1f) | kaybolan cip 0, kategori-bazli sayac 14 kategoride duser"
          % (g_bayt, m_bayt - g_bayt, yuzde(m_bayt - g_bayt, m_bayt)))
    print("B2 KAYIPLI esikle kirpma (adet < esik olan kayit duser):")
    print("   %6s %10s %10s %10s %12s %12s"
          % ("esik", "bayt", "kazanc", "%kazanc", "dusen kayit", "kaybolan cip"))
    kirpma = {}
    for esik in (2, 3, 5, 10, 25, 50):
        kirpilmis = marka_kirp(markalar, esik)
        b = bayt(dump("markalar") + ":" + dump(kirpilmis) + ",")
        dusen = kayit - sum(len(kirpilmis[k]) for k in kirpilmis)
        cip_kayip = len(tekil_marka - marka_cipleri(kirpilmis))
        kirpma[esik] = (b, m_bayt - b, dusen, cip_kayip)
        print("   %6d %10d %10d %9.1f%% %12d %12d"
              % (esik, b, m_bayt - b, yuzde(m_bayt - b, m_bayt), dusen, cip_kayip))
    print()

    # --- birleşik hüküm
    print("-" * 78)
    print("BIRLESIK")
    print("-" * 78)
    # KOL_B_TAVAN = ÜST SINIR tanımıyla haritanın TAMAMI (kırpmanın gidebileceği en uç
    # nokta). Gerçekte seçilebilecek her eşik bunun ALTINDADIR ve ÇİP KAYBI taşır —
    # tabloda ayrı sütun olarak durur, tavanla karıştırılmaz.
    kol_b_tavan = m_bayt
    ab = kol_a_tavan + kirpma[2][1]
    for etiket, kazanc in (("kol a (kayipsiz, A5)", kol_a_tavan),
                           ("kol b esik=2 (1387 cip duser)", kirpma[2][1]),
                           ("kol b MUTLAK tavan (harita silinir)", kol_b_tavan),
                           ("kol a + kol b(esik=2)", ab)):
        kalan = toplam - kazanc
        print("%-38s -> artefakt %7d B | doluluk %%%.1f | pay %%%.1f"
              % (etiket, kalan, yuzde(kalan, build.OZET_BUTCE),
                 100.0 - yuzde(kalan, build.OZET_BUTCE)))

    # RUNWAY yalnız GERÇEKTEN KATALOGLA BÜYÜYEN kalemlerin eğiminden hesaplanır
    # (sabit adetli havuzların bayt oynaması metin gürültüsüdür, eğim değil).
    buyuyen = ("markalar", "parametrik", "kategoriler")
    for i, isim in ((0, "ESKI uc"), (1, "YENI uc")):
        egim = sum(max(0.0, egimler[k][i]) for k in buyuyen)
        if egim <= 0:
            continue
        print("runway (%s, buyuyen kalemler %s, egim %.3f B/urun): bugun +%d urun"
              " | kol a sonrasi +%d urun | kol a+b(esik2) sonrasi +%d urun"
              % (isim, "+".join(buyuyen), egim,
                 int((build.OZET_BUTCE - toplam) / egim),
                 int((build.OZET_BUTCE - (toplam - kol_a_tavan)) / egim),
                 int((build.OZET_BUTCE - (toplam - ab)) / egim)))
    print()
    print("KAPANIS OZET_BAYT=%d EN_BUYUK_KALEM=%s:%d KOL_A_TAVAN=%d KOL_B_TAVAN=%d"
          " KOL_B_ESIK2=%d"
          % (toplam, max(paylar, key=paylar.get), max(paylar.values()),
             kol_a_tavan, kol_b_tavan, kirpma[2][1]))

    if "--json" in sys.argv:
        yol = sys.argv[sys.argv.index("--json") + 1]
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({"toplam": toplam, "paylar": paylar, "cerceve": cerceve,
                       "fark": fark, "egimler": egimler,
                       "kol_a_tavan": kol_a_tavan, "kol_b_interning": m_bayt - ic_bayt,
                       "kol_b_global": m_bayt - g_bayt,
                       "markalar_bayt": m_bayt, "kirpma": kirpma,
                       "kart_ornegi": len(kartlar), "tekil_kart": len(tekil),
                       "n": n_tam}, f, ensure_ascii=False, indent=1)

    return 0 if fark == 0 else 2


if __name__ == "__main__":
    sys.exit(main())

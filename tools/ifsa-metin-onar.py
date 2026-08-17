#!/usr/bin/env python3
r"""ifsa-metin-onar.py — katalog metnindeki URETIM-SURECI IFSASINI deterministik onarir.

Okan onayi 17 Agu 2026 (kalip tablosu tek ekranda sunuldu, "onayla, uygula").

🔴 NE YAPMAZ — TEK TEK OKU:
  * URUN SILMEZ. Bu arac `duzelt.py --sil` YOLUNU HIC CAGIRMAZ; sadece `alan`+`deger`
    islemi uretir. Okan emri birebir: "sitede bulunan tum urunler satilabilir. SAKIN
    siteden bir urun SILME." denetim-kapisi.py'nin recete ettigi `--uygula --evet-sil N`
    caresi BU SINIFTA doktrin ihlalidir ([[okan-hukmu-urun-silinmez-koken-intern]]).
  * `fiyat` / `lisans` / `uyelik` / `tasarimci` / `gorseller` alanlarina DOKUNMAZ
    (YAZILABILIR_ALANLAR ile kilitli).
  * urunler.json'a DOGRUDAN YAZMAZ. Kanonik yol `tools/duzelt.py --toplu` (flock +
    guard izin manifesti + aciklama_koru olcu satiri korumasi).
  * AI KULLANMAZ. Butun donusum tablo + regex; ayni girdi her koşumda ayni cikti.

YONTEM — iki kolon:
  1. FIIL EKSENI (K-FIIL): `basıl-` koku URETIM anlaminda ise `üretil-`e cevrilir.
     Anlam ve cumle uzunlugu KORUNUR ("Sert malzemeden basılır." -> "Sert malzemeden
     üretilir."). Ev yazimi zaten budur (canli katalogda "Orijinal geometriye sadık
     üretilir." kayitli).
  2. ISIM EKSENI (K-BASKI): `baskı` isminin SUREC cekimleri/tamlamalari tek tek
     eslenir ("baskı sonrası" -> "üretim sonrası", "dekoratif baskı modeli" ->
     "dekoratif model").

🔴 KORUMA (`koru`) — HER kalip kendi yanlis-pozitif suzgecini TASIR ve suzgec
   CUMLE kapsamlidir (pencere/karakter mesafesi DEGIL; denetim-kapisi._cumle ile ayni
   gerekce). Turkce cok-anlamlilik OLCULDU (17 Agu, canli katalog 29.035 kayit):
     * `basıl-` = PRINT ama ayni zamanda BASMA: "düğmeye kazara basılmasını önler",
       "yanlışlıkla basılan anahtar tuşları", "Ayakla basılan", "geniş başlığı parmakla
       rahat basılır", "fitil yerine basılır" (olculdu: 10 canli kayit press).
     * `baskı` = PRINT ama ayni zamanda BASINÇ: "baskıyla oturur", "hafif baskı ile
       takılır", "yay baskısı", "baskı balatası", "baskı takozu" (olculdu: 57+ satir).
   Suzgec eslesirse kalip O CUMLEDE UYGULANMAZ ve kayit ELLE kovasina dusmez —
   dokunulmamis mesru metindir.

🔴 SESSIZ ATLAMA YOK: kalip tablosunun KAPSAMADIGI ama hala `basıl-`/`baskı` tasiyan
   kayitlar `ELLE` kovasinda ID'siyle raporlanir. "Temizlendi" hukmu yalniz DEGISEN +
   ELLE sayilariyla BIRLIKTE anlamlidir ([[kapi-varlik-olcer-yokluk-olcmez]]).

Kullanim:
  python3 tools/ifsa-metin-onar.py                      # report-only, TUM katalog
  python3 tools/ifsa-metin-onar.py --dilim 100          # ilk 100 kaydin islem json'u
  python3 tools/ifsa-metin-onar.py --dilim 100 --uygula # uret + duzelt.py --toplu kostur
  python3 tools/ifsa-metin-onar.py --kendini-test       # kabul + mutasyon bataryasi

Kabul testi + mutasyon: tools/ifsa-kip-test.py (deploy.yml serit-a3'te BLOKLAYICI).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
DUZELT = os.path.join(ROOT, "tools", "duzelt.py")

# Bu arac YALNIZ bu iki metin alanini yazar. Fiyat/lisans/uyelik/tasarimci/gorseller
# BILEREK DISARIDA — gorev yasagi koda baglandi, yorum notuna DEGIL.
YAZILABILIR_ALANLAR = ("baslik", "aciklama")

# --- cumle sinirlari -----------------------------------------------------------------
# 🔴 TEK KAYNAK ZORUNLULUGU: bu desen denetim-kapisi._CUMLE_SON_RE ile BIREBIR AYNI
# olmak zorunda. Ikisi ayrisirsa onarim aracinin "mesru cumle" dedigi seye kapi "ihlal"
# der (ya da tersi) ve ayrisma SESSIZ olur ([[ikiz-tanim-sessiz-ayrisma]]). ifsa-kip-test
# `.pattern` esitligini VAKAYLA iddia eder — yorum notuna guvenilmez.
# Metin json.load'dan gelir: satir sonlari GERCEK "\n" karakteridir (dosyadaki iki
# karakterlik `\n` kacisi DEGIL), yani ayni desen her iki tarafta ayni cumleyi verir.
_CUMLE_SON_RE = re.compile(r"[.!?](?=\s|$)|[\n;]", re.UNICODE)


def _cumle_araligi(metin, i, j):
    """[i,j) eslesmesini iceren cumlenin (bas, son) araligi."""
    bas, son = 0, len(metin)
    for m in _CUMLE_SON_RE.finditer(metin):
        if m.end() <= i:
            bas = m.end()
        elif m.start() >= j:
            son = m.start()
            break
    return bas, son


# =============================================================================
# KALIP TABLOSU (Okan onayli, 17 Agu 2026)
# Her giris: (ad, desen, karsilik, koru)
#   desen/karsilik  : re.sub semantigi (gruplar \1.. ile tasinir)
#   koru            : O CUMLEDE eslesirse kalip UYGULANMAZ (yanlis-pozitif suzgeci)
# =============================================================================

# press-anlami suzgeci — basilan NESNE ya da basan UZUV cumlede geciyorsa BASMA'dir.
# Kelime siniri ZORUNLU: sinirsiz `tu[şs]` "kuTUSu"/"tuTUŞ" icinde eslesir ve gercek
# ihlali susturur (denetim-kapisi.py'de olculmus fail-open; ayni tuzak burada da var).
_PRESS_KORU = (r"\bd[üu][ğg]me\w*|\btu[şs]\w*|\bbuton\w*|\bkorna\w*|\bpedal\w*"
               r"|\bfitil\w*|ayak\s*day|\bparmakla\b|\bayakla\b|\bmandal\w*"
               r"|[üu]zerine\s+bas|\banahtar\s+tu")

# basinc-anlami suzgeci — `baskı` bir KUVVET/PARCA adiysa dokunma.
_BASINC_KORU = (r"bask[ıi]\s*(?:balata|plaka|pim|c[ıi]vata|bur[çc]|disk|nokta|apar"
                r"|merkez|takoz|klips|y[üu]zey|kuvvet|yay[ıi]|g[öo]rd|alma|kolu)"
                r"|bask[ıi]y[la]a?\s*(?:otur|tutun|ge[çc]|tak[ıi]l|s[ıi]k[ıi][şs]"
                r"|yerle|klipsle|sabit|e[ğg])"
                r"|bask[ıi]l[ıi]\s*(?:olarak|devre)|su\s*bask[ıi]n|debriyaj"
                r"|bask[ıi]\s*ge[çc]me|bask[ıi]s[ıi]n[ıa]\s*(?:kar[şs][ıi]|ak[üu])"
                r"|bask[ıi]y[ıi]\s*azalt|bask[ıi]s[ıi](?:yla|nda)\s*(?:yerinde|tutan)")

# --- KOLON 1: FIIL EKSENI ----------------------------------------------------------
# `basıl-` -> `üretil-`, YUZEY BICIMI YUZEY BICIMINE.
#
# 🔴 NEDEN GRUP TASIMA (`bas[ıi]l(...)` -> `üretil\1`) YANLIS — TURKCE UNLU UYUMU:
#   `basıl` KALIN sirali koktur, eki KALIN gelir: bas-ıl-**ır**.
#   `üretil` INCE sirali koktur, eki INCE gelir: üre-til-**ir**.
#   Eki oldugu gibi tasiyan bir donusum "üretilır" uretir — Turkce OLMAYAN bir kelime,
#   ve 216 canli aciklamaya yazilirdi. Bu yuzden kip listesi ACIK ve TAM yazilir.
#
# 🔴 SIRA UZUNDAN KISAYA: "basılmasını" once "basılması"na eslesirse geriye "nı" kalir
#   ve "üretilmesinı" cikar (yine unlu uyumu kirilir). Uzun bicimler ONCE gelir.
#
# 🔴 LISTEDE OLMAYAN BICIM SESSIZCE BOZULMAZ: bilinmeyen bir kip (or. "basıldıysa")
#   hicbir kalibi eslemez -> metin DEGISMEZ ve kayit ELLE kovasinda ID'siyle raporlanir.
#   Yani kapsam disi kip "yanlis onarilmis" degil "onarilmamis" olur (fail-closed).
_FIIL_ESLEME = (
    ("basılmasında", "üretilmesinde"),
    ("basılmasını",  "üretilmesini"),
    ("basılmasına",  "üretilmesine"),
    ("basıldığında", "üretildiğinde"),
    ("basıldıktan",  "üretildikten"),
    ("basılabilir",  "üretilebilir"),
    ("basılabilen",  "üretilebilen"),
    ("basılacaktır", "üretilecektir"),
    ("basılırken",   "üretilirken"),
    ("basılması",    "üretilmesi"),
    ("basılmadan",   "üretilmeden"),
    ("basılmalıdır", "üretilmelidir"),
    ("basılmalı",    "üretilmeli"),
    ("basılmaya",    "üretilmeye"),
    ("basılmıştır",  "üretilmiştir"),
    ("basılmış",     "üretilmiş"),
    ("basılacak",    "üretilecek"),
    ("basılınca",    "üretilince"),
    ("basılırsa",    "üretilirse"),
    ("basılır",      "üretilir"),
    ("basılıp",      "üretilip"),
    ("basılan",      "üretilen"),
    ("basımı",       "üretimi"),
    ("basım",        "üretim"),
)
_K_FIIL = tuple(("fiil/" + kaynak, r"\b" + kaynak + r"\b", hedef, _PRESS_KORU)
                for kaynak, hedef in _FIIL_ESLEME)

# --- KOLON 2: ISIM EKSENI (`baskı`) ------------------------------------------------
# Her giris CANLI katalogda GORULMUS bir es-dizimdir; spekulatif giris YOK.
# ⚠️ IYELIK EKI KORUNUR: "Vespa'nın dekoratif baskı modeli" -> "... dekoratif modelI"
#   (yalin "model" DEGIL) — tamlama bozulmasin.
_K_BASKI = (
    ("baski-dekoratif-model", r"dekoratif\s+bask[ıi]\s+modeli", "dekoratif modeli", _BASINC_KORU),
    ("baski-model",           r"\bbask[ıi]\s+modeli",           "modeli",          _BASINC_KORU),
    ("baski-muhafaza",        r"\bbask[ıi]\s+muhafaza",         "muhafaza",        _BASINC_KORU),
    ("baski-kutu",            r"\bbask[ıi]\s+kutu",             "kutu",            _BASINC_KORU),
    ("baski-uretil",          r"bask[ıi]da\s+[üu]retil",        "özel üretil",     _BASINC_KORU),
    ("baski-ile-uretilen",    r"bask[ıi]yla\s+[üu]retilen",     "özel üretilen",   _BASINC_KORU),
    ("baski-sonrasi",         r"\bbask[ıi]\s+sonras",           "üretim sonras",   _BASINC_KORU),
    ("baski-oncesi",          r"\bbask[ıi]\s+[öo]ncesi",        "üretim öncesi",   _BASINC_KORU),
    ("baski-da-olcu",         r"bask[ıi]da\s+([öo]l[çc][üu]|[öo]l[çc]ek|marka)",
     r"üretimde \1", _BASINC_KORU),
    ("baski-da-test",         r"bask[ıi]da\s+test\s+edil",      "üretimde test edil", _BASINC_KORU),
    ("baski-test",            r"test\s+bask[ıi]s[ıi]yla",       "deneme üretimiyle",  _BASINC_KORU),
    ("baski-test-2",          r"test\s+bask[ıi]s[ıi]nda",       "deneme üretiminde",  _BASINC_KORU),
    ("baski-icin",            r"\bbask[ıi]\s+i[çc]in\s+(optimize|tasarlan)",
     r"üretim için \1", _BASINC_KORU),
)

KALIPLAR = _K_FIIL + _K_BASKI

# 🔴 IGNORECASE ZORUNLU + BUYUK HARF GERI YAZILIR: kapi metni tr_lower'layip bakar, bu
# arac ise CANLI metni AYNEN yazar. Kucuk-harf duyarli desen cumle BASINDAKI "Baskı
# sonrası"/"Basılır" bicimlerini KACIRIR — kapi ihlal der, arac onaramaz, ikisi ayrisir.
# Eslesme buyuk harfle basliyorsa karsilik da buyuk harfle yazilir (bkz. _buyuk_uyarla).
_DERLI = tuple((ad, re.compile(d, re.UNICODE | re.IGNORECASE), k,
                re.compile(g, re.UNICODE | re.IGNORECASE))
               for ad, d, k, g in KALIPLAR)


def _buyuk_uyarla(eslesen, karsilik):
    """Eslesme buyuk harfle basliyorsa karsiligi da buyuk harfle basla.

    ⚠️ TURKCE NOKTALI I TUZAGI: 'i' -> buyuk hali 'İ'dir, 'I' DEGIL. Bugunku karsilik
    tablosunda 'i' ile baslayan giris YOK (hepsi ü/ö/m/k/d/[üo]zel), ama tabloya
    eklenirse bu satir onu dogru cevirsin diye ayrik ele alinir."""
    if not eslesen[:1].isupper() or not karsilik[:1].islower():
        return karsilik
    bas = "İ" if karsilik[0] == "i" else karsilik[0].upper()
    return bas + karsilik[1:]


def _kalip_uygula(metin, rx, karsilik, koru):
    """Tek kalibi metne uygular. (yeni_metin, vurus_sayisi).

    TEK GECIS, SOLDAN SAGA: eslesmeler ORIJINAL metin uzerinde bulunur, karar
    (koru) o eslesmenin CUMLESINE bakilarak verilir, cikti parca parca kurulur.
    Boylece (a) korunan cumle atlanirken sonsuz donguye girilmez, (b) karsiligin
    kendisi yeniden eslesse bile ikinci kez islenmez (ornegin `üretil` -> `üretil`
    gibi bir kalip eklenirse durus garantili)."""
    parcalar, son_index, vurus = [], 0, 0
    for m in rx.finditer(metin):
        if m.start() < son_index:
            continue                                  # onceki eslesmeyle ortusuyor
        bas, son = _cumle_araligi(metin, m.start(), m.end())
        if koru.search(metin[bas:son]):
            continue                                  # MESRU cumle (press/basinc) — dokunma
        parcalar.append(metin[son_index:m.start()])
        parcalar.append(_buyuk_uyarla(m.group(0), m.expand(karsilik)))
        son_index = m.end()
        vurus += 1
    if not vurus:
        return metin, 0
    parcalar.append(metin[son_index:])
    return "".join(parcalar), vurus


def onar_metin(metin):
    """(yeni_metin, [uygulanan_kalip_adi, ...]) — saf fonksiyon, dosya/ag YOK."""
    if not isinstance(metin, str) or not metin:
        return metin, []
    uygulanan = []
    for ad, rx, karsilik, koru in _DERLI:
        metin, vurus = _kalip_uygula(metin, rx, karsilik, koru)
        uygulanan.extend([ad] * vurus)
    return metin, uygulanan


def urun_onar(urun):
    """(islemler, uygulanan_kalipler, onarilmis_urun) — urunler.json'a YAZMAZ."""
    islemler, kalipler = [], []
    onarilmis = dict(urun)
    for alan in YAZILABILIR_ALANLAR:
        eski = urun.get(alan)
        if not isinstance(eski, str) or not eski:
            continue
        yeni, uyg = onar_metin(eski)
        if uyg and yeni != eski:
            islemler.append({"id": urun.get("id"), "alan": alan, "deger": yeni})
            onarilmis[alan] = yeni
            kalipler.extend(uyg)
    return islemler, kalipler, onarilmis


# =============================================================================
# I/O + CLI
# =============================================================================
def _oku_urunler():
    with open(URUNLER, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        raise ValueError("urunler.json bir dizi degil")
    return d


def _kapi_sert():
    """denetim-kapisi.kapi_ifsa — TEK KAYNAK. 'Ihlal nedir?' sorusuna bu arac KENDI
    yanitini uretMEZ; kapiya sorar. Boylece ELLE kovasi ("kalip kapsamadi") kapinin
    hukmuyle AYNI eksende olculur ([[ikiz-tanim-sessiz-ayrisma]])."""
    import importlib.util
    yol = os.path.join(ROOT, "tools", "denetim-kapisi.py")
    s = importlib.util.spec_from_file_location("dk_onar", yol)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m.kapi_ifsa


# Bu aracin ONARDIGI ihlal sinifi. Bunun DISINDAKI her kural "yan ihlal"dir: ayri bir
# is, ayri bir karar. denetim-kapisi'ndaki kural adlariyla BIREBIR ayni olmak zorunda —
# ifsa-kip-test bunu vakayla dogrular.
KIP_KURALLARI = frozenset(("baski-fiili", "uretim-kipi-basil", "baski-surec-cekimi"))


def _yan_ihlal_imzasi(sert_fn, urun):
    """Kaydin KIP DISI SERT ihlallerinin (kural, cumle) imzasi.

    🔴 NEDEN VAR — KARMA CUMLE SINIFI (17 Agu 2026, CI kolunda OLCULDU):
    `denetim-kapisi.py --commit-farki` bir ihlali "onceden vardi" saymak icin
    (kapi, gerekce) ikilisini karsilastirir ve `gerekce` metni O IHLALIN CUMLESINI
    icerir. Ayni cumlede hem bizim onardigimiz kip ihlali hem BASKA bir ihlal varsa
    (olculen vaka: `cup-holder-100mm-dacia-logan-2009` — "baskı sonrası tolerans ayarı
    icin STL editoru ile ..." cumlesi hem `baski-surec-cekimi` hem `dosya-ifsasi`
    tasiyor), yarim onarim o cumleyi degistirir, `dosya-ifsasi`nin gerekce metni de
    degisir ve kapi ONCEDEN VAR OLAN ihlali "bu itmenin GETIRDIGI" sanip TUM EKIBIN
    yayinini durdurur. Olculdu: tek kayit yuzunden `--commit-farki` rc=1.

    KARAR: yarim onarma. Boyle bir kayda HIC DOKUNULMAZ ve ELLE kovasinda
    `karma-cumle` gerekcesiyle gorunur. Bu TEKIL YAMA DEGIL SINIF kapatmasidir —
    gelecekteki her karma cumle ayni yoldan atlanir ([[tekil-yama-sinifi-kapatmaz]]).
    """
    return frozenset((s["kural"], s["cumle"]) for s in sert_fn(urun)["sert"]
                     if s["kural"] not in KIP_KURALLARI)


def _tara(urunler, dilim=None):
    """(islemler, kalip_sayaci, elle, dokunulan) — dilim: en fazla kac KAYIT islensin.

    ELLE = ONARIMDAN SONRA kapinin HALA SERT dedigi kayit. Yani "hala 'baskı' kelimesi
    geciyor" DEGIL — press/basinc okumasi tasiyan MESRU metin ELLE'ye DUSMEZ. Kalibin
    kapsamadigi gercek ihlal ID'siyle ve KURAL adiyla gorunur; sessizce atlanmaz."""
    sert_fn = _kapi_sert()
    islemler, elle = [], []
    sayac = {}
    dokunulan = 0
    karma = 0
    for u in urunler:
        if not isinstance(u, dict):
            continue
        u_islem, kalipler, onarilmis = urun_onar(u)
        if u_islem and _yan_ihlal_imzasi(sert_fn, u) != _yan_ihlal_imzasi(sert_fn, onarilmis):
            # KARMA CUMLE: onarim baska bir ihlalin cumlesini de degistiriyor -> DOKUNMA.
            u_islem, kalipler, onarilmis = [], [], u
            karma += 1
        kalan = sert_fn(onarilmis)["sert"]
        if kalan:
            elle.append((u.get("id"), sorted({s["kural"] for s in kalan})))
        if not u_islem:
            continue
        if dilim is not None and dokunulan >= dilim:
            continue
        islemler.extend(u_islem)
        dokunulan += 1
        for k in kalipler:
            sayac[k] = sayac.get(k, 0) + 1
    return islemler, sayac, elle, dokunulan, karma


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dilim", type=int, default=None, metavar="N",
                    help="en fazla N KAYIT isle (dilimli calisma; olcum her dilimden sonra)")
    ap.add_argument("--uygula", action="store_true",
                    help="islem json'unu uret VE `duzelt.py --toplu` ile UYGULA "
                         "(varsayilan: report-only). URUN SILMEZ.")
    ap.add_argument("--islem-json", default=None, metavar="YOL",
                    help="uretilen islem json'unu bu yola yaz (varsayilan: gecici dosya, "
                         "kullanildiktan sonra SILINIR — Okan disk kurali)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="kabul + mutasyon bataryasi (repo dosyasi DEGISMEZ)")
    args = ap.parse_args()

    if args.kendini_test:
        import importlib.util
        yol = os.path.join(ROOT, "tools", "ifsa-kip-test.py")
        s = importlib.util.spec_from_file_location("ifsa_kip_test", yol)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        return m.kos()

    urunler = _oku_urunler()
    islemler, sayac, elle, dokunulan, karma = _tara(urunler, args.dilim)

    print("=== IFSA METIN ONARIM === katalog: %d kayit" % len(urunler))
    print("  dokunulacak kayit : %d%s"
          % (dokunulan, (" (dilim=%d)" % args.dilim) if args.dilim else " (TUM katalog)"))
    print("  islem sayisi      : %d" % len(islemler))
    print("  ELLE (kapi hala SERT): %d  (kalip KAPSAMADI — sessizce atlanmadi, listelendi)"
          % len(elle))
    print("  KARMA CUMLE atlandi : %d  (ayni cumlede BASKA ihlal var — yarim onarim CI'yi "
          "bloklardi; bilerek DOKUNULMADI)" % karma)
    print("  SILINEN_URUN      : 0  (bu arac silme yolunu HIC cagirmaz)")
    if sayac:
        print("  --- kalip dokumu ---")
        for k in sorted(sayac, key=lambda x: (-sayac[x], x)):
            print("  %-24s | %d" % (k, sayac[k]))
    if elle:
        elle_kural = {}
        for _uid, kurallar in elle:
            for k in kurallar:
                elle_kural[k] = elle_kural.get(k, 0) + 1
        print("  --- ELLE kural dokumu ---")
        for k in sorted(elle_kural, key=lambda x: (-elle_kural[x], x)):
            print("  %-24s | %d" % (k, elle_kural[k]))
        print("  --- ELLE ornek (ilk 15 id) ---")
        for uid, kurallar in elle[:15]:
            print("  %-48s %s" % (uid, ",".join(kurallar)))

    if not args.uygula:
        print("(report-only — uygulamak icin --uygula)")
        return 0
    if not islemler:
        print("uygulanacak islem yok.")
        return 0

    yol = args.islem_json
    gecici = yol is None
    if gecici:
        fd, yol = tempfile.mkstemp(prefix=".ifsa-onar-", suffix=".json", dir=ROOT)
        os.close(fd)
    try:
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(islemler, f, ensure_ascii=False, indent=2)
        p = subprocess.run([sys.executable, DUZELT, "--toplu", yol], cwd=ROOT)
        rc = p.returncode
    finally:
        # Okan disk kurali: ureten temizler. Kalici yol ISTENDIYSE birakilir.
        if gecici:
            try:
                os.unlink(yol)
            except OSError:
                pass
    print("duzelt.py --toplu rc=%d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())

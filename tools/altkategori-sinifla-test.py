#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — alt kategori KUMESI + UC GECISLI siniflandirici SESSIZ hata uretemez.

  python3 tools/altkategori-sinifla-test.py              # kabul (CI'da bloklayici)
  python3 tools/altkategori-sinifla-test.py --mutasyon   # cift yonlu mutasyon (elle)
  python3 tools/altkategori-sinifla-test.py --kok /yol   # modulleri BASKA agactan oku

NEDEN VAR (olculdu, 2 Agu): `altkategori` yalnizca Marin'de tanimliydi (12 deger, 935
kayit) ve katalogun %94'unde alan BOSTU. Kume 6 kategoriye genisletildi (60 deger) ve
urunun hangi gruba dustugunu hesaplayan deterministik bir siniflandirici yazildi. Bu
yolun HER kusuru SESSIZDIR: yanlis kanonik deger katalog ile D1 arasinda metin ayrismasi
uretir (bu depoda olculdu), esik kaymasi 12 bin urunu tek kovaya doker, sozluk elle
yazilirsa "veriden turedi" iddiasi YALAN olur ve kimse fark etmez.

OLCULEN SESSIZ-HATA SINIFLARI:
  K KUME    Deger imza tasirsa tedarikci kimligi public repoya + D1'e sizar; MIRAS bir
            deger bir harf degisirse 935 kayit SESSIZCE gecersizlesir (kanonik "" olur,
            alt-filtre bos doner, hicbir sey COKMEZ).
  E ESIK    Kategori/grup esikleri kagitta kalirsa gurultu grubu kumeye girer; esik
            fiilen olculmezse "esik var" iddiasi tautolojidir.
  S SIRA    Artik kova oncelikte one kayarsa TUM kategori tek kovaya duser — yigilma
            cozulmus gorunur, TASINMIS olur.
  T TURETME 2. gecis sozlugu elle yazilirsa "yakinlik verinin olcusu" iddiasi coker;
            cikti yine makul gorunur, dayanagi kalmaz.
  D DETERM. Girdi sirasina duyarli siniflandirma iki kosumda farkli katalog uretir;
            diff-upsert her push'ta satirlari yeniden yazar, kimse sebebini bulamaz.
  F FAIL-   Siniflandirici kume DISI deger uretirse duzelt.py onu reddeder ama rapor
    CLOSED  "atandi" der: olculen sayi ile yazilabilir sayi sessizce ayrisir.

urunler.json yalnizca OKUNUR; hicbir iddia ona YAZMAZ (siniflandirici zaten yazmaz).
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

GERCEK_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

gecen = [0]
kalan = [0]


def dogrula(ad, kosul, detay=""):
    if kosul:
        gecen[0] += 1
        print("  GECTI " + ad)
    else:
        kalan[0] += 1
        print("  KALDI " + ad + (" — " + str(detay)[:400] if detay else ""))


def yukle(kok, ad, dosya):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(kok, "tools", dosya))
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


# 🔴 MARIN MIRASI — BAYT CAPASI. Bu 12 dize 935 kayitta KULLANILIYOR (olculdu). Liste
# BURADA arama.py'den TURETILMEZ, ELLE YAZILIR: turetilseydi iddia tautoloji olurdu
# ("kume kendine esit"). Bir harf degisirse T2 KIRMIZI yanar.
MIRAS_12 = (
    "Boya - Bakım", "Bujiler", "Dümen ve Kumanda", "Elektrik", "Filtreler",
    "Motor Parçaları", "Motor Yağları", "Pervaneler", "Sintine ve Ekipmanları",
    "Soğutma", "Tutyalar ve Anotlar", "Yakıt Sistemi",
)
# Kategori esigini gecemeyen kategoriler (K4 karari) — kume TANIMLI OLMAMALI.
ESIK_ALTI_KATEGORI = ("Ofis", "Bisiklet", "Bahçe", "Tamirat", "Jeneratör", "Kamera",
                      "Skan Art", "Oyun/Hobi")


def _urun(uid, kategori, baslik, aciklama=""):
    return {"id": uid, "kategori": kategori, "baslik": baslik, "aciklama": aciklama,
            "marka": [], "fiyat": "100 TL",
            "gorseller": ["https://media.pruvo3d.com/urunler/x-1.jpg"]}


def _fikstur_tablo(S, mutfak, banyo):
    """2. GECIS fiksturu: GERCEK `Ev` grup adlari, KONTROLLU terimler.

    Iki varyant ayni grup ADLARINI kullanir, terimleri YER DEGISTIRIR -> 1. gecis
    ciktisi degisir. Sozluk TURETILIYORSA 2. gecis atamasi da degismek ZORUNDADIR.
    """
    return {"Ev": (
        ("Mutfak", S.BELIRGIN, mutfak, ""),
        ("Banyo", S.BELIRGIN, banyo, ""),
        ("Saklama ve Düzen", S.ARTIK, ("boylebirseyyok",), "artik kova"),
    )}


_FIKSTUR_URUNLER = [
    _urun("f1", "Ev", "kasik kutu sari"), _urun("f2", "Ev", "kasik kutu mavi"),
    _urun("f3", "Ev", "kasik kutu yesil"),
    _urun("f4", "Ev", "sabun raf sari"), _urun("f5", "Ev", "sabun raf mavi"),
    _urun("f6", "Ev", "sabun raf yesil"),
    _urun("f7", "Ev", "kutu"),           # 1. geciste eslesmez -> 2. gecise kalir
]


def kabul(kok):
    arama = yukle(kok, "aramamod", "arama.py")
    S = yukle(kok, "siniflamod", "altkategori-sinifla.py")
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        katalog = json.load(f)

    # ══ T1 — KUMENIN TUMU IMZA NOBETINDEN GECIYOR (her ad AYRI iddia) ═══════════════
    print("\n[T1] IMZA — her kume degeri tek tek nobetten geciyor (depo PUBLIC)")
    for kategori in sorted(arama.ALTKATEGORI_IZINLI):
        for deger in arama.ALTKATEGORI_IZINLI[kategori]:
            sebep = arama.altkategori_imza_sebebi(deger)
            dogrula("T1 %s / %r imza nobetinden geciyor" % (kategori, deger),
                    sebep is None, sebep)

    # ══ T2 — MARIN MIRASI BAYT-ESIT + 935 KAYIT GECERLI ════════════════════════════
    print("\n[T2] MIRAS — Marin'in 12 degeri BAYT olarak korunmus")
    marin = arama.ALTKATEGORI_IZINLI.get("Marin", ())
    eksik = [d for d in MIRAS_12 if d not in marin]
    dogrula("T2a MIRAS 12 degerin HEPSI kumede ve BAYT-ESIT (ad degisirse 935 kayit "
            "sessizce gecersizlesir)", not eksik, eksik)
    bayt = [d for d in MIRAS_12 if d.encode("utf-8") not in
            [x.encode("utf-8") for x in marin]]
    dogrula("T2b UTF-8 BAYT dizisi ayni (gorsel olarak ayni ama farkli kodlanmis dize "
            "kabul edilmiyor)", not bayt, bayt)
    dolu = [u for u in katalog if isinstance(u, dict)
            and isinstance(u.get("altkategori"), str) and u["altkategori"].strip()]
    gecersiz = [(u.get("id"), u.get("kategori"), u.get("altkategori"))
                for u in dolu
                if arama.altkategori_sebebi(u.get("kategori"),
                                            u.get("altkategori")) is not None]
    dogrula("T2c GERCEK KATALOG: altkategorisi dolu %d kaydin HICBIRI genisleyen kumeyle "
            "gecersizlesmiyor" % len(dolu), not gecersiz, gecersiz[:5])
    kanonik_ayrisan = [(u.get("id"), u.get("altkategori"), arama.altkategori_kanonik(u))
                       for u in dolu
                       if arama.altkategori_kanonik(u) != u.get("altkategori")]
    dogrula("T2d GERCEK KATALOG: dolu kayitlarin D1 metni katalog metniyle AYNI kaliyor",
            not kanonik_ayrisan, kanonik_ayrisan[:5])

    # ══ T3 — NORMALIZE CAKISMASI YOK ═══════════════════════════════════════════════
    print("\n[T3] CAKISMA — yeni degerler mevcutlarla normalize sonrasi carpismiyor")
    katlama = {}
    carpisan = []
    for kategori, degerler in sorted(arama.ALTKATEGORI_IZINLI.items()):
        icKatlama = {}
        for d in degerler:
            a = arama.model_normalize(d)
            if a in icKatlama and icKatlama[a] != d:
                carpisan.append((kategori, d, icKatlama[a]))
            icKatlama[a] = d
        for d in degerler:
            a = arama.model_normalize(d)
            # FARKLI bayt, AYNI anahtar -> sessiz ikiz (kategori sinirini asarak da olur)
            if a in katlama and katlama[a] != d:
                carpisan.append((kategori, d, katlama[a]))
            katlama[a] = d
    dogrula("T3a hicbir iki FARKLI deger ayni normalize anahtara katlanmiyor (ikiz yazim "
            "kategori icinde de, kategoriler arasinda da yok)", not carpisan, carpisan)
    dogrula("T3b katlama FIILEN olcuyor (kontrol: 'Pervaneler' ile 'pervane ler' ayni "
            "anahtara duser)",
            arama.model_normalize("Pervaneler") == arama.model_normalize("pervane ler"))

    # ══ T4 — ESIKLER (gercek katalogda OLCULUYOR) ══════════════════════════════════
    print("\n[T4] ESIK — kategori >=%d urun · grup >=%d urun"
          % (S.ESIK_KATEGORI_URUN, S.ESIK_GRUP_URUN))
    kat_sayi = S.kategori_dagilimi(katalog)
    tanimsiz = [k for k in ESIK_ALTI_KATEGORI if k in arama.ALTKATEGORI_IZINLI]
    dogrula("T4a <%d urunlu %d kategoriye kume TANIMLI DEGIL (%s)"
            % (S.ESIK_KATEGORI_URUN, len(ESIK_ALTI_KATEGORI),
               ", ".join("%s %d" % (k, kat_sayi.get(k, 0)) for k in ESIK_ALTI_KATEGORI)),
            not tanimsiz, tanimsiz)
    kucuk = [(k, kat_sayi.get(k, 0)) for k in arama.ALTKATEGORI_IZINLI
             if kat_sayi.get(k, 0) < S.ESIK_KATEGORI_URUN]
    dogrula("T4b kume TANIMLI her kategori >=%d urun tasiyor" % S.ESIK_KATEGORI_URUN,
            not kucuk, kucuk)
    # Grup esigi 1. GECIS sayimi uzerinden olculur (2./3. gecis grubu SISIRIR; esik
    # grubun ACILMASINI belirler, sonradan tasinan urunu degil).
    birinci = {}
    for kategori in S.ADAYLAR:
        urunler = [u for u in katalog if isinstance(u, dict)
                   and u.get("kategori") == kategori]
        metinler = [S.urun_metni(u) for u in urunler]
        kova = set(S.artik_kovalar(kategori))
        sayim = {}
        serbest = []          # daha belirgin bir grubun ZATEN almadigi urunler
        for m in metinler:
            ad = S.grup_bul(m, kategori)
            if ad:
                sayim[ad] = sayim.get(ad, 0) + 1
            if (not ad) or ad in kova:
                serbest.append(m)
        birinci[kategori] = (sayim, serbest)
    zayif = []
    for kategori, (sayim, _m) in birinci.items():
        for ad, sinif, _t, _g in S.ADAYLAR[kategori]:
            if sinif in (S.BELIRGIN, S.ARTIK) and sayim.get(ad, 0) < S.ESIK_GRUP_URUN:
                zayif.append((kategori, ad, sayim.get(ad, 0)))
    dogrula("T4c kumedeki her YENI grup >=%d urun tasiyor (MIRAS haric — K3 ile "
            "korunuyor)" % S.ESIK_GRUP_URUN, not zayif, zayif)
    # ELENEN adayin OLCUSU: kac urunu daha belirgin bir grup ZATEN almiyor. Ham eslesme
    # yaniltir (ayni urun ust gruba dusmus olabilir); esigin sordugu soru "bu grup
    # ACILSA neyi kurtarirdi"dir. SEKIL_RED sayiyla DEGIL EKSENLE (K1) reddedilir —
    # 'Kapaklar ve Tapalar' 54 urun kurtarirdi ve yine de kumeye GIRMEZ.
    elenen_hata = []
    for kategori, (_s, serbest) in birinci.items():
        for ad, sinif, terimler, gerekce in S.ADAYLAR[kategori]:
            if sinif not in (S.ELENEN, S.SEKIL_RED):
                continue
            if ad in arama.ALTKATEGORI_IZINLI.get(kategori, ()):
                elenen_hata.append((kategori, ad, "ELENEN ama KUMEDE"))
            if not gerekce:
                elenen_hata.append((kategori, ad, "GEREKCESIZ eleme"))
            if sinif == S.ELENEN and terimler:
                n = sum(1 for m in serbest if S._terim_re(terimler).search(m))
                if n >= S.ESIK_GRUP_URUN:
                    elenen_hata.append((kategori, ad, "esik ALTI degil: %d" % n))
    dogrula("T4d ELENEN/SEKIL_RED adaylarin HICBIRI kumede degil, hepsi GEREKCELI ve "
            "ELENEN olanlarin katkisi fiilen <%d urun" % S.ESIK_GRUP_URUN,
            not elenen_hata, elenen_hata)
    dogrula("T4e SEKIL_RED adaylar SAYIYLA DEGIL EKSENLE reddedildi (K1): en az biri "
            "esigi ASIYOR ve yine de kumede DEGIL — 'az kalsin' istisnasi yok",
            any(sinif == S.SEKIL_RED and terimler
                and sum(1 for m in birinci[k][1] if S._terim_re(terimler).search(m))
                >= S.ESIK_GRUP_URUN
                for k in S.ADAYLAR for _a, sinif, terimler, _g in S.ADAYLAR[k]))

    # ══ T5/T15 — DETERMINIZM (girdi sirasi + tekrar) ════════════════════════════════
    print("\n[T5] DETERMINIZM — ayni girdi ayni cikti, girdi SIRASI sonucu degistirmiyor")
    ev = [u for u in katalog if isinstance(u, dict) and u.get("kategori") == "Ev"]
    kosum1 = S.siniflandir_toplu(ev, "Ev")
    kosum2 = S.siniflandir_toplu(ev, "Ev")
    dogrula("T5a iki kosum BAYT-ESIT",
            hashlib.sha256(repr(kosum1).encode()).hexdigest()
            == hashlib.sha256(repr(kosum2).encode()).hexdigest())
    ters = list(reversed(ev))
    kosum3 = S.siniflandir_toplu(ters, "Ev")
    esles1 = {u["id"]: v for u, v in zip(ev, kosum1)}
    esles3 = {u["id"]: v for u, v in zip(ters, kosum3)}
    dogrula("T5b TERS sirada ayni id -> ayni (deger, gecis) (girdi sirasina duyarlilik "
            "yok)", esles1 == esles3,
            [(k, esles1[k], esles3[k]) for k in esles1 if esles1[k] != esles3[k]][:5])
    karisik = ev[1::2] + ev[0::2]
    esles4 = {u["id"]: v for u, v in zip(karisik,
                                         S.siniflandir_toplu(karisik, "Ev"))}
    dogrula("T15 KARISIK sirada da ayni sonuc (3. gecis dahil deterministik)",
            esles1 == esles4,
            [(k, esles1[k], esles4[k]) for k in esles1 if esles1[k] != esles4[k]][:5])

    # ══ T6 — FAIL-CLOSED: kume DISI deger URETILEMEZ ═══════════════════════════════
    print("\n[T6] FAIL-CLOSED — siniflandirici kume disi deger uretemez")
    tum_cikti = {}
    dagitim = {}
    bos_kalan = {}
    for kategori in S.ADAYLAR:
        urunler = [u for u in katalog if isinstance(u, dict)
                   and u.get("kategori") == kategori]
        sonuc = S.siniflandir_toplu(urunler, kategori)
        tum_cikti[kategori] = sonuc
        d = {}
        bos = 0
        for deger, gecis in sonuc:
            if not deger:
                bos += 1
                continue
            d.setdefault(deger, [0, 0, 0, 0])[gecis] += 1
        dagitim[kategori] = d
        bos_kalan[kategori] = bos
    disari = []
    for kategori, sonuc in tum_cikti.items():
        izinli = set(arama.ALTKATEGORI_IZINLI.get(kategori, ()))
        for deger, _g in sonuc:
            if deger and deger not in izinli:
                disari.append((kategori, deger))
    dogrula("T6a GERCEK KATALOG: uretilen her deger izinli kumede ya da \"\" (%d kayit)"
            % sum(len(v) for v in tum_cikti.values()), not disari, sorted(set(disari))[:5])
    dogrula("T6b uretilen her deger duzelt.py kapisindan da GECIYOR (yazilamayan deger "
            "'atandi' diye raporlanamaz)",
            not [(k, d) for k, s in tum_cikti.items() for d, _g in s
                 if d and arama.altkategori_sebebi(k, d) is not None])
    dogrula("T6c kanonik() kume DISI adi \"\" yapiyor (fail-closed yon)",
            S.kanonik("Ev", "Uydurma Grup") == "" and S.kanonik("Ev", "Mutfak") == "Mutfak"
            and S.kanonik("Ev", "Aydınlatma") == "")

    # ══ T7 — ARTIK KOVA GERCEKTEN SON ══════════════════════════════════════════════
    print("\n[T7] SIRA — artik kova oncelikte EN SONDA")
    fikstur = [
        ("Otomobil", "Far Montaj Braketi ve Klipsi", "Aydınlatma"),
        ("Otomobil", "Jant Göbeği Kapağı Klipsi", "Tekerlek ve Jant"),
        ("Otomobil", "Koltuk Montaj Aparatı", "Koltuk ve Kemer"),
        ("Otomobil", "Plastik Klips", "Montaj ve Bağlantı"),
        ("Marin", "Olta Kamışı Tutucusu Montaj Aparatı", "Olta Ekipmanları"),
        ("Marin", "Braket Kelepçesi", "Montaj Ekipmanları"),
        ("Motosiklet", "Far Braketi Montaj Aparatı", "Aydınlatma"),
        ("Ev", "Mutfak Aleti Sepeti Düzenleyici", "Mutfak"),
        ("Elektronik", "Davul Baget Tutucu Braketi", "Ses ve Müzik"),
        ("Dekorasyon", "Saksı Standı ve Tasarım Kutusu", "Bitki ve Saksı"),
    ]
    yanlis = []
    for kategori, baslik, beklenen in fikstur:
        d = S.siniflandir(_urun("t", kategori, baslik))
        if d != beklenen:
            yanlis.append((baslik, beklenen, d))
    dogrula("T7a %d fiksturun HEPSI belirgin gruba gidiyor, artik kovaya DEGIL "
            "(daha belirgin sinyal varken kova kazanamaz)" % len(fikstur),
            not yanlis, yanlis)
    sira_hata = []
    for kategori in S.ADAYLAR:
        adlar = list(S.kume_adlari(kategori))
        kovalar = list(S.artik_kovalar(kategori))
        if kovalar and adlar[-len(kovalar):] != kovalar:
            sira_hata.append((kategori, adlar, kovalar))
    dogrula("T7b HER kategoride artik kova(lar) oncelik sirasinin SONUNDA",
            not sira_hata, sira_hata)
    dogrula("T7c her kume TANIMLI kategoride EN AZ bir artik kova var (bos kalan 0 "
            "ancak boyle garanti edilir)",
            all(S.artik_kovalar(k) for k in S.ADAYLAR),
            [k for k in S.ADAYLAR if not S.artik_kovalar(k)])

    # ══ T8/T11/T12 — GERCEK KATALOG KOSUMU ═════════════════════════════════════════
    print("\n[T8] GERCEK KATALOG — dagilim, bos kalan, gecis kirilimi")
    toplam_atanan = 0
    for kategori in sorted(dagitim):
        n = sum(sum(v[1:]) for v in dagitim[kategori].values())
        toplam_atanan += n
        print("      %-12s grup %2d · atanan %5d · bos %d"
              % (kategori, len(dagitim[kategori]), n, bos_kalan[kategori]))
    dogrula("T8a her kume TANIMLI kategori icin dagilim URETILIYOR (grup basina sayi)",
            all(dagitim[k] for k in S.ADAYLAR), {k: len(v) for k, v in dagitim.items()})
    dogrula("T8b uretilen grup adlari kumenin TAMAMINI kapsiyor ya da altkumesi "
            "(uydurma grup yok)",
            all(set(dagitim[k]) <= set(arama.ALTKATEGORI_IZINLI[k]) for k in dagitim))
    dogrula("T11 BOS KALAN = 0 — alt kategori alan %d kategorinin HICBIRINDE bos urun yok"
            % len(S.ADAYLAR), all(v == 0 for v in bos_kalan.values()), bos_kalan)
    gecis_hata = []
    for kategori, d in dagitim.items():
        for ad, c in d.items():
            if c[0]:
                gecis_hata.append((kategori, ad, "gecis 0 ile atanmis"))
            if sum(c[1:]) == 0:
                gecis_hata.append((kategori, ad, "grup bos"))
    dogrula("T12a her atamanin gecisi 1/2/3'ten biri ve her grup icin kirilim URETILIYOR",
            not gecis_hata, gecis_hata[:5])
    g1 = sum(c[1] for d in dagitim.values() for c in d.values())
    g2 = sum(c[2] for d in dagitim.values() for c in d.values())
    g3 = sum(c[3] for d in dagitim.values() for c in d.values())
    dogrula("T12b gecis kirilimi TOPLAMI atanan urun sayisina esit (1:%d + 2:%d + 3:%d "
            "= %d)" % (g1, g2, g3, toplam_atanan), g1 + g2 + g3 == toplam_atanan)
    dogrula("T12c UC GECIS de FIILEN calisiyor (biri hic ates etmiyorsa kural olu "
            "koddur)", g1 > 0 and g2 > 0 and g3 > 0, (g1, g2, g3))

    # ══ T9 — MEVCUT KAPI GENISLEYEN KUMEYLE HALA YESIL ═════════════════════════════
    print("\n[T9] KAPI — tools/altkategori-kapisi.py genisleyen kumeyle rc=0")
    p = subprocess.run([sys.executable, os.path.join(kok, "tools", "altkategori-kapisi.py"),
                        "--kok", kok], capture_output=True, text=True)
    dogrula("T9a altkategori-kapisi.py rc=0 (60 degerli kume A/B/C/D eksenlerini geciyor)",
            p.returncode == 0, (p.stdout + p.stderr)[-400:])
    dogrula("T9b kapi 935 mevcut kaydi KABUL ediyor (A1/A3 iddialari GECTI)",
            "KALDI A1" not in p.stdout and "KALDI A3" not in p.stdout,
            [s for s in p.stdout.splitlines() if s.strip().startswith("KALDI")][:3])

    # ══ T10 — MARKA/MODEL JETONU SIZAMAZ ═══════════════════════════════════════════
    print("\n[T10] SIZMA — marka/model jetonu grup adi olamaz")
    marka_anahtar = {arama.model_normalize(m) for m in arama.UYUM_MARKA_IZINLI}
    katalog_marka = set()
    for u in katalog:
        if isinstance(u, dict):
            for m in (u.get("marka") or []):
                if isinstance(m, str) and m.strip():
                    katalog_marka.add(arama.nrm(m.strip()))
    sizan = []
    for kategori, degerler in arama.ALTKATEGORI_IZINLI.items():
        for d in degerler:
            if arama.model_normalize(d) in marka_anahtar:
                sizan.append((kategori, d, "KAPALI marka kumesi"))
            for w in d.replace("-", " ").replace("/", " ").split():
                if arama.nrm(w) in katalog_marka or arama.model_normalize(w) in marka_anahtar:
                    sizan.append((kategori, d, w))
    dogrula("T10a hicbir kume degeri/jetonu marka adi DEGIL (kapali kume %d jeton + "
            "katalogun %d tekil markasi)" % (len(marka_anahtar), len(katalog_marka)),
            not sizan, sizan[:5])
    dogrula("T10b marka jetonlari metinden FIILEN siliniyor (turetilmis liste, elle "
            "yazilmis degil)",
            "toyota" not in S.markasiz("Toyota Corolla Kapı Kolu")
            and "kapi" in S.markasiz("Toyota Corolla Kapı Kolu"))
    dogrula("T10c marka jetonu 2. gecis sozluguNE de giremiyor (sozluk markasiz metinden "
            "turer)", not [t for t in S.baslik_jetonlari(
                _urun("x", "Ev", "Yamaha Bosch Mutfak Rafı")) if t in marka_anahtar],
            S.baslik_jetonlari(_urun("x", "Ev", "Yamaha Bosch Mutfak Rafı")))
    dogrula("T10d siniflandirici marka dolu bir baslikta bile YALNIZ kume degeri ya da "
            "\"\" uretiyor",
            S.siniflandir(_urun("x", "Otomobil", "Toyota Yamaha BMW Volvo Peugeot"))
            in ("",) + tuple(arama.ALTKATEGORI_IZINLI["Otomobil"]))

    # ══ T13 — 2. GECIS SOZLUGU TURETILIYOR (elle liste YOK) ═════════════════════════
    print("\n[T13] TURETME — 2. gecis sozlugu 1. gecis ciktisindan turer")
    a_tablo = _fikstur_tablo(S, ("kasik",), ("sabun",))
    b_tablo = _fikstur_tablo(S, ("sabun",), ("kasik",))
    a = S.siniflandir_toplu(_FIKSTUR_URUNLER, "Ev", esik=0.5, adaylar=a_tablo)
    b = S.siniflandir_toplu(_FIKSTUR_URUNLER, "Ev", esik=0.5, adaylar=b_tablo)
    dogrula("T13a fikstur A: 1. gecis 'kasik' urunlerini Mutfak'a atiyor",
            [x[0] for x in a[:6]] == ["Mutfak"] * 3 + ["Banyo"] * 3, a)
    dogrula("T13b fikstur B: terimler YER DEGISTIRINCE 1. gecis atamasi da yer degistirdi",
            [x[0] for x in b[:6]] == ["Banyo"] * 3 + ["Mutfak"] * 3, b)
    dogrula("T13c hedef urun 2. GECISLE atandi (1. geciste eslesmiyor)",
            a[6][1] == 2 and b[6][1] == 2, (a[6], b[6]))
    dogrula("T13d 🔴 1. GECIS CIKTISI DEGISINCE 2. GECIS ATAMASI DA DEGISTI (%r -> %r) — "
            "sozluk ELLE YAZILMIS OLSAYDI degismezdi" % (a[6][0], b[6][0]),
            a[6][0] != b[6][0] and a[6][0] and b[6][0], (a[6], b[6]))
    sozluk = S.sozluk_turet(["Mutfak", "Mutfak", ""], [("kasik", "kutu"), ("kasik",), ("x",)])
    dogrula("T13e sozluk YALNIZ 1. gecis atamasi olan urunlerden turer (atanmamis urun "
            "sozluge girmez)",
            sozluk.grup_n["Mutfak"] == 2 and sozluk.genel_n == 2
            and sozluk.genel_df.get("x", 0) == 0 and sozluk.grup_df["Mutfak"]["kasik"] == 2,
            (dict(sozluk.grup_n), dict(sozluk.genel_df)))

    # ══ T14 — ESIK FIILEN OLCUYOR ══════════════════════════════════════════════════
    print("\n[T14] ESIK DUYARLILIGI — esik degisince dagilim degisiyor")
    dusuk = S.siniflandir_toplu(ev, "Ev", esik=0.0)
    yuksek = S.siniflandir_toplu(ev, "Ev", esik=1e9)
    d2 = sum(1 for _d, g in dusuk if g == 2)
    y2 = sum(1 for _d, g in yuksek if g == 2)
    d3 = sum(1 for _d, g in dusuk if g == 3)
    y3 = sum(1 for _d, g in yuksek if g == 3)
    dogrula("T14a esik 0.0 -> 2.gecis %d · 3.gecis %d | esik sonsuz -> 2.gecis %d · "
            "3.gecis %d (esik FIILEN dagilimi kaydiriyor)" % (d2, d3, y2, y3),
            d2 > y2 and y3 > d3 and y2 == 0, (d2, y2, d3, y3))
    dogrula("T14b esik ne olursa olsun BOS KALAN 0 (3. gecis her zaman yakaliyor)",
            not [1 for d, _g in dusuk if not d] and not [1 for d, _g in yuksek if not d])
    dogrula("T14c secilen esik %.1f bit ve ESIK_YAKINLIK TEK KAYNAK (varsayilan kosum "
            "esikli kosumla ayni)" % S.ESIK_YAKINLIK,
            S.siniflandir_toplu(ev, "Ev") == S.siniflandir_toplu(ev, "Ev",
                                                                 esik=S.ESIK_YAKINLIK))

    # ══ TS — IKIZ TANIM: kume <-> siniflandirici tablosu ═══════════════════════════
    print("\n[TS] IKIZ TANIM — arama.ALTKATEGORI_IZINLI ile ADAYLAR tablosu ayrisamaz")
    ayrisan = []
    for kategori in arama.ALTKATEGORI_IZINLI:
        kume = set(arama.ALTKATEGORI_IZINLI[kategori])
        tablo = set(S.kume_adlari(kategori))
        if kume != tablo:
            ayrisan.append((kategori, sorted(kume - tablo), sorted(tablo - kume)))
    dogrula("TS1 her kategoride kume == siniflandirici tablosu (kume disi grup yok, "
            "terimsiz kume degeri yok)", not ayrisan, ayrisan)
    dogrula("TS2 tablodaki HER grubun terimi VAR (terimsiz grup 1. geciste olu kalir)",
            not [(k, ad) for k in S.ADAYLAR for ad, s, t, _g in S.ADAYLAR[k]
                 if s in (S.BELIRGIN, S.MIRAS, S.ARTIK) and not t])

    print("\nSONUC: %s — gecen %d · kalan %d"
          % ("YESIL" if kalan[0] == 0 else "KIRMIZI", gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


# ── CIFT YONLU MUTASYON ─────────────────────────────────────────────────────────────
# KIRMIZI beklenen = oldurucu mutant · YESIL beklenen = ILGISIZ degisiklik (kapinin
# gereginden genis olmadiginin kaniti).
MUTANTLAR = [
    ("M1", "altkategori-sinifla.py",
     '("Bardak Altlıkları", ELENEN, ("bardak altligi",),',
     '("Bardak Altlıkları", BELIRGIN, ("bardak altligi",),', "KIRMIZI",
     "T4c: esik kontrolu kalkar, <15 urunlu aday kumeye girer"),
    ("M2", "altkategori-sinifla.py", "    return onde + sonda", "    return sonda + onde",
     "KIRMIZI", "T7: artik kova oncelikte BASA gecer -> her sey kovaya duser"),
    ("M3", "altkategori-sinifla.py",
     "    if arama.altkategori_sebebi(kategori, ad) is not None:\n"
     "        return \"\"\n    return arama.altkategori_metin(ad)",
     "    return ad + \" (mutant)\"", "KIRMIZI",
     "T6: fail-closed kalkar -> siniflandirici kume DISI deger uretir"),
    ("M4", "arama.py", '        "Pervaneler",\n', '        "Pervanelar",\n', "KIRMIZI",
     "T2: MIRAS bir Marin degerinin harfi degisir -> 935 kayit gecersizlesir"),
    ("M5", "altkategori-sinifla.py",
     "    t = (adaylar or ADAYLAR).get(kategori, ())\n",
     "    t = (adaylar or ADAYLAR).get(kategori, ())\n"
     "    _sira._n = getattr(_sira, '_n', 0) + 1\n"
     "    if _sira._n % 2 == 0:\n        t = tuple(reversed(t))\n", "KIRMIZI",
     "T5: siniflandirma girdi SIRASINA duyarli olur"),
    ("M6", "altkategori-sinifla.py", "    adlar = [e[0] for e in sira]",
     "    adlar = [_oge[0] for _oge in sira]", "YESIL",
     "ILGISIZ (KONTROL): davranissiz yeniden adlandirma — YESIL kalmali"),
    ("M7", "altkategori-sinifla.py",
     "        for t in jet:\n            grup_df[ad][t] += 1\n            genel_df[t] += 1",
     "        for t in ('far', 'lamba', 'motor', 'kapi'):\n"
     "            grup_df[ad][t] += 1\n            genel_df[t] += 1", "KIRMIZI",
     "T13: 2. gecis sozlugu ELLE YAZILMIS sabit listeye doner (veriden turemez)"),
]

KOPYALANAN = ["arama.py", "altkategori-sinifla.py", "altkategori-sinifla-test.py",
              "altkategori-kapisi.py", "d1-sync.py", "d1-sema.sql", "duzelt.py",
              "gorsel_koken.py", "konfigur-bundle-kapisi.py"]


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _kopya_kur():
    tmp = tempfile.mkdtemp(prefix="pruvo-altkat-sinifla-mut-")
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in KOPYALANAN:
        shutil.copy2(os.path.join(GERCEK_KOK, "tools", ad), os.path.join(tmp, "tools", ad))
    os.symlink(os.path.join(GERCEK_KOK, "urunler.json"), os.path.join(tmp, "urunler.json"))
    return tmp


def _kok_kostur(tmp):
    return subprocess.run([sys.executable, os.path.join(tmp, "tools",
                                                        "altkategori-sinifla-test.py"),
                           "--kok", tmp], capture_output=True, text=True)


def mutasyon():
    print("=== CIFT YONLU MUTASYON — mutant KOPYAYA uygulanir, CANLI dosyaya ASLA")
    once = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    basarisiz = []
    # M00 MUTASYONSUZ KONTROL — harness saglam mi. Kirmiziysa TUM mutant sonuclari yalanci.
    tmp0 = _kopya_kur()
    p0 = _kok_kostur(tmp0)
    kontrol = p0.returncode == 0
    print("  %s M00 [YESIL] MUTASYONSUZ KONTROL -> %s"
          % ("OK  " if kontrol else "HATA", "YESIL" if kontrol else "KIRMIZI"))
    shutil.rmtree(tmp0, ignore_errors=True)
    if not kontrol:
        print("     " + (p0.stderr or p0.stdout).strip().splitlines()[-1][:300])
        print("\nMUTASYON SONUCU: OLCULEMEDI — harness bozuk.")
        return 1
    for kod, dosya, eski, yeni, beklenen, aciklama in MUTANTLAR:
        tmp = _kopya_kur()
        hedef = os.path.join(tmp, "tools", dosya)
        with open(hedef, encoding="utf-8") as f:
            metin = f.read()
        sayi = metin.count(eski)
        if sayi != 1:
            basarisiz.append("%s CAPA BAYAT (%d eslesme) %s" % (kod, sayi, dosya))
            print("  HATA %s [%s] %s -> CAPA BAYAT (%d eslesme) | EKSEN OLCULMEDI"
                  % (kod, beklenen, dosya, sayi))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        mutant = metin.replace(eski, yeni)
        if mutant == metin:
            basarisiz.append("%s MUTANT UYGULANMADI %s" % (kod, dosya))
            shutil.rmtree(tmp, ignore_errors=True)
            continue
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(mutant)
        p = _kok_kostur(tmp)
        goruldu = "KIRMIZI" if p.returncode != 0 else "YESIL"
        oldu = [s.strip() for s in p.stdout.splitlines() if s.strip().startswith("KALDI")]
        isaret = "OK  " if goruldu == beklenen else "HATA"
        if goruldu != beklenen:
            basarisiz.append("%s %s: beklenen %s, goruldu %s"
                             % (kod, dosya, beklenen, goruldu))
        # 🔴 KIRMIZI YETMEZ: mutant COKEREK de rc!=0 verebilir. En az bir ADLANDIRILMIS
        # iddianin KALDI demesi sarti "olduruldu" ile "olculemedi"yi ayirir.
        if goruldu == "KIRMIZI" and beklenen == "KIRMIZI" and not oldu:
            basarisiz.append("%s %s: KIRMIZI ama HICBIR iddia KALDI demedi — kapi COKTU"
                             % (kod, dosya))
        print("  %s %s [%s] %s -> %s (%d iddia kirmizi) | %s"
              % (isaret, kod, beklenen, dosya, goruldu, len(oldu), aciklama))
        for s in oldu[:3]:
            print("        " + s[:150])
        shutil.rmtree(tmp, ignore_errors=True)
    sonra = {d: _sha(os.path.join(GERCEK_KOK, "tools", d)) for d in KOPYALANAN}
    bozuk = [d for d in once if once[d] != sonra[d]]
    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(once), "DEGISMEDI ✔" if not bozuk else "DEGISTI ✘ %s" % bozuk))
    if bozuk:
        basarisiz.append("CANLI DOSYA DEGISTI: %s" % bozuk)
    if basarisiz:
        print("\nMUTASYON SONUCU: %d/%d beklenti TUTMADI" % (len(basarisiz), len(MUTANTLAR)))
        for s in basarisiz:
            print("  - " + s)
        return 1
    print("\nMUTASYON SONUCU: %d/%d beklenti TUTTU ✔" % (len(MUTANTLAR), len(MUTANTLAR)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK)
    ap.add_argument("--mutasyon", action="store_true")
    a = ap.parse_args()
    if a.mutasyon:
        return mutasyon()
    print("=== ALT KATEGORI KUME + SINIFLANDIRICI KABUL (kok: %s)" % a.kok)
    return kabul(a.kok)


if __name__ == "__main__":
    sys.exit(main())

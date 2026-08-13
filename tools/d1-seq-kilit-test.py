#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 seq DAIRESEL KILIT kabul testi (offline; canli D1'e DOKUNMAZ — saf fonksiyon fiksturu).

OLCULEN OLAY (13 Agu 2026): `--durum` rc=1 diyordu — D1=26620, urunler.json benzersiz=26756,
EKSIK=136, FAZLA=0. Kilit DAIRESELDI:
  * `diff_plan` mid-array yeni id icin iki komsu arasinda TAM SAYI bosluk ister; bulamayinca
    fail-loud durur ve `--seq-normalize` kosulmasini ister (kesirli seq YAZMAZ).
  * `seq_normalize` ise on-kosul olarak "D1 id kumesi == kanonik katalog id kumesi" arardi;
    136 id eksik oldugu icin O DA dururdu.
  -> INSERT normalize'i, normalize INSERT'i bekliyordu. Site urunu gosterirken Ege (D1'den
  okur) 136 urunu ONEREMIYORDU = SESSIZ satis kaybi.

ONARIM EKSENI: on-kosul GEVSETILMEDI, SIVRILTILDI — "kume esitligi" yerine "FAZLA>0"
(D1'de var, katalogda YOK). Bu test o ekseni ve DEGISMEMESI gerekenleri birlikte cakar:
  V1 EKSIK VAR / FAZLA YOK -> normalize plan URETIR, yalniz D1'de MEVCUT id'ler icin.
  V2 FAZLA VAR            -> normalize DURUR (fail-loud), hicbir UPDATE uretilmez.
  V3 SANDVIC COZULDU      -> seyrek (SEQ_ADIM arali) tabloda diff_plan tam-sayi orta nokta bulur.
  V4 SANDVIC HALA YAKALANIYOR -> bitisik komsuda diff_plan HALA fail-loud durur (regresyon).
  V5 GERI ALMA            -> eksik TEK BASINA geri alma sebebi DEGIL; ortak kumede sira
                             sapmasi / satir sayisi degisimi geri almayi TETIKLER.

IKINCI OLAY — KUYRUK BLOGU (13 Agu 2026, ayni gun): normalize kosup seq'ler SEYREK
(1.000.000 arali) hale geldigi HALDE `d1-sync.py` HALA rc=1 veriyordu. Kok neden: 136
eksik id iki BITISIK bloktu ve kuyruk blogu (dizinin SONUNA dayanan 44 yeni id) alt
komsusuzdu; eski kuyruk kolu bosluktan yalniz 1 tam sayi aliyordu (`atanan = yuksek - 1`)
-> IKINCI kuyruk kaydi `yuksek - alt <= 1` gorup DURUYORDU. 🔴 Ariza yogunluga DEGIL blok
UZUNLUGUNA bagli: kuyrukta k>=2 yeni id varsa aralik ne kadar genis olursa olsun (ust=
45.000.000 ile de) DURUYORDU. H5 hukmu: kuyruk blogu tek tam sayi degil, bloga ORANLI
adim tuketir — `adim = yuksek // (k + 1)`, sondan i. kayit `i * adim` alir.
  K1  kuyrukta 1 yeni id  -> uretir (eski davranisla AYNI sonuc sinifi: 0 < atanan < yuksek).
  K2  kuyrukta 2 yeni id  -> URETIR (bu vaka onarimdan ONCE DURUYORDU) + bloga ORANLI dagilir.
  K44 kuyrukta 44 yeni id (ust=45.000.000) -> hepsi uretilir, farkli/tam sayi/pozitif/<ust.
  K_TASMA yuksek kucuk + blok buyuk (ust=3, k=10) -> yer YOK -> AYNEN fail-loud DURUR.
  K_MID_REGRESYON ayni dizide hem mid-array hem kuyruk varken mid-array davranisi DEGISMEDI.

MUTASYON BATARYASI (`--mutasyon`): alti OLDURUCU mutant. Her mutant, `tools/d1-sync.py`nin
BIREBIR kopyasi uzerinde TEK bir metin degisimiyle uretilir, kopya `tools/` altina gecici
sibling olarak yazilir (kardes modul importlari ayni dizinden cozulsun diye), yuklenir,
vakalar yeniden kosulur ve dosya `finally` ile SILINIR. Kanonik kaynak DEGISMEZ (`git diff`
temiz kalir) ve `sys.dont_write_bytecode` ile `__pycache__` uretilmez.
  M1 on-kosul kaldirilir      : `if fazla:`                  -> `if False:`        => V2 KIRMIZI
  M2 eksik id'e de UPDATE     : `if uid in mevcut and mevcut[uid] != hedef[uid]`
                                                             -> `if mevcut.get(uid) != hedef[uid]`
                                                                                   => V1 KIRMIZI
  M3 kesir yasagi kolu silinir: `elif yuksek - alt <= 1:`     -> `elif False:`      => V4 KIRMIZI
  M4 geri alma NO-OP          : `return (sonra != once or bool(fark) or bool(ortak_sapma)), ...`
                                                             -> `return False, ...` => V5 KIRMIZI
  M5 kuyrukta ORANLI adim yok : `adim = yuksek // (blok_k + 1)` -> `adim = 1`
                                (eski davranisin sinifi: blok araligin DIBINE yigilir)
                                                                   => K2 KIRMIZI
  M6 kuyruk tasma kolu silinir: `if adim < 1:`                 -> `if False:`      => K_TASMA KIRMIZI
Ayni degisimler kanonik dosyaya ELLE de uygulanabilir; kanit YENIDEN URETILEBILIR.
"""
import importlib.util
import os
import re
import sys

sys.dont_write_bytecode = True   # __pycache__ artigi birakma (Okan disk emri)

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARACLAR = os.path.join(KOK, "tools")
YOL = os.path.join(ARACLAR, "d1-sync.py")

MUTANTLAR = [
    ("M1 on-kosul kaldirildi (FAZLA>0'da da kosar)",
     "    if fazla:\n", "    if False:\n", "V2"),
    ("M2 eksik id icin de UPDATE uretilir (satir ekleme yolu)",
     "for uid in hedef if uid in mevcut and mevcut[uid] != hedef[uid]]",
     "for uid in hedef if mevcut.get(uid) != hedef[uid]]", "V1"),
    ("M3 diff_plan kesir yasagi kolu silindi",
     "                elif yuksek - alt <= 1:\n", "                elif False:\n", "V4"),
    ("M4 geri alma kolu her zaman NO-OP",
     "    return (sonra != once or bool(fark) or bool(ortak_sapma)), fark, ortak_sapma\n",
     "    return False, fark, ortak_sapma\n", "V5"),
    ("M5 kuyruk kolunda bloga ORANLI adim yerine sabit 1",
     "                    adim = yuksek // (blok_k + 1)\n",
     "                    adim = 1\n", "K2"),
    ("M6 kuyruk tasma (adim<1) fail-loud kolu silindi",
     "                    if adim < 1:\n", "                    if False:\n", "K_TASMA"),
]


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def urun(uid):
    return {"id": uid, "baslik": uid, "kategori": "Oyun/Hobi", "marka": [],
            "fiyat": "100 TL", "gorseller": [], "aciklama": uid}


# INSERT SQL'inin 3. VALUES alani = atanan seq. Iddialar SQL METNINDEN okunur (fonksiyon
# ic degiskeninden DEGIL): yazilan sey ile iddia edilen sey AYNI yuzeyden gelsin.
SEQ_DESEN = re.compile(r"VALUES \('([^']*)','[^']*',(-?\d+),")


def seq_oku(sql):
    e = SEQ_DESEN.search(sql)
    return (e.group(1), int(e.group(2))) if e else (None, None)


def kuyruk_vaka(m, k, ust):
    """KUYRUK fiksturu: [b2, b1(bilinen; en dusuk seq = ust), q<k> ... q1(yeni)].
    q1 dizinin SON kaydidir. Doner: (atanan {id: seq}, patladi_mi, mesaj)."""
    bilinenler = [urun("b2"), urun("b1")]
    seqler = {"b2": ust * 2, "b1": ust}
    var = {u["id"]: (m.arama.urun_hash(u), "") for u in bilinenler}
    dizi = bilinenler + [urun("q%d" % i) for i in range(k, 0, -1)]
    try:
        yeni_sql, _d, _b, _s, _g = m.diff_plan(dizi, var, {}, False, seqler["b2"],
                                               dict(seqler))
        return dict(seq_oku(s) for s in yeni_sql), False, ""
    except SystemExit as e:
        return {}, True, str(e.code)


def vakalar(m):
    """Doner: {vaka: (gecti_mi, detay)}. Ayni govde hem kanonik hem mutant modul icin kosar."""
    sonuc = {}

    # ── V1 — EKSIK VAR / FAZLA YOK: plan URETILIR, yalniz D1'de MEVCUT id'ler icin ──────
    katalog = [urun(x) for x in ("a", "b", "c", "d")]
    hedef = m.seq_hedefleri(katalog)
    # D1'de yalniz a ve c var (b ve d EKSIK = olculen 136 vakasinin fiksturu); ikisinin de
    # seq'i kanonik degerden SAPMIS -> ikisi icin de UPDATE beklenir.
    mevcut_v1 = {"a": 7, "c": 3}
    ifadeler, hata = m.seq_normalize_plan(katalog, mevcut_v1)
    kapsanan = [uid for uid in ("a", "b", "c", "d")
                if ifadeler is not None and any("'%s'" % uid in s for s in ifadeler)]
    sonuc["V1a plan URETILIR (EKSIK>0, FAZLA=0 durdurmaz)"] = (
        hata is None and ifadeler is not None and len(ifadeler) == 2, "hata=%r" % (hata,))
    sonuc["V1b UPDATE yalniz D1'de MEVCUT id'leri kapsar (eksik id icin UPDATE YOK)"] = (
        kapsanan == ["a", "c"], "kapsanan=%s" % (kapsanan,))
    sonuc["V1c UPDATE kanonik SEYREK hedefi yazar (SEQ_ADIM arali)"] = (
        ifadeler is not None
        and ("SET seq=%d WHERE id='a';" % hedef["a"]) in " ".join(ifadeler)
        and ("SET seq=%d WHERE id='c';" % hedef["c"]) in " ".join(ifadeler),
        str(ifadeler))

    # ── V2 — FAZLA VAR: fail-loud DUR, hicbir UPDATE uretilmez ─────────────────────────
    mevcut_v2 = dict(mevcut_v1)
    mevcut_v2["hayalet"] = 99          # D1'de VAR, kanonik katalogda YOK
    ifadeler2, hata2 = m.seq_normalize_plan(katalog, mevcut_v2)
    sonuc["V2a FAZLA>0 -> fail-loud DURUR (bayat-yazici korumasi GEVSEMEZ)"] = (
        hata2 is not None and "hayalet" in hata2, "hata=%r" % (hata2,))
    sonuc["V2b FAZLA>0 -> hicbir UPDATE uretilmez"] = (ifadeler2 is None, str(ifadeler2))

    # ── V3 — SANDVIC COZULDU: seyrek tabloda mid-array yeni id TAM SAYI orta nokta alir ─
    # `seq_hedefleri` SEYREK uretir; normalize kostuktan sonraki dunya budur.
    u3, un, u2, u1 = urun("u3"), urun("un"), urun("u2"), urun("u1")
    seyrek = m.seq_hedefleri([u3, u2, u1])          # 3*SEQ_ADIM, 2*SEQ_ADIM, 1*SEQ_ADIM
    var = {u["id"]: (m.arama.urun_hash(u), "") for u in (u3, u2, u1)}
    try:
        yeni3, _d, _b, _s, _g = m.diff_plan([u3, un, u2, u1], var, {}, False,
                                            seyrek["u3"], dict(seyrek))
        cikti3, patladi3 = yeni3, False
    except SystemExit as e:
        cikti3, patladi3 = str(e.code), True
    beklenen_orta = seyrek["u2"] + (seyrek["u3"] - seyrek["u2"]) // 2
    sonuc["V3a seyrek tabloda 'SEQ TAM SAYI ARALIGI TUKENDI' URETILMEZ"] = (
        not patladi3, str(cikti3))
    sonuc["V3b mid-array yeni id TAM SAYI orta noktayi alir"] = (
        not patladi3 and len(cikti3) == 1 and str(beklenen_orta) in cikti3[0]
        and ".0" not in cikti3[0], str(cikti3))

    # ── V4 — SANDVIC HALA YAKALANIYOR: bitisik komsuda diff_plan fail-loud (H3 regresyonu) ─
    bitisik = {"u3": 1000000, "u2": 999999, "u1": 999998}
    try:
        m.diff_plan([u3, un, u2, u1], var, {}, False, bitisik["u3"], dict(bitisik))
        v4 = (False, "diff_plan durmadi — kesirli/cakisan seq yazilirdi")
    except SystemExit as e:
        v4 = ("SEQ TAM SAYI ARALIGI TUKENDI" in str(e.code)
              and "--seq-normalize" in str(e.code), str(e.code))
    sonuc["V4 bitisik komsuda diff_plan HALA fail-loud durur"] = v4

    # ── K1 — kuyrukta TEK yeni id: eski davranisla AYNI sonuc sinifi ───────────────────
    ust1 = 2000000
    a1, p1, msj1 = kuyruk_vaka(m, 1, ust1)
    sonuc["K1 kuyrukta 1 yeni id -> tam sayi uretir (0 < atanan < ust)"] = (
        not p1 and len(a1) == 1 and isinstance(a1.get("q1"), int)
        and 0 < a1["q1"] < ust1, "patladi=%s a=%s %s" % (p1, a1, msj1))

    # ── K2 — kuyrukta IKI yeni id: ONARIMIN EKSENI (bu vaka once DURUYORDU) ────────────
    k2, ust2 = 2, 3000000
    a2, p2, msj2 = kuyruk_vaka(m, k2, ust2)
    d2 = [a2.get("q1"), a2.get("q2")]                       # sondan basa: q1 en KUCUK olmali
    sonuc["K2a kuyrukta 2 yeni id URETILIR (fail-loud DURMAZ)"] = (
        not p2 and len(a2) == 2, "patladi=%s a=%s %s" % (p2, a2, msj2))
    sonuc["K2b iki atama TAM SAYI, FARKLI, monoton (dizinin sonundaki en KUCUK)"] = (
        all(isinstance(v, int) for v in d2) and 0 < d2[0] < d2[1] < ust2,
        "atamalar=%s ust=%d" % (d2, ust2))
    # BLOGA ORANLI: 0 -> q1 -> q2 -> ust bosluklarinin HEPSI en az bir "adim" olmali.
    # Sabit adim=1 (eski davranisin sinifi) blogu araligin DIBINE yigar -> bu iddia KIRMIZI.
    bosluk2 = ([d2[0], d2[1] - d2[0], ust2 - d2[1]]
               if all(isinstance(v, int) for v in d2) else [])
    sonuc["K2c blok araliga ORANLI dagilir (her bosluk >= ust//(k+1))"] = (
        bool(bosluk2) and min(bosluk2) >= ust2 // (k2 + 1),
        "bosluklar=%s beklenen_adim=%d" % (bosluk2, ust2 // (k2 + 1)))

    # ── K44 — olculen canli vaka: 44 kayitlik kuyruk, ust=45.000.000 ───────────────────
    k44, ust44 = 44, 45000000
    a44, p44, msj44 = kuyruk_vaka(m, k44, ust44)
    v44 = sorted(a44.values())
    sonuc["K44 44'luk kuyruk (ust=45.000.000) TAMAMEN uretilir"] = (
        not p44 and len(a44) == k44, "patladi=%s adet=%d %s" % (p44, len(a44), msj44))
    sonuc["K44b hepsi tam sayi, FARKLI, pozitif ve en buyugu ust'ten KUCUK"] = (
        len(v44) == k44 and all(isinstance(v, int) for v in v44)
        and len(set(v44)) == k44 and v44[0] > 0 and v44[-1] < ust44,
        "en_kucuk=%s en_buyuk=%s adet=%d" % (v44[:1], v44[-1:], len(set(v44))))

    # ── K_TASMA — yer GERCEKTEN yok: fail-loud kolu KORUNUR ────────────────────────────
    a_t, p_t, msj_t = kuyruk_vaka(m, 10, 3)
    sonuc["K_TASMA ust=3 + 10'luk kuyruk -> AYNEN fail-loud DURUR"] = (
        p_t and "SEQ TAM SAYI ARALIGI TUKENDI" in msj_t and "--seq-normalize" in msj_t,
        "patladi=%s a=%s msj=%s" % (p_t, a_t, msj_t))

    # ── K_MID_REGRESYON — ayni dizide hem mid-array hem kuyruk: mid-array DEGISMEDI ────
    u4, u3m, u2m, u1m = urun("u4"), urun("u3"), urun("u2"), urun("u1")
    unm, q2m, q1m = urun("un"), urun("q2"), urun("q1")
    seq_m = {"u4": 5000000, "u3": 4000000, "u2": 3000000, "u1": 2000000}
    var_m = {u["id"]: (m.arama.urun_hash(u), "") for u in (u4, u3m, u2m, u1m)}
    try:
        yeni_m, _dm, _bm, _sm, _gm = m.diff_plan([u4, unm, u3m, u2m, u1m, q2m, q1m],
                                                 var_m, {}, False, seq_m["u4"], dict(seq_m))
        atanan_m, patladi_m = dict(seq_oku(s) for s in yeni_m), False
    except SystemExit as e:
        atanan_m, patladi_m = {}, str(e.code)
    beklenen_mid = seq_m["u3"] + (seq_m["u4"] - seq_m["u3"]) // 2
    sonuc["K_MID_REGRESYON mid-array TAM SAYI orta noktayi ALMAYA DEVAM EDER"] = (
        patladi_m is False and atanan_m.get("un") == beklenen_mid,
        "atanan=%s beklenen=%d patladi=%s" % (atanan_m, beklenen_mid, patladi_m))
    kq = [atanan_m.get("q1"), atanan_m.get("q2")]
    sonuc["K_MID_REGRESYON2 ayni dizideki kuyruk blogu da uretilir (mid-array'e sizmadan)"] = (
        all(isinstance(v, int) for v in kq) and 0 < kq[0] < kq[1] < seq_m["u1"],
        "kuyruk=%s ust=%d" % (kq, seq_m["u1"]))

    # ── V5 — GERI ALMA: eksik TEK BASINA sebep DEGIL; ortak kumede sapma SEBEP ─────────
    son_temiz = {"a": hedef["a"], "c": hedef["c"]}          # b, d hala D1'de YOK
    g1, _f1, _o1 = m.seq_geri_alma_gerek(katalog, hedef, son_temiz, 2, 2)
    sonuc["V5a EKSIK tek basina geri alma TETIKLEMEZ"] = (not g1, "geri_al=%s" % g1)

    # Ortak kumede GORELI SIRA sapmasi (deger farkindan BAGIMSIZ olcmek icin hedef=son verilir):
    # kanonik sira a > b > c iken canli sira b > c > a.
    katalog3 = [urun(x) for x in ("a", "b", "c")]
    sapik = {"a": 100, "b": 300, "c": 200}
    g2, f2, o2 = m.seq_geri_alma_gerek(katalog3, dict(sapik), sapik, 3, 3)
    sonuc["V5b ortak kumede SIRA sapmasi geri almayi TETIKLER"] = (
        g2 and not f2 and bool(o2), "geri_al=%s fark=%s ortak_sapma=%s" % (g2, f2, o2))

    g3, _f3, _o3 = m.seq_geri_alma_gerek(katalog, hedef, son_temiz, 2, 3)
    sonuc["V5c satir sayisi degisimi (eszamanli yazar) geri almayi TETIKLER"] = (
        g3, "geri_al=%s" % g3)

    g4, f4, _o4 = m.seq_geri_alma_gerek(katalog, hedef, {"a": hedef["a"], "c": 1}, 2, 2)
    sonuc["V5d ortak kumede DEGER farki geri almayi TETIKLER"] = (
        g4 and f4 == ["c"], "geri_al=%s fark=%s" % (g4, f4))

    return sonuc


def kos(m, basliksiz=False):
    sonuc = vakalar(m)
    kalan = []
    for ad in sonuc:
        gecti, detay = sonuc[ad]
        if gecti:
            if not basliksiz:
                print("GECTI " + ad)
        else:
            kalan.append(ad)
            if not basliksiz:
                print("KALDI " + ad + " — " + detay)
    return sonuc, kalan


def mutant_kos():
    """Her mutant icin: kopyayi mutasyona ugrat -> hedef vaka KIRMIZI mi? -> kopyayi SIL."""
    with open(YOL, encoding="utf-8") as f:
        kaynak = f.read()
    olduren = 0
    for i, (ad, eski, yeni, hedef_vaka) in enumerate(MUTANTLAR, 1):
        adet = kaynak.count(eski)
        if adet != 1:
            print("KALDI %s — mutasyon capasi %d kez gecti (1 olmali): %r" % (ad, adet, eski))
            continue
        # Sibling yol: d1-sync.py kardes modullerini (arama, git_ortami, konfigur-bundle-kapisi)
        # KENDI dizininden cozer -> kopya BASKA dizine yazilirsa import COKER (sahte kirmizi).
        # Her mutanta AYRI ad: ayni saniyede yeniden yuklenen ayni ad bayat bytecode riskidir.
        kopya = os.path.join(ARACLAR, "_seq_mutant_%d_gecici.py" % i)
        try:
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
            mm = modul_yukle(kopya, "d1_sync_mutant_%d" % i)
            _sonuc, kalan = kos(mm, basliksiz=True)
            kirmizi = [k for k in kalan if k.startswith(hedef_vaka)]
            if kirmizi:
                olduren += 1
                print("OLDURULDU %s -> %s KIRMIZI (%s)" % (ad, hedef_vaka, "; ".join(kirmizi)))
            else:
                print("HAYATTA KALDI %s -> %s hala YESIL (test bu mutanti GORMUYOR)"
                      % (ad, hedef_vaka))
        finally:
            if os.path.exists(kopya):
                os.remove(kopya)
    print("MUTANT_KIRMIZI=%d/%d" % (olduren, len(MUTANTLAR)))
    return olduren == len(MUTANTLAR)


def main():
    if "--mutasyon" in sys.argv[1:]:
        sys.exit(0 if mutant_kos() else 1)
    m = modul_yukle(YOL, "d1_sync_seq_kilit")
    sonuc, kalan = kos(m)
    print("SONUC: %d gecti, %d kaldi" % (len(sonuc) - len(kalan), len(kalan)))
    sys.exit(0 if not kalan else 1)


main()

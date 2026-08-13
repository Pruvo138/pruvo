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

MUTASYON BATARYASI (`--mutasyon`): dort OLDURUCU mutant. Her mutant, `tools/d1-sync.py`nin
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
Ayni degisimler kanonik dosyaya ELLE de uygulanabilir; kanit YENIDEN URETILEBILIR.
"""
import importlib.util
import os
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

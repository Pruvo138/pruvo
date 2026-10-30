#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON SURUCUSU — tools/ata-lisans-test.py GERCEKTEN olcuyor mu?

"Batarya kostum" ANLATISI KANIT DEGILDIR; surucu REPODA durur ve yeniden kosulabilir
([[mutasyon-kaniti-yeniden-uretilebilir]]). Kabul = cikis kodu degil, HER MUTANTIN
BEKLENEN ISARETI + KIRMIZI mutantta DUSEN IDDIANIN DOGRU iddia oldugu.

🔴 NEDEN BU KADAR MUTANT VAR: onceki batarya 3 oldurucu ile "gecti" diyordu ama bagimsiz
curutucu 12 SESSIZ GECIS olctu — batarya KENDI DELIGINI GORMUYORDU
([[beyan-edilmis-survivor]]). Artik her delik (D1..D12) icin AYRI bir oldurucu mutant vardir
ve her biri o delige ait D-IDDIASINI dusurmelidir. Mutantin sadece "kirmizi yakmasi" YETMEZ:
BASARISIZ dokumu o delige ait etiketi ICERMELIDIR.

🔴 CANLI AGACA ASLA DOKUNMAZ: tools/ gecici bir dizine KOPYALANIR, mutasyon KOPYAYA
uygulanir, test KOPYADAN kosulur ([[mutasyon-diske-yazma-tuzagi]]).

🔴 CAPA TEKILLIGI (2. tur onarimi): dusen iddianin kaniti ALT-DIZE testidir — bu yuzden capa
TEKIL olmak ZORUNDADIR. Eskiden OLD-03'un capasi 'D1' idi ve dokumdeki 'D11b' / 'D12'
satirlarina da uyuyordu: mutant BASKA bir iddiayi dusurse bile kanit YESIL yanardi. Artik
test her BASARISIZ satirini '[<etiket>]' ile yazar ve capalar KOSELI PARANTEZLIDIR
('[D1]' ile '[D11b]' artik ayrisir).

KONTROL MUTANTLARI (gurultu makinesi olmadigimizin kaniti): gercek ama KAPSAM DISI
davranis/sabit degisiklikleri YESIL kalmalidir.

Kosum:  python3 tools/ata-lisans-mutasyon.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
KAPI_ADI = "ata-lisans-kapisi.py"
TEST_ADI = "ata-lisans-test.py"

# (ad, aranan, yerine, beklenen_isaret, kanit_metni)
MUTANTLAR = [
    # ---------------- ACIKLAMA EKSI (23 Eki 2026) ----------------
    # ONCUL: Thingiverse 4853978/7332849/7332847 = thing:3543408 (CC BY-NC-ND); `ancestors`
    # BOS, atif YALNIZ aciklama metninde. Bu 4 mutant o eksenin KIRILAMAZ oldugunu olcer.
    ("AK-01 tetik kontrolu kaldir",
     '        if not any(d.search(ham) for d in ACIKLAMA_TETIKLERI):\n'
     '            continue                                    # tetik YOK -> bu alandan ref yok',
     '        pass',
     "KIRMIZI", "[A5-ACIKLAMA-TETIKSIZ]"),
    # D19 (29 Eki 2026): "adapted from" tetigi sokulurse canli th1252975 sekli yeniden
    # ALAN-YOK rc=0 olur; genisletilirse ("adapter" parca adi) yanlis-ihlal uretir.
    ("AK-D19a 'adapted' tetigi sokulur",
     '    re.compile(r"\\badapt(?:ed|ing|ation|ion)s?\\b", re.IGNORECASE),\n',
     '',
     "KIRMIZI", "[A10-ACIKLAMA-ADAPTED]"),
    ("AK-D19b 'adapt' tetigi koke genisler (adapter parca adi tetik olur)",
     '    re.compile(r"\\badapt(?:ed|ing|ation|ion)s?\\b", re.IGNORECASE),\n',
     '    re.compile(r"\\badapt\\w*", re.IGNORECASE),\n',
     "KIRMIZI", "[A11-ACIKLAMA-ADAPTER-ATA-YOK]"),
    ("AK-02 thing: kimlik deseni kaldir",
     '        adaylar += ["https://www.thingiverse.com/thing:%s" % n\n'
     '                    for n in _THING_KIMLIK_RE.findall(ham)]',
     '        adaylar = adaylar',
     "KIRMIZI", "[A2-ACIKLAMA-THING-KIMLIK]"),
    ("AK-03 ND kurali kaldir",
     '        if lisans_nd_mi(lisans_metni):\n'
     '            return [_sonuc(DURUM_IHLAL, "ATA LISANSI ND — turev yasak",\n'
     '                           ata, host, kimlik, lisans_metni, adaptor.ad, derinlik)]',
     '        if False:\n            pass',
     "KIRMIZI", "[A9-ATA-ND]"),
    ("AK-04 'I used this design' deseni kaldir (ilk 9 desen YETMEZ)",
     '    re.compile(r"\\bus(?:ed|ing|es)\\s+(?:this|the|that|his|her|their|a|an)?\\s*"\n'
     '               r"(?:design|model|part|file)s?\\b", re.IGNORECASE),\n',
     '',
     "KIRMIZI", "[A8-ACIKLAMA-USED-THIS-DESIGN]"),

    # AK-05: "0 VURUS = TEMIZ" YASAGI. Once aciklama alanlarinin HICBIRINDE dolu metin
    # yoksa kayit ALAN-YOK rc=0 ile "temiz" sayiliyordu (olculmedi sessizce yesile donuyordu).
    ("AK-05 'hepsi bos' kontrolu kaldir",
     '    if bos_aciklama_kurali and not dolu_metin:\n'
     '        okunamaz.append("aciklama metni YOK (description/summary/... hepsi bos) — "\n'
     '                        "0 vurus temiz sayilmaz")',
     '    if False:\n        pass',
     "KIRMIZI", "[B2-ACIKLAMA-YOK]"),

    # AK-07: Printables `thingiverseLink` yapisal ata ekseni (BaBa 23 Eki 23:4x).
    ("AK-07 thingiverseLink ata alanindan cikar",
     '                "thingiverseLink")',
     '                )',
     "KIRMIZI", "[TL1-THINGIVERSELINK]"),

    # AK-08/AK-09: Printables `remixParents` yapisal ata (BaBa 24 Eki tik 84).
    ("AK-08 remixParents sekli taninmaz (parentPrintId kolu kaldir)",
     '    if isinstance(el, dict) and ("parentPrintId" in el or "parentPrint" in el):',
     '    if False:',
     "KIRMIZI", "[RP1-PARENTPRINTID]"),
    ("AK-09 aciklama ekseninde semasiz yedek geri acilir (metin = ata linki)",
     '    if bulunan or yalniz_url:',
     '    if bulunan:',
     # RP1 bu kolu artik olcemez: host listesi (AK-15) sahte host'lu metni zaten dusurur.
     "KIRMIZI", "[PO8-SEMASIZ-MODEL-HOST]"),

    # AK-10/AK-11: uretim defteri ata_destegi (BaBa 24 Eki tik 87).
    ("AK-10 PR ata_destegi False'a doner (PR dilimi toplu taramada OLCULMEDI)",
     '            # alan sorgudan cikinca ikisi ALAN-YOK. Sekil olculmeden diger platformlar '
     'CEVRILMEZ.\n            ata_destegi=True),',
     '            ata_destegi=False),',
     "KIRMIZI", "[PD2-PR-KAPSAM]"),
    ("AK-11 TV ata_destegi olcumsuz True'ya cevrilir",
     '            satilabilir=genel_satilabilir,\n            ata_destegi=False),',
     '            satilabilir=genel_satilabilir,\n            ata_destegi=True),',
     "KIRMIZI", "[PD1-BAYRAK]"),

    # AK-12..AK-16: politika (BaBa 24 Eki tik 88 ③(a)(c) + ④).
    ("AK-12 tetik koku daraltilir ('based' -> yalniz 'based on')",
     '    re.compile(r"\\bbased\\b", re.IGNORECASE),',
     '    re.compile(r"\\bbased\\s+on\\b", re.IGNORECASE),',
     "KIRMIZI", "[PO1-BASED-KOK]"),
    ("AK-13 oz-ata yazar kontrolu kapali (ata lisansina duser)",
     '    oz = oz_aday and turev[0] == adaptor.ad and eser_yazari(detay) == turev[1]',
     '    oz = False',
     "KIRMIZI", "[PO2-OZ-ATA]"),
    ("AK-14 oz-ata ust zinciri yargilamadan doner",
     '                      ata, host, kimlik, lisans_metni or gomulu, adaptor.ad, derinlik)]\n'
     '    else:',
     '                      ata, host, kimlik, lisans_metni or gomulu, adaptor.ad, derinlik)]\n'
     '        return out\n'
     '    else:',
     "KIRMIZI", "[PO3-OZ-ATA-UST-NC]"),
    ("AK-15 ata adayi host listesi kaldirilir (dis host ELLE-BAK'a duser)",
     '                   if ata_adayi_url_mu(u, defter)]',
     '                   if host_coz(u)]',
     "KIRMIZI", "[PO5a-DIS-HOST-VIDEO]"),
    ("AK-17 yapisal NOTR ayiklamasi kaldirilir (forum linki ELLE-BAK'a duser)",
     '            atalar, notr_sayi = notr_ayikla(atalar, defter)',
     '            notr_sayi = 0',
     "KIRMIZI", "[PO9-YAPISAL-TVLINK-FORUM]"),
    ("AK-18 NOTR alan siniri kaldirilir (originals'ta bilinmeyen host da NOTR olur)",
     '        if (r.get("alan") in NOTR_ALANLARI and link and h and not r.get("license")',
     '        if (link and h and not r.get("license")',
     "KIRMIZI", "[S-FC-ADAPTORSUZ]"),
    ("AK-19 Printables model-disi URL siniflari (CDN + @profil) kapatilir",
     '    return ata_adayi_host_mu(host_coz(url), defter) and not model_disi_url_mu(url)',
     '    return ata_adayi_host_mu(host_coz(url), defter)',
     "KIRMIZI", "[PO11-PR-GORSEL-CDN]"),
    ("AK-16 printables.com/<N> kisa bicim kaldirilir",
     '                                    or _kimlik_kok_sayi(u)),',
     '                                    ),',
     "KIRMIZI", "[PO7-KISA-BICIM]"),
    ("AK-20 prusaprinters.org (eski alan adi) pr host'larindan cikar",
     '            ad="pr", hostlar=("printables.com", "prusaprinters.org"),',
     '            ad="pr", hostlar=("printables.com",),',
     "KIRMIZI", "[PO13-PR-ESKI-ALAN]"),
    ("AK-21 prints/<N> kimlik isaretcisi kaldirilir",
     '(_kimlik_bas_sayi(u, "model") or _kimlik_bas_sayi(u, "prints")',
     '(_kimlik_bas_sayi(u, "model")',
     "KIRMIZI", "[PO13-PR-ESKI-ALAN]"),
    ("AK-22 oz-atif tohumu kaldirilir (turev kendi kimligini ata sayar)",
     '                    gorulen.update((h, kendi) for h in kaynak_adaptor.hostlar)',
     '                    pass',
     "KIRMIZI", "[PO14-OZ-ATIF-TOHUM]"),

    # ---------------- eksen: HOST cozumlemesi (kapinin yeni ekseni) ----------------
    ("OLD-01 host korlugu",
     '            if host == h or host.endswith("." + h):',
     '            if True:',
     "KIRMIZI", "[S-AYIRT-HOST]"),
    ("OLD-02 yargi tersine",
     '    if not satilabilir_ile(lisans_metni, adaptor.satilabilir):',
     '    if satilabilir_ile(lisans_metni, adaptor.satilabilir):',
     "KIRMIZI", "[S-POZ-NCSA]"),

    # ---------------- CANLI KIPI: host secimi (23 Eki 2026) ----------------
    # 🔴 ONCUL OLCUM: (a) printables-api.detail(N) ağdan model detayı döndürüyor ve
    # description/summary alanlarından en az birini içeriyor (1569795 -> description 580
    # karakter, summary 55); (b) MaCiT PR kayıtlarının `link` alanı `printables.com/model/<N>`
    # biçiminde. İKİSİ DE DOĞRU -> Printables PR->PR ata zinciri kapiya girebilir.
    # Bu mutant: `--canli` host secimini thingiverse'e SABITLER (pr adaptörü secilemez).
    # Beklenen: P1 (printables URL -> pr adaptörü + kimlik) KIRMIZI.
    ("CANLI-01 canli host secimi thingiverse'e sabitlenir",
     '    adaptor = adaptor_bul(host, defter)\n'
     '    if adaptor is None:\n'
     '        raise KaliciHata("bu host icin adaptor YOK (verilen: %s)" % host)',
     '    adaptor = adaptor_bul("thingiverse.com", defter)\n'
     '    if adaptor is None:\n'
     '        raise KaliciHata("bu host icin adaptor YOK (verilen: %s)" % host)',
     "KIRMIZI", "[P1-PR-HOST]"),

    # TSV'de stdout SADEce TSV olmalidir: `kuru_kosum`'un kapsam ilerleme satiri (rapor
    # metni) makine ciktisini bozardi -> ayristirici ilk satirdan kirilir.
    ("TSV-01 --kuru-kosum --tsv kapsam satiri stdout'a karisir",
     '                a.limit, a.kaynak, yaz=(lambda _s: None) if a.tsv else None)',
     '                a.limit, a.kaynak, yaz=None)',
     "KIRMIZI", "[T1c-TSV-KURU]"),

    # ---------------- D1: turev detayi None -> sessiz "ata yok" ----------------
    ("OLD-03 (D1) turev detayi None sessiz gecer",
     '        out = [_sonuc(DURUM_KALICI, "turev detayi YOK (API null / kayit silinmis-gizli)")]',
     '        out = [_sonuc(DURUM_ALAN_YOK, "turev detayi YOK -> ata yok sayildi")]',
     "KIRMIZI", "[D1]"),

    # ---------------- D2: ata alan adlari ----------------
    ("OLD-04 (D2) ata alan listesi TEK ada iner",
     'ATA_ALANLARI = ("originals", "remixParents", "derivedFrom", "ancestors",\n'
     '                "originalDesigns", "remixOf",\n',
     'ATA_ALANLARI = ("originals",\n',
     "KIRMIZI", "[D2a]"),

    # ---------------- D3: sekil varyasyonlari ----------------
    ("OLD-05 (D3a) dict/string ata sekli atlanir",
     '        elif isinstance(ham, (dict, str)):\n'
     '            elemanlar = [ham]                           # tekil sekil de COZULUR, atlanmaz',
     '        elif isinstance(ham, (dict, str)):\n'
     '            continue',
     "KIRMIZI", "[D3a]"),
    ("OLD-06 (D3c) taninmayan ata sekli sessiz gecer",
     "            hatalar.append(\"ata alani '%s' TANINMAYAN sekilde (%s)\" "
     "% (alan, type(ham).__name__))",
     '            pass',
     "KIRMIZI", "[D3c]"),
    ("OLD-07 (D3d) zarf acilmaz",
     '        icler = [d[k] for k in d if _ad(k) in _ZARF_N and isinstance(d[k], dict)]',
     '        icler = []',
     "KIRMIZI", "[D3d]"),
    ("OLD-08 (D3e) BOS turev detayi 'ata yok' sayilir",
     '        elif not isinstance(acik, dict) or not acik:\n'
     '            out = [_sonuc(DURUM_KALICI, "turev detayi BOS (zarf acildiktan sonra da)")]',
     '        elif False:\n'
     '            out = [_sonuc(DURUM_KALICI, "turev detayi BOS (zarf acildiktan sonra da)")]',
     "KIRMIZI", "[D3e]"),

    # ---------------- D4: tek alanda coklu URL ----------------
    ("OLD-09 (D4) yalniz ILK ata URL'sine bakilir",
     '    return [{"link": u, "license": lis, "kimlik_alani": kim, "alan": alan} for u in urller]',
     '    return [{"link": urller[0], "license": lis, "kimlik_alani": kim, "alan": alan}]',
     "KIRMIZI", "[D4]"),

    # ---------------- D5: zincir ----------------
    ("OLD-10 (D5a) zincir ozyinelemesi kapali",
     '        for ust in ustler:\n'
     '            out.extend(ata_yargi(ust, defter, gs, adaptor, derinlik + 1, gorulen, turev))',
     '        for ust in ustler:\n'
     '            pass',
     "KIRMIZI", "[D5a]"),
    ("OLD-11 (D5b) derinlik tavani fail-OPEN",
     '        if derinlik >= DERINLIK_TAVANI:',
     '        if False:',
     "KIRMIZI", "[D5b]"),

    # ---------------- D6: gomulu lisans sozlugu ----------------
    ("OLD-12 (D6) gomulu lisans TEK sozlukle yargilanir",
     '    gomulu_veto = bool(gomulu) and not coklu_sozluk_satilabilir(gomulu, kaynak_adaptor)',
     '    gomulu_veto = bool(gomulu) and not genel_satilabilir(gomulu)',
     "KIRMIZI", "[D6-gomulu-yp]"),
    # VETO'nun KENDI BASINA olculebilmesi icin ayirt edici fikstur gerekir: alt sozluklerin
    # HICBIRININ yakalamadigi ama ticari kullanimi kapatan serbest-metin yazimlar
    # ("... not for commercial use", "... Premium License"). Onlar olmadan bu mutant
    # yasardi = beyan edilmis survivor.
    ("OLD-13 NC/tescilli VETOSU tamamen kaldirilir",
     '    if not isinstance(ham, str):\n        return True',
     '    if True:\n        return False\n    if not isinstance(ham, str):\n        return True',
     "KIRMIZI", "[yanlis-negatif]"),
    # V1: "exclusive" ONEK MUAFIYETI. Duz alt-dize aramasina donunce TAM METIN CC lisanslari
    # ("... royalty-free, non-exclusive ...") veto yer = yanlis-pozitif; yayin durur.
    ("OLD-21 (V1) 'exclusive' yeniden DUZ ALT-DIZE arar",
     '_TESCILLI_DESEN = (re.compile(r"(?<!non)(?<!non[ -])\\bexclusive\\b"),)',
     '_TESCILLI_DESEN = (re.compile(r"exclusive"),)',
     "KIRMIZI", "[veto-tam-metin]"),
    ("OLD-29 (V1) 'non'+'commercial' yan yana sarti KUME uyeligine doner",
     '    if any(a == "non" and b == "commercial" for a, b in zip(toks, toks[1:])):',
     '    if "non" in toks and "commercial" in toks:',
     "KIRMIZI", "[veto-tam-metin]"),
    ("OLD-30 (V1) 'non'+'commercial' jeton kurali tamamen kalkar",
     '    if any(a == "non" and b == "commercial" for a, b in zip(toks, toks[1:])):\n'
     '        return True\n'
     '    return False',
     '    return False',
     "KIRMIZI", "[yanlis-negatif]"),

    # ---------------- D7 / D12: hata siniflandirmasi ----------------
    ("OLD-14 (D7) timeout KALICI kovasina duser",
     '    except (socket.timeout, TimeoutError):\n'
     '        raise GeciciHata("okuma timeout")\n'
     '    except ValueError:',
     '    except (socket.timeout, TimeoutError):\n'
     '        raise KaliciHata("okuma timeout")\n'
     '    except ValueError:',
     "KIRMIZI", "[D7]"),
    ("OLD-15 (D12) bozuk JSON GECICI sayilir",
     '        raise KaliciHata("bozuk JSON / gecersiz deger")',
     '        raise GeciciHata("bozuk JSON / gecersiz deger")',
     "KIRMIZI", "[D12]"),

    # ---------------- D8: kapsam ayrimi ----------------
    ("OLD-16 (D8) kapsam kovalari birlestirilir",
     '        elif not ad.ata_destegi:\n            olculmedi_adaptorlu.append(urun_id)',
     '        elif not ad.ata_destegi:\n            olculmedi_adaptorsuz.append(urun_id)',
     "KIRMIZI", "[D8-kapsam]"),
    ("OLD-17 (D8) OLCULMEMIS kapsam rc'yi 2'ye cekmez",
     '    if kapsam and (kapsam.get("olculmedi_adaptorlu") or kapsam.get("olculmedi_adaptorsuz")\n'
     '                   or kapsam.get("taranmadi")):\n        return 2',
     '    if False:\n        return 2',
     "KIRMIZI", "[D8-rc]"),

    # ---------------- D9: izlenebilirlik ----------------
    ("OLD-18 (D9) sonuclarda urun kimligi set edilmez",
     '    for s in out:\n'
     '        s["urun"] = urun_id                     # her sonuc IZLENEBILIR olmali (ALAN-YOK dahil)',
     '    for s in out:\n'
     '        s.setdefault("urun", None)',
     "KIRMIZI", "[D9]"),

    # ---------------- D11: ust kademe sekil hatasi ----------------
    ("OLD-19 (D11b) ust kademe sekil hatasi yutulur",
     '        for h in sekil_hatalari:\n'
     '            out.append(_sonuc(DURUM_KALICI, "ust kademe: " + h, ata, host, kimlik, None,',
     '        for h in []:\n'
     '            out.append(_sonuc(DURUM_KALICI, "ust kademe: " + h, ata, host, kimlik, None,',
     "KIRMIZI", "[D11b]"),

    # ---------------- kimlik cikarimi: API bicimi (canli kuru kosumda olculdu) ----------------
    ("OLD-20 kimlik cikariminda API bicimi taninmaz",
     '        if parca.lower() in ("things", "thing") and i + 1 < len(parcalar):',
     '        if False:',
     "KIRMIZI", "[kendini-test]"),

    # ------- IKINCI TUR: "ALAN-YOK" IDDIASININ KANITI (D13..D18) — her eksen AYRI -------
    ("OLD-22 (D13) zarf tavani 4 kademeyi acamayacak kadar dar",
     'ZARF_TAVANI = 6',
     'ZARF_TAVANI = 3',
     "KIRMIZI", "[D13]"),
    ("OLD-23 (D13b) zarf TAVANI asilinca fail-OPEN",
     '        if n >= tavan:\n'
     '            return d, ("detay zarfi %d kademeden derin (tavan %d) — govde ACILAMADI"\n'
     '                       % (n + 1, tavan)), govde_gorundu',
     '        if n >= tavan:\n'
     '            return d, None, govde_gorundu',
     "KIRMIZI", "[D13b-tavan]"),
    ("OLD-24 (D13c) govde isareti inisi DURDURUR (zarf ici ata gorunmez olur)",
     '        if ata_anahtarlari(d):\n'
     '            return d, None, True                  # ata alani BULUNDU: iz aramaya gerek yok',
     '        if ata_anahtarlari(d) or _govde_mi(d):\n'
     '            return d, None, True',
     "KIRMIZI", "[D13c]"),
    ("OLD-25 (D14) BELIRSIZ zarf fail-OPEN (disaridaki sozluk donuyor)",
     '        if len(icler) > 1:\n'
     '            return d, ("detay zarfi BELIRSIZ: ayni duzeyde %d ic sozluk — govde OLCULMEDI"\n'
     '                       % len(icler)), govde_gorundu',
     '        if len(icler) > 1:\n'
     '            return d, None, govde_gorundu',
     "KIRMIZI", "[D14-belirsiz]"),
    ("OLD-26 (D15/16/17) ata alani TAM ESLESME ile aranir (yazim varyanti korlugu)",
     '    varlar = [k for k in d if _ad(k) in _ATA_N]',
     '    varlar = [k for k in d if k in ATA_ALANLARI]',
     "KIRMIZI", "[D16]"),
    ("OLD-27 (D18) ALAN-YOK yeniden VARSAYILIR (govde izi aranmaz)",
     '                if govde_gorundu:',
     '                if True:',
     "KIRMIZI", "[D18]"),
    ("OLD-28 (D18) govde izi HER sekilde True (tanima olcusuz)",
     '    return isinstance(d, dict) and any(_ad(k) in _GOVDE_N for k in d)',
     '    return isinstance(d, dict)',
     "KIRMIZI", "[D18-govde-izi]"),

    # ---------------- KONTROL (yanlis-pozitif olmadigi kaniti) ----------------
    ("KONTROL-1 ilgisiz davranis (kuru kosum tavani)",
     'ap.add_argument("--limit", type=int, default=40,',
     'ap.add_argument("--limit", type=int, default=41,',
     "YESIL", None),
    ("KONTROL-2 ilgisiz metin (rapor basligi)",
     'yaz("ATA-LISANS KAPISI — RAPOR KIPI (veri YAZILMAZ, silme UYGULANMAZ)")',
     'yaz("ATA-LISANS KAPISI — rapor (kontrol mutanti)")',
     "YESIL", None),
    ("KONTROL-3 ilgisiz sabit (zarf anahtar kumesi genisler)",
     'ZARF_ANAHTARLARI = ("data", "result", "response", "payload", "design", "model")',
     'ZARF_ANAHTARLARI = ("data", "result", "response", "payload", "design", "model", "zarf")',
     "YESIL", None),
]


def _agac_kur(tmp):
    """Gecici KOPYA agaci: tools/ + kapinin 'yazmaz' iddiasini olcebilmesi icin
    veri kokunde iki taklit dosya (icerikleri onemsiz; olculen sey DEGISMEMELERI)."""
    hedef_tools = os.path.join(tmp, "tools")
    shutil.copytree(_HERE, hedef_tools)
    _pycache_temizle(hedef_tools)
    with open(os.path.join(tmp, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([{"id": "uydurma", "baslik": "uydurma"}], f)
    with open(os.path.join(tmp, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
        json.dump({"uydurma": {"kaynak": "uydurma", "link": ""}}, f)
    return hedef_tools


def _pycache_temizle(kok):
    """🔴 OLCULEN TUZAK: bytecode onbellegi kaynagi (boyut + saniye cozunurluklu mtime) ile
    dogrular. AYNI UZUNLUKTA bir mutasyon ("KaliciHata"->"GeciciHata") ayni saniye icinde
    yazilirsa onbellek GECERLI sanilir ve MUTASYON UYGULANMAZ — bir onceki mutantin kodu
    kosar, kirmizi yanar ama YANLIS iddia duser. Bu surucude tam olarak bu olctu (OLD-14/15).
    Cozum: kopyada __pycache__ YOK + alt sureclerde bytecode yazimi KAPALI."""
    for dizin, altlar, _dosyalar in os.walk(kok):
        for alt in list(altlar):
            if alt == "__pycache__":
                shutil.rmtree(os.path.join(dizin, alt), ignore_errors=True)
                altlar.remove(alt)


def _kos(tools_dizin):
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"       # bkz _pycache_temizle
    r = subprocess.run([sys.executable, "-B", os.path.join(tools_dizin, TEST_ADI)],
                       capture_output=True, text=True, env=ortam)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    hatalar = []
    with tempfile.TemporaryDirectory() as tmp:
        tools_dizin = _agac_kur(tmp)
        kapi_yol = os.path.join(tools_dizin, KAPI_ADI)
        with open(kapi_yol, encoding="utf-8") as f:
            temiz_kaynak = f.read()

        # 0) TABAN: mutasyonsuz kopya YESIL + SESSIZ_GECIS=0 olmali
        rc, cikti = _kos(tools_dizin)
        if rc != 0 or "SESSIZ_GECIS=0" not in cikti:
            print("TABAN KIRMIZI — mutasyonsuz kopya gecmedi (rc=%d)" % rc)
            print(cikti[-3000:])
            return 2
        print("  ok   TABAN (mutasyonsuz kopya) YESIL · SESSIZ_GECIS=0")

        for ad, aranan, yerine, beklenen, kanit in MUTANTLAR:
            adet = temiz_kaynak.count(aranan)
            if adet != 1:
                hatalar.append("%s: capa %d kez gecti (1 olmali) — surucu BAYAT" % (ad, adet))
                print("  HATA %-52s capa sayisi=%d" % (ad, adet))
                continue
            with open(kapi_yol, "w", encoding="utf-8") as f:
                f.write(temiz_kaynak.replace(aranan, yerine))
            rc, cikti = _kos(tools_dizin)
            olculen = "YESIL" if rc == 0 else "KIRMIZI"
            coktu = ("Traceback" in cikti and "BASARISIZ" not in cikti)
            dokum = cikti.split("BASARISIZ", 1)[1] if "BASARISIZ" in cikti else ""
            kanit_ok = True if not kanit else (kanit in dokum)
            ok = (olculen == beklenen) and not coktu and kanit_ok
            if not ok:
                hatalar.append("%s: beklenen %s, olculen %s%s%s"
                               % (ad, beklenen, olculen, " (COKTU)" if coktu else "",
                                  "" if kanit_ok else " (dusen iddia %r DEGIL)" % kanit))
            print("  %-4s %-52s beklenen=%-7s olculen=%-7s%s%s"
                  % ("ok" if ok else "HATA", ad, beklenen, olculen,
                     " COKTU" if coktu else "", "" if kanit_ok else " KANIT-YOK"))
            with open(kapi_yol, "w", encoding="utf-8") as f:
                f.write(temiz_kaynak)

    oldurucu = sum(1 for m in MUTANTLAR if m[3] == "KIRMIZI")
    kontrol = len(MUTANTLAR) - oldurucu
    print("")
    if hatalar:
        print("MUTASYON BATARYASI BASARISIZ — %d/%d mutant beklenen isareti VERMEDI:"
              % (len(hatalar), len(MUTANTLAR)))
        for h in hatalar:
            print("  x %s" % h)
        return 1
    print("MUTASYON BATARYASI GECTI — oldurucu %d/%d KIRMIZI, kontrol %d/%d YESIL."
          % (oldurucu, oldurucu, kontrol, kontrol))
    return 0


if __name__ == "__main__":
    sys.exit(main())

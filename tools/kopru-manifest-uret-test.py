#!/usr/bin/env python3
"""KABUL: tools/kopru-manifest-uret.py (kopru-15 DILIM-2) — TeKiN kayit -> manifest satiri sozlugu.

IKI KATMAN
  F (HERMETIK, CI'da kosar): sahte kayit + sahte manifest gecici dizinde. Sozluk vakalari (olcu->form,
     tam->adim 1, sayi->adim 0.01, enlem->0.000001, renk->bolge, dosya->form disi, kosul AYNEN, teklif),
     --yaz idempotent (2. kosum degisen=0, bayt ayni), --denetle YESIL; mutantlar KIRMIZI yakmali.
  R (GERCEK, HERMETIK — sinif-r-k80 9 Eki): repodaki SABIT kayit (jenerator/kopru/, TeKiN kaydinin sha-sabit
     kopyasi + uretec SEMA'lari + KAYNAK_SHA) + bu agacin manifesti --denetle YESIL, --yaz kopyada degisen=0;
     mutantlar gercek kopyalarda KIRMIZI. CI'da da KOSAR: `ATLANDI` YOK — kayit yoksa R0 KIRMIZI; R0b: env
     verilmemisken kayit yolu repo DISINA (makine yolu) donerse KIRMIZI. `KOPRU_KAYIT` env yalniz elle
     karsilastirma. Bilgi satiri `KAYIT_BAYAT=<n>|OLCULEMEDI` (bloklamaz): sabit sha TeKiN main gerisinde mi.
MUTANTLAR (gecici kopyalarda; calisma agacina YAZMAZ):
  MK1 kayitta bool->boolean · MK2 manifestte tek alanin kosul'u silindi · MK3 adim dusuruldu (0.01->0.001)
  MK4 kayitta bilinmeyen girdi · MK5 kosul var olmayan alana bakiyor · MK0 kontrol: editoryal metin degisti
  MK6 manifestte form `ornek` silindi · RENK EKSENI (8 Eki): MK7 manifest renk_tavani > boyanabilir sayi · MK8 kopru
  govde adi parametre sonekinden sapti · MK9 renk_ parametresi silindi (tavan iner); F15 parametresiz govde = BILGI.
  K3c SOZLUK (F16-F21, hermetik): renk_liste -> palet (renk_secimi/palet_bolgeleri/renk_tavani) + bozuk bicim
  KIRMIZI · metin liste -> {liste, satir_max, max:karakter_max} + bozuk bicim KIRMIZI · sema_adi uste yazimi.
  R katmani (K3c: gercek kayit = yapboz + anahtarlik; silinen sehir/yildiz/kosul capali MR'ler bu iki kayda
  tasindi): MR1 renk_liste -> bilinmeyen tip · MR2 palet tavani 4->3 · MR3 adim dusuruldu · MR4 anahtarlik
  satirlar max silindi · MR5 liste:true silindi · MR6 kayitta satir_max silindi · MR7 renk_liste oge bozuk ·
  MR8 yapboz renk_secimi silindi · MR9 sema_adi dosyada yok · MR0 kontrol: anahtarlik durustluk metni degisti.
Cikti son satiri: VAKA_KIRMIZI=<n> SURVIVOR=<n>   (rc 0 yalniz ikisi de 0)
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "kopru-manifest-uret.py")
SABIT_KAYIT = os.path.join(KOK, "jenerator", "kopru", "kopru_kayitlari.json")
GERCEK_KAYIT = os.environ.get("KOPRU_KAYIT") or SABIT_KAYIT

sonuc = {}


def vaka(ad, gecti, ac=""):
    sonuc[ad] = bool(gecti)
    print(("✅ " if gecti else "❌ ") + ad + (" — " + ac if ac else ""))


def arac_yukle():
    spec = importlib.util.spec_from_file_location("kopru_manifest_uret", ARAC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def kos(*arg):
    p = subprocess.run([sys.executable, ARAC] + list(arg), capture_output=True, text=True)
    return p.returncode, p.stdout


SAHTE_KAYIT = {"surum": "test", "kayitlar": [
    {"kod": "parca", "uretec": "ozel_uret:parca", "girdi_tipi": ["olcu"],
     "parametreler": [
         {"ad": "mod", "etiket": "Mod", "tip": "secim", "secenekler": ["a", "b"], "varsayilan": "a"},
         {"ad": "adet", "etiket": "Adet", "tip": "sayi", "min": 1, "max": 8, "varsayilan": 2, "birim": "adet",
          "tam": True},
         {"ad": "duvar_mm", "etiket": "Duvar", "tip": "sayi", "min": 1.2, "max": 4, "varsayilan": 1.6, "birim": "mm"},
         {"ad": "kapak", "etiket": "Kapak", "tip": "bool", "varsayilan": False,
          "kosul": [{"alan": "mod", "degerler": ["b"]}]}],
     "olcek": {"min_mm": 10, "max_mm": 200, "adim_mm": 10}, "izinli_malzeme": ["PLA"], "renk_bolgeleri": []},
    {"kod": "harita", "uretec": "harita_uret", "girdi_tipi": ["konum"],
     "parametreler": [
         {"ad": "enlem", "etiket": "Enlem", "tip": "sayi", "min": -90, "max": 90, "zorunlu": True},
         {"ad": "hane", "etiket": "Hane", "tip": "tam", "min": 2, "max": 6, "varsayilan": 4},
         {"ad": "gorsel", "etiket": "Gorsel", "tip": "dosya", "zorunlu": True},
         {"ad": "renk_plaka", "etiket": "Plaka rengi", "tip": "renk", "varsayilan": "#000000"},
         {"ad": "renk_yazi", "etiket": "Yazi rengi", "tip": "renk"}],
     "olcek": {"min_mm": 60, "max_mm": 250, "adim_mm": 5}, "izinli_malzeme": ["PLA", "PETG"],
     "ornek": {"girdi": {"enlem": 41.0256, "hane": "<yer tutucu>", "renk_plaka": "#FFFFFF"}},
     # Kopru govde listesi: "cerceve"nin renk_ parametresi YOK -> BILGI boyanamaz-bolge (KIRMIZI degil).
     "renk_bolgeleri": ["plaka", "yazi", "cerceve"]},
    {"kod": "rolyef", "uretec": "rolyef_uret", "girdi_tipi": ["foto"],
     "parametreler": [
         {"ad": "uzun_kenar_mm", "etiket": "Uzun kenar", "tip": "sayi", "min": 60, "max": 250, "varsayilan": 120,
          "birim": "mm"},
         {"ad": "ters", "etiket": "Ters", "tip": "bool", "varsayilan": False}],
     "olcek": {"min_mm": 60, "max_mm": 250, "adim_mm": 10}, "izinli_malzeme": ["PLA"],
     "tur_tanimi_teklifi": {"ad": "Bust", "girdi": "foto",
                            "alanlar": [{"ad": "uzun_kenar_mm", "etiket": "Boyut", "max": 200},
                                        {"ad": "ters", "etiket": "Ters (negatif)"}]}}]}

RENK = ('"Beyaz": "#F2F2F2", "Siyah": "#1A1A1A", "Gri": "#818184", "Lacivert": "#12294D", "Kırmızı": "#B3262E", '
        '"Sarı": "#E8B923", "Yeşil": "#2E7D4F", "Mavi": "#2E5E8C", "Ahşap": "#C8B89A"')


# Renk tavani = boyanabilir renk_* sayisi (en az 1): harita 2 (plaka, yazi); bust ANA kayittan (rolyef 1).
SAHTE_TAVAN = {"parca": 1, "harita": 2, "rolyef": 1, "bust": 1}


def sahte_manifest():
    satir = []
    for kod in ("parca", "harita", "rolyef", "bust"):
        satir.append('      {\n        kod: "%s",\n        ad: "Sahte %s",\n        motor: "D",\n'
                     '        fiyat: { formul: "mm_x_10tl", adim_mm: 1, renk_tavani: %d },\n'
                     '        durustluk: "Sahte metin."\n      }' % (kod, kod, SAHTE_TAVAN[kod]))
    return ("(function (kok) {\n  var VERI = {\n    turler: [\n" + ",\n".join(satir) + "\n    ],\n"
            "    RENK_HEX: { " + RENK + " }\n  };\n  kok.PRUVO_FOTO = VERI;\n"
            "})(typeof globalThis !== \"undefined\" ? globalThis : this);\n")


def degistir(yol, eski, yeni, regex=False):
    s = open(yol, encoding="utf-8").read()
    n = len(re.findall(eski, s, re.M)) if regex else s.count(eski)
    if n < 1:
        raise AssertionError("capa yok: %r" % eski)
    s = re.sub(eski, yeni, s, count=1, flags=re.M) if regex else s.replace(eski, yeni, 1)
    open(yol, "w", encoding="utf-8").write(s)


def mutant(ad, kayit, manifest, beklenen_kalip, hazirla):
    """Kopyalar uzerinde mutasyon -> --denetle rc 1 VE KIRMIZI satiri kalibi tasimali (kontrol: rc 0)."""
    d = tempfile.mkdtemp(prefix="kopru-uret-mutant-")
    try:
        k, m = os.path.join(d, "k.json"), os.path.join(d, "m.js")
        shutil.copyfile(kayit, k)
        shutil.copyfile(manifest, m)
        hazirla(k, m)
        rc, out = kos("--denetle", "--kayit", k, "--manifest", m)
        if beklenen_kalip is None:
            vaka(ad, rc == 0 and "DENETLE=YESIL" in out, out.strip().splitlines()[-1] if out.strip() else "")
        else:
            kir = [s for s in out.splitlines() if s.startswith("KIRMIZI ")]
            vaka(ad, rc == 1 and any(re.search(beklenen_kalip, s) for s in kir),
                 "rc=%d %s" % (rc, " | ".join(kir[:3])))
    except AssertionError as e:
        vaka(ad, False, str(e))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def hermetik():
    print("F) HERMETIK FIKSTUR")
    u = arac_yukle()
    satirlar, hatalar = u.hepsini_uret(SAHTE_KAYIT)
    p, h = satirlar["parca"], satirlar["harita"]
    vaka("F1 girdi olcu->form · konum aynen · foto->foto-1",
         p["girdi"] == ["form"] and h["girdi"] == ["konum"] and satirlar["bust"]["girdi"] == ["foto-1"] and not hatalar,
         "%s %s %s" % (p["girdi"], h["girdi"], hatalar))
    vaka("F2 tam:true -> sayi adim 1 (tam bayragi duser)",
         p["form"]["adet"] == {"tip": "sayi", "etiket": "Adet", "min": 1, "max": 8, "adim": 1, "varsayilan": 2,
                               "birim": "adet"}, json.dumps(p["form"]["adet"]))
    vaka("F3 sayi -> adim 0.01 (max'tan hemen sonra)",
         list(p["form"]["duvar_mm"]) == ["tip", "etiket", "min", "max", "adim", "varsayilan", "birim"] and
         p["form"]["duvar_mm"]["adim"] == 0.01, json.dumps(p["form"]["duvar_mm"]))
    vaka("F4 kosul AYNEN form alaninda",
         p["form"]["kapak"].get("kosul") == [{"alan": "mod", "degerler": ["b"]}], json.dumps(p["form"]["kapak"]))
    vaka("F5 enlem adim 0.000001 · tip tam -> sayi adim 1 · dosya form disi",
         h["form"]["enlem"]["adim"] == 0.000001 and h["form"]["hane"]["tip"] == "sayi" and
         h["form"]["hane"]["adim"] == 1 and "gorsel" not in h["form"], json.dumps(h["form"]))
    vaka("F6 renk -> bolge (cift acik-once, tek koyu-once; ad ' rengi'siz) · form disi",
         [(b["kod"], b["ad"], b["renkler"][0]) for b in h["renk_bolgeleri"]] == [("plaka", "Plaka", "Beyaz"),
                                                                              ("yazi", "Yazi", "Siyah")] and
         not any(k.startswith("renk_") for k in h["form"]), json.dumps(h["renk_bolgeleri"])[:200])
    vaka("F7 olcek -> olcu_mm + fiyat adim · izinli_malzeme -> govde",
         h["olcu_mm"] == {"en_az": 60, "en_cok": 250} and h["fiyat_adim_mm"] == 5 and
         h["malzemeler"] == {"govde": ["PLA", "PETG"]})
    b = satirlar["bust"]["form"]
    vaka("F8 teklif turu (bust): ana parametre + teklif alani ustune, ayni sozluk",
         b["uzun_kenar_mm"]["etiket"] == "Boyut" and b["uzun_kenar_mm"]["max"] == 200 and
         b["uzun_kenar_mm"]["adim"] == 0.01 and b["ters"] == {"tip": "bool", "etiket": "Ters (negatif)",
                                                               "varsayilan": False}, json.dumps(b))
    # kopru-15 SON3: kayit `ornek.girdi` -> form alani `ornek` (yer tutucu `<...>` tasinmaz, renk form disi,
    # ornegi olmayan kaydin alaninda `ornek` anahtari YOK).
    vaka("F17 ornek.girdi -> form ornek (yer tutucu/renk tasinmaz; orneksiz kayit etkilenmez)",
         h["form"]["enlem"].get("ornek") == 41.0256 and "ornek" not in h["form"]["hane"] and
         not any("ornek" in a for a in p["form"].values()), json.dumps(h["form"]))
    vaka("F9 deterministik: iki uretim BIREBIR", json.dumps(u.hepsini_uret(SAHTE_KAYIT), sort_keys=True) ==
         json.dumps(u.hepsini_uret(json.loads(json.dumps(SAHTE_KAYIT))), sort_keys=True))
    # kopru-15 ESLE: metin -> max (kayit > uretec SEMA) + zorunlu:false (zorunlu:true degilse). max'siz metin
    # VERI.parametreDogrula'da HER degerde `parametre-metin` (braille ⑤ 400).
    hm = []
    sema = {"ad": {"tip": "str", "uzunluk_max": 40}, "notlar": {"tip": "liste", "oge": {"tip": "str", "uzunluk_max": 12}},
            "uzun": {"tip": "str"}}
    a1, _ = u._alan_uret("t", [], {"ad": "ad", "tip": "metin", "varsayilan": ""}, hm, sema)
    a2, _ = u._alan_uret("t", [], {"ad": "notlar", "tip": "metin", "zorunlu": True}, hm, sema)
    a3, _ = u._alan_uret("t", [], {"ad": "uzun", "tip": "metin", "max": 7}, hm, sema)
    a4, _ = u._alan_uret("t", [], {"ad": "uzun", "tip": "metin", "zorunlu": True}, hm, sema)
    vaka("F14 metin max uretec SEMA'sindan (str uzunluk_max · liste oge · yoksa 1000) · kayit max ONCELIKLI · "
         "zorunlu:true degilse zorunlu:false",
         a1 == {"tip": "metin", "varsayilan": "", "max": 40, "zorunlu": False} and
         a2 == {"tip": "metin", "zorunlu": True, "max": 12} and
         a3 == {"tip": "metin", "max": 7, "zorunlu": False} and a4["max"] == 1000 and not hm,
         json.dumps([a1, a2, a3, a4, hm]))
    hm = []
    u._alan_uret("t", [], {"ad": "yok", "tip": "metin"}, hm, sema)
    u._alan_uret("t", [], {"ad": "ad", "tip": "metin"}, hm, None)
    vaka("F15 metin tavani turetilemiyor (uretec alani/SEMA yok) -> KIRMIZI metin-tavani-yok",
         hm == ["metin-tavani-yok:t.yok", "metin-tavani-yok:t.ad"], json.dumps(hm))
    dj = tempfile.mkdtemp(prefix="kopru-uret-sema-")
    try:
        os.makedirs(os.path.join(dj, "g"))
        with open(os.path.join(dj, "g", "x_uret.py"), "w", encoding="utf-8") as f:
            f.write('MAX = 9\nSEMA = {\n    "a": {"tip": "str", "uzunluk_max": 12},\n'
                    '    "b": {"tip": "float", "min": 0.0, "max": float(MAX)},\n}\n')
        sm = u.uretec_semasi(dj, "g/x_uret.py")
        vaka("F16 uretec_semasi: ast ile literal alanlar (literal olmayan max atlanir) · dosya yok -> None",
             sm == {"a": {"tip": "str", "uzunluk_max": 12}, "b": {"tip": "float", "min": 0.0}} and
             u.uretec_semasi(dj, "g/yok.py") is None, json.dumps(sm))
    finally:
        shutil.rmtree(dj, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="kopru-uret-test-")
    try:
        k, m = os.path.join(d, "k.json"), os.path.join(d, "m.js")
        json.dump(SAHTE_KAYIT, open(k, "w", encoding="utf-8"), ensure_ascii=False)
        open(m, "w", encoding="utf-8").write(sahte_manifest())
        rc0, out0 = kos("--denetle", "--kayit", k, "--manifest", m)
        vaka("F10 turetilmemis manifest -> --denetle KIRMIZI", rc0 == 1, out0.strip().splitlines()[-1])
        rc1, out1 = kos("--yaz", "--kayit", k, "--manifest", m)
        bayt1 = open(m, "rb").read()
        rc2, out2 = kos("--yaz", "--kayit", k, "--manifest", m)
        vaka("F11 --yaz idempotent (1. degisen=4, 2. degisen=0, bayt ayni)",
             rc1 == 0 and "degisen=4" in out1 and rc2 == 0 and "degisen=0" in out2 and open(m, "rb").read() == bayt1,
             "%s | %s" % (out1.strip(), out2.strip()))
        rc3, out3 = kos("--denetle", "--kayit", k, "--manifest", m)
        vaka("F12 --denetle YESIL", rc3 == 0 and "DENETLE=YESIL" in out3, out3.strip())
        vaka("F15 parametresiz kopru govdesi -> BILGI boyanamaz-bolge (KIRMIZI degil)",
             rc3 == 0 and "BILGI boyanamaz-bolge:harita.cerceve" in out3, out3.strip())
        rc4, out4 = kos("--denetle", "--kayit", os.path.join(d, "yok.json"), "--manifest", m)
        vaka("F13 kayit yok -> HAL=KAYIT-YOK rc 3 (sessiz YESIL degil)", rc4 == 3 and "HAL=KAYIT-YOK" in out4, out4)

        # ---- K3c SOZLUK: renk_liste (palet) + metin liste + sema_adi ----
        def tek(params, girdi=("foto",)):
            return u.satir_uret({"kod": "x", "uretec": "x_uret", "girdi_tipi": list(girdi), "parametreler": params,
                                 "olcek": {"min_mm": 10, "max_mm": 100, "adim_mm": 5, "belirleyen_parametre": "a"}})
        rl = {"ad": "renkler", "etiket": "Renkler", "tip": "renk_liste", "uzunluk_max": 3, "oge": "#RRGGBB",
              "varsayilan": ["#C8B89A"]}
        s16, h16 = tek([rl])
        vaka("F16 renk_liste -> palet: renk_secimi palet · palet_bolgeleri renk1..3 · tavan 3 · form/bolge DISI",
             not h16 and s16["renk_secimi"] == "palet" and s16["palet_bolgeleri"] == ["renk1", "renk2", "renk3"] and
             s16["renk_tavani"] == 3 and s16["form"] == {} and s16["renk_bolgeleri"] == [], json.dumps([s16, h16])[:300])
        bozuk = [("oge", dict(rl, oge="#RGB"), r"renk-liste-oge:x\.renkler"),
                 ("tavan 5", dict(rl, uzunluk_max=5), r"renk-liste-tavani:x\.renkler=5"),
                 ("tavan bool", dict(rl, uzunluk_max=True), r"renk-liste-tavani:x\.renkler=True"),
                 ("cift", [rl, dict(rl, ad="renkler2")], r"renk-liste-cift:x\.renkler2"),
                 ("bolge karisik", [rl, {"ad": "renk_taban", "etiket": "Taban rengi", "tip": "renk"}],
                  r"renk-liste-bolge-karisik:x")]
        for ad, prm, kalip in bozuk:
            _, hb = tek(prm if isinstance(prm, list) else [prm])
            vaka("F17 renk_liste %s -> KIRMIZI" % ad, any(re.search(kalip, x) for x in hb), json.dumps(hb))
        ml = {"ad": "satirlar", "etiket": "Yazi", "tip": "metin", "liste": True, "satir_max": 3, "karakter_max": 40,
              "zorunlu": True}
        s18, h18 = tek([ml], ("metin",))
        vaka("F18 metin liste -> {tip metin, etiket, liste, satir_max, max:karakter_max, zorunlu} · girdi metin",
             not h18 and s18["form"]["satirlar"] == {"tip": "metin", "etiket": "Yazi", "liste": True, "satir_max": 3,
                                                    "max": 40, "zorunlu": True} and s18["girdi"] == ["metin"] and
             s18["renk_secimi"] is None and s18["palet_bolgeleri"] is None, json.dumps([s18["form"], h18]))
        for ad, prm, kalip in [("satir_max yok", {k: v for k, v in ml.items() if k != "satir_max"},
                                r"metin-satir-max:x\.satirlar"),
                               ("satir_max 0", dict(ml, satir_max=0), r"metin-satir-max:x\.satirlar"),
                               ("liste dize", dict(ml, liste="evet"), r"metin-liste-bicimi:x\.satirlar"),
                               ("karakter_max 0", dict(ml, karakter_max=0), r"metin-tavani-bicimi:x\.satirlar")]:
            _, hb = tek([prm], ("metin",))
            vaka("F19 metin %s -> KIRMIZI" % ad, any(re.search(kalip, x) for x in hb), json.dumps(hb))
        _, h20 = tek([dict(rl, tip="renk_dizi")])
        vaka("F20 sozlukte olmayan tip yine KIRMIZI", h20 == ["bilinmeyen-tip:x.renkler=renk_dizi"], json.dumps(h20))
        os.makedirs(os.path.join(d, "jen", "u"))
        with open(os.path.join(d, "jen", "u", "u.py"), "w", encoding="utf-8") as f:
            f.write('SEMA = {"g": {"tip": "float", "min": 20.0, "max": 400.0}, "s": {"tip": "str"}}\n'
                    'DAR_SEMA = {"g": {"tip": "float", "min": 30.0, "max": 80.0}}\n')
        jen = os.path.join(d, "jen")
        vaka("F21 sema_adi SEMA'nin ustune alan alan · ad yok -> None · ad yok kaydi -> KIRMIZI sema-adi-yok",
             u.uretec_semasi(jen, "u/u.py", "DAR_SEMA") == {"g": {"tip": "float", "min": 30.0, "max": 80.0},
                                                          "s": {"tip": "str"}} and
             u.uretec_semasi(jen, "u/u.py", "YOK_SEMA") is None and
             "sema-adi-yok:y=YOK_SEMA" in u.hepsini_uret(
                 {"kayitlar": [{"kod": "y", "cagri": {"betik": "u/u.py"}, "sema_adi": "YOK_SEMA",
                                "parametreler": []}]}, jen)[1])
        print("F-MUTANT")
        mutant("MK1 kayitta bool->boolean -> KIRMIZI", k, m, r"bilinmeyen-tip:parca\.kapak=boolean",
               lambda kk, mm: degistir(kk, '"tip": "bool"', '"tip": "boolean"'))
        mutant("MK2 manifestte kosul silindi -> KIRMIZI", k, m, r"sapma:parca\.form\.kapak\.kosul",
               lambda kk, mm: degistir(mm, r"^\s+kosul: .*\n", "", regex=True))
        mutant("MK3 adim dusuruldu 0.01->0.001 -> KIRMIZI", k, m, r"sapma:parca\.form\.duvar_mm\.adim",
               lambda kk, mm: degistir(mm, "adim: 0.01,", "adim: 0.001,"))
        mutant("MK4 kayitta bilinmeyen girdi -> KIRMIZI", k, m, r"bilinmeyen-girdi:parca=olcuu",
               lambda kk, mm: degistir(kk, '"olcu"]', '"olcuu"]'))
        mutant("MK5 kosul olmayan alana bakiyor -> KIRMIZI", k, m, r"kosul-alan:parca\.kapak->yok",
               lambda kk, mm: degistir(kk, '"alan": "mod"', '"alan": "yok"'))
        mutant("MK6 manifestte ornek silindi -> KIRMIZI", k, m, r"sapma:harita\.form\.enlem\.ornek",
               lambda kk, mm: degistir(mm, r"^\s+ornek: 41\.0256,?\n", "", regex=True))
        mutant("MK7 manifest renk_tavani boyanabilir sayidan buyuk -> KIRMIZI", k, m,
               r"sapma:harita\.fiyat\.renk_tavani manifest=3 kopru=2",
               lambda kk, mm: degistir(mm, r'(kod: "harita",[\s\S]*?renk_tavani: )2', r"\g<1>3", regex=True))
        mutant("MK8 kopru govde adi parametre sonekinden sapti -> KIRMIZI", k, m,
               r"renk-bolge-adi:harita\.renk_yazi",
               lambda kk, mm: degistir(kk, '["plaka", "yazi", "cerceve"]', '["plaka", "metin", "cerceve"]'))
        mutant("MK9 kayitta renk_yazi silindi (tavan 1'e iner) -> KIRMIZI", k, m,
               r"sapma:harita\.fiyat\.renk_tavani manifest=2 kopru=1",
               lambda kk, mm: degistir(kk, r',\s*\{"ad": "renk_yazi"[^}]*\}', "", regex=True))
        mutant("MK0 kontrol: editoryal metin degisti -> YESIL kalir", k, m, None,
               lambda kk, mm: degistir(mm, "Sahte metin.", "Baska metin."))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def gercek():
    print("R) GERCEK KAYIT (sabit, repoda)")
    env = bool(os.environ.get("KOPRU_KAYIT"))
    vaka("R0b kayit yolu repoda (env yokken makine yolu YASAK)", env or
         os.path.realpath(GERCEK_KAYIT).startswith(os.path.realpath(KOK) + os.sep),
         "env=KOPRU_KAYIT" if env else GERCEK_KAYIT)
    if not os.path.isfile(GERCEK_KAYIT):
        vaka("R0 sabit kayit mevcut", False, "kayit-yok %s (ATLANMAZ — hermetik kayit repoda olmali)" % GERCEK_KAYIT)
        return
    vaka("R0 sabit kayit mevcut", True, GERCEK_KAYIT)
    u0 = arac_yukle()
    if not env:
        vaka("R0c KAYNAK_SHA satiri + uretec semalari mevcut", bool(u0.sabit_sha()) and
             isinstance(u0.jenerator_kok(GERCEK_KAYIT), dict), str(u0.sabit_sha()))
    print(u0.bayat_raporu())
    man = os.path.join(KOK, "foto-uretim-veri.js")
    rc, out = kos("--denetle", "--kayit", GERCEK_KAYIT, "--manifest", man)
    vaka("R1 gercek kayit + manifest --denetle YESIL", rc == 0 and "DENETLE=YESIL" in out, out.strip().splitlines()[-1])
    d = tempfile.mkdtemp(prefix="kopru-uret-gercek-")
    try:
        m = os.path.join(d, "m.js")
        shutil.copyfile(man, m)
        rc2, out2 = kos("--yaz", "--kayit", GERCEK_KAYIT, "--manifest", m)
        vaka("R2 --yaz kopyada degisen=0 + bayt ayni (manifest = uretim ciktisi)",
             rc2 == 0 and "degisen=0" in out2 and open(m, "rb").read() == open(man, "rb").read(), out2.strip())
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("R-MUTANT")
    # K3c: gercek kayit yapboz (renk_liste) + anahtarlik (metin liste); eski bool/kosul/sehir/yildiz capalari yok.
    mutant("MR1 gercek kayitta renk_liste -> renk_dizi (sozlukte yok) -> KIRMIZI", GERCEK_KAYIT, man,
           r"bilinmeyen-tip:yapboz\.renkler=renk_dizi",
           lambda kk, mm: degistir(kk, r'"tip":\s*"renk_liste"', '"tip": "renk_dizi"', regex=True))
    mutant("MR2 gercek kayitta palet tavani 4->3 -> KIRMIZI", GERCEK_KAYIT, man,
           r"sapma:yapboz\.fiyat\.renk_tavani manifest=4 kopru=3",
           lambda kk, mm: degistir(kk, r'"uzunluk_max":\s*4,(\s*"oge")', r'"uzunluk_max": 3,\1', regex=True))
    mutant("MR3 gercek manifestte adim dusuruldu -> KIRMIZI", GERCEK_KAYIT, man, r"sapma:\w+\.form\.\w+\.adim",
           lambda kk, mm: degistir(mm, "adim: 0.01,", "adim: 0.001,"))
    mutant("MR4 gercek manifestte anahtarlik satirlar max silindi -> KIRMIZI", GERCEK_KAYIT, man,
           r"sapma:anahtarlik\.form\.satirlar\.max",
           lambda kk, mm: degistir(mm, "            satir_max: 3,\n            max: 40,\n", "            satir_max: 3,\n"))
    mutant("MR5 gercek manifestte anahtarlik liste:true silindi -> KIRMIZI", GERCEK_KAYIT, man,
           r"sapma:anahtarlik\.form\.satirlar\.liste",
           lambda kk, mm: degistir(mm, "            liste: true,\n", ""))
    mutant("MR6 gercek kayitta satir_max silindi -> KIRMIZI", GERCEK_KAYIT, man, r"metin-satir-max:anahtarlik\.satirlar",
           lambda kk, mm: degistir(kk, r'"satir_max":\s*3,\s*', "", regex=True))
    mutant("MR7 gercek kayitta renk_liste oge bozuk -> KIRMIZI", GERCEK_KAYIT, man, r"renk-liste-oge:yapboz\.renkler",
           lambda kk, mm: degistir(kk, r'"oge":\s*"#RRGGBB"', '"oge": "#RGB"', regex=True))
    mutant("MR8 gercek manifestte yapboz renk_secimi silindi -> KIRMIZI", GERCEK_KAYIT, man, r"sapma:yapboz\.renk_secimi",
           lambda kk, mm: degistir(mm, '        renk_secimi: "palet",\n        palet_bolgeleri: ["renk1"',
                                   '        palet_bolgeleri: ["renk1"'))
    # MR9: kayit kopyasi gecici dizinde uretec dosyasini bulamaz -> gercek jenerator koku ile bellekte olculur.
    u = arac_yukle()
    kayit = json.load(open(GERCEK_KAYIT, encoding="utf-8"))
    ak = [k for k in kayit["kayitlar"] if k.get("sema_adi") == "ANAHTARLIK_SEMA"]
    for k in ak:
        k["sema_adi"] = "YOK_SEMA"
    _, h9 = u.hepsini_uret(kayit, u.jenerator_kok(GERCEK_KAYIT))
    vaka("MR9 gercek kayitta sema_adi uretec dosyasinda yok -> KIRMIZI", len(ak) == 1 and
         "sema-adi-yok:anahtarlik=YOK_SEMA" in h9, "uygulandi=%d %s" % (len(ak), h9))
    # FOTO KOLU (anahtarlik-foto, 9 Eki; 10 Eki figur_kulak): kol kaydi ayri satir URETMEZ; ana satira foto_kolu,
    # ana girdi AYNEN. anahtarlik-plaket kopruda ayri kayit, UI'da SUNULMAZ -> satir yok.
    gs, gh = arac_yukle().hepsini_uret(json.load(open(GERCEK_KAYIT, encoding="utf-8")))
    vaka("R-FK1 gercek kayit: anahtarlik-foto satiri YOK + anahtarlik.foto_kolu {foto-1, figur_kulak} + girdi [metin]",
         "anahtarlik-foto" not in gs and gs["anahtarlik"].get("foto_kolu") == {"girdi": ["foto-1"], "uretec": "figur_kulak"}
         and gs["anahtarlik"]["girdi"] == ["metin"] and not gh,
         "%s %s %s" % (sorted(gs), gs["anahtarlik"].get("foto_kolu"), gh))
    vaka("R-FK2 gercek kayit: anahtarlik-plaket (SUNULMAYAN) satiri YOK, manifestte de YOK",
         "anahtarlik-plaket" not in gs and 'kod: "anahtarlik-plaket"' not in open(man, encoding="utf-8").read(),
         "%s" % sorted(gs))
    mutant("MR10 gercek manifestte anahtarlik foto_kolu silindi -> KIRMIZI", GERCEK_KAYIT, man,
           r"sapma:anahtarlik\.foto_kolu",
           lambda kk, mm: degistir(mm, ',\n        foto_kolu: { girdi: ["foto-1"], uretec: "figur_kulak" }', ""))
    mutant("MR11 gercek kayitta figur-3mf -> figur-stl (sozlukte yok) -> KIRMIZI", GERCEK_KAYIT, man,
           r"bilinmeyen-girdi:anahtarlik-foto=figur-stl",
           lambda kk, mm: degistir(kk, '"figur-3mf"', '"figur-stl"'))
    mutant("MR13 manifestte foto kolu eski plaket_kulak'a doner -> KIRMIZI", GERCEK_KAYIT, man,
           r"sapma:anahtarlik\.foto_kolu",
           lambda kk, mm: degistir(mm, 'uretec: "figur_kulak" }', 'uretec: "plaket_kulak" }'))
    mutant("MR14 SUNULMAYAN disi yeni kayit -> tur-yok KIRMIZI (gizleme listesi genis degil)", GERCEK_KAYIT, man,
           r"tur-yok:anahtarlik-plaketx",
           lambda kk, mm: degistir(kk, '"kod": "anahtarlik-plaket"', '"kod": "anahtarlik-plaketx"'))
    # Form alani `aciklama` editoryal (ArTisT cumlesi): kopru uretmiyorsa tasinir, uretiyorsa kopru kazanir.
    ft = arac_yukle().form_aciklama_tasi
    vaka("R-AC1 form aciklama: eksikse manifestten tasinir, uretilen varsa ezilmez, yeni alana uydurulmaz",
         ft({"a": {"tip": "sayi", "aciklama": "X"}}, {"a": {"tip": "sayi"}}) == {"a": {"tip": "sayi", "aciklama": "X"}}
         and ft({"a": {"aciklama": "X"}}, {"a": {"aciklama": "Y"}}) == {"a": {"aciklama": "Y"}}
         and ft({}, {"b": {"tip": "sayi"}}) == {"b": {"tip": "sayi"}})
    mutant("MR15 gercek manifestte yapboz satir min degisti (aciklama tasinsa da) -> KIRMIZI", GERCEK_KAYIT, man,
           r"sapma:yapboz\.form",
           lambda kk, mm: degistir(mm, 'aciklama: "Yapbozun dikey kaç parçaya bölüneceği.",\n            min: 3,',
                                   'aciklama: "Yapbozun dikey kaç parçaya bölüneceği.",\n            min: 2,'))
    mutant("MR12 gercek kayitta foto kolunun ana turu yok -> KIRMIZI", GERCEK_KAYIT, man,
           r"kol-ana-yok:anahtarlik-foto->anahtarlik",
           lambda kk, mm: degistir(kk, '"kod": "anahtarlik",', '"kod": "anahtarlikx",'))
    mutant("MR0 kontrol: anahtarlik durustluk metni degisti -> YESIL kalir", GERCEK_KAYIT, man, None,
           lambda kk, mm: degistir(mm, 'durustluk: "Metal halka ve zincir', 'durustluk: "Metal halka ya da zincir'))


def main():
    hermetik()
    gercek()
    vk = sum(1 for k, g in sonuc.items() if not g and not k.startswith("M"))
    sv = sum(1 for k, g in sonuc.items() if not g and k.startswith("M"))
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (vk, sv))
    return 0 if vk == 0 and sv == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

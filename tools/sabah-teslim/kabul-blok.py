# -*- coding: utf-8 -*-
"""`bekci-kabul.py`ye EKLENEN teslim (KANAL=cip) bataryasi — kaynak metin.

MEVCUT bataryaya vaka EKLER; yeni dosya ACMAZ, taban vaka sayisini DUSURMEZ.
"""

KABUL_BLOGU = '''

# ------------------------------------------------------- H — TESLIM (KANAL=cip)

# 🔴 BUGUNUN DERSI, BATARYANIN EKSENI: "KOL KOSTU" KABUL DEGILDIR.
# 27 Agu sabahi kol kostu, hukum verdi, damgaladi — ve TESLIM OLMADI. Bu yuzden
# asagidaki vakalar kolun kosmasini DEGIL, TESLIMIN KENDISINI olcer:
#   B1  sentetik KIRMIZI  -> karar GEREKLI + prompt URETILDI + damga KONDU
#                            + kayit satiri SOMUT rc tasir (rc=None YAZILAMAZ)
#   B2  POZITIF KONTROL   -> hukum YESIL iken cip DOGMAZ, damga TUKETILMEZ
#   B3  MUKERRER YASAGI   -> ayni gun ikinci kosum ikinci cip URETMEZ
#   B4  CIPIN ICI DOLU    -> prompt o gunun spec'ini YA DA uretilememe SEBEBINI tasir
#   B5  MUTANT            -> teslim kolu oldurulunce B1 KIRMIZI, KONTROL B2 DEGISMEZ,
#                            ve kirmizinin SEBEBI hedef koldur (atif ayrica kanitlanir)
#
# TAMAMI FIKSTURDEDIR: canli damga dizinine, canli loga, canli prompt duzlemine
# ve canli `tamirci-spec/` dizinine HIC DOKUNULMAZ.

TESLIM_MUTANT_CAPASI = "    if not kirmizi_mi(k):\\n"
TESLIM_MUTANT_YAMASI = "    if True:  # MUTANT: teslim kolu OLDURULDU\\n"


def _teslim_fikstur_kur(td, bugun):
    """Fikstur duzlemi: kanca/kalp SAG, iki kanit dizini (bos/dolu), bos log."""
    kanca = os.path.join(td, "SKILL-sag.md")
    with open(kanca, "w", encoding="utf-8") as f:
        f.write("ADIM 0 — ÇİP-DOĞUM BEKÇİSİ\\n")
    kalp = os.path.join(td, "kalp-taze.md")
    damga = (dt.datetime.now(dt.timezone.utc)
             - dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(kalp, "w", encoding="utf-8") as f:
        f.write("KOSTU=A@%s\\n" % damga)
    kollar = [{"id": "A", "kanca": kanca,
               "jeton": "ADIM 0 — ÇİP-DOĞUM BEKÇİSİ", "tavan_saat": 30}]

    bos = os.path.join(td, "kanit-bos")
    os.makedirs(bos, exist_ok=True)
    dolu = os.path.join(td, "kanit-dolu")
    os.makedirs(dolu, exist_ok=True)
    spec_metni = "# KraL-Tamirci-%s — FIKSTUR SPEC GOVDESI-XYZZY\\n" % bugun.isoformat()
    with open(os.path.join(dolu, "KraL-Tamirci-%s.md" % bugun.strftime("%Y%m%d")),
              "w", encoding="utf-8") as f:
        f.write(spec_metni)

    sabah_log = os.path.join(td, "kral-sabah.log")
    with open(sabah_log, "w", encoding="utf-8") as f:
        f.write("TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'\\n")
    return {"kollar": kollar, "kalp": kalp, "bos": bos, "dolu": dolu,
            "spec_metni": spec_metni, "sabah_log": sabah_log}


def _teslim_cagri(CDB, fx, td, kanit_dizini, etiket, saat=10, kuru=False):
    """Tek `teslim_karari` cagrisi — TUM duzlem fiksturden gelir."""
    damga_dizini = os.path.join(td, "damga-%s" % etiket)
    log_yolu = os.path.join(td, "log-%s.log" % etiket)
    prompt_dizini = os.path.join(td, "prompt-%s" % etiket)
    return CDB.teslim_karari(
        simdi=yerel_epok(dt.date.today(), saat),
        dizin=kanit_dizini, esik_saat=9,
        damga_dizini=damga_dizini, log_yolu=log_yolu,
        prompt_dizini=prompt_dizini,
        teslim_kollari=fx["kollar"], teslim_kalp_yolu=fx["kalp"],
        sabah_log=fx["sabah_log"], kuru=kuru), damga_dizini, log_yolu, prompt_dizini


def _log_metni(yol):
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _teslim_kolunu_kos(CDB, td, ad):
    """B1+B2+B3+B4 kollarini TEK modul uzerinde kosar. Doner: olcum sozlugu.

    Ayni fonksiyon hem TABAN (mutasyonsuz) hem MUTANT modulle cagrilir; boylece
    mutantin oldurdugu seyin TAM OLARAK hangi kol oldugu okunabilir.
    """
    bugun = dt.date.today()
    fx = _teslim_fikstur_kur(td, bugun)
    o = {}

    # --- B1: sentetik KIRMIZI (bugunun spec'i YOKMUS gibi)
    t1, damga1, log1, prompt1 = _teslim_cagri(CDB, fx, td, fx["bos"], "%s-b1" % ad)
    o["b1_karar"] = t1["karar"]
    o["b1_cip"] = t1["cip_adi"]
    o["b1_prompt"] = t1["prompt_yolu"]
    o["b1_prompt_bayt"] = (os.path.getsize(t1["prompt_yolu"])
                           if t1["prompt_yolu"] != "-" and os.path.isfile(t1["prompt_yolu"])
                           else -1)
    o["b1_damga_var"] = int(os.path.isfile(
        os.path.join(damga1, "%s.bildirildi" % t1["anahtar"])))
    o["b1_log"] = _log_metni(log1)
    o["b1_anahtar"] = t1["anahtar"]
    o["b1_damga_dizini"] = damga1
    o["b1_log_yolu"] = log1

    # --- B3: AYNI gun, AYNI damga duzleminde IKINCI kosum
    t3 = CDB.teslim_karari(
        simdi=yerel_epok(bugun, 11), dizin=fx["bos"], esik_saat=9,
        damga_dizini=damga1, log_yolu=log1,
        prompt_dizini=os.path.join(td, "prompt-%s-b3" % ad),
        teslim_kollari=fx["kollar"], teslim_kalp_yolu=fx["kalp"],
        sabah_log=fx["sabah_log"])
    o["b3_karar"] = t3["karar"]

    # --- B2 POZITIF KONTROL: kanit VAR -> cip DOGMAZ
    t2, damga2, log2, prompt2 = _teslim_cagri(CDB, fx, td, fx["dolu"], "%s-b2" % ad)
    o["b2_karar"] = t2["karar"]
    o["b2_damga_dizini_var"] = int(os.path.isdir(damga2)
                                   and bool(os.listdir(damga2)))
    o["b2_prompt_dizini_var"] = int(os.path.isdir(prompt2)
                                    and bool(os.listdir(prompt2)))

    # --- B4: prompt GOVDESI (spec YOK hali)
    o["b4_govde_yok"] = ""
    if o["b1_prompt_bayt"] > 0:
        with open(t1["prompt_yolu"], encoding="utf-8") as f:
            o["b4_govde_yok"] = f.read()

    # --- B4b: prompt GOVDESI (spec VAR hali) — dogrudan uretici cagrilir
    k_dolu = CDB.karar(yerel_epok(bugun, 10), fx["dolu"], 9, None,
                       fx["kollar"], fx["kalp"], None)
    o["b4_govde_var"] = CDB.prompt_govdesi(k_dolu, fx["sabah_log"])
    o["b4_spec_metni"] = fx["spec_metni"]
    return o


def teslim_cip_bataryasi():
    baslik("H — TESLIM KOLU (KANAL=cip): olculen sey KOL DEGIL, TESLIMIN KENDISI")
    with tempfile.TemporaryDirectory(prefix="bekci-teslim-") as td:
        CDB = modul_yukle(MODUL, "cip_dogum_bekcisi_teslim", (CRON,))

        # ---- kanal sabiti gercekten degisti mi (kanal=YOK bir daha yazilamaz)
        kayit("H0 BILDIRIM_KANALI=cip",
              getattr(CDB, "BILDIRIM_KANALI", "-") == "cip"
              and "cip" in getattr(CDB, "KANALLAR", ()),
              "kanal=%s kanallar=%s" % (getattr(CDB, "BILDIRIM_KANALI", "-"),
                                        getattr(CDB, "KANALLAR", ())))

        # ---- in-process kol (gunde 96 tur) damgayi TUKETMEZ
        bugun = dt.date.today()
        fx0 = _teslim_fikstur_kur(td, bugun)
        damga0 = os.path.join(td, "damga-inproc")
        log0 = os.path.join(td, "log-inproc.log")
        s0 = CDB.kol(simdi=yerel_epok(bugun, 10), dizin=fx0["bos"], esik_saat=9,
                     damga_dizini=damga0, log_yolu=log0,
                     teslim_kollari=fx0["kollar"], teslim_kalp_yolu=fx0["kalp"])
        damga_bos = not (os.path.isdir(damga0) and os.listdir(damga0))
        kayit("H1 in-process kol damgayi TUKETMEZ",
              s0.get("hukum") == "KIRMIZI" and damga_bos
              and s0["bildirim"].get("rc") == 0,
              "hukum=%s damga_bos=%d rc=%s teslim=%s" % (
                  s0.get("hukum"), int(damga_bos), s0["bildirim"].get("rc"),
                  s0["bildirim"].get("teslim")))

        # ---- TABAN kollari
        taban_td = os.path.join(td, "taban")
        os.makedirs(taban_td, exist_ok=True)
        T = _teslim_kolunu_kos(CDB, taban_td, "taban")

        kayit("H2 (B1) sentetik KIRMIZI -> karar GEREKLI",
              T["b1_karar"] == "GEREKLI" and T["b1_damga_var"] == 1
              and T["b1_prompt_bayt"] > 0,
              "karar=%s damga=%d prompt_bayt=%d cip=%s" % (
                  T["b1_karar"], T["b1_damga_var"], T["b1_prompt_bayt"], T["b1_cip"]))

        kayit("H3 (B1) teslim satiri SOMUT rc tasir",
              "kanal=cip" in T["b1_log"] and "rc=None" not in T["b1_log"]
              and "kanal=YOK" not in T["b1_log"],
              "kanal_cip=%d rc_none=%d kanal_yok=%d" % (
                  int("kanal=cip" in T["b1_log"]), int("rc=None" in T["b1_log"]),
                  int("kanal=YOK" in T["b1_log"])))

        # ---- (c) KAYIT: gercek task_id -> BASARILI
        rc_ok, satir_ok = CDB.teslim_kaydet(T["b1_anahtar"], task_id="task_a1b2c3d4",
                                            log_yolu=T["b1_log_yolu"],
                                            damga_dizini=T["b1_damga_dizini"])
        kayit("H4 (B1) task_id kaydi -> TESLIM=BASARILI rc=0",
              rc_ok == 0 and "teslim=BASARILI" in satir_ok
              and "task_id=task_a1b2c3d4" in satir_ok and "rc=0" in satir_ok,
              "rc=%d satir=%s" % (rc_ok, satir_ok[-90:]))

        # ---- (c) KAYIT: UYDURUK/bicimsiz jeton -> BASARISIZ + damga GERI
        rc_kotu, satir_kotu = CDB.teslim_kaydet(
            T["b1_anahtar"], task_id="cip-dusurdum-soz-veriyorum",
            log_yolu=T["b1_log_yolu"], damga_dizini=T["b1_damga_dizini"])
        damga_geri = not os.path.isfile(os.path.join(
            T["b1_damga_dizini"], "%s.bildirildi" % T["b1_anahtar"]))
        kayit("H5 bicimsiz task_id -> BASARISIZ + damga GERI",
              rc_kotu == 1 and "teslim=BASARISIZ" in satir_kotu
              and "TASK_ID_BICIMI" in satir_kotu and damga_geri,
              "rc=%d damga_geri=%d satir=%s" % (rc_kotu, int(damga_geri),
                                                satir_kotu[-70:]))

        kayit("H6 (B3) ayni gun IKINCI kosum -> MUKERRER",
              T["b3_karar"] == "MUKERRER",
              "karar=%s" % T["b3_karar"])

        kayit("H7 (B2) KONTROL: kanit VAR -> cip DOGMAZ, damga TUKETILMEZ",
              T["b2_karar"] == "GEREKSIZ" and T["b2_damga_dizini_var"] == 0
              and T["b2_prompt_dizini_var"] == 0,
              "karar=%s damga=%d prompt=%d" % (
                  T["b2_karar"], T["b2_damga_dizini_var"], T["b2_prompt_dizini_var"]))

        kayit("H8 (B4) spec YOK -> prompt SEBEBI tasir",
              "SPEC URETILMEDI" in T["b4_govde_yok"]
              and "kral-sabah.py" in T["b4_govde_yok"]
              and "TypeError" in T["b4_govde_yok"],
              "bayt=%d sebep=%d arac=%d log_kuyrugu=%d" % (
                  len(T["b4_govde_yok"]),
                  int("SPEC URETILMEDI" in T["b4_govde_yok"]),
                  int("kral-sabah.py" in T["b4_govde_yok"]),
                  int("TypeError" in T["b4_govde_yok"])))

        kayit("H9 (B4) spec VAR -> prompt SPEC METNINI tasir",
              "GOVDESI-XYZZY" in T["b4_govde_var"],
              "bayt=%d spec_gomulu=%d" % (
                  len(T["b4_govde_var"]), int("GOVDESI-XYZZY" in T["b4_govde_var"])))

        # ---------------------------------------------------------------
        # B7/B9 — IHTAR gunde 2 kosum + TAVAN TURETILDI (elle kopya YOK)
        # ---------------------------------------------------------------
        kollar = {k["id"]: k for k in getattr(CDB, "TESLIM_KOLLARI", ())}
        ihtar = kollar.get("IHTAR", {})
        teftis = kollar.get("TEFTIS", {})
        esik = getattr(CDB, "ESIK_SAAT", -1)

        kayit("H13 (B7) IHTAR gunde 2 kosum, sabah kolu VAR",
              tuple(ihtar.get("saatler") or ()) and len(ihtar["saatler"]) == 2
              and min(ihtar["saatler"]) == esik,
              "saatler=%s esik=%s" % (ihtar.get("saatler"), esik))

        # 🔴 ESIK BAGLANTISI: sabah saati ESIKTEN TURER, ikiz sayi olmamali.
        kayit("H14 sabah saati ESIK_SAAT ile TEK KAYNAK",
              getattr(CDB, "TESLIM_SABAH_SAATI", None) == esik
              and esik in tuple(ihtar.get("saatler") or ()),
              "TESLIM_SABAH_SAATI=%s ESIK_SAAT=%s" % (
                  getattr(CDB, "TESLIM_SABAH_SAATI", None), esik))

        # 🔴 B9: tavan TURETILMIS mi — her kol icin formulden yeniden hesaplanip
        # alanla KIYASLANIR. Elle yazilmis bir sabit bu kolu OLDURUR.
        turetilmis = []
        for kid, k in sorted(kollar.items()):
            saatler = tuple(k.get("saatler") or ())
            beklenen = CDB.kol_tavani(saatler) if saatler else None
            turetilmis.append("%s saatler=%s bosluk=%s tavan=%s beklenen=%s" % (
                kid, saatler,
                CDB.en_genis_bosluk(saatler) if saatler else "-",
                k.get("tavan_saat"), beklenen))
        kayit("H15 (B9) tavan TURETILDI (elle sabit DEGIL)",
              all(k.get("saatler") and k.get("tavan_saat") == CDB.kol_tavani(k["saatler"])
                  for k in kollar.values()) and bool(kollar),
              " || ".join(turetilmis))

        # REGRESYON: turetme ESKI SABITLERI degistirmemeli (ikisi de 30 idi)
        kayit("H16 turetme REGRESYON YOK (ikisi de 30)",
              float(ihtar.get("tavan_saat") or -1) == 30.0
              and float(teftis.get("tavan_saat") or -1) == 30.0,
              "IHTAR=%s TEFTIS=%s (eski sabit: 30/30)" % (
                  ihtar.get("tavan_saat"), teftis.get("tavan_saat")))

        # Formulun KENDISI fiksturle olculur (yoksa "30 cikti, demek dogru" olurdu)
        fx_bosluk = [((9, 15), 18.0), ((17, 23), 18.0), ((15,), 24.0),
                     ((0, 12), 12.0), ((6, 12, 18), 12.0)]
        dusen_fx = ["%s->%s(bekl %s)" % (s, CDB.en_genis_bosluk(s), b)
                    for s, b in fx_bosluk if CDB.en_genis_bosluk(s) != b]
        kayit("H17 en_genis_bosluk() fiksturu 5/5",
              not dusen_fx, "dusen=%s" % (dusen_fx or "YOK"))

        # ================================================================
        # B5 MUTANT — teslim kolu OLDURULUR
        # ================================================================
        mut_td = os.path.join(td, "mutant")
        os.makedirs(mut_td, exist_ok=True)
        mut_modul = os.path.join(mut_td, "cip_dogum_bekcisi.py")
        with open(MODUL, encoding="utf-8") as f:
            kaynak = f.read()
        capa_adedi = kaynak.count(TESLIM_MUTANT_CAPASI)
        if capa_adedi != 1:
            # 🔴 CAPA COKMESI SESSIZ GECILMEZ ([[capa-cokmesi-arkasindaki-capalari-gizler]])
            kayit("H10 MUTANT capasi TEK", False,
                  "capa_adedi=%d (1 bekleniyor) -> mutant KOSTURULAMADI" % capa_adedi)
            kayit("H11 MUTANT B1 OLDU", None, "capa yok")
            kayit("H12 MUTANT KONTROL B2 DEGISMEDI", None, "capa yok")
            return
        kayit("H10 MUTANT capasi TEK", True, "capa_adedi=1")
        with open(mut_modul, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(TESLIM_MUTANT_CAPASI, TESLIM_MUTANT_YAMASI))
        MCDB = modul_yukle(mut_modul, "cip_dogum_bekcisi_teslim_mutant", (CRON,))
        M = _teslim_kolunu_kos(MCDB, mut_td, "mutant")

        # HEDEF-KOL ATFI: mutant B1'i oldurmeli VE oldurme SEBEBI hedef kol
        # olmali — yani karar `GEREKSIZ`e dusmeli (cokme/istisna DEGIL).
        kayit("H11 MUTANT B1 OLDU (hedef-kol atifli)",
              M["b1_karar"] != T["b1_karar"] and M["b1_karar"] == "GEREKSIZ"
              and M["b1_prompt_bayt"] <= 0,
              "taban=%s mutant=%s prompt_bayt=%d (sebep: kirmizi_mi() kolu)" % (
                  T["b1_karar"], M["b1_karar"], M["b1_prompt_bayt"]))

        kayit("H12 MUTANT KONTROL B2 DEGISMEDI",
              M["b2_karar"] == T["b2_karar"] == "GEREKSIZ",
              "taban=%s mutant=%s" % (T["b2_karar"], M["b2_karar"]))
'''

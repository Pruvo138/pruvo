# -*- coding: utf-8 -*-
"""`cip_dogum_bekcisi.py`ye EKLENEN teslim blogu — kaynak metin.

Bu dosya BIR MODUL DEGIL, `kur.py`nin canli dosyaya ekledigi METINDIR.
Ayri tutulmasinin sebebi: yama metni kod olarak okunabilsin, gozden gecirilebilsin
ve `kur.py` icine gomulu dev bir dizge olmasin.
"""

TESLIM_BLOGU = '''

# ============================================================================
# TESLIM KOLU — KANAL=cip   (27 Agu 2026, `KraL-SabahTeslim-27Agu`, OKAN KARARI)
# ----------------------------------------------------------------------------
# 🔴 OLCULEN ARIZA (26-27 Agu): bekci DOGRU atesledi, DOGRU hukum verdi, DOGRU
# damgaladi — ve Okan HICBIR SEY GORMEDI. Log satiri birebir:
#   `... anahtar=20260827 kanal=YOK rc=None teslim=OLCULEMEDI (kanal=YOK,
#    ekrana hicbir sey dusmedi)`
# Yani zincirin uc halkasindan ikisi calisti, sonuncusu BOSLUGA BASTI.
#
# 🔴 OKAN KARARI: teslim kanali CIP. Gerekce OLCULMUS — bugun ona ULASTIGI
# KANITLANMIS tek kanal paneldir (dusurulen ciplerin hepsini gordu ve tikladi).
#
# 🔴 MIMARI KISIT (bu blogun VAROLUS SEBEBI): kabuk betigi / cron CIP DUSUREMEZ.
# Cipi ancak bir Claude oturumu yaratabilir. Dolayisiyla teslim IKI PARCADIR:
#   (a) HUKUM + YUK  -> burasi (`teslim_karari`), her yerden cagrilabilir
#   (b) CIP DOGUMU   -> panel `Routines` uzerindeki zamanlanmis Claude oturumu
#   (c) KAYIT        -> burasi (`teslim_kaydet`), task_id ile geri yazar
# `bildir()` bu yuzden CIP kanalinda damgayi TUKETMEZ; damga "bugun TESLIM
# EDILDI" jetonudur ve onu yalniz (a) koyar. Aksi halde gunde 96 kez kosan
# in-process kol damgayi 09:08'de yakar, 09:00 rutini MUKERRER goruр teslim
# etmez — teslim ASLA gerceklesmez.
#
# 🔴 `rc=None` ARTIK YAZILAMAZ: her teslim satiri somut bir rc tasir; kanal ya
# cipi uretir (`TESLIM=BASARILI task_id=...`) ya da `TESLIM=BASARISIZ sebep=...`
# basar. "Olcemedim" bir teslim hukmu DEGILDIR.
# ============================================================================

TESLIM_PROMPT_DIZINI = "/private/tmp/pruvo-bekci-teslim"
TESLIM_KARARLARI = ("GEREKLI", "GEREKSIZ", "MUKERRER", "OLCULEMEDI")
# Cip adi `<Ev>-<Is>` duzenine uyar (CLAUDE.md CHIP DUZENI ②).
TESLIM_AYLARI = ("Oca", "Sub", "Mar", "Nis", "May", "Haz",
                 "Tem", "Agu", "Eyl", "Eki", "Kas", "Ara")
# task_id BICIM KAPISI: isci/oturum ciktisi jeton UYDURABILIR
# ([[isci-ciktisi-arsiv-jetonunu-uydurabilir]]). Bicimi tutmayan jeton TESLIM
# SAYILMAZ; kayit `BASARISIZ` duser ve damga geri verilir (yeniden denenebilsin).
_TASK_ID_DESENI = re.compile(r"^task_[0-9a-fA-F]{6,}$")


def cip_adi(yerel_tarih):
    """O gunun Tamirci cipinin adi. TEK yerde uretilir."""
    return "KraL-Tamirci-%d%s" % (yerel_tarih.day,
                                  TESLIM_AYLARI[yerel_tarih.month - 1])


def _son_satirlar(yol, adet=25):
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            satirlar = dosya.read().splitlines()
    except OSError as hata:
        return "(%s okunamadi: %s)" % (yol, type(hata).__name__)
    if not satirlar:
        return "(%s BOS)" % yol
    return "\\n".join(satirlar[-adet:])


def prompt_govdesi(k, sabah_log=None):
    """CIPIN PROMPT'U — tek tikla is baslar, Okan'a "git bak" DENMEZ.

    Iki hal:
      · o gunun spec'i VAR    -> spec metni AYNEN gomulur
      · spec YOK (asil hal)   -> URETILEMEME SEBEBI gomulur (bekci hukmu +
        beklenen yol + `kral-sabah.log` kuyrugu) ve cipin ILK adimi spec'i
        URETMEK olur.
    """
    sabah_log = sabah_log or os.path.join(CRON_KOKU, "kral-sabah.log")
    yol = k.get("kanit_yolu") or "-"
    ad = k.get("kanit_adi") or "-"
    tarih = k.get("tarih") or "-"

    spec_metni = None
    try:
        if os.path.isfile(yol) and os.path.getsize(yol) > 0:
            with open(yol, encoding="utf-8", errors="replace") as dosya:
                spec_metni = dosya.read()
    except OSError:
        spec_metni = None

    bas = [
        "Sen `%s` CIPISIN (PRUVO / KraL evi). Raporlarini bu imzayla at." % cip_adi(
            dt.date.fromisoformat(tarih) if tarih != "-" else dt.date.today()),
        "",
        "## ADIM 0 — ACILIS",
        "1. `/Users/okan/dev/pruvo/CLAUDE.md` oku ve uy (KOMUT STILI dahil).",
        "2. Ortak kutuyu (`~/.claude/projects/-Users-okan-dev-pruvo/memory/"
        "mimar-posta-kutusu.md`) oku; 🔴 oraya **`Write` ile ASLA** yazma, yalniz "
        "`Edit` ile EN USTE ekle. Kutuya kisa bir `BASLIYORUM` blogu birak.",
        "3. Kapanista sayili kapanis + son satir birebir `✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM`.",
        "",
        "## NEDEN DOGDUN (bekci olcumu — iddia degil)",
        "- BEKCI_HUKUM=%s  sebep=%s" % (k.get("hukum"), k.get("sebep")),
        "- Beklenen dogum kaniti: `%s`" % yol,
        "- Olculen boyut: %s bayt (0/-1 = kanit YOK)" % k.get("boyut"),
        "- Yerel saat %s, esik %s" % (k.get("saat"), k.get("esik")),
        "",
    ]

    if spec_metni:
        bas += [
            "## BUGUNUN TAMIRCI SPEC'I (`%s` — AYNEN)" % ad,
            "",
            spec_metni.rstrip("\\n"),
        ]
    else:
        bas += [
            "## 🔴 SPEC URETILMEDI — ISININ BIRINCI ADIMI ONU URETMEK",
            "",
            "O gunun Tamirci spec'i (`%s`) YOK. Sebebi asagidaki kuyrukta." % ad,
            "",
            "**ILK KOMUT (tek satir):**",
            "```bash",
            "python3 /Users/okan/.claude/cron/kral-sabah.py",
            "```",
            "Cikti `SONUC_KOLU=SPEC_VAR` derse spec uretildi -> onu OKU ve isini ondan al.",
            "`SONUC_KOLU=SPEC_URETILMEDI` derse SEBEBI onar; araci onarmadan is yapma "
            "(bugunun arizasi tam olarak buydu).",
            "",
            "**`kral-sabah.log` KUYRUGU (son 25 satir, ham):**",
            "```",
            _son_satirlar(sabah_log, 25),
            "```",
        ]

    bas += [
        "",
        "## YASAKLAR",
        "Tekil yama (tek satir duzeltip kapatmak) · olcmedigine YESIL demek · "
        "`urunler.json` · ortak kutuya `Write` · bypass · main'e merge/push "
        "(karar MIMARDA) · Okan'a rutin bildirim.",
    ]
    return "\\n".join(bas)


def _teslim_log_satiri(anahtar, rc, teslim, detay, ayrinti, simdi=None):
    """🔴 TEK BICIM: her teslim satiri SOMUT rc + SOMUT teslim hukmu tasir."""
    simdi = simdi if simdi is not None else time.time()
    return "%s BEKCI_BILDIRIM anahtar=%s kanal=cip rc=%d teslim=%s (%s) ayrinti=%s" % (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(simdi)),
        anahtar, int(rc), teslim, detay, ayrinti)


def teslim_karari(simdi=None, dizin=None, esik_saat=None, damga_dizini=None,
                  log_yolu=None, prompt_dizini=None, yerel_cozucu=None,
                  teslim_kollari=None, teslim_kalp_yolu=None,
                  teslim_bayatlik_saat=None, anahtar_oneki="", kuru=False,
                  sabah_log=None):
    """(a) HUKUM + YUK. Rutin (zamanlanmis Claude oturumu) BUNU cagirir.

    Doner sozluk: {karar, anahtar, hukum, sebep, cip_adi, prompt_yolu, ayrinti}
      · GEREKLI    -> cip DOGACAK; damga KONDU, prompt YAZILDI
      · GEREKSIZ   -> hukum YESIL/PENCERE_DISI; cip DOGMAZ, damga KONMAZ (B2)
      · MUKERRER   -> bugun zaten teslim edildi; ikinci cip YOK (B3)
      · OLCULEMEDI -> damga/prompt yazilamadi; SESSIZ GECILMEZ

    🔴 HEARTBEAT: karar ne olursa olsun loga BIR satir duser. "Rutin bugun kostu
    mu" sorusu boylece tek dosyadan cevaplanir — kolun kendisi de OLCULUR.
    """
    simdi = simdi if simdi is not None else time.time()
    prompt_dizini = prompt_dizini or TESLIM_PROMPT_DIZINI

    k = karar(simdi, dizin, esik_saat, yerel_cozucu, teslim_kollari,
              teslim_kalp_yolu, teslim_bayatlik_saat)
    anahtar = "%s%s" % (anahtar_oneki, str(k.get("tarih") or "-").replace("-", ""))
    taban = {"karar": "OLCULEMEDI", "anahtar": anahtar, "hukum": k.get("hukum"),
             "sebep": k.get("sebep"), "cip_adi": "-", "prompt_yolu": "-",
             "ayrinti": "-", "kanit_yolu": k.get("kanit_yolu")}

    def _don(karar_adi, ayrinti, rc, teslim, detay):
        s = dict(taban)
        s["karar"] = karar_adi
        s["ayrinti"] = ayrinti
        if not kuru:
            _loga_yaz(_teslim_log_satiri(anahtar, rc, teslim, detay, ayrinti, simdi),
                      log_yolu)
        return s

    # --- B2 POZITIF KONTROL: sessiz gun SESSIZ KALIR ---
    # 🔴 Bu kol OLMAZSA arac "her sabah cip" makinesine doner. Hukum YESIL ya da
    # PENCERE_DISI ise cip DOGMAZ ve damga TUKETILMEZ.
    if not kirmizi_mi(k):
        return _don("GEREKSIZ",
                    "hukum=%s -> cip DOGMAZ (sessiz gun sessiz kalir)" % k.get("hukum"),
                    0, "GEREKMEDI", "hukum=%s" % k.get("hukum"))

    # --- B3 MUKERRER YASAGI: gun basina EN FAZLA 1 cip ---
    if kuru:
        var = os.path.isfile(os.path.join(damga_dizini or DAMGA_DIZINI,
                                          "%s%s" % (anahtar, DAMGA_SONEKI)))
        if var:
            return _don("MUKERRER", "damga VAR (kuru)", 0, "MUKERRER", "kuru")
    else:
        kazandi, damga_yolu = _damga_koy(anahtar, simdi, damga_dizini)
        if not kazandi:
            return _don("MUKERRER",
                        "damga VAR -> bugun zaten teslim edildi (%s)" % damga_yolu,
                        0, "MUKERRER", "damga=%s" % damga_yolu)

    # --- B4 CIPIN ICI: o gunun spec'i ya da URETILEMEME SEBEBI ---
    ad = cip_adi(dt.date.fromisoformat(k["tarih"]) if k.get("tarih") not in (None, "-")
                 else dt.date.today())
    taban["cip_adi"] = ad
    govde = prompt_govdesi(k, sabah_log)
    prompt_yolu = os.path.join(prompt_dizini, "prompt-%s.md" % anahtar)
    if not kuru:
        try:
            os.makedirs(prompt_dizini, exist_ok=True)
            with open(prompt_yolu, "w", encoding="utf-8") as dosya:
                dosya.write(govde)
        except OSError as hata:
            # Damgayi GERI VER: teslim edilemedi, yarinki/sonraki kosum denesin.
            _damga_geri_ver(anahtar, damga_dizini)
            return _don("OLCULEMEDI",
                        "prompt YAZILAMADI: %s" % type(hata).__name__,
                        1, "BASARISIZ", "prompt_yazilamadi")
    taban["prompt_yolu"] = prompt_yolu

    return _don("GEREKLI",
                "cip=%s prompt=%s bayt=%d" % (ad, prompt_yolu, len(govde.encode("utf-8"))),
                0, "BEKLIYOR", "cip=%s" % ad)


def _damga_geri_ver(anahtar, damga_dizini=None):
    """Teslim BASARISIZ olduysa damga geri verilir — yoksa arac 'teslim ettim'
    yalanini kalicilastirir ve o gun bir daha denenemez."""
    yol = os.path.join(damga_dizini or DAMGA_DIZINI,
                       "%s%s" % (anahtar, DAMGA_SONEKI))
    try:
        os.unlink(yol)
        return True
    except OSError:
        return False


def teslim_kaydet(anahtar, task_id=None, sebep=None, log_yolu=None,
                  damga_dizini=None, simdi=None):
    """(c) KAYIT — cip DOGDUKTAN sonra rutin bunu cagirir.

    `task_id` verilirse TESLIM=BASARILI + task_id loga yazilir.
    Verilmezse/bicimsizse TESLIM=BASARISIZ + SEBEP yazilir ve damga GERI VERILIR.
    🔴 Her iki yolda da rc SOMUTTUR; `rc=None` URETILEMEZ.
    Doner: (rc, satir)
    """
    simdi = simdi if simdi is not None else time.time()
    if task_id and _TASK_ID_DESENI.match(str(task_id).strip()):
        satir = _teslim_log_satiri(anahtar, 0, "BASARILI",
                                   "cip panelde DOGDU", "task_id=%s" % task_id.strip(),
                                   simdi)
        _loga_yaz(satir, log_yolu)
        return 0, satir
    if task_id:
        neden = "TASK_ID_BICIMI:%r" % str(task_id)[:40]
    else:
        neden = sebep or "SEBEP_VERILMEDI"
    geri = _damga_geri_ver(anahtar, damga_dizini)
    satir = _teslim_log_satiri(anahtar, 1, "BASARISIZ", neden,
                               "damga_geri_verildi=%d" % (1 if geri else 0), simdi)
    _loga_yaz(satir, log_yolu)
    return 1, satir


if __name__ == "__main__":
    _ap = argparse.ArgumentParser(description="cip-dogum bekcisi")
    _ap.add_argument("--kuru", action="store_true",
                     help="karar VERILIR, bildirim/damga/log YOK")
    _ap.add_argument("--teslim-karari", action="store_true",
                     help="(a) TESLIM KOLU: bugun cip dusurulecek mi")
    _ap.add_argument("--teslim-kaydet", action="store_true",
                     help="(c) KAYIT: cip dogdu, task_id'yi yaz")
    _ap.add_argument("--anahtar", default=None, help="teslim anahtari (YYYYAAGG)")
    _ap.add_argument("--task-id", default=None, help="dogan cipin task_id'si")
    _ap.add_argument("--sebep", default=None, help="teslim BASARISIZ ise sebep")
    _a = _ap.parse_args()

    if _a.teslim_kaydet:
        if not _a.anahtar:
            print("TESLIM_KAYIT=OLCULEMEDI sebep=ANAHTAR_YOK")
            sys.exit(2)
        _rc, _satir = teslim_kaydet(_a.anahtar, _a.task_id, _a.sebep)
        print(_satir)
        print("TESLIM_KAYIT=%s rc=%d" % ("BASARILI" if _rc == 0 else "BASARISIZ", _rc))
        sys.exit(_rc)

    if _a.teslim_karari:
        _t = teslim_karari(kuru=_a.kuru)
        print("TESLIM_KARARI=%s" % _t["karar"])
        print("ANAHTAR=%s" % _t["anahtar"])
        print("HUKUM=%s" % _t["hukum"])
        print("SEBEP=%s" % _t["sebep"])
        print("CIP_ADI=%s" % _t["cip_adi"])
        print("PROMPT_YOLU=%s" % _t["prompt_yolu"])
        print("AYRINTI=%s" % _t["ayrinti"])
        sys.exit(0 if _t["karar"] in ("GEREKLI", "GEREKSIZ", "MUKERRER") else 1)

    _s = kol(kuru=_a.kuru)
    print(_s["ozet"] + " kanit=%s boyut=%s" % (_s.get("kanit_adi"), _s.get("boyut")))
    sys.exit(1 if kirmizi_mi(_s) else 0)
'''

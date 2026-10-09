#!/usr/bin/env python3
"""KOPRU MANIFEST URETECI (kopru-15 DILIM-2, 8 Eki 2026) — TeKiN `kopru_kayitlari.json` -> foto-uretim-veri.js
tur satirlari, DETERMINISTIK ve TEK fonksiyonla (`satir_uret`).

NEDEN: 15 kopru turunun manifest satirlari elle/m3 kopyasiyla yazilmisti; TeKiN `kosul` metadatasi ve
surekli `sayi` alanlarinin `adim`i tasinmamisti -> G4a ② `uretec-red:genel` x4. Satirlar artik BU
araçtan turetilir; `--denetle` manifest kayittan saparsa adiyla KIRMIZI yakar (CI'da test uzerinden).

SOZLUK (eşleme YALNIZ burada; manifest yorumu bu dosyayi isaret eder):
  girdi   : olcu -> "form" · foto -> "foto-1" · plaket-3mf -> "foto-1" (saglayici plaketi FOTODAN cikar) ·
            ses/metin/konum/tarih aynen · baska -> KIRMIZI
  FOTO KOLU (anahtarlik-foto 9 Eki): KOL_KAYDI'ndaki kayit AYRI tur satiri URETMEZ; ana turun ikinci girdi koludur:
            ana satira `foto_kolu: {girdi: [<eslenmis>], uretec: <kol uretec'i>}` yazilir. Form/renk/olcu ANA kayittan
            (kulak konumu ortak `anahtarlik_kulak_konum`). Ana `girdi` DEGISMEZ: foto girdisi ancak sunucu zinciri
            (saglayici plaket -> kosucu plaket_kulak) baglaninca ana girdiye katilir (yoksa ② foto alir, isimlik
            fotoyu yok sayar = sessiz hata). Ana kayit yoksa KIRMIZI `kol-ana-yok`.
  tip     : sayi -> sayi + adim (kayittaki `adim`, yoksa 0.01; enlem/boylam 0.000001)
            tam (ya da sayi + `tam:true`) -> sayi + adim 1
            renk -> form DEGIL, renk_bolgeleri (`renk_<b>` -> {kod:<b>, ad:<etiket - " rengi">, renkler})
            dosya -> form DISI (girdinin kendisi) · bool/secim aynen
            metin -> aynen + `max` (kayittaki `karakter_max` -> `max`; yoksa URETECIN `SEMA[ad]` uzunluk tavani: str->uzunluk_max,
            yoksa uretec varsayilani 1000; liste->oge.uzunluk_max; ast ile okunur, uretec KOSMAZ; uretec
            dosyasi/alani yok -> KIRMIZI) + `zorunlu:true` degilse `zorunlu:false` (bos/yok = uretec
            varsayilani). NEDEN (kopru-15 ESLE): max'siz metin alanini VERI.parametreDogrula her degerde
            `parametre-metin` ile reddediyordu (braille ⑤ 400).
            metin + `liste:true` (K3c anahtarlik) -> {tip:"metin", etiket, liste:true, satir_max, max:karakter_max,
            zorunlu}: deger satir DIZISI (1..satir_max oge, her oge <= max); `satir_max` pozitif tam sayi degilse
            ya da `liste` true/false degilse KIRMIZI (VERI.parametreDogrula metin dali bu alanlari FAIL-CLOSED olcer)
            renk_liste (K3c yapboz) -> form DEGIL, manifestin PALET mekanizmasi: renk_secimi "palet" +
            palet_bolgeleri ["renk1".."renkN"] (N = uzunluk_max, 1..4) + fiyat.renk_tavani = N; kosucu esle_<kod>
            odenen renkleri SIRAYLA uretecin <ad> listesine (yapboz `renkler`) gecirir. `oge` "#RRGGBB" degilse,
            ikinci renk_liste ya da renk_* bolgesiyle karisik kayit KIRMIZI
            ses girdili kaydin min/max'siz `sayi` alani (genlik dizisi) -> tip "ses"
            baska tip -> KIRMIZI
  ornek   : kaydin `ornek.girdi.<ad>` degeri form alanina `ornek` olarak AYNEN (yer tutucu `<...>` metni
            tasinmaz). foto-ornek-uc-uca.ornek_parametre sayi/metin icin ONCE bunu kullanir. NEDEN (kopru-15
            SON3): min tabanli ornek sehir'i bos alana (30,30 -> OSM bina yok), zorunlu metin "PRUVO" yildiz'in
            tarih_saat'ini bicim disina dusuruyordu.
  kosul   : form alaninda `kosul: [{alan, degerler}]` AYNEN (alan formda olmali, yoksa KIRMIZI)
  olcu_mm : olcek.min_mm/max_mm · fiyat.adim_mm : olcek.adim_mm · malzemeler : {govde: izinli_malzeme}
  olcu_ekseni : olcek.belirleyen_parametre DOLU -> "sabit" (surgu = hedef) · bos/null -> "turetilmis"
            (kopru-15 dilim-3: surgu YOK, fiyat onizlemede OLCULEN uzun kenardan; sunucu kaydindan)
  sema_adi: kayit `sema_adi` doluysa uretec dosyasinin o adli literal sozlugu SEMA'nin USTUNE (alan alan) yazilir
            (anahtarlik: isimlik_uret ANAHTARLIK_SEMA genislik/kontur araligini daraltir); ad dosyada yoksa KIRMIZI
  bust    : rolyef `tur_tanimi_teklifi` (alanlar rolyef parametresinin ustune yazilir, sonra ayni sozluk)
Editoryal alanlar (ad, aciklama, motor, fiyat.formul, ornek_kanit_izni, durustluk, ornek_notu) manifestte
elle kalir; arac yalniz TURETILEN alanlari yazar/denetler.

KULLANIM
  python3 tools/kopru-manifest-uret.py               # uretilen satirlari JSON basar (yazmaz)
  python3 tools/kopru-manifest-uret.py --yaz         # 15 satiri manifestte yeniden yazar (idempotent)
  python3 tools/kopru-manifest-uret.py --denetle     # manifest == uretim mi? rc 0 YESIL · 1 KIRMIZI · 3 kayit yok
  python3 tools/kopru-manifest-uret.py --kayit-tazele  # TeKiN kaydini repoya sabitler (+ SEMA + KAYNAK_SHA) ve --yaz
  python3 tools/kopru-manifest-uret.py --bayat       # RAPOR: sabit kayit TeKiN main'in kac commit gerisinde (rc 0)
  --kayit <yol> (varsayilan KOPRU_KAYIT ya da SABIT kayit <repo>/jenerator/kopru/kopru_kayitlari.json)

SABIT KAYIT (sinif-r-k80, 9 Eki 2026): R/E katmanlari makinedeki CANLI TeKiN kaydini (~/dev/pruvo-jenerator)
okuyordu -> CI'da `ATLANDI`, pre-push'ta TeKiN her push'unda kirmizi. Artik repoda sha-sabit anlik goruntu:
  jenerator/kopru/kopru_kayitlari.json  (TeKiN kaydinin bayt-esit kopyasi)
  jenerator/kopru/uretec_semalari.json  ({betik: {SEMA, <sema_adi>...}} — uretec dosyalarindan ast ile)
  jenerator/kopru/KAYNAK_SHA            (`KAYNAK_SHA=<TeKiN jenerator commit'i>`)
Guncelleme YALNIZ bilincli commit'le: `--kayit-tazele` (kopya + sema + sha satiri + manifest --yaz).
`KOPRU_KAYIT` env yalniz elle karsilastirma icindir (kayit yaninda uretec_semalari.json yoksa eski yol:
SEMA `<jen>/<betik>` dosyasindan).
  --manifest <yol> (varsayilan <repo>/foto-uretim-veri.js)
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SABIT_DIZIN = os.path.join(KOK, "jenerator", "kopru")
SABIT_KAYIT = os.path.join(SABIT_DIZIN, "kopru_kayitlari.json")
SEMA_DOSYASI = "uretec_semalari.json"
SABIT_SHA = os.path.join(SABIT_DIZIN, "KAYNAK_SHA")
TEKIN_KOK = os.environ.get("KOPRU_TEKIN_KOK") or os.path.expanduser("~/dev/pruvo-jenerator")
TEKIN_KAYIT_GORELI = "jeneratorler/kopru/kopru_kayitlari.json"
VARSAYILAN_KAYIT = SABIT_KAYIT

GIRDI_ESLE = {"olcu": "form", "foto": "foto-1", "plaket-3mf": "foto-1", "ses": "ses", "metin": "metin", "konum": "konum", "tarih": "tarih"}
BILINEN_TIP = ("sayi", "tam", "secim", "metin", "bool", "renk", "dosya", "renk_liste")
RENK_LISTE_OGE = "#RRGGBB"
RENK_LISTE_TAVAN = 4  # AMS 4 yuva (VERI.renkTavani 1..4)
# Okan 9 Eki "malzeme seçiminde sadece pla ve petg": foto-uretim-veri.js VERI.MALZEMELER kodlariyla AYNI (sapma
# tools/kopru-manifest-uret-test.py + --denetle ile olculur: kopru ASA/ABS izinli olsa da manifeste girmez).
FOTO_MALZEMELERI = ("PLA", "PETG")
KONUM_ADIM = {"enlem": 0.000001, "boylam": 0.000001}
VARSAYILAN_ADIM = 0.01
# Bolge renk listeleri (sunum kurali, kayitta YOK): cift sirali bolge acik-once, tek sirali koyu-once ->
# iki bolgenin ilk (varsayilan) renkleri farkli. Adlar manifest RENK_HEX'te olmali (--denetle olcer).
RENK_ACIK_ONCE = ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
RENK_KOYU_ONCE = ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
TEKLIF_KOD = {"rolyef": "bust"}  # tur_tanimi_teklifi -> manifest tur kodu
TURETILEN = ("girdi", "uretec", "olcu_mm", "renk_bolgeleri", "malzemeler", "form", "olcu_ekseni", "renk_secimi",
             "palet_bolgeleri", "foto_kolu")
# Ikinci girdi kolu kayitlari: kayit kodu -> ana tur kodu (yukaridaki FOTO KOLU).
KOL_KAYDI = {"anahtarlik-foto": "anahtarlik"}
# Yalniz renk_liste kaydinda DOLU; None -> manifestte alan YAZILMAZ (varsa silinir), --denetle alan yok bekler.
OPSIYONEL = ("renk_secimi", "palet_bolgeleri", "foto_kolu")

NODE_OKU = (
    "const vm=require('vm'),fs=require('fs');const k={};"
    "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});"
    "process.stdout.write(JSON.stringify({turler:k.PRUVO_FOTO.turler,renk_hex:k.PRUVO_FOTO.RENK_HEX}));"
)


class KayitHatasi(Exception):
    pass


def uretec_semasi(jen, betik, sema_adi=None):
    """Uretec dosyasindaki ust duzey `SEMA = {...}` -> {alan: {anahtar: deger}} (ast; YALNIZ literal degerler,
    `float(ARALIK_MAX_MM)` gibi literal olmayanlar atlanir). Dosya/SEMA yok -> None. Uretec import EDILMEZ.
    `sema_adi` (kayit alani, or. ANAHTARLIK_SEMA) verilirse o sozluk SEMA'nin ustune alan alan yazilir; yoksa None."""
    if isinstance(jen, dict):  # sabit kayit: uretec_semalari.json (betik -> {sozluk_adi: sozluk})
        ent = jen.get(betik) if betik else None
        if not isinstance(ent, dict):
            return None
        oku = lambda ad: json.loads(json.dumps(ent[ad])) if isinstance(ent.get(ad), dict) else None  # noqa: E731
    else:
        yol = os.path.join(jen, betik) if jen and betik else ""
        if not yol or not os.path.isfile(yol):
            return None
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read(), yol)
        oku = lambda ad: _sozluk_oku(agac, ad)  # noqa: E731
    taban = oku("SEMA")
    if taban is None or not sema_adi or sema_adi == "SEMA":
        return taban
    ust = oku(sema_adi)
    if ust is None:
        return None
    for alan, kural in ust.items():
        taban[alan] = dict(taban.get(alan) or {}, **kural)
    return taban


def _sozluk_oku(agac, ad):
    for d in agac.body:
        if (isinstance(d, ast.Assign) and isinstance(d.value, ast.Dict)
                and any(isinstance(t, ast.Name) and t.id == ad for t in d.targets)):
            sema = {}
            for k, v in zip(d.value.keys, d.value.values):
                if not (isinstance(k, ast.Constant) and isinstance(v, ast.Dict)):
                    continue
                alan = {}
                for kk, vv in zip(v.keys, v.values):
                    try:
                        alan[ast.literal_eval(kk)] = ast.literal_eval(vv)
                    except (ValueError, TypeError, SyntaxError):
                        continue
                sema[k.value] = alan
            return sema
    return None


def metin_tavani(sema_alani):
    """Uretec alan semasi -> metin uzunluk tavani (uretec_ortak._deger_dogrula ile ayni kural) ya da None."""
    if not isinstance(sema_alani, dict):
        return None
    if sema_alani.get("tip") == "str":
        return sema_alani.get("uzunluk_max", 1000)
    oge = sema_alani.get("oge")
    if sema_alani.get("tip") == "liste" and isinstance(oge, dict) and oge.get("tip") == "str":
        return oge.get("uzunluk_max", 1000)
    return None


def ornek_degeri(ornek_girdi, ad):
    """Kayit `ornek.girdi[ad]` -> (var_mi, deger). Yer tutucu metin (`<100 elemanli dizi, sinus>`) ornek DEGIL."""
    if not isinstance(ornek_girdi, dict) or ad not in ornek_girdi:
        return False, None
    v = ornek_girdi[ad]
    if isinstance(v, str) and v.startswith("<"):
        return False, None
    return True, v


def _alan_uret(kayit_kod, girdiler, p, hatalar, sema=None, ornek_girdi=None):
    """Tek kayit parametresi -> (form_alani | None, renk_bolgesi | None). `sema` = uretec SEMA (metin tavani),
    `ornek_girdi` = kaydin `ornek.girdi` sozlugu (form alanina `ornek`)."""
    ad, tip = p.get("ad"), p.get("tip")
    if tip not in BILINEN_TIP:
        hatalar.append("bilinmeyen-tip:%s.%s=%s" % (kayit_kod, ad, tip))
        return None, None
    if tip == "dosya":
        return None, None
    if tip == "renk":
        if not str(ad).startswith("renk_"):
            hatalar.append("renk-adi:%s.%s" % (kayit_kod, ad))
            return None, None
        etiket = p.get("etiket") or ad
        return None, {"kod": ad[len("renk_"):], "ad": re.sub(r"\s+rengi$", "", etiket, flags=re.I) or etiket}
    if tip == "sayi" and "ses" in girdiler and "min" not in p and "max" not in p:
        return {"tip": "ses", "etiket": p.get("etiket") or ad}, None
    alan = {"tip": "sayi" if tip == "tam" else tip}
    if tip == "metin" and "liste" in p and not isinstance(p["liste"], bool):
        hatalar.append("metin-liste-bicimi:%s.%s" % (kayit_kod, ad))
    liste = tip == "metin" and p.get("liste") is True
    if liste and not _pozitif_tam(p.get("satir_max")):
        hatalar.append("metin-satir-max:%s.%s" % (kayit_kod, ad))
    adim = None
    if tip == "tam" or (tip == "sayi" and p.get("tam") is True):
        adim = 1
    elif tip == "sayi":
        adim = p.get("adim") or KONUM_ADIM.get(ad, VARSAYILAN_ADIM)
        if "min" not in p or "max" not in p:
            hatalar.append("sayi-araliksiz:%s.%s" % (kayit_kod, ad))
    for k, v in p.items():
        if k in ("ad", "tip", "tam", "adim"):
            continue
        if tip == "metin" and k == "karakter_max":
            k = "max"
        alan[k] = v
        if k == "max" and adim is not None:
            alan["adim"] = adim
    if adim is not None and "adim" not in alan:
        alan["adim"] = adim
    if tip == "metin":
        if "max" in alan and not _pozitif_tam(alan["max"]):
            hatalar.append("metin-tavani-bicimi:%s.%s" % (kayit_kod, ad))
        if "max" not in alan:
            tavan = alan.pop("uzunluk_max", None) or metin_tavani((sema or {}).get(ad))
            if tavan is None:
                hatalar.append("metin-tavani-yok:%s.%s" % (kayit_kod, ad))
            else:
                alan["max"] = tavan
        if p.get("zorunlu") is not True:
            alan["zorunlu"] = False
    var, v = ornek_degeri(ornek_girdi, ad)
    if var:
        alan["ornek"] = v
    return alan, None


def _pozitif_tam(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def _palet_uret(kayit_kod, p, hatalar):
    """renk_liste parametresi -> palet renk tavani N (1..RENK_LISTE_TAVAN) ya da None (KIRMIZI yazilir)."""
    n = p.get("uzunluk_max")
    if not _pozitif_tam(n) or n > RENK_LISTE_TAVAN:
        hatalar.append("renk-liste-tavani:%s.%s=%r" % (kayit_kod, p.get("ad"), n))
        return None
    if p.get("oge") != RENK_LISTE_OGE:
        hatalar.append("renk-liste-oge:%s.%s=%r" % (kayit_kod, p.get("ad"), p.get("oge")))
        return None
    return n


def satir_uret(kayit, parametreler=None, kod=None, girdi_tipi=None, sema=None):
    """TEK fonksiyon: kayit -> manifest satirinin TURETILEN alanlari. Hata listesi ikinci donus."""
    hatalar = []
    kod = kod or kayit.get("kod")
    girdi_tipi = girdi_tipi if girdi_tipi is not None else (kayit.get("girdi_tipi") or [])
    girdi = []
    for g in girdi_tipi:
        if g not in GIRDI_ESLE:
            hatalar.append("bilinmeyen-girdi:%s=%s" % (kod, g))
        else:
            girdi.append(GIRDI_ESLE[g])
    form, bolgeler, palet = {}, [], None
    ornek_girdi = (kayit.get("ornek") or {}).get("girdi") if isinstance(kayit.get("ornek"), dict) else None
    for p in (parametreler if parametreler is not None else (kayit.get("parametreler") or [])):
        if p.get("tip") == "renk_liste":
            if palet is not None:
                hatalar.append("renk-liste-cift:%s.%s" % (kod, p.get("ad")))
            palet = _palet_uret(kod, p, hatalar) or 0
            continue
        alan, bolge = _alan_uret(kod, girdi_tipi, p, hatalar, sema, ornek_girdi)
        if alan is not None:
            form[p["ad"]] = alan
        if bolge is not None:
            bolge["renkler"] = list(RENK_ACIK_ONCE if len(bolgeler) % 2 == 0 else RENK_KOYU_ONCE)
            bolgeler.append(bolge)
    for ad, alan in form.items():
        for k in alan.get("kosul") or []:
            if not isinstance(k, dict) or k.get("alan") not in form or not isinstance(k.get("degerler"), list):
                hatalar.append("kosul-alan:%s.%s->%s" % (kod, ad, k.get("alan") if isinstance(k, dict) else k))
    if palet and bolgeler:
        hatalar.append("renk-liste-bolge-karisik:%s" % kod)
    o = kayit.get("olcek") or {}
    satir = {"girdi": girdi, "uretec": kayit.get("uretec") or "",
             "olcu_mm": {"en_az": o.get("min_mm"), "en_cok": o.get("max_mm")},
             "renk_bolgeleri": bolgeler,
             # Okan 9 Eki: foto programinda malzeme YALNIZ PLA/PETG (VERI.MALZEMELER) — kopru izinli listesi suzulur.
             "malzemeler": {"govde": [m for m in (kayit.get("izinli_malzeme") or []) if m in FOTO_MALZEMELERI]},
             "form": form,
             "olcu_ekseni": "sabit" if o.get("belirleyen_parametre") else "turetilmis",
             "fiyat_adim_mm": o.get("adim_mm"),
             # RENK TAVANI (BaBa 8 Eki 15:4x) = uretecin BOYANABILIR renk_* parametre sayisi (en az 1); YAZILMAZ,
             # --denetle manifest fiyat.renk_tavani'yi buna karsi olcer.
             # PALET (renk_liste): tavan = listenin uzunluk_max'i; renkler[i] -> palet_bolgeleri[i] (VERI.paletBolgeRenkleri).
             "renk_tavani": palet or max(1, len(bolgeler)),
             "renk_secimi": "palet" if palet else None,
             "palet_bolgeleri": ["renk%d" % (i + 1) for i in range(palet)] if palet else None,
             "foto_kolu": None,
             # DINAMIK MIN (BaBa 14:3x / TeKiN 6320f2a): olcek.min_mm_dinamik -> manifest olcu_min_dinamik: true
             # (yalniz true iken yazilir); koşucu onizlemede `kopru_uret.py min-hesapla` sorar.
             "olcu_min_dinamik": o.get("min_mm_dinamik") is True,
             "kopru_bolgeleri": list(kayit.get("renk_bolgeleri") or []),
             "renk_sonekleri": [b["kod"] for b in bolgeler]}
    return satir, hatalar


def teklif_parametreleri(kayit, hatalar):
    """`tur_tanimi_teklifi.alanlar` -> ana kaydin ayni adli parametresi + teklifin alanlari (ustune)."""
    ana = {p.get("ad"): p for p in kayit.get("parametreler") or []}
    cikti = []
    for a in (kayit.get("tur_tanimi_teklifi") or {}).get("alanlar") or []:
        if a.get("ad") not in ana:
            hatalar.append("teklif-alani-yok:%s.%s" % (kayit.get("kod"), a.get("ad")))
            continue
        p = dict(ana[a["ad"]])
        p.update(a)
        cikti.append(p)
    return cikti


def jenerator_kok(kayit_yolu):
    """`<jen>/jeneratorler/kopru/kopru_kayitlari.json` -> `<jen>` (cagri.betik bu koke goreli).
    Kayit yaninda `uretec_semalari.json` varsa (SABIT kayit) -> o sozluk (dict); uretec deposu GEREKMEZ."""
    sd = os.path.join(os.path.dirname(os.path.abspath(kayit_yolu)), SEMA_DOSYASI)
    if os.path.isfile(sd):
        with open(sd, encoding="utf-8") as f:
            return json.load(f)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(kayit_yolu))))


def uretec_var(jen, betik):
    """Uretec kaynagi bu betigi taniyor mu (dosya ya da sabit sema kaydi)."""
    if not jen or not betik:
        return False
    if isinstance(jen, dict):
        return isinstance(jen.get(betik), dict)
    return os.path.isfile(os.path.join(jen, betik))


def semalari_cikar(kayitlar, jen):
    """Gercek uretec deposundan {betik: {"SEMA": .., <sema_adi>: ..}} (yalniz ast literal; import YOK)."""
    cikti = {}
    for k in kayitlar.get("kayitlar") or []:
        betik = (k.get("cagri") or {}).get("betik")
        yol = os.path.join(jen, betik) if betik else ""
        if not yol or not os.path.isfile(yol):
            continue
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read(), yol)
        ent = cikti.setdefault(betik, {})
        for ad in ("SEMA", k.get("sema_adi")):
            if ad and ad not in ent:
                s = _sozluk_oku(agac, ad)
                if s is not None:
                    ent[ad] = s
    return cikti


def _git(kok, *arg):
    p = subprocess.run(["git", "-C", kok] + list(arg), capture_output=True, text=True)
    return p.returncode, p.stdout.strip()


def sabit_sha(yol=SABIT_SHA):
    try:
        with open(yol, encoding="utf-8") as f:
            m = re.search(r"^KAYNAK_SHA=([0-9a-f]{40})$", f.read(), re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def kayit_tazele(tekin=TEKIN_KOK, dizin=SABIT_DIZIN):
    """TeKiN kaydi -> repoda sabit kopya + sema + KAYNAK_SHA. Kaynak kirliyse (kayit/uretec HEAD'den farkli) RED."""
    kaynak = os.path.join(tekin, TEKIN_KAYIT_GORELI)
    rc, sha = _git(tekin, "rev-parse", "HEAD")
    if rc != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha) or not os.path.isfile(kaynak):
        print("HAL=TAZELE-RED sebep=tekin-deposu-yok kok=%s rc=3" % tekin)
        return 3
    with open(kaynak, "rb") as f:
        ham = f.read()
    kayitlar = json.loads(ham.decode("utf-8"))
    betikler = sorted({(k.get("cagri") or {}).get("betik") for k in kayitlar.get("kayitlar") or []} - {None})
    _, kirli = _git(tekin, "status", "--porcelain", "--", TEKIN_KAYIT_GORELI, *betikler)
    if kirli:
        print("HAL=TAZELE-RED sebep=kaynak-kirli (KAYNAK_SHA ile bayt-esit olmaz) %s rc=3" % kirli.replace("\n", " | "))
        return 3
    semalar = semalari_cikar(kayitlar, tekin)
    os.makedirs(dizin, exist_ok=True)
    with open(os.path.join(dizin, "kopru_kayitlari.json"), "wb") as f:
        f.write(ham)
    with open(os.path.join(dizin, SEMA_DOSYASI), "w", encoding="utf-8") as f:
        json.dump(semalar, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    with open(os.path.join(dizin, "KAYNAK_SHA"), "w", encoding="utf-8") as f:
        f.write("KAYNAK_SHA=%s\n" % sha)
    print("TAZELE kayit=%d bayt betik=%d sema=%d KAYNAK_SHA=%s" % (len(ham), len(betikler),
                                                                 sum(len(v) for v in semalar.values()), sha))
    return 0


def bayat_raporu(tekin=TEKIN_KOK, sha_yolu=SABIT_SHA, kayit_yolu=SABIT_KAYIT):
    """RAPOR satiri (bloklamaz): sabit kayit sha'si TeKiN main'in kac commit gerisinde."""
    sha = sabit_sha(sha_yolu)
    if not sha:
        return "KAYIT_BAYAT=OLCULEMEDI sebep=KAYNAK_SHA-yok"
    rc, ana = _git(tekin, "rev-parse", "--verify", "-q", "main")
    if rc != 0 or not ana:
        return "KAYIT_BAYAT=OLCULEMEDI sebep=tekin-deposu-yok kaynak=%s" % sha[:8]
    rc, n = _git(tekin, "rev-list", "--count", "%s..%s" % (sha, ana))
    if rc != 0:
        return "KAYIT_BAYAT=OLCULEMEDI sebep=KAYNAK_SHA-tekin'de-yok kaynak=%s" % sha[:8]
    rc2, ham = _git(tekin, "show", "%s:%s" % (ana, TEKIN_KAYIT_GORELI))
    try:
        with open(kayit_yolu, encoding="utf-8") as f:
            ayni = rc2 == 0 and json.loads(ham) == json.load(f)
    except (OSError, ValueError):
        ayni = False
    return "KAYIT_BAYAT=%s kaynak=%s tekin_main=%s kayit_icerik=%s" % (n, sha[:8], ana[:8],
                                                                      "AYNI" if ayni else "FARKLI")


def hepsini_uret(kayitlar, jen=None):
    """{tur_kodu: turetilen_satir} (kayit sirasi; teklif turu ana kaydin hemen ardinda) + hatalar.
    `jen` = uretec deposu koku (metin tavani uretec SEMA'sindan); None -> yalniz kayittaki `max`."""
    satirlar, hatalar = {}, []
    if not isinstance(kayitlar, dict) or not isinstance(kayitlar.get("kayitlar"), list):
        raise KayitHatasi("kayit bicimi: {'kayitlar': [...]} degil")
    kollar = []
    for k in kayitlar["kayitlar"]:
        if k.get("kod") in KOL_KAYDI:
            kollar.append(k)
            continue
        sema = uretec_semasi(jen, (k.get("cagri") or {}).get("betik"), k.get("sema_adi"))
        betik = (k.get("cagri") or {}).get("betik")
        # Uretec dosyasi VAR ama `sema_adi` sozlugu yok -> KIRMIZI (dosya yoksa — CI / kopya kayit — eski davranis:
        # metin tavani kayittan).
        if k.get("sema_adi") and sema is None and uretec_var(jen, betik):
            hatalar.append("sema-adi-yok:%s=%s" % (k.get("kod"), k.get("sema_adi")))
        s, h = satir_uret(k, sema=sema)
        satirlar[k.get("kod")] = s
        hatalar += h
        if k.get("tur_tanimi_teklifi"):
            tk = TEKLIF_KOD.get(k.get("kod"))
            if not tk:
                hatalar.append("teklif-kodu-yok:%s" % k.get("kod"))
                continue
            tf = k["tur_tanimi_teklifi"]
            s2, h2 = satir_uret(k, parametreler=teklif_parametreleri(k, hatalar), kod=tk,
                                girdi_tipi=[tf.get("girdi")] if isinstance(tf.get("girdi"), str) else tf.get("girdi"),
                                sema=sema)
            # Teklif turu (bust) ana kaydin uretecini kosar: boyanabilir renk sayisi ANA kayittan (rolyef kolu).
            s2["renk_tavani"], s2["kopru_bolgeleri"], s2["renk_sonekleri"] = s["renk_tavani"], [], []
            satirlar[tk] = s2
            hatalar += h2
    for k in kollar:
        ana = satirlar.get(KOL_KAYDI[k["kod"]])
        s, h = satir_uret(k)
        hatalar += h
        if ana is None:
            hatalar.append("kol-ana-yok:%s->%s" % (k["kod"], KOL_KAYDI[k["kod"]]))
            continue
        ana["foto_kolu"] = {"girdi": s["girdi"], "uretec": k.get("uretec") or ""}
    return satirlar, hatalar


# ---------------------------------------------------------------- JS yazimi (manifest bicemi)
def _sayi(v):
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        s = repr(v)
        if "e" in s:
            s = ("%.12f" % v).rstrip("0").rstrip(".")
        return s
    return str(v)


def _anahtar(k):
    return k if re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", k) else json.dumps(k, ensure_ascii=False)


def _satirici(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return _sayi(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(_satirici(x) for x in v) + "]"
    return "{ " + ", ".join("%s: %s" % (_anahtar(k), _satirici(x)) for k, x in v.items()) + " }" if v else "{}"


def _yalin(v):
    return not isinstance(v, (dict, list)) or (isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v))


def js(v, girinti):
    """Manifest bicemi: skaler dizi, <=80 karakterlik dizi ve <=60 karakterlik duz nesne (form alani
    HARIC: `tip` tasiyan nesne hep alt alta) tek satir; gerisi alt alta."""
    if isinstance(v, dict):
        tek = _satirici(v)
        if not v or (all(_yalin(x) for x in v.values()) and len(tek) <= 60 and "tip" not in v):
            return tek
        ic = " " * (girinti + 2)
        return "{\n" + ",\n".join("%s%s: %s" % (ic, _anahtar(k), js(x, girinti + 2)) for k, x in v.items()) + \
            "\n" + " " * girinti + "}"
    if isinstance(v, list):
        tek = _satirici(v)
        if not v or all(not isinstance(x, (dict, list)) for x in v) or len(tek) <= 80:
            return tek
        ic = " " * (girinti + 2)
        return "[\n" + ",\n".join(ic + js(x, girinti + 2) for x in v) + "\n" + " " * girinti + "]"
    return _satirici(v)


# ---------------------------------------------------------------- manifest okuma/yazma
def manifest_oku(yol):
    p = subprocess.run(["node", "-e", NODE_OKU, yol], capture_output=True, text=True)
    if p.returncode != 0:
        raise KayitHatasi("manifest okunamadi: " + p.stderr.strip()[:300])
    return json.loads(p.stdout)


def satir_birlestir(mevcut, uretilen):
    """Mevcut satirin anahtar sirasi korunur; TURETILEN alanlar ve fiyat.adim_mm uretimden."""
    s = {}
    for k, v in mevcut.items():
        if k in OPSIYONEL and uretilen.get(k) is None:
            continue
        if k in TURETILEN:
            s[k] = uretilen[k]
        elif k == "fiyat" and isinstance(v, dict):
            s[k] = dict(v, adim_mm=uretilen["fiyat_adim_mm"])
        elif k == "olcu_min_dinamik":
            continue
        else:
            s[k] = v
    for k in TURETILEN:
        if k not in s and not (k in OPSIYONEL and uretilen.get(k) is None):
            s[k] = uretilen[k]
    if uretilen.get("olcu_min_dinamik"):
        s["olcu_min_dinamik"] = True
    return s


def satir_araligi(satirlar, kod):
    """turler dizisinde `kod: "<kod>",` satirini tasiyan nesnenin [bas, son] satir indeksleri."""
    for i, l in enumerate(satirlar):
        if l == '        kod: "%s",\n' % kod and i > 0 and satirlar[i - 1] == "      {\n":
            for j in range(i + 1, len(satirlar)):
                if satirlar[j] in ("      },\n", "      }\n"):
                    return i - 1, j
    return None


def yaz(manifest_yol, uretilen):
    m = manifest_oku(manifest_yol)
    turler = {t.get("kod"): t for t in m.get("turler") or []}
    with open(manifest_yol, encoding="utf-8") as f:
        satirlar = f.readlines()
    degisen, eksik = [], []
    for kod, u in uretilen.items():
        if kod not in turler:
            eksik.append(kod)
            continue
        ar = satir_araligi(satirlar, kod)
        if ar is None:
            eksik.append(kod)
            continue
        bas, son = ar
        virgul = "," if satirlar[son].rstrip("\n").endswith(",") else ""
        yeni = (" " * 6 + js(satir_birlestir(turler[kod], u), 6) + virgul + "\n").splitlines(True)
        if satirlar[bas:son + 1] != yeni:
            satirlar[bas:son + 1] = yeni
            degisen.append(kod)
    if degisen:
        gecici = manifest_yol + ".kopru-uret.tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            f.writelines(satirlar)
        os.replace(gecici, manifest_yol)
    return degisen, eksik


def denetle(manifest_yol, uretilen, hatalar, bilgi=None):
    """KIRMIZI listesi. RENK EKSENI (BaBa 8 Eki 15:4x): fiyat.renk_tavani == boyanabilir renk_* sayisi; renk_<sonek>
    soneki kopru `renk_bolgeleri`nde olmali (ad sapmasi KIRMIZI); parametresiz kopru bolgesi KIRMIZI DEGIL, `bilgi`ye
    (TeKiN renk_<b> ekleyince tavan aractan yukselir)."""
    m = manifest_oku(manifest_yol)
    turler = {t.get("kod"): t for t in m.get("turler") or []}
    renk_hex = m.get("renk_hex") or {}
    kirmizi = list(hatalar)
    for ad in RENK_ACIK_ONCE + RENK_KOYU_ONCE:
        if ad not in renk_hex:
            kirmizi.append("renk-tablo-disi:%s" % ad)
    for kod, u in uretilen.items():
        t = turler.get(kod)
        if t is None:
            kirmizi.append("tur-yok:%s" % kod)
            continue
        for k in TURETILEN:
            if json.dumps(t.get(k), sort_keys=True) != json.dumps(_js_esdeger(u.get(k)), sort_keys=True):
                kirmizi.append("sapma:%s.%s%s" % (kod, k, _ilk_fark(t.get(k), u[k])))
        if (t.get("fiyat") or {}).get("adim_mm") != u["fiyat_adim_mm"]:
            kirmizi.append("sapma:%s.fiyat.adim_mm" % kod)
        if (t.get("olcu_min_dinamik") is True) != (u.get("olcu_min_dinamik") is True):
            kirmizi.append("sapma:%s.olcu_min_dinamik manifest=%s kopru=%s" % (
                kod, t.get("olcu_min_dinamik") is True, u.get("olcu_min_dinamik") is True))
        if (t.get("fiyat") or {}).get("renk_tavani") != u["renk_tavani"]:
            kirmizi.append("sapma:%s.fiyat.renk_tavani manifest=%s kopru=%s" % (
                kod, (t.get("fiyat") or {}).get("renk_tavani"), u["renk_tavani"]))
        kb = u.get("kopru_bolgeleri") or []
        if kb:
            for s in u.get("renk_sonekleri") or []:
                if s not in kb:
                    kirmizi.append("renk-bolge-adi:%s.renk_%s kopru_bolgeleri=%s" % (kod, s, ",".join(kb)))
            for b in kb:
                if b not in (u.get("renk_sonekleri") or []) and bilgi is not None:
                    bilgi.append("boyanamaz-bolge:%s.%s (renk_%s parametresi yok)" % (kod, b, b))
    return kirmizi


def _js_esdeger(v):
    """Python degerini node JSON ciktisina denk yap (2.0 -> 2)."""
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, list):
        return [_js_esdeger(x) for x in v]
    if isinstance(v, dict):
        return {k: _js_esdeger(x) for k, x in v.items()}
    return v


def _ilk_fark(a, b):
    b = _js_esdeger(b)
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(b) + [k for k in a if k not in b]:
            if json.dumps(a.get(k), sort_keys=True) != json.dumps(b.get(k), sort_keys=True):
                return "." + k + _ilk_fark(a.get(k), b.get(k))
    return ""


def main():
    ap = argparse.ArgumentParser(description="TeKiN kopru kayitlari -> manifest tur satirlari")
    ap.add_argument("--kayit", default=os.environ.get("KOPRU_KAYIT") or VARSAYILAN_KAYIT)
    ap.add_argument("--manifest", default=os.path.join(KOK, "foto-uretim-veri.js"))
    kip = ap.add_mutually_exclusive_group()
    kip.add_argument("--yaz", action="store_true")
    kip.add_argument("--denetle", action="store_true")
    kip.add_argument("--kayit-tazele", action="store_true")
    kip.add_argument("--bayat", action="store_true")
    a = ap.parse_args()
    if a.bayat:
        print(bayat_raporu())
        return 0
    if a.kayit_tazele:
        rc = kayit_tazele()
        if rc:
            return rc
        a.kayit, a.yaz = SABIT_KAYIT, True
    try:
        with open(a.kayit, encoding="utf-8") as f:
            kayitlar = json.load(f)
    except (OSError, ValueError) as e:
        print("HAL=KAYIT-YOK yol=%s sebep=%s rc=3" % (a.kayit, e.__class__.__name__))
        return 3
    try:
        uretilen, hatalar = hepsini_uret(kayitlar, jenerator_kok(a.kayit))
        if a.denetle:
            bilgi = []
            kirmizi = denetle(a.manifest, uretilen, hatalar, bilgi)
            for k in bilgi:
                print("BILGI " + k)
            for k in kirmizi:
                print("KIRMIZI " + k)
            print("DENETLE=%s tur=%d kirmizi=%d rc=%d" % ("YESIL" if not kirmizi else "KIRMIZI", len(uretilen),
                                                          len(kirmizi), 1 if kirmizi else 0))
            return 1 if kirmizi else 0
        if hatalar:
            for h in hatalar:
                print("KIRMIZI " + h)
            print("URETIM=RED hata=%d rc=1" % len(hatalar))
            return 1
        if a.yaz:
            degisen, eksik = yaz(a.manifest, uretilen)
            for k in eksik:
                print("KIRMIZI tur-yok:%s (editoryal alanlar elle eklenmeli)" % k)
            print("YAZ degisen=%d [%s] eksik=%d rc=%d" % (len(degisen), ",".join(degisen), len(eksik), 1 if eksik else 0))
            return 1 if eksik else 0
        json.dump(uretilen, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0
    except KayitHatasi as e:
        print("HAL=KAYIT-BOZUK %s rc=3" % e)
        return 3


if __name__ == "__main__":
    sys.exit(main())

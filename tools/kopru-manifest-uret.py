#!/usr/bin/env python3
"""KOPRU MANIFEST URETECI (kopru-15 DILIM-2, 8 Eki 2026) — TeKiN `kopru_kayitlari.json` -> foto-uretim-veri.js
tur satirlari, DETERMINISTIK ve TEK fonksiyonla (`satir_uret`).

NEDEN: 15 kopru turunun manifest satirlari elle/m3 kopyasiyla yazilmisti; TeKiN `kosul` metadatasi ve
surekli `sayi` alanlarinin `adim`i tasinmamisti -> G4a ② `uretec-red:genel` x4. Satirlar artik BU
araçtan turetilir; `--denetle` manifest kayittan saparsa adiyla KIRMIZI yakar (CI'da test uzerinden).

SOZLUK (eşleme YALNIZ burada; manifest yorumu bu dosyayi isaret eder):
  girdi   : olcu -> "form" · foto -> "foto-1" · ses/metin/konum/tarih aynen · baska -> KIRMIZI
  tip     : sayi -> sayi + adim (kayittaki `adim`, yoksa 0.01; enlem/boylam 0.000001)
            tam (ya da sayi + `tam:true`) -> sayi + adim 1
            renk -> form DEGIL, renk_bolgeleri (`renk_<b>` -> {kod:<b>, ad:<etiket - " rengi">, renkler})
            dosya -> form DISI (girdinin kendisi) · bool/secim aynen
            metin -> aynen + `max` (kayitta yoksa URETECIN `SEMA[ad]` uzunluk tavani: str->uzunluk_max,
            yoksa uretec varsayilani 1000; liste->oge.uzunluk_max; ast ile okunur, uretec KOSMAZ; uretec
            dosyasi/alani yok -> KIRMIZI) + `zorunlu:true` degilse `zorunlu:false` (bos/yok = uretec
            varsayilani). NEDEN (kopru-15 ESLE): max'siz metin alanini VERI.parametreDogrula her degerde
            `parametre-metin` ile reddediyordu (braille ⑤ 400).
            ses girdili kaydin min/max'siz `sayi` alani (genlik dizisi) -> tip "ses"
            baska tip -> KIRMIZI
  kosul   : form alaninda `kosul: [{alan, degerler}]` AYNEN (alan formda olmali, yoksa KIRMIZI)
  olcu_mm : olcek.min_mm/max_mm · fiyat.adim_mm : olcek.adim_mm · malzemeler : {govde: izinli_malzeme}
  olcu_ekseni : olcek.belirleyen_parametre DOLU -> "sabit" (surgu = hedef) · bos/null -> "turetilmis"
            (kopru-15 dilim-3: surgu YOK, fiyat onizlemede OLCULEN uzun kenardan; sunucu kaydindan)
  bust    : rolyef `tur_tanimi_teklifi` (alanlar rolyef parametresinin ustune yazilir, sonra ayni sozluk)
Editoryal alanlar (ad, aciklama, motor, fiyat.formul, ornek_kanit_izni, durustluk, ornek_notu) manifestte
elle kalir; arac yalniz TURETILEN alanlari yazar/denetler.

KULLANIM
  python3 tools/kopru-manifest-uret.py               # uretilen satirlari JSON basar (yazmaz)
  python3 tools/kopru-manifest-uret.py --yaz         # 15 satiri manifestte yeniden yazar (idempotent)
  python3 tools/kopru-manifest-uret.py --denetle     # manifest == uretim mi? rc 0 YESIL · 1 KIRMIZI · 3 kayit yok
  --kayit <yol> (varsayilan KOPRU_KAYIT ya da ~/dev/pruvo-jenerator/jeneratorler/kopru/kopru_kayitlari.json)
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
VARSAYILAN_KAYIT = os.path.expanduser("~/dev/pruvo-jenerator/jeneratorler/kopru/kopru_kayitlari.json")

GIRDI_ESLE = {"olcu": "form", "foto": "foto-1", "ses": "ses", "metin": "metin", "konum": "konum", "tarih": "tarih"}
BILINEN_TIP = ("sayi", "tam", "secim", "metin", "bool", "renk", "dosya")
KONUM_ADIM = {"enlem": 0.000001, "boylam": 0.000001}
VARSAYILAN_ADIM = 0.01
# Bolge renk listeleri (sunum kurali, kayitta YOK): cift sirali bolge acik-once, tek sirali koyu-once ->
# iki bolgenin ilk (varsayilan) renkleri farkli. Adlar manifest RENK_HEX'te olmali (--denetle olcer).
RENK_ACIK_ONCE = ["Beyaz", "Gri", "Ahşap", "Sarı", "Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi"]
RENK_KOYU_ONCE = ["Siyah", "Lacivert", "Kırmızı", "Yeşil", "Mavi", "Gri", "Beyaz", "Sarı", "Ahşap"]
TEKLIF_KOD = {"rolyef": "bust"}  # tur_tanimi_teklifi -> manifest tur kodu
TURETILEN = ("girdi", "uretec", "olcu_mm", "renk_bolgeleri", "malzemeler", "form", "olcu_ekseni")

NODE_OKU = (
    "const vm=require('vm'),fs=require('fs');const k={};"
    "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});"
    "process.stdout.write(JSON.stringify({turler:k.PRUVO_FOTO.turler,renk_hex:k.PRUVO_FOTO.RENK_HEX}));"
)


class KayitHatasi(Exception):
    pass


def uretec_semasi(jen, betik):
    """Uretec dosyasindaki ust duzey `SEMA = {...}` -> {alan: {anahtar: deger}} (ast; YALNIZ literal degerler,
    `float(ARALIK_MAX_MM)` gibi literal olmayanlar atlanir). Dosya/SEMA yok -> None. Uretec import EDILMEZ."""
    yol = os.path.join(jen, betik) if jen and betik else ""
    if not yol or not os.path.isfile(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        agac = ast.parse(f.read(), yol)
    for d in agac.body:
        if (isinstance(d, ast.Assign) and isinstance(d.value, ast.Dict)
                and any(isinstance(t, ast.Name) and t.id == "SEMA" for t in d.targets)):
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


def _alan_uret(kayit_kod, girdiler, p, hatalar, sema=None):
    """Tek kayit parametresi -> (form_alani | None, renk_bolgesi | None). `sema` = uretec SEMA (metin tavani)."""
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
        alan[k] = v
        if k == "max" and adim is not None:
            alan["adim"] = adim
    if adim is not None and "adim" not in alan:
        alan["adim"] = adim
    if tip == "metin":
        if "max" not in alan:
            tavan = alan.pop("uzunluk_max", None) or metin_tavani((sema or {}).get(ad))
            if tavan is None:
                hatalar.append("metin-tavani-yok:%s.%s" % (kayit_kod, ad))
            else:
                alan["max"] = tavan
        if p.get("zorunlu") is not True:
            alan["zorunlu"] = False
    return alan, None


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
    form, bolgeler = {}, []
    for p in (parametreler if parametreler is not None else (kayit.get("parametreler") or [])):
        alan, bolge = _alan_uret(kod, girdi_tipi, p, hatalar, sema)
        if alan is not None:
            form[p["ad"]] = alan
        if bolge is not None:
            bolge["renkler"] = list(RENK_ACIK_ONCE if len(bolgeler) % 2 == 0 else RENK_KOYU_ONCE)
            bolgeler.append(bolge)
    for ad, alan in form.items():
        for k in alan.get("kosul") or []:
            if not isinstance(k, dict) or k.get("alan") not in form or not isinstance(k.get("degerler"), list):
                hatalar.append("kosul-alan:%s.%s->%s" % (kod, ad, k.get("alan") if isinstance(k, dict) else k))
    o = kayit.get("olcek") or {}
    satir = {"girdi": girdi, "uretec": kayit.get("uretec") or "",
             "olcu_mm": {"en_az": o.get("min_mm"), "en_cok": o.get("max_mm")},
             "renk_bolgeleri": bolgeler,
             "malzemeler": {"govde": list(kayit.get("izinli_malzeme") or [])},
             "form": form,
             "olcu_ekseni": "sabit" if o.get("belirleyen_parametre") else "turetilmis",
             "fiyat_adim_mm": o.get("adim_mm")}
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
    """`<jen>/jeneratorler/kopru/kopru_kayitlari.json` -> `<jen>` (cagri.betik bu koke goreli)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(kayit_yolu))))


def hepsini_uret(kayitlar, jen=None):
    """{tur_kodu: turetilen_satir} (kayit sirasi; teklif turu ana kaydin hemen ardinda) + hatalar.
    `jen` = uretec deposu koku (metin tavani uretec SEMA'sindan); None -> yalniz kayittaki `max`."""
    satirlar, hatalar = {}, []
    if not isinstance(kayitlar, dict) or not isinstance(kayitlar.get("kayitlar"), list):
        raise KayitHatasi("kayit bicimi: {'kayitlar': [...]} degil")
    for k in kayitlar["kayitlar"]:
        sema = uretec_semasi(jen, (k.get("cagri") or {}).get("betik"))
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
            satirlar[tk] = s2
            hatalar += h2
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
        if k in TURETILEN:
            s[k] = uretilen[k]
        elif k == "fiyat" and isinstance(v, dict):
            s[k] = dict(v, adim_mm=uretilen["fiyat_adim_mm"])
        else:
            s[k] = v
    for k in TURETILEN:
        if k not in s:
            s[k] = uretilen[k]
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


def denetle(manifest_yol, uretilen, hatalar):
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
            if json.dumps(t.get(k), sort_keys=True) != json.dumps(_js_esdeger(u[k]), sort_keys=True):
                kirmizi.append("sapma:%s.%s%s" % (kod, k, _ilk_fark(t.get(k), u[k])))
        if (t.get("fiyat") or {}).get("adim_mm") != u["fiyat_adim_mm"]:
            kirmizi.append("sapma:%s.fiyat.adim_mm" % kod)
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
    a = ap.parse_args()
    try:
        with open(a.kayit, encoding="utf-8") as f:
            kayitlar = json.load(f)
    except (OSError, ValueError) as e:
        print("HAL=KAYIT-YOK yol=%s sebep=%s rc=3" % (a.kayit, e.__class__.__name__))
        return 3
    try:
        uretilen, hatalar = hepsini_uret(kayitlar, jenerator_kok(a.kayit))
        if a.denetle:
            kirmizi = denetle(a.manifest, uretilen, hatalar)
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

#!/usr/bin/env python3
"""KABUL: KOPRU ESLEME SINIF KAPISI (kopru-15 ESLE, 8 Eki 2026) — `tools/foto-uretec-kosucu.py` esle_<kod>
ciktisini uretec kabul eder mi + sunucu (VERI.parametreDogrula) ornek parametreyi kabul eder mi.

NEDEN: braille ②④ `RET: bilinmeyen alan: uzun_kenar_mm` (esleme uretecin tanimadigi alani gonderdi) ve
⑤ `400/parametre-metin` (kayitta `max`'siz metin alani -> sunucu HER metni reddetti) ancak canli kosumda
(render + R2 + D1, tur basina) yakalaniyordu. Bu kapi SINIFI hermetik yakalar; alan kumesi sabit liste
DEGIL, kayittan / uretec dosyasindan TURETILIR.

IKI KATMAN
  S (HERMETIK, CI'da kosar; node + bu agacin manifesti): ESLEMELER'deki her manifest turu icin
     S1 `foto-ornek-uc-uca.ornek_parametre` (⑤'in gonderdigi AYNI parametre) -> parametreDogrula ok=true
     S2 `varsayilan:""` metin alani GONDERILMEYINCE ok=true (istege bagli metin; bos = uretec varsayilani)
     O1 on adimli uretec (G5 topo: veri_cek.py) on adima URETEC JSON'unu verir, §2 zarfini DEGIL (sahte on adim +
        sahte uretec gecici dizinde; zarf anahtari gorurse RET -> `RED on-adim`)
     S3 istege bagli metin alanlari DOLU ("PRUVO") gonderilince ok=true (E bu parametreyle kosar -> alan donusumu
        da olculur)
  E (sinif-r-k80 9 Eki: repodaki SABIT kayit jenerator/kopru/ + uretec_semalari.json -> CI'da da KOSAR;
     kayit yoksa `ESLE=KIRMIZI kayit-yok` + MA/MS2 SURVIVOR — ATLANDI YOK; `KOPRU_KAYIT` env elle karsilastirma):
     her kopru kaydi (+ teklif turu bust) icin S1'in DOGRULANMIS parametresi + ornek dosya/renk -> esle_<kod>:
     E1 ALAN  cikti anahtarlari ⊆ kayit `parametreler` adlari ∪ cagri bayrak adlari ∪ cagri `sabit` anahtarlari
     E2 TIP   her deger uretecin `SEMA[alan]` kuralina uyar (uretec dosyasindan ast; kayit `sema_adi` doluysa o
              sozluk SEMA'nin ustune — anahtarlik ANAHTARLIK_SEMA; uretec_ortak._deger_dogrula aynasi; SEMA'da
              olmayan alan = uretec `bilinmeyen alan` RET'i)
     E3 EKSEN `olcek.belirleyen_parametre` dolu -> cikti[belirleyen] == zarfin olcu_mm'i (surgu = hedef olcu)
     E4 RENK  donen bolgeler ⊆ manifest renk_bolgeleri ∪ palet_bolgeleri (bust, yapboz); zarfa palet
              bolgelerinin renkleri de konur (odenen palet rengi esleyiciye ULASIR)
              + PALET-EKSIK: palet turunde palet_bolgeleri < fiyat.renk_tavani · RENK-DUSTU: renkli palet bolgesi
              esleme donusunde yok
     E5 SABIT kayit `cagri.sabit` (anahtarlik: true) ciktida AYNEN (eksikse uretec plaka modunda basar)
MUTANTLAR (gecici kopyada; calisma agacina YAZMAZ). K3c: kalan kopru turleri yapboz + anahtarlik; silinen
braille/topo/yildiz/koordinat capali mutantlar bu iki turun capalarina tasindi (null/no-op YASAK). On adimli
(G5 veri_cek) ve "0 = uretec varsayilani" (G5_SIFIR_VARSAYILAN) turu kalmadi -> O1/Z katmanlari bos kosar,
eski MA6/MA7 SILINDI (capasi olan tur yok).
  MA1 esle_anahtarlik'e uzun_kenar_mm eklendi -> E1 ALAN-DISI anahtarlik.uzun_kenar_mm
  MA2 anahtarlik satirlar listesi tek dizeye birlestirildi -> E2 TIP anahtarlik.satirlar
  MA3 G5 surgu olcusu belirleyen alana yazilmiyor -> E3 EKSEN anahtarlik.genislik_mm
  MA3b yapboz surgu olcusu yazilmiyor -> E3 EKSEN yapboz.uzun_kenar_mm
  MA4 renk on eki bozuk -> E1 ALAN-DISI anahtarlik.renk-
  MA5 anahtarlik sabiti (anahtarlik:true) silindi -> E5 SABIT anahtarlik.anahtarlik
  MA6 yapboz palet listesi baska alana yaziliyor -> E1 ALAN-DISI yapboz.renk_listesi
  MS1 manifestte anahtarlik satirlar `max` silindi -> S1 SUNUCU-RED anahtarlik=parametre-metin
  MS2 manifestte anahtarlik satirlar `liste:true` silindi -> SUNUCU-RED anahtarlik / E2 TIP anahtarlik.satirlar
  MS3 manifestte yapboz palet_bolgeleri silindi -> E4 PALET-EKSIK yapboz
  MA0 kontrol: yorum eklendi -> 0 kirmizi
Cikti son satiri: VAKA_KIRMIZI=<n> SURVIVOR=<n>   (rc 0 yalniz ikisi de 0)
"""
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOSUCU = os.path.join(KOK, "tools", "foto-uretec-kosucu.py")
MANIFEST = os.path.join(KOK, "foto-uretim-veri.js")
GERCEK_KAYIT = os.environ.get("KOPRU_KAYIT") or os.path.join(KOK, "jenerator", "kopru", "kopru_kayitlari.json")

NODE = (
    "const vm=require('vm'),fs=require('fs');const k={};"
    "vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});"
    "const V=k.PRUVO_FOTO;const g=JSON.parse(fs.readFileSync(0,'utf8')||'null');"
    "if(!g){process.stdout.write(JSON.stringify(V.turler));}else{const o={};"
    "for(const a in g){o[a]=V.parametreDogrula(g[a][0],g[a][1]);}process.stdout.write(JSON.stringify(o));}"
)


def modul(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


ORNEK = modul("foto_ornek_uc_uca", os.path.join(KOK, "tools", "foto-ornek-uc-uca.py"))
URET = modul("kopru_manifest_uret", os.path.join(KOK, "tools", "kopru-manifest-uret.py"))


def node(manifest, girdi=None):
    p = subprocess.run(["node", "-e", NODE, manifest], input=json.dumps(girdi) if girdi is not None else "",
                       capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise SystemExit("node: " + p.stderr.strip()[:300])
    return json.loads(p.stdout)


# ------------------------------------------------------------------ S: sunucu kabulu (hermetik)
def s_katmani(manifest, kodlar):
    """-> (kirmizi listesi, {kod: dogrulanmis parametre}, {kod: manifest satiri})."""
    turler = {t.get("kod"): t for t in node(manifest) if isinstance(t, dict)}
    kirmizi, sorgu = [], {}
    for kod in sorted(kodlar):
        t = turler.get(kod)
        if not t:
            continue
        p, hata = ORNEK.ornek_parametre(t, (t.get("olcu_mm") or {}).get("en_az"))
        if p is None:
            kirmizi.append("ORNEK-YOK %s=%s" % (kod, hata))
            continue
        sorgu[kod] = [kod, p]
        dolu = dict(p)
        for ad, s in (t.get("form") or {}).items():
            if s.get("tip") == "metin" and s.get("varsayilan") == "":
                sorgu["%s-bos.%s" % (kod, ad)] = [kod, {k: v for k, v in p.items() if k != ad}]
            if s.get("tip") == "metin" and ad not in p and ORNEK.kosul_tamam(s, p):
                dolu[ad] = "PRUVO"[:s.get("max") or 5]
        if dolu != p:
            sorgu["%s-dolu" % kod] = [kod, dolu]
    sonuc = node(manifest, sorgu) if sorgu else {}
    deger = {}
    for a, r in sorted(sonuc.items()):
        if not r.get("ok"):
            kirmizi.append("SUNUCU-RED %s=%s" % (a, r.get("hata")))
        elif a in turler and a not in deger:
            deger[a] = r.get("deger")
        if r.get("ok") and a.endswith("-dolu"):
            deger[a[:-len("-dolu")]] = r.get("deger")
    return kirmizi, deger, turler


def sifir_katmani(kos, deger):
    """Z: G5 "0 = uretec varsayilani" savunmasi (G5_SIFIR_VARSAYILAN) uretece 0 GECIRMEZ. 8 Eki: manifest
    yenilemesi (2492ac66) iki alanin formunu min >= 1 yapti -> dogrulanmis girdiyle 0 gelemiyor, MA6 S/E
    katmaninda esdeger kaldi; savunma kosucu girisinde (dogrulanmamis zarf) DOGRUDAN olculur."""
    kirmizi = []
    rh = kos.renk_tablosu()
    for kod, alanlar in sorted(getattr(kos, "G5_SIFIR_VARSAYILAN", {}).items()):
        if kod not in deger or kod not in kos.ESLEMELER:
            continue
        d = tempfile.mkdtemp(prefix="esle-sifir-")
        try:
            g = {"tur": kod, "olcu_mm": 100, "parametreler": dict(deger[kod], **{a: 0 for a in alanlar}),
                 "dosyalar": _dosyalar(d), "renkler": {}}
            u, _ = kos.ESLEMELER[kod](g, d, rh)
            kirmizi += ["SIFIR-GECTI %s.%s" % (kod, a) for a in alanlar if a in u]
        except kos.KopruRed as e:
            kirmizi.append("SIFIR-RED %s=%s" % (kod, e.kod))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    return kirmizi


# ------------------------------------------------------------------ E: esleme -> uretec kabulu
def deger_dogrula(ad, v, s):
    """uretec_ortak._deger_dogrula aynasi; semada literal olmayan parca (min/max/secenekler) atlanir."""
    tip = s.get("tip")
    if tip == "bool":
        return None if isinstance(v, bool) else "bool olmali"
    if tip == "int":
        if isinstance(v, bool) or not isinstance(v, int):
            return "tamsayi olmali"
    elif tip == "float":
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            return "sayi olmali"
    elif tip == "str":
        if not isinstance(v, str):
            return "metin olmali"
        return "metin cok uzun" if len(v) > s.get("uzunluk_max", 1000) else None
    elif tip == "enum":
        return "izinli degil: %r" % (v,) if "secenekler" in s and v not in s["secenekler"] else None
    elif tip == "liste":
        if not isinstance(v, list):
            return "liste olmali"
        if len(v) > s.get("uzunluk_max", 10000):
            return "liste cok uzun"
        for i, e in enumerate(v if isinstance(s.get("oge"), dict) else []):
            r = deger_dogrula("%s[%d]" % (ad, i), e, s["oge"])
            if r:
                return r
        return None
    else:
        return None
    if "min" in s and v < s["min"]:
        return "%s < min %s" % (v, s["min"])
    if "max" in s and v > s["max"]:
        return "%s > max %s" % (v, s["max"])
    return None


def _dosyalar(dizin):
    with open(os.path.join(dizin, "foto.png"), "wb") as f:
        f.write(ORNEK.png(64, 48) if hasattr(ORNEK, "png") else b"\x89PNG\r\n\x1a\n")
    with open(os.path.join(dizin, "ses.wav"), "wb") as f:
        f.write(b"RIFF")
    with open(os.path.join(dizin, "logo.svg"), "w", encoding="utf-8") as f:
        f.write(ORNEK.ORNEK_SVG)
    return {"foto": "foto.png", "ses": "ses.wav", "svg": "logo.svg"}


def e_katmani(kosucu, kayitlar, jen, turler, deger):
    """-> (kirmizi listesi, denetlenen tur sayisi, E2 atlanan turler)."""
    kayit = {k.get("kod"): k for k in kayitlar.get("kayitlar") or []}
    atlanan = []
    teklif = {tk: ana for ana, tk in URET.TEKLIF_KOD.items()}
    kirmizi, n = [], 0
    rh = kosucu.renk_tablosu()
    for kod in sorted(kosucu.ESLEMELER):
        k = kayit.get(kod) or kayit.get(teklif.get(kod))
        t = turler.get(kod)
        if not k or not t:
            continue
        n += 1
        cagri = k.get("cagri") or {}
        sabit = cagri.get("sabit") if isinstance(cagri.get("sabit"), dict) else {}
        kabul = {p.get("ad") for p in k.get("parametreler") or []} | set(sabit)
        kabul |= {b[2:] for b in list(cagri.get("bayraklar") or []) +
                  [cagri.get(x) for x in ("girdi_bayragi", "cikti_bayragi", "veri_bayragi")]
                  if isinstance(b, str) and b.startswith("--")}
        sema = URET.uretec_semasi(jen, cagri.get("betik"), k.get("sema_adi"))
        if sema is None and not URET.uretec_var(jen, cagri.get("betik")):
            kirmizi.append("URETEC-YOK %s=%s" % (kod, cagri.get("betik")))
            continue
        if sema is None:
            # G4 ozel_uret: sema olcu_formu.json'dan (ust duzey literal SEMA yok) -> E2 olculemez, ADIYLA basilir.
            atlanan.append(kod)
        o = k.get("olcek") or {}
        bel = o.get("belirleyen_parametre")
        p = dict(deger.get(kod) or {})
        en_az, adim = (t.get("olcu_mm") or {}).get("en_az") or 0, o.get("adim_mm") or 10
        olcu = next(en_az + i * adim for i in range(1, 50) if p.get(bel) != en_az + i * adim)
        d = tempfile.mkdtemp(prefix="esle-")
        try:
            renkler = {b["kod"]: b["renkler"][0] for b in t.get("renk_bolgeleri") or []}
            renkler.update({b: "Beyaz" for b in t.get("palet_bolgeleri") or []})
            g = {"tur": kod, "olcu_mm": olcu, "parametreler": p, "dosyalar": _dosyalar(d), "renkler": renkler}
            try:
                # Uretim yolunun secimi (tekin_kos ile ayni nokta; bust -> esle_bust).
                u, bolgeler = kosucu.esle_fonksiyonu(t, kosucu.cli_tablosu().get(t.get("uretec")))(g, d, rh)
            except kosucu.KopruRed as e:
                kirmizi.append("KOPRU-RED %s=%s" % (kod, e.kod))
                continue
        finally:
            shutil.rmtree(d, ignore_errors=True)
        for a in sorted(u):
            if a not in kabul:
                kirmizi.append("ALAN-DISI %s.%s" % (kod, a))
            elif sema is None:
                continue
            elif a not in sema:
                kirmizi.append("SEMA-DISI %s.%s" % (kod, a))
            else:
                r = deger_dogrula(a, u[a], sema[a])
                if r:
                    kirmizi.append("TIP %s.%s %s" % (kod, a, r))
        for a, v in sorted(sabit.items()):
            if u.get(a) != v:
                kirmizi.append("SABIT %s.%s beklenen=%r gelen=%r" % (kod, a, v, u.get(a)))
        if bel and u.get(bel) != float(olcu):
            kirmizi.append("EKSEN %s.%s beklenen=%s gelen=%s" % (kod, bel, float(olcu), u.get(bel)))
        # Palet turu (bust) bolgeleri manifest palet_bolgeleri'nden (renkler[i] -> palet_bolgeleri[i]).
        izinli = {r["kod"] for r in t.get("renk_bolgeleri") or []} | set(t.get("palet_bolgeleri") or [])
        disi = [b for b in bolgeler if b not in izinli]
        if disi:
            kirmizi.append("RENK %s=%s" % (kod, ",".join(disi)))
        # RENK-DUSTU (K3c): renklendirilen her palet bolgesi uretece gitmeli — yoksa odenen renk sessizce duser.
        # (PALET-EKSIK manifest-yalniz -> palet_katmani; kayitsiz CI'da da kosar.)
        palet = list(t.get("palet_bolgeleri") or [])
        dusen = [b for b in palet if b not in bolgeler]
        if dusen:
            kirmizi.append("RENK-DUSTU %s=%s" % (kod, ",".join(dusen)))
    return kirmizi, n, atlanan


SAHTE_ON_ADIM = (
    "import json,sys\na=sys.argv\ng=json.load(open(a[a.index('--girdi')+1]))\n"
    "z=sorted(set(g)&{'kategori','parametreler','dosyalar','renkler'})\n"
    "if z:\n    sys.stderr.write('RET: bilinmeyen alan: %s\\n' % ', '.join(z)); sys.exit(2)\n"
    "json.dump({}, open(a[a.index('--cikti')+1], 'w'))\n")
SAHTE_URETEC = "import sys\nsys.stderr.write('RET: sahte-uretec-son\\n'); sys.exit(2)\n"


def on_adim_katmani(kosucu, turler, deger):
    """O1: on adimli CLI satiri (manifest uretec -> cli_tablosu) sahte betiklerle; on adim RET'i -> KIRMIZI."""
    kirmizi = []
    for kod in sorted(deger):
        t = turler.get(kod) or {}
        cli = kosucu.cli_tablosu().get(t.get("uretec"))
        if not cli or not cli.get("on_adim"):
            continue
        d = tempfile.mkdtemp(prefix="esle-onadim-")
        try:
            jen = os.path.join(d, "jen")
            for yol, metin in ((cli["on_adim"]["betik"], SAHTE_ON_ADIM), (cli["betik"], SAHTE_URETEC)):
                os.makedirs(os.path.dirname(os.path.join(jen, yol)), exist_ok=True)
                with open(os.path.join(jen, yol), "w", encoding="utf-8") as f:
                    f.write(metin)
            gd = os.path.join(d, "girdi")
            os.makedirs(gd)
            with open(os.path.join(gd, "girdi.json"), "w", encoding="utf-8") as f:
                json.dump({"kategori": kod, "olcu_mm": (t.get("olcu_mm") or {}).get("en_az"), "parametreler": deger[kod],
                           "renkler": {}, "dosyalar": {}}, f)
            rc, oz = kosucu.tekin_kos(cli, t, gd, os.path.join(d, "cikti"), sys.executable, jen)
            if "on-adim" in oz or "sahte-uretec-son" not in oz:
                kirmizi.append("ON-ADIM %s rc=%s %s" % (kod, rc, oz[:120]))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    return kirmizi


def palet_katmani(turler, kodlar):
    """P: PALET-EKSIK (K3c) — fiyatlanan her renk (renk_tavani) bir palet bolgesine baglanmali. Yalniz manifesti
    okur, TeKiN kaydina bagli DEGIL -> kayitsiz CI'da da kosar (9 Eki: E katmaninda durunca SERIT B'de MS3 SURVIVOR)."""
    kirmizi = []
    for kod in sorted(kodlar):
        t = turler.get(kod)
        if not t or t.get("renk_secimi") != "palet" or not t.get("uretec"):
            continue
        palet = list(t.get("palet_bolgeleri") or [])
        tavan = (t.get("fiyat") or {}).get("renk_tavani") or 1
        if len(palet) < tavan:
            kirmizi.append("PALET-EKSIK %s palet_bolgeleri=%d renk_tavani=%s" % (kod, len(palet), tavan))
    return kirmizi


def kayit_oku():
    try:
        with open(GERCEK_KAYIT, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def kapi(kosucu_yolu, manifest, kayitlar):
    """Tum kapi: -> (kirmizi listesi, e_denetlenen | None, E2 atlanan turler)."""
    kos = modul("foto_uretec_kosucu_esle_%d" % abs(hash(kosucu_yolu)), kosucu_yolu)
    kirmizi, deger, turler = s_katmani(manifest, set(kos.ESLEMELER))
    kirmizi += on_adim_katmani(kos, turler, deger)
    kirmizi += sifir_katmani(kos, deger)
    kirmizi += palet_katmani(turler, set(kos.ESLEMELER))
    if kayitlar is None:
        return kirmizi, None, []
    e, n, atlanan = e_katmani(kos, kayitlar, URET.jenerator_kok(GERCEK_KAYIT), turler, deger)
    return kirmizi + e, n, atlanan


# ------------------------------------------------------------------ mutantlar
def _degistir(metin, eski, yeni):
    if eski not in metin:
        raise LookupError("capa yok: " + eski[:60])
    return metin.replace(eski, yeni, 1)


MUTANT_KOSUCU = {
    "MA1 esle_anahtarlik'e uzun_kenar_mm eklendi": (
        '    u["anahtarlik"] = True\n', '    u["anahtarlik"] = True\n    u["uzun_kenar_mm"] = float(g["olcu_mm"])\n',
        r"ALAN-DISI anahtarlik\.uzun_kenar_mm"),
    "MA2 anahtarlik satirlar tek dizeye birlestirildi": (
        '    u["anahtarlik"] = True\n', '    u["anahtarlik"] = True\n    u["satirlar"] = "\\n".join(u["satirlar"])\n',
        r"TIP anahtarlik\.satirlar"),
    "MA3 G5 surgu olcusu belirleyen alana yazilmiyor": (
        '    u[G5_OLCU_ALANI[kod]] = float(g["olcu_mm"])\n', "", r"EKSEN anahtarlik\.genislik_mm"),
    "MA3b yapboz surgu olcusu yazilmiyor": (
        '    u["uzun_kenar_mm"] = float(g["olcu_mm"])\n', "", r"EKSEN yapboz\.uzun_kenar_mm"),
    "MA4 renk on eki bozuk": ('u["renk_" + b] = h', 'u["renk-" + b] = h', r"ALAN-DISI anahtarlik\.renk-"),
    "MA5 anahtarlik sabiti silindi": ('    u["anahtarlik"] = True\n', "", r"SABIT anahtarlik\.anahtarlik"),
    "MA6 yapboz palet listesi baska alana": ('        u["renkler"] = renkler\n', '        u["renk_listesi"] = renkler\n',
                                            r"ALAN-DISI yapboz\.renk_listesi"),
    "MA0 kontrol: yorum eklendi -> 0 kirmizi": ("def esle_anahtarlik(", "# kontrol\ndef esle_anahtarlik(", None),
}
MUTANT_MANIFEST = {
    "MS1 manifestte anahtarlik satirlar max silindi": (
        "            satir_max: 3,\n            max: 40,\n", "            satir_max: 3,\n",
        r"SUNUCU-RED anahtarlik=parametre-metin"),
    "MS2 manifestte anahtarlik satirlar liste:true silindi": (
        "            liste: true,\n", "", r"SUNUCU-RED anahtarlik|TIP anahtarlik\.satirlar"),
    "MS3 manifestte yapboz palet_bolgeleri silindi": (
        '        palet_bolgeleri: ["renk1", "renk2", "renk3", "renk4"]\n', "", r"PALET-EKSIK yapboz"),
}
# Manifest mutantlarindan kalibi YALNIZ E katmaninda yakalananlar (9 Eki olcum: kayitsiz kosumda S `liste:true`
# silinince REDDETMIYOR -> kalip TIP'ten gelir). Kayit yoksa (sinif-r-k80: sabit kayit repoda, olmamasi ariza)
# MA'lar gibi SURVIVOR sayilir — ATLANDI YOK.
E_GEREKEN_MS = {"MS2 manifestte anahtarlik satirlar liste:true silindi"}


def mutant(ad, kayitlar):
    d = tempfile.mkdtemp(prefix="esle-mutant-")
    try:
        os.makedirs(os.path.join(d, "tools"))
        kos, man = os.path.join(d, "tools", "foto-uretec-kosucu.py"), os.path.join(d, "foto-uretim-veri.js")
        with open(KOSUCU, encoding="utf-8") as f:
            ks = f.read()
        with open(MANIFEST, encoding="utf-8") as f:
            ms = f.read()
        try:
            if ad in MUTANT_KOSUCU:
                eski, yeni, kalip = MUTANT_KOSUCU[ad]
                ks = _degistir(ks, eski, yeni)
            else:
                eski, yeni, kalip = MUTANT_MANIFEST[ad]
                ms = _degistir(ms, eski, yeni)
        except LookupError as e:
            return False, str(e)
        with open(kos, "w", encoding="utf-8") as f:
            f.write(ks)
        with open(man, "w", encoding="utf-8") as f:
            f.write(ms)
        if (ad in MUTANT_KOSUCU or ad in E_GEREKEN_MS) and kayitlar is None:
            return False, "kayit-yok (E katmani mutanti olculemedi — sabit kayit repoda olmali)"
        kirmizi, _, _ = kapi(kos, man, kayitlar)
        if kalip is None:
            return not kirmizi, "kirmizi=%d %s" % (len(kirmizi), "; ".join(kirmizi)[:200])
        return any(re.search(kalip, k) for k in kirmizi), "; ".join(kirmizi)[:200] or "KIRMIZI YOK"
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    kayitlar = kayit_oku()
    kirmizi, n, atlanan = kapi(KOSUCU, MANIFEST, kayitlar)
    for k in kirmizi:
        print("KIRMIZI " + k)
    print("S=%s kirmizi=%d" % ("YESIL" if not [k for k in kirmizi if k.startswith(("SUNUCU", "ORNEK"))]
                                else "KIRMIZI", len([k for k in kirmizi if k.startswith(("SUNUCU", "ORNEK"))])))
    if n is None:
        kirmizi.append("KAYIT-YOK %s" % GERCEK_KAYIT)
        print("ESLE=KIRMIZI kayit-yok yol=%s" % GERCEK_KAYIT)
    else:
        print("ESLE=%s tur=%d E2_ATLANDI=%d [%s] (uretec SEMA'si ust duzey literal degil)"
              % ("YESIL" if not kirmizi else "KIRMIZI", n, len(atlanan), ",".join(atlanan)))
    survivor = 0
    for ad in list(MUTANT_KOSUCU) + list(MUTANT_MANIFEST):
        g, ac = mutant(ad, kayitlar)
        print("%s %s — %s" % ("✅" if g else "❌ SURVIVOR", ad, ac))
        survivor += 0 if g else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (len(kirmizi), survivor))
    return 1 if kirmizi or survivor else 0


if __name__ == "__main__":
    sys.exit(main())

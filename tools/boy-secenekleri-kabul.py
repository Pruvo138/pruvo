#!/usr/bin/env python3
"""K59 kabul kapisi: boy secenegi D1 -> edge kart -> odeme fiyat paritesi."""

import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
SHOP = os.path.join(ROOT, "shop")
SRC = os.path.join(SHOP, "src")
EDGE_WORKER = "/Users/okan/dev/pruvo-bot/worker/src/index.js"
sys.path.insert(0, TOOLS)

import arama
import build


def modul_yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def python_ekseni():
    d1 = modul_yukle("d1_sync_boy_kabul", os.path.join(TOOLS, "d1-sync.py"))
    urun = {
        "id": "boy-kabul-urunu", "baslik": "Boy Kabul Urunu", "kategori": "Otomobil",
        "marka": [], "fiyat": "100 TL", "gorseller": ["https://media.example/x.jpg"],
        "aciklama": "Kabul fiksturu",
        "boy_secenekleri": [{"etiket": "S", "fark_tl": 0},
                             {"etiket": "L", "fark_tl": 50}],
    }
    if arama.katalog_alan_tip_sebebi("boy_secenekleri", urun["boy_secenekleri"]):
        raise AssertionError("gecerli boy semasi reddedildi")
    if not arama.katalog_alan_tip_sebebi(
            "boy_secenekleri", [{"etiket": "L", "fark_tl": -1}]):
        raise AssertionError("negatif boy farki kabul edildi")
    kart = build.kart_ozeti(urun)
    if kart.get("boy_secenekleri") != urun["boy_secenekleri"]:
        raise AssertionError("edge karti boy_secenekleri alanini tasimadi")
    conn = sqlite3.connect(":memory:")
    conn.executescript(d1._KT_SEMA)
    h1 = arama.urun_hash(urun)
    conn.executescript(d1.satir_sql(urun, 1, "hs", h1))
    yazilan = conn.execute(
        "SELECT boy_secenekleri FROM urunler WHERE id='boy-kabul-urunu'").fetchone()[0]
    if json.loads(yazilan) != urun["boy_secenekleri"]:
        raise AssertionError("D1 boy secenekleri geri-okumasi ayristi")
    degisen = dict(urun)
    degisen["boy_secenekleri"] = [{"etiket": "S", "fark_tl": 0},
                                   {"etiket": "L", "fark_tl": 60}]
    if arama.urun_hash(degisen) == h1:
        raise AssertionError("boy farki degisimi urun hash'ini degistirmedi")


def dinamik_edge_ekseni():
    """Canli /ara kartinin sahibi kardes Worker da alani tasiyor mu?"""
    if not os.path.exists(EDGE_WORKER):
        print("EDGE_EKSENI=OLCULEMEDI (kardes depo yok: %s)" % EDGE_WORKER)
        return False
    kaynak = open(EDGE_WORKER, encoding="utf-8").read()
    sabit = re.search(r'const KART_ALANLARI\s*=\s*"([^"]*)"', kaynak)
    if not sabit or "boy_secenekleri" not in sabit.group(1):
        raise AssertionError("dinamik edge Worker KART_ALANLARI boy_secenekleri kolonunu tasimiyor")
    govde = re.search(r"function kartaCevir\(r\) \{([\s\S]*?)\n\}", kaynak)
    if not govde or "boy_secenekleri" not in govde.group(1):
        raise AssertionError("dinamik edge Worker kartaCevir boy_secenekleri alanini acmiyor")
    return True


NODE_KABUL = r'''
import worker from "./index.js";

const urun = {id:"boy-kabul-urunu", baslik:"Boy Kabul Urunu", kategori:"Otomobil",
  fiyat:"100 TL", parametrik:0, gorsel:"", konfigur:"", tur:"",
  boy_secenekleri:JSON.stringify([{etiket:"S",fark_tl:0},{etiket:"L",fark_tl:50}])};

function katalog(kolonsuz) {
  return {prepare(sql) {
    const secilen = ((/SELECT ([^]*?) FROM /.exec(sql) || [])[1] || "")
      .split(",").map((x) => x.trim()).filter(Boolean);
    if (kolonsuz && secilen.includes("boy_secenekleri")) {
      return {bind() { return {async all() { throw new Error("no such column: boy_secenekleri"); }}; }};
    }
    return {bind(...idler) { return {async all() {
      const out = {};
      for (const c of secilen) { if (c in urun) out[c] = urun[c]; }
      return {results: idler.includes(urun.id) ? [out] : []};
    }}; }};
  }};
}

let ip = 1;
async function prova(boy, kolonsuz=false) {
  const kalem = {id:urun.id, malzeme:"PLA", renk:"Siyah", adet:1};
  if (boy !== undefined) kalem.boy_etiket = boy;
  const request = new Request("https://pruvo3d.com/api/shop/fiyat", {method:"POST",
    headers:{"Content-Type":"application/json", "CF-Connecting-IP":"10.0.0." + ip++},
    body:JSON.stringify({sepet:[kalem]})});
  const env = {SITE_URL:"https://pruvo3d.com", KATALOG:katalog(kolonsuz),
    FIYAT_RATE_LIMIT:{async limit(){return {success:true};}}};
  const cevap = await worker.fetch(request, env, {waitUntil(){}});
  return {kod:cevap.status, govde:await cevap.json()};
}

const gecerli = await prova("L");
if (gecerli.kod !== 200 || gecerli.govde.satirlar[0].birim_kurus !== 15000) {
  throw new Error("gecerli L boyu 15000 kurus olmadi: " + JSON.stringify(gecerli));
}
const gecersiz = await prova("XL");
if (gecersiz.kod !== 400 || gecersiz.govde.hata !== "gecersiz-boy") {
  throw new Error("bilinmeyen boy fail-closed reddedilmedi: " + JSON.stringify(gecersiz));
}
const eksik = await prova(undefined);
if (eksik.kod !== 400 || eksik.govde.hata !== "boy-secimi-zorunlu") {
  throw new Error("boy secimi atlanabildi: " + JSON.stringify(eksik));
}
const gocYok = await prova("L", true);
if (gocYok.kod !== 400 || gocYok.govde.hata !== "boy-desteklenmiyor") {
  throw new Error("D1 kolonu yokken fail-closed davranmadi: " + JSON.stringify(gocYok));
}
'''


def js_ekseni():
    gecici = tempfile.mkdtemp(prefix="src-boy-kabul-", dir=SHOP)
    try:
        for ad in os.listdir(SRC):
            if not ad.endswith(".js"):
                continue
            kaynak = open(os.path.join(SRC, ad), encoding="utf-8").read()
            def json_gom(eslesme):
                degisken, goreli = eslesme.group(1), eslesme.group(2)
                json_yolu = os.path.normpath(os.path.join(SRC, goreli))
                ham = open(json_yolu, encoding="utf-8").read().strip()
                json.loads(ham)
                return "const %s = %s;" % (degisken, ham)
            kaynak = re.sub(
                r'^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$',
                json_gom, kaynak, flags=re.M)
            with open(os.path.join(gecici, ad), "w", encoding="utf-8") as f:
                f.write(kaynak)
        with open(os.path.join(gecici, "package.json"), "w", encoding="utf-8") as f:
            json.dump({"type": "module"}, f)
        kabul = os.path.join(gecici, "kabul.mjs")
        with open(kabul, "w", encoding="utf-8") as f:
            f.write(NODE_KABUL)
        sonuc = subprocess.run(
            ["node", kabul], cwd=ROOT,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        if sonuc.returncode != 0:
            raise AssertionError("Worker boy kabul ekseni KIRMIZI:\n%s" % sonuc.stdout)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def main():
    python_ekseni()
    edge_olculdu = dinamik_edge_ekseni()
    js_ekseni()
    if edge_olculdu:
        print("K59 BOY_SECENEKLERI KABUL: D1=1 EDGE=2 ODEME=4 TEST_RC=0")
    else:
        print("K59 BOY_SECENEKLERI KABUL: D1=1 EDGE=KAPSAM_DISI ODEME=4 TEST_RC=0")


if __name__ == "__main__":
    main()

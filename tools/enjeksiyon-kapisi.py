#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ENJEKSİYON KAPISI — build.py'nin sayfalara inline bastığı JS bozulmadan mı gidiyor?

Çalıştır:  python3 tools/enjeksiyon-kapisi.py   -> PASS/FAIL döker, hepsi geçerse exit 0.
Tam build KOŞMAZ: build.attribution_ekle / meta_ekle doğrudan çağrılır (hızlı + deterministik).

NEDEN VAR (yaşanmış hata, 20 Tem):
  `re.sub`un REPLACEMENT dizesi backslash kaçışı YORUMLAR. Enjekte edilen gövde ise VERİ,
  kalıp değil. Sonuçları:
    · attribution-ref.js'teki `"\\n"` GERÇEK satır sonuna dönüyor -> JS string literali
      kırılıyor -> sayfa PARSE EDİLMİYOR (sessiz: HTML açılır, script çalışmaz, rıza
      katmanı hiç tanımlanmaz).
    · `replace(/^\\s+|\\s+$/g, "")` gibi bir satır eklenince `\\s` GEÇERSİZ kaçış olduğu için
      `re.error: bad escape \\s` -> TÜM build çöker, yayın durur.
  Doğru çözüm kaynak dosyada `\\n`/`\\s` kullanımını yasaklamak DEĞİL (tuzak geri gelir),
  enjeksiyon yolunu kaçışa DUYARSIZ yapmaktır (`sub(lambda m: snippet, ...)`).

Neyi kanıtlar:
  1) Enjekte edilen gövde `attribution-ref.js` ile BAYT BAYT aynı — hem "ilk ekleme" hem
     "mevcut bloğu yenileme" yolunda (yenileme yolu re.sub kullanır, asıl tuzak orada).
  2) `node --check`: üretilen sayfadaki attribution script'i sözdizimsel TEMİZ.
  3) RUNTIME: script koşunca `window.pruvoRef` + `window.pruvoRefRiza` gerçekten TANIMLI
     (kaynakta grep DEĞİL — çalıştırıp ölçüyoruz; rıza geri alma yolu buna bağlı).
  4) NEGATİF KONTROL: kaçış yorumlayan eski yol kullanılsaydı bu kapı KIRMIZI yanardı
     (kapının dişi olduğunun kanıtı; yoksa "hep yeşil" bir kapı olurdu).
"""

import os
import re
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import build as B  # noqa: E402

sonuclar = []


def kontrol(ad, kosul, detay=""):
    sonuclar.append((ad, bool(kosul), detay))


with open(os.path.join(ROOT, "attribution-ref.js"), encoding="utf-8") as f:
    KAYNAK = f.read().strip()


def govdeyi_cikar(html):
    """Enjekte edilmiş attribution bloğundan JS gövdesini aynen söker."""
    i = html.find(B.ATTRIBUTION_START)
    j = html.find(B.ATTRIBUTION_END)
    if i == -1 or j == -1:
        return None
    blok = html[i + len(B.ATTRIBUTION_START):j]
    m = re.search(r"<script>\n(.*)\n</script>", blok, re.S)
    return m.group(1) if m else None


def node_check(js_metni):
    """node --check ile sözdizimi denetimi (gerçek parser; regex tahmini değil)."""
    yol = os.path.join(tempfile.mkdtemp(), "parca.js")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(js_metni)
    p = subprocess.run(["node", "--check", yol], capture_output=True, text=True)
    return p.returncode == 0, (p.stderr or "").strip().split("\n")[0]


HARNESS = r"""
"use strict";
const fs = require("fs");
const vm = require("vm");
const src = fs.readFileSync(process.argv[2], "utf8");
function Depo(){ this.d = {}; }
Depo.prototype.getItem = function(k){ return Object.prototype.hasOwnProperty.call(this.d,k) ? this.d[k] : null; };
Depo.prototype.setItem = function(k,v){ this.d[k] = String(v); };
Depo.prototype.removeItem = function(k){ delete this.d[k]; };
const ctx = {
  window: {},
  document: { readyState: "complete", cookie: "",
              querySelectorAll: () => [], addEventListener: () => {} },
  localStorage: new Depo(),
  location: { search: "", hostname: "pruvo3d.com", href: "https://pruvo3d.com/" },
  navigator: { sendBeacon: () => true },
  Blob: function(){},
  crypto: { getRandomValues: (b) => { for (let i=0;i<b.length;i++) b[i] = i; return b; } },
  URL, URLSearchParams, Uint8Array, Date, JSON, String, console
};
vm.runInNewContext(src, ctx, { filename: "enjekte-attribution.js" });
const eksik = ["pruvoRef", "pruvoRefRiza"].filter((ad) => typeof ctx.window[ad] !== "function");
if (eksik.length) { console.log("EKSIK:" + eksik.join(",")); process.exit(1); }
console.log("TANIMLI");
"""


def runtime_tanimli(js_metni):
    """Script'i gerçekten koşturup window.pruvoRef / pruvoRefRiza tanımlı mı ölçer."""
    dizin = tempfile.mkdtemp()
    js_yol = os.path.join(dizin, "modul.js")
    h_yol = os.path.join(dizin, "harness.js")
    with open(js_yol, "w", encoding="utf-8") as f:
        f.write(js_metni)
    with open(h_yol, "w", encoding="utf-8") as f:
        f.write(HARNESS)
    p = subprocess.run(["node", h_yol, js_yol], capture_output=True, text=True)
    return p.returncode == 0, ((p.stdout or "") + (p.stderr or "")).strip().split("\n")[0]


# ---------------------------------------------------------------- 1) BAYT BİREBİRLİK
# (a) YENİLEME yolu: sayfada blok zaten var -> re.sub calisir (ASIL TUZAK BURADA).
with open(os.path.join(ROOT, "gizlilik", "index.html"), encoding="utf-8") as f:
    gizlilik_html = f.read()
kontrol("0 On kosul: gizlilik/ sayfasinda attribution isaretleri var",
        B.ATTRIBUTION_START in gizlilik_html)

yenilenmis = B.attribution_ekle(gizlilik_html)
govde_y = govdeyi_cikar(yenilenmis)
kontrol("1a Yenileme yolu (re.sub): govde attribution-ref.js ile BAYT BAYT ayni",
        govde_y == KAYNAK,
        "" if govde_y == KAYNAK else "uzunluk %s != %s" % (
            len(govde_y) if govde_y else None, len(KAYNAK)))

# (b) ILK EKLEME yolu: blok yok -> str.replace (kacis yorumlamaz ama yine de kilitlensin).
bos_sayfa = "<html><head><script>\n</script>\n<title>x</title></head><body></body></html>"
ilk = B.attribution_ekle(bos_sayfa)
govde_i = govdeyi_cikar(ilk)
kontrol("1b Ilk ekleme yolu: govde BAYT BAYT ayni", govde_i == KAYNAK)

# (c) IDEMPOTENT: iki kez kosunca da bozulmamali (CI her push'ta yeniden basiyor).
iki_kez = B.attribution_ekle(B.attribution_ekle(gizlilik_html))
kontrol("1c Idempotent: 2. kosuda da BAYT BAYT ayni", govdeyi_cikar(iki_kez) == KAYNAK)

# (d) Meta piksel enjeksiyonu ayni sayfayi bozmuyor (iki blok ust uste biner).
meta_sonrasi = B.meta_ekle(yenilenmis)
kontrol("1d meta_ekle sonrasi attribution govdesi hâlâ BAYT BAYT ayni",
        govdeyi_cikar(meta_sonrasi) == KAYNAK)

# ---------------------------------------------------------------- 2) SOZDIZIMI
tamam, hata = node_check(govde_y or "")
kontrol("2a node --check: yenilenen sayfadaki attribution script'i TEMIZ", tamam, hata)
tamam_u, hata_u = node_check(govdeyi_cikar(B.render_product({
    "id": "enjeksiyon-kapisi-ornek", "kategori": "Otomobil", "marka": ["Test"],
    "baslik": "Örnek", "aciklama": "Örnek açıklama.", "fiyat": "100 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/x-1.jpg"],
}, [])) or "")
kontrol("2b node --check: URUN sayfasindaki attribution script'i TEMIZ", tamam_u, hata_u)

# ---------------------------------------------------------------- 3) RUNTIME TANIMLILIK
tamam_r, cikti_r = runtime_tanimli(govde_y or "")
kontrol("3 RUNTIME: window.pruvoRef + window.pruvoRefRiza TANIMLI (riza geri alma buna bagli)",
        tamam_r, cikti_r)

# ---------------------------------------------------------------- 4) NEGATIF KONTROL
# Eski (kacis yorumlayan) yol kullanilsaydi kapi kirmizi yanar miydi? Kaynakta `\s` varken
# re.error firlar; `\n` varken sessizce satir sonu olur. Ikisi de "bozulma" sayilir.
snippet = B.attribution_head_snippet()
desen = re.compile(re.escape(B.ATTRIBUTION_START) + r".*?" + re.escape(B.ATTRIBUTION_END), re.S)
try:
    eski = desen.sub(snippet, gizlilik_html, count=1)      # KASITLI eski/hatali yol
    eski_bozuk = govdeyi_cikar(eski) != KAYNAK
    eski_not = "govde degisti" if eski_bozuk else "DEGISMEDI (kapi dissiz!)"
except re.error as e:
    eski_bozuk, eski_not = True, "re.error: %s" % e
kontrol("4 Negatif kontrol: kacis-yorumlayan ESKI yol bu kapiyi kirmizi yakardi",
        eski_bozuk, eski_not)

# ---------------------------------------------------------------- SONUC
print()
gecen = 0
for ad, ok, detay in sonuclar:
    print("%s  %s%s" % ("PASS" if ok else "FAIL", ad, ("  -> " + detay) if (detay and not ok) else ""))
    gecen += 1 if ok else 0
print("-" * 48)
print("Toplam: %d  |  PASS: %d  |  FAIL: %d" % (len(sonuclar), gecen, len(sonuclar) - gecen))
sys.exit(0 if gecen == len(sonuclar) else 1)

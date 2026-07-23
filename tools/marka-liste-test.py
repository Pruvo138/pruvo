#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — MARKA KÜRATÖRLÜĞÜ (ana sayfa marka çip listesi).

Okan talebi (23 Tem): (1) çip listesinde model/motor kodu gibi TANINMAYAN kalem olmasın,
(2) "Toyota 86"/"Mercedes-Benz" gibi varyantlar tek kaleme katlansın (görünüm + filtre
eşleşmesi tutarlı), (3) Philips/Miele/Bosch/Siemens gibi bilinen markalar katalogda ürünü
varsa listede olsun. Tanınmayan markalı ürünler listeden düşer ama ARAMAYLA bulunur kalır.

NE YAPAR:
  A) index.html'deki "MARKA KÜRATÖRLÜĞÜ" bloğunu (TANINMIS_MARKALAR + markaNorm +
     markaKatla + taninmisMarkaMi) ve norm() fonksiyonunu KAYNAKTAN ayıklar — küratörlü
     liste/katlama mantığının kopyası tutulmaz, testin sınadığı şey CANLI koddur.
  B) Bloğu node ile GERÇEK urunler.json'a uygular (çip boru hattının parametrik kopyası
     marka-limit-test.js deseninde) ve şunları kilitler:
       1. Çip evreninde (Tümü + her kategori) tanınmayan kalem = 0.
       2. Toyota TEK kalem; "Mercedes" filtresi "Mercedes-Benz"-yalnız ürünleri de bulur
         (katlama eşleşmede de geçerli — exact-match'e dönen mutasyon burada KIRMIZI yanar).
       3. Philips/Miele/Bosch/Siemens çip evreninde VE en az bir görünümde görünür çip.
       4. Varyant/ikiz kalemler (Mercedes-Benz, Toyota 86, KIA, MINI, Ikea, Volvo Penta...)
          ayrı çip DEĞİL; eski tanınmayan çipler (E46, Tacoma, Corsa, Octavia...) çip DEĞİL.
  C) Kaynak kuplajı: katlama/küratörlük gerçekten kablolu mu (sortedBrands filter,
     brandCounts katlama, filtered() katlamalı eşleşme, applyUrlParams katlama).

NEDEN .py + node: JS mantığı node'da koşmak zorunda; CI kapsam kapısı (ci-kapsam-test.py)
yalnız "python3 tools/..." icra satırlarını sayar ve IZIN_LISTESI'ne dokunmak yasak →
piksel-katalog-parite-test.py deseni: python3 sarmalayıcı, node FAIL-CLOSED alt süreç.
Node yoksa CI'da (GITHUB_ACTIONS) DAİMA exit 1; yerelde MARKA_LISTE_NODE_ATLA=1 ile
AÇIK uyarıyla atlanabilir. Offline, ağ yok, urunler.json'a YAZMAZ. Ölçüldü ~1 s.

Çalıştır:  python3 tools/marka-liste-test.py   (çıkış 0 = geçti, 1 = kaldı)
"""
import json
import os
import re
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
INDEX = os.path.join(ROOT, "index.html")
URUNLER = os.path.join(ROOT, "urunler.json")

FAILS = []


def kontrol(ad, kosul):
    if kosul:
        print("  PASS  " + ad)
    else:
        FAILS.append(ad)
        print("  FAIL  " + ad)


def bitir():
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldı)" % len(FAILS))
        sys.exit(1)
    print("\nSONUC: YESIL ✅")
    sys.exit(0)


src = open(INDEX, encoding="utf-8").read()

# ---- A) Kaynaktan ayıklama (kopya değil, canlı kod) -------------------------
BLOK_BAS = "// --- MARKA KÜRATÖRLÜĞÜ BAŞ"
BLOK_SON = "// --- MARKA KÜRATÖRLÜĞÜ SON ---"
bas = src.find(BLOK_BAS)
son = src.find(BLOK_SON)
kontrol("index.html MARKA KÜRATÖRLÜĞÜ blok marker'ları var", bas != -1 and son != -1 and son > bas)
if bas == -1 or son == -1 or son <= bas:
    bitir()
blok = src[src.index("\n", bas) + 1: son]

m = re.search(r"function norm\(s\)\{[\s\S]*?\n  \}", src)
kontrol("index.html norm() ayıklanabildi", bool(m))
if not m:
    bitir()
norm_src = m.group(0)

for imza in ("TANINMIS_MARKALAR", "function markaKatla", "function taninmisMarkaMi", "function markaNorm"):
    kontrol("blokta %s tanımlı" % imza, imza in blok)

# ---- C) Kaynak kuplajı: küratörlük/katlama gerçekten kablolu ----------------
kontrol("sortedBrands küratörlü (.filter(taninmisMarkaMi))", ".filter(taninmisMarkaMi)" in src)
kontrol("brandCounts katlıyor (markaKatla(b))", "markaKatla(b)" in src)
kontrol("brandCounts ürün-içi tekilleştiriyor (var gorulen = {})", "var gorulen = {};" in src)
kontrol("filtered() katlamalı eşleşiyor (markaKatla(activeBrand))", "markaKatla(activeBrand)" in src)
kontrol("applyUrlParams deep-link'i katlıyor (markaKatla(mar))", "markaKatla(mar)" in src)
kontrol("MARKA_LIMIT=32 kuralı duruyor (Okan 19 Tem)", "slice(0, MARKA_LIMIT)" in src)

# ---- B) node ile GERÇEK katalog üzerinde davranış ---------------------------
try:
    subprocess.run(["node", "--version"], capture_output=True, check=True)
    node_var = True
except (OSError, subprocess.CalledProcessError):
    node_var = False

if not node_var:
    if os.environ.get("GITHUB_ACTIONS"):
        kontrol("CI'da node var (FAIL-CLOSED: setup-node eksik/bozuk)", False)
        bitir()
    if os.environ.get("MARKA_LISTE_NODE_ATLA") == "1":
        print("UYARI: node yok + MARKA_LISTE_NODE_ATLA=1 → davranış bölümü AÇIK uyarıyla atlandı "
              "(yalnız kaynak-kuplaj kontrolleri koştu).")
        bitir()
    kontrol("node bulundu (yerelde kur ya da MARKA_LISTE_NODE_ATLA=1 ile açık uyarıyla atla)", False)
    bitir()

# Çip boru hattının PARAMETRİK kopyası (marka-limit-test.js deseni; index.html ile birebir
# aynı kural: sayım→katlama→tekilleştirme→küratör filtresi→sayı-azalan/alfabetik→32 cap).
harness = r"""
"use strict";
NORM_SRC
BLOK_SRC
const PRODUCTS = require(URUNLER_JSON);

function brandCounts(products, activeCat){
  const counts = {};
  products.forEach(function(p){
    if(activeCat !== "Tümü" && p.kategori !== activeCat){ return; }
    const gorulen = {};
    (p.marka || []).forEach(function(b){
      const k = markaKatla(b);
      if(gorulen[k]){ return; }
      gorulen[k] = true;
      counts[k] = (counts[k] || 0) + 1;
    });
  });
  return counts;
}
function sortedBrands(products, activeCat){
  const counts = brandCounts(products, activeCat);
  return Object.keys(counts).filter(taninmisMarkaMi).sort(function(a, b){
    if(counts[b] !== counts[a]){ return counts[b] - counts[a]; }
    return a.localeCompare(b, "tr");
  });
}
const MARKA_LIMIT = 32;
function chips(products, activeCat){ return sortedBrands(products, activeCat).slice(0, MARKA_LIMIT); }
function filteredMarka(products, marka){
  const hedef = markaKatla(marka);
  return products.filter((p) => (p.marka || []).some((b) => markaKatla(b) === hedef));
}

let pass = 0, fail = 0;
function ok(cond, msg){
  if(cond){ pass++; console.log("  PASS  " + msg); }
  else    { fail++; console.log("  FAIL  " + msg); }
}

const kategoriler = [...new Set(PRODUCTS.map((p) => p.kategori))];
const gorunumler = ["Tümü", ...kategoriler];

// 1) Çip evreninde tanınmayan kalem = 0 (tüm görünümler)
let taninmayan = [];
for(const g of gorunumler){
  for(const c of chips(PRODUCTS, g)){
    if(!taninmisMarkaMi(c)){ taninmayan.push(g + ":" + c); }
  }
}
ok(taninmayan.length === 0,
   "tüm görünümlerde tanınmayan çip = 0 (bulunan: " + (taninmayan.slice(0, 10).join(", ") || "-") + ")");

// Küratör filtresi YÜK TAŞIYOR mu: ham sayımda tanınmayan değer varken evren temiz kalmalı
const hamTumu = Object.keys(brandCounts(PRODUCTS, "Tümü"));
const hamTaninmayan = hamTumu.filter((b) => !taninmisMarkaMi(b));
if(hamTaninmayan.length){
  ok(sortedBrands(PRODUCTS, "Tümü").every(taninmisMarkaMi),
     "küratör filtresi yük taşıyor (ham evrende " + hamTaninmayan.length + " tanınmayan değer var, listede 0)");
}else{
  console.log("  SKIP  ham evrende tanınmayan değer kalmamış (mutasyon kanıtı koşulamadı)");
}

// 2) Toyota TEK kalem + katlama eşleşmede de geçerli
for(const g of gorunumler){
  const toyotalar = chips(PRODUCTS, g).filter((c) => markaNorm(c).indexOf("toyota") === 0);
  ok(toyotalar.length <= 1, g + " görünümünde Toyota tek kalem (bulunan: " + toyotalar.join(", ") + ")");
}
const exactMercedes = PRODUCTS.filter((p) => (p.marka || []).indexOf("Mercedes") !== -1).length;
const katliMercedes = filteredMarka(PRODUCTS, "Mercedes").length;
ok(katliMercedes > exactMercedes,
   "Mercedes filtresi varyantları da buluyor (exact " + exactMercedes + " < katlamalı " + katliMercedes + ")");
const t86 = PRODUCTS.filter((p) => (p.marka || []).indexOf("Toyota 86") !== -1);
const katliToyota = filteredMarka(PRODUCTS, "Toyota");
ok(t86.every((p) => katliToyota.indexOf(p) !== -1),
   "Toyota filtresi 'Toyota 86' ürünlerini de buluyor (" + t86.length + " ürün)");
ok(filteredMarka(PRODUCTS, "Mercedes-Benz").length === katliMercedes,
   "deep-link ?marka=Mercedes-Benz katlanınca aynı sonucu verir");

// 3) Bilinen ev/elektronik markaları: evrende VE en az bir görünümde görünür çip
const evren = sortedBrands(PRODUCTS, "Tümü");
for(const b of ["Philips", "Miele", "Bosch", "Siemens"]){
  const urun = filteredMarka(PRODUCTS, b).length;
  if(urun === 0){ console.log("  SKIP  " + b + " katalogda ürünsüz (liste şartı yok)"); continue; }
  ok(evren.indexOf(b) !== -1, b + " çip evreninde (ürün: " + urun + ")");
  ok(gorunumler.some((g) => chips(PRODUCTS, g).indexOf(b) !== -1),
     b + " en az bir görünümde görünür çip");
}

// 4) Varyant/ikiz/tanınmayan kalemler ayrı çip DEĞİL
const yasakKalem = ["Mercedes-Benz", "Toyota 86", "KIA", "MINI", "Ikea", "Volvo Penta",
                    "E46", "E36", "E30", "Tacoma", "Corsa", "Octavia", "Astra", "Duster",
                    "R1200GS", "Vectra", "Corolla", "4Runner", "Tundra", "RAV4"];
let yasakBulunan = [];
for(const g of gorunumler){
  for(const c of chips(PRODUCTS, g)){
    if(yasakKalem.indexOf(c) !== -1){ yasakBulunan.push(g + ":" + c); }
  }
}
ok(yasakBulunan.length === 0,
   "varyant/model-kodu kalemi çip değil (bulunan: " + (yasakBulunan.slice(0, 10).join(", ") || "-") + ")");

// Sayılarla döküm (rapor için)
console.log("  BILGI Tümü görünümü çipleri: " + chips(PRODUCTS, "Tümü").join(", "));
console.log("  BILGI evren büyüklüğü (küratörlü liste): " + evren.length +
            " | ham tekil değer: " + hamTumu.length);
console.log("SONUC " + pass + " geçti " + fail + " kaldı");
process.exit(fail === 0 ? 0 : 1);
"""
harness = (harness
           .replace("NORM_SRC", norm_src)
           .replace("BLOK_SRC", blok)
           .replace("URUNLER_JSON", json.dumps(URUNLER)))

with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(harness)
    tmp = f.name
try:
    r = subprocess.run(["node", tmp], capture_output=True, text=True)
finally:
    os.unlink(tmp)

sys.stdout.write(r.stdout)
if r.returncode != 0:
    kontrol("node davranış bölümü yeşil (stderr: %s)" % (r.stderr.strip()[:300] or "-"), False)
else:
    kontrol("node davranış bölümü yeşil", True)

bitir()

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
     brandCounts katlama, filtered() katlamalı eşleşme, applyUrlParams katlama) + dört
     serbest metin çağrı yerinin de TEK arama planından geçtiği.
  D) 🔴 MARKA SORGUSU İKİZ PARİTESİ (5 Ağu): "marka adıyla yapılan sorgu" kuralı İKİ
     gövdede yaşar — index.html MARKA SORGUSU bloğu (müşterinin tarayıcısı) ve
     tools/arama.py + marka_model_build.marka_adi_kanonu (D1/uç modeli, marka invaryant
     kapısı). Beklenti PYTHON üretim fonksiyonlarıyla hesaplanır, iddia GERÇEK katalogda
     JS koşularak ölçülür (68 sorgu: 34 marka + 34 marka-olmayan). Ayrışırsa müşteri
     sitede başka, ölçümde başka sonuç görür ([[ikiz-tanim-sessiz-ayrisma]]).
     Ayrıca: marka OLMAYAN sorgunun semantiği DEĞİŞMEMİŞ olmalı (mimar sınırı) ve
     uzun-önce kuralı deterministik fikstürle kanıtlanır ("Land Rover" → "Rover" DEĞİL).

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
import shutil
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

# --- MARKA SORGUSU bloğu (marka adıyla yapılan aramanın ÜYELİK yüklemi) ------
# Bu blok tools/arama.py + tools/marka_model_build.py ile İKİZDİR; ayrışırsa müşteri
# sitede başka, uçta/Ege'de başka sonuç görür. Aşağıda GERÇEK katalogla ölçülür.
SORGU_BAS = "// --- MARKA SORGUSU BAŞ"
SORGU_SON = "// --- MARKA SORGUSU SON ---"
sbas, sson = src.find(SORGU_BAS), src.find(SORGU_SON)
kontrol("index.html MARKA SORGUSU blok marker'ları var", sbas != -1 and sson > sbas)
if sbas == -1 or sson <= sbas:
    bitir()
sorgu_blok = src[src.index("\n", sbas) + 1: sson]
for imza in ("function markaAdiKanonu", "function baslikMarkalari", "function markaUyeMi",
             "function markaSorgusuEsler", "function aramaPlani", "function aramaPlaniEsler"):
    kontrol("MARKA SORGUSU bloğunda %s tanımlı" % imza, imza in sorgu_blok)

mk = re.search(r"var ARAMA_EKLER=\[[^\n]*\n  function aramaKok\(w\)\{[^\n]*\n", src)
mh = re.search(r"function haystack\(p\)\{[\s\S]*?\n  \}", src)
mc = re.search(r"function cipIndeks\(\)\{[\s\S]*?\n  \}", src)
kontrol("index.html aramaKok/haystack/cipIndeks ayıklanabildi", all([mk, mh, mc]))
if not (mk and mh and mc):
    bitir()
kok_src, hay_src, cip_src = mk.group(0), mh.group(0), mc.group(0)

for imza in ("TANINMIS_MARKALAR", "function markaKatla", "function taninmisMarkaMi", "function markaNorm"):
    kontrol("blokta %s tanımlı" % imza, imza in blok)

# ---- C) Kaynak kuplajı: küratörlük/katlama gerçekten kablolu ----------------
kontrol("sortedBrands küratörlü (.filter(taninmisMarkaMi))", ".filter(taninmisMarkaMi)" in src)
kontrol("brandCounts katlıyor (markaKatla(b))", "markaKatla(b)" in src)
kontrol("brandCounts ürün-içi tekilleştiriyor (var gorulen = {})", "var gorulen = {};" in src)
kontrol("filtered() katlamalı eşleşiyor (markaKatla(activeBrand))", "markaKatla(activeBrand)" in src)
# Dört serbest metin çağrı yeri de TEK plandan geçmeli — biri elde kalırsa marka sorgusu
# o yüzeyde sessizce eski serbest metin davranışında kalır.
kontrol("serbest metin çağrı yerleri TEK plandan geçiyor (aramaPlani × 4)",
        src.count("aramaPlani(query)") == 4)
kontrol("eski satır içi jeton döngüsü kalmadı (norm(query).split → 0)",
        "norm(query).split(/\\s+/).filter(Boolean).map(aramaKok)" not in src)
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

# ---- B2) İKİZ PARİTE VERİSİ: Python tarafının BEKLENTİSİ ---------------------
# 🔴 NEDEN: "marka adıyla yapılan sorgu" kuralı İKİ GÖVDEDE yaşar — index.html (müşterinin
# tarayıcısı) ve tools/arama.py (D1/uç modeli, marka invaryant kapısı). İkisi sessizce
# ayrışırsa kimse görmez ([[ikiz-tanim-sessiz-ayrisma]]): site başka, ölçüm başka sonuç
# verir. Burada beklenti PYTHON üretim fonksiyonlarıyla hesaplanır, iddia JS'te ölçülür.
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
try:
    import arama                                                     # noqa: PLC0415
    import marka_model_build as mmb                                  # noqa: PLC0415
    _urunler = json.load(open(URUNLER, encoding="utf-8"))
    _evren = mmb.MarkaEvreni(src)
    _ek = mmb.cip_evreni_markalari(_urunler, src)
    _ix = mmb._cip_indeks_yukle().indeks_uret(_urunler, src)
except Exception as e:                                               # noqa: BLE001
    kontrol("ikiz parite kaynakları okunabildi (%s: %s)" % (type(e).__name__, e), False)
    bitir()

_ek_normlu = mmb.ek_marka_normlu(_ek)
_kanon_bellek = {}


def _kanon(dizge):
    if dizge not in _kanon_bellek:
        _kanon_bellek[dizge] = mmb.marka_adi_kanonu(dizge, _evren, _ek_normlu)
    return _kanon_bellek[dizge]


# MARKA sorguları: küratörlü liste + çip evreni + yazım varyantları (KIA/vauxhall/boşluklu).
MARKA_SORGULARI = ["MAN", "Mini", "Haval", "Mercury", "Yamaha", "Acer", "Rover", "Makita",
                   "Suzuki", "Holden", "Tesla", "Honda", "3M", "Garmin", "GoPro", "Seat",
                   "MG", "Audi", "Samsung", "Proton", "Raymarine", "Sigma", "Smart",
                   "Sierra", "Skoda", "Tecnoseal", "Land Rover", "Black+Decker", "KIA",
                   "vauxhall", "  Toyota  ", "Raspberry Pi", "Alfa Romeo", "citroen"]
# MARKA OLMAYAN sorgular: davranış AYNEN korunmalı (mimar sınırı). Gürültü kaynaklarının
# KENDİSİ de burada ("mandal", "havalandırma", "43mm") — marka sorgusu onları BOZMAMALI.
MARKA_OLMAYAN = ["jant kapagi", "jant kapağı", "menteşe", "vida", "kapak", "far", "klips",
                 "o-ring", "conta", "braket", "tutucu", "adaptör", "kelepçe", "somun",
                 "bardaklık", "anahtarlık", "kablo", "rulman", "yakıt filtresi", "gidon",
                 "ayna", "pedal", "silecek", "torpido", "audi a4", "toyota jant", "mandal",
                 "havalandırma", "43mm", "ipad", "kumanda", "manuel", "",
                 "yokboylebirsey12345"]

_hs = [(p.get("id"), arama.haystack(p)) for p in _urunler]
_uyelik, _baslik = {}, {}
for _p in _urunler:
    _pid = _p.get("id")
    if _pid:
        _uyelik[_pid] = mmb.marka_uyelikleri(_p.get("marka") or [], _evren, _ek)
        _baslik[_pid] = arama.baslik_marka_uyumlari(_p.get("baslik"), _kanon)


def _serbest(q):
    tok = arama.tokenlar(q)
    return sorted(i for i, h in _hs if i and arama.esles(h, tok))


beklenen, sapan_semantik = {}, []
for _q in MARKA_SORGULARI + MARKA_OLMAYAN:
    _km = arama.marka_sorgu_kanonu(_q, _kanon)
    if _km:
        _ids = sorted(i for i in _uyelik
                      if arama.marka_sorgusu_esler(_km, _uyelik[i], _baslik[i]))
    else:
        _ids = _serbest(_q)
    beklenen[_q] = {"kanon": _km, "n": len(_ids), "ilk": _ids[:5]}
    # MARKA OLMAYAN sorguda kural DEĞİŞMEMELİ: sonuç serbest metinle BİREBİR aynı olmalı.
    if _q in MARKA_OLMAYAN:
        _es = _serbest(_q)
        if _km is not None or len(_es) != len(_ids) or _es[:5] != _ids[:5]:
            sapan_semantik.append(_q)

kontrol("marka OLMAYAN sorgu semantiği DEĞİŞMEDİ (%d sorgu, sapan: %d %s)"
        % (len(MARKA_OLMAYAN), len(sapan_semantik), sapan_semantik[:4]), not sapan_semantik)
# Gürültü kesildi mi: marka sorgusu serbest metinden DAR olmalı (yoksa kural bağlanmamış).
_kesilen = [q for q in MARKA_SORGULARI if beklenen[q]["n"] < len(_serbest(q))]
kontrol("marka sorgusu serbest metinden DAR (%d/%d sorguda gürültü kesildi)"
        % (len(_kesilen), len(MARKA_SORGULARI)), len(_kesilen) >= 20)

_tmpdir = tempfile.mkdtemp(prefix="marka-liste-ikiz-")
VERI_YOLU = os.path.join(_tmpdir, "beklenen.json")
IX_YOLU = os.path.join(_tmpdir, "cip-indeks.json")
with open(VERI_YOLU, "w", encoding="utf-8") as f:
    json.dump(beklenen, f, ensure_ascii=False)
with open(IX_YOLU, "w", encoding="utf-8") as f:
    json.dump(_ix, f, ensure_ascii=False)

# Çip boru hattının PARAMETRİK kopyası (marka-limit-test.js deseni; index.html ile birebir
# aynı kural: sayım→katlama→tekilleştirme→küratör filtresi→sayı-azalan/alfabetik→32 cap).
harness = r"""
"use strict";
global.window = { PRUVO_CIP_INDEKS: require(IX_JSON) };
NORM_SRC
KOK_SRC
HAY_SRC
CIP_SRC
BLOK_SRC
SORGU_SRC
const PRODUCTS = require(URUNLER_JSON);
const IKIZ_BEKLENEN = require(VERI_JSON);

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
// Katalogdaki son "Mercedes-Benz" değeri kanonik "Mercedes" olunca veri-bağımlı mutasyon
// tanığı kayboldu. Varyant katlamayı üretim koduyla, deterministik tek ürün fikstürüyle ölç.
const mercedesVaryantUrunleri = PRODUCTS.concat([{marka: ["Mercedes-Benz"]}]);
const exactMercedes = mercedesVaryantUrunleri.filter((p) => (p.marka || []).indexOf("Mercedes") !== -1).length;
const katliMercedes = filteredMarka(mercedesVaryantUrunleri, "Mercedes").length;
ok(katliMercedes > exactMercedes,
   "Mercedes filtresi varyantları da buluyor (exact " + exactMercedes + " < katlamalı " + katliMercedes + ")");
const t86 = PRODUCTS.filter((p) => (p.marka || []).indexOf("Toyota 86") !== -1);
const katliToyota = filteredMarka(PRODUCTS, "Toyota");
ok(t86.every((p) => katliToyota.indexOf(p) !== -1),
   "Toyota filtresi 'Toyota 86' ürünlerini de buluyor (" + t86.length + " ürün)");
ok(filteredMarka(mercedesVaryantUrunleri, "Mercedes-Benz").length === katliMercedes,
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

// 5) İKİZ PARİTE — index.html MARKA SORGUSU bloğu ile tools/arama.py AYNI kümeyi mi verir?
// Beklenti PYTHON üretim fonksiyonlarından geldi; burada GERÇEK katalogla JS koşuluyor.
let ikizKaldi = [];
Object.keys(IKIZ_BEKLENEN).forEach(function(q){
  const bek = IKIZ_BEKLENEN[q];
  const plan = aramaPlani(q);
  const ids = PRODUCTS.filter(function(p){ return aramaPlaniEsler(p, plan); })
                      .map(function(p){ return p.id; }).sort();
  if((plan.kanon || null) !== (bek.kanon || null) || ids.length !== bek.n ||
     JSON.stringify(ids.slice(0, 5)) !== JSON.stringify(bek.ilk)){
    ikizKaldi.push(JSON.stringify(q) + " js{" + plan.kanon + "," + ids.length +
                   "} py{" + bek.kanon + "," + bek.n + "}");
  }
});
ok(ikizKaldi.length === 0, "İKİZ PARİTE: index.html ↔ tools/arama.py marka sorgusu birebir (" +
   Object.keys(IKIZ_BEKLENEN).length + " sorgu; sapan: " +
   (ikizKaldi.slice(0, 3).join(" | ") || "-") + ")");

// 6) UZUN-ÖNCE kuralı YÜK TAŞIYOR mu (deterministik fikstür — veriye bağımlı değil).
// "Land Rover" bigramı tuttuğunda tekil "Rover" ÜRETİLMEMELİ: ikisi AYRI marque'tır ve
// katalogda 87 Land Rover ürünü "Rover" sorgusuna sızıyordu (ölçüldü 5 Ağu).
const lrTek = baslikMarkalari({baslik: "Land Rover Defender Kapı Kolu Kapağı"});
ok(lrTek.indexOf("Land Rover") !== -1 && lrTek.indexOf("Rover") === -1,
   "uzun-önce: 'Land Rover Defender ...' → " + JSON.stringify(lrTek) + " (Rover ÜRETİLMEZ)");
// KONTROL (iddia edilmeyen eksen): 'Land' öneki YOKKEN tekil Rover DOĞMALI — kural
// "Rover'ı hep ez" değil, "uzun eşleşmeyi bölme"dir.
const rvTek = baslikMarkalari({baslik: "Rover 75 Torpido Klipsi"});
ok(rvTek.indexOf("Rover") !== -1,
   "uzun-önce KONTROL: 'Rover 75 ...' → " + JSON.stringify(rvTek) + " (Rover DOĞAR)");
// Çok kelimeli marka bölünmüyor + önek katlaması METİNDE çalışmıyor (jeton yutulmaz).
const abTek = baslikMarkalari({baslik: "Alfa Romeo 156 Vites Topuzu"});
ok(abTek.indexOf("Alfa Romeo") !== -1, "çok kelimeli marka bütün: " + JSON.stringify(abTek));
const ymTek = baslikMarkalari({baslik: "Sierra 18-8076 Yamaha Mercury Ortak Tip Benzin Fişi"});
ok(ymTek.indexOf("Yamaha") !== -1 && ymTek.indexOf("Mercury") !== -1,
   "önek katlaması METİNDE yok: 'Yamaha Mercury' → " + JSON.stringify(ymTek) +
   " (ikisi de doğar; markaKatla olsaydı Mercury YUTULURDU)");

// Sayılarla döküm (rapor için)
console.log("  BILGI Tümü görünümü çipleri: " + chips(PRODUCTS, "Tümü").join(", "));
console.log("  BILGI evren büyüklüğü (küratörlü liste): " + evren.length +
            " | ham tekil değer: " + hamTumu.length);
console.log("SONUC " + pass + " geçti " + fail + " kaldı");
process.exit(fail === 0 ? 0 : 1);
"""
harness = (harness
           .replace("NORM_SRC", norm_src)
           .replace("KOK_SRC", kok_src)
           .replace("HAY_SRC", hay_src)
           .replace("CIP_SRC", cip_src)
           .replace("BLOK_SRC", blok)
           .replace("SORGU_SRC", sorgu_blok)
           .replace("URUNLER_JSON", json.dumps(URUNLER))
           .replace("VERI_JSON", json.dumps(VERI_YOLU))
           .replace("IX_JSON", json.dumps(IX_YOLU)))

with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(harness)
    tmp = f.name
try:
    r = subprocess.run(["node", tmp], capture_output=True, text=True)
finally:
    os.unlink(tmp)
    shutil.rmtree(_tmpdir, ignore_errors=True)

sys.stdout.write(r.stdout)
if r.returncode != 0:
    kontrol("node davranış bölümü yeşil (stderr: %s)" % (r.stderr.strip()[:300] or "-"), False)
else:
    kontrol("node davranış bölümü yeşil", True)

bitir()

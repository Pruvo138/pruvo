#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA/MODEL SAYFASI SAYAÇ KAPISI — "N parça" DOĞRU BİRİMDE Mİ + MÜKERRER KART VAR MI.

🔴 NEDEN VAR (7 Ağu 2026, Okan: "marka sayfaları eksik görünüyor" — SESSİZ kusur):
  1. Kapsam şeridi bildirilen marka sayfasında (`?kategori=…`) "201 parça" yazıyordu; sayfadan
     ulaşılabilen gerçek küme 330 kalemdi. Sayaç YALNIZ `.card` düğümlerini sayıyordu, model
     butonlarının ARDINDAKİ parçaları saymıyordu. Aynı sayfanın meta'sı "330 parça" diyordu →
     tek sayfada İKİ FARKLI SAYI. Ekranda hata görünmüyor; müşteri kataloğu eksik sanıyor.
  2. `marka_only + ikincil + kucuk_urunler` birleşimi id bazında tekilleştirilmiyordu →
     31 marka sayfasında 282 fazla kart (aynı ürün iki kez).

🔴 KAPININ KENDİ KÖRLÜĞÜ KAPANDI (8 Ağu 2026, Okan hükmü). Eski `BIRIM_KALEM/cakisma`
iddiası "kart kolu ile kova ÇAKIŞABİLİR, tekilleştirme yutar" diyordu — yani kusuru DOĞRU
DAVRANIŞ diye kutsuyordu; bölüm kimliği hiç iddia EDİLMİYORDU. İddia TERSİNE ÇEVRİLDİ:
çakışma İHLALDİR (`BIRIM_AYRIM/eleme` + `AYRIK/<sayfa>`). Ölçülen iki yönlü işaret:
onarım ÖNCESİ jeneratörle bu kapı `AYRIK` ekseninde 32 sayfa, `AGIRLIK` ekseninde 11 sayfa
kırmızı yakıyor; onarım SONRASI 0/0.

KAPI NEYİ ÖLÇER (üretilen HTML üzerinden, ÖRNEKLEME YOK — 1043 marka adresinin TAMAMI):
  MUKERRER      : sayfadaki ham kart sayısı == tekil kart sayısı.
  KIMLIK        : KART YÜZEYİ == başlıktaki toplam. Yüzey = SSR kartları ∪ düz bağ girdileri
                  ∪ artım yükünün (`parcalar.json`) kalemleri. Okan hükmü: marka sayfası
                  markanın TÜM parçalarını kart olarak listeler; ağırlık yüzünden bir kısmı
                  AYNI SAYFADA artımlı çizilir, ama yüzey EKSİLMEZ. Yük yok/bozuksa KIRMIZI.
  KIMLIK_MUKERRER: ne yükün içinde ne SSR ile yük arasında çift kalem olmaz.
  AYRIK         : yerel bölüm ∩ model kovaları == ∅ (çakışma İHLAL). Yerel bölüm sayfanın
                  KENDİ beyanından (yükte model indeksi boş olan kalemler) okunur; yük yoksa
                  kartlardan çıkarılır -> eksen onarım ÖNCESİ şekilde de ölçülebilir.
  BAG_YEREL     : düz bağ listesindeki her kalem yereldir (model sayfası olanı bağa koymak
                  gereksiz bayt, yereli koymamak ÖKSÜZ ürün demek).
  KART_N        : SSR'de basılan kart sayısı == min(MARKA_KART_N, toplam). N aşılırsa sayfa
                  yeniden şişer, N'den az basılırsa ilk boya sessizce zayıflar.
  AGIRLIK       : üretilen HTML baytı <= HTML_TAVAN (katalog her partide büyüyor; tavan
                  kapıda değilse bir sonraki parti sayfayı sessizce yeniden şişirir).
  ARTIM         : istemcinin çizeceği kart gövdesi (PRUVO_ARTIM.kartHtml, node'da GERÇEKTEN
                  koşturulur) Python `_kart` ile BAYT-AYNI — yükteki HER kalem için.
  ARTIM_SUZ     : sayfa-içi model/kapsam süzgeci kanonik kümeyi verir; tanınmayan yükte
                  BOŞ küme döner (fail-closed) ve süzgeç GERÇEKTEN daraltır (kontrol).
  KAYIP         : marka sayfasından ULAŞILABİLEN tekil küme == katalogdaki üyelik kümesi
                  (bağımsız türetme: `marka_uyelikleri`, gruplandır/sayfa üreticisi DEĞİL).
  TOPLAM        : SSR'de basılan `.mm-sayim-toplam` == ulaşılabilen tekil küme büyüklüğü.
  KIRILIM       : `data-katsay` kategori kırılımının toplamı == SSR toplamı (tek kaynak).
  KIRILIM_KAT   : kırılımdaki her kategori sayısı == ulaşılabilen kümenin o kategorideki sayısı.
  SIRA          : tekilleştirme kart sırasını BOZMAZ (kart id'leri katalog sırasına göre en
                  çok 3 monoton koşuya ayrılır: kucuk + marka_only + ikincil).
  JS_FILTRESIZ  : sayfanın KENDİ gömülü kapsam modülü, kapsam pasifken SSR toplamını verir.
  JS_SERIT      : `?kategori=K` ile şeridin BASTIĞI metin == "… — <beklenen> parça"; beklenen
                  HTML'den bağımsız sayılır (kart+model sayfası birleşimi, o kategoride).
  JS_ALTKUME    : şeritteki sayı görünen kart sayısından küçük olamaz.
  INVARYANT_*   : 🔴 12 Ağu 2026 (Okan, canlı): aynı marka için ekranda DÖRT ayrı sayı vardı
                  — beyan 593 · başlık 80 · kapsam beyanı 575 · kapsam başlığı 304. Başlık
                  O AN BASILAN kartı (`MARKA_KART_N` tavanı) sayıyordu, sayfadan
                  ERİŞİLEBİLENİ değil; istemcide ise GÖRÜNEN DOM DÜĞÜMÜNÜ. HÜKÜM: sayfada
                  BEYAN EDİLEN parça sayısı == o yüzeyde ERİŞİLEBİLEN kart sayısı.
                  INVARYANT_SSR (başlık == erişim, kırılımıyla) · INVARYANT_BEYAN (başlık
                  ile beyan cümlesi TEK kırılımdan) · INVARYANT_PARCA (bölüm rozetleri
                  sayfayı BÖLER) · INVARYANT_ALT (düz bağ rozeti alt kümedir) ·
                  INVARYANT_KAPSAM[_PARCA|_ALT] (aynı hüküm HER `?kategori=` kolunda) ·
                  SAYAC_KIRILIMLI/SAYAC_N/SAYAC_VAR/SAYAC_BOLUM_BILINEN (fail-closed
                  envanter: kırılımsız/tanınmayan/eksik rozet KIRMIZI). ÖRNEKLEME YOK:
                  93 marka + 1052 model sayfasının TAMAMI × her kapsam kolu.

Kullanım:
  python3 tools/marka-sayac-kapisi.py            # kapı (rc=0 yeşil, rc=1 kırmızı)
  python3 tools/marka-sayac-kapisi.py --iz       # yalnız kaynak izi (mutasyon kanıtı)
  python3 tools/marka-sayac-kapisi.py --ozet     # kapı + AUDI/mükerrer özet satırları
FAIL-CLOSED: ölçüm kurulamazsa rc=3 (ÖLÇÜLEMEDİ) — yeşil sayılmaz.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

# Marka sayfası HTML tavanı = ana sayfanın (index.html) 7 Ağu'da ölçülen baytı.
# Okan hükmü: en büyük marka sayfası ana sayfayı AŞMASIN. SABİT tutulur (index.html de
# büyüyor; tavanı ona bağlamak tavanı kendiliğinden gevşetirdi → pencere-göreli alarm tuzağı
# [[pencere-goreli-alarm-kendini-sonduruyor]]).
HTML_TAVAN = 213155

# Marka sayfasında SSR'de basılması BEKLENEN tam kart sayısı. 🔴 BİLEREK KAPININ KENDİ
# BEYANI (`mm.MARKA_KART_N` import EDİLMEZ): sabiti ithal eden iddia, sabiti değiştiren
# mutantı yeşil geçirir — çapa ÜRETİLEN HTML'e bağlanır, jeneratörün sabitine değil.
# Değer değişecekse burada da BİLEREK değişmeli (iki taraflı, görünür karar).
BEKLENEN_KART_N = 80

# 🔴 SCRIPT GÖVDESİ SAYFA İÇERİĞİ DEĞİLDİR. Artım modülü (PRUVO_ARTIM.kartHtml) kart
# şablonunu JS içinde taşır; script'i soymadan tarayan bir ölçüm o ŞABLONU kart SAYAR
# (ölçüldü: her marka sayfasında +1 hayalet kart, kimlik iddiası +1 sapardı).
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
# data-kat'ten SONRA ek alan gelebilir (data-mm = model üyeliği; sayfa-içi filtre bundan süzer).
KART_RE = re.compile(r'<div class="card" data-kat="([^"]*)"[^>]*><a class="card-main" '
                     r'href="([^"]+)"')
# Model sayfası OLMAYAN kalemlerin düz bağ girdileri (kart değil, ama sayfada GÖRÜNÜR öğe ve
# sayfadan ULAŞILABİLİR kalem: ulaşılabilirlik kümesine kartlarla AYNI ağırlıkta girer).
BAG_RE = re.compile(r'<li class="mm-kalan-oge" data-kat="([^"]*)"><a href="([^"]+)"')
BTN_RE = re.compile(r'<a class="mm-model-btn" href="([^"]+)" data-katsay="([^"]*)"')
TOPLAM_RE = re.compile(r'<p class="mm-toplam" data-katsay="([^"]*)">.*?'
                       r'<span class="mm-sayim-toplam">(\d+)</span>')
SAYIM_KART_RE = re.compile(r'<span class="mm-sayim-kart">(\d+)</span>')
SAYIM_MODEL_RE = re.compile(r'<span class="mm-sayim-model">(\d+)</span>')
# BÖLÜM SAYACI — başlıklardaki "(N)". 🔴 12 Ağu 2026: bu sayı O AN BASILANI yazıyordu
# (`MARKA_KART_N` tavanı), sayfadan ERİŞİLEBİLENİ değil; beyan cümlesiyle AYNI sayfada
# ayrışıyordu (canlı: beyan 593 ↔ başlık 80; kapsam kolunda 575 ↔ 304). Artık her başlık
# KENDİ kümesinin kategori kırılımını taşır ve INVARYANT ekseni bu kırılımı BAĞIMSIZ
# ölçülen erişim kümesiyle karşılaştırır.
BOLUM_RE = re.compile(r'<span class="mm-sayim-kart" data-bolum="([^"]*)" '
                      r'data-katsay="([^"]*)">(\d+)</span>')
# Artım manifesti (istemcinin veri yolunu BEYAN ettiği yer). 🔴 Kapı bu beyanı KANONİK
# değerle karşılaştırır; sayfanın kendi beyanını "doğru" kabul ETMEZ (bkz. TESLIM_YOLU).
MANIFEST_RE = re.compile(r'<script type="application/json" id="mmManifest">(.*?)</script>', re.S)


def coz_katsay(ham):
    return json.loads(ham.replace("&quot;", '"').replace("&amp;", "&"))


def urun_id(href):
    return href.strip("/").split("/")[-1]


# --------------------------------------------------------------------------- node harness
_JS_HARNESS = r"""
"use strict";
const fs = require("fs");
const vm = require("vm");
const VERI = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));

const ctx = { window: {}, JSON: JSON, String: String, Object: Object,
              URLSearchParams: URLSearchParams,
              console: {log(){}, warn(){}, error(){}} };
vm.runInNewContext(VERI.kapsamJs, ctx, {filename: "kapsam.js", timeout: 10000});
const K = ctx.window.PRUVO_KAPSAM;
if(!K){ console.log(JSON.stringify({hata: "PRUVO_KAPSAM tanimlanmadi"})); process.exit(0); }

function shim(sayfa){
  const kartlar = sayfa.kartlar.map((kat) => ({
    style: {display: ""}, getAttribute: (n) => (n === "data-kat" ? kat : null)}));
  // DÜZ BAĞ ÖĞELERİ de şimlenir. 🔴 NEDEN ZORUNLU: `uygula()` bu öğeleri AYRI bir seçiciyle
  // (.mm-kalan-oge[data-kat]) süzüyor; şim onları vermezse o dal HİÇ koşmaz ve "bağ öğeleri
  // kapsam dışında da ekranda kalıyor" kusuru kapıdan sessizce geçerdi (fail-open).
  const duzler = (sayfa.baglar || []).map((kat) => ({
    style: {display: ""}, getAttribute: (n) => (n === "data-kat" ? kat : null)}));
  const butonlar = sayfa.butonlar.map((b) => {
    const adet = {textContent: ""};
    const attrs = {"data-katsay": b.katsay, href: b.href};
    return {style: {display: ""}, attrs,
            getAttribute: (n) => (attrs[n] === undefined ? null : attrs[n]),
            setAttribute: (n, v) => { attrs[n] = v; },
            querySelector: (s) => (s === ".adet" ? adet : null)};
  });
  const toplamEl = sayfa.toplamKatsay === null ? [] : [{
    getAttribute: (n) => (n === "data-katsay" ? sayfa.toplamKatsay : null)}];
  const sayimToplam = {textContent: ""};
  const sayimKart = {textContent: ""};
  const sayimModel = {textContent: ""};
  // BÖLÜM SAYAÇLARI: başlıkların taşıdığı "(N)". Şim onları vermezse `bolumSayaclari()`
  // dalı HİÇ koşmaz ve "başlık o an basılanı yazıyor" kusuru kapıdan sessizce geçerdi.
  const bolumler = (sayfa.bolumler || []).map((b) => {
    const attrs = {"data-bolum": b.bolum, "data-katsay": b.katsay};
    return {bolum: b.bolum, textContent: String(b.n),
            getAttribute: (n) => (attrs[n] === undefined ? null : attrs[n])};
  });
  const kutu = {
    kapsamNot: {style: {display: "none"}},
    kapsamNotMetin: {textContent: ""},
    kapsamNotSifirla: {attrs: {href: "./"},
                       getAttribute(n){ return this.attrs[n]; },
                       setAttribute(n, v){ this.attrs[n] = v; }},
    kapsamBos: {style: {display: "none"}}
  };
  const harita = {
    ".card[data-kat]": kartlar,
    ".mm-kalan-oge[data-kat]": duzler,
    ".mm-model-btn[data-katsay]": butonlar,
    ".mm-toplam[data-katsay]": toplamEl,
    "a[data-kapsam-tasi]": [],
    ".mm-sayim-kart": [sayimKart],
    ".mm-sayim-kart[data-katsay]": bolumler,
    ".mm-sayim-model": [sayimModel],
    ".mm-sayim-toplam": [sayimToplam]
  };
  return {dok: {querySelectorAll: (s) => (harita[s] || []),
                getElementById: (id) => (kutu[id] || null)},
          kartlar, duzler, kutu, sayimToplam, bolumler};
}

// SENTETİK FAIL-CLOSED FİKSTÜRLERİ: gerçek sayfalarda kırılım HEP sağlamdır, bu yüzden
// "kırılım yok/bozuk/tutarsız" dalları gerçek katalogla ÖLÇÜLEMEZ (fail-open mutantı hayatta
// kalırdı). Bu fikstürler o dalları tek tek zorlar.
const sentetik = {};
for(const f of VERI.sentetik){
  const s = shim(f);
  K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(f.kategori), pathname: "/x/"});
  sentetik[f.ad] = {serit: s.kutu.kapsamNotMetin.textContent, rozet: s.sayimToplam.textContent,
                    bolum: s.bolumler.map((b) => b.textContent)};
}

// ARTIM MODÜLÜ: istemcinin çizeceği kart gövdesi Python `_kart` ile BAYT-AYNI mı.
// (Kart başlığı/fiyatı Python'da bağlam-duyarlı kurallarla üretilir; JS'e PORT edilmedi,
// yalnız SAPMA override olarak taşınır. Bu eksen o sözleşmenin GERÇEKTEN tutduğunu ölçer —
// tutmazsa "tümünü göster" sonrası kartlar sessizce ayrışırdı.)
const artim = {kuruldu: false, kartlar: {}, suz: null};
if(VERI.artimJs){
  const actx = {window: {}, JSON: JSON, String: String, Object: Object, console: ctx.console};
  vm.runInNewContext(VERI.artimJs, actx, {filename: "artim.js", timeout: 10000});
  const A = actx.window.PRUVO_ARTIM;
  if(A){
    artim.kuruldu = true;
    for(const kayit of VERI.kartDenekleri){
      artim.kartlar[kayit.id] = A.kartHtml(kayit.urun, kayit.o, VERI.site, A.mmAttr(kayit.kalem));
    }
    // TESLİM YOLU: modülün KENDİ kurduğu istek adresi + partileme (kanonikle karşılaştırılır)
    artim.istek = {
      adres: A.istekAdresi(VERI.manifestOrnek, ["a-1", "b-2"]),
      parti_n: A.partile(VERI.partiDenek, VERI.manifestOrnek.parti).length,
      parti_ilk: A.partile(VERI.partiDenek, VERI.manifestOrnek.parti)[0].length,
      manifest_kabul: !!A.manifest({getElementById: () => ({textContent: VERI.manifestMetni})}),
      // FAIL-CLOSED: uc/yol/parti eksik manifest REDDEDİLMELİ (null dönmeli)
      manifest_red: !A.manifest({getElementById: () => ({textContent: VERI.manifestEksik})})
    };
    // suz(): model + kapsam süzgeci (sayfa-içi filtrenin çekirdeği)
    artim.suz = {
      hepsi: A.suz(VERI.suzYuk, null, null).map((k) => k[0]),
      model0: A.suz(VERI.suzYuk, 0, null).map((k) => k[0]),
      kategori: A.suz(VERI.suzYuk, null, VERI.suzKategori).map((k) => k[0]),
      bozuk: A.suz(null, null, null).length
    };
  }
}

const cikti = {sentetik: sentetik, artim: artim};
for(const yol of Object.keys(VERI.sayfalar)){
  const sayfa = VERI.sayfalar[yol];
  const kayit = {filtresiz: null, kategoriler: {}};
  // filtresiz: kapsam PASİF -> sayfaya dokunulmaz; kanonik toplam yine de okunabilmeli
  kayit.filtresiz = K.toplamla(shim(sayfa).dok, K.coz(null, VERI.kategoriler));
  for(const kat of sayfa.olcumKategorileri){
    const s = shim(sayfa);
    K.uygula(s.dok, {search: "?kategori=" + encodeURIComponent(kat), pathname: "/" + yol + "/"});
    kayit.kategoriler[kat] = {
      serit: s.kutu.kapsamNotMetin.textContent,
      rozet: s.sayimToplam.textContent,
      gorunenKart: s.kartlar.filter((k) => k.style.display !== "none").length,
      gorunenDuz: s.duzler.filter((k) => k.style.display !== "none").length,
      gizlenenDuz: s.duzler.filter((k) => k.style.display === "none").length,
      // Başlıkların kapsam altında BASTIĞI sayılar (INVARYANT ekseninin istemci ucu).
      bolum: s.bolumler.map((b) => ({bolum: b.bolum, metin: b.textContent}))
    };
  }
  cikti[yol] = kayit;
}
console.log(JSON.stringify(cikti));
"""


class Kapi:
    """İddia defteri + İNSANA GÖSTERİLEN ÖZETİN TEK KAYNAĞI.

    🔴 NEDEN SAYFA BURADA KAYITLI (12 Ağu 2026, bağımsız çürütücü — bu kapının KENDİ
    içinde, tam da bu işin onardığı sınıf): kapı `DUSEN=2292 HUKUM=KIRMIZI` derken
    `--dokum` özeti "sapan marka 0" basıyordu. Sebep İKİ AYRI SAYIM NOKTASIYDI: hüküm
    `self.dusen`den, özet ise AYRI bir karşılaştırmadan (üretilen toplam != gerçek toplam)
    doğuyordu. Onarılan kusurun aynısı: kabul kümesi ile özet/kıyas kümesi ayrı
    fonksiyonlardan türeyince SESSİZCE ayrışır ([[kabul-araligi-karsilastirma-araligi]] ·
    [[ikiz-tanim-sessiz-ayrisma]]). Yarın biri `--dokum`a bakıp "sapan 0, sorun yok" der
    ve kapı KIRMIZIYKEN iş kapanır.

    ÇÖZÜM: özet, HÜKMÜ BESLEYEN `self.dusen` kümesinden türer — ikinci sayım noktası YOK.
    Sapan sayfa, düşen iddianın KENDİ kimliğinden çözülür (`sayfa_coz`). Kaçış deliği
    `OZET_KANONIK/aile_bilinen` ile fail-closed KIRMIZI kapatılır: sayfaya çözülmeyen bir
    düşen iddia, KÜRESEL aile listesinde BEYAN EDİLMİŞ olmak zorundadır."""

    def __init__(self):
        self.gecen = 0
        self.dusen = []
        self.sayfalar = frozenset()      # sayfa evreni (tara()'dan sonra atanır)

    def iddia(self, kimlik, kosul, detay="", sayfa=None):
        if kosul:
            self.gecen += 1
        else:
            self.dusen.append(kimlik + ((" — " + detay) if detay else ""))

    @property
    def taban(self):
        return self.gecen + len(self.dusen)

    def sayfa_coz(self, dusen_satiri):
        """Bir DÜŞEN satırının ait olduğu sayfa yolu (yoksa None).
        Kimlik biçimi: `<AILE>/<sayfa yolu>[/<kategori|indeks>] — <detay>`."""
        parcalar = dusen_satiri.split(" — ")[0].split("/")
        for n in range(len(parcalar), 1, -1):
            aday = "/".join(parcalar[1:n])
            if aday in self.sayfalar:
                return aday
        return None

    @property
    def sapan_sayfalar(self):
        """İNSANA GÖSTERİLEN ÖZETİN TEK KAYNAĞI — hükmü besleyen kümeden türer."""
        return {y for y in (self.sayfa_coz(d) for d in self.dusen) if y}


# 🔴 SAYFAYA BAĞLI OLMAYAN (küresel) iddia aileleri — TEK TEK BEYAN EDİLİR.
# Düşen bir iddia ne bir sayfaya çözülüyor ne de burada beyan edilmişse kapı
# `OZET_KANONIK/aile_bilinen` ile KIRMIZI yanar: yeni bir eksen sayfa taşımayan bir
# kimlik biçimiyle eklenirse özet onu SESSİZCE saymaz olurdu — kabul kümesi ile özet
# kümesinin ayrışması bu depoda ölçülmüş bir sınıftır.
KURESEL_AILELER = frozenset({
    "BIRIM_TEKIL", "BIRIM_KALEM", "BIRIM_AYRIM", "MARKA_LITERAL", "FAIL_CLOSED",
    "TESLIM_KANON", "ARTIM", "ARTIM_SUZ", "ARTIM_ADRES", "JS_SENTETIK",
    "JS_DUZ_KONTROL", "OZET_KANONIK",
})


def kaynak_izi():
    """Mutasyonun UYGULANDIĞINI kanıtlayan iz: ölçülen kaynak dosyaların sha1'i.
    (Aynı uzunlukta mutasyon + bytecode önbelleği tuzağı: mutant koşumu bu izi BASAR;
    iz değişmemişse mutasyon uygulanmamıştır ve o tur SAYILMAZ.)"""
    h = hashlib.sha1()
    for ad in ("marka_model_build.py",):
        with open(os.path.join(TOOLS, ad), "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


def sayfalari_uret(tmp):
    import build                      # noqa: PLC0415
    import marka_model_build as mm    # noqa: PLC0415
    with open(os.path.join(build.ROOT, "urunler.json"), encoding="utf-8") as f:
        products = json.load(f)
    ctx = build.marka_model_ctx()
    ctx["ROOT"] = tmp
    shutil.copy(os.path.join(build.ROOT, "index.html"), os.path.join(tmp, "index.html"))
    with open(os.path.join(build.ROOT, "index.html"), encoding="utf-8") as f:
        index_html = f.read()
    mm.uret(products, ctx)
    return products, mm, index_html, ctx


def tara(tmp):
    kok = os.path.join(tmp, "marka")
    sayfalar = {}
    for dirpath, _dn, filenames in os.walk(kok):
        if "index.html" not in filenames:
            continue
        rel = os.path.relpath(dirpath, tmp).replace(os.sep, "/")
        if rel == "marka":
            continue                          # /marka/ dizini: kart/kova yok
        yol = os.path.join(dirpath, "index.html")
        with open(yol, encoding="utf-8") as f:
            ham = f.read()
        page = SCRIPT_RE.sub("", ham)          # script gövdesi içerik değil (bkz. SCRIPT_RE)
        kartlar = [(kat, urun_id(href)) for kat, href in KART_RE.findall(page)]
        baglar = [(kat, urun_id(href)) for kat, href in BAG_RE.findall(page)]
        butonlar = [(href, coz_katsay(ks)) for href, ks in BTN_RE.findall(page)]
        # ARTIM YÜKÜ: sayfanın kart YÜZEYİNİN kanonik listesi (SSR'de basılı olmayan kalemler
        # bu sayfada artımlı çizilir). Yük YOKSA None -> kimlik iddiası bunu KIRMIZI sayar.
        yuk = None
        yuk_yolu = os.path.join(dirpath, "parcalar.json")
        if os.path.exists(yuk_yolu):
            try:
                with open(yuk_yolu, encoding="utf-8") as f:
                    yuk = json.load(f)
            except Exception:                                     # noqa: BLE001
                yuk = "BOZUK"
        mm_man = MANIFEST_RE.search(ham)
        manifest = None
        if mm_man:
            try:
                manifest = json.loads(mm_man.group(1))
            except Exception:                                     # noqa: BLE001
                manifest = "BOZUK"
        t = TOPLAM_RE.search(page)
        sayfalar[rel] = {
            "kartlar": kartlar,
            "baglar": baglar,
            "manifest": manifest,
            "artim_js_var": "PRUVO ARTIM BAS" in ham,
            "urunler_json_gecti": "/urunler.json" in ham,
            "yuk": yuk,
            "bayt": os.path.getsize(yol),
            "butonlar": butonlar,
            "toplam_katsay": coz_katsay(t.group(1)) if t else None,
            "toplam_katsay_ham": t.group(1).replace("&quot;", '"') if t else None,
            "toplam": int(t.group(2)) if t else None,
            "sayim_kart": [int(x) for x in SAYIM_KART_RE.findall(page)],
            "sayim_model": [int(x) for x in SAYIM_MODEL_RE.findall(page)],
            # (bolum, kırılım, basılan N) — başlıkların taşıdığı sayı ve kaynağı
            "bolumler": [{"bolum": b, "katsay": coz_katsay(k), "katsay_ham": k.replace(
                "&quot;", '"'), "n": int(n)} for b, k, n in BOLUM_RE.findall(page)],
        }
    return sayfalar


def bagimsiz_uyelik(products, mm, index_html):
    """Katalogdaki GERÇEK marka üyeliği — sayfa üreticisinden BAĞIMSIZ türetme.
    index.html marka filtresiyle aynı yüklem (`marka_uyelikleri`); gruplandir/uret ÇAĞRILMAZ."""
    evren = mm.MarkaEvreni(index_html)
    ek = mm.cip_evreni_markalari(products, index_html)
    uyelik = {}
    for p in products:
        pid = p.get("id")
        if not pid:
            continue
        for kan in mm.marka_uyelikleri(p.get("marka") or [], evren, ek):
            uyelik.setdefault(kan, set()).add(pid)
    # SIRA iddiasının GİRDİSİ (iddiası değil): kovalar. Kapı tekilleştirmeyi KENDİ yazar.
    veri = mm.gruplandir(products, evren, ek)
    return uyelik, veri


def birim_iddialari(kapi):
    """BİRİM EKSENİ — kanonik sayma fonksiyonları, sayfa üretmeden.

    🔴 NEDEN AYRI VE ÖNCE KOŞAR: jeneratörün fail-closed ikiz kontrolü bir kusurda build'i
    DURDURUR; tek başına bırakılsa üç ayrı kusur da aynı "durdu" imzasını üretir ve batarya
    ayırt edemezdi ([[beyan-edilmis-survivor]]). Birim ekseni build'den ÖNCE koşar, bu yüzden
    her kusur kendi kimliğiyle düşer."""
    import marka_model_build as mm      # noqa: PLC0415
    a, b, c = {"id": "a"}, {"id": "b"}, {"id": "c"}
    a2 = {"id": "a"}
    kapi.iddia("BIRIM_TEKIL/mukerrer",
               [p["id"] for p in mm._tekil([a, b], [a2, c])] == ["a", "b", "c"],
               "mükerrer id düşmedi")
    kapi.iddia("BIRIM_TEKIL/sira",
               [p["id"] for p in mm._tekil([c, a, b])] == ["c", "a", "b"],
               "ilk görülen sıra bozuldu")
    kapi.iddia("BIRIM_KALEM/kova",
               [p["id"] for p in mm.sayfa_kalemleri([a], [[b], [c]])] == ["a", "b", "c"],
               "kova kalemleri toplama girmedi")

    # 🔴 İDDİA TERSİNE ÇEVRİLDİ (8 Ağu 2026). ESKİ iddia şuydu:
    #     BIRIM_KALEM/cakisma: len(sayfa_kalemleri([a, b], [[a2, c]])) == 3
    # yani kart kolu ile kova ÇAKIŞABİLİR, tekilleştirme onu yutar — çakışma DOĞRU
    # DAVRANIŞ sayılıyordu. Kapı bu yüzden Okan'ın İKİ KEZ bildirdiği kusuru
    # GÖRMÜYORDU: "Diğer" bölümü kovalarla kesişiyordu ve bölüm kimliği hiç iddia
    # edilmiyordu ([[kapi-beyanin-dogrulugunu-degil-varligini-olcer]]).
    # YENİ hüküm: ÇAKIŞMA İHLALDİR — kovada görünen ürün kart kolundan ELENİR.
    # FAIL-CLOSED, ÇÖKMEDEN: yüklem hiç YOKSA (onarım öncesi jeneratör / kaldıran mutant)
    # kapı KIRMIZI yanar; AttributeError ile çökmez (çökme kırmızıyla karışır ve mutasyon
    # bataryası "öldü mü, patladı mı" ayrımını yapamazdı → [[hukum-yanlis-birimde]]).
    if not hasattr(mm, "bolum_ayrimi"):
        kapi.iddia("BIRIM_AYRIM/yuklem_var", False,
                   "bolum_ayrimi YOK: bölüm ayrımı yüklemi kurulmamış (çakışma hâlâ kutsanıyor)")
        return
    # 🔴 SystemExit YAKALANIR: `bolum_ayrimi`nin İÇ fail-closed'u bu fikstürde yükselirse
    # (eleme bozulmuş demektir) kapı ETİKETLİ bir iddia düşürmeli. Yakalanmazsa SystemExit
    # kapıyı sessizce sonlandırır: rc=1 olur ama HİÇBİR iddia basılmaz ve "kaç iddia
    # ölçüldü" kaybolur — çıkış kodu kırmızı görünürken ölçüm YOKTUR
    # ([[olculdu-diyen-hukum-kaniti]] · [[hukum-yanlis-birimde]]).
    try:
        kart, kalemler, sayilar = mm.bolum_ayrimi([[a, b]], [[a2, c]])
    except SystemExit as e:
        kapi.iddia("BIRIM_AYRIM/eleme", False,
                   "bolum_ayrimi SAĞLAM fikstürde durdu (eleme bozuk): %s" % (str(e)[:120],))
        kapi.iddia("BIRIM_AYRIM/toplam_korunur", False, "ölçülemedi: fonksiyon durdu")
        kapi.iddia("BIRIM_AYRIM/kimlik", False, "ölçülemedi: fonksiyon durdu")
        kapi.iddia("BIRIM_AYRIM/fail_closed_kurulu", False, "ölçülemedi: fonksiyon durdu")
        return
    kapi.iddia("BIRIM_AYRIM/eleme", [p["id"] for p in kart] == ["b"],
               "kovada görünen ürün kart kolundan ELENMEDİ (çakışma hâlâ kutsanıyor): %r"
               % ([p["id"] for p in kart],))
    kapi.iddia("BIRIM_AYRIM/toplam_korunur",
               sorted(p["id"] for p in kalemler) == ["a", "b", "c"],
               "eleme ÜRÜN KAYBETTİRDİ (toplam değişmemeli): %r"
               % (sorted(p["id"] for p in kalemler),))
    kapi.iddia("BIRIM_AYRIM/kimlik",
               sayilar["kart"] + sayilar["kova"] == sayilar["toplam"] == 3,
               "kart %d + kova %d != toplam %d"
               % (sayilar["kart"], sayilar["kova"], sayilar["toplam"]))
    # FAIL-CLOSED: kimlik tutmuyorsa build DURMALI (sessiz yanlış sayı basmaktansa).
    # Tekilleştirme bozulunca kimlik ayrışır; bu dalın GERÇEKTEN yükseldiğini ölç.
    _durdu = False
    try:
        mm.bolum_ayrimi([[a, b], [b]], [[{"id": "b"}]])
    except SystemExit:
        _durdu = True
    except Exception:                                             # noqa: BLE001
        _durdu = False
    try:
        _saglam = mm.bolum_ayrimi([[a]], [[b]])[2]["toplam"] == 2
    except SystemExit:
        _saglam = False
    kapi.iddia("BIRIM_AYRIM/fail_closed_kurulu", _saglam and not _durdu,
               "sağlam girdide kimlik yükseldi ya da toplam bozuk (saglam=%s, durdu=%s)"
               % (_saglam, _durdu))


def marka_literal_iddialari(kapi, mm, index_html):
    """SINIF ONARIMI KAPISI (Okan hükmü): onarım TÜRETMEDE olmalı, marka-özel dalda değil.
    Onarımın dokunduğu her yüzeyde SABİT marka adı sayısı 0 olmalı — bir marka literali
    "bu sayfada çalışıyor" demektir, sınıfın kapandığı anlamına GELMEZ."""
    import inspect                       # noqa: PLC0415
    evren = mm.MarkaEvreni(index_html)
    adlar = sorted(set(evren.taninmis) | set(evren.marka_alias.keys())
                   | set(evren.marka_alias.values()), key=len, reverse=True)
    desen = re.compile(r"(?<![0-9A-Za-zÇĞİÖŞÜçğıöşü])(" +
                       "|".join(re.escape(a) for a in adlar if a) +
                       r")(?![0-9A-Za-zÇĞİÖŞÜçğıöşü])")
    hedefler = {}
    for ad in ("_tekil", "sayfa_kalemleri", "bolum_ayrimi", "_kart_yuk_kaydi",
               "_toplam_bloku", "_bolum_sayaci", "_marka_sayfasi", "_model_sayfasi"):
        fn = getattr(mm, ad, None)
        if fn is not None:                    # yüklem yoksa AYRI eksen kırmızı yakar
            hedefler["mm." + ad] = inspect.getsource(fn)
    for ad, oz in (("mm.KAPSAM_JS", "_KAPSAM_JS_GOVDE"), ("mm.ARTIM_JS", "_ARTIM_JS_GOVDE")):
        govde = getattr(mm, oz, None)
        if govde is not None:
            hedefler[ad] = govde
    for ad in ("marka-sayac-kapisi.py", "marka-sayac-mutasyon.py",
               "marka-invaryant-sayac-mutasyon.py"):
        with open(os.path.join(TOOLS, ad), encoding="utf-8") as f:
            hedefler["tools/" + ad] = f.read()
    for ad, metin in hedefler.items():
        vurus = sorted(set(desen.findall(metin)))
        kapi.iddia("MARKA_LITERAL/" + ad, not vurus, "sabit marka adı: %s" % (vurus,))


def olc(ozet=False, dokum=False, sayfa_detay=None):
    kapi = Kapi()
    birim_iddialari(kapi)
    tmp = tempfile.mkdtemp(prefix="mm-sayac-kapi-")
    try:
        products, mm, index_html, mm_ctx = sayfalari_uret(tmp)
        sayfalar = tara(tmp)
    except SystemExit as e:
        # Jeneratörün FAIL-CLOSED ikiz kontrolü durdurdu: bu da bir ALARM kimliğidir
        # (mutasyon bataryası bunu ayrı bir düşüş imzası olarak sayar, "ölçülemedi" değil).
        kapi.iddia("FAIL_CLOSED/jenerator", False, str(e)[:120])
        print("FAIL-CLOSED: jeneratör durdu: %s" % (str(e)[:200],))
        return 1, kapi, {}
    # 🔴 SAYFALAMA SINIFI (19 Agu 2026, SERIT B onarimi — OLCULEN COKME): sayfalama
    # sayfalari `marka/<slug>/sayfa/<N>` uc egik cizgi tasir; slash sayisina dayanan
    # eski iki-sinif ayrimi (1=marka, 2=model) onlari HICBIR sinifa koymuyordu ve
    # `erisim` sozlugune HIC yazilmiyorlardi -> asagidaki dogrulama dongusu
    # `KeyError: marka/volkswagen/sayfa/18` ile COKUYORDU (kapi hukum vermeden oluyor,
    # yani ekseni sessizce olcusuz kaliyordu). Sayfalama sayfasi ERISIM bakimindan
    # model sayfasiyla ayni desendedir: kendi diliminin kartlarini tasir.
    sayfalama_sayfalari = {k: v for k, v in sayfalar.items() if "/sayfa/" in k}
    marka_sayfalari = {k: v for k, v in sayfalar.items()
                       if k.count("/") == 1 and k not in sayfalama_sayfalari}
    model_sayfalari = {k: v for k, v in sayfalar.items()
                       if k.count("/") == 2 and k not in sayfalama_sayfalari}
    if len(marka_sayfalari) < 50 or len(model_sayfalari) < 500:
        print("OLCULEMEDI: sayfa evreni beklenenden küçük (marka=%d model=%d)"
              % (len(marka_sayfalari), len(model_sayfalari)))
        return 3, kapi, {}

    marka_literal_iddialari(kapi, mm, index_html)
    uyelik, veri = bagimsiz_uyelik(products, mm, index_html)
    slug_marka = {}
    for kan in uyelik:
        slug_marka.setdefault("marka/" + mm._slug(kan), kan)

    # ---------------------------------------------------------- ulaşılabilir tekil kümeler
    erisim = {}          # marka yolu -> {kategori: set(id)}

    def _sayfalama_alt(kok_yol):
        """`<kok>/sayfa/<N>` yuzeyleri — gezintiyle ULASILABILIR devam dilimleri."""
        onek = kok_yol + "/sayfa/"
        return [v for k, v in sayfalama_sayfalari.items() if k.startswith(onek)]

    for yol, s in marka_sayfalari.items():
        kume = {}
        for kat, pid in s["kartlar"]:
            kume.setdefault(kat, set()).add(pid)
        for kat, pid in s["baglar"]:          # düz bağ girdileri de ULAŞILABİLİR kalemdir
            kume.setdefault(kat, set()).add(pid)
        for href, _tablo in s["butonlar"]:
            mp = model_sayfalari.get(href.strip("/"))
            if mp is None:
                continue
            for kat, pid in mp["kartlar"]:
                kume.setdefault(kat, set()).add(pid)
        # 🔴 SAYFALAMA DILIMLERI DE ERISILEBILIR (19 Agu 2026, SERIT B onarimi):
        # sayfalama geldiginden beri kok marka sayfasi markanin TAMAMINI basmiyor,
        # kalani `<yol>/sayfa/<N>` yuzeylerinde ve oraya SAYFA GEZINTISIYLE ulasilir.
        # Kok sayfanin KENDI beyani (build.py `sayfa_kalemleri`, sayfa==1 kolu) zaten
        # TUM erisilebilir kumeyi sayar; erisim turetmesi o dilimleri saymayinca
        # TOPLAM ve KAYIP eksenleri 69 markada KIRMIZI yaniyordu (olculdu — kapi
        # daha once KeyError ile coktugu icin bu satirlar hic gorunmemisti).
        for ds in _sayfalama_alt(yol):
            for kat, pid in ds["kartlar"]:
                kume.setdefault(kat, set()).add(pid)
            for kat, pid in ds["baglar"]:
                kume.setdefault(kat, set()).add(pid)
        erisim[yol] = kume
    for yol, s in model_sayfalari.items():
        kume = {}
        for kat, pid in s["kartlar"]:
            kume.setdefault(kat, set()).add(pid)
        for ds in _sayfalama_alt(yol):        # model sayfasinin kendi sayfalamasi
            for kat, pid in ds["kartlar"]:
                kume.setdefault(kat, set()).add(pid)
        erisim[yol] = kume
    # Sayfalama sayfalari: kendi diliminin kartlari (build.py `sayfa_kalemleri`
    # kolu 1. sayfada tum erisilebilir kumeyi, devam sayfasinda KENDI dilimini
    # beyan eder; erisim de o yuzeyin KENDI kartlarindan turer).
    for yol, s in sayfalama_sayfalari.items():
        kume = {}
        for kat, pid in s["kartlar"]:
            kume.setdefault(kat, set()).add(pid)
        for kat, pid in s["baglar"]:
            kume.setdefault(kat, set()).add(pid)
        erisim[yol] = kume

    def tumu(kume):
        out = set()
        for v in kume.values():
            out |= v
        return out

    mukerrer_toplam = 0
    for yol, s in sayfalar.items():
        ham, tekil = len(s["kartlar"]), len(set(i for _k, i in s["kartlar"]))
        mukerrer_toplam += ham - tekil
        kapi.iddia("MUKERRER/" + yol, ham == tekil, "ham %d, tekil %d" % (ham, tekil))

    # ------------------------------------------------------------------- OKAN HÜKMÜ: KİMLİK
    # 🔴 "Marka sayfası markanın TÜM parçalarını KART olarak listeler" (Okan, 8 Ağu).
    # Ağırlık yüzünden kartların bir kısmı SSR'de basılmaz, AYNI SAYFADA artımlı çizilir;
    # bu yüzden ölçülen birim KART YÜZEYİDİR = SSR kartları ∪ artım yükünün kalemleri.
    # KİMLİK (fail-closed): kart yüzeyi == başlıktaki toplam VE mükerrer == 0, 93/93.
    # Üçü de TEK kanonik kümeden (`sayfa_kalemleri`/`bolum_ayrimi`) türer.
    for yol, s in marka_sayfalari.items():
        yuk = s["yuk"]
        if yuk is None or yuk == "BOZUK" or not isinstance(yuk.get("k"), list):
            kapi.iddia("KIMLIK/" + yol, False,
                       "artım yükü YOK/BOZUK (kart yüzeyi ölçülemez): %r"
                       % (yuk if yuk == "BOZUK" else type(yuk).__name__,))
            kapi.iddia("KIMLIK_MUKERRER/" + yol, False, "yük olmadan mükerrer ölçülemez")
            continue
        yuk_ids = [k[0] for k in yuk["k"] if k and k[0]]
        html_ids = [i for _k, i in s["kartlar"]] + [i for _k, i in s["baglar"]]
        yuzey = set(yuk_ids) | set(html_ids)
        kapi.iddia("KIMLIK/" + yol, len(yuzey) == s["toplam"],
                   "kart yüzeyi %d (SSR kart %d + bağ %d + yük %d), başlık toplamı %s"
                   % (len(yuzey), len(s["kartlar"]), len(s["baglar"]),
                      len(yuk_ids), s["toplam"]))
        # Mükerrer: ne yükün kendi içinde, ne de SSR ile yük arasında ÇİFT kalem olmaz.
        kapi.iddia("KIMLIK_MUKERRER/" + yol,
                   len(yuk_ids) == len(set(yuk_ids))
                   and len(html_ids) == len(set(html_ids)),
                   "yük mükerrer %d, SSR mükerrer %d"
                   % (len(yuk_ids) - len(set(yuk_ids)),
                      len(html_ids) - len(set(html_ids))))

    # ------------------------------------------------- BÖLÜM AYRIMI (çakışma artık İHLAL)
    # Sayfanın YEREL bölümü (SSR kartları + düz bağlar) ile model kovaları AYRIK olmalı.
    # Bu, `BIRIM_AYRIM/eleme`nin GERÇEK sayfalardaki karşılığıdır: onarımdan önce
    # `marka_only`/`ikincil` kovadan elenmediği için 32 sayfada kesişim vardı.
    # 🔴 YEREL BÖLÜM SAYFANIN KENDİ BEYANINDAN OKUNUR, N'DEN BAĞIMSIZ: artım yükündeki bir
    # kalemin model indeksi BOŞSA o kalem hiçbir model kovasında değildir = yerel bölümdedir.
    # (Kart olarak basılıp basılmaması ağırlık kararıdır; bölüm kimliğini DEĞİŞTİRMEZ.)
    for yol, s in marka_sayfalari.items():
        yuk = s["yuk"]
        if isinstance(yuk, dict) and isinstance(yuk.get("k"), list):
            yerel_beyan = set(k[0] for k in yuk["k"] if k and k[0] and not (k[2] or []))
        else:
            # YÜK YOKSA (onarım ÖNCESİ sayfa şekli): sayfa bölümlerini beyan etmiyordur ve
            # kartların TAMAMI "Diğer …" bölümüdür. Eksen o şekilde de ÖLÇÜLEBİLİR kalır —
            # yoksa kapı yalnız onarımdan SONRA anlam taşır ve iki yönlü işaret veremezdi
            # ([[kapi-beyanin-dogrulugunu-degil-varligini-olcer]]).
            yerel_beyan = set(i for _k, i in s["kartlar"])
        kova = set()
        for href, _tablo in s["butonlar"]:
            mp = model_sayfalari.get(href.strip("/"))
            if mp is None:
                continue
            kova |= set(i for _k, i in mp["kartlar"])
        kesisim = yerel_beyan & kova
        kapi.iddia("AYRIK/" + yol, not kesisim,
                   "yerel bölüm ∩ model kovası = %d kalem (bölümler çakışıyor; ekrandaki "
                   "sayılar toplamı vermez)" % (len(kesisim),))
        # Düz bağ listesindeki kalemlerin HEPSİ yerel olmalı: model sayfası OLAN bir kalemi
        # bağ listesine koymak gereksiz bayt, yerel bir kalemi koymamak ÖKSÜZ ürün demektir.
        bag_ids = set(i for _k, i in s["baglar"])
        kapi.iddia("BAG_YEREL/" + yol, bag_ids <= yerel_beyan,
                   "bağ listesinde yerel OLMAYAN %d kalem" % (len(bag_ids - yerel_beyan),))

    # ------------------------------------------------------- TESLİM YOLU (kanonik kaynaktan)
    # 🔴 NEDEN BÖYLE (bağımsız çürütme, mutant X3): testler fetch adresini SAYFANIN KENDİ
    # BEYANINDAN okuyorsa, adresi bozan mutant YEŞİL geçer — canlıda 32 büyük marka sayfası
    # tek ek kart çizmez ve kimse görmez. Bu yüzden beyan, KANONİK kaynaktan BAĞIMSIZ
    # ayıklanan değerle KARŞILAŞTIRILIR. Kanonik kaynak = index.html'in `EDGE_UC`'si;
    # kapı onu KENDİ deseniyle çıkarır (jeneratörün fonksiyonunu çağırmaz -> tautoloji yok).
    kanon_uc = None
    _m_uc = re.search(r'var\s+EDGE_UC\s*=\s*"([^"]+)"', index_html)
    if _m_uc:
        kanon_uc = _m_uc.group(1).rstrip("/")
    kapi.iddia("TESLIM_KANON/uc_ayiklandi", bool(kanon_uc),
               "index.html'de EDGE_UC bulunamadı: teslim yolu kanonik kaynaktan "
               "DOĞRULANAMAZ (fail-closed)")
    KANON_YOL = "/katalog?ids="
    for yol, s in marka_sayfalari.items():
        man = s["manifest"]
        if man is None:
            # Manifest YOKSA: sayfanın SSR kartları toplamı KARŞILAMALI, yoksa kalan
            # kalemlere ulaşan hiçbir yol yok demektir.
            kapi.iddia("TESLIM/" + yol, len(s["kartlar"]) >= (s["toplam"] or 0),
                       "manifest YOK ama SSR kart %d < toplam %s: kalan kalemlere ulaşan "
                       "YOL YOK" % (len(s["kartlar"]), s["toplam"]))
            continue
        if man == "BOZUK":
            kapi.iddia("TESLIM/" + yol, False, "manifest BOZUK JSON")
            continue
        kapi.iddia("TESLIM/" + yol,
                   man.get("uc") == kanon_uc and man.get("yol") == KANON_YOL
                   and man.get("parti") == 100 and man.get("site") == mm_ctx["SITE"]
                   and man.get("yuk") == "/" + yol + "/parcalar.json",
                   "beyan edilen teslim yolu KANONİKTEN ayrıştı: uc=%r (kanon %r) yol=%r "
                   "(kanon %r) parti=%r yuk=%r site=%r"
                   % (man.get("uc"), kanon_uc, man.get("yol"), KANON_YOL,
                      man.get("parti"), man.get("yuk"), man.get("site")))
        # 🔴 AĞIRLIK REGRESYON NÖBETİ: sayfa hiçbir yerde TÜM KATALOGU göstermemeli.
        # (İlk yazımda artım kolu `/urunler.json` çekiyordu: 21.330.991 B ham /
        # 3.133.127 B gzip, 32 sayfada, kaydırmada otomatik.)
        kapi.iddia("TESLIM_AGIRLIK/" + yol, not s["urunler_json_gecti"],
                   "sayfada `/urunler.json` geçiyor: tüm katalog indirme yolu geri gelmiş "
                   "(ana sayfa bu deseni EDGE_KATALOG ile bilerek terk etti)")

    # ------------------------------------------------------------------------- AĞIRLIK
    # 🔴 NEDEN KAPI (Okan hükmü + ölçülmüş drift sınıfı): "1,27 MB kabul edilemez".
    # Ağırlık ONARILDI ama katalog HER PARTİDE büyüyor; tavanı kapıya yazmazsak bir sonraki
    # parti sayfayı sessizce yeniden şişirir ([[envanter-drift-parti-basina]]).
    for yol, s in marka_sayfalari.items():
        kapi.iddia("AGIRLIK/" + yol, s["bayt"] <= HTML_TAVAN,
                   "üretilen HTML %d bayt > tavan %d" % (s["bayt"], HTML_TAVAN))

    for yol, s in sayfalar.items():
        # 🔴 FAIL-CLOSED (19 Agu 2026): erisim turetmesi bu yolu URETMEDIYSE eskiden
        # KeyError ile COKUYORDUK — cokme hukum DEGILDIR, o yuzey sessizce olcusuz
        # kalirdi. Artik ADIYLA KIRMIZI: yeni bir sayfa SINIFI (or. sayfalama)
        # eklendiginde erisim turetmesinin de genisletilmesi ZORUNLU olur.
        if yol not in erisim:
            kapi.iddia("ERISIM_TURETILMEDI/" + yol, False,
                       "sayfa taramada VAR ama erisim turetmesi bu yolu URETMEDI -> "
                       "yeni bir sayfa sinifi eklenmis ve turetme genisletilmemis "
                       "(sinif ayrimi: marka=1 egik cizgi, model=2, sayfalama=/sayfa/)")
            continue
        kume = tumu(erisim[yol])
        kapi.iddia("TOPLAM/" + yol, s["toplam"] == len(kume),
                   "SSR %s, ulaşılabilir %d" % (s["toplam"], len(kume)))
        tablo = s["toplam_katsay"] or {}
        kapi.iddia("KIRILIM/" + yol, sum(tablo.values()) == (s["toplam"] or -1),
                   "kırılım %d, SSR %s" % (sum(tablo.values()), s["toplam"]))
        beklenen_tablo = {k: len(v) for k, v in erisim[yol].items() if k}
        kapi.iddia("KIRILIM_KAT/" + yol, tablo == beklenen_tablo,
                   "gömülü %r != ölçülen %r" % (tablo, beklenen_tablo))

    # ═══════════════════════════════════════════════ İNVARYANT (12 Ağu 2026, Okan, canlı)
    # 🔴 BELİRTİ: aynı marka için ekranda DÖRT ayrı sayı — beyan 593 · başlık 80 ·
    # kapsam beyanı 575 · kapsam başlığı 304. Hata SESSİZ: sayfa "çalışıyor" görünüyor.
    # HÜKÜM: sayfada BEYAN EDİLEN parça sayısı == o yüzeyde ERİŞİLEBİLEN kart sayısı.
    # 🔴 ÖRNEKLEME YOK: TÜM marka VE model sayfaları (sayı beyan eden her yüzey) ölçülür;
    # erişim kümesi kapının KENDİ türetmesidir (SSR kart ∪ düz bağ ∪ model sayfası kartı),
    # sayfanın kendi beyanı "doğru" KABUL EDİLMEZ.
    for yol, s in sayfalar.items():
        gercek_tablo = {k: len(v) for k, v in erisim[yol].items() if k}
        gercek = len(tumu(erisim[yol]))
        bl = s["bolumler"]
        eris = [b for b in bl if b["bolum"] == "erisim"]
        parca = [b for b in bl if b["bolum"] == "parca"]
        alt = [b for b in bl if b["bolum"] == "alt"]
        # (a) FAIL-CLOSED ENVANTER: kırılım TAŞIMAYAN sayım rozeti KALMAYACAK. Böyle bir
        # rozet istemcide DOM sayımına düşer = onarılan kusurun geri gelme yolu.
        kapi.iddia("SAYAC_KIRILIMLI/" + yol, not s["sayim_kart"],
                   "kırılım taşımayan %d sayım rozeti var (istemcide DOM sayımına düşer): %r"
                   % (len(s["sayim_kart"]), s["sayim_kart"][:5]))
        # 🔴 İKİ YÖNLÜ İŞARET: kapı onarım ÖNCESİ sayfa şeklini de ÖLÇEBİLİR kalmalı,
        # yoksa "kaç sayfa GERÇEKTEN yalan sayı basıyordu" sorusu repo araçlarıyla
        # yeniden üretilemez ve geçici bir betiğe mahkûm olur
        # ([[mutasyon-kaniti-yeniden-uretilebilir]] aynı ilke: ölçüm repoda koşar durur).
        # Kırılımsız rozet TAŞIYAN sayfalarda o rozetin DEĞERİ erişilebilir toplam mı?
        # (Onarım sonrası kırılımsız rozet KALMADIĞI için bu eksen boş geçer.)
        if s["sayim_kart"]:
            kapi.iddia("SAYAC_ESKI_DEGER/" + yol,
                       all(n == gercek for n in s["sayim_kart"]),
                       "kırılımsız başlık sayısı %r != erişilebilir %d (sayfa YALAN SAYI "
                       "basıyor)" % (s["sayim_kart"], gercek))
        kapi.iddia("SAYAC_BOLUM_BILINEN/" + yol, len(eris) + len(parca) + len(alt) == len(bl),
                   "tanınmayan data-bolum: %r"
                   % (sorted(set(b["bolum"] for b in bl) - {"erisim", "parca", "alt"}),))
        # (b) her rozetin BASTIĞI sayı KENDİ kırılımının toplamıdır (tek kaynak)
        for i, b in enumerate(bl):
            kapi.iddia("SAYAC_N/%s/%d" % (yol, i), b["n"] == sum(b["katsay"].values()),
                       "basılan %d != kendi kırılımının toplamı %d (bolum=%s)"
                       % (b["n"], sum(b["katsay"].values()), b["bolum"]))
        # (c) 🔴 ÇEKİRDEK: "erisim" rozeti sayfanın TÜM erişilebilir yüzeyini beyan eder —
        # SAYISI da KIRILIMI da bağımsız ölçülenle BİREBİR.
        for i, b in enumerate(eris):
            kapi.iddia("INVARYANT_SSR/%s/%d" % (yol, i),
                       b["n"] == gercek and b["katsay"] == gercek_tablo,
                       "başlık %d / kırılım %r != erişilebilir %d / %r"
                       % (b["n"], b["katsay"], gercek, gercek_tablo))
        # (d) BEYAN ile BAŞLIK TEK kanonik kırılımdan doğar (iki sayı ayrışamaz)
        if eris:
            kapi.iddia("INVARYANT_BEYAN/" + yol,
                       all(b["katsay"] == (s["toplam_katsay"] or {}) and b["n"] == s["toplam"]
                           for b in eris),
                       "başlık beyan cümlesinden AYRIŞTI (başlık %r, beyan %r)"
                       % ([b["n"] for b in eris], s["toplam"]))
        # (e) "parca" rozetleri sayfayı BÖLER: kategori kategori toplamları erişim kümesi
        if parca:
            top = {}
            for b in parca:
                for k, v in b["katsay"].items():
                    top[k] = top.get(k, 0) + v
            kapi.iddia("INVARYANT_PARCA/" + yol, top == gercek_tablo,
                       "bölüm rozetleri toplamı %r != erişilebilir %r" % (top, gercek_tablo))
        # (f) "alt" rozeti erişim kümesinin ALT kümesidir (kategori kategori)
        for i, b in enumerate(alt):
            asan = {k: v for k, v in b["katsay"].items() if v > gercek_tablo.get(k, 0)}
            kapi.iddia("INVARYANT_ALT/%s/%d" % (yol, i), not asan,
                       "alt bölüm rozeti erişim kümesini AŞIYOR: %r" % (asan,))
        # (g) sayı beyan eden her yüzeyde rozet BULUNMALI: yoksa "başlık sayı taşımasın"
        # kararı sessizce alınmış olur ve invaryant ölçülemez hâle gelir (dejenere yeşil).
        kapi.iddia("SAYAC_VAR/" + yol,
                   len(eris) >= 1 if yol.count("/") == 1 else len(parca) >= 1,
                   "sayfa hiç bölüm rozeti taşımıyor (kart yüzeyi beyan edilmiyor)")

    for yol, marka in slug_marka.items():
        s = marka_sayfalari.get(yol)
        if s is None:
            continue                       # eşik altı marka: sayfa yok (ayrı eksen)
        kapi.iddia("KAYIP/" + yol, tumu(erisim[yol]) == uyelik[marka],
                   "sayfa %d, katalog %d, eksik %d, fazla %d"
                   % (len(tumu(erisim[yol])), len(uyelik[marka]),
                      len(uyelik[marka] - tumu(erisim[yol])),
                      len(tumu(erisim[yol]) - uyelik[marka])))

    # SIRA: tekilleştirme kart dizilimini yeniden DİZMEZ — İLK GÖRÜLEN KALIR.
    # 🔴 Kapı KENDİ tekilleştirmesini yazar (mm._tekil'i ÇAĞIRMAZ): jeneratörün fonksiyonunu
    # çağırsaydı "sırayı bozacak şekilde tekilleştir" mutantı kapıyı da bozar ve iddia
    # tautolojiye düşerdi (mutant yeşil geçerdi).
    def yerel_tekil(diziler):
        out, gor = [], set()
        for dz in diziler:
            for pid in dz:
                if pid in gor:
                    continue
                gor.add(pid)
                out.append(pid)
        return out

    for yol, s in marka_sayfalari.items():
        marka = slug_marka.get(yol)
        d = veri.get(marka) if marka else None
        if d is None:
            kapi.iddia("SIRA/" + yol, False, "marka kovası bulunamadı")
            continue
        gruplar = list(d["gruplar"].values())
        buyuk = [g for g in gruplar if mm.yayimlanir_mi(g)]
        yayimda = set()
        for g in buyuk:
            yayimda.update(p.get("id") for p in g["urunler"] if p.get("id"))
        kucuk, gor = [], set()
        for g in gruplar:
            if mm.yayimlanir_mi(g):
                continue
            for p in g["urunler"]:
                pid = p.get("id")
                if pid in yayimda or pid in gor:
                    continue
                gor.add(pid)
                kucuk.append(pid)
        # 🔴 BÖLÜM AYRIMI KAPININ KENDİ YÜKLEMİYLE KURULUR (mm.bolum_ayrimi ÇAĞRILMAZ):
        # jeneratörün fonksiyonunu çağırsaydık "elemeyi kaldır" mutantı kapıyı da bozar,
        # iddia tautolojiye düşer ve mutant YEŞİL geçerdi.
        beklenen_yerel = [pid for pid in yerel_tekil(
            [kucuk,
             [p.get("id") for p in d["marka_only"]],
             [p.get("id") for p in d.get("ikincil", [])]]) if pid not in yayimda]
        # Yerel bölüm sayfada İKİ yerde durur: ilk N kalem KART, kalanı DÜZ BAĞ. İkisinin
        # SIRALI birleşimi (kart yüzeyinin yerel kısmı + bağ listesi) kanonik yerel dizilime
        # eşit olmalı — tekilleştirme/eleme sırayı YENİDEN DİZMEZ.
        yerel_kume = set(beklenen_yerel)
        gercek = ([i for _k, i in s["kartlar"] if i in yerel_kume]
                  + [i for _k, i in s["baglar"]])
        kapi.iddia("SIRA/" + yol, gercek == beklenen_yerel,
                   "yerel bölüm dizilimi ayrıştı (sayfa %d = yerel kart %d + bağ %d, "
                   "beklenen %d, ilk fark %s)"
                   % (len(gercek), len([1 for _k, i in s["kartlar"] if i in yerel_kume]),
                      len(s["baglar"]), len(beklenen_yerel),
                      next((n for n, (a, b) in enumerate(zip(gercek, beklenen_yerel))
                            if a != b), "uzunluk")))
        # SSR'de basılan kart sayısı N tavanına UYMALI (ağırlık onarımının davranışsal ucu):
        # N aşılırsa sayfa yeniden şişer, N'den az basılırsa ilk boya sessizce zayıflar.
        # 🔴 DAVRANIŞSAL ÇAPA, SABİT İTHALİ DEĞİL (bağımsız çürütme, mutant X1): iddia
        # `mm.MARKA_KART_N`'i import ederse N'i 80->40 yapan mutant YEŞİL kalır (tautoloji).
        # Beklenen değer BURADA BEYAN EDİLİR (BEKLENEN_KART_N) ve ÜRETİLEN HTML'deki kart
        # sayısıyla karşılaştırılır. Sınırın İKİ YANI ayrı iddiadır: N'i aşan sayfa TAM N
        # basmalı, N'in altındaki sayfa TAMAMINI basmalı — tek iddia olsaydı "hep toplam bas"
        # mutantı büyük sayfalarda yakalanır, küçük sayfalarda görünmezdi.
        toplam_n = s["toplam"] or 0
        if toplam_n > BEKLENEN_KART_N:
            kapi.iddia("KART_N_TAVAN/" + yol, len(s["kartlar"]) == BEKLENEN_KART_N,
                       "toplam %d > N: SSR kart %d, beyan edilen N %d"
                       % (toplam_n, len(s["kartlar"]), BEKLENEN_KART_N))
        else:
            kapi.iddia("KART_N_ALTI/" + yol, len(s["kartlar"]) == toplam_n,
                       "toplam %d <= N: SSR kart %d (tamamı basılmalı)"
                       % (toplam_n, len(s["kartlar"])))
        # Manifestin BEYAN ettiği `basili` sayısı GERÇEKTEN basılan kart sayısı olmalı
        # (ayrışırsa istemci yanlış yerden devam eder: kalemleri atlar ya da tekrar çizer).
        man_b = s["manifest"].get("basili") if isinstance(s["manifest"], dict) else None
        if man_b is not None:
            kapi.iddia("KART_N_BEYAN/" + yol, man_b == len(s["kartlar"]),
                       "manifest basili=%r != sayfadaki SSR kart %d"
                       % (man_b, len(s["kartlar"])))

    # ------------------------------------------------------------------ istemci (node) ekseni
    kategoriler = mm.kategori_evreni(index_html)
    js = mm.kapsam_scripti(kategoriler)
    js = js[js.index(mm._KAPSAM_JS_BAS):js.index(mm._KAPSAM_JS_SON)]
    KAT = kategoriler[0]
    OLCULEMEDI = "Kapsam: yalnız %s kategorisi — parça sayısı ölçülemedi" % KAT
    sentetik = [
        # kırılım YOK -> sayı BASILMAZ (fail-open olsaydı 0/kart sayısı basardı)
        {"ad": "eksik", "kategori": KAT, "kartlar": [KAT, KAT], "butonlar": [],
         "toplamKatsay": None, "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım YOK + görünen kart 0 ama kovada 5 parça VAR: "0 parça" basmak tam da
        # bildirilen sessiz kusurdur. Tutarlılık kapısı (toplam < kart) burada devreye
        # GİREMEZ (kart 0) -> fail-open'a dönen bir düzeltme YALNIZ bu fikstürde yakalanır
        # ([[duzeltme-fail-open-cevirebilir]]).
        {"ad": "eksik_kovali", "kategori": KAT, "kartlar": ["Ofis"],
         "butonlar": [{"href": "/marka/x/y/", "katsay": '{"%s":5}' % KAT}],
         "toplamKatsay": None, "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım BOZUK JSON
        {"ad": "bozuk", "kategori": KAT, "kartlar": [KAT], "butonlar": [],
         "toplamKatsay": "{bozuk", "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım BOŞ metin
        {"ad": "bos", "kategori": KAT, "kartlar": [KAT], "butonlar": [],
         "toplamKatsay": "", "serit": OLCULEMEDI, "rozet": "—"},
        # kırılım TUTARSIZ (toplam < görünen kart) -> bayat/bozuk veri, sayı BASILMAZ
        {"ad": "tutarsiz", "kategori": KAT, "kartlar": [KAT, KAT, KAT], "butonlar": [],
         "toplamKatsay": '{"%s":1}' % KAT, "serit": OLCULEMEDI, "rozet": "—"},
        # SAĞLAM kontrol: kova + kart, kapsam içindeki sayı basılır (hep-null mutantını öldürür)
        {"ad": "saglam", "kategori": KAT, "kartlar": [KAT, KAT, "Ofis"],
         "butonlar": [{"href": "/marka/x/y/", "katsay": '{"%s":5}' % KAT}],
         "toplamKatsay": '{"%s":7,"Ofis":1}' % KAT,
         "serit": "Kapsam: yalnız %s kategorisi — 7 parça" % KAT, "rozet": "7"},
        # BÖLÜM ROZETİ, SAĞLAM: başlık kapsam içindeki sayıya DÜŞER (13 -> 9). Gerçek
        # sayfalarda rozet HEP sağlamdır, bu yüzden aşağıdaki bozuk dallar yalnız sentetik
        # fikstürle zorlanabilir (fail-open mutantı aksi hâlde hayatta kalırdı).
        {"ad": "bolum_saglam", "kategori": KAT, "kartlar": [KAT], "butonlar": [],
         "toplamKatsay": '{"%s":9}' % KAT,
         "bolumler": [{"bolum": "erisim", "katsay": '{"%s":9,"Ofis":4}' % KAT, "n": 13}],
         "serit": "Kapsam: yalnız %s kategorisi — 9 parça" % KAT, "rozet": "9",
         "bolum": ["9"]},
        # BÖLÜM ROZETİ, BOZUK/BOŞ kırılım: sayı BASILMAZ ("—"). Fail-open'a çeviren bir
        # düzeltme burada 0 ya da DOM sayısı basar ([[duzeltme-fail-open-cevirebilir]]).
        {"ad": "bolum_bozuk", "kategori": KAT, "kartlar": [KAT], "butonlar": [],
         "toplamKatsay": '{"%s":9}' % KAT,
         "bolumler": [{"bolum": "erisim", "katsay": "{bozuk", "n": 13},
                      {"bolum": "alt", "katsay": "", "n": 2}],
         "serit": "Kapsam: yalnız %s kategorisi — 9 parça" % KAT, "rozet": "9",
         "bolum": ["—", "—"]},
    ]
    for _f in sentetik:
        _f.setdefault("bolumler", [])
        _f.setdefault("bolum", [])
    # ---- ARTIM EKSENİ GİRDİSİ: her marka sayfasının yükündeki HER kalem için, istemcinin
    # çizeceği kart ile Python `_kart`ın çıktısını KARŞILAŞTIRILABİLİR hâle getir.
    # ÖRNEKLEME YOK: bütün kalemler ölçülür (kimlik gibi, kart gövdesi de 93/93 sayfada).
    artim_js = getattr(mm, "_ARTIM_JS_GOVDE", None)
    urun_ix = {p.get("id"): p for p in products if p.get("id")}
    kart_denekleri, py_kartlar, gorulen_denek = [], {}, set()
    for yol, s in marka_sayfalari.items():
        yuk = s["yuk"]
        if not isinstance(yuk, dict) or not isinstance(yuk.get("k"), list):
            continue
        for kalem in yuk["k"]:
            pid = kalem[0] if kalem else None
            p = urun_ix.get(pid)
            if p is None:
                continue
            mm_attr = (' data-mm="%s"' % " ".join(str(x) for x in (kalem[2] or []))
                       ) if (kalem[2] or []) else ""
            anahtar = pid + "|" + mm_attr
            if anahtar in gorulen_denek:
                continue
            gorulen_denek.add(anahtar)
            kart_denekleri.append({
                "id": anahtar, "kalem": kalem,
                "o": (yuk.get("o") or {}).get(pid),
                # 🔴 EDGE ŞEKLİ (kartHtml canlıda BU şekli okur): `/katalog?ids=` tekil
                # `gorsel` alanı döner, `gorseller` dizisi YOKTUR (canlı ölçüldü: 100/100
                # ürün, 0 sapan alan). Deneği yerel `gorseller` diziyle beslemek ekseni
                # sahte yeşile çevirirdi — kart kapağı canlıda boş kalır, kapı görmezdi.
                "urun": {"id": p.get("id"), "kategori": p.get("kategori"),
                         "baslik": p.get("baslik"),
                         "gorsel": (mm_ctx["images_of"](p) or [""])[0],
                         "fiyat": p.get("fiyat"), "parametrik": p.get("parametrik")},
            })
            py_kartlar[anahtar] = mm._kart(mm_ctx, p, mm_attr)
    # suz() ekseni: gerçek bir sayfanın yükü üzerinde model + kapsam süzgeci
    suz_yol = max(marka_sayfalari, key=lambda y: len(marka_sayfalari[y]["butonlar"]))
    suz_yuk = marka_sayfalari[suz_yol]["yuk"]
    suz_kategori = (suz_yuk.get("kat") or [None])[0] if isinstance(suz_yuk, dict) else None

    ornek_manifest = marka_sayfalari[suz_yol]["manifest"]
    if not isinstance(ornek_manifest, dict):
        ornek_manifest = {"uc": kanon_uc or "", "yol": KANON_YOL, "parti": 100,
                          "yuk": "/x/parcalar.json", "site": mm_ctx["SITE"],
                          "toplam": 0, "basili": 0}
    veri = {"kapsamJs": js, "kategoriler": kategoriler, "sentetik": sentetik, "sayfalar": {},
            "artimJs": artim_js, "site": mm_ctx["SITE"], "kartDenekleri": kart_denekleri,
            "suzYuk": suz_yuk if isinstance(suz_yuk, dict) else None,
            "suzKategori": suz_kategori,
            "manifestOrnek": ornek_manifest,
            "manifestMetni": json.dumps(ornek_manifest, ensure_ascii=False),
            # uc/yol/parti YOK -> modül bu manifesti REDDETMELİ (fail-closed)
            "manifestEksik": json.dumps({"yuk": "/x/parcalar.json",
                                         "site": mm_ctx["SITE"]}, ensure_ascii=False),
            "partiDenek": ["id-%d" % i for i in range(250)]}
    for yol, s in sayfalar.items():
        veri["sayfalar"][yol] = {
            "kartlar": [k for k, _i in s["kartlar"]],
            "butonlar": [{"href": h, "katsay": json.dumps(t, ensure_ascii=False,
                                                         separators=(",", ":"), sort_keys=True)}
                         for h, t in s["butonlar"]],
            "baglar": [k for k, _i in s["baglar"]],
            "toplamKatsay": s["toplam_katsay_ham"],
            "bolumler": [{"bolum": b["bolum"], "katsay": b["katsay_ham"], "n": b["n"]}
                         for b in s["bolumler"]],
            "olcumKategorileri": sorted(k for k in erisim[yol] if k),
        }
    girdi = os.path.join(tmp, "js-girdi.json")
    with open(girdi, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False)
    harness = os.path.join(tmp, "harness.js")
    with open(harness, "w", encoding="utf-8") as f:
        f.write(_JS_HARNESS)
    try:
        cp = subprocess.run(["node", harness, girdi], capture_output=True, text=True,
                            timeout=600)
    except Exception as e:                                   # noqa: BLE001
        print("OLCULEMEDI: node koşturulamadı: %r" % (e,))
        return 3, kapi, {}
    if cp.returncode != 0 or not cp.stdout.strip():
        print("OLCULEMEDI: node rc=%d %s" % (cp.returncode, cp.stderr[-400:]))
        return 3, kapi, {}
    js_sonuc = json.loads(cp.stdout)
    if "hata" in js_sonuc:
        print("OLCULEMEDI: %s" % js_sonuc["hata"])
        return 3, kapi, {}

    # ------------------------------------------------- ARTIM: kart gövdesi TEK KAYNAK mı
    artim = js_sonuc.get("artim") or {}
    kapi.iddia("ARTIM/kuruldu", bool(artim.get("kuruldu")),
               "PRUVO_ARTIM node'da kurulmadı (artımlı kart çizimi ölçülemez)")
    js_kartlar = artim.get("kartlar") or {}
    sapan_kart = [k for k, v in py_kartlar.items() if js_kartlar.get(k) != v]
    kapi.iddia("ARTIM/kart_bayt_ayni", not sapan_kart,
               "%d/%d kalemde istemci kartı Python `_kart` ile AYRIŞTI (ilk: %s | js=%r | py=%r)"
               % (len(sapan_kart), len(py_kartlar), (sapan_kart or ["-"])[0],
                  (js_kartlar.get(sapan_kart[0]) if sapan_kart else "")[:150],
                  (py_kartlar.get(sapan_kart[0]) if sapan_kart else "")[:150]))
    kapi.iddia("ARTIM/kart_denek_dolu", len(py_kartlar) > 1000,
               "kart eşitliği DEJENERE ölçüldü (denek=%d): boş ölçüm yeşil sayılmaz"
               % (len(py_kartlar),))
    # suz(): sayfa-içi filtrenin çekirdeği. Model süzgeci DARALTMALI, kategori süzgeci
    # DARALTMALI, tanınmayan yük BOŞ küme (fail-closed) vermeli.
    sz = artim.get("suz") or {}
    bek_hepsi = [k[0] for k in (suz_yuk.get("k") or [])] if isinstance(suz_yuk, dict) else []
    bek_model0 = [k[0] for k in (suz_yuk.get("k") or []) if 0 in (k[2] or [])] \
        if isinstance(suz_yuk, dict) else []
    bek_kat = [k[0] for k in (suz_yuk.get("k") or [])
               if (suz_yuk.get("kat") or [])[k[1]] == suz_kategori] \
        if isinstance(suz_yuk, dict) else []
    kapi.iddia("ARTIM_SUZ/hepsi", sz.get("hepsi") == bek_hepsi,
               "süzgeçsiz küme %s != kanonik %d" % (len(sz.get("hepsi") or []), len(bek_hepsi)))
    kapi.iddia("ARTIM_SUZ/model", sz.get("model0") == bek_model0 and 0 < len(bek_model0),
               "model süzgeci %s != kanonik %d" % (len(sz.get("model0") or []), len(bek_model0)))
    kapi.iddia("ARTIM_SUZ/kategori", sz.get("kategori") == bek_kat and 0 < len(bek_kat),
               "kategori süzgeci %s != kanonik %d" % (len(sz.get("kategori") or []), len(bek_kat)))
    kapi.iddia("ARTIM_SUZ/fail_closed", sz.get("bozuk") == 0,
               "tanınmayan yükte kart basıldı (fail-open): %r" % (sz.get("bozuk"),))
    kapi.iddia("ARTIM_SUZ/daraltiyor", len(bek_model0) < len(bek_hepsi),
               "KONTROL: model süzgeci dejenere (daraltmıyor) — %d == %d"
               % (len(bek_model0), len(bek_hepsi)))

    # ---- TESLİM YOLU: modülün KURDUĞU adres kanonikle aynı mı (X3 mutantının kimliği)
    ist = artim.get("istek") or {}
    bek_adres = (kanon_uc or "") + KANON_YOL + "a-1%2Cb-2"
    kapi.iddia("ARTIM_ADRES/kanonik", ist.get("adres") == bek_adres,
               "modülün kurduğu istek adresi %r != kanonik %r" % (ist.get("adres"), bek_adres))
    kapi.iddia("ARTIM_ADRES/partileme", ist.get("parti_n") == 3 and ist.get("parti_ilk") == 100,
               "250 id, 100'lük parti -> 3 istek beklenir; ölçülen parti=%r ilk=%r "
               "(tek istekte 100'den fazla id edge ucunu aşar)"
               % (ist.get("parti_n"), ist.get("parti_ilk")))
    kapi.iddia("ARTIM_ADRES/manifest_kabul", ist.get("manifest_kabul") is True,
               "geçerli manifest reddedildi -> artım kolu hiç kurulmaz")
    kapi.iddia("ARTIM_ADRES/manifest_fail_closed", ist.get("manifest_red") is True,
               "uc/yol/parti EKSİK manifest KABUL edildi (fail-open): sayfa ölü uca istek atar")

    for f in sentetik:
        r = (js_sonuc.get("sentetik") or {}).get(f["ad"]) or {}
        kapi.iddia("JS_SENTETIK/%s/serit" % f["ad"], r.get("serit") == f["serit"],
                   "şerit %r != %r" % (r.get("serit"), f["serit"]))
        kapi.iddia("JS_SENTETIK/%s/rozet" % f["ad"], r.get("rozet") == f["rozet"],
                   "rozet %r != %r" % (r.get("rozet"), f["rozet"]))
        kapi.iddia("JS_SENTETIK/%s/bolum" % f["ad"], r.get("bolum") == f["bolum"],
                   "bölüm rozetleri %r != %r" % (r.get("bolum"), f["bolum"]))

    for yol, s in sayfalar.items():
        r = js_sonuc.get(yol)
        if r is None:
            kapi.iddia("JS_FILTRESIZ/" + yol, False, "node çıktısı yok")
            continue
        kapi.iddia("JS_FILTRESIZ/" + yol, r["filtresiz"] == s["toplam"],
                   "js %s, SSR %s" % (r["filtresiz"], s["toplam"]))
        for kat, olcum in r["kategoriler"].items():
            bek = len(erisim[yol].get(kat, ()))
            kapi.iddia("JS_SERIT/%s/%s" % (yol, kat),
                       olcum["serit"] == ("Kapsam: yalnız %s kategorisi — %d parça" % (kat, bek)),
                       "şerit %r, beklenen %d parça" % (olcum["serit"], bek))
            kapi.iddia("JS_ROZET/%s/%s" % (yol, kat), olcum["rozet"] == str(bek),
                       "rozet %r != %d" % (olcum["rozet"], bek))
            kapi.iddia("JS_ALTKUME/%s/%s" % (yol, kat), olcum["gorunenKart"] <= bek,
                       "görünen kart %d > toplam %d" % (olcum["gorunenKart"], bek))
            # DÜZ BAĞ ÖĞELERİ de kapsamda süzülür: o kategoride OLAN bağ girdisi görünür
            # kalır, olmayan GİZLENİR (kaçak yok). Bağı olmayan sayfada iki sayı da 0.
            bag_kat = [k for k, _i in s["baglar"] if k == kat]
            kapi.iddia("JS_DUZ/%s/%s" % (yol, kat),
                       olcum.get("gorunenDuz") == len(bag_kat)
                       and olcum.get("gizlenenDuz") == len(s["baglar"]) - len(bag_kat),
                       "görünen bağ %r (beklenen %d), gizlenen %r (beklenen %d)"
                       % (olcum.get("gorunenDuz"), len(bag_kat), olcum.get("gizlenenDuz"),
                          len(s["baglar"]) - len(bag_kat)))
            # 🔴 İNVARYANTIN İSTEMCİ UCU — kusur TAM BURADAYDI: başlık GÖRÜNEN DOM
            # düğümünü yazıyordu ve artımlı çizilecek kalemler henüz DOM'da olmadığı için
            # kapsam kolunda beyan 575 iken başlık 304 basıyordu. Artık kapsam altında da
            # BEYAN == ERİŞİLEBİLİR olmak zorunda; her sayfa × her kapsam kolu ölçülür.
            bo = olcum.get("bolum") or []
            eris_m = [b["metin"] for b in bo if b["bolum"] == "erisim"]
            kapi.iddia("INVARYANT_KAPSAM/%s/%s" % (yol, kat),
                       all(m == str(bek) for m in eris_m),
                       "kapsam başlığı %r != erişilebilir %d" % (eris_m, bek))
            parca_m = [b["metin"] for b in bo if b["bolum"] == "parca"]
            if parca_m:
                kapi.iddia("INVARYANT_KAPSAM_PARCA/%s/%s" % (yol, kat),
                           all(m.isdigit() for m in parca_m)
                           and sum(int(m) for m in parca_m if m.isdigit()) == bek,
                           "bölüm başlıkları toplamı %r != erişilebilir %d" % (parca_m, bek))
            alt_m = [b["metin"] for b in bo if b["bolum"] == "alt"]
            kapi.iddia("INVARYANT_KAPSAM_ALT/%s/%s" % (yol, kat),
                       all(m.isdigit() and int(m) == olcum.get("gorunenDuz") for m in alt_m),
                       "düz bağ başlığı %r != görünen bağ %r"
                       % (alt_m, olcum.get("gorunenDuz")))

    # KONTROL: JS_DUZ ekseni DEJENERE olmasın. Hiçbir sayfada bağ öğesi gizlenmiyorsa
    # "0 == 0" karşılaştırması her mutantı yeşil geçirir ([[fikstur-degeri-mutasyonu-korlestirir]]).
    duz_gizlenen = sum((olcum.get("gizlenenDuz") or 0)
                       for yol in sayfalar
                       for olcum in ((js_sonuc.get(yol) or {}).get("kategoriler") or {}).values())
    duz_toplam = sum(len(s["baglar"]) for s in sayfalar.values())
    kapi.iddia("JS_DUZ_KONTROL/dejenere_degil", duz_gizlenen > 0 and duz_toplam > 0,
               "bağ öğesi hiç süzülmedi (gizlenen=%d, toplam bağ=%d): eksen ölçmüyor"
               % (duz_gizlenen, duz_toplam))

    bilgi = {"mukerrer": mukerrer_toplam, "marka": len(marka_sayfalari),
             "model": len(model_sayfalari), "bag": duz_toplam, "tmp": tmp}

    # ═══════════════════════════════════ ÖZET ↔ HÜKÜM TEK KAYNAK (12 Ağu 2026)
    # 🔴 BU KAPININ KENDİ İÇİNDE, ONARDIĞI SINIFIN AYNISI VARDI (bağımsız çürütücü ölçtü):
    # merge-base jeneratörüyle kapı `DUSEN=2292 HUKUM=KIRMIZI` derken `--dokum` özeti
    # "sapan marka 0" basıyordu. Hüküm `kapi.dusen`den, özet ise AYRI bir karşılaştırmadan
    # (üretilen toplam != gerçek toplam + katalog ayrışması) doğuyordu — yani kabul kümesi
    # ile özet kümesi İKİ AYRI SAYIM NOKTASINDAN geliyordu ve sessizce ayrıştılar. Marka
    # sayfasında beyanın `toplam`dan, başlığın `basili`den doğması NE İSE bu O'dur.
    # Artık özet HÜKMÜ BESLEYEN kümeden türer (`kapi.sapan_sayfalar`); ikinci sayım yok.
    kapi.sayfalar = frozenset(sayfalar)
    cozulmeyen = sorted({d.split(" — ")[0].split("/")[0] for d in kapi.dusen
                         if kapi.sayfa_coz(d) is None} - KURESEL_AILELER)
    kapi.iddia("OZET_KANONIK/aile_bilinen", not cozulmeyen,
               "düşen iddia ne bir SAYFAYA çözülüyor ne de KURESEL_AILELER'de beyan "
               "edilmiş: %s — özet bu aileyi SESSİZCE saymaz (hüküm KIRMIZI iken insan "
               "'sapan 0' okur)" % (cozulmeyen,))
    sapan_sayfalar = kapi.sapan_sayfalar
    sapan_marka = {y for y in sapan_sayfalar if y.count("/") == 1}
    # KONTROL: kapı kırmızıysa özet SUSAMAZ. Sayfaya bağlı bir eksen düştüğü hâlde özet
    # sıfır sapan gösteriyorsa iki uç ayrışmış demektir (fail-closed).
    sayfali_dusen = [d for d in kapi.dusen if kapi.sayfa_coz(d)]
    kapi.iddia("OZET_KANONIK/ozet_susmuyor", bool(sapan_sayfalar) == bool(sayfali_dusen),
               "sayfaya bağlı düşen iddia %d ama özetteki sapan sayfa %d — özet hükümden "
               "KOPMUŞ" % (len(sayfali_dusen), len(sapan_sayfalar)))
    # AİLE KIRILIMI — hangi eksen kaç MARKA sayfasını sapan yaptı (aynı kanonik kümeden).
    aile_marka = {}
    for d in kapi.dusen:
        y = kapi.sayfa_coz(d)
        if y and y.count("/") == 1:
            aile_marka.setdefault(d.split(" — ")[0].split("/")[0], set()).add(y)
    bilgi["aile_marka"] = {a: len(v) for a, v in sorted(aile_marka.items())}
    bilgi["sapan_marka"] = len(sapan_marka)
    bilgi["sapan_sayfa"] = len(sapan_sayfalar)

    # ---------------------------------------------------------------- BÜYÜKLÜK KATMANLARI
    # 🔴 TOPLAM TEKİL SAPMAYI GİZLER: onarım yalnız çok-ürünlü markalarda çalışıyorsa
    # "0 sapan" toplamı bunu ÖRTER. Katman katman ayrı basılır; sapanlar marka bazında.
    def katman(n):
        if n > 500:
            return "cok(>500)"
        if n >= 50:
            return "orta(50-500)"
        if n > 1:
            return "az(2-49)"
        return "tekil(1)"

    katmanlar = {}
    for yol, s in sayfalar.items():
        seviye = "marka" if yol.count("/") == 1 else "model"
        kt = katman(len(tumu(erisim[yol])))
        d0 = katmanlar.setdefault((seviye, kt), {"sayfa": 0, "sapan": [], "mukerrer": 0})
        d0["sayfa"] += 1
        d0["mukerrer"] += len(s["kartlar"]) - len(set(i for _k, i in s["kartlar"]))
        # 🔴 SAPAN, HÜKMÜ BESLEYEN KÜMEDEN OKUNUR — burada YENİDEN HESAPLANMAZ.
        # (Eski kod `s["toplam"] != gercek` ile ayrı bir kıyas kuruyordu: beyan cümlesi
        # doğruyken BAŞLIK yalan söyleyen 35 markayı GÖRMÜYORDU.)
        if yol in sapan_sayfalar:
            aileler = sorted({d.split(" — ")[0].split("/")[0] for d in kapi.dusen
                              if kapi.sayfa_coz(d) == yol})
            d0["sapan"].append("%s (%s)" % (yol, ",".join(aileler)))
    bilgi["katmanlar"] = katmanlar

    # 🔴 ÖZETİN KAYNAĞI ÖLÇÜLÜR (beyan değil): insana BASILAN tablonun sapan kümesi,
    # hükmü besleyen kümenin AYNISI olmak zorunda. Özeti hükümden koparan her değişiklik
    # burada KIRMIZI yakar — mutasyon bataryası bu ekseni ayrı bir mutantla sınar.
    basilan_sapan = {satir.split(" ")[0] for d0 in katmanlar.values()
                     for satir in d0["sapan"]}
    kapi.iddia("OZET_KANONIK/ozet_kaynagi", basilan_sapan == sapan_sayfalar,
               "insana basılan özetin sapan kümesi (%d) hükmü besleyen kümeden (%d) "
               "AYRIŞTI — yalnız özette olan %s, yalnız hükümde olan %s"
               % (len(basilan_sapan), len(sapan_sayfalar),
                  sorted(basilan_sapan - sapan_sayfalar)[:3],
                  sorted(sapan_sayfalar - basilan_sapan)[:3]))

    if dokum:
        print("== BÜYÜKLÜK KATMANLARI (üretilen == gerçek) ==")
        for anahtar in sorted(katmanlar):
            d0 = katmanlar[anahtar]
            print("  %-6s %-13s sayfa=%4d  sapan=%d  mukerrer_kart=%d%s"
                  % (anahtar[0], anahtar[1], d0["sayfa"], len(d0["sapan"]), d0["mukerrer"],
                     ("  -> " + ", ".join(d0["sapan"][:10])) if d0["sapan"] else ""))
    if sayfa_detay:
        s = sayfalar.get(sayfa_detay)
        if s is None:
            print("DETAY: %s bulunamadı" % sayfa_detay)
        else:
            print("DETAY %s: SSR_toplam=%s kart=%d tekil_kart=%d kirilim=%s"
                  % (sayfa_detay, s["toplam"], len(s["kartlar"]),
                     len(set(i for _k, i in s["kartlar"])),
                     json.dumps(s["toplam_katsay"], ensure_ascii=False, sort_keys=True)))
    shutil.rmtree(tmp, ignore_errors=True)
    return (0 if not kapi.dusen else 1), kapi, bilgi


def main():
    if "--iz" in sys.argv[1:]:
        print("IZ=" + kaynak_izi())
        return 0
    argv = sys.argv[1:]
    detay = argv[argv.index("--sayfa") + 1] if "--sayfa" in argv else None
    rc, kapi, bilgi = olc(dokum="--dokum" in argv, sayfa_detay=detay)
    for d in kapi.dusen[:40]:
        print("  DUSEN  " + d)
    if len(kapi.dusen) > 40:
        print("  ... (+%d düşen daha)" % (len(kapi.dusen) - 40))
    # AİLE İMZASI: mutasyon bataryası mutantları BUNUNLA ayırt eder (çıkış kodu DEĞİL —
    # iki farklı kusur da rc=1 verir; ayrışmayan imza "aynı iddiayı düşürdüler" demektir).
    aile = {}
    for d in kapi.dusen:
        aile[d.split("/")[0]] = aile.get(d.split("/")[0], 0) + 1
    print("AILELER=" + (",".join("%s:%d" % kv for kv in sorted(aile.items())) or "-"))
    print("IZ=" + kaynak_izi())
    print("IDDIA=%d/%d  DUSEN=%d  MUKERRER_KART=%s  SAYFA=marka %s + model %s"
          % (kapi.gecen, kapi.taban, len(kapi.dusen), bilgi.get("mukerrer"),
             bilgi.get("marka"), bilgi.get("model")))
    # 🔴 ÖZET SAYI HÜKÜMLE AYNI KÜMEDEN — `--dokum` beklemeden GÖRÜNÜR. (Bu satır
    # olmadığı için "DUSEN=2292 KIRMIZI" ile "sapan marka 0" aynı koşumda basılabiliyordu.)
    print("SAPAN_MARKA=%s  SAPAN_SAYFA=%s"
          % (bilgi.get("sapan_marka"), bilgi.get("sapan_sayfa")))
    print("AILE_SAPAN_MARKA=" + (",".join("%s:%d" % kv for kv in
                                          sorted((bilgi.get("aile_marka") or {}).items()))
                                 or "-"))
    print("HUKUM=" + ("YESIL" if rc == 0 else ("KIRMIZI" if rc == 1 else "OLCULEMEDI")))
    return rc


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIZIKSEL CANLI KAPISI — hazir ticari malda "canli worker NE TAHSIL EDER" olcumu.

NEDEN VAR (olculmus korluk, 1 Agu):
  Canli shop worker paketi BAYAT kaldi (30 Tem 20:30 – 1 Agu 01:58 penceresi). Bedeli PARA:
  `tur == "fiziksel"` olan 676 hazir ticari malda malzeme/renk carpani HALA uygulaniyordu.
  Bayat bir localStorage sepet satiri (ASA + "Diger") liste fiyatinin 1,840 katini tahsil
  ediyordu — 16.400 TL'lik bir termostat muhafazasi icin canli uc 30.176,00 TL dondu.
  UI o satiri artik URETEMEZ ama sepet localStorage'da YASAR; istemcide secici gizlemek
  bu yolu KAPATMAZ.

  🔴 ASIL KUSUR KORLUKTU: o an `tools/konfigur-canli-kapisi.py` rc=0 ve
  `tools/canli-saglik-kapisi.py` rc=0 idi. Sebep: canli-saglik K4 (KART) ekseni
  konfigur-canli-kapisi'ye DEVREDIYOR, o da yalnizca KONFIGURLU (17) urunu olcuyor.
  `tur`/fiziksel fiyat yolu icin CANLI HICBIR EKSEN YOKTU. Ayni sinif korluk 30 Tem'de de
  yasandi (worker deploy edilmemis, kart kanali 2 gun kapali) ve AYNI BICIMDE tekrar etti.

CEKIRDEK IDDIA (bu evde verilmis isletme karari, secenekler.js TUR_FIZIKSEL blogu):
  fiziksel uruntte malzeme/renk SECIMI KARSILIKSIZDIR -> HER secim kombinasyonu LISTE
  FIYATIDIR. Baski (ozel uretim) uruntte carpan MESRUDUR ve uygulanmalidir.

OLCULEN DORT IDDIA (her prova ayri ayri):
  A  CANLI LISTE     fiziksel uruntte canli birim_kurus == liste kurusu (her kombinasyonda).
                     Ihlali = MUSTERIDEN FAZLA/EKSIK TAHSILAT. Bu iddia depodaki koddan
                     TURETILMEZ; dogrudan isletme kuralidir.
  B  DEPO LISTE      AYNI iddia YEREL KAHIN'de (depo HEAD'inin KENDI worker kodu, offline
                     kosturulur). A kirmizi + B yesil -> CANLI PAKET BAYAT (deploy gerekir).
                     A kirmizi + B kirmizi -> kural DEPODA da kirik (once kod duzelir).
                     Teshisi ayiran eksen budur.
  C  NESIL           canli birim_kurus == yerel kahin birim_kurus (fiziksel VE baski, TUM
                     provalarda). "Canli paket depodaki kaynakla ayni nesli tasiyor mu"
                     sorusunun UCUZ sinyali: deploy EDILMEMIS worker'i, fiziksel kurala
                     bagli olmadan da yakalar (yarin baska bir fiyat kolu degisirse de calisir).
  D  AYIRT EDICI GUC baski (ozel uretim) KONTROL TABANI: en pahali kombinasyonda canli birim
                     liste fiyatindan BUYUK olmali (carpan uygulanmali), taban kombinasyonda
                     (PLA+Siyah) liste fiyatina ESIT olmali. Bu iddia iki isi birden yapar:
                     (1) yanlis-pozitif butcesi — baski urunlerinde carpan MESRUDUR, nobetci
                     onlari YAKMAZ; (2) provanin KENDI ayirt edici gucunu kanitlar — carpan
                     her yerde kalksa "A yesil" ANLAMSIZ olurdu, bu iddia o hali KIRMIZI yakar.

YAN ETKI YOK: POST /api/shop/fiyat PROVA ucudur — siparis ACMAZ, D1'e YAZMAZ, iyzico'ya
  GITMEZ, Telegram/e-posta GONDERMEZ, olcum olayi GONDERMEZ. Yapisal kanit CI'da:
  shop/test/fiyat-prova.mjs D1 run() ve global fetch sayaclarini SAYAR (prova cagrisinda 0).
  Bu kapi yalnizca POST atar; hicbir sey yazmaz, hicbir sir okumaz, DEPLOY ETMEZ.

IKI KOL — HANGISI NEREDE KOSAR:
  * OFFLINE KOL (`--kendini-test`): ag YOK. Saf karar mantigi + HTTP kod eslemesi (sahte
    urlopen) + KIRMIZI-MUTASYON + gercek katalogla yanlis-pozitif nobeti + YEREL KAHIN'in
    fiilen kosmasi. CI'da (deploy.yml) BLOKLAYICI kosan kol BUDUR. node ISTER (setup-node
    bloklayici on-kosul); node yoksa KIRMIZI verir, sessiz yesil YOK.
  * CANLI KOL (bayraksiz kosum): ag ISTER. CI'da BILEREK kosmaz — canli sonuc olcumu bir
    DEPLOY KAPISI degil IZLEME isidir; tek gecici DNS hatasi tum ekibin yayinini durdururdu
    ([[kapi-kapsam-eksen-secimi]]). Sahibi tools/canli-saglik-kapisi.py K6 eksenidir:
    o arac bu dosyayi bulup CAGIRIR, bulamazsa ARAC-YOK -> ARIZA -> OLCULEMEDI.

CIKIS KODLARI (ucu de ANLAMLI — "olculemedi" ASLA yesil sayilmaz):
  0 PARITE      — dort iddia da tuttu.
  1 DRIFT       — en az bir iddia ihlal edildi (fazla/eksik tahsilat, bayat paket, taninmayan
                  urun ya da ayirt edici gucun kaybi).
  2 OLCULEMEDI  — ag/uc/node erisilemedi, 429, bozuk cevap ya da OLCULECEK FIZIKSEL URUN YOK.
                  Drift KANITI yok, ama parite de KANITLANMADI -> sessiz yesil VERILMEZ.

KULLANIM:
    python3 tools/fiziksel-canli-kapisi.py                  # CANLI kol (ag ISTER)
    python3 tools/fiziksel-canli-kapisi.py --uc https://.../api/shop/fiyat
    python3 tools/fiziksel-canli-kapisi.py --adet 5         # kac fiziksel urun ornekleniyor
    python3 tools/fiziksel-canli-kapisi.py --kendini-test   # OFFLINE kol (CI'da bu kosar)
"""
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
URUNLER_VARSAYILAN = os.path.join(ROOT, "urunler.json")
UC_VARSAYILAN = "https://pruvo3d.com/api/shop/fiyat"

# 🔴 TEK DIZE — secenekler.js TUR_FIZIKSEL / tools/arama.py _TUR_FIZIKSEL / build.py ile AYNI
# fail-closed kural: YALNIZ tam "fiziksel" dizesi hazir ticari mal demektir (kirpma/kucultme
# YOK). Bu sabit yalnizca ORNEKLEM SECIMINDE kullanilir; fiyat kurali burada TEKRARLANMAZ
# (liste kurusu secenekler.js fiyatSayisi'ndan, hesap depo worker'indan gelir).
TUR_FIZIKSEL = "fiziksel"

# Kontrol tabani, olculen fiziksel urunlerle AYNI kategoriden secilir: boylece kontrol ile
# denek arasindaki TEK fark `tur` alani olur (kategori/fonksiyonellik degisken degildir).
KONTROL_KATEGORI = "Marin"

# Prova kombinasyonlari. "Diger" renk `renk_ozel` ISTER (worker aksi halde 400 verir).
# ASA+Diger = EN PAHALI kombinasyon (1,60 x 1,15 = 1,840) — 1 Agu'da canlida olculen sapma
# tam olarak budur. PETG+Beyaz iki carpani AYIRIR (malzeme VAR, renk YOK).
KOMBINASYONLAR = [
    ("PLA", "Siyah", "", "taban"),
    ("PETG", "Beyaz", "", "malzeme"),
    ("ASA", "Diğer", "turuncu", "en-pahali"),
]
# Kontrol tabaninda iki uc yeter: carpansiz taban + en pahali (ayirt edici guc).
KONTROL_KOMBINASYONLARI = [KOMBINASYONLAR[0], KOMBINASYONLAR[2]]

ADET_VARSAYILAN = 3          # ornekleme alinan fiziksel urun sayisi
GECIKME_VARSAYILAN = 0.35    # FIYAT_RATE_LIMIT 60/60 sn

# R2/edge urllib UA 403 dersi ([[r2-urllib-ua-403-tuzagi]]): ciplak python-urllib UA'si edge
# tarafindan bot sayilip 403 yiyebilir -> tarayici UA'si kullanilir.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# ---------------------------------------------------------------- orneklem
def _anahtar(pid, malzeme, renk):
    return "%s|%s|%s" % (pid, malzeme, renk)


def orneklem_sec(urunler, adet=ADET_VARSAYILAN):
    """(problar, urun_kayitlari) — DETERMINISTIK secim (rastgelelik YOK: ayni katalog ayni
    provayi verir, kosumlar karsilastirilabilir).

    Fiziksel urunler id'ye gore siralanip esit araliklarla `adet` tanesi alinir (bas/orta/son
    -> katalogun farkli partileri ornege girer). Kontrol tabani AYNI kategoriden, `tur`SUZ,
    parametrik/konfigur OLMAYAN, fiyati DOLU bir baski urunudur.

    🔴 FIYAT BURADA AYRISTIRILMAZ: "16.400 TL" -> 1640000 cevrimi secenekler.js
    fiyatSayisi'nindir (yerel kahin doner). Burada ikinci bir ayristirici YOKTUR
    ([[ikiz-tanim-sessiz-ayrisma]])."""
    fiz = sorted([u for u in urunler
                  if u.get("tur") == TUR_FIZIKSEL and u.get("fiyat")
                  and not u.get("parametrik") and not u.get("konfigur")],
                 key=lambda u: u["id"])
    secili = []
    if fiz and adet > 0:
        n = min(adet, len(fiz))
        for i in range(n):
            secili.append(fiz[(i * (len(fiz) - 1)) // max(1, n - 1) if n > 1 else 0])
    # Mukerrer secimi ele (kucuk katalogda araliklar cakisabilir), sirayi koru.
    gorulen, denekler = set(), []
    for u in secili:
        if u["id"] not in gorulen:
            gorulen.add(u["id"])
            denekler.append(u)

    kontroller = [u for u in sorted(urunler, key=lambda x: x.get("id") or "")
                  if u.get("kategori") == KONTROL_KATEGORI and not u.get("tur")
                  and not u.get("parametrik") and not u.get("konfigur") and u.get("fiyat")]
    kontrol = kontroller[len(kontroller) // 2] if kontroller else None

    problar = []
    for u in denekler:
        for malzeme, renk, ozel, etiket in KOMBINASYONLAR:
            problar.append({"id": u["id"], "sinif": "FIZIKSEL", "malzeme": malzeme,
                            "renk": renk, "renk_ozel": ozel, "kombinasyon": etiket,
                            "anahtar": _anahtar(u["id"], malzeme, renk)})
    if kontrol is not None:
        for malzeme, renk, ozel, etiket in KONTROL_KOMBINASYONLARI:
            problar.append({"id": kontrol["id"], "sinif": "BASKI", "malzeme": malzeme,
                            "renk": renk, "renk_ozel": ozel, "kombinasyon": etiket,
                            "anahtar": _anahtar(kontrol["id"], malzeme, renk)})
    kayitlar = denekler + ([kontrol] if kontrol is not None else [])
    return problar, kayitlar


def d1_satiri(u):
    """Canli D1'in `urunler` satirinin ikizi — YALNIZ sepetiFiyatla'nin SELECT ettigi kolonlar
    (tools/d1-sync.py KOLONLAR ile ayni alan adlari; fiyat HAM DIZE olarak durur)."""
    return {"id": u.get("id"), "baslik": u.get("baslik") or "", "kategori": u.get("kategori") or "",
            "fiyat": u.get("fiyat") or "", "parametrik": 1 if u.get("parametrik") else 0,
            "gorsel": (u.get("gorseller") or [""])[0],
            "konfigur": json.dumps(u["konfigur"], ensure_ascii=False) if u.get("konfigur") else "",
            "tur": TUR_FIZIKSEL if u.get("tur") == TUR_FIZIKSEL else ""}


# ---------------------------------------------------------------- yerel kahin (offline)
# 🔴 KAHIN = DEPONUN KENDI WORKER KODU. Fiyat kurali burada YENIDEN YAZILMAZ: shop/src/*.js
# oldugu gibi yuklenir ve GERCEK `POST /api/shop/fiyat` handler'i sahte bir D1 ile kosturulur.
# Ikinci bir hesap kopyasi olsaydi kapi kendi kopyasini dogrular, ayrisma gorunmezdi.
# Gecici agac shop/ ALTINDA AYNI DERINLIKTE kurulur ki kaynaklardaki "../../secenekler.js",
# "../../konfigur.js", "../../jenerator/..." goreli yollari GERCEK depoya cozulsun; JSON
# import satirlari icerige gomulur (Node surumunden bagimsiz olsun diye).
KAHIN_BETIGI = r"""
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const KOK = %(kok)s;
const GIRDI_YOL = %(girdi)s;
const SHOP = path.join(KOK, "shop");
const SRC = path.join(SHOP, "src");
const ONEK = "src-fizcanli-tmp-";

for (const ad of fs.readdirSync(SHOP)) {
  if (ad.startsWith(ONEK)) { fs.rmSync(path.join(SHOP, ad), { recursive: true, force: true }); }
}
const dizin = path.join(SHOP, ONEK + process.pid);
fs.mkdirSync(dizin, { recursive: true });
process.on("exit", () => { fs.rmSync(dizin, { recursive: true, force: true }); });

for (const ad of fs.readdirSync(SRC)) {
  if (!ad.endsWith(".js")) { continue; }
  const ham = fs.readFileSync(path.join(SRC, ad), "utf8");
  const gomulu = ham.replace(
    /^import\s+([A-Za-z_$][\w$]*)\s+from\s+"([^"]+\.json)";[ \t]*$/gm,
    (tam, isim, rel) => {
      const icerik = fs.readFileSync(path.resolve(SRC, rel), "utf8").trim();
      JSON.parse(icerik);
      return "const " + isim + " = " + icerik + ";";
    });
  if (/\bfrom\s+"[^"]*\.json"/.test(gomulu)) {
    throw new Error("JSON import gomulemedi (" + ad + ") — desen guncellenmeli");
  }
  fs.writeFileSync(path.join(dizin, ad), gomulu);
}

const mod = await import(pathToFileURL(path.join(dizin, "index.js")).href);
const S = globalThis.PRUVO_SECENEK;
if (!S || typeof S.fiyatSayisi !== "function") {
  throw new Error("secenekler.js yuklenemedi — liste fiyati kaynagi YOK");
}

const girdi = JSON.parse(fs.readFileSync(GIRDI_YOL, "utf8"));

/* Sahte D1: gercek D1 gibi PROJEKSIYON yapar (satir yalniz SECILEN kolonlari tasir), boylece
   SELECT'ten dusen bir kolon burada sessizce "hala var" gorunmez. YAZMA yolu BILEREK PATLAR:
   prova ucu D1'e yazarsa bu kahin gurultuyle olur (yan etkisizlik burada da olculur). */
function d1Sahte(satirlar) {
  const harita = new Map(satirlar.map((u) => [u.id, u]));
  return {
    prepare(sql) {
      const secilen = ((/SELECT ([^]*?) FROM /.exec(sql) || [])[1] || "")
        .split(",").map((a) => a.trim()).filter(Boolean);
      return {
        bind(...arg) {
          return {
            async all() {
              return { results: arg.map((id) => harita.get(id)).filter(Boolean).map((u) => {
                if (!secilen.length || secilen.includes("*")) { return u; }
                const o = {};
                for (const c of secilen) { if (c in u) { o[c] = u[c]; } }
                return o;
              }) };
            },
            async first() { return null; },
            async run() { throw new Error("PROVA YOLU D1'E YAZDI — yan etkisizlik IHLALI"); },
          };
        },
      };
    },
  };
}

const ENV = {
  SITE_URL: "https://pruvo3d.com",
  KATALOG: d1Sahte(girdi.urunler),
  FIYAT_RATE_LIMIT: { async limit() { return { success: true }; } },
};

const yerel = {};
for (const p of girdi.problar) {
  const kalem = { id: p.id, malzeme: p.malzeme, renk: p.renk, adet: 1 };
  if (p.renk_ozel) { kalem.renk_ozel = p.renk_ozel; }
  const istek = new Request("https://pruvo3d.com/api/shop/fiyat", {
    method: "POST",
    headers: { "Content-Type": "application/json", "CF-Connecting-IP": "127.0.0.1" },
    body: JSON.stringify({ sepet: [kalem] }),
  });
  const cevap = await mod.default.fetch(istek, ENV, { waitUntil() {} });
  let govde = {};
  try { govde = await cevap.json(); } catch (e) { govde = {}; }
  let sonuc;
  if (cevap.status === 200) {
    const s = (govde.satirlar || [])[0];
    sonuc = (s && Number.isInteger(s.birim_kurus))
      ? ["ok", s.birim_kurus] : ["hata", "beklenmeyen cevap bicimi"];
  } else if (cevap.status === 400) {
    sonuc = ["400", String(govde.hata || "?")];
  } else {
    sonuc = ["hata", "HTTP " + cevap.status];
  }
  yerel[p.anahtar] = sonuc;
}

/* LISTE KURUSU TEK KAYNAK: secenekler.js fiyatSayisi ("16.400 TL" -> 16400). Bu dosyada
   ikinci bir fiyat ayristiricisi YOKTUR. */
const liste = {};
for (const u of girdi.urunler) {
  const n = S.fiyatSayisi(u.fiyat);
  liste[u.id] = (n == null) ? null : n * 100;
}
console.log(JSON.stringify({ liste: liste, yerel: yerel }));
"""


def yerel_kahin(problar, kayitlar, node=None, zaman_asimi=180):
    """(liste_kurus, yerel_sonuclar) — depo HEAD'inin KENDI worker kodunu OFFLINE kosturur.
    Ag YOK, siparis YOK, depo agaci commit edilebilir halde KALIR (gecici dizin silinir).

    Hata halinde SystemExit DEGIL, ("hata", metin) sozlugu doner: kahin olculemedi diye kapi
    PATLAMAZ, OLCULEMEDI (rc 2) sinifina duser."""
    girdi = {"urunler": [d1_satiri(u) for u in kayitlar], "problar": problar}
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8",
                                     delete=False) as f:
        json.dump(girdi, f, ensure_ascii=False)
        girdi_yol = f.name
    betik = KAHIN_BETIGI % {"kok": json.dumps(ROOT), "girdi": json.dumps(girdi_yol)}
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", encoding="utf-8",
                                     delete=False) as f:
        f.write(betik)
        betik_yol = f.name
    try:
        p = subprocess.run([node or os.environ.get("NODE", "node"), betik_yol],
                           capture_output=True, text=True, timeout=zaman_asimi)
    except (OSError, subprocess.SubprocessError) as e:
        return ({}, {"__hata__": "node kosturulamadi: %s" % e})
    finally:
        os.unlink(betik_yol)
        os.unlink(girdi_yol)
    if p.returncode != 0:
        return ({}, {"__hata__": "yerel kahin kosmadi (exit %d): %s"
                                 % (p.returncode, (p.stderr or p.stdout or "")[-400:])})
    satirlar = (p.stdout or "").strip().splitlines()
    if not satirlar:
        return ({}, {"__hata__": "yerel kahin bos cikti verdi"})
    try:
        veri = json.loads(satirlar[-1])
    except ValueError as e:
        return ({}, {"__hata__": "yerel kahin ciktisi ayristirilamadi: %s" % e})
    yerel = {k: tuple(v) for k, v in (veri.get("yerel") or {}).items()}
    return (veri.get("liste") or {}, yerel)


# ---------------------------------------------------------------- canli okuma
def _prova(uc, govde, zaman_asimi=15):
    """Tek canli prova. Doner: ("ok", kurus) | ("400", hata_kodu) | ("hata", metin).

    Ag/HTTP katmani BURADA izole — karar mantigi (karsilastir) bu fonksiyonu SAHTELEYEREK
    offline sinanabilir; ikinci bir kod yolu yoktur."""
    ham = json.dumps(govde).encode("utf-8")
    istek = urllib.request.Request(uc, data=ham, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(istek, timeout=zaman_asimi) as y:
            veri = json.loads(y.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            veri = json.loads(e.read().decode("utf-8"))
        except Exception:
            return ("hata", "HTTP %d (govde okunamadi)" % e.code)
        if e.code == 429:
            return ("hata", "429 hiz siniri")
        if e.code == 400:
            return ("400", str(veri.get("hata") or "?"))
        return ("hata", "HTTP %d: %s" % (e.code, veri.get("hata") or "?"))
    except Exception as e:                                   # ag/DNS/TLS/zaman asimi
        return ("hata", type(e).__name__ + ": " + str(e))
    satirlar = veri.get("satirlar")
    if not isinstance(satirlar, list) or len(satirlar) != 1:
        return ("hata", "beklenmeyen cevap bicimi")
    k = satirlar[0].get("birim_kurus")
    if not isinstance(k, int):
        return ("hata", "birim_kurus sayisal degil")
    return ("ok", k)


def canli_oku(problar, uc, gecikme=GECIKME_VARSAYILAN, prova=_prova):
    """{anahtar: sonuc} — her prova icin bir istek. `prova` disaridan verilebilir
    (kendini-test sahte katmani kullanir)."""
    out = {}
    for i, p in enumerate(problar):
        if i and gecikme:
            time.sleep(gecikme)
        kalem = {"id": p["id"], "malzeme": p["malzeme"], "renk": p["renk"], "adet": 1}
        if p.get("renk_ozel"):
            kalem["renk_ozel"] = p["renk_ozel"]
        out[p["anahtar"]] = prova(uc, {"sepet": [kalem]})
    return out


# ---------------------------------------------------------------- karar (SAF)
def _yon(fark):
    return "EKSIK" if fark < 0 else "FAZLA"


def karsilastir(problar, liste, yerel, canli):
    """SAF karar fonksiyonu (ag YOK, dosya YOK) -> (durum, satirlar).
    durum: "PARITE" | "DRIFT" | "OLCULEMEDI"    satirlar: [(sinif, anahtar, aciklama)]

    SINIF ONCELIGI (bilerek, konfigur-canli-kapisi ile AYNI): DRIFT KANITI olcum arizasini
    EZER. Bir uruntte fazla tahsilat kaniti varken baska bir uruntte ag hatasi olmasi kapiyi
    "olculemedi"ye DUSUREMEZ — elimizde ZATEN para kaybettiren bir bulgu var."""
    satirlar = []
    drift = 0
    ariza = 0

    # 🔴 BOS ORNEKLEM = OLCULEMEDI. "Olculecek fiziksel urun bulamadim" ASLA yesil degildir:
    # `tur` alani katalogtan toptan dusse (ya da secim suzgeci bozulsa) kapi SESSIZ YESIL
    # yanardi ve tam da korumasi gereken 676 urun olcumsuz kalirdi.
    if not [p for p in problar if p["sinif"] == "FIZIKSEL"]:
        return ("OLCULEMEDI", [("ARIZA", "-", "ORNEKLEMDE FIZIKSEL URUN YOK — kapinin "
                                "koruduğu sinif olculemedi (katalogda `tur` alani dustu mu?)")])
    if not [p for p in problar if p["sinif"] == "BASKI"]:
        return ("OLCULEMEDI", [("ARIZA", "-", "KONTROL TABANI YOK — yanlis-pozitif butcesi ve "
                                "provanin ayirt edici gucu olculemez")])

    kahin_hatasi = yerel.get("__hata__")
    if kahin_hatasi:
        ariza += 1
        satirlar.append(("ARIZA", "-", "YEREL KAHIN olculemedi — " + str(kahin_hatasi)))

    for p in problar:
        ah = p["anahtar"]
        etiket = "%s [%s %s]" % (p["id"], p["malzeme"], p["renk"])
        lk = liste.get(p["id"])
        c = canli.get(ah)
        y = yerel.get(ah)

        # -- (A) CANLI LISTE: fiziksel uruntte HER kombinasyon liste fiyatidir.
        if c is None:
            ariza += 1
            satirlar.append(("ARIZA", etiket, "canli sonuc YOK"))
        elif c[0] == "400":
            drift += 1
            if c[1] == "bilinmeyen-urun":
                satirlar.append(("TANIMIYOR", etiket,
                                 "canli worker urunu D1'de BULAMIYOR (katalog senkronu eksik) "
                                 "— kart kanali bu uruntte KAPALI"))
            else:
                satirlar.append(("TANIMIYOR", etiket,
                                 "canli worker kalemi REDDEDIYOR (400 " + str(c[1]) +
                                 ") — kart kanali KAPALI, kalem WhatsApp'a duser"))
        elif c[0] != "ok":
            ariza += 1
            satirlar.append(("ARIZA", etiket, "canli olculemedi — " + str(c[1])))
        elif not isinstance(lk, int) or lk <= 0:
            ariza += 1
            satirlar.append(("ARIZA", etiket, "liste kurusu OKUNAMADI (fiyat alani bos/bozuk)"))
        elif p["sinif"] == "FIZIKSEL":
            if c[1] != lk:
                drift += 1
                fark = c[1] - lk
                satirlar.append(("SAPMA", etiket,
                                 "HAZIR TICARI MALDA CARPAN UYGULANMIS: canli %d kurus, liste "
                                 "%d kurus (fark %+d kurus = %s tahsilat, x%.3f)"
                                 % (c[1], lk, fark, _yon(fark), c[1] / float(lk))))
        elif p["sinif"] == "BASKI":
            # -- (D) AYIRT EDICI GUC / yanlis-pozitif butcesi. Baski uruntte carpan MESRUDUR;
            # kapi onu YAKMAZ. Ama en pahali kombinasyon liste fiyatina ESITSE prova artik
            # hicbir carpani goremiyor demektir -> "A yesil" ANLAMSIZ olur.
            if p["kombinasyon"] == "en-pahali" and c[1] <= lk:
                drift += 1
                satirlar.append(("AYIRT-EDICI-YOK", etiket,
                                 "KONTROL TABANI: baski uruntte en pahali kombinasyon liste "
                                 "fiyatini ASMIYOR (canli %d <= liste %d) — ya baski fiyati "
                                 "geriledi ya da prova ayirt edici gucunu KAYBETTI"
                                 % (c[1], lk)))
            elif p["kombinasyon"] == "taban" and c[1] != lk:
                drift += 1
                satirlar.append(("LISTE-SAPMASI", etiket,
                                 "KONTROL TABANI: carpansiz kombinasyonda canli %d kurus, depo "
                                 "listesi %d kurus — canli D1 fiyati depo ile AYRISMIS"
                                 % (c[1], lk)))

        # -- (B) DEPO LISTE: ayni iddia YEREL KAHIN'de. Teshisi ayiran eksen (bayat paket mi,
        # depoda da kirik mi).
        if (p["sinif"] == "FIZIKSEL" and not kahin_hatasi and y is not None
                and y[0] == "ok" and isinstance(lk, int) and lk > 0 and y[1] != lk):
            drift += 1
            satirlar.append(("REPO-KIRIK", etiket,
                             "DEPO HEAD'inin worker kodu da liste fiyatini vermiyor: yerel %d "
                             "kurus, liste %d kurus — once KOD duzelir, deploy sonra"
                             % (y[1], lk)))

        # -- (C) NESIL: canli paket depodaki kaynakla ayni nesli tasiyor mu (fiziksel kurala
        # BAGLI OLMAYAN, genel sinyal — yarin baska bir fiyat kolu degisse de calisir).
        if kahin_hatasi or y is None:
            pass
        elif y[0] == "hata":
            ariza += 1
            satirlar.append(("ARIZA", etiket, "yerel kahin olculemedi — " + str(y[1])))
        elif c is not None and c[0] == "ok" and y[0] == "ok" and c[1] != y[1]:
            drift += 1
            satirlar.append(("NESIL", etiket,
                             "CANLI PAKET BAYAT: canli %d kurus, depo HEAD'inin kodu %d kurus "
                             "(fark %+d kurus) — Worker yeniden yayinlanmali"
                             % (c[1], y[1], c[1] - y[1])))
        elif c is not None and c[0] == "400" and y[0] == "ok":
            # Kalem canlida REDDEDILIYOR ama depo kodu onu FIYATLIYOR -> bayat paket.
            # (Drift zaten yukarida TANIMIYOR olarak sayildi; burada yalniz TESHIS eklenir.)
            satirlar.append(("NESIL", etiket,
                             "CANLI PAKET BAYAT: canli kalemi 400 ile reddederken depo "
                             "HEAD'inin kodu %d kurus hesapliyor" % y[1]))
        elif c is not None and c[0] == "ok" and y[0] == "400":
            drift += 1
            satirlar.append(("NESIL", etiket,
                             "canli %d kurus tahsil ederken depo HEAD'inin kodu kalemi "
                             "REDDEDIYOR (400 %s)" % (c[1], y[1])))

    if drift:
        return ("DRIFT", satirlar)
    if ariza:
        return ("OLCULEMEDI", satirlar)
    return ("PARITE", satirlar)


DURUM_KOD = {"PARITE": 0, "DRIFT": 1, "OLCULEMEDI": 2}
SORUN_SINIFLARI = ("SAPMA", "TANIMIYOR", "NESIL", "REPO-KIRIK", "AYIRT-EDICI-YOK",
                   "LISTE-SAPMASI", "ARIZA")


def rapor(durum, satirlar, problar, uc, sessiz=False):
    if sessiz:
        return DURUM_KOD[durum]
    fiz = len([p for p in problar if p["sinif"] == "FIZIKSEL"])
    kon = len([p for p in problar if p["sinif"] == "BASKI"])
    print("FIZIKSEL CANLI KAPISI")
    print("  uc        : " + uc)
    print("  prova     : %d fiziksel + %d kontrol (baski) = %d iddia kumesi"
          % (fiz, kon, len(problar)))
    sayim = {s: len([x for x in satirlar if x[0] == s]) for s in SORUN_SINIFLARI}
    print("  sapma: %d  tanimiyor: %d  nesil: %d  repo-kirik: %d  ayirt-edici-yok: %d  "
          "liste-sapmasi: %d  olculemeyen: %d"
          % (sayim["SAPMA"], sayim["TANIMIYOR"], sayim["NESIL"], sayim["REPO-KIRIK"],
             sayim["AYIRT-EDICI-YOK"], sayim["LISTE-SAPMASI"], sayim["ARIZA"]))
    for sinif, ah, aciklama in satirlar:
        print("    %-16s %s — %s" % (sinif, ah, aciklama))
    print("-" * 70)
    if durum == "PARITE":
        print("SONUC: YESIL ✅  — hazir ticari malda canli tahsilat LISTE FIYATI; canli paket "
              "depo HEAD'i ile ayni nesil.")
    elif durum == "DRIFT":
        print("SONUC: KIRMIZI ❌  — yukaridaki kalemlerde MUSTERIDEN YANLIS TUTAR tahsil "
              "ediliyor ya da kalem odenemiyor.")
        print("  COZUM (Okan/KraL kapisi — canli odeme yolu):")
        print("    1) REPO-KIRIK satiri VARSA once KODU duzelt (deploy bir sey duzeltmez).")
        print("    2) shop dizininden Worker'i yeniden yayinla.")
        print("    3) bu kapiyi tekrar kostur -> YESIL olmali.")
    else:
        print("SONUC: ⚪ OLCULEMEDI — parite KANITLANMADI (sessiz yesil verilmez).")
        print("  Ag/uc/node erisilemedi, hiz sinirina takildi ya da orneklem BOS; tekrar kostur.")
    return DURUM_KOD[durum]


# ---------------------------------------------------------------- kendini test
def kendini_test(node=None):
    """OFFLINE kabul: karar mantigi + HTTP eslemesi + KIRMIZI-MUTASYON + yanlis-pozitif +
    YEREL KAHIN'in fiilen kosmasi. Ag YOK, depo dosyasi DEGISMEZ."""
    ham = ["FIZIKSEL CANLI KAPISI — KENDINI TEST (offline)"]
    kirmizi = 0

    def iddia(ad, kosul, detay=""):
        nonlocal kirmizi
        if kosul:
            ham.append("    ✅ " + ad)
        else:
            kirmizi += 1
            ham.append("    ❌ " + ad + (" — " + str(detay) if detay else ""))

    # Sentetik sahne: 1 fiziksel urun (liste 100000 krs) x 3 kombinasyon + 1 baski kontrolu.
    def sahne():
        problar = []
        for malzeme, renk, ozel, etiket in KOMBINASYONLAR:
            problar.append({"id": "fiz", "sinif": "FIZIKSEL", "malzeme": malzeme, "renk": renk,
                            "renk_ozel": ozel, "kombinasyon": etiket,
                            "anahtar": _anahtar("fiz", malzeme, renk)})
        for malzeme, renk, ozel, etiket in KONTROL_KOMBINASYONLARI:
            problar.append({"id": "bas", "sinif": "BASKI", "malzeme": malzeme, "renk": renk,
                            "renk_ozel": ozel, "kombinasyon": etiket,
                            "anahtar": _anahtar("bas", malzeme, renk)})
        liste = {"fiz": 100000, "bas": 100000}
        return problar, liste

    def saglikli(problar):
        """Her sey dogruyken beklenen sonuc kumesi: fiziksel HEP liste, baski carpanli."""
        out = {}
        for p in problar:
            if p["sinif"] == "FIZIKSEL":
                out[p["anahtar"]] = ("ok", 100000)
            elif p["kombinasyon"] == "taban":
                out[p["anahtar"]] = ("ok", 100000)
            else:
                out[p["anahtar"]] = ("ok", 184000)
        return out

    ham.append("  (A) KARAR MANTIGI")
    problar, liste = sahne()
    iyi = saglikli(problar)
    d, s = karsilastir(problar, liste, dict(iyi), dict(iyi))
    iddia("S1 her sey dogru -> PARITE (rc 0)", d == "PARITE" and DURUM_KOD[d] == 0,
          [x for x in s])

    # 🔴 1 AGU'DA CANLIDA OLCULEN VAKA: fiziksel uruntte ASA+"Diger" -> liste x1,840.
    bozuk = dict(iyi)
    bozuk[_anahtar("fiz", "ASA", "Diğer")] = ("ok", 184000)
    d, s = karsilastir(problar, liste, dict(iyi), bozuk)
    iddia("S2 fiziksel uruntte carpan uygulanmis (canli) -> DRIFT (rc 1)", d == "DRIFT", d)
    iddia("S2 teshis 'FAZLA tahsilat' + carpani soyluyor",
          any("FAZLA tahsilat" in a and "x1.840" in a for k, _, a in s if k == "SAPMA"),
          [a for k, _, a in s if k == "SAPMA"])
    iddia("S2 AYNI turda NESIL ekseni de konusuyor (canli != yerel kahin)",
          any(k == "NESIL" for k, _, a in s))

    eksik = dict(iyi)
    eksik[_anahtar("fiz", "PLA", "Siyah")] = ("ok", 50000)
    d, s = karsilastir(problar, liste, dict(iyi), eksik)
    iddia("S3 eksik tahsilat yonu EKSIK diye etiketleniyor",
          d == "DRIFT" and any("EKSIK tahsilat" in a for k, _, a in s if k == "SAPMA"))

    # Depoda da kirik: canli VE yerel kahin ayni yanlisi veriyor -> NESIL yesil, REPO-KIRIK.
    ikisi = dict(iyi)
    ikisi[_anahtar("fiz", "ASA", "Diğer")] = ("ok", 184000)
    d, s = karsilastir(problar, liste, dict(ikisi), dict(ikisi))
    iddia("S4 kural DEPODA da kirik -> REPO-KIRIK teshisi", d == "DRIFT" and
          any(k == "REPO-KIRIK" for k, _, a in s), [k for k, _, a in s])
    iddia("S4 bu halde NESIL (bayat paket) SUCLANMIYOR (yanlis teshis yok)",
          not any(k == "NESIL" for k, _, a in s), [k for k, _, a in s])

    # Bayat paket, fiziksel kuraldan BAGIMSIZ: baski urununde canli != yerel.
    nesil = dict(iyi)
    nesil[_anahtar("bas", "ASA", "Diğer")] = ("ok", 178250)
    d, s = karsilastir(problar, liste, dict(iyi), nesil)
    iddia("S5 baski urununde canli != depo -> NESIL (fiziksel kurala bagli OLMAYAN sinyal)",
          d == "DRIFT" and any(k == "NESIL" for k, _, a in s), [k for k, _, a in s])

    # Kontrol tabani: baski urununde carpan KALKMIS -> ayirt edici guc kaybi.
    kor = dict(iyi)
    kor[_anahtar("bas", "ASA", "Diğer")] = ("ok", 100000)
    d, s = karsilastir(problar, liste, dict(kor), dict(kor))
    iddia("S6 baskida carpan kalkti -> AYIRT-EDICI-YOK (kapi kendi korlugunu yakiyor)",
          d == "DRIFT" and any(k == "AYIRT-EDICI-YOK" for k, _, a in s), [k for k, _, a in s])

    # 🔴 YANLIS-POZITIF BUTCESI: baski urununde carpan MESRUDUR — kapi onu YAKMAZ.
    d, s = karsilastir(problar, liste, dict(iyi), dict(iyi))
    iddia("S7 baski (ozel uretim) urununde 1,840 carpan MESRU -> hicbir satir yanmiyor",
          d == "PARITE" and not any(x[1].startswith("bas") for x in s
                                    if x[0] in SORUN_SINIFLARI),
          [x for x in s])

    hata = dict(iyi)
    for a in list(hata):
        hata[a] = ("hata", "ag")
    d, s = karsilastir(problar, liste, dict(iyi), hata)
    iddia("S8 ag hatasi -> OLCULEMEDI (rc 2), ASLA yesil",
          d == "OLCULEMEDI" and DURUM_KOD[d] == 2, d)

    karma = dict(hata)
    karma[_anahtar("fiz", "ASA", "Diğer")] = ("ok", 184000)
    d, s = karsilastir(problar, liste, dict(iyi), karma)
    iddia("S9 ariza + sapma karisik -> DRIFT (kanit arizayi ezer)", d == "DRIFT", d)

    d, s = karsilastir(problar, liste, dict(iyi), {})
    iddia("S10 cevabi HIC gelmeyen prova -> OLCULEMEDI (sessiz atlanmaz)",
          d == "OLCULEMEDI", d)

    d, s = karsilastir(problar, liste, {"__hata__": "node yok"}, dict(iyi))
    iddia("S11 yerel kahin kosmadi -> OLCULEMEDI (kahinsiz parite ILAN EDILMEZ)",
          d == "OLCULEMEDI", d)

    d, s = karsilastir(problar, {"fiz": None, "bas": 100000}, dict(iyi), dict(iyi))
    iddia("S12 liste fiyati okunamadi -> OLCULEMEDI (0 TL'ye dusulmez)", d == "OLCULEMEDI", d)

    dortyuz = dict(iyi)
    dortyuz[_anahtar("fiz", "PLA", "Siyah")] = ("400", "bilinmeyen-urun")
    d, s = karsilastir(problar, liste, dict(iyi), dortyuz)
    iddia("S13 canlida TANINMAYAN urun -> DRIFT + D1 senkron teshisi",
          d == "DRIFT" and any("D1" in a for k, _, a in s if k == "TANIMIYOR"))

    # 🔴 BOS ORNEKLEM: katalogtan `tur` toptan dusse kapi SESSIZ YESIL yanmamali.
    d, s = karsilastir([p for p in problar if p["sinif"] == "BASKI"], liste,
                       dict(iyi), dict(iyi))
    iddia("S14 orneklemde FIZIKSEL urun YOK -> OLCULEMEDI (sessiz yesil YOK)",
          d == "OLCULEMEDI" and any("FIZIKSEL URUN YOK" in a for _k, _i, a in s), d)
    d, s = karsilastir([p for p in problar if p["sinif"] == "FIZIKSEL"], liste,
                       dict(iyi), dict(iyi))
    iddia("S15 KONTROL TABANI yoksa -> OLCULEMEDI (yanlis-pozitif butcesi olculemez)",
          d == "OLCULEMEDI", d)

    # ---- (B) HTTP KATMANI: kod -> sinif eslemesi (sahte urlopen, ag YOK)
    ham.append("  (B) HTTP KATMANI")

    class _SahteHata(urllib.error.HTTPError):
        def __init__(self, kod, govde):
            super().__init__("u", kod, "x", {}, io.BytesIO(json.dumps(govde).encode()))

    gercek = urllib.request.urlopen
    for ad, sahte_hata, beklenen in [
            ("400 bilinmeyen-urun -> ('400', ...)", _SahteHata(400, {"hata": "bilinmeyen-urun"}),
             "400"),
            ("429 -> ('hata', ...) (drift SAYILMAZ)", _SahteHata(429, {"hata": "cok-istek"}),
             "hata"),
            ("500 -> ('hata', ...)", _SahteHata(500, {"hata": "sunucu-hatasi"}), "hata")]:
        def _patlat(*a, **k):
            raise sahte_hata
        urllib.request.urlopen = _patlat
        try:
            tur, _ = _prova("http://ornek/uc", {"sepet": [{"id": "fiz"}]})
        finally:
            urllib.request.urlopen = gercek
        iddia("HTTP " + ad, tur == beklenen, tur)

    # ---- (C) KIRMIZI-MUTASYON: nobet NO-OP yapilinca ilgili senaryo YESILE donmeli
    # (donmuyorsa o senaryo bu satirlari OLCMUYOR demektir = olu iddia).
    ham.append("  (C) KIRMIZI-MUTASYON")
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        oz = f.read()
    sapma_sahne = dict(iyi)
    sapma_sahne[_anahtar("fiz", "ASA", "Diğer")] = ("ok", 184000)
    # 🔴 "SESSIZ GECTI" OLCUSU SINIF BAZLIDIR, sadece rc DEGIL: REPO-KIRIK gibi bazi eksenler
    # tek baslarina ASLA yalniz yanmaz (kural depoda kirikse ya canli da kiriktir -> SAPMA, ya
    # canli dogrudur -> NESIL). Yalniz rc'ye baksaydik o eksenin mutanti "hala DRIFT" gorunur
    # ve nobetci OLCULEMEZ olurdu. Bu yuzden her mutasyon icin KAYBOLMASI GEREKEN SINIF yazilir
    # ve once ORIJINALIN o sinifi FIILEN URETTIGI dogrulanir (bos iddia olmasin).
    #
    # ⚠️ CAPA METINLERI PARCALI YAZILIR: capa duz literal olsaydi bu tablonun KENDISI kaynakta
    # ikinci bir eslesme uretir ve "capa yok/cok" dalina duserdi.
    mutasyonlar = [
        ("MU1 fiziksel liste karsilastirmasi olduruldu (fazla tahsilat gorulmez)",
         "            if c[1] " + "!= lk:", "            if False:",
         dict(iyi), dict(sapma_sahne), "SAPMA"),
        ("MU2 NESIL ekseni olduruldu (bayat paket gorulmez)",
         "        elif c is not None and c[0] == \"ok\" and y[0] == \"ok\" and c[1] " +
         "!= y[1]:", "        elif False:",
         dict(iyi), nesil, "NESIL"),
        ("MU3 kontrol tabani (ayirt edici guc) olduruldu",
         '            if p["kombinasyon"] == "en-pahali" and c[1] ' + "<= lk:",
         "            if False:", dict(kor), dict(kor), "AYIRT-EDICI-YOK"),
        ("MU4 REPO-KIRIK ekseni olduruldu (depodaki kirik kural gorulmez)",
         '        if (p["sinif"] == "FIZIK' + 'SEL" and not kahin_hatasi and y is not None',
         "        if (False and y is not None", dict(ikisi), dict(ikisi), "REPO-KIRIK"),
        ("MU5 ariza -> PARITE'ye cevrildi (sessiz yesil)",
         '    if ariza:\n        return ("OLCULEMEDI", satirlar)', "    if False:\n        pass",
         dict(iyi), hata, None),
    ]
    for ad, capa, yerine, my, mc, kayip in mutasyonlar:
        if oz.count(capa) != 1:
            kirmizi += 1
            ham.append("    ❌ MUTASYON CAPASI YOK/COK (nobet yeniden yazilmis): " + ad)
            continue
        d_o, s_o = karsilastir(problar, liste, my, mc)
        if kayip is not None and not any(x[0] == kayip for x in s_o):
            kirmizi += 1
            ham.append("    ❌ BOS IDDIA: " + ad + " -> ORIJINAL '" + kayip + "' uretmiyor")
            continue
        if kayip is None and d_o != "OLCULEMEDI":
            kirmizi += 1
            ham.append("    ❌ BOS IDDIA: " + ad + " -> ORIJINAL OLCULEMEDI demiyor (" +
                       str(d_o) + ")")
            continue
        ns = {"__name__": "fck_mutant", "__file__": os.path.abspath(__file__)}
        exec(compile(oz.replace(capa, yerine), "<fck-mutant>", "exec"), ns)
        d_m, s_m = ns["karsilastir"](problar, liste, my, mc)
        if kayip is None:
            sessiz = (d_m != "OLCULEMEDI")
        else:
            sessiz = not any(x[0] == kayip for x in s_m)
        if not sessiz:
            kirmizi += 1
            ham.append("    ❌ OLU IDDIA: " + ad + " -> mutant HALA konusuyor (" +
                       str(d_m) + ")")
        else:
            ham.append("    ✅ " + ad + " -> mutant sessiz gecti (nobet YUK TASIYOR)")

    # ---- (D) GERCEK KATALOG + YEREL KAHIN (offline ama node ISTER)
    ham.append("  (D) GERCEK KATALOG + YEREL KAHIN (offline, node)")
    try:
        with open(URUNLER_VARSAYILAN, encoding="utf-8") as f:
            urunler = json.load(f)
    except Exception as e:
        urunler = None
        kirmizi += 1
        ham.append("    ❌ urunler.json okunamadi — " + str(e))
    if urunler is not None:
        g_problar, g_kayitlar = orneklem_sec(urunler)
        iddia("D1 gercek katalogtan fiziksel orneklem cikti (%d prova)" % len(g_problar),
              len([p for p in g_problar if p["sinif"] == "FIZIKSEL"]) > 0, len(g_problar))
        iddia("D2 kontrol tabani (baski) secildi ve fiziksel URUN DEGIL",
              any(p["sinif"] == "BASKI" for p in g_problar))
        g_liste, g_yerel = yerel_kahin(g_problar, g_kayitlar, node=node)
        if g_yerel.get("__hata__"):
            kirmizi += 1
            ham.append("    ❌ YEREL KAHIN KOSMADI (fail-closed) — " + str(g_yerel["__hata__"]))
            ham.append("       deploy.yml setup-node BLOKLAYICI on-kosuldur; node olmadan "
                       "bu kol yesil SAYILMAZ.")
        else:
            fiz_ok = [p for p in g_problar if p["sinif"] == "FIZIKSEL"]
            liste_esit = [p for p in fiz_ok
                          if g_yerel.get(p["anahtar"], ("?",))[0] == "ok"
                          and g_yerel[p["anahtar"]][1] == g_liste.get(p["id"])]
            iddia("D3 depo HEAD'inin worker kodu fiziksel uruntte LISTE fiyati veriyor (%d/%d)"
                  % (len(liste_esit), len(fiz_ok)), len(liste_esit) == len(fiz_ok),
                  [(p["anahtar"], g_yerel.get(p["anahtar"]), g_liste.get(p["id"]))
                   for p in fiz_ok if p not in liste_esit][:3])
            kon = [p for p in g_problar
                   if p["sinif"] == "BASKI" and p["kombinasyon"] == "en-pahali"]
            iddia("D4 depo kodu BASKI urununde carpani UYGULUYOR (kontrol tabani anlamli)",
                  all(g_yerel.get(p["anahtar"], ("?",))[0] == "ok"
                      and g_yerel[p["anahtar"]][1] > (g_liste.get(p["id"]) or 0) for p in kon),
                  [(p["anahtar"], g_yerel.get(p["anahtar"]), g_liste.get(p["id"]))
                   for p in kon])
            # YANLIS-POZITIF: canli, yerel kahinle BIREBIR ayni olsaydi kapi YESIL olmali
            # (kapi "hep kirmizi" olamaz).
            d, _s = karsilastir(g_problar, g_liste, dict(g_yerel), dict(g_yerel))
            iddia("D5 canli == depo kodu senaryosunda kapi YESIL (hep-kirmizi degil)",
                  d == "PARITE", d)

    print("\n".join(ham))
    print("-" * 70)
    print("SONUC: YESIL ✅ (kendini test)" if kirmizi == 0
          else "SONUC: KIRMIZI ❌ — %d iddia kaldi" % kirmizi)
    return 0 if kirmizi == 0 else 1


# ---------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uc", default=UC_VARSAYILAN)
    ap.add_argument("--urunler", default=URUNLER_VARSAYILAN)
    ap.add_argument("--adet", type=int, default=ADET_VARSAYILAN,
                    help="ornekleme alinan fiziksel urun sayisi")
    ap.add_argument("--gecikme", type=float, default=GECIKME_VARSAYILAN,
                    help="istekler arasi bekleme (FIYAT_RATE_LIMIT 60/60 sn)")
    ap.add_argument("--node", default=None, help="node ikili yolu (varsayilan: $NODE ya da node)")
    ap.add_argument("--sessiz", action="store_true", help="yalniz cikis kodu")
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    a = ap.parse_args(argv)
    if a.kendini:
        return kendini_test(node=a.node)
    with open(a.urunler, encoding="utf-8") as f:
        urunler = json.load(f)
    problar, kayitlar = orneklem_sec(urunler, a.adet)
    if not problar:
        return rapor("OLCULEMEDI",
                     [("ARIZA", "-", "ORNEKLEMDE FIZIKSEL URUN YOK — katalogda `tur` alani "
                       "dustu mu?")], problar, a.uc, a.sessiz)
    liste, yerel = yerel_kahin(problar, kayitlar, node=a.node)
    canli = canli_oku(problar, a.uc, a.gecikme)
    durum, satirlar = karsilastir(problar, liste, yerel, canli)
    return rapor(durum, satirlar, problar, a.uc, a.sessiz)


if __name__ == "__main__":
    sys.exit(main())

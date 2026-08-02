#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YONET ANAHTAR/CEREZ KABUL ALT KUMESI (`node shop/test/kabul.js --yonet-cerez`) MUTASYON HARNESS'I.

NE ISE YARAR: bu alt kume bir GUVENLIK kapisidir (siparis yonetimi paneline giris).
"iddialar yesil" tek basina HICBIR SEY kanitlamaz — kanit, korumayi BOZUNCA iddianin
KIRMIZI yanmasidir (mutasyon) VE bozulmamis/ilgisiz refaktorde YESIL kalmasidir
(kontrol mutanti). Bu surucu olmadan, ileride bir iddianin icini bosaltan degisiklik
nobetciyi SESSIZCE oldurur ve kimse fark etmez.

NEDEN VAR: `yonet-anahtar-cerez` dali mutasyon bataryasini RAPORDA anlatti ama
SURUCUYU COMMIT ETMEDI ("python3 <mutasyon surucusu v2>"). Guvenlik kapisinin kaniti
yeniden uretilemez hale gelmisti. Bu dosya o boslugu kapatir; depo konvansiyonu
(tools/yayin-gecikme-mutasyon.py, tools/konfigur-nobet-mutasyon.py,
tools/commit-mesaji-mutasyon.py, tools/gecmis-geri-donus-mutasyon.py) surucunun
REPODA DURMASIDIR.

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir. Canli shop/src/yonet.js'i bozup `finally`
ile geri alma deseni bu evde YASAK: tek bir kesinti (Ctrl-C, OOM, kota bitmesi)
calisma agacinda MUTANT birakir — yani deploy edilebilir bir ARKA KAPI. Burada gecici
bir dizine kabul testinin ihtiyac duydugu agacin TAM KOPYASI yazilir; kaynak agaca
HICBIR YAZMA yapilmaz, aynada kaynaga giden SYMLINK bulunmadigi olculur, ve kaynak
dosyanin sha256'si basta alinip HER kosumdan sonra + en sonda yeniden dogrulanir.

MUTANTLAR (hepsi GERCEK, canliya sizabilecek bozulmalar; hepsi KIRMIZI yanmali)
  M1 ?anahtar= geri geldi     — isin BAS SEBEBI: anahtar erisim loglarina/Referer'a yazilir
  M2 sabitEsit fail-open      — `String(a || "")`: bos sifre + tanimsiz secret = YETKI
  M3 secret kapisi POST'un    — yonet()'in kapisi giris POST'undan SONRAYA alinir VE
     ARKASINA alindi            girisYap'in kendi kapisi silinir (iki kapi BIRDEN duser)
  M4 ikame DIZESI             — girisEkrani'nda fonksiyon yerine dize: `$\\`` enjeksiyonu
  M5 hiz siniri kalkti        — paylasilan tek anahtara kaba kuvvet serbest
  M6 govde ust siniri kalkti  — anahtarsiz uca sinirsiz govde ayristirma
  M7 cerez adi naive includes — `pruvo_yonet_x=<anahtar>` yakin-iskasi yetki alir
  M8 HttpOnly dusuruldu       — XSS oturum cerezini calabilir
  M9 SameSite=Strict -> Lax   — capraz-site gezinmede cerez gider (CSRF ekseni acilir)
  M10 girisYap'in KENDI secret — savunma derinliginin IC KATMANI duser. 2 Agu'a kadar bu
      kapisi silindi             mutant SURVIVOR'di (K4 adiyla, YESIL beklentisiyle):
                                 alt kume onu HIC olcmuyordu, cunku tek iddia (eski "C22")
                                 istegi yonet() uzerinden gecirip IKI kapinin VEYA'sini
                                 olcuyordu. Iddia C22a (girisYap IZOLE, yonet() bypass) +
                                 C22b (yonet() ust kapisi IZOLE) olarak IKIYE AYRILDI ve
                                 bu mutant artik KIRMIZI yaniyor -> SURVIVOR degil.

KONTROL MUTANTLARI (YESIL kalmali — surucu "her sey kirmizi" diye ucuza gecemesin;
ayrica kapinin ILGISIZ refaktorde yanlis alarm uretmedigi olculur)
  K1 sabitEsit'te YEREL DEGISKEN adi degisti (davranis ayni)
  K2 girisYap'a YORUM SATIRI eklendi (davranis ayni)
  K3 anahtarGecerli'de baslik/cerez KONTROL SIRASI takas edildi (iki tasiyici da calisir)
  (K4 EMEKLI: yukaridaki M10'a donustu. Beyan edilmis SURVIVOR'in tehlikesi olculdu —
   "bugun yesil kalmasi normal" demek, o katmanin HIC olculmedigini gizliyordu; iki ayri
   yesil commit iki kapiyi ayri ayri dusurup birlikte anahtarsiz cerez kurulumuna kapi
   acabilirdi. Bir katmanin savunma derinligi oldugu iddiasi ancak o katman TEK BASINA
   olculuyorsa kanittir.)

KABUL — HER KIRMIZI-BEKLENTILI MUTANT ICIN UC SART BIRDEN:
  1. IDDIA SAYISI taban kosumla AYNI. (Cokme kirmiziyla KARISIR: mutant testi
     COKERTIRSE cikis kodu da 1 olur ama hicbir sey OLCULMEMISTIR. Sayi esitligi
     "test sonuna kadar kostu" demektir; bu depoda olculdu — sorgu parametresini geri
     ekleyen mutant ilk turda SONUC satirini hic basmamisti.)
  2. Cikis kodu 1 VE en az bir ❌ satiri.
  3. BEKLENEN IDDIA KODLARININ HEPSI kirmizi satirlarda ADIYLA gecmeli (isaret sarti —
     mutant "kaza eseri" baska bir yerden kirmizi yakip gecmis sayilmasin).
Kontrol mutantlarinda: cikis 0, ❌ yok, IDDIA SAYISI taban ile ayni.

CAPA YOK: taban iddia sayisi KOSUMDA olculur, kodda SABIT DEGILDIR (bugunku sayiyi
yazsak, yarin bir iddia eklenince sahte kirmizi yanardi). Mutant kosumlari o OLCULEN
sayiyla karsilastirilir.

Ag YOK · wrangler YOK · D1 YOK · canli uc YOK (alt kumenin kendisi deterministik).
Bu harness CI'da KOSMAZ — gelistirici/curutucu aracidir.
Kullanim: python3 tools/yonet-cerez-mutasyon.py   (0 = tum mutantlar yakalandi, 1 = kusur)
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEDEF = os.path.join(ROOT, "shop", "src", "yonet.js")
NODE = shutil.which("node")
FAILS = []

# Aynaya TASINAN agac: `--yonet-cerez` kolunun GERCEKTEN dokundugu her sey.
# (kabul.js modul basinda kok secenekler.js'i require eder ve shop/config.json okur;
#  yonet.js -> semalar.js -> jenerator/urunler/*.json, konfigur.js -> kok konfigur.js;
#  C17 iddialari tools/yazdir.py KAYNAGINI okur.)
# ⚠️ Bu kume EKSIK KALIRSA taban kosumu KIRMIZI yanar ve harness DURUR — sessizce
# "olctum" demez. Yani liste bayatlarsa davranis fail-closed'dur.
AYNA_DIZIN = [
    os.path.join("shop", "src"),
    os.path.join("shop", "test"),
    os.path.join("jenerator", "urunler"),
]
AYNA_DOSYA = [
    os.path.join("shop", "config.json"),
    "secenekler.js",
    "konfigur.js",
    os.path.join("tools", "yazdir.py"),
]
# Aynaya girmeyen artefaktlar: yerel sir dosyalari (.dev.vars) ve turetilmis agaclar.
KOPYA_HARIC = shutil.ignore_patterns(".*", "node_modules", "__pycache__")


def check(etiket, kosul, detay=""):
    print("  [%s] %s%s" % ("PASS" if kosul else "FAIL", etiket,
                           ("  -> " + detay) if detay else ""))
    if not kosul:
        FAILS.append(etiket)
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ------------------------------------------------------------------ mutantlar
# (kod, aciklama, [(bulunacak, yerine), ...], beklenen_kirmizi_iddia_kodlari)
# beklenen kod listesi BOS ise: KONTROL mutanti -> YESIL kalmali.

M1 = ("M1", "?anahtar= sorgu parametresi yolu GERI GELDI (isin bas sebebi)", [(
    """function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {""",
    """function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  if (sabitEsit(url.searchParams.get("anahtar") || "", env.YONET_ANAHTAR)) { return true; }
  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {""")],
      ["C1", "C16a", "C16b"])

M2 = ("M2", "sabitEsit FAIL-OPEN'a dondu (String(a || \"\") — bos girdide true)", [(
    """export function sabitEsit(a, b) {
  if (typeof a !== "string" || typeof b !== "string") { return false; }
  if (a.length === 0 || b.length === 0) { return false; }
  if (a.length !== b.length) { return false; }""",
    """export function sabitEsit(a, b) {
  a = String(a || "");
  b = String(b || "");
  if (a.length !== b.length) { return false; }""")],
      ["C21a", "C21b", "C21c"])

# yonet()'in secret kapisini POST dagitiminin ARKASINA alir.
_SIRA_TAKAS = (
    """export async function yonet(request, env, url, ctx, altYol, telegram) {
  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;
  if (altYol === "/" && m === "POST") { return girisYap(request, url, env); }""",
    """export async function yonet(request, env, url, ctx, altYol, telegram) {
  const m = request.method;
  if (altYol === "/" && m === "POST") { return girisYap(request, url, env); }
  if (!env.YONET_ANAHTAR) { return yon404(); }""")
# girisYap'in KENDI secret kapisini siler.
_ICKAPI_SIL = (
    """  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();""",
    """  const simdi = Date.now();""")

M3 = ("M3", "secret kapisi giris POST'unun ARKASINA alindi + girisYap'in kendi kapisi silindi",
      [_SIRA_TAKAS, _ICKAPI_SIL], ["C15", "C22a"])

M4 = ("M4", "girisEkrani'nda ikame FONKSIYONU yerine ikame DIZESI ($` enjeksiyonu)", [(
    """GIRIS_HTML.replace("__EYLEM__", () => yol)""",
    """GIRIS_HTML.replace("__EYLEM__", yol)""")],
      ["C20"])

M5 = ("M5", "giris HIZ SINIRI kaldirildi (kaba kuvvet serbest)", [(
    """  return girisSayac.adet >= GIRIS_TAVAN;
}""",
    """  return false;
}""")],
      ["C18a", "C18b"])

M6 = ("M6", "giris GOVDE UST SINIRI kaldirildi (sinirsiz ayristirma)", [(
    """  const bildirilen = parseInt(request.headers.get("Content-Length") || "", 10);
  if (Number.isFinite(bildirilen) && bildirilen > GIRIS_GOVDE_SINIRI) { return null; }
  if (!request.body) { return ""; }""",
    """  if (!request.body) { return ""; }"""),
    ("""    if (toplam > GIRIS_GOVDE_SINIRI) { try { await okuyucu.cancel(); } catch (e) {} return null; }
""", "")],
      ["C19b"])

M7 = ("M7", "cerez ADI tam esitligi -> naive includes (yakin-iska yetki alir)", [(
    """    if (parca.slice(0, esit).trim() !== CEREZ_ADI) { continue; }""",
    """    if (!parca.includes(CEREZ_ADI)) { continue; }""")],
      ["C5a"])

M8 = ("M8", "Set-Cookie'den HttpOnly dusuruldu (XSS oturum cerezini calabilir)", [(
    """const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Strict; Path=/";""",
    """const CEREZ_BAYRAK = "Secure; SameSite=Strict; Path=/";""")],
      ["C10a", "C12c"])

M9 = ("M9", "SameSite=Strict -> Lax (capraz-site gezinmede cerez gider)", [(
    """const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Strict; Path=/";""",
    """const CEREZ_BAYRAK = "HttpOnly; Secure; SameSite=Lax; Path=/";""")],
      ["C10c", "C12e"])

K1 = ("K1", "KONTROL: sabitEsit'te yerel degisken adi degisti (davranis AYNI)", [(
    """  let fark = 0;
  for (let i = 0; i < a.length; i++) { fark |= a.charCodeAt(i) ^ b.charCodeAt(i); }
  return fark === 0;""",
    """  let farkBiti = 0;
  for (let i = 0; i < a.length; i++) { farkBiti |= a.charCodeAt(i) ^ b.charCodeAt(i); }
  return farkBiti === 0;""")],
      [])

K2 = ("K2", "KONTROL: girisYap'a yorum satiri eklendi (davranis AYNI)", [(
    """  if (!env.YONET_ANAHTAR) { return yon404(); }
  const simdi = Date.now();""",
    """  if (!env.YONET_ANAHTAR) { return yon404(); }
  // kontrol mutanti: yalnizca yorum — davranis degismez.
  const simdi = Date.now();""")],
      [])

K3 = ("K3", "KONTROL: anahtarGecerli'de baslik/cerez kontrol SIRASI takas edildi", [(
    """  if (sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR)) {
    return true;
  }
  return sabitEsit(yonetCereziOku(request), env.YONET_ANAHTAR);""",
    """  if (sabitEsit(yonetCereziOku(request), env.YONET_ANAHTAR)) { return true; }
  return sabitEsit(request.headers.get("X-Yonet-Anahtar") || "", env.YONET_ANAHTAR);""")],
      [])

# ESKIDEN K4 (beyan edilmis SURVIVOR, YESIL beklentili). Iddia ikiye ayrilinca (C22a/C22b)
# bu katman TEK BASINA olculur oldu -> artik KIRMIZI beklentilidir. C22b'yi BEKLEMEZ:
# yonet()'in ust kapisi bu mutantta yerinde durdugu icin GET / hala 404 doner (dogru).
M10 = ("M10", "YALNIZ girisYap'in kendi secret kapisi silindi (savunma derinliginin IC katmani)",
       [_ICKAPI_SIL], ["C22a"])

MUTANTLAR = [M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, K1, K2, K3]


# ------------------------------------------------------------------ ayna
def ayna_kur(hedef_kok):
    """<hedef_kok> = kabul testinin ihtiyac duydugu agacin TAM KOPYASI.
    KAYNAGA GIDEN SYMLINK YOKTUR (symlinks=False + follow_symlinks=True)."""
    for gorece in AYNA_DIZIN:
        shutil.copytree(os.path.join(ROOT, gorece), os.path.join(hedef_kok, gorece),
                        symlinks=False, ignore=KOPYA_HARIC, ignore_dangling_symlinks=True)
    for gorece in AYNA_DOSYA:
        hedef = os.path.join(hedef_kok, gorece)
        os.makedirs(os.path.dirname(hedef), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, gorece), hedef, follow_symlinks=True)


def symlinkleri_bul(kok):
    bulunan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        for ad in altlar + dosyalar:
            y = os.path.join(dizin, ad)
            if os.path.islink(y):
                bulunan.append(os.path.relpath(y, kok))
    return bulunan


def mutasyonla(pristine, degisimler, kod):
    """Mutasyonu metne uygular. Dayanak bulunamazsa HARNESS BAYATTIR -> gurultulu duser
    (sessizce 'olctum' demek, hic olcmemekten kotudur)."""
    metin = pristine
    for eski, yeni in degisimler:
        if eski not in metin:
            raise SystemExit(
                "HARNESS BAYAT (%s): shop/src/yonet.js icinde mutasyon dayanagi "
                "bulunamadi:\n%r\n(kod degismis olabilir — mutasyonu guncelle; yoksa bu "
                "harness HICBIR SEY olcmuyor demektir)" % (kod, eski[:200]))
        yeni_metin = metin.replace(eski, yeni, 1)
        if yeni_metin == metin:
            raise SystemExit("HARNESS BAYAT (%s): mutasyon metni DEGISTIRMIYOR" % kod)
        metin = yeni_metin
    return metin


IDDIA_RE = re.compile(r"^IDDIA SAYISI:\s*(\d+)\s*$", re.M)
KIRMIZI_RE = re.compile(r"❌ KALDI\s+(\S+)")


def kos(ayna, metin):
    """Ayna icindeki yonet.js'i <metin> ile yazar ve alt kumeyi kosar.
    Doner: (cikis_kodu, iddia_sayisi|None, kirmizi_kodlar, kirmizi_satirlar, cikti_kuyrugu)"""
    with open(os.path.join(ayna, "shop", "src", "yonet.js"), "w", encoding="utf-8") as f:
        f.write(metin)
    r = subprocess.run([NODE, os.path.join(ayna, "shop", "test", "kabul.js"), "--yonet-cerez"],
                       cwd=ayna, capture_output=True, text=True, timeout=300)
    cikti = (r.stdout or "") + (r.stderr or "")
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    satirlar = [s.strip() for s in cikti.splitlines() if "❌ KALDI" in s]
    kodlar = KIRMIZI_RE.findall(cikti)
    return r.returncode, iddia, kodlar, satirlar, cikti[-1600:]


def main():
    print("YONET ANAHTAR/CEREZ MUTASYON HARNESS'I — `node shop/test/kabul.js --yonet-cerez`")
    if NODE is None:
        raise SystemExit("node bulunamadi (PATH) — bu harness node ister.")
    if not os.path.isfile(HEDEF):
        raise SystemExit("shop/src/yonet.js yok: %s" % HEDEF)

    canli_once = sha(HEDEF)
    with open(HEDEF, encoding="utf-8") as f:
        pristine = f.read()
    print("  hedef: shop/src/yonet.js  sha256=%s…  (%d bayt)"
          % (canli_once[:16], len(pristine.encode("utf-8"))))

    ayna = tempfile.mkdtemp(prefix="yonet-cerez-mutasyon-")
    try:
        ayna_kur(ayna)

        # --- 0) AYNA DOKUNULMAZLIGI: kaynaga giden fiziksel yol var mi? -------------
        print("\n0) AYNA DOKUNULMAZLIGI")
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))
        ayna_hedef = os.path.join(ayna, "shop", "src", "yonet.js")
        check("aynadaki yonet.js gecici dizinde (realpath kaynak agacin DISINDA)",
              os.path.realpath(ayna_hedef).startswith(os.path.realpath(ayna)) and
              os.path.realpath(ayna_hedef) != os.path.realpath(HEDEF),
              os.path.realpath(ayna_hedef))

        # --- 1) TABAN: mutasyonsuz ayna YESIL olmali; iddia sayisi BURADA olculur ---
        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, _t_kod, t_satir, t_kuyruk = kos(ayna, pristine)
        taban_ok = check("taban kosumu YESIL (cikis 0, kirmizi 0)",
                         t_rc == 0 and not t_satir,
                         "cikis=%d kirmizi=%d %s" % (t_rc, len(t_satir),
                                                     t_satir[0][:90] if t_satir else ""))
        if not taban_ok:
            print("\n  --- taban kosumunun ciktisi (son 1600 karakter) ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: ya ayna agaci EKSIK (AYNA_DIZIN/AYNA_DOSYA "
                  "guncellenmeli) ya da alt kume gercekten bozuk. Mutant kosumlari "
                  "ANLAMSIZ olurdu — durduruluyor.")
            return 1
        check("taban IDDIA SAYISI okunabildi (SONUC satiri basildi)",
              t_iddia is not None, "iddia=%s" % t_iddia)
        if t_iddia is None:
            return 1
        print("   TABAN IDDIA SAYISI = %d  (capa DEGIL: kosumda olculdu; mutantlar bu "
              "sayiyla kiyaslanir)" % t_iddia)
        check("taban kosumundan sonra canli yonet.js DEGISMEDI (sha256)",
              sha(HEDEF) == canli_once)

        # --- 2) MUTASYON BATARYASI -------------------------------------------------
        print("\n2) MUTASYON BATARYASI — %d kosum (%d kirmizi-beklentili, %d kontrol)"
              % (len(MUTANTLAR), sum(1 for m in MUTANTLAR if m[3]),
                 sum(1 for m in MUTANTLAR if not m[3])))
        matris = []
        for kod, aciklama, degisimler, beklenen in MUTANTLAR:
            metin = mutasyonla(pristine, degisimler, kod)
            rc, iddia, kirmizi_kod, kirmizi, kuyruk = kos(ayna, metin)
            sayi_ok = (iddia == t_iddia)
            if beklenen:
                eksik = [b for b in beklenen if b not in kirmizi_kod]
                gecti = sayi_ok and rc == 1 and bool(kirmizi) and not eksik
                detay = ("cikis=%d iddia=%s/%d kirmizi=%d isaret=%s"
                         % (rc, iddia, t_iddia, len(kirmizi),
                            "TAM" if not eksik else ("EKSIK:" + ",".join(eksik))))
                if not sayi_ok:
                    detay += ("  ⚠️ IDDIA SAYISI TUTMUYOR -> mutant testi COKERTMIS "
                              "olabilir; bu 'kirmizi' OLCUM DEGIL")
                beklenti = "KIRMIZI"
            else:
                gecti = sayi_ok and rc == 0 and not kirmizi
                detay = ("cikis=%d iddia=%s/%d kirmizi=%d %s"
                         % (rc, iddia, t_iddia, len(kirmizi),
                            kirmizi[0][:90] if kirmizi else ""))
                beklenti = "YESIL"
            check("%s [%s] %s" % (kod, beklenti, aciklama), gecti, detay)
            if not gecti:
                print("       --- %s ciktisinin kuyrugu ---\n%s" % (kod, kuyruk))
            matris.append((kod, beklenti, rc, iddia, len(kirmizi),
                           ",".join(sorted(set(kirmizi_kod)))[:56] or "-"))
            if sha(HEDEF) != canli_once:
                check("KAYNAK AGAC DEGISTI (ayna kacagi!) [%s]" % kod, False)

        print("\n   --- MUTASYON MATRISI ---")
        print("   %-4s %-9s %-6s %-10s %-8s %s" % ("kod", "beklenti", "cikis", "iddia",
                                                   "kirmizi", "kirmizi iddia kodlari"))
        for kod, beklenti, rc, iddia, adet, kodlar in matris:
            print("   %-4s %-9s %-6d %-10s %-8d %s"
                  % (kod, beklenti, rc, "%s/%d" % (iddia, t_iddia), adet, kodlar))
    finally:
        shutil.rmtree(ayna, ignore_errors=True)

    # --- 3) SON DOKUNULMAZLIK ------------------------------------------------------
    print("\n3) KAYNAK DOKUNULMAZLIGI (sha256, harness sonu)")
    canli_sonra = sha(HEDEF)
    check("shop/src/yonet.js sha256 BASTAKIYLE AYNI (mutant diskte kalmadi)",
          canli_sonra == canli_once,
          "once=%s… sonra=%s…" % (canli_once[:16], canli_sonra[:16]))

    print("\n" + ("SONUC: TUM MUTANTLAR YAKALANDI, KONTROLLER YESIL ✅"
                 if not FAILS else
                 "SONUC: %d KUSUR ❌\n  - %s" % (len(FAILS), "\n  - ".join(FAILS))))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())

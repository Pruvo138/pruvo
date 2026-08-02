#!/usr/bin/env python3
"""
wa-yetki-mutasyon.py — `/api/shop/yonet/wa-siparis` YETKI YUZEYININ iki ekseni icin
CIFT YONLU mutasyon surucusu.

NEDEN VAR: `shop/test/wa-siparis.mjs` bir turda 158 iddiayla YESIL yanarken asagidaki
IKI eksen HIC olculmuyordu — yani "yesil" o eksenlerde bir sey soylemiyordu:

  EKSEN 1 (panel koku).  Dalin eski iddiasi `Ege anahtari GET /yonet -> 404` idi. main
    yetkisiz koku 200 SIFRE KUTUSU yapinca bu iddia BAYATLADI. Bayat iddiayi "200 bekle"
    diye gecistirmek nobetciyi OLDURURDU: asil niyet "Ege anahtari anonimden FAZLA hicbir
    sey almiyor"dur. Yeni iddia bunu UC eksende olcer (ayni sinif · yetkili veri yok ·
    yanit sifre kutusu, panel DEGIL).

  EKSEN 2 (ozellik-kapali yazma yolu).  `if (!env.YONET_ANAHTAR) return yon404()` kapisi
    `/wa-siparis` blogunun ONUNDE mi ARKASINDA mi durdugu OLCULMUYORDU: kapiyi arkaya
    tasiyan mutant iki yerlesimde de 157/1 veriyordu (fark yalnizca bayat iddiadan
    geliyordu). Ayarlanmamis bir secret'in arkasinda ACIK kalan yazma ucu bu depodaki
    sessiz-hata sinifidir -> kapi ONDE, fail-closed.

🔴 MUTANT CANLI DOSYAYA ASLA UYGULANMAZ. Kaynak agac gecici bir AYNAYA kopyalanir,
mutant AYNADA calisir; koşum sonunda canli dosyalarin sha256'si basta/sonda karsilastirilir
(bir kesinti bile canliya mutant birakmaz).

CI'DA KOSMAZ — gelistirici/curutucu aracidir (kardesi: tools/yonet-cerez-mutasyon.py).
Elle: python3 tools/wa-yetki-mutasyon.py
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which("node")
KAYNAK = "shop/src/yonet.js"
TEST = "shop/test/wa-siparis.mjs"
KOPYA_HARIC = shutil.ignore_patterns(".*", "node_modules", "__pycache__")

# Aynaya tasinacak asgari kume: test `../../secenekler.js`'i require ediyor, `shop/src/
# semalar.js` de `../../jenerator/urunler/*.json` semalarini import ediyor. Eksik birakmak
# testi COKERTIR ve cokme "kirmizi" ile karisir -> asgari kume TAM tutulur.
AYNA_DIZIN = ["shop", "jenerator"]
AYNA_DOSYA = ["secenekler.js", "konfigur.js"]


def sha256(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ayna_kur():
    ayna = tempfile.mkdtemp(prefix="wa-yetki-mutasyon-")
    for d in AYNA_DIZIN:
        shutil.copytree(os.path.join(ROOT, d), os.path.join(ayna, d), ignore=KOPYA_HARIC)
    for f in AYNA_DOSYA:
        kaynak = os.path.join(ROOT, f)
        if os.path.exists(kaynak):
            shutil.copy2(kaynak, os.path.join(ayna, f), follow_symlinks=True)
    return ayna


def uygula(ayna, degisimler):
    """degisimler: [(once, sonra)]. Her capa TAM 1 kez esleşmeli; degilse OLCULMEMIS."""
    yol = os.path.join(ayna, KAYNAK)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    for once, sonra in degisimler:
        n = metin.count(once)
        if n != 1:
            return "BAYAT CAPA: capa %d kez esleşti (1 olmali): %r" % (n, once[:70])
        metin = metin.replace(once, sonra)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    return None


def kos(ayna):
    """Ayna testini kostur; (gecen, kalan, [kirmizi iddia adlari], cikis_kodu) dondur."""
    p = subprocess.run([NODE, os.path.join(ayna, TEST)],
                       capture_output=True, text=True, cwd=ayna)
    cikti = (p.stdout or "") + (p.stderr or "")
    # 🔴 IKI BOSLUKLU onek SART: ozet satiri da "❌ KIRMIZI — gecen: .." diye basiyor ve
    # gevsek bir desen onu SAHTE bir iddia gibi sayardi (olculdu: her mutantta fazladan
    # "KIRMIZI" adli kirmizi cikiyordu ve TEK-EKSEN yargisini yanlis yere bozuyordu).
    kirmizilar = re.findall(r"^  ❌ (.+?)(?: — |$)", cikti, re.M)
    m = re.search(r"gecen: (\d+), kalan: (\d+)", cikti)
    if not m:
        return (None, None, kirmizilar, p.returncode, cikti)
    return (int(m.group(1)), int(m.group(2)), kirmizilar, p.returncode, cikti)


# ---------------------------------------------------------------- MUTANTLAR
# (kod, aciklama, beklenti, degisimler, hedef_onek)
#
# beklenti degerleri:
#   "KIRMIZI-TEK"    : kirmizilarin HEPSI hedef_onek ile baslamali. Eksenin TEK BASINA
#                      kirmizi yakilabildiginin kaniti — [[beyan-edilmis-survivor]]:
#                      zincirden gecen bir iddia katmanlarin VEYA'sini olcer; bir katman
#                      ancak YALNIZ BASINA kirmizi yakilabiliyorsa ayri bir iddiadir.
#   "KIRMIZI-ICINDE" : hedef eksen kirmizi olmali, BASKA nobetcilerin de yanmasi MESRU
#                      (savunma derinligi). Tek basina kanit SAYILMAZ; esi olan
#                      "KIRMIZI-TEK" mutantiyla birlikte anlam kazanir.
#   "YESIL"          : kontrol mutanti (davranis degismedi) — kapi METNI degil DAVRANISI
#                      olculuyor mu?

WA_BLOK_ONCE = """  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;"""
WA_BLOK_SONRA = """  const m = request.method;"""
GIRIS_SATIRI = """  if (altYol === "/" && m === "POST") { return girisYap(request, url, env); }"""

MUTANTLAR = [
    ("M1", "EKSEN 1 (genis): Ege anahtari `anahtarGecerli`yi TRUE yapar — en-az-yetki "
           "TAMAMEN coker (Ege /liste, /durum, /kargo ve panelin kendisini gorur)",
     "KIRMIZI-ICINDE",
     [("""function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }""",
       """function anahtarGecerli(request, url, env) {
  if (!env.YONET_ANAHTAR) { return false; }
  if (egeAnahtarGecerli(request, env)) { return true; }""")],
     "KOK:"),

    # M1'in genis mutant olmasi bir eksiklik degil ama KANIT da degil: mevcut
    # "Ege anahtari /X ucunu ACMAZ" nobetcileri de yaniyor, yani M1 katmanlarin
    # VEYA'sini olcuyor. Asagidaki mutant PANEL KOKUNU IZOLE eder: yalnizca kok GET
    # kolunda Ege anahtarina panel verilir; /liste, /durum, /kargo, /stl-liste
    # DOKUNULMADAN kalir -> yeni iddia TEK BASINA kirmizi yakmak ZORUNDA.
    ("M1b", "EKSEN 1 AYIRT EDICISI (izole): yalniz kok GET kolunda Ege anahtarina "
            "SIFRE KUTUSU yerine PANEL dondurulur; diger uclar DOKUNULMAZ",
     "KIRMIZI-TEK",
     [("""    return (altYol === "/" && m === "GET") ? girisEkrani(url) : yon404();""",
       """    return (altYol === "/" && m === "GET")
      ? (egeAnahtarGecerli(request, env) ? sayfa() : girisEkrani(url))
      : yon404();""")],
     "KOK:"),

    ("M2", "EKSEN 2 AYIRT EDICISI: ozellik-kapali kapisi `/wa-siparis` blogunun ARKASINA "
           "tasinir (YONET_ANAHTAR yokken Ege siparis YAZABILIR)",
     "KIRMIZI-TEK",
     [(WA_BLOK_ONCE, WA_BLOK_SONRA),
      (GIRIS_SATIRI, """  if (!env.YONET_ANAHTAR) { return yon404(); }\n""" + GIRIS_SATIRI)],
     "OZELLIK KAPALI:"),

    ("M3", "KONTROL: kapi kosulu AYNI anlamda baska sozdiziminde "
           "(bos dize zaten falsy) — kapi METNI degil DAVRANISI mi olculuyor?",
     "YESIL",
     [("""  if (!env.YONET_ANAHTAR) { return yon404(); }
  const m = request.method;""",
       """  if (!env.YONET_ANAHTAR || env.YONET_ANAHTAR === "") { return yon404(); }
  const m = request.method;""")],
     None),

    ("M4", "KONTROL: De Morgan — `!A && !B` yerine `!(A || B)` (davranis AYNI)",
     "YESIL",
     [("""    if (!anahtarGecerli(request, url, env) && !egeAnahtarGecerli(request, env)) {""",
       """    if (!(anahtarGecerli(request, url, env) || egeAnahtarGecerli(request, env))) {""")],
     None),
]


def main():
    if not NODE:
        sys.exit("node bulunamadi — bu surucu node gerektirir (YESIL degil, OLCULEMEDI).")

    canli = {y: sha256(os.path.join(ROOT, y)) for y in (KAYNAK, TEST)}

    print("=== WA YETKI — CIFT YONLU MUTASYON (mutant AYNAYA uygulanir, CANLIYA ASLA)")

    ayna = ayna_kur()
    try:
        taban = kos(ayna)
        if taban[1] != 0 or taban[0] is None:
            print("  TABAN KIRMIZI — mutasyon olcumu anlamsiz. kirmizi:", taban[2])
            return 1
        print("  OK   M00 [YESIL] MUTASYONSUZ KONTROL -> gecen %d, kalan 0 (harness saglam)"
              % taban[0])
    finally:
        shutil.rmtree(ayna, ignore_errors=True)

    basarisiz = 0
    for kod, aciklama, beklenti, degisimler, onek in MUTANTLAR:
        ayna = ayna_kur()
        try:
            hata = uygula(ayna, degisimler)
            if hata:
                print("  !!   %s OLCULEMEDI — %s" % (kod, hata))
                basarisiz += 1
                continue
            gecen, kalan, kirmizilar, _, cikti = kos(ayna)
            if gecen is None:
                print("  !!   %s OLCULEMEDI — test ozeti okunamadi (cokme?)" % kod)
                print("       " + cikti.strip().splitlines()[-1][:120] if cikti.strip() else "")
                basarisiz += 1
                continue
            gercek = "KIRMIZI" if kalan > 0 else "YESIL"
            hedefte = [a for a in kirmizilar if onek and a.startswith(onek)]
            disari = [a for a in kirmizilar if not (onek and a.startswith(onek))]
            if beklenti == "YESIL":
                tutdu = gercek == "YESIL"
                not_satiri = None
            elif beklenti == "KIRMIZI-TEK":
                tutdu = bool(hedefte) and not disari
                not_satiri = ("TEK-EKSEN: %s — hedef eksende %d kirmizi, eksen disi %d"
                              % ("EVET" if tutdu else "HAYIR", len(hedefte), len(disari)))
            else:  # KIRMIZI-ICINDE
                tutdu = bool(hedefte)
                not_satiri = ("EKSEN ICINDE: %s — hedef eksende %d kirmizi, "
                              "ayrica %d baska nobetci de yandi (mesru: savunma derinligi)"
                              % ("EVET" if tutdu else "HAYIR", len(hedefte), len(disari)))
            damga = "OK  " if tutdu else "HATA"
            if not tutdu:
                basarisiz += 1
            print("  %s %s [%s] -> %s (gecen %d, kalan %d) | %s"
                  % (damga, kod, beklenti, gercek, gecen, kalan, aciklama))
            if not_satiri:
                print("        " + not_satiri)
                for a in kirmizilar:
                    print("        KALDI " + ("[HEDEF] " if onek and a.startswith(onek)
                                              else "[DISARI] ") + a)
        finally:
            shutil.rmtree(ayna, ignore_errors=True)

    print("\n  CANLI DOSYA BUTUNLUGU (sha256, %d dosya): %s"
          % (len(canli),
             "DEGISMEDI ✔" if all(sha256(os.path.join(ROOT, y)) == h
                                  for y, h in canli.items()) else "DEGISTI ‼"))
    sonuc = "TUTTU ✔" if basarisiz == 0 else ("%d MUTANT BEKLENTIYI TUTMADI ‼" % basarisiz)
    print("MUTASYON SONUCU: %d/%d %s" % (len(MUTANTLAR) - basarisiz, len(MUTANTLAR), sonuc))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())

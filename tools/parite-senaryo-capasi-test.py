#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SENARYO CAPASI KAPISI — "yerelde YESIL / CI'da KIRMIZI" sinifinin nobetcisi.

KOK OLGU (7 Eyl 2026, OLCULDU — defter K196'nin icrasi):
`tools/parite-fikstur-test.js` senaryo kumesini ORTAMA gore kurar. Kardes bot deposu
(`/Users/okan/dev/pruvo-bot/worker/src/index.js`) YOKSA sekiz Ege senaryosu ve UC MARKA
senaryosu (SM1-SM3) HIC KAYDOLMAZ: yerelde 32 senaryo, CI'da 21 (olculdu — CI logu ve
`PARITE_BOT` ile yerelde birebir yeniden uretildi: "21 senaryo", "IDDIA: 178 gecti").
Iki ayri kusur ayni koku paylasiyordu:

  1. FIKSTUR: menzil DISI bir senaryo indeksi istendiginde hicbir senaryo kosmuyor,
     "IDDIA: 0 gecti | 0 KALDI" basiliyor ve CIKIS 0 (YESIL) veriliyordu. Yani
     "senaryo YOK" ile "senaryo GECTI" AYNI cikis kodunu uretiyordu (olculdu:
     `node tools/parite-fikstur-test.js 999` -> rc=0).
  2. BATARYA (`parite-fikstur-olcum-ortami-mutasyon.py`): senaryoyu POZISYONLA
     capaliyordu (SM1="29"). CI'da 29 menzil disi kaldigi icin 6 mutant "COKME" sayildi
     ve `hijyen-a3` CI'da KIRMIZI yandi — ayni agac yerelde 8/8 YESIL. Teshis edilemeyen
     bir sinif: KIRMIZI, koda degil ORTAMA bagliydi.

ONARIM: (1) fikstur menzil disi indekse `CIKIS_OLCULEMEDI` (3) verir ve her kosumda
makine-okunur `OLCUM-ORTAMI:` satiri basar; `--senaryolar` ile kayit defterini yayinlar.
(2) batarya capayi ADIN ILK JETONUYLA (TAM ESITLIK) cozer ve UC KOVAYA ayirir:
VAR / ATLANDI (on-kosul beyan edilmis + ortam yok) / KAYIP (KIRMIZI).

BU KAPI ONARIMIN FIILEN KORUDUGUNU OLCER. Her bacak MUTANTLA kanitlanir: kol sokulunce
eski sessiz-yesil (ya da eski kirmizi) GERI DONER.

NASIL: mutant DAIMA KOPYAYA uygulanir. ROOT'un tamami gecici bir dizine SYMLINK'lenir,
mutasyona ugrayan dosyalar gercek kopyayla degistirilir ve olcum O AYNADAN kosulur.
Gercek ev yoluna `rm -rf`/`rmtree`/`unlink` YOKTUR (silme yalnizca mkdtemp altinda).

CI-ALT-KUME: (bayraksiz)
Calistir:  python3 tools/parite-senaryo-capasi-test.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
FIKSTUR = "parite-fikstur-test.js"
BATARYA = "parite-fikstur-olcum-ortami-mutasyon.py"

# Ege/marka senaryolarini KAYDETTIRMEYEN ortam: var olmayan bir bot kaynagi. CI'nin
# hali BUDUR (kardes depo checkout edilmez); yerelde de birebir ayni kumeyi uretir.
YOK_BOT = os.path.join(tempfile.gettempdir(), "parite-capasi-yok-boyle-bir-bot.js")

gecen = 0
kalan = 0


def ONA(kosul, ad, kanit=""):
    global gecen, kalan
    if kosul:
        gecen += 1
        print("   ✅ " + ad)
    else:
        kalan += 1
        print("   ❌ " + ad + ("\n      KANIT: " + str(kanit)[:600] if kanit else ""))


def ayna_kur(tmp, mutasyonlar):
    """ROOT'un aynasi: tools/ gercek dizin, `.js` GERCEK KOPYA, digerleri symlink.

    🔴 `.js` SYMLINK OLAMAZ: node `require`'i symlink'i cozer ve aynadaki fikstur gercek
    agactaki komsularini yuklerdi -> mutant HIC yuklenmez, batarya "olcuyor gibi yapip"
    hicbir sey olcmezdi ([[mutant-canli-govdede-yasamaz]]).
    """
    kok = os.path.join(tmp, "kok")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git"):
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(kok, ad))
    for ad in os.listdir(TOOLS):
        kaynak = os.path.join(TOOLS, ad)
        hedef = os.path.join(kok, "tools", ad)
        if ad.endswith(".js") and os.path.isfile(kaynak):
            shutil.copy2(kaynak, hedef)
        else:
            os.symlink(kaynak, hedef)
    # 🔴 AYNI DOSYAYA IKI MUTASYON BIRIKMELI (olculdu, bu dosyanin ILK surumunde kusurdu):
    # her mutasyon GERCEK kaynaktan yeniden okunup yazilirsa ikincisi birincisini SILER.
    # C-MUTANT bacagi tam boyle "gecti": capa silme mutasyonu ezildigi icin batarya
    # normal kosup rc=0 verdi ve iddia YANLIS SEBEPLE yesil yandi
    # ([[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]). Govdeler dosya
    # basina BIRIKTIRILIR ve her capa KENDI SIRASINDA tam bir kez eslesmelidir.
    govdeler = {}
    for dosya, eski, yeni in mutasyonlar:
        govde = govdeler.get(dosya)
        if govde is None:
            govde = open(os.path.join(TOOLS, dosya), encoding="utf-8").read()
        # 🔴 CAPA TAM BIR KEZ ESLESMELI: kaymissa mutant UYGULANMAZ ve kosum "yesil"
        # gorunur — bu bir olcum degil, kor noktadir.
        if govde.count(eski) != 1:
            raise AssertionError("MUTANT CAPASI KAYDI: %s icinde %d kez esletti (1 bekleniyor):"
                                 " %r" % (dosya, govde.count(eski), eski[:80]))
        govdeler[dosya] = govde.replace(eski, yeni, 1)
    for dosya, govde in govdeler.items():
        hedef = os.path.join(kok, "tools", dosya)
        os.unlink(hedef)
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(govde)
    return kok


def kos(argv, mutasyonlar=(), bot_yok=True, sure=1800):
    tmp = tempfile.mkdtemp(prefix="parite-senaryo-capasi-")
    try:
        kok = ayna_kur(tmp, list(mutasyonlar))
        env = dict(os.environ)
        if bot_yok:
            env["PARITE_BOT"] = YOK_BOT
        tam = [argv[0], os.path.join(kok, "tools", argv[1])] + list(argv[2:])
        r = subprocess.run(tam, capture_output=True, text=True, cwd=kok,
                           env=env, timeout=sure)
        return r.returncode, r.stdout + r.stderr
    finally:
        # SILME MENZILI: yalnizca mkdtemp altindaki gecici agac.
        assert tmp.startswith(tempfile.gettempdir())
        shutil.rmtree(tmp, ignore_errors=True)


def iddia_toplami(cikti):
    m = re.search(r"^IDDIA: (\d+) gecti \| (\d+) KALDI", cikti, re.M)
    return (int(m.group(1)) + int(m.group(2))) if m else None


# ── MUTANT CAPALARI (tek kaynak: gercek govde) ─────────────────────────────────
M_MENZIL_KAPISI_SOK = (
    FIKSTUR,
    "  if (Number.isFinite(yalniz) && (yalniz < 0 || yalniz >= senaryolar.length)) {",
    "  if (false && Number.isFinite(yalniz) && (yalniz < 0 || yalniz >= senaryolar.length)) {")
K_DAVRANISSIZ = (
    FIKSTUR,
    "  if (!Number.isFinite(yalniz)) birimOlc();",
    "  if (!Number.isFinite(yalniz)) birimOlc();  // davranissiz yorum")
M_POZISYONEL_CAPA = (
    BATARYA,
    '    for m in re.finditer(r"^SENARYO: (\\d+)\\t(\\S+)", cikti, re.M):\n'
    "        defter[m.group(2)] = m.group(1)",
    '    defter = {"SM1": "29", "S8": "8"}')
M_IKI_KOVA = (
    BATARYA,
    '    if (CAPA_ONKOSULU.get(jeton) == "EGE" and bot_yolu\n'
    "            and not os.path.exists(bot_yolu)):",
    "    if True:")
M_CAPA_SIL = (BATARYA, 'S8 = "S8"    # S8 (K2) KIRMIZI + uc SUSUYOR',
              'S8 = "S8-BOYLE-BIR-SENARYO-YOK"')


def main():
    print("═" * 78)
    print("SENARYO CAPASI KAPISI — ortam kumeyi degistirince kapi SESSIZ KALMIYOR mu?")
    print("═" * 78)

    print("\n▶ A) FIKSTUR MENZIL KAPISI — menzil disi indeks YESIL veremez")
    rc, cikti = kos(["node", FIKSTUR, "29"])
    ortam = re.search(r"^OLCUM-ORTAMI: .*$", cikti, re.M)
    ONA(re.search(r"senaryo=21\b", ortam.group(0)) is not None if ortam else False,
        "ORTAM birebir CI kumesini uretti (senaryo=21, ege=YOK)", ortam and ortam.group(0))
    ONA(rc == 3, "menzil disi indeks -> cikis 3 (OLCULEMEDI), 0 DEGIL  [rc=%d]" % rc,
        cikti[-500:])
    ONA("MENZIL DISI" in cikti, "sebep ADIYLA yazili (MENZIL DISI)", cikti[-400:])
    ONA(iddia_toplami(cikti) is None,
        "'IDDIA: 0 gecti | 0 KALDI' SAHTE OZETI BASILMIYOR", cikti[-400:])

    print("\n▶ A-MUTANT) menzil kapisi SOKULDU -> eski SESSIZ YESIL geri gelmeli")
    rcm, ciktim = kos(["node", FIKSTUR, "29"], [M_MENZIL_KAPISI_SOK])
    ONA(rcm == 0 and iddia_toplami(ciktim) == 0,
        "kol sokulunce SAHTE YESIL DOGDU (rc=%d, olculen iddia=%s) — kol GERCEKTEN koruyor"
        % (rcm, iddia_toplami(ciktim)), ciktim[-400:])

    print("\n▶ A-KONTROL) davranissiz yazim -> hukum DEGISMEMELI")
    rck, _ = kos(["node", FIKSTUR, "29"], [K_DAVRANISSIZ])
    ONA(rck == 3, "davranissiz degisiklik kapiyi oynatmadi (rc=%d)" % rck)

    print("\n▶ B) BATARYA ADLA CAPALIYOR — CI ortaminda COKME URETMIYOR")
    rcb, ciktib = kos(["python3", BATARYA])
    ONA(rcb == 0, "batarya CI ortaminda cikis 0 (rc=%d)" % rcb, ciktib[-900:])
    ONA("COKME" not in ciktib, "hicbir mutant 'COKME' diye siniflanmadi", ciktib[-900:])
    ONA(re.search(r"⚪ 6/8 mutant BU ORTAMDA OLCULEMEDI", ciktib) is not None,
        "olculemeyen 6 mutant ADIYLA ve SAYIYLA raporlandi (yutulmadi)", ciktib[-900:])
    ONA(re.search(r"SONUC: YESIL .*2 mutant olculdu", ciktib) is not None,
        "olculen 2 mutant ('S8' kolu) gercekten kosuldu", ciktib[-600:])

    print("\n▶ B-MUTANT) capa POZISYONA geri alindi -> ESKI CI KIRMIZISI geri gelmeli")
    rcbm, ciktibm = kos(["python3", BATARYA], [M_POZISYONEL_CAPA])
    ONA(rcbm == 1 and "COKME" in ciktibm,
        "pozisyonel capa ile batarya yine KIRMIZI + COKME (rc=%d) — ad capasi kolu TASIYOR"
        % rcbm, ciktibm[-700:])

    print("\n▶ C) UCUNCU KOVA — ORTAM MAZUR GOSTERMEYEN kayip capa KIRMIZI yakar")
    rcc, ciktic = kos(["python3", BATARYA], [M_CAPA_SIL])
    ONA(rcc == 1, "her ortamda kaydolan bir capa yok olunca cikis 1 KIRMIZI (rc=%d)" % rcc,
        ciktic[-700:])
    ONA("CAPA DUSTU" in ciktic, "sebep ADIYLA: 'CAPA DUSTU'", ciktic[-700:])
    ONA("ATLANDI" not in ciktic.split("MUTASYON SONUCU")[-1].split("S8-BOYLE")[0]
        or "CAPA DUSTU" in ciktic,
        "kayip capa ATLANDI kovasina KACIRILMADI", ciktic[-700:])

    print("\n▶ C-MUTANT) uc kova IKIYE indirildi -> KIRMIZI kaybolmali")
    rccm, ciktim2 = kos(["python3", BATARYA], [M_CAPA_SIL, M_IKI_KOVA])
    ONA(rccm != 1,
        "iki kovaya inince KIRMIZI KAYBOLDU (rc=%d, taban rc=1) — ucuncu kova kolu TASIYOR"
        % rccm, ciktim2[-700:])
    ONA("CAPA DUSTU" not in ciktim2,
        "mutantta 'CAPA DUSTU' hukmu HIC BASILMIYOR (kol fiilen sokuldu)", ciktim2[-700:])

    print("\n" + "═" * 78)
    print("IDDIA: %d gecti | %d KALDI" % (gecen, kalan))
    if kalan:
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅ — ortam senaryo kumesini degistirdiginde kapi ne SESSIZ KALIR"
          " ne de kod kusuru diye YANLIS SUCLAR")
    return 0


if __name__ == "__main__":
    sys.exit(main())

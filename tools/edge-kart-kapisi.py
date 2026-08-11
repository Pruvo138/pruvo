#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/edge-kart-kapisi.py — EDGE KART ALAN KAPSAMI (sessiz fiyat/beyan sapmasi nobetcisi).

NEDEN VAR (OLCULDU, 1 Agu 2026 — bagimsiz curutucu bulgusu):
    index.html EDGE_KATALOG=true iken sepet paneli urun objesini `urunler.json`dan ALMAZ;
    `ozet.json` kartindan ya da edge Worker /katalog kartindan alir. `secenekler.js`
    satirOzeti sepet satirinin FIYATINI ve BEYANINI o urun objesinden okur. Karttan bir alan
    EKSIKSE panel o alani "yok" sayar ve SESSIZCE baska bir fiyat gosterir.

    Gercek vaka: `tur` alani (hazir ticari mal isareti) 31 Tem'de katalogda+D1'de dogdu,
    fiyat kuralina 1 Agu'da girdi, ama `kart_ozeti`ye EKLENMEDI. Olculen ayrisma —
      international-micron-99-antifouling-boya-20lt (bayat sepet satiri, ASA + "Diğer"):
      panel GOSTERIYOR 15.842.400 krs · Worker TAHSIL EDIYOR 8.610.000 krs
      fark 7.232.400 krs · 103 fiziksel urun toplaminda 53.270.280 krs
    Panel ayrica "Malzeme: ASA (+%60) · Renk: turuncu (özel, +%15)" yazip ayni sisik tutari
    WhatsApp mesajina koyuyordu. build.py kart_ozeti'nin KENDI YAZILI SOZLESMESI bunu zaten
    yasakliyordu ("sepet fiyatini etkileyecek bir alan ... BURAYA DA girmeli") — ihlali
    goren KAPI YOKTU. jenerator/test/vitrin-kabul.js test 8 iki taraf da alansiz oldugu icin
    YESIL kaliyordu (anchor-coupling).

OLCULEN EKSEN — ALAN LISTESI, `tur` LITERALI DEGIL:
    1. `secenekler.js` KAYNAGINDAN `urun.<alan>` okumalari CIKARILIR. Bu kume "sepet
       fiyatini/beyanini etkileyen alanlar"dir; elle yazilmaz, dolayisiyla YARIN EKLENEN
       bir alan da kendiliginden kapsama girer (mutant M-C bunu kanitlar).
    2. Her alan icin katalogda DEGER TASIYAN urun sayilir.
    3. Deger tasiyan alan, o urunlerin `kart_ozeti` kartinda BULUNMALI ve degeri BIREBIR
       ayni olmali. Tasiyan urun YOKSA alan MUAFTIR — ama muafiyet SAYIYLA raporlanir
       ("uyuyan risk"), sessizce gecmez.
    4. TEL EKSENI (12 Agu 2026): alan kartta VAR olmakla kalmaz — ornek kartlar ozet.json
       v3 TEMSILINDEN (sabit sirali dizi + gorsel oneki + `yeniRef`) gecirilir ve CANLI
       index.html `ozetAc` fonksiyonuyla geri acilir; deger orada da BIREBIR ayni olmali.
       Sepet paneli okudugu urun objesini ISTE O acilmis karttan alir.

FAIL-CLOSED: alan cikarimi bozulursa (kume beklenenden kucuk) kapi YESIL VEREMEZ — kirmizi
yanar. "Alan bulunamadi = kontrol edilecek bir sey yok" sessiz gecisi bu deponun defalarca
isirildigi desendir.

KAPSAM SINIRI: kartin IKINCI uretici tarafi (edge Worker `KART_ALANLARI`, ~/dev/pruvo-bot)
KARDES DEPODUR — bu kapi ona DOKUNMAZ. Yerelde varsa yalniz OLCER ve raporlar; CI fresh
checkout'unda o agac olmadigi icin ASLA kirmizi yakmaz (R_YOL sinifi yapisal kirmizisi yok).

🔴 11 AGU 2026 — O OLCUMUN AYRISTIRMASI KORDU (onarildi, bkz js_sabit_dize): eski regex
`KART_ALANLARI` sabitinin YALNIZ ILK tirnak ciftini okuyordu; `+` ile eklenen ikinci ve
sonraki dize parcalari GORUNMUYORDU. O parcalara dusen bir kolon SELECT'te GERCEKTEN
varken "eksik" raporlaniyordu (KOTUMSER yalan). Onarim ifadeyi ';'ye kadar ayristirip
tum dize literallerini birlestirir; dize-disi (dinamik) tanimda "alan yok" DEMEZ,
OLCULEMEDI basar. Onarimin canliligini olcen batarya: tools/edge-kart-tirnak-mutasyon.py.

MUTASYON (--mutasyon) — build/secenekler mutantlari BELLEKTE; index.html mutanti GECICI
DIZINE yazilir, depo agacina ASLA dokunulmaz. Iki YONLU (pozitif + negatif):
    M-A  kart_ozeti'den `tur` satiri silinir            -> KIRMIZI (curutucunun bulgusu)
    M-B  kart_ozeti'den `fiyat` alani silinir           -> KIRMIZI (eksen `tur`a capali DEGIL)
    M-C  secenekler.js'e YENI bir `urun.stokta` okumasi -> KIRMIZI (yarinki alan da yakalanir)
    M-D  istemci `ozetAc` `tur`u geri ACMAZ             -> KIRMIZI (TEL ekseni; eski kapsam KORDU)
    M-E  derleme teli 8'inci konumda KESER              -> KIRMIZI (TEL ekseni; eski kapsam KORDU)
    M-F  istemci `ozetAc` `aciklama`yi geri ACMAZ       -> YESIL  (NEGATIF nobetci: bu kapinin
         ekseni fiyat/beyan alanlaridir; kapsam bir DUVARA donusmedi)

Kullanim:
    python3 tools/edge-kart-kapisi.py
    python3 tools/edge-kart-kapisi.py --mutasyon
Cikis: 0 = yesil, 1 = kirmizi.
"""
import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
BUILD_YOL = os.path.join(TOOLS, "build.py")
SECENEKLER_YOL = os.path.join(ROOT, "secenekler.js")
URUNLER_YOL = os.path.join(ROOT, "urunler.json")
INDEX_YOL = os.path.join(ROOT, "index.html")
AYIKLA_YOL = os.path.join(TOOLS, "ozet-ac-ayikla.js")

# TEL ekseninde alan basina kac urun orneklenecek. Kucuk tutuluyor: bu eksen bir TEMSIL
# hatasi dedektorudur (konum kaymasi / kayip alan), veri denetimi DEGIL — deger denetimini
# yukaridaki KART ekseni alan basina 200 urunle zaten yapiyor. 6 alan x 8 urun tek `yeni`
# kesitine (OZET_YENI=48) sigar, yani tek node cagrisi.
TEL_ORNEK = 8

# Kardes depo (edge Worker) — YALNIZ OLCUM, kapiyi kirmizi YAKMAZ.
KARDES_WORKER = os.path.expanduser("~/dev/pruvo-bot/worker/src/index.js")

# Cikarimin SAGLIK esigi: secenekler.js satirOzeti bugun en az bu kadar alan okur
# (kategori/fiyat/parametrik/tur/boy_secenekleri). Regex bozulup 0-1 alan dondurdugunde
# kapi "kontrol edecek sey yok" diye YESIL yanmasin.
EN_AZ_ALAN = 4


# --------------------------------------------------------------------------- cikarim
def alanlari_cikar(kaynak):
    """secenekler.js kaynagindan `urun.<alan>` okumalarini cikarir (alan adlari kumesi).

    `urunId` gibi baska tanimlayicilar EslESMEZ (\\b + tam `urun` sozcugu). Cikarim
    KAYNAK TABANLIDIR: elle bakimli bir liste olsaydi yarin eklenen alan sessizce
    kapsam disi kalirdi."""
    return set(re.findall(r"\burun\s*\.\s*([A-Za-z_$][A-Za-z0-9_$]*)", kaynak))


# --------------------------------------------------------------- kardes JS sabiti
# 🔴 11 AGU 2026 — AYRISTIRMA KORLUGU ONARIMI (kardes mimar bulgusu).
#   ESKI DESEN:  re.search(r"KART_ALANLARI\s*=\s*([`\"'])([\s\S]*?)\1", w)
#   ILK tirnaktan ILK kapanan tirnaga kadarini okur. JS tarafinda sabit
#       const KART_ALANLARI =
#         "u.id, ... u.parametrik," +
#         " substr(u.aciklama, 1, 160) AS aciklama";
#   seklinde COK PARCALI yazildiginda IKINCI ve sonraki parcalar GORUNMEZ. Bir kolon
#   o parcalara dustugunde kapi, kolon SELECT'te GERCEKTEN varken "eksik alan(lar)"
#   basar — sessiz, KOTUMSER bir yalan. Olculdu: kardes depo bu korlugu bir YORUMLA
#   idare ediyordu ("yeni kolon alt satira degil BU satira yazilir") — yani bizim
#   ayristirma hatamiz kardes depoda LOAD-BEARING bir yazim kisitina donusmustu.
#
# 🔴 ONARIM GEVSETME DEGIL. Ifade YALNIZ dize literali + `+` + yorumdan olusabilir.
#   Degisken, fonksiyon cagrisi, `${...}` interpolasyonu, kapanmamis dize -> DINAMIK
#   sayilir ve OLCULEMEDI basilir. "Cozemedim = alan yok" sessiz gecisi YASAKTIR;
#   alan GERCEKTEN eksikken kapi eskisi gibi eksik demeye devam eder.
#
# 🔴 SATIR BASI CAPASI: atama `^[ \t]*(const|let|var)? AD =` ile aranir. Kardes
#   dosyada sabitin USTUNDE, ayni adi tasiyan bir YORUM blogu var; capa satir basina
#   bagli olmasa o yorum kazanir ve kapi yorumdan alan okurdu.

# Ayrik jetonlar — hicbiri digerinin ALT DIZESI DEGIL. ([[maskeleme-kismi-kapatma]]:
# "eksik alan(lar): YOK" gibi ortak govdeli iki kol, bir kolu olduren mutantin
# digerinin capasindan gecmesine izin veriyordu.)
JETON_TAM = "WORKER_KART_TAM"
JETON_EKSIK = "WORKER_KART_EKSIK"
JETON_OLCULEMEDI = "OLCULEMEDI"
JETON_AGAC_YOK = "WORKER_AGAC_YOK"

_KACIS = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


def _js_dize_oku(kaynak, i):
    """kaynak[i] bir tirnak. (deger, sonraki_index, sebep) doner; sebep varsa deger None."""
    q = kaynak[i]
    i += 1
    out = []
    n = len(kaynak)
    while i < n:
        c = kaynak[i]
        if c == "\\":
            if i + 1 >= n:
                return None, i, "kacis dizisi dosya sonunda yarim kaldi"
            e = kaynak[i + 1]
            out.append(_KACIS.get(e, e))
            i += 2
            continue
        if c == q:
            return "".join(out), i + 1, None
        if q == "`" and kaynak.startswith("${", i):
            return None, i, "template literal icinde ${...} interpolasyonu (DINAMIK tanim)"
        if q != "`" and c == "\n":
            return None, i, "kapanmamis dize literali (satir sonu)"
        out.append(c)
        i += 1
    return None, i, "kapanmamis dize literali (dosya sonu)"


def js_sabit_dize(kaynak, ad):
    """JS kaynagindaki `<ad> = "..." + '...' + `...`;` sabitini BIRLESTIREREK dondurur.

    Donus: (deger, parca_sayisi, sebep). deger None ise sebep OLCULEMEDI gerekcesidir
    (fail-closed: cozulemeyen tanim "alan yok" SAYILMAZ)."""
    m = re.search(r"^[ \t]*(?:const[ \t]+|let[ \t]+|var[ \t]+)?%s[ \t]*=(?!=)"
                  % re.escape(ad), kaynak, re.M)
    if not m:
        return None, 0, "`%s` atamasi bulunamadi (satir basi capasi tutmadi)" % ad
    i, n = m.end(), len(kaynak)
    parcalar = []
    bekle_operand = True
    while i < n:
        c = kaynak[i]
        if c in " \t\r\n":
            i += 1
            continue
        if kaynak.startswith("//", i):
            j = kaynak.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if kaynak.startswith("/*", i):
            j = kaynak.find("*/", i + 2)
            if j < 0:
                return None, 0, "kapanmamis blok yorum"
            i = j + 2
            continue
        if c == ";":
            if not parcalar:
                return None, 0, "`%s` ifadesinde hic dize literali yok" % ad
            if bekle_operand:
                return None, 0, "ifade '+' ile bitip ';' geldi (yarim ifade)"
            return "".join(parcalar), len(parcalar), None
        if bekle_operand:
            if c in "\"'`":
                deger, i, sebep = _js_dize_oku(kaynak, i)
                if sebep:
                    return None, 0, sebep
                parcalar.append(deger)
                bekle_operand = False
                continue
            return None, 0, ("`%s` dize literali ile tanimlanmamis; beklenmeyen jeton %r "
                             "(DINAMIK tanim ayristirilamaz)" % (ad, kaynak[i:i + 40]))
        if c == "+":
            i += 1
            bekle_operand = True
            continue
        return None, 0, "'+' ya da ';' bekleniyordu, gelen %r" % kaynak[i:i + 40]
    return None, 0, "ifade ';' ile kapanmadi (dosya sonu)"


def worker_kapsam_satiri(worker_kaynak, kontrol_alanlari):
    """Kardes depo Worker kaynagindan KART_ALANLARI'ni cozer, eksik alanlari bulur.

    Donus: (satir, eksikler). eksikler None => OLCULEMEDI.
    KAPSAM DISI: kardes depo bu kapinin duzlemi DEGIL — bu satir kapiyi ASLA kirmizi
    yakmaz, yalniz OLCER."""
    deger, parca, sebep = js_sabit_dize(worker_kaynak, "KART_ALANLARI")
    if deger is None:
        return ("edge Worker KART_ALANLARI %s: %s (kardes depo, KAPSAM DISI — hukum "
                "VERILMEDI; 'cozemedim = alan yok' sessiz gecisi YASAK)"
                % (JETON_OLCULEMEDI, sebep), None)
    eksikler = [a for a in kontrol_alanlari
                if not re.search(r"\b%s\b" % re.escape(a), deger)]
    if eksikler:
        return ("edge Worker KART_ALANLARI %s (kardes depo, KAPSAM DISI — yalniz olcum; "
                "%d dize parcasi birlestirildi): eksik alan(lar): %s"
                % (JETON_EKSIK, parca, ", ".join(eksikler)), eksikler)
    return ("edge Worker KART_ALANLARI %s (kardes depo, KAPSAM DISI — yalniz olcum; "
            "%d dize parcasi birlestirildi): kontrol edilen %d alanin hepsi SELECT'te"
            % (JETON_TAM, parca, len(kontrol_alanlari)), [])


def _dolu(deger):
    """Alan "deger tasiyor" mu? Bos dize / None / bos liste / False TASIMAZ sayilir —
    kartta gorunmemesi o urun icin fiyat/beyan farki yaratmaz."""
    if deger is None or deger is False:
        return False
    if isinstance(deger, (str, list, dict, tuple)):
        return len(deger) > 0
    return True


# --------------------------------------------------------------------------- build modulu
def build_modulu(mutasyon=None):
    """tools/build.py'yi (istege bagli TEK kaynak-kodu mutasyonuyla) BELLEKTE yukler.
    Mutasyon DISKE YAZILMAZ: kosum yarida kalirsa mutant build.py commit'e sizardi."""
    with open(BUILD_YOL, encoding="utf-8") as f:
        src = f.read()
    if mutasyon is not None:
        eski, yeni = mutasyon
        if src.count(eski) != 1:
            raise SystemExit("MUTASYON CAPASI KAYIP/COKLU (%d adet): %r — build.py degismis."
                             % (src.count(eski), eski))
        src = src.replace(eski, yeni, 1)
    mod = types.ModuleType("build_edge_olculen")
    mod.__file__ = BUILD_YOL
    mod.__name__ = "build_edge_olculen"      # __main__ DEGIL -> main() kendiliginden kosmaz
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(src, BUILD_YOL, "exec"), mod.__dict__)
    return mod


# --------------------------------------------------------------------------- TEL ekseni
# 🔴 KAPSAM TELE GENISLETILDI (12 Agu 2026, bagimsiz curutucu bulgusu).
#     ESKI KAPSAM: yalniz `kart_ozeti(p)` sozlugu — yani kartin URETILDIGI an. Olculdu:
#     bu dosya index.html'i ve ozet.json artefaktini HIC OKUMUYORDU (0 okuma).
#     v3 temsili araya bir TEL koydu (sabit sirali dizi + gorsel oneki + `yeniRef`) ve
#     kapinin kapsami telin USTUNDE kaldi: fiyat/beyan kaybettiren 3 mutantin 2'sinde
#     (istemci `tur`u geri ACMIYOR · derleme teli 8'inci konumda KESIYOR) kapi YESIL yaniyordu.
#     Alan `kart_ozeti`de VAR olmakla kalmamali, telden gecip CANLI istemci cozucusuyle
#     geri acildiginda da AYNI DEGERI tasimali — sepet paneli o acilmis karti okuyor.
#
# ⚠️ YENI DUVAR DEGIL, AYNI EKSENIN DERINLESMESI: olculen kume yine `secenekler.js`ten
#     cikarilan fiyat/beyan alanlaridir. `baslik`/`aciklama`/`gorsel` gibi alanlarin temsili
#     bu kapinin ekseni DEGILDIR (o tools/ozet-temsil-test.js'in isi) ve onlari bozan bir
#     degisiklik burayi KIRMIZI YAKMAZ — negatif nobetci (mutant M-F) bunu civiler.
def _tel_ornekle(urunler, alanlar, tel_ornek=TEL_ORNEK):
    """Alan basina en fazla `tel_ornek` tasiyici urun; sira korunur, id ile tekillenir."""
    secilen, gorulen = [], set()
    for alan in alanlar:
        n = 0
        for p in urunler:
            if n >= tel_ornek:
                break
            if not _dolu(p.get(alan)):
                continue
            n += 1
            pid = p.get("id")
            if pid in gorulen:
                continue
            gorulen.add(pid)
            secilen.append(p)
    return secilen


def _canli_cozucu_ac(artefakt_metni, index_yol):
    """ozet.json metnini CANLI index.html `ozetAc` fonksiyonundan gecirir.

    Cozucunun PYTHON KOPYASI TUTULMAZ (`ozet_karti_ac` build.py'nin kendi ikizidir ve
    istemciyle sessizce ayrisabilir) — gercek dosyadaki fonksiyon node ile kosturulur.
    Donus: (acilmis_sozluk, sebep). sebep varsa OLCULEMEDI'dir ve kapi KIRMIZI yanar;
    "cozemedim = sorun yok" sessiz gecisi YASAK."""
    if not shutil.which("node"):
        return None, ("node bulunamadi — CANLI istemci cozucusu kosturulamadi "
                      "(CI'da setup-node BLOKLAYICI on-kosuldur)")
    gec = tempfile.mkdtemp(prefix="edge-kart-tel-")
    try:
        yol = os.path.join(gec, "ozet.json")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(artefakt_metni)
        argv = ["node", AYIKLA_YOL, "--ac", yol, "--index", index_yol]
        r = subprocess.run(argv, capture_output=True, text=True)
        if r.returncode != 0:
            return None, ("canli cozucu rc=%d -> %s"
                          % (r.returncode, (r.stderr or r.stdout).strip()[-200:]))
        try:
            return json.loads(r.stdout), None
        except ValueError as e:
            return None, "canli cozucu ciktisi JSON degil: %s" % e
    finally:
        shutil.rmtree(gec, ignore_errors=True)


def tel_kosumu(mod, urunler, kontrol_alanlari, index_yol):
    """Ornek kartlari v3 TELINDEN gecirip CANLI istemci cozucusuyle geri acar.

    (hatalar, satirlar) dondurur."""
    hatalar, satirlar = [], []
    ornek = _tel_ornekle(urunler, kontrol_alanlari)
    if not ornek:
        satirlar.append("  · TEL (v3 -> canli ozetAc): deger tasiyan urun YOK -> olculecek "
                        "kart yok (kart ekseni zaten MUAF raporladi)")
        return hatalar, satirlar
    bolum = int(getattr(mod, "OZET_YENI", 48))
    kart_sayisi, deger_sayisi = 0, 0
    for bas in range(0, len(ornek), bolum):
        parti = ornek[bas:bas + bolum]
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                metin = mod.render_ozet(parti, temsil_surum=3)
        except SystemExit as e:
            hatalar.append("TEL: v3 artefakti URETILEMEDI (build fail-closed): %s" % e)
            return hatalar, satirlar
        acik, sebep = _canli_cozucu_ac(metin, index_yol)
        if sebep:
            hatalar.append("TEL: %s -> OLCULEMEDI (kapi bu halde YESIL VEREMEZ)" % sebep)
            return hatalar, satirlar
        if acik.get("yeniCozulemeyen"):
            hatalar.append("TEL: istemci %s referansi COZEMEDI -> o kartlar cizilmiyor "
                           "(sessiz kart kaybi)" % acik["yeniCozulemeyen"])
        kartlar = {}
        for k in (list(acik.get("parametrik") or [])
                  + [x for liste in (acik.get("bloklar") or {}).values() for x in liste]
                  + list(acik.get("yeni") or [])):
            if isinstance(k, dict) and "id" in k:
                kartlar.setdefault(json.dumps(k["id"], sort_keys=True), k)
        for p in parti:
            anahtar = json.dumps(p.get("id"), sort_keys=True)
            acilmis = kartlar.get(anahtar)
            if acilmis is None:
                hatalar.append("TEL: `%s` urunu v3 telinden GERI GELMEDI (istemci karti "
                               "cizmiyor) -> edge modunda sepet o urunu bulamaz" % p.get("id"))
                continue
            kart_sayisi += 1
            kaynak = mod.kart_ozeti(p)
            for alan in kontrol_alanlari:
                if alan not in kaynak:
                    continue
                beklenen = json.loads(json.dumps(kaynak[alan]))
                if alan not in acilmis:
                    hatalar.append("TEL: `%s` alani kartta URETILIYOR ama v3 telinden "
                                   "gecip CANLI istemci cozucusuyle acilinca YOK (or. %s) "
                                   "-> EDGE MODUNDA SESSIZ FIYAT/BEYAN SAPMASI"
                                   % (alan, p.get("id")))
                elif acilmis[alan] != beklenen:
                    hatalar.append("TEL: `%s` alani telden BOZUK donuyor: %s "
                                   "(acilan=%r kaynak=%r)"
                                   % (alan, p.get("id"), acilmis[alan], beklenen))
                else:
                    deger_sayisi += 1
    satirlar.append("  · TEL (v3 -> CANLI index.html ozetAc): %d kart geri acildi, %d "
                    "alan-degeri BIREBIR %s"
                    % (kart_sayisi, deger_sayisi, "✔" if not hatalar else "✘"))
    return hatalar, satirlar


# --------------------------------------------------------------------------- olcum
def kosum(secenek_kaynak, mod, urunler, ornek_en_cok=200, index_yol=None):
    """(hatalar, satirlar) dondurur. hatalar bos = YESIL."""
    hatalar, satirlar = [], []
    deger_tasiyan = []          # kardes depo olcumunde kontrol edilecek alanlar

    alanlar = alanlari_cikar(secenek_kaynak)
    satirlar.append("secenekler.js'ten cikarilan fiyat/beyan alanlari (%d): %s"
                    % (len(alanlar), ", ".join(sorted(alanlar))))
    if len(alanlar) < EN_AZ_ALAN:
        hatalar.append("FAIL-CLOSED: alan cikarimi %d alan dondurdu (>= %d bekleniyor) — "
                       "regex ya da secenekler.js degismis; kapi bu halde YESIL VEREMEZ"
                       % (len(alanlar), EN_AZ_ALAN))
        return hatalar, satirlar

    for alan in sorted(alanlar):
        tasiyanlar = [p for p in urunler if _dolu(p.get(alan))]
        if not tasiyanlar:
            satirlar.append("  · %-16s katalogda deger tasiyan urun 0 -> MUAF (uyuyan risk: "
                            "bu alani tasiyan ilk urun eklendigi gun kart da guncellenmeli)"
                            % alan)
            continue
        deger_tasiyan.append(alan)
        eksik, sapan = [], []
        for p in tasiyanlar[:ornek_en_cok]:
            kart = mod.kart_ozeti(p)
            if alan not in kart:
                eksik.append(p.get("id"))
            elif kart[alan] != p.get(alan):
                sapan.append("%s (kart=%r katalog=%r)" % (p.get("id"), kart[alan], p.get(alan)))
        if eksik:
            hatalar.append("`%s` alani sepet fiyatini/beyanini etkiliyor ve katalogda %d urunde "
                           "DOLU, ama edge kartinda YOK (or. %s) -> EDGE MODUNDA SESSIZ SAPMA"
                           % (alan, len(tasiyanlar), ", ".join(eksik[:3])))
        if sapan:
            hatalar.append("`%s` alani kartta VAR ama DEGERI ayrisiyor: %s"
                           % (alan, "; ".join(sapan[:3])))
        satirlar.append("  · %-16s tasiyan urun %5d | kartta: %s"
                        % (alan, len(tasiyanlar),
                           "YOK ✘" if eksik else ("DEGER AYRI ✘" if sapan else "VAR ✔")))

    # --- TEL EKSENI: alan `kart_ozeti`de var olmakla kalmasin, v3 temsilinden gecip CANLI
    # istemci cozucusuyle geri acildiginda da AYNI degeri tasisin.
    tel_hatalar, tel_satirlar = tel_kosumu(mod, urunler, deger_tasiyan,
                                           index_yol or INDEX_YOL)
    hatalar.extend(tel_hatalar)
    satirlar.extend(tel_satirlar)

    # --- kardes depo (edge Worker) — YALNIZ OLCUM
    if os.path.exists(KARDES_WORKER):
        with open(KARDES_WORKER, encoding="utf-8") as f:
            w = f.read()
        satir, _ = worker_kapsam_satiri(w, deger_tasiyan)
        satirlar.append(satir)
    else:
        satirlar.append("edge Worker (kardes depo ~/dev/pruvo-bot) diskte YOK -> %s "
                        "(CI fresh checkout'unda normal; bu kapi ona ASLA kirmizi yakmaz)"
                        % JETON_AGAC_YOK)
    return hatalar, satirlar


# --------------------------------------------------------------------------- mutasyon
# Her mutant DAR: yalnizca bu kapinin olctugu eksenin yakalayabilecegi bir bozulma.
# 🔴 IKI YONLU: POZITIF mutant (fiyat/beyan kaybettirir -> KIRMIZI olmali) ve NEGATIF
# mutant (fiyat/beyan ile ILGISIZ -> YESIL kalmali) AYNI tabloda. Tek yonlu nobetci olu
# nobetcidir: kapsam genisletilirken "her degisiklige kirmizi yanan" bir duvara donusmedigi
# ancak NEGATIF vaka ile kanitlanir (deploy.yml'de continue-on-error YOK — yanlis-pozitif
# TUM ekibin yayinini durdurur).
MUTANTLAR = [
    ("M-A kart_ozeti'den `tur` satiri silindi",
     ("build", '    if p.get("tur") == "fiziksel":\n        kart["tur"] = "fiziksel"\n',
      ""),
     "curutucunun bulgusu: fiziksel isaret edge kartina inmezse panel +%84 gosterir",
     "kirmizi"),
    ("M-B kart_ozeti'den `fiyat` alani silindi",
     ("build", '        "fiyat": p.get("fiyat") or "",\n', ""),
     "eksen ALAN LISTESI ekseni mi, yoksa `tur` literaline mi capali? (capaliysa bu YESIL kalir)",
     "kirmizi"),
    ("M-C secenekler.js'e YENI bir fiyat-etkileyen alan okumasi eklendi (urun.stokta)",
     ("secenek", "  function satirOzeti(urun, satir) {",
      "  function satirOzeti(urun, satir) {\n    var _yeniAlan = urun && urun.stokta;"),
     "yarin eklenen bir alan da kapsama giriyor mu? (girmiyorsa kapi YARIN OLU olur)",
     "kirmizi"),
    # --- TEL EKSENI (12 Agu): kapinin kapsami v3 telinin USTUNDE kalmisti ---
    ("M-D ISTEMCI: ozetAc `tur` alanini geri ACMAZ (curutucu W1)",
     ("index",
      '        if(i < alanlar.length && (i < 8 || deger !== null)){ out[alanlar[i]] = deger; }',
      '        if(i < alanlar.length && (i < 8 || deger !== null) && alanlar[i] !== "tur")'
      '{ out[alanlar[i]] = deger; }'),
     "alan kartta URETILIYOR ama istemci geri acmiyor -> panel +%84 sisik fiyat gosterir; "
     "ESKI KAPSAM bunu GORMUYORDU",
     "kirmizi"),
    ("M-E DERLEME: tel 8'inci konumdan sonra KESILIR (curutucu W2)",
     ("build",
      "    son = max((i for i, alan in enumerate(OZET_KART_ALANLARI) if alan in kart), "
      "default=-1)",
      "    son = min(7, max((i for i, alan in enumerate(OZET_KART_ALANLARI) if alan in kart), "
      "default=-1))"),
     "kosullu alanlar (tur/tavsiyeFilament/konfigur) tele HIC yazilmaz; kart sozlugu "
     "dogru oldugu icin ESKI KAPSAM YESIL yaniyordu",
     "kirmizi"),
    # --- NEGATIF NOBETCI: bu kapinin ekseni DISINDA kalan bir temsil bozulmasi ---
    ("M-F (NEGATIF) ISTEMCI: ozetAc `aciklama` alanini geri ACMAZ",
     ("index",
      '        if(i < alanlar.length && (i < 8 || deger !== null)){ out[alanlar[i]] = deger; }',
      '        if(i < alanlar.length && (i < 8 || deger !== null) && alanlar[i] !== "aciklama")'
      '{ out[alanlar[i]] = deger; }'),
     "`aciklama` sepet FIYATINI/BEYANINI surmez (secenekler.js okumaz) -> bu kapi "
     "YESIL KALMALI; bozulmayi tools/ozet-temsil-test.js yakalar. Kirmizi yanarsa kapsam "
     "genislemesi bir DUVARA donusmus demektir",
     "yesil"),
]


def mutasyon_kosumu(urunler, taban_kaynak):
    print("=== MUTASYON: kapi GERCEKTEN yuk tasiyor mu? (her mutant BEYAN EDILEN "
          "yonde olmali)")
    with open(INDEX_YOL, encoding="utf-8") as f:
        index_taban = f.read()
    gec = tempfile.mkdtemp(prefix="edge-kart-mutant-")
    tut = 0
    try:
        for ad, (hedef, eski, yeni), gerekce, beklenen in MUTANTLAR:
            index_yol = INDEX_YOL
            kaynak = taban_kaynak
            if hedef == "build":
                mod = build_modulu(mutasyon=(eski, yeni))
            elif hedef == "index":
                mod = build_modulu()
                if index_taban.count(eski) != 1:
                    raise SystemExit("MUTASYON CAPASI KAYIP/COKLU (%d adet): %r "
                                     "(index.html degismis)" % (index_taban.count(eski), eski))
                # Mutant KOPYAYA yazilir; depo agacindaki index.html'e DOKUNULMAZ.
                index_yol = os.path.join(gec, "mutant-index-%d.html" % (tut + 1))
                with open(index_yol, "w", encoding="utf-8") as f:
                    f.write(index_taban.replace(eski, yeni, 1))
            else:
                mod = build_modulu()
                if taban_kaynak.count(eski) != 1:
                    raise SystemExit("MUTASYON CAPASI KAYIP/COKLU: %r (secenekler.js degismis)"
                                     % eski)
                kaynak = taban_kaynak.replace(eski, yeni, 1)
            hatalar, _ = kosum(kaynak, mod, urunler, index_yol=index_yol)
            gozlenen = "kirmizi" if hatalar else "yesil"
            tamam = gozlenen == beklenen
            tut += 1 if tamam else 0
            print("  %s %s%s"
                  % ("✔ KIRMIZI" if gozlenen == "kirmizi" else "✔ YESIL" if tamam
                     else "✘ YESIL KALDI",
                     ad, "" if tamam else "   ← ✘ BEKLENEN: %s" % beklenen.upper()))
            print("      gerekce: %s" % gerekce)
            if hatalar:
                print("      %s: %s"
                      % ("yakalandi" if beklenen == "kirmizi" else "YANLIS-POZITIF",
                         hatalar[0][:150]))
    finally:
        shutil.rmtree(gec, ignore_errors=True)
    pozitif = sum(1 for m in MUTANTLAR if m[3] == "kirmizi")
    print("")
    if tut != len(MUTANTLAR):
        print("MUTASYON: KALDI — %d/%d mutant beyan edilen yonde DEGIL, kapi OLU IDDIA "
              "tasiyor ya da YANLIS-POZITIF uretiyor" % (len(MUTANTLAR) - tut, len(MUTANTLAR)))
        return 1
    print("MUTASYON: GECTI — %d/%d mutant beyan edilen yonde (%d oldurucu KIRMIZI + "
          "%d ilgisiz YESIL)." % (tut, len(MUTANTLAR), pozitif, len(MUTANTLAR) - pozitif))
    return 0


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutasyon", action="store_true",
                    help="kapinin yuk tasidigini kanitla (3 mutant KIRMIZI yanmali)")
    ap.add_argument("--urunler", default=URUNLER_YOL)
    args = ap.parse_args()

    with open(args.urunler, encoding="utf-8") as f:
        urunler = json.load(f)
    with open(SECENEKLER_YOL, encoding="utf-8") as f:
        secenek_kaynak = f.read()

    if args.mutasyon:
        return mutasyon_kosumu(urunler, secenek_kaynak)

    hatalar, satirlar = kosum(secenek_kaynak, build_modulu(), urunler)
    print("=== EDGE KART ALAN KAPSAMI (ozet.json / kart_ozeti) — katalog %d urun"
          % len(urunler))
    for s in satirlar:
        print(s)
    print("")
    if hatalar:
        for h in hatalar:
            print("KIRMIZI: %s" % h)
        print("")
        print("SONUC: KIRMIZI ❌ — edge modunda sepet paneli sunucudan FARKLI fiyat/beyan "
              "uretebilir.")
        return 1
    print("SONUC: YESIL ✅ — fiyat/beyan alanlarinin hepsi ya edge kartinda VAR ya da "
          "katalogda deger tasiyan urunu YOK (sayiyla raporlandi).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RULMAN URETILEBILIRLIK OLCUMU — semadaki `kisitlar` katsayilarinin DAYANAGI
   + SEMA KAPISI <-> URETIM MOTORU DORT-KOVA PARITESI (satisa acmanin kaniti).

NEDEN VAR: olcuye-ozel-rulman semasindaki genislik alt siniri iki "sihirli" sayi
tasir (0,95/3 katsayisi ve bilya icin -0,24 payi). Bunlar TURETILMEDI, uretim
motoruna gercek render atilarak OLCULDU. Olcum yeniden uretilemezse katsayilar
bir sonraki muhendis icin dogrulanamaz bir iddiaya doner -> bu arac o olcumu
tekrar kosar. (Kapali form ANLATILMAZ, OLCULUR.)

OLCULEN KAPALI FORM (2026-08-03, 1600+ render, 0 ayrisma):
    eleman_capi = (dis_cap - ic_cap) / 3 * k     k: bilya 1,00 · makara 0,95 · tutmali 0,75
      makara  uretilir <=> eleman_capi <= genislik
      bilya   uretilir <=> eleman_capi <  genislik + 0,24
      tutmali uretilir <=> DAIMA
Ilan edilen izgaranin %33,9'u (43.085 / 126.945) motorda URETILEMEZ durumdaydi;
sema kapisi (jenerator/konfigurator.js kisitAltSinir) bunlari artik reddediyor.

DORT-KOVA PARITESI (--parite, 2026-08-04) — SATISA ACMANIN KANITI
-----------------------------------------------------------------
"Kisit var => satilamaz" onculu, "kisit var VE yesil parite kaydi yok => satilamaz"
onculune cevrildi (tools/onizleme-vaat-kapisi.py A3). O kaydi URETEN olcum budur.
Her nokta IKI hukumle etiketlenir — SEMA KAPISI (gercek KONF.dogrula) ve URETIM
MOTORU (gercek OpenSCAD render'i) — ve dort kovaya dusulur:

    kova 11  sema KABUL + motor KABUL   satilir, uretilir              (mesru is)
    kova 00  sema RET   + motor RET     satilmaz, zaten uretilemezdi   (dogru red)
    kova 10  sema KABUL + motor RET     🔴 TEHLIKELI — PARA TAHSIL EDILIR, URUN YOK
    kova 01  sema RET   + motor KABUL   DAR — uretilebilir ama satilmiyor (kayip is,
                                        guvenli yon; kapi bunu tehlike SAYMAZ)

KABUL = "tehlikeli kova 0 **VE** olculen nokta >= esik **VE** cozulmeyen 0 **VE**
4 kontrol mutantinin dordu de beyanina uydu". Cikis kodu TEK BASINA kabul DEGILDIR
([[mutasyon-kaniti-yeniden-uretilebilir]]): bir COKUS de sifir-disi rc verir, sifir
render de "0 tehlikeli" gibi gorunur.

KONTROL MUTANTLARI (SURUCUNUN ICINDE — anlatilan batarya kanit degildir).
Mutasyon SEMA KOPYASINA uygulanir, render sonuclari YENIDEN KULLANILIR (motor
verdikleri degismez; degisen yalnizca sema kapisinin hukmu):
    M1 makara katsayisi 0,31667 -> 0,30   GENISLETIR -> tehlikeli nokta URETMELI
    M2 bilya sabiti     -0,24   -> -0,60  GENISLETIR -> tehlikeli nokta URETMELI
    M3 `kisitlar` blogu tumuyle SILINIR   GENISLETIR -> tehlikeli nokta URETMELI
    M4 makara katsayisi 0,31667 -> 0,36   DARALTIR   -> tehlikeli nokta URETMEMELI,
                                          ama DAR kovasini (01) BUYUTMELI
M1-M3 olcumun genislemeyi, M4 daralmayi gordugunu kanitlar. Ucu de olmasa
"tehlikeli 0" iddiasi her seye KABUL diyen bir olcumle de saglanirdi.

🔴 SIFIR-OLCUM / COKME FAIL-CLOSED: OpenSCAD ara sira SIGSEGV atiyor (3 Agu
olcumunde 5 nokta). Bir nokta sinyalle olurse ya da stderr'inde assertion YOKKEN
basarisiz olursa TEK TEK 3 kez yeniden render edilir; hala cozulmezse "cozulmeyen"
sayilir ve kosum YESIL OLAMAZ. "Gormedim" ile "yok" ayni sey degildir.

Kullanim:
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py            # 120 set, kapali form
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py --set 400
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py --sema-kapisi
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py --parite --mod hizli
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py --parite --mod kayit --kayit-yaz
  python3 jenerator/test/rulman-uretilebilirlik-olcum.py --parite --mod tam    # ~1,27 M render

FAIL-CLOSED: gizli uretim paketi ya da openscad yoksa OLCULEMEDI -> exit 3
("yesil" SAYILMAZ). Motor dosya adi/tedarikci bu dosyada ANILMAZ; eslem
dosyasindan okunur (public depoya sir girmez).
"""
import argparse
import concurrent.futures
import datetime
import importlib.util
import io
import json
import os
import random
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(TEST_DIR))
OLCULEMEDI = 3

K = {"bilya": 1.0, "makara": 0.95, "tutmali": 0.75}

# --- PARITE IZGARASI: semadaki ILAN EDILEN parametre kutusunun TAMAMI ------------
# (jenerator/urunler/olcuye-ozel-rulman.json min/max/adim ile birebir; sema degisince
#  IZGARA_KAYNAGI kontrolu KIRMIZI yakar -> capa bayatlayamaz.)
PARITE_MODLARI = {"hizli": 400, "kayit": 16000, "tam": None}


def parite_kaydi_modulu():
    yol = os.path.join(REPO, "tools", "parite_kaydi.py")
    spec = importlib.util.spec_from_file_location("pruvo_parite_kaydi", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def kapali_form(ic, dis, gen, eleman):
    """OLCULEN uretilebilirlik kurali (semadaki kisitlarin ikizi)."""
    cap = (dis - ic) / 3.0 * K[eleman]
    if eleman == "makara":
        return cap <= gen + 1e-9
    if eleman == "bilya":
        return cap < gen + 0.24 - 1e-9
    return True


def izg(mn, mx, ad):
    n = int(round((mx - mn) / ad))
    return [round(mn + i * ad, 6) for i in range(n + 1)]


def sema_yolu():
    return os.path.join(REPO, "jenerator", "urunler", "olcuye-ozel-rulman.json")


def sema_oku():
    with io.open(sema_yolu(), encoding="utf-8") as f:
        return json.load(f)


def eksenler(sema):
    """SEMADAN TURETILEN eksen listesi — sabit kopya DEGIL ([[ikiz-tanim-sessiz-ayrisma]]).
    Sema araligi degisirse izgara kendiliginden degisir; taninmayan tip -> OLCULEMEDI."""
    cikti = []
    for p in sema["parametreler"]:
        tip = p.get("tip", "sayi")
        if tip == "sayi":
            cikti.append((p["ad"], izg(p["min"], p["max"], p["adim"])))
        elif tip == "secim":
            cikti.append((p["ad"], [s["deger"] if isinstance(s, dict) else s
                                    for s in p["secenekler"]]))
        else:
            print("OLCULEMEDI: '%s' parametresinin tipi (%s) izgaraya cevrilemiyor"
                  % (p["ad"], tip))
            sys.exit(OLCULEMEDI)
    return cikti


def toplam_nokta(eks):
    n = 1
    for _, degerler in eks:
        n *= len(degerler)
    return n


def _asal_mi(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def _obeb(a, b):
    while b:
        a, b = b, a % b
    return a


def ornek_indisleri(toplam, istenen):
    """DETERMINISTIK, tohum GEREKTIRMEYEN, TUM eksenlere yayilan alt kume.

    i -> (i*ADIM) % toplam; ADIM, toplam ile ARALARINDA ASAL secilir (tam devir ->
    tekrar YOK). Duz `range(0, toplam, k)` KULLANILMAZ: k bir eksenin periyoduyla
    ortak carpan tasirsa o eksen SABITLENIR (or. cift adim `flans`i dondurur) ve
    olcum sessizce kutunun bir dilimini olcmeye baslardi."""
    if istenen is None or istenen >= toplam:
        return list(range(toplam))
    adim = max(2, toplam // istenen)
    while not (_asal_mi(adim) and _obeb(adim, toplam) == 1):
        adim += 1
    return [(i * adim) % toplam for i in range(istenen)]


def indis_noktasi(eks, indis):
    nokta = {}
    for ad, degerler in eks:            # ilk eksen EN HIZLI degisen
        nokta[ad] = degerler[indis % len(degerler)]
        indis //= len(degerler)
    return nokta


def paket_yukle():
    """(server modulu, eslem_ailesi, scad_yolu) — yoksa OLCULEMEDI."""
    # Gizli paket gitignore'ludur -> WORKTREE'de bulunmaz. Ana checkout'u
    # gostermek icin PRUVO_ONIZLEME_DIR (yoksa bu deponun kendi dizini).
    derleyici = os.environ.get("PRUVO_ONIZLEME_DIR",
                               os.path.join(REPO, "onizleme", "derleyici"))
    server_yol = os.path.join(derleyici, "server.py")
    eslem_yol = os.path.join(derleyici, "eslem-ozel.json")
    motor_dir = os.environ.get("PRUVO_UYELIK_DIR",
                               os.path.join(REPO, ".uyelik-kodlar"))
    for yol in (server_yol, eslem_yol):
        if not os.path.exists(yol):
            print("OLCULEMEDI: gizli uretim paketi yok (%s). R2'deki paketten geri alin."
                  % os.path.basename(yol))
            sys.exit(OLCULEMEDI)
    spec = importlib.util.spec_from_file_location("onizleme_server", server_yol)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    eslem = json.load(io.open(eslem_yol, encoding="utf-8"))["aileler"]
    aile = eslem.get("olcuye-ozel-rulman")
    if not aile:
        print("OLCULEMEDI: uretim esleminde olcuye-ozel-rulman yok")
        sys.exit(OLCULEMEDI)
    scad = os.path.join(motor_dir, aile["scad"])
    if not os.path.exists(scad):
        scad_yedek = os.path.join(derleyici, aile["scad"])
        if os.path.exists(scad_yedek):
            scad = scad_yedek
        else:
            print("OLCULEMEDI: uretim motoru .scad kaynagi yok (%s)" % motor_dir)
            sys.exit(OLCULEMEDI)
    return server, aile, scad


def openscad_yolu():
    sys.path.insert(0, TEST_DIR)
    import dogrula
    return dogrula.openscad_yolu()


# ---------------------------------------------------------------------------
# MOTOR HUKMU (tek kanonik render fonksiyonu — taban ve mutantlar AYNI veriyi kullanir)
# ---------------------------------------------------------------------------
URETILIR, URETILEMEZ, BELIRSIZ = "uretilir", "uretilemez", "belirsiz"


def _tek_render(openscad, server, aile, scad, tmp, i, nokta):
    """(hukum, tani) — motorun O NOKTADAKI kendi cevabi."""
    bayraklar, sebep = server.d_bayraklari(aile, nokta)
    if bayraklar is None:
        return BELIRSIZ, "eslem kapsami disi: %s" % sebep
    stl = os.path.join(tmp, "r%d.stl" % i)
    if os.path.exists(stl):
        os.remove(stl)
    try:
        p = subprocess.run([openscad, "-o", stl, "--export-format", "binstl"] +
                           server.OPENSCAD_EK_BAYRAKLAR + bayraklar + [scad],
                           capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        return BELIRSIZ, "zaman asimi"
    h = p.stderr.decode("utf-8", "replace")
    if p.returncode == 0 and os.path.exists(stl) and os.path.getsize(stl) > 0:
        os.remove(stl)
        return URETILIR, ""
    if "ERROR: Assertion" in h:
        return URETILEMEZ, ""
    # rc<0 = sinyal (SIGSEGV vb.); assertion'siz basarisizlik da hukum DEGILDIR.
    return BELIRSIZ, "rc=%s %s" % (p.returncode, h.strip().splitlines()[-1][:120] if h.strip() else "")


def motor_hukumleri(openscad, server, aile, scad, noktalar, isci):
    """[hukum] + cozulmeyen indis listesi. Belirsiz nokta TEK TEK 3 kez yeniden
    denenir ([[hukum-yanlis-birimde]]: cokme 'uretilemez' sayilamaz)."""
    tmp = tempfile.mkdtemp(prefix="rulman-parite-")
    hukumler = [None] * len(noktalar)
    tanilar = {}

    def is_(i):
        return i, _tek_render(openscad, server, aile, scad, tmp, i, noktalar[i])

    with concurrent.futures.ThreadPoolExecutor(max_workers=isci) as havuz:
        tamam = 0
        for i, (hukum, tani) in havuz.map(is_, range(len(noktalar))):
            hukumler[i] = hukum
            if tani:
                tanilar[i] = tani
            tamam += 1
            if tamam % 2000 == 0:
                print("  ... %d/%d render" % (tamam, len(noktalar)))
                sys.stdout.flush()

    belirsizler = [i for i, h in enumerate(hukumler) if h == BELIRSIZ]
    if belirsizler:
        print("  BELIRSIZ %d nokta — TEK TEK yeniden render ediliyor (3 deneme)"
              % len(belirsizler))
    for i in belirsizler:
        for _ in range(3):
            hukum, tani = _tek_render(openscad, server, aile, scad, tmp, i, noktalar[i])
            if hukum != BELIRSIZ:
                hukumler[i] = hukum
                tanilar.pop(i, None)
                break
            tanilar[i] = tani
    cozulmeyen = [i for i, h in enumerate(hukumler) if h == BELIRSIZ]
    for i in cozulmeyen[:5]:
        print("  [COZULMEYEN] %s -> %s" % (noktalar[i], tanilar.get(i)))
    return hukumler, cozulmeyen


# ---------------------------------------------------------------------------
# SEMA KAPISI HUKMU — GERCEK KONF.dogrula (regex/yeniden-yazim YOK)
# ---------------------------------------------------------------------------
NODE_PROBU = """
const KONF = require(process.argv[2]);
const fs = require("fs");
const sema = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const noktalar = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
process.stdout.write(JSON.stringify(
  noktalar.map(function (p) { return KONF.dogrula(sema, p).gecerli ? 1 : 0; })));
"""


def sema_hukumleri(sema, noktalar, tmp):
    """[0/1] — semanin O NOKTADAKI kendi cevabi. Hata -> OLCULEMEDI."""
    prob = os.path.join(tmp, "sema-prob.js")
    with io.open(prob, "w", encoding="utf-8") as f:
        f.write(NODE_PROBU)
    sema_dosya = os.path.join(tmp, "sema.json")
    with io.open(sema_dosya, "w", encoding="utf-8") as f:
        f.write(json.dumps(sema, ensure_ascii=False))
    nokta_dosya = os.path.join(tmp, "noktalar.json")
    with io.open(nokta_dosya, "w", encoding="utf-8") as f:
        f.write(json.dumps(noktalar, ensure_ascii=False))
    p = subprocess.run(["node", prob,
                        os.path.join(REPO, "jenerator", "konfigurator.js"),
                        sema_dosya, nokta_dosya], capture_output=True, text=True)
    if p.returncode != 0:
        print("OLCULEMEDI: sema kapisi kosulamadi: %s" % (p.stderr or "")[:300])
        sys.exit(OLCULEMEDI)
    return json.loads(p.stdout)


def _kisit_bul(sema, eleman):
    for ks in sema.get("kisitlar") or []:
        if isinstance(ks, dict) and (ks.get("eger") or {}).get("eleman") == eleman:
            return ks
    raise AssertionError("MUTASYON CAPASI BULUNAMADI: eger.eleman=%r kisidi yok "
                         "(sema degismis, batarya BAYAT)" % eleman)


def _m1(sema):
    ks = _kisit_bul(sema, "makara")
    ks["min"]["terimler"]["dis_cap"] = 0.30
    ks["min"]["terimler"]["ic_cap"] = -0.30
    return sema


def _m2(sema):
    ks = _kisit_bul(sema, "bilya")
    ks["min"]["sabit"] = -0.60
    return sema


def _m3(sema):
    if not sema.get("kisitlar"):
        raise AssertionError("MUTASYON CAPASI BULUNAMADI: silinecek `kisitlar` yok")
    sema["kisitlar"] = []
    return sema


def _m4(sema):
    ks = _kisit_bul(sema, "makara")
    ks["min"]["terimler"]["dis_cap"] = 0.36
    ks["min"]["terimler"]["ic_cap"] = -0.36
    return sema


# (ad, uygulayici, beklenen_isaret)  beklenen_isaret: ">0" tehlikeli uretmeli, "==0" uretmemeli
MUTANTLAR = [
    ("M1 makara katsayisi 0,31667 -> 0,30 (GENISLETIR)", _m1, ">0"),
    ("M2 bilya sabiti -0,24 -> -0,60 (GENISLETIR)", _m2, ">0"),
    ("M3 `kisitlar` blogu SILINDI (GENISLETIR)", _m3, ">0"),
    ("M4 makara katsayisi 0,31667 -> 0,36 (DARALTIR — kontrol)", _m4, "==0"),
]


def kovala(sema_h, motor_h):
    """(kovalar, tehlikeli, dar) — 11/00/10/01."""
    kovalar = {"11": 0, "00": 0, "10": 0, "01": 0}
    for s, m in zip(sema_h, motor_h):
        if m == BELIRSIZ:
            continue
        anahtar = ("1" if s else "0") + ("1" if m == URETILIR else "0")
        kovalar[anahtar] += 1
    return kovalar, kovalar["10"], kovalar["01"]


def parite(a):
    pk = parite_kaydi_modulu()
    sema = sema_oku()
    eks = eksenler(sema)
    toplam = toplam_nokta(eks)
    # 🔴 IKIZ TANIM KAPISI ([[ikiz-tanim-sessiz-ayrisma]]): kayda yazilan izgara
    # buyuklugunu KAPI da bagimsiz hesaplar (pk.ilan_edilen_izgara). Iki taraf
    # ayrisirsa kapi her kosumda BAYAT der; ayrismayi BURADA, kaydi yazmadan once
    # fail-closed yakala.
    kapi_izgarasi = pk.ilan_edilen_izgara(sema)
    if kapi_izgarasi != toplam:
        print("OLCULEMEDI: izgara buyuklugu ikizi AYRISTI (surucu=%d, kapi=%r) — "
              "kayit yazilsa kapi onu BAYAT sayardi" % (toplam, kapi_izgarasi))
        sys.exit(OLCULEMEDI)
    istenen = PARITE_MODLARI[a.mod] if a.nokta is None else a.nokta
    indisler = ornek_indisleri(toplam, istenen)
    noktalar = [indis_noktasi(eks, i) for i in indisler]

    # 🔴 CI'DA HANGISI KOSTU + KAC NOKTA: hukum satirindan ONCE, her zaman basilir.
    print("PARITE KOSUMU  mod=%s  ilan edilen izgara=%d nokta  OLCULECEK=%d nokta  "
          "eksen=%s" % (a.mod, toplam, len(noktalar),
                        ",".join("%s(%d)" % (ad, len(d)) for ad, d in eks)))
    sys.stdout.flush()

    server, aile, scad = paket_yukle()
    openscad = openscad_yolu()
    if not openscad:
        print("OLCULEMEDI: openscad bulunamadi")
        sys.exit(OLCULEMEDI)
    motor_ozet = pk.dosya_ozeti(scad)
    beklenen, hata = pk.parmakizi_oku(REPO, aile["scad"])
    if beklenen is None:
        print("OLCULEMEDI: %s" % hata)
        sys.exit(OLCULEMEDI)
    if motor_ozet != beklenen:
        print("OLCULEMEDI: yerel motor kaynagi paket parmakizindan FARKLI "
              "(yerel=%s… paket=%s…) — olcum yayindaki motoru olcmez"
              % (motor_ozet[:12], beklenen[:12]))
        sys.exit(OLCULEMEDI)

    motor_h, cozulmeyen = motor_hukumleri(openscad, server, aile, scad, noktalar, a.isci)
    tmp = tempfile.mkdtemp(prefix="rulman-sema-")
    taban_h = sema_hukumleri(sema, noktalar, tmp)
    kovalar, tehlikeli, dar = kovala(taban_h, motor_h)
    olculen = sum(kovalar.values())

    print("\nTABAN: 11=%d  00=%d  10(TEHLIKELI)=%d  01(dar)=%d  | olculen=%d  cozulmeyen=%d"
          % (kovalar["11"], kovalar["00"], kovalar["10"], kovalar["01"],
             olculen, len(cozulmeyen)))
    if tehlikeli:
        for s, m, n in list(zip(taban_h, motor_h, noktalar)):
            if s and m == URETILEMEZ:
                print("  [TEHLIKELI] %s" % n)
                break

    print("\nKONTROL MUTANTLARI (mutasyon SEMA KOPYASINA; render sonuclari YENIDEN KULLANILIR):")
    mutant_sayilari, mutant_basarisiz = {}, []
    for ad, uygula, isaret in MUTANTLAR:
        kod = ad.split()[0]
        try:
            mut_sema = uygula(json.loads(json.dumps(sema)))
        except AssertionError as e:
            print("  [FAIL] %-52s %s" % (ad, e))
            mutant_basarisiz.append(kod + " (CAPA YOK)")
            mutant_sayilari[kod] = -1
            continue
        mh = sema_hukumleri(mut_sema, noktalar, tmp)
        mk, mt, md = kovala(mh, motor_h)
        mutant_sayilari[kod] = mt
        if isaret == ">0":
            ok, aciklama = mt > 0, "tehlikeli=%d (>0 olmali)" % mt
        else:
            ok = (mt == 0 and md > dar)
            aciklama = "tehlikeli=%d (0 olmali) · dar=%d > taban dar=%d olmali" % (mt, md, dar)
        print("  [%s] %-52s %s" % ("PASS" if ok else "FAIL", ad, aciklama))
        if not ok:
            mutant_basarisiz.append(kod)

    esik = a.esik
    hukum = []
    if tehlikeli:
        hukum.append("TEHLIKELI KOVA=%d (0 olmali)" % tehlikeli)
    if cozulmeyen:
        hukum.append("COZULMEYEN=%d (0 olmali)" % len(cozulmeyen))
    if olculen < esik:
        hukum.append("OLCULEN NOKTA=%d < esik=%d" % (olculen, esik))
    if mutant_basarisiz:
        hukum.append("BEYANINA UYMAYAN MUTANT: " + ",".join(mutant_basarisiz))

    print("\nKABUL OLCUTU (cikis kodu TEK BASINA kabul degildir):")
    print("  olculen nokta = %d (esik %d) · tehlikeli kova = %d · cozulmeyen = %d · "
          "mutant %d/%d beyanina uydu"
          % (olculen, esik, tehlikeli, len(cozulmeyen),
             len(MUTANTLAR) - len(mutant_basarisiz), len(MUTANTLAR)))
    if hukum:
        print("KIRMIZI: " + " | ".join(hukum))
        return 1
    print("PARITE YESIL.")

    if a.kayit_yaz:
        girdi = {
            "surucu": "jenerator/test/rulman-uretilebilirlik-olcum.py --parite",
            "mod": a.mod if a.nokta is None else ("nokta=%d" % a.nokta),
            "ilanEdilenIzgara": toplam,
            "olculenNokta": olculen,
            "tehlikeliKova": tehlikeli,
            "cozulmeyen": len(cozulmeyen),
            "kovalar": kovalar,
            "kontrolMutantlari": mutant_sayilari,
            "motorDosya": aile["scad"],
            "motorOzet": motor_ozet,
            "semaUrunId": sema["id"],
            "semaKisitOzeti": pk.kisit_ozeti(sema),
            # 🔴 KUTU EKSENI: hangi PARAMETRE ARALIGI olculdu. Kisit blogu aynen
            # dururken bir `max` buyutulunce kayit BAYAT olsun diye (okuyucu
            # tools/parite_kaydi.py girdi_dogrula 5b).
            "semaKutuOzeti": pk.kutu_ozeti(sema),
            "tarih": datetime.date.today().isoformat(),
        }
        try:
            yol = pk.kayit_yaz(
                REPO, sema["hacimFormulu"], girdi,
                aciklama=("Sema kapisi <-> uretim motoru dort-kova paritesi. Bir ailenin "
                          "sema `kisitlar` blogu VARKEN satisa acilabilmesinin sarti: burada "
                          "YESIL ve TAZE bir girdi. Okuyucu tools/onizleme-vaat-kapisi.py "
                          "(A3), sozlesme tools/parite_kaydi.py. ELLE DUZENLENMEZ."),
                ezmeye_izin_ver=a.ezmeye_izin_ver, kuru_prova=a.kuru_prova)
        except pk.KucultmeReddi as exc:
            # FAIL-CLOSED: kanit ZAYIFLAYACAKTI -> sessiz basari YOK, sifir-disi cikis.
            print("KIRMIZI: %s" % exc)
            return pk.KOD_KUCULTME
        print("PARITE KAYDI %s: %s"
              % ("KURU PROVA (yazilmadi)" if a.kuru_prova else "YAZILDI",
                 os.path.relpath(yol, REPO)))
    return 0


def parser_kur():
    """CLI ayristiricisi — TEK KAYNAK.

    🔴 `--ezmeye-izin-ver` / `--kuru-prova` VARSAYILANI burada yasar ve kabul testi
    onu `parse_args([])` ile OLCER (duzyazidan/dokumandan DEGIL): varsayilan False'tan
    True'ya kayarsa test KIRMIZI yanar."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", type=int, default=120)
    ap.add_argument("--tohum", type=int, default=4242)
    ap.add_argument("--sema-kapisi", action="store_true",
                    help="yalniz semanin KABUL ettigi setleri at (beklenen: 0 uretilemez)")
    ap.add_argument("--parite", action="store_true",
                    help="sema kapisi <-> uretim motoru DORT-KOVA paritesi + 4 kontrol mutanti")
    ap.add_argument("--mod", choices=sorted(PARITE_MODLARI), default="hizli")
    ap.add_argument("--nokta", type=int, default=None,
                    help="--mod yerine acik nokta sayisi")
    ap.add_argument("--esik", type=int, default=200,
                    help="KABUL icin en az olculen nokta (satis kapisi esigi ayri: "
                         "tools/onizleme-vaat-kapisi.py EN_AZ_PARITE_NOKTA)")
    ap.add_argument("--isci", type=int, default=max(2, (os.cpu_count() or 4)))
    ap.add_argument("--kayit-yaz", action="store_true",
                    help="YESIL kosumda jenerator/test/uretilebilirlik-parite.json'u gunceller")
    ap.add_argument("--ezmeye-izin-ver", dest="ezmeye_izin_ver", action="store_true",
                    help="YIKICI: parite kaydinin sayisal alanlarini KUCULT (varsayilan KAPALI)")
    ap.add_argument("--kuru-prova", dest="kuru_prova", action="store_true",
                    help="kayit dosyasina hicbir sey yazma, ne olacagini bas")
    return ap


def main():
    a = parser_kur().parse_args()

    if a.parite:
        return parite(a)

    server, aile, scad = paket_yukle()
    openscad = openscad_yolu()
    if not openscad:
        print("OLCULEMEDI: openscad bulunamadi")
        sys.exit(OLCULEMEDI)

    IC, DIS, GEN = izg(5, 20, .5), izg(28, 60, .5), izg(5, 15, .5)
    BOS, ELE, FL = izg(.1, .3, .05), list(K), ["yok", "var"]
    rnd = random.Random(a.tohum)
    setler = []
    while len(setler) < a.set:
        s = {"ic_cap": rnd.choice(IC), "dis_cap": rnd.choice(DIS),
             "genislik": rnd.choice(GEN), "eleman": rnd.choice(ELE),
             "bosluk": rnd.choice(BOS), "flans": rnd.choice(FL)}
        setler.append(s)

    if a.sema_kapisi:
        p = subprocess.run(
            ["node", "-e",
             "const K=require(process.argv[1]);const s=require(process.argv[2]);"
             "const fs=require('fs');const g=JSON.parse(fs.readFileSync(0,'utf8'));"
             "process.stdout.write(JSON.stringify(g.filter(x=>K.dogrula(s,x).gecerli)));",
             os.path.join(REPO, "jenerator", "konfigurator.js"),
             os.path.join(REPO, "jenerator", "urunler", "olcuye-ozel-rulman.json")],
            input=json.dumps(setler), capture_output=True, text=True)
        if p.returncode != 0:
            print("OLCULEMEDI: sema kapisi kosulamadi: %s" % p.stderr[:300])
            sys.exit(OLCULEMEDI)
        setler = json.loads(p.stdout)
        print("sema kapisindan GECEN set: %d" % len(setler))

    tmp = tempfile.mkdtemp(prefix="rulman-olcum-")
    ayrisma, uretilemez, ok = [], 0, 0
    for i, s in enumerate(setler):
        bayraklar, sebep = server.d_bayraklari(aile, s)
        if bayraklar is None:
            print("  [RET ] eslem kapsami disi: %s" % sebep)
            continue
        stl = os.path.join(tmp, "r%d.stl" % i)
        p = subprocess.run([openscad, "-o", stl, "--export-format", "binstl"] +
                           server.OPENSCAD_EK_BAYRAKLAR + bayraklar + [scad],
                           capture_output=True, timeout=600)
        h = p.stderr.decode("utf-8", "replace")
        gercek = (p.returncode == 0 and os.path.exists(stl))
        if gercek:
            ok += 1
        elif "ERROR: Assertion" in h or "assert" in h.lower():
            uretilemez += 1
        else:
            print("  [HATA] derleme: %s" % h.strip().splitlines()[-1][:120])
            sys.exit(OLCULEMEDI)
        tahmin = kapali_form(s["ic_cap"], s["dis_cap"], s["genislik"], s["eleman"])
        if tahmin != gercek:
            ayrisma.append((s, "kapali-form=%s" % tahmin, "motor=%s" % gercek))

    olculen = ok + uretilemez
    print("\nOLCUM: %d set | RENDER EDILEN %d | uretilir %d | uretilemez(422) %d"
          % (len(setler), olculen, ok, uretilemez))
    print("KAPALI FORM ile AYRISMA: %d" % len(ayrisma))
    for x in ayrisma[:10]:
        print("  ", x)
    # 🔴 SIFIR-OLCUM FAIL-CLOSED ([[hukum-yanlis-birimde]] · onizleme/test/eslem-olcum.py
    # emsali): hukum satiri "uretilemez = 0" yaziyorsa bu ya "hicbiri uretilemez degil"
    # ya da "HIC OLCULMEDI" demektir; ikisi ayni cikis koduna dusmemeli. --sema-kapisi
    # kolunda sema HER SEYI reddederse setler bosalir ve eski kod SESSIZ YESIL verirdi —
    # yani satisa acma karari OLCULMEMIS bir sifira dayanabilirdi.
    if olculen == 0:
        print("OLCULEMEDI: render edilen set 0 — hukum verilemez "
              "(sema kapisi tum izgarayi reddetmis ya da --set 0 verilmis olabilir)")
        sys.exit(OLCULEMEDI)
    if a.sema_kapisi:
        print("SEMA KAPISI HUKMU: %d olculen sette uretilemez = %d (beklenen 0)"
              % (olculen, uretilemez))
        sys.exit(1 if uretilemez else 0)
    sys.exit(1 if ayrisma else 0)


if __name__ == "__main__":
    sys.exit(main())

"""K320 NOBETCISI — kapinin RED METNINDEKI kume, KARARI VEREN yapidan TURETILIR mi?

=== NEDEN VAR (olculmus ariza, 27 Agu 2026) ===
`mimar-icra-kapisi.py` red metninde "SERBEST / REDDEDILEN" kumelerini ELLE sayiyordu.
O metin, karari veren yapidan AYRISTI ve TABAN OLCUMU **DRIFT=9** cikti:
  * python ekseni (2): makine `defter-rotasyon.py` + `kutu-arsivle.py` cagrilarini
    20 Agu'dan (K258) beri GECIRIYORDU; metin "yalniz IKI komut serbest" diyordu.
  * olcum ekseni (7): makine 16 komut reddediyordu; metin 9 tanesini sayiyordu
    (df / file / memory_pressure / stat / sysctl / top / vm_stat metinde YOKTU).
BEDEL: `defter-kota-kapisi.py` defter tavani asilinca CARE olarak
`defter-rotasyon.py ... --tavan-kaynaktan --isaretciye-indir` basiyor. Mimar bu careyi
kosmak isteyip RED METNINI okudu, "care oteki kapida olu" hukmunu verdi ve defter UC
KOSUM boyunca tavanin USTUNDE kaldi — oysa cagri O TARIHTE ZATEN GECIYORDU. Kapi dogru
karar verirken YANLIS BILGI basti; maliyet, yanlis kararla ayniydi.

=== NE OLCER (kabul) ===
  A1  python ekseni: red metni, `_py_izinli`nin okudugu HER araci ADIYLA aniyor mu?
  A2  olcum ekseni: red metni, OLCUM_KOMUTLARI'nin HER uyesini aniyor mu?
  A3  🔴 TERS YON (28 Agu, K320Merge): red metni makinenin IZIN VERMEDIGI bir sey
      ANIYOR mu? A1/A2 yalniz `makine ⊆ metin` olcer; `metin ⊆ makine` olculmedigi
      surece metne ELLE fazladan bir ad eklemek NOBETCIYI GECER. Olculdu: bu
      nobetcinin ILK surumunde "serbest kumeye yalniz red metninde gorunen sahte
      arac ekle" mutanti 9/9 YESIL gecti — yani kor nokta VARDI. A3/A4 metnin
      ILGILI PARCASINI cikarip TURETILMIS dizgeye BIREBIR esitler; parcaya bir sey
      eklemek/cikarmak artik iki yonde de KIRMIZI yakar.
  A4  A3'un olcum ekseni karsiligi (OLCUM_KOMUTLARI parcasi BIREBIR esit mi).
  B1  CAGRI YERI: kapi BETIK olarak kosuldugunda CARE gercekten GECIYOR mu?
      ([[kapinin-menzili-cagri-yeridir]] — metinde ad gormek, o adin KARARDA
      okundugunu KANITLAMAZ.)
  B2  CAGRI YERI: kume DISI bayrak (--tavan-sayi) hala RED mi? (kova gevsemedi)
  M1  OLDURUCU MUTANT: `defter-rotasyon.py` kovadan DUSURULUR ->
      (a) CARE cagrisi RED'e doner VE (b) adi metinden SILINIR. IKISI BIRDEN
      donmezse tek kaynak YOKTUR (biri hala ikinci kopyadan besleniyordur).
  M2  KOMSU MUTANT: `kutu-arsivle.py` dusurulur -> CARE cagrisi HALA GECER, ama
      kutu-arsivle adi metinden DUSER. Kume ADIL: tek anahtar hepsini kapatmiyor.
  M3  OLCUM MUTANT: OLCUM_KOMUTLARI'na uydurma komut eklenir -> metinde GORUNUR.
  M5  TERS-YON MUTANT: red metnine, makinenin izin VERMEDIGI sahte bir arac adi
      ELLE eklenir -> A3 kolu KIRMIZI yanmali. M5, A3'un ta kendisini kullanir
      (ayri bir ikinci kontrol yazilsaydi o da ayrisirdi).
  M4  KONTROL (negatif): kaynak DEGISMEDEN kosulur -> hicbir kol kirmizi olmaz.
      M4 olmadan "mutant kirmizi yakti" bulgusu, kopyalama duzeneginin kendi
      arizasindan ayirt EDILEMEZDI ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).

Her mutant icin AYRICA "mutant kaynaga ULASTI MI" olculur (degisiklik sayisi == 1 ve
mutant kaynak tabandan FARKLI); ulasmayan mutant KIRMIZI sayilir, yesil DEGIL.

Gecici mutant kopyalari git-DISI tempdir'e yazilir (repo agacina iz birakilmaz).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

ARACLAR = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(ARACLAR, "mimar-icra-kapisi.py")
ANA_TP = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/ana.jsonl"

CARE = ("python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py "
        "/Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md "
        "--tavan-kaynaktan --isaretciye-indir")
KUME_DISI = ("python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py "
             "/Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md "
             "--tavan-sayi 130")
OLCUM_CAGRISI = "tail -5 /Users/okan/dev/pruvo/DEVAM.md"

sonuclar = []


def kaydet(ad, gecti, ayrinti=""):
    sonuclar.append((ad, gecti, ayrinti))


def kapi_kos(kapi_yolu, komut):
    """Kapiyi BETIK olarak kosar. Doner: ('GECTI'|'RED'|'COKTU', sebep_metni).

    'COKTU' RED'den AYRI tutulur: ilk surumde ikisi birlestirilmisti ve import'ta
    coken bir kopya "RED" diye okunuyordu ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
    """
    girdi = {"tool_name": "Bash", "tool_input": {"command": komut},
             "cwd": "/Users/okan/dev/pruvo", "transcript_path": ANA_TP}
    ortam = dict(os.environ)
    # Mutant kopya tempdir'de duruyor; kardes modul `mimar_kimlik` tools/'ta.
    ortam["PYTHONPATH"] = ARACLAR
    p = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(girdi),
                       capture_output=True, text=True, env=ortam)
    cikti = p.stdout.strip()
    if cikti:
        try:
            veri = json.loads(cikti)
        except Exception:
            return "COKTU", "stdout JSON degil: " + cikti[:160]
        ozel = veri.get("hookSpecificOutput") or {}
        if ozel.get("permissionDecision") == "deny":
            return "RED", ozel.get("permissionDecisionReason", "")
        return "COKTU", "beklenmedik karar: " + str(ozel.get("permissionDecision"))
    if p.returncode != 0:
        satirlar = [s for s in p.stderr.strip().splitlines() if s.strip()]
        return "COKTU", (satirlar[-1] if satirlar else "rc=" + str(p.returncode))[:200]
    return "GECTI", ""


def modul_yukle(kapi_yolu, ad):
    ortam_yolu = list(sys.path)
    sys.path.insert(0, ARACLAR)
    try:
        spec = importlib.util.spec_from_file_location(ad, kapi_yolu)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul
    finally:
        sys.path[:] = ortam_yolu


# --- TERS YON (A3/A4): metnin ILGILI PARCASI, turetilmis dizgeye BIREBIR esit mi?
# Parca, GEREKCE_SONU icindeki SABIT komsu metinlerle sinirlanir. Sinir bulunamazsa
# hukum "OLCULEMEDI"dir ve KIRMIZI sayilir (fail-closed) — bir gun metin yeniden
# yazilirsa kol sessizce yesile donmez.
PY_ON, PY_ARKA = "python YALNIZ şunlar: ", "; /.claude/worktrees/"
OLCUM_ON, OLCUM_ARKA = "filament, curl, ", ", node --check"


def parca(metin, on, arka):
    """on...arka arasindaki TEK parcayi dondurur; sinirlar tekil degilse None."""
    if metin.count(on) != 1 or metin.count(arka) != 1:
        return None
    bas = metin.index(on) + len(on)
    son = metin.index(arka)
    if son <= bas:
        return None
    return metin[bas:son]


def ters_yon(modul):
    """(py_uyumlu, olcum_uyumlu, ayrinti) — A3/A4'un ORTAK govdesi. M5 de bunu cagirir."""
    metin = modul.GEREKCE_SONU
    p_py = parca(metin, PY_ON, PY_ARKA)
    p_ol = parca(metin, OLCUM_ON, OLCUM_ARKA)
    b_py = modul.serbest_python_metni()
    b_ol = modul.olcum_komut_metni()
    ayrinti = []
    if p_py is None:
        ayrinti.append("py parcasi OLCULEMEDI (sinir metni tekil degil)")
    elif p_py != b_py:
        ayrinti.append("py FAZLASI/EKSIGI: " + repr(p_py.replace(b_py, "<TURETILMIS>"))[:110])
    if p_ol is None:
        ayrinti.append("olcum parcasi OLCULEMEDI (sinir metni tekil degil)")
    elif p_ol != b_ol:
        ayrinti.append("olcum FAZLASI/EKSIGI: " + repr(p_ol.replace(b_ol, "<TURETILMIS>"))[:110])
    return (p_py == b_py, p_ol == b_ol, " · ".join(ayrinti) or "parcalar TURETILMISE BIREBIR ESIT")


def kisa_adlar(modul):
    """Kapinin KARAR VEREN yapisindan serbest arac adlari (ikinci liste TUTULMAZ)."""
    adlar = {modul.DURUM_YOL, modul.D1_YOL}
    adlar |= set(modul.DEFTER_BAKIMI_BAYRAKLARI.keys())
    return {y.rsplit("/", 1)[-1] for y in adlar}


# ---------------------------------------------------------------- A) TURETILMISLIK
K = modul_yukle(KAPI, "kapi_taban")
metin = K.GEREKCE_SONU

bekleyen_py = sorted(kisa_adlar(K))
eksik_py = [a for a in bekleyen_py if a not in metin]
kaydet("A1 python ekseni: makinedeki HER arac red metninde",
       not eksik_py,
       "makine=%d metinde_eksik=%s" % (len(bekleyen_py), eksik_py or "YOK"))

eksik_olcum = sorted(k for k in K.OLCUM_KOMUTLARI if k not in metin)
kaydet("A2 olcum ekseni: OLCUM_KOMUTLARI'nin HER uyesi red metninde",
       not eksik_olcum,
       "makine=%d metinde_eksik=%s" % (len(K.OLCUM_KOMUTLARI), eksik_olcum or "YOK"))

py_uyumlu, olcum_uyumlu, ters_ayrinti = ters_yon(K)
kaydet("A3 TERS YON: red metninin python parcasi TURETILMISE BIREBIR esit",
       py_uyumlu, ters_ayrinti)
kaydet("A4 TERS YON: red metninin olcum parcasi TURETILMISE BIREBIR esit",
       olcum_uyumlu, ters_ayrinti)

# ---------------------------------------------------------------- B) CAGRI YERI
hukum, sebep = kapi_kos(KAPI, CARE)
kaydet("B1 CAGRI YERI: kota kapisinin bastigi CARE gecer", hukum == "GECTI", "hukum=" + hukum)

hukum_disi, sebep_disi = kapi_kos(KAPI, KUME_DISI)
kaydet("B2 CAGRI YERI: kume DISI bayrak (--tavan-sayi) RED kalir",
       hukum_disi == "RED", "hukum=" + hukum_disi)

hukum_olcum, sebep_olcum = kapi_kos(KAPI, OLCUM_CAGRISI)
turetilmis_gorunur = all(a in sebep_olcum for a in bekleyen_py)
kaydet("B3 RED sebebi okuyana TAM kumeyi gosterir (tail reddinde)",
       hukum_olcum == "RED" and turetilmis_gorunur,
       "hukum=%s tam_kume=%s" % (hukum_olcum, turetilmis_gorunur))

# ---------------------------------------------------------------- MUTASYONLAR
with open(KAPI) as f:
    TABAN_KAYNAK = f.read()

MUTANTLAR = (
    # (ad, ara, koy, care_beklenen, metinden_dusmesi_beklenen_ad)
    ("M1 OLDURUCU: defter-rotasyon kovadan dusuruldu",
     "    DEFTER_ROTASYON_YOL: frozenset((\"--tavan-kaynaktan\", \"--isaretciye-indir\")),\n",
     "",
     "RED", "defter-rotasyon.py"),
    ("M2 KOMSU: kutu-arsivle kovadan dusuruldu",
     "    KUTU_ARSIVLE_YOL: frozenset((\"--kuru\",)),\n",
     "",
     "GECTI", "kutu-arsivle.py"),
)

with tempfile.TemporaryDirectory(prefix="pruvo-k320-") as gecici:
    for ad, ara, koy, care_beklenen, dusen_ad in MUTANTLAR:
        adet = TABAN_KAYNAK.count(ara)
        if adet != 1:
            kaydet(ad, False, "MUTANT ULASMADI — capa %d kez bulundu (1 bekleniyordu)" % adet)
            continue
        mutant_kaynak = TABAN_KAYNAK.replace(ara, koy, 1)
        if mutant_kaynak == TABAN_KAYNAK:
            kaydet(ad, False, "MUTANT ULASMADI — kaynak DEGISMEDI")
            continue
        yol = os.path.join(gecici, "mutant.py")
        with open(yol, "w") as f:
            f.write(mutant_kaynak)

        hukum_m, _ = kapi_kos(yol, CARE)
        mutant_modul = modul_yukle(yol, "kapi_mutant_" + ad[:2])
        metin_m = mutant_modul.GEREKCE_SONU
        ad_dustu = dusen_ad not in metin_m

        gecti = (hukum_m == care_beklenen) and ad_dustu
        kaydet(ad, gecti,
               "CARE=%s (beklenen %s) · '%s' metinden dustu=%s"
               % (hukum_m, care_beklenen, dusen_ad, ad_dustu))

    # M3 — olcum ekseni gercekten turetilmis mi?
    UYDURMA = "zzolcum"
    ara3 = "    \"wc\", \"head\", \"tail\", \"sed\", \"awk\", \"sort\", \"stat\", \"file\",\n"
    if TABAN_KAYNAK.count(ara3) != 1:
        kaydet("M3 OLCUM: kumeye eklenen komut metinde gorunur", False,
               "MUTANT ULASMADI — capa bulunamadi")
    else:
        mutant3 = TABAN_KAYNAK.replace(
            ara3, ara3.rstrip("\n") + " \"" + UYDURMA + "\",\n", 1)
        yol3 = os.path.join(gecici, "mutant3.py")
        with open(yol3, "w") as f:
            f.write(mutant3)
        m3 = modul_yukle(yol3, "kapi_mutant_3")
        kaydet("M3 OLCUM: kumeye eklenen komut metinde gorunur",
               UYDURMA in m3.GEREKCE_SONU,
               "'%s' metinde=%s" % (UYDURMA, UYDURMA in m3.GEREKCE_SONU))

    # M5 — TERS-YON MUTANTI: makinenin izin VERMEDIGI bir arac adi red metnine ELLE
    # eklenir. A1/A2 bunu GECIRIR (makine ⊆ metin bozulmaz); oldurmesi gereken kol A3'tur.
    SAHTE = "python3 tools/sahte-arac.py"
    ara5 = ("\"gh, ls, grep, jq, echo, cat; python YALNIZ şunlar: \" "
            "+ serbest_python_metni() +\n")
    if TABAN_KAYNAK.count(ara5) != 1:
        kaydet("M5 TERS YON: metne elle eklenen sahte arac A3'u KIRMIZI yakar", False,
               "MUTANT ULASMADI — capa bulunamadi")
    else:
        mutant5 = TABAN_KAYNAK.replace(
            ara5,
            ara5.rstrip("\n") + " \" · '" + SAHTE + "'\" +\n", 1)
        yol5 = os.path.join(gecici, "mutant5.py")
        with open(yol5, "w") as f:
            f.write(mutant5)
        m5 = modul_yukle(yol5, "kapi_mutant_5")
        m5_py, m5_olcum, m5_ayrinti = ters_yon(m5)
        # A1 hala GECMELI (makine ⊆ metin bozulmadi) — kolun A3 oldugunu KANITLAR.
        m5_a1 = all(a in m5.GEREKCE_SONU for a in bekleyen_py)
        kaydet("M5 TERS YON: metne elle eklenen sahte arac A3'u KIRMIZI yakar",
               (not m5_py) and m5_a1,
               "A3=%s (KIRMIZI olmali) · A1=%s (yesil kalmali) · %s"
               % ("KIRMIZI" if not m5_py else "yesil", "yesil" if m5_a1 else "KIRMIZI",
                  m5_ayrinti[:90]))

    # M4 — NEGATIF KONTROL: kaynak degismeden ayni duzenekle kosulur.
    yol4 = os.path.join(gecici, "kontrol.py")
    with open(yol4, "w") as f:
        f.write(TABAN_KAYNAK)
    hukum4, _ = kapi_kos(yol4, CARE)
    m4 = modul_yukle(yol4, "kapi_kontrol")
    m4_py, m4_olcum, _ = ters_yon(m4)
    m4_temiz = (hukum4 == "GECTI"
                and all(a in m4.GEREKCE_SONU for a in bekleyen_py)
                and m4_py and m4_olcum)
    kaydet("M4 KONTROL: mutasyonsuz kopya HER kolda taban gibi davranir",
           m4_temiz, "CARE=%s A3=%s A4=%s" % (hukum4, m4_py, m4_olcum))

# ---------------------------------------------------------------- HUKUM
print("")
gecen = 0
for ad, gecti, ayrinti in sonuclar:
    damga = "OK  " if gecti else "KIRMIZI"
    gecen += 1 if gecti else 0
    print("%-7s %-58s | %s" % (damga, ad, ayrinti))

print("")
print("SERBEST_KUME_TEKKAYNAK: VAKA=%d GECEN=%d KIRMIZI=%d"
      % (len(sonuclar), gecen, len(sonuclar) - gecen))
sys.exit(0 if gecen == len(sonuclar) else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/yayin-gecikme-test.py — yayin gecikme nobetcisinin CURUTME (mutasyon) araci.

NE OLCER: "kabul testi YESIL" demek "nobetci CANLI" demek DEGILDIR. Bu arac nobetciyi
(ve kablolandigi durum.py / deploy.yml'i) BILEREK bozar ve kabul testinin GERCEKTEN
kirmizi yandigini — ve HANGI EKSENIN yandigini — olcer.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]):
  * her mutant kosumunda IDDIA SAYISI taban kosumla AYNI olmali — sayi dususu "mutant
    testi cokertti" demektir ve o kirmizi bir OLCUM DEGILDIR (cokme kirmiziyla karisir);
  * kirmizi EKSEN KODLARI kumesi mutantin BEYANIYLA karsilastirilir.

🔴 OLCUT, HER MUTANTIN KENDI KAYDINDA — TEK IZINLI DEGER: ESIT.
   Kirmizi kume BEYANA TAM ESIT olmali. Fazladan kirmizi da KUSURDUR: "bu mutant su
   ekseni yakar" hukmu ancak boyle nobet altindadir. Gevsek (KAPSAR) bir olcut YOKTUR;
   birden fazla eksen dusuren mutantlar eksenlerin HEPSINI beyan eder ve GEREKCESINI
   yazar.

🔴 BEYAN EDILMIS SURVIVOR YASAK ([[beyan-edilmis-survivor]]): Y1–Y8'in HER BIRI icin
   kirmizi kumesi TAM OLARAK {o eksen} olan en az bir mutant vardir; asagidaki
   "TEK-KIRMIZI HARITASI" bunu kosumda CALISTIRARAK dogrular. Ayirt edici mutanti
   olmayan bir eksen AYRI IDDIA sayilamaz.

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]] — `finally` ile geri alma deseni bu evde YASAK).
   Kosum basinda ve sonunda TUM kaynaklarin sha256'lari karsilastirilir; deploy.yml de
   bu listededir (aynadaki kopyasi mutasyonlanir, DEPODAKI dosyaya dokunulmaz).

🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/yayin-gecikme-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontroller YESIL + her eksenin tek-kirmizi mutanti
VAR + canli kaynaklar sha256 olarak DEGISMEDI.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

NOBETCI = "yayin-gecikme-nobeti.py"
TEST = "yayin-gecikme-test.py"
DURUM = "durum.py"
SUZGEC = "icra-suzgeci.py"
IS_AKISI = "is-akisi-kapisi.py"
DEPLOY = "deploy.yml"                     # .github/workflows/ altinda
# 🔴 5 Agu 2026 SERIT AYRIMI: kabul testinin adimi (serit B) nobet.yml'e TASINDI
# (bloklamayan joblarin kirmizisi yayin kosumunun rengini boyamasin diye,
# [[hukum-yanlis-birimde]]). Ayna agacta IKISI DE bulunmali: Y4 hem "canli kol
# CI'da kosmuyor" hem "kabul testi BLOKLAMAYAN seritte kosuyor" der.
NOBET = "nobet.yml"                       # .github/workflows/ altinda

AYNA_TOOLS = (NOBETCI, TEST, DURUM, SUZGEC, IS_AKISI)
FIKSTUR = os.path.join(TOOLS, "fikstur", "yayin-gecikme")
DEPLOY_YOL = os.path.join(ROOT, ".github", "workflows", DEPLOY)
NOBET_YOL = os.path.join(ROOT, ".github", "workflows", NOBET)
DOKUNULMAZ = ([os.path.join(TOOLS, a) for a in AYNA_TOOLS]
              + [DEPLOY_YOL, NOBET_YOL])

EKSENLER = ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7", "Y8", "Y9")

FAILS = []


def check(mesaj, kosul, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────────────
# MUTANTLAR — (kod, aciklama, hedef, [(bulunacak, yerine), ...], beyan, olcut)
#   hedef: AYNA_TOOLS'tan bir dosya adi ya da DEPLOY
#   beyan: kirmizi beklenen EKSEN kodlari ([] = KONTROL mutanti, YESIL kalmali)
# ─────────────────────────────────────────────────────────────────────────────────────
M1 = ("M1", "ESIK GEVSETME: tikanma esikleri devre disi (tikanma sessizlesir)",
      NOBETCI,
      # Capalar SATIR BASINA sabitlenir: ayni sayilar modul dokumaninda da geciyor.
      [("\nTIKALI_YAS_DK = 65\n", "\nTIKALI_YAS_DK = 100000\n"),
       ("\nTIKALI_HATA_ZINCIR = 4\n", "\nTIKALI_HATA_ZINCIR = 999\n")],
      # CAPRAZ (gerekce): zincir esigini oldurmek yalniz icerik ekseninin fiksturlerini
      # (Y1) degil, `bugun-build-dustu` KORELME kanarisini da (Y5) dusurur — o kanarinin
      # hukmu TAM DA hata zincirinden gelir. Iki eksen ayrik degil: ayni esik ikisini de
      # tasiyor.
      ["Y1", "Y5"], "ESIT")

M2 = ("M2", "OLCULEMEDI -> YESIL: ag/yetki yoklugu 'sorun yok' diye okunuyor",
      NOBETCI,
      [("        return \"OLCULEMEDI\", SINIF_RC[\"OLCULEMEDI\"], [str(e)], None",
        "        return \"AKIYOR\", 0, [str(e)], None")],
      # CAPRAZ (gerekce): ayni bozulma hem OLCULEMEDI fiksturlerini (agsiz/yetkisiz,
      # Y1) hem SOZLESME'nin fail-closed nobetini (Y2) hem de KABUL vaka 5'i (bos
      # kosum listesi fail-closed, Y8) dusurur; ucu de AYNI olguyu (olculemedi'nin
      # yesile dusmesi) olcer, ayrik degiller.
      ["Y1", "Y2", "Y8"], "ESIT")

M3 = ("M3", "IPTAL = HATA: eszamanlilik iptali TIKANMA sayiliyor (yanlis alarm)",
      NOBETCI,
      [("HATA_SONUCLARI = (\"failure\", \"startup_failure\", \"timed_out\", "
        "\"action_required\")",
        "HATA_SONUCLARI = (\"failure\", \"startup_failure\", \"timed_out\", "
        "\"action_required\", \"cancelled\")")],
      # CAPRAZ (gerekce): YAYINSIZ_SONUCLARI bu tuple'dan TURETILIR (ikiz tanim YOK), yani
      # ayni mutasyon EKSEN 3'un sinifini da kirletir. Sonuc: `dagilmis-hatalar-saglikli`
      # kanarisi (Y1) + "cancelled zincire girmesin" sozlesme nobeti (Y2) + EKSEN 3'un
      # sinif iddiasi (Y9) BIRLIKTE duser. Uc kirmizi da AYNI olgunun sonucudur.
      ["Y1", "Y2", "Y9"], "ESIT")

M4 = ("M4", "BIRIKME SIFIRLAMA: `ahead_by` okunmuyor (bekleyen icerik GORUNMEZ)",
      NOBETCI,
      [("    geride = g[\"ahead_by\"]", "    geride = 0")],
      # CAPRAZ (gerekce): `ahead_by` icerige dair HER olcumun UST AKISIDIR. Sifirlaninca
      # icerik ekseni (Y1), `bugun-build-dustu` korelme kanarisi (Y5) ve yas TABANI
      # olcumu (Y7 — yas artik hic hesaplanmiyor) ve EKSEN 3 (Y9 — yas kapisinin
      # arkasindadir) AYNI ANDA duser. Dort eksen de ayni fiziksel olgunun (bekleyen
      # icerigin gorunmez olmasi) sonucudur.
      ["Y1", "Y5", "Y7", "Y9"], "ESIT")

M5 = ("M5", "ZINCIR BASARIDA DURMUYOR: pencere boyu hatalar toplaniyor",
      NOBETCI,
      [("            else:\n                break\n        return n",
        "            else:\n                continue\n        return n")],
      ["Y1"], "ESIT")

M6 = ("M6", "SEKIL DOGRULAMASI YOK: API alani kaybolsa da nobetci tahmin yurutuyor",
      NOBETCI,
      [("KOSUM_ZORUNLU = (\"id\", \"status\", \"conclusion\", \"created_at\", "
        "\"run_started_at\",\n                 \"updated_at\", \"head_sha\", \"event\")",
        "KOSUM_ZORUNLU = ()")],
      ["Y1"], "ESIT")

M7 = ("M7", "ACLIK'ta VE -> VEYA: tek basina iptal zinciri alarm uretiyor",
      NOBETCI,
      [("    if eksen[\"iptal_zinciri\"] and eksen[\"yas_gecikme\"]:",
        "    if eksen[\"iptal_zinciri\"] or eksen[\"yas_gecikme\"]:")],
      # CAPRAZ (gerekce): kural VEYA'ya donunce `yas_gecikme` TEK BASINA ACLIK uretir ve
      # ACLIK, TIKALI'dan ONCE dondugu icin EKSEN 3'un hukmunu de yutar (Y9 kanarisi
      # ACLIK'a duser). Ayni tek satir iki ekseni birden bozuyor.
      ["Y1", "Y9"], "ESIT")

M8 = ("M8", "YAS TABANI KALDIRILDI: ff-only ile gelen eski tarihli commit yasi sisiriyor",
      NOBETCI,
      [("        baslangic = max(en_eski, olcum[\"yayin_ani\"])",
        "        baslangic = en_eski")],
      ["Y7"], "ESIT")

M9 = ("M9", "TABAN KOSUM BASLANGICINA GERI DONDU (2 Agu'da olculen YANLIS ALARM)",
      NOBETCI,
      [("        baslangic = max(en_eski, olcum[\"yayin_ani\"])",
        "        baslangic = max(en_eski, olcum[\"son_basarili_baslangic\"])")],
      ["Y7"], "ESIT")

M10 = ("M10", "OMUR TAVANI DEVRE DISI: takilan kosum ekseni sessizlesiyor",
       NOBETCI,
       [("\nKOSUM_OMUR_TAVANI_DK = 128\n", "\nKOSUM_OMUR_TAVANI_DK = 100000\n")],
       ["Y8"], "ESIT")

V1 = ("V1", "TAVAN 75'E GERI CEKILDI: 86,6 dk NORMAL kosum yanlis alarm uretir "
           "(sahte alarm sinifi geri gelir — KABUL vaka 1)",
       NOBETCI,
       [("\nKOSUM_OMUR_TAVANI_DK = 128\n", "\nKOSUM_OMUR_TAVANI_DK = 75\n")],
       # Tek-yonlu: 75 < 86,6 oldugu icin OLCULEN normal omur (86,6) alarm uretir ->
       # "KONTROL takilan-kosum-normal" + KABUL vaka 1 + omur-ekseni sozlesmesi
       # (tavan > OLCULEN max) AYNI ANDA duser — ucu de Y8 eksenidir.
       ["Y8"], "ESIT")

V2 = ("V2", "TAVAN 200'E CIKARILDI: 143,5 dk GERCEK takilma kacirilir (alarm korlesir — "
           "KABUL vaka 2/3)",
       NOBETCI,
       [("\nKOSUM_OMUR_TAVANI_DK = 128\n", "\nKOSUM_OMUR_TAVANI_DK = 200\n")],
       # 200 > 143,5 oldugu icin gercek takilma (143,5/169,1) ve fiksturun 130 dk'lik
       # kosumu artık yakalanmaz -> KABUL vaka 2/3 + "VAKA (b) takilan-kosum-bekleyen-yok"
       # duser — hepsi Y8 eksenidir.
       ["Y8"], "ESIT")

V3 = ("V3", "BOS KOSUM LISTESI SESSIZ GECIRILDI: fail-closed kirildi (OLCULEMEDI yerine "
           "bos liste akar — KABUL vaka 5)",
       NOBETCI,
       [("    if not kosumlar:\n        raise", "    if False:\n        raise")],
       # Bos `workflow_runs` artik OlcumHatasi URETMEZ -> bos liste akar ve nobetci
       # "sorun yok" demese bile OLCULEMEDI sinifini KAYBEDER -> KABUL vaka 5 (fail-closed)
       # kirmizi yakar. Yalniz Y8: hicbir fikstur bos kosum listesi kullanmaz.
       ["Y8"], "ESIT")

M11 = ("M11", "OMUR EKSENI `ahead_by` KAPISININ ARKASINA ALINDI (kor nokta geri geliyor)",
       NOBETCI,
       [("    if eksen[\"sure_tavani\"]:", "    if eksen[\"sure_tavani\"] and olcum"
                                           ".get(\"geride\"):")],
       ["Y8"], "ESIT")

M12 = ("M12", "ETKIN SONUC KOSUM DUZEYINE DONDU (`deploy` isi yetkili degil)",
       NOBETCI,
       [("    if isler.get(YAYIN_ISI) == \"success\":",
         "    if kosum.get(\"conclusion\") == \"success\":")],
       # CAPRAZ (gerekce): EKSEN 3'un zinciri de ETKIN SONUC uzerinde sayilir; yetki
       # kosum duzeyine donunce Y9 kanarisinin son yayinlayan kosumu (genel `failure`,
       # deploy=success) kaybolur ve zincir/taban BIRDEN kayar.
       ["Y5", "Y9"], "ESIT")

M19 = ("M19", "IS DUZEYI OZ-NOBETI CURUDU: `yayinsiz` sinifi sozlesme vakasindan dusuruldu "
              "(kosum yesil + deploy skipped artik 'yayinlandi' sayilir)",
       NOBETCI,
       [("        ({\"conclusion\": \"success\"}, {YAYIN_ISI: \"skipped\"}, \"yayinsiz\"),",
         "        ({\"conclusion\": \"success\"}, {YAYIN_ISI: \"skipped\"}, \"success\"),")],
       # Y5'in AYIRT EDICI mutanti: yalnizca is-duzeyi SOZLESME nobetini bozar, hicbir
       # fiksturun hukmunu degistirmez ([[beyan-edilmis-survivor]]).
       ["Y5"], "ESIT")

M13 = ("M13", "`gh` STDERR'I OLDUGU GIBI DISARI CIKIYOR (sir/kimlik sizintisi)",
       NOBETCI,
       [("    metin = (ham or \"\").strip()\n    d = metin.lower()",
         "    metin = (ham or \"\").strip()\n    return metin\n    d = metin.lower()")],
       ["Y6"], "ESIT")

M14 = ("M14", "PANO KABLOSU KESILDI: durum.py bolum 9'u artik CAGIRMIYOR",
       DURUM,
       [("        yayin_satirlari = _yayin_gecikme_satirlari()",
         "        yayin_satirlari = []")],
       ["Y3"], "ESIT")

M15 = ("M15", "nobet.yml'de kabul testi adimi SILINDI (olu nobetci)",
       NOBET,
       [("        run: python3 tools/yayin-gecikme-test.py",
         "        run: python3 -c \"pass\"")],
       ["Y4"], "ESIT")

M16 = ("M16", "OLCULEN TAVAN CAPASI GEVSETILDI: esik nobeti kendi tabanindan koptu",
       NOBETCI,
       [("\nOLCULEN_SAGLIKLI_IPTAL_TAVANI = 5\n",
         "\nOLCULEN_SAGLIKLI_IPTAL_TAVANI = 7\n")],
       ["Y2"], "ESIT")

M17 = ("M17", "EKSEN 3 DEVRE DISI: yayinsiz zincir ekseni hep False -> 5 Agu'da olculen "
              "kor nokta (74 dk yayin durmasi, alarm YOK) geri gelir",
       NOBETCI,
       [("        \"yayinsiz_zinciri\": (olcum[\"ardisik_yayinsiz\"] >= "
         "TIKALI_YAYINSIZ_ZINCIR",
         "        \"yayinsiz_zinciri\": (False and olcum[\"ardisik_yayinsiz\"] >= "
         "TIKALI_YAYINSIZ_ZINCIR")],
       # TEK-KIRMIZI: sozlesme nobetleri (Y2) esikleri hala tutarli gorur — bozulan sey
       # esik DEGIL, eksenin KENDISIDIR; o yuzden yalniz Y9 duser.
       ["Y9"], "ESIT")

M18 = ("M18", "EKSEN 3 ESIGI ETKISIZ: TIKALI_YAYINSIZ_ZINCIR yukseltildi (esik gevsetme "
              "yoluyla ayni kor nokta)",
       NOBETCI,
       [("\nTIKALI_YAYINSIZ_ZINCIR = 2\n", "\nTIKALI_YAYINSIZ_ZINCIR = 999\n")],
       # CAPRAZ (gerekce): esik hata zinciri esiginin (4) USTUNE cikinca SOZLESME nobeti
       # de konusur ("daha genis sinifi daha GEC yakalar") -> Y2 ile Y9 BIRLIKTE duser.
       # Ayirt edici (yalniz Y9) mutant M17'dir; bu giris esik yuzeyini ayrica olcer.
       ["Y2", "Y9"], "ESIT")

# ── KONTROL MUTANTLARI (YESIL kalmali) ──────────────────────────────────────────────
# Surucu "her seye kirmizi yanan" gurultulu bir alarma donusmesin: anlam tasimayan
# degisiklikler bataryayi KIRMIZI yakmamali, yoksa yukaridaki "OLDU" hukumlerinin hicbiri
# mutasyonun kendisine atfedilemez (cokme kirmiziyla karisir).
K1 = ("K1", "ilgisiz: modul basligindaki bir kelime degisti (nobetci)",
      NOBETCI,
      [("KULLANIM\n========", "KULLANIM\n========\n")],
      [], "ESIT")

K2 = ("K2", "ilgisiz: fonksiyon arasina bos satir eklendi (nobetci)",
      NOBETCI,
      [("\ndef takilan_kosum(kosumlar, simdi):", "\n\ndef takilan_kosum(kosumlar, simdi):")],
      [], "ESIT")

K3 = ("K3", "ilgisiz: sabit yanina aciklama yorumu eklendi (nobetci)",
      NOBETCI,
      [("TASLAK_ISI = \"yayin\"", "TASLAK_ISI = \"yayin\"   # is adi — tek kaynak")],
      [], "ESIT")

K4 = ("K4", "ilgisiz: kabul testi basligindaki bir kelime degisti",
      TEST,
      [("    print(\"YAYIN GECIKME NOBETCISI — KABUL TESTI\")",
        "    print(\"YAYIN GECIKME NOBETCISI - KABUL TESTI\")")],
      [], "ESIT")

K5 = ("K5", "ilgisiz: EKSEN 3 sabitinin yanina aciklama yorumu eklendi (esik DEGISMEDI)",
      NOBETCI,
      [("TIKALI_YAYINSIZ_ZINCIR = 2\n",
        "TIKALI_YAYINSIZ_ZINCIR = 2   # olculen tavan 1 (5 Agu, 7 gun)\n")],
      [], "ESIT")

MUTANTLAR = (M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, V1, V2, V3, M11, M12, M13,
             M14, M15, M16, M17, M18, M19, K1, K2, K3, K4, K5)
OLCUTLER = ("ESIT",)

IDDIA_RE = re.compile(r"^IDDIA SAYISI:\s*(\d+)\s*$", re.M)
KIRMIZI_RE = re.compile(r"^KIRMIZI IDDIA:\s*(\S+)\s*$", re.M)


def kayitlari_dogrula():
    """Kayitlarin KENDI sekli FAIL-CLOSED suzulur: taninmayan olcut VARSAYILANA DUSMEZ."""
    hata = []
    kodlar = set()
    for kayit in MUTANTLAR:
        if len(kayit) != 6:
            hata.append("%r: kayit 6 alanli olmali (kod, aciklama, hedef, degisimler, "
                        "beyan, olcut)" % (kayit[0],))
            continue
        kod, _aciklama, hedef, _degisimler, beyan, olcut = kayit
        if kod in kodlar:
            hata.append("%s: MUKERRER mutant kodu" % kod)
        kodlar.add(kod)
        if olcut not in OLCUTLER:
            hata.append("%s: bilinmeyen olcut %r — TEK izinli olcut: %s"
                        % (kod, olcut, ", ".join(OLCUTLER)))
        if hedef not in (DEPLOY, NOBET) and hedef not in AYNA_TOOLS:
            hata.append("%s: bilinmeyen hedef %r" % (kod, hedef))
        for b in beyan:
            if b not in EKSENLER:
                hata.append("%s: bilinmeyen eksen kodu %r" % (kod, b))
    return hata


def ayna_kur(hedef):
    """Gecici aynaya KOPYALAR. Kaynak agaca YAZMA YOKTUR."""
    os.makedirs(os.path.join(hedef, "tools"))
    os.makedirs(os.path.join(hedef, ".github", "workflows"))
    for ad in AYNA_TOOLS:
        shutil.copy2(os.path.join(TOOLS, ad), os.path.join(hedef, "tools", ad),
                     follow_symlinks=True)
    shutil.copytree(FIKSTUR, os.path.join(hedef, "tools", "fikstur", "yayin-gecikme"))
    shutil.copy2(DEPLOY_YOL, os.path.join(hedef, ".github", "workflows", DEPLOY),
                 follow_symlinks=True)
    shutil.copy2(NOBET_YOL, os.path.join(hedef, ".github", "workflows", NOBET),
                 follow_symlinks=True)
    return hedef


def symlinkleri_bul(kok):
    bulunan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        for ad in altlar + dosyalar:
            y = os.path.join(dizin, ad)
            if os.path.islink(y):
                bulunan.append(os.path.relpath(y, kok))
    return bulunan


def mutasyonla(pristine, degisimler, kod):
    """Mutasyonu METNE uygular. Dayanak yoksa/coklu ise HARNESS BAYATTIR -> gurultulu
    duser; 'olctum' deyip hicbir sey olcmemek en kotu haldir."""
    metin = pristine
    for eski, yeni in degisimler:
        adet = metin.count(eski)
        if adet != 1:
            raise SystemExit(
                "HARNESS BAYAT (%s): mutasyon dayanagi %d kez bulundu (tam 1 olmali):\n%r\n"
                "(kaynak degismis olabilir — mutasyonu guncelle; yoksa bu arac HICBIR SEY "
                "olcmuyor demektir)" % (kod, adet, eski[:200]))
        metin = metin.replace(eski, yeni, 1)
    return metin


def _ayna_yolu(ayna, ad):
    if ad in (DEPLOY, NOBET):
        return os.path.join(ayna, ".github", "workflows", ad)
    return os.path.join(ayna, "tools", ad)


def kos(ayna, pristine, mutant=None):
    """Aynayi TEMIZ kaynaklarla YENIDEN KURAR, sonra (varsa) TEK mutanti yazar ve kabul
    testini kosturur. Doner: (cikis_kodu, iddia_sayisi|None, kirmizi_kod_kumesi, kuyruk).

    🔴 HER KOSUMDA TAM YENIDEN YAZIM: yalnizca mutasyonlanan dosyayi yazmak, bir onceki
    mutanti aynada BIRAKIR ve sonraki mutantlar iki bozulmayi birden tasir (yalanci
    "oldu" hukumleri). Mutant izolasyonu varsayim degil, her kosumda YENIDEN kurulur.
    """
    metinler = dict(pristine)
    if mutant:
        metinler.update(mutant)
    for ad, metin in metinler.items():
        with open(_ayna_yolu(ayna, ad), "w", encoding="utf-8") as f:
            f.write(metin)
    r = subprocess.run([sys.executable, os.path.join(ayna, "tools", TEST)],
                       capture_output=True, text=True, timeout=1800)
    cikti = (r.stdout or "") + (r.stderr or "")
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    mk = KIRMIZI_RE.search(cikti)
    ham = mk.group(1) if mk else ""
    kirmizi = set(k for k in ham.split(",") if k and k != "-")
    return r.returncode, iddia, kirmizi, cikti[-1800:]


def main():
    print("YAYIN GECIKME NOBETCISI — MUTASYON (CURUTME) HARNESS'I")
    print("hedef kabul testi: tools/yayin-gecikme-test.py (tam takim)")

    sekil = kayitlari_dogrula()
    if sekil:
        print("KAYIT SEKLI BOZUK — hicbir mutant kosulmadi:")
        for h in sekil:
            print("  ✘ %s" % h)
        return 1

    canli_once = {y: sha(y) for y in DOKUNULMAZ}
    pristine = {}
    for ad in AYNA_TOOLS:
        with open(os.path.join(TOOLS, ad), encoding="utf-8") as f:
            pristine[ad] = f.read()
    with open(DEPLOY_YOL, encoding="utf-8") as f:
        pristine[DEPLOY] = f.read()
    with open(NOBET_YOL, encoding="utf-8") as f:
        pristine[NOBET] = f.read()

    print("\n0) KAYNAK SHA256 (kosum BASI)")
    for y in DOKUNULMAZ:
        print("   %-26s %s" % (os.path.basename(y), canli_once[y]))

    tmp = tempfile.mkdtemp(prefix="yayin-gecikme-mutasyon-")
    try:
        ayna = ayna_kur(os.path.join(tmp, "ayna"))
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        # --- 1) TABAN -----------------------------------------------------------
        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, t_kirmizi, t_kuyruk = kos(ayna, pristine)
        taban_ok = check("taban kosumu YESIL (cikis 0, kirmizi iddia 0)",
                         t_rc == 0 and not t_kirmizi,
                         "cikis=%d kirmizi=%s" % (t_rc, sorted(t_kirmizi) or "-"))
        if not taban_ok:
            print("\n  --- taban ciktisinin kuyrugu ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: mutant kosumlari ANLAMSIZ olurdu — durduruluyor.")
            return 1
        if not check("taban IDDIA SAYISI okunabildi", t_iddia is not None,
                     "iddia=%s" % t_iddia):
            return 1
        print("   TABAN IDDIA SAYISI = %d  (capa DEGIL: kosumda olculdu)" % t_iddia)

        # --- 2) BATARYA ---------------------------------------------------------
        oldurucu = [m for m in MUTANTLAR if m[4]]
        kontroller = [m for m in MUTANTLAR if not m[4]]
        print("\n2) MUTASYON BATARYASI — %d kosum (%d kirmizi-beklentili, %d kontrol)"
              % (len(MUTANTLAR), len(oldurucu), len(kontroller)))
        matris = []
        tek_kirmizi = {}          # eksen -> [mutant kodlari] (kirmizi kume TAM {eksen})
        for kod, aciklama, hedef, degisimler, beyan, olcut in MUTANTLAR:
            metin = mutasyonla(pristine[hedef], degisimler, kod)
            rc, iddia, kirmizi, kuyruk = kos(ayna, pristine, {hedef: metin})
            sayi_ok = (iddia == t_iddia)
            if beyan:
                eksik = [b for b in beyan if b not in kirmizi]
                fazla = sorted(kirmizi - set(beyan))
                gecti = sayi_ok and rc == 1 and bool(kirmizi) and not eksik and not fazla
                detay = ("cikis=%d iddia=%s/%d kirmizi=%s olcut=%s"
                         % (rc, iddia, t_iddia, ",".join(sorted(kirmizi)) or "-", olcut))
                if eksik:
                    detay += "  ⚠️ EKSIK: " + ",".join(eksik) + " (mutant SAG KALDI)"
                if fazla:
                    detay += ("  ⚠️ ESIT OLCUTU: BEYAN DISI FAZLA KIRMIZI -> "
                              + ",".join(fazla) + " (ya beyan ya iddia yanlis)")
                beklenti = "KIRMIZI/" + olcut
                if len(kirmizi) == 1:
                    tek_kirmizi.setdefault(sorted(kirmizi)[0], []).append(kod)
            else:
                gecti = sayi_ok and rc == 0 and not kirmizi
                detay = ("cikis=%d iddia=%s/%d kirmizi=%s"
                         % (rc, iddia, t_iddia, ",".join(sorted(kirmizi)) or "-"))
                beklenti = "YESIL"
            if not sayi_ok:
                detay += ("  ⚠️ IDDIA SAYISI TUTMUYOR -> mutant testi COKERTMIS olabilir; "
                          "bu 'kirmizi' OLCUM DEGIL")
            check("%-4s [%s] %s" % (kod, beklenti, aciklama), gecti, detay)
            if not gecti:
                print("       --- %s ciktisinin kuyrugu ---\n%s" % (kod, kuyruk))
            matris.append((kod, beklenti, rc, iddia,
                           ",".join(sorted(kirmizi)) or "-",
                           ",".join(beyan) or "-"))
            for y in DOKUNULMAZ:
                if sha(y) != canli_once[y]:
                    check("KAYNAK AGAC DEGISTI (ayna kacagi!) [%s -> %s]"
                          % (kod, os.path.basename(y)), False)

        print("\n   --- MUTASYON MATRISI ---")
        print("   %-5s %-14s %-6s %-9s %-16s %s"
              % ("kod", "beklenti", "cikis", "iddia", "kirmizi", "beyan"))
        for kod, beklenti, rc, iddia, kirmizi, beyan in matris:
            print("   %-5s %-14s %-6d %-9s %-16s %s"
                  % (kod, beklenti, rc, "%s/%d" % (iddia, t_iddia), kirmizi, beyan))

        # --- 3) TEK-KIRMIZI HARITASI (beyan edilmis survivor yasagi) ------------
        print("\n3) TEK-KIRMIZI HARITASI — her eksenin TEK BASINA yakilabilir mutanti")
        for eksen in EKSENLER:
            kodlar = tek_kirmizi.get(eksen, [])
            check("%s ekseninin TEK-KIRMIZI mutanti VAR" % eksen, bool(kodlar),
                  "mutant: %s" % (",".join(kodlar) or "YOK — bu eksen AYRI IDDIA "
                                                    "sayilamaz"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- 4) KAYNAK DOKUNULMAZLIGI ----------------------------------------------
    print("\n4) KAYNAK DOKUNULMAZLIGI (sha256, kosum SONU)")
    canli_sonra = {y: sha(y) for y in DOKUNULMAZ}
    for y in DOKUNULMAZ:
        check("%s sha256 BASTAKIYLE AYNI (mutant diskte kalmadi)" % os.path.basename(y),
              canli_sonra[y] == canli_once[y],
              "once=%s… sonra=%s…" % (canli_once[y][:16], canli_sonra[y][:16]))

    oldu = sum(1 for m in MUTANTLAR if m[4])
    print("\nSONUC: %d kirmizi-beklentili + %d kontrol mutanti kosuldu; %d eksen olculdu."
          % (oldu, len(MUTANTLAR) - oldu, len(EKSENLER)))
    if FAILS:
        print("KUSUR — %d:" % len(FAILS))
        for h in FAILS:
            print("  ✘ " + h)
        return 1
    print("TUM MUTANTLAR BEYANINA UYDU, KONTROLLER YESIL, HER EKSENIN TEK-KIRMIZI "
          "MUTANTI VAR ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())

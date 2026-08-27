#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/duzelt-uyum-mutasyon.py — `uyum` yazma yolu kabul testinin CURUTME araci.

NE OLCER: "kabul testi YESIL" demek "kapi CANLI" demek DEGILDIR. Bu arac
tools/duzelt.py ve tools/arama.py'yi BILEREK bozar ve tools/duzelt-uyum-test.py'nin
GERCEKTEN kirmizi yandigini — ve HANGI iddianin yandigini — olcer.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI ([[mutasyon-kaniti-yeniden-uretilebilir]]):
  * her mutant kosumunda IDDIA SAYISI taban kosumla AYNI olmali — sayi dususu "mutant
    testi cokertti" demektir ve o kirmizi bir OLCUM DEGILDIR (cokme kirmiziyla karisir);
  * kirmizi IDDIA KODLARI kumesi mutantin BEYANIYLA karsilastirilir.

🔴 OLCUT, HER MUTANTIN KENDI KAYDINDA:
  ESIT   -> kirmizi kume BEYANA TAM ESIT. Fazladan kirmizi da KUSURDUR: "bu mutant su
            ekseni yakar" hukmu ancak boyle nobet altindadir. VARSAYILAN budur.
  KAPSAR -> beyan ⊆ kirmizi. YALNIZ gerekcesi yazilmis capraz/bilesik bozulmalarda.

🔴 BEYAN EDILMIS SURVIVOR YASAK ([[beyan-edilmis-survivor]]): D1–D8'in HER BIRI icin
   kirmizi kumesi TAM OLARAK {o eksen} olan en az bir mutant vardir (asagidaki
   "TEK-KIRMIZI HARITASI" kosumda CALISTIRILARAK dogrulanir; eksik eksen = arac kirmizi).

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ.
   Kosum basinda ve sonunda kaynak sha256'lari karsilastirilir ([[mutasyon-diske-yazma-tuzagi]]).

🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/duzelt-uyum-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontroller YESIL + her eksenin tek-kirmizi
mutanti VAR + canli kaynaklar sha256 olarak DEGISMEDI.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
DUZELT = os.path.join(TOOLS, "duzelt.py")
ARAMA = os.path.join(TOOLS, "arama.py")
KOKEN = os.path.join(TOOLS, "gorsel_koken.py")
TEST = os.path.join(TOOLS, "duzelt-uyum-test.py")
AYNA_DOSYALAR = (DUZELT, ARAMA, KOKEN, TEST)

EKSENLER = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8")

# K325: ORTAK capa altyapisi (ikinci bir tane YAZILMADI). `mutant_metni` capayi hedefin
# KENDI kaynagindan turetir ve bes fail-closed kolla korur.
sys.path.insert(0, TOOLS)
import mutasyon_kopya  # noqa: E402

_TEMIZ_MODUL = {}


def temiz_modul(hedef):
    """TURETILMIS capalarin kapsam kaynagi — CANLI (mutasyonsuz) dosyadan yuklenir.

    🔴 Modul BIR KEZ yuklenir ve onbellege alinir: capa, olculen seyin MUTANT halinden
    etkilenmemeli (`mutasyon_kopya.kapsam_haritasi` doktrini). Ayna dosyalari mutantla
    yeniden yazildigi icin kapsami AYNADAN cozmek capayi olculene bagimli yapardi."""
    if hedef not in _TEMIZ_MODUL:
        yol = DUZELT if hedef == "duzelt" else ARAMA
        _TEMIZ_MODUL[hedef] = mutasyon_kopya.modul_yukle(yol, "k325_temiz_" + hedef)
    return _TEMIZ_MODUL[hedef]


class Turetilmis(tuple):
    """TURETILMIS CAPA isareti: `[(kapsam, desen, donusum), ...]` ciftleri tasir.

    🔴 NEDEN (27 Agu 2026, K325): ELLE yazili literal capa, hedef kaynak yeniden
    yazildiginda SESSIZCE eslesmez olur. M12'nin capasi bunu UC KEZ yasadi — dosyanin
    kendi yorumu 19 Agu'daki ikinci tazelemeyi anlatiyor, ucuncusu 27 Agu'da olculdu
    (`HARNESS BAYAT (M12): mutasyon dayanagi 0 kez bulundu`): `DEGISTIRILEBILIR` kumesi
    iki satira yayilip `boy_secenekleri` eklenince capa dustu ve surucu HICBIR SEY
    olcmedi. Ucuncu tekrar => tekil yama YASAK, sinif onarimi ZORUNLU.
    Capa artik hedefin KENDI kaynagindan turer: ortak altyapi
    `mutasyon_kopya.mutant_metni` (dort fail-closed kol) + K325'te eklenen BESINCI kol
    (modul duzeyi atama). IKINCI BIR ALTYAPI KURULMADI."""


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
#   hedef: "duzelt" | "arama"        beyan: kirmizi beklenen iddia kodlari ([] = KONTROL)
# ─────────────────────────────────────────────────────────────────────────────────────
M1 = ("M1", "TEKIL yolda `uyum` izinli alan kumesinden DUSURULDU (yol yariya kapanir)",
      "duzelt",
      [('        if alan not in DEGISTIRILEBILIR:\n'
        '            print("HATA: bilinmeyen/izinsiz alan: %s (izinli: %s)"',
        '        if alan not in DEGISTIRILEBILIR or alan == UYUM_ALANI:\n'
        '            print("HATA: bilinmeyen/izinsiz alan: %s (izinli: %s)"')],
      ["D1"], "ESIT")

M2 = ("M2", "TEKIL yolda MARKA TURETIM KABLOSU kesildi (marka bayat kalir)",
      "duzelt",
      [("        turetilen_marka = _uyum_marka_turet({args.id: degisiklikler})",
        "        turetilen_marka = {}")],
      ["D1"], "ESIT")

M3 = ("M3", "TURETIM MODEL jetonunu DUSURDU (arama: yalniz uyum[].marka) — arama metni "
      "sessizce daralir",
      "arama",
      [('        jetonlar = (uyum_marka_kanonik(oge.get("marka")),\n'
        '                    model_metin(oge.get("model")))',
        '        jetonlar = (uyum_marka_kanonik(oge.get("marka")),)')],
      ["D2"], "ESIT")

M4 = ("M4", "IKI-KAYNAK CATISMA KAPISI olduruldu (uyum+marka ayni cagrida gecer)",
      "duzelt",
      [("    catisan = []\n"
        "    for uid, alanlar in setler.items():\n"
        "        if UYUM_ALANI not in alanlar:",
        "    catisan = []\n"
        "    return catisan\n"
        "    for uid, alanlar in setler.items():\n"
        "        if UYUM_ALANI not in alanlar:")],
      ["D3"], "ESIT")

M5 = ("M5", "TOPLU kapinin KAPSAMI partinin ILK kaydina daraltildi (parti icindeki kirli "
      "kayit gorunmez olur)",
      "duzelt",
      [("        uyum_ihlal = _uyum_ihlalleri(urunler, set(setler) | set(alan_silmeler))",
        "        uyum_ihlal = _uyum_ihlalleri(\n"
        "            urunler, set(sorted(set(setler) | set(alan_silmeler))[:1]))")],
      ["D4"], "ESIT")

M6 = ("M6", "ATOMIKLIK BOZULDU: TOPLU yazim uyum kapisindan ONCE yapiliyor (red edilen "
      "parti diske sizar)",
      "duzelt",
      [("        uyum_ihlal = _uyum_ihlalleri(urunler, set(setler) | set(alan_silmeler))",
        "        _atomic_write(URUNLER, urunler)\n"
        "        uyum_ihlal = _uyum_ihlalleri(urunler, set(setler) | set(alan_silmeler))")],
      # CAPRAZ (gerekce): erken yazim hem "parti diske dokunmadi" (D4) hem "reddedilen
      # cagrida marka diskte degismedi" (D5) eksenini AYNI ANDA dusurur — iki eksen de
      # AYNI fiziksel olguyu (yazimin gate'ten once olmasi) olcer. Ayrik degiller, bu
      # yuzden ikisi birden BEYAN edilir (olcut yine ESIT: fazlalik KUSURDUR).
      ["D4", "D5"], "ESIT")

M7 = ("M7", "K5 IKIZ KAPISI olduruldu (arama: `marka` != turetilen kontrolu kalkti)",
      "arama",
      [("    turetilen = marka_uyumdan_turet(u)\n"
        "    mevcut = u.get(\"marka\")\n"
        "    if mevcut != turetilen:",
        "    turetilen = marka_uyumdan_turet(u)\n"
        "    mevcut = u.get(\"marka\")\n"
        "    if False:")],
      ["D5"], "ESIT")

M8 = ("M8", "`--alan-sil uyum` `marka`yi da DUSURDU (geri donus veri kaybina cevrildi)",
      "duzelt",
      [("        for uid, alanlar in alan_silmeler.items():\n"
        "            for alan in alanlar:\n"
        "                urunler[idx_by_id[uid]].pop(alan, None)",
        "        for uid, alanlar in alan_silmeler.items():\n"
        "            for alan in alanlar:\n"
        "                urunler[idx_by_id[uid]].pop(alan, None)\n"
        "                if alan == UYUM_ALANI:\n"
        "                    urunler[idx_by_id[uid]].pop(MARKA_ALANI, None)")],
      ["D6"], "ESIT")

M9 = ("M9", "KAPI KAPSAMI TUM KATALOGA genisletildi (ilgisiz eski ihlal mesru duzeltmeyi "
      "bloklar)",
      "duzelt",
      [("    for u in urunler:\n"
        "        if not isinstance(u, dict) or u.get(\"id\") not in idler:\n"
        "            continue\n"
        "        sebep = arama.uyum_sebebi(u)",
        "    for u in urunler:\n"
        "        if not isinstance(u, dict):\n"
        "            continue\n"
        "        sebep = arama.uyum_sebebi(u)")],
      ["D7"], "ESIT")

M10 = ("M10", "RC_ALTKATEGORI kodu RC_UYUM ile CAKISTIRILDI (cagiran hangi kapinin "
       "reddettigini ayirt edemez)",
       "duzelt",
       [("RC_ALTKATEGORI = 5", "RC_ALTKATEGORI = 7")],
       ["D8"], "ESIT")

M11 = ("M11", "TOPLU yolda MARKA TURETIM KABLOSU kesildi (marka bayat kalir, K5 patlar)",
       "duzelt",
       [("        turetilen_marka = _uyum_marka_turet(setler)",
         "        turetilen_marka = {}")],
       # Turetim kosmayinca yazim K5'ten geri doner: hem "toplu kabul" (D1) hem
       # "turetilen deger" (D2) ekseni ayni anda duser — ikisi de yazimin BASARISINA
       # bagli. Beyan ikisini birden tasir; olcut yine ESIT.
       ["D1", "D2"], "ESIT")

M12 = ("M12", "`uyum` DEGISTIRILEBILIR kumesinden tamamen CIKARILDI (yol yeniden kapali)",
       "duzelt",
       # 🔴 CAPA ARTIK ELLE YAZILI DEGIL (27 Agu, K325). Onceki iki literal capa da
       # bayatladi: 19 Agu'da `tavsiyeFilament` eklenince, 27 Agu'da kume iki satira
       # yayilip `boy_secenekleri` eklenince — ikisinde de 0 eslesme, arac HICBIR SEY
       # olcmedi. Capa hedefin KENDI kaynagindan turer: kapsam `DEGISTIRILEBILIR`
       # (modul duzeyi atama), desen `uyum` jetonunu tasiyan TEK satir, donusum o
       # jetonu (ve ardindaki ayraci) dusurur. Iddia DEGISMEDI: yalniz `uyum` kumeden
       # cikar, komsu alanlar durur. Kume yeniden bicimlenirse capa KENDILIGINDEN izler;
       # izlenemezse `CapaHatasi` -> HARNESS BAYAT (sessiz gecis YOK).
       Turetilmis([("DEGISTIRILEBILIR", r'"uyum"',
                    lambda s: s.replace('"uyum", ', "").replace(', "uyum"', ""))]),
       # CAPRAZ: alanin tumden kapanmasi `uyum` YAZAN her ekseni birden dusurur; ayirt
       # edici DEGILDIR, ama "kabul kumesi gercekten yuk tasiyor mu" sorusunu yanitlar.
       ["D1", "D2", "D3", "D4", "D8"], "ESIT")

# ── KONTROL MUTANTLARI (YESIL kalmali) ──────────────────────────────────────────────
# Surucu "her seye kirmizi yanan" gurultulu bir alarma donusmesin: anlam tasimayan
# degisiklikler bataryayi KIRMIZI yakmamali, yoksa yukaridaki "OLDU" hukumlerinin hicbiri
# mutasyonun kendisine atfedilemez (cokme kirmiziyla karisir).
K1 = ("K1", "ilgisiz: cikis kodu yorumunda kelime degisti (duzelt.py)",
      "duzelt",
      [("# cikis kodundan ayirt edebilir — \"rc != 0\" hepsini tek kovaya yigardi ve parti",
        "# cikis kodundan ayirt edebilir; \"rc != 0\" hepsini tek kovaya yigardi ve parti")],
      [], "ESIT")

K2 = ("K2", "ilgisiz: fonksiyon arasina bos satir eklendi (duzelt.py)",
      "duzelt",
      [("\ndef _uyum_rapor(ihlaller, kaynak):", "\n\ndef _uyum_rapor(ihlaller, kaynak):")],
      [], "ESIT")

K3 = ("K3", "ilgisiz: turetim docstring'inde kelime degisti (arama.py)",
      "arama",
      [("    IKIZ TANIM YASAGI: `marka` ile `uyum` ayni gercegi iki yerde tutar ve SESSIZCE",
        "    IKIZ TANIM YASAGI: `marka` ile `uyum` ayni gercegi iki yerde tutar ve SESSIZ")],
      [], "ESIT")

K4 = ("K4", "ilgisiz: alan adi sabitine aciklama yorumu eklendi (duzelt.py)",
      "duzelt",
      [('UYUM_ALANI = "uyum"', 'UYUM_ALANI = "uyum"          # alan adi — tek kaynak')],
      [], "ESIT")

MUTANTLAR = (M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12, K1, K2, K3, K4)

IDDIA_RE = re.compile(r"^IDDIA SAYISI:\s*(\d+)\s*$", re.M)
KIRMIZI_RE = re.compile(r"^KIRMIZI IDDIA:\s*(\S+)\s*$", re.M)


def ayna_kur():
    d = tempfile.mkdtemp(prefix="duzelt-uyum-mutasyon-")
    os.makedirs(os.path.join(d, "tools"))
    for yol in AYNA_DOSYALAR:
        shutil.copy2(yol, os.path.join(d, "tools", os.path.basename(yol)),
                     follow_symlinks=True)
    return d


def symlinkleri_bul(kok):
    bulunan = []
    for dizin, altlar, dosyalar in os.walk(kok):
        for ad in altlar + dosyalar:
            y = os.path.join(dizin, ad)
            if os.path.islink(y):
                bulunan.append(os.path.relpath(y, kok))
    return bulunan


def mutasyonla(pristine, degisimler, kod, mod=None):
    """Mutasyonu METNE uygular. Dayanak yoksa/coklu ise HARNESS BAYATTIR -> gurultulu
    duser; 'olctum' deyip hicbir sey olcmemek en kotu haldir.

    `degisimler` TURETILMIS ise capa ELLE yazili degildir: ortak altyapiya devredilir ve
    oradaki dort/bes fail-closed kol (kapsam YOK · blok tekil degil · capa tekil degil ·
    donusum ETKISIZ · modul atamasi tekil degil) `CapaHatasi` yukseltir. O hata da
    HARNESS BAYAT ile AYNI sinifta, ayni gurultuyle duser — sessiz gecis YOK."""
    if isinstance(degisimler, Turetilmis):
        if mod is None:
            raise SystemExit("HARNESS BAYAT (%s): turetilmis capa istendi ama hedef MODUL "
                             "yuklenmedi (kapsam cozulemez)" % (kod,))
        try:
            return mutasyon_kopya.mutant_metni(mod, pristine, list(degisimler))
        except mutasyon_kopya.CapaHatasi as e:
            raise SystemExit(
                "HARNESS BAYAT (%s): TURETILMIS capa cozulemedi -> %s\n"
                "(hedef kaynak degismis olabilir; capa ELLE yazili DEGIL, yine de "
                "cozulemiyorsa kapsam adi ya da desen bayattir — bu arac HICBIR SEY "
                "olcmuyor demektir)" % (kod, e))
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


def kos(ayna, pristine, mutant=None):
    """Aynayi TEMIZ kaynaklarla YENIDEN KURAR, sonra (varsa) TEK mutanti yazar ve kabul
    testini kosturur. Doner: (cikis_kodu, iddia_sayisi|None, kirmizi_kod_kumesi, kuyruk).

    🔴 HER KOSUMDA TAM YENIDEN YAZIM (bu harness'in ILK kosumunda OLCULEN kusur): once
    yalnizca mutasyonlanan dosya yaziliyordu, bu yuzden bir onceki mutantin BOZUK
    arama.py'si aynada KALIYORDU. Sonuc: M4'ten sonraki her mutant iki bozulmayi birden
    tasidi ve ILGISIZ kontrol mutantlari bile KIRMIZI yandi (yalanci "oldu" hukumleri).
    Mutant izolasyonu bir varsayim degil, her kosumda YENIDEN KURULAN bir olgudur."""
    metinler = dict(pristine)
    if mutant:
        metinler.update(mutant)
    for ad, metin in metinler.items():
        with open(os.path.join(ayna, "tools", ad), "w", encoding="utf-8") as f:
            f.write(metin)
    r = subprocess.run([sys.executable, os.path.join(ayna, "tools", "duzelt-uyum-test.py")],
                       capture_output=True, text=True, timeout=1800)
    cikti = (r.stdout or "") + (r.stderr or "")
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    mk = KIRMIZI_RE.search(cikti)
    ham = mk.group(1) if mk else ""
    kirmizi = set(k for k in ham.split(",") if k and k != "-")
    return r.returncode, iddia, kirmizi, cikti[-1800:]


def main():
    print("DUZELT `uyum` YAZMA YOLU — MUTASYON (CURUTME) HARNESS'I")
    print("hedef kabul testi: tools/duzelt-uyum-test.py (tam takim)")

    canli_once = {y: sha(y) for y in AYNA_DOSYALAR}
    pristine = {}
    for yol in AYNA_DOSYALAR:
        with open(yol, encoding="utf-8") as f:
            pristine[os.path.basename(yol)] = f.read()
    print("\n0) KAYNAK SHA256 (kosum BASI)")
    for yol in AYNA_DOSYALAR:
        print("   %-26s %s" % (os.path.basename(yol), canli_once[yol]))

    ayna = ayna_kur()
    try:
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        # --- 0b) K325 TURETILMIS CAPA KOLUNUN NOBETI --------------------------
        # 🔴 Kolun nobetcisi OLCTUGU SEYIN YANINDA durur (hafiza: capa altyapisi
        # yazildi ama vakalar tasinmadi -> borc gorunmez oldu). Ayri bir CI adimi
        # EKLENMEDI: bu surucu nerede kosarsa kol da orada olculur.
        oz = mutasyon_kopya.atama_kolu_oz_test(ayna)
        check("K325 turetilmis-capa kolu: 6 vaka (P1 · N1-N4 fail-closed · M1 hedef-kol atfi)",
              not oz, "basarisiz: %s" % (oz or "-"))

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
            dosya = "duzelt.py" if hedef == "duzelt" else "arama.py"
            # K325: TURETILMIS capa hedefin KENDI kaynagindan cozulur. Modul TEMIZ
            # kaynaktan yuklenir (mutasyon ONCESI) — `kapsam_haritasi` doktrini: capa,
            # olculen seyin mutant halinden ETKILENMEZ.
            metin = mutasyonla(pristine[dosya], degisimler, kod, mod=temiz_modul(hedef))
            rc, iddia, kirmizi, kuyruk = kos(ayna, pristine, {dosya: metin})
            sayi_ok = (iddia == t_iddia)
            if beyan:
                eksik = [b for b in beyan if b not in kirmizi]
                fazla = sorted(kirmizi - set(beyan)) if olcut == "ESIT" else []
                gecti = sayi_ok and rc == 1 and bool(kirmizi) and not eksik and not fazla
                detay = ("cikis=%d iddia=%s/%d kirmizi=%s olcut=%s"
                         % (rc, iddia, t_iddia, ",".join(sorted(kirmizi)) or "-", olcut))
                if eksik:
                    detay += "  ⚠️ EKSIK: " + ",".join(eksik) + " (mutant SAG KALDI)"
                if fazla:
                    detay += ("  ⚠️ ESIT OLCUTU: BEYAN DISI FAZLA KIRMIZI -> "
                              + ",".join(fazla) + " (ya beyan ya iddia yanlis)")
                beklenti = "KIRMIZI/" + olcut
                if kirmizi and len(kirmizi) == 1:
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
            for yol in AYNA_DOSYALAR:
                if sha(yol) != canli_once[yol]:
                    check("KAYNAK AGAC DEGISTI (ayna kacagi!) [%s -> %s]"
                          % (kod, os.path.basename(yol)), False)

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
        shutil.rmtree(ayna, ignore_errors=True)

    # --- 4) KAYNAK DOKUNULMAZLIGI ----------------------------------------------
    print("\n4) KAYNAK DOKUNULMAZLIGI (sha256, kosum SONU)")
    canli_sonra = {y: sha(y) for y in AYNA_DOSYALAR}
    for yol in AYNA_DOSYALAR:
        check("%s sha256 BASTAKIYLE AYNI (mutant diskte kalmadi)"
              % os.path.basename(yol), canli_sonra[yol] == canli_once[yol],
              "once=%s… sonra=%s…" % (canli_once[yol][:16], canli_sonra[yol][:16]))

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

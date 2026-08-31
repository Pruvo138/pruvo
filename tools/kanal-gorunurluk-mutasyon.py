#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KANAL/ATIF GORUNURLUGU NOBETCILERININ MUTASYON HARNESS'I.

  python3 tools/kanal-gorunurluk-mutasyon.py

NE ISE YARAR: `node shop/test/panel-atif.mjs` (45 iddia) ve
`python3 tools/kanal-kirilim-test.py` (41 iddia) YESIL yaniyor. "Yesil" tek basina
hicbir sey kanitlamaz — kanit, davranisi BOZUNCA iddianin KIRMIZI yanmasi VE ilgisiz
bir degisiklikte YESIL kalmasidir. Depo konvansiyonu: tools/panel-kaynak-mutasyon.py ·
tools/uretim-kaynak-mutasyon.py.

🔴 MUTASYON DAIMA GECICI AYNAYA uygulanir — calisma agacindaki kaynagi bozup `finally`
ile geri alma deseni bu evde YASAK (tek kesinti agacta deploy edilebilir bir MUTANT
birakir). Butun kaynak+test seti gecici dizine KOPYALANIR, mutant orada yasar, kosum
oradan yapilir; calisma agacindaki dosyalarin sha256'lari basta alinir ve HER kosumdan
sonra dogrulanir. Gecici dizin `finally` ile SILINIR (disk kurali).

🔴 HEDEF-KOL ATFI: her mutant HANGI test kolunun onu oldurmesi gerektigini beyan eder
(`kol`). Bir mutant "kirmizi yandi" ama YANLIS koldan yandiysa, o kol icin kanit
URETILMEMISTIR ([[sinif-adi-kol-adi-olarak-basilirsa-yanlis-alan-dogrulanir]]). Beklenen
kol kirmizi degilse mutant UYUSMAZ sayilir — toplam renk yetmez.

KABUL (cikis kodu degil, OLCULEN SAYI): her mutant icin BEKLENEN kol/durum ile
GERCEKLESEN birebir esit olmali. rc=1 (KIRMIZI) ile rc=3 (OLCULEMEDI: capa bulunamadi)
AYRI tutulur — ikisi de sifir disidir ama biri kanit, digeri kor nokta. En az bir NOTR
mutant HER IKI kolda da YESIL kalmali; hepsi kirmizi yanan batarya "her degisiklige
kirmizi" demektir, iddia degil.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mutasyona acik kaynaklar (calisma agacindaki YOLLARI; ayna icinde AYNI goreli yol).
SINIF = os.path.join("shop", "src", "kanal-sinif.mjs")
YONET = os.path.join("shop", "src", "yonet.js")
RAPOR = os.path.join("tools", "kanal-kirilim-raporu.py")

# Aynaya kopyalanacak dosyalar (goreli yollar). Ayna, testlerin bekledigi dizin
# yapisini birebir korur: panel-atif.mjs `../src/kanal-sinif.mjs`'i, kanal-sinif-cli.mjs
# `../shop/src/kanal-sinif.mjs`'i, rapor da kendi KOK'unu bu yapidan cozer.
AYNA_DOSYALAR = [
    SINIF, YONET, RAPOR,
    os.path.join("shop", "test", "panel-atif.mjs"),
    os.path.join("tools", "kanal-sinif-cli.mjs"),
    os.path.join("tools", "kanal-kirilim-test.py"),
]

KOL_PANEL = "panel-atif"
KOL_RAPOR = "kanal-kirilim-test"

KIRMIZI = "KIRMIZI"
YESIL = "YESIL"
OLCULEMEDI = "OLCULEMEDI"

# (ad, dosya, beklenen_kollar, aciklama, [(eski, yeni), ...])
#   beklenen_kollar: {kol: beklenen_durum} — BEYAN EDILMEYEN kol YESIL beklenir.
MUTANTLAR = [
    ("M1 'atif-yok' ORGANIGE KATLANDI (SPEC OLDURUCUSU)", SINIF,
     {KOL_PANEL: KIRMIZI, KOL_RAPOR: KIRMIZI},
     "atfi olmayan site siparisleri organik sayilir -> organik ROI oldugundan buyuk "
     "gorunur ve raporun TAMAMI yalan olur (spec'in adiyla andigi hata)",
     [("""  const bos = Object.keys(atif).length === 0;
  return { ...temel, kova: KOVA_ATIF_YOK, sebep: bos ? "atif-bos" : "atif-cozulemedi" };""",
       """  const bos = Object.keys(atif).length === 0;
  return { ...temel, kova: KOVA_SITE_ORGANIK, sebep: bos ? "atif-bos" : "atif-cozulemedi" };""")]),

    ("M2 `kanal` YOKKEN SESSIZCE 'site' SAYILDI (SPEC OLDURUCUSU)", SINIF,
     {KOL_PANEL: KIRMIZI},
     "goc kosmadan once WhatsApp siparisleri de site sayilir -> site ROI'si sessizce "
     "sisirilir; ekran olculmemis bir seyi olculmus gibi gosterir",
     [("""  const kanal = typeof kanalHam === "string" ? kanalHam.trim() : "";
  if (!kanal) {
    return { ...temel, kova: KOVA_KANAL_OLCULEMEDI, sebep: "kanal-kolonu-yok" };
  }""",
       """  const kanal = (typeof kanalHam === "string" ? kanalHam.trim() : "") || KANAL_SITE;""")]),

    ("M2b RAPOR: kanal kolonu YOKKEN fail-closed KOLU KALDIRILDI", RAPOR,
     {KOL_RAPOR: KIRMIZI},
     "M2'nin RAPOR tarafindaki ikizi: kolon olculemezken rapor yine de kova sayilari "
     "uretir -> 'OLCULEMEDI' hukmu sessizce 'TAMAM'a doner",
     [("""    if not kanal_kolonu_var:""", """    if False:""")]),

    ("M3 `fbp` BEYAZ-LISTEYE SIZDI (SPEC OLDURUCUSU)", SINIF,
     {KOL_PANEL: KIRMIZI},
     "kisiye baglanan Meta reklam-eslestirme kimligi /liste JSON'una ve panel HTML'ine "
     "girer -> ekran goruntusuyle disari cikabilen bir kimlik bedava ifsa olur",
     [("""export const GORUNUR_ATIF_ALANLARI = [
  "utm_source", "utm_medium", "utm_campaign", "utm_id", "ref",
];""",
       """export const GORUNUR_ATIF_ALANLARI = [
  "utm_source", "utm_medium", "utm_campaign", "utm_id", "ref", "fbp",
];""")]),

    ("M3b /liste: HAM `atif` JSON'u istemciye gonderildi", YONET,
     {KOL_PANEL: KIRMIZI},
     "M3'un WORKER tarafindaki ikizi: suzulmus ozetin YANINA ham atif da konur -> "
     "fbp/fbc/ga_client_id yonetim tarayicisina iner (panelde basilmasa bile JSON'da "
     "durur, ag/oturum kaydina ve DevTools'a duser)",
     [("""      kaynak: kaynakOzeti(s.kanal, s.atif),""",
       """      kaynak: kaynakOzeti(s.kanal, s.atif),
      atif: s.atif,""")]),

    ("M4 'iptal' CIROYA GIRDI (SPEC OLDURUCUSU)", SINIF,
     {KOL_PANEL: KIRMIZI, KOL_RAPOR: KIRMIZI},
     "vazgecilen siparisler ciroya sayilir -> reklam ROI'si terk edilmis sepetlerle "
     "sisirilir ve butce karari yanlis sayiya dayanir",
     [("""export const CIRO_DURUMLARI = new Set(["odendi", "uretimde", "kargolandi", "tamamlandi"]);""",
       """export const CIRO_DURUMLARI = new Set(["odendi", "uretimde", "kargolandi", "tamamlandi", "iptal"]);""")]),

    ("M5 UCUNCU SINIF YUTULDU: tanimsiz kanal 'site' sayildi", SINIF,
     {KOL_PANEL: KIRMIZI, KOL_RAPOR: KIRMIZI},
     "iki kovali siniflama tuzagi: ileride eklenecek bir kanal (or. instagram-dm) "
     "sessizce site kovasina duser ve site sayisini sahte buyutur",
     [("""  if (kanal !== KANAL_SITE) {
    return { ...temel, kova: KOVA_KANAL_BILINMIYOR, sebep: "kanal:" + kanal };
  }""", """  // ucuncu sinif kolu kaldirildi (mutant)""")]),

    ("M6 SESSIZ BOSLUK: atif yokken panel HIC bir sey yazmiyor", YONET,
     {KOL_PANEL: KIRMIZI},
     "'kaynak YOK' ile 'OLCULEMEDI' ayni bos hucreye duser; Okan bosluga bakip "
     "'bu siparisin kaynagi yok' saniyor (panel-kaynak N1 ile ayni sinif)",
     [(""" var govde=parcalar.length?parcalar.join(' · ')
  :'<span class="yok">kaynak kaydı yok</span>';""",
       """ var govde=parcalar.length?parcalar.join(' · '):'';""")]),

    ("M7 RAPOR: sifir olan kovalar tablodan dusuruldu", RAPOR,
     {KOL_RAPOR: KIRMIZI},
     "basilmayan kova, VAR OLMAYAN kovadan ayirt edilemez -> okuyan 'o durum hic "
     "olmadi' saniyor; kova adinin ciktida gorunmesi spec sarti",
     [("""    for kova in soz["kovalar"]:
        v = sayac[kova]
        ekle("%-24s %8d %10d %16s"
             % (kova, v["adet"], v["ciro_adet"], tl(v["ciro_kurus"])))""",
       """    for kova in soz["kovalar"]:
        v = sayac[kova]
        if not v["adet"]:
            continue
        ekle("%-24s %8d %10d %16s"
             % (kova, v["adet"], v["ciro_adet"], tl(v["ciro_kurus"])))""")]),

    ("M8 RAPOR: takvim dogrulamasi kalip suzgecine geri dondu", RAPOR,
     {KOL_RAPOR: KIRMIZI},
     "CANLI KOSUMDA OLCULEN GERCEK HATA: '2026-13-01' kaliptan gecer, SQL hicbir "
     "satirla eslesmez ve rapor 'TAMAM · 0 satir' basar -> yazim hatasi 'o aralikta "
     "siparis yok' gibi gorunur (sessiz sifir)",
     [("""        datetime.date.fromisoformat(deger)
        return True
    except ValueError:
        return False""",
       """        return len(deger) == 10 and deger[4] == "-" and deger[7] == "-"
    except ValueError:
        return False""")]),

    ("M9 RAPOR: bos aralik uyarisi kaldirildi (sessiz bos tablo)", RAPOR,
     {KOL_RAPOR: KIRMIZI},
     "bos tablo 'hic siparis yok' ile 'aralik/suzgec yanlis'i AYNI bos ekrana "
     "dusururdu",
     [("""        ekle("  ⚠️ BU ARALIKTA HIC SIPARIS YOK — tablo bos degil, ARALIK bos.")""",
       """        pass""")]),

    ("N1 NOTR: yalnizca yeni bir sabit eklendi (KONTROL)", SINIF,
     {},
     "davranis degismiyor; batarya 'her degisiklige kirmizi' DEGIL",
     [("""export const KANAL_SITE = "site";""",
       """export const KANAL_SINIF_NOTR_MUTANT = "notr";\nexport const KANAL_SITE = "site";""")]),

    ("N2 NOTR: rapor basligindaki cizgi uzunlugu degisti (KONTROL)", RAPOR,
     {},
     "gorsel detay; hicbir iddia cizgi uzunlugunu olcmuyor",
     [("""    ekle("=" * 70)""", """    ekle("=" * 64)""")]),
]


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ayna_kur(hedef):
    """Calisma agacindan aynaya kopyala (goreli yapiyi koruyarak)."""
    for goreli in AYNA_DOSYALAR:
        kaynak = os.path.join(KOK, goreli)
        varis = os.path.join(hedef, goreli)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        shutil.copyfile(kaynak, varis)


def kollari_kos(ayna):
    """Aynadaki IKI kabul kolunu kos. Doner {kol: (durum, son_satir)}."""
    ort = dict(os.environ)
    # Rapor testinin olcecegi rapor: AYNADAKI kopya (calisma agacindaki DEGIL).
    ort["PRUVO_KANAL_RAPOR"] = os.path.join(ayna, RAPOR)
    komutlar = {
        KOL_PANEL: [shutil.which("node") or "node",
                    os.path.join(ayna, "shop", "test", "panel-atif.mjs")],
        KOL_RAPOR: [sys.executable,
                    os.path.join(ayna, "tools", "kanal-kirilim-test.py")],
    }
    sonuc = {}
    for kol, komut in komutlar.items():
        p = subprocess.run(komut, capture_output=True, text=True, env=ort, cwd=ayna)
        satirlar = [s for s in (p.stdout or "").strip().splitlines() if s.strip()]
        son = satirlar[-1] if satirlar else (
            ((p.stderr or "").strip().splitlines() or [""])[-1])
        if p.returncode == 0:
            sonuc[kol] = (YESIL, son)
        elif p.returncode == 1:
            sonuc[kol] = (KIRMIZI, son)
        elif p.returncode == 3:
            sonuc[kol] = (OLCULEMEDI, son)
        else:
            sonuc[kol] = (OLCULEMEDI,
                          "beklenmeyen cikis kodu %d | %s" % (p.returncode, son[:160]))
    return sonuc


def main():
    eksik = [g for g in AYNA_DOSYALAR if not os.path.exists(os.path.join(KOK, g))]
    if eksik:
        print("KAYNAK/TEST eksik: %s — OLCULEMEDI" % ", ".join(eksik))
        return 3
    basta = {g: sha(os.path.join(KOK, g)) for g in AYNA_DOSYALAR}
    temiz = {}
    for g in (SINIF, YONET, RAPOR):
        with open(os.path.join(KOK, g), encoding="utf-8") as f:
            temiz[g] = f.read()

    tmp = tempfile.mkdtemp(prefix="pruvo-kanal-mut-")
    sonuclar = []
    try:
        # 0) TABAN: mutasyonsuz aynada IKI kol da YESIL olmali.
        ayna_kur(tmp)
        taban = kollari_kos(tmp)
        for kol, (durum, son) in taban.items():
            print("TABAN %-20s %s | %s" % (kol, durum, son))
        if any(d != YESIL for d, _ in taban.values()):
            print("🔴 Taban yesil degil — mutant sonuclari yorumlanamaz. DUR.")
            return 3

        for ad, dosya, beklenen_kollar, _neden, yamalar in MUTANTLAR:
            metin = temiz[dosya]
            uygulanmayan = []
            for eski, yeni in yamalar:
                if eski not in metin:
                    uygulanmayan.append(eski.strip()[:70])
                    continue
                metin = metin.replace(eski, yeni, 1)
            if uygulanmayan:
                # 🔴 SESSIZ ATLAMA YOK: capa tutmadiysa mutant UYGULANMADI demektir;
                # "kirmizi yanmadi" diye raporlamak yanlis-yesil olurdu.
                sonuclar.append((ad, beklenen_kollar, {}, OLCULEMEDI,
                                 "capa tutmadi: " + " | ".join(uygulanmayan)))
                print("  %-52s CAPA TUTMADI (%s)" % (ad, uygulanmayan[0]))
                continue
            if metin == temiz[dosya]:
                sonuclar.append((ad, beklenen_kollar, {}, OLCULEMEDI,
                                 "mutant metni kaynakla AYNI"))
                continue
            ayna_kur(tmp)  # her mutant TEMIZ aynadan baslar
            with open(os.path.join(tmp, dosya), "w", encoding="utf-8") as f:
                f.write(metin)
            gercek = kollari_kos(tmp)
            beklenen_tam = {KOL_PANEL: beklenen_kollar.get(KOL_PANEL, YESIL),
                            KOL_RAPOR: beklenen_kollar.get(KOL_RAPOR, YESIL)}
            uyumlu = all(gercek[k][0] == beklenen_tam[k] for k in beklenen_tam)
            sonuclar.append((ad, beklenen_tam,
                             {k: v[0] for k, v in gercek.items()},
                             "UYUMLU" if uyumlu else "UYUSMAZ",
                             " | ".join("%s=%s" % (k, v[1][:70]) for k, v in gercek.items())))
            print("  %-52s %s  panel=%-10s rapor=%-10s"
                  % (ad, "OK " if uyumlu else "🔴 ",
                     gercek[KOL_PANEL][0], gercek[KOL_RAPOR][0]))
            # Calisma agaci HER mutanttan sonra dogrulanir (sizinti erken yakalansin).
            for g in AYNA_DOSYALAR:
                if sha(os.path.join(KOK, g)) != basta[g]:
                    print("🔴 CALISMA AGACI DEGISTI (%s) — mutasyon sizdi. DUR." % g)
                    return 3
    finally:
        # DISKTE IZ BIRAKMA: hata alsak da gecici ayna dizini SILINIR.
        shutil.rmtree(tmp, ignore_errors=True)

    for g in AYNA_DOSYALAR:
        if sha(os.path.join(KOK, g)) != basta[g]:
            print("🔴 CALISMA AGACI DEGISTI (%s, kapanista) — DUR." % g)
            return 3

    uyusmaz = [x for x in sonuclar if x[3] != "UYUMLU"]
    # NOTR mutant = hicbir kolda kirmizi beklenmeyen mutant.
    notr = [x for x in sonuclar
            if x[1] and all(v == YESIL for v in x[1].values()) and x[3] == "UYUMLU"]
    oldurucu = [x for x in sonuclar
                if x[1] and any(v == KIRMIZI for v in x[1].values()) and x[3] == "UYUMLU"]
    print("")
    print("MUTANT: %d | beklendigi gibi: %d | uyusmayan: %d | oldurucu-dogrulanan: %d | notr-yesil: %d"
          % (len(sonuclar), len(sonuclar) - len(uyusmaz), len(uyusmaz),
             len(oldurucu), len(notr)))
    print("calisma agaci sha256 degismedi: %s"
          % all(sha(os.path.join(KOK, g)) == basta[g] for g in AYNA_DOSYALAR))
    for ad, bek, ger, hal, son in uyusmaz:
        print("  🔴 %s: beklenen %s, gercek %s (%s) | %s" % (ad, bek, ger, hal, son))
    if not notr:
        print("  🔴 Hicbir notr mutant yesil kalmadi — batarya 'her degisiklige kirmizi' olabilir.")
        return 1
    if len(oldurucu) < 4:
        print("  🔴 Dogrulanan oldurucu mutant 4'un ALTINDA (%d) — kabul sarti karsilanmadi."
              % len(oldurucu))
        return 1
    return 0 if not uyusmaz else 1


if __name__ == "__main__":
    sys.exit(main())

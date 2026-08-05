#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/cron-nabiz-kapisi.py NABIZ EKSENLERININ CURUTME (mutasyon) araci.

NE OLCER: "kabul testi YESIL" demek "eksen CANLI" demek DEGILDIR. Bu arac eksenleri
BILEREK bozar ve `--kendini-test`in GERCEKTEN kirmizi yandigini SAYIYLA olcer.
Kapsam: A5 TESLIM · A0 TETIKLEYICI SARTI · A3/A5 ORTAK CAPA · KADANS KOLU KABLOSU ·
EN UZUN BOSLUGUN UC TERIMLERI (X4/X5) · PUSH SERIDI TETIK IZIN LISTESI + DAL CIVISI
(X6-X13). Mutantlar UC dosyaya uygulanabilir: `tools/cron-nabiz-kapisi.py`,
`.github/workflows/deploy.yml` ve `.github/workflows/d1-uzlastirici.yml` (kadans kolunun
bloklamama sarti ve eszamanlilik kilidi YALNIZ is akisi dosyalarindan olculebilir).

🔴 KABUL IKI KATLIDIR: (a) mutant OLDU MU (kirmizi > 0) ve (b) HANGI EKSENI oldurdu
   (beyan kumesine TAM ESIT). Yalniz (a) olcen bir batarya, bir mutantin beklenmedik bir
   ekseni dusurmesini "oldurucu" sayar ([[beyan-edilmis-survivor]]).

NEDEN VAR (olculen korluk, 4 Agu 2026)
======================================
`paket-tazelik-alarmi.yml` cron'u `13,28,43,58` — gunde 96 zamanlanmis kosum BEKLENIR.
FIILEN olculen: 2,42 gunde 10 kosum (%4,31); en uzun ardisik bosluk 1053,5 dk (17,6 sa).
`d1-uzlastirici.yml` (cron `9,24,39,54`) AYNI oranda dusuyor ve IKISI AYNI DAKIKALARDA,
PARTI HALINDE atesleniyor -> hal is akisina ozgu DEGIL, depo/hesap duzeyinde.
O gun nabiz kapisi rc=0 (YESIL) veriyordu: A1 cron METNINI olcer (teslimi degil), A3
YALNIZ SON kosumun yasina bakar (2,5 sa -> taze), A0/A4 damga yasina bakar (0,8/8,5 sa
-> esik 9 sa'in altinda). Yani "nobetci var ama KOR" sinifi. A5 o boslugu kapatir.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]): her mutant kosumunda IDDIA SAYISI taban
   kosumla AYNI olmali. Sayi dusuyorsa mutant testi COKERTMISTIR ve o kirmizi bir OLCUM
   DEGILDIR (cokme kirmiziyla karisir).

🔴 KONTROL MUTANTI SART ([[fikstur-degeri-mutasyon-koru]]): anlam tasimayan bir degisiklik
   bataryayi kirmizi yakmamali, yoksa "oldu" hukumlerinin hicbiri mutasyona atfedilemez.

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]]). Kosum basinda ve sonunda kaynak sha256 karsilastirilir.

🔴 Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan
   KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/cron-teslim-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontrol YESIL kaldi + iddia sayilari korundu +
canli kaynaklar sha256 olarak DEGISMEDI.
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

KAPI = "tools/cron-nabiz-kapisi.py"
DEPLOY = os.path.join(".github", "workflows", "deploy.yml")
UZLASTIRICI = os.path.join(".github", "workflows", "d1-uzlastirici.yml")
# Mutasyona UGRAYABILEN her canli dosya burada: kosum basinda ve sonunda sha256
# karsilastirilir ([[mutasyon-diske-yazma-tuzagi]]).
HEDEFLER = (KAPI, DEPLOY, UZLASTIRICI)
DOKUNULMAZ = [os.path.join(ROOT, y) for y in HEDEFLER]

FAILS = []


def check(mesaj, kosul, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
    return kosul


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# MUTANTLAR — (kod, aciklama, HEDEF_DOSYA, [(bulunacak, yerine), ...], kirmizi_mi,
#             BEYAN_KUMESI)
#
# 🔴 ALTINCI ALAN = BEYAN EDILEN KIRMIZI EKSEN KUMESI (4 Agu 2026, uzlasma turu).
#    "kirmizi > 0" olcutu bir mutantin BEKLENMEDIK bir ekseni dusurmesini ve yine de
#    "oldurucu" sayilmasini ENGELLEMEZ ([[beyan-edilmis-survivor]]). Beyan verilen
#    mutantlarda olculen kirmizi eksen kumesi beyana TAM ESIT olmali (gevsek "kapsar"
#    olcutu YOK; fazladan kirmizi da kusurdur).
#      · `None`  -> yalnizca eski isaret sarti (kirmizi > 0) uygulanir.
#      · `set()` -> KONTROL: hicbir eksen kirmizi yanmamali.
#    Eksen kodu = `[FAIL]` satirinin ILK SOZCUGUDUR (A5 / PS10 / X4 ... gibi).
#    ALAN SAYISI KOSARAK DOGRULANIR (asagida): 6 alani olmayan bir mutant harness'i
#    GURULTULU dusurur — sessizce "beyansiz" moda kayamaz.
# ─────────────────────────────────────────────────────────────────────────────
M1 = ("M1", "🔴 TABAN KONTROLU NO-OP: `teslim < taban` -> `False` (A5 hicbir zaman "
            "alarm vermez; 4 Agu'daki hal aynen geri gelir)", KAPI,
      [("    if teslim < taban:\n", "    if False:\n")], True, None)

M2 = ("M2", "🔴 OLCULEMEDI -> YESIL: cozulemeyen zaman damgasi hata yerine SESSIZCE "
            "ATLANIYOR (teslim 8 -> 7, ikisi de tabanin ustunde: hal yesil kalir)", KAPI,
      [('                    damgalar.append(_iso(k["created_at"]))\n',
        '                    try:\n'
        '                        damgalar.append(_iso(k["created_at"]))\n'
        '                    except OlcumHatasi:\n'
        '                        continue\n')], True, None)

M3 = ("M3", "🔴 ESIK 'kirmizi gormeyeyim' DIYE DUSURULDU (guvenlik boleni 2 -> 8; "
            "15 dk cron tabani 4 -> 1)", KAPI,
      [("TESLIM_GUVENLIK_BOLENI = 2.0", "TESLIM_GUVENLIK_BOLENI = 8.0")], True, None)

M4 = ("M4", "🔴 ORTAK CAPA `yenileme_an`e cevrildi (A3 + A5 TEK KAYNAK): dosyaya her "
            "dokunus IKI ekseni birden susturur (olculdu: dokunma araligi medyan "
            "5,2-5,5 sa < N=9 sa -> eksenler fiilen OLU)", KAPI,
      [('    kayit_an = g.get("kayit_an")\n'
        '    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None\n',
        '    _capalar = [x for x in (g.get("kayit_an"), g.get("yenileme_an")) if x]\n'
        '    kayit_an = max(_capalar) if _capalar else None\n'
        '    gecmis_saat = ((simdi - kayit_an).total_seconds() / 3600.0) if kayit_an else None\n')],
      True, None)

M5 = ("M5", "🔴 SIRALAMA API'YE BIRAKILDI: pencere kosumlari siralanmiyor -> EN UZUN "
            "BOSLUK (korluk penceresinin gercek degeri) yanlis hesaplanir", KAPI,
      [("    damgalar = sorted(x for x in (g.get(\"tum_kosumlar\") or []) "
        "if x > pencere_basi)",
        "    damgalar = [x for x in (g.get(\"tum_kosumlar\") or []) if x > pencere_basi]")],
      True, None)

M6 = ("M6", "🔴 EVET SUZGECI YALNIZ ILK KAYITTA: listenin gerisi korlemesine sayiliyor "
            "(yarim calisan `event=schedule` suzgeci sahte YESIL uretir)", KAPI,
      [("                    if k.get(\"event\") != \"schedule\":\n"
        "                        raise OlcumHatasi(\"%s: event=schedule istendi ama "
        "kayit event=%r \"\n",
        "                    if k.get(\"event\") != \"schedule\" and False:\n"
        "                        raise OlcumHatasi(\"%s: event=schedule istendi ama "
        "kayit event=%r \"\n")],
      True, None)

# ── 4 AGU 2026'DA OLDURULEMEYEN MUTANTLAR (bu turun sebebi) ─────────────────
M7 = ("M7", "🔴 A0 TETIKLEYICI SARTI NO-OP: damgayi yazan kosumun `event=schedule` "
            "kumesinde olup olmadigina BAKILMIYOR -> elle (`workflow_dispatch`) yazilan "
            "bir damga alarmi 9 saat susturur. 4 Agu 09:45:48Z'de FIILEN olan budur ve "
            "o gun bu mutant OLDURULEMIYORDU.", KAPI,
      [('        if kimlik in kaynak["kimlikler"]:\n            return kayit\n',
        '        if True:\n            return kayit\n')], True, None)

M8 = ("M8", "🔴 A3 CAPASI ESKI HALINE (max(kayit_an, yenileme_an)) DONDURULDU — YALNIZ "
            "A3 cagri yerinde: cron dosyasina her dokunus A3'u N=9 sa SUSTURUR (canli "
            "olcum 4 Agu 10:04Z: cron 9,8 saattir oluyken A3 satiri 🟡 idi)", KAPI,
      [('        yeni_tanim = (g["son_kosum"] is None or kayit_an > g["son_kosum"])\n',
        '        kayit_an = max(kayit_an, g["yenileme_an"] or kayit_an)\n'
        '        kayit_yasi = (simdi - kayit_an).total_seconds() / 3600.0\n'
        '        yeni_tanim = (g["son_kosum"] is None or kayit_an > g["son_kosum"])\n')],
      True, None)

M9 = ("M9", "🔴 KADANS KOLU YAYIN YOLUNA SIZDIRILDI: `d1-kadans` job'u `deploy: needs` "
            "listesine eklendi -> D1/ag'a bagimli bir kol TUM EKIBIN yayinini durdurur "
            "(bu depoda olculen kapi-birikimi zarari)", DEPLOY,
      [("    needs: [build, serit-a2, serit-a3, serit-a4]\n",
        "    needs: [build, serit-a2, serit-a3, serit-a4, d1-kadans]\n")], True, None)

M10 = ("M10", "🔴 ESZAMANLILIK KILIDI SILINDI: uzlastiran isin `concurrency` grubu "
              "kaldirildi -> cron kolu ile push kolu AYNI ANDA kosabilir (D1'e cift "
              "yazim penceresi acilir)", UZLASTIRICI,
       [("    concurrency:\n      group: d1-uzlastirici\n      cancel-in-progress: false\n",
         "")], True, None)

M12 = ("M12", "🔴 KILITLENME RISKI: cagiran job da AYNI eszamanlilik grubunu tutuyor "
              "(cagiran job grubu tutarken cagrilan is ayni grubu ister -> kosum "
              "kilitlenebilir); kilit TEK YERDE olmali", DEPLOY,
       [("  d1-kadans:\n    uses: ./.github/workflows/d1-uzlastirici.yml\n",
         "  d1-kadans:\n    concurrency:\n      group: d1-uzlastirici\n"
         "      cancel-in-progress: false\n"
         "    uses: ./.github/workflows/d1-uzlastirici.yml\n")], True, None)

M11 = ("M11", "🔴 CRON IKINCI KOLU SILINDI ('kadans yetiyor' varsayimi): push'suz gecede "
              "uzlastirma HIC kosmaz ve A0/A3 capasi da kaybolur", UZLASTIRICI,
       [('  schedule:\n    - cron: "9,24,39,54 * * * *"\n',
         "  # cron KALDIRILDI (mutant)\n")], True, None)

# ── KONTROL MUTANTLARI (YESIL kalmali) ──────────────────────────────────────
K1 = ("K1", "ilgisiz: A5 sabitinin yanina aciklama yorumu eklendi", KAPI,
      [("TESLIM_SAYFA = 100", "TESLIM_SAYFA = 100   # GitHub sayfa boyu")], False, set())

K2 = ("K2", "ilgisiz: deploy.yml'de kadans job'unun USTUNE yorum satiri eklendi "
            "(is akisi semantigi DEGISMEZ)", DEPLOY,
      [("  d1-kadans:\n    uses:", "  # kadans kolu — gerekce ustteki blokta\n"
                                   "  d1-kadans:\n    uses:")], False, set())

K3 = ("K3", "ilgisiz: olculen elle-kosum kimliginin yanina aciklama yorumu eklendi", KAPI,
      [("_CRON_DISI_KOSUM = 30897735170",
        "_CRON_DISI_KOSUM = 30897735170   # 4 Agu 09:45:48Z")], False, set())

# ── EN UZUN BOSLUGUN UC TERIMLERI (4 Agu 2026 kanit-kalitesi onarimi) ───────
# 🔴 NEDEN VAR: "en uzun bosluk" UC ucu sayar (ic bosluklar · devam eden sessizlik ·
# pencere basi) ve kod bunlari satir satir gerekcelendiriyordu — ama TEK A5 fiksturunun
# maks boslugu bir IC bosluktu (2370 dk). Bagimsiz curutucu olctu: iki UC terimini silen
# mutantlar 0 KIRMIZI ile SURVIVOR veriyordu; yani "1053,5 dk korluk penceresinin GERCEK
# degeridir" iddiasinin HESABI OLCULMEMISTI ([[fikstur-degeri-mutasyon-koru]]).
# Kapiya X4/X5 fiksturleri eklendi; bu iki mutant onlarin AYIRT EDICI oldugunu kanitlar.
X4 = ("X4", "🔴 DEVAM EDEN SESSIZLIK ucu SILINDI: son kosumdan SIMDIYE kadar gecen sure "
            "bosluk sayilmiyor -> 44 saattir HIC kosmayan bir is akisi 'en uzun bosluk "
            "60 dk' diye SAGLIKLI raporlanir", KAPI,
      [("        bosluklar.append((simdi - damgalar[-1]).total_seconds() / 60.0)\n", "")],
      True, {"X4"})

X5 = ("X5", "🔴 PENCERE BASI ucu GIZLENDI: ilk kosumdan ONCEKI sessizlik bosluk "
            "sayilmiyor -> 'pencerenin 45 saati sessiz, son 3 saatte 4 kosum' (PARTI "
            "HALINDE teslim, 4 Agu'da OLCULEN hal) kucucuk bir bosluk gibi gorunur", KAPI,
      [("        if not g.get(\"pencere_kirpildi\"):\n"
        "            bosluklar.append((damgalar[0] - pencere_basi).total_seconds() / 60.0)",
        "        if False:\n"
        "            bosluklar.append((damgalar[0] - pencere_basi).total_seconds() / 60.0)")],
      True, {"X5"})

# ── PUSH SERIDI KABLO CAPASI — TETIK IZIN LISTESI + DAL CIVISI ──────────────
# Odeme yolu bayatlik olcumu cron'a EK olarak push tetikli `odeme-bayatlik-push.yml`
# seridinde de kosuyor. O seridin "yayini durdurmaz + disaridan surulemez" ozelligi
# BEYAN DEGIL, KOSULAN bir kapidir (`push_serit_kablosu`).
#
# 🔴 ILK TURDA KUSURLU IDI (bagimsiz curutucu): kapi bir KARA LISTE tutuyordu
# ("pull_request", "workflow_call") ve `pull_request_target` ACIK KALMISTI — o tetigi
# tasiyan bir is akisi kapidan YESIL geciyordu. Kara liste TAMAMLANAMAZ
# ([[maskeleme-kismi-kapatma]]); kapi IZIN LISTESINE cevrildi. Asagidaki mutantlar izin
# listesini TEK TEK genisletir: her biri BIR fiksturu — ve YALNIZ onu — kirmizi yakar.
# Mutanti OLMAYAN bir yasak yine BEYAN'dir; bu yuzden her yasak tetigin bir satiri var.
def _izin(*ekler):
    return [('PUSH_SERIT_IZINLI_TETIK = ("push", "workflow_dispatch")',
             'PUSH_SERIT_IZINLI_TETIK = ("push", "workflow_dispatch", %s)'
             % ", ".join('"%s"' % e for e in ekler))]


X6 = ("X6", "🔴 IZIN LISTESI GENISLETILDI: `pull_request` mesru sayiliyor (fork PR'i "
            "seridi baslatir; olcum cadansini ve kuyruk yukunu disaridan surdurur)",
      KAPI, _izin("pull_request"), True, {"PS10"})

X7 = ("X7", "🔴 BLOKE EDEN KUSURUN NOBETI: `pull_request_target` mesru sayiliyor — fork "
            "PR'ini TABAN DEPO baglaminda ve DEPO SECRET'leriyle kosturur, yani yabanci "
            "koda CLOUDFLARE_API_TOKEN acar (ilk turda kapi bu tetikte YESIL geciyordu)",
      KAPI, _izin("pull_request_target"), True, {"PS17"})

X8 = ("X8", "🔴 `issue_comment` mesru sayiliyor (herkesin yazabildigi bir yorum taban "
            "depo baglaminda secret'li kosum baslatir)",
      KAPI, _izin("issue_comment"), True, {"PS18"})

X9 = ("X9", "🔴 `workflow_run` mesru sayiliyor (serit deploy.yml'in TAMAMLANMASINA "
            "baglanir; nobetci olctugu hatta bagimli olur — Y4 sinifi)",
      KAPI, _izin("workflow_run"), True, {"PS19"})

X10 = ("X10", "🔴 MEKANIZMA NOBETI: ENUMERE EDILMEMIS bir tetik (`repository_dispatch`) "
              "izin listesine giriyor -> izin listesinin fail-closed'ligi coker",
       KAPI, _izin("repository_dispatch"), True, {"PS20"})

X11 = ("X11", "🔴 DAL CIVISI (GENIS desen kolu) NO-OP: `branches: ['**']` kabul edilir "
              "-> serit HER dala kosar, gurultu alarmi FIILEN susturur", KAPI,
       [("        elif dal_listesi != [PUSH_SERIT_DAL]:\n", "        elif False:\n")],
       True, {"PS21"})

X12 = ("X12", "🔴 DAL CIVISI (TANIMSIZ kolu) NO-OP: `push.branches` hic tanimli "
              "olmadiginda (varsayilan = TUM dallar) ariza URETILMEZ", KAPI,
       [("        if not dal_listesi:\n", "        if False:\n")], True, {"PS22"})

X13 = ("X13", "🔴 `workflow_call` mesru sayiliyor (is akislari arasi TEK bag yolu; serit "
              "deploy.yml'in `needs` grafinin ICINE girebilir)",
       KAPI, _izin("workflow_call"), True, {"PS11"})

# ── CANLI KALIBRASYON (5 Agu 2026) — Y EKSENLERI ────────────────────────────
# 🔴 NEDEN VAR: esik DONMUS bir sabitten (31 Tem, 4,016 sa penceresi, %12,5) turuyordu.
# 5 Agu olcumu rejimi %4,52 buldu (110,6 sa · 442 nominal · 20 teslim; en uzun bosluk
# 1053,2 dk) ve N=9 sa esigi BOS KIRMIZI uretmeye basladi (son 30 deploy kosumunda 3 kez).
# Esik artik CANLI olculen orandan turer. Bu onarim KENDI BASINA fail-open olabilirdi:
# teslim kotulestikce esik buyur, esik buyudukce alarm susar. Asagidaki mutantlar tam o
# geri besleme deligini ve tavanlari civiler.
Y1 = ("Y1", "🔴 MUTLAK SESSIZLIK TAVANI KALDIRILDI ('olcum ne derse o olsun'): turetilen "
            "N=20 sa'e cikar ve 19,0 saatlik TAM SESSIZLIK YESILE doner — pencereyi "
            "olcumun insafina birakan mutant", KAPI,
      [("    if n > tavan:\n        kaynak += \" · TAVAN %d sa BAGLADI\" % tavan\n"
        "        n = tavan\n", "")], True, {"A4", "EKSEN", "Y3"})

Y2 = ("Y2", "🔴 TAVAN SONSUZA ACILDI (tavan sabiti 18 -> 9999): 'pencereyi sonsuz "
            "genisletme' mutantinin sabit kolu; ayni 19,0 sa fiksturu YESILE doner",
      KAPI, [("MUTLAK_SESSIZLIK_SAAT = 18", "MUTLAK_SESSIZLIK_SAAT = 9999")],
      True, {"Y-INV", "Y3"})

Y3 = ("Y3", "🔴 COKMUS REJIM SABIR SATIN ALIYOR: A5 TABAN SARTI kaldirildi -> teslim "
            "cokerken (1/48 sa) canli oran KABUL EDILIR, esik 9 -> 18 sa'e cikar ve "
            "12 saatlik sessizlik YESILE doner. Onarimin fail-open'a cevrilebildigi "
            "TAM NOKTA ([[duzeltme-fail-open-cevirebilir]])", KAPI,
      [("    if teslim < a5_tabani:\n        return None, "
        "(\"teslim %d < A5 tabani %d: COKMUS rejim kendi esigini BUYUTEMEZ\"\n"
        "                      % (teslim, a5_tabani))\n", "")], True, {"A3", "IKIZ", "Y4"})

Y4 = ("Y4", "🔴 'KOSUM VAR' ile 'TESLIM VAR' KARISTIRILDI: oran W penceresindeki "
            "teslimden degil is akisinin TOPLAM kosum sayisindan turetiliyor (137/192 "
            "= %71) -> esik 18 sa'ten 3 sa'e duser ve saglikli fikstur BOS KIRMIZI "
            "yakar", KAPI,
      [("    teslim = len([x for x in (g.get(\"tum_kosumlar\") or []) "
        "if x > pencere_basi])\n",
        "    teslim = g.get(\"kosum_sayisi\") or len(\n"
        "        [x for x in (g.get(\"tum_kosumlar\") or []) if x > pencere_basi])\n")],
      True, {"A4", "Y6"})

# 🔴 Y5 ILK YAZIMINDA `raise`i `if False:`e cevirmisti; o mutant ZeroDivisionError ile
# bataryayi COKERTTI (iddia sayisi None) — cokme kirmizisi bir OLCUM DEGILDIR
# ([[mutasyon-kaniti-yeniden-uretilebilir]]). Mutant, gercek bir muhendisin yazacagi
# SESSIZ FALLBACK'e cevrildi; kapi ayrica cokme halini de ADIYLA kirmizi yakiyor.
Y5 = ("Y5", "🔴 SIFIR TESLIM FAIL-OPEN: sifir/negatif oran OLCULEMEDI demek yerine "
            "SESSIZCE donmus orana dusuruluyor -> 'sifir teslim' ile '%12,5 teslim' "
            "AYNI esigi uretir; teslim sifira giderken alarm bunu HIC gormez", KAPI,
      [("    if oran <= 0:\n        raise OlcumHatasi(\"teslim orani %r -> efektif "
        "cadans SONSUZ olurdu; sifir teslim \"\n                          \"bir esik "
        "TURETEMEZ (fail-closed)\" % (oran,))\n",
        "    if oran <= 0:\n        oran = TESLIM_ORANI\n")],
      True, {"Y-INV"})

Y6 = ("Y6", "🔴 A4 TAVANI (OLCULEN ZARAR penceresi) A0 TAVANINA ESITLENDI: 9 -> 18 sa. "
            "1 Agu'nun 14,5 saatlik fazla tahsilat penceresi (676 fiziksel urunde %84'e "
            "varan) YESILE doner — teslim istatistigi bir ZARAR esigini GEVSETEMEZ",
      KAPI, [("PAKET_BAYATLIK_TAVAN_SAAT = 9", "PAKET_BAYATLIK_TAVAN_SAAT = 18")],
      True, {"A4", "Y-INV", "EKSEN"})

Y7 = ("Y7", "🔴 KIRPIK SAYFA FAIL-OPEN: API sayfa siniri dolmusken oran YINE de "
            "turetiliyor -> teslim EKSIK sayilir, oran DUSUK cikar, esik HAKSIZ YERE "
            "buyur (yanlis yonde tehlikeli)", KAPI,
      [("    if g.get(\"pencere_kirpildi\"):\n"
        "        return None, \"API sayfa siniri doldu (teslim EKSIK sayilir)\"\n", "")],
      True, {"Y5"})

# ── KONTROL MUTANTLARI (Y kolu — YESIL kalmali) ─────────────────────────────
K4 = ("K4", "ilgisiz: canli kalibrasyon sabitinin yanina aciklama yorumu eklendi", KAPI,
      [("OLCULEN_CANLI_TESLIM = 20", "OLCULEN_CANLI_TESLIM = 20   # 5 Agu kesimi")],
      False, set())

K5 = ("K5", "ANLAM TASIMAYAN YENIDEN ADLANDIRMA: `canli_teslim_orani` icindeki yerel "
            "`a5_tabani` degiskeni `alt_sinir` olarak yeniden adlandirildi (davranis AYNI)",
      KAPI,
      [("    a5_tabani = teslim_tabani(aralik, W)\n",
        "    alt_sinir = teslim_tabani(aralik, W)\n"),
       ("    if teslim < a5_tabani:\n", "    if teslim < alt_sinir:\n"),
       ("                      % (teslim, a5_tabani))\n",
        "                      % (teslim, alt_sinir))\n")],
      False, set())

K6 = ("K6", "SIRALAMA DEGISIKLIGI: `canli_esik` icinde birbirinden BAGIMSIZ iki atama "
            "(`aralik` ve `donmus`) yer degistirdi — bagimlilik yok, davranis AYNI",
      KAPI,
      [("    aralik = g.get(\"aralik\")\n"
        "    donmus = esik_saat(aralik) if aralik else ESIK_TABAN_SAAT\n",
        "    aralik = g.get(\"aralik\")\n"
        "    _ = None\n"
        "    donmus = esik_saat(aralik) if aralik else ESIK_TABAN_SAAT\n")],
      False, set())

MUTANTLAR = (M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12,
             X4, X5, X6, X7, X8, X9, X10, X11, X12, X13,
             Y1, Y2, Y3, Y4, Y5, Y6, Y7,
             K1, K2, K3, K4, K5, K6)

# 🔴 ALAN SAYISI NOBETI: 6 alani olmayan bir mutant sessizce "beyansiz" moda kayardi.
_bozuk = [m[0] for m in MUTANTLAR if len(m) != 6]
if _bozuk:
    raise SystemExit("🔴 HARNESS BAYAT: 6 alani olmayan mutant(lar): %s" % _bozuk)

IDDIA_RE = re.compile(r"^(\d+) iddia kosturuldu, (\d+) KIRMIZI\.$", re.M)
# Kirmizi EKSEN kodu = `[FAIL]` satirinin ilk sozcugu (kapinin `iddia()` bicimi).
EKSEN_RE = re.compile(r"^  \[FAIL\] (\S+)", re.M)


def ayna_kur(hedef):
    """tools/ + .github/workflows/ tam kopya. Symlink IZLENIR (fiziksel kopya)."""
    os.makedirs(hedef)
    shutil.copytree(os.path.join(ROOT, "tools"), os.path.join(hedef, "tools"),
                    symlinks=False)
    shutil.copytree(os.path.join(ROOT, ".github", "workflows"),
                    os.path.join(hedef, ".github", "workflows"), symlinks=False)
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
    for bul, yerine in degisimler:
        n = metin.count(bul)
        if n != 1:
            raise SystemExit(
                "🔴 HARNESS BAYAT (%s): dayanak metin %d kez bulundu (1 olmali).\n"
                "   Aranan: %r" % (kod, n, bul[:120]))
        metin = metin.replace(bul, yerine, 1)
    return metin


def kos(ayna, metinler):
    """Aynadaki kapiyi `--kendini-test` ile kostur -> (rc, iddia, kirmizi, kuyruk).

    `metinler` = {gorece_yol: icerik} — mutasyon KAPI'ya da is akisi dosyasina da
    uygulanabilir (kadans kolunun bloklamama sarti yalniz deploy.yml'den olculur)."""
    for rel, metin in metinler.items():
        with open(os.path.join(ayna, rel), "w", encoding="utf-8") as f:
            f.write(metin)
    r = subprocess.run([sys.executable, os.path.join(ayna, KAPI), "--kendini-test"],
                       cwd=ayna, capture_output=True, text=True)
    cikti = r.stdout + r.stderr
    m = IDDIA_RE.search(cikti)
    iddia = int(m.group(1)) if m else None
    kirmizi = int(m.group(2)) if m else None
    return r.returncode, iddia, kirmizi, set(EKSEN_RE.findall(cikti)), cikti[-2500:]


def main():
    print("NABIZ EKSENLERI — CURUTME (mutasyon) KOSUMU")
    print("hedefler: %s\n" % ", ".join(HEDEFLER))
    once = {y: sha(y) for y in DOKUNULMAZ}

    pristine = {}
    for kod, _a, hedef, _d, _k, _b in MUTANTLAR:
        if hedef in pristine:
            continue
        yol = os.path.join(ROOT, hedef)
        if not os.path.exists(yol):
            raise SystemExit("🔴 HARNESS BAYAT (%s): hedef dosya YOK: %s" % (kod, hedef))
        with open(yol, encoding="utf-8") as f:
            pristine[hedef] = f.read()

    tmp = tempfile.mkdtemp(prefix="cron-teslim-mutasyon-")
    try:
        ayna = ayna_kur(os.path.join(tmp, "ayna"))
        baglar = symlinkleri_bul(ayna)
        check("aynada SYMLINK yok (canli kaynaga giden yol fiziksel olarak kapali)",
              not baglar, "symlink: %s" % (baglar[:6] or "-"))

        print("\n1) TABAN KOSUMU (mutasyonsuz ayna — YESIL olmali)")
        t_rc, t_iddia, t_kirmizi, _t_eksen, t_kuyruk = kos(ayna, dict(pristine))
        if not check("taban YESIL (cikis 0, kirmizi iddia 0)",
                     t_rc == 0 and t_kirmizi == 0,
                     "cikis=%s kirmizi=%s" % (t_rc, t_kirmizi)):
            print("\n  --- taban ciktisinin kuyrugu ---\n%s" % t_kuyruk)
            print("\n  ⚠️ TABAN KIRMIZI: mutant kosumlari ANLAMSIZ — durduruluyor.")
            return 1
        check("taban IDDIA SAYISI okunabildi", t_iddia is not None, "iddia=%s" % t_iddia)
        print("   taban iddia sayisi: %s" % t_iddia)

        print("\n2) MUTANTLAR")
        for kod, aciklama, hedef, degisimler, kirmizi_bekleniyor, beyan in MUTANTLAR:
            metinler = dict(pristine)
            metinler[hedef] = mutasyonla(pristine[hedef], degisimler, kod)
            rc, iddia, kirmizi, eksenler, kuyruk = kos(ayna, metinler)
            print("\n  %s [%s] %s" % (kod, hedef, aciklama))
            # 🔴 ISARET SARTI: iddia sayisi degismemeli. Dusmusse mutant testi COKERTMIS
            # demektir ve o kirmizi bir olcum degildir.
            ok_sayi = check("%s: iddia sayisi KORUNDU (cokme kirmizisi DEGIL)" % kod,
                            iddia == t_iddia, "taban=%s mutant=%s" % (t_iddia, iddia))
            if kirmizi_bekleniyor:
                ok = check("%s: mutant OLDU (cikis != 0 ve kirmizi iddia > 0)" % kod,
                           rc != 0 and (kirmizi or 0) > 0,
                           "cikis=%s kirmizi=%s" % (rc, kirmizi))
            else:
                ok = check("%s: KONTROL — mutant YESIL kaldi (gurultu yok)" % kod,
                           rc == 0 and kirmizi == 0,
                           "cikis=%s kirmizi=%s" % (rc, kirmizi))
            # 🔴 BEYAN SARTI: kirmizi EKSEN kumesi beyana TAM ESIT olmali. Fazladan
            # kirmizi da kusurdur — "oldurucu" hukmu o zaman baska bir eksene aittir.
            ok_beyan = True
            if beyan is not None:
                ok_beyan = check(
                    "%s: kirmizi EKSEN kumesi beyana TAM ESIT (%s)"
                    % (kod, sorted(beyan) or "BOS"), eksenler == beyan,
                    "olculen=%s beyan=%s" % (sorted(eksenler) or "-", sorted(beyan) or "-"))
            print("     olculen kirmizi eksen: %s" % (sorted(eksenler) or "-"))
            if not (ok and ok_sayi and ok_beyan):
                print("  --- kuyruk ---\n%s" % kuyruk)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n3) CANLI KAYNAKLAR DEGISMEDI MI")
    for y in DOKUNULMAZ:
        check("sha256 ayni: %s" % os.path.relpath(y, ROOT), sha(y) == once[y])

    oldurucu = sum(1 for m in MUTANTLAR if m[4])
    kontrol = len(MUTANTLAR) - oldurucu
    print("\nOZET: %d oldurucu + %d kontrol mutanti · %d kusur"
          % (oldurucu, kontrol, len(FAILS)))
    if FAILS:
        print("🔴 CURUTME KIRMIZI:")
        for f in FAILS:
            print("   - %s" % f)
        return 1
    print("✅ CURUTME GECTI — her oldurucu mutant KIRMIZI yandi, beyanli mutantlarin "
          "kirmizi eksen kumesi beyana TAM ESIT cikti, kontrol mutantlari "
          "YESIL kaldi (A5 TESLIM · A0 TETIKLEYICI · A3/A5 ORTAK CAPA · KADANS KOLU).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

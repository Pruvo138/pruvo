#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K361 EV HARITASI BATARYASI — ev->dizin tablosu REPO DISINDA, FAIL-CLOSED.

Mimar hukmu (Okan emri / BaBa, 2 Eyl 2026): ev->dizin eslemesi PRUVO
reposundan CIKTI, tek kaynak `~/.claude/cron/evler.json`. Sebep yapisaldi:
**yeni ev acmak PRUVO kodu degistirmeyi gerektiriyordu** — Faralya (FaR) bu
yuzden repoda commit'siz bir satir birakmisti.

BU BATARYA NE OLCER (hepsi HERMETIK — canli `evler.json`'a DOKUNMAZ; her vaka
gecici bir fikstur yazar ve `PRUVO_EVLER_JSON` ile onu gosterir):

  F1 KONFIG_YOK     : dosya yok        -> RED + sifir-disi rc + OLCULEMEDI jetonu
                      **+ KURTARMA komutu ciktida GECER** (RED cikmaz sokak degil)
  F2 KONFIG_BOZUK   : gecersiz JSON    -> ayni
  F3 KONFIG_BOS     : gecerli ama `{}` -> ayni  (🔴 en tehlikeli hal: bos tablo
                      "hicbir evde acik kalem yok" demeye gelir ve kapiyi
                      SESSIZCE ACAR — [[yeni-hal-cozucunun-varsayilan-kovasina-duser]])
  F4 BILINMEYEN_KOK : tabloda olmayan depo koku HALA cozulemez (fail-closed
                      davranis DEGISMEDI)
  F5 FAR_POZITIF    : `FaR` girisi VARKEN Faralya koku COZULUR (pozitif kol —
                      "hep RED veren" bir kapi da olcum yapmiyor demektir)
  F6 TEK_KAYNAK     : `sahiplik-kapisi.EV_BILINEN` ile T4'un kumesi AYNI
                      kaynaktan gelir (ikinci tablo YOK)
  F7 NOT_KAYIPSIZ   : BaBa (27 Agu) ve FaR (2 Eyl) gerekce yorumlari
                      `evler-NOT.md`'de KAYIPSIZ duruyor  [YEREL DUZLEM]
  F8 TOHUM_KAPSAM   : CANLI tablodaki her ev `tools/evler-tohum.json`da DA var —
                      yoksa yeni makinede bootstrap o evi SESSIZCE kaybeder
                      (tam da FaR vakasinin tekrari)  [YEREL DUZLEM]
  F9 KUR_EZMEZ      : `--ev-haritasi-kur` bos makinede dosyayi URETIR (1. kosum)
                      ve ikinci kosumda UZERINE YAZMAZ (2. kosum) — ezmek,
                      tabloya sonradan eklenen evleri yok ederdi

🔴 UCUNCU YOL (mimar hukmu, 2 Eyl): FaR "dosya yoksa gomulu tabloya DUSSUN"
onerdi; hukum REDDETTI ama RED'i cikmaz sokak birakmadi. Ayrim BUDUR:
  * RUNTIME  : sessiz dusus YOK (F1/F2/F3) + kurtarma komutu ciktida
  * ELLE KOL : `--ev-haritasi-kur` tohumu okur, config YOKSA uretir, VARSA EZMEZ
Iki yolun ayristigi OLCULUR — bkz. ME4.

MUTANTLAR (her biri OLDURDUGU vakayi ADIYLA kanitlar — [[K182 hedef-kol atfi]]):
  ME1 yukleyici hatada BOS DICT doner         -> F1+F2+F3'u oldurmeli
  ME2 sahiplik kumesi TEKRAR SABITLENIR       -> F6'yi oldurmeli
  ME3 bilinmeyen kok COZULUR olur             -> F4'u oldurmeli
  ME4 TOHUM runtime yukleyicisine BAGLANIR    -> F1'i oldurmeli (FaR'in
      (dosya yokken kendiliginden tohumdan okur)  reddedilen onerisi birebir)
  ME0 ESDEGER KONTROL (davranisi degistirmez) -> HICBIR SEYI oldurmemeli
🔴 ME1 ile ME4 AYNI DEGILDIR ve kume esitligiyle ayrilir: ME1 uc bozuk hali de
oldurur (bos tablo GECERLI sayilir), ME4 YALNIZ "dosya yok" halini oldurur
(dosya VAR ama bozuk/bos ise sessiz dusus tetiklenmez). Ayni hedefe atanmis iki
mutant birbirini golgeler ([[ad-iki-rolde-mutanti-golgeler]]).

KABUL:
  python3 tools/ev-haritasi-kapisi-test.py
    -> rc=0, `VAKA=9/9 MUTANT=4/4 KONTROL=1/1` (yerel duzlem).

Disiplin: canli `~/.claude/cron/evler.json`'a YAZMAZ, canli defterlere
DOKUNMAZ, ag YOK. Butun fiksturler `tempfile.mkdtemp()` altinda ve is bitince
SILINIR (Okan diski).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BU_DIZIN = os.path.dirname(os.path.abspath(__file__))
REPO_KOK = os.path.abspath(os.path.join(BU_DIZIN, os.pardir))
T4 = os.path.join(BU_DIZIN, "parti-borc-kapisi.py")
N2B = os.path.join(BU_DIZIN, "parti-kapisi.py")
SAHIPLIK = os.path.join(BU_DIZIN, "sahiplik-kapisi.py")

# Canli tek kaynak + not dosyasi (F7 icin OKUNUR, yazilmaz).
CANLI_KONFIG = "/Users/okan/.claude/cron/evler.json"
CANLI_NOT = "/Users/okan/.claude/cron/evler-NOT.md"
TOHUM = os.path.join(BU_DIZIN, "evler-tohum.json")

OLCULEMEDI_JETON = "T4-OLCULEMEDI"
# 🔴 RED'i cikmaz sokak olmaktan cikaran satirin SABIT jetonu + bayragi.
# "hata verdi" YETMEZ: fikstur TAM KOMUTUN basildigini iddia eder.
KURTARMA_JETON = "KURTARMA:"
KURTARMA_BAYRAK = "--ev-haritasi-kur"

# F7 — tasinan gerekce yorumlarinin AYIRT EDICI cumleleri. Bunlar bulunmuyorsa
# tasima KAYIPLIDIR. (Kisa parcalar secildi: bicimlendirme degisse de anlam
# tasiyan cekirdek ayni kalir.)
NOT_CAPALARI = (
    ("BaBa/27Agu-a", "BaBa'nin satiri BAYATTI"),
    ("BaBa/27Agu-b", "BaBa KraL'da oturur"),
    ("BaBa/27Agu-c", "/Users/okan/dev/pruvo-advisor"),
    ("BaBa/27Agu-d", "BaBa'nin defteri/postasi KraL'in dizininde ARANIYORDU"),
    ("FaR/2Eyl-a", "Faralya evi acildi"),
    ("FaR/2Eyl-b", "/Users/okan/dev/faralya"),
    ("FaR/2Eyl-c", "otel altyapi"),
    ("FaR/2Eyl-d", "N2B-DEFTER-YOK"),
    ("ortak-a", "bilinmeyen kok HALA cozulemez"),
    ("ortak-b", "fail-closed KORUNUR"),
)

# Fikstur ev haritasi — CANLI tablonun kopyasi DEGIL; F4/F5 icin gereken en
# kucuk kume (bir "bilinen" ev + FaR).
FAR_DEPO_KOKU = "/Users/okan/dev/faralya"
KRAL_DEPO_KOKU = "/Users/okan/dev/pruvo"


def _proje_dizini(depo_kok):
    """Depo koku -> Claude proje dizini (`/` -> `-`). N2B ile AYNI kural."""
    mutlak = os.path.abspath(depo_kok).rstrip("/")
    return "/Users/okan/.claude/projects/" + mutlak.replace("/", "-")


def _kos(argv, konfig, mutant=None):
    """Bir kapiyi ALT SUREC olarak kosar; (rc, cikti) doner.

    Konfig ORTAM DEGISKENIYLE enjekte edilir — canli dosyaya dokunulmaz.
    `mutant` verilirse betigin YAMALI kopyasi kosulur (bkz. `_mutant_kopya`).
    """
    ortam = dict(os.environ)
    if konfig is None:
        ortam.pop("PRUVO_EVLER_JSON", None)
    else:
        ortam["PRUVO_EVLER_JSON"] = konfig
    p = subprocess.run([sys.executable] + argv, capture_output=True, text=True,
                       env=ortam, cwd=REPO_KOK)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# ---------------------------------------------------------------------------
# MUTANTLAR — kaynagi gecici bir kopyaya YAMALAYIP kosarız. CANLI GOVDE
# DEGISMEZ ([[mutant-canli-govdede-yasamaz]] tersi: burada canli govde
# korunur, mutant kopyada yasar ve kopya is bitince SILINIR).
# Her yama, GERCEKTEN degistirdigi metni CAPA olarak dogrular; capa
# bulunamazsa mutant "ULASMADI" sayilir ve batarya KIRMIZI yanar
# ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
# ---------------------------------------------------------------------------
MUTANT_YAMALARI = {
    # ME1 — TEK IDDIA: "BOS TABLO GECERLI SAYILIR" (fail-OPEN). Iddia KODDA
    # IKI KATMANDA yasadigi icin yama da iki katmani birden acar; aksi halde
    # ikinci katman mutanti KURTARIR ve mutant "ulasmadi" olur
    # ([[artik-yuzey-mutant-dedektorunu-korlestirir]]).
    "ME1": [
        # (a) yukleyici sarmali: HER hata yolu bos dict doner (tek capa, uc
        # hata yolunu birden kapsar — yukleyicinin ICINDEKI raise'lar
        # `_olculemedi()` sarmalindan gectigi icin ayri ayri yamalanmaz).
        (T4,
         "    try:\n"
         "        return ev_haritasi_yukle(yol), None\n"
         "    except EvHaritasiOlculemedi as e:\n"
         "        return None, str(e)",
         "    try:\n"
         "        return ev_haritasi_yukle(yol), None\n"
         "    except EvHaritasiOlculemedi as e:\n"
         "        return {}, None   # ME1 MUTANT: bos tablo GECERLI sayilir"),
        # (b) modul baglamasi: bos dict artik None'a CEVRILMEZ.
        # 🔴 CAPA IKI SATIRLIDIR: tek satirlik hali `ev_haritasi_tazele()`
        # govdesindeki GIRINTILI kopyayla da eslesir ve mutant YANLIS YERE
        # duserdi ([[mutant-yardimcisi-neyi-yamadigi-imzasindan-okunmaz]]).
        (T4,
         "EV_DIZIN, EV_HARITASI_HATA = _harita_baglayici()\n"
         "EV_BILINEN = frozenset(EV_DIZIN) if EV_DIZIN else None",
         "EV_DIZIN, EV_HARITASI_HATA = _harita_baglayici()\n"
         "EV_BILINEN = frozenset(EV_DIZIN) if EV_DIZIN is not None else None"
         "   # ME1 MUTANT"),
        # (c) ayni iddia `ev_haritasi_tazele()` govdesinde de yasar
        (T4,
         "    EV_BILINEN = frozenset(EV_DIZIN) if EV_DIZIN else None\n"
         "    return EV_DIZIN, EV_HARITASI_HATA",
         "    EV_BILINEN = frozenset(EV_DIZIN) if EV_DIZIN is not None else None"
         "   # ME1 MUTANT\n"
         "    return EV_DIZIN, EV_HARITASI_HATA"),
    ],
    # ME2 — sahiplik kumesi TEKRAR SABITLENIR (ikinci tablo geri gelir).
    "ME2": [
        (SAHIPLIK,
         "EV_BILINEN, EV_BILINEN_HATA = EV_BILINEN_COZ()",
         "EV_BILINEN, EV_BILINEN_HATA = "
         "({\"KraL\", \"MaCiT\", \"TeKiN\"}, None)   # ME2 MUTANT"),
    ],
    # ME3 — bilinmeyen kok COZULUR olur (fail-closed kaybolur).
    "ME3": [
        (N2B,
         "    return None, \"depo koku bilinen bir eve cozulemedi: %s\" % depo_kok",
         "    return \"KraL\", None   # ME3 MUTANT: bilinmeyen kok cozulur"),
    ],
    # 🔴 ME4 — FaR'IN REDDEDILEN ONERISI BIREBIR: "dosya yoksa gomulu tabloya
    # DUSSUN". Tohum RUNTIME yukleyicisine baglanir -> config yokken kapi
    # sessizce gecer. Bu mutant F1'i (ve YALNIZ F1'i) oldurmelidir: dosya VAR
    # ama bozuk/bos oldugunda dusus tetiklenmez, yani ME1'den AYRISIR.
    "ME4": [
        (T4,
         "    try:\n"
         "        return ev_haritasi_yukle(yol), None\n"
         "    except EvHaritasiOlculemedi as e:\n"
         "        return None, str(e)",
         "    try:\n"
         "        return ev_haritasi_yukle(yol), None\n"
         "    except EvHaritasiOlculemedi as e:\n"
         "        if not os.path.exists(yol or evler_json_yolu()):\n"
         "            return ev_haritasi_yukle(tohum_yolu()), None"
         "   # ME4 MUTANT: SESSIZ DUSUS\n"
         "        return None, str(e)"),
    ],
    # ME0 — ESDEGER KONTROL: yalnizca bir yorum satiri eklenir.
    "ME0": [
        (T4,
         "ACIK_KALEM_DOSYA = \"memory/acik-kalemler.md\"",
         "# ME0 esdeger kontrol — davranis DEGISMEZ\n"
         "ACIK_KALEM_DOSYA = \"memory/acik-kalemler.md\""),
    ],
}


def _mutant_kopya(kok, ad):
    """Yamali bir tools/ kopyasi uretir; (yeni_tools_dizini, hata) doner."""
    hedef = os.path.join(kok, "mutant-" + ad)
    if os.path.isdir(hedef):
        shutil.rmtree(hedef)
    shutil.copytree(BU_DIZIN, hedef,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for kaynak, capa, yeni in MUTANT_YAMALARI[ad]:
        yol = os.path.join(hedef, os.path.basename(kaynak))
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        # 🔴 CAPA TEKIL OLMALI: birden fazla eslesme, mutantin YANLIS YERE
        # dusmesi demektir ve "mutant ulasmadi"yi gorunmez kilar.
        n = metin.count(capa)
        if n != 1:
            return None, ("CAPA %s (%s icinde, %d eslesme): %r"
                          % ("BULUNAMADI" if n == 0 else "COKLU-ESLESME",
                             os.path.basename(kaynak), n, capa[:70]))
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin.replace(capa, yeni, 1))
    return hedef, None


# ---------------------------------------------------------------------------
# VAKALAR
# ---------------------------------------------------------------------------
def _fikstur_konfigler(kok):
    """(yok, bozuk, bos, dolu_farsiz, dolu_farli) yollari."""
    os.makedirs(kok, exist_ok=True)
    yok = os.path.join(kok, "yok.json")            # kasten YAZILMAZ
    bozuk = os.path.join(kok, "bozuk.json")
    bos = os.path.join(kok, "bos.json")
    farsiz = os.path.join(kok, "farsiz.json")
    farli = os.path.join(kok, "farli.json")
    with open(bozuk, "w", encoding="utf-8") as f:
        f.write("{ \"KraL\": bu gecerli json degil ,,, ")
    with open(bos, "w", encoding="utf-8") as f:
        json.dump({}, f)
    with open(farsiz, "w", encoding="utf-8") as f:
        json.dump({"_not": "FaR YOK — bilinmeyen kok kolu",
                   "KraL": _proje_dizini(KRAL_DEPO_KOKU)}, f)
    with open(farli, "w", encoding="utf-8") as f:
        json.dump({"_not": "FaR VAR — pozitif kol",
                   "KraL": _proje_dizini(KRAL_DEPO_KOKU),
                   "FaR": _proje_dizini(FAR_DEPO_KOKU)}, f)
    return yok, bozuk, bos, farsiz, farli


def _ev_coz_kos(kok, tools_dizini, konfig, depo_kok):
    """`parti-kapisi.ev_coz` ALT SURECTE cagrilir; `EV=<ad>` ya da `EV=-` basar.

    🔴 Prob betigi IZOLASYON KOKUNE yazilir, `tools/` icine DEGIL: repo calisma
    agacinda artik birakmak yasaktir (Okan disk kurali) ve birakilan artik
    `ci-kapsam` kesfine dusup sahte kapsam uretirdi.
    """
    os.makedirs(kok, exist_ok=True)
    betik = os.path.join(kok, "_ev-coz-probu.py")
    with open(betik, "w", encoding="utf-8") as f:
        f.write(
            "import importlib.util, os, sys\n"
            "spec = importlib.util.spec_from_file_location('n2b', %r)\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "ev, hata = m.ev_coz(sys.argv[1])\n"
            "print('EV=%%s' %% (ev or '-'))\n"
            "print('HATA=%%s' %% (hata or '-'))\n"
            % os.path.join(tools_dizini, "parti-kapisi.py"))
    return _kos([betik, depo_kok], konfig)


def vakalar(kok, tools_dizini):
    """7 vakayi kosar; [(ad, gecti, satir)] doner."""
    t4 = os.path.join(tools_dizini, "parti-borc-kapisi.py")
    sahiplik = os.path.join(tools_dizini, "sahiplik-kapisi.py")
    yok, bozuk, bos, farsiz, farli = _fikstur_konfigler(kok)
    sonuc = []

    # --- F1/F2/F3: uc bozuk hal -> RED + sifir-disi rc + OLCULEMEDI jetonu ---
    for ad, konfig, etiket in (("F1 KONFIG_YOK", yok, "dosya YOK"),
                               ("F2 KONFIG_BOZUK", bozuk, "gecersiz JSON"),
                               ("F3 KONFIG_BOS", bos, "gecerli ama {}")):
        rc, cikti = _kos([t4, "--rapor"], konfig)
        jeton = OLCULEMEDI_JETON in cikti
        red = "HUKUM: RED" in cikti
        # 🔴 "acik kalem yok" iddiasi SIZMAMALI: rapor tablosunda hicbir ev
        # GECER hukmu almamali (bos tablo tam olarak bunu yapardi).
        gecer_iddiasi = any(s.split()[-2:-1] == ["GECER"] or " GECER " in s
                            for s in cikti.splitlines()
                            if s.strip().startswith(("KraL", "MaCiT", "ArTisT",
                                                     "HocA", "TeKiN", "BaBa",
                                                     "ORTAK", "FaR")))
        # 🔴 UCUNCU YOL: RED cikmaz sokak OLMAMALI — kurtaran TAM KOMUT basilmali.
        kurtarma = [s for s in cikti.splitlines() if s.startswith(KURTARMA_JETON)]
        kurtarma_var = bool(kurtarma) and KURTARMA_BAYRAK in kurtarma[0]
        gecti = (rc != 0) and jeton and red and not gecer_iddiasi and kurtarma_var
        sonuc.append((ad, gecti,
                      "%s -> rc=%d (sifir-disi=%s) OLCULEMEDI_JETON=%s RED=%s "
                      "ACIK_KALEM_YOK_IDDIASI=%s KURTARMA_KOMUTU=%s"
                      % (etiket, rc, rc != 0, jeton, red, gecer_iddiasi,
                         (kurtarma[0][len(KURTARMA_JETON):].strip()
                          if kurtarma_var else "🔴 YOK"))))

    # --- F4: bilinmeyen depo koku HALA cozulemez ------------------------------
    rc, cikti = _ev_coz_kos(kok, tools_dizini, farsiz, FAR_DEPO_KOKU)
    ev = next((s.split("=", 1)[1] for s in cikti.splitlines()
               if s.startswith("EV=")), "?")
    gecti = (ev == "-")
    sonuc.append(("F4 BILINMEYEN_KOK", gecti,
                  "FaR girisi YOKken %s -> EV=%s (beklenen '-': fail-closed "
                  "davranis DEGISMEDI)" % (FAR_DEPO_KOKU, ev)))

    # --- F5: FaR girisi VARKEN Faralya koku COZULUR (pozitif kol) -------------
    rc, cikti = _ev_coz_kos(kok, tools_dizini, farli, FAR_DEPO_KOKU)
    ev5 = next((s.split("=", 1)[1] for s in cikti.splitlines()
                if s.startswith("EV=")), "?")
    gecti = (ev5 == "FaR")
    sonuc.append(("F5 FAR_POZITIF", gecti,
                  "FaR girisi VARken %s -> EV=%s (beklenen FaR)"
                  % (FAR_DEPO_KOKU, ev5)))

    # --- F6: TEK KAYNAK — sahiplik kumesi T4'unkiyle AYNI ---------------------
    betik = os.path.join(kok, "_tek-kaynak-probu.py")   # izolasyon kokune
    with open(betik, "w", encoding="utf-8") as f:
        f.write(
            "import importlib.util\n"
            "def y(ad, yol):\n"
            "    s = importlib.util.spec_from_file_location(ad, yol)\n"
            "    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
            "    return m\n"
            "t4 = y('t4', %r)\n"
            "sh = y('sh', %r)\n"
            "print('T4=%%s' %% ','.join(sorted(t4.EV_BILINEN or [])))\n"
            "print('SAHIPLIK=%%s' %% ','.join(sorted(sh.EV_BILINEN or [])))\n"
            % (t4, sahiplik))
    rc, cikti = _kos([betik], farli)
    t4_kume = next((s.split("=", 1)[1] for s in cikti.splitlines()
                    if s.startswith("T4=")), "?")
    sh_kume = next((s.split("=", 1)[1] for s in cikti.splitlines()
                    if s.startswith("SAHIPLIK=")), "??")
    gecti = (t4_kume == sh_kume) and t4_kume not in ("", "?")
    sonuc.append(("F6 TEK_KAYNAK", gecti,
                  "T4={%s} SAHIPLIK={%s} (esit olmali — ikinci tablo YOK)"
                  % (t4_kume, sh_kume)))

    # --- F9: `--ev-haritasi-kur` URETIR ama EZMEZ (hermetik, iki kosum) -------
    # 🔴 IKI KOSUM DA GOSTERILIR. Ezme yasagi bos bir iddia degil: 1. kosumdan
    # sonra dosyaya ELLE bir ev eklenir (FaR'in satirinin benzeri) ve 2. kosumun
    # onu KORUDUGU olculur. Yalniz "ZATEN VAR dedi"ye bakmak, ezip ayni metni
    # basan bir gerileme icin KOR olurdu.
    kur_hedef = os.path.join(kok, "yeni-mac", "evler.json")
    rc1, c1 = _kos([t4, "--ev-haritasi-kur", "--ev-haritasi-hedef", kur_hedef], None)
    uretildi = os.path.isfile(kur_hedef)
    ev_sayisi_1 = 0
    if uretildi:
        try:
            with open(kur_hedef, encoding="utf-8") as f:
                v = json.load(f)
            ev_sayisi_1 = len([k for k in v if not k.startswith("_")])
            v["ZzTest"] = "/Users/okan/.claude/projects/-Users-okan-dev-zztest"
            with open(kur_hedef, "w", encoding="utf-8") as f:
                json.dump(v, f, ensure_ascii=False, indent=2)
        except (OSError, ValueError):
            uretildi = False
    rc2, c2 = _kos([t4, "--ev-haritasi-kur", "--ev-haritasi-hedef", kur_hedef], None)
    korundu = False
    if uretildi:
        try:
            with open(kur_hedef, encoding="utf-8") as f:
                korundu = "ZzTest" in json.load(f)
        except (OSError, ValueError):
            korundu = False
    gecti = (rc1 == 0 and uretildi and ev_sayisi_1 > 0
             and rc2 == 0 and "ZATEN VAR" in c2 and korundu
             and "YAZILDI" in c1)
    sonuc.append(("F9 KUR_EZMEZ", gecti,
                  "1.kosum rc=%d URETTI=%s ev=%d · 2.kosum rc=%d ZATEN_VAR=%s "
                  "ELLE_EKLENEN_KORUNDU=%s"
                  % (rc1, uretildi, ev_sayisi_1, rc2, "ZATEN VAR" in c2, korundu)))

    # --- F8: TOHUM KAPSAMI — canli tablodaki her ev tohumda DA var mi? -------
    # 🔴 YEREL DUZLEM. Neden kapi: Okan yeni Mac'e geciyor; `~/.claude/cron`
    # tasinmazsa bootstrap TOHUMDAN yapilir. Tohum bir evi tasimiyorsa o ev
    # yeni makinede SESSIZCE kaybolur — FaR vakasinin birebir tekrari.
    if not os.path.isfile(CANLI_KONFIG):
        sonuc.append(("F8 TOHUM_KAPSAM", None,
                      "KAPSAM_DISI — %s bu duzlemde YOK (yerel-duzlem vakasi)"
                      % CANLI_KONFIG))
    else:
        def _evler(yol):
            with open(yol, encoding="utf-8") as f:
                return {k for k in json.load(f) if not k.startswith("_")}
        try:
            canli, tohum_evleri = _evler(CANLI_KONFIG), _evler(TOHUM)
            eksik_ev = sorted(canli - tohum_evleri)
            sonuc.append(("F8 TOHUM_KAPSAM", not eksik_ev,
                          "canli=%d tohum=%d · tohumda EKSIK=%s"
                          % (len(canli), len(tohum_evleri),
                             ",".join(eksik_ev) or "yok")))
        except (OSError, ValueError) as e:
            sonuc.append(("F8 TOHUM_KAPSAM", False, "OKUNAMADI: %s" % e))

    # --- F7: gerekce yorumlari KAYIPSIZ --------------------------------------
    # 🔴 UC HAL, IKI KOVA DEGIL: dosya YOKSA bu vaka KAPSAM_DISI'dir (kusur
    # DEGIL) — kosucuda (CI) `~/.claude/cron` hattinin ucu de yoktur. Sessizce
    # "gecti" SAYILMAZ; ayri bir kovada ADIYLA raporlanir
    # ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    if not os.path.isfile(CANLI_NOT):
        sonuc.append(("F7 NOT_KAYIPSIZ", None,
                      "KAPSAM_DISI — %s bu duzlemde YOK (yerel-duzlem vakasi; "
                      "kosucuda ~/.claude/cron hatti yoktur)" % CANLI_NOT))
        return sonuc
    try:
        with open(CANLI_NOT, encoding="utf-8") as f:
            not_metni = f.read()
    except OSError as e:
        sonuc.append(("F7 NOT_KAYIPSIZ", False,
                      "%s OKUNAMADI: %s" % (CANLI_NOT, e)))
        return sonuc
    eksik = [ad for ad, capa in NOT_CAPALARI if capa not in not_metni]
    sonuc.append(("F7 NOT_KAYIPSIZ", not eksik,
                  "%s icinde %d/%d capa bulundu%s"
                  % (os.path.basename(CANLI_NOT),
                     len(NOT_CAPALARI) - len(eksik), len(NOT_CAPALARI),
                     ("; EKSIK=" + ",".join(eksik)) if eksik else "")))
    return sonuc


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
# F1-F6 + F9 HER duzlemde kosar (hermetik); F7 ve F8 yerel-duzlemdir.
KAPSAM_TABANI = 7

MUTANT_HEDEFI = {
    "ME1": ("F1 KONFIG_YOK", "F2 KONFIG_BOZUK", "F3 KONFIG_BOS"),
    "ME2": ("F6 TEK_KAYNAK",),
    "ME3": ("F4 BILINMEYEN_KOK",),
    "ME4": ("F1 KONFIG_YOK",),
}


def main():
    kok = tempfile.mkdtemp(prefix="k361-ev-haritasi-")
    try:
        print("K361 EV HARITASI BATARYASI — hermetik (canli evler.json'a DOKUNMAZ)")
        print("izolasyon koku: %s" % kok)
        print("canli tek kaynak (yalniz F7 icin OKUNUR): %s" % CANLI_KONFIG)
        print("")

        print("TABAN (mutantsiz):")
        taban = vakalar(kok, BU_DIZIN)
        for ad, gecti, satir in taban:
            print("  %-20s %s  %s"
                  % (ad, "▫️" if gecti is None else ("✓" if gecti else "✗"),
                     satir))
        vaka_gecen = sum(1 for _a, g, _s in taban if g is True)
        vaka_kapsamda = sum(1 for _a, g, _s in taban if g is not None)
        kapsam_disi = len(taban) - vaka_kapsamda
        print("VAKA=%d/%d KAPSAM_DISI=%d" % (vaka_gecen, vaka_kapsamda, kapsam_disi))
        print("")

        taban_gecen = {ad for ad, g, _s in taban if g is True}
        mutant_basari = 0
        mutant_toplam = len(MUTANT_HEDEFI)
        for ad in sorted(MUTANT_HEDEFI):
            hedefler = MUTANT_HEDEFI[ad]
            print("MUTANT %s -> hedef vaka(lar): %s" % (ad, ", ".join(hedefler)))
            tools_m, hata = _mutant_kopya(kok, ad)
            if hata:
                print("  ✗ %s (mutant ULASMADI)" % hata)
                continue
            m_sonuc = vakalar(os.path.join(kok, "m-" + ad), tools_m)
            m_gecen = {a for a, g, _s in m_sonuc if g is True}
            oldurulen = sorted(taban_gecen - m_gecen)
            fazla = [x for x in oldurulen if x not in hedefler]
            eksik = [x for x in hedefler if x not in oldurulen]
            for a, g, s in m_sonuc:
                if a in hedefler:
                    print("    | %-20s %s  %s" % (a, "✓" if g else "✗", s))
            print("  oldurulen: %s" % (", ".join(oldurulen) or "(hicbiri)"))
            if not eksik and not fazla:
                print("  SONUÇ: BEKLENDI YAKALANDI (hedef kol atfi TAM)")
                mutant_basari += 1
            else:
                print("  SONUÇ: KIRMIZI — eksik=%s fazla=%s"
                      % (eksik or "-", fazla or "-"))
            print("")

        print("KONTROL ME0 (esdeger — HICBIR seyi oldurmemeli)")
        tools_k, hata = _mutant_kopya(kok, "ME0")
        kontrol_basari = 0
        if hata:
            print("  ✗ %s" % hata)
        else:
            k_sonuc = vakalar(os.path.join(kok, "m-ME0"), tools_k)
            k_gecen = {a for a, g, _s in k_sonuc if g is True}
            oldurulen = sorted(taban_gecen - k_gecen)
            if not oldurulen:
                print("  SONUÇ: GECTI (esdeger yama hicbir vakayi oldurmedi — "
                      "batarya ambiyans olcmuyor)")
                kontrol_basari = 1
            else:
                print("  SONUÇ: KIRMIZI — esdeger yama %s vakasini oldurdu "
                      "(batarya kirilgan)" % ", ".join(oldurulen))
        print("")

        ozet = ("VAKA=%d/%d MUTANT=%d/%d KONTROL=%d/1 KAPSAM_DISI=%d"
                % (vaka_gecen, vaka_kapsamda, mutant_basari, mutant_toplam,
                   kontrol_basari, kapsam_disi))
        print(ozet)
        # 🔴 KAPSAM TABANI SAYIYLA CIVILI: F1-F6 HER duzlemde kosar. Kapsam
        # 6'nin altina duserse batarya "ihlal yok" diye YESIL yanmaz
        # ([[batarya-kapsam-tabani-sayiyla-civilenir]]).
        if vaka_kapsamda < KAPSAM_TABANI:
            print("OLCULEMEDI: kapsam %d < taban %d — batarya YESIL SAYILMAZ"
                  % (vaka_kapsamda, KAPSAM_TABANI))
            return 2
        tamam = (vaka_gecen == vaka_kapsamda and mutant_basari == mutant_toplam
                 and kontrol_basari == 1)
        return 0 if tamam else 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

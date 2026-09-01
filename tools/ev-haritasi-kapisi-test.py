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
                      `evler-NOT.md`'de KAYIPSIZ duruyor

MUTANTLAR (her biri OLDURDUGU vakayi ADIYLA kanitlar — [[K182 hedef-kol atfi]]):
  ME1 yukleyici hatada BOS DICT doner        -> F1+F2+F3'u oldurmeli
  ME2 sahiplik kumesi TEKRAR SABITLENIR      -> F6'yi oldurmeli
  ME3 bilinmeyen kok COZULUR olur            -> F4'u oldurmeli
  ME0 ESDEGER KONTROL (davranisi degistirmez) -> HICBIR SEYI oldurmemeli

KABUL:
  python3 tools/ev-haritasi-kapisi-test.py
    -> rc=0, `VAKA=7/7 MUTANT=3/3 KONTROL=1/1`.

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

OLCULEMEDI_JETON = "T4-OLCULEMEDI"

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
        # (a) yukleyici: uc hata yolunun HEPSI bos dict doner
        (T4,
         "    if not harita:\n"
         "        # 🔴 EN ONEMLI KOL: gecerli JSON ama SIFIR ev.",
         "    if not harita:\n"
         "        return {}   # ME1 MUTANT: bos tablo GECERLI sayilir\n"
         "        # 🔴 EN ONEMLI KOL: gecerli JSON ama SIFIR ev."),
        (T4,
         "    except OSError as e:\n"
         "        raise EvHaritasiOlculemedi(",
         "    except OSError as e:\n"
         "        return {}   # ME1 MUTANT\n"
         "        raise EvHaritasiOlculemedi("),
        (T4,
         "    except ValueError as e:\n"
         "        raise EvHaritasiOlculemedi(",
         "    except ValueError as e:\n"
         "        return {}   # ME1 MUTANT\n"
         "        raise EvHaritasiOlculemedi("),
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
        gecti = (rc != 0) and jeton and red and not gecer_iddiasi
        sonuc.append((ad, gecti,
                      "%s -> rc=%d (sifir-disi=%s) OLCULEMEDI_JETON=%s RED=%s "
                      "ACIK_KALEM_YOK_IDDIASI=%s"
                      % (etiket, rc, rc != 0, jeton, red, gecer_iddiasi)))

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
# F1-F6 HER duzlemde kosar (hermetik); yalniz F7 yerel-duzlemdir.
KAPSAM_TABANI = 6

MUTANT_HEDEFI = {
    "ME1": ("F1 KONFIG_YOK", "F2 KONFIG_BOZUK", "F3 KONFIG_BOS"),
    "ME2": ("F6 TEK_KAYNAK",),
    "ME3": ("F4 BILINMEYEN_KOK",),
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

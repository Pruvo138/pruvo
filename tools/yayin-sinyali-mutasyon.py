#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN SINYALI AYRIMI — IKI YONLU CURUTME BATARYASI (5 Agu 2026).

NEDEN VAR (IKI KEZ OLCULEN MALIYET)
───────────────────────────────────
GitHub bir KOSUMUN `conclusion`'ini o kosumdaki TUM joblarin EN KOTUSUNDEN turetir.
Bloklamayan nobet/alarm joblari `deploy.yml` icindeyken kirmizilari YAYIN kosumunun
rengini boyuyordu. Sonuc: 28 ardisik kosum `failure` gorundu, mimar "yayin 11 saattir
durdu, ~1.500 urun sitede yok" hukmunu verip deftere/posta kutusuna/Okan'a yazdi.
JOB duzeyinde olculdugunde o 28 kosumun 14'unde `deploy`+`yayin` YESIL kosmustu;
gercek hasar TEK commit / 447 urundu. Ayni gun ekip bir kez daha "deploy kirmizi"
sanip yanlis kaynagi aradi. Sinif: [[hukum-yanlis-birimde]].

COZUM (susturma DEGIL, KANAL AYRIMI): bloklamayan joblar `.github/workflows/nobet.yml`
is akisina TASINDI. Ayni komut, ayni fail-closed cikis kodu, AYRI `conclusion`.

🔴 BU BATARYA NEDEN IKI YONLU (mimar olcutu — tek yon KABUL EDILMEZ)
────────────────────────────────────────────────────────────────────
"Bloklamayan kirmizi kosumu boyamasin" (YON A) TEK BASINA en kotu yolla da
saglanabilir: her seyi susturmak. O yuzden AYNI bataryada YON B olculur — "yayini
DURDURAN bir job kirmizi olunca kosum KIRMIZI olmali VE `deploy` KOSMAMALI".
A'yi gecen ama B'yi gecmeyen bir duzenleme GERCEK yayin arizasini da sessizlestirir.

Ek olarak, "kosum yesillessin" diye `deploy: needs` listesini DARALTMA yolu bir
mutantla KAPATILIR: bu, deploy.yml'in kendi yorumunun YASAKLADIGI sessiz fail-open'dir.

KANONIK OLCUT — TEK FONKSIYON
─────────────────────────────
Kosum rengi simulatoru `tools/is-akisi-kapisi.py :: kosum_sonucu()`ten IMPORT edilir;
burada IKINCI bir model YAZILMAZ. Kabul ile kiyas ayri fonksiyonlardan turetilseydi
sessizce ayrisirlardi ([[kabul-araligi-karsilastirma-araligi]],
[[ikiz-tanim-sessiz-ayrisma]]).

KABUL = OLCULEN IDDIA SAYISI + ISARET, cikis kodu DEGIL: cokme (import hatasi, bos
tablo) kirmiziyla KARISTIRILMAZ ([[mutasyon-kaniti-yeniden-uretilebilir]]).

CANLI DOSYALARA DOKUNULMAZ: her mutant GECICI bir kopyaya uygulanir, kosum sonunda
canli dosyalarin sha256'si karsilastirilir ([[mutasyon-diske-yazma-tuzagi]]).

KULLANIM
    python3 tools/yayin-sinyali-mutasyon.py
"""
import hashlib
import importlib.util
import os
import shutil
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
WORKFLOW_DIZIN = os.path.join(ROOT, ".github", "workflows")
KAPI_YOLU = os.path.join(TOOLS, "is-akisi-kapisi.py")
DEPLOY = "deploy.yml"
NOBET = "nobet.yml"
# Mutasyona ugrayabilen canli dosyalar (sha256 nobeti).
DOKUNULMAZ = (os.path.join(WORKFLOW_DIZIN, DEPLOY),
              os.path.join(WORKFLOW_DIZIN, NOBET),
              KAPI_YOLU)


def _kapi_modulu():
    spec = importlib.util.spec_from_file_location("_isakisi_kapisi", KAPI_YOLU)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


IAK = _kapi_modulu()


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _oku(ad):
    with open(os.path.join(WORKFLOW_DIZIN, ad), encoding="utf-8") as f:
        return f.read()


def _govde(metin, etiket):
    g, hata = IAK.ayristir(metin)
    if hata or not isinstance(g, dict):
        raise SystemExit("OLCULEMEDI: %s ayristirilamadi -> %s" % (etiket, hata))
    return g


# ═══════════════════════════════════════════════════════════════════════════
# MUTANTLAR — is akisi metnine uygulanir, kapi GECICI kopyada kosturulur.
# (kod, aciklama, hedef_dosya, [(bulunacak, yerine), ...], KIRMIZI_olmali_mi)
# ═══════════════════════════════════════════════════════════════════════════
NEEDS_SATIRI = "    needs: [build, serit-a2, serit-a3, serit-a4]\n"

MUTANTLAR = (
    ("M1", "🔴 BLOKLAMAYAN ALARM JOB'U YAYIN IS AKISINA GERI KONDU: kirmizisi yayini "
           "durdurmaz ama kosumun conclusion'ini `failure` yapar -> 'yayin durdu' "
           "yanlis hukmu geri gelir (olculen bedel: 28 kosumun 14'unde deploy YESILDI)",
     DEPLOY, [("jobs:\n", "jobs:\n  zzz-alarm:\n    runs-on: ubuntu-latest\n"
                          "    steps:\n      - run: echo alarm\n")], True),
    ("M2", "🔴 `deploy: needs` LISTESI DARALTILDI (bir serit dusuruldu): 'kosum "
           "yesillessin' diye yapilan bu duzenleme o seritteki TUM kapilarin "
           "kirmizisini yayini DURDURMAZ hale getirir = SESSIZ FAIL-OPEN",
     DEPLOY, [(NEEDS_SATIRI, "    needs: [build, serit-a2, serit-a3]\n")], True),
    ("M3", "🔴 `deploy: needs` BUTUNUYLE SILINDI: hicbir serit yayini durdurmaz",
     DEPLOY, [(NEEDS_SATIRI, "")], True),
    ("M4", "🔴 NOBET IS AKISININ `push` TETIGI KALDIRILDI: alarmlar main'e push'ta HIC "
           "kosmaz -> 'kirmizi bir yerde GORUNUR kalir' sarti duser (susturmanin "
           "sessiz bicimi)",
     NOBET, [("on:\n  push:\n    branches: [main]\n  workflow_dispatch:\n",
              "on:\n  workflow_dispatch:\n")], True),
    ("M5", "🔴 NOBET KOSUMU IPTALLE OLDURULEBILIR YAPILDI (`cancel-in-progress: true`): "
           "ard arda push'ta alarm kosumu iptal edilir, conclusion `cancelled` olur ve "
           "nobet HIC rapor etmez",
     NOBET, [("  cancel-in-progress: false\n", "  cancel-in-progress: true\n")], True),
    ("M6", "🔴 NOBET JOB'U `continue-on-error: true` ILE SUSTURULDU: bloklamamak SESSIZ "
           "OLMAK DEGILDIR — bu yazimla alarm KENDI kosumunun renginde de gorunmez",
     NOBET, [("  envanter:\n    runs-on: ubuntu-latest\n",
              "  envanter:\n    runs-on: ubuntu-latest\n    continue-on-error: true\n")],
     True),
    ("M7", "🔴 NOBET JOB'U DAIMA-YANLIS `if:` ILE OLDURULDU (ayni sinif, farkli yazim)",
     NOBET, [("  envanter:\n    runs-on: ubuntu-latest\n",
              "  envanter:\n    runs-on: ubuntu-latest\n    if: false\n")], True),
    ("M8", "🔴 NOBET SERIDI `uses:` ILE YAYIN GRAFIGINE GERI BAGLANDI: cagrilan joblar "
           "yayin kosumunun job grafiginde kosar ve rengini YINE boyar (ayrim fiilen "
           "geri alinir) — ustelik `needs`e de eklendigi icin G1/G8 SUSAR, KIRMIZI'yi "
           "TEK BASINA bu eksen yakmalidir",
     DEPLOY, [("jobs:\n", "jobs:\n  zzz-nobet-cagrisi:\n    uses: "
                          "./.github/workflows/%s\n" % NOBET),
              (NEEDS_SATIRI,
               "    needs: [build, serit-a2, serit-a3, serit-a4, zzz-nobet-cagrisi]\n")],
     True),
    ("M9", "🔴 PAGES YAYINI NOBET SERIDINE KAYDIRILDI: 'bu dosyanin tum joblari "
           "bloklamaz' hukmu YANLISLASIR ve gercek yayin arizasi B seridine tasinir",
     NOBET, [("      - name: \"Katalog envanteri: onceden var olan uretim-sureci "
              "ifsasi (RAPOR — yayini DURDURMAZ)\"\n",
              "      - uses: actions/deploy-pages@v4\n"
              "      - name: \"Katalog envanteri: onceden var olan uretim-sureci "
              "ifsasi (RAPOR — yayini DURDURMAZ)\"\n")], True),
    # ── KONTROLLER (YESIL kalmali; mimarin adiyla istedigi uc eksen) ──────────
    ("K1", "KONTROL: JOB SIRASI degistirildi (`yayin` job'u `deploy`den ONCE yazildi) "
           "— `needs:` grafigi AYNI, GitHub sirayi grafikten cozer",
     DEPLOY, "JOB_SIRASI", False),
    ("K2", "KONTROL: DAVRANIS DEGISTIRMEYEN YENIDEN ADLANDIRMA (is akisi `name:` ve bir "
           "adim adi degisti; icra edilen komut AYNI)",
     DEPLOY, [("name: Build & deploy to GitHub Pages\n",
               "name: Yayin hatti (Pages)\n")], False),
    ("K3", "KONTROL: `needs` LISTESINE DOKUNMAYAN BICIMSEL DEGISIKLIK (akis yazimi -> "
           "blok yazimi; kume ve kimlik AYNI)",
     DEPLOY, [(NEEDS_SATIRI, "    needs:\n      - build\n      - serit-a2\n"
                             "      - serit-a3\n      - serit-a4\n")], False),
    ("K4", "KONTROL: nobet seridine YENI bir alarm job'u eklendi (alarm eklemek serbest; "
           "yayin rengi etkilenmez)",
     NOBET, [("jobs:\n", "jobs:\n  zzz-yeni-alarm:\n    runs-on: ubuntu-latest\n"
                         "    steps:\n      - run: echo yeni\n")], False),
    ("K5", "KONTROL: deploy.yml'e YORUM satiri eklendi (semantik DEGISMEZ)",
     DEPLOY, [("jobs:\n", "# yorum — mutant kontrolu\njobs:\n")], False),
)


def _job_sirasi_mutanti(metin):
    """`yayin` job blogunu `deploy` blogunun ONUNE tasi (grafik AYNI kalir)."""
    bas = metin.index("\n  deploy:\n")
    y_bas = metin.index("\n  yayin:\n")
    deploy_blok = metin[bas:y_bas]
    # `yayin` job'u dosyanin SONUNA kadar surer (son job).
    yayin_blok = metin[y_bas:]
    return metin[:bas] + yayin_blok.rstrip("\n") + "\n" + deploy_blok.lstrip("\n")


def _mutant_metni(kod, temel, degisimler):
    if degisimler == "JOB_SIRASI":
        return _job_sirasi_mutanti(temel), 1
    yeni = temel
    uygulanan = 0
    for bul, koy in degisimler:
        if bul not in yeni:
            return None, 0
        yeni = yeni.replace(bul, koy, 1)
        uygulanan += 1
    return yeni, uygulanan


def _kapi_kosumu(dizin):
    """(hata_sayisi, iddia_sayisi) — Bolum G'yi GECICI dizinde kostur."""
    hatalar, iddia = IAK.yayin_sinyali_kontrol(dizin)
    return len(hatalar), iddia, hatalar


def main():
    baslangic = {y: _sha(y) for y in DOKUNULMAZ}
    dep_metin = _oku(DEPLOY)
    nob_metin = _oku(NOBET)
    dep_govde = _govde(dep_metin, DEPLOY)
    nob_govde = _govde(nob_metin, NOBET)

    olculen = 0
    kusur = []

    print("YAYIN SINYALI AYRIMI — IKI YONLU CURUTME")
    print("=" * 74)

    # ═══════════════════════════════════════════════════════════════════════
    # 1) KOSUM SONUCU SIMULASYONU — YON A ve YON B, AYRI AYRI IDDIALAR
    # ═══════════════════════════════════════════════════════════════════════
    print("\n1) KOSUM RENGI: YON A (bloklamayan kirmizi) + YON B (yayini durduran kirmizi)")
    dep_jobs = dep_govde["jobs"]
    nob_jobs = nob_govde["jobs"]
    yayin_isi = IAK._yayin_isi(dep_jobs)
    if yayin_isi is None:
        raise SystemExit("OLCULEMEDI: %s icinde Pages yayin job'u YOK" % DEPLOY)
    _zincir, bloklayan = IAK._yayin_zinciri(dep_jobs, yayin_isi)
    bloklayanlar = sorted(bloklayan - {yayin_isi})

    taban_sonuc, taban_kosan = IAK.kosum_sonucu(dep_govde, ())
    olculen += 1
    if taban_sonuc != "success" or yayin_isi not in taban_kosan:
        kusur.append("TABAN BOZUK: hicbir job kirmizi degilken kosum %r / kosan=%r"
                     % (taban_sonuc, sorted(taban_kosan)))
    print("   TABAN: kirmizi yok -> conclusion=%s · deploy KOSTU=%s"
          % (taban_sonuc, yayin_isi in taban_kosan))

    # YON A — nobet.yml'deki HER job tek tek kirmizi. IKI AYRI IDDIA.
    for job_id in sorted(nob_jobs):
        y_sonuc, y_kosan = IAK.kosum_sonucu(dep_govde, ())      # yayin kosumu etkilenmez
        n_sonuc, _n_kosan = IAK.kosum_sonucu(nob_govde, {job_id})
        olculen += 2
        if y_sonuc != "success" or yayin_isi not in y_kosan:
            kusur.append("YON A (A1) BOZUK [%s]: nobet job'u kirmizi iken YAYIN kosumu "
                         "%r (deploy kostu=%s) -> ayrim tutmuyor"
                         % (job_id, y_sonuc, yayin_isi in y_kosan))
        if n_sonuc != "failure":
            kusur.append("YON A (A2) BOZUK [%s]: alarm kirmizi ama NOBET kosumunun "
                         "conclusion'i %r -> alarm KENDI kanalinda GORUNMUYOR "
                         "(susturma, cozulen kusurun tersi)" % (job_id, n_sonuc))
        print("   A [%-16s] yayin kosumu=%s (DEGISMEDI) · nobet kosumu=%s (GORUNUR)"
              % (job_id, y_sonuc, n_sonuc))

    # YON B — yayini BLOKLAYAN her job tek tek kirmizi. IKI AYRI IDDIA.
    for job_id in bloklayanlar:
        sonuc, kosan = IAK.kosum_sonucu(dep_govde, {job_id})
        olculen += 2
        if sonuc != "failure":
            kusur.append("YON B (B1) BOZUK [%s]: yayini durduran job kirmizi ama kosum "
                         "%r -> gercek yayin arizasi SESSIZLESTIRILMIS" % (job_id, sonuc))
        if yayin_isi in kosan:
            kusur.append("YON B (B2) BOZUK [%s]: job kirmizi iken `%s` YINE KOSTU -> "
                         "kapi yayini DURDURMUYOR" % (job_id, yayin_isi))
        print("   B [%-16s] kosum=%s · deploy KOSTU=%s"
              % (job_id, sonuc, yayin_isi in kosan))

    # SINIR: yayin ARDILI (`yayin`) — kirmizisi kosumu boyar ve bu DOGRUDUR.
    ardillar = sorted(set(dep_jobs) - bloklayan - {yayin_isi})
    for job_id in ardillar:
        sonuc, kosan = IAK.kosum_sonucu(dep_govde, {job_id})
        olculen += 1
        if sonuc != "failure":
            kusur.append("SINIR BOZUK [%s]: yayin ARDILI kirmizi ama kosum %r -> "
                         "'urunler canliya alinamadi' hali GORUNMEZ olur"
                         % (job_id, sonuc))
        print("   SINIR [%-12s] kosum=%s (ardil kirmizisi = yayin zincirinin KENDI "
              "kusuru, boyamasi DOGRU)" % (job_id, sonuc))

    # ═══════════════════════════════════════════════════════════════════════
    # 2) KAPI MUTASYONU — Bolum G eksenleri TEK TEK kirmizi yakiyor mu
    # ═══════════════════════════════════════════════════════════════════════
    print("\n2) KAPI MUTASYONU (tools/is-akisi-kapisi.py :: yayin_sinyali_kontrol)")
    gecici = tempfile.mkdtemp(prefix="pruvo-yayin-sinyali-")
    try:
        for ad in os.listdir(WORKFLOW_DIZIN):
            shutil.copy2(os.path.join(WORKFLOW_DIZIN, ad), os.path.join(gecici, ad))
        taban_hata, taban_iddia, taban_liste = _kapi_kosumu(gecici)
        olculen += 1
        if taban_hata:
            kusur.append("KAPI TABANI KIRMIZI: mutasyonsuz kopyada %d hata -> mutant "
                         "sinyali GURULTUYE gomulur (%s)"
                         % (taban_hata, taban_liste[0].splitlines()[0]))
        if taban_iddia < 7:
            kusur.append("KAPI TABANI BOS: %d iddia olculdu (en az 7 bekleniyor) -> "
                         "kapi govdesi bosaltilmis olabilir" % taban_iddia)
        print("   TABAN: %d hata · %d iddia" % (taban_hata, taban_iddia))

        for kod, aciklama, hedef, degisimler, kirmizi_olmali in MUTANTLAR:
            temel = dep_metin if hedef == DEPLOY else nob_metin
            mutant, uygulanan = _mutant_metni(kod, temel, degisimler)
            olculen += 1
            if mutant is None or not uygulanan:
                kusur.append("%s: MUTANT URETILEMEDI (capa bayat) -> bu eksen "
                             "OLCULEMEDI, YESIL SAYILMAZ" % kod)
                print("   %s ⚠ capa bayat (%s)" % (kod, hedef))
                continue
            with open(os.path.join(gecici, hedef), "w", encoding="utf-8") as f:
                f.write(mutant)
            try:
                hata, iddia, liste = _kapi_kosumu(gecici)
            except Exception as e:                              # noqa: BLE001
                kusur.append("%s: KAPI COKTU (%s: %s) -> cokme KIRMIZI DEGILDIR"
                             % (kod, type(e).__name__, e))
                hata, iddia, liste = None, 0, []
            finally:
                with open(os.path.join(gecici, hedef), "w", encoding="utf-8") as f:
                    f.write(temel)
            if hata is None:
                continue
            if iddia < 7:
                kusur.append("%s: IDDIA SAYISI DUSTU (%d) -> kapi kirmizi degil COKMUS "
                             "olabilir" % (kod, iddia))
            oldu = hata > 0
            if oldu != kirmizi_olmali:
                kusur.append("%s: beklenen %s, olculen %s -> %s"
                             % (kod, "KIRMIZI" if kirmizi_olmali else "YESIL",
                                "KIRMIZI" if oldu else "YESIL", aciklama))
            print("   %s %s %-6s %s" % (
                "✔" if oldu == kirmizi_olmali else "✘", kod,
                "KIRMIZI" if oldu else "YESIL", aciklama.split(":")[0][:70]))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    # ═══════════════════════════════════════════════════════════════════════
    # 3) CANLI DOSYALAR DEGISMEDI MI
    # ═══════════════════════════════════════════════════════════════════════
    print("\n3) CANLI KAYNAKLAR DEGISMEDI MI")
    for yol in DOKUNULMAZ:
        olculen += 1
        if _sha(yol) != baslangic[yol]:
            kusur.append("CANLI DOSYA DEGISTI: %s -> mutasyon diske sizmis" % yol)
        print("   ✔ sha256 ayni: %s" % os.path.relpath(yol, ROOT))

    print("\n" + "=" * 74)
    oldurucu = sum(1 for m in MUTANTLAR if m[4])
    kontrol = sum(1 for m in MUTANTLAR if not m[4])
    print("OZET: %d iddia olculdu · %d oldurucu + %d kontrol mutanti · %d kusur"
          % (olculen, oldurucu, kontrol, len(kusur)))
    if kusur:
        for k in kusur:
            print("  ❌ " + k)
        return 1
    print("✅ CURUTME GECTI — YON A (bloklamayan kirmizi yayin kosumunu BOYAMIYOR + "
          "alarm KENDI kanalinda GORUNUYOR) ve YON B (yayini durduran kirmizi kosumu "
          "KIRMIZI yakiyor + deploy KOSMUYOR) AYRI AYRI olculdu; `deploy: needs` "
          "daraltan mutant KIRMIZI yandi, %d kontrol YESIL kaldi." % kontrol)
    return 0


if __name__ == "__main__":
    sys.exit(main())

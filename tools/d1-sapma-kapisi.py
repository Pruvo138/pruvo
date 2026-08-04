#!/usr/bin/env python3
"""D1 SAPMA ALARMI — "sapma oldu" sinyalinin KENDI KANALI (4 Agu 2026).

═══════════════════════════════════════════════════════════════════════════════
NEDEN VAR — IKI SORUYU TEK CIKIS KODUNA YIGMAK (OLCULEN KUSUR)
═══════════════════════════════════════════════════════════════════════════════
`d1-uzlastirici.yml` sapma bulunca BILEREK `exit 1` verir: sapmanin KENDISI bir
ust-yol kacagidir (pre-push kancasi / CI D1 adimi / elle push) ve onarildi diye o
kacak yok olmaz. 4 Agu'da bu is akisi `workflow_call` ile deploy.yml'in BLOKLAMAYAN
`d1-kadans` koluna baglandi (gerekce: GitHub cron kuyrugu 48 saatte nominal 192
tetiklemenin 7'sini teslim etti = %3,65; en uzun bosluk 17,6 saat).

YAN ETKI: `d1-kadans` `deploy: needs`'te OLMADIGI icin yayini DURDURMUYOR — ama
cagiran kosumun GENEL `conclusion`'ini `failure` yapiyordu. Boylece deploy.yml
kosumunun conclusion'i IKI ayri soruyu birden cevaplar oldu:
    "yayin calisti mi?"   ve   "D1 sapmasi var mi?"
Bu depoda olculmus sinif ([[hukum-yanlis-birimde]]): TOPLU SONUC TEKIL EKSENI GIZLER.
"deploy kosumu yesil mi" refleksiyle bakan biri yayini saglikli sanip sapmayi kacirir;
tersi de olur — kirmiziya alisan biri yayin GERCEKTEN bozuldugunda gormez.

COZUM SAPMAYI SUSTURMAK DEGIL (en kolay ve en yanlis yol o olurdu), KANALI AYIRMAK:
  * kadans kolunda ONARILAN sapma `d1-sapma-damgasi` artifact'ine yazilir, cagiran
    kosumun cikis kodu TEMIZ kalir -> deploy.yml conclusion'i YALNIZ yayin sagligi,
  * BU NOBETCI o damgayi okur ve KENDI kosumunda (d1-sapma-alarmi.yml, AYRI
    conclusion) KIRMIZI yanar -> sapma sinyali KAYBOLMAZ, YERI DEGISIR,
  * ONARILAMAYAN sapma bayraktan BAGIMSIZ olarak uzlastiricinin kendi kosumunda
    KIRMIZI kalir (ayri hukum: emniyet agi tutmadi).

═══════════════════════════════════════════════════════════════════════════════
🔴 NEDEN CRON DEGIL, `workflow_run` (olculmus gerekce)
═══════════════════════════════════════════════════════════════════════════════
Bu depoda alarm kollari bugune dek cron'a bagliydi; 4 Agu'da cron TESLIMININ kendisi
olculdu ve CURUDU (yukaridaki %3,65 / 17,6 saat). Sapma kanalini cron'a baglamak,
tam da kadans kolunun cozdugu sorunu geri getirirdi. `d1-sapma-alarmi.yml` bu yuzden
`workflow_run` ile deploy.yml'in BITISINDE tetiklenir: depo saatte onlarca push aliyor,
yani kanal push kadans'iyla AYNI siklikta calisir ve GitHub'in zamanlanmis kuyruguna
HIC bagimli degildir. Kendi KOSUMU ve kendi `conclusion`'i vardir -> yayin sagligi ile
sapma sinyali AYRI birimlerde okunur.

YAYINI DURDURAMAZ (yapisal, beyan degil): `push`/`workflow_call` tetikleyicisi YOK ·
deploy.yml'e `needs:` ile bagli DEGIL · ayri `concurrency` grubu · ve zaten deploy
BITTIKTEN sonra kosar. Bu sartlari tools/cron-nabiz-kapisi.py::kadans_kablosu OLCER.

═══════════════════════════════════════════════════════════════════════════════
CIKIS KODLARI (kabukta YUTULMAZ — `|| true` bu depoda beyansiz fail-open sayilir)
═══════════════════════════════════════════════════════════════════════════════
  0  temiz       — tetikleyen kosumda `d1-sapma-damgasi` YOK: o kosumda D1 sapmasi
                   OLCULDU ve SIFIRDI (ya da uzlastirma o kosumda hic kosmadi).
  1  sapma       — damga VAR: D1 sapmasi olustu (onarildi ama ust-yol KACIRDI).
  2  olculemedi  — kosum kimligi cozulemedi / API okunamadi / yanit sekli bozuk.
                   SESSIZ YESIL DEGIL: kosum KIRMIZI yanar.

TEK KAYNAK: damga ADI ve IDDIASI tools/cron-nabiz-kapisi.py::DAMGA_KUTUGU'nden MODUL
olarak alinir. Ikinci kopya TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]); kutuk degisirse
bu nobetci de degisir, elle senkron yoktur.

KULLANIM
  python3 tools/d1-sapma-kapisi.py                 # canli olcum (TETIK_KOSUM env)
  python3 tools/d1-sapma-kapisi.py --gh-ozet       # + GITHUB_STEP_SUMMARY'ye yaz
  python3 tools/d1-sapma-kapisi.py --kendini-test  # AGSIZ, iki yonlu fikstur
"""

import argparse
import importlib.util
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

DEPO = os.environ.get("GITHUB_REPOSITORY") or "Pruvo138/pruvo"
# Sapma kanalinin OLCTUGU yayin is akisi (kadans kolu bunun ICINDE kosar).
YAYIN_AKISI = "deploy.yml"

RC_TEMIZ, RC_SAPMA, RC_OLCULEMEDI = 0, 1, 2


class OlcumHatasi(Exception):
    """Olculemedi (rc 2). 'Sapma yok' ile ASLA karistirilmaz."""


def _modul(ad):
    """tools/<ad>.py'yi MODUL olarak yukle (tire iceren ad -> importlib). Fail-closed."""
    yol = os.path.join(TOOLS, "%s.py" % ad)
    if not os.path.exists(yol):
        raise OlcumHatasi("tools/%s.py YOK -> damga adi TEK KAYNAKTAN alinamadi" % ad)
    spec = importlib.util.spec_from_file_location("pruvo_%s" % ad.replace("-", "_"), yol)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:  # noqa: BLE001
        raise OlcumHatasi("tools/%s.py yuklenemedi (%s: %s)" % (ad, type(e).__name__, e))
    return mod


def damga_adi():
    """TEK KAYNAK: cron-nabiz-kapisi.py::DAMGA_KUTUGU icindeki sapma damgasinin adi.

    Kutukte YOKSA fail-closed: adi burada UYDURMAK, hicbir yazicinin uretmedigi bir
    artifact'i beklemek (yani DAIMA yesil bir alarm) demek olurdu."""
    mod = _modul("cron-nabiz-kapisi")
    kutuk = getattr(mod, "DAMGA_KUTUGU", None)
    ad = getattr(mod, "SAPMA_DAMGA_ADI", None)
    if not isinstance(kutuk, dict) or not ad:
        raise OlcumHatasi("cron-nabiz-kapisi.py'de SAPMA_DAMGA_ADI/DAMGA_KUTUGU YOK -> "
                          "damga adi TEK KAYNAKTAN turetilemedi")
    if ad not in kutuk:
        raise OlcumHatasi("SAPMA_DAMGA_ADI (%r) DAMGA_KUTUGU'nde KAYITLI DEGIL -> "
                          "yazici tarafi bu adi uretemez (`--damga-yaz` reddeder)" % ad)
    return ad


def _api():
    """cron-nabiz-kapisi.py'nin GERCEK GitHub istemcisi (ikinci istemci TUTULMAZ)."""
    mod = _modul("cron-nabiz-kapisi")
    getir = getattr(mod, "api_getir", None)
    if getir is None:
        raise OlcumHatasi("cron-nabiz-kapisi.py::api_getir YOK -> API kolu capasiz")
    return getir


def tetik_kosum(getir, ortam=None):
    """Olculecek YAYIN kosumunun kimligi -> (kosum_id, kaynak).

    `workflow_run` olayinda GitHub tetikleyen kosumun kimligini verir; is akisi onu
    TETIK_KOSUM olarak gecer. ELLE (`workflow_dispatch`) kosumda bu bos gelir ve o
    zaman EN SON TAMAMLANMIS deploy.yml kosumu olculur — "olculecek bir sey yok" diye
    YESIL DONMEK bu nobetciyi elle kosturuldugunda anlamsiz kilardi."""
    ort = os.environ if ortam is None else ortam
    ham = str(ort.get("TETIK_KOSUM") or "").strip()
    if ham:
        if not ham.isdigit():
            raise OlcumHatasi("TETIK_KOSUM sayisal degil: %r" % ham)
        return int(ham), "workflow_run"
    d = getir("repos/%s/actions/workflows/%s/runs?status=completed&per_page=1"
              % (DEPO, YAYIN_AKISI))
    if not isinstance(d, dict) or not isinstance(d.get("workflow_runs"), list):
        raise OlcumHatasi("kosum listesi yaniti beklenen sekilde degil "
                          "(`workflow_runs` dizisi yok)")
    kosumlar = d["workflow_runs"]
    if not kosumlar:
        raise OlcumHatasi("%s icin TAMAMLANMIS hicbir kosum yok -> olculecek yayin "
                          "kosumu bulunamadi" % YAYIN_AKISI)
    kimlik = kosumlar[0].get("id")
    if not isinstance(kimlik, int):
        raise OlcumHatasi("kosum kaydinda sayisal `id` YOK: %r" % (kosumlar[0],))
    return kimlik, "son-tamamlanan"


def sapma_gozle(getir, kosum_id, ad):
    """Verilen KOSUMUN artifact'lerinde sapma damgasi var mi -> gozlem sozlugu.

    🔴 KOSUM BAZLI (depo bazli DEGIL): depo genelinde "en yeni damga kac saatlik"
    sormak, bu eksende YANLIS BIRIMDIR — sapma DAMGASI bir YAS olcusu degil, BELIRLI
    bir yayin kosumunun IKILI hukmudur. Yas esigi konsaydi, iki sapma arasindaki
    sessiz saatlerde alarm kendiliginden sonerdi.
    HER sekil arizasi OlcumHatasi (rc 2): 'damga yok' ile 'okuyamadim' AYRI hallerdir."""
    d = getir("repos/%s/actions/runs/%s/artifacts?per_page=100" % (DEPO, kosum_id))
    if not isinstance(d, dict) or not isinstance(d.get("artifacts"), list):
        raise OlcumHatasi("artifact yaniti beklenen sekilde degil (`artifacts` dizisi "
                          "yok) -> sapma ekseni OKUNAMADI, 'yesil' SAYILMAZ")
    adlar = []
    for a in d["artifacts"]:
        if not isinstance(a, dict) or "name" not in a:
            raise OlcumHatasi("artifact kaydinda `name` YOK: %r" % (a,))
        adlar.append(str(a["name"]))
    return {"kosum": kosum_id, "sapma": ad in adlar, "adlar": sorted(adlar)}


def hukum(gozlem, kaynak):
    """(rc, satirlar) — gozlemden HUKUM. Uc hal, ucu de ADIYLA basilir."""
    kosum = gozlem["kosum"]
    baglanti = "https://github.com/%s/actions/runs/%s" % (DEPO, kosum)
    if gozlem["sapma"]:
        return RC_SAPMA, [
            "🔴 D1 SAPMASI OLDU — yayin kosumu %s icinde `d1-sapma-damgasi` VAR." % kosum,
            "Uzlastirici sapmayi ONARDI ve TEYIT etti; bu alarm onarimi degil SAPMANIN",
            "OLUSMASINI bildirir: sapma bir UST-YOL kacagidir (pre-push kancasi / CI D1",
            "adimi / elle push) ve onarildi diye o kacak yok olmaz.",
            "Sapma sayilari o kosumun `d1-kadans` isinin ozetinde: %s" % baglanti,
            "Bu kosum KIRMIZI; YAYIN kosumu ETKILENMEDI (iki sinyal AYRI kanalda).",
        ]
    return RC_TEMIZ, [
        "🟢 TEMIZ — yayin kosumu %s icinde sapma damgasi YOK." % kosum,
        "Kosum kimligi kaynagi: %s · o kosumdaki artifact'ler: %s"
        % (kaynak, ", ".join(gozlem["adlar"]) or "(hic yok)"),
    ]


def _ozet_yaz(satirlar, rc, ortam=None):
    ort = os.environ if ortam is None else ortam
    yol = ort.get("GITHUB_STEP_SUMMARY")
    if not yol:
        return
    baslik = {RC_TEMIZ: "### 🟢 D1 sapma alarmi: TEMIZ",
              RC_SAPMA: "### 🔴 D1 sapma alarmi: SAPMA OLUSTU",
              RC_OLCULEMEDI: "### 🔴 D1 sapma alarmi: OLCULEMEDI"}[rc]
    with open(yol, "a", encoding="utf-8") as f:
        f.write(baslik + "\n\n")
        for s in satirlar:
            f.write("%s\n" % s)
        f.write("\n")


# ═══════════════════════════════════════════════════════════════════════════════
# KENDINI TEST — AGSIZ, IKI YONLU
# ═══════════════════════════════════════════════════════════════════════════════
# 🔴 NEDEN SART: bu nobetcinin canli kolu GUNLERCE 'temiz' donebilir (sapma nadirdir).
# "Alarm sapmayi gorur" iddiasi canli kosumla KANITLANAMAZ — ancak fiksturle. Fikstur
# GERCEK API govdesinin ayni SEKLINI besler ([[nobetci-fikstur-sekli]]).
def _sahte_api(artifact_adlari, kosum_listesi=None, bozuk=None):
    def getir(yol, zaman_asimi=25):   # noqa: ARG001
        if bozuk == "artifact-sekil" and "/artifacts" in yol:
            return {"beklenmeyen": True}
        if bozuk == "artifact-adsiz" and "/artifacts" in yol:
            return {"artifacts": [{"id": 1}]}
        if bozuk == "kosum-sekil" and "/runs?" in yol:
            return {"beklenmeyen": True}
        if "/artifacts" in yol:
            return {"artifacts": [{"name": a, "id": i}
                                  for i, a in enumerate(artifact_adlari)]}
        if "/runs?" in yol:
            return {"workflow_runs": list(kosum_listesi or [])}
        raise AssertionError("fiksturde tanimsiz API yolu: %s" % yol)
    return getir


def kendini_test():
    sonuc = {"gecti": 0, "kaldi": 0}

    def iddia(ad, kosul, detay=""):
        if kosul:
            sonuc["gecti"] += 1
            print("  [PASS] %s" % ad)
        else:
            sonuc["kaldi"] += 1
            print("  [FAIL] %s  -> %s" % (ad, detay))

    print("D1 SAPMA ALARMI — KENDINI TEST (agsiz)")
    print("-" * 70)

    # --- TEK KAYNAK: damga adi kutukten gelir ve YAZICI onu uretebilir ---
    try:
        ad = damga_adi()
        ad_hata = None
    except Exception as e:  # noqa: BLE001
        ad, ad_hata = None, "%s: %s" % (type(e).__name__, e)
    iddia("TEK KAYNAK: sapma damgasinin adi cron-nabiz-kapisi.py::DAMGA_KUTUGU'nden "
          "gelir (ikinci kopya YOK -> sessiz ayrisma imkansiz)", bool(ad), ad_hata)
    if ad:
        nabiz = _modul("cron-nabiz-kapisi")
        govde = nabiz.damga_govdesi(ortam={}, ad=ad)
        iddia("TEK KAYNAK: yazici (`--damga-yaz --damga-adi %s`) bu adi FIILEN uretebilir "
              "ve govde kendi is akisini/iddiasini tasir" % ad,
              govde.get("damga") == ad and govde.get("is_akisi") == "d1-uzlastirici.yml"
              and bool(govde.get("iddia")), repr(govde))

    ad = ad or "d1-sapma-damgasi"

    # --- IKI YONLU HUKUM ---
    g = sapma_gozle(_sahte_api([ad, "uzlastirma-damgasi"]), 111, ad)
    rc, satirlar = hukum(g, "workflow_run")
    iddia("SAPMA VAR -> rc 1 (KIRMIZI). Damga varken yesil donmek, ayrimin en kolay ve "
          "en yanlis cozumu olan SESSIZLESTIRME olurdu", rc == RC_SAPMA,
          "rc=%d %r" % (rc, satirlar[:1]))

    g = sapma_gozle(_sahte_api(["uzlastirma-damgasi"]), 112, ad)
    rc, _ = hukum(g, "workflow_run")
    iddia("SAPMA YOK -> rc 0 (yanlis-pozitif yok; baska damgalar alarmi tetiklemez)",
          rc == RC_TEMIZ, "rc=%d" % rc)

    g = sapma_gozle(_sahte_api([]), 113, ad)
    rc, _ = hukum(g, "workflow_run")
    iddia("HIC ARTIFACT YOK -> rc 0 (uzlastirma o kosumda sapma BULMADI)",
          rc == RC_TEMIZ, "rc=%d" % rc)

    # --- FAIL-CLOSED: OLCULEMEDI ile 'sapma yok' AYRI HALLERDIR ---
    for etiket, bozuk in (("artifact yaniti sekli bozuk", "artifact-sekil"),
                          ("artifact kaydinda `name` yok", "artifact-adsiz")):
        try:
            sapma_gozle(_sahte_api([], bozuk=bozuk), 114, ad)
            dustu = False
        except OlcumHatasi:
            dustu = True
        iddia("FAIL-CLOSED: %s -> OLCULEMEDI (rc 2), 'sapma yok' SAYILMAZ" % etiket,
              dustu)

    # --- KOSUM KIMLIGI COZUMU ---
    kimlik, kaynak = tetik_kosum(_sahte_api([]), ortam={"TETIK_KOSUM": "987"})
    iddia("KOSUM KIMLIGI: TETIK_KOSUM verilmisse O kosum olculur (workflow_run kolu)",
          (kimlik, kaynak) == (987, "workflow_run"), repr((kimlik, kaynak)))

    kimlik, kaynak = tetik_kosum(_sahte_api([], kosum_listesi=[{"id": 555}]), ortam={})
    iddia("KOSUM KIMLIGI: TETIK_KOSUM yoksa (elle kosum) EN SON TAMAMLANMIS %s kosumu "
          "olculur — 'olculecek sey yok' diye YESIL DONULMEZ" % YAYIN_AKISI,
          (kimlik, kaynak) == (555, "son-tamamlanan"), repr((kimlik, kaynak)))

    for etiket, ort, fikstur in (
            ("TETIK_KOSUM sayisal degil", {"TETIK_KOSUM": "abc"}, _sahte_api([])),
            ("kosum listesi sekli bozuk", {}, _sahte_api([], bozuk="kosum-sekil")),
            ("hic tamamlanmis kosum yok", {}, _sahte_api([], kosum_listesi=[]))):
        try:
            tetik_kosum(fikstur, ortam=ort)
            dustu = False
        except OlcumHatasi:
            dustu = True
        iddia("FAIL-CLOSED: %s -> OLCULEMEDI (rc 2)" % etiket, dustu)

    # --- HUKUM METNI: uc hal AYRI AYRI adlandirilir ---
    g = sapma_gozle(_sahte_api([ad]), 116, ad)
    _rc, satirlar = hukum(g, "workflow_run")
    metin = " ".join(satirlar)
    iddia("HUKUM METNI: sapma halinde 'YAYIN kosumu ETKILENMEDI' AYRIMI ACIKCA yazilir "
          "(okuyucu iki sinyali karistirmasin)",
          "ETKILENMEDI" in metin and "AYRI kanalda" in metin, metin)

    print("-" * 70)
    print("%d iddia kosturuldu, %d KIRMIZI." % (sonuc["gecti"] + sonuc["kaldi"],
                                                sonuc["kaldi"]))
    if sonuc["kaldi"]:
        print("❌ KENDINI TEST DUSTU")
        return 1
    print("✅ KENDINI TEST GECTI")
    return 0


def main():
    ap = argparse.ArgumentParser(description="D1 sapma alarmi (kadans kolunun kanali)")
    ap.add_argument("--kendini-test", action="store_true",
                    help="agsiz iki yonlu fikstur kabulu")
    ap.add_argument("--gh-ozet", action="store_true",
                    help="hukmu GITHUB_STEP_SUMMARY'ye de yaz")
    a = ap.parse_args()

    if a.kendini_test:
        return kendini_test()

    try:
        ad = damga_adi()
        getir = _api()
        kosum, kaynak = tetik_kosum(getir)
        gozlem = sapma_gozle(getir, kosum, ad)
    except OlcumHatasi as e:
        satirlar = ["🔴 OLCULEMEDI: %s" % e,
                    "Bu SESSIZ YESIL DEGILDIR: sapma kanali okunamadigi surece 'sapma "
                    "yok' hukmu VERILEMEZ."]
        print("\n".join(satirlar))
        if a.gh_ozet:
            _ozet_yaz(satirlar, RC_OLCULEMEDI)
        return RC_OLCULEMEDI

    rc, satirlar = hukum(gozlem, kaynak)
    print("\n".join(satirlar))
    print(json.dumps(gozlem, ensure_ascii=False, sort_keys=True))
    if a.gh_ozet:
        _ozet_yaz(satirlar, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())

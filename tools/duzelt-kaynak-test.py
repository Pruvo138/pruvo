#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/duzelt-kaynak-test.py — K171 kapsam: --kaynak-durum / --kaynak-temizle.

GERCEK .urun-kaynaklari.json'a DOKUNULMAZ: sahte repo (<tmp>/urunler.json +
<tmp>/.urun-kaynaklari.json) kurulur. duzelt.py yollari kendi __file__ konumundan
turettigi icin kopya sahte katalog uzerinde calisir.

Kabul eksenleri:
  K1  --kaynak-durum: dosya TAM ise `KAYNAK_KAYIT=N URUN=N ARTIK=N ARTIK_ORNEK=ids`
                     (sadece id, govde YOK), rc=0.
  K2  --kaynak-durum: dosya YOK ise OLCULEMEDI + rc != 0.
  K3  --kaynak-temizle yalniz kullanilirsa hata (rc=2).
  K4  --kaynak-temizle + --sil: ayni flock icinde KAYNAKLAR da dusurulur.
  K5  --kaynak-temizle + --sil: idempotent (ZATEN_YOK raporlanir, hata degil).
  K6  --kaynak-temizle + --toplu: batch'teki urun_silmeler KAYNAKLAR'dan dusurulur.
  K7  --kaynak-temizle: temizlik ONCESI/SONRASI iki olcum KAYNAK_KAYIT ve KALAN
      uzerinden tutarli (gercek yazim, "yazma kaldirildi" mutantini yakalar).
  K8  --kaynak-temizle: dosyaya KAYIT GOVDESI BASILMAZ (sadece id + sayi).
      Bu eksen asagidaki kisisel-veri-test'i davet eder; burada 'uyelik'/'link'
      gecmedigini GORUNEN cikti uzerinden teyit ederiz.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
DUZELT = os.path.join(TOOLS, "duzelt.py")
# duzelt.py'nin kardes kapanisi (gorsel_koken/arama/veri_kok ...) ELLE LISTELENMEZ —
# kopyalanan kaynagin import'larindan TURETILIR (veri_kok.kum_kur). Elle liste 18 Eyl'de
# veri_kok.py'yi kacirip yayini durdurdu ([[elle-tutulan-bagimlilik-listesi-sessizce-bayatlar]]).
_vk_spec = importlib.util.spec_from_file_location("veri_kok", os.path.join(TOOLS, "veri_kok.py"))
veri_kok = importlib.util.module_from_spec(_vk_spec)
_vk_spec.loader.exec_module(veri_kok)

FAILS = []
# Vaka etiketi: mutasyon bataryasi her mutantin TAM OLARAK hangi vaka kumesini kirmizi
# yaktigini son satirdaki `KIRMIZI_VAKA=` uzerinden olcer (etiketsiz eski eksen = "k").
VAKA = ["k"]
KIRMIZI_VAKA = set()


def kontrol(kosul, mesaj, detay=""):
    print(("  ✔ " if kosul else "  ✘ ") + mesaj + (("   [%s]" % detay) if detay else ""))
    if not kosul:
        FAILS.append(mesaj + (("   [%s]" % detay) if detay else ""))
        KIRMIZI_VAKA.add(VAKA[0])


def cagir(repo, *argv):
    """Gerçek duzelt.py'yi sahte repoda çalıştır; (rc, stdout, stderr) döndür."""
    yeni = {
        "PYTHONPATH": os.path.join(repo, "tools"),
        # 13 Eyl 2026: duzelt silmesi ACIK izin ister (duzelt.py::SIL_IZIN_ENV). Bu batarya
        # KAYNAK TEMIZLEME mekanigini olcer -> izinle kosar; izinsiz RED'i
        # tools/urun-silme-kapisi-test.py (V13/V14 + M1/M2) olcer.
        "PRUVO_URUN_SIL_IZNI": "OKAN",
        # VERI KOKU = sahte repo — git/__file__ sansina birakilmaz.
        veri_kok.ENV_AD: os.path.abspath(repo),
    }
    env = os.environ.copy()
    env.update(yeni)
    r = subprocess.run(
        [sys.executable, os.path.join(repo, "tools", "duzelt.py")] + list(argv),
        capture_output=True, text=True, env=env,
    )
    return r.returncode, r.stdout, r.stderr


def sahte_repo(kaynaklar=None, urunler=None):
    """Sahte repo: <tmp>/urunler.json + <tmp>/.urun-kaynaklari.json + tools/duzelt.py."""
    d = tempfile.mkdtemp(prefix="duzelt-kaynak-testi-")
    veri_kok.kum_kur(os.path.join(d, "tools"), {"duzelt.py": None}, TOOLS)
    with open(os.path.join(d, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump(
            urunler if urunler is not None
            else [{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                   "aciklama": "a", "fiyat": "100 TL",
                   "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
            f, ensure_ascii=False, indent=2)
    if kaynaklar is not None:
        with open(os.path.join(d, ".urun-kaynaklari.json"), "w", encoding="utf-8") as f:
            json.dump(kaynaklar, f, ensure_ascii=False, indent=2)
    return d


def temizle(*dizinler):
    for d in dizinler:
        shutil.rmtree(d, ignore_errors=True)


def _oku(repo, ad):
    with open(os.path.join(repo, ad), "rb") as f:
        return f.read()


def _kaynak(repo):
    with open(os.path.join(repo, ".urun-kaynaklari.json"), encoding="utf-8") as f:
        return json.load(f)


def _urun(uid):
    return {"id": uid, "kategori": "Otomobil", "marka": ["X"], "baslik": uid,
            "aciklama": "a", "fiyat": "100 TL",
            "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}


def damga_vakalari():
    """`--kaynak-damga ID.. --silindi METIN` + damgali kaydin temizlik/ARTIK korumasi.
    Her vaka KENDI etiketiyle kirmizi yanar (mutasyon bataryasi kumeyi birebir olcer)."""
    tpl = {"a-1": {"link": "https://a1", "uyelik": "u-a1", "lisans": "CC BY"},
           "a-2": {"link": "https://a2", "tasarimci": "t2"},
           "a-3": {"link": "https://a3"}}

    # ── [yaz] ────────────────────────────────────────────────────────────────
    VAKA[0] = "yaz"
    print("\n[yaz] — var olan kayitlara damga yazilir, rc=0")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        urun_once = _oku(repo, "urunler.json")
        rc, out, err = cagir(repo, "--kaynak-damga", "a-1", "a-2", "--silindi", "Okan sil 6 Eki")
        kontrol(rc == 0, "rc=0", "rc=%d err=%r" % (rc, err[-200:]))
        kontrol(out.strip() == "KAYNAK_DAMGA yazildi=2 zaten=0 yok=0 cakisma=0",
                "cikti tek satir yazildi=2", "out=%r" % out)
        k = _kaynak(repo)
        kontrol(k["a-1"].get("silindi") == "Okan sil 6 Eki"
                and k["a-2"].get("silindi") == "Okan sil 6 Eki", "a-1/a-2 damgali")
        kontrol("silindi" not in k["a-3"], "a-3 damgasiz kaldi")
        kontrol(_oku(repo, "urunler.json") == urun_once, "urunler.json bayt-esit")
    finally:
        temizle(repo)

    # ── [alanlar] ───────────────────────────────────────────────────────────
    VAKA[0] = "alanlar"
    print("\n[alanlar] — damga disindaki tum alanlar/kayitlar bayt-esit")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        rc, out, _ = cagir(repo, "--kaynak-damga", "a-1", "--silindi", "x")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        k = _kaynak(repo)
        a1 = dict(k["a-1"])
        a1.pop("silindi", None)
        kontrol(json.dumps(a1) == json.dumps(tpl["a-1"]), "a-1 diger alanlari + sira esit",
                "a1=%s" % sorted(a1))
        kontrol(list(k["a-1"].keys())[-1] == "silindi", "silindi SONA eklendi")
        kontrol(json.dumps(k["a-2"]) == json.dumps(tpl["a-2"])
                and json.dumps(k["a-3"]) == json.dumps(tpl["a-3"]), "komsu kayitlar esit")
        kontrol(list(k.keys()) == list(tpl.keys()), "kayit sirasi/kumesi esit")
    finally:
        temizle(repo)

    # ── [zaten] ─────────────────────────────────────────────────────────────
    VAKA[0] = "zaten"
    print("\n[zaten] — ayni metin: dosya YENIDEN YAZILMAZ, zaten=1")
    kay = json.loads(json.dumps(tpl))
    kay["a-1"]["silindi"] = "x"
    repo = sahte_repo(kaynaklar=kay, urunler=[_urun("u-var")])
    try:
        yol = os.path.join(repo, ".urun-kaynaklari.json")
        st = os.stat(yol)
        bayt = _oku(repo, ".urun-kaynaklari.json")
        rc, out, _ = cagir(repo, "--kaynak-damga", "a-1", "--silindi", "x")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol(out.strip() == "KAYNAK_DAMGA yazildi=0 zaten=1 yok=0 cakisma=0",
                "zaten=1", "out=%r" % out)
        st2 = os.stat(yol)
        kontrol(st2.st_ino == st.st_ino and _oku(repo, ".urun-kaynaklari.json") == bayt,
                "dosya yeniden yazilmadi (inode + bayt esit)")
    finally:
        temizle(repo)

    # ── [yok] ───────────────────────────────────────────────────────────────
    VAKA[0] = "yok"
    print("\n[yok] — defterde olmayan id: kayit YARATILMAZ, rc=3")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        rc, out, _ = cagir(repo, "--kaynak-damga", "a-1", "z-yok", "--silindi", "x")
        kontrol(rc == 3, "rc=3", "rc=%d" % rc)
        kontrol(out.strip() == "KAYNAK_DAMGA yazildi=1 zaten=0 yok=1 cakisma=0",
                "yazildi=1 yok=1", "out=%r" % out)
        k = _kaynak(repo)
        kontrol("z-yok" not in k, "z-yok kaydi YARATILMADI")
        kontrol(len(k) == 3 and k["a-1"].get("silindi") == "x", "a-1 yine damgalandi")
    finally:
        temizle(repo)

    # ── [cakisma] ───────────────────────────────────────────────────────────
    VAKA[0] = "cakisma"
    print("\n[cakisma] — farkli metin: eski damga KORUNUR, rc=4")
    kay = json.loads(json.dumps(tpl))
    kay["a-1"]["silindi"] = "eski metin"
    repo = sahte_repo(kaynaklar=kay, urunler=[_urun("u-var")])
    try:
        rc, out, _ = cagir(repo, "--kaynak-damga", "a-1", "--silindi", "yeni metin")
        kontrol(rc == 4, "rc=4", "rc=%d" % rc)
        kontrol("cakisma=1" in out and "yazildi=0" in out, "cakisma=1 yazildi=0",
                "out=%r" % out)
        kontrol(_kaynak(repo)["a-1"].get("silindi") == "eski metin", "eski metin korundu")
    finally:
        temizle(repo)

    # ── [temizlik] ──────────────────────────────────────────────────────────
    VAKA[0] = "temizlik"
    print("\n[temizlik] — --sil --kaynak-temizle damgali kaydi SILMEZ")
    kay = {"u-dam": {"link": "https://d", "silindi": "Okan sil"},
           "u-duz": {"link": "https://e"}}
    repo = sahte_repo(kaynaklar=kay, urunler=[_urun("u-dam"), _urun("u-duz")])
    try:
        islem = os.path.join(repo, "islem.json")
        with open(islem, "w", encoding="utf-8") as f:
            json.dump([{"id": "u-dam", "sil": "test"}, {"id": "u-duz", "sil": "test"}], f)
        rc, out, err = cagir(repo, "--toplu", islem, "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d err=%r" % (rc, err[-200:]))
        k = _kaynak(repo)
        kontrol("u-dam" in k and k["u-dam"] == kay["u-dam"], "damgali u-dam KORUNDU")
        kontrol("u-duz" not in k, "damgasiz u-duz silindi")
        kontrol("KAYNAK_SILINEN=1" in out and "KAYNAK_DAMGALI_KORUNAN=1" in out,
                "SILINEN=1 KORUNAN=1", "out=%r" % out)
    finally:
        temizle(repo)

    # ── [artik] ─────────────────────────────────────────────────────────────
    VAKA[0] = "artik"
    print("\n[artik] — --kaynak-durum damgaliyi ARTIK saymaz, DAMGALI sonda")
    kay = {"u-var": {"link": "https://v"}, "u-art": {"link": "https://a"},
           "u-dam": {"link": "https://d", "silindi": "Okan sil"}}
    repo = sahte_repo(kaynaklar=kay, urunler=[_urun("u-var")])
    try:
        rc, out, _ = cagir(repo, "--kaynak-durum")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol(out.strip() == "KAYNAK_KAYIT=3 URUN=1 ARTIK=1 ARTIK_ORNEK=u-art DAMGALI=1",
                "satir birebir (DAMGALI sonda)", "out=%r" % out)
    finally:
        temizle(repo)

    # ── [bos] ───────────────────────────────────────────────────────────────
    VAKA[0] = "bos"
    print("\n[bos] — bos/whitespace metin + karisik arguman: rc=2, yazim yok")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        bayt = _oku(repo, ".urun-kaynaklari.json")
        for argv, ad in ((["--kaynak-damga", "a-1", "--silindi", "   "], "whitespace"),
                         (["--kaynak-damga", "a-1", "--silindi", ""], "bos"),
                         (["--kaynak-damga", "a-1"], "silindi-yok"),
                         (["--silindi", "x"], "damga-yok"),
                         (["--kaynak-damga", "a-1", "--silindi", "x", "--kaynak-durum"],
                          "karisik-durum"),
                         (["u-var", "--sil", "t", "--kaynak-damga", "a-1", "--silindi", "x"],
                          "karisik-sil")):
            rc, _, _ = cagir(repo, *argv)
            kontrol(rc == 2, "%s rc=2" % ad, "rc=%d" % rc)
        kontrol(_oku(repo, ".urun-kaynaklari.json") == bayt, "defter bayt-esit")
    finally:
        temizle(repo)
    VAKA[0] = "k"


def tasarimci_vakalari():
    """`--kaynak-tasarimci ID DEGER`: yalniz YER TUTUCU `tasarimci` doldurulur.
    Her vaka KENDI `t-*` etiketiyle kirmizi yanar (mutasyon bataryasi kumeyi birebir olcer).
    Gercek ad iceren tek kayit `t-cakisma` vakasindadir; ciktinin birebir bicimi yalniz
    `t-gizlilik`te olculur (digerleri `sonuc=` alt dizesine bakar)."""
    ad = "Gizli Tasarimci Z9"
    tpl = {"p-1": {"link": "https://p1", "uyelik": "u-p1", "tasarimci": "?", "lisans": "CC0"},
           "p-2": {"link": "https://p2"},
           "p-3": {"link": "https://p3", "tasarimci": "  "}}

    # ── [t-yaz] ─────────────────────────────────────────────────────────────
    VAKA[0] = "t-yaz"
    print("\n[t-yaz] — yer tutucu ('?', alan yok, bosluk) -> ad yazilir, rc=0")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        for uid in ("p-1", "p-2", "p-3"):
            rc, out, err = cagir(repo, "--kaynak-tasarimci", uid, ad)
            kontrol(rc == 0, "%s rc=0" % uid, "rc=%d err=%r" % (rc, err[-200:]))
            kontrol("KAYNAK_TASARIMCI sonuc=yazildi" in out, "%s sonuc=yazildi" % uid,
                    "out=%r" % out)
            kontrol(_kaynak(repo)[uid].get("tasarimci") == ad, "%s tasarimci yazildi" % uid)
    finally:
        temizle(repo)

    # ── [t-alanlar] ─────────────────────────────────────────────────────────
    VAKA[0] = "t-alanlar"
    print("\n[t-alanlar] — tasarimci disindaki alanlar/kayitlar bayt-esit")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        rc, _, _ = cagir(repo, "--kaynak-tasarimci", "p-1", ad)
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        k = _kaynak(repo)
        bek = dict(tpl["p-1"])
        bek["tasarimci"] = ad
        kontrol(json.dumps(k["p-1"]) == json.dumps(bek),
                "p-1 yalniz tasarimci degisti, alan sirasi esit", "p1=%s" % sorted(k["p-1"]))
        kontrol(json.dumps(k["p-2"]) == json.dumps(tpl["p-2"])
                and json.dumps(k["p-3"]) == json.dumps(tpl["p-3"]), "komsu kayitlar esit")
        kontrol(list(k.keys()) == list(tpl.keys()), "kayit sirasi/kumesi esit")
    finally:
        temizle(repo)

    # ── [t-urunler] ─────────────────────────────────────────────────────────
    VAKA[0] = "t-urunler"
    print("\n[t-urunler] — urunler.json bayt-esit (yazildi yolunda bile)")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        urun_once = _oku(repo, "urunler.json")
        rc, _, _ = cagir(repo, "--kaynak-tasarimci", "p-1", ad)
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol(_oku(repo, "urunler.json") == urun_once, "urunler.json bayt-esit")
    finally:
        temizle(repo)

    # ── [t-zaten] ───────────────────────────────────────────────────────────
    VAKA[0] = "t-zaten"
    print("\n[t-zaten] — ayni ad: dosya YENIDEN YAZILMAZ, rc=0")
    kay = json.loads(json.dumps(tpl))
    kay["p-1"]["tasarimci"] = ad
    repo = sahte_repo(kaynaklar=kay, urunler=[_urun("u-var")])
    try:
        yol = os.path.join(repo, ".urun-kaynaklari.json")
        st = os.stat(yol)
        bayt = _oku(repo, ".urun-kaynaklari.json")
        rc, out, _ = cagir(repo, "--kaynak-tasarimci", "p-1", ad)
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_TASARIMCI sonuc=zaten" in out, "sonuc=zaten", "out=%r" % out)
        kontrol(os.stat(yol).st_ino == st.st_ino and _oku(repo, ".urun-kaynaklari.json") == bayt,
                "dosya yeniden yazilmadi (inode + bayt esit)")
    finally:
        temizle(repo)

    # ── [t-yok] ─────────────────────────────────────────────────────────────
    VAKA[0] = "t-yok"
    print("\n[t-yok] — defterde olmayan id: kayit YARATILMAZ, rc=3")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        bayt = _oku(repo, ".urun-kaynaklari.json")
        rc, out, _ = cagir(repo, "--kaynak-tasarimci", "z-yok", ad)
        kontrol(rc == 3, "rc=3", "rc=%d" % rc)
        kontrol("KAYNAK_TASARIMCI sonuc=yok" in out, "sonuc=yok", "out=%r" % out)
        kontrol("z-yok" not in _kaynak(repo), "z-yok kaydi YARATILMADI")
        kontrol(_oku(repo, ".urun-kaynaklari.json") == bayt, "defter bayt-esit")
    finally:
        temizle(repo)

    # ── [t-cakisma] ─────────────────────────────────────────────────────────
    VAKA[0] = "t-cakisma"
    print("\n[t-cakisma] — baska gercek ad: UZERINE YAZILMAZ, rc=4")
    kay = json.loads(json.dumps(tpl))
    kay["p-1"]["tasarimci"] = "Eski Gercek Ad"
    repo = sahte_repo(kaynaklar=kay, urunler=[_urun("u-var")])
    try:
        bayt = _oku(repo, ".urun-kaynaklari.json")
        rc, out, _ = cagir(repo, "--kaynak-tasarimci", "p-1", ad)
        kontrol(rc == 4, "rc=4", "rc=%d" % rc)
        kontrol("KAYNAK_TASARIMCI sonuc=cakisma" in out, "sonuc=cakisma", "out=%r" % out)
        kontrol(_kaynak(repo)["p-1"].get("tasarimci") == "Eski Gercek Ad", "eski ad duruyor")
        kontrol(_oku(repo, ".urun-kaynaklari.json") == bayt, "defter bayt-esit")
    finally:
        temizle(repo)

    # ── [t-gizlilik] ────────────────────────────────────────────────────────
    VAKA[0] = "t-gizlilik"
    print("\n[t-gizlilik] — stdout tek satir; DEGER/link/uyelik stdout/stderr/log'da YOK")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        for uid, bek in (("p-1", "yazildi"), ("p-1", "zaten"), ("z-yok", "yok")):
            rc, out, err = cagir(repo, "--kaynak-tasarimci", uid, ad)
            kontrol(out.strip() == "KAYNAK_TASARIMCI sonuc=%s" % bek,
                    "%s/%s stdout birebir tek satir" % (uid, bek), "rc=%d" % rc)
            kontrol(ad not in out and ad not in err, "%s/%s ciktida DEGER yok" % (uid, bek))
            kontrol("https://p1" not in out + err and "u-p1" not in out + err,
                    "%s/%s ciktida link/uyelik yok" % (uid, bek))
        log = os.path.join(repo, ".urunler-guard.log")
        metin = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
        kontrol("kaynak-tasarimci: sonuc=yazildi" in metin, "log satiri yazildi")
        kontrol(ad not in metin, "log'da DEGER yok")
    finally:
        temizle(repo)

    # ── [t-karisik] ─────────────────────────────────────────────────────────
    VAKA[0] = "t-karisik"
    print("\n[t-karisik] — bos ID/DEGER + karisik arguman: rc=2, yazim yok")
    repo = sahte_repo(kaynaklar=json.loads(json.dumps(tpl)), urunler=[_urun("u-var")])
    try:
        bayt = _oku(repo, ".urun-kaynaklari.json")
        urun_once = _oku(repo, "urunler.json")
        for argv, etiket in ((["--kaynak-tasarimci", "", ad], "bos-id"),
                             (["--kaynak-tasarimci", "  ", ad], "bosluk-id"),
                             (["--kaynak-tasarimci", "p-1", ""], "bos-deger"),
                             (["--kaynak-tasarimci", "p-1", "   "], "bosluk-deger"),
                             (["--kaynak-tasarimci", "p-1", "?"], "yer-tutucu-deger"),
                             (["--kaynak-tasarimci", "p-1", ad, "--kaynak-durum"],
                              "karisik-durum"),
                             (["--kaynak-tasarimci", "p-1", ad, "--kaynak-damga", "p-1",
                               "--silindi", "x"], "karisik-damga"),
                             (["u-var", "--alan", "baslik", "--deger", "y",
                               "--kaynak-tasarimci", "p-1", ad], "karisik-alan")):
            rc, _, _ = cagir(repo, *argv)
            kontrol(rc == 2, "%s rc=2" % etiket, "rc=%d" % rc)
        kontrol(_oku(repo, ".urun-kaynaklari.json") == bayt, "defter bayt-esit")
        kontrol(_oku(repo, "urunler.json") == urun_once, "urunler.json bayt-esit")
    finally:
        temizle(repo)
    VAKA[0] = "k"


def main():
    print("K171 — --kaynak-durum / --kaynak-temizle kabul testi (sahte repo)\n")

    # ── K1: --kaynak-durum, TAM dosya ────────────────────────────────────────
    print("K1 — --kaynak-durum (TAM dosya)")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://x", "uyelik": "u1"},
                   "u-yok": {"link": "https://y", "uyelik": "u2"},
                   "u-yok2": {"link": "https://z", "uyelik": "u3"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "--kaynak-durum")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_KAYIT=3" in out, "KAYNAK_KAYIT=3", "out=%r" % out.strip())
        kontrol("URUN=1" in out, "URUN=1", "out=%r" % out.strip())
        kontrol("ARTIK=2" in out, "ARTIK=2", "out=%r" % out.strip())
        kontrol("u-yok" in out and "u-yok2" in out, "ARTIK_ORNEK 2 id'yi icerir")
        # K8: kayit govdesi (link/uyelik) BASILMAMALI
        kontrol("https://x" not in out and "https://y" not in out and "https://z" not in out,
                "Ciktida LINK yok", "out=%r" % out)
        kontrol("\"uyelik\"" not in out and "u1" not in out and "u2" not in out and "u3" not in out,
                "Ciktida UYELIK degeri yok", "out=%r" % out)
    finally:
        temizle(repo)

    # ── K2: --kaynak-durum, dosya YOK ───────────────────────────────────────
    print("\nK2 — --kaynak-durum (dosya YOK)")
    repo = sahte_repo(kaynaklar=None)  # dosya yok
    try:
        rc, out, err = cagir(repo, "--kaynak-durum")
        kontrol(rc != 0, "rc != 0 (sessiz sifir YASAK)", "rc=%d" % rc)
        kontrol("OLCULEMEDI" in err, "stderr OLCULEMEDI icerir", "err=%r" % err.strip())
    finally:
        temizle(repo)

    # ── K3: --kaynak-temizle yalniz ──────────────────────────────────────────
    print("\nK3 — --kaynak-temizle yalniz (ARGUMAN HATASI)")
    repo = sahte_repo()
    try:
        rc, out, err = cagir(repo, "--kaynak-temizle")
        kontrol(rc == 2, "rc=2", "rc=%d" % rc)
        kontrol("kaynak-temizle" in err, "hata mesaji kaynak-temizle iceriyor")
    finally:
        temizle(repo)

    # ── K4: --kaynak-temizle + --sil (tek urun) ─────────────────────────────
    print("\nK4 — --kaynak-temizle + --sil (tek urun)")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://x"}, "u-diger": {"link": "https://w"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_SILINEN=1" in out, "KAYNAK_SILINEN=1", "out=%r" % out)
        kontrol("ZATEN_YOK=0" in out, "ZATEN_YOK=0")
        kontrol("KAYNAK_KALAN=1" in out, "KAYNAK_KALAN=1")
        # Dogrula: KAYNAKLAR dosyasi gercekten silinmis
        with open(os.path.join(repo, ".urun-kaynaklari.json"), encoding="utf-8") as f:
            kalan = json.load(f)
        kontrol("u-var" not in kalan and "u-diger" in kalan,
                "KAYNAKLAR: u-var dustu, u-diger duruyor", "kalan=%s" % sorted(kalan))
    finally:
        temizle(repo)

    # ── K5: --kaynak-temizle + --sil IDEMPOTENT (id yoksa) ──────────────────
    print("\nK5 — --kaynak-temizle + --sil (idempotent: id YOK)")
    repo = sahte_repo(
        kaynaklar={"u-diger": {"link": "https://w"}},  # u-var kaynakta yok
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_SILINEN=0" in out, "KAYNAK_SILINEN=0", "out=%r" % out)
        kontrol("ZATEN_YOK=1" in out, "ZATEN_YOK=1")
        kontrol("KAYNAK_KALAN=1" in out, "KAYNAK_KALAN=1")
    finally:
        temizle(repo)

    # ── K6: --kaynak-temizle + --toplu (batch) ──────────────────────────────
    print("\nK6 — --kaynak-temizle + --toplu (batch silme)")
    repo = sahte_repo(
        kaynaklar={"u-1": {"link": "https://1"}, "u-2": {"link": "https://2"},
                   "u-3": {"link": "https://3"}},
        urunler=[
            {"id": "u-1", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
             "aciklama": "a", "fiyat": "100 TL",
             "gorseller": ["https://media.pruvo3d.com/urunler/u-1-1.jpg"]},
            {"id": "u-2", "kategori": "Otomobil", "marka": ["X"], "baslik": "U2",
             "aciklama": "a", "fiyat": "100 TL",
             "gorseller": ["https://media.pruvo3d.com/urunler/u-2-2.jpg"]},
            {"id": "u-3", "kategori": "Otomobil", "marka": ["X"], "baslik": "U3",
             "aciklama": "a", "fiyat": "100 TL",
             "gorseller": ["https://media.pruvo3d.com/urunler/u-3-3.jpg"]},
        ],
    )
    try:
        islem = os.path.join(repo, "islem.json")
        with open(islem, "w", encoding="utf-8") as f:
            json.dump([
                {"id": "u-1", "sil": "test"},
                {"id": "u-2", "alan": "fiyat", "deger": "200 TL"},  # Duzeltme, silme degil
                {"id": "u-3", "sil": "test"},
            ], f, ensure_ascii=False)
        rc, out, err = cagir(repo, "--toplu", islem, "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("KAYNAK_SILINEN=2" in out, "KAYNAK_SILINEN=2 (silinen 2)", "out=%r" % out)
        kontrol("KAYNAK_KALAN=1" in out, "KAYNAK_KALAN=1 (u-2 kalici)", "out=%r" % out)
        with open(os.path.join(repo, ".urun-kaynaklari.json"), encoding="utf-8") as f:
            kalan = json.load(f)
        kontrol(list(kalan.keys()) == ["u-2"], "yalniz u-2 kaldi", "kalan=%s" % sorted(kalan))
    finally:
        temizle(repo)

    # ── K7: --kaynak-temizle IKI OLcum (oncesi/sonrasi) ─────────────────────
    print("\nK7 — --kaynak-turum: ONCESI / SONRASI olcum tutarliligi")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://x"}, "u-yok1": {"link": "1"},
                   "u-yok2": {"link": "2"}, "u-yok3": {"link": "3"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, _ = cagir(repo, "--kaynak-durum")
        kontrol(rc == 0 and "ARTIK=3" in out, "ONCESI ARTIK=3", "out=%r" % out)

        # u-var'i sil --kaynak-temizle ile
        rc, out, _ = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "temizlik rc=0")
        kontrol("KAYNAK_SILINEN=1" in out, "KAYNAK_SILINEN=1", "out=%r" % out)

        rc, out, _ = cagir(repo, "--kaynak-durum")
        kontrol(rc == 0 and "ARTIK=3" in out, "SONRASI ARTIK=3 (u-var zaten urunlerdeydi; "
                 "orphan'lar ayni kaldi)", "out=%r" % out)
    finally:
        temizle(repo)

    # ── K8: --kaynak-temizle ciktida govde YOK ───────────────────────────────
    print("\nK8 — --kaynak-temizle ciktisinda KAYIT GOVDESI yok")
    repo = sahte_repo(
        kaynaklar={"u-var": {"link": "https://oops", "uyelik": "ucretsiz-uyelik-adi",
                              "lisans": "CC BY-NC"}},
        urunler=[{"id": "u-var", "kategori": "Otomobil", "marka": ["X"], "baslik": "U1",
                  "aciklama": "a", "fiyat": "100 TL",
                  "gorseller": ["https://media.pruvo3d.com/urunler/u-var-1.jpg"]}],
    )
    try:
        rc, out, err = cagir(repo, "u-var", "--sil", "test", "--kaynak-temizle")
        kontrol(rc == 0, "rc=0", "rc=%d" % rc)
        kontrol("https://oops" not in out and "https://oops" not in err,
                "Ciktida/adimda LINK yok", "out=%r err=%r" % (out, err))
        kontrol("ucretsiz-uyelik-adi" not in out and "ucretsiz-uyelik-adi" not in err,
                "Ciktida UYELIK degeri yok", "out=%r err=%r" % (out, err))
        kontrol("CC BY-NC" not in out and "CC BY-NC" not in err,
                "Ciktida LISANS degeri yok", "out=%r err=%r" % (out, err))
    finally:
        temizle(repo)

    damga_vakalari()
    tasarimci_vakalari()

    print("\n" + ("-" * 78))
    print("KIRMIZI_VAKA=%s" % ",".join(sorted(KIRMIZI_VAKA)))
    if FAILS:
        print("HATALI: %d iddia kirmizi" % len(FAILS))
        for f in FAILS:
            print("  -", f)
        return 1
    print("HEPSI GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())

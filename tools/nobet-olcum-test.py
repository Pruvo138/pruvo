#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/nobet-olcum-test.py — `tools/nobet-olcum.py` KABUL TESTI (HERMETIK).

Kabul sorusu her vaka icin aynidir: **bu satiri silsem hangi iddia kirmizi yanar?**
Cevabi olmayan vaka kapsam yanilsamasidir.

🔴 HERMETIK: hicbir vaka GERCEK ev yolunu, gercek `evler.json`'u, gercek `isci.log`'u
ya da gercek kutuyu OKUMAZ/YAZMAZ. Butun dunya `tempfile.TemporaryDirectory()`
icinde kurulur; `repo_yolu_turet`in taban dizini `--fs-kok` ile oraya cevrilir.
Tek istisna TAVAN SAHIPLERI (`tools/defter-kota-taban.py` vb.) — onlar BU DEPONUN
dosyalaridir, salt OKUNUR.
🔴 FILO DERSI (BaBa, 4 Eyl — bir ev kabul testiyle KENDI deposunu SILDI): bu dosyada
yikici komut YOKTUR; gecici dunya baglam yoneticisinin kendi kapanisiyla gider ve
hicbir yol gercek bir eve cozulmez.

🔴 MUTANTLAR IZOLE KOPYADA KOSAR (canli govdede DEGIL — [[mutant-canli-govdede-yasamaz]]):
kaynak gecici dizine KOPYALANIR, metin capasi degistirilir, **capanin GERCEKTEN
1 kez degistigi DOGRULANIR** (isabet 0 ise mutant INERT'tir ve batarya kirmizi
yanar — [[mutant-capasi-giris-noktasinin-okumadigi-degerde-olmez]]), kopyanin
YAMASIZ hali once YESIL olmalidir ([[kopya-turetilemiyorsa-bayatlik-olculmez]]).
Her mutant icin KIRMIZI YANAN VAKANIN ADI basilir.

Kosum: `python3 tools/nobet-olcum-test.py`  (rc=0 = yesil)
CI: .github/workflows/nobet.yml `serit-b`
"""
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYNAK = os.path.join(ROOT, "tools", "nobet-olcum.py")

GIT_KIMLIK = ("-c", "user.name=nobet-olcum-test",
              "-c", "user.email=nobet-olcum-test@example.invalid",
              "-c", "commit.gpgsign=false")

SIMDI = dt.datetime(2026, 9, 10, 21, 0, 0, tzinfo=dt.timezone.utc)


def modul_yukle(yol, ad="pruvo_nobet_olcum"):
    # 🔴 BYTECODE ONBELLEGI KAPALI: mutant ile taban ayni boyutta olabilir ve
    # `__pycache__` girisi (mtime+boyut) yamasiz bytecode'u yeniden kosturur.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(ad, yol)
    if spec is None or spec.loader is None:
        raise RuntimeError("yuklenemedi: %s" % yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# FIKSTUR DUNYASI
# ---------------------------------------------------------------------------
def _git(kok, *argv, kimlikli=False):
    argliste = ["git", "-C", kok]
    if kimlikli:
        argliste += list(GIT_KIMLIK)
    argliste += list(argv)
    return subprocess.run(argliste, capture_output=True, text=True)


def _yaz(yol, icerik):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(icerik)


def _depo_ac(kok):
    os.makedirs(kok, exist_ok=True)
    _git(kok, "init", "-q")
    _git(kok, "symbolic-ref", "HEAD", "refs/heads/main")
    return kok


def _islemle(kok, mesaj):
    _git(kok, "add", "-A")
    return _git(kok, "commit", "-q", "-m", mesaj, kimlikli=True)


def fikstur_kur(tmp):
    """Fikstur dunyasi. Donen sozluk vakalarin okudugu TEK kaynaktir."""
    repolar = os.path.join(tmp, "repolar")
    hafiza = os.path.join(tmp, "hafiza")
    os.makedirs(repolar, exist_ok=True)
    os.makedirs(hafiza, exist_ok=True)

    # --- KraL: temiz · origin VAR · main 1 ILERI · 1 ARTIK + 1 CANLI worktree ---
    kral = _depo_ac(os.path.join(repolar, "pruvo"))
    _yaz(os.path.join(kral, "DEVAM.md"), "satir1\nsatir2\n")
    _yaz(os.path.join(kral, "CLAUDE.md"), "kral baglam\n")
    _islemle(kral, "ilk")
    bare = os.path.join(tmp, "uzak", "pruvo.git")
    os.makedirs(os.path.dirname(bare), exist_ok=True)
    subprocess.run(["git", "init", "-q", "--bare", bare], capture_output=True)
    _git(kral, "remote", "add", "origin", bare)
    _git(kral, "push", "-q", "origin", "main")
    _git(kral, "fetch", "-q", "origin")
    artik_agac = os.path.join(kral, ".claude", "worktrees", "artik-agac")
    _git(kral, "worktree", "add", "-q", "-b", "artik-dal", artik_agac)
    canli_agac = os.path.join(kral, ".claude", "worktrees", "canli-agac")
    _git(kral, "worktree", "add", "-q", "-b", "canli-dal", canli_agac)
    _yaz(os.path.join(canli_agac, "yeni.md"), "canli is\n")
    _islemle(canli_agac, "canli daldaki is")          # main'in atasi DEGIL -> CANLI
    _yaz(os.path.join(kral, "ek.md"), "main ilerledi\n")
    _islemle(kral, "main 1 ileri")                     # origin/main'e gore 1 ILERI

    # --- MaCiT: 2 IZLENMEYEN dosya (kirli=2) · remote YOK (remote_bos) ---
    macit = _depo_ac(os.path.join(repolar, "pruvo-hasat"))
    _yaz(os.path.join(macit, "DEVAM.md"), "m\n")
    _islemle(macit, "ilk")
    _yaz(os.path.join(macit, "kir1.txt"), "a\n")
    _yaz(os.path.join(macit, "kir2.txt"), "b\n")

    # --- eLiF / EyLüL: COK PARCALI ev adi (esleme tuzaginin kendisi) ---
    elif_ = _depo_ac(os.path.join(repolar, "faralya-panel"))
    _yaz(os.path.join(elif_, "DEVAM.md"), "e\n")
    _islemle(elif_, "ilk")
    eylul = _depo_ac(os.path.join(repolar, "faralya-pazarlama"))
    _yaz(os.path.join(eylul, "DEVAM.md"), "y\n")
    _islemle(eylul, "ilk")

    # --- CAKISMA: gercek UU uretir (parse degil, git'in kendi ciktisi) ---
    cakisma = _depo_ac(os.path.join(repolar, "cakisma"))
    _yaz(os.path.join(cakisma, "a.txt"), "bir\n")
    _islemle(cakisma, "ilk")
    _git(cakisma, "checkout", "-q", "-b", "yan")
    _yaz(os.path.join(cakisma, "a.txt"), "iki\n")
    _islemle(cakisma, "yan")
    _git(cakisma, "checkout", "-q", "main")
    _yaz(os.path.join(cakisma, "a.txt"), "uc\n")
    _islemle(cakisma, "main")
    _git(cakisma, "merge", "yan", kimlikli=True)       # CAKISIR -> UU

    # --- hafiza proje dizinleri (ad semasi: `-<yol parcalari>`) ---
    hafiza_dizinleri = {}
    for ev, repo in (("KraL", kral), ("MaCiT", macit), ("eLiF", elif_),
                     ("EyLüL", eylul), ("CaK", cakisma)):
        goreli = os.path.relpath(repo, tmp)
        ad = "-" + goreli.replace(os.sep, "-")
        dizin = os.path.join(hafiza, ad)
        os.makedirs(os.path.join(dizin, "memory"), exist_ok=True)
        hafiza_dizinleri[ev] = dizin
    # KraL: `<proje>/memory/MEMORY.md` · eLiF: `<proje>/MEMORY.md` (iki konum da olculur)
    _yaz(os.path.join(hafiza_dizinleri["KraL"], "memory", "MEMORY.md"), "k1\nk2\nk3\n")
    _yaz(os.path.join(hafiza_dizinleri["eLiF"], "MEMORY.md"), "e1\n")

    evler_json = os.path.join(tmp, "evler.json")
    tablo = {
        "_sema": "evler/1",
        "_not": "FIKSTUR — alt cizgili anahtarlar EV SAYILMAZ",
        "KraL": hafiza_dizinleri["KraL"],
        "ORTAK": hafiza_dizinleri["KraL"],          # AYNI koke dusen ikinci ad
        "MaCiT": hafiza_dizinleri["MaCiT"],
        "eLiF": hafiza_dizinleri["eLiF"],
        "EyLüL": hafiza_dizinleri["EyLüL"],
        "CaK": hafiza_dizinleri["CaK"],
    }
    with open(evler_json, "w", encoding="utf-8") as dosya:
        json.dump(tablo, dosya, ensure_ascii=False, indent=2)

    bozuk_json = os.path.join(tmp, "evler-bozuk.json")
    _yaz(bozuk_json, "{ bu json DEGIL")

    isci_log = os.path.join(tmp, "isci.log")
    _yaz(isci_log, _isci_log_metni(kral))

    return {
        "tmp": tmp, "repolar": repolar, "hafiza": hafiza,
        "evler_json": evler_json, "bozuk_json": bozuk_json, "isci_log": isci_log,
        "KraL": kral, "MaCiT": macit, "eLiF": elif_, "EyLüL": eylul, "CaK": cakisma,
        "artik_agac": artik_agac, "canli_agac": canli_agac,
    }


def _isci_log_metni(kral_kok):
    """Sentetik isci.log — her blok BASLANGIC/MOTOR/BITIS uclusuyle kapanir."""
    ici = "2026-09-10T19:00:00Z"      # SIMDI - 2 st  -> pencere ICI
    disi = "2026-09-08T19:00:00Z"     # SIMDI - 50 st -> pencere DISI
    gecici = os.path.join(kral_kok, ".claude", "worktrees", "gecici-agac")
    bloklar = [
        # cok parcali ev adlari — tam basename ile eslesmeli
        "=== %s BASLANGIC motor=minimax-m3 ev=faralya-panel etiket=a ===" % ici,
        "MOTOR=minimax-m3",
        "MOTOR=minimax-m3",
        "=== %s BITIS rc=0 sure=10 hal=SAGLIKLI ===" % ici,
        "=== %s BASLANGIC motor=minimax-m3 ev=faralya-pazarlama etiket=b ===" % ici,
        "MOTOR=minimax-m3",
        "=== %s BITIS rc=0 sure=10 hal=SAGLIKLI ===" % ici,
        "=== %s BASLANGIC motor=minimax-m3 ev=pruvo-hasat etiket=c ===" % ici,
        "MOTOR=minimax-m3",
        "=== %s BITIS rc=0 sure=10 hal=SAGLIKLI ===" % ici,
        # ev= alani WORKTREE adi; cozum ANAHTAR= tam yolundan YUKARI yuruyerek
        "=== %s BASLANGIC motor=minimax-m3 ev=gecici-agac etiket=d ===" % ici,
        "MOTOR=minimax-m3",
        "GUVEN=EVET ANAHTAR=%s IZIN=0" % gecici,
        "=== %s BITIS rc=0 sure=10 hal=SAGLIKLI ===" % ici,
        # hicbir eve cozulmeyen jeton -> `bilinmeyen:` kovasi GORUNUR kalir
        "=== %s BASLANGIC motor=minimax-m3 ev=yok-boyle-ev etiket=e ===" % ici,
        "MOTOR=minimax-m3",
        "=== %s BITIS rc=0 sure=10 hal=SAGLIKLI ===" % ici,
        # PENCERE DISI: sayilmamali
        "=== %s BASLANGIC motor=minimax-m3 ev=faralya-panel etiket=f ===" % disi,
        "MOTOR=minimax-m3",
        "=== %s BITIS rc=0 sure=10 hal=SAGLIKLI ===" % disi,
    ]
    return "\n".join(bloklar) + "\n"


def rapor_al(M, f, evler_json=None):
    return M.olc(evler_json=evler_json or f["evler_json"],
                 isci_log=f["isci_log"],
                 kalp_md=os.path.join(f["tmp"], "yok-kalp.md"),
                 kalp_json=os.path.join(f["tmp"], "yok-kalp.json"),
                 repo_kok=ROOT, fs_kok=f["tmp"], simdi=SIMDI)


def _ev(rapor, ad):
    for kayit in rapor.get("evler") or []:
        if kayit.get("ev") == ad:
            return kayit
    return None


def _kova(rapor, ad):
    return ((rapor.get("motor_orani") or {}).get("kovalar") or {}).get(ad) or {}


# ---------------------------------------------------------------------------
# VAKALAR — (ad, fonksiyon) ; fonksiyon (gecti_mi, detay) donuyor
# ---------------------------------------------------------------------------
def v_evler_kaynagi_yok(M, f):
    """MUTANT ① HEDEFI: evler.json YOKSA fail-closed (rc=1 + OLCULEMEDI)."""
    rapor = rapor_al(M, f, evler_json=os.path.join(f["tmp"], "hic-yok.json"))
    gecti = (rapor.get("rc") == 1 and rapor.get("EVLER_KAYNAGI") == M.OLCULEMEDI
             and bool(rapor.get("EVLER_KAYNAGI_SEBEP")))
    return gecti, "rc=%s EVLER_KAYNAGI=%s sebep=%r" % (
        rapor.get("rc"), rapor.get("EVLER_KAYNAGI"),
        (rapor.get("EVLER_KAYNAGI_SEBEP") or "")[:60])


def v_evler_kaynagi_bozuk(M, f):
    """Bozuk JSON da sessiz varsayilana DUSMEZ (ayni fail-closed kol)."""
    rapor = rapor_al(M, f, evler_json=f["bozuk_json"])
    gecti = rapor.get("rc") == 1 and rapor.get("EVLER_KAYNAGI") == M.OLCULEMEDI
    return gecti, "rc=%s EVLER_KAYNAGI=%s" % (rapor.get("rc"),
                                              rapor.get("EVLER_KAYNAGI"))


def v_butun_evler_satir_basar(M, f):
    """5 ayri koke dusen 6 ad -> 5 satir, rc=0 (bir ev dusse digerleri olculur)."""
    rapor = rapor_al(M, f)
    adlar = [k.get("ev") for k in rapor.get("evler") or []]
    gecti = (rapor.get("rc") == 0
             and set(adlar) == {"KraL", "MaCiT", "eLiF", "EyLüL", "CaK"}
             and rapor.get("sure_sn") is not None
             and (rapor.get("komut_turu") or 0) > 0)
    return gecti, "rc=%s evler=%s sure=%s komut_turu=%s" % (
        rapor.get("rc"), adlar, rapor.get("sure_sn"), rapor.get("komut_turu"))


def v_ayni_koke_dusen_ad_birlesir(M, f):
    """`ORTAK` KraL'in aynasidir: IKI satir degil BIR satir + `adlar` iki ad."""
    rapor = rapor_al(M, f)
    kral = _ev(rapor, "KraL")
    gecti = bool(kral) and kral.get("adlar") == ["KraL", "ORTAK"] \
        and _ev(rapor, "ORTAK") is None
    return gecti, "adlar=%s ORTAK satiri=%s" % (
        (kral or {}).get("adlar"), _ev(rapor, "ORTAK") is not None)


def v_cok_parcali_ev_yolu(M, f):
    """Naif `-`->`/` cevirimi `faralya-panel`i bozar; turetim DOSYA SISTEMINE sorar."""
    hedef = f["eLiF"]
    ad = "-" + os.path.relpath(hedef, f["tmp"]).replace(os.sep, "-")
    yol, hata = M.repo_yolu_turet(os.path.join(f["hafiza"], ad), kok=f["tmp"])
    gecti = (yol == hedef and hata is None)
    return gecti, "turetilen=%r beklenen=%r hata=%r" % (yol, hedef, hata)


def v_cozulemeyen_ev_olculemedi_alir(M, f):
    """Var olmayan koke dusen ad rc'yi BOZMAZ, birebir OLCULEMEDI + sebep alir."""
    bozuk = os.path.join(f["tmp"], "evler-eksik.json")
    with open(f["evler_json"], encoding="utf-8") as dosya:
        tablo = json.load(dosya)
    tablo["YoK"] = os.path.join(f["hafiza"], "-repolar-hic-boyle-depo-yok")
    with open(bozuk, "w", encoding="utf-8") as dosya:
        json.dump(tablo, dosya, ensure_ascii=False)
    rapor = rapor_al(M, f, evler_json=bozuk)
    yok = _ev(rapor, "YoK")
    gecti = (rapor.get("rc") == 0 and yok is not None
             and yok.get("SINIF") == M.OLCULEMEDI and bool(yok.get("sebep"))
             and _ev(rapor, "KraL") is not None)
    return gecti, "rc=%s YoK=%s sebep=%r" % (
        rapor.get("rc"), (yok or {}).get("SINIF"),
        ((yok or {}).get("sebep") or "")[:50])


def v_kirlilik_sayimi(M, f):
    """MUTANT ② HEDEFI: MaCiT'te 2 izlenmeyen dosya -> kirli=2 (0 DEGIL)."""
    rapor = rapor_al(M, f)
    git = (_ev(rapor, "MaCiT") or {}).get("git") or {}
    gecti = (git.get("kirli") == 2)
    return gecti, "MaCiT kirli=%r (2 beklenir)" % git.get("kirli")


def v_temiz_ev_sifir(M, f):
    """Ters kol: temiz ev 0 basar — mutant 'hep 0' olsa bu vaka YESIL kalir,
    o yuzden kirlilik ekseni IKI vakayla civilenir (tek yonlu nobetci olu nobetcidir)."""
    rapor = rapor_al(M, f)
    git = (_ev(rapor, "eLiF") or {}).get("git") or {}
    gecti = (git.get("kirli") == 0)
    return gecti, "eLiF kirli=%r (0 beklenir)" % git.get("kirli")


def v_uu_sayimi(M, f):
    """Gercek merge cakismasi UU=1 basar (status ciktisi UU ile baslar)."""
    rapor = rapor_al(M, f)
    git = (_ev(rapor, "CaK") or {}).get("git") or {}
    gecti = (git.get("UU") == 1 and (git.get("kirli") or 0) >= 1)
    return gecti, "CaK UU=%r kirli=%r" % (git.get("UU"), git.get("kirli"))


def v_remote_bos(M, f):
    """🔴 FILO DERSI: `git remote -v` BOS = bayrak. Iki yonlu olculur."""
    rapor = rapor_al(M, f)
    macit = ((_ev(rapor, "MaCiT") or {}).get("git") or {})
    kral = ((_ev(rapor, "KraL") or {}).get("git") or {})
    gecti = (macit.get("remote_bos") is True and kral.get("remote_bos") is False
             and (kral.get("remote_satir") or 0) >= 1)
    return gecti, "MaCiT remote_bos=%r · KraL remote_bos=%r satir=%r" % (
        macit.get("remote_bos"), kral.get("remote_bos"), kral.get("remote_satir"))


def v_ileri_geri(M, f):
    """KraL main'i origin/main'e gore 1 ILERI, 0 GERI."""
    rapor = rapor_al(M, f)
    git = (_ev(rapor, "KraL") or {}).get("git") or {}
    gecti = (git.get("ileri") == 1 and git.get("geri") == 0)
    return gecti, "KraL ileri=%r geri=%r (1/0 beklenir)" % (git.get("ileri"),
                                                           git.get("geri"))


def v_worktree_artik_canli(M, f):
    """ARTIK = temiz ∧ main'in atasi. CANLI = main'de OLMAYAN is var."""
    rapor = rapor_al(M, f)
    agaclar = {a["ad"]: a for a in
               (((_ev(rapor, "KraL") or {}).get("worktree") or {}).get("agaclar") or [])}
    artik = agaclar.get("artik-agac") or {}
    canli = agaclar.get("canli-agac") or {}
    gecti = (artik.get("SINIF") == "ARTIK" and canli.get("SINIF") == "CANLI"
             and artik.get("main_atasi") is True
             and canli.get("main_atasi") is False)
    return gecti, "artik-agac=%s (ata=%s) · canli-agac=%s (ata=%s)" % (
        artik.get("SINIF"), artik.get("main_atasi"),
        canli.get("SINIF"), canli.get("main_atasi"))


def v_worktree_kirli_canli(M, f):
    """Temiz olmayan worktree, HEAD'i main'de olsa bile ARTIK SAYILMAZ."""
    _yaz(os.path.join(f["artik_agac"], "gecici-kir.txt"), "kir\n")
    try:
        rapor = rapor_al(M, f)
        agaclar = {a["ad"]: a for a in
                   (((_ev(rapor, "KraL") or {}).get("worktree") or {})
                    .get("agaclar") or [])}
        artik = agaclar.get("artik-agac") or {}
        gecti = (artik.get("SINIF") == "CANLI" and artik.get("kirli") == 1
                 and artik.get("main_atasi") is True)
        detay = "artik-agac=%s kirli=%r ata=%s" % (
            artik.get("SINIF"), artik.get("kirli"), artik.get("main_atasi"))
    finally:
        os.remove(os.path.join(f["artik_agac"], "gecici-kir.txt"))
    return gecti, detay


def v_motor_faralya_panel(M, f):
    """MUTANT ③ HEDEFI: `ev=faralya-panel` -> `eLiF` kovasi (`faralya` DEGIL)."""
    rapor = rapor_al(M, f)
    kova = _kova(rapor, "eLiF")
    gecti = (kova.get("minimax-m3") == 2)
    return gecti, "eLiF kovasi=%r (minimax-m3=2 beklenir)" % kova


def v_motor_faralya_pazarlama(M, f):
    """MUTANT ③ ikinci kolu: `faralya-pazarlama` -> `EyLüL`."""
    rapor = rapor_al(M, f)
    kova = _kova(rapor, "EyLüL")
    gecti = (kova.get("minimax-m3") == 1)
    return gecti, "EyLüL kovasi=%r (minimax-m3=1 beklenir)" % kova


def v_motor_coklu_parca_hasat(M, f):
    """`pruvo-hasat` de cok parcalidir: tek-parcali esleme onu KraL'a katlardi."""
    rapor = rapor_al(M, f)
    gecti = (_kova(rapor, "MaCiT").get("minimax-m3") == 1)
    return gecti, "MaCiT kovasi=%r (minimax-m3=1 beklenir)" % _kova(rapor, "MaCiT")


def v_motor_anahtar_yolundan(M, f):
    """`ev=` worktree adiysa cozum `ANAHTAR=` tam yolundan YUKARI yuruyerek gelir."""
    rapor = rapor_al(M, f)
    gecti = (_kova(rapor, "KraL").get("minimax-m3") == 1)
    return gecti, "KraL kovasi=%r (minimax-m3=1 beklenir)" % _kova(rapor, "KraL")


def v_motor_bilinmeyen_gorunur(M, f):
    """Cozulemeyen jeton SESSIZCE YUTULMAZ: `bilinmeyen:<jeton>` kovasi ciktida."""
    rapor = rapor_al(M, f)
    kova = _kova(rapor, "bilinmeyen:yok-boyle-ev")
    ozet = (rapor.get("motor_orani") or {}).get("ozet") or {}
    gecti = (kova.get("minimax-m3") == 1 and ozet.get("eslesmeyen_kosum") == 1)
    return gecti, "bilinmeyen:yok-boyle-ev=%r eslesmeyen=%r" % (
        kova, ozet.get("eslesmeyen_kosum"))


def v_motor_pencere_disi_sayilmaz(M, f):
    """50 saat onceki kosum 24 saat penceresine GIRMEZ (eLiF 2 kalir, 3 olmaz)."""
    rapor = rapor_al(M, f)
    ozet = (rapor.get("motor_orani") or {}).get("ozet") or {}
    gecti = (ozet.get("kosum") == 6 and ozet.get("pencere_ici") == 5
             and _kova(rapor, "eLiF").get("minimax-m3") == 2)
    return gecti, "kosum=%r pencere_ici=%r eLiF=%r" % (
        ozet.get("kosum"), ozet.get("pencere_ici"),
        _kova(rapor, "eLiF").get("minimax-m3"))


def v_asim_bayragi_dort_kol(M, f):
    """`ASIM` dort kolu da ayri ayri: SATIR · BAYT · IKISI · "" (yesil)."""
    kollar = [
        (M.asim_bayragi(131, 130, 100, 12288), "SATIR"),
        (M.asim_bayragi(10, 130, 99999, 12288), "BAYT"),
        (M.asim_bayragi(131, 130, 99999, 12288), "IKISI"),
        (M.asim_bayragi(10, 130, 100, 12288), ""),
        (M.asim_bayragi(130, 130, 12288, 12288), ""),      # ESITLIK asim DEGIL
        (M.asim_bayragi(None, None, 100, None), ""),       # tavan yok -> bayrak yok
    ]
    hatali = [(g, b) for g, b in kollar if g != b]
    return (not hatali), "hatali kol=%r" % hatali


def v_memory_iki_konum(M, f):
    """MEMORY.md `<proje>/memory/` ya da `<proje>/` altinda olabilir; ikisi de olculur."""
    rapor = rapor_al(M, f)
    kral = ((_ev(rapor, "KraL") or {}).get("defter") or {}).get("MEMORY") or {}
    elif_ = ((_ev(rapor, "eLiF") or {}).get("defter") or {}).get("MEMORY") or {}
    gecti = (kral.get("satir") == 3 and kral.get("hata") is None
             and elif_.get("satir") == 1 and elif_.get("hata") is None
             and kral["yol"].endswith(os.path.join("memory", "MEMORY.md"))
             and not elif_["yol"].endswith(os.path.join("memory", "MEMORY.md")))
    return gecti, "KraL=%r/%r · eLiF=%r/%r" % (
        kral.get("satir"), kral.get("hata"), elif_.get("satir"), elif_.get("hata"))


def v_tavan_sahipten_okunur(M, f):
    """Tavanlar SAHIP dosyalarindan gelir; betikte IKINCI bir sabit YOK."""
    tavan, kaynaklar = M.tavanlar_coz(ROOT)
    beklenen = {}
    for anahtar, dosya, ad in (
            ("devam_satir", "defter-kota-taban.py", "TAVAN_SATIR"),
            ("devam_bayt", "defter-kota-taban.py", "TAVAN_BAYT"),
            ("memory_satir", "hafiza-indeks-arsivle.py", "VARSAYILAN_TAVAN_SATIR"),
            ("memory_bayt", "hafiza-indeks-arsivle.py", "VARSAYILAN_TAVAN_BAYT"),
            ("kutu_satir", "kutu-arsivle.py", "VARSAYILAN_TAVAN")):
        with open(os.path.join(ROOT, "tools", dosya), encoding="utf-8") as dosya_h:
            metin = dosya_h.read()
        import re as _re
        esleme = _re.search(r"^%s\s*=\s*(\d+)\s*$" % _re.escape(ad), metin,
                            _re.MULTILINE)
        beklenen[anahtar] = int(esleme.group(1)) if esleme else None
    sapan = {a: (tavan.get(a), beklenen.get(a)) for a in beklenen
             if tavan.get(a) != beklenen.get(a) or beklenen.get(a) is None}
    gecti = (not sapan) and all(M.OLCULEMEDI not in (kaynaklar.get(a) or "")
                                for a in beklenen)
    return gecti, "sapan=%r · tavan=%r" % (sapan, {a: tavan.get(a) for a in beklenen})


def v_kutu_tavani_sahipten(M, f):
    """Kutu tavani/yolu `kutu-arsivle.py`'den TURETILIR; kapanis jetonu SAYILIR."""
    sahte_kok = os.path.join(f["tmp"], "sahte-kral")
    kutu = os.path.join(f["tmp"], "sahte-kutu.md")
    _yaz(kutu, "blok1\n%s\nblok2\n%s\nson\n" % (M.KAPANIS_JETONU, M.KAPANIS_JETONU))
    _yaz(os.path.join(sahte_kok, "tools", "kutu-arsivle.py"),
         "import os\nVARSAYILAN_TAVAN = 3\n"
         "KUTU_VARSAYILAN = os.path.expanduser(\n    \"%s\")\n" % kutu)
    sonuc = M.kutu_olc(sahte_kok, 3)
    gecti = (sonuc.get("yol") == kutu and sonuc.get("satir") == 5
             and sonuc.get("kapanis_bekleyen") == 2 and sonuc.get("ASIM") == "SATIR"
             and sonuc.get("hata") is None)
    return gecti, "yol=%r satir=%r bekleyen=%r ASIM=%r hata=%r" % (
        sonuc.get("yol"), sonuc.get("satir"), sonuc.get("kapanis_bekleyen"),
        sonuc.get("ASIM"), sonuc.get("hata"))


def v_kalp_yasi(M, f):
    """Bekci kalbi: son damga YASI (dk); damga yoksa birebir sebep."""
    kalp_md = os.path.join(f["tmp"], "kalp.md")
    kalp_json = os.path.join(f["tmp"], "kalp.json")
    _yaz(kalp_md, "KOSTU=IHTAR@2026-09-10T18:00:00Z\n"
                  "KOSTU=TEFTIS@2026-09-10T20:00:00Z\n")
    _yaz(kalp_json, json.dumps({"damga": "2026-09-10T20:30:00Z"}))
    sonuc = M.kalp_olc(kalp_md, kalp_json, simdi=SIMDI)
    md = sonuc["bekci_teslim_kalp"]
    js = sonuc["gozcu_kalp"]
    bos = M.kalp_olc(os.path.join(f["tmp"], "yok.md"),
                     os.path.join(f["tmp"], "yok.json"), simdi=SIMDI)
    gecti = (md.get("yas_dk") == 60.0 and md.get("kol") == "TEFTIS"
             and js.get("yas_dk") == 30.0
             and bos["bekci_teslim_kalp"]["hata"] == "dosya yok"
             and bos["gozcu_kalp"]["hata"] == "dosya yok")
    return gecti, "md yas=%r kol=%r · json yas=%r · bos hata=%r" % (
        md.get("yas_dk"), md.get("kol"), js.get("yas_dk"),
        bos["bekci_teslim_kalp"]["hata"])


# 🔴 HUKUM YASAGI (Okan karari ②, 10 Eyl 23:3x): cron kolu hukum yazamaz — BETIK DE
# YAZMAZ. Bu vaka ciktinin EMIR KIPINE kaymadigini olcer. Liste buyurse kapi
# kirmizi yanar ve hukum metni RUTINE tasinir.
HUKUM_JETONLARI = ("IHTAR", "IHLAL", "CEZA", "KALDIR", "SILINSIN", "EMIR:",
                   "ALTIN KURAL", "KAPATILACAK", "DEVREDILIR", "HUKUM:",
                   "KIRMIZI YANDI", "OKAN KAPISI")


def v_hukum_yazmaz(M, f):
    """Iki yonlu: gercek cikti TEMIZ olmali, hukum jetonu gecen metin YAKALANMALI."""
    rapor = rapor_al(M, f)
    metin = M.md_uret(rapor)
    buyuk = metin.upper()
    sizan = [j for j in HUKUM_JETONLARI if j in buyuk]
    # negatif kol: nobetcinin kendisi olu olmasin
    kirli = "Bu ev IHTAR aldi, agac KALDIR."
    yakalanan = [j for j in HUKUM_JETONLARI if j in kirli.upper()]
    gecti = (not sizan) and len(yakalanan) == 2
    return gecti, "sizan=%r · negatif kolda yakalanan=%r" % (sizan, yakalanan)


def v_md_json_ayni_kosumdan(M, f):
    """MD ve JSON AYNI rapordan turer — ikinci kaynak yok (damga/sure birebir)."""
    rapor = rapor_al(M, f)
    metin = M.md_uret(rapor)
    gecti = (str(rapor.get("damga")) in metin
             and str(rapor.get("sure_sn")) in metin
             and str(rapor.get("komut_turu")) in metin
             and json.loads(json.dumps(rapor, ensure_ascii=False)) is not None)
    return gecti, "damga/sure/komut_turu MD'de=%s" % gecti


VAKALAR = (
    ("EVLER_KAYNAGI_YOK", v_evler_kaynagi_yok),
    ("EVLER_KAYNAGI_BOZUK", v_evler_kaynagi_bozuk),
    ("BUTUN_EVLER_SATIR_BASAR", v_butun_evler_satir_basar),
    ("AYNI_KOKE_DUSEN_AD_BIRLESIR", v_ayni_koke_dusen_ad_birlesir),
    ("COK_PARCALI_EV_YOLU", v_cok_parcali_ev_yolu),
    ("COZULEMEYEN_EV_OLCULEMEDI", v_cozulemeyen_ev_olculemedi_alir),
    ("KIRLILIK_SAYIMI", v_kirlilik_sayimi),
    ("TEMIZ_EV_SIFIR", v_temiz_ev_sifir),
    ("UU_SAYIMI", v_uu_sayimi),
    ("REMOTE_BOS", v_remote_bos),
    ("ILERI_GERI", v_ileri_geri),
    ("WORKTREE_ARTIK_CANLI", v_worktree_artik_canli),
    ("WORKTREE_KIRLI_CANLI", v_worktree_kirli_canli),
    ("MOTOR_FARALYA_PANEL", v_motor_faralya_panel),
    ("MOTOR_FARALYA_PAZARLAMA", v_motor_faralya_pazarlama),
    ("MOTOR_COKLU_PARCA_HASAT", v_motor_coklu_parca_hasat),
    ("MOTOR_ANAHTAR_YOLUNDAN", v_motor_anahtar_yolundan),
    ("MOTOR_BILINMEYEN_GORUNUR", v_motor_bilinmeyen_gorunur),
    ("MOTOR_PENCERE_DISI_SAYILMAZ", v_motor_pencere_disi_sayilmaz),
    ("ASIM_BAYRAGI_DORT_KOL", v_asim_bayragi_dort_kol),
    ("MEMORY_IKI_KONUM", v_memory_iki_konum),
    ("TAVAN_SAHIPTEN_OKUNUR", v_tavan_sahipten_okunur),
    ("KUTU_TAVANI_SAHIPTEN", v_kutu_tavani_sahipten),
    ("KALP_YASI", v_kalp_yasi),
    ("HUKUM_YAZMAZ", v_hukum_yazmaz),
    ("MD_JSON_AYNI_KOSUMDAN", v_md_json_ayni_kosumdan),
)
VAKA_TABLOSU = dict(VAKALAR)


# ---------------------------------------------------------------------------
# MUTANTLAR — IZOLE KOPYA + CAPA ISABETI DOGRULANIR
# ---------------------------------------------------------------------------
# (kod, aciklama, capa, yama, hedef vakalar)
MUTANTLAR = (
    ("M1",
     "evler.json okumasi SABITE cevrilir (fail-closed kol olur)",
     '    if not os.path.isfile(yol):\n'
     '        return None, "dosya yok: %s" % yol\n',
     '    if not os.path.isfile(yol):\n'
     '        return {"KraL": "/sabit/ev"}, None\n',
     ("EVLER_KAYNAGI_YOK",)),
    ("M2",
     "bir evin `git status` kolu sabit 0 dondurur",
     '    sonuc["kirli"] = len(satirlar)\n',
     '    sonuc["kirli"] = 0\n',
     ("KIRLILIK_SAYIMI",)),
    ("M3",
     "MOTOR ORANI ev eslemesi ESKI (tek-parcali) haline doner",
     '        ev = basename_haritasi.get(jeton)\n',
     '        ev = basename_haritasi.get(jeton.split("-")[0])\n',
     ("MOTOR_FARALYA_PANEL", "MOTOR_FARALYA_PAZARLAMA")),
)


def mutant_kos(kod, aciklama, capa, yama, hedefler, f, tmp):
    """Izole kopyada mutant kosar. (oldu_mu, satirlar) doner."""
    satirlar = []
    kopya_dizin = os.path.join(tmp, "mutant-%s" % kod)
    os.makedirs(kopya_dizin, exist_ok=True)
    # 🔴 TABAN ve MUTANT AYRI DOSYALARA yazilir — AYNI yola iki kez yazmak
    # OLCULEN BIR YANLIS YESIL uretti (10 Eyl, M1): capa ile yama AYNI UZUNLUKTA
    # oldugu ve iki yazim ayni saniyede dustugu icin CPython'un `__pycache__`
    # girisi (mtime+boyut anahtarli) GECERLI sayildi ve YAMASIZ bytecode yeniden
    # kosuldu -> mutant SAGKALMIS gorunuyordu, oysa yama dosyada DURUYORDU.
    # Ayri yol + `dont_write_bytecode` bu pencereyi tamamen kapatir.
    taban_yol = os.path.join(kopya_dizin, "taban_%s.py" % kod.lower())
    kopya = os.path.join(kopya_dizin, "mutant_%s.py" % kod.lower())
    shutil.copyfile(KAYNAK, taban_yol)

    with open(taban_yol, encoding="utf-8") as dosya:
        metin = dosya.read()
    isabet = metin.count(capa)
    if isabet != 1:
        satirlar.append("   🔴 CAPA ISABETI=%d (1 bekleniyor) — mutant INERT, "
                        "capayi guncelle" % isabet)
        return False, satirlar

    # ① kopya YAMASIZ halde hedef vakalari GECMELI (kopya turetilebilir mi)
    taban = modul_yukle(taban_yol, "pruvo_nobet_olcum_taban_%s" % kod.lower())
    for hedef in hedefler:
        gecti, detay = VAKA_TABLOSU[hedef](taban, f)
        if not gecti:
            satirlar.append("   🔴 YAMASIZ KOPYA `%s` vakasini GECMEDI (%s) — "
                            "bayatlik olculemez" % (hedef, detay))
            return False, satirlar
    satirlar.append("   yamasiz kopya: %s → YESIL" % ", ".join(hedefler))

    # ② yamayi uygula ve hedef vakalarin KIRMIZI yandigini ADIYLA yaz
    with open(kopya, "w", encoding="utf-8") as dosya:
        dosya.write(metin.replace(capa, yama))
    mutant = modul_yukle(kopya, "pruvo_nobet_olcum_mutant_%s" % kod.lower())
    yanan = []
    for hedef in hedefler:
        gecti, detay = VAKA_TABLOSU[hedef](mutant, f)
        durum = "YESIL (SAGKALDI)" if gecti else "KIRMIZI"
        satirlar.append("   hedef vaka `%s` → %s · %s" % (hedef, durum, detay))
        if not gecti:
            yanan.append(hedef)
    # yan etki: hedef olmayan vakalardan hangileri de kirmizi yandi (bilgi)
    yan = []
    for ad, fn in VAKALAR:
        if ad in hedefler:
            continue
        try:
            gecti, _d = fn(mutant, f)
        except KeyboardInterrupt:
            raise
        except BaseException:                                      # noqa: BLE001
            gecti = False
        if not gecti:
            yan.append(ad)
    satirlar.append("   yan etki (hedef disi kirmizi): %s" % (", ".join(yan) or "YOK"))
    oldu = len(yanan) == len(hedefler)
    if not oldu:
        satirlar.append("   🔴 MUTANT SAGKALDI — hedef kol OLCULMUYOR")
    return oldu, satirlar


# ---------------------------------------------------------------------------
def main():
    if not os.path.isfile(KAYNAK):
        print("!! olculecek kaynak YOK: %s" % KAYNAK)
        return 1
    with tempfile.TemporaryDirectory(prefix="nobet-olcum-test-") as tmp:
        f = fikstur_kur(tmp)
        print("== VAKALAR (%d) ==" % len(VAKALAR))
        M = modul_yukle(KAYNAK)
        bulgu = 0
        vaka_gecen = 0
        for ad, fn in VAKALAR:
            try:
                gecti, detay = fn(M, f)
            except KeyboardInterrupt:
                raise
            except BaseException as hata:                          # noqa: BLE001
                gecti, detay = False, "PATLADI: %r" % (hata,)
            print("%s %-30s %s" % ("✅" if gecti else "🔴", ad, detay))
            if gecti:
                vaka_gecen += 1
            else:
                bulgu += 1

        print("\n== MUTANTLAR (%d) ==" % len(MUTANTLAR))
        olen = 0
        for kod, aciklama, capa, yama, hedefler in MUTANTLAR:
            print("%s — %s" % (kod, aciklama))
            oldu, satirlar = mutant_kos(kod, aciklama, capa, yama, hedefler, f, tmp)
            for satir in satirlar:
                print(satir)
            print("   → %s" % ("ÖLDÜ ✅" if oldu else "SAĞKALDI 🔴"))
            if oldu:
                olen += 1
            else:
                bulgu += 1

    print("\nSONUC: VAKA %d/%d · MUTANT %d/%d · BULGU=%d"
          % (vaka_gecen, len(VAKALAR), olen, len(MUTANTLAR), bulgu))
    print("YESIL ✅" if bulgu == 0 else "KIRMIZI 🔴")
    return 0 if bulgu == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

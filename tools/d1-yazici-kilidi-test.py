#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 YAZICI KILIDI — KABUL TESTI (K49). GERCEK SURECLER, CANLI D1'e DOKUNMAZ.

  python3 tools/d1-yazici-kilidi-test.py

OLCULEN ARIZA: `tools/d1-sync.py`'nin YAZICI yolunda kilit YOKTU. Iki tam-katalog
yazicisi ayni anda kosabiliyordu; birinin HENUZ yazdigi satirlar otekinin `fazla`
kumesine dusup DELETE ediliyordu. Sinif UC KEZ atesledi (kosum 31532464176 -> 37 mesru
satir · 31502177931 -> 41 · 31546544881 -> 5). K48 turunda ikinci yazici kosulmak
uzereyken ucustaki yazici (PID 86177, ~350 sn) TESADUFEN olculup durduruldu: bizi kural
degil TESADUF korudu.

NEDEN BU DOSYA REPODA DURUYOR ([[mutasyon-kaniti-yeniden-uretilebilir]]): anlatilan
batarya kanit degildir. Surucu repoda durur, CI'da kosar, mutasyon bataryasi
(tools/d1-yazici-kilidi-mutasyon.py) BU dosyayi kapi olarak kullanir.

🔴 CANLI D1'E DOKUNULMAZ. Yaris GERCEK ISLETIM SISTEMI SURECLERIYLE kurulur ama her
surec d1-sync'in OFFLINE harness'ini (`_kt_kos`: sorgu/dosya_calistir uclari bellek ici
sqlite'a baglanir) kosar. Ag yok, wrangler yok, `pruvo-katalog` yok.

OLCULEN EKSENLER
  A YARIS (pozitif)    : ucusta GERCEK bir yazici varken ikinci YAZICI SURECI fail-closed
                         durur (rc = KILIT_MESGUL_RC) ve TEK SATIR bile yazmaz; birinci
                         yazici BOZULMADAN devam eder (rc=0, satirlari yazilmis).
  B KONTROL (negatif)  : tek yazici -> rc=0, satirlar yazilir, kilit SONDA BIRAKILIR
                         (yanlis-pozitif nobeti: kapi mesru kosumu kirmiyor).
  C BAYAT KILIT / OLU  : kayittaki PID OLU -> kilit DEVRALINIR (rc=0) ve gurultuyle basar.
  D BAYAT KILIT / CANLI: kayittaki PID YASIYOR -> DEVRALINMAZ (rc != 0).
  E OKUYUCU MUAF       : kilit BASKASINDA iken `--durum`/`--kuru` kollari kilide TAKILMAZ.
  F SAF BIRIM          : PID/kayit cozumu + kilit CAPASININ geri cekilme hali.
  G WORKTREE KAPSAMI   : AYNI deponun IKI agaci (ana + gercek `git worktree add`) TEK
                         canli D1'e yazar -> kilit AGAC SINIRINI asmali. Kilit KOK'e
                         capalanirsa her agac AYRI kilit alir ve ariza GERI DONER.

IC KOLLAR (surucu kendini alt surec olarak cagirir — sentetik yazici sureci):
  --yavas-yazici <kilit> <urun> <gecikme>  GERCEK yazici kolunu offline kos, her ifadede
                                           <gecikme> sn uyu (kilit penceresi genisler)
  --yazici-dene  <kilit> [bekleme]         GERCEK yazici kolunu offline kos, cikis kodunu don
  (<kilit> = `-` ise modulun KENDI cozdugu VARSAYILAN kilit kullanilir — G ekseni)
  --uyuyan       <saniye>                  yalnizca yasayan bir PID uret (D ekseni icin)
  --modul <yol>                            d1-sync modulunu BU dosyadan yukle (mutasyon
                                           surucusu mutant KOPYAYI boyle isaret eder)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
VARSAYILAN_MODUL = os.path.join(TOOLS, "d1-sync.py")

# Ic kollarin toplam suresi. Yazici ~1,2 sn tutar; racer 1,5 sn bekler -> pencere KESIN.
YAZICI_URUN = 12
YAZICI_GECIKME = 0.10
RACER_BEKLEME = 1.5


def modul_yukle(yol):
    """d1-sync.py'yi modul olarak yukle (adi tire icerir -> importlib gerekir)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(yol)))
    spec = importlib.util.spec_from_file_location("d1_sync_kilit_kabul", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ══════════════════════════════════════════════════════════════════════════════
# IC KOLLAR — alt surec olarak kosarlar
# ══════════════════════════════════════════════════════════════════════════════
def _kilit_coz(mod, arg):
    """`-` = modulun KENDI cozdugu VARSAYILAN kilit (G ekseni bunu olcer); aksi hal
    acik yol (A-E eksenleri: gercek `.git` capasina DOKUNULMAZ)."""
    return mod.KILIT if arg == "-" else arg


def _kol_yavas_yazici(mod, kilit, urun_sayisi, gecikme):
    """GERCEK yazici kolu (main(), bayraksiz) — offline sqlite, her ifadede uyur."""
    kilit = _kilit_coz(mod, kilit)
    conn = mod._kt_baglan()
    urunler = [mod._kt_urun("y%03d" % i) for i in range(urun_sayisi)]

    def _yavasla(_sql, _sayac):
        time.sleep(gecikme)
        return False        # ifade UYGULANIR (dusurulmez) — yalnizca yavaslatilir

    kod, cikti, sayac = mod._kt_kos(conn, urunler, [], dusur=_yavasla, kilit=kilit)
    print(json.dumps({"rc": kod, "yazma": sayac["yazma"],
                      "satir": conn.execute("SELECT COUNT(*) FROM urunler").fetchone()[0],
                      "cikti": cikti[-400:]}, ensure_ascii=False))
    return kod


def _kol_yazici_dene(mod, kilit, bekleme):
    """GERCEK yazici kolu — kilit mesgulse fail-closed durmali."""
    kilit = _kilit_coz(mod, kilit)
    if bekleme is not None:
        mod.KILIT_BEKLEME_SN = bekleme
    conn = mod._kt_baglan()
    urunler = [mod._kt_urun("z%03d" % i) for i in range(3)]
    kod, cikti, sayac = mod._kt_kos(conn, urunler, [], kilit=kilit)
    # `devralindi` AYRI bir alan: devralma mesaji ciktinin BASINDA durur, `cikti` ise
    # KUYRUKTAN kirpilir -> alt-dize aramasi kirpilmis metinde sessizce yanilirdi.
    print(json.dumps({"rc": kod, "yazma": sayac["yazma"],
                      "satir": conn.execute("SELECT COUNT(*) FROM urunler").fetchone()[0],
                      "devralindi": "BAYAT YAZICI KILIDI DEVRALINDI" in cikti,
                      "cikti": cikti[-600:]}, ensure_ascii=False))
    return kod


def _ic_kol(argv):
    """Ic kol calistirildiysa (kod, True); degilse (None, False)."""
    modul = VARSAYILAN_MODUL
    if "--modul" in argv:
        i = argv.index("--modul")
        modul = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        return modul, argv, False
    if argv[0] == "--uyuyan":
        time.sleep(float(argv[1]))
        return modul, argv, True
    if argv[0] == "--yavas-yazici":
        sys.exit(_kol_yavas_yazici(modul_yukle(modul), argv[1], int(argv[2]),
                                   float(argv[3])))
    if argv[0] == "--yazici-dene":
        bekleme = float(argv[2]) if len(argv) > 2 else None
        sys.exit(_kol_yazici_dene(modul_yukle(modul), argv[1], bekleme))
    return modul, argv, False


# ══════════════════════════════════════════════════════════════════════════════
# YARDIMCILAR
# ══════════════════════════════════════════════════════════════════════════════
def _ben(modul, *args):
    komut = [sys.executable, os.path.abspath(__file__)] + [str(a) for a in args]
    if modul != VARSAYILAN_MODUL:
        komut += ["--modul", modul]
    return komut


def _kayit_bekle(yol, pid, zaman_asimi=15.0):
    """Kilit dosyasinda `pid`e ait SAHIP KAYDI belirene kadar bekle. Doner: belirdi mi."""
    son = time.time() + zaman_asimi
    while time.time() < son:
        try:
            with open(yol, encoding="utf-8") as f:
                ham = f.read().strip()
            if ham:
                k = json.loads(ham)
                if int(k.get("pid")) == pid:
                    return True
        except (OSError, ValueError, TypeError):
            pass
        time.sleep(0.05)
    return False


def _json_son(metin):
    """Alt surecin son JSON satirini coz (stdout'ta baska gurultu olabilir)."""
    for satir in reversed([s for s in metin.splitlines() if s.strip()]):
        try:
            return json.loads(satir)
        except ValueError:
            continue
    return {}


def _kayit_yaz(yol, kayit):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False))


def _ortak_git_dizini(mod, kok):
    """`kok`un ORTAK git dizini (mutlak, realpath) ya da "" (git agaci DEGIL).
    Ortam `git_ortami()` ile temizlenir — miras GIT_DIR kesfi bozar."""
    try:
        r = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=kok,
                           capture_output=True, text=True, timeout=10,
                           env=mod.git_ortami())
    except (OSError, subprocess.SubprocessError):
        return ""
    yol = r.stdout.strip()
    if r.returncode != 0 or not yol:
        return ""
    if not os.path.isabs(yol):
        yol = os.path.join(kok, yol)
    yol = os.path.realpath(yol)
    return yol if os.path.isdir(yol) else ""


def _agac_kur(hedef, modul):
    """`hedef` agacinda bir `tools/` kur: gercek tools/ icerigi SYMLINK, olculen modul
    ise `hedef/tools/d1-sync.py` olarak baglanir. Boylece modulun KOK'u `hedef` olur
    (KOK = dirname(dirname(__file__)) ve abspath symlink COZMEZ)."""
    tdizin = os.path.join(hedef, "tools")
    os.makedirs(tdizin, exist_ok=True)
    for ad in os.listdir(TOOLS):
        h = os.path.join(tdizin, ad)
        if os.path.lexists(h):
            continue
        os.symlink(os.path.join(TOOLS, ad), h)
    d1 = os.path.join(tdizin, "d1-sync.py")
    if os.path.lexists(d1):
        os.unlink(d1)
    os.symlink(os.path.abspath(modul), d1)
    return d1


def _worktree_ekseni(mod, modul, tmp, dogrula):
    """G ekseni: AYNI deponun IKI agaci (ana + `git worktree add`) TEK canli D1'e
    yazar; kilit ikisini de kapsamali. Doner: (kuruldu, ayni_capa, yaris_rc)."""
    depo = os.path.join(tmp, "g-depo")
    wt = os.path.join(tmp, "g-worktree")
    os.makedirs(depo)
    try:
        mod.sentetik_git(depo, "init", "-q", check=True, capture_output=True)
        open(os.path.join(depo, "tohum.txt"), "w").write("tohum\n")
        mod.sentetik_git(depo, "add", "tohum.txt", check=True, capture_output=True)
        mod.sentetik_git(depo, "commit", "-q", "-m", "tohum",
                         check=True, capture_output=True)
        mod.sentetik_git(depo, "worktree", "add", "-q", "-b", "ikinci", wt,
                         check=True, capture_output=True)
    except Exception as e:                                  # noqa: BLE001
        dogrula("G0 PENCERE: sentetik depo + gercek `git worktree add` kuruldu",
                False, "%s: %s" % (type(e).__name__, e))
        return False, None, None

    d1_ana = _agac_kur(depo, modul)
    d1_wt = _agac_kur(wt, modul)
    mod_ana = modul_yukle(d1_ana)
    mod_wt = modul_yukle(d1_wt)

    dogrula("G0 PENCERE: sentetik depo + gercek `git worktree add` kuruldu; iki agacta "
            "AYRI KOK olctuk", mod_ana.KOK != mod_wt.KOK, (mod_ana.KOK, mod_wt.KOK))
    ayni_capa = mod_ana.KILIT == mod_wt.KILIT
    dogrula("G1 KAPSAM: AYRI KOK'lu iki agac AYNI kilit dosyasini cozuyor "
            "(ortak git dizini capasi)", ayni_capa, (mod_ana.KILIT, mod_wt.KILIT))

    # GERCEK YARIS: ana agactan yazici ucusta iken WORKTREE'den ikinci yazici.
    yazici = subprocess.Popen(
        _ben(d1_ana, "--yavas-yazici", "-", YAZICI_URUN, YAZICI_GECIKME),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        kuruldu = _kayit_bekle(mod_ana.KILIT, yazici.pid)
        dogrula("G2 PENCERE: ana agactaki yazici kilidi ALDI", kuruldu,
                "kayit belirmedi: %s" % mod_ana.KILIT)
        r = subprocess.run(_ben(d1_wt, "--yazici-dene", "-", RACER_BEKLEME),
                           capture_output=True, text=True)
        yaris_rc = r.returncode
        gj = _json_son(r.stdout)
        dogrula("G3 WORKTREE YARISI: WORKTREE'deki ikinci yazici fail-closed durdu "
                "(rc=%d, beklenen %d) — kilit AGAC SINIRINI asiyor"
                % (yaris_rc, mod.KILIT_MESGUL_RC),
                yaris_rc == mod.KILIT_MESGUL_RC, (r.stdout[-300:], r.stderr[-500:]))
        dogrula("G4 WORKTREE YARISI: ikinci yazici TEK IFADE bile gondermedi",
                gj.get("yazma") == 0 and gj.get("satir") == 0, gj)
    finally:
        yazici.kill()
        yazici.communicate()
    return True, ayni_capa, yaris_rc


def _olu_pid():
    """GERCEKTEN olu bir PID uret: bir alt surec baslat, bitmesini bekle, PID'ini don."""
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    # PID yeniden kullanilabilir; ayni tur icinde pratikte kullanilmaz. Fail-closed yon
    # zaten testin lehine DEGIL aleyhinedir: PID canliysa vaka KALDI yakar, sessiz gecmez.
    return p.pid


# ══════════════════════════════════════════════════════════════════════════════
def main(modul):
    gecen, kalan = [0], [0]
    olculen = []

    def dogrula(ad, kosul, detay=""):
        olculen.append((ad, bool(kosul)))
        if kosul:
            gecen[0] += 1
            print("  GECTI  " + ad)
        else:
            kalan[0] += 1
            print("  KALDI  " + ad + ((" — " + str(detay)[:500]) if detay else ""))

    mod = modul_yukle(modul)
    MESGUL = mod.KILIT_MESGUL_RC
    print("D1 YAZICI KILIDI KABUL TESTI (gercek surecler · offline sqlite · CANLI D1 YOK)")
    print("  modul: %s · kilit sabiti: %s · mesgul rc: %d"
          % (modul, os.path.basename(mod.KILIT), MESGUL))

    tmp = tempfile.mkdtemp(prefix="d1-yazici-kilidi-")
    try:
        # ── A. YARIS (pozitif) — ucusta GERCEK yazici varken ikincisi DURMALI ─────
        kilit = os.path.join(tmp, "a.lock")
        yazici = subprocess.Popen(
            _ben(modul, "--yavas-yazici", kilit, YAZICI_URUN, YAZICI_GECIKME),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ucusta = _kayit_bekle(kilit, yazici.pid)
        dogrula("A0 PENCERE KURULDU: birinci yazici kilidi ALDI ve SAHIP KAYDINI yazdi",
                ucusta, "kilit dosyasinda %s pid'li kayit belirmedi" % yazici.pid)

        t0 = time.time()
        r2 = subprocess.run(_ben(modul, "--yazici-dene", kilit, RACER_BEKLEME),
                            capture_output=True, text=True)
        yaris_sure = time.time() - t0
        ikinci = _json_son(r2.stdout)
        birinci_cikti, birinci_hata = yazici.communicate(timeout=120)
        birinci = _json_son(birinci_cikti)
        yaris_rc = r2.returncode

        dogrula("A1 YARIS: ikinci YAZICI SURECI fail-closed durdu (rc=%d, beklenen %d)"
                % (yaris_rc, MESGUL),
                yaris_rc == MESGUL, (r2.stdout[-300:], r2.stderr[-600:]))
        dogrula("A2 YARIS: ikinci yazici D1'e TEK IFADE bile gondermedi (yazma=0)",
                ikinci.get("yazma") == 0 and ikinci.get("satir") == 0, ikinci)
        dogrula("A3 YARIS: ret SEBEBI adiyla basildi (sessiz cikis DEGIL)",
                "BASKA BIR D1 YAZICISI UCUSTA" in r2.stderr, r2.stderr[-400:])
        dogrula("A4 YARIS: ikinci yazici ASILMADI — sinirli bekleme (%.1f sn < %.1f sn)"
                % (yaris_sure, RACER_BEKLEME + 25),
                yaris_sure < RACER_BEKLEME + 25, yaris_sure)
        dogrula("A5 BIRINCI YAZICI BOZULMADI: rc=0 ve %d urunun HEPSI yazildi"
                % YAZICI_URUN,
                yazici.returncode == 0 and birinci.get("rc") == 0
                and birinci.get("satir") == YAZICI_URUN,
                (yazici.returncode, birinci, birinci_hata[-300:]))
        dogrula("A6 HIJYEN: birinci yazici bitince kilit dosyasi BOS (bayat kayit yok)",
                os.path.exists(kilit) and open(kilit).read().strip() == "",
                repr(open(kilit).read()[:200]) if os.path.exists(kilit) else "dosya yok")

        # ── B. KONTROL KOLU (negatif) — yanlis-pozitif nobeti ────────────────────
        kilit_b = os.path.join(tmp, "b.lock")
        rb = subprocess.run(_ben(modul, "--yazici-dene", kilit_b),
                            capture_output=True, text=True)
        kontrol_rc = rb.returncode
        bj = _json_son(rb.stdout)
        dogrula("B1 KONTROL: TEK yazici normal kosar (rc=0) — kapi mesru kosumu KIRMIYOR",
                kontrol_rc == 0, (rb.stdout[-300:], rb.stderr[-400:]))
        dogrula("B2 KONTROL: satirlar GERCEKTEN yazildi (3 urun) — kapi yazmayi engellemedi",
                bj.get("satir") == 3 and bj.get("yazma", 0) > 0, bj)
        dogrula("B3 KONTROL: kilit SONDA BIRAKILDI (dosya bos, artik kilit yok)",
                os.path.exists(kilit_b) and open(kilit_b).read().strip() == "",
                repr(open(kilit_b).read()[:200]) if os.path.exists(kilit_b) else "dosya yok")
        dogrula("B4 KONTROL: mutlu yolda kilit gurultusu BASILMAZ (bayraksiz davranis ayni)",
                "KILIT" not in rb.stderr and "DEVRALINDI" not in rb.stdout,
                (rb.stdout[-200:], rb.stderr[-200:]))

        # ── C. BAYAT KILIT / SAHIP OLU -> DEVRALINIR ─────────────────────────────
        kilit_c = os.path.join(tmp, "c.lock")
        olu = _olu_pid()
        _kayit_yaz(kilit_c, {"pid": olu, "baslangic": time.time() - 400,
                             "kol": "senkron", "makine": "coken-makine"})
        dogrula("C0 OLCUM: uretilen PID GERCEKTEN olu (pid_yasiyor False diyor)",
                mod.pid_yasiyor(olu) is False, olu)
        rc_ = subprocess.run(_ben(modul, "--yazici-dene", kilit_c),
                             capture_output=True, text=True)
        bayat_olu_rc = rc_.returncode
        cj = _json_son(rc_.stdout)
        dogrula("C1 BAYAT KILIT (OLU PID): kilit DEVRALINDI, yazici kostu (rc=0)",
                bayat_olu_rc == 0 and cj.get("satir") == 3,
                (rc_.stdout[-300:], rc_.stderr[-400:]))
        dogrula("C2 BAYAT KILIT (OLU PID): devralma SESSIZ DEGIL — gerekce basildi",
                cj.get("devralindi") is True, rc_.stdout[-300:])
        dogrula("C3 KONTROL (yanlis-pozitif nobeti): TEMIZ kilitte 'devralindi' "
                "gurultusu BASILMAZ",
                bj.get("devralindi") is False, bj)

        # ── D. BAYAT KILIT / SAHIP CANLI -> DEVRALINMAZ ──────────────────────────
        # 🔴 Bu, devralma kolunun FAIL-OPEN kenaridir: "muhtemelen olmustur" ile
        # devralinirsa iki yazici ayni anda kosar ve mesru satir silinir.
        kilit_d = os.path.join(tmp, "d.lock")
        uyuyan = subprocess.Popen(_ben(modul, "--uyuyan", 30))
        try:
            _kayit_yaz(kilit_d, {"pid": uyuyan.pid, "baslangic": time.time() - 400,
                                 "kol": "senkron", "makine": "baska-oturum"})
            dogrula("D0 OLCUM: kayittaki PID GERCEKTEN canli (pid_yasiyor True diyor)",
                    mod.pid_yasiyor(uyuyan.pid) is True, uyuyan.pid)
            rd = subprocess.run(_ben(modul, "--yazici-dene", kilit_d),
                                capture_output=True, text=True)
            bayat_canli_rc = rd.returncode
            dj = _json_son(rd.stdout)
            dogrula("D1 BAYAT KILIT (CANLI PID): DEVRALINMADI — fail-closed durdu (rc=%d)"
                    % bayat_canli_rc,
                    bayat_canli_rc != 0, (rd.stdout[-300:], rd.stderr[-500:]))
            dogrula("D2 BAYAT KILIT (CANLI PID): tek satir bile yazilmadi",
                    dj.get("yazma", 0) == 0 and dj.get("satir", 0) == 0, dj)
            dogrula("D3 BAYAT KILIT (CANLI PID): ret gerekcesi CANLI PID'i adiyla soyluyor",
                    "CANLI BIR SURECE AIT" in rd.stderr and str(uyuyan.pid) in rd.stderr,
                    rd.stderr[-400:])
        finally:
            uyuyan.kill()
            uyuyan.wait()

        # ── E. OKUYUCU MUAF — kilit BASKASINDA iken okuyucu kollari TAKILMAZ ─────
        # Kilit gercekten TUTULUYOR: `--yavas-yazici` ucusta.
        kilit_e = os.path.join(tmp, "e.lock")
        yazici_e = subprocess.Popen(
            _ben(modul, "--yavas-yazici", kilit_e, YAZICI_URUN, YAZICI_GECIKME),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            tutuluyor = _kayit_bekle(kilit_e, yazici_e.pid)
            conn_e = mod._kt_baglan()
            urunler_e = [mod._kt_urun("e%02d" % i) for i in range(3)]
            t0 = time.time()
            kod_kuru, cikti_kuru, sayac_kuru = mod._kt_kos(conn_e, urunler_e, ["--kuru"],
                                                           kilit=kilit_e)
            kuru_sure = time.time() - t0
            mod._kt_kos(conn_e, urunler_e, [], kilit=os.path.join(tmp, "e-yazma.lock"))
            tk = mod._kt_turetilmis()
            t0 = time.time()
            kod_durum, cikti_durum, _ = mod._kt_kos(conn_e, urunler_e, ["--durum"],
                                                    turetilmis=tk, kilit=kilit_e)
            durum_sure = time.time() - t0
            dogrula("E0 PENCERE: kilit BASKA bir surec tarafindan TUTULUYOR",
                    tutuluyor, "kayit belirmedi")
            dogrula("E1 OKUYUCU MUAF: kilit tutuluyorken `--kuru` rc=0 ve BEKLEMEDI "
                    "(%.2f sn)" % kuru_sure,
                    kod_kuru == 0 and sayac_kuru["yazma"] == 0 and kuru_sure < 3.0,
                    (kod_kuru, sayac_kuru, cikti_kuru[-300:]))
            dogrula("E2 OKUYUCU MUAF: kilit tutuluyorken `--durum` rc=0 ve BEKLEMEDI "
                    "(%.2f sn)" % durum_sure,
                    kod_durum == 0 and durum_sure < 3.0,
                    (kod_durum, cikti_durum[-400:]))
        finally:
            yazici_e.kill()
            yazici_e.communicate()

        # ── F. SAF BIRIM: fail-closed yon (olcemedigimiz PID OLU SAYILMAZ) ───────
        dogrula("F1 SAF: gecersiz PID kaydi OLU SAYILMAZ (fail-closed)",
                mod.pid_yasiyor(None) is True and mod.pid_yasiyor("abc") is True
                and mod.pid_yasiyor(-1) is True and mod.pid_yasiyor(0) is True)
        dogrula("F2 SAF: kendi surecimiz YASIYOR",
                mod.pid_yasiyor(os.getpid()) is True)
        bos = os.path.join(tmp, "bos.lock")
        open(bos, "w").close()
        dogrula("F3 SAF: BOS kilit dosyasi 'sahip YOK' demektir (kayit None)",
                mod.kilit_kaydi_oku(bos) is None)
        bozuk = os.path.join(tmp, "bozuk.lock")
        with open(bozuk, "w") as f:
            f.write("{yarim-json")
        dogrula("F4 SAF: BOZUK kayit -> pid COZULEMEZ (None) ama kayit 'bozuk' isaretli",
                mod.kilit_kaydi_pid(mod.kilit_kaydi_oku(bozuk)) is None
                and "bozuk" in (mod.kilit_kaydi_oku(bozuk) or {}))
        depo_yok = os.path.join(tmp, "depo-yok")
        os.makedirs(depo_yok, exist_ok=True)
        dogrula("F5 SAF: git DEPOSU OLMAYAN dizinde kilit KOK'e geri cekilir "
                "(olculemedi -> kilit yine ALINIR, yalniz kapsami daralir)",
                mod._kilit_yolu(depo_yok)
                == os.path.join(depo_yok, mod.KILIT_YEDEK_ADI),
                mod._kilit_yolu(depo_yok))
        # 🔴 BEKLENTI OLCULEN AGACTAN TURETILIR, SABIT DEGIL: bu kapi hem gercek depoda
        # hem de mutasyon AYNASINDA (git deposu OLMAYAN gecici dizin) kosar. Sabit
        # "ortak git dizininde olmali" iddiasi aynada YANLIS-KIRMIZI yanar ve KONTROL
        # mutantlarini kirmiziya boyardi ([[nobetci-fikstur-sekli]]).
        ortak = _ortak_git_dizini(mod, mod.KOK)
        dogrula("F6 SAF: KILIT MUTLAK ve capasi olculen agacin haline UYUYOR (%s)"
                % ("depo -> ortak git dizini" if ortak else "depo DEGIL -> KOK'e cekilme"),
                os.path.isabs(mod.KILIT) and mod.KILIT == (
                    os.path.join(ortak, mod.KILIT_ADI) if ortak
                    else os.path.join(mod.KOK, mod.KILIT_YEDEK_ADI)),
                (mod.KILIT, ortak, mod.KOK))

        # ── G. WORKTREE KAPSAMI — AYNI DEPONUN IKI AGACI, TEK CANLI D1 ───────────
        # 🔴 OLCULEN KAPSAM HATASI: kilit KOK'e capalanirsa her worktree AYRI bir
        # kilit dosyasi kullanir ve iki yazici AYNI canli veritabanina ayni anda yazar.
        # `urunler.json` icin KOK dogru birimdir (her agacta AYRI dosya); D1 icin
        # DEGILDIR (TEK global kaynak). Bu eksen sentetik bir depo + GERCEK
        # `git worktree add` ile iki agac kurar ve aralarinda GERCEK yaris kosar.
        g_kuruldu, g_ayni_capa, g_yaris_rc = _worktree_ekseni(mod, modul, tmp, dogrula)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nOLCULEN SAYILAR")
    print("  YARIS_TEST(ikinci yazici rc) = %d   (beklenen %d)" % (yaris_rc, MESGUL))
    print("  KONTROL(tek yazici rc)       = %d   (beklenen 0)" % kontrol_rc)
    print("  BAYAT_KILIT_OLU rc           = %d   (beklenen 0)" % bayat_olu_rc)
    print("  BAYAT_KILIT_CANLI rc         = %d   (beklenen != 0)" % bayat_canli_rc)
    print("  WORKTREE_YARISI rc           = %s   (beklenen %d · ayni capa: %s)"
          % (g_yaris_rc, MESGUL, g_ayni_capa))
    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 1 if kalan[0] else 0


if __name__ == "__main__":
    _modul, _argv, _bitti = _ic_kol(sys.argv[1:])
    if _bitti:
        sys.exit(0)
    sys.exit(main(_modul))

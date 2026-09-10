#!/usr/bin/env python3
"""`cip-kapanis-kancasi.py` KABUL BATARYASI — davranissal, gercek subprocess.

Bu kanca BES EVIN her oturumunda kosar. Iki ayri felaket kipi var ve IKISI de
burada olculur:
  (a) BLOKLAMASI GEREKIRKEN GECIRIR -> yarim cip sessizce kapanir, is kaybolur.
  (b) GECMESI GEREKIRKEN BLOKLAR    -> mimar oturumlari / hatali girdi filoyu
      kilitler; kanca catlarsa da ayni sonuc.
Her vaka POZITIF ve NEGATIF yonuyle yazilir; tek yon = olu nobetci.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.realpath(__file__))
KANCA = os.path.join(KOK, "cip-kapanis-kancasi.py")
SAYAC_DIZIN = os.path.expanduser("~/.claude/cron/.cip-kapanis-sayaci")


def _ak():
    spec = importlib.util.spec_from_file_location(
        "_arsiv_kapisi", os.path.join(KOK, "arsiv-kapisi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kancayi_kos(veri, kanca=KANCA, kutu=None):
    argv = [sys.executable, kanca]
    if kutu:
        argv += ["--kutu", kutu]
    # Kanca KOPYASI gecici dizinde kosarken yaninda `arsiv-kapisi.py` YOKTUR;
    # kanonik `tools/` ortamla soylenir, yoksa kopya fail-open gecer ve mutasyon
    # turu tabaniyla birlikte coker (5 Eyl'de olculdu).
    ortam = dict(os.environ, PRUVO_KANONIK_TOOLS=KOK)
    s = subprocess.run(argv, input=json.dumps(veri),
                       capture_output=True, text=True, timeout=180, env=ortam)
    blokladi = False
    sebep = ""
    for satir in s.stdout.splitlines():
        satir = satir.strip()
        if not satir.startswith("{"):
            continue
        try:
            k = json.loads(satir)
        except ValueError:
            continue
        if k.get("decision") == "block":
            blokladi = True
            sebep = k.get("reason", "")
    return s.returncode, blokladi, sebep, s.stdout, s.stderr


def _sayaci_temizle(sid):
    try:
        os.remove(os.path.join(SAYAC_DIZIN, "%s.txt" % sid))
    except OSError:
        pass


def kos(kanca=KANCA, sessiz=False):
    ak = _ak()
    gecti = kirmizi = iddia = 0

    def check(ad, kosul):
        nonlocal gecti, kirmizi, iddia
        iddia += 1
        if kosul:
            gecti += 1
            if not sessiz:
                print("  [OK] %s" % ad)
        else:
            kirmizi += 1
            if not sessiz:
                print("  [KIRMIZI] %s" % ad)

    # --- fikstur: KIRMIZI cip agaci (kapanis yok) --------------------------
    kok = os.path.realpath(tempfile.mkdtemp(prefix="kanca-test-"))
    try:
        repo_k, hedef_k, kutu_k, _c = ak._kur_fikstur(kok + "/kirmizi", kapanis=False)
        repo_y, hedef_y, kutu_y, _c2 = ak._kur_fikstur(kok + "/yesil")

        # V1 POZITIF: kirmizi cip agaci -> BLOKLA
        sid = "test-v1"
        _sayaci_temizle(sid)
        rc, blok, sebep, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": hedef_k, "stop_hook_active": False}, kanca=kanca, kutu=kutu_k)
        check("V1 kirmizi cip -> BLOKLADI", blok)
        check("V1 rc=0 (blok exit koduyla degil JSON'la)", rc == 0)
        check("V1 sebep KIRMIZI kolu adiyla anar", "KAPANIS_YOK" in sebep)
        _sayaci_temizle(sid)

        # V2 NEGATIF: YESIL cip agaci -> GECIR
        sid = "test-v2"
        _sayaci_temizle(sid)
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": hedef_y, "stop_hook_active": False}, kanca=kanca, kutu=kutu_y)
        check("V2 yesil cip -> GECIRDI (yanlis-pozitif nobetcisi)", not blok)
        _sayaci_temizle(sid)

        # V3 NEGATIF: stop_hook_active -> ASLA blokla (dongu emniyeti)
        sid = "test-v3"
        _sayaci_temizle(sid)
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": hedef_k, "stop_hook_active": True}, kanca=kanca, kutu=kutu_k)
        check("V3 stop_hook_active=True -> GECIRDI", not blok)
        _sayaci_temizle(sid)

        # V4 NEGATIF: ANA checkout (mimar oturumu) -> GECIR
        sid = "test-v4"
        _sayaci_temizle(sid)
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": sid, "cwd": repo_k, "stop_hook_active": False}, kanca=kanca, kutu=kutu_k)
        check("V4 ana checkout -> GECIRDI (mimar cip degil)", not blok)
        _sayaci_temizle(sid)

        # V5 TAVAN: ayni oturum TAVAN kez bloklanir, sonrasi GECER
        sid = "test-v5"
        _sayaci_temizle(sid)
        bloklar = []
        for _ in range(4):
            _rc, blok, _s, _o, _e = kancayi_kos(
                {"session_id": sid, "cwd": hedef_k, "stop_hook_active": False},
                kanca=kanca, kutu=kutu_k)
            bloklar.append(blok)
        check("V5 tavan: ilk iki cagri blokladi", bloklar[0] and bloklar[1])
        check("V5 tavan: 3. ve 4. cagri GECTI (sonsuz dongu YOK)",
              (not bloklar[2]) and (not bloklar[3]))
        _sayaci_temizle(sid)

        # V6 FAIL-OPEN: bozuk stdin -> ne catla ne blokla
        rc, blok, _s, _o, _e = kancayi_kos_ham("bu JSON degil{{", kanca)
        check("V6 bozuk stdin -> rc=0", rc == 0)
        check("V6 bozuk stdin -> BLOKLAMADI", not blok)

        # V7 FAIL-OPEN: cwd yok
        _rc, blok, _s, _o, _e = kancayi_kos(
            {"session_id": "test-v7", "cwd": "/var/empty/yok", "stop_hook_active": False},
            kanca=kanca)
        check("V7 cwd yok -> GECIRDI", not blok)

        # --- V8 K396: KANCANIN ONERDIGI CARE, KAPININ FIILEN OKUDUGU CARE MI? ---
        # 🔴 BU NOBETCININ SEBEBI OLCULMUS BIR VAKADIR (10 Eyl 2026): kanca cipe
        # "'BEKLIYOR' olarak kutuya yaz" diyordu, `arsiv-kapisi.py` govdesinde o
        # jeton HIC YOKTU (`grep`=0) ve iki cip ust uste bu olu tavsiyeye takildi.
        # Kanca metni kapinin IKINCI KOPYASI gibi davranip sessizce ayrismisti
        # ([[kapi-red-metni-ikinci-kopyadir]]). Bu kol o ayrismayi OLCER: kancanin
        # BASTIGI jeton, kutu-arsivle'nin KANONIK jetonuyla BIREBIR ayni olmali VE
        # kapi govdesi o jetonu FIILEN okuyor olmali. Tek yon yetmez — jetonun
        # varligini olcmek, KULLANILDIGINI olcmez ([[capa-turetme-altyapisi-kullanilmadan-kaldi]]).
        import importlib.util as _ilu

        def _modul(ad, yol):
            _sp = _ilu.spec_from_file_location(ad, yol)
            _m = _ilu.module_from_spec(_sp)
            _sp.loader.exec_module(_m)
            return _m

        _tools = os.path.dirname(os.path.realpath(KANCA))
        _ka = _modul("kutu_arsivle_v8", os.path.join(_tools, "kutu-arsivle.py"))
        # 🔴 OLCULMUS KUSUR (10 Eyl, cip `KraL-Tamirci-10Eyl`): kancanin KOPYASINI
        # okuyan IKI tuketici var ve yalniz BIRI sozlesmeye baglanmisti.
        # `kancayi_kos()` kopyaya kanonik `tools/`u `PRUVO_KANONIK_TOOLS` ile SOYLER
        # (alt-surec env'i); burasi ise ayni kopyayi IC-SURECTE import ediyordu ve
        # o yolda degisken YOKTU. Kopya iki ekseni de tutturamayip makineye ozel
        # sabite dusuyor, Okan'in diskinde o dosya VAR oldugu icin V8b YESIL yaniyor,
        # CI'da YOK oldugu icin KIRMIZI -> mutasyon turunun TABANI kirmizi -> 5
        # mutant HIC olculmuyordu ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).
        # Sozlesme TEK KAYNAKTAN (`KOK`) kurulur; ikinci bir literal yol acilmadi.
        _onceki_env = os.environ.get("PRUVO_KANONIK_TOOLS")
        os.environ["PRUVO_KANONIK_TOOLS"] = KOK
        try:
            _kanca_mod = _modul("kanca_v8", kanca)
        finally:
            if _onceki_env is None:
                os.environ.pop("PRUVO_KANONIK_TOOLS", None)
            else:
                os.environ["PRUVO_KANONIK_TOOLS"] = _onceki_env
        _kanonik = getattr(_ka, "MERGE_BEKLIYOR_JETON", None)
        check("V8a kanonik jeton kutu-arsivle'de TANIMLI", bool(_kanonik))
        check("V8b kancanin bastigi jeton == kanonik jeton",
              getattr(_kanca_mod, "MUAFIYET_JETONU", None) == _kanonik)
        # V8e ANTI-MASKE: V8b tek basina YETMEZ — cunku Okan'in makinesinde
        # makineye ozel sabit de dogru jetonu okutur ve V8b sozlesme KOPUKKEN de
        # yesil yanar. Olculecek sey jetonun degeri DEGIL, jetonun HANGI EKSENDEN
        # geldigidir. Kopya, harness'in soyledigi kanonik `tools/`den cozulmelidir;
        # `makineye ozel kanonik repo` ekseninden cozulmesi CI'da yapisal KIRMIZI
        # demektir ve burada da KIRMIZI sayilir — yoksa arizayi kosucunun diski
        # gizler ([[iki-kollu-govde-tek-sabite-capalanirsa-kosucunun-diskini-olcer]]).
        _nereden = getattr(_kanca_mod, "KAPI_NEREDEN", None)
        check("V8e kopya HARNESS sozlesmesinden cozuldu (makine yolu DEGIL; "
              "gorulen=%s)" % _nereden, _nereden == "harness ortami")
        # Kapi govdesi jetonu FIILEN tuketiyor mu: beyani olan + itilmis bir
        # fikstur, `MERGE_BEKLIYOR` haliyle GECMELI. Bu, "jeton var" degil
        # "jeton ISE YARIYOR" iddiasidir.
        _repo_m, _hedef_m, _kutu_m, _cm = ak._kur_fikstur(
            kok + "/muaf", mainde=False, itilmis=True, merge_beyani=True)
        _h, _rc_m, _sat_m = ak.olc(_repo_m, _hedef_m, kutu_yolu=_kutu_m)
        check("V8c kapi jetonu FIILEN okuyor (beyan+push -> MERGE_BEKLIYOR, rc=0)",
              _rc_m == ak.RC_ARSIVLENEBILIR
              and ("HAL=%s" % ak.HAL_MERGE_BEKLIYOR) in "\n".join(_sat_m))
        # Kanca KIRMIZI bir cipe bloklarken jetonu METINDE de basmali — cip onu
        # okuyup uygulayacak. Basilmazsa tavsiye yine ULASMAZ.
        sid = "test-v8"
        _sayaci_temizle(sid)
        _rc8, blok8, sebep8, _o8, _e8 = kancayi_kos(
            {"session_id": sid, "cwd": hedef_k, "stop_hook_active": False},
            kanca=kanca, kutu=kutu_k)
        check("V8d blok metni kanonik jetonu ADIYLA basiyor",
              blok8 and bool(_kanonik) and _kanonik in sebep8)
        _sayaci_temizle(sid)
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    if not sessiz:
        print("\nIDDIA=%d GECTI=%d KIRMIZI=%d" % (iddia, gecti, kirmizi))
        print("KABUL %s" % ("YESIL" if kirmizi == 0 else "KIRMIZI"))
    return kirmizi == 0


def kancayi_kos_ham(ham, kanca=KANCA):
    s = subprocess.run([sys.executable, kanca], input=ham,
                       capture_output=True, text=True, timeout=120)
    blokladi = '"block"' in s.stdout
    return s.returncode, blokladi, "", s.stdout, s.stderr


MUTANTLAR = (
    ("M1 dongu-emniyetini-kaldir", "V3",
     '    if veri.get("stop_hook_active"):\n        return _gecti(',
     '    if False:\n        return _gecti('),
    ("M2 ana-checkout-muafiyetini-kaldir", "V4",
     '    if ana:\n        return _gecti("ana checkout',
     '    if False:\n        return _gecti("ana checkout'),
    ("M3 tavani-kaldir", "V5",
     '    if kac >= TAVAN:\n        return _gecti(',
     '    if False:\n        return _gecti('),
    ("M4 yesili-de-blokla", "V2",
     '    if s.returncode == RC_YESIL:\n        return _gecti("kapi YESIL")',
     '    if False:\n        return _gecti("kapi YESIL")'),
    # 🔴 K396 NOBETCISI: jetonu TURETMEK yerine GOMMEK — tam da kapatilan kusurun
    # kendisi. Mutant kancaya kendi sabitini yazdirir; V8b (kanonikle esitlik)
    # KIRMIZI yanmali. Bu mutant olmezse "kanca ile kapi ayrisamaz" iddiasi
    # OLCULMEMIS demektir ve ayrisma bir tur sonra sessizce geri gelir.
    ("M5 jetonu-turetme-gom", "V8",
     'MUAFIYET_JETONU = _muafiyet_jetonu()',
     'MUAFIYET_JETONU = "BEKLIYOR"'),
    # 🔴 K401 NOBETCISI: harness sozlesmesi (`PRUVO_KANONIK_TOOLS`) cozucuden
    # dusurulur. Bu, 10 Eyl'e kadar CANLI olan halin ta kendisidir: kopya iki
    # ekseni de tutturamaz, makineye ozel yola duser ve OKAN'IN DISKINDE dogru
    # jetonu okur. `V8b` bu mutanti GOREMEZ (jeton dogru cikar) — goren tek kol
    # `V8e`dir, cunku o jetonun DEGERINI degil HANGI EKSENDEN geldigini olcer.
    # Mutant olmezse "yesili uretense sozlesme, kosucunun diski degil" iddiasi
    # OLCULMEMIS demektir ve ariza bir tur sonra sessizce geri gelir
    # ([[iki-kollu-govde-tek-sabite-capalanirsa-kosucunun-diskini-olcer]]).
    ("M6 harness-eksenini-kaldir", "V8e",
     '    adaylar = ((os.environ.get(KANONIK_ENV) or "", "harness ortami"),\n',
     '    adaylar = ((\"\", \"harness ortami\"),\n'),
    # KONTROL: hedefsiz, davranis DEGISTIRMEYEN degisiklik. Bu "mutant" OLMEMELI.
    # Olurse batarya battaniye-kirmizidir (her degisiklige kirmizi yanar) ve
    # yukaridaki alti kill'in HICBIRI hedefine atfedilemez.
    ("MK2 kontrol-yorum-degisikligi", "(hedefsiz)",
     '\nRC_YESIL = 0',
     '\n# KONTROL MUTANTI: yalniz yorum, davranis ayni.\nRC_YESIL = 0'),
)

# Hedefsiz KONTROL mutantlari: OLMEMELERI beklenir (battaniye-kirmizi nobetcisi).
KONTROL_MUTANTLARI = ("MK2",)


def mutasyon():
    with open(KANCA, encoding="utf-8") as f:
        taban = f.read()
    kok = os.path.realpath(tempfile.mkdtemp(prefix="kanca-mut-"))
    kirmizi = 0
    print("MUTASYON — kopya uzerinde, canli kanca DEGISMEZ")
    try:
        kontrol = os.path.join(kok, "kontrol.py")
        with open(kontrol, "w", encoding="utf-8") as f:
            f.write(taban)
        ok = kos(kontrol, sessiz=True)
        print("  [%s] MK kontrol (mutantsiz kopya) -> %s"
              % ("OK" if ok else "KIRMIZI", "YESIL" if ok else "KIRMIZI"))
        if not ok:
            # 🔴 OLCULMUS SAHTE YESIL (5 Eyl, CI hali): kontrol KIRMIZI oldugu halde
            # tur devam edip 4 mutantin 4'unu "OLDU" diye BASIYORDU — oysa hepsinin
            # kirmizisi mutantin degil, TABANIN kirmizisiydi. Taban kirmiziyken
            # mutant hukmu VERILEMEZ ([[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
            #
            # 🔴 IKINCI KUSUR, AYNI KOLDA (10 Eyl, cip `KraL-Tamirci-10Eyl`): taban
            # `sessiz=True` kosuldugu icin KIRMIZI'nin SEBEBI hicbir yere yazilmiyordu.
            # CI logunda yalniz "TABAN KIRMIZI" duruyor, HANGI iddianin dustugu YOK;
            # yerelde de yeniden uretilemiyor (yesil yaniyor). Ariza bu yuzden gunlerce
            # yasadi: susma, "hic kosmadi"dan AYIRT EDILEMIYORDU
            # ([[taban-kirmizisi-nobetciyi-susturur]]). Taban kirmiziysa AYNI kopya
            # bir kez daha, bu sefer SESLI kosulur ve dusen iddia ADIYLA basilir.
            print("\n!! TABAN KIRMIZI — mutasyon turu KOSMAZ (once bataryayi yesile "
                  "getir). Bu turda OLCULEN mutant sayisi 0.")
            print("-- TABANIN SEBEBI (ayni kopya, sesli tekrar) " + "-" * 26)
            kos(kontrol, sessiz=False)
            print("-" * 70)
            print("MUTANT=0/%d KIRMIZI=1 (TABAN)" % len(MUTANTLAR))
            print("MUTASYON OLCULEMEDI")
            return False

        for ad, hedef, capa, yeni in MUTANTLAR:
            if taban.count(capa) != 1:
                print("  [KIRMIZI] %-34s CAPA ULASMADI (count=%d)"
                      % (ad, taban.count(capa)))
                kirmizi += 1
                continue
            yol = os.path.join(kok, ad.split()[0] + ".py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(taban.replace(capa, yeni))
            oldu = not kos(yol, sessiz=True)
            kontrol_mu = ad.split()[0] in KONTROL_MUTANTLARI
            # KONTROL mutantinda BEKLENTI TERSTIR: yasamasi gerekir.
            beklenti_tuttu = (not oldu) if kontrol_mu else oldu
            print("  [%s] %-34s hedef vaka=%-4s %s"
                  % ("OK" if beklenti_tuttu else "KIRMIZI", ad, hedef,
                     ("-> KONTROL yasadi (battaniye-kirmizi YOK)" if kontrol_mu
                      else "-> mutant OLDU") if beklenti_tuttu
                     else ("-> KONTROL OLDU = BATTANIYE KIRMIZI" if kontrol_mu
                           else "-> mutant ULASMADI")))
            if not beklenti_tuttu:
                kirmizi += 1
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    print("\nMUTANT=%d KIRMIZI=%d" % (len(MUTANTLAR) + 1, kirmizi))
    print("MUTASYON %s" % ("YESIL" if kirmizi == 0 else "KIRMIZI"))
    return kirmizi == 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(0 if mutasyon() else 1)
    sys.exit(0 if kos() else 1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d1-bayat-cikis-test.py — BAYAT ağaç kolunun CI çıkış kodu beyanı (spec-bayatlik-fail-open, 16 Agu 2026).

OLCULEN SINIF KUSURU (mimar): `d1-sync.py` uzun senkron sirasinda (`~95 sn`) ağac
bayatladiginda ICERIDEKI bayatlik kapisi devreye giriyor ve beyan metni "yayin
DURMAZ — pre-push hook exit 0 doner, CI adimi continue-on-error" diyordu ama kapinin
kendisi `sys.exit(...)` ile sifir-DISI cikardi. Uc ardarda CI kosumu
(`31966004096` / `31968088742` / `31969477134`) `Katalogu D1'e senkronla` adiminda
dusup `deploy`/`yayin` skipped etti. Beyan ile davranis UCMUYOR (sinif).

ONARIM: `bayatlik_engel_metni(...)` basildiktan sonra `return` ile normal cikis
(yazma YAPILMAZ; bu kapinin fail-closed ozelligi KORUNUR). Gercek senkron hatalari
(ag/yetki/SQL/wrangler/sema) gene sifir-disi cikar — fail-open kapsamini sizdirmaz.

BU DOSYA: spec'in zorunlu kabul testi. 3 vaka + 1 mutant (16 Agu 2026).

  V1 BAYAT agac             -> rc=0, D1'e yazma 0 kez (yazma sayaci)
  V2 TAZE + normal senkron  -> rc=0, yazma yolu CAGRILDI (>0)
  V3 TAZE + gercek hata     -> rc=1 (geri-okuma istisnasi; fail-open sizmasin)
  M1 Mutant                 -> bayat kolunu sys.exit(1)'e GERI ALAN mutant V1'i
                                KIRMIZI yakarak OLMELI. Bu en sade mutant: ayni
                                aracin onceki sinif-bozuk halini kosar.

YALNIZCA bu dosyanin test kapsaminda uretilir; canli D1'e / wrangler'a / ag'a
DOKUNMAZ. Stdlib + sqlite (offline fikstur); ~2 s.
"""
import importlib.util
import os
import re
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.dirname(os.path.abspath(__file__))
D1_SYNC = os.path.join(TOOLS, "d1-sync.py")
sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True       # hedef repoya __pycache__ YAZMA

# d1-sync modulunu adiyla degil dosyadan yukle (import sistemi `.` icermeyen ad ister).
_spec = importlib.util.spec_from_file_location("d1_sync_under_test", D1_SYNC)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_kt_kos = _mod._kt_kos
_kt_baglan = _mod._kt_baglan
_kt_urun = _mod._kt_urun
_kt_seyrelt = _mod._kt_seyrelt


def main():
    gecen = 0
    kalan = 0

    def dogrula(ad, kosul, detay=""):
        nonlocal gecen, kalan
        if kosul:
            gecen += 1
            print("  GECTI  " + ad)
        else:
            kalan += 1
            print("  KALDI  " + ad + (" — " + str(detay)[:400] if detay else ""))

    print("d1-bayat-cikis KABUL TESTI (offline sqlite fikstur; canli D1'e DOKUNMAZ)")

    # FIKSTUR — 3 eski urun, "bayat" olayinda silinmemelerini istiyoruz. Seyrelt
    # UYGULANIR: kanonik katalog 1.000.000 aralikli seq'lerle yasar; yeni urun
    # eklenirken TAM SAYI bosluk bulabilsin diye (13 Agu olculdu, --seq-normalize
    # tuzagi; V55 ile ayni fikstur deseni).
    eski_agac = [_kt_urun("e0"), _kt_urun("e1"), _kt_urun("e2")]

    # ── V1 BAYAT AGAC → rc=0, yazma sayaci 0 ──────────────────────────────────
    # Gercek senkronun "BAYAT koluna dustugu" an: yazmak istedigi 1 yeni id
    # D1'e YAZILMAMALI, yuksek sesli engel metni basilmali, ama process rc=0 ile
    # BITMELI (CI adimi yayini durdurmamali).
    conn1 = _kt_baglan()
    _kt_kos(conn1, eski_agac, [])
    _kt_seyrelt(conn1)
    kod, cikti, sayac = _kt_kos(conn1, eski_agac + [_kt_urun("ny00")], [],
                                bayatlik="BAYAT")
    dogrula("V1a BAYAT AGAC: rc=0 (beyan hizalı)",
            kod == 0, kod)
    dogrula("V1b BAYAT AGAC: D1'e HICBIR yazma yapilmadi (yazma sayaci 0)",
            sayac["yazma"] == 0, sayac)
    dogrula("V1c BAYAT AGAC: kapinin beyan metni BASILDI (sessiz-ENGEL degil)",
            "BAYATLIK KAPISI" in cikti
            and ("yayin DURMAZ" in cikti or "continue-on-error" in cikti),
            cikti[-1000:])
    # YENI urun tabloya GERCEKTEN GIRMEDI (D1 davranisi fail-closed korundu):
    dogrula("V1d BAYAT AGAC: 'ny00' D1'e YAZILMADI (fail-closed yazma reddi AYNEN KALIR)",
            _mod._kt_deger(conn1, "ny00", "hash") is None)

    # ── V2 TAZE + NORMAL SENKRON → rc=0, yazma yolu CAGRILDI ──────────────────
    # BAYAT koluna DUSMEMELI: gercek bir degisiklik D1'e yazilir, yazma sayaci > 0.
    conn2 = _kt_baglan()
    _kt_kos(conn2, eski_agac, [])
    _kt_seyrelt(conn2)
    kod, cikti, sayac = _kt_kos(conn2, eski_agac + [_kt_urun("ny01")], [],
                                bayatlik="UC")
    dogrula("V2a TAZE + normal: rc=0", kod == 0, kod)
    dogrula("V2b TAZE + normal: yazma yolu CAGRILDI (yazma sayaci > 0)",
            sayac["yazma"] > 0, sayac)
    dogrula("V2c TAZE + normal: geri-okuma dogrulandi (sessiz ariza yok)",
            "GERI-OKUMA DOGRULANDI" in cikti, cikti[-300:])
    # YENI urun tabloya GERCEKTEN GIRDI:
    dogrula("V2d TAZE + normal: 'ny01' D1'e YAZILDI (yazma yolu gercekten isledi)",
            _mod._kt_deger(conn2, "ny01", "hash") is not None)

    # ── V3 TAZE + GERCEK HATA → rc=1 (fail-open SIZMASIN) ────────────────────
    # oku_patlat=True: geri-okuma sorgusu RuntimeError atar; senkronun GERCEK hata
    # yolu (sys.exit mesaji) sifir-dISI cikar. Bayat kolu burada devreye GIRMEZ
    # (agac UC), bu yuzden onarimimizin fail-open kapsamini sizdirmadigini kanitlar.
    conn3 = _kt_baglan()
    _kt_kos(conn3, eski_agac, [])
    _kt_seyrelt(conn3)
    kod, cikti, _ = _kt_kos(conn3, eski_agac + [_kt_urun("ny02")], [],
                            bayatlik="UC", oku_patlat=True)
    dogrula("V3 TAZE + gercek hata (geri-okuma istisnasi) -> rc=1 "
            "(fail-open kapsami sizmadi)",
            kod == 1, (kod, cikti[-300:]))

    # ── M1 MUTANT KABULU: bayat kolu sys.exit(1)'e GERI ALINIRSA V1 KIRMIZI ──
    # Bu test, onarimi GERI ALMANIN (eski sinif-bozuk haline donmenin) testi
    # KIRMIZI oldugunu kanitlar; boylece bu kapi "her durumda yesil" olamaz.
    # Mantik: bayat kolunu `sys.exit(...)` ile eski bozuk haline ceviren mutant,
    # ayni V1 fiksturu ile ko; beklenen: kod=1 (sinif-bozuk hal) — V1 KIRMIZI.
    print("\n[M1 MUTASYON KOLU] bayat kolu sys.exit ile eski bozuk haline sifirlaniyor")
    _mutant_yol = None
    with open(D1_SYNC, encoding="utf-8") as _f:
        _kaynak = _f.read()
    # Bayat bolgesinin onarimli govdesini TERSINE cevir: `return` -> `sys.exit(1)`.
    # Bayat branch tek bir `return` satiri icerir (bizim onarimimiz). Onu bul ve
    # yerine eski sinif-bozuk halini koy.
    _marker = '# Yazma YAPMA; yuksek sesli engel metnini BAS'
    _idx = _kaynak.find(_marker)
    if _idx < 0:
        dogrula("M1 MUTASYON: beklenen bayat bloku KAYNAKTA BULUNAMADI "
                "(yorum degisti; elle yeni mutant kalibi yaz)",
                False, "kalip degisti")
    else:
        _return_idx = _kaynak.find('        return\n', _idx)
        if _return_idx < 0:
            dogrula("M1 MUTASYON: `        return` satiri bulunamadi (ic govde degisti)",
                    False, "kalip degisti")
        else:
            # Mutant gecici dosyada yasayacak; ancak `_KBK_YOL` `__file__`'a gore
            # COZULUYOR ve gecici dosyanin yaninda `konfigur-bundle-kapisi.py` yok.
            # Orijinal tools dizinine sabitle ve ARDINDAN kalan ofsetleri yeni
            # kaynak uzerinden tekrar hesapla (offset kaymasi olabilir).
            _kaynak_mut = _kaynak.replace(
                "_KBK_YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), \"konfigur-bundle-kapisi.py\")",
                "_KBK_YOL = os.path.join(%r, \"konfigur-bundle-kapisi.py\")" % TOOLS,
                1,
            )
            _idx_mut = _kaynak_mut.find(_marker)
            _return_idx_mut = _kaynak_mut.find('        return\n', _idx_mut)
            _mutant = (_kaynak_mut[:_return_idx_mut]
                       + '        sys.exit("MUTANT: eski sinif-bozuk hal")  # M1\n'
                       + _kaynak_mut[_return_idx_mut + len('        return\n'):])
            try:
                with tempfile.NamedTemporaryFile(
                        "w", suffix=".py", delete=False, encoding="utf-8") as _mf:
                    _mf.write(_mutant)
                    _mutant_yol = _mf.name
                _mspec = importlib.util.spec_from_file_location(
                    "d1_sync_mutant", _mutant_yol)
                _mmod = importlib.util.module_from_spec(_mspec)
                _mspec.loader.exec_module(_mmod)
                # MUTANT altinda ayni V1 fiksturu: eski kod sys.exit(1) ile cikar.
                mconn = _mmod._kt_baglan()
                _mmod._kt_kos(mconn, eski_agac, [])
                _mmod._kt_seyrelt(mconn)
                mkod, mcikti, msayac = _mmod._kt_kos(
                    mconn, eski_agac + [_mmod._kt_urun("ny00")], [],
                    bayatlik="BAYAT")
                dogrula("M1 MUTASYON OLMELI: V1 mutant altinda rc=0 DEGIL "
                        "(sinif-bozuk hal yakalandi)",
                        mkod != 0,
                        (mkod, mcikti[-400:]))
                dogrula("M1 MUTASYON: D1'e yazma yine 0 (fail-closed yazma reddi korunuyor)",
                        msayac["yazma"] == 0
                        and _mmod._kt_deger(mconn, "ny00", "hash") is None)
            finally:
                if _mutant_yol:
                    try:
                        os.unlink(_mutant_yol)
                    except OSError:
                        pass

    print()
    print("=== OZET: %d gecti, %d kaldi ===" % (gecen, kalan))
    return 0 if kalan == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

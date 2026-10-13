#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parametrik_sema.py — `parametrik:true` kayit ⇒ `jenerator/urunler/<id>.json` SEMASI ZORUNLU.

TEK KAYNAK: kural yalniz burada yazilidir. Iki tuketici ayni fonksiyonu cagirir, kopya kural
YOK: `tools/denetim-kapisi.py::kapi_parametrik_sema` (uretici tarafi, working-tree) ve
`tools/urun-kuyruk-birlestir.py` (tuketici tarafi, aday agacinin git nesneleri).

NEDEN VAR (13 Eki 2026, KraL-Tamirci-13Eki — OLCULEN OLAY): `009b7315` TEK parametrik kaydi
`olcuye-ozel-saksi-vazo` kataloga ekledi ama sema dosyasi (`jenerator/urunler/<id>.json`)
ayni merge'de DEGILDI (sema ayri cipte suruyordu). `build.konf_sema(id)` None dondu; sayfa
konfiguratorsuz (adetSec yok) ve fiyatsiz render oldu. Hicbir kapi "parametrik ⇒ sema"
demiyordu (`git grep konf_sema` = kapi 0); kirmizi, ALAKASIZ bir yerden gorundu:
`varlik-mutasyon.py` G5 (`--ornek 1` = "ilk parametrik kayit") `1c BAYAT 'Adet − +'` verdi,
`serit-a3` dustu, `deploy`+`yayin` SKIPPED — yeni urunlerin HICBIRI canliya inmedi (40+ dk).
Yanlis mesaj asil kusuru gizledi: sorun test degil, KAYIT sema olmadan girmisti.

KAPSAM = YENI parametrik kayit (kuyruk tarafinda: main'de parametrik OLMAYAN, aday'da olan id).
Onceden VAR OLAN kayit bu kapiyi TETIKLEMEZ (toplu gecmis borc ayri karardir; sessiz-yesil
sanilmasin diye `--tum-katalog --envanter` kolu RAPORLAR).

FAIL-CLOSED: id sema yoluna GUVENLE cevrilemiyorsa (bos / metin degil / yol ayiraci / `..`)
"sema var" DENMEZ — gerekce doner, kayit bloklanir. `sema_var` cagrisi istisna atarsa da
"sema yok" sayilir (belirsizlik DISARI).
"""
import re

# tools/build.py::JEN_URUN_DIR ile AYNI dizin; ayrisma `tools/parametrik-sema-test.py` V9'da olculur.
SEMA_DIZIN = "jenerator/urunler"
# Kanonik urun id'si: kucuk ASCII harf/rakam, tekil `-` `_` `.` ayiraclari. `..`, `/`, bosluk,
# bas/son ayirac REDDEDILIR (yol kacisi / sessiz yanlis dosya).
_GUVENLI_ID = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")


def parametrik_mi(urun):
    """Kayit parametrik mi? `parametrik` alani truthy (build.py/varlik-test.py ile AYNI olcut)."""
    return isinstance(urun, dict) and bool(urun.get("parametrik"))


def sema_yolu(uid):
    """id -> `jenerator/urunler/<id>.json` (repo kokune GORE). Guvenli degilse None."""
    if not isinstance(uid, str) or not _GUVENLI_ID.match(uid):
        return None
    return "%s/%s.json" % (SEMA_DIZIN, uid)


def semasiz_gerekce(urun, sema_var):
    """None = tamam (parametrik degil YA DA sema VAR). str = IHLAL gerekcesi.

    `sema_var(goreli_yol) -> bool`: tuketici sema dosyasinin varligini KENDI evreninde olcer
    (working-tree dosyasi ya da git nesnesi). Bu modul dosya sistemine/git'e DOKUNMAZ."""
    if not parametrik_mi(urun):
        return None
    uid = urun.get("id")
    yol = sema_yolu(uid)
    if yol is None:
        return ("parametrik kayit: id %r sema yoluna GUVENLE cevrilemiyor (kucuk ASCII "
                "harf/rakam + tekil - _ . bekleniyor) — fail-closed" % (uid,))
    try:
        var = bool(sema_var(yol))
    except Exception as e:                                           # noqa: BLE001
        return ("parametrik kayit %s: sema varligi OLCULEMEDI (%s: %s) — fail-closed"
                % (uid, type(e).__name__, e))
    if var:
        return None
    return ("parametrik kayit `%s` kataloga SEMASI OLMADAN giriyor: `%s` YOK. Sema olmadan "
            "sayfa konfiguratorsuz + adetsiz + fiyatsiz render olur (calismayan ozellik "
            "canliya iner). CARE SIRASI: ONCE sema dosyasi main'e (kod yolu), SONRA kayit "
            "(kuyruk yalniz urunler.json tasir; sema kuyruktan GECMEZ) — dogrudan commit'te "
            "ikisi AYNI commit'te olabilir. Sema hazir degilse kaydi EKLEME. Kapiyi/testi "
            "GEVSETME." % (uid, yol))


def semasizlar(urunler, sema_var, sadece_idler=None):
    """Liste uzerinde toplu olcum -> [(id, gerekce)] (sirali). `sadece_idler` verilirse yalniz
    o id'ler (kuyruk tarafi: aday'da YENI parametrik olanlar)."""
    cikti = []
    for u in urunler:
        if not parametrik_mi(u):
            continue
        if sadece_idler is not None and u.get("id") not in sadece_idler:
            continue
        g = semasiz_gerekce(u, sema_var)
        if g:
            cikti.append((u.get("id"), g))
    return sorted(cikti, key=lambda x: str(x[0]))

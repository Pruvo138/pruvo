#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/d1-kaynak-sync.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/d1-kaynak-sync-zarf-test.py

VAKA (Z): aracin D1 okuma yolu (`d1_linkler` + `tablo_var_mi`) `d1_zarf_fikstur.zarf(...)`
ile beslenir; satir sayisi + en az bir alan degeri birebir beklenenle eslesmeli.

MUTANT (M1): mutant kopyada ayristirma satiri `blok.get("results")` -> `[]` kirilir;
Z vakasi KIRMIZI yanar (0 satir sayar).

VAKA (Y, 21 Eki): `--durum` YETIM siniflamasi ayni gercek zarf uzerinden uctan uca —
silinmis id -> SILINMIS (kirmizi yakmaz), katalogda var-ama-D1'de-yok -> GERCEK_EKSIK
(SAPMA), bozuk katalog -> OLCULEMEDI.
MUTANT (M2): SILINMIS'i GERCEK_EKSIK sayan kopya -> Y KIRMIZI yanar.

Son satir: KABUL <g>/2 MUTANT <m>/2  (YESIL icin 2/2 + 2/2; rc=0).
"""
import contextlib
import importlib
import importlib.util
import io
import json as _json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

# AG/SUBPROCESS YASAGI (17 Eki): zarf testi canli wrangler'a CIKAMAZ. Mutant kolu sahteyi
# takmadan gercek d1-sync'e gidince yerelde canli D1 sorgusu, CI'da kimliksiz kirmizi oldu.
import subprocess as _sp                                 # noqa: E402


_SP_ASIL = {ad: getattr(_sp, ad) for ad in ("run", "Popen", "check_output", "call")}
_YASAK_JETON = ("wrangler", "npx", "curl", "wget")        # git SERBEST (veri_kok cozumu)


def _sarmala(ad):
    asil = _SP_ASIL[ad]

    def _bekci(*a, **k):
        cmd = a[0] if a else k.get("args")
        metin = " ".join(map(str, cmd)) if isinstance(cmd, (list, tuple)) else str(cmd)
        if any(j in metin for j in _YASAK_JETON):
            raise RuntimeError("ZARF TESTI AGA CIKAMAZ: %r" % metin[:120])
        return asil(*a, **k)
    return _bekci


for _ad in _SP_ASIL:
    setattr(_sp, _ad, _sarmala(_ad))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import d1_zarf_fikstur                                  # noqa: E402  (ortak gercek zarf)
ARAC = os.path.join(TOOLS, "d1-kaynak-sync.py")


def _yukle_isimle(ad, modul_yol):
    """Tireli adi importlib ile yukle ve sys.modules'a koy."""
    spec = importlib.util.spec_from_file_location(ad, modul_yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _yukle_arac(arac_yolu, modul_ad):
    """Aracin govdesini importlib ile yukle (tireli adlar dahil)."""
    spec = importlib.util.spec_from_file_location(modul_ad, arac_yolu)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mutasyonla(yol, eski, yeni):
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(eski) != 1:
        raise AssertionError("MUTANT CAPASI BAYAT: %r govdede %d kez" % (eski, govde.count(eski)))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni))


_LOADER = ('_ds_spec = importlib.util.spec_from_file_location("d1_sync", _DS_YOL)\n'
           'ds = importlib.util.module_from_spec(_ds_spec)\n'
           '_ds_spec.loader.exec_module(ds)')


def _mutant_ns(eski, yeni):
    """Arac govdesini `eski`->`yeni` ile bozup ayri bir ad alaninda kur. Capa tek degilse None.
    d1-sync gercek haliyle (yeniden yuklenmeden) baglanir; ag/subprocess bekcisi gecerli."""
    with open(ARAC, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(eski) != 1 or govde.count(_LOADER) != 1:
        return None
    if "d1_sync_mutant" not in sys.modules:
        _yukle_isimle("d1_sync_mutant", os.path.join(TOOLS, "d1-sync.py"))
    govde = govde.replace(eski, yeni, 1).replace(
        _LOADER, 'ds = sys.modules["d1_sync_mutant"]', 1)
    ns = {"__name__": "_mutant_", "__file__": ARAC}
    exec(govde, ns)
    return ns


def _yetim_vakalari(durum_fn, ayarla, tmp):
    """durum()'u sahte gizli kayit + katalog + GERCEK zarfla kos. Doner: sorun metni ya da ""."""
    def kos(yerel_idler, d1_idler, katalog):
        kay = os.path.join(tmp, "kaynaklar.json")
        kat = os.path.join(tmp, "urunler.json")
        with open(kay, "w", encoding="utf-8") as f:
            _json.dump({i: {"link": "https://example.com/%s" % i} for i in yerel_idler}, f)
        with open(kat, "w", encoding="utf-8") as f:
            f.write(katalog if isinstance(katalog, str)
                    else _json.dumps([{"id": i} for i in katalog]))
        satir = [{"id": i, "link": "https://example.com/%s" % i} for i in d1_idler]
        ayarla("KAYNAKLAR", kay)
        ayarla("URUNLER", kat)
        ayarla("ds", type("DS", (), {"sorgu": staticmethod(
            lambda sql: d1_zarf_fikstur.zarf(satir) if "FROM urun_kaynak" in sql
            else d1_zarf_fikstur.zarf([{"name": "urun_kaynak"}]))}))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = durum_fn()
        return rc, buf.getvalue()

    beklenen = (
        ("ikisi", (["silinmis", "var", "tam"], ["tam"], ["tam", "var"]), 1,
         ["YETIM SILINMIS=1 GERCEK_EKSIK=1 TOPLAM=2", "HUKUM=SAPMA"]),
        ("yalniz-silinmis", (["silinmis", "tam"], ["tam"], ["tam"]), 0,
         ["YETIM SILINMIS=1 GERCEK_EKSIK=0 TOPLAM=1", "HUKUM=SENKRON"]),
        ("bozuk-katalog", (["silinmis", "tam"], ["tam"], "{bozuk"), 1,
         ["YETIM OLCULEMEDI", "HUKUM=OLCULEMEDI"]),
    )
    for ad, girdi, rc_bek, satirlar in beklenen:
        rc, cikti = kos(*girdi)
        if rc != rc_bek or any(s not in cikti for s in satirlar) or "://" in cikti:
            return "%s: rc=%d (bek %d) cikti=%r" % (ad, rc, rc_bek, cikti[-160:])
    return ""


def main():
    gecen, hata = [], []

    # ── Z: gercek zarf fiksturu uzerinden d1_linkler + tablo_var_mi ────────────
    m = _yukle_arac(ARAC, "d1_kaynak_sync_zarf")
    bek = [{"id": "u-001", "link": "https://example.com/a"},
           {"id": "u-002", "link": "https://example.com/b"},
           {"id": "u-003", "link": ""}]
    zarf = d1_zarf_fikstur.zarf(bek)
    # tablo_var_mi: sqlite_master sorgusu tablo adini iceren bir satir donmeli.
    # Icerigi onemsiz; "results bos degil" == tablo var sayimi yeterli.
    zarf_tab = d1_zarf_fikstur.zarf([{"name": "urun_kaynak"}])
    cagri = {"n": 0}

    def sahte_sorgu(sql):
        cagri["n"] += 1
        return zarf if "FROM urun_kaynak" in sql else zarf_tab

    eski_ds = m.ds
    try:
        m.ds = type("DS", (), {"sorgu": staticmethod(sahte_sorgu)})
        var = m.tablo_var_mi()
        linkler = m.d1_linkler()
        if (var is True and len(linkler) == 3
                and linkler["u-001"] == "https://example.com/a"
                and linkler["u-002"] == "https://example.com/b"
                and linkler["u-003"] == ""
                and cagri["n"] >= 2):
            gecen.append("Z")
        else:
            hata.append("Z wrangler zarf ayristirilmadi: var=%s n=%d linkler=%r"
                        % (var, cagri["n"], list(linkler.items())[:3]))
    finally:
        m.ds = eski_ds

    # ── M1: mutant kopyada ayristirma [] olursa d1_linkler bos doner ───────────
    # d1-sync'i ONCE sys.modules'a gercek haliyle koy ki mutant govde onu bulabilsin.
    tmp = tempfile.mkdtemp(prefix="d1-kaynak-sync-mutant-")
    try:
        _yukle_isimle("d1_sync_mutant", os.path.join(TOOLS, "d1-sync.py"))

        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        if govde.count('for satir in (blok.get("results") or []):') != 1:
            raise AssertionError("MUTANT CAPASI BAYAT: ana satir bulunamadi")
        mutant = govde.replace('for satir in (blok.get("results") or []):',
                               'for satir in []:', 1)
        # d1-sync modulunu gercekten karsilasacak sekilde loader'i bypass et.
        mutant = mutant.replace(
            '_ds_spec = importlib.util.spec_from_file_location("d1_sync", _DS_YOL)\nds = importlib.util.module_from_spec(_ds_spec)\n_ds_spec.loader.exec_module(ds)',
            'sys.modules["d1_sync"] = sys.modules["d1_sync_mutant"]\n'
            'ds = sys.modules["d1_sync_mutant"]',
            1)
        # KAYNAKLAR'i bos gecici dosyaya yonlendir (yoksa sys.exit).
        sahte_kaynak = os.path.join(tmp, ".urun-kaynaklari.json")
        with open(sahte_kaynak, "w", encoding="utf-8") as f:
            _json.dump({}, f)
        mutant = mutant.replace(
            'KAYNAKLAR = os.path.join(KOK, ".urun-kaynaklari.json")',
            'KAYNAKLAR = %r' % sahte_kaynak, 1)
        mutant = mutant.replace(
            'sys.path.insert(0, os.path.join(KOK, "tools"))',
            'sys.path.insert(0, %r)' % TOOLS, 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os, "json": _json,
              "re": __import__("re"), "importlib": importlib,
              "argparse": __import__("argparse")}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        # govde d1-kaynak-sync modulunu adla kaydetmedi; `d1_linkler` ns uzerinden erisilir.
        # Esle: ns icindeki d1_linkler fonksiyonunun __module__'u "_mutant_" olmali.
        if ns.get("d1_linkler") is not None:
            # dummy wrapper: d1_linkler'i bir shim modulune bagla ki m2.ds atayalim.
            shim = type("M", (object,), {
                "d1_linkler": staticmethod(ns["d1_linkler"]),
                "tablo_var_mi": staticmethod(ns["tablo_var_mi"]),
                "ds": None})()
            m2 = shim
        else:
            m2 = ns.get("d1_kaynak_sync") or ns.get("ds")
        if m2 is None:
            hata.append("M1 mutant govdesi yuklenemedi (modul bulunamadi)")
        else:
            zarf2 = d1_zarf_fikstur.zarf(bek)
            zarf2_tab = d1_zarf_fikstur.zarf([{"name": "urun_kaynak"}])
            m2.ds = type("DS", (), {"sorgu": staticmethod(
                lambda sql: zarf2 if "FROM urun_kaynak" in sql else zarf2_tab)})
            # Mutant fonksiyonlarin global'i `ns`'tir: sahte `ds` ORAYA takilmazsa d1_linkler
            # gercek d1-sync'e (canli wrangler) gider — 17 Eki CI kirmizisi bu yuzdendi.
            ns["ds"] = m2.ds
            try:
                linkler2 = m2.d1_linkler()
                if len(linkler2) == 0:
                    gecen.append("M1")
                else:
                    hata.append("M1 ayristirma [] ile kirildi ama linkler bos degil: %r"
                                % list(linkler2.items())[:3])
            except Exception as e:
                hata.append("M1 mutant istisna firlatti: %s" % e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── Y: --durum YETIM siniflamasi gercek zarf uzerinden (uctan uca) ─────────
    tmp_y = tempfile.mkdtemp(prefix="d1-kaynak-sync-yetim-")
    asil = {k: getattr(m, k) for k in ("KAYNAKLAR", "URUNLER", "ds")}
    try:
        sorun = _yetim_vakalari(m.durum, lambda k, v: setattr(m, k, v), tmp_y)
        (hata.append("Y " + sorun) if sorun else gecen.append("Y"))

        # ── M2: SILINMIS'i GERCEK_EKSIK sayan kopya -> Y KIRMIZI yanmali ───────
        ns = _mutant_ns(
            '        sinif["GERCEK_EKSIK" if urun_id in katalog else "SILINMIS"]'
            '.append(urun_id)\n',
            '        sinif["GERCEK_EKSIK"].append(urun_id)\n')
        if ns is None:
            hata.append("M2 MUTANT CAPASI BAYAT (siniflama/yukleyici satiri govdede tek degil)")
        elif _yetim_vakalari(ns["durum"], ns.__setitem__, tmp_y):
            gecen.append("M2")
        else:
            hata.append("M2 SILINMIS->GERCEK_EKSIK mutanti Y vakalarini GECTI (kor test)")
    finally:
        for k, v in asil.items():
            setattr(m, k, v)
        shutil.rmtree(tmp_y, ignore_errors=True)

    z_n = len([g for g in gecen if g in ("Z", "Y")])
    m_n = len([g for g in gecen if g.startswith("M")])
    for h in hata:
        print("KIRMIZI: %s" % h)
    print("KABUL %d/2 MUTANT %d/2" % (z_n, m_n))
    if hata or z_n != 2 or m_n != 2:
        print("HAL=KIRMIZI")
        return 1
    print("HAL=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
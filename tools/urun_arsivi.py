#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urun_arsivi.py — URUN SILME ARSIVI (`arsiv/urunler-arsiv.json`) TEK KAYNAK sekli.

NEDEN (BaBa 20 Eki 13:4x hukmu (1), Okan kurali 6 Eki "sil = TAMAMEN silinir, arsiv YOK"):
repo PUBLIC; eski yazicilar silinen urunun TAM GOVDESINI (`kayit`) arsive yaziyordu —
silinen urun public agacta yasamaya devam ediyordu. Arsiv artik GOVDE TASIMAZ; yalniz
silmenin izini tasir. Govde git gecmisinde zaten vardir (silme commit'inin ebeveyni):

    {"id", "silinme_ts", "silme_commit", "govde_sha256", "yazan", "kuyruk_id"}

  id            silinen urunun id'si
  silinme_ts    UTC damga (yazim ani)
  silme_commit  urunu urunler.json'dan DUSUREN commit (40 hex). Yazim aninda o commit
                HENUZ YOKTUR (kayit o commit'in ICINDE dogar) -> null yazilir ve SONRAKI
                arsiv yaziminda `bekleyenleri_doldur` ile git gecmisinden doldurulur;
                okuyucu (urun-geri-yukle) null'u ayni cozumleyiciyle anlik cozer.
  govde_sha256  sha256(json.dumps(kayit, sort_keys=True, ensure_ascii=False)) — silme
                kapisi (urun-silme-kapisi.py) dusen kaydi bununla eslestirir; geri yukleme
                git'ten aldigi govdeyi bununla DOGRULAR (eslesmezse fail-closed).
  yazan         panel-uygulayici | duzelt.py (gorunur iz; govde degil)
  kuyruk_id     panel kuyruk satiri (gerekce D1'de bu id ile bulunur; panel disi null)

IZINLI_ALANLAR DISINDA alan tasiyan giris (ozellikle eski `kayit`) GOVDELI sayilir ->
silme kapisi KIRMIZI (fail-closed: bilinmeyen alan govde suphesidir).

Tuketiciler: tools/panel-uygulayici.py · tools/duzelt.py · tools/urun-silme-kapisi.py ·
tools/urun-geri-yukle.py · tools/urun-arsiv-govdesiz.py (bir kerelik indirme + dogrulama).
"""
import hashlib
import json
import os
import re
import subprocess
import sys

_BU_DIZIN = os.path.dirname(os.path.realpath(__file__))
for _aday in (os.environ.get("PRUVO_KANONIK_TOOLS") or "", _BU_DIZIN):
    if _aday and os.path.isfile(os.path.join(_aday, "git_ortami.py")):
        if _aday not in sys.path:
            sys.path.insert(0, _aday)
        break
from git_ortami import git_ortami  # noqa: E402

ARSIV_YOLU = "arsiv/urunler-arsiv.json"
KATALOG_YOLU = "urunler.json"
ZORUNLU_ALANLAR = ("id", "silinme_ts", "silme_commit", "govde_sha256")
IZINLI_ALANLAR = frozenset(ZORUNLU_ALANLAR + ("yazan", "kuyruk_id"))
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class ArsivHatasi(Exception):
    pass


def govde_sha256(kayit):
    return hashlib.sha256(json.dumps(kayit, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def giris_yap(kayit, yazan, kuyruk_id, silinme_ts):
    """Silinen kayit icin GOVDESIZ arsiv girisi (yazicilarin TEK yolu)."""
    return {"id": kayit["id"], "silinme_ts": silinme_ts, "silme_commit": None,
            "govde_sha256": govde_sha256(kayit), "yazan": yazan, "kuyruk_id": kuyruk_id}


def giris_id(giris):
    """Girisin urun id'si; eski govdeli sekil (`kayit`) de okunur (gecmis commit'ler)."""
    if not isinstance(giris, dict):
        return None
    if isinstance(giris.get("id"), str):
        return giris["id"]
    kayit = giris.get("kayit")
    if isinstance(kayit, dict) and isinstance(kayit.get("id"), str):
        return kayit["id"]
    return None


def giris_sha(giris):
    """Girisin govde parmak izi; eski govdeli sekilde govdeden HESAPLANIR."""
    if not isinstance(giris, dict):
        return None
    if isinstance(giris.get("govde_sha256"), str):
        return giris["govde_sha256"]
    if isinstance(giris.get("kayit"), dict):
        return govde_sha256(giris["kayit"])
    return None


def sekil_ihlali(giris):
    """Girisin GOVDESIZ sekle aykiriligi (metin) ya da None."""
    if not isinstance(giris, dict):
        return "giris sozluk degil"
    fazla = sorted(set(giris) - IZINLI_ALANLAR)
    if fazla:
        return "izinsiz alan (govde suphesi): %s" % ",".join(fazla)
    eksik = [a for a in ZORUNLU_ALANLAR if a not in giris]
    if eksik:
        return "eksik alan: %s" % ",".join(eksik)
    if not isinstance(giris["id"], str) or not giris["id"]:
        return "id gecersiz"
    if not isinstance(giris["govde_sha256"], str) or not _SHA256.match(giris["govde_sha256"]):
        return "govde_sha256 gecersiz"
    sc = giris["silme_commit"]
    if sc is not None and not (isinstance(sc, str) and _COMMIT.match(sc)):
        return "silme_commit gecersiz"
    return None


def govdeli_girisler(arsiv):
    """[(sira, id, ihlal)] — GOVDESIZ sekle uymayan girisler."""
    return [(i, giris_id(g), sekil_ihlali(g)) for i, g in enumerate(arsiv)
            if sekil_ihlali(g)]


# ── git gecmisinden cozumleme ────────────────────────────────────────────────────

def _git(kok, *args):
    return subprocess.run(["git", "-C", kok] + list(args), capture_output=True,
                          env=git_ortami(), timeout=300)


def _json_at(kok, rev, yol):
    """rev:yol JSON'u; dosya o rev'de YOKSA None. Bozuksa ArsivHatasi."""
    p = _git(kok, "show", "%s:%s" % (rev, yol))
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise ArsivHatasi("%s:%s BOZUK JSON (%s)" % (rev, yol, e))


def _katalog_kaydi(kok, rev, uid):
    for k in _json_at(kok, rev, KATALOG_YOLU) or []:
        if isinstance(k, dict) and k.get("id") == uid:
            return k
    return None


def _ayni_giris(a, b):
    return giris_id(a) == giris_id(b) and a.get("silinme_ts") == b.get("silinme_ts")


def tasiyan_commit(kok, giris):
    """Arsiv girisini (id + silinme_ts) arsive EKLEYEN commit (40 hex) ya da None."""
    ts = giris.get("silinme_ts")
    if not isinstance(ts, str):
        return None
    p = _git(kok, "log", "--format=%H", "--reverse", "-S", '"silinme_ts": "%s"' % ts,
             "--", ARSIV_YOLU)
    if p.returncode != 0:
        return None
    for c in p.stdout.decode().split():
        simdi = _json_at(kok, c, ARSIV_YOLU) or []
        once = _json_at(kok, c + "^", ARSIV_YOLU) or []
        if (any(_ayni_giris(g, giris) for g in simdi if isinstance(g, dict))
                and not any(_ayni_giris(g, giris) for g in once if isinstance(g, dict))):
            return c
    return None


def silme_dogrula(kok, uid, sha, commit):
    """commit urunu dusuren commit mi ve ebeveynindeki govde parmak izine esit mi?
    Doner: ebeveyndeki govde (dict) ya da None."""
    once = _katalog_kaydi(kok, commit + "^", uid)
    if once is None or govde_sha256(once) != sha:
        return None
    if _katalog_kaydi(kok, commit, uid) is not None:
        return None
    return once


def silme_commit_coz(kok, giris):
    """Girisin silme commit'i: dolu ise DOGRULANIR, null ise arsive ekleyen commit'ten
    turetilip DOGRULANIR. Dogrulanamazsa ArsivHatasi (fail-closed)."""
    uid, sha = giris_id(giris), giris_sha(giris)
    aday = giris.get("silme_commit") or tasiyan_commit(kok, giris)
    if not aday:
        raise ArsivHatasi("%s: silme commit'i cozulemedi (girisi tasiyan commit yok)" % uid)
    if silme_dogrula(kok, uid, sha, aday) is None:
        raise ArsivHatasi("%s: %s^:%s govdesi govde_sha256 ile ESLESMEDI ya da commit "
                          "urunu dusurmuyor" % (uid, aday[:12], KATALOG_YOLU))
    return aday


def govde_getir(kok, giris):
    """(govde, silme_commit) — govde `git show <silme_commit>^:urunler.json`dan gelir ve
    govde_sha256 ile dogrulanir. Aksi ArsivHatasi."""
    c = silme_commit_coz(kok, giris)
    return _katalog_kaydi(kok, c + "^", giris_id(giris)), c


def bekleyenleri_doldur(kok, arsiv):
    """silme_commit'i null olan girisleri git gecmisinden doldurur (yerinde). Cozulemeyen
    (henuz commit'lenmemis) giris null KALIR. Doner: doldurulan sayisi."""
    n = 0
    for g in arsiv:
        if isinstance(g, dict) and "kayit" not in g and g.get("silme_commit") is None:
            try:
                g["silme_commit"] = silme_commit_coz(kok, g)
                n += 1
            except ArsivHatasi:
                pass
    return n

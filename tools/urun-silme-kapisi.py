#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urun-silme-kapisi.py — URUN SILME SINIF KAPISI: izinsiz id kumesi KUCULMESI = KIRMIZI.

🔴 DOKTRIN (Okan hukmu, 17 Agu 2026): "SAKIN siteden bir urun SILME." Yayindan dusurmenin
TEK mesru yolu `gizli:true`dir (kayit tabanda KALIR):
    python3 tools/duzelt.py <id> --alan gizli --deger true

NEDEN VAR (13 Eyl 2026, olculdu — 3. tekrarin OTESI, tekil yama YASAK):
  `urunler.json` id kumesini KUCULTEN commit'ler HICBIR kapi yakmadan main'e girdi:
    8759f3e2 (26 Agu) `duzelt.py --sil` ile 3 kayit — onarilabilir fiyat/ifsa ihlali icin
    db33e358 (26 Agu) otosil kolu 1 kayit sildi (4 dk sonra elle geri alindi)
    aea5ccac (8 Eyl)  2 vape-tutucu kaydi "politika" gerekcesiyle sildi (yol `gizli:true` idi)
  Mekanizma: `tools/urunler-guard.py` izinsiz silmeyi geri ekler AMA izin manifesti
  (`.urunler-sil-izin.json`) `duzelt.py --sil GEREKCE` ile SARTSIZ yaziliyordu — gerekce
  yalniz bir log metniydi. Yani koruma katmani vardi, TUTAN EL yoktu.

IDDIA: <taban> -> <yeni> arasinda katalogdan DUSEN her id su iki izinden BIRINI tasir:
  (1) ID-RENAME — dusen kayit, yeni eklenen bir kaydin `id` DISINDA birebir aynisidir
      (`duzelt.py --yeni-id` ve guard'in `_id_rename_haritasi` ile AYNI olcut).
  (2) ARSIV — `arsiv/urunler-arsiv.json`da `kayit.id == <id>` giris SAYISI yenide
      tabandakinden BUYUKTUR (kayit ayni aralikta arsive TASINDI). Bu, Okan'in 2 Eyl
      panel yolunun (`tools/urun-silme-yordami.md`, "Sil (arsive)") ve izinli
      `PRUVO_URUN_SIL_IZNI=OKAN python3 tools/duzelt.py <id> --sil` kolunun biraktigi
      KALICI kanittir. Yeni sozluk DEGIL: arsiv duzlemi zaten vardi.
  Aksi -> IZINSIZ_SILME -> KIRMIZI (rc 1).
  * YENI id eklemek, bir alani degistirmek, `gizli:true` yapmak -> kapiyi HIC tetiklemez.
  * ESKI arsiv girisi YETMEZ: geri yuklenmis (`urun-geri-yukle.py`) bir kaydin arsivde
    eski girisi DURUR; ikinci silme ancak YENI giris ile mesrudur (sayac, varlik degil).
  * MERGE (index kipinde MERGE_HEAD varsa): taban = TUM ebeveynlerde bulunan id'ler.
    Bir ebeveynde zaten olmayan id'nin yoklugu o ebeveynin halidir (guard ILKE 1).

KIPLER (hepsi SALT OKUR; hicbir dosyaya yazmaz):
  (varsayilan) CI KOLU  — taban = `PRUVO_CI_ONCEKI_SHA` ya da GitHub push olayinin
                          `before`i; yeni = `GITHUB_SHA`. Ikisi yoksa / sifir SHA ise
                          HEAD^1 -> HEAD (workflow_dispatch). Taban commit'i yerelde
                          YOKSA OLCULEMEDI (rc 2) — "olcemedim" yesil sayilmaz.
  --index               — HEAD -> INDEX (pre-commit adim 9). urunler.json index'te HEAD'e
                          esitse tarama KOSMAZ ve nedeni BASILIR (sessiz atlama yok).
  --taban X --yeni Y    — acik aralik (fikstur / elle olcum).

📌 BEYAN EDILEN SINIR — CI KOLU "TEK ATIMLIK"tir (diriltme-kapisi EKSEN 1 ile ayni sinif):
  izinsiz silme bir push'ta KIRMIZI yanar ve o push'un deploy'unu durdurur; bir SONRAKI
  push'un araligi o commit'i icermez. CARE yazim oncesi koldadir: pre-commit adim 9
  ihlali COMMIT ANINDA durdurur. Kancasiz/`--no-verify` yol icin CI kolu tek atim KALIR.

Cikis: 0 YESIL · 1 KIRMIZI (izinsiz silme) · 2 OLCULEMEDI (bozuk JSON, cozulemeyen ref).
Kabul + mutantlar: tools/urun-silme-kapisi-test.py
"""
import argparse
import json
import os
import subprocess
import sys

KATALOG_YOLU = "urunler.json"
# TEK KAYNAK ile ayni yol: tools/panel-uygulayici.py::ARSIV_DOSYASI (test IKIZ-TANIM vakasi olcer)
ARSIV_YOLU = "arsiv/urunler-arsiv.json"
# TEK KAYNAK ile ayni ad/deger: tools/duzelt.py::SIL_IZIN_ENV / SIL_IZIN_DEGERI (test olcer)
SIL_IZIN_ENV = "PRUVO_URUN_SIL_IZNI"
SIL_IZIN_DEGERI = "OKAN"
SIFIR_SHA = "0" * 40
ORNEK_TAVAN = 40

YESIL, KIRMIZI, OLCULEMEDI = 0, 1, 2


class Olculemedi(Exception):
    pass


def _temiz_env(index_kipi):
    """Hook icinde git GIT_DIR/GIT_INDEX_FILE koyar. INDEX kipi commit edilen index'i
    OKUMAK ZORUNDA (GIT_INDEX_FILE miras kalir, `-C` kullanilmaz); diger kipler acik
    `-C <depo>` ile kosar ve bu degiskenler ayrismaya yol acmasin diye DUSURULUR."""
    env = os.environ.copy()
    if not index_kipi:
        for ad in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            env.pop(ad, None)
    return env


def _git(depo, args, index_kipi=False):
    komut = ["git"] + ([] if index_kipi else ["-C", depo]) + list(args)
    p = subprocess.run(komut, capture_output=True, env=_temiz_env(index_kipi),
                       cwd=depo if index_kipi else None, timeout=300)
    return p.returncode, p.stdout, p.stderr


def _dosya_oku(depo, ref, yol, index_kipi=False):
    """ref:yol icerigi (bytes) ya da dosya o ref'te YOKSA None. ref '' -> INDEX."""
    nesne = (":" + yol) if ref == "" else ("%s:%s" % (ref, yol))
    rc, _, _ = _git(depo, ["cat-file", "-e", nesne], index_kipi)
    if rc != 0:
        return None
    rc, out, err = _git(depo, ["show", nesne], index_kipi)
    if rc != 0:
        raise Olculemedi("git show %s basarisiz: %s" % (nesne, err.decode("utf-8", "replace").strip()))
    return out


def _json(bayt, etiket):
    try:
        return json.loads(bayt.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise Olculemedi("%s BOZUK JSON (%s)" % (etiket, e))


def katalog_oku(depo, ref, index_kipi=False):
    """[kayit] ; dosya YOKSA []. Kok dizi degilse OLCULEMEDI."""
    bayt = _dosya_oku(depo, ref, KATALOG_YOLU, index_kipi)
    if bayt is None:
        return []
    veri = _json(bayt, "%s:%s" % (ref or "INDEX", KATALOG_YOLU))
    if not isinstance(veri, list):
        raise Olculemedi("%s:%s kok DIZI DEGIL" % (ref or "INDEX", KATALOG_YOLU))
    return veri


def arsiv_sayaci(depo, ref, index_kipi=False):
    """{id: arsivdeki giris sayisi} ; arsiv dosyasi YOKSA {}."""
    bayt = _dosya_oku(depo, ref, ARSIV_YOLU, index_kipi)
    if bayt is None:
        return {}
    veri = _json(bayt, "%s:%s" % (ref or "INDEX", ARSIV_YOLU))
    if not isinstance(veri, list):
        raise Olculemedi("%s:%s kok DIZI DEGIL" % (ref or "INDEX", ARSIV_YOLU))
    sayac = {}
    for giris in veri:
        kayit = giris.get("kayit") if isinstance(giris, dict) else None
        uid = kayit.get("id") if isinstance(kayit, dict) else None
        if isinstance(uid, str):
            sayac[uid] = sayac.get(uid, 0) + 1
    return sayac


def _id_haritasi(liste):
    h = {}
    for k in liste:
        if isinstance(k, dict) and isinstance(k.get("id"), str):
            h.setdefault(k["id"], k)
    return h


def _kanon_idsiz(kayit):
    k = {a: v for a, v in kayit.items() if a != "id"}
    return json.dumps(k, sort_keys=True, ensure_ascii=False)


def degerlendir(taban, yeni, taban_arsiv, yeni_arsiv, ek_ebeveynler=()):
    """SAF hukum (git'e dokunmaz). Doner: dict(dusen, rename, arsivli, izinsiz)."""
    taban_h = _id_haritasi(taban)
    yeni_h = _id_haritasi(yeni)
    taban_idleri = set(taban_h)
    butun_ebeveyn_idleri = set(taban_h)
    for eb in ek_ebeveynler:
        eb_idleri = set(_id_haritasi(eb))
        taban_idleri &= eb_idleri
        butun_ebeveyn_idleri |= eb_idleri
    dusen = taban_idleri - set(yeni_h)

    eklenen_anahtar = {}
    for uid in sorted(set(yeni_h) - butun_ebeveyn_idleri):
        eklenen_anahtar.setdefault(_kanon_idsiz(yeni_h[uid]), []).append(uid)

    rename, arsivli, izinsiz = [], [], []
    for uid in sorted(dusen):
        anahtar = _kanon_idsiz(taban_h[uid])
        adaylar = eklenen_anahtar.get(anahtar)
        if adaylar:
            rename.append((uid, adaylar.pop(0)))
            continue
        if yeni_arsiv.get(uid, 0) > taban_arsiv.get(uid, 0):
            arsivli.append(uid)
            continue
        izinsiz.append(uid)
    return {"dusen": sorted(dusen), "rename": rename, "arsivli": arsivli, "izinsiz": izinsiz}


def _commit_var(depo, sha):
    rc, _, _ = _git(depo, ["cat-file", "-e", sha + "^{commit}"])
    return rc == 0


def ci_araligi(depo):
    onceki = os.environ.get("PRUVO_CI_ONCEKI_SHA", "").strip()
    hedef = os.environ.get("GITHUB_SHA", "").strip()
    olay = os.environ.get("GITHUB_EVENT_PATH", "").strip()
    if not onceki and olay:
        try:
            with open(olay, encoding="utf-8") as f:
                onceki = str(json.load(f).get("before") or "").strip()
        except (OSError, ValueError, TypeError, AttributeError) as e:
            raise Olculemedi("GitHub olayinin before SHA'si okunamadi: %s" % e)
    if onceki and onceki != SIFIR_SHA:
        hedef = hedef or "HEAD"
        if not _commit_var(depo, onceki):
            raise Olculemedi("taban commit'i yerelde YOK: %s (fetch-depth: 0 mi?)" % onceki)
        return onceki, hedef, "CI(before)"
    if not _commit_var(depo, "HEAD^1"):
        raise Olculemedi("HEAD^1 YOK (shallow ya da ilk commit) — aralik cozulemedi")
    return "HEAD^1", hedef or "HEAD", "CI(HEAD^1)"


def _depo_bul(verilen):
    if verilen:
        return os.path.abspath(verilen)
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip()
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rapor(eksen, taban_ad, yeni_ad, sonuc):
    print("URUN_SILME_KAPISI: eksen=%s taban=%s yeni=%s DUSEN=%d RENAME=%d ARSIVLI=%d IZINSIZ=%d"
          % (eksen, taban_ad, yeni_ad, len(sonuc["dusen"]), len(sonuc["rename"]),
             len(sonuc["arsivli"]), len(sonuc["izinsiz"])))
    for eski, yeni in sonuc["rename"][:ORNEK_TAVAN]:
        print("  RENAME %s -> %s" % (eski, yeni))
    for uid in sonuc["arsivli"][:ORNEK_TAVAN]:
        print("  ARSIVLI_SILME %s" % uid)
    for uid in sonuc["izinsiz"][:ORNEK_TAVAN]:
        print("  IZINSIZ_SILME %s" % uid)
    if len(sonuc["izinsiz"]) > ORNEK_TAVAN:
        print("  ... +%d izinsiz silme daha" % (len(sonuc["izinsiz"]) - ORNEK_TAVAN))
    if sonuc["izinsiz"]:
        print("HUKUM: KIRMIZI — katalogdan izinsiz %d urun SILINDI (Okan hukmu 17 Agu: "
              "urun SILINMEZ)." % len(sonuc["izinsiz"]))
        print("CARE (yayindan dusurmek): kaydi GERI KOY ve gizle -> "
              "python3 tools/duzelt.py <id> --alan gizli --deger true")
        print("IZINLI SILME (yalniz Okan karari): %s=%s python3 tools/duzelt.py <id> --sil "
              "\"<gerekce>\" — kayit %s'a TASINIR; ayni commit'e `git add %s %s`."
              % (SIL_IZIN_ENV, SIL_IZIN_DEGERI, ARSIV_YOLU, KATALOG_YOLU, ARSIV_YOLU))
        return KIRMIZI
    print("HUKUM: YESIL")
    return YESIL


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--depo", help="depo koku (varsayilan: cwd'nin git koku)")
    ap.add_argument("--index", action="store_true", help="HEAD -> INDEX (pre-commit kolu)")
    ap.add_argument("--taban", help="acik aralik: onceki revizyon")
    ap.add_argument("--yeni", help="acik aralik: yeni revizyon (varsayilan HEAD)")
    args = ap.parse_args(argv)
    depo = _depo_bul(args.depo)
    try:
        if args.index:
            if args.taban or args.yeni:
                print("URUN_SILME_KAPISI: HATA --index, --taban/--yeni ile birlikte verilmez")
                return OLCULEMEDI
            rc, _, _ = _git(depo, ["rev-parse", "--verify", "--quiet", "HEAD"], True)
            if rc != 0:
                print("URUN_SILME_KAPISI: ATLANDI — HEAD YOK (ilk commit), karsilastirilacak taban yok.")
                return YESIL
            rc, _, _ = _git(depo, ["diff", "--cached", "--quiet", "HEAD", "--", KATALOG_YOLU], True)
            if rc == 0:
                print("URUN_SILME_KAPISI: ATLANDI — %s index'te HEAD'e gore DEGISMEDI (on-eleme)."
                      % KATALOG_YOLU)
                return YESIL
            if rc != 1:
                raise Olculemedi("git diff --cached HEAD rc=%d — on-eleme olculemedi" % rc)
            ek = []
            rc, out, _ = _git(depo, ["rev-parse", "--verify", "--quiet", "MERGE_HEAD"], True)
            if rc == 0 and out.strip():
                ek.append(katalog_oku(depo, "MERGE_HEAD", True))
            sonuc = degerlendir(katalog_oku(depo, "HEAD", True), katalog_oku(depo, "", True),
                                arsiv_sayaci(depo, "HEAD", True), arsiv_sayaci(depo, "", True), ek)
            return _rapor("INDEX" + ("+MERGE_HEAD" if ek else ""), "HEAD", "INDEX", sonuc)
        if args.taban:
            taban, yeni, eksen = args.taban, args.yeni or "HEAD", "ARALIK"
        elif args.yeni:
            print("URUN_SILME_KAPISI: HATA --yeni tek basina verilmez (--taban gerekli)")
            return OLCULEMEDI
        else:
            taban, yeni, eksen = ci_araligi(depo)
        for ref in (taban, yeni):
            if not _commit_var(depo, ref):
                raise Olculemedi("revizyon cozulemedi: %s" % ref)
        sonuc = degerlendir(katalog_oku(depo, taban), katalog_oku(depo, yeni),
                            arsiv_sayaci(depo, taban), arsiv_sayaci(depo, yeni))
        return _rapor(eksen, taban, yeni, sonuc)
    except Olculemedi as e:
        print("URUN_SILME_KAPISI: OLCULEMEDI — %s" % e)
        print("HUKUM: OLCULEMEDI (rc 2) — olculemeyen sey YESIL sayilmaz.")
        return OLCULEMEDI


if __name__ == "__main__":
    sys.exit(main())

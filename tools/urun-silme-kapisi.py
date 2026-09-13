#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""urun-silme-kapisi.py — URUN SILME SINIF KAPISI: izinsiz id kumesi KUCULMESI = KIRMIZI.

🔴 DOKTRIN (Okan hukmu, 17 Agu 2026): "SAKIN siteden bir urun SILME." Yayindan dusurmenin
TEK mesru yolu `gizli:true`dir (kayit tabanda KALIR):
    python3 tools/duzelt.py <id> --alan gizli --deger true

NEDEN VAR (13 Eyl 2026, olculdu — 3. tekrarin OTESI, tekil yama YASAK):
  14 Agu -> 13 Eyl arasinda `urunler.json` id kumesini KUCULTEN 31 commit'in 22'si (54 kayit)
  izinsizdi ve HICBIR kapi yanmadi: 8759f3e2 (`duzelt.py --sil`, onarilabilir fiyat/ifsa
  ihlali icin 3 kayit) · db33e358 (otosil kolu) · aea5ccac (2 kayit, yol `gizli:true` idi).
  Mekanizma: `tools/urunler-guard.py` izinsiz silmeyi geri ekler AMA izin manifesti
  (`.urunler-sil-izin.json`) `duzelt.py --sil GEREKCE` ile SARTSIZ yaziliyordu.

IDDIA: <taban> -> <yeni> arasinda katalogdan DUSEN her id su izinlerden BIRINI tasir:
  (1) ID-RENAME — dusen kayit, yeni eklenen bir kaydin `id` DISINDA birebir aynisidir
      (`duzelt.py --yeni-id` ve guard'in `_id_rename_haritasi` ile AYNI olcut).
  (2) ARSIV — `arsiv/urunler-arsiv.json`da, dusen kaydin TAM iceriginin BIREBIR aynisini
      tasiyan giris SAYISI yenide tabandakinden BUYUKTUR (kayit ayni aralikta arsive
      TASINDI). Yalniz id tasiyan / icerigi farkli giris izin SAYILMAZ: kaydin kendisi
      kaybolmamali (curutucu B2, 13 Eyl). Kaynak: Okan'in 2 Eyl panel yolu
      (`tools/urun-silme-yordami.md`, "Sil (arsive)") ve izinli `duzelt.py --sil`.
  (3) MERGE GETIRISI (yalniz --index + MERGE_HEAD): id ORTAK ATADA vardi ve ebeveynlerden
      BIRI onu silmisti. Bir tarafin YENI EKLEDIGI (atada olmayan) id'nin sonucta yoklugu
      KAYIPTIR -> KIRMIZI (curutucu B3: `checkout --theirs` cozumu yeni kaydi yutuyordu).
  Aksi -> IZINSIZ_SILME -> KIRMIZI (rc 1). Yeni id eklemek, alan degistirmek, `gizli:true`
  yapmak kapiyi HIC tetiklemez. ESKI arsiv girisi YETMEZ (sayac artmali).

KIPLER (hepsi SALT OKUR):
  (varsayilan) CI KOLU  — yeni = `GITHUB_SHA` (yoksa HEAD). Taban = son PENCERE (20)
                          first-parent commit'in tabani; GitHub olayinin `before`i daha
                          ESKIYSE o. `PRUVO_CI_ONCEKI_SHA` verilirse AYNEN kullanilir.
                          Araliktaki (dal commit'leri dahil) katalog degistiren HER commit
                          KENDI ebeveynine gore hukum alir (merge: ortak ataya gore); uc
                          nokta karsilastirmasi rename/arsiv sonrasi duzenlemeyi sahte
                          KIRMIZI yakiyordu (curutucu N1, gercekte 3 olay / 9 konum).
                          NEDEN PENCERE (curutucu SUPHE, 13 Eyl): deploy.yml kuyrugunda
                          bekleyen koşum iptal edilince bir sonraki koşumun `before`i
                          silmeyi ATLAR; `before..after` kolu SIFIR atima inerdi. Pencere
                          uc noktalari karsilastirir: izinsiz silme 20 commit boyunca her
                          push'ta KIRMIZI kalir, kayit GERI KONUNCA kendiliginden YESIL olur.
  --index               — HEAD -> INDEX (pre-commit adim 9). urunler.json index'te HEAD'e
                          esitse tarama KOSMAZ ve nedeni BASILIR.
  --taban X --yeni Y    — acik aralik (fikstur / elle olcum).

📌 BEYAN EDILEN SINIRLAR (curutucu raporu 13 Eyl; hepsi olculdu, gizlenmez):
  * IZIN YEREL OLARAK SAHTELENEBILIR (B1): `duzelt.py` silme iznini ortamdan okur; bir ajan
    onu kendine verebilir. Bu kapi KAZAYI ve REFLEKSI (kapiyi yesile cevirmek icin katalog
    budamak) durdurur; kotu niyeti degil. Izinli silme GORUNUR iz birakir: arsiv girisi
    (`yazan`) + CI ciktisinda ARSIVLI_SILME satiri + yerel guard logu. Kirmizi cikti izin
    reçetesini BASMAZ; care yalniz `gizli:true`dir.
  * `git cherry-pick` / catismasiz `git merge` pre-commit KOSTURMAZ (B4) -> o yollarda
    yalniz CI penceresi kalir.
  * `git commit --amend` ile ayni commit'te eklenip cikarilan kayit SAHTE KIRMIZI olabilir
    (B5; taban amend edilen commit). Care: `git reset --soft HEAD^` + yeniden commit.
  * Ayni id'li mukerrer kayit / id'siz kayit silmesi olculmez (B6; HEAD'de 0 vaka).
  * AYNI commit'te duzenlenip arsivle silinen kayit SAHTE KIRMIZI olur (N3; arsiv icerigi
    HEAD'deki eski halle eslesmez). Care: duzenlemeyi once ayri commit'le.

Cikis: 0 YESIL · 1 KIRMIZI (izinsiz silme) · 2 OLCULEMEDI (bozuk JSON, cozulemeyen ref).
Kabul + mutantlar: tools/urun-silme-kapisi-test.py
"""
import argparse
import json
import os
import subprocess
import sys

# TEK KAYNAK: git ortami SCRUB politikasi `tools/git_ortami.py::GIT_BAGLAM_DEGISKENLERI`.
# Burada elle bir kume YAZILMAZ (ikiz-tanim ayrismasin diye); sadece hangi adlarin
# KORUNACAGI cagri yerinde ilan edilir. Mutasyon turu bu dosyanin KOPYASINI gecici
# bir dizine yazar; kopya kanonik `tools/`e bakan `TOOLS_DIZINI`ni tasir.
TOOLS_DIZINI = os.path.dirname(os.path.realpath(__file__))
for _aday in (os.environ.get("PRUVO_KANONIK_TOOLS") or "", TOOLS_DIZINI,
              os.path.join("/Users/okan/dev/pruvo", "tools")):
    if _aday and os.path.isfile(os.path.join(_aday, "git_ortami.py")):
        sys.path.insert(0, _aday)
        break
from git_ortami import git_ortami  # noqa: E402

KATALOG_YOLU = "urunler.json"
# TEK KAYNAK ile ayni yol: tools/panel-uygulayici.py::ARSIV_DOSYASI (test IKIZ-TANIM vakasi olcer)
ARSIV_YOLU = "arsiv/urunler-arsiv.json"
# TEK KAYNAK ile ayni ad/deger: tools/duzelt.py::SIL_IZIN_ENV / SIL_IZIN_DEGERI (test olcer)
SIL_IZIN_ENV = "PRUVO_URUN_SIL_IZNI"
SIL_IZIN_DEGERI = "OKAN"
SIFIR_SHA = "0" * 40
PENCERE = 20
ORNEK_TAVAN = 40

YESIL, KIRMIZI, OLCULEMEDI = 0, 1, 2


class Olculemedi(Exception):
    pass


def _temiz_env(index_kipi):
    """Hook icinde git GIT_DIR/GIT_INDEX_FILE koyar. INDEX kipi commit edilen index'i
    OKUMAK ZORUNDA (GIT_DIR + GIT_INDEX_FILE miras kalir, `-C` kullanilmaz); diger
    kipler acik `-C <depo>` ile kosar ve bu degiskenler ayrismaya yol acmasin diye
    DUSURULUR. Tum kararlar `tools/git_ortami.GIT_BAGLAM_DEGISKENLERI` TEK KAYNAK'tan
    turer — burada elle bir alt kume YAZILMAZ (ikiz-tanim ayrisirdi)."""
    if index_kipi:
        return git_ortami(korunan_baglam=("GIT_DIR", "GIT_INDEX_FILE"))
    return git_ortami()


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


def _kanon_idsiz(kayit):
    k = {a: v for a, v in kayit.items() if a != "id"}
    return json.dumps(k, sort_keys=True, ensure_ascii=False)


def _arsiv_anahtari(kayit):
    """Arsiv girisi silinen kaydin TAM icerigini tasimali (id dahil)."""
    return json.dumps(kayit, sort_keys=True, ensure_ascii=False)


def arsiv_sayaci(depo, ref, index_kipi=False):
    """{id: {tam_icerik_anahtari: [yazan, ...]}} ; arsiv dosyasi YOKSA {}."""
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
            yazan = giris.get("yazan") if isinstance(giris.get("yazan"), str) else "?"
            sayac.setdefault(uid, {}).setdefault(_arsiv_anahtari(kayit), []).append(yazan)
    return sayac


def _id_haritasi(liste):
    h = {}
    for k in liste:
        if isinstance(k, dict) and isinstance(k.get("id"), str):
            h.setdefault(k["id"], k)
    return h


def degerlendir(taban, yeni, taban_arsiv, yeni_arsiv, ek_ebeveynler=(), ortak_ata=None):
    """SAF hukum (git'e dokunmaz). taban = ilk ebeveyn; ek_ebeveynler = MERGE_HEAD;
    ortak_ata = merge-base katalogu. Doner: dict(dusen, rename, arsivli, merge, izinsiz)."""
    ebeveynler = [_id_haritasi(taban)] + [_id_haritasi(e) for e in ek_ebeveynler]
    yeni_h = _id_haritasi(yeni)
    kayit_h = {}
    for eb in reversed(ebeveynler):
        kayit_h.update(eb)                    # ayni id'de ilk ebeveynin kaydi kazanir
    ata_idleri = set(_id_haritasi(ortak_ata)) if ortak_ata is not None else set()
    merge_getirisi, dusen = [], []
    for uid in sorted(set(kayit_h) - set(yeni_h)):
        if (len(ebeveynler) > 1 and uid in ata_idleri
                and any(uid not in eb for eb in ebeveynler)):
            merge_getirisi.append(uid)        # atada vardi, bir ebeveyn sildi
            continue
        dusen.append(uid)

    eklenen_anahtar = {}
    for uid in sorted(set(yeni_h) - set(kayit_h)):
        eklenen_anahtar.setdefault(_kanon_idsiz(yeni_h[uid]), []).append(uid)

    rename, arsivli, izinsiz = [], [], []
    for uid in dusen:
        adaylar = eklenen_anahtar.get(_kanon_idsiz(kayit_h[uid]))
        if adaylar:
            rename.append((uid, adaylar.pop(0)))
            continue
        anahtar = _arsiv_anahtari(kayit_h[uid])
        yeni_g = yeni_arsiv.get(uid, {}).get(anahtar, [])
        if len(yeni_g) > len(taban_arsiv.get(uid, {}).get(anahtar, [])):
            arsivli.append((uid, yeni_g[-1]))
            continue
        izinsiz.append(uid)
    return {"dusen": dusen, "rename": rename, "arsivli": arsivli,
            "merge": merge_getirisi, "izinsiz": izinsiz}


def uc_nokta_hukmu(depo, taban, yeni):
    """Iki uc noktayi karsilastir (acik --taban/--yeni kipi)."""
    return degerlendir(katalog_oku(depo, taban), katalog_oku(depo, yeni),
                       arsiv_sayaci(depo, taban), arsiv_sayaci(depo, yeni))


def pencere_hukmu(depo, taban, yeni):
    """CI kolu: taban..yeni icindeki (dal commit'leri DAHIL) urunler.json'a dokunan HER
    commit KENDI ebeveynine gore hukum alir; merge commit'i ortak ataya gore.
    NEDEN (curutucu N1, 13 Eyl): uc nokta karsilastirmasi rename/arsiv kanitini ara
    commit'te birakip sonradan duzenlenen kaydi IZINSIZ sayiyordu (gercek gecmiste 3 olay /
    9 pencere konumu SAHTE KIRMIZI). Izinsiz silinen id pencere sonunda katalogda VARSA
    (geri konulmus) AFFEDILIR -> kirmizi ONARILABILIR kalir."""
    rc, out, err = _git(depo, ["rev-list", "--reverse", "--parents", "%s..%s" % (taban, yeni)])
    if rc != 0:
        raise Olculemedi("rev-list %s..%s: %s" % (taban, yeni, err.decode("utf-8", "replace").strip()))
    onbellek = {}

    def oku(sha):
        if sha not in onbellek:
            if len(onbellek) >= 4:
                onbellek.pop(next(iter(onbellek)))
            onbellek[sha] = (katalog_oku(depo, sha), arsiv_sayaci(depo, sha))
        return onbellek[sha]

    toplam = {"dusen": [], "rename": [], "arsivli": [], "merge": [], "izinsiz": [], "kaynak": {}}
    incelenen = 0
    for satir in out.decode("utf-8", "replace").splitlines():
        parcalar = satir.split()
        if len(parcalar) < 2:
            continue
        c, ebeveynler = parcalar[0], parcalar[1:]
        dokundu = False
        for p in ebeveynler:
            rcd, _, _ = _git(depo, ["diff", "--quiet", p, c, "--", KATALOG_YOLU])
            if rcd not in (0, 1):
                raise Olculemedi("git diff %s %s rc=%d" % (p, c, rcd))
            dokundu = dokundu or rcd == 1
        if not dokundu:
            continue
        incelenen += 1
        p_kat, p_ars = oku(ebeveynler[0])
        c_kat, c_ars = oku(c)
        if len(ebeveynler) == 1:
            s = degerlendir(p_kat, c_kat, p_ars, c_ars)
        else:
            rcm, ata, errm = _git(depo, ["merge-base", ebeveynler[0], ebeveynler[1]])
            if rcm != 0 or not ata.strip():
                raise Olculemedi("merge-base %s: %s" % (c, errm.decode("utf-8", "replace").strip()))
            s = degerlendir(p_kat, c_kat, p_ars, c_ars,
                            [katalog_oku(depo, p) for p in ebeveynler[1:]],
                            katalog_oku(depo, ata.decode().strip()))
        for anahtar in ("dusen", "rename", "arsivli", "merge"):
            toplam[anahtar].extend(s[anahtar])
        for uid in s["izinsiz"]:
            if uid not in toplam["kaynak"]:
                toplam["izinsiz"].append(uid)
            toplam["kaynak"][uid] = c[:8]
    son_idleri = set(_id_haritasi(katalog_oku(depo, yeni)))
    toplam["affedilen"] = [u for u in toplam["izinsiz"] if u in son_idleri]
    toplam["izinsiz"] = [u for u in toplam["izinsiz"] if u not in son_idleri]
    toplam["incelenen"] = incelenen
    return toplam


def _commit_var(depo, sha):
    rc, _, _ = _git(depo, ["cat-file", "-e", sha + "^{commit}"])
    return rc == 0


def _ata_mi(depo, eski, yeni):
    rc, _, _ = _git(depo, ["merge-base", "--is-ancestor", eski, yeni])
    return rc == 0


def pencere_tabani(depo, hedef):
    """hedef'ten geriye PENCERE first-parent commit; zincir kisaysa kok commit."""
    rc, out, err = _git(depo, ["rev-list", "--first-parent", "--max-count=%d" % (PENCERE + 1), hedef])
    satirlar = out.decode("utf-8", "replace").split()
    if rc != 0 or not satirlar:
        raise Olculemedi("pencere tabani cozulemedi (%s): %s"
                         % (hedef, err.decode("utf-8", "replace").strip()))
    return satirlar[-1]


def ci_araligi(depo):
    acik = os.environ.get("PRUVO_CI_ONCEKI_SHA", "").strip()
    hedef = os.environ.get("GITHUB_SHA", "").strip() or "HEAD"
    if not _commit_var(depo, hedef):
        raise Olculemedi("hedef commit cozulemedi: %s" % hedef)
    if acik:
        if not _commit_var(depo, acik):
            raise Olculemedi("PRUVO_CI_ONCEKI_SHA yerelde YOK: %s" % acik)
        return acik, hedef, "CI(acik)"
    before = ""
    olay = os.environ.get("GITHUB_EVENT_PATH", "").strip()
    if olay:
        try:
            with open(olay, encoding="utf-8") as f:
                before = str(json.load(f).get("before") or "").strip()
        except (OSError, ValueError, TypeError, AttributeError) as e:
            raise Olculemedi("GitHub olayinin before SHA'si okunamadi: %s" % e)
    pencere = pencere_tabani(depo, hedef)
    if (before and before != SIFIR_SHA and _commit_var(depo, before)
            and _ata_mi(depo, before, hedef) and _ata_mi(depo, before, pencere)):
        return before, hedef, "CI(before)"
    return pencere, hedef, "CI(pencere-%d)" % PENCERE


def _depo_bul(verilen):
    if verilen:
        return os.path.abspath(verilen)
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if p.returncode == 0 and p.stdout.strip():
        return p.stdout.strip()
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rapor(eksen, taban_ad, yeni_ad, sonuc):
    print("URUN_SILME_KAPISI: eksen=%s taban=%s yeni=%s DUSEN=%d RENAME=%d ARSIVLI=%d "
          "MERGE_GETIRISI=%d IZINSIZ=%d"
          % (eksen, taban_ad, yeni_ad, len(sonuc["dusen"]), len(sonuc["rename"]),
             len(sonuc["arsivli"]), len(sonuc["merge"]), len(sonuc["izinsiz"])))
    for eski, yeni in sonuc["rename"][:ORNEK_TAVAN]:
        print("  RENAME %s -> %s" % (eski, yeni))
    for uid, yazan in sonuc["arsivli"][:ORNEK_TAVAN]:
        print("  ARSIVLI_SILME %s (yazan=%s)" % (uid, yazan))
    for uid in sonuc["merge"][:ORNEK_TAVAN]:
        print("  MERGE_GETIRISI %s" % uid)
    if "incelenen" in sonuc:
        print("  PENCERE: incelenen commit=%d AFFEDILEN(geri konulan)=%d"
              % (sonuc["incelenen"], len(sonuc["affedilen"])))
    for uid in sonuc["izinsiz"][:ORNEK_TAVAN]:
        kaynak = sonuc.get("kaynak", {}).get(uid)
        print("  IZINSIZ_SILME %s%s" % (uid, (" (commit %s)" % kaynak) if kaynak else ""))
    if len(sonuc["izinsiz"]) > ORNEK_TAVAN:
        print("  ... +%d izinsiz silme daha" % (len(sonuc["izinsiz"]) - ORNEK_TAVAN))
    if sonuc["izinsiz"]:
        print("HUKUM: KIRMIZI — katalogdan izinsiz %d urun SILINDI (Okan hukmu 17 Agu: "
              "urun SILINMEZ)." % len(sonuc["izinsiz"]))
        print("CARE: kaydi GERI KOY ve gizle -> "
              "python3 tools/duzelt.py <id> --alan gizli --deger true")
        print("Silme yalniz Okan'in acik karariyla yapilir (yordam: tools/urun-silme-yordami.md).")
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
            rc, out, _ = _git(depo, ["rev-parse", "--verify", "--quiet", "MERGE_HEAD"], True)
            merge_var = bool(rc == 0 and out.strip())
            # MERGE'DE ON-ELEME YOK (curutucu N2): `checkout --ours` cozumu index'i HEAD'e
            # esitler ama dalin YENI ekledigi kaydi yutar; HEAD'e gore on-eleme onu gormezdi.
            rc, _, _ = _git(depo, ["diff", "--cached", "--quiet", "HEAD", "--", KATALOG_YOLU], True)
            if rc == 0 and not merge_var:
                print("URUN_SILME_KAPISI: ATLANDI — %s index'te HEAD'e gore DEGISMEDI (on-eleme)."
                      % KATALOG_YOLU)
                return YESIL
            if rc not in (0, 1):
                raise Olculemedi("git diff --cached HEAD rc=%d — on-eleme olculemedi" % rc)
            ek, ata = [], None
            if merge_var:
                ek.append(katalog_oku(depo, "MERGE_HEAD", True))
                rc, taban_sha, err = _git(depo, ["merge-base", "HEAD", "MERGE_HEAD"], True)
                if rc != 0 or not taban_sha.strip():
                    raise Olculemedi("merge-base HEAD MERGE_HEAD cozulemedi: %s"
                                     % err.decode("utf-8", "replace").strip())
                ata = katalog_oku(depo, taban_sha.decode().strip(), True)
            sonuc = degerlendir(katalog_oku(depo, "HEAD", True), katalog_oku(depo, "", True),
                                arsiv_sayaci(depo, "HEAD", True), arsiv_sayaci(depo, "", True),
                                ek, ata)
            return _rapor("INDEX" + ("+MERGE_HEAD" if ek else ""), "HEAD", "INDEX", sonuc)
        if args.yeni and not args.taban:
            print("URUN_SILME_KAPISI: HATA --yeni tek basina verilmez (--taban gerekli)")
            return OLCULEMEDI
        if args.taban:
            taban, yeni = args.taban, args.yeni or "HEAD"
            for ref in (taban, yeni):
                if not _commit_var(depo, ref):
                    raise Olculemedi("revizyon cozulemedi: %s" % ref)
            return _rapor("ARALIK", taban, yeni, uc_nokta_hukmu(depo, taban, yeni))
        taban, yeni, eksen = ci_araligi(depo)
        for ref in (taban, yeni):
            if not _commit_var(depo, ref):
                raise Olculemedi("revizyon cozulemedi: %s" % ref)
        sonuc = pencere_hukmu(depo, taban, yeni)
        return _rapor(eksen, taban, yeni, sonuc)
    except Olculemedi as e:
        print("URUN_SILME_KAPISI: OLCULEMEDI — %s" % e)
        print("HUKUM: OLCULEMEDI (rc 2) — olculemeyen sey YESIL sayilmaz.")
        return OLCULEMEDI


if __name__ == "__main__":
    sys.exit(main())

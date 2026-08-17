#!/usr/bin/env python3
"""Katalogda mukerrer id, baslik ve kaynak linklerini denetler."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAKLAR = os.path.join(ROOT, ".urun-kaynaklari.json")
ISTISNALAR = os.path.join(ROOT, ".mukerrer-istisna.json")

# Cozulen istisna yolu bir kez basilsin diye (iki cagri noktasi var).
_ISTISNA_BILDIRILDI = set()


def _ana_agac_koku(kok=ROOT):
    """Paylasilan ANA calisma agacinin koku (worktree icinden cagrilsa da). Yoksa None."""
    try:
        p = subprocess.run(["git", "-C", kok, "rev-parse", "--git-common-dir"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=15)
    except Exception:                                           # noqa: BLE001
        return None
    if p.returncode != 0:
        return None
    ortak = (p.stdout or "").strip()
    if not ortak:
        return None
    if not os.path.isabs(ortak):
        ortak = os.path.join(kok, ortak)
    ana = os.path.dirname(os.path.abspath(ortak))
    return ana if os.path.isdir(ana) else None


def istisna_yolu(kok=ROOT, bildir=True):
    """Gecerli `.mukerrer-istisna.json` yolu — WORKTREE'DE DE ana agactaki kayit gorulur.

    🔴 NEDEN VAR (olculdu, ayni sinif UCUNCU kez): dosya `.gitignore`dadir ve
    `git worktree add` IZLENMEYEN dosyalari TASIMAZ. Sonuc olculdu (16 Agu 2026):
    ayni HEAD icin ana agacta `rc=0`, worktree'de `rc=1` — yani hukum AGACA GORE
    DEGISIYORDU. Bedeli: iki tur kancayi ATLADI, bir worktree (`k119e`) bu yuzden
    temizlenemedi ve URUN VERISINE HIC DOKUNMAYAN commit'ler bile bloklandi.
    Kural: **ayni HEAD, ayni hukum** — istisna kaydi ORTAK, agaca gore degismez.

    🔴 KAPSAM DAR: yalniz KAYIT ARANAN YER degisir. Dosya hicbir agacta yoksa
    davranis ESKISININ AYNISI (istisna YOK). Paylasilan dosyanin VARLIGI tek
    basina hicbir seyi yesile cevirmez; icerigi eskisi gibi ISLENIR."""
    yerel = os.path.join(kok, ".mukerrer-istisna.json")
    if os.path.exists(yerel):
        return yerel
    ana = _ana_agac_koku(kok)
    if ana and os.path.abspath(ana) != os.path.abspath(kok):
        paylasilan = os.path.join(ana, ".mukerrer-istisna.json")
        if os.path.exists(paylasilan):
            if bildir and paylasilan not in _ISTISNA_BILDIRILDI:
                _ISTISNA_BILDIRILDI.add(paylasilan)
                print("ISTISNA KAYNAGI: %s (paylasilan ana agac — worktree izlenmeyen "
                      "dosyayi tasimaz)" % paylasilan)
            return paylasilan
    return yerel


def _kaynak_linki(kayit):
    """Desteklenen kaynak kaydi biciminden linki cikarir."""
    link = ""
    if isinstance(kayit, str):
        link = kayit.split(None, 1)[0] if kayit.strip() else ""
    elif isinstance(kayit, dict):
        link = kayit.get("link", "")
    elif isinstance(kayit, list) and kayit and isinstance(kayit[0], dict):
        link = kayit[0].get("kaynak") or kayit[0].get("link", "")
    return link.strip() if isinstance(link, str) else ""


def _kaynaklari_oku(path):
    """Kaynak haritasi yoksa veya bozuksa sessizce None dondurur."""
    try:
        with open(path, encoding="utf-8") as f:
            kaynaklar = json.load(f)
    except (OSError, ValueError):
        return None
    return kaynaklar if isinstance(kaynaklar, dict) else None


def _istisnalari_oku(path):
    """Istisna dosyasi yoksa veya bozuksa sessizce bos kume dondurur."""
    try:
        with open(path, encoding="utf-8") as f:
            kayitlar = json.load(f)
    except (OSError, ValueError):
        return set()
    if not isinstance(kayitlar, list):
        return set()
    return {
        kayit.get("kaynak").strip()
        for kayit in kayitlar
        if isinstance(kayit, dict)
        and isinstance(kayit.get("kaynak"), str)
        and kayit.get("kaynak").strip()
    }


def _baslik_istisnalari_oku(path):
    """Baslik ekseni istisnalari -> {(baslik, frozenset(idler))}.

    🔴 17 AGU 2026 — "DOGRULANMIS YARGI HICBIR YERE COKMUYOR" SINIFI (olculdu):
    Bir BASLIK bulgusu mimarca DOGRULANIP MESRU ilan edildi (iki kayit FARKLI
    tasarimcidan) ama istisna dosyasi YALNIZ `kaynak` eksenini taniyordu; yargiyi
    yazacak alan YOKTU. Sonuc: ayni gerekce ile kanca UC kez blokladi, iki ev
    `PRUVO_MUKERRER_ATLA=1` ile gecti — kapi fiilen DEVRE DISI kaldi. Istisnasi
    OLMAYAN bir eksen, o eksende kapiyi kapatmaz; ATLAMAYI ogretir.

    🔴 NEDEN ID KUMESIYLE ANAHTARLANIR: yalniz baslik METNINE bakan bir istisna o
    basligi SONSUZA DEK acardi — ayni basligi tasiyan UCUNCU bir kayit sessizce
    girerdi. Kayit id KUMESINE baglidir: kume degisirse istisna ESLESMEZ ve bulgu
    YENIDEN kirmizi yanar. Yani istisna "bu baslik serbest" degil, "SU IKI KAYDIN
    ayni basligi tasimasi incelendi" demektir.

    FAIL-CLOSED: eksik/bos/tekil `idler` GECERSIZ sayilir — joker istisna YOKTUR.
    """
    try:
        with open(path, encoding="utf-8") as f:
            kayitlar = json.load(f)
    except (OSError, ValueError):
        return set()
    if not isinstance(kayitlar, list):
        return set()
    cikti = set()
    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            continue
        baslik = kayit.get("baslik")
        idler = kayit.get("idler")
        if not isinstance(baslik, str) or not baslik.strip():
            continue
        if not isinstance(idler, list) or len(idler) < 2:
            continue
        temiz = {i.strip() for i in idler if isinstance(i, str) and i.strip()}
        if len(temiz) != len(idler):      # bos/tekrarli/str-olmayan giris -> GECERSIZ
            continue
        cikti.add((baslik.strip(), frozenset(temiz)))
    return cikti


def _tara(urunler, kaynaklar=None, istisnalar=None, baslik_istisnalari=None):
    """Bulunan mukerrerleri (tur, deger, idler) olarak dondurur."""
    idler = defaultdict(list)
    basliklar = defaultdict(list)

    for sira, urun in enumerate(urunler):
        if not isinstance(urun, dict):
            continue
        urun_id = urun.get("id")
        gosterim_id = str(urun_id) if urun_id is not None else "#%d" % (sira + 1)
        idler[urun_id].append(gosterim_id)

        baslik = urun.get("baslik")
        if isinstance(baslik, str):
            basliklar[baslik.strip()].append(gosterim_id)

    bulgular = []
    for urun_id, ilgili_idler in idler.items():
        if len(ilgili_idler) > 1:
            bulgular.append(("ID", str(urun_id), ilgili_idler))

    baslik_muaf = baslik_istisnalari or set()
    for baslik, ilgili_idler in basliklar.items():
        if len(ilgili_idler) > 1:
            if (baslik, frozenset(ilgili_idler)) in baslik_muaf:
                continue
            bulgular.append(("BASLIK", baslik, ilgili_idler))

    if kaynaklar is not None:
        linkler = defaultdict(list)
        # Bir id katalogda iki kez geciyorsa kaynak bulgusunu da yapay olarak
        # cogaltma; bu durum zaten mukerrer id bulgusunda raporlanir.
        tekil_idler = dict.fromkeys(
            urun.get("id") for urun in urunler
            if isinstance(urun, dict) and urun.get("id") is not None
        )
        for urun_id in tekil_idler:
            link = _kaynak_linki(kaynaklar.get(urun_id))
            if link and link not in (istisnalar or set()):
                linkler[link].append(str(urun_id))
        for link, ilgili_idler in linkler.items():
            if len(ilgili_idler) > 1:
                bulgular.append(("KAYNAK", link, ilgili_idler))

    return bulgular


def _oz_sinama():
    temiz = [
        {"id": "urun-a", "baslik": "Baslik A"},
        {"id": "urun-b", "baslik": "Baslik B"},
    ]

    kontroller = [
        ("temiz veri", not _tara(temiz, {})),
        ("mukerrer id", any(
            b[0] == "ID" for b in _tara([
                {"id": "ayni", "baslik": "Bir"},
                {"id": "ayni", "baslik": "Iki"},
            ], {})
        )),
        ("mukerrer baslik", any(
            b[0] == "BASLIK" for b in _tara([
                {"id": "bir", "baslik": " Ayni Baslik "},
                {"id": "iki", "baslik": "Ayni Baslik"},
            ], {})
        )),
        ("mukerrer kaynak", any(
            b[0] == "KAYNAK" for b in _tara(temiz, {
                "urun-a": "https://ornek.test/model aciklama",
                "urun-b": [{"kaynak": "https://ornek.test/model"}],
            })
        )),
    ]

    with tempfile.TemporaryDirectory() as gecici:
        olmayan = os.path.join(gecici, "kaynaklar.json")
        try:
            bulgular = _tara(temiz, _kaynaklari_oku(olmayan))
            eksik_dosya_ok = not bulgular
        except Exception:
            eksik_dosya_ok = False
    kontroller.append(("kaynak dosyasi yok", eksik_dosya_ok))

    with tempfile.TemporaryDirectory() as gecici:
        istisna_dosyasi = os.path.join(gecici, "istisnalar.json")
        with open(istisna_dosyasi, "w", encoding="utf-8") as f:
            json.dump([{
                "kaynak": "https://ornek.test/model",
                "neden": "Bilinen ortak kaynak",
            }], f)
        istisnali_bulgular = _tara(temiz, {
            "urun-a": "https://ornek.test/model aciklama",
            "urun-b": [{"kaynak": "https://ornek.test/model"}],
        }, _istisnalari_oku(istisna_dosyasi))
    kontroller.append(("istisnali kaynak", not istisnali_bulgular))

    with tempfile.TemporaryDirectory() as gecici:
        bozuk_istisna = os.path.join(gecici, "istisnalar.json")
        with open(bozuk_istisna, "w", encoding="utf-8") as f:
            f.write("{bozuk json")
        try:
            bozuk_bulgular = _tara(temiz, {
                "urun-a": "https://ornek.test/model aciklama",
                "urun-b": [{"kaynak": "https://ornek.test/model"}],
            }, _istisnalari_oku(bozuk_istisna))
            bozuk_istisna_ok = any(b[0] == "KAYNAK" for b in bozuk_bulgular)
        except Exception:
            bozuk_istisna_ok = False
    kontroller.append(("bozuk istisna dosyasi", bozuk_istisna_ok))

    # --- BASLIK EKSENI ISTISNASI (K143 (a) kolu) -----------------------------
    # Istisna id KUMESINE baglidir: ayni cift -> muaf; kumeye UCUNCU kayit
    # girerse -> YENIDEN kirmizi. Eksik `idler` joker DEGIL, GECERSIZ'dir.
    ayni_baslikli_cift = [
        {"id": "kaynak-a-parca", "baslik": "Ayni Ad Farkli Tasarim"},
        {"id": "kaynak-b-parca", "baslik": "Ayni Ad Farkli Tasarim"},
    ]
    ucuncu_kayit = ayni_baslikli_cift + [
        {"id": "kaynak-c-parca", "baslik": "Ayni Ad Farkli Tasarim"},
    ]
    with tempfile.TemporaryDirectory() as gecici:
        baslik_istisnasi = os.path.join(gecici, "istisnalar.json")
        with open(baslik_istisnasi, "w", encoding="utf-8") as f:
            json.dump([{
                "baslik": "Ayni Ad Farkli Tasarim",
                "idler": ["kaynak-a-parca", "kaynak-b-parca"],
                "neden": "Incelendi: bagimsiz iki tasarim",
            }], f)
        muaf = _baslik_istisnalari_oku(baslik_istisnasi)

        jokersiz = os.path.join(gecici, "jokersiz.json")
        with open(jokersiz, "w", encoding="utf-8") as f:
            json.dump([{"baslik": "Ayni Ad Farkli Tasarim",
                        "neden": "idler ALANI YOK — gecersiz olmali"}], f)
        joker = _baslik_istisnalari_oku(jokersiz)

    kontroller.extend([
        ("baslik istisnasi kayitli cifti susturur",
         not _tara(ayni_baslikli_cift, {}, set(), muaf)),
        ("baslik istisnasi UCUNCU kayitta ESLESMEZ",
         any(b[0] == "BASLIK" for b in _tara(ucuncu_kayit, {}, set(), muaf))),
        ("idler'siz istisna GECERSIZ (joker yok)",
         any(b[0] == "BASLIK" for b in _tara(ayni_baslikli_cift, {}, set(), joker))),
        ("istisnasiz baslik cifti KIRMIZI",
         any(b[0] == "BASLIK" for b in _tara(ayni_baslikli_cift, {}, set(), set()))),
    ])

    hatalar = [ad for ad, gecti in kontroller if not gecti]
    if hatalar:
        for ad in hatalar:
            print("TEST KALDI: %s" % ad, file=sys.stderr)
        return 1
    print("TEST GECTI")
    return 0


def _git_oku(args):
    return subprocess.run(["git", "-C", ROOT] + args, capture_output=True, text=True)


def _index_urunler():
    r = _git_oku(["show", ":urunler.json"])
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def _head_urunler():
    r = _git_oku(["show", "HEAD:urunler.json"])
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


# Kapsam on-elemesinin ve yargi biriminin ORTAK pathspec'i. TEK YERDE durur ki
# "neyi eliyoruz" ile "neyi yargiliyoruz" sessizce ayrisamasin.
URUN_YOLLARI = ["urunler.json", ".urun-kaynaklari.json"]


def _urun_stage_durumu():
    """Bu commit URUN dosyalarina dokunuyor mu — TEK KANONIK OLCUM.

    Donus: "stage" | "stage-disi" | "olculemedi".

    Hem kapsam on-elemesi hem de yargi birimi (`_commit_katalogu`) AYNI bu olcumu
    kullanir. Iki ayri `git diff --cached` cagrisi yapilsaydi, biri kapsami elerken
    digeri baska bir surumu yargilayabilir ve iki eksen sessizce ayrisirdi
    ([[kabul-araligi-karsilastirma-araligi]]).
    """
    r = _git_oku(["diff", "--cached", "--quiet", "--"] + URUN_YOLLARI)
    if r.returncode == 0:
        return "stage-disi"
    if r.returncode == 1:
        return "stage"
    return "olculemedi"


def _commit_katalogu(durum):
    """Pre-commit yargi birimi: stage edilmisse INDEX, degilse HEAD surumu.
    Ikisi de okunamazsa (None, gerekce) dondurur (fail-closed cagri sahibine dus)."""
    if durum == "stage":
        urunler = _index_urunler()
        if urunler is not None:
            return urunler, None
        return None, "urunler.json stage edilmis ama INDEX surumu okunamadi"
    if durum == "stage-disi":
        urunler = _head_urunler()
        if urunler is not None:
            return urunler, None
        return None, "urunler.json stage edilmemis ama HEAD surumu okunamadi"
    urunler = _index_urunler()
    if urunler is not None:
        return urunler, None
    urunler = _head_urunler()
    if urunler is not None:
        return urunler, None
    return None, "commit icerigi okunamadi (INDEX ve HEAD)"


def _pre_commit_tarama():
    # --- KAPSAM ON-ELEMESI (17 Agu 2026, K143 (b) kolu) ----------------------
    # 🔴 OLCULEN ARIZA: bu kol commit'in KAPSAMINI hic sormuyordu. urunler.json
    #   stage'lenmemisse yargi birimi HEAD'e dusuyor (bkz. `_commit_katalogu`) —
    #   yani YALNIZ `DEVAM.md` degistiren bir commit bile HEAD'de duran bir urun
    #   mukerrerinden BLOKLANIYORDU. Commit'in kapsami ile kancanin kapsami
    #   ayrismisti ([[kanca-stage-disi-agaci-tarar]]). Bedeli olculdu: ayni gerekce
    #   UC commit'i durdurdu, iki ev PRUVO_MUKERRER_ATLA=1 ile gecti; bir kapiyi
    #   herkesin atladigi an o kapi KORUMUYOR demektir.
    # FAIL-CLOSED YON KORUNUR: yalnizca "URUN DOSYASINA DOKUNULMADIGI OLCULDU"
    #   hali eler. Urun dosyasi stage'lendiginde tarama AYNEN kosar; olcum
    #   YAPILAMADIGINDA da (rc>1) kosar — olculemeyen sey yesil sayilmaz.
    # ATLAMA SESSIZ DEGIL: nedeni her seferinde BASILIR (sessiz atlama = sessiz yesil).
    durum = _urun_stage_durumu()
    if durum == "stage-disi":
        print("-- mukerrer taramasi ATLANDI: bu commit urun dosyalarina DOKUNMUYOR "
              "(%s stage'lenmedi; kapsam on-elemesi INDEX ekseninde)." % ", ".join(URUN_YOLLARI))
        return 0

    kaynaklar = _kaynaklari_oku(KAYNAKLAR)
    istisnalar = _istisnalari_oku(istisna_yolu())
    baslik_istisnalari = _baslik_istisnalari_oku(istisna_yolu())
    urunler, gerekce = _commit_katalogu(durum)
    if urunler is None:
        print("COMMIT KAYNAGI OKUNAMADI: %s" % gerekce)
        with open(URUNLER, encoding="utf-8") as f:
            calisma = json.load(f)
        bulgular = _tara(calisma, kaynaklar, istisnalar, baslik_istisnalari)
        if bulgular:
            for tur, deger, ilgili_idler in bulgular:
                print("MUKERRER %s: %s -> %s" % (tur, deger, ", ".join(ilgili_idler)))
        print("calisma agaci tarandi: %d urun, %d mukerrer" % (len(calisma), len(bulgular)))
        return 1
    bulgular = _tara(urunler, kaynaklar, istisnalar, baslik_istisnalari)
    if bulgular:
        for tur, deger, ilgili_idler in bulgular:
            print("MUKERRER %s: %s -> %s" % (tur, deger, ", ".join(ilgili_idler)))
        return 1
    print("mukerrer yok: %d urun tarandi (commit icerigi)" % len(urunler))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", action="store_true", help="bellek ici oz-sinamayi calistir")
    ap.add_argument("--pre-commit", action="store_true",
                    help="commit icerigini (index/HEAD) yargila; calisma agaci degil")
    args = ap.parse_args()

    if args.test:
        return _oz_sinama()

    if args.pre_commit:
        return _pre_commit_tarama()

    with open(URUNLER, encoding="utf-8") as f:
        urunler = json.load(f)
    kaynaklar = _kaynaklari_oku(KAYNAKLAR)
    istisnalar = _istisnalari_oku(istisna_yolu())
    baslik_istisnalari = _baslik_istisnalari_oku(istisna_yolu())
    bulgular = _tara(urunler, kaynaklar, istisnalar, baslik_istisnalari)

    if bulgular:
        for tur, deger, ilgili_idler in bulgular:
            print("MUKERRER %s: %s -> %s" % (tur, deger, ", ".join(ilgili_idler)))
        return 1

    print("mukerrer yok: %d urun tarandi" % len(urunler))
    return 0


if __name__ == "__main__":
    sys.exit(main())

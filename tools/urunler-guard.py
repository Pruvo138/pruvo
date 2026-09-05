#!/usr/bin/env python3
"""urunler-guard.py — urunler.json icin PROVENANS-BILEN, FAIL-LOUD koruma katmani.

AMAC: toplu urun ekleme sirasinda MEVCUT (bir EBEVEYNDE zaten var olan) urunlerin
kazayla bozulmasini YAPISAL olarak imkansiz kilmak.

🔴 IKI ILKE (4 Agu 2026 olayindan sonra — bkz. "OLAY" bolumu):

  ILKE 1 — PROVENANS: bir MERGE sirasinda gorulen degisim, IKI EBEVEYNDEN
  BIRINDEN geliyorsa MESRUDUR. Izinsiz olan, HICBIR EBEVEYNDE bulunmayan
  degisimdir. Guard merge halini (MERGE_HEAD) artik GORUR ve hukmunu iki
  ebeveynin BIRLESIMINE dayandirir.

  ILKE 2 — SESSIZ MUTASYON YERINE FAIL-LOUD (bu ikisinden onemlisi):
  provenansi KARARLASTIRAMADIGI her halde guard veriyi SESSIZCE DEGISTIRMEZ;
  commit'i SIFIR-DISI cikisla REDDEDER ve nedenini stderr'e BASAR. "Emin
  degilsem geri sararim" YASAK; "emin degilsem DURDURURUM ve soylerim" DOGRU.
  Geri sarma yalnizca provenansi KESIN olarak "izinsiz" cikan DAR halde
  (merge DISI, tek ebeveyn = HEAD) kalir ve HER geri sarma stderr'e GORUNUR
  basilir (ne degisti, hangi urun, hangi alan).

OLAY (4 Agu 2026, olculdu): bir muhendis worktree'sinde `origin/main` dala merge
edildi. Merge commit'i (aba92a1c) atilirken guard, merge'in GETIRDIGI guncel
katalogu dalin BAYAT haline GERI SARDI — 5 ekleme / 11 silme; bir uründen 1
gorsel, digerinden `lisans` blogu (GNU GPL v2.0 ATFI) + 1 gorsel dustu, aciklama
461 -> 378 karaktere bayatladi. HICBIR KAPI CALMADI: cikis kodu 0, stdout/stderr
BOS. Kok neden: guard yalnizca `HEAD`e bakiyordu; merge halinde HEAD = DALIN
BAYAT ucu, merge'in getirdigi guncel icerik ise MERGE_HEAD'de. Atfin sessizce
dusmesi ayrica HUKUKI risktir (CC BY sinifi atif KALMAK ZORUNDA).

KURAL — working-tree urunler.json'i EBEVEYN(LER)le karsilastirir:
  MERGE DISI (tek ebeveyn = HEAD):
    * HEAD'de OLMAYAN id (yeni urun)                 -> SERBEST, hic dokunma.
    * HEAD'de OLAN bir urunun alan(lar)i degismisse:
        - degisen alanlarin TAMAMI .urunler-duzelt-izin.json manifestinde o id
          icin (ayni deger ile) beyan edilmisse        -> KABUL (mesru duzeltme).
        - aksi halde  -> provenans KESIN olarak "izinsiz": urunun TUM alanlarini
          HEAD'deki haline yerinde geri dondur ve GERI SARMAYI STDERR'E BAS.
    * HEAD'de olup working-tree'den SILINMIS urun:
        - id .urunler-sil-izin.json manifestinde beyan edilmisse -> KABUL.
        - eski->yeni, .urunler-id-rename-izin.json'da beyanli ve kayit id disinda
          birebir ayniysa -> tek ID-RENAME islemi olarak KABUL (duplicate uretilmez).
        - aksi halde (izinsiz) -> geri ekle (koru) + STDERR'E BAS.
  MERGE HALINDE (MERGE_HEAD var; ebeveynler = HEAD + MERGE_HEAD):
    * id HICBIR ebeveynde yoksa                      -> yeni urun, SERBEST.
    * urunun WT hali HERHANGI BIR ebeveynin haline BIREBIR esitse
                                                     -> MERGE GETIRISI, MESRU.
    * HEAD'e gore degisen alanlarin TAMAMI manifestte beyanliysa -> KABUL.
    * aksi halde: hangi ebeveyne geri sarilacagi BELIRSIZDIR -> REDDET (exit 3),
      SESSIZ MUTASYON YOK.
    * SILME: id en az BIR ebeveynde YOKSA yoklugu bir ebeveyn halidir -> MESRU
      (or. main urunu silmis). Iki ebeveynde de VARSA ve sil-izni yoksa -> REDDET.

FAIL-LOUD (exit 3, veri DEGISTIRILMEZ) halleri:
  * working-tree urunler.json BOZUK JSON        (eskiden: sessiz atlama)
  * working-tree urunler.json YOK ama HEAD'de dolu katalog var
  * HEAD:urunler.json BOZUK JSON                (eskiden: sessiz atlama)
  * merge halinde herhangi bir ebeveynin katalogu OKUNAMIYOR/BOZUK
  * merge halinde provenansi cozulemeyen urun/silme
  * guard'in kendi BEKLENMEDIK HATASI           (eskiden: sessiz exit 0)
🔴 REDDEDILDIGINDE CIKIS YOLLARI — `CIKIS_YOLLARI` TEK KAYNAKTIR. Basilan metin o
listeden TURER ve kabul testi (`tools/urunler-guard-provenans-test.py` :: E1-E4)
her yolu FIILEN kosturup rc=0 verdigini OLCER; metin ile mekanizma ayrisirsa kapi
KIRMIZI yanar ([[ikiz-tanim-sessiz-ayrisma]]). ⚠️ `PRUVO_GUARD_ZORLA=1 git commit ...`
gibi KOMUT ONUNE yazilan env atamasi CALISMAZ: harness PreToolUse hook'u harness
surecinin env'inde kosar, komutun env'ini GORMEZ (olculdu: rc=2, hala bloklu).

🔴 KORUMA TASINABILIR DEGIL — NEREDE KOSAR, NEREDE KOSMAZ (durust beyan):
  KOSAR : Claude Code oturumlari — `.claude/settings.json` PreToolUse(Bash) kablosu
          `tools/urunler-guard-hook.py`yi cagirir; kopru IZLENDIGI icin fail-loud
          davranisi her makinede aynidir. `--no-verify` bunu ATLATAMAZ.
  KOSMAZ: git-native yol FAIL-OPEN'dir. `.git/hooks/pre-commit` bugun
          `python3 "$guard" --tetik commit >/dev/null 2>&1 || true` yazar — cikis
          kodunu VE stderr'i yutar. Kanca commit EDILMEDIGI icin (gitignore) bu
          dosyadan duzeltilemez; her makinede ELLE kurulur. Sonuc: harness'siz bir
          oturumda (duz terminal, emekli motor, baska makine, CI) bu guard commit'i
          BLOKLAMAZ — yalnizca `.urunler-guard.log`a yazar.
  Onerilen kanca duzeltmesi: `pre-commit` cikis kodunu YUTMASIN — `|| true` ve
  `>/dev/null 2>&1` kaldirilip guard'in rc'si ve stderr'i oldugu gibi gecirilsin.
  Uygulanana kadar "koruma her yerde gecerli" SANILMAMALIDIR.

Manifest DEGER-BAGLI'dir: bir alanin degisimine ancak working-tree'deki yeni
deger, manifeste yazilan beklenen deger ile birebir esitse izin verilir. Bu
sayede eski/bayat bir manifest asla yeni bir kazayi mesrulastiramaz. Silme
manifesti id-listesidir. Guard manifestleri ASLA SILMEZ; iki kez pes pese
calismasi idempotenttir.

Tum okuma/yazma .urunler.lock flock'u altinda yapilir.
Ne yaptigini .urunler-guard.log'a VE stderr'e yazar.

Cikis kodlari:  0 = temiz / mesru duzeltme / (dar) geri sarma yapildi
                3 = REDDEDILDI — provenans kararlastirilamadi, veri DEGISMEDI

Kullanim:  python3 tools/urunler-guard.py [--tetik commit|push|manuel]
"""
import argparse
import copy
import datetime
import fcntl
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
MANIFEST = os.path.join(ROOT, ".urunler-duzelt-izin.json")
MANIFEST_SIL = os.path.join(ROOT, ".urunler-sil-izin.json")
MANIFEST_ID_RENAME = os.path.join(ROOT, ".urunler-id-rename-izin.json")
LOG = os.path.join(ROOT, ".urunler-guard.log")

RED = 3          # provenans kararlastirilamadi -> commit REDDEDILIR
ZORLA_ENV = "PRUVO_GUARD_ZORLA"

# 🔴 TEK KAYNAK — bastigimiz cikis yollari BURADAN turer ([[ikiz-tanim-sessiz-ayrisma]]).
# Kabul testi (urunler-guard-provenans-test.py :: E1-E4) her yolu FIILEN kosturur ve
# rc=0 verdigini OLCER; ayrica basilan metnin bu listedeki HER kodu tasidigini olcer.
# Metin ile mekanizma ayrisirsa kapi KIRMIZI yanar — "belgelenen cikis calisiyor"
# BEYAN degil OLCUMDUR.
CIKIS_YOLLARI = (
    ("MANIFEST",
     "degisimi BEYAN et: python3 tools/duzelt.py --id <id> --alan <alan> --deger <deger> "
     "(deger-bagli izin .urunler-duzelt-izin.json'a yazilir; silme icin "
     ".urunler-sil-izin.json)"),
    ("EBEVEYN",
     "urunu ebeveynlerden BIRININ hali ile AYNEN birak (merge'de: o urun icin main'in "
     "ya da dalin halini oldugu gibi sec — ucuncu bir hal uretme)"),
    ("ZORLA",
     "SURECIN env'ine PRUVO_GUARD_ZORLA=1 koy (export). ⚠️ Komut ONUNE yazmak "
     "(PRUVO_GUARD_ZORLA=1 git commit ...) CALISMAZ: PreToolUse hook'u harness "
     "surecinin env'inde kosar, komutun env'ini GORMEZ — olculdu: rc=2, hala bloklu"),
)

_MISSING = object()


class Belirsiz(Exception):
    """Provenans KARARLASTIRILAMADI. Veri DEGISTIRILMEZ, commit REDDEDILIR.

    Bu istisna guard'in TEK "durdur" yoludur; sessiz mutasyonun yerini alir.
    """

    def __init__(self, sebep, ayrinti=""):
        super().__init__(sebep)
        self.sebep = sebep
        self.ayrinti = ayrinti


def _log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f:
            f.write("[%s] %s\n" % (ts, msg))
    except OSError:
        pass


def _bas(msg):
    """GORUNURLUK: guard'in yaptigi/reddettigi her sey stderr'e de basilir."""
    try:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def _git(*args):
    """git -C ROOT <args> -> (rc, stdout_bytes). Hata yutulur."""
    try:
        p = subprocess.run(["git", "-C", ROOT, *args],
                           capture_output=True)
        return p.returncode, p.stdout
    except Exception:
        return 1, b""


def _canon(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False)


def _atomic_write(path, obj):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _changed_fields(head_p, wt_p):
    """head_p ve wt_p arasinda farkli olan alan adlari."""
    out = []
    for k in set(head_p) | set(wt_p):
        a = head_p.get(k, _MISSING)
        b = wt_p.get(k, _MISSING)
        if a is _MISSING or b is _MISSING:
            if not (a is _MISSING and b is _MISSING):
                out.append(k)
            continue
        if _canon(a) != _canon(b):
            out.append(k)
    return out


def _authorized(uid, field, wt_p, manifest):
    """wt_p[field] degisimi manifestte (ayni deger ile) beyan edilmis mi?"""
    entry = manifest.get(uid)
    if not isinstance(entry, dict) or field not in entry:
        return False
    expected = entry[field]
    # Beyanli ALAN SILME: manifest {"__alan_sil__": true} sentineli tasiyorsa
    # o alanin working-tree'de YOK olmasi mesrudur (duzelt.py --alan-sil yazar).
    if isinstance(expected, dict) and expected.get("__alan_sil__") is True:
        return field not in wt_p
    if field not in wt_p:  # WT'de silinmis alan -> deger-bagli izin veremez
        return False
    return _canon(wt_p[field]) == _canon(expected)


def _id_rename_haritasi(manifest, wt_list, ebeveynler):
    """Beyanli ve yapisal olarak kanitlanmis ``eski -> yeni`` islemleri.

    ID guard'in kimlik ekseni oldugu icin rename normalde silme+ekleme gorunur.
    Bu dar kol yalniz eski ebeveyn kaydinin ``id`` disinda byte-anlamsal olarak ayni
    tek hedef kayda donustugu vakayi bir islem sayar. Cakisma, duplicate, eksik hedef
    veya baska alan degisikligi muafiyet alamaz.
    """
    if not isinstance(manifest, dict):
        return {}
    wt_adet = {}
    wt_by_id = {}
    for p in wt_list:
        if isinstance(p, dict) and isinstance(p.get("id"), str):
            uid = p["id"]
            wt_adet[uid] = wt_adet.get(uid, 0) + 1
            wt_by_id[uid] = p
    ebeveyn_ids = set()
    for by_id in ebeveynler:
        ebeveyn_ids |= set(by_id)
    hedef_adet = {}
    for yeni in manifest.values():
        if isinstance(yeni, str):
            hedef_adet[yeni] = hedef_adet.get(yeni, 0) + 1

    gecerli = {}
    for eski, yeni in manifest.items():
        if not isinstance(eski, str) or not isinstance(yeni, str) or eski == yeni:
            continue
        if hedef_adet.get(yeni) != 1:
            continue
        eski_haller = [by_id[eski] for by_id in ebeveynler if eski in by_id]
        if not eski_haller or eski in wt_by_id or yeni in ebeveyn_ids:
            continue
        if wt_adet.get(yeni) != 1:
            continue
        hedef = wt_by_id[yeni]
        beklenenler = []
        for eski_hal in eski_haller:
            beklenen = copy.deepcopy(eski_hal)
            beklenen["id"] = yeni
            beklenenler.append(_canon(beklenen))
        if _canon(hedef) in beklenenler:
            gecerli[eski] = yeni
    return gecerli


# ----------------------------------------------------------------- provenans
def _merge_head():
    """Merge devam ediyor mu? -> MERGE_HEAD sha (str) ya da None.

    GIT DIZINI uzerinden OLCULUR (worktree'de de dogru yeri gosterir). Dizin
    cozulemezse bu bir OKUMA BASARISIZLIGIDIR, "merge yok" DEGILDIR -> Belirsiz.
    """
    rc, out = _git("rev-parse", "--absolute-git-dir")
    if rc != 0:
        raise Belirsiz("GIT DIZINI OKUNAMADI",
                       "git rev-parse --absolute-git-dir rc=%d (%s)" % (rc, ROOT))
    gitdir = out.decode("utf-8", "replace").strip()
    yol = os.path.join(gitdir, "MERGE_HEAD")
    if not os.path.exists(yol):
        return None
    try:
        with open(yol, encoding="utf-8") as f:
            sha = f.read().split()[0].strip()
    except (OSError, IndexError, UnicodeDecodeError) as e:
        raise Belirsiz("MERGE_HEAD OKUNAMADI", "%s: %r" % (yol, e))
    if not sha:
        raise Belirsiz("MERGE_HEAD BOS", yol)
    return sha


def _katalog(ref):
    """<ref>:urunler.json -> ("var", liste) | ("yok", None) | ("bozuk", sebep)."""
    rc, ham = _git("show", "%s:urunler.json" % ref)
    if rc != 0:
        return "yok", None
    try:
        obj = json.loads(ham.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        return "bozuk", repr(e)
    if not isinstance(obj, list):
        return "bozuk", "kok dizi degil: %s" % type(obj).__name__
    return "var", obj


def _by_id(liste):
    out = {}
    for p in liste or []:
        if isinstance(p, dict) and "id" in p:
            out[p["id"]] = p
    return out


def _ebeveyn_halleri(uid, ebeveynler):
    """uid icin ebeveynlerdeki KANONIK hallerin kumesi (id'i olmayan ebeveyn atlanir)."""
    return {_canon(by_id[uid]) for by_id in ebeveynler if uid in by_id}


# ---------------------------------------------------------------------- heal
def heal(tetik):
    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        return _heal_kilitli(tetik)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()


def _heal_kilitli(tetik):
    merge_sha = _merge_head()
    merge_mi = merge_sha is not None

    # --- Ebeveyn kataloglari -------------------------------------------------
    head_durum, head_list = _katalog("HEAD")
    if head_durum == "bozuk":
        raise Belirsiz("HEAD:urunler.json BOZUK",
                       "taban okunamadan hicbir provenans hukmu verilemez (%s)" % head_list)
    if head_durum == "yok" and not merge_mi:
        _log("%s: HEAD:urunler.json yok (yeni repo / izlenmiyor?) — korunacak taban YOK." % tetik)
        return "taban-yok"

    ebeveynler = []
    if head_durum == "var":
        ebeveynler.append(_by_id(head_list))
    head_by_id = ebeveynler[0] if ebeveynler else {}

    merge_by_id = {}
    if merge_mi:
        m_durum, m_list = _katalog(merge_sha)
        if m_durum != "var":
            raise Belirsiz("MERGE HALINDE EBEVEYN KATALOGU OKUNAMADI",
                           "MERGE_HEAD=%s durum=%s (%s)" % (merge_sha[:12], m_durum, m_list))
        if head_durum != "var":
            raise Belirsiz("MERGE HALINDE HEAD KATALOGU OKUNAMADI",
                           "HEAD durum=%s — iki ebeveyn olmadan provenans cozulemez" % head_durum)
        merge_by_id = _by_id(m_list)
        ebeveynler.append(merge_by_id)

    # --- Working tree --------------------------------------------------------
    try:
        with open(URUNLER, encoding="utf-8") as f:
            wt_list = json.load(f)
    except FileNotFoundError:
        if head_by_id:
            raise Belirsiz("working-tree urunler.json YOK",
                           "HEAD'de %d urun var — tum katalogun yoklugu geri sarilamaz"
                           % len(head_by_id))
        _log("%s: working-tree urunler.json yok, HEAD de bos — atlandi." % tetik)
        return "wt-yok"
    except ValueError as e:
        # Eskiden SESSIZ atlanirdi -> bozuk katalog commit'e girebiliyordu.
        raise Belirsiz("working-tree urunler.json BOZUK JSON",
                       "HEAD'e sifirlamak tum yeni urunleri silerdi; hukum verilemez (%r)" % e)
    if not isinstance(wt_list, list):
        raise Belirsiz("working-tree urunler.json KOK DIZI DEGIL",
                       "tip=%s" % type(wt_list).__name__)

    # --- Manifestler ---------------------------------------------------------
    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            with open(MANIFEST, encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, dict):
                manifest = m
        except ValueError:
            _log("%s: UYARI manifest bozuk — izin YOK sayildi." % tetik)

    sil_izin = set()
    if os.path.exists(MANIFEST_SIL):
        try:
            with open(MANIFEST_SIL, encoding="utf-8") as f:
                s = json.load(f)
            if isinstance(s, list):
                sil_izin = set(s)
        except ValueError:
            _log("%s: UYARI silme manifesti bozuk — izin YOK sayildi." % tetik)

    id_rename_manifest = {}
    if os.path.exists(MANIFEST_ID_RENAME):
        try:
            with open(MANIFEST_ID_RENAME, encoding="utf-8") as f:
                r = json.load(f)
            if isinstance(r, dict):
                id_rename_manifest = r
        except ValueError:
            _log("%s: UYARI id-rename manifesti bozuk — izin YOK sayildi." % tetik)

    id_rename = _id_rename_haritasi(id_rename_manifest, wt_list, ebeveynler)
    wt_idleri = {p.get("id") for p in wt_list if isinstance(p, dict)}
    ebeveyn_idleri = set()
    for by_id in ebeveynler:
        ebeveyn_idleri |= set(by_id)
    gecersiz_rename = [eski for eski, yeni in id_rename_manifest.items()
                       if eski in ebeveyn_idleri and eski not in wt_idleri
                       and yeni in wt_idleri and eski not in id_rename]
    if gecersiz_rename:
        raise Belirsiz(
            "ID-RENAME BEYANI DOGRULANAMADI",
            "eski kayit geri eklenmedi; duplicate uretilmedi (%s)"
            % ", ".join(sorted(gecersiz_rename)))
    yeni_eski = {yeni: eski for eski, yeni in id_rename.items()}

    restored, kept_auth, merge_getirisi, yetkili_rename = [], [], [], []
    belirsizler = []
    yeni = 0
    wt_ids = set()

    # 1) Working-tree sirasini KORU; mevcut urunleri yerinde denetle.
    for i, p in enumerate(wt_list):
        if not isinstance(p, dict) or "id" not in p:
            continue
        uid = p["id"]
        wt_ids.add(uid)
        if uid in yeni_eski:
            yetkili_rename.append((yeni_eski[uid], uid))
            continue
        halleri = _ebeveyn_halleri(uid, ebeveynler)
        if not halleri:
            yeni += 1
            continue  # hicbir ebeveynde yok -> yeni urun, serbest

        # ILKE 1 — PROVENANS: WT hali herhangi bir EBEVEYNIN hali ise MESRUDUR.
        if _canon(p) in halleri:
            if merge_mi and uid in head_by_id and _canon(p) != _canon(head_by_id[uid]):
                merge_getirisi.append(uid)
            continue

        head_p = head_by_id.get(uid)
        if head_p is None:
            # Yalniz MERGE_HEAD'de var; WT hali ondan da farkli -> ebeveynsiz icerik.
            belirsizler.append(
                "%s: WT hali HICBIR EBEVEYNE uymuyor (yalniz MERGE_HEAD'de mevcut)" % uid)
            continue

        changed = _changed_fields(head_p, p)
        unauth = [c for c in changed if not _authorized(uid, c, p, manifest)]
        if not unauth:
            kept_auth.append((uid, sorted(changed)))
            continue

        if merge_mi:
            # ILKE 2 — hangi ebeveyne geri sarilacagi BELIRSIZ; SESSIZ MUTASYON YOK.
            belirsizler.append(
                "%s: merge halinde WT hali HICBIR EBEVEYNE uymuyor, beyan da yok "
                "(izinsiz alanlar: %s)" % (uid, ",".join(sorted(unauth))))
            continue

        # Merge DISI: tek ebeveyn var, provenans KESIN olarak "izinsiz" -> dar geri sarma.
        wt_list[i] = copy.deepcopy(head_p)
        restored.append((uid, sorted(changed)))

    # 2) SILINEN urunler.
    tum_ebeveyn_ids = set()
    for by_id in ebeveynler:
        tum_ebeveyn_ids |= set(by_id)
    eksik = [uid for uid in sorted(tum_ebeveyn_ids) if uid not in wt_ids]

    silinen, yetkili_silme, merge_silmesi = [], [], []
    for uid in eksik:
        if uid in id_rename:
            continue
        if uid in sil_izin:
            yetkili_silme.append(uid)
            continue
        if merge_mi:
            # Yokluk bir EBEVEYN HALI mi? (en az bir ebeveynde bulunmuyorsa evet)
            if any(uid not in by_id for by_id in ebeveynler):
                merge_silmesi.append(uid)     # or. main urunu silmis -> MESRU
            else:
                belirsizler.append(
                    "%s: merge halinde IKI EBEVEYNDE de var ama WT'de YOK, sil-izni yok" % uid)
            continue
        silinen.append(uid)

    # 3) ILKE 2 — belirsiz kalan tek bir hal bile varsa HICBIR SEY YAZILMAZ.
    if belirsizler:
        raise Belirsiz("MERGE PROVENANSI COZULEMEDI (%d kalem)" % len(belirsizler),
                       "\n".join("    - " + b for b in belirsizler))

    for uid in silinen:
        wt_list.insert(0, copy.deepcopy(head_by_id[uid]))

    degisti = bool(restored or silinen)

    if degisti:
        _atomic_write(URUNLER, wt_list)
        rc, staged = _git("diff", "--cached", "--name-only")
        if rc == 0 and "urunler.json" in staged.decode("utf-8", "replace").split():
            _git("add", "urunler.json")
        # GORUNURLUK: her geri sarma stderr'e basilir (eskiden yalniz log'daydi).
        _bas("!! urunler-guard (%s): KATALOG DEGISTIRILDI — izinsiz degisim geri alindi."
             % tetik)
        for uid, fs in restored:
            _bas("   GERI SARILDI  %s  alanlar: %s" % (uid, ", ".join(fs)))
        for uid in silinen:
            _bas("   GERI EKLENDI  %s  (izinsiz silme)" % uid)
        _bas("   Ayrinti: .urunler-guard.log")

    # Ozet log
    parts = ["%s: merge=%s yeni=%d" % (tetik, merge_sha[:12] if merge_mi else "yok", yeni)]
    if merge_getirisi:
        parts.append("MERGE_GETIRISI_MESRU=%d %s"
                     % (len(merge_getirisi), ", ".join(merge_getirisi[:40])))
    if merge_silmesi:
        parts.append("MERGE_SILMESI_MESRU=%d %s"
                     % (len(merge_silmesi), ", ".join(merge_silmesi[:40])))
    if restored:
        parts.append("GERI_YUKLENEN=%d %s" % (
            len(restored),
            ", ".join("%s[%s]" % (u, ",".join(fs)) for u, fs in restored[:40])))
    if silinen:
        parts.append("SILINMISTEN_GERI=%d %s" % (len(silinen), ", ".join(silinen[:40])))
    if kept_auth:
        parts.append("mesru_duzeltme=%d %s" % (
            len(kept_auth),
            ", ".join("%s[%s]" % (u, ",".join(fs)) for u, fs in kept_auth[:40])))
    if yetkili_silme:
        parts.append("yetkili_silme=%d %s" % (len(yetkili_silme), ", ".join(yetkili_silme[:40])))
    if yetkili_rename:
        parts.append("yetkili_id_rename=%d %s" % (
            len(yetkili_rename),
            ", ".join("%s->%s" % cift for cift in yetkili_rename[:40])))
    if not (restored or silinen or kept_auth or yetkili_silme or merge_getirisi
            or merge_silmesi or yetkili_rename):
        parts.append("mudahale=YOK")
    _log(" | ".join(parts))
    return "tamam"


def _reddet(tetik, sebep, ayrinti):
    """ILKE 2 — sessiz mutasyon yerine GURULTULU RED. Veri DEGISTIRILMEDI."""
    zorla = os.environ.get(ZORLA_ENV) == "1"
    _bas("!! urunler-guard (%s): %s" % (tetik, sebep))
    if ayrinti:
        _bas(ayrinti if ayrinti.startswith("    ") else "    " + ayrinti)
    _bas("   VERI DEGISTIRILMEDI — guard sessizce geri sarmaz.")
    if zorla:
        _bas("   %s=1 verildi -> RED UYARIYA cevrildi, commit DEVAM EDIYOR." % ZORLA_ENV)
        _log("%s: RED(%s) — %s=1 ile ZORLANDI, veri degistirilmedi. %s"
             % (tetik, sebep, ZORLA_ENV, ayrinti.replace("\n", " ")))
        return 0
    _bas("   CALISAN CIKIS YOLLARI (olculur — kabul testi E1-E4):")
    for kod, tarif in CIKIS_YOLLARI:
        _bas("     [%s] %s" % (kod, tarif))
    _log("%s: RED(%s) — commit REDDEDILDI, veri degistirilmedi. %s"
         % (tetik, sebep, ayrinti.replace("\n", " ")))
    return RED


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tetik", default="manuel",
                    help="tetikleyen baglam: commit|push|manuel")
    args = ap.parse_args()
    try:
        heal(args.tetik)
    except Belirsiz as e:
        return _reddet(args.tetik, e.sebep, e.ayrinti)
    except Exception as e:
        # Eskiden bu hal SESSIZCE exit 0 verirdi: guard KOSMAMIS oluyordu ama
        # commit yesil geciyordu. Koruma kosmadiysa commit GECMEZ.
        return _reddet(args.tetik, "GUARD BEKLENMEDIK HATA", repr(e))
    return 0


if __name__ == "__main__":
    sys.exit(main())

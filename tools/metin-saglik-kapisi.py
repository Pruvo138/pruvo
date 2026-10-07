#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/metin-saglik-kapisi.py — urun METIN SAGLIK kapisi (baslik + aciklama).

OLCULEN VAKA (7 Eki 2026): `d2b659fd` partisi 3 urunu BOZUK KELIMEYLE canliya cikardi:
"kaanibölümüm" (montajsiz-cift-kanatli-mentese-40-mm, boru-kelepcesi-25-mm-m4-vidali) ve
"tahliśfe" (silindir-saksi-100-mm-drenajli). parti-kontrol · mukerrer · kategori · denetim
4/4 GECIRDI: hicbiri kelimenin KENDISINE bakmiyordu = SINIF ACIGI. Ustelik parti-kontrol.py
hicbir kancaya/CI adimina BAGLI DEGIL (elle kosuluyordu; commit SONRASI kosulunca "parti yok"
der). Bu kapi bu yuzden KENDI baglantisiyla gelir: pre-commit (INDEX ekseni, commit ONCESI)
+ deploy.yml (tum katalog, taban non-growth).

KURALLAR (alanlar: baslik + aciklama; kayitta varsa kisa_aciklama/kisa-aciklama da):
  A (BLOKLAYICI, yalniz YENI PARTIDE): kelimede Turk alfabesi + ASCII disi bir LATIN harfi
    (ś ć ń ź ż ł ß ø ë é ...). Turk alfabesi = abcçdefgğhıijklmnoöprsştuüvyz + qwx (+ buyuk)
    + TDK sapkali unluler âîû (hâlinde/mekân/rüzgâr: katalogda 118+ urunde gecen MESRU
    Turkce yazim; sapka "yabanci harf" degildir).
    IZIN LISTESI TOKEN bazlidir (harf bazli DEGIL) ve ELLE YAZILMAZ: `--izin-turet` onu
    katalogdan turetir -> tools/metin-saglik-izin.json. Kanit kriteri: token >=2 FARKLI
    urunde geciyor YA DA bir urunun `marka` alaninda geciyor. Tek urunde gecen, marka
    kaniti olmayan token (tahliśfe) listeye GIREMEZ -> taban raporuna duser.
    Ek kanit (calisma aninda): token urunun KENDI `marka` degerlerinden birine esitse gecer.
  B (UYARI): >=12 harfli kelime VE katalogda TEKIL. Tekillik ekseni:
    parti kipinde HEAD katalogunda bu kelimeyi tasiyan urun sayisi 0 (yani eklenince
    katalogdaki tek kaynak bu parti olur); taban kipinde kelimeyi tasiyan urun sayisi 1.
    Turkce eklemeli dildir: uzunluk TEK BASINA hata degil, uzunluk + tekillik birlikte.
  C (UYARI): kelime icinde i/İ/ı/I BUYUK-KUCUK anormalligi: govdesi kucuk harfli kelimenin
    ortasinda buyuk İ/I ("bİr", "kIrmizi") ya da >=3 buyuk harfli BUYUK kelimede kucuk i/ı
    ("KIRMıZI"). Karisik-harf marka bicimleri (iPhone, WiFi, LiFePO4) dokunulmaz.

KIPLER:
  --pre-commit  INDEX (`:urunler.json`) vs `HEAD:urunler.json`. Parti = HEAD'de olmayan id.
                A -> rc 1 (commit DURUR). B/C -> UYARI satiri, rc 0. Index'te urunler.json
                degismediyse ATLANDI (nedeni basilir) rc 0. Okunamayan girdi -> rc 2.
  (varsayilan)  TUM katalog (deponun urunler.json'u ya da --katalog). A'ya takilan URUN sayisi
                TABAN_A_URUN'u ASARSA rc 1 (non-growth); B/C sayilari RAPOR. --tsv <yol>
                taban listesini (kural, id, token) yazar.
  --izin-turet  izin listesini katalogdan turetir (stdout'a ozet; --yaz ile dosyaya).
  --kendini-test  fikstur vakalari + mutantlar + gecici git deposunda commit-ONCESI kanit.
"""
import argparse
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from git_ortami import git_ortami, sentetik_git  # noqa: E402  (kanonik git ortami — fikstur-git-sizinti-kapisi)

KOD_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IZIN_YOLU = os.path.join(KOD_KOK, "tools", "metin-saglik-izin.json")
KANCA_YOLU = os.path.join(KOD_KOK, "tools", "kancalar", "pre-commit")

# TABAN (7 Eki 2026, 38.291 urun, izin listesi uygulanmis): A'ya takilan urun sayisi.
# Yalniz ASAGI cekilir (temizlik sonrasi); yukari cekmek kapiyi gevsetmektir.
TABAN_A_URUN = 30

ALFABE = set("abcçdefgğhıijklmnoöprsştuüvyzqwx" "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZQWX" "âîûÂÎÛ")
METIN_ALANLARI = ("baslik", "aciklama", "kisa_aciklama", "kisa-aciklama")
TOKEN_RE = re.compile(r"[^\W\d_]+")
B_ASGARI_HARF = 12
IZIN_ASGARI_URUN = 2  # izin kaniti: token >= bu kadar FARKLI urunde
I_AILESI = set("iİıI")


def anahtar(token):
    """Frekans/izin anahtari: i-ailesi katlanir (İ/I/ı -> i) + kucuk harf."""
    return token.replace("İ", "i").replace("I", "i").replace("ı", "i").lower()


def metin(urun):
    return " ".join(urun.get(a) for a in METIN_ALANLARI if isinstance(urun.get(a), str))


def tokenlar(urun):
    return TOKEN_RE.findall(unicodedata.normalize("NFC", metin(urun)))


def yabanci_harf_var(token):
    for ch in token:
        if ch not in ALFABE and ch.isalpha() and unicodedata.name(ch, "").startswith("LATIN "):
            return True
    return False


def c_anormal(token):
    if len(token) < 2:
        return False
    # Yalniz TURKCEYE OZGU harfler (İ, ı) olculur: Latin I/i karisik-harf kodlarda olagan
    # (olculdu 7 Eki: TDCi/CRDi/VVTi/MiEV/IIe/OutIn ~30 urun — hepsi mesru).
    govde = token[1:]
    harfler = [c for c in govde if c.isalpha() and c not in I_AILESI]
    if harfler and all(c.islower() for c in harfler) and "İ" in govde:
        return True
    tum = [c for c in token if c.isalpha() and c not in I_AILESI]
    if len(tum) >= 3 and all(c.isupper() for c in tum) and "ı" in token:
        return True
    return False


def marka_anahtarlari(urun):
    m = urun.get("marka")
    degerler = m if isinstance(m, list) else ([m] if isinstance(m, str) else [])
    out = set()
    for d in degerler:
        if isinstance(d, str):
            out.update(anahtar(t) for t in TOKEN_RE.findall(unicodedata.normalize("NFC", d)))
    return out


def urun_frekansi(urunler):
    """anahtar -> bu anahtari tasiyan FARKLI urun sayisi."""
    sayac = collections.Counter()
    for u in urunler:
        if isinstance(u, dict):
            sayac.update({anahtar(t) for t in tokenlar(u)})
    return sayac


def urun_bulgulari(urun, izin, frekans, tekil_esigi):
    """{'A': [token], 'B': [token], 'C': [token]} — tekil_esigi: frekans <= esik ise B."""
    kendi = marka_anahtarlari(urun)
    sonuc = {"A": [], "B": [], "C": []}
    gorulen = set()
    for t in tokenlar(urun):
        k = anahtar(t)
        if k in gorulen:
            continue
        gorulen.add(k)
        if yabanci_harf_var(t) and k not in izin and k not in kendi:
            sonuc["A"].append(t)
        if len(t) >= B_ASGARI_HARF and frekans.get(k, 0) <= tekil_esigi:
            sonuc["B"].append(t)
        if c_anormal(t):
            sonuc["C"].append(t)
    return sonuc


def izin_oku(yol=IZIN_YOLU):
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    tok = veri.get("tokenlar")
    if not isinstance(tok, dict) or not tok:
        raise ValueError("izin dosyasinda 'tokenlar' bos/gecersiz")
    return set(tok)


def izin_turet(urunler):
    urunde = collections.defaultdict(set)
    markalar = set()
    for u in urunler:
        if not isinstance(u, dict):
            continue
        markalar |= marka_anahtarlari(u)
        for t in tokenlar(u):
            if yabanci_harf_var(t):
                urunde[anahtar(t)].add(u.get("id"))
    cikti = {}
    for k in sorted(urunde):
        n = len(urunde[k])
        kanit = [x for x, ok in (("marka", k in markalar), ("frekans>=2", n >= IZIN_ASGARI_URUN)) if ok]
        if kanit:
            cikti[k] = {"urun": n, "kanit": "+".join(kanit)}
    return cikti, {k: len(v) for k, v in urunde.items() if k not in cikti}


# ----------------------------------------------------------------------------- kipler
def parti_denetle(index_urunler, head_urunler, izin):
    """(a_bulgulari, uyarilar, parti_boyu) — a/uyari: [(id, kural, token)]."""
    head_ids = {u.get("id") for u in head_urunler if isinstance(u, dict)}
    frekans = urun_frekansi(head_urunler)
    parti = [u for u in index_urunler if isinstance(u, dict) and u.get("id") not in head_ids]
    a, uyari = [], []
    for u in parti:
        b = urun_bulgulari(u, izin, frekans, tekil_esigi=0)
        uid = u.get("id") or "?"
        a += [(uid, "A", t) for t in b["A"]]
        uyari += [(uid, kural, t) for kural in ("B", "C") for t in b[kural]]
    return a, uyari, len(parti)


def taban_denetle(urunler, izin):
    """{'A': {id: [token]}, 'B': ..., 'C': ...} — tum katalog."""
    frekans = urun_frekansi(urunler)
    out = {"A": {}, "B": {}, "C": {}}
    for u in urunler:
        if not isinstance(u, dict):
            continue
        b = urun_bulgulari(u, izin, frekans, tekil_esigi=1)
        for kural in out:
            if b[kural]:
                out[kural][u.get("id") or "?"] = b[kural]
    return out


def _git(args, cwd=None):
    env = None
    if cwd is not None:  # gecici depo: kancadan miras GIT_DIR/GIT_INDEX_FILE baska depoyu olcturur
        env = git_ortami()
    return subprocess.run(["git"] + args, capture_output=True, cwd=cwd, env=env)


def pre_commit(cwd=None):
    r = _git(["diff", "--cached", "--quiet", "--", "urunler.json"], cwd)
    if r.returncode == 0:
        print("METIN-SAGLIK: ATLANDI — urunler.json index'te HEAD'e gore degismedi.")
        return 0
    if r.returncode != 1:
        print("METIN-SAGLIK: OLCULEMEDI — git diff --cached rc=%d" % r.returncode)
        return 2
    try:
        izin = izin_oku()
        idx = json.loads(_git(["show", ":urunler.json"], cwd).stdout.decode("utf-8"))
        hr = _git(["show", "HEAD:urunler.json"], cwd)
        head = json.loads(hr.stdout.decode("utf-8")) if hr.returncode == 0 else []
        if not isinstance(idx, list) or not isinstance(head, list):
            raise ValueError("urunler.json dizi degil")
    except (OSError, ValueError) as e:
        print("METIN-SAGLIK: OLCULEMEDI — %s" % e)
        return 2
    a, uyari, boy = parti_denetle(idx, head, izin)
    for uid, kural, t in uyari:
        print("UYARI %s %s: %r (%s)" % (kural, uid, t,
              "uzun+tekil kelime" if kural == "B" else "i/I harf karisimi"))
    for uid, kural, t in a:
        print("SORUN A %s: %r Turk alfabesi disi Latin harf tasiyor (izin listesinde yok)"
              % (uid, t))
    print("METIN-SAGLIK: parti=%d A=%d B/C-uyari=%d -> %s"
          % (boy, len(a), len(uyari), "KIRMIZI" if a else "YESIL"))
    return 1 if a else 0


def katalog_kipi(katalog, tsv):
    try:
        izin = izin_oku()
        with open(katalog, encoding="utf-8") as f:
            urunler = json.load(f)
        if not isinstance(urunler, list):
            raise ValueError("urunler.json dizi degil")
    except (OSError, ValueError) as e:
        print("METIN-SAGLIK TABAN: OLCULEMEDI — %s" % e)
        return 2
    t = taban_denetle(urunler, izin)
    if tsv:
        with open(tsv, "w", encoding="utf-8") as f:
            f.write("kural\tid\ttokenlar\n")
            for kural in ("A", "B", "C"):
                for uid in sorted(t[kural]):
                    f.write("%s\t%s\t%s\n" % (kural, uid, " ".join(t[kural][uid])))
    n = {k: len(v) for k, v in t.items()}
    print("METIN-SAGLIK TABAN: urun=%d A=%d (taban %d) B=%d C=%d [B/C RAPOR]"
          % (len(urunler), n["A"], TABAN_A_URUN, n["B"], n["C"]))
    for uid in sorted(t["A"]):
        print("  A %s: %s" % (uid, " ".join(t["A"][uid])))
    if n["A"] > TABAN_A_URUN:
        print("KIRMIZI: A urun sayisi tabani ASTI (%d > %d) — yeni yabanci harfli metin girdi."
              % (n["A"], TABAN_A_URUN))
        return 1
    if n["A"] < TABAN_A_URUN:
        print("NOT: A tabani asagi cekilebilir (%d < %d)." % (n["A"], TABAN_A_URUN))
    print("YESIL")
    return 0


# --------------------------------------------------------------------- kendini-test
def _u(uid, baslik, aciklama, marka=None):
    return {"id": uid, "baslik": baslik, "aciklama": aciklama, "marka": marka or []}


_HEAD = [_u("eski-%d" % i, "Braket", "Dayanikli değiştirilebilir parça, kullanılabilirlik "
            "yüksek. Citroën uyumlu.") for i in range(3)]
_IZIN = {"citroën", "škoda"}


def _vakalar(m):
    """[(ad, gecti)] — m: denetlenen modul (kendisi ya da mutant)."""
    def parti(*yeni):
        return m.parti_denetle(_HEAD + list(yeni), _HEAD, _IZIN)

    def a_var(*yeni):
        return bool(parti(*yeni)[0])

    def uyari(kural, *yeni):
        return [t for _i, k, t in parti(*yeni)[1] if k == kural]

    tahlis = _u("silindir-saksi", "Silindir Saksı", "Drenaj deliği suyu tahliśfe eder.")
    kaani1 = _u("mentese", "Menteşe", "Montajsız kaanibölümüm tasarım.")
    kaani2 = _u("kelepce", "Kelepçe", "Vidalı kaanibölümüm gövde.")
    v = [
        ("A1 tahliśfe -> KIRMIZI", a_var(tahlis)),
        ("A2 temiz uzun Turkce (değiştirilebilir/kullanılabilirlik) -> A YOK",
         not a_var(_u("yeni", "Kapak", "değiştirilebilir ve kullanılabilirlik odaklı"))),
        ("A3 izinli marka tokeni (Škoda, CITROËN) -> GECER",
         not a_var(_u("yeni", "Škoda Kapak", "CITROËN ve Škoda uyumlu."))),
        ("A4 izinsiz yabanci token (złotilik) -> KIRMIZI",
         a_var(_u("yeni", "Kapak", "złotilik parça"))),
        ("A5 urunun kendi markasi kanittir (Hähnel, marka alaninda) -> GECER",
         not a_var(_u("yeni", "Hähnel Adaptör", "Hähnel MK200.", marka=["Hähnel"]))),
        ("A6 sapkali Turkce (hâlinde/mekân/rüzgâr) -> GECER",
         not a_var(_u("yeni", "Askı", "hâlinde mekân rüzgâr dâhil"))),
        ("A7 HEAD'de zaten olan urun parti DISI (bloklamaz)",
         not m.parti_denetle(_HEAD + [tahlis], _HEAD + [tahlis], _IZIN)[0]),
        ("B1 kaanibölümüm (2 partili urunde, HEAD'de yok) -> UYARI x2",
         uyari("B", kaani1, kaani2).count("kaanibölümüm") == 2),
        ("B2 HEAD'de gecen uzun kelime (değiştirilebilir) -> UYARI YOK",
         not uyari("B", _u("yeni", "Kapak", "değiştirilebilir kapak"))),
        ("B3 kisa yeni kelime (<12 harf) -> UYARI YOK",
         not uyari("B", _u("yeni", "Kapak", "zırtapozlu"))),
        ("C1 'bİr' -> UYARI", uyari("C", _u("yeni", "Kapak", "bİr kapak")) == ["bİr"]),
        ("C2 'KIRMıZI' -> UYARI", uyari("C", _u("yeni", "KIRMıZI", "kapak")) == ["KIRMıZI"]),
        ("C3 iPhone/WiFi/İstanbul/IKEA/TDCi/MiEV/IIe/OutIn -> UYARI YOK",
         not uyari("C", _u("yeni", "iPhone WiFi", "İstanbul IKEA LiFePO4 TDCi MiEV IIe OutIn"))),
        ("T1 taban: tahliśfe A'ya, kaanibölümüm tekil degil (2 urun) B'ye DUSMEZ",
         "silindir-saksi" in m.taban_denetle(_HEAD + [tahlis, kaani1, kaani2], _IZIN)["A"]
         and "mentese" not in m.taban_denetle(_HEAD + [kaani1, kaani2], _IZIN)["B"]),
        ("T2 taban: tek urunde gecen uzun kelime B'ye duser",
         "silindir-saksi" in m.taban_denetle(
             _HEAD + [_u("silindir-saksi", "Saksı", "kaanibölümümler")], _IZIN)["B"]),
        ("I1 izin turetimi: tek urunlu marka-disi token (tahliśfe) listeye GIRMEZ",
         "tahliśfe" not in m.izin_turet(_HEAD + [tahlis])[0]),
        ("I2 izin turetimi: >=2 urunde gecen (citroën) GIRER",
         "citroën" in m.izin_turet(_HEAD)[0]),
    ]
    return v


def _kanca_bagli(kanca_metni):
    """pre-commit'te kapi INDEX kipinde cagriliyor ve rc!=0 commit'i durduruyor mu."""
    return ('metin-saglik-kapisi.py"' in kanca_metni
            and '"$pruvo_metin" --pre-commit' in kanca_metni
            and re.search(r'if \[ "\$pruvo_metin_rc" -ne 0 \]; then\n(?:.*\n){0,4}?\s*exit 1',
                          kanca_metni) is not None)


MUTANTLAR = [
    ("A kolu silindi",
     '        if yabanci_harf_var(t) and k not in izin and k not in kendi:\n',
     '        if False:\n'),
    ("B kolu silindi",
     '        if len(t) >= B_ASGARI_HARF and frekans.get(k, 0) <= tekil_esigi:\n',
     '        if False:\n'),
    ("C kolu silindi", '        if c_anormal(t):\n', '        if False:\n'),
    ("alfabe genisletildi (ś eklendi)",
     '"âîûÂÎÛ")\n', '"âîûÂÎÛś")\n'),
    ("izin kaniti gevsedi (tek urun yeter)",
     'IZIN_ASGARI_URUN = 2  # izin kaniti: token >= bu kadar FARKLI urunde\n',
     'IZIN_ASGARI_URUN = 1  # mutant\n'),
]


def _modul_yukle(yol, ad):
    import importlib.util
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _git_deposunda_kanit(gecici):
    """Gercek git deposunda: bozuk metin STAGE'liyken (commit ONCESI) rc 1; ayni metin
    commit'lendikten sonra kipin 'ATLANDI' dedigini de gosterir (d2b659fd'deki bos donus)."""
    os.makedirs(gecici)

    def g(*a):
        if sentetik_git(gecici, *a, capture_output=True).returncode != 0:
            raise RuntimeError("git %s basarisiz" % " ".join(a))
    g("init", "-q")
    yol = os.path.join(gecici, "urunler.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(_HEAD, f, ensure_ascii=False)
    g("add", "urunler.json")
    g("commit", "-q", "-m", "taban")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump([_u("silindir-saksi", "Saksı", "suyu tahliśfe eder")] + _HEAD, f,
                  ensure_ascii=False)
    g("add", "urunler.json")
    once = _sessiz(pre_commit, gecici)
    g("commit", "-q", "--no-verify", "-m", "parti")
    sonra = _sessiz(pre_commit, gecici)
    return once, sonra


def _sessiz(fn, *a):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a)
    return rc, buf.getvalue()


def kendini_test():
    sonuc = []
    for ad, ok in _vakalar(sys.modules[__name__]):
        sonuc.append((ad, ok))
    gecici = tempfile.mkdtemp(prefix="metin-saglik-test-")
    try:
        (rc1, c1), (rc2, c2) = _git_deposunda_kanit(os.path.join(gecici, "depo"))
        sonuc.append(("G1 commit ONCESI (index) bozuk parti -> rc 1", rc1 == 1 and "tahliśfe" in c1))
        sonuc.append(("G2 commit SONRASI ayni kip ATLANDI der (bos donus = yanlis an)",
                      rc2 == 0 and "ATLANDI" in c2))
        with open(__file__, encoding="utf-8") as f:
            kaynak = f.read()
        olen = 0
        for i, (ad, capa, yeni) in enumerate(MUTANTLAR):
            if kaynak.count(capa) != 1:
                sonuc.append(("M%d capa TEK kez tutmadi: %s (OLCULEMEDI)" % (i + 1, ad), False))
                continue
            yol = os.path.join(gecici, "mutant_%d.py" % i)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa, yeni))
            dusen = [a for a, ok in _vakalar(_modul_yukle(yol, "mutant_%d" % i)) if not ok]
            olen += bool(dusen)
            sonuc.append(("M%d mutant '%s' -> KIRMIZI (%d vaka dustu)" % (i + 1, ad, len(dusen)),
                          bool(dusen)))
        try:
            with open(KANCA_YOLU, encoding="utf-8") as f:
                kanca = f.read()
        except OSError:
            kanca = ""
        sonuc.append(("K1 pre-commit kancasi kapiyi INDEX kipinde cagiriyor + rc!=0 durduruyor",
                      _kanca_bagli(kanca)))
        sil = kanca.replace('"$pruvo_metin" --pre-commit', '"$pruvo_metin" --yok')
        sonuc.append(("KM1 kanca adimi silinmis mutant -> KIRMIZI", not _kanca_bagli(sil)))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    for ad, ok in sonuc:
        print("%s %s" % ("GECTI " if ok else "KIRMIZI", ad))
    kirmizi = [a for a, ok in sonuc if not ok]
    print("VAKA=%d GECTI=%d KIRMIZI=%d MUTANT=%d/%d"
          % (len(sonuc), len(sonuc) - len(kirmizi), len(kirmizi), olen, len(MUTANTLAR)))
    return 1 if kirmizi else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pre-commit", action="store_true")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--izin-turet", action="store_true")
    ap.add_argument("--yaz", action="store_true", help="--izin-turet ciktisini dosyaya yaz")
    ap.add_argument("--katalog", default=os.path.join(KOD_KOK, "urunler.json"))
    ap.add_argument("--tsv", help="taban listesini bu yola yaz (commit EDILMEZ)")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    if a.pre_commit:
        return pre_commit()
    if a.izin_turet:
        with open(a.katalog, encoding="utf-8") as f:
            urunler = json.load(f)
        izin, disarida = izin_turet(urunler)
        print("IZIN: %d token (kanitli) · disarida kalan tek-urunlu: %d" % (len(izin), len(disarida)))
        for k in sorted(disarida):
            print("  DISARIDA %s (%d urun)" % (k, disarida[k]))
        if a.yaz:
            veri = {"_aciklama": "tools/metin-saglik-kapisi.py --izin-turet --yaz ile TURETILIR; "
                                 "elle satir ekleme. Kanit: >=2 farkli urun ya da marka alani.",
                    "katalog_urun": len(urunler), "tokenlar": izin}
            with open(IZIN_YOLU, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, indent=1, sort_keys=True)
                f.write("\n")
        return 0
    return katalog_kipi(a.katalog, a.tsv)


if __name__ == "__main__":
    sys.exit(main())

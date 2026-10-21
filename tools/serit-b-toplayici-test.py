#!/usr/bin/env python3
"""SERIT B toplayici kabul bataryasi — nobet.yml `serit-b` = dilimlerin TEK hukmu mu.

21 Eki 2026 (cip kral-serit-b-matrix): tek `serit-b` isi (141 dk, 256 sirali adim)
`serit-b-1..N` ardisik dilimlerine bolundu; `serit-b` adi TOPLAYICI iste kaldi cunku
~60 arac/belge bu adi okur. Toplayici yanlis kurulursa ad yasar ama hukum OLUR:
bir dilim `needs`'ten duserse onun kirmizisi `serit-b`ye hic ulasmaz; `always()`
yoksa dusen dilim toplayiciyi `skipped` yapar ve "kirmizi yok" gorunur (fail-open).

AG YOK, canli dosyaya YAZILMAZ: mutantlar nobet.yml metninin BELLEKTEKI kopyasina
uygulanir; once mutasyonsuz metin TABAN olarak olculur (taban kirmiziysa her mutant
"oldu" gorunurdu).

Iddialar:
  T1 dilim kumesi (`serit-b-<n>`) >= 2 ve toplayici `needs` == dilim kumesi
  T2 toplayici `if:` `always()` tasir; dilimlerde `needs:` YOK (paralel kosarlar)
  T3 toplayici adimi `toJSON(needs)` uzerinden dilim SAYISINI ve her `.result ==
     "success"` kosulunu olcer; `continue-on-error` YOK
  T4 her dilimin ilk 4 adimi (kurulum) BIREBIR ayni
  T5 sira bagimliligi: kanonik duzlem -> mimar bataryalari ve kanca-kur -> kanca
     nobeti AYNI dilimde, dogru sirada; kanca ikilisi dilimin sonunda
Mutantlar: M1 bir dilim `needs`'ten cikar · M2 `.result == "success"` kontrolu silinir ·
  M3 `if: always()` silinir · M4 sayi kontrolu 1 eksik · M5 toplayici adimina
  `continue-on-error: true` · M6 kanca-kur onceki dilime tasinir.
Cikti: `SONUC: YESIL|KIRMIZI iddia x/y mutant k/m`; rc 0 yalniz hepsi tamamsa.
"""
import os
import re
import sys

import yaml

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOBET_YML = os.path.join(KOK, ".github", "workflows", "nobet.yml")
TOPLAYICI = "serit-b"
DILIM_RE = re.compile(r"^serit-b-(\d+)$")
KURULUM = 4
# (onkosul adim run alt dizgesi, ona bagli adimlarin run alt dizgeleri)
SIRA = (
    ("ln -sfn \"$GITHUB_WORKSPACE\" /Users/okan/dev/pruvo",
     ("tools/mimar-kilit-test.py", "tools/mimar-kapi-mutasyon-test.py",
      "tools/mimar-agent-jev-test.py")),
    ("tools/kanca-kur.py", ("tools/kanca-nobeti.py",)),
)


def _run(adim):
    return adim.get("run") or "" if isinstance(adim, dict) else ""


def denetle(metin):
    """{iddia: [hata, ...]} — bos liste = iddia YESIL."""
    h = {k: [] for k in ("T1", "T2", "T3", "T4", "T5")}
    try:
        jobs = yaml.safe_load(metin)["jobs"]
    except Exception as e:  # okunamayan metin her iddiayi KIRMIZI yakar
        return {k: ["nobet.yml okunamadi: %s" % e] for k in h}
    dilimler = sorted((k for k in jobs if DILIM_RE.match(k)),
                      key=lambda k: int(DILIM_RE.match(k).group(1)))
    top = jobs.get(TOPLAYICI)
    if not isinstance(top, dict):
        return {k: ["toplayici `serit-b` isi YOK"] for k in h}
    needs = top.get("needs")
    needs = [needs] if isinstance(needs, str) else list(needs or [])
    if len(dilimler) < 2:
        h["T1"].append("dilim sayisi %d (< 2)" % len(dilimler))
    if sorted(needs) != sorted(dilimler):
        h["T1"].append("needs %s != dilimler %s" % (sorted(needs), dilimler))

    if "always()" not in str(top.get("if", "")):
        h["T2"].append("toplayici `if:` always() TASIMIYOR: %r" % top.get("if"))
    for d in dilimler:
        if jobs[d].get("needs"):
            h["T2"].append("%s `needs:` tasiyor (paralel degil)" % d)

    adimlar = top.get("steps") or []
    govde = " ".join(_run(a) + " " + " ".join(str(v) for v in (a.get("env") or {}).values())
                     for a in adimlar if isinstance(a, dict))
    if "toJSON(needs)" not in govde:
        h["T3"].append("toplayici `toJSON(needs)` okumuyor")
    if '.result == "success"' not in govde:
        h["T3"].append('toplayici her `.result == "success"` kosulunu olcmuyor')
    m = re.search(r"length == (\d+)", govde)
    if not m or int(m.group(1)) != len(dilimler):
        h["T3"].append("dilim sayisi kontrolu %s != %d" % (m.group(1) if m else "YOK", len(dilimler)))
    if top.get("continue-on-error") or any(isinstance(a, dict) and a.get("continue-on-error")
                                           for a in adimlar):
        h["T3"].append("toplayicida continue-on-error VAR (fail-open)")

    if dilimler:
        kur = (jobs[dilimler[0]].get("steps") or [])[:KURULUM]
        if len(kur) < KURULUM or not any("actions/checkout" in str(a.get("uses", "")) for a in kur):
            h["T4"].append("%s kurulum blogu eksik" % dilimler[0])
        for d in dilimler[1:]:
            if (jobs[d].get("steps") or [])[:KURULUM] != kur:
                h["T4"].append("%s kurulumu %s ile BIREBIR degil" % (d, dilimler[0]))

    yer = {}
    for d in dilimler:
        for i, a in enumerate(jobs[d].get("steps") or []):
            yer.setdefault(_run(a), (d, i, len(jobs[d]["steps"])))

    def bul(alt):
        return [v for k, v in yer.items() if alt in k]

    for onkosul, bagimlilar in SIRA:
        o = bul(onkosul)
        if len(o) != 1:
            h["T5"].append("onkosul `%s` %d yerde" % (onkosul, len(o)))
            continue
        for b in bagimlilar:
            for d, i, _n in bul(b):
                if d != o[0][0] or i <= o[0][1]:
                    h["T5"].append("`%s` (%s#%d) onkosul `%s` (%s#%d) ardinda degil"
                                   % (b, d, i, onkosul, o[0][0], o[0][1]))
            if not bul(b):
                h["T5"].append("bagimli `%s` dilimlerde YOK" % b)
    kn = bul("tools/kanca-nobeti.py")
    if kn and kn[0][1] < kn[0][2] - 2:
        h["T5"].append("kanca ikilisi dilimin sonunda degil (%s#%d/%d)" % kn[0])
    return h


def _kanca_kur_tasi(metin):
    """M6: kanca-kur adimini onceki dilimin sonuna tasi."""
    adim = re.search(r"\n      - name: \"Kanca kablolamasi[^\n]*\n(?:        [^\n]*\n)+", metin)
    if not adim:
        return metin
    metin = metin.replace(adim.group(0), "\n", 1)
    son = max(re.findall(r"^  serit-b-(\d+):$", metin, re.M), key=int)
    baslik = "\n  serit-b-%s:\n" % son
    return metin.replace(baslik, adim.group(0) + baslik, 1)


MUTANTLAR = (
    ("M1", "bir dilim needs'ten cikar", "T1",
     lambda m: m.replace("needs: [serit-b-1, serit-b-2, serit-b-3, serit-b-4]",
                         "needs: [serit-b-1, serit-b-2, serit-b-4]", 1)),
    ("M2", ".result == success kontrolu silinir", "T3",
     lambda m: m.replace(' and all(.[]; .result == "success")', "", 1)),
    ("M3", "if: always() silinir", "T2",
     lambda m: m.replace("    if: ${{ always() }}\n", "", 1)),
    ("M4", "sayi kontrolu 1 eksik", "T3",
     lambda m: m.replace("length == 4", "length == 3", 1)),
    ("M5", "toplayici adimina continue-on-error", "T3",
     lambda m: m.replace("        env:\n          DILIM_SONUCLARI:",
                         "        continue-on-error: true\n        env:\n          DILIM_SONUCLARI:", 1)),
    ("M6", "kanca-kur onceki dilime tasinir", "T5", _kanca_kur_tasi),
)


def main():
    with open(NOBET_YML, encoding="utf-8") as f:
        canli = f.read()
    hata = 0
    taban = denetle(canli)
    for k, v in taban.items():
        print("%s %s%s" % ("YESIL" if not v else "KIRMIZI", k, "" if not v else " | " + "; ".join(v)))
    iddia_ok = sum(1 for v in taban.values() if not v)
    if iddia_ok != len(taban):
        hata += 1
    oldu = 0
    for kimlik, aciklama, hedef, mut in MUTANTLAR:
        metin = mut(canli)
        if metin == canli:
            print("KACTI %s (%s) -> mutant UYGULANAMADI (capa yok)" % (kimlik, aciklama))
            hata += 1
            continue
        sonuc = denetle(metin)
        yakalandi = bool(sonuc[hedef])
        oldu += yakalandi
        print("%s %s (%s) -> %s %s" % ("YAKALANDI" if yakalandi else "KACTI", kimlik, aciklama,
                                       hedef, "; ".join(sonuc[hedef])[:160]))
        if not yakalandi:
            hata += 1
    print("SONUC: %s iddia %d/%d mutant %d/%d" % ("YESIL" if hata == 0 else "KIRMIZI",
                                                  iddia_ok, len(taban), oldu, len(MUTANTLAR)))
    return 0 if hata == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Kabul testi: .github/workflows/d1-uzlastirici.yml icindeki "ONARILAMADI" adiminin
`if:` kosulunu OLCER — PyYAML varsa onunla, yoksa duz metin (regex) ile ayiklar,
kucuk bir GitHub-ifade degerlendiricisiyle 5 dunyada calistirir ve YENI kosulun
dogru (fail-closed) davrandigini + ESKI kosulun (kontrol mutanti) vaka-2'de
yanlis-kirmizi urettigini ispatlar.

Kok neden (kosum 31214568441, 20:08Z, 7 Agu 2026 OLCULDU):
  Eski kosul: failure() && steps.olcum.outputs.sapma == 'var'
  `failure()` bu job'daki HERHANGI onceki adim dustuyse true olur. Cron/elle
  kolunda "(1) Sapma gorunurlugu" adimi sapma=='var' oldugunda KASITLI exit 1
  verir (GORUNURLUK sinyali, degismedi) -> bu adim onu kendi failure() girdisi
  sanip "onarim/teyit DUSTU" diye YANLIS beyan ediyordu; oysa o kosumda
  onarim+teyit ikisi de success idi (durum: hash UYUSMAZ 0 | EKSIK 0 | FAZLA 0).

  Yeni kosul: always() && steps.olcum.outputs.sapma == 'var' && steps.teyit.outcome != 'success'
  GERCEK teyit sonucunu okur; fail-closed (skipped/cancelled de != 'success').
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_PATH = os.path.join(ROOT, ".github", "workflows", "d1-uzlastirici.yml")
STEP_NAME_MARKER = "ONARILAMADI"

ESKI_KOSUL_METNI = "failure() && steps.olcum.outputs.sapma == 'var'"


# ══════════════════════════════════════════════════════════════════════════
# 1) YAML'DAN (veya duz metinden) `if:` KOSULUNU AYIKLA
# ══════════════════════════════════════════════════════════════════════════
def kosulu_ayikla_yaml(path):
    try:
        import yaml
    except ImportError:
        return None
    with open(path, "r", encoding="utf-8") as f:
        veri = yaml.safe_load(f)
    for job in veri.get("jobs", {}).values():
        for step in job.get("steps", []):
            ad = step.get("name", "") or ""
            if STEP_NAME_MARKER in ad:
                return step.get("if")
    return None


def kosulu_ayikla_duz_metin(path):
    with open(path, "r", encoding="utf-8") as f:
        icerik = f.read()
    # Adim basligini bul, hemen ardindan gelen `if:` satirini al.
    desen = re.compile(
        r'-\s*name:\s*"[^"\n]*' + re.escape(STEP_NAME_MARKER) + r'[^"\n]*"\s*\n\s*if:\s*(.+)'
    )
    eslesme = desen.search(icerik)
    if not eslesme:
        return None
    return eslesme.group(1).strip()


def kosulu_ayikla(path):
    kosul = kosulu_ayikla_yaml(path)
    if kosul is not None:
        return kosul, "pyyaml"
    kosul = kosulu_ayikla_duz_metin(path)
    if kosul is not None:
        return kosul, "duz-metin"
    raise RuntimeError(f"'{STEP_NAME_MARKER}' adimi veya 'if:' satiri bulunamadi: {path}")


# ══════════════════════════════════════════════════════════════════════════
# 2) KUCUK GITHUB-IFADE DEGERLENDIRICISI
#    Desteklenen alt kume: always(), failure(), &&, ||, ==, !=,
#    steps.X.outcome, steps.X.outputs.Y, 'string literal'
# ══════════════════════════════════════════════════════════════════════════
TOKEN_DESENI = re.compile(
    r"""\s*(?:
        (?P<AND>&&) |
        (?P<OR>\|\|) |
        (?P<NEQ>!=) |
        (?P<EQ>==) |
        (?P<LPAREN>\() |
        (?P<RPAREN>\)) |
        (?P<STRING>'[^']*') |
        (?P<IDENT>[A-Za-z_][A-Za-z0-9_.]*)
    )""",
    re.VERBOSE,
)


def tokenlere_ayir(ifade):
    tokenler = []
    pos = 0
    while pos < len(ifade):
        if ifade[pos].isspace():
            pos += 1
            continue
        m = TOKEN_DESENI.match(ifade, pos)
        if not m or m.end() == pos:
            raise ValueError(f"Tokenize edilemedi: {ifade!r} (pozisyon {pos})")
        tur = m.lastgroup
        deger = m.group(tur)
        tokenler.append((tur, deger))
        pos = m.end()
    return tokenler


class Degerlendirici:
    """Recursive-descent parser + evaluator. `world` dict'inden okur:
    world['steps'][ad]['outcome'] / world['steps'][ad]['outputs'][anahtar]
    world['failure'] -> bool (bu job'da failure() ne doner)
    """

    def __init__(self, tokenler, world):
        self.tokenler = tokenler
        self.pos = 0
        self.world = world

    def bak(self):
        return self.tokenler[self.pos] if self.pos < len(self.tokenler) else (None, None)

    def yut(self, beklenen_tur=None):
        tur, deger = self.bak()
        if beklenen_tur and tur != beklenen_tur:
            raise ValueError(f"Beklenen {beklenen_tur}, bulunan {tur} ({deger!r})")
        self.pos += 1
        return tur, deger

    def degerlendir(self):
        sonuc = self.or_ifade()
        if self.pos != len(self.tokenler):
            raise ValueError(f"Fazladan token: {self.tokenler[self.pos:]}")
        return sonuc

    def or_ifade(self):
        sol = self.and_ifade()
        while self.bak()[0] == "OR":
            self.yut("OR")
            sag = self.and_ifade()
            sol = bool(sol) or bool(sag)
        return sol

    def and_ifade(self):
        sol = self.karsilastirma()
        while self.bak()[0] == "AND":
            self.yut("AND")
            sag = self.karsilastirma()
            sol = bool(sol) and bool(sag)
        return sol

    def karsilastirma(self):
        sol = self.temel()
        tur = self.bak()[0]
        if tur in ("EQ", "NEQ"):
            self.yut(tur)
            sag = self.temel()
            esit = sol == sag
            return esit if tur == "EQ" else (not esit)
        return sol

    def temel(self):
        tur, deger = self.bak()
        if tur == "LPAREN":
            self.yut("LPAREN")
            ic = self.or_ifade()
            self.yut("RPAREN")
            return ic
        if tur == "STRING":
            self.yut("STRING")
            return deger[1:-1]
        if tur == "IDENT":
            self.yut("IDENT")
            if self.bak()[0] == "LPAREN":
                self.yut("LPAREN")
                self.yut("RPAREN")
                return self._fonksiyon_cagir(deger)
            return self._tanimlayici_coz(deger)
        raise ValueError(f"Beklenmeyen token: {tur} {deger!r}")

    def _fonksiyon_cagir(self, ad):
        if ad == "always":
            return True
        if ad == "failure":
            return bool(self.world.get("failure", False))
        raise ValueError(f"Bilinmeyen fonksiyon: {ad}()")

    def _tanimlayici_coz(self, yol):
        parcalar = yol.split(".")
        if parcalar[0] != "steps":
            raise ValueError(f"Desteklenmeyen tanimlayici: {yol}")
        adim_adi = parcalar[1]
        alan = self.world.get("steps", {}).get(adim_adi, {})
        if parcalar[2] == "outcome":
            return alan.get("outcome")
        if parcalar[2] == "outputs":
            return alan.get("outputs", {}).get(parcalar[3])
        raise ValueError(f"Desteklenmeyen alan: {yol}")


def kosulu_calistir(ifade, world):
    tokenler = tokenlere_ayir(ifade)
    return bool(Degerlendirici(tokenler, world).degerlendir())


# ══════════════════════════════════════════════════════════════════════════
# 3) 5 DUNYA — sapma/teyit kombinasyonlari (cron/elle kolu, kadans_kolu=false
#    varsayilan; bu yuzden "(1) Sapma gorunurlugu" adimi sapma=='var' oldugunda
#    KOSULSUZ exit 1 verir -> failure_context = (sapma == 'var'))
# ══════════════════════════════════════════════════════════════════════════
def dunya_kur(sapma, teyit_outcome):
    return {
        "failure": (sapma == "var"),  # "(1) Sapma gorunurlugu" adiminin gercek etkisi
        "steps": {
            "olcum": {"outputs": {"sapma": sapma}},
            "teyit": {"outcome": teyit_outcome},
        },
    }


VAKALAR = [
    # (no, aciklama, sapma, teyit_outcome, beklenen_ateslesin_mi)
    (1, "sapma=yok, teyit=success", "yok", "success", False),
    (2, "sapma=var, teyit=success (bugunku hatanin kapandigi vaka)", "var", "success", False),
    (3, "sapma=var, teyit=failure", "var", "failure", True),
    (4, "sapma=var, teyit=skipped (fail-closed)", "var", "skipped", True),
    (5, "sapma=var, teyit=cancelled (fail-closed)", "var", "cancelled", True),
]


def main():
    kosul, kaynak = kosulu_ayikla(WORKFLOW_PATH)
    print(f"[kaynak={kaynak}] YENI_KOSUL(dosyadan)={kosul!r}")

    iddia_no = 0
    basarisiz = []

    for no, aciklama, sapma, teyit_outcome, beklenen in VAKALAR:
        iddia_no += 1
        world = dunya_kur(sapma, teyit_outcome)
        sonuc = kosulu_calistir(kosul, world)
        durum = "OK" if sonuc == beklenen else "FAIL"
        print(
            f"IDDIA {iddia_no} (vaka {no}: {aciklama}): "
            f"beklenen_ateslesin={beklenen} gercek_ateslesin={sonuc} -> {durum}"
        )
        if sonuc != beklenen:
            basarisiz.append((no, aciklama, beklenen, sonuc))

    # ══════════════════════════════════════════════════════════════════════
    # KONTROL MUTANTI: ESKI kosul ayni degerlendiriciden gecirilince vaka-2'de
    # ATESLEMELI (yanlis-kirmizi uretmeli) -> testin ayirt edici oldugunun kaniti.
    # ══════════════════════════════════════════════════════════════════════
    iddia_no += 1
    vaka2 = VAKALAR[1]
    world_vaka2 = dunya_kur(vaka2[2], vaka2[3])
    eski_sonuc = kosulu_calistir(ESKI_KOSUL_METNI, world_vaka2)
    mutant_dustu = eski_sonuc is True  # eski kosul vaka-2'de YANLIS-KIRMIZI uretti mi
    durum = "OK (mutant dustu — eski kod vaka-2'de yanlis-kirmizi uretiyordu)" if mutant_dustu else "FAIL (mutant DUSMEDI — test ayirt edici degil)"
    print(
        f"IDDIA {iddia_no} (KONTROL MUTANTI, eski kosul={ESKI_KOSUL_METNI!r}, vaka 2): "
        f"eski_kosul_atesledi={eski_sonuc} -> {durum}"
    )
    if not mutant_dustu:
        basarisiz.append(("kontrol-mutanti", "eski kosul vaka-2'de ateslemedi", True, eski_sonuc))

    print(f"ESKI_KOSUL={ESKI_KOSUL_METNI}")
    print(f"YENI_KOSUL={kosul}")

    if basarisiz:
        print(f"IDDIA={iddia_no} DUSEN={len(basarisiz)} -> {basarisiz}")
        sys.exit(1)

    print(f"IDDIA={iddia_no} HEPSI_GECTI")
    sys.exit(0)


if __name__ == "__main__":
    main()

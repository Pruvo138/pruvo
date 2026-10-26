#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HOMONIM MARKA kabul bataryasi — baslik kolu KAPALI 4 marka (Mini, Rover, Alpine, Sigma).

Hukum (26 Eki 2026, BaBa tik 188/196): bu 4 markanin adi baslikta baska bir seyi de adlandirir
(iPad mini / mini boy · Range Rover = Land Rover · Alpine ses sistemi · Sigma ROX / Subaru
Sigma). Uyelik YALNIZ marka[]/uyum'dan gelir; mesru uyeler VERIYLE tasinir (A310 x3 Renault|
Alpine, Sigma Art lens Canon+Sigma). Tek kaynak: index.html `var BASLIK_KOLU_KAPALI = [...]`
(JS baslikMarkalari + arama.baslik_marka_uyumlari + marka_model_build.baslik_uyelikleri).

  H1 — 4 kapali markada SAYFA kumesi == UYELIK kumesi == ARAMA kumesi (baslik-yalniz 0).
  H2 — sayilar SABIT (olculdu 26 Eki, katalog 40925): SAYILAR.
  H3 — VERI: 3 A310 kaydi Alpine'de, Sigma Art lens Sigma'da (uyelik kolundan).
  H4 — KONTROL MARKA: baslik kolu digerlerinde ACIK — GoPro aramasinda baslik-yalniz uye > 0.
  H5 — TEK KAYNAK: MarkaEvreni.baslik_kapali == arama.baslik_kolu_kapali() == 4 marka.

  M1 — kapali liste BOS                      -> beyan {H1, H2, H5}
  M2 — Rover listeden cikar                  -> beyan {H1, H2, H5}
  KONTROL-MUTANT — literal bosluksuz yazilir -> beyan {} (ayni JSON, hepsi YESIL)

Mutasyon yalniz BELLEKTEKI index.html metnine ve arama'nin bellekteki kumesine uygulanir;
canli index.html'in sha256'si bas/son karsilastirilir. rc=0 hepsi gectiyse, aksi 1.
"""
import hashlib
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
INDEX = os.path.join(KOK, "index.html")
URUNLER = os.path.join(KOK, "urunler.json")
sys.path.insert(0, TOOLS)

import arama                                                        # noqa: E402
import marka_model_build as mmb                                     # noqa: E402

KAPALI = frozenset({"Mini", "Rover", "Alpine", "Sigma"})
LITERAL = 'var BASLIK_KOLU_KAPALI = ["Mini", "Rover", "Alpine", "Sigma"];'
# OLCULDU 26 Eki 2026 (dal kral/homonim-marka, katalog 40925): sayfa = uyelik = arama.
SAYILAR = {"Mini": 138, "Rover": 3, "Alpine": 8, "Sigma": 4}
VERI = {"Alpine": ("renault-alpine-a310-koltuk-kolu-kilavuzu",
                   "renault-alpine-a310-on-far-contasi",
                   "renault-alpine-a310-kapi-kolu-kilavuz-burcu"),
        "Sigma": ("canon-ef-sigma-art-18-35mm-odak-zum-disli-halkasi",)}
KONTROL_MARKA = "GoPro"


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def olc(index_html, urunler, arama_kapali):
    """Marka -> {sayfa, uye, arama} id kumeleri (4 kapali + kontrol marka)."""
    eski = arama._BASLIK_KOLU_KAPALI
    arama._BASLIK_KOLU_KAPALI = arama_kapali
    try:
        evren = mmb.MarkaEvreni(index_html)
        ek = mmb.cip_evreni_markalari(urunler, index_html)
        veri = mmb.gruplandir(urunler, evren, ek)
        ek_normlu = mmb.ek_marka_normlu(ek)
        bellek = {}

        def kanon(dizge):
            if dizge not in bellek:
                bellek[dizge] = mmb.marka_adi_kanonu(dizge, evren, ek_normlu)
            return bellek[dizge]

        hedefler = sorted(KAPALI) + [KONTROL_MARKA]
        sonuc = {m: {"sayfa": set(), "uye": set(), "arama": set()} for m in hedefler}
        for m in hedefler:
            d = veri.get(m)
            if d:
                for kaynak in ([g["urunler"] for g in d["gruplar"].values()]
                               + [d["marka_only"], d.get("ikincil", [])]):
                    sonuc[m]["sayfa"].update(p["id"] for p in kaynak if p.get("id"))
        for p in urunler:
            pid = p.get("id")
            if not pid:
                continue
            uyeler = mmb.marka_uyelikleri(p.get("marka") or [], evren, ek)
            bu = arama.baslik_marka_uyumlari(p.get("baslik"), kanon)
            for m in hedefler:
                if m in uyeler:
                    sonuc[m]["uye"].add(pid)
                if arama.marka_sorgusu_esler(m, uyeler, bu):
                    sonuc[m]["arama"].add(pid)
        return sonuc, evren.baslik_kapali, arama.baslik_kolu_kapali()
    finally:
        arama._BASLIK_KOLU_KAPALI = eski


def eksenler(olcum, sessiz=False):
    s, ev_kapali, ar_kapali = olcum
    h1 = all(s[m]["sayfa"] == s[m]["uye"] == s[m]["arama"] for m in KAPALI)
    h2 = all(len(s[m]["sayfa"]) == SAYILAR[m] and len(s[m]["arama"]) == SAYILAR[m]
             for m in KAPALI)
    h3 = all(set(ids) <= s[m]["uye"] for m, ids in VERI.items())
    kontrol_fazla = s[KONTROL_MARKA]["arama"] - s[KONTROL_MARKA]["uye"]
    h4 = len(kontrol_fazla) > 0 and s[KONTROL_MARKA]["uye"] <= s[KONTROL_MARKA]["arama"]
    h5 = ev_kapali == ar_kapali == KAPALI
    if not sessiz:
        for m in sorted(KAPALI):
            print("H1/H2 %-6s sayfa=%d uye=%d arama=%d (beklenen %d) baslik-yalniz sayfa=%d "
                  "arama=%d" % (m, len(s[m]["sayfa"]), len(s[m]["uye"]), len(s[m]["arama"]),
                               SAYILAR[m], len(s[m]["sayfa"] - s[m]["uye"]),
                               len(s[m]["arama"] - s[m]["uye"])))
        for m, ids in VERI.items():
            print("H3 %s veri uyesi %d/%d eksik=%s" % (m, len(set(ids) & s[m]["uye"]), len(ids),
                                                     sorted(set(ids) - s[m]["uye"])))
        print("H4 kontrol %s uye=%d arama=%d baslik-yalniz=%d" % (
            KONTROL_MARKA, len(s[KONTROL_MARKA]["uye"]), len(s[KONTROL_MARKA]["arama"]),
            len(kontrol_fazla)))
        print("H5 tek kaynak evren=%s arama=%s" % (sorted(ev_kapali), sorted(ar_kapali)))
    return {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5}


def _mutant(ad, index_html, urunler, yeni_literal, beyan):
    if index_html.count(LITERAL) != 1:
        print("%s UYGULANAMADI (literal %d kez) -> KUSUR" % (ad, index_html.count(LITERAL)))
        return False
    m_html = index_html.replace(LITERAL, yeni_literal)
    m_kapali = arama.baslik_kolu_kapali_ayikla(m_html)
    olcum = olc(m_html, urunler, m_kapali)
    kirmizi = {k for k, v in eksenler(olcum, sessiz=True).items() if not v}
    esit = kirmizi == set(beyan)
    ozet = " ".join("%s=%d/%d" % (m, len(olcum[0][m]["sayfa"]), len(olcum[0][m]["arama"]))
                    for m in sorted(KAPALI))
    print("%s kirmizi=%s beyan=%s -> %s · sayfa/arama %s" % (
        ad, sorted(kirmizi), sorted(beyan), "ESIT" if esit else "ESIT DEGIL (KUSUR)", ozet))
    return esit


def main():
    sha_bas = _sha(INDEX)
    with open(INDEX, encoding="utf-8") as f:
        index_html = f.read()
    with open(URUNLER, encoding="utf-8") as f:
        urunler = json.load(f)
    print("katalog %d kayit" % len(urunler))
    sonuc = eksenler(olc(index_html, urunler, arama.baslik_kolu_kapali()))
    print()
    sonuc["M1"] = _mutant("M1 (kapali liste bos)", index_html, urunler,
                          "var BASLIK_KOLU_KAPALI = [];", {"H1", "H2", "H5"})
    sonuc["M2"] = _mutant("M2 (Rover listeden cikti)", index_html, urunler,
                          'var BASLIK_KOLU_KAPALI = ["Mini", "Alpine", "Sigma"];',
                          {"H1", "H2", "H5"})
    sonuc["KONTROL-MUTANT"] = _mutant("KONTROL-MUTANT (bosluksuz literal)", index_html, urunler,
                                      'var BASLIK_KOLU_KAPALI = ["Mini","Rover","Alpine","Sigma"];',
                                      set())
    sha_son = _sha(INDEX)
    sonuc["SHA"] = sha_bas == sha_son
    print("SHA index.html bas=%s son=%s %s" % (sha_bas[:12], sha_son[:12],
                                               "AYNI" if sonuc["SHA"] else "DEGISTI (KUSUR)"))
    print()
    gecen = sum(1 for v in sonuc.values() if v)
    print("SONUC: %s — gecen %d · kalan %d · iddia %d"
          % ("YESIL" if gecen == len(sonuc) else "KIRMIZI", gecen, len(sonuc) - gecen,
             len(sonuc)))
    sys.exit(0 if gecen == len(sonuc) else 1)


if __name__ == "__main__":
    main()

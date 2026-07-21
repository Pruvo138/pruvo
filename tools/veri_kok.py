#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""veri_kok.py — ekleme betikleri icin KOD KOKU ile VERI KOKU'nu AYIRIR.

NEDEN VAR (olculdu, S4 turu — sessiz-hata sinifi):
urun-ekle / printables-ekle / makerworld-ekle betiklerinde ROOT sabiti uzun sure
"/Users/okan/dev/pruvo" idi. Bu, kabul testinin bir WORKTREE'den betigi gercekten import
etmesini engelliyordu (yanindaki YENI modulleri degil, ana kopyadakileri arardi; ana kopyada
henuz olmayan bir modul -> ImportError). O yuzden ROOT `__file__`'dan turetildi. AMA bu tek
degisiklik VERI duzlemini de tasidi: betik bir worktree'den kosuldugunda artik WORKTREE'nin
urunler.json / .urun-kaynaklari.json / .urunler.lock dosyalarina yazardi. Urun verisinin TEK
yazari (MaCiT) bir worktree'den ekleme yaparsa is SESSIZCE YANLIS YERE gider: parti "STAGED"
gorunur, ana kopyada hicbir sey yoktur, worktree silinince kayit da gider. Ustelik kilit
(.urunler.lock) da ayri dosya olur -> ana kopyadaki paralel yazicilarla serilesme COKER.

COZUM (iki kok, tek kural):
  * KOD KOKU  = betigin KENDI konumu (tools/../). Modul yukleme HEP buradan yapilir ->
    worktree'de test edilebilirlik korunur.
  * VERI KOKU = deponun ANA KOPYASI. Git'e sorulur: `git rev-parse --git-common-dir` bagli
    (linked) bir worktree'de ANA kopyanin .git dizinini verir; ana kopyada ".git" doner.
    Boylece veri DAIMA tek yere (ana kopya) yazilir — sabit "/Users/okan/dev/pruvo" yolunu
    KODA GOMMEDEN (fresh checkout / CI / baska makine calisir).
  * Ikisi FARKLIYSA (= worktree'den kosuluyorsun) STDERR'e GURULTULU uyari basilir ve akis
    OLDURULMEZ (fail-loud, fail-open degil): is dogru yere gider ama neden oraya gittigi
    gorunur olur.
  * Git yoksa / burasi git deposu degilse (or. sentetik fikstur agaci) veri koku = kod koku;
    sessiz. Bu, kabul testlerinin sahte agaclarda kosabilmesi icindir.

Saf/yan-etkisiz: dosya yazmaz, ag'a cikmaz; yalniz `git rev-parse` okur (enjekte edilebilir).
"""
import os
import subprocess


def _git_ortak_dizin(kok):
    """`git rev-parse --git-common-dir` ciktisi (str) ya da None (git yok / depo degil)."""
    try:
        r = subprocess.run(["git", "-C", kok, "rev-parse", "--git-common-dir"],
                           capture_output=True, text=True)
    except (OSError, ValueError):
        return None
    if r.returncode != 0:
        return None
    cikti = (r.stdout or "").strip()
    return cikti or None


def cozumle(betik_dosyasi, _git=None):
    """Doner (kod_kok, veri_kok, uyari).

    uyari: None (ayni kok) ya da STDERR'e basilacak GURULTULU metin (worktree tespit edildi).
    _git: yalniz test enjeksiyonu icin — kok alip git-common-dir metni/None dondurur.
    """
    kod_kok = os.path.dirname(os.path.dirname(os.path.abspath(betik_dosyasi)))
    git = _git or _git_ortak_dizin
    ortak = git(kod_kok)
    if not ortak:
        return kod_kok, kod_kok, None                    # git yok / depo degil -> tek kok
    if not os.path.isabs(ortak):
        ortak = os.path.join(kod_kok, ortak)
    # <ana-kopya>/.git  ->  <ana-kopya>
    ana = os.path.dirname(os.path.normpath(ortak))
    if not ana or os.path.normpath(ana) == os.path.normpath(kod_kok):
        return kod_kok, kod_kok, None                    # ana kopyadayiz -> sessiz
    uyari = (
        "\n" + "=" * 78 + "\n"
        "⚠️  DIKKAT — WORKTREE'DEN KOSULUYOR: KOD ile VERI ayri koklerde.\n"
        "    kod  (moduller)     : %s\n"
        "    VERI (urunler.json) : %s   <-- YAZMA BURAYA GIDER (ana kopya)\n"
        "    Sebep: urun verisinin TEK kopyasi ana depodadir; worktree'ye yazsaydik parti\n"
        "    STAGED gorunur ama ana kopyada HIC OLMAZDI (worktree silininde kayit da giderdi)\n"
        "    ve .urunler.lock ayrisip paralel yazicilarin serilesmesi COKERDI.\n"
        + "=" * 78 + "\n") % (kod_kok, ana)
    return kod_kok, ana, uyari

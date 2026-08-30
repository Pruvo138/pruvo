#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mimar-commit-kapisi.py — git commit backstop for source/data changes.

Kural:
- Ana repo'da kaynak (.py/.js/.mjs/.ts/.html/.css/.sql) VEYA veri (urunler.json /
  .urun-kaynaklari.json) staged ise commit'i blokla; .md vb. serbest.
- Worktree'de her sey serbest (mühendis alani).

BILINEN-BYPASS (sessiz degil, DAR): PRUVO_MIMAR_ONAY=worker YALNIZCA veri düzlemini
(urunler.json / .urun-kaynaklari.json) açar — ürün-ekleme partileri ana checkout'ta bu
dosyalari commit'ler (MaCiT'in sahasi, kirilmamali). Env=worker staged'de HERHANGI bir
KAYNAK dosyasi varken commit'i AÇMAZ: kaynak isi worktree'de commit'lenir. Bu daraltma,
env bypass'inin geçmiste mimarin kaynak-koda kaçis kapisina (tools/*.py'nin ana
checkout'a bu yolla girmesi) dönüsmesini kapatir; bilinen tek gevseme belgeli ve dar.

BYPASS MUHASEBESI (kapi bir DISIPLIN cihazidir, hapishane degil — hepsi KAYITLI):
  1. PRUVO_MIMAR_ONAY=worker  → yalniz VERI duzlemi. T3 AYRIMI (22 Tem): staged
     YALNIZ KOKTEKI veri dosyalarindan olusuyorsa (KOK-TAM-YOL, kok_veri_mi —
     2. tur: tools/urunler.json gibi ad-benzeri/alt-dizin/backslash yol temiz
     kategoriye GIREMEZ) bu MESRU veri-yazari (MaCiT) hattidir → (veri düzlemi
     ayrica KaaN'in shop/src/konfigurlar.js KOK-TAM-YOL config'ini kapsar,
     konfig_veri_mi)
     log satiri "veri-duzlemi-gecis" (escape SAYILMAZ; 'allow-' oneki tasimaz ki
     haftalik sayim temiz kalsin). Staged BOS ya da veri-disi dosya iceriyorsa
     ESKISI GIBI "allow-escape" (gercek istisna gurultulu kalir). Gerekce: eski
     tek-kategori duzeninde her urun partisi escape logu uretiyordu (olculdu:
     190 kayitta 152 mesru parti + 38 bos-staged) → gercek ihlal gurultude
     kaybolacakti.
  2. Sequencer suruyor (MERGE_HEAD/CHERRY_PICK_HEAD/REVERT_HEAD/rebase-*) → YALNIZCA
     korunan (kaynak/veri) dosya staged DEGILKEN gurultulu allow; stderr + log satiri
     "allow-sequencer".
     🔴 20 Tem REGRESYON ONARIMI (R1): bu istisna main()'in EN BASINDA, korunan-dosya
     kontrolunun ONUNDE ve KOSULSUZ 'return 0' idi. Olculdu: env yok + staged
     index.html + elle yazilmis .git/MERGE_HEAD -> exit 0 (main'de ayni vaka exit 1).
     Yani tek 'Write .git/MERGE_HEAD' yalniz veri duzlemini degil KAYNAK commit'ini de
     aciyordu. Istisna artik korunan-dosya kontrolunun ARKASINDA ve semantigi DAR:
     sequencer suruyorken bile korunan kaynak/veri staged ise kapi KAPALI (fail-closed).
     Geriye kalan mesru islev: sequencer'in kendi urettigi (korunan dosya icermeyen)
     commit'in GURULTULU + LOGLU gecmesi.
     BEDELI ACIK: cakisma cozumu KAYNAK dosya iceriyorsa 'git commit' bloklanir →
     cakismayi worktree'de coz ve merge'i oradan tasi (ya da kayitli --no-verify).
  3. git commit --no-verify → kapi hic kosmaz (git'in kendi kapisi; ayni zincirdeki
     urunler-guard'i da oldurur, bu yuzden hata metni bu yolu ONERMEZ).
  4. 'git worktree add <yol>' → mimar kendine tam muaf bir bolge acar (worktree
     toplevel'i bu kapinin kapsami disidir). BILEREK acik: kapi disiplin cihazi.
  Haftalik olcum (escape = yalniz gercek istisna; veri partileri ayri sayilir):
     grep -c allow- /Users/okan/dev/pruvo/.git/pruvo-kapi-log.jsonl
     grep -c veri-duzlemi-gecis /Users/okan/dev/pruvo/.git/pruvo-kapi-log.jsonl

Test kolayligi icin:
- --stdin: staged dosya listesini stdin'den oku.
- --toplevel YOL: repo toplevel'ini elle ver.
- --gitdir YOL: git dizinini elle ver (sequencer testi + log hedefi).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ANA_REPO = "/Users/okan/dev/pruvo"
KAYNAK_UZANTI = {".py", ".js", ".mjs", ".ts", ".html", ".css", ".sql"}
VERI_BASENAME = {"urunler.json", ".urun-kaynaklari.json"}
# KaaN'in (jeneratör mimari) veri-config düzlemi: TEK dosya, KOK-TAM-YOL. urunler.json
# emsali — env=worker ile commit'lenebilir, env yoksa BLOKLU. Ayrinti: konfig_veri_mi.
KONFIG_VERI_YOL = "shop/src/konfigurlar.js"

# Bir merge/cherry-pick/revert/rebase suruyorsa commit KORUNAN DOSYA YOKKEN gecer
# (gurultulu + loglu). Korunan dosya varsa sequencer istisnasi ISLEMEZ — bkz. R1.
SEQUENCER_DOSYA = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD")
SEQUENCER_DIZIN = ("rebase-merge", "rebase-apply")


def _basename(yol: str) -> str:
    if not yol:
        return ""
    temiz = yol.strip().replace("\\", "/")
    if not temiz:
        return ""
    return os.path.basename(temiz)


def veri_mi(yol: str) -> bool:
    """Dosya yolu VERI düzlemi mi? (urunler.json / .urun-kaynaklari.json)
    BASENAME-GENIS — BLOKLAMA tarafinin kontrolu (fail-closed yon: ad-benzeri
    alt-dizin dosyasi da env'siz bloklanir). TEMIZ serit icin kok_veri_mi kullanilir."""
    return _basename(yol) in VERI_BASENAME


def kok_veri_mi(yol: str) -> bool:
    """TEMIZ serit (veri-duzlemi-gecis) kontrolu — KOK-TAM-YOL (T3 2. tur).

    Curutucu bulgusu: temiz serit basename-bazli veri_mi ile kurulmustu;
    'tools/urunler.json', 'a/b/.urun-kaynaklari.json' ve backslash-adli
    'tools\\urunler.json' gibi GERCEK git yollari TEMIZ kategoriye giriyordu
    (main'de allow-escape idiler) -> escape muhasebesi sifir gurultuyle
    atlatilabilirdi. Bu kontrol DAR: staged yol, repo KOKUNDEKI
    urunler.json / .urun-kaynaklari.json'un KENDISI olmali. Bastaki './' soyulur;
    BASKA normalizasyon YOK — backslash'li ad ESLESMEZ, alt-dizin ESLESMEZ ->
    allow-escape'e duser (fail-closed: suphede gurultulu yol). BLOKLAMA tarafi
    (korunan_mi/veri_mi) bilerek basename-GENIS kalir."""
    temiz = (yol or "").strip()
    if temiz.startswith("./"):
        temiz = temiz[2:]
    return temiz in VERI_BASENAME


def konfig_veri_mi(yol: str) -> bool:
    """shop/src/konfigurlar.js'in KENDISI mi? KOK-TAM-YOL — ./ soyulur, BASKA
    normalizasyon YOK (backslash'li ad ESLESMEZ, alt-dizin ESLESMEZ). kok_veri_mi
    ile AYNI fail-closed disiplin: yalniz REPO KOKUNDEKI tam yol TRUE.

    KaaN'in veri-config düzlemi (urunler.json emsali): env=worker ile ana checkout'ta
    commit'lenebilir, env yoksa BLOKLU kalir. BLOK tarafi (kaynak_mi/.js) DARALMAZ —
    'evil/konfigurlar.js' ya da 'shop\\src\\konfigurlar.js' konfig_veri_mi=False → hala
    .js kaynak → env=worker'da bile BLOKLU."""
    temiz = (yol or "").strip()
    if temiz.startswith("./"):
        temiz = temiz[2:]
    return temiz == KONFIG_VERI_YOL


def kaynak_mi(yol: str) -> bool:
    """Dosya yolu KAYNAK kodu mu? (.py/.js/.mjs/.ts/.html/.css/.sql; veri HARIC)

    Uzanti karsilastirmasi KUCUK HARFE indirilir — 'tools/x.PY' olculmus bir kacakti
    (macOS dosya sistemi harf duyarsiz, git yolu oldugu gibi tasir).

    KOK-TAM-YOL muafiyeti: shop/src/konfigurlar.js veri-config düzlemidir (urunler.json
    gibi), KAYNAK sayilmaz. Yalniz TAM yol muaf — alt-dizin/backslash konfigurlar.js
    hala .js kaynak (blok DARALMAZ).

    VERI_BASENAME SAVUNMA DALI (savunma-derinligi, davranissal olarak OLU): asagidaki
    'basename in VERI_BASENAME -> return False' dali kaynak/veri AYRIMINI (bir veri
    dosyasi ASLA kaynak sayilmaz) ACIK + saglam kilar. Bugun VERI_BASENAME'in tamami
    .json (kaynak-disi) oldugundan uzanti kontrolu zaten ayni sonucu verir -> dalin
    BAGIMSIZ davranissal etkisi YOK; hicbir mutasyon onu kirmizi yakamaz (bkz.
    mimar-commit-kapisi-mutasyon.py: 'M4 KALDIRILDI' + guard_olu_mu invariant'i). Dal
    KALIR (savunma-derinligi): bir gun bir veri basename'i kaynak uzantisi kazanirsa
    (or. .js), bu dal o veri dosyasinin kaynak sanilip env=worker veri commit'inin
    YANLISLIKLA bloklanmasini onler."""
    if konfig_veri_mi(yol):
        return False
    basename = _basename(yol)
    if not basename or basename in VERI_BASENAME:
        return False
    _, uzanti = os.path.splitext(basename)
    return uzanti.lower() in KAYNAK_UZANTI


def korunan_mi(yol: str) -> bool:
    """Dosya kaynak VEYA veri VEYA konfig-veri mi? (env yoksa hepsi bloklanir —
    shop/src/konfigurlar.js de urunler.json gibi env=worker ister)."""
    return kaynak_mi(yol) or veri_mi(yol) or konfig_veri_mi(yol)


def _git_cikti(komut: list[str]) -> str:
    sonuc = subprocess.run(
        komut,
        capture_output=True,
        text=True,
        check=False,
    )
    if sonuc.returncode != 0:
        return ""
    return sonuc.stdout


def staged_dosyalar(stdin_modu: bool) -> list[str]:
    if stdin_modu:
        return [satir.strip() for satir in sys.stdin if satir.strip()]
    cikti = _git_cikti(["git", "diff", "--cached", "--name-only"])
    return [satir.strip() for satir in cikti.splitlines() if satir.strip()]


def toplevel(args_toplevel: str | None) -> str:
    if args_toplevel:
        return os.path.normpath(args_toplevel)
    cikti = _git_cikti(["git", "rev-parse", "--show-toplevel"]).strip()
    return os.path.normpath(cikti) if cikti else ""


def git_dizini(kok: str, args_gitdir: str | None) -> str:
    if args_gitdir:
        return os.path.normpath(args_gitdir)
    cikti = _git_cikti(["git", "-C", kok, "rev-parse", "--git-dir"]).strip()
    if cikti:
        if not os.path.isabs(cikti):
            cikti = os.path.join(kok, cikti)
        return os.path.normpath(cikti)
    return os.path.join(kok, ".git")


def sequencer_suruyor(gitdir: str) -> bool:
    """merge / cherry-pick / revert / rebase devam ediyor mu?"""
    try:
        for ad in SEQUENCER_DOSYA:
            if os.path.exists(os.path.join(gitdir, ad)):
                return True
        for ad in SEQUENCER_DIZIN:
            if os.path.isdir(os.path.join(gitdir, ad)):
                return True
    except Exception:
        return False
    return False


def bypass_kaydet(gitdir: str, kok: str, karar: str, mesaj: str, staged_sayisi: int) -> None:
    """Her BYPASS yolu GURULTULU + LOGLU olur; karar DEGISMEZ (kapi bir kilit degil,
    bir hatirlaticidir). Log yazilamazsa yine de stderr satiri kalir.

    Muhasebe: grep -c allow- <gitdir>/pruvo-kapi-log.jsonl
    'allow-escape'        = PRUVO_MIMAR_ONAY=worker, veri-duzlemi DISI kullanim
                            (staged bos ya da veri-disi dosya var) — GERCEK istisna
    'allow-sequencer'     = merge/cherry-pick/revert/rebase suruyor (SAHTE de kurulabilir)
    'veri-duzlemi-gecis'  = worker + staged YALNIZ veri dosyalari — MESRU MaCiT hatti;
                            'allow-' saymaz: grep -c veri-duzlemi-gecis <log>"""
    try:
        sys.stderr.write(mesaj + "\n")
    except Exception:
        pass
    try:
        satir = json.dumps({
            "t": int(time.time()),
            "karar": karar,
            "kok": kok,
            "staged": staged_sayisi,
        }, ensure_ascii=False)
        with open(os.path.join(gitdir, "pruvo-kapi-log.jsonl"), "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--stdin", action="store_true", help="staged dosyalari stdin'den oku")
    parser.add_argument("--toplevel", help="repo toplevel yolunu elle ver")
    parser.add_argument("--gitdir", help="git dizinini elle ver (test icin)")
    args = parser.parse_args()

    kok = toplevel(args.toplevel)
    if kok != ANA_REPO:
        return 0

    gitdir = git_dizini(kok, args.gitdir)
    staged = staged_dosyalar(args.stdin)
    kaynaklar = [yol for yol in staged if kaynak_mi(yol)]

    if os.environ.get("PRUVO_MIMAR_ONAY") == "worker":
        # DAR bypass: worker onayi YALNIZ veri düzlemini açar. Kaynak varsa reddet.
        if kaynaklar:
            sys.stderr.write(
                "COMMIT ENGELLENDI: PRUVO_MIMAR_ONAY=worker YALNIZ urunler.json / "
                ".urun-kaynaklari.json commit'ini açar; KAYNAK kodunu AÇMAZ. "
                "Kaynak isi worktree'de commit'lenir, ana checkout'a girmez.\n"
            )
            for yol in kaynaklar:
                sys.stderr.write(f"{yol}\n")
            return 1
        # T3 (22 Tem): YALNIZ veri-duzlemi dosyalarina dokunan commit MESRU veri-yazari
        # (MaCiT) hattidir — 'allow-escape' SAYILMAZ, AYRI kategoriyle kayda gecer
        # ('veri-duzlemi-gecis'; 'allow-' onekini TASIMAZ ki haftalik escape sayimi
        # temiz kalsin). DAR kosul: staged BOS DEGIL ve HER staged dosya veri
        # duzleminde. Karisik (veri + baska dosya) ya da bos-staged kullanim ESKISI
        # GIBI allow-escape gurultusudur — gercek istisna gorunur kalir.
        # T3 2. TUR: kontrol KOK-TAM-YOL (kok_veri_mi) — basename-bazli veri_mi
        # burada KULLANILMAZ (tools/urunler.json sinifi temiz kategoriye giremez).
        # KaaN veri-config düzlemi shop/src/konfigurlar.js de KOK-TAM-YOL temiz
        # kategoridedir (konfig_veri_mi) — env=worker + SAF konfig/veri commit'i
        # 'veri-duzlemi-gecis' (allow-escape DEGIL).
        veriler = [yol for yol in staged if kok_veri_mi(yol) or konfig_veri_mi(yol)]
        if staged and len(veriler) == len(staged):
            bypass_kaydet(
                gitdir, kok, "veri-duzlemi-gecis",
                "VERI-DUZLEMI GECISI (PRUVO_MIMAR_ONAY=worker; staged yalniz "
                "urunler.json / .urun-kaynaklari.json) — mesru veri-yazari commit'i. "
                "Kayit: grep -c veri-duzlemi-gecis " +
                os.path.join(gitdir, "pruvo-kapi-log.jsonl"),
                len(staged),
            )
            return 0
        bypass_kaydet(
            gitdir, kok, "allow-escape",
            "ESCAPE HATCH KULLANILDI (PRUVO_MIMAR_ONAY=worker, veri duzlemi DISI "
            "kullanim: staged bos ya da veri-disi dosya iceriyor) — commit kapisi "
            "atlandi. Bu yol loglanir: grep -c allow-escape " +
            os.path.join(gitdir, "pruvo-kapi-log.jsonl"),
            len(staged),
        )
        return 0

    # KORUNAN DOSYA KONTROLU SEQUENCER ISTISNASINDAN ONCE GELIR (R1 onarimi).
    # Sahte MERGE_HEAD yazmak artik kaynak/veri commit'ini ACMAZ; sequencer suruyorsa
    # bu yalnizca hata metnine bir satir ekler (teshis), karari DEGISTIRMEZ.
    bloklanan = [yol for yol in staged if korunan_mi(yol)]
    if bloklanan:
        sys.stderr.write(
            "COMMIT ENGELLENDI (mimar kod-kilidi / Layer 2): kaynak/veri degisikligi worker isidir. "
            "PRUVO_MIMAR_ONAY=worker YALNIZ urunler.json / .urun-kaynaklari.json commit'ini açar "
            "(kaynak kodu worktree'de commit'lenir).\n"
        )
        if sequencer_suruyor(gitdir):
            sys.stderr.write(
                "NOT: sequencer (merge/cherry-pick/revert/rebase) suruyor ama istisna "
                "KORUNAN dosyayi ACMAZ (fail-closed). Cakismayi worktree'de coz.\n"
            )
        for yol in bloklanan:
            sys.stderr.write(f"{yol}\n")
        return 1

    # Sequencer istisnasi: korunan dosya YOKKEN gurultulu + loglu allow. Tek
    # 'Write .git/MERGE_HEAD' ile sahte durum kurulabilir → bu yol SESSIZ OLAMAZ.
    if sequencer_suruyor(gitdir):
        bypass_kaydet(
            gitdir, kok, "allow-sequencer",
            "SEQUENCER ISTISNASI (merge/cherry-pick/revert/rebase suruyor, korunan dosya "
            "YOK) — commit kapisi atlandi. Bu yol loglanir: grep -c allow-sequencer " +
            os.path.join(gitdir, "pruvo-kapi-log.jsonl"),
            len(staged),
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

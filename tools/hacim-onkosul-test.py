#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HACIM-TAM-TAKIM ON-KOSUL + PAKET BUTUNLUK KABUL TESTI (K377, 7 Eyl 2026).

NEYI OLCER
==========
`.github/workflows/nobet.yml::hacim-tam-takim` isi 2026-07-16'da EMEKLI EDILEN
`ONIZLEME_PAKET_B64` secret'ini fail-closed on-kosul sayiyordu. Secret repoda YOK ve
OLMAYACAK (Okan karari; tek kaynak tools/onizleme-paket-yukle.py modul sonu notu), bu
yuzden is her elle tetikte on-kosulda `exit 1` verip checkout'a HIC GELMIYORDU. Kol
"dogru" davraniyordu (gurultulu kirmizi) ama YANLIS SARTA capalanmisti: isin tamami
aylarca OLCULMEDI.

Bu test o onarimin KOLLARINI olcer — YAML'i okur, shell govdelerini KAYNAKTAN cikarir
ve IZOLE gecici bir dizinde kosturur. Ikinci bir kopya yazmaz: govde bozulursa/silinirse
test onu goremez degil, KIRMIZI yanar.

KOLLAR
------
  K1  R2 on-kosulu, kimlik BOS       -> rc!=0 + eksik secret ADLARI basilir  (M1 hedefi)
  K2  R2 on-kosulu, kimlik DOLU      -> rc==0            (taban; yoksa K1 totoloji olurdu)
  K3  Butunluk, eslem-ozel.json YOK  -> rc!=0 + "OLCULEMEDI"                 (M2 hedefi)
  K4  Butunluk, eslem-ozel.json VAR  -> rc==0            (taban)
  K5  NON-GROWTH: hacim-tam-takim govdesinde `ONIZLEME_PAKET_B64` ATFI 0 olmali
      (geri eklenirse kirmizi; "grep==0 nobetcisi yasak kaydinda oludur" dersi geregi
      ayni turda K6 ile CIFT YONLU olcum yapilir)
  K6  IKIZ TANIM YOK: `aws s3 cp` gecen is-akisi dosyasi sayisi 0 olmali — cekme
      mantigi YALNIZ .github/actions/gizli-paket-cek/action.yml icinde yasar; oradaki
      sayi ise >=1 olmali (kolun CANLI oldugunu ayrica kanitlar)

MUTANT KANITI (K182 — her mutant HEDEF kolu OLDURDUGUNU AYRICA kanitlar)
------------------------------------------------------------------------
`--mutant m1` ve `--mutant m2` govdeyi IZOLE KOPYADA yamalar (kaynak dosyaya
DOKUNMAZ) ve o kolu yeniden kosar. Beklenen: hedef kol TABANDA yesilken mutantla
KIRMIZI olur. Mutantli sonuc tabanla AYNI cikarsa test `MUTANT ULASMADI` der ve
rc=2 (OLCULEMEDI) doner — sessizce yesile DUSMEZ.

  m1: on-kosul govdesindeki `exit 1` -> `exit 0`  (fail-closed kol susturulur)
  m2: butunluk govdesindeki `test -f ... || {...}` satirlari SILINIR

YIKICI YUK YOK: tum kosumlar tempfile.TemporaryDirectory() icinde gecer; gercek ev
yoluna yazilmaz, silme cagrisi YAPILMAZ.

rc: 0 = YESIL · 1 = KIRMIZI · 2 = OLCULEMEDI (ayristirici yok / mutant ulasmadi)
"""

import argparse
import os
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOBET = os.path.join(KOK, ".github", "workflows", "nobet.yml")
ACTION = os.path.join(KOK, ".github", "actions", "gizli-paket-cek", "action.yml")
IS_AKISI_DIZIN = os.path.join(KOK, ".github", "workflows")

IS_ADI = "hacim-tam-takim"
ONKOSUL_ADIM = "On-kosul: kardes depo jetonu + R2 paket kimligi beyan edilmis mi"
ACTION_ONKOSUL_ADIM = "On-kosul: R2 kimligi + paket anahtari beyan edilmis mi (fail-closed)"
BUTUNLUK_ADIM = "Paket butunlugu: eslem-ozel.json geldi mi"

R2_SECRETLARI = ("R2_ERISIM_ID", "R2_GIZLI_ANAHTAR", "CLOUDFLARE_ACCOUNT_ID")


def yaml_yukle(yol):
    """FAIL-CLOSED: gercek bir YAML ayristirici yoksa YESIL SAYMAZ, OLCULEMEDI der."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("OLCULEMEDI: pyyaml yok — is akisi YAML'i ayristirilamadi.")
        print("  Cozum: pip install pyyaml  (CI'da nobet.yml::hijyen-build zaten kurar)")
        sys.exit(2)
    import yaml
    with open(yol, encoding="utf-8") as f:
        return yaml.safe_load(f)


def adim_govdesi(yol, is_adi, adim_adi):
    """Bir is akisi/action adiminin `run:` govdesini KAYNAKTAN cikarir.

    Adim bulunamazsa OLCULEMEDI: adim yeniden adlandirilirsa test sessizce
    yesile dusmez (ad supurmesi fikstur yuzeyini korlestirir dersi)."""
    belge = yaml_yukle(yol)
    if is_adi is None:
        adimlar = belge.get("runs", {}).get("steps", []) or []
    else:
        adimlar = belge.get("jobs", {}).get(is_adi, {}).get("steps", []) or []
    for adim in adimlar:
        if adim.get("name") == adim_adi:
            govde = adim.get("run")
            if not govde:
                print("OLCULEMEDI: '%s' adiminda `run` govdesi YOK." % adim_adi)
                sys.exit(2)
            return govde
    print("OLCULEMEDI: '%s' adimi bulunamadi (%s)." % (adim_adi, os.path.basename(yol)))
    print("  Adim yeniden adlandirildiysa bu dosyadaki sabiti de guncelleyin.")
    sys.exit(2)


def kos(govde, ortam, calisma_dizini):
    """Govdeyi IZOLE dizinde kosar. Kaynak agaca yazmaz."""
    tam_ortam = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "HOME": calisma_dizini}
    tam_ortam.update(ortam)
    proc = subprocess.run(["bash", "-c", govde], cwd=calisma_dizini,
                          env=tam_ortam, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def m1_yamala(govde):
    """M1: fail-closed kolu sustur — `exit 1` -> `exit 0`."""
    return govde.replace("exit 1", "exit 0")


def m2_yamala(govde):
    """M2: butunluk kontrolunu tamamen kaldir."""
    satirlar = [s for s in govde.splitlines() if "eslem-ozel.json" not in s
                and "OLCULEMEDI" not in s and s.strip() not in ("}", "echo; }")]
    return "\n".join(satirlar) + "\ntrue\n"


# --------------------------------------------------------------------------- kollar
def k1_onkosul_bos(govde, _dizin):
    """Kimlik BOS -> KIRMIZI ve eksik adlar basilmali."""
    ortam = {"JEN_TOKEN": "", "R2_ERISIM_ID": "", "R2_GIZLI_ANAHTAR": "",
             "CLOUDFLARE_ACCOUNT_ID": "", "PAKET_ANAHTAR": ""}
    rc, cikti = kos(govde, ortam, _dizin)
    if rc == 0:
        return False, "rc=0 — SESSIZ ATLAMA: bos kimlikle on-kosul GECTI"
    eksik_ad = [ad for ad in R2_SECRETLARI if ad in cikti]
    if not eksik_ad:
        return False, "rc=%d ama eksik secret ADI basilmadi (gurultusuz kirmizi)" % rc
    return True, "rc=%d · basilan eksik ad sayisi=%d" % (rc, len(eksik_ad))


def k2_onkosul_dolu(govde, _dizin):
    """Kimlik DOLU -> YESIL (taban; bu kol olmadan K1 totoloji olurdu)."""
    ortam = {"JEN_TOKEN": "x", "R2_ERISIM_ID": "x", "R2_GIZLI_ANAHTAR": "x",
             "CLOUDFLARE_ACCOUNT_ID": "x", "PAKET_ANAHTAR": "onizleme/paket-vX.tar.gz"}
    rc, cikti = kos(govde, ortam, _dizin)
    if rc != 0:
        return False, "rc=%d — dolu kimlikle on-kosul KIRMIZI yandi: %s" % (rc, cikti.strip()[:200])
    return True, "rc=0 (taban yesil)"


def _butunluk_sahne(dizin, dosya_var):
    hedef = os.path.join(dizin, "onizleme", "derleyici")
    os.makedirs(hedef, exist_ok=True)
    yol = os.path.join(hedef, "eslem-ozel.json")
    if dosya_var:
        with open(yol, "w", encoding="utf-8") as f:
            f.write('{"aileler": {}}\n')
    return yol


def k3_butunluk_eksik(govde, dizin):
    """Paket acildi ama eslem-ozel.json YOK -> KIRMIZI + OLCULEMEDI."""
    _butunluk_sahne(dizin, dosya_var=False)
    rc, cikti = kos(govde, {}, dizin)
    if rc == 0:
        return False, "rc=0 — eslem-ozel.json YOKken butunluk GECTI (yalanci yesil)"
    if "OLCULEMEDI" not in cikti:
        return False, "rc=%d ama 'OLCULEMEDI' basilmadi" % rc
    return True, "rc=%d · OLCULEMEDI basildi" % rc


def k4_butunluk_tam(govde, dizin):
    """Dosya VAR -> YESIL (taban)."""
    _butunluk_sahne(dizin, dosya_var=True)
    rc, cikti = kos(govde, {}, dizin)
    if rc != 0:
        return False, "rc=%d — dosya VARken butunluk kirmizi yandi: %s" % (rc, cikti.strip()[:200])
    return True, "rc=0 (taban yesil)"


def k5_emekli_secret_atfi():
    """NON-GROWTH: hacim-tam-takim govdesinde emekli secret ATFI 0 olmali."""
    belge = yaml_yukle(NOBET)
    adimlar = belge.get("jobs", {}).get(IS_ADI, {}).get("steps", []) or []
    if not adimlar:
        return False, "OLCULEMEDI: %s isinin adimlari okunamadi" % IS_ADI
    metin = str(adimlar)
    sayi = metin.count("ONIZLEME_PAKET_B64")
    if sayi:
        return False, ("emekli secret %d kez ATIFTA — 16 Tem Okan karari geri alinmis "
                       "(repoda YOK, is on-kosulda oluyor)" % sayi)
    return True, "atif=0 (emekli secret geri eklenmemis)"


def k6_ikiz_tanim_yok():
    """Cekme mantigi YALNIZ ortak action'da yasamali. Cift yonlu olcum:
    is akislarinda 0 · action'da >=1 (kol CANLI oldugunu ayrica kanitlar)."""
    kirli = []
    for ad in sorted(os.listdir(IS_AKISI_DIZIN)):
        if not ad.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(IS_AKISI_DIZIN, ad), encoding="utf-8") as f:
            if "aws s3 cp" in f.read():
                kirli.append(ad)
    if not os.path.exists(ACTION):
        return False, "OLCULEMEDI: ortak action YOK (%s)" % ACTION
    with open(ACTION, encoding="utf-8") as f:
        action_sayi = f.read().count("aws s3 cp")
    if kirli:
        return False, "IKIZ TANIM: is akisinda cekme mantigi var -> %s" % ", ".join(kirli)
    if action_sayi < 1:
        return False, "OLU KOL: ortak action icinde `aws s3 cp` YOK (cekme nereye gitti?)"
    return True, "is akisi=0 · ortak action=%d (tek tanim)" % action_sayi


# --------------------------------------------------------------------------- surucu
def kollari_kos(mutant):
    onkosul = adim_govdesi(ACTION, None, ACTION_ONKOSUL_ADIM)
    butunluk = adim_govdesi(NOBET, IS_ADI, BUTUNLUK_ADIM)
    if mutant == "m1":
        onkosul = m1_yamala(onkosul)
    elif mutant == "m2":
        butunluk = m2_yamala(butunluk)

    sonuc = {}
    with tempfile.TemporaryDirectory(prefix="pruvo-onkosul-") as d:
        sonuc["K1 on-kosul/kimlik BOS -> KIRMIZI"] = k1_onkosul_bos(onkosul, d)
    with tempfile.TemporaryDirectory(prefix="pruvo-onkosul-") as d:
        sonuc["K2 on-kosul/kimlik DOLU -> YESIL"] = k2_onkosul_dolu(onkosul, d)
    with tempfile.TemporaryDirectory(prefix="pruvo-butunluk-") as d:
        sonuc["K3 butunluk/eslem YOK -> KIRMIZI"] = k3_butunluk_eksik(butunluk, d)
    with tempfile.TemporaryDirectory(prefix="pruvo-butunluk-") as d:
        sonuc["K4 butunluk/eslem VAR -> YESIL"] = k4_butunluk_tam(butunluk, d)
    sonuc["K5 emekli secret atfi = 0"] = k5_emekli_secret_atfi()
    sonuc["K6 ikiz cekme tanimi YOK"] = k6_ikiz_tanim_yok()
    return sonuc


def bas(baslik, sonuc):
    print(baslik)
    for ad, (gecti, not_) in sonuc.items():
        print("  %s  %-38s %s" % ("✅" if gecti else "❌", ad, not_))
    return [ad for ad, (gecti, _) in sonuc.items() if not gecti]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutant", choices=["m1", "m2"],
                    help="IZOLE kopyada govdeyi yamalar (kaynak dosyaya DOKUNMAZ)")
    args = ap.parse_args()

    print("=" * 74)
    print("HACIM ON-KOSUL + PAKET BUTUNLUK KABULU (K377)")
    print("=" * 74)

    taban = kollari_kos(None)
    dusen = bas("\nTABAN (mutantsiz):", taban)

    if not args.mutant:
        print("-" * 74)
        if dusen:
            print("SONUC: KIRMIZI ❌ — dusen kol: %s" % " · ".join(dusen))
            return 1
        print("SONUC: YESIL ✅ — 6 kol gecti. Mutant kanitini AYRICA kosun:")
        print("  python3 tools/hacim-onkosul-test.py --mutant m1")
        print("  python3 tools/hacim-onkosul-test.py --mutant m2")
        return 0

    if dusen:
        print("-" * 74)
        print("OLCULEMEDI: taban zaten KIRMIZI (%s) — mutant hukmu verilemez." % " · ".join(dusen))
        return 2

    hedef = {"m1": "K1 on-kosul/kimlik BOS -> KIRMIZI",
             "m2": "K3 butunluk/eslem YOK -> KIRMIZI"}[args.mutant]
    mutantli = kollari_kos(args.mutant)
    dusen_m = bas("\nMUTANT %s (izole kopya):" % args.mutant.upper(), mutantli)

    print("-" * 74)
    if not dusen_m:
        print("MUTANT ULASMADI ❌ — %s yamasi HICBIR kolu oldurmedi; mutantli kosum" % args.mutant)
        print("tabanla AYNI. Yama govdeye degmiyor ya da kol zaten olcmuyor.")
        return 2
    if hedef not in dusen_m:
        print("YANLIS ALAN ❌ — %s dusurdu ama HEDEF kol (%s) hala yesil." % (" · ".join(dusen_m), hedef))
        return 2
    print("MUTANT KANITI ✅ — %s yamasi HEDEF kolu oldurdu: %s" % (args.mutant, hedef))
    print("  (mutantla dusen kol sayisi: %d · taban: 0)" % len(dusen_m))
    return 0


if __name__ == "__main__":
    sys.exit(main())

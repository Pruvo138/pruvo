#!/usr/bin/env python3
"""K304-BOOTSTRAP KABUL BATARYASI — kapi dagitim KURUCUSUNUN serbest kolu.

OLCULEN ARIZA (28 Agu 2026, KraL-HasatKapiKurulum-28Agu): `kapi-dagitim-kur.py --ev
<kardes_ev>` HICBIR evde mimar eliyle kosturulamiyordu (KraL'da R2, kardes evde R2+F).
Yani yeni kapiyi kuracak komut, kurulmamis eski kapi tarafindan bloke ediliyordu.

BU BATARYA NE OLCER:
  ① kurucu cagrisi kaynakta SERBEST kolda tanimli (V1 · V1F)
  ② MUTANT: tanim dusunce cagri RED'e doner, geri konunca gecer — ve mutantin
     HEDEF KOLU oldurdugu, denyin GEREKCESI okunarak AYRICA kanitlanir (K182)
  ③ muafiyet DIZGE eslemesiyle degil CAGRI YERIYLE olculur (V4 · M3)
  ④ GEVSEME YOK: muafiyet yalniz bu kurucuyu kapsar (V2 · V3 · V5 · V6 · V7)

🔴 MUTASYON CANLI DOSYADA YAPILMAZ. Her mutant gecici bir KOPYAYA uygulanir; kopya
`finally`de silinir ve silindigi BASILIR ([[diskte-iz-birakma-yasagi]]).

rc: 0 = tum vakalar + tum mutantlar + KONTROL beklendigi gibi · 1 = en az biri dustu.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(BURASI, "mimar-icra-kapisi.py")

KRAL = "/Users/okan/dev/pruvo"
HASAT = "/Users/okan/dev/pruvo-hasat"
KURUCU = KRAL + "/tools/kapi-dagitim-kur.py"

sys.path.insert(0, BURASI)
from mimar_kimlik import _proje_damgasi  # noqa: E402

# Kanonik govdedeki iki EV CAPASI — shim bunlari eve cevirir; kardes-ev fiksturu
# AYNI donusumu uygular (ikinci bir renderer yazilmaz).
CAPA_REPO = 'REPO_ONEKI = "/Users/okan/dev/pruvo/"'
CAPA_WT = 'GIT_WORKTREE_KAYIT = "/Users/okan/dev/pruvo/.git/worktrees"'


def _cip_worktree(ev_koku):
    """Evin git'e KAYITLI ilk worktree koku — ROL ekseni bunu bekler. Yoksa None."""
    kayit = os.path.join(ev_koku, ".git", "worktrees")
    try:
        adlar = sorted(os.listdir(kayit))
    except OSError:
        return None
    for ad in adlar:
        try:
            with open(os.path.join(kayit, ad, "gitdir"), encoding="utf-8") as f:
                icerik = f.read().strip()
        except OSError:
            continue
        if icerik:
            return os.path.normpath(os.path.dirname(icerik))
    return None


def yuk(komut, cwd, cip_koku=None):
    """PreToolUse yuku. cip_koku verilirse oturum damgasi O worktree'ye ait olur."""
    g = {"tool_name": "Bash", "tool_input": {"command": komut}, "cwd": cwd}
    if cip_koku:
        g["transcript_path"] = ("/Users/okan/.claude/projects/"
                                + _proje_damgasi(cip_koku) + "/oturum.jsonl")
    return g


def kos(kapi, girdi):
    # 🔴 MUTANT KOPYALARI GECICI DIZINDE YASAR; kapi govdesi kendi dizinini sys.path'te
    # sanarak `mimar_kimlik`i import eder. PYTHONPATH verilmezse mutant IMPORT'ta coker,
    # stdout BOS kalir ve "izin" gibi OKUNUR — mutant oldurmedigi bir kolu oldurmus
    # gorunur. Fikstur kusuru ile davranis farki karistirilmaz.
    cevre = dict(os.environ)
    cevre["PYTHONPATH"] = BURASI + os.pathsep + cevre.get("PYTHONPATH", "")
    p = subprocess.run([sys.executable, kapi], input=json.dumps(girdi),
                       capture_output=True, text=True, timeout=60, env=cevre)
    if not p.stdout.strip():
        # BOS stdout = izin SAYILMAZ; yalniz rc=0 ise izindir. Aksi halde kapi COKMUSTUR
        # (fail-open korlugu: kapinin kendi 20 Tem dersi).
        if p.returncode != 0:
            return ("COKTU", (p.stderr or "").strip()[-200:])
        return ("izin", "")
    try:
        veri = json.loads(p.stdout)
    except Exception:
        return ("COZULEMEDI", p.stdout[:200])
    h = veri.get("hookSpecificOutput") or {}
    if h.get("permissionDecision") == "deny":
        return ("deny", h.get("permissionDecisionReason") or "")
    return ("izin", "")


def kardes_ev_govdesi(kaynak_yolu, hedef_yolu, ev_koku):
    """Kardes evin SHIM'inin exec ettigi govdenin BIREBIR ayni donusumu."""
    with open(kaynak_yolu, encoding="utf-8") as f:
        metin = f.read()
    if metin.count(CAPA_REPO) != 1 or metin.count(CAPA_WT) != 1:
        raise RuntimeError("EV CAPALARI TAM BIR KEZ degil — fikstur kurulamaz")
    metin = metin.replace(CAPA_REPO, 'REPO_ONEKI = "' + ev_koku + '/"')
    metin = metin.replace(CAPA_WT,
                          'GIT_WORKTREE_KAYIT = "' + ev_koku + '/.git/worktrees"')
    with open(hedef_yolu, "w", encoding="utf-8") as f:
        f.write(metin)
    return hedef_yolu


# === MUTANTLAR — her biri BIR HEDEF KOLU oldurur; 'atif' o kolun deny gerekcesinde
# gorunmesi gereken imzadir (K182: mutantin dogru kolu oldurdugunu AYRICA kanitla). ===
MUTANTLAR = (
    ("M1_R2_KOLU_DUSER",
     "if disari and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "if False and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "V1", "repo DIŞINA çözülen"),
    ("M2_F_KOLU_DUSER",
     "if not repo_ici(betik, cwd) and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "if False and _kapi_dagitim_muaf(ad, argumanlar, cwd):",
     "V1F", "repo DIŞINDAKİ bir betiği"),
    ("M3_DIZGE_ESLEMESINE_DONER",
     "if betik is None or _coz(betik, cwd) != kurucu:",
     "if betik is None or os.path.basename(betik) != "
     "os.path.basename(kurucu):",
     "V4B_WORKTREE_KOPYASI", None),
)

KONTROL_MUTANTI = ("KONTROL_YORUM",
                   "# E2/R2) YOL TARAMASI",
                   "# E2/R2) YOL TARAMASI (kontrol mutanti — davranis DEGISMEZ)")


def vakalar(cip_kral, cip_hasat):
    """(ad, kapi_secici, girdi, beklenen) — kapi_secici: 'kral' | 'hasat'."""
    return (
        ("V1", "kral",
         yuk("python3 " + KURUCU + " --ev " + HASAT, cip_kral, cip_kral), "izin"),
        ("V1F", "hasat",
         yuk("python3 " + KURUCU + " --ev " + HASAT, cip_hasat, cip_hasat), "izin"),
        ("V2_ANA_OTURUM", "kral",
         yuk("python3 " + KURUCU + " --ev " + HASAT, KRAL), "deny"),
        ("V3_KAYITSIZ_EV", "kral",
         yuk("python3 " + KURUCU + " --ev /private/tmp/sahte-ev", cip_kral, cip_kral),
         "deny"),
        ("V4A_REPO_DISI_TAKLIT", "kral",
         yuk("python3 /private/tmp/kapi-dagitim-kur.py --ev " + HASAT,
             cip_kral, cip_kral), "deny"),
        # 🔴 V4B — MUAFIYETIN CAPASI: kurucunun WORKTREE KOPYASI muafiyeti DEVRALMAZ.
        # Kopya repo ICINDEDIR (kayitli worktree), yani 2. adim onu ELEMEZ; onu eleyen
        # TEK sey 1. adimdaki KANONIK YOL TAM ESITLIGIDIR. Basename eslemesine donen bir
        # kapi burada IZIN verirdi — ve o an her dal, kurucuyu kendi agacinda degistirip
        # kardes evlere yazma yetkisi devsirebilirdi. M3 tam bu kolu hedefler.
        ("V4B_WORKTREE_KOPYASI", "kral",
         yuk("python3 " + cip_kral + "/tools/kapi-dagitim-kur.py --ev " + HASAT,
             cip_kral, cip_kral), "deny"),
        ("V5_BASKA_ARAC", "kral",
         yuk("python3 " + KRAL + "/tools/durum.py --ev " + HASAT, cip_kral, cip_kral),
         "deny"),
        ("V6_SATIR_ICI", "kral",
         yuk('python3 -c "import sys" ' + KURUCU, cip_kral, cip_kral), "deny"),
        ("V7_TEHLIKELI_ENV", "kral",
         yuk("PYTHONPATH=/private/tmp python3 " + KURUCU + " --ev " + HASAT,
             cip_kral, cip_kral), "deny"),
        ("KONTROL_LS", "kral", yuk("ls", cip_kral, cip_kral), "izin"),
    )


def batarya(kapilar, vaka_listesi, basli=False):
    dusen = []
    gozlem = {}
    for ad, secici, girdi, beklenen in vaka_listesi:
        h, neden = kos(kapilar[secici], girdi)
        gozlem[ad] = (h, neden)
        ok = (h == beklenen)
        if not ok:
            dusen.append(ad)
        if basli:
            print("  " + ad + " beklenen=" + beklenen + " gozlenen=" + h
                  + ("" if ok else "   <== DUSTU"))
    return dusen, gozlem


def kurulu_shim_kolu(cip_hasat):
    """KURULU SHIM KOLU — kardes evde GERCEKTEN DURAN dosyayi kosturur.

    Kurucunun kendi 'FIKSTUR=3/3' cumlesi onun IDDIASIDIR, benim olcumum degil
    ([[aracin-teshis-cumlesi-olcum-degil]]). Burada ayni dosya BAGIMSIZ olarak, kurucudan
    ayri vakalarla surulur: kurulumdan sonra kapinin GERCEK ihlalleri hala reddettigi
    (fail-closed KORUNDU) bu kolda olculur.

    Yol EV KUMESINDEN turetilir, elle yazilmaz."""
    try:
        import kapi_dagitim as _KD
        yol = None
        for ad, kok, goreli, mod in _KD.EVLER:
            if ad == "MaCiT":
                yol = _KD.kurulu_yol(kok, goreli)
        if yol is None or not os.path.exists(yol):
            return (["KURULU_SHIM_YOK"], 0)
    except Exception as hata:
        return (["KURULU_SHIM_OLCULEMEDI " + repr(hata)], 0)

    vaka = (
        ("S1_ALLOW_ls", yuk("ls", HASAT), "izin"),
        ("S2_DENY_satir_ici", yuk('python3 -c "1"', cip_hasat, cip_hasat), "deny"),
        ("S3_DENY_repo_disi_betik",
         yuk("python3 /private/tmp/x.py", cip_hasat, cip_hasat), "deny"),
        ("S4_DENY_ana_oturum_arac",
         yuk("python3 " + HASAT + "/tools/bir-arac.py", HASAT), "deny"),
        ("S5_ROL_CIP_arac_serbest",
         yuk("python3 " + cip_hasat + "/tools/bir-arac.py", cip_hasat, cip_hasat),
         "izin"),
    )
    dusen = []
    print("  KURULU_SHIM=" + yol + " BAYT=" + str(os.path.getsize(yol)))
    for ad, girdi, beklenen in vaka:
        h, _neden = kos(yol, girdi)
        ok = (h == beklenen)
        if not ok:
            dusen.append(ad)
        print("    " + ad + " beklenen=" + beklenen + " gozlenen=" + h
              + ("" if ok else "   <== DUSTU"))
    return dusen, len(vaka)


def main():
    gecici = tempfile.mkdtemp(prefix="k304-bootstrap-")
    silindi = False
    try:
        cip_kral = _cip_worktree(KRAL)
        cip_hasat = _cip_worktree(HASAT)
        print("FIKSTUR cip_kral=" + str(cip_kral))
        print("FIKSTUR cip_hasat=" + str(cip_hasat))
        if not cip_kral or not cip_hasat:
            print("HUKUM=OLCULEMEDI (kayitli worktree yok; fail-closed)")
            return 1

        hasat_govde = kardes_ev_govdesi(
            KAPI, os.path.join(gecici, "hasat-govde.py"), HASAT)
        kapilar = {"kral": KAPI, "hasat": hasat_govde}
        vaka_listesi = vakalar(cip_kral, cip_hasat)

        print("=== TABAN ===")
        dusen, taban_gozlem = batarya(kapilar, vaka_listesi, basli=True)
        print("TABAN VAKA=" + str(len(vaka_listesi)) + " DUSEN=" + str(len(dusen)))
        if dusen:
            print("HUKUM=TABAN_KIRMIZI " + ",".join(dusen))
            return 1

        with open(KAPI, encoding="utf-8") as f:
            temiz = f.read()

        print("=== MUTANTLAR (hedef-kol atifli) ===")
        olen = 0
        atif_tam = 0
        for ad, eski, yeni, hedef_vaka, atif in MUTANTLAR:
            if temiz.count(eski) != 1:
                print("  " + ad + " CAPA_TUTMADI (kaynakta " + str(temiz.count(eski))
                      + " kez) — kapsam sessizce daralmaz, RED")
                return 1
            mut_yol = os.path.join(gecici, ad + ".py")
            with open(mut_yol, "w", encoding="utf-8") as f:
                f.write(temiz.replace(eski, yeni))
            mut_kapilar = dict(kapilar)
            mut_kapilar["kral"] = mut_yol
            if hedef_vaka == "V1F":
                mut_kapilar["hasat"] = kardes_ev_govdesi(
                    mut_yol, os.path.join(gecici, ad + "-hasat.py"), HASAT)
            mut_dusen, mut_gozlem = batarya(mut_kapilar, vaka_listesi)
            hedef_oldu = hedef_vaka in mut_dusen
            olen += 1 if hedef_oldu else 0
            # K182 — HEDEF KOL ATFI: mutant sadece 'bir sey kirmadi', TAM O KOLU kirdi.
            atif_ok = True
            if atif is not None:
                atif_ok = atif in (mut_gozlem[hedef_vaka][1] or "")
                atif_tam += 1 if atif_ok else 0
            else:
                atif_tam += 1 if hedef_oldu else 0
            print("  " + ad + " hedef=" + hedef_vaka
                  + " oldu=" + ("EVET" if hedef_oldu else "HAYIR")
                  + " hedef_kol_atfi=" + ("TAM" if atif_ok else "TUTMADI")
                  + " yan_dusen=" + ",".join(a for a in mut_dusen if a != hedef_vaka))
            if not hedef_oldu or not atif_ok:
                print("HUKUM=MUTANT_YASADI " + ad)
                return 1

        eski, yeni = KONTROL_MUTANTI[1], KONTROL_MUTANTI[2]
        kon_yol = os.path.join(gecici, "kontrol.py")
        with open(kon_yol, "w", encoding="utf-8") as f:
            f.write(temiz.replace(eski, yeni, 1))
        kon_kapilar = dict(kapilar)
        kon_kapilar["kral"] = kon_yol
        kon_dusen, _ = batarya(kon_kapilar, vaka_listesi)
        print("  " + KONTROL_MUTANTI[0] + " dusen=" + str(len(kon_dusen))
              + " (YESIL kalmali)")
        if kon_dusen:
            print("HUKUM=KONTROL_KIRMIZI " + ",".join(kon_dusen))
            return 1

        print("=== KURULU SHIM (kardes evde duran GERCEK dosya) ===")
        shim_dusen, shim_vaka = kurulu_shim_kolu(cip_hasat)
        print("  KURULU_SHIM_VAKA=" + str(shim_vaka)
              + " DUSEN=" + str(len(shim_dusen)))
        if shim_dusen:
            print("HUKUM=KURULU_SHIM_KIRMIZI " + ",".join(shim_dusen))
            return 1

        print("VAKA=" + str(len(vaka_listesi)) + " DUSEN=0 MUTANT_OLEN="
              + str(olen) + "/" + str(len(MUTANTLAR))
              + " ATIF=" + str(atif_tam) + "/" + str(len(MUTANTLAR))
              + " KONTROL=YESIL")
        print("HUKUM=GECTI")
        return 0
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        silindi = not os.path.exists(gecici)
        print("GECICI_SILINDI=" + str(silindi) + " YOL=" + gecici)


if __name__ == "__main__":
    sys.exit(main())

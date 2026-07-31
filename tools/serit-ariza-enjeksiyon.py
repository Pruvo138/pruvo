#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SERIT AYRIMI — IKI YONLU ARIZA ENJEKSIYONU (elde kosulan KANIT araci).

    python3 tools/serit-ariza-enjeksiyon.py

CI ADIMI DEGILDIR (bilincli: kanit araci yayin hattina yuk bindirmez; emsal
tools/ege-bilgi-tavan-mutasyon.py). Kesif predikatina de girmez (`-test.py` /
`test-*.py` / `*-kapisi.py` degil) -> ci-kapsam-test.py muafiyet ISTEMEZ.

NE KANITLAR — iki yon birden:
  YON 1 (B KIRMIZI -> YAYIN CIKAR): serit B'deki bir adim kirmiziya dusurulunce
         `deploy` job'u YINE DE kosar. Kapi kirmizi GORUNUR, yayin durmaz.
  YON 2 (A KIRMIZI -> YAYIN CIKMAZ): serit A'daki bir adim kirmiziya dusurulunce
         `deploy` job'u KOSMAZ (atlanir). Icerik korumasi AYNEN durur.

🔴 MUTASYON DISKE YAZILMAZ: hedef `run:` govdeleri YALNIZ BELLEKTE degistirilir,
gercek .github/workflows/deploy.yml SALT OKUNUR acilir. (Bu depoda olculdu: diske
yazilan mutant geri alinmazsa dalda CANLI kalir.) Kabuk kolu icin uretilen gecici
dosyalar `finally` ile silinir.

OLCUM IKI BACAKLI — ikisi de gerekli:
  (A) GRAF BACAGI  : GitHub `needs:` semantigi. Bir job ancak `needs:`indeki TUM
      joblar BASARILI ise kosar. `deploy` YALNIZ `build`'e baglidir -> `serit-b`
      kirmizi olsa da kosar. Simulator KENDI kanaryalariyla korunur (asagida K1-K4):
      "hep kosar" ya da "hep atlanir" diyen bir simulator KIRMIZI yanar.
  (B) KABUK BACAGI : hedef adimin cikis kodu GERCEKTEN job'u kirmizi yakiyor mu.
      Adimin GERCEK `run:` govdesi, hedef komut basarisiz bir komutla degistirilerek
      GitHub'in varsayilan kabugunda (`bash -e`) KOSULUR ve rc != 0 beklenir.
      Bu bacak `|| true`, `set +e`, `continue-on-error` gibi fail-open sarmalayicilarini
      yakalar — GRAF bacagi tek basina onlari GOREMEZ.
"""
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YML = os.path.join(KOK, ".github", "workflows", "deploy.yml")

try:
    import yaml
except ImportError:  # pragma: no cover
    print("OLCULEMEDI: pyyaml yok -> `pip install pyyaml`")
    sys.exit(2)

YAYIN_ACTION_ONEKI = "actions/deploy-pages"

# (etiket, adim_adi, beklenen_serit)
VAKALAR = (
    ("B1", "CI kapsam kapisi (her kabul testi kosuluyor mu / gerekceli muaf mi)", "B"),
    ("B2", "Nobetci mutasyon harness'i (kapilar bozulunca kirmizi yaniyor mu)", "B"),
    ("B3", "Yayin ic-dil kapisi oz-nobetcisi (SERIT B)", "B"),
    ("B4", "Katalog/parti veri kapilari kabul testi (durum + edge + derin cap)", "B"),
    ("A1", "Kisisel veri korumasi testi", "A"),
    ("A2", "Diriltme kapisi (silinmis urun geri gelmis mi)", "A"),
    ("A3", "Yayin ic-dil kapisi (uretilen ciktinin yorum yuzeyi)", "A"),
    ("A4", "Statik sayfalari uret", "A"),
)

BASARISIZ_KOMUT = 'python3 -c "import sys; sys.exit(1)"  # ARIZA ENJEKSIYONU'


# ---------------------------------------------------------------------------
def yukle():
    with open(YML, encoding="utf-8") as f:
        return yaml.safe_load(f.read())


def yayin_isi(jobs):
    for job_id, job in jobs.items():
        for step in (job.get("steps") or []):
            if isinstance(step, dict) and str(step.get("uses", "")).strip().startswith(
                    YAYIN_ACTION_ONEKI):
                return job_id
    return None


def needs_listesi(job):
    n = job.get("needs")
    if isinstance(n, str):
        return [n]
    return [str(x) for x in n] if isinstance(n, list) else []


def bloklayan_joblar(jobs, yayin):
    """Yayin job'u + ona GECISLI `needs:` ile bagli tum atalar."""
    kume = {yayin}
    degisti = True
    while degisti:
        degisti = False
        for job_id in list(kume):
            for x in needs_listesi(jobs.get(job_id) or {}):
                if x in jobs and x not in kume:
                    kume.add(x)
                    degisti = True
    return kume


def _dogru(v):
    return v is True or (isinstance(v, str) and v.strip().lower() == "true")


def simule(jobs, basarisiz):
    """GitHub `needs:` semantigi — {job_id: 'basarili'|'basarisiz'|'atlandi'}.

    basarisiz: {(job_id, adim_indeksi), ...} — o adimin cikis kodu != 0.
    KURAL: job ancak `needs:`indeki TUM joblar 'basarili' ise KOSAR (varsayilan `if:`).
    Kosan bir job, `continue-on-error` TASIMAYAN basarisiz bir adimi varsa 'basarisiz'.
    """
    sonuc = {}
    kalan = set(jobs)
    while kalan:
        ilerledi = False
        for job_id in sorted(kalan):
            job = jobs[job_id]
            gerekli = needs_listesi(job)
            if any(g not in sonuc for g in gerekli if g in jobs):
                continue
            ilerledi = True
            kalan.discard(job_id)
            if any(sonuc.get(g) != "basarili" for g in gerekli if g in jobs):
                sonuc[job_id] = "atlandi"
                continue
            if _dogru(job.get("continue-on-error")):
                sonuc[job_id] = "basarili"
                continue
            kotu = False
            for i, step in enumerate(job.get("steps") or []):
                if (job_id, i) in basarisiz and not _dogru(
                        (step or {}).get("continue-on-error")):
                    kotu = True
                    break
            sonuc[job_id] = "basarisiz" if kotu else "basarili"
        if not ilerledi:  # dongusel `needs:` — fail-closed
            for job_id in kalan:
                sonuc[job_id] = "atlandi"
            break
    return sonuc


def adim_bul(jobs, ad):
    for job_id, job in jobs.items():
        for i, step in enumerate(job.get("steps") or []):
            if isinstance(step, dict) and step.get("name") == ad:
                return job_id, i, step
    return None, None, None


def kabuk_bacagi(step, hedef_satir_onek):
    """(rc, cikti) — adimin GERCEK `run:` govdesi, hedef komut BASARISIZ bir komutla
    degistirilip GitHub varsayilan kabugunda (`bash -e`) kosulur."""
    govde = step.get("run") or ""
    yeni = []
    degisti = False
    for satir in govde.splitlines():
        if satir.strip().startswith(hedef_satir_onek):
            yeni.append(satir[:len(satir) - len(satir.lstrip())] + BASARISIZ_KOMUT)
            degisti = True
        else:
            yeni.append(satir)
    if not degisti:
        yeni = [BASARISIZ_KOMUT]
    gecici = tempfile.mkdtemp(prefix="pruvo-serit-kabuk-")
    try:
        yol = os.path.join(gecici, "adim.sh")
        with open(yol, "w", encoding="utf-8") as f:
            f.write("\n".join(yeni) + "\n")
        p = subprocess.run(["bash", "-e", yol], cwd=KOK, capture_output=True, text=True)
        return p.returncode, (p.stdout + p.stderr)[-200:]
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


# ---------------------------------------------------------------------------
def main():
    govde = yukle()
    jobs = govde.get("jobs") or {}
    yayin = yayin_isi(jobs)
    if yayin is None:
        print("OLCULEMEDI: `%s` kullanan yayin job'u bulunamadi." % YAYIN_ACTION_ONEKI)
        return 2
    bloklayan = bloklayan_joblar(jobs, yayin)
    serit_b = set(jobs) - bloklayan

    print("=" * 78)
    print("SERIT AYRIMI — IKI YONLU ARIZA ENJEKSIYONU")
    print("=" * 78)
    print("  is akisi           : %s (SALT OKUNDU)" % os.path.relpath(YML, KOK))
    print("  Pages yayin job'u  : %s" % yayin)
    print("  YAYINI BLOKLAYAN   : %s" % ", ".join(sorted(bloklayan)))
    print("  YAYINI BLOKLAMAYAN : %s" % ", ".join(sorted(serit_b)))
    for job_id in sorted(jobs):
        print("    - %-10s adim=%3d  needs=%s"
              % (job_id, len(jobs[job_id].get("steps") or []),
                 needs_listesi(jobs[job_id]) or "-"))
    print()

    hata = []
    iddia = 0

    # ---- KANARYALAR: simulatorun KENDISI olcuyor mu -----------------------
    print("-" * 78)
    print("KANARYALAR (simulator 'hep kosar' ya da 'hep atlanir' diyemez)")
    iddia += 1
    k1 = simule(jobs, set())
    print("  K1 hicbir ariza yok                       -> %s = %s" % (yayin, k1[yayin]))
    if k1[yayin] != "basarili":
        hata.append("K1 BOZUK: arizasiz kosumda yayin job'u kosmadi (%s)" % k1[yayin])

    a_job, a_idx, _a_step = adim_bul(jobs, VAKALAR[4][1])
    iddia += 1
    k2 = simule(jobs, {(a_job, a_idx)})
    print("  K2 serit A adimi kirmizi                  -> %s = %s" % (yayin, k2[yayin]))
    if k2[yayin] != "atlandi":
        hata.append("K2 BOZUK: A kirmiziyken yayin job'u atlanmadi (%s)" % k2[yayin])

    # K3: ayni A adimina `continue-on-error: true` -> simulator bunu OKUMALI
    iddia += 1
    import copy
    j3 = copy.deepcopy(jobs)
    j3[a_job]["steps"][a_idx]["continue-on-error"] = True
    k3 = simule(j3, {(a_job, a_idx)})
    print("  K3 ayni adim + `continue-on-error: true`  -> %s = %s" % (yayin, k3[yayin]))
    if k3[yayin] != "basarili":
        hata.append("K3 BOZUK: `continue-on-error` OKUNMUYOR -> simulator adim "
                    "ozelliklerine kor (%s)" % k3[yayin])

    # K4: `deploy` serit-b'ye de BAGLANIRSA B kirmizi yayini DURDURMALI
    iddia += 1
    b_job, b_idx, _b_step = adim_bul(jobs, VAKALAR[0][1])
    j4 = copy.deepcopy(jobs)
    j4[yayin]["needs"] = sorted(set(needs_listesi(j4[yayin])) | {b_job})
    k4 = simule(j4, {(b_job, b_idx)})
    print("  K4 `deploy` B'ye de baglanirsa B kirmizi  -> %s = %s" % (yayin, k4[yayin]))
    if k4[yayin] != "atlandi":
        hata.append("K4 BOZUK: graf OKUNMUYOR -> B'ye baglanan yayin job'u yine kostu "
                    "(%s)" % k4[yayin])

    # K5: hedef adim serit A'da OLSAYDI yayin dururdu (ayrimin GERCEK oldugu)
    iddia += 1
    j5 = copy.deepcopy(jobs)
    tasinan = j5[b_job]["steps"][b_idx]
    hedef_a = sorted(bloklayan - {yayin})[0]
    j5[hedef_a]["steps"].append(tasinan)
    k5 = simule(j5, {(hedef_a, len(j5[hedef_a]["steps"]) - 1)})
    print("  K5 ayni adim serit A'da olsaydi           -> %s = %s" % (yayin, k5[yayin]))
    if k5[yayin] != "atlandi":
        hata.append("K5 BOZUK: adim A job'una tasinip kirmizi yapildiginda yayin "
                    "durmadi (%s)" % k5[yayin])
    print()

    # ---- 6+ VAKA: IKI YONLU ENJEKSIYON ------------------------------------
    print("-" * 78)
    print("%-4s %-58s %-9s %-9s %-8s %s" % ("VAKA", "ADIM", "JOB", "BEKLENEN",
                                            "GOZLENEN", "KABUK"))
    print("-" * 78)
    for etiket, ad, beklenen_serit in VAKALAR:
        job_id, idx, step = adim_bul(jobs, ad)
        if job_id is None:
            hata.append("VAKA %s: '%s' adimi deploy.yml'de BULUNAMADI (yeniden "
                        "adlandirilmis olabilir) -> vaka OLCULEMEDI" % (etiket, ad))
            continue
        gercek_serit = "B" if job_id in serit_b else "A"
        if gercek_serit != beklenen_serit:
            hata.append("VAKA %s: '%s' adimi SERIT %s'de bekleniyordu, SERIT %s'de "
                        "bulundu (job=%s)" % (etiket, ad, beklenen_serit,
                                              gercek_serit, job_id))
        beklenen_yayin = "basarili" if beklenen_serit == "B" else "atlandi"
        s = simule(jobs, {(job_id, idx)})
        gozlenen = s[yayin]
        iddia += 1
        if gozlenen != beklenen_yayin:
            hata.append("VAKA %s (%s): %s adimi kirmiziyken yayin job'u '%s' bekleniyordu, "
                        "'%s' gozlendi" % (etiket, gercek_serit, ad, beklenen_yayin, gozlenen))
        # KABUK BACAGI — adimin cikis kodu gercekten job'u kirmizi yakiyor mu
        iddia += 1
        onek = (step.get("run") or "").strip().split("\n")[0].split()[0]
        rc, kuyruk = kabuk_bacagi(step, onek)
        kabuk = "rc=%d" % rc
        if rc == 0:
            hata.append("VAKA %s: adimin `run:` govdesi basarisiz komutla bile `bash -e` "
                        "altinda rc=0 verdi -> FAIL-OPEN sarmalayici var (%s) [%s]"
                        % (etiket, ad, kuyruk.strip()[:120]))
        if _dogru(step.get("continue-on-error")):
            hata.append("VAKA %s: adim `continue-on-error: true` tasiyor -> kirmizi "
                        "yansa da job'u bozmaz (%s)" % (etiket, ad))
        print("%-4s %-58s %-9s %-9s %-8s %s"
              % (etiket, ad[:58], job_id, beklenen_yayin, gozlenen, kabuk))

    print()
    print("=" * 78)
    if hata:
        for h in hata:
            print("  ❌ " + h)
        print("SONUC: KIRMIZI ❌  (%d iddia, %d hata)" % (iddia, len(hata)))
        return 1
    print("SONUC: YESIL ✅  — %d iddia. Serit B kirmiziyken yayin CIKAR; serit A "
          "kirmiziyken yayin CIKMAZ." % iddia)
    return 0


if __name__ == "__main__":
    sys.exit(main())

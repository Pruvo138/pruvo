#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/shop-bayatlik-kapisi.py — CURUTME (mutasyon) araci.

NE OLCER: "kabul testi YESIL" demek "nobetci CANLI" demek DEGILDIR. Bu arac nobetciyi
BILEREK bozar ve kabul testinin GERCEKTEN kirmizi yandigini — ve HANGI EKSENIN yandigini
— olcer.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]):
   * her mutant kosumunda IDDIA SAYISI taban kosumla AYNI olmali — sayi dususu "mutant
     testi cokertti" demektir ve o kirmizi bir OLCUM DEGILDIR (cokme kirmiziyla karisir);
   * kirmizi EKSEN kumesi mutantin BEYANINA TAM ESIT olmali (gevsek "kapsar" olcutu YOK;
     fazladan kirmizi da kusurdur).
   * KONTROL MUTANTI (K0) zararsizdir ve kirmizi kumesi BOS olmalidir — kontrol mutanti
     olmayan bir batarya "her seye kirmizi yanan" bir testi kanit sayar.
   * 🔴 KAYITLI SURVIVOR (S1) KONTROL DEGILDIR: anlamli bir davranisi degistirdigi halde
     hicbir iddiayi kirmizi yakmayan bir mutanttir ve BILEREK, BEYANI BOS olarak tutulur.
     Isi, "bu kod parcasinin faydasi OLCULMEMISTIR" hukmunu KOSAN bir sekilde tasimaktir;
     ilgili kemer bir gun OLCULURSE bu satir SAPMA verir ve beyan guncellenir.

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyaya DOKUNULMAZ
   ([[mutasyon-diske-yazma-tuzagi]]). Kosum basinda ve sonunda kaynagin sha256'si
   karsilastirilir ve basilir.

🔴 AYNA NEDEN SENTETIK DEPO: kapinin B9/B10 iddialari GERCEK bundle kumesini (wrangler.toml
   + ithalat grafi + `git ls-files`) olcer. Ayna, gercek bundle dosyalarinin KOPYASINDAN
   kucuk bir git deposu kurar — mutant depo agacina DOKUNMADAN ayni iddialari kosar.

Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde kosulan KANIT
aracidir — repoda durmasinin sebebi kanitin YENIDEN URETILEBILIR olmasidir.

Kullanim: python3 tools/shop-bayatlik-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontrol mutanti temiz + iddia sayilari esit +
kaynak sha256 degismedi.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "shop-bayatlik-kapisi.py")

# (kod, aciklama, eski_DUZ_METIN, yeni_metin, beyan_edilen_kirmizi_eksenler)
# 🔴 DESENLER DUZ METINDIR (regex DEGIL): kacis karakteri hatasi bir mutanti sessizce
# "eslesmedi"ye dusurur ve batarya delik kalir. Eslesme sayisi 1 degilse SAPMA yazilir.
MUTANTLAR = [
    ("K0", "KONTROL — zararsiz yorum degisikligi (batarya kirmizi-sever mi?)",
     "# ---------------------------------------------------------------- zaman",
     "# ---------------------------------------------------------------- ZAMAN(K0)",
     set()),
    # G2 (360,0 dk -> BAYAT) esigin USTUNDE bir vakadir; esik 600'e cekilince o da
    # "bekliyor"a duser. Beyan OLCULEN kumeye esitlenir (gevsek "kapsar" olcutu YOK).
    ("M1", "ESIK 120 -> 600 dk (esigi YUKARI cekmek)",
     "\nESIK_DK = 120\n", "\nESIK_DK = 600\n", {"D3", "D5", "F1", "G2"}),
    ("M2", "ESIK 120 -> 30 dk (esigi ASAGI cekmek)",
     "\nESIK_DK = 120\n", "\nESIK_DK = 30\n", {"D2"}),
    # 🔴 M3 TEK SATIRLIK OLAMAZ: yalniz KOD_TASIYAN'a "secret" eklemek ETKISIZ kalir
    # (KOD_TASIMAYAN once bakilir) — ilk turda o mutant SURVIVOR verdi ve kusur MUTANTTA
    # idi, kapida degil. Etkili mutant iki sabiti BIRLIKTE degistirir.
    ("M3", "secret surumu KOD sayiliyor (olculen nesil maskelemesi geri geliyor)",
     'KOD_TASIMAYAN = frozenset(("secret",))\n'
     '# Kod tasidigi OLCULEN tetikler. Bilinmeyen bir tetik SESSIZCE kod sayilmaz: '
     'Cloudflare\n'
     '# yeni bir deger (or. `rollback`) uretirse nesil bu veriden TURETILEMEZ -> '
     'fail-closed.\n'
     'KOD_TASIYAN = frozenset(("version_upload", "deployment", "upload"))',
     'KOD_TASIMAYAN = frozenset()\n'
     'KOD_TASIYAN = frozenset(("version_upload", "deployment", "upload", "secret"))',
     {"C2"}),
    ("M4", "aktif dagitim yerine EN YUKSEK NUMARALI surum kod sayiliyor (geri alma korlugu)",
     '    aktif_id = yuzde_yuz[0]["version_id"]',
     '    aktif_id = max(surumler, key=lambda v: v["number"])["id"]',
     {"C3", "C6", "C9"}),
    ("M5", "saat sapmasi kapisi kaldirildi (simdi < kod zamani fail-open)",
     '        raise Olculemedi("saat sapmasi: \'simdi\' canli kod zamanindan ESKI")',
     "        pass", {"D6"}),
    ("M6", "goreli OLMAYAN (npm) ithalat sessizce atlaniyor",
     '            if not spec.startswith("."):\n                raise Olculemedi(',
     '            if not spec.startswith("."):\n                continue\n'
     '            if spec == "IMKANSIZ":\n                raise Olculemedi(',
     {"B5"}),
    ("M7", "izlenmeyen bundle dosyasi kapisi kaldirildi",
     "    disarda = [y for y in rel if y not in izlenen]", "    disarda = []",
     {"B6"}),
    ("M8", "$GITHUB_OUTPUT her zaman 'taze' yaziyor (fail-open sinyal)",
     '(("GITHUB_OUTPUT", "durum=%s\\n" % durum),',
     '(("GITHUB_OUTPUT", "durum=taze\\n"),', {"E1", "E2"}),
    ("M9", "geride suzgeci kaldirildi: TUM commit'ler geride sayiliyor",
     "    geride = [c for c in commitler if c[1] > kod_zamani]",
     "    geride = list(commitler)", {"D1", "D5"}),
    ("M10", "git log yol suzgeci kaldirildi (bundle DISI commit bayatlik uretiyor)",
     '             "--since=%s" % kod_zamani.isoformat(), "--", *yollar)',
     '             "--since=%s" % kod_zamani.isoformat())', {"F3"}),
    ("M11", "sig (shallow) gecmis derinlestirilmiyor -> kesik gecmis 'taze' gosteriyor",
     '        if r.stdout.strip() != "true":\n            return True',
     "        if True:\n            return True", {"F4"}),
    # 🔴 M12-M15: 4 Agu sorusturmasinda OLCULEN fail-open'in (HEAD uzak main ucunun
    # gerisindeyken sahte 'taze') kapatilmasini nobet altina alir. Dordu de TEK KIRMIZI
    # verir: her biri AYRI bir ekseni civiler, kirmizi kumesi tautoloji degildir.
    ("M12", "olculen ref ATA kontrolu etkisiz: HEAD uzak ucun GERISINDE olsa da olcum "
            "surer (4 Agu sorusturmasinda olculen sahte-taze geri geliyor)",
     '    for ad, sha in cozulen:\n'
     '        a = _git(kok, "merge-base", "--is-ancestor", sha, head)',
     '    for ad, sha in cozulen:\n'
     '        a = _git(kok, "rev-parse", "HEAD")', {"G1"}),
    ("M13", "uzak uc HIC okunamayinca 'guncel' VARSAYILIYOR (fail-open)",
     '    if not cozulen:\n'
     '        raise Olculemedi(\n'
     '            "uzak %s ucu OKUNAMADI (denenen: %s): HEAD\'in olculmesi GEREKEN ref '
     'oldugu "\n'
     '            "KANITLANAMIYOR" % (ANA_DAL, ", ".join(UZAK_UC_ADAYLARI)))',
     '    if not cozulen:\n        return head, "VARSAYIM"', {"G5"}),
    ("M14", "calisma agaci / HEAD ayrisma kapisi kaldirildi",
     "    sapan = sorted(s for s in r.stdout.splitlines() if s.strip())",
     "    sapan = []", {"G6"}),
    ("M15", "FETCH_HEAD aday uc listesinden dusuruldu -> CI'nin FIILEN kurdugu halde "
            "kanit bulunamaz (duzeltme her 15 dk'da bir YANLIS kirmizi yakardi)",
     'UZAK_UC_ADAYLARI = ("refs/remotes/origin/%s" % ANA_DAL, "FETCH_HEAD")',
     'UZAK_UC_ADAYLARI = ("refs/remotes/origin/%s" % ANA_DAL,)', {"G4"}),
    # 🔴 M16/M17 — 4 Agu 2026 KANIT-KALITESI ONARIMI. Bu iki EKSENIN (G3 · G7) ayirt
    # edici mutanti YOKTU: mutant yazildiginda kabul testi Traceback ile COKUYOR,
    # `IDDIA:` satiri BASILMIYOR ve olculen iddia sayisi 39 -> 0'a dusuyordu. rc=1
    # disaridan "kirmizi" gorunur ama olcum YOKTUR ([[mutasyon-kaniti-yeniden-uretilebilir]]).
    # Kapi tarafindaki onarim: G3/G7 cagrilari `_olcum_veya_none` ile sarildi.
    ("M16", "olculen ref ATA kontrolu TERSINE cevrildi: HEAD uzak ucun ILERISINDE "
            "olan MESRU hal (itilmemis yerel commit) OLCULEMEDI sayilir -> kapi her "
            "15 dk'da bir YANLIS kirmizi yakardi",
     '        if a.returncode == 1:\n', '        if a.returncode == 0:\n', {"G3"}),
    ("M17", "calisma agaci kontrolunun YOL SUZGECI kaldirildi: bundle DISI kirlilik "
            "(bu depoda `urunler.json` parti yazimi SUREKLI var) kapiyi OLCULEMEDI'ye "
            "dusurur -> nobetci pratikte hicbir zaman hukum veremezdi",
     '    r = _git(kok, "diff", "--name-only", "HEAD", "--", *yollar)',
     '    r = _git(kok, "diff", "--name-only", "HEAD")', {"G7"}),
    # 🔴 S1 KONTROL DEGIL, KAYITLI SURVIVOR (durust beyan, 4 Agu 2026): esitlik-once
    # kisayolunun "sig agacta yanlis kirmiziyi onler" gerekcesi OLCULMEMISTIR ve koddan
    # ERISILEBILIR DEGILDIR (ayrinti kapinin `olculen_ref_dogrula` yorumunda). Kisayol
    # devre disi birakildiginda HICBIR iddia kirmizi yanmaz. Bu satir o olcumu YENIDEN
    # URETILEBILIR kilar: beyan BOS'tur, yani batarya "bu kemer olculmuyor" hukmunu
    # KOSARAK tasir. Kisayolu bir gun OLCEN bir iddia yazilirsa bu beyan SAPMA verir.
    ("S1", "KAYITLI SURVIVOR — esitlik-once kisayolu devre disi (olculen fayda YOK: "
           "39 iddia / 0 kirmizi; kemer, koruma degil)",
     "        if sha == head:\n            return head, ad\n",
     "        if False:\n            return head, ad\n", set()),
]

IDDIA_RE = re.compile(r"^IDDIA: (\d+) · KIRMIZI: (\d+)\s*(.*)$", re.M)
EKSEN_RE = re.compile(r"^  KIRMIZI (\S+)", re.M)


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ayna_kur(hedef):
    """Gercek bundle dosyalarinin KOPYASINDAN kucuk bir git deposu kur."""
    sys.path.insert(0, TOOLS)
    import importlib.util
    spec = importlib.util.spec_from_file_location("_kapi", KAPI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _ad, giris = mod.wrangler_giris(mod.WRANGLER_TOML)
    yollar = mod.bundle_dosyalari(ROOT, os.path.join(mod.SHOP, giris),
                                  mod.izlenen_kume(ROOT))
    yollar = list(yollar) + ["shop/wrangler.toml"]
    for y in yollar:
        kaynak = os.path.join(ROOT, y)
        varis = os.path.join(hedef, y)
        os.makedirs(os.path.dirname(varis), exist_ok=True)
        shutil.copy2(kaynak, varis)
    os.makedirs(os.path.join(hedef, "tools"), exist_ok=True)
    subprocess.run(["git", "-C", hedef, "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", hedef, "config", "user.email", "m@m"], check=True)
    subprocess.run(["git", "-C", hedef, "config", "user.name", "m"], check=True)
    subprocess.run(["git", "-C", hedef, "add", "-A"], check=True)
    subprocess.run(["git", "-C", hedef, "commit", "-q", "-m", "ayna"], check=True)
    return len(yollar)


def kos(ayna_kapi):
    r = subprocess.run([sys.executable, ayna_kapi, "--kendini-test"],
                       capture_output=True, text=True, timeout=600)
    m = IDDIA_RE.search(r.stdout)
    if not m:
        return None, None, r
    return int(m.group(1)), set(EKSEN_RE.findall(r.stdout)), r


def main():
    kaynak_sha_bas = sha(KAPI)
    print("kaynak sha256 (bas): %s" % kaynak_sha_bas)
    with open(KAPI, encoding="utf-8") as f:
        temiz = f.read()

    with tempfile.TemporaryDirectory() as t:
        n_dosya = ayna_kur(t)
        ayna_kapi = os.path.join(t, "tools", "shop-bayatlik-kapisi.py")
        with open(ayna_kapi, "w", encoding="utf-8") as f:
            f.write(temiz)

        taban_n, taban_kirmizi, r0 = kos(ayna_kapi)
        if taban_n is None:
            print(r0.stdout[-2000:], r0.stderr[-1000:])
            sys.exit("TABAN kosumu iddia satiri basmadi — olcum YOK")
        print("ayna: %d bundle dosyasi · TABAN iddia=%d kirmizi=%s"
              % (n_dosya, taban_n, sorted(taban_kirmizi) or "-"))
        if taban_kirmizi:
            sys.exit("TABAN kirmizi — mutasyon olcumu anlamsiz")

        hatali = []
        for kod, aciklama, desen, yeni, beyan in MUTANTLAR:
            adet = temiz.count(desen)
            mutant = temiz.replace(desen, yeni, 1)
            if adet != 1:
                hatali.append("%s: desen 1 kez eslesmedi (%d)" % (kod, adet))
                print("  %-4s BASARISIZ — desen eslesmedi" % kod)
                continue
            with open(ayna_kapi, "w", encoding="utf-8") as f:
                f.write(mutant)
            n, kirmizi, r = kos(ayna_kapi)
            if n is None:
                hatali.append("%s: kabul testi COKTU (iddia satiri yok)" % kod)
                print("  %-4s COKTU — %s" % (kod, (r.stderr or "").strip()[-160:]))
                continue
            if n != taban_n:
                hatali.append("%s: iddia sayisi %d != taban %d (cokme kirmiziyla karisir)"
                              % (kod, n, taban_n))
            if kirmizi != beyan:
                hatali.append("%s: kirmizi %s != beyan %s"
                              % (kod, sorted(kirmizi), sorted(beyan)))
            durum = "UYDU" if (n == taban_n and kirmizi == beyan) else "SAPMA"
            print("  %-4s %-6s iddia=%d kirmizi=%s  beyan=%s  | %s"
                  % (kod, durum, n, sorted(kirmizi) or "-", sorted(beyan) or "-",
                     aciklama))

    kaynak_sha_son = sha(KAPI)
    print("kaynak sha256 (son): %s  %s"
          % (kaynak_sha_son, "DEGISMEDI" if kaynak_sha_son == kaynak_sha_bas
             else "🔴 DEGISTI"))
    if kaynak_sha_son != kaynak_sha_bas:
        hatali.append("canli kaynak degisti — mutasyon aynaya sinirli KALMADI")

    # TEK-KIRMIZI HARITASI: her eksen icin kirmizi kumesi TAM {eksen} olan mutant var mi
    tekil = {}
    for kod, _a, _d, _y, beyan in MUTANTLAR:
        if len(beyan) == 1:
            tekil.setdefault(sorted(beyan)[0], []).append(kod)
    print("tek-kirmizi haritasi (ayirt edici mutanti OLAN eksenler): %s"
          % ", ".join("%s<-%s" % (e, "/".join(k)) for e, k in sorted(tekil.items())))

    print("\nMUTANT: %d · SAPMA: %d" % (len(MUTANTLAR), len(hatali)))
    for h in hatali:
        print("  🔴 " + h)
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())

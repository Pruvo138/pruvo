#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/urunler-guard-provenans-mutasyon.py — CURUTME (mutasyon) araci.

NE OLCER: "kabul testi YESIL" demek "koruma CANLI" demek DEGILDIR. Bu arac
urunler-guard.py / urunler-guard-hook.py'yi — ve testin KENDI mekanizmalari
(ortam temizligi X1, belge capasi X2) icin kabul testinin kendisini — BILEREK
bozar, sonra tools/urunler-guard-provenans-test.py'nin GERCEKTEN kirmizi
yandigini ve HANGI EKSENIN yandigini olcer.

🔴 KABUL = CIKIS KODU DEGIL, OLCULEN IDDIA SAYISI + ISARET SARTI
   ([[mutasyon-kaniti-yeniden-uretilebilir]]):
   * her mutant kosumunda IDDIA SAYISI taban kosumla AYNI olmali — sayi dususu
     "mutant testi cokertti" demektir ve o kirmizi bir OLCUM DEGILDIR;
   * ciktida `Traceback` GORUNMEMELI;
   * kirmizi EKSEN kumesi mutantin BEYANINA TAM ESIT olmali (gevsek "kapsar"
     olcutu YOK; fazladan kirmizi da kusurdur);
   * KONTROL MUTANTI (K0) zararsizdir ve kirmizi kumesi BOS olmalidir.

🔴 GUVENLIK: mutasyon yalnizca gecici bir AYNAYA uygulanir; canli dosyalara
   DOKUNULMAZ ([[mutasyon-diske-yazma-tuzagi]]). Kosum basinda ve sonunda her iki
   kaynagin sha256'si karsilastirilir ve basilir. Kabul testi kendi gecici git
   depolarini kurdugu icin GERCEK urunler.json'a da hic dokunulmaz.

Bu arac bir CI adimi DEGILDIR (yavas, kasitli-bozuk kopyalar uretir); elde
kosulan KANIT aracidir — repoda durmasinin sebebi kanitin YENIDEN
URETILEBILIR olmasidir.

Kullanim: python3 tools/urunler-guard-provenans-mutasyon.py
Cikis 0 = her mutant beyanina UYDU + kontrol temiz + iddia sayilari esit +
kaynak sha256'lari degismedi.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
GUARD = os.path.join(TOOLS, "urunler-guard.py")
KOPRU = os.path.join(TOOLS, "urunler-guard-hook.py")
TEST = os.path.join(TOOLS, "urunler-guard-provenans-test.py")

# Mutasyon hedefleri. T (kabul testinin KENDISI) yalnizca testin KENDI
# mekanizmalarini — ortam temizligi (X1) ve belge capasi (X2) — oldurulebilir
# kilmak icin vardir: bu ikisi guard'da degil TESTTE yasar, dolayisiyla guard'i
# bozarak olculemezler. Aynada mutasyonlu test kopyasi kosar; --kaynak/--kaynak-kopru
# hep ACIKCA verildigi icin kopyanin kendi varsayilanlari devreye girmez.
G, K, T = "guard", "kopru", "test"

# Mutasyon AYNAYA uygulanir; su BES canli dosyanin sha256'si kosum basinda ve
# sonunda karsilastirilir (mutasyon araci hicbirine YAZMAZ).
IZLENEN = (
    GUARD, KOPRU, TEST,
    os.path.abspath(__file__),
    os.path.join(os.path.dirname(TOOLS), ".github", "workflows", "deploy.yml"),
)

# (kod, aciklama, HEDEF_DOSYA, eski_DUZ_METIN, yeni_metin, beyan_edilen_kirmizi)
# 🔴 DESENLER DUZ METINDIR (regex DEGIL). Eslesme sayisi 1 degilse SAPMA yazilir.
MUTANTLAR = [
    ("K0", "KONTROL — zararsiz yorum degisikligi (batarya kirmizi-sever mi?)", G,
     "# ----------------------------------------------------------------- provenans",
     "# ------------------------------------------------------------ PROVENANS(K0)",
     set()),

    # M1 OLCUMU: provenans olmadan merge replay'i SESSIZCE bozulmaz — REDDEDILIR
    # (P5 rc=0 duser). P1-P4 yesil KALIR cunku ILKE 2 veriyi korur. Bu iki ilkenin
    # birlikte olcumudur: merge korlugu + fail-loud = veri kaybi YOK, GURULTU VAR.
    # (Ikisi BIRLIKTE kaldirilinca olay geri gelir -> M9.)
    ("M1", "PROVENANS NO-OP: merge halinde yalniz HEAD ebeveyn sayiliyor", G,
     'def _ebeveyn_halleri(uid, ebeveynler):\n'
     '    """uid icin ebeveynlerdeki KANONIK hallerin kumesi '
     '(id\'i olmayan ebeveyn atlanir)."""\n'
     '    return {_canon(by_id[uid]) for by_id in ebeveynler if uid in by_id}',
     'def _ebeveyn_halleri(uid, ebeveynler):\n'
     '    """M1: MERGE_HEAD ebeveyni gormezden gelinir."""\n'
     '    ilk = ebeveynler[:1]\n'
     '    return {_canon(by_id[uid]) for by_id in ilk if uid in by_id}',
     {"P5", "E3"}),

    ("M2", "FAIL-LOUD -> SESSIZ GERI SARMA (merge'de belirsiz hal geri sariliyor)", G,
     "        if merge_mi:\n"
     "            # ILKE 2 — hangi ebeveyne geri sarilacagi BELIRSIZ; "
     "SESSIZ MUTASYON YOK.\n"
     "            belirsizler.append(\n"
     '                "%s: merge halinde WT hali HICBIR EBEVEYNE uymuyor, beyan da yok "\n'
     '                "(izinsiz alanlar: %s)" % (uid, ",".join(sorted(unauth))))\n'
     "            continue\n",
     "        if merge_mi:\n"
     "            pass  # M2: sessiz geri sarmaya geri donuldu\n",
     # E4 de duser: sessizce geri saran guard RED BLOGUNU hic basmaz -> belgelenen
     # cikis yollari ekrana da gelmez.
     {"B1", "B2", "B5", "E1", "E4", "H1"}),

    ("M3", "KORUMA ETKISIZ: izinsiz alan degisimi ARTIK GERI SARILMIYOR", G,
     '        # Merge DISI: tek ebeveyn var, provenans KESIN olarak "izinsiz" '
     '-> dar geri sarma.\n'
     "        wt_list[i] = copy.deepcopy(head_p)\n"
     "        restored.append((uid, sorted(changed)))",
     "        # M3: geri sarma yazimi kaldirildi\n"
     "        restored.append((uid, sorted(changed)))",
     # X1 de duser: X1'in POZITIF CAPASI izin BEKLENEN degerini (geri sarilmis
     # katalogun sha'si) sart kosar, geri sarma olmayinca capa kirilir. Bu ortusme
     # capanin BEDELIDIR ve BEYAN EDILMISTIR; X1'i AYIRT EDEN mutantlar M16/M18-M21.
     {"K1", "X1"}),

    ("M4", "KORUMA ETKISIZ: izinsiz SILME artik geri EKLENMIYOR", G,
     "    for uid in silinen:\n"
     "        wt_list.insert(0, copy.deepcopy(head_by_id[uid]))",
     "    for uid in silinen:\n"
     "        pass  # M4",
     {"K2"}),

    ("M5", "GORUNURLUK KAPATILDI: geri sarma stderr'e basilmiyor", G,
     '        _bas("!! urunler-guard (%s): KATALOG DEGISTIRILDI — '
     'izinsiz degisim geri alindi."\n'
     "             % tetik)\n"
     "        for uid, fs in restored:\n"
     '            _bas("   GERI SARILDI  %s  alanlar: %s" % (uid, ", ".join(fs)))',
     "        for uid, fs in restored:\n"
     "            pass  # M5",
     # X1 de duser: capanin ucuncu bileseni "GERI SARILDI stderr'e basildi" bayragi.
     {"G1", "X1"}),

    ("M6", "BOZUK WT SESSIZ ATLANIYOR (eski fail-open)", G,
     '        raise Belirsiz("working-tree urunler.json BOZUK JSON",\n'
     '                       "HEAD\'e sifirlamak tum yeni urunleri silerdi; '
     'hukum verilemez (%r)" % e)',
     '        _log("%s: bozuk JSON — atlandi (%r)" % (tetik, e))  # M6\n'
     '        return "bozuk-atlandi"',
     {"B3"}),

    ("M7", "KOPRU YUTUYOR: guard'in RED hukmu PreToolUse'a tasinmiyor", K,
     '    if p.returncode != 0:\n'
     '        return _blokla("!! urunler-guard REDDETTI (rc=%d) — %s bloklandi."\n'
     '                       % (p.returncode, tetik), p.stderr)',
     "    if p.returncode != 0:\n"
     "        return 0  # M7",
     {"H1"}),

    ("M8", "GUARD'IN KENDI HATASI SESSIZCE YUTULUYOR (eski fail-open)", G,
     "    except Exception as e:\n"
     "        # Eskiden bu hal SESSIZCE exit 0 verirdi: guard KOSMAMIS oluyordu ama\n"
     "        # commit yesil geciyordu. Koruma kosmadiysa commit GECMEZ.\n"
     '        return _reddet(args.tetik, "GUARD BEKLENMEDIK HATA", repr(e))',
     "    except Exception as e:\n"
     '        _log("beklenmedik hata %r — bloklamadan cikildi." % (e,))  # M8\n'
     "        return 0",
     {"B6"}),

    ("M9", "ESKI GUARD (4 Agu OLAYI): merge hali HIC GORULMUYOR", G,
     '    rc, out = _git("rev-parse", "--absolute-git-dir")\n'
     "    if rc != 0:\n"
     '        raise Belirsiz("GIT DIZINI OKUNAMADI",',
     "    return None  # M9: merge korlugu geri getirildi\n"
     '    rc, out = _git("rev-parse", "--absolute-git-dir")\n'
     "    if rc != 0:\n"
     '        raise Belirsiz("GIT DIZINI OKUNAMADI",',
     {"P1", "P2", "P3", "P4", "M1", "B1", "B2", "B4", "B5", "E1", "E3", "E4", "H1"}),

    # "Hicbir ebeveynde olmayan id SERBESTTIR" ekseni beyan edilmis bir SURVIVOR
    # olmasin diye AYIRT EDICI mutant: yeni-urun muafiyeti kaldirilinca hem mesru
    # parti (N1) hem merge'in getirdigi yeni urun (M2/M3) REDDEDILIR.
    ("M10", "YENI URUN MUAFIYETI KALDIRILDI (mesru parti bloklanir)", G,
     "        if not halleri:\n"
     "            yeni += 1",
     "        if False:  # M10\n"
     "            yeni += 1",
     {"N1"}),

    # M2/M3 iddialari beyan edilmis SURVIVOR olmasin diye ayirt edici mutantlar:
    ("M11", "YALNIZ MERGE_HEAD'de olan urunun provenansi TANINMIYOR", G,
     "        # ILKE 1 — PROVENANS: WT hali herhangi bir EBEVEYNIN hali ise MESRUDUR.\n"
     "        if _canon(p) in halleri:",
     "        # M11\n"
     "        if _canon(p) in halleri and uid in head_by_id:",
     {"M2", "M3"}),

    ("M12", "MANIFEST BEYANI GORMEZDEN GELINIYOR (mesru duzeltme bloklanir)", G,
     "        unauth = [c for c in changed if not _authorized(uid, c, p, manifest)]",
     "        unauth = list(changed)  # M12",
     {"K3", "M3", "E2"}),

    # KOPRUNUN YANLIS-POZITIF ekseni de oldurulebilir olmali (H2/H3 dekor DEGIL):
    ("M13", "KOPRU HER HALDE BLOKLUYOR (mesru commit de bloklanir)", K,
     '    if p.returncode != 0:\n'
     '        return _blokla("!! urunler-guard REDDETTI (rc=%d) — %s bloklandi."',
     '    if True:  # M13\n'
     '        return _blokla("!! urunler-guard REDDETTI (rc=%d) — %s bloklandi."',
     {"H2"}),

    ("M14", "KOPRU GIT-DISI KOMUTTA DA GUARD KOSTURUYOR", K,
     "    tetik = _tetik(command)\n"
     "    if not tetik:\n"
     "        return 0",
     '    tetik = _tetik(command) or "commit"  # M14\n'
     "    if not tetik:\n"
     "        return 0",
     {"H3"}),

    # IKIZ TANIM AYRISMASI ([[ikiz-tanim-sessiz-ayrisma]]): CIKIS_YOLLARI listesi AYNEN
    # dururken BASILAN metin ondan sapiyor -> "belgelenen cikis yolu" bayatlar.
    ("M15", "BASILAN CIKIS METNI listeden AYRISIYOR (yalniz ilk yol basiliyor)", G,
     "    for kod, tarif in CIKIS_YOLLARI:\n"
     '        _bas("     [%s] %s" % (kod, tarif))',
     "    for kod, tarif in CIKIS_YOLLARI[:1]:  # M15\n"
     '        _bas("     [%s] %s" % (kod, tarif))',
     {"E4"}),

    # ORTAM SIZINTISI: temizlik kaldirilinca miras alinan GIT_* hem fikstur
    # depolarini hem guard'in `git -C ROOT` cagrilarini YABANCI depoya baktirir.
    # X1 DIFERANSIYEL oldugu icin (temiz kosum vs kirli kosum) bu mutant TEK
    # KIRMIZI yakar: guard'in davranisi degismez, yalnizca iki taraf AYRISIR.
    ("M16", "ORTAM SIZINTISI: alt-surec env'inden GIT_* depo degiskenleri SILINMIYOR", T,
     "    for ad in SIZINTI_ENV:\n"
     "        e.pop(ad, None)\n",
     "    # M16: sizinti temizligi kaldirildi\n",
     {"X1"}),

    # BELGE CAPASI: docstring'deki sayi ile len(KODLAR) ayrisirsa X2 kirmizi
    # yanmali — yoksa "TAM N IDDIA" satiri bir daha sessizce bayatlar.
    ("M17", "BELGE AYRISMASI: docstring'deki iddia sayisi KODLAR'dan sapiyor", T,
     "TAM 28 `IDDIA:`",
     "TAM 27 `IDDIA:`",
     {"X2"}),

    # 🔴 X1'IN OLCUM DEGERI — dort mutant, "iddia yesil ama HICBIR SEY olcmuyor"
    # ailesini kapatir. X1 salt diferansiyelken (yalniz temiz==kirli) DORDU DE
    # HAYATTA KALIYORDU; pozitif capa + POTENS kontrolu eklendikten sonra dordu de
    # oluyor. Bu mutantlar olmadan X1'in yesili "olcum tamamen yok edilmis" haliyle
    # UYUMLUYDU ([[fikstur-degeri-mutasyon-koru]], [[beyan-edilmis-survivor]]).
    ("M18", "IZ URETIMI BOSALTILDI: _koruma_izi SABIT donduruyor", T,
     '    d = kur_depo(guard, kopru, [GUNCEL], env=env)\n'
     '    kat = oku_katalog(d)\n'
     '    kat[0]["fiyat"] = "9999 TL"\n'
     '    kat[0].pop("lisans", None)\n'
     '    yaz_katalog(d, kat)\n'
     '    rc, _o, err = kos_guard(d, env=env)\n'
     '    return (rc, sha(d), "GERI SARILDI" in err)',
     '    return (0, "M18-SABIT", True)',
     {"X1"}),

    ("M19", "KARSILASTIRMA SABITLENDI: _iz_esit her zaman True", T,
     "    return iz == beklenen",
     "    return True  # M19",
     {"X1"}),

    # NOT (olculdu): "degerleri BOS STRING yap" bu ekseni OLCMEZ — git bos
    # GIT_DIR/GIT_WORK_TREE'yi de bozuk sayar, yani kirli taraf HALA potenttir ve
    # X1 hakli olarak yesil kalir. Ekseni gercekten olcen mutant, kirli ortamin
    # HIC KURULMAMASIDIR: o zaman POTENS kontrolu (ham kosum SAPMALI) kirilir.
    ("M20", "KIRLI TARAF ZARARSIZLASTIRILDI: kirli ortam HIC kurulmuyor", T,
     "        os.environ.update(kirli)\n",
     "        pass  # M20: kirli ortam hic kurulmadi\n",
     {"X1"}),

    ("M21", "IZ DARALTILDI: sha + geri-sarma bayragi dusuruldu, yalniz rc kaldi", T,
     '    return (rc, sha(d), "GERI SARILDI" in err)',
     "    return (rc,)  # M21",
     {"X1"}),
]

IDDIA_RE = re.compile(r"^IDDIA: (\S+) (YESIL|KIRMIZI)\b")


def sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def kos(guard_yol, kopru_yol, test_yol=TEST):
    p = subprocess.run([sys.executable, test_yol,
                        "--kaynak", guard_yol, "--kaynak-kopru", kopru_yol],
                       capture_output=True, text=True)
    cikti = p.stdout + p.stderr
    kirmizi, toplam = set(), 0
    for satir in p.stdout.splitlines():
        m = IDDIA_RE.match(satir)
        if not m:
            continue
        toplam += 1
        if m.group(2) == "KIRMIZI":
            kirmizi.add(m.group(1))
    return kirmizi, toplam, ("Traceback" in cikti)


def ayna(kod, hedef, eski, yeni):
    """Gecici aynada mutasyonu uygula -> (guard_yolu, kopru_yolu, test_yolu, hata)."""
    d = tempfile.mkdtemp(prefix="guard-mutant-%s-" % kod)
    gy = os.path.join(d, "urunler-guard.py")
    ky = os.path.join(d, "urunler-guard-hook.py")
    ty = os.path.join(d, "urunler-guard-provenans-test.py")
    shutil.copy(GUARD, gy)
    shutil.copy(KOPRU, ky)
    shutil.copy(TEST, ty)
    yol = {G: gy, K: ky, T: ty}[hedef]
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    n = metin.count(eski)
    if n != 1:
        return gy, ky, ty, "DESEN %d kez eslesti (1 bekleniyordu)" % n
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin.replace(eski, yeni, 1))
    return gy, ky, ty, None


def main():
    once = {y: sha(y) for y in IZLENEN}
    print("URUNLER-GUARD PROVENANS — MUTASYON BATARYASI")
    print("  CANLI DOSYA sha256 (once):")
    for y in IZLENEN:
        print("    %s  %s" % (once[y], os.path.relpath(y, os.path.dirname(TOOLS))))

    t_kirmizi, t_toplam, t_tb = kos(GUARD, KOPRU)
    print("\nTABAN: iddia=%d kirmizi=%d traceback=%s" % (t_toplam, len(t_kirmizi), t_tb))
    sapma = []
    if t_kirmizi:
        sapma.append("TABAN kirmizi degil: %s" % sorted(t_kirmizi))
    if t_tb:
        sapma.append("TABAN kosumunda Traceback")

    print("\n%-4s %-6s %-6s %s" % ("KOD", "IDDIA", "TB", "KIRMIZI KUME (beyan -> olculen)"))
    for kod, aciklama, hedef, eski, yeni, beyan in MUTANTLAR:
        gy, ky, ty, hata = ayna(kod, hedef, eski, yeni)
        if hata:
            sapma.append("%s: %s" % (kod, hata))
            print("%-4s %-6s %-6s !! %s" % (kod, "-", "-", hata))
            continue
        kirmizi, toplam, tb = kos(gy, ky, ty)
        uydu = (kirmizi == beyan)
        if toplam != t_toplam:
            sapma.append("%s: iddia sayisi %d != taban %d (mutant testi COKERTTI)"
                         % (kod, toplam, t_toplam))
        if tb:
            sapma.append("%s: ciktida Traceback (cokme kirmiziyla karisir)" % kod)
        if not uydu:
            sapma.append("%s: beyan %s != olculen %s" % (kod, sorted(beyan), sorted(kirmizi)))
        print("%-4s %-6d %-6s %s %s -> %s   %s"
              % (kod, toplam, "VAR" if tb else "yok",
                 "OK " if uydu else "!! ", sorted(beyan), sorted(kirmizi), aciklama))

    sonra = {y: sha(y) for y in IZLENEN}
    print("\n  CANLI DOSYA sha256 (sonra):")
    for y in IZLENEN:
        esit = once[y] == sonra[y]
        if not esit:
            sapma.append("CANLI DOSYA DEGISTI: %s" % y)
        print("    %s  %-6s %s" % (sonra[y], "AYNI" if esit else "DEGISTI",
                                   os.path.relpath(y, os.path.dirname(TOOLS))))

    print("\nMUTANT=%d  TABAN_IDDIA=%d  SAPMA=%d" % (len(MUTANTLAR), t_toplam, len(sapma)))
    for s in sapma:
        print("  SAPMA: %s" % s)
    return 0 if not sapma else 1


if __name__ == "__main__":
    sys.exit(main())

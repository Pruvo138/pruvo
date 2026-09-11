#!/usr/bin/env python3
"""PreToolUse (Bash) kancasi: onay penceresi TETIKLEYEN komut biçimlerini RAPOR eder.

=== 11 EYL 2026 — REDDETME YETKISI KALDIRILDI (OKAN EMRI) ======================
🔴 OKAN (11 Eyl, birebir): "tum tikayicilari kaldir".
Kapi 17 Tem'de "insan onayi yerine MAKINE reddi" diye kurulmustu (Okan: "midem
bulandi" — pencere yerine otomatik geri tepme). O GEREKCE BUGUN YOK: bu oturumlar
`bypassPermissions` ile kosuyor (`.claude/settings.json::permissions.defaultMode`)
ve ustune `PermissionRequest` kancasi her istegi `allow`a bagliyor — yani ONAY
PENCERESI ZATEN DUSMUYOR. Kapinin kalan tek fiili etkisi MIMARI DURDURMAKTI.

OLCULEN ARIZA (11 Eyl, kapinin kendisine dogrudan cagriyla — 3 vaka):
  * `echo "x=$?"`                          -> deny ($ genisletmesi)
  * `python3 tools/defter-kota-kapisi.py ... ; echo "RC=$?"` -> deny (ayni kol,
    bu turda mimari IKI KEZ durdurdu: rc okumak bir OLCUMDUR, is baslatma degil)
  * `git commit -m "kutu 250 -> 500 oldu"`  -> deny (cikti yonlendirme (>))
Ucuncusu sinifin en kotusu: YONLENDIRME YOKTU, `->` yalnizca COMMIT MESAJININ
METNINDE geciyordu. Metin icerigi komut sanildi.

🔴 ARTIK: `deny` DONMEZ. Bulgular stderr'e TEK SATIR olarak yazilir ve cikis 0'dir.
🔴 stdout BOS BIRAKILIR — `allow` karari stdout'a JSON olarak BASILMAZ. Sebep
   olculmus: bu kanca PreToolUse/Bash zincirinde ILK sirada (settings.json) ve
   ardindan `urunler-guard-hook.py`, `parti-kapisi.py`, `mimar-icra-kapisi.py`
   kosuyor. Buradan `allow` basmak o nobetcilerin `deny`ini EZERDI — yani bir
   tikayiciyi kaldirirken UC nobetciyi birden kor ederdi. (Ayni gerekce kardes
   kapida da yazili: `mimar-kod-kilidi.py::iz_bas`.)

=== TIRNAK-DUYARLI AYRISTIRMA (ayni kalemin parcasi) ==========================
🔴 METIN ICINDEKI `>` KOMUT SAYILMAZ. Eski surum komutun TAMAMINI ham dizge olarak
tariyordu; olculen menzil (11 Eyl, 10 vaka):
  * `git commit -m "kutu 250 -> 500 oldu"`   -> DENY  (SAHTE: metin)
  * `git commit -m "A -> B tasindi"`          -> DENY  (SAHTE: metin)
  * `git merge -m "kapsam 225/0->224/1 ..."`  -> ALLOW (bosluk yok, desene denk gelmiyor)
  * `grep x y.md 2>/dev/null | grep z`        -> ALLOW (lookbehind `2`yi eliyor)
  * `python3 tools/durum.py > /tmp/x.txt`     -> DENY  (GERCEK yonlendirme)
Yani tetik "`>` ardindan BOSLUK" idi ve tirnak icini hic ayirt etmiyordu.

🔴 MASKE SINIFI HER DESEN ICIN AYRIDIR — POSIX KABUK SEMANTIGI. Bu ayrimi ILK
onarimda atlayip hepsini AYNI maskeyle taradim; kendi kabul probum yakaladi:
`echo "x=$?"` yanlislikla "metin" sayildi, oysa GERCEK kabukta `"$?"` GENISLER.
Dogru sinif:
  * "HEPSI"  -> desen TEK ve CIFT tirnak icinde LITERALDIR (kabuk onu operator
                saymaz): `>` yonlendirme, `<<` heredoc, `for`/`while`.
  * "TEKIL"  -> desen yalniz TEK tirnak icinde literaldir; CIFT tirnakta GENISLER:
                `$...` degisken/komut genisletmesi.
Yanlis sinif iki yonde de hata uretir: HEPSI secilirse gercek genisletme gozden
kacar (kapi kor), TEKIL secilirse commit mesajindaki `->` komut sanilir (bugunku
ariza).
"""
import json
import re
import sys

try:
    girdi = json.load(sys.stdin)
except Exception:
    sys.exit(0)

komut = (girdi.get("tool_input") or {}).get("command") or ""

YASAK = [
    (r"<<", "heredoc (<<)", "HEPSI"),
    (r"\$[A-Za-z_{(?@#!]", "kabuk değişkeni/genişletmesi ($...)", "TEKIL"),
    (r"(?<![0-9<>])>(?!&)\s", "çıktı yönlendirme (>)", "HEPSI"),
    (r"(?m)^\s*for\s+\w+\s+in\s", "for döngüsü", "HEPSI"),
    (r"(?m)^\s*while\s+", "while döngüsü", "HEPSI"),
]


def tirnaklari_maskele(metin, cift_de_maskele):
    """Tirnakli bolumleri ESIT UZUNLUKTA bosluga cevirir (kabuk semantigi).

    `cift_de_maskele=True`  -> tek VE cift tirnak maskelenir ("HEPSI" sinifi).
    `cift_de_maskele=False` -> YALNIZ tek tirnak maskelenir ("TEKIL" sinifi);
                               cift tirnak icerigi TARAMADA KALIR cunku orada
                               `$` gercekten genisler.

    Kurallar (POSIX kabuk, sade hali):
      * '...'  tek tirnak: icinde KACIS YOK, ilk kapanista biter.
      * "..."  cift tirnak: `\\` bir sonraki karakteri kacirir.
      * tirnak DISINDA `\\x` -> x kacirilmis sayilir (or. `\\$` genisletme DEGIL).
    Kapanmamis tirnak: kalan kismin TAMAMI tirnak ici sayilir (fail-safe — bu kapi
    artik RAPOR uretir, yanlis-pozitif raporu yalnizca gurultudur).

    UZUNLUK KORUNUR: maskelenen her karakter tek bir bosluga doner, boylece desen
    eslesmelerinin indeksi gercek komuttaki konumla AYNI kalir (assert ile olculur).
    """
    cikti = []
    i = 0
    n = len(metin)
    while i < n:
        k = metin[i]
        if k == "\\" and i + 1 < n:
            # Kacis: iki karakteri de "metin" say (genisletme tetiklemez).
            cikti.append(" ")
            cikti.append(" ")
            i += 2
            continue
        if k == "'":
            cikti.append(" ")
            i += 1
            while i < n and metin[i] != "'":
                cikti.append(" ")
                i += 1
            if i < n:
                cikti.append(" ")
                i += 1
            continue
        if k == '"':
            cikti.append(" ")
            i += 1
            while i < n and metin[i] != '"':
                if metin[i] == "\\" and i + 1 < n:
                    cikti.append(" ")
                    cikti.append(" ")
                    i += 2
                    continue
                # CIFT TIRNAK ICI: sinifa gore maskelenir ya da TARAMADA KALIR.
                cikti.append(" " if cift_de_maskele else metin[i])
                i += 1
            if i < n:
                cikti.append(" ")
                i += 1
            continue
        cikti.append(k)
        i += 1
    return "".join(cikti)


TARAMA = {
    "HEPSI": tirnaklari_maskele(komut, True),
    "TEKIL": tirnaklari_maskele(komut, False),
}
for _sinif, _metin in TARAMA.items():
    assert len(_metin) == len(komut), "maskeleme uzunlugu bozdu (konum raporu kayar)"

bulunan = [ad for desen, ad, sinif in YASAK if re.search(desen, TARAMA[sinif])]

# 🔴 TIRNAK ICINDE KALIP DUSEN desenler AYRICA sayilir: "kapi ne yakalamayi BIRAKTI"
# sorusu olculebilir kalsin diye. Bu sayi bir KARAR tasimaz, yalniz TANI.
ham_bulunan = [ad for desen, ad, _s in YASAK if re.search(desen, komut)]
tirnakta_dusen = [ad for ad in ham_bulunan if ad not in bulunan]

if bulunan:
    sys.stderr.write(
        "KOMUT STILI UYARISI (RED DEGIL, cikis 0): " + ", ".join(bulunan) +
        " — CLAUDE.md KOMUT STILI onerisi: betigi Write ile bir .py dosyasina yaz ve "
        "tam yolla duz calistir. 11 Eyl 2026'dan beri bu kapi REDDETMEZ (Okan: "
        "\"tum tikayicilari kaldir\").\n")
if tirnakta_dusen:
    sys.stderr.write(
        "KOMUT STILI TANI: " + ", ".join(tirnakta_dusen) +
        " deseni yalnizca TIRNAK ICINDE (metin olarak) gecti — komut sayilmadi.\n")

sys.exit(0)

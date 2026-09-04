#!/usr/bin/env python3
"""BAGLAM KOTASI KAPISI — PreToolUse (BaBa emri, 4 Eyl 2026).

NEDEN VAR — OLCULDU, TAHMIN DEGIL (BaBa filo olcumu, her evin son transkripti):
  zirve/tur — KraL 316K/257 · MaCiT 370K/310 · TeKiN 477K/284 · ArTisT 174K/70 ·
  HocA 346K/170 · FaR 446K/442. **Bes evin dordu 250K esiginin USTUNDE calisti.**
  Acilis baglami her evde 84-89K (makine geneli taban; harness + arac semalari).
  Her tur TUM baglami yeniden faturalar -> uzun oturum katlanarak pahalilasir ve
  mimar "bir sey daha bakayim" diyerek kapanisi ERTELER.

NE YAPAR (iki esik, iki ayri kol):
  UYARI  (>=350 tur VEYA >=200K): araci GECIRIR, uyari satiri basar.
  RED    (>=400 tur VEYA >=250K): YALNIZ KAPANIS-SINIFI arac gecer; gerisi RED
         "ONCE kapanis + /clear". Kapanis sinifi = defteri/kutuyu yazmak, commit/push
         etmek ve okuma/olcme (grep/ls/git status) — yani oturumu KAPATMAYA yarayan
         her sey. Boylece kapi, kapanmasini istedigi seyi ENGELLEMEZ
         ([[koruma-kurali-korudugunu-durdurur]]).
  MEKANIK (kod/test dosyasina >=15 Write): RED "mekanik is m3'e" — hacim isi ucuz kata.

🔴 FAIL-OPEN, SESSIZ DEGIL: transkript okunamazsa/bicim degisirse kapi ISI DURDURMAZ
  (yanlis pozitif tum filoyu kilitler) ama `OLCULEMEDI` satirini stderr'e basar —
  [[olculemedi-bypass-degil-menzil-daraltmasi]]. Bypass DEGIL, menzil daraltmasidir.

🔴 OLCUM EKSENI TEK: baglam boyu = SON asistan mesajinin `usage` toplamidir
  (input + cache_read + cache_creation). "Toplam uretilen jeton" DEGIL — faturalanan
  sey her turda yeniden gonderilen BAGLAMDIR. Tur sayisi ayri eksendir; ikisi VEYA
  ile baglanir cunku biri digerini yakalamaz (kisa turlu-buyuk baglam ve tersi).
"""
import json
import os
import re
import sys

# ── ESIKLER (BaBa emri; sayilar filo olcumunden) ──────────────────────────────────
UYARI_TUR = 350
UYARI_JETON = 200_000
RED_TUR = 400
RED_JETON = 250_000
MEKANIK_WRITE = 15          # kod/test dosyasina Write sayisi

# Kod/test sayilan uzantilar (mekanik kol). Defter/kutu/markdown BURADA DEGIL:
# onlar kapanis yuzeyidir, mekanik hacim isi degildir.
KOD_UZANTILARI = (".py", ".js", ".mjs", ".ts", ".tsx", ".sql", ".sh", ".json")

# ── KAPANIS SINIFI — RED esiginde GECEN tek kume ──────────────────────────────────
# Defter/kutu dosya adlari (Write/Edit hedefi bunlardan biriyse kapanis sayilir).
KAPANIS_DOSYA_DESENI = re.compile(
    r"(DEVAM\.md|DEVAM-ARSIV\.md|mimar-posta-kutusu(-arsiv)?\.md|MEMORY\.md|"
    r"/memory/[^/]+\.md)$")

# Kapanis-sinifi Bash komutlari: commit/push + SALT OKUMA olcum komutlari.
KAPANIS_BASH = (
    re.compile(r"\bgit\b[^|;&]*\b(commit|push|status|log|diff|show|rev-parse|"
               r"ls-files|fetch)\b"),
    re.compile(r"^\s*(grep|rg|ls|cat|head|tail|wc|find|du|df|jq|sed -n|pgrep|ps)\b"),
    re.compile(r"\bkutu-arsivle\.py|defter-rotasyon\.py"),
)


def _sayi(x):
    try:
        return int(x or 0)
    except (TypeError, ValueError):
        return 0


def transkript_olc(yol):
    """(tur, baglam_jetonu, kod_write, hata) — transkriptten OLC.

    tur           = asistan mesaji sayisi (bir tur = bir asistan yaniti).
    baglam_jetonu = SON asistan mesajinin usage toplami (input+cache_read+cache_creation).
    kod_write     = kod/test dosyasina yapilan Write cagrisi sayisi.
    hata          = None ise olculdu; DOLU ise OLCULEMEDI (fail-open).
    """
    if not yol or not os.path.isfile(yol):
        return 0, 0, 0, "transcript_path yok ya da okunamiyor: %r" % (yol,)
    tur = 0
    baglam = 0
    kod_write = 0
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            for satir in f:
                satir = satir.strip()
                if not satir:
                    continue
                try:
                    kayit = json.loads(satir)
                except ValueError:
                    continue
                if kayit.get("type") != "assistant":
                    continue
                tur += 1
                mesaj = kayit.get("message") or {}
                kullanim = mesaj.get("usage") or {}
                if kullanim:
                    baglam = (_sayi(kullanim.get("input_tokens"))
                              + _sayi(kullanim.get("cache_read_input_tokens"))
                              + _sayi(kullanim.get("cache_creation_input_tokens")))
                for blok in (mesaj.get("content") or []):
                    if not isinstance(blok, dict) or blok.get("type") != "tool_use":
                        continue
                    if blok.get("name") != "Write":
                        continue
                    hedef = ((blok.get("input") or {}).get("file_path") or "")
                    if hedef.endswith(KOD_UZANTILARI) and "/scratchpad/" not in hedef:
                        kod_write += 1
    except OSError as e:
        return 0, 0, 0, "transkript okunamadi: %s" % e
    if tur == 0:
        return 0, 0, 0, "transkriptte asistan mesaji YOK (bicim degismis olabilir)"
    return tur, baglam, kod_write, None


def kapanis_sinifi_mi(arac, girdi):
    """Bu arac cagrisi oturumu KAPATMAYA yarayan sinifta mi?"""
    if arac in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        hedef = (girdi.get("file_path") or girdi.get("notebook_path") or "")
        return bool(KAPANIS_DOSYA_DESENI.search(hedef))
    if arac == "Bash":
        komut = girdi.get("command") or ""
        return any(rx.search(komut) for rx in KAPANIS_BASH)
    # Okuma/arama araclari daima serbest — olcmek kapanisin parcasidir.
    return arac in ("Read", "Grep", "Glob", "TodoWrite", "AskUserQuestion")


def deny(sebep):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": sebep,
    }}))
    sys.exit(0)


def main():
    try:
        veri = json.load(sys.stdin)
    except Exception:                                              # noqa: BLE001
        sys.exit(0)                       # kanca bozulursa isi DURDURMA

    arac = veri.get("tool_name", "")
    girdi = veri.get("tool_input", {}) or {}
    tur, baglam, kod_write, hata = transkript_olc(veri.get("transcript_path"))

    if hata:
        print("BAGLAM KOTASI: OLCULEMEDI — %s (kapi GECIRDI; bypass DEGIL, menzil "
              "daraltmasi)" % hata, file=sys.stderr)
        sys.exit(0)

    # ── MEKANIK KOL: hacim isi ucuz kata ─────────────────────────────────────────
    if kod_write >= MEKANIK_WRITE and arac == "Write":
        hedef = girdi.get("file_path") or ""
        if hedef.endswith(KOD_UZANTILARI) and "/scratchpad/" not in hedef:
            deny("BAGLAM KOTASI — MEKANIK IS: bu oturumda kod/test dosyasina %d `Write` "
                 "yapildi (tavan %d). Hacim isi mimar elinde DEGIL ucuz katta kosar: "
                 "spec yaz, `~/.claude/cron/isci.sh minimax-m3 <ev> <spec.md> tamir` ile "
                 "devret. (tur=%d · baglam=%dK)"
                 % (kod_write, MEKANIK_WRITE, tur, baglam // 1000))

    # ── RED KOLU: yalniz kapanis sinifi gecer ────────────────────────────────────
    if tur >= RED_TUR or baglam >= RED_JETON:
        if not kapanis_sinifi_mi(arac, girdi):
            deny("BAGLAM KOTASI — RED: oturum tur=%d (tavan %d) · baglam=%dK "
                 "(tavan %dK). Her tur TUM baglami yeniden faturaliyor. ONCE KAPANIS "
                 "SONRA /clear: sayili kapanisi deftere+kutuya yaz, commit+push et, "
                 "oturumu kapat. Bu esikte YALNIZ kapanis-sinifi arac gecer "
                 "(defter/kutu Write · git commit/push · okuma-olcme)."
                 % (tur, RED_TUR, baglam // 1000, RED_JETON // 1000))
        sys.exit(0)

    # ── UYARI KOLU: gecirir ama SESSIZ DEGIL ─────────────────────────────────────
    if tur >= UYARI_TUR or baglam >= UYARI_JETON:
        print("BAGLAM KOTASI — UYARI: tur=%d (uyari %d, red %d) · baglam=%dK "
              "(uyari %dK, red %dK). Kapanisi PLANLA: kalan isi bitir, deftere+kutuya "
              "sayiyla yaz, /clear."
              % (tur, UYARI_TUR, RED_TUR, baglam // 1000,
                 UYARI_JETON // 1000, RED_JETON // 1000), file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()

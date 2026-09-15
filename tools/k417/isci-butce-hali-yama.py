#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K417 — ISCI "TUR BITTI" / "GOREV BITTI" AYIRMA YAMASI (15 Eyl 2026).

Hedef dosyalar `~/.claude/cron/` altindadir (repoda KOPYASI YOKTUR); bu
yuzden yama repoda YASAR, kurulu kopyaya UYGULANIR ve olcum KURULU
KOPYADAN yapilir ([[emir-canliligi-kurulu-kopyadan-olculur]]).

--------------------------------------------------------------------------
OLCULEN VAKA (iddia degil; 15 Eyl 2026, MaCiT d27-hazirla olayindan)
--------------------------------------------------------------------------
MaCiT isci `tools/thing-hazirla.py`'yi arka planda baslatip "tamamlaninca
raporlayacagim" dedi ve `sleep 60 &` birakarak cikti. Claude ise son
asistan metninde "sonra raporlayacagim" yazip cikti; zarf
`HAL=SAGLIKLI SUBTYPE=success` basildi ve isci.sh 5 dakika icinde
`HAL=SAGLIKLI SUBTYPE=success SEBEP=zarf-okundu` ile kapandi. Sonuc:
46 id'nin 31'i eksik kaldi (5 dk sonra MaCiT baktiginda hicbiri yapilmamisti).

--------------------------------------------------------------------------
UC KOL
--------------------------------------------------------------------------
A) SUREC EKSENI — BIRINCIL  (isci.sh)
   Tur bittikten sonra (bekci_durdur'un hemen ARDINDAN) iscinin kendi
   pgid'sinde $$'dan farkli yasayan alt surec varsa is YARIM sayilir:
     - HAL_DOSYASI ustune yazilir: HAL=EKSIK SEBEP=arka-plan-sureci-bulundu
     - CLAUDE_RC=1 yapilir (eger 0 ise) -- is 0 (saglikli) ile BITMESIN
   pgid/ppid taramasi yalniz iscinin KENDI pgid'sinde; sistem/baska isler
   KONTROLE GIRMEZ (MaCiT vakasinda `sleep 60 &` tam olarak bu yuzden
   yakalanmali: kendi alt surecimiz).
   Bekci kendi KENDISI'ni durdurduktan sonra, yalnizca yasayan yabanci
   alt surecler (claude'un torunlari, sleep, vs.) HAL=EKSIK'i tetikler.

B) DIZGE KOLU — YARDIMCI  (isci-hal-cozucu.py)
   Son asistan metninde "arka planda" veya "sonra raporlayacagim" gecerse
   HAL SAGLIKLI KALIR, durum satirina `UYARI=ARKA_PLAN_BEYANI` alani
   EKLENIR (yalniz telemetri). Bu kol TEK BASINA hâl degistirmez; sadece
   sonradan bakildiginda "is yarimdi ama surec birakmamisti" dedirtir.

C) TUKETICILERIN TANIMASI  (isci-karantina-karar.py, isci-durma-notu.py)
   HAL=EKSIK yeni bir HAL'dir; motor sayacini ARTIRMAZ, kendi kovasinda
   (`__eksik__`) GORUNUR. Durma notu EKSIK'i de bilir (insan cumlesi
   uretir). Taninmayan tüketici OLCULEMEDI basar, SAGLIKLI SAYMAZ
   ([[fail-closed-tip]]).

Kullanim:
    python3 tools/k417/isci-butce-hali-yama.py --kuru     # yazmadan olc
    python3 tools/k417/isci-butce-hali-yama.py            # uygular
    python3 tools/k417/isci-butce-hali-yama.py --durum    # kurulu mu
    python3 tools/k417/isci-butce-hali-yama.py --kok DIZIN --durum
Cikis: 0 = tum kollar KURULU · 1 = eksik/dusen · 2 = arac hatasi.
"""

import argparse
import hashlib
import os
import shutil
import sys
import time

VARSAYILAN_KOK = os.path.expanduser("~/.claude/cron")
REPO_CRON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cron")

# Kurulacak YENI dosyalar: repo KANONIK kaynaktir, kurulu kopya birebir
# ayni olmalidir. (isci.sh + isci-karantina-karar.py + isci-sabitler.zsh +
# isci-motor-uc.zsh CANLI ~/.claude/cron/ altindadir ve repo disidir;
# YAMALAR onlara uygulanir ama kopyalari repo'da TUTULMAZ — k337 deseni.)
KOPYALANAN = ("isci-hal-cozucu.py", "isci-durma-notu.py")


# --------------------------------------------------------------------------
# YAMALAR — her biri (dosya, capa, yeni, isaret, kol)
# --------------------------------------------------------------------------

ISCI = "isci.sh"
COZUCU = "isci-hal-cozucu.py"
KARANTINA = "isci-karantina-karar.py"
DURMA = "isci-durma-notu.py"

YAMALAR = []


def _y(dosya, capa, yeni, isaret, kol, aciklama, gevsek_isaret=None):
    """Yama tanimlama (K337-capa-kaymasi dersi)."""
    YAMALAR.append({
        "dosya": dosya, "capa": capa, "yeni": yeni, "isaret": isaret,
        "kol": kol, "aciklama": aciklama,
        "gevsek_isaret": gevsek_isaret,
    })


def _gevsek_var(metin, gev):
    if not gev:
        return False
    if isinstance(gev, str):
        return metin.count(gev) >= 1
    return all(metin.count(g) >= 1 for g in gev)


# --- A: SUREC EKSENI — birincil -------------------------------------------
# isci.sh'de ana cagri bekci_durdur'un hemen ARDINDAN alt surec taramasi.
# capa: bekci_durdur satirinin tekrar edildigi yer (ilk tekrar blogu).
# Patch, pgid taramasini ekler ve HAL_DOSYASI ustune yazar.
_y(ISCI,
   """bekci_durdur

BITIS_SANIYE=$(date +%s)""",
   """bekci_durdur

# === K417-ARKA-PLAN-SURECI-KONTROLU BAS ===
# (15 Eyl 2026, KraL K417): MaCiT d27-hazirla olayinda isci
# "tamamlaninca raporlayacagim" yazip `sleep 60 &` birakti; zarf
# SAGLIKLI kapandi ve 31/46 id eksik kaldi. Surec kontrolu: claude
# bittikten sonra iscinin KENDI pgid'sinde $$'dan farkli yasayan
# alt surec varsa is YARIM sayilir; HAL_DOSYASI ustune
# `HAL=EKSIK SEBEP=arka-plan-sureci-bulundu` yazilir ve CLAUDE_RC
# 0 ise 1 yapilir (is 0 ile BITMESIN). pgid/ppid taramasi YALNIZ
# iscinin kendi pgid'sinde; sistem/baska isler KONTROLE GIRMEZ.
ISCI_PGID_K417=$(ps -o pgid= -p "$$" 2>/dev/null | tr -d ' ')
if [[ -n "$ISCI_PGID_K417" ]]; then
  ARKA_BULUNDU=0
  while IFS= read -r pid_k417; do
    [[ -z "$pid_k417" ]] && continue
    [[ "$pid_k417" == "$$" ]] && continue
    pid_pgid=$(ps -o pgid= -p "$pid_k417" 2>/dev/null | tr -d ' ')
    if [[ "$pid_pgid" == "$ISCI_PGID_K417" ]]; then
      pid_cmd=$(ps -o args= -p "$pid_k417" 2>/dev/null | head -c 200)
      echo "K417-ARKA_PLAN_SURECI_VAR pid=$pid_k417 pgid=$ISCI_PGID_K417 komut=$pid_cmd" >> "$LOG"
      ARKA_BULUNDU=1
      break
    fi
  done < <(ps -o pid= -A 2>/dev/null)
  if (( ARKA_BULUNDU == 1 )); then
    if [[ -n "${HAL_DOSYASI:-}" ]]; then
      printf 'HAL=EKSIK SUBTYPE= IS_ERROR=0 MALIYET_USD= TUR= OTURUM= SEBEP=arka-plan-sureci-bulundu\\n' > "$HAL_DOSYASI"
    fi
    if (( CLAUDE_RC == 0 )); then
      CLAUDE_RC=1
    fi
    echo "K417-HAL_ATANDI sebep=arka-plan-sureci-bulundu rc=$CLAUDE_RC" >> "$LOG"
  fi
  unset ARKA_BULUNDU pid_pgid pid_cmd
fi
# === K417-ARKA-PLAN-SURECI-KONTROLU SON ===

BITIS_SANIYE=$(date +%s)""",
   "=== K417-ARKA-PLAN-SURECI-KONTROLU BAS ===",
   "A", "ana cagrinin sonunda alt surec taramasi: yasayan varsa HAL=EKSIK")


# Tekrar blogunun da ayni kontrolu yapmasi gerekir. Tekrar blokundaki
# `bekci_durdur` satirinin ARDINDAN ayni isi yapan bir blok eklenir.
_y(ISCI,
   """  bekci_durdur
  BITIS_SANIYE=$(date +%s)
  SURE=$(( BITIS_SANIYE - BASLANGIC_SANIYE ))
fi""",
   """  bekci_durdur
  # === K417-ARKA-PLAN-SURECI-KONTROLU (TEKRAR) BAS ===
  # Tekrar blogu da ayni kontrolu yapar; pgid zaten ISCI_PGID_K417
  # olarak yukari tanimlandi. Tekrar blogundaki bekci_durdur'dan
  # sonra yasayan alt surec varsa HAL=EKSIK yine yazilir.
  if [[ -n "${ISCI_PGID_K417:-}" ]]; then
    ARKA_BULUNDU=0
    while IFS= read -r pid_k417; do
      [[ -z "$pid_k417" ]] && continue
      [[ "$pid_k417" == "$$" ]] && continue
      pid_pgid=$(ps -o pgid= -p "$pid_k417" 2>/dev/null | tr -d ' ')
      if [[ "$pid_pgid" == "$ISCI_PGID_K417" ]]; then
        pid_cmd=$(ps -o args= -p "$pid_k417" 2>/dev/null | head -c 200)
        echo "K417-ARKA_PLAN_SURECI_VAR pid=$pid_k417 pgid=$ISCI_PGID_K417 komut=$pid_cmd" >> "$LOG"
        ARKA_BULUNDU=1
        break
      fi
    done < <(ps -o pid= -A 2>/dev/null)
    if (( ARKA_BULUNDU == 1 )); then
      if [[ -n "${HAL_DOSYASI:-}" ]]; then
        printf 'HAL=EKSIK SUBTYPE= IS_ERROR=0 MALIYET_USD= TUR= OTURUM= SEBEP=arka-plan-sureci-bulundu\\n' > "$HAL_DOSYASI"
      fi
      if (( CLAUDE_RC == 0 )); then
        CLAUDE_RC=1
      fi
      echo "K417-HAL_ATANDI sebep=arka-plan-sureci-bulundu rc=$CLAUDE_RC" >> "$LOG"
    fi
    unset ARKA_BULUNDU pid_pgid pid_cmd
  fi
  # === K417-ARKA-PLAN-SURECI-KONTROLU (TEKRAR) SON ===
  BITIS_SANIYE=$(date +%s)
  SURE=$(( BITIS_SANIYE - BASLANGIC_SANIYE ))
fi""",
   "=== K417-ARKA-PLAN-SURECI-KONTROLU (TEKRAR) BAS ===",
   "A", "tekrar blogunda da ayni pgid taramasi")


# --- B: DIZGE KOLU — yardimci ----------------------------------------------
# isci-hal-cozucu.py'de `durum_satiri` uretecisi HAL=... satirinin sonuna
# `UYARI=ARKA_PLAN_BEYANI` ekleyebilir. Bu kol TEK BASINA hâl degistirmez.
# Yarilanma yeri: HAL_ADLARI taniminin altinda `_ARKA_PLAN_IPUCU`
# sozlugu ile "arka planda" / "sonra raporlayacagim" desenlerini tutar.
# durum_satiri ise bu sozlukten gecerse ek alan yazar.
_y(COZUCU,
   """HAL_HATALI_SONUC = "HATALI_SONUC"
HAL_OLCULEMEDI = "OLCULEMEDI"
HAL_BILINMEYEN = "BILINMEYEN_HAL\"""",
   """HAL_HATALI_SONUC = "HATALI_SONUC"
HAL_OLCULEMEDI = "OLCULEMEDI"
HAL_BILINMEYEN = "BILINMEYEN_HAL"
# 🔴 K417 (15 Eyl 2026) — HAL_EKSIK: surec ekseni ana karar; bu subtype
# isci.sh tarafindan HAL_DOSYASI ustune yazilir. Cozucu tanimazsa
# hal BILINMEYEN_HAL'e dusmez; tanimadigi icin sessizce SAGLIKLI de
# SAYMAZ (fail-closed; HAL_EKSIK'i HAL_ADLARI'na koyarak resmi tanir).
HAL_EKSIK = "EKSIK"
# K417-B: dizge kolu YARDIMCI. Son asistan metninde bu desenlerden
# biri varsa `durum_satiri` urettigi satira `UYARI=ARKA_PLAN_BEYANI`
# alani eklenir. HAL degismez (surec ekseni zaten ana karar; dizge
# yalniz telemetri/insan-geri-bildirim).
_ARKA_PLAN_IPUCU = (
    "arka planda", "arka planda baslatt", "sonra raporlayac",
    "later report", "background process", "fire-and-forget",
)""",
   "HAL_EKSIK = \"EKSIK\"",
   "B", "isci-hal-cozucu.py yeni HAL=EKSIK'i ve ipucu sozlugunu tanir")


_y(COZUCU,
   """def hal_adi(zarf):
    \"\"\"Zarftan HAL adini ve subtype'i dondurur.\"\"\"
    subtype = zarf.get(\"subtype\")
    hatali = bool(zarf.get(\"is_error\"))
    if not isinstance(subtype, str) or not subtype:
        return (HAL_BILINMEYEN, \"\")
    ad = HAL_ADLARI.get(subtype)
    if ad is None:
        return (HAL_BILINMEYEN, subtype)
    if ad == \"SAGLIKLI\" and hatali:
        return (HAL_HATALI_SONUC, subtype)
    return (ad, subtype)""",
   """def hal_adi(zarf):
    \"\"\"Zarftan HAL adini ve subtype'i dondurur.\"\"\"
    subtype = zarf.get(\"subtype\")
    hatali = bool(zarf.get(\"is_error\"))
    if not isinstance(subtype, str) or not subtype:
        return (HAL_BILINMEYEN, \"\")
    ad = HAL_ADLARI.get(subtype)
    if ad is None:
        return (HAL_BILINMEYEN, subtype)
    if ad == \"SAGLIKLI\" and hatali:
        return (HAL_HATALI_SONUC, subtype)
    return (ad, subtype)


def _arka_plan_uyari(zarf):
    \"\"\"Son asistan metninde arka-plan ipucu varsa True dondurur (K417-B).\"\"\"
    if not isinstance(zarf, dict):
        return False
    metin = zarf.get(\"result\") or \"\"
    if not isinstance(metin, str):
        return False
    kucuk = metin.lower()
    return any(ipucu in kucuk for ipucu in _ARKA_PLAN_IPUCU)""",
   "def _arka_plan_uyari(zarf):",
   "B", "asistan metninde arka-plan ipucu tarayicisi")


_y(COZUCU,
   """def durum_satiri(zarf):
    \"\"\"Tek makine-okunur satir uretir.\"\"\"
    if zarf is None:
        return (\"HAL=%s SUBTYPE= IS_ERROR= MALIYET_USD= TUR= OTURUM= \"
                \"SEBEP=zarf-yok\" % HAL_OLCULEMEDI)
    ad, subtype = hal_adi(zarf)
    maliyet = zarf.get(\"total_cost_usd\")
    tur = zarf.get(\"num_turns\")
    oturum = zarf.get(\"session_id\")
    return (\"HAL=%s SUBTYPE=%s IS_ERROR=%d MALIYET_USD=%s TUR=%s OTURUM=%s \"
            \"SEBEP=zarf-okundu\"
            % (ad, subtype or \"yok\", 1 if zarf.get(\"is_error\") else 0,
               maliyet if isinstance(maliyet, (int, float)) else \"yok\",
               tur if isinstance(tur, int) else \"yok\",
               oturum if isinstance(oturum, str) and oturum else \"yok\"))""",
   """def durum_satiri(zarf):
    \"\"\"Tek makine-okunur satir uretir.\"\"\"
    uyari = \"\"
    if zarf is None:
        return (\"HAL=%s SUBTYPE= IS_ERROR= MALIYET_USD= TUR= OTURUM= \"
                \"SEBEP=zarf-yok\" % HAL_OLCULEMEDI)
    ad, subtype = hal_adi(zarf)
    if _arka_plan_uyari(zarf):
        uyari = \"ARKA_PLAN_BEYANI\"
    maliyet = zarf.get(\"total_cost_usd\")
    tur = zarf.get(\"num_turns\")
    oturum = zarf.get(\"session_id\")
    return (\"HAL=%s SUBTYPE=%s IS_ERROR=%d MALIYET_USD=%s TUR=%s OTURUM=%s \"
            \"SEBEP=zarf-okundu UYARI=%s\"
            % (ad, subtype or \"yok\", 1 if zarf.get(\"is_error\") else 0,
               maliyet if isinstance(maliyet, (int, float)) else \"yok\",
               tur if isinstance(tur, int) else \"yok\",
               oturum if isinstance(oturum, str) and oturum else \"yok\",
               uyari))""",
   "SEBEP=zarf-okundu UYARI=%s",
   "B", "durum_satiri UYARI alanini ekler (yardimci telemetri)")


# --- C: TUKETICILERIN TANIMASI -------------------------------------------
# isci-karantina-karar.py'de BUTCE kolu gibi bir EKSIK kolu. HAL=EKSIK
# motorun ardisik sayacini ARTIRMAZ (motor arizasi degil); kendi kovasinda
# (`__eksik__`) sayilir. Eski cagrisi BIREBIR korur; --hal bosken eski
# davranis ayni durur.
_y(KARANTINA,
   "BUTCE_HALI = \"BUTCE_TAVANI\"",
   "BUTCE_HALI = \"BUTCE_TAVANI\"\nEKSIK_HALI = \"EKSIK\"\nEKSIK_KOVASI = \"__eksik__\"",
   "EKSIK_HALI = \"EKSIK\"",
   "C", "karar aracinda EKSIK_HALI ve EKSIK_KOVASI tanitilir")


_y(KARANTINA,
   "    if hal == BUTCE_HALI and rc != 0 and not karar:",
   """    if hal == EKSIK_HALI and rc != 0 and not karar:
        # K417 (15 Eyl 2026): EKSIK motor arizasi degildir; kendi kovasinda
        # sayilir, motor sayacina DOKUNMAZ (BUTCE_HALI deseniyle ayni).
        _motor_ardisik = int(ardisik_oku(karantina_dosyasi).get(motor) or 0)
        if kuru:
            _eksik_ardisik = butce_oku(karantina_dosyasi, motor) + 1
        else:
            _eksik_ardisik = butce_guncelle(karantina_dosyasi, motor, True)
        print(
            "KARANTINA_KARAR motor=%s rc=%d hal=%s imza=%s yazildi=hayir "
            "sebep=eksik-tur-yarim-kaldi ardisik=%d "
            "eksik_ardisik=%d"
            % (motor, rc, hal, sebep, _motor_ardisik, _eksik_ardisik)
        )
        return 10
    if hal == BUTCE_HALI and rc != 0 and not karar:""",
   "sebep=eksik-tur-yarim-kaldi",
   "C", "EKSIK halinde motor sayaci ARTMAZ; kendi kovasinda sayilir")


# isci-durma-notu.py'de HAL_CUMLESI sozlugune EKSIK eklenir; tanimazsa
# OLCULEMEDI mesaji basar.
_y(DURMA,
   """    \"OLCULEMEDI\": \"KOSUMUN HALI OLCULEMEDI (zarf yok)\",
    \"BILINMEYEN_HAL\": \"KOSUM TANINMAYAN BIR HALLE DONDU\",
}""",
   """    \"OLCULEMEDI\": \"KOSUMUN HALI OLCULEMEDI (zarf yok)\",
    \"BILINMEYEN_HAL\": \"KOSUM TANINMAYAN BIR HALLE DONDU\",
    \"EKSIK\": \"KOSUM YARIM KALDI (arka plan sureci bulundu, HAL=SAGLIKLI uydurulMADI)\",
}""",
   "\"EKSIK\": \"KOSUM YARIM KALDI",
   "C", "durma notu EKSIK icin insan cumlesi uretir")


# --------------------------------------------------------------------------
def sha(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(65536), b""):
            h.update(parca)
    return h.hexdigest()


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def kopya_durumu(kok):
    """Repo kanonik YENI dosyalar ile kurulu kopyayi SHA ile karsilastirir."""
    satirlar = []
    esit = 0
    for ad in KOPYALANAN:
        kaynak = os.path.join(REPO_CRON, ad)
        hedef = os.path.join(kok, ad)
        if not os.path.isfile(kaynak):
            satirlar.append("KOPYA %s KAYNAK_YOK" % ad)
            continue
        k_sha = sha(kaynak)
        if not os.path.isfile(hedef):
            satirlar.append("KOPYA %s KURULU_YOK repo_sha=%s" % (ad, k_sha[:12]))
            continue
        h_sha = sha(hedef)
        if k_sha == h_sha:
            esit += 1
            satirlar.append("KOPYA %s ESIT sha=%s bayt=%d"
                            % (ad, k_sha[:12], os.path.getsize(hedef)))
        else:
            satirlar.append("KOPYA %s AYRISTI repo=%s kurulu=%s"
                            % (ad, k_sha[:12], h_sha[:12]))
    return esit, satirlar


def yama_durumu(kok):
    kurulu, eksik, satirlar = 0, 0, []
    icerikler = {}
    for y in YAMALAR:
        yol = os.path.join(kok, y["dosya"])
        if yol not in icerikler:
            try:
                icerikler[yol] = _oku(yol)
            except OSError as e:
                icerikler[yol] = None
                satirlar.append("DOSYA_OKUNAMADI %s (%s)"
                                % (y["dosya"], type(e).__name__))
        metin = icerikler[yol]
        if metin is None:
            eksik += 1
            continue
        n_isaret = metin.count(y["isaret"])
        n_capa = metin.count(y["capa"])
        if n_isaret == 1:
            kurulu += 1
            satirlar.append("YAMA kol=%s %s KURULU (%s)"
                            % (y["kol"], y["dosya"], y["aciklama"]))
        elif n_isaret > 1:
            eksik += 1
            satirlar.append("YAMA kol=%s %s COGALMIS isaret=%d 🔴"
                            % (y["kol"], y["dosya"], n_isaret))
        elif n_capa == 1:
            eksik += 1
            satirlar.append("YAMA kol=%s %s EKSIK (capa yerinde, yama YOK)"
                            % (y["kol"], y["dosya"]))
        elif _gevsek_var(metin, y.get("gevsek_isaret")):
            kurulu += 1
            satirlar.append("YAMA kol=%s %s GEVSEK-KURULU (%s)"
                            % (y["kol"], y["dosya"], y["aciklama"]))
        else:
            eksik += 1
            satirlar.append("YAMA kol=%s %s CAPA_YOK capa_sayisi=%d 🔴"
                            % (y["kol"], y["dosya"], n_capa))
    return kurulu, eksik, satirlar


def uygula(kok, kuru):
    degisen = []
    hata = []
    # 0) Hedef kok zaten varsa icindeki dosyalari TEMIZLE — onceki
    #    kosumdan kalan K417-yama uygulanmis kopyalar yeni capalari
    #    BULAMAZ, sessiz "EKSIK" rapor edilirdi (YAMA_DURUMU'nun
    #    capa_sayisi=0 kosulu). Idempotens icin temizden basla.
    for ad in KOPYALANAN:
        hedef = os.path.join(kok, ad)
        if os.path.isfile(hedef):
            os.unlink(hedef)
    # 1) YENI dosyalar: repo -> kurulu (birebir kopya)
    for ad in KOPYALANAN:
        kaynak = os.path.join(REPO_CRON, ad)
        hedef = os.path.join(kok, ad)
        if not os.path.isfile(kaynak):
            hata.append("KAYNAK_YOK %s" % kaynak)
            continue
        varsa_esit = os.path.isfile(hedef) and sha(hedef) == sha(kaynak)
        if varsa_esit:
            continue
        if kuru:
            degisen.append("KOPYALANACAK %s" % ad)
            continue
        if os.path.isfile(hedef):
            shutil.copy2(hedef, hedef + ".yedek-k417-%d" % int(time.time()))
        shutil.copy2(kaynak, hedef)
        os.chmod(hedef, 0o755)
        degisen.append("KOPYALANDI %s sha=%s" % (ad, sha(hedef)[:12]))

    # 2) Yamalar
    dosyalar = sorted({y["dosya"] for y in YAMALAR})
    for dosya in dosyalar:
        yol = os.path.join(kok, dosya)
        try:
            metin = _oku(yol)
        except OSError as e:
            hata.append("OKUNAMADI %s (%s)" % (dosya, type(e).__name__))
            continue
        onceki = metin
        for y in YAMALAR:
            if y["dosya"] != dosya:
                continue
            if metin.count(y["isaret"]) >= 1:
                continue
            n = metin.count(y["capa"])
            if n != 1:
                if _gevsek_var(metin, y.get("gevsek_isaret")):
                    degisen.append("ATLANDI-GEVSEK kol=%s %s (%s)"
                                   % (y["kol"], dosya, y["aciklama"]))
                    continue
                hata.append("CAPA_SAYISI kol=%s %s capa=%d (1 bekleniyordu)"
                            % (y["kol"], dosya, n))
                continue
            metin = metin.replace(y["capa"], y["yeni"], 1)
            degisen.append("YAMALANDI kol=%s %s (%s)"
                           % (y["kol"], dosya, y["aciklama"]))
        if metin != onceki and not kuru:
            shutil.copy2(yol, yol + ".yedek-k417-%d" % int(time.time()))
            gecici = yol + ".k417-yeni"
            with open(gecici, "w", encoding="utf-8") as f:
                f.write(metin)
            os.chmod(gecici, os.stat(yol).st_mode & 0o777)
            os.replace(gecici, yol)
    return degisen, hata


def geri_al(kok):
    """En YENI `.yedek-k417-*` kopyasindan yamalanan dosyalari geri yukler."""
    satirlar = []
    for dosya in sorted({y["dosya"] for y in YAMALAR}):
        yol = os.path.join(kok, dosya)
        yedekler = sorted(
            a for a in os.listdir(kok)
            if a.startswith(dosya + ".yedek-k417-")
        )
        if not yedekler:
            satirlar.append("GERI_ALINAMADI %s YEDEK_YOK" % dosya)
            continue
        kaynak = os.path.join(kok, yedekler[-1])
        shutil.copy2(kaynak, yol)
        satirlar.append("GERI_ALINDI %s <- %s sha=%s"
                        % (dosya, yedekler[-1], sha(yol)[:12]))
    return satirlar


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--kok", default=VARSAYILAN_KOK)
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--durum", action="store_true")
    ap.add_argument("--geri-al", dest="geri_al", action="store_true")
    ns = ap.parse_args()

    kok = os.path.abspath(os.path.expanduser(ns.kok))
    if not os.path.isdir(kok):
        sys.stderr.write("HATA: kok dizin yok: %s\n" % kok)
        return 2

    if ns.geri_al:
        for s in geri_al(kok):
            print("  " + s)
        return 0

    if not ns.durum:
        degisen, hata = uygula(kok, ns.kuru)
        for s in degisen:
            print("  " + s)
        for s in hata:
            print("  🔴 " + s)
        if ns.kuru:
            print("KURU KOSUM (yazilmadi) degisecek=%d hata=%d"
                  % (len(degisen), len(hata)))
            return 0 if not hata else 1

    esit, kopya_satirlari = kopya_durumu(kok)
    kurulu, eksik, yama_satirlari = yama_durumu(kok)
    for s in kopya_satirlari + yama_satirlari:
        print("  " + s)
    print("DURUM kok=%s KOPYA_ESIT=%d/%d YAMA_KURULU=%d EKSIK=%d"
          % (kok, esit, len(KOPYALANAN), kurulu, eksik))
    return 0 if (eksik == 0 and esit == len(KOPYALANAN)) else 1


if __name__ == "__main__":
    sys.exit(main())
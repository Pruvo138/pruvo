#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K302 — hasat_ekle: ic["marka"] LISTE ise ayristir + fail-closed.

KOK NEDEN (MaCiT olcum 26 Agu 2026, BMW x TV dilimi):
  Eski hasat_ekle.py uyum = [{"marka": ic["marka"]}] satirinda ic["marka"] listeyse
  LISTEYI dogrudan uyum[0].marka'ya yaziyordu. arama.marka_uyumdan_turet() ise
  o alanin STRING olmasini bekliyor; uyum_marka_kanonik(liste) -> "" doner, sonuc
  u["marka"] = [] olarak SESSIZCE bosaliyordu. 61 BMW kaydi bu sekilde bozuldu,
  duzelt.py --toplu ile ELLE onarildi; Ford x TV ekleme dilimi (56 kayit) AYNI
  tuzaga dusuyordu.

COZUM: ic["marka"] turunu BICIMCE ayristir:
  - str           -> {"marka": ic["marka"]}              (eski davranis korunur)
  - liste, 1 elm  -> {"marka": ic["marka"][0]}           (eski davranis korunur)
  - liste, 2 elm  -> {"marka": ic["marka"][0], "model": ic["marka"][1]}
  - liste, 3+ elm -> {"marka": ic["marka"][0], "model": ic["marka"][1]}
                     (ilk ikisi yeterli; ekler bilerek SESSIZCE birakilir -
                      uyum model/motor/oem girisleri UYUM_ALANLARI listesinin
                      DISINDA tutulur)
  - liste, 0 elm  -> {"marka": ""}                       (fail-closed tetikler)

FAIL-CLOSED: kayit yazimi ONCESI; ic["marka"] dolu (string non-empty ya da
liste non-empty) iken turetilen_marka bos cikarsa ValueError. Bugun sessiz
gectigi icin 61 kayit fark edilmeden bozuldu.

BU DOSYA KRAL'E AITTIR: MaCiT'in olcum/hasat_ekle.py'i ile ayni mantigi TASIYAN,
PRUVO araclariyla (arama.marka_uyumdan_turet) entegre calisan tek-kaynak
fonksiyonu. MaCiT kendi orchestrator'inda BUNU kullanir (ya da refactor eder).
"""
import os
import sys

# arama.py ayni tools/ icinde; proje koku uzerinden import edilebilir olsun
_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

from tools.arama import marka_uyumdan_turet  # noqa: E402


def uyum_uret(ic_marka):
    """ic["marka"] -> (uyum_listesi, marka_listesi) ya da ValueError.

    Returns:
        (uyum, marka): uyum 1 elemanli liste, marka uretilen marka listesi.
                       ikisi de BOS degilse normal; marka BOS ise fail-closed.

    Raises:
        ValueError: ic_marka turu uyumsuz (string degil, liste degil, None) ya da
                    ic_marka non-EMPTY ama turetilen marka EMPTY (bicim bozuk).
    """
    if ic_marka is None:
        # None = "bu kayit marka tasimaz" (Tamirat/sinifsiz). Iki alan da bos doner;
        # fail-closed BURADA tetiklenmez — cunku ic_marka non-empty kosulu yok.
        return ([{"marka": ""}], [])
    if isinstance(ic_marka, str):
        uyum_oge = {"marka": ic_marka}
        uyum = [uyum_oge]
        marka = marka_uyumdan_turet({"uyum": uyum})
        _fail_closed(ic_marka, marka)
        return uyum, marka
    if isinstance(ic_marka, list):
        if len(ic_marka) == 0:
            uyum_oge = {"marka": ""}
            uyum = [uyum_oge]
            marka = marka_uyumdan_turet({"uyum": uyum})
            # FAIL-CLOSED YOK: ic_marka zaten bos (non-empty kosulu saglanmadi).
            return uyum, marka
        if len(ic_marka) == 1:
            uyum_oge = {"marka": ic_marka[0]}
            uyum = [uyum_oge]
            marka = marka_uyumdan_turet({"uyum": uyum})
            _fail_closed(ic_marka, marka)
            return uyum, marka
        # 2+ elemanli: ilki marka, ikincisi model; geri kalan bilerek SESSIZ
        uyum_oge = {"marka": ic_marka[0], "model": ic_marka[1]}
        uyum = [uyum_oge]
        marka = marka_uyumdan_turet({"uyum": uyum})
        _fail_closed(ic_marka, marka)
        return uyum, marka
    raise ValueError("ic['marka'] turu desteklenmiyor: %s" % type(ic_marka).__name__)


def _fail_closed(ic_marka, turetilen_marka):
    """ic_marka non-empty ama turetilen_marka EMPTY ise FAIL-CLOSED (ValueError).

    NEDEN: 26 Agu 2026 BMW/Ford x TV olayi — 61 kayit SESSIZCE bozuldu, hicbir
    kapı yakalamadi. Marka alani katalogda ARAMA + FILTRE icin kullanildigi icin
    bos kalmasi = urun marka filtresinde ve aramada GORUNMEZ olur. YAZARKEN hata
    vermek, SONRA duzelt.py ile gezmekten HIZLI ve UCUZ.
    """
    ic_non_empty = (
        (isinstance(ic_marka, str) and ic_marka.strip() != "") or
        (isinstance(ic_marka, list) and len(ic_marka) > 0)
    )
    if ic_non_empty and not turetilen_marka:
        raise ValueError(
            "marka turetilemedi (ic_marka=%r, uyum'dan uretilen marka bos) — "
            "fail-closed: icerigi reddet" % (ic_marka,)
        )


if __name__ == "__main__":
    # CLI: dogrudan calistirildiginda ornekleri basar
    ornekler = [
        ["BMW", "E30"],
        ["Audi"],
        ["Ford", "Focus", "Mk3"],
        "Renault",
        [],
        None,
    ]
    for ic in ornekler:
        try:
            uyum, marka = uyum_uret(ic)
            print("ic=%-30s -> uyum=%s  marka=%s" % (repr(ic), uyum, marka))
        except ValueError as e:
            print("ic=%-30s -> ValueError: %s" % (repr(ic), e))

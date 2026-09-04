#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ÇİP SÜPÜRGESİ — Okan'ın ELİYLE tetiklediği kapanışsız-çip taraması.

🔴 NEDEN VAR (ölçüldü 4 Eyl 2026): `Stop` kancası (`9927c03f`) KENAR-tetiklidir —
yalnız CANLI bir oturum dururken ateşler. Oturumu ölen çip (çökme, kill, kota,
makinenin uyuması) o kenarı HİÇ üretmez, kanca onu HİÇ görmez. Geriye kalan emniyet
"açan mimar kapatır" idi; zorlayıcısı olmayan bir davranış kuralı. Ölçülen sonuç:
`optimistic-fermi-e89dd3` (31 Ağu) ve `funny-panini-ce6bbb` (1 Eyl) günlerce açık
kaldı, hiçbir mimar kapatmadı, kanca hiçbirini kapanışa ZORLAMADI.
Bu bir SEVİYE sorusudur → [[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]].

🔴 NE YAPMAZ — KAPANIŞ UYDURMAZ. Sonucu bilinmeyen bir işe "başarıyla kapandı"
yazmak SAHTE YEŞİLDİR ve kaybolmuş işi gizler. `--terk` bile bir BAŞARI kapanışı
değil, "TERK EDİLDİ, sonucu ÖLÇÜLMEDİ" tutanağıdır ve neyi ölçmenin kapatacağını
yazar. Kayıt DOĞRU olur; kutu da rotasyona açılır.

🔴 EŞLEŞME KURALI İKİZLENMEZ: "bu çip kapandı mı" hükmü `kutu-arsivle.py`den
IMPORT edilir. İkinci bir eşleşme kuralı yazmak K360'ın ta kendisini geri getirirdi.

KULLANIM
  python3 tools/cip-supurme.py                 → RAPOR (salt okuma, hiçbir şey yazmaz)
  python3 tools/cip-supurme.py --gun 2          → yalnız 2 günden eski olanlar
  python3 tools/cip-supurme.py --terk <ad> --kuru   → terk tutanağının ÖNİZLEMESİ
  python3 tools/cip-supurme.py --terk <ad>      → tutanağı kutuya YAZ (kayıpsız)

ÇIKIŞ KODU: 0 = eşiğin üstünde açık çip YOK · 1 = VAR (adıyla basılır) · 2 = ölçülemedi.
"""
import argparse
import datetime as dt
import importlib.util
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "kutu-arsivle.py")
MEM = os.path.expanduser("~/.claude/projects/-Users-okan-dev-pruvo/memory")
KUTU = os.path.join(MEM, "mimar-posta-kutusu.md")
ARSIV = os.path.join(MEM, "mimar-posta-kutusu-arsiv.md")

# Bilinen evler. 🔴 KAPALI KÜME + ÜÇÜNCÜ HAL GÖRÜNÜR: eşleşmeyen imza sessizce bir
# kovaya DÜŞMEZ, `BILINMIYOR` olarak BASILIR ([[yeni-hal-cozucunun-varsayilan-kovasina-duser]]).
EVLER = ("KraL", "MaCiT", "ArTisT", "HocA", "TeKiN", "BaBa", "FaR")
TARIH_RE = re.compile(r"^##\s*(\d{4})-(\d{2})-(\d{2})")


def _kutu_modulu():
    spec = importlib.util.spec_from_file_location("kutu_arsivle", ARAC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _coz(K, yol):
    metin, hata = K.oku(yol)
    if hata:
        return None, None, None, hata
    satirlar = metin.splitlines()
    bas, fmh = K.frontmatter_sonu(satirlar)
    if fmh:
        return None, None, None, fmh
    return metin, satirlar, K.blok_baslari(satirlar, bas), None


def _tarih(baslik):
    m = TARIH_RE.match(baslik)
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _ev(satirlar, bas, son):
    """Blogun SAHIBI. Once imza satiri (— <Ev>), sonra baslik. Bulunamazsa BILINMIYOR."""
    for i in range(son - 1, bas - 1, -1):
        s = satirlar[i].strip()
        if s.startswith("—") or s.startswith("--"):
            for ev in EVLER:
                if ev.lower() in s.lower():
                    return ev
    baslik = satirlar[bas]
    for ev in EVLER:
        if ev.lower() in baslik.lower():
            return ev
    return "BILINMIYOR"


def tara(gun_esigi=0):
    K = _kutu_modulu()
    _m, k_sat, k_bas, hata = _coz(K, KUTU)
    if hata:
        return None, "KUTU OKUNAMADI: %s" % hata
    _m2, a_sat, a_bas, a_hata = _coz(K, ARSIV)

    kutu_kapanan = K.kapanan_cipler(k_sat, k_bas)
    # FAIL-CLOSED: arsiv okunamiyorsa "kapanmis" BILGISI EKSIKTIR; eksik bilgiyle
    # bir blogu terk ADAYI ilan etmek yanlis suclamadir -> arsiv hali AYRICA basilir.
    arsiv_kapanan = K.kapanan_cipler(a_sat, a_bas) if not a_hata else set()

    araliklar = K.blok_araliklari(k_sat, k_bas)
    acik = K.basliyorum_adlari(k_sat, k_bas)
    bugun = dt.date.today()

    satir = []
    for idx, ad in sorted(acik.items()):
        # 🔴 K360-A sonrasi cip KIMLIGI TEK AD DEGIL AD KUMESIDIR (acilis backtick'ten,
        # kapanis duz metinden cozulebiliyor). Kapanmislik kumelerin KESISIMIYLE sorulur;
        # tek ad kiyasi K360'in kendisini geri getirirdi.
        # `sorted`: kume uzerinde `tuple()` SIRASIZDIR; adlar[0] ekranda ve `--terk`
        # ciktisinda kullanildigi icin sira DETERMINISTIK olmali (yoksa ayni kutu iki
        # kosumda iki farkli ad basar ve mutant/kabul kollari kayganlasir).
        adlar = (tuple(sorted(ad))
                 if isinstance(ad, (tuple, list, set, frozenset)) else (ad,))
        if any(a in kutu_kapanan or a in arsiv_kapanan for a in adlar):
            continue
        bas, son = araliklar[idx]
        tarih = _tarih(k_sat[bas])
        yas = (bugun - tarih).days if tarih else None
        if gun_esigi and (yas is None or yas < gun_esigi):
            continue
        satir.append({
            "ad": adlar[0],
            "adlar": adlar,
            "ev": _ev(k_sat, bas, son),
            "tarih": tarih.isoformat() if tarih else "OLCULEMEDI",
            "yas": yas,
            "baslik": k_sat[bas][:96],
        })
    return {"acik": satir, "arsiv_hata": a_hata,
            "toplam_acik": len(acik), "esik": gun_esigi}, None


def rapor(veri):
    print("ÇİP SÜPÜRGESİ — kutuda kapanışı OLMAYAN `BAŞLIYORUM` blokları")
    print("kaynak: %s" % KUTU)
    if veri["arsiv_hata"]:
        print("🔴 ARŞİV OKUNAMADI (%s) — 'kapanmış' bilgisi EKSİK, liste FAZLA gösterebilir."
              % veri["arsiv_hata"])
    print()
    if not veri["acik"]:
        print("AÇIK ÇİP YOK (eşik=%d gün, taranan BAŞLIYORUM=%d)"
              % (veri["esik"], veri["toplam_acik"]))
        return 0
    print("%-26s %-9s %-12s %-11s %s" % ("ÇİP", "EV", "AÇILIŞ", "YAŞ", "DİĞER ADLARI"))
    for s in veri["acik"]:
        yas = "%d gün" % s["yas"] if s["yas"] is not None else "OLCULEMEDI"
        digerleri = ", ".join(s["adlar"][1:]) or "—"
        print("%-26s %-9s %-12s %-11s %s"
              % (s["ad"][:26], s["ev"], s["tarih"], yas, digerleri[:40]))
    print()
    ev_sayim = {}
    for s in veri["acik"]:
        ev_sayim[s["ev"]] = ev_sayim.get(s["ev"], 0) + 1
    print("EV BAŞINA: %s" % ", ".join("%s=%d" % (e, n) for e, n in sorted(ev_sayim.items())))
    print("AÇIK=%d (eşik=%d gün)" % (len(veri["acik"]), veri["esik"]))
    print()
    print("NE YAPILMALI: sahibi mimar sayılı kapanışını yazsın. Oturumu ölmüş ve sonucu")
    print("ölçülemeyen çip için tutanak:  python3 tools/cip-supurme.py --terk <ÇİP> --kuru")
    return 1


TERK_SABLONU = """## {tarih} — ⚠️ {ad} **TERK TUTANAĞI — İŞ BİTMEDİ, SONUÇ ÖLÇÜLMEDİ**

Bu bir BAŞARI kapanışı DEĞİLDİR. Çipin oturumu sayılı kapanış yazmadan düştü; süpürge
(`tools/cip-supurme.py`, Okan'ın eliyle tetiklendi) bloğu kapanışsız buldu ve tutanağa
geçirdi. **Ne yapıldığı, nereye kadar geldiği ÖLÇÜLMEMİŞTİR.**

· çip: `{ad}` · ev: **{ev}** · açılış: {acilis} · yaş: {yas}
· kapanış: kutuda YOK, arşivde YOK (eşleşme hükmü `kutu-arsivle.py`den)
· 🔴 İŞ KAYBI RİSKİ: çipin dalı/worktree'si varsa İÇERİĞİ HÂLÂ ORADA olabilir —
  silmeden ÖNCE `python3 tools/arsiv-kapisi.py <agac-yolu>` koşulur, `rc=0` görülmeden
  silinmez.

*Neyi ölçmek KAPATIR:* sahibi ev (**{ev}**) çipin dalını bulur, kapsamını `merge-base`den
ölçer, ya merge eder ya gerekçeli budar; sonucu SAYIYLA bu kutuya yazar. O kapanış
geldiğinde bu tutanak geçersizdir.

— KraL (mimar oturumu, süpürge tutanağı)

---

"""


def terk_yaz(ad, kuru):
    veri, hata = tara(0)
    if hata:
        print(hata)
        return 2
    # Eslesme AD KUMESININ HERHANGI bir uyesiyle kurulur (K360-A).
    hedef = next((s for s in veri["acik"] if ad in s["adlar"]), None)
    if hedef is None:
        print("🔴 `%s` kapanışsız açık çip listesinde YOK — tutanak YAZILMADI." % ad)
        print("   (Kapanışı zaten olabilir ya da ad birebir eşleşmiyor. Önce raporu koş.)")
        return 2

    blok = TERK_SABLONU.format(
        tarih=dt.date.today().isoformat(), ad=hedef["ad"], ev=hedef["ev"],
        acilis=hedef["tarih"],
        yas=("%d gün" % hedef["yas"]) if hedef["yas"] is not None else "OLCULEMEDI")

    if kuru:
        print("--kuru — YAZILMADI. Kutuya girecek blok:")
        print()
        print(blok.rstrip())
        return 0

    with open(KUTU, "r", encoding="utf-8") as f:
        eski = f.read()
    satirlar = eski.splitlines(keepends=True)
    kesim = 0
    if satirlar and satirlar[0].rstrip("\n") == "---":
        i = 1
        while i < len(satirlar):
            if satirlar[i].rstrip("\n") == "---":
                kesim = i + 1
                break
            i += 1
    ust, alt = "".join(satirlar[:kesim]), "".join(satirlar[kesim:])
    yeni = ust + blok + alt
    if ust not in yeni or alt not in yeni:
        print("🔴 KAYIPLI — YAZILMADI")
        return 2
    gecici = KUTU + ".supurme-tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write(yeni)
    os.replace(gecici, KUTU)
    print("YAZILDI: `%s` terk tutanağı (ev=%s). lossless=GECTI  %d -> %d satır"
          % (ad, hedef["ev"], eski.count("\n"), yeni.count("\n")))
    return 0


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--gun", type=int, default=0,
                   help="yalnız bu kadar günden eski açık çipler (varsayılan 0 = hepsi)")
    p.add_argument("--terk", metavar="CIP",
                   help="bu çip için TERK TUTANAĞI yaz (başarı kapanışı DEĞİL)")
    p.add_argument("--kuru", action="store_true", help="--terk ile: yazma, önizle")
    a = p.parse_args()

    if a.terk:
        return terk_yaz(a.terk, a.kuru)
    veri, hata = tara(a.gun)
    if hata:
        print(hata)
        return 2
    return rapor(veri)


if __name__ == "__main__":
    sys.exit(main())

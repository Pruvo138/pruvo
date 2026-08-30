#!/usr/bin/env python3
"""6 EV DOGRULAMASI — codex KALITE KAPISI (cikti dosyasi sarti) + yanlis-pozitif nobeti.

BaBa hukmu (27 Tem): "'codex exec' cikti dosyasi sarti 6 EVDE de gecerli olacak."
Bu takim o sartin HER EVDE canli kapida gercekten kosdugunu, ve kuralin o evin RUTIN
cagrilarini KAPATMADIGINI olcer. Kural metni tools/mimar-kapi-kur.py'ye gomulu
(--codex-kurali); bu betik onun KABUL KAPISIDIR.

  python3 tools/mimar-kapi-6ev-test.py            # 6 evi olcer
  python3 tools/mimar-kapi-6ev-test.py --ev KraL  # tek ev

GERCEK 'codex' CAGRILMAZ: her vaka kapi BETIGINE stdin'den GERCEK PreToolUse JSON'u
verir ve permissionDecision'a bakar (kredi yakilmaz).

UC OLCUM SINIFI:
  * CODEX  — kalite kapisi (2 kusur dahil) + MESRU cagrilar + yanlis-pozitif nobetcisi
  * ISCI   — agent_id DOLU cagrilarda kural uygulanmamali (delegasyonun temeli)
  * RUTIN  — evin gundelik cagrilari YESIL kalmali (BaBa sarti: kapi kapsam genislemesi
             alakasiz isi durdurmasin — memory/kapi-kapsam-eksen-secimi.md)

FAIL-OPEN KORLUGU: "stdout bos => allow" tek basina yeterli sayilmaz. Her evde
CODEX-6 vakasi ('codex exec "x"') DENY olmak ZORUNDA; kapi silinse/coksede o vaka
kirmizi yanar, yani takim "kapi yok" durumunu ALLOW diye yutmaz. Ayrica 'iz' kolonu
ALLOW yolunda stderr izinin var olup olmadigini raporlar (BaBa evi iz basmaz — bu
BILINEN ve raporlanan bir farktir, karar vermez).

Cikis kodu 0 = tum evlerde tum vakalar beklenen degeri verdi.
"""
import json
import os
import subprocess
import sys

KRAL_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISCI_ID = "a4482c781a922b6a1"  # canli olculmus bir alt-ajan agent_id bicimi

# (mimar, ev koku, kapi dosyasi (ev-goreli))
EVLER = (
    ("KraL", KRAL_KOK, "tools/mimar-icra-kapisi.py"),
    ("MaCiT", "/Users/okan/dev/pruvo-hasat", ".claude/mimar-icra-kapisi.py"),
    ("KaaN", "/Users/okan/dev/pruvo-jenerator", ".claude/mimar-icra-kapisi.py"),
    ("ArTisT", "/Users/okan/dev/pruvo-pazarlama", ".claude/mimar-icra-kapisi.py"),
    ("HocA", "/Users/okan/dev/pruvo-bot", ".claude/mimar-icra-kapisi.py"),
    ("BaBa", "/Users/okan/dev/pruvo-advisor", ".claude/mimar-icra-kapisi.py"),
)

# Ev-basina python ALLOWLIST cagrisi (RUTIN-8). Evlerin python politikasi FARKLI:
#   KraL  : sabit allowlist (durum.py) → ALLOW
#   4 kardes: allowlist dosyasi .claude/mimar-kapi-allow.txt KURULMAMIS → tasarim geregi
#             python arac kosumu RED (bu kuralla ILGISIZ, kurulumdan ONCE de RED'di)
#   BaBa  : yol-tabanli — ev ICINDEKI betik ALLOW
PY_CAGRI = {
    "KraL": ("python3 /Users/okan/dev/pruvo/tools/durum.py", "allow"),
    "MaCiT": ("python3 {EV}/tools/durum.py", "deny"),
    "KaaN": ("python3 {EV}/tools/durum.py", "deny"),
    "ArTisT": ("python3 {EV}/tools/durum.py", "deny"),
    "HocA": ("python3 {EV}/tools/durum.py", "deny"),
    "BaBa": ("python3 {EV}/olc.py", "allow"),
}

# (sinif, no, komut, agent_id, beklenen)  — beklenen: "allow"/"deny" ya da ev->deger dict
VAKALAR = [
    # --- CODEX: 27 TEM 2. TUR'DE KAPATILAN IKI KUSUR ---
    ("CODEX", 1, 'codex exec --output-last-message=-o "x"', None, "deny"),
    ("CODEX", 2, 'codex exec -o -v "x"', None, "deny"),
    ("CODEX", 3, 'nice -n 10 codex exec "x"', None, "deny"),
    ("CODEX", 4, 'env -u FOO codex exec "x"', None, "deny"),
    # --- CODEX: kalite kapisinin cekirdegi ---
    ("CODEX", 5, 'codex exec -o /tmp/son-mesaj.txt "x"', None, "allow"),
    ("CODEX", 6, 'codex exec "x"', None, "deny"),
    ("CODEX", 7, 'codex exec --output-last-message=/tmp/son-mesaj.txt "x"', None, "allow"),
    ("CODEX", 8, "codex --version", None, "allow"),
    ("CODEX", 9, "codex resume -o /tmp/son-mesaj.txt", None, "deny"),
    # --- CODEX: YANLIS-POZITIF NOBETCILERI (daraltma + ikinci okuma bedeli) ---
    ("CODEX", 10, 'nice -n 10 codex exec -o /tmp/son-mesaj.txt "x"', None, "allow"),
    ("CODEX", 11, "time grep -rn codex {EV}/", None, "allow"),
    ("CODEX", 12, "grep -rn codex {EV}/", None, "allow"),
    # --- ISCI: agent_id DOLU -> codex kurali UYGULANMAZ (delegasyonun temeli) ---
    ("ISCI", 20, 'codex exec "x"', ISCI_ID, "allow"),
    ("ISCI", 21, 'nice -n 10 codex exec "x"', ISCI_ID, "allow"),
    ("ISCI", 22, 'codex exec --output-last-message=-o "x"', ISCI_ID, "allow"),
    # ISCI muafiyetinin GENEL ekseni: repo-disi betik kosumu.
    # 13 Agu: ISCI kimlik ekseni 6 eve dagitildi; isci muafiyeti artik BaBa'da da
    # gecerli — eski `deny` beklentisi eksenin YOKLUGUNU olcuyordu.
    ("ISCI", 23, "python3 /private/tmp/analiz.py", ISCI_ID, "allow"),
    # BaBa negatif nobetcileri: kimliksiz mimar ve kume-disi sarmalayici izi ayni
    # repo-disi betik cagrisinda kapinin tamamen acilmadigini kanitlar.
    ("ISCI", 24, "python3 /private/tmp/analiz.py", None,
     {"BaBa": "deny", "*": "deny"}),
    ("ISCI", 25, "python3 /private/tmp/analiz.py", None,
     {"BaBa": "deny", "*": "deny"}, "Bash", {"PRUVO_ISCI_KOSUMU": "gpt-9"}),
    # --- RUTIN: BaBa sarti — alakasiz gundelik cagri YESIL kalmali ---
    ("RUTIN", 30, "git -C {EV} status", None, "allow"),
    ("RUTIN", 31, "ls", None, "allow"),
    ("RUTIN", 32, "grep -rn foo .", None, "allow"),
    ("RUTIN", 33, "jq . {EV}/.claude/settings.json", None, "allow"),
    ("RUTIN", 34, "gh run list", None, "allow"),
    ("RUTIN", 35, "echo x", None, "allow"),
    ("RUTIN", 36, "cat {EV}/.claude/settings.json", None, "allow"),
    ("RUTIN", 37, "<PY>", None, "<PY>"),
    # === 8 AGU MCP-TARAYICI KAPISI (Okan teftisi K17) — 6 EVDE davranissal olcum ===
    # 6-ELEMANLI tuple: sonuncu eleman tool_name (5-elemanli mevcut vakalar 'Bash' kalir).
    # K1'in IKI AYAGI: ana-oturum RED + isci GECER. Kapi GERCEKTEN cagrilir, cikis kodu +
    # permissionDecision iddia edilir — metin eslemesi ("dosyada gecim mi") OLCMEZ.
    # 🔴 20 AGU (Okan emri): TARAYICI EKSENI EV BAZLI ACILDI — KraL + MaCiT'te ana oturum
    # tarayiciyi surer, kalan dort evde 8 Agu reddi AYNEN durur.
    #
    # 🔴🔴 BU DOSYADAKI ASIL KANIT, 40-42 ile 60'IN AYNI IKI EVDE ZIT HUKUM TASIMASIDIR:
    #     40-42 (tarayici)      -> {"KraL": allow, "MaCiT": allow, "*": deny}
    #     60    (Claude iscisi) -> {"KraL": deny,  "MaCiT": deny,  "*": allow}
    # Iki eksen tek kumeye/tek yukleme indirgenirse bu iki satir AYNI anda yesil KALAMAZ.
    # Yani "tarayiciyi acarken Claude yasagini da sessizce actim" hatasi burada CANLI
    # olcumle kirmizi yanar (memory/ad-iki-rolde-mutanti-golgeler.md).
    ("MCP", 40, "", None, {"KraL": "allow", "MaCiT": "allow", "*": "deny"},
     "mcp__claude-in-chrome__computer"),
    ("MCP", 41, "", None, {"KraL": "allow", "MaCiT": "allow", "*": "deny"},
     "mcp__Claude_Browser__computer"),
    ("MCP", 42, "", None, {"KraL": "allow", "MaCiT": "allow", "*": "deny"},
     "mcp__Control_Chrome__open_url"),
    ("MCP", 43, "", ISCI_ID, "allow", "mcp__claude-in-chrome__computer"),
    ("MCP", 44, "", ISCI_ID, "allow", "mcp__Claude_Browser__computer"),
    ("MCP", 45, "", ISCI_ID, "allow", "mcp__Control_Chrome__open_url"),
    # YANLIS-POZITIF NOBETI (K4): kapsam DISI benzer adli araclar ana oturumda REDDEDILMEZ.
    # Tek yonlu nobetci olu nobetcidir; bu eksen olculmezse kapi sessizce tasar.
    ("MCP-FP", 46, "", None, "allow", "mcp__visualize__show_widget"),
    ("MCP-FP", 47, "", None, "allow", "mcp__Blender__get_objects_summary"),
    ("MCP-FP", 48, "", None, "allow", "mcp__ccd_session__mark_chapter"),
    ("MCP-FP", 49, "", None, "allow", "mcp__scheduled-tasks__list_scheduled_tasks"),
    ("MCP-FP", 50, "", None, "allow", "mcp__Claude_Browser_Extra__computer"),
    # === 13 AGU CLAUDE ISCI SERT BLOGU ===
    # KraL + MaCiT'te gecerli beyan bile RED; kalan dort evde eski beyan kurali korunur.
    ("AGENT", 60, "codex-muafiyet: kapi kodu — sessiz-hata", None,
     {"KraL": "deny", "MaCiT": "deny", "*": "allow"}, "Agent"),
    ("AGENT", 61, "beyansiz mimar isi", None, "deny", "Agent"),
    ("AGENT", 62, "codex-muafiyet: kapi kodu — sessiz-hata", ISCI_ID,
     "allow", "Agent"),
]


def kapiyi_kostur(kapi_yolu, kok, komut, agent_id, tool_name="Bash", ortam_ek=None):
    """Doner: (karar, iz_var). karar: allow/deny/EKSIK-KAPI/COKTU/PARSE-HATASI.

    tool_name VARSAYILAN 'Bash' (mevcut TUM vakalar aynen kosar — regresyon 0). MCP
    araclarinda karar YALNIZ tool_name'den cikar; arac-ozel girdi semasi TAKLIT EDILMEZ,
    tool_input BOS birakilir (8 Agu MCP-TARAYICI kapisi)."""
    if not os.path.exists(kapi_yolu):
        return "EKSIK-KAPI", False
    payload = {
        "session_id": "6ev-test",
        "cwd": kok,
        "permission_mode": "bypassPermissions",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": ({} if tool_name.startswith("mcp__") else
                       ({"prompt": komut} if tool_name in ("Agent", "Task") else
                        {"command": komut})),
    }
    if agent_id is not None:
        payload["agent_id"] = agent_id
    ortam = dict(os.environ)
    ortam["CLAUDE_PROJECT_DIR"] = kok
    # Test gercek sarmalayici ISCI kosumunun icinde calisabilir. Buradaki vakalar kendi
    # agent_id eksenini simule eder; dis PRUVO_ISCI_KOSUMU izi ic fiksturlere sizarsa
    # MIMAR deny vakalari yalanci allow olur.
    ortam.pop("PRUVO_ISCI_KOSUMU", None)
    ortam.pop("PRUVO_CLAUDE_ISCI_IZNI", None)
    if ortam_ek:
        ortam.update(ortam_ek)
    sonuc = subprocess.run([sys.executable, kapi_yolu], input=json.dumps(payload),
                           capture_output=True, text=True, env=ortam)
    iz = "MIMAR-KAPISI allow" in (sonuc.stderr or "")
    if sonuc.returncode != 0:
        return "COKTU", iz
    cikti = (sonuc.stdout or "").strip()
    if not cikti:
        return "allow", iz
    try:
        veri = json.loads(cikti)
    except Exception:
        return "PARSE-HATASI", iz
    return ((veri.get("hookSpecificOutput") or {}).get("permissionDecision") or "allow"), iz


def beklenen_coz(beklenen, ev):
    if isinstance(beklenen, dict):
        return beklenen.get(ev, beklenen.get("*"))
    return beklenen


def ev_kostur(ad, kok, goreli):
    kapi = os.path.join(kok, goreli)
    print("")
    print("=" * 88)
    print("EV {:<7} KOK {:<32} KAPI {}".format(ad, kok, goreli))
    print("=" * 88)
    if not os.path.isdir(kok):
        print("  EV YOK — atlanmadi, KIRMIZI sayilir (dogrulanamayan ev = kurulmamis ev)")
        return [(ad, 0, "ev-yok", "EV YOK")]
    print("{:<6} {:<4} {:<8} {:<8} {:<4} {:<6} {}".format(
        "Sinif", "No", "Beklenen", "Olculen", "Iz", "Sonuc", "Komut"))
    print("-" * 88)
    basarisiz = []
    for vaka in VAKALAR:
        # 5-elemanli = Bash vakasi (mevcut); 6-elemanli = tool_name tasiyan vaka (MCP).
        sinif, no, komut, agent_id, beklenen = vaka[:5]
        tool_name = vaka[5] if len(vaka) > 5 else "Bash"
        ortam_ek = vaka[6] if len(vaka) > 6 else None
        if komut == "<PY>":
            komut, beklenen = PY_CAGRI[ad]
        komut = komut.replace("{EV}", kok)
        bek = beklenen_coz(beklenen, ad)
        olculen, iz = kapiyi_kostur(kapi, kok, komut, agent_id, tool_name, ortam_ek)
        gecti = (olculen == bek)
        if not gecti:
            basarisiz.append((ad, no, bek, olculen))
        print("{:<6} {:<4} {:<8} {:<8} {:<4} {:<6} {}".format(
            sinif, no, bek, olculen, "var" if iz else "yok",
            "OK" if gecti else "KIRMIZI", (tool_name if len(vaka) > 5 else komut)[:34]))
    return basarisiz


def main():
    argv = sys.argv[1:]
    secilen = argv[argv.index("--ev") + 1] if "--ev" in argv else None
    evler = [e for e in EVLER if (secilen is None or e[0] == secilen)]

    print("6 EV DOGRULAMASI — codex kalite kapisi (gercek codex CAGRILMAZ)")
    print("VAKA/EV: {} | EV SAYISI: {}".format(len(VAKALAR), len(evler)))

    basarisiz = []
    for ad, kok, goreli in evler:
        basarisiz += ev_kostur(ad, kok, goreli)

    print("")
    print("=" * 88)
    toplam = len(VAKALAR) * len(evler)
    if basarisiz:
        print("SONUC: {}/{} vaka GECTI — KIRMIZI:".format(toplam - len(basarisiz), toplam))
        for ad, no, bek, olculen in basarisiz:
            print("  {:<7} vaka {:<4} beklenen={:<6} olculen={}".format(ad, no, bek, olculen))
        sys.exit(1)
    print("SONUC: {}/{} vaka GECTI ({} ev x {} vaka).".format(
        toplam, toplam, len(evler), len(VAKALAR)))
    sys.exit(0)


main()

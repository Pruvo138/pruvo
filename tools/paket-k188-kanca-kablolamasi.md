# K188 — KUTU EŞİK KAPISI KANCA KABLOLAMASI (tek ekran, tek tık)

**DURUM: kapı `main`'de (`4ebefad1`) ama CANLI DEĞİL.** `tools/kutu-esik-kapisi.py`
hiçbir `PreToolUse` kancasına bağlı olmadığı için posta kutusuna yazma yolunda
**hiç koşmuyor** — bu evde ölçülmüş `[[kablo-da-kosuyor-demek-degil]]` sınıfı.

Kurulum **MİMAR/OKAN kapısıdır**; chip kurmadı, tek-tıklık hâle getirdi.

---

## 1. NEDEN `kanca-kur.py` DEĞİL (ölçüldü)

`tools/kanca-kur.py` **yalnız git kancalarını** kurar (`core.hooksPath` →
`tools/kancalar/`: `pre-commit`, `pre-push`, `commit-msg`, `post-*`).
`PreToolUse` bir **git kancası değil, Claude Code oturum kancasıdır**; yeri
`.claude/settings.json`. İki mekanizma ayrı — `kanca-kur.py`'ye eklenecek bir şey yok.

```
git check-ignore -v .claude/settings.json
.gitignore:5:.claude/	.claude/settings.json
```

**`.claude/` tamamen gitignore'da → bu değişiklik COMMIT EDİLEMEZ.** Her makinede
elle yapılır. (CLAUDE.md'deki "`.claude/settings.json` kablolaması commit EDİLMEZ"
kuralıyla birebir uyumlu.)

---

## 2. YAPILACAK TEK DEĞİŞİKLİK

Dosya: `/Users/okan/dev/pruvo/.claude/settings.json`
Yer: `hooks.PreToolUse` içindeki **mevcut** `"matcher": "Edit|Write|MultiEdit"` bloğu.

**ÖNCE (şu an):**
```json
{
  "matcher": "Edit|Write|MultiEdit",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"${CLAUDE_PROJECT_DIR:-.}/tools/mimar-kod-kilidi.py\""
    }
  ]
}
```

**SONRA (kurulunca):**
```json
{
  "matcher": "Edit|Write|MultiEdit|NotebookEdit",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"${CLAUDE_PROJECT_DIR:-.}/tools/mimar-kod-kilidi.py\""
    },
    {
      "type": "command",
      "command": "python3 \"${CLAUDE_PROJECT_DIR:-.}/tools/kutu-esik-kapisi.py\"",
      "timeout": 90,
      "statusMessage": "kutu esik kapisi"
    }
  ]
}
```

**Tam olarak iki şey değişir:**
1. `matcher`'a `|NotebookEdit` eklenir — kapının `IZINLI_ARACLAR` kümesi
   `['Edit','MultiEdit','NotebookEdit','Write']`; matcher'da `NotebookEdit`
   olmazsa o kol hiç tetiklenmez (ölçüldü, kapı kaynağından okundu).
2. `hooks` dizisine kapı **ikinci sırada** eklenir (kod kilidinden sonra).
   `timeout: 90` → rotasyon alt süreci için (kapının kendi iç zaman aşımı 60 sn).

**DEĞİŞMEYEN:** başka hiçbir matcher, `Bash` kolu, `PermissionRequest`,
`permissions`, `core.hooksPath`, hiçbir repo dosyası. Kapı **argümansız** çağrılır;
hedef kutuyu `KUTU_VARSAYILAN_YOLU`'ndan kendisi bulur.

---

## 3. ÖLÇÜLEN KANIT (kurulum ÖNCESİ, simülasyonla)

Simülasyon kapıyı **üretimdeki çağrı şekliyle** çağırır: `argv BOŞ`, stdin'de
`PreToolUse` JSON; yalnız hedef kutu fikstüre yönlendirilir
(`PRUVO_KUTU_ESIK_KUTU` — kapının kendi test kancası).

```
KOL A — EŞİK ALTI            rc=0  stdout='ESIK ALTI satir=84 tavan=300'        kutu degisti=HAYIR
KOL B — EŞİK ÜSTÜ, iner      rc=0  stdout='ROTASYON TETIKLENDI once=540 sonra=236 tavan=300'
                                   arsiv +6685 bayt
KOL C — rotasyon inemez      rc=2  stderr='...fail-closed... kutu 329 satir, tavan 300 ...REDDEDILDI'
                                   kutu degisti=HAYIR
YALITIM — başka dosya        rc=0  stdout=''  stderr=''  (kutu 540>300 OLDUĞU HALDE karışmadı)
GERCEK KUTU BAYT DEGISMEDI=EVET  bayt_once=22984 bayt_sonra=22984
SIMULASYON: 5/5
```

Kapının kendi öz-testi (bağımsız): `KENDINI-TEST: 11/11`, `V10` = hedef dışı
dosyada eşik kaynağı **hiç yüklenmiyor**, `GERCEK_KUTU_BAYT_DEGISMEDI=EVET`.

`rc=2` = Claude Code `PreToolUse` sözleşmesinde **BLOK**; stderr Claude'a geri verilir.
`rc=0` = izin. Kapı bu sözleşmeye uyuyor.

---

## 4. KURULUMDAN SONRA CANLI DOĞRULAMA (🔴 asıl kabul)

Kuru koşum "kablo doğru" der, "koşuyor" DEMEZ. Kurduktan sonra:

```bash
python3 /Users/okan/dev/pruvo/tools/kutu-esik-kapisi.py --kendini-test
```

Sonra **gerçek bir yazma** ile üç kolu görün — posta kutusuna Write/Edit yapıldığında:
* kutu ≤300 satır → kapı sessiz, yazma geçer
* kutu >300 satır → `ROTASYON TETIKLENDI once=… sonra=…` görünür, yazma geçer
* rotasyon inemezse → yazma **reddedilir**, `fail-closed` mesajı düşer

🔴 Bu üçüncü ayak **ancak kanca kurulduktan sonra** ölçülebilir; chip kurmadığı
için canlı tetikleme kanıtı bu pakette **YOK** — kurulumdan sonra alınacak.

---

## 5. GERİ ALMA

`.claude/settings.json`'da eklenen ikinci `hooks` girdisini sil ve `matcher`'ı
`"Edit|Write|MultiEdit"`'e döndür. Repo tarafında geri alınacak bir şey yok
(kapı dosyası zaten `main`'de ve kablolanmadan zararsız).

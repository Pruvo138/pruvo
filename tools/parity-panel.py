#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marka x platform DURUM PANELI -> yerel self-contained HTML (dis hosting YOK).
🔴 hic aranmamis (yapilacak) · 🟡 az kalmis (markanin en dolu platformunun <1/2'si = dengesiz) ·
⚪ arandi ama urun yok · 🟢 yeterli. Arama + 'sadece yapilacaklar' + siralama. Yenile: scripti tekrar kos."""
import json
import os
from datetime import datetime

DEFTER = "/Users/okan/dev/pruvo/.marka-kapsama.json"
OUT = "/Users/okan/Desktop/pruvo-marka-durum.html"
PLATS = ["Printables", "Thingiverse", "MakerWorld", "Cults3D", "MyMiniFactory", "********"]
KISA = ["Printables", "Thingiverse", "MakerWorld", "Cults3D", "MMF", "********"]
AZ_ORAN = 0.5   # markanin en dolu platformunun bu oraninin altindaysa "az kalmis" (sari)
AZ_MIN = 10     # en dolu platform bu sayidan azsa orantiya bakma (kucuk markada gurultu)

LAST_SUMMARY = {"toplam_marka": 0, "yapilacak_marka": 0, "kirmizi_hucre": 0, "sari_hucre": 0}


def render_html():
    d = json.load(open(DEFTER, encoding="utf-8")) if os.path.exists(DEFTER) else {}

    def hucre(m, p):
        k = d.get(m, {}).get(p)
        if not k:
            return None
        if k.get("eklenen", 0) > 0:
            return k["eklenen"]
        if k.get("taranan", 0) > 0:
            return 0
        return None

    def toplam(m):
        return sum(v for p in PLATS for v in [hucre(m, p)] if v)

    def _durum_hucreler(m):
        """(kirmizi_platformlar, sari_platformlar) — kirmizi=hic aranmadi, sari=az kalmis (orantili)."""
        vals = {p: hucre(m, p) for p in PLATS}
        tot = sum(v for v in vals.values() if v)
        en = max([v for v in vals.values() if v] or [0])
        kirmizi = [p for p in PLATS if vals[p] is None] if tot >= 3 else []
        sari = []
        if en >= AZ_MIN:
            sari = [p for p in PLATS if vals[p] and vals[p] < en * AZ_ORAN]
        return kirmizi, sari

    def durum(m):
        kirmizi, sari = _durum_hucreler(m)
        notlar = []
        if kirmizi:
            notlar.append("hiç aranmadı: " + ", ".join(KISA[PLATS.index(p)] for p in kirmizi))
        if sari:
            notlar.append("az kalmış: " + ", ".join(KISA[PLATS.index(p)] for p in sari))
        return " · ".join(notlar)

    satirlar = []
    for m in sorted(d.keys(), key=lambda m: -toplam(m)):
        cells = [hucre(m, p) for p in PLATS]
        tot = toplam(m)
        kirmizi, sari = _durum_hucreler(m)
        satirlar.append({"m": m, "cells": cells, "t": tot, "durum": durum(m),
                         "kirmizi": len(kirmizi), "sari": len(sari),
                         "yapilacak": (len(kirmizi) + len(sari)) > 0})

    toplam_marka = len(satirlar)
    yapilacak_marka = sum(1 for s in satirlar if s["yapilacak"])
    kirmizi_hucre = sum(s["kirmizi"] for s in satirlar)
    sari_hucre = sum(s["sari"] for s in satirlar)
    LAST_SUMMARY.update({"toplam_marka": toplam_marka, "yapilacak_marka": yapilacak_marka,
                         "kirmizi_hucre": kirmizi_hucre, "sari_hucre": sari_hucre})
    ts = datetime.now().strftime("%d.%m.%Y %H:%M")

    DATA = json.dumps({"rows": satirlar, "plats": KISA, "azOran": AZ_ORAN, "azMin": AZ_MIN}, ensure_ascii=False)

    HTML = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRUVO — Marka Durum Paneli</title>
<style>
:root{--navy:#12294d;--kirmizi:#e23b3b;--sari:#e6a417;--yesil:#1f9d55;--metin:#1c2431}
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,Segoe UI,Roboto,Arial,sans-serif;color:var(--metin);background:#f4f6f9}
header{background:var(--navy);color:#fff;padding:16px 22px}
header h1{margin:0;font-size:19px;letter-spacing:.5px}
header .ts{opacity:.8;font-size:12px;margin-top:3px}
.tiles{display:flex;gap:12px;padding:14px 22px;flex-wrap:wrap}
.tile{background:#fff;border:1px solid #e3e7ee;border-radius:10px;padding:10px 16px;min-width:110px}
.tile b{display:block;font-size:22px}
.tile.k b{color:var(--kirmizi)} .tile.s b{color:var(--sari)} .tile.y b{color:var(--yesil)}
.bar{display:flex;gap:12px;align-items:center;padding:0 22px 12px;flex-wrap:wrap}
.bar input[type=search]{padding:8px 12px;border:1px solid #cdd4de;border-radius:8px;font-size:14px;min-width:220px}
.bar label{display:flex;gap:6px;align-items:center;cursor:pointer;user-select:none}
.legend{margin-left:auto;display:flex;gap:14px;font-size:12px;align-items:center;flex-wrap:wrap}
.dot{width:12px;height:12px;border-radius:3px;display:inline-block;margin-right:5px;vertical-align:-1px}
.wrap{padding:0 22px 40px;overflow-x:auto}
table{border-collapse:collapse;width:100%;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06)}
th,td{padding:8px 10px;text-align:center;border-bottom:1px solid #eef1f5;white-space:nowrap}
th{background:#f0f3f8;position:sticky;top:0;cursor:pointer;font-size:12px;color:#48566b}
th:hover{background:#e6ebf3}
td.m{text-align:left;font-weight:600;position:sticky;left:0;background:#fff}
td.d{text-align:left;color:#6b7789;font-size:12px;white-space:normal;min-width:230px}
td.t{font-weight:700}
.c{font-weight:600;border-radius:5px}
.c.red{background:#fde3e3;color:#a51f1f}
.c.yellow{background:#fdf0d0;color:#8a6410}
.c.green{background:#e2f4ea;color:#137a41}
.c.gray{background:#eef0f3;color:#9aa4b2}
tr:hover td:not(.c){background:#fafbfd}
</style></head><body>
<header><h1>PRUVO — Marka × Platform Durum Paneli</h1>
<div class="ts">son güncelleme: __TS__ · 🔴 hiç aranmadı · 🟡 az kalmış (liderin yarısından az) · 🟢 yeterli · ⚪ arandı-boş</div></header>
<div class="tiles">
<div class="tile"><b id="tm"></b>toplam marka</div>
<div class="tile k"><b id="ty"></b>yapılacak marka</div>
<div class="tile k"><b id="tk"></b>🔴 hiç aranmadı (hücre)</div>
<div class="tile s"><b id="ts2"></b>🟡 az kalmış (hücre)</div>
</div>
<div class="bar">
<input type="search" id="q" placeholder="marka ara…">
<label><input type="checkbox" id="onlytodo"> sadece yapılacaklar</label>
<span class="legend"><span><span class="dot" style="background:#e23b3b"></span>hiç aranmamış</span>
<span><span class="dot" style="background:#e6a417"></span>az kalmış</span>
<span><span class="dot" style="background:#1f9d55"></span>yeterli</span>
<span><span class="dot" style="background:#c3cad4"></span>arandı, yok</span></span>
</div>
<div class="wrap"><table id="t"><thead></thead><tbody></tbody></table></div>
<script>
const D=__DATA__;
const plats=D.plats;
let sortKey='t',sortDir=-1;
const thead=document.querySelector('#t thead'),tbody=document.querySelector('#t tbody');
function head(){let h='<tr><th data-k="m">Marka</th>';plats.forEach((p,i)=>h+='<th data-k="p'+i+'">'+p+'</th>');
 h+='<th data-k="t">Top</th><th data-k="todo">Yapılacak</th><th data-k="d" style="text-align:left">Durum</th></tr>';thead.innerHTML=h;
 thead.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=(k==='m')?1:-1;}render();});}
function rowMax(r){let mx=0;r.cells.forEach(v=>{if(v>mx)mx=v;});return mx;}
function val(r,k){if(k==='m')return r.m;if(k==='t')return r.t;if(k==='todo')return r.kirmizi+r.sari;if(k==='d')return r.durum;
 if(k[0]==='p'){const v=r.cells[+k.slice(1)];return v==null?-1:v;}return 0;}
function cellHtml(v,mx){
 if(v==null)return '<td class="c red">·</td>';
 if(v===0)return '<td class="c gray">0</td>';
 const az=(mx>=D.azMin && v<mx*D.azOran);
 return '<td class="c '+(az?'yellow':'green')+'">'+v+'</td>';}
function render(){
 const q=document.getElementById('q').value.trim().toLowerCase();
 const ot=document.getElementById('onlytodo').checked;
 let rows=D.rows.filter(r=>(!q||r.m.toLowerCase().includes(q))&&(!ot||r.yapilacak));
 rows.sort((a,b)=>{const x=val(a,sortKey),y=val(b,sortKey);if(x<y)return -sortDir;if(x>y)return sortDir;return a.m.localeCompare(b.m);});
 let h='';rows.forEach(r=>{const mx=rowMax(r);h+='<tr><td class="m">'+r.m+'</td>';r.cells.forEach(v=>h+=cellHtml(v,mx));
  const yap=r.kirmizi+r.sari;
  h+='<td class="t">'+r.t+'</td><td class="c '+(yap?(r.kirmizi?'red':'yellow'):'green')+'">'+(yap||'✓')+'</td><td class="d">'+(r.durum||'—')+'</td></tr>';});
 tbody.innerHTML=h||'<tr><td colspan="10" style="padding:20px;color:#9aa4b2">eşleşme yok</td></tr>';
 document.getElementById('tm').textContent=D.rows.length;
 document.getElementById('ty').textContent=D.rows.filter(r=>r.yapilacak).length;
 document.getElementById('tk').textContent=D.rows.reduce((s,r)=>s+r.kirmizi,0);
 document.getElementById('ts2').textContent=D.rows.reduce((s,r)=>s+r.sari,0);
}
head();document.getElementById('q').oninput=render;document.getElementById('onlytodo').onchange=render;render();
</script></body></html>"""

    return HTML.replace("__DATA__", DATA).replace("__TS__", ts)


if __name__ == "__main__":
    HTML = render_html()
    yazilan = OUT
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(HTML)
    except PermissionError:
        yazilan = "/private/tmp/pruvo-marka-durum.html"
        with open(yazilan, "w", encoding="utf-8") as f:
            f.write(HTML)
    print("YAZILDI: %s" % yazilan)
    print("toplam %d marka | yapilacak %d | kirmizi hucre %d | sari hucre %d"
          % (LAST_SUMMARY["toplam_marka"], LAST_SUMMARY["yapilacak_marka"],
             LAST_SUMMARY["kirmizi_hucre"], LAST_SUMMARY["sari_hucre"]))

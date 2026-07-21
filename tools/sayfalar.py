# -*- coding: utf-8 -*-
"""
PRUVO statik içerik/yasal sayfaları + ödeme logoları.
build.py bu modülü import eder ve her sayfayı /<slug>/index.html olarak üretir.

NOT: Yasal metinler standart e-ticaret şablonudur; satıcı bilgileri gerçek
mükellefiyete göre doldurulmuştur. Yayına almadan mali müşavir/avukata
kontrol ettirmek önerilir.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import filament_ortak

# ------------------------------------------------------------------ satıcı bilgileri
SELLER = {
    "unvan": "Okan Gemalmaz",
    "tur": "Şahıs firması",
    "adres": "Akarca Mah. Adnan Menderes (BBT) Blv. No:303 Daire No:203, Fethiye / Muğla",
    "vd": "Fethiye Vergi Dairesi",
    "vkn": "3910052435",
    "tel": "+90 532 595 4005",
    "eposta": "info@pruvo3d.com",
    "kargo": "Yurtiçi Kargo",
    "teslim": "ölçü onayından sonra 3-5 iş günü",
    "site": "https://pruvo3d.com",
}

# ------------------------------------------------------------------ kişisel veri koruması
# Satıcının kişisel bilgileri (ad, adres, vergi no, telefon, e-posta) HTML kaynağına
# düz metin yazılmaz: değer 2-3 karakterlik parçalara bölünüp data-özniteliklerine
# KARIŞIK SIRADA konur. Görünürlük iki yoldan sağlanır (yasal zorunluluk — müşteri
# her koşulda okuyabilmeli):
#   1) JS açık: sayfadaki küçük betik (PV_SCRIPT_HTML) parçaları doğru sırada
#      birleştirip gerçek metin olarak basar, tel:/mailto:/harita linklerini kurar.
#   2) JS kapalı: CSS `content: attr(data-a) attr(data-b) ...` aynı parçaları doğru
#      sırada ::after içinde gösterir (saf CSS, betik gerekmez). Pseudo-element metni
#      zaten seçilip kopyalanamaz. (Karakter tersleme BİLEREK yok: CSS attr() ters
#      çeviremez; JS'siz görünürlük parçalama+sıra karıştırmayla korunur.)
# Ek katmanlar: .pv-blok üzerinde user-select:none + contextmenu engeli (sadece bu
# bloklarda; sayfanın kalanında sağ tık normal).
_PV_ADLAR = "abcdefghijkl"


def _pv_esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _pv_span(deger):
    # tek span en fazla 12 parça taşır (ilk parça 2, kalanlar 3 karakter = 35 krk.)
    parcalar = []
    i = 0
    while i < len(deger):
        boy = 2 if i == 0 else 3
        parcalar.append(deger[i:i + boy])
        i += boy
    # kaynak sırası karıştırılır: önce tek indisler, sonra çiftler → ardışık iki
    # parça kaynakta yan yana gelmez, ham HTML grep'i/regex hasadı tutmaz.
    sira = list(range(1, len(parcalar), 2)) + list(range(0, len(parcalar), 2))
    attrs = " ".join('data-%s="%s"' % (_PV_ADLAR[j], _pv_esc(parcalar[j]))
                     for j in sira)
    return '<span class="pv pv-blok" %s></span>' % attrs


def pv_html(deger):
    """Kişisel veri değerini kaynakta düz metin bırakmayan korumalı span(lar)."""
    maks = 2 + 3 * (len(_PV_ADLAR) - 1)  # 35 karakter/span
    return "".join(_pv_span(deger[i:i + maks])
                   for i in range(0, len(deger), maks))


# İçerik sayfalarının CSS'ine eklenir (CONTENT_CSS'in sonunda). Statik sayfalar
# (iletisim/gizlilik) aynı kuralları kendi <style> bloklarında taşır.
PV_CSS = """
  .pv::after{content:attr(data-a) attr(data-b) attr(data-c) attr(data-d) attr(data-e) attr(data-f) attr(data-g) attr(data-h) attr(data-i) attr(data-j) attr(data-k) attr(data-l)}
  .pv.pv-tamam::after{content:none}
  .pv-blok{-webkit-user-select:none;-moz-user-select:none;user-select:none}
"""

# İçerik sayfalarının sonuna basılan betik (saf JS, harici kütüphane YOK).
# Statik sayfalarda (iletisim/gizlilik) birebir aynısı gömülü durur.
PV_SCRIPT_HTML = """<script>
// Kişisel veri koruması: parçalanmış data-özniteliklerini birleştirip gösterir,
// tel/e-posta/harita linklerini kurar, korumalı bloklarda sağ tıkı kapatır.
(function(){
  var K="abcdefghijkl";
  var sp=document.querySelectorAll(".pv");
  for(var i=0;i<sp.length;i++){
    var v="";
    for(var j=0;j<K.length;j++){ v+=sp[i].getAttribute("data-"+K[j])||""; }
    sp[i].textContent=v;
    sp[i].className+=" pv-tamam";
  }
  var ln=document.querySelectorAll("[data-pv-link]");
  for(var m=0;m<ln.length;m++){
    var a=ln[m], ic=a.querySelectorAll(".pv"), t=a.getAttribute("data-pv-link"), d="";
    for(var n=0;n<ic.length;n++){ d+=ic[n].textContent; }
    if(t==="tel"){ a.href="tel:"+d.replace(/[^+0-9]/g,""); }
    else if(t==="eposta"){ a.href="mailto:"+d; }
    else if(t==="harita"){ a.href="https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(d); }
  }
  var bl=document.querySelectorAll(".pv-blok");
  for(var b=0;b<bl.length;b++){
    bl[b].addEventListener("contextmenu",function(e){e.preventDefault();});
  }
})();
</script>"""

# ------------------------------------------------------------------ ödeme logoları (footer)
# Güvenli, her zaman render olan inline SVG rozetler. iyzico resmi "logo band"
# varsa panelden alıp değiştirilebilir.
PAY_BAND_HTML = """<div class="pay-band">
  <span class="pay-label">Güvenli Ödeme</span>
  <span class="pay-logos">
    <span class="pay-pill pay-iyzico">iyzico<b>&nbsp;ile Öde</b></span>
    <span class="pay-pill"><svg viewBox="0 0 48 16" width="46" height="15" role="img" aria-label="Visa"><text x="24" y="13" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="14" font-style="italic" font-weight="700" fill="#1a1f71">VISA</text></svg></span>
    <span class="pay-pill"><svg viewBox="0 0 40 24" width="38" height="23" role="img" aria-label="Mastercard"><circle cx="15" cy="12" r="9" fill="#EB001B"/><circle cx="25" cy="12" r="9" fill="#F79E1B"/><path d="M20 5.2a9 9 0 0 0 0 13.6 9 9 0 0 0 0-13.6z" fill="#FF5F00"/></svg></span>
  </span>
</div>"""

# footer alt navigasyon (yasal + kurumsal linkler)
FOOT_NAV_HTML = (
    '<div class="foot-nav">'
    '<a href="/hakkimizda/">Hakkımızda</a> &middot; '
    '<a href="/iletisim/">İletişim</a> &middot; '
    '<a href="/sss/">S.S.S.</a> &middot; '
    '<a href="/malzeme-rehberi/">Malzeme Rehberi</a> &middot; '
    '<a href="/gizlilik/">Gizlilik Politikası</a> &middot; '
    '<a href="/teslimat-iade/">Teslimat ve İade</a> &middot; '
    '<a href="/mesafeli-satis/">Mesafeli Satış Sözleşmesi</a>'
    '</div>'
)

# ------------------------------------------------------------------ içerik sayfaları için ek CSS
CONTENT_CSS = """
  .content{max-width:820px;margin:0 auto;padding:34px 20px 56px}
  .content h1{font-size:26px;color:var(--navy);margin:0 0 6px}
  .content .lead{color:var(--gray-text);font-size:14px;margin-bottom:26px}
  .content h2{font-size:18px;color:var(--navy);margin:28px 0 10px}
  .content p,.content li{font-size:15px;color:#39434f;line-height:1.75}
  .content ul,.content ol{padding-left:20px;margin:8px 0}
  .content a{color:var(--navy-2)}
  .content .info-table{width:100%;border-collapse:collapse;margin:10px 0 4px;font-size:14.5px}
  .content .info-table td{padding:8px 10px;border:1px solid var(--gray-line);vertical-align:top}
  .content .info-table td:first-child{background:var(--gray-card);font-weight:600;color:var(--navy);width:38%}
  .content .info-table th{padding:8px 10px;border:1px solid var(--gray-line);background:var(--navy);
    color:#fff;text-align:left;font-size:13.5px}
  .content .karsilastirma td:first-child{width:auto;white-space:nowrap}
  .content .upd{margin-top:30px;font-size:12.5px;color:var(--gray-text)}
  .pay-band{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:10px;margin-top:14px}
  .pay-label{font-size:12px;color:#8996ad;letter-spacing:.4px}
  .pay-logos{display:inline-flex;align-items:center;gap:8px;flex-wrap:wrap}
  .pay-pill{display:inline-flex;align-items:center;background:#fff;border-radius:6px;
    padding:5px 9px;height:26px;box-shadow:0 1px 3px rgba(0,0,0,.18)}
  .pay-iyzico{font-weight:800;font-size:13px;color:#1e64ff;letter-spacing:-.3px}
  .pay-iyzico b{color:#12294d;font-weight:700}
""" + PV_CSS


def _seller_table():
    # Kişisel değerler düz metin basılmaz — pv_html (yukarıdaki koruma katmanı).
    s = SELLER
    return (
        '<table class="info-table pv-blok"><tbody>'
        '<tr><td>Satıcı</td><td>%s (%s)</td></tr>'
        '<tr><td>Adres</td><td>%s</td></tr>'
        '<tr><td>Vergi Dairesi / No</td><td>%s &ndash; %s</td></tr>'
        '<tr><td>Telefon</td><td>%s</td></tr>'
        '<tr><td>E-posta</td><td>%s</td></tr>'
        '<tr><td>Web</td><td>pruvo3d.com</td></tr>'
        '</tbody></table>'
        % (pv_html(s["unvan"]), s["tur"], pv_html(s["adres"]),
           pv_html(s["vd"]), pv_html(s["vkn"]),
           pv_html(s["tel"]), pv_html(s["eposta"]))
    )


# ------------------------------------------------------------------ sayfa gövdeleri
# hakkimizda/iletisim/sss/gizlilik elle yazılmış statik sayfalardır; gövde düzeni <slug>/index.html üzerinden yapılır.


def _teslimat_iade():
    s = SELLER
    return (
        "<h1>Teslimat ve İade Koşulları</h1>"
        '<p class="lead">Kargo, teslimat süresi ve iade/cayma hakkı.</p>'
        "<h2>Teslimat</h2>"
        "<ul>"
        "<li>Ürünler talep üzerine üretildiğinden ürün genellikle <strong>%s</strong> "
        "içinde kargoya verilir; kargo transit süresi adrese ve kargo firmasına göre "
        "ayrıdır. Özel/karmaşık işlerde süre sipariş sırasında bildirilir.</li>"
        # Kargo metni ACIK KURAL olarak yazilir (mimar karari, 16 Tem; Okan kurali —
        # tutarlar secenekler.js kargoKurus ile birebir, degisirse burasi da guncellenir).
        "<li>Gönderiler <strong>%s</strong> ile yapılır. 2.500 TL altındaki siparişlerde "
        "kargo ücreti 250 TL'dir; 2.500 TL ve üzeri siparişlerde kargo ücretsizdir.</li>"
        "<li>Teslimatta pakedi kontrol edin; hasarlıysa tutanak tutturup teslim almayın "
        "ve bizimle iletişime geçin.</li>"
        "</ul>"
        "<h2>Cayma Hakkı ve İade</h2>"
        "<ul>"
        "<li>Standart (stok/seri) ürünlerde, teslim tarihinden itibaren <strong>14 gün</strong> "
        "içinde gerekçe göstermeden cayma hakkınız vardır.</li>"
        "<li>Cayma bildirimini %s adresinden ya da %s numarasından iletin. Ürünü kullanılmamış "
        "ve tekrar satılabilir durumda iade edin.</li>"
        "<li>İade onayından sonra bedel, ödeme yönteminize 14 gün içinde iade edilir.</li>"
        "</ul>"
        "<h2>Cayma Hakkının İstisnası</h2>"
        "<p>Mesafeli Sözleşmeler Yönetmeliği m.15 uyarınca <strong>kişiye/ölçüye özel "
        "üretilen, müşteri talepleri doğrultusunda hazırlanan ürünlerde</strong> cayma "
        "hakkı kullanılamaz. Bu ürünler açıkça özel üretim olarak sipariş edilir. Ayıplı "
        "(kusurlu) ürün elbette ücretsiz onarılır ya da değiştirilir.</p>"
        "<h2>Ayıplı / Yanlış Ürün</h2>"
        "<p>Hatalı, hasarlı ya da siparişten farklı bir ürün ulaşırsa; fotoğrafla birlikte "
        "bize ulaşın, kargo masrafı bize ait olacak şekilde değişim/iade sağlarız.</p>"
        "<h2>İletişim</h2>" + _seller_table()
    ) % (s["teslim"], s["kargo"], pv_html(s["eposta"]), pv_html(s["tel"]))


def _mesafeli_satis():
    s = SELLER
    return (
        "<h1>Mesafeli Satış Sözleşmesi</h1>"
        '<p class="lead">İşbu sözleşme, 6502 sayılı Tüketicinin Korunması Hakkında Kanun ve '
        'Mesafeli Sözleşmeler Yönetmeliği uyarınca düzenlenmiştir.</p>'
        "<h2>1. Taraflar</h2>"
        "<p><strong>SATICI:</strong></p>" + _seller_table() +
        "<p><strong>ALICI:</strong> Sipariş sırasında bildirilen ad-soyad, adres ve "
        "iletişim bilgilerine sahip müşteri.</p>"
        "<h2>2. Konu</h2>"
        "<p>İşbu sözleşmenin konusu, ALICI'nın pruvo3d.com üzerinden siparişini verdiği, "
        "nitelikleri ve satış fiyatı sipariş sırasında belirtilen ürünün satışı ve teslimi "
        "ile tarafların hak ve yükümlülüklerinin belirlenmesidir.</p>"
        "<h2>3. Ürün ve Ödeme</h2>"
        "<p>Ürünün türü, miktarı, özellikleri ve tüm vergiler dâhil satış fiyatı sipariş "
        "onayında belirtilir. Ödeme, Satıcı'nın sunduğu güvenli ödeme yöntemleriyle yapılır; "
        "kart bilgileri Satıcı tarafından saklanmaz.</p>"
        "<h2>4. Teslimat</h2>"
        "<p>Ürün, üretim tamamlandıktan sonra <strong>%s</strong> ile ALICI'nın bildirdiği "
        "adrese gönderilir. Ürün genellikle <strong>%s</strong> içinde kargoya verilir; kargo "
        "transit süresi adrese ve kargo firmasına göre ayrıdır. Özel üretimlerde süre sipariş "
        "sırasında bildirilir; yasal azami süre 30 gündür.</p>"
        "<h2>5. Cayma Hakkı</h2>"
        "<p>ALICI, standart ürünlerde teslim tarihinden itibaren <strong>14 gün</strong> içinde "
        "gerekçe göstermeksizin cayma hakkına sahiptir. Cayma bildirimi %s / %s üzerinden "
        "yapılır; ürün kullanılmamış ve tekrar satılabilir olmalıdır. Bedel 14 gün içinde iade "
        "edilir.</p>"
        "<h2>6. Cayma Hakkının İstisnaları</h2>"
        "<p>Yönetmelik m.15 gereği <strong>ALICI'nın istekleri doğrultusunda kişiye/ölçüye "
        "özel hazırlanan ürünlerde</strong> cayma hakkı kullanılamaz. Bu ürünler sipariş "
        "sırasında açıkça özel üretim olarak teyit edilir.</p>"
        "<h2>7. Genel Hükümler</h2>"
        "<p>ALICI, ürün nitelikleri ve satış fiyatını okuyup bilgi sahibi olduğunu ve "
        "elektronik ortamda siparişi onayladığını kabul eder. Ayıplı üründe ALICI'nın "
        "6502 sayılı Kanun'dan doğan hakları saklıdır.</p>"
        "<h2>8. Uyuşmazlık</h2>"
        "<p>İşbu sözleşmeden doğan uyuşmazlıklarda, Ticaret Bakanlığı'nca ilan edilen "
        "değerlere kadar Tüketici Hakem Heyetleri, aşan uyuşmazlıklarda Tüketici Mahkemeleri "
        "yetkilidir.</p>"
        "<p class=\"upd\">Sipariş onayıyla işbu sözleşme kurulmuş sayılır.</p>"
    ) % (s["kargo"], s["teslim"], pv_html(s["eposta"]), pv_html(s["tel"]))


def _malzeme_rehberi():
    """/malzeme-rehberi/ — sitede satılan 4 malzeme (PLA/PETG/ASA/TPU) tam açıklama +
    karşılaştırma tablosu; ayrıca mühendislik malzemeleri (ABS, Karbon Katkılı — WhatsApp
    özel talebiyle) ayrı bölümde, SİTE SEÇENEĞİ OLARAK SUNULMADAN anlatılır (Okan, 16 Tem).
    İçerik tools/filamentler.json'dan üretilir (tek kaynak; ürün sayfası balonlarıyla
    birebir aynı metinler). Isı değeri verilirken ölçüt adı anılır (HDT @ 0.45 MPa)."""
    ref = filament_ortak.referans()
    site_fil = [f for f in ref["filamentler"] if f.get("site")]
    ozel_fil = [f for f in ref["filamentler"] if not f.get("site")]

    def _esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _bolum(f):
        return (
            "<h2>%s — %s</h2>"
            '<p><strong>Isı dayanımı (HDT @ 0.45 MPa):</strong> %s%s</p>'
            "<p>%s</p>"
            % (_esc(f.get("uzunAd") or f["ad"]), _esc(f["kisaEtiket"]),
               _esc(f["isiDayanimi"]),
               (" (%s)" % _esc(f["isiDetay"])) if f.get("isiDetay") else "",
               _esc(f["uzun"])))

    bolumler = "".join(_bolum(f) for f in site_fil)
    ozel_bolumler = "".join(_bolum(f) for f in ozel_fil)

    def _satir(f):
        return ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                % (_esc(f["ad"]), _esc(f["isiDayanimi"]), _esc(f["uv"]),
                   _esc(f["su"]), _esc(f["darbe"])))

    tablo = (
        '<div style="overflow-x:auto"><table class="info-table karsilastirma"><thead>'
        "<tr><th>Malzeme</th><th>Isı dayanımı*</th><th>Güneş (UV)</th>"
        "<th>Su / nem</th><th>Darbe</th></tr></thead><tbody>"
        + "".join(_satir(f) for f in site_fil) + "</tbody></table></div>"
        '<p class="upd">* Isı dayanımı ölçütü: HDT @ 0.45 MPa; değerler marka bağımsız '
        "yaklaşık aralıklardır.</p>")

    # Kategori -> varsayılan tavsiye özeti (aynı listeyi paylaşan kategoriler gruplanır)
    gruplar, sira = {}, []
    for kat, liste in ref["kategoriTavsiye"].items():
        anahtar = json.dumps(liste, ensure_ascii=False)
        if anahtar not in gruplar:
            gruplar[anahtar] = []
            sira.append(anahtar)
        gruplar[anahtar].append(kat)
    oneri_md = []
    for anahtar in sira:
        liste = json.loads(anahtar)
        parca = liste[0]["ad"]
        for t in liste[1:]:
            parca += ", %s (%s)" % (t["ad"], t.get("not", "").lower() or "alternatif")
        oneri_md.append("<li><strong>%s:</strong> %s</li>"
                        % (_esc(", ".join(gruplar[anahtar])), _esc(parca)))

    wa = ("https://wa.me/905451386526?text=Merhaba%2C%20m%C3%BChendislik%20malzemesiyle%20"
          "%C3%B6zel%20%C3%BCretim%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum.")

    return (
        "<h1>Malzeme Rehberi</h1>"
        '<p class="lead">Hangi malzeme nerede kullanılır? Dürüst değerler, net öneriler.</p>'
        "<p>Her parçayı kullanım yerine göre uygun malzemeyle üretiyoruz. Aşağıda "
        "sitede sipariş edebileceğiniz dört malzeme sınıfının özelliklerini ve hangi "
        "parçada hangisini önerdiğimizi bulabilirsiniz. Emin değilseniz WhatsApp'tan "
        "sorun; kullanım alanınıza göre birlikte seçelim.</p>"
        + bolumler +
        "<h2>Karşılaştırma</h2>" + tablo +
        '<p>Parçanız sürekli sıcak ortamda çalışıyorsa, hangi sınıfın o sıcaklıkta formunu koruduğunu <a href="/isiya-dayanikli-plastik-parca-uretimi/">ısıya dayanıklı plastik parça üretimi</a> sayfasında ayrıntılı anlatıyoruz.'
        ' Sürekli güneş altında duran, sararma ve renk sabitliği önem taşıyan parçalar için ise <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekan parça üretimi</a> sayfasına bakabilirsiniz.'
        ' En üst sınıfa gerçekten ihtiyacınız olup olmadığını tartmak isterseniz <a href="/karbon-fiber-takviyeli-naylon-parca-ne-zaman-gerekir/">karbon fiber takviyeli naylon parça ne zaman gerekir</a> sayfası bunu beş soruyla ayırıyor.</p>'
        "<h2>Hangi parçada hangi malzeme?</h2><ul>" + "".join(oneri_md) + "</ul>"
        "<h2>Mühendislik malzemeleri (özel talep)</h2>"
        '<p>Daha yüksek ısı dayanımı ya da mukavemet gereken kritik parçalar için '
        'ABS ve karbon fiber katkılı malzemeleri <strong>WhatsApp üzerinden özel talep</strong> '
        "olarak değerlendiriyoruz; bu malzemeler standart sipariş akışında (sepet) yer almaz, "
        "kullanım koşullarınızı konuşarak fiyatlandırırız. Karbon katkı ısı dayanımını "
        "artırmaz, taşıyıcı malzemenin değerini korur; katkının kazandırdığı sertlik ve "
        "mukavemettir.</p>"
        + ozel_bolumler +
        '<p><a href="%s" target="_blank" rel="noopener">WhatsApp\'tan mühendislik '
        "malzemesi hakkında bilgi alın &rarr;</a></p>"
        "<p>Ölçüye özel üretilen parçalarda en uygun malzemeyi kullanım alanınıza göre "
        "size sorarak belirleriz.</p>") % _esc(wa)


def _numuneye_gore_plastik_parca_uretimi():
    return (
        "<h1>Numuneye Göre Plastik Parça Üretimi — Getir, Ölçelim, Üretelim</h1>"
        '<p class="lead">Kırılan ya da bulunamayan parçanızı getirin; ölçüsünü alıp ölçüye '
        "özel, doğru malzemeyle üretelim. Tek adet olur.</p>"
        "<h2>Elinizdeki parça kırıldı ya da hiçbir yerde bulunamıyor mu?</h2>"
        "<p>Bazı parçalar artık üretilmez, yedeği kalmaz ya da hiçbir zaman ayrı satılmaz. "
        "Makinenin küçük bir dişlisi, beyaz eşyanın klipsi, teknedeki bir bağlantı aparatı, "
        "eski bir cihazın kırılan tutamağı… Tek bir parça yüzünden koca bir ürün çalışmaz "
        "hale gelir. Söz konusu parça tente iskeletini güverteye bağlayan bir aparatsa "
        '<a href="/tekne-tentesi-bimini-guverte-aparati-ozel-uretim/">tekne tentesi ve bimini '
        "aparatı özel üretim</a> sayfasında o bağlantıların ölçülerini ayrıca veriyoruz. "
        "Piyasada muadili yoktur, kalıpçıya gitseniz tek adet için kalıp masrafı "
        "anlamsızdır.</p>"
        "<p>İşte tam bu noktada devreye giriyoruz: <strong>elinizdeki numuneye göre, ölçüye "
        "özel plastik parça üretiyoruz.</strong> Bir tane bile olsa üretiriz.</p>"
        "<h2>Nasıl çalışır: getir, ölçelim, üretelim</h2>"
        "<ol><li><strong>Getir</strong> — Kırık parçayı, eski numuneyi ya da yerine geçecek "
        "örneği bize ulaştırın. Elinizde parça yoksa ölçü ve fotoğraf da çoğu zaman yeterli olur.</li>"
        "<li><strong>Ölçelim</strong> — Parçanın milimetrik ölçüsünü çıkarır, kırık ya da "
        "aşınmış yerleri tamamlayarak orijinaline sadık kalırız.</li>"
        "<li><strong>Üretelim</strong> — Ölçüye özel üretir, kullanacağınız yere uygun "
        "malzemeyle teslim ederiz.</li></ol>"
        '<p>Ölçü sizden, üretim bizden. Standart kataloglara sığmayan işin adresi burası. Hangi ölçülere ihtiyaç duyduğumuzu ve numuneyi bize nasıl ulaştıracağınızı adım adım anlattığımız <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır ve nasıl gönderilir</a> sayfasına da göz atabilirsiniz.</p>'
        "<h2>Sadece ölçü değil, doğru malzeme</h2>"
        "<p>Bir parçanın dayanması yalnızca ölçüsüne değil, doğru malzemeye de bağlıdır. "
        "İşi olacağı yere göre malzeme merdiveninde konumlandırırız:</p>"
        "<ul><li><strong>Standart iç mekân kullanımı</strong> için ekonomik ve boyutsal "
        "olarak stabil seçenekler.</li>"
        "<li><strong>Isı, güneş (UV) ve dış/deniz koşulu</strong> görecek parçalar için "
        "PETG veya ASA gibi dayanıklı malzemeler.</li>"
        "<li><strong>Yüksek mukavemet</strong> isteyen, yük altında çalışacak parçalar için "
        "karbon ya da cam elyaf takviyeli PA-CF / PA-GF.</li></ul>"
        "<p>Ayrıca farklı renk seçenekleriyle üretim mümkün. Parçanızı anlatın, hangi "
        "malzemenin doğru olduğunu birlikte belirleyelim.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik üretimin de bir sınırı var, bunu baştan söyleriz: Ürettiğimiz pervane "
        "tipi parçalar fan / hafif çark işini görür, tekne itiş gücü için değildir. Profil "
        "ve kızak tipi parçalar hafif, yük taşımayan uygulamalar içindir. Contalar düşük–orta "
        "basınca uygundur. Parçanız ağır bir mekanik yük taşıyacaksa bunu önceden konuşur, "
        "sizi yanıltmayız.</p>"
        "<h2>Siparişinizi verin</h2>"
        '<p>Numuneye göre tek adet plastik parça üretimi için siteden kartla güvenli ödeme '
        'yapabilir veya parçanızın fotoğrafını ve ölçüsünü WhatsApp üzerinden '
        'gönderebilirsiniz: <a href="https://wa.me/905451386526" target="_blank" '
        'rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        '<p><a href="/">PRUVO ürün ve özel üretim hizmetini</a> inceleyin; benzer çözümler '
        'için <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça</a> '
        've <a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçası</a> '
        "sayfalarına bakın.</p>"
        "<p>İlgili çözümler: "
        '<a href="/kirik-plastik-parca-yaptirma/">kırık plastik parçanın yenisini yaptırma</a>, '
        '<a href="/piyasada-bulunmayan-yedek-parca-uretimi/">piyasada bulunmayan yedek parça üretimi</a> ve '
        '<a href="/tek-adet-ozel-parca-uretimi/">tek adet özel parça üretimi</a>. '
        'Parçanın kodunu ya da numarasını hiçbir yerde bulamıyorsanız '
        '<a href="/yedek-parca-kodu-bilinmiyorsa-ne-yapilir/">yedek parça kodu bilinmiyorsa ne yapılır</a> '
        'sayfası kodsuz ilerlemenin yolunu adım adım anlatıyor.</p>'
        "<p>Bulunamayan parça diye bir dert kalmasın. Getirin, ölçelim, üretelim.</p>"
    )


def _bulunamayan_yedek_parca_ozel_uretim():
    return (
        "<h1>Bulunamayan Yedek Parça İçin Özel Üretim</h1>"
        '<p class="lead">Servis “parça yok” mu dedi? Üretimi durmuş ya da piyasada olmayan '
        "parçayı ölçüsüne göre özel üretiyoruz.</p>"
        '<h2>"Parça yok" duvarına mı çarptınız?</h2>'
        "<p>Cihaz sağlam, tek bir parça kırık. Ama yetkili servis “o parça artık gelmiyor” "
        "diyor, model üretimden kalkmış, piyasada da bulunamıyor. <strong>Yetkili servis parça "
        "yok dediğinde ne yapabilirim</strong> sorusunun cevabı çoğu zaman koca bir makineyi "
        "hurdaya çıkarmak zorunda olmadığınız: kırılan, aşınan ya da kaybolan o küçük parçayı "
        "ölçüsüne göre yeniden ürettirebilirsiniz.</p>"
        "<p>PRUVO tam da bunu yapar. <strong>Bulunamayan yedek parça özel üretim</strong> ve "
        "<strong>üretimi durmuş parça yaptırma</strong> işimizin merkezinde: kataloğu olmayan, "
        "tedariki kesilmiş ya da hiç seri üretilmemiş parçaları tek adet halinde üretiriz.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Süreç sade. <strong>Getirirsiniz</strong> — elinizdeki kırık parçayı, eski parçanın "
        "fotoğrafını ya da yerine oturması gereken boşluğun ölçülerini paylaşırsınız. "
        "<strong>Ölçeriz</strong> — parçanın geometrisini, delik yerlerini, kalınlığını ve "
        "montaj noktalarını birebir çıkarırız. <strong>Üretiriz</strong> — ölçüye özel, tek "
        "parça olarak üretip elinize teslim ederiz.</p>"
        "<p>Elinizde numune olması şart değil; ölçüler, montaj deliği aralıkları ve fotoğraf "
        "çoğu zaman yeterli. Kırık parçanın iki yarısı varsa daha da net sonuç alırsınız.</p>"
        "<h2>Ölçüye göre neyi ayarlıyoruz</h2>"
        "<p>Seri üründe olmayan esneklik bizde standart. Parçanın <strong>dış ölçülerini</strong> "
        "birebir hedefe göre ayarlıyoruz; <strong>montaj/vida deliklerinin yerini ve "
        "aralığını</strong> eşleştiriyoruz; klips, tırnak, geçme gibi <strong>bağlantı "
        "detaylarını</strong> yerine oturacak şekilde işliyoruz; kalınlık ve et payını "
        "dayanıklılığa göre belirliyoruz. Renk tarafında <strong>farklı renk seçenekleri</strong> "
        "sunuyoruz. Yani “yaklaşık benzeri” değil, boşluğa tam oturan parça.</p>"
        "<h2>Doğru malzeme, kalıcı çözüm</h2>"
        "<p>İç mekân ve düşük yük parçalarında ekonomik seçenekler yeterlidir; ısı, güneş "
        "(UV), nem ve deniz koşullarında PETG veya ASA gibi dayanıklı malzemelere çıkarız; "
        "taşıyıcı ve yüksek mukavemet gereken parçalarda karbon ya da cam fiber takviyeli "
        "PA-CF / PA-GF kullanırız. Parçanın nerede çalışacağını sorar, ona göre yönlendiririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Her şeyi vaat etmeyiz; güven buradan gelir. Özel üretim parça, tekne iten bir "
        "pervane ya da ağır yük "
        "taşıyan ana bir kiriş değildir; pervane tipi işlerde fan/hafif çark, profillerde "
        "yük-dışı/hafif kullanım, contalarda düşük–orta basınç mantıklıdır. Ağır zorlanmayı "
        "baştan değerlendirip doğru malzemeye ya da uygun tasarıma yönlendiririz.</p>"
        "<h2>Siparişe başlayın</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a> inceleyebilir; '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre parça üretimi</a> '
        've <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası üretimi</a> '
        "hakkında ayrıntı okuyabilirsiniz. "
        'Bulunamayan parça bir karavanın iç donanımındaysa — dolap mandalı, perde rayı ucu, havalandırma kapağı gibi — <a href="/karavan-plastik-parca-ozel-uretim/">karavan plastik yedek parça üretimi</a> sayfasında o kalemleri ayrıca ele alıyoruz. '
        'Parça üretimden kalkmış eski bir aracın içinden çıkıyorsa <a href="/klasik-arac-eski-model-oto-plastik-parca-uretimi/">eski model araç plastik parçası özel üretim</a> sayfası doğrudan o duruma ayrıldı.'
        "</p>"
        '<p>Ölçüye özel üretimi sitemizden kartla online sipariş edebilirsiniz. Emin değilseniz '
        'ya da parçanızı önce değerlendirmemizi istiyorsanız fotoğraf ve ölçüyle WhatsApp’tan '
        'yazın: <a href="https://wa.me/905451386526" target="_blank" '
        'rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p><strong>Ölçü sizden, üretim bizden.</strong></p>"
    )


def _beyaz_esya_plastik_parca_uretimi():
    return (
        "<h1>Beyaz Eşya Plastik Parçası Kırıldı? Yenisini Üretelim</h1>"
        '<p class="lead">Buzdolabı rafı, çamaşır makinesi menteşesi, sepet tekeri… Kırılan '
        "beyaz eşya plastiğini ölçüsüne göre üretiyoruz.</p>"
        "<h2>Buzdolabı rafı, çamaşır makinesi menteşesi, sepet tekeri — küçük bir plastik "
        "parça yüzünden cihaz elde kalmasın</h2>"
        "<p>Beyaz eşyalarda en çok kırılan şey koca bir motor değil; küçük bir plastik "
        "parçadır. Buzdolabı kapak rafı, sebzelik rayı, çamaşır makinesi kapak menteşesi, "
        "bulaşık makinesi sepet tekeri, fan kanadı, düğme, tutamak… Servis çoğu zaman o "
        "parçanın tek satılmadığını, komple modülün değişeceğini söyler; modelin yaşı bir-iki "
        "yılı geçtiyse yedeğinin kalmadığını söyler. Oysa çalışmayan tek şey avuç içi kadar "
        "bir parçadır.</p>"
        "<p>Biz o tek parçayı yeniden üretiyoruz. Komple modül almanıza gerek yok. Kırılan "
        'parça sepet tekeri, aks klipsi veya ray taşıyıcısıysa <a href="/bulasik-makinesi-sepet-tekerlegi-yaptirma/">'
        "bulaşık makinesi sepet tekerleği</a> sayfasında sıcak su, deterjan ve yük sınırlarını ayrıca açıklıyoruz.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Akış basit. <strong>Kırık parçayı bize ulaştırın</strong> — elinizdeki numune, "
        "kırık haliyle bile yeter. "
        "Parçadan <strong>ölçüyü alırız</strong>, kırık kısımları tamamlar, ölçüye özel yeniden "
        "<strong>üretiriz</strong>. Numune yoksa ölçülü bir fotoğraf veya cihazın marka-modeli "
        "de çoğu durumda çıkış noktası olur.</p>"
        "<p>Tek adet üretiriz — minimum sipariş yok. Piyasada bulunamayan, üretimi durmuş, "
        "eski model parçalar tam da bizim işimizdir.</p>"
        "<h2>Ölçüye göre ayarladığımız seçenekler</h2>"
        "<p>Parçayı birebir kopyalamakla kalmayız; ihtiyacınıza göre uyarlarız:</p>"
        "<ul><li><strong>Boyut ve delik ölçüleri</strong> — vida deliği aralığı, çap, kalınlık "
        "sizin parçanıza göre.</li>"
        "<li><strong>Bağlantı ve montaj noktaları</strong> — geçme, vidalı, klipsli detaylar.</li>"
        "<li><strong>Dayanım kademesi</strong> — kullanılacağı yere göre malzeme seçimi.</li>"
        "<li><strong>Farklı renk seçenekleri</strong> — cihaza uygun tonlarda.</li></ul>"
        "<h2>Doğru malzeme, uzun ömür</h2>"
        "<p>Beyaz eşyanın içi sıradan plastiği yorar: sıcak, nem ve sürekli yük. Isıya ve "
        "neme dayanıklı PETG / ASA; sürekli zorlanan menteşe ve taşıyıcı parçalarda "
        "cam ya da karbon fiber takviyeli PA-GF / PA-CF ile yüksek mukavemet hedefleriz. "
        "Fırın içi gibi yüksek sıcaklık noktaları malzemenin sınırını aşabilir; orada sizi "
        "baştan doğru yönlendiririz. Bulaşık makinesi sepeti ya da buharlı pişirici kapağı "
        'gibi sürekli sıcak su ve buhar gören parçalarda seçim daha da daralır; o koşulu <a href="/sicak-su-ve-buhar-temasli-plastik-parca-uretimi/">'
        "sıcak su ve buhara dayanıklı parça üretimi</a> sayfasında ayrıca anlattık.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Her parçayı her koşulda garanti etmeyiz — güveniniz bizim için bir kere satıştan "
        "önemli. Taşıyıcı raf, menteşe, teker, tutamak, düğme ve kanat gibi mekanik parçalarda "
        "doğru malzemeyle uzun ömürlü sonuç alırız. Çok yüksek sıcaklık ya da ağır darbe "
        "alan noktalarda sınırı önceden söyler, en uygun çözümü öneririz.</p>"
        "<h2>Parçanızı üretmeye hazırız</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetine</a> dönün; '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre üretim</a>, '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça</a> ve '
        '<a href="/malzeme-rehberi/">malzeme rehberi</a> sayfalarını inceleyin. '
        '<a href="/olcuye-ozel-izgara-petek-uretimi/">Ölçüye özel ızgara ve menfez</a>, '
        '<a href="/olcuye-ozel-mentese-uretimi/">menteşe</a>, '
        '<a href="/olcuye-ozel-kulp-tutamak-uretimi/">kulp ve tutamak</a> ile '
        '<a href="/ev-aleti-plastik-disli-parca-uretimi/">ev aleti dişli parçaları</a> '
        'için ilgili hizmet sayfalarına geçebilirsiniz.</p>'
        '<p>Cihazın yüzeyindeki kumanda parçası yorulduysa <a href="/olcuye-ozel-dugme-ayar-topuzu-uretimi/">ölçüye özel düğme ve ayar topuzu üretimi</a> sayfasında mil profiline göre nasıl çalıştığımızı anlattık.'
        ' Sepet, çekmece ya da raf altındaki yuvarlanan parça kırıldıysa <a href="/olcuye-ozel-tekerlek-makara-uretimi/">ölçüye özel tekerlek ve makara üretimi</a> sayfası çap, kanal ve aks ölçülerini nasıl aldığımızı gösterir.</p>'
        '<p>Kırık parçanızın fotoğrafını gönderin, birlikte bakalım. Sitemizden kartla online '
        'sipariş verebilir; ölçü danışmanlığı ve özel işler için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _oto_ic_trim_klips_parca_uretimi():
    return (
        "<h1>Bulunamayan Oto İç Trim ve Klips Parçalarının Üretimi</h1>"
        '<p class="lead">Torpido ızgara klipsi, kapak kolu ve iç trim braketi bulunamıyor '
        "mu? Kırılan parçayı numuneden ölçüye özel üretiyoruz.</p>"
        "<h2>Küçük bir klips yüzünden takılıp kalmayın</h2>"
        "<p>Aracın içindeki en küçük parça bile bir yerde tutar: torpido ızgarasını yerine "
        "oturtan klips, kapak kolunun arkasındaki mandal, tavan döşemesini taşıyan braket, "
        "konsol bağlantı tırnağı. Bu alt parçalar çoğu zaman münferit satılmaz; ya koca bir "
        "modül almanız istenir ya da “artık üretilmiyor” yanıtını alırsınız. Model eskidikçe bulunamayan "
        "oto plastik parça sorunu büyür; üretimden yıllar önce kalkmış araçlarda bu tablo "
        'kural halini alır ve <a href="/klasik-arac-eski-model-oto-plastik-parca-uretimi/">eski '
        "model araç plastik parçası özel üretim</a> sayfasında o kalemleri tek tek ele aldık.</p>"
        "<p>PRUVO tam bu noktada devreye girer. Kırılan, çatlayan veya kaybolan iç trim "
        "parçasını <strong>numuneden ölçüye özel üretiyoruz</strong> — tek adet de olsa.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<ol><li><strong>Getir</strong> — Elinizdeki kırık parçayı, kalıntıyı veya net bir "
        "fotoğrafı/ölçüyü bize iletin. Parça kırıksa iki parçadan da eksiksiz bir bütün "
        "çıkarabiliriz.</li>"
        "<li><strong>Ölç</strong> — Klips çapı, tırnak açısı, geçme mesafesi, vida yuvası gibi "
        "kritik ölçüleri milimetrik çıkarırız. Orijinaline oturması için önemli olan tutuş "
        "noktalarıdır.</li>"
        "<li><strong>Üret</strong> — Onayınızla parçayı üretir, size ulaştırırız.</li></ol>"
        "<p>Torpido ızgara klipsi, kapak kolu mandalı, döşeme braketi, konsol tırnağı ve "
        "hava kanalı yönlendiricisi gibi iç aksam parçalarında çalışırız. Özellikle havalandırma "
        'kanadı, yönlendirme klipsi veya ayar düğmesi kırıldıysa <a href="/oto-havalandirma-izgara-klipsi-yaptirma/">'
        "oto havalandırma ızgara klipsi</a> sayfası bağlantı ölçülerini ayrıntılı anlatır.</p>"
        "<h2>Doğru malzeme = orijinali kadar dayanıklı</h2>"
        "<p>Her parça aynı plastikten çıkmaz. İç trim parçaları araç içinde ısıya ve UV’ye "
        "maruz kalır; yazın kapalı araçta torpido üstü ciddi ısınır. Bu yüzden malzemeyi "
        "işine göre seçeriz:</p>"
        "<ul><li>Düşük yük, iç mekân görünürde olmayan parça — dengeli, temiz malzeme.</li>"
        "<li><strong>Isı ve UV dayanımı</strong> gereken görünür trim parçalarında PETG / ASA.</li>"
        "<li><strong>Sürekli esneyen ve yüksek mukavemet isteyen</strong> klips ve braketlerde "
        "karbon ya da cam fiber takviyeli PA-CF / PA-GF.</li>"
        "<li>İç döşeme tonuna yakın farklı renk seçenekleri.</li></ul>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik parçanın gücünü olduğu gibi söyleriz. İç trim klipsi ve braketler bu "
        "üretim için çok uygundur — orijinali de plastiktir. "
        "Ancak sürekli darbe alan taşıyıcı bir gövde ya da yüksek sıcaklıktaki motor bölmesi "
        "parçasında koşulları baştan değerlendiririz. Amacımız parçanın çalışacağı yerde tutmasıdır.</p>"
        "<h2>Parçanızı üretelim</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a>, '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneden parça üretimini</a> ve '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça çözümünü</a> '
        'inceleyebilirsiniz. Genel bağlama ve tutturma işleri için '
        '<a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe üretimi</a> '
        'sayfasına geçebilirsiniz.</p>'
        '<p>Sitemizden kartla online sipariş verebilir; fotoğraf ve ölçü danışmak için '
        'WhatsApp üzerinden yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _makine_parcasi_olcuye_ozel_uretim():
    return (
        "<h1>Makinenizin Bulunamayan Plastik Parçası İçin Ölçüye Özel Üretim</h1>"
        '<p class="lead">Üretimden kalkmış makinenin plastik dişli, kasnak ya da burcu '
        "bulunamıyor mu? Numuneden ölçüye özel üretelim.</p>"
        "<h2>Parça piyasada yok, makine duruyor</h2>"
        "<p>Bir plastik dişli kırıldı, bir kasnak aşındı, bir burç dağıldı; ama parça artık "
        "hiçbir yerde bulunamıyor. Makine üretimden kalkmış, üretici kapanmış, yedek stok "
        "tükenmiş. Elinizde "
        "çalışan koca bir tezgâh var, sırf küçük bir plastik parça yüzünden bekliyor. Sanayide, "
        "atölyede, bakım hattında en çok karşılaşılan tıkanma budur: <strong>parçanın kendisi "
        "değil, bulunamaması</strong> işi durdurur.</p>"
        "<p>PRUVO tam bu noktada devreye girer. Kırılan, aşınan ya da hiç bulunamayan makine "
        "parçasını <strong>ölçüye özel üretiriz</strong>. Katalogdan seçmezsiniz; sizin parçanız, "
        "sizin makineniz için üretilir.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Süreç sade. Kırık parçayı ya da elinizdeki numuneyi bize ulaştırırsınız. Parçayı "
        "<strong>milimetrik olarak ölçeriz</strong>; diş sayısı, çap, kalınlık, montaj deliği "
        "ve geçme toleransı dahil ölçeriz. Numune yoksa teknik çizim, fotoğraf ya da eski "
        "parçanın ölçüleriyle de çalışırız. Ardından <strong>ölçüye özel üretiriz</strong> ve "
        "size ulaştırırız. Bulunamayan bir parçayı yeniden var etmenin en hızlı yolu budur.</p>"
        "<p>Numune ne kadar sağlamsa üretim o kadar birebir olur; parçanız kırık da olsa "
        "çoğu zaman ölçüyü çıkarmaya yeter.</p>"
        "<h2>Doğru malzeme = güven</h2>"
        "<p>Her parça aynı plastikten yapılmaz. Parçanın <strong>çalışacağı koşula göre "
        "malzeme seçeriz</strong>:</p>"
        "<ul><li>Isıya, güneşe ve neme maruz kalan parçalarda PETG veya ASA.</li>"
        "<li>Yük taşıyan, sürtünen ve tork aktaran parçalarda karbon ya da cam fiber "
        "takviyeli PA-CF / PA-GF.</li>"
        "<li>Ölçüye özel üretimde farklı renk seçenekleri.</li></ul>"
        "<p>Böylece parça sadece “boşluğu doldurmaz”, makinenin gerçek çalışma yükü altında "
        "ayakta kalır.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik üretim güçlüdür ama her işin ilacı değildir; size bunu açıkça söyleriz. "
        "Diş profili, kasnak, burç, kılavuz, tampon, muhafaza, tırnak ve konektör gibi "
        "parçalarda iyi sonuç alırız. Bu parçalar paket akışında, kılavuz ve kayış çevresinde çalışıyorsa "
        '<a href="/paketleme-makinesi-plastik-yedek-parca-yaptirma/">paketleme makinesi plastik yedek parçası</a> '
        "sayfası sektörün ölçüm ve kullanım koşullarını ayrıca açıklar. Motor ile pompa arasındaki esnek kavramanın dağılan "
        'göbeğini de aynı yoldan çıkarıyoruz; ölçü listesi <a href="/plastik-kaplin-gobegi-esnek-kavrama-uretimi/">'
        "kaplin göbeği ölçüye özel plastik üretim</a> sayfasında. "
        "Ağır darbe alan, sürekli yüksek sıcaklıkta çalışan ya "
        "da metal mukavemeti şart olan parçalarda sınırı baştan söyleriz. Amaç bir defalık "
        "satış değil, çalışan bir parçadır.</p>"
        "<h2>Parçanızı yeniden üretelim</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetini</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişliyi</a>, '
        '<a href="/numuneye-gore-triger-kasnagi-uretimi/">triger kasnağını</a> ve '
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç ve rulman yatağını</a> ve '
        '<a href="/kasnak-olcuye-ozel-uretim/">ölçüye özel kasnağı</a> '
        'inceleyin. Döner çark yerine karşı pinyonla doğrusal hareket eden dişli çubuğu gerekiyorsa '
        '<a href="/olcuye-ozel-kramayer-disli-uretimi/">ölçüye özel kramayer dişli</a> '
        'sayfasına geçin. Tarıma özgü uygulamalar için '
        '<a href="/tarim-makinesi-plastik-parca-uretimi/">tarım makinesi plastik parça üretimi</a> '
        'sayfasına, ahır ve sağım hattındaki parçalar için '
        '<a href="/sut-sagim-hayvancilik-ekipmani-plastik-parca-uretimi/">süt sağım ve hayvancılık ekipmanı plastik parça üretimi</a> '
        'sayfasına geçebilirsiniz. Tezgâh ve dokuma hattındaki parçalar için '
        '<a href="/tekstil-makinesi-plastik-parca-uretimi/">tekstil makinesi plastik parça üretimi</a> '
        'sayfasına bakabilirsiniz.</p>'
        '<p>Siteden kartla online sipariş verebilir; numune, ölçü ve özel iş danışması için '
        'WhatsApp üzerinden ulaşabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Numuneyi getirin, ölçelim, üretelim; makineniz tekrar çalışsın.</p>"
    )


def _tekne_plastik_parca_ozel_uretim_gocek_fethiye():
    return (
        "<h1>Tekne ve Marina Plastik Parçaları — Göcek ve Fethiye'de Ölçüye Özel Üretim</h1>"
        '<p class="lead">Göcek ve Fethiye’de teknenizin kırılan veya bulunamayan plastik '
        "parçasını deniz koşuluna dayanıklı ASA/PETG ile ölçüye özel üretiyoruz.</p>"
        "<p>Teknede bir parça kırılır ve tam o modelin yedeği hiçbir yerde bulunmaz. Eski bir "
        "motor, üretimi durmuş bir aksesuar ya da güneşte kırılganlaşıp çatlayan bir kapak, "
        "klips, menteşe, ızgara… Bayi “artık gelmiyor” der, marinadaki dükkânlarda muadili "
        "yoktur. Göcek ve Fethiye'de teknesiyle uğraşan herkesin tanıdığı bir sorun bu.</p>"
        "<p>PRUVO tam burada devreye girer: <strong>piyasada olmayan, kırılan ya da hiç "
        "bulunamayan plastik parçayı teknenize göre ölçüye özel üretiyoruz.</strong></p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Yol basit. Kırık parçayı ya da eldeki örneği <strong>getirirsiniz</strong>; birebir "
        "<strong>ölçeriz</strong>, kırık da olsa eldeki ölçüden yeniden çıkarırız; teknenize "
        "takılacak yeni parçayı <strong>üretiriz</strong>. Örnek parça yoksa ölçüleri sizden "
        "alır, çizip onayınıza sunarız. Ölçü sizden, üretim bizden.</p>"
        "<p>Ölçüye özel çalıştığımız için biçim, kalınlık, delik yerleri, kenar ve montaj "
        "detayları sizin parçanıza göre ayarlanır — hazır raf ürünü değil, teknenizin "
        "ihtiyacına oturan parça çıkar. Farklı "
        "renk seçenekleriyle de üretilebilir.</p>"
        "<h2>Deniz koşuluna doğru malzeme</h2>"
        "<p>Deniz ortamı plastiğe acımasız: tuz, sürekli güneş, ısı, nem. Sıradan malzeme "
        "(PLA) burada kısa sürede sararır ve kırılganlaşır. Parçayı çalışacağı yere göre doğru "
        "malzemeye yönlendiririz:</p>"
        "<ul><li><strong>PETG / ASA:</strong> UV, ısı ve deniz koşuluna dayanıklı; güverte "
        "üstü ve dış mekân parçalarının çoğu için doğru seçim; özellikle ASA uzun güneş "
        "maruziyetinde renk ve mukavemetini korur.</li>"
        "<li><strong>PA-CF / PA-GF:</strong> braket, bağlantı ve yüksek mukavemet isteyen "
        "parçalarda karbon ya da cam fiber takviyeli seçenekler.</li></ul>"
        "<p>Hangi parçanın hangi malzemeyle daha uzun dayanacağını birlikte konuşur, size en "
        "uygununu öneririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Bu üretimin sınırını da açıkça söyleriz — güven bundan doğar. Plastik parça; "
        "pervane işi için fan/hafif çark seviyesindedir ve tekneyi iten "
        "sevk pervanesi değildir. Profil ve beam gibi parçalar hafif, yük-dışı kullanım "
        "içindir; conta ise düşük–orta basınçta iş görür. Yani her parçayı üretiriz demeyiz; "
        "parçanızın çalışacağı koşula bakar, o koşulu kaldıracaksa üretir, kaldırmayacaksa "
        "baştan söyleriz.</p>"
        "<h2>Parçanızı üretelim</h2>"
        '<p><a href="/?kategori=Marin">Marin ürünlerini ve ana hizmeti</a>, '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre parça üretimini</a>, '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça çözümünü</a> '
        've <a href="/iletisim/">iletişim bilgilerini</a> inceleyebilirsiniz. '
        'Kırılan parça tente iskeletini güverteye ya da borularını birbirine bağlayan aparatsa '
        '<a href="/tekne-tentesi-bimini-guverte-aparati-ozel-uretim/">tekne tentesi ve bimini aparatı özel üretim</a> '
        'sayfası o bağlantı parçalarını ayrıca anlatıyor.</p>'
        '<p>Siteden kartla online sipariş verebilir; parçanızın fotoğrafı ve ölçüsü için '
        'WhatsApp üzerinden danışabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Göcek ve Fethiye'de tekneniz için ölçüye özel plastik parça: ölçü sizden, "
        "üretim bizden.</p>"
    )


def _kisiye_ozel_logolu_kase_yaptirma():
    return (
        "<h1>Kişiye Özel Logolu Kaşe Yaptırma</h1>"
        '<p class="lead">Yazı, logo ya da ikon işlenmiş kaşenizi ölçünüze göre üretiyoruz: '
        "dikdörtgen/kare/yuvarlak, düz veya kesikli çerçeve, vidalı ayrı sap. Online sipariş.</p>"
        "<p>İşletme adınız, logonuz ya da özel bir ikonla kaşe aradığınızda genelde iki "
        "sorunla karşılaşırsınız: hazır kalıplar sizin ölçünüze ve tasarımınıza "
        "uymaz, ya da eldeki kaşenin sapı kırılır, yazısı silinir, yenisini bulmak zorlaşır. "
        "Piyasada tam istediğiniz biçimde bir karşılığı olmayan bu parçayı, siz nasıl "
        "istiyorsanız öyle, ölçüye özel üretiyoruz. İstenen iş kaşe değil, üretilen parçanın "
        'kendi yüzeyine logo, isim, yön oku veya parça kodu eklemekse <a href="/ozel-parcaya-logo-ve-yazi-isleme/">'
        "özel parçaya logo ve yazı işleme</a> sayfası doğru adrestir.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Yöntemimiz basit. Bize kaşede olmasını istediğiniz içeriği (yazı, logo, ikon) ve "
        "tercih ettiğiniz biçimi iletirsiniz; biz tasarımı ölçünüze göre kurar, ölçüye özel "
        "üretir, kargoya veririz. Kırılan bir kaşenin ölçüsünü verdiğinizde de birebir "
        "karşılığını çıkarabiliriz. "
        "Hazır rafa bağlı değilsiniz; parça ihtiyacınıza göre şekillenir.</p>"
        "<h2>Ölçünüze göre ayarladığımız seçenekler</h2>"
        "<p>Logolu kaşe yaptırma sürecinde şu ayarları size göre belirliyoruz:</p>"
        "<ul><li><strong>İçerik:</strong> düz yazı, ikon/emoji, yazı ile ikonun birlikte "
        "kullanımı ya da kendi logonuz işlenir; gönderdiğiniz logonun işlenmeye uygun olup "
        'olmadığını <a href="/kaseye-islenecek-logo-dosyasi-nasil-hazirlanir/">kaşeye işlenecek '
        "logo dosyası nasıl hazırlanır</a> sayfasındaki kontrollerle önceden görebilirsiniz.</li>"
        "<li><strong>Biçim:</strong> dikdörtgen, kare veya yuvarlak.</li>"
        "<li><strong>Çerçeve:</strong> çerçevesiz, düz çerçeve veya kesikli çerçeve.</li>"
        "<li><strong>Sap:</strong> ayrı parça olarak vidalı takılan sap; sap kırılırsa "
        "gövdeyi değil yalnız o parçayı yenilersiniz.</li>"
        "<li><strong>Boyut:</strong> içeriğe göre ölçeklenir, kartvizit yazınızdan büyük "
        "logonuza kadar orantılı çıkar.</li>"
        "<li><strong>Renk:</strong> farklı renk seçenekleri arasından belirlersiniz.</li></ul>"
        "<p>Belirsiz “her şeyi yaparız” yerine, gerçek ayarları önünüze koyuyoruz; ne "
        "alacağınızı baştan bilirsiniz.</p>"
        "<h2>Doğru malzeme, uzun ömür</h2>"
        "<p>Kaşe her gün elden geçen bir parçadır; malzemesi işini görmeli. Standart günlük "
        "kullanım için dayanıklı gövde, daha zorlu koşullarda ısıya ve dış etkiye direnç "
        "isteyen kullanım için PETG veya ASA, sürekli yük altındaki yoğun kullanım "
        "için karbon/cam fiber takviyeli PA-CF / PA-GF malzemelere kadar sizi doğru "
        "seçenekle eşleştiririz. Amaç, sapın ve gövdenin ilk "
        "aya değil yıllara dayanmasıdır.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Kaşe, mürekkep aktaracağı yüzeyde net iz bırakmalıdır. Çok ince detayları çok "
        "küçük ölçüye sığdırmaya çalışırsak iz kalitesi düşer. Logonuzun okunur çıkacağı "
        "uygun boyutu birlikte belirler, gerçekçi olmayan sonuç sözü vermeyiz.</p>"
        "<h2>Sipariş</h2>"
        '<p><a href="/">PRUVO ürün ve özel üretim hizmetini</a>, '
        '<a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre özel üretimi</a> ve '
        '<a href="/bulunamayan-yedek-parca-ozel-uretim/">tek adet parça çözümünü</a> '
        "inceleyebilirsiniz.</p>"
        '<p>Kaşenizi sitemizden kartla online ödeme ile sipariş edebilirsiniz. Logo dosyası '
        'veya özel biçim için WhatsApp: <a href="https://wa.me/905451386526" target="_blank" '
        'rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _olcuye_ozel_conta_uretimi():
    return (
        "<h1>Ölçüye Özel Conta ve O-ring Üretimi</h1>"
        '<p class="lead">Orijinali bulunmayan contayı iç çap ve kesit ölçünüze göre '
        "üretiyoruz. Yuvarlak, kare ve pahlı profil seçenekleri sunuyoruz.</p>"
        "<p>Aradığınız conta piyasada yok mu? Eski makinenin, pompanın, valfin ya da bir "
        "armatürün sızdırmazlık contası kırıldı, sertleşti veya orijinali artık bulunamıyor "
        "olabilir. Standart dışı bir iç çap, alışılmadık bir kesit ya da üretimi bırakılmış "
        "bir parça söz konusu olduğunda tek tek mağaza dolaşmak çoğu zaman sonuç vermez. Biz "
        "tam bu noktada devreye giriyoruz: <strong>orijinali bulunmayan contayı ölçünüze göre özel "
        "üretiyoruz.</strong></p>"
        "<h2>Nasıl çalışır: getirin, ölçelim, üretelim</h2>"
        "<p>Süreç basit. Elinizdeki eski contayı, sızdıran parçayı ya da yalnızca ölçülerini "
        "bize iletirsiniz. Ölçüyü "
        "teyit eder, doğru profili ve malzemeyi birlikte belirler, ardından size özel üretiriz. "
        "Bir örneğiniz yoksa iç çap ve kesit kalınlığı üretim için yeterli olabilir.</p>"
        "<h2>Ölçünüze göre ne ayarlanabilir?</h2>"
        "<p>Conta hazır bir katalog parçası değil; sizin uygulamanıza göre kurgulanır:</p>"
        "<ul><li><strong>Ölçü:</strong> AS568 standart O-ring kodu ile ya da doğrudan verdiğiniz "
        "iç çap + kesit kalınlığıyla üretiriz.</li>"
        "<li><strong>Profil:</strong> yuvarlak (O), kare, pahlı, D-ring veya X-ring — yuvanıza "
        "hangisi oturuyorsa.</li>"
        "<li><strong>Kullanım yeri:</strong> su, yakıt, ısı ya da dış mekân (UV) — nerede "
        "çalışacağı malzeme seçimini belirler.</li>"
        "<li><strong>Esnek yapı:</strong> yuvasına oturan, sıkıştırıldığında görevini gören "
        "esneklikte.</li><li>Farklı renk seçenekleri.</li></ul>"
        "<h2>Doğru malzeme, doğru koşul</h2>"
        "<p>Sızdırmazlıkta malzeme her şeydir. Sıradan bir seçim yerine, contanın maruz "
        "kalacağı koşula göre yükseliriz: ısı, güneş ve nem söz konusuysa PETG veya ASA; "
        "daha yüksek dayanım ve boyut "
        "kararlılığı gereken yerlerde karbon ya da cam fiber takviyeli PA-CF / PA-GF "
        "malzemelere geçeriz. Hangi ortamda çalışacağını bize söylediğinizde, ömrü en uzun "
        "olacak malzemeye yönlendiririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Şeffaf olalım: özel tasarım üretim conta <strong>düşük–orta basınçlı</strong> "
        "sızdırmazlık için "
        "uygundur; toz, sıvı sızıntısı, titreşim yalıtımı, kapak ve muhafaza contaları gibi. "
        "Sızdırmazlık değil, tekrarlı titreşimi azaltan esnek ayak, tampon veya ara parça gerekiyorsa "
        '<a href="/titresim-sonumleyici-esnek-plastik-parca-yaptirma/">titreşim sönümleyici esnek parça</a> '
        "sayfası daha uygundur. "
        "Yüksek basınçlı hidrolik hatlar ya da ağır yük altındaki sistemler bu üretimin "
        "sınırının dışındadır. Contanızın nerede çalışacağını paylaşırsanız, uygunsa üretir; "
        "değilse baştan söyleriz. Amacımız işe yarayan parça, satılmış bir parça değil.</p>"
        "<h2>Siparişe başlayın</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişliyi</a> ve '
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">ölçüye özel burç ve rulman '
        'yatağını</a> inceleyebilirsiniz. Kapatma ve koruma ihtiyacı için '
        '<a href="/olcuye-ozel-tapa-kapak-uretimi/">ölçüye özel tapa ve kapak üretimi</a> '
        'sayfasına geçebilirsiniz.</p>'
        '<p>Ölçünüz belliyse ya da elinizde örnek parça varsa hemen başlayabiliriz. Sitemizden '
        'kartla online ödeme yapabilir; ölçü ve malzeme danışmanlığı için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _olcuye_ozel_plastik_disli_uretimi():
    return (
        "<h1>Ölçüye Özel Plastik Dişli ve Kramayer Üretimi</h1>"
        '<p class="lead">Kırılan ya da aşınan dişlinizi numuneden ölçüye özel üretiyoruz: '
        "düz, helis, konik, sonsuz ve kramayer.</p>"
        "<p>Bir dişli aşındığında ya da kırıldığında iş çoğu zaman durur. Eski makinelerde, "
        "ithal cihazlarda, mutfak robotundan bahçe ekipmanına kadar birçok üründe o dişlinin "
        "yedeği artık üretilmez, piyasada bulunmaz ya da yalnızca komple modül olarak satılır. "
        "Elinizdeki parça küçük bir plastik çark olsa bile onsuz sistem çalışmaz.</p>"
        "<p><strong>Kırık ya da aşınan dişlinizi numuneden ölçüye özel üretiyoruz.</strong> "
        "Tek bir parça için bile çalışırız.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Akış basit. Kırık dişliyi ya da net ölçülerini bize iletirsiniz; biz ölçüyü "
        "çıkarır, eşleşecek dişliyle "
        "uyumlu olacak şekilde üretiriz. Modül ve diş adımı biliniyorsa doğrudan kullanır, "
        "bilinmiyorsa numuneden ölçeriz. <strong>Ölçü sizden, üretim bizden.</strong></p>"
        "<h2>Ölçünüze göre ayarladığımız seçenekler</h2>"
        "<p>Standart bir katalog değil, sizin parçanız için üretim yapıyoruz. Belirleyebildiğimiz "
        "başlıklar:</p>"
        "<ul><li><strong>Dişli tipi:</strong> düz (spur), helis, çift helis, konik, sonsuz "
        "(worm), iç dişli, taç dişli ve kramayer.</li>"
        "<li><strong>Ölçüler:</strong> diş sayısı, dış çap, kalınlık ve mil çapı.</li>"
        "<li><strong>Modül / diş adımı:</strong> biliniyorsa değere göre, bilinmiyorsa "
        'numuneden çıkararak; kırık dişlide bu değeri kendiniz bulmak isterseniz '
        '<a href="/kirik-dislinin-modulu-nasil-bulunur/">kırık dişlinin modülü nasıl bulunur</a> '
        "sayfasındaki dış çap ve diş sayısı yöntemi yeterlidir.</li>"
        "<li>Farklı renk seçenekleri.</li></ul>"
        "<p>Bir dişlinin eşleştiği dişliyle çalışabilmesi için aynı modül ve aynı basınç "
        "açısında olması gerekir. Döner hareketi doğrusal harekete çeviren dişli çubuğu "
        'gerekiyorsa modül, diş sayısı, kalınlık ve karşı pinyon uyumunu <a href="/olcuye-ozel-kramayer-disli-uretimi/">'
        "ölçüye özel kramayer dişli</a> sayfasında ayrıca ele alıyoruz. Bu yüzden mümkünse eşleşeceği dişliyi ya da net ölçüleri "
        "de isteriz.</p>"
        "<h2>Doğru malzeme: yüke göre seçim</h2>"
        "<p>Bir dişlinin ömrü, ne kadar zorlandığına ve nerede çalıştığına bağlıdır. Sıradan "
        "malzeme (PLA) çabuk yenilir. Isı, nem ve dış koşul varsa PETG ya da ASA; gerçek "
        "yük ve sürtünme varsa karbon veya cam fiber takviyeli malzeme (PA-CF / PA-GF) "
        "öneririz. Bu takviyeli malzemeler sertlik ve aşınma dayanımı bakımından belirgin "
        "biçimde üstündür — yük taşıyan dişlilerde fark buradan gelir. Dişliniz için takviyeli "
        'sınıfın şart olup olmadığını <a href="/karbon-fiber-takviyeli-naylon-parca-ne-zaman-gerekir/">'
        "karbon fiber takviyeli naylon parça ne zaman gerekir</a> sayfasındaki sorularla önceden "
        "tartabilirsiniz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik dişli, elektrikli el aletlerinden ofis makinelerine, ev ve bahçe "
        "ekipmanından hafif mekanizmalara kadar geniş bir alanda işe yarar. Yüksek torklu ağır "
        "sanayi güç aktarım hatları ya da metalin zorunlu olduğu yerler için doğru cevap "
        "plastik değildir. Parçanızın çalışacağı koşulu bize söyleyin; uyacaksa en dayanıklı "
        "malzemeye yönlendirir, uymuyorsa açıkça belirtiriz. Amacımız çalışan bir parça "
        "teslim etmektir.</p>"
        "<h2>Sipariş ve ölçü danışma</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetini</a>, '
        '<a href="/numuneye-gore-triger-kasnagi-uretimi/">ölçüye özel triger kasnağını</a> '
        've <a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç ve rulman '
        "yatağını</a> inceleyin.</p>"
        '<p>Sitemizden kartla online ödeme yapabilir; dişlinizin fotoğrafı ve ölçüleri için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
    )


def _numuneye_gore_triger_kasnagi_uretimi():
    return (
        "<h1>Numuneye Göre Triger Kasnağı ve Kayışı Üretimi</h1>"
        '<p class="lead">Bulunamayan triger kasnağını profil ve diş sayısına göre, mil tipi '
        "ve flanş seçimiyle üretiyoruz.</p>"
        "<p>Makinenizin, yazıcınızın veya CNC tezgâhınızın triger kasnağı kırılmış ve tam "
        "karşılığını hiçbir yerde bulamıyorsunuz. Model kalkmış, stok tükenmiş, ya da eldeki "
        "kasnak sizin mil çapınıza veya kayış profilinize uymuyor. Piyasadaki hazır kasnaklar "
        "standart ölçülerde gelir; sizin ihtiyacınız ise belirli bir diş sayısı, belirli bir "
        "genişlik ve belirli bir mil bağlantısıdır. Böyle bir parça için tek yol, onu "
        "<strong>ölçüye özel ürettirmektir</strong>.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>İşleyiş basittir. Elinizdeki kırık kasnağı, kayışı ya da ölçülerini bize "
        "iletirsiniz. Kayış profilini, diş sayısını "
        "ve mil detaylarını netleştirir; parçayı verdiğiniz ölçüye göre üretiriz. Numune yoksa "
        "yalnızca ölçülerle de çalışırız. Amaç mevcut kayışınıza ve milinize sorunsuz oturan "
        "bir parça çıkarmaktır.</p>"
        "<h2>Neyi ölçünüze göre ayarlıyoruz?</h2>"
        "<p>Standart bir katalogdan değil, sizin ihtiyacınıza göre üretim yaptığımız için şu "
        "detayların hepsini belirleyebilirsiniz:</p>"
        "<ul><li><strong>Kayış profili:</strong> GT2 (2 / 3 / 5 mm), HTD (3M / 5M / 8M), "
        'T2.5, T5, T10, AT5, MXL, XL, L. Elinizdeki kayışın hangi profilde olduğunu '
        '<a href="/kayis-profili-nasil-belirlenir-gt2-htd-t5/">kayış profili nasıl anlaşılır</a> '
        "sayfasındaki diş adımı ölçümüyle çıkarabilirsiniz.</li>"
        "<li><strong>Diş sayısı ve kayış genişliği</strong> — mevcut kayışınıza tam oturacak "
        "şekilde.</li>"
        "<li><strong>Mil bağlantısı:</strong> düz, kanallı (keyway), altıgen ya da D-lama; "
        "ölçtüğünüz <strong>mil çapına</strong> göre.</li>"
        "<li><strong>Yan flanş:</strong> iki tarafta, yalnız üstte, yalnız altta ya da "
        "flanşsız — kayış kaçmasın diye.</li>"
        "<li><strong>Göbek (hub) ve setskur</strong> — mile kilitlemek için, isterseniz.</li>"
        "<li>Farklı renk seçenekleri.</li></ul>"
        "<h2>Doğru malzeme güveni</h2>"
        "<p>Her kasnak aynı koşulda çalışmaz, biz de malzemeyi kullanım yerine göre seçeriz. "
        "Standart iç mekân uygulamaları için dayanıklı temel malzemeler; ısı, UV ve nemli "
        "ortamlarda PETG veya ASA; sürekli yük ve aşınmada karbon ya da cam fiber "
        "takviyeli PA-CF / PA-GF kullanırız. Parçanın nerede döneceğini paylaştığınızda doğru "
        "malzemeye yönlendiririz.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Açık olalım: özel ürettiğimiz kasnaklar <strong>düşük–orta yük ve tork</strong> "
        "için uygundur; hafif tahrik, konumlandırma ve düşük güçlü aktarım işlerinde güvenle "
        "çalışır. Yüksek güçlü, ağır sanayi tahrik hatlarında metal kasnağın yerini tutmaz. "
        "Parçanızı çalışacağı yere göre değerlendirir, uygun değilse baştan söyleriz — bu "
        "bizim için güvenin temeli.</p>"
        "<h2>Kasnağınızı ürettirin</h2>"
        '<p><a href="/">Ana hizmet ve ürünleri</a>, '
        '<a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçasını</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">plastik dişliyi</a> ve '
        '<a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç çözümünü</a>, '
        '<a href="/olcuye-ozel-baglanti-konektor/">ölçüye özel konektörü</a>, '
        '<a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketini</a>, '
        '<a href="/olcuye-ozel-profil-beam/">ölçüye özel profili</a> ve '
        '<a href="/kasnak-olcuye-ozel-uretim/">ölçüye özel kasnağı</a> '
        "inceleyebilirsiniz.</p>"
        '<p>Bulunamayan triger kasnağınızı ya da kayış kasnağınızı ölçüye özel üretiyoruz. '
        'Ölçülerinizi veya numunenizi paylaşın, üretelim. Sitemizden kartla online ödeme '
        'yapabilir; ölçü ve profil danışmanlığı için '
        'WhatsApp hattımıza yazabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _numuneden_plastik_burc_rulman_uretimi():
    return (
        "<h1>Numuneden Plastik Burç ve Rulman Yatağı Üretimi</h1>"
        '<p class="lead">Aşınan burcu ya da rulman yatağını iç/dış çap ve genişlik '
        "ölçünüze göre üretiyoruz. Standart kod ya da özel ölçüyle çalışıyoruz.</p>"
        "<p>Aşınmış bir burç, yerinde durmayan bir rulman yatağı ya da makinede boşluk yapan "
        "tek bir parça yüzünden koca bir tezgâh durabilir. Çoğu zaman o parça piyasada artık "
        "bulunmaz, üzerinde kod yoktur veya orijinali fahiş fiyatlıdır. Eski parça kırık ya "
        "da yıpranmış olsa bile ondan yola çıkarak yenisini üretiyoruz.</p>"
        "<h2>Nasıl çalışır: getir, ölç, üret</h2>"
        "<p>Çalışma şeklimiz basit: parçayı ya da ölçüyü getirin, biz ölçüp size özel üretelim. "
        "Elinizde numune varsa iç çap, dış çap ve genişliği bizzat ölçeriz; numune yoksa "
        "vereceğiniz ölçülere göre çalışırız. Sonuç, "
        "montaj yerine oturan ve boşluk yapmayan bir parçadır.</p>"
        "<h2>Plastik burç üretimi: ölçü sizden</h2>"
        "<p>Burç ve rulman yatağını iki yoldan üretiyoruz. Standart bir rulman ölçüsü (608, "
        "6200, 6900, R8 ya da flanşlı F688ZZ gibi) veriyorsanız o koda göre; standart dışıysa "
        "doğrudan iç çap + dış çap + genişlik ölçünüze göre üretiriz. İhtiyaç olan yerlerde "
        "flanşlı seçenek sunarız, böylece parça yatağında eksenel olarak sabit durur. İster "
        "tek parça sabit burç, ister yerinde dönen rulman yatağı olsun, ölçüye özel burç "
        "üretimi ile parçayı uygulamanıza göre çıkarırız. Farklı renk seçenekleri de mümkün.</p>"
        "<p>Numuneden rulman yatağı yaptırma sürecinde en önemli soru şudur: parça nerede, "
        "hangi hızda ve yükte çalışacak? İhtiyaç rulmanın kendisi değil, müşterinin temin "
        "ettiği metal mil veya rulmanı çevreleyen gövde ve mesnetse "
        '<a href="/mil-rulman-icin-olcuye-ozel-plastik-yuva/">mil ve rulman için ölçüye özel plastik yuva</a> '
        "sayfası doğru başlangıçtır. Kullanım "
        "koşulu malzemeyi, malzeme de parçanın ömrünü belirler.</p>"
        "<h2>Doğru malzeme güveni</h2>"
        "<p>Sıradan plastik yerine, işin gereğine göre doğru malzemeyi seçiyoruz. Isıya, "
        "dışarıda çalışacaksa UV ve neme dayanıklı PETG ya da ASA; sürtünme ve "
        "yükün arttığı yerlerde karbon veya cam fiber takviyeli PA-CF / PA-GF gibi yüksek "
        "mukavemetli malzemeler kullanırız. Parça hem ölçünüze hem çalışacağı ortama uygun olur.</p>"
        "<h2>Dürüst sınır</h2>"
        "<p>Plastik burcun da bir sınırı var, bunu baştan söyleriz: bu parçalar "
        "<strong>düşük–orta hız ve yükte, çoğunlukla kuru (yağsız) çalışma</strong> "
        "için uygundur. Yüksek devirli, ağır yük altındaki ana rulman uygulamalarının yerini "
        "tutmaz. Parçanızın nerede çalışacağını bize anlatın; uygun değilse en baştan "
        "söyleriz, uygunsa doğru malzemeye yönlendiririz. Amaç, size gerçekten işini gören "
        "bir parça vermek.</p>"
        "<h2>Sipariş verin</h2>"
        '<p><a href="/">PRUVO özel üretim hizmetini</a>, '
        '<a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçasını</a>, '
        '<a href="/olcuye-ozel-plastik-disli-uretimi/">plastik dişliyi</a> ve '
        '<a href="/numuneye-gore-triger-kasnagi-uretimi/">triger kasnağını</a> '
        "inceleyebilirsiniz. Mil yatağı değil de iki mili birbirine bağlayan esnek kavrama "
        'dağıldıysa <a href="/plastik-kaplin-gobegi-esnek-kavrama-uretimi/">kaplin göbeği '
        "ölçüye özel plastik üretim</a> sayfasına geçin.</p>"
        '<p>Ölçünüzü hazırlayın, gerisini biz halledelim. Siteden kartla online ödeme '
        'yapabilir; ölçü danışmanlığı, özel iş veya numune '
        'için WhatsApp hattımıza ulaşabilirsiniz: <a href="https://wa.me/905451386526" '
        'target="_blank" rel="noopener"><strong>+90 545 138 6526</strong></a>.</p>'
        "<p>Ölçü sizden, üretim bizden.</p>"
    )


def _piyasada_bulunmayan_yedek_parca_uretimi():
    return (u"""<h1>Piyasada Bulunmayan Yedek Parçayı Üretiyoruz — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Muadili çıkmayan, hiç ayrı satılmamış ya da modeli çoktan kalkmış parçayı elinizde tutuyorsunuz — biz onu ölçüp yeniden üretiyoruz.</p>
<p>Bazı parçalar için arama motoruna ne yazarsanız yazın sonuç çıkmaz. Çünkü o parça piyasada tek başına hiç satılmamıştır; komple bir grubun içinde gelmiş, tek başına stok kodu bile almamıştır. Ya da üretici o modeli yıllar önce bırakmış, servis desteği tümüyle kapanmıştır. Parçanın üzerinde okunur bir kod da kalmadıysa arama yönteminiz tümden değişir; <a href="/yedek-parca-kodu-bilinmiyorsa-ne-yapilir/">yedek parça kodu bilinmiyorsa ne yapılır</a> sayfası kodun yerini ölçünün nasıl aldığını anlatıyor. Elinizdeki cihaz, makine ya da mobilya sapasağlam çalışıyor; sırf bu tek plastik parça kırıldığı için kullanılamaz halde bekliyor.</p>
<p>Bu, fiyat karşılaştırıp en ucuzunu bulma meselesi değil. Ortada karşılaştırılacak bir muadil yok. İhtiyacınız olan şey, o parçanın bire bir aynısının yeniden var edilmesi. İşte bizim işimiz tam olarak bu: elinizdeki örnekten yola çıkıp ölçüsüne sadık kalarak parçayı özel üretiyoruz. Numune kırık, eksik ya da deforme olsa bile ölçüleri çıkarıp bütünleyebiliriz; benzer bir işi <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> sayfasında da anlatıyoruz.</p>
<p>Servis desteği hâlâ süren ama yedeği stokta bulunmayan parçalar için ayrı bir sayfamız var — o durumu <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretim</a> tarafında ele alıyoruz. Bu sayfa özellikle muadili hiç olmayan, tek başına satılmamış ya da modeli tümden kalkmış parçalar içindir. Kargoyla nereden gönderirseniz gönderin, üretip geri yolluyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırık ya da sağlam parçanızın fotoğrafını, varsa eski ölçülerini WhatsApp'tan gönderin; fiziksel numuneyi kargoyla yollayabilirsiniz.</li>
<li><strong>Ölç.</strong> Parçayı milimetrik ölçeriz; kırık veya aşınmışsa özgün halini tersine çıkarır, montaj noktalarını ve tork/temas yüzeylerini doğrularız.</li>
<li><strong>Üret.</strong> Onayınızın ardından doğru malzemeyle özel üretir, kargoyla adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her parça kendine özgü olduğu için üretimi tek tek sizin örneğinize göre kurarız:</p>
<ul>
<li><strong>Bire bir ölçü</strong> — dış boyut, delik çapları, delikler arası mesafe, vida/cıvata yuvaları elinizdeki örneğe göre.</li>
<li><strong>Montaj detayı</strong> — geçme, vidalı, klipsli ya da kanal-ray bağlantı; tırnak ve kilit noktaları özgün parçadaki gibi.</li>
<li><strong>Malzeme sınıfı</strong> — kullanılacağı ortama göre standart, ısı/UV/nem dayanımlı ya da yüksek mukavemetli seçim.</li>
<li><strong>Farklı renk seçenekleri</strong> — görünür parçalarda mevcut ürününüze yakın ton.</li>
<li><strong>Eksik/kırık numune tamamlama</strong> — parça bütün değilse ölçüyü çıkarıp özgün formu bütünleriz.</li>
</ul>
<p>Kendi çiziminiz ya da teknik resminiz varsa onunla da çalışırız; <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfası bu yönü daha ayrıntılı anlatır.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçeriz. İç mekanda, yük altında olmayan parçalarda standart malzeme yeterlidir. Güneş, ısı, nem ya da dış ortam söz konusuysa PETG veya ASA gibi dayanıklı malzemelere çıkarız. Zorlanan, tork veya darbe gören parçalarda karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Hangi parçanın nereye oturduğunu <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında açıklıyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parça plastik esaslıdır; doğru malzemeyle çok yerde orijinalin işini görür ama sınırını açıkça söyleriz. Yük taşıyan, sürekli yüksek tork ya da ağır darbe altında çalışan metal bir parçanın tam yerine geçmesini vaat etmeyiz. Bağlantı, kapak, klips, dişli/kasnak gibi düşük–orta yük ve tork gören parçalarda ise doğru malzemeyle uzun ömürlü sonuç alırsınız. Parçanızın nerede çalıştığını sorar, buna göre yönlendiririz; hangi parça tiplerini hiç üstlenmediğimizi de <a href="/hangi-parcalar-ozel-uretimle-yapilamaz/">hangi parçalar özel üretimle yapılamaz</a> sayfasında açıkça yazdık.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Parçanızın fotoğrafını ve ölçülerini WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; birlikte netleştirip üretime alalım. Ölçüsü ve malzemesi netleşen işlerde siteden kartla online ödemeyle de sipariş verebilirsiniz. Numuneyi kargoyla gönderin, üretip adresinize yollayalım.</p>""")


def _kirik_plastik_parca_yaptirma():
    return (u"""<h1>Kırık Plastik Parça mı? Yenisini Üretelim — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizde kırılmış, çatlamış ya da parçalanmış bir plastik parça var ve piyasada aynısını bulamıyorsunuz; biz o kırık numuneden yenisini ölçüye özel üretiyoruz.</p>
<p>Çoğu kırık parça öyle görünür: küçük bir kulakçık kopmuştur, bir tırnak kırılmıştır, gövde ikiye ayrılmıştır. Onarmaya çalışırsınız, yapıştırırsınız, bir süre sonra aynı yerden yine gider. Aslında aradığınız şey tamir değil — o parçanın <strong>sağlam bir yenisi</strong>. Ama üretici çoktan modeli kaldırmıştır, yedek parça listesinde yoktur ya da "komple takım al" derler. Sizin tek ihtiyacınız o küçük plastik parça.</p>
<p>İşte tam burada devreye giriyoruz. Kırık parça çöp değil, ölçünün ta kendisidir. Elinizdeki kırık örnek çoğu zaman yeniyi çıkarmaya yeter: kırık kenarları birleştirir, ölçüleri alır, deforme olmuş yerleri toparlar ve parçayı sıfırdan, ölçüye özel yeniden üretiriz. Parçaların çoğu ikiye ayrılmış olsa bile iki yarım bir araya gelince tam geometri okunur. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Kayıp bir tırnak, aşınmış bir diş, kopmuş bir bağlantı — bunların hepsi telafi edilebilir; kırılan yalnızca kapağı yerinde tutan geçme tırnaksa <a href="/kirik-plastik-tirnak-yaptirma/">kırık plastik tırnak yaptırma</a> sayfası o tek parçayı ayrıca ele alır. Amaç, orijinaline bakan ama gerektiğinde daha dayanıklı malzemeden çıkan bir parça vermek. Kırık parçadan yenisini yaptırma işi, aslında bir kez doğru yapıldığında bir daha kırılmayan parçayı almaktır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir / gönder.</strong> Kırık parçayı kargoyla bize yollayın; parçalıysa tüm kırık kısımları birlikte koyun — eksik kenar, ölçü kaybı demek.</li>
<li><strong>Ölç.</strong> Kırık örnekten ölçüleri çıkarır, deforme veya aşınmış bölgeleri toparlar, montaj noktalarını doğrularız. Emin olamadığımız bir nokta olursa size sorarız.</li>
<li><strong>Üret.</strong> Onayınızdan sonra parçayı ölçüye özel üretip adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Ebat ve geometri:</strong> kırık numunenin birebir ölçüsünde ya da istediğiniz noktada düzeltilmiş ölçüde.</li>
<li><strong>Kopan/aşınan detay:</strong> kırılan tırnak, kulakçık, diş veya bağlantı noktası yeniden oluşturulur.</li>
<li><strong>Bağlantı biçimi:</strong> vida deliği, geçmeli tırnak, klips yuvası aslına uygun konumlandırılır.</li>
<li><strong>Dayanım kademesi:</strong> aynı yerden bir daha kırılmaması için parçayı <a href="/darbeye-dayanikli-plastik-parca-yaptirma/">darbeye dayanıklı bir malzeme sınıfına</a> taşıyabiliriz.</li>
<li><strong>Farklı renk seçenekleri:</strong> görünür parçalarda size uygun renk.</li>
</ul>
<p>Benzer işler için <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> ve <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretim</a> sayfalarına da bakabilirsiniz.</p>
<h2>Doğru malzeme</h2>
<p>Parçanın çalışacağı yere göre malzemeyi seçeriz. İç mekânda, düşük yük altında çalışan standart parçalar için dayanıklı bir taban malzeme yeterlidir. Isıya, güneşe (UV), neme ya da deniz koşuluna maruz kalan parçalarda PETG veya ASA gibi dayanıklı malzemelere çıkarız. Yük taşıyan, tork gören, sık zorlanan parçalarda ise karbon ya da cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Beyaz eşya parçaları için ayrıntı: <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a>. Malzeme seçiminin tümü: <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>
<h2>Dürüst sınır</h2>
<p>Kırık parçanın yenisini üretebilmemiz için elimizde okunabilir bir geometri olması gerekir; parça toz haline gelmişse ya da kritik bir bölge tamamen kayıpsa ölçü çıkmaz. Ürettiğimiz parça, malzemenin sınırları içinde çalışır: yük taşıyan bağlantılarda montaj/hafif yük, dişli-kasnak türü parçalarda düşük–orta tork esas alınır. Parçayı çalışacağı koşula göre doğru malzemeye yönlendirir, yapamayacağımız zorlamayı baştan söyleriz.</p>
<h2>Sipariş</h2>
<p>Sitemizden kartla online ödeyerek siparişinizi başlatabilir, kırık parçanızı kargoyla gönderebilirsiniz. Ölçü danışmanlığı, özel iş ve emin olamadığınız durumlar için WhatsApp: <strong>+90 545 138 6526</strong>. Kırık parçayı elinizde tutun — o, yenisinin ölçüsüdür.</p>""")


def _tek_adet_ozel_parca_uretimi():
    return (u"""<h1>Tek Adet Özel Parça Üretimi — Minimum Sipariş Yok</h1>
<p class="lead">Kırılan, kaybolan ya da hiçbir yerde bulamadığınız o tek parçayı, kalıp masrafı olmadan ve adet zorunluluğu olmadan ölçüsüne birebir üretiriz.</p>
<p>Elinizde tek bir parça var. Kırıldı, aşındı ya da orijinali yıllar önce üretimden kalktı. Bir tedarikçiye sorduğunuzda ilk duyduğunuz cümle hep aynı: "Kalıp çıkarmamız gerekir, o da şu kadar tutar" ya da "en az 500 adet basarız, altına inmeyiz." Tek bir parça için kalıp masrafını göze almak mantıksız; 500 adet almaksa saçma. Arada sıkışıp kalıyorsunuz.</p>
<p>Biz tam bu boşluk için varız. Bizde <strong>minimum sipariş yok</strong> — bir tanesi de üretilir, ikisi de. Kalıp çıkarmadığımız için o maliyet faturanıza binmez; tek parçanın kendi maliyetini ödersiniz, o kadar. İster elinizdeki numuneyi ölçelim, ister bir teknik çizim gönderin, ister tek seferlik bir prototip fikri olsun — adetli olmayan özel üretim bizim standart işimiz. Tek adet bir işin bedelinin hangi kalemlerden oluştuğunu <a href="/ozel-parca-uretimi-fiyati-nasil-belirlenir/">özel parça üretimi fiyatı nasıl belirlenir</a> sayfasında kalem kalem anlattık.</p>
<p>Bu, prototip aşamasındaki bir tasarımı tek parça yaptırmak isteyen mühendisten, evindeki bir cihazın tek bir dişli-tırnağını arayan tamirciye kadar herkes için geçerli. "Sadece bir tane lazım, kimse yapmıyor" dediğiniz noktada devreye giriyoruz. Ölçü sizden, üretim bizden.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Elinizdeki kırık ya da eski parçayı kargoyla bize gönderin; ya da ölçülerini, fotoğrafını, varsa çizimini iletin. Numune yoksa nereye takıldığını anlatın, birlikte netleştiririz.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçeriz; oturması gereken deliği, dişi, kenar boşluğunu birebir çıkarırız. Tek adette hata payı olmasın diye kritik ölçüleri sizinle teyit ederiz.</li>
<li><strong>Üret</strong> — Onayladığınız ölçüde tek parçanızı üretir, kargoyla adresinize yollarız; tek adet bir işin ölçü onayından sonra <a href="/ozel-parca-kac-gunde-hazir-olur/">kaç günde hazır olduğunu</a> ayrı bir sayfada kademe kademe yazdık. İşin doğasına göre en uygun malzemeyi öneririz.</li>
</ol>
<h2>Doğru malzeme</h2>
<p>Her parça aynı malzemeyi kaldırmaz; seçimi işin çalışacağı yere göre yaparız. İç mekân, düşük yük ve görünürde duracak parçalarda standart malzeme yeterlidir. Isıya, güneşe (UV), neme ya da deniz koşuluna maruz kalacak bir parça için <strong>PETG veya ASA</strong> gibi dayanıklı malzemelere çıkarız. Gerçek mukavemet, tork ya da darbe gereken yerlerde ise <strong>karbon ya da cam fiber takviyeli (PA-CF / PA-GF)</strong> seçeneği devreye girer. <strong>Farklı renk seçenekleri</strong> de mümkün. Hangi parçanın hangi malzemeyi hak ettiğini siz bilmek zorunda değilsiniz — kullanım yerini söyleyin, doğru malzemeye biz yönlendirelim.</p>
<h2>Dürüst sınır</h2>
<p>Üretilen parça, malzemesinin sınırları içinde iş görür; bunu baştan söylemek işimizin bir parçası. Bağlantı, braket, kapak, tutucu gibi <strong>yük taşımayan montaj parçalarında</strong> ve prototiplerde sonuç çok sağlıklı olur. Aşırı yük altında sürekli çalışacak, yüksek sıcaklıkta zorlanacak ya da metalin yerini birebir tutması beklenen kritik güvenlik parçalarında ise sınırı açıkça belirtir, gerekiyorsa sizi doğru malzemeye ya da farklı bir çözüme yönlendiririz. Tek adet iş de olsa yapmayacağımızı yapabiliriz demeyiz.</p>
<p>Benzer ihtiyaçlarda şu sayfalara da bakabilirsiniz: <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> ve <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parçanın özel üretimi</a>.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü ya da numunenizi hazırlayın, gerisini biz halledelim. Ürünleri inceleyip <strong>kartla online ödemeyle</strong> doğrudan sipariş vermek için <a href="/">mağazamıza</a> göz atabilirsiniz. Tek parçalık özel işiniz, ölçü danışması ya da elinizdeki numuneyle ilgili sorularınız için WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_baglanti_konektor():
    return (u"""<h1>Ölçüye Özel Bağlantı ve Konektör Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Kırılan bağlantı parçasının yerine takılanı bulamıyorsanız, o parçayı ölçünüze göre üretiyoruz.</p>
<p>Boruyu boruya, çubuğu çubuğa birleştiren o küçük ekleme parçası kırıldığında iş çoğu zaman durur. Piyasada tam o çapta, tam o açıda konektör yoktur; yakın olanı zorla takarsınız, ya oynar ya çatlar. Eski parça artık üretilmiyordur, marka bilinmiyordur, ölçüsü standart değildir. "Benzeri olur mu?" diye dükkan dükkan gezmek yerine tek bir çözüm var: elinizdeki parçayı ya da birleştirmek istediğiniz boruların ölçüsünü bize verin.</p>
<p>Biz ölçüye özel bağlantı ve konektör üretimi yapıyoruz. Kaç kollu olacağını, hangi çapta boruyu geçireceğini, kolların hangi açıyla duracağını siz söylüyorsunuz; parçayı o ölçülere göre üretip gönderiyoruz. Sergi, stant, çadır iskeleti, sera, raf sistemi, korkuluk, hobi konstrüksiyon — çubuk birleştirme ekleminin standart dışı olduğu her yerde iş görür. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Örnek parça, fotoğraf ya da iki borunun dış çapı ve aradaki açı — elimize ne geçerse ona göre üretime başlarız. Daha büyük mekanik işleriniz için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfamıza da bakabilirsiniz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir:</strong> Kırık konektörü, birleştireceğiniz boruları ya da net bir fotoğraf/ölçü krokisini WhatsApp'tan gönderin.</li>
<li><strong>Ölç:</strong> Boru/çubuk çapını, kol sayısını, açıyı ve geçme sıkılığını birlikte netleştiririz.</li>
<li><strong>Üret:</strong> Onayınızdan sonra parçayı ölçüye özel üretip kargoyla adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Boru bağlantı konektörü yaptırırken şu değerleri sizin işinize göre belirliyoruz:</p>
<ul>
<li><strong>Kol sayısı:</strong> 2 kol (düz ek veya dirsek), 3 kol (T / Y / köşe birleşimi), 4 kol (X kesişim).</li>
<li><strong>Kol kesiti:</strong> yuvarlak, kare veya sekizgen — geçireceğiniz profile göre.</li>
<li><strong>Geçecek çubuk/boru çapı:</strong> milimetrik olarak sizin borunuza göre.</li>
<li><strong>Geçme sıkılığı:</strong> sıkı (sabit oturur), normal ya da gevşek (sökülüp takılabilir).</li>
<li><strong>Kol boyu:</strong> her kolun uzunluğu ayrı ayrı ayarlanır.</li>
<li><strong>Kollar arası açı:</strong> düz, dirsek ya da istediğiniz özel derece.</li>
<li><strong>Farklı renk seçenekleri.</strong></li>
</ul>
<h2>Doğru malzeme</h2>
<p>Konektörü nerede kullanacağınıza göre malzemeyi seçeriz. İç mekanda, hafif yükte standart dayanıklı malzeme yeter. Dışarıda, güneş ve nem altında, teknede kullanılacaksa ısıya ve UV'ye dayanıklı PETG veya ASA'ya çıkarız. Titreşimli, zorlayan, taşıyıcı bir noktadaki birleşim içinse karbon veya cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Hangi malzemenin gerektiğini birlikte kararlaştırırız; <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında sınıfların farkını ayrıntılı bulabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Bağlantı ve konektör parçaları yük dışı montaj ve birleştirme işleri içindir — iskeleti bir arada tutar, hizalar, sabitler. Üzerine sürekli ağır darbe binen, insan taşıyan ya da yapısal güvenlik gerektiren taşıyıcı bir noktada tek başına ana yük elemanı olarak önermeyiz. Parçanın çalışacağı yeri baştan konuşur, gereken yerde daha güçlü malzemeye yönlendirir, taşıyamayacağı yükü de açıkça söyleriz.</p>
<h2>Sipariş</h2>
<p>Ölçüsü belli konektörleri siteden kartla online ödeyerek sipariş edebilirsiniz. Ölçü danışmak, örnek parça göndermek veya özel açı/çap istemek için WhatsApp'tan yazın: <strong>+90 545 138 6526</strong>. Örnekten birebir üretime dair <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre üretim</a> yaklaşımımız burada da aynı: getirin, ölçelim, üretelim.</p>""")


def _olcuye_ozel_montaj_braketi():
    return (u"""<h1>Ölçüye Özel Montaj Braketi Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizdeki parça standart ölçüde değilse, hazır braket çoğu zaman tam oturmaz; ölçüye özel montaj braketi üretimi ile deliğinden açısına kadar tam sizin yerinize göre üretiriz.</p>
<p>Piyasadaki köşebent ve L braketler belli deliklere, belli kalınlıklara göre seri üretilir. Sizin montajınız ise çoğu zaman araya sıkışmış bir boşluğa, tuhaf bir açıya ya da mevcut deliklerle hizalanması gereken özel bir vida düzenine oturur. Standart braketi zorla eğip bükmek, fazladan delik açmak veya iki parçayı üst üste bindirmek hem çirkin durur hem güveni bozar.</p>
<p>Bir makinede, panoda, tekne içinde ya da mobilyada "tam buraya oturan bir parça olsa" dediğiniz noktayı biz üretiriz. Kırılan orijinal braketi getirin, fotoğrafını veya ölçüsünü paylaşın; aynısını ya da geliştirilmiş halini çıkaralım. Özel köşebent braket yaptırma, açılı montaj braketi üretimi ya da mevcut delik aralığına birebir oturan L braket ölçüye özel üretim — hepsi aynı akışla ilerler. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Bağlantı noktalarını taşıyan makine gövdeleri için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfamıza da bakabilirsiniz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık braketi, montaj boşluğunun ölçüsünü veya basit bir el çizimini iletin. Kargoyla parçayı da gönderebilirsiniz; üretip yollarız.</li>
<li><strong>Ölç</strong> — Kalınlık, kol uzunlukları, iç açı ve vida deliklerinin yerini birlikte netleştiririz; braket sık sökülecekse dişin plastikte mi duracağını yoksa <a href="/plastik-parcaya-vida-disi-acilir-mi/">gömme somuna mı oturacağını</a> da bu adımda konuşuruz. Nereye monte edileceğine göre en doğru geometriyi öneririz.</li>
<li><strong>Üret</strong> — Onayınızdan sonra ölçüye özel üretiriz ve adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Braket tipi:</strong> açılı/köşebent, köşe, düz plaka, T, L veya Y formu</li>
<li><strong>İç açı:</strong> açılı braketlerde istediğiniz dereceye göre (90°, 120° veya ara açılar)</li>
<li><strong>Ölçüler:</strong> kalınlık × genişlik × kol uzunluğu milimetrik olarak size özel</li>
<li><strong>Vida düzeni:</strong> M3–M8 veya inç ölçü; her kola delik sayısı ve delik aralığı sizin montajınıza göre</li>
<li><strong>Takviye:</strong> açılı braketlerde payanda/flanş desteği ile ek sağlamlık</li>
<li><strong>Simetri:</strong> sağ/sol ayna çift olarak, karşılıklı montaj için</li>
<li><strong>Farklı renk seçenekleri</strong></li>
</ul>
<h2>Doğru malzeme</h2>
<p>İşin yerine göre malzemeyi birlikte seçeriz. İç mekân, düşük yüklü montajlar için standart dayanımlı malzeme yeterlidir. Isı, UV, nem ya da deniz koşulu varsa PETG veya ASA gibi dayanıklı malzemelere çıkarız. Yükü gerçekten taşıyan, titreşim ve zorlanma altındaki braketlerde ise karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. <a href="/malzeme-rehberi/">Malzeme rehberi</a> sayfasında hangi koşula hangi malzemenin uyduğunu ayrıntılı anlatıyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Braket, yük-dışı ve montaj amaçlı bir bağlantı parçasıdır; iki yüzeyi hizalar, konumlar, hafif kuvvetleri taşır. Ana taşıyıcı kiriş, kaldırma noktası ya da sürekli ağır darbe/çekme alan kritik yapı elemanı olarak konumlandırmayız. Nereye monte edeceğinizi söyleyin, o yüke göre malzeme ve takviyeyi doğru seçelim — taşıyabileceğinden fazlasını vaat etmeyiz.</p>
<p>Numuneden birebir kopya çıkarma yaklaşımımızı <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre triger kasnağı üretimi</a> örneğinde de görebilirsiniz.</p>
<h2>Sipariş</h2>
<p>Sitemizden kartla online ödemeyle sipariş verebilirsiniz. Ölçü danışmanlığı, özel geometri ya da numune göndermek için WhatsApp hattımız açık: <strong>+90 545 138 6526</strong>. Braketinizi getirin, ölçelim, üretelim.</p>""")


def _olcuye_ozel_profil_beam():
    return (u"""<h1>Ölçüye Özel Profil, Kızak ve Kiriş Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizdeki profil, kızak ya da kiriş piyasada tam ölçüsüyle yok mu; kırıldı, eğildi, standart boy tutmuyor mu? Ölçüsünü siz verin, biz ölçüye özel üretip kargoyla yollayalım.</p>
<p>Standart bir sigma profil, U kanal ya da köşebent bulmak kolay — ama işiniz milimetrik oturmadığında o standart boy hiçbir işe yaramıyor. Bir dolabın içine tam giren kızak, bir tezgâhın altına oturan hafif kiriş, özel bir kesitte bir bağlantı profili... Bunlar rafta satılmaz. Mağazadan mağazaya dolaşıp "yaklaşık" bir şey almak yerine, gerçek ölçünüzü söyleyin.</p>
<p><strong>Ölçüye özel profil üretimi</strong> işimizin çekirdeğinde bu var: kesit tipini, yüksekliğini, genişliğini, et kalınlığını ve boyunu siz belirlersiniz; biz o ölçüde üretiriz. İster mevcut bir parçayı örnek gönderin, ister ölçüleri yazın — sonucu size özel çıkarırız. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Aynı mantıkla ürettiğimiz diğer ölçüye özel işler için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> ve <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre triger kasnağı üretimi</a> sayfalarına da bakabilirsiniz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir/gönder</strong> — kırık ya da örnek profili kargoyla yollayın, ya da kesit tipini ve ölçüleri (yükseklik × genişlik × et kalınlığı × uzunluk) bize iletin.</li>
<li><strong>Ölçelim</strong> — kesiti ve ölçüleri netleştirir, kullanım yerinize göre doğru malzemeyi öneririz.</li>
<li><strong>Üretelim</strong> — ölçüye özel üretip adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Kesit tipi:</strong> I, T, L köşebent, Z, U kanal, kutu/dikdörtgen, çokgen, elips ve alüminyum sigma profil formu.</li>
<li><strong>Alüminyum sigma standart boyu:</strong> 2020, 3030, 4040, 4545, 5050, 6060, 8080, 100 serisine uygun kesit.</li>
<li><strong>Ana ölçüler:</strong> yükseklik × genişlik × et kalınlığı × uzunluk — hepsi milimetrik, size göre.</li>
<li><strong>İçi dolu ya da boru/boşluklu</strong> gövde — ağırlık ve kullanıma göre.</li>
<li><strong>Çokgen kesitte kenar sayısı:</strong> 5–18 arası.</li>
<li><strong>Farklı renk seçenekleri</strong> — kullanım yerine uygun tonlar.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Standart iç mekân ve hafif kullanım için dayanıklı temel malzeme yeterli. Isıya, UV'ye, neme ya da deniz koşuluna maruz kalacak profillerde PETG veya ASA'ya çıkarız. Yük altında biçimini koruması gereken, daha sert ve mukavemetli kiriş/kızak gerekiyorsa karbon ya da cam fiber takviyeli PA-CF / PA-GF öneririz. Parçanın nerede çalışacağını söyleyin, malzemeyi ona göre seçelim. Malzeme seçenekleri ve hangi koşulda hangisinin doğru olduğu için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasına göz atabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Açık konuşalım: ürettiğimiz profil, kızak ve kirişler <strong>yük taşıyan yapısal eleman değildir</strong> — hafif, yük-dışı kullanım içindir. Kılavuz kızağı, kablo/hat taşıyıcısı, hafif çerçeve, montaj profili, konumlandırma kirişi gibi işlerde çok iyi sonuç verir; taşıma hattındaki kılavuz çıta ve yan tutucu profilleri için ölçü ayrıntısını <a href="/konveyor-bant-plastik-parca-yaptirma/">konveyör hattı parçaları</a> sayfasında bulursunuz. Ana taşıyıcı gövde, üzerine yük binen ya da darbe alan konstrüksiyon içinse metal profil doğru tercihtir; sizi yanıltmayız. En uygun malzemeyle, sınırını bilerek üretiriz.</p>
<h2>Sipariş</h2>
<p>Siteden kartla online ödemeyle ölçüye özel siparişinizi verebilirsiniz. Kesit, ölçü ya da malzeme konusunda emin değilseniz WhatsApp'tan yazın, birlikte netleştirelim: <strong>+90 545 138 6526</strong>. Ölçünüzü gönderin, üretip yollayalım.</p>""")


def _kasnak_olcuye_ozel_uretim():
    return (u"""<h1>Ölçüye Özel Kasnak Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Elinizdeki kasnak kırıldı ya da aşındı, tam karşılığını hiçbir yerde bulamıyorsanız; ölçüsünü verin, birebir karşılığını üretelim.</p>
<p>Eski makinede, çırpıcıda, konveyörde, pompada ya da hobi tezgahında dönen bir kayış kasnağı çatladığında iş çoğu zaman durur; taşıma hattında duran şey kasnak değil de kılavuz çıta, kızak ya da makara gövdesiyse <a href="/konveyor-bant-plastik-parca-yaptirma/">konveyör bant parçası üretimi</a> sayfamız o parçaları ölçü ölçü anlatıyor. Piyasada aynı çapta, aynı oluk sayısında, aynı mil çapında hazır parça bulmak neredeyse imkansızdır; "yakın" olan da kayışı oturtmaz, titreşim yapar, kısa sürede yeniden atar. Marka gitmiş, model plakası silinmiş, üretici parçayı bırakmışsa iş iyice çıkmaza girer.</p>
<p>PRUVO tam da bu noktada devreye girer. Ölçüye özel kasnak üretimi bizim işimiz: elinizdeki numuneden ya da verdiğiniz ölçülerden yola çıkıp, kayışınıza doğru oturan kasnağı üretiriz. V kayış kasnağı yaptırma mı, düz kayış kasnağı üretimi mi, yoksa kordon (yuvarlak kayış) kasnağı mı fark etmez — mevcut sisteminize göre çözeriz.</p>
<p>Kayışın yaptırdığınız numuneden kasnak üretimi en garantili yoldur: kırık parçayı kargoyla gönderin, ölçüp aynısını çıkaralım. Ölçü sizden, üretim bizden.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir:</strong> Kırık ya da örnek kasnağı kargoyla bize gönderin; parça yoksa çap, oluk sayısı, mil çapı ve kayış tipini iletin.</li>
<li><strong>Ölç:</strong> Kanal profilini, dış çapı ve göbek bağlantısını milimetrik ölçer, kayışınıza göre teyit ederiz.</li>
<li><strong>Üret:</strong> Onaydan sonra üretip adresinize yollarız; çalışacağı yere göre doğru malzemeye yönlendiririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Kayış tipi:</strong> V-kayış, düz kayış ya da kordon (yuvarlak kayış) — hangisiyle çalışıyorsanız ona göre.</li>
<li><strong>Kanal (oluk) sayısı:</strong> Tek oluktan çok oluklu kasnağa kadar mevcut kayış düzeninize göre.</li>
<li><strong>Dış çap (mm):</strong> Devir/oran ihtiyacınıza uygun tam ölçü.</li>
<li><strong>Mil çapı ve göbek bağlantısı:</strong> Düz geçme, kanallı (kama yuvalı) ya da setskur (sıkma vidalı) göbek.</li>
<li><strong>Yan flanş:</strong> Kayışın kasnaktan kaçmaması için yanak/flanş ekleriz.</li>
<li><strong>Farklı renk seçenekleri:</strong> İhtiyacınıza göre renk çözeriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Kapalı ortamda, ılıman koşulda çalışan bir kasnak için standart mühendislik plastiği yeterlidir. Isıya, güneşe (UV), neme ya da deniz koşuluna maruz kalan yerlerde PETG veya ASA tercih ederiz. Yükün ve torkun arttığı, aşınmanın hızlandığı uygulamalarda ise karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemetli üretim yaparız. Parçanın nerede döneceğini bize söyleyin; malzemeyi ona göre seçelim.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz kasnak <strong>düşük–orta yük ve tork</strong> aralığı içindir: hobi tezgahı, hafif konveyör, küçük pompa, çırpıcı, model/prototip düzenekleri gibi işler. Ağır sanayi tahriki, yüksek devirli güç aktarımı ya da yüksek tork taşıyan ana kayış-kasnak hattı için tek başına önermeyiz. Zaman/senkron gerektiren dişli kayış (GT2/HTD triger) işiniz varsa doğru sayfa <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre triger kasnağı üretimi</a>; kayışınızın profilini bilmiyorsanız <a href="/kayis-profili-nasil-belirlenir-gt2-htd-t5/">kayış profili nasıl anlaşılır</a> sayfasındaki ölçüm profili verir; dişli çark ihtiyacınız için <a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişli üretimi</a>, mil yatağı için <a href="/numuneden-plastik-burc-rulman-uretimi/">numuneden plastik burç/rulman üretimi</a> sayfalarına bakın. Genel bir makine parçası mı arıyorsunuz? <a href="/makine-parcasi-olcuye-ozel-uretim/">Makine parçası ölçüye özel üretim</a> sayfası başlangıç noktanız olsun.</p>
<h2>Sipariş</h2>
<p>Siparişi siteden kartla online verebilirsiniz. Ölçü paylaşmak, numunenizi konuşmak ya da uygunluk sormak isterseniz WhatsApp hattımız açık: <strong>+90 545 138 6526</strong>. Kırık kasnağı gönderin, doğru karşılığını üretip yollayalım.</p>""")


def _olcuye_ozel_vida_somun_civata_uretimi():
    return (u"""<h1>Ölçüye Özel Vida, Somun ve Cıvata Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Piyasada bulunamayan çapta, adımda ya da malzemede bir bağlantı elemanına mı ihtiyacınız var? Ölçünüzü verin, size özel vida, somun ve cıvatayı üretip gönderelim.</p>
<p>Standart cıvata her yerde; asıl sorun standart olmayanı bulmakta başlar. Kırılan bir plastik somunun tam karşılığı yok, eski bir makinenin diş adımı bugünkü kataloglara uymuyor, ya da metal bir bağlantının iletken olması işinizi bozuyor. Bu noktada mağazadan mağazaya dolaşmak yerine parçanın kendisini çözüme dönüştürüyoruz.</p>
<p>Elinizdeki numuneyi ya da ölçüleri esas alıyoruz. Özel çap, özel diş adımı, standart dışı kafa biçimi — hangi detay sizi zorluyorsa onu ölçüye özel üretiyoruz. Trapez ve ACME hareket vidalarında olduğu gibi piyasada hazır karşılığı zor bulunan formları, ayar ve konumlandırma mekanizmalarınız için milimetrik çıkarıyoruz.</p>
<p>Metal olmayan, yalıtımlı bağlantı arayanlar için de doğru yerdesiniz. Elektronik montajda kısa devre riskini kaldıran, ısı köprüsü oluşturmayan, korozyona girmeyen plastik somun ve cıvataları ölçünüze göre hazırlıyoruz. <strong>Ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçanızı, teknik çizimi ya da yalnızca ölçülerinizi bize iletin. Numune yoksa çap, boy ve diş adımını yazmanız yeterli.</li>
<li><strong>Ölç</strong> — Diş tipini, kafa biçimini ve kullanım yerini birlikte netleştirir, işe uygun malzemeye yönlendiririz.</li>
<li><strong>Üret</strong> — Onaydan sonra size özel üretir, kargoyla adresinize göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Ürün tipi:</strong> başlı cıvata / dişli mil-saplama / somun / pul</li>
<li><strong>Ölçü standardı:</strong> metrik (M) / inç (UTS) / tümüyle özel çap + adım</li>
<li><strong>Ölçü ve boy:</strong> M2–M20 arası çap, milimetre hassasiyetinde boy</li>
<li><strong>Diş tipi:</strong> kaba, ince, trapez, ACME veya kare (hareket vidası için)</li>
<li><strong>Kafa tipi:</strong> gömme, yuvarlak, imbus, altıgen ya da pan</li>
<li><strong>Tornavida ağzı:</strong> imbus, torx, yıldız veya düz</li>
<li><strong>Somun ve pul:</strong> somun şekli ve kalınlığı, normal ya da geniş pul boyu</li>
<li><strong>Farklı renk seçenekleri</strong> — montajınıza uygun renkte</li>
</ul>
<p>Belirsiz vaat yerine gerçek ayarları konuşuyoruz; hangi kombinasyon işinizi görüyorsa onu üretiyoruz. Daha karmaşık montajlar için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfamıza da bakabilirsiniz.</p>
<h2>Doğru malzeme</h2>
<p>Kullanım yeri malzemeyi belirler. İç mekan, hafif ayar ve hobi işleri için standart dayanımlı seçenek yeterlidir. Isı, UV, nem ya da deniz koşuluna açık bağlantılarda PETG veya ASA gibi dayanıklı malzemelere çıkarız. Yük ve tork taşıyan, tekrar tekrar sökülüp takılan yerlerde ise karbon ya da cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Malzeme seçiminde tereddüt ederseniz <a href="/malzeme-rehberi/">malzeme rehberi</a> yol gösterir.</p>
<h2>Dürüst sınır</h2>
<p>Açık olalım: ölçüye özel ürettiğimiz vida ve somunlar hafif–orta yük, ayar, yalıtım ve hobi işleri içindir. Yüksek tork altında sürekli çalışan, güvenlik kritik ya da ağır makine bağlantılarında çelik cıvatanın yerine geçmez. Vidanın oturacağı parçanın kendisini üretiyorsak diş tarafını ayrıca planlarız; gömme somun mu yoksa doğrudan diş mi gerektiğini <a href="/plastik-parcaya-vida-disi-acilir-mi/">plastik parçaya vida dişi açılır mı</a> sayfasında karşılaştırdık. İşiniz yapıya girer girmez size bunu söyler, doğru malzemeye ya da metal çözüme yönlendiririz. Sızdırmazlık gerektiren noktalarda <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> ile tamamlayabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Siparişinizi siteden kartla online ödemeyle verebilirsiniz; ölçüye özel işler dahil güvenli ödeme açık. <a href="/">Ürünleri incelemek</a> ve sipariş için mağazamıza göz atın. Ölçü danışmanlığı, özel iş ve numune paylaşımı için WhatsApp hattımız da hazır: <strong>+90 545 138 6526</strong>. Ölçünüzü iletin, gerisini biz halledelim.</p>""")


def _olcuye_ozel_yay_uretimi():
    return (u"""<h1>Ölçüye Özel Plastik Yay Üretimi — Getir, Ölçelim, Üretelim</h1>
<p class="lead">Kırılan ya da piyasada tam boyu bulunamayan bir bası yayını, elinizdeki ölçüye göre üretip yolluyoruz.</p>
<p>Bir kapak mekanizması takılıyor, bir klips artık geri itmiyor, tampon içindeki küçük yay kırılmış ve o parçanın kodu, markası, yedeği hiçbir yerde yok. Standart bir yay katalogundan geçen ürün sizinkine ne boyca ne kuvvetçe uyuyor; ya çok sert, ya çok uzun, ya oturmuyor. Bu, çelik bir yay değil ama çelik yay da gerektirmiyor — sadece belirli bir boyda, belirli bir yumuşaklıkta geri dönüş kuvveti isteyen bir eleman.</p>
<p>İşte bu noktada devreye giriyoruz. Kırık parçanızı, eski yayın ölçülerini ya da yerine oturması gereken boşluğun ölçüsünü bize iletin; biz o yayı milimetrik olarak, ihtiyacınız olan sertlikte özel üretelim. Elinizde numune yoksa boy, çap ve ne kadar kuvvet beklediğinizi konuşarak da çıkarabiliriz. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>İki farklı yay ailesi üretiyoruz: klasik <strong>spiral bası yayı</strong> (sıkışıp geri açılan, oturaklı yay) ve <strong>dalga / serpantin flexure elemanları</strong> (şerit formunda, esneyerek geri dönen yaylar). Hangisinin işinize uyduğunu ölçünüze bakıp söyleriz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık yayı, numuneyi ya da yerine gireceği boşluğun ölçüsünü kargoyla gönderin veya WhatsApp'tan fotoğraf ve ölçüleri iletin.</li>
<li><strong>Ölç</strong> — Serbest boy, çap, sarım ve beklenen kuvveti çıkarır, doğru yay tipini ve malzemeyi öneririz.</li>
<li><strong>Üret</strong> — Onayınızdan sonra ölçüye özel üretip adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Yay tipi:</strong> spiral bası yayı ya da dalga / serpantin (flexure) form</li>
<li><strong>Spiral için:</strong> serbest boy, dış çap, aktif sarım sayısı, tel çapı ve düz oturma ucu</li>
<li><strong>Dalga için:</strong> form seçimi (sinüs, kare, üçgen, testere ya da darbe profili), genlik, çevrim sayısı, toplam boy ve şerit kalınlığı</li>
<li><strong>Sertlik / yumuşaklık:</strong> tel çapı ve sarım sayısına göre daha sert ya da daha yumuşak geri dönüş</li>
<li><strong>Farklı renk seçenekleri</strong></li>
</ul>
<p>Bu maddeleri sizin uygulamanıza göre birlikte netleştiriyoruz; ölçü kağıt üzerinde değil, gerçek parçanız üzerinden çıkıyor.</p>
<h2>Doğru malzeme</h2>
<p>Yayın çalışacağı yer malzemeyi belirler. İç mekanda, ılıman koşulda çalışan bir geri dönüş yayı için standart malzeme yeterli. Isı, nem, UV ya da açık hava söz konusuysa PETG veya ASA gibi dayanıklı malzemelere çıkıyoruz. Tekrarlı yükleme altında daha yüksek mukavemet ve yorulma direnci gereken yerlerde ise karbon ya da cam fiber takviyeli PA-CF / PA-GF öneriyoruz. Aynı mantığı diğer parçalarınızda da uyguluyoruz; ayrıntı için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasına bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz yaylar hafif kuvvet ve geri dönüş işleri içindir: klips, kapak yayı, tampon, hafif basıya karşı geri iten elemanlar. Hareketi geri itmek değil de belirli bir noktada durdurmak istiyorsanız iş <a href="/plastik-stoper-durdurucu-yaptirma/">plastik stoper ve durdurucu üretimi</a> tarafına düşer. Yüksek kuvvetli, sürekli ağır yük taşıyan ya da yorulma kritik bir çelik yayın yerine geçmez. Beklediğiniz kuvveti bize söyleyin; iş bu sınırın dışına çıkıyorsa açıkça belirtir, boşuna üretim yapmayız.</p>
<h2>Sipariş</h2>
<p>Site üzerinden kartla online ödeyip sipariş verebilir ya da ölçünüzü konuşmak için WhatsApp'tan <strong>+90 545 138 6526</strong> hattına yazabilirsiniz. Yayla birlikte çalışan bir tespit ya da montaj parçası da mı lazım — <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> ve <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> sayfalarımıza göz atın. Kırık parçayı gönderin, ölçelim, üretip yollayalım.</p>""")


def _elektronik_cihaz_plastik_parca_uretimi():
    return (u"""<h1>Elektronik Cihazın Kırık Plastik Parçasını Üretelim</h1>
<p class="lead">Cihaz sağlam çalışıyor ama küçücük bir plastik kırıldı diye kullanamıyorsanız, o parçayı ölçüsüne göre yeniden üretiyoruz.</p>
<p>Uzaktan kumandanın pil kapağı kaçtı, ses sisteminin düğmesi koptu, modemin ayağı kırıldı, cihazın kapağını tutan minik klips ikiye ayrıldı... İçindeki elektronik gayet iyi durumda, ama o bir tek parça bulunamadığı için koca cihaz çekmecede bekliyor. Bunu çok yaşıyorsunuz, çünkü bu parçalar hiçbir zaman ayrı satılmaz: üretici cihazı komple değiştirmenizi bekler, servis "yedeği yok" der, internette aradığınızda tam o modelin parçası hiçbir yerde çıkmaz. Cihazın etiketi silinmiş ve parçanın kodu okunmuyorsa <a href="/yedek-parca-kodu-bilinmiyorsa-ne-yapilir/">yedek parça kodu bilinmiyorsa ne yapılır</a> sayfasındaki adımlar kodsuz ilerlemenin yolunu gösterir.</p>
<p>İşte tam bu boşluğu dolduruyoruz. Elinizdeki kırık parçayı ya da onun takıldığı yeri esas alıp, birebir uyan yenisini üretiyoruz. <strong>Cihaz düğmesi, klipsi, pil kapağı, gövde muhafazası, montaj braketi, ayak, tırnak, kılavuz</strong> — küçük ve bulunması imkânsız plastik parçalar bizim işimiz. Yeni parça eski deliklere oturur, aynı yere geçer, cihaz yeniden çalışır hale gelir.</p>
<p>Markası, modeli, yaşı fark etmez. Parça artık üretilmiyor olsa bile elimizdeki örnekten ya da ölçüden yola çıkarız. <strong>Ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı (kırık parçaları bir arada) veya takıldığı cihazı kargoyla bize gönderin. Parça tamamen kaybolduysa, takılacağı yerin fotoğrafını ve kaba ölçülerini paylaşmanız yeterli.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçer, kırık uçları ve montaj noktalarını çıkarırız. Nereye, nasıl oturduğunu netleştirip size teyit ederiz.</li>
<li><strong>Üret</strong> — Onaydan sonra doğru malzemeyle üretip adresinize yollarız. Takın, cihaz çalışsın.</li>
</ol>
<h2>Doğru malzeme</h2>
<p>Her parça aynı plastikten üretilmez; nereye takılacağına göre seçeriz.</p>
<ul>
<li><strong>Standart / iç mekân parçaları</strong> (kumanda kapağı, düğme, iç klips): dengeli ve temiz malzeme yeterli.</li>
<li><strong>Isıya, neme, UV'ye maruz kalan yerler</strong> (dış gövde, havalandırma yakını, priz/adaptör muhafazası): PETG veya ASA gibi ısı ve dış koşula dayanıklı malzemeler.</li>
<li><strong>Yük taşıyan, sürekli takılıp çıkan, zorlanan parçalar</strong> (menteşe, taşıyıcı braket, gerilmeye çalışan klips): karbon veya cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet.</li>
</ul>
<p>Renk konusunda <strong>farklı renk seçenekleri</strong> sunuyoruz; parçayı cihazın rengine yakın üretmeye çalışırız. Aynı mantığı <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parçalarında</a> da uyguluyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parçalar <strong>yük dışı muhafaza, kapak, düğme ve montaj klipsleridir</strong> — cihazı bir arada tutan, örten, konumlandıran parçalar. Isı üreten güç elektroniğine (trafo, güç katı, ısınan adaptör içi) doğrudan temas eden bir parça söz konusuysa, kullanacağınız yeri bize söyleyin; orada malzemenin ısı sınırı vardır ve gerekiyorsa ısıya dayanıklı sınıfa yönlendirir, olmayacaksa açıkça söyleriz. Elektriksel yalıtım kritik bir noktaysa bunu baştan konuşuruz. Sözü olmayan işi almayız; parçanız çalışacağı yere göre doğru çözüme oturur.</p>
<p>Örnek parça elinizde yoksa <a href="/numuneye-gore-plastik-parca-uretimi/">numuneden üretim</a> yöntemiyle, hiç bulunamayan bir parça arıyorsanız <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça üretimi</a> sayfamızla ilerleyebilirsiniz. Kablo yönetimi için <a href="/olcuye-ozel-kablo-kanali-organizer-uretimi/">ölçüye özel kablo kanalı ve organizer</a>, uçan ve uzaktan kumandalı modeller için <a href="/drone-rc-model-plastik-parca-uretimi/">drone ve RC model parça üretimi</a> sayfalarına geçebilirsiniz. Malzeme seçimini derinlemesine görmek için <a href="/malzeme-rehberi/">malzeme rehberine</a> bakın.</p>
<h2>Sipariş</h2>
<p>Siparişi iki şekilde verebilirsiniz. Siteden <strong>kartla online ödeme</strong> yaparak doğrudan başlatabilir; ölçü danışmanlığı, özel iş ve parçanızın fotoğrafını göndermek için <strong>WhatsApp +90 545 138 6526</strong> hattından bize yazabilirsiniz. Kırık parçanın fotoğrafını atın, uyup uymayacağını birlikte netleştirelim, üretip yollayalım.</p>""")


def _motosiklet_plastik_parca_ozel_uretim():
    return (u"""<h1>Motosikletin Bulunamayan Plastik Parçasını Üretelim</h1>
<p class="lead">Grenajı çatlamış, klipsi kırılmış, ayna kapağı düşmüş — bayi "o parça artık gelmiyor" diyorsa, o parçayı ölçüsüne göre yeniden üretiyoruz.</p>
<p>Motosiklette en çok kaybolan şey pahalı bir mekanik parça değil; küçük ama olmazsa olmaz bir plastik detaydır. Grenaj klipsi kırılır, panel oynar, titreşim başlar. Ayna kapağı ya da muhafaza kaybolur, açıkta kalan yuva çirkin durur. Eski ya da az satan bir modelde bu parçaların muadili çoğu zaman hiçbir yerde bulunamaz; bulsanız bile komple grenaj takımı almaya zorlanırsınız. Tek ihtiyacınız olan o küçük parçadır.</p>
<p>Biz tam da bu noktada devreye giriyoruz. Elinizdeki kırık parçayı, sökülmüş yuvayı ya da ölçülerinizi bize iletirsiniz; biz o parçayı milimetrik olarak, motosikletinizin gerçek geometrisine uygun şekilde özel üretiriz. Piyasada karşılığı olmayan grenaj klipsi, panel tutucu, ayna kapağı ve muhafaza gibi parçalar için <strong>motosiklet plastik parça özel üretim</strong> yaklaşımımız, "yok" cevabına takılıp kalmanızı önler. Marka veya model fark etmez; parçanın kendisi elimize ölçüyle ulaştığı sürece üretilebilir.</p>
<p>Prensibimiz basit: <strong>Ölçü sizden, üretim bizden.</strong> Kırık grenaj klipsi yaptırma ya da bulunamayan motosiklet parçası üretimi ihtiyacınızı, tahmine değil gerçek ölçüye dayandırırız.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da sökülmüş parçayı, varsa eski parçanın fotoğraflarını ve takıldığı yeri bize iletin. Parça elinizde yoksa yuvanın ölçülerini paylaşın.</li>
<li><strong>Ölç</strong> — Deliği, klips mesafesini, kalınlığı ve montaj noktalarını netleştiririz; oturması gereken yere göre toleransı belirleriz.</li>
<li><strong>Üret</strong> — Parçayı ölçünüze göre üretir, kargoyla adresinize göndeririz. Takıp yerine oturttuğunuzda iş biter.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li>Kırık grenaj/panel klipslerinde <strong>klips genişliği, tırnak mesafesi ve dişi-erkek geçme toleransı</strong></li>
<li>Ayna kapağı ve muhafazalarda <strong>dış hat, derinlik ve montaj kulakçıklarının konumu</strong></li>
<li><strong>Delik çapı ve vida yuvası</strong> — mevcut cıvata/klips ölçünüze göre</li>
<li><strong>Kalınlık ve et payı</strong> — titreşimde çıtırdamayacak sıkılıkta oturma</li>
<li><strong>Farklı renk seçenekleri</strong> — mat siyah başta olmak üzere gövdeye yakın tonlar</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçeriz. İç tarafta, güneş ve ısı görmeyen tutucu/klips gibi parçalarda standart dayanıklı malzeme yeterlidir. Motorun yanına yakın, güneş altında kalan ya da yağmura/neme maruz kalan dış panel, ayna kapağı ve muhafazalarda <strong>ısı ve UV'ye dayanıklı ASA veya PETG</strong> kullanırız — açıkta sararmaz, kırılganlaşmaz. Yük binen, sürekli zorlanan montaj noktalarında ise <strong>karbon ya da cam fiber takviyeli (PA-CF / PA-GF)</strong> yüksek mukavemetli seçeneğe çıkarız.</p>
<p>Aynı mantık farklı araç plastiklerinde de geçerli; <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim ve klips parçalarında</a> da aynı ölçüye-özel yaklaşımı uyguluyoruz. Hangi malzemenin hangi koşula uygun olduğunu <a href="/malzeme-rehberi/">malzeme rehberimizde</a> görebilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parçalar yük taşımayan trim, kapak, klips ve muhafaza parçalarıdır; dış gövde estetiği ve montaj işlevi içindir. Motor, süspansiyon ya da taşıyıcı gövde gibi yapısal yük altındaki metal parçaların yerini almaz. Güneş ve ısı söz konusuysa doğru malzemeye (ASA/PETG) yönlendirir, beklentiyi baştan net koyarız. Bu netlik, taktığınız parçanın işini görmesi içindir.</p>
<p>Motosikletiniz için özel bir parça mı gerekiyor, model belirsiz mi? <a href="/bulunamayan-yedek-parca-ozel-uretim/">Bulunamayan yedek parça üretimi</a> ya da <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre üretim</a> sayfalarımız da yol gösterir. Aynı yaklaşımı diğer iki tekerlekli araçlarda da sürdürüyoruz; dış örtü, kapak ve panel parçaları için <a href="/elektrikli-scooter-plastik-parca-uretimi/">elektrikli scooter plastik parça üretimi</a> sayfamıza geçebilirsiniz.</p>
<h2>Sipariş</h2>
<p>Siteden kartla online ödemeyle sipariş verebilir, dilerseniz parçanızı ve ölçünüzü <strong>WhatsApp +90 545 138 6526</strong> hattından iletebilirsiniz. Kırık parçanın fotoğrafını gönderin; üretilebilirliğini ve seçenekleri birlikte netleştirelim. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_huni_uretimi():
    return (u"""<h1>Ölçüye Özel Huni Üretimi — Ağız ve Uç Ölçünüze Göre</h1>
<p class="lead">Standart huninin girmediği dar, eğik veya derin ağızlara; ağzın ve akıtma ucunun tam ölçüsüne göre huni üretiyoruz.</p>
<p>Piyasadaki hazır huniler tek beden mantığıyla satılır: uç çok kalın gelir, ağza oturmaz, dolum sırasında yarısı dışarı taşar. Dar bir depo ağzına, eğik bir dolum boğazına ya da özel bir hortum çapına denk gelen huniyi çoğu zaman rafta bulamazsınız. Biz de tam bu noktada devreye giriyoruz: parçanın gireceği ağzı ve akıtma ucunun oturacağı çapı ölçün, huniyi o ölçüye göre üretelim.</p>
<p>Mutfakta dar ağızlı şişeye dolum yapan, yağ ve yakıt aktarımında damlatmadan doldurmak isteyen, laboratuvarda belirli bir çapa yönlendirme yapan ya da sıkışık bir alanda açılı bir ağza ulaşmaya çalışan herkes için mantıklı. <strong>Plastik huni yaptırma</strong> ihtiyacınızı "yaklaşık uyar" değil, milimetrik ölçüyle karşılıyoruz.</p>
<p>İster elinizde örnek bir huni olsun ister sadece ağız ve uç ölçüleri; <strong>özel ölçü huni</strong> talebinizi ölçüden üretime taşıyoruz. Ölçüyü kargoyla ya da fotoğrafla iletin, üretip size gönderelim.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Elinizdeki örnek huniyi, dolum yaptığınız ağzın fotoğrafını ya da ölçülerini WhatsApp'tan iletin.</li>
<li><strong>Ölç</strong> — Ağız çapını, akıtma ucunun gireceği deliği/hortumu ve gereken koni yüksekliğini birlikte netleştirelim.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip kargoyla gönderelim. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Standart bir kalıp değil, sizin ölçünüze göre şu ayarları yapıyoruz:</p>
<ul>
<li><strong>Ağız çapı (mm)</strong> — geniş toplama ağzından dar boğaza, ihtiyacınıza göre</li>
<li><strong>Koni yüksekliği (mm)</strong> — sığ ve hızlı ya da uzun ve kontrollü akış</li>
<li><strong>Akıtma ucu iç çapı ve boyu (mm)</strong> — hangi ağza ya da hortuma gireceğine göre</li>
<li><strong>Açılı uç kesimi (0–60°)</strong> — dar ve eğik ağızlara rahat oturması için ucu düz ya da açılı kesiyoruz</li>
<li><strong>Glık-glık önleyici hava kanalı (anti-glug)</strong> — dolum sırasında hava kilidini ve fışkırmayı önler</li>
<li><strong>İç yönlendirici kanat</strong> — akışı ortalar, taşmayı azaltır</li>
<li><strong>Asma deliği</strong> — kancaya ya da çiviye asıp saklamak için</li>
<li><strong>Farklı renk seçenekleri</strong> — kullanım alanınıza uygun renklerle</li>
</ul>
<p><strong>Dar ağız dolum hunisi</strong> mi, <strong>yağ-yakıt dolum hunisi üretimi</strong> mi; hangisi olursa olsun ucu ve ağzı işin geometrisine göre biçimlendiriyoruz.</p>
<h2>Doğru malzeme</h2>
<p>Kullanım yerine göre doğru plastiği seçiyoruz. Standart iç-mekan kullanımı için sağlam ve temiz bir gövde; gıda teması, ısı, güneş ve nemin olduğu koşullarda ise <strong>PETG veya ASA</strong> merdivenine çıkıyoruz. Yüksek mukavemet gereken zorlu işlerde <strong>karbon veya cam fiber takviyeli (PA-CF / PA-GF)</strong> seçenekleri var. Hangi sıvı ve hangi ortam olduğunu söyleyin, malzemeyi ona göre yönlendirelim. Malzeme kararında yol göstermesi için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfamıza bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Huni hafif kullanım parçasıdır: sıvıyı yönlendirmek, dolum ve aktarma yapmak için idealdir. Ucu düz ya da 60°'ye kadar açılı kesebiliriz; ancak bükük veya eğri boyunlu (S kıvrımlı) huni üretmeyiz — gövde ve uç düz eksende çalışır. Aşındırıcı kimyasal ya da yüksek sıcaklıkta sürekli temas söz konusuysa önce malzemeyi netleştirir, sınırı açık söyleriz. Amacımız işe yarayan, ölçüsüne oturan bir parça.</p>
<p>Bir sınırı da baştan yazalım: gıda ve tıbbi sertifika gerektiren üretimler kapsamımız dışındadır, böyle bir belge vermeyiz. Ticari gıda üretiminde ürüne doğrudan temas eden, belgeli hat parçası istenen işleri almayız; ürüne temas etmeyen gövde, tutucu ve aparat işleri ise bize uygundur. Hunimiz kişisel ve atölye ölçeğinde dolum, aktarma ve yönlendirme işi içindir; sertifikaya bağlı bir kullanım söz konusuysa bunu üretimden önce söyleriz.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü ya da örnek parçanızı iletin, ölçüye özel üretip gönderelim. <a href="/">Siteden</a> kartla online ödeme yapabilir; ölçü danışması ve özel iş için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>.</p>
<p>Benzer ölçüye özel işler: <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> ve elinizdeki örnekten çoğaltma için <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a>.</p>""")


def _olcuye_ozel_izgara_petek_uretimi():
    return (u"""<h1>Ölçüye Özel Izgara, Menfez ve Petek Panel Üretimi</h1>
<p class="lead">Boşluğuna tam oturan menfezi, ızgarayı ya da petek paneli ölçüye özel üretiyoruz — piyasada hazır bedeni bulunmayan yeri milimetrik kapatırız.</p>
<p>Havalandırma menfezi kırılmış, dolap arkasındaki fan kapağı boşta kalmış, gider ızgarası ölçü tutmuyor ya da çekmece içine filtre paneli lazım — ve gittiğiniz her yerde "standart bu kadar, sizin ölçü yok" cevabı. Standart bir menfez sizin boşluğunuzu 3-5 mm açık bırakınca da iş görmez: ya toz kaçar, ya hava düzgün yönlenmez, ya da paneli zorla kesip bozarsınız.</p>
<p>Biz tam tersini yaparız: ölçü sizden, üretim bizden. Boşluğun enini, boyunu ve derinliğini siz verirsiniz; menfezi, ızgarayı ya da petek paneli o boşluğa oturacak şekilde üretiriz. Panjur açısından delik şekline, çerçeve formundan montaj tipine kadar her ayrıntı sizin yerinize göre belirlenir.</p>
<p>İster tekli bir kayıp parça olsun ister birkaç adet aynı panel — ölçüsünü alır, doğru malzemeden üretir, kargoyla adresinize yollarız.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Elinizdeki kırık menfezin/ızgaranın fotoğrafını ya da kapatmak istediğiniz boşluğu WhatsApp'tan iletin.</li>
<li><strong>Ölç</strong> — Boşluğun en × boy × derinliğini ve varsa montaj deliği aralığını birlikte netleştiririz.</li>
<li><strong>Üret</strong> — Onayınızın ardından ölçüye özel üretir, kargoyla göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Tip:</strong> panjur (hava yönlendirmeli, kanat açısı -45° / +45°), delikli desen ya da kör kapak</li>
<li><strong>En × boy × derinlik / kalınlık (mm):</strong> boşluğunuza tam oturacak ölçü</li>
<li><strong>Delik / göz şekli:</strong> petek, yuvarlak, kare, sekizgen, beşgen, üçgen</li>
<li><strong>Çerçeve / taban şekli:</strong> dikdörtgen, elips/yuvarlak, altıgen</li>
<li><strong>Montaj:</strong> geçme yuvası (insert) ya da vida deliği (M2–M10)</li>
<li><strong>Mod:</strong> delikli (perfore/filtre) ya da kabartma desen</li>
<li><strong>Farklı renk seçenekleri</strong></li>
</ul>
<p>Somut örnek: dolap havalandırması için altıgen çerçeveli, petek gözlü, geçmeli bir panel; ya da fan önüne yuvarlak kör kapak; ya da gider için kare gözlü, M4 vida delikli dikdörtgen ızgara — hepsi sizin ölçünüze göre.</p>
<h2>Doğru malzeme</h2>
<p>İç mekân, kuru ortamda kullanılacak bir menfez için standart malzeme yeter. Isı, nem, UV ya da dış hava alan yerlerde (mutfak, banyo, tekne, dış cephe menfezi) <strong>PETG ya da ASA</strong> gibi ısıya ve dış koşullara dayanıklı malzemeye geçeriz. Yüksek mukavemet, tokluk gereken panellerde ise <strong>karbon veya cam fiber takviyeli (PA-CF / PA-GF)</strong> malzeme kullanırız. Rengi de işinize göre seçersiniz — farklı renk seçenekleri mevcut.</p>
<p>Menfez sadece bir örnek: <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parçalarını</a> ve <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim klips parçalarını</a> da aynı mantıkla ölçüye özel üretiriz. Hangi malzemenin hangi işe gittiğini <a href="/malzeme-rehberi/">malzeme rehberinde</a> ayrıntılı anlattık.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz menfez, ızgara ve petek paneller hafif kullanım ve yük-dışı uygulamalar içindir: havalandırma, hava yönlendirme, toz/filtre tutma, gider ızgarası, dekoratif panel gibi. Üzerine çıkılacak, ağırlık taşıyacak ya da yapısal yük binecek bir ızgara ararsanız bu parçalar o iş için değildir. Nereye takacağınızı söyleyin, o kullanıma göre doğru malzemeye yönlendirelim.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü ve tipini netleştirelim: menfezinizi, ızgaranızı ya da petek panelinizi ölçüye özel üretip gönderelim. <a href="/">Siteden</a> kartla online ödeyebilir ya da WhatsApp'tan yazıp özel ölçü/üretim danışmanlığı alabilirsiniz: <strong>+90 545 138 6526</strong>.</p>
<p>Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_klips_kelepce_uretimi():
    return (u"""<h1>Ölçüye Özel Klips, Kelepçe ve Kablo Bağı Üretimi</h1>
<p class="lead">Piyasada tam çapını bulamadığınız klips, kelepçe ve kablo bağını ölçünüze özel üretiyoruz — siz ölçüyü verin, parça size göre çıksın.</p>
<p>Boruyu, hortumu, kabloyu ya da mili tutması gereken parça çoğu zaman "yaklaşık" gelir: 18 mm ararsınız, rafta 16 ile 20 vardır; biri boşta oynar, öteki geçmez. Kırılan orijinal kelepçenin muadili hiç yoktur ya da koca bir set almadan tek parça satılmaz. Sonuçta ya zorlayıp kırarsınız ya da bant, kablo bağı, tel gibi geçici çözümlerle idare edersiniz.</p>
<p>Bizim yaptığımız iş tam da bu boşluğu kapatmak. Tuttuğu parçanın gerçek çapını, kelepçenin genişliğini ve nasıl geçmesini istediğinizi alıp, o ölçüye birebir oturan klips veya kelepçeyi üretiriz. "Ölçü sizden, üretim bizden." Standart bir katalogdan seçmezsiniz; parça sizin milimetrenize göre biçimlenir.</p>
<p>Elinizde numune varsa daha da net: eski, kırık kelepçeyi kargoyla gönderin, ölçüsünü çıkarıp yenisini üretip yollayalım. Numune yoksa kumpasla aldığınız çap ve genişlik ölçüleri yeterli.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da yetersiz parçanızı gönderin veya bağlanacak boru/kablo/mil çapını ölçüp bize iletin.</li>
<li><strong>Ölç</strong> — Çapı, genişliği ve geçme biçimini netleştiririz; gerekiyorsa doğru tipi birlikte seçeriz.</li>
<li><strong>Üret</strong> — Ölçünüze özel klips/kelepçeyi üretir, adresinize kargolarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Bağlanacak boru / kablo / mil çapı (mm)</strong> — tutması gereken parçanın gerçek çapına göre üretim.</li>
<li><strong>Kelepçe tipi</strong> — açık (geçmeli), kapalı (tam sarma) ya da vidalı sıkma; kullanımınıza göre seçilir.</li>
<li><strong>Genişlik ve et kalınlığı</strong> — daha ince ve hafif mi, yoksa daha geniş ve dolgun mu olsun.</li>
<li><strong>Geçme sıkılığı</strong> — sıkı geçme (yerinden oynamasın) veya normal (kolay tak-çıkar).</li>
<li><strong>Montaj / vida deliği (isteğe bağlı)</strong> — yüzeye vidalanacaksa M ölçüsüne göre delik ekleriz.</li>
<li><strong>Farklı renk seçenekleri</strong> — görünür yerlerde ortama uyum için renk seçebilirsiniz.</li>
</ul>
<p>Aynı mantıkla üretilen yakın işler için <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim klips ve parça üretimi</a> ile <a href="/olcuye-ozel-baglanti-konektor/">ölçüye özel bağlantı ve konektör</a> sayfalarına da bakabilirsiniz. Boru ve hortum tutucusu sulama düzeninde çalışıyorsa <a href="/tarimsal-sulama-ekipmani-plastik-parca-yaptirma/">tarımsal sulama ekipmanı plastik parçası</a> sayfası su, güneş ve montaj koşulunu birlikte ele alır.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçeriz. İç mekan, kuru ve ılıman kullanımda standart malzeme yeterlidir. Motor bölmesi, güneş altı, dış cephe, nem ya da deniz koşulunda ısıya ve UV'ye dayanıklı <strong>PETG veya ASA</strong> öneririz. Havuz çevresindeki hortum bağlantı bileziği ve kapak klipsi gibi parçalarda ise klor teması da hesaba katılır; ayrıntısı <a href="/havuz-ekipmani-plastik-parca-yaptirma/">havuz çevresi plastik parçaları</a> sayfamızda. Zorlu, sürekli gerilim gören noktalarda ise cam/karbon fiber takviyeli <strong>PA-GF / PA-CF</strong> ile yüksek mukavemetli üretim yaparız. Hangi koşulda kullanacağınızı söyleyin, doğru malzemeye birlikte karar verelim. Detay için <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>
<h2>Dürüst sınır</h2>
<p>Açık olalım: klips ve kelepçeler <strong>yük taşıyan bağlantı değildir</strong>. İşleri tutmak, hizada sabitlemek, oynamayı önlemek — yani yük-dışı, düşük ila orta tutma kuvvetidir. Ağır çekme, asma ya da taşıyıcı bir bağlantı arıyorsanız bu doğru parça değildir; bunu baştan söyler, sizi zorlama altında çalışan uygun bir çözüme yönlendiririz. Amaç, elinize tam oturan ama beklentiyi de karşılayan bir parça çıkarmak.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödeyerek doğrudan sipariş verebilirsiniz. Ölçü danışmak, numune göndermek ya da özel bir iş konuşmak isterseniz WhatsApp hattımız açık: <strong>+90 545 138 6526</strong>. Çapınızı ve tipini iletin, ölçünüze özel klips/kelepçenizi üretip gönderelim.</p>""")


def _olcuye_ozel_kablo_kanali_organizer_uretimi():
    return (u"""<h1>Ölçüye Özel Kablo Kanalı, Yönlendirici ve Organizer Üretimi</h1>
<p class="lead">Standart kesitte bulamadığınız kablo kanalını ölçünüze göre üretiyoruz: kaç kablo geçecekse, nereye oturacaksa ona göre.</p>
<p>Masanın altında dağılan şarj kabloları, panoda birbirine giren besleme hatları, araç içinde sabitlenmeyen tesisat, atölyede ayakaltındaki uzatmalar... Piyasadaki hazır kablo kanalları hep bir "standart" kesitte gelir; sizin boşluğunuza ya çok büyük ya çok küçük olur, kanal sayısı tutmaz, montaj yeri uymaz. Aradığınızı bulamayınca ya idare edersiniz ya da olmayacak bir parçayı zorlarsınız.</p>
<p>Biz işi tersten kuruyoruz: ölçü sizden, üretim bizden. Kablo kanalını, yönlendiriciyi ya da masa/pano organizerini <strong>sizin boşluğunuza ve kablo sayınıza göre</strong> tasarlayıp üretiyoruz. Kaç göz istiyorsanız, hangi uzunlukta, kapaklı mı açık mı — hepsi size özel çıkıyor. Böylece kablolar oynamaz, kanal tam oturur, görüntü toplanır.</p>
<p>İster tek bir masa düzenleyici olsun, ister pano içine birkaç metre özel kanal — adet fark etmez. Ölçüyü siz verin, üretip kargoyla gönderelim.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Nereye takılacağını anlatın: masa altı, pano rayı, araç konsolu, atölye duvarı. Varsa mevcut parçanın fotoğrafını ya da boşluğun ölçüsünü iletin.</li>
<li><strong>Ölç</strong> — Uzunluk, genişlik, yükseklik ve kaç kablo geçeceğini birlikte netleştiririz. Giriş/çıkış ağzının nereye geleceğini belirleriz.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip kargoyla adresinize yollarız. Elinize takıp kullanacağınız hale gelmiş gelir.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Uzunluk × genişlik × yükseklik (mm)</strong> — boşluğunuza tam oturan kesit, ara ölçü dahil</li>
<li><strong>Kanal / göz sayısı</strong> — kaç kablo grubunu ayrı tutmak istiyorsanız ona göre bölmeli</li>
<li><strong>Kapaklı ya da açık</strong> — klipsli kapakla kabloları gizleyin, ya da hızlı erişim için açık bırakın</li>
<li><strong>Montaj biçimi</strong> — yapışkanlı, vidalı ya da geçmeli; yüzeyinize hangisi uyuyorsa</li>
<li><strong>Kablo giriş/çıkış ağzı ve çapı</strong> — kablonun gireceği-çıkacağı yer ve genişliği size göre</li>
<li><strong>Farklı renk seçenekleri</strong> — beyaz masaya, koyu panoya ya da araç içine uyum</li>
</ul>
<p>Belirsiz "her şeyi yaparız" değil; bunlar gerçekten ayarladığımız değerler. Ölçüyü söyleyin, ona göre çıksın.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi kullanım yerine göre seçeriz. İç mekan, masa üstü ve normal oda koşulu için standart dayanıklı malzeme yeterlidir. Araç içi, cam kenarı, dış hava ya da nemli ortam söz konusuysa ısıya ve UV'ye dayanıklı <strong>PETG ya da ASA</strong>'ya geçeriz — güneşte sararmaz, sıcakta yumuşamaz. Sürekli darbe alan ya da yük gören bir noktada tutuluyorsa <strong>karbon/cam fiber takviyeli PA-CF / PA-GF</strong> ile yüksek mukavemetli üretiriz. Renk için farklı seçenekler sunarız.</p>
<h2>Dürüst sınır</h2>
<p>Kablo kanalı ve organizer, kabloları düzenleyen <strong>hafif, yük-dışı</strong> bir parçadır. Kabloyu toplar, yönlendirir, yerinde tutar; ama üstüne çıkılacak, ağırlık taşıyacak ya da yapısal yük binecek bir eleman değildir. Klipsli kapak ve geçmeli montaj düşük–orta tutuş içindir. Ağır sabitleme ya da taşıyıcı gereken yerde bunu baştan söyler, doğru çözüme yönlendiririz. Ne işe yarayıp yaramadığını açık söylemek bizim için güvenin temeli.</p>
<p>Kablo yönetiminin yanında yük-dışı hafif profil ve beam gibi parçalar için <a href="/olcuye-ozel-profil-beam/">ölçüye özel profil ve beam üretimi</a> sayfasına, cihaz içi plastik parçalar için <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parça üretimi</a> sayfasına, malzeme seçimini derinlemesine görmek için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasına bakabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Kablo kanalınızı, yönlendiricinizi ya da organizerinizi ölçüye özel üretip gönderelim.</p>
<ul>
<li><strong><a href="/">Site üzerinden</a>:</strong> kartla online ödemeyle sipariş verin, üretip kargoyla yollayalım.</li>
<li><strong>WhatsApp:</strong> ölçü danışmak ya da özel iş için <strong>+90 545 138 6526</strong> — boşluğunuzu anlatın, birlikte netleştirelim.</li>
</ul>""")


def _olcuye_ozel_mentese_uretimi():
    return (u"""<h1>Ölçüye Özel Menteşe ve Reze Üretimi</h1>
<p class="lead">Kırılan menteşenizin ölçüsünü verin, birebir muadilini üretip kargoyla gönderelim.</p>
<p>Dolabın kapağı bir sabah elinizde kalır, kutunun kilit mekanizması oynar, eski bir cihazın menteşesi çatlar. Sonra başlar arayış: hırdavatçıda yok, aynı ölçü hiçbir yerde çıkmıyor, çıkan da ya bir milim büyük ya delikleri tutmuyor. Piyasada bulunamayan menteşe yüzünden koca bir kapağı, dolabı ya da cihazı çöpe atmak zorunda kalmak can sıkar. Oysa çözüm çoğu zaman tek bir küçük parçadır.</p>
<p>PRUVO tam burada devreye girer. <strong>Ölçüye özel menteşe üretimi</strong> işimizin merkezinde: kanat boyunuzu, delik aralığınızı ve pim çapınızı verirsiniz, biz o parçayı milimetrik olarak üretiriz. Standart kalıplara sıkışmadığımız için <strong>bulunamayan menteşe</strong> dediğiniz parça bizde ölçüye göre yeniden hayat bulur. İster tek bir dolap menteşesi olsun, ister eski bir sandığın özel kanatlı rezesi.</p>
<p><strong>Plastik menteşe yaptırma</strong> ihtiyacı olan herkes için akış aynı: mevcut parçayı ya da ölçülerini bize iletirsiniz, gerisini biz hallederiz. Kırık parçanın fotoğrafı ve birkaç ölçü çoğu zaman yeterlidir.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık menteşeyi ya da ölçülerini bize gönderin. Elinizdeki parçanın fotoğrafı ve delik düzeni işi büyük ölçüde çözer.</li>
<li><strong>Ölç</strong> — Kanat boyu, genişlik, pim çapı ve vida deliği aralığını netleştirir, size uygun malzemeyi öneririz.</li>
<li><strong>Üret</strong> — Onayınızdan sonra parçayı ölçünüze özel üretir, kargoyla adresinize yollarız. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p><strong>Özel ölçü menteşe</strong> demek, hazır rafta olmayan her detayı sizin parçanıza göre kurmak demek. Ayarladığımız gerçek seçenekler:</p>
<ul>
<li><strong>Kanat (yaprak) boyu × genişliği</strong> — kırık parçanın birebir ölçüsünde, milimetrik</li>
<li><strong>Pim/mil çapı</strong> — menteşenin döndüğü mil ölçüsüne göre</li>
<li><strong>Vida deliği sayısı ve aralığı</strong> — mevcut delik düzeninize oturacak şekilde</li>
<li><strong>Açılım açısı</strong> — 90°, 180° ya da kapağınızın gerektirdiği özel açı; açının sonunda kapağın duvara ya da gövdeye vurmasını engelleyen parçayı <a href="/plastik-stoper-durdurucu-yaptirma/">ölçüye özel durdurucu</a> olarak ayrıca üretiyoruz</li>
<li><strong>Kanat kalınlığı</strong> — hafiften daha sağlam gövdeye, kullanım yerine göre</li>
<li><strong>Farklı renk seçenekleri</strong> — mobilyanıza ya da cihazınıza yakın tonlarda</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Her menteşe aynı koşulda çalışmaz, malzemeyi ona göre seçeriz. İç mekân dolap ve kutu menteşelerinde standart dayanıklı malzeme yeterlidir. Nem, ısı ya da güneş gören yerlerde (mutfak, banyo, dış kapaklar) PETG veya ASA gibi ısı ve UV'ye dayanıklı malzemelere geçeriz. Sık açılıp kapanan, daha çok zorlanan menteşelerde ise karbon ve cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Aynı mantık <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> tarafında da geçerli; hangi malzemenin nereye gittiğini <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında açıkladık.</p>
<h2>Dürüst sınır</h2>
<p>Menteşe, doğası gereği yük taşıyan değil, hareket veren bir parçadır. Bizim ürettiğimiz menteşeler yük-dışı ve düşük–orta zorlanma için doğru çözümdür: dolap kapağı, kutu, çekmece, cihaz kapağı, hafif kanatlar. Ağır bir odun kapısını taşıyacak menteşeyi ya da yük taşıyan bir reze sistemini plastikten üretmeyiz; orası metalin işidir. Parçanızın çalışacağı yeri bize anlatın, uygun değilse baştan söyleriz. Sabit montaj ve bağlantı ihtiyacında ise <a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketi</a> tarafına bakabilirsiniz. Menteşeniz PVC pencere ya da kapı doğramasındaki bir kanada aitse, o sistemin mandal, kapak ve makara parçalarını <a href="/pvc-dograma-kapi-pencere-plastik-parca-uretimi/">PVC doğrama plastik yedek parça üretimi</a> sayfasında ayrıca anlattık.</p>
<h2>Sipariş</h2>
<p>Ölçülerinizi ilettikten sonra siparişinizi doğrudan <a href="/">sitemizden</a> kartla online verebilirsiniz. Emin olamadığınız bir ölçü, delik düzeni ya da malzeme varsa önce danışın: WhatsApp <strong>+90 545 138 6526</strong>. Kırık menteşenin fotoğrafını ve ölçülerini gönderin, birebir muadilini üretip yollayalım.</p>""")


def _olcuye_ozel_kulp_tutamak_uretimi():
    return (u"""<h1>Ölçüye Özel Kulp, Tutamak ve Kol Üretimi</h1>
<p class="lead">Delik arası tutmayan ya da modeli artık bulunamayan kulbu, ölçünüze göre üretip kargoyla gönderiyoruz.</p>
<p>Çekmecenin, dolabın ya da bir cihazın kulbu kırıldığında iş çoğu zaman tek bir parçada tıkanır: mağazadaki kulplar güzel ama vida delikleri arası mesafe sizinkiyle uyuşmaz, ya da o modelin üretimi çoktan kalkmıştır. Eski deliklere yeni delik açmak, mobilyayı sabitleyip durmak, "yaklaşık olsun" demek çözüm değil. Siz aynı delik aralığını, aynı formu ve doğru vida ölçüsünü istiyorsunuz.</p>
<p>Biz bu noktada devreye giriyoruz: <strong>ölçüye özel kulp üretimi</strong> ile parçayı sizin ölçülerinize göre tek tek çıkarıyoruz. Kırık kulbu ya da elinizdeki eş parçayı referans alıyor; delik arası mesafeyi, boyu ve formu birebir tutuyoruz. Özel tutamak yaptırma, çekmece kulpu üretimi, dolap kulpu ölçüye özel — hepsi aynı mantıkla çalışır: sizin ölçünüz, bizim üretimimiz.</p>
<p>Tek bir kulp da olur, bir mobilya takımının tüm kulpları da. Tekli kırık parça değişiminden, tüm çekmecelere aynı formda seri kol üretimine kadar aynı hassasiyetle ilerliyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık kulbu, eş bir örneği ya da net fotoğraf ve ölçüleri WhatsApp'tan paylaşın.</li>
<li><strong>Ölç</strong> — Vida delikleri arası mesafeyi, toplam boyu, vida ölçüsünü ve formu birlikte netleştiriyoruz.</li>
<li><strong>Üret</strong> — Parçayı ölçünüze göre üretip kargoyla adresinize gönderiyoruz.</li>
</ol>
<p><em>Ölçü sizden, üretim bizden.</em></p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Vida delikleri arası mesafe (mm):</strong> İki montaj deliği arasındaki mesafeyi birebir tutuyoruz; eski delikler aynen oturur.</li>
<li><strong>Form:</strong> Düz çubuk, kavisli, gömme (parmak boşluğu) ya da tekli düğme — kullanımınıza uygun biçim.</li>
<li><strong>Toplam boy ve tutuş kalınlığı:</strong> Elin rahat kavradığı uzunluk ve gövde kalınlığı.</li>
<li><strong>Vida ölçüsü ve deliği (M ölçüsü):</strong> Kullandığınız vidaya uygun delik çapı ve havşa; sık sökülüp takılan kollarda <a href="/plastik-parcaya-vida-disi-acilir-mi/">gömme somunlu diş çözümüne</a> geçeriz.</li>
<li><strong>Yüzey / kavrama profili:</strong> Düz, tırtıklı ya da hafif kavrama dokusu.</li>
<li><strong>Farklı renk seçenekleri:</strong> Mobilyanıza ya da cihazınıza yakın tonlarda üretim.</li>
</ul>
<p>Ölçüleri paylaşırken kararsız kaldığınız yeri boş bırakın; birlikte netleştiririz.</p>
<h2>Doğru malzeme</h2>
<p>İç mekân, günlük kullanım kulpları için standart malzeme yeterli ve temiz bir sonuç verir. Mutfak, ıslak alan ya da güneş gören yüzeylerde ısı, nem ve UV'ye dayanıklı <strong>PETG veya ASA</strong> öneriyoruz. Sık ve sert çekilen, yüke daha çok maruz kalan kollarda ise <strong>karbon/cam elyaf takviyeli (PA-CF / PA-GF)</strong> yüksek mukavemetli malzemeye geçiyoruz. Parçanızın çalışacağı yere göre doğru malzemeye sizi yönlendiriyoruz. Aynı mantığın malzeme tarafını <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında ayrıntılı anlattık.</p>
<h2>Dürüst sınır</h2>
<p>Kulp ve tutamaklar <strong>hafif kullanım ve günlük tutuş</strong> için tasarlanır: çekmece açmak, dolap kapağını çekmek, cihazı taşımak. Ağır yük asma, tüm ağırlığın tek kulba bindiği taşıma ya da darbeli zorlama için uygun değildir. Kullanımınızı baştan konuşur, doğru malzemeyle en dayanıklı sonucu birlikte hedefleriz. Beyaz eşya ve cihaz parçalarında benzer değişimler için <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> sayfasına, kırılan diğer plastik parçalar için <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> sayfasına bakabilirsiniz.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödemeyle sipariş verebilir, ölçü ve form danışmanlığı için WhatsApp hattımızdan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Kırık kulbun fotoğrafını ve delik arası ölçüsünü gönderin; formu netleştirip üretime alalım. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_tapa_kapak_uretimi():
    return (u"""<h1>Ölçüye Özel Tapa, Kapak ve Tıkaç Üretimi</h1>
<p class="lead">Kırılan, kaybolan ya da piyasada hiç bulunmayan tapayı ölçüsüne göre üretiyoruz — ölçü sizden, üretim bizden.</p>
<p>Bir profilin, borunun ya da hazne ağzının tapası zamanla kırılır, kaybolur veya hiç birlikte gelmez. Yedeğini aramaya çıktığınızda ise standart ölçüler tutmaz: çap birkaç milim oynar, geçme ya çok gevşek ya hiç girmez. Nalburda, sanayide, internette dolaşıp "yaklaşık" bir şey bulmak yerine, tam oturan bir parça istersiniz. Biz de tam bunu yapıyoruz.</p>
<p>Kare profil ağzını kapatan bir tıkaç, alüminyum borunun uç kapağı, makine haznesinin diş kapağı, mobilya ayağının tabanı ya da elektronik kutusunun deliğini kapatan bir tapa — hepsi ölçüye özel üretilebilir. Elinizdeki delik ya da ağız ne ise, iç veya dış çapını, geçme tipini ve sıkılığını söylersiniz; parçayı ona göre çıkarırız.</p>
<p>En sık gelen ihtiyaç şu: elde tek bir sağlam örnek var ama eşi yok. O örneği referans alıp aynısını, isterseniz farklı renkte çoğaltabiliriz. Örnek yoksa da sorun değil; ağzın iç/dış çapını ve derinliğini ölçüp bize iletmeniz yeterli.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir / ilet</strong> — Kırık tapayı, kapağı ya da kapatılacak ağzı bize gösterin. Ulaşamıyorsanız kargoyla gönderin; uzaktaysanız birkaç net fotoğraf ve ölçü de yeter.</li>
<li><strong>Ölç</strong> — İç ya da dış çapı, derinliği ve geçme sıkılığını netleştiririz. Kritik yüzeyleri birlikte konuşuruz.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip size ulaştırırız. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Standart bir tapayı değil, sizin ağzınıza özel bir parçayı çıkarıyoruz. Somut olarak ayarlanan noktalar:</p>
<ul>
<li><strong>İç ya da dış çap (mm)</strong> — deliğin içine mi girecek, ağzın üstüne mi geçecek, ona göre ölçüye özel</li>
<li><strong>Geçme tipi</strong> — içten geçme, dıştan geçme ya da vidalı (dişli) kapak</li>
<li><strong>Geçme sıkılığı</strong> — sıkı (zor çıkan, kalıcı) ya da normal (elle takıp çıkarılabilen)</li>
<li><strong>Kesit</strong> — yuvarlak, kare, dikdörtgen ya da profil ağzına özel form</li>
<li><strong>Sap / tutma çıkıntısı</strong> — isteğe bağlı, elle kolay çekip çıkarmak için</li>
<li><strong>Farklı renk seçenekleri</strong> — göze uygun, ayırt edici ton seçimi</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Parçanın çalışacağı yere göre malzeme seçiyoruz. İç mekân, kuru ortam ve hafif kullanım için standart, dayanıklı bir malzeme yeterli. Güneş, ısı, nem, deniz koşulu ya da dışarıda kalacak bir tapa söz konusuysa UV ve ısıya dayanıklı PETG veya ASA'ya çıkıyoruz. Sürekli darbe alan, zorlanan ya da yük taşıyan bir uygulamada karbon/cam fiber takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlıyoruz. Hangi malzemenin sizin işinize oturduğunu birlikte netleştirmek için <a href="/malzeme-rehberi/">malzeme rehberine</a> göz atabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Tapa, kapak ve tıkaç bizim için <strong>hafif kullanım</strong> işidir: kapatma, koruma, toz-nem tutma, örtme amaçlıdır. Basınçlı sızdırmazlık, contalama ya da yüksek basınç altında tam kapatma gerektiren yerlerde tapa doğru çözüm değildir — bunun için <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> sayfasına bakın. Ne olacağını olduğundan büyük göstermeyiz; parçayı çalışacağı yere göre doğru malzemeye yönlendiririz.</p>
<p>Bulunamayan başka bir yedek parça mı arıyorsunuz? <a href="/bulunamayan-yedek-parca-ozel-uretim/">Bulunamayan yedek parça özel üretim</a> sayfası tam bu iş için.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü netleştirip üretime alalım. Elinizdeki örneği ya da ağzın ölçülerini iletin; siz onaylayın, biz üretip gönderelim. <a href="/">Siteden</a> kartla online ödeme ile sipariş verebilir, özel iş ve ölçü danışması için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Ölçü sizden, üretim bizden.</p>""")


def _tarim_makinesi_plastik_parca_uretimi():
    return (u"""<h1>Tarım ve Bahçe Makinesi Plastik Parçalarının Özel Üretimi</h1>
<p class="lead">Modeli kalkmış tarım aletinizin kırılan plastik parçasını, elinizdeki örneğe göre ölçüye özel üretiyoruz.</p>
<p>Çapa makinesi, mibzer, pülverizatör, biçme makinesi, sırt atomizörü ya da bahçe traktörü... Bu makinelerin yıllar önce üretilmiş modellerinde bir plastik parça kırıldığında çoğu zaman yedeği artık hiçbir yerde bulunmuyor. Arıza makine gövdesinde değil, sulama düzenindeki basınç taşımayan kelepçe, vana kolu, filtre kapağı tutucusu veya hortum kılavuzundaysa <a href="/tarimsal-sulama-ekipmani-plastik-parca-yaptirma/">tarımsal sulama ekipmanı plastik parçası</a> sayfasına geçebilirsiniz. Bayi "o model bitti" diyor, sanayide örneği yok, makine tek bir kapak, dişli göbeği ya da bağlantı klipsi yüzünden atıl kalıyor. Oysa parçanın kendisi elinizde — kırık haliyle bile ölçü alınabilir durumda. Çim biçme makinesinin tekerlek göbeği, yükseklik ayar kolu ya da misina kafası tutucusu kırıldıysa <a href="/cim-bicme-bahce-makinesi-plastik-parca-yaptirma/">çim biçme ve bahçe makinesi plastik parça yaptırma</a> sayfasında bu parçaların ölçülerini tek tek açıyoruz. Ahırdaki sağım ünitesinden, suluk ya da yemlik düzeneğinden bir parça kırıldıysa <a href="/sut-sagim-hayvancilik-ekipmani-plastik-parca-uretimi/">süt sağım ve hayvancılık ekipmanı plastik parça üretimi</a> sayfası o kalemlere ayrıldı.</p>
<p>İşte tam da bunun için varız. Bize kırık parçanın kendisini ya da net ölçülerini/fotoğrafını gönderin; biz onu birebir çıkarıp, çalıştığı koşula uygun malzemeyle yeniden üretelim. <a href="/bulunamayan-yedek-parca-ozel-uretim/">Bulunamayan yedek parçalarda</a> yaptığımız iş budur: piyasada olmayanı sizin örneğinizden geri getiriyoruz.</p>
<p>Tarım ve bahçe makineleri güneş, UV, nem, toz ve titreşim altında çalışır. Bu yüzden "bir plastik bulalım takalım" mantığıyla değil, parçanın maruz kaldığı dış koşula göre doğru malzemeyi seçerek üretiyoruz. Kaporta altındaki bir bağlantıdan, sürekli güneş gören bir kapağa kadar her parçanın gereği farklıdır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eskiyen parçayı, varsa sağlam bir eşini, kargoyla bize gönderin. Parça bulunamıyorsa net fotoğraf ve ölçüler de yeterli.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik çıkarır, kırık/aşınmış yerleri tamamlar, montaj deliklerini ve oturma noktalarını orijinaline göre doğrularız.</li>
<li><strong>Üret</strong> — Onayınızın ardından ölçüye özel üretip adresinize yollarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Birebir ölçü</strong> — Delik çapları, vida/cıvata yuvaları, kanal ve tırnak mesafeleri elinizdeki parçaya göre.</li>
<li><strong>Malzeme sınıfı</strong> — Kullanım yerine göre iç mekân plastiğinden dış koşula dayanıklı sınıfa kadar seçim.</li>
<li><strong>Duvar/et kalınlığı</strong> — Aynı parçayı ihtiyaca göre daha sağlam ya da orijinaliyle aynı ölçüde.</li>
<li><strong>Farklı renk seçenekleri</strong> — Makinenin rengine yakın ya da ayırt edici bir tonda.</li>
<li><strong>Adet</strong> — Tek parça ya da atölyeniz/deponuz için küçük seri.</li>
</ul>
<p>Standart bir <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretiminde</a> olduğu gibi, döner aktarım gerektiren yerlerde <a href="/olcuye-ozel-plastik-disli-uretimi/">plastik dişli üretimi</a> de yapıyoruz.</p>
<h2>Doğru malzeme</h2>
<p>Malzeme, parçanın nerede çalıştığına göre yükselen bir merdivendir. İç mekânda ya da yükten uzak yerlerde PETG dengeli ve dayanıklı bir tercihtir. Sürekli güneş, UV, nem ve dış hava gören parçalarda ASA öne çıkar — solmaya ve ısıya direnir. Yük ve tork taşıyan, zorlanan parçalarda ise karbon/cam elyaf takviyeli PA-CF / PA-GF ile yüksek mukavemet sağlarız. Hangisinin uygun olduğunu parçanızın çalıştığı yere göre biz öneririz. Ayrıntı için <a href="/malzeme-rehberi/">malzeme rehberine</a> bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Her parçayı doğru yere yönlendiririz. Kulp, kapak, huni, tapa gibi parçalar hafif kullanım içindir. Klips, kelepçe, menteşe gibi bağlantılar yük-dışı ya da düşük–orta zorlanma için uygundur; kasnak türü aktarımlar düşük–orta yük ve torkta iş görür, ağır tahrik hattının metal parçasının yerini tutmaz. Dişli ve genel parçalarda dayanım, çalışacağı yüke göre değişir. Metal zorunlu ağır tahrik parçasını plastikle değiştirmeyiz — parçanızı en doğru çözüme yönlendirmek işimizin bir parçası.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Siparişinizi <a href="/">siteden</a> kartla online ödemeyle verebilir, kırık parçanızı ölçtürmek ve doğru malzemeyi konuşmak için WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına yazabilirsiniz. Parçayı gönderin, ölçelim, üretip yollayalım.</p>""")


def _mobilya_plastik_baglanti_ayak_parca_uretimi():
    return (u"""<h1>Mobilya Plastik Bağlantı, Ayak ve Kayar Pabuç Üretimi</h1>
<p class="lead">Kutudan çıkan o küçük plastik parça kırıldı ve hiçbir yerde bulamıyorsanız, numunesini bize gönderin; birebir aynısını ölçüye özel üretip yollayalım.</p>
<p>Dolabın, gardırobun, koltuğun ya da masanın montaj kutusunda gelen o minik plastik bağlantı elemanları çoğu zaman ayrı satılmaz. Bir tanesi kırıldığında ya da kaybolduğunda, koca mobilya sırf o parça yüzünden sallanır, kapak kapanmaz, ayak dengesini kaybeder. Sorun eğimli zemini veya farklı ayak yüksekliğini dengelemekse <a href="/olcuye-ozel-seviye-simi-ve-takoz-uretimi/">ölçüye özel seviye şimi ve takoz</a> çözümü gereken en, boy ve yüksekliğe göre hazırlanır. Marka bu parçaları perakende vermez; benzeri diye alınan muadil de ölçü tutmaz.</p>
<p>Biz tam bu noktada devreye giriyoruz. Elinizdeki kırık parçayı ya da sağlam bir eşini numune olarak alıp, mobilya plastik bağlantı parçası üretimi işini birebir kopya mantığıyla yapıyoruz. Dolap bağlantı parçası özel geometrisiyle, mobilya ayağı yaptırma talebiniz gerçek ölçüsüyle, kayar pabuç üretimi ise yüzeyde sessiz kaymayı sağlayacak formuyla çıkar. Tek adet yeter; bir sürü sipariş etmek zorunda değilsiniz.</p>
<p>Bulunamayan mobilya plastik parça derdinin çözümü, parçayı sıfırdan aramak değil; var olanı ölçüye özel yeniden üretmek. Kapak her açılışta duvara vuruyor ya da çekmece dayanacağı yeri bulamıyorsa aranan parça bir durdurucudur ve <a href="/plastik-stoper-durdurucu-yaptirma/">plastik stoper yaptırma</a> tam bu ölçüyle çalışır. Kanca, geçme dili, tırnak, kayar taban, ayak altlığı, gizli bağlantı pimi... hangisiyse, o parçanın oturması gereken yere tam oturmasını sağlıyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da sağlam parçanın fotoğrafını ve mümkünse birkaç ölçüsünü WhatsApp'tan gönderin; parçayı kargoyla numune olarak da yollayabilirsiniz.</li>
<li><strong>Ölç</strong> — Numuneyi milimetrik ölçüp geometrisini birebir çıkarıyoruz; delik aralığı, geçme payı, kalınlık ve tırnak formu dahil.</li>
<li><strong>Üret</strong> — Ölçüye özel üretip adresinize gönderiyoruz. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li>Numuneden birebir kopya: delik aralığı, geçme dili, tırnak ve kanca formu aynen</li>
<li>Tek adet ya da az sayıda üretim — stok/toptan zorunluluğu yok</li>
<li>Ayak yüksekliği, taban çapı ve oturma açısı sizin mobilyanıza göre</li>
<li>Kayar pabuçta yüzeye uygun kayma tabanı ve sessiz temas formu</li>
<li>Farklı renk seçenekleri (mobilyanızla uyumlu tona yakın)</li>
</ul>
<h2>Doğru malzeme</h2>
<p>İç mekân mobilya parçalarının çoğu için standart, sağlam bir malzeme yeterli olur. Neme, ısıya ya da güneş gören bir yüzeye maruz kalan parçalarda PETG veya ASA gibi dayanıklı malzemelere geçiyoruz. Sürekli yük altında çalışan, gerilen ya da darbe alan bağlantılarda ise cam/karbon fiber takviyeli PA-GF / PA-CF ile yüksek mukavemetli üretim yapıyoruz. Parçanın nerede çalışacağını söyleyin, doğru malzemeye biz yönlendirelim. Malzeme seçimini derinlemesine görmek isterseniz <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfamıza bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Açık konuşalım: bu parçalar bağlantı, konumlandırma ve hafif taşıma içindir. Klips, geçme ve menteşe benzeri elemanlar yük-dışı ya da düşük–orta yük içindir; ayak ve altlıklar mobilyanın kendi ağırlığını dengeler, ağır darbe ya da taşıyıcı iskelet görevi görmez. Dolabın tüm yükünü tek bir plastik ayağa bindiren bir kullanım için değil, orijinal parçanın yaptığı işi aynen görmesi için üretiriz. Neyin sınırda olduğunu baştan söyleriz. Kırılan parça bağlantı ya da ayak değil de çekmecenin, sepetin veya sürgülü kapağın yuvarlanan kısmıysa, <a href="/olcuye-ozel-tekerlek-makara-uretimi/">ölçüye özel tekerlek ve makara üretimi</a> sayfamız tam bu iş içindir.</p>
<h2>Sipariş</h2>
<p>Numunenizin fotoğrafını ve ölçülerini WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; birlikte netleştirip fiyat verelim. Onay sonrası <a href="/">siteden</a> kartla online ödemeyle siparişinizi tamamlayabilirsiniz.</p>
<p>İlgili olabilecek diğer hizmetlerimiz: <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a>, <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> ve <a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketi</a>.</p>""")


def _drone_rc_model_plastik_parca_uretimi():
    return (u"""<h1>Drone ve RC Model İçin Ölçüye Özel Plastik Parça Üretimi</h1>
<p class="lead">Kırılan drone kolunu, RC modelin gövde kapağını ya da iniş takımını bulamıyorsanız; parçayı bize gönderin, ölçüye özel yeniden üretelim.</p>
<p>Drone ve RC model kullananlar aynı sorunu yaşar: bir kaza olur, motor kolu çatlar ya da montaj braketi kırılır; üretici o parçayı artık satmıyordur veya modeliniz zaten piyasadan kalkmıştır. Tek bir küçük plastik parça yüzünden koca bir cihaz rafta bekler. Biz tam da bu noktada devreye giriyoruz: elinizdeki kırık parçadan ya da ölçülerinden yola çıkarak aynısını, çoğu zaman daha dayanıklı malzemeyle üretiyoruz.</p>
<p>Drone gövde kolu, motor yuvası, iniş takımı ayağı, kamera/gimbal braketi, pil kapağı, gövde plakası, RC araç süspansiyon kolu, tampon ve şasi bağlantı parçaları gibi yapısal ve montaj parçalarını ölçünüze göre üretiyoruz. Elimizde parçanın kendisi varsa birebir çıkarırız; yoksa fotoğraf, teknik çizim ya da ölçülerinizle çalışırız.</p>
<p>Hobi kullanıcısı için en kritik denge hafiflik ve mukavemettir. Uçan bir modelde her gram önemlidir ama parça da darbeye dayanmalıdır; aynı kol her düşüşte yeniden kırılıyorsa <a href="/darbeye-dayanikli-plastik-parca-yaptirma/">darbeye dayanıklı parça üretimi</a> sayfasındaki kesit ve sınıf düzeltmelerini uygularız. Bu yüzden drone ve RC model parçalarında çoğunlukla karbon fiber takviyeli malzemeye (PA-CF) yöneliriz: hafif kalır, bükülmez, kazada seri parçadan daha iyi dayanır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı kargoyla gönderin ya da ölçü/fotoğraf/çizimi WhatsApp'tan iletin.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçer, bağlantı deliklerini ve montaj noktalarını birebir çıkarırız.</li>
<li><strong>Üret</strong> — Doğru malzemeyle üretip adresinize göndeririz. Ölçü sizden, üretim bizden.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Parça tipi:</strong> gövde kolu, motor yuvası, iniş takımı, gimbal/kamera braketi, pil kapağı, gövde plakası, RC şasi ve süspansiyon bağlantıları</li>
<li><strong>Ölçü:</strong> kol uzunluğu, delik aks aralığı, vida/cıvata çapı, montaj deseni birebir sizin modelinize göre</li>
<li><strong>Malzeme sınıfı:</strong> iç mekan/standart, ısı-UV dayanımı, yüksek mukavemet (aşağıda detay)</li>
<li><strong>Renk:</strong> farklı renk seçenekleri (aynı modelin sağ/sol kolunu ayırmak için renk kodlaması dahil)</li>
<li><strong>Adet:</strong> tek yedek ya da kaza ihtimaline karşı birkaç kolluk set</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Standart iç mekan parçalarında PETG ile başlarız. Dışarıda, güneş ve nem altında uçan modeller için ısı ve UV'ye dayanıklı ASA öneririz. Uçuş yükü taşıyan gövde kolu, motor yuvası, iniş takımı gibi parçalarda ise karbon/cam fiber takviyeli malzemeye (PA-CF / PA-GF) geçeriz: en yüksek mukavemet, en düşük ağırlık. Hangi parçanın nereye takılacağını sorar, ona göre yönlendiririz.</p>
<h2>Dürüst sınır</h2>
<p>Açık olalım: itiş pervanesi ve yüksek devirli uçuş pervanesi ÜRETMİYORUZ. Bunlar hassas balans ve yüksek devir dayanımı ister; plastik üretim burada güvenli değildir ve sizi yanıltmayız. Bizim işimiz yapısal ve montaj parçaları: kol, braket, kapak, iniş takımı, şasi bağlantıları. Braket ve klips tipi bağlantı parçaları yük dışı/düşük-orta zorlama içindir; gövde kolu ve iniş takımını ise kazada tekrar tekrar dayanacak takviyeli malzemeyle veririz. Parçayı çalışacağı yere göre doğru malzemeye yönlendirir, taşıyamayacağı yükü taşır demeyiz.</p>
<p>İlgili sayfalar: <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a>, <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parça üretimi</a>, <a href="/olcuye-ozel-baglanti-konektor/">ölçüye özel bağlantı ve konektör</a> ve <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödemeyle sipariş verebilir, ölçüye özel işiniz için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Kırık parçanızı gönderin ya da ölçülerinizi iletin; drone ve RC modelinizi tekrar uçuşa hazır hale getirelim. Ölçü sizden, üretim bizden.</p>""")


def _ev_aleti_plastik_disli_parca_uretimi():
    return (u"""<h1>Mutfak Robotu ve Ev Aleti Plastik Dişli/Parça Üretimi</h1>
<p class="lead">Blenderiniz dönmüyor, kıyma makinesinden ses gelip iş görmüyor ya da mikser boşta kalıyorsa suçlu çoğu zaman içerideki küçük plastik dişlidir. İyi haber: cihazı çöpe atmanıza gerek yok, o parçayı ölçünüze göre yeniden üretebiliriz.</p>
<p>Ev aleti plastik dişli üretimi, yedek parçası artık bulunmayan cihazlar için en kestirme çözümdür. Marka servisi "parça yok" dediğinde ya da model eskidiğinde, elinizdeki kırık dişliyi örnek alıp aynı diş sayısı, aynı çap ve aynı mil yatağıyla yeniden yapıyoruz. Mutfak robotu dişli yaptırma, blender dişli üretimi, kıyma makinesi plastik parça veya mikser yedek parça özel talepleri bizim için tipik iştir.</p>
<p>Aradığınız parçayı bulamadıysanız genel <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretimi</a> sayfamıza da bakabilirsiniz; sadece dişli değil, kırılan her küçük plastik parçayı aynı yöntemle ele alıyoruz. Dişlinin kendisine odaklanmak isterseniz <a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişli üretimi</a> sayfamız üst başvuru noktanızdır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir:</strong> Kırık dişliyi veya parçayı kargoyla bize gönderin. Elinizde parça kalmadıysa cihaz marka-modelini ve varsa parça numarasını iletin; numara hiçbir yerde okunmuyorsa <a href="/yedek-parca-kodu-bilinmiyorsa-ne-yapilir/">yedek parça kodu bilinmiyorsa ne yapılır</a> sayfası kodsuz ilerlemenin adımlarını veriyor.</li>
<li><strong>Ölç:</strong> Diş sayısını, dış çapı, mil deliğini ve kanal/kama detaylarını milimetrik ölçeriz. Ölçü sizde değilse örnekten biz çıkarırız; diş büyüklüğünü kendiniz hesaplamak isterseniz <a href="/kirik-dislinin-modulu-nasil-bulunur/">kırık dişlinin modülü nasıl bulunur</a> sayfası adım adım gösteriyor.</li>
<li><strong>Üret:</strong> Ölçüye özel üretip test eder, kargoyla adresinize yollarız. Türkiye'nin her yerine gönderiyoruz.</li>
</ol>
<h2>Ölçünüze göre çıkardığımız detaylar</h2>
<ul>
<li>Diş sayısı, modül ve diş profili (parçaya birebir uyacak şekilde)</li>
<li>Dış çap, iç çap ve toplam yükseklik</li>
<li>Mil deliği çapı, kama/kanal veya D-tipi düzleştirme</li>
<li>Bağlantı tırnakları, kertikler ve oturma yüzeyleri</li>
<li>Malzeme ve farklı renk seçenekleri</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Standart iç mekan parçalarında sağlam ve tok malzemelerle (PETG ve ASA) çalışırız; ısı, nem ve sürekli kullanım bunlarda sorun çıkarmaz. Sürtünen ve aşınan dişlilerde ise yüksek mukavemetli, karbon veya cam fiber takviyeli malzeme (PA-CF / PA-GF) öneririz — bu grup aşınma dayanımı ve boyutsal kararlılıkta belirgin fark yaratır. Cihazınızın çalışma koşuluna göre doğru malzemeye yönlendiririz. Malzemelerin nerede ne işe yaradığını <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasından ayrıntılı görebilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Plastik dişli ve parçalarda dayanım, çalıştığı yüke göre değişir; dürüst konuşmak güven verir. Mutfak robotu, blender, mikser ve kıyma makinesi gibi ev aletlerindeki dişliler genelde düşük–orta tork aralığında çalışır ve bu iş için uygundur. Ağır sanayi tahriki, yüksek tork ya da metalin taşıması gereken sürekli yük söz konusuysa parça plastikle kalıcı çözüm olmaz; böyle bir durumda size baştan söyler, doğru yönlendirmeyi yaparız. Aynı yaklaşımı geniş <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> tarafında da uyguluyoruz.</p>
<h2>Sipariş</h2>
<p><a href="/">Siteden</a> kartla online ödemeyle sipariş verebilir ya da parçanızı anlatmak, ölçü danışmak için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Kırık dişlinizin fotoğrafını gönderin, uygunluğunu ve seçenekleri birlikte netleştirelim. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_cetvel_mastar_sablon_uretimi():
    return (u"""<h1>Ölçüye Özel Cetvel, Gönye ve Mastar Üretimi</h1>
<p>Standart cetvel her işe uymaz. Tezgahınıza sığmayan boy, çalıştığınız özel taksimat, üzerinde firma adınızın olması ya da elinizdeki referans ölçüyü tekrar tekrar işaretlemek için bir mastar gerektiğinde piyasada hazır ürün bulamazsınız. PRUVO'da cetvelinizi, gönyenizi ve ölçü mastarınızı <strong>istediğiniz boya ve işarete göre üretiyoruz.</strong> Ölçü sizden, üretim bizden.</p>
<p>Marangozdan tornacıya, terziden atölye ustasına kadar herkesin tekrar eden bir ölçüsü vardır: hep aynı 37 cm, hep aynı 22,5 derece, hep aynı delik aralığı. Bunu her seferinde metreyle ölçüp işaretlemek zaman kaybı ve hata kaynağıdır. <strong>Ölçüye özel cetvel üretimi</strong> tam burada devreye girer — sık kullandığınız ölçüyü tek bir alete gömeriz, siz sadece dayayıp işaretlersiniz.</p>
<p>Aynı şekilde <strong>ölçüye özel gönye yaptırma</strong> talebi çoğu zaman standart 90 derecelik gönyenin ötesindedir: üçgen gönye, marangoz L-gönyesi ya da sizin işinize özel bir açı. Kırılan, ölçüsü kaymış ya da hiç bulamadığınız gönyeyi yenisiyle, sizin ölçünüzde üretiriz. <strong>Ölçü mastarı üretimi</strong> ise seri işlerde referansı sabitler: bir kere doğru mastarı çıkarırız, üretimin geri kalanı ona göre akar.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Elinizdeki cetveli, gönyeyi veya çıkarmak istediğiniz ölçüyü bize iletin. Kırık bir parça, bir fotoğraf ya da yazılı ölçü yeterli.</li>
<li><strong>Ölç</strong> — İstediğiniz boyu, taksimatı, açıyı ve üzerine geçecek yazı/logoyu netleştiririz. Kararsız kaldığınız yerde biz yönlendiririz.</li>
<li><strong>Üret</strong> — Ölçüye özel üretir, kontrol eder, size ulaştırırız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her cetvel/gönye siparişini şu seçeneklere göre size özel hazırlıyoruz:</p>
<ul>
<li><strong>Tip:</strong> düz cetvel · üçgen gönye · L (marangoz) gönyesi</li>
<li><strong>Ölçü sistemi:</strong> metrik (cm/mm) ya da inç</li>
<li><strong>Uzunluk:</strong> istediğiniz boy — tezgahınıza ya da işinize göre</li>
<li><strong>İşaret stili:</strong> kabartma · oyma · gömme çizgiler</li>
<li><strong>Tek yüz ya da çift yüz taksimat</strong></li>
<li><strong>Üzerine isim, firma yazısı ya da logo işleme</strong> — logolu cetvel üretimi</li>
<li><strong>Anahtarlık halkası</strong> ya da <strong>asma/depolama deliği</strong></li>
<li><strong>Farklı renk seçenekleri</strong></li>
</ul>
<p>Ne istediğinizi tam bilmiyorsanız sorun değil; kullanım yerini anlatın, doğru taksimat ve boyu birlikte belirleriz.</p>
<h2>Doğru malzeme</h2>
<p>İşin yerine göre malzemeyi seçeriz. Günlük ofis ve atölye kullanımı için sağlam standart malzeme yeter. Sıcağa, güneşe ve neme maruz kalan (dışarıda, tezgah başında, güneş gören) kullanım için ısı ve UV dayanımı yüksek PETG ya da ASA'ya çıkarız. Sürekli darbe alan, sürtünen, ağır atölye şartında çalışan aletler için karbon ya da cam elyaf takviyeli (PA-CF / PA-GF) yüksek mukavemetli malzemeyi öneririz. Cetvelinizin çalışacağı yere göre sizi doğru malzemeye yönlendiririz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz cetvel, gönye ve mastar <strong>günlük atölye ve ofis ölçüsü</strong> içindir — işaretleme, dayama, referans ve seri işte tekrarlanabilirlik için idealdir. Kalibreli metroloji aleti ya da mikron seviyesinde hassas ölçüm cihazı değildir; hassas metroloji gerektiren işlerde sertifikalı ölçüm aletine yönlendiririz. Vaadimizi net tutarız: gündelik işinizde güvenle kullanacağınız, ölçünüze birebir uyan bir alet.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü, boyunuzu ve üzerine geçecek yazı/logoyu iletin. Cetvel veya mastar dışında üretilen parçanın kendi yüzeyine isim, yön oku, kısa metin ya da parça kodu ekletmek için <a href="/ozel-parcaya-logo-ve-yazi-isleme/">özel parçaya logo ve yazı işleme</a> sayfasına geçebilirsiniz. Sitemizden <strong>kartla online ödeyerek</strong> sipariş verebilir ya da ölçü danışmak, özel bir iş konuşmak için <strong>WhatsApp +90 545 138 6526</strong> hattından bize yazabilirsiniz.</p>
<p>İz bırakan bir alet mi arıyorsunuz? Kişiye özel işleme için <a href="/kisiye-ozel-logolu-kase-yaptirma/">logolu kaşe yaptırma</a> sayfamıza bakın (kaşe iz bırakır, cetvel ölçer — farklı işler). Tek bir özel parça için <a href="/tek-adet-ozel-parca-uretimi/">tek adet özel parça üretimi</a>, malzeme seçimi için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfalarımız yardımcı olur.</p>""")


def _olcuye_ozel_koruma_kapagi_muhafaza_uretimi():
    return (u"""<h1>Ölçüye Özel Koruma Kapağı, Muhafaza ve Koruyucu Üretimi</h1>
<p>Açıkta kalan bir dişli, kayış, terminal ya da sensör; toz, çapak, darbe ve istenmeyen temasın hedefidir. Piyasada tam o parçaya oturan bir koruma kapağı çoğu zaman bulunmaz — ya çok büyük, ya çok küçük, ya da hiç yoktur. PRUVO açıkta kalan parçanızı ölçüye özel örten koruyucu kapak, muhafaza ve guard üretir. Ölçü sizden, üretim bizden.</p>
<p>Kırılan bir kapağı yenilemek, hiç olmayan bir yere koruma eklemek ya da mevcut muhafazayı iyileştirmek isteyin — parçayı örten, kaplayan, kılıflayan gövdeyi bulunduğu yere göre çıkarırız. Amaç, korumaya aldığınız parçanın çevresini kapatmak: elin, tozun, sıçrayan suyun veya yandan gelen darbenin doğrudan temasını kesmek.</p>
<p>Dişli koruması, kayış muhafazası, terminal kutusu kapağı, sensör koruma kapağı, valf üzeri koruyucu — hepsi aynı mantıkla çalışır. Önce korunacak parçayı ve etrafındaki boşluğu ölçeriz, sonra o hacmi saran kapağı üretiriz. Standart bir kalıba sığmayan, size özel bir geometri olduğu için sonuç birebir oturur; boşlukta oynamaz, yanlış noktadan açık kalmaz.</p>
<p>Bu bir muhafaza koruyucusudur, bir ağzı tıkayan tapa değil. Bir boruyu, deliği veya bağlantı ağzını kapatmak istiyorsanız <a href="/olcuye-ozel-tapa-kapak-uretimi/">ölçüye özel tapa ve kapak üretimi</a> sayfasına bakın; bu sayfa açıktaki bir parçayı örten koruma içindir.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Korumak istediğiniz parçayı, mevcut kırık kapağı ya da montaj bölgesinin fotoğraf ve ölçülerini WhatsApp'tan iletin: +90 545 138 6526.</li>
<li><strong>Ölç</strong> — Korunacak parçanın dış ölçülerini, çevresindeki boşluğu ve sabitleme noktalarını birlikte netleştiririz. Neyi kapatacağını, nereye tutunacağını konuşuruz.</li>
<li><strong>Üret</strong> — Ölçüye özel koruma kapağınızı üretir, size ulaştırırız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her koruma kapağı bulunduğu yere göre biçimlenir. Sizinle netleştirdiğimiz noktalar:</p>
<ul>
<li><strong>Kapsanan hacim</strong> — Korunan parçayı ne kadar örteceği: yalnızca üst yüzey mi, çevreyi saran tam muhafaza mı.</li>
<li><strong>Sabitleme biçimi</strong> — Vidalı, geçmeli ya da mevcut cıvata deliklerine oturan bağlantı.</li>
<li><strong>Erişim ve boşluklar</strong> — Kablo, mil, kayış veya bağlantı için gereken açıklıklar; servis için sökülebilir kapak.</li>
<li><strong>Havalandırma</strong> — Isınan parçada ısı kaçışı için gereken açıklıklar (tam kapalı istenmiyorsa).</li>
<li><strong>Yüzey ve kenar</strong> — Keskin köşesiz, ele ve montaja uygun kenar işlemi.</li>
</ul>
<p>Uydurma bir katalog dayatmayız; ne koruyacağınıza göre bu seçenekleri sizinle belirler, ona göre üretiriz.</p>
<h2>Doğru malzeme</h2>
<p>Koruma kapağının dayanması gereken koşulu birlikte belirleriz. İç mekân, düşük yük için standart malzeme yeterlidir. Isı, UV ve neme maruz kalan (motor çevresi, dış ortam, güneş altı) muhafazalarda PETG veya ASA kullanırız. Sürekli güneş gören bir muhafazada renk sabitliği ve sararma konusunu ayrıca ele aldık: <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">güneşe dayanıklı dış mekân plastik parça üretimi</a>. Darbeye ve zorlanmaya en çok maruz kalan koruyucularda karbon ya da cam fiber takviyeli PA-CF / PA-GF yüksek mukavemet verir. Farklı renk seçenekleriyle üretebiliriz. Doğru malzeme seçimi için <a href="/malzeme-rehberi/">malzeme rehberimize</a> bakabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz koruma kapağı; toz, çapak, hafif darbe ve temas koruması içindir — yük taşıyan, basınç tutan yapısal bir muhafaza değildir. Ağır mekanik yükü karşılayan, contalı sızdırmazlık gerektiren ya da yüksek iç basınca dayanması istenen bir gövde arıyorsanız bunu baştan söyler, sizi doğru çözüme yönlendiririz. Amacımız, açıktaki parçanızı doğru malzemeyle güvenle örtmek. Benzer makine parçaları için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfasına da göz atabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Korumak istediğiniz parçanın ölçü ve fotoğrafını WhatsApp'tan gönderin: <strong>+90 545 138 6526</strong>. Netleşen işlerde siteden kartla online ödemeyle siparişinizi tamamlayabilirsiniz. Ölçü sizden, üretim bizden.</p>""")


def _olcuye_ozel_adaptor_reduksiyon_gecis_uretimi():
    return (u"""<h1>Ölçüye Özel Adaptör, Redüksiyon ve Geçiş Parçası Üretimi</h1>
<p>Bir çaptan başka çapa geçmeniz gereken parça piyasada yoksa, ölçüye özel adaptör üretimi ile milimetrik olarak sizin ölçünüze üretiyoruz. Farklı iki çapı birbirine bağlayan adaptör, redüksiyon ve geçiş parçalarını, elinizdeki mevcut ağız ölçülerine göre üretiriz.</p>
<p>Çoğu geçiş ihtiyacı standart üründe karşılığı olmayan bir ölçüde ortaya çıkar: bir ucu 40 mm, diğer ucu 32 mm olan bir hortum adaptörü; süpürge ağzına oturmayan bir aparat; iki farklı boru hattını birleştiren bir çap düşürücü. Hazır fitinglerde bu ara ölçüler çoğu zaman bulunmaz, bulunsa da tam oturmaz. Sonuç bant, conta ve kaçak dolu geçici çözümlerdir.</p>
<p>Biz redüksiyon parçası üretimini elinizdeki gerçek ölçüye sabitleriz. İki ucun iç/dış çapını, geçiş boyunu ve bağlantı biçimini (geçmeli, dişli, kelepçeli) sizden alır, tam oturan tek parça bir geçiş fitingi üretiriz. Ara ölçü, kademeli çap düşürme veya açılı geçiş fark etmez; parça sizin sisteminize göre çıkar.</p>
<p>Boru geçiş parçası, çap düşürücü adaptör ve özel geçiş fitingi ihtiyaçlarınızda mantık hep aynıdır: parçayı getirir ya da ölçüsünü verirsiniz, biz üretiriz. Ölçü sizden, üretim bizden.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Değiştirmek istediğiniz parçayı, ya da bağlayacağınız iki ağzı bize iletin. Fiziksel parça yoksa çap ve boy ölçülerini paylaşmanız yeterli.</li>
<li><strong>Ölç</strong> — Her iki ucun çaplarını, geçiş boyunu ve bağlantı tipini birlikte netleştiririz. Emin değilseniz WhatsApp'tan ölçü danışması yaparız.</li>
<li><strong>Üret</strong> — Onaylanan ölçüye göre ölçüye özel üretiyoruz ve size ulaştırırız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Giriş ve çıkış çapı</strong> — İki ucun iç ya da dış çapını ayrı ayrı sizin ölçünüze ayarlarız.</li>
<li><strong>Geçiş biçimi</strong> — Ani redüksiyon ya da kademeli/konik geçiş; hattınıza uygun olanı seçeriz.</li>
<li><strong>Bağlantı tipi</strong> — Geçmeli, dişli ya da kelepçe/hortum kelepçesine uygun ağız.</li>
<li><strong>Geçiş boyu ve et kalınlığı</strong> — Sağlamlık ve montaj payına göre uzunluğu ve cidarı ayarlarız.</li>
<li><strong>Sızdırmazlık payı</strong> — Contayla birlikte çalışacaksa oturma yüzeyini ona göre bırakırız. Ayrı <a href="/olcuye-ozel-conta-uretimi/">conta üretimi</a> de yaparız.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Kullanım yerine göre malzeme seçeriz. Standart iç mekân ve düşük yük için genel amaçlı malzeme yeterlidir. Isı, UV ve nem söz konusuysa (dış ortam, sıcak akışkan, ıslak zemin) PETG veya ASA gibi dayanıklı malzemelere çıkarız. Mekanik yük, titreşim ya da yüksek mukavemet gerekiyorsa karbon/cam fiber takviyeli PA-CF / PA-GF öneririz. Farklı renk seçenekleri de sunarız. Hangi malzemenin sizin işinize oturduğunu <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında görebilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Bu geçiş parçaları düşük–orta basınçlı hatlar için uygundur: hortum bağlantıları, süpürge/toz emme, havalandırma, düşük basınçlı su ve akışkan yönlendirme. Yüksek basınçlı hidrolik ya da basınçlı gaz hatları bu üretimin dışındadır; oralarda metal fiting gerekir. Aynı çapta çok kollu birleştirme arıyorsanız o iş <a href="/olcuye-ozel-baglanti-konektor/">bağlantı/konektör üretimi</a> sayfasına aittir; bu sayfa farklı iki çapı birbirine geçirir.</p>
<h2>Sipariş</h2>
<p>Ölçülerinizi hazırlayın, gerisini biz halledelim. Siteden kartla online sipariş verebilir, ölçü danışması ve özel işler için WhatsApp +90 545 138 6526 üzerinden bize yazabilirsiniz. Ölçü sizden, üretim bizden.</p>""")


def _bisiklet_plastik_parca_ozel_uretim():
    return (u"""<h1>Bisiklet Plastik Parçalarının Ölçüye Özel Üretimi</h1>
<p>Modeli kalkmış, kırılmış ya da hiçbir yerde bulamadığınız bisiklet plastik parçasını ölçüye özel üretiyoruz. Çamurluk bağlantısı, şişelik kafesi, kablo yönlendirici, reflektör tutucu, vites-fren maşa kapağı — elinizdeki parçayı ya da ölçüsünü getirin, aynısını çıkaralım. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Bisiklet plastik parçaları kolay yıpranır: güneş altında sararır, kırılganlaşır, çatlar; bir düşme ya da tek bir sert darbe bağlantı kulağını koparır. Üstelik birçok model artık üretilmiyor, yedeği stoklarda kalmıyor. Tek bir küçük klips yüzünden çamurluğun tamamını, bidon kafesinin gitmesi yüzünden komple aparatı değiştirmek zorunda kalıyorsunuz.</p>
<p>Bizim işimiz tam da bu boşluğu kapatmak. Piyasada karşılığı olmayan bisiklet yedek parçasını, kırılan parçanın kendisinden ya da vereceğiniz ölçülerden yola çıkarak birebir üretiyoruz. Elinizde kırık parça varsa daha da iyi: <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parçayı yaptırma</a> sürecinde parçaları birleştirip ölçüyü oradan alıyoruz. Hangi marka, hangi yıl olduğunu bilmeniz gerekmez — parça yeterli.</p>
<p>Bisiklet aksesuar parça üretimi ve bisiklet yedek parça yaptırma konusunda bize en çok gelen işler: kopan çamurluk bağlantısı üretimi, dağılan şişelik kafesi yaptırma, gövdeden düşen kablo yönlendirici, yerinden çıkan reflektör tutucu ve çatlayan vites-fren maşa kapağı. <a href="/bulunamayan-yedek-parca-ozel-uretim/">Bulunamayan yedek parçanın özel üretimi</a> için de aynı yol geçerli.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eski parçayı bize ulaştırın; parça yoksa ölçüleri ve birkaç net fotoğraf yeterli.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçüyoruz; bağlantı deliklerini, kalınlığı, kavis ve kulakları birebir çıkarıyoruz.</li>
<li><strong>Üret</strong> — Doğru malzemeyle ölçüye özel üretip elinize ulaştırıyoruz. Takıldığında oturması esas.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her bisiklet parçası farklı; standart bir kalıba sığmaz. Ölçünüze göre şunları ayarlıyoruz:</p>
<ul>
<li><strong>Bağlantı deliği</strong> çapı, sayısı ve aralarındaki mesafe — cıvatanıza/vidanıza birebir oturur.</li>
<li><strong>Kalınlık ve kesit</strong> — orijinaline göre ince ya da takviyeli; kırılan yer daha dayanıklı çıkabilir.</li>
<li><strong>Kavis ve gövde formu</strong> — çamurluk yayına, kadro borusuna ya da bidon çapına uyacak biçim.</li>
<li><strong>Klips ve geçme tırnakları</strong> — yerine tık diye oturan kulak/klips ölçüsü.</li>
<li><strong>Renk</strong> — farklı renk seçenekleri arasından parçanıza yakışanı.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Bisiklet dışarıda, güneşte ve nemde çalışır; malzeme seçimi bu yüzden kritik. Standart plastikle yetinmeyiz. Dışarıda kalan, UV ve nemle uğraşan parçalarda ısıya ve güneşe dayanıklı <strong>PETG veya ASA</strong> kullanırız — sararmadan, kırılganlaşmadan uzun ömür verir. Yük gören, sık zorlanan bağlantılarda ise cam/karbon fiber takviyeli <strong>PA-GF / PA-CF</strong> ile yüksek mukavemet sağlarız. Parçanın nerede, nasıl çalıştığına bakıp doğru malzemeye yönlendiririz. Kararsızsanız <a href="/malzeme-rehberi/">malzeme rehberine</a> göz atabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Açık konuşalım: burada ürettiğimiz parçalar hafif ve yük-dışı bisiklet plastik parçalarıdır — çamurluk bağlantısı, bidon kafesi, klips, tutucu, kapak gibi. <strong>Kadro, çatal, jant, direksiyon kelepçesi gibi ana yükü taşıyan yapısal parçaları üretmeyiz;</strong> bunlar sürüş güvenliğini doğrudan etkiler ve orijinal mühendislik gerektirir. Doğru malzemeyle işlevsel, uzun ömürlü bir plastik parça sözü veririz; taşıyıcı bir emniyet parçası sözü vermeyiz.</p>
<h2>Sipariş</h2>
<p>Elinizdeki parçayı ya da ölçüleri paylaşın, birlikte netleştirelim. Siteden kartla online sipariş verebilir, ölçü danışmak ya da özel iş için WhatsApp'tan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Bisiklet klips parçasından çamurluk bağlantısına, aradığınız parçayı ölçüye özel üretelim.</p>""")


def _kamera_optik_aksesuar_plastik_parca_uretimi():
    return (u"""<h1>Kamera, Tripod ve Optik Aksesuar Plastik Parça Üretimi</h1>
<p>Kameranızın pil kapağı kırıldı, tripodun hızlı çıkış plakası kayboldu, flaş kızağı çatladı ya da bir lens parçası artık hiçbir yerde bulunamıyor. Bu küçük plastik parçalar için koca ekipman rafta bekliyor. Ölçüsünü verin, o parçayı size özel üretelim. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Kamera ve optik aksesuarların en zayıf halkası çoğu zaman ufacık bir plastik detaydır: pil yuvasının menteşeli kapağı, tripod ayağının bağlantı kelepçesi, hızlı çıkış (quick release) plakası, flaş kızağının (hot shoe) oturma parçası, adaptör halkası ya da lens üzerindeki bir tutamak. Model eskiyince yedeği üretilmez, bulunsa da tek parça için sipariş verilmez. Sonuçta sağlam bir cihaz, on liralık bir parça yüzünden kullanılamaz hale gelir.</p>
<p>Biz tam da bu noktada devreye giriyoruz. Elinizdeki kırık parçayı, eski parçanın izini ya da birkaç ölçüyü baz alarak birebir aynısını, sizin cihazınıza oturacak şekilde üretiyoruz. Katalogda olmayan, üreticisinin arkasını bıraktığı parçalar için en pratik yol bu: mevcut olanı çoğaltmak değil, sizin özel ihtiyacınıza göre yeniden üretmek.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eksik parçayı, mümkünse eski parçanızı elinizde bulundurun. Fotoğraf ve birkaç net ölçü (kalınlık, delik çapları, vida aralığı, kızak genişliği) çoğu iş için yeterlidir.</li>
<li><strong>Ölç</strong> — Bağlantı noktalarını, oturma yüzeyini ve toleransları birlikte netleştiriyoruz. Kamera aksesuarlarında geçme ve klik hassastır; bu yüzden ölçüyü baştan doğru alıyoruz.</li>
<li><strong>Üret</strong> — Parçayı ölçünüze özel üretip size ulaştırıyoruz. Cihaza takıp deneyeceğiniz, oturan bir parça teslim ediyoruz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Kamera ve tripod aksesuarlarında her parça kendine özgü olduğu için işi ölçünüze göre biçimlendiriyoruz:</p>
<ul>
<li><strong>Boyut ve geçme toleransı</strong> — pil kapağı, kızak ve plaka gibi parçaların oturma ölçüsü sizin cihazınıza göre ayarlanır.</li>
<li><strong>Bağlantı detayları</strong> — vida deliği çapı, dişli yuva, klik/kilit tırnağı, menteşe noktası eski parçanıza birebir uyarlanır.</li>
<li><strong>1/4" ve 3/8" bağlantılar</strong> — tripod ayağı, hızlı çıkış plakası, adaptör gibi standart vida bağlantıları ölçüye göre konumlandırılır.</li>
<li><strong>Yüzey ve kenar işlemi</strong> — kavrama yüzeyi, pah, yuvarlatma gibi detaylar ihtiyaca göre eklenir.</li>
<li><strong>Farklı renk seçenekleri</strong> — cihazınızla uyumlu ton için renk alternatifleri sunulur.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Parçanın çalışacağı koşula göre malzemeyi seçiyoruz. Görünürde durup taşımayan iç parçalarda standart malzeme yeterli olurken; ısı, güneş ve nem gören dış aksesuarlarda (tripod bağlantısı, dış kapak) <strong>PETG veya ASA</strong> ile daha dayanıklı üretim yapıyoruz. Sürekli yüke ve kuvvete maruz kalan bağlantı parçalarında ise <strong>karbon ya da cam elyaf takviyeli (PA-CF / PA-GF)</strong> yüksek mukavemetli malzemeye çıkıyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz plastik parçalar yük taşımayan, hafif aksesuar parçalarıdır: pil kapağı, kızak, tutamak, bağlantı kelepçesi, adaptör halkası. Ağır bir kamerayı tek başına taşıyacak taşıyıcı bir tripod başlığı ya da hassas optik hizalama gerektiren (lens elemanı konumlandırması gibi) parçalarda önce sizinle konuşur, sınırı açıkça söyleriz. Amacımız takıldığında oturan, işini gören bir parça vermek; taşımayacağı yükü taşır gibi göstermek değil.</p>
<h2>Sipariş</h2>
<p>Kırık ya da eksik parçanızın fotoğrafını ve ölçülerini gönderin, üretilebilirliğini birlikte netleştirelim. Siteden kartla online sipariş verebilir; ölçü danışmak ve özel işler için WhatsApp hattımızdan yazabilirsiniz: <strong>+90 545 138 6526</strong>.</p>
<p>Benzer işler için: <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parça üretimi</a>, <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretim</a> ve <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>""")


def _oyuncak_hobi_model_plastik_parca_uretimi():
    return (u"""<h1>Oyuncak, Hobi ve Maket Plastik Parçalarının Özel Üretimi</h1>
<p>Kırılan bir oyuncak parçası, kaybolan bir kutu oyunu pulu ya da maket-kitinizde eksik kalan tek bir bağlantı — çoğu zaman bütün seti bloke eden şey işte bu küçük parçadır. Piyasada bulunamayan, üretimi durmuş ya da hiç yedeği satılmayan bu parçaları <strong>ölçüye özel üretiyoruz</strong>. Ölçü sizden, üretim bizden.</p>
<p>Oyuncaklar, kutu oyunları, maketler ve koleksiyon figürleri genellikle özel kalıplarla, artık tedarik edilemeyen parçalarla gelir. Tek bir dişli, klips, ayak, mafsal ya da bağlantı elemanı kırıldığında ürünün tamamı kullanılamaz hale gelebilir. Biz eldeki parçayı ya da kırığın izini referans alarak birebir yenisini <strong>özel tasarım üretim</strong> ile çıkarıyoruz.</p>
<p>Kutu oyunlarında kaybolan pullar, tokenlar, standlar ve tutucular; maket ve kit dünyasında eksik gövde parçaları, bağlantı pimleri ve tabanlar; koleksiyon figürlerinde kırılan kol, silah, aksesuar ya da sehpa parçaları için tek adetten üretim yapıyoruz. Elinizde örnek yoksa fotoğraf ve ölçüyle de yola çıkabiliriz.</p>
<p>Not: Uçan ya da süren radyo kontrollü araç parçaları için ayrı bir çalışma alanımız var — onun için <a href="/drone-rc-model-plastik-parca-uretimi/">drone ve RC model plastik parça üretimi</a> sayfasına bakın. Bu sayfa oyuncak, kutu oyunu, maket ve figür nişine odaklıdır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı, örneği ya da net fotoğrafı bize ulaştırın. WhatsApp'tan görsel ve ölçü paylaşmak en hızlısıdır.</li>
<li><strong>Ölç</strong> — Parçanın kritik ölçülerini (bağlantı çapı, kalınlık, delik aralığı, uzunluk) birlikte netleştiriyoruz. Ölçü sizde yoksa örnek üzerinden biz alıyoruz.</li>
<li><strong>Üret</strong> — Doğru malzemeyle ölçüye özel üretip size gönderiyoruz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Birebir ölçü</strong> — parçanın boyutu, kalınlığı, bağlantı çapı ve delik konumları eldeki örneğe göre milimetrik ayarlanır.</li>
<li><strong>Bağlantı biçimi</strong> — geçmeli pim, klips, vidalı ya da yapıştırma bağlantı; mevcut ürünle uyumlu olacak şekilde.</li>
<li><strong>Adet</strong> — tek parçadan küçük seriye; yalnızca ihtiyacınız kadar üretiriz.</li>
<li><strong>Yüzey ve netlik</strong> — düz ya da dokulu yüzey, keskin ya da yumuşatılmış kenar seçeneği.</li>
<li><strong>Farklı renk seçenekleri</strong> — sete uyacak makul bir renk üzerinde anlaşırız.</li>
</ul>
<p>Sadece tek bir eksik parça mı arıyorsunuz? <a href="/tek-adet-ozel-parca-uretimi/">Tek adet özel parça üretimi</a> tam bu iş için.</p>
<h2>Doğru malzeme</h2>
<p>Kullanım yerine göre malzemeyi seçiyoruz. Görünür, düşük yük alan iç parçalarda standart malzeme yeterli olur. Sık takıp çıkarılan, esnemesi ya da güneş/nem görmesi gereken parçalarda <strong>PETG veya ASA</strong> (ısı, UV ve neme dayanıklı) tercih ederiz. Mafsal, dişli, taşıyıcı klips gibi zorlanan parçalarda <strong>karbon/cam fiber takviyeli PA-CF / PA-GF</strong> ile yüksek mukavemet sağlarız.</p>
<h2>Dürüst sınır</h2>
<p>Bunlar hobi ve oyuncak amaçlı, hafif kullanım parçalarıdır; ağır darbe ya da sürekli yük altında çalışan mekanik parçaların yerini tutmaz. Küçük çocukların kullandığı oyuncaklarda küçük/ayrılabilir parça yutma riski ve malzeme güvenliği sizin sorumluluğunuzdadır; bu tür ürünlerde kullanım amacını bize önceden belirtin, uygun malzeme ve tasarıma birlikte karar verelim. Neyin dayanacağını, neyin dayanmayacağını baştan açıkça söyleriz.</p>
<p>İlgili bir ihtiyaç: <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a>.</p>
<h2>Sipariş</h2>
<p>Parçanızın fotoğrafını ve ölçüsünü WhatsApp <strong>+90 545 138 6526</strong> hattına gönderin; üretilebilirliğini ve seçenekleri birlikte netleştirelim. Onay sonrası siteden kartla online ödeyerek siparişinizi tamamlayabilirsiniz. Ölçü sizden, üretim bizden.</p>""")


def _klima_kombi_havalandirma_plastik_parca_uretimi():
    return (u"""<h1>Klima, Kombi ve Havalandırma Plastik Parçalarının Özel Üretimi</h1>
<p>Klimanızın kırılan swing kanadı, kombinizin çatlayan bir plastik parçası ya da havalandırma cihazının yerine takılacak parça piyasada bulunamıyor mu? Cihaz sağlam, ama küçük bir plastik parça yüzünden çalışmıyor. Bu parçayı ölçüsüne göre özel üretiyoruz. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Klima, kombi ve havalandırma cihazlarındaki plastik parçalar zamanla kırılır, çatlar veya güneş ve nemle kırılganlaşır. Üreticiden yedek parça çoğu zaman bulunamaz; bulunsa bile eski modellerde temin süresi uzar. Cihazın tamamını değiştirmek ise gereksiz bir maliyettir.</p>
<p>Elimize gelen kırık swing kanadını, panjur dilini, drenaj tavası parçasını, filtre çerçevesini veya ön panel klipsini inceleyip milimetrik ölçüsüne göre yeniden üretiyoruz. Parça kırıksa bile eldeki parçalardan ve ölçülerden aslına uygun bir kopya çıkarabiliyoruz. Amacımız cihazınızı tekrar çalışır hale getiren, tam oturan bir parça teslim etmek.</p>
<p>Klima kanat parçası üretimi, kombi plastik parça yaptırma ve havalandırma cihazı parçası işlerinde en çok karşılaştığımız sorun, parçanın hem ölçü hem de dayanıklılık olarak doğru olmaması. Biz ikisini birden çözüyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eskimiş parçayı bize ulaştırın; fotoğraf ve ölçüyle de başlayabiliriz.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçer, montaj noktalarını ve klips/vida yerlerini birebir çıkarırız.</li>
<li><strong>Üret</strong> — Doğru malzemeyle ölçüye özel üretir, cihazınıza tam oturan parçayı teslim ederiz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her cihaz parçası kendi ölçüsüne göre çıkar; standart kalıp yoktur. Sizinle netleştirdiğimiz noktalar:</p>
<ul>
<li><strong>Parça tipi</strong> — swing/salınım kanadı, panjur dili, drenaj tavası parçası, filtre/ızgara çerçevesi, ön panel klipsi, kablo/hortum tutucusu.</li>
<li><strong>Montaj detayı</strong> — klips geçmeli mi, vidalı mı; menteşe/pim yeri, kanca ve tırnak konumları birebir korunur.</li>
<li><strong>Ölçü ve tolerans</strong> — dış ölçü, kalınlık ve oturma boşluğu cihaza tam geçecek şekilde ayarlanır.</li>
<li><strong>Kullanım koşulu</strong> — iç mekân mı, nemli/ıslak bölge mi, ısıya yakın mı; malzeme buna göre seçilir.</li>
<li><strong>Renk</strong> — cihaz gövdesine yakın, farklı renk seçenekleri arasından uygun olanı belirleriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Sıradan plastik güneş ve nemde kısa sürede kırılır. Parçanın çalışacağı yere göre doğru malzemeyi seçiyoruz: standart kullanım için dayanıklı seçenekler; ısı, UV ve neme maruz kalan drenaj/dış panel parçalarında <strong>PETG veya ASA</strong>; yük taşıyan, sürekli hareket eden ya da yüksek mukavemet isteyen parçalarda <strong>karbon veya cam elyaf takviyeli (PA-CF / PA-GF)</strong> malzemeler. Böylece parça, çalışacağı koşula uygun sınıfta üretilmiş olur.</p>
<h2>Dürüst sınır</h2>
<p>Açık söyleyelim: kombinin yanma bölgesine temas eden veya sürekli yüksek sıcaklığa maruz kalan parçaları özel plastikle üretmiyoruz — bu, malzemenin sınırının dışındadır ve güvenli olmaz. Bizim alanımız klima kanat/panjur, drenaj ve tava parçaları, filtre çerçeveleri, panel ve klips gibi ısıl yük taşımayan plastik parçalardır. Parçanızın nereye takıldığını sorar, sınırın dışındaysa dürüstçe söyleriz.</p>
<p>Kırılan parça kanat ya da panjur değil, cihazın havayı üfleyen dönen çarkıysa, o iş için <a href="/olcuye-ozel-fan-carki-uretimi/">ölçüye özel fan çarkı ve kanat üretimi</a> sayfamız doğru adrestir; çark kanattan ayrı bir parçadır, dış çap, kanat sayısı ve mil geçmesi ayrı ölçülür. Cihaz değil de duvara ya da tavana geçen bir menfez/ızgara paneli arıyorsanız, o iş için <a href="/olcuye-ozel-izgara-petek-uretimi/">ölçüye özel ızgara ve petek üretimi</a> sayfamıza bakın. Beyaz eşya parçaları için <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a>, malzeme seçimi için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfalarımız yardımcı olur.</p>
<h2>Sipariş</h2>
<p>Kırık parçanızın fotoğrafını ve ölçüsünü WhatsApp hattımızdan gönderin: <strong>+90 545 138 6526</strong>. Ölçüyü birlikte netleştirir, uygun malzemeyi öneririz. Onay verdiğinizde siteden kartla online ödemeyle siparişinizi tamamlarsınız. Ölçü sizden, üretim bizden.</p>""")


def _aydinlatma_armatur_plastik_parca_uretimi():
    return (u"""<h1>Aydınlatma ve Armatür Plastik Parçalarının Özel Üretimi</h1>
<p>Avize, spot, lamba ya da armatürünüzün kırılan plastik parçasını piyasada bulamıyorsanız, o parçayı ölçüsüne göre yeniden üretiyoruz. Ölçü sizden, üretim bizden.</p>
<p>Aydınlatma ürünlerinde arızalanan çoğu şey ampul değil, onu tutan küçük plastik parçadır: kırılan duy tutucu bracket, kopan difüzör klipsi, çatlayan montaj halkası, eksik spot çerçevesi ya da yerinden çıkan lamba tabanı. Bu parçalar çoğu zaman ürüne özeldir; markası kalkmış, modeli belirsiz veya çoktan üretimden kalkmıştır. Tek bir parça için koca armatürü değiştirmek de mantıklı değildir.</p>
<p>Biz tam da bu noktada devreye giriyoruz. Elinizdeki kırık parçayı ya da bağlanacağı yuvayı esas alıp, aynı ölçülerde yenisini özel tasarım üretimle çıkarıyoruz. Aydınlatma plastik parça üretiminde amaç, parçanın hem geometrik olarak yerine oturması hem de bulunacağı koşula uygun malzemeden olmasıdır.</p>
<p>Spot montaj halkası üretimi, avize parçası yaptırma, duy tutucu üretimi ya da lamba plastik parça ihtiyacınız ne olursa olsun, süreç aynıdır: parçayı anlıyoruz, ölçüyoruz, üretiyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eksik parçayı, elinizde varsa örneğini bize ulaştırın. Parça kırıksa parçaları da saklayın; ölçü çıkarmamıza yardımcı olur.</li>
<li><strong>Ölç</strong> — Parçayı ve bağlandığı yuvayı milimetrik ölçüyoruz. Delik aralığı, çap, kanca geometrisi, klips tırnağı gibi kritik noktaları birebir çıkarıyoruz.</li>
<li><strong>Üret</strong> — Doğru malzemeyi seçip parçayı ölçünüze özel üretiyoruz. Yerine takılıp çalıştığından emin oluyoruz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Parça tipi:</strong> duy tutucu bracket, difüzör/cam klipsi, montaj halkası, spot çerçevesi, avize kolu bağlantısı, lamba tabanı.</li>
<li><strong>Bağlantı ölçüleri:</strong> vida deliği aralığı, çap, tırnak/klips geometrisi, kanca açısı — hepsi mevcut yuvanıza göre.</li>
<li><strong>Difüzör/cam tutuş biçimi:</strong> klipsli, vidalı ya da geçmeli.</li>
<li><strong>Malzeme sınıfı:</strong> kullanılacağı sıcaklık ve yük durumuna göre seçiyoruz.</li>
</ul>
<p>Kısacası ürünün kendi ölçülerini esas alıyoruz; genel geçer değil, elinizdeki parçanın gerçeğine göre.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçiyoruz. Isıya ve yüke uzak montaj parçalarında standart malzeme yeterlidir. Isınabilen ortam ya da nemli/UV koşula açık noktalarda PETG veya ASA gibi dayanıklı malzemelere çıkıyoruz. Mekanik olarak zorlanan, taşıyıcı bağlantılarda ise karbon veya cam fiber takviyeli (PA-CF / PA-GF) yüksek mukavemetli malzemeleri kullanıyoruz. Farklı renk seçenekleri sunabiliyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Açık olalım: ampule ya da ısı kaynağına çok yakın, sürekli yüksek sıcaklığa maruz kalan noktalar plastik parçanın sınırıdır. Doğrudan ısınan cam yuvası ya da güçlü halojen ampule temas eden bir bileşen için plastik doğru çözüm olmaz. Ancak ısı kaynağından uzaktaki montaj, tutuş ve bağlantı parçalarında — bracket, klips, halka, çerçeve, taban — ölçüye özel ürettiğimiz parça uzun süre iş görür. Parçanızın bulunduğu yeri konuşalım, ısıya yakınsa sizi doğru malzemeye yönlendirir, uygun değilse açıkça söyleriz.</p>
<p>Ayrıca daha genel kırık plastik parça ihtiyaçları için <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a>, cihaz içi parçalar için <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parça üretimi</a> sayfalarına, malzeme seçimini detaylı görmek için <a href="/malzeme-rehberi/">malzeme rehberine</a> bakabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Elinizdeki parçayı anlatın, birlikte doğru malzemeyi belirleyelim. Siparişinizi siteden kartla online verebilir ya da ölçü ve parça danışması için WhatsApp hattımızdan yazabilirsiniz: <strong>+90 545 138 6526</strong>. Ölçü sizden, üretim bizden.</p>""")


def _ofis_ekipmani_plastik_parca_uretimi():
    return (u"""<h1>Ofis Makinesi ve Ekipmanı Plastik Parçalarının Özel Üretimi</h1>
<p>Kırılan ofis parçasını bize getirin ya da ölçüsünü iletin; ölçüye özel, doğru malzemeden yeni parçasını üretelim.</p>
<p>Ofis makineleri ve mobilyaları yıllarca çalışır, ama küçük bir plastik parça kırıldığında koca cihaz kullanılmaz hale gelir. Fotokopi/tarayıcı makinesindeki bir dişli aşınır, evrak imha makinesinde bir klips kopar, ofis koltuğunun mekanizma kolu çatlar — ve o parça artık hiçbir yerde bulunmaz. Model eskimiştir, üretici parçayı ayrı satmaz ya da tüm mekanizmayı yenilemeniz istenir.</p>
<p>Biz tam da bu noktada devreye giriyoruz. Piyasada bulunamayan, kırılan ya da eskiyen plastik parçayı milimetrik ölçüye göre yeniden üretiyoruz. <strong>Ofis ekipmanı plastik parça üretimi</strong> işinde çalışma mantığımız net: elinizdeki parçayı ölçü referansı alırız, kırık yerleri tamamlarız, gerekiyorsa dayanımı orijinalinden yüksek malzemeyle güçlendiririz. Ofis koltuğu parçası üretimi ya da ofis makinesi plastik parça yaptırma — hangi cihaz olursa olsun işleyiş aynı.</p>
<p>Fotokopi/tarayıcı makinesi dişlisi ve rulmanı, evrak imha makinesi parçası, laminasyon makinesi parçası, ciltleme aparatı, ofis koltuğu piston kapağı ve taban parçaları, kırtasiye ve sunum/pano aparatları — hepsi ölçüye özel çıkabilir. Ofis kırtasiyesinde en sık yenilenen kalem olan kaşede işi geciktiren şey ise ölçü değil dosyadır; <a href="/kaseye-islenecek-logo-dosyasi-nasil-hazirlanir/">kaşeye işlenecek logo dosyası nasıl hazırlanır</a> sayfası gönderilecek logonun nasıl kontrol edileceğini anlatıyor. Aynı yaklaşımı <a href="/ev-aleti-plastik-disli-parca-uretimi/">ev aletlerindeki plastik dişli ve parçalarda</a> ve <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parçalarında</a> da uyguluyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı yanınızda getirin ya da fotoğrafı ve ölçüleriyle WhatsApp'tan iletin.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçeriz; delik çapları, diş sayısı, bağlantı noktaları ve kırık bölgeleri çıkarırız.</li>
<li><strong>Üret</strong> — Ölçüye ve kullanım yerine uygun malzemeyle yeni parçayı üretir, size teslim ederiz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Parça tipi:</strong> dişli, rulman yatağı, klips, kol, kapak, taban, braket, aparat — ne kırıldıysa.</li>
<li><strong>Ölçü ve delik eşleme:</strong> dış ölçü, delik çapı ve aks aralığı orijinaliyle birebir eşlenir.</li>
<li><strong>Bağlantı ve montaj:</strong> vida yuvası, geçme tırnak, kanal ve pim noktaları yerine oturur.</li>
<li><strong>Dayanım kademesi:</strong> normal kullanım mı, sürekli yük mü, ısı yanında mı — ona göre malzeme.</li>
<li><strong>Farklı renk seçenekleri:</strong> görünür parçalarda mevcut renge yakın seçenekler sunarız.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Her parça aynı malzemeyi istemez. Az yük gören iç parçalarda standart mühendislik plastiği yeterlidir. Sürekli sürtünen, ısıya ya da neme yakın çalışan parçalarda PETG veya ASA gibi dayanıklı malzemelere geçeriz. Yüksek mukavemet gereken dişli ve yük taşıyan parçalarda ise karbon ya da cam elyaf takviyeli PA-CF / PA-GF kullanırız. Hangi parçaya hangi malzemenin uyduğunu <a href="/malzeme-rehberi/">malzeme rehberimizde</a> ayrıntılı anlatıyoruz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parçalar mekanizma, bağlantı ve hafif–orta yük işleri içindir; <strong>ofis makinesi dişli üretimi</strong> ve benzeri işlerde orijinaline yakın, çoğu zaman daha dayanıklı sonuç alırsınız. Ancak ağır yük altında ezilen ya da yüksek tork taşıyan metal bir parçanın yerini plastik tutmaz — böyle bir durumda parçayı doğru malzemeye yönlendirir, gerçekçi sınırı açıkça söyleriz.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Sipariş ve ölçü danışmanlığı için siteden kartla online sipariş verebilir ya da WhatsApp'tan +90 545 138 6526 numarasına yazabilirsiniz. Kırık parçanızı anlatın, size en uygun çözümü birlikte netleştirelim.</p>""")


def _muzik_enstruman_plastik_parca_uretimi():
    return (u"""<h1>Müzik Enstrümanı Plastik Parçalarının Özel Üretimi</h1>
<p>Akort düğmesi kırıldı, köprü pini kayboldu, nefesli çalgının valf kapağı çatladı ya da klavyenin bir tuşu eksik. Enstrüman sağlam duruyor ama tek bir küçük plastik parça yüzünden çalınamıyor. Bu parçaların çoğu artık üretilmiyor, modeli bulunamıyor veya sırf o parça için koca bir set almak gerekiyor. PRUVO tam burada devreye girer: elinizdeki parçayı ölçüp ölçünüze özel yeniden üretiriz. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Enstrüman plastik parça üretimi, seri kalıp mantığıyla değil, tek parçaya odaklanarak yapılır. Kırık gitar akort düğmesini, eksik köprü pinini, nefesli çalgı valf kapağını, klavye tuşunu, çene ya da başparmak dayamasını, kopan klipsi orijinaline sadık kalarak yeniden üretiriz. Elinizdeki örnek parça kırık bile olsa, kalan parçalardan ve ölçülerden hareketle doğru geometriyi çıkarırız.</p>
<p>Gitar plastik parça yaptırma, nefesli çalgı parçası ya da klavye tuşu üretimi gibi işlerde en büyük kazanç, tek parça için bütün enstrümanı ya da pahalı setleri elden çıkarmak zorunda kalmamanızdır. Bulunamayan yedek parçayı, modeli piyasadan kalkmış bir çalgının küçük ama kritik bileşenini ölçüye özel üretiriz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eksik parçayı bize ulaştırın; parça yoksa ölçülerini ve fotoğraflarını iletin. WhatsApp'tan hızlıca danışabilirsiniz.</li>
<li><strong>Ölç</strong> — Parçanın boyutlarını, delik/vida yerlerini, oturma geometrisini milimetrik çıkarırız. Kritik parçada nasıl kullanacağınızı sorar, buna göre yönlendiririz.</li>
<li><strong>Üret</strong> — Onayınızın ardından ölçüye özel üretir, kontrol edip göndeririz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her enstrüman parçası kendine özgü olduğundan, üretimi sizin parçanıza göre ayarlarız:</p>
<ul>
<li><strong>Birebir ölçü</strong> — Kırık akort düğmesi, köprü pini, valf kapağı; orijinalin boyutlarına ve oturma yerine göre.</li>
<li><strong>Bağlantı ve oturma detayı</strong> — Vida yuvası, mil deliği, geçme klips, dişli oturması: enstrümanınıza tam oturacak şekilde.</li>
<li><strong>Form ve profil</strong> — Çene/başparmak dayamasının eğrisi, tuşun yüzey profili, düğmenin kavrama şekli.</li>
<li><strong>Renk uyumu</strong> — Enstrümanın mevcut parçalarına yakın, farklı renk seçenekleriyle bütünlük.</li>
</ul>
<p>Elinizde örnek varsa ona göre, yoksa marka-model ve ölçü bilgisiyle çıkarım yaparak üretiriz.</p>
<h2>Doğru malzeme</h2>
<p>Malzeme, parçanın nerede ve nasıl çalışacağına göre seçilir. Az yük gören iç parçalarda standart malzeme yeterlidir. Isı, nem ve UV'ye maruz kalan (sahne, taşıma, dış ortam) parçalarda <strong>PETG veya ASA</strong> kullanırız. Yüksek mukavemet ve tekrarlı kuvvet gereken yerlerde <strong>karbon veya cam fiber takviyeli (PA-CF / PA-GF)</strong> malzemeye çıkarız. Doğru malzeme, parçanın hem dayanmasını hem de enstrümanınıza zarar vermemesini sağlar.</p>
<h2>Dürüst sınır</h2>
<p>Sesi ve rezonansı doğrudan belirleyen kritik bileşenlerde (örneğin köprü, eşik gibi tınıyı taşıyan parçalar) plastik üretim her zaman en doğru tercih olmayabilir; bu tür parçalarda malzeme ve kullanım danışmanlığı vererek sizi yönlendiririz. Düğme, kapak, tuş, dayama ve klips gibi mekanik/ergonomik parçalarda ise ölçüye özel üretim güçlü ve kalıcı bir çözümdür. Beklentiyi baştan net konuşur, işe yaramayacak bir üretime girmeyiz.</p>
<p>İlgili işler: <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a>, <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretim</a> ve malzeme seçimi için <a href="/malzeme-rehberi/">malzeme rehberi</a>.</p>
<h2>Sipariş</h2>
<p>Elinizdeki parçayı ölçüp fiyat verelim. Sitemizden kartla online sipariş verebilir ya da parçanızı fotoğraflayıp WhatsApp <strong>+90 545 138 6526</strong> üzerinden danışabilirsiniz. Kırık düğmeden eksik tuşa, enstrümanınızı yeniden çalınır hale getiren parçayı ölçünüze özel üretiriz.</p>""")


def _akvaryum_terraryum_plastik_parca_uretimi():
    return (u"""<h1>Akvaryum ve Teraryum Plastik Parçalarının Özel Üretimi</h1>
<p>Akvaryumunuzun ya da teraryumunuzun bir plastik parçası kırıldığında yenisini bulmak çoğu zaman imkânsızdır: model eski, marka artık üretmiyor ya da parça tek başına satılmıyor. PRUVO'da çözüm basit — parçayı getirin, ölçüsünü alalım, ölçünüze özel yeniden üretelim. Ölçü sizden, üretim bizden.</p>
<p>Filtre klipsi, çıkış borusu ya da lülesi, kapak menteşesi, hortum tutucu, yemleme kapağı — akvaryum ve teraryum sistemlerinin en çok kırılan küçük plastik parçaları bunlardır. Piyasada tek tek bulunmadıkları için genelde koca bir ekipmanı elden çıkarmanız gerekir. Oysa çoğu zaman eksik olan tek bir tutucu ya da bir menteşedir.</p>
<p>Biz bu niş parçaları tek tek, akvaryum plastik parça üretimi mantığıyla ele alıyoruz. Elinizdeki kırık parçayı örnek alarak yenisini çıkarabilir, parça tamamen kayıpsa fotoğraf ve ölçülerle birlikte hangi noktaya oturması gerektiğini konuşarak yeniden tasarlayabiliriz. Teraryum parçası yaptırma taleplerinde de aynı yol geçerli: kapak kelepçesinden havalandırma ızgarasına kadar ölçüye özel üretiyoruz.</p>
<p>Sürekli suyla ve canlıyla temas eden bir ortam olduğu için malzeme seçimi burada işin en kritik yanı. Doğru malzemeyle üretilen bir parça yıllarca dayanırken, yanlış seçim kısa sürede kırılganlaşır. Bu yüzden her parçayı çalışacağı yere göre değerlendiriyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da eksik parçayı bize ulaştırın; parça yoksa ölçülerini ve nereye oturduğunu fotoğrafla paylaşın.</li>
<li><strong>Ölç</strong> — Bağlantı noktalarını, çap ve kalınlıkları milimetrik ölçeriz; oturma toleransını sizinle netleştiririz.</li>
<li><strong>Üret</strong> — Ölçünüze ve kullanım koşulunuza uygun malzemeyle özel üretir, size ulaştırırız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Bağlantı ölçüsü</strong> — hortum çapı, boru dış çapı, klips genişliği ve menteşe pim aralığı sizin sisteminize göre.</li>
<li><strong>Parça tipi</strong> — filtre klipsi, çıkış borusu / lüle, kapak menteşesi, hortum tutucu, yemleme kapağı ve benzeri küçük parçalar.</li>
<li><strong>Kalınlık ve sağlamlık</strong> — hafif tutucudan yük taşıyan menteşeye göre et kalınlığı ayarı.</li>
<li><strong>Yüzey ve oturma</strong> — düz ya da kavisli yüzeye tam oturacak biçim; kayması istenmeyen yerlerde sıkı geçme.</li>
<li><strong>Renk</strong> — koyu ya da açık, sisteminize uygun farklı renk seçenekleri.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Akvaryum ve teraryum ortamı sürekli nem, su teması ve çoğu zaman UV'li aydınlatma demek. Sıradan malzeme burada uzun ömürlü olmaz. Bu yüzden nem, ısı ve UV'ye dayanıklı <strong>PETG ve ASA</strong> grubu malzemelerle çalışırız. Menteşe gibi tekrarlayan yük altındaki parçalar için ise <strong>karbon ya da cam fiber takviyeli (PA-CF / PA-GF)</strong> yüksek mukavemetli seçeneklere geçeriz. Hangi parçanın hangi malzemeyle üretileceğini kullanım koşulunuzu dinleyerek beraber belirleriz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz parçalar akvaryum ve teraryumun hafif kullanımı içindir: tutma, klipsleme, yönlendirme, kapak ve menteşe işlevleri. Sürekli su altında kalan ya da canlı-gıda ile doğrudan temas eden parçalarda malzeme danışması şarttır — bunu peşinen konuşuruz. Ürettiğimiz parça basınçlı sızdırmazlık contası değildir; yüksek basınçlı hat ya da tam su geçirmezlik gerektiren yerlerde sınırımızı açıkça söyleriz.</p>
<p>Aynı mantıkla üretilen diğer işler için <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> ve <a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe üretimi</a> sayfalarına, malzeme seçiminin ayrıntısı için <a href="/malzeme-rehberi/">malzeme rehberi</a>ne göz atabilirsiniz.</p>
<h2>Sipariş</h2>
<p>Ölçüsü belli parçalar için siteden kartla online sipariş verebilirsiniz. Emin olmadığınız, özel ölçü ya da malzeme danışması gereken işlerde WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Parçanızı getirin, ölçelim, ölçünüze özel üretelim.</p>""")


def _pvc_dograma_kapi_pencere_plastik_parca_uretimi():
    return (u"""<h1>PVC Doğrama Plastik Parçası: Ölçüye Özel Yeniden Üretim</h1>
<p>PVC pencerenin kolu boşa dönüyorsa, sinekliğin mandalı elinizde kaldıysa ya da panjur kayışı makarasından çıkıyorsa sorun genelde koca doğramada değil, içindeki tek bir küçük plastikte olur. Kapağın tırnağı kırılır, mandalın yayı oturduğu yuva çatlar, makaranın kanalı aşınır — ve o parça yüzünden çalışmayan bütün bir kanat ortaya çıkar. Doğramanın kendisi sapasağlam durur, hareket eden minik plastik gider.</p>
<p>Bu parçalar için yedek bulmak çoğu zaman imkânsıza yakındır. Doğrama sistemleri markaya ve yıla göre değişir; on yıl önce takılan bir serinin ispanyolet kapağı bugün üretimden kalkmıştır, sineklik mandalı ithal edilmiyordur, panjur kayış makarası yalnızca komple mekanizmayla satılıyordur. Yapı marketinde "benzerini" bulursunuz, ama kanal genişliği tutmaz, mil çapı boşluk yapar, vida delikleri denk gelmez. Sonunda ustalar tek çıkış olarak komple kanat ya da komple mekanizma değişimini önerir; küçük bir plastik yüzünden büyük bir masraf çıkar. <strong>pvc pencere plastik yedek parça</strong> aramasının çoğu böyle biter.</p>
<p>PRUVO tam bu noktada devreye girer. Elinizdeki kırık parçayı — parçaları — alır, ölçüsünü çıkarır ve aynı ölçüde yeniden üretiriz. İspanyolet kapağı yaptırma, sineklik mandalı yedek parça, pvc doğrama köşe takozu, balkon kapısı kilit dili, panjur kayış makarası gibi işler bizim için standart iştir; kataloğu olmayan, modeli kalmayan parça bizde numuneden yeniden doğar. <strong>Ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı bize ulaştırın. Parça ikiye, üçe ayrıldıysa sorun değil; kırıkları bir araya getirip ölçü alabiliriz. Tamamen kaybolmuşsa oturduğu yuvanın ve karşı parçanın net fotoğrafları ile bir cetvel ölçüsü işi başlatmaya yeter. Fiziksel örneğin hiç kalmadığı işlerde hangi kanıtların gerektiğini <a href="/numune-olmadan-plastik-parca-yaptirilir-mi/">numune olmadan plastik parça yaptırılır mı</a> rehberinde sıralıyoruz.</li>
<li><strong>Ölç</strong> — Kanal genişliği, mil çapı, oturma derinliği, vida delikleri arası mesafe gibi kritik ölçüleri tek tek çıkarırız. Aşınmış bölgeleri orijinal haliyle hesaplar, kırık yüzeyleri tamamlarız.</li>
<li><strong>Üret</strong> — Parçanın çalışacağı yere uygun malzemeyi seçer, ölçüye özel üretiriz. Takıldığında boşluk yapmayan, tırnağı tutan, kanadı yerine oturtan bir parça elinize geçer.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Numuneden birebir ölçü</strong> — kırık parçalar bir araya getirilerek orijinal geometri geri kazanılır.</li>
<li><strong>Doğrama kanal genişliği ve profil kesiti</strong> — parçanın oturduğu kanala tam giren genişlik.</li>
<li><strong>Mil / pim çapı ve oturma derinliği</strong> — kolun, mandalın ya da milin boşluk yapmadan dönmesi için.</li>
<li><strong>Makara çapı, kalınlığı ve kayış kanal genişliği</strong> — panjur kayışının kanaldan atmaması için üç ölçü birlikte ayarlanır.</li>
<li><strong>Vida delik çapı ve delikler arası mesafe</strong> — mevcut deliklere yeni delik açmadan denk gelen bağlantı.</li>
<li><strong>Dış cepheye bakan parçalarda UV dayanımlı ASA, iç parçalarda standart sınıf</strong> — konuma göre malzeme kararı.</li>
<li><strong>Farklı renk seçenekleri</strong> — beyaz, kahve, antrasit; doğramanızın rengine yakın olanı seçeriz.</li>
</ul>
<p>Ayarlar bu kadar somuttur çünkü doğrama parçasında iş milimetrede biter. Bir mandalın mil çapı yarım milimetre büyük olursa yuvasına girmez, yarım milimetre küçük olursa boşta döner.</p>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın nerede ve ne yaptığına göre seçeriz:</p>
<ul>
<li><strong>Standart sınıf</strong> — kapalı alanda kalan, güneş görmeyen, ılıman koşulda çalışan iç parçalar: iç mandal kapakları, kılavuz takozlar, iç tutamak parçaları.</li>
<li><strong>PETG / ASA</strong> — dış cepheye bakan, doğrudan güneş gören, yağmura ve sıcak-soğuk döngüsüne maruz kalan parçalar. Panjur makarası, dış sineklik mandalı, cephe tarafındaki kapaklar için varsayılanımız <strong>UV dayanımlı ASA</strong>'dır; standart malzeme dışarıda zamanla sararır ve kırılganlaşır, bunu bilerek önermeyiz.</li>
<li><strong>PA-CF / PA-GF (karbon / cam elyaf takviyeli)</strong> — yük taşıyan, sürekli hareket eden ya da kilit mekanizmasına bağlı çalışan küçük parçalar. Balkon kapısı kilit dili, ispanyolet aktarma parçaları ve sürekli açılıp kapanan ağır kanat aksesuarlarında mukavemet gerektiğinde bu sınıfa çıkarız.</li>
</ul>
<p>Hangi sınıfın gerektiğini parçayı gördüğümüzde söyleriz; gereksiz yere üst sınıfa çıkarıp fiyat şişirmeyiz, ama dışarıda çalışacak parçaya iç malzeme de vermeyiz.</p>
<h2>Dürüst sınır</h2>
<p>Plastiğin doğramada nereye kadar gittiğini açıkça söylüyoruz — güven bundan doğar.</p>
<p><strong>Üretiriz:</strong> mandal, kapak, takoz, makara, kilit dili, tutamak ve benzeri küçük hareketli parçalar. Bunlar zaten fabrikada da plastiktir; ölçüsü doğru olduğunda orijinaliyle aynı işi görür.</p>
<p><strong>Üretmeyiz:</strong> camı taşıyan profil, ana kilit karkası ve güvenlik kilidi gövdesi. Bunlar yapısal ve güvenlik parçalarıdır; kanadın ağırlığını ya da zorlamaya karşı direnci taşırlar. Bu işler metal profil ve orijinal mekanizmanın alanıdır, plastikle karşılanmaz — böyle bir talep geldiğinde açıkça hayır deriz.</p>
<p><strong>Malzemede taviz vermeyiz:</strong> sürekli güneş alan bir dış parçaya standart sınıf önermeyiz. Ucuza çıksın diye verilen böyle bir parça bir yaz görür, ikinci yazda kırılır; baştan UV dayanımlı sınıfa çıkmak daha doğrudur.</p>
<h2>Sipariş</h2>
<p>Sitemizden <strong>kartla online ödeme</strong> yapabilirsiniz; ölçüye özel üretilen doğrama parçaları da buna dahildir. Parçanız hangi sistemden, hangi ölçüde, hangi renkte olacak emin değilseniz önce yazın: <strong>WhatsApp +90 545 138 6526</strong>. Kırık parçanın ve takıldığı yerin birkaç fotoğrafını gönderin, üretilebilir mi, hangi malzeme gerekir, ne kadar sürer — net cevap verelim. Emin olmadan sipariş vermenizi istemeyiz.</p>
<p>Doğramada işiniz menteşe tarafındaysa <a href="/olcuye-ozel-mentese-uretimi/">ölçüye özel menteşe üretimi</a> sayfasında o parça tipini ayrıntılı anlatıyoruz; kırılan şey bir tutturma elemanıysa <a href="/olcuye-ozel-klips-kelepce-uretimi/">klips ve kelepçe üretimi</a> sayfasına, elinizde adı bile bilinmeyen bir kırık parça duruyorsa doğrudan <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> sayfasına bakabilirsiniz. Sorun sürme kanadın altındaki makaradaysa — kanat zor kayıyor, makara yalpalıyor ya da rayından çıkıyorsa — <a href="/olcuye-ozel-tekerlek-makara-uretimi/">ölçüye özel tekerlek ve makara üretimi</a> sayfasında çap, kanal ve aks ölçüsünün nasıl alındığını anlatıyoruz. Hangisi olursa olsun akış aynı: getir, ölç, üret.</p>""")


def _olcuye_ozel_dugme_ayar_topuzu_uretimi():
    return (u"""<h1>Kırılan Düğme ve Ayar Topuzu: Mil Ölçüsüne Göre Üretim</h1>
<p>Bir cihazın en çok yıpranan parçası çoğu zaman en küçük parçasıdır: elle çevrilen kumanda düğmesi. Ocakta zorlanan bir topuz, radyoda gevşeyip mile boş dönen bir kadran, tezgahta çarpma sonucu çatlayan bir ayar düğmesi… Cihazın geri kalanı sapasağlam durur, ama tek bir plastik parça yüzünden ayar yapılamaz hale gelir. Cihaz düğmesi ayar topuzu yaptırma ihtiyacının neredeyse tamamı bu noktada doğar: makine çalışıyor, sadece kumanda ucu gitmiş.</p>
<p>Bu parçayı piyasada bulmak zordur, çünkü topuz evrensel bir yedek parça değildir. Üretici her modelde mil profilini, kavrama derinliğini ve dış ölçüyü kendi tercihine göre belirler; birkaç yıl sonra o kalıp da tedarikten düşer. Görünüş olarak benzeyen bir topuz aldığınızda mil kesiti tutmaz, D-mil düz yuvaya oturmaz, tırtıllı mil boşluk yapar. "Ocak düğmesi kırıldı yenisi nereden bulunur" ya da "fırın ayar düğmesi yaptırma" diye arayanların çoğu, aslında tek bir ölçünün — mil profilinin — peşindedir; markanın kendisinin değil.</p>
<p>PRUVO bu işi ters yönden çözer. Cihazın markasını, modelini ya da yaşını sormadan, topuzun oturduğu milin kesitine ve çapına bakarız. D-mil, tırtıllı, kare ya da düz mil; hangi profil varsa aynı ölçüde kavrama yuvası oluşturur, topuzun dış biçimini de kullanım şekline göre ayarlarız. Amfi ses topuzu özel üretim isteyen bir kullanıcı ile kaynak makinesi ayar topuzu arayan bir atölye, teknik olarak aynı işi ister: mile birebir oturan, elde kaymayan bir kumanda ucu. <strong>Ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırık topuzun parçalarını ya da milin kendisini elimize ulaştırın. Topuz tamamen kaybolduysa yalnızca milin fotoğrafı ve birkaç ölçü de yeterlidir; parçayı göndermeden de ilerleyebiliriz.</li>
<li><strong>Ölç.</strong> Mil kesitini (D, tırtıllı, kare, düz) ve mil çapını, kavrama derinliğini, varsa sıkma vidasının konumunu ölçeriz. Panelde topuzun kaplayacağı dış çap ve yükseklik de burada belirlenir; gösterge çizgisinin hangi konumu göstereceğini birlikte kararlaştırırız.</li>
<li><strong>Üret.</strong> Onaylanan ölçülerle topuzu üretir, mil üzerinde geçme sıkılığını kontrol ederiz. Çok sayıda düğmeli bir panelde tek topuz değiştiğinde göze batmaması için gövde biçimini ve rengi mevcut takımla uyumlu seçebiliriz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Mil tipi ve çapı:</strong> D-mil, tırtıllı (kertikli), kare ya da düz mil; ölçülen çapa göre yuva işlenir. D-mil topuz ölçüye özel istendiğinde düzlemin yönü ve derinliği de ayrıca belirlenir.</li>
<li><strong>Topuz dış çapı ve yüksekliği:</strong> parmakla mı, avuçla mı çevrileceğine göre; dar panellerde komşu düğmeye değmeyecek ölçüde.</li>
<li><strong>Kavrama derinliği ve sıkma vidası yuvası:</strong> milin ne kadar içeri gireceği; isteğe bağlı yandan sıkma vidası yuvası ve somun yatağı.</li>
<li><strong>Gövde biçimi:</strong> düz silindir, aşağı doğru genişleyen konik ya da güç gerektiren ayarlar için kanatlı tutuş.</li>
<li><strong>Üst yüzeyde gösterge:</strong> çizgi ya da ok işareti; kapalı konumun nereye geleceğini siz söylersiniz.</li>
<li><strong>Kenar tırtılı:</strong> parmak kavrama dokusu; ıslak ya da yağlı elle çevrilen yerlerde daha derin tırtıl.</li>
<li><strong>Farklı renk seçenekleri:</strong> mevcut panel takımına yakın ton ya da bilinçli olarak ayırt edici bir renk.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Topuzun ömrünü belirleyen şey biçimden çok malzemedir. Oda sıcaklığında çalışan bir ses sistemi, ölçü aleti ya da tezgah düğmesi için standart sınıf yeterlidir; ucuzdur, boyutu kararlıdır.</p>
<p>Isınan gövdelere yakın konumlarda — fırın kapağı çevresi, ocak paneli, motor ya da kompresör gövdesi — ısıya ve UV'ye dayanıklı sınıfa çıkarız (PETG, ASA). ASA hem açık havada renk atmaya hem de ısıya PETG'den daha dirençlidir.</p>
<p>Sürekli çevrilen, sıkışmış ya da yüksek tork uygulanan millerde karbon/cam elyaf takviyeli sınıfı (PA-CF / PA-GF) öneririz. Bu sınıf kavrama duvarının incelmesine izin verir ve uzun süreli kullanımda yuva ağzının yayvanlaşmasını geciktirir. Hangi sınıfın gerektiğini parçanın çalıştığı yeri öğrenip biz söyleriz; gereksiz yere pahalı malzemeye yönlendirmeyiz.</p>
<h2>Dürüst sınır</h2>
<p>Doğrudan aleve ya da sürekli yüksek sıcaklığa temas eden konumlarda standart malzeme yumuşar. Ocak ve fırın gibi sıcak bölgelerde ısıya dayanıklı sınıfa çıkarız; buna rağmen doğrudan alev teması ya da fırın içi sıcaklığa maruz kalan konumlar için uygun değildir. Topuz, panel yüzeyinde ve sıcaklığın düştüğü mesafede çalışmalıdır.</p>
<p>İkinci sınır sıkışmış millerde ortaya çıkar. Yıllardır çevrilmemiş, içi kurumuş bir vana ya da valf milinde topuz ağzı zorlanır; zorlamayı önce en ince kesit karşılar. Böyle bir durumda kavrama duvarını kalınlaştırır, gerekirse takviyeli malzemeye geçer ya da milin kendisinin temizlenmesini öneririz. Plastik bir topuzun sıkışmış bir mili söktürmesini vaat etmeyiz — sınırı önceden söylemek, iki hafta sonra ikinci bir kırık parçayla uğraşmaktan iyidir.</p>
<h2>Sipariş</h2>
<p>Sitede kartla online ödeme var; ölçüye özel üretilen parçalar da dahil, siparişi doğrudan verebilirsiniz. Mil kesitinden emin değilseniz ya da elinizde ölçü aleti yoksa, kırık parçanın ve milin fotoğrafını WhatsApp hattımıza gönderin: <strong>+90 545 138 6526</strong>. Hangi ölçüleri nasıl alacağınızı adım adım tarif eder, uygun malzeme sınıfını birlikte belirleriz.</p>
<p>Cihazınızda düğmeyle birlikte başka parçalar da yorulduysa aynı ölçü mantığı onlar için de geçerlidir: gövde ve panel parçaları için <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> sayfasına, çekilerek ya da taşınarak kullanılan elemanlar için <a href="/olcuye-ozel-kulp-tutamak-uretimi/">ölçüye özel kulp ve tutamak üretimi</a> sayfasına bakabilirsiniz. Düğme dönüyor ama hareket cihaza geçmiyorsa sorun genelde aktarımdadır; bu durumda <a href="/ev-aleti-plastik-disli-parca-uretimi/">ev aleti plastik dişli parça üretimi</a> sayfasındaki yöntem işinizi görür. Hepsinde akış aynı: getir, ölç, üret.</p>""")


def _olcuye_ozel_fan_carki_uretimi():
    return (u"""<h1>Fan Çarkı Kırıldı: Ölçüye Özel Yeni Çark Üretimi</h1>
<p>Fan çarkı kırıldığında cihazın kendisi sağlamdır; dönen tek bir plastik parça yüzünden hava akışı biter. Kanadın ucundan bir parça kopar, göbek çatlar, mil deliği ovalleşir — ve çark ya hiç dönmez ya da titreyerek dönüp yatağı da götürür. Sorun büyük değildir, ama yedeği yoktur. Cihazın modeli eskidir, üretici o parçayı ayrı satmaz, sanayide bulunan hazır çarkların çapı ya da mil deliği tutmaz. Milimetrelik fark yüzünden elinizdeki çark takılmaz.</p>
<p>Biz bu noktada devreye giriyoruz: <strong>ölçüye özel fan çarkı</strong> üretiyoruz. Elinizdeki kırık parçayı ölçüyor, dış çapını, kanat sayısını, kanat açısını ve mil geçme ölçüsünü birebir çıkarıyor, yenisini o ölçülerle üretiyoruz. Fan pervanesi kırıldı, yenisi hiçbir yerde yok diyorsanız aradığınız çözüm budur. Aspiratör çarkı özel üretim işi de aynı yoldan yürür: parça tek başına, cihaz markasından bağımsız, kendi geometrisi üzerinden ele alınır.</p>
<p>Ölçü sizden, üretim bizden. Soğutma fanı kanadı yaptırma, salyangoz fan çarkı ölçüye göre çıkarma, kafes tipi radyal çarkın göbeğini yenileme — hepsi aynı mantıkla çalışır. Kırık parçanız yoksa da sorun değil; mil çapını, dış çapı ve yüksekliği kumpasla alıp bize iletmeniz yeterli. Elimizde model yoksa geometriyi sıfırdan kurar, üretim öncesi ölçü teyidini sizinle yaparız.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırık çarkı, parçalarını ya da elinizdeki ölçüleri bize iletin. Fotoğraf ve kumpas ölçüsü çoğu iş için yeterlidir; parçayı elden teslim etmek isterseniz o da olur. Kanatları kopmuş çarkın göbeği sağlamsa, geometriyi ondan çıkarırız.</li>
<li><strong>Ölç.</strong> Dış çap, göbek çapı, toplam yükseklik, mil deliği ölçüsü, kanat sayısı ve kanat açısı çıkarılır. Dönüş yönü mutlaka teyit edilir — ters yönlü bir çark takıldığında fan döner ama hava akışı oluşmaz. Ölçü listesini onayınıza sunarız.</li>
<li><strong>Üret.</strong> Onaylanan geometriyle çark üretilir, göbek ve mil geçmesi kontrol edilir, çapak alınır. Denge açısından kanatlar simetrik çıkar; kritik işlerde mil geçmesini deneme parçasıyla önceden doğrularız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Çark dış çapı ve toplam yükseklik</strong> — yuvaya giren tam ölçü; kanat ucuyla gövde arasındaki boşluk korunur.</li>
<li><strong>Kanat sayısı ve kanat açısı</strong> — orijinaldeki kanat adedi ve eğim birebir alınır; hava debisi ve ses seviyesi buna bağlıdır.</li>
<li><strong>Dönüş yönü</strong> — saat yönü ya da ters yön. Kanat eğimi yön üzerine kurulur, motorun yönüne göre seçilir.</li>
<li><strong>Mil deliği çapı, D-kesit ya da kama kanalı</strong> — düz mil, düzlemi tıraşlanmış D-kesit mil ya da kamalı mil; hangisi varsa o işlenir.</li>
<li><strong>Göbek yüksekliği ve set vidası yuvası</strong> — göbek boyu mil boyuna göre ayarlanır, set vidası için yuva ve gerekirse somun yatağı açılır.</li>
<li><strong>Eksenel ya da radyal form</strong> — pervane tipi eksenel çark (hava mil boyunca akar) ya da salyangoz/kafes tipi radyal çark (hava kanat ucundan dışarı atılır).</li>
<li><strong>Farklı renk seçenekleri</strong> — görünür yerdeki çarklarda cihazla uyumlu renk seçilebilir.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Çarkın nerede döndüğü malzemeyi belirler. Oda sıcaklığında, kapalı gövde içinde çalışan düşük devirli bir havalandırma çarkı standart malzemeyle sorunsuz gider.</p>
<p>Isınan bölge söz konusuysa — kombi çevresi, fırın arkası, elektronik kabin içi, güneş gören dış üniteler — PETG ya da ASA tercih ederiz. ASA açık havada UV ve neme karşı belirgin biçimde daha dayanıklıdır, kolay gevrekleşmez; ısı dayanımı da PETG'den yüksek olduğu için motorun yaydığı ısıya yakın çalışan çarklarda tercihimizdir.</p>
<p>Yüksek devir, sürekli çalışma ve titreşim varsa karbon ya da cam elyaf takviyeli malzemeye (PA-CF / PA-GF) çıkarız. Takviyeli gövde daha rijittir; kanat uçları savrulma altında daha az esner, göbek mil üzerinde kolay gevşemez. Endüstriyel aspiratör çarkları ve gün boyu dönen soğutma fanları bu sınıfa girer.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz çark hava taşıyan fan/hafif çark sınıfındadır: soğutma, havalandırma ve emiş içindir. Su içinde itiş sağlayan tekne pervanesi, sirkülasyon pompası çarkı ya da yüksek devirli türbin görevi görmez — bunlar sürekli sıvı yükü ve kavitasyon altında çalışır, plastik çarkın işi değildir. Bu tip talepleri en başta reddederiz.</p>
<p>İkinci sınır dengedir. Dönen her çark dengesizliği devir karesiyle büyütür; 1 gramlık asimetri yüksek devirde yatağı titretir. Bu yüzden ölçülerin tam alınması ve kanat geometrisinin simetrik olması şarttır. Kırık çarkta kanadın bir kısmı kayıpsa, kalan kanatlardan geometriyi çıkarıp simetriyi biz kurarız; ama eksik ölçüyle "yaklaşık" iş yapmayız.</p>
<p>Üçüncüsü sıcaklıktır. Motor gövdesine temas eden ya da 100 °C üzerine çıkan bölgelerde plastik çarkın yeri yoktur; orada metal çark doğrudur ve bunu açıkça söyleriz. Sizin işinize yaramayacak bir parçayı üretmektense, hangi malzemenin doğru olduğunu en baştan konuşmayı tercih ederiz.</p>
<h2>Sipariş</h2>
<p>Sitemizden kartla online ödeme yapabilirsiniz; ölçüye özel üretilen çarklar da buna dahildir. Ölçüden emin değilseniz ya da elinizdeki parçanın üretilebilirliğini önce konuşmak istiyorsanız WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Kırık çarkın fotoğrafı ve birkaç kumpas ölçüsü, işin yapılabilir olup olmadığını söylememize çoğu zaman yeter. Ölçüleri teyit ettikten sonra üretim süresini ve fiyatı net şekilde paylaşırız.</p>
<p>Çarkın takılı olduğu cihazın başka plastik parçaları da yıprandıysa <a href="/klima-kombi-havalandirma-plastik-parca-uretimi/">klima, kombi ve havalandırma cihazlarının plastik parçaları</a> için ayrı bir sayfamız var; kapak, kanal ve bağlantı elemanlarını orada anlatıyoruz. Küçük soğutma fanları bir kart ya da kabin içinde çalışıyorsa <a href="/elektronik-cihaz-plastik-parca-uretimi/">elektronik cihaz plastik parçaları</a> sayfası daha yakın düşer. Hangi malzemenin sizin çalışma sıcaklığınıza ve devrinize uyduğunu karşılaştırmalı görmek isterseniz <a href="/malzeme-rehberi/">malzeme rehberimize</a> göz atın; seçim orada tek tabloda toplu duruyor.</p>""")


def _olcuye_ozel_tekerlek_makara_uretimi():
    return (u"""<h1>Kırılan Tekerlek ve Makara: Üç Ölçüyle Yeniden Üretim</h1>
<p>Çekmece bir gün açılmaz olur, sepet rayından çıkar, sürgü kapak yerinde takılır. Söküp baktığınızda sorun çoğu zaman tek bir küçük parçadadır: kırılmış ya da yürüyüş yüzeyi aşınmış plastik bir tekerlek. Parça iki liralık görünür ama onun yüzünden koca dolap, koca makine ya da koca kapı iş görmez. Servis "komple grup değişecek" der, yedek parçacı "o model kalktı" der, internette bulduğunuz benzeri de aks deliği tutmadığı için boşta döner.</p>
<p>Bunun sebebi açık: tekerlek ve makara dünyası milimetre dünyasıdır. Aynı görünen iki tekerleğin biri 24 mm çapında ve 6 mm akslı, öteki 25,5 mm çapında ve 5 mm akslıdır; kanal derinliği yarım milimetre şaşınca parça rayına oturmaz. Üreticiler bu parçaları tek tek satmaz, kalıpları da model ömrü bitince rafa kalkar. Sonuçta piyasada bulunamayan şey aslında ürün değil, sizin ölçünüzdür. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>PRUVO tam bu noktada devreye girer. Elinizdeki kırık parçadan, eski tekerlekten ya da boşalan yuvadan yola çıkarak <strong>plastik tekerlek makara yaptırma</strong> işini ölçüye özel yapıyoruz. Çekmece tekerleği yedek parça arayan bir mobilyacı da, bulaşık makinesi sepet tekerleği kopmuş bir ev sahibi de, sürgü kapı makarası özel üretim isteyen bir atölye de aynı yoldan geçer: çap, kanal ve aks. Valiz tekerleği yaptırma ya da aks çapına göre makara talebi de aynı üç ölçüyle çözülür. Elinizde numune yoksa yuvanın ölçüsünü alırız; tek bir parça için de üretim yaparız, adetli iş de aynı hassasiyetle çıkar.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırık tekerleği, sağlam kalan eşini ya da parçanın oturduğu çatalın fotoğrafını gönderin. Parçanız param parça olsa bile sorun değil; ölçü verecek kadar iz kalması yeter. Elinizde hiç parça yoksa yuva ve aks ölçüsünü birlikte çıkarırız.</li>
<li><strong>Ölç.</strong> Dış çap, kalınlık, aks deliği ve kanal biçimini tek tek doğrularız. Nerede, ne yükte, ne sıklıkta çalıştığını sorarız — bu bilgi malzeme seçimini belirler. Ölçüleri size yazılı olarak teyit ederiz, onay vermeden üretime geçmeyiz.</li>
<li><strong>Üret.</strong> Onaylı ölçüyle parçayı üretir, aksa ve yuvaya oturmasını kontrol eder, gönderime hazırlarız. Gerekirse önce tek numune çıkarır, oturduğunu gördükten sonra kalan adede geçeriz.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Tekerlek dış çapı ve kalınlığı</strong> — rayın ya da çatalın izin verdiği ölçüye kadar, milimetrik.</li>
<li><strong>Aks/pim deliği çapı ve göbek uzunluğu</strong> — mevcut pime sıkı değil, dönecek kadar boşluklu oturur.</li>
<li><strong>Yürüyüş yüzeyi biçimi</strong> — düz, V kanallı, U kanallı ya da tırnaklı. Kanalın açısı ve derinliği rayınıza göre belirlenir.</li>
<li><strong>Rulman yuvası mı düz delik mi</strong> — mevcut rulmanınız varsa ona göre yuva açarız; yoksa doğrudan pim üzerinde dönen düz delikli tip yaparız.</li>
<li><strong>Çatal/gövde ile arasındaki boşluk payı</strong> — parçanın sürtmeden, salmadan dönmesi için iki yandaki pay ayarlanır.</li>
<li><strong>Sessiz ve kaygan çalışma için yüzey tercihi</strong> — sürtünmesi düşük, çalışırken sesi az olan bir yüzey isteyebilirsiniz.</li>
<li><strong>Farklı renk seçenekleri</strong> — görünen yerdeki parçalarda mobilyanıza yakın tonu seçebilirsiniz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Tekerleğin ömrünü belirleyen şey ölçü kadar malzemedir. İç mekânda, kuru ortamda çalışan çekmece ve dolap tekerlekleri için standart mühendislik plastiği yeterlidir; sürtünmesi düşük, sessiz ve ekonomiktir.</p>
<p>Nem, sıcak su ya da güneş varsa bir üst kademeye çıkarız: bulaşık makinesi sepet tekerleği gibi sıcak-nemli ortamda çalışan parçalarda ve dış kapı makaralarında PETG ya da ASA tercih ederiz. Sepet rayı, aks klipsi ve deterjan temasının birlikte değerlendirilmesi için <a href="/bulasik-makinesi-sepet-tekerlegi-yaptirma/">bulaşık makinesi sepet tekerleği</a> sayfasına bakabilirsiniz. Bunlar ısıya ve UV'ye standart plastikten belirgin biçimde daha iyi dayanır, güneş altında kolay kolay kırılganlaşmaz.</p>
<p>Yük yüksekse, parça küçükse ya da aks deliği ince kalıyorsa karbon/cam elyaf takviyeli PA-CF ve PA-GF'ye çıkarız. Bu grup, aynı ölçüde çok daha yüksek mukavemet ve boyut kararlılığı verir; ağır sürgü kapak makaralarında ve sürekli çalışan taşıma tekerleklerinde tercih ettiğimiz sınıftır. Hangi kademenin gerektiğini biz söyleriz, gereksiz yere üst malzemeye çıkıp maliyeti şişirmeyiz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz tekerlek <strong>hafif ve orta yük</strong> içindir: mobilya çekmecesi, sepet, sürgü kapak, hafif taşıma, valiz ve el arabası ölçeğindeki serbest dönen tekerlekler. Bu aralıkta plastik tekerlek işini rahatlıkla görür. Aks üzerinden tork alan, kama kanalı ve flanş delik dairesi isteyen bahçe makinesi tekerlek göbeği ise ayrı bir hesaptır; onu <a href="/cim-bicme-bahce-makinesi-plastik-parca-yaptirma/">çim biçme makinesi plastik parça yaptırma</a> sayfasında anlatıyoruz.</p>
<p>Ağır yük, sürekli yüksek hız ya da sıcak-ıslak ortamda çalışan tekerleklerde takviyeli malzemeye çıkarız; buna rağmen metal ya da kauçuk kaplı tekerleğin taşıma kapasitesini vaat etmeyiz. Bir yükün altına giren transpalet tekerleği, sanayi arabası tekeri ya da darbe yiyen zemin makarası plastiğin işi değildir — bunu baştan söyleriz.</p>
<p>Rulmanın kendisini de üretmeyiz. Bilyeli rulman metal işidir; biz mevcut rulmanınızın ölçüsüne göre yuvayı açar, tekerleği o rulmanın etrafına kurarız. Aynı şekilde bu sayfadaki iş yük taşıyıp yuvarlanan serbest tekerlek ve makaradır; rayın içinde kayan kızak dili, uç durdurucu ve makara yatağı gerekiyorsa <a href="/cekmece-rayi-plastik-parcasi-yaptirma/">çekmece rayı plastik parçası yaptırma</a> sayfası doğru adrestir, güç aktaran kayış kasnağı ya da kayış gerdirme elemanı ise farklı bir hesabın konusudur.</p>
<h2>Sipariş</h2>
<p>Siteden <strong>kartla online ödeme</strong> ile sipariş verebilirsiniz; ölçüye özel üretim de dahil, kart ödemesi geçerlidir. Ölçüden emin değilseniz ya da parçanın çalışacağı yeri anlatmak istiyorsanız önce WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Kırık parçanın ve yuvanın birkaç fotoğrafı çoğu zaman doğru üretim için yeterli olur; eksik kalan ölçüyü biz sorarız.</p>
<p>Tekerleğiniz kendi ekseninde değil de bir yatak içinde dönüyorsa, asıl aradığınız parça <a href="/numuneden-plastik-burc-rulman-uretimi/">numuneden ürettiğimiz plastik burç ve yatak elemanları</a> olabilir. Çekmecenin tekerleği kadar rayı, ayağı ya da bağlantısı da kırılmışsa <a href="/mobilya-plastik-baglanti-ayak-parca-uretimi/">mobilya bağlantı ve ayak parçalarını</a> aynı siparişte birlikte çıkarabiliriz. Sorun bir ev aletinin içindeki sepet, raf ya da mekanizma parçasıysa <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> tarafına bakmanız daha doğru olur. Hangisi olursa olsun yol aynı: getir, ölç, üret.</p>""")


def _karavan_plastik_parca_ozel_uretim():
    return (u"""<h1>Karavan ve Motokaravan Plastik Parçası: Ölçüye Özel Üretim</h1>
<p>Karavanda bozulan şey çoğu zaman motor ya da şasi değil, içeride her gün elinizin değdiği küçük plastik donanımdır. Dolap kapağını tutan mandal kırılır, kilit dili yerinden çıkar, perde rayının ucundaki durdurucu kaybolur, havalandırma kapağının kolu çatlar. Araç yola çıkacak duruma gelmiştir ama dolaplar seyir halinde açılır, perde rayda durmaz, kapak titrer. Karavan plastik yedek parça ihtiyacının çoğu bu ölçekte doğar: küçük, ucuz görünen, ama olmadığında yaşam alanını kullanılmaz yapan parçalar.</p>
<p>Bu parçaların bulunamamasının nedeni bellidir. Karavanların büyük bölümü ithaldir; iç donanımı üreten firma çoğu zaman aracı üreten firma değildir. Model on yıl önce üretimden kalkmıştır, iç mobilya donanımı hiç yedek olarak stoklanmamıştır, ya da parça yalnızca komple dolap kiti içinde satılmaktadır. Kırılan karavan mandalı için bayiye sorduğunuzda ya "o parça ayrı gelmiyor" cevabını alırsınız ya da aylarca sürecek bir tedarik süreci konuşulur. Karavan dolap kilit dili, karavan perde rayı ucu, menteşe pimi, kanal kızağı gibi motokaravan plastik aksesuar kalemleri tam da bu yüzden internette aranır ve bulunamaz.</p>
<p>PRUVO bu noktada devreye girer. Elinizdeki kırık parçayı ya da yerine geçeceği yuvayı ölçer, aynı işi görecek parçayı ölçüye özel üretiriz. Tek adet üretiriz; minimum sipariş adedi yoktur. Karavan iç mekan plastik parça işinde kalıp beklemek, set almak ya da kataloğun sizin modelinizi içermesini ummak gerekmez. Konumuz açık: <strong>ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık parçayı, parçaların hepsini (kırıldıysa parçaları atmayın) ya da parçanın oturduğu yuvanın fotoğrafını bize iletin. Kargoyla gönderebilir, WhatsApp'tan fotoğraf ve kaba ölçüleri paylaşabilirsiniz. Parça hiç yoksa yuvanın, vida deliklerinin ve karşı yüzeyin ölçüsü de yeterlidir.</li>
<li><strong>Ölç</strong> — Parçayı milimetrik ölçeriz: dış ölçüler, vida delik çapı, delikler arası mesafe, kanal genişliği, kayma boşluğu. Kırık parçadaki aşınmayı ve orijinaldeki zayıf kesiti de not ederiz; aynı yerden yeniden kırılmaması için gerekiyorsa kesiti kalınlaştırmayı öneririz.</li>
<li><strong>Üret</strong> — Onayınızdan sonra parçayı seçilen malzeme ve renkte üretir, size göndeririz. Aynı parçadan ileride tekrar gerekirse ölçüleriniz kayıtlıdır; ikinci sipariş ilkinden hızlı çıkar.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Parça dış ölçüleri</strong> — uzunluk, genişlik ve kalınlık milimetre bazında; mevcut yuvaya tam oturacak şekilde.</li>
<li><strong>Vida delik çapı ve delikler arası mesafe</strong> — mevcut dolap gövdesindeki delikleri kullanabilmeniz için birebir; havşalı ya da havşasız istediğinizi belirtmeniz yeterlidir.</li>
<li><strong>Mandal / kilit dili yüksekliği ve kanal genişliği</strong> — dilin ne kadar çıkacağı, karşı yuvaya ne kadar gireceği ve kapağın oynamaması için gereken sıkılık ayarlanır.</li>
<li><strong>Ray veya kızak profil kesiti ve kayma boşluğu</strong> — perde rayı ucu, durdurucu ve kızak parçalarında profilin kesiti çıkarılır; sürtmeden ama boşluk yapmadan kayacak tolerans verilir. Hareketin nerede duracağını belirleyen parça için <a href="/plastik-stoper-durdurucu-yaptirma/">ölçüye özel stoper üretimi</a> sayfasındaki yükseklik ve oturma payı ölçüleri esas alınır.</li>
<li><strong>Malzeme seçimi</strong> — iç mekanda kalacak donanım için standart sınıf, güneş gören dış yüzeyler için ASA.</li>
<li><strong>Farklı renk seçenekleri</strong> — beyaz, gri, siyah, antrasit gibi iç donanımda yaygın tonlar; mevcut mobilyanızla uyumlu olanı birlikte seçeriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalışacağı yere göre seçeriz. Dolap içinde kalan, doğrudan güneş görmeyen mandal, tutucu ve ara parçalarda standart sınıf yeterlidir ve ekonomiktir. Camın önünde duran, tavan penceresine yakın, yaz boyunca ısınan bölgelerdeki parçalarda PETG'ye çıkarız. Sürekli güneş altında kalan dış yüzey donanımında — servis kapağı kolu, dış havalandırma çerçevesi, dış mandal kapağı — UV dayanımı olan ASA kullanırız; bu sınıf zamanla sararmaya ve kırılganlaşmaya karşı belirgin biçimde daha dayanıklıdır. Sürekli kuvvet gören, ince kesitli, yola çıktığında titreşimle sürekli zorlanan bir dil veya kol söz konusuysa karbon/cam elyaf takviyeli sınıfa (PA-CF / PA-GF) geçeriz; bu sınıf sertlik ve yorulma dayanımı ister.</p>
<h2>Dürüst sınır</h2>
<p>Bu sayfadaki iş, karavanın yaşam alanı donanımıdır: mobilya mandalı, dolap kilit dili, menteşe, kapak, ray ve kızak parçaları, havalandırma ve servis kapağı detayları. Bu kalemlerde parçanın kırılan kesitini gerekirse kalınlaştırır, aynı yerden yeniden kırılma ihtimalini azaltırız.</p>
<p>Sınırı da açıkça söylüyoruz. Şasi, aks, çeki demiri ve bunlara bağlı taşıyıcı elemanlar plastikle üretilmez; bunlar aracın yol güvenliğini ilgilendiren metal parçalardır. Gaz hattı üzerindeki bağlantılar ve su hattında yük taşıyan rakor/bağlantı parçaları da bu kapsamın dışındadır. Sürekli güneş gören dış parçalarda standart malzeme önermeyiz; müşteri istese bile UV dayanımlı sınıfa yönlendiririz, çünkü bir sezon sonra kırılan parçanın maliyeti ilk seferde doğru malzeme seçmekten yüksektir. Hafif yüklü tutucu ve kanal parçaları güvenle üretilir; ağır yükü asılı taşıyacak bir askı beklentisi varsa bunu baştan konuşur, gerekirse metal destekle birlikte çözeriz.</p>
<h2>Sipariş</h2>
<p>Sitemizden kartla online ödeme yapabilirsiniz; ölçüye özel üretilen parçalar dahil tüm siparişler kartla ödenebilir. Ölçüden emin değilseniz ya da parçanın fotoğrafı üzerinden konuşmak isterseniz WhatsApp danışma hattımız açık: <strong>+90 545 138 6526</strong>. Kırık parçanın fotoğrafını ve yanına bir cetvel koyup çektiğiniz ikinci bir kareyi göndermeniz çoğu iş için başlangıç olarak yeterlidir; kalan ölçüleri biz sorarız.</p>
<p>Karavan dışında da aynı yöntem geçerli: piyasada karşılığı olmayan her tekil parça için <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parçaları ölçüye özel ürettiğimiz</a> sayfaya göz atabilirsiniz. Dolap kapağı düşüyorsa sorun mandalda değil menteşede olabilir; bu durumda <a href="/olcuye-ozel-mentese-uretimi/">ölçüye özel menteşe üretimi</a> tarafına bakmak daha doğru sonuç verir. Kaybolan tapa, tıpa ve körleme kapakları içinse <a href="/olcuye-ozel-tapa-kapak-uretimi/">tapa ve kapak üretimi</a> sayfasındaki ölçü seçenekleri işinizi görecektir.</p>""")


def _tekstil_makinesi_plastik_parca_uretimi():
    return (u"""<h1>Tekstil Makinesi Plastik Parçası: Numuneden Ölçüye Özel Üretim</h1>
<p>Dokuma tezgâhının iplik kılavuzu kırıldığında ya da masuranın flanşı çatladığında iş durur; oysa arayan da bilir ki o küçük plastik parça hiçbir yerde raf malı olarak durmaz. Makine on beş yaşındaysa, ithal edilmiş ama temsilcisi çekilmişse, ya da parça zaten üreticinin kataloğunda ayrı kalem olarak geçmiyorsa aramanın sonu genelde aynı yere çıkar: "yok, komple grup satıyoruz." Tek bir kılavuz için komple grup almak da, tezgâhı beklemeye almak da atölyenin işine gelmez.</p>
<p>Tekstil makinesi plastik parça ihtiyacının ikinci zorluğu adet. Elinizde on tezgâh varsa on iki masura lazımdır, beş yüz değil. Kalıplı üretim yapan yerler bu adetlere bakmaz bile; kalıp masrafı tek başına parçanın yüz katıdır. Bu yüzden konfeksiyon makinesi yedek plastik arayan atölyeler çoğu zaman ya kırık parçayı yapıştırıp idare eder ya da bir tornacıya metalden benzerini yaptırır — biri kısa ömürlü, diğeri gereksiz pahalı ve çoğu zaman karşı yüzeyi aşındıran bir çözümdür.</p>
<p>PRUVO tam bu boşlukta çalışır. Elinizdeki kırık masurayı, iplik kılavuzunu, dokuma makinesi plastik burcunu ya da kızak takozunu numune olarak alır, ölçüsünü çıkarır ve size ölçüye özel üretiriz. Ölçü sizden, üretim bizden. Tek adet de olur, beş ile elli arasında düşük adetli seri plastik parça da; minimum sipariş engeli yoktur ve aynı parçayı altı ay sonra tekrar istediğinizde ölçüsü bizde durduğu için aynısını yeniden üretiriz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Kırık ya da aşınmış parçayı elden getirin veya kargoyla gönderin. Parça tamamen dağılmışsa masadaki iki büyük kırık bile yeter; yoksa kumpasla aldığınız iç çap / dış çap / boy ölçülerini net fotoğrafla birlikte WhatsApp'tan iletmeniz de çalışır.</li>
<li><strong>Ölç</strong> — Numuneyi ölçer, kritik yüzeyleri (yatak deliği, kılavuz kanalı, flanş oturma yüzeyi) tek tek çıkarırız. Parçanın makinede nerede çalıştığını, hangi hızda döndüğünü ve neye sürttüğünü sorarız; malzeme kararı buradan çıkar.</li>
<li><strong>Üret</strong> — Ölçüler onaylandıktan sonra üretime alırız. Düşük adetli seride önce tek numune üretip sizde denemenizi öneririz; oturduğunu gördükten sonra kalan adet gelir.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Numuneden ölçü ya da hazır ölçü listesi:</strong> Elinizdeki parçadan ölçü çıkarırız; teknik ölçü listeniz veya makine kılavuzundan aldığınız değerler varsa doğrudan onunla da üretiriz.</li>
<li><strong>İç çap, dış çap, boy ve flanş çapı:</strong> Masura ve burçta dört ana ölçü ayrı ayrı ayarlanır. Mil üzerine geçen iç çapta sıkı/geçer tercihinizi sorarız.</li>
<li><strong>Kılavuz kanal genişliği ve yüzey geçiş yarıçapı:</strong> İplik kılavuzunda kanalın ipliğe göre genişliği ve ipliğin girdiği köşedeki yumuşama yarıçapı ayarlanabilir — bu iki değer ipliğin tüylenip tüylenmeyeceğini belirler.</li>
<li><strong>Sürtünme ve aşınma beklentisine göre malzeme:</strong> Aynı ölçüdeki parçayı PETG, ASA ya da takviyeli PA-CF / PA-GF olarak üretebiliriz.</li>
<li><strong>Düşük adetli seri ve tekrar üretim:</strong> 5–50 adet aralığı bizim için normal iştir. Ölçü kayıtlı kaldığı için ikinci parti ilkiyle aynı ölçülerde çıkar.</li>
<li><strong>Farklı renk seçenekleri:</strong> Vardiya ayrımı ya da makine numarası takibi için parçaları farklı renklerde isteyebilirsiniz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme kararı parçanın makinedeki yerine göre verilir. Az yük gören kapak, muhafaza, göstergelik ve konum parçalarında standart malzeme yeterlidir ve en ekonomik olanıdır. Atölye sıcaklığının yükseldiği, temizlik kimyasalının bulaştığı ya da parçanın sürekli titreşim aldığı yerlerde PETG veya ASA'ya çıkarız; bunlar ısıya ve darbeye standart malzemeden belirgin şekilde dayanıklıdır. İplik kılavuzu, burç, kızak takozu gibi sürekli sürtünen ve ölçüsünü koruması gereken parçalarda karbon ya da cam elyaf takviyeli PA-CF / PA-GF öneririz: rijitliği yüksektir, ısı altında ölçü kaçırmaz ve aşınma direnci ciddi biçimde daha iyidir. Masura yaptırma işlerinde ise ipliğin temas ettiği yüzeyin pürüzsüzlüğü malzeme kadar önemlidir; o yüzden yüzey geçişlerini ayrıca çalışırız.</p>
<h2>Dürüst sınır</h2>
<p>Her tekstil plastiği aynı işi görmez, bunu baştan söyleriz. Kılavuz, masura, takoz, burç ve kapak gibi parçalar bizim rahatça ürettiğimiz sınıftır. Buna karşılık çok yüksek devirde sürekli sürtünen elemanlar, sıcak silindire doğrudan temas eden parçalar ve ana tahrik yükünü taşıyan bağlantılar plastiğin sınırını aşar. Böyle bir parça geldiğinde iki şeyden birini yaparız: ya açıkça "bunu plastikten üretmeyelim, metale gitmeniz doğru olur" deriz, ya da takviyeli malzemeyle bir deneme parçası üretip makinede birlikte test ederiz. Tutmazsa tutmadığını da söyleriz. Zorlama bir söz vermek yerine parçanın gerçek ömrünü konuşmak ikimizin de işine gelir.</p>
<h2>Sipariş</h2>
<p>Ölçüsü belli işlerde sitemizden kartla online ödeme yapabilirsiniz; ölçüye özel üretim de dahil, sipariş doğrudan sistemden geçer. Parçanız hakkında önce konuşmak, numune fotoğrafı göndermek ya da adet ve malzeme için fikir almak isterseniz WhatsApp hattımız açık: <strong>+90 545 138 6526</strong>. Fotoğraf ve iki üç kumpas ölçüsü çoğu zaman ilk değerlendirme için yeterlidir.</p>
<p>Tezgâh yanındaki ihtiyacınız yalnızca tekstil plastikleriyle sınırlı değilse, genel çerçeveyi <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçasında ölçüye özel üretim</a> sayfasında anlattık. Aşınan yatak elemanları için <a href="/numuneden-plastik-burc-rulman-uretimi/">numuneden burç ve rulman üretimi</a> sayfasına, elinizde tek bir kırık parça varken nasıl ilerlediğimizi görmek için de <a href="/tek-adet-ozel-parca-uretimi/">tek adet özel parça üretimi</a> sayfasına bakabilirsiniz.</p>""")


def _elektrikli_scooter_plastik_parca_uretimi():
    return (u"""<h1>Elektrikli Scooter Plastik Parçası: Ölçüye Özel Üretim</h1>
<p>Elektrikli scooter kullananların en sık yaşadığı sorun, motorun ya da bataryanın değil, dış plastiklerin bitmesidir. Kaldırım taşına sürtünen çamurluk çatlar, scooter devrildiğinde gidon kapağı kırılır, şarj kapağı bir süre sonra mandalını kaybedip açık kalır. Cihaz gayet iyi çalışıyordur; ama küçük bir plastik parça yüzünden yağmurda kullanılamaz, sesli titrer ya da içine su alma riski taşır.</p>
<p>Bu parçaların piyasada bulunamamasının nedeni açıktır: ülkeye giren scooter modellerinin çoğu kısa ömürlü ithal serilerdir. Model bir yıl satılır, ertesi yıl yerine yenisi gelir ve eski modelin dış plastikleri için yedek stok hiç açılmaz. Servisler "bu modelin parçası gelmiyor" der, satıcı yeni cihaz önerir. Elektrikli scooter plastik yedek parça arayan kullanıcı, aslında sadece elli gramlık bir kapak için binlerce liralık cihazı gözden çıkarmak zorunda kalır.</p>
<p>PRUVO bu noktada devreye girer. Kırılan scooter gövde parçasını, elinizdeki numuneden ölçerek yeniden üretiriz. Katalogdan model aramayız; parçanın kendisini ölçeriz. Scooter çamurluğu yaptırma, scooter gidon kapağı ya da şarj kapağı kırıldı yenisi lazım diyen her talep, aynı yoldan ilerler: <strong>ölçü sizden, üretim bizden.</strong></p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırılan parçayı, parçaların hepsini bize ulaştırın. Tek parça halinde olması gerekmez; ikiye üçe ayrılmış kapaklar da işimize yarar. Parça tamamen kayıpsa, takıldığı yerin fotoğrafını ve elinizdeki ölçüleri paylaşmanız yeterli olur.</li>
<li><strong>Ölç.</strong> Ayrılmış parçaları birleştirerek bütün geometriyi çıkarırız; delik çapları, mandal dili kalınlığı ve boru çapı gibi kritik ölçüleri tek tek doğrularız. Bu aşamada nereye takıldığını ve nasıl bir yük aldığını da sorarız — malzeme seçimi buna göre değişir.</li>
<li><strong>Üret.</strong> Onayladığınız ölçüyle parçayı üretir, geçme ve vida noktalarını kontrol ederiz. Takıldığında oturmuyorsa toleransı düzeltip yeniden üretiriz. Koşulu şimdiden yazalım: sapma bizim aldığımız ölçüden kaynaklanıyorsa revizyon bizdendir, ayrıca ücret istemeyiz; parçanın ölçüsü sizin isteğinizle değişirse bu yeni bir iş olarak fiyatlandırılır.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Numuneden ölçü:</strong> elinizdeki orijinal parça referanstır. Ayrılmış parçalar birleştirilerek eksik geometri tamamlanır.</li>
<li><strong>Mandal dili kalınlığı ve geçme toleransı:</strong> şarj kapağı ya da batarya kapağı mandalının hem tutması hem de zorlamadan açılması için dil kalınlığını ve geçme boşluğunu ayarlarız.</li>
<li><strong>Gidon/boru dış çapı ve kelepçe genişliği:</strong> gidon kapağı, tutucu ve kelepçe tipi parçalar boru çapına birebir oturacak şekilde çıkar.</li>
<li><strong>Vida delik çapı ve merkez mesafeleri:</strong> mevcut gövdedeki delikler değişmez; delik çapını ve delikler arası mesafeyi cihazınıza göre veririz.</li>
<li><strong>Dış kullanım ve titreşim koşulu:</strong> güneşte kalan, yağmur gören ve sürekli titreşim altındaki parçalarda ASA veya PETG; yük alan tutucu ve bağlantılarda karbon elyaf takviyeli PA-CF.</li>
<li><strong>Farklı renk seçenekleri:</strong> çamurluk ve kapaklarda gövde rengine yakın seçeneklerle çalışırız.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme, parçanın nerede durduğuna göre seçilir. İç tarafta kalan, güneş görmeyen kapak ve ara parçalarda standart malzeme yeterlidir. Ancak scooter dış plastikleri günün büyük kısmını açık havada geçirir: çamurluk, gidon kapağı ve şarj kapağı hem UV hem sıcaklık hem de sürekli titreşim altındadır. Bu parçalarda ASA ve PETG kullanırız — ASA güneş altında rengini ve sertliğini korur, PETG darbede kırılmak yerine esner.</p>
<p>Yük taşıyan tutucular, sepet bağlantısı ya da telefon tutucu gövdesi gibi üzerine kuvvet binen parçalarda merdivenin üst kademesine çıkarız: karbon ya da cam elyaf takviyeli PA-CF / PA-GF. Bu malzemeler titreşim altında yorulmaya karşı belirgin şekilde daha dayanıklıdır. Hangi kademenin gerektiğine parçayı gördükten sonra karar veririz; gereksiz yere üst malzemeye yönlendirmeyiz.</p>
<h2>Dürüst sınır</h2>
<p>Scooter tarafında ürettiğimiz aile bellidir: çamurluk, kapaklar, gidon parçaları, tutucular ve örtü parçaları. Bunlar kırıldığında cihazın kullanımını bozan ama güvenliğini doğrudan belirlemeyen parçalardır.</p>
<p>Üretmediğimiz parçalar da aynı netlikte: fren sistemine ait parçalar, şasi boru bağlantıları ve sürüş sırasında tüm ağırlığınızı taşıyan katlama kilidinin ana gövdesi. Bu parçalar ani ve tek yönlü bir kuvvet altında çalışır; verdikleri hata sessiz olmaz, sürüş sırasında olur. Plastikle üretilmeleri doğru değildir ve bu taleplerde sizi orijinal parçaya ya da metal muadiline yönlendiririz. Sınırı önceden söylemek, sonradan sorun çıkarmaktan iyidir.</p>
<p>Aynı dürüstlük ölçü konusunda da geçerli: elinizde hiçbir numune yoksa ve parçanın takıldığı yuvayı da göremiyorsak, tahmine dayalı üretim yapmayız.</p>
<h2>Sipariş</h2>
<p>Parça ölçüsü netleştikten sonra siparişi doğrudan sitemizden verebilirsiniz; ölçüye özel işler dahil kartla online ödeme açıktır. Ölçüden emin değilseniz ya da parçanın kapsamımıza girip girmediğini merak ediyorsanız, önce WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Kırılan parçanın birkaç fotoğrafı ve takıldığı yerin görüntüsü, çoğu zaman ilk değerlendirme için yeterli olur.</p>
<p>Elinizdeki scooter parçası aslında daha geniş bir işin küçük bir örneği: gövde plastiği kırılan araçlarda aynı yöntemi uyguluyoruz. İki tekerlekli araçlarda benzer bir ihtiyacınız varsa <a href="/motosiklet-plastik-parca-ozel-uretim/">motosiklet plastik parça özel üretim</a> sayfamıza göz atabilir, elinizde parçalanmış bir gövde varsa <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parçadan yenisini yaptırma</a> akışını inceleyebilirsiniz. Sorun tek bir kapak değil de kapağı yerinde tutan bağlantıysa, <a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe üretimi</a> tarafı tam olarak bu iş içindir.</p>""")


def _isiya_dayanikli_plastik_parca_uretimi():
    return (u"""<h1>Isıya Dayanıklı Plastik Parça: Doğru Malzemeyle Ölçüye Özel Üretim</h1>
<p>Bir parça sıcakta çalışacaksa mesele artık şekli değil, malzemesidir. Fırın çevresindeki bir tutamak, kombi yakınındaki bir kelepçe, motor bölmesinde duran bir kablo yatağı ya da rezistanslı bir cihazın gövde içindeki ayağı — hepsi normal koşullarda sorunsuz görünür, sıcak birkaç saat sürekli kaldığında yumuşar, sarkar, deliği ovalleşir ve vidayı tutamaz hale gelir. Çoğu kişi parçanın kırıldığını sanır; aslında parça erimemiş, sadece sürekli çalışma sıcaklığının üstünde bir malzemeden yapılmıştır.</p>
<p>Bu tip parçaların piyasada bulunamamasının iki sebebi var. Birincisi, sıcak bölgedeki parçalar genelde cihaza özeldir: üretici onu ayrı bir yedek parça olarak satmaz, komple modül olarak satar ya da hiç satmaz. İkincisi, benzerini bulsanız bile aynı ölçüde ama yanlış sınıf plastikten olur; ilk ısınma döneminde aynı yerden aynı şekilde bozulur. Sıcağa dayanıklı plastik parça arayan çoğu insan, aslında ölçü değil malzeme arıyordur.</p>
<p>PRUVO'da yaptığımız iş tam olarak burada başlar. Isıya dayanıklı plastik parça üretimi bizde tek bir soruyla kurulur: bu parça, günlük kullanımda kaç dereceye kadar ısınan bir yerde, ne kadar süre duracak? Cevabına göre malzeme sınıfını seçer, duvar kalınlığını ve iç yapısını o sıcaklıkta biçim koruyacak şekilde ayarlar, ölçüyü numunenizden ya da verdiğiniz ölçü listesinden çıkarırız. Yüksek sıcaklık plastik seçimi tahmine değil, parçanın gerçek konumuna dayanır. Ölçü sizden, üretim bizden.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir</strong> — Bozulan, yumuşayan ya da deforme olan parçayı elinize alın. Elinizde parça kalmadıysa yerinden çekilmiş net fotoğraflar ve kaba ölçüler de yeterli olur. Bize parçanın nerede durduğunu da söyleyin: fırın kapağı yanı mı, motor bölmesi mi, kombi hattı mı.</li>
<li><strong>Ölç</strong> — Kritik ölçüleri, delik merkezlerini, vida yuvalarını ve oturma yüzeyini çıkarırız. Aynı anda çalışma sıcaklığını konuşuruz; sürekli sıcaklık, kısa süreli tepe sıcaklıktan daha belirleyicidir.</li>
<li><strong>Üret</strong> — Seçilen malzeme sınıfıyla ölçüye özel üretiriz. Tek adet de olur, aynı parçadan birkaç yedek de.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Sürekli çalışma sıcaklığına göre malzeme sınıfı:</strong> PETG, ASA ya da takviyeli PA-CF. Seçim parçanın durduğu yere göre yapılır, "en iyi malzeme" diye tek bir cevap yoktur.</li>
<li><strong>Duvar kalınlığı ve iç yapı yoğunluğu:</strong> ısı altında biçim koruma bunlara bağlıdır; sıcak bölgede duran parçayı daha kalın cidar ve daha yoğun iç yapıyla çıkarırız.</li>
<li><strong>Ölçü ve tolerans:</strong> numuneden birebir ya da verdiğiniz ölçü listesinden; sıkı geçmesi gereken yüzeyi ayrıca konuşuruz.</li>
<li><strong>Delik çapı, vida yuvası ve gömme yuva derinliği:</strong> mevcut cıvata ve vidalarınızla uyumlu olacak şekilde.</li>
<li><strong>Farklı renk seçenekleri:</strong> görünür yerde duran parçalarda renk uyumu için.</li>
<li><strong>Tek adet ya da küçük seri:</strong> aynı sıcak noktada birden fazla parça varsa hepsi birlikte çıkar.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme merdiveni sıcaklığa göre yukarı çıkar. Standart sınıf plastikler oda koşulunda iyidir ama ısınan hiçbir bölgeye girmez; güneş altında kalan bir kapakta bile yumuşamaya eğilimlidir. <strong>PETG</strong>, ılık ortamlar ve düzenli ısınıp soğuyan gövde içi parçalar için ilk sağlam adımdır. <strong>ASA</strong>, dış ortamda güneş ve UV ile birlikte ısı gören yerlerde tercih edilir; rengini ve sertliğini uzun süre korur. Parça kapalı bir gövde içinde değil de doğrudan güneş altında duruyorsa asıl konu sıcaklık bandı değil renk ve yüzey sabitliğidir; bu tarafı <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekan parça üretimi</a> sayfamızda ayrıca anlattık. Sıcakla birlikte mekanik yük ya da titreşim varsa — motor bölmesi plastik parça malzemesi seçiminde sık karşılaştığımız durum — karbon ya da cam elyaf takviyeli <strong>PA-CF / PA-GF</strong> sınıfına çıkarız; bu sınıf hem biçimini daha yüksek sıcaklıkta korur hem de eğilmeye direnir.</p>
<p>Fırın çevresi plastik parça işlerinde çoğu zaman mesafe belirleyicidir: kapaktan on santim uzaktaki bir tutamak ile sıcak yüzeye değen bir ayak aynı parça değildir. Bu yüzden malzeme kararını parçanın adına göre değil, konumuna göre veririz.</p>
<h2>Dürüst sınır</h2>
<p>Plastiğin sıcaklık sınırı vardır ve bunu önden söyleriz. Malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; bu aralık gövde içi, kombi yakını, fırın çevresi ve motor bölmesindeki birçok parça için yeterlidir. Ama alev teması olan, kızgın metal yüzeye değen, rezistans üstünde ya da egzoz hattına yakın duran noktalarda plastik parça önermiyoruz — orada doğru cevap metaldir ve bunu size söyleriz, iş almak için "olur" demeyiz.</p>
<p>Ara bölge de vardır: kısa süreli tepe sıcaklığı yüksek ama sürekli sıcaklığı ılımlı olan yerler. Böyle bir noktada malzeme sınıfını bir kademe yukarı alıp cidarı kalınlaştırarak çözüm üretebiliriz; çözümün nerede durduğunu da açıkça belirtiriz. Ölçüyü ve parçanın tam konumunu bize ilettiğinizde, sınırın hangi tarafında olduğunuzu üretime girmeden önce öğrenirsiniz.</p>
<h2>Sipariş</h2>
<p>Sitemizde kartla online ödeme var; ölçüye özel işler dahil siparişinizi doğrudan verebilirsiniz. Parçanızın sıcak bölgede tam olarak nerede durduğundan emin değilseniz, önce WhatsApp danışma hattımızdan yazın: <strong>+90 545 138 6526</strong>. Fotoğrafı ve kaba ölçüyü gönderin, hangi malzeme sınıfının uygun olduğunu ve işin plastikle çözülüp çözülmeyeceğini söyleyelim.</p>
<p>Sınıflar arasındaki farkı yan yana görmek isterseniz <a href="/malzeme-rehberi/">malzeme rehberi sayfamız</a> tüm seçenekleri karşılaştırmalı olarak anlatıyor. Parçanız bir ısıtma-soğutma hattının üstündeyse <a href="/klima-kombi-havalandirma-plastik-parca-uretimi/">klima, kombi ve havalandırma parçaları için hazırladığımız sayfaya</a> göz atın; fırın, bulaşık makinesi ya da kurutucu gibi bir cihazın içinden çıkan bir parçadan söz ediyorsak <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya parçası üretimini anlattığımız sayfa</a> doğrudan sizin durumunuza değiniyor. Parçayı zorlayan kuru sıcaklık değil de sıcak su ve buharsa <a href="/sicak-su-ve-buhar-temasli-plastik-parca-uretimi/">sıcak su ve buhara dayanıklı parça üretimi</a> sayfası o koşulu ayrı ele alıyor.</p>""")


def _uv_gunes_dayanikli_dis_mekan_plastik_parca_uretimi():
    return (u"""<h1>Dış Mekan Plastik Parçası: UV Dayanımlı Malzemeyle Ölçüye Özel Üretim</h1>
<p>Balkon korkuluğundaki kapak, bahçe sulama hattının klipsi, tente kolunun ucundaki tutucu, çatı olukunun bağlantı pabucu… Bu parçaların hepsinin ortak bir kaderi var: iki üç yaz mevsimi sonunda önce rengi kaçar, sonra elinizde kalır. Sebebi kırılganlık değil, güneş. Sürekli ultraviyole altında kalan sıradan plastik moleküler olarak yorulur; önce sararır, sonra camlaşır ve en küçük darbede parçalanır. Yağmur ve gece–gündüz arasındaki sıcaklık farkı bu yorulmayı hızlandırır. Kırılan parçayı elinize aldığınızda kenarların toz gibi ufalandığını görürsünüz — o parça artık esnemiyordur.</p>
<p>Asıl sorun, bu parçaların çoğunun tek başına satılmamasıdır. Tente üreticisi yıllar önce modeli değiştirmiş, bahçe sulama setinin markası piyasadan çekilmiş, çatı sisteminin yedeği ancak komple set halinde geliyordur. Bir avuç içi kadar tutucu için tüm sistemi yenilemek zorunda kalmak hem pahalı hem gereksizdir. İşte bu yüzden <strong>güneşe dayanıklı dış mekan plastik parça üretimi</strong> bizim en sık gelen taleplerimizden biri. Elimize gelen kırık parçayı ölçer, aynı geometriyi UV dayanımlı malzemede yeniden üretiriz. Güneşin yanına klorlu suyun da eklendiği yerde — havuz süpürgesi tekerleği, skimmer kapak mandalı, merdiven tutucusu — sınıf seçimi biraz daha daralır; o parçalar için <a href="/havuz-ekipmani-plastik-parca-yaptirma/">havuz ekipmanı plastik parça yaptırma</a> sayfamız ayrı yazıldı.</p>
<p>PRUVO olarak yaptığımız iş, mevcut parçayı taklit etmek değil; onu doğru malzemeye taşımaktır. <strong>Güneşte sararmayan plastik parça</strong> arayan bir kullanıcı aslında iki şey ister: renk sabitliği ve yıllar sonra hâlâ esneyebilen bir gövde. ASA gibi dış mekan için geliştirilmiş malzemeler bunu sağlar. <strong>Bahçe plastik parça yaptırma</strong>, <strong>tente parçası özel üretim</strong> ya da <strong>çatı ve cephe plastik aksesuar</strong> ihtiyacınız olsun, akış aynıdır ve tek cümleyle özetlenir: Ölçü sizden, üretim bizden.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırık parçayı, parçaların hepsini ya da sadece fotoğrafını gönderin. Elinizde hiçbir şey kalmadıysa monte olduğu yerin fotoğrafı ve birkaç kaba ölçü de yeter; gerisini biz çıkarırız. Kırık iki yarım, tek parçadan daha iyidir — kırılma yüzeyi kesit hakkında bilgi verir.</li>
<li><strong>Ölç.</strong> Dış ölçüleri, montaj delik çaplarını, delikler arası mesafeyi ve varsa açıları kumpasla tek tek alırız. Parçanın hangi yöne baktığını, gün içinde ne kadar güneş gördüğünü ve üzerine kaç kilo geldiğini sorarız; malzeme kararı bu üç cevaptan çıkar.</li>
<li><strong>Üret.</strong> Onayladığınız ölçü ve malzemeyle özel tasarım üretim yaparız. Tek adet de üretiriz, aynı parçadan on iki tane de. Zayıf gördüğümüz noktaya kaburga ekler, duvar kalınlığını orijinalinden biraz artırırız — çünkü kırılan parça zaten bir kere zayıf çıkmıştır.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>UV ve hava koşuluna göre malzeme seçimi:</strong> ASA veya PETG. Parçanın gün boyu doğrudan güneş görüp görmediğine, yağmurda kalıp kalmadığına göre seçilir.</li>
<li><strong>Dış yüzey renk seçenekleri:</strong> farklı renk seçenekleri sunuyoruz. Açık renkler güneş altında belirgin biçimde daha az ısınır; koyu renk isteyen müşteriye bunu peşinen söyleriz.</li>
<li><strong>Duvar kalınlığı ve takviye kaburgası:</strong> orijinali ince olduğu için kırıldıysa gövdeyi kalınlaştırır, iç tarafa görünmeyen kaburgalar ekleriz. Dışarıdan aynı parça, içeride ek destek.</li>
<li><strong>Ölçü ve tolerans:</strong> kırık parçadan birebir kopyalayabilir ya da sizin verdiğiniz ölçü listesine göre üretebiliriz. Geçme yerlerinde sıkı mı gevşek mi olsun, siz söylersiniz.</li>
<li><strong>Montaj deliği çapı ve delikler arası mesafe:</strong> mevcut vidalarınıza göre ayarlanır; delik yerini kaydırmak veya ilave delik açmak da mümkündür.</li>
<li><strong>Adet:</strong> tek adet ya da küçük seri. Sitedeki tüm korkulukların kapakları gidiyorsa hepsini birden üretmek adet başına daha mantıklıdır.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme merdivenimizin en altında standart plastikler var; bunlar iç mekan, kuru ve gölge işler için uygundur ve dış mekanda kullanılmaz. Bir üst kademe dış koşul sınıfıdır: <strong>PETG</strong> yağmura ve neme dayanır, kısmi güneş gören yerlerde iş görür. <strong>ASA</strong> bu sayfanın asıl malzemesidir — sürekli güneş altında renk ve mukavemet koruması için geliştirilmiştir, tente ve cephe parçalarında ilk tercihimizdir.</p>
<p>Parça aynı zamanda yük taşıyor veya sürekli titreşim altındaysa merdivenin en üstüne çıkarız: <strong>karbon ve cam elyaf takviyeli PA-CF / PA-GF</strong>. Bunlar rijitliği ve boyut kararlılığını belirgin biçimde yükseltir. Hangi kademede duracağımıza parçanın çalıştığı yere bakarak birlikte karar veririz; gereğinden pahalı malzeme önermeyiz. Parçanız güneşin yanı sıra sürekli sıcak bir noktada da duruyorsa — motor bölmesi, fırın çevresi, kombi hattı gibi — malzeme kararı bu kez sıcaklığa göre verilir; o tarafın ayrıntısı <a href="/isiya-dayanikli-plastik-parca-uretimi/">ısıya dayanıklı plastik parça üretimi</a> sayfamızdadır.</p>
<h2>Dürüst sınır</h2>
<p>UV dayanımlı malzemelerde bile yıllar içinde hafif bir renk açılması görülebilir. Bu normaldir ve mekanik dayanımı etkilemez: parça soluklaşır ama kırılganlaşmaz. Sıradan plastikte olan ise farklıdır; orada sararma çöküşün habercisidir.</p>
<p>İkinci sınır yük tarafındadır. Sürekli güneş altında ağırlık taşıyan gerçek bir taşıyıcı eleman — ana kol, taşıyıcı ayak, yük altındaki kiriş — gerekiyorsa doğru seçim metaldir, bunu açıkça söyleriz. Plastik profil ve kiriş ancak hafif, yük dışı işlerde anlamlıdır. Bizim üstlendiğimiz taraf örtü, tutucu, klips, kapak ve muhafazadır: sistemi ayakta tutan değil, sistemi tamamlayan parçalar. Bu ayrımı baştan yapmak, iki yıl sonra aynı şikâyetle karşılaşmamızı önler.</p>
<h2>Sipariş</h2>
<p>Sitemizden kartla online ödeme yapabilirsiniz; ölçüye özel üretilen parçalar da buna dahildir. Ölçüden emin değilseniz ya da parçanın hangi malzemede olması gerektiğini konuşmak isterseniz WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Kırık parçanın ve monte olduğu yerin fotoğrafını gönderin, uygun malzemeyi ve süreyi size söyleyelim.</p>
<p>Hangi malzemenin hangi koşulda ne kadar dayandığını daha geniş bir çerçevede görmek isterseniz <a href="/malzeme-rehberi/">malzeme rehberimiz</a> iyi bir başlangıç noktasıdır. Güneş gören bir panoyu, sayacı veya elektrik kutusunu koruyacak bir gövde arıyorsanız <a href="/olcuye-ozel-koruma-kapagi-muhafaza-uretimi/">ölçüye özel koruma kapağı ve muhafaza üretimi</a> sayfamıza bakın. Tente kolunu ya da bimini borusunu tutan aparat kırıldıysa ve parça bir de tuzlu havada duruyorsa <a href="/tekne-tentesi-bimini-guverte-aparati-ozel-uretim/">tekne tentesi ve bimini aparatı özel üretim</a> sayfası tam o parçalara ayrıldı. Kırılan parçanın markası piyasadan çekilmişse ya da yedeği hiçbir yerde bulunmuyorsa <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretim</a> hizmetimiz tam olarak bu durum için var. Aradığınız parça dış cephede güneş gören kapı ve pencere donanımıysa — ispanyolet kapağı, sineklik mandalı, panjur makarası, köşe takozu — <a href="/pvc-dograma-kapi-pencere-plastik-parca-uretimi/">PVC doğrama kapı ve pencere plastik parça üretimi</a> sayfamız doğrudan bu parçalara ayrıldı.</p>""")


def _parca_olcusu_nasil_alinir_ve_gonderilir():
    return (u"""<h1>Parça Ölçüsü Nasıl Alınır? Ölçü Gönderme Rehberi</h1>
<p>Elinizde artık üretilmeyen bir parça var. Kırılmış, aşınmış ya da hiç bulunamıyor. Özel üretim yaptırmaya karar verdiniz, sonra tek bir soruda takıldınız: parça ölçüsü nasıl alınır, hangi ölçüleri nasıl göndermek gerekir? Bu soru göründüğünden daha kritiktir, çünkü özel üretimin tamamı sizin verdiğiniz sayıların üzerine kurulur. Ölçü doğruysa parça ilk seferde oturur; ölçü eksikse üretim gecikir, yanlışsa parça çalışmaz. Takvim de tam buraya bağlıdır: süre sayacı ölçü onayıyla başlar, kademelerin gerçekçi aralıklarını <a href="/ozel-parca-kac-gunde-hazir-olur/">özel parça kaç günde hazır olur</a> sayfasında bulabilirsiniz.</p>
<p>Piyasada bu iş genelde "teknik çizim gönderin" diye karşılanır. Oysa müşterilerin çok büyük bölümünde teknik çizim yoktur, çoğu zaman kumpas bile yoktur. Elde sadece kırık bir kapak, yuvasından çıkmış bir burç ya da telefonla çekilmiş bir fotoğraf vardır. Kumpas olmadan ölçü alma da, kırık parçanın ölçüsü nasıl çıkarılır sorusu da tamamen çözülebilir işlerdir — yeter ki hangi beş altı sayının gerçekten gerektiğini bilin. Özel üretim için hangi ölçüler gerekir sorusunun cevabı kısadır ve bu sayfada tek tek listelenmiştir. Hâlâ parçanın üzerinde bir kod ya da numara arıyorsanız <a href="/yedek-parca-kodu-bilinmiyorsa-ne-yapilir/">yedek parça kodu bilinmiyorsa ne yapılır</a> sayfası kod çıkmadığında ölçüyle nasıl ilerlendiğini gösteriyor.</p>
<p>PRUVO'da işleyiş nettir: <strong>Ölçü sizden, üretim bizden.</strong> Siz parçayı ölçer ya da parçanın kendisini ulaştırırsınız, biz ölçüyü yazılı olarak teyit eder, malzemeyi kullanım yerine göre seçer ve ölçüye özel üretiriz. Aşağıdaki rehber, ölçüyü doğru almanız ve tek seferde göndermeniz için yazıldı.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Parçanın kendisini ulaştırabiliyorsanız en sağlıklısı budur; kırık da olsa gönderin, parçalar birleştirilerek ölçü çıkarılır. Gönderemiyorsanız fotoğraf yeterlidir: parçayı düz bir zemine koyun, tepeden dik açıyla ve yanından olmak üzere en az iki kare çekin. Yanına bir cetvel ya da bilinen ölçüde bir nesne (kredi kartı, madeni para) koymanız ölçeği doğrular.</li>
<li><strong>Ölç.</strong> Kumpasınız varsa doğrudan kullanın. Yoksa cetvel ve şerit metre iş görür: parçayı A4 kağıdın üstüne koyup kalemle çevresini geçirin, sonra kağıt üzerinden ölçün — bu yöntem elde tutup ölçmekten çok daha isabetlidir. Delik çapı için deliğe geçen bir matkap ucu ya da vidayı deneyip onun çapını okuyabilirsiniz. Delik merkez mesafesi nasıl ölçülür sorusunun pratik cevabı: iki deliğin dış kenarları arasını ölçün, sonra bir delik çapı kadar çıkarın; sonuç merkezden merkeze mesafedir.</li>
<li><strong>Üret.</strong> Ölçüleri WhatsApp'tan ya da sipariş notundan iletirsiniz. Biz listeyi yazılı olarak size geri okuruz, onaydan sonra üretim yapılır ve parça adresinize ulaşır.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Her parçada bize gereken sayılar bunlardır. Hepsini milimetre cinsinden verin, virgüllü değer varsa yuvarlamayın:</p>
<ul>
<li><strong>Toplam en, boy ve kalınlık</strong> — parçanın dış sınırları. Kalınlık en çok atlanan ölçüdür, mutlaka yazın.</li>
<li><strong>Delik çapı ve delikler arası mesafe (merkezden merkeze)</strong> — montaj noktalarının tuttuğu tek şey budur; delik sayısını ve yerleşimini de belirtin.</li>
<li><strong>Mil/şaft geçme çapı</strong> — parçanın oturacağı milin çapı. Milin kendisini ölçmek, deliği ölçmekten daha güvenilirdir.</li>
<li><strong>Dişli parçalarda diş sayısı ve dış çap</strong> — dişleri fotoğraftan sayabiliyorsak sorun yok, sayamıyorsanız diş sayısını siz sayın; bu iki sayının dişin büyüklüğünü nasıl verdiğini <a href="/kirik-dislinin-modulu-nasil-bulunur/">kırık dişlinin modülü nasıl bulunur</a> sayfasında gösterdik.</li>
<li><strong>Kayış-kasnak parçalarında diş aralığı ve genişlik</strong> — kayışın üstündeki yazı (GT2, HTD gibi) varsa aynen aktarın; yazı silinmişse <a href="/kayis-profili-nasil-belirlenir-gt2-htd-t5/">kayış profili nasıl anlaşılır</a> sayfasındaki iki diş arası ölçümü profili verir.</li>
<li><strong>Halka/conta parçalarda iç çap, dış çap ve kalınlık</strong> — üç sayı da şarttır, ikisi tek başına yeterli değildir.</li>
<li><strong>Tolerans beklentisi</strong> — sıkı geçme mi istiyorsunuz, boşluklu mu? "Elle zor girsin" ya da "rahat dönsün" demeniz bile yeterli bilgidir.</li>
<li><strong>Kullanım yeri</strong> — dışarıda mı, motor yanında mı, deniz ortamında mı, yük taşıyacak mı? Bu, malzeme seçimini belirler.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Aynı ölçü, farklı malzemelerle bambaşka bir parça verir. Kapalı ortamda, ısı ve yük görmeyen parçalarda standart malzeme yeterlidir. Güneş altında, dış cephede, motor bölgesinde ya da tuzlu havada duracak parçalarda ısı ve UV dayanımı olan PETG veya ASA tercih edilir. Yük taşıyan, burulan, dişli gibi sürekli temas eden parçalarda ise karbon ya da cam elyaf takviyeli PA-CF / PA-GF grubuna çıkarız. Farklı renk seçenekleri mevcuttur; renk tercihini de ölçü listenize ekleyebilirsiniz. Kullanım yerini yazmanız, bizim sizin yerinize doğru malzemeyi seçmemizi sağlar.</p>
<h2>Dürüst sınır</h2>
<p>Kırık parçanın eksik bir bölümü varsa oradaki ölçü tahmine dayanır — bunu size açıkça söyleriz, sessizce doldurup "oldu" demeyiz. Simetriden ya da karşı parçadan yola çıkarız, ama tahmin olduğunu bilerek ilerlersiniz. Milimetrenin altında hassasiyet isteyen geçmelerde ilk parçayı deneme olarak üretip ölçüyü birlikte oturturuz; tek hamlede mikron tutturma sözü vermeyiz. Ölçü yanlış verilirse parça yanlış çıkar, bu basittir ve kimsenin işine yaramaz. Bu yüzden üretim öncesi tüm ölçüleri yazılı olarak teyit eder, onayınızı almadan üretime geçmeyiz. Teyitten sonra bir sapma çıkarsa koşul açıktır: sapma bizim aldığımız ölçüden kaynaklanıyorsa revizyon bizdendir, ayrıca ücret istemeyiz; ölçüyü siz değiştirirseniz bu yeni bir iş olarak fiyatlandırılır. Ayrıca parçanın çalışacağı yere göre plastiğin sınırını da söyleriz: pervane biçimli parçalar fan veya hafif çark olarak iş görür, tekne itişi için değildir; profil ve kirişler hafif, yük dışı kullanımda kalır; contalar düşük–orta basınç aralığında güvenlidir; dişlilerde yüke göre takviyeli malzemeye çıkılır.</p>
<h2>Sipariş</h2>
<p>Ölçü listeniz hazırsa sipariş vermek kolaydır. Sitemizden kartla online ödeme yapabilirsiniz; ölçüye özel işler de dahil olmak üzere ödeme adımı doğrudan site üzerinden tamamlanır. Ölçüden emin değilseniz ya da hangi sayıyı vereceğinizi çözemediyseniz önce WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Parçanın fotoğrafını gönderin, hangi ölçüleri nasıl alacağınızı adım adım söyleyelim. Ölçü teyidi yazılı yapılır, böylece iki taraf da aynı sayılara bakar.</p>
<p>Parçayı ölçmek yerine doğrudan elimize ulaştırmak istiyorsanız <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> sayfasındaki akış tam size göredir; ölçüyü biz çıkarırız. Halka ve sızdırmazlık parçalarında iç çap, dış çap ve kalınlık üçlüsünü nasıl kullandığımızı görmek için <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> sayfasına göz atın. Süre, ödeme ve teslimat gibi kalan sorularınızın cevapları ise <a href="/sss/">sıkça sorulan sorular</a> bölümünde toplandı.</p>""")


def _ozel_parca_uretimi_fiyati_nasil_belirlenir():
    return (u"""<h1>Özel Parça Üretiminde Fiyatı Ne Belirler?</h1>
<p>Elinizde piyasada karşılığı olmayan bir parça var: kırılmış bir tutucu, aşınmış bir dişli, kaybolmuş bir kapak. İlk sorunuz da çok doğal olarak şu oluyor: bunun bedeli ne olur? Özel parça üretimi fiyatı nasıl hesaplanır sorusunun tek satırlık bir cevabı yok; çünkü seri üretimde fiyatı belirleyen kalıp ve stok mantığı, tek parçalık ya da küçük adetli işlerde geçerli değildir. Burada fiyatı belirleyen şey rafta bekleyen bir ürünün etiketi değil, sizin parçanızın ölçüsü, çalışacağı yer ve dayanması gereken koşuldur.</p>
<p>Piyasada bu parçayı bulamamanızın nedeni de aynı: üretici o modeli kapatmış, yedek parça akışı durmuş ya da parça hiç ticari olarak satılmamış, bir makinenin içinde doğmuş. Bayiye sorduğunuzda "komple grup" fiyatı çıkıyor; oysa ihtiyacınız olan tek bir küçük eleman. Özel parça yaptırma ne kadar tutar diye araştıran çoğu kişi, aslında kıyaslanabilir bir referans arıyor. Biz de bu sayfada fiyat listesi vermek yerine, teklifinizi oluşturan değişkenleri açıkça anlatıyoruz — böylece ölçüye özel üretim fiyatı size kapalı bir kutu gibi gelmiyor.</p>
<p>PRUVO'nun işi tam olarak burada başlıyor. Ölçü sizden, üretim bizden. Numunenizi, fotoğrafınızı ya da hazır dosyanızı alırız; parçayı ölçer, malzemesini çalışacağı yere göre seçer ve size net bir rakam veririz. Tek parça üretim maliyeti ile on adetlik bir işin birim maliyeti farklıdır ve bunu da teklifte ayrı ayrı görürsünüz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<ol>
<li><strong>Getir.</strong> Kırık parçayı, benzerini ya da ölçülü bir fotoğrafını gönderin. Elinizde teknik çizim veya hazır dosya varsa doğrudan onu kullanırız. Teklif için ne göndermeliyim diye düşünüyorsanız cevap kısa: parçanın kendisi en iyisi, olmuyorsa yanına cetvel/kumpas koyarak çekilmiş net fotoğraflar ve kritik ölçüler yeter.</li>
<li><strong>Ölç.</strong> Dış ölçüleri, delik çaplarını, diş adımlarını ve oturma yüzeylerini çıkarırız. Parçanın nerede, hangi yüke ve sıcaklığa maruz çalıştığını sorarız; çünkü bu bilgi hem malzemeyi hem fiyatı doğrudan etkiler.</li>
<li><strong>Üret.</strong> Onaylı ölçü ve malzemeyle özel tasarım üretim yapılır. İlk numunede ölçü tutmazsa revizyon turunu konuşur, düzeltir ve gönderiyi ona göre planlarız.</li>
</ol>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Fiyatı oluşturan kalemler soyut değil; hepsi sizin verdiğiniz girdiye bağlı somut ayarlardır:</p>
<ul>
<li><strong>Parça hacmi ve dış ölçüleri.</strong> Fiyatın en büyük tek bileşeni budur; büyüyen hacim hem malzeme hem üretim süresi demektir.</li>
<li><strong>Malzeme sınıfı.</strong> Standart iç mekân malzemesi mi, ısı/UV/nem gören PETG-ASA mı, yoksa yüksek mukavemet için karbon veya cam elyaf takviyeli PA-CF / PA-GF mi? Sınıf yükseldikçe birim maliyet artar, dayanım da artar.</li>
<li><strong>Dayanım seviyesi.</strong> Dekoratif bir kapak ile yük taşıyan bir braket aynı iç yapıyla üretilmez. Dayanım isteği arttıkça malzeme ve süre artar.</li>
<li><strong>Adet.</strong> Adet arttıkça birim maliyet düşer; hazırlık bir kez yapılır, aynı ölçü tekrar tekrar üretilir. Bu yüzden "şimdilik bir tane" ile "yılda yirmi tane" farklı fiyatlanır.</li>
<li><strong>Ölçü girdisinin hazır olup olmaması.</strong> Numune elimizdeyse en hızlısı ve en ucuzu; fotoğraf + ölçü ile de çalışırız; hazır dosya gelirse ölçü çıkarma adımı tamamen düşer.</li>
<li><strong>Revizyon turu.</strong> İlk denemede oturması beklenen sade geometrili parçalarda ek tur çıkmaz; karmaşık geometride bir deneme turu fiyata dahil edilir, baştan söyleriz.</li>
<li><strong>Farklı renk seçenekleri.</strong> Renk tercihi çoğu işte fiyatı değiştirmez; özel bir ton isteniyorsa bunu teklifte ayrıca belirtiriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme seçimi, fiyatın en çok tartışılan kalemi olduğu için kısa bir merdivenle anlatalım. İç mekânda, güneş görmeyen, ısınmayan, yük almayan parçalarda standart malzeme yeterlidir ve en ekonomik seçenektir. Dışarıda duran, güneş altında kalan, sıcak-nemli ortamda ya da deniz koşulunda çalışan parçalarda PETG veya ASA sınıfına çıkarız; burada maliyet bir kademe artar ama parça ömrü belirgin şekilde uzar. Titreşim, darbe, sürekli yük ya da vidalı bağlantıya oturan kritik parçalarda karbon veya cam elyaf takviyeli PA-CF / PA-GF öneririz; bu en pahalı sınıftır ve gerekmedikçe önermeyiz. Ucuz malzemeyle üretilip altı ay sonra yenisi istenen parça, doğru malzemeyle bir kez üretilenden pahalıya gelir.</p>
<h2>Dürüst sınır</h2>
<p>Bu sayfada sabit fiyat listesi vermiyoruz ve bunu bilerek yapıyoruz: ölçüsüz verilen fiyat tahmini yanıltıcıdır, sonra da ya bizi ya sizi zor durumda bırakır. Kesin fiyat, ölçü ve malzeme netleştiğinde çıkar; genellikle numune veya ölçülü fotoğraf elimize geçtikten sonra kısa sürede. Takvim de aynı ana bağlıdır: sayaç ölçü onayıyla başlar, <a href="/ozel-parca-kac-gunde-hazir-olur/">hangi kademenin ne kadar sürdüğünü</a> ayrı bir sayfada kademe kademe yazdık.</p>
<p>İkinci sınır adetle ilgili: adet çok yükseldiğinde başka bir üretim yöntemi sizin için daha ekonomik olabilir. Böyle bir durumda bunu açıkça söyleriz, işi zorlamayız.</p>
<p>Üçüncüsü malzemenin fiziksel sınırı. Pervane benzeri parçalarda fan ve hafif çark işini karşılarız, tekne itişi gibi gerçek itki uygulamaları bu malzemelerin işi değildir. Profil ve kiriş türü parçalarda hafif, yük dışı kullanımlar uygundur. Contalarda düşük–orta basınç aralığı gerçekçidir. Dişlilerde yüke göre takviyeli sınıfa çıkmak gerekir; bu da fiyatı yukarı taşır. Parçanız bu sınırların dışındaysa fiyat vermeden önce söyleriz; hangi iş tiplerini hiç almadığımızı <a href="/hangi-parcalar-ozel-uretimle-yapilamaz/">hangi parçalar özel üretimle yapılamaz</a> sayfasında tek tek yazdık.</p>
<h2>Sipariş</h2>
<p>Ölçüsü ve malzemesi netleşen işlerde ödemeyi sitemizden kartla online yapabilirsiniz; ölçüye özel işler de buna dahildir, ayrı bir ödeme yöntemi aramanız gerekmez. Fiyat öncesi danışmak, ölçü göndermek veya parçanızın uygun olup olmadığını sormak isterseniz WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Fotoğrafı ve ölçüyü aynı mesajda gönderirseniz teklif en hızlı şekilde çıkar.</p>
<p>Maliyetin büyük kısmını malzeme kararı belirlediği için, teklifi beklerken <a href="/malzeme-rehberi/">malzeme rehberimize göz atıp parçanızın çalışacağı koşula hangi sınıfın uyduğunu</a> önceden görebilirsiniz. Tek bir adet için fiyatın nasıl oluştuğunu ve neden birim maliyetin daha yüksek çıktığını merak ediyorsanız <a href="/tek-adet-ozel-parca-uretimi/">tek adet özel parça üretimi sayfamız</a> bu tarafı ayrıntılı anlatıyor. Elinizde kırık orijinal varsa en net teklif oradan çıkar; <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi akışını</a> okuyup parçayı nasıl göndereceğinizi baştan planlayabilirsiniz.</p>""")


def _olcuye_ozel_distans_ara_pul_uretimi():
    return (u"""<h1>Aradaki milimetreyi tutturan ara pulu ölçünüze göre üretiyoruz</h1>
<p>Ses küçüktür. Tezgâhın altına eğilmiş, gövdeyi yerine oturtmak için bağlantıyı hafifçe sıkarsınız; parmağınızın altından kuru bir çatırtı gelir ve iki yüzey arasındaki o ince halka ikiye ayrılır. Parçalar zemine düşer, yan yana konur, dönmez. Sonrası tanıdıktır: gövde birkaç milimetre aşağı oturur, kayış hizadan çıkar, kapak sürtmeye durur, titreşim artar. Aradığınız şey artık büyük bir parça değil, iki yüzey arasındaki boşluğu tutan tek bir halkadır — ve o halkanın ölçüsü çoğu zaman hiçbir katalogda yazmaz.</p>
<p>Ardından kutudaki standart ölçüler denenir. İç çap tutar, dış çap taşar. Dış çap tutar, kalınlık ince kalır ve boşluk kapanmaz. İki tanesi üst üste konur, bu kez fazla gelir. Piyasadaki hazır ölçüler bir merdivenin sabit kademeleridir; sizin ihtiyacınız çoğu zaman iki kademe arasına düşer. İç çap dış çap ölçüsüne göre distans pul yaptırma işini bu yüzden hazır bir rafın değil, sizin verdiğiniz üç ölçünün belirlediği bir üretim olarak ele alıyoruz: iç çap, dış çap, kalınlık.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Elinizde kırık parça varsa en kolayı odur: iki yarımı da saklayın, düz bir zemine koyup üstten net bir fotoğrafını çekin, yanına bir cetvel koyun. Kırık parçanız yoksa da iş durmaz; parçanın oturduğu yuvayı ve içinden geçen bağlantının çapını ölçmeniz yeter. Ölçüyü kumpas ile alabiliyorsanız en iyisi, alamıyorsanız fotoğraf ve kaba ölçüyle de yola çıkarız, kalan farkı biz sorarız.</p>
<p>Ölçüyü nasıl ilettiğiniz de size kalmış: kumpas değerlerini yazabilir, parçanın oturduğu yeri gösteren bir fotoğraf gönderebilir ya da kırık parçanın kendisini bize ulaştırabilirsiniz. Adet de bu adımda netleşir; tek bir halka için de üretim yaparız, aynı hat üzerindeki on beş nokta için de. Aynı montajda birbirinden farklı iki ölçü varsa ikisini tek işte toplarız; ayrı ayrı sipariş vermenize gerek kalmaz.</p>
<p>Ölçüleri aldıktan sonra size tek bir sayfa halinde geri döneriz: iç çap, dış çap, kalınlık, adet ve malzeme önerisi. Onay verdiğinizde üretim sıraya girer. Mesafe parçası distans yaptırma işlerinde en sık yaptığımız şey, tek bir kalınlık yerine birkaç kademeli takım hazırlamaktır; montajda hangisinin oturduğunu görür, doğru olanı yerinde bırakırsınız.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>İç çap:</strong> içinden geçen bağlantının çapını belirler; onda bir milimetrelik fark bile, parçanın merkezde durmasıyla yana kaçması arasındaki farktır.</li>
<li><strong>Dış çap:</strong> yükün yüzeye yayıldığı alanı belirler; dar kalırsa iz bırakır, taşarsa yuvaya oturmaz.</li>
<li><strong>Kalınlık:</strong> aradaki boşluğu birebir kapatan ölçüdür; asıl hizayı bu tutar.</li>
<li><strong>Geçme sıkılığı:</strong> aynı iç çapı serbest geçme ya da elle iterek oturan sıkı geçme olarak ayarlarız; titreşimli yerlerde sıkı geçme parçanın yerinden yürümesini zorlaştırır.</li>
<li><strong>Kenar pahı:</strong> köşenin kırılarak yumuşatıldığı açıdır; yuvaya rahat girmesini ve kenardan çatlak açılmamasını sağlar.</li>
<li><strong>Dış kenar formu:</strong> yuvarlak, altıgen ya da dilimli kenar; dar yuvalarda parmakla tutup çevirebilmek için kenar formunu değiştiririz.</li>
<li><strong>Yandan geçmeli açık form:</strong> bağlantıyı tümüyle sökmeden yandan takılabilen açık (C) kesit; sıkışık montajlarda zaman kazandırır.</li>
<li><strong>Kademeli omuzlu form:</strong> bir tarafı yuvaya girip diğer tarafı yüzeyde kalan iki çaplı yapı; merkezleme gerektiren yerlerde tercih edilir.</li>
<li><strong>Kalınlık takımı:</strong> birbirinden onda bir milimetrelerle ayrılan bir set; ölçüden emin olamadığınız işlerde ikinci bir gönderiyi beklemeden doğru olanı yerinde seçersiniz.</li>
<li><strong>Renk:</strong> farklı renk seçenekleri sunuyoruz; aynı makinede farklı kalınlıkları ayırt etmek için renk kodlaması işinizi kolaylaştırır.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Özel ölçü plastik pul rondela yaptırma işinde malzemeyi parçanın çalışacağı yere göre seçeriz, en pahalısına yönlendirmeyiz. Kuru, kapalı, oda sıcaklığındaki bir mobilya ya da elektronik montajında standart sınıf yeterlidir; parçanın işi boşluk kapatmaksa fazlası masraftır.</p>
<p>Dışarıda kalan, güneş gören, nemli ya da tuzlu havaya maruz yerlerde bir üst kademeye çıkarız: PETG ve ASA sınıfı malzemeler ısı ve UV karşısında formunu daha uzun koruyan seçeneklerdir. Motor çevresi, sürekli titreşim alan bağlantılar, sıkma torkunun yüksek olduğu noktalar ve sertliğin gerçekten belirleyici olduğu işler için karbon ya da cam elyaf takviyeli PA-CF ve PA-GF sınıfına geçeriz. Yağ, deterjan ya da temizlik kimyasalı damlayan noktalarda da seçim ayrı yapılır; parçanın neyle temas ettiğini söylerseniz sınıfı ona göre daraltırız. Hangi sınıfın neden seçildiğini siparişten önce tek cümleyle söyleriz; kararı bilerek verirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Bu sayfadaki iş, yalnızca iç çap, dış çap ve kalınlık ile tanımlanan ara pul, distans ve rondelalardır. Eğimli yüzeyi dengeleyen, makine ayağını seviyeye getiren veya rampa oluşturan parça için <a href="/olcuye-ozel-seviye-simi-ve-takoz-uretimi/">ölçüye özel seviye şimi ve takoz üretimi</a> sayfası uygundur. Kademeli takımları, açık formları, omuzlu geçişleri rahatlıkla üretiriz.</p>
<p>Bu sayfanın kapsamı dışında kalan yerler de açıktır: dönen bir milin ağırlığını taşıyacak yataklama parçaları, dişli geometrileri ve motor içi yüksek sıcaklığa sürekli maruz kalan bileşenler burada anlattığımız ara pul işinden ayrıdır. Bunlar kendi ölçü ve malzeme kararını ister; böyle bir ihtiyacınız varsa ayrı bir iş olarak konuşuruz. Parçanızın çalışacağı yer bu sayfanın sınırının dışındaysa bunu işi aldıktan sonra değil, konuşurken söyleriz. Ölçü sizden, üretim bizden; ama uygun olmayan işe evet demeyiz.</p>
<h2>Sipariş</h2>
<p>Siteden kartla online ödeme yapabilirsiniz; ölçüye özel işler de buna dahildir. Ölçüden emin değilseniz ya da parçanın yerini anlatmak istiyorsanız WhatsApp hattımızdan yazın: <strong>+90 545 138 6526</strong>. Fotoğraf ve kaba ölçü çoğu zaman konuşmayı tek seferde bitirmeye yeter; gerisini biz sorar, ölçüyü birlikte netleştiririz.</p>
<p>Elinizdeki kırık parçadan yola çıkacaksanız <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre parça üretimi</a> sayfasındaki ölçü alma adımları işinizi kolaylaştırır. Aynı montajda ölçüye özel bağlantı elemanı da gerekiyorsa <a href="/olcuye-ozel-vida-somun-civata-uretimi/">ölçüye özel bağlantı elemanı üretimi</a> sayfasına, hangi sınıfın nerede kullanıldığını görmek isterseniz <a href="/malzeme-rehberi/">malzeme rehberimize</a> göz atabilirsiniz.</p>""")


def _olcuye_ozel_raf_pimi_tutucu_uretimi():
    return (u"""<h1>Rafınız oynuyorsa: delik çapına göre raf pimini üretiyoruz</h1>
<p>Raf bir köşesinden aşağı kaymışsa suçlu genelde rafın kendisi değil, yan paneldeki deliğe giren o küçük plastik pimdir. Kırılan pim ayrı satılan bir kalem değildir: çoğu markanın yedek listesinde yer almaz, mobilyanın modeli eskidiyse bulma ihtimali iyice azalır. Nalburda satılan hazır pimler ise tek ölçüde gelir — 5 mm deliğe göre üretilmiş bir pim 7 mm deliğe oturmaz, oturan da rafın kalınlığını kavramaz. Sonu, rafın altına karton sıkıştırmak oluyor; raf yine oynuyor, panel deliği de her yüklenişte biraz daha genişliyor.</p>
<p>Biz o pimi kendi deliğinize göre üretiyoruz. Elinizdeki kırık parçayı gönderin ya da yalnızca bir kumpas ölçüsü iletin; delik çapına göre raf pimi desteği yaptırma işi bu kadar kısa bir alışveriştir. Dolap raf tutucu pim yaptırma taleplerinde en sık gördüğümüz üç durum var: pimin gövdesi kırılmış, taşıma dili kopmuş, ya da mobilyanın modeli piyasadan kalktığı için o özel biçimli tutucu artık satışta bulunmuyor. Üçünde de yol aynı: raf pimi ölçüye özel üretim.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>İlk adım ölçü. Yanınızda kırık pimin parçaları varsa en kolayı odur — kırık halde bile gövde çapını, omuz kalınlığını ve dil uzunluğunu okuyabiliriz. Parça tamamen kaybolduysa iki ölçü yeter: yan paneldeki deliğin çapı ile derinliği, bir de rafın kalınlığı. Telefonla çekilmiş net bir fotoğrafın yanına cetvel koyun, biz üzerinden doğrularız.</p>
<p>İkinci adım biçim. Vitrin raf desteği plastik parça olarak çalışacaksa cam rafı kavrayan kanallı bir dil çizeriz; ahşap ya da sunta rafta çoğu zaman düz platform dili yeterli olur. Rafın önden görünen bir yüzü varsa dili kısa tutup gizleriz.</p>
<p>Üçüncü adım üretim. Ölçüleri üretime almadan önce size yazılı olarak geri okuruz; onay sizden geldikten sonra parçayı üretir, gönderiyoruz. Tek adet de üretiriz, dolabın tamamı için sekiz-on iki adetlik takım da; takım halinde ürettiğimizde tüm pimler aynı ölçüde çıkar, raf düzlemi bir köşeden şaşmaz. Ölçü sizden, üretim bizden.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Pim gövde çapı:</strong> Panele giren kısmın çapı deliğe tam oturmalı; yarım milimetre boşluk rafın oynamasının asıl sebebidir.</li>
<li><strong>Gövde derinliği:</strong> Deliğin dibine dayanan doğru boy, yükü panele düzgün aktarır; kısa kalan pim ağzından zorlanır.</li>
<li><strong>Aşınmış delik telafisi:</strong> Delik zamanla genişlediyse gövde çapını ölçülen gerçek çapa göre büyütür, boşluğu kapatırız.</li>
<li><strong>Omuz çapı ve kalınlığı:</strong> Pimin panele dayandığı yaka, yükü delik ağzına değil geniş bir yüzeye yayar.</li>
<li><strong>Taşıma dili uzunluğu:</strong> Rafın altına ne kadar gireceğini belirler; uzun dil daha çok destek, kısa dil daha az görünür yüzey demektir.</li>
<li><strong>Dil genişliği ve kesiti:</strong> Yük arttıkça kesit kalınlaşır — kırılma çoğunlukla ince kesitli dilde olur.</li>
<li><strong>Kanal genişliği:</strong> Cam ya da ahşap rafın kalınlığına birebir açılır; rafın kanala sıkı oturması yanal kaymayı belirgin biçimde azaltır.</li>
<li><strong>Kanal derinliği ve iç köşe yumuşatması:</strong> Cam rafta keskin köşe risklidir, iç köşeyi yuvarlatarak temas yüzeyini yayarız.</li>
<li><strong>Dil biçimi:</strong> Düz platform, L dili ya da kavrayan kanallı tip — rafın türüne göre seçilir.</li>
<li><strong>Pim ucu:</strong> Düz, hafif konik ya da esnek geçmeli; sıkı deliklerde konik uç montajı kolaylaştırır.</li>
<li><strong>Vida deliği:</strong> Tutucu panele vidayla da tutunuyorsa vida deliğinin çapı ve konumu mevcut izlere göre açılır, yeni delik açmanız gerekmez.</li>
<li><strong>Yön ve simetri:</strong> Sağ-sol ayrı çalışan dil gerekiyorsa çift takım hazırlanır.</li>
<li><strong>Renk:</strong> Beyaz, gri, antrasit gibi farklı renk seçenekleri arasından mobilyanıza yakın olanı seçilir.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Kapalı bir dolabın içinde, oda sıcaklığında çalışan bir raf pimi için standart sınıf malzeme çoğu zaman yeterlidir ve gereksiz yere üst sınıfa itmeyiz — parçanın fiyatını şişirmenin anlamı yok.</p>
<p>Parça güneş gören bir vitrinde, mutfakta ocak yakınında ya da nemli bir ortamda duracaksa ısıya ve UV'ye dayanıklı sınıfa geçeriz: PETG ya da ASA. Bu grup, sıcakta yumuşayıp sarkma riskini ciddi biçimde düşürür.</p>
<p>Dil kesiti zorunlu olarak ince kalıyorsa ya da raf beklenenden ağır yükleniyorsa karbon veya cam elyaf takviyeli sınıfa çıkarız (PA-CF / PA-GF). Bu malzemeler eğilmeye karşı belirgin biçimde daha diri davranır. Hangisinin gerektiğine rafın ölçüsü ve üstündeki yüke göre karar verir, sebebini de size yazarız; seçim sizde kalsın isterseniz iki seçeneği yan yana koyup farkı anlatırız.</p>
<h2>Dürüst sınır</h2>
<p>Hafif ve orta yüklü raflar için üretiriz: kitap, tabak, dosya, giysi, vitrin eşyası. Ağır depo rafı, kasa taşıyan market rafı ya da üstüne çıkılan raf için plastik pim önermeyiz — orası metal ray ve konsol işidir, size de bunu söyleriz. Kilogram cinsinden kanıtlanamayan taşıma vaadi vermeyiz; onun yerine kesiti kalınlaştırır ya da pim sayısını artırırız. Panel deliği aşırı genişlemiş, sunta içi ufalanmışsa pim tek elle sorunu çözmez; o durumda deliğin önce dolgu ile onarılması gerektiğini açıkça söyleriz.</p>
<p>Bu sayfa tek bir parçaya kilitli: dolap ve vitrin yan panelindeki deliğe giren raf pimi ve raf tutucusu. Mekanizma, menteşe ve muhafaza içinde eksen görevi gören diğer tipler için <a href="/plastik-pim-yaptirma/">plastik pim yaptırma</a> sayfasına bakın; kapak menteşesi, kulp ve dolap ayağı bu kapsamın dışında kalır.</p>
<h2>Sipariş</h2>
<p>Ölçünüz netse siteden kartla online ödeme yapabilirsiniz; ölçüye özel üretim de kart ödemesine dahildir. Emin değilseniz kırık parçanın fotoğrafını ve delik çapını WhatsApp'tan +90 545 138 6526 numarasına gönderin, uygun ölçüyü birlikte belirleyelim. Kaç adet gerektiğini bilmiyorsanız dolabın raf sayısını yazmanız yeter, gereken pim adedini birlikte çıkarırız.</p>
<p>Aynı dolapta çözülmesi gereken tek şey raf pimi olmayabilir: dolap ayağı, birleştirme parçası gibi ihtiyaçlar için <a href="/mobilya-plastik-baglanti-ayak-parca-uretimi/">mobilya plastik bağlantı ve ayak parçası üretimi</a> sayfasına, kapağın kendisi düşüyorsa <a href="/olcuye-ozel-mentese-uretimi/">ölçüye özel menteşe üretimi</a> sayfasına bakabilirsiniz. Elinizde kırık parça varsa yolun en kısası <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a>: parçayı gönderirsiniz, ölçüsünü çıkarır ve yenisini üretiriz.</p>""")


def _olcuye_ozel_mandal_kilit_dili_uretimi():
    return (u"""<h1>Kapak kapanmıyorsa kırılan mandalın yerine yenisini üretiyoruz</h1>
<p>Vitrin dolabının kapağını tutan mandal ile alet çantasının kapağındaki mandal, fotoğrafta neredeyse ikizdir. İkisinde de aynı esneyen dil, aynı tırnak profili vardır. Buna rağmen biri diğerinin yerine takılmaz: iki vida deliğinin merkezleri arasındaki mesafe 24 mm yerine 26 mm'dir, dil boyu iki milimetre kısadır, tırnağın dayandığı omuz yarım milimetre daha kalındır. Raftan aldığınız muadili denediğinizde kapak ya tam kilitlenmez ya da zorlayarak oturur, kısa sürede aynı yerden yeniden çatlar. Piyasada "bulunamıyor" denen mandalların çoğu aslında yok değildir; ölçüsü tutmaz. Yarım milimetre, kapağın kapanmasıyla kapanmaması arasındaki farktır.</p>
<p>Biz işi parçanın markasıyla değil ölçüsüyle karşılıyoruz. Elinizdeki kırık mandalı, sağlam bir eşini ya da parçanın oturduğu yuvayı görmemiz yeterli. Dolap kapağı mandal dili üretimi de, alet çantası mandalı yaptırma da aynı yoldan ilerler: mevcut geometri ölçülür, kırılan yer güçlendirilir, yenisi ölçünüze göre üretilir. Nem, tuz ve titreşim altında çalışan örnekler için <a href="/tekne-kabin-dolap-mandali-yaptirma/">tekne kabin dolap mandalı</a> sayfası montaj ayrıntılarını ayrıca ele alır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p><strong>Getir.</strong> Kırık parçanın tüm kalıntılarını saklayın. İki üç fotoğraf gönderin: parçanın düz üstten görüntüsü, yanından profili ve yanına bir cetvel ya da kumpas koyup çektiğiniz bir kare. Parça tamamen dağıldıysa, oturduğu yuvanın ve karşı tırnağın fotoğrafı da işe yarar.</p>
<p><strong>Ölç.</strong> Delik aralığı, dil boyu, kalınlık ve tırnak açısını tek tek çıkarıyoruz. Kırılan noktayı da inceliyoruz: mandallar genellikle dilin gövdeye bağlandığı dar boyundan kopar. Yeni parçada o bölgeye ek et payı ve yumuşak bir kenar geçişi veriyoruz ki gerilim tek bir çizgide toplanmasın. Ölçü netleştiğinde fiyat ve teslim süresini yazılı olarak iletiyoruz.</p>
<p><strong>Üret.</strong> Onayınızdan sonra parça üretilir, ölçüleri kontrol edilir ve size gönderilir. Tek adet de üretiriz; adet alt sınırımız yoktur.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Dil boyu:</strong> Dilin karşı tırnağa uzandığı mesafe. Kısa kalırsa kapak boşta oynar, uzun olursa kapanırken takılır.</li>
<li><strong>Dil kalınlığı ve esneme payı:</strong> Mandalın ne kadar kolay açılacağını bu belirler. İnce kesit rahat açılır ama çabuk yorulur; kalın kesit sağlam durur, parmakla açması zorlaşır. İkisi arasında sizin kullanımınıza göre denge kurarız.</li>
<li><strong>Delik aralığı:</strong> Vida ya da perçin deliklerinin merkezleri arası mesafe. Mevcut gövdeye deliksiz oturmanın tek şartı budur, milimetrik çalışırız.</li>
<li><strong>Delik çapı ve havşa derinliği:</strong> Vida kafasının yüzeyden taşmaması, kapağın düzgün oturması için önemlidir.</li>
<li><strong>Gövde eni ve yüksekliği:</strong> Parçanın oturduğu yuvaya sığması, komşu parçalara sürtmemesi gerekir.</li>
<li><strong>Omuz yüksekliği:</strong> Tırnağın dayandığı kademenin yüksekliği kapağın ne kadar sıkı duracağını belirler.</li>
<li><strong>Tırnak açısı:</strong> Dik açı sıkı kilitler ve zor açılır, yatık açı kolay açılır. Günde onlarca kez açılan bir kapakla yılda birkaç kez açılan bir muhafaza aynı açıyı istemez.</li>
<li><strong>Karşı tırnak yuvası:</strong> Yuvanın derinliği ve genişliği dille birlikte ayarlanır; ikisi birbirine göre çalışır.</li>
<li><strong>Kenar yumuşatma:</strong> Keskin iç köşe çatlağın ilk adresidir, köşeleri yuvarlatarak bu riski azaltırız.</li>
<li><strong>Farklı renk seçenekleri:</strong> Parçanın görünür yüzde kalması durumunda mevcut renge yakın seçim yapabiliriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Mandalı çalıştığı yere göre seçeriz, gereksiz üst sınıfa itmeyiz. Kapalı mekânda, oda sıcaklığında duran bir dolap ya da kutu mandalı için standart sınıf malzeme yeterlidir ve fiyatı en uygun seçenektir.</p>
<p>Parça güneş gören bir yerdeyse, dışarıda duran bir sandık ya da panonun kapağını tutuyorsa, ısı ve nem değişimine giriyorsa bir üst kademeye çıkarız: PETG veya ASA. Bu malzemeler ısıda yumuşamaya ve güneşe standart sınıftan belirgin şekilde daha dirençlidir.</p>
<p>Mandal gün içinde çok sık açılıp kapanıyor, taşınan bir çantada sürekli yük alıyor ya da ince kesitle yüksek tutma kuvveti isteniyorsa karbon veya cam elyaf takviyeli sınıfa geçeriz: PA-CF ve PA-GF. Bunlar daha rijit ve daha yorulmaya dayanıklıdır, buna karşılık esneme payı azalır — bu yüzden takviyeli malzemede dil kesitini yeniden hesaplarız. Hangi kademenin gerektiğini parçayı gördükten sonra söyleriz; ihtiyaç yoksa üst sınıf önermeyiz.</p>
<h2>Dürüst sınır</h2>
<p>Ne üretiriz: kapağı kapalı tutan mandal gövdesi, esneyen kilit dili ve onun oturduğu karşı tırnak ya da yuva. Dolap, çekmece, alet çantası, kutu, muhafaza kapağı, pano kapağı gibi yerlerde ölçüye özel plastik mandal kilit dili yaptırma işini rahatlıkla yaparız. Titreşimle çalışan bahçe makinelerinde tırnak yüksekliğindeki bir milimetrelik eksiklik kapağı çalışırken açtırır; o mandalları <a href="/cim-bicme-bahce-makinesi-plastik-parca-yaptirma/">bahçe makinesi plastik parça üretimi</a> sayfasında ayrıca ele alıyoruz.</p>
<p>Ne üretmeyiz: anahtarlı kilit göbeği, barel ve içindeki metal mekanizma bizim işimiz değildir. Güvenlik amaçlı, sertifika istenen kilitleme parçalarını da üretmeyiz. Sürekli tam güçle zorlanan, insan güvenliğinin ona bağlı olduğu bir bağlantıda metal çözüm doğrudur ve bunu size açıkça söyleriz. Mandal esneyerek çalışan bir parçadır; her açılışta bir miktar yorulur. Bizim yaptığımız, kırılan noktayı güçlendirip ölçüyü tam tutturmaktır — sınırsız ömür sözü vermeyiz.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Kırık parçanın fotoğrafını WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; ölçüleri birlikte netleştirelim, fiyatı ve teslim süresini yazalım. Onay verdiğinizde siteden kartla online ödeme yapabilirsiniz — ölçüye özel işler de kartla ödemeye açıktır.</p>
<p>Elinizdeki parça birden fazla yerinden kopmuşsa <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> sayfasındaki yol haritası işinizi kolaylaştırır. Kapağın açılıp kapanmasını sağlayan dönen bağlantı da yıprandıysa <a href="/olcuye-ozel-mentese-uretimi/">ölçüye özel menteşe üretimi</a> tarafına, kapağı tutan geçmeli tutucular kırıldıysa <a href="/olcuye-ozel-klips-kelepce-uretimi/">klips ve tutucu parça üretimi</a> tarafına bakabilirsiniz. Hangi malzeme kademesinin size uyduğunu merak ediyorsanız <a href="/malzeme-rehberi/">malzeme rehberi</a> seçimi sadeleştirir.</p>""")


def _dus_kabini_banyo_plastik_parca_uretimi():
    return (u"""<h1>Duş kabini makarası kırıldı diye kabinin tamamını değiştirmeyin</h1>
<p>Duş kabinlerinde arıza çoğu zaman camdan ya da profilden gelmez; iki gramlık bir duş kabini makarasından, kayar kapının alt kılavuzundan veya fitili tutan ince bir tutucudan gelir. Bir kabinde yıpranan şey neredeyse her zaman hareketli plastik gruptur: duş kabini makarası, kılavuz pabucu, fitil tutucusu, menteşe takozu. Sorun bu kadar küçükken önünüze konan çözüm büyür: tek parça yerine kanat, kanat yerine kabinin tamamı önerilir. Kırılan parçanın maliyeti ile teklif edilen yenileme arasındaki fark kat kat açılır.</p>
<p>Bu hesap tutmuyor. Cam, profil ve kanat düzeni işini görmeye devam ediyorsa değişmesi gereken tek şey kırılan parçadır; biz de yalnızca onu yapıyoruz: duş kabini makarası ve plastik parça özel üretimi. Elinizdeki kırık tekerleği, kılavuzu, fitil tutucusunu ya da banyo dolabı plastik yedek parçasını ölçer, aynı işi görecek parçayı ölçüye özel üretiriz. Model adı bilinmiyor, üretici piyasadan çekilmiş, kutusu yok — hiçbiri engel değil; parçanın kendisi yeterli.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Kırık parçayı bize ulaştırırsınız. Parça kırıldıysa kırık parçalarını da atmayın; iki ucu bir araya getirildiğinde ölçü çok daha net çıkar. Elinizde hiç örnek kalmadıysa parçanın oturduğu yuvanın, profil kanalının ve vida deliklerinin fotoğrafı ile kumpas ölçüleri de iş görür.</p>
<p>Ölçüyü biz çıkarırız: duş kabini makarasının çapı, kanal kesiti, aks deliği, vida merkez mesafesi, kılavuzun cam yuvası. Ardından ölçüleri size teyit ederiz. Onay verdiğinizde parça üretilir ve gönderilir. Tek kanattaki duş kabini makaralarının tamamı yorulmuşsa dört ya da altı adet birlikte üretmek mantıklıdır; tek adet de üretiriz, adet alt sınırımız yoktur.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Duş kabini makarası dış çapı ve sırt kesiti (V kanal, yuvarlak sırt, düz sırt):</strong> tekerlek profilin kanalına tam oturmazsa kanat ya takılır ya raydan çıkar.</li>
<li><strong>Aks/mil delik çapı ve vida ölçüsü (M4, M5, M6):</strong> mevcut vidalarınızı kullanmaya devam edebilmeniz için delik ölçüsü birebir alınır.</li>
<li><strong>Eksantrik ayar mesafesi:</strong> kabin kanadının yükseklik ayarını yapan kaçıklık ölçüsüdür; korunmazsa kapı alt tarafta sürtmeye devam eder.</li>
<li><strong>Gövde ile taşıyıcı plaka arasındaki ofset kalınlığı:</strong> camın profile göre hizasını belirler, yanlışsa kanat yamuk kapanır.</li>
<li><strong>İki vida deliği arasındaki merkez mesafesi:</strong> yeni parçanın mevcut deliklere delme yapılmadan oturmasını sağlar.</li>
<li><strong>Kılavuz pabucunun genişliği, derinliği ve cam kalınlığı yuvası (6 mm veya 8 mm):</strong> kayar kapı kılavuz parçası üretiminde en kritik ölçüdür; gevşek yuva kanadı sallandırır.</li>
<li><strong>Kılavuz eğim açısı ve kanat yönü:</strong> sağ ve sol kanat çoğu kabinde simetriktir, yön yanlış olursa parça ters çalışır.</li>
<li><strong>Fitil ve mıknatıs tutucusunun kanal genişliği ile dudak kalınlığı:</strong> fitilin yerinden fırlamadan tutulmasını bu iki ölçü belirler.</li>
<li><strong>Tutamak yuvasına oturan pim/burç çapı ve oturma derinliği:</strong> tutamağın kabin üzerindeki yuvada boşluk yapmadan sabit durması içindir; kabin dışındaki mekanizma ve muhafaza pimlerini de aynı ölçülerle <a href="/plastik-pim-yaptirma/">ölçüye özel plastik pim</a> olarak üretiyoruz.</li>
<li><strong>Banyo dolabı menteşe takozu delik aralığı ve kanat açıklığı:</strong> dolap kapağının duvara ya da yan panele çarpmadan açılmasını sağlar.</li>
<li><strong>Farklı renk seçenekleri:</strong> şeffafa yakın, beyaz, gri ve siyah tonlarda üretim yapılabilir; görünen parçalarda kabin rengine yakın olanı seçeriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Banyo, bir parça için sıradan bir ortam değildir: sürekli nem, sıcak su buharı, kireç ve haftada birkaç kez temizlik kimyasalı. Buharın ve sıcak suyun malzeme seçimini nasıl daralttığını <a href="/sicak-su-ve-buhar-temasli-plastik-parca-uretimi/">sıcak su ve buhara dayanıklı parça üretimi</a> sayfasında ayrıntılı anlattık. Standart sınıf malzeme burada zamanla kırılganlaşır. Bu yüzden kabin parçalarında varsayılanımız nem ve sıcaklık dalgalanmasına dayanıklı sınıftır — kılavuz pabucu, fitil tutucusu, tapa ve takoz gibi parçalarda PETG ya da ASA çoğu durumda doğru karşılıktır. Cam ağırlığını taşıyan duş kabini makarası gövdesi ve aks bölgesinde yük ve sürtünme birlikte çalıştığı için karbon/cam elyaf takviyeli sınıfa (PA-CF, PA-GF) çıkarız.</p>
<p>Gereksiz yere üst sınıfa itmeyiz. Yükü olmayan bir fitil tutucusunu takviyeli malzemeden üretmek size fazladan maliyet çıkarır, karşılığında ek bir fayda sağlamaz. Parçanın nerede ve hangi yükte çalıştığını sorar, gerekli sınıfı öneririz; kararı ölçüyle beraber size yazılı olarak iletiriz.</p>
<h2>Dürüst sınır</h2>
<p>Ne üretiriz: duş kabini makarası ve tekerlek gövdesi, aks ve burcu, alt-üst kılavuz pabucu, fitil ve mıknatıs tutucusu, tutamak yuvasına oturan pim ve burç, banyo dolabı menteşe takozu, kabin üzerindeki tapa ve kapaklar.</p>
<p>Ne üretmeyiz: cam kesimi ve temperleme yapmayız, alüminyum profil imalatı yapmayız, yerinde montaj ve servis vermeyiz, komple kanat veya mekanizma seti satmayız. Sızdırmazlık görevi olan parçalarda düşük ve orta seviyede sıkma yüküne uygun çözüm üretiriz; kabinin tamamının su tutması, cam ağırlığının duş kabini makaraları arasında paylaşımı ve genel denge özgün düzenin sorumluluğunda kalır. Taşıyıcı olmayan ara eleman talebi gelirse hafif, yük dışı kullanım için üretiriz. Bu sınırları önceden söylüyoruz, çünkü parçanın çalışmayacağı bir yere satılması kimsenin işine yaramaz.</p>
<h2>Sipariş</h2>
<p>Kırık parçanın fotoğrafını ve varsa ölçülerini WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; ölçü ve malzeme önerisini biz çıkaralım. Onaydan sonra ölçüye özel işler dahil siteden kartla online ödeme yapabilirsiniz. Ölçü sizden, üretim bizden.</p>
<p>Kabininizin modeli piyasadan kalktıysa <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretimi</a> sayfasındaki akış tam olarak bu durum için yazıldı. Elinizde kırık da olsa parçanın kendisi varsa <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> en hızlı yoldur. Kabin dışında kalan mobilya ve dolap kulplarında ise <a href="/olcuye-ozel-kulp-tutamak-uretimi/">ölçüye özel kulp ve tutamak üretimi</a> sayfasına göz atabilirsiniz. Banyo dışında kalan genel tekerlek ihtiyaçları — mobilya, ekipman, taşıma arabası — için <a href="/olcuye-ozel-tekerlek-makara-uretimi/">ölçüye özel tekerlek üretimi</a> sayfası daha doğru adrestir.</p>""")


def _stor_jaluzi_perde_mekanizma_parcasi_uretimi():
    return (u"""<h1>Perdenin yan kapağı ya da zincir kasnağı kırıldıysa çözümü var</h1>
<p>Perde mekanizmasında bütün yük, avuç içine sığan birkaç plastik parçanın üzerindedir. Zincirin her çekilişinde boncuklar kasnağın yuvalarına biner, yan kapak borunun tüm ağırlığını iki küçük tırnakla tutar, boru tapası dönerken sürtünür. Günde iki kez kaldırılıp indirilen bir perdede bu hareket yıl boyunca yüzlerce kez tekrarlanır ve yorulma en ince kesitte kendini gösterir: kasnağın bir dişi kopar, yan kapağın tırnağı çatlar. Sonuç, ya kilitlenmeyen ya da her indirişte kendiliğinden kayan bir perdedir.</p>
<p>Sıkıntının ikinci yarısı tedarik tarafındadır. Bu parçalar çoğu zaman ayrı satılmaz; komple mekanizma seti olarak satılır. Tek bir kasnak için bütün takımı almak, üstelik yeni takımın ölçüsünün eski borunuza uymama riskini de göze almak anlamına gelir. Perde takımı beş yıl önce alındıysa aynı serinin bulunması da çoğu zaman mümkün olmaz. Oysa ihtiyacınız olan tek şey ölçüsü tutan bir plastik parçadır; biz de yalnız onu üretiriz. Stor perde mekanizma plastik parça yaptırma, jaluzi yan kapak parçası üretimi, zebra perde zincir kasnağı yaptırma ve perde boru tapası özel üretim işlerinin hepsi elinizdeki örnekten ölçü alınarak yapılır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>İlk adım örneği bize ulaştırmanızdır. Kırık parçanın iki yarısı da duruyorsa ikisini birden gönderin; kırık yüzeyler birleştirildiğinde orijinal ölçü net biçimde okunur. Parça tamamen kaybolduysa borunun kendisi, zincir ve karşı taraftaki sağlam kapak yeterli bilgiyi verir, çünkü mekanizmalar genelde simetriktir.</p>
<p>İkinci adım ölçüdür. Boru iç çapı, kanal profili, zincir boncuk aralığı, vida delik mesafeleri ve montaj yüksekliği tek tek ölçülür. Uzaktan çalışıyorsanız parçanın yanına bir cetvel koyup üstten ve yandan çekilmiş net fotoğraflar göndermeniz çoğu iş için yeterlidir; kritik ölçüleri kumpas ile okuyup bize yazarsanız daha da hızlı ilerleriz.</p>
<p>Üçüncü adım üretimdir. Ölçüler onaylandıktan sonra parça milimetrik olarak üretilir, gerekirse tek bir deneme örneği çıkarılıp yerine oturması teyit edilir, sonra takım tamamlanır. Perdenin yerine takılması size kalır; parça mevcut vida deliklerine ve mevcut boruya uyacak şekilde üretildiği için duvarda yeni delik açma ihtiyacı çoğu işte ortadan kalkar.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Boru iç çapı ve et kalınlığı</strong> — tapa ile yan kapağın boşluk yapmadan oturduğu ana ölçüdür; yarım milimetre fark bile perdeyi tıkırdatır.</li>
<li><strong>Borunun iç kanal/kertik profili ve kanal adedi</strong> — tapanın boru içinde boşa dönmesini bu kilit engeller.</li>
<li><strong>Zincir boncuk çapı ve boncuklar arası merkez aralığı</strong> — kasnak yuvası bu aralığa göre açılmazsa zincir atlar, perde tutmaz.</li>
<li><strong>Kasnak dış çapı ve yuva sayısı</strong> — bir tam turda inen perde miktarını ve zincirin oturuş açısını belirler.</li>
<li><strong>Kasnak göbek deliği çapı ve kesiti</strong> (yuvarlak, altıgen, D kesit) — dönüşün mile aktarılması bu kesite bağlıdır.</li>
<li><strong>Yan kapak vida deliği merkez mesafesi ve delik çapı</strong> — duvardaki mevcut delikleri yeniden açmadan takabilmeniz için birebir korunur.</li>
<li><strong>Kapağın duvar veya tavan mesafesi</strong> — perde ile duvar arasındaki boşluğu belirler; denizliğe ya da pencere koluna sürtmeyi bu ölçü çözer.</li>
<li><strong>Tırnak/klips kalınlığı ve esneme payı</strong> — takarken kırılmadan geçmesi, taktıktan sonra tutması için ayrı ayrı ayarlanır.</li>
<li><strong>Braket ayak yüksekliği, taban kalınlığı ve vida aralığı</strong> — perdenin sarkma açısını ve tutunma gücünü belirler.</li>
<li><strong>Yön ve ayna simetrisi</strong> — zincir sağdan da soldan da çalışabilir; parça size göre ters üretilir.</li>
<li><strong>Jaluzi lamel kalınlığı ve ip deliği çapı</strong> — lamelin takılmadan hareket etmesi buna bağlıdır.</li>
<li><strong>Yüzey işlemi ve farklı renk seçenekleri</strong> — görünen kapaklarda mevcut takımla uyum için seçilir.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme, parçanın nerede çalıştığına göre seçilir. Salon veya yatak odasında, güneşin doğrudan vurmadığı bir perdenin yan kapağı ile boru tapası için standart sınıf fazlasıyla yeterlidir; burada gereksiz üst sınıfa itmeyiz.</p>
<p>Balkon, veranda, cam kenarı ve gün boyu doğrudan güneş alan cepheler farklıdır. Orada yüzey ısınır ve morötesi ışık plastiği zamanla gevretir; bu konumdaki kapak ve braketler için ısı ile hava koşuluna dayanıklı sınıfa (PETG ve ASA) geçeriz. Renk solmasının da önüne büyük ölçüde bu geçiş geçer.</p>
<p>Sürekli yük altında çalışan ve dişi aşınan parçalar — zincir kasnağı, mil göbeği, kilit dili tutucusu, ağır bir borunun tüm ağırlığını tutan braket — için karbon ya da cam elyaf takviyeli sınıfı (PA-CF / PA-GF) öneririz. Bu sınıf daha rijittir ve tekrarlayan çekmeye karşı daha az yorulur.</p>
<h2>Dürüst sınır</h2>
<p>Ne ürettiğimizi net söyleriz: perde mekanizmasının kırılan iç plastik parçalarını üretiriz — yan kapak, zincir kasnağı, boru tapası, duvar ve tavan braketi, kilit dili tutucusu, ara pimler ve klipsler.</p>
<p>Ne üretmediğimizi de aynı netlikte söyleriz. Kumaş ve perde imalatı yapmayız, komple hazır mekanizma sistemi satmayız, yerinde ölçü alma ve montaj servisimiz yoktur. Motorlu sistemlerde motorun ve elektroniğin kendisi bizim işimiz değildir; yalnız o sistemin plastik kapak ve tutucularını üretiriz. Yay barelli mekanizmanın çelik yayı ve mili de metal parçadır, onları karşılamayız.</p>
<p>Bir sınır daha: perde borusunun kendisi taşıyıcı bir profildir, plastik olarak üretmeyiz — bu tür profil ve kiriş parçalarını yalnız hafif, yük dışı kullanımlar için yaparız. Çok geniş ve ağır bir borunun tüm ağırlığını tek bir plastik kapağın tutması da sınırlıdır; böyle bir durumda takviyeli malzemeye geçmeyi ya da yükü iki noktadan alan bir braket kullanmayı açıkça öneririz.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Kırık parçanın fotoğrafını ve varsa ölçülerini WhatsApp hattımıza gönderin: <strong>+90 545 138 6526</strong>. Uygunluğu ve seçenekleri en kısa sürede konuşur, ardından işi netleştiririz. Sitemizden kartla online ödeme yapabilirsiniz; ölçüye özel işler de bu ödeme akışına dahildir, ayrı bir yönteme gerek kalmaz.</p>
<p>Zincirin oturduğu kasnak dışında farklı bir tahrik parçanız da kırıldıysa <a href="/kasnak-olcuye-ozel-uretim/">ölçüye özel kasnak üretimi</a> sayfasına, borunun ya da profilin ucunu kapatan parçalar için <a href="/olcuye-ozel-tapa-kapak-uretimi/">ölçüye özel tapa ve kapak üretimi</a> sayfasına göz atabilirsiniz. Elinizde perdeyle ilgisi olmayan, iki parçaya ayrılmış bir plastik varsa <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> sayfası aynı akışı anlatır: örneği gönderin, ölçüsünü alalım, yenisini üretelim.</p>""")


def _spor_salonu_fitness_ekipmani_plastik_parca_uretimi():
    return (u"""<h1>Kondisyon aletinin kırılan plastiğini yenisiyle değiştirelim</h1>
<p>Salonda ya da evde bir kondisyon aletinin en zayıf halkası genelde metal aksamı değil, gövdeyi saran plastikleridir. Koşu bandının motor kapağı, ağırlık kolonunun halat kılavuzu kılıfı, seçme piminin oturduğu yuva, gövde borusunun ayak pabucu; hepsi tekrarlı hareket, ter ve darbe görür. Terin taşıdığı tuz ve nem yüzeyde kalır, temizlik bezi her gün aynı kenara sürtünür, ağırlık bırakıldığında gövdeye kısa ve sert bir darbe biner. Aynı parça hep aynı noktadan kopuyorsa çözüm çoğu kez ölçüyü değil sınıfı yukarı çekmektir; bu kararı <a href="/darbeye-dayanikli-plastik-parca-yaptirma/">darbeye dayanıklı plastik parça yaptırma</a> sayfasında kesit kesit anlattık. Plastik bu üç yükü aynı anda taşıdığında önce tırnaktan, sonra vida kulağından çatlar. Kırıldığında tedarik tarafı çoğu zaman kapanmıştır: eski seri için ayrılan yedek stok birkaç sezonda tükenir. Geriye kalan tek şey elinizdeki kırık örnektir.</p>
<p>Spor salonu ekipmanı plastik parçası arayan işletmeler ve ev tipi alet sahipleri bu yüzden iki kötü seçenek arasında sıkışır: aletin tamamını gözden çıkarmak ya da kırık parçayla idare etmek. Üçüncü yol, elde kalan o örneği kullanmaktır. Kondisyon aleti plastik parça yaptırma işi bizde numuneyle yürür: parçayı ölçer, ölçüsüne birebir uyan yenisini üretiriz. Koşu bandı plastik yan kapak üretimi, halat kılavuzu kılıfı, ağırlık seçme piminin oturduğu yuva ve gövde borusunun ayak pabucu bu işin en sık gelen dört kalemidir.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Kırık parçayı bize getirir ya da yollarsınız. Parça birkaç ayrı kırıkta olsa da olur; önemli olan delik merkezlerinin, kanal genişliğinin ve oturma yüzeylerinin okunabilmesidir. Elinizde örnek kalmadıysa, parçanın takıldığı yuvanın ölçüsünü kumpas ile alır, net fotoğraflarla birlikte gönderirsiniz.</p>
<p>Ölçüleri kumpas ile teker teker çıkarır, üretim öncesinde onayınız için ölçü listesini iletiriz. Onay verdiğinizde tek adet de olsa üretime alınır, size gelen parça yerine oturduğunda iş biter. Adet tarafında esneğiz: bir salon aynı modelden on iki koşu bandına aynı kapağı isteyebilir, ev kullanıcısı tek parçayla gelebilir. Salonlar için çok kullanılan bir kalemi ölçü dosyasıyla kayıt altına alırız; ileride aynı parça yine kırıldığında ölçü işini yeniden yapmaya gerek kalmaz, doğrudan üretime geçeriz.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Delik merkez mesafeleri:</strong> Kapağın gövdeye tutunduğu vida deliklerinin arası milimetrik tutulur; bir milimetre kayma kapağın oturmasını engeller.</li>
<li><strong>Dış hat ve et kalınlığı:</strong> Kapak profili gövde kenarına oturduğu için kesit kalınlığı ve kenar yarıçapı örneğe göre çıkarılır; ince kalırsa esner, kalın kalırsa yuvaya girmez.</li>
<li><strong>Tırnak yüksekliği ve açısı:</strong> Kapağın klips tırnakları hem tutmalı hem sökülebilmeli; bu yüzden tırnak boyu ve giriş açısı örnekten ölçülür.</li>
<li><strong>Kılavuz kılıfında kanal genişliği ve derinliği:</strong> Halat kalınlığına göre ayarlanır; dar kanal halatı sıkıştırır, geniş kanal halatın kanaldan çıkmasına yol açar.</li>
<li><strong>İç çap ve göbek toleransı:</strong> Kılavuz kılıfının veya yuvanın mil üzerine ne kadar sıkı oturacağı, boşluk payı verilerek belirlenir.</li>
<li><strong>Pim yuvası çapı ve kademe aralığı:</strong> Ağırlık seçme piminin girdiği yuvanın çapı ile yuvalar arasındaki mesafe, kendi kolonunuzun ölçüsüne göre çıkarılır.</li>
<li><strong>Ayak pabucunda boru kesiti:</strong> Yuvarlak, oval ya da kare boruya göre iç ölçü ve yükseklik ayarlanır; taban genişliği zeminde iz kalmayacak şekilde seçilir.</li>
<li><strong>Yüzey ve renk:</strong> Farklı renk seçenekleri sunarız; mat ya da dokulu yüzey tercihinizi de üretimden önce belirleriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Parçayı çalışacağı yere göre malzemeye yönlendiririz. Salon içinde, güneş görmeyen ve yük almayan bir yan kapak için standart sınıf yeterlidir — gereksiz üst sınıfa itip fiyat şişirmeyiz.</p>
<p>Ter, temizlik kimyasalı ve sürekli el teması olan yerlerde ya da cam kenarında güneş alan salonlarda PETG veya ASA sınıfına çıkarız; bu sınıf ısı ve ışık altında biçimini daha iyi korur. Halat kılavuzu kılıfı, pim yuvası gibi sürtünme ve tekrarlı temas gören parçalarda ise karbon ya da cam elyaf takviyeli PA-CF / PA-GF sınıfını öneririz; bu sınıf sertliğini ve boyutunu tekrarlı harekette daha iyi tutar. Hangi sınıfın gerektiğini parçanın fotoğrafını ve görevini gördükten sonra söyleriz.</p>
<h2>Dürüst sınır</h2>
<p>Üretiriz: yük taşımayan yan kapaklar, koruyucu muhafazalar, halat kılavuzu kılıfı, pim yuvası gövdesi, gövde borusu ayak pabucu, kapak tırnakları, kablo geçiş parçaları ve benzeri görünen-koruyan plastikler.</p>
<p>Üretmeyiz: kullanıcının ya da ağırlık bloklarının yükünü taşıyan parçalar. Yük taşıyan ve güvenlik işlevi gören parçalar (ağırlık taşıyan kol, emniyet pimi, kilit mekanizması) kapsam dışıdır. Halat ucu bağlantı elemanı, emniyet kancası, oturma yeri ile gövde arasındaki taşıyıcı bağlantılar ve kopması durumunda kullanıcıyı riske atacak elemanlar da aynı gruptadır; bunlar metal aslıyla değiştirilmelidir. Aynı şekilde motor, kayış gerdirme ve fren grubunun yük alan elemanlarına da girmeyiz. Bu sınırı ilk konuşmada söyleriz, çünkü doğru parçayı üretmek kadar hangi parçayı üretmeyeceğimizi bilmek de işin bir bölümüdür. Görevi doğrudan güvenlik olan bir eleman, ölçüsü elimizde olsa bile kapsamımıza girmez.</p>
<h2>Sipariş</h2>
<p>Kırık parçanın fotoğrafını ve varsa kumpas ölçülerini WhatsApp'tan +90 545 138 6526 numarasına gönderin; uygun olup olmadığını, malzeme sınıfını ve fiyatı yazalım. Ölçüye özel işler dahil sitemizden kartla online ödeme yapabilirsiniz; onay sonrası üretim sırasına alınır.</p>
<p>Salonunuzda aynı sıkıntı yaşayan tek parça bu değilse, <a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçası üretimi</a> sayfamıza da göz atın. Kırılan şey bir muhafaza ya da kayış kapağıysa <a href="/olcuye-ozel-koruma-kapagi-muhafaza-uretimi/">ölçüye özel koruma kapağı ve muhafaza üretimi</a> sayfası daha yakın olabilir; elinizde tek bir örnek varsa ve adet derdiniz yoksa <a href="/tek-adet-ozel-parca-uretimi/">tek adet özel parça üretimi</a> sayfasındaki akış tam size göredir.</p>""")


def _ticari_arac_kamyon_plastik_parca_ozel_uretim():
    return (u"""<h1>Eski model kamyonda bulunamayan plastik parçayı üretiyoruz</h1>
<p>Uzun yolda arıza çoğu zaman önce sesten belli olur: kabinde ıslık gibi bir hava sesi, torpidodan gelen tıkırtı, kaplamanın her kasiste verdiği çıtırtı. Şoför bunları mekanizmaya yorar; fan arızalı, kilit bozuk, döşeme gevşemiş sanır. Oysa ağır ticari araçlarda bu tabloyu kuran şey genellikle kopmuş tek bir plastik ayrıntıdır. <a href="/oto-havalandirma-izgara-klipsi-yaptirma/">Havalandırma ızgarasının kanat tırnağı ve yönlendirme klipsi</a> kırılınca kanat tam kapanmaz ve içeri hava sızar; menteşe mili yorulunca torpido kapağı yerinde durur ama her kasiste tıkırdar; kaplama panelini sac kenarına kilitleyen klipsin tırnağı koptuğunda panel sallanır. Kırılma olduğu anda fark edilmez, aylar sonra farklı bir arıza gibi kendini gösterir.</p>
<p>Teşhis buraya gelince yol tıkanır. Kamyon, kamyonet ve minibüs kabin plastikleri model ömrü uzun sürdüğü için stoklardan erken çekilir; araç günlük iş görmeye devam ederken o ızgara ya da klips tedarik listelerinden düşer. Karşınıza çıkan seçenek genellikle koca bir kaplama grubunu ya da komple torpido setini almaktır — kırık olan tek küçük parça için.</p>
<p>Biz o tek parçayı ölçüsüne göre üretiriz. Kamyon kabin plastik parça yaptırma işlerinde elimize gelen şey çoğu zaman kırık orijinalin kendisi, bazen de sadece parçanın oturduğu boşluktur. İkisi de yeter.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Kırık parçayı ya da parçaların hepsini bize ulaştırırsınız; ulaşamıyorsanız net fotoğraf ve birkaç kumpas ölçüsü ile de yol alırız. Parçanın hangi yüzeye oturduğunu, hangi tırnağın hangi yöne kilitlendiğini ve araçta ne iş gördüğünü konuşuruz. Ölçüleri çıkarır, kritik noktaları size onaylatır, sonra üretime alırız. Kırık parçada eksik köşe varsa simetriden ve karşılığındaki sağlam parçadan tamamlarız. Tek adet üretiriz; ticari araç iç kaplama klipsi üretimi gibi işlerde ise aynı klipsten sekiz, on beş adetlik takım hâlinde çoğaltırız — kabin sökülmüşken hepsini birden yenilemek en sağlıklısıdır.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Çerçeve dış ölçüsü ve köşe yarıçapı:</strong> Kamyon havalandırma ızgarası yaptırma işinde parçanın torpido boşluğuna zorlanmadan oturması bu iki ölçüye bağlıdır; yarım milimetre şaşarsa çerçeve ya oynar ya yerine girmez.</li>
<li><strong>Kanat açısı ve kanat aralığı:</strong> Hava yönünü ve sesi belirler; orijinaldeki açıyı korur, isterseniz sürücüye yönelimi bir tık değiştiririz.</li>
<li><strong>Menteşe mili çapı ve mil eksen mesafesi:</strong> Torpido kapağının salınmadan, sürtmeden açılıp kapanması buna bağlıdır.</li>
<li><strong>Kilit dili yüksekliği ve yuva derinliği:</strong> Kapağın "klik" tutması ile yolda kendiliğinden açılması arasındaki fark bu ölçüdür.</li>
<li><strong>Klips gövde çapı ve tırnak yüksekliği:</strong> Tırnak, sac kalınlığına göre ayarlanır; kalın sacta kısa tırnak tutmaz, ince sacta uzun tırnak paneli gevşek bırakır. Panel sağlam da kırılan yalnızca geçme tırnaksa, o tek tırnağın kök kalınlığı ve esneme payı için <a href="/kirik-plastik-tirnak-yaptirma/">kırık geçme tırnak üretimi</a> sayfasına bakın.</li>
<li><strong>Klips tabla çapı ve boyun boyu:</strong> Panel ile sac arasındaki mesafeyi belirler, kaplamanın düz oturmasını sağlar.</li>
<li><strong>Braket delik merkez mesafesi ve delik çapı:</strong> Konsol braketi mevcut vida deliklerine birebir gelmezse parça zorlanır ve aynı yerden yeniden kırılır.</li>
<li><strong>Kesit kalınlığı ve destek kanadı açısı:</strong> Titreşim yükünü dağıtır; ince kesit esner, gereksiz kalın kesit sökümü zorlaştırır.</li>
<li><strong>Kablo kanalı iç genişliği ve derinliği:</strong> Kabin arkasındaki demetin kapağı kapanacak şekilde toplanmasını sağlar.</li>
<li><strong>Diş adımı ve yuva derinliği:</strong> Vida ile tutturulan parçalarda orijinal vidanızın kendi yuvasına düzgün oturması içindir.</li>
<li><strong>Farklı renk seçenekleri:</strong> Kabin tonuna yakın koyu gri, siyah ve açık gri ile çalışırız; görünen yüzeylerde renk uyumunu önceden konuşuruz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalıştığı yere göre seçeriz, otomatikman en üst sınıfa itmeyiz. Görünmeyen, ısı ve güneş almayan iç tutucularda standart sınıf yeterlidir ve maliyeti düşük tutar. Ön cam altında, gün boyu güneş gören torpido kapağı, havalandırma ızgarası ve görünen kaplama parçalarında ısıya ve mor ötesine dayanıklı sınıfa (PETG ve ASA) geçeriz; ticari araç kabini yazın çok ısınır, standart sınıf orada zamanla yumuşar ve şekil kaybeder. Sürekli takıp çıkarılan, titreşimle yorulan klips, tırnak, konsol braketi ve menteşe gibi mekanik yük gören parçalarda ise karbon ya da cam elyaf takviyeli sınıfa (PA-CF / PA-GF) çıkarız; buradaki kazanç sertlik ve yorulma direncidir. Hangi sınıfın gerektiğini parçayı gördüğümüzde söyler, gerekmeyen yere üst sınıf yazmayız.</p>
<h2>Dürüst sınır</h2>
<p>Kabin ve iç mekan plastiklerini üretiriz: havalandırma ızgarası ve kanadı, torpido kapağı, kaplama klipsi ve tırnağı, konsol braketi, kablo kanalı, tutucu ve ara elemanlar; kapı içinde camı taşıyan kızak ya da tutucu kırıldıysa o iş <a href="/cam-krikosu-plastik-parcasi-yaptirma/">cam krikosu plastik parçası yaptırma</a> sayfasında anlatılıyor. Üretmediklerimiz de aynı netlikte: motor bölümünde sürekli ısı ve yağ altında çalışan parçalar, yakıt hattı elemanları, fren hattı bağlantıları, hava yastığı kapağı ve emniyet kemeri parçaları gibi güvenlik fonksiyonu taşıyan parçalar kapsamımıza girmez. Araç ağırlığını taşıyan gövde ve şasi elemanı da üretmeyiz. Kabin içinde bile taşıyıcı olan bir noktada isek metal çözüm önerir, işi kabul etmeyiz. Parçanın kabinde ne iş gördüğünü birlikte netleştirir, kapsamımızın dışında kalan işi önceden söyleriz.</p>
<h2>Sipariş</h2>
<p>Kırık parçanın ve takıldığı yerin fotoğrafını WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; ölçüleri ve malzeme sınıfını konuşup net fiyat verelim. Onay sonrası siteden kartla online ödeme yapabilirsiniz — ölçüye özel üretilen parçalar dahil.</p>
<p>Minibüs plastik yedek parça özel üretim taleplerinde çoğu zaman aynı kabinden birkaç kalem birden çıkar; hepsini tek seferde değerlendirmek isterseniz <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça üretimi</a> sayfasındaki akış işinizi görür. Binek araç iç döşeme ve trim bağlantıları için <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim klips üretimi</a> sayfasına, kabin dışındaki farklı ızgara ve petek işleri için <a href="/olcuye-ozel-izgara-petek-uretimi/">ölçüye özel ızgara ve petek üretimi</a> sayfasına göz atabilirsiniz.</p>""")


def _elektrikli_supurge_aparati_plastik_parca_uretimi():
    return (u"""<h1>Süpürgenin kırılan ucu yüzünden sağlam cihazı atmayın</h1>
<p>Bir süpürgenin uç tarafı, göründüğünden çok daha zorlu bir ortamda çalışır. Motorun ısıttığı hava saatlerce aynı kanaldan geçer, plastik gövde sürekli ılık kalır. Boru zemine her değdiğinde küçük bir titreşim biner; koltuk altına uzanırken aynı bağlantı burulur, çekilir, bir mobilya kenarına takılır. Zemin yıkama makinelerinde bunlara su, deterjan ve tam kurumayan nem eklenir. Balkonda ya da depoda güneş gören bir gövde ise aylar içinde gevrekleşir. Bütün bu koşullar en ince yerde sonuç verir: hortum ucundaki bağlantı bileziğinde, kilit tırnağında ya da fırça kapağının kenarında.</p>
<p>Kırılan parça çoğu zaman avuç içi kadardır, sonucu ise cihazın tamamında görülür. Boru ucundan çıkar, ek yerinden hava kaçırır, fırça kapağı yerinde durmaz, emiş belirgin biçimde zayıflar. Kırık yüzeye bakınca koşulun izi okunur: ılık havada gevşeyen kesit, deterjanlı nemde matlaşan yüzey, burulmadan sonra tırnak dibinden ilerleyen çatlak. Tek parça çoğu zaman ayrı satılmaz, set hâlinde satılır; birkaç yıllık modellerde ise stok kapanmış olur. Elektrikli süpürge yedek aparat parçası yaptırma sorusu genellikle bu noktada gelir. Üretici o modeli artık desteklemiyor olsa bile, elinizdeki kırık örnek bizim için yeterli ölçü kaynağıdır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Kırık parçayı bize ulaştırırsınız; iki yarım hâlinde olması sorun değil, önemli olan oturduğu yüzeylerin ve kilit noktalarının okunabilmesidir. Parçayı milimetrik ölçeriz, hortumun ve boru ucunun oturma çaplarını doğrularız, gerekiyorsa cihazın kendi borusundan ek ölçü isteriz. Ölçüler netleştikten sonra hangi ölçünün nereden alındığını gösteren kısa bir özet iletiriz; onayınızla iş üretim sırasına girer. Süpürge hortum bağlantı bileziği üretimi gibi işlerde ilk adım tek adet deneme parçasıdır: cihaza takılır, oturması görülür, gerekirse birkaç onda milimetrelik düzeltmeyle son hâline getirilir. Bu düzeltmenin koşulu açıktır: sapma bizim aldığımız ölçüden kaynaklanıyorsa revizyon bizdendir, ayrıca ücret çıkmaz; parçanın ölçüsü sizin isteğinizle değişirse bu yeni bir iş olarak fiyatlandırılır.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Hortumun iç ve dış oturma çapı:</strong> Bileziğin hortuma sıkı ama zorlamasız girmesi bu iki ölçüye bağlıdır; yarım milimetrelik hava kaçağı emişte hissedilir.</li>
<li><strong>Boru ucu geçiş çapı ve oturma derinliği:</strong> Parçanın boruya ne kadar girdiğini belirler; kısa oturma her çekişte oynama, fazla derin oturma takılma yaratır.</li>
<li><strong>Kilit tırnağının sayısı, açısı ve kalınlığı:</strong> Tırnak, cihazın kendi yuvasına aynı açıyla girmezse ya kilitlenmez ya da ilk kullanımda kopar.</li>
<li><strong>Tırnak esneme payı ve kök yarıçapı:</strong> Tırnağın açılıp geri gelmesini bu pay sağlar; köşe yuvarlatması olmayan tırnaklar genellikle aynı yerden kırılır. Kök kalınlığını, kol boyunu ve esneme payını nasıl dengelediğimizi <a href="/kirik-plastik-tirnak-yaptirma/">kırılan tırnağın yeniden üretimi</a> sayfasında ayrıntılı anlatıyoruz.</li>
<li><strong>Fırça kapağı uzunluğu ve kanal genişliği:</strong> Zemin temizleme makinesi plastik yedek parça işlerinde kapak, fırça milini boydan boya hizada tutar; kanal dar olursa fırça sıkışır, geniş olursa tıkırdar.</li>
<li><strong>Kapak vida delikleri arası mesafe ve delik çapı:</strong> Cihazın kendi vidalarıyla takılabilmesi için delik ekseni birebir korunur.</li>
<li><strong>Klips ve kilit dili yuva payı:</strong> Süpürge fırça kapağı yaptırma taleplerinde kapağın gövdeye tek elle oturması bu paya bağlıdır.</li>
<li><strong>Geçiş bileziğinin iki tarafı ayrı ayrı:</strong> Eski bir aparatı farklı çaptaki bir boruya bağlamak gerektiğinde her iki uç bağımsız ölçülür.</li>
<li><strong>Kenar kalınlığı ve iç kaburgalar:</strong> Zorlanan bölgede et kalınlığını artırır, gereksiz yerde ince tutarız; parça hem dirençli hem hafif kalır.</li>
<li><strong>Yüzey ve renk:</strong> Farklı renk seçenekleri sunarız; çoğu müşteriye cihazın gövde rengine yakın bir ton yeterli geliyor.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın gerçekten çalıştığı yere göre seçeriz, kimseyi gereksiz üst sınıfa itmeyiz. Kuru ortamda, motordan uzakta duran hafif bir kapak için standart sınıf bir mühendislik plastiği çoğu zaman yeterlidir ve daha ekonomiktir. Motor gövdesine yakın, ılık havanın geçtiği bileziklerde ve nemli çalışan zemin yıkama aparatlarında ısıya ve neme daha dayanıklı PETG tercih ederiz. Dış alanda, güneş gören bir aparat söz konusuysa ASA daha uygun olur; UV altında rengini ve tokluğunu daha iyi korur.</p>
<p>Sürekli takılıp çıkarılan, her seferinde esneyen kilit tırnaklarında ve fırça mili çevresinde sürtünmeye maruz kalan kapaklarda karbon ya da cam elyaf takviyeli PA-CF / PA-GF sınıfına çıkarız. Bu sınıf hem daha rijit hem de aşınmaya karşı daha dirençlidir. Hangi sınıfı önerdiğimizi ve nedenini fiyat vermeden önce yazılı olarak söyleriz; isterseniz aynı parçayı iki farklı sınıfta karşılaştırarak değerlendirebilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiklerimiz nettir: hortum ve boru tarafındaki bağlantı bilezikleri, geçiş bilezikleri, kilit tırnakları ve dilleri, fırça kapakları, aparat gövdesindeki klips ve tutamak parçaları, kırılan ek ağızları. Üretmediklerimiz de aynı ölçüde nettir: motor ve elektrik aksamı, anahtar ve kablo grubu, elektronik kart, filtre ve toz kesesi gibi gözenekli ya da dokuma ürünler bu işin dışındadır. Motorun içindeki, doğrudan yüksek ısıya temas eden parçalar da kapsam dışıdır.</p>
<p>Bir sınırı daha peşinen söyleriz: plastik bir aparat, çelik bir parçanın yerini her koşulda tutmaz. Sürekli darbe alan, üzerine ağırlık binen ya da çok yüksek kuvvetle zorlanan bir noktada plastik çözümün ömrü kısalır. Böyle bir durumda bunu açıkça söyler, ya kesiti güçlendirmeyi ya da o işi almamayı tercih ederiz. Ölçü sizden, üretim bizden — ama hangi ölçünün hangi malzemeyle anlamlı olduğunu da açıkça paylaşırız.</p>
<h2>Sipariş</h2>
<p>Kırık parçanın birkaç net fotoğrafını ve varsa cihaz modelini WhatsApp hattımıza gönderin: +90 545 138 6526. Ölçü ve malzeme netleştikten sonra siparişinizi siteden kartla online olarak tamamlayabilirsiniz; ölçüye özel işler de bu şekilde ödenebiliyor. Tek adet üretim yaparız, adet alt sınırı aramayız.</p>
<p>Süpürgenizde arıza dişli tarafındaysa <a href="/ev-aleti-plastik-disli-parca-uretimi/">ev aleti plastik dişli parça üretimi</a> sayfası daha yakın bir adres; evdeki büyük cihazların kırılan plastik detayları için <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> sayfasına, iki farklı ekipmanı birbirine bağlayan ara parça arıyorsanız <a href="/olcuye-ozel-adaptor-reduksiyon-gecis-uretimi/">ölçüye özel adaptör ve geçiş parçası üretimi</a> sayfasına göz atabilirsiniz.</p>""")


def _asinmaya_dayanikli_surtunme_parcasi_uretimi():
    return (u"""<h1>Sürte sürte boşluk yapan parçayı daha dirençli sınıfta üretelim</h1>
<p>Aşınan bir kızak ya da kılavuz parçası için raftan "benzeri" alındığında hikaye çoğu zaman aynı biter. Ölçü kabaca tutar: parça yuvasına girer, vidası denk gelir, ilk gün sorun görünmez. Ama kanal genişliği yarım milimetre fazladır, tırnak yüksekliği bir tık alçaktır, delik merkez mesafesi bir-iki milimetre kaymıştır. Bu küçük farklar parçayı yüzeyin tamamına değil tek bir şeride oturtur. Yük o dar şeride yığılır, hareket her seferinde aynı çizgiyi tırtıklar ve kısa süre sonra o tanıdık takırtı geri gelir. Aşınan kılavuz parçası muadili diye satılan ürünlerin çoğu tek bir popüler modele göre seri üretilmiştir; sizin makineniz o model değilse "yakın ölçü" size zaman kazandırmaz, sadece arızayı erteler.</p>
<p>İkinci sık hata malzeme tarafındadır. Muadil parça çoğu zaman sürtünme koşulu düşünülmeden, ucuz ve kolay işlenen bir sınıfta üretilir. Yüzey ilk temaslarda parlar, sonra tozumaya ve kendini yemeye ilk adımı atar. Boşluk yapan sürtünme parçası çözümü bu yüzden iki değişkende birden aranır: parçanın gerçek ölçüsü ve temas yüzeyinin malzeme sınıfı. Aynı ikili, kapı içinde ray boyunca sürterek çalışan <a href="/cam-krikosu-plastik-parcasi-yaptirma/">cam krikosu plastik parçası</a> için de geçerlidir; kızak yenildikçe cam eğik gitmeye başlar. Sürtünen kızak parçası özel üretim taleplerinde işe eski parçanın nerede ve nasıl yendiğini okuyarak gireriz; aşınma izi hem doğru ölçüyü hem de gereken malzeme sınıfını aynı anda söyler.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Elinizdeki aşınmış parçayı — kırık, yenmiş, yarısı kalmış olsun fark etmez — bize ulaştırın. Aşınmış bir parçanın üstündeki iz aslında en değerli bilgidir: hangi yüzeyin taşıdığını, temasın nereye yığıldığını, hareketin hangi yönde olduğunu gösterir. Ölçüyü biz alırız; siz sadece parçanın makinede nereye oturduğunu ve nasıl çalıştığını anlatın. Numune gönderemiyorsanız net fotoğraf ve birkaç kumpas ölçüsü de yeterli olur, eksik kalan yerleri sorarız.</p>
<p>Ardından ölçüyü ve önerdiğimiz malzeme sınıfını size yazılı geçeriz. Onaydan sonra üretim yapılır, tek adet de olsa aynı süreç işler. Aşınmaya dayanıklı plastik parça yaptırma işinde ölçü onayı en kritik adımdır; oradan sonrası mekaniktir.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Temas yüzeyi genişliği ve uzunluğu</strong> — yükün kaç milimetrekareye yayıldığını bu belirler; yüzey daralırsa aşınma hızlanır.</li>
<li><strong>Kanal / kızak ağız genişliği ve derinliği</strong> — karşı parçanın içinde sallanmadan yürümesi buna bağlıdır.</li>
<li><strong>Geçme payı</strong> — sıkı, kayar ya da bilinçli boşluklu; hareketin serbest mi yoksa sabit mi olması gerektiğine göre ayarlanır.</li>
<li><strong>Et kalınlığı ve destek kaburgası</strong> — parça eğilirse temas tek kenara kayar; kalınlık aşınmayı doğrudan etkiler.</li>
<li><strong>Delik çapı, delik merkez mesafesi ve havşa</strong> — mevcut vida düzenine birebir oturması için.</li>
<li><strong>Tırnak yüksekliği ve tutma açısı</strong> — tırnak alçak kalırsa parça oynar, yüksek kalırsa takarken zorlar.</li>
<li><strong>Köşe radyusu ve pah</strong> — keskin köşe hem takılmayı zorlaştırır hem çatlamanın ilk noktası olur.</li>
<li><strong>Yüzey tercihi</strong> — düz yüzey ya da yağ/tozu toplayan ince kanallar.</li>
<li><strong>Malzeme sınıfı</strong> — elyaf takviyeli sert yüzey mi, düşük sürtünmeli kaygan yüzey mi istendiği.</li>
<li><strong>Farklı renk seçenekleri</strong> — görünür yerlerde uyum için.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Standart sınıf, sürekli temas eden bir yüzeyde en zayıf tercihtir: ölçüyü tutar ama sürtünmeyi kaldıramaz. Bir üst kademede PETG ve ASA gibi sınıflar gelir; bunlar ısınan ortamlarda ve dış koşulda formunu daha iyi korur, orta yüklü kılavuz ve kaydırıcı yüzeylerde iş görür. Sürtünen yüzey aynı zamanda sürekli sıcak bir ortamda çalışıyorsa sınır aşınmadan önce ısı tarafında zorlanır; o durumda <a href="/isiya-dayanikli-plastik-parca-uretimi/">ısıya dayanıklı plastik parça üretimi</a> sayfamızdaki sınıflara bakarız. Yük ve hareket arttığında karbon veya cam elyaf takviyeli sınıflara (PA-CF / PA-GF) çıkarız — bu sınıflar daha sert, daha rijit bir yüzey verir ve aşınma altında ölçüsünü daha iyi koruma eğilimindedir.</p>
<p>Ama herkesi en üst sınıfa itmeyiz. Ayda birkaç kez hareket eden, düşük yüklü bir tutucu için elyaf takviyeli sınıf gereksiz masraftır; orada ara sınıf yeterlidir. Bazı durumlarda ise sert değil kaygan yüzey doğru cevaptır: karşı yüzeyi çizmemesi gereken parçalarda düşük sürtünmeli sınıf tercih edilir. Hangi sınıfın nerede işe yaradığını daha ayrıntılı görmek isterseniz malzeme tarafını ayrıca anlattığımız sayfamız var; takviyeli sınıfa çıkmanın bu parçada gerekli olup olmadığını <a href="/karbon-fiber-takviyeli-naylon-parca-ne-zaman-gerekir/">karbon fiber takviyeli naylon parça ne zaman gerekir</a> sayfasındaki sorularla tartabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ne üretiriz: kuru ya da hafif yağlı çalışan, orta hızlı ve orta yüklü sürtünme yüzeyleri — kızaklar, kaydırıcılar, aşınma plakaları, kılavuz dilleri, tırnaklı tutucular, yatak yüzeyleri. Bu yüzeylerin en hızlı yendiği yer taşıma hatlarıdır; kılavuz çıta, yan tutucu ve kızak profilinin ölçü listesini <a href="/konveyor-bant-plastik-parca-yaptirma/">konveyör bant plastik parçası yaptırma</a> sayfasında ayrı ayrı verdik.</p>
<p>Ne üretmeyiz: sürekli yüksek sıcaklık altında çalışan, metal yerine geçmesi beklenen taşıyıcı yatak yüzeyleri ve sert darbe alan emniyet parçaları. Bunlar plastiğin sınırının dışındadır ve size "olur" demeyiz. Aynı dürüstlük diğer işlerimizde de geçerli: pervane tarafında yalnız fan ve hafif çark üretiriz, tekne itiş pervanesi üretmeyiz; profil ve beam parçalarımız hafif, yük dışı kullanım içindir; conta işlerimiz düşük–orta zorlanma aralığındadır. Ölçü sizden, üretim bizden; ama parçanın çalışacağı yer plastiğin sınırını aşıyorsa bunu üretimden önce söyleriz.</p>
<h2>Sipariş</h2>
<p>Ölçüye özel işlerde kartla online ödeme yapabilirsiniz; ölçüsü size göre belirlenen parçalar da bu akışa dahildir. Emin olamadığınız bir nokta varsa önce WhatsApp'tan +90 545 138 6526 numarasına yazın, parçanın fotoğrafına bakıp ölçü ve malzeme sınıfını birlikte netleştirelim.</p>
<p>Konuyu derinleştirmek isterseniz sınıflar arasındaki farkı anlattığımız <a href="/malzeme-rehberi/">malzeme rehberimize</a> göz atabilir, dönen millerde çalışan yüzeyler için <a href="/numuneden-plastik-burc-rulman-uretimi/">numuneden burç ve rulman üretimi</a> sayfamızı inceleyebilir, aşınan parça bir tezgâhın veya hattın içindeyse <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfamızdan devam edebilirsiniz.</p>""")


def _yaga_ve_kimyasala_dayanikli_plastik_parca_uretimi():
    return (u"""<h1>Yağ değen yerde yumuşayan parçayı doğru malzemeyle üretelim</h1>
<p>Yağ değen bir plastik parçanın bozulması çoğu zaman sessiz olur. Vidayı sökersiniz, parça elinizde eğilir; kenarı yumuşamış, yüzeyi yapış yapış olmuştur. Yenisini ararsanız aynı aparat genelde tek olarak değil, komple grubun içinde satılır; servise sorarsanız parçayı görmeden fiyat vermiyorlar, gördükten sonra da modülün tamamının değişmesini öneriyorlar. İnternetten ölçüsü yakın görünen bir muadil ısmarlarsanız o da ya deliklere oturmuyor ya da oturuyor, fakat birkaç hafta yağın içinde kaldıktan sonra yine şişiyor, kenarları yumuşuyor. Yağa dayanıklı plastik parça özel üretim aramanızın nedeni genellikle bu tekrardır: ölçü doğruydu, yanlış olan parçanın temas ettiği sıvıya göre seçilen sınıftı.</p>
<p>Yağ, solvent ve temizlik kimyasalı teması, plastik bir parçayı kırarak değil yavaşça gevşeterek bitirir. Bozulma çatlamayla değil, yüzeyden içeri doğru ilerleyerek olur: önce yüzey mattan yapışkana döner, sonra vidalı bölge tutuşunu kaybeder, en son ölçüsü kayar. Bu yüzden solvent temas eden plastik parça üretimi işi, ölçü işinden önce malzeme işidir. Parçanın nerede durduğunu, hangi sıvıya, ne sıklıkta ve kaç derecede temas ettiğini öğrenmeden alınan ölçü bizim için eksik veridir.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>İlk adım numunedir. Kırılan, şişen ya da yumuşamış parçanın kendisi elimize ulaşırsa en sağlıklısı olur; ulaşamıyorsa iki taraflı net fotoğraf ve kumpas ölçüleri de yeterlidir. WhatsApp'tan gönderdiğiniz görsele bakarken size üç soru sorarız: parça hangi sıvıya değiyor (motor yağı mı, hidrolik yağ mı, tiner–alkol sınıfı bir çözücü mü, yoksa köpüklü sanayi temizleyicisi mi), temas sürekli mi yoksa ara ara mı, ve o bölge çalışırken kaç dereceye çıkıyor.</p>
<p>Ölçüleri çıkardıktan sonra parçayı sıvıya uygun sınıfta üretiriz. Deforme olmuş bir numuneyi ölçerken şişmiş bölgeyi olduğu gibi kopyalamayız; komşu yüzeylerden ve montaj noktalarından orijinal ölçüyü geri kurarız. Tek adet de üretiriz, aynı parçadan birkaç yedek de.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Kompresör çevresi plastik aparat yaptırma ya da yağ hattı yakınındaki bir tutucu için ölçü listemiz şudur:</p>
<ul>
<li><strong>Dış çap ve iç çap:</strong> geçtiği mile, boruya veya hortuma tam oturması için ikisini ayrı ayrı ayarlarız; yağlı yüzeyde gevşek geçen parça zamanla yerinden döner.</li>
<li><strong>Et kalınlığı:</strong> temas eden yüzey kalınlaştıkça sıvının içeri ilerlemesi zorlaşır, bu yüzden kritik bölgede kalınlığı ölçünüzün izin verdiği kadar artırırız.</li>
<li><strong>Delik çapı ve delik merkez mesafesi:</strong> mevcut cıvata düzenine birebir uyması gerekir; tek milimetrelik kayma parçayı gergin çalıştırır.</li>
<li><strong>Kanal genişliği ve derinliği:</strong> hortum kelepçesi, klips ya da o-ring yatağı gibi kanallar ölçünüze göre açılır.</li>
<li><strong>Diş ölçüsü ve yönü:</strong> metrik diş adımı, dişin uzunluğu ve sağ–sol yönü orijinaline göre üretilir.</li>
<li><strong>Açı ve eğim:</strong> yağın üzerinde durmayıp akması istenen yüzeylerde eğimi biz belirleriz, damlama yönünü siz söylersiniz.</li>
<li><strong>Flanş çapı ve toplam yükseklik:</strong> dar hacimlerde parçanın komşu gövdeye çarpmaması için yükseklik ölçünüze çekilir.</li>
<li><strong>Köşe radüsü:</strong> keskin iç köşe, kimyasal temasında ilk yorulan noktadır; radüsü büyüterek bunu azaltırız.</li>
<li><strong>Farklı renk seçenekleri:</strong> bakım sırasında kolay ayırt edilsin diye parçayı ayrı renkte üretebiliriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Merdiveni gereğinden yukarı tırmandırmayız. Yağ teması seyrekse, oda sıcaklığındaysa ve parça yalnızca konum tutuyorsa standart sınıf çoğu zaman yeterlidir; bunun için sizden fazla ücret istemeyiz.</p>
<p>Sürekli yağ, gres ya da köpüklü temizleyici teması varsa ve bölge ısınıyorsa bir üst kademeye geçeriz: PETG ve ASA sınıfları yağ ile alkol bazlı temizleyicilere karşı belirgin biçimde daha kararlıdır, ASA ayrıca güneş altında rengini ve formunu daha iyi korur. Aynı ikili zorlama — kimyasal teması ve gün boyu güneş — havuz çevresindeki parçalarda birlikte görülür; o parçaların sınıf seçimini <a href="/havuz-ekipmani-plastik-parca-yaptirma/">havuz ekipmanı parça üretimi</a> sayfasında ayrıca anlatıyoruz. Motor bölgesi, kompresör çevresi, hidrolik hat yakını gibi hem sıcak hem sürekli temaslı yerlerde ise karbon veya cam elyaf takviyeli PA-CF ve PA-GF sınıflarını öneririz; bu sınıflar sıcakken de formunu daha iyi koruduğu için sıvı teması altında ölçüsünü daha iyi tutar. Kimyasala dirençli plastik parça derken kastettiğimiz budur: sonsuz dayanım değil, o sıvıya ve o sıcaklığa göre doğru seçilmiş sınıf.</p>
<h2>Dürüst sınır</h2>
<p>Üretiriz: yağ, gres, hidrolik sıvı, motorin, alkol ve yaygın sanayi temizleyicisi teması olan tutucular, kapaklar, aparatlar, geçiş elemanları ve muhafazalar. Temas sürekli olsa bile, doğru sınıf seçildiğinde makul bir servis ömrü hedefleriz.</p>
<p>Üretmeyiz ya da açıkça uyarırız: gıdayla temas eden parçalar ve içme suyu hattına giren elemanlar kapsamımız dışındadır. Güçlü asit, kostik ve klorlu çözücü gibi agresif kimyasallarda plastik sınıfının bir sınırı vardır; böyle bir temas tarif ederseniz size en yakın seçeneği söyler, garanti edemeyeceğimiz noktayı da aynı netlikte söyleriz. Yakıt hattının içinde kalan ve alev bölgesine değen parçalar da bizim işimiz değildir. Numuneniz kimyasaldan yumuşamış geliyorsa, aynı sınıfın tekrarını değil bir üst kademeyi öneririz — yoksa aynı sonucu birkaç ay sonra yeniden yaşama ihtimaliniz yüksektir.</p>
<h2>Sipariş</h2>
<p>Parçanızın fotoğrafını ve ölçülerini WhatsApp'tan +90 545 138 6526 numarasına gönderin; hangi sıvıya değdiğini de yazın, size uygun sınıfı ve fiyatı çıkaralım. Ölçüye özel işler dahil olmak üzere siteden kartla online ödeme yapabilirsiniz. Ölçü sizden, üretim bizden.</p>
<p>Hangi sınıfın nerede durduğunu kendiniz karşılaştırmak isterseniz <a href="/malzeme-rehberi/">malzeme rehberimize</a> göz atın. Yağ ve temizleyici teması çoğunlukla bir makinenin çevresinde olur; o tarafta <a href="/makine-parcasi-olcuye-ozel-uretim/">ölçüye özel makine parçası üretimi</a> sayfamız daha ayrıntılıdır. Sıvı geçişini kesen yumuşak elemanlar arıyorsanız <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a> sayfamıza geçebilirsiniz.</p>""")


def _kalip_yaptirmadan_parca_urettirme():
    return (u"""<h1>Kalıp masrafına girmeden 1-200 adet parça nasıl ürettirilir</h1>
<p>Kalıp yaptırmadan parça ürettirme işini şöyle yapıyoruz: elinizdeki numuneyi ya da ölçü listesini alırız, ilk numuneden iki yüz adete kadar aynı yoldan üretiriz. Arada kalıp yok; dolayısıyla kalıp bedeli, kalıp bekleme süresi ve kalıp üzerinde revizyon derdi de yok. Küçük seri parça ürettirmek isteyen atölyenin, makine imalatçısının ya da kendi ürününü toparlayan girişimcinin karşısına çıkan asıl duvar budur: parçanın kendisi değil, o parçayı üretilebilir hale getirmenin sabit maliyeti.</p>
<p>Az adetli seri plastik parça üretiminde karar ekseni tektir: kaç adet lazım ve bu adet ne sıklıkla tekrarlanacak? Yılda birkaç kez onar-yirmişer ilerleyen bir ihtiyaçta sabit kalıp yatırımı çoğu zaman kendini toplamaz; para kalıba yatar, stok rafta bekler, üstelik parçada küçük bir ölçü düzeltmesi gerektiğinde yatırım da çöpe gider. Kalıpsız plastik parça üretiminde ise maliyet adete dağılır: az adette birim daha yüksektir ama peşin ve geri dönüşsüz bir yatırım yapmazsınız. Adet arttıkça birim aşağı iner, çünkü ölçü işi, ilk numune ve hazırlık bir kez yapılır; sonraki adetler doğrudan üretime düşer. Adet ile birim fiyat arasındaki bu ilişkiyi ve fiyatı belirleyen diğer kalemleri <a href="/ozel-parca-uretimi-fiyati-nasil-belirlenir/">özel parça üretimi fiyatı nasıl belirlenir</a> sayfasında kalem kalem açıkladık.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p><strong>Getir.</strong> Kırık ya da sağlam numuneyi elden getirin, adresimize gönderin veya fotoğrafla birlikte ölçüleri iletin. Tek bir teknik çizim de yeterlidir; çizim yoksa numuneden ölçü çıkarırız.</p>
<p><strong>Ölç.</strong> Parçayı milimetrik ölçeriz. Kritik yerler (delik merkezleri, geçme payları, diş ölçüsü) tek tek not edilir ve size onaylatılır. Ölçüde belirsizlik varsa önce tek adet numune üretir, yerine taktırırız; seriye ancak numune yerine oturduktan sonra geçeriz. Bu deneme adımı, küçük seri çalışmanın size sağladığı güvenlik ağıdır.</p>
<p><strong>Üret.</strong> Onaylı ölçü dosyanız bizde kayıtlı kalır. Altı ay sonra otuz adet daha istediğinizde süreci yeniden kurmayız; kayıttan üretime geçeriz. Aynı ölçünün ikinci partisinde hazırlık işi tekrarlanmadığı için birim de aşağı iner. Ölçüde küçük bir değişiklik gerekiyorsa (delik iki milim kaysın, kalınlık artsın) yeni bir yatırım gerekmez, tek kalem düzeltmeyle sonraki parti değişmiş halde çıkar. Küçük seride revizyon kolaylığı, kalıpsız çalışmanın en somut kazancıdır.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Aşağıdaki maddeler, az adetli işlerde en sık ayarladığımız gerçek ölçülerdir. Hangisini bildiriyorsanız onu esas alırız, kalanını numuneden okuruz.</p>
<ul>
<li><strong>Dış ölçü / gövde ebadı:</strong> Parçanın oturduğu yuvaya birebir uyması için ana ölçüler sizin numunenizden alınır.</li>
<li><strong>Et kalınlığı:</strong> Zorlanan yerde kalınlık artırılır, hafiflik gerekiyorsa incelir; parçanın dayanımını doğrudan etkileyen ölçü budur.</li>
<li><strong>Delik çapı ve delik merkez mesafesi:</strong> Mevcut civata deliklerinizle çakışması gerekir; birkaç milim kayma parçayı kullanılmaz kılar.</li>
<li><strong>Geçme payı (tolerans):</strong> Sıkı geçme mi, serbest dönme mi istiyorsunuz — pay buna göre ayarlanır.</li>
<li><strong>Diş adımı ve diş yönü:</strong> Vidalanan parçalarda mevcut dişinize uyumlu adım verilir, sağ/sol yön ayrı belirtilir.</li>
<li><strong>Kanal / oluk genişliği ve derinliği:</strong> Kayış, kablo, keçe ya da conta oturan yataklarda kanal ölçüsü işlevi doğrudan belirler.</li>
<li><strong>Açı ve eğim:</strong> Bağlantı açısı, akış eğimi veya montaj yatkınlığı gereken yerlerde derece bazında ayarlanır.</li>
<li><strong>Köşe radyusu ve pah:</strong> Yorulma çatlağı çoğu zaman keskin köşeden yürür; radyus vererek bunu azaltırız.</li>
<li><strong>Adet ve renk:</strong> İlk numuneden küçük seriye kadar aynı ölçüyle üretilir, farklı renk seçenekleri sunulur.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalıştığı yere göre seçeriz, faturayı şişirmek için üst sınıfa itmeyiz. İç mekânda, ısınmayan ve zorlanmayan bir aparat standart sınıfla gayet iyi çalışır. Güneş altında, açık havada, nemli veya sıcak ortamda duran parçalarda ısı ve UV dayanımı yüksek sınıfa (PETG ve ASA) çıkarız. Sürekli yük alan, titreşen, dişli gibi zorlanan ya da rijitliği kritik parçalarda karbon/cam elyaf takviyeli sınıfı (PA-CF / PA-GF) öneririz. Küçük seride bunun ek bir avantajı var: aynı ölçüyü farklı malzemede deneyip sahada hangisinin tuttuğunu görebilirsiniz. Kalıba yatırım yapıldığında bu esneklik büyük ölçüde daralır.</p>
<h2>Dürüst sınır</h2>
<p>Adet binlere çıkıyorsa ve ölçü artık değişmeyecekse, kalıplı seri üretim uzun vadede daha mantıklıdır; bunu size açıkça söyleriz, iş almak için tersini savunmayız. Bizim alanımız küçük seri ve tekrar siparişin sürdüğü 1-200 adet aralığı ile ölçünün hâlâ oturmakta olduğu dönemdir.</p>
<p>Ürettiklerimiz: aparat, braket, tutucu, ara parça, muhafaza, dişli, kasnak, klips ve benzeri işlevsel parçalar. Pervane işinde yalnızca fan ve hafif çark üretiriz — tekne itişi sağlayan pervane bizim işimiz değildir. Profil ve beam türü parçalar hafif ve yük dışı kullanım içindir; taşıyıcı gövde olarak verilmez. Sızdırmazlık parçaları düşük ve orta zorlanma içindir. Motor içi yüksek sıcaklık bölgesi, emniyet kritik bağlantılar ve gıda/tıbbi sertifika gerektiren üretimler kapsam dışıdır. Kapsam dışında kalan işlerin tamamını ve her birinin gerekçesini <a href="/hangi-parcalar-ozel-uretimle-yapilamaz/">hangi parçalar özel üretimle yapılamaz</a> sayfasında topladık.</p>
<h2>Sipariş</h2>
<p>Ölçü netse siparişi doğrudan siteden verip kartla online ödeyebilirsiniz; ölçüye özel işler de kartla ödemeye açıktır. Emin değilseniz önce konuşalım: numunenin fotoğrafını ve kritik ölçüleri WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin, adet aralığınıza göre en doğru yolu birlikte belirleyelim. Elinizde bir adet planı varsa — şimdi on, üç ay sonra elli gibi — bunu önceden iletin; ölçü kaydını buna göre hazırlarız. Ölçü sizden, üretim bizden.</p>
<p>Tek bir acil yedek parça yeterliyse konu ayrıdır; <a href="/tek-adet-ozel-parca-uretimi/">tek adet özel parça üretimi</a> sayfası o akışı anlatıyor; elinizde kırık ya da sağlam bir örnek varsa <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> ile ölçüyü nasıl çıkardığımızı görebilirsiniz. İhtiyacınız bir tezgâh ya da hat parçasıysa <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfasına göz atın.</p>""")



def _plastik_pim_yaptirma():
    return (u"""<h1>Kaybolan ya da kırılan plastik pimi ölçüsüne göre üretiyoruz</h1>
<p>Kuru bir "çıt" sesi duyulur. Dolap kapağını her zamanki gibi çekmişsinizdir, mekanizma bir an takılmış, sonra kapak elinizde kalmıştır. Yere eğilip bakarsınız: parmak ucu kadar, bir ucu kırılmış küçük bir plastik pim, halının kenarında durmaktadır. Kimi zaman ses bile çıkmaz — muhafazanın kapağını açarsınız, pim yuvasından kayıp gitmiştir ve nereye düştüğü belli değildir. Tek eksik odur; onun yerine geçecek doğru çapta bir parça bulana kadar mekanizma çalışmaz.</p>
<p>Plastik pim yaptırma ihtiyacı çoğu zaman böyle küçük bir andan doğar. Pim standart bir vida değildir: çapı ondalıklıdır, boyu yuvaya göre kesilmiştir, ucu yuvaya rahat girsin diye pahlıdır. Yanlış çapta bir muadil taktığınızda ya yuvaya oturmaz ya da boşluk yapıp mekanizmayı tekrar tekrar çıkarır. Biz ölçüye özel plastik pimi tam bu ölçülerle üretiyoruz: kırık parçayı ya da yuvanın ölçüsünü alırız, çapı ve boyu kumpas ile okuruz, geçme payını sizin uygulamanıza göre veririz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Elinizde kırık pimin parçaları varsa iş kolaydır: iki yarımı yan yana koyup toplam boyu, gövde çapını ve varsa omuz kalınlığını ölçeriz. Parça tamamen kaybolduysa yuvadan gideriz — deliğin çapını, derinliğini ve pimin geçtiği kulakçıkların arasındaki mesafeyi ölçmenizi isteriz. Net fotoğraf, yanına konmuş bir cetvel ve iki üç kumpas değeri genelde yeterlidir. Dolap içindeki raf deliğine oturan tipteyse <a href="/olcuye-ozel-raf-pimi-tutucu-uretimi/">dolap raf pimi ve raf tutucusu üretimi</a> sayfasındaki delik çapı ölçüleri işinizi görür.</p>
<p>Ölçüleri aldıktan sonra size hangi payla çalışacağımızı söyleriz: pim yuvada dönecekse serbest geçme, sabit duracaksa sıkı geçme. Onayınızdan sonra parçayı üretir, gerekirse ilk parçayı deneme olarak gönderip oturmasını teyit ederiz. Koşul açık: sapma bizim aldığımız ölçüden kaynaklanıyorsa yeniden üretim bizdendir; ölçüyü siz değiştirirseniz bu yeni bir iş olarak fiyatlandırılır. Ölçü sizden, üretim bizden — bu akış boyunca sizden istediğimiz tek şey birkaç doğru rakamdır.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Gövde çapı (0,1 mm kademelerle):</strong> Pimin işini yapan ana ölçü budur; onda bir milimetrelik fark bile mekanizmanın boşluk yapmasıyla pimin yuvaya oturmaması arasındaki farktır.</li>
<li><strong>Toplam boy ve omuz altı boy:</strong> Kulakçıklar arasındaki mesafeye göre belirlenir; kısa kalırsa pim tek taraftan tutar, uzun kalırsa gövdeye sürter.</li>
<li><strong>Uç formu:</strong> Düz, pahlı, küresel ya da mantar tepe. Pahlı uç yuvaya kendiliğinden merkezlenir, mantar tepe ise pimin karşı taraftan kaçmasını zorlaştırır.</li>
<li><strong>Omuz / flanş çapı ve kalınlığı:</strong> Pimin yuvaya belli bir derinlikten fazla girmesini engelleyen durdurucudur; menteşe ve muhafaza pimlerinde eksenin yerinde kalmasını bu ölçü sağlar.</li>
<li><strong>Geçme payı (tolerans):</strong> Dönen pimde bir miktar boşluk bırakırız; sıkı oturması gereken pimde payı en aza indiririz. Milimetre altı geçmelerde ilk parçayı deneme olarak üretip ölçüyü birlikte oturturuz. Aynı çapta iki pim, payı yüzünden büsbütün farklı davranır.</li>
<li><strong>Emniyet deliği ya da kanal:</strong> Kopilya, tel ya da segman kullanılacaksa deliğin çapını ve uçtan mesafesini, kanal kullanılacaksa yuva genişliğini ölçünüze göre açarız.</li>
<li><strong>Kafa formu:</strong> Düz, tırtıllı ya da elle çekilebilen küçük tutamaklı. Sık sökülüp takılan mekanizmalarda tırnak yerine parmakla çalışan bir kafa işi kolaylaştırır.</li>
<li><strong>Adet ve farklı renk seçenekleri:</strong> Tek pim de üretiriz, aynı ölçüden takım da. Görünen yerlerdeki pimler için farklı renk seçenekleri sunarız.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Pimi çalıştığı yere göre seçeriz, gereksiz üst sınıfa itmeyiz. Ev içinde, ılıman ortamda, düşük yükle çalışan bir dolap ya da muhafaza pimi için standart sınıf yeterlidir ve en ekonomik seçenektir.</p>
<p>Sıcak bölgeye yakın, güneş gören ya da nemli ortamda duran pimlerde bir üst kademeye çıkarız: PETG ve ASA sınıfı malzemeler ısı ve UV karşısında formunu daha iyi korur. Dış mekânda, balkonda, araç içinde ya da deniz havasına açık yerlerde tercihimiz bu gruptur.</p>
<p>Sürekli hareket eden, yana yük alan, sürtünmeyle çalışan pimlerde karbon ya da cam elyaf takviyeli PA-CF / PA-GF sınıfına geçeriz. Bu sınıf daha rijittir ve tekrarlı harekete karşı daha iyi durur. Ancak sizden gelen bilgi "hafif bir kapak menteşesi" ise sizi bu sınıfa yönlendirmeyiz; ödediğiniz farkın karşılığını almanız gerekir. Hangi kademenin yeterli olduğunu, pimin taşıdığı yükü ve çalıştığı ortamın sıcaklığını konuşarak birlikte belirleriz.</p>
<h2>Dürüst sınır</h2>
<p>Ne üretiriz: mekanizma, menteşe, kapak ve muhafaza pimleri; eksen görevi gören, dönme ya da eksen tutma işi yapan küçük çaplı pimler; emniyet deliği veya kanalı olan pim takımları; kaybolan orijinalin ölçüsünden yeniden üretim.</p>
<p>Bu sayfanın konusu dışında kalanlar: yüksek tork aktaran mil ve şaft işleri. Bir pim, dönme hareketini taşımak yerine bir motorun ya da kompresörün gücünü aktarıyorsa, plastik bir eksenin yeri orası değildir; böyle bir işi bize gönderdiğinizde metal çözüme yönlendiririz. Aynı şekilde darbeyle çakılan, çekiçle yerine oturtulan pimler de bu sayfanın kapsamı dışındadır. Sınırı önden söylememiz, parçanın yerinde ne kadar dayanacağını konuşmadan sipariş almamızdan daha değerlidir.</p>
<h2>Sipariş</h2>
<p>Ölçüleriniz netse siparişi doğrudan sitemizden verebilirsiniz; ölçüye özel işler dahil kartla online ödeme açıktır. Emin olmadığınız bir çap, bir pay ya da bir uç formu varsa önce konuşalım: WhatsApp +90 545 138 6526 numarasına kırık parçanın fotoğrafını ve kumpas değerlerini gönderin, uygun malzemeyi ve payı birlikte belirleyelim.</p>
<p>Pimle birlikte menteşenin gövdesi de kırıldıysa <a href="/olcuye-ozel-mentese-uretimi/">ölçüye özel menteşe üretimi</a> sayfasına, pimin döndüğü yuvada boşluk oluştuysa <a href="/numuneden-plastik-burc-rulman-uretimi/">numuneden burç ve yatak üretimi</a> sayfasına göz atın. Kumpasınız yoksa ya da ölçüyü nasıl aktaracağınızdan emin değilseniz <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır ve gönderilir</a> rehberimiz sırayla anlatıyor.</p>""")


def _kirik_plastik_tirnak_yaptirma():
    return (u"""<h1>Kapağı tutan tırnak kırıldıysa gövdeyi değiştirmenize gerek yok</h1>
<p>Kenardaki küçük tırnak kırıldı diye koca kapağı ya da gövdeyi yenilemek gerekir mi? Çoğu durumda hayır. Kırık plastik tırnak yaptırma işi tam olarak bu sorunun cevabıdır: kapağı yerinde tutan geçme tırnağı ölçüsüne göre yeniden üretilir, kapağın kendisi ve oturduğu gövde olduğu gibi kalır. Tırnak milimetrik bir ayrıntıdır; yüksekliği, kök kalınlığı ve esneme payı doğru tutturulduğunda kapak yine tanıdık "klik" sesiyle oturur.</p>
<p>Peki tırnak neden kırılır? Çünkü görevi gereği her açıp kapamada esner. Zamanla, sıcakla ve güneşle sertleşen malzeme bir gün esnemek yerine kökünden kopar. Kopan yer çoğu zaman tek bir noktadır: kolun gövdeye bağlandığı dip. Kapak artık kapanır ama tutmaz, titreşimle açılır, kenarı kalkar. Geçme tırnak üretimi bu tek noktayı hedefler; kapak tırnağı yaptırma dediğimiz iş, kırılan kolu ve çengeli aynı geometride yeniden ortaya koymaktır.</p>
<p>Elinizde kırık parçanın kendisi varsa iş kolaydır: iki yarımı yan yana koyup ölçeriz. Kırık parça kaybolduysa da yol kapanmaz; tırnağın oturduğu karşı yuva, gövdedeki iz ve kapağın kenar profili bize gereken ölçüleri verir. Plastik tırnak yenileme talebinin büyük kısmı bu şekilde, tek fotoğraf ve birkaç kumpas ölçüsüyle çözülür.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Üç adımlık net bir akış izliyoruz. <strong>Getir:</strong> kırık tırnağı, kapağı ya da mümkünse ikisini birden bize ulaştırın; gönderiyle yollayabilir, elden bırakabilirsiniz. <strong>Ölç:</strong> parçayı kumpasla ölçer, karşı yuvaya geçme miktarını ve kolun esneme payını çıkarırız. Ölçüde tereddüt varsa sizi arar, parçanın çalıştığı yeri sorarız — kapağın ne sıklıkla açıldığı, güneş görüp görmediği malzeme kararını doğrudan etkiler. <strong>Üret:</strong> onayınızdan sonra tırnağı ölçünüze göre üretir, ilk denemede oturmazsa esneme payını ve geçme derinliğini düzelterek revize ederiz. Koşulu şimdiden yazalım: sapma bizim aldığımız ölçüden kaynaklanıyorsa revizyon bizdendir; parçanın ölçüsü sizin tarafınızda değişirse bu yeni bir iş olarak fiyatlandırılır.</p>
<p>Kapağı sökemiyorsanız ölçüyü kendiniz de alabilirsiniz; hangi kotların gerektiğini adım adım anlattığımız bir sayfamız var ve çoğu kişi için kısa süren bir iştir; <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır ve gönderilir</a> rehberi gerekli kotları sırayla anlatır.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Bu parçada "yaklaşık" diye bir şey yok; tutan da kıran da onda birlik farklardır. Ayarladığımız ölçüler:</p>
<ul>
<li><strong>Tırnak (çengel) yüksekliği:</strong> karşı yuvaya ne kadar dalacağını belirler; az olursa kapak titreşimde kurtulur, fazla olursa kapak zorlanmadan açılmaz.</li>
<li><strong>Geçme derinliği ve giriş rampası açısı:</strong> kapağı iterken hissettiğiniz direnç bu açıdan gelir. Yumuşak giriş, sert tutuş isteniyorsa giriş ve tutuş açıları ayrı ayrı verilir.</li>
<li><strong>Kök kalınlığı:</strong> kırılmanın gerçekleştiği yer burasıdır. Kalın kök daha güçlü ama daha az esner; kalınlığı kolun uzunluğuna göre dengeleriz.</li>
<li><strong>Kol uzunluğu ve esneme payı:</strong> tırnağın kaç milimetre yana verip geri döneceği. Kısa kolda aynı esneme çok daha fazla zorlanma demektir; kolu uzatarak aynı tutuşu daha rahat sağlarız.</li>
<li><strong>Tırnak genişliği:</strong> yuvanın ağzına göre ayarlanır, yanal boşluk kalmasın diye.</li>
<li><strong>Kök kavisi (radius):</strong> dipteki keskin köşe çatlağı davet eder; kavis vererek yükü yayarız.</li>
<li><strong>Oturma yüzeyi ve delik mesafeleri:</strong> tırnak ayrı bir parça olarak vidalanıp yapıştırılacaksa taban plakasının ölçüsü, delik çapı ve delikler arası mesafe birebir çıkarılır.</li>
<li><strong>Adet ve renk:</strong> aynı kapakta genelde iki ya da dört tırnak vardır; hepsini birden yenilemek çoğu zaman mantıklıdır. Gövdeye yakın olsun diye farklı renk seçenekleri sunuyoruz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Tırnak, mukavemetten önce <strong>esneklik</strong> ister; en sert malzeme burada en iyi malzeme değildir. İç mekanda, ılık ortamda çalışan bir kapak tırnağı için standart sınıf ya da esnekliğini koruyan PETG çoğu zaman yeterlidir ve gereksiz yere üst sınıfa itmeyiz.</p>
<p>Güneş gören, dışarıda duran, sıcakta kalan kapaklarda (araç içi, dış ünite kapağı, bahçe ekipmanı) ısıya ve morötesi ışınlara dayanıklı ASA sınıfına çıkarız; bu sınıf yaz sıcağında ve güneş altında esnekliğini daha iyi korur. Sık açılan, yüklenen, sürtünen tutucularda ise karbon veya cam elyaf takviyeli PA-CF / PA-GF sınıfını öneririz — ama sadece kolun geometrisi buna izin veriyorsa, çünkü takviyeli sınıf daha rijittir ve ince, uzun esneyen bir kolda avantaj sağlamayabilir. Hangi sınıfı seçeceğimize parçanın çalıştığı yere göre karar veririz; malzeme merdiveninin tamamını ayrı bir rehberde açıkladık.</p>
<h2>Dürüst sınır</h2>
<p>Ne yaparız: kapak, panel, muhafaza ve kutu kapaklarındaki geçme tırnaklarını, tek tırnaklı kolları, çift taraflı kelepçe tırnaklarını ve ayrı vidalanan tırnaklı tutucuları ölçüye göre üretiriz. Kırık parçadan da, karşı yuvadan da ölçü çıkarabiliriz.</p>
<p>Ne yapmayız: her kırık gövde kurtarılamaz. Tırnağın oturacağı yüzey çatlamış, gövdenin kendisi ezilmiş ya da yuva ağzı kopmuşsa yeni tırnak da tutunacak sağlam bir zemin bulamaz — bu durumda size açıkça söyler, boşuna ücret almayız. Aynı şekilde kapağın tamamının taşıyıcı bir yük altında çalıştığı, çarpma emniyeti gibi can güvenliğine bağlı uygulamalara girmiyoruz. Kilit, mandal ve hareketli bağlantı elemanları da üretiyoruz; onlar bu sayfanın konusu dışında, kendi sayfalarında anlatılıyor.</p>
<h2>Sipariş</h2>
<p>Kırık tırnağın ve kapağın fotoğrafını çekin, elinizde kumpas varsa birkaç ölçüyü de ekleyin. Siteden kartla online ödeme yapabilirsiniz — ölçüye özel işler dahil. Emin olamadığınız her şey için WhatsApp'tan yazın: <strong>+90 545 138 6526</strong>. Fotoğrafa bakıp ölçünün alınabilir olup olmadığını, kaç adet gerektiğini ve hangi malzeme sınıfının uygun olduğunu söyleriz. Ölçü sizden, üretim bizden.</p>
<p>Kırılan parçanın tırnak mı yoksa kilitleyen bir dil mi olduğundan emin değilseniz <a href="/olcuye-ozel-mandal-kilit-dili-uretimi/">ölçüye özel mandal ve kilit dili üretimi</a> sayfasına da göz atın; aynı arızanın iki farklı adıdır. Kapağı tutan eleman ayrı bir gövdeye geçen bir parçaysa <a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe üretimi</a> sayfası daha uygun olabilir. Kırılan yalnızca tırnak değil de parçanın gövdesiyse <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> sayfasında genel akışı bulursunuz.</p>""")


def _cekmece_rayi_plastik_parcasi_yaptirma():
    return (u"""<h1>Ray komple satılıyorsa kırılan tek plastiği ölçüsüne göre üretelim</h1>
<p>Çekmece rayları raftan bakıldığında birbirinin kopyası gibi durur: aynı uzunluk, aynı çelik ton, aynı iki kanal. Ayrım, gözle seçilmeyen yerdedir. Bir markanın kızak dili 3,2 mm, ötekinin 3,6 mm'dir; durdurucunun kanca yüksekliği yarım milimetre oynar; makaranın dış çapı 14 yerine 15 mm, pim deliği 4 yerine 4,2 mm'dir. İşte bu yarım milimetreler yüzünden hırdavatçıdan alınan "uyar" denilen plastik ya kanala girmez ya da girer ama boşluk yapar, çekmece tıkırdayarak yürür. Çekmece rayı plastik parçası yaptırma talebinin arkasında neredeyse her zaman bu ölçü uyuşmazlığı vardır: parça piyasada yok değildir, sizin rayınıza uyanı yoktur.</p>
<p>Mobilyacı ya da mutfak firması çoğu kez tek plastiği ayrı vermez; rayın tamamını, çoğu zaman da sağ-sol çift olarak satar. Yeni rayın delik aralığı yan panele oturmayınca iş, kabin gövdesini yeniden delmeye kadar gider. Oysa kırılan çoğunlukla rayın ucundaki çekmece rayı durdurucusu, kanalda kayan kızak dili ya da tek bir makaradır. Elinizdeki kırık parçayı ölçer, aynı geometride yenisini üretiriz; ray da mobilya da yerinde kalır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Üç aşamalı, açık bir yol izliyoruz. Önce parçayı getirirsiniz: iki yarısı elinizde duran bir durdurucu, kopmuş bir kızak dili ya da yuvasından çıkmış bir makara bizim için yeterli numunedir. İkinci aşamada ölçeriz — kumpas ile dış çap, kanal genişliği, kalınlık, delik merkezleri ve varsa eğim açısı alınır; kırık yüzeyler karşılıklı getirilerek kayıp bölge tamamlanır. Üçüncü aşamada parça üretilir ve size ulaştırılır. Deneme parçası isteyen işlerde önce tek adet çıkarılır, rayına takılıp doğrulandıktan sonra kalan adetler tamamlanır; böylece ölçü hatası çoğalmadan yakalanır. Deneme tutmazsa ölçüyü kimin verdiğine bakarız: kot bizim ölçümümüzden kaydıysa yeni parçayı ücretsiz üretiriz; ray ya da çekmece tarafındaki ölçü sizin isteğinizle değişirse bu ayrı bir iş olarak fiyatlandırılır. Numuneyi göndermeden önce ölçüyü kendiniz almak isterseniz <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır ve gönderilir</a> anlatımı yeterli olacaktır.</p>
<p>Numune tamamen kayıpsa da yol var: rayın uzunluğu, kanal kesiti ve sağlam duran karşı taraftaki eş parçanın fotoğrafı üzerinden gidilir. Çekmecenin sağ tarafı sağlamsa, sol tarafın parçası onun ayna kopyası olarak üretilir. Ray kızak dili yaptırma da çekmece makarası yaptırma da bu şekilde tek parça hâlinde çözülür.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Kanal genişliği ve kızak dili kalınlığı:</strong> Parça kanal içinde ne sıkışmalı ne salınmalı; çekmecenin sessiz ve düzgün kaymasını belirleyen ana ölçü budur.</li>
<li><strong>Kızak dilinin boyu ve uç yuvarlaklığı:</strong> Dil kısa kalırsa çekmece raydan atlar, uzun kalırsa sonuna kadar kapanmaz.</li>
<li><strong>Durdurucunun kanca yüksekliği ve eğim açısı:</strong> Çekmecenin kendiliğinden çıkmadan durması, ama isteyerek çekildiğinde sökülebilmesi bu açıya bağlıdır.</li>
<li><strong>Makara dış çapı ve sırt profili:</strong> Düz sırt mı, ortadan oluklu mu — profil, makaranın kanal içinde hizada kalmasını sağlar.</li>
<li><strong>Makara pim deliği çapı ve göbek genişliği:</strong> Delik birkaç onda milimetre gevşerse makara yalpalar, sıkı olursa dönmez; bu ölçü hedeflenerek üretilir.</li>
<li><strong>Vida veya perçin deliği çapı ile delikler arası mesafe:</strong> Mevcut ray gövdesindeki deliklere birebir oturması için ölçülür, böylece paneli yeniden delmek gerekmez.</li>
<li><strong>Sağ-sol simetri:</strong> Aynı parçanın ayna kopyası istenebilir; çekmecenin iki yanı tek siparişte çıkar.</li>
<li><strong>Adet ve renk:</strong> Tek parça da üretilir, bir mutfağın tüm çekmeceleri için takım da. Farklı renk seçenekleri vardır; parça göz önünde olmadığı için genelde işlev önceliklidir.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme sınıfını gerektiğinden yukarı çekmeyiz; parçanın işi ne kadarını istiyorsa o kadarını öneririz. Az hareket gören, yalnızca konum tutan bir durdurucu ya da kılavuz için standart sınıf çoğu kez yeterlidir ve en ekonomik seçenektir. Ağır yüklü mutfak çekmeceleri, sürekli açılıp kapanan dolaplar ve tokluk isteyen kızak dilleri için PETG'ye çıkarız; darbede kırılmak yerine esner. Bulaşık makinesi yanı, fırın altı gibi ısınan ya da neme açık kabinlerde ASA tercih edilir. Günde onlarca kez dönen, yük altında sürtünen makaralarda ve ince kesitli dillerde karbon/cam elyaf takviyeli PA-CF veya PA-GF sınıfına geçeriz; aşınmaya ve şekil kaybına karşı en dirençli seçenek budur. Hangi sınıfın gerektiğine parçanın çalıştığı yeri sorarak birlikte karar veririz; çekmecenin ne taşıdığını ve nerede durduğunu bilmek doğru sınıfı seçmeye yeter.</p>
<h2>Dürüst sınır</h2>
<p>Üretebildiğimiz şey rayın plastik takımıdır: uç durdurucu, kızak dili, kılavuz burcu, makara ve makara yatağı, kopmuş tutucu dilleri. Rayın çelik gövdesi, bilyalı çelik kafesi ve metal yatakları ise bu sayfanın konusu dışındadır; onlar çekilmiş sac ve çelik işidir, o yükü plastiğe taşıtmayı önermeyiz. Yumuşak kapanma damperinin içindeki yağlı ünite de kapalı bir montaj kalemidir; orada yalnızca kırılan dış gövde ya da bağlantı ayağı konuşulabilir. Çok ağır yükü tek noktadan taşıyan metal bir askıyı plastikle değiştirmeyi de önermeyiz; yükün nereye bindiğini görmeden söz vermeyiz. Konu ray mekanizmasının dışına çıktığında bunu açıkça söyleriz: dolap gövdesi bağlantıları, ayak nişleri ya da banyo mekanizmaları bu sayfanın konusu değildir, onlar için ayrı sayfalarımız var.</p>
<h2>Sipariş</h2>
<p>Kırık parçanın fotoğrafını ve elinizdeki ölçüleri WhatsApp'tan +90 545 138 6526 numarasına iletin; numuneyi elden ya da gönderiyle bize ulaştırmanız da mümkündür. Ölçü doğrulandıktan sonra fiyat ve üretim süresi net olarak yazılır. Siteden kartla online ödeme yapabilirsiniz; ölçüye özel işler de kartla ödenir, ayrı bir süreç gerekmez. Tek bir durdurucu için de, bir mutfağın bütün çekmeceleri için de aynı yol geçerlidir; adet arttıkça parça maliyeti düşer.</p>
<p>Evdeki diğer kayar mekanizmalar için de aynı yolu izliyoruz: banyoda takılan kapak için <a href="/dus-kabini-banyo-plastik-parca-uretimi/">duş kabini makarası ve banyo plastikleri</a> sayfasına, ray dışındaki gövde bağlantıları ve dolap ayakları için <a href="/mobilya-plastik-baglanti-ayak-parca-uretimi/">mobilya bağlantı ve ayak parçası üretimi</a> sayfasına, ray sistemine bağlı olmayan serbest tekerlekler için <a href="/olcuye-ozel-tekerlek-makara-uretimi/">ölçüye özel tekerlek ve makara üretimi</a> sayfasına göz atabilirsiniz.</p>""")


def _plastik_stoper_durdurucu_yaptirma():
    return (u"""<h1>Aşınan stoperi birebir ölçüyle yenileyelim, çarpma bitsin</h1>
<p>Dolap kapağı her açılışta duvara vuruyorsa, makine tablası hareketin sonunda sert bir sesle duruyorsa ya da çekmece dayanacağı yeri bulamayıp sonuna kadar kaçıyorsa aranan eleman çoğu zaman iki santimlik bir durdurucudur. O küçük parça ufalandığında yedeği tek olarak bulunamaz; karşınıza mekanizmanın tamamını yenileme maliyeti çıkar. Avuç içi kadar bir eleman için taşıyıcı grubun, tablanın ya da kapı takımının tamamını sipariş etmek ve günlerce beklemek ekonomik bir karar değildir. Plastik stoper yaptırma bu maliyeti aradan çıkarır: elinizdeki kırık parçanın ölçüsünü alır, ölçüye özel stoperi tek adet üretir, grubun geri kalanına dokunmayız.</p>
<p>Hareket durdurucu yaptırma işi göründüğünden daha ölçü hassastır. Bir stoperin görevi milimetre cinsindendir: bir milimetre kısa olursa kapak yine temas eder, bir milimetre uzun olursa mekanizma tam oturmaz ve zorlar. Bu yüzden "yaklaşık aynısı" olan hazır bir parça çoğu zaman sorunu çözmez. Kapak stoperi üretimi, makine tablasının sonundaki durdurucu, çekmece grubunun sonunu belirleyen tampon ya da kolun açılma sınırını tutan takoz — hepsinde kritik olan sizin parçanızın gerçek ölçüsüdür.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Elinizde eski parçanın kırık bile olsa bir örneği varsa iş kolaydır. Parçayı bize ulaştırır ya da net fotoğrafını ve kumpas ölçülerini iletirsiniz; yüksekliği, çapı, delik aralığını ve oturduğu yuvayı ölçer, üretim öncesi teyit ederiz. Örnek parça tamamen kayıpsa yuvanın ölçüsü ve hareketin durması gereken mesafe yeterlidir: kalan boşluğu ölçer, gövde yüksekliğini ona göre belirleriz. Ölçü sizden, üretim bizden. Onay verdiğiniz ölçüyle üretim yapılır, tek adet de olsa iş görülür; kalıp ya da minimum adet şartı yoktur.</p>
<p>Ölçüyü doğrulamanın en pratik yolu, parçanın söküldüğü yerin fotoğrafını da göndermenizdir; durdurucunun neye çarptığını ve hareketin nereden geldiğini görmek yükseklik kararını netleştirir. Kritik bir kotada tereddüt kalırsa önce tek adet deneme parçası üretir, yerine takıp kontrol etmenizi isteriz; gerekirse ölçüyü bir kademe düzeltir, üretimi ona göre tamamlarız. Koşul açık: sapma bizim aldığımız ölçüden kaynaklanıyorsa düzeltmenin ücreti bizdedir; ölçüyü siz değiştirirseniz bu yeni bir iş olarak fiyatlandırılır. Bu yol, yanlış yükseklikte çoğaltılmış bir takım hazırlamaktan hem hızlı hem hesaplıdır.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Gövde yüksekliği:</strong> hareketin duracağı noktayı bu ölçü belirler; kapağın duvara ne kadar yaklaşacağı doğrudan buna bağlıdır.</li>
<li><strong>Dış çap ya da kesit ölçüsü:</strong> temas yüzeyi ne kadar genişse yük o kadar yayılır, iz bırakma ve ezilme azalır.</li>
<li><strong>Yuva çapı ve oturma payı:</strong> parça yuvasında oynamamalı, zorlanarak da girmemeli; payı sizin yuvanıza göre veririz.</li>
<li><strong>Vida deliği çapı:</strong> mevcut vidanızın ölçüsüne göre açılır, yeni delik açmanıza gerek kalmaz.</li>
<li><strong>Delik merkezleri arası mesafe:</strong> iki delikli tiplerde mevcut deliklerle birebir örtüşmesi gerekir, aksi halde parça eğik oturur.</li>
<li><strong>Havşa ya da düz delik tercihi:</strong> vida kafasının yüzeyden taşmaması gerekiyorsa havşa açarız.</li>
<li><strong>Taban plakası kalınlığı:</strong> yüzeye yaslanan tabanın kalınlığı hem yüksekliği hem de yükün dağılımını etkiler.</li>
<li><strong>Temas yüzeyi açısı:</strong> hareket eğik geliyorsa yüzeyi o açıya göre eğeriz, temas noktasal olmaz.</li>
<li><strong>Yumuşak temas kanalı:</strong> sese ve sarsıntıya duyarlı yerlerde fitil ya da yumuşak yastık oturacak kanal açılabilir.</li>
<li><strong>Yüzey dokusu ve farklı renk seçenekleri:</strong> görünen yerlerde mobilyanıza ya da makine gövdenize yakın renk seçilebilir.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalıştığı yere göre seçeriz, otomatik olarak en üst sınıfa itmeyiz. Ev içinde, kapalı ortamda, hafif temasla çalışan bir durdurucuda standart sınıf yeterlidir ve gereksiz maliyet çıkarmaz. Güneş gören, ısınan ya da nemli ortamda duran parçalarda PETG ve ASA sınıfına çıkarız; bu sınıf sıcaklık ve dış ortam etkisine standart malzemeden daha iyi dayanır. Temasın sürekli ve sert olduğu, günde yüzlerce kez yük alan makine noktalarında karbon ya da cam elyaf takviyeli PA-CF ve PA-GF sınıfını öneririz; bu sınıf hem daha rijittir hem de yüzey aşınmasına karşı daha dirençlidir. Hangi sınıfın işinizi göreceğinden emin değilseniz parçanın nerede çalıştığını anlatın, seçimi birlikte yapalım. <a href="/malzeme-rehberi/">Malzeme rehberi</a>, ortam koşullarına göre sınıfları karşılaştırır.</p>
<h2>Dürüst sınır</h2>
<p>Ne üretiriz: hareketin sınırını belirleyen kapak, çekmece, kol, tabla ve mekanizma durdurucuları; yuvaya oturan takozlar, vidalı durdurucu plakaları, tampon gövdeleri. Ne üretmeyiz: insan güvenliğinin tek dayanağı olan emniyet durdurucuları, ağır yükün düşmesini engelleyen son emniyet elemanları, yangın ve tahliye ekipmanına ait parçalar. Bunlar sertifikalı metal elemanların işidir.</p>
<p>Açıkça söyleyelim: sert darbenin sürekli tekrarlandığı bir noktada malzeme sınıfını yukarı çekeriz, ama stoper doğası gereği sarf parçadır — yükü o karşılar ki arkasındaki pahalı grup karşılamasın. Zamanla yüzeyi ezilir ve yenilenmesi gerekir. Bunu peşinen bilmeniz, sonradan hayal kırıklığı yaşamanızdan iyidir. Tutma ve sabitleme görevi üstlenen parçalar ise bu sayfanın konusu dışındadır; stoper yalnız hareketi sınırlar.</p>
<h2>Sipariş</h2>
<p>Ölçünüzü ve parçanın çalıştığı yeri iletin, uygun malzeme sınıfını ve fiyatı netleştirelim. Sitemizden kartla online ödeme yapabilirsiniz; ölçüye özel üretim de dahil olmak üzere sipariş kartla tamamlanır. Ölçü konusunda tereddüdünüz varsa ya da parçanın fotoğrafını göndermek istiyorsanız WhatsApp hattımız açık: +90 545 138 6526.</p>
<p>Aynı mantık çevresindeki parçalar için de geçerli: perdesi düzgün toplanmayan bir sistemde çoğu zaman sorun mekanizmanın sınırındaki küçük parçadır ve <a href="/stor-jaluzi-perde-mekanizma-parcasi-uretimi/">stor ve jaluzi mekanizma parçası üretimi</a> bunu tek tek çözer. Kapağın duruşu hem durdurucuya hem de bağlantıya bağlıysa <a href="/olcuye-ozel-mentese-uretimi/">ölçüye özel menteşe üretimi</a> sayfasına, tezgâh ve tabla üstündeki tekrarlı hareketler söz konusuysa <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfasına göz atın.</p>""")


def _konveyor_bant_plastik_parca_yaptirma():
    return (u"""<h1>Hat durmasın: kılavuz çıta, kızak ve makarayı ölçüsüne göre veriyoruz</h1>
<p>Bir taşıma hattında kılavuz çıta sürekli iş görür. Dakikada otuz kutu geçen orta hızlı bir bantta sekiz saatlik vardiyanın sonunda o çıtanın aynı iki santimlik şeridine on dört binden fazla temas olur. Üç vardiyalı bir tesiste bu rakam günde kırk bini, ayda bir milyonu geçer. Bu kadar tekrarlı temas parçada iz bırakır: kanalın ağzı yavaş yavaş açılır, kızak yüzeyi parlar ve incelir, makara gövdesinin göbek deliği ovalleşir.</p>
<p>Sonucu üretim müdürü de bakımcı da aynı sırayla görür: önce ürün kanalın içinde yalpalar, sonra fotosel yanlış sayar, en sonunda kutular hattın kenarında sıkışır ve hat durur. Onarım için sökülen parça çoğu zaman avuç içi kadar bir plastik çıtadır. Konveyör kılavuz parçası, bant hattı kızak parçası ve makara gövdesi için bize gelen taleplerin neredeyse tamamı bu tabloyla gelir; motoru, redüktörü, şasisi yerli yerinde duran koca bir hat, sürtünen tek bileşen yüzünden bekler. Aynı taşıma akışı paketleme makinesinin kılavuz, kapak, burç veya kayış çevresi parçasında duruyorsa <a href="/paketleme-makinesi-plastik-yedek-parca-yaptirma/">paketleme makinesi plastik yedek parçası</a> sayfası daha doğrudan yol gösterir.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Elinizdeki yenmiş parçayı, kırık yarısını ya da hattan sökülmüş numuneyi bize ulaştırırsınız. Parça iki yarıya ayrılmışsa da olur; ölçüyü ikisinin üzerinden çıkarırız. Numune gönderemeyecek durumdaysanız kanal genişliği, çıta kesiti, montaj delik aralığı ve toplam uzunluk için kumpas ölçüsü ve düz zemin üzerinde çekilmiş net fotoğraf yeterlidir.</p>
<p>Ölçüleri çıkarıp size ayarları teyit ettiririz: kaç milimetre kanal, kaç milimetre dönüş yarıçapı, hangi delik aralığı. Bu adım önemlidir, çünkü yenmiş numunenin ölçüsü zaten aşınmış ölçüdür; biz aşınma payını geri ekleyerek ilk günkü kotu hedefleriz. Onaydan sonra parça özel olarak üretilir ve tek adet de olsa aynı özenle hazırlanır. Aynı hatta ileride yine gerekirse ölçü kaydınızı talebiniz üzerine saklarız; ikinci siparişte ölçü adımı çoğu zaman kısalır.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Kanal genişliği ve derinliği</strong> — taşınan kutu, kasa ya da şişe kalınlığına göre; birkaç onda milimetrelik boşluk farkı ürünün akıcı gitmesiyle sıkışması arasındaki farktır.</li>
<li><strong>Çıta kesiti (en × kalınlık) ve tek parça uzunluğu</strong> — mevcut ray yuvasına oynamadan oturması, ek yerlerinin tümsek yapmaması için.</li>
<li><strong>Dönüş yarıçapı</strong> — kavisli bölümde ürünün kenara yüklenmeden dönebilmesi kavis ölçüsünün doğruluğuna bağlıdır.</li>
<li><strong>Montaj delik aralığı ve delik çapı</strong> — hattaki mevcut vida düzenini değiştirmeden takabilmeniz için delik-delik mesafesini birebir tutarız.</li>
<li><strong>Delik tipi: düz ya da oval kayar delik</strong> — hat gerilip gevşedikçe parçanın milimetrik kaçış payına ihtiyacı olur; oval delik bu payı verir.</li>
<li><strong>Havşa/gömme derinliği</strong> — vida kafası yüzeyden taşarsa taşınan ürünü çizer; kafayı yüzeyin altına indiririz.</li>
<li><strong>Giriş pahı ve yüzey kavisi</strong> — ürünün kanala takılmadan girmesini sağlayan, numunede çoğu zaman gözden kaçan ayrıntıdır.</li>
<li><strong>Yan tutucu yüksekliği ve açısı</strong> — yüksek ve dar ürünlerde devrilme riskine göre yükseklik artar.</li>
<li><strong>Makara gövde dış çapı ve genişliği</strong> — bandın gövde üzerinde ortalanması için genişliği bant enine göre veririz.</li>
<li><strong>Göbek/mil deliği çapı ve yatak yuvası ölçüsü</strong> — hazır rulman ya da mil bu yuvaya oturacağından tolerans burada belirleyicidir. Metal elemanı çevreleyen ayrı bir gövde veya mesnet gerekiyorsa <a href="/mil-rulman-icin-olcuye-ozel-plastik-yuva/">mil ve rulman için ölçüye özel plastik yuva</a> sayfasındaki ölçü listesine geçin.</li>
<li><strong>Flanş yüksekliği</strong> — bandın makaradan yana kaçmasını engelleyen bileziğin ölçüsü.</li>
<li><strong>Farklı renk seçenekleri</strong> — vardiya içinde bakımcının parçayı uzaktan ayırt etmesi işe yarar.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi parçanın çalıştığı yere göre seçeriz, listenin en üstünü satmaya çalışmayız. Kuru ortamda, düşük hızda ve hafif ürün taşıyan bir kılavuzda standart sınıf çoğu zaman yeterlidir; gereksiz üst sınıfa itmek maliyeti şişirir, hattı daha iyi çalıştırmaz. Kılavuz ve kızak parçaları sürtünme parçalarıdır; <a href="/asinmaya-dayanikli-surtunme-parcasi-uretimi/">aşınmaya dayanıklı sürtünme parçası üretimi</a> sayfası bu aşınma nedenlerini ayrıntılı anlatır.</p>
<p>Yıkama yapılan gıda hattı, nemli ortam ya da açık alandaki bir taşıma düzeni söz konusuysa ısıya, neme ve güneşe dayanıklı sınıfa (PETG ve ASA) çıkarız. Sürekli temas eden, gün boyu yük altında sürtünen kızak ve makara gövdelerinde ise karbon veya cam elyaf takviyeli yüksek mukavemet sınıfını (PA-CF, PA-GF) öneririz; bu sınıfın boyutsal kararlılığı ve yüzey direnci belirgin biçimde daha yüksektir. Hangi sınıfın uygun olduğunu, hattın hızını ve taşınan ürünün ağırlığını sorarak birlikte belirleriz.</p>
<h2>Dürüst sınır</h2>
<p>Açık konuşalım: neyi üretebileceğimizi olduğu kadar neyi üretemeyeceğimizi de söyleriz. Kılavuz çıtayı, yan tutucuyu, kızak profilini, zincir kılavuzunu, makara gövdesini, gergi ve ayar aparatlarını ölçüsüne göre üretiriz. Taşıyıcı bandın veya zincirin kendisini, çelik mili, aksı ve rulmanın metal iç yapısını üretmeyiz — hazır rulmanın oturacağı yuvayı ise ölçüsüne göre veririz. Yıkama yapılan gıda hatlarında yalnızca ürüne temas etmeyen kılavuz, kızak ve makara gövdesi işlerini alırız; ürünle doğrudan temas eden yüzeyler ve gıda teması sertifikası gerektiren parçalar kapsamımız dışındadır, böyle bir belge vermeyiz.</p>
<p>Hattın ana tahrik yükünü tek bir plastik parçanın taşıdığı görevlerde ve sürekli yüksek sıcaklıkta çalışan fırın hatlarında önce bizi arayın; parçayı görmeden ve yükü öğrenmeden "olur" demeyiz, uygun değilse bunu açıkça söyleriz. Dişli, kasnak, burç ve braket gibi bileşenleri de üretiyoruz; onlar bu sayfanın konusu dışında kalıyor, ayrı sayfalarda anlatılıyor. Tahrik motorunu redüktöre bağlayan esnek kavramanın göbeği dağıldıysa doğru adres <a href="/plastik-kaplin-gobegi-esnek-kavrama-uretimi/">kaplin göbeği ölçüye özel plastik üretim</a> sayfasıdır.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden. Numuneyi ya da ölçü fotoğrafını gönderin, ayarları teyit edelim; siteden kartla online ödeme yapabilirsiniz, ölçüye özel işler de buna dahildir. Ölçüyü konuşmak, hangi malzeme sınıfının işinizi göreceğini sormak ya da adet üzerinden fiyat almak için WhatsApp: +90 545 138 6526.</p>
<p>Hattaki aksaklık taşıma bileşeninde değil de gövdedeki herhangi bir aparattaysa <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfasına, dönen gövdenin kendisi konuşuluyorsa <a href="/olcuye-ozel-tekerlek-makara-uretimi/">ölçüye özel tekerlek ve makara üretimi</a> sayfasına göz atın. Kumpas ile ölçü almayı ve numuneyi bize ulaştırmayı daha önce yapmadıysanız <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır ve gönderilir</a> adım adım yol gösteriyor.</p>""")


def _havuz_ekipmani_plastik_parca_yaptirma():
    return (u"""<h1>Klorlu su ve güneşte kırılan havuz plastiklerini yeniliyoruz</h1>
<p>Havuz sezonu açılırken çıkan arıza listesi genelde küçük plastiklerden oluşur: süpürgenin tekerleği kırılmıştır, skimmer kapağının mandalı kopmuştur, merdivenin duvara tutunan plastiği çatlamıştır. Bu parçalar çoğu zaman ayrı yedek olarak satılmaz; satış noktası ya gövdenin tamamını ya da yeni bir ekipmanı önerir. Beş gramlık bir plastik yüzünden çalışır haldeki takımı değiştirmek istemeyenler bize ulaşıyor. Havuz plastik parça yaptırma işi bizim için tek cümleyle özetlenir: kırık parçayı ölçer, aynı işi görecek yenisini üretiriz.</p>
<p>Havuz çevresindeki plastiklerin ortak kaderi de bellidir. Klorlu su, dengeleyici kimyasallar ve sezon boyu süren güneş, yıllar içinde malzemeyi sertleştirir; kırılma çoğunlukla darbeden değil, malzemenin yorulmasından gelir. Bu yüzden aynı parça genelde aynı noktadan tekrar çatlar. Elinizde kırık numune varsa iş kolaydır — ölçü doğrudan o parçadan alınır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Kırık parçayı bize elden ulaştırırsınız ya da gönderirsiniz. Parça ikiye üçe ayrılmışsa sorun değil; kırıkları yan yana getirip ölçüyü tamamlarız. Aşınmış bir parçada ise özgün ölçüyü, parçanın aşınmamış bölgelerinden ve oturduğu yuvadan geri kurarız. Numune hiç yoksa parçanın oturduğu yuvadan, aks çapından ve vida aralığından ölçü çıkarırız; bu durumda birkaç kumpas ölçüsünü ve iki üç net fotoğrafı sizden isteriz.</p>
<p>Ölçüler netleştikten sonra parçanın çalıştığı yeri konuşuruz: su altında mı kalıyor, gün boyu güneş görüyor mu, üzerine yük biniyor mu, sürtünerek mi çalışıyor. Cevaplara göre malzeme sınıfı ve et kalınlığı belirlenir. Tek adet de üretiriz, aynı ekipmandan birkaç takım da.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Tekerlek ve makara dış çapı ile genişliği</strong> — havuz süpürgesi tekerleği yaptırma işlerinde çap birkaç milimetre şaşarsa gövde tabana oturmaz, süpürge zeminde tutuklaşır.</li>
<li><strong>Aks deliği çapı ve pim yuvası</strong> — tekerleğin şaft üzerinde boşluk yapmadan dönmesi bu ölçüye bağlıdır; sıkı geçme mi, serbest dönme mi istediğinizi önceden konuşuruz.</li>
<li><strong>Fırça tutucu delik aralığı ve vida çapı</strong> — mevcut gövdeyi delmeden takılabilmesi için delik merkezleri arası mesafe birebir korunur.</li>
<li><strong>Hortum bağlantı bileziğinin iç çapı, et kalınlığı ve kanal derinliği</strong> — kanal derinliği hortumun kaçmadan tutunmasını, et kalınlığı ise bileziğin sıkarken çatlamamasını belirler.</li>
<li><strong>Skimmer kapak mandalı dilinin uzunluğu, kalınlığı ve kavrama açısı</strong> — skimmer kapak mandalı yaptırma taleplerinde en kritik ölçü açıdır; birkaç derecelik fark kapağın ya hiç kilitlenmemesine ya da zor açılmasına yol açar.</li>
<li><strong>Izgara ve kapak klipsinin tırnak yüksekliği ile esneme payı</strong> — tırnak fazla yüksekse klips takarken kırılır, alçaksa yerinde durmaz.</li>
<li><strong>Merdiven tutucusunun boru dış çapı, kavrama genişliği ve ayak delik mesafesi</strong> — havuz merdiveni tutucu üretimi işlerinde boru çapı ile duvar delik aralığı birlikte tutmalıdır, aksi halde tutucu boruyu zorlar.</li>
<li><strong>Yüzey ve kenar işlemi</strong> — el değen tutamak ve kulplarda kenarlar yumuşatılır, su içinde kalan parçalarda yüzey düz tutulur.</li>
<li><strong>Farklı renk seçenekleri</strong> — beyaz, gri, lacivert gibi mevcut ekipmana yakın tonlarla çalışırız.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Havuz çevresi bizim için üç kademeli bir seçim demek. Standart sınıf, yalnızca gölgede duran, su ile sürekli teması olmayan ve yük almayan yardımcı parçalar için yeterlidir; buraya kimseyi zorla üst sınıfa itmeyiz, çünkü fiyatı büyütmenin anlamı yoktur. Havuz suyunun klor ve kimyasal dozajı parçayı zamanla kırılganlaştırdığı için, malzeme seçimini <a href="/yaga-ve-kimyasala-dayanikli-plastik-parca-uretimi/">kimyasala dayanıklı parça üretimi</a> ölçütlerine göre yaparız; gün boyu güneş alan kapak ve tutucular içinse <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekân parçaları</a> sayfasındaki sınıf karşılaştırması yol gösterir.</p>
<p>Güneş gören ve sürekli ıslanan parçalarda ise ısıya ve dış hava koşuluna dayanıklı sınıflara geçeriz: PETG ve ASA. ASA özellikle gün boyu güneş altında kalan kapak, klips ve tutucularda tercih ettiğimiz sınıftır; renk ve yüzey kararlılığı standart sınıfa göre belirgin şekilde iyidir. Klorlu ve kimyasal dozajlı suyla teması yoğun olan parçalarda malzeme seçimini bu koşula göre daraltırız.</p>
<p>Üzerine yük binen, sürtünen ya da vida dişi taşıyan parçalarda karbon veya cam elyaf takviyeli sınıflara çıkarız (PA-CF / PA-GF); ancak bu kademeyi yalnızca suyun dışında kalan, yük alan noktalar için öneririz. Merdiven tutucusu, havuz kenarındaki bağlantı ve tutamak grupları bu kademenin tipik örnekleridir. Sürekli su altında ya da ıslak kalan bileşenlerde — süpürge tekerleği ve makarası, skimmer içindeki parçalar — takviyeli sınıfa çıkmayız; bu sınıf nem aldıkça boyutsal kararlılığını kaybettiği için o noktaları PETG ve ASA tarafında bırakırız.</p>
<h2>Dürüst sınır</h2>
<p>Ne üretiriz: süpürge tekerleği ve makarası, fırça ve süpürge tutucusu, hortum bağlantı bileziği, ızgara ve kapak klipsi, skimmer kapak mandalı, merdiven tutucusu, tutamak, kulp, tapa ve muhafaza türü çevre parçaları.</p>
<p>Ne üretmeyiz: pompanın su itişini üstlenen çarkı bu yöntemle önermiyoruz — ürettiğimiz çarklar hafif fan ve hafif çark sınıfındadır. Sızdırmazlık parçalarını düşük–orta yük aralığında değerlendiririz, tesisatın yüksek yük alan hatlarını kapsam dışı tutarız. Taşıyıcı profil ve beam işlerinde de hafif, yük taşımayan uygulamalarda kalırız. Havuz suyunun kimyasal dengesini etkileyebilecek gıda ya da içme suyu temas sertifikası vermiyoruz; bunu önceden söylemek işin doğrusu. Ölçü sizden, üretim bizden — ama parçanın nerede duracağını birlikte karara bağlarız.</p>
<h2>Sipariş</h2>
<p>Ölçüsü netleşen parçaları siteden kartla online ödeyerek sipariş edebilirsiniz; ölçüye özel işler de bu akışa dahildir. Numunenizden emin değilseniz, kırık parçanın fotoğrafını ve elinizdeki ölçüleri WhatsApp'tan +90 545 138 6526 numarasına gönderin, uygun sınıfı ve süreyi birlikte belirleyelim.</p>
<p>Tırnaklı bağlantılar ve kelepçe tipi tutuculara ayrı ayrı bakmak isterseniz <a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe üretimi</a> sayfasına, elinizdeki kırık örnekten nasıl ölçü çıkardığımızı görmek isterseniz <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre parça üretimi</a> sayfasına göz atabilirsiniz.</p>""")


def _cam_krikosu_plastik_parcasi_yaptirma():
    return (u"""<h1>Cam inip kalkmıyorsa tüm krikoyu değil, kırılan plastiği yenileyin</h1>
<p>Kapı düğmesine dokunduğunuzda motorun sesini duyuyor ama camın kımıldamadığını görüyorsanız, arıza çoğu zaman sandığınız yerde değildir. Mekanizma dönmeye devam eder, halat sarılır, ancak camı taşıyan plastik kızak ya da tutucu çatladığı için hareket cama aktarılmaz. Cam bir tarafından yukarı gelip diğer tarafından geride kalıyorsa, kapı içinde takırtı duyuluyorsa ya da cam kendi ağırlığıyla aşağı kayıyorsa tablo aynıdır: metal aksam sağlam, kırılan tek şey camı kavrayan plastik parçadır. Bu sayfa tam olarak o parçanın numuneden birebir yenilenmesini anlatıyor — cam krikosu plastik parçası yaptırma, cam kaldırma kızağı yaptırma ve cam krikosu tutucusu üretimi hep aynı işin adlarıdır.</p>
<p>Servis genellikle komple mekanizma değişimi önerir; çünkü o küçük plastik ayrı satılmaz. Oysa değişen şey aslında bir avuç plastiktir. Elinizdeki kırık parçayı bize ulaştırdığınızda, o parçayı ölçüp aynı geometride yenisini üretiriz. Araç cam mekanizması plastiği için kalıp yaptırmak gerekmez, tek adet üretim de yaparız.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>İlk adım parçayı elimize almaktır. Kırık parçanın tüm kırıkları elinizde olmasa bile sorun değil; kalan gövde, karşı taraftaki sağlam eşi ya da parçanın oturduğu ray bize referans verir. İkinci aşamada parçayı kumpas ile ölçeriz: cam kanalının genişliği ve derinliği, halatın oturduğu yuvanın çapı, kızağın ray içindeki kayma yüzeyi, delik eksenleri arasındaki mesafe tek tek çıkarılır. Üçüncü aşamada bu ölçülerle yeni parça üretilir ve size ulaşır. Numuneden ilerleyen genel akışı <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> sayfasında da bulabilirsiniz.</p>
<p>Numune gönderemiyorsanız kırık parçanın birkaç net fotoğrafı, yanına konmuş bir cetvel ve birkaç kritik ölçü de işi yürütmeye yeter. Araç marka-model bilgisi yardımcı olur ama tek dayanağımız değildir; ölçü sizden gelir, üretim bizden.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Cam kanalı genişliği</strong> — camın oturduğu yarığın milimetrik açıklığı. Dar olursa cam yerine girmez, geniş olursa camla parça arasında oynama olur ve takırtı geri gelir.</li>
<li><strong>Cam kanalı derinliği ve dip radüsü</strong> — camın kavranma yüzeyini belirler. Yetersiz derinlik, camın kaldırma kuvvetini dar bir alandan almasına ve kenardan zorlanmaya yol açar.</li>
<li><strong>Halat / makara yuvası çapı ve genişliği</strong> — mekanizmanın çeliğinin oturduğu yuva. Buradaki yarım milimetre, halatın yuvadan çıkması ile düzgün sarılması arasındaki farktır.</li>
<li><strong>Kızak uzunluğu ve ray kesiti</strong> — parçanın ray içinde kaç milimetre boyunca temas ettiği ve kesitin profili. Kısa temas, kızağın yana yatmasına ve camın eğik gitmesine sebep olur.</li>
<li><strong>Kayma yüzeyi toleransı</strong> — ray ile kızak arasındaki boşluk. Sıkı ayar motoru zorlar, gevşek ayar oynama yaratır; numuneye göre araya makul bir pay koyarız.</li>
<li><strong>Vida/pim delik çapı ve delikler arası mesafe</strong> — parça yerine oturmuyorsa çoğu zaman sebep bu iki ölçüdür. Delik eksenlerini numuneden aynen taşırız.</li>
<li><strong>Kelepçe iç açıklığı ve kapanma kuvveti</strong> — camı ya da çubuğu saran kelepçenin ne kadar kavradığı. Açıklık numuneden alınır, gerekiyorsa bir kademe sıkı üretilir.</li>
<li><strong>Cam eğim açısı</strong> — kapı camları düz değildir; parçanın cama oturduğu açı yanlışsa cam kanalda zorlanır. Numunedeki açıyı ölçer, aynen uygularız.</li>
<li><strong>Renk</strong> — görünmeyen bir parça olduğu için genelde önemsizdir, yine de farklı renk seçenekleri sunabiliriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Kapı içi, aracın en zorlu bölgelerinden biridir: yazın sıcak, kışın soğuk, sürekli nem ve titreşim vardır. Bu yüzden standart sınıf malzemeyi bu parçada tek seçenek olarak sunmayız; onu daha çok ölçü doğrulama numunesi için kullanırız.</p>
<p>Camı taşımayan, yalnızca konumlandıran tutucu ve kapak parçalarında ısı ve neme dayanıklı sınıf (PETG ve ASA) çoğu durumda yeterlidir. Camın ağırlığını taşıyan kızak, halat yuvası ve kelepçe gibi yük altındaki parçalarda ise karbon ya da cam elyaf takviyeli sınıfa (PA-CF / PA-GF) çıkarız; bu sınıf hem daha rijittir hem de sürtünen yüzeyde aşınmaya karşı daha iyi durur.</p>
<p>Her parçayı en üst sınıfa itmeyiz. Yalnızca konum tutan bir plastiği takviyeli malzemeden üretmek maliyeti gereksiz yükseltir. Parçanın hangi kuvveti taşıdığını numuneye ve kırılma biçimine göre değerlendirir, uygun kademeyi öneririz. Malzeme sınıflarının farklarını ayrıntılı görmek isterseniz <a href="/malzeme-rehberi/">malzeme sınıflarını karşılaştıran rehberimize</a> göz atabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Üretiriz: cam kaldırma kızağı, cam tutucu/taşıyıcı gövdesi, kelepçe, halat kılavuzu, makara gövdesi, kapı içi konumlandırma parçaları ve bunların numuneden çıkarılan tüm ölçüleri.</p>
<p>Üretmeyiz: mekanizmanın metal aksamı, çelik halat, motor ve redüktör grubu, dişli kutusunun metal gövdesi. Cam fitili gibi esnek elastomer profiller sert plastik işi değildir, bu sayfanın konusu dışındadır. Motor dönmüyorsa ya da halat kopmuşsa çözüm bu sayfada değildir; o durumda mekanizmanın kendisi yenilenmelidir.</p>
<p>Ayrıca kapı iç panelindeki dekoratif kaplama ve döşeme parçaları bu sayfanın konusu dışındadır — o iş ayrı bir sayfada ele alınır. Plastik parçanın da bir sınırı vardır: sürekli darbe alan, aşırı ısınan ya da doğrudan çelik yerine geçmesi beklenen bir eleman yerine plastik önermeyiz. Parçanın çalıştığı yeri konuşur, uygun değilse açıkça söyleriz.</p>
<h2>Sipariş</h2>
<p>Kırık parçayı ya da net ölçülü fotoğraflarını bize iletin; uygunluk ve ölçü teyidini birlikte yapalım. Ölçüye özel işler dahil olmak üzere sitemizden kartla online ödeme yapabilirsiniz. Soru sormak, ölçü paylaşmak ya da parçanın fotoğrafını göndermek için WhatsApp hattımız açık: +90 545 138 6526.</p>
<p>Aynı arıza kamyon ve ticari araçlarda daha sık görülür ve yedeği çok daha zor bulunur; filo aracınız varsa <a href="/ticari-arac-kamyon-plastik-parca-ozel-uretim/">kamyon ve ticari araç kabin plastikleri sayfamıza</a> bakmanızı öneririz. Kapı panelindeki kaplama ve tespit elemanları için <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim ve klips üretimi sayfamız</a>. Aracınız üretimden kalkmış eski bir modelse kriko plastiğiyle birlikte başka kalemler de bulunamaz hale gelir; <a href="/klasik-arac-eski-model-oto-plastik-parca-uretimi/">eski model araç plastik parçası özel üretim</a> sayfası o kalemleri topluca anlatıyor.</p>""")


def _darbeye_dayanikli_plastik_parca_yaptirma():
    return (u"""<h1>Aynı parça tekrar tekrar kırılıyorsa malzemeyi yukarı çekelim</h1>
<p>Ani yük, düşme ya da çarpma alan bir parçada kırılma çoğu zaman darbenin tek noktada toplandığını gösterir. Kırık yüzey cam gibi düzse, parça gelen enerjiyi esneyerek dağıtmak yerine aniden iletmiş olabilir; aynı yerden ikinci, üçüncü kez kopuyorsa malzeme sınıfı ve kesit birlikte ele alınmalıdır.</p>
<p>Darbeye dayanıklı plastik parça yaptırma talebiyle bize gelen işlerin büyük kısmında hedef, gelen enerjiyi kopma yerine hafif esneme ve şekil değiştirme ile karşılayabilen daha tok bir sınıf ve doğru kesittir. Isı, güneş/UV ve yağ ya da kimyasal teması ise ayrı çalışma koşullarıdır: <a href="/isiya-dayanikli-plastik-parca-uretimi/">ısıya dayanıklı parça üretimi</a>, <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekân parçası seçenekleri</a> ve <a href="/yaga-ve-kimyasala-dayanikli-plastik-parca-uretimi/">yağa ve kimyasala dayanıklı parça üretimi</a> bu koşulları ayrı ayrı anlatır. Bu işi soran çoğu kişi "kırılmaya dayanıklı plastik parça yaptırma" diyor; kastedilen sınırsız bir dayanım vaadi değil, aynı darbede daha iyi davranan tok bir malzeme ve doğru kesittir.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Elinizdeki kırık parçayı, parçaların tamamını ya da net fotoğraflarını bize ulaştırırsınız. Kırık yüzeye biz de bakarız: kopma tek noktadan mı, tarama şeklinde mi, delik kenarından mı gelişmiş? Bu bakış, hangi ölçünün büyütülmesi ve hangi malzeme sınıfının seçilmesi gerektiğini gösterir. Ardından parçayı ölçeriz; kalınlık, delik merkezleri ve oturma yüzeyleri milimetrik çıkarılır. Onaydan sonra üretilir ve size gönderilir. Tek adet de yapılır, yedeğiyle beraber ikili de.</p>
<p>Takviyeli plastik parça üretiminde en sık yaptığımız düzeltme, kırılan bölgenin geometrisini olduğu gibi kopyalamak yerine iyileştirmektir: köşedeki keskin geçişe yarıçap vermek, delik etrafındaki dar bileziği kalınlaştırmak, ince kanadın dibine ölçülü bir dolgu eklemek. Aynı malzemede bile bu üç dokunuş, kopma eğilimini azaltmaya yardım eder.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Et kalınlığı:</strong> Darbede en çok işi kalınlık yapar; kırılan bölgeyi gerektiği kadar kalınlaştırır, montaja giren yüzeyleri olduğu gibi koruruz.</li>
<li><strong>Köşe yarıçapı (radüs):</strong> Keskin iç köşe çatlağın çıkış noktasıdır, oraya yarıçap vermek enerjiyi geniş alana yayar.</li>
<li><strong>Delik çapı ve delik–kenar mesafesi:</strong> Kenara çok yakın açılmış bir delik ilk sert darbede yırtılır, bu mesafeyi güvenli değere çekeriz.</li>
<li><strong>Kesit yüksekliği ve genişliği:</strong> Kola, ayağa veya bağlantı kulağına gelen eğilme yönüne göre kesiti o yönde büyütür, gereksiz yerde hacim şişirmeyiz.</li>
<li><strong>Oturma yüzeyi alanı:</strong> Parça darbeyi tek noktadan değil geniş bir yüzeyden gövdeye aktarmalı; temas alanını artırmak çoğu kez malzeme değiştirmekten daha etkilidir.</li>
<li><strong>Kaburga (destek) düzeni:</strong> İnce bir yüzeyi kalınlaştırmadan güçlendirmenin yolu, arkasına ölçülü destek kaburgaları koymaktır.</li>
<li><strong>Kanal derinliği, geçiş açısı ve diş ölçüsü:</strong> Karşı parçayla eşleşmesi gereken tüm ölçüler numuneden birebir alınır, aksi halde sağlam parça bile yerine oturmaz.</li>
<li><strong>Renk:</strong> Farklı renk seçenekleri sunarız; seçim montajdaki görünüme göre yapılır.</li>
</ul>
<p>Bu maddeleri tek tek konuşuruz, çünkü bir ölçüyü büyütmek çoğu zaman komşu ölçüyü de değiştirmeyi gerektirir.</p>
<h2>Doğru malzeme</h2>
<p>Merdiveni aşağıdan yukarı çıkarız. Kapalı ortamda, ılıman koşulda, ara sıra hafif temas gören bir parça için standart sınıf yeterlidir; buna gereksiz maliyet bindirmeyiz. Titreşimin sürekli olduğu, parçanın esneyip toparlanması gereken, düşme ve çarpmanın rutin sayıldığı yerlerde bir üst sınıfa — PETG ya da ASA tarafına — geçeriz; bu sınıflar ani yüklemede kopmak yerine bir miktar şekil değiştirir. Yük taşıyan kollarda, bağlantı kulaklarında, ağır ekipmanın altına giren ayaklarda ise karbon ya da cam elyaf takviyeli sınıfa (PA-CF / PA-GF) çıkarız; burada rijitlik ve yorulma direnci birlikte yükselir.</p>
<p>Şunu açıkça söyleyelim: en üst sınıf her zaman en doğru cevap değildir. Takviyeli malzemeler daha rijittir, yani daha az esner. Esnemenin darbeyi yuttuğu bir klipste, kilit dilinde ya da ince bir tırnak bölgesinde daha tok ama daha esnek bir sınıf çoğu kez daha iyi sonuç verir. Parçanın nerede ve nasıl zorlandığını anlatın, sınıfı birlikte seçelim; kararı önceden daraltmak isterseniz <a href="/karbon-fiber-takviyeli-naylon-parca-ne-zaman-gerekir/">karbon fiber takviyeli naylon parça ne zaman gerekir</a> sayfası takviyeli sınıfın gerçekten gerektiği durumları sıralıyor.</p>
<h2>Dürüst sınır</h2>
<p>Yaptığımız iş: tekrarlayan çarpma ve düşme koşulunda çalışan gövde parçaları, kulaklar, kollar, ayaklar, koruma elemanları, kapak ve muhafazalar; kırık numuneden ölçüye özel yenisi.</p>
<p>Söylemediğimiz şey: her darbenin sönümleneceği. Ani darbeden farklı olarak tekrarlı titreşimi azaltan esnek ayak, tampon ve ara parçalar için <a href="/titresim-sonumleyici-esnek-plastik-parca-yaptirma/">titreşim sönümleyici esnek parça</a> sayfasına bakabilirsiniz. Malzeme sınıfı denklemin yalnız bir parçasıdır. Oturma yüzeyi dar bir parça, en iyi malzemeyle bile aynı noktadan yorulur; kesiti yetersiz bir kol yine eğilir; metalin taşıdığı ağır yükü plastik sınıfına devretmek doğru bir karar değildir. Çarpışma emniyeti, can güvenliği ve sertifika gerektiren elemanlar kapsamımız dışındadır. Parçanızın çalıştığı yeri gördüğümüzde iyileşmenin sınırlı kalacağını düşünüyorsak, bunu üretimden önce söyleriz.</p>
<h2>Sipariş</h2>
<p>Ölçü sizden, üretim bizden: kırık parçanızın fotoğrafını ve ölçülerini gönderin, malzeme sınıfını ve ölçü düzeltmelerini birlikte netleştirelim. Siteden kartla online ödeme yapabilir, ölçüye özel işleri de aynı yoldan sipariş verebilirsiniz. Kaç adet istediğinizi ve parçanın nerede, hangi yükün altında çalıştığını yazmanız süreci kısaltır. Karar vermeden önce konuşmak isterseniz WhatsApp hattımız açık: +90 545 138 6526.</p>
<p>Darbe sorununun en görünür olduğu alanlardan biri kondisyon aletleridir; düşen ağırlığın ve sürekli yüklenen kolun altında çalışan parçalar için <a href="/spor-salonu-fitness-ekipmani-plastik-parca-uretimi/">fitness ekipmanı plastik parça üretimi</a> sayfamıza da göz atın.</p>""")


def _cim_bicme_bahce_makinesi_plastik_parca_yaptirma():
    return (u"""<h1>Servis komple grup satıyorsa kırılan tek parçayı üretelim</h1>
<p>"Uyar" denilerek satılan muadil parçayı makineye götürdüğünüzde iş genellikle birkaç milimetrede tıkanır. Çim biçme makinesi tekerlek göbeği yaptırma araştıran kullanıcıların büyük kısmı bunu zaten yaşamıştır: raftaki göbeğin mil çapı 12 mm, sizin aksınız 12,7 mm; ya da çap tutar ama kama kanalı açılmamıştır, tekerlek dönerken aksın üstünde boşa savrulur. Flanş delikleri de sık sık yarım santim kayıktır; vidayı zorlayarak tutturursanız gövde çatlar, ilk çim yığınında yine aynı yere gelirsiniz.</p>
<p>Yükseklik ayar kolunda tablo benzerdir. Kolun boyu ve pim çapı denk gelse bile kademe dişlerinin adım açısı farklıdır; kol takılır, ancak makine üç kademe yerine iki kademede kilitlenir ve orta konumda kendiliğinden düşer. Kapak mandalında sorun daha ince: tırnak yüksekliği bir milimetre kısa olduğu için kapak kapanır gibi yapar, çalışma titreşiminde açılır. Tırpan misina kafası tutucusunda ise iç vida ölçüsü ve dönüş yönü tutmadığında parça yuvasına oturmaz — piyasadaki en yakın muadil bile aynı sınıf makinenin farklı yılına aittir.</p>
<p>Biz bu parçaları raftan seçmeyiz; elinizdeki numunenin gerçek ölçülerini alıp o makineye ait tek adet olarak üretiriz. Bahçe makinesi plastik yedek parça arayışında en sık duyulan cevap komple grup satışıdır; oysa makinenin taşıyıcı gövdesi kullanılabilir durumdayken yalnızca tek bir tutucu ya da mandal kırılmıştır.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>İlk adım numunedir. Kırık parçanın tüm parçalarını, ufalanmış kısımlar dahil saklayın; kırılma yüzeyi bize et kalınlığını ve yük yönünü gösterir. Parçayı elden getirebilir ya da gönderiyle bize ulaştırabilirsiniz. Numune tamamen kayıpsa, parçanın oturduğu yuvanın ölçüsü ve makinenin model bilgisiyle de yol alırız.</p>
<p>Ölçüyü kumpas ile biz alırız: çap, kanal, delik mesafesi, açı ve et kalınlığı tek tek kaydedilir. Kritik ölçüleri size yazılı olarak teyit ederiz — özellikle mil çapı, vida yönü ve delik dairesi çapı gibi yanlış olduğunda parçayı tek kalemde kullanılamaz kılan değerleri. Onay verdiğinizde üretime alınır, kontrol edilip gönderilir. Tek adet üretmek işimizin olağan hâli; adet artırma zorunluluğu koymayız.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Mil çapı, kama kanalı genişliği ve derinliği:</strong> tekerlek göbeğinin akstan tork almasını sağlayan tek nokta burasıdır; kanal dar ya da bol olursa tekerlek boşa döner.</li>
<li><strong>Göbek genişliği ve omuz yüksekliği:</strong> tekerleğin gövdeye sürtmeden, doğru hizada dönmesini belirler.</li>
<li><strong>Flanş delik sayısı, delik çapı ve delik dairesi çapı:</strong> vidalar zorlanmadan girsin diye numuneden birebir alınır.</li>
<li><strong>Burç yuvası iç çapı, derinliği ve geçme payı:</strong> yuva sıkı olursa parça çatlar, bol olursa oynar; pay ölçüye göre verilir.</li>
<li><strong>Kademe adım açısı ve kademe sayısı:</strong> yükseklik ayar kolunun her konumda net kilitlenmesi bu açıya bağlıdır.</li>
<li><strong>Kilit dişi profili ve pim çapı:</strong> kolun kendiliğinden düşmemesi için diş tepesi ve pim boşluğu ayrı ayarlanır.</li>
<li><strong>Mandal tırnak yüksekliği ve geri esneme payı:</strong> kapağın titreşimde açılmaması ile mandalın ilk kullanımda kırılmaması arasındaki dengeyi bu iki değer kurar.</li>
<li><strong>Vida merkez mesafesi ve vida gövde çapı:</strong> mevcut delikleri değiştirmeden montaj yapabilmeniz için.</li>
<li><strong>Misina kafası tutucusunda iç vida ölçüsü ve dönüş yönü:</strong> sağ ya da sol diş yanlış seçilirse parça çalışırken gevşer.</li>
<li><strong>Misina çıkış deliği çapı, sayısı ve konumu:</strong> kullandığınız misina kalınlığına göre belirlenir, deliğin aşınan ağzı kalınlaştırılabilir.</li>
<li><strong>Et kalınlığı ve iç destek yoğunluğu:</strong> darbe alan bölgelerde artırılır, gereksiz ağırlık eklenmez.</li>
<li><strong>Yüzey dokusu ve farklı renk seçenekleri:</strong> gövdeye görsel olarak uyum için.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Sınıfı, parçanın makinede gördüğü işe bakarak belirleriz; kimseyi ihtiyacı olmayan bir üst kademeye yönlendirmeyiz. Kapak içinde kalan, güneş görmeyen ve düşük yük taşıyan bir tutucu için standart sınıf yeterlidir; gereksiz maliyeti size yüklemeyiz. Sürekli güneş altında kalan dış mekân parçaları için <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekân parçası seçenekleri</a> ayrı ayrı anlatılıyor.</p>
<p>Açıkta duran, gün boyu güneş altında kalan ve nem gören parçalarda — kapak mandalı, deflektör tırnağı, dış gövde kelepçesi — ısı ve UV koşuluna dayanıklı sınıfa çıkarız; ASA ve PETG bu grupta çalışır; standart sınıfa göre renk solmasına ve gevrekleşmeye belirgin biçimde daha dirençlidir.</p>
<p>Tekerlek göbeği, ayar kolu kilidi ve misina kafası tutucusu gibi sürekli yük ve titreşim alan parçalarda karbon ya da cam elyaf takviyeli sınıfa geçeriz. PA-CF ve PA-GF, rijitlik ve aşınma direncinin gerçekten belirleyici olduğu bu noktalarda tercih edilir. Hangi sınıfa gireceğinizi numuneyi gördükten sonra söyler, gerekçesini de yazarız.</p>
<h2>Dürüst sınır</h2>
<p>Ne ürettiğimizi ve neyi kapsam dışında tuttuğumuzu açık söylüyoruz. Ürettiklerimiz: tekerlek göbeği, yükseklik ayar kolu ve kademe kilidi, kapak mandalı ve menteşe pimi, misina kafası tutucusu ve gövdesi, sap kelepçesi, kablo yönlendirici, deflektör tırnağı gibi taşıyıcı ve kumanda parçaları.</p>
<p>Kapsam dışı tuttuğumuz kısım kesici organın kendisi ve bıçak tahrik hattıdır. Bıçak, bıçak tutucu metal göbek, misinanın kendisi, kavrama ve metal tahrik mili bu sayfanın konusu dışındadır; bıçağı döndüren hat üzerindeki bir parçayı plastik muadille değiştirmeyi de önermeyiz. Bunlar güvenlik parçalarıdır ve yerine geçecek malzeme sınıfı ayrıdır. Misina kafası tutucusu bu hattın açık istisnasıdır: misina kesici bir organ değil, savrularak kesen esnek bir sarf malzemesidir. Tutucuyu ölçüsüne göre üretiriz; ancak önce makinenin çalışma devrini ve kafaya binen yükü sorar, bu iki değeri ölçüyle birlikte yazılı teyit ederiz. Değerler takviyeli sınıfın sınırını aşıyorsa parçayı üretmeyiz, bunu da baştan söyleriz. Ölçü sizden, üretim bizden; sınırı da işin sonunda değil, ilk konuşmada söyleriz.</p>
<h2>Sipariş</h2>
<p>Numunenizi ya da ölçülerinizi iletin; uygunluk ve fiyat teyidini yazılı veririz. Siteden kartla online ödeme yapabilirsiniz, ölçüye özel üretimler de buna dahildir. Konuşarak ilerlemek isterseniz WhatsApp hattımız açık: +90 545 138 6526.</p>
<p>Elektrikli el aletlerindeki benzer sorunlar için <a href="/elektrikli-supurge-aparati-plastik-parca-uretimi/">elektrikli süpürge aparatı ve hortum bağlantı bileziği üretimi</a> sayfamıza göz atabilirsiniz; kırılan aparat ve bağlantı mantığı burada anlattığımızla aynıdır. Traktör ve tarla ekipmanına ait parçalar için <a href="/tarim-makinesi-plastik-parca-uretimi/">tarım makinesi plastik parça üretimi</a>. Ahır ve padok tarafındaki sağım ünitesi, suluk ve yemlik parçaları için <a href="/sut-sagim-hayvancilik-ekipmani-plastik-parca-uretimi/">süt sağım ve hayvancılık ekipmanı plastik parça üretimi</a> sayfasına bakın. Numuneyi bize ulaştırmadan önce <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır ve nasıl gönderilir</a> sayfasındaki kısa yönergeyi okumanız süreci hızlandırır.</p>""")


def _ozel_parca_kac_gunde_hazir_olur():
    return (u"""<h1>Ölçü onayından sonra 3-5 iş günü içinde kargoya verilir</h1>
<p>Özel üretimde fiyattan önce sorulan soru genelde şudur: özel parça kaç günde hazır olur? Soru yerinde, çünkü bu sayfaya çoğunlukla bir iş beklerken gelinir — makine durmuştur, araç kullanılamaz haldedir ya da tezgâhın bir gözü boş kalmıştır. Parça arayışında geçen günlerin üstüne bir de belirsiz bir üretim süresi eklenince takvim tümüyle kayar.</p>
<p>Net cevap şu: özel üretim parça, ölçü onayından sonra 3-5 iş günü içinde kargoya verilir. Ölçünün bize ulaşması ve teyidi bu sürenin öncesindedir; ölçü netleşene kadar sayaç işlemez. Aşağıda her kademeyi ve süreyi etkileyen noktaları açık yazıyoruz; böylece ölçüye özel parça süresi konusunda tahmin yürütmek yerine takviminizi kurabilirsiniz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p><strong>1. Ölçü ya da numunenin bize ulaşması.</strong> Kırık parçanın fotoğrafını ve kumpas ölçülerini WhatsApp'tan iletebilir, parçayı fiziken de gönderebilirsiniz. Elinizde hiç ölçü yoksa, ölçü alma yöntemini anlatan sayfamızdaki sırayı izlemeniz yeterlidir; <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsünün nasıl alınıp gönderileceğini</a> burada anlatıyoruz.</p>
<p><strong>2. Teyit.</strong> Ölçüleri okur, tutmayan veya eksik kalan yerleri size sorarız. Delik aralığı, cidar kalınlığı, diş ölçüsü gibi kritik değerlerden biri eksikse iş burada durur ve teyit yazışması tamamlanana kadar süre başlamaz.</p>
<p><strong>3. Üretim.</strong> Ölçü onayından sonra başlayan 3-5 iş günlük sürenin üretim kısmını, parçanın boyutuna, cidarına ve adedine göre planlarız.</p>
<p><strong>4. Gönderim.</strong> Üretim biter bitmez parçayı gönderime hazırlarız; teslim noktası ve taşıma koşulları size verdiğimiz takvimde belirtilir.</p>
<p>Ölçüsü tam gelen tek adet işlerde ölçü onayından sonra 3-5 iş günü içinde kargoya verilir; revizyon gerektiren ya da karmaşık ölçülü işlerde süreyi sipariş sırasında ayrıca bildiririz. Ölçü netleşene kadar sayaç işlemez; tarihi ölçünüzü teyit ettiğimizde veririz.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<p>Süreyi belirleyen asıl şey, ölçünüzde hangi değerlerin net geldiğidir. Aşağıdakiler hem parçanızda ayarladığımız gerçek ölçülerdir, hem de eksik kaldığında teyit kademesini uzatan kalemlerdir:</p>
<ul>
<li><strong>Dış çap ve iç çap.</strong> Parçanın oturma yerini bu ikisi belirler; biri eksikse yeniden ölçmeden ilerleyemeyiz.</li>
<li><strong>Yükseklik ve cidar kalınlığı.</strong> Kalın cidar üretim kademesini uzatır, ince cidar kısaltır; süre tahmininde ilk baktığımız değer budur.</li>
<li><strong>Delik çapı ve delikler arası mesafe.</strong> Montajın tutması buna bağlıdır; yanlış gelen bir delik mesafesi doğrudan bir revizyon turu anlamına gelir.</li>
<li><strong>Diş ölçüsü ve adımı.</strong> Vidalı bağlantılarda dişin standardı bilinmiyorsa numune isteriz; bu da ölçü teyidini uzatır.</li>
<li><strong>Kanal, oluk ve kama yuvası genişliği.</strong> Hareketli parçalarda toleransı burada tuttururuz; ölçü net gelirse tek turda biter.</li>
<li><strong>Açı ve eğim.</strong> Eğik yüzeyli parçalarda açı bildirilmezse teyit yazışması uzar.</li>
<li><strong>Adet.</strong> 1 adet ile 50 adet arasındaki fark doğrudan üretim kademesine yansır; adedi erken söylerseniz verdiğimiz tarih o kadar kesin olur.</li>
<li><strong>Renk.</strong> Farklı renk seçenekleri sunuyoruz; istediğiniz renk o an elimizde yoksa bunu tarih verirken belirtiriz.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzeme kararı da süreye dokunur, ama seçim kriterimiz hız değil, parçanın çalıştığı yerdir. Oda koşulunda duran, güneş ve ısı görmeyen bir parçada standart sınıf yeterlidir. Motor bölmesi, dış cephe, güverte gibi ısı ve UV gören yerlerde PETG ya da ASA sınıfına çıkarız. Yük taşıyan, sürtünen veya titreşim altında çalışan parçalarda karbon ve cam elyaf takviyeli PA-CF, PA-GF sınıfını öneririz. Gerekmediği halde üst sınıfa itmeyiz: iç mekânda duran bir tutamak için elyaf takviyeli malzeme hem gereksiz, hem de teslimi uzatan bir tercih olur. Malzemeyi de ölçü gibi konuşarak, parçanın çalışma koşuluna göre birlikte belirleriz.</p>
<h2>Dürüst sınır</h2>
<p>Süre konusunda da kapsam konusunda da abartmıyoruz. Tarih veririz, gecikme olursa aynı gün haber veririz; tutulamayacak bir gün sözü vermeyiz. Kapsamda ise dişli, burç, kasnak, braket, conta, klips gibi parçaları ölçüye özel üretiriz. Pervane dediğimizde fan ve hafif çark kastedilir, tekneyi iten pervane değil. Profil ve beam türü parçaları hafif, yük taşımayan kullanımlar için yaparız. Conta tarafında düşük ve orta seviye zorlanan hatlar hedefimizdir; yüksek zorlanan hatlarda sizi uygun malzemeye yönlendirir, gerekiyorsa işi almayız. Yanma riski taşıyan ya da can güvenliğine doğrudan bağlı kritik parçalarda da iş almıyoruz. Bu sınırları önden söylememizin nedeni açık: yanlış beklentiyle üretilen parça hem sizin gününüzü hem bizim işimizi geri alır.</p>
<h2>Sipariş</h2>
<p>Ölçüleriniz netse siteden kartla online ödeme yapabilirsiniz; ölçüye özel işler de bu akışa dahildir. Emin olamadığınız bir değer varsa önce WhatsApp'tan yazın: <strong>+90 545 138 6526</strong>. Fotoğrafı ve ölçüleri görür görmez size kademe kademe bir takvim veririz.</p>
<p>Sürenin neden bu aralıkta kaldığını merak ediyorsanız, <a href="/kalip-yaptirmadan-parca-urettirme/">kalıp yaptırmadan küçük seri parça ürettirme</a> sayfası kalıplı üretimin haftalar süren hazırlığıyla farkı anlatıyor. Bütçe tarafını ayrıca planlıyorsanız <a href="/ozel-parca-uretimi-fiyati-nasil-belirlenir/">özel parça üretiminde fiyatın nasıl belirlendiğini</a> anlatan sayfaya bakabilirsiniz. Aradığınız parçanın muadili hiçbir yerde çıkmıyorsa <a href="/piyasada-bulunmayan-yedek-parca-uretimi/">piyasada bulunmayan yedek parça üretimi</a> sayfası konuya daha geniş giriyor.</p>""")


def _plastik_parcaya_vida_disi_acilir_mi():
    return (u"""<h1>Vidalı bağlantıda diş sıyrılmasın diye ne yapıyoruz</h1>
<p>Vidayla bağlanacak bir parça ürettiğimizde diş çözümünü parçanın kendisiyle birlikte planlıyoruz: metal gömme somun mu oturacak, doğrudan diş mi açılacak, o bölgede cidar ne kadar kalın kalacak ve bağlantı ömrü boyunca kaç kez sökülüp takılacak. Gömme somun, plastiğe gömülen hazır metal bir ek parçadır; plastik parçayı biz üretiriz, dişin dayanması için yuvasını açar ve somunu yerine oturturuz. "Plastik parçaya vida dişi açılır mı" sorusunun kısa cevabı evet; uzun cevabı ise dişin ne kadar dayandığının parçanın ölçüsüne, malzemesine ve montaj alışkanlığınıza bağlı olduğudur. Bu yüzden sipariş öncesinde vidanın çapını, kafa tipini ve o bağlantının ne sıklıkta açılacağını sorarız.</p>
<p>Sahadan gelen şikâyet neredeyse hep aynı: parça sağlam duruyor ama vida yuvası bir noktadan sonra boşta dönüyor. Plastik parçada diş sıyrılması çoğu zaman yalnızca malzeme tercihinden değil, diş boyunun kısa kalmasından, cidarın ince bırakılmasından veya aynı yuvanın onlarca kez sökülmesinden kaynaklanır. Aynı yuvaya metal gömme somun oturttuğunuzda vidanın karşılaştığı yüzey artık metal olur; yük plastiğe geniş bir alandan, sıyırma yerine yayılarak aktarılır. Vidalı plastik parça üretiminde iki çözümü de sunuyoruz, hangisinin gerektiğine parçanın çalışma koşuluna göre karar veriyoruz.</p>
<h2>Nasıl çalışır: getir, ölç, üret</h2>
<p>Elinizde kırık ya da dişi boşalmış bir parça varsa onu bize ulaştırın; yoksa net fotoğraf, kumpas ölçüsü ve kullandığınız vidanın çap-boy bilgisi de yeterli olur. Parçayı ölçer, vidalı bölgeyi ayrı bir kalem olarak ele alır, size iki seçeneği yan yana koyarız: doğrudan diş yeterli mi, yoksa gömme somun mu gerekli. Karar verdikten sonra üretir, montaj yönüne göre yuva derinliğini ayarlar ve deneme montajı yapabileceğiniz şekilde teslim ederiz. Ölçü sizden, üretim bizden; karar ikimizin ortak işi.</p>
<h2>Ölçünüze göre ayarladığımız seçenekler</h2>
<ul>
<li><strong>Vida nominal çapı ve diş adımı:</strong> Kullandığınız cıvata belliyse (M3'ten M10'a kadar geniş bir aralıkta) yuva ona göre hazırlanır, vida yerine rahat oturur.</li>
<li><strong>Gömme somun tipi ve boyu:</strong> Kısa somun ince cidarda işe yarar, uzun somun daha yüksek sıkma kuvvetini taşır; seçim cidar kalınlığına göre yapılır.</li>
<li><strong>Somun yuvasının iç çapı ve derinliği:</strong> Yuva doğru ölçüldüğünde somun merkezde ve dik oturur; eğri oturan somun daha ilk sıkmada yükü tek noktaya yığar.</li>
<li><strong>Diş boyu, yani vidanın parça içindeki temas uzunluğu:</strong> Genel yaklaşımımız bu boyu vida çapının en az iki katına çıkarmaktır; kısa diş, sıyrılmanın en sık sebeplerinden biridir.</li>
<li><strong>Vida göbeğinin dış çapı ve çevresindeki cidar kalınlığı:</strong> Göbek fazla inceyse sıkma anında çatlayabilir, gereğinden kalınsa parçayı büyütür; ikisinin ortasını ölçüyle buluruz.</li>
<li><strong>Delik eksen mesafesi ve kenar payı:</strong> Deliğin kenara mesafesi yetersizse sıkarken kenar yarılabilir; mevcut montajınızdaki eksen mesafesini birebir tuttururuz.</li>
<li><strong>Kör delik veya geçme delik tercihi:</strong> Kör delik su ve toz geçişini büyük ölçüde azaltır, geçme delik uzun cıvatayla arkadan somunlamaya izin verir.</li>
<li><strong>Havşa, silindir kafa yuvası veya düz oturma yüzeyi:</strong> Vida kafası parçadan taşmasın isteniyorsa havşa açarız; taşması sorun değilse düz yüzey daha fazla yük taşır.</li>
<li><strong>Diş girişindeki pah ve kılavuz payı:</strong> Küçük bir pah vidanın çapraz girme riskini azaltır, bu da ilk montajda oluşan hasarı düşürür.</li>
<li><strong>Renk ve yüzey:</strong> Farklı renk seçenekleri sunarız; görünen montajlarda mevcut parçanızın tonuna yakın çalışırız.</li>
</ul>
<h2>Doğru malzeme</h2>
<p>Malzemeyi bağlantının çalıştığı yere göre seçeriz. İç mekânda, ılıman ortamda, elle sıkılan ve düşük yük gören bir bağlantı için standart sınıf yeterlidir; sizi gereksiz üst sınıfa itmeyiz, çünkü fiyatı yükseltir ama o montajda karşılığı sınırlı kalır. Güneş gören, dış ortamda duran ya da ısınan bir gövde söz konusuysa PETG veya ASA tarafına geçeriz; bu sınıf sıcaklık ve UV altında formunu daha iyi koruduğu için diş yuvası da geç gevşer. Sık sökülen, yüksek tork gören, titreşim altındaki bağlantılarda karbon veya cam elyaf takviyeli PA-CF / PA-GF sınıfını öneririz; sertliği sayesinde diş yanaklarının ezilmesi gecikir. Gömme somun bu merdivenin her kademesinde uygulanabilir ve çoğu durumda malzemeyi yükseltmekten daha etkili bir çözüm olur. <a href="/malzeme-rehberi/">Malzeme rehberi</a>, sınıfların hangi koşulda çalıştığını karşılaştırır.</p>
<h2>Dürüst sınır</h2>
<p>Yüksek tork uygulanan ve düzenli olarak sökülüp takılan bağlantılarda doğrudan açılmış diş yerine metal gömme somun öneririz; bunu tercih etmezseniz dişin zamanla gevşeyebileceğini önden söyleriz. Bir kez monte edilip yerinde kalacak, elle sıkılan bağlantılarda doğrudan diş çoğu zaman yeterlidir ve gereksiz maliyet çıkarmayız. Emniyet açısından kritik, can güvenliğine bağlı ya da sertifika istenen cıvatalı bağlantıları üstlenmeyiz. Vidalı bölgenin metal muadiliyle aynı sıkma kuvvetini taşıyacağını da iddia etmeyiz; hedefimiz parçanın kendi montajında düzgün çalışmasıdır. Vida ve somunun kendisini ölçüye göre üretmek ise bu sayfanın konusu dışında, ayrı bir kalem olarak ele alınır.</p>
<h2>Sipariş</h2>
<p>Ölçüsü netleşmiş işler için sitede kartla online ödeme yapabilirsiniz; ölçüye özel üretim de bu akışa dahildir. Emin olamadığınız bir ölçü varsa parçanın fotoğrafını ve kullandığınız vidanın çapını WhatsApp'tan +90 545 138 6526 numarasına iletin, gömme somun mu yoksa doğrudan diş mi gerektiğini birlikte karara bağlayalım.</p>
<p>Vidalı bağlantıda sıkma yüzeyini genişletmek veya cıvata boyunu dengelemek gerekiyorsa <a href="/olcuye-ozel-distans-ara-pul-uretimi/">ölçüye özel ara pul ve distans üretimi</a> sayfasındaki iç çap, dış çap ve kalınlık seçeneklerine göz atın; ikisi çoğu zaman aynı montajda buluşur. Bağlantı elemanının kendisini ölçüye göre yaptırmak istiyorsanız <a href="/olcuye-ozel-vida-somun-civata-uretimi/">ölçüye özel vida, somun ve cıvata üretimi</a> ayrı bir hizmet olarak duruyor. Elinizdeki mevcut parçadan birebir çoğaltma için <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre parça üretimi</a> sayfasına bakabilirsiniz.</p>""")


def _hangi_parcalar_ozel_uretimle_yapilamaz():
    return (u"""<h1>Hangi Parçalar Özel Üretimle Yapılamaz?</h1>
<p>Elinizde kırılmış ya da piyasada bulunamayan bir parça var ve "bu plastikten olur mu" diye soruyorsunuz. Cevabı baştan net verelim: parçaların büyük bölümü ölçüye özel üretilebilir, ama hepsi değil. Sınırı söylemeden iş almak hem size hem bize zarar verir. Aşağıda hangi işi aldığımızı, hangisini almadığımızı ve emin olmadığınızda ne yapmanız gerektiğini yazdık. Ölçü sizden, üretim bizden.</p>
<h2>Hiç yapamadığımız işler</h2>
<p>Şu başlıklar bizim işimiz değil, açıkça söylüyoruz:</p>
<ul>
<li>Metal üretimi ve metal işleme; talaşlı imalat, freze, torna gibi süreçler.</li>
<li>Cam, seramik, silikon ve kauçuk döküm; kalıplı seri üretim.</li>
<li>Lehim, kaynak, galvaniz, eloksal, krom kaplama gibi birleştirme ve yüzey işlemleri.</li>
<li><strong>Can güvenliği taşıyan ve yük taşıyan yapı elemanları.</strong> Bir insanın ağırlığını taşıyacak ayak, vinç veya asansör bağlantısı, emniyet halatı kulağı gibi parçalar plastikle yapılmaz; bu tür işleri kabul etmiyoruz.</li>
<li><strong>Yüksek basınç ve akışkan tutma.</strong> Basınçlı hat, hidrolik devre, yakıt deposu gövdesi gibi işler kapsamımız dışında.</li>
<li><strong>Sertifikalı ve sürekli gıda teması.</strong> Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; o belgeyi vermiyoruz.</li>
<li><strong>Sürekli çok yüksek sıcaklık.</strong> Fırın içi ve egzoz yakını gibi sürekli yüksek sıcaklıkta kalan konumlar malzememizin sınırını aşar; malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz, üzeri bizim işimiz değildir.</li>
</ul>
<p>Parçanız yukarıdaki kesin maddelerden birine giriyorsa doğru adres biz değiliz; sizi boş yere oyalamayız. Gıdayla ya da içme suyuyla temas eden parçalar ile sıcak su ve program başına birkaç dakika buhar gören noktalar bu maddelerin dışındadır: kullanım yerini yazın, malzeme uygunluğunu birlikte değerlendirir, işi doğru sınıfla üretiriz. Metal gereken işlerde çoğu zaman parçanın tamamı değil yalnızca bir bölümü metaldir. O zaman gövdeyi biz üretiriz; mil, rulman ya da yaylı pim gibi metal elemanı siz temin edersiniz, biz parçayı o standart elemanın ölçüsüne göre — yuvası, geçme toleransı ve somun yatağı dahil — tasarlar ve üretiriz.</p>
<h2>Üretilebilir ama ömrü sınırlı parçalar</h2>
<p>Şu iki başlıkta iş alırız; yeter ki beklenti baştan doğru kurulsun:</p>
<ul>
<li><strong>Bilinçli olarak feda edilen parçalar.</strong> Bazı mekanizmalarda plastik parça, arıza anında önce kendisi kırılıp arkasındaki pahalı organı korusun diye seçilir. Bu işi üretiriz; ama parçanın "önce feda olan" rolünü ve değişim aralığını baştan konuşuruz.</li>
<li><strong>Ağır aşınma.</strong> Metal üzerinde sürekli sürten, kum ve çakıl içinde çalışan yüzeyler zamanla aşınır; parçayı üretiriz ama ömrünün sınırlı olacağını baştan söyleriz. Bu işlerde ikinci bir adedi yedek olarak çıkarmak en ucuz çözümdür.</li>
</ul>
<h2>Nasıl karar veriyoruz</h2>
<p>Parçanın adına değil, çalıştığı yere bakarız. Dört soru sorarız: parça ne kadar kuvvet taşıyor, kaç derecede çalışıyor, güneş veya deniz suyu ya da kimyasal görüyor mu, kırılırsa ne oluyor. Sonuncusu en önemlisi. Parça kırılınca sadece bir işlev mi duruyor, yoksa biri zarar mı görüyor? İkinci durumda işi almayız.</p>
<p>Değerlendirme için elimizde şunlar olmalı: kırık parçanın birkaç net fotoğrafı, kumpasla alınmış ölçüler (dış çap, iç çap, kalınlık, delik aralığı) ve parçanın makine üzerindeki yerini gösteren bir kare. Ölçü almayı bilmiyorsanız WhatsApp'tan +90 545 138 6526 numarasına yazın; hangi ölçüyü nereden alacağınızı adım adım anlatırız.</p>
<h2>Doğru malzeme</h2>
<p>Sınırı belirleyen en büyük etken malzeme seçimidir. Aynı geometri yanlış malzemeyle iki günde dağılır, doğru malzemeyle uzun süre görevini yapar.</p>
<ul>
<li><strong>PLA</strong> — yalnız iç mekân, düşük yük, prototip ve ölçü kontrolü. Sıcak bırakılmış araç içinde bile deforme olur.</li>
<li><strong>PETG</strong> — genel amaçlı; nem, hafif darbe ve ev/atölye koşulları için dengeli seçim.</li>
<li><strong>ASA</strong> — dış ortam, güneş ve deniz havası. UV altında rengini ve dayanımını koruyan seçenek.</li>
<li><strong>TPU (esnek)</strong> — conta, tampon, esneyerek geçen tutucu gibi yumuşak sınıf işleri; sitede seçilebilen standart sınıflardandır.</li>
<li><strong>PA (naylon) ve takviyeli PA-CF / PA-GF · özel talep</strong> — sürtünen, aşınan, yük binen parçalar; dişli, makara, braket. Takviye rijitliği ve ölçü kararlılığını artırır; ısı dayanımını ise takviye değil taşıyıcı malzeme belirler.</li>
</ul>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Standart sınıflarda farklı renk seçenekleri sunuyoruz; tercihinizi sipariş notunda belirtebilirsiniz. Hangi malzemenin sizin işinize uyduğunu <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasında kullanım örnekleriyle karşılaştırdık.</p>
<h2>Dürüst sınır</h2>
<p>Üç konuda baştan sınır koyuyoruz, çünkü en çok yanlış anlaşılan işler bunlar:</p>
<ul>
<li><strong>Pervane ve çark.</strong> Fan pervanesi, havalandırma çarkı, hafif karıştırıcı çarkı üretiriz. Tekneyi iten deniz pervanesi üretmeyiz; o iş bu malzemenin işi değil. Ayrıntı: <a href="/olcuye-ozel-fan-carki-uretimi/">ölçüye özel fan çarkı üretimi</a>.</li>
<li><strong>Profil ve beam.</strong> Hafif, yük dışı profiller, kablo kanalı, kızak ve destek çıtaları uygundur; ağırlık taşıyan konstrüksiyon elemanı değildir. Ayrıntı: <a href="/olcuye-ozel-profil-beam/">ölçüye özel profil ve beam</a>.</li>
<li><strong>Conta ve sızdırmazlık.</strong> Düşük ve orta basınçta çalışan kapak contası, ara pul, toz keçesi mantığındaki parçalar olur; contayı esnek TPU sınıfında üretiriz. Yüksek basınçlı hat contası olmaz. Ayrıntı: <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a>.</li>
</ul>
<h2>Sık sorulan sınır soruları</h2>
<p><strong>Orijinali metaldi, plastikten olur mu?</strong> Bazen olur. Parça sadece konum tutuyor, kapak sabitliyor ya da hafif kuvvet aktarıyorsa takviyeli naylon çoğu zaman yeterli gelir. Sürekli darbe alan, sıkma torkuyla zorlanan yerlerde ise metal kalmalıdır.</p>
<p><strong>Motor içinde çalışacak parça yapılır mı?</strong> Motor bloğu içi ve yağ/ısı ortamı bizim işimiz değil. Motorun dışındaki kapak, kelepçe, kablo tutucu, hava kanalı ağzı gibi parçalar rahatlıkla üretilir.</p>
<p><strong>Tek parça mı, çok mu?</strong> Tek parça da üretiriz, küçük seri de. Aynı parçadan birkaç adet istemeniz üretimi kolaylaştırır.</p>
<p><strong>Numunem kırık, işe yarar mı?</strong> Yarar. Kırık parçanın iki yarısı bir arada ölçü almak için genellikle yeterlidir; eksik köşe varsa karşı tarafın ölçüsünden tamamlarız.</p>
<h2>Sipariş</h2>
<p>Parçanızın fotoğrafını ve ölçülerini WhatsApp'tan +90 545 138 6526 numarasına gönderin. Uygunsa malzeme önerisini ve fiyatı yazarız; uygun değilse nedenini ve nereye başvurmanız gerektiğini söyleriz. Onay verdiğinizde sitede kartla online ödeme yapabilirsiniz. Üretilen parçalar 3-5 iş gününde kargoya verilir.</p>
<p>Emin olmadığınız parçayı sormaktan çekinmeyin; "bu olur mu" sorusunun cevabı bizde ücretsiz. Ölçü sizden, üretim bizden.</p>""")


def _karbon_fiber_takviyeli_naylon_parca_ne_zaman_gerekir():
    return (u"""<h1>Karbon Fiber Takviyeli Naylon Parça Ne Zaman Gerekir?</h1>
<p>Sıradan sınıfta ürettirdiğiniz parça iş görmediyse ya da parçayı baştan zorlu bir yere takacaksanız sorulacak soru şudur: bu iş gerçekten takviyeli sınıf mı istiyor, yoksa bir alt sınıf yeter mi? Karbon fiber takviyeli naylon (PA-CF) ve cam fiber takviyeli naylon (PA-GF) elimizdeki en sert ve en rijit seçeneklerdir; ama her parça bu sınıfa ihtiyaç duymaz ve gereksiz yere seçilirse maliyeti boşuna yükseltir. Bu sayfa, kararı elinizdeki parçaya bakarak vermeniz için. Ölçü sizden, üretim bizden.</p>
<h2>Takviyeli naylon nedir, ne değildir</h2>
<p>Naylon (PA) tek başına sağlam ve aşınmaya dayanıklı bir mühendislik malzemesidir; fakat esnektir ve nem çekince yumuşar. İçine kısa karbon ya da cam elyaf katıldığında elyaf, malzemenin içinde yük taşıyan bir iskelet gibi çalışır. Sonuç: belirgin şekilde daha yüksek rijitlik, yük altında daha az eğilme ve daha düşük çekme payı, yani ölçü tutarlılığı. Isı dayanımını ise elyaf katkısı değil taşıyıcı malzeme belirler; ısı asıl sorununuzsa sınıfı taşıyıcıya göre seçeriz.</p>
<p>Bedeli de var. Takviyeli sınıf daha serttir ama daha gevrektir: darbede eğilerek değil, kırılarak yorulur. İnce klipsler, esneyerek geçen tırnaklar, sürekli bükülen menteşeler için takviyeli malzeme yanlış tercihtir; orada esneyebilen bir sınıf daha uzun ömürlüdür. Takviyeli sınıfta renk seçenekleri sınırlıdır; hangi tonda üretilebileceğini özel talep sırasında birlikte netleştiririz.</p>
<h2>Nasıl karar verirsiniz</h2>
<p>Beş soruyu sırayla cevaplayın. Birine bile "evet" diyorsanız takviyeli sınıfı konuşuyoruz demektir.</p>
<p><strong>1. Parça sürekli bir yükü mü taşıyor?</strong> Bir ağırlığı asılı tutan braket, gergi kolu, mesnet gibi parçalar günlerce sabit yük altında kalır. Sıradan sınıf bu koşulda zamanla sarkar; buna sünme denir ve genelde kırılmadan önce ölçü kaçmasıyla kendini gösterir. Takviyeli naylon bu sarkmaya belirgin şekilde daha çok direnir.</p>
<p><strong>2. Parça yük altında eğiliyor mu?</strong> Uzun bir mesnet, ince kesitli braket, kapağı taşıyan kol zorlandığında yaylanır ve ölçü kaçar. Takviyeli sınıf burada belirgin şekilde daha az eğilir. Parça aynı zamanda sıcak bir bölgede duruyorsa ısıyı takviye değil taşıyıcı malzeme belirler; sınır değerler için <a href="/isiya-dayanikli-plastik-parca-uretimi/">ısıya dayanıklı plastik parça üretimi</a> sayfasına bakın.</p>
<p><strong>3. Parçanın vidası, dişi ya da yatağı var mı?</strong> Sıkılan bir cıvatanın altında ezilen kulak, defalarca sökülüp takılan dişli göbek, mile geçen bir kovan. Bunlar noktasal basınca maruz kalır; elyaf takviyesi burada ezilmeyi ciddi biçimde azaltır. Vidalı bağlantılarda metal geçme somun kullanmanızı öneririz; somunu siz temin edersiniz, biz yatağını o ölçüye göre veririz.</p>
<p><strong>4. Parça sürtünerek mi çalışıyor?</strong> Kızak, kayar burç, zincir kılavuzu, aktarma dişlisi. Naylon ailesi zaten düşük sürtünmelidir, takviyeli olanı aşınma ömrünü uzatır. Ayrıntı için <a href="/asinmaya-dayanikli-surtunme-parcasi-uretimi/">aşınmaya dayanıklı sürtünme parçası üretimi</a> sayfasına bakabilirsiniz.</p>
<p><strong>5. Aynı yerden ikinci kez mi kırıldı?</strong> Aynı noktadan tekrar eden kırık, yalnızca malzemenin değil çoğu zaman kesitin de yetersiz olduğunu söyler. Bu durumda malzemeyi yükseltmekle kalmayıp o bölgeye et kalınlığı ve kavis eklemeyi öneririz.</p>
<p>Beş sorunun hepsine "hayır" diyorsanız takviyeli sınıfa para vermenize gerek yok. Kapak, muhafaza, ara parça, düzenleyici, gösterge tutucu gibi işlerde bir alt sınıf hem daha uygun hem daha tokdur.</p>
<h2>Doğru malzeme</h2>
<p>Sıralamayı düşükten yükseğe böyle kuruyoruz:</p>
<ul>
<li><strong>PLA</strong> — iç mekân, yük yok, ısı yok. Şablon, maket, düzenleyici, kalıcı olmayan işler.</li>
<li><strong>PETG</strong> — genel amaçlı dayanıklı sınıf. Tok, nemden etkilenmez, ılık ortamlara dayanır. Ev ve atölye parçalarının çoğu burada biter.</li>
<li><strong>ASA</strong> — dışarıda, güneş ve hava koşulu altında kalan parçalar. UV ve hava şartlarına dirençlidir, rengini ve biçimini korur.</li>
<li><strong>TPU (esnek)</strong> — sertlik merdiveninin dışında ayrı bir aile: conta, tampon, esneyerek geçen tutucular; sitede seçilebilir.</li>
<li><strong>PA (naylon) · özel talep</strong> — sürtünen, esneyip geri dönmesi gereken, darbe alan parçalar. Kayar yüzeyler, burçlar, tokluk isteyen bağlantılar.</li>
<li><strong>PA-CF / PA-GF (karbon veya cam fiber takviyeli naylon) · özel talep</strong> — yukarıdaki beş sorunun en az birine "evet" diyen işler. En yüksek rijitlik ve en iyi ölçü kararlılığı.</li>
</ul>
<p>Karbon ile cam takviye arasındaki fark pratikte şu: karbon takviyeli daha rijit ve daha hafiftir, ölçü kararlılığı biraz daha iyidir; cam takviyeli ise darbeye karşı daha affedicidir ve maliyeti daha uygundur. Titreşim alan, ara sıra darbe yiyen parçalarda cam takviyeliyi, eğilmemesi gereken taşıyıcı parçalarda karbon takviyeliyi öneririz. Tüm sınıfların karşılaştırması için <a href="/malzeme-rehberi/">malzeme rehberi</a> sayfasına bakın.</p>
<h2>Dürüst sınır</h2>
<p>Takviyeli naylon üst sınıfımızdır, ama metalin yerine geçtiğini söylemeyiz. Yüksek tork aktaran güç organları, basınçlı hidrolik hatlar, sürekli kızgın yüzeye temas eden parçalar bizim alanımızın dışındadır; metal üretimi, talaşlı imalat ya da kaplama işi yapmıyoruz ve işiniz oraya düşüyorsa bunu açıkça söyleriz. Sert parçalarda site üzerinden seçilebilen aile PLA, PETG ve ASA'dır; PA ile takviyeli PA-CF / PA-GF özel talep sınıfıdır. Conta ve kayış gibi esneklik isteyen işleri esnek TPU sınıfında çözeriz; TPU sitede seçilebilen standart sınıflardandır ve ürün sayfası olan kalemlerde doğrudan kartla ödenebilir. Bizim alanımıza girmeyen bir talebi kabul edip sizi oyalamak yerine baştan söyleriz.</p>
<p>Ürettiğimiz pervane ve çark parçaları hava ya da hafif akış çarkıdır, tekne itişi sağlayan pervane değildir. Profil ve kiriş parçaları hafif ve yük taşımayan kullanımlar içindir. Conta ve sızdırmazlık parçaları düşük–orta basınç içindir. Takviyeli malzeme bu sınırları genişletir ama kaldırmaz; parçanın nereye takılacağını bize söylerseniz sınıfı birlikte doğru seçeriz.</p>
<h2>Sipariş</h2>
<p>Naylon (PA) ve takviyeli sınıf sitedeki hazır seçenekler arasında durmaz; PA, PA-CF ve PA-GF özel talep olarak değerlendirilir. Ölçüleriniz hazırsa parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Hangi sınıfın gerektiğinden emin değilseniz de aynı numaradan yazabilirsiniz; gereksiz üst sınıfa yönlendirmeyiz.</p>
<p>PLA, PETG, ASA ve esnek TPU ile çözülen işlerde, sitede ürün sayfası olan katalog ve ölçüye özel (parametrik) kalemlerde doğrudan sepetten kartla ödeyebilirsiniz; numuneden ya da ölçüden üretilecek parçalarda ölçüyü WhatsApp'ta netleştirdikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Ölçüye özel olarak ne tür parçalar ürettiğimizi görmek için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfasına bakabilirsiniz.</p>
<p>Kırık parçayı atmayın; elinizde durması en güvenilir referanstır. Onaylanan işler <strong>3-5 iş gününde kargoya verilir</strong>.</p>""")


def _kaseye_islenecek_logo_dosyasi_nasil_hazirlanir():
    return (u"""<h1>Kaşeye İşlenecek Logo Dosyası Nasıl Hazırlanır?</h1>
<p>Logolu kaşe siparişlerinde işi geciktiren tek şey neredeyse hep aynı: gönderilen logo dosyası. Kartvizitte güzel duran bir görsel, kaşe gövdesine işlendiğinde okunmayabilir. Bu sayfa, dosyanızı göndermeden önce kendi kendinize yapabileceğiniz kontrolleri anlatır. Ölçü sizden, üretim bizden.</p>
<p>Kaşede logo, mürekkebi taşıyan yüzeyin kâğıda göre yükseltilmesiyle oluşur. Yani logonuz renkle değil, <strong>yüzey farkıyla</strong> çalışır. Bu yüzden sorulacak soru "logom güzel mi" değil, "logom iki renge indirildiğinde ne kalıyor" sorusudur.</p>
<h2>Hangi dosya işlenir: SVG mi PNG mi</h2>
<p>Kısa cevap: <strong>SVG tercih edilir, temiz bir PNG de çoğu zaman iş görür.</strong></p>
<p><strong>SVG (vektör):</strong> En iyisi budur. Vektör dosyada logonun kenarları matematiksel eğrilerdir; kaşe boyutuna küçültüldüğünde kenar bozulmaz. Elinizde marka kılavuzu, tabela dosyası veya tasarımcınızın verdiği bir vektör varsa (SVG, AI, EPS, PDF) onu gönderin; gerekirse SVG'ye biz çeviririz. SVG gönderirken yazıları "eğriye dönüştürülmüş" (outline) haliyle kaydettirin — aksi halde bizde o font yoksa yazı kayar.</p>
<p><strong>PNG (piksel):</strong> Şeffaf zeminli, en az 1000 piksel genişliğinde ve keskin kenarlı bir PNG işlenebilir. Logoyu vektöre çevirip kaşe formuna oturturuz. Ancak PNG'de ince detaylar, gölge, degrade ve yumuşak kenarlar ayıklanmak zorundadır; bu ayıklama sırasında logonun bir kısmı sadeleşebilir.</p>
<p><strong>Çalışmayan dosyalar:</strong> WhatsApp'tan geçmiş ekran görüntüsü, sosyal medya profil fotoğrafı, faturadan telefonla çekilmiş logo fotoğrafı, JPEG sıkıştırması yüzünden kenarları bulanmış görseller. Bunlar gelirse size haber verir, elinizdeki temiz kaynağı isteriz.</p>
<h2>Logonuzu ikiye indirin: kalan şey kaşeniz olur</h2>
<p>Gönderdiğiniz logoyu zihninizde siyah-beyaza indirin. Gri tonlar, degradeler ve gölgeler kaşede yoktur; hepsi ya dolu ya boş olur. Şu üç kontrolü yapın:</p>
<p><strong>1. Renk ayrımına dayanan detay var mı?</strong> Lacivert zemin üstünde gri yazı gibi bir kurgu, iki renge indiğinde kaybolur. Bu tür logolarda genelde markanın sade tek renk versiyonunu kullanırız.</p>
<p><strong>2. En ince çizgi ne kadar ince?</strong> Kaşe ölçeğinde 0,4 mm'nin altındaki çizgiler ve çok küçük puntolu alt başlıklar ("kurumsal çözümler", vergi numarası, web adresi) mürekkeple dolar ve leke gibi çıkar. Ölçüyü küçültmek yerine o satırı çıkarmak ya da büyütmek daha doğrudur.</p>
<p><strong>3. İç boşluklar kapanıyor mu?</strong> "a", "e", "o" harflerinin gözleri ile logo içindeki dar boşluklar, mürekkep yayıldığında birbirine kaynayabilir. Sık dokulu, çok çizgili amblemlerde bu riski önceden söyleriz.</p>
<p>Bu üç maddeyi geçen bir logo, kaşede rahat okunur.</p>
<h2>Nasıl sipariş verilir ve dosya nasıl gönderilir</h2>
<p>Akış basittir: logonuzu gönderirsiniz, işlenebilirliğini kontrol eder, gerekiyorsa sadeleştirme öneririz; onayınızdan sonra kaşe gövdesi ölçüye göre üretilir.</p>
<p>Logolu ya da özel biçimli kaşede sizden istediğimiz bilgiler şunlar:</p>
<ul>
<li><strong>İçerik türü:</strong> yalnız yazı, emoji/ikon, yazı + ikon ya da logo (SVG). Logolu seçenekte dosyayı siz gönderirsiniz.</li>
<li><strong>Yazı satırları:</strong> firma adı, unvan, vergi dairesi ve numarası gibi satırları düz metin olarak yazın; görselden okumaya çalışmayalım.</li>
<li><strong>Biçim:</strong> dikdörtgen, kare veya yuvarlak.</li>
<li><strong>Yaklaşık ölçü ve satır sayısı:</strong> gövde içeriğe göre büyür, bu yüzden kaç satır olacağı ölçüyü belirler.</li>
<li><strong>Çerçeve:</strong> yok, düz ya da kesikli.</li>
<li><strong>Sap:</strong> saplı ya da sapsız. Sap ayrı parçadır, gövdeye vidalanarak takılır; istenirse sonradan değiştirilebilir.</li>
<li><strong>Renk:</strong> standart sınıflarda farklı renk seçenekleri arasından seçersiniz.</li>
</ul>
<p>Ürün sayfasındaki gerçek aralıklar şunlardır: yazı yüksekliği 6–14 mm (varsayılan 8 mm), kenar payı 3–10 mm (varsayılan 5 mm), yüzey kabartması 0,8–2,2 mm (varsayılan 1,4 mm) ve kaşe metni en çok 40 karakter. Biçim dikdörtgen, kare ya da yuvarlak; sap saplı ya da sapsız seçilir. Gövde ölçüsü ayrı bir alan değildir, yazı yüksekliği ile kenar payından çıkar. İhtiyacınız bu aralıkların dışındaysa — daha büyük gövde, 40 karakterden uzun metin, logo ya da özel kenar işlemi — ürün sayfası yerine WhatsApp'tan +90 545 138 6526 numarasına yazın; ölçüyü ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Süreç ve ürün seçenekleri için <a href="/kisiye-ozel-logolu-kase-yaptirma/">kişiye özel logolu kaşe yaptırma</a> sayfasına bakabilirsiniz.</p>
<h2>Doğru malzeme</h2>
<p>Kaşe gövdesi ve sapı, elde tutulan ve düzenli kullanılan bir parçadır; boyut kararlılığı ve tokluk ister. Standart kullanım için PETG uygundur: darbeye PLA'dan dayanıklıdır, ofis ve tezgâh koşullarında ölçüsünü korur.</p>
<p>Kaşenin araç içinde, güneş gören bir vitrinde veya sıcak bir depoda kalma ihtimali varsa ASA öneririz; ısı ve güneş altında deforme olmaya karşı daha güvenlidir. Günde defalarca kullanılan kaşelerde en çok zorlanan yer sap ile gövdenin vida dişi bölgesidir; orada da PETG ya da ASA sınıfında kalırız, ikisi de ürün sayfasından seçilir. Kaşeyi naylon ya da takviyeli sınıfa çıkarmak gerekmez; ıslak mürekkeple sürekli sanayi temposu bu ürünün hedefi değildir. PLA yalnız az kullanılan, masada duran kaşelerde tercih edilir.</p>
<p>Logo işlenecek, gövdesi ürün sayfasındaki aralıkların dışında kalacak ya da özel kenar işlemi istenen kaşelerde yazı satırlarını, biçimi, yaklaşık ölçüyü ve varsa logo dosyanızı WhatsApp'tan +90 545 138 6526 numarasına gönderin; fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Parçanın nerede duracağını söyleyin, malzemeyi biz doğru seçelim.</p>
<h2>Dürüst sınır</h2>
<p>Kaşe, üzerine ıstampa mürekkebi alan bir yüzeydir; matbaa klişesi değildir. Beklentiyi doğru kuralım:</p>
<ul>
<li><strong>Çok ince detay sınırlıdır.</strong> Saç teli inceliğindeki çizgiler, mikro yazılar ve fotoğraf tonlaması kaşede karşılık bulmaz. Bu yüzden sadeleştirme öneriyoruz.</li>
<li><strong>Metal klişe, lazer gravür, kauçuk döküm gibi işleri biz yapmayız.</strong> İşiniz gerçekten kauçuk otomatik kaşe gerektiriyorsa bunu açıkça söyler, kendi çözümümüzü dayatmayız.</li>
<li><strong>Islak mürekkeple sürekli sanayi temposu</strong> için tasarlanmış bir üründen bahsetmiyoruz; günlük ofis, atölye, muhasebe ve etkinlik kullanımı hedefimizdir.</li>
</ul>
<p>Aynı dosya mantığı ölçülü işaretleme gereken ürünlerde de geçerlidir; ölçü ve işaret isteyen işler için <a href="/olcuye-ozel-cetvel-mastar-sablon-uretimi/">ölçüye özel cetvel, mastar ve şablon üretimi</a> sayfası yol gösterir.</p>
<h2>Sipariş</h2>
<p>Logolu ya da emoji/ikonlu kaşe siparişleri WhatsApp'tan ilerler: dosyanızı ve yazı satırlarınızı <strong>+90 545 138 6526</strong> numarasına gönderin; işlenebilirliğini kontrol eder, biçimi ve ölçüyü birlikte netleştiririz, ardından siparişinizi <strong>kartla online ödeyerek</strong> tamamlarsınız. Yalnız yazıdan oluşan kaşede ise ürün sayfasına girip metin, yazı boyutu, kenar payı, kabartma derinliği, biçim ve sap seçimini yaptıktan sonra Sepete Ekle ile sepete ekler, kartla online ödersiniz.</p>
<p>Onaylanan işler 3-5 iş gününde kargoya verilir. Fiyatın neye göre çıktığını <a href="/ozel-parca-uretimi-fiyati-nasil-belirlenir/">özel parça üretimi fiyatı nasıl belirlenir</a> sayfasında, süreye etki eden adımları <a href="/ozel-parca-kac-gunde-hazir-olur/">özel parça kaç günde hazır olur</a> sayfasında bulabilirsiniz.</p>""")


def _kayis_profili_nasil_belirlenir_gt2_htd_t5():
    return (u"""<h1>Kayış Profili Nasıl Anlaşılır? GT2, HTD ve T5 Ayrımı</h1>
<p>Kayış koptuğunda ya da kasnağın dişleri sıyrıldığında ilk soru hep aynıdır: bu kayış hangi profil? Profil yanlış belirlenirse yeni kasnak dişlere oturmaz, kayış tırmanır, sistem kısa sürede yeniden durur. İyi haber şu: profili anlamak için özel bir cihaz gerekmez. Bir cetvel, mümkünse bir kumpas ve düz bir masa yeterlidir. Aşağıda diş adımını nasıl ölçeceğinizi, GT2, HTD ve T5 arasındaki gerçek farkı ve profili belirledikten sonra aynı ölçüde kasnağı nasıl yaptıracağınızı adım adım anlatıyoruz.</p>
<h2>Nasıl ölçersiniz: diş adımı</h2>
<p>Diş adımı, iki komşu dişin aynı noktaları arasındaki mesafedir. Profilin kimliği bu ölçüdür.</p>
<ol>
<li>Kayışı düz bir zemine, dişli yüzü yukarı bakacak şekilde gergin biçimde yatırın.</li>
<li>Tek diş ölçmeyin. Bir dişin tepesinden on birinci dişin tepesine kadar olan mesafeyi ölçün — yani arada tam on diş aralığı kalsın — ve çıkan değeri ona bölün. Tek diş ölçümünde yarım milimetrelik sapma bile sizi yanlış profile götürür.</li>
<li>Sonuç 2 mm çıktıysa GT2 2M, 3 mm çıktıysa GT2 3M ya da HTD 3M, 5 mm çıktıysa GT2 5M, T5, AT5 ya da HTD 5M, 10 mm çıktıysa T10 gündemdedir. Bu ikililerde profili kesinleştirmek için bir sonraki adıma ve kayış sırtındaki yazıya bakın; emin olamazsanız fotoğrafı bize gönderin.</li>
<li>Diş şekline bakın: dişin dibi yuvarlak mı, yoksa kenarları düz inen yamuk (trapez) bir diş mi? Aynı adım iki farklı diş şekliyle gelebilir, ayrım burada netleşir.</li>
<li>Kayış sırtındaki yazıyı okuyun. Çoğu kayışta "GT2", "HTD 5M" ya da "225-5M-09" gibi bir kabartma bulunur. Ortadaki ifade profili, ilk sayı çevre uzunluğunu, son sayı genişliği verir.</li>
</ol>
<p>İki noktaya dikkat edin: kayış eskiyip uzadıysa adım büyümüş görünür, ölçtüğünüz değeri en yakın standart adıma yuvarlayın; kayış kopmuşsa uçlardaki iki dişi hesaba katmayın, deforme olmuş olabilirler.</p>
<p>Kasnak tarafında da iki ölçü isteriz: diş sayısı ve kayışın oturduğu yatak genişliği. Diş sayısını saymak en güvenli yoldur; kırık kasnakta parçalar duruyorsa birleştirip sayabilirsiniz. Genişliği kumpasla ölçün, yan flanşların iç yüzleri arası mesafe kayış genişliğinden bir tık fazladır. Ölçü almanın genel yöntemi ve fotoğrafı bize nasıl ileteceğiniz için <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır</a> sayfasına bakabilirsiniz.</p>
<h2>Profil isimleri ne anlatır</h2>
<p><strong>GT2 (2, 3 ve 5 mm):</strong> yuvarlatılmış diş dibi, düşük geri boşluk. Konum hassasiyeti isteyen küçük makinelerde yaygındır. En sık karşılaşılan hali 2 mm adımlı olanıdır.</p>
<p><strong>HTD 3M, 5M, 8M:</strong> derin ve yuvarlak diş. Aynı genişlikte daha yüksek tork taşır, hafif geri boşluğu vardır. Endüstriyel aktarmalarda ve pompalarda sık görülür.</p>
<p><strong>T2.5, T5, T10 ve AT5:</strong> yamuk dişli metrik aile. T5, AT5, HTD 5M ve GT2 5M'in adımı aynıdır ama diş şekilleri farklıdır; sahada en çok karıştırılan yer tam olarak burasıdır. Adımı 5 mm ölçtüyseniz önce diş dibinin yuvarlak mı düz mü olduğuna bakın: düz inen yamuk diş T5 ya da AT5'i, yuvarlak diş dibi ise GT2 5M veya HTD 5M'i gösterir.</p>
<p><strong>MXL, XL, L ve 40DP:</strong> inç tabanlı eski aile. Adımları metrik ölçüde küsuratlı çıkar (MXL yaklaşık 2,03 mm); on diş üzerinden ölçmek şart olur.</p>
<p>Kayış ve kasnak aynı profilde olmalıdır. Adımı tutan ama diş şekli farklı bir eşleşme önce çalışır gibi görünür, sonra diş uçları yuvarlanır ve kayış atlar. Kasnaklardan biri sağlamsa onu ölçü referansı alın.</p>
<p>Profili doğru belirlediğinizde işin geri kalanı kolaydır: aynı profilde, sizin verdiğiniz diş sayısı ve genişlikte kasnak üretiriz. Numuneniz varsa parçayı gönderin, ölçüsünü biz alalım; <a href="/numuneye-gore-triger-kasnagi-uretimi/">numuneye göre triger kasnağı üretimi</a> tam olarak bu iştir. Ölçüleri kendiniz veriyorsanız <a href="/kasnak-olcuye-ozel-uretim/">ölçüye özel kasnak üretimi</a> sayfasındaki bilgi listesi işinizi görür.</p>
<h2>Doğru malzeme</h2>
<p>Kasnağın nerede çalıştığı malzemeyi belirler. Oda sıcaklığında, düşük yüklü bir düzenekte PETG yeterlidir ve boyut kararlılığı iyidir. Güneş ve dış hava koşulu varsa ASA tercih edilir; renk ve yüzey uzun süre formunu korur. Diş dibi sürekli aşınıyorsa ya da yük arttıysa naylon (PA) ve özellikle karbon ya da cam elyaf takviyeli PA-CF / PA-GF doğru adrestir: diş ucu kolay kolay ezilmez, kasnak ölçüsünü daha uzun süre korur. Isıyı ise takviye değil taşıyıcı malzeme belirler. PLA'yı yalnızca ölçü kontrol numunesi için kullanırız, çalışan parçada değil. Kayışta ise sert sınıf değil, sitede seçilebilen esnek TPU sınıfı doğrudur. Standart sınıflarda farklı renk seçenekleriyle üretebiliriz.</p>
<h2>Dürüst sınır</h2>
<p>Bizim güçlü olduğumuz taraf kasnak ve makara gibi sert plastik parçalardır. Kayışın kendisi ayrı bir konudur: kordonlu fabrika kayışının yerini tutma iddiamız yok. Düşük–orta yüklü düzeneklerde kayışı da profiline, diş sayısına ve genişliğine göre esnek TPU sınıfında üretiriz; sürekli tam yükte çalışan yüksek yüklü aktarmada standart kayış kullanın. Sürekli çalışan, yüksek tork aktaran ana aktarma kasnakları metal kasnağın alanıdır; biz bu işi üstlenmeyiz. Mili ve rulmanı siz temin edersiniz; biz kasnağı o elemanın ölçüsüne göre, yuvası ve geçme toleransı dahil kurarız.</p>
<h2>Sipariş</h2>
<p>Bize şu bilgileri iletin: profil (GT2 2 mm, HTD 5M, T5 gibi), diş sayısı, kayış genişliği, mil çapı ve renk. Kayış da üretilecekse şeklini (kapalı döngü ya da düz) yazın. Emin olmadığınız kalem varsa fotoğraf gönderin. Diğer makine parçaları için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfasına da göz atın.</p>
<p>Sitedeki ölçüye özel kasnak sayfasında diş sayısı 18-80, kayış genişliği 4-30 mm ve mil çapı 3-5 mm aralığında ölçü ve malzeme seçilir, sepete eklenip kartla ödenir; yan flanş yerleşimi (iki taraf, yalnız üst, yalnız alt ya da flanşsız) ile mil bağlantısı (düz delik, kamalı kanal, altıgen ya da D-lama) da aynı kasnak sayfasında seçilir. Kayışın kendi sayfasında diş sayısı 20-300, genişlik 3-50 mm aralığı geçerlidir; kayışta malzemeyi esnek TPU seçin, sert sınıf kayış işini görmez. İki kalem de aynı sepete girer. Mil çapı 5 mm'nin üstündeyse, setskur yuvası gibi ürün sayfasında karşılığı olmayan bir isteğiniz varsa veya naylon (PA) / takviyeli sınıf (PA-CF / PA-GF) gerekiyorsa — bunlar sitede hazır seçenek değildir — kasnağın fotoğrafını, ölçülerini ve nerede çalıştığını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Onaylanan işler 3-5 iş gününde kargoya verilir. Ölçü sizden, üretim bizden.</p>""")


def _kirik_dislinin_modulu_nasil_bulunur():
    return (u"""<h1>Kırık Dişlinin Modülü Nasıl Bulunur?</h1>
<p>Elinizde kırılmış bir plastik dişli var; üzerinde kod yok, kataloğu da yok. Yeni bir dişli yaptırmak için her şeyden önce tek bir sayıyı bulmanız gerekir: <strong>modül</strong>. Modül, dişin büyüklüğünü tanımlar ve iki dişlinin birbirine geçip geçmeyeceğini belirleyen ölçüdür. Modülü yanlış seçilen dişli, çapı doğru olsa bile karşı dişliye oturmaz. Bu sayfada modülü elinizdeki parçadan nasıl çıkaracağınızı adım adım anlattık. Ölçü sizden, üretim bizden.</p>
<h2>Modül nedir, neden kritiktir</h2>
<p>Modül, bölüm dairesi çapının diş sayısına bölümüdür; pratikte "dişin kaç milimetrelik olduğu" demektir. Modülü 1 olan bir dişli, modülü 1,25 olan bir dişliyle çalışmaz. Bir aktarma organında birlikte dönen bütün dişliler aynı modüle ve aynı basınç açısına sahip olmak zorundadır. Basınç açısı endüstride neredeyse her zaman 20 derecedir; aksi bir işaret yoksa bu değeri kabul ederiz.</p>
<p>İkinci kritik nokta merkez mesafesidir. Dişlinin oturduğu iki mil arasındaki mesafe sabit olduğu için, modül ile diş sayısı birlikte bu mesafeyi tutturmak zorundadır. Bu yüzden ölçüyü tahmin etmiyor, elinizdeki parçadan hesaplıyoruz.</p>
<h2>Nasıl ölçersiniz ve modülü nasıl hesaplarsınız</h2>
<p><strong>1. Dış çapı ölçün.</strong> Dişlinin diş uçlarından diş uçlarına, en geniş yerinden ölçün. Kumpas varsa kumpasla ölçün; yoksa parçayı düz bir kâğıdın üzerine koyup iki kenarını işaretleyin ve işaretler arasını cetvelle ölçün. Ölçüyü milimetre cinsinden, virgülden sonra bir hane ile not edin. Dişli aşınmışsa diş uçları hafif yuvarlanmış olabilir, bu birkaç onda milimetrelik fark yaratır; sorun değil, dördüncü adımdaki yuvarlama bunu düzeltir.</p>
<p><strong>2. Diş sayısını sayın.</strong> Bir dişi kalemle işaretleyip oradan başlayın ve tur tamamlanana kadar sayın. Dişli kırıksa ve bazı dişler eksikse, sağlam bir bölümdeki diş aralığını ölçüp tam tura oranlayın; ya da eksik bölgeyi kâğıt üzerine çizip tamamlayın.</p>
<p><strong>3. Formülü uygulayın.</strong> Düz (spur) bir dişlide:</p>
<p><strong>modül = dış çap ÷ (diş sayısı + 2)</strong></p>
<p>Örnek: dış çap 48 mm, diş sayısı 46 ise modül = 48 ÷ 48 = 1. Örnek: dış çap 27 mm, diş sayısı 34 ise modül = 27 ÷ 36 = 0,75.</p>
<p><strong>4. En yakın standarda yuvarlayın.</strong> Yaygın modüller: 0,4 · 0,5 · 0,6 · 0,7 · 0,75 · 0,8 · 1 · 1,25 · 1,5 · 2 · 2,5 · 3. Ölçüm hatası yüzünden 0,98 ya da 1,03 çıkması normaldir; bunlar modül 1 demektir. Arada kalırsanız iki değeri de bize yazın, karşı dişlinin ölçüsüyle birlikte doğrusunu seçelim. Ev aletlerinde ve küçük mekanizmalarda modül genelde 0,5 ile 1 arasındadır; tarım ve sanayi makinelerinde 1,5 ile 3 arası daha sık görülür.</p>
<p><strong>5. Kontrol edin.</strong> Komşu iki diş ucunun tepe noktaları arası mesafe, diş adımının yaklaşık karşılığıdır: diş adımı = 3,1416 × modül. Modül 1 için bu yaklaşık 3,14 mm eder. Ölçtüğünüz aralık buna yakınsa hesabınız tutuyordur.</p>
<p>Dişli inç sisteminde ise modül yerine diametral pitch kullanılır; o durumda ölçüleri gönderin, çeviriyi biz yapalım. Ölçü alma yöntemleri ve kumpassız çözümler için <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü nasıl alınır</a> sayfasına bakabilirsiniz.</p>
<h2>Modül dışında bize gereken ölçüler</h2>
<p>Dişliyi birebir üretebilmemiz için şunları da isteriz: <strong>kalınlık</strong> (diş genişliği), <strong>delik yani mil çapı</strong>, mil profili (düz delik, D-mil, kama kanalı, tırtıllı ya da vidalı), göbek varsa göbek çapı ve yüksekliği, kaçık delik veya set vidası yuvası. Dişli tipini de belirtin. Helis ve çift helis dişlilerde helis açısı ile dönüş yönü de belirleyicidir; bunlar şartsa ürün sayfası yerine WhatsApp'tan ilerleriz, emin değilseniz açılı bir fotoğraf yeterli olur.</p>
<p>Karşı dişli, mil ya da kramayer elinizdeyse onun da diş sayısını ve dış çapını gönderin: iki parçanın modülü aynı çıkmalı, çıkmıyorsa ölçümlerden birinde hata var demektir ve bunu üretimden önce yakalamış oluruz. Bu ölçülerle birlikte hangi cihazda çalıştığını ve renk tercihinizi de yazın; standart sınıflarda farklı renk seçenekleri sunuyoruz. Dişli üretiminin bütün seçeneklerini <a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişli üretimi</a> sayfasında toplu halde görebilirsiniz.</p>
<h2>Doğru malzeme</h2>
<p>Dişlide malzeme seçimi ömrü doğrudan belirler. PLA'yı çalışan dişlide kullanmayız; onu yalnız ölçü doğrulama numunesi için üretiriz. Genel amaçlı, darbeye ve ılık ortama dayanıklı çözüm PETG'dir. Güneş ve dış hava koşulu varsa ASA kullanırız. Sürekli dönen, yüke binen dişlilerde PA yani naylon; yüksek tork, aşınma ve boyut kararlılığı isteyen sanayi işlerinde ise karbon ya da cam fiber takviyeli PA-CF / PA-GF öneririz.</p>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Mutfak robotu, blender ve mikser gibi ev aletlerinde tipik seçim için <a href="/ev-aleti-plastik-disli-parca-uretimi/">ev aleti plastik dişli üretimi</a> sayfasına bakın.</p>
<h2>Dürüst sınır</h2>
<p>Özel üretim dişli her yerde metalin yerini tutmaz; sınırını baştan söyleriz. Yüksek devirde sürekli çalışan, ağır tork aktaran ya da yağ banyosunda ısınan güç aktarma dişlilerinde metal dişli doğru çözümdür. Biz metal üretimi, talaşlı imalat ya da kaplama işi yapmıyoruz; işiniz oraya düşüyorsa açıkça söyleriz.</p>
<p>Bunun dışında iki not: fan çarkı ve kanat üretiyoruz, ancak bunlar hava/hafif akış çarkıdır, tekne itişi sağlayan pervane değildir. Profil ve kiriş parçalarımız hafif ve yük taşımayan kullanımlar içindir. Plastik dişliyi bilinçli olarak "önce feda olan parça" diye de seçebilirsiniz; mekanizmayı korumak istediğinizde doğru bir tercihtir.</p>
<h2>Sipariş</h2>
<p>Ölçüleriniz hazırsa iki yol var. Ürün sayfasında dişli tipi olarak düz, helis, çift helis, konik, sonsuz vida, iç dişli, taç ve kramayerin tamamı seçilebilir; modülü 1 ile 1,5, diş sayısı 32-64, kalınlığı 6-8 mm ve delik çapı 2-8 mm aralığındaki işlerde tipi, malzemeyi, rengi ve bu ölçüleri seçer, Sepete Ekle ile sepete ekler, kartla online ödersiniz. Helis açısı, dönüş yönü ve eşleşen dişlinin diş sayısı ürün sayfasında girilemez; belirli bir helis açısı ya da dönüş yönü şartsa, modül 0,5 veya 2 gibi aralık dışı bir değer gerekiyorsa ya da kamalı, D-milli veya göbekli dişli istiyorsanız ölçüleri WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına yazın; eşleşmeyi birlikte doğrular, fiyatı belirledikten sonra siparişinizi kartla online ödersiniz. Kırık parçayı atmayın: <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> akışında numune en güvenilir referanstır.</p>
<p>Onaylanan işler <strong>3-5 iş gününde kargoya verilir</strong>.</p>""")


def _klasik_arac_eski_model_oto_plastik_parca_uretimi():
    return (u"""<h1>Eski Model Araç Plastik Parçası Özel Üretim</h1>
<p>Eski bir aracı ayakta tutarken en çok zorlayan şey motor değil, küçük plastik parçalardır. Kelebek cam mandalı, kolçak yuvası, ızgara tırnağı, kalorifer kumanda düğmesi, torpido kapak menteşesi, kapı döşeme klipsi... Bu parçaların üretimi yıllar önce durmuş; stokta kalan son örnekler ise elden ele dolaşıp fahiş fiyata çıkıyor. Elinizde kırık ya da sağlam tek bir örnek varsa yenisini o örneğin ölçüsüne göre üretiriz. Ölçü sizden, üretim bizden.</p>
<p>Bu sayfa restorasyon yapan araç sahipleri, klasik araç kulüpleri ve oto döşemecileri için yazıldı. İhtiyacınız tek parça da olabilir, aynı parçadan birkaç adet de.</p>
<h2>Nasıl çalışır: örnek parçadan yeni parçaya</h2>
<ol>
<li><strong>Parçanın fotoğrafını gönderin.</strong> Kırık parçayı atmayın; kırık haliyle bile ölçü kaynağıdır. Parçayı düz bir zemine koyup üstten ve yandan çekin, yanına cetvel veya madeni para koyun.</li>
<li><strong>Kritik ölçüleri alın.</strong> Bizim için önemli olan üç şey vardır: parçanın oturduğu yuvanın ölçüsü, vida veya pim deliklerinin çapı ile aralarındaki mesafe, bir de tırnak/klips gibi geçme yerlerinin kalınlığı. Kumpas varsa milimetrik yazın, yoksa fotoğraf üzerinden konuşuruz.</li>
<li><strong>Teyitleşiriz.</strong> Eksik kalan ölçüyü sorar, parçanın araçta hangi yükü taşıdığını netleştirir, malzemeyi ona göre öneririz. Parça çok karmaşıksa örneği kargoyla bize gönderip ölçüyü bizim almamızı isteyebilirsiniz.</li>
<li><strong>Gerekiyorsa önce deneme parçası.</strong> Geçme toleransı hassas parçalarda ilk bir adet üretilir, siz araçta denersiniz. Koşulu şimdiden yazalım: sapma bizim aldığımız ölçüden kaynaklanıyorsa revizyon bizdendir, ayrıca ücret istemeyiz; parçanın ölçüsü sizin isteğinizle değişirse bu yeni bir iş olarak fiyatlandırılır. Adetli işlerde bu adım para ve zaman kazandırır.</li>
<li><strong>Üretim ve gönderim.</strong> Onaydan sonra parça üretilir, kontrol edilir ve <strong>3-5 iş gününde kargoya verilir</strong>. Üretim öncesi ölçü teyidi yazılı olarak sizde kalır, sonradan karışıklık çıkmaz.</li>
</ol>
<p>Bu akış yalnızca otomobile özel değil; <a href="/piyasada-bulunmayan-yedek-parca-uretimi/">piyasada bulunmayan yedek parça üretimi</a> sayfasında aynı yöntemi başka alanlar için de anlattık. Parçanız elinizde kırık durumdaysa <a href="/kirik-plastik-parca-yaptirma/">kırık plastik parça yaptırma</a> sayfasındaki fotoğraf ve ölçü kılavuzu işinizi kolaylaştırır.</p>
<h2>Hangi parçalar için geliyorlar</h2>
<p>En sık istenenler şunlar: kapı ve tavan döşemesini tutan klips ve tırnaklar, kolçak ile kol dayama yuvaları, kelebek cam mandalı ve mafsalı, cam kaldırma mekanizmasının plastik makarası, kalorifer ve radyo kumanda düğmeleri, havalandırma ızgara kanadı, torpido kapak menteşesi, ayna kapağı ve gövde bağlantı ayağı, çamurluk ile marşpiyel altındaki geçme dübeller, plaka altlığı, koltuk yatırma kolu, cam silecek kolu kapağı, far ve stop lambası ayar tırnağı.</p>
<p>İç döşeme tarafında sık kırılan geçmeler için <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim klips parça üretimi</a>, cam mekanizması parçaları için <a href="/cam-krikosu-plastik-parcasi-yaptirma/">cam krikosu plastik parçası yaptırma</a> sayfalarına bakabilirsiniz.</p>
<p>Parçanın orijinal numarası okunmuyorsa sorun değil; numara olmadan da örnekten üretim yapılır. Numara okunuyorsa yazın, iki parça arasında karışıklık olmasın diye kayda geçiririz.</p>
<h2>Doğru malzeme</h2>
<p>Eski araçta parçanın nerede durduğu, hangi malzemeden yapılacağını belirler. Kullandığımız malzemeler ve tipik yerleri:</p>
<ul>
<li><strong>PETG</strong> — kabin içi parçaların çoğu. Tok, kolay kırılmaz, klips ve tırnak gibi esneyip geçen parçalarda iyi sonuç verir.</li>
<li><strong>ASA</strong> — dışarıda, güneş altında duran her şey. Izgara kanadı, ayna kapağı, cam çerçevesi bağlantısı gibi parçalarda güneş ve hava koşuluna PETG'den daha uzun süre dayanır.</li>
<li><strong>PA (naylon) · özel talep</strong> — sürtünen, kayan, sürekli hareket eden yerler: makara, kızak, mafsal burcu, kilit mekanizması içindeki hareketli parça.</li>
<li><strong>PA-CF / PA-GF (karbon veya cam elyaf takviyeli naylon) · özel talep</strong> — yük binen braket, kol, ayak ve mesnet tipi parçalar. Rijitlik ve ölçü kararlılığı gerektiğinde bunu öneririz; ısı dayanımını takviye değil taşıyıcı malzeme belirler.</li>
<li><strong>TPU (esnek)</strong> — tampon, titreşim takozu, esneyerek geçen tutucu ve düşük-orta basınçlı ara conta; sitede seçilebilen standart sınıflardandır.</li>
<li><strong>PLA</strong> — yalnız ölçü denemesi ve maket için. Araç içi sıcaklıkta şeklini koruyamaz, gerçek parçada kullanmayız.</li>
</ul>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Standart sınıflarda farklı renk seçenekleri var; dış parçalarda genelde siyah tercih edilir, iç döşemede araç rengine yakın ton seçilir. Yüzey astar üstünden boyanabilir, döşeme rengine tam uyum isteyen restorasyoncular bu yolu kullanıyor.</p>
<h2>Dürüst sınır</h2>
<p>Her parçayı üretmeyiz; nerede durmamız gerektiğini baştan söylüyoruz.</p>
<ul>
<li><strong>Güvenlik ve taşıyıcı parça yapmayız.</strong> Süspansiyon, direksiyon, fren hattı, emniyet kemeri kilidi, motor takozu gibi can güvenliğine giren parçalar bu üretimin dışındadır.</li>
<li><strong>Isı sınırı var.</strong> Egzoz, turbo ve motor bloğuna yakın, sürekli yüksek sıcaklıkta duran parçalar uygun değildir. Malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Benzin ve solvent ile sürekli temas eden yakıt hattı parçalarını da almayız.</li>
<li><strong>Conta işi esnek TPU sınıfındadır ve düşük-orta basınç ile sınırlıdır.</strong> Kapı fitili yerine geçen sızdırmazlık parçaları, yüksek basınçlı hidrolik ve yağ devresi contaları bizim işimiz değildir.</li>
<li><strong>Fan ve hafif çark üretiriz</strong>, tekneyi iten pervane ya da ağır tahrik yükü taşıyan güç parçası bu kapsamda değil.</li>
<li><strong>Profil ve beam tipi uzun parçalar</strong> hafif, yük taşımayan kullanım içindir.</li>
<li><strong>Metal işleme, talaşlı imalat ve kaplama yapmıyoruz.</strong> Parçanız mutlaka metal olmalıysa bunu açıkça söyler, doğru atölyeye yönlendiririz. Metal vida, pim ve yaylı klipsi siz temin edersiniz; biz parçayı o elemanların ölçüsüne göre, yuvası ve geçme toleransı dahil kurarız.</li>
<li><strong>Görünür yüzeyde birebir orijinal doku garanti etmiyoruz.</strong> Deri veya kumaş dokulu iç kaplama parçalarında yüzey farkı olabilir; kritik olan yer görünürse baştan konuşuruz.</li>
</ul>
<h2>Sipariş</h2>
<p>Örneğinizden üretilen parçaların sitede hazır ürün sayfası olmaz; bu işlerde akış WhatsApp'tan başlar. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını <strong>+90 545 138 6526</strong> numarasına gönderin. Ölçüden emin değilseniz aynı numaradan yazın, hangi noktayı ölçmeniz gerektiğini adım adım söyleriz. Fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Ölçü onayından sonra parça üretilir, kontrol edilir ve 3-5 iş gününde kargoya verilir.</p>
<p>Elinizde birden fazla kırık parça varsa hepsini tek seferde gönderin; aynı araçtan çıkan parçaları birlikte değerlendirmek hem ölçü teyidini hem gönderimi kolaylaştırır.</p>""")


def _plastik_kaplin_gobegi_esnek_kavrama_uretimi():
    return (u"""<h1>Kaplin Göbeği Ölçüye Özel Plastik Üretim</h1>
<p>Motor ile pompa arasındaki kavrama dağıldı, elinizde parçalanmış bir yıldız göbek kaldı ve üzerinde okunur bir kod yok. Piyasada aradığınız ölçüde göbek bulunamıyorsa, parçayı sıfırdan aramak yerine ölçüsünü çıkarmak daha hızlı yoldur: iki mil çapı, tırnak sayısı ve göbek boyu belli olduğunda aynı ölçüde yenisini üretiriz. Ölçü sizden, üretim bizden.</p>
<h2>Kaplin göbeği ne işe yarar, neden ilk o dağılır</h2>
<p>Esnek kavrama üç parçadan oluşur: motor tarafına oturan metal kaplin yarımı, karşı mile oturan ikinci yarım ve ikisinin tırnakları arasına giren elastik göbek. Göbek burada bilerek en zayıf halkadır. İki milin ekseni tam üst üste gelmediğinde, motor ilk kalkışta darbe verdiğinde ya da yük ani değiştiğinde bu darbeyi göbek yutar. Böylece rulman ve mil korunur, dağılan yalnız göbek olur. Yani göbeğin bozulması arıza değil, tasarımın işlediğinin göstergesidir; sizin işiniz doğru ölçüde yenisini takmaktır.</p>
<p>Bu göbeği en çok şu makinelerde değiştiriyoruz: küçük su ve yakıt pompaları, havalandırma fanları, kompresör tahrikleri, konveyör ve karıştırıcı redüktör bağlantıları, tezgâh üstü makineler ve tarım ekipmanı yardımcı milleri. Ortak nokta hep aynıdır: makine sağlamdır, duran tek şey iki mil arasındaki küçük plastik parçadır.</p>
<p>Sorun şurada başlar: makine eskiyse, ithal edilmişse ya da göbek yalnız o modele özelse yedeği bulunmaz. Bir üst ya da bir alt ölçü göbek takmak da çözüm değildir; tırnaklar arasında boşluk kalırsa kavrama vurmaya başlar, sıkı gelirse tırnak dibinden çatlar.</p>
<h2>Nasıl ölçer, nasıl sipariş verirsiniz</h2>
<p>Dağılmış parçaların hepsini bir araya toplayın; tek bir sağlam kanat bile ölçüyü çıkarmaya yeter. Sonra şu ölçüleri alın:</p>
<p><strong>1. Dış çap.</strong> Göbeğin en geniş yerini, kanat uçlarından karşı kanat uçlarına ölçün. Kumpas yoksa parçayı düz bir kâğıda yatırıp iki kenarını işaretleyin, işaretler arasını cetvelle ölçün.</p>
<p><strong>2. Göbek yüksekliği.</strong> Kavrama yarımları arasına giren kalınlık. Bu ölçü iki mil arasındaki boşluğu belirler; şaşarsa kaplin ya sıkışır ya boşta kalır.</p>
<p><strong>3. Tırnak sayısı.</strong> Yıldız göbeklerde tipik olarak altı, sekiz ya da on kanat bulunur. Kanatları sayın; parça kırıksa metal kaplin yarımının üzerindeki yuva sayısını sayın, aynıdır.</p>
<p><strong>4. Kanat kalınlığı ve kanat arası açıklık.</strong> Kavramanın metal yarımındaki yuvanın genişliğini ölçmek en güvenilir yoldur, çünkü o yuva aşınmamıştır.</p>
<p><strong>5. Kaplin yarımlarının dış çapı ve mil çapları.</strong> İki mil farklı çapta olabilir; ikisini de ayrı yazın. Kama kanalı varsa genişliğini ve derinliğini de not edin.</p>
<p>Ölçüleri milimetre cinsinden, virgülden sonra bir hane ile yazın. Ardından kırık parçanın üstten ve yandan fotoğrafını, yanına kumpas ya da cetvel koyarak çekin. Ölçü almakta zorlanırsanız en kolay yol, kırık parçayı bize göndermenizdir; ölçüyü numuneden biz çıkarırız. Aynı yöntemi <a href="/numuneden-plastik-burc-rulman-uretimi/">numuneden plastik burç ve rulman üretimi</a> işlerinde de kullanıyoruz.</p>
<p>Ölçüler elimize geçtiğinde tırnak geometrisini kavramanın metal yuvasına göre yeniden kurar, kritik gördüğümüz her ölçüyü üretimden önce size yazılı olarak teyit ettiririz. Ölçüsünden emin olmadığınız bir kavramada, asıl parçadan önce tek bir deneme göbeği üretip yerine oturmasını kontrol etmeniz en güvenli yoldur.</p>
<h2>Doğru malzeme</h2>
<p>Kaplin göbeğinde malzeme seçimi, parçanın ne kadar dayanacağını doğrudan belirler. Sıradan PLA bu iş için uygun değildir: sürtünmeyle ısınan bir yuvada yumuşar ve kısa sürede dağılır; yalnız ölçü doğrulaması için deneme parçası olarak işe yarar.</p>
<p><strong>TPU (esnek)</strong> ilk sınıfımızdır: göbeğin asıl işi sönümlemedir, darbeyi yutarak rulmanı ve mili korur. Esnek sınıf standart malzemelerimizdendir, özel talep gerektirmez; kaplin göbeğinin sitede hazır ürün sayfası olmadığı için sipariş yine WhatsApp'tan başlar. <strong>PETG</strong>, düşük devirli ve düşük momentli aktarmalarda, oda sıcaklığına yakın ortamlarda çalışır; bir miktar esneyerek darbe yutar. <strong>ASA</strong> rijit sınıftır: UV ve sıcaklığa dayanır, ama darbeyi yutmaz, yükü rulmana ve mile aktarır. ASA'yı yalnız iki durumda öneririz: göbekten sönümleme beklenmiyorsa ve eksen kaçıklığı düzeltilmişse, ya da ortam sıcaklığı esnek sınıfın yaklaşık 60-80 °C bandını aşıyorsa. Sönümleme bekleniyorsa güneş altında ve dış ortamda da TPU'da kalırız: esnek sınıfın UV dayanımı ASA kadar yüksek değildir, ama göbek zaten bilerek feda olan parçadır. <strong>PA (naylon)</strong> özel talep sınıfıdır: sürtünmeye ve tekrarlı darbeye dayanır, kanat dibinde çatlamaya karşı diğerlerinden belirgin şekilde iyidir. <strong>PA-CF veya PA-GF</strong>, yani karbon ya da cam fiber takviyeli naylon, ASA ile aynı koşulda — göbeğin şekil değiştirmemesi gereken, eksen kaçıklığı düzeltilmiş ve sönümlemenin kavramadan beklenmediği düzeneklerde — kullanılır; farkı, aynı rijitliği çok daha yüksek mukavemet ve aşınma direnciyle vermesidir.</p>
<p>Seçimi tahminle değil kullanım yerine göre yaparız: devir, tahmini moment, ortam sıcaklığı ve parçanın yağla temas edip etmediğini yazmanız yeterlidir. Standart sınıflarda farklı renk seçenekleri mevcuttur; renk dayanımı değiştirmez.</p>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<h2>Dürüst sınır</h2>
<p>Bu sayfadaki iş, esnek kavramanın <strong>elastik göbeğidir</strong> — metal yarımlar değil. Kaplin gövdesini, mil bağlantısını ya da metal parçaları biz üretmiyoruz; metal işleme, talaşlı imalat bizim alanımız değildir. Metal kaplin yarımlarını ve mili siz temin edersiniz; biz göbeği o yarımların yuvasına ve mil ölçüsüne göre kurarız. Gövde sağlamsa yalnız göbeği yenilersiniz.</p>
<p>Sınırı açık söyleyelim: özel üretim göbek, yüksek momentli ve sürekli tam yükte dönen ağır sanayi aktarmalarında orijinal göbeğin yerini tutmaz. Küçük pompa, fan, konveyör, ev tipi ve atölye tipi makineler, düşük–orta yüklü tahrik hatları bu üretimin doğal yeridir. Mil eksenleri belirgin şekilde kaçıksa göbek yine kısa ömürlü olur; ömrü uzatmanın yolu doğru malzeme değil, kaçıklığı düzeltmektir. Aynı sınır mantığını sürekli temas eden parçalarda da uyguluyoruz; yükü hangi malzemeye yönlendirdiğimizi <a href="/asinmaya-dayanikli-surtunme-parcasi-uretimi/">aşınmaya dayanıklı sürtünme parçası üretimi</a> sayfasında ayrıntılı yazdık.</p>
<h2>Sipariş</h2>
<p>Ölçüleri ve fotoğrafları WhatsApp'tan <strong>+90 545 138 6526</strong> numarasına gönderin; ölçüyü birlikte kontrol eder, malzemeyi kullanım yerine göre öneririz. Emin olmadığınız ölçüyü boş bırakın, hangi bilginin eksik olduğunu biz söyleriz. Fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Onaydan sonra parça <strong>3-5 iş gününde kargoya verilir</strong>.</p>
<p>Aynı makinede kayış kasnağı ya da başka bir aktarma parçası da yenilenecekse tek seferde çözelim: <a href="/kasnak-olcuye-ozel-uretim/">kasnak ölçüye özel üretim</a> ve <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfalarına bakabilirsiniz.</p>""")


def _sicak_su_ve_buhar_temasli_plastik_parca_uretimi():
    return (u"""<h1>Sıcak Su ve Buhara Dayanıklı Parça Üretimi</h1>
<p>Bulaşık makinesinin sepet tekerleği, su ısıtıcısının kapak mandalı, buharlı pişiricinin kulp bağlantısı, kahve makinesinin kapak menteşesi, çamaşır makinesinin tahliye kapağı tırnağı... Sürekli sıcak su ve buhar gören plastik parçalar zamanla yumuşar, şeklini kaybeder, kılcal çatlar ve bir gün elinizde kalır. Yedeği çoğu zaman tek başına satılmaz; komple modül fiyatı ise parçanın kendisiyle orantısızdır. Elinizdeki deforme veya kırık örneği ölçü kaynağı olarak kullanır, aynı işi yapacak yenisini o koşula uygun sınıfta üretiriz. Ölçü sizden, üretim bizden.</p>
<p>Bu sayfa evinde beyaz eşyasını kendi tamir eden kullanıcılar kadar, servis ve tamirhane işletenler için de yazıldı.</p>
<h2>Nasıl çalışır: deforme parçadan yeni parçaya</h2>
<ol>
<li><strong>Parçayı sökün ve fotoğraflayın.</strong> Eğrilmiş ya da kırık haliyle bile parça ölçü kaynağıdır, atmayın. Düz bir zemine koyup üstten ve yandan çekin; yanına cetvel veya madeni para koyarsanız ölçek oturur.</li>
<li><strong>Kritik ölçüleri verin.</strong> Bizim için üç şey belirleyicidir: parçanın oturduğu yuvanın ölçüsü, vida ile pim deliklerinin çapı ve aralarındaki mesafe, geçme tırnaklarının kalınlığı. Kumpasınız varsa milimetrik yazın, yoksa fotoğraf üzerinden birlikte çıkarırız.</li>
<li><strong>Çalışma koşulunu yazın.</strong> Burası en önemli adım. Parça kaç derece suyla temas ediyor, temas sürekli mi yoksa program başına birkaç dakika mı, üzerinden buhar mı geçiyor, ortamda deterjan veya kireç çözücü var mı? Cevaplar malzemeyi doğrudan değiştirir.</li>
<li><strong>Teyitleşir, üretiriz.</strong> Eksik ölçüyü sorar, gerekiyorsa geçme toleransı için önce tek adet üretip yerine denemenizi isteriz. Oturduğunu gördükten sonra kalan adede geçeriz.</li>
</ol>
<p>Ölçüyü hiç bilmiyorsanız örneği bize kargoyla gönderip ölçüyü bizim almamızı isteyebilirsiniz. Aynı yaklaşımın diğer ev aletlerindeki karşılığı için <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> sayfasına bakabilirsiniz.</p>
<h2>Sıcak su ve buhar gören tipik parçalar</h2>
<p>En sık karşımıza çıkan işler şunlardır: bulaşık makinesinde sepet tekerleği ve ray durdurucusu, kapak menteşe bağlantısı, kapak yay kolu; su ısıtıcısında kapak mandalı, kulp bağlantı parçası, su seviyesi göstergesi kelepçesi; kahve makinesinde gövde kapak menteşesi ve hazne yuvası kılavuzu; buharlı pişiricide gövde kulpu, kapak kilit dili ve tahliye kapağı tırnağı; çamaşır makinesinde deterjan çekmecesi kılavuzu ve tahliye kapağı kolu. Ortak nokta hepsinin küçük, ölçüsü kritik ve tek başına satılmayan parçalar olmasıdır.</p>
<p>Parçanın kodu silinmişse ya da yoksa sorun değil; biz koddan değil, örneğin ölçüsünden çalışırız.</p>
<h2>Doğru malzeme</h2>
<p>Sıcak su ve buhar işinde parçanın şekli kadar malzemesi belirleyicidir. Aynı geometri yanlış malzemede bir ay dayanmaz.</p>
<ul>
<li><strong>PLA burada kullanılmaz.</strong> Ilık suda bile yumuşamaya başlar; sıcak su gören hiçbir parçayı bu sınıfta üretmeyiz.</li>
<li><strong>PETG</strong>, ara sıcaklıkta çalışan, doğrudan buhar hattında olmayan parçalar için makul bir seçimdir (yaklaşık 70-75 °C): kapak mandalı, ray kılavuzu gibi parçalar. Neme ve deterjana karşı dengeli davranır.</li>
<li><strong>ASA</strong> — sıcak su ve buhar gören mekanik parçalarda sitede seçebileceğiniz en yüksek ısı sınıfı (yaklaşık 90-95 °C): mandal, kılavuz, tutamak, sepet tekerleği, ray durdurucusu. Güneş gören dış gövdelerde de sararmaya dirençlidir.</li>
<li><strong>PA (naylon) · özel talep</strong> — sürtünen, geçen, kilitlenen parçalarda aşınma direnci için.</li>
<li><strong>PA-CF / PA-GF (karbon veya cam fiber takviyeli naylon) · özel talep</strong>, yük taşıyan parçaların sınıfıdır: kol yatağı, dişli göbeği, taşıyıcı braket. Rijitlik ve ölçü kararlılığında en güçlü seçenektir; ısı dayanımını takviye değil taşıyıcı malzeme belirler.</li>
</ul>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Standart sınıflarda farklı renk seçenekleri sunarız; parçanın rengi işlevini değiştirmez, malzeme değiştirir. Sınıflar arasındaki farkı ayrıntılı okumak isterseniz <a href="/malzeme-rehberi/">malzeme rehberi</a> ve <a href="/isiya-dayanikli-plastik-parca-uretimi/">ısıya dayanıklı plastik parça üretimi</a> sayfalarına bakın.</p>
<h2>Dürüst sınır</h2>
<p>Nerede işe yaradığımızı söylediğimiz kadar, nerede yaramadığımızı da söyleriz. Malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir.</p>
<ul>
<li><strong>Basınçlı hat ve akışkan yolu bizim işimiz değil.</strong> Basınç altında kalan hat elemanlarını (kazan, buhar borusu, emniyet valfi) ve akışkanı taşıyan ya da yönlendiren parçaları (püskürtme kolu, hazne borusu, valf gövdesi) üretmeyiz. Bizim alanımız devrenin dışındaki mekanik parçalardır: mandal, tutamak, sepet tekerleği, ray durdurucusu, kılavuz, kapak tırnağı, kelepçe gövdesi.</li>
<li><strong>Conta düşük–orta basınç içindir.</strong> Bulaşık makinesi, tahliye hattı, gövde kapağı gibi program başına ısınan noktalarda sızdırmazlık elemanını çalışma yerine göre ölçüye özel üretiriz. Contayı esnek TPU sınıfında üretiriz; bu sınıfın ısı bandı yaklaşık 60-80 °C'dir, ASA gibi üst sert sınıfların altında kalır. Sürekli sıcak kalan ya da buhar gören noktada conta yerine mekanik parçayı üstleniriz — contanın çalışacağı sıcaklığı önce yazın, uygun olup olmadığını söyleyelim. Uygunsa ürün sayfasında malzeme olarak TPU'yu, iç çap 5-200 mm ve kesit kalınlığı 1-15 mm aralığında ölçüyü, yuvarlak, kare ya da pahlı profili seçip sepete ekler, kartla ödersiniz; bu aralığın dışında kalan ölçüler WhatsApp'tan ilerler. İçme suyu ya da gıda devresine giren bir sızdırmazlık elemanı söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz; yüksek basınçlı devrede ya da doğrudan alev yakınında kullanılmasını önermeyiz. Ayrıntı için <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta üretimi</a>.</li>
<li><strong>Fan ve hafif çark tarafındayız.</strong> Buhar tahliyesinde dönen hafif fan kanadını üretiriz; ağır yük altında sürekli dönen güç aktaran çarkı bu malzemelerle önermeyiz.</li>
<li><strong>Metal işlemeyiz.</strong> Talaşlı imalat, kaynak ve kaplama işlerini yapmayız. Parçanız gerçekten metal olmak zorundaysa bunu baştan söyler, sizi boşuna oyalamayız.</li>
<li><strong>Sertifikalı gıda ekipmanı ve alev bizim alanımız değil.</strong> Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; o belgeyi vermiyoruz. Gıdayla ya da içme suyuyla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Bu sayfadaki işlerde alanımız ekipmanın mekanik parçalarıdır. Ocak üstü, fırın içi ve doğrudan alev gören konumlar için parça üretmeyiz.</li>
</ul>
<p>Sınır cümlesi kurmak müşteri kaybettirmez; yanlış yerde çalışan bir parça kaybettirir.</p>
<h2>Sipariş</h2>
<p>Elinizdeki parçanın fotoğrafını ve ölçüsünü <strong>+90 545 138 6526</strong> numarasına gönderin. Ölçüde emin olmadığınız yer varsa aynı numaradan sorabilirsiniz; çalışma koşulunu birlikte netleştirip malzemeyi öneririz. Ölçü ve malzeme netleştikten sonra fiyatı belirler, siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Onaylanan siparişler <strong>3-5 iş gününde kargoya verilir</strong>.</p>""")


def _sut_sagim_hayvancilik_ekipmani_plastik_parca_uretimi():
    return (u"""<h1>Süt Sağım ve Hayvancılık Ekipmanı Plastik Parça Üretimi</h1>
<p>Sağım ünitesindeki tutucu kırıldığında, suluk şamandıra kapağı çatladığında ya da padok düzeneğindeki kelepçe yerinden çıktığında iş bekler. Bu parçalar çoğu zaman tek başına satılmaz; bayi sizi komple ünite almaya yönlendirir ya da "modeli kalmadı" der. Biz elinizdeki kırık parçayı ölçer, aynı görevi görecek yenisini ölçüye özel üretiriz. Ölçü sizden, üretim bizden.</p>
<h2>Hangi parçalar geliyor</h2>
<p>Çiftlikten en sık gelen işler şunlar: sağım başlığı ve kolektör çevresindeki tutucular, hortum askısı ve yönlendirici klipsleri, süt hattı taşıyıcı ayakları, vakum hattı bağlantı gövdeleri, pulsatör kapak ve kelepçeleri, otomatik suluk şamandıra kolu ve kapağı, yemlik bölme mandalı, kilit dili, padok ve boyunduruk düzeneğindeki plastik burç ve tutucular, sürü yönetim panosunun kırılan muhafaza kulakları.</p>
<p>Bunların büyük kısmı "küçük ama işi durduran" parçalardır. Seri üretimde bir bayinin stokta tutması mantıksız olduğu için ortadan kalkarlar. Ölçüye özel üretimde ise tek adet üretmek sorun değildir; hatta yedek olarak ikinci bir adet çıkarmak en ucuz sigortadır. Ekipmanın markası ya da parça kodu bilinmese de olur; ölçü elimizdeyse üretiriz.</p>
<p>Kırık parçanın yerine geçecek bir bağlantı elemanı arıyorsanız <a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe üretimi</a> sayfasındaki ölçü listesi işinizi hızlandırır. Traktör, römork, balya makinesi gibi tarla tarafındaki parçalar için <a href="/tarim-makinesi-plastik-parca-uretimi/">tarım makinesi plastik parça üretimi</a> sayfasına bakın.</p>
<h2>Nasıl çalışır</h2>
<p>Üç yol var. Birincisi, kırık parçayı bize kargoyla gönderirsiniz; parçaları birleştirip ölçer, aslına uygun yenisini üretiriz. İkincisi, parça tamamen kaybolduysa yerine oturduğu yuvanın ölçüsünü alırsınız: dış çap, iç çap, kalınlık, delik aralığı, vida ölçüsü ve varsa açı. Kumpas yoksa parçayı düz bir zemine koyup cetvelle yanından fotoğraflamanız çoğu iş için yeterli olur; eksik kalan ölçüyü biz sorarız. Üçüncüsü, parça sağlamken yedek çıkarmak istiyorsanız aynı akış geçerlidir ve montajı sökmeden ölçü alabilirsiniz.</p>
<p>Ölçü alırken en çok atlanan üç nokta şudur: parçanın oturduğu milin gerçek çapı, vidanın diş ölçüsü ve tutucunun montaj deliği arasındaki mesafe. Bu üçünü doğru verirseniz iş ilk seferde tutar; şüphedeyseniz eski parçayı da gönderin, karşılaştırırız.</p>
<p>Ölçüler netleştikten sonra malzeme ve renk seçimini birlikte yaparız, üretim onayınızla başlar. Onaylı işler 3-5 iş gününde kargoya verilir. Aynı parçadan birden fazla adet isterseniz tek seferde üretilir; yedek olarak ikinci adedi aynı siparişte istemek genelde daha uygun olur.</p>
<h2>Doğru malzeme</h2>
<p>Ahırda parçayı öldüren üç şey vardır: yıkama suyunun sıcaklığı, temizlik kimyasalı ve güneş. Malzemeyi buna göre seçeriz.</p>
<p>PETG, günlük yıkamaya ve ılık suya giren iç mekan parçalarında ilk tercihimizdir; tok yapılı ve temizliği kolaydır. ASA, açık padokta, çatı altı olmayan sulukta ve dışarıda kalan düzeneklerde kullanılır; güneş altında kırılganlaşmaya PETG'den daha dirençlidir. PA yani naylon — özel talep sınıfı — sürtünen burç, mandal dili ve sık açılıp kapanan menteşe tipi parçalarda tercih edilir. Yük taşıyan tutucu, kolektör askısı ve titreşimli bölgedeki braket gibi işlerde karbon veya cam elyaf takviyeli PA-CF / PA-GF kullanırız; bunlar daha rijittir ve zorlanmada esneyip sürünmez. PLA'yı yalnızca ahır dışında kalan, ısı görmeyen deneme ve şablon işlerinde kullanırız; sağım ortamına önermiyoruz. Sıcak su ve buharla yapılan hat temizliğinde parçanın kaç dereceye çıktığını söylerseniz seçimi ona göre daraltırız; ılık yıkama ile buharlı temizlik arasındaki fark, malzeme kararını tek başına değiştirir. Malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir.</p>
<p>Asitli ve bazlı meme daldırma çözeltileri, yıkama kimyasalı ve yağ temasının olduğu yerlerde seçimi ayrıca daraltırız; ayrıntı için <a href="/yaga-ve-kimyasala-dayanikli-plastik-parca-uretimi/">yağa ve kimyasala dayanıklı plastik parça üretimi</a> sayfasına bakabilirsiniz. Yıl boyu güneşte kalan parçalarda <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneş dayanımlı dış mekan üretimi</a> sayfasındaki notlar geçerlidir.</p>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Standart sınıflarda farklı renk seçenekleri sunuyoruz; renk ayrımı özellikle sağım hattında hangi tutucunun nereye ait olduğunu işaretlemek için işinize yarar.</p>
<h2>Dürüst sınır</h2>
<p>Her parçayı üretemeyiz ve üretemeyeceğimizi baştan söyleriz.</p>
<p>Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; o belgeyi vermiyoruz. Süt yolunun iç yüzeyi tam olarak bu tanıma girer: sürekli sütle temas eden ve her sağımda kimyasalla temizlenen bir hattır, orayı üretmiyoruz. Meme lastiği, silikon manşon, kauçuk körük gibi esnek elemanlar zaten dökümle üretilir; orijinalini kullanın. Hattın dışında kalan, gıdayla ya da içme suyuyla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Bizim alanımız süt yolunun dışındaki mekanik parçalardır: tutucu, askı, klips, burç, kapak ve muhafaza. Vakum hattındaki yüksek basınçlı sızdırmazlık elemanlarına da girmeyiz; ürettiğimiz conta esnek TPU sınıfındadır ve düşük-orta basınç içindir; bu sınıfın ısı bandı yaklaşık 60-80 °C'dir, ASA gibi üst sert sınıfların altında kalır. Metal işleme, talaşlı imalat ve kaynak gerektiren işleri yapmıyoruz; bu tip parçaları uygun atölyeye yönlendiririz. Mili, rulmanı ve metal kelepçeyi siz temin edersiniz; parçayı o elemanların ölçüsüne göre, yuvası ve geçme toleransı dahil kurarız.</p>
<p>Ürettiğimiz parça orijinalin yerine geçen bir yedektir; sağım ünitesinin sertifikalı bir bileşenini değiştirdiğimiz iddiasında değiliz. Hijyen açısından kritik bölgelerde servisinizin görüşünü alın.</p>
<p>Fan tipi parçalarda sınır nettir: havalandırma fanı kanadı ve hafif çark üretilebilir, zorlu itiş uygulamaları için uygun değildir. Profil ve beam işlerinde ürettiğimiz parça hafif ve yük taşımayan yerler içindir; hayvanın ağırlığını taşıyacak bir doğrama parçası bizden çıkmaz. Kilit ve mandal işlerinde de hayvanın zorlayabileceği ana kilidi değil, onun etrafındaki plastik elemanları üretiriz.</p>
<h2>Sipariş</h2>
<p>Ölçüyü ya da kırık parçanın fotoğrafını WhatsApp hattına (+90 545 138 6526) gönderin; malzeme önerisi ve fiyatı size dönelim. Ölçü ve malzeme WhatsApp'ta netleştikten sonra siparişinizi sitede kartla güvenli online ödeme yaparak tamamlarsınız; ürün sayfası olan katalog ve ölçüye özel (parametrik) kalemleri ise doğrudan sepete ekleyip kartla ödeyebilirsiniz. Onaylanan işler 3-5 iş gününde kargoya verilir.</p>
<p>Yanınızda kumpas yoksa endişelenmeyin; parçayı gönderin, ölçüsünü biz alalım. Aynı arızanın tekrarlamasını istemiyorsanız, kırılan parçanın nerede zorlandığını söyleyin: kesit kalınlığını artırarak ya da malzemeyi bir üst sınıfa taşıyarak o noktayı güçlendirmeyi deneriz.</p>""")


def _tekne_tentesi_bimini_guverte_aparati_ozel_uretim():
    return (u"""<h1>Tekne Tentesi ve Bimini Aparatı Özel Üretim</h1>
<p>Bimini ya da tente iskeletinde iş çoğu zaman tek bir küçük parçada durur: bez sağlam, borular sağlam, ama boruyu güverteye ya da birbirine bağlayan plastik aparat kırılmıştır. Sezon ortasında o aparatın yedeğini bulmak kolay değildir; set yıllar önce alınmıştır, üreticisi bilinmez, satılan muadillerin boru çapı veya açısı tutmaz. Biz elinizdeki kırık parçanın ya da ölçünün üzerinden aynı işi gören aparatı yeniden üretiyoruz. Kabin içindeki titreşim ve neme maruz dolap bağlantıları içinse <a href="/tekne-kabin-dolap-mandali-yaptirma/">tekne kabin dolap mandalı üretimi</a> ayrı ölçü ve malzeme kararları ister. <strong>Ölçü sizden, üretim bizden.</strong></p>
<p>Parçanın adını, kodunu veya markasını bilmeniz gerekmez. Kırık parçanın fotoğrafı ve birkaç ölçü çoğu iş için yeterlidir.</p>
<h2>Hangi tente ve güverte parçalarını yeniden üretiyoruz</h2>
<ul>
<li>Bimini borusunu güverteye bağlayan menteşeli taban tutucuları ve kaideleri</li>
<li>Boru uçlarına geçen mafsallı eklem gövdeleri, açılı dirsek ve orta bağlantı parçaları</li>
<li>Tente askı kayışı için kanca, halka, gergi mandalı ve kilit dili</li>
<li>Boru içi ve boru ucu tapaları, açık kalan deliklerin kapak ve rozetleri</li>
<li>Kelepçe yatakları, kayar ray takozları, tente kolunun oturduğu burçlar</li>
<li>Kırılan plastik topuz, kelebek somun ve el sıkma vidası gövdeleri</li>
</ul>
<p>Bunların hepsi ölçüye göre çıkar. Aynı parçadan iki adet de yedeğiyle altı adet de istenebilir; tek adet çıkarmak da çoğaltmak da ayrı bir hazırlık istemez.</p>
<p>Çoğu tekne sahibi bize kırık parçayı iki durumda getiriyor. Birincisi, aparat zaten bir kez kırılmış ve geçici olarak kelepçeyle bağlanmıştır; ikincisi, aparat sağlam ama simetriğindeki kırıldığı için tenteyi tek tarafa yaslamak gerekmiştir. İkisinde de sağlam olan taraf bize ölçü referansı olur: sağlam parçanın fotoğrafı ve ölçüsü üzerinden kırılanın aynısını, istenirse ayna simetriğini çıkarırız. Elinizde hiç parça kalmadıysa boruların üzerindeki oturma izi ve güvertedeki vida delikleri yeterli başlangıçtır.</p>
<h2>Nasıl ölçü veriyorsunuz ve iş nasıl ilerliyor</h2>
<ol>
<li><strong>Fotoğraf gönderin.</strong> Kırık parçayı yanına bir cetvel ya da kumpas koyarak iki üç açıdan çekin. Parça iki parçaya ayrılmışsa ikisini de gösterin.</li>
<li><strong>Kritik ölçüleri yazın.</strong> Tente işinde belirleyici olan ölçüler nettir: geçen borunun dış çapı, aparatın bağlandığı vida deliklerinin merkez arası, güverteye oturan tabanın uzunluk-genişliği ve iki kolun arasındaki açı. Bu dördü çoğu aparat için yeterlidir.</li>
<li><strong>Teyit ederiz.</strong> Ölçüde çelişki varsa ya da parçanın çalıştığı yer daha güçlü bir malzeme istiyorsa size söyleriz. Ne yapacağımızı ve ne yapmayacağımızı baştan yazarız.</li>
<li><strong>Onaydan sonra üretime alırız.</strong> Tente ve bimini aparatlarının çoğu örneğinizden ya da ölçünüzden üretilir; bu parçaların sitede hazır ürün sayfası olmaz, fiyatı WhatsApp hattında belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</li>
<li><strong>Kargoya veririz.</strong> Onaylanan işler <strong>3-5 iş gününde kargoya verilir.</strong></li>
</ol>
<p>Bazı bağlantılar ise sitedeki genel amaçlı ölçüye özel kalemlerle çözülür ve süreç daha kısadır: bağlantı konektörü sayfasında çubuk ya da boru çapı 6-20 mm aralığında, montaj braketi sayfasında kalınlık 3-6 mm, genişlik 20-40 mm, uzunluk 40-120 mm, iç açı 60-120 derece ve delik adedi 1-3 arasında seçilir; bu kalemleri ürün sayfasından malzeme ve ölçü seçip sepete ekler, kartla ödersiniz. Dikkat: bimini borusu çoğunlukla 22-25 mm çapındadır ve konektör sayfasındaki 20 mm tavanın üstünde kalır. Kol sayısı ürün sayfasında 2-4 arasında seçilir; iki kollu düz ek, üç kollu T ve dört kollu X birleşme gövdesi bu aralıktadır. 22-25 mm çapındaki bir eklem, dörtten çok kollu birleşme gövdesi, payandalı ya da sağ-sol simetrik özel braket ürün sayfasından seçilemez; bu işlerde ölçüyü WhatsApp hattına yazın, fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Detay için <a href="/olcuye-ozel-baglanti-konektor/">ölçüye özel bağlantı ve konektör</a> sayfasına, kapatma parçaları için <a href="/olcuye-ozel-tapa-kapak-uretimi/">ölçüye özel tapa ve kapak üretimi</a> sayfasına bakabilirsiniz.</p>
<h2>Doğru malzeme seçimi</h2>
<p>Güvertede duran bir parçanın düşmanı bellidir: güneş, tuz ve sıcakta yumuşama. Malzemeyi buna göre seçeriz.</p>
<ul>
<li><strong>PETG</strong> — kapalı alanda ya da gölgede duran, orta yük taşıyan iç aksam parçaları için tok ve kırılmaya dirençlidir.</li>
<li><strong>ASA</strong> — açık güvertede kalan tente aparatlarında ilk tercihimiz. Güneş altında rengini ve tokluğunu uzun süre korur, dış ortam için tasarlanmış bir malzemedir.</li>
<li><strong>PA (naylon) · özel talep</strong> — sürtünen, geçen, esneyerek çalışan yerlerde: burç, mafsal yatağı, kayar takoz.</li>
<li><strong>PA-CF / PA-GF · özel talep</strong> — karbon ya da cam elyaf takviyeli naylon. Yük alan tutucularda, mafsal gövdelerinde ve gergi altında çalışan parçalarda kullandığımız en sert seçenek.</li>
<li><strong>PLA</strong> — yalnız örnek ve ölçü provası içindir; güvertede kullanılmasını önermeyiz.</li>
</ul>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Standart sınıflarda farklı renk seçenekleri sunuyoruz; beyaz ve siyah gövde renkleri tekne aksamında en çok istenenler. Dış mekân malzemesi seçimini daha ayrıntılı anlattığımız sayfa: <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekân parça üretimi</a>. Yük alan braket ve mesnet tipi bağlantılar için <a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketi</a> sayfasına göz atın.</p>
<h2>Dürüst sınır</h2>
<p>Her parçayı bu yöntemle çözemeyiz; hangisini çözemediğimizi baştan söylemek işinizi hızlandırır.</p>
<ul>
<li><strong>Emniyet ve can yükü taşıyan bağlantı bizim işimiz değildir.</strong> Direk, arma, vinç, halat gerdirme ya da insan ağırlığı taşıyan noktalarda metal parçanın yerini almayız.</li>
<li><strong>Pervane</strong> ancak fan ve hafif çark ölçeğinde üretilir; tekneyi iten pervane değildir.</li>
<li><strong>Profil ve kiriş</strong> parçaları hafif ve yük dışı kullanım içindir; taşıyıcı eleman olarak verilmez.</li>
<li><strong>Conta</strong> esnek TPU sınıfında üretilir, düşük ve orta basınç içindir; yüksek basınç hattına uygun değildir.</li>
<li><strong>Metal işleme, talaşlı imalat, kaynak veya kaplama yapmıyoruz.</strong> Parçanın metal olması şartsa bunu söyler, sizi doğru yere yönlendiririz. Paslanmaz vida ve cıvatayı siz temin edersiniz; aparatı o elemanların ölçüsüne göre, somun yatağı dahil kurarız.</li>
<li>Sıcak egzoz hattına yakın ve sürekli yüksek sıcaklıkta duran parçaları da almayız. Malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir.</li>
</ul>
<h2>Sipariş</h2>
<p>Kırık aparatın fotoğrafını, ölçülerini ve nereye takılacağını <strong>+90 545 138 6526</strong> numarasına gönderin; ne yapılabileceğini ve hangi malzemeye gideceğini yazalım. Fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Ürün sayfası olan ölçüye özel kalemleri ise doğrudan sepete ekleyip kartla ödeyebilirsiniz. Onaylanan işler 3-5 iş gününde kargoya verilir.</p>""")


def _yedek_parca_kodu_bilinmiyorsa_ne_yapilir():
    return (u"""<h1>Yedek Parça Kodu Bilinmiyorsa Ne Yapılır?</h1>
<p>Kırılan parçanın üzerinde numara yok, cihazın etiketi silinmiş, üretici de o modeli yıllar önce bırakmış. Bu, parçanın bulunamayacağı anlamına gelmez; yalnızca arama yönteminiz değişir. Kod bir kısayoldur, zorunluluk değil. Kodun yerini tutan tek şey ölçüdür: doğru ölçülmüş bir parçanın eşi, kataloğu kalmamış bir cihaz için bile üretilebilir. Ölçü sizden, üretim bizden.</p>
<p>Bu sayfada önce kodu bulma ihtimalinizi sonuna kadar kullanıyoruz; kod hiç çıkmazsa ölçüyle nasıl ilerleyeceğinizi adım adım anlatıyoruz.</p>
<h2>Kod nerede saklanır, aramayı erken bırakmayın</h2>
<p>Kodu bulabilirseniz işiniz kolaylaşır, çünkü kod cihazın hangi seriye ait olduğunu da söyler. Şu beş yere bakın:</p>
<ul>
<li><strong>Cihazın arka veya alt yüzeyi.</strong> Buzdolabı, çamaşır makinesi, klima ve fırınlarda model ile seri numarası genellikle burada bir etikettedir.</li>
<li><strong>Kapak içi ve çekmece boşluğu.</strong> Çamaşır makinelerinde kapak kasnağının içi, fırınlarda alt çekmece, oto parçalarında torpido kapağı sık kullanılan yerlerdir.</li>
<li><strong>Parçanın kendi üzerindeki kabartma rakamlar.</strong> Plastik parçalarda çoğu zaman küçük bir kabartma numara ve üretim tarihi bulunur. Silinmişse eğik ışık tutup fotoğraf çekin, rakamlar gölgede belirir.</li>
<li><strong>Kılavuz, fatura, garanti belgesi.</strong> Servis kaydınız varsa çağrı numarasıyla birlikte model bilgisi de yazılıdır.</li>
<li><strong>Enerji etiketi.</strong> Beyaz eşyada ürün adı ve model kodu bu etikette de geçer.</li>
</ul>
<p>Bir de arama tarafında sık yapılan hata var: insanlar cihazın ticari adını aratıyor, oysa yedek parça listeleri model kodu üzerinden düzenlenir. Etikette birden fazla numara varsa hepsini not edin; bunlardan biri model, biri seri numarası, biri de servis kodudur. Yine de bazı cihazlarda üretici kodu hiç vermemiştir ya da parça tek başına satılmamıştır. Böyle durumlarda kod aramak zaman kaybıdır, doğrudan ölçüye geçin.</p>
<p>Kodu buldunuz ama parça yine de piyasada yoksa durum değişmez: yine ölçüyle ilerleriz. Bu senaryoyu ayrıca <a href="/piyasada-bulunmayan-yedek-parca-uretimi/">piyasada bulunmayan yedek parça üretimi</a> sayfasında anlattık.</p>
<h2>Nasıl ilerlersiniz: koddan değil ölçüden başlamak</h2>
<p><strong>1. Kırık parçaları atmayın.</strong> İki üç parçaya ayrılmış bir parça bile ölçü için yeterlidir; parçaları bantla birleştirmek çoğu zaman tam geometriyi geri verir. Eksik köşe varsa sorun değil, karşı yüzeyden simetriyi çıkarırız.</p>
<p><strong>2. Fotoğrafları doğru çekin.</strong> Parçanın üst, alt ve iki yan görünüşünü, düz bir zeminde, yanında bir cetvel olacak şekilde çekin. Cetvel ölçeği doğrular ve tahmini ortadan kaldırır. Parçanın söküldüğü yeri de bir kare fotoğraflayın; oturduğu yuva çoğu zaman ölçüden daha çok şey anlatır.</p>
<p><strong>3. Kritik ölçüleri alın.</strong> Kumpas varsa kumpasla, yoksa cetvelle milimetre cinsinden not edin: dış ölçü veya dış çap, iç delik veya mil çapı, kalınlık, delik merkezleri arası mesafe, vida çapı ve adımı, varsa diş sayısı. Milin köşeli veya kamalı olması, deliğin havşalı olması gibi ayrıntıları yazıyla ekleyin. Ölçü almanın tüm ayrıntısı için <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">ölçü alma ve gönderme rehberimiz</a> yeterlidir.</p>
<p><strong>4. Parçanın görevini anlatın.</strong> Yük taşıyor mu, dönüyor mu, sıcak bir yüzeye mi değiyor, dışarıda güneş görüyor mu, suyla teması var mı? Bu birkaç cümle malzeme seçimini belirler ve yanlış malzemeden dolayı ikinci kez kırılmayı engeller.</p>
<p><strong>5. Gönderin ve teyitleşin.</strong> Fotoğrafları ve ölçüleri WhatsApp hattımıza iletin. Ölçüleri okur, eksik veya çelişkili gördüğümüz yeri sorar, üretilecek geometriyi size yazılı olarak teyit ederiz. Onayınız olmadan üretime geçmeyiz.</p>
<p>Parçayı elden veya kargoyla bize ulaştırmak isterseniz de olur; <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre üretim</a> yolunda ölçüyü biz alırız, siz hiç ölçmezsiniz. Kırık parça hiç kalmadıysa, yalnızca oturduğu yuvanın ölçüleriyle de ilerleyebiliriz; bu yöntemi <a href="/bulunamayan-yedek-parca-ozel-uretim/">bulunamayan yedek parça özel üretimi</a> sayfasında bulursunuz. Fiziksel örneğin tamamen kayıp olduğu durumlarda gereken fotoğraf ve karşı parça bilgilerini <a href="/numune-olmadan-plastik-parca-yaptirilir-mi/">numune olmadan plastik parça yaptırma</a> rehberinde topladık.</p>
<h2>Doğru malzeme</h2>
<p>Kodu bilinmeyen bir parçanın orijinali hangi malzemedendi, çoğu zaman bilinmez. Biz malzemeyi parçanın çalıştığı yere göre seçeriz:</p>
<ul>
<li><strong>PLA</strong> — yalnızca yük almayan, ısınmayan, kapalı ortamdaki parçalar; kapak, tutamak, kılavuz gibi.</li>
<li><strong>PETG</strong> — genel amaçlı dayanım ve tokluk; ev aletlerinin çoğu iç parçası, muhafazalar, kelepçeler.</li>
<li><strong>ASA</strong> — dışarıda kalan, güneş ve hava koşulu gören parçalar; renk ve yüzey açık havada uzun süre korunur.</li>
<li><strong>TPU (esnek)</strong> — conta, tampon, esneyerek geçen tutucu gibi yumuşak sınıf işleri.</li>
<li><strong>PA (naylon) · özel talep</strong> — sürtünen, kayan, aşınan parçalar; kızak, burç, dişli, makara.</li>
<li><strong>PA-CF / PA-GF (karbon veya cam fiber takviyeli naylon) · özel talep</strong> — yüksek mukavemet, rijitlik ve ölçü kararlılığı gereken braket ve bağlantı parçaları; ısı dayanımını takviye değil taşıyıcı malzeme belirler.</li>
</ul>
<p>Naylon (PA) ve takviyeli sınıf (PA-CF / PA-GF) sitedeki hazır seçenekler arasında yer almaz; özel talep olarak değerlendirilir. Parçanın fotoğrafını, ölçülerini ve nereye takılacağını WhatsApp'tan +90 545 138 6526 numarasına yazın; uygun sınıfı ve fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız.</p>
<p>Standart sınıflarda farklı renk seçenekleri sunarız; rengi baştan söylemeniz yeterli.</p>
<h2>Dürüst sınır</h2>
<p>Her parça bu yöntemle üretilmez, bunu baştan söyleriz:</p>
<ul>
<li><strong>Pervane</strong> dediğimizde fan kanadı ve hafif çarkı kastediyoruz; tekneyi iten pervane bu kapsamda değildir.</li>
<li><strong>Profil ve taşıyıcı kiriş</strong> benzeri parçaları yalnızca hafif ve yük dışı kullanım için üretiriz; ana taşıyıcı eleman olarak öneremeyiz.</li>
<li><strong>Conta</strong> üretimimiz esnek TPU sınıfındadır ve düşük-orta basınç içindir; yüksek basınçlı hat ve buhar hattı bizim sınırımızın dışındadır.</li>
<li>Metal parça üretimi, talaşlı imalat, döküm veya kaplama işleri yapmayız. Parçanız gerçekten metal olmak zorundaysa bunu söyler, sizi doğru yere yönlendiririz. Mil, rulman, yaylı pim ve metal vida gibi elemanları siz temin edersiniz; biz parçayı o standart elemanın ölçüsüne göre — yuvası, geçme toleransı ve somun yatağı dahil — tasarlar ve üretiriz.</li>
</ul>
<p>Bu sınırları peşinen söylememizin sebebi basit: yerine oturmayan parça, hiç üretilmemiş parçadan daha pahalıya gelir. Ölçü ve görev bilgisi elimize geldiğinde, parçanın bu yöntemle sağlıklı çalışıp çalışmayacağını üretimden önce söyleriz.</p>
<h2>Sipariş</h2>
<p>Fotoğraf ve ölçüleri WhatsApp hattımıza gönderin: <strong>+90 545 138 6526</strong>. Ölçüyü teyit ettikten sonra üretim onayınızı alırız; fiyatı belirledikten sonra siparişinizi kartla online ödeyerek tamamlarsınız. Sitede ürün sayfası olan katalog ve ölçüye özel (parametrik) kalemlerde ise ürün sayfasından malzeme, renk ve ölçü seçip sepete ekler, doğrudan kartla ödersiniz. Üretilen parça 3-5 iş gününde kargoya verilir.</p>
<p>Elinizde yalnızca kırık bir parça ve bir cetvel olması yeterli. Kod olmadan da doğru parçaya ulaşılır.</p>""")


# build.py'nin ÜRETTİĞİ yeni sayfalar (hakkimizda/iletisim/sss/gizlilik zaten
# elle yapılmış statik dosya olarak repo'da; onlar üretilmez, korunur).
# slug -> (başlık, meta açıklama, gövde fonksiyonu)

def _olcuye_ozel_seviye_simi_ve_takoz_uretimi():
    return (u"""<h1>Ölçüye Özel Seviye Şimi ve Takoz Üretimi</h1>
<p>Bir makine ayağı zemine tam oturmadığında, dolap sallandığında ya da bir parçanın belirli açıyla yükselmesi gerektiğinde aranan şey çoğu zaman standart bir pul değil, eğimli bir şimdir. Hazır takozun eni, boyu veya yüksekliği uymadığında küçük fark bütün düzeni bozar. Ölçüye özel seviye şimi ve takozu; oturacağı alanı, gereken yükseltiyi ve yüzey davranışını dikkate alarak üretiyoruz. Amaç boşluğu rastgele doldurmak değil, parçayı belirlenen konumda kararlı tutmaktır.</p>
<p>Bu sayfa eğimli seviyeleme parçasına odaklanır. Düz ve eksenel mesafe ayarı için <a href="/olcuye-ozel-distans-ara-pul-uretimi/">ölçüye özel distans ve ara pul</a>, hareketi sonlandıran küçük parçalar için <a href="/plastik-stoper-durdurucu-yaptirma/">plastik stoper ve durdurucu</a> sayfası daha doğru başlangıçtır.</p>
<h2>Hangi işlerde kullanılır</h2>
<p>Seviye şimi; masa ve dolap ayağındaki küçük kot farkını almak, yük taşımayan bir muhafazayı hizalamak, cihaz altındaki boşluğu kapatmak veya bir kapağa kontrollü eğim vermek için kullanılabilir. Rampa biçimi kablo geçişinde, düşük kotlu eşiklerde ve atölye düzeneklerinde yönlendirme sağlayabilir. Üst yüzey düz, basamaklı ya da tutunmayı artıran tırtıklı olabilir. Parçanın eni, boyu, yüksekliği ve eğimin hangi yöntemle tanımlanacağı sipariş sırasında seçilir.</p>
<p>Şim ile takoz aynı şey değildir. Şim çoğunlukla ince bir ayar parçasıdır; takoz daha belirgin bir yükseltme ya da dayama görevi görür. Rampa ise iki kot arasında geçiş kurar. Kullanım amacını doğru yazmanız, yalnız ölçüyü değil yüzey biçimini de doğru seçmemizi sağlar. Zeminin sert, pürüzlü veya nemli olması da malzeme kararını değiştirir.</p>
<h2>Nasıl ölçülür ve seçim yapılır</h2>
<p>Önce parçanın oturacağı boşluğun enini ve boyunu ölçün. Sonra ince uç ile kalın uç arasındaki yükseklik farkını belirleyin. Açı biliniyorsa açıyla, bilinmiyorsa doğrudan yükseklikle ilerlenebilir. Alt yüzeyin düz mü, bir ayağı kavrayacak yuvalı mı olması gerektiğini fotoğrafla gösterin. Üst yüzeyde kaymayı azaltmak istiyorsanız bunu seçimde belirtin; tırtıklı yüzey, tek başına emniyet bağlantısı değildir.</p>
<p>Ölçüde tereddüt varsa <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü alma rehberi</a> ile en, boy, yükseklik ve temas yüzeyini kontrol edin. Bir cetvelle genel ölçü, kumpasla kritik kalınlık alınması yeterlidir. Zemindeki eğim düzensizse tek bir noktadan değil, iki uçtan ölçü verin. Sağ ve sol için farklı takoz gerekiyorsa her konumu ayrı adlandırın.</p>
<p>Bu kalemin sitede konfigüratörlü ürün sayfası bulunur. Sayfadaki gerçek seçenekler içinde ölçüleri, eğim yöntemini ve üst yüzeyi belirleyebilir; malzeme ile rengi seçip Sepete Ekle üzerinden kartla ödeyebilirsiniz. Ürün sayfasında bulunmayan bir geometri, taşıma cebi veya ölçü gerekiyorsa fotoğrafı ve kullanım yerini WhatsApp'tan iletin; fiyat netleştikten sonra kartla online ödeme yapılır.</p>
<h2>Uygulama öncesi kontrol</h2>
<p>Takozu yerleştirmeden önce zeminin temiz ve sabit olduğundan emin olun. Gevşek taş, yağ veya talaş üzerinde doğru ölçü bile kararlı durmaz. Parçanın ince ucunu boşluğa zorlayarak sokmak yerine yükseltiyi ölçüp ona göre seçim yapmak gerekir. İki takoz üst üste kullanılacaksa kayma ihtimali artar; tek parçada doğru yüksekliğe gitmek daha sağlıklıdır.</p>
<p>Birden çok ayağı olan cihazlarda yalnız sorunlu köşeyi ölçmek yetmez. Diğer ayakların zemine temasını ve gövdenin terazisini birlikte kontrol edin. Takozdan sonra kapak, mil veya ray hizası değişiyorsa asıl sorun şasi eğriliği olabilir. Üretilen parçanın işi mevcut düzeni güvenli aralıkta hizalamaktır; yapısal arızayı örtmek değildir.</p>
<p>Bakım sırasında takozun yerinden çıkmaması için montaj biçimini baştan belirleyin. Sıkıştırma, vida ile konumlandırma veya bir yuvaya oturma seçenekleri farklı ölçü ister. Vida kullanılacaksa deliğin yeri ve baş biçimi fotoğrafta gösterilmelidir. Nemli zeminde suyun altında birikmemesi için yüzey ve kenar düzeni ayrıca konuşulur. Böylece yalnız ilk gün oturan değil, kullanım sırasında konumunu koruyan bir parça elde edilir.</p>
<h2>Doğru malzeme</h2>
<p>PLA, kuru iç mekânda yük almayan bir hizalama parçası için ekonomik seçimdir. PETG, atölye nemi ve günlük darbeler karşısında daha tok davranır. ASA, güneş gören dış ortamda tercih edilir. TPU sitedeki malzeme seçicide yer alır; titreşimi azaltması veya yüzeye daha yumuşak oturması istenen takozlarda önce bu esnek sınıf değerlendirilir. PA ve PA-CF ya da PA-GF, daha rijit ve aşınmaya dirençli özel işler için WhatsApp üzerinden değerlendirilir; ürün sayfasında seçilmez.</p>
<p>Malzemenin sertliği tek başına yeterli değildir. Takozun altında oluşacak kuvvet, temas alanı ve kenarların zemine nasıl oturduğu birlikte değerlendirilir. Küçük bir ayak üzerine yüksek kuvvet biniyorsa kesit ezilebilir; daha geniş taban veya uygun bir endüstriyel seviye elemanı gerekebilir.</p>
<h2>Dürüst sınır</h2>
<p>Bu parça bina, araç kaldırma düzeneği, insan taşıyan platform veya emniyet kritik makine için taşıyıcı kama değildir. Ağır yükün altında hesap gerektiren şim ve takozlar bizim alanımız değildir. Üretilebilir parça, hafif ve orta görevli seviyeleme ile konumlandırma içindir. Daha geniş sınır listesi için <a href="/hangi-parcalar-ozel-uretimle-yapilamaz/">hangi parçalar özel üretimle yapılamaz</a> rehberine bakın.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Ürün sayfasındaki seçenekler ihtiyacınızı karşılıyorsa ölçü, yüzey, malzeme ve rengi seçin; Sepete Ekle ile kartla ödeyin. Aralık dışı veya farklı taban geometrisi gereken işlerde +90 545 138 6526 üzerinden fotoğraf, ölçü ve montaj yerini gönderin. Tekliften sonra kartla online ödeme yapabilirsiniz. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _olcuye_ozel_kramayer_disli_uretimi():
    return (u"""<h1>Ölçüye Özel Kramayer Dişli Üretimi</h1>
<p>Döner hareketi düz bir eksende ilerlemeye çevirmek için kullanılan kramayer, karşısındaki pinyonla aynı diş geometrisini paylaşmak zorundadır. Boyu benzer görünen iki parça, modülü veya diş aralığı farklıysa birlikte çalışmaz. Kırılmış bir kramayeri yalnız dış ölçüsüne bakarak çoğaltmak bu yüzden yeterli değildir. Biz kramayeri; karşı dişlinin bilgisi, diş yönü, montaj boyu ve çalışma boşluğuyla birlikte değerlendirerek ölçüye özel üretiyoruz.</p>
<p>Genel döner dişli ihtiyacı için <a href="/olcuye-ozel-plastik-disli-uretimi/">ölçüye özel plastik dişli</a> sayfası uygundur. Bu sayfa yalnız doğrusal hareket üreten kramayerin ölçümüne, uyumuna ve sınırlarına odaklanır.</p>
<h2>Kramayerde hangi bilgiler gerekir</h2>
<p>İlk bilgi modüldür. Modül, dişin büyüklüğünü belirler ve karşı dişliyle birebir eşleşmelidir. Kırık parçanın sağlam bölümünde birkaç diş kalmışsa diş aralığı, toplam yükseklik ve kalınlık ölçülebilir. Karşı pinyon elinizdeyse onun diş sayısı ve dış çapı da kontrol kaynağı olur. Modülü nasıl çıkaracağınızı <a href="/kirik-dislinin-modulu-nasil-bulunur/">kırık dişlinin modülünü bulma rehberi</a> adım adım anlatır.</p>
<p>Montaj boyu ikinci kritik bilgidir. Kramayerin yalnız dişli kısmı değil, vida delikleri, başlangıç ve bitiş payı, arka yüz kalınlığı ve varsa kılavuz omuzları da ölçülür. Birden fazla parçanın uç uca geleceği sistemlerde diş fazının devam etmesi gerekir; iki parçayı gelişigüzel yan yana koymak geçişte takılmaya yol açabilir. Hareket yönünü ve pinyonun hangi taraftan temas ettiğini fotoğrafla göstermeniz bu hatayı önler.</p>
<h2>Nasıl ilerler ve uyumu kontrol ederiz</h2>
<p>Kırık kramayeri düz bir zeminde, cetvel yanında ve iki yüzden fotoğraflayın. Karşı pinyonu, montaj kanalını ve vida noktalarını ayrıca gösterin. Ölçü listesine toplam boy, gövde kalınlığı, dişli kısmın yüksekliği, delik merkezleri ve karşı dişli bilgisini ekleyin. Eksik dişler varsa sağlam bölümden tekrar eden geometrinin devamı çıkarılabilir.</p>
<p>Sitedeki konfigüratörlü dişli ürün sayfasında kramayer tipi gerçek seçeneklerden biridir. Sayfada kramayer tipini, desteklenen modülü, diş sayısını ve kalınlığı seçip malzeme ile rengi belirleyebilir, Sepete Ekle üzerinden kartla ödeyebilirsiniz. Montaj deliği, özel boy, bağlantı geometrisi veya sayfadaki aralıkların dışında bir ölçü gerekiyorsa fotoğraf ve karşı parça bilgisi WhatsApp'tan değerlendirilir; fiyat netleştikten sonra kartla online ödeme yapılır.</p>
<p>İlk parçayı mekanizmada elle ve yüksüz deneyin. Dişler rahatça kavramalı, fakat belirgin yan boşlukla vuruntu yapmamalıdır. Kramayer kanal içinde sıkışıyorsa sorun her zaman dişte değildir; ray paralelliği, pinyon ekseni veya montaj vidasının gövdeyi eğmesi de etkili olabilir. Genel makine parçası değerlendirmesi için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfasına bakabilirsiniz.</p>
<h2>Devreye almadan önce kontrol</h2>
<p>Kramayerin doğru görünmesi tek başına yeterli değildir. Pinyonla temas çizgisi boyunca hareketin tamamı elle çevrilerek denenmelidir. Başlangıçta rahat, ortada sıkı bir bölge varsa ray doğruluğu veya montaj yüzeyi kontrol edilir. Vidalardan biri fazla sıkıldığında uzun gövde hafifçe eğilebilir ve diş boşluğu değişebilir. Bu nedenle montaj vidaları kademeli sıkılır, her adımda hareket yeniden denenir.</p>
<p>Kramayer birden fazla parçadan oluşuyorsa birleşim noktasında pinyonun takılmaması gerekir. Uçların konumu, diş devamı ve aradaki boşluk aynı anda ayarlanır. Yük yönü tersine dönen sistemlerde geri boşluk daha görünür hâle gelir; uygulamanın hassasiyet beklentisini baştan yazın. Bir gösterge sürgüsü ile kuvvet aktaran kapak aynı toleransı istemez.</p>
<p>Bakım düzeni de önemlidir. Ortam tozluysa diş aralarındaki birikinti aşınmayı hızlandırabilir. Parçayı temizlerken kullanılacak maddeyi ve varsa yağlayıcıyı söyleyin; kimyasal uyum malzeme seçimini etkiler. İlk denemeyi koruma kapağı açıkken yalnız güvenli ve enerjisiz koşulda yapmak, temas izini gözle değerlendirmeyi kolaylaştırır. Uygun olmayan kavramada sistemi zorlamayın; ölçü düzeltmesi yapılmalıdır.</p>
<h2>Doğru malzeme</h2>
<p>PLA yalnız ölçü ve kavrama provasında kullanılabilir. PETG, düşük hız ve düşük yükte tok bir genel seçenek sunar. PA, sürtünme ve aşınma bulunan hareket sistemlerinde özel talep olarak öne çıkar. PA-CF ve PA-GF, daha rijit gövde gereken işlerde değerlendirilir; ancak her takviyeli sınıf darbe için doğru değildir. Aşınma davranışını <a href="/asinmaya-dayanikli-surtunme-parcasi-uretimi/">aşınmaya dayanıklı sürtünme parçası</a> sayfasında ayrıntılı anlattık.</p>
<p>Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU yer alır. TPU seçilebilir olsa da diş formunu yük altında koruması gereken kramayer için ilk tercih değildir. PA ve takviyeli sınıflar ürün sayfasında seçilmez; çalışma koşulu WhatsApp'ta değerlendirilir.</p>
<h2>Dürüst sınır</h2>
<p>Kramayeri düşük ve orta yükte konumlandırma, kapak hareketi, gösterge veya hafif otomasyon için üretebiliriz. İnsan taşıyan kapı, kaldırma sistemi, fren, direksiyon ya da emniyet kilidi gibi arıza halinde zarar doğuran mekanizmalara parça vermeyiz. Yüksek hız, sürekli yüksek tork ve yağlama hesabı gerektiren endüstriyel aktarma organları uygun metal sistemlerin alanıdır.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Ürün sayfasındaki gerçek aralıkta bir kramayer için tip, ölçü, malzeme ve rengi seçip Sepete Ekle ile kartla ödeyin. Aralık dışı veya eşleşmesi özel olan işlerde +90 545 138 6526 numarasına kramayeri, karşı dişliyi, ölçüleri ve montaj yerini gönderin. Fiyat netleştikten sonra kartla online ödeme yapabilirsiniz. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _paketleme_makinesi_plastik_yedek_parca_yaptirma():
    return (u"""<h1>Paketleme Makinesi Plastik Yedek Parçası</h1>
<p>Paketleme hattı bazen büyük bir arızadan değil, filmi yönlendiren küçük bir kılavuzun, koruma kapağı tırnağının veya ayar düğmesinin kırılmasından durur. Makinenin modeli eskiyse bu parça tek başına satılmaz; komple modül beklemek üretim kaybını büyütür. Elinizde kırık örnek, sağlam eş parça veya montaj ölçüleri varsa yük taşımayan plastik yardımcı parçayı aynı göreve göre yeniden tasarlar ve ölçüye özel üretiriz.</p>
<p>Bu sayfa genel makine parçası hizmetinin paketleme hattına özgü bölümüdür. Diğer sektörlerdeki dişli, burç ve muhafazalar için <a href="/makine-parcasi-olcuye-ozel-uretim/">makine parçası ölçüye özel üretim</a> sayfası daha geniş çerçeve sunar.</p>
<h2>Hangi parçalar değerlendirilebilir</h2>
<p>Film ve etiket yolundaki düşük yükte çalışan kılavuzlar, kablo tutucular, sensör muhafazaları, ayar topuzları, hafif makaraların yan kapakları, koruma paneli klipsleri, konum göstergeleri ve kutu yönlendirme parçaları uygun adaylardır. Kayış muhafazası, kablo kanalı ağzı ve düğme gövdesi de örnekten çıkarılabilir. Parçanın ambalaja dokunup dokunmadığını, sıcak çene veya rezistansa yakınlığını ve temizlik kimyasalı görüp görmediğini baştan söyleyin.</p>
<p>Kayışlı aktarmada profil bilgisi önemlidir. Diş aralığı bilinmiyorsa <a href="/kayis-profili-nasil-belirlenir-gt2-htd-t5/">kayış profilini belirleme rehberi</a> ile mevcut kayışı ve kasnağı kontrol edin. Motor ile pompa veya redüktör arasında esnek bir bağlantı varsa konu kılavuz değil kaplin olabilir; bu durumda <a href="/plastik-kaplin-gobegi-esnek-kavrama-uretimi/">esnek kaplin göbeği</a> sayfasındaki ölçü listesi kullanılmalıdır.</p>
<h2>Nasıl ölçü gönderilir ve tasarım netleşir</h2>
<p>Parçayı sökebiliyorsanız üst, alt ve yan görünüşlerini cetvel yanında fotoğraflayın. Kırık parçaları bir araya getirin, fakat yapıştırmadan önce birleşim yüzeyini de çekin. Dış ölçü, kalınlık, delik çapı, delik merkezleri, mil veya ray ölçüsü ve hareket yönü temel bilgilerdir. Parçanın makine üzerindeki yerini gösteren geniş bir fotoğraf, tek başına parça görüntüsünden daha değerlidir.</p>
<p>Sağlam bir eş parça varsa sağ-sol simetriyi belirtin. Aynı parça hattın başka istasyonunda çalışıyorsa oradaki örnek ölçü için kullanılabilir. Aşınan yüzeyin başlangıç biçimi kaybolmuşsa karşı parçanın izi ve çalışma boşluğu birlikte incelenir. Parçanın saniyede kaç kez hareket ettiğini, yükü ve temizlik düzenini bilmek malzeme kararını değiştirir.</p>
<p>Bu parçalar için hazır ürün sayfası yoktur. Fotoğraf, ölçü ve montaj yerini WhatsApp'tan gönderirsiniz; yapılabilirlik ve malzeme netleşir, fiyat verilir, ardından kartla online ödeme yaparsınız. Sitedeki katalog ürünlerinden bir dişli, kasnak veya standart ölçüye özel kalem ihtiyacı karşılıyorsa yalnız o ürünün sayfasından seçenekleri belirleyip Sepete Ekle ile ödeme yapılır.</p>
<h2>Hattı durduran sorunu doğru ayırın</h2>
<p>Paket düzgün ilerlemiyorsa sorun her zaman kılavuz parçada değildir. Film gerginliği, sensör hizası, kirlenmiş makara veya gevşek bağlantı aynı belirtiyi verebilir. Kırılan parçanın hemen öncesinde ve sonrasında ne olduğunu anlatın: paket yana mı kaçtı, kapak mı açıldı, kayış mı sıyırdı, sensör mü konum değiştirdi? Bu bilgi tasarımın yalnız şekle değil gerçek göreve göre kurulmasını sağlar.</p>
<p>Aynı parça tekrar kırıldıysa kırılma yüzeyi önemli kanıttır. Vida çevresinde çatlak varsa sıkma kuvveti, ince boyunda kırık varsa kesit ve yük yönü, sürtünen yüzde aşınma varsa boşluk değerlendirilir. Eski geometrinin aynısını koşulsuz çoğaltmak yerine, montajı değiştirmeden kesit geçişini yumuşatmak veya uygun malzemeye geçmek gerekebilir. Değişiklik, karşı parçaya çarpma ya da emniyet mesafesini bozma ihtimali açısından kontrol edilir.</p>
<p>Birden çok adet istendiğinde önce tek örnekle mekanik prova yapmak daha güvenlidir. Örnek; makine enerjisizken yerine oturma, elle hareket ve kapak kapanma kontrolünden geçirilir. İşlev doğrulandıktan sonra aynı geometri çoğaltılır. Böylece ölçü hatasının bütün adede taşınması önlenir. Seri üretim kalıbı sunmuyoruz; ihtiyaca göre tek adet ve düşük adetli özel üretim yapıyoruz.</p>
<p>Kontrol notuna parçanın hangi vardiyada, hangi hızda ve hangi ürünle çalıştığını da ekleyin. Aynı makine farklı paket ölçüsünde başka kuvvet görebilir. Söküm sırasında kullanılan ara pul ve vidaları ayrı saklayın; montaj dizilimi değişirse doğru üretilmiş parça bile eğri oturabilir. Prova sonucunu fotoğrafla kaydetmek sonraki adetler için güvenilir referans oluşturur.</p>
<h2>Doğru malzeme</h2>
<p>PETG, koruma kapağı, sensör tutucu ve genel kılavuzlarda tok bir başlangıçtır. ASA, güneş gören veya dış ortamla bağlantılı hattın parçalarında kullanılır. TPU; titreşimi sönümleyen tampon, esnek temas pabucu olmayan yumuşak temas parçası ve koruyucu ara elemanlarda önce değerlendirilir. Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU vardır. PA, kayan kılavuz ve burçta; PA-CF veya PA-GF ise rijitlik gereken özel parçada WhatsApp üzerinden değerlendirilir.</p>
<p>Takviyeli sınıf her zaman daha iyi değildir. Esneyerek çalışan klipste gevrek davranabilir; rijit bir mesnette ise ölçü kararlılığı sağlayabilir. Karar ölçütlerini <a href="/karbon-fiber-takviyeli-naylon-parca-ne-zaman-gerekir/">takviyeli naylon ne zaman gerekir</a> rehberinde bulabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Koruyucu kapak açıkken makinenin çalışmasına izin veren emniyet anahtarı, acil durdurma sistemi, kesici bıçak, ısıtıcı çene, yüksek hızlı ana aktarma ve operatörü koruyan güvenlik elemanları bizim işimiz değildir. Ürettiğimiz parça yardımcı, düşük ve orta görevli plastik parçadır; makinenin güvenlik devresinin yerine geçmez.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Kırık parçayı, montaj yerini ve ölçü listesini +90 545 138 6526 numarasına gönderin. Bu konu için hazır ürün sayfası olmadığı için önce yapılabilirlik ve fiyat netleşir; sonra kartla online ödeme yaparsınız. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _tarimsal_sulama_ekipmani_plastik_parca_yaptirma():
    return (u"""<h1>Tarımsal Sulama Ekipmanı Plastik Parçası</h1>
<p>Sulama düzeninde küçük bir tutucu kırıldığında bütün hat çalışıyor görünse bile hortum yerinden çıkar, filtre kapağı sabitlenmez veya vana kolu çevrilemez. Hazır parçanın çapı uymadığında bant ve tel geçici çözüm olur; güneş ve su altında kısa sürede gevşer. Basıncı taşımayan kelepçe, kol, kapak tutucu ve yönlendirme parçalarını örneğe veya montaj ölçüsüne göre özel üretiyoruz.</p>
<p>Traktör, çapa ve bahçe makinesinin gövde parçaları için <a href="/tarim-makinesi-plastik-parca-uretimi/">tarım makinesi plastik parça üretimi</a> sayfası uygundur. Buradaki konu sulama hattının yardımcı plastik aksamıdır; borunun veya basınçlı bağlantının kendisi değildir.</p>
<h2>Hangi sulama parçaları uygun adaydır</h2>
<p>Hortumu çerçeveye sabitleyen açık kelepçeler, damlama hattını düzenleyen kılavuzlar, vana kolunun plastik tutamağı, filtre gövdesinin yük taşımayan dış kapağı, sensör muhafazası, kablo tutucu, makara yanlığı ve güneşten kırılan gösterge çerçevesi değerlendirilebilir. Standart bir kelepçe ölçüsü ihtiyacı karşılıyorsa <a href="/olcuye-ozel-klips-kelepce-uretimi/">ölçüye özel klips ve kelepçe</a> ürününden doğrudan seçim yapılabilir.</p>
<p>Parçanın suyla temas etmesi tek başına sorun değildir; belirleyici olan basınç, kimyasal, güneş ve sıcaklıktır. Gübreli su, temizlik maddesi veya tarım ilacı gören yüzeyi ayrıca belirtin. Sürekli basınç altında kalan gövde, vana içi, pompa çarkı veya sızdırmazlık elemanı yardımcı parça sayılmaz ve bu kapsamda değerlendirilmez.</p>
<h2>Nasıl ölçülür ve fotoğraflanır</h2>
<p>Kelepçe için kavranacak borunun dış çapını, kelepçenin genişliğini, vida deliğini ve kapanma biçimini ölçün. Vana kolu için mil kesitini, kol boyunu ve durma açılarını gösterin. Kapak tutucusunda karşılık tırnağını, menteşe noktasını ve oturma yüzeyini fotoğraflayın. Kırık parça kayıpsa montaj yerinin karşılıklı ölçülerini ve sağlam benzerini kullanın.</p>
<p>Fotoğrafları kuru ve temiz parçayla, cetvel yanında çekin. Sistemin genel görünüşünü de ekleyin; parçanın taşıdığı kuvveti ancak yerine bakınca doğru yorumlayabiliriz. Dış ortamda kalma süresi, doğrudan güneş, don, titreşim ve kimyasal teması kısa not olarak yazın. Aynı ölçüde birkaç hat varsa adet bilgisini en başta vermeniz tasarım kontrolünü kolaylaştırır.</p>
<p>Bu başlıktaki özel parçalar için hazır ürün sayfası yoktur. Fotoğraf, ölçü ve montaj yerini WhatsApp'tan gönderirsiniz; yapılabilirlik ve fiyat netleşince kartla online ödeme yaparsınız. Sitede ürün sayfası olan kelepçe gibi ölçüye özel bir kalem gerçek seçenekleri karşılıyorsa malzeme ve rengi seçer, Sepete Ekle üzerinden doğrudan kartla ödersiniz.</p>
<h2>Sahada dayanımı artıran ayrıntılar</h2>
<p>Dış ortam parçasında yalnız malzeme adı değil, suyun nerede biriktiği ve kuvvetin hangi yönden geldiği de önemlidir. Kelepçenin keskin köşesi hortumu aşındırabilir; kapak üzerindeki su cebi don olduğunda genişleyip parçayı çatlatabilir. Fotoğrafta akış yönünü, parçanın yatay ya da düşey durduğunu ve yağmurdan sonra su tutan bölgeleri gösterin. Kenarları yumuşatmak ve suyun kaçacağı yol bırakmak kullanım ömrünü artırabilir.</p>
<p>Güneş alan hatta renk ve yüzey sıcaklığı da dikkate alınır. Koyu yüzeyler doğrudan güneşte daha çok ısınabilir; mevcut gölgeleme ve çalışma saati karar verirken önemlidir. Parça toprakla temas ediyorsa kumun sürtünmesi, hayvanların eriştiği yerdeyse darbe ve kemirme riski ayrıca yazılmalıdır.</p>
<p>Sezon sonunda sökülen sistemlerde kolay montaj istenir; yıl boyu kalan sistemde kilitlenme ve gevşeme daha önemlidir. Sık sökülüp takılan tırnakları gereksiz sert yapmak doğru değildir. Vida ile sabitlenen parçada ise metal vidanın sıkma kuvveti geniş bir yüzeye yayılmalıdır. Ürün teslim edildiğinde önce basınçsız ve yüksüz koşulda oturma kontrolü yapın; hat çalışırken sızıntı veya bağlantı sorunu varsa yardımcı parçayı zorlayarak telafi etmeyin.</p>
<p>Sulama sezonu başlamadan önce yardımcı parçaları yüksüz durumda tek tek kontrol edin. Kelepçede beyazlama, kapakta çatlak veya kılavuzda gevşeme görülüyorsa arıza büyümeden ölçü alın. Aynı hattın farklı noktalarında boru çapı değişebileceği için tek ölçüyü bütün sisteme uygulamayın. Konumları etiketlemek sağ-sol ve giriş-çıkış karışıklığını önler.</p>
<h2>Doğru malzeme</h2>
<p>ASA, güneş ve hava koşulu gören tarımsal parçada ilk değerlendirdiğimiz sert sınıftır. PETG, gölgede veya korunaklı yerde suya ve günlük darbeye karşı dengeli davranır. TPU, hortumu zedelememesi gereken esnek kelepçe içliği, tampon ve titreşim azaltan ara parçada önce düşünülür. Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU bulunur. PA ve takviyeli PA-CF ya da PA-GF yalnız özel talepte, gerçek yük ve kimyasal bilgisiyle değerlendirilir.</p>
<p>Dış ortam malzeme kararlarını <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekân parçası</a> sayfasında karşılaştırabilirsiniz. Sulama düzeni hayvancılık alanındaki suluk ve yemlik yardımcılarıyla birlikte çalışıyorsa <a href="/sut-sagim-hayvancilik-ekipmani-plastik-parca-uretimi/">süt sağım ve hayvancılık ekipmanı parçası</a> sayfasındaki hijyen ve sınır notları da geçerlidir.</p>
<h2>Dürüst sınır</h2>
<p>Basınçlı boru, vana gövdesi, pompa çarkı, ana sızdırmazlık elemanı ve kimyasal deposu üretmiyoruz. Ürettiğimiz parçalar hattı yönlendiren, tutan veya dıştan koruyan düşük ve orta görevli yardımcı elemanlardır. Büyük sulama borusunu taşıyan yapısal mesnet ve insan ya da hayvan güvenliğini etkileyen kilit de bu kapsamda değildir.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Kırık parçanın ve montaj yerinin fotoğrafını, ölçüleri ve kullanım koşulunu +90 545 138 6526 numarasına gönderin. Hazır ürün sayfası olmayan bu işte fiyat önce netleşir; ardından kartla online ödeme yaparsınız. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _tekne_kabin_dolap_mandali_yaptirma():
    return (u"""<h1>Tekne Kabin Dolap Mandalı Özel Üretim</h1>
<p>Kabin dolabının kapağı seyirde açılıyorsa sorun çoğu zaman menteşede değil, birkaç santimlik mandal dili veya karşılık parçasındadır. Eski tekne mobilyasında aynı vida aralığına uyan hazır mandal bulmak zor olabilir; yeni ürünün gövdesi büyük gelir ya da kapak kalınlığına oturmaz. Kırık örnek, sağlam eş parça ve montaj ölçüsü üzerinden aynı işlevi gören mandalı ölçüye özel üretiyoruz.</p>
<p>Genel dolap ve çanta mandalları için <a href="/olcuye-ozel-mandal-kilit-dili-uretimi/">ölçüye özel mandal ve kilit dili</a> sayfası uygundur. Bu içerik, kabin içindeki nem, tuzlu hava, titreşim ve dar montaj alanı gibi tekneye özgü koşullara odaklanır.</p>
<h2>Hangi kabin parçaları değerlendirilebilir</h2>
<p>Dolap kapağı mandal dili, karşılık tırnağı, çekmece stoperi, hafif tutamak, ray ucu, kapak tamponu, havalandırma kapağı klipsi ve profil tapası uygun adaylardır. Kayıp boru veya profil kapakları için <a href="/olcuye-ozel-tapa-kapak-uretimi/">ölçüye özel tapa ve kapak</a> sayfasındaki hazır seçenekler de değerlendirilebilir.</p>
<p>Mandala bakarken yalnız kırık parçayı değil kapak hizasını da kontrol edin. Menteşe sarkmışsa yeni mandal doğru ölçüde olsa bile karşılığa girmeyebilir. Kapak ile gövde arasındaki boşluğu, vida deliklerinin merkezini, dilin ilerleme yönünü ve kapanırken ne kadar esnediğini not edin. Sağlam dolapta aynı mandal varsa onu sökmeden farklı açılardan fotoğraflamak çoğu kez yeterlidir.</p>
<h2>Nasıl ölçü verilir ve iş ilerler</h2>
<p>Kırık parçanın toplam enini, boyunu ve kalınlığını; vida deliği çapını ve merkezler arası mesafeyi ölçün. Dil veya kanca biçimindeyse karşılığı ne kadar geçtiğini gösterin. Kapak kenarı, gövde yüzeyi ve montaj vidası aynı karede görünsün. Tuzlu su sıçraması, doğrudan güneş ve kapak ağırlığı bilgisini ekleyin.</p>
<p>Parça sağ-sol ayna biçimindeyse hangi tarafın gerektiğini açıkça yazın. Vidalı bağlantıda vida başının yüzeye gömülüp gömülmediğini, somun yatağı olup olmadığını gösterin. Esneyerek kapanan tırnakta kalınlığı gereksiz artırmak kırılmayı hızlandırabilir; bu nedenle sağlam örneğin esneme yönü korunur. Güverte üstündeki tente bağlantısı için bu mandal sayfası yerine <a href="/tekne-tentesi-bimini-guverte-aparati-ozel-uretim/">tekne tentesi ve bimini aparatı</a> içeriğini kullanın.</p>
<p>Bu kabin parçalarının hazır ürün sayfası yoktur. Fotoğraf, ölçü ve montaj yerini WhatsApp'tan gönderirsiniz; malzeme ve fiyat netleşir, sonra kartla online ödeme yaparsınız. Eğer ihtiyaç sitede ürün sayfası bulunan genel bir mandal, tapa veya ölçüye özel kalemle karşılanıyorsa o sayfada seçenekleri belirleyip Sepete Ekle üzerinden doğrudan kartla ödeme yapılır.</p>
<h2>Kabin içinde doğru montaj</h2>
<p>Tekne kabininde kapaklar karada olduğundan farklı davranır. Gövde hareketi, titreşim ve nem nedeniyle küçük bir hizasızlık seyirde büyüyebilir. Yeni mandalı takmadan önce menteşe vidalarını, kapak açıklığını ve karşılık parçasının yerini kontrol edin. Kapak elle bastırılmadan kapanmıyorsa mandal dilini daha uzun yapmak sorunu çözmez; menteşe veya gövde ayarı gerekebilir.</p>
<p>Vida delikleri yıpranmışsa yalnız mandalı yenilemek yeterli olmayabilir. Bağlantı noktasını büyütmek mobilyaya zarar verebilir; bu durumda uygun bir karşılık plakası veya farklı sabitleme yöntemi tekne ustasıyla değerlendirilmelidir. Biz plastik gövdeyi ölçüye göre hazırlarız, montaj yüzeyinin sağlamlığını uzaktan garanti edemeyiz.</p>
<p>Parça yerine takıldığında kapak birkaç kez yavaşça açılıp kapatılır. Dil karşılığa sürtmeden girmeli, seyirde kendiliğinden açılmayacak kadar tutmalı ve acil durumda elle açılabilmelidir. Tuzlu su sıçramışsa tatlı suyla temizlemek, kum ve kristallerin sürtünen yüzeyde birikmesini azaltır. Güverte ile kabin sınırında kalan parçada doğrudan güneş süresi ayrıca değerlendirilir. Yedek isteniyorsa sağ-sol yön ve vida aralığı ilk örnek doğrulandıktan sonra çoğaltılır.</p>
<p>Kabin içindeki benzer mandalları da fotoğraflamak doğru gövde ailesini bulmayı kolaylaştırır. Aynı görünüşteki iki parça farklı dil boyuna sahip olabilir. Sökülen vida, pul ve karşılık parçalarını ayrı bir poşette saklayın; montaj sırası kaybolmasın. Kapak üzerinde eski çatlak varsa yeni mandaldan önce mobilya yüzeyi uygun usta tarafından değerlendirilmelidir.</p>
<h2>Doğru malzeme</h2>
<p>ASA, güneş ve tuzlu hava gören yüzeyde ilk sert malzeme tercihidir. PETG, kabin içinde ve gölgede kalan mandal gövdesinde tok bir seçenektir. TPU, kapak tamponu, ses kesen ara parça ve esnek tutucu için önce değerlendirilir. Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU bulunur. PA, sürtünen dil ve burçta; PA-CF veya PA-GF ise rijit özel gövdede WhatsApp üzerinden değerlendirilir.</p>
<p>Dış koşul seçimini <a href="/uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi/">UV ve güneşe dayanıklı dış mekân parçası</a> rehberinde ayrıntılı görebilirsiniz. Farklı renk seçenekleri vardır; kabin içindeki görünür parçanın mevcut mobilyayla uyumu sipariş öncesinde konuşulur.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz mandal dolap, hafif kapak ve eşya gözü içindir. Can yeleği dolabı gibi erişimin güvenlik açısından kritik olduğu bölüm, güverte kapağı, tekne kapısı ana kilidi, yakıt bölmesi kilidi veya insanı tutan bağlantı bu kapsamda değildir. Paslanmaz kilidin veya metal menteşenin yerine plastik parça önermeyiz.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Kırık mandalın, karşılığın ve dolap üzerindeki montaj yerinin fotoğraflarını +90 545 138 6526 numarasına gönderin. Bu özel parçada önce yapılabilirlik ve fiyat netleşir; ardından kartla online ödeme yaparsınız. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _titresim_sonumleyici_esnek_plastik_parca_yaptirma():
    return (u"""<h1>Titreşim Sönümleyici Esnek Plastik Parça</h1>
<p>Bir cihaz masa üzerinde yürüyorsa, kapak belirli devirde zırıltı yapıyorsa veya iki sert yüzey birbirine vuruyorsa daha sert parça çözüm olmayabilir. Tekrarlayan hareketi kesmek için kuvveti emen, kontrollü esneyen bir ara eleman gerekir. Tampon, ayak, burç çevresi veya kavrama göbeği biçimindeki esnek parçayı; sıkışma payı, hareket yönü ve montaj ölçüsüne göre özel üretiyoruz.</p>
<p>Ani darbeye karşı sert ve tok parça arıyorsanız <a href="/darbeye-dayanikli-plastik-parca-yaptirma/">darbeye dayanıklı plastik parça</a> sayfası daha uygundur. Buradaki hedef, tekrarlı titreşimi ve temas sesini azaltan esnek sınıftır.</p>
<h2>Nerede kullanılır</h2>
<p>Masa üstü cihaz ayağı, kapak tamponu, panel arası ara parça, küçük motor muhafazası takozu, boru kelepçesi içliği, hassas cihaz dayaması ve titreşen kapağın temas noktası uygun örneklerdir. Motor ile pompa arasında yıldız biçimli bir göbek gerekiyorsa <a href="/plastik-kaplin-gobegi-esnek-kavrama-uretimi/">esnek kaplin göbeği</a> sayfasındaki ölçüler kullanılır. Sızdırmazlık amacı taşıyan halka veya düz conta içinse <a href="/olcuye-ozel-conta-uretimi/">ölçüye özel conta</a> ürününe bakılmalıdır.</p>
<p>Titreşimin kaynağını ayırmak önemlidir. Dengesiz dönen bir mil, gevşek rulman veya eğri kasnak yalnız tamponla düzelmez. Esnek parça sesi azaltabilir ama mekanik arızayı gizlememelidir. Önce bağlantıları ve dönen elemanları kontrol edin; sonra hangi noktada ne kadar sıkışma gerektiğini belirleyin.</p>
<h2>Nasıl ölçülür ve sertlik kararı verilir</h2>
<p>Parçanın oturacağı alanın enini, boyunu ve yüksekliğini ölçün. Vida geçecekse delik çapını ve baş yatağını, ayağın zemine oturan bölümünü ve sıkıldıktan sonra kalacak boşluğu gösterin. Mevcut kauçuk benzeri parça varsa serbest durumdaki yüksekliğini ve takılıyken ne kadar ezildiğini ayrı ölçün. Titreşimin yönünü, cihazın yaklaşık ağırlığını ve parçanın yağ ya da su görüp görmediğini yazın.</p>
<p>Sertlik seçimi yalnız elde sıkınca oluşan his değildir. Çok yumuşak parça yük altında çöker ve cihazı hizasız bırakır; çok sert parça ise titreşimi doğrudan gövdeye iletir. Kesit kalınlığı, temas alanı ve sıkıştırma miktarı birlikte çalışır. İlk örneğin prova edilmesi, özellikle birden fazla ayağın aynı seviyede durduğu cihazlarda yararlıdır.</p>
<p>Bu tür özel tamponların hazır ürün sayfası yoktur. Fotoğraf, ölçü ve montaj yerini WhatsApp'tan gönderirsiniz; geometri, malzeme ve fiyat netleşince kartla online ödeme yaparsınız. Sitedeki ürün sayfası bulunan conta veya uygun ölçüye özel kalem gerçek ihtiyacı karşılıyorsa malzeme seçicide TPU'yu belirleyip Sepete Ekle üzerinden doğrudan kartla ödeyebilirsiniz.</p>
<h2>Sönümleme sorununu ölçmek</h2>
<p>Titreşim yalnız hissedilerek değil, hangi devirde ve hangi yönde oluştuğu gözlenerek anlatılmalıdır. Cihaz açılırken kısa süre mi sallanıyor, çalışma boyunca aynı mı kalıyor, belirli hızda mı artıyor? Ayağın zeminden ayrılması, kapağın çarpması veya panelin uğultu yapması farklı parça biçimleri gerektirir. Kısa bir video ve parçanın yerini gösteren fotoğraf değerlendirmeyi kolaylaştırır.</p>
<p>Birden fazla ayakta kullanılan tamponların yüksekliği eşit olmalıdır. Tek ayağa daha yumuşak parça koymak cihazı eğebilir ve rulman ya da mil hizasını bozabilir. Tasarımda yalnız serbest yükseklik değil, çalışma yükü altındaki sıkışma miktarı hedeflenir. Vida deliği varsa metal vida esnek gövdeyi kesmemeli; baş altında yeterli oturma yüzeyi bulunmalıdır.</p>
<p>İlk denemede cihaz düşük hızda çalıştırılır ve tamponun yuvasından çıkmadığı gözlenir. Aşırı ezilme, kenardan şişme veya zeminde yürüme varsa kesit ya da malzeme yeniden değerlendirilir. Yağ ve temizlik maddesi gören parçalarda kısa süreli temas ile sürekli bekleme aynı değildir. Sönümleme parçası bakım gerektirmeyen kalıcı bir çözüm gibi sunulmaz; düzenli gözle kontrol edilir ve şekil kaybı başladığında değiştirilir.</p>
<p>Parçanın sıkışacağı en küçük ve en büyük boşluğu ayrı ölçmek, esnek kesitin hareket payını belirler. Cihaz taşınırken ayaktan tutuluyorsa bunu da yazın; taşıma kuvveti çalışma titreşiminden farklıdır. Tamponun zemine yapışması veya iz bırakması istenmiyorsa yüzey türünü belirtin. İlk haftadaki şekil değişimi sonraki bakım aralığı için kaydedilmelidir.</p>
<h2>Doğru malzeme</h2>
<p>Esnek işlerde ilk değerlendirdiğimiz sınıf TPU'dur. Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU bulunur; conta, tampon, sönümleme ve esnek kaplin göbeğinde gereksiz yere sert sınıfa geçmeyiz. TPU'nun sertlik ve kesit davranışı kullanım yerine göre değerlendirilir. PETG veya ASA ancak parçadan sönümleme beklenmeyen, daha çok konum tutan bir gövde söz konusuysa uygundur.</p>
<p>PA ve takviyeli sınıflar rijit parçalara yöneliktir; titreşim emen bir tamponun yerine geçmez. Malzeme sınıflarının nem, güneş, darbe ve esneklik farklarını <a href="/malzeme-rehberi/">malzeme rehberi</a> içinde karşılaştırabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Ürettiğimiz esnek parça, üretici tarafından hesaplanmış motor takozu, araç süspansiyonu, fren elemanı, asansör tamponu veya insan güvenliği taşıyan titreşim izolatörü değildir. Yüksek hızlı dönen sistemde balans sorunu varsa önce mekanik servis gerekir. Conta sınıfımız düşük ve orta basınç içindir; yüksek basınç hattına verilmez.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Esnek TPU sınıfının gerçek ısı sınırı bu üst tavanın altında olabilir; çalışma sıcaklığını baştan yazın. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Parçanın fotoğrafını, ölçüsünü, montaj yerini ve titreşimin yönünü +90 545 138 6526 numarasına gönderin. Hazır ürün sayfası olmayan bu işte malzeme ve fiyat önce netleşir; sonra kartla online ödeme yapılır. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _oto_havalandirma_izgara_klipsi_yaptirma():
    return (u"""<h1>Oto Havalandırma Izgara Klipsi Üretimi</h1>
<p>Havalandırma ızgarasının tek kanadı boşta kaldığında yön ayarı yapılamaz; çoğu zaman kırılan parça görünmeyen küçük bir bağlantı klipsidir. Servis bütün ızgara gövdesini önerse de sağlam kanatlar ve çerçeve değişmek zorunda değildir. Kırık klips, ayar düğmesi veya kanat bağlantısını; sağlam eş parçadan, karşı yuvadan ve montaj geometrisinden ölçerek özel üretiyoruz.</p>
<p>Kapı döşemesi ve genel iç trim bağlantıları için <a href="/oto-ic-trim-klips-parca-uretimi/">oto iç trim ve klips parçası</a> sayfası uygundur. Buradaki içerik, havalandırma ızgarasının hareketli küçük bağlantılarına ayrılmıştır.</p>
<h2>Hangi parçalar yeniden yapılabilir</h2>
<p>Yatay veya düşey kanadı birbirine bağlayan ince çubuk klipsi, yönlendirme düğmesi, döner topuz gövdesi, kanat pivotu, çerçeve tırnağı ve dekor kapağı değerlendirilebilir. Düğme doğrudan mile geçiyorsa <a href="/olcuye-ozel-dugme-ayar-topuzu-uretimi/">ölçüye özel düğme ve ayar topuzu</a> sayfasındaki mil biçimleri daha doğru çözüm sunabilir. Esneyerek geçen tek bir tırnak kırıldıysa <a href="/kirik-plastik-tirnak-yaptirma/">kırık plastik tırnak</a> rehberindeki ölçüm yöntemi kullanılabilir.</p>
<p>Parçanın görevi yalnız görünüş değildir. Kanatlar birlikte hareket ederken klips hem çekme hem itme kuvveti alır; fazla sıkı yapılırsa ayar kolu zorlanır, fazla gevşek yapılırsa kanatlar yeniden düşer. Bu yüzden sağlam taraftaki bağlantı boşluğu ve pivot çapı ölçülür. Yuvada kırık kalıntı varsa sökmeden önce fotoğrafını çekin.</p>
<h2>Nasıl sökülür, ölçülür ve gönderilir</h2>
<p>Izgara çerçevesini zorlayarak çıkarmayın; görünmeyen başka tırnaklar kırılabilir. Erişim güvenliyse sağlam klipsi cetvel veya kumpas yanında fotoğraflayın. Toplam boy, kalınlık, pivot çapı, kanatlar arası mesafe ve düğmenin oturduğu kesit temel ölçülerdir. Sağlam yolcu tarafı ızgarası sürücü tarafıyla ayna biçimindeyse yön bilgisini yazın.</p>
<p>Araç marka, model ve üretim yılı yardımcı bilgidir; tek başına doğru parçayı belirlemez. Aynı modelde farklı konsol paketi bulunabilir. Bu nedenle parça fotoğrafı, ızgaranın genel görünüşü ve montaj ölçüsü birlikte gönderilmelidir. Eski model araçlarda parça kodu okunmuyorsa <a href="/klasik-arac-eski-model-oto-plastik-parca-uretimi/">eski model araç plastik parçası</a> sayfasındaki numune yolu geçerlidir.</p>
<p>Bu özgül klipsin hazır ürün sayfası yoktur. Fotoğraf, ölçü ve araçtaki montaj yerini WhatsApp'tan iletirsiniz; yapılabilirlik ve fiyat netleşir, sonra kartla online ödeme yaparsınız. Sitede ürün sayfası olan genel düğme veya klips ihtiyacı karşılıyorsa o ürünün gerçek seçeneklerini belirleyip Sepete Ekle ile kartla ödeyebilirsiniz.</p>
<h2>Montaj sonrası işlev kontrolü</h2>
<p>Yeni klips takıldığında bütün kanatlar aynı anda ve benzer dirençle hareket etmelidir. Bir kanat diğerlerinden önce duruyorsa çubuk boyu veya pivot hizası kontrol edilir. Düğmeyi zorlayarak çevirmek ince bağlantıları yeniden kırabilir; hareket sıkıysa parça sökülüp temas noktası incelenir. Havalandırma gövdesine yapıştırıcı sürmek sonraki bakımda bütün çerçevenin zarar görmesine yol açabileceği için önerilmez.</p>
<p>Konsol güneşte ısındığında boşluklar değişebilir. Oda sıcaklığında rahat çalışan klips, sıcak araçta genleşme nedeniyle sıkışmamalıdır. Aynı zamanda gevşek olup yol titreşiminde ses yapmaması gerekir. Bu denge için sağlam parçadaki çalışma payı korunur. İnce tırnaklarda köşe çatlağı görülüyorsa montaj yönü ve sökme kuvveti tekrar değerlendirilir.</p>
<p>Yönlendirme kanadının üzerinde telefon tutucu veya başka aksesuar kullanılıyorsa klipse ilave yük biner. Tasarım havanın yönünü ayarlayan özgün göreve göre yapılır; aksesuar taşıma vaadi verilmez. İlk kullanımda kanatlar elle yavaşça hareket ettirilir, ardından fan düşük kademede denenir. Ses, takılma veya kanadın düşmesi görülürse ölçü düzeltilmeden zorlanmamalıdır. Temizlikte sert alet yerine yumuşak bez kullanmak pivot çevresindeki ince yapıyı korur.</p>
<p>Klipsi sökerken kanatların sırasını ve yönünü küçük işaretlerle kaydedin. Benzer görünen kanatlar farklı pivot konumuna sahip olabilir. Izgara çevresinde daha önce yapılmış onarım varsa fotoğrafta gizlemeyin; yapıştırıcı kalıntısı gerçek boşluğu değiştirebilir. Montajdan sonra hava yönü, düğme hareketi ve yol sesini ayrı ayrı kontrol etmek işlev doğrulamasını kolaylaştırır.</p>
<h2>Doğru malzeme</h2>
<p>PETG, iç trimde tok davranan dengeli bir seçenektir. ASA, ön cama yakın güneş gören konsolda ısı ve UV koşulu nedeniyle değerlendirilir. TPU, titreşim sesi kesen tampon veya esnek ara parça için siteden seçilebilir; fakat ince yönlendirme klipsinin şekli koruması gerekiyorsa ilk tercih değildir. Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU bulunur. PA, aşınan pivot veya sürtünen küçük yatakta özel talep olarak düşünülebilir.</p>
<p>Renk seçenekleri araç içi tona göre değerlendirilir; yüzey dokusu ve parlaklık mevcut parçayla tam aynı olmayabilir. İşlevsel uyum ile kozmetik eşleşme ayrı hedeflerdir ve sipariş öncesinde hangisinin önemli olduğu belirtilmelidir.</p>
<h2>Dürüst sınır</h2>
<p>Havalandırma klipsi ile hava yastığı kapağı, emniyet kemeri elemanı veya sürüş güvenliğini etkileyen kumanda aynı kapsamda değildir. Hava yastığı çevresi, fren ve direksiyon bağlantısı, koltuk kilidi gibi güvenlik parçalarını üretmiyoruz. Isıtıcı çekirdeğe veya sıcak hava kanalının derinine giren parçada çalışma sıcaklığı ayrıca ölçülmelidir.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Kırık klipsi, sağlam eş parçayı ve ızgara üzerindeki yerini +90 545 138 6526 numarasına gönderin. Bu özel işte önce ölçü, malzeme ve fiyat netleşir; ardından kartla online ödeme yaparsınız. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _bulasik_makinesi_sepet_tekerlegi_yaptirma():
    return (u"""<h1>Bulaşık Makinesi Sepet Tekeri Üretimi</h1>
<p>Sepet raydan çıktığında sorun çoğu zaman makinenin kendisinde değil, aşınmış bir tekerlek veya kırılmış aks klipsindedir. Çapı yakın görünen hazır teker ray kanalına oturmayabilir; genişlik farkı sepeti yana çeker ve diğer tekerleri de zorlar. Kırık tekeri, sağlam eşini ve ray ölçüsünü birlikte inceleyerek düşük ve orta yükte çalışan yedek parçayı ölçüye özel üretiyoruz.</p>
<p>Diğer kapak, düğme ve sepet parçaları için <a href="/beyaz-esya-plastik-parca-uretimi/">beyaz eşya plastik parça üretimi</a> sayfası daha geniş kapsam sunar. Genel makara geometrilerini ve sınırlarını karşılaştırmak için <a href="/olcuye-ozel-tekerlek-makara-uretimi/">ölçüye özel tekerlek ve makara</a> rehberi de değerlendirilebilir.</p>
<h2>Teker ve taşıyıcıda hangi ölçüler önemlidir</h2>
<p>Tekerin dış çapı, genişliği, aks deliği veya klips geçme çapı, iki yan yüz arasındaki mesafe ve ray kanalının iç ölçüsü temel verilerdir. Tekerin kenarında rayı takip eden kanal varsa kanal genişliği ile derinliği ayrıca ölçülür. Aks parçası sepet telini kavrıyorsa tel çapı ve kilitlenme yönü gösterilmelidir. Sağlam tekeri sökmeden ölçmek mümkünse montaj sırasını fotoğrafla kaydedin.</p>
<p>Aşınmış tekerin çapı başlangıç değerini küçültmüş olabilir. Aynı sepetin az kullanılan arka tekeri veya üst sepetin benzer taşıyıcısı karşılaştırma için daha güvenilir olabilir. Sepetin boşken ve doluyken nasıl oturduğunu, tekerin ray üzerinde dönüp dönmediğini ya da kayarak mı ilerlediğini söyleyin.</p>
<h2>Nasıl ilerler ve prova yapılır</h2>
<p>Kırık parçayı temizleyip üst, alt ve yan yüzlerden fotoğraflayın. Yanına cetvel koyun; kritik delik ve kanal ölçülerini mümkünse kumpasla alın. Rayın kesitini, sepet telini ve sağlam karşı tarafı da gösterin. Ölçü alma konusunda tereddüt varsa <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü alma rehberi</a> ile kontrol listesi oluşturun.</p>
<p>İlk teker sepet boşken elle denenir. Rayda sıkışmamalı, yana devrilmemeli ve klips kendiliğinden açılmamalıdır. Ardından normal bulaşık yükünde kısa bir çevrim gözlenir. Deterjan, sıcak su ve kurutma aşaması malzemeyi birlikte zorlar; yalnız oda sıcaklığındaki prova yeterli değildir. Bu koşulları <a href="/sicak-su-ve-buhar-temasli-plastik-parca-uretimi/">sıcak su ve buhar temaslı parça</a> sayfasında ayrıntılı anlattık.</p>
<p>Bu özgül OEM parçanın ve genel teker-makara kaleminin hazır ürün sayfası yoktur. Fotoğraf, ölçü, cihaz modeli ve montaj yerini WhatsApp'tan gönderirsiniz; yapılabilirlik ve fiyat netleşir, sonra kartla online ödeme yaparsınız. Landing sayfasındaki genel makara bilgisi ölçü karşılaştırmasına yardım eder, doğrudan Sepete Ekle akışı sunmaz.</p>
<h2>Neden teker tekrar kırılır</h2>
<p>Sepet rayı eğilmişse, tel gövde yamulmuşsa veya bir teker diğerlerinden küçükse yük eşit dağılmaz. Yeni parça kısa sürede aynı noktadan kırılabilir. Teker siparişinden önce sepeti boşken ray üzerinde sürün; sağ ve sol tarafta benzer direnç olup olmadığını kontrol edin. Ray üzerinde çapak, deterjan kalıntısı veya pas varsa temizlenmelidir.</p>
<p>Aks klipsinin görevi tekeri tutmak kadar bakımda sökülebilmesini de sağlamaktır. Gereksiz sıkı geçme montaj sırasında tırnağı zorlar; gevşek geçme sıcak çevrimde tekerin çıkmasına yol açar. Sağlam parçadaki kilit yönü ve esneme payı bu yüzden önemlidir. Birden fazla teker aşınmışsa yalnız en kötü olanı değiştirmek sepeti eğik bırakabilir; takım hâlindeki ölçü farkları kontrol edilir.</p>
<p>İlk çevrimden sonra makine soğuduğunda teker ve klips gözle incelenir. Şekil değişimi, rayda sürtme izi veya sepetin yana çekmesi varsa parça kullanılmaya devam edilmez. Deterjan türü, sıcaklık programı ve kurutma alışkanlığı kullanım koşulunu değiştirir. Üretilen yedek, sepet taşıma işlevi içindir; üreticinin güvenlik testlerinin veya bakım talimatının yerine geçmez. Cihazın elektrik ve su bağlantısına müdahale etmeyin; yalnız erişilebilir sepet aksamında çalışın.</p>
<p>Cihaz model etiketini ve sepetin alt mı üst mü olduğunu fotoğrafa ekleyin. Aynı makine ailesinde iki sepet farklı teker kullanabilir. Sağlam parçayı ölçerken sıcak çevrimden sonra tamamen soğumasını bekleyin. Bir tekerin ray dışına çıkmasına zorlayarak devam etmek rayı ve sepet telini de eğebilir; arıza görüldüğünde kullanım durdurulmalıdır.</p>
<h2>Doğru malzeme</h2>
<p>PETG, su ve günlük darbe için dengeli olsa da sürekli sıcak çevrimde parça geometrisi ayrıca değerlendirilir. ASA daha yüksek sıcaklık ve ölçü kararlılığı gereken bazı gövdelerde düşünülebilir. PA, sürtünen ve aşınan teker veya burçta özel talep olarak öne çıkar. TPU sitede seçilebilir; rayda sessiz çalışan esnek bir dış yüzey isteniyorsa değerlendirilebilir, fakat yumuşaklığın sepeti hizasız bırakmaması gerekir. Sitedeki seçicide PLA, PETG, ASA ve TPU bulunur.</p>
<p>Malzeme bulaşık alanında kullanıldığı için parça ile gıda temasını ayırmak gerekir. Sepet tekeri çoğunlukla taşıyıcı elemandır; yine de kullanım yeri ve temizlik döngüsü sipariş sırasında açıkça yazılmalıdır.</p>
<h2>Dürüst sınır</h2>
<p>Yüksek sıcaklıkta ana su hattını kapatan vana, pompa gövdesi, ısıtıcı çevresi, basınçlı bağlantı ve ana kapı kilidi bu hizmet kapsamında değildir. Ürettiğimiz parça sepetin düşük ve orta yükte hareketini sağlayan yardımcı teker veya taşıyıcıdır; cihaz güvenlik sisteminin yerine geçmez.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Tekerin, sağlam eşinin, rayın ve sepet üzerindeki bağlantının fotoğraflarını +90 545 138 6526 numarasına gönderin. Bu özel işte önce ölçü, malzeme ve fiyat belirlenir; ardından kartla online ödeme yaparsınız. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _ozel_parcaya_logo_ve_yazi_isleme():
    return (u"""<h1>Özel Parçaya Logo ve Yazı İşleme</h1>
<p>Bir parçanın üzerine marka logosu, yön oku, kısa kullanım notu veya parça kodu eklemek hem tanımayı kolaylaştırır hem montaj hatasını azaltır. Fakat ekranda net görünen her logo küçük bir yüzeyde okunmaz; ince çizgiler kaybolabilir, uzun metin sıkışabilir. Ölçüye özel ürettiğimiz uygun parçalara kabartma, oyma veya gömme görünümlü yazı ve sade logo uygulayabiliyoruz.</p>
<p>Bu hizmet kaşe yaptırmakla aynı niyet değildir. Kaşe arıyorsanız <a href="/kisiye-ozel-logolu-kase-yaptirma/">kişiye özel logolu kaşe</a> sayfasını kullanın. Buradaki konu, nihai parçanın kendi yüzeyindeki kalıcı işaret ve tanımlamadır.</p>
<h2>Hangi içerikler uygundur</h2>
<p>Firma adı, kısa parça kodu, sağ-sol işareti, aç-kapa yönü, ölçü değeri, sıra numarası, uyarı simgesi ve sade tek renk logo uygun örneklerdir. Çok küçük alt yazı, fotoğraf ayrıntısı, ince gölge geçişi ve çok renkli görsel aynı netlikle yüzeye aktarılamaz. İşaretin amacı dekor mu, montaj yönlendirmesi mi, izlenebilirlik mi; bunu baştan belirtin.</p>
<p>Logo dosyanızın temiz olması sonucu doğrudan etkiler. Çizgilerin kapalı, yazının okunaklı ve arka planın ayrı olması gerekir. Dosyanın nasıl hazırlanacağını <a href="/kaseye-islenecek-logo-dosyasi-nasil-hazirlanir/">logo dosyası hazırlama rehberi</a> anlatır. Aynı kurallar parça yüzeyindeki logoda da geçerlidir: sade kontur, yeterli kalınlık ve küçük ölçekte deneme.</p>
<h2>Nasıl yerleşim belirlenir</h2>
<p>Önce logonun geleceği yüzeyin enini, boyunu ve eğimini ölçün. Vida deliği, tırnak, kenar pahı ve sürtünen alanların üzerine yazı gelmemelidir. Logonun hangi yönden okunacağını montaj fotoğrafında işaretleyin. Sağ ve sol parçalarda aynı logo kullanılacaksa ayna dönüşü gerekip gerekmediğini belirtin.</p>
<p>Kısa metni yazım hatasına karşı sipariş öncesinde düz metin olarak da gönderin. Büyük-küçük harf, noktalama ve Türkçe karakterler teyit edilir. Kabartma, oyma veya gömme görünüm seçimi yüzey kalınlığına göre yapılır. Ölçü işaretli bir mastar veya cetvel istiyorsanız <a href="/olcuye-ozel-cetvel-mastar-sablon-uretimi/">ölçüye özel cetvel ve mastar</a> ürünü daha doğru yoldur.</p>
<p>Logo işlemesi tek başına bağımsız bir hazır ürün değildir; uygulanacağı parçayla birlikte değerlendirilir. Özel parçanın fotoğrafını, ölçüsünü, montaj yerini ve logo dosyasını WhatsApp'tan gönderirsiniz; yapılabilirlik ve fiyat netleşir, sonra kartla online ödeme yaparsınız. Sitede ürün sayfası olan kaşe, cetvel veya başka bir ölçüye özel kalem kendi seçeneklerinde yazı ve logo sunuyorsa o sayfadan seçim yapıp Sepete Ekle ile kartla ödeyebilirsiniz.</p>
<h2>Okunaklılık için prova</h2>
<p>Logo nihai boyuta küçültülmeden önce siyah-beyaz görünümde kontrol edilmelidir. İnce boşluklar kapanıyor, harf içleri kayboluyor veya sembol tanınmıyorsa sadeleştirme gerekir. En küçük ayrıntı parçanın boyutuna ve yüzeyine göre belirlenir; yalnız dosyanın çözünürlüğüne bakmak yeterli değildir. Özellikle uzun firma adlarında tek satır yerine iki satır veya yalnız kısa marka adı daha okunaklı olabilir.</p>
<p>Yön oku, sağ-sol işareti ve parça kodu dekoratif logodan farklı değerlendirilir. Montaj sırasında uzaktan okunması gerekiyorsa kontrast ve yön önceliklidir. Sürtünen, ele temas eden veya temizlenirken aşınan yüzeyde çok ince kabartma hızla silikleşebilir. Yazıyı korunaklı bir yüzeye taşımak çoğu zaman daha doğru çözümdür.</p>
<p>Sipariş teyidinde uygulanacak metin, yazım biçimi, logo yönü ve parça üzerindeki konum tek görsel üzerinde işaretlenir. Aynı parçanın sağ-sol sürümü varsa metnin ayna dönmemesine dikkat edilir. İlk örnekte okunaklılık kontrol edilir; adetli işlerde bu onaydan sonra aynı yerleşim korunur. Dosyada yapılan sadeleştirme müşteriye gösterilmeden üretime geçilmez. Böylece görsel beklenti ile teknik olarak uygulanabilir yüzey arasında baştan ortak karar kurulur.</p>
<p>Logonun çevresinde bırakılacak boşluk, işaretin kendisi kadar önemlidir. Kenara çok yaklaşan şekil hem zor okunur hem yüzeyde zayıf bölüm oluşturabilir. Parça birden fazla yönde takılabiliyorsa okunma yönünü montaj fotoğrafı üzerinde okla gösterin. Aynı adette farklı kodlar isteniyorsa kod listesini sıralı ve yazılı biçimde iletin.</p>
<h2>Doğru malzeme</h2>
<p>Yazının görünürlüğünü yalnız renk değil yüzey ve kullanım koşulu belirler. PLA kuru iç mekânda dekoratif ve hafif işlerde kullanılabilir. PETG tok genel parçalarda, ASA dış ortam ve güneşte değerlendirilir. TPU sitede seçilebilir; esnek yüzeyde büyük ve sade işaret uygulanabilir, fakat ince ayrıntı sert malzemedeki kadar keskin olmayabilir. Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU bulunur. PA ve takviyeli sınıflar özel talepte değerlendirilir.</p>
<p>Taban ile yazı arasında belirgin ton farkı okunabilirliği artırır. Farklı renk seçenekleri vardır, ancak her tonun her malzemede bulunacağı varsayılmamalıdır. Fiyatı parça boyutu, malzeme, yüzey ayrıntısı ve adet etkiler; genel çerçeveyi <a href="/ozel-parca-uretimi-fiyati-nasil-belirlenir/">özel parça fiyatı nasıl belirlenir</a> sayfasında bulabilirsiniz.</p>
<h2>Dürüst sınır</h2>
<p>Bu yüzey işlemi resmi sertifika, kalibrasyon belgesi, güvenlik etiketi veya yasal uygunluk işareti yerine geçmez. Yetkisiz marka kullanımını, yanıltıcı uygunluk damgasını ve başkasına ait logonun izinsiz çoğaltılmasını kabul etmeyiz. Çok ince fotoğraf ayrıntısını veya endüstriyel etiket kalitesinde renk geçişini vaat etmeyiz.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Parça görselini, ölçüleri, logo dosyasını, işlenecek metni ve montaj yönünü +90 545 138 6526 numarasına gönderin. Bu özel işte fiyat önce netleşir; ardından kartla online ödeme yapılır. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _mil_rulman_icin_olcuye_ozel_plastik_yuva():
    return (u"""<h1>Mil ve Rulman İçin Ölçüye Özel Plastik Yuva</h1>
<p>Rulman sağlam olduğu hâlde onu taşıyan gövde çatladıysa bütün mekanizmayı değiştirmek gerekmeyebilir. Sorun çoğu zaman rulmanın dış bileziğini tutan yuva, mili hizalayan mesnet veya bağlantı deliklerinin bulunduğu plastik gövdedir. Elinizdeki metal elemanın gerçek ölçüsüne göre yuva çapını, oturma derinliğini, geçme payını ve montaj geometrisini tasarlayarak düşük ve orta görevli taşıyıcıyı özel üretiyoruz.</p>
<p>Burç veya düşük yükte çalışan plastik rulmanın kendisi gerekiyorsa <a href="/numuneden-plastik-burc-rulman-uretimi/">plastik burç ve rulman yatağı</a> sayfası uygundur. Buradaki ürün, müşterinin temin ettiği metal mil ya da rulmanı çevreleyen plastik yuva ve mesnettir.</p>
<h2>Hangi ölçüler gerekir</h2>
<p>Rulmanın üzerindeki standart kod okunuyorsa kodu, dış çapı, genişliği ve varsa flanşı not edin. Kod yoksa kumpasla dış çapı birkaç yönden ölçün; aşınmış gövdeye göre değil metal rulmanın kendisine göre ilerleyin. Yuvanın derinliği, omuz konumu, açık veya kapalı oluşu ve rulmanın hangi taraftan takılacağı belirlenmelidir. Mil için çap, kesit biçimi, eksen yönü ve çalışma boşluğu gerekir.</p>
<p>Montaj gövdesinde toplam en, boy, kalınlık, delik çapı ve delik merkezleri ölçülür. Yuva iki parçalı kelepçe biçimindeyse birleşim yüzeyi ve vida yönü fotoğraflanır. Mevcut gövde çatlamışsa çatlağın başladığı nokta yük yönünü gösterir; yalnız aynısını çoğaltmak yerine köşe geçişi veya kesit yerleşimi gözden geçirilebilir.</p>
<h2>Nasıl ilerler ve geçme kontrol edilir</h2>
<p>Metal rulmanı, kırık yuvayı ve mekanizma üzerindeki montaj yerini ayrı ayrı fotoğraflayın. Cetvel genel ölçek verir, fakat geçme çapı için kumpas gerekir. Ölçü sırasını <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü alma rehberi</a> ile kontrol edebilirsiniz. Rulmanın dönmesi gereken bilezik ile gövdeye sabit kalması gereken bileziği açıkça belirtin.</p>
<p>Geçme toleransı kullanım yerine göre değişir. Çok sıkı yuva rulmanı sıkıştırabilir veya montajda gövdeyi çatlatabilir; çok gevşek yuva ise titreşim ve eksen kaçıklığı üretir. İlk örnek metal elemanla prova edilir. Isı değişimi, nem ve montaj vidasının sıkma kuvveti de boşluğu etkiler. Hazır bir L veya T mesnet çözümü gerekiyorsa <a href="/olcuye-ozel-montaj-braketi/">ölçüye özel montaj braketi</a> seçenekleri değerlendirilebilir.</p>
<p>Bu özel yuva için hazır ürün sayfası yoktur. Rulman veya mil fotoğrafını, ölçüyü ve montaj yerini WhatsApp'tan gönderirsiniz; yapılabilirlik, tolerans ve fiyat netleşir, sonra kartla online ödeme yaparsınız. Sitedeki katalog ürünü olan burç, rulman veya braket gerçek ihtiyacı karşılıyorsa yalnız ilgili ürün sayfasından seçenekleri belirleyip Sepete Ekle ile kartla ödeme yapılır.</p>
<h2>Hizalama hatasını önleme</h2>
<p>Rulman yuvası yalnız çapı tutan bir halka değildir; ekseni mekanizmanın geri kalanına göre doğru yerde tutar. Vida delikleri doğru görünse bile yuva merkezi kayıksa mil zorlanır, ses ve ısınma oluşur. Bu nedenle montaj yüzeyinden mil eksenine olan mesafe iki yönde ölçülür. Karşı tarafta ikinci yatak varsa iki merkezin aynı hat üzerinde olduğu kontrol edilir.</p>
<p>Rulmanı yuvaya çekiçle zorlamak doğru değildir. Geçme sıkıysa metal eleman, plastik gövde veya rulman bileziği zarar görebilir. Montaj yöntemi tasarım aşamasında belirlenir: önden bastırma, iki parçalı kelepçe veya kapakla tutma seçenekleri farklı geometri ister. Sökme gerekecekse erişim payı bırakılır. Vida sıkma sırası da gövdeyi eğmemek için dengeli olmalıdır.</p>
<p>İlk denemede mil elle çevrilir. Takılma, belirgin sürtünme, boşluk veya yuvanın hareket etmesi varsa sistem çalıştırılmaz. Kısa ve yüksüz kontrolden sonra sıcaklık artışı gözlenir; olağan dışı ısınma hizasızlık işareti olabilir. Plastik yuva, bakım gerektirmeyen hassas endüstriyel yatak iddiası taşımaz. Kullanım süresince çatlak, gevşeme ve aşınma düzenli incelenir. Metal rulmanın tipi ve üretici montaj önerisi de korunmalıdır.</p>
<p>Yuvanın yanında kayış veya dişli varsa eksen konumu yalnız rulmana göre değil bu elemanlara göre de kontrol edilir. Kasnak hizasındaki küçük kaçıklık yeni gövdeyi gereksiz zorlayabilir. Sökülen ara pulların sırasını kaydedin ve metal elemanın yüzeyindeki çapakları ölçümden önce temizleyin. Prova sırasında koruma kapağı ve diğer bağlantılar da yerinde olmalıdır.</p>
<h2>Doğru malzeme</h2>
<p>PETG, düşük hız ve düşük yükteki genel muhafaza ve mesnetlerde tok bir başlangıçtır. PA, sürtünme ve aşınma olan yuvalarda özel talep olarak değerlendirilir. PA-CF ve PA-GF, gövdenin yük altında daha az esnemesi gereken işlerde düşünülebilir; fakat ince klips veya darbeli bağlantıda otomatik seçim değildir. Karar ölçütleri için <a href="/karbon-fiber-takviyeli-naylon-parca-ne-zaman-gerekir/">takviyeli naylon ne zaman gerekir</a> rehberine bakın.</p>
<p>Sitedeki malzeme seçicide PLA, PETG, ASA ve TPU yer alır. TPU, rulmanı konumda tutan rijit yuva için uygun değildir; titreşim ayıran ayrı bir ara bilezik söz konusuysa değerlendirilebilir. PA ve takviyeli sınıflar ürün sayfasında seçilmez, özel talep olarak ele alınır.</p>
<h2>Dürüst sınır</h2>
<p>Yüksek devirli ana mil yatağı, araç teker rulmanı, kaldırma düzeneği, direksiyon, fren veya insan güvenliğini etkileyen rulman yuvası üretmiyoruz. Ürettiğimiz gövde düşük ve orta hız/yükte, yardımcı mekanizmalarda kullanılır. Hassas eksen kaçıklığı ve sürekli yağlama hesabı gereken yataklar uygun endüstriyel metal gövdelerin alanıdır.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Rulman kodunu, metal elemanın ölçüsünü, kırık yuvayı ve montaj yerini +90 545 138 6526 numarasına gönderin. Hazır ürün sayfası olmayan bu işte tolerans ve fiyat önce netleşir; ardından kartla online ödeme yaparsınız. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")

def _numune_olmadan_plastik_parca_yaptirilir_mi():
    return (u"""<h1>Numune Olmadan Plastik Parça Yaptırılır mı?</h1>
<p>Kırık parça çöpe atılmış, kaybolmuş veya parçalanıp ölçü veremeyecek hâle gelmiş olabilir. Bu durumda üretim imkânsız değildir; fakat parçanın kendisi yerine çevresindeki izlerden ilerlemek gerekir. Montaj yuvası, karşı parça, vida delikleri, sağlam sağ-sol eş, eski fotoğraf veya servis çizimi geometriyi yeniden kurmak için kaynak olabilir. Numune yokken yapılabilirlik, elimizde kalan bu referansların yeterliliğine bağlıdır.</p>
<p>Parça var fakat kodu bilinmiyorsa <a href="/yedek-parca-kodu-bilinmiyorsa-ne-yapilir/">yedek parça kodu bilinmiyorsa</a> rehberi daha doğru başlangıçtır. Elinizde fiziksel örnek varsa <a href="/numuneye-gore-plastik-parca-uretimi/">numuneye göre plastik parça üretimi</a> yolu daha hızlı ve daha güvenilirdir.</p>
<h2>Numune yerine hangi kanıtlar kullanılabilir</h2>
<p>Parçanın oturduğu yuvadaki vida delikleri, aşınma izi, tozdan korunmuş yüzey, karşı tırnak ve mil çapı temel ipuçlarıdır. Aynı cihazın diğer tarafında ayna simetrik parça bulunabilir. Kullanım kılavuzundaki patlatılmış görünüş, eski ilan fotoğrafı veya telefonunuzdaki söküm öncesi kare de biçimi anlamaya yardımcı olur. Ancak perspektifli fotoğraftan hassas ölçü çıkarmak güvenilir değildir; en az bir gerçek ölçü referansı gerekir.</p>
<p>Parçanın görevini tarif etmek de geometri kadar önemlidir. Kapak mı tutuyor, mili mi merkezliyor, kabloyu mu yönlendiriyor, yalnız görünüşü mü tamamlıyor? Hareket yönü, yük, sıcaklık, güneş, su ve kimyasal bilgisi bilinmeden doğru malzeme seçilemez. Parça kaybolduğunda gereksiz ayrıntıyı değil işlevi yeniden kurmayı hedefleriz.</p>
<h2>Nasıl ölçü ve fotoğraf hazırlanır</h2>
<p>Montaj yerini karşıdan, yandan ve üstten çekin. Her karede cetvel veya bilinen ölçülü bir nesne bulunsun. Vida deliği çapı, delik merkezleri, yuvanın eni-boyu-derinliği, mil veya boru çapı ve hareket mesafesi temel listedir. Ölçülerin nereden alınacağını <a href="/parca-olcusu-nasil-alinir-ve-gonderilir/">parça ölçüsü alma ve gönderme rehberi</a> üzerinden kontrol edin.</p>
<p>Sağlam benzer parça varsa hangi yönünün ayna olacağını işaretleyin. Montaj yüzeyi eğriyse yalnız iki uç ölçüsü yetmeyebilir; birkaç noktadan yükseklik alın. Vida ve mil gibi standart elemanları fotoğrafta gösterin. İlk tasarımın prova parçası gerekebileceğini kabul edin; numunesiz işte bir düzeltme turu olağandır ve fiyatlandırma öncesinde konuşulur.</p>
<p>Bu tür kayıp parça için hazır ürün sayfası yoktur. Fotoğrafları, ölçüleri ve montaj yerini WhatsApp'tan gönderirsiniz; yapılabilirlik değerlendirilir, fiyat verilir, sonra kartla online ödeme yaparsınız. İhtiyaç sitede ürün sayfası bulunan standart bir ölçüye özel kalemle karşılanıyorsa yalnız o ürünün gerçek seçenekleri içinde malzeme ve renk seçip Sepete Ekle üzerinden kartla ödeme yapılır.</p>
<h2>Yapılabilirliği güçlendiren ek bilgiler</h2>
<p>Eski bir fotoğrafta parça görünüyorsa görüntüyü kırpmadan gönderin; çevredeki bilinen nesneler yön ve yerleşim hakkında bilgi verir. Cihazın marka-model etiketi, kullanım kılavuzu ve montaj şeması da yardımcı olabilir. Ancak ekrandaki çizime dayanarak kesin boyut söylemeyiz. Her kritik ölçü fiziksel montaj yerinden doğrulanmalıdır.</p>
<p>Parçanın karşılığı hareket ediyorsa açık ve kapalı konumları ayrı fotoğraflayın. Bir kolun ne kadar döndüğü, bir kapağın nereye kadar geldiği veya tırnağın hangi yönde esnediği tasarımı belirler. Vida izleri ve temiz kalmış yüzeyler eski parçanın dış sınırını gösterebilir. Kırık parçadan kalan küçük bir parça bile malzeme kalınlığı ve yüzey biçimi için saklanmalıdır.</p>
<p>Numunesiz işte önce sade ve işlevsel geometri tercih edilir. Dekoratif kıvrımları tahmin etmek yerine montajı ve görevi doğrulamak daha güvenlidir. Görünür yüzey önemliyse prova sonrasında biçim ayrıca düzenlenebilir. İlk parçayı yerine takıp işlevi görmeden çoklu adet istemek riski büyütür. Her belirsizliği açıkça listeler, hangi ölçünün kesin, hangisinin tahmin olduğunu teklif öncesinde ayırırız. Yeterli veri yoksa işi almak yerine ek ölçü isteriz; emniyet kritik parçada tahminle ilerlemeyiz.</p>
<p>İnternet üzerinde bulunan benzer bir görsel yalnız biçim fikri verir; sizin cihazınızdaki ölçünün kanıtı sayılmaz. Ölçeği belli olmayan görüntüden vida aralığı veya kalınlık çıkarılmaz. Servis belgesinde parça adı geçiyorsa onu da ekleyin, fakat son kararı fiziksel yuva ölçüsü belirler. Her ölçünün yanına hangi iki nokta arasında alındığını yazın.</p>
<h2>Doğru malzeme</h2>
<p>Numune olmadığında orijinal malzeme de çoğu kez bilinmez; seçim çalışma yerine göre yapılır. PLA kuru iç mekânda yük almayan prova ve basit kapaklarda, PETG tok genel parçada, ASA güneş gören dış ortamda değerlendirilir. TPU esnek tampon, conta, tutucu veya sönümleme işi için önce düşünülür ve sitedeki seçicide bulunur. Sitedeki standart seçenekler PLA, PETG, ASA ve TPU'dur. PA ile PA-CF ya da PA-GF özel talep olarak WhatsApp'ta değerlendirilir.</p>
<p>Malzeme kadar kesit ve yük yönü de önemlidir. Eski parçanın neden kaybolduğunu bilmiyorsak montajın gevşeme ihtimalini, titreşimi ve sökme yöntemini sorarız. Amaç yalnız boşluğu doldurmak değil, güvenli biçimde aynı yardımcı işlevi sağlamaktır.</p>
<h2>Dürüst sınır</h2>
<p>Referans yoksa bazı geometriler güvenilir biçimde yeniden kurulamaz. Emniyet kritik, insan yükü taşıyan, basınç tutan veya kırılması tehlike doğuran parçayı tahminle üretmeyiz. Hangi işlerin kapsam dışında olduğunu <a href="/hangi-parcalar-ozel-uretimle-yapilamaz/">hangi parçalar özel üretimle yapılamaz</a> sayfasında açıkça listeliyoruz. Ölçü kanıtı yetersizse bunu teklif öncesinde söyleriz.</p>
<p>Isı sınırımız nettir: malzeme sınıfına göre sürekli 90-100 °C bandına kadar çıkabiliriz; üzeri bizim işimiz değildir. Sertifika gerektiren, sürekli gıda temaslı ve düzenli sterilize edilen ekipman için üretim yapmıyoruz; belge vermiyoruz. İçme suyu ya da gıdayla temas eden bir parça söz konusuysa malzeme uygunluğunu kullanım yerine göre birlikte değerlendiririz. Mil, rulman, vida gibi metal elemanı siz temin edersiniz; biz parçayı o elemanın ölçüsüne göre — yuvası, geçme toleransı dahil — tasarlar ve üretiriz.</p>
<h2>Sipariş</h2>
<p>Montaj yerinin fotoğraflarını, ölçü listesini, cihaz bilgisini ve parçanın görevini +90 545 138 6526 numarasına gönderin. Hazır ürün sayfası olmayan bu işte yapılabilirlik ve fiyat önce netleşir; sonra kartla online ödeme yapılır. Onaylanan sipariş 3-5 iş gününde kargoya verilir.</p>""")
CONTENT_PAGES = [
    ("teslimat-iade", "Teslimat ve İade", "PRUVO teslimat, kargo ve iade/cayma hakkı koşulları.", _teslimat_iade),
    ("mesafeli-satis", "Mesafeli Satış Sözleşmesi", "PRUVO mesafeli satış sözleşmesi.", _mesafeli_satis),
    ("malzeme-rehberi", "Malzeme Rehberi",
     "PLA, PETG, ASA ve TPU malzemelerinin karşılaştırması: ısı, güneş (UV), su ve darbe "
     "dayanımı; hangi parçada hangi malzeme önerilir. Mühendislik malzemeleri (ABS, karbon "
     "katkılı) WhatsApp özel talebiyle.", _malzeme_rehberi),
    ("numuneye-gore-plastik-parca-uretimi", "Numuneye Göre Plastik Parça Üretimi",
     "Kırılan ya da bulunamayan parçanızı getirin; ölçüsünü alıp ölçüye özel, doğru "
     "malzemeyle üretelim. Tek adet olur. Online sipariş ve WhatsApp.", _numuneye_gore_plastik_parca_uretimi),
    ("bulunamayan-yedek-parca-ozel-uretim", "Bulunamayan Yedek Parça Özel Üretim",
     'Servis "parça yok" mu dedi? Üretimi durmuş ya da piyasada olmayan parçayı ölçüsüne '
     "göre özel üretiyoruz. Doğru malzeme, tek adet, online sipariş.", _bulunamayan_yedek_parca_ozel_uretim),
    ("beyaz-esya-plastik-parca-uretimi", "Beyaz Eşya Plastik Parça Üretimi",
     "Buzdolabı rafı, çamaşır makinesi menteşesi, sepet tekeri... Kırılan beyaz eşya "
     "plastiğini ölçüsüne göre üretiyoruz. Numune yeter, tek adet.", _beyaz_esya_plastik_parca_uretimi),
    ("oto-ic-trim-klips-parca-uretimi", "Oto İç Trim ve Klips Parça Üretimi",
     "Torpido ızgara klipsi, kapak kolu, iç trim braketi bulunamıyor mu? Kırılan parçayı "
     "numuneden ölçüye özel üretiyoruz. Dayanıklı malzeme, tek adet.", _oto_ic_trim_klips_parca_uretimi),
    ("makine-parcasi-olcuye-ozel-uretim", "Makine Parçası Ölçüye Özel Üretim",
     "Üretimden kalkmış makinenin plastik dişli, kasnak ya da burcu bulunamıyor mu? Numuneden "
     "ölçüye özel, yük durumuna uygun malzemeyle üretelim.", _makine_parcasi_olcuye_ozel_uretim),
    ("tekne-plastik-parca-ozel-uretim-gocek-fethiye", "Tekne Plastik Parça Üretimi | Göcek-Fethiye",
     "Göcek ve Fethiye'de teknenizin kırılan veya bulunamayan plastik parçasını deniz "
     "koşuluna dayanıklı ASA/PETG ile ölçüye özel üretiyoruz.", _tekne_plastik_parca_ozel_uretim_gocek_fethiye),
    ("kisiye-ozel-logolu-kase-yaptirma", "Kişiye Özel Logolu Kaşe Yaptırma",
     "Yazı, logo ya da ikon işlenmiş kaşenizi ölçünüze göre üretiyoruz: dikdörtgen, kare "
     "veya yuvarlak; düz veya kesikli çerçeve, vidalı ayrı sap. Online sipariş.", _kisiye_ozel_logolu_kase_yaptirma),
    ("olcuye-ozel-conta-uretimi", "Ölçüye Özel Conta ve O-ring Üretimi",
     "Orijinali bulunmayan contayı iç çap ve kesit ölçünüze göre üretiyoruz. Yuvarlak, kare, "
     "pahlı profil; kullanım yerine uygun malzeme. Düşük-orta basınç.", _olcuye_ozel_conta_uretimi),
    ("olcuye-ozel-plastik-disli-uretimi", "Ölçüye Özel Plastik Dişli Üretimi",
     "Kırılan ya da aşınan dişlinizi numuneden ölçüye özel üretiyoruz: düz, helis, konik, "
     "sonsuz, kramayer. Yüke göre karbon/cam fiber takviye seçeneği.", _olcuye_ozel_plastik_disli_uretimi),
    ("numuneye-gore-triger-kasnagi-uretimi", "Ölçüye Özel Triger Kasnağı Üretimi",
     "Bulunamayan triger kasnağını profil ve diş sayısına göre üretiyoruz: GT2, HTD, T5/T10, "
     "MXL... Mil tipi ve flanş seçimiyle. Düşük-orta yük için.", _numuneye_gore_triger_kasnagi_uretimi),
    ("numuneden-plastik-burc-rulman-uretimi", "Plastik Burç ve Rulman Yatağı Üretimi",
     "Aşınan burcu ya da rulman yatağını iç/dış çap ve genişlik ölçünüze göre üretiyoruz. "
     "Standart kod ya da özel ölçü. Düşük hız/yük, kuru çalışma.", _numuneden_plastik_burc_rulman_uretimi),
    ('piyasada-bulunmayan-yedek-parca-uretimi', 'Piyasada Bulunmayan Yedek Parça Üretimi', 'Üretimden kalkmış, muadili olmayan ya da hiç ayrı satılmayan parçayı numuneden ölçüye özel üretiyoruz. Tek adet, doğru malzeme. Getir, ölçelim, üretelim.', _piyasada_bulunmayan_yedek_parca_uretimi),
    ('kirik-plastik-parca-yaptirma', 'Kırık Plastik Parçanın Yenisini Yaptırma', 'Kırılan plastik parçayı atmayın; numunesinden ölçüye özel yenisini üretiyoruz. Tek adet, kullanım yerine uygun dayanıklı malzeme. Getir, ölçelim, üretelim.', _kirik_plastik_parca_yaptirma),
    ('tek-adet-ozel-parca-uretimi', 'Tek Adet Özel Plastik Parça Üretimi', 'Tek bir parça mı lazım? Minimum sipariş yok. Numune ya da ölçüden tek adet özel plastik parça üretiyoruz, doğru malzemeyle. Getir, ölçelim, üretelim.', _tek_adet_ozel_parca_uretimi),
    ('olcuye-ozel-baglanti-konektor', 'Ölçüye Özel Bağlantı ve Konektör Üretimi', 'Çubuk ve boruları birleştiren konektörü ölçünüze göre üretiyoruz: 2-4 kol, yuvarlak/kare/sekizgen kesit, çap ve açıya göre. Yük-dışı montaj. Getir, ölç, üret.', _olcuye_ozel_baglanti_konektor),
    ('olcuye-ozel-montaj-braketi', 'Ölçüye Özel Montaj Braketi Üretimi', 'Açılı, köşe, düz, T, L veya Y montaj braketini ölçünüze göre üretiyoruz: iç açı, vida deliği düzeni, sağ/sol simetri. Yük-dışı montaj. Getir, ölç, üret.', _olcuye_ozel_montaj_braketi),
    ('olcuye-ozel-profil-beam', 'Ölçüye Özel Profil, Kızak ve Kiriş Üretimi', 'I, T, L, U, kutu, çokgen ya da sigma profil kesitini ölçünüze göre üretiyoruz. Yükseklik, genişlik, et kalınlığı sizden. Yük-dışı/hafif. Getir, ölç, üret.', _olcuye_ozel_profil_beam),
    ('kasnak-olcuye-ozel-uretim', 'Ölçüye Özel Kasnak Üretimi (V/Düz Kayış)', 'V-kayış, düz kayış ve kordon kasnağını numuneden ölçüye özel üretiyoruz: kanal sayısı, dış çap, mil bağlantısı. Düşük-orta yük/tork. Getir, ölç, üret.', _kasnak_olcuye_ozel_uretim),
    ('olcuye-ozel-vida-somun-civata-uretimi', 'Ölçüye Özel Vida, Somun ve Cıvata Üretimi', 'Cıvata, dişli mil, somun ve pulu ölçünüze göre üretiyoruz: metrik/inç/özel diş, kafa ve tornavida ağzı, trapez hareket vidası. Hafif-orta yük. Getir, ölç, üret.', _olcuye_ozel_vida_somun_civata_uretimi),
    ('olcuye-ozel-yay-uretimi', 'Ölçüye Özel Plastik Yay Üretimi', 'Bası yayı ya da dalga/flexure elemanını ölçünüze göre üretiyoruz: serbest boy, dış çap, tel çapı, sarım. Hafif kuvvet/geri dönüş işleri. Getir, ölçelim, üretelim.', _olcuye_ozel_yay_uretimi),
    ('elektronik-cihaz-plastik-parca-uretimi', 'Elektronik Cihaz Plastik Parça Üretimi', "Kırılan düğme, klips, kapak, tutamak ya da muhafazayı numuneden ölçüye özel üretiyoruz. Isı ve UV'ye dayanıklı malzeme. Tek adet. Getir, ölçelim, üretelim.", _elektronik_cihaz_plastik_parca_uretimi),
    ('motosiklet-plastik-parca-ozel-uretim', 'Motosiklet Plastik Parça Özel Üretim', 'Grenaj klipsi, ayna kapağı, muhafaza ya da braket bulunamıyor mu? Motosiklet plastik parçasını numuneden ölçüye özel üretiyoruz. UV/ısıya dayanıklı, tek adet.', _motosiklet_plastik_parca_ozel_uretim),
    ('olcuye-ozel-huni-uretimi', 'Ölçüye Özel Huni Üretimi — Dolum ve Mutfak', 'Mutfak, yağ-yakıt dolumu ya da dar ağızlar için huniyi ölçünüze göre üretiyoruz: ağız çapı, akıtma ucu, açılı uç, glık-glık önleyici hava kanalı. Getir, ölç, üret.', _olcuye_ozel_huni_uretimi),
    ('olcuye-ozel-izgara-petek-uretimi', 'Ölçüye Özel Izgara, Menfez ve Petek Üretimi', 'Havalandırma menfezi, fan kapağı, filtre ızgarası ya da petek paneli boşluğunuza göre üretiyoruz: panjur/delikli/kör, göz şekli, geçmeli ya da vidalı. Getir, ölç, üret.', _olcuye_ozel_izgara_petek_uretimi),
    ('olcuye-ozel-klips-kelepce-uretimi', 'Ölçüye Özel Klips ve Kelepçe Üretimi', 'Kırılan klips ya da bulunamayan boru/kablo kelepçesini ölçünüze göre üretiyoruz: çap, genişlik, açık/kapalı tip, geçme sıkılığı. Yük-dışı. Getir, ölç, üret.', _olcuye_ozel_klips_kelepce_uretimi),
    ('olcuye-ozel-kablo-kanali-organizer-uretimi', 'Ölçüye Özel Kablo Kanalı ve Organizer', 'Masa, pano ya da araç için kablo kanalını ve organizerı ölçünüze göre üretiyoruz: genişlik, kanal sayısı, kapaklı/açık, montaj tipi. Hafif kullanım. Getir, ölç, üret.', _olcuye_ozel_kablo_kanali_organizer_uretimi),
    ('olcuye-ozel-mentese-uretimi', 'Ölçüye Özel Plastik Menteşe Üretimi', 'Kırılan ya da bulunamayan menteşeyi ölçünüze göre üretiyoruz: kanat boyu, pim çapı, delik düzeni, açılım açısı. Yük-dışı/düşük-orta. Getir, ölç, üret.', _olcuye_ozel_mentese_uretimi),
    ('olcuye-ozel-kulp-tutamak-uretimi', 'Ölçüye Özel Kulp ve Tutamak Üretimi', 'Kırılan çekmece kulpunu, dolap tutamağını ya da cihaz kolunu ölçünüze göre üretiyoruz: delik mesafesi, form, vida ölçüsü. Hafif kullanım. Getir, ölç, üret.', _olcuye_ozel_kulp_tutamak_uretimi),
    ('olcuye-ozel-tapa-kapak-uretimi', 'Ölçüye Özel Tapa, Kapak ve Tıkaç Üretimi', 'Boru, profil ya da haznenin kayıp tapasını/kapağını ölçünüze göre üretiyoruz: iç/dış çap, geçme sıkılığı, vidalı ya da geçmeli. Hafif kullanım. Getir, ölç, üret.', _olcuye_ozel_tapa_kapak_uretimi),
    ('tarim-makinesi-plastik-parca-uretimi', 'Tarım Makinesi Plastik Parça Üretimi', 'Traktör, çapa, biçme, ilaçlama ya da bahçe makinesinin bulunamayan plastik parçasını numuneden ölçüye özel üretiyoruz. UV ve dış koşula dayanıklı malzeme.', _tarim_makinesi_plastik_parca_uretimi),
    ('mobilya-plastik-baglanti-ayak-parca-uretimi', 'Mobilya Plastik Bağlantı ve Ayak Parçası', 'Kırılan mobilya bağlantısını, ayağını, kayar pabucunu ya da geçme parçasını ölçünüze göre üretiyoruz. Numune yeter, tek adet. Getir, ölç, üret.', _mobilya_plastik_baglanti_ayak_parca_uretimi),
    ('drone-rc-model-plastik-parca-uretimi', 'Drone ve RC Model Plastik Parça Üretimi', 'Kırılan drone gövdesi, motor kolu, iniş takımı ya da RC model parçasını numuneden ölçüye özel üretiyoruz. Hafif ve dayanıklı malzeme. Getir, ölç, üret.', _drone_rc_model_plastik_parca_uretimi),
    ('ev-aleti-plastik-disli-parca-uretimi', 'Ev Aleti Plastik Dişli ve Parça Üretimi', 'Mutfak robotu, blender, kıyma makinesi ya da mikserin kırılan plastik dişlisini ve parçasını numuneden ölçüye özel üretiyoruz. Yüke göre takviyeli malzeme.', _ev_aleti_plastik_disli_parca_uretimi),
    ('olcuye-ozel-cetvel-mastar-sablon-uretimi', 'Ölçüye Özel Cetvel, Gönye ve Mastar Üretimi', 'Cetvel, gönye ve ölçü mastarını boyunuza göre üretiyoruz: metrik/inç, kabartma ya da oyma taksimat, tek/çift yüz, isim-logo işlenir. Getir, ölç, üret.', _olcuye_ozel_cetvel_mastar_sablon_uretimi),
    ('olcuye-ozel-koruma-kapagi-muhafaza-uretimi', 'Ölçüye Özel Koruma Kapağı ve Muhafaza Üretimi', 'Dişli, kayış, terminal, sensör ya da bağlantıyı toz ve darbeden koruyan kapak ve muhafazayı ölçünüze göre üretiyoruz. Yük-dışı koruma. Getir, ölç, üret.', _olcuye_ozel_koruma_kapagi_muhafaza_uretimi),
    ('olcuye-ozel-adaptor-reduksiyon-gecis-uretimi', 'Ölçüye Özel Adaptör, Redüksiyon ve Geçiş Üretimi', 'İki farklı çapı birleştiren adaptör, redüksiyon ve geçiş parçasını ölçünüze göre üretiyoruz: giriş/çıkış çapı, geçmeli ya da dişli. Düşük-orta basınç.', _olcuye_ozel_adaptor_reduksiyon_gecis_uretimi),
    ('bisiklet-plastik-parca-ozel-uretim', 'Bisiklet Plastik Parça ve Aksesuar Özel Üretimi', 'Kırılan ya da bulunamayan bisiklet plastik parçasını numuneden ölçüye özel üretiyoruz: çamurluk bağlantısı, şişelik, kablo yönlendirici, klips. Getir, ölç, üret.', _bisiklet_plastik_parca_ozel_uretim),
    ('kamera-optik-aksesuar-plastik-parca-uretimi', 'Kamera ve Optik Aksesuar Plastik Parça Üretimi', 'Kırılan kamera, tripod ya da optik aksesuar plastik parçasını numuneden ölçüye özel üretiyoruz: pil kapağı, ayak bağlantısı, flaş kızağı, lens parası.', _kamera_optik_aksesuar_plastik_parca_uretimi),
    ('oyuncak-hobi-model-plastik-parca-uretimi', 'Oyuncak, Hobi ve Maket Plastik Parça Üretimi', 'Kırılan ya da kaybolan oyuncak, kutu oyunu, maket ve koleksiyon parçasını numuneden ölçüye özel üretiyoruz. Tek adet olur. Getir, ölç, üret.', _oyuncak_hobi_model_plastik_parca_uretimi),
    ('klima-kombi-havalandirma-plastik-parca-uretimi', 'Klima, Kombi ve Havalandırma Plastik Parça Üretimi', 'Klima, kombi ya da havalandırma cihazının kırılan plastik parçasını numuneden ölçüye özel üretiyoruz: kanat, panjur, drenaj, klips. Isı sınırını açık söyleriz.', _klima_kombi_havalandirma_plastik_parca_uretimi),
    ('aydinlatma-armatur-plastik-parca-uretimi', 'Aydınlatma ve Armatür Plastik Parça Üretimi', 'Avize, spot, armatür ya da lamba plastik parçasını numuneden ölçüye özel üretiyoruz: soket tutucu, difüzör klipsi, montaj halkası, kapak. Isıya yakınlık sınırı.', _aydinlatma_armatur_plastik_parca_uretimi),
    ('ofis-ekipmani-plastik-parca-uretimi', 'Ofis Makinesi ve Ekipmanı Plastik Parça Üretimi', 'Fotokopi, evrak imha, laminasyon ya da ofis koltuğu mekanizmasının kırılan plastik parçasını numuneden ölçüye özel üretiyoruz. Tek adet olur. Getir, ölç, üret.', _ofis_ekipmani_plastik_parca_uretimi),
    ('muzik-enstruman-plastik-parca-uretimi', 'Müzik Enstrümanı Plastik Parça Özel Üretimi', 'Gitar, nefesli ya da klavye enstrümanının kırılan plastik parçasını numuneden ölçüye özel üretiyoruz: akort düğmesi, tuş, klips, dayama. Getir, ölç, üret.', _muzik_enstruman_plastik_parca_uretimi),
    ('akvaryum-terraryum-plastik-parca-uretimi', 'Akvaryum ve Teraryum Plastik Parça Üretimi', 'Akvaryum ya da teraryumun kırılan plastik parçasını numuneden ölçüye özel üretiyoruz: filtre klipsi, çıkış borusu, kapak menteşesi, hortum tutucu. Suya dayanıklı.', _akvaryum_terraryum_plastik_parca_uretimi),
    ('pvc-dograma-kapi-pencere-plastik-parca-uretimi', 'PVC Pencere ve Kapı Plastik Yedek Parça Üretimi', 'Kırılan ispanyolet kapağı, sineklik mandalı, panjur makarası ve köşe takozunu numuneden ölçüp aynı ölçüde yeniden üretiyoruz. Ölçü sizden, üretim bizden.', _pvc_dograma_kapi_pencere_plastik_parca_uretimi),
    ('olcuye-ozel-dugme-ayar-topuzu-uretimi', 'Cihaz Düğmesi ve Ayar Topuzu Ölçüye Özel Üretim', 'Ocak, fırın, radyo ve tezgah düğmesi kırıldıysa mil profilini ölçüp aynı ölçüde üretiyoruz. D-mil, tırtıllı, kare mil ve farklı renk seçenekleri sizin.', _olcuye_ozel_dugme_ayar_topuzu_uretimi),
    ('olcuye-ozel-fan-carki-uretimi', 'Ölçüye Özel Fan Çarkı ve Kanat Üretimi', 'Kırılan fan çarkını dış çap, kanat sayısı ve mil ölçüsüne göre birebir üretiyoruz. Havalandırma ve soğutma içindir; tekne itişi ya da pompa çarkı işi yapmaz.', _olcuye_ozel_fan_carki_uretimi),
    ('olcuye-ozel-tekerlek-makara-uretimi', 'Plastik Tekerlek ve Makara Ölçüye Özel Üretim', 'Çekmece, sepet, sürgü ve valiz tekerleğini çap, kanal ve aks ölçüsüne göre üretiyoruz. Hafif-orta yük içindir; ağır yükte takviyeli malzemeye çıkarız.', _olcuye_ozel_tekerlek_makara_uretimi),
    ('karavan-plastik-parca-ozel-uretim', 'Karavan Plastik Yedek Parça Özel Üretimi', 'Karavan dolap mandalı, perde rayı ucu ve havalandırma kapağı gibi bulunamayan parçaları ölçüye özel üretiyoruz. Tek adet olur, güneş gören yüzeye ASA.', _karavan_plastik_parca_ozel_uretim),
    ('tekstil-makinesi-plastik-parca-uretimi', 'Tekstil Makinesi Plastik Parça Ölçüye Özel Üretim', 'Masura, iplik kılavuzu, burç ve kızak takozu gibi tekstil makinesi plastiklerini numuneden ölçüye özel üretiyoruz. Tek adet ve düşük adetli seri olur.', _tekstil_makinesi_plastik_parca_uretimi),
    ('elektrikli-scooter-plastik-parca-uretimi', 'Elektrikli Scooter Plastik Yedek Parça Üretimi', 'Elektrikli scooter çamurluğu, gidon kapağı, şarj kapağı ve mandalı ölçüye özel üretiyoruz. Fren ve şasi parçaları kapsam dışı; sınırımızı açıkça söyleriz.', _elektrikli_scooter_plastik_parca_uretimi),
    ('isiya-dayanikli-plastik-parca-uretimi', 'Isıya Dayanıklı Plastik Parça Üretimi', 'Fırın çevresi, motor bölmesi ve kombi yakınındaki sıcak noktalar için ısıya dayanıklı parça üretiyoruz. PETG, ASA ve takviyeli sınıf; sınırını söyleriz.', _isiya_dayanikli_plastik_parca_uretimi),
    ('uv-gunes-dayanikli-dis-mekan-plastik-parca-uretimi', 'Güneşe Dayanıklı Dış Mekan Plastik Parça Üretimi', 'Güneşte sararıp kırılan balkon, bahçe, çatı ve tente parçalarını UV dayanımlı ASA ile ölçüye özel yeniden üretiyoruz. Ölçü sizden, üretim bizden.', _uv_gunes_dayanikli_dis_mekan_plastik_parca_uretimi),
    ('parca-olcusu-nasil-alinir-ve-gonderilir', 'Parça Ölçüsü Nasıl Alınır ve Nasıl Gönderilir', 'Özel üretim için hangi ölçüler gerekir? Kumpas yoksa cetvelle nasıl ölçülür, kırık parça nasıl ölçülür, hangi beş ölçü her parçada şarttır: adım adım.', _parca_olcusu_nasil_alinir_ve_gonderilir),
    ('ozel-parca-uretimi-fiyati-nasil-belirlenir', 'Özel Parça Üretimi Fiyatı Nasıl Belirlenir', 'Özel parça üretiminde fiyatı ne belirler? Boyut, malzeme sınıfı, dayanım, adet ve ölçü girdisi. Şeffaf anlatım, net teklif; kartla ödeme sitede yapılır.', _ozel_parca_uretimi_fiyati_nasil_belirlenir),
    ('olcuye-ozel-distans-ara-pul-uretimi', 'Ölçüye Özel Distans ve Ara Pul Üretimi (İç/Dış Çap)', 'İç çap, dış çap ve kalınlık sizden: kırılan ara pulu, distansı ve rondelayı ölçünüze göre üretiyoruz. Numunenizi ya da ölçülerinizi gönderin, net fiyatını alın.', _olcuye_ozel_distans_ara_pul_uretimi),
    ('olcuye-ozel-raf-pimi-tutucu-uretimi', 'Dolap Raf Pimi ve Raf Tutucusu Ölçüye Özel Üretim', 'Dolap rafınız oynuyor ya da pim kırıldı mı? Delik çapına göre raf pimini ölçünüze özel üretiyoruz. Ölçüyü gönderin, üretelim. Kartla ödeme var.', _olcuye_ozel_raf_pimi_tutucu_uretimi),
    ('olcuye-ozel-mandal-kilit-dili-uretimi', 'Kırık Mandal Dili ve Kilit Mandalı Ölçüye Özel Üretim', 'Kırık mandal parçası yaptırma: dolap kapağı mandal dili, alet çantası mandalı ve karşı tırnağı ölçünüze göre üretiyoruz. Numuneyi gönderin, fiyatı öğrenin.', _olcuye_ozel_mandal_kilit_dili_uretimi),
    ('dus-kabini-banyo-plastik-parca-uretimi', 'Duş Kabini Makarası ve Banyo Plastik Parçası Üretimi', 'Duş kabini makarası, kılavuzu veya fitil tutucusu kırıldığında kabini komple değiştirmeyin. Numunenize göre ölçüye özel üretiyoruz; kartla sipariş verin.', _dus_kabini_banyo_plastik_parca_uretimi),
    ('stor-jaluzi-perde-mekanizma-parcasi-uretimi', 'Stor ve Jaluzi Perde Mekanizma Parçası Özel Üretim', "Stor, jaluzi ve zebra perdenin kırılan yan kapağı, zincir kasnağı, boru tapası ve braketi elinizdeki örnekten ölçülüp özel üretilir. Ölçünüzü WhatsApp'tan iletin.", _stor_jaluzi_perde_mekanizma_parcasi_uretimi),
    ('spor-salonu-fitness-ekipmani-plastik-parca-uretimi', 'Fitness Aleti Plastik Yedek Parçası Ölçüye Özel Üretim', 'Kondisyon ve spor salonu aletlerinin kırılan yan kapak, makara kılıfı, pim yuvası ve ayak pabucunu ölçünüze özel üretiyoruz. Örneği gönderin, fiyatı yazalım.', _spor_salonu_fitness_ekipmani_plastik_parca_uretimi),
    ('ticari-arac-kamyon-plastik-parca-ozel-uretim', 'Kamyon ve Ticari Araç Plastik Parçası Ölçüye Özel Üretim', 'Kamyon, kamyonet ve minibüs kabininde bulunamayan havalandırma ızgarası, torpido kapağı ve kaplama klipsini ölçünüze göre üretiyoruz. Kartla sipariş verin.', _ticari_arac_kamyon_plastik_parca_ozel_uretim),
    ('elektrikli-supurge-aparati-plastik-parca-uretimi', 'Elektrikli Süpürge Aparatı ve Yedek Plastik Parça Üretimi', 'Süpürge hortum bağlantı bileziği, kilit tırnağı ya da fırça kapağı kırıldıysa cihazı atmayın: elinizdeki kırık örnekten ölçü alıp ölçünüze özel üretiyoruz.', _elektrikli_supurge_aparati_plastik_parca_uretimi),
    ('asinmaya-dayanikli-surtunme-parcasi-uretimi', 'Aşınmaya Dayanıklı Sürtünme Parçası Ölçüye Özel Üretim', 'Sürtünen kızak, kılavuz ve yatak yüzeyi boşluk mu yaptı? Aşınmaya dayanıklı sınıfta, ölçünüze göre üretiyoruz. Numuneyi gönderin, geçme payını belirleyelim.', _asinmaya_dayanikli_surtunme_parcasi_uretimi),
    ('yaga-ve-kimyasala-dayanikli-plastik-parca-uretimi', 'Yağa ve Kimyasala Dayanıklı Plastik Parça Özel Üretim', 'Yağ, solvent ve temizlik kimyasalı değince yumuşayan parçayı; temas ettiği sıvı ve sıcaklığa uygun sınıfta, ölçünüze göre üretiyoruz. Numunenizi gönderin.', _yaga_ve_kimyasala_dayanikli_plastik_parca_uretimi),
    ('kalip-yaptirmadan-parca-urettirme', 'Kalıp Yaptırmadan Az Adet Parça Ürettirme Yolu', "Kalıp masrafına girmeden 1-200 adet parça ürettirin: numuneyle ya da ölçüyle üretim, ölçü kaydından tekrar sipariş. Kartla ödeyin ya da WhatsApp'tan yazın.", _kalip_yaptirmadan_parca_urettirme),
    ('plastik-pim-yaptirma', 'Plastik Pim Yaptırma: Ölçüye Özel Çap ve Boy Üretimi', 'Kırılan ya da kaybolan plastik pim mi arıyorsunuz? Çapı, boyu ve uç formunu ölçünüze göre üretiyoruz. Kumpas değerlerinizi gönderin, geçme payıyla üretelim.', _plastik_pim_yaptirma),
    ('kirik-plastik-tirnak-yaptirma', 'Kırık Plastik Tırnak Yaptırma: Geçme Tırnak Üretimi', 'Kapak veya panelde geçme tırnak kırıldıysa gövdeyi değiştirmeyin: tırnak yüksekliği, kök kalınlığı ve esneme payını ölçünüze göre üretiyoruz. Ölçünüzü gönderin.', _kirik_plastik_tirnak_yaptirma),
    ('cekmece-rayi-plastik-parcasi-yaptirma', 'Çekmece Rayı Plastik Parçası Yaptırma', 'Kırılan çekmece rayı durdurucusu, kızak dili veya makarası numuneden birebir ölçüyle üretilir. Rayın tamamını almadan tek parçayı yenileyin; ölçünüzü yazın.', _cekmece_rayi_plastik_parcasi_yaptirma),
    ('plastik-stoper-durdurucu-yaptirma', 'Plastik Stoper Yaptırma: Ölçüye Özel', 'Aşınan ya da kırılan stoper yüzünden tüm mekanizmayı değiştirmeyin. Hareket durdurucuyu yükseklik, çap ve vida deliği ölçüsüyle üretiyoruz; ölçünüzü iletin.', _plastik_stoper_durdurucu_yaptirma),
    ('konveyor-bant-plastik-parca-yaptirma', 'Konveyör Bant Plastik Parçası Yaptırma', 'Konveyör kılavuz çıtası, yan tutucu, kızak ve makara gövdesi numuneden ölçüye özel üretilir. Kanal, yarıçap, delik aralığı sizden; ölçü gönderin, üretelim.', _konveyor_bant_plastik_parca_yaptirma),
    ('havuz-ekipmani-plastik-parca-yaptirma', 'Havuz Ekipmanı Plastik Parça Yaptırma', 'Havuz süpürgesi tekerleği, skimmer kapak mandalı, merdiven tutucusu: kırık numuneden ölçüye özel üretiyoruz. Klor ve güneşe göre sınıf seçeriz. Ölçünüzü yazın.', _havuz_ekipmani_plastik_parca_yaptirma),
    ('cam-krikosu-plastik-parcasi-yaptirma', 'Cam Krikosu Plastik Parçası Yaptırma', 'Cam inip kalkmıyorsa arıza çoğu zaman motorda değil, kırılan plastik kızak ve tutucudadır. Numunenizden ölçüye özel yenisini üretiyoruz; ölçünüzü bize iletin.', _cam_krikosu_plastik_parcasi_yaptirma),
    ('darbeye-dayanikli-plastik-parca-yaptirma', 'Darbeye Dayanıklı Plastik Parça Yaptırma', 'Aynı plastik parça hep aynı yerden mi kırılıyor? Darbeye dayanıklı plastik parça yaptırma için malzeme sınıfını ve kesiti birlikte seçelim, ölçünüzü gönderin.', _darbeye_dayanikli_plastik_parca_yaptirma),
    ('cim-bicme-bahce-makinesi-plastik-parca-yaptirma', 'Çim Biçme Makinesi Plastik Parça Yaptırma', 'Çim biçme makinesinin tekerlek göbeği, ayar kolu ya da misina kafası tutucusu kırıldıysa numunenizden tekil üretiyoruz. Ölçüyü gönderin, siparişi verin.', _cim_bicme_bahce_makinesi_plastik_parca_yaptirma),
    ('ozel-parca-kac-gunde-hazir-olur', 'Özel Üretim Parça Kaç Günde Hazır Olur?', 'Özel üretim parça kaç günde hazır olur? Ölçü onayından sonra 3-5 iş günü içinde kargoya verilir: hangi kademe neyi bekletir, süreyi ne uzatır. Ölçünüzü iletin.', _ozel_parca_kac_gunde_hazir_olur),
    ('plastik-parcaya-vida-disi-acilir-mi', 'Plastik Parçaya Vida Dişi Açılır mı?', 'Plastik parçaya vida dişi açılır mı? Diş sıyrılmasına karşı metal gömme somun, diş boyu ve cidar kalınlığını ölçünüze göre ayarlıyoruz. Ölçünüzü iletin.', _plastik_parcaya_vida_disi_acilir_mi),
    ('hangi-parcalar-ozel-uretimle-yapilamaz', 'Hangi Parçalar Özel Üretimle Yapılamaz?', 'Her parça ölçüye özel üretilemez. Yük taşıyan, yüksek basınçlı ve sürekli sıcak çalışan parçalarda sınırımızı, doğru malzeme seçimini dürüstçe anlattık.', _hangi_parcalar_ozel_uretimle_yapilamaz),
    ('karbon-fiber-takviyeli-naylon-parca-ne-zaman-gerekir', 'Karbon Fiber Takviyeli Naylon Ne Zaman Gerekir?', 'Karbon fiber takviyeli naylon parça ne zaman gerekir? Beş soruyla PA-CF ve PA-GF sınıfına gerçekten ihtiyacınız var mı anlayın; malzeme sıralaması ve sınırlar.', _karbon_fiber_takviyeli_naylon_parca_ne_zaman_gerekir),
    ('kaseye-islenecek-logo-dosyasi-nasil-hazirlanir', 'Kaşe Logosu İçin Dosya Nasıl Hazırlanır?', 'Kaşeye logo işlenmesi için dosya SVG mi PNG mi olmalı? Gönderdiğiniz logonun işlenebilir olup olmadığını önceden anlayın, doğru dosyayla sipariş verin.', _kaseye_islenecek_logo_dosyasi_nasil_hazirlanir),
    ('kayis-profili-nasil-belirlenir-gt2-htd-t5', 'Kayış Profili Nasıl Anlaşılır? GT2, HTD, T5 Ölçüsü', 'Kopan kayışın profilini iki diş arası mesafeyi ölçerek belirleyin: GT2, HTD ve T5 farkı, diş adımı ölçme adımları ve aynı profilde ölçüye özel kasnak üretimi.', _kayis_profili_nasil_belirlenir_gt2_htd_t5),
    ('kirik-dislinin-modulu-nasil-bulunur', 'Kırık Dişlinin Modülü Nasıl Bulunur? Ölçü Rehberi', 'Kırık dişlinin modülü nasıl bulunur? Dış çapı ölçüp diş sayısı artı ikiye bölerek modülü hesaplayın, eşleşen dişliyi ölçüye özel ürettirin. Ölçü listesi ve malzeme.', _kirik_dislinin_modulu_nasil_bulunur),
    ('klasik-arac-eski-model-oto-plastik-parca-uretimi', 'Eski Model Araç Plastik Parçası Özel Üretim', 'Üretimden kalkmış eski model araç plastik parçasını örneğinizin ölçüsüne göre üretiyoruz: kapı döşeme klipsi, kolçak yuvası, ızgara tırnağı, kumanda düğmesi.', _klasik_arac_eski_model_oto_plastik_parca_uretimi),
    ('plastik-kaplin-gobegi-esnek-kavrama-uretimi', 'Kaplin Göbeği Ölçüye Özel Plastik Üretim', 'Kaplin göbeği yaptırma: yıldız kavrama göbeği bulunamıyorsa mil çapını ve tırnak sayısını ölçün, ölçüye özel esnek kavrama parçasını üretelim. Ölçü listesi içeride.', _plastik_kaplin_gobegi_esnek_kavrama_uretimi),
    ('sicak-su-ve-buhar-temasli-plastik-parca-uretimi', 'Sıcak Su ve Buhara Dayanıklı Parça Üretimi', 'Bulaşık makinesi, su ısıtıcısı ve buharlı ekipmanda sıcak su ile buhar gören plastik parçayı ölçüye özel üretiyoruz. Çalışma koşulunuza göre PETG ve ASA seçenekleri.', _sicak_su_ve_buhar_temasli_plastik_parca_uretimi),
    ('sut-sagim-hayvancilik-ekipmani-plastik-parca-uretimi', 'Süt Sağım ve Hayvancılık Ekipmanı Parçası', 'Süt sağım makinesi plastik parçası, suluk-yemlik tutucusu ve padok ekipmanı bağlantısı ölçüye özel üretilir. Kırık parçanızı ölçer, doğru malzemeyle yaparız.', _sut_sagim_hayvancilik_ekipmani_plastik_parca_uretimi),
    ('tekne-tentesi-bimini-guverte-aparati-ozel-uretim', 'Tekne Tentesi ve Bimini Aparatı Özel Üretim', 'Kırılan bimini bağlantı aparatı, guverte tutucusu veya tente askı parçası bulunamıyorsa ölçüsüne göre üretiyoruz. UV ve tuzlu havaya dayanıklı malzeme, net teslim.', _tekne_tentesi_bimini_guverte_aparati_ozel_uretim),
    ('yedek-parca-kodu-bilinmiyorsa-ne-yapilir', 'Yedek Parça Kodu Bilinmiyorsa Ne Yapılır?', 'Yedek parça kodu bilinmiyor mu? Etiket ve kod nerede aranır, kod hiç çıkmazsa parçanın ölçüsüyle eşi nasıl ürettirilir; adım adım ölçü listesi ve malzeme rehberi.', _yedek_parca_kodu_bilinmiyorsa_ne_yapilir),
    ('olcuye-ozel-seviye-simi-ve-takoz-uretimi', 'Ölçüye Özel Seviye Şimi ve Takoz Üretimi', 'Eğimli seviye şimi, makine ayağı takozu veya kapı rampasını en, boy, yükseklik ve yüzey tercihlerinize göre üretiyoruz; sınırlar ve sipariş akışı içeride.', _olcuye_ozel_seviye_simi_ve_takoz_uretimi),
    ('olcuye-ozel-kramayer-disli-uretimi', 'Ölçüye Özel Kramayer Dişli Üretimi', 'Doğrusal hareket için kramayer dişliyi modül, diş sayısı, kalınlık ve karşı dişli bilgisine göre üretiyoruz; uyum ölçüleri, malzeme ve sipariş adımları.', _olcuye_ozel_kramayer_disli_uretimi),
    ('paketleme-makinesi-plastik-yedek-parca-yaptirma', 'Paketleme Makinesi Plastik Yedek Parçası', 'Paketleme makinesindeki kırık kılavuz, düğme, kapak, burç veya kayış çevresi parçasını numuneye ve çalışma yerine göre ölçüye özel üretiyoruz; süreç içeride.', _paketleme_makinesi_plastik_yedek_parca_yaptirma),
    ('tarimsal-sulama-ekipmani-plastik-parca-yaptirma', 'Tarımsal Sulama Ekipmanı Plastik Parçası', 'Sulama ekipmanındaki kırık kelepçe, vana kolu, filtre kapağı tutucusu veya hortum kılavuzunu kullanım koşuluna göre ölçüye özel üretiyoruz; sınırlar içeride.', _tarimsal_sulama_ekipmani_plastik_parca_yaptirma),
    ('tekne-kabin-dolap-mandali-yaptirma', 'Tekne Kabin Dolap Mandalı Özel Üretim', 'Tekne kabinindeki kırık dolap mandalı, kapak karşılığı, tutamak veya ray ucunu montaj ölçüsüne göre üretiyoruz; deniz koşulu, sınırlar ve sipariş adımları.', _tekne_kabin_dolap_mandali_yaptirma),
    ('titresim-sonumleyici-esnek-plastik-parca-yaptirma', 'Titreşim Sönümleyici Esnek Plastik Parça', 'Titreşimi azaltan esnek tampon, ayak, ara parça veya kavrama göbeğini ölçüye ve hareket koşuluna göre üretiyoruz; TPU seçimi, sınırlar ve sipariş akışı.', _titresim_sonumleyici_esnek_plastik_parca_yaptirma),
    ('oto-havalandirma-izgara-klipsi-yaptirma', 'Oto Havalandırma Izgara Klipsi Üretimi', 'Kırık oto havalandırma kanadı, yönlendirme klipsi veya ayar düğmesini sağlam eş parça ve yuva ölçüsüne göre üretiyoruz; malzeme, sınır ve sipariş bilgisi.', _oto_havalandirma_izgara_klipsi_yaptirma),
    ('bulasik-makinesi-sepet-tekerlegi-yaptirma', 'Bulaşık Makinesi Sepet Tekeri Üretimi', 'Kırık bulaşık makinesi sepet tekerini, aks klipsini veya ray taşıyıcısını numune ölçüsüne göre üretiyoruz; sıcak su, deterjan ve yük sınırları içeride.', _bulasik_makinesi_sepet_tekerlegi_yaptirma),
    ('ozel-parcaya-logo-ve-yazi-isleme', 'Özel Parçaya Logo ve Yazı İşleme', 'Ölçüye özel parçaya logo, isim, kısa metin, yön oku veya parça kodu işliyoruz; okunaklı dosya hazırlığı, yüzey seçimi, net sınırlar ve sipariş adımları.', _ozel_parcaya_logo_ve_yazi_isleme),
    ('mil-rulman-icin-olcuye-ozel-plastik-yuva', 'Mil ve Rulman İçin Ölçüye Özel Plastik Yuva', 'Elinizdeki mil veya rulmana uygun plastik yuva, taşıyıcı ve mesnedi iç-dış ölçü, geçme toleransı ve montaj deliklerine göre özel üretiyoruz; süreç içeride.', _mil_rulman_icin_olcuye_ozel_plastik_yuva),
    ('numune-olmadan-plastik-parca-yaptirilir-mi', 'Numune Olmadan Plastik Parça Yaptırılır mı?', 'Kırık parça tamamen kayıpsa montaj yeri, karşı parça, fotoğraf ve kritik ölçülerle üretim mümkün mü? Gerekli bilgileri, sınırları ve sipariş yolunu anlattık.', _numune_olmadan_plastik_parca_yaptirilir_mi),
]

# Statik içerik/yasal sayfalar: elle yazılmış, build.py ÜRETMEZ (repo'da commit'li), korunur.
STATIK_SAYFALAR = ["hakkimizda", "iletisim", "sss", "gizlilik"]

# sitemap + deploy.yml yayın-beyaz-listesi için TÜM içerik/yasal slug'lar (statik + ÜRETİLEN).
# Üretilen kısım CONTENT_PAGES'ten TÜRETİLİR = TEK KAYNAK: CONTENT_PAGES'e sayfa eklemek
# sitemap'e VE yayın manifestine (build.py _yayin-icerik-dizinleri.txt) otomatik yansır.
# Eskiden bu liste elle tutuluyordu -> CONTENT_PAGES'e eklenip buraya eklenmeyen sayfa
# sitemap dışı kalıp yayına girmiyordu (sessiz 404). Artık senkron elle DEĞİL.
SITEMAP_SLUGS = STATIK_SAYFALAR + [slug for slug, _baslik, _meta, _fn in CONTENT_PAGES]

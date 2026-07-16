/**
 * Parametrik ("olcuye ozel" sari seri) urun semalari — Worker bundle'ina STATIK import.
 *
 * NEDEN ELLE LISTE: Worker'da dosya sistemi/glob YOK; wrangler(esbuild) sadece statik
 * import'lari bundle'a katar. Bu liste jenerator/urunler/ ile ELDE senkron tutulur.
 * BAYATLAMA KORUMASI: kabul testi 9, bu haritanin jenerator/urunler/*.json ile BIREBIR
 * ortustugunu dogrular — yeni sema eklenip burasi guncellenmezse test KIRMIZI yanar
 * (sessizce "sema yok -> odeme reddi" davranisina dusmez).
 *
 * Semalar public veri (matematik + aralik); sir icermez (gizlilik: Koolm izi yok).
 */

import jeton from "../../jenerator/urunler/kisiye-ozel-jeton-cip-madalyon.json";
import konektor from "../../jenerator/urunler/olcuye-ozel-baglanti-konektor.json";
import cetvel from "../../jenerator/urunler/olcuye-ozel-cetvel.json";
import kase from "../../jenerator/urunler/olcuye-ozel-damga-kase.json";
import huni from "../../jenerator/urunler/olcuye-ozel-huni.json";
import izgara from "../../jenerator/urunler/olcuye-ozel-izgara-menfez-kapak.json";
import braket from "../../jenerator/urunler/olcuye-ozel-montaj-braketi.json";
import oring from "../../jenerator/urunler/olcuye-ozel-oring-conta.json";
import pervane from "../../jenerator/urunler/olcuye-ozel-pervane-fan-cark.json";
import petek from "../../jenerator/urunler/olcuye-ozel-petek-delikli-panel.json";
import profil from "../../jenerator/urunler/olcuye-ozel-profil-beam.json";
import ramp from "../../jenerator/urunler/olcuye-ozel-ramp-sim-takoz.json";
import rulman from "../../jenerator/urunler/olcuye-ozel-rulman.json";
import kasnak from "../../jenerator/urunler/olcuye-ozel-triger-kasnagi.json";
import kayis from "../../jenerator/urunler/olcuye-ozel-triger-kayisi.json";
import vida from "../../jenerator/urunler/olcuye-ozel-vida-civata-somun-pul.json";
import yay from "../../jenerator/urunler/olcuye-ozel-yay-dalga-flexure.json";
import disli from "../../jenerator/urunler/ozel-disli-kramayer-uretimi.json";
// Yeni sari aileler 1. dalga (2026-07-17)
import adaptor from "../../jenerator/urunler/olcuye-ozel-hortum-adaptoru.json";
import kutu from "../../jenerator/urunler/olcuye-ozel-kutu-organizer.json";
import kavanoz from "../../jenerator/urunler/olcuye-ozel-vidali-kavanoz-tapa.json";

const HEPSI = [jeton, konektor, cetvel, kase, huni, izgara, braket, oring, pervane, petek,
               profil, ramp, rulman, kasnak, kayis, vida, yay, disli,
               adaptor, kutu, kavanoz];

// Anahtar semanin KENDI id'sinden gelir (dosya adindan degil): sema id'si urunler.json'daki
// kebab-id ile eslesmezse zaten sema bulunamaz ve odeme reddedilir.
export const SEMALAR = new Map(HEPSI.map((s) => [s.id, s]));

export default SEMALAR;

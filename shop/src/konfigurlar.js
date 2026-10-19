/**
 * URETILMIS DOSYA — ELLE DUZENLEME (elle yapilan degisiklik ilk uretimde KAYBOLUR).
 *
 * KAYNAK: urunler.json — "konfigur" alani tasiyan urunler (TEK KAYNAK).
 * URET  : python3 tools/konfigur-bundle-kapisi.py --yaz
 * KAPI  : python3 tools/konfigur-bundle-kapisi.py   (deploy.yml'de BLOKLAYICI; artefakt
 *         bayatsa CI KIRMIZI yanar -> "urun eklendi, ayna guncellenmedi" penceresi kapali)
 *
 * NEDEN AYRI ARTEFAKT: tum urunler.json (13k+ urun) Worker bundle'ina katilamaz (script
 * boyutu). Yalniz konfigur objeleri turetilir. Anahtar = urunler.json'daki kebab-id;
 * eslesmezse index.js konfigur kolu urunu GORMEZ -> konfigur-beklenen.js fail-closed kapisi
 * kalemi 400'e dusurur (sessizce sabit fiyata DUSMEZ).
 *
 * Konfigur verisi public (matematik + aralik + renk/malzeme); sir icermez.
 */


/** id -> konfigur objesi (urunler.json'dan TURETILMIS; id'ye gore sirali). */
const VERI = {
  "agac-kabuklu-orman-ruhu-kafatasi-maskesi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "ahsap-tabut-duvar-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "alev-hukumdari-fantastik-ates-tac": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "anka-kusu-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 669.09,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "at-bustu-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 267.47,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "at-figuru-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 269.34,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "ates-ejderhasi-duvar-basi-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "aya-park-etmis-ufo-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "balina-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 213.12,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "beyinli-kafatasi-bust-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "biyolojik-tehlike-kapi-tabelasi-uyari-plakasi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "biyomekanik-korku-duvar-rafi-sergi-askisi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Genişlik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "boga-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 77.27,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "boynuzlu-kafatasi-masa-ustu-duzenleyici-kase": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "buruk-govdeli-fantastik-bonsai-agaci": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "buyulu-mana-iksiri-sisesi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "capa-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 319.18,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "cizgi-film-tarzi-tahta-kilic-propu": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Uzunluk",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "cthulhu-idolu-antik-kalinti-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "damlayan-birikinti-raf-aksesuari": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Genişlik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "dikenli-kabuklu-kaplumbaga-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "dikenli-kalp-gul-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "dort-yaprakli-yonca-anahtarlik": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "dusuk-poligon-topuz-anahtarligi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "ejderha-kafatasi-masa-ustu-kase": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "eklemli-deniz-yildizi-stres-oyuncagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "eklemli-gecko-kertenkele-stres-oyuncagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "eklemli-palyaco-baligi-stres-oyuncagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "eklemli-timsah-stres-oyuncagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "eklemli-vatoz-stres-oyuncagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "eriyen-buzlu-cubuk-dondurma-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "eriyen-lolipop-masa-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "etcil-bitki-fantastik-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "fener-baligi-iskeleti-duvar-trofesi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "futuristik-akilli-saat-standi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "gelecekci-ankh-duvar-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "geyik-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 55.68,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "gizemli-alev-lambasi-fantastik-led-isik": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "gotik-kafatasi-iskelet-anahtar-duvar-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "gotik-kafatasi-kitap-arasi-dekoru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "gozsuz-ogre-fantastik-canavar-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "gozu-bagli-baykus-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 346.49,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "grafiti-adam-sprey-kutusu-karakter-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "halka-frizbi-ucan-halka-disk": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "hayalet-govdeli-kutuk-saksi-ve-kalemlik": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "helezon-kalemlik-saklama-bardagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "ihtilaf-elmasi-kaideli-heykel": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "isirilmis-elma-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "iskelet-ejderha-masa-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "iskelet-kedi-karikatur-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kafatasi-patlamasi-kemik-yildiz-duvar-dekoru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kafatasi-vazo-genis-agizli-heykelsi-vazo": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kafatasli-bomba-karanlik-raf-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kaktus-masa-figuru-saksili-karakter": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kalp-seklinde-led-mumluk": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kan-portali-duvar-mumlugu-ve-askisi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kapi-ustu-uyari-tabelasi-kapi-gecme-yasak-bolge": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kar-tanesi-duvar-dekoru-ve-susu-seti": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kara-dikenli-canavar-kurt-duvar-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kase-kafali-figur-saklama-kabi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kaya-bardak-altligi-fantastik-tas-altlik": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kemik-ejderha-ouroboros-duvar-dekoru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kizgin-yuzlu-buyucu-sapkasi-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kizgin-yuzlu-cizgi-karakter-cosplay-maskesi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kral-kobra-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kudurmus-kedi-modul-tasarim-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kurt-heykeli-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 239222.8,
      "refYukseklikMm": 1899.739
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kurt-maskesi-acili-yirtici-cosplay-maskesi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "kurutulmus-kafa-anahtarligi-dikisli-gozler": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "magara-adami-krag-karakter-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "mantar-duvar-rafi-organik-islevsel-sanat": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Genişlik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "minimal-dis-fircasi-ve-macun-standi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "mr-bones-iskelet-kase-tutucu": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "olu-kafali-guve-duvar-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "omurga-hilal-duvar-dekoru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "retro-hayalet-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "sarmal-yumurta-lambasi-led-mum-icin": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "sarmasik-yapraklari-kablo-susu": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "savas-yarali-kafatasi-karanlik-dekor-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "seytan-gargoyle-kapi-tokmagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "seytani-cin-masa-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "sicrayan-buyuk-beyaz-kopekbaligi-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "sifa-iksiri-sisesi-fantastik-mini-vazo": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "sinsi-siyam-kedisi-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "sonsuzluk-dugumu-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 133.94,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "sonsuzluk-halkasi-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 221.9,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "soyut-boga-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 247.33,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "surukleme-ahsap-gemi-dumeni-duvar-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Çap",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "tas-cerceveli-prizma-minyatur-sergi-standi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "tedirgin-kara-kedi-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "tiki-kafatasi-led-mumluk": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "uc-bilge-iskelet-figur-seti": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "uc-bilge-uzayli-figur-seti": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "uc-bilge-yaratik-figur-seti": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "uykulu-eklemli-ahtapot-stres-oyuncagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "vampir-kafatasi-kitap-arasi-dekoru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "voronoi-desenli-organik-delikli-maske": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yakut-tilsim-anahtarligi-ve-kolye-ucu": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yaprak-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 33.57,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yarasa-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 171.99,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yari-insan-yari-canavar-donusum-figuru": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yarim-yuz-kafatasi-maskesi-sessizlikte-dovulmus": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yazici-qr-kod-gizleme-kapagi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Genişlik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yeleli-at-bustu-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 152.83,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "yelkenli-serit-dekoratif-figur": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 300,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        500
      ],
      [
        300,
        2500
      ]
    ],
    "hacim": {
      "refHacimCm3": 51.58,
      "refYukseklikMm": 150
    },
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 2,
      "Gri": 1,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "zehirli-elma-kafatasi-anahtarligi": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Boyut",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "zombi-t-rex-heykeli": {
    "boyutMm": {
      "adim": 10,
      "etiket": "Yükseklik",
      "max": 250,
      "min": 60,
      "varsayilan": 150
    },
    "fiyatCapalari": [
      [
        60,
        600
      ],
      [
        250,
        2500
      ]
    ],
    "fiyatModu": "dogrusal",
    "gorselOrnek": true,
    "malzemeler": [
      {
        "ad": "PLA",
        "katsayi": 1
      },
      {
        "ad": "PETG",
        "katsayi": 1.3
      },
      {
        "ad": "ASA",
        "katsayi": 1.6
      }
    ],
    "renkGorselIndeks": {
      "Beyaz": 0,
      "Gri": 0,
      "Siyah": 0
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  }
};

export const KONFIGURLAR = new Map(Object.entries(VERI));

export default KONFIGURLAR;

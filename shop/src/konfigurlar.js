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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "at-silueti-serit-dekoratif-figur": {
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
      "refHacimCm3": 41.75,
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
    },
    "renkler": [
      "Siyah",
      "Beyaz",
      "Gri"
    ],
    "varsayilanMalzeme": "PLA"
  },
  "soyut-yarasa-serit-dekoratif-figur": {
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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
      "Gri": 0,
      "Siyah": 1
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

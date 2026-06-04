# Bulanık Mantık Destekli Adaptif Trafik Işığı Simülasyonu

Benzetim Programları dersi final projesi.
Ali Alizada - 21703903

Trafik ışıklarını sabit süreli yerine bulanık mantıkla anlık trafiğe göre ayarlayan bir sistem. Tek kavşak, 4'lü koridor ve 2×2 grid topolojilerinde, hem sentetik hem de İstanbul Büyükşehir Belediyesi'nin gerçek trafik verisiyle, dört farklı kontrolcünün (Sabit, Bulanık, Webster, Aktüe) istatistiksel karşılaştırması.

## Tek bakışta proje

| Özellik | Değer |
|---|---|
| Benzetim motoru | SimPy 4 (ayrık olay benzetimi) |
| Mikro-simülatör entegrasyonu | SUMO + TraCI |
| Karşılaştırılan kontrolcüler | Sabit, Bulanık (3 girdili), Webster (1958), Aktüe |
| Topolojiler | Tek kavşak, 4'lü koridor, 2×2 grid |
| Veri kaynağı | Sentetik + İBB Açık Veri (Saatlik Trafik Yoğunluk) |
| İstatistiksel sağlamlık | 15 tohumlu Monte Carlo, %95 güven aralığı, Welch t-testi |
| Bulanık kural sayısı | Mamdani min-max, 9 kural, 3 girdi |
| Arayüz | Streamlit (6 sekmeli dashboard) |

## Hızlı başlangıç

```bash
pip install -r requirements.txt
py -m streamlit run app.py
```

Komut satırından tüm senaryoları çalıştırmak:
```bash
py -m src.main --tohum 15 --dakika 60
py -m src.main --ibb data/traffic_density_202501.csv
```

İBB verisini indirmek:
```bash
curl -L -o data/traffic_density_202501.csv \
  "https://data.ibb.gov.tr/dataset/3ee6d744-5da2-40c8-9cd6-0e3e41f1928f/resource/57cb067b-1a0b-460b-8342-7884bd4537e8/download/traffic_density_202501.csv"
```

## Kullanılan benzetim teknikleri

Tek bir yöntem değil, dersin kapsadığı tekniklerin birleşimi:

- Ayrık Olay Benzetimi (DES): araç gelişi, geçiş, faz değişimi gibi olaylar arasında zaman sıçraması (SimPy)
- Stokastik süreçler: homojen olmayan Poisson süreci, geliş aralıkları üstel dağılımdan
- Monte Carlo: 15 bağımsız tohumlu tekrar, ortalama ± güven aralığı
- Mikro + makro birlikte: SimPy (mezzo, hızlı) + SUMO (mikro, gerçekçi)
- Veri tabanlı benzetim: İBB saatlik araç sayımları → λ(t) profili
- Karşılaştırmalı benzetim + ortak rastgele sayılar (CRN)
- Yalancı rastgele sayı üreteci (Mersenne Twister)
- Doğrulama ve geçerli kılma (verification + validation)

## Sistem mimarisi

```
src/
├── controllers/    Sabit, Bulanık, Webster, Aktüe kontrolcüleri
├── data/           İBB CSV loader + trafik profili veri yapıları
├── network/        Intersection + topoloji (single/corridor/grid)
├── stats/          Çoklu tohum, güven aralığı, Welch t-testi
├── viz/            Karşılaştırma grafiği, ısı haritası, animasyon
├── sumo/           SUMO ağ üretici + TraCI runner
├── engine.py       Simülasyon orkestratörü
└── main.py         CLI giriş noktası
```

Tüm kontrolcüler ortak bir Controller soyut sınıfından türer; aynı kontrolcü tek kavşak, koridor ve grid topolojilerinde değişiklik olmadan kullanılabilir.

## Bulanık mantık girdileri ve üyelik fonksiyonları

Bulanık kontrolcü üç girdi alır:

- Kendi yöndeki kuyruk uzunluğu (az / orta / fazla)
- Kendi yöndeki ortalama bekleme süresi (az / orta / fazla)
- Karşı yöndeki kuyruk uzunluğu (az / orta / fazla)

Çıktı: yeşil ışık süresi (12–40 sn aralığında, ağırlıklı ortalama yöntemiyle durulaştırma).

![Bulanık üyelik fonksiyonları](docs/images/05_uyelik_fonksiyonlari.png)

## Sonuçlar

Her senaryo 15 farklı tohumla 60 dakika çalıştırıldı. Ortalama bekleme süresi ± %95 güven aralığı raporlanır.

### Tek kavşak (sentetik veri)

Düşük yoğunlukta tüm kontrolcüler yakın sonuç verir; sabit yeşil süresi (20 sn) zaten yeterli olduğundan adaptif olmanın belirgin bir avantajı yoktur.

![Tek kavşak sentetik karşılaştırma](docs/images/01_tek_kavsak_sentetik.png)

| Kontrolcü | Ort. bekleme (sn) | Max kuyruk |
|---|---:|---:|
| Sabit Süreli | 14.65 ± 0.57 | 17.80 ± 2.28 |
| Bulanık Mantık | 14.76 ± 0.51 | 18.13 ± 1.85 |
| Webster | 35.10 ± 4.59 | 48.07 ± 5.78 |
| Aktüe | 19.02 ± 0.90 | 20.00 ± 1.61 |

### Koridor / 4 Kavşak (sentetik veri)

Burada bulanık mantığın gücü ortaya çıkar. Karşı yön kuyruğu girdisi K1'den biriken araçların K2'ye taşıması gibi dengesiz baskıları algılar.

![Koridor sentetik karşılaştırma](docs/images/02_koridor_sentetik.png)

| Kontrolcü | Ort. bekleme (sn) | Max kuyruk |
|---|---:|---:|
| Sabit Süreli | 125.67 ± 7.20 | 270.93 ± 11.04 |
| Bulanık Mantık | 58.65 ± 4.84 | 296.93 ± 23.96 |
| Webster | 216.23 ± 8.07 | 341.33 ± 13.27 |
| Aktüe | 58.92 ± 3.71 | 146.53 ± 16.04 |

Sabit süreli sistemin 125.67 sn bekleme süresi bulanık mantıkla 58.65 sn'ye düşmektedir; bu yaklaşık yüzde elli üç iyileşmedir. Welch t = 16.56, istatistiksel olarak çok anlamlı.

![Koridor yoğunluk ısı haritası](docs/images/06_koridor_isi_haritasi.png)

### 2×2 Grid (sentetik veri)

![Grid sentetik karşılaştırma](docs/images/03_grid_sentetik.png)

| Kontrolcü | Ort. bekleme (sn) | Max kuyruk |
|---|---:|---:|
| Sabit Süreli | 84.64 ± 3.77 | 281.47 ± 20.54 |
| Bulanık Mantık | 60.65 ± 6.59 | 381.93 ± 33.95 |
| Webster | 215.11 ± 6.42 | 590.73 ± 19.19 |
| Aktüe | 63.24 ± 3.43 | 236.67 ± 20.07 |

![Grid yoğunluk ısı haritası](docs/images/07_grid_isi_haritasi.png)

### İBB gerçek veri (doygun koridor)

İstanbul'un en yoğun geohash hücrelerinde trafik talebi mevcut bulanık yeşil aralığını (12–40 sn) zorlar. Bu doygun rejimde aktüe basit gap-out mantığıyla en iyi sonucu üretir; bulanığın yeşil aralığı yeniden kalibre edilmediği sürece klasik fixed-time ile yakın sonuç verir.

![İBB koridor karşılaştırma](docs/images/04_koridor_ibb.png)

| Kontrolcü | Ort. bekleme (sn) | Max kuyruk |
|---|---:|---:|
| Sabit Süreli | 371.08 ± 4.59 | 627.93 ± 15.63 |
| Bulanık Mantık | 315.46 ± 29.42 | 743.00 ± 19.70 |
| Webster | 515.95 ± 12.21 | 701.80 ± 14.92 |
| Aktüe | 315.05 ± 6.61 | 556.53 ± 20.77 |

Bu bulgu önemlidir: bulanık parametre kalibrasyonu trafik rejimine bağlıdır.

### Welch t-testi özeti

Sabit Süreli referans alındığında pozitif t değeri anlamlı iyileşme, negatif t değeri anlamlı kötüleşme demektir.

Sentetik veri:

| Topoloji | Bulanık | Webster | Aktüe |
|---|---|---|---|
| Tek kavşak | -0.31 (anlamsız) | -9.49 (kötü) | -8.80 (kötü) |
| Koridor | +16.56 (iyi) | -17.95 (kötü) | +17.67 (iyi) |
| Grid | +6.78 (iyi) | -37.59 (kötü) | +9.01 (iyi) |

İBB verisi:

| Topoloji | Bulanık | Webster | Aktüe |
|---|---|---|---|
| Tek kavşak | -0.53 (anlamsız) | -24.39 (kötü) | -2.23 (kötü) |
| Koridor | +4.01 (iyi) | -23.83 (kötü) | +14.94 (iyi) |
| Grid | -12.06 (kötü) | -56.89 (kötü) | +11.10 (iyi) |

## Canlı kavşak animasyonu

Tek kavşak senaryosunda ışık durumu ve kuyruk değişimleri:

![Kavşak animasyonu](docs/images/08_kavsak_animasyon.gif)

## SUMO entegrasyonu (opsiyonel)

Her senaryo için .nod.xml, .edg.xml, .rou.xml ve .sumocfg dosyaları otomatik üretilir. SUMO kurulu ise:

```bash
sumo-gui -c results/final/single/sumo/scenario.sumocfg
```

Bulanık kontrolcüyü SUMO içinde TraCI üzerinden çalıştırmak:

```bash
pip install traci sumolib
py -m src.sumo.runner --scenario results/final/corridor/sumo/scenario.sumocfg --gui
```

Aynı bulanık çekirdek (src/controllers/fuzzy.py) hem SimPy hem SUMO ortamında çalışır.

## Çalıştırma seçenekleri

Hızlı test:
```bash
py -m src.main --hizli
```

Tam koşum (sentetik):
```bash
py -m src.main --tohum 15 --dakika 60
```

Tam koşum (İBB):
```bash
py -m src.main --tohum 15 --dakika 60 --ibb data/traffic_density_202501.csv
```

Sadece belirli topoloji:
```bash
py -m src.main --topoloji corridor
```

Çıktılar `results/final/<topoloji>/` altına yazılır: karşılaştırma çubuk grafiği, ısı haritası, kuyruk tarihçesi, özet CSV, t-test CSV, üyelik fonksiyonu PNG, animasyon GIF (tek kavşak), SUMO dosyaları.

## Dosya yapısı

```
ProjeVize/
├── app.py                      Streamlit dashboard
├── src/                        Ana kaynak kod
├── scripts/                    Yardımcı scriptler
│   ├── create_word_report.py   Markdown raporu Word'e çevirir
│   └── sumo_aglarini_derle.py  SUMO ağlarını netconvert ile derler
├── data/                       İBB CSV verisi (gitignore'da)
├── results/                    Çıktı dosyaları (gitignore'da)
├── docs/images/                README görselleri
├── RAPOR_TASLAGI.md            Final rapor (markdown kaynak)
├── Bulanik_Mantik_Trafik_Raporu_FINAL.docx  Final rapor (Word)
└── requirements.txt
```

## Kullanılan teknolojiler

Python, SimPy, pandas, NumPy, matplotlib, Streamlit, python-docx. Bulanık mantık dış kütüphane kullanılmadan saf Python ile yazıldı. SUMO + TraCI opsiyonel.

## Kaynaklar

- İstanbul Büyükşehir Belediyesi Açık Veri: https://data.ibb.gov.tr/dataset/hourly-traffic-density-data-set
- Webster, F. V. (1958). Traffic Signal Settings.
- Pappis, C. P. & Mamdani, E. H. (1977). A Fuzzy Logic Controller for a Traffic Junction.
- Welch, B. L. (1947). The generalization of Student's problem.
- SimPy 4: https://simpy.readthedocs.io/
- SUMO: https://sumo.dlr.de/docs/

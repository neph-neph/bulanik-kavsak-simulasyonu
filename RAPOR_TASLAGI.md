# BENZETIM PROGRAMLARI DERSI

## Vize Projesi Raporu

### Proje Basligi

**Bulanik Mantik Destekli Adaptif Trafik Isigi Kontrolunun SimPy ile Benzetimi**

### Hazirlayan

**Ad Soyad:** [Burayi doldurunuz]  
**Numara:** [Burayi doldurunuz]  
**Bolum:** [Burayi doldurunuz]  
**Ders:** Benzetim Programlari  
**Ogretim Uyesi:** [Burayi doldurunuz]  
**Tarih:** [Burayi doldurunuz]

---

## 1. GIRIS

Sehir ici ulasimda trafik isiklari genellikle sabit sureli olarak calistirilmaktadir. Bu durum, trafik yogunlugunun degistigi kosullarda bir yondeki araclarin gereksiz yere beklemesine neden olabilmektedir. Ornegin bir yonde uzun kuyruklar olusurken diger yonde yol bos kalabilmektedir.

Bu projede trafik isiklarinin surelerini anlik trafik durumuna gore ayarlayan bulanik mantik tabanli bir kontrol sistemi gelistirilmistir. Sistem SimPy kutuphanesi ile benzetim ortaminda test edilmis ve sabit sureli kontrol ile karsilastirilmistir.

---

## 2. PROBLEMIN TANIMI

Calismada ele alinan problem, tek bir kavsakta trafik yogunlugu degismesine ragmen trafik isiklarinin sabit surelerle calistirilmasidir. Sabit sureli sistemler basit olmasina karsin degisen kosullara uyum saglama kapasitesine sahip degildir.

Projenin amaci, kuyruk uzunlugu ve bekleme suresi bilgilerini kullanarak yesil isik suresini dinamik olarak belirleyen bir yapinin olusturulmasidir. Bu kapsamda asagidaki sorulara cevap aranmistir:

- Sabit sureli kontrol ile bulanik mantik tabanli kontrol arasinda performans farki olusmakta midir?
- Bekleme suresi ve kuyruk uzunlugu hangi yonde degismektedir?
- Olusturulan model daha kapsamli bir calisma icin temel olusturabilir mi?

---

## 3. KULLANILAN VERI VE SENARYO

Projede gercek veri seti kullanilmamistir. Arac gelisleri rastgele olarak uretilmis, ancak farkli zaman dilimlerinde farkli yogunluk degerleri tanimlanarak daha gercekci bir trafik akisi elde edilmeye calisilmistir.

Calismada iki ana yon tanimlanmistir: Kuzey-Guney ve Dogu-Bati. Trafik yogunlugu uc evrede modellenmistir:

- Ilk evrede Kuzey-Guney yonu daha yogun tutulmustur.
- Ikinci evrede iki yon birbirine yakin yogunluktadir.
- Ucuncu evrede Dogu-Bati yonunun yogunlugu artirilmistir.

---

## 4. YONTEM

### 4.1 Benzetim Ortami

Model Python dilinde gelistirilmis olup ayrik olay benzetimi icin SimPy kutuphanesi kullanilmistir. Her arac belirli zaman araliklarinda sisteme dahil edilmekte, trafik isigi durumuna gore kuyrukta beklemekte veya kavsaktan gecmektedir. Simulasyon suresi varsayilan olarak 60 dakikadir.

### 4.2 Sabit Sureli Kontrol

Ilk modelde yesil isik suresi sabit tutulmustur. Her iki yon icin ayni yesil sure degeri uygulanmistir. Bu yapi klasik trafik isigi sistemini temsil etmektedir.

### 4.3 Bulanik Mantik Tabanli Kontrol

Ikinci modelde yesil isik suresi iki girdi degiskenine bagli olarak hesaplanmaktadir:

- Kuyruk uzunlugu
- Ortalama bekleme suresi

Bu girdiler icin dusuk, orta ve yuksek olarak siniflandirilan bulanik kumeler olusturulmustur. Uyelik fonksiyonlari olarak ucgen ve yamuk fonksiyonlar kullanilmistir. Kural tabani min-max bilesim yontemiyle degerlendirilmis, durusiklastirma icin agirlikli ortalama yontemi uygulanmistir.

### 4.4 Performans Olcutleri

Iki kontrol yonteminin karsilastirilmasinda asagidaki olcutler kullanilmistir:

- Ortalama bekleme suresi (yon bazli ve toplam)
- Maksimum ve ortalama kuyruk uzunlugu
- Kavsaktan gecen arac sayisi
- Simulasyon sonunda kalan arac sayisi
- Gecis orani

---

## 5. KULLANILAN YAZILIM VE KUTUPHANELER

- Python
- SimPy (ayrik olay benzetimi)
- pandas (veri tablolari)
- matplotlib (grafik olusturma)
- Streamlit (opsiyonel arayuz)

Bulanik mantik kurallari harici bir kutuphane kullanilmadan dogrudan Python ile kodlanmistir.

---

## 6. ARAYUZ

Projeye temel duzeyde bir Streamlit arayuzu eklenmistir. Arayuz uzerinden simulasyon suresi, sabit yesil isik suresi ve rastgelelik tohumu parametreleri degistirilebilmektedir. Sonuc tablosu ve kuyruk grafikleri ayni ekran uzerinde goruntulenebilmektedir.

---

## 7. BULGULAR

Simulasyon ayni kosullar altinda her iki kontrol yontemi icin calistirilmistir. Elde edilen sonuclar asagidaki tabloda verilmistir.

### Tablo 1. Kontrol yontemlerine ait sonuclar

| Olcut | Sabit Sureli | Bulanik Mantik |
|---|---:|---:|
| Uretilen arac sayisi | 759 | 759 |
| Kavsaktan gecen arac sayisi | 723 | 753 |
| Kalan arac sayisi | 36 | 6 |
| Ortalama toplam bekleme suresi (sn) | 86,77 | 28,39 |
| Kuzey-Guney ort. bekleme (sn) | 136,45 | 32,50 |
| Dogu-Bati ort. bekleme (sn) | 14,67 | 21,98 |
| Maksimum toplam kuyruk | 70 | 31 |
| Ortalama toplam kuyruk | 36,33 | 11,68 |
| Gecis orani | 0,953 | 0,992 |

Sonuclar incelendiginde bulanik mantik tabanli sistemin toplam ortalama bekleme suresini 86,77 saniyeden 28,39 saniyeye dusurdugu gorulmektedir. Maksimum kuyruk uzunlugu 70 aractan 31 araca gerilemistir. Simulasyon sonunda kuyrukta kalan arac sayisi da 36'dan 6'ya dusmustur.

Kuzey-Guney yonunde sabit sureli sistem 136,45 saniye ortalama bekleme uretirken bulanik mantik sistemi bu degeri 32,50 saniyeye indirmistir. Dogu-Bati yonunde bekleme suresi bir miktar artmis olsa da toplam sistem performansi belirgin olarak iyilesmistir. Bu durum yogun olan yone daha fazla yesil sure tahsis edilmesinin beklenen bir sonucudur.

---

## 8. SONUC

Bu calismada tek kavsakli bir trafik sistemi icin sabit sureli kontrol ile bulanik mantik tabanli adaptif kontrol karsilastirilmistir. Elde edilen bulgular bulanik mantik yaklasiminin bekleme suresi, kuyruk uzunlugu ve gecis orani acisindan daha basarili oldugunu gostermistir.

Model vize projesi kapsaminda tek kavsak uzerinde calistirilmistir. Ilerleyen asamalarda birden fazla kavsak, yaya fazi ve daha gercekci trafik senaryolari ile genisletilebilir.

---

## 9. KAYNAKCA

[1] SimPy Documentation. Erisim adresi: https://simpy.readthedocs.io/en/stable/

[2] Streamlit Documentation. Erisim adresi: https://docs.streamlit.io/

[3] Koukol, M., Zajickova, L., Marek, L., Tucek, P. "Fuzzy Logic in Traffic Engineering: A Review on Signal Control." Mathematical Problems in Engineering, 2015.

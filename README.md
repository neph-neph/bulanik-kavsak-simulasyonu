# Bulanik Mantik ile Akilli Kavsak Simulasyonu

Trafik isiklari icin bulanik mantik tabanli kontrol sistemi. SimPy ile simulasyon yapilip sabit sureli kontrol ile karsilastirilmistir.

## Ne yapar?

Tek bir kavsaktaki trafik akisini simule eder. Iki farkli kontrol yontemi test edilir:
- **Sabit sureli:** Yesil isik hep ayni sure yanar
- **Bulanik mantik:** Kuyruk uzunlugu ve bekleme suresine gore yesil sure dinamik olarak degisir

Kuzey-Guney ve Dogu-Bati yonleri icin olusturulan araclarin kuyruk uzunluklari ve bekleme sureleri karsilastirilir.

## Kullanilan teknolojiler

- Python
- SimPy
- pandas
- matplotlib
- Streamlit

Bulanik mantik kurallari projede dogrudan Python ile yazildi, ekstra kutuphane kullanilmadi.

## Dosyalar

```
app.py                    - Streamlit arayuzu
src/fuzzy_controller.py   - Bulanik mantik fonksiyonlari
src/simulation.py         - SimPy simulasyonu
src/main.py               - Komut satirindan calistirmak icin
```

## Kurulum

```bash
pip install -r requirements.txt
```

## Calistirma

Komut satirindan:

```bash
python src/main.py
```

Streamlit arayuzu:

```bash
streamlit run app.py
```

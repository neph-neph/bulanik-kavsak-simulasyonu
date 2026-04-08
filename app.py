from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from simulation import SimulasyonAyarlari, kontrolleri_karsilastir


st.set_page_config(page_title="Akilli Kavsak Simulasyonu", layout="wide")
st.title("Bulanik Mantik Destekli Akilli Kavsak Simulasyonu")
st.write(
    " Ali Alizada - 21703903 "
)

duration = st.sidebar.slider("Simulasyon suresi (dakika)", min_value=15, max_value=120, value=60, step=5)
fixed_green = st.sidebar.slider("Sabit yesil isik suresi (sn)", min_value=10, max_value=40, value=20, step=1)
seed = st.sidebar.number_input("Seed", min_value=1, max_value=9999, value=42, step=1)

ayarlar = SimulasyonAyarlari(
    simulasyon_suresi_dakika=duration,
    sabit_yesil_suresi=fixed_green,
    tohum=int(seed),
)
metrics, histories = kontrolleri_karsilastir(ayarlar)

metrics_display = metrics.rename(
    columns={
        "kontrol_tipi": "Kontrol Tipi",
        "uretilen_arac_sayisi": "Uretilen Arac Sayisi",
        "gecen_arac_sayisi": "Gecen Arac Sayisi",
        "kalan_kuyruk_sayisi": "Kalan Kuyruk Sayisi",
        "ortalama_bekleme_kuzey_guney_saniye": "Kuzey-Guney Ortalama Bekleme (sn)",
        "ortalama_bekleme_dogu_bati_saniye": "Dogu-Bati Ortalama Bekleme (sn)",
        "ortalama_bekleme_toplam_saniye": "Toplam Ortalama Bekleme (sn)",
        "maksimum_kuyruk_kuzey_guney": "Kuzey-Guney Maksimum Kuyruk",
        "maksimum_kuyruk_dogu_bati": "Dogu-Bati Maksimum Kuyruk",
        "maksimum_kuyruk_toplam": "Toplam Maksimum Kuyruk",
        "ortalama_kuyruk_toplam": "Toplam Ortalama Kuyruk",
        "gecis_orani": "Gecis Orani",
    }
)

st.subheader("Karsilastirma Tablosu")
st.dataframe(metrics_display, width="stretch")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Ortalama Bekleme Suresi")
    wait_df = metrics[["kontrol_tipi", "ortalama_bekleme_toplam_saniye"]].set_index("kontrol_tipi")
    st.bar_chart(wait_df)

with col2:
    st.subheader("Maksimum Toplam Kuyruk")
    queue_df = metrics[["kontrol_tipi", "maksimum_kuyruk_toplam"]].set_index("kontrol_tipi")
    st.bar_chart(queue_df)

st.subheader("Kuyruk Gecmisi")
kontrol_secimi = st.radio(
    "Kontrol tipi",
    options=["Sabit Sureli", "Bulanik Mantik"],
    horizontal=True,
)

if kontrol_secimi == "Sabit Sureli":
    secilen_gecmis = histories["sabit"].copy()
else:
    secilen_gecmis = histories["bulanik"].copy()

selected_history = secilen_gecmis[["zaman_saniye", "kuzey_guney_kuyruk", "dogu_bati_kuyruk"]].copy()
selected_history = selected_history.rename(
    columns={
        "zaman_saniye": "Zaman",
        "kuzey_guney_kuyruk": "Kuzey-Guney Kuyrugu",
        "dogu_bati_kuyruk": "Dogu-Bati Kuyrugu",
    }
)
selected_history = selected_history.set_index("Zaman")
st.line_chart(selected_history)


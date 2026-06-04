from pathlib import Path
import sys
import tempfile

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.controllers import (
    ActuatedController,
    FixedController,
    FuzzyController,
    WebsterController,
)
from src.data import IBBLoader, ornek_profil_olustur
from src.engine import SenaryoAyarlari, senaryo_calistir
from src.stats import kontrolcu_karsilastirmasi
from src.viz import (
    isi_haritasi_olustur,
    kavsak_animasyonu_olustur,
    uyelik_fonksiyonu_grafigi,
)

st.set_page_config(page_title="Trafik Simülasyonu", layout="wide")
st.title("Bulanık Mantık Trafik Işığı Simülasyonu")
st.write("Ali Alizada - 21703903")

yan = st.sidebar
yan.header("Ayarlar")

topoloji_etiket = yan.selectbox(
    "Topoloji",
    options=["Tek Kavşak", "Koridor (4 kavşak)", "2x2 Grid"],
)
topoloji = {
    "Tek Kavşak": "single",
    "Koridor (4 kavşak)": "corridor",
    "2x2 Grid": "grid_2x2",
}[topoloji_etiket]

veri_kaynagi = yan.radio("Veri kaynağı", options=["Sentetik", "İBB Gerçek Veri"])

ibb_dosyasi = None
if veri_kaynagi == "İBB Gerçek Veri":
    ibb_dosyasi = yan.text_input("İBB CSV yolu", value="data/traffic_density_202501.csv")
    if not Path(ibb_dosyasi).exists():
        yan.warning("Dosya bulunamadı, sentetik kullanılacak.")
        veri_kaynagi = "Sentetik"
        ibb_dosyasi = None

dakika = yan.slider("Simülasyon süresi (dk)", 15, 240, 60, 15)
tohum_sayisi = yan.slider("Tohum sayısı", 1, 30, 5, 1)
baslangic_saati = yan.slider("Başlangıç saati", 0, 23, 7, 1)
yaya_aktif = yan.checkbox("Yaya fazı", value=False)

kontrolcu_seciminin = yan.multiselect(
    "Kontrolcüler",
    options=["Sabit Süreli", "Bulanık Mantık", "Webster", "Aktüe"],
    default=["Sabit Süreli", "Bulanık Mantık", "Webster", "Aktüe"],
)

fabrikalar_tum = {
    "Sabit Süreli": FixedController,
    "Bulanık Mantık": FuzzyController,
    "Webster": WebsterController,
    "Aktüe": ActuatedController,
}
secilen_fabrikalar = {ad: fabrikalar_tum[ad] for ad in kontrolcu_seciminin}


@st.cache_resource(show_spinner=False)
def populer_geohashleri_getir(csv_yolu: str):
    return IBBLoader(csv_yolu).populer_geohashler(ilk_n=20)


@st.cache_resource(show_spinner=False)
def kavsak_profili_yukle(csv_yolu: str, ad: str, kg: str, db: str, baslangic: int):
    return IBBLoader(csv_yolu).kavsak_profili_olustur(
        ad=ad,
        yon_geohash={"kuzey_guney": kg, "dogu_bati": db},
        baslangic_saati=baslangic,
    )


def profilleri_olustur():
    if veri_kaynagi == "İBB Gerçek Veri" and ibb_dosyasi:
        populer = populer_geohashleri_getir(ibb_dosyasi)
        secilebilir = [p.geohash for p in populer]
        if topoloji == "single":
            ad_listesi = ["K1"]
        elif topoloji == "corridor":
            ad_listesi = [f"K{i+1}" for i in range(4)]
        else:
            ad_listesi = ["K11", "K12", "K21", "K22"]

        secilen = {}
        for ad in ad_listesi:
            cols = st.columns(2)
            with cols[0]:
                kg = st.selectbox(f"{ad} KG geohash", secilebilir, key=f"{ad}_kg", index=ad_listesi.index(ad) * 2 % len(secilebilir))
            with cols[1]:
                db = st.selectbox(f"{ad} DB geohash", secilebilir, key=f"{ad}_db", index=(ad_listesi.index(ad) * 2 + 1) % len(secilebilir))
            secilen[ad] = (kg, db)

        profiller = {ad: kavsak_profili_yukle(ibb_dosyasi, ad, *secilen[ad], baslangic_saati) for ad in ad_listesi}
        if topoloji == "single":
            return [profiller["K1"]]
        if topoloji == "corridor":
            return [profiller[f"K{i+1}"] for i in range(4)]
        return profiller
    else:
        if topoloji == "single":
            return [ornek_profil_olustur()]
        if topoloji == "corridor":
            return [ornek_profil_olustur() for _ in range(4)]
        return {ad: ornek_profil_olustur() for ad in ["K11", "K12", "K21", "K22"]}


if st.button("Çalıştır", type="primary"):
    profiller = profilleri_olustur()
    if not secilen_fabrikalar:
        st.error("En az bir kontrolcü seçin.")
        st.stop()

    with st.spinner("Çalışıyor..."):
        ayarlar = SenaryoAyarlari(
            simulasyon_dakika=dakika,
            yaya_aktif=yaya_aktif,
            baslangic_saati=baslangic_saati,
        )
        karsilastirma = kontrolcu_karsilastirmasi(
            topoloji,
            secilen_fabrikalar,
            profiller,
            tohumlar=list(range(1, tohum_sayisi + 1)),
            temel_ayarlar=ayarlar,
            referans_kontrolcu="Sabit Süreli" if "Sabit Süreli" in secilen_fabrikalar else next(iter(secilen_fabrikalar)),
        )

    sekmeler = st.tabs(["Karşılaştırma", "Isı Haritası", "Üyelik Fonksiyonları", "Animasyon", "Ham Veri"])

    with sekmeler[0]:
        st.subheader("Sonuçlar (ort ± %95 CI)")
        st.dataframe(karsilastirma["ozet_tablosu"], use_container_width=True)
        if karsilastirma["t_test_sonuclari"]:
            st.subheader("t-testi (referans: Sabit Süreli)")
            ttest = []
            for ad, v in karsilastirma["t_test_sonuclari"].items():
                ttest.append({
                    "kontrolcu": ad,
                    "t": round(v["t"], 2),
                    "anlamlı": "evet" if v["anlamli_alpha_005"] else "hayır",
                })
            st.dataframe(pd.DataFrame(ttest), use_container_width=True)

    with sekmeler[1]:
        with tempfile.TemporaryDirectory() as td:
            yol = Path(td) / "isi.png"
            try:
                ilk_ad = next(iter(secilen_fabrikalar))
                tek_sonuc = senaryo_calistir(topoloji, secilen_fabrikalar[ilk_ad], profiller, SenaryoAyarlari(simulasyon_dakika=dakika, tohum=1, yaya_aktif=yaya_aktif, baslangic_saati=baslangic_saati))
                isi_haritasi_olustur(tek_sonuc.gecmis, yol, pencere_saniye=60, baslik=f"{ilk_ad} - {topoloji}")
                st.image(str(yol))
            except Exception as e:
                st.error(str(e))

    with sekmeler[2]:
        with tempfile.TemporaryDirectory() as td:
            yol = Path(td) / "uyelik.png"
            uyelik_fonksiyonu_grafigi(yol)
            st.image(str(yol))

    with sekmeler[3]:
        if topoloji != "single":
            st.info("Animasyon sadece tek kavşak için.")
        else:
            with tempfile.TemporaryDirectory() as td:
                yol = Path(td) / "kavsak.gif"
                ilk_ad = next(iter(secilen_fabrikalar))
                tek = senaryo_calistir("single", secilen_fabrikalar[ilk_ad], profiller, SenaryoAyarlari(simulasyon_dakika=dakika, tohum=1, yaya_aktif=yaya_aktif, baslangic_saati=baslangic_saati))
                try:
                    kavsak_animasyonu_olustur(tek.gecmis, yol, fps=10, kare_atlama=20)
                    st.image(str(yol))
                except Exception as e:
                    st.error(str(e))

    with sekmeler[4]:
        for ad, ozet in karsilastirma["ham_sonuclar"].items():
            st.write(f"**{ad}**")
            st.dataframe(ozet.ham_calistirmalar, use_container_width=True)
else:
    st.info("Sol panelden ayarları seçip Çalıştır'a bas.")

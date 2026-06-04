# Karsilastirma grafikleri (cubuk, zaman serisi, uyelik fonksiyonu)

from pathlib import Path
from typing import Dict, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def karsilastirma_grafigi(
    ozet_df: pd.DataFrame,
    cikti_yolu: Path,
    metrikler: Iterable[str] = ("ortalama_bekleme_sn", "max_kuyruk", "gecis_orani"),
    baslik: str = "Kontrolcü karşılaştırması",
):
    # Birden fazla metrik icin yan yana cubuk grafigi (CI hata cubuklariyla)
    metrikler = list(metrikler)
    fig, axes = plt.subplots(1, len(metrikler), figsize=(5 * len(metrikler), 4.5))
    if len(metrikler) == 1:
        axes = [axes]

    for ax, metrik in zip(axes, metrikler):
        ortalama = []
        hata = []
        for _, satir in ozet_df.iterrows():
            metin = str(satir[metrik])
            # "11.28 ± 0.36" formatı
            if "±" in metin:
                ort_s, yari_s = metin.split("±")
                ortalama.append(float(ort_s.strip()))
                hata.append(float(yari_s.strip()))
            else:
                ortalama.append(float(metin))
                hata.append(0.0)
        ax.bar(ozet_df["kontrolcu"], ortalama, yerr=hata, capsize=4, color=["#d95f02", "#1b9e77", "#7570b3", "#e7298a"])
        ax.set_title(metrik)
        ax.tick_params(axis="x", labelrotation=20)

    fig.suptitle(baslik)
    fig.tight_layout()
    fig.savefig(cikti_yolu, dpi=150)
    plt.close(fig)


def kuyruk_zaman_grafigi(
    gecmis_per_kontrolcu: Dict[str, pd.DataFrame],
    cikti_yolu: Path,
    kavsak_id: str = "K1",
    yon: str = "kuzey_guney",
):
    fig, ax = plt.subplots(figsize=(11, 4.5))
    sutun = f"{yon}_kuyruk"
    for ad, df in gecmis_per_kontrolcu.items():
        bu_kavsak = df[df["kavsak"] == kavsak_id] if "kavsak" in df.columns else df
        if sutun not in bu_kavsak.columns:
            continue
        ax.plot(bu_kavsak["zaman_saniye"], bu_kavsak[sutun], label=ad, alpha=0.85)
    ax.set_xlabel("Zaman (sn)")
    ax.set_ylabel(f"{yon} kuyruk uzunluğu")
    ax.set_title(f"{kavsak_id} - {yon} yönü kuyruk değişimi")
    ax.legend()
    fig.tight_layout()
    fig.savefig(cikti_yolu, dpi=150)
    plt.close(fig)


def uyelik_fonksiyonu_grafigi(cikti_yolu: Path):
    # Bulanik uyelik fonksiyonlarini ciz (kuyruk, bekleme, karsi yon kuyrugu)
    from ..controllers.fuzzy import ucgen_uyelik, yamuk_uyelik

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    # Kuyruk
    x = np.linspace(0, 40, 400)
    axes[0].plot(x, [yamuk_uyelik(v, 0, 0, 4, 10) for v in x], label="az")
    axes[0].plot(x, [ucgen_uyelik(v, 6, 14, 24) for v in x], label="orta")
    axes[0].plot(x, [yamuk_uyelik(v, 18, 26, 40, 40) for v in x], label="fazla")
    axes[0].set_title("Kuyruk uzunluğu")
    axes[0].set_xlabel("Araç sayısı")
    axes[0].set_ylabel("Üyelik")
    axes[0].legend()

    # Bekleme
    x2 = np.linspace(0, 90, 400)
    axes[1].plot(x2, [yamuk_uyelik(v, 0, 0, 6, 15) for v in x2], label="az")
    axes[1].plot(x2, [ucgen_uyelik(v, 10, 22, 38) for v in x2], label="orta")
    axes[1].plot(x2, [yamuk_uyelik(v, 30, 45, 90, 90) for v in x2], label="fazla")
    axes[1].set_title("Ortalama bekleme")
    axes[1].set_xlabel("Saniye")
    axes[1].legend()

    # Karşı yön kuyruk (aynı setlerle)
    axes[2].plot(x, [yamuk_uyelik(v, 0, 0, 4, 10) for v in x], label="az")
    axes[2].plot(x, [ucgen_uyelik(v, 6, 14, 24) for v in x], label="orta")
    axes[2].plot(x, [yamuk_uyelik(v, 18, 26, 40, 40) for v in x], label="fazla")
    axes[2].set_title("Karşı yön kuyruk")
    axes[2].set_xlabel("Araç sayısı")
    axes[2].legend()

    fig.suptitle("Bulanık üyelik fonksiyonları")
    fig.tight_layout()
    fig.savefig(cikti_yolu, dpi=150)
    plt.close(fig)

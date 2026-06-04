# Zaman x kavsak/yon yogunluk isi haritasi

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def isi_haritasi_olustur(
    gecmis_df: pd.DataFrame,
    cikti_yolu: Path,
    pencere_saniye: float = 60.0,
    kavsak_id: Optional[str] = None,
    baslik: str = "Kavşak yoğunluğu ısı haritası",
):
    # Saniye bazli tarihceyi pencerelere bolup ortalama kuyruk = renk koyulugu
    df = gecmis_df.copy()
    if kavsak_id is not None and "kavsak" in df.columns:
        df = df[df["kavsak"] == kavsak_id]
    if df.empty:
        return

    df["pencere"] = (df["zaman_saniye"] // pencere_saniye).astype(int)
    kuyruk_sutunlari = [c for c in df.columns if c.endswith("_kuyruk")]

    if "kavsak" in df.columns:
        df["seri"] = df["kavsak"] + " / " + df.apply(lambda r: "", axis=1)
        seriler = []
        for kav in df["kavsak"].unique():
            for sut in kuyruk_sutunlari:
                seriler.append(f"{kav}/{sut.replace('_kuyruk','')}")
        matris = np.zeros((len(seriler), df["pencere"].max() + 1))
        for i, kav in enumerate(df["kavsak"].unique()):
            alt = df[df["kavsak"] == kav]
            for j, sut in enumerate(kuyruk_sutunlari):
                ort = alt.groupby("pencere")[sut].mean()
                idx = len(kuyruk_sutunlari) * i + j
                for pen, deg in ort.items():
                    matris[idx, pen] = deg
        etiketler = seriler
    else:
        ort = df.groupby("pencere")[kuyruk_sutunlari].mean()
        matris = ort.T.values
        etiketler = [c.replace("_kuyruk", "") for c in kuyruk_sutunlari]

    fig, ax = plt.subplots(figsize=(12, max(2.5, 0.4 * len(etiketler) + 1.5)))
    im = ax.imshow(matris, aspect="auto", cmap="YlOrRd", interpolation="nearest")
    ax.set_yticks(range(len(etiketler)))
    ax.set_yticklabels(etiketler)
    ax.set_xlabel(f"Zaman ({pencere_saniye:.0f} sn'lik pencereler)")
    ax.set_title(baslik)
    fig.colorbar(im, ax=ax, label="Ortalama kuyruk uzunluğu")
    fig.tight_layout()
    fig.savefig(cikti_yolu, dpi=150)
    plt.close(fig)

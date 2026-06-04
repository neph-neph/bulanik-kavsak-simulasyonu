# Tek kavsak icin matplotlib FuncAnimation ile GIF/MP4 uretir

from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter


def _isik_rengi(aktif: str, yon: str) -> str:
    if aktif == "sari":
        return "#facc15"
    if aktif == yon:
        return "#22c55e"
    return "#dc2626"


def kavsak_animasyonu_olustur(
    gecmis_df,
    cikti_yolu: Path,
    kavsak_id: str = "K1",
    yonler=("kuzey_guney", "dogu_bati"),
    fps: int = 5,
    kare_atlama: int = 5,
    format: str = "gif",
):
    # Tarihceyi animasyona cevir. format: 'gif' (Pillow) veya 'mp4' (FFmpeg)
    df = gecmis_df.copy()
    if "kavsak" in df.columns:
        df = df[df["kavsak"] == kavsak_id]
    if df.empty:
        return
    df = df.iloc[::kare_atlama].reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.axis("off")

    # Yollar
    ax.add_patch(patches.Rectangle((4, 0), 2, 10, color="#1f2937", zorder=0))  # KG yol
    ax.add_patch(patches.Rectangle((0, 4), 10, 2, color="#1f2937", zorder=0))  # DB yol

    # Sinyal lambaları
    kg_isik = patches.Circle((5, 7), 0.35, color="red", zorder=3)
    db_isik = patches.Circle((7, 5), 0.35, color="red", zorder=3)
    ax.add_patch(kg_isik)
    ax.add_patch(db_isik)

    baslik_text = ax.text(5, 9.5, "", ha="center", fontsize=12, weight="bold")
    kg_sayi_text = ax.text(5, 1, "", ha="center", color="white", fontsize=11)
    db_sayi_text = ax.text(1.2, 5, "", ha="center", color="white", fontsize=11)

    def kareyi_ciz(idx):
        rec = df.iloc[idx]
        aktif = rec["aktif_isik"]
        kg_isik.set_color(_isik_rengi(aktif, "kuzey_guney"))
        db_isik.set_color(_isik_rengi(aktif, "dogu_bati"))
        kg = int(rec.get("kuzey_guney_kuyruk", 0))
        db = int(rec.get("dogu_bati_kuyruk", 0))
        kg_sayi_text.set_text(f"KG: {kg}")
        db_sayi_text.set_text(f"DB: {db}")
        baslik_text.set_text(f"{kavsak_id} | t = {rec['zaman_saniye']:.0f} sn | aktif: {aktif}")
        return [kg_isik, db_isik, baslik_text, kg_sayi_text, db_sayi_text]

    anim = FuncAnimation(fig, kareyi_ciz, frames=len(df), interval=1000 / fps, blit=False)
    if format == "mp4":
        writer = FFMpegWriter(fps=fps)
    else:
        writer = PillowWriter(fps=fps)
    anim.save(str(cikti_yolu), writer=writer)
    plt.close(fig)

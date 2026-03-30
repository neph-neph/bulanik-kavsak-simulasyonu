import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from simulation import SimulasyonAyarlari, kontrolleri_karsilastir


def create_comparison_plot(metrics, output_dir):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].bar(metrics["kontrol_tipi"], metrics["ortalama_bekleme_toplam_saniye"], color=["#d95f02", "#1b9e77"])
    axes[0].set_title("Ortalama Bekleme Suresi")
    axes[0].set_ylabel("Saniye")

    axes[1].bar(metrics["kontrol_tipi"], metrics["maksimum_kuyruk_toplam"], color=["#7570b3", "#66a61e"])
    axes[1].set_title("Maksimum Toplam Kuyruk")
    axes[1].set_ylabel("Arac Sayisi")

    fig.tight_layout()
    fig.savefig(output_dir / "controller_comparison.png", dpi=150)
    plt.close(fig)


def create_queue_plot(histories, output_dir):
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    sabit_gecmis = histories["sabit"]
    bulanik_gecmis = histories["bulanik"]

    axes[0].plot(sabit_gecmis["zaman_saniye"], sabit_gecmis["kuzey_guney_kuyruk"], label="Kuzey-Guney Kuyrugu")
    axes[0].plot(sabit_gecmis["zaman_saniye"], sabit_gecmis["dogu_bati_kuyruk"], label="Dogu-Bati Kuyrugu")
    axes[0].set_title("Sabit Sureli Kontrol")
    axes[0].set_ylabel("Arac Sayisi")
    axes[0].legend()

    axes[1].plot(bulanik_gecmis["zaman_saniye"], bulanik_gecmis["kuzey_guney_kuyruk"], label="Kuzey-Guney Kuyrugu")
    axes[1].plot(bulanik_gecmis["zaman_saniye"], bulanik_gecmis["dogu_bati_kuyruk"], label="Dogu-Bati Kuyrugu")
    axes[1].set_title("Bulanik Mantik Kontrollu Sistem")
    axes[1].set_xlabel("Zaman (saniye)")
    axes[1].set_ylabel("Arac Sayisi")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_dir / "queue_history.png", dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Akilli kavsak simulasyonunu calistirir.")
    parser.add_argument("--duration", type=int, default=60, help="Simulasyon suresi (dakika).")
    parser.add_argument("--fixed-green", type=int, default=20, help="Sabit yesil isik suresi (saniye).")
    parser.add_argument("--seed", type=int, default=42, help="Rastgelelik tohumu.")
    parser.add_argument("--output-dir", default="results", help="Sonuc dosyalarinin kaydedilecegi klasor.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ayarlar = SimulasyonAyarlari(
        simulasyon_suresi_dakika=args.duration,
        sabit_yesil_suresi=args.fixed_green,
        tohum=args.seed,
    )
    metrics, histories = kontrolleri_karsilastir(ayarlar)

    metrics.to_csv(output_dir / "metrics.csv", index=False)
    histories["sabit"].to_csv(output_dir / "sabit_gecmis.csv", index=False)
    histories["bulanik"].to_csv(output_dir / "bulanik_gecmis.csv", index=False)

    create_comparison_plot(metrics, output_dir)
    create_queue_plot(histories, output_dir)

    print("Simulasyon tamamlandi.")
    print(metrics.to_string(index=False))
    print(f"\nSonuclar su klasore kaydedildi: {output_dir.resolve()}")


if __name__ == "__main__":
    main()

# Komut satiri arayuzu. Tum senaryolari calistirir, sonuclari results/final altina yazar.
# Ornek: py -m src.main --tohum 15 --dakika 60 --ibb data/traffic_density_202501.csv

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from .controllers import (
    ActuatedController,
    FixedController,
    FuzzyController,
    WebsterController,
)
from .data import IBBLoader, ornek_profil_olustur
from .engine import SenaryoAyarlari, senaryo_calistir
from .stats import kontrolcu_karsilastirmasi
from .sumo import sumo_koridor_olustur, sumo_grid_olustur, sumo_tek_kavsak_olustur
from .viz import (
    isi_haritasi_olustur,
    karsilastirma_grafigi,
    kavsak_animasyonu_olustur,
    kuyruk_zaman_grafigi,
    uyelik_fonksiyonu_grafigi,
)


FABRIKALAR = {
    "Sabit Süreli": FixedController,
    "Bulanık Mantık": FuzzyController,
    "Webster": WebsterController,
    "Aktüe": ActuatedController,
}


def _ibb_profilleri_olustur(ibb_csv: Path, ad_listesi: List[str]) -> Dict[str, "IntersectionProfile"]:
    loader = IBBLoader(ibb_csv)
    populer = loader.populer_geohashler(ilk_n=max(2 * len(ad_listesi), 20))
    secilen = populer[: 2 * len(ad_listesi)]
    if len(secilen) < 2 * len(ad_listesi):
        raise RuntimeError("Yeterli geohash bulunamadı.")
    profiller = {}
    for i, ad in enumerate(ad_listesi):
        kg = secilen[2 * i].geohash
        db = secilen[2 * i + 1].geohash
        profiller[ad] = loader.kavsak_profili_olustur(
            ad=ad,
            yon_geohash={"kuzey_guney": kg, "dogu_bati": db},
            baslangic_saati=7,
        )
    return profiller


def _senaryo_profilleri(topoloji: str, ibb_csv: Path = None):
    if topoloji == "single":
        ads = ["K1"]
    elif topoloji == "corridor":
        ads = [f"K{i+1}" for i in range(4)]
    else:
        ads = ["K11", "K12", "K21", "K22"]
    if ibb_csv:
        profiller = _ibb_profilleri_olustur(Path(ibb_csv), ads)
    else:
        profiller = {ad: ornek_profil_olustur() for ad in ads}
    if topoloji == "single":
        return [profiller["K1"]]
    if topoloji == "corridor":
        return [profiller[f"K{i+1}"] for i in range(4)]
    return profiller


def senaryo_pipeline(out_dir: Path, topoloji: str, tohum_sayisi: int, dakika: int, ibb_csv: Path = None, yaya_aktif: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)
    profiller = _senaryo_profilleri(topoloji, ibb_csv)

    ayarlar = SenaryoAyarlari(simulasyon_dakika=dakika, yaya_aktif=yaya_aktif)
    karsilastirma = kontrolcu_karsilastirmasi(
        topoloji,
        FABRIKALAR,
        profiller,
        tohumlar=list(range(1, tohum_sayisi + 1)),
        temel_ayarlar=ayarlar,
    )
    ozet_df = karsilastirma["ozet_tablosu"]
    ozet_df.to_csv(out_dir / "ozet.csv", index=False)

    # T-test sonuçları
    ttest = []
    for ad, v in karsilastirma["t_test_sonuclari"].items():
        ttest.append({
            "kontrolcu": ad,
            "t": round(v["t"], 3),
            "df": round(v["df"], 1),
            "kritik_t": v["kritik_t"],
            "anlamli_alpha_005": v["anlamli_alpha_005"],
        })
    pd.DataFrame(ttest).to_csv(out_dir / "ttest.csv", index=False)

    # Ham çalıştırmalar
    ham_combined = []
    for ad, ozet in karsilastirma["ham_sonuclar"].items():
        df = ozet.ham_calistirmalar.copy()
        df["kontrolcu"] = ad
        ham_combined.append(df)
    pd.concat(ham_combined, ignore_index=True).to_csv(out_dir / "ham_calistirmalar.csv", index=False)

    # Grafikler
    karsilastirma_grafigi(
        ozet_df,
        out_dir / "karsilastirma.png",
        metrikler=("ortalama_bekleme_sn", "max_kuyruk", "gecis_orani"),
        baslik=f"{topoloji} - kontrolcü karşılaştırması",
    )

    # Tek tohum çalıştırıp tarihçe alarak ısı haritası + (single ise) animasyon
    for ad, fab in FABRIKALAR.items():
        sonuc = senaryo_calistir(topoloji, fab, profiller, SenaryoAyarlari(simulasyon_dakika=dakika, tohum=1, yaya_aktif=yaya_aktif))
        sonuc.gecmis.to_csv(out_dir / f"gecmis_{ad.replace(' ', '_')}.csv", index=False)
        isi_haritasi_olustur(
            sonuc.gecmis,
            out_dir / f"isi_{ad.replace(' ', '_')}.png",
            pencere_saniye=60,
            baslik=f"{ad} - {topoloji}",
        )
        if topoloji == "single":
            try:
                kavsak_animasyonu_olustur(
                    sonuc.gecmis,
                    out_dir / f"anim_{ad.replace(' ', '_')}.gif",
                    fps=10,
                    kare_atlama=20,
                )
            except Exception as e:
                print(f"Animasyon üretilemedi ({ad}):", e)

    # Üyelik fonksiyonları (sabit, tek defa)
    uyelik_fonksiyonu_grafigi(out_dir / "uyelik_fonksiyonlari.png")

    # SUMO dosyaları
    sumo_out = out_dir / "sumo"
    if topoloji == "single":
        sumo_tek_kavsak_olustur(sumo_out, profiller[0], sure_dakika=dakika)
    elif topoloji == "corridor":
        sumo_koridor_olustur(sumo_out, profiller, sure_dakika=dakika)
    else:
        sumo_grid_olustur(sumo_out, profiller, sure_dakika=dakika)

    print(f"[{topoloji}] tamam -> {out_dir}")
    print(ozet_df.to_string(index=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="results/final")
    parser.add_argument("--ibb", default=None, help="İBB CSV yolu (yoksa sentetik kullanılır)")
    parser.add_argument("--tohum", type=int, default=10)
    parser.add_argument("--dakika", type=int, default=60)
    parser.add_argument("--yaya", action="store_true")
    parser.add_argument("--hizli", action="store_true", help="3 tohum × 30 dk (hızlı smoke)")
    parser.add_argument("--topoloji", choices=["single", "corridor", "grid_2x2", "hepsi"], default="hepsi")
    args = parser.parse_args()

    if args.hizli:
        args.tohum = 3
        args.dakika = 30

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    topolojiler = ["single", "corridor", "grid_2x2"] if args.topoloji == "hepsi" else [args.topoloji]
    for t in topolojiler:
        senaryo_pipeline(
            out_root / t,
            topoloji=t,
            tohum_sayisi=args.tohum,
            dakika=args.dakika,
            ibb_csv=args.ibb,
            yaya_aktif=args.yaya,
        )


if __name__ == "__main__":
    main()

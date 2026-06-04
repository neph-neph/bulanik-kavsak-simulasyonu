from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .profile import IntersectionProfile, TrafficProfile


@dataclass
class GeohashOzeti:
    geohash: str
    enlem: float
    boylam: float
    toplam_arac: int
    saatlik_ortalama: List[float]


class IBBLoader:
    # CSV sutunlari: DATE_TIME, LATITUDE, LONGITUDE, GEOHASH,
    # MINIMUM_SPEED, MAXIMUM_SPEED, AVERAGE_SPEED, NUMBER_OF_VEHICLES

    def __init__(self, csv_yolu, chunksize: int = 500_000):
        self.csv_yolu = Path(csv_yolu)
        if not self.csv_yolu.exists():
            raise FileNotFoundError(f"CSV bulunamadi: {self.csv_yolu}")
        self.chunksize = chunksize
        self._cache: Dict[str, pd.DataFrame] = {}

    def _yukle(self, gerekli_geohashler: Optional[List[str]] = None) -> pd.DataFrame:
        anahtar = "|".join(sorted(gerekli_geohashler)) if gerekli_geohashler else "__hepsi__"
        if anahtar in self._cache:
            return self._cache[anahtar]

        parcalar = []
        for chunk in pd.read_csv(self.csv_yolu, chunksize=self.chunksize):
            if gerekli_geohashler is not None:
                chunk = chunk[chunk["GEOHASH"].isin(gerekli_geohashler)]
            if not chunk.empty:
                parcalar.append(chunk)

        if not parcalar:
            return pd.DataFrame()

        df = pd.concat(parcalar, ignore_index=True)
        df["DATE_TIME"] = pd.to_datetime(df["DATE_TIME"], errors="coerce")
        df = df.dropna(subset=["DATE_TIME"])
        df["saat"] = df["DATE_TIME"].dt.hour
        self._cache[anahtar] = df
        return df

    def populer_geohashler(self, ilk_n: int = 50, ornek_satir: int = 1_500_000) -> List[GeohashOzeti]:
        #sadece ilk N satira bakar (yogunluk tahmini).
        df = pd.read_csv(self.csv_yolu, nrows=ornek_satir)
        toplam = df.groupby("GEOHASH")["NUMBER_OF_VEHICLES"].sum().sort_values(ascending=False)
        en_yogun = toplam.head(ilk_n).index.tolist()
        merkezler = df.groupby("GEOHASH")[["LATITUDE", "LONGITUDE"]].mean().loc[en_yogun]

        df["DATE_TIME"] = pd.to_datetime(df["DATE_TIME"], errors="coerce")
        df = df.dropna(subset=["DATE_TIME"])
        df["saat"] = df["DATE_TIME"].dt.hour
        saatlik = (
            df[df["GEOHASH"].isin(en_yogun)]
            .groupby(["GEOHASH", "saat"])["NUMBER_OF_VEHICLES"]
            .mean()
            .unstack(fill_value=0)
        )

        ozetler = []
        for gh in en_yogun:
            satir = saatlik.loc[gh] if gh in saatlik.index else pd.Series(0, index=range(24))
            saatlik_liste = [float(satir.get(s, 0.0)) for s in range(24)]
            ozetler.append(
                GeohashOzeti(
                    geohash=gh,
                    enlem=float(merkezler.loc[gh, "LATITUDE"]),
                    boylam=float(merkezler.loc[gh, "LONGITUDE"]),
                    toplam_arac=int(toplam[gh]),
                    saatlik_ortalama=saatlik_liste,
                )
            )
        return ozetler

    def yon_profili_olustur(self, geohash: str, olcekleme: float = 1.0, etiket: str = "") -> TrafficProfile:
        # Tek geohash icin 24 saatlik ortalama profil
        df = self._yukle(gerekli_geohashler=[geohash])
        if df.empty:
            raise ValueError(f"Geohash icin veri bulunamadi: {geohash}")
        saatlik = df.groupby("saat")["NUMBER_OF_VEHICLES"].mean().reindex(range(24), fill_value=0)
        return TrafficProfile(
            saatlik_arac_sayisi=[float(v) for v in saatlik.values],
            olcekleme=olcekleme,
            etiket=etiket or geohash,
        )

    def kavsak_profili_olustur(
        self,
        ad: str,
        yon_geohash: Dict[str, str],
        yon_olcekleme: Optional[Dict[str, float]] = None,
        baslangic_saati: int = 7,
    ) -> IntersectionProfile:
        # Her yone bir geohash atayarak komple kavsak profili olustur
        yon_olcekleme = yon_olcekleme or {}
        profiller = {}
        for yon, gh in yon_geohash.items():
            profiller[yon] = self.yon_profili_olustur(gh, olcekleme=yon_olcekleme.get(yon, 1.0), etiket=f"{ad}/{yon}")
        return IntersectionProfile(yon_profilleri=profiller, ad=ad, baslangic_saati=baslangic_saati)


def ornek_profil_olustur(
    saatlik_kg: Optional[List[float]] = None,
    saatlik_db: Optional[List[float]] = None,
) -> IntersectionProfile:
    # IBB CSV yoksa veya hizli test gerekirse: sabah/aksam pikli sentetik kavsak
    if saatlik_kg is None:
        saatlik_kg = [
            80, 50, 30, 20, 30, 60, 180, 420, 780, 620,
            500, 540, 580, 560, 540, 600, 720, 880, 820, 600,
            400, 280, 200, 140,
        ]
    if saatlik_db is None:
        saatlik_db = [
            60, 40, 25, 18, 25, 55, 160, 360, 700, 580,
            460, 500, 540, 520, 500, 560, 660, 780, 720, 540,
            360, 240, 170, 120,
        ]
    return IntersectionProfile(
        yon_profilleri={
            "kuzey_guney": TrafficProfile(saatlik_kg, etiket="KG"),
            "dogu_bati": TrafficProfile(saatlik_db, etiket="DB"),
        },
        ad="ornek_kavsak",
        baslangic_saati=7,
    )

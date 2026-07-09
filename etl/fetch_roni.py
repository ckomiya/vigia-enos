"""Descarga y procesa el índice RONI desde NOAA CPC."""
from pathlib import Path

import pandas as pd
import requests

RONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_DIR / "data" / "raw" / "roni_raw.txt"
PROCESSED_PATH = BASE_DIR / "data" / "processed" / "roni.csv"

# Mes central de cada temporada de 3 meses (DJF -> enero, JFM -> febrero, etc.)
SEASON_TO_REF_MONTH = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def fetch_raw() -> str:
    response = requests.get(RONI_URL, timeout=30)
    response.raise_for_status()
    return response.text


def parse_roni(raw_text: str) -> pd.DataFrame:
    rows = []
    for line in raw_text.splitlines()[1:]:  # ignora la fila de cabecera "SEAS YR ANOM"
        line = line.strip()
        if not line:
            continue
        season, year, roni = line.split()
        rows.append((season, int(year), float(roni)))

    df = pd.DataFrame(rows, columns=["season", "year", "roni"])
    df["ref_month"] = df["season"].map(SEASON_TO_REF_MONTH)
    return df


def main() -> None:
    raw_text = fetch_raw()

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(raw_text, encoding="utf-8")

    df = parse_roni(raw_text)

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)

    print(f"Guardado crudo en {RAW_PATH} ({len(raw_text)} bytes)")
    print(f"Guardado procesado en {PROCESSED_PATH} ({len(df)} filas)")


if __name__ == "__main__":
    main()

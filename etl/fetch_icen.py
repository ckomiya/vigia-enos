"""Descarga y procesa el índice ICEN desde el IGP."""
from pathlib import Path

import pandas as pd
import requests

ICEN_URL = "http://met.igp.gob.pe/datos/ICEN.txt"

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_DIR / "data" / "raw" / "icen_raw.txt"
PROCESSED_PATH = BASE_DIR / "data" / "processed" / "icen.csv"


def fetch_raw() -> str:
    response = requests.get(ICEN_URL, timeout=30)
    response.raise_for_status()
    return response.text


def parse_icen(raw_text: str) -> pd.DataFrame:
    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        year, month, icen = line.split()
        rows.append((int(year), int(month), float(icen)))
    return pd.DataFrame(rows, columns=["year", "month", "icen"])


def main() -> None:
    raw_text = fetch_raw()

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_text(raw_text, encoding="utf-8")

    df = parse_icen(raw_text)

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)

    print(f"Guardado crudo en {RAW_PATH} ({len(raw_text)} bytes)")
    print(f"Guardado procesado en {PROCESSED_PATH} ({len(df)} filas)")


if __name__ == "__main__":
    main()

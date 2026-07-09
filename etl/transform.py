"""Une las series ICEN y RONI y categoriza el valor puntual más reciente
de cada índice, según los umbrales del CLAUDE.md.

ICEN: la metodología vigente de ENFEN 2026 categoriza por percentiles
(P4/P10/P25/P75/P90/P95/P99) sobre la serie histórica 1950-2023, no por
valores fijos. Ese cálculo todavía no está implementado aquí; por decisión
explícita para este MVP se usa como fallback provisional la metodología
anterior de valores fijos en °C (Nota Técnica ENFEN 01-2024). Migrar a
percentiles es un TODO pendiente, no un descuido.

RONI: además de la categorización puntual, se detectan eventos por
persistencia (racha de 5+ temporadas consecutivas sin volver a Neutro),
según la regla documentada en el CLAUDE.md.

ICEN: la categorización sigue siendo solo puntual — su regla de
persistencia (3+ meses consecutivos) queda documentada mas no implementada,
para una fase posterior.
"""
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
ICEN_PATH = BASE_DIR / "data" / "processed" / "icen.csv"
RONI_PATH = BASE_DIR / "data" / "processed" / "roni.csv"
MERGED_PATH = BASE_DIR / "data" / "processed" / "merged.csv"

# RONI (Pacífico central, Niño 3.4)
RONI_EL_NINO_THRESHOLD = 0.5
RONI_LA_NINA_THRESHOLD = -0.5
RONI_EVENT_MIN_SEASONS = 5

# ICEN (costa peruana, Niño 1+2) — Nota Técnica ENFEN 01-2024 (fallback
# provisional; la metodología vigente usa percentiles, ver docstring arriba)
ICEN_FRIA_THRESHOLD = -0.7
ICEN_NEUTRA_THRESHOLD = 0.5
ICEN_CALIDA_DEBIL_THRESHOLD = 1.3
# Rangos de cálida moderada/fuerte/extraordinaria: pendiente confirmar
# valores exactos (CLAUDE.md), por eso agrupamos todo lo > 1.3 como
# "Cálida" sin subdividir por ahora.


def categorize_roni(value: float) -> str:
    if value >= RONI_EL_NINO_THRESHOLD:
        return "El Niño"
    if value <= RONI_LA_NINA_THRESHOLD:
        return "La Niña"
    return "Neutro"


def categorize_icen(value: float) -> str:
    if value < ICEN_FRIA_THRESHOLD:
        return "Fría"
    if value <= ICEN_NEUTRA_THRESHOLD:
        return "Neutra"
    if value <= ICEN_CALIDA_DEBIL_THRESHOLD:
        return "Cálida débil"
    return "Cálida"


def detect_roni_events(roni_df: pd.DataFrame) -> pd.DataFrame:
    """Marca cada fila con "El Niño activo" / "La Niña activo" cuando forma
    parte de una racha de RONI_EVENT_MIN_SEASONS o más temporadas
    consecutivas en la misma categoría (El Niño o La Niña), sin que una
    temporada Neutra intermedia rompa la racha. Filas fuera de una racha así
    quedan en None.
    """
    df = roni_df.sort_values(["year", "ref_month"]).reset_index(drop=True)
    categorias = df["roni"].apply(categorize_roni)

    evento = pd.Series([None] * len(df), dtype=object)

    i = 0
    n = len(df)
    while i < n:
        cat = categorias.iloc[i]
        j = i
        while j < n and categorias.iloc[j] == cat:
            j += 1
        racha_len = j - i
        if cat != "Neutro" and racha_len >= RONI_EVENT_MIN_SEASONS:
            label = "El Niño activo" if cat == "El Niño" else "La Niña activo"
            evento.iloc[i:j] = label
        i = j

    df["evento_roni"] = evento
    return df


def merge_series(icen_df: pd.DataFrame, roni_df: pd.DataFrame) -> pd.DataFrame:
    merged = icen_df.merge(
        roni_df,
        left_on=["year", "month"],
        right_on=["year", "ref_month"],
        how="outer",
    ).sort_values(["year", "month"]).reset_index(drop=True)
    return merged


def main() -> None:
    icen_df = pd.read_csv(ICEN_PATH)
    roni_df = pd.read_csv(RONI_PATH)

    roni_df = detect_roni_events(roni_df)
    roni_df.to_csv(RONI_PATH, index=False)

    merged = merge_series(icen_df, roni_df)
    merged.to_csv(MERGED_PATH, index=False)

    latest_icen = icen_df.sort_values(["year", "month"]).iloc[-1]
    latest_roni = roni_df.sort_values(["year", "ref_month"]).iloc[-1]

    estado_icen = categorize_icen(latest_icen["icen"])
    estado_roni = categorize_roni(latest_roni["roni"])

    print(f"Guardado unido en {MERGED_PATH} ({len(merged)} filas)")
    print(
        f"Estado ICEN más reciente: {estado_icen} "
        f"(ICEN={latest_icen['icen']} en {int(latest_icen['year'])}-{int(latest_icen['month']):02d})"
    )
    print(
        f"Estado RONI más reciente: {estado_roni} "
        f"(RONI={latest_roni['roni']} en {latest_roni['season']} {latest_roni['year']})"
    )
    print(f"Evento RONI vigente: {latest_roni['evento_roni'] or 'Sin evento confirmado'}")


if __name__ == "__main__":
    main()

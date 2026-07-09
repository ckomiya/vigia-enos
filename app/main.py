"""Dashboard Vigía ENOS — Fase 1 (MVP).

Página única: serie temporal de ICEN + RONI con líneas de umbral, y un
KPI tipo semáforo con el estado puntual más reciente de cada índice.
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from etl import fetch_icen, fetch_roni  # noqa: E402
from etl.transform import (  # noqa: E402
    ICEN_CALIDA_DEBIL_THRESHOLD,
    ICEN_FRIA_THRESHOLD,
    ICEN_NEUTRA_THRESHOLD,
    RONI_EL_NINO_THRESHOLD,
    RONI_LA_NINA_THRESHOLD,
    categorize_icen,
    categorize_roni,
)
from etl import transform  # noqa: E402

MERGED_PATH = BASE_DIR / "data" / "processed" / "merged.csv"

# Paleta "instrumento oceanográfico" — panel de monitoreo científico.
COLOR_BG = "#0B1E2D"
COLOR_PANEL = "#12293D"
COLOR_GRID = "#1E3A4F"
COLOR_WARM = "#E8703A"  # El Niño / ICEN
COLOR_COLD = "#3A9BC4"  # La Niña / RONI
COLOR_TEXT = "#DCE6ED"
COLOR_TEXT_MUTED = "#7A93A6"
# Versión oscurecida de COLOR_COLD: #3A9BC4 da solo ~2.5:1 de contraste con
# COLOR_TEXT (falla WCAG AA); esta versión da ~7.5:1.
COLOR_COLD_ACTIVE = "#1B4A63"

FONT_DISPLAY = "'Space Grotesk', sans-serif"
FONT_MONO = "'IBM Plex Mono', monospace"

# Semáforo: cálido = acento cálido, frío = acento frío, neutro = texto muted.
SEMAFORO_COLOR = {
    "El Niño": COLOR_WARM,
    "Cálida": COLOR_WARM,
    "Cálida débil": COLOR_WARM,
    "Neutro": COLOR_TEXT_MUTED,
    "Neutra": COLOR_TEXT_MUTED,
    "La Niña": COLOR_COLD,
    "Fría": COLOR_COLD,
}


def get_last_update_label() -> str:
    """Deriva el texto de última actualización del mtime de merged.csv, para
    que sobreviva a un reinicio del servidor (no depende de estado en memoria
    del callback)."""
    if not MERGED_PATH.exists():
        return "Sin datos aún"
    mtime = datetime.fromtimestamp(MERGED_PATH.stat().st_mtime)
    return f"Última actualización: {mtime.strftime('%d/%m/%Y %H:%M:%S')}"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(MERGED_PATH)
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    return df.sort_values("date")


def build_timeseries_figure(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["date"], y=df["icen"], name="ICEN", mode="lines",
        line=dict(color=COLOR_WARM),
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["roni"], name="RONI", mode="lines",
        line=dict(color=COLOR_COLD),
    ))

    icen_thresholds = [
        (ICEN_FRIA_THRESHOLD, "ICEN Fría"),
        (ICEN_NEUTRA_THRESHOLD, "ICEN Neutra/Cálida déb."),
        (ICEN_CALIDA_DEBIL_THRESHOLD, "ICEN Cálida déb./Cálida"),
    ]
    for value, label in icen_thresholds:
        fig.add_hline(
            y=value, line_dash="dot", line_color=COLOR_WARM, opacity=0.5,
            annotation_text=label, annotation_position="top left",
            annotation_font_size=9, annotation_font_color=COLOR_TEXT_MUTED,
        )

    roni_thresholds = [
        (RONI_LA_NINA_THRESHOLD, "RONI La Niña"),
        (RONI_EL_NINO_THRESHOLD, "RONI El Niño"),
    ]
    for value, label in roni_thresholds:
        fig.add_hline(
            y=value, line_dash="dash", line_color=COLOR_COLD, opacity=0.5,
            annotation_text=label, annotation_position="bottom right",
            annotation_font_size=9, annotation_font_color=COLOR_TEXT_MUTED,
        )

    fig.update_layout(
        title=dict(
            text="ICEN y RONI en el tiempo",
            font=dict(family=FONT_DISPLAY, color=COLOR_TEXT, size=18),
        ),
        xaxis_title="Fecha",
        yaxis_title="Anomalía",
        paper_bgcolor=COLOR_PANEL,
        plot_bgcolor=COLOR_PANEL,
        font=dict(family=FONT_MONO, color=COLOR_TEXT_MUTED),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.15, x=0,
            font=dict(family=FONT_DISPLAY, color=COLOR_TEXT),
        ),
        margin=dict(t=140),
    )

    fig.update_xaxes(gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, tickfont=dict(family=FONT_MONO, color=COLOR_TEXT_MUTED))
    fig.update_yaxes(gridcolor=COLOR_GRID, zerolinecolor=COLOR_GRID, tickfont=dict(family=FONT_MONO, color=COLOR_TEXT_MUTED))

    last_date = df["date"].max()
    default_start = last_date - pd.DateOffset(years=10)

    fig.update_xaxes(
        range=[default_start, last_date],
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1 año", step="year", stepmode="backward"),
                dict(count=5, label="5 años", step="year", stepmode="backward"),
                dict(count=10, label="10 años", step="year", stepmode="backward"),
                dict(step="all", label="Todo"),
            ],
            bgcolor=COLOR_PANEL,
            activecolor=COLOR_COLD_ACTIVE,
            bordercolor=COLOR_GRID,
            borderwidth=1,
            font=dict(color=COLOR_TEXT, family=FONT_MONO, size=12),
            y=1.02,
            yanchor="bottom",
            x=0,
            xanchor="left",
        ),
        rangeslider=dict(visible=True, bgcolor=COLOR_PANEL, bordercolor=COLOR_GRID),
    )
    return fig


def find_active_roni_event(roni_df: pd.DataFrame):
    """Devuelve (etiqueta_evento, temporada_inicio, año_inicio) para la racha
    vigente en la última fila, o (None, None, None) si no hay evento activo
    en este momento."""
    df = roni_df.sort_values(["year", "ref_month"]).reset_index(drop=True)
    latest = df.iloc[-1]

    if pd.isna(latest["evento_roni"]):
        return None, None, None

    evento = latest["evento_roni"]
    i = len(df) - 1
    while i > 0 and df.iloc[i - 1]["evento_roni"] == evento:
        i -= 1
    inicio = df.iloc[i]
    return evento, inicio["season"], int(inicio["year"])


def _kpi_card_style(color: str) -> dict:
    return {
        "backgroundColor": COLOR_PANEL,
        "color": COLOR_TEXT,
        "borderRadius": "6px",
        "borderTop": f"4px solid {color}",
        "padding": "20px",
        "textAlign": "center",
        "flex": "1",
        "margin": "0 10px",
    }


def roni_kpi_card(
    estado_roni: str, valor: float, fecha_label: str,
    evento: str, temporada_inicio: str, anio_inicio: int,
) -> html.Div:
    color = SEMAFORO_COLOR.get(estado_roni, COLOR_TEXT_MUTED)

    if evento is None:
        evento_texto = "Sin evento confirmado (sin racha de 5+ temporadas)"
    else:
        evento_texto = f"{evento} desde {temporada_inicio} {anio_inicio}"

    return html.Div(
        style=_kpi_card_style(color),
        children=[
            html.H4(
                "Estado RONI",
                style={"margin": "0 0 8px 0", "fontFamily": FONT_DISPLAY, "fontWeight": "500", "color": COLOR_TEXT_MUTED},
            ),
            html.H2(estado_roni, style={"margin": "0 0 4px 0", "fontFamily": FONT_DISPLAY, "fontWeight": "700", "color": color}),
            html.P(
                f"Valor: {valor:.2f} ({fecha_label})",
                style={"margin": "0 0 8px 0", "fontFamily": FONT_MONO},
            ),
            html.Hr(style={"border": "none", "borderTop": f"1px solid {COLOR_GRID}", "margin": "8px 0"}),
            html.P(evento_texto, style={"margin": "0", "fontSize": "13px", "color": COLOR_TEXT_MUTED}),
        ],
    )


def kpi_card(titulo: str, estado: str, valor: float, fecha_label: str) -> html.Div:
    color = SEMAFORO_COLOR.get(estado, COLOR_TEXT_MUTED)
    return html.Div(
        style=_kpi_card_style(color),
        children=[
            html.H4(
                titulo,
                style={"margin": "0 0 8px 0", "fontFamily": FONT_DISPLAY, "fontWeight": "500", "color": COLOR_TEXT_MUTED},
            ),
            html.H2(estado, style={"margin": "0 0 4px 0", "fontFamily": FONT_DISPLAY, "fontWeight": "700", "color": color}),
            html.P(
                f"Valor: {valor:.2f} ({fecha_label})",
                style={"margin": "0", "fontFamily": FONT_MONO},
            ),
        ],
    )


def build_dashboard_content(df: pd.DataFrame) -> list:
    icen_df = df.dropna(subset=["icen"]).sort_values("date")
    roni_df = df.dropna(subset=["roni"]).sort_values("date")

    latest_icen = icen_df.iloc[-1]
    latest_roni = roni_df.iloc[-1]

    estado_icen = categorize_icen(latest_icen["icen"])
    estado_roni = categorize_roni(latest_roni["roni"])
    evento, temporada_inicio, anio_inicio = find_active_roni_event(roni_df)

    return [
        html.Div(
            style={"display": "flex", "marginBottom": "24px"},
            children=[
                kpi_card(
                    "Estado ICEN", estado_icen, latest_icen["icen"],
                    f"{int(latest_icen['year'])}-{int(latest_icen['month']):02d}",
                ),
                roni_kpi_card(
                    estado_roni, latest_roni["roni"],
                    f"{latest_roni['season']} {int(latest_roni['year'])}",
                    evento, temporada_inicio, anio_inicio,
                ),
            ],
        ),
        dcc.Graph(figure=build_timeseries_figure(df)),
        dcc.Markdown(
            """
**Categorización del estado actual:**

- **RONI**: incluye detección de eventos por persistencia (5 temporadas
  consecutivas cruzando el umbral ±0.5), no solo el valor puntual.
- **ICEN**: se muestra únicamente el valor puntual más reciente, sin regla
  de persistencia (3 meses consecutivos) todavía implementada. Además, se
  usa la metodología de umbrales fijos en °C (Nota Técnica ENFEN 01-2024)
  en vez de la metodología vigente por percentiles (Informes ENFEN 2026),
  ya que el rango base de años para calcular los percentiles no tiene una
  regla de actualización oficial confirmada — ver detalle en el
  repositorio del proyecto.
            """,
            style={"fontSize": "12px", "color": COLOR_TEXT_MUTED},
        ),
    ]


def run_etl_pipeline() -> None:
    fetch_icen.main()
    fetch_roni.main()
    transform.main()


def build_layout() -> html.Div:
    return html.Div(
        style={
            "fontFamily": FONT_DISPLAY,
            "backgroundColor": COLOR_BG,
            "color": COLOR_TEXT,
            "minHeight": "100vh",
            "padding": "24px",
        },
        children=[
            html.Div(
                style={"maxWidth": "1100px", "margin": "0 auto"},
                children=[
                    html.H1("Vigía ENOS", style={"fontWeight": "700", "marginBottom": "0"}),
                    html.Div(
                        style={
                            "height": "4px",
                            "width": "100%",
                            "background": f"linear-gradient(to right, {COLOR_COLD}, {COLOR_TEXT}, {COLOR_WARM})",
                            "margin": "10px 0 20px 0",
                            "borderRadius": "2px",
                        },
                    ),
                    html.P(
                        "Monitoreo del fenómeno El Niño / La Niña — ICEN (IGP) y RONI (NOAA CPC).",
                        style={"color": COLOR_TEXT_MUTED},
                    ),
                    html.Details(
                        style={
                            "marginBottom": "20px",
                            "backgroundColor": COLOR_PANEL,
                            "borderLeft": f"3px solid {COLOR_COLD}",
                            "borderRadius": "4px",
                            "padding": "12px 16px",
                        },
                        children=[
                            html.Summary(
                                "¿Qué son ICEN y RONI?",
                                style={"cursor": "pointer", "fontWeight": "700", "color": COLOR_TEXT},
                            ),
                            dcc.Markdown(
                                """
**ICEN** (Índice Costero El Niño) mide la anomalía de temperatura
superficial del mar frente a la costa peruana (región Niño 1+2). Lo
calcula el IGP y refleja las condiciones oceánicas locales que afectan
directamente el clima y la pesca en Perú.

**RONI** (Relative Oceanic Niño Index) mide la anomalía en el Pacífico
central-oriental (región Niño 3.4). Lo calcula NOAA y es el estándar
internacional para monitorear el ENOS a escala global.

Existen ambos porque el fenómeno El Niño puede manifestarse de forma
distinta en la costa peruana que en el Pacífico central: un evento puede
verse fuerte en RONI pero débil en ICEN, o viceversa.
                                """,
                                style={"fontSize": "13px", "color": COLOR_TEXT_MUTED, "marginTop": "8px"},
                            ),
                        ],
                    ),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "8px"},
                        children=[
                            html.Button(
                                "Actualizar datos", id="actualizar-btn", n_clicks=0,
                                className="btn-actualizar",
                            ),
                            html.Span(
                                get_last_update_label(), id="ultima-actualizacion",
                                style={"fontSize": "13px", "color": COLOR_TEXT_MUTED, "fontFamily": FONT_MONO},
                            ),
                        ],
                    ),
                    dcc.Loading(
                        id="loading-dashboard",
                        type="circle",
                        color=COLOR_COLD,
                        children=html.Div(
                            id="dashboard-content",
                            children=build_dashboard_content(load_data()),
                        ),
                    ),
                    html.P(
                        "Desarrollado por Christian Gonzales Komiya",
                        style={
                            "fontSize": "12px", "color": COLOR_TEXT_MUTED,
                            "textAlign": "center", "marginTop": "32px",
                        },
                    ),
                ],
            ),
        ],
    )


app = Dash(__name__)
app.title = "Vigía ENOS"

app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            body {
                margin: 0;
                background-color: """ + COLOR_BG + """;
            }
            .btn-actualizar {
                background-color: """ + COLOR_PANEL + """;
                border: 1px solid """ + COLOR_COLD + """;
                color: """ + COLOR_TEXT + """;
                font-family: 'Space Grotesk', sans-serif;
                font-weight: 500;
                padding: 10px 18px;
                border-radius: 4px;
                cursor: pointer;
                transition: background-color 0.15s ease;
            }
            .btn-actualizar:hover {
                background-color: """ + COLOR_GRID + """;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""

app.layout = build_layout()


@app.callback(
    Output("dashboard-content", "children"),
    Output("ultima-actualizacion", "children"),
    Input("actualizar-btn", "n_clicks"),
    prevent_initial_call=True,
)
def actualizar_datos(n_clicks):
    try:
        run_etl_pipeline()
        df = load_data()
        return build_dashboard_content(df), get_last_update_label()
    except Exception as exc:
        df = load_data()
        mensaje = f"Error al actualizar ({exc}). Mostrando últimos datos disponibles."
        return build_dashboard_content(df), mensaje


if __name__ == "__main__":
    app.run()

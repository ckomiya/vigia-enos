# Vigía ENOS

Dashboard en Dash que muestra la evolución del ICEN y el RONI, con KPIs
de estado actual (Neutro / El Niño / La Niña).

**Demo:** https://vigia-enos.onrender.com/

## ¿Qué es?

- **ICEN** (Índice Costero El Niño): mide la anomalía de temperatura
  superficial del mar frente a la costa peruana. Fuente: IGP.
- **RONI** (Relative Oceanic Niño Index): mide la anomalía en el Pacífico
  central-oriental. Fuente: NOAA CPC.

El dashboard muestra ambos en un gráfico de serie temporal con umbrales de
categorización, dos KPIs tipo semáforo con el estado más reciente de cada
índice, y un indicador de evento por persistencia (5+ temporadas
consecutivas) para el RONI.

## Requisitos

- Python 3.11+ (entorno virtual incluido en `venv/`)
- Dependencias en `requirements.txt`

## Instalación

```
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## Uso

### 1. Descargar y procesar los datos

```
venv\Scripts\python.exe etl\fetch_icen.py
venv\Scripts\python.exe etl\fetch_roni.py
venv\Scripts\python.exe etl\transform.py
```

Esto guarda snapshots crudos en `data/raw/` y los datos procesados en
`data/processed/` (`icen.csv`, `roni.csv`, `merged.csv`).

### 2. Correr el dashboard

```
venv\Scripts\python.exe app\main.py
```

Abre `http://127.0.0.1:8050/` en el navegador. El botón "Actualizar datos"
en la propia interfaz vuelve a correr el pipeline completo (los 3 comandos
de arriba) sin necesidad de reiniciar la app.

## Estructura del proyecto

```
etl/
  fetch_icen.py     # descarga y parsea ICEN (IGP)
  fetch_roni.py     # descarga y parsea RONI (NOAA CPC)
  transform.py      # une ambas series, categoriza y detecta eventos RONI
app/
  main.py           # dashboard Dash (single page)
data/
  raw/              # snapshots crudos descargados (no versionados)
  processed/        # CSVs procesados (no versionados)
CLAUDE.md           # contexto y decisiones del proyecto para retomarlo
```

## Metodología de categorización

Ver `CLAUDE.md` para el detalle completo de umbrales, fuentes y decisiones
tomadas (ej. por qué se usa la metodología de valores fijos para ICEN en
vez de percentiles).

## Stack

Python, Dash, Plotly, pandas, requests. Sin frameworks JS adicionales.

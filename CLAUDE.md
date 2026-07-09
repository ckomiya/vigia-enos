# Vigía ENOS

Dashboard en Dash que muestra la evolución del ICEN y el RONI, con KPIs
de estado actual (Neutro / El Niño / La Niña).

## Fase 1 (MVP) — COMPLETADA (alcance final del proyecto)

### Fuentes
- ICEN: http://met.igp.gob.pe/datos/ICEN.txt
  (mayúsculas, sin "www." — el servidor es case-sensitive.
  Texto plano con líneas de comentario "%" seguidas de filas "yy mm ICEN")
- RONI: https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt
  (Índice Oceánico Niño Relativo — reemplaza al ONI clásico como estándar
  oficial de NOAA para el monitoreo ENOS desde 2026. Texto plano, columnas:
  SEAS YR ANOM. SEAS es una temporada de 3 meses tipo "DJF", "JFM", etc.)

### Umbrales de categorización

#### RONI (Pacífico central, Niño 3.4)
- El Niño: RONI >= 0.5
- La Niña: RONI <= -0.5
- Neutro: -0.5 < RONI < 0.5

#### ICEN (costa peruana, Niño 1+2)

**DECISIÓN TOMADA para el MVP: se usa la metodología de valores fijos
(abajo), NO percentiles.** Motivo: los umbrales fijos ya estaban
confirmados con fuente oficial, mientras que el rango exacto de años
para calcular percentiles no tiene una regla de actualización publicada
(se confirmó con búsqueda específica que no existe tal regla). Revisar
esta decisión si se retoma el cálculo de percentiles en una fase futura.

- Fría: ICEN < -0.7
- Neutra: -0.7 <= ICEN <= 0.5
- Cálida débil: 0.5 < ICEN <= 1.3
- Cálida moderada/fuerte/extraordinaria: no confirmados en esta metodología
  (Nota Técnica ENFEN 01-2024)

**Metodología alternativa NO implementada (para fase futura, si se desea
mayor precisión): percentiles respecto al periodo base 1950-2023**
(Informes ENFEN 2026, ej. Año 12 N°02 y N°05):
- Condiciones Cálidas: Débil (>P75 y <=P90), Moderada (>P90 y <=P95),
  Fuerte (>P95 y <=P99), Extraordinaria (>P99)
- Condiciones Frías: Débil (>=P10 y <P25), Moderada (>=P4 y <P10),
  Fuerte (<P4)
- Cálculo: `df['icen'].quantile(0.90)` etc. sobre la serie histórica completa.
- Periodo base 1950-2023 vigente en 2026, SIN regla publicada de
  actualización futura (confirmado con búsqueda) — a diferencia de la
  climatología de referencia, que sí se actualiza cada 5 años.

### Reglas de persistencia para declarar "evento"
- ICEN: condición cálida (o fría) sostenida durante al menos 3 meses
  consecutivos. Magnitud del evento = la categoría más alta alcanzada
  durante esos meses. (PENDIENTE de implementar — documentado para
  fase posterior, simétrico a lo ya hecho con RONI abajo)
- RONI: anomalía sostenida durante al menos 5 temporadas consecutivas
  de 3 meses (sin romper la racha). **IMPLEMENTADO**: columna
  `evento_roni` en el CSV procesado, con un tercer indicador en el
  dashboard mostrando si hay evento vigente y desde cuándo.

### Resultado del MVP
- ETL en etl/, app Dash en app/main.py.
- Snapshots crudos en data/raw/ antes de transformar.
- Dashboard con: 2 KPIs semáforo (ICEN, RONI) + indicador de evento por
  persistencia (RONI) + gráfico de serie temporal con botones de rango
  rápido (1/5/10 años/Todo) + rangeslider, por defecto mostrando últimos
  10 años + sección colapsable con explicación breve de ICEN/RONI.

### Stack
Python, Dash, Plotly, pandas, requests. Sin frameworks JS adicionales.
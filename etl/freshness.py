"""Verifica si las fuentes (IGP, NOAA) tienen datos nuevos y, solo en ese
caso, regenera los CSV procesados.

La comparación es contra el texto crudo guardado en data/raw/ (detecta tanto
meses nuevos como correcciones a valores pasados). Para no consultar las
fuentes en cada visita, se respeta un intervalo mínimo entre verificaciones.
"""
import os
import threading
import time
from datetime import datetime

from etl import fetch_icen, fetch_roni, transform

CHECK_INTERVAL_SECONDS = 6 * 3600

ACTUALIZADO = "actualizado"
SIN_CAMBIOS = "sin cambios"
OMITIDO = "omitido"  # dentro del intervalo, no se consultaron las fuentes

_lock = threading.Lock()
_last_check_ts: float | None = None
_last_check_at: datetime | None = None


def get_last_check_at() -> datetime | None:
    return _last_check_at


def _write_atomic(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _changed(path, new_text: str) -> bool:
    return not path.exists() or path.read_text(encoding="utf-8") != new_text


def check_and_update(force: bool = False) -> str:
    """Devuelve ACTUALIZADO, SIN_CAMBIOS u OMITIDO. Propaga excepciones de red
    para que quien llama decida cómo avisar al usuario."""
    global _last_check_ts, _last_check_at

    with _lock:
        now = time.time()
        if (
            not force
            and _last_check_ts is not None
            and now - _last_check_ts < CHECK_INTERVAL_SECONDS
        ):
            return OMITIDO

        icen_text = fetch_icen.fetch_raw()
        roni_text = fetch_roni.fetch_raw()

        icen_changed = _changed(fetch_icen.RAW_PATH, icen_text)
        roni_changed = _changed(fetch_roni.RAW_PATH, roni_text)

        if icen_changed or roni_changed:
            # Parsear antes de escribir nada: si el formato cambió y falla,
            # los datos locales quedan intactos.
            icen_df = fetch_icen.parse_icen(icen_text)
            roni_df = fetch_roni.parse_roni(roni_text)

            _write_atomic(fetch_icen.RAW_PATH, icen_text)
            _write_atomic(fetch_roni.RAW_PATH, roni_text)
            icen_df.to_csv(fetch_icen.PROCESSED_PATH, index=False)
            roni_df.to_csv(fetch_roni.PROCESSED_PATH, index=False)
            transform.main()

        _last_check_ts = now
        _last_check_at = datetime.now()
        return ACTUALIZADO if (icen_changed or roni_changed) else SIN_CAMBIOS

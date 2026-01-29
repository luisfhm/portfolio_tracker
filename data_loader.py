# data_loader.py
import json
import os
import pandas as pd

def load_positions(path=None):
    """
    Carga posiciones desde archivo (local) o desde secrets (cloud).
    - Si se da `path`, se carga desde archivo (ej: demo.json o positions.json).
    - Si no se da `path`, intenta cargar desde secrets (modo real en cloud).
      Si no hay secrets (ej: ejecución local sin path), intenta cargar positions.json.
    """
    if path is not None:
        # Cargar desde archivo explícito (ej: demo.json)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # Modo "real": intentar secrets primero, luego archivo local
        data = None

        # 1. Intentar desde Streamlit secrets (solo en cloud o local con secrets)
        try:
            import streamlit as st
            if "REAL_POSITIONS_JSON" in st.secrets:
                json_str = st.secrets["REAL_POSITIONS_JSON"]
                data = json.loads(json_str)
        except Exception:
            pass  # st.secrets no disponible o falló

        # 2. Si no hay secrets, intentar desde archivo local positions.json
        if data is None:
            local_path = "positions.json"
            if os.path.exists(local_path):
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                raise FileNotFoundError(
                    "No se encontró positions.json en local ni REAL_POSITIONS_JSON en secrets."
                )

    # Normalizar a DataFrame
    rows = []
    for item in data.get("global", []):
        item = item.copy()
        item["mercado"] = "Global"
        rows.append(item)
    for item in data.get("mexico", []):
        item = item.copy()
        item["mercado"] = "México"
        rows.append(item)

    return pd.DataFrame(rows)
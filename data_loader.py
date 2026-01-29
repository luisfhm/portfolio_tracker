# data_loader.py
import json
import os
import pandas as pd

def load_positions(path=None):
    """
    Carga posiciones desde:
    - Archivo explícito si se pasa `path` (ej: demo.json)
    - st.secrets["REAL_POSITIONS_JSON"] si existe (modo real en cloud)
    - positions.json local si no hay secrets ni path (modo real local)
    """
    data = None

    if path is not None:
        # Modo demo o prueba explícita
        file_path = path
    else:
        # Modo real: primero secrets, luego archivo local
        try:
            import streamlit as st
            if "REAL_POSITIONS_JSON" in st.secrets:
                json_str = st.secrets["REAL_POSITIONS_JSON"]
                data = json.loads(json_str)
        except Exception:
            pass  # No estamos en Streamlit o no hay secrets

        if data is None:
            file_path = "positions.json"
        else:
            # Ya tenemos data desde secrets → no necesitamos abrir archivo
            pass

    # Si no vino de secrets, cargar desde archivo
    if data is None:
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"No se encontró el archivo: {file_path}\n"
                "Asegúrate de tener 'positions.json' (modo real local) o 'demo.json' (modo demo), "
                "o configura REAL_POSITIONS_JSON en Streamlit Secrets (modo real cloud)."
            )
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    # Construir DataFrame con columna "mercado" correcta desde el origen
    rows = []

    for item in data.get("global", []):
        row = item.copy()
        row["mercado"] = "Global"
        rows.append(row)

    for item in data.get("mexico", []):
        row = item.copy()
        row["mercado"] = "México"
        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("El JSON no contiene posiciones válidas en 'global' ni 'mexico'.")

    # Aseguramos tipos básicos
    df["titulos"] = pd.to_numeric(df["titulos"], errors="coerce")
    df["costo_promedio"] = pd.to_numeric(df["costo_promedio"], errors="coerce")

    return df